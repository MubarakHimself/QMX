"""UNKNOWN enforcement at the exact ``(VenueId, account)`` stream boundary (Story 24.6).

QMX-F062 / TN-6 / TN-7 / TN-24c / DEC-0191 / DEC-0195 / DEC-0258:

* A ratified UNKNOWN trigger (timeout, transport error, disconnect mid-command)
  mints an ``UNKNOWN`` **state**, never a rejection.
* The entire affected ``(VenueId, account)`` command stream blocks — including new
  protection dispatch — while sensing and recording continue. Every other stream
  remains independent (strictly finer than a connection; coarser than a binding).
* A risk-non-increasing act arriving while blocked is journaled as a persistent
  standing protection intent and re-decided when the block clears — never marked
  refused-and-done, retried, or dropped. Journal failure uses the reserved
  protection-intent extent; failure of that write is honestly ``UNDELIVERABLE``
  and alarmed.
* A reconciled read-back inside the configured lookback that is unambiguous may
  auto-resolve; otherwise only an operator-principal attestation over the served
  read-back detail may resolve. ``drift``, reconciliation ``unknown``, and
  ``out-of-lookback`` never auto-resolve.

Only ``qmn.venue`` may import ``qmf.venue``; this module consumes the re-exported
shapes (DEC-0241).
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final, cast

from qmf.core import (
    Account,
    Fingerprint,
    Instant,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    SinkAck,
    SinkResult,
    TypedRefusal,
    VenueId,
    is_ok,
    is_refusal,
    unpersistable,
)

from qmn.loop.accumulator import stream_key as node_stream_key
from qmn.venue import (
    AdmissionDisposition,
    AdmissionResult,
    Command,
    CommandKind,
    ConnectionManager,
    Reconciliation,
    ReconciliationVerdict,
    ResolveObservation,
    ResolveResolution,
    StandingIntentDecision,
    StandingIntentDisposition,
    StandingIntentJournalEvent,
    StandingProtectionIntent,
    StreamBlockCause,
    SubmissionOutcome,
    SubmissionResult,
    UnknownBlock,
    UnknownGate,
    UnknownTrigger,
    is_risk_reducing,
    venue_command_stream,
)

__all__ = [
    "OPERATOR_PRINCIPAL",
    "UNDELIVERABLE_ALARM_CLASS",
    "CommandStreamUnknownBoundary",
    "HeldProtectionAct",
    "HoldDisposition",
    "ProtectionIntentExtent",
    "ReadbackClarity",
    "ResolveDecision",
    "ResolvePath",
    "UndeliverableProtectionIntent",
    "UnknownStreamRegistry",
    "decide_resolve_path",
    "unknown_never_rejection",
]


OPERATOR_PRINCIPAL: Final[str] = "operator"
UNDELIVERABLE_ALARM_CLASS: Final[str] = "silent-degradation"


class ResolvePath(StrEnum):
    """Which resolve_unknown path the node may take (TN-6 two-path precedence)."""

    AUTO = "auto"
    OPERATOR_ATTESTATION = "operator-attestation"
    HOLD_NO_RESOLVE = "hold-no-resolve"


class ReadbackClarity(StrEnum):
    """Whether a served read-back is unambiguous for one outstanding command."""

    OBSERVED_ACCEPTED = "observed-accepted"
    OBSERVED_ABSENT = "observed-absent"
    AMBIGUOUS = "ambiguous"
    ABSENT = "absent"


class HoldDisposition(StrEnum):
    """Fate of a risk-non-increasing act under an UNKNOWN block (glossary HELD)."""

    HELD = "held"
    UNDELIVERABLE = "undeliverable"


@dataclass(frozen=True, slots=True)
class ResolveDecision:
    """The node's two-path resolve decision for one outstanding UNKNOWN."""

    path: ResolvePath
    clarity: ReadbackClarity
    verdict: ReconciliationVerdict
    auto_resolution: ResolveResolution | None
    detail: str

    @property
    def may_auto_resolve(self) -> bool:
        return self.path is ResolvePath.AUTO and self.auto_resolution is not None


@dataclass(frozen=True, slots=True)
class UndeliverableProtectionIntent:
    """Honest terminal when neither the journal nor the reserved extent can hold."""

    command_fp1: Fingerprint
    kind: CommandKind
    stream: str
    alarm_class: str
    detail: str


@dataclass(frozen=True, slots=True)
class HeldProtectionAct:
    """A risk-non-increasing act held under UNKNOWN — never refused-and-done."""

    command: Command
    command_fp1: Fingerprint
    kind: CommandKind
    held_at: Instant
    disposition: HoldDisposition
    journaled_to_extent: bool
    undeliverable: UndeliverableProtectionIntent | None
    intent: StandingProtectionIntent | None
    detail: str


def unknown_never_rejection(outcome: object) -> bool:
    """``UNKNOWN`` is a state; it is never re-labelled as a venue rejection."""
    return outcome is SubmissionOutcome.UNKNOWN


def decide_resolve_path(
    reconciliation: object,
    *,
    clarity: object,
    covers_lookback: object = True,
) -> Result[ResolveDecision]:
    """Apply TN-6 two-path precedence for ``resolve_unknown`` (DEC-0195, DEC-0258).

    Auto-resolve only when the verdict is ``reconciled``, the read-back covers the
    configured lookback, and clarity is unambiguous (``observed-accepted`` or
    ``observed-absent``). ``drift``, reconciliation ``unknown``, and
    ``out-of-lookback`` never auto-resolve — they require operator-principal
    attestation over the served read-back detail (or hold with no resolve).
    """
    if not isinstance(reconciliation, Reconciliation):
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "reconciliation",
                "reason": "resolve path is decided against a Reconciliation verdict",
                "given": repr(reconciliation),
            },
        )
    resolved_clarity: ReadbackClarity | None
    if isinstance(clarity, ReadbackClarity):
        resolved_clarity = clarity
    elif isinstance(clarity, str):
        try:
            resolved_clarity = ReadbackClarity(clarity)
        except ValueError:
            resolved_clarity = None
    else:
        resolved_clarity = None
    if resolved_clarity is None:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "clarity",
                "reason": (
                    "read-back clarity is observed-accepted | observed-absent | "
                    "ambiguous | absent"
                ),
                "given": repr(clarity),
            },
        )
    if not isinstance(covers_lookback, bool):
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "covers_lookback",
                "reason": "lookback coverage is a boolean from the declared lookback window",
                "given": repr(covers_lookback),
            },
        )

    verdict = reconciliation.verdict
    if (
        verdict is ReconciliationVerdict.RECONCILED
        and covers_lookback
        and resolved_clarity
        in {ReadbackClarity.OBSERVED_ACCEPTED, ReadbackClarity.OBSERVED_ABSENT}
    ):
        auto = (
            ResolveResolution.OBSERVED_ACCEPTED
            if resolved_clarity is ReadbackClarity.OBSERVED_ACCEPTED
            else ResolveResolution.OBSERVED_ABSENT
        )
        return Ok(
            ResolveDecision(
                path=ResolvePath.AUTO,
                clarity=resolved_clarity,
                verdict=verdict,
                auto_resolution=auto,
                detail=(
                    "unambiguous reconciled read-back inside lookback; node may "
                    "auto-resolve via observed-accepted | observed-absent"
                ),
            )
        )
    if verdict in {
        ReconciliationVerdict.DRIFT,
        ReconciliationVerdict.UNKNOWN,
        ReconciliationVerdict.OUT_OF_LOOKBACK,
    }:
        return Ok(
            ResolveDecision(
                path=ResolvePath.OPERATOR_ATTESTATION,
                clarity=resolved_clarity,
                verdict=verdict,
                auto_resolution=None,
                detail=(
                    f"{verdict.value} never auto-resolves; only an operator-principal "
                    "attestation over the served read-back detail may resolve"
                ),
            )
        )
    # Reconciled but ambiguous/absent, or lookback not covered.
    return Ok(
        ResolveDecision(
            path=ResolvePath.OPERATOR_ATTESTATION,
            clarity=resolved_clarity,
            verdict=verdict,
            auto_resolution=None,
            detail=(
                "read-back is ambiguous, absent, or outside lookback; only an "
                "operator-principal attestation may resolve"
            ),
        )
    )


@dataclass
class ProtectionIntentExtent:
    """Reserved protection-intent extent (TN-4 / TN-7) under the state tree.

    When the normal journal cannot persist a standing protection intent, the node
    writes here rather than holding in memory alone. Capacity is a declared bound;
    exhaustion surfaces as a storage failure so the caller can mint UNDELIVERABLE.
    """

    capacity: int
    _records: list[Mapping[str, object]] = field(default_factory=list[Mapping[str, object]])

    @classmethod
    def try_create(cls, capacity: object) -> Result[ProtectionIntentExtent]:
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity <= 0:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "capacity",
                    "reason": "reserved protection-intent extent capacity is a positive int",
                    "given": repr(capacity),
                },
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
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "record",
                    "reason": "protection-intent extent stores a mapping record",
                    "given": type(record).__name__,
                },
            )
        if len(self._records) >= self.capacity:
            return unpersistable(
                "reserved protection-intent extent is full; standing intent cannot "
                "be persisted"
            )
        self._records.append(dict(cast("Mapping[str, object]", record)))
        return Ok(SinkAck())


@dataclass
class CommandStreamUnknownBoundary:
    """UNKNOWN block for exactly one ``(VenueId, account)`` command stream.

    Wraps the parent :class:`~qmn.venue.UnknownGate` and adds the node laws: reserved
    extent fallback, UNDELIVERABLE+alarm, two-path resolve, and HELD (not refused)
    disposition for risk-non-increasing acts.
    """

    venue_id: VenueId
    account: Account
    connection_manager: ConnectionManager
    gate: UnknownGate
    extent: ProtectionIntentExtent
    _extent_held: list[HeldProtectionAct] = field(default_factory=list[HeldProtectionAct])
    _undeliverable: list[UndeliverableProtectionIntent] = field(
        default_factory=list[UndeliverableProtectionIntent]
    )
    _alarms: list[Mapping[str, object]] = field(default_factory=list[Mapping[str, object]])

    @classmethod
    def try_create(
        cls,
        *,
        venue_id: object,
        account: object,
        connection_manager: object,
        extent: object,
    ) -> Result[CommandStreamUnknownBoundary]:
        if not isinstance(venue_id, VenueId) or venue_id.value.strip() == "":
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "venue_id",
                    "reason": "stream boundary binds a VenueId",
                    "given": repr(venue_id),
                },
            )
        if not isinstance(account, Account):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "account",
                    "reason": "stream boundary binds an Account",
                    "given": repr(account),
                },
            )
        if account.venue != venue_id:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "account",
                    "reason": "account must belong to the bound VenueId",
                    "venue": venue_id.value,
                    "account_venue": account.venue.value,
                },
            )
        if not isinstance(connection_manager, ConnectionManager):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "connection_manager",
                    "reason": "boundary writes through the venue ConnectionManager",
                    "given": type(connection_manager).__name__,
                },
            )
        expected = venue_command_stream(venue_id, account)
        if connection_manager.writer_id.stream != expected:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "connection_manager",
                    "reason": (
                        "ConnectionManager WriterId stream must equal this "
                        "(VenueId, account) command stream — QMX-F062 granularity"
                    ),
                    "expected_stream": expected,
                    "writer_stream": connection_manager.writer_id.stream,
                },
            )
        if not isinstance(extent, ProtectionIntentExtent):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "extent",
                    "reason": "boundary requires a reserved ProtectionIntentExtent",
                    "given": type(extent).__name__,
                },
            )
        gate = UnknownGate.try_create(connection_manager)
        if is_refusal(gate):
            return gate
        return Ok(
            cls(
                venue_id=venue_id,
                account=account,
                connection_manager=connection_manager,
                gate=gate.value,
                extent=extent,
            )
        )

    @property
    def stream(self) -> str:
        """Canonical venue ``(VenueId, account)`` stream token."""
        return venue_command_stream(self.venue_id, self.account)

    @property
    def node_stream_key(self) -> str:
        """Node-side stream token (accumulator / loop identity)."""
        return node_stream_key(self.venue_id, self.account)

    @property
    def stream_open(self) -> bool:
        return self.gate.stream_open

    @property
    def outstanding(self) -> tuple[UnknownBlock, ...]:
        return self.gate.outstanding

    @property
    def standing_intents(self) -> tuple[StandingProtectionIntent, ...]:
        return self.gate.standing_intents

    @property
    def extent_held(self) -> tuple[HeldProtectionAct, ...]:
        return tuple(self._extent_held)

    @property
    def undeliverable(self) -> tuple[UndeliverableProtectionIntent, ...]:
        return tuple(self._undeliverable)

    @property
    def alarms(self) -> tuple[Mapping[str, object], ...]:
        return tuple(self._alarms)

    @property
    def sensing_continues(self) -> bool:
        """Sensing/recording pipe is never gated by an UNKNOWN command block."""
        return self.connection_manager.sensing_pipe_open

    def record_unknown(self, submission_result: object) -> Result[UnknownBlock]:
        """Register an UNKNOWN submission — never translate it into a rejection."""
        if not isinstance(submission_result, SubmissionResult):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "submission_result",
                    "reason": "an outstanding block is recorded from a typed SubmissionResult",
                    "given": repr(submission_result),
                },
            )
        if not unknown_never_rejection(submission_result.outcome):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "submission_result",
                    "reason": (
                        "only an UNKNOWN outcome blocks the stream; UNKNOWN is never "
                        "translated into a rejection"
                    ),
                    "outcome": submission_result.outcome.value,
                },
            )
        if submission_result.outcome is SubmissionOutcome.REJECTED_BY_VENUE:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "outcome",
                    "reason": "UNKNOWN must never be re-labelled rejected-by-venue",
                },
            )
        return self.gate.record_unknown(submission_result)

    def admit(
        self, command: object, *, receive_instant: object
    ) -> Result[AdmissionResult | HeldProtectionAct]:
        """Admit or hold one command at this stream's UNKNOWN boundary.

        While UNKNOWN is outstanding every command is blocked, protection included.
        A risk-non-increasing act is HELD as a standing protection intent (journaled
        before dispatch); place_order is refused without hold. Journal failure falls
        back to the reserved extent; extent failure is UNDELIVERABLE + alarm.
        """
        if not isinstance(command, Command):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "command",
                    "reason": "boundary admits a typed CT-19 Command",
                    "given": type(command).__name__,
                },
            )
        if venue_command_stream(command.venue_id, command.account) != self.stream:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "command",
                    "reason": "command runs on a different (VenueId, account) stream",
                    "boundary_stream": self.stream,
                    "command_stream": venue_command_stream(command.venue_id, command.account),
                },
            )
        if not isinstance(receive_instant, Instant):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "receive_instant",
                    "reason": "wall receive Instant is mandatory at the stream gate",
                    "given": repr(receive_instant),
                },
            )

        admitted = self.gate.admit(command, receive_instant=receive_instant)
        if is_ok(admitted):
            result = admitted.value
            if result.disposition is AdmissionDisposition.HELD_AS_STANDING_INTENT:
                # Node law: held, not refused-and-done / retried / dropped.
                assert result.standing_intent is not None
                return Ok(
                    HeldProtectionAct(
                        command=command,
                        command_fp1=result.command_fp1,
                        kind=command.kind,
                        held_at=receive_instant,
                        disposition=HoldDisposition.HELD,
                        journaled_to_extent=False,
                        undeliverable=None,
                        intent=result.standing_intent,
                        detail=(
                            "risk-non-increasing act held as standing protection intent; "
                            "re-decided when the UNKNOWN block clears — never refused, "
                            "retried, or dropped"
                        ),
                    )
                )
            return Ok(result)

        # Storage failure journaling a standing intent: reserved extent fallback.
        refusal = admitted
        assert is_refusal(refusal)
        if (
            self.gate.stream_open
            or not is_risk_reducing(command.kind)
            or refusal.category is not RefusalCategory.STORAGE_FAILURE
        ):
            return refusal
        return self._hold_via_extent_or_undeliverable(command, receive_instant)

    def _hold_via_extent_or_undeliverable(
        self, command: Command, held_at: Instant
    ) -> Result[HeldProtectionAct]:
        fp = command.fingerprint()
        if is_refusal(fp):
            return fp
        command_fp1 = fp.value
        journal_event = StandingIntentJournalEvent.held(command_fp1, command.kind)
        record: dict[str, object] = {
            "kind": "standing-protection-intent",
            "stream": self.stream,
            "command_fp1": command_fp1.value,
            "command_kind": command.kind.value,
            "held_at_ns": held_at.value_ns,
            "event_type": journal_event.event_type,
            "extent": "reserved-protection-intent",
        }
        written = self.extent.write(record)
        if is_ok(written):
            intent = StandingProtectionIntent(
                command=command,
                command_fp1=command_fp1,
                kind=command.kind,
                held_at=held_at,
                journal_event=journal_event,
                detail=(
                    "journaled into the reserved protection-intent extent after the "
                    "normal journal refused; re-decided when the block clears"
                ),
            )
            held = HeldProtectionAct(
                command=command,
                command_fp1=command_fp1,
                kind=command.kind,
                held_at=held_at,
                disposition=HoldDisposition.HELD,
                journaled_to_extent=True,
                undeliverable=None,
                intent=intent,
                detail=(
                    "normal journal failed; standing protection intent persisted to "
                    "the reserved protection-intent extent"
                ),
            )
            self._extent_held.append(held)
            return Ok(held)

        undeliverable = UndeliverableProtectionIntent(
            command_fp1=command_fp1,
            kind=command.kind,
            stream=self.stream,
            alarm_class=UNDELIVERABLE_ALARM_CLASS,
            detail=(
                "standing protection intent could not be journaled to the evidence "
                "room or the reserved protection-intent extent; honestly UNDELIVERABLE"
            ),
        )
        self._undeliverable.append(undeliverable)
        alarm: dict[str, object] = {
            "alarm_class": UNDELIVERABLE_ALARM_CLASS,
            "reason": "undeliverable-protection-intent",
            "stream": self.stream,
            "command_fp1": command_fp1.value,
            "command_kind": command.kind.value,
        }
        self._alarms.append(alarm)
        held = HeldProtectionAct(
            command=command,
            command_fp1=command_fp1,
            kind=command.kind,
            held_at=held_at,
            disposition=HoldDisposition.UNDELIVERABLE,
            journaled_to_extent=False,
            undeliverable=undeliverable,
            intent=None,
            detail=undeliverable.detail,
        )
        return Ok(held)

    def resolve_auto(
        self,
        command_fp1: object,
        decision: object,
        *,
        receive_instant: object,
    ) -> Result[ResolveObservation]:
        """Clear one UNKNOWN via the auto path — only when ``decide_resolve_path`` said so."""
        if not isinstance(decision, ResolveDecision):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "decision",
                    "reason": "auto-resolve requires a ResolveDecision from decide_resolve_path",
                    "given": repr(decision),
                },
            )
        if not decision.may_auto_resolve or decision.auto_resolution is None:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "resolve_path",
                    "reason": (
                        "auto-resolve refused: drift, unknown, out-of-lookback, or "
                        "ambiguous read-back never auto-resolves"
                    ),
                    "path": decision.path.value,
                    "verdict": decision.verdict.value,
                    "clarity": decision.clarity.value,
                },
            )
        return self.gate.resolve_unknown(
            command_fp1,
            decision.auto_resolution,
            receive_instant=receive_instant,
        )

    def resolve_by_operator_attestation(
        self,
        command_fp1: object,
        *,
        principal: object,
        receive_instant: object,
        readback_detail: object = "",
    ) -> Result[ResolveObservation]:
        """Clear one UNKNOWN only under an operator-principal attestation (TN-6)."""
        if not isinstance(principal, str) or principal.strip() != OPERATOR_PRINCIPAL:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "principal",
                    "reason": (
                        "only an operator-principal attestation over the served "
                        "read-back detail may resolve when auto-resolve is unavailable"
                    ),
                    "required_principal": OPERATOR_PRINCIPAL,
                    "given": repr(principal),
                },
            )
        if readback_detail is None or (
            isinstance(readback_detail, str) and readback_detail.strip() == ""
        ):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "readback_detail",
                    "reason": (
                        "operator attestation resolves over the served read-back "
                        "detail from the evidence channel"
                    ),
                    "given": repr(readback_detail),
                },
            )
        resolved = self.gate.resolve_unknown(
            command_fp1,
            ResolveResolution.OPERATOR_ATTESTED,
            receive_instant=receive_instant,
        )
        if is_refusal(resolved):
            return resolved
        # Stamp attestation provenance onto the observation detail (immutable replace
        # via a fresh ResolveObservation — parent observation carries no signer).
        obs = resolved.value
        return Ok(
            ResolveObservation(
                command_fp1=obs.command_fp1,
                kind=obs.kind,
                resolution=ResolveResolution.OPERATOR_ATTESTED,
                receive_instant=obs.receive_instant,
                detail=(
                    f"operator-principal attestation over served read-back detail; "
                    f"principal={OPERATOR_PRINCIPAL}; readback={readback_detail!r}"
                ),
            )
        )

    def redecide_standing_intent(
        self, intent: object, reconciliation: object
    ) -> Result[StandingIntentDecision]:
        """Re-decide a gate-held standing intent (never a retry)."""
        return self.gate.redecide_standing_intent(intent, reconciliation)

    def redecide_extent_held(
        self, held: object, reconciliation: object
    ) -> Result[StandingIntentDecision]:
        """Re-decide an extent-held act once the UNKNOWN block has cleared."""
        if not isinstance(held, HeldProtectionAct) or held.intent is None:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "held",
                    "reason": "re-decision reads a HeldProtectionAct with a standing intent",
                    "given": repr(held),
                },
            )
        if held not in self._extent_held and held.command_fp1.value not in {
            item.command_fp1.value for item in self._extent_held
        }:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "held",
                    "reason": "not an extent-held standing protection intent on this stream",
                    "command_fp1": held.command_fp1.value,
                },
            )
        if not isinstance(reconciliation, Reconciliation):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "reconciliation",
                    "reason": "a standing intent is re-decided against a Reconciliation verdict",
                    "given": repr(reconciliation),
                },
            )
        if not self.gate.stream_open:
            return Ok(
                StandingIntentDecision(
                    intent=held.intent,
                    disposition=StandingIntentDisposition.HOLD_OPEN,
                    verdict=reconciliation.verdict,
                    alarm=True,
                    detail=(
                        "the UNKNOWN block has not cleared; extent-held standing "
                        "intent holds open without dispatching"
                    ),
                )
            )
        if reconciliation.standing_intent_may_dispatch:
            self._extent_held = [
                item
                for item in self._extent_held
                if item.command_fp1.value != held.command_fp1.value
            ]
            return Ok(
                StandingIntentDecision(
                    intent=held.intent,
                    disposition=StandingIntentDisposition.DISPATCH,
                    verdict=reconciliation.verdict,
                    alarm=False,
                    detail=(
                        "re-decided against a reconciled verdict; protection act "
                        "dispatches fresh — never a retry"
                    ),
                )
            )
        return Ok(
            StandingIntentDecision(
                intent=held.intent,
                disposition=StandingIntentDisposition.HOLD_OPEN,
                verdict=reconciliation.verdict,
                alarm=True,
                detail=(
                    "drift, unknown, or out-of-lookback alarms and holds the "
                    "extent-held intent open without dispatching"
                ),
            )
        )


@dataclass
class UnknownStreamRegistry:
    """Registry of per-``(VenueId, account)`` UNKNOWN boundaries (QMX-F062).

    Two accounts on one logical connection are independent streams; two bindings
    on one account share one stream and therefore one block.
    """

    _streams: MutableMapping[str, CommandStreamUnknownBoundary] = field(
        default_factory=dict[str, CommandStreamUnknownBoundary]
    )

    def register(self, boundary: object) -> Result[CommandStreamUnknownBoundary]:
        if not isinstance(boundary, CommandStreamUnknownBoundary):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "boundary",
                    "reason": "registry accepts a CommandStreamUnknownBoundary",
                    "given": type(boundary).__name__,
                },
            )
        key = boundary.stream
        existing = self._streams.get(key)
        if existing is not None and existing is not boundary:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "stream",
                    "reason": (
                        "one UNKNOWN boundary per (VenueId, account) command stream; "
                        "duplicate registration refused"
                    ),
                    "stream": key,
                },
            )
        self._streams[key] = boundary
        return Ok(boundary)

    def get(self, venue_id: object, account: object) -> Result[CommandStreamUnknownBoundary]:
        if not isinstance(venue_id, VenueId) or not isinstance(account, Account):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "stream",
                    "reason": "lookup requires VenueId and Account",
                    "venue": repr(venue_id),
                    "account": repr(account),
                },
            )
        key = venue_command_stream(venue_id, account)
        boundary = self._streams.get(key)
        if boundary is None:
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.AFTER_CONDITION,
                context={
                    "field": "stream",
                    "reason": "no UNKNOWN boundary registered for this (VenueId, account)",
                    "stream": key,
                },
                after_condition_descriptor="register CommandStreamUnknownBoundary",
            )
        return Ok(boundary)

    def boundary_for_command(self, command: object) -> Result[CommandStreamUnknownBoundary]:
        if not isinstance(command, Command):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "command",
                    "reason": "stream lookup reads a typed Command",
                    "given": type(command).__name__,
                },
            )
        return self.get(command.venue_id, command.account)

    @property
    def streams(self) -> tuple[str, ...]:
        return tuple(sorted(self._streams))

    def is_independent(self, left: object, right: object) -> Result[bool]:
        """Whether two boundaries are independent command streams (QMX-F062)."""
        if not isinstance(left, CommandStreamUnknownBoundary) or not isinstance(
            right, CommandStreamUnknownBoundary
        ):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "boundaries",
                    "reason": "independence compares two CommandStreamUnknownBoundary values",
                },
            )
        return Ok(left.stream != right.stream)
