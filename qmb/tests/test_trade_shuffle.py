"""Story 22.2 — Monte Carlo trade-shuffle (sequence-risk mode).

Covers the five acceptance criteria: re-ordering the realised trades and
re-accumulating the equity path in exact-integer money while staying world=replay
and procedure-ephemeral (AC1); deterministic base_seed + scenario_index seeding with
a recorded RNG/data-window provenance and a bit-for-bit reproducible fingerprint
(AC2); the direction-aware distribution summary as chart series data with no verdict
(AC3); the scenario count as a UI-editable configurable with no baked MC-1000 default
(AC4); and the governed role=replicate fan-out under the min(cpu, memory) governor
(AC5).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from fractions import Fraction
from typing import TypeVar, cast

from qmb.orchestrator.governor import (
    DECISION_ADMITTED,
    DECISION_QUEUED,
    ResourceGovernor,
)
from qmb.results.measures import ClosedTrade, TradeSide
from qmb.robustness import (
    DIRECTION_LOWER_IS_BETTER,
    FANOUT_DAEMON,
    FANOUT_DOCKER,
    FANOUT_GOVERNOR_BOUND,
    FANOUT_ON_FULL,
    FANOUT_RAY,
    MC_1000_BASELINE,
    MC_1000_IS_BAKED_DEFAULT,
    RNG_FAMILY,
    SCENARIO_COUNT_KEY,
    SCENARIO_RUN_ROLE,
    SEED_DERIVATION_RULE,
    SHUFFLE_MINTS_SYNTHETIC_SERIES,
    TRADE_SHUFFLE_PROCEDURE,
    governed_scenario_requests,
    metric_direction,
    refuse_scenario_bar_verdict,
    run_trade_shuffle,
    scenario_seed,
    shuffle_identity,
    shuffle_scenarios,
)
from qmf.core.chrono import Instant, Interval
from qmf.core.exact import Money
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_DAY_NS = 86_400_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _money(minor: int) -> Money:
    return _ok(Money.try_create(minor, "USD", 2))


def _instant(ns: int) -> Instant:
    return _ok(Instant.try_create(ns))


def _trades() -> list[ClosedTrade]:
    pnls = (500, -300, 800, -1000, 200, -150, 400, -600)
    return [
        _ok(
            ClosedTrade.try_create(
                _money(pnl),
                _money(10),
                TradeSide.LONG if pnl >= 0 else TradeSide.SHORT,
                _instant((index + 1) * _DAY_NS),
            )
        )
        for index, pnl in enumerate(pnls)
    ]


def _window() -> Interval:
    return _ok(Interval.try_create(_instant(0), _instant(9 * _DAY_NS)))


def _run(metrics: list[str], *, base_seed: int = 42, scenarios: int = 300, **kwargs: object):
    return run_trade_shuffle(
        trades=_trades(),
        starting_capital=_money(100_000),
        period=_window(),
        base_seed=base_seed,
        metrics=metrics,
        config={SCENARIO_COUNT_KEY: scenarios},
        **kwargs,
    )


# --- AC1: re-order realised trades, re-accumulate exact equity, stay replay ---


def test_net_profit_is_order_invariant_but_drawdown_is_sequence_dependent() -> None:
    result = _ok(_run(["net_profit", "max_drawdown"]))
    net = result.metric_named("net_profit")
    drawdown = result.metric_named("max_drawdown")
    assert net is not None and drawdown is not None
    # The sum of the same realised P&Ls is invariant under re-ordering.
    assert net.summary.minimum == net.summary.maximum
    # The drawdown depends on the order the P&Ls arrive in — that is the sequence risk.
    assert drawdown.summary.minimum != drawdown.summary.maximum


def test_result_stays_replay_and_procedure_ephemeral_with_seed_in_label() -> None:
    result = _ok(_run(["max_drawdown"], base_seed=7))
    assert result.world == "replay"
    assert result.procedure == TRADE_SHUFFLE_PROCEDURE
    assert result.mints_synthetic_series is False
    assert SHUFFLE_MINTS_SYNTHETIC_SERIES is False
    label = result.result_label()
    assert label["procedure"] == TRADE_SHUFFLE_PROCEDURE
    assert label["base_seed"] == 7
    assert label["world"] == "replay"
    assert label["mints_synthetic_series"] is False


def test_empty_trade_record_is_invalid_input() -> None:
    refused = run_trade_shuffle(
        trades=[],
        starting_capital=_money(100_000),
        period=_window(),
        base_seed=1,
        metrics=["net_profit"],
        config={SCENARIO_COUNT_KEY: 10},
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_money_math_is_exact_no_binary_float_in_identity() -> None:
    result = _ok(_run(["max_drawdown", "net_profit"]))
    # No binary float appears anywhere in the identity content: the money path and
    # every summarised statistic stay exact (AD-7). The identity is fingerprintable.
    _assert_no_floats(result.fp1_identity())
    assert is_ok(result.fingerprint())


def _assert_no_floats(value: object) -> None:
    assert not isinstance(value, float), value
    if isinstance(value, Mapping):
        for item in cast("Mapping[object, object]", value).values():
            _assert_no_floats(item)
    elif isinstance(value, (list, tuple)):
        for item in cast("Sequence[object]", value):
            _assert_no_floats(item)


# --- AC2: deterministic seeding + provenance + reproducibility ---------------


def test_scenario_seed_is_base_plus_index() -> None:
    assert _ok(scenario_seed(42, 0)) == 42
    assert _ok(scenario_seed(42, 5)) == 47
    assert _ok(scenario_seed(0, 0)) == 0
    assert is_refusal(scenario_seed(-1, 0))
    assert is_refusal(scenario_seed(42, -1))
    assert is_refusal(scenario_seed(True, 0))


def test_provenance_records_rng_family_seed_rule_count_and_window() -> None:
    result = _ok(_run(["max_drawdown"], base_seed=42, scenarios=250))
    provenance = result.provenance
    assert provenance.rng_family == RNG_FAMILY
    assert provenance.base_seed == 42
    assert provenance.seed_derivation_rule == SEED_DERIVATION_RULE == "base_seed + scenario_index"
    assert provenance.scenario_count == 250
    assert provenance.data_window_start_ns == 0
    assert provenance.data_window_end_ns == 9 * _DAY_NS
    # It is exactly the rng_provenance stamp the CT-32 label folds in.
    assert result.rng_provenance() == provenance.fp1_identity()
    assert is_ok(fingerprint(provenance.fp1_identity()))


def test_same_inputs_reproduce_the_fingerprint_bit_for_bit() -> None:
    first = _ok(_run(["max_drawdown", "sharpe_ratio", "losing_streak"], base_seed=42))
    second = _ok(_run(["max_drawdown", "sharpe_ratio", "losing_streak"], base_seed=42))
    assert _ok(first.fingerprint()).value == _ok(second.fingerprint()).value


def test_a_different_base_seed_gives_a_different_fingerprint() -> None:
    base = _ok(_run(["max_drawdown"], base_seed=42))
    other = _ok(_run(["max_drawdown"], base_seed=43))
    assert _ok(base.fingerprint()).value != _ok(other.fingerprint()).value


def test_shuffle_scenarios_seed_and_role() -> None:
    scenarios = _ok(shuffle_scenarios(42, 4, run_root="fp1:sha256:parent"))
    assert [scenario.seed for scenario in scenarios] == [42, 43, 44, 45]
    assert [scenario.scenario_index for scenario in scenarios] == [0, 1, 2, 3]
    assert all(scenario.role == SCENARIO_RUN_ROLE for scenario in scenarios)
    # Run ids are deterministic and distinct.
    ids = [scenario.run_id.value for scenario in scenarios]
    assert len(set(ids)) == 4
    again = _ok(shuffle_scenarios(42, 4, run_root="fp1:sha256:parent"))
    assert [scenario.run_id.value for scenario in again] == ids
    # A different parent run root re-keys the replicate ids.
    other = _ok(shuffle_scenarios(42, 4, run_root="fp1:sha256:other"))
    assert [scenario.run_id.value for scenario in other] != ids


# --- AC3: direction-aware distribution summary as chart series, no verdict ----


def test_metric_direction_is_lower_is_better_for_drawdown_family() -> None:
    assert metric_direction("max_drawdown") == DIRECTION_LOWER_IS_BETTER
    assert metric_direction("max_drawdown_recovery") == DIRECTION_LOWER_IS_BETTER
    assert metric_direction("losing_streak") == DIRECTION_LOWER_IS_BETTER
    assert metric_direction("net_profit") == qmb.DIRECTION_HIGHER_IS_BETTER
    assert metric_direction("sharpe_ratio") == qmb.DIRECTION_HIGHER_IS_BETTER


def test_summary_carries_percentile_ranks_bands_and_direction_aware_rank() -> None:
    result = _ok(
        _run(
            ["max_drawdown"],
            band_probabilities=[Fraction(1, 20), Fraction(19, 20)],
        )
    )
    drawdown = result.metric_named("max_drawdown")
    assert drawdown is not None
    # Confidence bands were computed at the caller-supplied probabilities.
    assert [band.probability for band in drawdown.summary.bands] == [
        Fraction(1, 20),
        Fraction(19, 20),
    ]
    # Direction-aware rank for a lower-is-better metric is the complement of the raw
    # percentile rank (the fraction of scenarios the original result is better than).
    expected = Fraction(1) - drawdown.summary.percentile_rank
    assert drawdown.observed_favorable_rank == expected
    assert Fraction(0) <= drawdown.observed_favorable_rank <= Fraction(1)


def test_chart_series_are_data_never_images_and_no_verdict() -> None:
    result = _ok(_run(["max_drawdown", "net_profit"]))
    series = result.chart_series()
    assert len(series) == len(result.metrics)
    for item in series:
        assert set(item) == {"name", "unit_kind", "values"}
        assert "png" not in item and "image" not in item and "base64" not in item
    assert result.emits_verdict is False
    for metric in result.metrics:
        assert metric.emits_verdict is False
        assert metric.summary.emits_verdict is False


def test_higher_is_better_metric_keeps_raw_percentile_rank() -> None:
    result = _ok(_run(["net_profit"]))
    net = result.metric_named("net_profit")
    assert net is not None
    assert net.direction == qmb.DIRECTION_HIGHER_IS_BETTER
    assert net.observed_favorable_rank == net.summary.percentile_rank


# --- AC4: scenario count is a UI-editable configurable, no baked MC-1000 -------


def test_scenario_count_resolves_from_the_run_config_key() -> None:
    result = _ok(_run(["net_profit"], scenarios=123))
    assert result.provenance.scenario_count == 123


def test_no_scenario_count_is_a_typed_refusal_no_baked_default() -> None:
    refused = run_trade_shuffle(
        trades=_trades(),
        starting_capital=_money(100_000),
        period=_window(),
        base_seed=1,
        metrics=["net_profit"],
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert MC_1000_IS_BAKED_DEFAULT is False
    assert MC_1000_BASELINE == 1000


def test_explicit_scenario_count_is_accepted_and_bad_values_refuse() -> None:
    explicit = run_trade_shuffle(
        trades=_trades(),
        starting_capital=_money(100_000),
        period=_window(),
        base_seed=1,
        metrics=["net_profit"],
        scenario_count=50,
    )
    assert _ok(explicit).provenance.scenario_count == 50
    assert is_refusal(_run(["net_profit"], scenarios=0))
    assert is_refusal(_run(["net_profit"], scenarios=-5))


def test_off_roster_metric_is_invalid_input() -> None:
    assert is_refusal(_run(["not_a_measure"]))
    assert is_refusal(_run([]))


# --- AC5: governed role=replicate fan-out under the min(cpu, memory) governor --


def test_scenarios_fan_out_as_governed_replicate_requests_with_enqueue_on_full() -> None:
    scenarios = _ok(shuffle_scenarios(42, 3, run_root="fp1:sha256:parent"))
    requests = _ok(governed_scenario_requests(scenarios, projected_peak_memory=4, cpu_cost=1))
    assert len(requests) == 3
    governor = _ok(ResourceGovernor.try_create(cpu_budget=2, memory_budget=8, on_full="enqueue"))
    decisions = [_ok(governor.submit(request)).decision for request in requests]
    # min(cpu=2, memory=8//4=2) = 2 admitted, the third enqueues (never oversubscribed).
    assert decisions == [DECISION_ADMITTED, DECISION_ADMITTED, DECISION_QUEUED]


def test_scenario_never_writes_a_bar_verdict() -> None:
    assert SCENARIO_RUN_ROLE == "replicate"
    refused = refuse_scenario_bar_verdict("bar-pass")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["role"] == "replicate"


def test_fanout_declares_no_ray_no_daemon_no_required_docker() -> None:
    assert FANOUT_GOVERNOR_BOUND == "min-cpu-memory"
    assert FANOUT_ON_FULL == "enqueue"
    assert FANOUT_RAY == "absent"
    assert FANOUT_DAEMON == "not-required"
    assert FANOUT_DOCKER == "not-required"
    identity = shuffle_identity()
    assert identity["fanout_bound"] == "min-cpu-memory"
    assert identity["scenario_run_role"] == "replicate"
    assert identity["mc_1000_is_baked_default"] is False


# --- identity ----------------------------------------------------------------


def test_shuffle_identity_excludes_semver_and_is_fingerprintable() -> None:
    identity = shuffle_identity()
    assert qmb.__version__ not in str(identity)
    assert is_ok(fingerprint(identity))
    # Reachable from the library root and the API door as one object.
    assert qmb.shuffle_identity() == identity
