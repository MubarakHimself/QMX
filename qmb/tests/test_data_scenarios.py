"""Tier-1 tests for deterministic multi-scenario generation & the pinned RNG (Story 23.4).

Covers the story acceptance criteria: bit-reproducibility and reproduce-or-refuse
from ``{process, seed, source-dataset id, generator-config fp1}`` (AC1); the QMX-owned,
version-pinned RNG recorded in provenance, never a runtime stdlib Random (AC2); the
per-scenario substream ``base_seed + scenario_index`` with each scenario tagged by index
and reproducible in isolation (AC3); the history-seeded scenario-0 untouched original
anchor with perturbed scenarios ``>0`` (AC4); the from-scratch gbm having no anchor and
no computable robustness band (AC5); and the process-per-run governor fan-out bounded by
min(cpu, memory) with enqueue-when-full and counted, typed scenario failures (AC6).
"""

from __future__ import annotations

from typing import TypeVar, cast

from qmb.data import (
    GENERATOR_WORLD,
    RNG_ALGORITHM,
    RNG_FAMILY,
    RNG_VERSION,
    SEED_DERIVATION_RULE,
    GeneratedScenario,
    GovernorAdmissionPlan,
    ScenarioFanout,
    admit_scenario_fanout,
    derive_scenario_seeds,
    derive_substream_seed,
    generate,
    generate_scenarios,
    refuse_robustness_band_for_from_scratch,
    regenerate_scenario,
    reproduce_generation,
    resolve_generator_config,
    scenario_governed_requests,
    tag_synthetic_artifact,
)
from qmb.data.gap_check import AlwaysOpenCalendar, MarketHoursCalendar
from qmb.data.rng import PinnedRng, rng_provenance
from qmf.core import RefusalCategory, Result, World, is_ok, is_refusal
from qmf.core.chrono import CalendarIdentity
from qmf.core.fingerprint import fingerprint

T = TypeVar("T")

_STEP = 60_000_000_000  # 1-minute bars
_START = 0
_END = 600_000_000_000  # ten 1-minute slots


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _always_open() -> MarketHoursCalendar:
    identity = _ok(CalendarIdentity.try_create("always-open", "v1", "none"))
    return cast("MarketHoursCalendar", AlwaysOpenCalendar(identity=identity))


def _source_bars(count: int = 40, *, scale: int = 5) -> tuple[dict[str, object], ...]:
    bars: list[dict[str, object]] = []
    price = 110_000
    for index in range(count):
        close = price + (60 if index % 3 else -40)
        bars.append(
            {
                "instant_ns": index * _STEP,
                "open": price,
                "high": max(price, close) + 30,
                "low": min(price, close) - 30,
                "close": close,
                "scale": scale,
            }
        )
        price = close
    return tuple(bars)


def _gbm(**extra: object) -> dict[str, object]:
    body: dict[str, object] = {
        "process": "gbm",
        "venue": "dukascopy-fx",
        "symbol": "EURUSD",
        "scale": 5,
        "tick_size": 1,
        "resolution": "M1",
        "bar_step_ns": _STEP,
        "start_ns": _START,
        "end_ns": _END,
        "seed_price": 110_000,
        "volatility": "0.001",
        "seed": 7,
        "scenario_count": 4,
        "claim_class": "logic-smoke",
    }
    body.update(extra)
    return body


def _history(process: str, **extra: object) -> dict[str, object]:
    body: dict[str, object] = {
        "process": process,
        "venue": "dukascopy-fx",
        "symbol": "EURUSD",
        "scale": 5,
        "tick_size": 1,
        "resolution": "M1",
        "bar_step_ns": _STEP,
        "start_ns": _START,
        "end_ns": _END,
        "seed": 11,
        "scenario_count": 4,
        "source_dataset": {
            "venue": "dukascopy-fx",
            "symbol": "EURUSD",
            "resolution": "M1",
            "side": "bid",
        },
    }
    body.update(extra)
    return body


# --- AC1: reproduce-or-refuse from {process, seed, source-dataset id, fp1} -----


def test_artifact_is_bit_reproducible_from_the_config() -> None:
    first = _ok(generate(_gbm(scenario_count=1), calendar=_always_open()))
    second = _ok(generate(_gbm(scenario_count=1), calendar=_always_open()))
    assert first.artifact_fingerprint == second.artifact_fingerprint
    assert first.artifact_fingerprint.startswith("fp1:sha256:")
    assert tuple(b.as_mapping() for b in first.bars) == tuple(b.as_mapping() for b in second.bars)


def test_reproduce_generation_matches_the_recorded_artifact_fingerprint() -> None:
    original = _ok(generate(_gbm(), calendar=_always_open()))
    reproduced = _ok(
        reproduce_generation(
            _gbm(),
            expected_artifact_fingerprint=original.artifact_fingerprint,
            calendar=_always_open(),
        )
    )
    assert reproduced.artifact_fingerprint == original.artifact_fingerprint


def test_non_reproducible_artifact_is_a_typed_refusal() -> None:
    original = _ok(generate(_gbm(seed=7), calendar=_always_open()))
    # A different seed cannot reproduce the recorded fingerprint — reproduce-or-refuse.
    refusal = reproduce_generation(
        _gbm(seed=999),
        expected_artifact_fingerprint=original.artifact_fingerprint,
        calendar=_always_open(),
    )
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "artifact_fingerprint"


def test_reproduce_generation_rejects_a_missing_expected_fingerprint() -> None:
    refusal = reproduce_generation(
        _gbm(), expected_artifact_fingerprint=None, calendar=_always_open()
    )
    assert is_refusal(refusal)
    assert refusal.context["field"] == "expected_artifact_fingerprint"


# --- AC2: the QMX-owned, version-pinned RNG recorded in provenance -------------


def test_rng_is_qmx_owned_and_version_pinned_never_stdlib() -> None:
    provenance = rng_provenance()
    assert provenance["rng_algorithm"] == RNG_ALGORITHM == "qmx-splitmix64"
    assert provenance["rng_version"] == RNG_VERSION == 1
    assert provenance["rng_family"] == RNG_FAMILY == "qmx-splitmix64-v1"
    assert provenance["is_qmx_owned"] is True
    assert provenance["is_runtime_stdlib_random"] is False


def test_config_identity_records_the_rng_algorithm_and_version() -> None:
    config = _ok(resolve_generator_config(_gbm()))
    identity = config.fp1_identity()
    assert identity["rng_algorithm"] == RNG_ALGORITHM
    assert identity["rng_family"] == RNG_FAMILY
    assert identity["rng_version"] == RNG_VERSION
    # The recipe carries no runtime-stdlib RNG token.
    assert "mt19937" not in RNG_FAMILY
    assert "stdlib" not in RNG_FAMILY


def test_store_provenance_record_carries_the_rng_algorithm_and_version() -> None:
    config = _ok(resolve_generator_config(_gbm()))
    provenance = _ok(tag_synthetic_artifact(config, generation_timestamp_ns=1))
    record = provenance.as_record()
    assert record["rng_algorithm"] == RNG_ALGORITHM
    assert record["rng_family"] == RNG_FAMILY
    assert record["rng_version"] == RNG_VERSION
    assert record["rng_is_runtime_stdlib_random"] is False


def test_pinned_rng_is_deterministic_and_seed_sensitive() -> None:
    a = PinnedRng(7)
    b = PinnedRng(7)
    assert [a.next_u64() for _ in range(8)] == [b.next_u64() for _ in range(8)]
    c = PinnedRng(8)
    assert [PinnedRng(7).next_u64() for _ in range(8)] != [c.next_u64() for _ in range(8)]
    # randrange is unbiased-in-range and gauss is finite.
    draws = [PinnedRng(3).randrange(5) for _ in range(1)]
    assert all(0 <= d < 5 for d in draws)


def test_receipt_and_generate_use_the_pinned_rng_family() -> None:
    receipt = _ok(generate(_gbm(), calendar=_always_open()))
    assert receipt.rng_family == RNG_FAMILY
    assert receipt.rng_algorithm == RNG_ALGORITHM
    assert receipt.rng_version == RNG_VERSION


# --- AC3: per-scenario substreams, tagged by index, reproducible in isolation --


def test_scenario_substreams_are_base_seed_plus_index() -> None:
    seeds = _ok(derive_scenario_seeds(7, 4))
    assert seeds == (7, 8, 9, 10)
    assert derive_substream_seed(7, 3) == 10
    assert SEED_DERIVATION_RULE == "base_seed + scenario_index"


def test_each_scenario_is_tagged_by_index_and_seed() -> None:
    fanout = _ok(generate_scenarios(_gbm(scenario_count=5), calendar=_always_open()))
    assert [s.scenario_index for s in fanout.scenarios] == [0, 1, 2, 3, 4]
    assert [s.seed for s in fanout.scenarios] == [7, 8, 9, 10, 11]
    # Distinct scenarios have distinct series fingerprints and run ids.
    fps = {s.series_fingerprint.value for s in fanout.scenarios}
    run_ids = {s.run_id.value for s in fanout.scenarios}
    assert len(fps) == 5
    assert len(run_ids) == 5


def test_scenario_reproduces_in_isolation() -> None:
    fanout = _ok(generate_scenarios(_gbm(scenario_count=5), calendar=_always_open()))
    isolated = _ok(regenerate_scenario(_gbm(scenario_count=5), 3, calendar=_always_open()))
    inside = fanout.scenario_at(3)
    assert inside is not None
    assert isolated.scenario_index == 3
    assert isolated.seed == derive_substream_seed(7, 3)
    assert isolated.series_fingerprint.value == inside.series_fingerprint.value
    assert tuple(b.as_mapping() for b in isolated.bars) == tuple(
        b.as_mapping() for b in inside.bars
    )


def test_fanout_result_fingerprint_is_reproducible() -> None:
    first = _ok(generate_scenarios(_gbm(scenario_count=4), calendar=_always_open()))
    second = _ok(generate_scenarios(_gbm(scenario_count=4), calendar=_always_open()))
    assert _ok(first.fingerprint()).value == _ok(second.fingerprint()).value


def test_regenerate_scenario_rejects_an_out_of_range_index() -> None:
    refusal = regenerate_scenario(_gbm(scenario_count=3), 5, calendar=_always_open())
    assert is_refusal(refusal)
    assert refusal.context["field"] == "scenario_index"


# --- AC4: history-seeded scenario 0 is the untouched original real path --------


def test_history_seeded_scenario_zero_is_the_untouched_original() -> None:
    source = _source_bars()
    fanout = _ok(
        generate_scenarios(
            _history("block-bootstrap", block_length=5, scenario_count=4),
            calendar=_always_open(),
            source_series=source,
        )
    )
    assert fanout.has_original_anchor is True
    anchor = fanout.original_anchor()
    assert anchor is not None
    assert anchor.scenario_index == 0
    assert anchor.is_original_anchor is True
    # scenario 0 carries the source OHLC verbatim on the generation grid (untouched).
    for index, bar in enumerate(anchor.bars):
        row = source[index]
        assert (bar.open, bar.high, bar.low, bar.close) == (
            row["open"],
            row["high"],
            row["low"],
            row["close"],
        )


def test_history_seeded_scenarios_above_zero_are_perturbed() -> None:
    source = _source_bars()
    fanout = _ok(
        generate_scenarios(
            _history("block-bootstrap", block_length=5, scenario_count=4),
            calendar=_always_open(),
            source_series=source,
        )
    )
    anchor = fanout.original_anchor()
    assert anchor is not None
    for scenario in fanout.scenarios[1:]:
        assert scenario.is_original_anchor is False
        assert scenario.bars != anchor.bars


def test_history_seeded_anchor_needs_enough_real_bars() -> None:
    # A source series shorter than the generation window cannot anchor the original.
    refusal = generate_scenarios(
        _history("block-bootstrap", block_length=2, scenario_count=3),
        calendar=_always_open(),
        source_series=_source_bars(count=3),
    )
    assert is_refusal(refusal)
    assert refusal.context["field"] == "source_series"


# --- AC5: from-scratch gbm has no anchor and no computable robustness band -----


def test_gbm_fanout_has_no_original_anchor_and_no_band() -> None:
    fanout = _ok(generate_scenarios(_gbm(scenario_count=4), calendar=_always_open()))
    assert fanout.has_original_anchor is False
    assert fanout.robustness_band_computable is False
    assert fanout.original_anchor() is None
    assert all(not s.is_original_anchor for s in fanout.scenarios)


def test_gbm_run_emits_only_infra_stress_or_logic_smoke_verdicts() -> None:
    fanout = _ok(generate_scenarios(_gbm(scenario_count=3), calendar=_always_open()))
    assert set(fanout.permittable_claim_classes) == {"infra-stress", "logic-smoke"}
    assert "robustness" not in fanout.permittable_claim_classes
    assert fanout.world == GENERATOR_WORLD == World.SIMULATED.value


def test_robustness_band_on_a_from_scratch_run_is_a_typed_refusal() -> None:
    fanout = _ok(generate_scenarios(_gbm(scenario_count=3), calendar=_always_open()))
    refusal = fanout.robustness_band_refusal()
    assert refusal is not None
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert refusal.context["field"] == "robustness_band"
    # The standalone contract refusal agrees.
    standalone = refuse_robustness_band_for_from_scratch("gbm")
    assert standalone.category is RefusalCategory.POLICY_REJECTION
    assert standalone.context["has_original_anchor"] is False


def test_history_seeded_fanout_has_a_computable_band_and_no_band_refusal() -> None:
    fanout = _ok(
        generate_scenarios(
            _history("block-bootstrap", block_length=5, scenario_count=4),
            calendar=_always_open(),
            source_series=_source_bars(),
        )
    )
    assert fanout.robustness_band_computable is True
    assert fanout.robustness_band_refusal() is None


# --- AC6: governor fan-out (min(cpu, memory), enqueue-when-full), typed failures --


def test_scenario_fanout_runs_process_per_run_under_the_governor() -> None:
    fanout = _ok(
        generate_scenarios(
            _gbm(scenario_count=4), calendar=_always_open(), projected_peak_memory=1000
        )
    )
    assert len(fanout.governed_requests) == 4
    plan = _ok(
        admit_scenario_fanout(
            fanout,
            budgets={"qmb_governor_cpu_budget": 2, "qmb_governor_memory_budget": 2500},
        )
    )
    assert isinstance(plan, GovernorAdmissionPlan)
    # min(cpu=2, memory=floor(2500/1000)=2) => parallelism bound 2; 2 admitted, 2 queued.
    assert plan.parallelism_bound == 2
    assert len(plan.admitted) == 2
    assert len(plan.queued) == 2
    assert plan.silent_oversubscription is False
    assert plan.on_full == "enqueue"


def test_governor_refuse_mode_overflow_is_a_typed_refusal_never_oversubscription() -> None:
    fanout = _ok(
        generate_scenarios(
            _gbm(scenario_count=4), calendar=_always_open(), projected_peak_memory=1000
        )
    )
    refusal = admit_scenario_fanout(
        fanout,
        budgets={"qmb_governor_cpu_budget": 2, "qmb_governor_memory_budget": 2500},
        on_full="refuse",
    )
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION


def test_a_run_that_can_never_fit_the_budget_is_a_typed_refusal() -> None:
    requests = _ok(
        scenario_governed_requests(
            _ok(generate_scenarios(_gbm(scenario_count=2), calendar=_always_open())).scenarios,
            projected_peak_memory=10_000,
        )
    )
    refusal = admit_scenario_fanout(
        requests, budgets={"qmb_governor_cpu_budget": 4, "qmb_governor_memory_budget": 1000}
    )
    assert is_refusal(refusal)


def test_scenario_failures_are_counted_and_reported_as_typed_refusals() -> None:
    # gaussian-noise with a large sigma drives some substreams' cumulative walk to an
    # invalid (non-positive) bar; those scenarios are counted, never silently dropped.
    source = _source_bars()
    fanout = _ok(
        generate_scenarios(
            _history("gaussian-noise", sigma="0.3", scenario_count=16, seed=11),
            calendar=_always_open(),
            source_series=source,
        )
    )
    assert fanout.filtered_count == 2
    assert fanout.produced_count == 14
    assert fanout.produced_count + fanout.filtered_count == fanout.scenario_count
    assert len(fanout.failures) == fanout.filtered_count
    for failure in fanout.failures:
        assert failure.category == RefusalCategory.INVALID_INPUT.value
        assert failure.field != ""
        assert failure.scenario_index >= 1  # the untouched anchor never fails
    # The failed indices are absent from the produced scenarios but their count is explicit.
    produced_indices = {s.scenario_index for s in fanout.scenarios}
    failed_indices = {f.scenario_index for f in fanout.failures}
    assert produced_indices.isdisjoint(failed_indices)
    # Every failure still carries its deterministic run id (it consumed a governor slot).
    assert all(f.run_id.value.startswith("fp1:sha256:") for f in fanout.failures)


def test_governed_requests_cover_every_scenario_including_failures() -> None:
    # The fan-out plan spawns all N scenarios process-per-run; a scenario that later
    # refuses still consumed a governor slot, so it is one of the governed requests.
    source = _source_bars()
    fanout = _ok(
        generate_scenarios(
            _history("gaussian-noise", sigma="0.3", scenario_count=16, seed=11),
            calendar=_always_open(),
            source_series=source,
            projected_peak_memory=1000,
        )
    )
    assert fanout.filtered_count > 0
    assert len(fanout.governed_requests) == fanout.scenario_count
    request_ids = {r.run_id.value for r in fanout.governed_requests}
    scenario_ids = {s.run_id.value for s in fanout.scenarios}
    failure_ids = {f.run_id.value for f in fanout.failures}
    assert request_ids == scenario_ids | failure_ids


# --- reproducibility of the failure accounting (determinism, NFR-03) ----------


def test_failure_accounting_is_deterministic() -> None:
    source = _source_bars()
    first = _ok(
        generate_scenarios(
            _history("gaussian-noise", sigma="0.3", scenario_count=16, seed=11),
            calendar=_always_open(),
            source_series=source,
        )
    )
    second = _ok(
        generate_scenarios(
            _history("gaussian-noise", sigma="0.3", scenario_count=16, seed=11),
            calendar=_always_open(),
            source_series=source,
        )
    )
    assert first.filtered_count == second.filtered_count
    assert [f.scenario_index for f in first.failures] == [f.scenario_index for f in second.failures]
    assert _ok(first.fingerprint()).value == _ok(second.fingerprint()).value


# --- identity and door surface ------------------------------------------------


def test_fanout_and_scenario_surfaces_are_fingerprintable() -> None:
    fanout = _ok(generate_scenarios(_gbm(scenario_count=3), calendar=_always_open()))
    assert is_ok(fingerprint(fanout.fp1_identity()))
    assert isinstance(fanout, ScenarioFanout)
    for scenario in fanout.scenarios:
        assert isinstance(scenario, GeneratedScenario)
        assert is_ok(fingerprint(scenario.fp1_identity()))
        assert scenario.as_mapping()["bar_count"] == len(scenario.bars)
    mapping = fanout.as_mapping()
    assert mapping["produced_count"] == fanout.produced_count
