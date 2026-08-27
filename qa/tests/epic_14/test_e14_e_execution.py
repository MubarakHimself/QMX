"""Epic 14 · Group E — CT-23 intake, execution ports, CT-29 exits (Story 14.5, R21-R25).

B-6/AR-56: inbound execution is a CT-23 Book-resolved authorized intent or a
typed refusal, never a bot-sized order; fill/slippage/cost are SEPARATE ports
and fill decides Fill|NoFill|PartialFill with partials first-class; every close
mints exactly one CT-29 exit; every pre-GAP-0048 fill carries the optimistic
taint and claims no edge / spends no split budget; store-persisted synthetic
data is world=simulated and a policy rejection for governed evidence.
"""

from __future__ import annotations

from _e14 import ok

from qmf.core.exact import Price, Quantity
from qmf.core.fingerprint import World, fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import RefusalCategory, is_refusal
from qmb.execution.ports import (
    CLAIMS_EDGE,
    SPENDS_SPLIT_BUDGET,
    TAINT_OPTIMISTIC,
    Fill,
    FillKind,
    NoFill,
    PartialFill,
    classify_fill_quantity,
    derive_world_from_provenance,
    ports_identity,
    record_virtual_close,
    refuse_optimistic_edge_claim,
    refuse_store_synthetic_governed_evidence,
    require_authorized_intent,
)


def _qty(value: int) -> Quantity:
    return ok(Quantity.try_create(value, "lot", 0))


def _price(value: int = 110000) -> Price:
    instrument = Instrument(venue=VenueId(value="sim-venue"), symbol="EURUSD")
    return ok(Price.try_create(value, instrument, 5))


# --- T-14.5-a / T-14.5-f (L3/L2) only a CT-23 intent; never a bot-sized order [R21]
def test_t145a_inbound_is_ct23_intent_never_bot_sized_order() -> None:
    bot_sized_order = {"instrument": "eurusd", "requested_r": "0.5", "size": 10}
    refused = require_authorized_intent(bot_sized_order)
    assert is_refusal(refused) and refused.category is RefusalCategory.INVALID_INPUT
    assert is_refusal(require_authorized_intent("eurusd@2.0"))
    assert is_refusal(require_authorized_intent(None))
    ident = ports_identity()
    # The AD-40 full-loss-before-open requirement is pinned on the port identity.
    assert ident["full_loss_before_open"] is True
    # Inbound authorized intents are the CT-23 EntryIntent / ExitIntent nouns.
    named = " ".join(ident["authorized_intent"])
    assert "EntryIntent" in named and "ExitIntent" in named


# --- T-14.5-b (L2) fill decides Fill|NoFill|PartialFill, partials first-class [R22]
def test_t145b_fill_decisions_are_first_class() -> None:
    partial = ok(
        classify_fill_quantity(
            requested=_qty(10),
            filled=_qty(10),
            position_cap=_qty(4),  # cap forces a partial
            lot_step=_qty(1),
            pre_slip_price=_price(),
        )
    )
    assert isinstance(partial, PartialFill)
    assert partial.kind is FillKind.PARTIAL_FILL
    assert partial.quantity.as_fraction() == 4
    assert partial.remaining_quantity.as_fraction() == 6
    full = ok(
        classify_fill_quantity(
            requested=_qty(10),
            filled=_qty(10),
            position_cap=_qty(10),
            lot_step=_qty(1),
            pre_slip_price=_price(),
        )
    )
    assert isinstance(full, Fill) and full.kind is FillKind.FILL
    none = ok(
        classify_fill_quantity(
            requested=_qty(10),
            filled=_qty(0),
            position_cap=_qty(10),
            lot_step=_qty(1),
            pre_slip_price=_price(),
        )
    )
    assert isinstance(none, NoFill) and none.kind is FillKind.NO_FILL
    # PartialFill is its own type, not a flag on Fill.
    assert PartialFill is not Fill


# --- T-14.5-c (L3) exactly one CT-29 exit per virtual close [R23] · P1 --------
def test_t145c_one_ct29_exit_per_close() -> None:
    ref = ok(fingerprint({"virtual_position": "vp-1"}))
    # A second close of an already-closed virtual position is a policy rejection.
    refused = record_virtual_close(
        None,
        virtual_position_ref=ref,
        opening_bot_id="bot",
        original_risk_distance=None,
        original_risk_amount=None,
        fill_references=(),
        realized_pnl=None,
        cost_components=(),
        close_reason=None,
        mechanism=None,
        outcome=None,
        closing_authority=None,
        close_reason_mapping_version=None,
        result_label=None,
        loss_predicate_format_version=None,
        recorded_at=None,
        closed_refs=(ref,),  # already closed
    )
    assert is_refusal(refused) and refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context.get("field") == "virtual_position_ref"


# --- T-14.5-d (L3) every fill is optimistic-tainted; no edge / no budget [R24] P1
def test_t145d_optimistic_taint_claims_no_edge() -> None:
    assert CLAIMS_EDGE is False
    assert SPENDS_SPLIT_BUDGET is False
    fill = ok(Fill.try_create(_qty(10), _qty(10), _price()))
    assert fill.taint == TAINT_OPTIMISTIC
    assert ok(NoFill.try_create("closed")).taint == TAINT_OPTIMISTIC
    # An optimistic fill claiming edge or spending split budget is refused.
    assert ok(refuse_optimistic_edge_claim()) is None
    edge = refuse_optimistic_edge_claim(claims_edge=True)
    assert is_refusal(edge) and edge.category is RefusalCategory.POLICY_REJECTION
    budget = refuse_optimistic_edge_claim(spends_split_budget=True)
    assert is_refusal(budget) and budget.category is RefusalCategory.POLICY_REJECTION
    # A non-optimistic taint is itself refused until GAP-0048.
    assert is_refusal(refuse_optimistic_edge_claim(taint="aggressive"))


# --- T-14.5-e (L3) store-persisted synthetic is world=simulated, refused [R25] P1
def test_t145e_synthetic_is_world_simulated_policy_rejection() -> None:
    refused = refuse_store_synthetic_governed_evidence("synthetic-tainted")
    assert is_refusal(refused) and refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context.get("world") == World.SIMULATED.value
    assert refused.context.get("gap") == "GAP-0048"
    # Recorded provenance derives world=replay and is admitted.
    assert ok(refuse_store_synthetic_governed_evidence("recorded")) is World.REPLAY
    assert ok(derive_world_from_provenance("recorded")) is World.REPLAY
    assert ok(derive_world_from_provenance("synthetic-tainted")) is World.SIMULATED
