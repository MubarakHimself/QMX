"""CT-16 — batch mode with as-of-only alignment and presence-mapped outputs
(COMP-QMF-INDICATORS; Story 7.3).

Batch mode computes a configured indicator over a whole input series and returns
**full-length, index-aligned, presence-mapped** output — one
:class:`~qmf.indicators.series.IndicatorSeries` per declared output channel, the same
length as the input, with begin-index trimming prohibited, every position carrying a
``registry:presence_map_states`` value, and no NaN or sentinel anywhere (DEC-0126). Four
laws this module enforces:

* **As-of-only alignment.** :func:`align_to_instant` aligns a value to an evaluation
  instant by the last value known at or before it; forward-fill or interpolation across
  the evaluation instant is a ``policy rejection`` refusal (FM-1). There is no
  look-ahead across the evaluation instant.
* **Schedule vs missing.** A position the market-hours calendar marks closed is
  ``absent_by_schedule``, never a gap; a calendar-open position with no data follows the
  declared missing-value policy — ``mark-gap`` marks a ``gap``, ``refuse`` returns a
  ``policy rejection`` — never silent filling (FM-1).
* **Warm-up.** Warm-up is an integer count of completed input observations in the
  input's own sample unit (never ticks, never a Duration), at least the reference's
  lookback; during warm-up the output is a marked ``not_ready`` value, never a number.
* **Knowable-at and provisional evidence.** Every output sample carries a knowable-at
  instant — the earliest instant at which every contributing input was knowable — and
  provisional samples never enter governed evidence (:func:`require_governed`).

The indicator receives its ``BarSpec`` as data (each :class:`InputSeries` column is the
aggregated-bar column the application supplies) and never derives bar boundaries itself.
The numeric core is resolved through the canonical-arithmetic seam (Story 7.2): a
:class:`BatchKernel` maps the dense present observations to dense output values, and
:class:`ReferenceKernel` is the bridge that wraps the pinned reference where it owns a
formula. The engine itself is integer-and-presence only — no binary float crosses it;
the descale/rescale to and from the analytic reference stays inside the kernel bridge,
which stores its float-analytic results as scaled integers at a declared output scale.

Default-deny holds: this module imports only ``qmf.core`` and this package's own
modules; ``numpy`` is a private conversion detail resolved by name and never crosses a
public boundary, and no reference object crosses one either (DEC-0120, FM-5). Public
value types are frozen dataclasses, the kernel seam is a :class:`typing.Protocol`, and
every operation succeeds or RETURNS a CT-04 refusal (DEC-0101, DEC-0109).
"""

from __future__ import annotations

import importlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from typing import Any, Final, Protocol, cast, runtime_checkable

from qmf.core import (
    EvidenceClass,
    Fingerprint,
    Instant,
    Interval,
    Ok,
    RefusalCategory,
    Result,
    ResultLabel,
    Retryability,
    TypedRefusal,
    World,
    is_refusal,
)
from qmf.indicators import _reference
from qmf.indicators.arithmetic import resolve_canonical_arithmetic
from qmf.indicators.configured_indicator import (
    ConfiguredIndicator,
    EmissionTiming,
    MissingValuePolicy,
    SupportedMode,
)
from qmf.indicators.series import (
    IndicatorSeries,
    InputSeries,
    PresenceState,
    encode_int64_values,
)

__all__ = [
    "DEFAULT_ANALYTIC_SCALE",
    "AlignmentMode",
    "AsOfSample",
    "BatchKernel",
    "BatchResult",
    "KernelOutput",
    "ReferenceKernel",
    "align_to_instant",
    "compute_batch",
    "require_governed",
]

# The declared output storage scale (count of decimal places) a float-analytic channel
# is stored at in the bulk form. A property of the producing bridge, carried out-of-band
# beside the int64 values, so the analytic result never persists as a binary float.
DEFAULT_ANALYTIC_SCALE: Final[int] = 8

# The largest integer float64 represents exactly (its 53-bit mantissa). A magnitude past
# this cannot descale to the analytic reference without loss, so it is refused rather
# than silently rounded (CT-16 exact-to-analytic descale).
_FLOAT64_EXACT_INT_MAX: Final[int] = 2**53

# The reference-owned formulas the batch bridge wraps in this story: single real input,
# single real output, one integer ``period`` parameter. The broader wrapper set (multi
# output, multi input) lands in Story 7.6; a formula outside this set is refused here
# rather than mis-called.
_SINGLE_INPUT_TIMEPERIOD: Final[frozenset[str]] = frozenset(
    {"sma", "ema", "wma", "rsi", "mom", "roc"}
)

# The parameter names a period-taking formula accepts, in resolution order.
_PERIOD_NAMES: Final[tuple[str, ...]] = ("period", "timeperiod")


# --- refusal builders -------------------------------------------------------


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a batch operation returns (CT-04)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT, retryability=Retryability.NO, context=context
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``policy rejection`` refusal the alignment and missing-value laws return.

    Forward-fill or interpolation across the evaluation instant, a calendar-open gap
    under a ``refuse`` missing-value policy, and provisional evidence reaching governed
    evidence are all policy rejections (CT-16 FM-1; DEC-0109, DEC-0126).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION, retryability=Retryability.NO, context=context
    )


def _unsupported(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``unsupported capability`` refusal a mode/formula guard returns (CT-04)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.UNSUPPORTED_CAPABILITY,
        retryability=Retryability.NO,
        context=context,
    )


# --- as-of alignment --------------------------------------------------------


class AlignmentMode(StrEnum):
    """A requested alignment mode to an evaluation instant (CT-16 FM-1; DEC-0126).

    Only ``as-of`` is legal for governed evidence — the last value known at or before
    the instant. ``forward-fill`` and ``interpolate`` are named here **so that a request
    for either is refused with a policy rejection** (they would use data known only
    after the instant — look-ahead across the evaluation instant), never so they become
    usable values.
    """

    AS_OF = "as-of"
    FORWARD_FILL = "forward-fill"
    INTERPOLATE = "interpolate"


@dataclass(frozen=True, slots=True)
class AsOfSample:
    """The result of aligning a series to an evaluation instant as-of (CT-16; DEC-0126).

    When a value is known at or before the instant, ``presence`` is ``present`` and
    ``index`` / ``value`` / ``knowable_at`` name it. When nothing is known yet as-of the
    instant, ``presence`` is ``not_ready`` and those fields are ``None`` — a legitimate
    as-of answer, never a filled-in number.
    """

    presence: PresenceState
    scale: int
    index: int | None = None
    value: int | None = None
    knowable_at: Instant | None = None


def align_to_instant(
    series: object, evaluation_instant: object, mode: object
) -> Result[AsOfSample]:
    """Align a bulk series to an evaluation instant, as-of only (CT-16 FM-1; DEC-0126).

    Under ``as-of`` the result is the last **present** value whose knowable-at is at or
    before ``evaluation_instant`` — no look-ahead across the instant. A ``forward-fill``
    or ``interpolate`` request is a ``policy rejection`` refusal, because both would draw
    on data known only after the instant. When nothing is known as-of the instant the
    result is a ``not_ready`` :class:`AsOfSample`, never a filled value.
    """
    if not isinstance(series, (InputSeries, IndicatorSeries)):
        return _invalid(
            "series", "as-of alignment takes an InputSeries or IndicatorSeries", given=repr(series)
        )
    if not isinstance(evaluation_instant, Instant):
        return _invalid(
            "evaluation_instant",
            "the evaluation instant is an Instant",
            given=repr(evaluation_instant),
        )
    resolved_mode = mode if isinstance(mode, AlignmentMode) else _coerce_mode(mode)
    if resolved_mode is None:
        return _invalid(
            "mode",
            "the alignment mode is one of the closed set",
            given=repr(mode),
            allowed=[member.value for member in AlignmentMode],
        )
    if resolved_mode is not AlignmentMode.AS_OF:
        return _policy(
            "mode",
            "only as-of alignment is permitted for governed evidence; forward-fill or "
            "interpolation across the evaluation instant is refused (no look-ahead) (FM-1)",
            requested=resolved_mode.value,
        )
    horizon = evaluation_instant.value_ns
    for index in range(series.length - 1, -1, -1):
        if (
            series.presence_at(index) is PresenceState.PRESENT
            and series.knowable_at[index].value_ns <= horizon
        ):
            return Ok(
                AsOfSample(
                    presence=PresenceState.PRESENT,
                    scale=series.scale,
                    index=index,
                    value=series.value_at(index),
                    knowable_at=series.knowable_at[index],
                )
            )
    return Ok(AsOfSample(presence=PresenceState.NOT_READY, scale=series.scale))


def _coerce_mode(value: object) -> AlignmentMode | None:
    if isinstance(value, str):
        try:
            return AlignmentMode(value)
        except ValueError:
            return None
    return None


# --- the numeric kernel seam ------------------------------------------------


@dataclass(frozen=True, slots=True)
class KernelOutput:
    """The dense numeric output a :class:`BatchKernel` produces (CT-16; DEC-0126, DEC-0127).

    ``channels`` maps each declared output-channel name to a dense tuple aligned to the
    dense present-observation sequence — a scaled integer where a value is defined, or
    ``None`` where the reference's leading-undefined prefix leaves it undefined.
    ``lookback`` is the reference's lookback (the leading-undefined count); ``scale`` is
    the out-of-band storage scale of every value in ``channels``.
    """

    channels: Mapping[str, tuple[int | None, ...]]
    lookback: int
    scale: int


@runtime_checkable
class BatchKernel(Protocol):
    """The canonical-arithmetic numeric core of batch mode (CT-16; DEC-0127).

    A pure seam the engine drives with the **dense present observations** (missing,
    closed, and not-ready positions already removed) and asks for dense output values.
    Where the pinned reference implements the formula the kernel wraps it (mandatory
    wrapping); where it does not, the kernel is the package-canonical arithmetic. The
    kernel is package-neutral — no reference object crosses this boundary — and returns
    scaled integers, so the engine never touches a binary float.
    """

    def compute(
        self,
        dense_inputs: Mapping[str, tuple[int, ...]],
        input_scales: Mapping[str, int],
        configuration: ConfiguredIndicator,
    ) -> Result[KernelOutput]:  # pragma: no cover - protocol seam
        ...


class ReferenceKernel:
    """The batch arithmetic bridge that wraps the pinned canonical reference (Story 7.3).

    For a reference-owned single-input, single-output, ``period``-taking formula
    (``sma``, ``ema``, ``wma``, ``rsi``, ``mom``, ``roc``) it descales the dense present
    integers to the analytic reference, delegates to the reference function resolved
    through the canonical-arithmetic seam (wrapping is mandatory; no reference object
    crosses the boundary), and rescales each analytic result to a scaled integer at the
    declared ``output_scale`` under an explicit half-even rounding mode — so no binary
    float persists. The reference's own leading-undefined prefix becomes the lookback;
    NaN and infinity map to an undefined (``None``) dense value, never a stored number.

    The broader wrapper set (multi-output, volume-weighted, session-anchored) lands in
    Story 7.6; a formula outside this bridge's set is refused, never mis-called.
    """

    def __init__(self, *, output_scale: int = DEFAULT_ANALYTIC_SCALE) -> None:
        self._output_scale = output_scale

    def compute(
        self,
        dense_inputs: Mapping[str, tuple[int, ...]],
        input_scales: Mapping[str, int],
        configuration: ConfiguredIndicator,
    ) -> Result[KernelOutput]:
        """Compute dense reference output for the configuration's formula."""
        formula = configuration.formula_id
        if formula not in _SINGLE_INPUT_TIMEPERIOD:
            return _unsupported(
                "formula_id",
                "the batch reference bridge wraps single-input period-taking formulas; "
                "this formula is not in its set (the broader wrapper set is Story 7.6)",
                given=formula,
                supported=sorted(_SINGLE_INPUT_TIMEPERIOD),
            )
        resolved = resolve_canonical_arithmetic(formula)
        if isinstance(resolved, TypedRefusal):
            return resolved
        owner = resolved.value
        if owner.reference_function is None:  # pragma: no cover - ownership registry defends this
            return _unsupported(
                "formula_id",
                "the resolved owner names no reference function to wrap",
                given=formula,
            )
        reference_fn: Any = _reference.reference_function(owner.reference_function)
        if reference_fn is None:
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.NO,
                context={
                    "field": "reference",
                    "reason": "the pinned canonical reference is unavailable; a governed "
                    "producer never falls back to re-implemented arithmetic (FM-2)",
                    "function": owner.reference_function,
                },
            )
        primary = configuration.inputs[0].name
        dense = dense_inputs.get(primary)
        if dense is None:
            return _invalid(
                "dense_inputs", "the primary input column was not supplied", input=primary
            )
        period = _period_param(configuration)
        if isinstance(period, TypedRefusal):
            return period
        analytics = _descale(dense, input_scales.get(primary, 0))
        if isinstance(analytics, TypedRefusal):
            return analytics
        channel = configuration.output_schema[0].name
        return self._run_reference(reference_fn, analytics, period, channel)

    def _run_reference(
        self, reference_fn: Any, analytics: list[float], period: int, channel: str
    ) -> Result[KernelOutput]:
        """Delegate to the reference function and project its output to scaled integers.

        The ``numpy`` conversion is a private detail resolved by name; the reference
        function's leading-undefined prefix is counted as the lookback, and NaN /
        infinity become an undefined (``None``) dense value, never a stored number.
        """
        if not analytics:
            return Ok(KernelOutput(channels={channel: ()}, lookback=0, scale=self._output_scale))
        numpy: Any = importlib.import_module("numpy")
        array: Any = numpy.asarray(analytics, dtype="float64")
        produced: list[float] = [float(item) for item in reference_fn(array, timeperiod=period)]
        dense_output: list[int | None] = []
        lookback = 0
        counting_prefix = True
        for item in produced:
            if math.isnan(item) or math.isinf(item):
                dense_output.append(None)
                if counting_prefix:
                    lookback += 1
                continue
            counting_prefix = False
            dense_output.append(_rescale(item, self._output_scale))
        return Ok(
            KernelOutput(
                channels={channel: tuple(dense_output)},
                lookback=lookback,
                scale=self._output_scale,
            )
        )


def _period_param(configuration: ConfiguredIndicator) -> int | TypedRefusal:
    """Resolve the integer ``period`` parameter of a period-taking formula, or refuse.

    The period is an exact rational with denominator one and a positive numerator; a
    fractional or non-positive period, or an absent one, is refused.
    """
    for name in _PERIOD_NAMES:
        rational = configuration.parameters.get(name)
        if rational is None:
            continue
        if rational.denominator != 1 or rational.numerator < 1:
            return _invalid(
                "parameters",
                "the period is a positive whole number of observations",
                parameter=name,
                given=f"{rational.numerator}/{rational.denominator}",
            )
        return rational.numerator
    return _invalid(
        "parameters",
        "a period-taking formula declares a 'period' (or 'timeperiod') exact-rational parameter",
        expected=list(_PERIOD_NAMES),
    )


def _descale(dense: Sequence[int], scale: int) -> list[float] | TypedRefusal:
    """Descale dense scaled integers to the analytic reference (CT-16 exact-to-analytic).

    A magnitude past float64's exact-integer range is refused rather than silently
    rounded; every other value becomes ``value / 10**scale`` — the pinned descale.
    """
    factor = 10**scale
    out: list[float] = []
    for index, item in enumerate(dense):
        if abs(item) > _FLOAT64_EXACT_INT_MAX:
            return _invalid(
                "values",
                "a bulk value is past float64's exact-integer range; the exact-to-analytic "
                "descale refuses it rather than rounding silently",
                index=index,
                given=item,
            )
        out.append(item / factor)
    return out


def _rescale(value: float, scale: int) -> int:
    """Rescale one finite analytic value to a scaled integer, half-even (CT-16 return).

    The analytic-to-exact return: the exact binary value of the float is shifted to the
    target scale by an exact power of ten and rounded to an integer under an explicit
    half-even rounding mode, with exact integer arithmetic — no binary float persists.
    """
    shifted = Fraction(value) * (10**scale)
    floor_value, remainder = divmod(shifted.numerator, shifted.denominator)
    if remainder == 0:
        return floor_value
    twice = 2 * remainder
    if twice < shifted.denominator:
        return floor_value
    if twice > shifted.denominator:
        return floor_value + 1
    return floor_value if floor_value % 2 == 0 else floor_value + 1


# --- the batch result -------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BatchResult:
    """A batch computation's output: presence-mapped series plus the result label.

    ``outputs`` maps each declared output-channel name to a full-length, index-aligned
    :class:`IndicatorSeries`. ``label`` is the AD-12 result label — producer contract
    identity, format version, input fingerprints, evidence time range, evidence class,
    and world — carrying the whole result's governed-evidence identity (DEC-0110).
    """

    outputs: Mapping[str, IndicatorSeries]
    label: ResultLabel


# --- position classification ------------------------------------------------


class _PositionClass(StrEnum):
    """How one output position is classed from its inputs (internal to the engine)."""

    CLOSED = "closed"
    MISSING = "missing"
    NOT_READY = "not_ready"
    COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class _Layout:
    """The per-position analysis of the aligned input columns (internal)."""

    classes: tuple[_PositionClass, ...]
    dense_index: tuple[int | None, ...]
    provisional: tuple[bool, ...]
    knowable_at: tuple[Instant, ...]
    dense_inputs: Mapping[str, tuple[int, ...]]
    input_scales: Mapping[str, int]


def _analyze_layout(
    names: Sequence[str],
    columns: Sequence[InputSeries],
    missing_value_policy: MissingValuePolicy,
) -> _Layout | TypedRefusal:
    """Classify every position and compact the dense present-observation sequence.

    Schedule dominates: a position any input marks ``absent_by_schedule`` is ``closed``.
    Otherwise a calendar-open gap follows the missing-value policy — ``refuse`` returns a
    policy rejection here, ``mark-gap`` classes it ``missing``. A not-ready input leaves
    the position ``not_ready``; a position whose inputs are all value-bearing is
    ``complete`` and contributes to the dense sequence, flagged provisional when any
    contributing input is provisional. Every position records its knowable-at as the max
    over its inputs — the earliest instant at which every contributing input was knowable.
    """
    length = columns[0].length
    classes: list[_PositionClass] = []
    dense_index: list[int | None] = []
    provisional: list[bool] = []
    knowable_at: list[Instant] = []
    dense: dict[str, list[int]] = {name: [] for name in names}
    for position in range(length):
        states = [column.presence_at(position) for column in columns]
        knowable_at.append(
            max((column.knowable_at[position] for column in columns), key=lambda i: i.value_ns)
        )
        if any(state is PresenceState.ABSENT_BY_SCHEDULE for state in states):
            classes.append(_PositionClass.CLOSED)
            dense_index.append(None)
            provisional.append(False)
        elif any(state is PresenceState.GAP for state in states):
            if missing_value_policy is MissingValuePolicy.REFUSE:
                return _policy(
                    "missing_value_policy",
                    "a calendar-open position has no data and the declared policy refuses; "
                    "never silent-filled (FM-1)",
                    position=position,
                )
            classes.append(_PositionClass.MISSING)
            dense_index.append(None)
            provisional.append(False)
        elif any(state is PresenceState.NOT_READY for state in states):
            classes.append(_PositionClass.NOT_READY)
            dense_index.append(None)
            provisional.append(False)
        else:
            dense_position = len(dense[names[0]])
            for name, column in zip(names, columns, strict=True):
                dense[name].append(column.value_at(position))
            classes.append(_PositionClass.COMPLETE)
            dense_index.append(dense_position)
            provisional.append(any(state is PresenceState.PROVISIONAL for state in states))
    return _Layout(
        classes=tuple(classes),
        dense_index=tuple(dense_index),
        provisional=tuple(provisional),
        knowable_at=tuple(knowable_at),
        dense_inputs={name: tuple(values) for name, values in dense.items()},
        input_scales={name: column.scale for name, column in zip(names, columns, strict=True)},
    )


def _build_channel(
    dense_output: tuple[int | None, ...],
    layout: _Layout,
    warm_up: int,
    in_progress: bool,
    output_scale: int,
) -> Result[IndicatorSeries]:
    """Scatter one channel's dense output back to a full-length presence-mapped series.

    Output length equals input length (begin-index trimming prohibited). A closed
    position is ``absent_by_schedule``, a missing one ``gap``, a not-ready input
    ``not_ready``; a complete position is ``not_ready`` while warm-up is incomplete (a
    marked value, never a number) and otherwise ``present`` — or ``provisional`` when the
    emission policy is in-progress or a contributing input was provisional. No NaN or
    sentinel is ever written.
    """
    values: list[int] = []
    presence: list[PresenceState] = []
    for position, position_class in enumerate(layout.classes):
        if position_class is _PositionClass.CLOSED:
            presence.append(PresenceState.ABSENT_BY_SCHEDULE)
            values.append(0)
        elif position_class is _PositionClass.MISSING:
            presence.append(PresenceState.GAP)
            values.append(0)
        elif position_class is _PositionClass.NOT_READY:
            presence.append(PresenceState.NOT_READY)
            values.append(0)
        else:
            dense_position = layout.dense_index[position]
            resolved = _resolve_complete(dense_output, dense_position, warm_up, layout, in_progress)
            presence.append(resolved[0])
            values.append(resolved[1])
    encoded = encode_int64_values(values)
    if isinstance(encoded, TypedRefusal):
        return encoded
    return IndicatorSeries.try_create(encoded.value, output_scale, presence, layout.knowable_at)


def _resolve_complete(
    dense_output: tuple[int | None, ...],
    dense_position: int | None,
    warm_up: int,
    layout: _Layout,
    in_progress: bool,
) -> tuple[PresenceState, int]:
    """The presence and value of a complete position after warm-up and emission rules."""
    if dense_position is None:  # pragma: no cover - complete positions always carry a dense index
        return PresenceState.NOT_READY, 0
    if dense_position < warm_up:
        return PresenceState.NOT_READY, 0
    value = dense_output[dense_position]
    if value is None:
        return PresenceState.NOT_READY, 0
    if in_progress or layout.provisional[dense_position]:
        return PresenceState.PROVISIONAL, value
    return PresenceState.PRESENT, value


# --- the batch entry point --------------------------------------------------


def compute_batch(
    configuration: object,
    inputs: object,
    *,
    kernel: object,
    world: object,
    evidence_class: object = None,
) -> Result[BatchResult]:
    """Compute a configured indicator over whole input series in batch mode (CT-16).

    Produces one full-length, index-aligned, presence-mapped
    :class:`IndicatorSeries` per declared output channel and the AD-12 result label,
    under as-of-only alignment. The configuration must declare batch mode; every declared
    input name must have an :class:`InputSeries` in ``inputs`` and all columns must be
    index-aligned (equal length). Warm-up must be at least the reference's lookback.
    Schedule, missing-value, warm-up, knowable-at, and provisional-evidence laws are all
    enforced (see the module docstring). Every failure is a returned CT-04 refusal.
    """
    if not isinstance(configuration, ConfiguredIndicator):
        return _invalid(
            "configuration", "a ConfiguredIndicator is required", given=repr(configuration)
        )
    if SupportedMode.BATCH not in configuration.supported_modes:
        return _unsupported(
            "supported_modes",
            "the configuration does not declare batch mode",
            declared=[mode.value for mode in configuration.supported_modes],
        )
    resolved_world = _coerce_world(world)
    if resolved_world is None:
        return _invalid(
            "world",
            "world is one of the closed set",
            given=repr(world),
            allowed=[member.value for member in World],
        )
    resolved_evidence = _coerce_evidence(evidence_class)
    if isinstance(resolved_evidence, TypedRefusal):
        return resolved_evidence
    columns = _resolve_columns(configuration, inputs)
    if isinstance(columns, TypedRefusal):
        return columns
    names = [series_input.name for series_input in configuration.inputs]
    layout = _analyze_layout(names, columns, configuration.missing_value_policy)
    if isinstance(layout, TypedRefusal):
        return layout
    if not isinstance(kernel, BatchKernel):
        return _invalid("kernel", "a BatchKernel is required", given=repr(kernel))
    kernel_output = kernel.compute(layout.dense_inputs, layout.input_scales, configuration)
    if isinstance(kernel_output, TypedRefusal):
        return kernel_output
    produced = kernel_output.value
    if configuration.warm_up < produced.lookback:
        return _invalid(
            "warm_up",
            "warm-up must be at least the reference's lookback (a marked not-ready value "
            "covers every undefined leading position)",
            warm_up=configuration.warm_up,
            reference_lookback=produced.lookback,
        )
    outputs = _build_outputs(configuration, layout, produced)
    if isinstance(outputs, TypedRefusal):
        return outputs
    return _label_result(
        configuration, columns, names, layout, outputs, resolved_world, resolved_evidence
    )


def _resolve_columns(
    configuration: ConfiguredIndicator, inputs: object
) -> list[InputSeries] | TypedRefusal:
    """Resolve every declared input name to an index-aligned :class:`InputSeries`."""
    if not isinstance(inputs, Mapping):
        return _invalid(
            "inputs",
            "inputs are a mapping of input name to InputSeries",
            given=repr(type(inputs).__name__),
        )
    typed_inputs = cast("Mapping[object, object]", inputs)
    columns: list[InputSeries] = []
    for series_input in configuration.inputs:
        column = typed_inputs.get(series_input.name)
        if not isinstance(column, InputSeries):
            return _invalid(
                "inputs",
                "each declared input needs an InputSeries in the inputs mapping",
                input=series_input.name,
            )
        columns.append(column)
    length = columns[0].length
    if length == 0:
        return _invalid("inputs", "a batch computes over a non-empty series")
    for series_input, column in zip(configuration.inputs, columns, strict=True):
        if column.length != length:
            return _invalid(
                "inputs",
                "input columns must be index-aligned (equal length)",
                input=series_input.name,
                length=column.length,
                expected=length,
            )
    return columns


def _build_outputs(
    configuration: ConfiguredIndicator, layout: _Layout, produced: KernelOutput
) -> dict[str, IndicatorSeries] | TypedRefusal:
    """Build one presence-mapped output series per declared output channel."""
    in_progress = (
        configuration.emission_policy is not None
        and configuration.emission_policy.timing is EmissionTiming.IN_PROGRESS
    )
    complete_count = sum(
        1 for position_class in layout.classes if position_class is _PositionClass.COMPLETE
    )
    outputs: dict[str, IndicatorSeries] = {}
    for channel in configuration.output_schema:
        dense_output = produced.channels.get(channel.name)
        if dense_output is None:
            return _invalid(
                "output_schema",
                "the kernel produced no output for this channel",
                channel=channel.name,
            )
        if len(dense_output) != complete_count:
            return _invalid(
                "output_schema",
                "the kernel output length does not match the dense present-observation count",
                channel=channel.name,
                produced=len(dense_output),
                expected=complete_count,
            )
        built = _build_channel(
            dense_output, layout, configuration.warm_up, in_progress, produced.scale
        )
        if isinstance(built, TypedRefusal):
            return built
        outputs[channel.name] = built.value
    return outputs


def _label_result(
    configuration: ConfiguredIndicator,
    columns: Sequence[InputSeries],
    names: Sequence[str],
    layout: _Layout,
    outputs: Mapping[str, IndicatorSeries],
    world: World,
    evidence_class: EvidenceClass | None,
) -> Result[BatchResult]:
    """Assemble the AD-12 result label and the batch result (DEC-0110, DEC-0126)."""
    producer = configuration.fp1()
    if is_refusal(producer):  # pragma: no cover - config content is canonical by construction
        return producer
    input_fingerprints: list[Fingerprint] = []
    for column in columns:
        fp = column.fingerprint()
        if isinstance(fp, TypedRefusal):  # pragma: no cover - series content is canonical
            return fp
        input_fingerprints.append(fp.value)
    interval = _evidence_range(layout.knowable_at)
    if isinstance(interval, TypedRefusal):
        return interval
    any_provisional = any(
        state is PresenceState.PROVISIONAL
        for series in outputs.values()
        for state in series.presence
    )
    resolved_class = (
        EvidenceClass.PROVISIONAL
        if any_provisional
        else (evidence_class if evidence_class is not None else EvidenceClass.CONFIRMED)
    )
    label = ResultLabel.try_create(
        producer_contract_identity=producer.value,
        producer_contract_format_version=configuration.contract_format_version,
        input_fingerprints=input_fingerprints,
        evidence_time_range=interval.value,
        evidence_class=resolved_class,
        world=world,
    )
    if isinstance(label, TypedRefusal):  # pragma: no cover - parts are validated above
        return label
    return Ok(BatchResult(outputs=dict(outputs), label=label.value))


def _evidence_range(knowable_at: Sequence[Instant]) -> Result[Interval]:
    """The half-open evidence time range spanning every position's knowable-at."""
    low = min(instant.value_ns for instant in knowable_at)
    high = max(instant.value_ns for instant in knowable_at)
    start = Instant.try_create(low)
    if is_refusal(start):  # pragma: no cover - low is an existing instant's ns
        return start
    end = Instant.try_create(high + 1)
    if is_refusal(end):
        return end
    return Interval.try_create(start.value, end.value)


def require_governed(result: object) -> Result[ResultLabel]:
    """Assert a batch result may enter governed evidence, or refuse (CT-16; DEC-0126).

    Provisional samples never enter governed evidence: a result whose evidence class is
    provisional, or that carries any provisional output position, is a ``policy
    rejection`` refusal. Otherwise the confirmed :class:`~qmf.core.ResultLabel` is
    returned for the caller to route through the governed-evidence store.
    """
    if not isinstance(result, BatchResult):
        return _invalid("result", "a BatchResult is required", given=repr(result))
    if result.label.evidence_class is EvidenceClass.PROVISIONAL:
        return _policy(
            "evidence_class",
            "provisional evidence never enters governed evidence (FM-1)",
            evidence_class=result.label.evidence_class.value,
        )
    for name, series in result.outputs.items():
        if any(state is PresenceState.PROVISIONAL for state in series.presence):
            return _policy(
                "presence",
                "an output channel carries provisional samples, which never enter "
                "governed evidence",
                channel=name,
            )
    return Ok(result.label)


def _coerce_world(value: object) -> World | None:
    if isinstance(value, World):
        return value
    if isinstance(value, str):
        try:
            return World(value)
        except ValueError:
            return None
    return None


def _coerce_evidence(value: object) -> EvidenceClass | TypedRefusal | None:
    """Resolve an optional evidence class: ``None`` when unset, else a member or refusal."""
    if value is None:
        return None
    if isinstance(value, EvidenceClass):
        return value
    if isinstance(value, str):
        try:
            return EvidenceClass(value)
        except ValueError:
            return _invalid(
                "evidence_class",
                "the evidence class is one of the closed set",
                given=repr(value),
                allowed=[member.value for member in EvidenceClass],
            )
    return _invalid(
        "evidence_class", "the evidence class is a member or its string value", given=repr(value)
    )
