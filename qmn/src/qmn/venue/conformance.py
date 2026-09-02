"""FEAT-0023 venue conformance double — third :class:`VenueClientPort` (DEC-0208, DEC-0228).

Deterministic, credential-free, and network-free. Selected by ``(world, VenueId)``.
The same suite exercises this double and is reusable unchanged by live and replay
implementations. Compound-command acceptance stays blocked until FTR-02 lands.
Story 28.3 adds named money-path fault injection (timeout, transport-error,
disconnect, superseded-by-fill, reconnect-gap, unpersistable identity, queue
bound, protective-stop-capability) so the paper-milestone campaign can prove
degraded states without a live demo account.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

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
from qmn.venue.verify import (
    VenueFactVerification,
    VenueFactVerifier,
    conformance_measured_facts,
    ctrader_static_declaration,
)

# Shared capability-profile keys every VenueClientPort implementation must surface
# from verify_capabilities; a missing key is a capability-shape divergence (TN-23).
PORT_CONTRACT_CAPABILITY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "verified",
        "static_declaration_present",
        "measured_at_connection",
        "command_sequencer_open",
        "market_data_recordable",
        "proto_tag",
    }
)

__all__ = [
    "CONFORMANCE_CASES",
    "INJECTED_COMMAND_FAULTS",
    "PORT_CONTRACT_CAPABILITY_KEYS",
    "SHARED_FAULT_CONTRACT",
    "ConformanceCase",
    "ConformanceDouble",
    "InjectedFault",
    "PositionModel",
    "agree_live_and_double_fault_contract",
    "compare_port_contract_shapes",
    "compound_command_acceptance_blocked",
    "run_conformance_suite",
    "run_port_contract_suite",
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


class InjectedFault(StrEnum):
    """Named money-path faults the double (and node-local seams) can inject.

    Timeout, transport-error, disconnect, and superseded-by-fill arm the matching
    :class:`ConformanceCase`. Reconnect-gap, unpersistable identity, queue bound,
    and protective-stop-capability are scripted flags the campaign drives through
    reconnect, identity bind, the pacer, and the protective-stop gate.
    """

    TIMEOUT = "timeout"
    TRANSPORT_ERROR = "transport-error"
    DISCONNECT = "disconnect"
    SUPERSEDED_BY_FILL = "superseded-by-fill"
    RECONNECT_GAP = "reconnect-gap"
    UNPERSISTABLE_IDENTITY = "unpersistable-identity"
    QUEUE_BOUND = "queue-bound"
    PROTECTIVE_STOP_CAPABILITY = "protective-stop-capability"


INJECTED_COMMAND_FAULTS: Final[tuple[InjectedFault, ...]] = tuple(InjectedFault)

# Outcomes both the double and a live client must honour for the four venue
# command faults (TN-23). Live reuse is tagged ``@pytest.mark.live``; absence of
# a live demo account does not weaken the double's contract.
SHARED_FAULT_CONTRACT: Final[Mapping[str, str]] = MappingProxyType(
    {
        InjectedFault.TIMEOUT.value: SubmissionOutcome.UNKNOWN.value,
        InjectedFault.TRANSPORT_ERROR.value: SubmissionOutcome.UNKNOWN.value,
        InjectedFault.DISCONNECT.value: SubmissionOutcome.UNKNOWN.value,
        InjectedFault.SUPERSEDED_BY_FILL.value: (SubmissionOutcome.REJECTED_BY_VENUE.value),
    }
)

_CASE_BY_FAULT: Final[Mapping[InjectedFault, ConformanceCase | None]] = MappingProxyType(
    {
        InjectedFault.TIMEOUT: ConformanceCase.TIMEOUT,
        InjectedFault.TRANSPORT_ERROR: ConformanceCase.TRANSPORT_ERROR,
        InjectedFault.DISCONNECT: ConformanceCase.DISCONNECT,
        InjectedFault.SUPERSEDED_BY_FILL: ConformanceCase.SUPERSEDED_BY_FILL,
        InjectedFault.RECONNECT_GAP: None,
        InjectedFault.UNPERSISTABLE_IDENTITY: None,
        InjectedFault.QUEUE_BOUND: None,
        InjectedFault.PROTECTIVE_STOP_CAPABILITY: None,
    }
)

_DEFAULT_STOP_FORMS: Final[dict[str, str]] = {"market": "entry-relative"}


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
    _verification: VenueFactVerification | None = None
    _verifier: VenueFactVerifier | None = None
    _injected: InjectedFault | None = None
    _armed_reconcile: ReconciliationVerdict | None = None
    _identity_persistable: bool = True
    _queue_bound_breached: bool = False
    _protective_stop_forms: dict[str, str] = field(
        default_factory=lambda: dict(_DEFAULT_STOP_FORMS)
    )
    _gap_recovered: list[dict[str, object]] = field(default_factory=list[dict[str, object]])

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

    def inject(self, fault: object) -> Result[InjectedFault]:
        """Arm one named Story 28.3 money-path fault for the next drive."""
        resolved = _coerce_injected_fault(fault)
        if is_refusal(resolved):
            return resolved
        armed = resolved.value
        self._clear_injection()
        self._injected = armed
        case = _CASE_BY_FAULT[armed]
        if case is not None:
            armed_case = self.arm(case)
            if is_refusal(armed_case):
                return armed_case
        if armed is InjectedFault.RECONNECT_GAP:
            self._gap_recovered = [
                {
                    "observation_id": "fill-gap-1",
                    "kind": "fill",
                    "receive_wall_ns": 1_700_000_000_000_000_100,
                    "payload": {"qty": 1, "injected_fault": armed.value},
                    "execution_id": "exec-gap-1",
                }
            ]
            self._armed = ConformanceCase.DISCONNECT
        elif armed is InjectedFault.UNPERSISTABLE_IDENTITY:
            self._identity_persistable = False
        elif armed is InjectedFault.QUEUE_BOUND:
            self._queue_bound_breached = True
        elif armed is InjectedFault.PROTECTIVE_STOP_CAPABILITY:
            self._protective_stop_forms = {}
        return Ok(armed)

    def arm_reconcile(self, verdict: object) -> Result[ReconciliationVerdict]:
        """Arm the next :meth:`reconcile` verdict (four-verdict injection)."""
        if isinstance(verdict, ReconciliationVerdict):
            resolved = verdict
        elif isinstance(verdict, str):
            try:
                resolved = ReconciliationVerdict(verdict.strip().lower())
            except ValueError:
                return TypedRefusal(
                    category=RefusalCategory.INVALID_INPUT,
                    retryability=Retryability.NO,
                    context={
                        "field": "verdict",
                        "reason": "armed reconcile verdict is "
                        "reconciled|drift|unknown|out-of-lookback",
                        "given": verdict,
                    },
                )
        else:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "verdict",
                    "reason": "armed reconcile verdict is reconciled|drift|unknown|out-of-lookback",
                    "given": repr(verdict),
                },
            )
        self._armed_reconcile = resolved
        return Ok(resolved)

    def _clear_injection(self) -> None:
        self._injected = None
        self._armed = None
        self._identity_persistable = True
        self._queue_bound_breached = False
        self._protective_stop_forms = dict(_DEFAULT_STOP_FORMS)
        self._gap_recovered = []

    @property
    def injected_fault(self) -> InjectedFault | None:
        return self._injected

    @property
    def identity_persistable(self) -> bool:
        return self._identity_persistable

    @property
    def queue_bound_breached(self) -> bool:
        return self._queue_bound_breached

    @property
    def protective_stop_forms(self) -> Mapping[str, str]:
        return MappingProxyType(dict(self._protective_stop_forms))

    def gap_recovered_observations(self) -> tuple[Mapping[str, object], ...]:
        """Fill/lifecycle observations recovered after an injected reconnect gap."""
        return tuple(dict(item) for item in self._gap_recovered)

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
        """Run Story 24.2 CT-18 verify-or-refuse against synthetic measured facts.

        Static declaration stays distinct from the measured observation profile.
        No network and no Spotware token — the credentialed live path is tagged
        ``@pytest.mark.live`` separately.
        """
        if not self._session_open or self._account is None:
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.AFTER_CONDITION,
                context={
                    "field": "session",
                    "reason": "capability verification requires an open session",
                },
                after_condition_descriptor="open_session",
            )
        declaration = ctrader_static_declaration()
        if is_refusal(declaration):
            return declaration
        verifier = VenueFactVerifier.try_create(declaration.value, self._venue_id, self._account)
        if is_refusal(verifier):
            return verifier
        receive = Instant.try_create(1_700_000_000_000_000_000)
        if is_refusal(receive):
            return receive
        measured = conformance_measured_facts(
            received_at=receive.value,
            position_model=self._position_model.value,
        )
        if is_refusal(measured):
            return measured
        verified = verifier.value.verify(measured.value, received_at=receive.value)
        if is_refusal(verified):
            return verified
        outcome = verified.value
        sequencer = verifier.value.require_command_sequencer(outcome)
        if is_refusal(sequencer):
            # Surface journaled data-quality defects; sequencer stays closed.
            self._verification = outcome
            self._verifier = verifier.value
            self._observations.append(
                {
                    "kind": "data-quality",
                    "journal": [event.as_mapping() for event in outcome.journal],
                    "defects": {key: value.value for key, value in outcome.defects.items()},
                }
            )
            return sequencer
        self._verification = outcome
        self._verifier = verifier.value
        self._capabilities_verified = True
        profile: dict[str, object] = {
            "position_model": self._position_model.value,
            "proto_tag": 91,
            "verified": True,
            "static_declaration_present": True,
            "measured_at_connection": True,
            "profile_version": outcome.profile_version,
            "command_sequencer_open": outcome.command_sequencer_open,
            "market_data_recordable": outcome.market_data_recordable,
            "static_fields": sorted(
                name.value
                for name, cap_field in outcome.declaration.fields.items()
                if cap_field.is_static
            ),
            "measured_checks": [fact.check.value for fact in outcome.profile.facts],
            "journal_event_types": [event.event_type for event in outcome.journal],
            "protective_stop_forms": dict(self._protective_stop_forms),
        }
        self._observations.append({"kind": "capability-profile", "profile": dict(profile)})
        return Ok(profile)

    @property
    def verification(self) -> VenueFactVerification | None:
        """The latest Story 24.2 verification outcome, if any."""
        return self._verification

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
        verdict = (
            self._armed_reconcile
            if self._armed_reconcile is not None
            else ReconciliationVerdict.RECONCILED
        )
        self._armed_reconcile = None
        return Ok(
            Reconciliation(
                verdict=verdict,
                detail=f"conformance double synthetic reconciliation ({verdict.value})",
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


def _coerce_injected_fault(fault: object) -> Result[InjectedFault]:
    if isinstance(fault, InjectedFault):
        return Ok(fault)
    if isinstance(fault, str):
        try:
            return Ok(InjectedFault(fault.strip().lower()))
        except ValueError:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "fault",
                    "reason": "unknown injected money-path fault",
                    "given": fault,
                    "allowed": [member.value for member in InjectedFault],
                },
            )
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context={
            "field": "fault",
            "reason": "unknown injected money-path fault",
            "given": repr(fault),
            "allowed": [member.value for member in InjectedFault],
        },
    )


def agree_live_and_double_fault_contract(
    double_results: object,
    live_results: object = None,
) -> Result[Mapping[str, str]]:
    """Prove the four venue-command fault outcomes match the shared contract.

    ``live_results`` is optional: a missing live demo account does not fail the
    credential-free campaign. When supplied, every shared key must match the
    double and the contract (TN-23; QMX-F062/F063/D008).
    """
    double = _fault_result_map(double_results, "double_results")
    if is_refusal(double):
        return double
    for key, expected in SHARED_FAULT_CONTRACT.items():
        got = double.value.get(key)
        if got != expected:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "double_results",
                    "reason": "conformance double fault outcome diverged from the "
                    "shared live/double contract",
                    "fault": key,
                    "expected": expected,
                    "got": got,
                },
            )
    if live_results is None:
        return Ok(dict(SHARED_FAULT_CONTRACT))
    live = _fault_result_map(live_results, "live_results")
    if is_refusal(live):
        return live
    for key, expected in SHARED_FAULT_CONTRACT.items():
        got = live.value.get(key)
        if got != expected or got != double.value.get(key):
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "live_results",
                    "reason": "live and double fault-contract results disagree",
                    "fault": key,
                    "expected": expected,
                    "double": double.value.get(key),
                    "live": got,
                },
            )
    return Ok(dict(SHARED_FAULT_CONTRACT))


def _fault_result_map(value: object, field: str) -> Result[Mapping[str, str]]:
    if not isinstance(value, Mapping):
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": field,
                "reason": "fault-contract results are a mapping of fault → outcome",
                "given": type(value).__name__,
            },
        )
    body: dict[str, str] = {}
    for key, item in cast("Mapping[object, object]", value).items():
        token = key.value if isinstance(key, StrEnum) else key
        if not isinstance(token, str) or token.strip() == "":
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": field,
                    "reason": "fault-contract keys are fault name strings",
                    "given": repr(key),
                },
            )
        outcome = item.value if isinstance(item, StrEnum) else item
        if not isinstance(outcome, str) or outcome.strip() == "":
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": field,
                    "reason": "fault-contract values are outcome strings",
                    "fault": token,
                    "given": repr(item),
                },
            )
        body[token.strip()] = outcome.strip()
    return Ok(body)


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


def run_port_contract_suite(
    client: object,
    *,
    account: object | None = None,
) -> Result[Mapping[str, object]]:
    """Shared VenueClientPort contract suite for double, replay, and live (Story 24.8).

    Double and replay run on every credential-free CI lane. The credentialed live
    path is an explicit token-gated acceptance that reuses this same suite. A
    capability-key or refusal-shape divergence fails closed (TN-23; SC-13).

    Caller must leave ``client`` ready for ``verify_capabilities`` (session may be
    closed — this suite opens it; live/replay must already hold any injected
    ``VenueFactVerification`` via ``accept_verification``).
    """
    if not isinstance(client, VenueClientPort):
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "client",
                "reason": "port contract suite requires a VenueClientPort",
                "given": type(client).__name__,
            },
        )
    kind = client.kind
    if kind not in {
        VenueClientKind.CONFORMANCE,
        VenueClientKind.REPLAY,
        VenueClientKind.CTRADER,
    }:
        return TypedRefusal(
            category=RefusalCategory.UNSUPPORTED_CAPABILITY,
            retryability=Retryability.NO,
            context={
                "field": "kind",
                "reason": "port contract suite covers conformance | replay | ctrader",
                "kind": getattr(kind, "value", repr(kind)),
            },
        )

    blocked = compound_command_acceptance_blocked()
    if blocked.category is not RefusalCategory.UNSUPPORTED_CAPABILITY:
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "ftr02",
                "reason": "FTR-02 block must remain unsupported-capability",
                "category": blocked.category.value,
            },
        )

    resolved_account: Account
    if account is None:
        minted = Account.try_create("port-contract-acct", client.venue_id, AccountRole.DEMO)
        if is_refusal(minted):
            return minted
        resolved_account = minted.value
    elif isinstance(account, Account):
        if account.venue != client.venue_id:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "account",
                    "reason": "account must belong to the client's VenueId",
                    "venue": client.venue_id.value,
                    "account_venue": account.venue.value,
                },
            )
        resolved_account = account
    else:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "account",
                "reason": "port contract suite binds an Account",
                "given": repr(account),
            },
        )

    opened = client.open_session(resolved_account)
    if is_refusal(opened):
        return opened
    caps = client.verify_capabilities()
    if is_refusal(caps):
        return caps
    profile = caps.value
    missing = sorted(key for key in PORT_CONTRACT_CAPABILITY_KEYS if key not in profile)
    if missing:
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "capability_shape",
                "reason": "capability profile missing required port-contract keys",
                "kind": kind.value,
                "missing": missing,
                "required": sorted(PORT_CONTRACT_CAPABILITY_KEYS),
            },
        )
    if profile.get("verified") is not True:
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "capability_shape",
                "reason": "verified must be True after a successful verify_capabilities",
                "kind": kind.value,
                "verified": profile.get("verified"),
            },
        )
    if profile.get("static_declaration_present") is not True:
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "capability_shape",
                "reason": "static_declaration_present must be True",
                "kind": kind.value,
            },
        )

    submit_shape = _probe_submit_shape(client, resolved_account, kind)
    if is_refusal(submit_shape):
        return submit_shape

    compound_cmd = _compound_probe(client.venue_id, resolved_account)
    if is_refusal(compound_cmd):
        return compound_cmd
    compound = client.submit(compound_cmd.value)
    # Prefer the shared FTR-02 helper when the client short-circuits compounds;
    # otherwise require the same unsupported-capability refusal category.
    if is_ok(compound):
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "compound_command",
                "reason": "compound-command acceptance must stay blocked (FTR-02)",
                "kind": kind.value,
            },
        )
    if compound.category is not RefusalCategory.UNSUPPORTED_CAPABILITY:
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "refusal_shape",
                "reason": "compound-command refusal category diverged from FTR-02",
                "kind": kind.value,
                "expected": RefusalCategory.UNSUPPORTED_CAPABILITY.value,
                "got": compound.category.value,
            },
        )

    observed = client.observations()
    if is_refusal(observed):
        return observed
    reconciled = client.reconcile()
    reconcile_shape = _reconcile_shape(reconciled, kind)
    if is_refusal(reconcile_shape):
        return reconcile_shape

    closed = client.close_session()
    if is_refusal(closed):
        return closed

    return Ok(
        {
            "kind": kind.value,
            "compound_command": "blocked-ftr02",
            "capability_keys": sorted(
                key for key in profile if key in PORT_CONTRACT_CAPABILITY_KEYS
            ),
            "capability_verified": True,
            "submit_shape": dict(submit_shape.value),
            "reconcile_shape": dict(reconcile_shape.value),
            "observation_count": len(observed.value),
        }
    )


def compare_port_contract_shapes(
    shapes: object,
) -> Result[Mapping[str, object]]:
    """Fail when capability keys or refusal shapes diverge across implementations."""
    if not isinstance(shapes, Mapping):
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "shapes",
                "reason": "compare_port_contract_shapes takes a non-empty "
                "kind → suite-result mapping",
                "given": type(shapes).__name__,
            },
        )
    incoming = cast("Mapping[object, object]", shapes)
    if not incoming:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "shapes",
                "reason": "compare_port_contract_shapes takes a non-empty "
                "kind → suite-result mapping",
                "given": "empty-mapping",
            },
        )
    normalized: dict[str, Mapping[str, object]] = {}
    for key, value in incoming.items():
        kind_token: object = key.value if isinstance(key, VenueClientKind) else key
        if not isinstance(kind_token, str) or kind_token.strip() == "":
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "shapes",
                    "reason": "shape keys are VenueClientKind or kind value strings",
                    "given": repr(key),
                },
            )
        if not isinstance(value, Mapping):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "shapes",
                    "reason": "each shape value is a port-contract suite result mapping",
                    "kind": kind_token,
                    "given": type(value).__name__,
                },
            )
        normalized[kind_token.strip()] = cast("Mapping[str, object]", value)

    capability_sets = {
        kind: frozenset(_string_list(result.get("capability_keys")))
        for kind, result in normalized.items()
    }
    reference_keys: frozenset[str] | None = None
    for kind, keys in capability_sets.items():
        if not PORT_CONTRACT_CAPABILITY_KEYS.issubset(keys):
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "capability_shape",
                    "reason": "capability keys diverge from the shared port contract",
                    "kind": kind,
                    "missing": sorted(PORT_CONTRACT_CAPABILITY_KEYS - keys),
                },
            )
        if reference_keys is None:
            reference_keys = keys
        elif keys != reference_keys:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "capability_shape",
                    "reason": "capability-key sets diverge across VenueClientPort implementations",
                    "kind": kind,
                    "expected": sorted(reference_keys),
                    "got": sorted(keys),
                },
            )

    for kind, result in normalized.items():
        if result.get("compound_command") != "blocked-ftr02":
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "refusal_shape",
                    "reason": "compound-command refusal shape diverged",
                    "kind": kind,
                    "got": result.get("compound_command"),
                },
            )
        submit_shape = result.get("submit_shape")
        if not isinstance(submit_shape, Mapping):
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "refusal_shape",
                    "reason": "submit_shape missing from suite result",
                    "kind": kind,
                },
            )
        expected = _expected_submit_shape(kind)
        got_shape = dict(cast("Mapping[str, object]", submit_shape))
        if got_shape != expected:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "refusal_shape",
                    "reason": "submit refusal/outcome shape diverged from the kind's port contract",
                    "kind": kind,
                    "expected": expected,
                    "got": got_shape,
                },
            )

    return Ok(
        {
            "compared": sorted(normalized),
            "capability_keys": sorted(reference_keys or ()),
            "parity": True,
        }
    )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in cast("Sequence[object]", value) if isinstance(item, str)]


def _expected_submit_shape(kind: str) -> dict[str, object]:
    if kind == VenueClientKind.REPLAY.value:
        return {
            "form": "refusal",
            "category": RefusalCategory.POLICY_REJECTION.value,
        }
    if kind == VenueClientKind.CONFORMANCE.value:
        return {
            "form": "outcome",
            "outcome": SubmissionOutcome.ACCEPTED_BY_VENUE.value,
        }
    # Live cTrader: credential-free path refuses wire handoff (no auto-retry).
    return {
        "form": "refusal",
        "category": RefusalCategory.UNSUPPORTED_CAPABILITY.value,
    }


def _probe_submit_shape(
    client: VenueClientPort,
    account: Account,
    kind: VenueClientKind,
) -> Result[Mapping[str, object]]:
    command = Command.cancel_order(
        client.venue_id,
        account,
        "port-contract-session",
        1,
        "order-port-contract",
    )
    if is_refusal(command):
        return command
    if kind is VenueClientKind.CONFORMANCE and isinstance(client, ConformanceDouble):
        armed = client.arm(ConformanceCase.SUCCESS)
        if is_refusal(armed):
            return armed
    submitted = client.submit(command.value)
    if kind is VenueClientKind.REPLAY:
        if not is_refusal(submitted):
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "refusal_shape",
                    "reason": "replay submit must be a typed policy refusal",
                    "kind": kind.value,
                },
            )
        if submitted.category is not RefusalCategory.POLICY_REJECTION:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "refusal_shape",
                    "reason": "replay submit refusal category diverged",
                    "expected": RefusalCategory.POLICY_REJECTION.value,
                    "got": submitted.category.value,
                },
            )
        return Ok(
            {
                "form": "refusal",
                "category": submitted.category.value,
            }
        )
    if kind is VenueClientKind.CONFORMANCE:
        if is_refusal(submitted):
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "refusal_shape",
                    "reason": "conformance success case must yield a SubmissionResult",
                    "category": submitted.category.value,
                },
            )
        return Ok(
            {
                "form": "outcome",
                "outcome": submitted.value.outcome.value,
            }
        )
    # Live: expect a typed refusal (wire handoff not invented) — never an auto-accept.
    if not is_refusal(submitted):
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "refusal_shape",
                "reason": "live credential-free submit must not invent an accepted "
                "outcome; expected a typed refusal",
                "kind": kind.value,
            },
        )
    return Ok(
        {
            "form": "refusal",
            "category": submitted.category.value,
        }
    )


def _reconcile_shape(
    reconciled: Result[Reconciliation],
    kind: VenueClientKind,
) -> Result[Mapping[str, object]]:
    if kind is VenueClientKind.CTRADER:
        # Live reconcile stays FTR-01-blocked until position/balance mapping lands.
        if not is_refusal(reconciled):
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "reconcile_shape",
                    "reason": "live reconcile must remain FTR-01 unsupported-capability "
                    "until position/balance CT-13 mapping lands",
                    "kind": kind.value,
                },
            )
        if reconciled.category is not RefusalCategory.UNSUPPORTED_CAPABILITY:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "reconcile_shape",
                    "reason": "live reconcile refusal category diverged",
                    "expected": RefusalCategory.UNSUPPORTED_CAPABILITY.value,
                    "got": reconciled.category.value,
                },
            )
        return Ok(
            {
                "form": "refusal",
                "category": reconciled.category.value,
                "ftr": reconciled.context.get("ftr"),
            }
        )
    if is_refusal(reconciled):
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "reconcile_shape",
                "reason": "double/replay reconcile must succeed in the shared suite",
                "kind": kind.value,
                "category": reconciled.category.value,
            },
        )
    return Ok(
        {
            "form": "verdict",
            "verdict": reconciled.value.verdict.value,
        }
    )


def _compound_probe(venue_id: VenueId, account: Account) -> Result[CompoundCommand]:
    """Minimal compound probe — acceptance stays FTR-02 blocked on every port."""
    parent = Command.cancel_order(
        venue_id,
        account,
        "port-contract-compound",
        99,
        "order-compound-parent",
    )
    if is_refusal(parent):
        return parent
    return CompoundCommand.fan_out(parent.value, (0, 1))
