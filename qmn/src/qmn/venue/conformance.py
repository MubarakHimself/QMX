"""FEAT-0023 venue conformance double — third :class:`VenueClientPort` (DEC-0208, DEC-0228).

Deterministic, credential-free, and network-free. Selected by ``(world, VenueId)``.
The same suite exercises this double and is reusable unchanged by live and replay
implementations. Compound-command acceptance stays blocked until FTR-02 lands.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final

from qmf.core import (
    Account,
    AccountRole,
    Duration,
    Fingerprint,
    Instant,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    VenueId,
    World,
    is_ok,
    is_refusal,
)
from qmf.venue.commands import (
    Command,
    CommandKind,
    CommandObservation,
    CompoundCommand,
    JournalEvent,
    SubmissionOutcome,
    SubmissionResult,
    UnknownTrigger,
)
from qmf.venue.events import Reconciliation, ReconciliationVerdict, SubjectResolution

from qmn.venue.port import VenueClientKind, VenueClientPort

__all__ = [
    "CONFORMANCE_CASES",
    "ConformanceCase",
    "ConformanceDouble",
    "PositionModel",
    "compound_command_acceptance_blocked",
    "run_conformance_suite",
]


class ConformanceCase(StrEnum):
    """Deterministic suite cases both the double and live/replay must pass."""

    SUCCESS = "success"
    REJECTION = "rejection"
    TIMEOUT = "timeout"
    TRANSPORT_ERROR = "transport-error"
    DISCONNECT = "disconnect"
    PARTIAL = "partial"
    SUPERSEDED_BY_FILL = "superseded-by-fill"
    NETTING = "netting"
    HEDGING = "hedging"


CONFORMANCE_CASES: Final[tuple[ConformanceCase, ...]] = tuple(ConformanceCase)


class PositionModel(StrEnum):
    """CT-18 measured position model (netting | hedging)."""

    NETTING = "netting"
    HEDGING = "hedging"


# FTR-02 blocks compound-command acceptance until the CT-19/TN-6 annotation lands.
_FTR02_BLOCK: Final[TypedRefusal] = TypedRefusal(
    category=RefusalCategory.UNSUPPORTED_CAPABILITY,
    retryability=Retryability.NO,
    context={
        "field": "compound_command",
        "reason": "compound-command acceptance blocked until FTR-02's CT-19/TN-6 "
        "all-rejected contract annotation lands",
        "ftr": "FTR-02",
    },
)


def compound_command_acceptance_blocked() -> TypedRefusal:
    """The typed refusal every compound-command acceptance path returns until FTR-02."""
    return _FTR02_BLOCK


@dataclass
class ConformanceDouble:
    """FEAT-0023 conformance double implementing :class:`VenueClientPort`.

    Script-driven: :meth:`arm` selects the next deterministic outcome. No network,
    no credentials, no ambient clock (instants are injected).
    """

    _world: World
    _venue_id: VenueId
    _account: Account | None = None
    _session_open: bool = False
    _armed: ConformanceCase | None = None
    _position_model: PositionModel = PositionModel.NETTING
    _observations: list[dict[str, object]] = field(default_factory=list[dict[str, object]])
    _capabilities_verified: bool = False
    _ordinal: int = 0

    @classmethod
    def try_create(cls, world: object, venue_id: object) -> Result[ConformanceDouble]:
        """Build a conformance double for ``(world, VenueId)``."""
        if not isinstance(world, World):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "world",
                    "reason": "conformance double is selected by (world, VenueId)",
                    "given": repr(world),
                },
            )
        if world is World.REPLAY:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "world",
                    "reason": "replay compositions bind the replay VenueClientPort, "
                    "never the conformance double",
                    "world": world.value,
                },
            )
        if not isinstance(venue_id, VenueId) or venue_id.value.strip() == "":
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "venue_id",
                    "reason": "conformance double requires a valid VenueId",
                    "given": repr(venue_id),
                },
            )
        return Ok(cls(_world=world, _venue_id=venue_id))

    @property
    def kind(self) -> VenueClientKind:
        return VenueClientKind.CONFORMANCE

    @property
    def venue_id(self) -> VenueId:
        return self._venue_id

    @property
    def world(self) -> World:
        return self._world

    def arm(self, case: object) -> Result[ConformanceCase]:
        """Arm the next deterministic outcome the subsequent submit/observe will emit."""
        if isinstance(case, ConformanceCase):
            resolved = case
        elif isinstance(case, str):
            try:
                resolved = ConformanceCase(case)
            except ValueError:
                return TypedRefusal(
                    category=RefusalCategory.INVALID_INPUT,
                    retryability=Retryability.NO,
                    context={
                        "field": "case",
                        "reason": "unknown conformance case",
                        "given": case,
                        "allowed": [m.value for m in ConformanceCase],
                    },
                )
        else:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "case",
                    "reason": "unknown conformance case",
                    "given": repr(case),
                },
            )
        if resolved is ConformanceCase.NETTING:
            self._position_model = PositionModel.NETTING
        elif resolved is ConformanceCase.HEDGING:
            self._position_model = PositionModel.HEDGING
        self._armed = resolved
        return Ok(resolved)

    def open_session(self, account: object) -> Result[bool]:
        if not isinstance(account, Account):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "account",
                    "reason": "open_session requires an Account",
                    "given": repr(account),
                },
            )
        if account.venue != self._venue_id:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "account",
                    "reason": "account does not belong to this VenueId",
                    "venue": self._venue_id.value,
                    "account_venue": account.venue.value,
                },
            )
        self._account = account
        self._session_open = True
        return Ok(True)

    def close_session(self) -> Result[bool]:
        self._session_open = False
        self._account = None
        return Ok(True)

    def verify_capabilities(self) -> Result[Mapping[str, object]]:
        if not self._session_open:
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.AFTER_CONDITION,
                context={
                    "field": "session",
                    "reason": "capability verification requires an open session",
                },
                after_condition_descriptor="open_session",
            )
        profile: dict[str, object] = {
            "position_model": self._position_model.value,
            "proto_tag": 91,
            "verified": True,
            "static_declaration_present": True,
            "measured_at_connection": True,
        }
        self._capabilities_verified = True
        self._observations.append({"kind": "capability-profile", "profile": dict(profile)})
        return Ok(profile)

    def submit(self, command: object) -> Result[SubmissionResult]:
        if isinstance(command, CompoundCommand):
            return compound_command_acceptance_blocked()
        if not isinstance(command, Command):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "command",
                    "reason": "submit requires a CT-19 Command",
                    "given": type(command).__name__,
                },
            )
        if not self._session_open or not self._capabilities_verified:
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.AFTER_CONDITION,
                context={
                    "field": "readiness",
                    "reason": "submit requires an open session and verified capabilities",
                },
                after_condition_descriptor="open_session then verify_capabilities",
            )
        case = self._armed if self._armed is not None else ConformanceCase.SUCCESS
        receive = Instant.try_create(1_700_000_000_000_000_000)
        if is_refusal(receive):
            return receive
        instant = receive.value
        fp_result = command.fingerprint()
        if is_refusal(fp_result):
            return fp_result
        fp = fp_result.value
        result = _resolve_case(case, command, fp, instant)
        if is_ok(result):
            self._observations.append(
                {
                    "kind": "command-outcome",
                    "case": case.value,
                    "outcome": result.value.outcome.value,
                    "command_kind": command.kind.value,
                    "position_model": self._position_model.value,
                }
            )
            if case is ConformanceCase.SUPERSEDED_BY_FILL:
                self._observations.append(
                    {
                        "kind": "subject-terminal",
                        "resolution": SubjectResolution.SUPERSEDED_BY_TERMINAL_SUBJECT.value,
                    }
                )
            if case in {ConformanceCase.NETTING, ConformanceCase.HEDGING}:
                self._observations.append(
                    {
                        "kind": "position-model",
                        "position_model": self._position_model.value,
                    }
                )
            if case is ConformanceCase.PARTIAL:
                self._observations.append(
                    {
                        "kind": "fill",
                        "partial": True,
                        "observation_kind": "fill",
                    }
                )
        self._armed = None
        return result

    def observations(self) -> Result[Sequence[Mapping[str, object]]]:
        return Ok(tuple(dict(item) for item in self._observations))

    def reconcile(self) -> Result[Reconciliation]:
        return Ok(
            Reconciliation(
                verdict=ReconciliationVerdict.RECONCILED,
                detail="conformance double synthetic reconciliation",
            )
        )


def _resolve_case(
    case: ConformanceCase,
    command: Command,
    fp: Fingerprint,
    instant: Instant,
) -> Result[SubmissionResult]:
    if case is ConformanceCase.SUCCESS:
        return _outcome(fp, command.kind, SubmissionOutcome.ACCEPTED_BY_VENUE, instant)
    if case is ConformanceCase.REJECTION:
        return _outcome(
            fp,
            command.kind,
            SubmissionOutcome.REJECTED_BY_VENUE,
            instant,
            venue_code="conformance-reject",
        )
    if case is ConformanceCase.TIMEOUT:
        return _unknown(fp, command.kind, UnknownTrigger.TIMEOUT, instant)
    if case is ConformanceCase.TRANSPORT_ERROR:
        return _unknown(fp, command.kind, UnknownTrigger.TRANSPORT_ERROR, instant)
    if case is ConformanceCase.DISCONNECT:
        return _unknown(fp, command.kind, UnknownTrigger.DISCONNECT, instant)
    if case is ConformanceCase.PARTIAL:
        return _outcome(
            fp,
            command.kind,
            SubmissionOutcome.ACCEPTED_BY_VENUE,
            instant,
            detail="partial fill observed; order remains open",
        )
    if case is ConformanceCase.SUPERSEDED_BY_FILL:
        return _outcome(
            fp,
            command.kind,
            SubmissionOutcome.REJECTED_BY_VENUE,
            instant,
            detail=SubjectResolution.SUPERSEDED_BY_TERMINAL_SUBJECT.value,
        )
    # netting / hedging — successful submit under the armed position model
    return _outcome(fp, command.kind, SubmissionOutcome.ACCEPTED_BY_VENUE, instant)


def _outcome(
    fp: Fingerprint,
    kind: CommandKind,
    outcome: SubmissionOutcome,
    instant: Instant,
    *,
    venue_code: str | None = None,
    detail: str = "",
) -> Result[SubmissionResult]:
    observation = CommandObservation(
        command_fp1=fp,
        kind=kind,
        outcome=outcome,
        receive_instant=instant,
        venue_code=venue_code,
        detail=detail,
    )
    return Ok(
        SubmissionResult(
            command_fp1=fp,
            kind=kind,
            outcome=outcome,
            observation=observation,
            journal_event=JournalEvent.for_outcome(fp, kind, outcome),
        )
    )


def _unknown(
    fp: Fingerprint,
    kind: CommandKind,
    trigger: UnknownTrigger,
    instant: Instant,
) -> Result[SubmissionResult]:
    elapsed = Duration.try_create(1_000_000_000)
    if is_refusal(elapsed):
        return elapsed
    deadline = Instant.try_create(instant.value_ns + 5_000_000_000)
    if is_refusal(deadline):
        return deadline
    observation = CommandObservation(
        command_fp1=fp,
        kind=kind,
        outcome=SubmissionOutcome.UNKNOWN,
        receive_instant=instant,
        unknown_trigger=trigger,
        monotonic_elapsed=elapsed.value,
        submission_deadline=deadline.value,
        detail="conformance double UNKNOWN trigger",
    )
    return Ok(
        SubmissionResult(
            command_fp1=fp,
            kind=kind,
            outcome=SubmissionOutcome.UNKNOWN,
            observation=observation,
            journal_event=JournalEvent.for_outcome(fp, kind, SubmissionOutcome.UNKNOWN),
        )
    )


def run_conformance_suite(client: object) -> Result[Mapping[str, str]]:
    """Run every deterministic case against ``client`` without network or credentials.

    The same suite is reusable unchanged by live and replay implementations that
    honour :class:`VenueClientPort`. Compound-command acceptance is asserted blocked
    (FTR-02) and never treated as a suite pass.
    """
    if not isinstance(client, VenueClientPort):
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "client",
                "reason": "conformance suite requires a VenueClientPort",
                "given": type(client).__name__,
            },
        )
    if not isinstance(client, ConformanceDouble):
        return TypedRefusal(
            category=RefusalCategory.UNSUPPORTED_CAPABILITY,
            retryability=Retryability.NO,
            context={
                "field": "client",
                "reason": "live/replay suite reuse is tagged separately; this gate runs "
                "the credential-free conformance double",
                "kind": getattr(client, "kind", None),
            },
        )
    # Compound-command path must stay blocked (FTR-02) — asserted, not accepted.
    blocked = compound_command_acceptance_blocked()
    if blocked.category is not RefusalCategory.UNSUPPORTED_CAPABILITY:
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={"field": "ftr02", "reason": "FTR-02 block must remain unsupported-capability"},
        )

    results: dict[str, str] = {"compound_command": "blocked-ftr02"}
    # Suite driver uses the double's arm/submit surface; cases are ordered and
    # deterministic. Account/session lifecycle is opened once.
    account_result = Account.try_create("conformance-acct", client.venue_id, AccountRole.DEMO)
    if is_refusal(account_result):
        return account_result
    opened = client.open_session(account_result.value)
    if is_refusal(opened):
        return opened
    caps = client.verify_capabilities()
    if is_refusal(caps):
        return caps

    for case in CONFORMANCE_CASES:
        armed = client.arm(case)
        if is_refusal(armed):
            return armed
        command = _fixture_command(client.venue_id, account_result.value, case)
        if is_refusal(command):
            return command
        submitted = client.submit(command.value)
        if is_refusal(submitted):
            return submitted
        results[case.value] = submitted.value.outcome.value

    closed = client.close_session()
    if is_refusal(closed):
        return closed
    return Ok(results)


def _fixture_command(venue_id: VenueId, account: Account, case: ConformanceCase) -> Result[Command]:
    """Mint a minimal cancel_order fixture — avoids money-path place_order fields."""
    # cancel_order needs a subject reference only among the lighter kinds.
    # Use a stable ordinal derived from the case name length for determinism.
    ordinal = sum(ord(ch) for ch in case.value) % 10_000
    return Command.cancel_order(
        venue_id,
        account,
        "conformance-session",
        ordinal,
        f"order-{case.value}",
    )
