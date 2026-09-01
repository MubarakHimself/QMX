"""Story 26.15 / E12-F05 — ungoverned Python-bot tunnel cannot bypass node gates."""

from __future__ import annotations

import ast
from typing import TypeVar, cast

from qmb.runloop import CancelToken, ScriptedLimitProbe
from qmf.core import (
    Account,
    AccountRole,
    DataDrivenClock,
    Duration,
    ExactRational,
    Instant,
    Instrument,
    Price,
    Quantity,
    RefusalCategory,
    Result,
    UnitKind,
    ValueFactor,
    VenueId,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.core.chrono import CalendarIdentity
from qmf.risk.door import (
    CitedEvidence,
    Direction,
    EntryIntent,
    EvidenceSlot,
    ExitLogicRef,
    ReasonCode,
)
from qmf.risk.exit_policy import ExitPolicy
from qmf.risk.footprint_requirements import FootprintRequirements
from qmf.risk.paper import ExecutionTarget
from qml.conformance import (
    admit_ungoverned_tunnel,
    gate_registration,
    lint_declaration,
    run_layer2_suite,
)
from qml.declaration import BotDefinition, mint_bot_definition, mint_confluence
from qml.families import mint_strategy_family
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity
from qml.protocol import (
    PROTOCOL_FORMAT_VERSION,
    FunctionFactory,
    construct_bot,
    mint_state_scope,
)
from qmn.order.protection import ENTRY_RELATIVE_FORM
from qmn.promotion import AdmissionLayerFreshState
from qmn.seats import (
    ADMISSION_LAYER_NAMES,
    FORBIDDEN_SEAT_SURFACE_KEYS,
    INTENT_PATH_HOPS,
    SEAT_ADMISSION_PROOFS,
    SEAT_ADMISSION_SURFACE,
    UNGOVERNED_EVIDENCE_KINDS,
    UNGOVERNED_TUNNEL_NAMES,
    AdmittedNodeSeat,
    BookPathContext,
    SeatContainment,
    SeatTransitionStream,
    cite_governed_seat_occurrence,
    construct_governed_seat,
    dispatch_hosted_intents,
    dispatch_seat_intents,
    inject_seat_callback,
    propose_node_seat,
    refuse_bot_constructed_ct19,
    refuse_composition_root_ungoverned_import,
    refuse_ungoverned_tunnel_seat,
    scan_production_src_for_ungoverned_tunnel,
    ungoverned_tunnel_names_in_tree,
)
from qmn.venue import Command, CommandKind, OrderParameters, OrderType, TimeInForce

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_SOURCE: dict[str, str] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}
_VENUE_CAPS: frozenset[str] = frozenset({"trading", "time-interval"})
_MISSING = object()


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _duration(ns: int = 1_000_000_000) -> Duration:
    return _ok(Duration.try_create(ns))


def _pinned(tag: str) -> ProducerBinding:
    return _ok(ProducerBinding.try_create(_ok(fingerprint({"class": "test-producer", "tag": tag}))))


def _containment() -> SeatContainment:
    return _ok(
        SeatContainment.try_create(
            callback_deadline=_duration(),
            memory_ceiling_bytes=10_000_000,
        )
    )


def _world() -> dict[str, object]:
    zone = _pinned("zone")
    sma = _pinned("sma")
    family = _ok(mint_strategy_family("trend-follow"))
    confluence = _ok(mint_confluence([{"role": "level", "producer_binding": zone}]))
    calendar = _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))
    footprint = _ok(
        mint_footprint(
            [
                {
                    "instrument_role": "primary",
                    "bar_specs": [{"kind": "time-interval", "seconds": 60}],
                    "stream_role": "trading",
                }
            ],
            [calendar],
            [zone, sma],
        )
    )
    logic = _ok(mint_logic_identity("research-bot", "1.0.0", _SOURCE))
    declaration = _ok(
        mint_bot_definition(
            strategy_family_id=family.family_id.value,
            confluence_set=[confluence],
            parameter_space=[
                {
                    "name": "lookback",
                    "type": "exact integer",
                    "bounds": {"min": 1, "max": 200},
                    "step": 1,
                    "default": 20,
                    "unit_kind": UnitKind.COUNT,
                    "ui": "ui-editable",
                }
            ],
            footprint=footprint,
            permitted_exit_intents=(),
            logic_reference=logic,
        )
    )
    return {
        "confluence": confluence,
        "declaration": declaration,
        "family": family,
        "logic": logic,
        "producers": [zone, sma],
        "source": _SOURCE,
    }


def _candidate(world: dict[str, object], *, factory: FunctionFactory | None = None):
    declaration = cast(BotDefinition, world["declaration"])
    layer1 = lint_declaration(
        declaration,
        family_catalog=[world["family"]],
        confluence_catalog=[world["confluence"]],
        producer_catalog=world["producers"],
        logic_catalog=[world["logic"]],
    )
    scope = _ok(
        mint_state_scope(
            os="windows-11",
            logic_identity=declaration.logic_reference,
            protocol_format_version=PROTOCOL_FORMAT_VERSION,
            arithmetic_reference_build="none",
        )
    )
    layer2 = run_layer2_suite(
        declaration=declaration,
        factory=factory if factory is not None else FunctionFactory(logic=lambda evidence: ()),
        source_tree=cast(dict[str, str], world["source"]),
        state_scope=scope,
        state_bound=256,
    )
    return gate_registration(layer1=layer1, layer2=layer2)


def _layers(*, layer1: bool = True, layer2: bool = True, layer3: bool = True):
    return _ok(
        AdmissionLayerFreshState.try_create(
            layer1_linters_passed=layer1,
            layer2_shakedown_passed=layer2,
            layer3_operator_signature_present=layer3,
        )
    )


def _exit_policy(family_id: str = "trend-follow") -> ExitPolicy:
    ref = _ok(ExitLogicRef.try_create("book.default.evidence_stop", {"style": "structure"}))
    return _ok(ExitPolicy.try_create({family_id: ref}, permitted_exit_intent_kinds=()))


def _requirements() -> FootprintRequirements:
    return _ok(FootprintRequirements.try_create(()))


def _propose(
    *,
    factory: object | None = None,
    world: dict[str, object] | None = None,
    candidate: object = _MISSING,
    admission_layers: object | None = None,
    assignment: object = None,
    binding_ref: object = "binding-live-1",
    bms_instance_id: object = "bms-1",
    callback: object = None,
    hosted: object = None,
    tunnel: object = None,
    clock: object = None,
    book: object = None,
    venue: object = None,
    signal_snapshot: object = None,
    exit_policy: object | None = None,
    venue_capabilities: object = _VENUE_CAPS,
) -> Result[AdmittedNodeSeat]:
    bundle = world if world is not None else _world()
    layer2_factory = factory if isinstance(factory, FunctionFactory) else None
    ticket = _ok(_candidate(bundle, factory=layer2_factory)) if candidate is _MISSING else candidate
    logic: object = factory if factory is not None else FunctionFactory(logic=lambda evidence: ())
    return propose_node_seat(
        logic,
        seat_id="seat-alpha",
        binding_ref=binding_ref,
        bms_instance_id=bms_instance_id,
        declaration=bundle["declaration"],
        containment=_containment(),
        candidate=ticket,
        admission_layers=admission_layers if admission_layers is not None else _layers(),
        exit_policy=exit_policy if exit_policy is not None else _exit_policy(),
        footprint_requirements=_requirements(),
        venue_capabilities=venue_capabilities,
        account_role=AccountRole.DEMO,
        assignment=assignment,
        read_surfaces={},
        stream_id="stream-eurusd",
        clock=clock,
        book=book,
        venue=venue,
        signal_snapshot=signal_snapshot,
        callback=callback,
        hosted=hosted,
        tunnel=tunnel,
    )


def _venue() -> VenueId:
    return _ok(VenueId.try_create("ctrader"))


def _instrument() -> Instrument:
    return Instrument(venue=_venue(), symbol="EURUSD")


def _account() -> Account:
    return _ok(Account.try_create("acct-1", _venue(), AccountRole.DEMO))


def _price(value: int) -> Price:
    return _ok(Price.try_create(value, _instrument(), 5))


def _r(numerator: int = 1, denominator: int = 1) -> ExactRational:
    return _ok(ExactRational.try_create(numerator, denominator, UnitKind.R_MULTIPLE))


def _rate() -> ExactRational:
    return _ok(ExactRational.try_create(1_000, 1, UnitKind.RATE))


def _entry() -> EntryIntent:
    slot = _ok(EvidenceSlot.try_create("sqs", "sqs-ref-1", _instant()))
    cited = _ok(CitedEvidence.try_create(sqs_reading=slot))
    return _ok(
        EntryIntent.try_create(
            _instrument(),
            Direction.LONG,
            _ok(ReasonCode.try_create("momentum-break", "scalper-v1")),
            _ok(ExecutionTarget.try_create("demo", _venue(), "acct-1")),
            proposed_r=_r(1),
            cited_evidence=cited,
        )
    )


class _OffsetStopModule:
    def derive_full_loss_price(
        self, *, entry_price: Price, direction: Direction, cited_evidence: CitedEvidence
    ) -> Result[Price]:
        del cited_evidence
        if direction is Direction.LONG:
            value = entry_price.value - 1_000
        else:
            value = entry_price.value + 1_000
        return Price.try_create(value, entry_price.instrument, entry_price.scale)


def _path(*, bms: str = "bms-1") -> BookPathContext:
    return BookPathContext(
        entry_price=_price(110_000),
        exit_logic_ref=_ok(
            ExitLogicRef.try_create("book.default.evidence_stop", {"style": "structure"})
        ),
        module=_OffsetStopModule(),
        book_resolved_requested_r=_r(1),
        r_unit_price=_rate(),
        value_factor=_ok(ValueFactor.try_create(100_000, 1, _instrument(), "USD")),
        money_scale=2,
        account=_account(),
        venue_id=_venue(),
        session_epoch="session-26-15",
        ordering_ordinal=0,
        bms_instance_id=bms,
        protective_stop_forms={"market": ENTRY_RELATIVE_FORM},
    )


def _drive_probe() -> ScriptedLimitProbe:
    return ScriptedLimitProbe(elapsed_ns=(0, 1), memory_bytes=(1, 1))


# --- surface ----------------------------------------------------------------


def test_admission_surface_and_closed_proof_roster() -> None:
    assert SEAT_ADMISSION_SURFACE == "qmn.seats.admission"
    assert SEAT_ADMISSION_PROOFS == (
        "registered_ct33",
        "qml_runtime_protocol",
        "prediction_linter",
        "declared_footprint",
        "canonical_assignment",
        "book_binding",
        "admission_layers",
    )
    assert ADMISSION_LAYER_NAMES == (
        "layer1_linters",
        "layer2_shakedown",
        "layer3_operator_signature",
    )
    assert INTENT_PATH_HOPS == ("book", "bms", "protection", "order")
    assert "admit_ungoverned_tunnel" in UNGOVERNED_TUNNEL_NAMES
    assert "ungoverned" in UNGOVERNED_EVIDENCE_KINDS
    assert "clock" in FORBIDDEN_SEAT_SURFACE_KEYS


# --- AC1: ungoverned tunnel cannot occupy a node seat -----------------------


def test_ungoverned_tunnel_access_is_refused_as_a_node_seat() -> None:
    access = _ok(admit_ungoverned_tunnel())
    refused = _refusal(_propose(candidate=access))
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["seat_allowed"] is False
    assert refused.context["tunnel_open"] is True
    missing = _refusal(_propose(candidate=None))
    assert missing.context["field"] == "candidate"
    explicit = refuse_ungoverned_tunnel_seat()
    assert explicit.category is RefusalCategory.POLICY_REJECTION


def test_missing_conformance_ticket_and_admission_layers_refuse() -> None:
    world = _world()
    refused = _refusal(_propose(world=world, candidate=object()))
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "candidate"
    incomplete = _refusal(_propose(world=world, admission_layers=_layers(layer3=False)))
    assert incomplete.context["field"] == "admission_layers"
    no_bms = _refusal(_propose(world=world, bms_instance_id=""))
    assert no_bms.category is RefusalCategory.INVALID_INPUT
    no_binding = _refusal(_propose(world=world, binding_ref=""))
    assert no_binding.category is RefusalCategory.INVALID_INPUT


def test_prediction_linter_and_canonical_assignment_run_at_seat_time() -> None:
    world = _world()
    unknown_family = _ok(
        ExitPolicy.try_create(
            {"other-family": _ok(ExitLogicRef.try_create("book.other", {"style": "structure"}))},
            permitted_exit_intent_kinds=(),
        )
    )
    predicted = _refusal(_propose(world=world, exit_policy=unknown_family))
    assert predicted.category is RefusalCategory.POLICY_REJECTION
    tuned = _refusal(_propose(world=world, assignment={"lookback": 21}))
    assert "canonical assignment" in str(tuned.context["reason"])
    caps = _refusal(_propose(world=world, venue_capabilities=frozenset({"trading"})))
    assert caps.context["field"] == "venue_capabilities"


def test_direct_callback_injection_refuses() -> None:
    def injected_callback(evidence: object) -> object:
        del evidence
        return ()

    world = _world()
    injected = _refusal(_propose(world=world, callback=injected_callback))
    assert injected.context["field"] == "callback"
    hosted = _ok(
        construct_bot(
            FunctionFactory(logic=lambda evidence: ()),
            declaration=world["declaration"],
            assignment={"lookback": 20},
            read_surfaces={},
        )
    )
    as_factory = _refusal(
        propose_node_seat(
            hosted,
            seat_id="seat-alpha",
            binding_ref="binding-live-1",
            bms_instance_id="bms-1",
            declaration=world["declaration"],
            containment=_containment(),
            candidate=_ok(_candidate(world)),
            admission_layers=_layers(),
            exit_policy=_exit_policy(),
            footprint_requirements=_requirements(),
            venue_capabilities=_VENUE_CAPS,
        )
    )
    assert as_factory.context["field"] == "factory"
    raw = _refusal(
        _propose(
            world=world,
            factory=injected_callback,
            candidate=_ok(_candidate(world)),
        )
    )
    assert raw.context["field"] == "factory"
    helper = inject_seat_callback(object())
    assert helper.category is RefusalCategory.POLICY_REJECTION


def test_clock_book_venue_and_signal_snapshot_are_refused_at_the_seat_door() -> None:
    clock = DataDrivenClock(
        boot_epoch_id="boot",
        wall_instants=(_instant(),),
        monotonic_ns=(0,),
    )
    assert _refusal(_propose(clock=clock)).category is RefusalCategory.POLICY_REJECTION
    assert _refusal(_propose(book=object())).category is RefusalCategory.POLICY_REJECTION
    assert _refusal(_propose(venue=object())).category is RefusalCategory.POLICY_REJECTION
    assert _refusal(_propose(signal_snapshot=object())).category is RefusalCategory.POLICY_REJECTION


def test_composition_root_ungoverned_imports_refuse() -> None:
    scanned = scan_production_src_for_ungoverned_tunnel()
    assert is_ok(scanned)
    helper = refuse_composition_root_ungoverned_import()
    assert helper.category is RefusalCategory.POLICY_REJECTION
    tree = ast.parse("from qml.conformance import admit_ungoverned_tunnel\n")
    assert ungoverned_tunnel_names_in_tree(tree) == ("admit_ungoverned_tunnel",)
    clean = ast.parse("from qmn.seats import propose_node_seat\n")
    assert ungoverned_tunnel_names_in_tree(clean) == ()


def test_governed_proposal_records_every_named_proof() -> None:
    admitted = _ok(_propose())
    assert isinstance(admitted, AdmittedNodeSeat)
    assert admitted.proof.proofs == SEAT_ADMISSION_PROOFS
    assert admitted.proof.assignment_is_canonical is True
    assert admitted.proof.candidate.ticket.layer1_passed is True
    assert admitted.proof.candidate.ticket.layer2_passed is True
    assert admitted.proof.admission_layers.all_passed is True
    assert admitted.proof.bms_instance_id == "bms-1"
    assert admitted.seat.assignment_is_canonical is True
    identity = admitted.proof.fp1_identity()
    assert identity["class"] == "seat-admission-proof"
    assert identity["proofs"] == list(SEAT_ADMISSION_PROOFS)


# --- AC2: hosted intents cross Book/BMS/protection/order --------------------


def test_hosted_entry_crosses_book_bms_protection_and_order() -> None:
    factory = FunctionFactory(logic=lambda evidence: (_entry(),))
    admitted = _ok(_propose(factory=factory))
    receipt = _ok(
        dispatch_seat_intents(
            admitted,
            _instant(),
            path=_path(),
            stream=SeatTransitionStream(),
            cancel=CancelToken(),
            probe=_drive_probe(),
        )
    )
    assert receipt.hops == INTENT_PATH_HOPS
    assert receipt.bms_instance_id == "bms-1"
    assert len(receipt.authorized) == 1
    assert len(receipt.commands) == 1
    assert receipt.commands[0].kind is CommandKind.PLACE_ORDER
    assert receipt.authorized[0].requested_r == _r(1)
    assert not hasattr(receipt.authorized[0].admitted, "bot_quantity")


def test_bot_supplied_size_and_direct_ct19_refuse() -> None:
    admitted = _ok(_propose())
    sized = _refusal(
        dispatch_hosted_intents(
            admitted,
            {"kind": "entry", "quantity": _ok(Quantity.try_create(3, "lot", 0))},
            path=_path(),
        )
    )
    assert sized.category is RefusalCategory.INVALID_INPUT
    params = _ok(
        OrderParameters.try_create(
            OrderType.MARKET,
            TimeInForce.GOOD_TILL_CANCEL,
            _ok(Quantity.try_create(1, "lot", 0)),
        )
    )
    command = _ok(Command.place_order(_venue(), _account(), "session-26-15", 0, params))
    ct19 = _refusal(dispatch_hosted_intents(admitted, command, path=_path()))
    assert ct19.context["field"] == "ct19"
    helper = refuse_bot_constructed_ct19(command)
    assert helper.category is RefusalCategory.POLICY_REJECTION


def test_raw_ql7_construct_cannot_enter_the_money_path() -> None:
    world = _world()
    raw = _ok(
        construct_governed_seat(
            FunctionFactory(logic=lambda evidence: (_entry(),)),
            seat_id="seat-alpha",
            binding_ref="binding-live-1",
            declaration=world["declaration"],
            containment=_containment(),
            assignment={"lookback": 20},
            read_surfaces={},
        )
    )
    refused = _refusal(dispatch_hosted_intents(raw, (_entry(),), path=_path()))
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "seat"
    mismatched = _ok(_propose())
    bms = _refusal(dispatch_hosted_intents(mismatched, (_entry(),), path=_path(bms="bms-other")))
    assert bms.context["field"] == "bms_instance_id"


def test_ungoverned_evidence_cannot_cite_a_governed_seat() -> None:
    admitted = _ok(_propose())
    ungoverned = _refusal(
        cite_governed_seat_occurrence(
            seat=admitted,
            candidate=admitted.proof.candidate,
            evidence_kind="ungoverned",
        )
    )
    assert ungoverned.category is RefusalCategory.POLICY_REJECTION
    assert ungoverned.context["citation_allowed"] is False
    missing_ticket = _refusal(
        cite_governed_seat_occurrence(
            seat=admitted,
            candidate=None,
            evidence_kind="governed-evidence",
        )
    )
    assert missing_ticket.category is RefusalCategory.POLICY_REJECTION
    world = _world()
    raw = _ok(
        construct_governed_seat(
            FunctionFactory(logic=lambda evidence: ()),
            seat_id="seat-alpha",
            binding_ref="binding-live-1",
            declaration=world["declaration"],
            containment=_containment(),
        )
    )
    raw_cite = _refusal(
        cite_governed_seat_occurrence(
            seat=raw,
            candidate=admitted.proof.candidate,
            evidence_kind="governed-evidence",
        )
    )
    assert raw_cite.context["field"] == "seat"
    cited = _ok(
        cite_governed_seat_occurrence(
            seat=admitted,
            candidate=admitted.proof.candidate,
            evidence_kind="governed-evidence",
        )
    )
    assert cited.kind.value == "governed-evidence"
    assert cited.fingerprint == admitted.proof.candidate.fingerprint
