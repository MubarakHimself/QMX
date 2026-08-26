"""Reference usage — Monte Carlo candle-perturbation, alternate-history mode (Story 22.3).

Executable::

    python qmb/examples/candle_perturbation_usage.py

Shows what the second B-14 ladder rung pins down:

1. It moving-block-bootstraps exact-integer OHLC delta tuples of a replay run's real
   candles, cumulative-sums them onto the seed price in exact money, and always
   rebuilds a valid strictly-positive OHLC series (high/low bounds enforced). Scenario
   0 is the true history. It DOES mint a synthetic series, but never persists it, so
   the run stays world=replay (procedure-ephemeral).
2. Persistence law: procedure-ephemeral stays world=replay with a robustness claim; a
   config that persists the synthetic series is a world=simulated policy rejection
   gated behind GAP-0048; a replay clock on synthetic-tainted persisted data is a
   typed invalid input (B-2/B-7 wins).
3. Each scenario's seed is base_seed + scenario_index; the result records the RNG
   family, seed rule, block length, scenario count, resampling scheme, and data-window
   UTC-ns bounds, and re-running the same inputs reproduces the fingerprint bit-for-bit.
4. Scenarios fan out under the orchestrator's min(cpu, memory) governor with
   enqueue-on-full; each governed scenario is role=replicate and never a bar verdict.
5. The objective is summarised across the alternate histories — percentiles, bands,
   and a direction-aware empirical percentile rank — as chart series data, never a
   verdict. The claim class is robustness (alternate-history), never edge.
"""

from __future__ import annotations

from fractions import Fraction
from typing import TypeVar

from qmb.doors import api
from qmf.core.chrono import Instant
from qmf.core.exact import Money
from qmf.core.refusal import Result, is_ok, is_refusal

T = TypeVar("T")

_DAY_NS = 86_400_000_000_000

_RAW = (
    (100, 105, 98, 103),
    (103, 108, 101, 107),
    (107, 110, 104, 106),
    (106, 111, 105, 109),
    (109, 112, 107, 110),
    (110, 115, 108, 113),
    (113, 116, 111, 112),
    (112, 114, 109, 111),
)


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _money(minor: int) -> Money:
    return _unwrap(Money.try_create(minor, "USD", 2), "money")


def _instant(ns: int) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def main() -> None:
    # A completed replay run's real historical OHLC candle series.
    candles = [
        _unwrap(
            api.Candle.try_create(_instant((index + 1) * _DAY_NS), o, h, low, c),
            "candle",
        )
        for index, (o, h, low, c) in enumerate(_RAW)
    ]

    # 1. Moving-block bootstrap onto the seed price; scenario 0 is the true history.
    result = _unwrap(
        api.run_candle_perturbation(
            candles=candles,
            base_seed=42,
            config={
                api.BLOCK_LENGTH_KEY: 3,
                api.PERTURBATION_SCENARIO_COUNT_KEY: 200,
            },
        ),
        "candle-perturbation result",
    )
    assert result.world == "replay"
    assert result.procedure == api.CANDLE_PERTURBATION_PROCEDURE
    assert result.mints_synthetic_series is True
    assert result.persists_synthetic_series is False
    true = result.true_history()
    assert tuple((c.open, c.high, c.low, c.close) for c in true.candles) == _RAW
    print(
        "moving-block bootstraps OHLC deltas onto the seed price; scenario 0 is the true "
        "history; world stays replay:",
        result.world,
    )
    for series in result.series:
        for candle in series.candles:
            assert candle.open > 0 and candle.high > 0 and candle.low > 0 and candle.close > 0
            assert candle.high >= max(candle.open, candle.close) >= candle.low
    print(
        "every scenario rebuilds a valid strictly-positive OHLC series (high/low bounds "
        "enforced):",
        f"{len(result.series)} scenarios",
    )

    # 2. Persistence law (B-7, GAP-0048).
    ephemeral = _unwrap(
        api.perturbation_persistence(persist=False, clock="replay"),
        "ephemeral persistence",
    )
    assert ephemeral.world == "replay" and ephemeral.claim_class == "robustness"
    persisted = api.perturbation_persistence(persist=True, clock="simulated")
    assert is_refusal(persisted)
    replay_synth = api.perturbation_persistence(persist=True, clock="replay")
    assert is_refusal(replay_synth)
    print(
        "procedure-ephemeral -> world=replay robustness; persisting -> world=simulated policy "
        "rejection; replay clock on synthetic-tainted persisted data -> invalid input:",
        f"{ephemeral.world} / {persisted.category.value} / {replay_synth.category.value}",
    )

    # 3. Deterministic seeding, full provenance, and reproducibility.
    provenance = result.provenance
    assert provenance.rng_family == api.RNG_FAMILY
    assert provenance.resampling_scheme == api.RESAMPLING_SCHEME == "moving-block-bootstrap"
    assert provenance.block_length == 3
    print(
        "result records RNG family, seed rule, block length, scenario count, resampling "
        "scheme, data window:",
        f"{provenance.rng_family} block={provenance.block_length} "
        f"scheme={provenance.resampling_scheme} "
        f"window=[{provenance.data_window_start_ns}..{provenance.data_window_end_ns}]",
    )
    again = _unwrap(
        api.run_candle_perturbation(
            candles=candles,
            base_seed=42,
            config={api.BLOCK_LENGTH_KEY: 3, api.PERTURBATION_SCENARIO_COUNT_KEY: 200},
        ),
        "second candle-perturbation result",
    )
    assert _unwrap(result.fingerprint(), "fp1").value == _unwrap(again.fingerprint(), "fp2").value
    print("re-running the same inputs reproduces the result fingerprint bit-for-bit")

    # 4. Governed role=replicate fan-out under the min(cpu, memory) governor.
    scenarios = _unwrap(
        api.perturbation_scenarios(42, 3, run_root="fp1:sha256:parent"),
        "scenarios",
    )
    assert scenarios[0].is_true_history and all(s.role == api.SCENARIO_RUN_ROLE for s in scenarios)
    requests = _unwrap(
        api.governed_perturbation_requests(scenarios, projected_peak_memory=4, cpu_cost=1),
        "governed requests",
    )
    governor = _unwrap(
        api.ResourceGovernor.try_create(cpu_budget=2, memory_budget=8, on_full="enqueue"),
        "governor",
    )
    decisions = [_unwrap(governor.submit(request), "admission").decision for request in requests]
    assert decisions == [api.DECISION_ADMITTED, api.DECISION_ADMITTED, api.DECISION_QUEUED]
    assert is_refusal(api.refuse_perturbation_bar_verdict("bar-pass"))
    print(
        "scenarios fan out under the min(cpu, memory) governor with enqueue-on-full; each is "
        "role=replicate, never a bar verdict:",
        decisions,
    )

    # 5. The objective summarised across the alternate histories, as data, no verdict.
    #    (The orchestrator supplies one objective value per scenario after each run.)
    objectives = [_money(v) for v in (1000, 950, 1100, 1000, 900)]
    objective = _unwrap(
        api.summarize_perturbation_objective(
            objective_identity="net_profit",
            observed=objectives[0],
            scenario_objectives=objectives[1:],
            direction=api.DIRECTION_HIGHER_IS_BETTER,
            band_probabilities=[Fraction(1, 20), Fraction(19, 20)],
        ),
        "objective distribution",
    )
    assert objective.emits_verdict is False
    series = objective.chart_series()
    assert set(series) == {"name", "unit_kind", "values"}
    print(
        "objective summarised across the alternate histories as chart series data, no verdict:",
        f"favorable_rank={objective.observed_favorable_rank} p_value={objective.summary.p_value}",
    )

    # 6. Claim class robustness (alternate-history), never edge; cannot gate live money.
    assert result.claim_class == "robustness"
    assert is_refusal(api.refuse_edge_claim(api.CANDLE_PERTURBATION_PROCEDURE))
    assert is_refusal(api.refuse_live_money_gate(api.CANDLE_PERTURBATION_PROCEDURE))
    print(
        "claim class is robustness (alternate-history), never edge; cannot gate live money:",
        api.PERTURBATION_VERDICT_DEFERRED_TO,
    )

    print("candle perturbation ok")


if __name__ == "__main__":
    main()
