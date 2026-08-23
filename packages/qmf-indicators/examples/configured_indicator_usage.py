"""Reference usage — CT-16 the configured-indicator declaration record and its fp1
identity (COMP-QMF-INDICATORS).

Executable::

    python packages/qmf-indicators/examples/configured_indicator_usage.py

Shows the four things Story 7.1 pins down:

1. A configured indicator's ``fp1`` is computed by the single qmf-core fingerprint
   function and spans the entire declared configuration (``fp1:sha256:<hex>``).
2. Every declared identity element is present in the fingerprint content — an element
   missing from the fingerprint would be a contract defect.
3. Two configurations differing in any one identity element receive distinct
   fingerprints, and that ``fp1`` is the only dedup key.
4. A parameter expressed as a binary float is refused — parameters are exact
   rationals only (scaled integers or numerator/denominator pairs).
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    CalendarIdentity,
    ExactRational,
    Instrument,
    Result,
    TypedRefusal,
    UnitKind,
    VenueId,
    is_ok,
)
from qmf.indicators import (
    IDENTITY_ELEMENTS,
    AlignmentPolicy,
    ArithmeticReference,
    ChannelKind,
    ConfiguredIndicator,
    MissingValuePolicy,
    OutputArity,
    OutputChannel,
    QuoteSide,
    SeriesInput,
    SupportedMode,
)

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    """Tiny demo helper: a construction we assert must succeed here."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _configuration(period_numerator: int) -> ConfiguredIndicator:
    """A simple moving-average configuration parameterized by its period."""
    venue = _unwrap(VenueId.try_create("venue-ic"), "venue id")
    instrument = _unwrap(Instrument.try_create(venue, "EURUSD"), "instrument")
    close = _unwrap(
        SeriesInput.try_create(
            name="close",
            source=instrument,
            bar_spec={"kind": "time-interval", "seconds": 60},
            channel_kind=ChannelKind.EXACT_PRICE,
            quote_side=QuoteSide.MID,
        ),
        "close input",
    )
    period = _unwrap(
        ExactRational.try_create(period_numerator, 1, UnitKind.COUNT), "period parameter"
    )
    calendar = _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"), "calendar")
    output = _unwrap(
        OutputChannel.try_create(
            "sma", ChannelKind.FLOAT_ANALYTIC, OutputArity.SCALAR_PER_SAMPLE, 0
        ),
        "output channel",
    )
    reference = _unwrap(
        ArithmeticReference.try_create(
            "ta-lib-c@sha256:aaaa",
            "ta-lib-py@sha256:bbbb",
            {"compatibility_mode": "classic", "candle_settings": "default"},
        ),
        "arithmetic reference",
    )
    return _unwrap(
        ConfiguredIndicator.try_create(
            formula_id="sma",
            contract_format_version=1,
            parameters={"period": period},
            inputs=[close],
            calendar_requirements=[calendar],
            alignment_policy=AlignmentPolicy.AS_OF,
            missing_value_policy=MissingValuePolicy.MARK_GAP,
            warm_up=period_numerator,
            output_schema=[output],
            supported_modes=[SupportedMode.BATCH, SupportedMode.STREAMING],
            arithmetic_reference_configuration=reference,
        ),
        "configured indicator",
    )


def fp1_spans_the_whole_configuration() -> str:
    """The fp1 is qmf-core's fingerprint over the entire declared configuration."""
    config = _configuration(20)
    fp = _unwrap(config.fp1(), "configuration fingerprint")
    assert fp.value.startswith("fp1:sha256:")
    content = config.fp1_identity()
    for element in IDENTITY_ELEMENTS:
        assert element in content, element
    return fp.value


def one_parameter_change_forks_identity() -> tuple[str, str]:
    """Two configurations differing only in the period receive distinct fingerprints."""
    fp_20 = _unwrap(_configuration(20).fp1(), "sma-20 fingerprint").value
    fp_50 = _unwrap(_configuration(50).fp1(), "sma-50 fingerprint").value
    assert fp_20 != fp_50
    return fp_20, fp_50


def binary_float_parameter_is_refused() -> TypedRefusal:
    """A parameter expressed as a binary float is refused — exact rationals only."""
    venue = _unwrap(VenueId.try_create("venue-ic"), "venue id")
    instrument = _unwrap(Instrument.try_create(venue, "EURUSD"), "instrument")
    close = _unwrap(
        SeriesInput.try_create(
            name="close",
            source=instrument,
            bar_spec={"kind": "time-interval", "seconds": 60},
            channel_kind=ChannelKind.EXACT_PRICE,
            quote_side=QuoteSide.MID,
        ),
        "close input",
    )
    output = _unwrap(
        OutputChannel.try_create(
            "sma", ChannelKind.FLOAT_ANALYTIC, OutputArity.SCALAR_PER_SAMPLE, 0
        ),
        "output channel",
    )
    reference = _unwrap(
        ArithmeticReference.try_create(
            "ta-lib-c@sha256:aaaa", "ta-lib-py@sha256:bbbb", {"compatibility_mode": "classic"}
        ),
        "arithmetic reference",
    )
    refusal = ConfiguredIndicator.try_create(
        formula_id="sma",
        contract_format_version=1,
        parameters={"period": 20.0},  # a binary float on the parameter path
        inputs=[close],
        calendar_requirements=[],
        alignment_policy=AlignmentPolicy.AS_OF,
        missing_value_policy=MissingValuePolicy.MARK_GAP,
        warm_up=20,
        output_schema=[output],
        supported_modes=[SupportedMode.BATCH],
        arithmetic_reference_configuration=reference,
    )
    assert isinstance(refusal, TypedRefusal)
    assert refusal.category.value == "invalid input"
    return refusal


def main() -> None:
    fp = fp1_spans_the_whole_configuration()
    print(f"fp1 spans the whole configuration: {fp[:19]}...")

    fp_20, fp_50 = one_parameter_change_forks_identity()
    print(f"one parameter change forks identity: {fp_20 != fp_50}")

    refusal = binary_float_parameter_is_refused()
    print(f"binary float parameter refused: {refusal.category.value}")


if __name__ == "__main__":
    main()
