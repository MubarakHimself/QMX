"""The measuring half of the CT-16 light/heavy benchmark harness (AR-22 / NFR-04;
COMP-QMF-INDICATORS; Story 7.5).

This private module is the **only** code in the package that reads a clock or allocates a
timed workload; the pure value types and the regression gate live in
:mod:`qmf.indicators.benchmark`. It measures a configuration on the two CT-16 rungs — burst
throughput over a whole series (the batch path) and per-tick latency over incremental
updates (the streaming/live path) — with the no-op tick path measured separately, and it
tracks peak traced memory so a peak-memory regression is caught exactly as a slowdown is
(DEC-0111, DEC-0126, DEC-0128).

The harness measures **caller-supplied** inputs and observations: it constructs no market
data of its own, and it takes the configuration, the canonical-arithmetic kernel, the feeder
identity, and the accumulated observations from the caller (the tier-2 benchmark test). It
carries the same standing as the unit tests — a test exercises it every run — and its
measurements become the fingerprinted ``(OS, CPU-class)`` baselines a light claim is proven
against (:class:`~qmf.indicators.benchmark.BenchmarkBaseline`).

Every quantity is an integer: elapsed times are ``perf_counter_ns`` nanosecond deltas and
memory is ``tracemalloc`` peak bytes — no binary float appears. The clock reads are marked
with the ``# ambient-scan: allow`` directive the AR-16 gate requires for a benchmark
harness. Stdlib plus ``qmf-core`` and this package's own modules only.
"""

from __future__ import annotations

import time
import tracemalloc
from collections.abc import Callable, Mapping, Sequence

from qmf.core import (
    Instant,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    World,
    WriterId,
    is_refusal,
)
from qmf.indicators.batch import BatchKernel, compute_batch
from qmf.indicators.benchmark import (
    BenchmarkMeasurement,
    BenchmarkRung,
    NoOpTickMeasurement,
    RungMeasurement,
)
from qmf.indicators.configured_indicator import ConfiguredIndicator
from qmf.indicators.series import InputSeries, PresenceState
from qmf.indicators.streaming import SnapshotScope, StreamingIndicator, StreamingObservation

# The default no-op tick iteration count for the self-standing probe — enough to time the
# accept-a-tick plumbing away from measurement noise without dominating a suite run.
DEFAULT_NOOP_ITERATIONS = 200


def _timed(work: Callable[[], TypedRefusal | None]) -> tuple[int, int, TypedRefusal | None]:
    """Run ``work`` once under tracemalloc, returning ``(elapsed_ns, peak_bytes, refusal)``.

    ``work`` returns a refusal to abort the measurement (an underlying compute refused) or
    ``None`` on success; the timing and peak-memory reading are taken regardless so a partial
    run is never reported as a clean zero.
    """
    tracemalloc.start()
    start = time.perf_counter_ns()  # ambient-scan: allow - AR-22 benchmark wall-clock
    refusal = work()
    elapsed = time.perf_counter_ns() - start  # ambient-scan: allow - AR-22 benchmark wall-clock
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak_bytes, refusal


def measure_burst(
    configuration: ConfiguredIndicator,
    inputs: Mapping[str, InputSeries],
    *,
    kernel: BatchKernel,
    world: World,
    repeats: int = 1,
) -> Result[RungMeasurement]:
    """Measure the burst-throughput rung — batch over the whole series, ``repeats`` times.

    Observations counted is the primary column length times ``repeats`` (accepted input
    observations at the configured BarSpec). Any underlying batch refusal is returned.
    """
    if not configuration.inputs:  # pragma: no cover - a valid configuration always has inputs
        return _bad("inputs", "the configuration declares no inputs")
    primary = configuration.inputs[0].name
    primary_column = inputs.get(primary)
    if primary_column is None:
        return _bad("inputs", "the primary input column was not supplied", input=primary)
    observations = primary_column.length * repeats

    def _work() -> TypedRefusal | None:
        for _ in range(repeats):
            result = compute_batch(configuration, inputs, kernel=kernel, world=world)
            if is_refusal(result):
                return result
        return None

    elapsed, peak_bytes, refusal = _timed(_work)
    if refusal is not None:
        return refusal
    return RungMeasurement.try_create(
        BenchmarkRung.BURST_THROUGHPUT, observations, elapsed, peak_bytes
    )


def measure_latency(
    configuration: ConfiguredIndicator,
    observations: Sequence[Mapping[str, StreamingObservation]],
    *,
    kernel: BatchKernel,
    world: World,
    writer_id: WriterId,
    scope: SnapshotScope,
    input_scales: Mapping[str, int],
) -> Result[RungMeasurement]:
    """Measure the per-tick-latency rung — one streaming update per accepted observation.

    Feeds each observation mapping through a fresh :class:`~qmf.indicators.StreamingIndicator`
    and times the whole feed; the rung is denominated per accepted input observation. Any
    creation or update refusal is returned.
    """
    created = StreamingIndicator.try_create(
        configuration,
        kernel=kernel,
        world=world,
        writer_id=writer_id,
        scope=scope,
        input_scales=input_scales,
    )
    if is_refusal(created):
        return created
    stream = created.value
    count = len(observations)

    def _work() -> TypedRefusal | None:
        for update in observations:
            fed = stream.update(update)
            if is_refusal(fed):
                return fed
        return None

    elapsed, peak_bytes, refusal = _timed(_work)
    if refusal is not None:
        return refusal
    return RungMeasurement.try_create(BenchmarkRung.PER_TICK_LATENCY, count, elapsed, peak_bytes)


def measure_noop_tick(
    value: int,
    presence: PresenceState,
    knowable_ns: int,
    *,
    iterations: int = DEFAULT_NOOP_ITERATIONS,
) -> Result[NoOpTickMeasurement]:
    """Measure the no-op tick path separately — accept an observation, do no arithmetic.

    Times the accept-a-tick plumbing: constructing the instant and validating a
    :class:`~qmf.indicators.StreamingObservation` ``iterations`` times, with no kernel run.
    Isolating it makes the per-tick-latency rung's arithmetic cost attributable (CT-16;
    DEC-0111). Refuses a non-positive iteration count.
    """
    if iterations < 1:
        return _bad("iterations", "the no-op probe runs at least once", given=iterations)

    def _work() -> TypedRefusal | None:
        for _ in range(iterations):
            instant = Instant.try_create(knowable_ns)
            if is_refusal(instant):
                return instant
            observation = StreamingObservation.try_create(value, presence, instant.value)
            if is_refusal(observation):
                return observation
        return None

    elapsed, peak_bytes, refusal = _timed(_work)
    if refusal is not None:
        return refusal
    return Ok(NoOpTickMeasurement(iterations=iterations, elapsed_ns=elapsed, peak_bytes=peak_bytes))


def measure_configuration(
    configuration: ConfiguredIndicator,
    inputs: Mapping[str, InputSeries],
    observations: Sequence[Mapping[str, StreamingObservation]],
    *,
    kernel: BatchKernel,
    world: World,
    writer_id: WriterId,
    scope: SnapshotScope,
    input_scales: Mapping[str, int],
    noop_value: int,
    noop_presence: PresenceState,
    noop_knowable_ns: int,
    burst_repeats: int = 1,
    noop_iterations: int = DEFAULT_NOOP_ITERATIONS,
) -> Result[BenchmarkMeasurement]:
    """Measure one configuration on both rungs plus the no-op tick path (CT-16; DEC-0111).

    Runs the burst rung (batch), the per-tick-latency rung (streaming), and the separate
    no-op tick probe, then assembles a :class:`~qmf.indicators.benchmark.BenchmarkMeasurement`
    stamped with the configuration's ``fp1`` and the overall peak memory (the max across the
    three measurements). Any underlying refusal is returned.
    """
    fingerprint = configuration.fp1()
    if is_refusal(fingerprint):  # pragma: no cover - a valid configuration always fingerprints
        return fingerprint
    burst = measure_burst(configuration, inputs, kernel=kernel, world=world, repeats=burst_repeats)
    if is_refusal(burst):
        return burst
    latency = measure_latency(
        configuration,
        observations,
        kernel=kernel,
        world=world,
        writer_id=writer_id,
        scope=scope,
        input_scales=input_scales,
    )
    if is_refusal(latency):
        return latency
    noop = measure_noop_tick(
        noop_value, noop_presence, noop_knowable_ns, iterations=noop_iterations
    )
    if is_refusal(noop):
        return noop
    peak_bytes = max(burst.value.peak_bytes, latency.value.peak_bytes, noop.value.peak_bytes)
    return Ok(
        BenchmarkMeasurement(
            configuration_fingerprint=fingerprint.value.value,
            burst=burst.value,
            latency=latency.value,
            noop_tick=noop.value,
            peak_bytes=peak_bytes,
        )
    )


def _bad(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal the measuring harness returns for a bad argument."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT, retryability=Retryability.NO, context=context
    )
