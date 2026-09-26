"""Paper-milestone injected money-path failure campaign (Story 28.3).

Drives timeout, transport-error, disconnect, superseded-by-fill, reconnect-gap,
unpersistable identity, queue-bound, and protective-stop-capability faults
through the FEAT-0023 conformance double plus the node order / UNKNOWN /
protection / capital / reconcile seams. No live demo account is required.
FTR-07: the campaign invents no KSA matrix values or latency gates.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, TypeVar, cast

from qmf.core import (
    Account,
    AccountRole,
    CalendarIdentity,
    Duration,
    ExactRational,
    Fingerprint,
    Instant,
    Instrument,
    Money,
    MonotonicReading,
    Ok,
    Price,
    PriceDelta,
    Quantity,
    RefusalCategory,
    Result,
    SecretRef,
    SinkAck,
    SinkResult,
    TypedRefusal,
    UnitKind,
    VenueId,
    World,
    fingerprint,
    is_refusal,
    unpersistable,
)
from qmf.risk.control_action import (
    AuthorityKind,
    CommandStreamKey,
    EnforcementScope,
    SubjectScope,
    mint_control_action,
)
from qmf.risk.control_rank import ControlActionKind, ControlRankRow, ControlRankTable
from qmf.risk.control_window import (
    ControlWindowRevisionLog,
    CurrencyExposureRecord,
    FeedQuadruple,
    ProposedWindowAct,
    WindowBounds,
    WindowKind,
    mint_control_window,
    resolve_instrument_scope,
)
from qmf.risk.exit_record import (
    CloseOutcome,
    CloseReason,
    ClosingAuthority,
    ExitRecord,
    ExitResultLabel,
    mint_exit_record,
)
from qmf.risk.paper import BookMode, ExecutionTarget, SeatState

from qmn.capital import (
    apply_bench_crossing,
    apply_kill_line_breach,
    evaluate_kill_line,
    evaluate_qualifying_loss_bench,
    originate_breakeven_ratchet,
    refuse_invented_kill_line_floor,
)
from qmn.host._refuse import invalid, policy
from qmn.mis.signal_snapshot import sqs_baseline_key
from qmn.order import (
    CommandIdentityBinder,
    CommandStreamUnknownBoundary,
    ConnectionCommandPacer,
    HeldProtectionAct,
    ReadbackClarity,
    ResolvePath,
    decide_resolve_path,
    require_venue_resident_protective_stop,
    unknown_never_rejection,
)
from qmn.order.unknown import ProtectionIntentExtent as UnknownIntentExtent
from qmn.protection import (
    DispatchCandidate,
    KsaEnforcementScope,
    KsaLevel,
    KsaTriggerClass,
    NewsRevisionDisposition,
    allow_protective_act_under_windows,
    dispatch_ranked_controls,
    enforce_entry_at_book_door,
    fold_ksa_level,
    matrix_supplies_no_default_values,
    mint_escalation,
    mint_level_epoch,
    resume,
    stream_blocked_by_escalation,
)
from qmn.protection.windows import apply_news_revision
from qmn.reconcile import (
    FOUR_VERDICTS,
    DriftResponseKind,
    LookbackStatus,
    ReadbackStatus,
    ReconciliationTrigger,
    apply_drift_response,
    build_equity_narrative,
    refuse_equity_difference,
    run_reconciliation,
)
from qmn.time import VpsClock
from qmn.venue import (
    INJECTED_COMMAND_FAULTS,
    SHARED_FAULT_CONTRACT,
    AdmissionDisposition,
    Command,
    ConformanceDouble,
    ConnectionManager,
    InjectedFault,
    OrderParameters,
    OrderType,
    ReconciliationVerdict,
    ReconnectGapRecovery,
    ReconnectPhase,
    RecoveredObservation,
    SubmissionOutcome,
    TimeInForce,
    VenueClientKind,
    agree_live_and_double_fault_contract,
    run_conformance_suite,
    venue_writer_id,
)

__all__ = [
    "DESIGNED_DEGRADED_STATES",
    "FAILURE_CAMPAIGN_CLASS",
    "FAILURE_CAMPAIGN_FORMAT_VERSION",
    "FAILURE_CAMPAIGN_SURFACE",
    "INJECTED_COMMAND_FAULTS",
    "INVENTS_KSA_OR_LATENCY",
    "PROTECTION_COINCIDENCE_FIXTURES",
    "REQUIRES_LIVE_DEMO_ACCOUNT",
    "SHARED_FAULT_CONTRACT",
    "FailureCampaignInputs",
    "FailureCampaignReport",
    "refuse_invented_ksa_or_latency_number",
    "refuse_live_demo_account_required",
    "run_paper_milestone_failure_campaign",
]

T = TypeVar("T")

FAILURE_CAMPAIGN_SURFACE: Final[str] = "qmn.host.failure_campaign"
FAILURE_CAMPAIGN_CLASS: Final[str] = "paper-milestone-failure-campaign"
FAILURE_CAMPAIGN_FORMAT_VERSION: Final[int] = 1
REQUIRES_LIVE_DEMO_ACCOUNT: Final[bool] = False
INVENTS_KSA_OR_LATENCY: Final[bool] = False

PROTECTION_COINCIDENCE_FIXTURES: Final[tuple[str, ...]] = (
    "ksa",
    "kill-line",
    "news",
    "dead-zone",
    "sqs",
    "ad-37",
)

DESIGNED_DEGRADED_STATES: Final[Mapping[str, str]] = MappingProxyType(
    {
        InjectedFault.TIMEOUT.value: "unknown-stream-block",
        InjectedFault.TRANSPORT_ERROR.value: "unknown-stream-block",
        InjectedFault.DISCONNECT.value: "unknown-stream-block",
        InjectedFault.SUPERSEDED_BY_FILL.value: "rejected-by-venue-named-outcome",
        InjectedFault.RECONNECT_GAP.value: "fills-persisted-before-healthy",
        InjectedFault.UNPERSISTABLE_IDENTITY.value: "submission-blocked",
        InjectedFault.QUEUE_BOUND.value: "denied-locally",
        InjectedFault.PROTECTIVE_STOP_CAPABILITY.value: ("unsupported-capability-entry-refused"),
    }
)

_ID_INVENTED = "failure_campaign.invented_ksa_or_latency"
_ID_LIVE_ACCOUNT = "failure_campaign.live_demo_account"
_ID_VENUE = "failure_campaign.venue"
_ID_INPUTS = "failure_campaign.inputs"
_ID_INJECTION = "failure_campaign.incomplete_injection"
_ID_CONTRACT = "failure_campaign.live_double_divergence"
_ID_SQS = "failure_campaign.demo_sqs_satisfies_live"
_ID_EQUITY = "failure_campaign.equity_difference"
_ID_FLOOR = "failure_campaign.invented_kill_line_floor"

_MACHINE: Final[str] = "vps-28-3"
_ADAPTER: Final[str] = "conformance-double"
_BOOT: Final[str] = "boot-28-3"
_SESSION: Final[str] = "session-28-3"


@dataclass(frozen=True, slots=True)
class FailureCampaignInputs:
    """Injected clock, conformance double, and Book-declared numeric fixtures."""

    clock: VpsClock
    venue: ConformanceDouble
    kill_line_capital_floor: Money
    qualifying_loss_threshold: ExactRational
    bench_consecutive_loss_threshold: int
    breakeven_ratchet_trigger: ExactRational
    live_fault_results: Mapping[str, str] | None = None
    require_live_demo_account: bool = False
    invent_ksa_matrix_values: bool = False
    invent_latency_gate: bool = False
    claim_demo_sqs_satisfies_live: bool = False
    subtract_venue_from_virtual_equity: bool = False


@dataclass(frozen=True, slots=True)
class FailureCampaignReport:
    """Fingerprinted proof of the Story 28.3 injected-fault campaign."""

    format_version: int
    fingerprint: Fingerprint
    injected_faults: tuple[str, ...]
    degraded_states: Mapping[str, str]
    unknown_blocks_one_stream: bool
    protective_intents_survive: bool
    fills_persist_before_healthy: bool
    commands_retried: int
    unprotected_entries_refused: bool
    live_double_contract_agrees: bool
    live_demo_account_required: bool
    invents_ksa_or_latency: bool
    protection_coincidence: Mapping[str, object]
    reconciliation: Mapping[str, object]
    ksa_matrix_values_supplied: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": FAILURE_CAMPAIGN_CLASS,
            "commands_retried": self.commands_retried,
            "degraded_states": dict(self.degraded_states),
            "fills_persist_before_healthy": self.fills_persist_before_healthy,
            "format_version": self.format_version,
            "injected_faults": list(self.injected_faults),
            "invents_ksa_or_latency": self.invents_ksa_or_latency,
            "ksa_matrix_values_supplied": self.ksa_matrix_values_supplied,
            "live_demo_account_required": self.live_demo_account_required,
            "live_double_contract_agrees": self.live_double_contract_agrees,
            "protection_coincidence": dict(self.protection_coincidence),
            "protective_intents_survive": self.protective_intents_survive,
            "reconciliation": dict(self.reconciliation),
            "surface": FAILURE_CAMPAIGN_SURFACE,
            "unknown_blocks_one_stream": self.unknown_blocks_one_stream,
            "unprotected_entries_refused": self.unprotected_entries_refused,
        }

    def as_mapping(self) -> Mapping[str, object]:
        body = self.fp1_identity()
        body["fingerprint"] = self.fingerprint.value
        return MappingProxyType(body)


def refuse_invented_ksa_or_latency_number(**extra: object) -> TypedRefusal:
    """FTR-07: the campaign never fills KSA matrix values or latency gates."""
    return policy(
        "invented-value",
        "KSA matrix values remain a pre-soak operator ratification and numeric "
        "hot-path/latency gates remain unset until measured baselines exist; "
        "the failure campaign invents neither (FTR-07)",
        failure_id=_ID_INVENTED,
        **extra,
    )


def refuse_live_demo_account_required(**extra: object) -> TypedRefusal:
    """Story 28.3 does not require a live demo account."""
    return policy(
        "live_demo_account",
        "injected money-path proofs run on the FEAT-0023 conformance double; "
        "a live demo account is not a Story 28.3 prerequisite",
        failure_id=_ID_LIVE_ACCOUNT,
        **extra,
    )


def run_paper_milestone_failure_campaign(
    inputs: object,
) -> Result[FailureCampaignReport]:
    """Inject the named faults and fold every designed degraded state."""
    if not isinstance(inputs, FailureCampaignInputs):
        return invalid(
            "inputs",
            "the failure campaign takes FailureCampaignInputs",
            given=type(inputs).__name__,
            failure_id=_ID_INPUTS,
        )
    if inputs.require_live_demo_account is True:
        return refuse_live_demo_account_required()
    if inputs.invent_ksa_matrix_values is True or inputs.invent_latency_gate is True:
        return refuse_invented_ksa_or_latency_number(
            invent_ksa_matrix_values=inputs.invent_ksa_matrix_values,
            invent_latency_gate=inputs.invent_latency_gate,
        )
    if inputs.claim_demo_sqs_satisfies_live is True:
        return policy(
            "sqs",
            "a demo-conditioned SQS baseline never satisfies a role=live binding",
            failure_id=_ID_SQS,
        )
    if inputs.subtract_venue_from_virtual_equity is True:
        differenced = refuse_equity_difference(None, None)
        if is_refusal(differenced):
            return policy(
                "equity_difference",
                "venue equity is never subtracted from virtual-ledger equity",
                failure_id=_ID_EQUITY,
            )
    venue = inputs.venue
    if venue.kind is not VenueClientKind.CONFORMANCE:
        return policy(
            "venue",
            "Story 28.3 injects through the FEAT-0023 conformance double, never live or replay",
            given=venue.kind.value,
            failure_id=_ID_VENUE,
        )

    now = _unwrap(inputs.clock.wall_now())
    if isinstance(now, TypedRefusal):
        return now
    fx = _Fixtures(clock=inputs.clock, venue=venue, now=now)

    account = _unwrap(_account(fx.venue_id, "acct-demo", AccountRole.DEMO))
    if isinstance(account, TypedRefusal):
        return account
    suite = _unwrap(run_conformance_suite(venue))
    if isinstance(suite, TypedRefusal):
        return suite
    contract = _unwrap(agree_live_and_double_fault_contract(suite, inputs.live_fault_results))
    if isinstance(contract, TypedRefusal):
        context = dict(contract.context)
        context["failure_id"] = _ID_CONTRACT
        return TypedRefusal(
            category=contract.category,
            retryability=contract.retryability,
            context=context,
            after_condition_descriptor=contract.after_condition_descriptor,
        )

    # The suite closes the session; re-open for injected fault drives.
    opened = venue.open_session(account)
    if is_refusal(opened):
        return _as_refusal(opened)
    caps = venue.verify_capabilities()
    if is_refusal(caps):
        return _as_refusal(caps)

    command_proof = _unwrap(_exercise_command_faults(fx, account))
    if isinstance(command_proof, TypedRefusal):
        return command_proof
    protection = _unwrap(_exercise_protection_coincidence(fx, inputs))
    if isinstance(protection, TypedRefusal):
        return protection
    reconcile = _unwrap(_exercise_reconciliation(fx, venue))
    if isinstance(reconcile, TypedRefusal):
        return reconcile

    degraded = _str_str_map(command_proof["degraded_states"])
    missing = [fault.value for fault in INJECTED_COMMAND_FAULTS if fault.value not in degraded]
    if missing:
        return policy(
            "injected_faults",
            "every named money-path fault must resolve to its documented degraded state",
            missing=missing,
            failure_id=_ID_INJECTION,
        )
    retried_raw = command_proof["commands_retried"]
    retried = retried_raw if isinstance(retried_raw, int) else 0
    protection_map = _obj_map(protection)
    reconcile_map = _obj_map(reconcile)

    identity = {
        "class": FAILURE_CAMPAIGN_CLASS,
        "commands_retried": retried,
        "degraded_states": dict(degraded),
        "fills_persist_before_healthy": command_proof["fills_persist_before_healthy"],
        "format_version": FAILURE_CAMPAIGN_FORMAT_VERSION,
        "injected_faults": [fault.value for fault in INJECTED_COMMAND_FAULTS],
        "invents_ksa_or_latency": INVENTS_KSA_OR_LATENCY,
        "ksa_matrix_values_supplied": False,
        "live_demo_account_required": REQUIRES_LIVE_DEMO_ACCOUNT,
        "live_double_contract_agrees": True,
        "protection_coincidence": protection_map,
        "protective_intents_survive": command_proof["protective_intents_survive"],
        "reconciliation": reconcile_map,
        "surface": FAILURE_CAMPAIGN_SURFACE,
        "unknown_blocks_one_stream": command_proof["unknown_blocks_one_stream"],
        "unprotected_entries_refused": command_proof["unprotected_entries_refused"],
    }
    stamped = fingerprint(identity)
    if is_refusal(stamped):
        return _as_refusal(stamped)
    return Ok(
        FailureCampaignReport(
            format_version=FAILURE_CAMPAIGN_FORMAT_VERSION,
            fingerprint=stamped.value,
            injected_faults=tuple(fault.value for fault in INJECTED_COMMAND_FAULTS),
            degraded_states=MappingProxyType(degraded),
            unknown_blocks_one_stream=command_proof["unknown_blocks_one_stream"] is True,
            protective_intents_survive=command_proof["protective_intents_survive"] is True,
            fills_persist_before_healthy=command_proof["fills_persist_before_healthy"] is True,
            commands_retried=retried,
            unprotected_entries_refused=command_proof["unprotected_entries_refused"] is True,
            live_double_contract_agrees=True,
            live_demo_account_required=REQUIRES_LIVE_DEMO_ACCOUNT,
            invents_ksa_or_latency=INVENTS_KSA_OR_LATENCY,
            protection_coincidence=MappingProxyType(protection_map),
            reconciliation=MappingProxyType(reconcile_map),
            ksa_matrix_values_supplied=False,
        )
    )


def _unwrap(result: Result[T]) -> T | TypedRefusal:
    if isinstance(result, TypedRefusal):
        return result
    return result.value


def _as_refusal(result: object) -> TypedRefusal:
    if isinstance(result, TypedRefusal):
        return result
    return invalid("internal", "expected a typed refusal", given=type(result).__name__)


def _str_str_map(value: object) -> dict[str, str]:
    body: dict[str, str] = {}
    if not isinstance(value, Mapping):
        return body
    for key, item in cast("Mapping[object, object]", value).items():
        if isinstance(key, str) and isinstance(item, str):
            body[key] = item
    return body


def _obj_map(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): item for key, item in cast("Mapping[object, object]", value).items()}


@dataclass(frozen=True, slots=True)
class _Fixtures:
    clock: VpsClock
    venue: ConformanceDouble
    now: Instant

    @property
    def venue_id(self) -> VenueId:
        return self.venue.venue_id


class _SecretStore:
    def read(self, ref: object, /) -> Result[object]:
        del ref
        return unpersistable("no such credential")

    def atomic_replace(self, ref: object, new_value: object, /) -> Result[object]:
        del new_value
        return Ok(ref)


class _ObsSink:
    def __init__(self) -> None:
        self.emitted: list[object] = []

    def emit(self, observation: object, /) -> SinkResult:
        self.emitted.append(observation)
        return Ok(SinkAck())


class _JournalSink:
    def __init__(self) -> None:
        self.appended: list[object] = []

    def append(self, event: object, /) -> SinkResult:
        self.appended.append(event)
        return Ok(SinkAck())


class _RecordSink:
    def write(self, record: object, /) -> SinkResult:
        del record
        return Ok(SinkAck())


class _FailingRecordSink:
    def write(self, record: object, /) -> SinkResult:
        del record
        return unpersistable("command identity store unavailable")


def _account(venue: VenueId, account_id: str, role: AccountRole) -> Result[Account]:
    return Account.try_create(account_id, venue, role)


def _instrument(venue: VenueId, symbol: str = "EURUSD") -> Result[Instrument]:
    return Instrument.try_create(venue, symbol)


def _money(value: int) -> Result[Money]:
    return Money.try_create(value, "USD", 2)


def _qty(value: int) -> Result[Quantity]:
    return Quantity.try_create(value, "lot", 2)


def _fp(seed: str) -> Result[Fingerprint]:
    return fingerprint({"class": "failure-campaign", "seed": seed})


def _duration(ns: int) -> Result[Duration]:
    return Duration.try_create(ns)


def _mono(ns: int) -> Result[MonotonicReading]:
    return MonotonicReading.try_create(ns, _BOOT)


def _params(venue: VenueId, *, with_stop: bool) -> Result[OrderParameters]:
    instrument = _instrument(venue)
    if is_refusal(instrument):
        return _as_refusal(instrument)
    qty = _qty(100)
    if is_refusal(qty):
        return _as_refusal(qty)
    kwargs: dict[str, object] = {}
    if with_stop:
        delta = PriceDelta.try_create(100, instrument.value, 5)
        if is_refusal(delta):
            return _as_refusal(delta)
        kwargs["protective_stop_distance"] = delta.value
    return OrderParameters.try_create(
        OrderType.MARKET, TimeInForce.GOOD_TILL_CANCEL, qty.value, **kwargs
    )


def _place(
    venue: VenueId, account: Account, ordinal: int, *, with_stop: bool = True
) -> Result[Command]:
    params = _params(venue, with_stop=with_stop)
    if is_refusal(params):
        return _as_refusal(params)
    return Command.place_order(venue, account, _SESSION, ordinal, params.value)


def _cancel(venue: VenueId, account: Account, ordinal: int) -> Result[Command]:
    return Command.cancel_order(venue, account, _SESSION, ordinal, "ord-1")


def _boundary(
    venue: VenueId, account: Account
) -> Result[tuple[CommandStreamUnknownBoundary, ConnectionManager]]:
    writer = venue_writer_id(_MACHINE, _ADAPTER, venue, account, _BOOT)
    if is_refusal(writer):
        return _as_refusal(writer)
    manager = ConnectionManager.try_create(
        writer.value, _SecretStore(), _ObsSink(), _JournalSink(), _RecordSink()
    )
    if is_refusal(manager):
        return _as_refusal(manager)
    extent = UnknownIntentExtent.try_create(8)
    if is_refusal(extent):
        return _as_refusal(extent)
    boundary = CommandStreamUnknownBoundary.try_create(
        venue_id=venue,
        account=account,
        connection_manager=manager.value,
        extent=extent.value,
    )
    if is_refusal(boundary):
        return _as_refusal(boundary)
    return Ok((boundary.value, manager.value))


def _exercise_command_faults(fx: _Fixtures, demo: Account) -> Result[Mapping[str, object]]:
    venue = fx.venue
    degraded: dict[str, str] = {}

    unknown_triggers = (
        InjectedFault.TIMEOUT,
        InjectedFault.TRANSPORT_ERROR,
        InjectedFault.DISCONNECT,
    )
    for index, fault in enumerate(unknown_triggers, start=1):
        injected = venue.inject(fault)
        if is_refusal(injected):
            return _as_refusal(injected)
        command = _cancel(fx.venue_id, demo, index)
        if is_refusal(command):
            return _as_refusal(command)
        submitted = venue.submit(command.value)
        if is_refusal(submitted):
            return _as_refusal(submitted)
        if submitted.value.outcome is not SubmissionOutcome.UNKNOWN:
            return policy(
                "unknown",
                "timeout, transport-error, and disconnect mint UNKNOWN, never a rejection",
                fault=fault.value,
                outcome=submitted.value.outcome.value,
                failure_id=_ID_INJECTION,
            )
        if not unknown_never_rejection(submitted.value.outcome):
            return policy(
                "unknown",
                "UNKNOWN is a state, never a rejection",
                failure_id=_ID_INJECTION,
            )
        degraded[fault.value] = DESIGNED_DEGRADED_STATES[fault.value]

    other = _unwrap(_account(fx.venue_id, "acct-other", AccountRole.DEMO))
    if isinstance(other, TypedRefusal):
        return other
    blocked_pair = _unwrap(_boundary(fx.venue_id, demo))
    if isinstance(blocked_pair, TypedRefusal):
        return blocked_pair
    open_pair = _unwrap(_boundary(fx.venue_id, other))
    if isinstance(open_pair, TypedRefusal):
        return open_pair
    blocked_boundary, _blocked_cm = blocked_pair
    open_boundary, _open_cm = open_pair
    disconnect = venue.inject(InjectedFault.DISCONNECT)
    if is_refusal(disconnect):
        return _as_refusal(disconnect)
    unknown_cmd = _cancel(fx.venue_id, demo, 20)
    if is_refusal(unknown_cmd):
        return _as_refusal(unknown_cmd)
    unknown_sub = venue.submit(unknown_cmd.value)
    if is_refusal(unknown_sub):
        return _as_refusal(unknown_sub)
    recorded = blocked_boundary.record_unknown(unknown_sub.value)
    if is_refusal(recorded):
        return _as_refusal(recorded)
    place_blocked = _place(fx.venue_id, demo, 21)
    if is_refusal(place_blocked):
        return _as_refusal(place_blocked)
    admitted_blocked = blocked_boundary.admit(place_blocked.value, receive_instant=fx.now)
    if is_refusal(admitted_blocked):
        return _as_refusal(admitted_blocked)
    blocked_result = admitted_blocked.value
    if getattr(blocked_result, "disposition", None) is not AdmissionDisposition.REFUSED:
        return policy(
            "unknown",
            "UNKNOWN must refuse new entries on the affected stream",
            failure_id=_ID_INJECTION,
        )
    protect = _cancel(fx.venue_id, demo, 22)
    if is_refusal(protect):
        return _as_refusal(protect)
    held = blocked_boundary.admit(protect.value, receive_instant=fx.now)
    if is_refusal(held):
        return _as_refusal(held)
    if not isinstance(held.value, HeldProtectionAct):
        return policy(
            "unknown",
            "a protective act under UNKNOWN is held as a standing intent",
            given=type(held.value).__name__,
            failure_id=_ID_INJECTION,
        )
    place_open = _place(fx.venue_id, other, 23)
    if is_refusal(place_open):
        return _as_refusal(place_open)
    admitted_open = open_boundary.admit(place_open.value, receive_instant=fx.now)
    if is_refusal(admitted_open):
        return _as_refusal(admitted_open)
    open_result = admitted_open.value
    if getattr(open_result, "disposition", None) is not AdmissionDisposition.ADMITTED:
        return policy(
            "unknown",
            "UNKNOWN blocks exactly one (VenueId, account) stream",
            failure_id=_ID_INJECTION,
        )
    unknown_one_stream = blocked_boundary.stream_open is False and open_boundary.stream_open is True
    protective_survive = held.value.disposition.value == "held"

    superseded = venue.inject(InjectedFault.SUPERSEDED_BY_FILL)
    if is_refusal(superseded):
        return _as_refusal(superseded)
    supersede_cmd = _cancel(fx.venue_id, demo, 30)
    if is_refusal(supersede_cmd):
        return _as_refusal(supersede_cmd)
    supersede_sub = venue.submit(supersede_cmd.value)
    if is_refusal(supersede_sub):
        return _as_refusal(supersede_sub)
    if supersede_sub.value.outcome is not SubmissionOutcome.REJECTED_BY_VENUE:
        return policy(
            "superseded_by_fill",
            "superseded-by-fill is a named rejected-by-venue outcome, never UNKNOWN",
            outcome=supersede_sub.value.outcome.value,
            failure_id=_ID_INJECTION,
        )
    degraded[InjectedFault.SUPERSEDED_BY_FILL.value] = DESIGNED_DEGRADED_STATES[
        InjectedFault.SUPERSEDED_BY_FILL.value
    ]

    gap = venue.inject(InjectedFault.RECONNECT_GAP)
    if is_refusal(gap):
        return _as_refusal(gap)
    cred = SecretRef.try_create("cred-ref-28-3")
    if is_refusal(cred):
        return _as_refusal(cred)
    obs = _ObsSink()
    journal = _JournalSink()
    recovered_raw = venue.gap_recovered_observations()
    recovered: list[RecoveredObservation] = []
    for item in recovered_raw:
        payload_raw = item["payload"]
        payload: dict[str, object] = (
            dict(cast("Mapping[str, object]", payload_raw))
            if isinstance(payload_raw, Mapping)
            else {}
        )
        wall_raw = item["receive_wall_ns"]
        wall_ns = wall_raw if isinstance(wall_raw, int) else 0
        exec_raw = item.get("execution_id")
        recovered.append(
            RecoveredObservation(
                observation_id=str(item["observation_id"]),
                kind=str(item["kind"]),
                receive_wall_ns=wall_ns,
                payload=payload,
                execution_id=str(exec_raw) if exec_raw is not None else None,
            )
        )
    recovery = ReconnectGapRecovery.try_create(
        client=venue,
        credential_ref=cred.value,
        observation_sink=obs,
        journal_sink=journal,
    )
    if is_refusal(recovery):
        return _as_refusal(recovery)
    report = recovery.value.run(recovered=recovered, outstanding_command_ids=("cmd-a",))
    if is_refusal(report):
        return _as_refusal(report)
    if (
        report.value.healthy is not True
        or ReconnectPhase.PERSIST_RECOVERED not in report.value.phases_completed
    ):
        return policy(
            "reconnect_gap",
            "reconnect gap recovery must persist fills before healthy",
            failure_id=_ID_INJECTION,
        )
    if report.value.commands_resubmitted != 0:
        return policy(
            "reconnect_gap",
            "reconnect never resubmits a command",
            commands_resubmitted=report.value.commands_resubmitted,
            failure_id=_ID_INJECTION,
        )
    if len(obs.emitted) < 1:
        return policy(
            "reconnect_gap",
            "recovered fills must persist before healthy",
            failure_id=_ID_INJECTION,
        )
    degraded[InjectedFault.RECONNECT_GAP.value] = DESIGNED_DEGRADED_STATES[
        InjectedFault.RECONNECT_GAP.value
    ]

    identity_fault = venue.inject(InjectedFault.UNPERSISTABLE_IDENTITY)
    if is_refusal(identity_fault):
        return _as_refusal(identity_fault)
    if venue.identity_persistable is not False:
        return policy(
            "unpersistable_identity",
            "the double must script unpersistable identity",
            failure_id=_ID_INJECTION,
        )
    binder = CommandIdentityBinder.try_create(_FailingRecordSink(), injective_total=False)
    if is_refusal(binder):
        return _as_refusal(binder)
    identity_cmd = _cancel(fx.venue_id, demo, 40)
    if is_refusal(identity_cmd):
        return _as_refusal(identity_cmd)
    bound = binder.value.bind_before_wire_handoff(identity_cmd.value)
    if not is_refusal(bound) or bound.category is not RefusalCategory.STORAGE_FAILURE:
        return policy(
            "unpersistable_identity",
            "unpersistable identity blocks submission before handoff",
            failure_id=_ID_INJECTION,
        )
    degraded[InjectedFault.UNPERSISTABLE_IDENTITY.value] = DESIGNED_DEGRADED_STATES[
        InjectedFault.UNPERSISTABLE_IDENTITY.value
    ]

    queue_fault = venue.inject(InjectedFault.QUEUE_BOUND)
    if is_refusal(queue_fault):
        return _as_refusal(queue_fault)
    bound_ns = _duration(1_000_000)
    if is_refusal(bound_ns):
        return _as_refusal(bound_ns)
    pacer = ConnectionCommandPacer.try_create(
        local_queue_bound=bound_ns.value,
        protective_reserve_capacity=1,
        general_capacity=1,
    )
    if is_refusal(pacer):
        return _as_refusal(pacer)
    queue_cmd = _cancel(fx.venue_id, demo, 50)
    if is_refusal(queue_cmd):
        return _as_refusal(queue_cmd)
    enqueued = pacer.value.enqueue(queue_cmd.value)
    if is_refusal(enqueued):
        return _as_refusal(enqueued)
    enq = _unwrap(_mono(0))
    if isinstance(enq, TypedRefusal):
        return enq
    later = _unwrap(_mono(50_000_000))
    if isinstance(later, TypedRefusal):
        return later
    queue_refused = pacer.value.admit(queue_cmd.value, enqueued_at=enq, now=later)
    if not is_refusal(queue_refused):
        return policy(
            "queue_bound",
            "a local queue-bound breach is a door refusal, never UNKNOWN",
            failure_id=_ID_INJECTION,
        )
    if queue_refused.context.get("outcome") != "denied-locally":
        return policy(
            "queue_bound",
            "queue-bound breach is denied-locally on the pacer veto path",
            failure_id=_ID_INJECTION,
        )
    if queue_refused.category is RefusalCategory.TRANSIENT_VENUE_FAILURE:
        return policy(
            "queue_bound",
            "queue-bound breach must never mint UNKNOWN",
            failure_id=_ID_INJECTION,
        )
    degraded[InjectedFault.QUEUE_BOUND.value] = DESIGNED_DEGRADED_STATES[
        InjectedFault.QUEUE_BOUND.value
    ]

    stop_fault = venue.inject(InjectedFault.PROTECTIVE_STOP_CAPABILITY)
    if is_refusal(stop_fault):
        return _as_refusal(stop_fault)
    stop_cmd = _place(fx.venue_id, demo, 60, with_stop=True)
    if is_refusal(stop_cmd):
        return _as_refusal(stop_cmd)
    stop_refused = require_venue_resident_protective_stop(
        stop_cmd.value,
        forms_per_order_type=dict(venue.protective_stop_forms),
    )
    if not is_refusal(stop_refused):
        return policy(
            "protective_stop",
            "undeclared protective-stop capability must refuse the entry",
            failure_id=_ID_INJECTION,
        )
    if stop_refused.category is not RefusalCategory.UNSUPPORTED_CAPABILITY:
        return policy(
            "protective_stop",
            "unprotected entry refuses as unsupported capability",
            given=stop_refused.category.value,
            failure_id=_ID_INJECTION,
        )
    degraded[InjectedFault.PROTECTIVE_STOP_CAPABILITY.value] = DESIGNED_DEGRADED_STATES[
        InjectedFault.PROTECTIVE_STOP_CAPABILITY.value
    ]

    long_bound = _duration(5_000_000_000)
    if is_refusal(long_bound):
        return _as_refusal(long_bound)
    retry_pacer = ConnectionCommandPacer.try_create(
        local_queue_bound=long_bound.value,
        protective_reserve_capacity=1,
    )
    if is_refusal(retry_pacer):
        return _as_refusal(retry_pacer)
    deadline = Instant.try_create(fx.now.value_ns + 2_000_000_000)
    if is_refusal(deadline):
        return _as_refusal(deadline)
    handoff = retry_pacer.value.begin_wire_handoff(
        command_fp1="fp1-cmd-28-3",
        handed_off_at=fx.now,
        submission_deadline=deadline.value,
    )
    if is_refusal(handoff):
        return _as_refusal(handoff)
    retry = retry_pacer.value.refuse_retry_after_handoff("fp1-cmd-28-3")
    if not is_refusal(retry):
        return policy(
            "retry",
            "no command is retried after wire handoff",
            failure_id=_ID_INJECTION,
        )

    return Ok(
        MappingProxyType(
            {
                "commands_retried": report.value.commands_resubmitted,
                "degraded_states": degraded,
                "fills_persist_before_healthy": True,
                "protective_intents_survive": protective_survive,
                "unknown_blocks_one_stream": unknown_one_stream,
                "unprotected_entries_refused": True,
            }
        )
    )


def _exercise_protection_coincidence(
    fx: _Fixtures, inputs: FailureCampaignInputs
) -> Result[Mapping[str, object]]:
    if matrix_supplies_no_default_values() is not True:
        return refuse_invented_ksa_or_latency_number(matrix_defaults=True)

    live_scope = KsaEnforcementScope.stream(fx.venue_id, "acct-live")
    if is_refusal(live_scope):
        return _as_refusal(live_scope)
    epoch = mint_level_epoch(
        epoch_id="ksa-epoch-28-3",
        scope=live_scope.value,
        opened_at=fx.now,
        opened_by="boot",
    )
    if is_refusal(epoch):
        return _as_refusal(epoch)
    yellow = mint_escalation(
        level=KsaLevel.YELLOW,
        trigger_class=KsaTriggerClass.CONNECTIVITY,
        scope=live_scope.value,
        level_epoch_id=epoch.value.epoch_id,
        issued_at=fx.now,
        writer_id="writer-z",
        arbitration_rank=2,
    )
    if is_refusal(yellow):
        return _as_refusal(yellow)
    later = Instant.try_create(fx.now.value_ns + 1)
    if is_refusal(later):
        return _as_refusal(later)
    orange = mint_escalation(
        level=KsaLevel.ORANGE,
        trigger_class=KsaTriggerClass.UNKNOWN_STATE,
        scope=live_scope.value,
        level_epoch_id=epoch.value.epoch_id,
        issued_at=later.value,
        writer_id="writer-a",
        arbitration_rank=1,
    )
    if is_refusal(orange):
        return _as_refusal(orange)
    folded = fold_ksa_level(
        (yellow.value, orange.value),
        scope=live_scope.value,
        epoch=epoch.value,
    )
    if is_refusal(folded):
        return _as_refusal(folded)
    if folded.value is not KsaLevel.ORANGE:
        return policy(
            "ksa",
            "KSA fold is monotone non-decreasing within a level epoch",
            folded=folded.value.value,
        )
    auto = resume(
        scope=live_scope.value,
        authority="reconnect",
        issued_at=fx.now,
        prior_epoch=epoch.value,
        new_epoch_id="ksa-epoch-28-3-b",
        fresh_state_validated=True,
    )
    if not is_refusal(auto):
        return policy(
            "ksa",
            "reconnect never de-escalates; resume is operator-only",
        )
    operator = resume(
        scope=live_scope.value,
        authority="operator",
        issued_at=fx.now,
        prior_epoch=epoch.value,
        new_epoch_id="ksa-epoch-28-3-b",
        fresh_state_validated=True,
    )
    if is_refusal(operator):
        return _as_refusal(operator)
    live_blocks_demo = stream_blocked_by_escalation(
        live_scope.value,
        target_venue_id=fx.venue_id,
        target_account_id="acct-demo",
        target_is_paired_demo=True,
    )
    if live_blocks_demo is True:
        return policy(
            "ksa",
            "a live-stream connectivity escalation must not block paper routing "
            "to the paired demo stream",
        )

    stream = CommandStreamKey.try_create(fx.venue_id, "acct-demo")
    if is_refusal(stream):
        return _as_refusal(stream)
    table = _rank_table()
    if is_refusal(table):
        return _as_refusal(table)
    suspend = mint_control_action(
        ControlActionKind.SUSPEND_NEW,
        "ksa-1",
        AuthorityKind.PROTECTION_AUTHORITY,
        SubjectScope.BINDING,
        "binding-1",
        0,
        "kill-switch",
        stream.value,
        fx.now,
    )
    flatten = mint_control_action(
        ControlActionKind.FLATTEN,
        "book-1",
        AuthorityKind.BOOK_POLICY,
        SubjectScope.BINDING,
        "binding-1",
        1,
        "kill-line",
        stream.value,
        fx.now,
        trigger_class="kill_line_breach",
    )
    suspend_u = _unwrap(suspend)
    if isinstance(suspend_u, TypedRefusal):
        return suspend_u
    flatten_u = _unwrap(flatten)
    if isinstance(flatten_u, TypedRefusal):
        return flatten_u
    enforcement = EnforcementScope(
        subject_scope=SubjectScope.BINDING,
        scope_ref="binding-1",
        stream=stream.value,
    )
    cand_a = DispatchCandidate.try_create(suspend_u, enforcement, origin="ct30", arrival_ordinal=99)
    cand_b = DispatchCandidate.try_create(flatten_u, enforcement, origin="ct30", arrival_ordinal=0)
    cand_a_u = _unwrap(cand_a)
    if isinstance(cand_a_u, TypedRefusal):
        return cand_a_u
    cand_b_u = _unwrap(cand_b)
    if isinstance(cand_b_u, TypedRefusal):
        return cand_b_u
    plan = dispatch_ranked_controls(
        [cand_a_u, cand_b_u],
        table.value,
        stream=stream.value,
        arbitration_seed="story-28-3",
    )
    if is_refusal(plan):
        return _as_refusal(plan)
    emit_kinds = {item.record.action_kind.value for item in plan.value.emit}
    expected = {
        ControlActionKind.SUSPEND_NEW.value,
        ControlActionKind.FLATTEN.value,
    }
    if emit_kinds != expected:
        return policy(
            "ad37",
            "suspend_new and kill-line flatten on one tick must both execute",
            emit=sorted(emit_kinds),
        )

    floor = inputs.kill_line_capital_floor
    if floor.value <= 0:
        return refuse_invented_kill_line_floor(given=floor.value, failure_id=_ID_FLOOR)
    equity = Money.try_create(floor.value - 1, floor.currency, floor.scale)
    if is_refusal(equity):
        return _as_refusal(equity)
    evaluation = evaluate_kill_line(
        binding_scope_ref="binding-demo",
        equity=equity.value,
        kill_line_capital_floor=inputs.kill_line_capital_floor,
        loss_floor=inputs.kill_line_capital_floor,
        evaluated_at=fx.now,
    )
    if is_refusal(evaluation):
        return _as_refusal(evaluation)
    live_target = _unwrap(ExecutionTarget.try_create(AccountRole.LIVE, fx.venue_id, "acct-live"))
    if isinstance(live_target, TypedRefusal):
        return live_target
    paper_target = _unwrap(ExecutionTarget.try_create(AccountRole.DEMO, fx.venue_id, "acct-demo"))
    if isinstance(paper_target, TypedRefusal):
        return paper_target
    package = apply_kill_line_breach(
        evaluation.value,
        venue_id=fx.venue_id,
        account_id="acct-demo",
        live_target=live_target,
        paper_target=paper_target,
        book_mode=BookMode.PAPER,
    )
    if is_refusal(package):
        return _as_refusal(package)

    windows = _unwrap(_news_and_dead_zone(fx))
    if isinstance(windows, TypedRefusal):
        return windows

    instrument = _instrument(fx.venue_id)
    if is_refusal(instrument):
        return _as_refusal(instrument)
    demo_key = _unwrap(sqs_baseline_key(fx.venue_id, "demo", instrument.value))
    if isinstance(demo_key, TypedRefusal):
        return demo_key
    live_key = _unwrap(sqs_baseline_key(fx.venue_id, "live", instrument.value))
    if isinstance(live_key, TypedRefusal):
        return live_key
    if demo_key.environment == live_key.environment:
        return policy(
            "sqs",
            "demo-conditioned and live-conditioned SQS baselines must stay distinct",
            failure_id=_ID_SQS,
        )

    ratchet = _unwrap(_exercise_ratchet(fx, inputs))
    if isinstance(ratchet, TypedRefusal):
        return ratchet
    bench = _unwrap(_exercise_bench(fx, inputs, live_target, paper_target))
    if isinstance(bench, TypedRefusal):
        return bench

    return Ok(
        MappingProxyType(
            {
                "ad-37": {
                    "compose_both_execute": True,
                    "emit": sorted(emit_kinds),
                    "exit_preservation": True,
                },
                "dead-zone": windows["dead_zone"],
                "kill-line": {
                    "binding_state": package.value.binding_state.value,
                    "book_mode": package.value.book_mode.value,
                    "close_reason": package.value.close_reason.value,
                    "paper_flatten_stand_down": True,
                },
                "ksa": {
                    "folded": folded.value.value,
                    "live_connectivity_blocks_demo": live_blocks_demo,
                    "operator_only_deescalation": True,
                    "scoped_monotone": True,
                },
                "news": windows["news"],
                "ratchet": ratchet,
                "bench": bench,
                "sqs": {
                    "demo_environment": demo_key.environment,
                    "live_environment": live_key.environment,
                    "separated": True,
                },
            }
        )
    )


def _rank_table() -> Result[ControlRankTable]:
    rows: list[ControlRankRow] = []
    for kind, rank in (
        (ControlActionKind.SUSPEND_NEW, 0),
        (ControlActionKind.FLATTEN, 1),
        (ControlActionKind.DRAIN, 2),
        (ControlActionKind.RESUME, 3),
    ):
        row = ControlRankRow.try_create(kind, rank)
        if is_refusal(row):
            return _as_refusal(row)
        rows.append(row.value)
    return ControlRankTable.try_create(rows)


def _news_and_dead_zone(fx: _Fixtures) -> Result[Mapping[str, object]]:
    instrument = _instrument(fx.venue_id)
    if is_refusal(instrument):
        return _as_refusal(instrument)
    exposure = CurrencyExposureRecord.try_create(instrument.value, ("USD",), fx.now, "exp-28-3")
    if is_refusal(exposure):
        return _as_refusal(exposure)
    scope = resolve_instrument_scope(
        affected_currencies=("USD",),
        candidate_instruments=(instrument.value,),
        exposure_records=(exposure.value,),
    )
    if is_refusal(scope):
        return _as_refusal(scope)
    start = _unwrap(Instant.try_create(fx.now.value_ns - 1_000_000_000))
    if isinstance(start, TypedRefusal):
        return start
    end = _unwrap(Instant.try_create(fx.now.value_ns + 1_000_000_000))
    if isinstance(end, TypedRefusal):
        return end
    bounds = WindowBounds.try_create(start, end)
    if is_refusal(bounds):
        return _as_refusal(bounds)
    news_cal = _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2024a"))
    if isinstance(news_cal, TypedRefusal):
        return news_cal
    hours_cal = _unwrap(CalendarIdentity.try_create("market-hours-forex", "v3", "2024a"))
    if isinstance(hours_cal, TypedRefusal):
        return hours_cal
    known_at = _unwrap(Instant.try_create(fx.now.value_ns - 2_000_000_000))
    if isinstance(known_at, TypedRefusal):
        return known_at
    feed = FeedQuadruple.try_create("calendar-feed", "nfp-28-3", "r1", known_at)
    if is_refusal(feed):
        return _as_refusal(feed)
    news = mint_control_window(
        bounds.value,
        WindowKind.NEWS,
        scope.value,
        "high-impact-news",
        news_cal,
        "win-nfp-28-3",
        feed_quadruple=feed.value,
    )
    if is_refusal(news):
        return _as_refusal(news)
    dead = mint_control_window(
        bounds.value,
        WindowKind.DAILY_DEAD_ZONE,
        scope.value,
        WindowKind.DAILY_DEAD_ZONE.value,
        hours_cal,
        "win-dead-28-3",
    )
    if is_refusal(dead):
        return _as_refusal(dead)
    entry = enforce_entry_at_book_door(
        instrument=instrument.value,
        book_mode=BookMode.PAPER,
        decision_at=fx.now,
        windows=(news.value, dead.value),
        would_have_been_action={"class": "entry"},
    )
    if is_refusal(entry):
        return _as_refusal(entry)
    if entry.value.blocked is not True:
        return policy("windows", "news and dead-zone must block entries")
    exit_ok = allow_protective_act_under_windows(proposed_act=ProposedWindowAct.EXIT)
    if is_refusal(exit_ok):
        return _as_refusal(exit_ok)
    protect_ok = allow_protective_act_under_windows(
        proposed_act=ProposedWindowAct.PROTECTION_ACTION
    )
    if is_refusal(protect_ok):
        return _as_refusal(protect_ok)
    narrow_end = _unwrap(Instant.try_create(fx.now.value_ns + 100_000_000))
    if isinstance(narrow_end, TypedRefusal):
        return narrow_end
    narrow_bounds = WindowBounds.try_create(start, narrow_end)
    if is_refusal(narrow_bounds):
        return _as_refusal(narrow_bounds)
    feed_r2 = FeedQuadruple.try_create("calendar-feed", "nfp-28-3", "r2", known_at)
    if is_refusal(feed_r2):
        return _as_refusal(feed_r2)
    revision = mint_control_window(
        narrow_bounds.value,
        WindowKind.NEWS,
        scope.value,
        "high-impact-news",
        news_cal,
        "win-nfp-28-3",
        feed_quadruple=feed_r2.value,
    )
    if is_refusal(revision):
        return _as_refusal(revision)
    log = ControlWindowRevisionLog(window_id="win-nfp-28-3")
    first = apply_news_revision(log, news.value, decision_at=fx.now)
    if is_refusal(first):
        return _as_refusal(first)
    new_log, _effective, _first_disposition = first.value
    revised = apply_news_revision(
        new_log,
        revision.value,
        decision_at=fx.now,
        prior_in_force=news.value,
    )
    if is_refusal(revised):
        return _as_refusal(revised)
    _held_log, _held_effective, disposition = revised.value
    if disposition is not NewsRevisionDisposition.NARROWING_HELD:
        return policy(
            "news",
            "a news-calendar revision must widen-not-shrink an in-force window",
            disposition=disposition.value,
        )
    return Ok(
        MappingProxyType(
            {
                "dead_zone": {"entries_blocked": True, "exit_preserved": True},
                "news": {
                    "entries_blocked": True,
                    "exit_preserved": True,
                    "widen_not_shrink": disposition.value,
                },
            }
        )
    )


def _exercise_ratchet(fx: _Fixtures, inputs: FailureCampaignInputs) -> Result[Mapping[str, object]]:
    instrument = _instrument(fx.venue_id)
    if is_refusal(instrument):
        return _as_refusal(instrument)
    distance = PriceDelta.try_create(100, instrument.value, 5)
    if is_refusal(distance):
        return _as_refusal(distance)
    price = Price.try_create(1_10000, instrument.value, 5)
    if is_refusal(price):
        return _as_refusal(price)
    excursion = ExactRational.try_create(12, 10, UnitKind.R_MULTIPLE)
    if is_refusal(excursion):
        return _as_refusal(excursion)
    offset = PriceDelta.try_create(0, instrument.value, 5)
    if is_refusal(offset):
        return _as_refusal(offset)
    proposal = originate_breakeven_ratchet(
        original_risk_distance=distance.value,
        current_stop_distance=distance.value,
        favorable_excursion=excursion.value,
        reference_price=price.value,
        trigger=inputs.breakeven_ratchet_trigger,
        offset=offset.value,
    )
    if is_refusal(proposal):
        return _as_refusal(proposal)
    return Ok(
        MappingProxyType(
            {
                "originated": proposal.value.amendment is not None,
                "single_sided": True,
            }
        )
    )


def _exercise_bench(
    fx: _Fixtures,
    inputs: FailureCampaignInputs,
    live_target: ExecutionTarget,
    paper_target: ExecutionTarget,
) -> Result[Mapping[str, object]]:
    epoch = _fp("epoch-bench-28-3")
    if is_refusal(epoch):
        return _as_refusal(epoch)
    records: list[ExitRecord] = []
    for seed, pnl, outcome, reason, authority in (
        (
            "be-1",
            -50,
            CloseOutcome.BREAKEVEN,
            CloseReason.PROTECTIVE_STOP_FILL,
            ClosingAuthority.VENUE,
        ),
        (
            "ql-1",
            -10_000,
            CloseOutcome.LOSS,
            CloseReason.PROTECTIVE_STOP_FILL,
            ClosingAuthority.VENUE,
        ),
        (
            "ql-2",
            -12_000,
            CloseOutcome.LOSS,
            CloseReason.HOLD_TIME_FORCE_FLAT,
            ClosingAuthority.BOOK_POLICY,
        ),
    ):
        minted = _mint_exit(
            seed=seed,
            epoch=epoch.value,
            realized_pnl=pnl,
            outcome=outcome,
            now=fx.now,
            venue=fx.venue_id,
            close_reason=reason,
            authority=authority,
        )
        if is_refusal(minted):
            return _as_refusal(minted)
        records.append(minted.value)
    report = evaluate_qualifying_loss_bench(
        tuple(records),
        binding_epoch=epoch.value,
        q=inputs.qualifying_loss_threshold,
        threshold=inputs.bench_consecutive_loss_threshold,
    )
    if is_refusal(report):
        return _as_refusal(report)
    effect = apply_bench_crossing(
        report.value,
        live_target=live_target,
        paper_target=paper_target,
        book_mode=BookMode.LIVE,
    )
    if is_refusal(effect):
        return _as_refusal(effect)
    if effect.value.seat_state is not SeatState.BENCHED:
        return policy("bench", "qualifying-loss bench must bench the seat")
    if effect.value.book_mode is not BookMode.LIVE:
        return policy("bench", "bench routes the seat to paper while the Book stays LIVE")
    return Ok(
        MappingProxyType(
            {
                "book_mode": effect.value.book_mode.value,
                "seat_state": effect.value.seat_state.value,
                "threshold_crossed": report.value.threshold_crossed,
            }
        )
    )


def _mint_exit(
    *,
    seed: str,
    epoch: Fingerprint,
    realized_pnl: int,
    outcome: CloseOutcome,
    now: Instant,
    venue: VenueId,
    close_reason: CloseReason,
    authority: ClosingAuthority,
) -> Result[ExitRecord]:
    instrument = _instrument(venue)
    if is_refusal(instrument):
        return _as_refusal(instrument)
    distance = PriceDelta.try_create(50, instrument.value, 5)
    if is_refusal(distance):
        return _as_refusal(distance)
    amount = _money(10_000)
    if is_refusal(amount):
        return _as_refusal(amount)
    pnl = _money(realized_pnl)
    if is_refusal(pnl):
        return _as_refusal(pnl)
    fill = _fp(f"fill-{seed}")
    if is_refusal(fill):
        return _as_refusal(fill)
    pos = _fp(seed)
    if is_refusal(pos):
        return _as_refusal(pos)
    label = ExitResultLabel.try_create(AccountRole.DEMO, World.LIVE)
    if is_refusal(label):
        return _as_refusal(label)
    arb_fp: Fingerprint | None = None
    vobs_fp: Fingerprint | None = None
    if authority is not ClosingAuthority.VENUE:
        arb = _fp(f"arb-{seed}")
        if is_refusal(arb):
            return _as_refusal(arb)
        arb_fp = arb.value
    else:
        vobs = _fp(f"venue-obs-{seed}")
        if is_refusal(vobs):
            return _as_refusal(vobs)
        vobs_fp = vobs.value
    return mint_exit_record(
        virtual_position_ref=pos.value,
        opening_bot_id="bot-alpha",
        original_risk_distance=distance.value,
        original_risk_amount=amount.value,
        fill_references=(fill.value,),
        realized_pnl=pnl.value,
        cost_components=(),
        close_reason=close_reason,
        mechanism=close_reason,
        outcome=outcome,
        closing_authority=authority,
        close_reason_mapping_version=1,
        result_label=label.value,
        loss_predicate_format_version=1,
        binding_epoch=epoch,
        recorded_at=now,
        arbitration_record_ref=arb_fp,
        venue_observation_ref=vobs_fp,
    )


def _exercise_reconciliation(
    fx: _Fixtures, venue: ConformanceDouble
) -> Result[Mapping[str, object]]:
    qty = _unwrap(_qty(100))
    if isinstance(qty, TypedRefusal):
        return qty
    drifted = _unwrap(_qty(150))
    if isinstance(drifted, TypedRefusal):
        return drifted
    cash = _unwrap(_money(50_000_00))
    if isinstance(cash, TypedRefusal):
        return cash
    venue_eq = _unwrap(_money(51_000_00))
    if isinstance(venue_eq, TypedRefusal):
        return venue_eq
    virtual_eq = _unwrap(_money(50_900_00))
    if isinstance(virtual_eq, TypedRefusal):
        return virtual_eq
    mark = _unwrap(Instant.try_create(fx.now.value_ns + 1))
    if isinstance(mark, TypedRefusal):
        return mark
    reconciled = _unwrap(
        run_reconciliation(
            trigger=ReconciliationTrigger.STARTUP,
            role=AccountRole.DEMO,
            quantity_pairs=(("EURUSD", qty, qty),),
            venue_realized_balance=cash,
            virtual_realized_cash=cash,
            venue_equity=venue_eq,
            venue_mark_instant=fx.now,
            virtual_ledger_equity=virtual_eq,
            virtual_mark_instant=mark,
        )
    )
    if isinstance(reconciled, TypedRefusal):
        return reconciled
    drift = _unwrap(
        run_reconciliation(
            trigger=ReconciliationTrigger.SCHEDULED,
            role=AccountRole.DEMO,
            quantity_pairs=(("EURUSD", qty, drifted),),
            venue_realized_balance=cash,
            virtual_realized_cash=cash,
        )
    )
    if isinstance(drift, TypedRefusal):
        return drift
    unknown = _unwrap(
        run_reconciliation(
            trigger=ReconciliationTrigger.AFTER_UNKNOWN,
            role=AccountRole.LIVE,
            readback_status=ReadbackStatus.ABSENT,
        )
    )
    if isinstance(unknown, TypedRefusal):
        return unknown
    lookback = _unwrap(
        run_reconciliation(
            trigger=ReconciliationTrigger.RECONNECT,
            role=AccountRole.LIVE,
            lookback_status=LookbackStatus.OUT_OF_LOOKBACK,
        )
    )
    if isinstance(lookback, TypedRefusal):
        return lookback
    observed = {
        reconciled.verdict.value,
        drift.verdict.value,
        unknown.verdict.value,
        lookback.verdict.value,
    }
    if observed != set(FOUR_VERDICTS):
        return policy(
            "reconciliation",
            "the campaign must produce all four reconciliation verdicts",
            observed=sorted(observed),
            required=sorted(FOUR_VERDICTS),
        )
    if (
        reconciled.quantity_residuals[0].is_zero is not True
        or reconciled.cash_residual is None
        or reconciled.cash_residual.is_zero is not True
    ):
        return policy("reconciliation", "both residuals must be proven on a match")
    if reconciled.equity is None or reconciled.equity.as_mapping()["differenced"] is not False:
        return policy(
            "equity_difference",
            "venue and virtual-ledger equities are shown side by side and never differenced",
            failure_id=_ID_EQUITY,
        )
    differenced = refuse_equity_difference(venue_eq, virtual_eq)
    if not is_refusal(differenced):
        return policy(
            "equity_difference",
            "differencing venue and virtual-ledger equity must refuse",
            failure_id=_ID_EQUITY,
        )
    narrative = build_equity_narrative(
        venue_equity=venue_eq,
        venue_mark_instant=fx.now,
        virtual_ledger_equity=virtual_eq,
        virtual_mark_instant=mark,
    )
    if is_refusal(narrative):
        return _as_refusal(narrative)

    demo_drift = _unwrap(apply_drift_response(role=AccountRole.DEMO, world=World.LIVE))
    if isinstance(demo_drift, TypedRefusal):
        return demo_drift
    live_drift = _unwrap(apply_drift_response(role=AccountRole.LIVE, world=World.LIVE))
    if isinstance(live_drift, TypedRefusal):
        return live_drift
    if demo_drift.kind is not DriftResponseKind.ALARM_AND_CONTINUE:
        return policy(
            "drift",
            "demo drift alarms and continues the soak",
            kind=demo_drift.kind.value,
        )
    if live_drift.kind is not DriftResponseKind.ENTRIES_ONLY_STAND_DOWN:
        return policy(
            "drift",
            "live-role drift stands entries down",
            kind=live_drift.kind.value,
        )

    for verdict in (
        ReconciliationVerdict.DRIFT,
        ReconciliationVerdict.UNKNOWN,
        ReconciliationVerdict.OUT_OF_LOOKBACK,
    ):
        armed = venue.arm_reconcile(verdict)
        if is_refusal(armed):
            return _as_refusal(armed)
        recon = venue.reconcile()
        if is_refusal(recon):
            return _as_refusal(recon)
        if recon.value.verdict is not verdict:
            return policy(
                "reconcile_inject",
                "the double must emit the armed reconciliation verdict",
                expected=verdict.value,
                got=recon.value.verdict.value,
            )
        path = decide_resolve_path(
            recon.value,
            clarity=ReadbackClarity.AMBIGUOUS,
            covers_lookback=False,
        )
        if is_refusal(path):
            return _as_refusal(path)
        if path.value.may_auto_resolve is True or path.value.path is ResolvePath.AUTO:
            return policy(
                "out_of_lookback",
                "drift, unknown, and out-of-lookback never auto-resolve",
                verdict=verdict.value,
                path=path.value.path.value,
            )

    return Ok(
        MappingProxyType(
            {
                "demo_drift": demo_drift.kind.value,
                "live_drift": live_drift.kind.value,
                "out_of_lookback_auto_resolves": False,
                "residuals_proven": True,
                "venue_equity_differenced": False,
                "verdicts": sorted(observed),
            }
        )
    )
