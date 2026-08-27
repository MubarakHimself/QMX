"""Epic 17 · Group A — port-set composition & fidelity identity (Story 17.1, R1-R12).

Independent, requirements-derived assertions (T-17.1-a..m). Every assertion states
what a RATIFIED requirement demands (epics.md Story 17.1 ACs + B-6/B-7 spine +
CT-04/CT-23 + LABEL/SC-06/SC-07), never what the source happens to do. A failing
test is a FINDING, never a licence to soften the assertion or edit source.
"""

from __future__ import annotations

from _e17 import (
    NoStopModule,
    OffsetStopModule,
    RecordingCost,
    RecordingFill,
    RecordingFinancing,
    RecordingSlippage,
    config,
    entry,
    exit_intent,
    exit_logic_ref,
    ok,
    price,
    qty,
    r_multiple,
    refusal,
    replay_binding,
    slice_path,
)

from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import RefusalCategory, is_ok, is_refusal
from qmb.execution.binder import bind_execution_ports
from qmb.execution.fidelity import (
    FidelityTaxonomy,
    compare_book_bar_fidelity,
    compute_run_fidelity,
    stamp_fidelity,
)
from qmb.execution.ports import (
    TAINT_OPTIMISTIC,
    CostPort,
    ExecutionPorts,
    FillPort,
    FinancingPort,
    SlippagePort,
    apply_execution_ports,
    execute_authorized,
    refuse_optimistic_edge_claim,
    refuse_store_synthetic_governed_evidence,
    require_authorized_intent,
)

_ADAPTERS = dict(
    fill_adapter="declared-path",
    slippage_adapter="zero",
    cost_adapter="zero",
    financing_schedule="fx-broker",
)


def _ports():
    fill, slip, cost, fin = (
        RecordingFill(),
        RecordingSlippage(),
        RecordingCost(),
        RecordingFinancing(),
    )
    return ok(ExecutionPorts.try_create(fill, slip, cost, fin)), fill, slip, cost, fin


def _flat_path():
    return slice_path(prints=(100_000,), open=100_000, high=100_000, low=100_000, close=100_000)


# --- T-17.1-a (L2) three SEPARATE ports + financing, each by adapter-id [R1] ---
def test_t171a_binder_composes_three_separate_ports_plus_financing() -> None:
    bound = ok(bind_execution_ports(config(**_ADAPTERS)))
    ports = bound.ports
    # Three separate Protocol ports, each of the right seam, plus a financing scheduler.
    assert isinstance(ports.fill, FillPort)
    assert isinstance(ports.slippage, SlippagePort)
    assert isinstance(ports.cost, CostPort)
    assert isinstance(ports.financing, FinancingPort)
    # SEPARATE: fill, slippage and cost are distinct objects (B-6, AR-56).
    assert len({id(ports.fill), id(ports.slippage), id(ports.cost)}) == 3
    # Each was resolved by the adapter-id named in the config.
    assert bound.fill_adapter_id == "declared-path"
    assert bound.slippage_adapter_id == "zero"
    assert bound.cost_adapter_id == "zero"
    assert bound.financing_schedule_ref == "fx-broker"
    # Counter-case (verifies the guard can fail): a config missing the cost adapter refuses.
    missing = dict(_ADAPTERS)
    del missing["cost_adapter"]
    assert is_refusal(bind_execution_ports(config(**missing)))


# --- T-17.1-b (L2) composition order is pinned fill -> slippage -> cost [R1] ---
def test_t171b_composition_order_is_pinned_fill_slippage_cost() -> None:
    order: list[str] = []

    class OrderedFill:
        def decide(self, intent, path, *, requested_quantity, **rest):
            order.append("fill")
            from qmf.core.refusal import Ok
            from qmb.execution.ports import Fill

            return Ok(ok(Fill.try_create(requested_quantity, requested_quantity, price(100_000))))

    class OrderedSlippage:
        def apply(self, fill, path):
            order.append("slippage")
            # Slippage must run BEFORE cost: it receives a fill with NO post-slip yet.
            assert fill.post_slip_price is None
            from qmb.execution.ports import restamp_filled

            return restamp_filled(fill, post_slip_price=fill.pre_slip_price)

    class OrderedCost:
        def quote(self, fill):
            from _e17 import money

            return money(0)

        def itemize(self, fill):
            order.append("cost")
            # Cost itemizes on the POST-slip fill: slippage already stamped a post price.
            assert fill.post_slip_price is not None
            from qmb.execution.ports import CostedFill

            return CostedFill.try_create(fill, ())

    ports = ok(ExecutionPorts.try_create(OrderedFill(), OrderedSlippage(), OrderedCost(),
                                         RecordingFinancing()))
    out = apply_execution_ports(ports, intent=entry(), path=_flat_path(),
                                requested_quantity=qty(10), position_cap=qty(10), lot_step=qty(1))
    assert is_ok(out)
    # The pinned order is observed behaviourally, not read off a self-declared constant.
    assert order == ["fill", "slippage", "cost"]


# --- T-17.1-c (L3) binding only from resolved config, no ambient discovery [R2]
def test_t171c_binding_is_only_from_resolved_config_no_ambient_discovery() -> None:
    # An unknown adapter-id is refused against the closed catalog, not discovered.
    bad = dict(_ADAPTERS, cost_adapter="mystery-broker")
    unknown = refusal(bind_execution_ports(config(**bad)))
    assert unknown.category is RefusalCategory.INVALID_INPUT
    # A config that names NO cost adapter is refused, never ambiently defaulted to zero.
    missing = dict(_ADAPTERS)
    del missing["cost_adapter"]
    assert is_refusal(bind_execution_ports(config(**missing)))
    # Same config binds the same adapters deterministically.
    cfg = config(**_ADAPTERS)
    a = ok(bind_execution_ports(cfg))
    b = ok(bind_execution_ports(cfg))
    assert (a.fill_adapter_id, a.slippage_adapter_id, a.cost_adapter_id) == (
        b.fill_adapter_id, b.slippage_adapter_id, b.cost_adapter_id
    )


# --- T-17.1-d (L3) non-CT-23 inbound -> CT-04 refusal, no port executes [R3] P0
def test_t171d_non_ct23_inbound_refuses_and_no_port_executes() -> None:
    ports, fill, slip, cost, fin = _ports()
    bot_sized_order = {"instrument": "eurusd", "requested_r": "0.5", "size": 10}
    refused = apply_execution_ports(ports, intent=bot_sized_order, path=_flat_path(),
                                    requested_quantity=qty(10), position_cap=qty(10),
                                    lot_step=qty(1))
    assert is_refusal(refused) and refused.category is RefusalCategory.INVALID_INPUT
    # No port executed — observed through the test-owned recorders, not a returned flag.
    assert fill.calls == [] and slip.calls == [] and cost.calls == []
    # The guard itself: a bot-sized order / bare string / None are all refused.
    assert is_refusal(require_authorized_intent(bot_sized_order))
    assert is_refusal(require_authorized_intent("eurusd@2.0"))
    assert is_refusal(require_authorized_intent(None))
    # Counter-case: a real CT-23 intent DOES drive the ports (proves the recorder observes).
    ports2, fill2, _s, _c, _f = _ports()
    ok(apply_execution_ports(ports2, intent=entry(), path=_flat_path(),
                             requested_quantity=qty(10), position_cap=qty(10), lot_step=qty(1)))
    assert len(fill2.calls) == 1


# --- T-17.1-e (L2) well-formed CT-23 intent admitted unchanged, never re-sized [R4] P0
def test_t171e_authorized_intent_executed_without_resizing() -> None:
    the_entry = entry()
    ports, fill, slip, cost, fin = _ports()
    out = ok(apply_execution_ports(ports, intent=the_entry, path=_flat_path(),
                                   requested_quantity=qty(10), position_cap=qty(10),
                                   lot_step=qty(1)))
    from qmb.execution.ports import CostedFill

    assert isinstance(out, CostedFill)
    # The ports executed the SAME intent object — not a rewritten/re-sized copy.
    assert fill.calls[0]["intent"] is the_entry
    # Quantity is preserved end-to-end: the fill is the full requested quantity.
    assert out.fill.quantity.as_fraction() == 10
    assert out.fill.requested_quantity.as_fraction() == 10
    # A cost port that RE-SIZES the fill is refused by the never-resize guard (AR-56).
    from _e17 import ResizingCost

    bad = ok(ExecutionPorts.try_create(RecordingFill(), RecordingSlippage(), ResizingCost(),
                                       RecordingFinancing()))
    resized = apply_execution_ports(bad, intent=entry(), path=_flat_path(),
                                    requested_quantity=qty(10), position_cap=qty(10),
                                    lot_step=qty(1))
    assert is_refusal(resized) and resized.context.get("field") == "quantity"


# --- T-17.1-f (L3) opening intent with no AD-40 full-loss -> refuse before open [R5] P0
def test_t171f_open_without_full_loss_refuses_before_any_fill() -> None:
    ports, fill, slip, cost, fin = _ports()
    refused = execute_authorized(
        replay_binding(), intent=entry(), ports=ports, path=_flat_path(),
        requested_quantity=qty(10), position_cap=qty(10), lot_step=qty(1),
        data_provenance="recorded", entry_price=price(105_000),
        exit_logic_ref=exit_logic_ref(), module=NoStopModule(),
        book_resolved_requested_r=r_multiple(2),
    )
    assert is_refusal(refused)
    # The refusal precedes any open — the fill port was never invoked.
    assert fill.calls == [] and slip.calls == [] and cost.calls == []
    # Counter-case: an entry WITH a derivable full-loss price executes and invokes fill.
    ports2, fill2, _s, _c, _f = _ports()
    out = execute_authorized(
        replay_binding(), intent=entry(), ports=ports2, path=_flat_path(),
        requested_quantity=qty(10), position_cap=qty(10), lot_step=qty(1),
        data_provenance="recorded", entry_price=price(105_000),
        exit_logic_ref=exit_logic_ref(), module=OffsetStopModule(),
        book_resolved_requested_r=r_multiple(2),
    )
    assert is_ok(out) and len(fill2.calls) == 1


# --- T-17.1-g (L2) risk-reducing CT-29 exit admitted without a new full-loss [R6]
def test_t171g_exit_intent_admitted_without_new_full_loss() -> None:
    ports, fill, slip, cost, fin = _ports()
    out = execute_authorized(
        replay_binding(), intent=exit_intent(), ports=ports, path=_flat_path(),
        requested_quantity=qty(10), position_cap=qty(10), lot_step=qty(1),
        data_provenance="recorded",
    )
    from qmb.execution.ports import CostedFill

    # No entry_price / module / full-loss supplied — the exit still executes.
    assert is_ok(out) and isinstance(out.value, CostedFill)
    assert len(fill.calls) == 1


# --- T-17.1-h (L2) fidelity identity = adapter-id + comp-version + taint field [R7] P0
def test_t171h_fidelity_identity_shape_and_taint_field() -> None:
    ident = ok(stamp_fidelity("declared-path"))
    assert ident.adapter_id == "declared-path"
    assert ident.composition_version == 1
    assert ident.taint == TAINT_OPTIMISTIC
    # Taint is a FIELD, never part of the fp1 identity tuple (DEC-0164).
    content = ident.fp1_identity()
    assert "adapter_id" in content and "composition_version" in content
    assert "taint" not in content
    # A non-optimistic taint is refused until GAP-0048 (the taint cannot be dropped).
    assert is_refusal(stamp_fidelity("declared-path", taint="live"))


# --- T-17.1-i (L2) changing the bound set changes identity; never silently drifts [R8]
def test_t171i_changing_bound_set_changes_identity_no_drift() -> None:
    # Two runs binding different cost adapters produce DIFFERENT execution identities.
    a = ok(bind_execution_ports(config(**dict(_ADAPTERS, cost_adapter="zero"))))
    b = ok(bind_execution_ports(config(**dict(_ADAPTERS, cost_adapter="percent-of-notional"))))
    fp_a = ok(fingerprint(a.fp1_identity()))
    fp_b = ok(fingerprint(b.fp1_identity()))
    assert fp_a.value != fp_b.value
    # The same bound set fingerprints identically — identity never silently drifts.
    c = ok(bind_execution_ports(config(**dict(_ADAPTERS, cost_adapter="zero"))))
    assert ok(fingerprint(c.fp1_identity())).value == fp_a.value


# --- T-17.1-j (L1) run-fidelity fold returns the LOWEST bound adapter [R9] P0 --
def test_t171j_run_fidelity_is_lowest_wins_fold() -> None:
    ids = [ok(stamp_fidelity(name)) for name in ("fill.x", "slip.y", "cost.z")]
    taxonomy = ok(FidelityTaxonomy.try_create({"fill.x": 5, "slip.y": 2, "cost.z": 9}))
    run = ok(compute_run_fidelity(ids, taxonomy=taxonomy))
    assert run.lowest_adapter_id == "slip.y"  # rank 2 is the lowest fidelity
    # Move the min to a different adapter -> the winner follows (falsifiable fold).
    taxonomy2 = ok(FidelityTaxonomy.try_create({"fill.x": 1, "slip.y": 2, "cost.z": 9}))
    assert ok(compute_run_fidelity(ids, taxonomy=taxonomy2)).lowest_adapter_id == "fill.x"
    # Without a deferred taxonomy artifact NO ordinal winner is invented (SC-07).
    no_tax = ok(compute_run_fidelity(ids))
    assert no_tax.lowest_adapter_id is None and no_tax.taxonomy_deferred is True
    # A taxonomy missing an adapter's rank refuses rather than fabricating an order.
    partial = ok(FidelityTaxonomy.try_create({"fill.x": 1}))
    assert is_refusal(compute_run_fidelity(ids, taxonomy=partial))


# --- T-17.1-k (L3) mixed-fidelity comparison without override -> CT-04 refusal [R10] P0
def test_t171k_mixed_fidelity_comparison_refuses_without_override() -> None:
    left = ok(compute_run_fidelity([ok(stamp_fidelity("fill.a"))]))
    right = ok(compute_run_fidelity([ok(stamp_fidelity("fill.b"))]))
    refused = compare_book_bar_fidelity(left, right)
    assert is_refusal(refused) and refused.category is RefusalCategory.POLICY_REJECTION
    # An explicit bool-True override permits the comparison.
    assert is_ok(compare_book_bar_fidelity(left, right, override=True))
    # A non-bool override is refused — never a silent truthy flag.
    assert is_refusal(compare_book_bar_fidelity(left, right, override="yes"))
    # Identical fidelities compare without an override (no false refusal).
    assert is_ok(compare_book_bar_fidelity(left, left))


# --- T-17.1-l (L3) world=simulated / replay-on-synthetic refused [R11] --------
def test_t171l_world_simulated_and_replay_on_synthetic_refused() -> None:
    # A replay clock bound to synthetic-tainted data is invalid input (B-7).
    cfg = config(clock="replay", data_provenance="synthetic-tainted", world=World.SIMULATED,
                 **_ADAPTERS)
    refused = refusal(bind_execution_ports(cfg))
    assert refused.category is RefusalCategory.INVALID_INPUT
    # Store-persisted synthetic data derives world=simulated and is a policy rejection.
    sim = refusal(refuse_store_synthetic_governed_evidence("synthetic-tainted"))
    assert sim.category is RefusalCategory.POLICY_REJECTION
    assert sim.context.get("world") == World.SIMULATED.value
    # Recorded provenance derives world=replay and composes.
    assert refuse_store_synthetic_governed_evidence("recorded").value is World.REPLAY


# --- T-17.1-m (L3) optimistic-tainted run barred from edge claim / split budget [R12] P0
def test_t171m_optimistic_taint_bars_edge_claim_and_split_budget() -> None:
    # The default (no claim) is admitted.
    assert refuse_optimistic_edge_claim().value is None
    # Claiming edge is a policy rejection.
    edge = refusal(refuse_optimistic_edge_claim(claims_edge=True))
    assert edge.category is RefusalCategory.POLICY_REJECTION
    # Spending split budget is a policy rejection.
    budget = refusal(refuse_optimistic_edge_claim(spends_split_budget=True))
    assert budget.category is RefusalCategory.POLICY_REJECTION
    # A non-optimistic taint is itself refused until GAP-0048.
    assert is_refusal(refuse_optimistic_edge_claim(taint="aggressive"))
