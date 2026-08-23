"""Tier-2 tests for the CT-16 conformance register bound to the concept-walk list
(COMP-QMF-INDICATORS; Story 7.5).

These tests bind the story's first acceptance criterion: the conformance register keeps its
concept-walk list **expressible** as governed CT-16 configurations — multi-instrument and
multi-BarSpec input sets, derived-series chaining, non-time bar kinds, calendar-scoped
windows and calendar-anchored sampling, projected outputs under knowable-at, batch-only
statistical methods, price-valued outputs re-entering the money path, and delta-typed price
differences. Each concept is expressed by a governed configuration the test builds; the
harness proves every register concept is covered and expressible, and fails closed on a
missing or non-expressible concept.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    CalendarIdentity,
    Duration,
    ExactRational,
    Fingerprint,
    Instrument,
    Result,
    UnitKind,
    VenueId,
    is_ok,
    is_refusal,
)
from qmf.indicators import (
    CONCEPT_WALK_REGISTER,
    AlignmentPolicy,
    ArithmeticReference,
    ChannelKind,
    ConceptExpression,
    ConceptWalk,
    ConfiguredIndicator,
    MissingValuePolicy,
    OutputArity,
    OutputChannel,
    SeriesInput,
    SupportedMode,
    check_expressible,
    run_conformance,
)

T = TypeVar("T")


def _unwrap(result: Result[T]) -> T:
    assert is_ok(result), f"expected Ok, got {result}"
    return result.value


# --- fixtures ---------------------------------------------------------------


def _instrument(symbol: str = "EURUSD", venue: str = "venue-ic") -> Instrument:
    return _unwrap(Instrument.try_create(_unwrap(VenueId.try_create(venue)), symbol))


def _calendar() -> CalendarIdentity:
    return _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))


def _period(numerator: int = 3) -> ExactRational:
    return _unwrap(ExactRational.try_create(numerator, 1, UnitKind.COUNT))


def _arithmetic_reference() -> ArithmeticReference:
    return _unwrap(
        ArithmeticReference.try_create(
            "ta-lib-c==0.7.1",
            "ta-lib==0.7.1",
            {"compatibility_mode": "default", "candle_settings": "reference-default"},
        )
    )


def _series_input(
    name: str = "close",
    *,
    source: object = None,
    bar_spec: object = None,
    channel_kind: ChannelKind = ChannelKind.EXACT_PRICE,
    upstream_fingerprint: object = None,
) -> SeriesInput:
    return _unwrap(
        SeriesInput.try_create(
            name=name,
            source=source if source is not None else _instrument(),
            bar_spec=bar_spec if bar_spec is not None else {"kind": "time-interval", "seconds": 60},
            channel_kind=channel_kind,
            quote_side="mid",
            upstream_fingerprint=upstream_fingerprint,
        )
    )


def _output_channel(
    name: str = "sma",
    *,
    channel_kind: ChannelKind = ChannelKind.FLOAT_ANALYTIC,
    index_offset: int = 0,
) -> OutputChannel:
    return _unwrap(
        OutputChannel.try_create(name, channel_kind, OutputArity.SCALAR_PER_SAMPLE, index_offset)
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


def _a_fingerprint() -> Fingerprint:
    return _unwrap(_config().fp1())


# --- per-concept configurations ---------------------------------------------


def _multi_instrument_config() -> ConfiguredIndicator:
    return _config(
        inputs=[
            _series_input("eur", source=_instrument("EURUSD")),
            _series_input("gbp", source=_instrument("GBPUSD")),
        ]
    )


def _multi_barspec_config() -> ConfiguredIndicator:
    return _config(
        inputs=[
            _series_input("close_1m", bar_spec={"kind": "time-interval", "seconds": 60}),
            _series_input("close_5m", bar_spec={"kind": "time-interval", "seconds": 300}),
        ]
    )


def _derived_series_config() -> ConfiguredIndicator:
    return _config(inputs=[_series_input("upstream_sma", upstream_fingerprint=_a_fingerprint())])


def _non_time_bar_config() -> ConfiguredIndicator:
    return _config(inputs=[_series_input("ticks", bar_spec={"kind": "tick-count", "count": 500})])


def _calendar_scoped_window_config() -> ConfiguredIndicator:
    return _config(warm_up_time_bound=_unwrap(Duration.try_create(3_600_000_000_000)))


def _calendar_anchored_sampling_config() -> ConfiguredIndicator:
    return _config(inputs=[_series_input("session", bar_spec={"kind": "session", "session": "NY"})])


def _projected_output_config() -> ConfiguredIndicator:
    return _config(output_schema=[_output_channel("projected", index_offset=1)])


def _batch_only_config() -> ConfiguredIndicator:
    return _config(supported_modes=[SupportedMode.BATCH])


def _price_valued_config() -> ConfiguredIndicator:
    return _config(output_schema=[_output_channel("level", channel_kind=ChannelKind.EXACT_PRICE)])


def _delta_typed_config() -> ConfiguredIndicator:
    return _config(
        formula_id="mom",
        parameters={"period": _period(10)},
        output_schema=[_output_channel("mom", channel_kind=ChannelKind.EXACT_PRICE)],
    )


def _all_expressions() -> list[ConceptExpression]:
    return [
        ConceptExpression(ConceptWalk.MULTI_INSTRUMENT, _multi_instrument_config()),
        ConceptExpression(ConceptWalk.MULTI_BARSPEC, _multi_barspec_config()),
        ConceptExpression(ConceptWalk.DERIVED_SERIES_CHAINING, _derived_series_config()),
        ConceptExpression(ConceptWalk.NON_TIME_BAR_KINDS, _non_time_bar_config()),
        ConceptExpression(ConceptWalk.CALENDAR_SCOPED_WINDOWS, _calendar_scoped_window_config()),
        ConceptExpression(
            ConceptWalk.CALENDAR_ANCHORED_SAMPLING, _calendar_anchored_sampling_config()
        ),
        ConceptExpression(ConceptWalk.PROJECTED_OUTPUTS_KNOWABLE_AT, _projected_output_config()),
        ConceptExpression(ConceptWalk.BATCH_ONLY_STATISTICAL, _batch_only_config()),
        ConceptExpression(ConceptWalk.PRICE_VALUED_REENTRY, _price_valued_config()),
        ConceptExpression(ConceptWalk.DELTA_TYPED_PRICE_DIFFERENCES, _delta_typed_config()),
    ]


# --- the register ------------------------------------------------------------


def test_register_lists_the_ten_concepts_in_order() -> None:
    assert CONCEPT_WALK_REGISTER == (
        ConceptWalk.MULTI_INSTRUMENT,
        ConceptWalk.MULTI_BARSPEC,
        ConceptWalk.DERIVED_SERIES_CHAINING,
        ConceptWalk.NON_TIME_BAR_KINDS,
        ConceptWalk.CALENDAR_SCOPED_WINDOWS,
        ConceptWalk.CALENDAR_ANCHORED_SAMPLING,
        ConceptWalk.PROJECTED_OUTPUTS_KNOWABLE_AT,
        ConceptWalk.BATCH_ONLY_STATISTICAL,
        ConceptWalk.PRICE_VALUED_REENTRY,
        ConceptWalk.DELTA_TYPED_PRICE_DIFFERENCES,
    )


# --- each concept is expressible --------------------------------------------


def test_every_register_concept_is_expressible() -> None:
    for expression in _all_expressions():
        check = _unwrap(check_expressible(expression.concept, expression.configuration))
        assert check.expressible is True, f"{expression.concept} not expressible: {check.defect}"
        assert check.fingerprint is not None
        assert check.defect is None


def test_conformance_suite_passes_over_the_full_concept_walk() -> None:
    report = _unwrap(run_conformance(_all_expressions()))
    assert report.passed is True
    assert report.missing == ()
    assert len(report.checks) == len(CONCEPT_WALK_REGISTER)
    assert all(check.expressible for check in report.checks)


# --- fail-closed behaviour ---------------------------------------------------


def test_a_missing_concept_fails_the_suite() -> None:
    # Drop one concept: the suite reports it missing and does not pass.
    partial = [
        expression
        for expression in _all_expressions()
        if expression.concept is not ConceptWalk.DELTA_TYPED_PRICE_DIFFERENCES
    ]
    report = _unwrap(run_conformance(partial))
    assert report.passed is False
    assert ConceptWalk.DELTA_TYPED_PRICE_DIFFERENCES in report.missing


def test_a_non_expressing_configuration_is_not_expressible() -> None:
    # A single-instrument configuration does not express the multi-instrument concept.
    check = _unwrap(check_expressible(ConceptWalk.MULTI_INSTRUMENT, _config()))
    assert check.expressible is False
    assert check.fingerprint is None
    assert check.defect is not None


def test_a_non_expressing_expression_fails_the_suite() -> None:
    expressions = [ConceptExpression(concept, _config()) for concept in CONCEPT_WALK_REGISTER]
    report = _unwrap(run_conformance(expressions))
    # Every register concept is covered, but the plain sma config only structurally expresses
    # a few of them, so the suite does not pass.
    assert report.missing == ()
    assert report.passed is False
    assert any(check.expressible is False for check in report.checks)


def test_delta_and_price_level_are_distinct_concepts() -> None:
    # The plain sma-with-exact-price config expresses price-valued re-entry but NOT the
    # delta-typed price-difference concept (which needs a difference formula).
    price_level = _price_valued_config()
    assert _unwrap(check_expressible(ConceptWalk.PRICE_VALUED_REENTRY, price_level)).expressible
    assert (
        _unwrap(
            check_expressible(ConceptWalk.DELTA_TYPED_PRICE_DIFFERENCES, price_level)
        ).expressible
        is False
    )


# --- validation paths --------------------------------------------------------


def test_check_expressible_refuses_bad_arguments() -> None:
    assert is_refusal(check_expressible("not-a-concept", _config()))
    assert is_refusal(check_expressible(ConceptWalk.MULTI_INSTRUMENT, object()))


def test_run_conformance_refuses_bad_arguments() -> None:
    assert is_refusal(run_conformance(object()))
    assert is_refusal(run_conformance("multi-instrument"))
    assert is_refusal(run_conformance([object()]))
