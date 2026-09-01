"""Unix-socket powers transport under ``SO_PEERCRED`` (TN-17 / QMX-F045).

Story 25.7. Peer credentials from the AF_UNIX transport resolve exactly the
declared operator or ops UID — neither equal to the fixed ``qmx`` service
account. Unknown peers are refused and journaled before any handler runs.
Claimed identities in the payload are recorded beside the peer credential and
never override it. Agent / machine / service signers are refused; the principal
set is closed at ``{operator, ops}``.
"""

from __future__ import annotations

import socket
import struct
from collections.abc import Mapping, MutableSequence, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Protocol, cast

from qmf.core.refusal import Ok, Result, is_refusal

from qmn.doors.http._refuse import clean_token, invalid, policy

__all__ = [
    "AGENT_SIGNER_PREFIXES",
    "CLOSED_POWERS",
    "OPERATOR_ONLY_POWERS",
    "OPERATOR_PRINCIPAL",
    "OPS_ALLOWED_POWERS",
    "OPS_PRINCIPAL",
    "POWERS_SOCKET_MODE",
    "POWERS_SOCKET_OWNER",
    "POWERS_SOCKET_PATH",
    "POWERS_TRANSPORT_SURFACE",
    "PRINCIPAL_SET",
    "SERVICE_ACCOUNT_NAME",
    "AuthenticatedPeer",
    "DeclaredPrincipals",
    "PeerCredential",
    "PowersCallAuthorization",
    "PowersJournal",
    "RecordingPowersJournal",
    "authorize_powers_call",
    "declare_principals",
    "evaluate_unit_principals",
    "is_human_signer",
    "ops_power_allowed",
    "peercred_option",
    "powers_transport_identity",
    "read_peercred",
    "resolve_peer_principal",
]

POWERS_TRANSPORT_SURFACE: Final[str] = "qmn.doors.http.powers"

POWERS_SOCKET_PATH: Final[str] = "/run/qmn/powers.sock"
POWERS_SOCKET_OWNER: Final[str] = "qmx:qmxops"
POWERS_SOCKET_MODE: Final[int] = 0o660
SERVICE_ACCOUNT_NAME: Final[str] = "qmx"

OPERATOR_PRINCIPAL: Final[str] = "operator"
OPS_PRINCIPAL: Final[str] = "ops"
# Closed principal set — agent is never a member (QMX-F045 / DEC-0234).
PRINCIPAL_SET: Final[frozenset[str]] = frozenset({OPERATOR_PRINCIPAL, OPS_PRINCIPAL})

# Ops principal may call only these powers (plus evidence reads on the other door).
OPS_ALLOWED_POWERS: Final[frozenset[str]] = frozenset(
    {
        "notify_test",
        "restore_drill_run",
        "config_validate",
        "hub_publish",
    }
)

# Operator-only powers refused to ops BY THE TRANSPORT before handler dispatch.
OPERATOR_ONLY_POWERS: Final[frozenset[str]] = frozenset(
    {
        "resurrect",
        "resume",
        "de_escalate",
        "resolve_unknown",
        "flatten",
        "kill_switch_escalate",
        "paper_flip",
        "paper_epoch_reset",
        "promotion_sign",
        "activation",
        "config_version_activate",
        "seat_reinstate",
        "state_carry",
        "carries_ledger",
        "continues_performance",
        "value_status_countersign",
        "sealed_period_final_look",
        "settings_edit",
        "secrets_is_set",
        "attestation",
        "countersign",
    }
)

CLOSED_POWERS: Final[frozenset[str]] = OPS_ALLOWED_POWERS | OPERATOR_ONLY_POWERS

# Claimed-signer prefixes that prove a non-human actor (QMX-F045).
AGENT_SIGNER_PREFIXES: Final[tuple[str, ...]] = (
    "agent:",
    "machine:",
    "service:",
    "bot:",
    "qma:",
    "automation:",
    "cron:",
    "systemd:",
)

# Linux ``SO_PEERCRED`` — asm-generic value; ``socket.SO_PEERCRED`` when present.
_SO_PEERCRED_LINUX: Final[int] = 17
_UCRED_FMT: Final[str] = "3i"
_UCRED_SIZE: Final[int] = struct.calcsize(_UCRED_FMT)


class PowersJournal(Protocol):
    """Append-only sink for powers transport decisions (admit or refuse)."""

    def append(self, record: Mapping[str, object], /) -> Result[Mapping[str, object]]:
        """Persist one powers journal record."""
        ...


@dataclass
class RecordingPowersJournal:
    """Test/double journal — records every transport decision."""

    records: MutableSequence[Mapping[str, object]] = field(
        default_factory=list[Mapping[str, object]]
    )

    def append(self, record: Mapping[str, object], /) -> Result[Mapping[str, object]]:
        frozen = MappingProxyType(dict(record))
        self.records.append(frozen)
        return Ok(frozen)


@dataclass(frozen=True, slots=True)
class PeerCredential:
    """``SO_PEERCRED`` triple read from the AF_UNIX transport (pid, uid, gid)."""

    pid: int
    uid: int
    gid: int

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType({"pid": self.pid, "uid": self.uid, "gid": self.gid})


@dataclass(frozen=True, slots=True)
class DeclaredPrincipals:
    """Two peer principals by uid from the resolved node-config (DEC-0234).

    Neither uid equals the fixed ``qmx`` service account. The principal set is
    closed — no agent / invented principal may be added.
    """

    operator_uid: int
    ops_uid: int
    service_account_uid: int

    def principal_for_uid(self, uid: int) -> str | None:
        if uid == self.operator_uid:
            return OPERATOR_PRINCIPAL
        if uid == self.ops_uid:
            return OPS_PRINCIPAL
        return None


@dataclass(frozen=True, slots=True)
class AuthenticatedPeer:
    """Transport-resolved principal — never taken from the payload."""

    principal: str
    peer: PeerCredential


@dataclass(frozen=True, slots=True)
class PowersCallAuthorization:
    """Admitted powers call: peer credential is authoritative over any claim."""

    principal: str
    peer: PeerCredential
    power: str
    claimed_signer: str | None
    peer_overrides_claim: bool


def powers_transport_identity() -> Mapping[str, object]:
    """Identity-bearing constants of the powers transport (no invented principals)."""
    return MappingProxyType(
        {
            "surface": POWERS_TRANSPORT_SURFACE,
            "socket_path": POWERS_SOCKET_PATH,
            "socket_owner": POWERS_SOCKET_OWNER,
            "socket_mode": POWERS_SOCKET_MODE,
            "service_account": SERVICE_ACCOUNT_NAME,
            "principal_set": tuple(sorted(PRINCIPAL_SET)),
            "ops_allowed_powers": tuple(sorted(OPS_ALLOWED_POWERS)),
            "closed_powers": tuple(sorted(CLOSED_POWERS)),
            "agent_never_a_principal": True,
            "residual_risk": "SO_PEERCRED proves an account, not a human (A32)",
        }
    )


def declare_principals(
    *,
    operator_uid: object,
    ops_uid: object,
    service_account_uid: object,
) -> Result[DeclaredPrincipals]:
    """Validate and seal the two declared peer principals (DEC-0234 / DEC-0236)."""
    op = _as_uid(operator_uid, "operator_uid")
    if is_refusal(op):
        return op
    ops = _as_uid(ops_uid, "ops_uid")
    if is_refusal(ops):
        return ops
    svc = _as_uid(service_account_uid, "service_account_uid")
    if is_refusal(svc):
        return svc
    if op.value == ops.value:
        return invalid(
            "principals",
            "operator and ops UIDs must be distinct declared principals",
            operator_uid=op.value,
            ops_uid=ops.value,
        )
    if op.value == svc.value:
        return policy(
            "operator_uid",
            "operator principal must not equal the fixed qmx service account",
            operator_uid=op.value,
            service_account_uid=svc.value,
        )
    if ops.value == svc.value:
        return policy(
            "ops_uid",
            "ops principal must not equal the fixed qmx service account",
            ops_uid=ops.value,
            service_account_uid=svc.value,
        )
    return Ok(
        DeclaredPrincipals(
            operator_uid=op.value,
            ops_uid=ops.value,
            service_account_uid=svc.value,
        )
    )


def resolve_peer_principal(
    *,
    peer: object,
    principals: object,
) -> Result[AuthenticatedPeer]:
    """Map a transport peer credential onto the closed principal set.

    An unknown peer (neither declared UID, including the ``qmx`` service
    account) is a ``policy rejection`` — refused by the transport.
    """
    if not isinstance(peer, PeerCredential):
        return invalid(
            "peer",
            "powers authentication requires a PeerCredential from SO_PEERCRED",
            given=type(peer).__name__,
        )
    if not isinstance(principals, DeclaredPrincipals):
        return invalid(
            "principals",
            "powers authentication requires DeclaredPrincipals from the resolved config",
            given=type(principals).__name__,
        )
    if peer.uid == principals.service_account_uid:
        return policy(
            "peer",
            "the qmx service account is never a powers principal",
            uid=peer.uid,
            service_account=SERVICE_ACCOUNT_NAME,
        )
    name = principals.principal_for_uid(peer.uid)
    if name is None:
        return policy(
            "peer",
            "powers peer credential is neither declared operator nor ops principal",
            uid=peer.uid,
            operator_uid=principals.operator_uid,
            ops_uid=principals.ops_uid,
        )
    return Ok(AuthenticatedPeer(principal=name, peer=peer))


def ops_power_allowed(power: object) -> bool:
    """True only for the closed ops-principal allow-list."""
    token = clean_token(power)
    return token is not None and token in OPS_ALLOWED_POWERS


def is_human_signer(signer: object) -> bool:
    """False for blank or agent/machine/service-prefixed claimed signers (QMX-F045)."""
    token = clean_token(signer)
    if token is None:
        return False
    folded = token.casefold()
    return not any(folded.startswith(prefix) for prefix in AGENT_SIGNER_PREFIXES)


def authorize_powers_call(
    *,
    peer: object,
    principals: object,
    power: object,
    claimed_signer: object = None,
    journal: PowersJournal | None = None,
) -> Result[PowersCallAuthorization]:
    """Authorize one powers call at the transport — before handler dispatch.

    Peer credentials from ``SO_PEERCRED`` are authoritative. A claimed signer in
    the payload is recorded beside the peer credential and never overrides it.
    Ops is refused every trading/protection/promotion/activation/settings/
    resurrect/attestation/countersign power. Agent signers are refused. An
    unknown power is refused (closed list). Every refusal is journaled when a
    sink is supplied.
    """
    resolved = resolve_peer_principal(peer=peer, principals=principals)
    power_token = clean_token(power)

    if is_refusal(resolved):
        _journal_refusal(
            journal,
            decision="refuse",
            reason="unknown-or-service-peer",
            peer=peer if isinstance(peer, PeerCredential) else None,
            power=power_token,
            claimed_signer=_optional_signer(claimed_signer),
            refusal_field=str(resolved.context.get("field", "peer")),
        )
        return resolved

    if power_token is None:
        refusal = invalid("power", "powers call names a non-blank power")
        _journal_refusal(
            journal,
            decision="refuse",
            reason="blank-power",
            peer=resolved.value.peer,
            principal=resolved.value.principal,
            power=None,
            claimed_signer=_optional_signer(claimed_signer),
            refusal_field="power",
        )
        return refusal

    if power_token not in CLOSED_POWERS:
        refusal = policy(
            "power",
            "powers list is closed; a capability not on it does not exist",
            given=power_token,
        )
        _journal_refusal(
            journal,
            decision="refuse",
            reason="unknown-power",
            peer=resolved.value.peer,
            principal=resolved.value.principal,
            power=power_token,
            claimed_signer=_optional_signer(claimed_signer),
            refusal_field="power",
        )
        return refusal

    if resolved.value.principal == OPS_PRINCIPAL and power_token not in OPS_ALLOWED_POWERS:
        refusal = policy(
            "power",
            "ops principal is refused trading, protection, promotion, activation, "
            "settings, resurrect, attestation, and countersign powers by the transport",
            principal=OPS_PRINCIPAL,
            power=power_token,
        )
        _journal_refusal(
            journal,
            decision="refuse",
            reason="ops-power-refused",
            peer=resolved.value.peer,
            principal=OPS_PRINCIPAL,
            power=power_token,
            claimed_signer=_optional_signer(claimed_signer),
            refusal_field="power",
        )
        return refusal

    signer_token = _optional_signer(claimed_signer)
    if claimed_signer is not None and signer_token is None:
        refusal = invalid(
            "claimed_signer",
            "claimed signer is omitted or a non-blank string; blank is invalid",
            given=repr(claimed_signer),
        )
        _journal_refusal(
            journal,
            decision="refuse",
            reason="blank-claimed-signer",
            peer=resolved.value.peer,
            principal=resolved.value.principal,
            power=power_token,
            claimed_signer=None,
            refusal_field="claimed_signer",
        )
        return refusal

    if signer_token is not None and not is_human_signer(signer_token):
        refusal = policy(
            "claimed_signer",
            "agent, machine, and service signers are refused at the powers transport; "
            "humanity beyond the account is asserted by a human signer (QMX-F045)",
            given=signer_token,
            principal=resolved.value.principal,
            power=power_token,
        )
        _journal_refusal(
            journal,
            decision="refuse",
            reason="agent-signer-refused",
            peer=resolved.value.peer,
            principal=resolved.value.principal,
            power=power_token,
            claimed_signer=signer_token,
            refusal_field="claimed_signer",
        )
        return refusal

    # Claimed identity never overrides peer credentials: principal stays peer-derived.
    auth = PowersCallAuthorization(
        principal=resolved.value.principal,
        peer=resolved.value.peer,
        power=power_token,
        claimed_signer=signer_token,
        peer_overrides_claim=True,
    )
    if journal is not None:
        journal.append(
            {
                "event_type": "control action",
                "kind": "powers-transport",
                "decision": "admit",
                "principal": auth.principal,
                "power": auth.power,
                "peer": dict(auth.peer.as_mapping()),
                "claimed_signer": auth.claimed_signer,
                "peer_overrides_claim": True,
            }
        )
    return Ok(auth)


def evaluate_unit_principals(
    *,
    operator_uid: object,
    unit_uids: object,
) -> Result[None]:
    """Preflight: refuse when any systemd unit runs under the operator UID.

    Automated units must never hold the operator principal (DEC-0202 / DEC-0234).
    An agent UID is likewise never admitted into the principal set.
    """
    op = _as_uid(operator_uid, "operator_uid")
    if is_refusal(op):
        return op
    if not isinstance(unit_uids, Sequence) or isinstance(unit_uids, (str, bytes)):
        return invalid(
            "unit_uids",
            "unit_uids is a sequence of integer UIDs declared on host units",
            given=type(unit_uids).__name__,
        )
    uids = cast("Sequence[object]", unit_uids)
    for index, raw in enumerate(uids):
        uid = _as_uid(raw, f"unit_uids[{index}]")
        if is_refusal(uid):
            return uid
        if uid.value == op.value:
            return policy(
                "unit_principals",
                "preflight refuses to boot when any systemd unit runs under the "
                "operator-principal uid; no automated unit may be the operator",
                operator_uid=op.value,
                unit_uid=uid.value,
                unit_index=index,
            )
    return Ok(None)


def peercred_option() -> int:
    """Return the platform ``SO_PEERCRED`` option constant (Linux)."""
    return int(getattr(socket, "SO_PEERCRED", _SO_PEERCRED_LINUX))


def read_peercred(sock: object) -> Result[PeerCredential]:
    """Read ``SO_PEERCRED`` from a connected AF_UNIX stream socket (Linux).

    Unit tests inject ``PeerCredential`` directly; this path is the production
    reader and refuses when the platform cannot supply peer credentials.
    """
    getsockopt = getattr(sock, "getsockopt", None)
    if not callable(getsockopt):
        return invalid(
            "sock",
            "SO_PEERCRED requires a connected AF_UNIX socket with getsockopt",
            given=type(sock).__name__,
        )
    try:
        raw = getsockopt(socket.SOL_SOCKET, peercred_option(), _UCRED_SIZE)
    except (AttributeError, OSError, TypeError, ValueError) as exc:
        return policy(
            "peer",
            "SO_PEERCRED peer credential could not be read from the transport",
            error=type(exc).__name__,
            detail=str(exc),
        )
    if not isinstance(raw, (bytes, bytearray)):
        return policy(
            "peer",
            "SO_PEERCRED returned an unexpected credential buffer",
            size=None,
            expected=_UCRED_SIZE,
        )
    buffer = bytes(raw)
    if len(buffer) != _UCRED_SIZE:
        return policy(
            "peer",
            "SO_PEERCRED returned an unexpected credential buffer",
            size=len(buffer),
            expected=_UCRED_SIZE,
        )
    pid, uid, gid = struct.unpack(_UCRED_FMT, buffer)
    if pid < 0 or uid < 0 or gid < 0:
        return policy(
            "peer",
            "SO_PEERCRED returned a negative pid/uid/gid",
            pid=pid,
            uid=uid,
            gid=gid,
        )
    return Ok(PeerCredential(pid=pid, uid=uid, gid=gid))


def _as_uid(raw: object, field: str) -> Result[int]:
    if isinstance(raw, bool) or not isinstance(raw, int):
        return invalid(field, "uid is a non-negative integer", given=repr(raw))
    if raw < 0:
        return invalid(field, "uid is a non-negative integer", given=raw)
    return Ok(raw)


def _optional_signer(raw: object) -> str | None:
    if raw is None:
        return None
    return clean_token(raw)


def _journal_refusal(
    journal: PowersJournal | None,
    *,
    decision: str,
    reason: str,
    peer: PeerCredential | None,
    power: str | None,
    claimed_signer: str | None,
    refusal_field: str,
    principal: str | None = None,
) -> None:
    if journal is None:
        return
    body: dict[str, object] = {
        "event_type": "control action",
        "kind": "powers-transport",
        "decision": decision,
        "reason": reason,
        "refusal_field": refusal_field,
        "power": power,
        "claimed_signer": claimed_signer,
        "peer_overrides_claim": True,
    }
    if principal is not None:
        body["principal"] = principal
    if peer is not None:
        body["peer"] = dict(peer.as_mapping())
    journal.append(body)
