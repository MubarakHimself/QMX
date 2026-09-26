"""D010 runtime risk gate over the node composition root (Story 26.14).

One executable gate: conformance double + injected clock + seeded fixtures
exercise CT-22/23/24/25/27/28/29/30/31/32 through real qmn call paths. Coverage
fails when a risk contract is importable but unwired. Paper profit and manual
observation never satisfy the gate. Refusal categories are produced by named
runtime paths, not by enum membership tautologies (D010; TN-23).
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import Final, TypeVar

from qmf.core import (
    Account,
    AccountRole,
    CalendarIdentity,
    CivilDate,
    Duration,
    ExactRational,
    Fingerprint,
    Instant,
    Instrument,
    Money,
    Ok,
    Price,
    PriceDelta,
    Quantity,
    RefusalCategory,
    Result,
    SinkAck,
    SinkResult,
    TradingDate,
    TypedRefusal,
    UnitKind,
    ValueFactor,
    VenueId,
    World,
    fingerprint,
    is_ok,
    is_refusal,
    unpersistable,
)
from qmf.risk.binding import BmsInstanceId, BookInstanceId
from qmf.risk.control_action import (
    AuthorityKind,
    CommandStreamKey,
    EnforcementScope,
    SubjectScope,
    mint_control_action,
)
from qmf.risk.control_rank import ControlActionKind, ControlRankRow, ControlRankTable
from qmf.risk.control_window import (
    CurrencyExposureRecord,
    FeedQuadruple,
    ProposedWindowAct,
    WindowBounds,
    WindowKind,
    mint_control_window,
    resolve_instrument_scope,
)
from qmf.risk.door import (
    CitedEvidence,
    Direction,
    EntryIntent,
    EvidenceSlot,
    ExitLogicRef,
    ReasonCode,
    refuse_no_full_loss_price,
)
from qmf.risk.exit_record import (
    CloseOutcome,
    CloseReason,
    ClosingAuthority,
    CostComponent,
    ExitRecord,
    ExitResultLabel,
    mint_exit_record,
)
from qmf.risk.journal import block_dispatch_on_journal_failure
from qmf.risk.paper import (
    BindingTransitionStream,
    BookMode,
    ExecutionTarget,
    PaperEpochLog,
    PaperTargetLog,
    SeatState,
)
from qmf.risk.performance import PublishAct, check_publish_never_act
from qmf.risk.templates import BmsDefinition, BookDefinition

from qmn.capital import (
    apply_bench_crossing,
    apply_kill_line_breach,
    evaluate_kill_line,
    evaluate_qualifying_loss_bench,
    refuse_stale_exit_before_intent,
)
from qmn.host._refuse import invalid, policy
from qmn.host.boot_ceremony import (
    CompositionFingerprintInputs,
    InMemoryBootAttemptSink,
    PreflightFacts,
    run_boot_ceremony,
)
from qmn.host.risk_population import (
    CapabilityRecord,
    PairedTargetRecord,
    PopulationBindingRecord,
    PopulationBmsRecord,
    PopulationBookRecord,
    PriorityRecord,
    RuntimeRiskGraph,
    ScopeRecord,
    SeatRecord,
    WindowRecord,
    admit_runtime_risk_population,
)
from qmn.journal_dispatch import (
    RecordingEffectDispatcher,
    RecordingJournalSink,
    journal_before_effect,
)
from qmn.ledger import refuse_paper_pnl_to_treasury
from qmn.order import (
    CommandStreamUnknownBoundary,
    PostAdmissionKind,
    admit_entry_at_book_door,
    mint_ct29_from_frozen_r,
    mint_place_order_from_authorized,
    mint_virtual_from_authorized,
    preserve_frozen_r,
    refuse_close_partial,
)
from qmn.order.unknown import ProtectionIntentExtent as UnknownIntentExtent
from qmn.paper import (
    build_paired_demo_target,
    mint_operator_paper_flip,
    resolve_book_execution_target,
)
from qmn.promotion import PromotionLanding, request_activation
from qmn.promotion.battery import SilentBatteryReport
from qmn.protection import (
    DispatchCandidate,
    allow_protective_act_under_windows,
    dispatch_ranked_controls,
    enforce_entry_at_book_door,
)
from qmn.reconcile import (
    FOUR_VERDICTS,
    LookbackStatus,
    ReadbackStatus,
    ReconciliationTrigger,
    run_reconciliation,
)
from qmn.seats import OPERATOR_PRINCIPAL, GovernedSeatState
from qmn.time import VpsClock
from qmn.venue import (
    AdmissionDisposition,
    Command,
    CommandObservation,
    ConformanceDouble,
    ConnectionManager,
    JournalEvent,
    OrderParameters,
    OrderType,
    StreamBlockCause,
    SubmissionOutcome,
    SubmissionResult,
    TimeInForce,
    UnknownTrigger,
    VenueClientKind,
    venue_writer_id,
)

__all__ = [
    "MANUAL_OBSERVATION_IS_PROOF",
    "PAPER_PROFIT_IS_PROOF",
    "REQUIRED_RISK_CONTRACTS",
    "RUNTIME_RISK_GATE_SURFACE",
    "RUNTIME_RISK_SCENARIOS",
    "RiskContractWiring",
    "RuntimeRiskCoverageReport",
    "RuntimeRiskGateInputs",
    "RuntimeRiskGateReport",
    "evaluate_runtime_risk_coverage",
    "qmn_production_src_root",
    "refuse_manual_observation_as_proof",
    "refuse_paper_profit_as_proof",
    "run_runtime_risk_gate",
]

T = TypeVar("T")

RUNTIME_RISK_GATE_SURFACE: Final[str] = "qmn.host.runtime_risk_gate"
PAPER_PROFIT_IS_PROOF: Final[bool] = False
MANUAL_OBSERVATION_IS_PROOF: Final[bool] = False

RUNTIME_RISK_SCENARIOS: Final[tuple[str, ...]] = (
    "entry_preservation",
    "exits_under_blocks",
    "paper_routing",
    "unknown",
    "four_verdict_reconciliation",
    "priority_compose_conflict",
    "bench",
    "kill_line",
    "next_day_activation",
)

_NS: Final[int] = 1_700_000_000_000_000_000
_BOUNDARY_NS: Final[int] = _NS + 86_400_000_000_000
_MACHINE: Final[str] = "vps-d010"
_ADAPTER: Final[str] = "conformance-double"
_BOOT: Final[str] = "boot-d010"
_SESSION: Final[str] = "session-d010"


@dataclass(frozen=True, slots=True)
class RiskContractWiring:
    """One risk contract that must be called, not merely imported."""

    contract_id: str
    traceability_id: str
    qmf_risk_modules: frozenset[str]
    required_calls: frozenset[str]


REQUIRED_RISK_CONTRACTS: Final[tuple[RiskContractWiring, ...]] = (
    RiskContractWiring(
        contract_id="CT-22",
        traceability_id="D010/CT-22",
        qmf_risk_modules=frozenset({"qmf.risk.templates"}),
        required_calls=frozenset({"BookDefinition.try_create"}),
    ),
    RiskContractWiring(
        contract_id="CT-23",
        traceability_id="D010/CT-23",
        qmf_risk_modules=frozenset({"qmf.risk.door"}),
        required_calls=frozenset({"admit_entry_at_book_door"}),
    ),
    RiskContractWiring(
        contract_id="CT-24",
        traceability_id="D010/CT-24",
        qmf_risk_modules=frozenset({"qmf.risk.paper"}),
        required_calls=frozenset({"resolve_book_execution_target"}),
    ),
    RiskContractWiring(
        contract_id="CT-25",
        traceability_id="D010/CT-25",
        qmf_risk_modules=frozenset({"qmf.risk.journal"}),
        required_calls=frozenset({"journal_before_effect"}),
    ),
    RiskContractWiring(
        contract_id="CT-27",
        traceability_id="D010/CT-27",
        qmf_risk_modules=frozenset({"qmf.risk.templates"}),
        required_calls=frozenset({"BmsDefinition.try_create"}),
    ),
    RiskContractWiring(
        contract_id="CT-28",
        traceability_id="D010/CT-28",
        qmf_risk_modules=frozenset({"qmf.risk.binding"}),
        required_calls=frozenset({"admit_runtime_risk_population"}),
    ),
    RiskContractWiring(
        contract_id="CT-29",
        traceability_id="D010/CT-29",
        qmf_risk_modules=frozenset({"qmf.risk.exit_record"}),
        required_calls=frozenset({"mint_ct29_from_frozen_r"}),
    ),
    RiskContractWiring(
        contract_id="CT-30",
        traceability_id="D010/CT-30",
        qmf_risk_modules=frozenset({"qmf.risk.control_action"}),
        required_calls=frozenset({"dispatch_ranked_controls"}),
    ),
    RiskContractWiring(
        contract_id="CT-31",
        traceability_id="D010/CT-31",
        qmf_risk_modules=frozenset({"qmf.risk.control_window"}),
        required_calls=frozenset(
            {"enforce_entry_at_book_door", "allow_protective_act_under_windows"}
        ),
    ),
    RiskContractWiring(
        contract_id="CT-32",
        traceability_id="D010/CT-32",
        qmf_risk_modules=frozenset({"qmf.risk.performance"}),
        required_calls=frozenset({"check_publish_never_act", "refuse_paper_profit_as_proof"}),
    ),
)


@dataclass(frozen=True, slots=True)
class RuntimeRiskCoverageReport:
    """Coverage of risk-contract runtime paths in production sources."""

    wired_contracts: tuple[str, ...]
    call_tokens: frozenset[str]
    imported_modules: frozenset[str]

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "imported_modules": tuple(sorted(self.imported_modules)),
                "wired_contracts": list(self.wired_contracts),
            }
        )


@dataclass(frozen=True, slots=True)
class RuntimeRiskGateInputs:
    """Conformance double, injected clock, and optional forbidden proofs."""

    clock: VpsClock
    venue: ConformanceDouble
    paper_profit: object | None = None
    manual_observation: object | None = None


@dataclass(frozen=True, slots=True)
class RuntimeRiskGateReport:
    """Structural proof that the risk contracts ran through the composition root."""

    contracts_exercised: tuple[str, ...]
    scenarios_exercised: tuple[str, ...]
    refusal_paths: Mapping[str, str]
    evidence_records: Mapping[str, Mapping[str, object]]
    coverage: RuntimeRiskCoverageReport
    composition_sealed: bool
    paper_profit_is_proof: bool = PAPER_PROFIT_IS_PROOF
    manual_observation_is_proof: bool = MANUAL_OBSERVATION_IS_PROOF

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "composition_sealed": self.composition_sealed,
                "contracts_exercised": list(self.contracts_exercised),
                "manual_observation_is_proof": self.manual_observation_is_proof,
                "paper_profit_is_proof": self.paper_profit_is_proof,
                "refusal_paths": dict(self.refusal_paths),
                "scenarios_exercised": list(self.scenarios_exercised),
            }
        )


def qmn_production_src_root() -> Path:
    """``qmn/src/qmn`` — production sources; tests never satisfy the gate."""
    return Path(__file__).resolve().parents[1]


def _unwrap(result: Result[T]) -> T | TypedRefusal:
    """Split a Result so callers return TypedRefusal without Result invariance."""
    if isinstance(result, TypedRefusal):
        return result
    return result.value


def refuse_paper_profit_as_proof(amount: object = None, **extra: object) -> TypedRefusal:
    """Paper P&L never proves the runtime risk gate (TN-23 / CT-32)."""
    _ = check_publish_never_act(PublishAct.SIZE)
    _ = refuse_paper_pnl_to_treasury(amount)
    return policy(
        "paper_profit",
        "paper profit and published performance never satisfy the runtime risk "
        "gate; measurement publishes and never acts (D010; TN-23; CT-32)",
        failure_id="risk_gate.paper_profit",
        paper_profit_is_proof=False,
        traceability_id="D010/TN-23",
        **extra,
    )


def refuse_manual_observation_as_proof(**extra: object) -> TypedRefusal:
    """A manual observation is not runtime evidence for D010."""
    return policy(
        "manual_observation",
        "manual observation never satisfies the runtime risk gate; only "
        "executable composition-root paths count (D010; TN-23)",
        failure_id="risk_gate.manual_observation",
        manual_observation_is_proof=False,
        traceability_id="D010/TN-23",
        **extra,
    )


def evaluate_runtime_risk_coverage(
    source_root: Path | None = None,
) -> Result[RuntimeRiskCoverageReport]:
    """Fail when a required risk contract is importable but not called."""
    root = source_root if source_root is not None else qmn_production_src_root()
    imported, calls = _scan_source_tokens(root)
    missing: list[RiskContractWiring] = []
    for spec in REQUIRED_RISK_CONTRACTS:
        if not spec.required_calls.issubset(calls):
            missing.append(spec)
    if missing:
        first = missing[0]
        imported_unwired = any(
            module in imported or any(item.startswith(f"{module}.") for item in imported)
            for spec in missing
            for module in spec.qmf_risk_modules
        )
        reason = (
            "risk contract is importable but unwired at the node composition root"
            if imported_unwired
            else "risk contract has no runtime path at the node composition root"
        )
        return policy(
            "coverage",
            reason,
            failure_id="risk_gate.unwired_contract",
            missing_runtime_path=tuple(sorted(first.required_calls)),
            traceability_id=first.traceability_id,
            contract_id=first.contract_id,
            missing_contracts=tuple(spec.contract_id for spec in missing),
        )
    wired = tuple(spec.contract_id for spec in REQUIRED_RISK_CONTRACTS)
    return Ok(
        RuntimeRiskCoverageReport(
            wired_contracts=wired,
            call_tokens=calls,
            imported_modules=imported,
        )
    )


def run_runtime_risk_gate(
    inputs: object,
) -> Result[RuntimeRiskGateReport]:
    """Exercise the risk contracts through the composition root."""
    if not isinstance(inputs, RuntimeRiskGateInputs):
        return invalid(
            "inputs",
            "the runtime risk gate takes RuntimeRiskGateInputs",
            given=type(inputs).__name__,
        )
    if inputs.paper_profit is not None:
        return refuse_paper_profit_as_proof(amount=inputs.paper_profit)
    if inputs.manual_observation is not None:
        return refuse_manual_observation_as_proof(given=repr(inputs.manual_observation))
    clock = inputs.clock
    venue = inputs.venue
    if venue.kind is not VenueClientKind.CONFORMANCE:
        return policy(
            "venue",
            "D010 requires the FEAT-0023 conformance double, never live or replay",
            given=venue.kind.value,
        )

    coverage = _unwrap(evaluate_runtime_risk_coverage())
    if isinstance(coverage, TypedRefusal):
        return coverage

    now = _unwrap(clock.wall_now())
    if isinstance(now, TypedRefusal):
        return now
    fx = _Fixtures(clock=clock, venue=venue, now=now)

    book = _unwrap(BookDefinition.try_create(2, "USD", {}))
    if isinstance(book, TypedRefusal):
        return book
    bms = _unwrap(BmsDefinition.try_create(1, {}))
    if isinstance(bms, TypedRefusal):
        return bms

    composed = _unwrap(_exercise_compose(fx))
    if isinstance(composed, TypedRefusal):
        return composed
    entry = _unwrap(_exercise_entry_preservation(fx))
    if isinstance(entry, TypedRefusal):
        return entry
    exits = _unwrap(_exercise_exits_under_blocks(fx))
    if isinstance(exits, TypedRefusal):
        return exits
    paper = _unwrap(_exercise_paper_routing(fx))
    if isinstance(paper, TypedRefusal):
        return paper
    unknown = _unwrap(_exercise_unknown(fx))
    if isinstance(unknown, TypedRefusal):
        return unknown
    reconcile = _unwrap(_exercise_four_verdicts(fx))
    if isinstance(reconcile, TypedRefusal):
        return reconcile
    compose = _unwrap(_exercise_priority_compose(fx))
    if isinstance(compose, TypedRefusal):
        return compose
    bench = _unwrap(_exercise_bench(fx))
    if isinstance(bench, TypedRefusal):
        return bench
    kill = _unwrap(_exercise_kill_line(fx))
    if isinstance(kill, TypedRefusal):
        return kill
    activation = _unwrap(_exercise_next_day_activation(fx))
    if isinstance(activation, TypedRefusal):
        return activation
    refusals = _unwrap(_produce_refusal_categories(fx))
    if isinstance(refusals, TypedRefusal):
        return refusals
    journaled = _unwrap(_exercise_journal_before_dispatch())
    if isinstance(journaled, TypedRefusal):
        return journaled

    _ = refuse_paper_profit_as_proof()
    _ = refuse_manual_observation_as_proof()

    evidence: dict[str, Mapping[str, object]] = {
        "entry_preservation": entry,
        "exits_under_blocks": exits,
        "paper_routing": paper,
        "unknown": unknown,
        "four_verdict_reconciliation": reconcile,
        "priority_compose_conflict": compose,
        "bench": bench,
        "kill_line": kill,
        "next_day_activation": activation,
        "ct22_book_definition": MappingProxyType(book.fp1_identity()),
        "ct27_bms_definition": MappingProxyType(bms.fp1_identity()),
        "journal_before_dispatch": journaled,
    }
    missing_scenario = [name for name in RUNTIME_RISK_SCENARIOS if name not in evidence]
    if missing_scenario:
        return policy(
            "scenarios",
            "the runtime risk gate must exercise every named D010 scenario",
            missing=missing_scenario,
        )
    expected_categories = {member.value for member in RefusalCategory}
    if set(refusals) != expected_categories:
        return policy(
            "refusal_category",
            "every CT-04 refusal category must have a named runtime production path",
            missing=sorted(expected_categories - set(refusals)),
        )
    return Ok(
        RuntimeRiskGateReport(
            contracts_exercised=tuple(spec.contract_id for spec in REQUIRED_RISK_CONTRACTS),
            scenarios_exercised=RUNTIME_RISK_SCENARIOS,
            refusal_paths=MappingProxyType(refusals),
            evidence_records=MappingProxyType(evidence),
            coverage=coverage,
            composition_sealed=composed["sealed"] is True,
        )
    )


def _scan_source_tokens(root: Path) -> tuple[frozenset[str], frozenset[str]]:
    imported: set[str] = set()
    calls: set[str] = set()
    if not root.exists():
        return frozenset(), frozenset()
    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
                for alias in node.names:
                    imported.add(f"{node.module}.{alias.name}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name)
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    calls.add(func.id)
                elif isinstance(func, ast.Attribute):
                    calls.add(func.attr)
                    if isinstance(func.value, ast.Name):
                        calls.add(func.value.id)
                        calls.add(f"{func.value.id}.{func.attr}")
    return frozenset(imported), frozenset(calls)


class _SecretStore:
    def read(self, ref: object, /) -> Result[object]:
        del ref
        return unpersistable("no such credential")

    def atomic_replace(self, ref: object, new_value: object, /) -> Result[object]:
        del new_value
        return Ok(ref)


class _ObsSink:
    def emit(self, observation: object, /) -> SinkResult:
        del observation
        return Ok(SinkAck())


class _JournalSink:
    def append(self, event: object, /) -> SinkResult:
        del event
        return Ok(SinkAck())


class _RecordSink:
    def write(self, record: object, /) -> SinkResult:
        del record
        return Ok(SinkAck())


class _OffsetStopModule:
    def derive_full_loss_price(
        self,
        *,
        entry_price: Price,
        direction: Direction,
        cited_evidence: CitedEvidence,
    ) -> Result[Price]:
        del cited_evidence
        if direction is Direction.LONG:
            value = entry_price.value - 1_000
        else:
            value = entry_price.value + 1_000
        return Price.try_create(value, entry_price.instrument, entry_price.scale)


class _NoStopModule:
    def derive_full_loss_price(
        self,
        *,
        entry_price: Price,
        direction: Direction,
        cited_evidence: CitedEvidence,
    ) -> Result[Price]:
        del entry_price, direction, cited_evidence
        return refuse_no_full_loss_price(module="no-stop")


@dataclass(frozen=True, slots=True)
class _DayBoundary:
    calendar_identity: CalendarIdentity
    next_ns: int

    def trading_date_for(self, instant: Instant) -> Result[TradingDate]:
        del instant
        civil = CivilDate.try_create(2026, 9, 1)
        if is_refusal(civil):
            return civil
        return TradingDate.try_create(self.calendar_identity, civil.value)

    def next_boundary_after(self, instant: Instant) -> Result[Instant]:
        del instant
        return Instant.try_create(self.next_ns)

    @property
    def identity(self) -> CalendarIdentity:
        return self.calendar_identity


@dataclass(frozen=True, slots=True)
class _Fixtures:
    clock: VpsClock
    venue: ConformanceDouble
    now: Instant

    @property
    def venue_id(self) -> VenueId:
        return self.venue.venue_id


def _fp(seed: str) -> Result[Fingerprint]:
    return fingerprint({"class": "d010", "seed": seed})


def _money(value: int) -> Result[Money]:
    return Money.try_create(value, "USD", 2)


def _qty(value: int) -> Result[Quantity]:
    return Quantity.try_create(value, "lot", 2)


def _r(numerator: int, denominator: int = 1) -> Result[ExactRational]:
    return ExactRational.try_create(numerator, denominator, UnitKind.R_MULTIPLE)


def _rate(numerator: int, denominator: int = 1) -> Result[ExactRational]:
    return ExactRational.try_create(numerator, denominator, UnitKind.RATE)


def _instrument(venue: VenueId, symbol: str = "EURUSD") -> Result[Instrument]:
    return Instrument.try_create(venue, symbol)


def _account(venue: VenueId, account_id: str, role: AccountRole) -> Result[Account]:
    return Account.try_create(account_id, venue, role)


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
            return row
        rows.append(row.value)
    return ControlRankTable.try_create(rows)


def _windows_for(binding_id: str) -> Result[tuple[WindowRecord, ...]]:
    built: list[WindowRecord] = []
    for kind in WindowKind:
        record = WindowRecord.try_create(
            window_id=f"{binding_id}-{kind.value}",
            kind=kind.value,
            binding_id=binding_id,
        )
        if is_refusal(record):
            return record
        built.append(record.value)
    return Ok(tuple(built))


def _risk_graph(venue: VenueId) -> Result[RuntimeRiskGraph]:
    venue_token = venue.value
    bms = _unwrap(
        PopulationBmsRecord.try_create(
            bms_instance_id="bms-1",
            venue_id=venue_token,
            account_id="acct-1",
            definition_fp1="bms-def-1",
        )
    )
    if isinstance(bms, TypedRefusal):
        return bms
    book_a = _unwrap(
        PopulationBookRecord.try_create(
            book_instance_id="book-1",
            bms_instance_id="bms-1",
            definition_fp1="book-def-1",
        )
    )
    if isinstance(book_a, TypedRefusal):
        return book_a
    book_b = _unwrap(
        PopulationBookRecord.try_create(
            book_instance_id="book-2",
            bms_instance_id="bms-1",
            definition_fp1="book-def-2",
        )
    )
    if isinstance(book_b, TypedRefusal):
        return book_b
    bind_a = _unwrap(
        PopulationBindingRecord.try_create(
            binding_id="bind-1",
            book_instance_id="book-1",
            bms_instance_id="bms-1",
            venue_id=venue_token,
            account_id="acct-1",
            role=AccountRole.LIVE,
            world=World.LIVE,
            environment="live",
            position_model="netting",
            instruments=frozenset({"EURUSD"}),
            attribution_instruments=frozenset({"EURUSD"}),
        )
    )
    if isinstance(bind_a, TypedRefusal):
        return bind_a
    bind_b = _unwrap(
        PopulationBindingRecord.try_create(
            binding_id="bind-2",
            book_instance_id="book-2",
            bms_instance_id="bms-1",
            venue_id=venue_token,
            account_id="acct-1",
            role=AccountRole.LIVE,
            world=World.LIVE,
            environment="live",
            position_model="netting",
            instruments=frozenset({"GBPUSD"}),
            attribution_instruments=frozenset({"GBPUSD"}),
        )
    )
    if isinstance(bind_b, TypedRefusal):
        return bind_b
    seat_a = _unwrap(
        SeatRecord.try_create(
            seat_id="seat-1",
            bot_id="bot-1",
            book_instance_id="book-1",
            binding_id="bind-1",
        )
    )
    if isinstance(seat_a, TypedRefusal):
        return seat_a
    seat_b = _unwrap(
        SeatRecord.try_create(
            seat_id="seat-2",
            bot_id="bot-2",
            book_instance_id="book-2",
            binding_id="bind-2",
        )
    )
    if isinstance(seat_b, TypedRefusal):
        return seat_b
    paired = _unwrap(
        PairedTargetRecord.try_create(
            live_binding_id="bind-1",
            paper_account_id="acct-demo",
            paper_role=AccountRole.DEMO,
            paper_bms_instance_id="bms-paper-1",
        )
    )
    if isinstance(paired, TypedRefusal):
        return paired
    ranks = _unwrap(_rank_table())
    if isinstance(ranks, TypedRefusal):
        return ranks
    priority = _unwrap(
        PriorityRecord.try_create(
            venue_id=venue_token,
            account_id="acct-1",
            rank_table=ranks,
        )
    )
    if isinstance(priority, TypedRefusal):
        return priority
    cap_a = _unwrap(
        CapabilityRecord.try_create(
            binding_id="bind-1",
            required=frozenset({"protective_stop"}),
            declared=frozenset({"protective_stop", "netting"}),
        )
    )
    if isinstance(cap_a, TypedRefusal):
        return cap_a
    cap_b = _unwrap(
        CapabilityRecord.try_create(
            binding_id="bind-2",
            required=frozenset({"protective_stop"}),
            declared=frozenset({"protective_stop", "netting"}),
        )
    )
    if isinstance(cap_b, TypedRefusal):
        return cap_b
    scope = _unwrap(ScopeRecord.try_create(kind="global"))
    if isinstance(scope, TypedRefusal):
        return scope
    windows_a = _unwrap(_windows_for("bind-1"))
    if isinstance(windows_a, TypedRefusal):
        return windows_a
    windows_b = _unwrap(_windows_for("bind-2"))
    if isinstance(windows_b, TypedRefusal):
        return windows_b
    return RuntimeRiskGraph.try_create(
        bms=(bms,),
        books=(book_a, book_b),
        bindings=(bind_a, bind_b),
        seats=(seat_a, seat_b),
        paired_targets=(paired,),
        windows=windows_a + windows_b,
        priorities=(priority,),
        capabilities=(cap_a, cap_b),
        scopes=(scope,),
    )


def _composition_inputs() -> Result[CompositionFingerprintInputs]:
    config = _fp("config-d010")
    cap = _fp("cap-ctrader")
    as_of = _fp("as-of-1")
    if is_refusal(config):
        return config
    if is_refusal(cap):
        return cap
    if is_refusal(as_of):
        return as_of
    return Ok(
        CompositionFingerprintInputs(
            config_fp=config.value,
            distribution_identities={
                "qmf": "lockstep",
                "qmb": "0.1.0",
                "qml": "0.1.0",
                "qmn": "0.1.0",
            },
            extension_identities={"qmf-calendar-forex": "1.0.0"},
            proto_release_tag="proto-1",
            tzdata_version="2026a",
            adapter_capability_fps=(cap.value,),
            registry_as_of_fp=as_of.value,
            calendar_code_identities={
                "market_hours_calendar": "mh-code-1",
                "day_boundary_calendar": "db-code-1",
                "news_calendar": "news-code-1",
            },
            os_cpu_class="linux-x86_64",
        )
    )


def _exercise_compose(fx: _Fixtures) -> Result[Mapping[str, object]]:
    graph = _risk_graph(fx.venue_id)
    if is_refusal(graph):
        return graph
    proof = admit_runtime_risk_population(graph.value)
    if is_refusal(proof):
        return proof
    inputs = _composition_inputs()
    if is_refusal(inputs):
        return inputs
    stream = f"{fx.venue_id.value}::acct-1"
    outcome = run_boot_ceremony(
        boot_epoch_id=_BOOT,
        machine=_MACHINE,
        composition_inputs=inputs.value,
        writer_streams=(
            ("command", stream),
            ("adapter", stream),
            ("risk", f"risk:{stream}"),
        ),
        risk_population=graph.value,
        boot_attempt_sink=InMemoryBootAttemptSink(),
        preflight=PreflightFacts(
            required_credential_refs=("venue-token",),
            credential_is_set={"venue-token": True},
        ),
    )
    if is_refusal(outcome):
        return outcome
    if not outcome.value.sealed:
        return policy(
            "compose",
            "the runtime risk gate requires Compose to Seal a valid population",
            failure_id="compose.risk_population",
        )
    return Ok(
        MappingProxyType(
            {
                "checks_run": list(proof.value.checks_run),
                "sealed": True,
            }
        )
    )


def _exercise_entry_preservation(fx: _Fixtures) -> Result[Mapping[str, object]]:
    venue = fx.venue_id
    instrument = _instrument(venue)
    if is_refusal(instrument):
        return instrument
    price = Price.try_create(110_000, instrument.value, 5)
    if is_refusal(price):
        return price
    target = ExecutionTarget.try_create(AccountRole.LIVE, venue, "acct-1")
    if is_refusal(target):
        return target
    reason = ReasonCode.try_create("momentum-break", "scalper-v1")
    if is_refusal(reason):
        return reason
    slot = EvidenceSlot.try_create("sqs", "sqs-ref-1", fx.now)
    if is_refusal(slot):
        return slot
    cited = CitedEvidence.try_create(sqs_reading=slot.value)
    if is_refusal(cited):
        return cited
    requested = _r(1)
    if is_refusal(requested):
        return requested
    entry = EntryIntent.try_create(
        instrument.value,
        Direction.LONG,
        reason.value,
        target.value,
        proposed_r=requested.value,
        cited_evidence=cited.value,
    )
    if is_refusal(entry):
        return entry
    logic = ExitLogicRef.try_create("book.default.evidence_stop", {"style": "structure"})
    if is_refusal(logic):
        return logic
    rate = _rate(1_000)
    if is_refusal(rate):
        return rate
    factor = ValueFactor.try_create(100_000, 1, instrument.value, "USD")
    if is_refusal(factor):
        return factor
    authorized = admit_entry_at_book_door(
        intent=entry.value,
        entry_price=price.value,
        exit_logic_ref=logic.value,
        module=_OffsetStopModule(),
        book_resolved_requested_r=requested.value,
        r_unit_price=rate.value,
        value_factor=factor.value,
        money_scale=2,
    )
    if is_refusal(authorized):
        return authorized
    account = _account(venue, "acct-1", AccountRole.LIVE)
    if is_refusal(account):
        return account
    command = mint_place_order_from_authorized(
        authorized.value,
        venue_id=venue,
        account=account.value,
        session_epoch=_SESSION,
        ordering_ordinal=1,
    )
    if is_refusal(command):
        return command
    epoch = _unwrap(_fp("epoch-entry"))
    if isinstance(epoch, TypedRefusal):
        return epoch
    cmd_fp = _unwrap(_fp("cmd-entry"))
    if isinstance(cmd_fp, TypedRefusal):
        return cmd_fp
    position = mint_virtual_from_authorized(
        authorized.value,
        binding_epoch=epoch,
        bot_id="bot-a",
        command_identity=cmd_fp,
    )
    if is_refusal(position):
        return position
    preserved = preserve_frozen_r(position.value, kind=PostAdmissionKind.FILL)
    if is_refusal(preserved):
        return preserved
    if preserved.value.rebased:
        return policy(
            "frozen_r",
            "a fill must not re-base frozen R except the journaled partial-entry path",
        )
    pnl = _unwrap(_money(-10_000))
    if isinstance(pnl, TypedRefusal):
        return pnl
    fill_fp = _unwrap(_fp("fill-1"))
    if isinstance(fill_fp, TypedRefusal):
        return fill_fp
    commission = _unwrap(_money(200))
    if isinstance(commission, TypedRefusal):
        return commission
    label = _unwrap(ExitResultLabel.try_create(AccountRole.LIVE, World.LIVE))
    if isinstance(label, TypedRefusal):
        return label
    venue_obs = _unwrap(_fp("venue-obs-1"))
    if isinstance(venue_obs, TypedRefusal):
        return venue_obs
    cost = _unwrap(CostComponent.try_create("commission", commission, "broker"))
    if isinstance(cost, TypedRefusal):
        return cost
    exit_record = mint_ct29_from_frozen_r(
        position.value,
        realized_pnl=pnl,
        fill_references=(fill_fp,),
        cost_components=(cost,),
        close_reason=CloseReason.PROTECTIVE_STOP_FILL,
        mechanism=CloseReason.PROTECTIVE_STOP_FILL,
        outcome=CloseOutcome.LOSS,
        closing_authority=ClosingAuthority.VENUE,
        close_reason_mapping_version=1,
        result_label=label,
        loss_predicate_format_version=1,
        recorded_at=fx.now,
        venue_observation_ref=venue_obs,
    )
    if is_refusal(exit_record):
        return exit_record
    return Ok(
        MappingProxyType(
            {
                "authorized_intent": authorized.value.fp1_identity(),
                "command_kind": command.value.kind.value,
                "exit_record": exit_record.value.fp1_identity(),
                "frozen_r": preserved.value.faces.fp1_identity(),
                "rebased": preserved.value.rebased,
            }
        )
    )


def _exercise_exits_under_blocks(fx: _Fixtures) -> Result[Mapping[str, object]]:
    instrument = _instrument(fx.venue_id)
    if is_refusal(instrument):
        return instrument
    start = _unwrap(Instant.try_create(_NS))
    if isinstance(start, TypedRefusal):
        return start
    end = _unwrap(Instant.try_create(_NS + 2_000_000_000))
    if isinstance(end, TypedRefusal):
        return end
    known = _unwrap(Instant.try_create(_NS - 100_000_000))
    if isinstance(known, TypedRefusal):
        return known
    bounds = WindowBounds.try_create(start, end)
    if is_refusal(bounds):
        return bounds
    exposure = CurrencyExposureRecord.try_create(instrument.value, ("USD",), start, "exp-1")
    if is_refusal(exposure):
        return exposure
    scope = resolve_instrument_scope(
        affected_currencies=("USD",),
        candidate_instruments=(instrument.value,),
        exposure_records=(exposure.value,),
    )
    if is_refusal(scope):
        return scope
    feed = FeedQuadruple.try_create("calendar-feed", "nfp-d010", "r1", known)
    if is_refusal(feed):
        return feed
    calendar = CalendarIdentity.try_create("forex-17NY", "v3", "2024a")
    if is_refusal(calendar):
        return calendar
    window = mint_control_window(
        bounds.value,
        WindowKind.NEWS,
        scope.value,
        "high-impact-news",
        calendar.value,
        "win-nfp-d010",
        feed_quadruple=feed.value,
    )
    if is_refusal(window):
        return window
    decision = Instant.try_create(_NS + 1_000_000_000)
    if is_refusal(decision):
        return decision
    blocked = enforce_entry_at_book_door(
        instrument=instrument.value,
        book_mode=BookMode.LIVE,
        decision_at=decision.value,
        windows=[window.value],
        would_have_been_action={"class": "would-have-been-entry", "symbol": "EURUSD"},
    )
    if is_refusal(blocked):
        return blocked
    exit_ok = allow_protective_act_under_windows(proposed_act=ProposedWindowAct.EXIT)
    if is_refusal(exit_ok):
        return exit_ok
    if not blocked.value.blocked:
        return policy(
            "window",
            "the D010 exits-under-blocks path requires an in-force entry block",
        )
    return Ok(
        MappingProxyType(
            {
                "entry_blocked": True,
                "exit_passed": True,
                "window_kind": window.value.window_kind.value,
            }
        )
    )


def _exercise_paper_routing(fx: _Fixtures) -> Result[Mapping[str, object]]:
    live_fp = _unwrap(_fp("live-binding-paper"))
    if isinstance(live_fp, TypedRefusal):
        return live_fp
    live_bms_fp = _unwrap(_fp("bms-live"))
    if isinstance(live_bms_fp, TypedRefusal):
        return live_bms_fp
    demo_bms_fp = _unwrap(_fp("bms-demo"))
    if isinstance(demo_bms_fp, TypedRefusal):
        return demo_bms_fp
    live_bms = BmsInstanceId.derive(live_bms_fp, "acct-live", fx.venue_id, World.LIVE)
    demo_bms = BmsInstanceId.derive(demo_bms_fp, "acct-demo", fx.venue_id, World.LIVE)
    if is_refusal(live_bms):
        return live_bms
    if is_refusal(demo_bms):
        return demo_bms
    paired = build_paired_demo_target(
        venue_id=fx.venue_id,
        account_id="acct-demo",
        live_bms_instance_id=live_bms.value,
        paired_bms_instance_id=demo_bms.value,
        live_binding_epoch=live_fp,
    )
    if is_refusal(paired):
        return paired
    live_target = ExecutionTarget.try_create(AccountRole.LIVE, fx.venue_id, "acct-live")
    if is_refusal(live_target):
        return live_target
    routed = resolve_book_execution_target(
        book_mode=BookMode.PAPER,
        seat_state=SeatState.ACTIVE,
        active_controls=(),
        live_target=live_target.value,
        paper_target=paired.value.paper_target,
        blocked_act="entry",
    )
    if is_refusal(routed):
        return routed
    book_id = BookInstanceId.try_create("book-inst-1")
    if is_refusal(book_id):
        return book_id
    start = _money(50_000_00)
    if is_refusal(start):
        return start
    flip = mint_operator_paper_flip(
        book_instance_id=book_id.value,
        live_binding_epoch=live_fp,
        transition_instant=fx.now,
        operator_signature="operator:sig-d010",
        starting_balance=start.value,
        paired=paired.value,
        transition_stream=BindingTransitionStream(),
        paper_target_log=PaperTargetLog(),
        paper_epoch_log=PaperEpochLog(),
    )
    if is_refusal(flip):
        return flip
    return Ok(
        MappingProxyType(
            {
                "bot_twin_minted": flip.value.bot_twin_minted,
                "book_twin_minted": flip.value.book_twin_minted,
                "mode": flip.value.transition.mode.value,
                "paper_role": paired.value.paper_target.role.value,
                "routing": routed.value.fp1_identity(),
            }
        )
    )


def _place_command(venue: VenueId, account: Account, ordinal: int) -> Result[Command]:
    instrument = _instrument(venue)
    if is_refusal(instrument):
        return instrument
    qty = Quantity.try_create(100, "lot", 2)
    if is_refusal(qty):
        return qty
    delta = PriceDelta.try_create(100, instrument.value, 5)
    if is_refusal(delta):
        return delta
    params = OrderParameters.try_create(
        OrderType.MARKET,
        TimeInForce.GOOD_TILL_CANCEL,
        qty.value,
        protective_stop_distance=delta.value,
    )
    if is_refusal(params):
        return params
    return Command.place_order(venue, account, _SESSION, ordinal, params.value)


def _unknown_submission(command: Command, now: Instant) -> Result[SubmissionResult]:
    fp = command.fingerprint()
    if is_refusal(fp):
        return fp
    elapsed = Duration.try_create(750_000_000)
    deadline = Instant.try_create(now.value_ns + 5_000_000_000)
    if is_refusal(elapsed):
        return elapsed
    if is_refusal(deadline):
        return deadline
    obs = CommandObservation(
        command_fp1=fp.value,
        kind=command.kind,
        outcome=SubmissionOutcome.UNKNOWN,
        receive_instant=now,
        unknown_trigger=UnknownTrigger.TIMEOUT,
        monotonic_elapsed=elapsed.value,
        submission_deadline=deadline.value,
        detail="lost transport certainty; UNKNOWN is a state",
    )
    return Ok(
        SubmissionResult(
            command_fp1=fp.value,
            kind=command.kind,
            outcome=SubmissionOutcome.UNKNOWN,
            observation=obs,
            journal_event=JournalEvent.for_outcome(
                fp.value, command.kind, SubmissionOutcome.UNKNOWN
            ),
        )
    )


def _exercise_unknown(fx: _Fixtures) -> Result[Mapping[str, object]]:
    account = _account(fx.venue_id, "acct-unknown", AccountRole.DEMO)
    if is_refusal(account):
        return account
    writer = venue_writer_id(_MACHINE, _ADAPTER, fx.venue_id, account.value, _BOOT)
    if is_refusal(writer):
        return writer
    manager = ConnectionManager.try_create(
        writer.value, _SecretStore(), _ObsSink(), _JournalSink(), _RecordSink()
    )
    if is_refusal(manager):
        return manager
    extent = UnknownIntentExtent.try_create(8)
    if is_refusal(extent):
        return extent
    boundary = CommandStreamUnknownBoundary.try_create(
        venue_id=fx.venue_id,
        account=account.value,
        connection_manager=manager.value,
        extent=extent.value,
    )
    if is_refusal(boundary):
        return boundary
    command = _place_command(fx.venue_id, account.value, 1)
    if is_refusal(command):
        return command
    unknown = _unknown_submission(command.value, fx.now)
    if is_refusal(unknown):
        return unknown
    block = boundary.value.record_unknown(unknown.value)
    if is_refusal(block):
        return block
    second = _place_command(fx.venue_id, account.value, 2)
    if is_refusal(second):
        return second
    admitted = boundary.value.admit(second.value, receive_instant=fx.now)
    if is_refusal(admitted):
        return admitted
    result = admitted.value
    if getattr(result, "disposition", None) is not AdmissionDisposition.REFUSED:
        return policy(
            "unknown",
            "an UNKNOWN block must refuse new entries on the same stream",
        )
    refusal = getattr(result, "refusal", None)
    if not isinstance(refusal, TypedRefusal):
        return invalid("unknown", "stream refuse must carry a typed refusal")
    if refusal.category is not RefusalCategory.TRANSIENT_VENUE_FAILURE:
        return policy(
            "unknown",
            "UNKNOWN entry refusal is transient venue failure, never a rejection label",
            given=refusal.category.value,
        )
    return Ok(
        MappingProxyType(
            {
                "block_cause": getattr(result, "block_cause", StreamBlockCause.OUTSTANDING_UNKNOWN),
                "outcome": unknown.value.outcome.value,
                "refusal_category": refusal.category.value,
                "sensing_continues": boundary.value.sensing_continues,
                "stream_open": boundary.value.stream_open,
            }
        )
    )


def _exercise_four_verdicts(fx: _Fixtures) -> Result[Mapping[str, object]]:
    del fx
    qty = _qty(100)
    drifted = _qty(150)
    cash = _money(50_000_00)
    if is_refusal(qty):
        return qty
    if is_refusal(drifted):
        return drifted
    if is_refusal(cash):
        return cash
    reconciled = run_reconciliation(
        trigger=ReconciliationTrigger.STARTUP,
        role=AccountRole.LIVE,
        quantity_pairs=(("EURUSD", qty.value, qty.value),),
        venue_realized_balance=cash.value,
        virtual_realized_cash=cash.value,
    )
    drift = run_reconciliation(
        trigger=ReconciliationTrigger.SCHEDULED,
        role=AccountRole.LIVE,
        quantity_pairs=(("EURUSD", qty.value, drifted.value),),
        venue_realized_balance=cash.value,
        virtual_realized_cash=cash.value,
    )
    unknown = run_reconciliation(
        trigger=ReconciliationTrigger.AFTER_UNKNOWN,
        role=AccountRole.LIVE,
        readback_status=ReadbackStatus.ABSENT,
    )
    lookback = run_reconciliation(
        trigger=ReconciliationTrigger.RECONNECT,
        role=AccountRole.LIVE,
        lookback_status=LookbackStatus.OUT_OF_LOOKBACK,
    )
    if is_refusal(reconciled):
        return reconciled
    if is_refusal(drift):
        return drift
    if is_refusal(unknown):
        return unknown
    if is_refusal(lookback):
        return lookback
    observed = {
        reconciled.value.verdict.value,
        drift.value.verdict.value,
        unknown.value.verdict.value,
        lookback.value.verdict.value,
    }
    if observed != set(FOUR_VERDICTS):
        return policy(
            "reconciliation",
            "the runtime risk gate must produce all four reconciliation verdicts",
            observed=sorted(observed),
            required=sorted(FOUR_VERDICTS),
        )
    return Ok(
        MappingProxyType(
            {
                "drift": drift.value.as_mapping(),
                "out_of_lookback": lookback.value.as_mapping(),
                "reconciled": reconciled.value.as_mapping(),
                "unknown": unknown.value.as_mapping(),
                "verdicts": sorted(observed),
            }
        )
    )


def _exercise_priority_compose(fx: _Fixtures) -> Result[Mapping[str, object]]:
    stream = CommandStreamKey.try_create(fx.venue_id, "acct-1")
    if is_refusal(stream):
        return stream
    table = _rank_table()
    if is_refusal(table):
        return table
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
    if is_refusal(suspend):
        return suspend
    if is_refusal(flatten):
        return flatten
    enforcement = EnforcementScope(
        subject_scope=SubjectScope.BINDING,
        scope_ref="binding-1",
        stream=stream.value,
    )
    cand_a = DispatchCandidate.try_create(
        suspend.value, enforcement, origin="ct30", arrival_ordinal=99
    )
    cand_b = DispatchCandidate.try_create(
        flatten.value, enforcement, origin="ct30", arrival_ordinal=0
    )
    if is_refusal(cand_a):
        return cand_a
    if is_refusal(cand_b):
        return cand_b
    plan = dispatch_ranked_controls(
        [cand_a.value, cand_b.value],
        table.value,
        stream=stream.value,
        arbitration_seed="d010-compose",
    )
    if is_refusal(plan):
        return plan
    kinds = {item.record.action_kind.value for item in plan.value.emit}
    expected = {
        ControlActionKind.SUSPEND_NEW.value,
        ControlActionKind.FLATTEN.value,
    }
    if kinds != expected:
        return policy(
            "compose",
            "suspend_new and flatten on one tick must both execute",
            emit=sorted(kinds),
        )
    return Ok(
        MappingProxyType(
            {
                "arrival_order_ignored": plan.value.arrival_order_ignored,
                "emit": sorted(kinds),
                "suppressed": len(plan.value.suppressed),
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
    close_reason: CloseReason = CloseReason.PROTECTIVE_STOP_FILL,
    authority: ClosingAuthority = ClosingAuthority.VENUE,
) -> Result[ExitRecord]:
    venue = _unwrap(VenueId.try_create("ctrader"))
    if isinstance(venue, TypedRefusal):
        return venue
    instrument = _unwrap(Instrument.try_create(venue, "EURUSD"))
    if isinstance(instrument, TypedRefusal):
        return instrument
    distance = _unwrap(PriceDelta.try_create(50, instrument, 5))
    if isinstance(distance, TypedRefusal):
        return distance
    amount = _unwrap(_money(10_000))
    if isinstance(amount, TypedRefusal):
        return amount
    pnl = _unwrap(_money(realized_pnl))
    if isinstance(pnl, TypedRefusal):
        return pnl
    fill = _unwrap(_fp(f"fill-{seed}"))
    if isinstance(fill, TypedRefusal):
        return fill
    pos = _unwrap(_fp(seed))
    if isinstance(pos, TypedRefusal):
        return pos
    label = _unwrap(ExitResultLabel.try_create(AccountRole.LIVE, World.LIVE))
    if isinstance(label, TypedRefusal):
        return label
    arb_fp: Fingerprint | None = None
    vobs_fp: Fingerprint | None = None
    if authority is not ClosingAuthority.VENUE:
        arb = _unwrap(_fp(f"arb-{seed}"))
        if isinstance(arb, TypedRefusal):
            return arb
        arb_fp = arb
    else:
        vobs = _unwrap(_fp(f"venue-obs-{seed}"))
        if isinstance(vobs, TypedRefusal):
            return vobs
        vobs_fp = vobs
    return mint_exit_record(
        virtual_position_ref=pos,
        opening_bot_id="bot-alpha",
        original_risk_distance=distance,
        original_risk_amount=amount,
        fill_references=(fill,),
        realized_pnl=pnl,
        cost_components=(),
        close_reason=close_reason,
        mechanism=close_reason,
        outcome=outcome,
        closing_authority=authority,
        close_reason_mapping_version=1,
        result_label=label,
        loss_predicate_format_version=1,
        binding_epoch=epoch,
        recorded_at=now,
        arbitration_record_ref=arb_fp,
        venue_observation_ref=vobs_fp,
    )


def _exercise_bench(fx: _Fixtures) -> Result[Mapping[str, object]]:
    epoch = _fp("epoch-bench")
    q = _r(1)
    if is_refusal(epoch):
        return epoch
    if is_refusal(q):
        return q
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
            close_reason=reason,
            authority=authority,
        )
        if is_refusal(minted):
            return minted
        records.append(minted.value)
    report = evaluate_qualifying_loss_bench(
        tuple(records),
        binding_epoch=epoch.value,
        q=q.value,
        threshold=2,
    )
    if is_refusal(report):
        return report
    live = ExecutionTarget.try_create(AccountRole.LIVE, fx.venue_id, "acct-live")
    paper = ExecutionTarget.try_create(AccountRole.DEMO, fx.venue_id, "acct-demo")
    if is_refusal(live):
        return live
    if is_refusal(paper):
        return paper
    effect = apply_bench_crossing(
        report.value,
        live_target=live.value,
        paper_target=paper.value,
        book_mode=BookMode.LIVE,
    )
    if is_refusal(effect):
        return effect
    return Ok(
        MappingProxyType(
            {
                "book_mode": effect.value.book_mode.value,
                "breakeven_clustering_count": report.value.breakeven_clustering_count,
                "qualifying_loss_count": report.value.qualifying_loss_count,
                "seat_state": effect.value.seat_state.value,
                "threshold_crossed": report.value.threshold_crossed,
            }
        )
    )


def _exercise_kill_line(fx: _Fixtures) -> Result[Mapping[str, object]]:
    floor = _money(80_000_00)
    equity = _money(70_000_00)
    if is_refusal(floor):
        return floor
    if is_refusal(equity):
        return equity
    evaluation = evaluate_kill_line(
        binding_scope_ref="binding-a",
        equity=equity.value,
        kill_line_capital_floor=floor.value,
        loss_floor=floor.value,
        evaluated_at=fx.now,
    )
    if is_refusal(evaluation):
        return evaluation
    live = ExecutionTarget.try_create(AccountRole.LIVE, fx.venue_id, "acct-live")
    paper = ExecutionTarget.try_create(AccountRole.DEMO, fx.venue_id, "acct-demo")
    if is_refusal(live):
        return live
    if is_refusal(paper):
        return paper
    package = apply_kill_line_breach(
        evaluation.value,
        venue_id=fx.venue_id,
        account_id="acct-live",
        live_target=live.value,
        paper_target=paper.value,
        book_mode=BookMode.LIVE,
    )
    if is_refusal(package):
        return package
    return Ok(
        MappingProxyType(
            {
                "binding_state": package.value.binding_state.value,
                "book_mode": package.value.book_mode.value,
                "breached": evaluation.value.breached,
                "close_reason": package.value.close_reason.value,
                "other_bindings_unaffected": package.value.other_bindings_unaffected,
            }
        )
    )


def _exercise_next_day_activation(fx: _Fixtures) -> Result[Mapping[str, object]]:
    card = _fp("promo-card")
    if is_refusal(card):
        return card
    landing = PromotionLanding(
        seat_id="seat-1",
        binding_id="binding-1",
        card_fp1=card.value,
        fingerprints={"book": "book", "bms": "bms", "bot": "bot"},
        battery=SilentBatteryReport(
            checks=(),
            passed=True,
            refusing_check=None,
            refusing_check_id=None,
        ),
    )
    identity = CalendarIdentity.try_create("account-day-boundary", "v1", "2026a")
    if is_refusal(identity):
        return identity
    accepted = request_activation(
        principal=OPERATOR_PRINCIPAL,
        landing=landing,
        signed_at=fx.now,
        day_boundary=_DayBoundary(identity.value, _BOUNDARY_NS),
        operator_signature="sig-operator-activate",
    )
    if is_refusal(accepted):
        return accepted
    if accepted.value.may_trade:
        return policy(
            "activation",
            "activation accepted mid-day must not trade until the next day-boundary",
        )
    if accepted.value.enforced_state is not GovernedSeatState.ADMITTED:
        return policy(
            "activation",
            "activation is accepted now and enforced only after the day-boundary",
            enforced=accepted.value.enforced_state.value,
        )
    if accepted.value.schedule.effective_at.value_ns <= fx.now.value_ns:
        return policy(
            "activation",
            "activation effective-at must be the next account day-boundary",
        )
    return Ok(
        MappingProxyType(
            {
                **accepted.value.as_mapping(),
                "same_day_trade_path_exists": False,
            }
        )
    )


def _exercise_journal_before_dispatch() -> Result[Mapping[str, object]]:
    receipt = journal_before_effect(
        kind="control",
        payload={"class": "d010-control", "action": "flatten"},
        journal=RecordingJournalSink(),
        dispatcher=RecordingEffectDispatcher(),
    )
    if is_refusal(receipt):
        return receipt
    failed = journal_before_effect(
        kind="control",
        payload={"class": "d010-control", "action": "flatten"},
        journal=RecordingJournalSink(fail=True),
        dispatcher=RecordingEffectDispatcher(),
    )
    if is_ok(failed):
        return policy(
            "journal",
            "a journal sink refusal must block dispatch",
        )
    venue = VenueId.try_create("ctrader")
    if is_refusal(venue):
        return venue
    stream = CommandStreamKey.try_create(venue.value, "acct-1")
    if is_refusal(stream):
        return stream
    issued = Instant.try_create(_NS)
    if is_refusal(issued):
        return issued
    record = mint_control_action(
        ControlActionKind.FLATTEN,
        "book-1",
        AuthorityKind.BOOK_POLICY,
        SubjectScope.BINDING,
        "binding-1",
        1,
        "kill-line",
        stream.value,
        issued.value,
        trigger_class="kill_line_breach",
    )
    if is_refusal(record):
        return record
    blocked = block_dispatch_on_journal_failure(
        record.value, journal_result=unpersistable("disk full")
    )
    if is_ok(blocked):
        return policy(
            "journal",
            "CT-25 storage failure must block dispatch",
        )
    return Ok(
        MappingProxyType(
            {
                "journaled_kind": receipt.value.kind,
                "storage_failure_blocks_dispatch": True,
            }
        )
    )


def _produce_refusal_categories(fx: _Fixtures) -> Result[dict[str, str]]:
    """Named production paths for every CT-04 category — not enum tautologies."""
    paths: dict[str, str] = {}

    invalid_book = BookDefinition.try_create(2, 1.5, {})
    if not is_refusal(invalid_book):
        return policy("refusal_category", "CT-22 must refuse a non-USD/non-string currency")
    if invalid_book.category is not RefusalCategory.INVALID_INPUT:
        # non-USD string is policy; a float/non-string should be invalid input.
        unsupported_version = BookDefinition.try_create(99, "USD", {})
        if not is_refusal(unsupported_version):
            return policy("refusal_category", "unknown Book format must refuse")
        if unsupported_version.category is RefusalCategory.UNSUPPORTED_CAPABILITY:
            paths[RefusalCategory.UNSUPPORTED_CAPABILITY.value] = (
                "BookDefinition.try_create/unknown-format"
            )
        invalid_intent = admit_entry_at_book_door(
            intent="not-an-intent",
            entry_price="x",
            exit_logic_ref="y",
            module=_OffsetStopModule(),
            book_resolved_requested_r="z",
            r_unit_price="z",
            value_factor="z",
            money_scale=2,
        )
        if is_refusal(invalid_intent):
            paths[invalid_intent.category.value] = "admit_entry_at_book_door/invalid"
    else:
        paths[RefusalCategory.INVALID_INPUT.value] = "BookDefinition.try_create/invalid-currency"

    close_partial = refuse_close_partial()
    paths[close_partial.category.value] = "refuse_close_partial"

    graph = _risk_graph(fx.venue_id)
    if is_refusal(graph):
        return graph
    dangling = SeatRecord.try_create(
        seat_id="seat-x",
        bot_id="bot-x",
        book_instance_id="book-1",
        binding_id="missing-bind",
    )
    if is_refusal(dangling):
        return dangling
    bad = replace(graph.value, seats=(*graph.value.seats, dangling.value))
    missing = admit_runtime_risk_population(bad)
    if not is_refusal(missing):
        return policy(
            "refusal_category",
            "a dangling seat must refuse Layer-1 population admission",
        )
    paths[missing.category.value] = "admit_runtime_risk_population/referential_integrity"

    stale = refuse_stale_exit_before_intent(
        closing_exit_record=None, persisted=False, journaled=False
    )
    if not is_refusal(stale):
        return policy("refusal_category", "stale exit must refuse the next intent")
    paths[stale.category.value] = "refuse_stale_exit_before_intent"

    paper = refuse_paper_profit_as_proof()
    paths[paper.category.value] = "refuse_paper_profit_as_proof"

    unknown = _exercise_unknown(fx)
    if is_refusal(unknown):
        return unknown
    paths[str(unknown.value["refusal_category"])] = (
        "CommandStreamUnknownBoundary.admit/place_under_unknown"
    )

    storage = journal_before_effect(
        kind="control",
        payload={"class": "d010-storage"},
        journal=RecordingJournalSink(fail=True),
        dispatcher=RecordingEffectDispatcher(),
    )
    if not is_refusal(storage):
        return policy("refusal_category", "journal failure must be a storage failure")
    paths[storage.category.value] = "journal_before_effect/storage_failure"

    unsupported = BookDefinition.try_create(99, "USD", {})
    if is_refusal(unsupported):
        paths[unsupported.category.value] = "BookDefinition.try_create/unknown-format"

    if RefusalCategory.INVALID_INPUT.value not in paths:
        no_stop = _instrument(fx.venue_id)
        if is_refusal(no_stop):
            return no_stop
        price = Price.try_create(110_000, no_stop.value, 5)
        if is_refusal(price):
            return price
        target = ExecutionTarget.try_create(AccountRole.LIVE, fx.venue_id, "acct-1")
        if is_refusal(target):
            return target
        reason = ReasonCode.try_create("momentum-break", "scalper-v1")
        if is_refusal(reason):
            return reason
        slot = EvidenceSlot.try_create("sqs", "sqs-ref-1", fx.now)
        if is_refusal(slot):
            return slot
        cited = CitedEvidence.try_create(sqs_reading=slot.value)
        if is_refusal(cited):
            return cited
        requested = _r(1)
        if is_refusal(requested):
            return requested
        entry = EntryIntent.try_create(
            no_stop.value,
            Direction.LONG,
            reason.value,
            target.value,
            proposed_r=requested.value,
            cited_evidence=cited.value,
        )
        if is_refusal(entry):
            return entry
        logic = ExitLogicRef.try_create("book.default.evidence_stop", {"style": "structure"})
        if is_refusal(logic):
            return logic
        rate = _rate(1_000)
        if is_refusal(rate):
            return rate
        factor = ValueFactor.try_create(100_000, 1, no_stop.value, "USD")
        if is_refusal(factor):
            return factor
        refused_entry = admit_entry_at_book_door(
            intent=entry.value,
            entry_price=price.value,
            exit_logic_ref=logic.value,
            module=_NoStopModule(),
            book_resolved_requested_r=requested.value,
            r_unit_price=rate.value,
            value_factor=factor.value,
            money_scale=2,
        )
        if is_refusal(refused_entry):
            paths[refused_entry.category.value] = "admit_entry_at_book_door/no-full-loss"

    return Ok(paths)
