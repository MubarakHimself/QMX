"""Tier-1 tests for CT-16 — the configured-indicator declaration record and its fp1
identity (COMP-QMF-INDICATORS; Story 7.1).

These tests bind the story's acceptance criteria: identity spans the entire declared
configuration and is computed by the single qmf-core fingerprint function; two
configurations differing in any one identity element receive distinct fingerprints;
an element missing from the fingerprint is a contract defect (the conformance test
fails); and a parameter expressed as a binary float is refused (exact rationals only).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar

from qmf.core import (
    CalendarIdentity,
    Duration,
    ExactRational,
    Fingerprint,
    Instrument,
    Result,
    TypedRefusal,
    UnitKind,
    VenueId,
    canonical_bytes,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.indicators import (
    IDENTITY_ELEMENTS,
    OPTIONAL_IDENTITY_ELEMENTS,
    AlignmentPolicy,
    ArithmeticReference,
    ChannelKind,
    ConfiguredIndicator,
    DeclaredBudget,
    EmissionPolicy,
    EmissionTiming,
    MissingValuePolicy,
    OutputArity,
    OutputChannel,
    QuoteSide,
    SeriesInput,
    SupportedMode,
)

T = TypeVar("T")


def _unwrap(result: Result[T]) -> T:
    """Unwrap an ``Ok`` in a test, failing loudly on a refusal."""
    assert is_ok(result), f"expected Ok, got {result}"
    return result.value


# --- fixtures ---------------------------------------------------------------


def _instrument() -> Instrument:
    venue = _unwrap(VenueId.try_create("venue-ic"))
    return _unwrap(Instrument.try_create(venue, "EURUSD"))


def _calendar(tzdata_version: str = "2025.2") -> CalendarIdentity:
    return _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", tzdata_version))


def _period(numerator: int = 20) -> ExactRational:
    return _unwrap(ExactRational.try_create(numerator, 1, UnitKind.COUNT))


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
            "ta-lib-c@sha256:aaaa",
            "ta-lib-py@sha256:bbbb",
            {"compatibility_mode": "classic", "candle_settings": "default"},
        )
    )


def _base_kwargs() -> dict[str, object]:
    """A fresh, fully-valid keyword set for :meth:`ConfiguredIndicator.try_create`."""
    return {
        "formula_id": "sma",
        "contract_format_version": 1,
        "parameters": {"period": _period(20)},
        "inputs": [_series_input("close")],
        "calendar_requirements": [_calendar()],
        "alignment_policy": AlignmentPolicy.AS_OF,
        "missing_value_policy": MissingValuePolicy.MARK_GAP,
        "warm_up": 20,
        "output_schema": [_output_channel("sma")],
        "supported_modes": [SupportedMode.BATCH, SupportedMode.STREAMING],
        "arithmetic_reference_configuration": _arithmetic_reference(),
    }


def _build(**overrides: object) -> ConfiguredIndicator:
    kwargs = _base_kwargs()
    kwargs.update(overrides)
    return _unwrap(ConfiguredIndicator.try_create(**kwargs))


def _fp(config: ConfiguredIndicator) -> str:
    return _unwrap(config.fp1()).value


def _refuse(**overrides: object) -> TypedRefusal:
    """Build a configuration with ``overrides`` applied to the valid baseline and assert
    it is refused, returning the :class:`TypedRefusal` for context checks.

    The ``**overrides: object`` signature keeps every override value typed as ``object``
    (as ``try_create`` accepts), so a bare ``[]`` / ``"x"`` literal never widens the
    keyword type to a partially-unknown union under pyright strict.
    """
    kwargs = _base_kwargs()
    kwargs.update(overrides)
    result = ConfiguredIndicator.try_create(**kwargs)
    assert is_refusal(result), f"expected a refusal, got {result}"
    return result


# --- identity is computed by the single qmf-core fingerprint function --------


def test_fp1_is_computed_by_qmf_core_and_is_self_describing() -> None:
    config = _build()
    fp = _unwrap(config.fp1())
    assert isinstance(fp, Fingerprint)
    assert fp.value.startswith("fp1:sha256:")
    # The fp1 is exactly qmf-core's fingerprint over the declaration's identity content —
    # no local hashing lives in this package.
    assert fp == _unwrap(fingerprint(config))
    assert fp == _unwrap(fingerprint(config.fp1_identity()))


def test_equal_configurations_share_one_fingerprint() -> None:
    assert _fp(_build()) == _fp(_build())


# --- identity spans the ENTIRE declared configuration ------------------------


def test_every_required_identity_element_is_present_in_the_fingerprint() -> None:
    """An element missing from the fingerprint is a contract defect (AC3)."""
    content = _build().fp1_identity()
    for element in IDENTITY_ELEMENTS:
        assert element in content, f"identity element {element!r} missing from fp1 content"


def test_each_identity_element_is_load_bearing_in_the_fingerprint() -> None:
    """Removing any declared identity element from the content changes the fingerprint,
    proving no element is stored-but-unhashed (an element that did not enter the
    fingerprint would be a silent contract defect)."""
    config = _build(
        emission_policy=EmissionPolicy(EmissionTiming.BAR_CLOSED, "per-bar"),
        warm_up_time_bound=_unwrap(Duration.try_create(3_600_000_000_000)),
        declared_budget=DeclaredBudget("live-path", True, "bounded-window", True),
    )
    content = config.fp1_identity()
    baseline = _unwrap(fingerprint(content))
    for element in (*IDENTITY_ELEMENTS, *OPTIONAL_IDENTITY_ELEMENTS):
        assert element in content, element
        pruned = {key: value for key, value in content.items() if key != element}
        assert _unwrap(fingerprint(pruned)) != baseline, (
            f"dropping identity element {element!r} did not change the fingerprint"
        )


def test_identity_element_names_lists_required_plus_declared_optional() -> None:
    lean = _build()
    assert lean.identity_element_names() == IDENTITY_ELEMENTS

    full = _build(
        emission_policy=EmissionPolicy(EmissionTiming.IN_PROGRESS, "per-tick"),
        warm_up_time_bound=_unwrap(Duration.try_create(60_000_000_000)),
        declared_budget=DeclaredBudget("live-path", True, "anchor-reset", True),
    )
    assert full.identity_element_names() == IDENTITY_ELEMENTS + OPTIONAL_IDENTITY_ELEMENTS


# --- two configurations differing in any one element receive distinct fp1 ----


def test_differing_in_any_one_required_element_yields_distinct_fingerprints() -> None:
    baseline = _fp(_build())
    variants: dict[str, dict[str, object]] = {
        "formula_id": {"formula_id": "ema"},
        "contract_format_version": {"contract_format_version": 2},
        "parameters": {"parameters": {"period": _period(21)}},
        "inputs": {"inputs": [_series_input("open")]},
        "calendar_requirements": {"calendar_requirements": [_calendar("2024.1")]},
        # alignment_policy has a single governed-evidence-legal member (as-of); its
        # presence is covered by the load-bearing test above.
        "missing_value_policy": {"missing_value_policy": MissingValuePolicy.REFUSE},
        "warm_up": {"warm_up": 21},
        "output_schema": {"output_schema": [_output_channel("ema")]},
        "supported_modes": {"supported_modes": [SupportedMode.BATCH]},
        "arithmetic_reference_configuration": {
            "arithmetic_reference_configuration": _unwrap(
                ArithmeticReference.try_create(
                    "ta-lib-c@sha256:cccc",
                    "ta-lib-py@sha256:bbbb",
                    {"compatibility_mode": "classic"},
                )
            )
        },
    }
    for element, override in variants.items():
        assert _fp(_build(**override)) != baseline, (
            f"a configuration differing only in {element!r} shared the baseline fingerprint"
        )


def test_declaring_each_optional_element_changes_the_fingerprint() -> None:
    baseline = _fp(_build())
    assert (
        _fp(_build(emission_policy=EmissionPolicy(EmissionTiming.BAR_CLOSED, "per-bar")))
        != baseline
    )
    assert _fp(_build(warm_up_time_bound=_unwrap(Duration.try_create(60_000_000_000)))) != baseline
    assert (
        _fp(_build(declared_budget=DeclaredBudget("live-path", True, "bounded", False))) != baseline
    )


def test_ordered_elements_are_order_significant() -> None:
    two_inputs = [_series_input("close"), _series_input("open")]
    reversed_inputs = [_series_input("open"), _series_input("close")]
    assert _fp(_build(inputs=two_inputs)) != _fp(_build(inputs=reversed_inputs))

    two_channels = [_output_channel("sma"), _output_channel("signal")]
    reversed_channels = [_output_channel("signal"), _output_channel("sma")]
    assert _fp(_build(output_schema=two_channels)) != _fp(_build(output_schema=reversed_channels))


def test_unordered_elements_are_order_independent() -> None:
    modes_a = _build(supported_modes=[SupportedMode.BATCH, SupportedMode.STREAMING])
    modes_b = _build(supported_modes=[SupportedMode.STREAMING, SupportedMode.BATCH])
    assert _fp(modes_a) == _fp(modes_b)

    cals_a = _build(calendar_requirements=[_calendar("2025.2"), _calendar("2024.1")])
    cals_b = _build(calendar_requirements=[_calendar("2024.1"), _calendar("2025.2")])
    assert _fp(cals_a) == _fp(cals_b)


def test_duplicate_unordered_members_collapse() -> None:
    once = _build(supported_modes=[SupportedMode.BATCH])
    twice = _build(supported_modes=[SupportedMode.BATCH, SupportedMode.BATCH])
    assert _fp(once) == _fp(twice)


# --- a binary-float parameter is refused (exact rationals only) --------------


def test_binary_float_parameter_is_refused() -> None:
    refusal = _refuse(parameters={"period": 20.0})
    assert refusal.category.value == "invalid input"
    assert refusal.context["field"] == "parameters"


def test_non_exact_rational_parameter_is_refused() -> None:
    # A plain int is not an ExactRational — a parameter must carry its unit-kind exactly.
    assert _refuse(parameters={"period": 20}).context["field"] == "parameters"


def test_blank_parameter_name_is_refused() -> None:
    assert _refuse(parameters={"  ": _period()}).context["field"] == "parameters"


def test_parameters_must_be_a_mapping() -> None:
    assert _refuse(parameters=[_period()]).context["field"] == "parameters"


def test_empty_parameter_set_is_legal() -> None:
    config = _build(parameters={})
    assert config.parameters == {}
    assert _unwrap(config.fp1()).value.startswith("fp1:sha256:")


# --- top-level validation refusals ------------------------------------------


def test_blank_formula_id_is_refused() -> None:
    assert _refuse(formula_id="  ").context["field"] == "formula_id"


def test_non_positive_contract_format_version_is_refused() -> None:
    for bad in (0, -1, True, "1"):
        assert _refuse(contract_format_version=bad).context["field"] == "contract_format_version"


def test_empty_inputs_is_refused() -> None:
    assert _refuse(inputs=[]).context["field"] == "inputs"


def test_inputs_must_be_a_sequence_not_a_bare_value() -> None:
    assert _refuse(inputs=_series_input()).context["field"] == "inputs"


def test_duplicate_input_names_are_refused() -> None:
    refusal = _refuse(inputs=[_series_input("close"), _series_input("close")])
    assert refusal.context["name"] == "close"


def test_non_series_input_member_is_refused() -> None:
    assert _refuse(inputs=["close"]).context["field"] == "inputs"


def test_bad_calendar_requirement_is_refused() -> None:
    assert _refuse(calendar_requirements=["forex"]).context["field"] == "calendar_requirements"


def test_calendar_requirements_must_be_a_sequence() -> None:
    assert _refuse(calendar_requirements=_calendar()).context["field"] == "calendar_requirements"


def test_empty_calendar_requirements_is_legal() -> None:
    config = _build(calendar_requirements=[])
    assert config.calendar_requirements == ()


def test_bad_alignment_policy_is_refused() -> None:
    assert _refuse(alignment_policy="forward-fill").context["field"] == "alignment_policy"


def test_bad_missing_value_policy_is_refused() -> None:
    assert _refuse(missing_value_policy="forward-fill").context["field"] == "missing_value_policy"


def test_negative_warm_up_is_refused() -> None:
    for bad in (-1, True, "20", 1.0):
        assert _refuse(warm_up=bad).context["field"] == "warm_up"


def test_zero_warm_up_is_legal() -> None:
    assert _build(warm_up=0).warm_up == 0


def test_empty_output_schema_is_refused() -> None:
    assert _refuse(output_schema=[]).context["field"] == "output_schema"


def test_output_schema_must_be_a_sequence() -> None:
    assert _refuse(output_schema=_output_channel()).context["field"] == "output_schema"


def test_duplicate_output_channel_names_are_refused() -> None:
    refusal = _refuse(output_schema=[_output_channel("sma"), _output_channel("sma")])
    assert refusal.context["name"] == "sma"


def test_non_output_channel_member_is_refused() -> None:
    assert _refuse(output_schema=["sma"]).context["field"] == "output_schema"


def test_empty_supported_modes_is_refused() -> None:
    assert _refuse(supported_modes=[]).context["field"] == "supported_modes"


def test_bad_supported_mode_is_refused() -> None:
    assert _refuse(supported_modes=["hybrid"]).context["field"] == "supported_modes"


def test_supported_modes_must_be_a_collection_not_a_bare_string() -> None:
    assert _refuse(supported_modes="batch").context["field"] == "supported_modes"


def test_bad_arithmetic_reference_is_refused() -> None:
    refusal = _refuse(arithmetic_reference_configuration={"c_library": "x"})
    assert refusal.context["field"] == "arithmetic_reference_configuration"


# --- optional-element typing refusals ---------------------------------------


def test_bad_emission_policy_type_is_refused() -> None:
    assert _refuse(emission_policy="bar-closed").context["field"] == "emission_policy"


def test_bad_warm_up_time_bound_type_is_refused() -> None:
    assert _refuse(warm_up_time_bound=3600).context["field"] == "warm_up_time_bound"


def test_bad_declared_budget_type_is_refused() -> None:
    assert _refuse(declared_budget="light").context["field"] == "declared_budget"


# --- SeriesInput -------------------------------------------------------------


def test_series_input_accepts_instrument_or_source_id() -> None:
    with_instrument = _fp(_build(inputs=[_series_input("close")]))
    source_input = _unwrap(
        SeriesInput.try_create(
            name="close",
            source="my-external-source",
            bar_spec={"kind": "time-interval", "seconds": 60},
            channel_kind=ChannelKind.EXACT_PRICE,
            quote_side=QuoteSide.MID,
        )
    )
    with_source = _fp(_build(inputs=[source_input]))
    # An instrument source and a source-id token live in distinct identity spaces.
    assert with_instrument != with_source


def test_series_input_bar_spec_forms_are_all_fingerprintable() -> None:
    fp_ref = _unwrap(fingerprint({"kind": "time-interval", "seconds": 60}))
    forms: list[object] = [
        {"kind": "time-interval", "seconds": 60},  # canonical mapping
        fp_ref,  # a Fingerprint reference
        fp_ref.value,  # a fingerprint string
        _calendar(),  # any value exposing fp1_identity
    ]
    for spec in forms:
        series = _unwrap(
            SeriesInput.try_create(
                name="close",
                source=_instrument(),
                bar_spec=spec,
                channel_kind=ChannelKind.EXACT_PRICE,
                quote_side=QuoteSide.MID,
            )
        )
        assert _unwrap(fingerprint(series)).value.startswith("fp1:sha256:")


def test_series_input_derived_upstream_fingerprint_enters_identity() -> None:
    upstream = _unwrap(fingerprint({"artifact": "sma-20"}))
    derived = _unwrap(
        SeriesInput.try_create(
            name="close",
            source=_instrument(),
            bar_spec={"kind": "time-interval", "seconds": 60},
            channel_kind=ChannelKind.FLOAT_ANALYTIC,
            quote_side=QuoteSide.MID,
            upstream_fingerprint=upstream,
        )
    )
    assert derived.upstream_fingerprint == upstream
    assert "upstream_fingerprint" in derived.fp1_identity()
    assert _fp(_build(inputs=[derived])) != _fp(_build(inputs=[_series_input("close")]))


def test_series_input_refusals() -> None:
    valid = {
        "name": "close",
        "source": _instrument(),
        "bar_spec": {"kind": "time-interval", "seconds": 60},
        "channel_kind": ChannelKind.EXACT_PRICE,
        "quote_side": QuoteSide.MID,
    }
    assert is_refusal(SeriesInput.try_create(**{**valid, "name": "  "}))
    assert is_refusal(SeriesInput.try_create(**{**valid, "source": 123}))
    assert is_refusal(SeriesInput.try_create(**{**valid, "bar_spec": 123}))
    assert is_refusal(SeriesInput.try_create(**{**valid, "bar_spec": "not-a-fingerprint"}))
    assert is_refusal(SeriesInput.try_create(**{**valid, "bar_spec": {"weight": 1.5}}))
    assert is_refusal(SeriesInput.try_create(**{**valid, "channel_kind": "volume"}))
    assert is_refusal(SeriesInput.try_create(**{**valid, "quote_side": "close"}))
    assert is_refusal(SeriesInput.try_create(**{**valid, "upstream_fingerprint": "nope"}))


def test_series_input_bad_fp1_identity_bar_spec_object_is_refused() -> None:
    class _DirtySpec:
        def fp1_identity(self) -> Mapping[str, object]:
            return {"weight": 1.5}  # a float never enters identity

    result = SeriesInput.try_create(
        name="close",
        source=_instrument(),
        bar_spec=_DirtySpec(),
        channel_kind=ChannelKind.EXACT_PRICE,
        quote_side=QuoteSide.MID,
    )
    assert is_refusal(result)
    assert result.context["field"] == "bar_spec"


# --- OutputChannel -----------------------------------------------------------


def test_output_channel_refusals() -> None:
    assert is_refusal(
        OutputChannel.try_create("  ", ChannelKind.BOOLEAN, OutputArity.FIXED_VECTOR, 0)
    )
    assert is_refusal(OutputChannel.try_create("x", "not-a-kind", OutputArity.FIXED_VECTOR, 0))
    assert is_refusal(OutputChannel.try_create("x", ChannelKind.BOOLEAN, "not-an-arity", 0))
    assert is_refusal(
        OutputChannel.try_create("x", ChannelKind.BOOLEAN, OutputArity.FIXED_VECTOR, True)
    )
    assert is_refusal(
        OutputChannel.try_create("x", ChannelKind.BOOLEAN, OutputArity.FIXED_VECTOR, "0")
    )


# --- EmissionPolicy / DeclaredBudget / ArithmeticReference -------------------


def test_emission_policy_refusals() -> None:
    assert is_refusal(EmissionPolicy.try_create("never", "per-bar"))
    assert is_refusal(EmissionPolicy.try_create(EmissionTiming.BAR_CLOSED, "  "))
    ok = _unwrap(EmissionPolicy.try_create(EmissionTiming.BAR_CLOSED, "per-bar"))
    assert ok.fp1_identity()["timing"] == "bar-closed"


def test_declared_budget_refusals() -> None:
    assert is_refusal(DeclaredBudget.try_create("  ", True, "window", True))
    assert is_refusal(DeclaredBudget.try_create("rung", "yes", "window", True))
    assert is_refusal(DeclaredBudget.try_create("rung", True, "  ", True))
    assert is_refusal(DeclaredBudget.try_create("rung", True, "window", "yes"))
    ok = _unwrap(DeclaredBudget.try_create("live-path", True, "bounded-window", False))
    assert ok.fp1_identity()["bounded_state"] is True


def test_arithmetic_reference_refusals() -> None:
    assert is_refusal(ArithmeticReference.try_create("  ", "py", {"mode": "classic"}))
    assert is_refusal(ArithmeticReference.try_create("c", "  ", {"mode": "classic"}))
    assert is_refusal(ArithmeticReference.try_create("c", "py", ["mode"]))
    assert is_refusal(ArithmeticReference.try_create("c", "py", {}))
    assert is_refusal(ArithmeticReference.try_create("c", "py", {"mode": 1.5}))


def test_arithmetic_reference_configuration_change_changes_identity() -> None:
    base = _fp(_build())
    other_ref = _build(
        arithmetic_reference_configuration=_unwrap(
            ArithmeticReference.try_create(
                "ta-lib-c@sha256:aaaa",
                "ta-lib-py@sha256:bbbb",
                {"compatibility_mode": "metastock"},
            )
        )
    )
    assert _fp(other_ref) != base


# --- immutability -----------------------------------------------------------


def test_parameter_mapping_is_frozen_against_caller_mutation() -> None:
    params: dict[str, ExactRational] = {"period": _period(20)}
    config = _build(parameters=params)
    before = _fp(config)
    params["period"] = _period(99)  # mutating the caller's dict must not touch identity
    params["extra"] = _period(5)
    assert _fp(config) == before


def test_arithmetic_reference_configuration_is_frozen_against_caller_mutation() -> None:
    reference_config: dict[str, object] = {"compatibility_mode": "classic"}
    reference = _unwrap(
        ArithmeticReference.try_create("c@sha256:1", "py@sha256:2", reference_config)
    )
    before = _unwrap(fingerprint(reference)).value
    reference_config["compatibility_mode"] = "metastock"
    assert _unwrap(fingerprint(reference)).value == before


# --- the fp1 is the canonical qmf-core serialization -------------------------


def test_fp1_identity_is_fp1_clean_and_stable() -> None:
    config = _build()
    content = config.fp1_identity()
    # The whole declaration serializes cleanly through qmf-core's one serializer.
    assert is_ok(canonical_bytes(content))
    # Rebuilding the same configuration produces byte-identical canonical content.
    assert _unwrap(canonical_bytes(config.fp1_identity())) == _unwrap(
        canonical_bytes(_build().fp1_identity())
    )
