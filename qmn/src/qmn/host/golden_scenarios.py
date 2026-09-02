"""Wire and prove SCN-0006/0008/0010/0011 through the node composition (Story 28.5).

Each golden scenario runs on the sealed composition root with an injected clock
and the FEAT-0023 conformance double. Fixtures carry proof key, COMP/CT/DEC/GAP
citations, Given/When/Then, clock, seed, source class, and fp1. Synthetic data
proves infrastructure and failure handling only — never trading edge (L20).
FTR-07: the runner invents no KSA matrix values or latency gates.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, TypeVar

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
    Ok,
    PriceDelta,
    Quantity,
    Result,
    SinkAck,
    SinkResult,
    TypedRefusal,
    UnitKind,
    VenueId,
    World,
    fingerprint,
    is_ok,
    is_refusal,
    unpersistable,
)
from qmf.risk.binding import BmsInstanceId, BookInstanceId, PositionModel
from qmf.risk.control_action import (
    AuthorityKind,
    CommandStreamKey,
    ControlActionRecord,
    EnforcementScope,
    ReconciliationVerdict,
    RiskReducingAct,
    SubjectScope,
    SuppressedControlAction,
    check_exit_preservation,
    mint_control_action,
    resolve_subject_scope,
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
    CostComponent,
    ExitRecord,
    ExitResultLabel,
    mint_exit_record,
)
from qmf.risk.paper import (
    BindingTransitionStream,
    BookMode,
    ExecutionTarget,
    PaperEpochLog,
    PaperTargetLog,
    RoutingOutcome,
    SeatState,
)

from qmn.capital import (
    OPERATOR_KILL_LINE_RESUME,
    apply_bench_crossing,
    refuse_stale_exit_before_intent,
    restore_kill_line_stand_down,
)
from qmn.capital.bench_fold import BENCH_FOLD_FIXTURE, evaluate_qualifying_loss_bench
from qmn.data.news_calendar import (
    FOREX_FACTORY_WEEKLY_JSON,
    SOLE_V1_PROVIDER,
    refuse_paid_news_provider,
    refuse_second_news_source,
    require_sole_free_provider,
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
from qmn.ledger import refuse_paper_pnl_to_treasury
from qmn.order import CommandStreamUnknownBoundary
from qmn.order.unknown import ProtectionIntentExtent as UnknownIntentExtent
from qmn.paper import (
    build_paired_demo_target,
    fold_book_mode,
    inspect_bot_node_journey,
    mint_operator_paper_flip,
    resolve_book_execution_target,
)
from qmn.protection import (
    CandidateOrigin,
    DispatchCandidate,
    KsaEnforcementScope,
    NewsRevisionDisposition,
    ProtectionIntentExtent,
    WindowActDisposition,
    allow_protective_act_under_windows,
    apply_news_revision,
    dispatch_ranked_controls,
    enforce_entry_at_book_door,
    matrix_supplies_no_default_values,
    persist_protective_intent,
    redecide_protective_intent,
    refuse_live_skip_at_door,
    refuse_symbol_currency_parse_at_door,
    require_total_unique_rank_table,
    stale_news_calendar_blocks_entries,
    stream_blocked_by_escalation,
    stream_dispatcher_key,
)
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
    "GOLDEN_PROOF_KEYS",
    "GOLDEN_SCENARIO_CLASS",
    "GOLDEN_SCENARIO_FORMAT_VERSION",
    "GOLDEN_SCENARIO_IDS",
    "GOLDEN_SCENARIO_SURFACE",
    "SOURCE_CLASS_SYNTHETIC",
    "TRADING_EDGE_IS_PROOF",
    "GoldenFixtureProof",
    "GoldenScenarioInputs",
    "GoldenScenarioReport",
    "refuse_golden_invented_ksa_or_latency",
    "refuse_golden_trading_edge_claim",
    "run_paper_milestone_golden_scenarios",
]

T = TypeVar("T")

GOLDEN_SCENARIO_SURFACE: Final[str] = "qmn.host.golden_scenarios"
GOLDEN_SCENARIO_CLASS: Final[str] = "paper-milestone-golden-scenarios"
GOLDEN_SCENARIO_FORMAT_VERSION: Final[int] = 1
TRADING_EDGE_IS_PROOF: Final[bool] = False
SOURCE_CLASS_SYNTHETIC: Final[str] = "synthetic"

GOLDEN_SCENARIO_IDS: Final[tuple[str, ...]] = (
    "SCN-0006",
    "SCN-0008",
    "SCN-0010",
    "SCN-0011",
)

GOLDEN_PROOF_KEYS: Final[tuple[str, ...]] = (
    "qmn/paper-transition",
    "qmn/news-window",
    "qmn/news-window/narrowing-revision",
    "qmn/compose-pair/suspend-plus-flatten",
    BENCH_FOLD_FIXTURE,
)

_ID_INPUTS = "golden_scenarios.inputs"
_ID_INVENTED = "golden_scenarios.invented_ksa_or_latency"
_ID_EDGE = "golden_scenarios.trading_edge"
_ID_VENUE = "golden_scenarios.venue"
_ID_FIXTURE = "golden_scenarios.fixture_metadata"

_MACHINE: Final[str] = "vps-28-5"
_ADAPTER: Final[str] = "conformance-double"
_BOOT: Final[str] = "boot-28-5"
_SESSION: Final[str] = "session-28-5"
_DEFAULT_SEED: Final[str] = "story-28-5"

_COMPONENTS_NODE: Final[tuple[str, ...]] = ("COMP-QMN", "COMP-QMF-RISK")
_GAPS_FTR07: Final[tuple[str, ...]] = ("GAP-0050",)


@dataclass(frozen=True, slots=True)
class _FixtureSpec:
    scenario: str
    proof_key: str
    components: tuple[str, ...]
    contracts: tuple[str, ...]
    decisions: tuple[str, ...]
    gaps: tuple[str, ...]
    given: str
    when: str
    then: str


_FIXTURE_SPECS: Final[tuple[_FixtureSpec, ...]] = (
    _FixtureSpec(
        scenario="SCN-0006",
        proof_key="qmn/paper-transition",
        components=_COMPONENTS_NODE,
        contracts=("CT-24", "CT-28", "CT-23", "CT-19"),
        decisions=("DEC-0149", "DEC-0143", "DEC-0150", "DEC-0205", "DEC-0208"),
        gaps=_GAPS_FTR07,
        given=(
            "A LIVE Book with a paired demo target, an injected clock, and the "
            "sealed node composition"
        ),
        when="Book paper transition and routing execute",
        then=(
            "the append-only epoch, frozen per-intent target, separate-stream "
            "UNKNOWN, immutable paper money, and human-signed return behavior "
            "match the scenario exactly"
        ),
    ),
    _FixtureSpec(
        scenario="SCN-0008",
        proof_key="qmn/news-window",
        components=("COMP-QMN", "COMP-QMF-RISK", "COMP-CALENDAR-FEED"),
        contracts=("CT-31", "CT-10", "CT-23"),
        decisions=("DEC-0152", "DEC-0150", "DEC-0214", "DEC-0208"),
        gaps=_GAPS_FTR07,
        given=(
            "Declared currency-exposure records, an in-force news window, a dead "
            "zone, and Forex Factory as the sole free source"
        ),
        when="pair-scoped news windows and revisions execute",
        then=(
            "declared exposure, fail-closed missing scope/staleness, entry-only "
            "block, exit preservation, widen-not-shrink, and sole free-source "
            "evidence match exactly"
        ),
    ),
    _FixtureSpec(
        scenario="SCN-0008",
        proof_key="qmn/news-window/narrowing-revision",
        components=("COMP-QMN", "COMP-QMF-RISK", "COMP-CALENDAR-FEED"),
        contracts=("CT-31", "CT-10"),
        decisions=("DEC-0152", "DEC-0208"),
        gaps=_GAPS_FTR07,
        given="An in-force news window with a later narrowing revision",
        when="the news-calendar revision is applied at the Book door",
        then=(
            "a narrowing revision does not open entries before the in-force "
            "window's declared end; widen-and-add apply automatically"
        ),
    ),
    _FixtureSpec(
        scenario="SCN-0010",
        proof_key="qmn/compose-pair/suspend-plus-flatten",
        components=_COMPONENTS_NODE,
        contracts=("CT-30", "CT-29", "CT-18"),
        decisions=("DEC-0150", "DEC-0151", "DEC-0208", "DEC-0209"),
        gaps=_GAPS_FTR07,
        given="One (VenueId, account) command stream with a BMS total unique rank table",
        when="conflicting/composing controls execute",
        then=(
            "one arbiter per stream, total rank, collapse/conflict/compose, scope "
            "refusal, and exit preservation match exactly"
        ),
    ),
    _FixtureSpec(
        scenario="SCN-0011",
        proof_key=BENCH_FOLD_FIXTURE,
        components=_COMPONENTS_NODE,
        contracts=("CT-29", "CT-24", "CT-23"),
        decisions=("DEC-0155", "DEC-0149", "DEC-0208", "DEC-0209"),
        gaps=_GAPS_FTR07,
        given="A LIVE Book, an active seat, and four CT-29 virtual-position closes",
        when="virtual-position exits and bench fold execute",
        then=(
            "one CT-29 record per close, breakeven exclusion, stale-evidence "
            "refusal, binding-epoch counter, and seat-to-paper/Book-LIVE routing "
            "match exactly"
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class GoldenScenarioInputs:
    """Injected clock, conformance double, and Book-declared numeric fixtures."""

    clock: VpsClock
    venue: ConformanceDouble
    paper_starting_balance: Money
    qualifying_loss_threshold: ExactRational
    bench_consecutive_loss_threshold: int
    news_calendar_max_staleness: Duration
    seed: str = _DEFAULT_SEED
    invent_ksa_matrix_values: bool = False
    invent_latency_gate: bool = False
    claim_trading_edge: bool = False


@dataclass(frozen=True, slots=True)
class GoldenFixtureProof:
    """One executable golden-scenario fixture with TN-23 identity metadata."""

    scenario: str
    proof_key: str
    components: tuple[str, ...]
    contracts: tuple[str, ...]
    decisions: tuple[str, ...]
    gaps: tuple[str, ...]
    given: str
    when: str
    then: str
    clock_ns: int
    seed: str
    source_class: str
    fingerprint: Fingerprint
    evidence: Mapping[str, object]
    trading_edge_claimed: bool = False

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "golden-fixture-proof",
            "clock_ns": self.clock_ns,
            "components": list(self.components),
            "contracts": list(self.contracts),
            "decisions": list(self.decisions),
            "evidence": dict(self.evidence),
            "gaps": list(self.gaps),
            "given": self.given,
            "proof_key": self.proof_key,
            "scenario": self.scenario,
            "seed": self.seed,
            "source_class": self.source_class,
            "then": self.then,
            "trading_edge_claimed": self.trading_edge_claimed,
            "when": self.when,
        }

    def as_mapping(self) -> Mapping[str, object]:
        body = self.fp1_identity()
        body["fingerprint"] = self.fingerprint.value
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class GoldenScenarioReport:
    """Fingerprinted proof that the four golden scenarios ran through composition."""

    format_version: int
    fingerprint: Fingerprint
    composition_sealed: bool
    scenarios_proven: tuple[str, ...]
    fixtures: tuple[GoldenFixtureProof, ...]
    source_class: str
    invents_ksa_or_latency: bool
    ksa_matrix_values_supplied: bool
    trading_edge_is_proof: bool
    synthetic_proves_infrastructure_only: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": GOLDEN_SCENARIO_CLASS,
            "composition_sealed": self.composition_sealed,
            "fixtures": [item.fingerprint.value for item in self.fixtures],
            "format_version": self.format_version,
            "invents_ksa_or_latency": self.invents_ksa_or_latency,
            "ksa_matrix_values_supplied": self.ksa_matrix_values_supplied,
            "proof_keys": [item.proof_key for item in self.fixtures],
            "scenarios_proven": list(self.scenarios_proven),
            "source_class": self.source_class,
            "surface": GOLDEN_SCENARIO_SURFACE,
            "synthetic_proves_infrastructure_only": (self.synthetic_proves_infrastructure_only),
            "trading_edge_is_proof": self.trading_edge_is_proof,
        }

    def as_mapping(self) -> Mapping[str, object]:
        body = self.fp1_identity()
        body["fingerprint"] = self.fingerprint.value
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class _Fixtures:
    clock: VpsClock
    venue: ConformanceDouble
    now: Instant
    seed: str
    paper_starting_balance: Money
    qualifying_loss_threshold: ExactRational
    bench_consecutive_loss_threshold: int
    news_calendar_max_staleness: Duration

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


def refuse_golden_invented_ksa_or_latency(**extra: object) -> TypedRefusal:
    """FTR-07: golden proofs never fill KSA matrix values or latency gates."""
    return policy(
        "invented-value",
        "KSA matrix values remain a pre-soak operator ratification and numeric "
        "hot-path/latency gates remain unset until measured baselines exist; "
        "golden-scenario proofs invent neither (FTR-07)",
        failure_id=_ID_INVENTED,
        **extra,
    )


def refuse_golden_trading_edge_claim(**extra: object) -> TypedRefusal:
    """Synthetic fixtures prove infrastructure/failure only, never trading edge."""
    return policy(
        "trading_edge",
        "synthetic golden-scenario fixtures prove infrastructure and failure "
        "handling only; they never validate trading edge (L20; DEC-0054)",
        failure_id=_ID_EDGE,
        source_class=SOURCE_CLASS_SYNTHETIC,
        trading_edge_is_proof=False,
        **extra,
    )


def run_paper_milestone_golden_scenarios(
    inputs: object,
) -> Result[GoldenScenarioReport]:
    """Execute SCN-0006/0008/0010/0011 through the sealed composition root."""
    if not isinstance(inputs, GoldenScenarioInputs):
        return invalid(
            "inputs",
            "the golden-scenario runner takes GoldenScenarioInputs",
            given=type(inputs).__name__,
            failure_id=_ID_INPUTS,
        )
    if inputs.invent_ksa_matrix_values is True or inputs.invent_latency_gate is True:
        return refuse_golden_invented_ksa_or_latency(
            invent_ksa_matrix_values=inputs.invent_ksa_matrix_values,
            invent_latency_gate=inputs.invent_latency_gate,
        )
    if inputs.claim_trading_edge is True:
        return refuse_golden_trading_edge_claim()
    if inputs.venue.kind is not VenueClientKind.CONFORMANCE:
        return policy(
            "venue",
            "Story 28.5 proves golden scenarios on the FEAT-0023 conformance "
            "double, never live or replay",
            given=inputs.venue.kind.value,
            failure_id=_ID_VENUE,
        )
    if not matrix_supplies_no_default_values():
        return refuse_golden_invented_ksa_or_latency(matrix_defaulted=True)

    now = _unwrap(inputs.clock.wall_now())
    if isinstance(now, TypedRefusal):
        return now
    fx = _Fixtures(
        clock=inputs.clock,
        venue=inputs.venue,
        now=now,
        seed=inputs.seed,
        paper_starting_balance=inputs.paper_starting_balance,
        qualifying_loss_threshold=inputs.qualifying_loss_threshold,
        bench_consecutive_loss_threshold=inputs.bench_consecutive_loss_threshold,
        news_calendar_max_staleness=inputs.news_calendar_max_staleness,
    )

    composed = _unwrap(_exercise_compose(fx))
    if isinstance(composed, TypedRefusal):
        return composed
    scn0006 = _unwrap(_exercise_scn0006(fx))
    if isinstance(scn0006, TypedRefusal):
        return scn0006
    scn0008 = _unwrap(_exercise_scn0008(fx))
    if isinstance(scn0008, TypedRefusal):
        return scn0008
    scn0010 = _unwrap(_exercise_scn0010(fx))
    if isinstance(scn0010, TypedRefusal):
        return scn0010
    scn0011 = _unwrap(_exercise_scn0011(fx))
    if isinstance(scn0011, TypedRefusal):
        return scn0011

    evidence_by_key: dict[str, Mapping[str, object]] = {
        "qmn/paper-transition": scn0006,
        "qmn/news-window": scn0008,
        "qmn/news-window/narrowing-revision": scn0008,
        "qmn/compose-pair/suspend-plus-flatten": scn0010,
        BENCH_FOLD_FIXTURE: scn0011,
    }
    fixtures = _unwrap(_stamp_fixtures(fx, evidence_by_key))
    if isinstance(fixtures, TypedRefusal):
        return fixtures
    proven = tuple(dict.fromkeys(item.scenario for item in fixtures))
    if proven != GOLDEN_SCENARIO_IDS:
        return policy(
            "scenarios",
            "every golden scenario must be proven through the composition root",
            proven=list(proven),
            required=list(GOLDEN_SCENARIO_IDS),
            failure_id=_ID_FIXTURE,
        )
    identity = {
        "class": GOLDEN_SCENARIO_CLASS,
        "composition_sealed": composed["sealed"] is True,
        "fixtures": [item.fingerprint.value for item in fixtures],
        "format_version": GOLDEN_SCENARIO_FORMAT_VERSION,
        "invents_ksa_or_latency": False,
        "ksa_matrix_values_supplied": False,
        "proof_keys": [item.proof_key for item in fixtures],
        "scenarios_proven": list(proven),
        "source_class": SOURCE_CLASS_SYNTHETIC,
        "surface": GOLDEN_SCENARIO_SURFACE,
        "synthetic_proves_infrastructure_only": True,
        "trading_edge_is_proof": TRADING_EDGE_IS_PROOF,
    }
    stamped = fingerprint(identity)
    if is_refusal(stamped):
        return stamped
    return Ok(
        GoldenScenarioReport(
            format_version=GOLDEN_SCENARIO_FORMAT_VERSION,
            fingerprint=stamped.value,
            composition_sealed=composed["sealed"] is True,
            scenarios_proven=proven,
            fixtures=fixtures,
            source_class=SOURCE_CLASS_SYNTHETIC,
            invents_ksa_or_latency=False,
            ksa_matrix_values_supplied=False,
            trading_edge_is_proof=TRADING_EDGE_IS_PROOF,
            synthetic_proves_infrastructure_only=True,
        )
    )


def _stamp_fixtures(
    fx: _Fixtures,
    evidence_by_key: Mapping[str, Mapping[str, object]],
) -> Result[tuple[GoldenFixtureProof, ...]]:
    built: list[GoldenFixtureProof] = []
    for spec in _FIXTURE_SPECS:
        evidence = evidence_by_key.get(spec.proof_key)
        if evidence is None:
            return policy(
                "proof_key",
                "every golden fixture must carry runtime evidence",
                proof_key=spec.proof_key,
                failure_id=_ID_FIXTURE,
            )
        identity = {
            "class": "golden-fixture-proof",
            "clock_ns": fx.now.value_ns,
            "components": list(spec.components),
            "contracts": list(spec.contracts),
            "decisions": list(spec.decisions),
            "evidence": dict(evidence),
            "gaps": list(spec.gaps),
            "given": spec.given,
            "proof_key": spec.proof_key,
            "scenario": spec.scenario,
            "seed": fx.seed,
            "source_class": SOURCE_CLASS_SYNTHETIC,
            "then": spec.then,
            "trading_edge_claimed": False,
            "when": spec.when,
        }
        stamped = fingerprint(identity)
        if is_refusal(stamped):
            return stamped
        built.append(
            GoldenFixtureProof(
                scenario=spec.scenario,
                proof_key=spec.proof_key,
                components=spec.components,
                contracts=spec.contracts,
                decisions=spec.decisions,
                gaps=spec.gaps,
                given=spec.given,
                when=spec.when,
                then=spec.then,
                clock_ns=fx.now.value_ns,
                seed=fx.seed,
                source_class=SOURCE_CLASS_SYNTHETIC,
                fingerprint=stamped.value,
                evidence=MappingProxyType(dict(evidence)),
                trading_edge_claimed=False,
            )
        )
    keys = tuple(item.proof_key for item in built)
    if keys != GOLDEN_PROOF_KEYS:
        return policy(
            "proof_keys",
            "golden fixtures must bind the TN-23 proof keys in declared order",
            given=list(keys),
            required=list(GOLDEN_PROOF_KEYS),
            failure_id=_ID_FIXTURE,
        )
    return Ok(tuple(built))


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
            "golden-scenario proofs require Compose to Seal a valid population",
        )
    return Ok(MappingProxyType({"checks_run": list(proof.value.checks_run), "sealed": True}))


def _exercise_scn0006(fx: _Fixtures) -> Result[Mapping[str, object]]:
    live_fp = _unwrap(_fp(fx, "live-binding-scn0006"))
    if isinstance(live_fp, TypedRefusal):
        return live_fp
    live_bms_fp = _unwrap(_fp(fx, "bms-live"))
    if isinstance(live_bms_fp, TypedRefusal):
        return live_bms_fp
    demo_bms_fp = _unwrap(_fp(fx, "bms-demo"))
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
    frozen = resolve_book_execution_target(
        book_mode=BookMode.LIVE,
        seat_state=SeatState.ACTIVE,
        active_controls=(),
        live_target=live_target.value,
        paper_target=paired.value.paper_target,
        blocked_act="entry",
    )
    if is_refusal(frozen):
        return frozen
    stream = BindingTransitionStream()
    targets = PaperTargetLog()
    epochs = PaperEpochLog()
    book_id = BookInstanceId.try_create("book-scn0006")
    if is_refusal(book_id):
        return book_id
    flip = mint_operator_paper_flip(
        book_instance_id=book_id.value,
        live_binding_epoch=live_fp,
        transition_instant=fx.now,
        operator_signature="operator:sig-28-5",
        starting_balance=fx.paper_starting_balance,
        paired=paired.value,
        transition_stream=stream,
        paper_target_log=targets,
        paper_epoch_log=epochs,
    )
    if is_refusal(flip):
        return flip
    mode = fold_book_mode(stream, book_id.value)
    if is_refusal(mode):
        return mode
    restarted = fold_book_mode(stream, book_id.value, as_of=fx.now)
    if is_refusal(restarted):
        return restarted
    after_flip = resolve_book_execution_target(
        book_mode=mode.value,
        seat_state=SeatState.ACTIVE,
        active_controls=(),
        live_target=live_target.value,
        paper_target=paired.value.paper_target,
        blocked_act="entry",
    )
    if is_refusal(after_flip):
        return after_flip
    frozen_target = frozen.value.execution_target
    new_target = after_flip.value.execution_target
    if frozen_target is None or new_target is None:
        return policy("execution_target", "SCN-0006 routing must resolve an execution target")
    if frozen_target.role is not AccountRole.LIVE or new_target.role is not AccountRole.DEMO:
        return policy(
            "frozen_target",
            "per-intent execution_target is frozen at mint; a later PAPER flip "
            "must not rewrite the earlier target",
            frozen=frozen_target.role.value,
            later=new_target.role.value,
        )
    current_epoch = epochs.current_epoch(live_fp)
    if is_refusal(current_epoch):
        return current_epoch
    if current_epoch.value.starting_balance != fx.paper_starting_balance:
        return policy("paper_money", "paper starting balance is frozen at flip")
    treasury = refuse_paper_pnl_to_treasury(fx.paper_starting_balance)
    if is_ok(treasury):
        return policy("paper_money", "paper P&L must never become Treasury cash")
    unsigned = restore_kill_line_stand_down(
        binding_scope_ref="binding-scn0006",
        venue_id=fx.venue_id,
        account_id="acct-live",
        issued_at=fx.now,
        operator_signature=None,
    )
    if is_ok(unsigned):
        return policy("return", "return to live touching real money requires an operator signature")
    signed = restore_kill_line_stand_down(
        binding_scope_ref="binding-scn0006",
        venue_id=fx.venue_id,
        account_id="acct-live",
        issued_at=fx.now,
        operator_signature="operator:sig-resume-28-5",
    )
    if is_refusal(signed):
        return signed
    journey = inspect_bot_node_journey(bot_id="bot-scn0006", promoted=True, activated=True)
    if is_refusal(journey):
        return journey
    if journey.value.paper_performance_gate is True:
        return policy("return", "paper performance never authorizes a return to live")
    unknown = _unwrap(_separate_stream_unknown(fx))
    if isinstance(unknown, TypedRefusal):
        return unknown
    live_scope = KsaEnforcementScope.stream(fx.venue_id, "acct-live")
    if is_refusal(live_scope):
        return live_scope
    live_blocks_demo = stream_blocked_by_escalation(
        live_scope.value,
        target_venue_id=fx.venue_id,
        target_account_id="acct-demo",
        target_is_paired_demo=True,
    )
    flatten = _unwrap(_standing_flatten(fx, "acct-live"))
    if isinstance(flatten, TypedRefusal):
        return flatten
    extent = ProtectionIntentExtent.try_create(8)
    if is_refusal(extent):
        return extent
    persisted = persist_protective_intent(
        flatten,
        extent=extent.value,
        journal=_JournalSink(),
    )
    if is_refusal(persisted):
        return persisted
    redecided = redecide_protective_intent(
        flatten,
        verdict=ReconciliationVerdict.RECONCILED,
        scope_flat=False,
    )
    if is_refusal(redecided):
        return redecided
    if restarted.value is not BookMode.PAPER:
        return policy(
            "restart",
            "a restart must re-decide standing intents and must not re-arm a Book left in PAPER",
        )
    return Ok(
        MappingProxyType(
            {
                "append_only_epoch": True,
                "book_mode": mode.value.value,
                "book_twin_minted": flip.value.book_twin_minted,
                "bot_twin_minted": flip.value.bot_twin_minted,
                "clears_only_by": OPERATOR_KILL_LINE_RESUME,
                "frozen_per_intent_target": True,
                "human_signed_return": True,
                "immutable_paper_money": True,
                "live_connectivity_does_not_block_demo": live_blocks_demo is False,
                "paper_performance_authorizes_return": False,
                "restart_does_not_rearm_paper": True,
                "separate_stream_unknown": unknown["paper_stream_open"] is True,
                "trading_edge_claimed": False,
            }
        )
    )


def _exercise_scn0008(fx: _Fixtures) -> Result[Mapping[str, object]]:
    sole = require_sole_free_provider(SOLE_V1_PROVIDER)
    if is_refusal(sole):
        return sole
    paid = refuse_paid_news_provider(provider="fmp")
    if is_ok(paid):
        return policy("news_source", "a paid news provider must be refused")
    second = refuse_second_news_source(provider="second-free")
    if is_ok(second):
        return policy("news_source", "a second news-calendar source must be refused")
    eurusd = _instrument(fx.venue_id, "EURUSD")
    xauusd = _instrument(fx.venue_id, "XAUUSD")
    if is_refusal(eurusd):
        return eurusd
    if is_refusal(xauusd):
        return xauusd
    exposure = CurrencyExposureRecord.try_create(
        eurusd.value, ("EUR", "USD"), fx.now, "exp-scn0008"
    )
    if is_refusal(exposure):
        return exposure
    scope = resolve_instrument_scope(
        affected_currencies=("USD",),
        candidate_instruments=(eurusd.value, xauusd.value),
        exposure_records=(exposure.value,),
    )
    if is_refusal(scope):
        return scope
    if xauusd.value not in scope.value.treated_as_affected_missing_exposure:
        return policy(
            "exposure",
            "a missing currency-exposure record must treat the instrument as affected",
        )
    symbol_parse = refuse_symbol_currency_parse_at_door("EURUSD")
    if is_ok(symbol_parse):
        return policy("exposure", "currency must never be parsed from the instrument symbol")
    start = _unwrap(Instant.try_create(fx.now.value_ns - 2_000_000_000))
    if isinstance(start, TypedRefusal):
        return start
    end = _unwrap(Instant.try_create(fx.now.value_ns + 2_000_000_000))
    if isinstance(end, TypedRefusal):
        return end
    bounds = WindowBounds.try_create(start, end)
    if is_refusal(bounds):
        return bounds
    known = _unwrap(Instant.try_create(fx.now.value_ns - 3_000_000_000))
    if isinstance(known, TypedRefusal):
        return known
    feed = FeedQuadruple.try_create("calendar-feed", "nfp-28-5", "r1", known)
    if is_refusal(feed):
        return feed
    news_cal = CalendarIdentity.try_create("news-ff-weekly", "v1", "2026a")
    hours_cal = CalendarIdentity.try_create("market-hours-forex", "v3", "2024a")
    if is_refusal(news_cal):
        return news_cal
    if is_refusal(hours_cal):
        return hours_cal
    news = mint_control_window(
        bounds.value,
        WindowKind.NEWS,
        scope.value,
        "high-impact-news",
        news_cal.value,
        "win-nfp-28-5",
        feed_quadruple=feed.value,
    )
    if is_refusal(news):
        return news
    dead = mint_control_window(
        bounds.value,
        WindowKind.DAILY_DEAD_ZONE,
        scope.value,
        WindowKind.DAILY_DEAD_ZONE.value,
        hours_cal.value,
        "win-dead-28-5",
    )
    if is_refusal(dead):
        return dead
    live_entry = enforce_entry_at_book_door(
        instrument=eurusd.value,
        book_mode=BookMode.LIVE,
        decision_at=fx.now,
        windows=[news.value],
        would_have_been_action={"class": "would-have-been-entry", "symbol": "EURUSD"},
    )
    paper_entry = enforce_entry_at_book_door(
        instrument=eurusd.value,
        book_mode=BookMode.PAPER,
        decision_at=fx.now,
        windows=[news.value],
        would_have_been_action={"class": "would-have-been-entry", "symbol": "EURUSD"},
    )
    dead_entry = enforce_entry_at_book_door(
        instrument=eurusd.value,
        book_mode=BookMode.LIVE,
        decision_at=fx.now,
        windows=[dead.value],
        would_have_been_action={"class": "would-have-been-entry", "kind": "daily_dead_zone"},
    )
    missing = enforce_entry_at_book_door(
        instrument=xauusd.value,
        book_mode=BookMode.LIVE,
        decision_at=fx.now,
        windows=[news.value],
        would_have_been_action={"class": "would-have-been-entry", "symbol": "XAUUSD"},
    )
    if is_refusal(live_entry):
        return live_entry
    if is_refusal(paper_entry):
        return paper_entry
    if is_refusal(dead_entry):
        return dead_entry
    if is_refusal(missing):
        return missing
    if not (
        live_entry.value.blocked
        and paper_entry.value.blocked
        and dead_entry.value.blocked
        and missing.value.blocked
    ):
        return policy("window", "news and dead-zone windows must block live and paper entries")
    if live_entry.value.disposition is not WindowActDisposition.VETO_JOURNALED:
        return policy("window", "a blocked news entry must journal a veto")
    exit_ok = allow_protective_act_under_windows(proposed_act=ProposedWindowAct.EXIT)
    if is_refusal(exit_ok):
        return exit_ok
    live_skip = refuse_live_skip_at_door()
    if is_ok(live_skip):
        return policy("window", "there is no live skip over an in-force window")
    stale_at = Instant.try_create(known.value_ns + fx.news_calendar_max_staleness.value_ns + 1)
    if is_refusal(stale_at):
        return stale_at
    stale = stale_news_calendar_blocks_entries(
        last_refresh_at=known,
        decision_at=stale_at.value,
        max_staleness=fx.news_calendar_max_staleness,
    )
    if is_ok(stale):
        return policy("staleness", "a stale news calendar must fail closed")
    fail_closed = enforce_entry_at_book_door(
        instrument=eurusd.value,
        book_mode=BookMode.LIVE,
        decision_at=fx.now,
        windows=[news.value],
        would_have_been_action={"class": "entry"},
        news_calendar_fresh=False,
    )
    if is_refusal(fail_closed):
        return fail_closed
    if fail_closed.value.disposition is not WindowActDisposition.FAIL_CLOSED:
        return policy("staleness", "unknown coverage must fail closed at the Book door")
    narrow_start = _unwrap(Instant.try_create(fx.now.value_ns - 1_000_000_000))
    if isinstance(narrow_start, TypedRefusal):
        return narrow_start
    narrow_end = _unwrap(Instant.try_create(fx.now.value_ns + 1_000_000_000))
    if isinstance(narrow_end, TypedRefusal):
        return narrow_end
    narrow_bounds = WindowBounds.try_create(narrow_start, narrow_end)
    if is_refusal(narrow_bounds):
        return narrow_bounds
    feed2 = FeedQuadruple.try_create("calendar-feed", "nfp-28-5", "r2", fx.now)
    if is_refusal(feed2):
        return feed2
    narrow = mint_control_window(
        narrow_bounds.value,
        WindowKind.NEWS,
        scope.value,
        "high-impact-news",
        news_cal.value,
        "win-nfp-28-5",
        feed_quadruple=feed2.value,
    )
    if is_refusal(narrow):
        return narrow
    log = ControlWindowRevisionLog(window_id="win-nfp-28-5")
    first = apply_news_revision(log, news.value, decision_at=fx.now)
    if is_refusal(first):
        return first
    held = apply_news_revision(
        first.value[0],
        narrow.value,
        decision_at=fx.now,
        prior_in_force=news.value,
    )
    if is_refusal(held):
        return held
    if held.value[2] is not NewsRevisionDisposition.NARROWING_HELD:
        return policy("revision", "narrowing an in-force window must be held")
    if held.value[1].bounds.end.value_ns != end.value_ns:
        return policy(
            "revision",
            "a narrowing revision must not open entries before the declared end",
        )
    return Ok(
        MappingProxyType(
            {
                "declared_exposure": True,
                "entry_only_block": True,
                "exit_preservation": True,
                "fail_closed_missing_scope": True,
                "fail_closed_staleness": True,
                "live_and_paper_blocked": True,
                "narrowing_held": True,
                "sole_free_source": sole.value,
                "sole_weekly_file": FOREX_FACTORY_WEEKLY_JSON,
                "trading_edge_claimed": False,
                "widen_not_shrink": held.value[2].value,
            }
        )
    )


def _exercise_scn0010(fx: _Fixtures) -> Result[Mapping[str, object]]:
    stream = CommandStreamKey.try_create(fx.venue_id, "acct-1")
    if is_refusal(stream):
        return stream
    key = stream_dispatcher_key(fx.venue_id, "acct-1")
    if is_refusal(key):
        return key
    table = _rank_table()
    if is_refusal(table):
        return table
    unique = require_total_unique_rank_table(table.value)
    if is_refusal(unique):
        return unique
    compose = _unwrap(_compose_pair(fx, stream.value, table.value))
    if isinstance(compose, TypedRefusal):
        return compose
    collapse = _unwrap(_collapse_flats(fx, stream.value, table.value))
    if isinstance(collapse, TypedRefusal):
        return collapse
    conflict = _unwrap(_conflict_pair(fx, stream.value, table.value))
    if isinstance(conflict, TypedRefusal):
        return conflict
    unresolvable = resolve_subject_scope(
        "not-a-scope",
        scope_ref="binding-1",
        stream=stream.value,
        position_model=PositionModel.NETTING,
    )
    if is_ok(unresolvable):
        return policy("scope", "an unresolvable subject scope must refuse")
    netting = resolve_subject_scope(
        SubjectScope.INSTRUMENT,
        scope_ref="EURUSD",
        stream=stream.value,
        position_model=PositionModel.NETTING,
        netting_indistinguishable_from_wider=True,
    )
    if is_ok(netting):
        return policy("scope", "netting-indistinguishable narrower scope must refuse, never widen")
    preserved = check_exit_preservation(blocked_act="entry")
    if is_refusal(preserved):
        return preserved
    blocked_exit = check_exit_preservation(blocked_act=RiskReducingAct.CLOSE_POSITION)
    if is_ok(blocked_exit):
        return policy("exit_preservation", "a control may never block a risk-reducing close")
    return Ok(
        MappingProxyType(
            {
                "collapse_one_flatten": collapse["emit_flatten"] == 1,
                "compose_both_execute": compose["both_execute"] is True,
                "conflict_higher_rank_wins": conflict["higher_wins"] is True,
                "exit_preservation": True,
                "one_arbiter_per_stream": key.value.account_id == "acct-1",
                "scope_refusal": True,
                "suppressed_count": collapse["suppressed"],
                "total_unique_rank": True,
                "trading_edge_claimed": False,
            }
        )
    )


def _exercise_scn0011(fx: _Fixtures) -> Result[Mapping[str, object]]:
    epoch = _unwrap(_fp(fx, "epoch-scn0011"))
    if isinstance(epoch, TypedRefusal):
        return epoch
    q = fx.qualifying_loss_threshold
    if q.unit_kind is not UnitKind.R_MULTIPLE:
        return invalid(
            "qualifying_loss_threshold",
            "q is a Book-declared r-multiple, never a spine constant",
        )
    records: list[ExitRecord] = []
    sequence: tuple[tuple[str, int, CloseOutcome, CloseReason, ClosingAuthority, int], ...] = (
        (
            "be-1",
            -50,
            CloseOutcome.BREAKEVEN,
            CloseReason.PROTECTIVE_STOP_FILL,
            ClosingAuthority.VENUE,
            50,
        ),
        (
            "scratch-1",
            -1_500,
            CloseOutcome.LOSS,
            CloseReason.BOT_INTENT,
            ClosingAuthority.BOOK_POLICY,
            0,
        ),
        (
            "ql-1",
            -10_000,
            CloseOutcome.LOSS,
            CloseReason.PROTECTIVE_STOP_FILL,
            ClosingAuthority.VENUE,
            200,
        ),
        (
            "ql-2",
            -12_000,
            CloseOutcome.LOSS,
            CloseReason.HOLD_TIME_FORCE_FLAT,
            ClosingAuthority.BOOK_POLICY,
            0,
        ),
    )
    for seed, pnl, outcome, reason, authority, commission in sequence:
        minted = _mint_exit(
            fx,
            seed=seed,
            epoch=epoch,
            realized_pnl=pnl,
            outcome=outcome,
            close_reason=reason,
            authority=authority,
            commission=commission,
        )
        if is_refusal(minted):
            return minted
        records.append(minted.value)
    if len(records) != 4:
        return policy("ct29", "each virtual-position close must mint exactly one CT-29 record")
    report = evaluate_qualifying_loss_bench(
        tuple(records),
        binding_epoch=epoch,
        q=q,
        threshold=fx.bench_consecutive_loss_threshold,
    )
    if is_refusal(report):
        return report
    if report.value.qualifying_loss_count != 2:
        return policy(
            "bench",
            "the fold must count two qualifying losses and exclude breakeven and scratch",
            count=report.value.qualifying_loss_count,
        )
    if report.value.breakeven_clustering_count != 1:
        return policy("bench", "a breakeven never counts under any q and is clustered apart")
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
    if effect.value.seat_state is not SeatState.BENCHED:
        return policy("bench", "a threshold crossing must bench the seat")
    if effect.value.book_mode is not BookMode.LIVE:
        return policy("bench", "a benched seat must leave the Book LIVE")
    if effect.value.routing.outcome is not RoutingOutcome.ROUTED_PAPER:
        return policy("bench", "a benched seat routes to the paired demo target")
    stale = refuse_stale_exit_before_intent(
        closing_exit_record=records[-1],
        persisted=False,
        journaled=True,
    )
    if is_ok(stale):
        return policy("stale_evidence", "an unpersisted exit must refuse the next same-seat intent")
    other_epoch = _unwrap(_fp(fx, "epoch-other"))
    if isinstance(other_epoch, TypedRefusal):
        return other_epoch
    outsider = _mint_exit(
        fx,
        seed="other-epoch",
        epoch=other_epoch,
        realized_pnl=-10_000,
        outcome=CloseOutcome.LOSS,
        close_reason=CloseReason.PROTECTIVE_STOP_FILL,
        authority=ClosingAuthority.VENUE,
        commission=0,
    )
    if is_refusal(outsider):
        return outsider
    bounded = evaluate_qualifying_loss_bench(
        (*records, outsider.value),
        binding_epoch=epoch,
        q=q,
        threshold=fx.bench_consecutive_loss_threshold,
    )
    if is_refusal(bounded):
        return bounded
    if len(bounded.value.fold.considered) != 4:
        return policy("binding_epoch", "the bench fold is bounded by the binding epoch")
    return Ok(
        MappingProxyType(
            {
                "binding_epoch_bounded": True,
                "book_mode": effect.value.book_mode.value,
                "breakeven_excluded": True,
                "one_ct29_per_close": True,
                "qualifying_loss_count": report.value.qualifying_loss_count,
                "routed_paper": True,
                "seat_state": effect.value.seat_state.value,
                "stale_evidence_refused": True,
                "threshold_crossed": report.value.threshold_crossed,
                "trading_edge_claimed": False,
            }
        )
    )


def _separate_stream_unknown(fx: _Fixtures) -> Result[Mapping[str, object]]:
    live_acct = _account(fx.venue_id, "acct-live", AccountRole.LIVE)
    demo_acct = _account(fx.venue_id, "acct-demo", AccountRole.DEMO)
    if is_refusal(live_acct):
        return live_acct
    if is_refusal(demo_acct):
        return demo_acct
    live_writer = venue_writer_id(_MACHINE, _ADAPTER, fx.venue_id, live_acct.value, _BOOT)
    demo_writer = venue_writer_id(_MACHINE, _ADAPTER, fx.venue_id, demo_acct.value, _BOOT)
    if is_refusal(live_writer):
        return live_writer
    if is_refusal(demo_writer):
        return demo_writer
    live_cm = ConnectionManager.try_create(
        live_writer.value, _SecretStore(), _ObsSink(), _JournalSink(), _RecordSink()
    )
    demo_cm = ConnectionManager.try_create(
        demo_writer.value, _SecretStore(), _ObsSink(), _JournalSink(), _RecordSink()
    )
    if is_refusal(live_cm):
        return live_cm
    if is_refusal(demo_cm):
        return demo_cm
    live_extent = UnknownIntentExtent.try_create(8)
    demo_extent = UnknownIntentExtent.try_create(8)
    if is_refusal(live_extent):
        return live_extent
    if is_refusal(demo_extent):
        return demo_extent
    live_b = CommandStreamUnknownBoundary.try_create(
        venue_id=fx.venue_id,
        account=live_acct.value,
        connection_manager=live_cm.value,
        extent=live_extent.value,
    )
    demo_b = CommandStreamUnknownBoundary.try_create(
        venue_id=fx.venue_id,
        account=demo_acct.value,
        connection_manager=demo_cm.value,
        extent=demo_extent.value,
    )
    if is_refusal(live_b):
        return live_b
    if is_refusal(demo_b):
        return demo_b
    command = _place_command(fx.venue_id, live_acct.value, 1)
    if is_refusal(command):
        return command
    unknown = _unknown_submission(command.value, fx.now)
    if is_refusal(unknown):
        return unknown
    blocked = live_b.value.record_unknown(unknown.value)
    if is_refusal(blocked):
        return blocked
    paper_cmd = _place_command(fx.venue_id, demo_acct.value, 1)
    if is_refusal(paper_cmd):
        return paper_cmd
    admitted = demo_b.value.admit(paper_cmd.value, receive_instant=fx.now)
    if is_refusal(admitted):
        return admitted
    live_next = _place_command(fx.venue_id, live_acct.value, 2)
    if is_refusal(live_next):
        return live_next
    live_refused = live_b.value.admit(live_next.value, receive_instant=fx.now)
    if is_refusal(live_refused):
        return live_refused
    paper_result = admitted.value
    live_result = live_refused.value
    paper_ok = getattr(paper_result, "disposition", None) is AdmissionDisposition.ADMITTED
    live_blocked = getattr(live_result, "disposition", None) is AdmissionDisposition.REFUSED
    live_cause = getattr(live_result, "block_cause", None)
    if not paper_ok or not live_blocked or live_cause is not StreamBlockCause.OUTSTANDING_UNKNOWN:
        return policy(
            "unknown",
            "an UNKNOWN on the live stream must not gate the paired demo stream",
        )
    return Ok(
        MappingProxyType(
            {
                "live_stream_open": live_b.value.stream_open,
                "paper_stream_open": demo_b.value.stream_open,
            }
        )
    )


def _standing_flatten(fx: _Fixtures, account: str) -> Result[ControlActionRecord]:
    stream = _unwrap(CommandStreamKey.try_create(fx.venue_id, account))
    if isinstance(stream, TypedRefusal):
        return stream
    return mint_control_action(
        ControlActionKind.FLATTEN,
        "book-scn0006",
        AuthorityKind.BOOK_POLICY,
        SubjectScope.BINDING,
        "binding-scn0006",
        1,
        "kill-line",
        stream,
        fx.now,
        trigger_class="kill_line_breach",
    )


def _compose_pair(
    fx: _Fixtures,
    stream: CommandStreamKey,
    table: ControlRankTable,
) -> Result[Mapping[str, object]]:
    suspend = mint_control_action(
        ControlActionKind.SUSPEND_NEW,
        "ksa-1",
        AuthorityKind.PROTECTION_AUTHORITY,
        SubjectScope.BINDING,
        "binding-1",
        0,
        "kill-switch",
        stream,
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
        stream,
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
        stream=stream,
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
        table,
        stream=stream,
        arbitration_seed=f"{fx.seed}-compose",
    )
    if is_refusal(plan):
        return plan
    kinds = {item.record.action_kind for item in plan.value.emit}
    expected = {ControlActionKind.SUSPEND_NEW, ControlActionKind.FLATTEN}
    if kinds != expected:
        return policy(
            "compose",
            "suspend_new and flatten on one tick must both execute",
            emit=sorted(kind.value for kind in kinds),
        )
    return Ok(MappingProxyType({"both_execute": True, "suppressed": len(plan.value.suppressed)}))


def _collapse_flats(
    fx: _Fixtures,
    stream: CommandStreamKey,
    table: ControlRankTable,
) -> Result[Mapping[str, object]]:
    kill_line = mint_control_action(
        ControlActionKind.FLATTEN,
        "book-1",
        AuthorityKind.BOOK_POLICY,
        SubjectScope.BINDING,
        "binding-1",
        1,
        "kill_line",
        stream,
        fx.now,
        trigger_class="kill_line_breach",
    )
    window = mint_control_action(
        ControlActionKind.FLATTEN,
        "book-1",
        AuthorityKind.BOOK_POLICY,
        SubjectScope.BINDING,
        "binding-1",
        1,
        "window",
        stream,
        fx.now,
        trigger_class="window_forced_flat",
    )
    later = _unwrap(Instant.try_create(fx.now.value_ns + 1))
    if isinstance(later, TypedRefusal):
        return later
    bot_close = mint_control_action(
        ControlActionKind.FLATTEN,
        "bot-exit",
        AuthorityKind.BOOK_POLICY,
        SubjectScope.BINDING,
        "binding-1",
        1,
        "bot-close-full",
        stream,
        later,
        trigger_class="hold_time_force_flat",
    )
    if is_refusal(kill_line):
        return kill_line
    if is_refusal(window):
        return window
    if is_refusal(bot_close):
        return bot_close
    enforcement = EnforcementScope(
        subject_scope=SubjectScope.BINDING,
        scope_ref="binding-1",
        stream=stream,
    )
    candidates: list[DispatchCandidate] = []
    for record, origin, ordinal in (
        (kill_line.value, CandidateOrigin.CT30, 0),
        (window.value, CandidateOrigin.CT30, 1),
        (bot_close.value, CandidateOrigin.RISK_NON_INCREASING, 2),
    ):
        cand = DispatchCandidate.try_create(
            record, enforcement, origin=origin, arrival_ordinal=ordinal
        )
        if is_refusal(cand):
            return cand
        candidates.append(cand.value)
    plan = dispatch_ranked_controls(
        candidates,
        table,
        stream=stream,
        arbitration_seed=f"{fx.seed}-collapse",
    )
    if is_refusal(plan):
        return plan
    emit_flatten = sum(
        1 for item in plan.value.emit if item.record.action_kind is ControlActionKind.FLATTEN
    )
    if emit_flatten != 1 or len(plan.value.suppressed) != 2:
        return policy(
            "collapse",
            "identical mechanical close commands collapse to one emission",
            emit_flatten=emit_flatten,
            suppressed=len(plan.value.suppressed),
        )
    return Ok(
        MappingProxyType({"emit_flatten": emit_flatten, "suppressed": len(plan.value.suppressed)})
    )


def _conflict_pair(
    fx: _Fixtures,
    stream: CommandStreamKey,
    table: ControlRankTable,
) -> Result[Mapping[str, object]]:
    suspend = mint_control_action(
        ControlActionKind.SUSPEND_NEW,
        "ksa-1",
        AuthorityKind.PROTECTION_AUTHORITY,
        SubjectScope.BINDING,
        "binding-1",
        0,
        "kill-switch",
        stream,
        fx.now,
    )
    resume = mint_control_action(
        ControlActionKind.RESUME,
        "op-1",
        AuthorityKind.OPERATOR,
        SubjectScope.BINDING,
        "binding-1",
        3,
        "operator-resume",
        stream,
        fx.now,
    )
    if is_refusal(suspend):
        return suspend
    if is_refusal(resume):
        return resume
    enforcement = EnforcementScope(
        subject_scope=SubjectScope.BINDING,
        scope_ref="binding-1",
        stream=stream,
    )
    cand_a = DispatchCandidate.try_create(suspend.value, enforcement, origin="ct30")
    cand_b = DispatchCandidate.try_create(resume.value, enforcement, origin="ct30")
    if is_refusal(cand_a):
        return cand_a
    if is_refusal(cand_b):
        return cand_b
    plan = dispatch_ranked_controls(
        [cand_a.value, cand_b.value],
        table,
        stream=stream,
        arbitration_seed=f"{fx.seed}-conflict",
    )
    if is_refusal(plan):
        return plan
    emit = {item.record.action_kind for item in plan.value.emit}
    suppressed_kinds: set[ControlActionKind] = set()
    for item in plan.value.suppressed:
        if isinstance(item, SuppressedControlAction):
            suppressed_kinds.add(item.suppressed.record.action_kind)
    if (
        ControlActionKind.SUSPEND_NEW not in emit
        or ControlActionKind.RESUME not in suppressed_kinds
    ):
        return policy(
            "conflict",
            "mutually exclusive commands let the higher rank win outright",
            emit=sorted(kind.value for kind in emit),
            suppressed=sorted(kind.value for kind in suppressed_kinds),
        )
    return Ok(MappingProxyType({"higher_wins": True}))


def _mint_exit(
    fx: _Fixtures,
    *,
    seed: str,
    epoch: Fingerprint,
    realized_pnl: int,
    outcome: CloseOutcome,
    close_reason: CloseReason,
    authority: ClosingAuthority,
    commission: int,
) -> Result[ExitRecord]:
    instrument = _instrument(fx.venue_id)
    if is_refusal(instrument):
        return instrument
    distance = PriceDelta.try_create(50, instrument.value, 5)
    if is_refusal(distance):
        return distance
    amount = _money(10_000)
    pnl = _money(realized_pnl)
    if is_refusal(amount):
        return amount
    if is_refusal(pnl):
        return pnl
    fill = _unwrap(_fp(fx, f"fill-{seed}"))
    pos = _unwrap(_fp(fx, seed))
    if isinstance(fill, TypedRefusal):
        return fill
    if isinstance(pos, TypedRefusal):
        return pos
    label = ExitResultLabel.try_create(AccountRole.LIVE, World.LIVE)
    if is_refusal(label):
        return label
    costs: tuple[CostComponent, ...] = ()
    if commission:
        fee = _money(commission)
        if is_refusal(fee):
            return fee
        cost = CostComponent.try_create("commission", fee.value, "broker")
        if is_refusal(cost):
            return cost
        costs = (cost.value,)
    arb_fp: Fingerprint | None = None
    vobs_fp: Fingerprint | None = None
    if authority is ClosingAuthority.VENUE:
        vobs = _unwrap(_fp(fx, f"venue-obs-{seed}"))
        if isinstance(vobs, TypedRefusal):
            return vobs
        vobs_fp = vobs
    else:
        arb = _unwrap(_fp(fx, f"arb-{seed}"))
        if isinstance(arb, TypedRefusal):
            return arb
        arb_fp = arb
    return mint_exit_record(
        virtual_position_ref=pos,
        opening_bot_id="bot-scn0011",
        original_risk_distance=distance.value,
        original_risk_amount=amount.value,
        fill_references=(fill,),
        realized_pnl=pnl.value,
        cost_components=costs,
        close_reason=close_reason,
        mechanism=close_reason,
        outcome=outcome,
        closing_authority=authority,
        close_reason_mapping_version=1,
        result_label=label.value,
        loss_predicate_format_version=1,
        binding_epoch=epoch,
        recorded_at=fx.now,
        arbitration_record_ref=arb_fp,
        venue_observation_ref=vobs_fp,
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
    config = fingerprint({"class": "golden-28-5", "seed": "config"})
    cap = fingerprint({"class": "golden-28-5", "seed": "cap"})
    as_of = fingerprint({"class": "golden-28-5", "seed": "as-of"})
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
    cmd_fp = command.fingerprint()
    if is_refusal(cmd_fp):
        return cmd_fp
    elapsed = Duration.try_create(750_000_000)
    deadline = Instant.try_create(now.value_ns + 5_000_000_000)
    if is_refusal(elapsed):
        return elapsed
    if is_refusal(deadline):
        return deadline
    obs = CommandObservation(
        command_fp1=cmd_fp.value,
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
            command_fp1=cmd_fp.value,
            kind=command.kind,
            outcome=SubmissionOutcome.UNKNOWN,
            observation=obs,
            journal_event=JournalEvent.for_outcome(
                cmd_fp.value, command.kind, SubmissionOutcome.UNKNOWN
            ),
        )
    )


def _account(venue: VenueId, account_id: str, role: AccountRole) -> Result[Account]:
    return Account.try_create(account_id, venue, role)


def _instrument(venue: VenueId, symbol: str = "EURUSD") -> Result[Instrument]:
    return Instrument.try_create(venue, symbol)


def _money(value: int) -> Result[Money]:
    return Money.try_create(value, "USD", 2)


def _fp(fx: _Fixtures, seed: str) -> Result[Fingerprint]:
    return fingerprint({"class": GOLDEN_SCENARIO_CLASS, "run": fx.seed, "seed": seed})


def _unwrap(result: Result[T]) -> T | TypedRefusal:
    if isinstance(result, TypedRefusal):
        return result
    return result.value
