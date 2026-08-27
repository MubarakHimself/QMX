"""Story 22.4 — the pre-build rule-significance gate (signal-only edge test).

Covers the six acceptance criteria: a signal-only pass over the B-2 event-slice loop
with orders disabled, trading locked as in warm-up, the strategy permanently flat, and
any mint/exit/command a typed policy rejection (AC1); look-ahead-safe next-bar log
returns where exact Price closes cross the return-space carve-out via the named AD-22
conversion (AC2); a detrended zero-edge null with the rule-return series re-centred to
zero and an empirical one-tailed p-value (AC3); the UI-editable resampling scheme
(iid/block/stationary), block length, iteration count, and minimum-observation floor,
each with no ratified value and no invented default (AC4); the insufficient-data typed
refusal, the floor-unset low-confidence label, recorded seed provenance, and bit-for-bit
reproducibility (AC5); and the advisory-only discipline — replay/simulated never live,
robustness never edge, never auto-merges, never gates live money, thresholds deferred to
GAP-0049 (AC6).
"""

from __future__ import annotations

from fractions import Fraction
from typing import TypeVar

from qmb.robustness import (
    ALPHA_THRESHOLDS_DEFERRED_TO,
    GATE_AUTO_MERGES,
    GATE_GATES_LIVE_MONEY,
    GATE_IS_ADVISORY,
    ITERATIONS_KEY,
    LOW_CONFIDENCE_FLOOR_UNSET_LABEL,
    MINIMUM_OBSERVATIONS_KEY,
    NULL_DETRENDED_BY,
    NULL_HYPOTHESIS,
    RESAMPLING_SCHEME_KEY,
    RESAMPLING_SCHEMES,
    RETURN_ALIGNMENT,
    RETURN_BASIS,
    RNG_FAMILY,
    RULE_SIGNIFICANCE_PROCEDURE,
    SCHEME_BLOCK,
    SCHEME_IID,
    SCHEME_STATIONARY,
    SIGNAL_PASS_ORDERS_ENABLED,
    SIGNAL_PASS_STRATEGY_STAYS_FLAT,
    SIGNAL_PASS_TRADING_LOCKED,
    SIGNIFICANCE_BLOCK_LENGTH_KEY,
    SIGNIFICANCE_CLAIM_CLASS,
    SIGNIFICANCE_MODE,
    SIGNIFICANCE_SEED_DERIVATION_RULE,
    SIGNIFICANCE_WORLD,
    SignalBar,
    guard_signal_pass,
    next_bar_log_returns,
    procedure_contract,
    refuse_edge_claim,
    refuse_gate_auto_merge,
    refuse_live_money_gate,
    refuse_live_result_world,
    refuse_signal_pass_act,
    run_signal_only_pass,
    run_significance_gate,
    significance_identity,
)
from qmb.runloop import RestingIntent, SliceObservation, run
from qmf.core.chrono import Instant
from qmf.core.exact import Price
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import Ok, RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_DAY_NS = 86_400_000_000_000
_BASE_NS = 1_700_000_000_000_000_000
_INSTRUMENT = Instrument(venue=VenueId(value="ctrader"), symbol="EURUSD")

# A price path stepping up after each odd bar; the rule fires on the even bars, right
# before every up-move — a clean edge-looking pattern.
_CLOSES = (
    100_000,
    101_000,
    100_500,
    102_000,
    101_500,
    103_000,
    102_500,
    104_000,
    103_500,
    105_000,
    104_500,
    106_000,
)
_FIRED = (True, False, True, False, True, False, True, False, True, False, True, False)


def _unwrap(result: Result[T], what: str = "value") -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _price(minor: int) -> Price:
    return _unwrap(Price.try_create(minor, _INSTRUMENT, 5), "price")


def _bars(fired: tuple[bool, ...] = _FIRED) -> tuple[SignalBar, ...]:
    return tuple(
        _unwrap(SignalBar.try_create(_instant(_BASE_NS + index * _DAY_NS), _price(close), flag))
        for index, (close, flag) in enumerate(zip(_CLOSES, fired, strict=True))
    )


# --- AC1: signal-only pass over the B-2 loop, orders disabled, flat ----------


def test_signal_only_pass_runs_the_loop_trading_locked_and_flat() -> None:
    bars = _bars()
    confirmed = _unwrap(run_signal_only_pass(bars))
    assert confirmed == bars
    assert SIGNAL_PASS_ORDERS_ENABLED is False
    assert SIGNAL_PASS_TRADING_LOCKED is True
    assert SIGNAL_PASS_STRATEGY_STAYS_FLAT is True


def test_mint_during_the_locked_pass_is_a_policy_rejection() -> None:
    bars = _bars()
    slices = tuple(
        (_unwrap(SliceObservation.try_create("signal-pass", bar.instant, True)),) for bar in bars
    )
    minted = run(
        slices=slices,
        stream_set=("signal-pass",),
        handler=_MintingHandler(),
        embargo=len(bars),
    )
    assert is_refusal(minted)
    assert minted.category is RefusalCategory.POLICY_REJECTION


def test_refuse_signal_pass_act_is_a_typed_policy_rejection() -> None:
    for action in ("enter", "exit", "command"):
        refusal = refuse_signal_pass_act(action)
        assert refusal.category is RefusalCategory.POLICY_REJECTION
        assert refusal.context["action"] == action
    guarded = guard_signal_pass("mint")
    assert is_refusal(guarded)
    assert guarded.category is RefusalCategory.POLICY_REJECTION


def test_the_gate_performs_the_signal_only_pass_and_refuses_a_bad_pass() -> None:
    # A single bar cannot form a next-bar return; the gate refuses it downstream, but
    # the signal-only pass itself accepts any non-empty ordered window.
    one = (_unwrap(SignalBar.try_create(_instant(_BASE_NS), _price(100_000), True)),)
    assert is_ok(run_signal_only_pass(one))
    empty = run_signal_only_pass(())
    assert is_refusal(empty)


# --- AC2: look-ahead-safe next-bar log returns through the carve-out ---------


def test_next_bar_log_returns_are_aligned_and_exact() -> None:
    bars = _bars()
    returns = _unwrap(next_bar_log_returns(bars))
    # One return per bar except the last (no next bar) — no forming/future leak.
    assert len(returns) == len(bars) - 1
    assert all(isinstance(value, Fraction) for value in returns)
    assert RETURN_ALIGNMENT == "signal-at-t-scored-on-next-bar-return"
    assert RETURN_BASIS == "log-returns"


def test_next_bar_return_needs_two_bars() -> None:
    one = (_unwrap(SignalBar.try_create(_instant(_BASE_NS), _price(100_000), True)),)
    refusal = next_bar_log_returns(one)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT


def test_close_price_must_be_exact_price_never_a_float() -> None:
    assert is_refusal(SignalBar.try_create(_instant(_BASE_NS), 1.5, True))
    assert is_refusal(SignalBar.try_create(_instant(_BASE_NS), 100_000, True))  # not a Price


def test_signals_are_strictly_time_ordered() -> None:
    a = _unwrap(SignalBar.try_create(_instant(_BASE_NS + _DAY_NS), _price(100_000), True))
    b = _unwrap(SignalBar.try_create(_instant(_BASE_NS), _price(101_000), False))
    refusal = run_significance_gate(
        signals=(a, b), base_seed=1, resampling_scheme=SCHEME_IID, iterations=50
    )
    assert is_refusal(refusal)


# --- AC3: detrended zero-edge null and the one-tailed p-value ----------------


def test_edge_rule_gets_a_small_p_value_no_edge_is_middling_anti_edge_is_large() -> None:
    edge = _unwrap(
        run_significance_gate(
            signals=_bars(),
            base_seed=7,
            resampling_scheme=SCHEME_IID,
            iterations=1000,
            minimum_observations=4,
        )
    )
    assert edge.p_value == 0  # fires right before every up-move
    assert edge.emits_verdict is False
    assert NULL_HYPOTHESIS == "E[return]=0"
    assert NULL_DETRENDED_BY == "in-sample-mean"

    all_fire = _bars(tuple(True for _ in _FIRED))
    middling = _unwrap(
        run_significance_gate(
            signals=all_fire,
            base_seed=7,
            resampling_scheme=SCHEME_IID,
            iterations=1000,
            minimum_observations=4,
        )
    )
    assert 0 < middling.p_value < 1  # zero excess over market drift

    anti = _bars(tuple(index % 2 == 1 for index in range(len(_FIRED))))
    against = _unwrap(
        run_significance_gate(
            signals=anti,
            base_seed=7,
            resampling_scheme=SCHEME_IID,
            iterations=1000,
            minimum_observations=4,
        )
    )
    assert against.p_value > middling.p_value


def test_p_value_is_an_exact_fraction_in_the_unit_interval() -> None:
    result = _unwrap(
        run_significance_gate(
            signals=_bars(),
            base_seed=11,
            resampling_scheme=SCHEME_IID,
            iterations=500,
            minimum_observations=4,
        )
    )
    assert isinstance(result.p_value, Fraction)
    assert 0 <= result.p_value <= 1
    assert result.null.iterations == 500


def test_a_rule_that_never_fires_is_a_typed_refusal_never_a_p_value() -> None:
    never = _bars(tuple(False for _ in _FIRED))
    refusal = run_significance_gate(
        signals=never, base_seed=7, resampling_scheme=SCHEME_IID, iterations=50
    )
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT


# --- AC4: configurable scheme and parameters, no invented default ------------


def test_the_three_resampling_schemes_are_configurable() -> None:
    assert RESAMPLING_SCHEMES == (SCHEME_IID, SCHEME_BLOCK, SCHEME_STATIONARY)
    for scheme in RESAMPLING_SCHEMES:
        result = _unwrap(
            run_significance_gate(
                signals=_bars(),
                base_seed=5,
                resampling_scheme=scheme,
                block_length=3,
                iterations=200,
                minimum_observations=4,
            )
        )
        assert result.provenance.resampling_scheme == scheme
    # iid ignores the block length (it has none in provenance).
    iid = _unwrap(
        run_significance_gate(
            signals=_bars(), base_seed=5, resampling_scheme=SCHEME_IID, iterations=200
        )
    )
    assert iid.provenance.block_length is None


def test_block_and_stationary_require_a_block_length() -> None:
    for scheme in (SCHEME_BLOCK, SCHEME_STATIONARY):
        refusal = run_significance_gate(
            signals=_bars(), base_seed=5, resampling_scheme=scheme, iterations=200
        )
        assert is_refusal(refusal)
        assert refusal.category is RefusalCategory.INVALID_INPUT


def test_unset_scheme_and_iterations_are_typed_refusals() -> None:
    assert is_refusal(run_significance_gate(signals=_bars(), base_seed=5, iterations=200))
    assert is_refusal(
        run_significance_gate(signals=_bars(), base_seed=5, resampling_scheme=SCHEME_IID)
    )
    off_roster = run_significance_gate(
        signals=_bars(), base_seed=5, resampling_scheme="bogus", iterations=200
    )
    assert is_refusal(off_roster)


def test_configurables_resolve_from_the_run_config_keys() -> None:
    config = {
        RESAMPLING_SCHEME_KEY: SCHEME_BLOCK,
        SIGNIFICANCE_BLOCK_LENGTH_KEY: 4,
        ITERATIONS_KEY: 300,
        MINIMUM_OBSERVATIONS_KEY: 5,
    }
    result = _unwrap(run_significance_gate(signals=_bars(), base_seed=9, config=config))
    assert result.provenance.resampling_scheme == SCHEME_BLOCK
    assert result.provenance.block_length == 4
    assert result.provenance.iterations == 300
    assert result.provenance.minimum_observations == 5
    assert result.low_confidence is False


def test_module_ships_no_invented_default_for_the_parameters() -> None:
    identity = significance_identity()
    assert identity["procedure"] == RULE_SIGNIFICANCE_PROCEDURE
    assert identity["resampling_schemes"] == RESAMPLING_SCHEMES
    assert identity["iterations_key"] == ITERATIONS_KEY
    assert identity["minimum_observations_key"] == MINIMUM_OBSERVATIONS_KEY
    assert identity["resampling_scheme_key"] == RESAMPLING_SCHEME_KEY


# --- AC5: insufficient data, low confidence, provenance, reproducibility -----


def test_below_the_configured_floor_is_a_typed_refusal() -> None:
    refusal = run_significance_gate(
        signals=_bars(),
        base_seed=7,
        resampling_scheme=SCHEME_IID,
        iterations=200,
        minimum_observations=100,
    )
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["minimum_observations"] == 100


def test_unset_floor_emits_a_low_confidence_label() -> None:
    result = _unwrap(
        run_significance_gate(
            signals=_bars(), base_seed=7, resampling_scheme=SCHEME_IID, iterations=200
        )
    )
    assert result.low_confidence is True
    assert result.low_confidence_label == LOW_CONFIDENCE_FLOOR_UNSET_LABEL
    assert result.provenance.minimum_observations is None


def test_floor_met_is_not_low_confidence() -> None:
    result = _unwrap(
        run_significance_gate(
            signals=_bars(),
            base_seed=7,
            resampling_scheme=SCHEME_IID,
            iterations=200,
            minimum_observations=3,
        )
    )
    assert result.low_confidence is False
    assert result.low_confidence_label is None


def test_provenance_records_seed_scheme_params_and_window_bounds() -> None:
    bars = _bars()
    result = _unwrap(
        run_significance_gate(
            signals=bars,
            base_seed=42,
            resampling_scheme=SCHEME_STATIONARY,
            block_length=3,
            iterations=250,
            minimum_observations=4,
        )
    )
    provenance = result.provenance
    assert provenance.rng_family == RNG_FAMILY
    assert provenance.base_seed == 42
    assert provenance.seed_derivation_rule == SIGNIFICANCE_SEED_DERIVATION_RULE
    assert provenance.resampling_scheme == SCHEME_STATIONARY
    assert provenance.block_length == 3
    assert provenance.iterations == 250
    assert provenance.data_window_start_ns == bars[0].instant.value_ns
    assert provenance.data_window_end_ns == bars[-1].instant.value_ns
    assert result.rng_provenance()["base_seed"] == 42


def test_re_running_reproduces_the_null_distribution_bit_for_bit() -> None:
    bars = _bars()
    first = _unwrap(
        run_significance_gate(
            signals=bars,
            base_seed=13,
            resampling_scheme=SCHEME_BLOCK,
            block_length=3,
            iterations=400,
            minimum_observations=4,
        )
    )
    second = _unwrap(
        run_significance_gate(
            signals=bars,
            base_seed=13,
            resampling_scheme=SCHEME_BLOCK,
            block_length=3,
            iterations=400,
            minimum_observations=4,
        )
    )
    assert first.null.fingerprint == second.null.fingerprint
    assert first.fp1_identity() == second.fp1_identity()
    assert _unwrap(first.fingerprint()) == _unwrap(second.fingerprint())


def test_a_different_seed_changes_the_null_distribution() -> None:
    bars = _bars()
    one = _unwrap(
        run_significance_gate(
            signals=bars,
            base_seed=1,
            resampling_scheme=SCHEME_IID,
            iterations=400,
            minimum_observations=4,
        )
    )
    two = _unwrap(
        run_significance_gate(
            signals=bars,
            base_seed=2,
            resampling_scheme=SCHEME_IID,
            iterations=400,
            minimum_observations=4,
        )
    )
    assert one.null.fingerprint != two.null.fingerprint


# --- AC6: advisory-only discipline -------------------------------------------


def test_the_result_is_replay_robustness_and_never_edge() -> None:
    result = _unwrap(
        run_significance_gate(
            signals=_bars(), base_seed=7, resampling_scheme=SCHEME_IID, iterations=200
        )
    )
    assert result.world == SIGNIFICANCE_WORLD == "replay"
    assert result.claim_class == SIGNIFICANCE_CLAIM_CLASS == "robustness"
    assert result.makes_edge_claim is False
    assert result.mode == SIGNIFICANCE_MODE
    assert result.procedure == RULE_SIGNIFICANCE_PROCEDURE


def test_the_gate_never_auto_merges_or_gates_live_money() -> None:
    assert GATE_IS_ADVISORY is True
    assert GATE_AUTO_MERGES is False
    assert GATE_GATES_LIVE_MONEY is False
    assert ALPHA_THRESHOLDS_DEFERRED_TO == "GAP-0049"
    auto = refuse_gate_auto_merge("build-pipeline")
    assert auto.category is RefusalCategory.POLICY_REJECTION
    assert auto.context["alpha_thresholds_deferred_to"] == "GAP-0049"
    assert is_refusal(refuse_live_money_gate(RULE_SIGNIFICANCE_PROCEDURE))
    assert is_refusal(refuse_edge_claim(RULE_SIGNIFICANCE_PROCEDURE))


def test_a_live_result_world_is_refused() -> None:
    refusal = refuse_live_result_world("live")
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert refusal.context["forbidden"] == "live"


def test_the_procedure_is_a_versioned_ladder_rung() -> None:
    contract = _unwrap(procedure_contract(RULE_SIGNIFICANCE_PROCEDURE))
    assert contract.procedure == RULE_SIGNIFICANCE_PROCEDURE
    assert contract.contract_format_version >= 1
    assert qmb.run_significance_gate is run_significance_gate
    assert qmb.RULE_SIGNIFICANCE_PROCEDURE == "rule-significance"


def test_result_label_and_chart_series_are_data_only() -> None:
    result = _unwrap(
        run_significance_gate(
            signals=_bars(), base_seed=7, resampling_scheme=SCHEME_IID, iterations=200
        )
    )
    label = result.result_label()
    assert label["gate_is_advisory"] is True
    assert label["makes_edge_claim"] is False
    assert label["world"] == "replay"
    series = result.chart_series()
    assert series["name"] == "rule_significance_null_distribution"
    assert "values" in series


class _MintingHandler:
    """A handler that tries to mint an order — illegal during the signal-only pass."""

    def update_stream(self, s: str, o: object, f: Instant) -> Result[None]:
        del s, o, f
        return Ok(None)

    def scheduled_position_event(self, s: str, f: Instant) -> Result[None]:
        del s, f
        return Ok(None)

    def execute_resting(self, i: object, o: object, f: Instant) -> Result[bool]:
        del i, o, f
        return Ok(False)

    def update_closed_data(self, s: str, o: object, f: Instant) -> Result[None]:
        del s, o, f
        return Ok(None)

    def mint_intents(self, s: str, f: Instant) -> Result[object]:
        return Ok((_unwrap(RestingIntent.try_create(f"order-{f.value_ns}", s)),))
