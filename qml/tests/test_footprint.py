"""Story 11.4 — footprint, producer templates, and horizon derivation (QL-4)."""

from __future__ import annotations

from typing import TypeVar, cast

from qmf.core.chrono import CalendarIdentity
from qmf.core.exact import ExactRational, UnitKind
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.indicators import (
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
from qml.footprint import (
    AD22_IDENTITY_FIELDS,
    FORBIDDEN_HORIZON_FIELDS,
    CompletenessReport,
    Footprint,
    Horizon,
    ProducerBinding,
    ProducerBindingForm,
    ProducerKind,
    ProducerTemplate,
    StreamMember,
    StreamRole,
    compute_transitive_union,
    derive_horizon,
    mint_footprint,
    mint_producer_template,
    report_completeness,
    resolve_template,
)

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _period(numerator: int = 20) -> ExactRational:
    return _ok(ExactRational.try_create(numerator, 1, UnitKind.COUNT))


def _calendar(tzdata_version: str = "2025.2") -> CalendarIdentity:
    return _ok(CalendarIdentity.try_create("forex-17NY", "v3", tzdata_version))


def _input(name: str = "close") -> dict[str, object]:
    return {
        "name": name,
        "source": {"kind": "instrument", "venue": "venue-ic", "symbol": "EURUSD"},
        "bar_spec": {"kind": "time-interval", "seconds": 60},
        "channel_kind": "exact-price",
        "quote_side": "mid",
    }


def _output(name: str = "sma") -> dict[str, object]:
    return {
        "name": name,
        "channel_kind": "float-analytic",
        "arity": "scalar-per-sample",
        "index_offset": 0,
    }


def _arithmetic() -> dict[str, object]:
    return {
        "c_library": "ta-lib-c@sha256:aaaa",
        "python_wrapper": "ta-lib-py@sha256:bbbb",
        "reference_configuration": {
            "compatibility_mode": "classic",
            "candle_settings": "default",
        },
    }


def _template_fields(**overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "formula_id": "sma",
        "contract_format_version": 1,
        "inputs": [_input()],
        "calendar_requirements": [_calendar()],
        "alignment_policy": "as-of",
        "missing_value_policy": "mark-gap",
        "warm_up": 20,
        "output_schema": [_output()],
        "supported_modes": ["batch", "streaming"],
        "arithmetic_reference_configuration": _arithmetic(),
        "space_bound": {"period": "sma_period"},
    }
    fields.update(overrides)
    return fields


def _template(**overrides: object) -> ProducerTemplate:
    return _ok(mint_producer_template(_template_fields(**overrides)))


def _stream(*, role: str = "trading") -> dict[str, object]:
    return {
        "instrument_role": "primary",
        "bar_specs": [{"kind": "time-interval", "seconds": 60}],
        "stream_role": role,
    }


def _pinned(tag: str) -> ProducerBinding:
    fp = _ok(fingerprint({"class": "test-producer", "tag": tag}))
    return _ok(ProducerBinding.try_create(fp))


# --- AC: resolution is total, single-valued ----------------------------------


def test_template_resolution_is_total_and_single_valued() -> None:
    template = _template()
    first = _ok(resolve_template(template, {"sma_period": _period(20)}))
    again = _ok(resolve_template(template, {"sma_period": _period(20)}))
    shuffled = _ok(
        resolve_template(
            template,
            {"unused": _period(99), "sma_period": _period(20)},
        )
    )
    assert first.fp1_identity() == again.fp1_identity() == shuffled.fp1_identity()
    fp_a = _ok(first.fingerprint_content())
    fp_b = _ok(again.fingerprint_content())
    fp_c = _ok(shuffled.fingerprint_content())
    assert fp_a == fp_b == fp_c
    assert fp_a.value.startswith("fp1:sha256:")
    via_core = _ok(fingerprint(first.fp1_identity()))
    assert fp_a == via_core


def test_different_space_bound_values_yield_distinct_fingerprints() -> None:
    twenty = _ok(resolve_template(_template(), {"sma_period": _period(20)}))
    twenty_one = _ok(resolve_template(_template(), {"sma_period": _period(21)}))
    assert _ok(twenty.fingerprint_content()) != _ok(twenty_one.fingerprint_content())


def test_missing_assignment_is_not_a_second_fingerprint() -> None:
    missing = resolve_template(_template(), {})
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.INVALID_INPUT
    assert missing.context["bot_space_parameter"] == "sma_period"
    blank = resolve_template(_template(), None)
    assert is_refusal(blank)


def test_resolved_indicator_fingerprint_matches_configured_indicator() -> None:
    """Dedup lands on ordinary CT-16 configured-producer fingerprints."""
    venue = _ok(VenueId.try_create("venue-ic"))
    instrument = _ok(Instrument.try_create(venue, "EURUSD"))
    series = _ok(
        SeriesInput.try_create(
            name="close",
            source=instrument,
            bar_spec={"kind": "time-interval", "seconds": 60},
            channel_kind=ChannelKind.EXACT_PRICE,
            quote_side=QuoteSide.MID,
        )
    )
    channel = _ok(
        OutputChannel.try_create(
            "sma", ChannelKind.FLOAT_ANALYTIC, OutputArity.SCALAR_PER_SAMPLE, 0
        )
    )
    arithmetic = _ok(
        ArithmeticReference.try_create(
            "ta-lib-c@sha256:aaaa",
            "ta-lib-py@sha256:bbbb",
            {"compatibility_mode": "classic", "candle_settings": "default"},
        )
    )
    configured = _ok(
        ConfiguredIndicator.try_create(
            formula_id="sma",
            contract_format_version=1,
            parameters={"period": _period(20)},
            inputs=[series],
            calendar_requirements=[_calendar()],
            alignment_policy=AlignmentPolicy.AS_OF,
            missing_value_policy=MissingValuePolicy.MARK_GAP,
            warm_up=20,
            output_schema=[channel],
            supported_modes=[SupportedMode.BATCH, SupportedMode.STREAMING],
            arithmetic_reference_configuration=arithmetic,
        )
    )
    resolved = _ok(resolve_template(_template(), {"sma_period": _period(20)}))
    qml_fp = _ok(resolved.fingerprint_content())
    ind_fp = _ok(configured.fp1())
    assert qml_fp == ind_fp
    assert qml_fp == _ok(fingerprint(configured.fp1_identity()))


# --- AC: omitted AD-22 identity field is Layer-1 registration refusal --------


def test_template_missing_any_ad22_identity_field_is_layer1_refusal() -> None:
    assert AD22_IDENTITY_FIELDS == (
        "formula_id",
        "contract_format_version",
        "inputs",
        "calendar_requirements",
        "alignment_policy",
        "missing_value_policy",
        "warm_up",
        "output_schema",
        "supported_modes",
        "arithmetic_reference_configuration",
    )
    for field in AD22_IDENTITY_FIELDS:
        payload = _template_fields()
        del payload[field]
        refused = mint_producer_template(payload)
        assert is_refusal(refused), field
        assert refused.category is RefusalCategory.INVALID_INPUT
        assert refused.context["layer"] == 1
        assert refused.context["journal"] is True
        assert refused.context["field"] == field


def test_template_blank_formula_id_is_layer1_refusal() -> None:
    refused = mint_producer_template(_template_fields(formula_id="  "))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["journal"] is True


def test_space_bound_and_fixed_parameter_overlap_is_invalid() -> None:
    refused = mint_producer_template(_template_fields(fixed_parameters={"period": _period(20)}))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_binary_float_parameter_is_refused() -> None:
    refused = resolve_template(_template(), {"sma_period": 20.5})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


# --- AC: transitive-union completeness ---------------------------------------


def test_complete_footprint_equals_confluence_legs_plus_bot_direct() -> None:
    leg = _pinned("leg-sma")
    direct = _pinned("bot-direct")
    extra = _pinned("extra")
    footprint = _ok(
        mint_footprint([_stream()], [_calendar()], [leg, direct]),
    )
    report = _ok(report_completeness(footprint, [leg], bot_direct=[direct]))
    assert isinstance(report, CompletenessReport)
    assert report.complete is True
    assert report.missing == ()
    assert report.extra == ()
    incomplete = _ok(report_completeness(footprint, [leg, extra], bot_direct=[direct]))
    assert incomplete.complete is False
    assert incomplete.missing != ()
    stuffed = _ok(
        mint_footprint([_stream()], [_calendar()], [leg, direct, extra]),
    )
    extras = _ok(report_completeness(stuffed, [leg], bot_direct=[direct]))
    assert extras.complete is False
    assert extras.extra != ()


def test_transitive_union_walks_child_confluence_cites() -> None:
    child_binding = _pinned("child-level")
    parent_binding = _pinned("parent-trigger")
    catalog = {
        "child-conf": [{"producer_binding": child_binding}],
    }
    parent_legs = [
        {"producer_binding": parent_binding, "confluence_ref": "child-conf"},
    ]
    union = _ok(compute_transitive_union(parent_legs, catalog=catalog))
    keys = {_ok(item.fingerprint_content()).value for item in union}
    assert _ok(parent_binding.fingerprint_content()).value in keys
    assert _ok(child_binding.fingerprint_content()).value in keys
    missing_child = compute_transitive_union(
        [{"confluence_ref": "unknown"}],
        catalog=catalog,
    )
    assert is_refusal(missing_child)
    assert missing_child.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_cyclic_confluence_composition_is_invalid() -> None:
    catalog = {
        "a": [{"confluence_ref": "b"}],
        "b": [{"confluence_ref": "a"}],
    }
    cycled = compute_transitive_union([{"confluence_ref": "a"}], catalog=catalog)
    assert is_refusal(cycled)
    assert cycled.category is RefusalCategory.INVALID_INPUT


# --- AC: horizon derived from the chain, never hand-declared -----------------


def test_horizon_is_derived_as_the_sum_along_the_chain() -> None:
    sma = _ok(resolve_template(_template(), {"sma_period": _period(20)}))
    slow = _ok(
        resolve_template(
            _template(formula_id="ema", warm_up=14, output_schema=[_output("ema")]),
            {"sma_period": _period(14)},
        )
    )
    horizon = _ok(derive_horizon((sma, slow)))
    assert isinstance(horizon, Horizon)
    assert horizon.warm_up == 34
    assert horizon.embargo == 0
    assert horizon.total == 34
    one = _ok(derive_horizon(sma))
    assert one.warm_up == 20


def test_structure_confirmation_delay_feeds_embargo() -> None:
    structure = _ok(
        resolve_template(
            _template(
                producer_kind=ProducerKind.STRUCTURE,
                formula_id="swing-point",
                confirmation_delay_bound=3,
                warm_up=5,
            ),
            {"sma_period": _period(5)},
        )
    )
    horizon = _ok(derive_horizon((structure,)))
    assert horizon.warm_up == 5
    assert horizon.embargo == 3
    assert horizon.total == 8


def test_unbounded_confirmation_delay_cannot_derive_a_finite_horizon() -> None:
    unbounded = _ok(
        resolve_template(
            _template(
                producer_kind=ProducerKind.STRUCTURE,
                confirmation_delay="unbounded",
            ),
            {"sma_period": _period(20)},
        )
    )
    refused = derive_horizon((unbounded,))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_hand_declared_horizon_field_is_refused() -> None:
    for field in FORBIDDEN_HORIZON_FIELDS:
        refused = Footprint.try_from_mapping(
            {
                "stream_set": [_stream()],
                "required_calendars": [_calendar()],
                "producer_bindings": [_pinned("x")],
                field: 99,
            }
        )
        assert is_refusal(refused), field
        assert refused.category is RefusalCategory.INVALID_INPUT
        forbidden = refused.context["forbidden"]
        assert isinstance(forbidden, tuple)
        assert field in forbidden
    via_kwargs = Footprint.try_create(
        [_stream()],
        [_calendar()],
        [_pinned("x")],
        warm_up_horizon=12,
    )
    assert is_refusal(via_kwargs)
    payload = _ok(mint_footprint([_stream()], [_calendar()], [_pinned("x")])).fp1_identity()
    for field in FORBIDDEN_HORIZON_FIELDS:
        assert field not in payload


def test_empty_chain_is_invalid() -> None:
    assert is_refusal(derive_horizon(()))
    assert is_refusal(derive_horizon("not-a-chain"))


# --- AC: stream set nested inside the footprint ------------------------------


def test_stream_set_is_nested_trading_or_data_only() -> None:
    trading = _ok(
        StreamMember.try_create("primary", [{"kind": "time-interval", "seconds": 60}], "trading")
    )
    data_only = _ok(
        StreamMember.try_create(
            "bias",
            [{"kind": "time-interval", "seconds": 3600}],
            StreamRole.DATA_ONLY,
        )
    )
    footprint = _ok(mint_footprint([trading, data_only], [_calendar()], [_pinned("sma")]))
    payload = footprint.fp1_identity()
    streams = cast("list[dict[str, object]]", payload["stream_set"])
    assert streams[0]["stream_role"] == "trading"
    assert streams[1]["stream_role"] == "data-only"
    assert streams[0]["instrument_role"] == "primary"
    assert "timeframe" not in str(payload)
    manifest = dict(footprint.host_manifest())
    assert set(manifest) == {
        "class",
        "stream_set",
        "required_calendars",
        "producer_bindings",
        "format_version",
    }
    assert "warm_up_horizon" not in manifest


def test_hosts_receive_only_the_declared_footprint_manifest() -> None:
    footprint = _ok(mint_footprint([_stream()], [_calendar()], [_pinned("sma")]))
    fed = footprint.host_manifest()
    assert fed == footprint.fp1_identity()
    assert "stream_set" in fed
    # The stream set is not a sibling of the footprint — it is nested inside it.
    assert "stream_set" not in {"family_id", "confluence_set", "parameter_space"}


def test_stream_set_refuses_unknown_role_and_empty_barspecs() -> None:
    assert is_refusal(
        StreamMember.try_create("primary", [{"kind": "time-interval", "seconds": 60}], "htf")
    )
    assert is_refusal(StreamMember.try_create("primary", [], "trading"))
    assert is_refusal(
        StreamMember.try_create("  ", [{"kind": "time-interval", "seconds": 60}], "trading")
    )
    assert is_refusal(mint_footprint([], [_calendar()], []))


def test_unknown_barspec_kind_is_invalid() -> None:
    refused = StreamMember.try_create("primary", [{"kind": "timeframe", "seconds": 60}], "trading")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_pinned_and_template_bindings_are_distinct_forms() -> None:
    template = _template()
    templated = _ok(ProducerBinding.try_create(template))
    assert templated.form is ProducerBindingForm.TEMPLATE
    pinned = _pinned("sma")
    assert pinned.form is ProducerBindingForm.PINNED_FINGERPRINT
    assert _ok(templated.fingerprint_content()) != _ok(pinned.fingerprint_content())
    parsed = _ok(ProducerBinding.try_create(pinned.pinned.value if pinned.pinned else ""))
    assert parsed.form is ProducerBindingForm.PINNED_FINGERPRINT


def test_template_binding_round_trips_from_mapping() -> None:
    template = _template()
    binding = _ok(
        ProducerBinding.try_create({"form": "template", "template": template.fp1_identity()})
    )
    assert binding.form is ProducerBindingForm.TEMPLATE
    assert binding.template is not None
    assert binding.template.formula_id == "sma"
    fp = _ok(Fingerprint.try_create(_ok(fingerprint({"k": "v"})).value))
    from_fp = _ok(ProducerBinding.try_create({"form": "pinned-fingerprint", "fingerprint": fp}))
    assert from_fp.pinned == fp


def test_duplicate_instrument_role_is_invalid() -> None:
    refused = mint_footprint([_stream(), _stream()], [_calendar()], [])
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
