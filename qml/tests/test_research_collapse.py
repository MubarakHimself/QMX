"""Story 51.2 — collapse open Stage 0 roles; refuse invented exits."""

from __future__ import annotations

from typing import TypeVar, cast

from qmf.core.chrono import CalendarIdentity
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qml.conformance import graduate_mill_to_governed, lint_declaration, run_layer2_suite
from qml.declaration import (
    FORBIDDEN_BOT_FIELDS,
    LEG_ROLES,
    BotDefinition,
    mint_bot_definition,
    mint_confluence,
)
from qml.families import mint_strategy_family
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity
from qml.protocol import PROTOCOL_FORMAT_VERSION, FunctionFactory, mint_state_scope
from qml.research import (
    CT34_LEG_ROLES,
    F_SLOTS,
    PYTHON_WHEN_REMAINDERS,
    STAGE0_CLASS_IS_CT33_FIELD,
    DictionaryCite,
    RoleBinding,
    collapse_stage0_roles,
    collapse_unresolved_f,
    mint_hypothesis,
    refuse_entry_hypothesis_as_ct33_field,
    refuse_invented_ct34_role,
    refuse_invented_exits,
)

T = TypeVar("T")

_SOURCE: dict[str, str] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _pinned(tag: str) -> ProducerBinding:
    return _ok(ProducerBinding.try_create(_ok(fingerprint({"class": "test-producer", "tag": tag}))))


def test_collapse_maps_open_roles_to_ct34_and_python_when() -> None:
    cite = DictionaryCite("dictionary/a.md", "swing-high")
    hyp = _ok(
        mint_hypothesis(
            hypothesis_class="entry_hypothesis",
            origin="seed_package",
            role_bindings=[
                RoleBinding(cite=cite, role="location"),
                RoleBinding(cite=cite, role="trigger"),
                RoleBinding(cite=cite, role="invalidation"),
                RoleBinding(cite=cite, role="confirmation"),
                RoleBinding(cite=cite, role="filter"),
            ],
            graph={"operators": ("ALL", "sequence", "within"), "meaning": ("boolean", "temporal")},
        )
    )
    collapsed = _ok(collapse_stage0_roles(hyp))
    assert collapsed.ct34_roles == ("level", "trigger", "confirmation", "filter")
    assert "invalidation" in collapsed.python_when
    assert set(collapsed.ct34_roles) <= LEG_ROLES
    assert set(collapsed.ct34_roles) <= CT34_LEG_ROLES

    operators = _ok(collapse_stage0_roles(["ALL", "sequence", "within", "arming"]))
    assert operators.ct34_roles == ()
    assert set(operators.python_when) <= PYTHON_WHEN_REMAINDERS | {"arming"}
    assert "all" in operators.python_when
    assert "sequence" in operators.python_when
    assert "within" in operators.python_when

    invented = refuse_invented_ct34_role("invalidation")
    assert is_refusal(invented)
    assert invented.context["gap_0085"] is False


def test_unresolved_f_yields_empty_permitted_exit_intents() -> None:
    collapsed = _ok(collapse_unresolved_f(dict.fromkeys(F_SLOTS, "unresolved")))
    assert collapsed.permitted_exit_intents == ()
    assert collapsed.book_family_policy is True
    assert collapsed.invented_exits is False

    refused = collapse_unresolved_f(
        dict.fromkeys(F_SLOTS, "unresolved"),
        invent_exits=True,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["permitted_exit_intents"] == ()

    direct = refuse_invented_exits(invent_close_reasons=True)
    assert is_refusal(direct)
    assert direct.context["invented_close_reasons"] is True


def test_entry_hypothesis_is_stage0_taxonomy_not_ct33_field() -> None:
    assert STAGE0_CLASS_IS_CT33_FIELD is False
    refused = refuse_entry_hypothesis_as_ct33_field("entry_hypothesis")
    assert is_refusal(refused)
    assert refused.context["is_ct33_field"] is False
    assert "entry_hypothesis" in FORBIDDEN_BOT_FIELDS
    assert "hypothesis_class" in FORBIDDEN_BOT_FIELDS

    zone = _pinned("zone")
    family = _ok(mint_strategy_family("trend-follow"))
    confluence = _ok(mint_confluence([{"role": "level", "producer_binding": zone}]))
    footprint = _ok(
        mint_footprint(
            [
                {
                    "instrument_role": "primary",
                    "bar_specs": [{"kind": "time-interval", "seconds": 60}],
                    "stream_role": "trading",
                }
            ],
            [_ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))],
            [zone],
        )
    )
    logic = _ok(mint_logic_identity("research-bot", "1.0.0", _SOURCE))
    banned = mint_bot_definition(
        {
            "strategy_family_id": family.family_id.value,
            "confluence_set": [confluence],
            "parameter_space": [
                {
                    "name": "lookback",
                    "type": "exact integer",
                    "bounds": {"min": 1, "max": 200},
                    "step": 1,
                    "default": 20,
                    "unit_kind": UnitKind.COUNT,
                    "ui": "ui-editable",
                }
            ],
            "footprint": footprint,
            "permitted_exit_intents": (),
            "logic_reference": logic,
            "entry_hypothesis": "asian-high",
        }
    )
    assert is_refusal(banned)
    payload = _ok(
        mint_bot_definition(
            {
                "strategy_family_id": family.family_id.value,
                "confluence_set": [confluence],
                "parameter_space": [
                    {
                        "name": "lookback",
                        "type": "exact integer",
                        "bounds": {"min": 1, "max": 200},
                        "step": 1,
                        "default": 20,
                        "unit_kind": UnitKind.COUNT,
                        "ui": "ui-editable",
                    }
                ],
                "footprint": footprint,
                "permitted_exit_intents": (),
                "logic_reference": logic,
            }
        )
    ).identity_payload()
    body = payload["body"]
    assert "entry_hypothesis" not in payload
    assert isinstance(body, dict)
    assert "entry_hypothesis" not in body
    assert "hypothesis_class" not in body


def test_mill_graduation_refuses_invented_exits_flag() -> None:
    zone = _pinned("zone")
    family = _ok(mint_strategy_family("trend-follow"))
    confluence = _ok(mint_confluence([{"role": "level", "producer_binding": zone}]))
    footprint = _ok(
        mint_footprint(
            [
                {
                    "instrument_role": "primary",
                    "bar_specs": [{"kind": "time-interval", "seconds": 60}],
                    "stream_role": "trading",
                }
            ],
            [_ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))],
            [zone],
        )
    )
    logic = _ok(mint_logic_identity("research-bot", "1.0.0", _SOURCE))
    declaration = _ok(
        mint_bot_definition(
            {
                "strategy_family_id": family.family_id.value,
                "confluence_set": [confluence],
                "parameter_space": [
                    {
                        "name": "lookback",
                        "type": "exact integer",
                        "bounds": {"min": 1, "max": 200},
                        "step": 1,
                        "default": 20,
                        "unit_kind": UnitKind.COUNT,
                        "ui": "ui-editable",
                    }
                ],
                "footprint": footprint,
                "permitted_exit_intents": (),
                "logic_reference": logic,
            }
        )
    )
    world = {
        "declaration": declaration,
        "family": family,
        "confluence": confluence,
        "logic": logic,
        "producers": [zone],
    }
    layer1 = lint_declaration(
        declaration=world["declaration"],
        family_catalog=[world["family"]],
        confluence_catalog=[world["confluence"]],
        producer_catalog=world["producers"],
        logic_catalog=[world["logic"]],
    )
    decl = cast(BotDefinition, world["declaration"])
    layer2 = run_layer2_suite(
        declaration=decl,
        factory=FunctionFactory(logic=lambda evidence: ()),
        source_tree=_SOURCE,
        state_scope=_ok(
            mint_state_scope(
                os="windows-11",
                logic_identity=decl.logic_reference,
                protocol_format_version=PROTOCOL_FORMAT_VERSION,
                arithmetic_reference_build="none",
            )
        ),
        state_bound=256,
    )
    hyp = _ok(
        mint_hypothesis(
            hypothesis_class="entry_hypothesis",
            origin="idea",
            f_labels=dict.fromkeys(F_SLOTS, "unresolved"),
        )
    )
    refused = graduate_mill_to_governed(
        layer1=layer1,
        layer2=layer2,
        hypothesis=hyp,
        invent_exits=True,
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "permitted_exit_intents"
