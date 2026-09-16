"""Story 51.1 — mill graduation passes originating_research_ref = research_ref only."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar, cast

from qmf.core.chrono import CalendarIdentity, WriterId
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import EdgeType, LineageEdge
from qml.conformance import (
    MILL_ORIGINATING_BANNED_KEYS,
    MILL_RESEARCH_CLASS,
    PROMOTED_FROM_EDGE_TYPE,
    Graduation,
    admit_mill_originating_research_ref,
    gate_registration,
    graduate_mill_to_governed,
    graduate_to_governed,
    lint_declaration,
    refuse_spawn_as_graduation,
    run_layer2_suite,
)
from qml.declaration import BotDefinition, mint_bot_definition, mint_confluence
from qml.families import mint_strategy_family
from qml.footprint import ProducerBinding, mint_footprint
from qml.host import (
    MILL_PROMOTED_FROM_IS_GOVERNED_EVIDENCE,
    MILL_PROMOTED_FROM_IS_LINEAGE,
    refuse_research_ref_as_governed_evidence,
    stamp_promoted_from_edge,
)
from qml.logic import mint_logic_identity
from qml.protocol import PROTOCOL_FORMAT_VERSION, FunctionFactory, mint_state_scope
from qml.research import (
    DictionaryCite,
    Hypothesis,
    fingerprint_hypothesis,
    mint_hypothesis,
    save_hypothesis,
)

import qml

T = TypeVar("T")

_SOURCE: dict[str, str] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}
_REGISTRATION = (
    Path(__file__).resolve().parents[1] / "src" / "qml" / "conformance" / "registration.py"
)
_OS = "windows-11"
_AR = "none"
_BOUND = 256


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _pinned(tag: str) -> ProducerBinding:
    fp = _ok(fingerprint({"class": "test-producer", "tag": tag}))
    return _ok(ProducerBinding.try_create(fp))


def _calendar() -> CalendarIdentity:
    return _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))


def _world() -> dict[str, object]:
    zone = _pinned("zone")
    sma = _pinned("sma")
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
            [_calendar()],
            [zone, sma],
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
        "producers": [zone, sma],
    }


def _layer1(world: dict[str, object]):
    return lint_declaration(
        declaration=world["declaration"],
        family_catalog=[world["family"]],
        confluence_catalog=[world["confluence"]],
        producer_catalog=world["producers"],
        logic_catalog=[world["logic"]],
    )


def _layer2(world: dict[str, object]):
    declaration = cast(BotDefinition, world["declaration"])
    scope = _ok(
        mint_state_scope(
            os=_OS,
            logic_identity=declaration.logic_reference,
            protocol_format_version=PROTOCOL_FORMAT_VERSION,
            arithmetic_reference_build=_AR,
        )
    )
    return run_layer2_suite(
        declaration=declaration,
        factory=FunctionFactory(logic=lambda evidence: ()),
        source_tree=_SOURCE,
        state_scope=scope,
        state_bound=_BOUND,
    )


def _hypothesis() -> Hypothesis:
    cite = DictionaryCite("dictionary/a.md", "swing-high")
    return _ok(
        mint_hypothesis(
            hypothesis_class="entry_hypothesis",
            origin="idea",
            dictionary_cites=[cite],
            title="mill graduate",
        )
    )


def test_mill_graduation_uses_research_ref_and_calls_graduate_to_governed() -> None:
    world = _world()
    hyp = _hypothesis()
    research_ref = _ok(fingerprint_hypothesis(hyp))
    assert research_ref.value.startswith("fp1:sha256:")

    graduated = _ok(
        graduate_mill_to_governed(
            layer1=_layer1(world),
            layer2=_layer2(world),
            hypothesis=hyp,
            originating_research_ref=research_ref,
        )
    )
    assert isinstance(graduated, Graduation)
    assert graduated.originating_research_ref == research_ref
    assert graduated.promoted_from_edge.edge_type == PROMOTED_FROM_EDGE_TYPE
    assert graduated.promoted_from_edge.to_ref == research_ref
    assert graduated.promoted_from_edge.from_ref == graduated.candidate.fingerprint

    # Same path with SavedHypothesis / omitted originating_research_ref.
    saved = _ok(save_hypothesis(hyp))
    via_saved = _ok(
        graduate_mill_to_governed(
            layer1=_layer1(world),
            layer2=_layer2(world),
            hypothesis=saved,
        )
    )
    assert via_saved.originating_research_ref == research_ref
    assert MILL_RESEARCH_CLASS == "qml-research-hypothesis"
    assert qml.graduate_mill_to_governed is graduate_mill_to_governed


def test_mill_refuses_citation_digest_artifact_source_and_seed_cite() -> None:
    hyp = _hypothesis()
    for banned in (
        {"source_ref": "src", "snapshot_ref": "snap", "locator": "loc"},
        {"artifact_ref": "art://1", "digest": "abc"},
        {"seed_cite": {"source_ref": "s", "snapshot_ref": "p", "locator": "l"}},
    ):
        refused = admit_mill_originating_research_ref(banned, hypothesis=hyp)
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
        assert refused.context["field"] == "originating_research_ref"

    class _Citation:
        source_ref = "src"
        artifact_ref = "art"
        snapshot_ref = "snap"
        locator = "loc"

    refused_obj = admit_mill_originating_research_ref(_Citation(), hypothesis=hyp)
    assert is_refusal(refused_obj)
    assert frozenset({"artifact_ref", "seed_cite", "source_ref"}) == MILL_ORIGINATING_BANNED_KEYS

    world = _world()
    refused_grad = graduate_mill_to_governed(
        layer1=_layer1(world),
        layer2=_layer2(world),
        hypothesis=hyp,
        originating_research_ref={"source_ref": "src", "artifact_ref": "art"},
    )
    assert is_refusal(refused_grad)


def test_host_stamps_promoted_from_lineage_not_governed_evidence() -> None:
    world = _world()
    hyp = _hypothesis()
    graduated = _ok(
        graduate_mill_to_governed(
            layer1=_layer1(world),
            layer2=_layer2(world),
            hypothesis=hyp,
        )
    )
    writer = _ok(WriterId.try_create("host", "authoring", "bot-definition", "boot-1"))
    stamped = _ok(stamp_promoted_from_edge(graduation=graduated, writer=writer))
    assert isinstance(stamped, LineageEdge)
    assert stamped.edge_type is EdgeType.PROMOTED_FROM
    assert stamped.to_ref == graduated.originating_research_ref
    assert stamped.from_ref == graduated.candidate.fingerprint
    assert MILL_PROMOTED_FROM_IS_LINEAGE is True
    assert MILL_PROMOTED_FROM_IS_GOVERNED_EVIDENCE is False

    refused = refuse_research_ref_as_governed_evidence(
        research_ref=graduated.originating_research_ref,
        candidate=graduated.candidate,
    )
    assert is_refusal(refused)
    assert refused.context["is_lineage"] is True
    assert refused.context["is_governed_evidence"] is False

    # Self-edge remains refused on the mill path.
    looped = graduate_mill_to_governed(
        layer1=_layer1(world),
        layer2=_layer2(world),
        hypothesis=hyp,
        originating_research_ref=graduated.candidate.fingerprint,
    )
    assert is_refusal(looped)


def test_parent_ungoverned_experiment_graduation_keeps_research_preimage_class() -> None:
    """Do not break parent QL-8 tests that fingerprint {"class": "research"}."""
    world = _world()
    research = _ok(fingerprint({"class": "research"}))
    graduated = _ok(
        graduate_to_governed(
            layer1=_layer1(world),
            layer2=_layer2(world),
            originating_research_ref=research,
        )
    )
    assert graduated.originating_research_ref == research
    # Mill path refuses a mismatched non-hypothesis fingerprint.
    hyp = _hypothesis()
    refused = graduate_mill_to_governed(
        layer1=_layer1(world),
        layer2=_layer2(world),
        hypothesis=hyp,
        originating_research_ref=research,
    )
    assert is_refusal(refused)
    assert refused.context["research_class"] == MILL_RESEARCH_CLASS


def test_spawn_governed_is_not_graduation_and_structure_helper_not_called() -> None:
    refused = refuse_spawn_as_graduation("spawn_governed")
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["spawn_governed"] is False
    mill_calls = refused.context["mill_calls"]
    assert isinstance(mill_calls, str)
    assert "graduate_to_governed" in mill_calls

    world = _world()
    hyp = _hypothesis()
    with_spawn = graduate_mill_to_governed(
        layer1=_layer1(world),
        layer2=_layer2(world),
        hypothesis=hyp,
        spawn_governed=True,
    )
    assert is_refusal(with_spawn)

    tree = ast.parse(_REGISTRATION.read_text(encoding="utf-8"), filename=str(_REGISTRATION))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("qmf.structure")
            assert node.module != "qmf.structure.research"
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("qmf.structure")

    # gate_registration without Stage 0 still works (skip-Stage-0 remains legal).
    candidate = _ok(gate_registration(layer1=_layer1(world), layer2=_layer2(world)))
    assert candidate.fingerprint.value.startswith("fp1:sha256:")
