"""Paper-milestone powers and secret probes (Story 28.4 / QMX-F045/F064).

Unknown peer, ops-principal forbidden call, automated operator UID, secret leak
pattern, stale-state authorization, and sandbox promotion each refuse at the
named boundary and journal without exposing a secret. DevOps recipes remain
unable to trade. A live VPS firewall apply is not a factory AC.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableSequence, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, TypeVar, cast

from qmf.core import Fingerprint, Ok, Result, TypedRefusal, fingerprint, is_ok, is_refusal

from qmn.doors.http.powers import (
    OPERATOR_PRINCIPAL,
    OPS_PRINCIPAL,
    DeclaredPrincipals,
    PeerCredential,
    RecordingPowersJournal,
    authorize_powers_call,
    declare_principals,
    evaluate_unit_principals,
)
from qmn.doors.library import DoorRuntime, enact_power
from qmn.host._refuse import invalid, policy
from qmn.promotion.hub import HubArtifact, publish_hub_fragment
from qmn.secrets.scan import scan_payload_for_secret_values

__all__ = [
    "DEVOPS_FORBIDDEN_ACTIONS",
    "SECURITY_PROBES_CLASS",
    "SECURITY_PROBES_FORMAT_VERSION",
    "SECURITY_PROBES_SURFACE",
    "SECURITY_PROBE_NAMES",
    "SecurityProbeInputs",
    "SecurityProbeReport",
    "devops_recipe_may_trade",
    "refuse_live_vps_firewall_probe",
    "run_paper_milestone_security_probes",
]

T = TypeVar("T")

SECURITY_PROBES_SURFACE: Final[str] = "qmn.host.security_probes"
SECURITY_PROBES_CLASS: Final[str] = "paper-milestone-security-probes"
SECURITY_PROBES_FORMAT_VERSION: Final[int] = 1

SECURITY_PROBE_NAMES: Final[tuple[str, ...]] = (
    "unknown-peer",
    "ops-principal-forbidden",
    "automated-operator-uid",
    "secret-leak-pattern",
    "stale-state-authorization",
    "sandbox-promotion",
)

# Mirrors qmn/deploy/boundary.py FORBIDDEN_RECIPE_ACTIONS (AR-79 / DEC-0202).
# Host code never imports the deploy tree.
DEVOPS_FORBIDDEN_ACTIONS: Final[frozenset[str]] = frozenset(
    {
        "place",
        "cancel",
        "amend",
        "flatten",
        "promote",
        "activate",
        "settings",
        "resurrect",
        "attestation",
        "countersign",
    }
)

_ID_INPUTS: Final[str] = "security_probes.inputs"
_ID_INCOMPLETE: Final[str] = "security_probes.incomplete_probe"
_ID_EXPOSED: Final[str] = "security_probes.secret_exposed"
_ID_FIREWALL: Final[str] = "security_probes.live_vps_firewall"
_ID_TRADE: Final[str] = "security_probes.devops_trade"

_OPERATOR_UID: Final[int] = 1001
_OPS_UID: Final[int] = 1002
_QMX_UID: Final[int] = 1000
_STRANGER_UID: Final[int] = 1999
_FIXTURE_NEEDLE: Final[str] = "fixture-" + "secret-zzzzzzzz"


@dataclass(frozen=True, slots=True)
class SecurityProbeInputs:
    """Injected principals and soak-local skip switches."""

    operator_uid: int = _OPERATOR_UID
    ops_uid: int = _OPS_UID
    service_account_uid: int = _QMX_UID
    stranger_uid: int = _STRANGER_UID
    secret_plaintext: str = _FIXTURE_NEEDLE
    run_live_vps_firewall: bool = False
    claim_devops_can_trade: bool = False


@dataclass
class _ProbeJournal:
    """In-campaign journal that must never retain a secret value."""

    records: MutableSequence[Mapping[str, object]] = field(
        default_factory=list[Mapping[str, object]]
    )

    def append(self, record: Mapping[str, object]) -> None:
        self.records.append(MappingProxyType(dict(record)))


@dataclass(frozen=True, slots=True)
class SecurityProbeReport:
    """Fingerprinted proof of the Story 28.4 powers/secret probes."""

    format_version: int
    fingerprint: Fingerprint
    probes: tuple[str, ...]
    each_refused: bool
    journaled_without_secret: bool
    devops_unable_to_trade: bool
    runs_live_vps_firewall: bool
    sections: Mapping[str, object]

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": SECURITY_PROBES_CLASS,
            "devops_unable_to_trade": self.devops_unable_to_trade,
            "each_refused": self.each_refused,
            "format_version": self.format_version,
            "journaled_without_secret": self.journaled_without_secret,
            "probes": list(self.probes),
            "runs_live_vps_firewall": self.runs_live_vps_firewall,
            "sections": dict(self.sections),
            "surface": SECURITY_PROBES_SURFACE,
        }

    def as_mapping(self) -> Mapping[str, object]:
        body = self.fp1_identity()
        body["fingerprint"] = self.fingerprint.value
        return MappingProxyType(body)


def devops_recipe_may_trade(action: object) -> bool:
    """False for every trading/protection/promotion control verb."""
    if not isinstance(action, str):
        return False
    return action.casefold() not in DEVOPS_FORBIDDEN_ACTIONS


def refuse_live_vps_firewall_probe(**extra: object) -> TypedRefusal:
    """Story 28.4 does not apply a live VPS firewall."""
    return policy(
        "live_vps_firewall",
        "powers/secret probes run in-process; unit/network posture is proven "
        "from templates. A live VPS firewall apply is soak-local.",
        failure_id=_ID_FIREWALL,
        **extra,
    )


def run_paper_milestone_security_probes(
    inputs: object,
) -> Result[SecurityProbeReport]:
    """Refuse each named probe at its boundary and journal without secrets."""
    if not isinstance(inputs, SecurityProbeInputs):
        return invalid(
            "inputs",
            "the security probes take SecurityProbeInputs",
            given=type(inputs).__name__,
            failure_id=_ID_INPUTS,
        )
    if inputs.run_live_vps_firewall is True:
        return refuse_live_vps_firewall_probe()
    if inputs.claim_devops_can_trade is True:
        return policy(
            "devops",
            "DevOps recipes remain unable to trade (AR-79 / DEC-0202 / QMX-F045)",
            failure_id=_ID_TRADE,
        )

    principals = declare_principals(
        operator_uid=inputs.operator_uid,
        ops_uid=inputs.ops_uid,
        service_account_uid=inputs.service_account_uid,
    )
    if is_refusal(principals):
        return _as_refusal(principals)

    journal = RecordingPowersJournal()
    probe_log = _ProbeJournal()
    unknown = _unwrap(_probe_unknown_peer(inputs, principals.value, journal, probe_log))
    if isinstance(unknown, TypedRefusal):
        return unknown
    ops = _unwrap(_probe_ops_forbidden(inputs, principals.value, journal, probe_log))
    if isinstance(ops, TypedRefusal):
        return ops
    automated = _unwrap(_probe_automated_operator_uid(inputs, probe_log))
    if isinstance(automated, TypedRefusal):
        return automated
    leak = _unwrap(_probe_secret_leak(inputs, probe_log))
    if isinstance(leak, TypedRefusal):
        return leak
    stale = _unwrap(_probe_stale_state(probe_log))
    if isinstance(stale, TypedRefusal):
        return stale
    sandbox = _unwrap(_probe_sandbox(probe_log))
    if isinstance(sandbox, TypedRefusal):
        return sandbox

    sections = {
        "automated-operator-uid": dict(automated),
        "ops-principal-forbidden": dict(ops),
        "sandbox-promotion": dict(sandbox),
        "secret-leak-pattern": dict(leak),
        "stale-state-authorization": dict(stale),
        "unknown-peer": dict(unknown),
    }
    missing = [name for name in SECURITY_PROBE_NAMES if name not in sections]
    if missing:
        return policy(
            "probes",
            "every named powers/secret probe must refuse at its boundary",
            missing=missing,
            failure_id=_ID_INCOMPLETE,
        )

    exposed = _secret_in_records(probe_log.records, inputs.secret_plaintext)
    exposed |= _secret_in_records(journal.records, inputs.secret_plaintext)
    if exposed:
        return policy(
            "secret",
            "a secret value appeared on a probe journal",
            failure_id=_ID_EXPOSED,
        )

    each_refused = all(section.get("refused") is True for section in sections.values())
    devops_blocked = all(not devops_recipe_may_trade(action) for action in DEVOPS_FORBIDDEN_ACTIONS)
    identity = {
        "class": SECURITY_PROBES_CLASS,
        "devops_unable_to_trade": devops_blocked,
        "each_refused": each_refused,
        "format_version": SECURITY_PROBES_FORMAT_VERSION,
        "journaled_without_secret": True,
        "probes": list(SECURITY_PROBE_NAMES),
        "runs_live_vps_firewall": False,
        "sections": sections,
        "surface": SECURITY_PROBES_SURFACE,
    }
    stamped = fingerprint(identity)
    if is_refusal(stamped):
        return _as_refusal(stamped)
    return Ok(
        SecurityProbeReport(
            format_version=SECURITY_PROBES_FORMAT_VERSION,
            fingerprint=stamped.value,
            probes=SECURITY_PROBE_NAMES,
            each_refused=each_refused,
            journaled_without_secret=True,
            devops_unable_to_trade=devops_blocked,
            runs_live_vps_firewall=False,
            sections=MappingProxyType(sections),
        )
    )


def _probe_unknown_peer(
    inputs: SecurityProbeInputs,
    principals: DeclaredPrincipals,
    journal: RecordingPowersJournal,
    probe_log: _ProbeJournal,
) -> Result[Mapping[str, object]]:
    result = authorize_powers_call(
        peer=PeerCredential(pid=42, uid=inputs.stranger_uid, gid=100),
        principals=principals,
        power="notify_test",
        journal=journal,
    )
    if is_ok(result):
        return policy("unknown-peer", "unknown peer must be refused before dispatch")
    probe_log.append(
        {
            "probe": "unknown-peer",
            "decision": "refuse",
            "reason": "unknown-or-service-peer",
            "principal": None,
        }
    )
    return Ok(
        MappingProxyType(
            {
                "field": result.context.get("field"),
                "journaled": True,
                "refused": True,
            }
        )
    )


def _probe_ops_forbidden(
    inputs: SecurityProbeInputs,
    principals: DeclaredPrincipals,
    journal: RecordingPowersJournal,
    probe_log: _ProbeJournal,
) -> Result[Mapping[str, object]]:
    refused_powers: list[str] = []
    for power in ("promotion_sign", "flatten", "resurrect", "seat_reinstate"):
        result = authorize_powers_call(
            peer=PeerCredential(pid=7, uid=inputs.ops_uid, gid=100),
            principals=principals,
            power=power,
            journal=journal,
        )
        if is_ok(result):
            return policy(
                "ops-principal-forbidden",
                "ops principal must be refused trading and human-only powers",
                power=power,
            )
        refused_powers.append(power)
        probe_log.append(
            {
                "probe": "ops-principal-forbidden",
                "decision": "refuse",
                "power": power,
                "principal": OPS_PRINCIPAL,
            }
        )
    return Ok(
        MappingProxyType(
            {
                "journaled": True,
                "principal": OPS_PRINCIPAL,
                "refused": True,
                "refused_powers": refused_powers,
            }
        )
    )


def _probe_automated_operator_uid(
    inputs: SecurityProbeInputs,
    probe_log: _ProbeJournal,
) -> Result[Mapping[str, object]]:
    result = evaluate_unit_principals(
        operator_uid=inputs.operator_uid,
        unit_uids=(inputs.service_account_uid, inputs.operator_uid),
    )
    if is_ok(result):
        return policy(
            "automated-operator-uid",
            "preflight must refuse a unit running under the operator UID",
        )
    probe_log.append(
        {
            "probe": "automated-operator-uid",
            "decision": "refuse",
            "reason": "unit-under-operator-uid",
            "unit_uid": result.context.get("unit_uid"),
        }
    )
    return Ok(
        MappingProxyType(
            {
                "field": result.context.get("field"),
                "journaled": True,
                "refused": True,
                "unit_uid": result.context.get("unit_uid"),
            }
        )
    )


def _probe_secret_leak(
    inputs: SecurityProbeInputs,
    probe_log: _ProbeJournal,
) -> Result[Mapping[str, object]]:
    payload = {"note": f"leaked {inputs.secret_plaintext}", "status": "ok"}
    scanned = scan_payload_for_secret_values(
        payload,
        (inputs.secret_plaintext,),
        surface="evidence",
    )
    if is_ok(scanned):
        return policy("secret-leak-pattern", "a secret value on a public surface must refuse")
    probe_log.append(
        {
            "probe": "secret-leak-pattern",
            "decision": "refuse",
            "reason": "secret-leak",
            "surface": "evidence",
            "findings_count": len(cast("tuple[object, ...]", scanned.context.get("findings", ()))),
        }
    )
    if inputs.secret_plaintext in str(probe_log.records[-1]):
        return policy(
            "secret",
            "the leak journal must not carry the secret value",
            failure_id=_ID_EXPOSED,
        )
    return Ok(
        MappingProxyType(
            {
                "failure_id": scanned.context.get("failure_id"),
                "journaled": True,
                "refused": True,
            }
        )
    )


def _probe_stale_state(probe_log: _ProbeJournal) -> Result[Mapping[str, object]]:
    runtime = DoorRuntime(
        boot_epoch="boot-28-4",
        composition_fp="fp1:compose-28-4",
        knowledge_time_ns=100,
        watermark_ns=100,
        source_time_ns=100,
        receive_time_ns=100,
        evidence_channel_budget=8,
    )
    result = enact_power(
        runtime,
        power="notify_test",
        principal=OPERATOR_PRINCIPAL,
        artifact_key="stale-28-4",
        evidence_knowledge_time_ns=50,
        requested={"ok": True},
    )
    if is_ok(result):
        return policy("stale-state-authorization", "stale evidence cannot authorize a power")
    probe_log.append(
        {
            "probe": "stale-state-authorization",
            "decision": "refuse",
            "reason": "stale-evidence",
            "power": "notify_test",
        }
    )
    return Ok(
        MappingProxyType(
            {
                "field": result.context.get("field"),
                "journaled": True,
                "refused": True,
            }
        )
    )


def _probe_sandbox(probe_log: _ProbeJournal) -> Result[Mapping[str, object]]:
    fp = fingerprint({"class": "sandbox-bot", "label": "28-4"})
    if is_refusal(fp):
        return _as_refusal(fp)
    artifact = HubArtifact.try_create(
        artifact_key="sandbox-28-4",
        fp1=fp.value,
        provenance="sandbox",
    )
    if is_refusal(artifact):
        return _as_refusal(artifact)
    published = publish_hub_fragment(artifact.value)
    if is_ok(published):
        return policy("sandbox-promotion", "sandbox provenance must refuse hub publish")
    probe_log.append(
        {
            "probe": "sandbox-promotion",
            "decision": "refuse",
            "reason": "sandbox-provenance",
            "crossing": "publish",
        }
    )
    return Ok(
        MappingProxyType(
            {
                "crossing": "publish",
                "field": published.context.get("field"),
                "journaled": True,
                "refused": True,
            }
        )
    )


def _secret_in_records(
    records: Sequence[Mapping[str, object]],
    plaintext: str,
) -> bool:
    return any(plaintext and plaintext in str(dict(record)) for record in records)


def _unwrap(result: Result[T]) -> T | TypedRefusal:
    if isinstance(result, TypedRefusal):
        return result
    return result.value


def _as_refusal(result: object) -> TypedRefusal:
    if isinstance(result, TypedRefusal):
        return result
    return invalid("internal", "expected a typed refusal", given=type(result).__name__)
