"""Story 12.3 — Layer 1 declaration linter (QL-8)."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar, cast

from qmf.core.chrono import CalendarIdentity
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qml.conformance import (
    CONFORMANCE_FORMAT_VERSION,
    LAYER1_CHECKS,
    Layer1Verdict,
    lint_declaration,
)
from qml.declaration import (
    BOT_DEFINITION_KIND_FORMAT_VERSION,
    PERMITTED_EXIT_INTENT_VOCABULARY,
    BotDefinition,
    Confluence,
    mint_bot_definition,
    mint_confluence,
)
from qml.families import mint_strategy_family
from qml.footprint import (
    AD22_IDENTITY_FIELDS,
    ProducerBinding,
    mint_footprint,
    mint_producer_template,
)
from qml.logic import mint_logic_identity

import qml

T = TypeVar("T")

_SOURCE: dict[str, str] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}
_LAYER1 = Path(__file__).resolve().parents[1] / "src" / "qml" / "conformance" / "layer1.py"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _pinned(tag: str) -> ProducerBinding:
    fp = _ok(fingerprint({"class": "test-producer", "tag": tag}))
    return _ok(ProducerBinding.try_create(fp))


def _calendar() -> CalendarIdentity:
    return _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))


def _logic():
    return _ok(mint_logic_identity("research-bot", "1.0.0", _SOURCE))


def _family():
    return _ok(mint_strategy_family("trend-follow"))


def _int_param(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "lookback",
        "type": "exact integer",
        "bounds": {"min": 1, "max": 200},
        "step": 1,
        "default": 20,
        "unit_kind": UnitKind.COUNT,
        "ui": "ui-editable",
    }
    payload.update(overrides)
    return payload


def _stream() -> dict[str, object]:
    return {
        "instrument_role": "primary",
        "bar_specs": [{"kind": "time-interval", "seconds": 60}],
        "stream_role": "trading",
    }


def _input() -> dict[str, object]:
    return {
        "name": "close",
        "source": {"kind": "instrument", "venue": "venue-ic", "symbol": "EURUSD"},
        "bar_spec": {"kind": "time-interval", "seconds": 60},
        "channel_kind": "exact-price",
        "quote_side": "mid",
    }


def _output() -> dict[str, object]:
    return {
        "name": "sma",
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
        "space_bound": {"period": "lookback"},
    }
    fields.update(overrides)
    return fields


def _fixture(*, extra_footprint: object = None) -> dict[str, object]:
    zone = _pinned("zone")
    sma = _pinned("sma") if extra_footprint is None else extra_footprint
    confluence = _ok(mint_confluence([{"role": "level", "producer_binding": zone}]))
    bindings = [zone] if extra_footprint is False else [zone, sma]
    footprint = _ok(mint_footprint([_stream()], [_calendar()], bindings))
    logic = _logic()
    family = _family()
    declaration = _ok(
        mint_bot_definition(
            {
                "strategy_family_id": family.family_id.value,
                "confluence_set": [confluence],
                "parameter_space": [_int_param()],
                "footprint": footprint,
                "permitted_exit_intents": (),
                "logic_reference": logic,
            }
        )
    )
    producers = [zone] if extra_footprint is False else [zone, sma]
    return {
        "declaration": declaration,
        "family": family,
        "confluence": confluence,
        "logic": logic,
        "producers": producers,
        "zone": zone,
        "sma": sma,
    }


def _lint(
    declaration: object,
    *,
    family: object = None,
    confluence: object = None,
    producers: object = None,
    formulas: object = (),
    logic: object = None,
) -> Result[Layer1Verdict]:
    return lint_declaration(
        declaration,
        family_catalog=() if family is None else [family],
        confluence_catalog=() if confluence is None else [confluence],
        producer_catalog=() if producers is None else producers,
        formula_catalog=formulas,
        logic_catalog=() if logic is None else [logic],
    )


def _lint_fixture(fix: dict[str, object], **overrides: object) -> Result[Layer1Verdict]:
    kwargs = {
        "declaration": fix["declaration"],
        "family": fix["family"],
        "confluence": fix["confluence"],
        "producers": fix["producers"],
        "logic": fix["logic"],
    }
    kwargs.update(overrides)
    return _lint(**kwargs)


# --- AC: schema completeness, unit-kinds, resolvable refs --------------------


def test_clean_declaration_passes_every_layer1_check() -> None:
    fix = _fixture()
    verdict = _ok(_lint_fixture(fix))
    assert isinstance(verdict, Layer1Verdict)
    assert verdict.checks == LAYER1_CHECKS
    assert verdict.declaration is fix["declaration"]
    identity = verdict.fp1_identity()
    assert identity["class"] == "qml-layer1-verdict"
    assert identity["contract_format_version"] == CONFORMANCE_FORMAT_VERSION
    assert identity["declaration_fingerprint"] == verdict.fingerprint.value
    assert qml.__version__ not in identity.values()
    assert "version" not in identity


def test_mapping_declaration_passes_when_catalogs_resolve() -> None:
    fix = _fixture()
    bot = cast(BotDefinition, fix["declaration"])
    mapping = {
        "contract_format_version": BOT_DEFINITION_KIND_FORMAT_VERSION,
        "strategy_family_id": bot.strategy_family_id.value,
        "confluence_set": list(bot.confluence_set),
        "parameter_space": [_int_param()],
        "footprint": bot.footprint,
        "permitted_exit_intents": bot.permitted_exit_intents,
        "logic_reference": bot.logic_reference,
    }
    verdict = _ok(_lint_fixture(fix, declaration=mapping))
    assert _ok(verdict.declaration.fingerprint_content()) == _ok(bot.fingerprint_content())


def test_missing_required_group_is_invalid_input_and_journaled() -> None:
    refused = lint_declaration({"strategy_family_id": "trend-follow"})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["journal"] is True
    assert refused.context["layer"] == 1


def test_parameter_missing_unit_kind_is_invalid_input() -> None:
    fix = _fixture()
    bot = cast(BotDefinition, fix["declaration"])
    payload = {
        "strategy_family_id": bot.strategy_family_id.value,
        "confluence_set": list(bot.confluence_set),
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
        "footprint": bot.footprint,
        "logic_reference": bot.logic_reference,
    }
    refused = _lint_fixture(fix, declaration=payload)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "unit_kind"
    assert refused.context["journal"] is True


def test_unresolvable_family_is_unavailable_dependency() -> None:
    fix = _fixture()
    refused = _lint_fixture(fix, family=None)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refused.context["field"] == "strategy_family_id"
    assert refused.context["journal"] is True


def test_unresolvable_confluence_is_unavailable_dependency() -> None:
    fix = _fixture()
    refused = _lint_fixture(fix, confluence=None)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refused.context["field"] == "confluence_ref"
    assert refused.context["journal"] is True


def test_unresolvable_logic_is_unavailable_dependency() -> None:
    fix = _fixture()
    refused = _lint_fixture(fix, logic=None)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refused.context["field"] == "logic_reference"
    assert refused.context["journal"] is True


def test_unresolvable_pinned_producer_is_unavailable_dependency() -> None:
    fix = _fixture()
    refused = _lint_fixture(fix, producers=())
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refused.context["journal"] is True


def test_unresolvable_producer_formula_is_unavailable_dependency() -> None:
    template = _ok(mint_producer_template(_template_fields()))
    binding = _ok(ProducerBinding.try_create(template))
    confluence = _ok(mint_confluence([{"role": "level", "producer_binding": binding}]))
    footprint = _ok(mint_footprint([_stream()], [_calendar()], [binding]))
    logic = _logic()
    family = _family()
    declaration = _ok(
        mint_bot_definition(
            {
                "strategy_family_id": family.family_id.value,
                "confluence_set": [confluence],
                "parameter_space": [_int_param()],
                "footprint": footprint,
                "logic_reference": logic,
            }
        )
    )
    missing = _lint(
        declaration,
        family=family,
        confluence=confluence,
        producers=(),
        formulas=(),
        logic=logic,
    )
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert missing.context["field"] == "formula_id"
    assert missing.context["journal"] is True
    present = _ok(
        _lint(
            declaration,
            family=family,
            confluence=confluence,
            producers=(),
            formulas=[{"formula_id": "sma", "contract_format_version": 1}],
            logic=logic,
        )
    )
    assert present.declaration is declaration
    wrong_version = _lint(
        declaration,
        family=family,
        confluence=confluence,
        producers=(),
        formulas={"sma": 2},
        logic=logic,
    )
    assert is_refusal(wrong_version)
    assert wrong_version.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert wrong_version.context["contract_format_version"] == 1


# --- AC: footprint transitive-union and template completeness ----------------


def test_confluence_leg_producer_absent_from_footprint_is_invalid_input() -> None:
    zone = _pinned("zone")
    other = _pinned("other")
    confluence = _ok(mint_confluence([{"role": "level", "producer_binding": zone}]))
    footprint = _ok(mint_footprint([_stream()], [_calendar()], [other]))
    logic = _logic()
    family = _family()
    declaration = _ok(
        mint_bot_definition(
            {
                "strategy_family_id": family.family_id.value,
                "confluence_set": [confluence],
                "parameter_space": [_int_param()],
                "footprint": footprint,
                "logic_reference": logic,
            }
        )
    )
    refused = _lint(
        declaration,
        family=family,
        confluence=confluence,
        producers=[zone, other],
        logic=logic,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "footprint"
    assert refused.context["missing"] != ()
    assert refused.context["journal"] is True


def test_bot_direct_producer_is_allowed_when_confluence_legs_are_present() -> None:
    fix = _fixture()
    verdict = _ok(_lint_fixture(fix))
    assert len(verdict.declaration.footprint.producer_bindings) == 2


def test_omitted_ad22_identity_field_is_layer1_typed_refusal() -> None:
    fix = _fixture()
    bot = cast(BotDefinition, fix["declaration"])
    for field in AD22_IDENTITY_FIELDS:
        incomplete = _template_fields()
        del incomplete[field]
        payload = {
            "strategy_family_id": bot.strategy_family_id.value,
            "confluence_set": list(bot.confluence_set),
            "parameter_space": [_int_param()],
            "footprint": {
                "stream_set": [_stream()],
                "required_calendars": [_calendar()],
                "producer_bindings": [incomplete],
            },
            "logic_reference": bot.logic_reference,
        }
        refused = lint_declaration(payload)
        assert is_refusal(refused), field
        assert refused.category is RefusalCategory.INVALID_INPUT
        assert refused.context["field"] == field
        assert refused.context["layer"] == 1
        assert refused.context["journal"] is True


# --- AC: permitted exit intents ---------------------------------------------


def test_permitted_exit_intents_must_be_ct23_subset() -> None:
    assert frozenset({"close_full", "tighten_protective_stop"}) == PERMITTED_EXIT_INTENT_VOCABULARY
    fix = _fixture()
    bot = cast(BotDefinition, fix["declaration"])
    both = _ok(
        mint_bot_definition(
            {
                "strategy_family_id": bot.strategy_family_id.value,
                "confluence_set": list(bot.confluence_set),
                "parameter_space": [_int_param()],
                "footprint": bot.footprint,
                "permitted_exit_intents": ("close_full", "tighten_protective_stop"),
                "logic_reference": bot.logic_reference,
            }
        )
    )
    assert _ok(_lint_fixture(fix, declaration=both)).declaration.permitted_exit_intents == (
        "close_full",
        "tighten_protective_stop",
    )
    refused = lint_declaration(
        {
            "strategy_family_id": bot.strategy_family_id.value,
            "confluence_set": list(bot.confluence_set),
            "parameter_space": [_int_param()],
            "footprint": bot.footprint,
            "permitted_exit_intents": ("close_partial",),
            "logic_reference": bot.logic_reference,
        }
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "permitted_exit_intents"
    assert refused.context["journal"] is True


def test_entry_listed_as_exit_intent_is_invalid_input() -> None:
    fix = _fixture()
    bot = cast(BotDefinition, fix["declaration"])
    refused = lint_declaration(
        {
            "strategy_family_id": bot.strategy_family_id.value,
            "confluence_set": list(bot.confluence_set),
            "parameter_space": [_int_param()],
            "footprint": bot.footprint,
            "permitted_exit_intents": ("entry",),
            "logic_reference": bot.logic_reference,
        }
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


# --- AC: unknown format version; failures never swallowed --------------------


def test_unknown_contract_format_version_is_unsupported_capability() -> None:
    refused = lint_declaration({"contract_format_version": 2, "strategy_family_id": "x"})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refused.context["field"] == "contract_format_version"
    assert refused.context["given"] == 2
    assert refused.context["journal"] is True
    assert refused.context["layer"] == 1
    nested = lint_declaration({"body": {"contract_format_version": 99, "strategy_family_id": "x"}})
    assert is_refusal(nested)
    assert nested.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_unknown_format_version_wins_over_schema_incompleteness() -> None:
    refused = lint_declaration({"contract_format_version": 2})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_layer1_never_returns_policy_rejection() -> None:
    refusals = [
        lint_declaration({"contract_format_version": 2}),
        lint_declaration({"strategy_family_id": "trend-follow"}),
        _lint_fixture(_fixture(), family=None),
        _lint_fixture(_fixture(), logic=None),
    ]
    for refused in refusals:
        assert is_refusal(refused)
        assert refused.category is not RefusalCategory.POLICY_REJECTION


def test_layer1_is_pure_no_io_or_process() -> None:
    tree = ast.parse(_LAYER1.read_text(encoding="utf-8"), filename=str(_LAYER1))
    banned = frozenset(
        {
            "subprocess",
            "threading",
            "multiprocessing",
            "socket",
            "asyncio",
            "qmf.venue",
        }
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in banned
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module not in banned
            assert not node.module.startswith("qmf.venue")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "open"


def test_catalogs_accept_mapping_and_formula_index_shapes() -> None:
    fix = _fixture()
    confluence = cast(Confluence, fix["confluence"])
    fp = _ok(confluence.fingerprint_content()).value
    zone = cast(ProducerBinding, fix["zone"])
    verdict = _ok(
        lint_declaration(
            fix["declaration"],
            family_catalog={"trend-follow": fix["family"]},
            confluence_catalog={fp: confluence},
            producer_catalog={_ok(zone.fingerprint_content()).value: zone, "sma": fix["sma"]},
            formula_catalog=(),
            logic_catalog={"research-bot": fix["logic"]},
        )
    )
    assert isinstance(verdict, Layer1Verdict)
    bad_formula = lint_declaration(
        fix["declaration"],
        family_catalog=[fix["family"]],
        confluence_catalog=[confluence],
        producer_catalog=fix["producers"],
        formula_catalog="sma",
        logic_catalog=[fix["logic"]],
    )
    assert is_refusal(bad_formula)
    assert bad_formula.category is RefusalCategory.INVALID_INPUT


def test_public_export_surface() -> None:
    assert qml.lint_declaration is lint_declaration
    assert qml.LAYER1_CHECKS == LAYER1_CHECKS
    assert qml.Layer1Verdict is Layer1Verdict
