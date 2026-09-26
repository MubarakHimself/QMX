"""Reference usage — Monte Carlo trade-shuffle, sequence-risk mode (Story 22.2).

Executable::

    python qmb/examples/trade_shuffle_usage.py

Shows what the first B-14 ladder rung pins down:

1. It re-orders a completed replay run's realised trades N times and re-accumulates
   the equity path in exact-integer money — path-dependent metrics (max drawdown)
   move while order-invariant ones (net profit) do not. It mints no synthetic market
   series, so the run stays world=replay (procedure-ephemeral).
2. Each scenario's seed is base_seed + scenario_index; the result records the RNG
   family, base seed, seed rule, scenario count, and data-window UTC-ns bounds, and
   re-running the same inputs reproduces the result fingerprint bit-for-bit.
3. Per selected metric the distribution is summarised with the Story 22.1 primitive —
   percentile ranks, confidence bands, and the direction-aware empirical percentile
   rank of the original result (lower-is-better for drawdown) — as chart series data,
   never images, and with no pass/fail verdict.
4. The scenario count is a UI-editable configurable with no ratified value; the
   MC-1000 baseline is not baked.
5. Scenarios fan out under the orchestrator's min(cpu, memory) governor with
   enqueue-on-full; each governed scenario is role=replicate, cancellable, and never
   writes a bar verdict.
"""

from __future__ import annotations

from fractions import Fraction
from typing import TypeVar

from qmb.doors import api
from qmf.core.chrono import Instant, Interval
from qmf.core.exact import Money
from qmf.core.refusal import Result, is_ok, is_refusal

T = TypeVar("T")

_DAY_NS = 86_400_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _money(minor: int) -> Money:
    return _unwrap(Money.try_create(minor, "USD", 2), "money")


def _instant(ns: int) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def main() -> None:
    # A completed replay run's realised-trade record (its CT-29 ClosedTrade stream),
    # closing on distinct daily bars, with mixed wins and losses.
    pnls = (500, -300, 800, -1000, 200, -150, 400, -600)
    trades = [
        _unwrap(
            api.ClosedTrade.try_create(
                _money(pnl),
                _money(10),
                api.TradeSide.LONG if pnl >= 0 else api.TradeSide.SHORT,
                _instant((index + 1) * _DAY_NS),
            ),
            "closed trade",
        )
        for index, pnl in enumerate(pnls)
    ]
    start = _money(100_000)
    window = _unwrap(Interval.try_create(_instant(0), _instant(9 * _DAY_NS)), "window")

    # 1. Re-order the realised trades and re-accumulate the equity path (exact money).
    result = _unwrap(
        api.run_trade_shuffle(
            trades=trades,
            starting_capital=start,
            period=window,
            base_seed=42,
            metrics=["max_drawdown", "net_profit", "sharpe_ratio", "losing_streak"],
            config={api.SCENARIO_COUNT_KEY: 500},
            band_probabilities=[Fraction(1, 20), Fraction(19, 20)],
        ),
        "trade-shuffle result",
    )
    assert result.world == "replay"
    assert result.procedure == api.TRADE_SHUFFLE_PROCEDURE
    assert result.mints_synthetic_series is False
    print(
        "re-orders realised trades and re-accumulates equity in exact integer money; "
        "world stays replay:",
        result.world,
    )

    net = result.metric_named("net_profit")
    drawdown = result.metric_named("max_drawdown")
    assert net is not None and drawdown is not None
    # Net profit is the invariant sum of the same P&Ls; drawdown depends on order.
    assert net.summary.minimum == net.summary.maximum
    assert drawdown.summary.minimum != drawdown.summary.maximum
    print(
        "net profit is order-invariant; max drawdown is sequence-dependent:",
        f"dd range [{drawdown.summary.minimum}..{drawdown.summary.maximum}]",
    )

    # 2. Deterministic per-scenario seeding + a full RNG/data-window provenance record.
    assert _unwrap(api.scenario_seed(42, 5), "scenario seed") == 47
    provenance = result.provenance
    assert provenance.rng_family == api.RNG_FAMILY
    assert provenance.seed_derivation_rule == "base_seed + scenario_index"
    assert provenance.scenario_count == 500
    assert provenance.data_window_start_ns == 0
    assert provenance.data_window_end_ns == 9 * _DAY_NS
    print(
        "scenario seed is base_seed + scenario_index; result records RNG family, base seed, "
        "rule, count, data window:",
        f"{provenance.rng_family} window=[{provenance.data_window_start_ns}"
        f"..{provenance.data_window_end_ns}]",
    )

    # Reproducibility: identical inputs reproduce the result fingerprint bit-for-bit.
    again = _unwrap(
        api.run_trade_shuffle(
            trades=trades,
            starting_capital=start,
            period=window,
            base_seed=42,
            metrics=["max_drawdown", "net_profit", "sharpe_ratio", "losing_streak"],
            config={api.SCENARIO_COUNT_KEY: 500},
            band_probabilities=[Fraction(1, 20), Fraction(19, 20)],
        ),
        "second trade-shuffle result",
    )
    first_fp = _unwrap(result.fingerprint(), "first fingerprint")
    second_fp = _unwrap(again.fingerprint(), "second fingerprint")
    assert first_fp.value == second_fp.value
    print("re-running the same inputs reproduces the result fingerprint bit-for-bit")

    # 3. Direction-aware summary as chart series data, never images; no verdict.
    assert api.metric_direction("max_drawdown") == api.DIRECTION_LOWER_IS_BETTER
    series = result.chart_series()
    assert len(series) == len(result.metrics)
    assert all("values" in item and "png" not in item for item in series)
    assert result.emits_verdict is False
    assert is_refusal(api.refuse_pass_fail_verdict("pass"))
    print(
        "distribution summary as chart series data, never images; direction-aware for drawdown "
        "(lower is better):",
        f"observed favorable_rank={drawdown.observed_favorable_rank} "
        f"p_value={drawdown.summary.p_value}",
    )
    print(
        "no pass/fail verdict; thresholds and the MC-1000 battery stay deferred:",
        api.SHUFFLE_VERDICT_DEFERRED_TO,
    )

    # 4. Scenario count is a UI-editable configurable with no ratified value.
    assert api.MC_1000_IS_BAKED_DEFAULT is False
    assert is_refusal(
        api.run_trade_shuffle(
            trades=trades,
            starting_capital=start,
            period=window,
            base_seed=1,
            metrics=["net_profit"],
        )
    )
    print(
        "scenario count is a UI-editable configurable with no ratified value; "
        "MC-1000 is not baked:",
        api.SCENARIO_COUNT_KEY,
    )

    # 5. Fan-out under the min(cpu, memory) governor with enqueue-on-full; replicate,
    # cancellable, never a bar verdict.
    scenarios = _unwrap(api.shuffle_scenarios(42, 3, run_root="fp1:sha256:parent"), "scenarios")
    assert all(scenario.role == api.SCENARIO_RUN_ROLE for scenario in scenarios)
    requests = _unwrap(
        api.governed_scenario_requests(scenarios, projected_peak_memory=4, cpu_cost=1),
        "governed requests",
    )
    governor = _unwrap(
        api.ResourceGovernor.try_create(cpu_budget=2, memory_budget=8, on_full="enqueue"),
        "governor",
    )
    decisions = [_unwrap(governor.submit(request), "admission").decision for request in requests]
    assert decisions == [api.DECISION_ADMITTED, api.DECISION_ADMITTED, api.DECISION_QUEUED]
    assert is_refusal(api.refuse_scenario_bar_verdict("bar-pass"))
    print(
        "scenarios fan out under the min(cpu, memory) governor with enqueue-on-full; each is "
        "role=replicate, cancellable, never a bar verdict:",
        decisions,
    )

    print("no synthetic market series is minted; procedure-ephemeral")
    print("trade shuffle ok")


if __name__ == "__main__":
    main()
