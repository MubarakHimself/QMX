"""Reference usage — the pre-build rule-significance gate, signal-only edge test (Story 22.4).

Executable::

    python qmb/examples/significance_gate_usage.py

Shows what the third B-14 ladder rung pins down:

1. The gate performs a signal-only pass over the B-2 event-slice loop with orders
   disabled — the same loop, the same pinned sub-phase order, trading locked as in
   warm-up — so the strategy stays permanently flat and the raw entry signal is
   isolated from exit and position-management logic. Minting an entry, an exit, or a
   command during the pass is a typed policy rejection.
2. Look-ahead safety: the signal at bar t is scored against the NEXT bar's log
   return, the first return not knowable at signal time. Close prices are exact Price
   integers that cross into the return-space float carve-out only via the named AD-22
   conversion from Story 22.1.
3. The zero-edge null detrends the returns by their in-sample mean and re-centres the
   rule-return series to zero before resampling; the reported statistic is the
   empirical one-tailed p-value = the fraction of null resamples at or above observed.
4. The resampling scheme (iid / block / stationary), block length, iteration count,
   and minimum-observation floor are UI-editable configurables with no ratified value;
   the module ships no invented default, and an unset required input is a typed refusal.
5. Below the configured floor the gate returns a typed refusal, never a fabricated
   p-value; with the floor unset it emits a low-confidence warning label. Seed
   provenance is recorded and re-running reproduces the null distribution bit-for-bit.
6. The gate is advisory: the result world is replay or simulated, never live, and the
   claim class is robustness, never edge; it never auto-merges and never gates live
   money, and the pass/fail alpha thresholds stay deferred to GAP-0049.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.doors import api
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

# A price path that steps up after every odd bar; the rule under test fires on those
# even bars, right before each up-move — a real edge-looking pattern.
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


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _price(minor: int) -> Price:
    return _unwrap(Price.try_create(minor, _INSTRUMENT, 5), "price")


def _bars() -> tuple[api.SignalBar, ...]:
    return tuple(
        _unwrap(
            api.SignalBar.try_create(_instant(_BASE_NS + index * _DAY_NS), _price(close), fired),
            "signal bar",
        )
        for index, (close, fired) in enumerate(zip(_CLOSES, _FIRED, strict=True))
    )


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
        return Ok((_unwrap(RestingIntent.try_create(f"order-{f.value_ns}", s), "intent"),))


def signal_only_pass_isolates_the_raw_signal() -> None:
    """AC1 — the pass runs the B-2 loop, orders disabled, trading locked, flat."""
    bars = _bars()
    confirmed = _unwrap(api.run_signal_only_pass(bars), "signal-only pass")
    assert confirmed == bars
    assert api.SIGNAL_PASS_ORDERS_ENABLED is False
    assert api.SIGNAL_PASS_TRADING_LOCKED is True
    assert api.SIGNAL_PASS_STRATEGY_STAYS_FLAT is True
    # The very same event-slice loop with a handler that mints an order refuses: any
    # attempt to act during the locked pass is a policy rejection (B-2).
    slices = tuple(
        (_unwrap(SliceObservation.try_create("signal-pass", bar.instant, True), "obs"),)
        for bar in bars
    )
    minted = run(
        slices=slices, stream_set=("signal-pass",), handler=_MintingHandler(), embargo=len(bars)
    )
    assert is_refusal(minted)
    assert minted.category is RefusalCategory.POLICY_REJECTION
    direct = api.refuse_signal_pass_act("enter")
    assert direct.category is RefusalCategory.POLICY_REJECTION
    print("signal-only pass over the B-2 loop with orders disabled; trading locked, strategy flat")
    print("minting an entry, an exit, or a command during the pass is a policy rejection")


def next_bar_return_alignment_is_look_ahead_safe() -> None:
    """AC2 — signal at bar t scored on the next bar's log return via the carve-out."""
    bars = _bars()
    returns = _unwrap(api.next_bar_log_returns(bars), "returns")
    # One return per bar except the last (no next bar), so no future/forming leak.
    assert len(returns) == len(bars) - 1
    assert api.RETURN_ALIGNMENT == "signal-at-t-scored-on-next-bar-return"
    assert api.RETURN_BASIS == "log-returns"
    # A raw binary-float close is refused: closes are exact Price integers.
    assert is_refusal(api.SignalBar.try_create(_instant(_BASE_NS), 1.5, True))
    print("signal at bar t scored on the next bar's log return; closes cross the AD-22 carve-out")


def zero_edge_null_and_one_tailed_p_value() -> None:
    """AC3 — detrended zero-edge null; empirical one-tailed p-value."""
    bars = _bars()
    result = _unwrap(
        api.run_significance_gate(
            signals=bars,
            base_seed=7,
            resampling_scheme=api.SCHEME_IID,
            iterations=1000,
            minimum_observations=4,
        ),
        "gate",
    )
    assert api.NULL_HYPOTHESIS == "E[return]=0"
    assert api.NULL_DETRENDED_BY == "in-sample-mean"
    # The rule fires right before every up-move: its excess mean beats every null
    # resample, so the one-tailed p-value is 0 (a strong signal).
    assert result.p_value == 0
    assert result.emits_verdict is False
    # A rule that fires on every bar has zero excess over the market drift: p near 0.5.
    flat = tuple(
        _unwrap(api.SignalBar.try_create(bar.instant, bar.close, True), "bar") for bar in bars
    )
    flat_result = _unwrap(
        api.run_significance_gate(
            signals=flat,
            base_seed=7,
            resampling_scheme=api.SCHEME_IID,
            iterations=1000,
            minimum_observations=4,
        ),
        "flat gate",
    )
    assert 0 < flat_result.p_value < 1
    print(
        "detrended zero-edge null; one-tailed p-value = fraction of null resamples "
        "at/above observed"
    )


def scheme_and_parameters_are_configurable() -> None:
    """AC4 — scheme / block length / iterations / floor configurable, no baked default."""
    bars = _bars()
    assert api.RESAMPLING_SCHEMES == (api.SCHEME_IID, api.SCHEME_BLOCK, api.SCHEME_STATIONARY)
    for scheme in (api.SCHEME_BLOCK, api.SCHEME_STATIONARY):
        built = _unwrap(
            api.run_significance_gate(
                signals=bars,
                base_seed=7,
                resampling_scheme=scheme,
                block_length=3,
                iterations=200,
                minimum_observations=4,
            ),
            "scheme run",
        )
        assert built.provenance.resampling_scheme == scheme
        assert built.provenance.block_length == 3
    # No invented default: a block scheme with no block length, an unset scheme, and
    # unset iterations are each a typed refusal.
    assert is_refusal(
        api.run_significance_gate(
            signals=bars, base_seed=7, resampling_scheme=api.SCHEME_BLOCK, iterations=200
        )
    )
    assert is_refusal(api.run_significance_gate(signals=bars, base_seed=7, iterations=200))
    assert is_refusal(
        api.run_significance_gate(signals=bars, base_seed=7, resampling_scheme=api.SCHEME_IID)
    )
    print("resampling scheme is iid, block, or stationary with a configurable block length")
    print("iterations and the minimum-observation floor are configurable with no ratified value")


def insufficient_data_and_reproducibility() -> None:
    """AC5 — floor discipline, low-confidence label, seed provenance, reproducibility."""
    bars = _bars()
    # Below the configured floor: a typed refusal, never a fabricated p-value.
    below = api.run_significance_gate(
        signals=bars,
        base_seed=7,
        resampling_scheme=api.SCHEME_IID,
        iterations=200,
        minimum_observations=100,
    )
    assert is_refusal(below)
    assert below.category is RefusalCategory.INVALID_INPUT
    print("below the configured floor is a typed refusal, never a fabricated p-value")
    # Floor unset: a low-confidence warning label instead of a hard number.
    unset = _unwrap(
        api.run_significance_gate(
            signals=bars, base_seed=7, resampling_scheme=api.SCHEME_IID, iterations=200
        ),
        "unset floor",
    )
    assert unset.low_confidence is True
    assert unset.low_confidence_label == api.LOW_CONFIDENCE_FLOOR_UNSET_LABEL
    print("an unset minimum-observation floor emits a low-confidence warning label")
    # Seed provenance recorded; re-running reproduces the null distribution bit-for-bit.
    assert unset.provenance.base_seed == 7
    assert unset.provenance.seed_derivation_rule == api.SIGNIFICANCE_SEED_DERIVATION_RULE
    assert unset.provenance.data_window_start_ns == bars[0].instant.value_ns
    assert unset.provenance.data_window_end_ns == bars[-1].instant.value_ns
    again = _unwrap(
        api.run_significance_gate(
            signals=bars, base_seed=7, resampling_scheme=api.SCHEME_IID, iterations=200
        ),
        "re-run",
    )
    assert unset.null.fingerprint == again.null.fingerprint
    assert _unwrap(unset.fingerprint(), "fp") == _unwrap(again.fingerprint(), "fp2")
    print("seed provenance recorded; re-running reproduces the null distribution bit-for-bit")


def the_gate_is_advisory_only() -> None:
    """AC6 — replay/simulated never live, robustness never edge, never auto-merges."""
    bars = _bars()
    result = _unwrap(
        api.run_significance_gate(
            signals=bars, base_seed=7, resampling_scheme=api.SCHEME_IID, iterations=200
        ),
        "gate",
    )
    assert result.world == "replay"
    assert result.claim_class == "robustness"
    assert result.makes_edge_claim is False
    assert api.GATE_IS_ADVISORY is True
    assert api.GATE_AUTO_MERGES is False
    assert api.GATE_GATES_LIVE_MONEY is False
    assert api.ALPHA_THRESHOLDS_DEFERRED_TO == "GAP-0049"
    assert is_refusal(api.refuse_live_result_world("live"))
    assert is_refusal(api.refuse_gate_auto_merge("build-pipeline"))
    assert is_refusal(api.refuse_live_money_gate(api.RULE_SIGNIFICANCE_PROCEDURE))
    assert is_refusal(api.refuse_edge_claim(api.RULE_SIGNIFICANCE_PROCEDURE))
    print(
        "advisory: world replay/simulated never live, robustness never edge; never auto-merges, "
        "never gates live money; alpha thresholds deferred to GAP-0049"
    )


def main() -> None:
    assert qmb.run_significance_gate is api.run_significance_gate
    assert qmb.RULE_SIGNIFICANCE_PROCEDURE == "rule-significance"
    signal_only_pass_isolates_the_raw_signal()
    next_bar_return_alignment_is_look_ahead_safe()
    zero_edge_null_and_one_tailed_p_value()
    scheme_and_parameters_are_configurable()
    insufficient_data_and_reproducibility()
    the_gate_is_advisory_only()
    print("rule significance gate ok")


if __name__ == "__main__":
    main()
