"""Epic 22 · Story 22.4 — pre-build rule-significance gate (signal-only edge test).

Independent L3 acceptance tests T22-320..325: the signal-only pass over the B-2 loop
with orders disabled (permanently flat), look-ahead-safe next-bar log returns, the
zero-edge null and its one-tailed p-value statistic, the insufficient-data / unset-floor
discipline, the configurable resampling scheme, and the advisory-only firewall. Every
test names its counter-case.
"""

from __future__ import annotations

import math
from fractions import Fraction

from conftest import (
    assert_ct04_refusal,
    instant,
    instr,  # noqa: F401  (session fixture)
    is_ok,
    is_refusal,
    price,
    unwrap,
)

from qmf.core.fingerprint import World
from qmf.core.refusal import RefusalCategory

from qmb.robustness import (
    SignalBar,
    carve_return_statistic,
    guard_signal_pass,
    next_bar_log_returns,
    refuse_gate_auto_merge,
    refuse_live_result_world,
    refuse_signal_pass_act,
    run_signal_only_pass,
    run_significance_gate,
)


def _bars(instrument, closes, fired):
    return [
        unwrap(SignalBar.try_create(instant(i), price(closes[i], instrument), fired[i]), f"b{i}")
        for i in range(len(closes))
    ]


def _fixture_bars(instrument):
    # Fired bars carry higher forward returns than the unfired ones, so the rule-return
    # mean is clearly non-zero — a real signal to test the null against.
    closes = [100000, 108000, 96000, 99000, 130000, 118000, 121000, 150000, 140000, 165000]
    fired = [True, True, False, False, True, False, True, True, False, True]
    return _bars(instrument, closes, fired)


# --- T22-320 (signal-only pass; orders disabled; permanently flat; mint refused) P0 ---


def test_t22_320_signal_only_pass_stays_flat_and_mint_attempts_are_refused(instr):
    """The signal-only pass runs the loop flat; any entry/exit/command mint is refused.

    Counter-case: a fill during the pass (strategy not flat) would make the pass refuse;
    a mint attempt returning Ok would breach the orders-disabled lock.
    """
    bars = _fixture_bars(instr)
    passed = run_signal_only_pass(bars)
    assert is_ok(passed), f"the signal-only pass must stay flat and succeed, got {passed!r}"

    for action in ("entry", "exit", "command"):
        assert_ct04_refusal(
            refuse_signal_pass_act(action), RefusalCategory.POLICY_REJECTION, what=f"mint {action}"
        )
        assert_ct04_refusal(
            guard_signal_pass(action), RefusalCategory.POLICY_REJECTION, what=f"guard {action}"
        )


# --- T22-321 (R-001 / look-ahead: next-bar alignment; exact Price; float via AD-22) P0 ---


def test_t22_321_returns_are_next_bar_aligned_exact_scaled_rationals(instr):
    """Return t is ln(close[t+1]/close[t]); n-1 of them; stored as exact scaled rationals.

    Counter-case: a binary-float log-return would leave a power-of-two denominator not
    dividing 10**12; a mis-alignment would break the recomputed first return's value/sign.
    """
    closes = [100000, 110000, 90000, 95000, 130000]
    bars = _bars(instr, closes, [True] * 5)
    returns = unwrap(next_bar_log_returns(bars), "returns")
    assert len(returns) == len(bars) - 1  # last bar has no next-bar return

    # Independent recompute of the first return through the same named AD-22 carve-out.
    expected0 = unwrap(carve_return_statistic("next_bar_log_return", math.log(110000 / 100000)), "e0").magnitude
    assert returns[0] == expected0
    assert returns[0] > 0 and returns[1] < 0  # up then down, next-bar aligned

    ten_scale = 10**12
    for r in returns:
        assert ten_scale % r.denominator == 0, f"log-return {r} is not an exact scaled rational"


def test_t22_321_signal_bar_close_must_be_exact_price_and_last_bar_has_no_return(instr):
    """A signal-bar close must be an exact Price (float refused); the last bar has no next return.

    Counter-case (look-ahead): if only the last bar fired and it were still scored, an
    observation would exist; correct next-bar alignment drops it (no next return), so the
    gate refuses "fired on no bar with a next-bar return".
    """
    refused = SignalBar.try_create(instant(0), 1.2345, True)
    assert_ct04_refusal(refused, RefusalCategory.INVALID_INPUT, what="float close")

    # Only the final bar fires -> no fired bar has a next-bar return -> refusal, not a p-value.
    closes = [100000, 110000, 120000, 130000]
    only_last = _bars(instr, closes, [False, False, False, True])
    result = run_significance_gate(
        signals=only_last, base_seed=1, resampling_scheme="iid", iterations=16, minimum_observations=1
    )
    assert_ct04_refusal(result, RefusalCategory.INVALID_INPUT, what="only-last-bar fired")


# --- T22-322 (zero-edge null; statistic = one-tailed p-value) P1 -------------


def test_t22_322_p_value_is_fraction_of_null_means_at_or_above_observed(instr):
    """The reported statistic equals the fraction of null resample means >= the observed mean.

    Counter-case: a strict ``>`` or two-tailed statistic would differ from the independent
    recompute over the exposed null means.
    """
    bars = _fixture_bars(instr)
    result = unwrap(
        run_significance_gate(
            signals=bars, base_seed=11, resampling_scheme="iid", iterations=200, minimum_observations=2
        ),
        "gate",
    )
    observed_mean = result.observed_mean
    null_means = [v.as_fraction() for v in result.null.means.values]
    expected_p = Fraction(sum(1 for m in null_means if m >= observed_mean), len(null_means))
    assert result.p_value == expected_p
    assert Fraction(0) <= result.p_value <= Fraction(1)


def test_t22_322_null_is_recentred_to_zero(instr):
    """The zero-edge null is re-centred to zero: null means centre on 0, not the observed mean.

    Counter-case: a null built WITHOUT re-centring would centre its means on the observed
    (non-zero) mean; we assert |mean(null_means)| is far smaller than |observed_mean|.
    """
    bars = _fixture_bars(instr)
    result = unwrap(
        run_significance_gate(
            signals=bars, base_seed=5, resampling_scheme="iid", iterations=400, minimum_observations=2
        ),
        "gate",
    )
    null_means = [v.as_fraction() for v in result.null.means.values]
    grand_mean = sum(null_means, Fraction(0)) / len(null_means)
    observed_mean = result.observed_mean
    assert observed_mean != 0
    assert abs(grand_mean) < abs(observed_mean) / 2, (
        f"null means centre on {grand_mean} not near zero (observed {observed_mean}) — not re-centred"
    )


# --- T22-323 (insufficient data; unset floor low-confidence; reproducible null) P0 ---


def test_t22_323_insufficient_data_is_refused_never_a_fabricated_p_value(instr):
    """An observation count below the configured floor is a RETURNED refusal, not a p-value.

    Counter-case: returning a p-value below the floor would fabricate significance.
    """
    bars = _fixture_bars(instr)
    result = run_significance_gate(
        signals=bars, base_seed=11, resampling_scheme="iid", iterations=64, minimum_observations=999
    )
    assert_ct04_refusal(result, RefusalCategory.INVALID_INPUT, what="below minimum-observation floor")


def test_t22_323_unset_floor_yields_low_confidence_label_and_reproducible_null(instr):
    """An unset floor labels the result low-confidence; the null reproduces bit-for-bit.

    Counter-case: an unset floor presenting a hard number with no low-confidence flag; or
    a non-reproducing null distribution.
    """
    bars = _fixture_bars(instr)
    first = unwrap(
        run_significance_gate(signals=bars, base_seed=11, resampling_scheme="iid", iterations=100),
        "first",
    )
    assert first.low_confidence is True
    assert first.low_confidence_label == "minimum-observation-floor-unset"

    second = unwrap(
        run_significance_gate(signals=bars, base_seed=11, resampling_scheme="iid", iterations=100),
        "second",
    )
    assert first.null.fingerprint.value == second.null.fingerprint.value
    assert unwrap(first.fingerprint(), "fp1").value == unwrap(second.fingerprint(), "fp2").value

    prov = first.provenance
    assert prov.iterations == 100
    assert prov.resampling_scheme == "iid"
    assert prov.data_window_start_ns == bars[0].instant.value_ns
    assert prov.data_window_end_ns == bars[-1].instant.value_ns


# --- T22-324 (configurable scheme/iterations/block/floor; no invented default) P1 ---


def test_t22_324_scheme_and_iterations_have_no_ratified_value(instr):
    """The scheme, iteration count, and block length are required — unset each refuses.

    Counter-case: a run succeeding with a defaulted scheme or iteration count.
    """
    bars = _fixture_bars(instr)
    no_scheme = run_significance_gate(signals=bars, base_seed=1, iterations=32, minimum_observations=2)
    assert_ct04_refusal(no_scheme, RefusalCategory.INVALID_INPUT, what="unset resampling scheme")

    no_iters = run_significance_gate(
        signals=bars, base_seed=1, resampling_scheme="iid", minimum_observations=2
    )
    assert_ct04_refusal(no_iters, RefusalCategory.INVALID_INPUT, what="unset iteration count")

    block_no_len = run_significance_gate(
        signals=bars, base_seed=1, resampling_scheme="block", iterations=32, minimum_observations=2
    )
    assert_ct04_refusal(block_no_len, RefusalCategory.INVALID_INPUT, what="block scheme without block length")


def test_t22_324_each_scheme_is_accepted_with_its_parameters(instr):
    """Each of iid / block / stationary is accepted with its required parameters.

    Counter-case: a supported scheme rejected, or an off-vocabulary scheme accepted.
    """
    bars = _fixture_bars(instr)
    iid = run_significance_gate(
        signals=bars, base_seed=1, resampling_scheme="iid", iterations=32, minimum_observations=2
    )
    assert is_ok(iid)
    for scheme in ("block", "stationary"):
        result = run_significance_gate(
            signals=bars,
            base_seed=1,
            resampling_scheme=scheme,
            block_length=3,
            iterations=32,
            minimum_observations=2,
        )
        assert is_ok(result), f"{scheme} scheme refused: {result!r}"
    bad = run_significance_gate(
        signals=bars, base_seed=1, resampling_scheme="bootstrap-9000", iterations=32, minimum_observations=2
    )
    assert_ct04_refusal(bad, RefusalCategory.INVALID_INPUT, what="off-vocabulary scheme")


# --- T22-325 (advisory: world never live; robustness never edge; never auto-merges) P0 ---


def test_t22_325_result_is_advisory_replay_world_never_live(instr):
    """The result world is replay (never live) and the claim class is robustness.

    Counter-case: a live world, or an edge claim, on the gate result.
    """
    bars = _fixture_bars(instr)
    result = unwrap(
        run_significance_gate(
            signals=bars, base_seed=11, resampling_scheme="iid", iterations=64, minimum_observations=2
        ),
        "gate",
    )
    assert result.world == World.REPLAY.value
    assert result.world != World.LIVE.value
    assert result.claim_class == "robustness"
    label = result.result_label()
    assert label["world"] == World.REPLAY.value
    assert label["claim_class"] == "robustness"


def test_t22_325_auto_merge_and_live_world_are_refused():
    """Auto-merging on the gate, or a live result world, is a RETURNED policy rejection.

    Counter-case: either returning Ok would let the advisory gate gate live money / merges.
    """
    assert_ct04_refusal(
        refuse_gate_auto_merge("ci-pipeline"), RefusalCategory.POLICY_REJECTION, what="auto-merge"
    )
    assert_ct04_refusal(
        refuse_live_result_world("live"), RefusalCategory.POLICY_REJECTION, what="live result world"
    )
