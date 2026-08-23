"""Tier-2 tests for the CT-16 light/heavy budget verdict and the synchronous-entry gate
(COMP-QMF-INDICATORS; Story 7.5).

These tests bind the story's third acceptance criterion: a configuration claiming light
**without a recorded live-path rung baseline, or whose benchmark misses a declared bound, is
refused** at the tier-2 gate; **every configuration is heavy by default**; and a **heavy
configuration's synchronous entry point returns ``unsupported capability``** (FM-3, FM-6).
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    CalendarIdentity,
    ExactRational,
    Instrument,
    RefusalCategory,
    Result,
    UnitKind,
    VenueId,
    is_ok,
    is_refusal,
)
from qmf.indicators import (
    AlignmentPolicy,
    ArithmeticReference,
    BenchmarkBaseline,
    BenchmarkMeasurement,
    BenchmarkRung,
    BudgetVerdict,
    ChannelKind,
    ConfiguredIndicator,
    DeclaredBudget,
    LightHeavyVerdict,
    MissingValuePolicy,
    NoOpTickMeasurement,
    OutputArity,
    OutputChannel,
    QuoteSide,
    RegressionTolerance,
    RungMeasurement,
    SeriesInput,
    SupportedMode,
    evaluate_light_claim,
    guard_synchronous_entry,
)

T = TypeVar("T")


def _unwrap(result: Result[T]) -> T:
    assert is_ok(result), f"expected Ok, got {result}"
    return result.value


# --- fixtures ---------------------------------------------------------------


def _series_input() -> SeriesInput:
    instrument = _unwrap(Instrument.try_create(_unwrap(VenueId.try_create("venue-ic")), "EURUSD"))
    return _unwrap(
        SeriesInput.try_create(
            name="close",
            source=instrument,
            bar_spec={"kind": "time-interval", "seconds": 60},
            channel_kind=ChannelKind.EXACT_PRICE,
            quote_side=QuoteSide.MID,
        )
    )


def _budget(*, bounded_state: bool = True, synchronous_availability: bool = True) -> DeclaredBudget:
    return _unwrap(
        DeclaredBudget.try_create(
            per_update_cost_rung="live-path",
            bounded_state=bounded_state,
            window_or_anchor_rule="bounded-window-200",
            synchronous_availability=synchronous_availability,
        )
    )


def _config(**overrides: object) -> ConfiguredIndicator:
    kwargs: dict[str, object] = {
        "formula_id": "sma",
        "contract_format_version": 1,
        "parameters": {"period": _unwrap(ExactRational.try_create(2, 1, UnitKind.COUNT))},
        "inputs": [_series_input()],
        "calendar_requirements": [
            _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))
        ],
        "alignment_policy": AlignmentPolicy.AS_OF,
        "missing_value_policy": MissingValuePolicy.MARK_GAP,
        "warm_up": 1,
        "output_schema": [
            _unwrap(
                OutputChannel.try_create(
                    "sma", ChannelKind.FLOAT_ANALYTIC, OutputArity.SCALAR_PER_SAMPLE, 0
                )
            )
        ],
        "supported_modes": [SupportedMode.BATCH, SupportedMode.STREAMING],
        "arithmetic_reference_configuration": _unwrap(
            ArithmeticReference.try_create(
                "ta-lib-c==0.7.1",
                "ta-lib==0.7.1",
                {"compatibility_mode": "default", "candle_settings": "reference-default"},
            )
        ),
    }
    kwargs.update(overrides)
    return _unwrap(ConfiguredIndicator.try_create(**kwargs))


def _fp(config: ConfiguredIndicator) -> str:
    return _unwrap(config.fp1()).value


def _baseline(config: ConfiguredIndicator) -> BenchmarkBaseline:
    return _unwrap(
        BenchmarkBaseline.try_create(
            configuration_fingerprint=_fp(config),
            os="windows-11",
            cpu_class="x86-64-avx2",
            burst_throughput_per_second=2_000,
            per_tick_latency_ns=500,
            peak_bytes=1_000,
        )
    )


def _measurement(
    config: ConfiguredIndicator, *, latency_ns: int = 500, peak_bytes: int = 1_000
) -> BenchmarkMeasurement:
    latency = RungMeasurement(
        rung=BenchmarkRung.PER_TICK_LATENCY,
        observations=10,
        elapsed_ns=10 * latency_ns,
        peak_bytes=peak_bytes,
    )
    burst = RungMeasurement(
        rung=BenchmarkRung.BURST_THROUGHPUT,
        observations=2_000,
        elapsed_ns=1_000_000_000,
        peak_bytes=peak_bytes,
    )
    noop = NoOpTickMeasurement(iterations=100, elapsed_ns=100, peak_bytes=peak_bytes)
    return BenchmarkMeasurement(
        configuration_fingerprint=_fp(config),
        burst=burst,
        latency=latency,
        noop_tick=noop,
        peak_bytes=peak_bytes,
    )


# --- heavy by default -------------------------------------------------------


def test_a_configuration_with_no_declared_budget_is_heavy_by_default() -> None:
    verdict = _unwrap(evaluate_light_claim(_config()))
    assert verdict.verdict is LightHeavyVerdict.HEAVY
    assert verdict.reasons  # a display-only rationale is carried


# --- FM-6: a light claim without a baseline or a proven bound is refused ------


def test_claiming_light_without_a_recorded_baseline_is_refused() -> None:
    config = _config(declared_budget=_budget())
    refusal = evaluate_light_claim(config)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert refusal.context["field"] == "declared_budget"


def test_claiming_light_without_a_measurement_is_refused() -> None:
    config = _config(declared_budget=_budget())
    refusal = evaluate_light_claim(config, baseline=_baseline(config))
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION


def test_claiming_light_with_an_unbounded_state_bound_is_refused() -> None:
    config = _config(declared_budget=_budget(bounded_state=False))
    refusal = evaluate_light_claim(
        config, baseline=_baseline(config), measurement=_measurement(config)
    )
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION


def test_claiming_light_without_synchronous_availability_is_refused() -> None:
    config = _config(declared_budget=_budget(synchronous_availability=False))
    refusal = evaluate_light_claim(
        config, baseline=_baseline(config), measurement=_measurement(config)
    )
    assert is_refusal(refusal)


def test_claiming_light_whose_benchmark_regresses_is_refused() -> None:
    config = _config(declared_budget=_budget())
    slow = _measurement(config, latency_ns=5_000)  # far past the baseline's 500ns
    refusal = evaluate_light_claim(config, baseline=_baseline(config), measurement=slow)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION


# --- a proven light claim ----------------------------------------------------


def test_a_proven_light_claim_is_light() -> None:
    config = _config(declared_budget=_budget())
    verdict = _unwrap(
        evaluate_light_claim(config, baseline=_baseline(config), measurement=_measurement(config))
    )
    assert verdict.verdict is LightHeavyVerdict.LIGHT
    assert verdict.reasons


def test_a_light_claim_honours_a_tolerance() -> None:
    config = _config(declared_budget=_budget())
    measured = _measurement(config, latency_ns=550, peak_bytes=1_050)
    tolerance = _unwrap(RegressionTolerance.try_create(latency_permille=100, memory_permille=100))
    verdict = _unwrap(
        evaluate_light_claim(
            config, baseline=_baseline(config), measurement=measured, tolerance=tolerance
        )
    )
    assert verdict.verdict is LightHeavyVerdict.LIGHT


# --- validation -------------------------------------------------------------


def test_evaluate_light_claim_validation() -> None:
    assert is_refusal(evaluate_light_claim(object()))
    config = _config(declared_budget=_budget())
    assert is_refusal(evaluate_light_claim(config, baseline=object()))
    assert is_refusal(
        evaluate_light_claim(config, baseline=_baseline(config), measurement=object())
    )
    assert is_refusal(
        evaluate_light_claim(
            config,
            baseline=_baseline(config),
            measurement=_measurement(config),
            tolerance=object(),
        )
    )


# --- FM-3: the synchronous-entry gate ---------------------------------------


def test_a_heavy_configurations_synchronous_entry_is_unsupported() -> None:
    heavy = _unwrap(evaluate_light_claim(_config()))
    refusal = guard_synchronous_entry(heavy)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refusal.context["field"] == "synchronous_entry"


def test_a_light_configurations_synchronous_entry_is_permitted() -> None:
    config = _config(declared_budget=_budget())
    light = _unwrap(
        evaluate_light_claim(config, baseline=_baseline(config), measurement=_measurement(config))
    )
    assert is_ok(guard_synchronous_entry(light))


def test_guard_synchronous_entry_refuses_a_non_verdict() -> None:
    assert is_refusal(guard_synchronous_entry(object()))
    # A direct heavy verdict value also gates.
    assert is_refusal(guard_synchronous_entry(BudgetVerdict(LightHeavyVerdict.HEAVY, ("x",))))
