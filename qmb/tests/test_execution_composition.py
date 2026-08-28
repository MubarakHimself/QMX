"""Story 17.1 — execution port-set composition and fidelity identity."""

from __future__ import annotations

from types import MappingProxyType
from typing import TypeVar

from qmb.config import (
    CLOCK_REPLAY,
    CLOCK_SIMULATED,
    PROVENANCE_RECORDED,
    PROVENANCE_SYNTHETIC_TAINTED,
    STARTING_CAPITAL_KEY,
    compile_run_config,
    materialize_bms_fragment,
    materialize_book_fragment,
    mint_replay_binding,
)
from qmb.doors import api
from qmb.execution import (
    AMBIENT_DISCOVERY,
    BOUND_FROM_RESOLVED_CONFIG,
    COMPOSITION_ORDER,
    COMPOSITION_VERSION,
    COST_ADAPTER_KEY,
    COST_ADAPTER_ZERO,
    FIDELITY_TAXONOMY_DEFERRED_TO,
    FILL_ADAPTER_DECLARED_PATH,
    FILL_ADAPTER_KEY,
    FINANCING_SCHEDULE_KEY,
    SLIPPAGE_ADAPTER_KEY,
    SLIPPAGE_ADAPTER_ZERO,
    TAINT_IS_IDENTITY,
    TAINT_OPTIMISTIC,
    BoundExecution,
    CostedFill,
    CostPort,
    DeclaredPathFillAdapter,
    FidelityIdentity,
    FidelityTaxonomy,
    FillPort,
    FinancingPort,
    RunFidelity,
    SlicePath,
    SlippagePort,
    ZeroCostAdapter,
    ZeroSlippageAdapter,
    bind_execution_ports,
    compare_book_bar_fidelity,
    composition_identity,
    lowest_fidelity,
    refuse_optimistic_edge_claim,
    stamp_fidelity,
)
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import ExactRational, Money, Price, Quantity, UnitKind
from qmf.core.fingerprint import World, fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import RegistrationRecord
from qmf.risk.door import Direction, EntryIntent, ExitIntent, ExitKind, ExitLogicRef, ReasonCode
from qmf.risk.grammar import AdmissionImpact, TemplateSection, TemplateVariable, UiEditability
from qmf.risk.paper import ExecutionTarget
from qmf.risk.templates import (
    BMS_CONTRACT_FORMAT_VERSION,
    BOOK_CONTRACT_FORMAT_VERSION,
    BmsDefinition,
    BookDefinition,
)

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_VENUE = "venue-replay"
_ACCOUNT = "acct-replay"
_SCHEDULE = "broker-swap-table"
_SEED = Money(value=1_000_000, currency="USD", scale=2)
_SEVERITY = "workspace-declared"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _fp(seed: str):
    return _ok(fingerprint({"seed": seed}))


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _instrument() -> Instrument:
    return Instrument(venue=VenueId(value=_VENUE), symbol="EURUSD")


def _price(value: int = 1_10000) -> Price:
    return _ok(Price.try_create(value, _instrument(), 5))


def _qty(value: int) -> Quantity:
    return _ok(Quantity.try_create(value, "lot", 0))


def _path() -> SlicePath:
    return _ok(SlicePath.try_create("eurusd", (_price(),)))


def _adapter_keys() -> dict[str, object]:
    return {
        COST_ADAPTER_KEY: COST_ADAPTER_ZERO,
        FILL_ADAPTER_KEY: FILL_ADAPTER_DECLARED_PATH,
        FINANCING_SCHEDULE_KEY: _SCHEDULE,
        SLIPPAGE_ADAPTER_KEY: SLIPPAGE_ADAPTER_ZERO,
    }


def _resolved(
    *,
    keys: dict[str, object] | None = None,
    omit: tuple[str, ...] = (),
    clock: str = CLOCK_REPLAY,
    provenance: str = PROVENANCE_RECORDED,
    world: World | None = None,
) -> qmb.ResolvedRunConfig:
    payload = _adapter_keys()
    if keys is not None:
        payload.update(keys)
    for key in omit:
        payload.pop(key, None)
    derived = World.SIMULATED if provenance == PROVENANCE_SYNTHETIC_TAINTED else World.REPLAY
    bound_world = world if world is not None else derived
    book = _fp("book")
    bms = _fp("bms")
    bot = _fp("bot")
    binding = _ok(
        mint_replay_binding(
            book_fp1=book,
            bms_fp1=bms,
            bot_fp1=bot,
            starting_capital=_SEED,
            seed_overridden=False,
            venue_id=_VENUE,
            account_id=_ACCOUNT,
            clock=clock,
            data_provenance=provenance,
            keys=payload,
        )
    )
    identity = {
        "book_fp1": book.value,
        "bms_fp1": bms.value,
        "bot_fp1": bot.value,
        "class": "resolved-run-config",
        "clock": clock,
        "data_provenance": provenance,
        "keys": payload,
        "world": bound_world.value,
    }
    return qmb.ResolvedRunConfig(
        format_version=1,
        book_fp1=book,
        bms_fp1=bms,
        bot_fp1=bot,
        book_fragment_fp1=_fp("book-frag"),
        bms_fragment_fp1=_fp("bms-frag"),
        keys=payload,
        clock=clock,
        data_provenance=provenance,
        world=bound_world,
        fingerprint=_ok(fingerprint(identity)),
        binding_fp1=binding.fingerprint,
        replay_binding=binding,
    )


def _entry() -> EntryIntent:
    return _ok(
        EntryIntent.try_create(
            _instrument(),
            Direction.LONG,
            _ok(ReasonCode.try_create("breakout", "scalper-v1")),
            _ok(ExecutionTarget.try_create("demo", VenueId(value=_VENUE), _ACCOUNT)),
        )
    )


def _exit() -> ExitIntent:
    return _ok(
        ExitIntent.try_create(
            ExitKind.CLOSE_FULL,
            _ok(ReasonCode.try_create("done", "scalper-v1")),
            _fp("vp-1"),
        )
    )


def _logic() -> ExitLogicRef:
    return _ok(ExitLogicRef.try_create("book.default.evidence_stop", {"style": "structure"}))


class _OffsetStopModule:
    def derive_full_loss_price(
        self, *, entry_price: Price, direction: Direction, cited_evidence: object
    ) -> Result[Price]:
        del cited_evidence
        value = entry_price.value - 500 if direction is Direction.LONG else entry_price.value + 500
        return Price.try_create(value, entry_price.instrument, entry_price.scale)


class _NoStopModule:
    def derive_full_loss_price(
        self, *, entry_price: Price, direction: Direction, cited_evidence: object
    ) -> Result[Price]:
        del entry_price, direction, cited_evidence
        from qmf.risk.door import refuse_no_full_loss_price

        return refuse_no_full_loss_price(module="no-stop")


class _BotSizedOrder:
    size = 1.0


def _writer(stream: str = "config-fragment") -> WriterId:
    return _ok(WriterId.try_create("node-a", "authoring", stream, "boot-1"))


def _money_variable(name: str, minor: int) -> TemplateVariable:
    return _ok(
        TemplateVariable.try_create(
            name,
            UnitKind.MONEY,
            Money(value=minor, currency="USD", scale=2),
            UiEditability.UI_EDITABLE,
            AdmissionImpact.RESIGN,
        )
    )


def _section(name: str, variable: TemplateVariable) -> TemplateSection:
    return _ok(TemplateSection.try_create(name, {variable.name: variable}))


def _compile_with_adapters() -> qmb.ResolvedRunConfig:
    book = _ok(
        BookDefinition.try_create(
            BOOK_CONTRACT_FORMAT_VERSION,
            "USD",
            {
                "admission_bar": _section("admission_bar", _money_variable("bar_floor", 1)),
                "money_rules": _section("money_rules", _money_variable("loss_floor", 800_000)),
                "exit_policy": _section("exit_policy", _money_variable("q", 100)),
            },
        )
    )
    bms = _ok(
        BmsDefinition.try_create(
            BMS_CONTRACT_FORMAT_VERSION,
            {
                "accounting_rules": _section(
                    "accounting_rules", _money_variable("numeraire_unit", 1)
                ),
                "constraints": _section("constraints", _money_variable("exposure_ceiling", 50_000)),
                "ksa_policy": _section("ksa_policy", _money_variable("posture", 1)),
                "reporting": _section("reporting", _money_variable("cadence", 1)),
            },
        )
    )
    book_record = _ok(
        RegistrationRecord.try_create(
            "book-definition",
            book.contract_format_version,
            (_ok(book.fingerprint()),),
            book.fp1_identity(),
            _writer("book-definition"),
            0,
            _instant(),
        )
    )
    bms_record = _ok(
        RegistrationRecord.try_create(
            "bms-definition",
            bms.contract_format_version,
            (_ok(bms.fingerprint()),),
            bms.fp1_identity(),
            _writer("bms-definition"),
            0,
            _instant(),
        )
    )
    bot = _ok(
        RegistrationRecord.try_create(
            "bot-definition",
            1,
            (),
            {"class": "bot-definition", "alias": "mean-reversion"},
            _writer("bot-definition"),
            0,
            _instant(),
        )
    )
    pointer = _ok(DatedPointer.try_create("mean-reversion", bot.stable_id, _instant()))
    as_of = _ok(
        AsOfSet.try_create(
            _instant(),
            records=(book_record, bms_record, bot),
            pointers=(pointer,),
        )
    )
    hub = _ok(PassiveHub.try_create((as_of,)))
    port = _ok(RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY))
    book_fragment = _ok(materialize_book_fragment(port, book_record.stable_id, _writer()))
    bms_fragment = _ok(materialize_bms_fragment(port, bms_record.stable_id, _writer()))
    return _ok(
        compile_run_config(
            port,
            book_fragment=book_fragment,
            bms_fragment=bms_fragment,
            run_spec={"bot": bot.stable_id, STARTING_CAPITAL_KEY: _SEED},
            workspace_defaults={
                "account_id": _ACCOUNT,
                "clock": CLOCK_REPLAY,
                "data_provenance": PROVENANCE_RECORDED,
                "venue_id": _VENUE,
                **_adapter_keys(),
            },
        )
    )


def test_bind_from_resolved_config_composes_separate_ports() -> None:
    assert AMBIENT_DISCOVERY is False
    assert BOUND_FROM_RESOLVED_CONFIG is True
    assert COMPOSITION_ORDER == ("fill", "slippage", "cost")
    compiled = _compile_with_adapters()
    bound = _ok(bind_execution_ports(compiled))
    assert isinstance(bound, BoundExecution)
    assert bound.fill_adapter_id == FILL_ADAPTER_DECLARED_PATH
    assert bound.slippage_adapter_id == SLIPPAGE_ADAPTER_ZERO
    assert bound.cost_adapter_id == COST_ADAPTER_ZERO
    assert bound.financing_schedule_ref == _SCHEDULE
    # composition-version is RECOMPUTED from the bound port set (R8, 17.1/AC4), never the
    # bare COMPOSITION_VERSION constant; the constant survives only as the recipe anchor.
    from qmb.execution import derive_composition_version

    assert bound.composition_version == _ok(derive_composition_version(bound.fidelity.bound))
    assert bound.composition_version.startswith(f"{COMPOSITION_VERSION}:")
    assert bound.composition_version != COMPOSITION_VERSION
    assert isinstance(bound.ports.fill, FillPort)
    assert isinstance(bound.ports.slippage, SlippagePort)
    assert isinstance(bound.ports.cost, CostPort)
    assert isinstance(bound.ports.financing, FinancingPort)
    assert bound.ports.fill is not bound.ports.slippage
    assert bound.ports.fill is not bound.ports.cost
    assert bound.ports.slippage is not bound.ports.cost
    assert isinstance(bound.ports.fill, DeclaredPathFillAdapter)
    assert isinstance(bound.ports.slippage, ZeroSlippageAdapter)
    assert isinstance(bound.ports.cost, ZeroCostAdapter)
    identity = composition_identity()
    assert identity["bound_from"] == "resolved-run-config"
    assert identity["ambient_discovery"] is False
    assert identity["composition_order"] == COMPOSITION_ORDER
    assert qmb.__version__ not in identity.values()


def test_binding_refuses_ambient_objects_and_unknown_ids() -> None:
    clean = _resolved()
    ambient_keys = dict(_adapter_keys())
    ambient_keys[FILL_ADAPTER_KEY] = DeclaredPathFillAdapter()
    stuffed = qmb.ResolvedRunConfig(
        format_version=clean.format_version,
        book_fp1=clean.book_fp1,
        bms_fp1=clean.bms_fp1,
        bot_fp1=clean.bot_fp1,
        book_fragment_fp1=clean.book_fragment_fp1,
        bms_fragment_fp1=clean.bms_fragment_fp1,
        keys=ambient_keys,
        clock=clean.clock,
        data_provenance=clean.data_provenance,
        world=clean.world,
        fingerprint=clean.fingerprint,
        binding_fp1=clean.binding_fp1,
        replay_binding=clean.replay_binding,
    )
    ambient = bind_execution_ports(stuffed)
    assert is_refusal(ambient)
    assert ambient.category is RefusalCategory.INVALID_INPUT
    assert ambient.context["field"] == FILL_ADAPTER_KEY
    unknown = bind_execution_ports(_resolved(keys={FILL_ADAPTER_KEY: "tick-fill"}))
    assert is_refusal(unknown)
    assert unknown.category is RefusalCategory.INVALID_INPUT
    missing = bind_execution_ports(_resolved(omit=(FILL_ADAPTER_KEY,)))
    assert is_refusal(missing)
    not_config = bind_execution_ports({"fill_adapter": FILL_ADAPTER_DECLARED_PATH})
    assert is_refusal(not_config)
    assert not_config.context["field"] == "config"
    assert isinstance(qmb.FILL_ADAPTER_CATALOG, MappingProxyType)


def test_bot_sized_order_is_refused_and_does_not_execute() -> None:
    bound = _ok(bind_execution_ports(_resolved()))
    refused = bound.execute(
        intent=_BotSizedOrder(),
        path=_path(),
        requested_quantity=_qty(1),
        position_cap=_qty(1),
        lot_step=_qty(1),
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "intent"


def test_full_loss_required_before_open_exits_skip_it() -> None:
    bound = _ok(bind_execution_ports(_resolved()))
    entry = _price()
    missing = bound.execute(
        intent=_entry(),
        path=_path(),
        requested_quantity=_qty(1),
        position_cap=_qty(1),
        lot_step=_qty(1),
        entry_price=entry,
        exit_logic_ref=_logic(),
        module=_NoStopModule(),
        book_resolved_requested_r=_ok(ExactRational.try_create(1, 1, UnitKind.R_MULTIPLE)),
    )
    assert is_refusal(missing)
    opened = bound.execute(
        intent=_entry(),
        path=_path(),
        requested_quantity=_qty(1),
        position_cap=_qty(1),
        lot_step=_qty(1),
        entry_price=entry,
        exit_logic_ref=_logic(),
        module=_OffsetStopModule(),
        book_resolved_requested_r=_ok(ExactRational.try_create(1, 1, UnitKind.R_MULTIPLE)),
    )
    assert is_ok(opened)
    assert isinstance(opened.value, CostedFill)
    assert opened.value.fill.taint == TAINT_OPTIMISTIC
    closed = bound.execute(
        intent=_exit(),
        path=_path(),
        requested_quantity=_qty(1),
        position_cap=_qty(1),
        lot_step=_qty(1),
    )
    assert is_ok(closed)


def test_fidelity_identity_is_adapter_id_composition_version_taint() -> None:
    bound = _ok(bind_execution_ports(_resolved()))
    assert bound.fidelity.taint == TAINT_OPTIMISTIC
    assert bound.fidelity.taxonomy_deferred is True
    assert len(bound.fidelity.bound) == 4
    for item in bound.fidelity.bound:
        assert isinstance(item, FidelityIdentity)
        assert item.composition_version == COMPOSITION_VERSION
        assert item.taint == TAINT_OPTIMISTIC
        assert "taint" not in item.fp1_identity()
        assert TAINT_IS_IDENTITY is False
    fill_id = bound.fidelity.bound[0]
    assert fill_id.adapter_id == FILL_ADAPTER_DECLARED_PATH
    financing = bound.fidelity.bound[3]
    assert financing.calibration_ref == _SCHEDULE
    stamped = _ok(stamp_fidelity("declared-path"))
    assert stamped.taint == TAINT_OPTIMISTIC
    other_taint = stamp_fidelity("declared-path", taint="calibrated")
    assert is_refusal(other_taint)
    assert other_taint.category is RefusalCategory.POLICY_REJECTION
    first = _ok(fingerprint(bound.fp1_identity()))
    permuted = dict(bound.fp1_identity())
    permuted["composition_order"] = list(reversed(COMPOSITION_ORDER))
    assert _ok(fingerprint(permuted)).value != first.value
    swapped = _ok(bind_execution_ports(_resolved()))
    assert _ok(fingerprint(swapped.fp1_identity())).value == first.value


def test_lowest_fidelity_consumes_deferred_taxonomy_without_inventing_ranks() -> None:
    bound = _ok(bind_execution_ports(_resolved()))
    deferred = _ok(lowest_fidelity(bound.fidelity.bound))
    assert deferred.taint == TAINT_OPTIMISTIC
    assert deferred.taxonomy_deferred is True
    assert deferred.lowest_adapter_id is None
    assert FIDELITY_TAXONOMY_DEFERRED_TO == "GAP-0048"
    taxonomy = _ok(
        FidelityTaxonomy.try_create(
            {
                FILL_ADAPTER_DECLARED_PATH: 2,
                "slippage.zero": 1,
                "cost.zero": 0,
                "financing.scheduled": 3,
            }
        )
    )
    ranked = _ok(lowest_fidelity(bound.fidelity.bound, taxonomy=taxonomy))
    assert ranked.taxonomy_deferred is False
    assert ranked.lowest_adapter_id == "cost.zero"
    missing = lowest_fidelity(bound.fidelity.bound, taxonomy={"only-quote-real": 0})
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    invented_float = FidelityTaxonomy.try_create({FILL_ADAPTER_DECLARED_PATH: 0.5})
    assert is_refusal(invented_float)
    assert invented_float.category is RefusalCategory.INVALID_INPUT


def test_mixed_fidelity_book_bar_comparison_refuses_without_override() -> None:
    left = _ok(bind_execution_ports(_resolved()))
    right_ids = tuple(
        _ok(stamp_fidelity("quote-real", composition_version=COMPOSITION_VERSION))
        if item.adapter_id == FILL_ADAPTER_DECLARED_PATH
        else item
        for item in left.fidelity.bound
    )
    right = _ok(lowest_fidelity(right_ids))
    refused = compare_book_bar_fidelity(left.fidelity, right)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "fidelity"
    same = compare_book_bar_fidelity(left, left.fidelity)
    assert is_ok(same)
    overridden = compare_book_bar_fidelity(left.fidelity, right, override=True)
    assert is_ok(overridden)
    bad_override = compare_book_bar_fidelity(left.fidelity, right, override="yes")
    assert is_refusal(bad_override)
    assert bad_override.category is RefusalCategory.INVALID_INPUT


def test_world_simulated_and_replay_on_synthetic_are_refused() -> None:
    simulated = bind_execution_ports(
        _resolved(
            clock=CLOCK_SIMULATED,
            provenance=PROVENANCE_SYNTHETIC_TAINTED,
            world=World.SIMULATED,
        )
    )
    assert is_refusal(simulated)
    assert simulated.category is RefusalCategory.POLICY_REJECTION
    assert simulated.context["field"] == "world"
    replay_synth = bind_execution_ports(
        _resolved(
            clock=CLOCK_REPLAY,
            provenance=PROVENANCE_SYNTHETIC_TAINTED,
            world=World.SIMULATED,
        )
    )
    assert is_refusal(replay_synth)
    assert replay_synth.category is RefusalCategory.INVALID_INPUT
    assert replay_synth.context["field"] == "clock"
    edge = refuse_optimistic_edge_claim(claims_edge=True)
    assert is_refusal(edge)
    assert edge.category is RefusalCategory.POLICY_REJECTION
    budget = refuse_optimistic_edge_claim(spends_split_budget=True)
    assert is_refusal(budget)
    bound = _ok(bind_execution_ports(_resolved()))
    financing = bound.ports.financing.schedule(stream_id="eurusd", direction=Direction.LONG)
    assert is_refusal(financing)
    assert financing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert financing.context["gap"] == "GAP-0048"


def test_api_door_matches_composition_surface() -> None:
    assert api.bind_execution_ports is qmb.bind_execution_ports is bind_execution_ports
    assert api.BoundExecution is qmb.BoundExecution is BoundExecution
    assert api.compare_book_bar_fidelity is qmb.compare_book_bar_fidelity
    assert api.lowest_fidelity is qmb.lowest_fidelity
    assert api.RunFidelity is qmb.RunFidelity is RunFidelity
    assert api.FILL_ADAPTER_KEY == qmb.FILL_ADAPTER_KEY == FILL_ADAPTER_KEY
    assert api.AMBIENT_DISCOVERY is qmb.AMBIENT_DISCOVERY is False
    assert api.composition_identity() == qmb.composition_identity()
    assert "version" not in qmb.composition_identity()
    assert qmb.__version__ not in qmb.composition_identity().values()
