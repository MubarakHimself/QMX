"""Reference usage — Layer 1 declaration linter (Story 12.3).

Executable::

    python qml/examples/layer1_usage.py

Shows the things QL-8 / Story 12.3 pin down:

1. Layer 1 runs at registration over in-memory catalogs. It is pure: no I/O,
   no process, no Book. Schema completeness is checked against the declared
   format version.
2. Every parameter is unit-kinded and the defaults form a valid canonical
   assignment. Every reference must resolve (family, confluence fingerprints,
   producer formulas at their declared format versions, logic distribution).
3. Footprint completeness is the Epic 11 transitive-union law: a confluence-leg
   producer absent from the footprint is a typed refusal. A template missing an
   AD-22 identity field is a typed refusal.
4. Permitted EXIT-intent kinds are a (possibly empty) subset of
   ``close_full | tighten_protective_stop``.
5. Failures are AD-11 typed refusals (``invalid input | unsupported capability
   | unavailable dependency``), journaled, never swallowed. An unknown contract
   format version is ``unsupported capability``, never a best-effort read.
"""

from __future__ import annotations

from typing import TypeVar, cast

from qmf.core.chrono import CalendarIdentity
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Result, TypedRefusal, is_ok
from qml.conformance import CONFORMANCE_FORMAT_VERSION, Layer1Verdict, lint_declaration
from qml.declaration import BotDefinition, mint_bot_definition, mint_confluence
from qml.families import mint_strategy_family
from qml.footprint import AD22_IDENTITY_FIELDS, ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity

T = TypeVar("T")

_SOURCE = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _pinned(tag: str) -> ProducerBinding:
    fp = _unwrap(fingerprint({"class": "example-producer", "tag": tag}), "producer fp")
    return _unwrap(ProducerBinding.try_create(fp), "binding")


def _calendar() -> CalendarIdentity:
    return _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"), "calendar")


def _stream() -> dict[str, object]:
    return {
        "instrument_role": "primary",
        "bar_specs": [{"kind": "time-interval", "seconds": 60}],
        "stream_role": "trading",
    }


def _int_param() -> dict[str, object]:
    return {
        "name": "lookback",
        "type": "exact integer",
        "bounds": {"min": 1, "max": 200},
        "step": 1,
        "default": 20,
        "unit_kind": UnitKind.COUNT,
        "ui": "ui-editable",
    }


def _world() -> dict[str, object]:
    zone = _pinned("zone")
    sma = _pinned("sma")
    family = _unwrap(mint_strategy_family("trend-follow"), "family")
    confluence = _unwrap(
        mint_confluence([{"role": "level", "producer_binding": zone}]),
        "confluence",
    )
    footprint = _unwrap(mint_footprint([_stream()], [_calendar()], [zone, sma]), "footprint")
    logic = _unwrap(mint_logic_identity("research-bot", "1.0.0", _SOURCE), "logic")
    declaration = _unwrap(
        mint_bot_definition(
            {
                "strategy_family_id": family.family_id.value,
                "confluence_set": [confluence],
                "parameter_space": [_int_param()],
                "footprint": footprint,
                "permitted_exit_intents": (),
                "logic_reference": logic,
            }
        ),
        "declaration",
    )
    return {
        "declaration": declaration,
        "family": family,
        "confluence": confluence,
        "logic": logic,
        "producers": [zone, sma],
        "zone": zone,
        "sma": sma,
    }


def _declaration_of(world: dict[str, object]) -> BotDefinition:
    return cast(BotDefinition, world["declaration"])


def _run(world: dict[str, object], **overrides: object) -> Result[Layer1Verdict]:
    kwargs: dict[str, object] = {
        "declaration": world["declaration"],
        "family_catalog": [world["family"]],
        "confluence_catalog": [world["confluence"]],
        "producer_catalog": world["producers"],
        "logic_catalog": [world["logic"]],
    }
    kwargs.update(overrides)
    return lint_declaration(**kwargs)


def clean_declaration_passes() -> bool:
    world = _world()
    verdict = _unwrap(_run(world), "layer1")
    assert verdict.fp1_identity()["contract_format_version"] == CONFORMANCE_FORMAT_VERSION
    assert verdict.declaration.permitted_exit_intents == ()
    return True


def missing_unit_kind() -> str:
    world = _world()
    declaration = _declaration_of(world)
    payload = {
        "strategy_family_id": declaration.strategy_family_id.value,
        "confluence_set": list(declaration.confluence_set),
        "parameter_space": [
            {
                "name": "lookback",
                "type": "exact integer",
                "bounds": {"min": 1, "max": 10},
                "step": 1,
                "default": 2,
                "ui": "ui-editable",
            }
        ],
        "footprint": declaration.footprint,
        "logic_reference": declaration.logic_reference,
    }
    refused = lint_declaration(payload)
    assert isinstance(refused, TypedRefusal)
    assert refused.context["journal"] is True
    return refused.category.value


def unresolvable_family() -> str:
    world = _world()
    refused = _run(world, family_catalog=())
    assert isinstance(refused, TypedRefusal)
    return refused.category.value


def unresolvable_confluence() -> str:
    world = _world()
    refused = _run(world, confluence_catalog=())
    assert isinstance(refused, TypedRefusal)
    return refused.category.value


def unresolvable_logic() -> str:
    world = _world()
    refused = _run(world, logic_catalog=())
    assert isinstance(refused, TypedRefusal)
    return refused.category.value


def unresolvable_producer_formula() -> str:
    world = _world()
    template = {
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
            "reference_configuration": {
                "compatibility_mode": "classic",
                "candle_settings": "default",
            },
        },
        "space_bound": {"period": "lookback"},
    }
    binding = _unwrap(ProducerBinding.try_create(template), "template binding")
    confluence = _unwrap(
        mint_confluence([{"role": "level", "producer_binding": binding}]),
        "template confluence",
    )
    footprint = _unwrap(mint_footprint([_stream()], [_calendar()], [binding]), "template footprint")
    declaration = _declaration_of(world)
    authored = _unwrap(
        mint_bot_definition(
            {
                "strategy_family_id": declaration.strategy_family_id.value,
                "confluence_set": [confluence],
                "parameter_space": [_int_param()],
                "footprint": footprint,
                "logic_reference": declaration.logic_reference,
            }
        ),
        "template declaration",
    )
    refused = lint_declaration(
        authored,
        family_catalog=[world["family"]],
        confluence_catalog=[confluence],
        producer_catalog=(),
        formula_catalog=(),
        logic_catalog=[world["logic"]],
    )
    assert isinstance(refused, TypedRefusal)
    return refused.category.value


def missing_confluence_leg_producer() -> str:
    world = _world()
    zone = world["zone"]
    sma = world["sma"]
    confluence = world["confluence"]
    footprint = _unwrap(mint_footprint([_stream()], [_calendar()], [sma]), "incomplete footprint")
    declaration = _declaration_of(world)
    authored = _unwrap(
        mint_bot_definition(
            {
                "strategy_family_id": declaration.strategy_family_id.value,
                "confluence_set": [confluence],
                "parameter_space": [_int_param()],
                "footprint": footprint,
                "logic_reference": declaration.logic_reference,
            }
        ),
        "incomplete declaration",
    )
    refused = lint_declaration(
        authored,
        family_catalog=[world["family"]],
        confluence_catalog=[confluence],
        producer_catalog=[zone, sma],
        logic_catalog=[world["logic"]],
    )
    assert isinstance(refused, TypedRefusal)
    assert refused.context["missing"] != ()
    return refused.category.value


def omitted_identity_field() -> str:
    incomplete = {
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
            "reference_configuration": {
                "compatibility_mode": "classic",
                "candle_settings": "default",
            },
        },
    }
    assert "warm_up" not in incomplete
    assert "warm_up" in AD22_IDENTITY_FIELDS
    world = _world()
    declaration = _declaration_of(world)
    refused = lint_declaration(
        {
            "strategy_family_id": declaration.strategy_family_id.value,
            "confluence_set": list(declaration.confluence_set),
            "parameter_space": [_int_param()],
            "footprint": {
                "stream_set": [_stream()],
                "required_calendars": [_calendar()],
                "producer_bindings": [incomplete],
            },
            "logic_reference": declaration.logic_reference,
        }
    )
    assert isinstance(refused, TypedRefusal)
    assert refused.context["field"] == "warm_up"
    return refused.category.value


def exit_kind_outside_vocabulary() -> str:
    world = _world()
    declaration = _declaration_of(world)
    refused = lint_declaration(
        {
            "strategy_family_id": declaration.strategy_family_id.value,
            "confluence_set": list(declaration.confluence_set),
            "parameter_space": [_int_param()],
            "footprint": declaration.footprint,
            "permitted_exit_intents": ("close_partial",),
            "logic_reference": declaration.logic_reference,
        }
    )
    assert isinstance(refused, TypedRefusal)
    return refused.category.value


def unknown_format_version() -> str:
    refused = lint_declaration({"contract_format_version": 2, "strategy_family_id": "trend-follow"})
    assert isinstance(refused, TypedRefusal)
    assert refused.context["journal"] is True
    return refused.category.value


def failures_are_journaled() -> bool:
    world = _world()
    family = cast(TypedRefusal, _run(world, family_catalog=()))
    schema = lint_declaration({"strategy_family_id": "trend-follow"})
    version = lint_declaration({"contract_format_version": 2})
    assert isinstance(schema, TypedRefusal)
    assert isinstance(version, TypedRefusal)
    assert family.context["journal"] is True
    assert schema.context["journal"] is True
    assert version.context["journal"] is True
    return True


def main() -> None:
    print(f"layer 1 format version: {CONFORMANCE_FORMAT_VERSION}")
    print(f"clean declaration passes: {clean_declaration_passes()}")
    print(f"missing unit-kind: {missing_unit_kind()}")
    print(f"unresolvable family: {unresolvable_family()}")
    print(f"unresolvable confluence: {unresolvable_confluence()}")
    print(f"unresolvable logic: {unresolvable_logic()}")
    print(f"unresolvable producer formula: {unresolvable_producer_formula()}")
    print(f"missing confluence-leg producer: {missing_confluence_leg_producer()}")
    print(f"omitted AD-22 field: {omitted_identity_field()}")
    print(f"exit kind outside vocabulary: {exit_kind_outside_vocabulary()}")
    print(f"unknown contract format version: {unknown_format_version()}")
    print(f"layer 1 failures journaled: {failures_are_journaled()}")
    print("layer1 linter ok")


if __name__ == "__main__":
    main()
