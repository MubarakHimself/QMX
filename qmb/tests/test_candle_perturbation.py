"""Story 22.3 — Monte Carlo candle-perturbation (alternate-history mode).

Covers the six acceptance criteria: moving-block-bootstrapping exact-integer OHLC
deltas onto the seed price and always rebuilding a valid strictly-positive series
with scenario 0 the true history (AC1); the procedure-ephemeral persistence rule that
keeps the run world=replay with the procedure identity and seed in the label and a
robustness-only claim (AC2); a persisting config compiling to world=simulated as a
typed policy rejection and a replay clock on synthetic-tainted persisted data as a
typed invalid input (AC3); deterministic base_seed + scenario_index seeding with a
recorded RNG / block / resampling / data-window provenance and a bit-for-bit
reproducible fingerprint (AC4); the governed role=replicate fan-out under the
min(cpu, memory) governor (AC5); and the direction-aware distribution summary as chart
series data with no verdict and a robustness — never edge — claim (AC6).
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
from qmb.robustness import (
    BLOCK_LENGTH_KEY,
    CANDLE_PERTURBATION_PROCEDURE,
    DIRECTION_HIGHER_IS_BETTER,
    DIRECTION_LOWER_IS_BETTER,
    PERTURBATION_CLAIM_CLASS,
    PERTURBATION_MINTS_SYNTHETIC_SERIES,
    PERTURBATION_PERSISTS_SYNTHETIC_SERIES,
    PERTURBATION_SCENARIO_COUNT_KEY,
    RESAMPLING_SCHEME,
    RNG_FAMILY,
    SCENARIO_RUN_ROLE,
    SEED_DERIVATION_RULE,
    WORLD_WHEN_EPHEMERAL,
    WORLD_WHEN_PERSISTED,
    Candle,
    governed_perturbation_requests,
    ohlc_deltas,
    perturbation_identity,
    perturbation_persistence,
    perturbation_scenarios,
    refuse_edge_claim,
    refuse_live_money_gate,
    refuse_persisted_synthetic_series,
    refuse_perturbation_bar_verdict,
    refuse_replay_clock_on_synthetic_persisted,
    run_candle_perturbation,
    summarize_perturbation_objective,
)
from qmf.core.chrono import Instant
from qmf.core.exact import Money
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_DAY_NS = 86_400_000_000_000

# A real historical candle series (strictly positive, valid OHLC), closing on
# distinct daily bars, with an up-and-down price path.
_RAW: tuple[tuple[int, int, int, int], ...] = (
    (100, 105, 98, 103),
    (103, 108, 101, 107),
    (107, 110, 104, 106),
    (106, 111, 105, 109),
    (109, 112, 107, 110),
    (110, 115, 108, 113),
    (113, 116, 111, 112),
    (112, 114, 109, 111),
)


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _money(minor: int) -> Money:
    return _ok(Money.try_create(minor, "USD", 2))


def _instant(ns: int) -> Instant:
    return _ok(Instant.try_create(ns))


def _candles() -> list[Candle]:
    return [
        _ok(Candle.try_create(_instant((index + 1) * _DAY_NS), o, h, low, c))
        for index, (o, h, low, c) in enumerate(_RAW)
    ]


def _run(*, base_seed: int = 42, block_length: int = 3, scenarios: int = 60, **kwargs: object):
    return run_candle_perturbation(
        candles=_candles(),
        base_seed=base_seed,
        config={BLOCK_LENGTH_KEY: block_length, PERTURBATION_SCENARIO_COUNT_KEY: scenarios},
        **kwargs,
    )


# --- AC1: moving-block bootstrap onto the seed price, valid, scenario 0 true ---


def test_scenario_zero_is_the_true_history_verbatim() -> None:
    result = _ok(_run())
    true = result.true_history()
    assert true.scenario_index == 0
    assert true.is_true_history is True
    rebuilt = tuple((c.open, c.high, c.low, c.close) for c in true.candles)
    assert rebuilt == _RAW


def test_every_scenario_is_a_valid_strictly_positive_ohlc_series() -> None:
    result = _ok(_run(block_length=2, scenarios=80))
    assert len(result.series) == 80
    for series in result.series:
        assert len(series.candles) == len(_RAW)
        for candle in series.candles:
            # Strictly positive (AC1).
            assert candle.open > 0 and candle.high > 0 and candle.low > 0 and candle.close > 0
            # High/low bounds enforced (AC1).
            assert candle.high >= max(candle.open, candle.close)
            assert candle.high >= candle.low
            assert candle.low <= min(candle.open, candle.close)


def test_deltas_cumulative_sum_back_to_the_true_series() -> None:
    # The exact-integer OHLC deltas, cumulative-summed in true order onto the seed
    # price, reconstruct the exact input candles (AC1).
    candles = _candles()
    deltas = _ok(ohlc_deltas(candles))
    assert len(deltas) == len(candles)
    anchor = candles[0].open
    for delta, candle in zip(deltas, candles, strict=True):
        assert anchor + delta.open_delta == candle.open
        assert anchor + delta.high_delta == candle.high
        assert anchor + delta.low_delta == candle.low
        assert anchor + delta.close_delta == candle.close
        anchor = candle.close


def test_result_stays_replay_and_mints_but_never_persists_synthetic_series() -> None:
    result = _ok(_run(base_seed=7))
    assert result.world == "replay"
    assert result.procedure == CANDLE_PERTURBATION_PROCEDURE
    assert result.mints_synthetic_series is True
    assert result.persists_synthetic_series is False
    assert PERTURBATION_MINTS_SYNTHETIC_SERIES is True
    assert PERTURBATION_PERSISTS_SYNTHETIC_SERIES is False
    label = result.result_label()
    assert label["procedure"] == CANDLE_PERTURBATION_PROCEDURE
    assert label["base_seed"] == 7
    assert label["world"] == "replay"
    assert label["provenance_kind"] == "procedure-ephemeral"
    assert label["claim_class"] == PERTURBATION_CLAIM_CLASS == "robustness"


def test_block_length_is_a_required_configurable_with_no_ratified_value() -> None:
    # Unset block length is a typed refusal — no invented default (SC-07).
    refused = run_candle_perturbation(
        candles=_candles(),
        base_seed=1,
        config={PERTURBATION_SCENARIO_COUNT_KEY: 10},
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    # An explicit block length is accepted.
    assert (
        _ok(
            run_candle_perturbation(
                candles=_candles(), base_seed=1, block_length=3, scenario_count=5
            )
        ).block_length
        == 3
    )


def test_block_length_cannot_exceed_the_candle_count() -> None:
    refused = _run(block_length=len(_RAW) + 1)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_empty_candle_series_and_invalid_candle_refuse() -> None:
    assert is_refusal(
        run_candle_perturbation(candles=[], base_seed=1, block_length=1, scenario_count=2)
    )
    # A non-positive or bound-violating candle never constructs.
    assert is_refusal(Candle.try_create(_instant(_DAY_NS), 0, 5, 1, 3))
    assert is_refusal(Candle.try_create(_instant(_DAY_NS), 10, 8, 5, 9))  # high below open


def test_money_math_is_exact_no_binary_float_in_identity() -> None:
    result = _ok(_run())
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


# --- AC2 / AC3: the B-7 persistence law --------------------------------------


def test_procedure_ephemeral_persistence_stays_replay_robustness() -> None:
    classified = _ok(perturbation_persistence(persist=False, clock="replay"))
    assert classified.world == WORLD_WHEN_EPHEMERAL == "replay"
    assert classified.data_provenance == "procedure-ephemeral"
    assert classified.claim_class == "robustness"
    assert classified.persisted is False


def test_persisting_the_synthetic_series_is_a_simulated_policy_rejection() -> None:
    refused = perturbation_persistence(persist=True, clock="simulated")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["world"] == WORLD_WHEN_PERSISTED == "simulated"
    assert refused.context["gated_behind"] == "GAP-0048"
    # The same policy rejection is reachable by its named door.
    named = refuse_persisted_synthetic_series("run-config")
    assert is_refusal(named)
    assert named.category is RefusalCategory.POLICY_REJECTION


def test_replay_clock_on_synthetic_persisted_data_is_invalid_input() -> None:
    refused = perturbation_persistence(persist=True, clock="replay")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["data_provenance"] == "synthetic-tainted"
    named = refuse_replay_clock_on_synthetic_persisted("replay")
    assert is_refusal(named)
    assert named.category is RefusalCategory.INVALID_INPUT


# --- AC4: deterministic seeding + provenance + reproducibility ---------------


def test_provenance_records_rng_block_scheme_and_window() -> None:
    result = _ok(_run(base_seed=42, block_length=4, scenarios=50))
    provenance = result.provenance
    assert provenance.rng_family == RNG_FAMILY
    assert provenance.base_seed == 42
    assert provenance.seed_derivation_rule == SEED_DERIVATION_RULE == "base_seed + scenario_index"
    assert provenance.block_length == 4
    assert provenance.scenario_count == 50
    assert provenance.resampling_scheme == RESAMPLING_SCHEME == "moving-block-bootstrap"
    assert provenance.data_window_start_ns == _DAY_NS
    assert provenance.data_window_end_ns == len(_RAW) * _DAY_NS
    # It is exactly the rng_provenance stamp the CT-32 label folds in (B-13).
    assert result.rng_provenance() == provenance.fp1_identity()
    assert is_ok(fingerprint(provenance.fp1_identity()))


def test_same_inputs_reproduce_the_fingerprint_bit_for_bit() -> None:
    first = _ok(_run(base_seed=42))
    second = _ok(_run(base_seed=42))
    assert _ok(first.fingerprint()).value == _ok(second.fingerprint()).value


def test_a_different_base_seed_gives_a_different_fingerprint() -> None:
    base = _ok(_run(base_seed=42))
    other = _ok(_run(base_seed=43))
    assert _ok(base.fingerprint()).value != _ok(other.fingerprint()).value


def test_scenarios_seed_role_and_true_history_flag() -> None:
    scenarios = _ok(perturbation_scenarios(42, 4, run_root="fp1:sha256:parent"))
    assert [s.seed for s in scenarios] == [42, 43, 44, 45]
    assert [s.scenario_index for s in scenarios] == [0, 1, 2, 3]
    assert scenarios[0].is_true_history is True
    assert all(s.is_true_history is False for s in scenarios[1:])
    assert all(s.role == SCENARIO_RUN_ROLE for s in scenarios)
    ids = [s.run_id.value for s in scenarios]
    assert len(set(ids)) == 4
    again = _ok(perturbation_scenarios(42, 4, run_root="fp1:sha256:parent"))
    assert [s.run_id.value for s in again] == ids
    other = _ok(perturbation_scenarios(42, 4, run_root="fp1:sha256:other"))
    assert [s.run_id.value for s in other] != ids


# --- AC5: governed role=replicate fan-out under min(cpu, memory) governor ------


def test_scenarios_fan_out_as_governed_replicate_requests_with_enqueue_on_full() -> None:
    scenarios = _ok(perturbation_scenarios(42, 3, run_root="fp1:sha256:parent"))
    requests = _ok(governed_perturbation_requests(scenarios, projected_peak_memory=4, cpu_cost=1))
    assert len(requests) == 3
    governor = _ok(ResourceGovernor.try_create(cpu_budget=2, memory_budget=8, on_full="enqueue"))
    decisions = [_ok(governor.submit(request)).decision for request in requests]
    # min(cpu=2, memory=8//4=2) = 2 admitted, the third enqueues (never oversubscribed).
    assert decisions == [DECISION_ADMITTED, DECISION_ADMITTED, DECISION_QUEUED]


def test_scenario_never_writes_a_bar_verdict() -> None:
    assert SCENARIO_RUN_ROLE == "replicate"
    refused = refuse_perturbation_bar_verdict("bar-pass")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["role"] == "replicate"


# --- AC6: distribution summary as data, robustness never edge, no live gate ----


def test_objective_summary_is_direction_aware_data_with_no_verdict() -> None:
    observed = _money(1000)
    scenario_objectives = [_money(950), _money(1100), _money(1000), _money(900), _money(1200)]
    higher = _ok(
        summarize_perturbation_objective(
            objective_identity="net_profit",
            observed=observed,
            scenario_objectives=scenario_objectives,
            direction=DIRECTION_HIGHER_IS_BETTER,
            band_probabilities=[Fraction(1, 20), Fraction(19, 20)],
        )
    )
    assert higher.emits_verdict is False
    assert higher.direction == DIRECTION_HIGHER_IS_BETTER
    # Higher-is-better keeps the raw percentile rank as the favourable fraction.
    assert higher.observed_favorable_rank == higher.summary.percentile_rank
    bands = [band.probability for band in higher.summary.bands]
    assert bands == [Fraction(1, 20), Fraction(19, 20)]
    # Lower-is-better takes the complement (a drawdown-style objective).
    lower = _ok(
        summarize_perturbation_objective(
            objective_identity="max_drawdown",
            observed=observed,
            scenario_objectives=scenario_objectives,
            direction=DIRECTION_LOWER_IS_BETTER,
        )
    )
    assert lower.observed_favorable_rank == Fraction(1) - lower.summary.percentile_rank


def test_objective_chart_series_are_data_never_images() -> None:
    result = _ok(
        _run(
            block_length=2,
            scenarios=6,
            objective_identity="net_profit",
            scenario_objectives=[_money(v) for v in (1000, 950, 1100, 1000, 900, 1200)],
            objective_direction=DIRECTION_HIGHER_IS_BETTER,
        )
    )
    assert result.objective is not None
    series = result.objective.chart_series()
    assert set(series) == {"name", "unit_kind", "values"}
    assert "png" not in series and "image" not in series and "base64" not in series
    assert result.emits_verdict is False


def test_objective_refuses_raw_float_and_unit_mismatch() -> None:
    # A raw binary float must cross the carve-out first; it is refused here (AD-7).
    assert is_refusal(
        summarize_perturbation_objective(
            objective_identity="net_profit",
            observed=1.5,
            scenario_objectives=[_money(1)],
            direction=DIRECTION_HIGHER_IS_BETTER,
        )
    )
    assert is_refusal(
        summarize_perturbation_objective(
            objective_identity="net_profit",
            observed=_money(1000),
            scenario_objectives=[2.5],
            direction=DIRECTION_HIGHER_IS_BETTER,
        )
    )


def test_claim_is_robustness_never_edge_and_cannot_gate_live_money() -> None:
    result = _ok(_run())
    assert result.claim_class == "robustness"
    edge = refuse_edge_claim(CANDLE_PERTURBATION_PROCEDURE)
    assert is_refusal(edge)
    assert edge.category is RefusalCategory.POLICY_REJECTION
    gate = refuse_live_money_gate(CANDLE_PERTURBATION_PROCEDURE)
    assert is_refusal(gate)
    assert gate.category is RefusalCategory.POLICY_REJECTION
    assert gate.context["gated_behind"] == "GAP-0048"


# --- identity ----------------------------------------------------------------


def test_perturbation_identity_excludes_semver_and_is_fingerprintable() -> None:
    identity = perturbation_identity()
    assert qmb.__version__ not in str(identity)
    assert is_ok(fingerprint(identity))
    assert identity["procedure"] == CANDLE_PERTURBATION_PROCEDURE
    assert identity["mints_synthetic_series"] is True
    assert identity["persists_synthetic_series"] is False
    assert identity["scenario_zero_is_true_history"] is True
    assert identity["claim_class"] == "robustness"
    # Reachable from the library root and the API door as one object.
    assert qmb.perturbation_identity() == identity
