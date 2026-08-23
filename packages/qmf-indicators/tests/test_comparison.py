"""Tier-1 tests for the CT-16 FM-4 arithmetic-upgrade comparison suite
(COMP-QMF-INDICATORS; Story 7.6).

These tests bind the story's fourth acceptance criterion: an upgrade to the canonical
reference that changes output for identical canonical inputs is caught by the comparison
suite **before the upgrade lands**, and the change mints the **per-configured-indicator**
contract format version with recorded before/after evidence — **never a silent accept** and
**never a protocol-wide bump** (FM-4).

The suite is a pure comparison over two :class:`BatchResult`\\ s. The *before* result is
computed with the real canonical reference; the *after* result models a candidate reference
that produced a differing (or identical) output over the same canonical inputs.
"""

from __future__ import annotations

from typing import TypeVar

import pytest
from qmf.core import (
    CalendarIdentity,
    ExactRational,
    Instant,
    Instrument,
    Result,
    UnitKind,
    VenueId,
    World,
    is_ok,
    is_refusal,
)
from qmf.indicators import (
    ArithmeticReference,
    BatchResult,
    ChannelKind,
    ComparisonReport,
    ConfiguredIndicator,
    ContractFormatMint,
    IndicatorSeries,
    InputSeries,
    ModeEqualityComparator,
    OutputChangeVerdict,
    PresenceState,
    QuoteSide,
    ReferenceKernel,
    SeriesInput,
    compare_reference_outputs,
    compute_batch,
    configure_wrapper,
    reference_status,
)
from qmf.indicators.configured_indicator import CONTRACT_FORMAT_VERSION
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


def _reference() -> ArithmeticReference:
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
        "period": _period(3),
        "inputs": [_series_input("close")],
        "calendar_requirements": [_calendar()],
        "arithmetic_reference_configuration": _reference(),
    }
    kwargs.update(overrides)
    return _unwrap(configure_wrapper(**kwargs))


_VALUES = [3, 6, 9, 12, 15, 18]


def _instants(count: int) -> list[Instant]:
    return [_unwrap(Instant.try_create(1_000 + step)) for step in range(count)]


def _require_reference() -> None:
    if not is_ok(reference_status()):
        pytest.skip("the pinned canonical reference is unavailable on this machine")


def _before_result(config: object, values: list[int] | None = None) -> BatchResult:
    resolved = values if values is not None else _VALUES
    instants = _instants(len(resolved))
    series = _unwrap(
        InputSeries.from_values(resolved, 0, [PresenceState.PRESENT] * len(resolved), instants)
    )
    return _unwrap(
        compute_batch(config, {"close": series}, kernel=ReferenceKernel(), world=World.REPLAY)
    )


def _perturb_channel(result: BatchResult, channel: str, *, delta: int) -> BatchResult:
    """A candidate-reference result: the same series with one present value nudged by delta."""
    series = result.outputs[channel]
    values = [series.value_at(index) for index in range(series.length)]
    for index, state in enumerate(series.presence):
        if state is PresenceState.PRESENT:
            values[index] += delta
            break
    changed = _unwrap(
        IndicatorSeries.try_create(
            _unwrap(encode_int64_values(values)),
            series.scale,
            list(series.presence),
            list(series.knowable_at),
        )
    )
    outputs = dict(result.outputs)
    outputs[channel] = changed
    return BatchResult(outputs=outputs, label=result.label)


# --- AC4: an output change is caught and mints, never silently -------------


def test_identical_output_is_unchanged_with_no_mint() -> None:
    _require_reference()
    config = _config()
    before = _before_result(config)
    report = _unwrap(compare_reference_outputs(config, before, before))
    assert report.verdict is OutputChangeVerdict.UNCHANGED
    # The upgrade may land with no mint — identical output is not a change.
    assert report.mint is None
    assert report.per_channel_equal == {"sma": True}
    # The protocol format version is reported and unchanged.
    assert report.protocol_format_version == CONTRACT_FORMAT_VERSION


def test_a_changed_output_mints_the_per_configured_indicator_version() -> None:
    _require_reference()
    config = _config()
    before = _before_result(config)
    after = _perturb_channel(before, "sma", delta=1)
    report = _unwrap(compare_reference_outputs(config, before, after))
    # AC4: the change is caught (never a silent accept) and carries a mint.
    assert report.verdict is OutputChangeVerdict.CHANGED
    assert report.per_channel_equal == {"sma": False}
    mint = report.mint
    assert isinstance(mint, ContractFormatMint)
    assert mint.formula_id == "sma"
    # The mint is the per-configured-indicator format version: previous + 1, never a jump.
    assert mint.previous_format_version == config.contract_format_version
    assert mint.minted_format_version == config.contract_format_version + 1
    assert mint.changed_channels == ("sma",)
    # Recorded before/after evidence: the fp1 of each output on both sides, and they differ.
    assert set(mint.before_evidence) == {"sma"}
    assert set(mint.after_evidence) == {"sma"}
    assert mint.before_evidence["sma"] != mint.after_evidence["sma"]
    assert mint.before_evidence["sma"].startswith("fp1:sha256:")


def test_a_change_never_bumps_the_protocol_version() -> None:
    _require_reference()
    config = _config()
    before = _before_result(config)
    after = _perturb_channel(before, "sma", delta=5)
    report = _unwrap(compare_reference_outputs(config, before, after))
    # Never a protocol-wide bump: the CT-16 protocol format version is unchanged even on a
    # changed verdict; the mint is per configured indicator only.
    assert report.protocol_format_version == CONTRACT_FORMAT_VERSION
    assert report.mint is not None
    assert report.mint.minted_format_version == config.contract_format_version + 1


def test_a_within_tolerance_change_is_unchanged_under_a_declared_comparator() -> None:
    _require_reference()
    config = _config()
    before = _before_result(config)
    after = _perturb_channel(before, "sma", delta=1)  # one ULP at the output scale
    exact = _unwrap(compare_reference_outputs(config, before, after))
    assert exact.verdict is OutputChangeVerdict.CHANGED  # default comparator is exact (0 ULP)
    tolerant = _unwrap(ModeEqualityComparator.try_create(1))
    within = _unwrap(compare_reference_outputs(config, before, after, tolerant))
    # A one-ULP difference is within a one-ULP tolerance: no change, no mint.
    assert within.verdict is OutputChangeVerdict.UNCHANGED
    assert within.mint is None


def test_a_higher_contract_format_version_mints_the_next_one() -> None:
    _require_reference()
    config = _config(contract_format_version=4)
    before = _before_result(config)
    after = _perturb_channel(before, "sma", delta=2)
    report = _unwrap(compare_reference_outputs(config, before, after))
    assert report.mint is not None
    assert report.mint.previous_format_version == 4
    assert report.mint.minted_format_version == 5


# --- validation and the identical-canonical-inputs guard --------------------


def test_compare_rejects_a_non_configuration_and_non_results() -> None:
    _require_reference()
    config = _config()
    before = _before_result(config)
    assert is_refusal(compare_reference_outputs(object(), before, before))
    non_result = compare_reference_outputs(config, object(), before)
    assert is_refusal(non_result) and non_result.context["field"] == "results"
    assert is_refusal(compare_reference_outputs(config, before, object()))


def test_compare_rejects_a_bad_comparator() -> None:
    _require_reference()
    config = _config()
    before = _before_result(config)
    refusal = compare_reference_outputs(config, before, before, object())
    assert is_refusal(refusal) and refusal.context["field"] == "comparator"


def test_compare_refuses_different_producer_identities() -> None:
    _require_reference()
    config_a = _config(period=_period(3))
    config_b = _config(period=_period(5))
    before = _before_result(config_a)
    other = _before_result(config_b)
    refusal = compare_reference_outputs(config_a, before, other)
    assert is_refusal(refusal) and refusal.context["field"] == "results"
    assert "producer" in refusal.context["reason"]


def test_compare_refuses_different_canonical_inputs() -> None:
    _require_reference()
    config = _config()
    before = _before_result(config, values=[3, 6, 9, 12, 15, 18])
    # Same configuration (same producer identity) but different input values -> different
    # input fingerprints; FM-4 compares identical canonical inputs.
    other = _before_result(config, values=[3, 6, 9, 12, 15, 21])
    refusal = compare_reference_outputs(config, before, other)
    assert is_refusal(refusal) and refusal.context["field"] == "results"
    assert "different canonical inputs" in refusal.context["reason"]


def test_compare_refuses_a_result_missing_a_declared_channel() -> None:
    _require_reference()
    config = _config()
    before = _before_result(config)
    # An after result whose outputs lack the declared channel (same label, so the identical
    # inputs guard passes first).
    renamed = BatchResult(outputs={"other": before.outputs["sma"]}, label=before.label)
    refusal = compare_reference_outputs(config, before, renamed)
    assert is_refusal(refusal) and refusal.context["field"] == "results"
    assert refusal.context["channel"] == "sma"


def test_comparison_report_is_a_frozen_value() -> None:
    _require_reference()
    config = _config()
    before = _before_result(config)
    report = _unwrap(compare_reference_outputs(config, before, before))
    assert isinstance(report, ComparisonReport)
    with pytest.raises(AttributeError):
        report.verdict = OutputChangeVerdict.CHANGED  # type: ignore[misc]
