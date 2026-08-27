"""Epic 22 · Story 22.3 — Monte Carlo candle-perturbation (alternate-history mode).

Independent L3 acceptance tests T22-315..319: the moving-block bootstrap of
exact-integer OHLC deltas (strictly-positive, high/low-bounded, scenario 0 = true
history), the procedure-ephemeral world=replay provenance, the persistence refusal
seam, reproducibility, and the data-only robustness summary. Every test names its
counter-case.
"""

from __future__ import annotations

from conftest import (
    assert_ct04_refusal,
    instant,
    is_exact_quantity,
    is_ok,
    is_refusal,
    unwrap,
)

from qmf.core.fingerprint import World
from qmf.core.refusal import RefusalCategory

from qmb.config.compiler import CLOCK_REPLAY, CLOCK_SIMULATED
from qmb.robustness import (
    RESAMPLING_SCHEME,
    Candle,
    ohlc_deltas,
    perturbation_persistence,
    refuse_perturbation_bar_verdict,
    refuse_persisted_synthetic_series,
    refuse_replay_clock_on_synthetic_persisted,
    run_candle_perturbation,
    summarize_perturbation_objective,
)
from qmb.robustness import DIRECTION_HIGHER_IS_BETTER


def _candles(n: int = 8):
    return [
        unwrap(Candle.try_create(instant(i), 100 + i, 112 + i, 88 + i, 105 + i), f"c{i}")
        for i in range(n)
    ]


def _run(**overrides):
    kwargs = dict(candles=_candles(), base_seed=3, block_length=3, scenario_count=6)
    kwargs.update(overrides)
    return run_candle_perturbation(**kwargs)


# --- T22-315 (R-001: exact-integer OHLC bootstrap; strictly positive; scenario 0) P0 ---


def test_t22_315_ohlc_deltas_cumulative_sum_reconstructs_the_exact_series():
    """OHLC deltas cumulative-summed onto the seed price reconstruct the exact input.

    Counter-case: any float in the delta/cumsum path would break the exact-integer
    round-trip; a wrong anchoring would misplace a price.
    """
    candles = _candles(6)
    seed_price = candles[0].open
    deltas = unwrap(ohlc_deltas(candles, seed_price=seed_price), "deltas")
    anchor = seed_price
    reconstructed = []
    for delta in deltas:
        o = anchor + delta.open_delta
        h = anchor + delta.high_delta
        low = anchor + delta.low_delta
        c = anchor + delta.close_delta
        assert all(isinstance(x, int) for x in (o, h, low, c))
        reconstructed.append((o, h, low, c))
        anchor = c
    assert reconstructed == [(c.open, c.high, c.low, c.close) for c in candles]


def test_t22_315_scenario_zero_is_true_history_and_every_scenario_is_valid_positive():
    """Scenario 0 is the true history verbatim; every scenario is strictly-positive and bounded.

    Counter-case: scenario 0 differing from the input, any non-positive price, or a
    high/low bound violation, would break the alternate-history invariant.
    """
    candles = _candles(8)
    result = unwrap(_run(candles=candles, scenario_count=6), "perturbation")
    true_history = result.true_history()
    assert [c.fp1_identity() for c in true_history.candles] == [c.fp1_identity() for c in candles]

    for series in result.series:
        for c in series.candles:
            assert c.low > 0 and c.open > 0 and c.high > 0 and c.close > 0
            assert c.high >= max(c.open, c.close) and c.high >= c.low
            assert c.low <= min(c.open, c.close)


def test_t22_315_block_length_has_no_ratified_value():
    """The block length is a required configurable — unset it is a RETURNED refusal.

    Counter-case: a run succeeding with neither config nor an explicit block length
    proves a baked default.
    """
    refused = run_candle_perturbation(candles=_candles(), base_seed=3, scenario_count=6)
    assert_ct04_refusal(refused, RefusalCategory.INVALID_INPUT, what="perturbation with no block length")


# --- T22-316 (procedure-ephemeral: world=replay; procedure+seed in label; robustness) P0 ---


def test_t22_316_perturbation_stays_world_replay_with_robustness_claim():
    """The minted synthetic series is never persisted: world stays replay, claim robustness.

    Counter-case: a world other than replay, a claim other than robustness, or a label
    missing the procedure/seed, would breach B-7.
    """
    result = unwrap(_run(base_seed=9), "perturbation")
    assert result.world == World.REPLAY.value
    assert result.claim_class == "robustness"
    label = result.result_label()
    assert label["world"] == World.REPLAY.value
    assert label["procedure"] == result.procedure
    assert label["base_seed"] == 9
    assert label["provenance_kind"] == "procedure-ephemeral"
    # The synthetic series exists (it is minted) yet is not persisted.
    assert len(result.series) == 6


# --- T22-317 (persistence refusal seam) P0 (SC-06) ---------------------------


def test_t22_317_ephemeral_ok_persist_simulated_policy_persist_replay_invalid():
    """The persistence seam: ephemeral OK; persist+simulated policy-refused; persist+replay invalid.

    Counter-case: persisting a synthetic series returning Ok (governed-evidence leak),
    or a replay clock bound to synthetic-tainted persisted data returning Ok.
    """
    ephemeral = perturbation_persistence(persist=False, clock=CLOCK_REPLAY)
    assert is_ok(ephemeral)
    assert unwrap(ephemeral, "ephemeral").world == World.REPLAY.value

    persisted = perturbation_persistence(persist=True, clock=CLOCK_SIMULATED)
    refusal = assert_ct04_refusal(persisted, RefusalCategory.POLICY_REJECTION, what="persist synthetic series")
    assert dict(refusal.context).get("world") == World.SIMULATED.value

    replay_on_synthetic = perturbation_persistence(persist=True, clock=CLOCK_REPLAY)
    assert_ct04_refusal(
        replay_on_synthetic, RefusalCategory.INVALID_INPUT, what="replay clock on synthetic-persisted"
    )


def test_t22_317_named_refusal_builders_return_the_right_categories():
    """The two named persistence refusals return the correct CT-04 categories, not raised.

    Counter-case: either raising, or returning the wrong category, would break the seam.
    """
    assert_ct04_refusal(
        refuse_persisted_synthetic_series("run-x"),
        RefusalCategory.POLICY_REJECTION,
        what="refuse_persisted_synthetic_series",
    )
    assert_ct04_refusal(
        refuse_replay_clock_on_synthetic_persisted("replay"),
        RefusalCategory.INVALID_INPUT,
        what="refuse_replay_clock_on_synthetic_persisted",
    )


# --- T22-318 (reproducibility; provenance records scheme/block/window) P1 -----


def test_t22_318_perturbation_reproduces_and_records_full_provenance():
    """A re-run reproduces the fingerprint; provenance records scheme/block/window bounds.

    Counter-case: a differing re-run fingerprint, or provenance whose window bounds do
    not equal the candle timeline, or whose resampling scheme is not the moving-block
    bootstrap.
    """
    candles = _candles(8)
    first = unwrap(_run(candles=candles), "first")
    second = unwrap(_run(candles=candles), "second")
    assert unwrap(first.fingerprint(), "fp1").value == unwrap(second.fingerprint(), "fp2").value

    prov = first.provenance
    assert prov.resampling_scheme == RESAMPLING_SCHEME == "moving-block-bootstrap"
    assert prov.block_length == 3
    assert prov.scenario_count == 6
    assert prov.seed_derivation_rule == "base_seed + scenario_index"
    assert prov.data_window_start_ns == candles[0].instant.value_ns
    assert prov.data_window_end_ns == candles[-1].instant.value_ns


# --- T22-319 (summary as data, no verdict; robustness never edge; no money gate) P1 ---


def test_t22_319_objective_summary_is_data_never_verdict_and_bar_verdict_refused():
    """The objective distribution is data (never a verdict); a bar verdict read is refused.

    Counter-case: an emitted verdict flag, an image payload, or a bar-verdict read that
    returns Ok, would breach L20 / the data-only rule.
    """
    candles = _candles(8)
    # One exact-integer objective per scenario, index-aligned (element 0 = true history).
    objectives = [10 + i for i in range(6)]
    result = unwrap(
        run_candle_perturbation(
            candles=candles,
            base_seed=3,
            block_length=3,
            scenario_count=6,
            objective_identity="sharpe_ratio",
            scenario_objectives=objectives,
            objective_direction=DIRECTION_HIGHER_IS_BETTER,
        ),
        "perturbation+objective",
    )
    assert result.objective is not None
    assert result.objective.emits_verdict is False
    chart = result.objective.chart_series()
    keys = {str(k).lower() for k in chart}
    assert "values" in keys
    assert not any(any(b in k for b in ("image", "png", "svg", "base64")) for k in keys)

    assert_ct04_refusal(
        refuse_perturbation_bar_verdict("book_pass"),
        RefusalCategory.POLICY_REJECTION,
        what="perturbation bar verdict",
    )


def test_t22_319_standalone_objective_summary_returns_direction_aware_data():
    """The standalone objective summariser returns direction-aware pure data, no verdict.

    Counter-case: a verdict field, or a direction-blind p-value.
    """
    summary = unwrap(
        summarize_perturbation_objective(
            objective_identity="sharpe_ratio",
            observed=20,
            scenario_objectives=[10, 12, 14, 30],
            direction=DIRECTION_HIGHER_IS_BETTER,
        ),
        "objective",
    )
    assert summary.emits_verdict is False
    assert is_exact_quantity(summary.distribution.values[0])
