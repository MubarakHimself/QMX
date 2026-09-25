"""AD-25 sequential fencing (Stories 59.3–59.4 / SCN-0020 Then 5).

One command owner per ``(account, venue, role)``. Happy path is idle through
retired. UNKNOWN during drain or residual attribution enters ``unknown-blocked``,
a terminal branch of this attempt — it does not continue to ``predecessor-acked``.
Operator reconcile mints a new ``attempt_id`` / epoch with immutable evidence;
automatic retry is refused. Dual writers cannot open a second command owner.
After ``fenced-activate``, a predecessor restart without the current
``(epoch, token)`` is refused; CAS guards refuse mismatched epoch/token.
Software rollback cannot unfill a new-owner fill. Outstanding positions,
UNKNOWN commands, and shared-account concurrency stay separate drain cases.
QMN issues venue tokens; QMB issues internal ATC-simulate tokens. GAP-0100
readiness-dashboard chrome is refused. GAP-0058 stays its own increment.
AD-25 stays the transition machine.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Fingerprint, Ok, Result, TypedRefusal, fingerprint, is_refusal

from qmn.host._refuse import clean_token, invalid, policy, unsupported

__all__ = [
    "FENCING_ACTIVATION",
    "FENCING_AUTO_RETRY",
    "FENCING_COMPOSITION_CLASSES",
    "FENCING_GAP_0058",
    "FENCING_GAP_0100",
    "FENCING_HAPPY_PATH",
    "FENCING_ISSUER_ATC_SIMULATE",
    "FENCING_ISSUER_VENUE",
    "FENCING_OWNER",
    "FENCING_PAYLOAD_FIELDS",
    "FENCING_PROTOCOL",
    "FENCING_RESIDUAL_DISPOSITIONS",
    "FENCING_SEPARATE_DRAIN_CASES",
    "FENCING_STATES",
    "FENCING_SURFACE",
    "FENCING_TERMINAL_BRANCH",
    "FENCING_TOKEN_UNIQUE_UNDER",
    "SOFTWARE_ROLLBACK_CAN_UNFILL",
    "UNKNOWN_BLOCKED_IS_TERMINAL",
    "FenceCasGuard",
    "FenceKey",
    "FenceTimeout",
    "FencingAttempt",
    "FencingRegistry",
    "FencingState",
    "OwnerFill",
    "ResidualDisposition",
    "fencing_machine_identity",
    "record_fencing_payload",
    "refuse_automatic_retry",
    "refuse_gap_0058_single_machine",
    "refuse_gap_0100_readiness_dashboard",
    "refuse_merged_residual_positions",
    "refuse_outstanding_positions",
    "refuse_shared_account_concurrency",
    "refuse_software_unfill",
    "refuse_stale_predecessor_restart",
    "refuse_unknown_commands_drain",
]

FENCING_SURFACE: Final[str] = "qmn.host.fencing"
FENCING_OWNER: Final[str] = "COMP-QMN"
FENCING_PROTOCOL: Final[str] = "AD-25"
FENCING_TERMINAL_BRANCH: Final[str] = "unknown-blocked"
FENCING_ISSUER_VENUE: Final[str] = "COMP-QMN"
FENCING_ISSUER_ATC_SIMULATE: Final[str] = "COMP-QMB"
FENCING_ACTIVATION: Final[str] = "operator-second-act"
FENCING_AUTO_RETRY: Final[bool] = False
FENCING_GAP_0058: Final[bool] = False
FENCING_GAP_0100: Final[bool] = False
SOFTWARE_ROLLBACK_CAN_UNFILL: Final[bool] = False
UNKNOWN_BLOCKED_IS_TERMINAL: Final[bool] = True
FENCING_SEPARATE_DRAIN_CASES: Final[tuple[str, ...]] = (
    "outstanding-positions",
    "unknown-commands",
    "shared-account-concurrency",
)
FENCING_HAPPY_PATH: Final[tuple[str, ...]] = (
    "idle",
    "drain-requested",
    "draining",
    "residuals-attributed",
    "predecessor-acked",
    "fenced-activate",
    "active",
    "retired",
)
FENCING_COMPOSITION_CLASSES: Final[tuple[str, ...]] = ("book-bms", "alternative")
FENCING_RESIDUAL_DISPOSITIONS: Final[tuple[str, ...]] = (
    "flatten",
    "transfer-to-successor",
    "hold-manual",
)
FENCING_TOKEN_UNIQUE_UNDER: Final[tuple[str, ...]] = (
    "account_id",
    "venue_kind",
    "role",
    "command_owner_epoch",
)
FENCING_PAYLOAD_FIELDS: Final[tuple[str, ...]] = (
    "from_composition_fp",
    "to_composition_fp",
    "composition_class",
    "account_id",
    "venue_kind",
    "role",
    "command_owner_epoch",
    "attempt_id",
    "machine_revision",
    "fencing_token",
    "issuer",
    "positions_snapshot",
    "orders_snapshot",
    "residual_disposition",
    "predecessor_ack",
    "timeout",
    "cas_guard",
    "completion_evidence",
)
_CHROME_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "chrome",
        "dashboard",
        "gap_0100",
        "readiness_chrome",
        "readiness_dashboard",
        "ui_dashboard",
        "ui_view",
    }
)
_GAP_0058_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "gap-0058",
        "gap_0058",
        "single_machine",
        "single_machine_placement",
        "single-machine",
        "single-machine-placement",
    }
)
_MERGED_RESIDUAL_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "has_residual_positions",
        "residual_positions",
    }
)
_RECORD_REASON: Final[str] = (
    "deploy payload records from_composition_fp, to_composition_fp, "
    "composition_class, account_id, venue_kind, role, command_owner_epoch, "
    "attempt_id, machine_revision, fencing_token unique under "
    "account/venue/role/epoch, issuer, positions and orders with snapshot_id, "
    "residual_disposition flatten | transfer-to-successor | hold-manual, "
    "predecessor_ack, timeout/escalation, cas_guard, completion_evidence "
    "(FR-WF-71; CONTRACTS §10)"
)
_OWNER_REASON: Final[str] = (
    "one command owner per (account, venue, role); dual writers cannot open a "
    "second command owner (FR-WF-70; SCN-0020 Then 5)"
)
_UNKNOWN_REASON: Final[str] = (
    "unknown-blocked is a terminal branch of this attempt; it does not continue "
    "to predecessor-acked. Operator reconcile mints a new attempt_id / epoch "
    "with immutable evidence — never an automatic retry (FR-WF-70; RC-06; "
    "SCN-0020 Then 5)"
)
_CHROME_REASON: Final[str] = (
    "GAP-0100 readiness dashboard chrome is refused; AD-25 fencing stays the "
    "transition machine (FR-WF-74)"
)
_ISSUER_REASON: Final[str] = (
    "QMN issues venue tokens; QMB issues internal ATC-simulate tokens (FR-WF-71; CONTRACTS §10)"
)
_STALE_REASON: Final[str] = (
    "stale predecessor restart without the current (epoch, token) is refused; "
    "CAS guards refuse mismatched epoch/token (FR-WF-72; RC-06; SCN-0020 Then 5)"
)
_AUTHORITY_REASON: Final[str] = (
    "a stale predecessor restart cannot recover command authority from local state "
    "(FR-WF-72; AD-14; DEC-0438)"
)
_UNFILL_REASON: Final[str] = (
    "software rollback after a new-owner fill cannot unfill (FR-WF-72; AD-14; SCN-0020 Then 5)"
)
_MERGED_REASON: Final[str] = (
    "outstanding positions, UNKNOWN commands, and shared-account concurrency "
    "are separate refusal/drain cases, not a boolean residual_positions string "
    "(FR-WF-72; AD-14)"
)
_GAP_0058_REASON: Final[str] = (
    "GAP-0058 single-machine placement stays its own increment (FR-WF-72; AD-14)"
)
_VENUE_FENCE_CLASS: Final[str] = "venue-fencing-token"


class FencingState(StrEnum):
    """Cheap-veto A2 fencing states. ``unknown-blocked`` is a terminal branch."""

    IDLE = "idle"
    DRAIN_REQUESTED = "drain-requested"
    DRAINING = "draining"
    RESIDUALS_ATTRIBUTED = "residuals-attributed"
    UNKNOWN_BLOCKED = "unknown-blocked"
    PREDECESSOR_ACKED = "predecessor-acked"
    FENCED_ACTIVATE = "fenced-activate"
    ACTIVE = "active"
    RETIRED = "retired"


FENCING_STATES: Final[tuple[str, ...]] = tuple(state.value for state in FencingState)

_HAPPY_NEXT: Final[Mapping[FencingState, FencingState]] = MappingProxyType(
    {
        FencingState.IDLE: FencingState.DRAIN_REQUESTED,
        FencingState.DRAIN_REQUESTED: FencingState.DRAINING,
        FencingState.DRAINING: FencingState.RESIDUALS_ATTRIBUTED,
        FencingState.RESIDUALS_ATTRIBUTED: FencingState.PREDECESSOR_ACKED,
        FencingState.PREDECESSOR_ACKED: FencingState.FENCED_ACTIVATE,
        FencingState.FENCED_ACTIVATE: FencingState.ACTIVE,
        FencingState.ACTIVE: FencingState.RETIRED,
    }
)
_UNKNOWN_FROM: Final[frozenset[FencingState]] = frozenset(
    {FencingState.DRAINING, FencingState.RESIDUALS_ATTRIBUTED}
)


class ResidualDisposition(StrEnum):
    """Closed residual disposition vocabulary (AD-25)."""

    FLATTEN = "flatten"
    TRANSFER_TO_SUCCESSOR = "transfer-to-successor"
    HOLD_MANUAL = "hold-manual"


@dataclass(frozen=True, slots=True)
class FenceKey:
    """Fence key is ``(account, venue, role)`` — one command owner per key."""

    account_id: str
    venue_kind: str | None
    role: str

    def as_tuple(self) -> tuple[str, str, str]:
        """Stable registry key. Absent venue is the empty string."""
        return (self.account_id, self.venue_kind or "", self.role)

    def as_record(self) -> dict[str, object]:
        """Contract fence-key object."""
        return {
            "account_id": self.account_id,
            "role": self.role,
            "venue_kind": self.venue_kind,
        }


@dataclass(frozen=True, slots=True)
class FenceTimeout:
    """Drain deadline plus escalation. Not a retry timer."""

    drain_deadline: str
    escalation: str

    def as_record(self) -> dict[str, object]:
        """Timeout/escalation record."""
        return {
            "drain_deadline": self.drain_deadline,
            "escalation": self.escalation,
        }


@dataclass(frozen=True, slots=True)
class FenceCasGuard:
    """CAS expected epoch/token for this attempt."""

    expected_epoch: int
    expected_token: str

    def as_record(self) -> dict[str, object]:
        """CAS guard record."""
        return {
            "expected_epoch": self.expected_epoch,
            "expected_token": self.expected_token,
        }


@dataclass(frozen=True, slots=True)
class OwnerFill:
    """A fill recorded under the post-``fenced-activate`` command owner."""

    fill_id: str
    fence_key: FenceKey
    command_owner_epoch: int
    fencing_token: str
    composition_fp: Fingerprint
    content: Mapping[str, object]

    def as_record(self) -> dict[str, object]:
        """Immutable fill record. Software rollback cannot unfill it."""
        return {
            "account_id": self.fence_key.account_id,
            "command_owner_epoch": self.command_owner_epoch,
            "composition_fp": self.composition_fp.value,
            "content": dict(self.content),
            "fencing_token": self.fencing_token,
            "fill_id": self.fill_id,
            "role": self.fence_key.role,
            "unfillable": True,
            "venue_kind": self.fence_key.venue_kind,
        }


@dataclass(frozen=True, slots=True)
class FencingAttempt:
    """One sequential fencing attempt. ``unknown-blocked`` does not continue."""

    from_composition_fp: Fingerprint
    to_composition_fp: Fingerprint
    composition_class: str
    account_id: str
    venue_kind: str | None
    role: str
    command_owner_epoch: int
    attempt_id: int
    machine_revision: int
    fencing_token: str
    issuer: str
    state: FencingState
    positions: tuple[Mapping[str, object], ...]
    orders: tuple[Mapping[str, object], ...]
    residual_disposition: ResidualDisposition
    predecessor_ack: bool
    timeout: FenceTimeout
    cas_guard: FenceCasGuard
    completion_evidence: Mapping[str, object] | None
    activation: str
    blocked_evidence: Mapping[str, object] | None = None
    predecessor_attempt_id: int | None = None

    @property
    def fence_key(self) -> FenceKey:
        """``(account, venue, role)`` ownership key."""
        return FenceKey(self.account_id, self.venue_kind, self.role)

    @property
    def unknown_blocked(self) -> bool:
        """True when this attempt took the terminal UNKNOWN branch."""
        return self.state is FencingState.UNKNOWN_BLOCKED

    @property
    def is_terminal(self) -> bool:
        """Retired (happy) or unknown-blocked (branch) ends the attempt."""
        return self.state in {FencingState.UNKNOWN_BLOCKED, FencingState.RETIRED}

    def as_record(self) -> dict[str, object]:
        """Recorded deploy payload. Field names match CONTRACTS §10."""
        body: dict[str, object] = {
            "account_id": self.account_id,
            "activation": self.activation,
            "attempt_id": self.attempt_id,
            "cas_guard": self.cas_guard.as_record(),
            "command_owner_epoch": self.command_owner_epoch,
            "completion_evidence": (
                None if self.completion_evidence is None else dict(self.completion_evidence)
            ),
            "composition_class": self.composition_class,
            "fencing_token": self.fencing_token,
            "from_composition_fp": self.from_composition_fp.value,
            "issuer": self.issuer,
            "machine_revision": self.machine_revision,
            "orders_snapshot": [dict(item) for item in self.orders],
            "positions_snapshot": [dict(item) for item in self.positions],
            "predecessor_ack": self.predecessor_ack,
            "residual_disposition": self.residual_disposition.value,
            "role": self.role,
            "state": self.state.value,
            "timeout": self.timeout.as_record(),
            "to_composition_fp": self.to_composition_fp.value,
            "token_unique_under": list(FENCING_TOKEN_UNIQUE_UNDER),
            "venue_kind": self.venue_kind,
        }
        if self.blocked_evidence is not None:
            body["blocked_evidence"] = dict(self.blocked_evidence)
        if self.predecessor_attempt_id is not None:
            body["predecessor_attempt_id"] = self.predecessor_attempt_id
        return body


@dataclass(frozen=True, slots=True)
class _CommandOwner:
    composition_fp: Fingerprint
    command_owner_epoch: int
    fencing_token: str
    writer: str


def fencing_machine_identity() -> dict[str, object]:
    """Identity-bearing fencing schema. Package SemVer is omitted."""
    return {
        "fencing_auto_retry": FENCING_AUTO_RETRY,
        "fencing_composition_classes": FENCING_COMPOSITION_CLASSES,
        "fencing_gap_0058": FENCING_GAP_0058,
        "fencing_gap_0100": FENCING_GAP_0100,
        "fencing_happy_path": FENCING_HAPPY_PATH,
        "fencing_issuer_atc_simulate": FENCING_ISSUER_ATC_SIMULATE,
        "fencing_issuer_venue": FENCING_ISSUER_VENUE,
        "fencing_owner": FENCING_OWNER,
        "fencing_payload_fields": FENCING_PAYLOAD_FIELDS,
        "fencing_protocol": FENCING_PROTOCOL,
        "fencing_residual_dispositions": FENCING_RESIDUAL_DISPOSITIONS,
        "fencing_separate_drain_cases": FENCING_SEPARATE_DRAIN_CASES,
        "fencing_states": FENCING_STATES,
        "fencing_surface": FENCING_SURFACE,
        "fencing_terminal_branch": FENCING_TERMINAL_BRANCH,
        "fencing_token_unique_under": FENCING_TOKEN_UNIQUE_UNDER,
        "software_rollback_can_unfill": SOFTWARE_ROLLBACK_CAN_UNFILL,
        "unknown_blocked_is_terminal": UNKNOWN_BLOCKED_IS_TERMINAL,
    }


def refuse_gap_0100_readiness_dashboard(
    field: object = "readiness_dashboard",
) -> TypedRefusal:
    """GAP-0100 chrome is not this story. AD-25 stays the transition machine."""
    token = clean_token(field) or "readiness_dashboard"
    return unsupported(token, _CHROME_REASON, gap="GAP-0100")


def refuse_automatic_retry(attempt: object) -> TypedRefusal:
    """Automatic retry of ``unknown-blocked`` is refused."""
    if not isinstance(attempt, FencingAttempt):
        return invalid(
            "attempt",
            "automatic retry is judged against a FencingAttempt",
            given=repr(type(attempt).__name__),
        )
    return policy(
        "unknown-blocked",
        _UNKNOWN_REASON,
        attempt_id=attempt.attempt_id,
        auto_retry=FENCING_AUTO_RETRY,
        command_owner_epoch=attempt.command_owner_epoch,
        state=attempt.state.value,
        terminal=UNKNOWN_BLOCKED_IS_TERMINAL,
    )


def refuse_stale_predecessor_restart(
    *,
    expected_epoch: object,
    expected_token: object,
    presented_epoch: object,
    presented_token: object,
) -> TypedRefusal:
    """CAS mismatch: predecessor restart lacks the current epoch/token."""
    return policy(
        "cas_guard",
        _STALE_REASON,
        expected_epoch=expected_epoch,
        expected_token=expected_token,
        presented_epoch=presented_epoch,
        presented_token=presented_token,
    )


def refuse_software_unfill(fill: object = None) -> TypedRefusal:
    """Software rollback cannot unwind a recorded new-owner fill."""
    extra: dict[str, object] = {
        "software_rollback_can_unfill": SOFTWARE_ROLLBACK_CAN_UNFILL,
        "unfill": False,
    }
    if isinstance(fill, OwnerFill):
        extra["command_owner_epoch"] = fill.command_owner_epoch
        extra["fill_id"] = fill.fill_id
    return policy("software_rollback", _UNFILL_REASON, **extra)


def refuse_merged_residual_positions(field: object = "residual_positions") -> TypedRefusal:
    """Boolean residual marker is not a drain case (AD-14)."""
    token = clean_token(field) or "residual_positions"
    return policy(
        token,
        _MERGED_REASON,
        drain_cases=FENCING_SEPARATE_DRAIN_CASES,
    )


def refuse_outstanding_positions() -> TypedRefusal:
    """Outstanding positions are their own drain case."""
    return policy(
        "outstanding-positions",
        _MERGED_REASON,
        drain_case="outstanding-positions",
        drain_cases=FENCING_SEPARATE_DRAIN_CASES,
    )


def refuse_unknown_commands_drain() -> TypedRefusal:
    """UNKNOWN commands are their own drain case, distinct from positions."""
    return policy(
        "unknown-commands",
        _MERGED_REASON,
        drain_case="unknown-commands",
        drain_cases=FENCING_SEPARATE_DRAIN_CASES,
    )


def refuse_shared_account_concurrency() -> TypedRefusal:
    """Shared-account concurrency is its own drain case, not a residual boolean."""
    return policy(
        "shared-account-concurrency",
        _MERGED_REASON,
        drain_case="shared-account-concurrency",
        drain_cases=FENCING_SEPARATE_DRAIN_CASES,
    )


def refuse_gap_0058_single_machine(
    field: object = "single-machine-placement",
) -> TypedRefusal:
    """GAP-0058 single-machine placement is not this story."""
    token = clean_token(field) or "single-machine-placement"
    return unsupported(token, _GAP_0058_REASON, gap="GAP-0058")


def record_fencing_payload(payload: object) -> Result[FencingAttempt]:
    """Record one deploy payload as an idle attempt. Does not claim the fence."""
    body = _as_fencing_body(payload)
    if is_refusal(body):
        return body
    forbidden = _refuse_payload_forbidden(body.value)
    if forbidden is not None:
        return forbidden
    fps = _bind_payload_fps(body.value)
    if is_refusal(fps):
        return fps
    identity = _bind_payload_identity(body.value)
    if is_refusal(identity):
        return identity
    snapshots = _bind_payload_snapshots(
        body.value, epoch=identity.value[5], token=identity.value[8]
    )
    if is_refusal(snapshots):
        return snapshots
    idle = _bind_idle_start(body.value)
    if is_refusal(idle):
        return idle
    return Ok(
        _mint_idle_attempt(fps.value, identity.value, snapshots.value, idle.value)
    )


class FencingRegistry:
    """One command owner per fence key. In-flight attempts are exclusive."""

    def __init__(self) -> None:
        self._inflight: dict[tuple[str, str, str], FencingAttempt] = {}
        self._owners: dict[tuple[str, str, str], _CommandOwner] = {}
        self._tokens: dict[tuple[str, str, str, int], str] = {}
        self._blocked: dict[tuple[str, str, str], FencingAttempt] = {}
        self._needs_reconcile: set[tuple[str, str, str]] = set()
        self._new_owner: set[tuple[str, str, str]] = set()
        self._fills: dict[tuple[str, str, str], list[OwnerFill]] = {}

    def command_owner(self, key: FenceKey) -> Mapping[str, object] | None:
        """Current command owner for ``key``, or ``None`` before the first owner."""
        owner = self._owners.get(key.as_tuple())
        if owner is None:
            return None
        return MappingProxyType(
            {
                "command_owner_epoch": owner.command_owner_epoch,
                "composition_fp": owner.composition_fp.value,
                "fencing_token": owner.fencing_token,
                "writer": owner.writer,
            }
        )

    def owner_fills(self, key: object) -> tuple[OwnerFill, ...]:
        """Fills recorded under this fence key. Software rollback cannot drop them."""
        parsed = _parse_fence_key(key)
        if is_refusal(parsed):
            return ()
        return tuple(self._fills.get(parsed.value.as_tuple(), ()))

    def start(self, payload: object) -> Result[FencingAttempt]:
        """Record an idle attempt and claim the fence. Dual writers are refused."""
        recorded = record_fencing_payload(payload)
        if is_refusal(recorded):
            return recorded
        return self._claim(recorded.value, predecessor_attempt_id=None)

    def request_drain(self, attempt: object) -> Result[FencingAttempt]:
        """``idle`` → ``drain-requested``."""
        return self._advance(attempt, FencingState.DRAIN_REQUESTED)

    def begin_drain(self, attempt: object) -> Result[FencingAttempt]:
        """``drain-requested`` → ``draining``."""
        return self._advance(attempt, FencingState.DRAINING)

    def attribute_residuals(self, attempt: object) -> Result[FencingAttempt]:
        """``draining`` → ``residuals-attributed``."""
        return self._advance(attempt, FencingState.RESIDUALS_ATTRIBUTED)

    def ack_predecessor(self, attempt: object) -> Result[FencingAttempt]:
        """``residuals-attributed`` → ``predecessor-acked``."""
        return self._advance(attempt, FencingState.PREDECESSOR_ACKED)

    def fenced_activate(self, attempt: object) -> Result[FencingAttempt]:
        """``predecessor-acked`` → ``fenced-activate``. Successor becomes owner."""
        return self._advance(attempt, FencingState.FENCED_ACTIVATE)

    def activate(self, attempt: object) -> Result[FencingAttempt]:
        """``fenced-activate`` → ``active``."""
        return self._advance(attempt, FencingState.ACTIVE)

    def retire(self, attempt: object) -> Result[FencingAttempt]:
        """``active`` → ``retired``. Predecessor is retired; successor stays owner."""
        return self._advance(attempt, FencingState.RETIRED)

    def observe_unknown(
        self,
        attempt: object,
        unknown_orders: object,
    ) -> Result[FencingAttempt]:
        """UNKNOWN during drain/residual attribution enters ``unknown-blocked``."""
        live = self._live(attempt)
        if is_refusal(live):
            return live
        current = live.value
        if current.state is FencingState.UNKNOWN_BLOCKED:
            return refuse_automatic_retry(current)
        if current.state not in _UNKNOWN_FROM:
            return policy(
                "state",
                "UNKNOWN orders block during drain or residual attribution",
                given=current.state.value,
            )
        orders = _parse_unknown_orders(unknown_orders)
        if is_refusal(orders):
            return orders
        evidence: dict[str, object] = {
            "auto_retry": FENCING_AUTO_RETRY,
            "attempt_id": current.attempt_id,
            "branch": FENCING_TERMINAL_BRANCH,
            "command_owner_epoch": current.command_owner_epoch,
            "fencing_token": current.fencing_token,
            "terminal": UNKNOWN_BLOCKED_IS_TERMINAL,
            "unknown_orders": [dict(item) for item in orders.value],
        }
        blocked = replace(
            current,
            state=FencingState.UNKNOWN_BLOCKED,
            predecessor_ack=False,
            completion_evidence=MappingProxyType(dict(evidence)),
            blocked_evidence=MappingProxyType(dict(evidence)),
        )
        key = current.fence_key.as_tuple()
        self._inflight.pop(key, None)
        self._blocked[key] = blocked
        self._needs_reconcile.add(key)
        return Ok(blocked)

    def retry(self, attempt: object) -> Result[FencingAttempt]:
        """Automatic retry cannot open a second command owner."""
        return refuse_automatic_retry(attempt)

    def operator_reconcile(
        self,
        blocked: object,
        *,
        principal: object,
        payload: object,
    ) -> Result[FencingAttempt]:
        """Mint a new attempt/epoch. Never an automatic retry of the blocked one."""
        bound = _bind_reconcile_request(blocked, principal=principal, payload=payload)
        if is_refusal(bound):
            return bound
        blocked_attempt, body = bound.value
        keyed = self._reconcile_stored(blocked_attempt)
        if is_refusal(keyed):
            return keyed
        _seed_reconcile_body(body, blocked_attempt)
        recorded = record_fencing_payload(body)
        if is_refusal(recorded):
            return recorded
        nxt = recorded.value
        key = blocked_attempt.fence_key
        if nxt.fence_key.as_tuple() != key.as_tuple():
            return policy(
                "fence_key",
                "reconcile stays on the same (account, venue, role)",
            )
        self._needs_reconcile.discard(key.as_tuple())
        claimed = self._claim(nxt, predecessor_attempt_id=blocked_attempt.attempt_id)
        if is_refusal(claimed):
            self._needs_reconcile.add(key.as_tuple())
            return claimed
        return Ok(replace(claimed.value, predecessor_attempt_id=blocked_attempt.attempt_id))

    def _reconcile_stored(self, blocked: FencingAttempt) -> Result[None]:
        key = blocked.fence_key
        if key.as_tuple() not in self._needs_reconcile:
            return policy(
                "unknown-blocked",
                "this fence key does not have a terminal unknown-blocked attempt",
            )
        stored = self._blocked.get(key.as_tuple())
        if stored is None or stored.attempt_id != blocked.attempt_id:
            return policy(
                "attempt_id",
                "reconcile cites the immutable blocked attempt",
            )
        if stored.completion_evidence != blocked.completion_evidence:
            return policy(
                "completion_evidence",
                "blocked evidence is immutable; operator reconcile mints a new attempt",
            )
        return Ok(None)

    def restart_predecessor(
        self,
        presented: object,
        *,
        command_owner_epoch: object | None = None,
        fencing_token: object | None = None,
    ) -> Result[Mapping[str, object]]:
        """Refuse a predecessor restart that lacks the current ``(epoch, token)``."""
        parsed = _presented_restart_creds(
            presented,
            command_owner_epoch=command_owner_epoch,
            fencing_token=fencing_token,
        )
        if is_refusal(parsed):
            return parsed
        key, epoch, token = parsed.value
        owner = self._owners.get(key.as_tuple())
        if owner is None:
            return policy(
                "command_owner",
                "no command owner on this fence key",
                fence_key=key.as_record(),
            )
        if epoch != owner.command_owner_epoch or token != owner.fencing_token:
            return refuse_stale_predecessor_restart(
                expected_epoch=owner.command_owner_epoch,
                expected_token=owner.fencing_token,
                presented_epoch=epoch,
                presented_token=token,
            )
        if owner.writer == "successor":
            return policy(
                "stale_predecessor",
                _AUTHORITY_REASON,
                command_owner_epoch=owner.command_owner_epoch,
                writer=owner.writer,
            )
        return Ok(
            MappingProxyType(
                {
                    "command_owner_epoch": owner.command_owner_epoch,
                    "composition_fp": owner.composition_fp.value,
                    "fencing_token": owner.fencing_token,
                    "writer": owner.writer,
                }
            )
        )

    def record_owner_fill(
        self,
        key: object,
        *,
        command_owner_epoch: object,
        fencing_token: object,
        fill: object,
    ) -> Result[OwnerFill]:
        """Record a fill under the current owner after ``fenced-activate``."""
        bound = self._bind_owner_fill(
            key,
            command_owner_epoch=command_owner_epoch,
            fencing_token=fencing_token,
            fill=fill,
        )
        if is_refusal(bound):
            return bound
        fence, owner, body, fill_id = bound.value
        recorded = OwnerFill(
            fill_id=fill_id,
            fence_key=fence,
            command_owner_epoch=owner.command_owner_epoch,
            fencing_token=owner.fencing_token,
            composition_fp=owner.composition_fp,
            content=body,
        )
        held = self._fills.setdefault(fence.as_tuple(), [])
        for existing in held:
            if existing.fill_id != fill_id:
                continue
            if dict(existing.content) != dict(body):
                return policy(
                    "fill_id",
                    _UNFILL_REASON,
                    fill_id=fill_id,
                    unfill=False,
                )
            return Ok(existing)
        held.append(recorded)
        return Ok(recorded)

    def _bind_owner_fill(
        self,
        key: object,
        *,
        command_owner_epoch: object,
        fencing_token: object,
        fill: object,
    ) -> Result[tuple[FenceKey, _CommandOwner, Mapping[str, object], str]]:
        parsed_key = _parse_fence_key(key)
        if is_refusal(parsed_key):
            return parsed_key
        fence = parsed_key.value
        tuple_key = fence.as_tuple()
        if tuple_key not in self._new_owner:
            return policy(
                "state",
                "new-owner fills are recorded after fenced-activate",
            )
        owner = self._owners.get(tuple_key)
        if owner is None:
            return policy(
                "command_owner",
                "no command owner on this fence key",
                fence_key=fence.as_record(),
            )
        epoch = _positive_int(command_owner_epoch, "command_owner_epoch")
        if is_refusal(epoch):
            return epoch
        token = clean_token(fencing_token)
        if token is None:
            return invalid("fencing_token", _STALE_REASON, given=repr(fencing_token))
        if epoch.value != owner.command_owner_epoch or token != owner.fencing_token:
            return refuse_stale_predecessor_restart(
                expected_epoch=owner.command_owner_epoch,
                expected_token=owner.fencing_token,
                presented_epoch=epoch.value,
                presented_token=token,
            )
        parsed_fill = _parse_fill(fill)
        if is_refusal(parsed_fill):
            return parsed_fill
        fill_id = clean_token(parsed_fill.value.get("fill_id"))
        if fill_id is None:
            return invalid("fill_id", "a new-owner fill carries fill_id")
        return Ok((fence, owner, parsed_fill.value, fill_id))

    def software_rollback(
        self,
        key: object,
        *,
        fill_id: object = None,
    ) -> Result[OwnerFill]:
        """Refuse to unwind fills. Recorded fills stay."""
        parsed_key = _parse_fence_key(key)
        if is_refusal(parsed_key):
            return parsed_key
        fills = self._fills.get(parsed_key.value.as_tuple(), [])
        if fill_id is not None:
            token = clean_token(fill_id)
            if token is None:
                return invalid("fill_id", "software rollback names a fill_id", given=repr(fill_id))
            match = [item for item in fills if item.fill_id == token]
            if not match:
                return invalid(
                    "fill_id",
                    "no such new-owner fill",
                    given=token,
                    remaining=len(fills),
                    unfill=False,
                )
            return refuse_software_unfill(match[0])
        if fills:
            return refuse_software_unfill(fills[-1])
        return policy(
            "software_rollback",
            _UNFILL_REASON,
            remaining=0,
            software_rollback_can_unfill=SOFTWARE_ROLLBACK_CAN_UNFILL,
            unfill=False,
        )

    def _claim(
        self,
        attempt: FencingAttempt,
        *,
        predecessor_attempt_id: int | None,
    ) -> Result[FencingAttempt]:
        key = attempt.fence_key.as_tuple()
        if key in self._needs_reconcile:
            return policy("unknown-blocked", _UNKNOWN_REASON, auto_retry=FENCING_AUTO_RETRY)
        if key in self._inflight:
            return policy("command_owner", _OWNER_REASON, fence_key=attempt.fence_key.as_record())
        owner = self._owners.get(key)
        if owner is not None and owner.writer == "successor":
            return policy("command_owner", _OWNER_REASON, writer=owner.writer)
        token_key = (
            attempt.account_id,
            attempt.venue_kind or "",
            attempt.role,
            attempt.command_owner_epoch,
        )
        existing_token = self._tokens.get(token_key)
        if existing_token is not None and existing_token != attempt.fencing_token:
            return policy(
                "fencing_token",
                "fencing_token is unique under account/venue/role/epoch",
                token_unique_under=list(FENCING_TOKEN_UNIQUE_UNDER),
            )
        if existing_token is None:
            for held_key, held_token in self._tokens.items():
                if held_token == attempt.fencing_token and held_key != token_key:
                    return policy(
                        "fencing_token",
                        "fencing_token is unique under account/venue/role/epoch",
                        token_unique_under=list(FENCING_TOKEN_UNIQUE_UNDER),
                    )
            self._tokens[token_key] = attempt.fencing_token
        self._new_owner.discard(key)
        claimed = replace(attempt, predecessor_attempt_id=predecessor_attempt_id)
        self._inflight[key] = claimed
        if owner is None:
            self._owners[key] = _CommandOwner(
                composition_fp=claimed.from_composition_fp,
                command_owner_epoch=claimed.command_owner_epoch,
                fencing_token=claimed.fencing_token,
                writer="predecessor",
            )
        return Ok(claimed)

    def _live(self, attempt: object) -> Result[FencingAttempt]:
        if not isinstance(attempt, FencingAttempt):
            return invalid(
                "attempt",
                "transitions run on a FencingAttempt",
                given=repr(type(attempt).__name__),
            )
        key = attempt.fence_key.as_tuple()
        if attempt.state is FencingState.UNKNOWN_BLOCKED:
            stored = self._blocked.get(key)
            if stored is None or stored.attempt_id != attempt.attempt_id:
                return policy("unknown-blocked", _UNKNOWN_REASON)
            return Ok(stored)
        live = self._inflight.get(key)
        if live is None:
            return policy("attempt_id", "no in-flight fencing attempt on this fence key")
        if live.attempt_id != attempt.attempt_id:
            return policy("attempt_id", _OWNER_REASON, live_attempt_id=live.attempt_id)
        if (
            live.command_owner_epoch != attempt.command_owner_epoch
            or live.fencing_token != attempt.fencing_token
        ):
            return policy(
                "cas_guard",
                "CAS guards refuse mismatched epoch/token",
                expected_epoch=live.command_owner_epoch,
                expected_token=live.fencing_token,
            )
        if live.state is not attempt.state:
            return policy("state", "stale fencing attempt", live_state=live.state.value)
        return Ok(live)

    def _advance(self, attempt: object, target: FencingState) -> Result[FencingAttempt]:
        live = self._live(attempt)
        if is_refusal(live):
            return live
        current = live.value
        if current.state is FencingState.UNKNOWN_BLOCKED:
            return policy("unknown-blocked", _UNKNOWN_REASON, terminal=True)
        expected = _HAPPY_NEXT.get(current.state)
        if expected is not target:
            return policy(
                "state",
                "AD-25 fencing stays the transition machine",
                from_state=current.state.value,
                to_state=target.value,
            )
        nxt = _next_fencing_state(current, target)
        self._commit_advance(current, nxt, target)
        return Ok(nxt)

    def _commit_advance(
        self, current: FencingAttempt, nxt: FencingAttempt, target: FencingState
    ) -> None:
        key = current.fence_key.as_tuple()
        if target is FencingState.FENCED_ACTIVATE:
            self._owners[key] = _CommandOwner(
                composition_fp=nxt.to_composition_fp,
                command_owner_epoch=nxt.command_owner_epoch,
                fencing_token=nxt.fencing_token,
                writer="successor",
            )
            self._new_owner.add(key)
        if target is FencingState.RETIRED:
            self._inflight.pop(key, None)
            owner = self._owners.get(key)
            if owner is not None:
                self._owners[key] = _CommandOwner(
                    composition_fp=nxt.to_composition_fp,
                    command_owner_epoch=nxt.command_owner_epoch,
                    fencing_token=nxt.fencing_token,
                    writer="predecessor",
                )
            return
        self._inflight[key] = nxt


def _next_fencing_state(current: FencingAttempt, target: FencingState) -> FencingAttempt:
    nxt = replace(
        current,
        state=target,
        predecessor_ack=target
        in {
            FencingState.PREDECESSOR_ACKED,
            FencingState.FENCED_ACTIVATE,
            FencingState.ACTIVE,
            FencingState.RETIRED,
        },
    )
    if target is not FencingState.RETIRED:
        return nxt
    return replace(
        nxt,
        completion_evidence=MappingProxyType(
            {
                "attempt_id": nxt.attempt_id,
                "branch": "happy-path",
                "command_owner_epoch": nxt.command_owner_epoch,
                "state": FencingState.RETIRED.value,
                "terminal": True,
            }
        ),
    )


def _presented_restart_creds(
    presented: object,
    *,
    command_owner_epoch: object | None,
    fencing_token: object | None,
) -> Result[tuple[FenceKey, int, str]]:
    if isinstance(presented, FencingAttempt):
        key = presented.fence_key
        epoch_raw: object = (
            presented.command_owner_epoch
            if command_owner_epoch is None
            else command_owner_epoch
        )
        token_raw: object = presented.fencing_token if fencing_token is None else fencing_token
    else:
        parsed_key = _parse_fence_key(presented)
        if is_refusal(parsed_key):
            return parsed_key
        key = parsed_key.value
        epoch_raw = command_owner_epoch
        token_raw = fencing_token
    epoch = _positive_int(epoch_raw, "command_owner_epoch")
    if is_refusal(epoch):
        return epoch
    token = clean_token(token_raw)
    if token is None:
        return invalid(
            "fencing_token",
            _STALE_REASON,
            given=repr(token_raw),
        )
    return Ok((key, epoch.value, token))


def _bind_reconcile_request(
    blocked: object,
    *,
    principal: object,
    payload: object,
) -> Result[tuple[FencingAttempt, dict[str, object]]]:
    if not isinstance(blocked, FencingAttempt) or not blocked.unknown_blocked:
        return policy(
            "unknown-blocked",
            "operator reconcile starts from a terminal unknown-blocked attempt",
            given=repr(getattr(blocked, "state", type(blocked).__name__)),
        )
    if clean_token(principal) != "operator":
        return policy(
            "principal",
            "operator reconcile mints a new attempt_id / epoch",
            required_principal="operator",
            given=repr(principal),
        )
    if not isinstance(payload, Mapping):
        return invalid(
            "payload",
            "reconcile records a new deploy payload",
            given=repr(type(payload).__name__),
        )
    body = dict(cast("Mapping[str, object]", payload))
    new_attempt_id = _positive_int(body.get("attempt_id"), "attempt_id")
    if is_refusal(new_attempt_id):
        return new_attempt_id
    new_epoch = _positive_int(body.get("command_owner_epoch"), "command_owner_epoch")
    if is_refusal(new_epoch):
        return new_epoch
    if new_attempt_id.value == blocked.attempt_id:
        return policy(
            "attempt_id",
            _UNKNOWN_REASON,
            blocked_attempt_id=blocked.attempt_id,
        )
    if new_epoch.value == blocked.command_owner_epoch:
        return policy(
            "command_owner_epoch",
            _UNKNOWN_REASON,
            blocked_epoch=blocked.command_owner_epoch,
        )
    return Ok((blocked, body))


def _seed_reconcile_body(body: dict[str, object], blocked: FencingAttempt) -> None:
    body.setdefault("account_id", blocked.account_id)
    body.setdefault("role", blocked.role)
    body.setdefault("composition_class", blocked.composition_class)
    body.setdefault("from_composition_fp", blocked.from_composition_fp.value)
    body.setdefault("to_composition_fp", blocked.to_composition_fp.value)
    body.setdefault("issuer", blocked.issuer)
    if "venue_kind" not in body:
        body["venue_kind"] = blocked.venue_kind


def _mint_idle_attempt(
    fps: tuple[Fingerprint, Fingerprint],
    identity: tuple[str, str, str, str | None, str, int, int, int, str],
    snapshots: tuple[
        tuple[Mapping[str, object], ...],
        tuple[Mapping[str, object], ...],
        FenceTimeout,
        FenceCasGuard,
        str,
    ],
    activation: str,
) -> FencingAttempt:
    from_fp, to_fp = fps
    composition_class, account_id, role, venue_kind, issuer, epoch, attempt_id, revision, token = (
        identity
    )
    positions, orders, timeout, cas, disposition = snapshots
    return FencingAttempt(
        from_composition_fp=from_fp,
        to_composition_fp=to_fp,
        composition_class=composition_class,
        account_id=account_id,
        venue_kind=venue_kind,
        role=role,
        command_owner_epoch=epoch,
        attempt_id=attempt_id,
        machine_revision=revision,
        fencing_token=token,
        issuer=issuer,
        state=FencingState.IDLE,
        positions=positions,
        orders=orders,
        residual_disposition=ResidualDisposition(disposition),
        predecessor_ack=False,
        timeout=timeout,
        cas_guard=cas,
        completion_evidence=None,
        activation=activation,
    )


def _as_fencing_body(payload: object) -> Result[Mapping[str, object]]:
    if not isinstance(payload, Mapping):
        return invalid(
            "payload",
            "a fencing deploy payload is a key->value mapping",
            given=repr(type(payload).__name__),
        )
    return Ok(cast("Mapping[str, object]", payload))


def _refuse_payload_forbidden(
    body: Mapping[str, object],
) -> Result[FencingAttempt] | None:
    chrome = _refuse_chrome(body)
    if chrome is not None:
        return chrome
    gap_0058 = _refuse_gap_0058(body)
    if gap_0058 is not None:
        return gap_0058
    return _refuse_merged_residual(body)


def _bind_payload_fps(
    body: Mapping[str, object],
) -> Result[tuple[Fingerprint, Fingerprint]]:
    from_fp = _parse_fp(body.get("from_composition_fp"), "from_composition_fp")
    if is_refusal(from_fp):
        return from_fp
    to_fp = _parse_fp(body.get("to_composition_fp"), "to_composition_fp")
    if is_refusal(to_fp):
        return to_fp
    if from_fp.value.value == to_fp.value.value:
        return invalid(
            "to_composition_fp",
            "handover replaces a live composition with a different composition_fp",
        )
    return Ok((from_fp.value, to_fp.value))


def _bind_payload_identity(
    body: Mapping[str, object],
) -> Result[tuple[str, str, str, str | None, str, int, int, int, str]]:
    composition_class = clean_token(body.get("composition_class"))
    if composition_class is None or composition_class not in FENCING_COMPOSITION_CLASSES:
        return invalid(
            "composition_class",
            _RECORD_REASON,
            given=repr(body.get("composition_class")),
        )
    account_id = clean_token(body.get("account_id"))
    if account_id is None:
        return invalid("account_id", _RECORD_REASON)
    role = clean_token(body.get("role"))
    if role is None:
        return invalid("role", _RECORD_REASON)
    venue_kind = _optional_token(body.get("venue_kind"), "venue_kind")
    if is_refusal(venue_kind):
        return venue_kind
    numbers = _bind_payload_numbers(body)
    if is_refusal(numbers):
        return numbers
    epoch, attempt_id, revision = numbers.value
    issuer = clean_token(body.get("issuer"))
    if issuer is None:
        return invalid("issuer", _ISSUER_REASON)
    issued = _issue_token(
        issuer=issuer,
        composition_class=composition_class,
        account_id=account_id,
        venue_kind=venue_kind.value,
        role=role,
        command_owner_epoch=epoch,
        supplied=body.get("fencing_token"),
    )
    if is_refusal(issued):
        return issued
    return Ok(
        (
            composition_class,
            account_id,
            role,
            venue_kind.value,
            issuer,
            epoch,
            attempt_id,
            revision,
            issued.value,
        )
    )


def _bind_payload_numbers(body: Mapping[str, object]) -> Result[tuple[int, int, int]]:
    epoch = _positive_int(body.get("command_owner_epoch"), "command_owner_epoch")
    if is_refusal(epoch):
        return epoch
    attempt_id = _positive_int(body.get("attempt_id"), "attempt_id")
    if is_refusal(attempt_id):
        return attempt_id
    revision = _positive_int(body.get("machine_revision"), "machine_revision")
    if is_refusal(revision):
        return revision
    return Ok((epoch.value, attempt_id.value, revision.value))


def _bind_payload_snapshots(
    body: Mapping[str, object],
    *,
    epoch: int,
    token: str,
) -> Result[
    tuple[
        tuple[Mapping[str, object], ...],
        tuple[Mapping[str, object], ...],
        FenceTimeout,
        FenceCasGuard,
        str,
    ]
]:
    disposition_token = clean_token(body.get("residual_disposition"))
    if disposition_token is None or disposition_token not in FENCING_RESIDUAL_DISPOSITIONS:
        return invalid(
            "residual_disposition",
            _RECORD_REASON,
            given=repr(body.get("residual_disposition")),
        )
    positions = _parse_records(body.get("positions_snapshot"), "positions_snapshot")
    if is_refusal(positions):
        return positions
    orders = _parse_records(body.get("orders_snapshot"), "orders_snapshot")
    if is_refusal(orders):
        return orders
    timeout = _parse_timeout(body.get("timeout"))
    if is_refusal(timeout):
        return timeout
    cas = _parse_cas(body.get("cas_guard"), epoch, token)
    if is_refusal(cas):
        return cas
    return Ok(
        (positions.value, orders.value, timeout.value, cas.value, disposition_token)
    )


def _bind_idle_start(body: Mapping[str, object]) -> Result[str]:
    ack = body.get("predecessor_ack", False)
    if not isinstance(ack, bool):
        return invalid(
            "predecessor_ack",
            "predecessor_ack is a boolean",
            given=repr(ack),
        )
    if ack:
        return invalid(
            "predecessor_ack",
            "idle attempts start with predecessor_ack false",
        )
    evidence = _parse_optional_mapping(body.get("completion_evidence"), "completion_evidence")
    if is_refusal(evidence):
        return evidence
    if evidence.value is not None:
        return invalid(
            "completion_evidence",
            "idle attempts start with completion_evidence null",
        )
    activation = body.get("activation", FENCING_ACTIVATION)
    activation_token = clean_token(activation)
    if activation_token != FENCING_ACTIVATION:
        return invalid(
            "activation",
            "activation is operator-second-act (DEC-0213)",
            given=repr(activation),
        )
    state_token = body.get("state", FencingState.IDLE.value)
    if state_token != FencingState.IDLE.value:
        return policy(
            "state",
            "recorded deploy payload starts idle; AD-25 is the transition machine",
            given=repr(state_token),
        )
    return Ok(activation_token)


def _refuse_chrome(body: Mapping[str, object]) -> Result[FencingAttempt] | None:
    for field in body:
        if field in _CHROME_FIELDS or field.lower() == "gap-0100":
            return unsupported(field, _CHROME_REASON, gap="GAP-0100")
    return None


def _refuse_gap_0058(body: Mapping[str, object]) -> Result[FencingAttempt] | None:
    for field in body:
        normalized = field.lower().replace("_", "-")
        if field in _GAP_0058_FIELDS or normalized in _GAP_0058_FIELDS:
            return refuse_gap_0058_single_machine(field)
    return None


def _refuse_merged_residual(body: Mapping[str, object]) -> Result[FencingAttempt] | None:
    for field in body:
        if field in _MERGED_RESIDUAL_FIELDS:
            return refuse_merged_residual_positions(field)
    return None


def _parse_fence_key(raw: object) -> Result[FenceKey]:
    if isinstance(raw, FenceKey):
        return Ok(raw)
    if isinstance(raw, FencingAttempt):
        return Ok(raw.fence_key)
    if not isinstance(raw, Mapping):
        return invalid(
            "fence_key",
            "fence key is (account, venue, role)",
            given=repr(type(raw).__name__),
        )
    body = cast("Mapping[str, object]", raw)
    account_id = clean_token(body.get("account_id"))
    role = clean_token(body.get("role"))
    if account_id is None or role is None:
        return invalid("fence_key", "fence key is (account, venue, role)")
    venue_kind = _optional_token(body.get("venue_kind"), "venue_kind")
    if is_refusal(venue_kind):
        return venue_kind
    return Ok(FenceKey(account_id, venue_kind.value, role))


def _parse_fill(raw: object) -> Result[Mapping[str, object]]:
    if not isinstance(raw, Mapping):
        return invalid(
            "fill",
            "a new-owner fill is a key->value mapping",
            given=repr(type(raw).__name__),
        )
    body = dict(cast("Mapping[str, object]", raw))
    if clean_token(body.get("fill_id")) is None:
        return invalid("fill_id", "a new-owner fill carries fill_id")
    return Ok(MappingProxyType(body))


def _parse_fp(raw: object, field: str) -> Result[Fingerprint]:
    if isinstance(raw, Fingerprint):
        return Ok(raw)
    if not isinstance(raw, str):
        return invalid(field, _RECORD_REASON, given=repr(raw))
    parsed = Fingerprint.try_create(raw)
    if is_refusal(parsed):
        return invalid(field, _RECORD_REASON, given=repr(raw))
    return parsed


def _optional_token(raw: object, field: str) -> Result[str | None]:
    if raw is None:
        return Ok(None)
    token = clean_token(raw)
    if token is None:
        return invalid(field, _RECORD_REASON, given=repr(raw))
    return Ok(token)


def _positive_int(raw: object, field: str) -> Result[int]:
    if isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
        return invalid(field, _RECORD_REASON, given=repr(raw))
    return Ok(raw)


def _parse_timeout(raw: object) -> Result[FenceTimeout]:
    if not isinstance(raw, Mapping):
        return invalid("timeout", _RECORD_REASON, given=repr(type(raw).__name__))
    body = cast("Mapping[str, object]", raw)
    deadline = clean_token(body.get("drain_deadline"))
    escalation = clean_token(body.get("escalation"))
    if deadline is None or escalation is None:
        return invalid("timeout", _RECORD_REASON)
    return Ok(FenceTimeout(drain_deadline=deadline, escalation=escalation))


def _parse_cas(raw: object, epoch: int, token: str) -> Result[FenceCasGuard]:
    if raw is None:
        return Ok(FenceCasGuard(expected_epoch=epoch, expected_token=token))
    if not isinstance(raw, Mapping):
        return invalid("cas_guard", _RECORD_REASON, given=repr(type(raw).__name__))
    body = cast("Mapping[str, object]", raw)
    expected_epoch = _positive_int(body.get("expected_epoch"), "cas_guard")
    if is_refusal(expected_epoch):
        return expected_epoch
    expected_token = clean_token(body.get("expected_token"))
    if expected_token is None:
        return invalid("cas_guard", _RECORD_REASON)
    if expected_epoch.value != epoch or expected_token != token:
        return policy(
            "cas_guard",
            "CAS guards refuse mismatched epoch/token",
            expected_epoch=epoch,
            expected_token=token,
        )
    return Ok(FenceCasGuard(expected_epoch=expected_epoch.value, expected_token=expected_token))


def _parse_optional_mapping(raw: object, field: str) -> Result[Mapping[str, object] | None]:
    if raw is None:
        return Ok(None)
    if not isinstance(raw, Mapping):
        return invalid(field, _RECORD_REASON, given=repr(type(raw).__name__))
    return Ok(MappingProxyType(dict(cast("Mapping[str, object]", raw))))


def _parse_records(raw: object, field: str) -> Result[tuple[Mapping[str, object], ...]]:
    if raw is None:
        return Ok(())
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return invalid(field, _RECORD_REASON, given=repr(type(raw).__name__))
    items: list[Mapping[str, object]] = []
    for index, item in enumerate(cast("Sequence[object]", raw)):
        if not isinstance(item, Mapping):
            return invalid(field, _RECORD_REASON, index=index)
        body = dict(cast("Mapping[str, object]", item))
        if clean_token(body.get("snapshot_id")) is None:
            return invalid(
                field,
                "positions and orders records carry snapshot_id (FR-WF-71)",
                index=index,
            )
        items.append(MappingProxyType(body))
    return Ok(tuple(items))


def _parse_unknown_orders(raw: object) -> Result[tuple[Mapping[str, object], ...]]:
    parsed = _parse_records(raw, "unknown_orders")
    if is_refusal(parsed):
        return parsed
    if not parsed.value:
        return invalid(
            "unknown_orders",
            "UNKNOWN orders during drain/residual attribution are a non-empty record",
        )
    return parsed


def _issue_token(
    *,
    issuer: str,
    composition_class: str,
    account_id: str,
    venue_kind: str | None,
    role: str,
    command_owner_epoch: int,
    supplied: object,
) -> Result[str]:
    if issuer == FENCING_ISSUER_ATC_SIMULATE:
        if venue_kind is not None:
            return invalid("venue_kind", _ISSUER_REASON, issuer=issuer)
        token = _supplied_token(supplied)
        if is_refusal(token):
            return token
        return Ok(token.value)
    if issuer != FENCING_ISSUER_VENUE:
        return invalid("issuer", _ISSUER_REASON, given=issuer)
    if venue_kind is None:
        return invalid("venue_kind", _ISSUER_REASON, issuer=issuer)
    if supplied is not None:
        token = _supplied_token(supplied)
        if is_refusal(token):
            return token
        return Ok(token.value)
    minted = fingerprint(
        {
            "account_id": account_id,
            "class": _VENUE_FENCE_CLASS,
            "command_owner_epoch": command_owner_epoch,
            "composition_class": composition_class,
            "issuer": issuer,
            "role": role,
            "venue_kind": venue_kind,
        }
    )
    if is_refusal(minted):
        return minted
    return Ok(minted.value.value)


def _supplied_token(raw: object) -> Result[str]:
    if isinstance(raw, Fingerprint):
        return Ok(raw.value)
    token = clean_token(raw)
    if token is None:
        return invalid("fencing_token", _ISSUER_REASON, given=repr(raw))
    parsed = Fingerprint.try_create(token)
    if is_refusal(parsed):
        return parsed
    return Ok(parsed.value.value)
