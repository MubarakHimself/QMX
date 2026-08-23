"""CT-17 — the light/heavy four-bound rule and the benchmark gate (COMP-QMF-STRUCTURE).

Families are policed for cost under the same benchmark discipline as indicators: the
benchmark harness has the **same standing as the unit tests** (a test exercises it every
run), and a family is *light* only when four declared bounds are benchmark-proven — otherwise
it is *heavy* by default (CT-17; DEC-0128, DEC-0129, DEC-0111).

**The three structure benchmark rungs (DEC-0129, DEC-0111).** :class:`BenchmarkRung` names the
rungs the harness measures for a family: **active object-set size**, **objects minted per
bar**, and **interaction records per bar**. The measurement harness lives in
:mod:`qmf.structure._bench`; this module holds the *policy* — the declared budget, the
light-claim verdict, and the regression gate — as public typed surface.

**The four light bounds and the light claim (FM-8, DEC-0128).** :class:`DeclaredBudget` carries
the four bounds a family declares to claim light: a per-update cost ceiling (the live-path
rung), a live-object-set-size ceiling, a scan/lookback-window ceiling, and synchronous
availability. :func:`evaluate_light_claim` proves a claim against measurements: it RETURNS a
``policy rejection`` when any measurement exceeds its declared bound, when the family is not
synchronously available, or when the live-path rung **lacks a recorded baseline** — a family is
heavy by default until it has one. The verdict is machine-scoped, display-only, and **never
identity**.

**A peak-memory regression fails exactly as a slowdown does (FM-8, DEC-0128).**
:func:`check_regression` compares a current measurement against its recorded baseline on
**both** wall-clock seconds and peak memory, and RETURNS a ``policy rejection`` when either
regresses beyond the declared tolerance — memory is not a softer signal than speed.

Default-deny holds: this module imports **only** ``qmf.core``. Wall-clock seconds and peak
bytes are benchmark measurements, never money-path values — no exact-money rule applies to
them, and no binary float ever reaches a :class:`~qmf.core.Price` or
:class:`~qmf.core.ExactRational` here. Public value types are frozen dataclasses, and every
operation succeeds or RETURNS a CT-04 :class:`~qmf.core.TypedRefusal`; domain failure is never
raised across the boundary (DEC-0101, DEC-0109, DEC-0113).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qmf.core import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
)

__all__ = [
    "BenchmarkRung",
    "DeclaredBudget",
    "LightVerdict",
    "Measurement",
    "RegressionVerdict",
    "check_regression",
    "evaluate_light_claim",
]

# Basis-points denominator for the tolerance ratio: a tolerance of N basis points allows a
# current value up to baseline * (10000 + N) / 10000 before it counts as a regression.
_BPS_DENOMINATOR: int = 10_000


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a budget operation returns (CT-04; DEC-0109)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``policy rejection`` refusal the tier-2 benchmark gate returns (FM-8; DEC-0128).

    A failed light claim or a benchmark regression is not *malformed* — it is a well-formed
    measurement the gate **declines** — so it is a policy rejection. ``retryability`` is ``no``:
    it succeeds only once the family is optimized or its declared bound widened, which is new
    evidence, not a retry of this measurement.
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def _non_negative_int(value: object) -> int | None:
    """Return ``value`` as a non-negative ``int`` (a ``bool`` is rejected), else ``None``."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


class BenchmarkRung(StrEnum):
    """The benchmark rungs the structure harness measures for a family (CT-17; DEC-0129,
    DEC-0111)."""

    ACTIVE_OBJECT_SET_SIZE = "active-object-set-size"
    OBJECTS_MINTED_PER_BAR = "objects-minted-per-bar"
    INTERACTION_RECORDS_PER_BAR = "interaction-records-per-bar"


@dataclass(frozen=True, slots=True)
class DeclaredBudget:
    """The four light-claim bounds a family declares to claim light (CT-17; DEC-0128).

    ``per_update_cost_ceiling_ns`` is the live-path per-update cost ceiling (nanoseconds);
    ``object_set_size_ceiling`` the bounded live-object-set size; ``scan_window_ceiling`` the
    bounded scan/lookback window; and ``synchronous_available`` whether the family answers
    synchronously (a marked not-ready value satisfies it). It is declared contract surface,
    distinct from the display-only light verdict.
    """

    per_update_cost_ceiling_ns: int
    object_set_size_ceiling: int
    scan_window_ceiling: int
    synchronous_available: bool

    @classmethod
    def try_create(
        cls,
        *,
        per_update_cost_ceiling_ns: object,
        object_set_size_ceiling: object,
        scan_window_ceiling: object,
        synchronous_available: object,
    ) -> Result[DeclaredBudget]:
        """Validate and build a :class:`DeclaredBudget`, returning value-or-refusal."""
        cost = _non_negative_int(per_update_cost_ceiling_ns)
        if cost is None:
            return _invalid(
                "per_update_cost_ceiling_ns",
                "the per-update cost ceiling is a non-negative integer of nanoseconds",
                given=repr(per_update_cost_ceiling_ns),
            )
        objects = _non_negative_int(object_set_size_ceiling)
        if objects is None:
            return _invalid(
                "object_set_size_ceiling",
                "the live-object-set-size ceiling is a non-negative integer",
                given=repr(object_set_size_ceiling),
            )
        window = _non_negative_int(scan_window_ceiling)
        if window is None:
            return _invalid(
                "scan_window_ceiling",
                "the scan/lookback window ceiling is a non-negative integer",
                given=repr(scan_window_ceiling),
            )
        if not isinstance(synchronous_available, bool):
            return _invalid(
                "synchronous_available",
                "synchronous availability is a bool",
                given=repr(synchronous_available),
            )
        return Ok(
            cls(
                per_update_cost_ceiling_ns=cost,
                object_set_size_ceiling=objects,
                scan_window_ceiling=window,
                synchronous_available=synchronous_available,
            )
        )


@dataclass(frozen=True, slots=True)
class Measurement:
    """One benchmark measurement at a rung: wall-clock seconds and peak memory (CT-17;
    DEC-0129, DEC-0111).

    A witness the harness produced, never a stored field of any object. ``seconds`` and
    ``peak_bytes`` are benchmark quantities, never money-path values.
    """

    rung: BenchmarkRung
    seconds: float
    peak_bytes: int


@dataclass(frozen=True, slots=True)
class LightVerdict:
    """The display-only, machine-scoped light verdict for a family (CT-17; DEC-0128).

    Returned only when the family **is** light. ``per_update_cost_ns``, ``object_set_size``, and
    ``scan_window`` are the proven measurements that cleared their declared bounds. The verdict
    is never identity: it never enters an object's ``fp1``.
    """

    light: bool
    per_update_cost_ns: int
    object_set_size: int
    scan_window: int


def evaluate_light_claim(
    budget: object,
    *,
    per_update_cost_ns: object,
    object_set_size: object,
    scan_window: object,
    has_baseline: object,
) -> Result[LightVerdict]:
    """Prove a family's light claim against measurements, returning the verdict or a refusal
    (FM-8; DEC-0128, DEC-0111).

    A family is light **only** when all four bounds hold and the live-path rung has a recorded
    baseline. This RETURNS a ``policy rejection`` when the live-path rung lacks a baseline (heavy
    by default), when a measurement exceeds its declared bound, or when the family is not
    synchronously available. On success it returns a :class:`LightVerdict` — display-only, never
    identity.
    """
    if not isinstance(budget, DeclaredBudget):
        return _invalid(
            "budget", "a light claim is evaluated against a DeclaredBudget", given=repr(budget)
        )
    cost = _non_negative_int(per_update_cost_ns)
    if cost is None:
        return _invalid(
            "per_update_cost_ns",
            "the per-update cost is a non-negative integer of ns",
            given=repr(per_update_cost_ns),
        )
    objects = _non_negative_int(object_set_size)
    if objects is None:
        return _invalid(
            "object_set_size",
            "the live-object-set size is a non-negative integer",
            given=repr(object_set_size),
        )
    window = _non_negative_int(scan_window)
    if window is None:
        return _invalid(
            "scan_window",
            "the scan/lookback window is a non-negative integer",
            given=repr(scan_window),
        )
    if not isinstance(has_baseline, bool):
        return _invalid(
            "has_baseline", "the baseline-present flag is a bool", given=repr(has_baseline)
        )

    if not has_baseline:
        return _policy(
            "has_baseline",
            "a family is heavy by default until the live-path rung has a recorded baseline; a "
            "light claim without one is refused at the tier-2 benchmark gate (FM-8)",
        )
    if not budget.synchronous_available:
        return _policy(
            "synchronous_available",
            "a light family answers synchronously; a family that is not synchronously available "
            "cannot claim light (FM-8)",
        )
    if cost > budget.per_update_cost_ceiling_ns:
        return _policy(
            "per_update_cost_ns",
            "the per-update cost exceeds the declared live-path ceiling; the light claim is "
            "refused at the tier-2 benchmark gate (FM-8)",
            measured=cost,
            ceiling=budget.per_update_cost_ceiling_ns,
        )
    if objects > budget.object_set_size_ceiling:
        return _policy(
            "object_set_size",
            "the live-object-set size exceeds the declared ceiling; the light claim is refused",
            measured=objects,
            ceiling=budget.object_set_size_ceiling,
        )
    if window > budget.scan_window_ceiling:
        return _policy(
            "scan_window",
            "the scan/lookback window exceeds the declared ceiling; the light claim is refused",
            measured=window,
            ceiling=budget.scan_window_ceiling,
        )
    return Ok(
        LightVerdict(
            light=True, per_update_cost_ns=cost, object_set_size=objects, scan_window=window
        )
    )


@dataclass(frozen=True, slots=True)
class RegressionVerdict:
    """The result of a passed benchmark regression check (CT-17; DEC-0128).

    Returned only when neither signal regressed. ``seconds_regressed`` and ``memory_regressed``
    are both ``False`` here; they are named so the gate treats a peak-memory regression exactly
    as it treats a slowdown.
    """

    regressed: bool
    seconds_regressed: bool
    memory_regressed: bool


def _regressed(baseline_value: float, current_value: float, tolerance_bps: int) -> bool:
    """Whether ``current_value`` exceeds ``baseline_value`` by more than ``tolerance_bps``.

    Applied identically to wall-clock seconds and to peak bytes, so a memory regression fails
    exactly as a slowdown does. Cross-multiplied to avoid dividing.
    """
    return current_value * _BPS_DENOMINATOR > baseline_value * (_BPS_DENOMINATOR + tolerance_bps)


def check_regression(
    baseline: object, current: object, *, tolerance_bps: object
) -> Result[RegressionVerdict]:
    """Check a current measurement against its baseline on speed and memory (FM-8; DEC-0128).

    RETURNS a ``policy rejection`` when wall-clock seconds **or** peak memory regressed beyond
    ``tolerance_bps`` basis points — the two signals are treated identically. ``baseline`` and
    ``current`` are :class:`Measurement` values of the **same** rung; a mismatched rung is an
    ``invalid input`` refusal.
    """
    if not isinstance(baseline, Measurement):
        return _invalid("baseline", "the baseline is a Measurement", given=repr(baseline))
    if not isinstance(current, Measurement):
        return _invalid("current", "the current reading is a Measurement", given=repr(current))
    tolerance = _non_negative_int(tolerance_bps)
    if tolerance is None:
        return _invalid(
            "tolerance_bps",
            "the tolerance is a non-negative integer of basis points",
            given=repr(tolerance_bps),
        )
    if baseline.rung is not current.rung:
        return _invalid(
            "current",
            "a regression check compares measurements of the same rung",
            baseline_rung=baseline.rung.value,
            current_rung=current.rung.value,
        )
    seconds_regressed = _regressed(baseline.seconds, current.seconds, tolerance)
    memory_regressed = _regressed(baseline.peak_bytes, current.peak_bytes, tolerance)
    if seconds_regressed or memory_regressed:
        return _policy(
            "current",
            "a benchmark regression fails the tier-2 gate; a peak-memory regression fails exactly "
            "as a slowdown does (FM-8)",
            rung=current.rung.value,
            seconds_regressed=seconds_regressed,
            memory_regressed=memory_regressed,
            baseline_seconds=baseline.seconds,
            current_seconds=current.seconds,
            baseline_peak_bytes=baseline.peak_bytes,
            current_peak_bytes=current.peak_bytes,
        )
    return Ok(RegressionVerdict(regressed=False, seconds_regressed=False, memory_regressed=False))
