"""CT-16 — the light/heavy benchmark harness value types and the regression gate
(COMP-QMF-INDICATORS; Story 7.5).

The package ships a benchmark harness with **the same standing as its unit tests**
(DEC-0111, DEC-0126, DEC-0128). It measures a configuration on **two rungs** — burst
throughput and per-tick latency, each denominated **per accepted input observation at the
configured BarSpec** — with **the no-op tick path measured separately**, and it tracks
peak memory so that **a peak-memory regression fails the tier-2 gate exactly as a
slowdown does**.

This module lands the harness's *pure* surface: the rung value types the measuring harness
(:mod:`qmf.indicators._bench`) fills in, the recorded ``(OS, CPU-class)``-scoped baseline a
light claim rests on, an integer-permille regression tolerance, and the
:func:`regression_gate` that compares a fresh measurement to its baseline and **refuses**
when latency, throughput, **or** peak memory has regressed past the declared tolerance.
The measuring harness — the only code that reads a clock or allocates a workload — is kept
private to :mod:`qmf.indicators._bench`; everything here is pure integer arithmetic over
values the harness produced, so the public surface reads no clock and holds no state.

Every number is an **integer**: elapsed times are ``int`` nanoseconds, throughput is
observations per second as an ``int``, memory is ``int`` bytes, and tolerances are integer
**permille** (parts per thousand) — never a binary float, never decimal text (CT-16
``units``; DEC-0105, DEC-0127). Derived metrics use exact integer division.

Default-deny holds: this module imports **only** ``qmf.core``. Public value types are
frozen dataclasses and every operation succeeds or RETURNS a CT-04 typed refusal
(DEC-0101, DEC-0109, DEC-0120).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from qmf.core import Ok, RefusalCategory, Result, Retryability, TypedRefusal

__all__ = [
    "PERMILLE",
    "BenchmarkBaseline",
    "BenchmarkMeasurement",
    "BenchmarkRung",
    "NoOpTickMeasurement",
    "RegressionReport",
    "RegressionTolerance",
    "RungMeasurement",
    "compare_to_baseline",
    "regression_gate",
]

# One thousand parts — the fixed-point base for every tolerance in this module. A
# tolerance is an integer count of parts per thousand (e.g. 50 permille = a 5% allowance),
# so the comparison stays exact integer arithmetic with no binary float and no decimal text
# (CT-16 ``units``; DEC-0127).
PERMILLE: Final[int] = 1000

# Nanoseconds in one second, for the throughput denominator (observations per second).
_NS_PER_SECOND: Final[int] = 1_000_000_000


class BenchmarkRung(StrEnum):
    """The two benchmark rungs a measurement records (CT-16; DEC-0111, DEC-0126).

    ``burst-throughput`` — how many accepted input observations the configuration processes
    per second in a whole-series burst (the batch path). ``per-tick-latency`` — the wall
    time one accepted input observation costs on the incremental (live) path, denominated
    per accepted input observation at the configured BarSpec. The no-op tick path is a
    third, separate measurement (:class:`NoOpTickMeasurement`), never folded into either
    rung.
    """

    BURST_THROUGHPUT = "burst-throughput"
    PER_TICK_LATENCY = "per-tick-latency"


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a benchmark value factory returns (CT-04)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT, retryability=Retryability.NO, context=context
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``policy rejection`` refusal the regression gate returns (CT-04).

    A latency slowdown, a throughput drop, or a peak-memory growth past the declared
    tolerance is a benchmark-budget policy violation — the tier-2 gate fails closed on it,
    a peak-memory regression exactly as a slowdown does (CT-16; DEC-0111, DEC-0128).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION, retryability=Retryability.NO, context=context
    )


def _nonneg_int(value: object) -> int | None:
    """Return ``value`` as a genuine non-negative ``int`` (a ``bool`` is rejected), else
    ``None`` — every benchmark quantity is a non-negative integer count."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``."""
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


# --- one rung's raw measurement ---------------------------------------------


@dataclass(frozen=True, slots=True)
class RungMeasurement:
    """One benchmark rung's raw measurement (CT-16; DEC-0111, DEC-0126).

    ``observations`` is the count of accepted input observations measured at the configured
    BarSpec; ``elapsed_ns`` is the total wall time the rung took; ``peak_bytes`` is the peak
    traced memory during it. The derived metrics — :meth:`throughput_per_second` and
    :meth:`per_observation_ns` — are exact integer quotients, so a rung is denominated per
    accepted input observation without a binary float ever appearing.
    """

    rung: BenchmarkRung
    observations: int
    elapsed_ns: int
    peak_bytes: int

    def throughput_per_second(self) -> int:
        """Accepted input observations per second (0 when no time elapsed)."""
        if self.elapsed_ns <= 0:
            return 0
        return self.observations * _NS_PER_SECOND // self.elapsed_ns

    def per_observation_ns(self) -> int:
        """Wall nanoseconds per accepted input observation (0 when none measured)."""
        if self.observations <= 0:
            return 0
        return self.elapsed_ns // self.observations

    @classmethod
    def try_create(
        cls, rung: object, observations: object, elapsed_ns: object, peak_bytes: object
    ) -> Result[RungMeasurement]:
        """Validate and build a :class:`RungMeasurement`, returning value-or-refusal."""
        resolved_rung = rung if isinstance(rung, BenchmarkRung) else _coerce_rung(rung)
        if resolved_rung is None:
            return _invalid(
                "rung",
                "the rung is one of the closed set",
                given=repr(rung),
                allowed=[member.value for member in BenchmarkRung],
            )
        obs = _nonneg_int(observations)
        if obs is None:
            return _invalid(
                "observations",
                "observations is a non-negative integer count of accepted input observations",
                given=repr(observations),
            )
        elapsed = _nonneg_int(elapsed_ns)
        if elapsed is None:
            return _invalid(
                "elapsed_ns",
                "elapsed_ns is a non-negative integer nanosecond count",
                given=repr(elapsed_ns),
            )
        peak = _nonneg_int(peak_bytes)
        if peak is None:
            return _invalid(
                "peak_bytes",
                "peak_bytes is a non-negative integer byte count",
                given=repr(peak_bytes),
            )
        return Ok(cls(rung=resolved_rung, observations=obs, elapsed_ns=elapsed, peak_bytes=peak))


def _coerce_rung(value: object) -> BenchmarkRung | None:
    if isinstance(value, str):
        try:
            return BenchmarkRung(value)
        except ValueError:
            return None
    return None


# --- the separately-measured no-op tick path --------------------------------


@dataclass(frozen=True, slots=True)
class NoOpTickMeasurement:
    """The no-op tick path, measured separately (CT-16; DEC-0111, DEC-0126).

    The fixed per-tick overhead of accepting one input observation with no arithmetic
    performed — the delivery/validation plumbing, isolated so the per-tick-latency rung's
    arithmetic cost is attributable. Never folded into a rung; it is reported on its own.
    """

    iterations: int
    elapsed_ns: int
    peak_bytes: int

    def per_tick_ns(self) -> int:
        """Wall nanoseconds per no-op tick (0 when none measured)."""
        if self.iterations <= 0:
            return 0
        return self.elapsed_ns // self.iterations


# --- a full measurement of one configuration --------------------------------


@dataclass(frozen=True, slots=True)
class BenchmarkMeasurement:
    """A full benchmark measurement of one configuration (CT-16; DEC-0111, DEC-0126).

    ``configuration_fingerprint`` is the ``fp1`` of the measured configuration (a
    display-only scoping value here — the verdict is machine-scoped and never identity).
    ``burst`` and ``latency`` are the two rungs; ``noop_tick`` is the separately-measured
    no-op tick path; ``peak_bytes`` is the overall peak traced memory across the run.
    """

    configuration_fingerprint: str
    burst: RungMeasurement
    latency: RungMeasurement
    noop_tick: NoOpTickMeasurement
    peak_bytes: int


# --- the recorded live-path rung baseline -----------------------------------


@dataclass(frozen=True, slots=True)
class BenchmarkBaseline:
    """A recorded ``(OS, CPU-class)``-scoped baseline for a configuration (CT-16; DEC-0128).

    The **recorded live-path rung baseline** a light claim rests on: the accepted
    burst-throughput, per-tick-latency, and peak-memory numbers for one configuration on
    one ``(os, cpu_class)`` tuple. The verdict a baseline supports is machine-scoped and
    display-only, **never** part of the configuration's ``fp1`` identity (DEC-0128). A
    configuration is heavy by default until such a baseline is recorded.
    """

    configuration_fingerprint: str
    os: str
    cpu_class: str
    burst_throughput_per_second: int
    per_tick_latency_ns: int
    peak_bytes: int

    @classmethod
    def try_create(
        cls,
        *,
        configuration_fingerprint: object,
        os: object,
        cpu_class: object,
        burst_throughput_per_second: object,
        per_tick_latency_ns: object,
        peak_bytes: object,
    ) -> Result[BenchmarkBaseline]:
        """Validate and build a :class:`BenchmarkBaseline`, returning value-or-refusal."""
        fingerprint_token = _clean_str(configuration_fingerprint)
        if fingerprint_token is None:
            return _invalid(
                "configuration_fingerprint",
                "the baseline names the measured configuration's fingerprint",
                given=repr(configuration_fingerprint),
            )
        os_token = _clean_str(os)
        if os_token is None:
            return _invalid(
                "os", "the baseline is scoped to a non-empty OS identity", given=repr(os)
            )
        cpu_token = _clean_str(cpu_class)
        if cpu_token is None:
            return _invalid(
                "cpu_class",
                "the baseline is scoped to a non-empty CPU-class identity",
                given=repr(cpu_class),
            )
        throughput = _nonneg_int(burst_throughput_per_second)
        if throughput is None:
            return _invalid(
                "burst_throughput_per_second",
                "burst throughput is a non-negative integer of observations per second",
                given=repr(burst_throughput_per_second),
            )
        latency = _nonneg_int(per_tick_latency_ns)
        if latency is None:
            return _invalid(
                "per_tick_latency_ns",
                "per-tick latency is a non-negative integer nanosecond count",
                given=repr(per_tick_latency_ns),
            )
        peak = _nonneg_int(peak_bytes)
        if peak is None:
            return _invalid(
                "peak_bytes",
                "peak_bytes is a non-negative integer byte count",
                given=repr(peak_bytes),
            )
        return Ok(
            cls(
                configuration_fingerprint=fingerprint_token,
                os=os_token,
                cpu_class=cpu_token,
                burst_throughput_per_second=throughput,
                per_tick_latency_ns=latency,
                peak_bytes=peak,
            )
        )


# --- the regression tolerance -----------------------------------------------


@dataclass(frozen=True, slots=True)
class RegressionTolerance:
    """The permitted regression per axis, in integer permille (CT-16; DEC-0111, DEC-0128).

    ``latency_permille`` is the allowed per-tick-latency slowdown, ``throughput_permille``
    the allowed burst-throughput drop, and ``memory_permille`` the allowed peak-memory
    growth — each parts per thousand of the baseline. The default is 0 (no regression
    permitted). Integer permille only: never a binary float, never decimal text.
    """

    latency_permille: int = 0
    throughput_permille: int = 0
    memory_permille: int = 0

    @classmethod
    def try_create(
        cls,
        latency_permille: object = 0,
        throughput_permille: object = 0,
        memory_permille: object = 0,
    ) -> Result[RegressionTolerance]:
        """Validate and build a :class:`RegressionTolerance`, returning value-or-refusal."""
        latency = _nonneg_int(latency_permille)
        throughput = _nonneg_int(throughput_permille)
        memory = _nonneg_int(memory_permille)
        if latency is None or throughput is None or memory is None:
            return _invalid(
                "tolerance",
                "each tolerance is a non-negative integer permille (parts per thousand)",
                latency_permille=repr(latency_permille),
                throughput_permille=repr(throughput_permille),
                memory_permille=repr(memory_permille),
            )
        return Ok(
            cls(
                latency_permille=latency,
                throughput_permille=throughput,
                memory_permille=memory,
            )
        )


# --- the comparison report --------------------------------------------------


@dataclass(frozen=True, slots=True)
class RegressionReport:
    """The per-axis outcome of comparing a measurement to its baseline (CT-16; DEC-0111).

    ``passed`` is true only when none of the three axes regressed. Each axis flag records
    whether that axis exceeded its tolerance: a latency slowdown, a throughput drop, or a
    peak-memory growth. A peak-memory regression is a first-class failure, exactly as a
    slowdown is.
    """

    passed: bool
    latency_regressed: bool
    throughput_regressed: bool
    memory_regressed: bool
    measured_latency_ns: int
    allowed_latency_ns: int
    measured_throughput_per_second: int
    allowed_throughput_per_second: int
    measured_peak_bytes: int
    allowed_peak_bytes: int


def compare_to_baseline(
    baseline: BenchmarkBaseline,
    measurement: BenchmarkMeasurement,
    tolerance: RegressionTolerance | None = None,
) -> RegressionReport:
    """Compare a measurement to its baseline on all three axes (pure; CT-16; DEC-0111).

    The per-tick-latency rung must not exceed ``baseline * (1000 + latency_permille) /
    1000``; the burst-throughput rung must not fall below ``baseline * (1000 -
    throughput_permille) / 1000``; and peak memory must not exceed ``baseline * (1000 +
    memory_permille) / 1000`` — every bound exact integer arithmetic. Returns a
    :class:`RegressionReport`; :func:`regression_gate` turns a non-passing report into the
    tier-2 refusal.
    """
    resolved = tolerance if tolerance is not None else RegressionTolerance()
    measured_latency = measurement.latency.per_observation_ns()
    allowed_latency = (
        baseline.per_tick_latency_ns * (PERMILLE + resolved.latency_permille) // PERMILLE
    )
    latency_regressed = measured_latency > allowed_latency
    measured_throughput = measurement.burst.throughput_per_second()
    allowed_throughput = (
        baseline.burst_throughput_per_second * (PERMILLE - resolved.throughput_permille) // PERMILLE
    )
    throughput_regressed = measured_throughput < allowed_throughput
    measured_memory = measurement.peak_bytes
    allowed_memory = baseline.peak_bytes * (PERMILLE + resolved.memory_permille) // PERMILLE
    memory_regressed = measured_memory > allowed_memory
    return RegressionReport(
        passed=not (latency_regressed or throughput_regressed or memory_regressed),
        latency_regressed=latency_regressed,
        throughput_regressed=throughput_regressed,
        memory_regressed=memory_regressed,
        measured_latency_ns=measured_latency,
        allowed_latency_ns=allowed_latency,
        measured_throughput_per_second=measured_throughput,
        allowed_throughput_per_second=allowed_throughput,
        measured_peak_bytes=measured_memory,
        allowed_peak_bytes=allowed_memory,
    )


def regression_gate(
    baseline: object,
    measurement: object,
    tolerance: object = None,
) -> Result[RegressionReport]:
    """The tier-2 benchmark gate — fail closed on any regression (CT-16; DEC-0111, DEC-0128).

    Validates the arguments, refuses if the measurement's configuration fingerprint does
    not match the baseline's (a baseline attests exactly one configuration), then compares
    on all three axes. Returns the passing :class:`RegressionReport` on success, or a
    ``policy rejection`` refusal naming every regressed axis with its measured and allowed
    values — a peak-memory regression fails the gate exactly as a slowdown does.
    """
    if not isinstance(baseline, BenchmarkBaseline):
        return _invalid("baseline", "a BenchmarkBaseline is required", given=repr(baseline))
    if not isinstance(measurement, BenchmarkMeasurement):
        return _invalid(
            "measurement", "a BenchmarkMeasurement is required", given=repr(measurement)
        )
    resolved_tolerance: RegressionTolerance
    if tolerance is None:
        resolved_tolerance = RegressionTolerance()
    elif isinstance(tolerance, RegressionTolerance):
        resolved_tolerance = tolerance
    else:
        return _invalid(
            "tolerance", "a RegressionTolerance is required (or omit it)", given=repr(tolerance)
        )
    if baseline.configuration_fingerprint != measurement.configuration_fingerprint:
        return _invalid(
            "configuration_fingerprint",
            "the measurement and the baseline attest different configurations; a baseline "
            "attests exactly one configuration",
            baseline=baseline.configuration_fingerprint,
            measurement=measurement.configuration_fingerprint,
        )
    report = compare_to_baseline(baseline, measurement, resolved_tolerance)
    if report.passed:
        return Ok(report)
    regressed: list[str] = []
    if report.latency_regressed:
        regressed.append(
            f"per-tick latency {report.measured_latency_ns}ns > "
            f"allowed {report.allowed_latency_ns}ns"
        )
    if report.throughput_regressed:
        regressed.append(
            f"burst throughput {report.measured_throughput_per_second}/s < allowed "
            f"{report.allowed_throughput_per_second}/s"
        )
    if report.memory_regressed:
        regressed.append(
            f"peak memory {report.measured_peak_bytes}B > allowed {report.allowed_peak_bytes}B"
        )
    return _policy(
        "benchmark",
        "a benchmark regression fails the tier-2 gate; a peak-memory regression fails "
        "exactly as a slowdown does (DEC-0111, DEC-0128)",
        regressed=regressed,
    )
