"""Reference usage — footprint, producer templates, derived horizon (Story 11.4).

Executable::

    python qml/examples/footprint_usage.py

Shows the things QL-4 / Story 11.4 pin down:

1. A producer template is a complete CT-16/CT-17 configuration minus only its
   space-bound parameter values. Resolution is a total, single-valued function
   producing one deterministic configured-producer fingerprint.
2. An omitted AD-22 identity field is a Layer-1 registration refusal.
3. Transitive-union completeness reports whether the footprint's producer-binding
   set equals the union of cited confluence-leg producers plus bot-direct producers.
4. The warm-up/embargo horizon is derived from the resolved producer chain — there
   is no second, hand-declared window on the declaration.
5. The stream set (instrument-role + BarSpec list, trading vs data-only) is nested
   inside the footprint; hosts provide only that declared footprint to the logic.
"""

from __future__ import annotations

from typing import TypeVar, cast

from qmf.core.chrono import CalendarIdentity
from qmf.core.exact import ExactRational, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Result, TypedRefusal, is_ok
from qml.footprint import (
    AD22_IDENTITY_FIELDS,
    Footprint,
    ProducerBinding,
    derive_horizon,
    mint_footprint,
    mint_producer_template,
    report_completeness,
    resolve_template,
)

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _period(n: int) -> ExactRational:
    return _unwrap(ExactRational.try_create(n, 1, UnitKind.COUNT), "period")


def _calendar() -> CalendarIdentity:
    return _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"), "calendar")


def _template_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "formula_id": "sma",
        "contract_format_version": 1,
        "inputs": [
            {
                "name": "close",
                "source": {"kind": "instrument", "venue": "venue-ic", "symbol": "EURUSD"},
                "bar_spec": {"kind": "time-interval", "seconds": 60},
                "channel_kind": "exact-price",
                "quote_side": "mid",
            }
        ],
        "calendar_requirements": [_calendar()],
        "alignment_policy": "as-of",
        "missing_value_policy": "mark-gap",
        "warm_up": 20,
        "output_schema": [
            {
                "name": "sma",
                "channel_kind": "float-analytic",
                "arity": "scalar-per-sample",
                "index_offset": 0,
            }
        ],
        "supported_modes": ["batch", "streaming"],
        "arithmetic_reference_configuration": {
            "c_library": "ta-lib-c@sha256:aaaa",
            "python_wrapper": "ta-lib-py@sha256:bbbb",
            "reference_configuration": {"compatibility_mode": "classic"},
        },
        "space_bound": {"period": "sma_period"},
    }
    body.update(overrides)
    return body


def _stream() -> dict[str, object]:
    return {
        "instrument_role": "primary",
        "bar_specs": [{"kind": "time-interval", "seconds": 60}],
        "stream_role": "trading",
    }


def resolution_is_total_and_single_valued() -> str:
    """Same assignment, any key order, one configured-producer fingerprint."""
    template = _unwrap(mint_producer_template(_template_body()), "template")
    a = _unwrap(resolve_template(template, {"sma_period": _period(20)}), "resolve-a")
    b = _unwrap(
        resolve_template(template, {"sma_period": _period(20), "unused": _period(1)}),
        "resolve-b",
    )
    fp_a = _unwrap(a.fingerprint_content(), "fp-a")
    fp_b = _unwrap(b.fingerprint_content(), "fp-b")
    via_core = _unwrap(fingerprint(a.fp1_identity()), "qmf-core fp1")
    assert fp_a == fp_b == via_core
    assert fp_a.value.startswith("fp1:sha256:")
    other = _unwrap(resolve_template(template, {"sma_period": _period(21)}), "resolve-21")
    assert _unwrap(other.fingerprint_content(), "fp-21") != fp_a
    return fp_a.value


def omitted_identity_field_is_layer1_refusal() -> TypedRefusal:
    """A template missing any AD-22 identity field is a Layer-1 registration refusal."""
    payload = _template_body()
    del payload["warm_up"]
    refused = mint_producer_template(payload)
    assert isinstance(refused, TypedRefusal)
    assert refused.category.value == "invalid input"
    assert refused.context["layer"] == 1
    assert refused.context["journal"] is True
    assert refused.context["field"] == "warm_up"
    assert "warm_up" in AD22_IDENTITY_FIELDS
    return refused


def completeness_reports_the_transitive_union() -> bool:
    """Footprint producer-binding set equals confluence legs plus bot-direct."""
    template = _unwrap(mint_producer_template(_template_body()), "template")
    binding = _unwrap(ProducerBinding.try_create(template), "binding")
    footprint = _unwrap(mint_footprint([_stream()], [_calendar()], [binding]), "footprint")
    complete = _unwrap(report_completeness(footprint, [binding], bot_direct=()), "complete")
    assert complete.complete is True
    empty = _unwrap(report_completeness(footprint, (), bot_direct=()), "empty-union")
    assert empty.complete is False
    assert empty.extra != ()
    return complete.complete


def horizon_is_derived_never_hand_declared() -> int:
    """Warm-up/embargo comes from the chain; a hand-declared window is refused."""
    template = _unwrap(mint_producer_template(_template_body()), "template")
    resolved = _unwrap(resolve_template(template, {"sma_period": _period(20)}), "resolved")
    horizon = _unwrap(derive_horizon((resolved,)), "horizon")
    assert horizon.warm_up == 20
    assert horizon.embargo == 0
    hand = Footprint.try_from_mapping(
        {
            "stream_set": [_stream()],
            "required_calendars": [_calendar()],
            "producer_bindings": [template],
            "warm_up_horizon": 99,
        }
    )
    assert isinstance(hand, TypedRefusal)
    assert hand.category.value == "invalid input"
    return horizon.warm_up


def stream_set_is_nested_and_is_the_host_manifest() -> dict[str, object]:
    """Hosts provide only the declared footprint; the stream set lives inside it."""
    template = _unwrap(mint_producer_template(_template_body()), "template")
    footprint = _unwrap(mint_footprint([_stream()], [_calendar()], [template]), "footprint")
    manifest = dict(footprint.host_manifest())
    streams = cast("list[dict[str, object]]", manifest["stream_set"])
    assert streams[0]["stream_role"] == "trading"
    assert "warm_up_horizon" not in manifest
    assert "timeframe" not in str(manifest)
    return manifest


def main() -> None:
    fp = resolution_is_total_and_single_valued()
    print(f"resolved producer fingerprint: {fp[:19]}...")
    refused = omitted_identity_field_is_layer1_refusal()
    print(f"omitted AD-22 field at Layer 1: {refused.category.value}")
    print(f"transitive-union complete: {completeness_reports_the_transitive_union()}")
    warm = horizon_is_derived_never_hand_declared()
    print(f"derived warm-up observations: {warm}")
    manifest = stream_set_is_nested_and_is_the_host_manifest()
    streams = cast("list[dict[str, object]]", manifest["stream_set"])
    print(f"host feeds nested stream set: {streams[0]['instrument_role']}")
    print("footprint authoring ok")


if __name__ == "__main__":
    main()
