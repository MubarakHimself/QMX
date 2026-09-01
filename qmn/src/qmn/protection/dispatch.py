"""Evidence-first protection dispatcher — one arbitration point per stream (Story 26.2).

AD-37 / TN-6 / TN-7 / SCN-0010 / FR-057 / NFR-12/15:

* Exactly one dispatcher per ``(VenueId, account)`` command stream.
* Arbitration reads the BMS-declared total unique AD-37 rank table — never
  arrival order. Collapse only identical mechanical commands; composing acts
  both execute; a lower rank never undoes or weakens a higher one.
* Venue-resident Tier-1 protection sits outside this ordering by construction.
* Under a dead/UNKNOWN wire, ``suspend_new`` / ``drain`` stay ``never-auto``;
  ``flatten`` requires ``scope-flat-at-reconciled-verdict``; a command outcome
  alone satisfies nothing; ``drift | unknown | out-of-lookback`` holds the
  intent open and alarms.
* Evidence-first: journal the standing intent before dispatch; on journal
  refusal write the reserved protection-intent extent; failure of both is
  ``UNDELIVERABLE`` and alarmed. Re-decide, never blind-retry.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableSequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final, cast

from qmf.core import (
    Fingerprint,
    Ok,
    Result,
    SinkAck,
    SinkResult,
    TypedRefusal,
    VenueId,
    is_ok,
    is_refusal,
    unpersistable,
)
from qmf.risk.control_action import (
    NEVER_AUTO_KINDS,
    ArbitrationOutcome,
    CommandStreamKey,
    ControlActionRecord,
    EnforcementScope,
    PendingControlAction,
    ReconciliationVerdict,
    SatisfactionPredicate,
    StandingIntentFold,
    StandingIntentStatus,
    arbitrate_same_tick,
    evaluate_satisfaction,
    journal_before_dispatch,
    reevaluate_standing_intent,
)
from qmf.risk.control_rank import (
    ControlActionKind,
    ControlRankTable,
    check_control_rank_uniqueness,
)

from qmn.protection._refuse import invalid, policy

__all__ = [
    "DISPATCHER_SURFACE",
    "RANKED_CONTROL_KINDS",
    "UNDELIVERABLE_ALARM_CLASS",
    "CandidateOrigin",
    "DeadWireSatisfaction",
    "DispatchCandidate",
    "DispatchPlan",
    "IntentPersistDisposition",
    "PersistedProtectiveIntent",
    "ProtectionIntentExtent",
    "StreamProtectionDispatcher",
    "UndeliverableProtectiveIntent",
    "check_dead_wire_satisfaction",
    "command_outcome_never_satisfies",
    "dispatch_ranked_controls",
    "exclude_venue_resident_tier1",
    "persist_protective_intent",
    "redecide_protective_intent",
    "require_total_unique_rank_table",
    "stream_dispatcher_key",
]

DISPATCHER_SURFACE: Final[str] = "qmn.protection.dispatch"
UNDELIVERABLE_ALARM_CLASS: Final[str] = "silent-degradation"

# Every CT-30 kind the BMS rank table must cover — total unique (DEC-0151).
RANKED_CONTROL_KINDS: Final[frozenset[ControlActionKind]] = frozenset(ControlActionKind)


class CandidateOrigin(StrEnum):
    """Where a pending act entered the dispatcher (SCN-0010 / TN-6)."""

    CT30 = "ct30"
    RISK_NON_INCREASING = "risk-non-increasing"
    VENUE_RESIDENT_TIER1 = "venue-resident-tier1"


class IntentPersistDisposition(StrEnum):
    """Fate of evidence-first standing-intent persistence (TN-4 / TN-7)."""

    JOURNALED = "journaled"
    EXTENT = "extent"
    UNDELIVERABLE = "undeliverable"


@dataclass(frozen=True, slots=True)
class DispatchCandidate:
    """One pending control or risk-non-increasing act at the stream arbiter.

    Venue-resident Tier-1 candidates carry ``origin =
    venue-resident-tier1`` and are excluded from rank ordering — they fire
    when they fire; the node assumes nothing (DEC-0151).
    """

    record: ControlActionRecord
    enforcement: EnforcementScope
    origin: CandidateOrigin
    mechanical_command: ControlActionKind
    arrival_ordinal: int = 0

    @classmethod
    def try_create(
        cls,
        record: object,
        enforcement: object,
        *,
        origin: object = CandidateOrigin.CT30,
        mechanical_command: object = None,
        arrival_ordinal: object = 0,
    ) -> Result[DispatchCandidate]:
        if not isinstance(record, ControlActionRecord):
            return invalid(
                "record",
                "a dispatch candidate carries a journaled ControlActionRecord",
                given=repr(record),
            )
        if not isinstance(enforcement, EnforcementScope):
            return invalid(
                "enforcement",
                "a dispatch candidate carries its resolved EnforcementScope",
                given=repr(enforcement),
            )
        if enforcement.stream != record.stream:
            return invalid(
                "enforcement",
                "enforcement scope must share the candidate's command stream — "
                "cross-stream ordering is a declared non-guarantee",
            )
        resolved_origin: CandidateOrigin | None
        if isinstance(origin, CandidateOrigin):
            resolved_origin = origin
        elif isinstance(origin, str):
            try:
                resolved_origin = CandidateOrigin(origin)
            except ValueError:
                resolved_origin = None
        else:
            resolved_origin = None
        if resolved_origin is None:
            return invalid(
                "origin",
                "candidate origin is ct30 | risk-non-increasing | venue-resident-tier1",
                given=repr(origin),
            )
        command = (
            record.action_kind
            if mechanical_command is None
            else (mechanical_command if isinstance(mechanical_command, ControlActionKind) else None)
        )
        if command is None and isinstance(mechanical_command, str):
            try:
                command = ControlActionKind(mechanical_command)
            except ValueError:
                command = None
        if command is None:
            return invalid(
                "mechanical_command",
                "the mechanical command is a ControlActionKind",
                given=repr(mechanical_command),
            )
        if (
            isinstance(arrival_ordinal, bool)
            or not isinstance(arrival_ordinal, int)
            or arrival_ordinal < 0
        ):
            return invalid(
                "arrival_ordinal",
                "arrival_ordinal is a non-negative int recorded for evidence only — "
                "arbitration never reads it",
                given=repr(arrival_ordinal),
            )
        return Ok(
            cls(
                record=record,
                enforcement=enforcement,
                origin=resolved_origin,
                mechanical_command=command,
                arrival_ordinal=arrival_ordinal,
            )
        )


@dataclass(frozen=True, slots=True)
class DispatchPlan:
    """Outcome of one stream evaluation — emit, suppress, Tier-1 outside."""

    stream: CommandStreamKey
    arbitration: ArbitrationOutcome | None
    emit: tuple[PendingControlAction, ...]
    suppressed: tuple[object, ...]
    venue_resident_outside: tuple[DispatchCandidate, ...]
    arrival_order_ignored: bool


@dataclass(frozen=True, slots=True)
class DeadWireSatisfaction:
    """Satisfaction check under a dead/UNKNOWN wire (TN-7)."""

    record: ControlActionRecord
    status: StandingIntentStatus
    predicate: SatisfactionPredicate
    verdict: ReconciliationVerdict
    command_outcome_satisfies: bool
    alarm: bool
    detail: str


@dataclass(frozen=True, slots=True)
class UndeliverableProtectiveIntent:
    """Honest terminal when journal and reserved extent both refuse (TN-4)."""

    record_fingerprint: Fingerprint
    stream: CommandStreamKey
    action_kind: ControlActionKind
    alarm_class: str
    detail: str


@dataclass(frozen=True, slots=True)
class PersistedProtectiveIntent:
    """Standing protective intent persisted before dispatch consideration."""

    record: ControlActionRecord
    record_fingerprint: Fingerprint
    disposition: IntentPersistDisposition
    undeliverable: UndeliverableProtectiveIntent | None
    detail: str


@dataclass
class ProtectionIntentExtent:
    """Reserved protection-intent extent for CT-30 standing intents (TN-4).

    Used when the normal journal sink refuses. Capacity is a declared bound;
    exhaustion surfaces as a storage failure so the dispatcher can mint
    ``UNDELIVERABLE``.
    """

    capacity: int
    _records: list[Mapping[str, object]] = field(default_factory=list[Mapping[str, object]])

    @classmethod
    def try_create(cls, capacity: object) -> Result[ProtectionIntentExtent]:
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity <= 0:
            return invalid(
                "capacity",
                "reserved protection-intent extent capacity is a positive int",
                given=repr(capacity),
            )
        return Ok(cls(capacity=capacity))

    @property
    def used(self) -> int:
        return len(self._records)

    @property
    def remaining(self) -> int:
        return self.capacity - len(self._records)

    @property
    def records(self) -> tuple[Mapping[str, object], ...]:
        return tuple(self._records)

    def write(self, record: object, /) -> SinkResult:
        if not isinstance(record, Mapping):
            return invalid(
                "record",
                "protection-intent extent stores a mapping record",
                given=type(record).__name__,
            )
        if len(self._records) >= self.capacity:
            return unpersistable(
                "reserved protection-intent extent is full; standing intent cannot be persisted"
            )
        self._records.append(dict(cast("Mapping[str, object]", record)))
        return Ok(SinkAck())


def stream_dispatcher_key(venue_id: object, account_id: object) -> Result[CommandStreamKey]:
    """Build the one-arbitration-point stream key for a dispatcher."""
    return CommandStreamKey.try_create(venue_id, account_id)


def require_total_unique_rank_table(rank_table: object) -> Result[ControlRankTable]:
    """Refuse a non-total or non-unique BMS rank table (AD-37; DEC-0151).

    Every ranked CT-30 kind must appear exactly once; two kinds sharing a rank
    is ``invalid input``. No QMF default fills a missing kind.
    """
    if not isinstance(rank_table, ControlRankTable):
        return invalid(
            "rank_table",
            "the dispatcher reads the BMS-declared ControlRankTable for this stream",
            given=repr(rank_table),
        )
    uniqueness = check_control_rank_uniqueness(rank_table)
    if is_refusal(uniqueness):
        return uniqueness
    present = set(rank_table.ranks_by_kind())
    missing = RANKED_CONTROL_KINDS - present
    if missing:
        return invalid(
            "rank_table",
            "the BMS rank table must be total — every ranked control-action kind "
            "present, ranks unique; no QMF default fills a gap",
            missing=sorted(kind.value for kind in missing),
        )
    return Ok(rank_table)


def exclude_venue_resident_tier1(
    candidates: object,
) -> Result[tuple[tuple[DispatchCandidate, ...], tuple[DispatchCandidate, ...]]]:
    """Split venue-resident Tier-1 out of the arbitration set (DEC-0151).

    Tier-1 protective stops sit outside the ordering by construction — they
    fire when they fire; nothing asks the node and the node assumes nothing.
    """
    items = _coerce_candidates(candidates)
    if isinstance(items, TypedRefusal):
        return items
    inside: list[DispatchCandidate] = []
    outside: list[DispatchCandidate] = []
    for item in items:
        if item.origin is CandidateOrigin.VENUE_RESIDENT_TIER1:
            outside.append(item)
        else:
            inside.append(item)
    return Ok((tuple(inside), tuple(outside)))


def command_outcome_never_satisfies() -> bool:
    """A command outcome alone never satisfies a standing protective intent."""
    return True


def check_dead_wire_satisfaction(
    record: object,
    *,
    verdict: object,
    scope_flat: object = False,
    no_pending_orders: object = False,
    command_outcome_observed: object = False,
) -> Result[DeadWireSatisfaction]:
    """Evaluate satisfaction under a dead/UNKNOWN wire (TN-7; DEC-0192).

    ``suspend_new`` / ``drain`` stay ``never-auto``. ``flatten`` requires
    ``scope-flat-at-reconciled-verdict``. A command outcome alone satisfies
    nothing. ``drift | unknown | out-of-lookback`` hold the intent open and
    alarm.
    """
    if not isinstance(record, ControlActionRecord):
        return invalid(
            "record",
            "dead-wire satisfaction reads a ControlActionRecord",
            given=repr(record),
        )
    if not isinstance(command_outcome_observed, bool):
        return invalid(
            "command_outcome_observed",
            "command_outcome_observed is a boolean",
            given=repr(command_outcome_observed),
        )
    if (
        record.action_kind in NEVER_AUTO_KINDS
        and record.satisfaction_predicate is not SatisfactionPredicate.NEVER_AUTO
    ):
        return policy(
            "satisfaction_predicate",
            "suspend_new and drain are never-auto under a dead wire — clearing "
            "only by an operator resume",
            action_kind=record.action_kind.value,
            given=record.satisfaction_predicate.value,
        )
    if (
        record.action_kind is ControlActionKind.FLATTEN
        and record.satisfaction_predicate
        is not SatisfactionPredicate.SCOPE_FLAT_AT_RECONCILED_VERDICT
    ):
        return policy(
            "satisfaction_predicate",
            "flatten requires scope-flat-at-reconciled-verdict; a command "
            "outcome alone satisfies nothing",
            given=record.satisfaction_predicate.value,
        )

    status = evaluate_satisfaction(
        record.satisfaction_predicate,
        verdict=verdict,
        scope_flat=scope_flat,
        no_pending_orders=no_pending_orders,
    )
    if is_refusal(status):
        return status

    if isinstance(verdict, ReconciliationVerdict):
        resolved_verdict = verdict
    elif isinstance(verdict, str):
        try:
            resolved_verdict = ReconciliationVerdict(verdict)
        except ValueError:
            return invalid(
                "verdict",
                "satisfaction reads reconciled | drift | unknown | out-of-lookback",
                given=repr(verdict),
            )
    else:
        return invalid(
            "verdict",
            "satisfaction reads a ReconciliationVerdict",
            given=repr(verdict),
        )

    effective = status.value
    # A command outcome alone never satisfies — even under a dead wire. Scope-flat
    # / never-auto predicates are the only clearance path; observing a close
    # acceptance without the predicate evidence leaves the intent open.
    if (
        command_outcome_observed
        and effective is StandingIntentStatus.SATISFIED
        and scope_flat is not True
        and record.satisfaction_predicate is SatisfactionPredicate.SCOPE_FLAT_AT_RECONCILED_VERDICT
    ):
        effective = StandingIntentStatus.OPEN

    alarm = effective is StandingIntentStatus.HELD_ALARM
    if alarm:
        detail = (
            f"{resolved_verdict.value} holds the standing intent open without "
            "dispatching; alarm raised — a protection mechanism never acts against "
            "state it cannot see"
        )
    elif effective is StandingIntentStatus.SATISFIED:
        detail = "standing intent satisfied under the declared predicate"
    elif record.satisfaction_predicate is SatisfactionPredicate.NEVER_AUTO:
        detail = (
            f"{record.action_kind.value} is never-auto; stands until an operator "
            "resume — a reconciled verdict never clears it"
        )
    else:
        detail = (
            "flatten remains open until a reconciled verdict shows the scope flat; "
            "a command outcome alone satisfies nothing"
        )
    return Ok(
        DeadWireSatisfaction(
            record=record,
            status=effective,
            predicate=record.satisfaction_predicate,
            verdict=resolved_verdict,
            command_outcome_satisfies=False,
            alarm=alarm,
            detail=detail,
        )
    )


def persist_protective_intent(
    record: object,
    *,
    journal_result: object,
    extent: object,
    alarms: MutableSequence[Mapping[str, object]] | None = None,
) -> Result[PersistedProtectiveIntent]:
    """Evidence-first standing-intent persistence (NFR-12/15; TN-4 / TN-7).

    Journal first. On sink refusal write the reserved protection-intent extent.
    Failure of both becomes ``UNDELIVERABLE`` and alarmed. The act is later
    re-decided — never blindly retried.
    """
    if not isinstance(record, ControlActionRecord):
        return invalid(
            "record",
            "persist_protective_intent journals a ControlActionRecord",
            given=repr(record),
        )
    if not isinstance(extent, ProtectionIntentExtent):
        return invalid(
            "extent",
            "evidence-first persistence requires a reserved ProtectionIntentExtent",
            given=type(extent).__name__,
        )
    fp = record.fingerprint()
    if is_refusal(fp):
        return fp

    journaled = journal_before_dispatch(record, journal_result=journal_result)
    if is_ok(journaled):
        return Ok(
            PersistedProtectiveIntent(
                record=record,
                record_fingerprint=fp.value,
                disposition=IntentPersistDisposition.JOURNALED,
                undeliverable=None,
                detail=(
                    "standing protective intent journaled before dispatch; "
                    "evidence-first — re-decided, never blind-retried"
                ),
            )
        )

    # Journal refused — reserved extent fallback.
    extent_record: dict[str, object] = {
        "kind": "standing-protection-intent",
        "stream": record.stream.fp1_identity(),
        "control_action_fp1": fp.value.value,
        "action_kind": record.action_kind.value,
        "authority": record.authority,
        "authority_kind": record.authority_kind.value,
        "subject_scope": record.subject_scope.value,
        "scope_ref": record.scope_ref,
        "satisfaction_predicate": record.satisfaction_predicate.value,
        "rank": record.rank,
        "extent": "reserved-protection-intent",
    }
    written = extent.write(extent_record)
    if is_ok(written):
        return Ok(
            PersistedProtectiveIntent(
                record=record,
                record_fingerprint=fp.value,
                disposition=IntentPersistDisposition.EXTENT,
                undeliverable=None,
                detail=(
                    "normal journal refused; standing protective intent persisted to "
                    "the reserved protection-intent extent — re-decided when storage "
                    "returns, never blind-retried"
                ),
            )
        )

    undeliverable = UndeliverableProtectiveIntent(
        record_fingerprint=fp.value,
        stream=record.stream,
        action_kind=record.action_kind,
        alarm_class=UNDELIVERABLE_ALARM_CLASS,
        detail=(
            "standing protective intent could not be journaled to the evidence room "
            "or the reserved protection-intent extent; honestly UNDELIVERABLE"
        ),
    )
    if alarms is not None:
        alarms.append(
            {
                "alarm_class": UNDELIVERABLE_ALARM_CLASS,
                "reason": "undeliverable-protection-intent",
                "stream": record.stream.fp1_identity(),
                "control_action_fp1": fp.value.value,
                "action_kind": record.action_kind.value,
            }
        )
    return Ok(
        PersistedProtectiveIntent(
            record=record,
            record_fingerprint=fp.value,
            disposition=IntentPersistDisposition.UNDELIVERABLE,
            undeliverable=undeliverable,
            detail=undeliverable.detail,
        )
    )


def redecide_protective_intent(
    record: object,
    *,
    verdict: object,
    scope_flat: object = False,
    no_pending_orders: object = False,
) -> Result[StandingIntentFold]:
    """Re-decide a standing protective intent — never a blind retry (DEC-0150).

    On reconnect the node re-evaluates against reconciled state and, if still
    unsatisfied, issues a **new** command with a **new** identity.
    """
    return reevaluate_standing_intent(
        record,
        verdict=verdict,
        scope_flat=scope_flat,
        no_pending_orders=no_pending_orders,
    )


def dispatch_ranked_controls(
    candidates: object,
    rank_table: object,
    *,
    stream: object,
    arbitration_seed: object = "protection-dispatch",
) -> Result[DispatchPlan]:
    """Evaluate one stream: rank-arbitrate node acts; leave Tier-1 outside.

    Uses the BMS-declared total unique AD-37 rank. Collapses only identical
    mechanical commands. Composing actions both execute. Arrival order is
    recorded on candidates for evidence but never consulted. A lower rank
    never undoes or weakens a higher one (exit-preservation invariant).
    """
    table = require_total_unique_rank_table(rank_table)
    if is_refusal(table):
        return table
    if not isinstance(stream, CommandStreamKey):
        return invalid(
            "stream",
            "the protection dispatcher runs at exactly one (VenueId, account) point",
            given=repr(stream),
        )
    split = exclude_venue_resident_tier1(candidates)
    if is_refusal(split):
        return split
    inside, outside = split.value

    for item in inside:
        if item.record.stream != stream or item.enforcement.stream != stream:
            return invalid(
                "candidates",
                "every candidate must share the dispatcher stream — cross-stream "
                "ordering is a declared non-guarantee",
            )

    if not inside:
        return Ok(
            DispatchPlan(
                stream=stream,
                arbitration=None,
                emit=(),
                suppressed=(),
                venue_resident_outside=outside,
                arrival_order_ignored=True,
            )
        )

    # Build pending set sorted by rank then fingerprint — NEVER by arrival_ordinal.
    pending: list[PendingControlAction] = []
    # Deliberately shuffle-stable against arrival: sort key ignores arrival_ordinal.
    ordered_inside = sorted(
        inside,
        key=lambda c: (c.record.rank, _record_fp_value(c.record)),
    )
    for item in ordered_inside:
        pending_result = PendingControlAction.try_create(
            item.record,
            item.enforcement,
            mechanical_command=item.mechanical_command,
        )
        if is_refusal(pending_result):
            return pending_result
        pending.append(pending_result.value)

    # Prove arrival order was not the arbitration input: reverse-arrival must
    # fingerprint-equal the forward plan (enforced in tests via arrival_order_ignored).
    outcome = arbitrate_same_tick(
        pending,
        table.value,
        stream=stream,
        arbitration_seed=arbitration_seed,
    )
    if is_refusal(outcome):
        return outcome
    return Ok(
        DispatchPlan(
            stream=stream,
            arbitration=outcome.value,
            emit=outcome.value.emit,
            suppressed=outcome.value.suppressed,
            venue_resident_outside=outside,
            arrival_order_ignored=True,
        )
    )


@dataclass
class StreamProtectionDispatcher:
    """One evidence-first protection dispatcher bound to a command stream.

    Owns the BMS rank table, the reserved extent, and the standing-intent
    persistence path for that stream. Cross-stream ordering is a declared
    non-guarantee.
    """

    stream: CommandStreamKey
    rank_table: ControlRankTable
    extent: ProtectionIntentExtent
    _standing: list[ControlActionRecord] = field(default_factory=list[ControlActionRecord])
    _alarms: list[Mapping[str, object]] = field(default_factory=list[Mapping[str, object]])
    _undeliverable: list[UndeliverableProtectiveIntent] = field(
        default_factory=list[UndeliverableProtectiveIntent]
    )

    @classmethod
    def try_create(
        cls,
        *,
        stream: object,
        rank_table: object,
        extent: object,
    ) -> Result[StreamProtectionDispatcher]:
        if not isinstance(stream, CommandStreamKey):
            return invalid(
                "stream",
                "a protection dispatcher binds exactly one (VenueId, account) stream",
                given=repr(stream),
            )
        table = require_total_unique_rank_table(rank_table)
        if is_refusal(table):
            return table
        if not isinstance(extent, ProtectionIntentExtent):
            return invalid(
                "extent",
                "a protection dispatcher requires a reserved ProtectionIntentExtent",
                given=type(extent).__name__,
            )
        return Ok(cls(stream=stream, rank_table=table.value, extent=extent))

    @property
    def venue_id(self) -> VenueId:
        return self.stream.venue_id

    @property
    def account_id(self) -> str:
        return self.stream.account_id

    @property
    def standing_intents(self) -> tuple[ControlActionRecord, ...]:
        return tuple(self._standing)

    @property
    def alarms(self) -> tuple[Mapping[str, object], ...]:
        return tuple(self._alarms)

    @property
    def undeliverable(self) -> tuple[UndeliverableProtectiveIntent, ...]:
        return tuple(self._undeliverable)

    def evaluate(
        self,
        candidates: object,
        *,
        arbitration_seed: object = "protection-dispatch",
    ) -> Result[DispatchPlan]:
        """Rank-arbitrate one stream's pending acts (Tier-1 stays outside)."""
        return dispatch_ranked_controls(
            candidates,
            self.rank_table,
            stream=self.stream,
            arbitration_seed=arbitration_seed,
        )

    def admit_protective_act(
        self,
        record: object,
        *,
        journal_result: object,
    ) -> Result[PersistedProtectiveIntent]:
        """Persist a protective act evidence-first before dispatch consideration."""
        if not isinstance(record, ControlActionRecord):
            return invalid(
                "record",
                "admit_protective_act journals a ControlActionRecord",
                given=repr(record),
            )
        if record.stream != self.stream:
            return invalid(
                "record",
                "protective act runs on a different (VenueId, account) stream",
                dispatcher_stream=self.stream.fp1_identity(),
                record_stream=record.stream.fp1_identity(),
            )
        persisted = persist_protective_intent(
            record,
            journal_result=journal_result,
            extent=self.extent,
            alarms=self._alarms,
        )
        if is_refusal(persisted):
            return persisted
        result = persisted.value
        if result.disposition is IntentPersistDisposition.UNDELIVERABLE:
            if result.undeliverable is not None:
                self._undeliverable.append(result.undeliverable)
            return Ok(result)
        self._standing.append(record)
        return Ok(result)

    def check_satisfaction(
        self,
        record: object,
        *,
        verdict: object,
        scope_flat: object = False,
        no_pending_orders: object = False,
        command_outcome_observed: object = False,
    ) -> Result[DeadWireSatisfaction]:
        """Dead-wire satisfaction for one standing intent on this stream."""
        checked = check_dead_wire_satisfaction(
            record,
            verdict=verdict,
            scope_flat=scope_flat,
            no_pending_orders=no_pending_orders,
            command_outcome_observed=command_outcome_observed,
        )
        if is_refusal(checked):
            return checked
        if checked.value.alarm:
            self._alarms.append(
                {
                    "alarm_class": "protection-escalation",
                    "reason": "standing-intent-held-alarm",
                    "stream": self.stream.fp1_identity(),
                    "action_kind": checked.value.record.action_kind.value,
                    "verdict": checked.value.verdict.value,
                    "detail": checked.value.detail,
                }
            )
        return Ok(checked.value)

    def redecide(
        self,
        record: object,
        *,
        verdict: object,
        scope_flat: object = False,
        no_pending_orders: object = False,
    ) -> Result[StandingIntentFold]:
        """Re-decide one standing intent — never a blind retry."""
        return redecide_protective_intent(
            record,
            verdict=verdict,
            scope_flat=scope_flat,
            no_pending_orders=no_pending_orders,
        )


def _coerce_candidates(
    candidates: object,
) -> tuple[DispatchCandidate, ...] | TypedRefusal:
    given = type(candidates).__name__
    if isinstance(candidates, (str, bytes, Mapping)) or not isinstance(candidates, Iterable):
        return invalid(
            "candidates",
            "the dispatcher reads a collection of DispatchCandidate values",
            given=given,
        )
    items: list[DispatchCandidate] = []
    for item in cast("Iterable[object]", candidates):
        if not isinstance(item, DispatchCandidate):
            return invalid(
                "candidates",
                "each candidate is a DispatchCandidate",
                given=repr(item),
            )
        items.append(item)
    return tuple(items)


def _record_fp_value(record: ControlActionRecord) -> str:
    fp = record.fingerprint()
    if is_refusal(fp):
        return ""
    return fp.value.value
