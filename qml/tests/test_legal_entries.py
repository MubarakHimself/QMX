"""Story 51.4 — three legal entries, none a toll booth; no auto-mint."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from typing import TypeVar, cast

from qmf.core.chrono import CalendarIdentity
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qml.conformance import (
    LEGAL_AUTHORING_ENTRIES,
    admit_ungoverned_tunnel,
    enumerate_legal_authoring_entries,
    gate_registration,
    gate_registration_requires_stage0,
    graduate_mill_to_governed,
    lint_declaration,
    refuse_auto_mint,
    refuse_entry_toll_booth,
    run_layer2_suite,
)
from qml.declaration import BotDefinition, mint_bot_definition, mint_confluence
from qml.families import mint_strategy_family
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity
from qml.protocol import PROTOCOL_FORMAT_VERSION, FunctionFactory, mint_state_scope
from qml.research import DictionaryCite, mint_bot_from_projection, mint_hypothesis, save_hypothesis

import qml

T = TypeVar("T")

_SOURCE: dict[str, str] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}
_PLAIN = Path(__file__).resolve().parent / "plain_research_bot.py"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _pinned(tag: str) -> ProducerBinding:
    return _ok(ProducerBinding.try_create(_ok(fingerprint({"class": "test-producer", "tag": tag}))))


def _world() -> dict[str, object]:
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
    return {
        "declaration": declaration,
        "family": family,
        "confluence": confluence,
        "logic": logic,
        "producers": [zone],
    }


def _layers(world: dict[str, object]):
    declaration = cast(BotDefinition, world["declaration"])
    layer1 = lint_declaration(
        declaration=world["declaration"],
        family_catalog=[world["family"]],
        confluence_catalog=[world["confluence"]],
        producer_catalog=world["producers"],
        logic_catalog=[world["logic"]],
    )
    layer2 = run_layer2_suite(
        declaration=declaration,
        factory=FunctionFactory(logic=lambda evidence: ()),
        source_tree=_SOURCE,
        state_scope=_ok(
            mint_state_scope(
                os="windows-11",
                logic_identity=declaration.logic_reference,
                protocol_format_version=PROTOCOL_FORMAT_VERSION,
                arithmetic_reference_build="none",
            )
        ),
        state_bound=256,
    )
    return layer1, layer2


def test_three_legal_entries_none_a_toll_booth() -> None:
    roster = _ok(enumerate_legal_authoring_entries())
    assert roster.entries == LEGAL_AUTHORING_ENTRIES
    assert roster.entries == (
        "ungoverned-python",
        "gate_registration",
        "stage0-graduate",
    )
    assert roster.toll_booth is False
    assert roster.gate_registration_requires_stage0 is False
    assert roster.conformance_gates_tunnel_entry is False
    assert gate_registration_requires_stage0() is False
    payload = dict(roster.to_payload())
    assert payload["toll_booth"] is False

    refused = refuse_entry_toll_booth(
        required_entry="stage0-graduate",
        for_entry="gate_registration",
    )
    assert is_refusal(refused)
    assert refused.context["toll_booth"] is False
    assert qml.LEGAL_AUTHORING_ENTRIES == LEGAL_AUTHORING_ENTRIES


def test_gate_registration_works_without_stage0() -> None:
    world = _world()
    layer1, layer2 = _layers(world)
    candidate = _ok(gate_registration(layer1=layer1, layer2=layer2))
    assert candidate.fingerprint.value.startswith("fp1:sha256:")
    # No Stage 0 import required for this path — research_ref absent by design.
    assert not hasattr(candidate, "originating_research_ref")
    assert not hasattr(candidate, "research_ref")


def test_stage0_graduate_requires_hypothesis_research_ref() -> None:
    world = _world()
    layer1, layer2 = _layers(world)
    hyp = _ok(
        mint_hypothesis(
            hypothesis_class="entry_hypothesis",
            origin="idea",
            dictionary_cites=[DictionaryCite("dictionary/a.md", "swing-high")],
        )
    )
    saved = _ok(save_hypothesis(hyp))
    graduated = _ok(
        graduate_mill_to_governed(
            layer1=layer1,
            layer2=layer2,
            hypothesis=saved,
        )
    )
    assert graduated.originating_research_ref == saved.research_ref


def test_auto_mint_from_dna_graph_yaml_hypothesis_package_refused() -> None:
    for source in ("dna", "graph.yaml", "hypothesis_package", "layout-demo"):
        refused = refuse_auto_mint(source=source, target="ct-33")
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
        assert refused.context["mints_ct33"] is False
        assert refused.context["mints_ct34"] is False
    from qml.research import LayoutDemoProjection

    view = LayoutDemoProjection(
        package_id="STRAT-000001",
        hypothesis_class="entry_hypothesis",
        read_only=True,
    )
    projection_refuse = mint_bot_from_projection(view)
    assert is_refusal(projection_refuse)
    assert projection_refuse.context["mints_ct33"] is False


def test_ungoverned_python_zero_qml_imports_still_runs() -> None:
    access = _ok(admit_ungoverned_tunnel())
    assert access.fp1_identity()["tunnel_open"] is True
    assert access.fp1_identity()["ticket_required"] is False

    source = _PLAIN.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(_PLAIN))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("qml")
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("qml")

    spec = importlib.util.spec_from_file_location("plain_research_bot", _PLAIN)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    bot = module.PlainResearchBot()
    assert bot.on_instant(object()) == ()
