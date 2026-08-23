"""Tier-2 tests for the CT-16 light/heavy benchmark harness (COMP-QMF-INDICATORS; Story 7.5).

These tests bind the story's second acceptance criterion: the benchmark harness measures a
configuration on **two rungs** — burst throughput and per-tick latency, per accepted input
observation at the configured BarSpec — with **the no-op tick path measured separately**, and
a **peak-memory regression fails the tier-2 gate exactly as a slowdown does**. The measuring
half is driven with an in-test kernel so the harness runs deterministically; the regression
gate is proven over constructed measurements so each axis (latency, throughput, memory) fails
closed independently.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar

from qmf.core import (
    CalendarIdentity,
    ExactRational,
    Instant,
    Instrument,
    Ok,
    RefusalCategory,
    Result,
    UnitKind,
    VenueId,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.indicators import (
    AlignmentPolicy,
    ArithmeticReference,
    BenchmarkBaseline,
    BenchmarkMeasurement,
    BenchmarkRung,
    ChannelKind,
    ConfiguredIndicator,
    InputSeries,
    KernelOutput,
    MissingValuePolicy,
    NoOpTickMeasurement,
    OutputArity,
    OutputChannel,
    PresenceState,
    QuoteSide,
    RegressionTolerance,
    RungMeasurement,
    SeriesInput,
    SnapshotScope,
    StreamingObservation,
    SupportedMode,
    _bench,
    compare_to_baseline,
    regression_gate,
)

T = TypeVar("T")


def _unwrap(result: Result[T]) -> T:
    assert is_ok(result), f"expected Ok, got {result}"
    return result.value


# --- fixtures ---------------------------------------------------------------


def _instrument() -> Instrument:
    return _unwrap(Instrument.try_create(_unwrap(VenueId.try_create("venue-ic")), "EURUSD"))


def _calendar() -> CalendarIdentity:
    return _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))


def _period(numerator: int = 2) -> ExactRational:
    return _unwrap(ExactRational.try_create(numerator, 1, UnitKind.COUNT))


def _series_input(name: str = "close") -> SeriesInput:
    return _unwrap(
        SeriesInput.try_create(
            name=name,
            source=_instrument(),
            bar_spec={"kind": "time-interval", "seconds": 60},
            channel_kind=ChannelKind.EXACT_PRICE,
            quote_side=QuoteSide.MID,
        )
    )


def _arithmetic_reference() -> ArithmeticReference:
    return _unwrap(
        ArithmeticReference.try_create(
            "ta-lib-c==0.7.1",
            "ta-lib==0.7.1",
            {"compatibility_mode": "default", "candle_settings": "reference-default"},
        )
    )


def _config(**overrides: object) -> ConfiguredIndicator:
    kwargs: dict[str, object] = {
        "formula_id": "sma",
        "contract_format_version": 1,
        "parameters": {"period": _period(2)},
        "inputs": [_series_input("close")],
        "calendar_requirements": [_calendar()],
        "alignment_policy": AlignmentPolicy.AS_OF,
        "missing_value_policy": MissingValuePolicy.MARK_GAP,
        "warm_up": 0,
        "output_schema": [
            _unwrap(
                OutputChannel.try_create(
                    "sma", ChannelKind.FLOAT_ANALYTIC, OutputArity.SCALAR_PER_SAMPLE, 0
                )
            )
        ],
        "supported_modes": [SupportedMode.BATCH, SupportedMode.STREAMING],
        "arithmetic_reference_configuration": _arithmetic_reference(),
    }
    kwargs.update(overrides)
    return _unwrap(ConfiguredIndicator.try_create(**kwargs))


def _writer() -> WriterId:
    return _unwrap(WriterId.try_create("m1", "indicator-feeder", "eurusd-sma", "boot-1"))


def _scope() -> SnapshotScope:
    return _unwrap(SnapshotScope.try_create("windows-11", "ta-lib==0.7.1"))


def _instants(count: int, start: int = 1_000) -> list[Instant]:
    return [_unwrap(Instant.try_create(start + step)) for step in range(count)]


def _input(scaled: list[int]) -> InputSeries:
    presence = [PresenceState.PRESENT] * len(scaled)
    return _unwrap(InputSeries.from_values(scaled, 2, presence, _instants(len(scaled))))


def _observations(scaled: list[int]) -> list[Mapping[str, StreamingObservation]]:
    updates: list[Mapping[str, StreamingObservation]] = []
    for step, value in enumerate(scaled):
        observation = _unwrap(
            StreamingObservation.try_create(
                value, PresenceState.PRESENT, _unwrap(Instant.try_create(1_000 + step))
            )
        )
        updates.append({"close": observation})
    return updates


class _EchoKernel:
    """A pure kernel echoing the primary dense input — deterministic timing workload."""

    def compute(
        self,
        dense_inputs: Mapping[str, tuple[int, ...]],
        input_scales: Mapping[str, int],
        configuration: ConfiguredIndicator,
    ) -> Result[KernelOutput]:
        primary = configuration.inputs[0].name
        channel = configuration.output_schema[0].name
        return Ok(KernelOutput(channels={channel: dense_inputs[primary]}, lookback=0, scale=2))


# --- AC2: the measuring harness records two rungs + the no-op tick separately ------


def test_measure_configuration_records_two_rungs_and_a_separate_noop() -> None:
    config = _config()
    scaled = [10, 20, 30, 40, 50]
    measurement = _unwrap(
        _bench.measure_configuration(
            config,
            {"close": _input(scaled)},
            _observations(scaled),
            kernel=_EchoKernel(),
            world=World.REPLAY,
            writer_id=_writer(),
            scope=_scope(),
            input_scales={"close": 2},
            noop_value=10,
            noop_presence=PresenceState.PRESENT,
            noop_knowable_ns=1_000,
            noop_iterations=25,
        )
    )
    # Two rungs, each denominated per accepted input observation.
    assert measurement.burst.rung is BenchmarkRung.BURST_THROUGHPUT
    assert measurement.burst.observations == len(scaled)
    assert measurement.latency.rung is BenchmarkRung.PER_TICK_LATENCY
    assert measurement.latency.observations == len(scaled)
    # The no-op tick path is measured separately, never folded into a rung.
    assert measurement.noop_tick.iterations == 25
    assert measurement.noop_tick.elapsed_ns >= 0
    # Peak memory is tracked; the fingerprint stamps the configuration measured.
    assert measurement.peak_bytes >= 0
    assert measurement.configuration_fingerprint == _unwrap(config.fp1()).value


def test_measure_burst_and_latency_individually() -> None:
    config = _config()
    scaled = [1, 2, 3, 4]
    burst = _unwrap(
        _bench.measure_burst(
            config, {"close": _input(scaled)}, kernel=_EchoKernel(), world=World.REPLAY, repeats=2
        )
    )
    assert burst.rung is BenchmarkRung.BURST_THROUGHPUT
    assert burst.observations == len(scaled) * 2  # repeats multiply the observation count
    latency = _unwrap(
        _bench.measure_latency(
            config,
            _observations(scaled),
            kernel=_EchoKernel(),
            world=World.REPLAY,
            writer_id=_writer(),
            scope=_scope(),
            input_scales={"close": 2},
        )
    )
    assert latency.rung is BenchmarkRung.PER_TICK_LATENCY
    assert latency.observations == len(scaled)


def test_measure_noop_tick_refuses_a_non_positive_iteration_count() -> None:
    assert is_refusal(_bench.measure_noop_tick(10, PresenceState.PRESENT, 1_000, iterations=0))


def test_measure_burst_propagates_a_missing_primary_column() -> None:
    refusal = _bench.measure_burst(
        _config(), {"other": _input([1, 2])}, kernel=_EchoKernel(), world=World.REPLAY
    )
    assert is_refusal(refusal) and refusal.context["field"] == "inputs"


# --- rung derived metrics ---------------------------------------------------


def test_rung_derived_metrics_are_exact_integer_quotients() -> None:
    latency = _unwrap(RungMeasurement.try_create(BenchmarkRung.PER_TICK_LATENCY, 10, 5_000, 100))
    assert latency.per_observation_ns() == 500
    burst = _unwrap(
        RungMeasurement.try_create(BenchmarkRung.BURST_THROUGHPUT, 2_000, 1_000_000_000, 100)
    )
    assert burst.throughput_per_second() == 2_000
    # Zero denominators degrade to zero, never a division error.
    empty = _unwrap(RungMeasurement.try_create(BenchmarkRung.BURST_THROUGHPUT, 0, 0, 0))
    assert empty.throughput_per_second() == 0
    assert empty.per_observation_ns() == 0


def test_rung_measurement_validation() -> None:
    assert is_refusal(RungMeasurement.try_create("nope", 1, 1, 1))
    assert is_refusal(RungMeasurement.try_create(BenchmarkRung.BURST_THROUGHPUT, -1, 1, 1))
    assert is_refusal(RungMeasurement.try_create(BenchmarkRung.BURST_THROUGHPUT, 1, -1, 1))
    assert is_refusal(RungMeasurement.try_create(BenchmarkRung.BURST_THROUGHPUT, 1, 1, -1))
    assert is_refusal(RungMeasurement.try_create(BenchmarkRung.BURST_THROUGHPUT, True, 1, 1))


def test_noop_per_tick_is_exact_and_zero_safe() -> None:
    noop = NoOpTickMeasurement(iterations=4, elapsed_ns=800, peak_bytes=10)
    assert noop.per_tick_ns() == 200
    assert NoOpTickMeasurement(iterations=0, elapsed_ns=0, peak_bytes=0).per_tick_ns() == 0


# --- the regression gate: constructed measurements --------------------------

_FINGERPRINT = "fp1:sha256:" + "0" * 64


def _measurement(
    *, latency_ns: int, throughput: int, peak_bytes: int, fingerprint: str = _FINGERPRINT
) -> BenchmarkMeasurement:
    latency = RungMeasurement(
        rung=BenchmarkRung.PER_TICK_LATENCY,
        observations=10,
        elapsed_ns=10 * latency_ns,
        peak_bytes=peak_bytes,
    )
    burst = RungMeasurement(
        rung=BenchmarkRung.BURST_THROUGHPUT,
        observations=throughput,
        elapsed_ns=1_000_000_000,
        peak_bytes=peak_bytes,
    )
    noop = NoOpTickMeasurement(iterations=100, elapsed_ns=100, peak_bytes=peak_bytes)
    return BenchmarkMeasurement(
        configuration_fingerprint=fingerprint,
        burst=burst,
        latency=latency,
        noop_tick=noop,
        peak_bytes=peak_bytes,
    )


def _baseline(
    *, latency_ns: int, throughput: int, peak_bytes: int, fingerprint: str = _FINGERPRINT
) -> BenchmarkBaseline:
    return _unwrap(
        BenchmarkBaseline.try_create(
            configuration_fingerprint=fingerprint,
            os="windows-11",
            cpu_class="x86-64-avx2",
            burst_throughput_per_second=throughput,
            per_tick_latency_ns=latency_ns,
            peak_bytes=peak_bytes,
        )
    )


def test_regression_gate_passes_when_within_budget() -> None:
    baseline = _baseline(latency_ns=500, throughput=2_000, peak_bytes=1_000)
    measured = _measurement(latency_ns=500, throughput=2_000, peak_bytes=1_000)
    report = _unwrap(regression_gate(baseline, measured))
    assert report.passed is True


def test_a_slowdown_fails_the_gate() -> None:
    baseline = _baseline(latency_ns=500, throughput=2_000, peak_bytes=1_000)
    measured = _measurement(latency_ns=600, throughput=2_000, peak_bytes=1_000)
    refusal = regression_gate(baseline, measured)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert "latency" in str(refusal.context["regressed"])


def test_a_throughput_drop_fails_the_gate() -> None:
    baseline = _baseline(latency_ns=500, throughput=2_000, peak_bytes=1_000)
    measured = _measurement(latency_ns=500, throughput=1_500, peak_bytes=1_000)
    refusal = regression_gate(baseline, measured)
    assert is_refusal(refusal)
    assert "throughput" in str(refusal.context["regressed"])


def test_a_peak_memory_regression_fails_the_gate_exactly_as_a_slowdown_does() -> None:
    baseline = _baseline(latency_ns=500, throughput=2_000, peak_bytes=1_000)
    measured = _measurement(latency_ns=500, throughput=2_000, peak_bytes=2_000)
    refusal = regression_gate(baseline, measured)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert "peak memory" in str(refusal.context["regressed"])


def test_tolerance_permits_a_declared_regression() -> None:
    baseline = _baseline(latency_ns=500, throughput=2_000, peak_bytes=1_000)
    measured = _measurement(latency_ns=550, throughput=1_900, peak_bytes=1_050)
    # 100 permille (10%) allows the 10% latency, 5% throughput, and 5% memory changes.
    tolerance = _unwrap(
        RegressionTolerance.try_create(
            latency_permille=100, throughput_permille=100, memory_permille=100
        )
    )
    assert _unwrap(regression_gate(baseline, measured, tolerance)).passed is True


def test_compare_to_baseline_reports_each_axis() -> None:
    baseline = _baseline(latency_ns=500, throughput=2_000, peak_bytes=1_000)
    measured = _measurement(latency_ns=600, throughput=1_500, peak_bytes=2_000)
    report = compare_to_baseline(baseline, measured)
    assert report.passed is False
    assert report.latency_regressed is True
    assert report.throughput_regressed is True
    assert report.memory_regressed is True
    assert report.measured_latency_ns == 600
    assert report.measured_throughput_per_second == 1_500
    assert report.measured_peak_bytes == 2_000


def test_regression_gate_refuses_a_fingerprint_mismatch_and_bad_arguments() -> None:
    baseline = _baseline(latency_ns=500, throughput=2_000, peak_bytes=1_000)
    other = _measurement(
        latency_ns=500, throughput=2_000, peak_bytes=1_000, fingerprint="fp1:sha256:" + "1" * 64
    )
    mismatch = regression_gate(baseline, other)
    assert is_refusal(mismatch) and mismatch.context["field"] == "configuration_fingerprint"
    assert is_refusal(
        regression_gate(object(), _measurement(latency_ns=1, throughput=1, peak_bytes=1))
    )
    assert is_refusal(regression_gate(baseline, object()))
    assert is_refusal(
        regression_gate(baseline, _measurement(latency_ns=1, throughput=1, peak_bytes=1), object())
    )


# --- value-type validation --------------------------------------------------


def test_baseline_validation() -> None:
    assert is_refusal(
        BenchmarkBaseline.try_create(
            configuration_fingerprint="  ",
            os="windows-11",
            cpu_class="x86-64",
            burst_throughput_per_second=1,
            per_tick_latency_ns=1,
            peak_bytes=1,
        )
    )
    assert is_refusal(
        BenchmarkBaseline.try_create(
            configuration_fingerprint=_FINGERPRINT,
            os="",
            cpu_class="x86-64",
            burst_throughput_per_second=1,
            per_tick_latency_ns=1,
            peak_bytes=1,
        )
    )
    assert is_refusal(
        BenchmarkBaseline.try_create(
            configuration_fingerprint=_FINGERPRINT,
            os="windows-11",
            cpu_class="  ",
            burst_throughput_per_second=1,
            per_tick_latency_ns=1,
            peak_bytes=1,
        )
    )
    assert is_refusal(
        BenchmarkBaseline.try_create(
            configuration_fingerprint=_FINGERPRINT,
            os="windows-11",
            cpu_class="x86-64",
            burst_throughput_per_second=-1,
            per_tick_latency_ns=1,
            peak_bytes=1,
        )
    )
    assert is_refusal(
        BenchmarkBaseline.try_create(
            configuration_fingerprint=_FINGERPRINT,
            os="windows-11",
            cpu_class="x86-64",
            burst_throughput_per_second=1,
            per_tick_latency_ns=-1,
            peak_bytes=1,
        )
    )
    assert is_refusal(
        BenchmarkBaseline.try_create(
            configuration_fingerprint=_FINGERPRINT,
            os="windows-11",
            cpu_class="x86-64",
            burst_throughput_per_second=1,
            per_tick_latency_ns=1,
            peak_bytes=-1,
        )
    )


def test_tolerance_validation() -> None:
    assert is_refusal(RegressionTolerance.try_create(latency_permille=-1))
    assert is_refusal(RegressionTolerance.try_create(throughput_permille=-1))
    assert is_refusal(RegressionTolerance.try_create(memory_permille=-1))
    tolerance = _unwrap(RegressionTolerance.try_create())
    assert tolerance.latency_permille == 0
