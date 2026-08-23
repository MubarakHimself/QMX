"""Tier-1 tests for CT-16 batch mode — as-of-only alignment and presence-mapped outputs
(COMP-QMF-INDICATORS; Story 7.3).

These tests bind the story's acceptance criteria:

* outputs are full-length and index-aligned to the input with begin-index trimming
  prohibited; every position carries a ``registry:presence_map_states`` value; no NaN or
  sentinel appears; and the indicator receives its BarSpec as data (it never derives bar
  boundaries — it passes knowable-at through unchanged);
* only as-of alignment is permitted for governed evidence; forward-fill or interpolation
  across the evaluation instant is a ``policy rejection`` refusal (FM-1);
* a market-hours-closed position is ``absent_by_schedule`` (never a gap), and a
  calendar-open position with no data follows the declared missing-value policy — a gap
  or a refusal, never silent filling; and
* warm-up is an integer count of completed observations at least the reference's
  lookback; during warm-up the output is a marked not-ready value, never a number; every
  output sample carries a knowable-at; and provisional samples never enter governed
  evidence.

The engine tests drive a pure in-test kernel so presence, alignment, and warm-up are
asserted deterministically; a final group drives the real :class:`ReferenceKernel` so the
canonical TA-Lib wrapping is exercised end to end on this machine.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypeVar

import pytest
from qmf.core import (
    CalendarIdentity,
    EvidenceClass,
    ExactRational,
    Instant,
    Instrument,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    UnitKind,
    VenueId,
    World,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.indicators import (
    AlignmentMode,
    AlignmentPolicy,
    ArithmeticReference,
    ChannelKind,
    ConfiguredIndicator,
    EmissionPolicy,
    EmissionTiming,
    IndicatorSeries,
    InputSeries,
    KernelOutput,
    MissingValuePolicy,
    OutputArity,
    OutputChannel,
    PresenceState,
    QuoteSide,
    ReferenceKernel,
    SeriesInput,
    SupportedMode,
    _reference,
    align_to_instant,
    compute_batch,
    presence_code,
    presence_from_code,
    reference_status,
    require_governed,
)
from qmf.indicators.series import encode_int64_values

T = TypeVar("T")


def _unwrap(result: Result[T]) -> T:
    assert is_ok(result), f"expected Ok, got {result}"
    return result.value


# --- fixtures ---------------------------------------------------------------


def _instrument() -> Instrument:
    return _unwrap(Instrument.try_create(_unwrap(VenueId.try_create("venue-ic")), "EURUSD"))


def _calendar() -> CalendarIdentity:
    return _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))


def _period(numerator: int = 3, denominator: int = 1) -> ExactRational:
    return _unwrap(ExactRational.try_create(numerator, denominator, UnitKind.COUNT))


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


def _output_channel(name: str = "sma") -> OutputChannel:
    return _unwrap(
        OutputChannel.try_create(name, ChannelKind.FLOAT_ANALYTIC, OutputArity.SCALAR_PER_SAMPLE, 0)
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
        "parameters": {"period": _period(3)},
        "inputs": [_series_input("close")],
        "calendar_requirements": [_calendar()],
        "alignment_policy": AlignmentPolicy.AS_OF,
        "missing_value_policy": MissingValuePolicy.MARK_GAP,
        "warm_up": 3,
        "output_schema": [_output_channel("sma")],
        "supported_modes": [SupportedMode.BATCH, SupportedMode.STREAMING],
        "arithmetic_reference_configuration": _arithmetic_reference(),
    }
    kwargs.update(overrides)
    return _unwrap(ConfiguredIndicator.try_create(**kwargs))


def _instants(count: int, start: int = 1_000) -> list[Instant]:
    return [_unwrap(Instant.try_create(start + step)) for step in range(count)]


def _input(
    scaled: Sequence[int],
    presence: Sequence[PresenceState],
    *,
    scale: int = 2,
    start: int = 1_000,
) -> InputSeries:
    return _unwrap(
        InputSeries.from_values(list(scaled), scale, list(presence), _instants(len(scaled), start))
    )


# --- an in-test kernel ------------------------------------------------------


class _EchoKernel:
    """A pure kernel: it echoes the primary dense input as the single output channel.

    ``lookback`` leading dense positions are undefined (``None``); the rest echo the input
    value. It lets the engine's presence, warm-up, and scatter behaviour be asserted
    deterministically without invoking the reference.
    """

    def __init__(self, *, lookback: int = 0, scale: int = 2) -> None:
        self._lookback = lookback
        self._scale = scale

    def compute(
        self,
        dense_inputs: Mapping[str, tuple[int, ...]],
        input_scales: Mapping[str, int],
        configuration: ConfiguredIndicator,
    ) -> Result[KernelOutput]:
        primary = configuration.inputs[0].name
        dense = dense_inputs[primary]
        channel = configuration.output_schema[0].name
        prefix = min(self._lookback, len(dense))
        values: list[int | None] = [None] * prefix + list(dense[prefix:])
        return Ok(
            KernelOutput(
                channels={channel: tuple(values)}, lookback=self._lookback, scale=self._scale
            )
        )


# --- AC1: full-length, index-aligned, presence-mapped, no NaN ---------------


def test_output_is_full_length_and_index_aligned() -> None:
    presence = [PresenceState.PRESENT] * 6
    series = _input([1, 2, 3, 4, 5, 6], presence)
    result = _unwrap(
        compute_batch(
            _config(warm_up=0), {"close": series}, kernel=_EchoKernel(), world=World.REPLAY
        )
    )
    out = result.outputs["sma"]
    # Begin-index trimming is prohibited: output length equals input length exactly.
    assert out.length == series.length == 6
    # Every position carries a presence-map state.
    assert len(out.presence) == 6
    assert all(isinstance(state, PresenceState) for state in out.presence)


def test_warm_up_prefix_is_not_ready_not_trimmed() -> None:
    # warm_up=3 leaves the first three complete positions not-ready but present in the
    # output — never trimmed off the front (no begin-index trimming).
    series = _input([10, 20, 30, 40, 50], [PresenceState.PRESENT] * 5)
    out = _unwrap(
        compute_batch(
            _config(warm_up=3), {"close": series}, kernel=_EchoKernel(), world=World.REPLAY
        )
    ).outputs["sma"]
    assert out.length == 5
    assert [state.value for state in out.presence] == [
        "not_ready",
        "not_ready",
        "not_ready",
        "present",
        "present",
    ]
    assert out.value_at(3) == 40
    assert out.value_at(4) == 50


def test_indicator_passes_knowable_at_through_and_derives_no_boundaries() -> None:
    # The indicator receives its BarSpec as data: it never derives bar boundaries, so the
    # output's knowable-at is exactly the input's, position for position.
    series = _input([1, 2, 3], [PresenceState.PRESENT] * 3, start=5_000)
    out = _unwrap(
        compute_batch(
            _config(warm_up=0), {"close": series}, kernel=_EchoKernel(), world=World.REPLAY
        )
    ).outputs["sma"]
    assert [instant.value_ns for instant in out.knowable_at] == [5_000, 5_001, 5_002]


# --- AC3: schedule vs missing -----------------------------------------------


def test_calendar_closed_is_absent_by_schedule_never_gap() -> None:
    presence = [
        PresenceState.PRESENT,
        PresenceState.ABSENT_BY_SCHEDULE,
        PresenceState.PRESENT,
    ]
    out = _unwrap(
        compute_batch(
            _config(warm_up=0),
            {"close": _input([1, 0, 3], presence)},
            kernel=_EchoKernel(),
            world=World.REPLAY,
        )
    ).outputs["sma"]
    assert out.presence[1] is PresenceState.ABSENT_BY_SCHEDULE


def test_calendar_open_gap_marks_gap_under_mark_gap_policy() -> None:
    presence = [PresenceState.PRESENT, PresenceState.GAP, PresenceState.PRESENT]
    out = _unwrap(
        compute_batch(
            _config(warm_up=0, missing_value_policy=MissingValuePolicy.MARK_GAP),
            {"close": _input([1, 0, 3], presence)},
            kernel=_EchoKernel(),
            world=World.REPLAY,
        )
    ).outputs["sma"]
    assert out.presence[1] is PresenceState.GAP


def test_calendar_open_gap_refuses_under_refuse_policy() -> None:
    presence = [PresenceState.PRESENT, PresenceState.GAP, PresenceState.PRESENT]
    refusal = compute_batch(
        _config(warm_up=0, missing_value_policy=MissingValuePolicy.REFUSE),
        {"close": _input([1, 0, 3], presence)},
        kernel=_EchoKernel(),
        world=World.REPLAY,
    )
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert refusal.context["field"] == "missing_value_policy"


def test_no_nan_or_sentinel_at_non_present_positions() -> None:
    # A non-present position carries a presence state, never a NaN or sentinel value; the
    # bulk form has no NaN (it is int64), and the value slot at a gap is a placeholder the
    # presence map forbids reading as data.
    presence = [PresenceState.PRESENT, PresenceState.GAP, PresenceState.ABSENT_BY_SCHEDULE]
    out = _unwrap(
        compute_batch(
            _config(warm_up=0),
            {"close": _input([7, 0, 0], presence)},
            kernel=_EchoKernel(),
            world=World.REPLAY,
        )
    ).outputs["sma"]
    assert out.presence[1] is PresenceState.GAP
    assert out.presence[2] is PresenceState.ABSENT_BY_SCHEDULE


# --- AC2: as-of only, forward-fill / interpolation refused ------------------


def test_as_of_alignment_picks_last_present_at_or_before() -> None:
    series = _input([10, 20, 30, 40], [PresenceState.PRESENT] * 4, start=100)
    out = _unwrap(
        compute_batch(
            _config(warm_up=0), {"close": series}, kernel=_EchoKernel(), world=World.REPLAY
        )
    ).outputs["sma"]
    sample = _unwrap(align_to_instant(out, _unwrap(Instant.try_create(102)), AlignmentMode.AS_OF))
    assert sample.presence is PresenceState.PRESENT
    assert sample.index == 2
    assert sample.value == 30
    assert sample.knowable_at is not None and sample.knowable_at.value_ns == 102


def test_as_of_returns_not_ready_when_nothing_known_yet() -> None:
    series = _input([10, 20], [PresenceState.PRESENT] * 2, start=100)
    out = _unwrap(
        compute_batch(
            _config(warm_up=0), {"close": series}, kernel=_EchoKernel(), world=World.REPLAY
        )
    ).outputs["sma"]
    sample = _unwrap(align_to_instant(out, _unwrap(Instant.try_create(50)), AlignmentMode.AS_OF))
    assert sample.presence is PresenceState.NOT_READY
    assert sample.value is None
    assert sample.index is None


def test_forward_fill_across_the_instant_is_policy_rejection() -> None:
    series = _input([10, 20], [PresenceState.PRESENT] * 2)
    refusal = align_to_instant(
        series, _unwrap(Instant.try_create(1_000)), AlignmentMode.FORWARD_FILL
    )
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert refusal.retryability is Retryability.NO


def test_interpolation_across_the_instant_is_policy_rejection() -> None:
    series = _input([10, 20], [PresenceState.PRESENT] * 2)
    refusal = align_to_instant(
        series, _unwrap(Instant.try_create(1_000)), AlignmentMode.INTERPOLATE
    )
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION


def test_as_of_alignment_string_mode_and_bad_inputs_refuse() -> None:
    series = _input([10], [PresenceState.PRESENT])
    # A string alignment mode is coerced; a good one works.
    assert is_ok(align_to_instant(series, _unwrap(Instant.try_create(2_000)), "as-of"))
    # A bad mode string is invalid input.
    bad_mode = align_to_instant(series, _unwrap(Instant.try_create(2_000)), "nearest")
    assert is_refusal(bad_mode) and bad_mode.context["field"] == "mode"
    # A non-series and a non-instant refuse.
    assert is_refusal(
        align_to_instant(object(), _unwrap(Instant.try_create(1)), AlignmentMode.AS_OF)
    )
    assert is_refusal(align_to_instant(series, 123, AlignmentMode.AS_OF))
    assert is_refusal(align_to_instant(series, _unwrap(Instant.try_create(1)), 42))


def test_as_of_skips_non_present_positions() -> None:
    presence = [PresenceState.PRESENT, PresenceState.GAP, PresenceState.NOT_READY]
    series = _input([10, 0, 0], presence, start=100)
    sample = _unwrap(
        align_to_instant(series, _unwrap(Instant.try_create(102)), AlignmentMode.AS_OF)
    )
    # The gap and not-ready positions carry no value; the as-of pick is the present one.
    assert sample.index == 0
    assert sample.value == 10


# --- AC4: warm-up, knowable-at, provisional ---------------------------------


def test_warm_up_below_reference_lookback_is_refused() -> None:
    series = _input([1, 2, 3, 4], [PresenceState.PRESENT] * 4)
    refusal = compute_batch(
        _config(warm_up=1), {"close": series}, kernel=_EchoKernel(lookback=3), world=World.REPLAY
    )
    assert is_refusal(refusal)
    assert refusal.context["field"] == "warm_up"
    assert refusal.context["reference_lookback"] == 3


def test_every_output_sample_carries_a_knowable_at() -> None:
    presence = [
        PresenceState.PRESENT,
        PresenceState.GAP,
        PresenceState.ABSENT_BY_SCHEDULE,
        PresenceState.PRESENT,
    ]
    series = _input([1, 0, 0, 4], presence, start=200)
    out = _unwrap(
        compute_batch(
            _config(warm_up=0), {"close": series}, kernel=_EchoKernel(), world=World.REPLAY
        )
    ).outputs["sma"]
    assert [instant.value_ns for instant in out.knowable_at] == [200, 201, 202, 203]
    assert len(out.knowable_at) == out.length


def test_in_progress_emission_marks_provisional_and_bars_governed_evidence() -> None:
    emission = _unwrap(EmissionPolicy.try_create(EmissionTiming.IN_PROGRESS, "per-update"))
    series = _input([10, 20, 30], [PresenceState.PRESENT] * 3)
    result = _unwrap(
        compute_batch(
            _config(warm_up=0, emission_policy=emission),
            {"close": series},
            kernel=_EchoKernel(),
            world=World.REPLAY,
        )
    )
    out = result.outputs["sma"]
    assert all(state is PresenceState.PROVISIONAL for state in out.presence)
    assert result.label.evidence_class is EvidenceClass.PROVISIONAL
    governed = require_governed(result)
    assert is_refusal(governed)
    assert governed.category is RefusalCategory.POLICY_REJECTION


def test_bar_closed_result_is_confirmed_and_governable() -> None:
    series = _input([10, 20, 30], [PresenceState.PRESENT] * 3)
    result = _unwrap(
        compute_batch(
            _config(warm_up=0), {"close": series}, kernel=_EchoKernel(), world=World.REPLAY
        )
    )
    assert result.label.evidence_class is EvidenceClass.CONFIRMED
    assert is_ok(require_governed(result))


def test_explicit_evidence_class_is_honored_when_not_provisional() -> None:
    series = _input([10, 20, 30], [PresenceState.PRESENT] * 3)
    result = _unwrap(
        compute_batch(
            _config(warm_up=0),
            {"close": series},
            kernel=_EchoKernel(),
            world=World.REPLAY,
            evidence_class=EvidenceClass.UNCONFIRMED,
        )
    )
    assert result.label.evidence_class is EvidenceClass.UNCONFIRMED


def test_provisional_input_forces_provisional_output() -> None:
    presence = [PresenceState.PRESENT, PresenceState.PROVISIONAL, PresenceState.PRESENT]
    series = _input([10, 20, 30], presence)
    result = _unwrap(
        compute_batch(
            _config(warm_up=0), {"close": series}, kernel=_EchoKernel(), world=World.REPLAY
        )
    )
    out = result.outputs["sma"]
    assert out.presence[1] is PresenceState.PROVISIONAL
    assert result.label.evidence_class is EvidenceClass.PROVISIONAL


# --- result label -----------------------------------------------------------


def test_result_label_carries_producer_and_input_identity() -> None:
    config = _config(warm_up=0)
    series = _input([1, 2, 3], [PresenceState.PRESENT] * 3)
    result = _unwrap(
        compute_batch(config, {"close": series}, kernel=_EchoKernel(), world=World.LIVE)
    )
    assert result.label.producer_contract_identity == _unwrap(config.fp1())
    assert result.label.producer_contract_format_version == config.contract_format_version
    assert result.label.world is World.LIVE
    # The input column's fingerprint enters the label's input-fingerprint set.
    input_fp = _unwrap(fingerprint(series))
    assert result.label.input_fingerprints == (input_fp,)


def test_evidence_time_range_spans_every_knowable_at() -> None:
    series = _input([1, 2, 3], [PresenceState.PRESENT] * 3, start=700)
    result = _unwrap(
        compute_batch(
            _config(warm_up=0), {"close": series}, kernel=_EchoKernel(), world=World.REPLAY
        )
    )
    interval = result.label.evidence_time_range
    assert interval.start.value_ns == 700
    assert interval.end.value_ns == 703  # half-open: last knowable-at (702) + 1


# --- multi-input ------------------------------------------------------------


def _two_input_config(**overrides: object) -> ConfiguredIndicator:
    return _config(inputs=[_series_input("high"), _series_input("low")], **overrides)


def test_multi_input_absent_dominates_and_knowable_at_is_the_max() -> None:
    config = _two_input_config(warm_up=0)
    high = _input(
        [10, 20, 30],
        [PresenceState.PRESENT, PresenceState.ABSENT_BY_SCHEDULE, PresenceState.PRESENT],
        start=1_000,
    )
    low = _input(
        [1, 2, 3],
        [PresenceState.PRESENT, PresenceState.PRESENT, PresenceState.PRESENT],
        start=1_005,
    )
    out = _unwrap(
        compute_batch(config, {"high": high, "low": low}, kernel=_EchoKernel(), world=World.REPLAY)
    ).outputs["sma"]
    # Any absent input closes the position by schedule.
    assert out.presence[1] is PresenceState.ABSENT_BY_SCHEDULE
    # Knowable-at is the max across the two inputs per position (low starts later).
    assert [instant.value_ns for instant in out.knowable_at] == [1_005, 1_006, 1_007]


def test_multi_input_gap_in_one_column_marks_gap() -> None:
    config = _two_input_config(warm_up=0)
    high = _input([10, 20], [PresenceState.PRESENT, PresenceState.GAP])
    low = _input([1, 2], [PresenceState.PRESENT, PresenceState.PRESENT])
    out = _unwrap(
        compute_batch(config, {"high": high, "low": low}, kernel=_EchoKernel(), world=World.REPLAY)
    ).outputs["sma"]
    assert out.presence[1] is PresenceState.GAP


def test_not_ready_input_leaves_output_not_ready() -> None:
    presence = [PresenceState.PRESENT, PresenceState.NOT_READY, PresenceState.PRESENT]
    series = _input([10, 0, 30], presence)
    out = _unwrap(
        compute_batch(
            _config(warm_up=0), {"close": series}, kernel=_EchoKernel(), world=World.REPLAY
        )
    ).outputs["sma"]
    assert out.presence[1] is PresenceState.NOT_READY


# --- compute_batch validation paths -----------------------------------------


def test_compute_batch_rejects_non_configuration() -> None:
    refusal = compute_batch(object(), {}, kernel=_EchoKernel(), world=World.REPLAY)
    assert is_refusal(refusal) and refusal.context["field"] == "configuration"


def test_compute_batch_requires_batch_mode() -> None:
    config = _config(supported_modes=[SupportedMode.STREAMING])
    series = _input([1, 2, 3], [PresenceState.PRESENT] * 3)
    refusal = compute_batch(config, {"close": series}, kernel=_EchoKernel(), world=World.REPLAY)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_compute_batch_rejects_bad_world_and_evidence_class() -> None:
    series = _input([1, 2, 3], [PresenceState.PRESENT] * 3)
    bad_world = compute_batch(
        _config(warm_up=0), {"close": series}, kernel=_EchoKernel(), world="mars"
    )
    assert is_refusal(bad_world) and bad_world.context["field"] == "world"
    bad_ev = compute_batch(
        _config(warm_up=0),
        {"close": series},
        kernel=_EchoKernel(),
        world=World.REPLAY,
        evidence_class="???",
    )
    assert is_refusal(bad_ev) and bad_ev.context["field"] == "evidence_class"


def test_compute_batch_rejects_missing_or_misaligned_inputs() -> None:
    series = _input([1, 2, 3], [PresenceState.PRESENT] * 3)
    # Not a mapping.
    assert is_refusal(compute_batch(_config(), object(), kernel=_EchoKernel(), world=World.REPLAY))
    # Missing the declared input.
    missing = compute_batch(_config(), {"other": series}, kernel=_EchoKernel(), world=World.REPLAY)
    assert is_refusal(missing) and missing.context["field"] == "inputs"
    # Empty series.
    empty = _unwrap(InputSeries.from_values([], 2, [], []))
    assert is_refusal(
        compute_batch(
            _config(warm_up=0), {"close": empty}, kernel=_EchoKernel(), world=World.REPLAY
        )
    )
    # Misaligned column lengths.
    config = _two_input_config(warm_up=0)
    high = _input([1, 2, 3], [PresenceState.PRESENT] * 3)
    low = _input([1, 2], [PresenceState.PRESENT] * 2)
    misaligned = compute_batch(
        config, {"high": high, "low": low}, kernel=_EchoKernel(), world=World.REPLAY
    )
    assert is_refusal(misaligned) and misaligned.context["expected"] == 3


def test_compute_batch_rejects_non_kernel_and_bad_kernel_output() -> None:
    series = _input([1, 2, 3], [PresenceState.PRESENT] * 3)
    assert is_refusal(
        compute_batch(_config(warm_up=0), {"close": series}, kernel=object(), world=World.REPLAY)
    )

    class _WrongChannelKernel:
        def compute(
            self,
            dense_inputs: Mapping[str, tuple[int, ...]],
            input_scales: Mapping[str, int],
            configuration: ConfiguredIndicator,
        ) -> Result[KernelOutput]:
            return Ok(KernelOutput(channels={"other": (1, 2, 3)}, lookback=0, scale=2))

    wrong = compute_batch(
        _config(warm_up=0), {"close": series}, kernel=_WrongChannelKernel(), world=World.REPLAY
    )
    assert is_refusal(wrong) and wrong.context["field"] == "output_schema"

    class _WrongLengthKernel:
        def compute(
            self,
            dense_inputs: Mapping[str, tuple[int, ...]],
            input_scales: Mapping[str, int],
            configuration: ConfiguredIndicator,
        ) -> Result[KernelOutput]:
            return Ok(KernelOutput(channels={"sma": (1, 2)}, lookback=0, scale=2))

    bad_len = compute_batch(
        _config(warm_up=0), {"close": series}, kernel=_WrongLengthKernel(), world=World.REPLAY
    )
    assert is_refusal(bad_len) and bad_len.context["expected"] == 3


def test_compute_batch_propagates_a_kernel_refusal() -> None:
    series = _input([1, 2, 3], [PresenceState.PRESENT] * 3)

    class _RefusingKernel:
        def compute(
            self,
            dense_inputs: Mapping[str, tuple[int, ...]],
            input_scales: Mapping[str, int],
            configuration: ConfiguredIndicator,
        ) -> Result[KernelOutput]:
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.NO,
                context={"field": "reference"},
            )

    refusal = compute_batch(
        _config(warm_up=0), {"close": series}, kernel=_RefusingKernel(), world=World.REPLAY
    )
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_require_governed_rejects_non_result() -> None:
    assert is_refusal(require_governed(object()))


# --- the bulk series vocabulary ---------------------------------------------


def test_presence_code_round_trips() -> None:
    for state in PresenceState:
        assert presence_from_code(presence_code(state)) is state
    # The registry's declared order pins the integer codes.
    assert presence_code(PresenceState.PRESENT) == 0
    assert presence_code(PresenceState.ABSENT_BY_SCHEDULE) == 4


def test_presence_from_code_rejects_unknown_and_non_int() -> None:
    assert presence_from_code(99) is None
    assert presence_from_code(True) is None
    assert presence_from_code("present") is None


def test_encode_int64_values_refuses_non_int_and_out_of_range() -> None:
    assert is_refusal(encode_int64_values([1, "x", 3]))
    assert is_refusal(encode_int64_values([2**63]))
    assert is_refusal(encode_int64_values([-(2**63) - 1]))
    assert is_ok(encode_int64_values([0, -1, 2**62]))


def test_input_series_round_trips_values_and_buffer() -> None:
    series = _input([5, -7, 9], [PresenceState.PRESENT] * 3)
    assert series.length == 3
    assert [series.value_at(index) for index in range(3)] == [5, -7, 9]
    assert series.presence_at(1) is PresenceState.PRESENT
    # The exposed buffer is a read-only view over the immutable int64 byte layout.
    assert series.buffer.readonly is True
    assert len(series.buffer) == 3 * 8


def test_input_series_value_at_out_of_range_raises() -> None:
    series = _input([1, 2], [PresenceState.PRESENT] * 2)
    with pytest.raises(IndexError):
        series.value_at(5)


def test_input_series_validation_paths() -> None:
    good_instants = _instants(2)
    # Odd byte length is not a whole number of int64 values.
    assert is_refusal(
        InputSeries.try_create(b"\x00\x01\x02", 2, [PresenceState.PRESENT], good_instants[:1])
    )
    # Bad scale.
    assert is_refusal(
        InputSeries.try_create(
            _unwrap(encode_int64_values([1])), -1, [PresenceState.PRESENT], good_instants[:1]
        )
    )
    # Presence not a sequence of states.
    assert is_refusal(
        InputSeries.try_create(_unwrap(encode_int64_values([1])), 2, "present", good_instants[:1])
    )
    # Knowable-at not a sequence of instants.
    assert is_refusal(
        InputSeries.try_create(_unwrap(encode_int64_values([1])), 2, [PresenceState.PRESENT], [123])
    )
    # Parallel-length mismatch (values vs presence).
    assert is_refusal(
        InputSeries.try_create(
            _unwrap(encode_int64_values([1, 2])), 2, [PresenceState.PRESENT], good_instants
        )
    )
    # Parallel-length mismatch (values vs knowable-at).
    assert is_refusal(
        InputSeries.try_create(
            _unwrap(encode_int64_values([1, 2])), 2, [PresenceState.PRESENT] * 2, good_instants[:1]
        )
    )
    # from_values over a non-sequence.
    assert is_refusal(InputSeries.from_values(object(), 2, [], []))
    # A memoryview is accepted (snapshotted to immutable bytes).
    view = memoryview(_unwrap(encode_int64_values([4, 5])))
    assert is_ok(InputSeries.try_create(view, 0, [PresenceState.PRESENT] * 2, good_instants))
    # Presence state strings are coerced; a bad token refuses.
    assert is_ok(
        InputSeries.try_create(_unwrap(encode_int64_values([1])), 0, ["present"], good_instants[:1])
    )
    assert is_refusal(
        InputSeries.try_create(_unwrap(encode_int64_values([1])), 0, ["nope"], good_instants[:1])
    )


def test_indicator_series_equality_rules() -> None:
    knowable = _instants(3)
    presence = [PresenceState.NOT_READY, PresenceState.PRESENT, PresenceState.GAP]
    left = _unwrap(
        IndicatorSeries.try_create(_unwrap(encode_int64_values([0, 42, 0])), 2, presence, knowable)
    )
    same = _unwrap(
        IndicatorSeries.try_create(_unwrap(encode_int64_values([0, 42, 0])), 2, presence, knowable)
    )
    assert _unwrap(left.equals(same)) is True
    # A differing presence map is unequal.
    other_presence = [PresenceState.PRESENT, PresenceState.PRESENT, PresenceState.GAP]
    diff_presence = _unwrap(
        IndicatorSeries.try_create(
            _unwrap(encode_int64_values([0, 42, 0])), 2, other_presence, knowable
        )
    )
    assert _unwrap(left.equals(diff_presence)) is False
    # A differing value at a present position is unequal.
    diff_value = _unwrap(
        IndicatorSeries.try_create(_unwrap(encode_int64_values([0, 43, 0])), 2, presence, knowable)
    )
    assert _unwrap(left.equals(diff_value)) is False
    # Equality compares only present positions: the not-ready slot's value is ignored.
    diff_hidden = _unwrap(
        IndicatorSeries.try_create(
            _unwrap(encode_int64_values([999, 42, 0])), 2, presence, knowable
        )
    )
    assert _unwrap(left.equals(diff_hidden)) is True
    # Non-series operand refuses.
    assert is_refusal(left.equals(object()))
    # A digest-bearing identity fingerprints without a float.
    assert is_ok(left.fingerprint())


# --- the real reference kernel (canonical TA-Lib wrapping) ------------------


def _require_reference() -> None:
    if not is_ok(reference_status()):
        pytest.skip("the pinned canonical reference is unavailable on this machine")


def test_reference_kernel_computes_canonical_sma() -> None:
    _require_reference()
    # SMA period 2 over [3, 6, 9] at input scale 0 -> [not_ready, 4.5, 7.5]; stored at the
    # analytic output scale (8): 4.5 -> 450000000, 7.5 -> 750000000. The reference lookback
    # is 1, so warm_up=1 leaves exactly the first position not-ready.
    config = _config(parameters={"period": _period(2)}, warm_up=1)
    series = _input([3, 6, 9], [PresenceState.PRESENT] * 3, scale=0)
    out = _unwrap(
        compute_batch(config, {"close": series}, kernel=ReferenceKernel(), world=World.REPLAY)
    ).outputs["sma"]
    assert out.scale == 8
    assert [state.value for state in out.presence] == ["not_ready", "present", "present"]
    assert out.value_at(1) == 450_000_000
    assert out.value_at(2) == 750_000_000


def test_reference_kernel_output_equals_across_scales() -> None:
    _require_reference()
    config = _config(parameters={"period": _period(2)}, warm_up=1)
    series = _input([3, 6, 9], [PresenceState.PRESENT] * 3, scale=0)
    out = _unwrap(
        compute_batch(config, {"close": series}, kernel=ReferenceKernel(), world=World.REPLAY)
    ).outputs["sma"]
    # A hand-built series at a coarser scale but equal magnitudes compares equal at present
    # positions (presence maps match, values compared across scales).
    coarse = _unwrap(
        IndicatorSeries.try_create(
            _unwrap(encode_int64_values([0, 4_500_000, 7_500_000])),
            6,
            list(out.presence),
            list(out.knowable_at),
        )
    )
    assert _unwrap(out.equals(coarse)) is True


def test_reference_kernel_refuses_unsupported_formula() -> None:
    _require_reference()
    config = _config(formula_id="obv")
    series = _input([1, 2, 3], [PresenceState.PRESENT] * 3)
    refusal = compute_batch(config, {"close": series}, kernel=ReferenceKernel(), world=World.REPLAY)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_reference_kernel_requires_a_period_parameter() -> None:
    _require_reference()
    config = _config(parameters={})
    series = _input([1, 2, 3], [PresenceState.PRESENT] * 3)
    refusal = compute_batch(config, {"close": series}, kernel=ReferenceKernel(), world=World.REPLAY)
    assert is_refusal(refusal) and refusal.context["field"] == "parameters"


def test_reference_kernel_refuses_fractional_period() -> None:
    _require_reference()
    config = _config(parameters={"period": _period(5, 2)}, warm_up=3)
    series = _input([1, 2, 3, 4], [PresenceState.PRESENT] * 4)
    refusal = compute_batch(config, {"close": series}, kernel=ReferenceKernel(), world=World.REPLAY)
    assert is_refusal(refusal) and refusal.context["field"] == "parameters"


def test_reference_kernel_refuses_value_past_float64_exact_range() -> None:
    _require_reference()
    huge = 2**53 + 1
    config = _config(parameters={"period": _period(2)}, warm_up=1)
    series = _input([huge, huge, huge], [PresenceState.PRESENT] * 3, scale=0)
    refusal = compute_batch(config, {"close": series}, kernel=ReferenceKernel(), world=World.REPLAY)
    assert is_refusal(refusal) and refusal.context["field"] == "values"


def test_reference_kernel_refuses_when_reference_function_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _require_reference()

    def _no_reference(name: object) -> None:
        return None

    monkeypatch.setattr(_reference, "reference_function", _no_reference)
    config = _config(parameters={"period": _period(2)}, warm_up=1)
    series = _input([3, 6, 9], [PresenceState.PRESENT] * 3, scale=0)
    refusal = compute_batch(config, {"close": series}, kernel=ReferenceKernel(), world=World.REPLAY)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_reference_kernel_handles_gaps_by_computing_over_present_observations() -> None:
    _require_reference()
    # A gap does not silent-fill: SMA jumps across it, computing over the present
    # observations only, and the gap position stays a gap in the output.
    config = _config(parameters={"period": _period(2)}, warm_up=1)
    presence = [
        PresenceState.PRESENT,
        PresenceState.GAP,
        PresenceState.PRESENT,
        PresenceState.PRESENT,
    ]
    series = _input([2, 0, 6, 8], presence, scale=0)
    out = _unwrap(
        compute_batch(config, {"close": series}, kernel=ReferenceKernel(), world=World.REPLAY)
    ).outputs["sma"]
    assert [state.value for state in out.presence] == ["not_ready", "gap", "present", "present"]
    # Present observations are [2, 6, 8]; SMA(2): pos 2 -> (2+6)/2 = 4, pos 3 -> (6+8)/2 = 7.
    assert out.value_at(2) == 400_000_000
    assert out.value_at(3) == 700_000_000
