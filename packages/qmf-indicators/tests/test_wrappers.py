"""Tier-1 tests for the CT-16 first wrapper set (COMP-QMF-INDICATORS; Story 7.6).

These tests bind the story's acceptance criteria:

* **AC1** — each wrapper is a configured indicator wrapping a TA-Lib formula the reference
  implements, declared in **both modes**, with **warm-up at least the reference's
  lookback**; and no trading-school name appears in any rule or vocabulary (the capability
  terms are mechanically stated).
* **AC2** — a both-modes wrapper passes the tier-2 equality law at the declared integer-ULP
  tolerance and its restore-equivalence test (exercised end to end against the real
  canonical reference).
* **AC3** — each ships executable tests (this file) and reference-usage examples (the
  example module and its runner test) as tier-1 artifacts.

The build/validation group is pure (no reference needed); a final group drives the real
:class:`ReferenceKernel` so the canonical wrapping, warm-up discipline, equality law, and
restore-equivalence are proven on this machine.
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
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.indicators import (
    WRAPPER_FORMULAS,
    WRAPPER_SET,
    ArithmeticReference,
    ChannelKind,
    ConfiguredIndicator,
    InputSeries,
    OutputArity,
    OutputChannel,
    PresenceState,
    QuoteSide,
    ReferenceKernel,
    SeriesInput,
    SnapshotScope,
    StreamingIndicator,
    StreamingObservation,
    SupportedMode,
    WrapperSpec,
    assert_mode_equality,
    compute_batch,
    configure_wrapper,
    reference_lookback,
    reference_status,
    wrapper_set_conformance_defects,
    wrapper_spec,
)
from qmf.indicators.arithmetic import FormulaOwner, FormulaOwnership

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


def _arithmetic_reference() -> ArithmeticReference:
    return _unwrap(
        ArithmeticReference.try_create(
            "ta-lib-c==0.7.1",
            "ta-lib==0.7.1",
            {"compatibility_mode": "default", "candle_settings": "reference-default"},
        )
    )


def _configure(formula_id: str, **overrides: object) -> Result[ConfiguredIndicator]:
    kwargs: dict[str, object] = {
        "formula_id": formula_id,
        "period": _period(3),
        "inputs": [_series_input("close")],
        "calendar_requirements": [_calendar()],
        "arithmetic_reference_configuration": _arithmetic_reference(),
    }
    kwargs.update(overrides)
    return configure_wrapper(**kwargs)


# --- AC1: the set, the shape, and school-neutral vocabulary -----------------


def test_wrapper_set_is_the_reference_owned_first_set() -> None:
    # The first wrapper set is exactly the reference-owned, single-input, period-taking
    # formulas the batch bridge computes end to end.
    assert set(WRAPPER_FORMULAS) == {"sma", "ema", "wma", "rsi", "mom", "roc"}
    assert set(WRAPPER_SET) == set(WRAPPER_FORMULAS)
    # WRAPPER_FORMULAS is a stable sorted roster.
    assert tuple(sorted(WRAPPER_FORMULAS)) == WRAPPER_FORMULAS


def test_every_wrapper_wraps_a_reference_formula_no_defects() -> None:
    # Each wrapper genuinely wraps the reference formula the canonical registry assigns it;
    # re-implementing arithmetic the reference owns would be a contract defect (FM-5).
    assert wrapper_set_conformance_defects() == ()


def test_no_trading_school_name_in_the_vocabulary() -> None:
    # School concepts enter only as mechanically stated capability terms (DEC-0132). The
    # capability terms describe mechanical operations (mean, difference, rate of change) and
    # name no trading school.
    banned = (
        "wyckoff",
        "elliott",
        "ict",
        "smart money",
        "fibonacci",
        "gann",
        "supply and demand",
        "order block",
    )
    for spec in WRAPPER_SET.values():
        lowered = spec.capability_term.lower()
        for school in banned:
            assert school not in lowered, (spec.formula_id, school)
        # The formula id is a mechanical acronym, never a school name.
        assert spec.formula_id in {"sma", "ema", "wma", "rsi", "mom", "roc"}


def test_each_wrapper_declares_both_modes_and_the_expected_shape() -> None:
    for formula_id in WRAPPER_FORMULAS:
        spec = WRAPPER_SET[formula_id]
        config = _unwrap(_configure(formula_id))
        # AC1: wraps a TA-Lib formula, declared in both modes.
        assert config.formula_id == formula_id
        assert set(config.supported_modes) == {SupportedMode.BATCH, SupportedMode.STREAMING}
        # One scalar-per-sample output channel, named and kinded per the wrapper spec.
        assert len(config.output_schema) == 1
        channel = config.output_schema[0]
        assert channel.name == spec.output_channel
        assert channel.channel_kind is spec.output_kind
        assert channel.arity is OutputArity.SCALAR_PER_SAMPLE
        # The period is the sole exact-rational parameter.
        assert set(config.parameters) == {"period"}
        # A configured indicator's fp1 identity computes.
        assert is_ok(config.fp1())


def test_default_warm_up_equals_the_reference_lookback() -> None:
    # AC1: warm-up is at least the reference's lookback; the default is exactly it — the
    # minimum legal value. period-1 for the moving averages, period for the rest.
    period = _period(4)
    expected = {"sma": 3, "ema": 3, "wma": 3, "rsi": 4, "mom": 4, "roc": 4}
    for formula_id, want in expected.items():
        config = _unwrap(_configure(formula_id, period=period))
        assert config.warm_up == want
        assert _unwrap(reference_lookback(formula_id, period)) == want
        # WrapperSpec exposes the same lookback.
        assert WRAPPER_SET[formula_id].reference_lookback(4) == want


def test_two_wrappers_differing_in_one_element_get_distinct_fingerprints() -> None:
    # Two configurations differing in any one identity element (here the period) receive
    # distinct fp1 values — that fp1 is the only dedup key.
    a = _unwrap(_configure("sma", period=_period(3)))
    b = _unwrap(_configure("sma", period=_period(5)))
    assert _unwrap(a.fp1()) != _unwrap(b.fp1())
    # And two different formulas at the same period differ too.
    c = _unwrap(_configure("ema", period=_period(3)))
    assert _unwrap(a.fp1()) != _unwrap(c.fp1())


# --- warm-up discipline: a larger warm-up is allowed, a smaller one refused -


def test_a_larger_warm_up_is_allowed() -> None:
    # A caller may declare a warm-up larger than the reference lookback (e.g. to cover an
    # unstable period); it is honoured.
    config = _unwrap(_configure("rsi", period=_period(3), warm_up=10))
    assert config.warm_up == 10


def test_a_warm_up_below_the_reference_lookback_is_refused() -> None:
    # sma period 5 has lookback 4; a warm-up of 2 is below it and refused here, before
    # compute_batch would refuse it too.
    refusal = _configure("sma", period=_period(5), warm_up=2)
    assert is_refusal(refusal)
    assert refusal.context["field"] == "warm_up"
    assert refusal.context["reference_lookback"] == 4


def test_a_non_integer_warm_up_is_refused() -> None:
    assert is_refusal(_configure("sma", period=_period(3), warm_up=1.5))
    assert is_refusal(_configure("sma", period=_period(3), warm_up=True))


# --- output-channel override ------------------------------------------------


def test_output_channel_override_is_honoured() -> None:
    channel = _unwrap(
        OutputChannel.try_create("avg", ChannelKind.EXACT_PRICE, OutputArity.SCALAR_PER_SAMPLE, 0)
    )
    config = _unwrap(_configure("sma", output_channel=channel))
    assert config.output_schema[0].name == "avg"
    assert config.output_schema[0].channel_kind is ChannelKind.EXACT_PRICE


def test_output_channel_override_must_be_an_output_channel() -> None:
    refusal = _configure("sma", output_channel=object())
    assert is_refusal(refusal) and refusal.context["field"] == "output_channel"


# --- validation paths -------------------------------------------------------


def test_configure_rejects_an_unknown_formula() -> None:
    refusal = _configure("obv")  # reference-owned but not in the first wrapper set
    assert is_refusal(refusal) and refusal.context["field"] == "formula_id"
    # TypedRefusal deep-freezes sequences to tuples; the roster is the first wrapper set.
    listed = refusal.context["wrapper_set"]
    assert isinstance(listed, tuple)
    assert listed == WRAPPER_FORMULAS
    assert "obv" not in listed


def test_configure_rejects_a_non_rational_or_fractional_period() -> None:
    # A binary float never reaches here (parameters are exact rationals only); a non-rational
    # is refused, and a fractional period is refused.
    assert is_refusal(_configure("sma", period=3))
    assert is_refusal(_configure("sma", period=3.0))
    frac = _configure("sma", period=_period(5, 2))
    assert is_refusal(frac) and frac.context["field"] == "period"
    zero = _configure("sma", period=_period(0, 1))
    assert is_refusal(zero) and zero.context["field"] == "period"


def test_configure_propagates_a_downstream_refusal() -> None:
    # A bad input set is refused by ConfiguredIndicator.try_create and surfaced verbatim.
    refusal = _configure("sma", inputs="not-a-sequence")
    assert is_refusal(refusal) and refusal.context["field"] == "inputs"


def test_wrapper_spec_and_reference_lookback_validation() -> None:
    assert is_refusal(wrapper_spec(""))
    assert is_refusal(wrapper_spec(123))
    unknown = wrapper_spec("nope")
    assert is_refusal(unknown) and unknown.context["field"] == "formula_id"
    # reference_lookback propagates a bad formula and a bad period.
    assert is_refusal(reference_lookback("nope", _period(3)))
    assert is_refusal(reference_lookback("sma", 3))
    # A resolved spec is the same object stored in the set.
    assert _unwrap(wrapper_spec("sma")) is WRAPPER_SET["sma"]


# --- conformance-defect detection (synthetic registries) --------------------


def test_conformance_defects_catch_a_key_mismatch() -> None:
    bad = {"sma": WrapperSpec("ema", "EMA", "ema", ChannelKind.FLOAT_ANALYTIC, -1, "x")}
    defects = wrapper_set_conformance_defects(bad, dict(_owner("ema", "EMA")))
    assert any("does not match its key" in defect for defect in defects)


def test_conformance_defects_catch_a_missing_owner() -> None:
    only = {"sma": WRAPPER_SET["sma"]}
    defects = wrapper_set_conformance_defects(only, {})
    assert any("no canonical owner" in defect for defect in defects)


def test_conformance_defects_catch_a_non_reference_owner() -> None:
    only = {"sma": WRAPPER_SET["sma"]}
    package_owner = {"sma": FormulaOwner(formula_id="sma", ownership=FormulaOwnership.PACKAGE)}
    defects = wrapper_set_conformance_defects(only, package_owner)
    assert any("not reference-owned" in defect for defect in defects)


def test_conformance_defects_catch_a_reference_function_mismatch() -> None:
    only = {"sma": WRAPPER_SET["sma"]}  # declares reference function "SMA"
    wrong_fn = {
        "sma": FormulaOwner(
            formula_id="sma", ownership=FormulaOwnership.REFERENCE, reference_function="WMA"
        )
    }
    defects = wrapper_set_conformance_defects(only, wrong_fn)
    assert any("but the canonical owner names" in defect for defect in defects)


def _owner(formula_id: str, reference_function: str) -> dict[str, FormulaOwner]:
    return {
        formula_id: FormulaOwner(
            formula_id=formula_id,
            ownership=FormulaOwnership.REFERENCE,
            reference_function=reference_function,
        )
    }


# --- AC2: equality law and restore-equivalence against the real reference ---


def _require_reference() -> None:
    if not is_ok(reference_status()):
        pytest.skip("the pinned canonical reference is unavailable on this machine")


def _writer() -> WriterId:
    return _unwrap(WriterId.try_create("m1", "indicator-feeder", "eurusd", "boot-1"))


def _scope() -> SnapshotScope:
    return _unwrap(SnapshotScope.try_create("windows-11", "ta-lib==0.7.1"))


_VALUES = [3, 6, 9, 12, 15, 18, 21, 24]


def _instants() -> list[Instant]:
    return [_unwrap(Instant.try_create(1_000 + step)) for step in range(len(_VALUES))]


@pytest.mark.parametrize("formula_id", ["sma", "ema", "wma", "rsi", "mom", "roc"])
def test_wrapper_streaming_equals_batch_under_the_reference(formula_id: str) -> None:
    _require_reference()
    config = _unwrap(_configure(formula_id, period=_period(3)))
    instants = _instants()
    series = _unwrap(
        InputSeries.from_values(_VALUES, 0, [PresenceState.PRESENT] * len(_VALUES), instants)
    )
    batch_result = _unwrap(
        compute_batch(config, {"close": series}, kernel=ReferenceKernel(), world=World.REPLAY)
    )
    stream = _unwrap(
        StreamingIndicator.try_create(
            config,
            kernel=ReferenceKernel(),
            world=World.REPLAY,
            writer_id=_writer(),
            scope=_scope(),
            input_scales={"close": 0},
        )
    )
    for value, instant in zip(_VALUES, instants, strict=True):
        _unwrap(
            stream.update({"close": StreamingObservation(value, PresenceState.PRESENT, instant)})
        )
    streaming_result = _unwrap(stream.result())
    # AC2: the tier-2 equality law passes at the declared integer-ULP tolerance (default 0).
    assert _unwrap(assert_mode_equality(config, batch_result, streaming_result)) is True


@pytest.mark.parametrize("formula_id", ["sma", "ema", "wma", "rsi", "mom", "roc"])
def test_wrapper_warm_up_prefix_is_exactly_the_reference_lookback(formula_id: str) -> None:
    _require_reference()
    config = _unwrap(_configure(formula_id, period=_period(3)))
    instants = _instants()
    series = _unwrap(
        InputSeries.from_values(_VALUES, 0, [PresenceState.PRESENT] * len(_VALUES), instants)
    )
    out = _unwrap(
        compute_batch(config, {"close": series}, kernel=ReferenceKernel(), world=World.REPLAY)
    ).outputs[config.output_schema[0].name]
    lookback = _unwrap(reference_lookback(formula_id, _period(3)))
    not_ready = sum(1 for state in out.presence if state is PresenceState.NOT_READY)
    # The marked not-ready prefix covers exactly the reference's lookback — no number during
    # warm-up, and no over-trimming (warm-up discipline).
    assert not_ready == lookback
    assert all(state is PresenceState.PRESENT for state in out.presence[lookback:])


@pytest.mark.parametrize("formula_id", ["sma", "ema", "wma", "rsi", "mom", "roc"])
def test_wrapper_restore_equivalence_under_the_reference(formula_id: str) -> None:
    _require_reference()
    config = _unwrap(_configure(formula_id, period=_period(3)))
    instants = _instants()

    cold = _unwrap(
        StreamingIndicator.try_create(
            config,
            kernel=ReferenceKernel(),
            world=World.REPLAY,
            writer_id=_writer(),
            scope=_scope(),
            input_scales={"close": 0},
        )
    )
    for value, instant in zip(_VALUES, instants, strict=True):
        _unwrap(cold.update({"close": StreamingObservation(value, PresenceState.PRESENT, instant)}))
    cold_result = _unwrap(cold.result())

    warm = _unwrap(
        StreamingIndicator.try_create(
            config,
            kernel=ReferenceKernel(),
            world=World.REPLAY,
            writer_id=_writer(),
            scope=_scope(),
            input_scales={"close": 0},
        )
    )
    for value, instant in zip(_VALUES[:4], instants[:4], strict=True):
        _unwrap(warm.update({"close": StreamingObservation(value, PresenceState.PRESENT, instant)}))
    snapshot = _unwrap(warm.snapshot())
    restored = _unwrap(
        StreamingIndicator.restore(
            snapshot,
            configuration=config,
            kernel=ReferenceKernel(),
            world=World.REPLAY,
            current_scope=_scope(),
        )
    )
    for value, instant in zip(_VALUES[4:], instants[4:], strict=True):
        _unwrap(
            restored.update({"close": StreamingObservation(value, PresenceState.PRESENT, instant)})
        )
    restored_result = _unwrap(restored.result())
    channel = config.output_schema[0].name
    # AC2: restore-then-N-updates equals cold-warm-then-the-same-N-updates.
    assert _unwrap(cold_result.outputs[channel].equals(restored_result.outputs[channel])) is True
