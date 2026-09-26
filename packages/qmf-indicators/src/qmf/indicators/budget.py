"""CT-16 — the light/heavy budget verdict and the synchronous-entry gate
(COMP-QMF-INDICATORS; Story 7.5).

Light versus heavy is **per configuration, never per name** (CT-16; DEC-0128). A
configuration is **heavy by default** until the live-path rung has a recorded baseline;
it is light **iff** its four declared bounds hold **and** are benchmark-proven:

1. per-update cost within the live-path rung (proven by the per-tick-latency rung staying
   within the recorded baseline — :func:`~qmf.indicators.benchmark.regression_gate`);
2. bounded declared state size (declared on the :class:`~qmf.indicators.DeclaredBudget`);
3. a bounded evidence window or a declared anchor-reset rule (declared on the budget, and
   its memory bound proven by the peak-memory axis of the same gate);
4. synchronous availability — which a marked not-ready value satisfies (declared on the
   budget).

Two gates land here (CT-16 FM-3, FM-6; DEC-0128, DEC-0111, DEC-0109):

* :func:`evaluate_light_claim` — the tier-2 evaluator. A configuration that **claims
  light** (declares a budget) **without a recorded live-path rung baseline, or whose
  benchmark misses a declared bound, is refused**. A configuration that makes no light
  claim is heavy by default (an ``Ok`` heavy verdict, not a refusal). The verdict it
  returns is **machine-scoped and display-only, never identity**.
* :func:`guard_synchronous_entry` — the FM-3 gate. A **heavy** configuration's synchronous
  entry point returns ``unsupported capability``; heavy runs off the trading path, computed
  once and fanned out through the same contract. A light configuration's synchronous entry
  is permitted.

Default-deny holds: this module imports **only** ``qmf.core`` and this package's own
modules. Public value types are frozen dataclasses and every operation succeeds or RETURNS
a CT-04 typed refusal (DEC-0101, DEC-0109, DEC-0120).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qmf.core import Ok, RefusalCategory, Result, Retryability, TypedRefusal, is_ok
from qmf.indicators.benchmark import (
    BenchmarkBaseline,
    BenchmarkMeasurement,
    RegressionTolerance,
    regression_gate,
)
from qmf.indicators.configured_indicator import ConfiguredIndicator

__all__ = [
    "BudgetVerdict",
    "LightHeavyVerdict",
    "evaluate_light_claim",
    "guard_synchronous_entry",
]


class LightHeavyVerdict(StrEnum):
    """The per-configuration light/heavy verdict (CT-16; DEC-0128).

    Machine-scoped and display-only, **never** part of the configuration's ``fp1``
    identity. ``light`` means the four bounds are declared and benchmark-proven; ``heavy``
    means the configuration is heavy by default (no proven light claim).
    """

    LIGHT = "light"
    HEAVY = "heavy"


@dataclass(frozen=True, slots=True)
class BudgetVerdict:
    """A configuration's light/heavy verdict with its display-only rationale (CT-16; DEC-0128).

    ``verdict`` is the machine-scoped, display-only decision; ``reasons`` is the human-legible
    rationale (which bounds were proven, or why the configuration is heavy). Neither enters
    ``fp1`` identity — the verdict is never a configuration's name.
    """

    verdict: LightHeavyVerdict
    reasons: tuple[str, ...]


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a budget operation returns (CT-04)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT, retryability=Retryability.NO, context=context
    )


def _refused_light_claim(reason: str, **extra: object) -> TypedRefusal:
    """Build the ``policy rejection`` refusal a failed light claim returns at the gate (FM-6).

    A configuration claiming light without a recorded live-path rung baseline, or whose
    benchmark misses a declared bound, is refused at the tier-2 gate; the configuration is
    heavy by default (CT-16 FM-6; DEC-0128, DEC-0111).
    """
    context: dict[str, object] = {"field": "declared_budget", "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION, retryability=Retryability.NO, context=context
    )


def evaluate_light_claim(
    configuration: object,
    *,
    baseline: object = None,
    measurement: object = None,
    tolerance: object = None,
) -> Result[BudgetVerdict]:
    """Evaluate a configuration's light claim at the tier-2 gate (CT-16 FM-6; DEC-0128).

    A configuration with **no declared budget** makes no light claim: it is heavy by default
    and this returns an ``Ok`` heavy verdict. A configuration that **claims light** (declares
    a :class:`~qmf.indicators.DeclaredBudget`) is evaluated against its four bounds:

    * a ``baseline`` (a :class:`~qmf.indicators.benchmark.BenchmarkBaseline`) is **required**
      — claiming light without a recorded live-path rung baseline is refused;
    * ``bounded_state`` and ``synchronous_availability`` must both be declared true;
    * the per-update cost and memory bounds must be **benchmark-proven** — a ``measurement``
      is required and it must pass :func:`~qmf.indicators.benchmark.regression_gate` against
      the baseline (a missed bound is a refusal).

    Any missed bound refuses the claim (``policy rejection``, FM-6). The returned verdict is
    machine-scoped and display-only, never identity.
    """
    if not isinstance(configuration, ConfiguredIndicator):
        return _invalid(
            "configuration", "a ConfiguredIndicator is required", given=repr(configuration)
        )
    budget = configuration.declared_budget
    if budget is None:
        return Ok(
            BudgetVerdict(
                verdict=LightHeavyVerdict.HEAVY,
                reasons=(
                    "no declared budget: the configuration makes no light claim and is heavy "
                    "by default until the live-path rung has a recorded baseline (DEC-0128)",
                ),
            )
        )
    if baseline is None:
        return _refused_light_claim(
            "a configuration claiming light without a recorded live-path rung baseline is "
            "refused at the tier-2 gate; every configuration is heavy by default (FM-6)"
        )
    if not isinstance(baseline, BenchmarkBaseline):
        return _invalid("baseline", "a BenchmarkBaseline is required", given=repr(baseline))
    unmet: list[str] = []
    if not budget.bounded_state:
        unmet.append("bound 2 (bounded declared state size) is not declared")
    if not budget.synchronous_availability:
        unmet.append("bound 4 (synchronous availability) is not declared")
    proof = _benchmark_proof(configuration, baseline, measurement, tolerance)
    if isinstance(proof, TypedRefusal):
        return proof
    unmet.extend(proof)
    if unmet:
        return _refused_light_claim(
            "the light claim misses a declared bound; the configuration is heavy by default (FM-6)",
            unmet=tuple(unmet),
        )
    return Ok(
        BudgetVerdict(
            verdict=LightHeavyVerdict.LIGHT,
            reasons=(
                "four bounds declared and benchmark-proven against the recorded live-path "
                f"rung baseline on ({baseline.os}, {baseline.cpu_class})",
                f"window-or-anchor rule: {budget.window_or_anchor_rule}",
                f"per-update cost rung: {budget.per_update_cost_rung}",
            ),
        )
    )


def _benchmark_proof(
    configuration: ConfiguredIndicator,
    baseline: BenchmarkBaseline,
    measurement: object,
    tolerance: object,
) -> list[str] | TypedRefusal:
    """The benchmark-proven bounds (1 and 3): the unmet reasons, or a refusal for a bad arg.

    A light claim's per-update-cost bound and memory bound are proven only by a live
    measurement passing the regression gate against the baseline. No measurement means the
    bounds are not benchmark-proven (an unmet reason); a measurement that regresses is also
    unmet. A malformed ``tolerance`` is a returned ``invalid input`` refusal.
    """
    if tolerance is not None and not isinstance(tolerance, RegressionTolerance):
        return _invalid(
            "tolerance", "a RegressionTolerance is required (or omit it)", given=repr(tolerance)
        )
    if measurement is None:
        return [
            "bounds 1 and 3 (per-update cost within the live-path rung; bounded memory) are "
            "not benchmark-proven: no measurement was supplied"
        ]
    if not isinstance(measurement, BenchmarkMeasurement):
        return _invalid(
            "measurement",
            "a BenchmarkMeasurement is required (or omit it)",
            given=repr(measurement),
        )
    resolved_tolerance = tolerance if isinstance(tolerance, RegressionTolerance) else None
    gate = regression_gate(baseline, measurement, resolved_tolerance)
    if is_ok(gate):
        return []
    return [f"the benchmark regressed against the baseline: {dict(gate.context)}"]


def guard_synchronous_entry(verdict: object) -> Result[None]:
    """Gate a synchronous (live-path) entry on the light/heavy verdict (CT-16 FM-3; DEC-0128).

    A **heavy** configuration's synchronous entry point returns ``unsupported capability``:
    heavy runs off the trading path, computed once and fanned out through the same contract.
    A **light** configuration's synchronous entry is permitted (``Ok``). The caller passes
    the :class:`BudgetVerdict` :func:`evaluate_light_claim` produced.
    """
    if not isinstance(verdict, BudgetVerdict):
        return _invalid("verdict", "a BudgetVerdict is required", given=repr(verdict))
    if verdict.verdict is LightHeavyVerdict.HEAVY:
        return TypedRefusal(
            category=RefusalCategory.UNSUPPORTED_CAPABILITY,
            retryability=Retryability.NO,
            context={
                "field": "synchronous_entry",
                "reason": "a heavy configuration's synchronous entry point returns unsupported "
                "capability; heavy runs off the trading path, computed once and fanned out "
                "through the same contract (FM-3, DEC-0128)",
                "verdict": verdict.verdict.value,
            },
        )
    return Ok(None)
