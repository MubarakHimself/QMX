"""CT-16 — the first wrapper set of TA-Lib-backed configured indicators
(COMP-QMF-INDICATORS; Story 7.6).

This module ships the **first set of concrete CT-16 configured indicators**, each one a
governed configuration wrapping a formula the pinned canonical reference implements
(``registry:canonical_indicator_reference``). The set is data-driven: :data:`WRAPPER_SET`
maps each formula id to a frozen :class:`WrapperSpec`, and :func:`configure_wrapper`
assembles a full :class:`~qmf.indicators.ConfiguredIndicator` from a caller-supplied
period, input set, calendar requirements, and the injected arithmetic-reference
configuration — declaring **both modes** and setting **warm-up to at least the
reference's lookback** (Story 7.6 AC).

The first set is the reference-owned, single-real-input, single-output, period-taking
formulas the batch bridge (:class:`~qmf.indicators.ReferenceKernel`) computes end to end:

* ``sma`` — arithmetic mean of the last N observations (reference lookback ``period - 1``);
* ``ema`` — exponentially weighted mean of the observations (lookback ``period - 1``);
* ``wma`` — linearly weighted mean of the last N observations (lookback ``period - 1``);
* ``rsi`` — index of average gain to average loss over N observations (lookback ``period``);
* ``mom`` — difference between an observation and the one N observations earlier
  (lookback ``period``);
* ``roc`` — rate of change of an observation over N observations, in percent
  (lookback ``period``).

Each capability term above is **mechanically stated**: no trading-school name appears in
any rule or vocabulary — a school concept enters only as the mechanical operation it names
(a mean, a difference, a rate of change) (DEC-0132). Every wrapper wraps the reference
formula — re-implementing arithmetic the reference owns is a contract defect
(:func:`wrapper_set_conformance_defects`; FM-5) — so the ownership law binds the set from
birth.

Warm-up is the story's discipline made concrete: a wrapper's default warm-up is exactly
the reference's lookback for its period (:meth:`WrapperSpec.reference_lookback`), the
minimum legal value — the marked not-ready prefix covers every leading undefined position
— and a caller may declare a **larger** warm-up but never a smaller one (a warm-up below
the reference lookback is refused here, before ``compute_batch`` would refuse it too).

Default-deny holds: this module imports **only** ``qmf.core`` and this package's own
modules. Public value types are frozen dataclasses and every operation succeeds or RETURNS
a CT-04 typed refusal (DEC-0101, DEC-0109, DEC-0120).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qmf.core import ExactRational, Ok, RefusalCategory, Result, Retryability, TypedRefusal
from qmf.indicators.arithmetic import CANONICAL_OWNERS, FormulaOwnership
from qmf.indicators.configured_indicator import (
    AlignmentPolicy,
    ChannelKind,
    ConfiguredIndicator,
    MissingValuePolicy,
    OutputArity,
    OutputChannel,
    SupportedMode,
)

__all__ = [
    "WRAPPER_FORMULAS",
    "WRAPPER_SET",
    "WrapperSpec",
    "configure_wrapper",
    "reference_lookback",
    "wrapper_set_conformance_defects",
    "wrapper_spec",
]

# The parameter names a period-taking formula accepts, in resolution order — the same set
# the batch bridge resolves (a wrapper declares its period under one of these keys).
_PERIOD_NAMES: Final[tuple[str, ...]] = ("period", "timeperiod")

# The default supported-mode set for a wrapper: both modes, so the tier-2 equality law
# binds (DEC-0126). A caller may narrow it to one mode.
_DEFAULT_MODES: Final[tuple[SupportedMode, ...]] = (
    SupportedMode.BATCH,
    SupportedMode.STREAMING,
)


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a wrapper operation returns (CT-04)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT, retryability=Retryability.NO, context=context
    )


# --- the wrapper specification ----------------------------------------------


@dataclass(frozen=True, slots=True)
class WrapperSpec:
    """The specification of one TA-Lib-backed configured-indicator wrapper (CT-16; DEC-0127).

    ``formula_id`` is the opaque, stable formula id (the same id the canonical-arithmetic
    ownership registry keys on); ``reference_function`` names the reference function the
    formula wraps (the delegation target — wrapping is mandatory); ``output_channel`` is
    the default output-channel name and ``output_kind`` its channel kind; ``lookback_offset``
    is the constant added to the period to get the reference's lookback (``-1`` for the
    moving-average formulas, ``0`` for the difference/oscillator formulas); and
    ``capability_term`` is the mechanically stated description — no trading-school name
    (DEC-0132).
    """

    formula_id: str
    reference_function: str
    output_channel: str
    output_kind: ChannelKind
    lookback_offset: int
    capability_term: str

    def reference_lookback(self, period: int) -> int:
        """The reference's lookback for this formula at ``period`` — the minimum warm-up.

        The leading-undefined count the reference produces: ``period - 1`` for the
        moving-average formulas and ``period`` for the difference/oscillator formulas. The
        warm-up must be at least this, so a marked not-ready value covers every undefined
        leading position (CT-16 warm-up discipline).
        """
        return period + self.lookback_offset


def _spec(
    formula_id: str,
    reference_function: str,
    output_kind: ChannelKind,
    lookback_offset: int,
    capability_term: str,
) -> WrapperSpec:
    """Build one :class:`WrapperSpec`; the output channel is named for the formula."""
    return WrapperSpec(
        formula_id=formula_id,
        reference_function=reference_function,
        output_channel=formula_id,
        output_kind=output_kind,
        lookback_offset=lookback_offset,
        capability_term=capability_term,
    )


# The first wrapper set (CT-16; DEC-0127, DEC-0134). Every entry is a reference-owned
# formula the batch bridge computes end to end; the ownership law binds it — a wrapper
# re-implementing arithmetic the reference owns is a contract defect (FM-5), which
# :func:`wrapper_set_conformance_defects` catches against the canonical-owner registry.
WRAPPER_SET: Final[Mapping[str, WrapperSpec]] = MappingProxyType(
    {
        "sma": _spec(
            "sma",
            "SMA",
            ChannelKind.FLOAT_ANALYTIC,
            -1,
            "arithmetic mean of the last N observations",
        ),
        "ema": _spec(
            "ema",
            "EMA",
            ChannelKind.FLOAT_ANALYTIC,
            -1,
            "exponentially weighted mean of the observations",
        ),
        "wma": _spec(
            "wma",
            "WMA",
            ChannelKind.FLOAT_ANALYTIC,
            -1,
            "linearly weighted mean of the last N observations",
        ),
        "rsi": _spec(
            "rsi",
            "RSI",
            ChannelKind.FLOAT_ANALYTIC,
            0,
            "index of average gain to average loss over N observations",
        ),
        "mom": _spec(
            "mom",
            "MOM",
            ChannelKind.FLOAT_ANALYTIC,
            0,
            "difference between an observation and the one N observations earlier",
        ),
        "roc": _spec(
            "roc",
            "ROC",
            ChannelKind.FLOAT_ANALYTIC,
            0,
            "rate of change of an observation over N observations, in percent",
        ),
    }
)

# The wrapper formula ids in a stable sorted order — the first wrapper set's roster.
WRAPPER_FORMULAS: Final[tuple[str, ...]] = tuple(sorted(WRAPPER_SET))


def wrapper_spec(formula_id: object) -> Result[WrapperSpec]:
    """Resolve the :class:`WrapperSpec` for ``formula_id``, or an ``invalid input`` refusal.

    A formula id outside the first wrapper set is refused (it has no wrapper yet) rather
    than defaulted, so a caller can never build a wrapper for a formula the set does not
    cover.
    """
    if not isinstance(formula_id, str) or formula_id.strip() == "":
        return _invalid(
            "formula_id", "a wrapper formula id is a non-empty token", given=repr(formula_id)
        )
    spec = WRAPPER_SET.get(formula_id)
    if spec is None:
        return _invalid(
            "formula_id",
            "the formula id is not in the first wrapper set",
            given=formula_id,
            wrapper_set=list(WRAPPER_FORMULAS),
        )
    return Ok(spec)


def _period_numerator(period: object) -> int | TypedRefusal:
    """Resolve a wrapper's integer period from an exact rational, or refuse.

    The period is a whole positive number of observations: an :class:`~qmf.core.ExactRational`
    with denominator one and a positive numerator. A binary float never reaches here —
    parameters are exact rationals only — and a fractional or non-positive period is refused.
    """
    if not isinstance(period, ExactRational):
        return _invalid(
            "period",
            "the period is an ExactRational (a whole positive number of observations); "
            "build it via ExactRational.try_create so a binary float never enters identity",
            given=repr(period),
        )
    if period.denominator != 1 or period.numerator < 1:
        return _invalid(
            "period",
            "the period is a positive whole number of observations",
            given=f"{period.numerator}/{period.denominator}",
        )
    return period.numerator


def reference_lookback(formula_id: object, period: object) -> Result[int]:
    """The reference's lookback for a wrapper formula at a period (CT-16 warm-up discipline).

    Resolves the wrapper spec and the integer period and returns the reference's
    leading-undefined count — the minimum legal warm-up. Refuses an unknown formula id or a
    non-whole/non-positive period.
    """
    resolved_spec = wrapper_spec(formula_id)
    if isinstance(resolved_spec, TypedRefusal):
        return resolved_spec
    numerator = _period_numerator(period)
    if isinstance(numerator, TypedRefusal):
        return numerator
    return Ok(resolved_spec.value.reference_lookback(numerator))


def wrapper_set_conformance_defects(
    wrappers: Mapping[str, WrapperSpec] = WRAPPER_SET,
    owners: Mapping[str, object] = CANONICAL_OWNERS,
) -> tuple[str, ...]:
    """Structural conformance over the wrapper set — the defects, or empty (CT-16 FM-5).

    A contract defect, caught here rather than at runtime: a wrapper whose formula id does
    not match its registry key; a wrapper whose formula has no canonical owner; a wrapper
    over a formula the canonical registry does not mark reference-owned (re-implementing a
    formula the reference does not own would not be canonical wrapping); or a wrapper whose
    declared reference function does not match the canonical owner's. An empty result means
    every wrapper genuinely wraps the reference formula the registry assigns it.
    """
    defects: list[str] = []
    for key, spec in wrappers.items():
        if spec.formula_id != key:
            defects.append(f"{key}: formula_id {spec.formula_id!r} does not match its key")
        owner = owners.get(key)
        if owner is None:
            defects.append(f"{key}: the wrapper formula has no canonical owner (FM-5)")
            continue
        ownership = getattr(owner, "ownership", None)
        if ownership is not FormulaOwnership.REFERENCE:
            defects.append(
                f"{key}: the wrapper formula is not reference-owned; a wrapper wraps a "
                f"formula the reference implements (FM-5)"
            )
            continue
        reference_function = getattr(owner, "reference_function", None)
        if reference_function != spec.reference_function:
            defects.append(
                f"{key}: the wrapper delegates to {spec.reference_function!r} but the "
                f"canonical owner names {reference_function!r} (FM-5)"
            )
    return tuple(defects)


def configure_wrapper(
    *,
    formula_id: object,
    period: object,
    inputs: object,
    calendar_requirements: object,
    arithmetic_reference_configuration: object,
    contract_format_version: object = 1,
    alignment_policy: object = AlignmentPolicy.AS_OF,
    missing_value_policy: object = MissingValuePolicy.MARK_GAP,
    supported_modes: object = _DEFAULT_MODES,
    warm_up: object = None,
    output_channel: object = None,
    emission_policy: object = None,
    warm_up_time_bound: object = None,
    declared_budget: object = None,
) -> Result[ConfiguredIndicator]:
    """Assemble a concrete CT-16 configured indicator for a wrapper formula, value-or-refusal.

    Builds a full :class:`~qmf.indicators.ConfiguredIndicator` wrapping the reference
    formula ``formula_id`` names: the ``period`` becomes the sole exact-rational parameter,
    the single ``output_channel`` (defaulting to the wrapper's declared name and kind,
    scalar-per-sample at offset 0) the output schema, and the **warm-up defaults to the
    reference's lookback** for the period — the minimum legal value. A caller may declare a
    **larger** ``warm_up`` (a non-negative integer at least the reference lookback) but a
    smaller one is refused here (CT-16 warm-up discipline). ``supported_modes`` defaults to
    **both modes**, so the tier-2 equality law binds.

    The ``inputs``, ``calendar_requirements``, and ``arithmetic_reference_configuration``
    are injected by the composition root and validated by
    :meth:`ConfiguredIndicator.try_create`; the arithmetic-reference configuration is the
    identity of ``registry:canonical_indicator_reference``, never hardcoded here. Every
    failure is a returned CT-04 refusal.
    """
    resolved_spec = wrapper_spec(formula_id)
    if isinstance(resolved_spec, TypedRefusal):
        return resolved_spec
    spec = resolved_spec.value
    numerator = _period_numerator(period)
    if isinstance(numerator, TypedRefusal):
        return numerator
    minimum_warm_up = spec.reference_lookback(numerator)
    resolved_warm_up = _resolve_warm_up(warm_up, minimum_warm_up)
    if isinstance(resolved_warm_up, TypedRefusal):
        return resolved_warm_up
    channel = _resolve_output_channel(output_channel, spec)
    if isinstance(channel, TypedRefusal):
        return channel
    return ConfiguredIndicator.try_create(
        formula_id=spec.formula_id,
        contract_format_version=contract_format_version,
        parameters={"period": period},
        inputs=inputs,
        calendar_requirements=calendar_requirements,
        alignment_policy=alignment_policy,
        missing_value_policy=missing_value_policy,
        warm_up=resolved_warm_up,
        output_schema=[channel],
        supported_modes=supported_modes,
        arithmetic_reference_configuration=arithmetic_reference_configuration,
        emission_policy=emission_policy,
        warm_up_time_bound=warm_up_time_bound,
        declared_budget=declared_budget,
    )


def _resolve_warm_up(warm_up: object, minimum: int) -> int | TypedRefusal:
    """Resolve the warm-up: the reference lookback by default, else a larger declared count.

    ``None`` defaults to the reference's lookback (the minimum). A declared warm-up must be
    a genuine non-negative integer at least the reference lookback; a warm-up below it is
    refused before ``compute_batch`` would refuse it too (CT-16 warm-up discipline).
    """
    if warm_up is None:
        return minimum
    if isinstance(warm_up, bool) or not isinstance(warm_up, int):
        return _invalid(
            "warm_up",
            "warm-up is an integer count of completed observations, at least the reference "
            "lookback (omit it to default to the reference lookback)",
            given=repr(warm_up),
        )
    if warm_up < minimum:
        return _invalid(
            "warm_up",
            "warm-up must be at least the reference's lookback; a marked not-ready value "
            "covers every undefined leading position (CT-16 warm-up discipline)",
            given=warm_up,
            reference_lookback=minimum,
        )
    return warm_up


def _resolve_output_channel(
    output_channel: object, spec: WrapperSpec
) -> OutputChannel | TypedRefusal:
    """Resolve the output channel: the wrapper's default, or a caller-supplied override.

    ``None`` builds the wrapper's default single scalar-per-sample channel (named for the
    formula, at the wrapper's declared kind, offset 0). A supplied :class:`OutputChannel`
    is used verbatim; any other value is refused.
    """
    if output_channel is None:
        built = OutputChannel.try_create(
            spec.output_channel, spec.output_kind, OutputArity.SCALAR_PER_SAMPLE, 0
        )
        if isinstance(built, TypedRefusal):  # pragma: no cover - the spec values are always valid
            return built
        return built.value
    if not isinstance(output_channel, OutputChannel):
        return _invalid(
            "output_channel",
            "the output channel is an OutputChannel (omit it for the wrapper's default)",
            given=repr(output_channel),
        )
    return output_channel
