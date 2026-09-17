"""Story 51.3 — origin stays qma; optional seed_cite is a distinct field."""

from __future__ import annotations

from typing import TypeVar, cast

from qmf.core.chrono import CalendarIdentity, WriterId
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qml.conformance import (
    gate_registration,
    graduate_mill_to_governed,
    lint_declaration,
    run_layer2_suite,
)
from qml.declaration import BotDefinition, mint_bot_definition, mint_confluence
from qml.families import mint_strategy_family
from qml.footprint import ProducerBinding, mint_footprint
from qml.host import (
    CANDIDATE_ORIGIN,
    QMA_INVENTS_SEED_CITE,
    SEED_CITE_IN_FP1,
    HostCandidate,
    SeedCite,
    admit_candidate_origin,
    attach_seed_cite,
    mint_host_candidate,
    refuse_ct07_to_knowledge_citation,
    refuse_qma_invented_seed_cite,
    stamp_promoted_from_edge,
)
from qml.logic import mint_logic_identity
from qml.protocol import PROTOCOL_FORMAT_VERSION, FunctionFactory, mint_state_scope
from qml.research import DictionaryCite, mint_hypothesis

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


def _candidate(world: dict[str, object]):
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
    return _ok(gate_registration(layer1=layer1, layer2=layer2))


def test_origin_is_frozen_qma_not_seed_locator() -> None:
    assert CANDIDATE_ORIGIN == "qma"
    assert _ok(admit_candidate_origin()) == "qma"
    assert _ok(admit_candidate_origin("qma")) == "qma"
    refused = admit_candidate_origin("strategies/STRAT-000001/identity.md")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["expected"] == "qma"
    refused_cite = admit_candidate_origin("seed_cite")
    assert is_refusal(refused_cite)


def test_seed_cite_is_distinct_and_outside_fp1() -> None:
    world = _world()
    candidate = _candidate(world)
    cite = {
        "source_ref": "research-corpus",
        "snapshot_ref": "snap-1",
        "locator": "strategies/STRAT-000001/identity.md",
    }
    hosted = _ok(mint_host_candidate(candidate=candidate, seed_cite=cite))
    assert isinstance(hosted, HostCandidate)
    assert hosted.origin == "qma"
    assert isinstance(hosted.seed_cite, SeedCite)
    assert hosted.seed_cite.source_ref == "research-corpus"
    assert hosted.mill_graduation is None
    assert hosted.promoted_from_edge is None
    assert SEED_CITE_IN_FP1 is False
    identity = hosted.fp1_identity()
    assert "seed_cite" not in identity
    assert "origin" not in identity
    decl = hosted.declaration_identity()
    body = decl["body"]
    assert "seed_cite" not in decl
    assert isinstance(body, dict)
    assert "seed_cite" not in body


def test_qma_never_invents_seed_cite_host_is_single_writer() -> None:
    assert QMA_INVENTS_SEED_CITE is False
    refused = refuse_qma_invented_seed_cite(invented_by="qma")
    assert is_refusal(refused)
    assert refused.context["qma_invents"] is False
    assert refused.context["host_is_single_writer"] is True


def test_no_ct07_edge_to_knowledge_citation() -> None:
    refused = refuse_ct07_to_knowledge_citation(
        to_ref="research-corpus",
        seed_cite={"source_ref": "s", "snapshot_ref": "p", "locator": "l"},
    )
    assert is_refusal(refused)
    assert refused.context["mill_edge_to_citation"] is False


def test_skip_stage0_may_set_seed_cite_without_mill_ct07() -> None:
    world = _world()
    candidate = _candidate(world)
    hosted = _ok(
        attach_seed_cite(
            candidate,
            seed_cite=SeedCite("src", "snap", "loc"),
        )
    )
    assert hosted.seed_cite is not None
    assert hosted.mill_graduation is None
    assert hosted.promoted_from_edge is None
    assert hosted.origin == "qma"


def test_mill_graduation_may_carry_seed_cite_with_research_ref_edge() -> None:
    world = _world()
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
    hyp = _ok(
        mint_hypothesis(
            hypothesis_class="entry_hypothesis",
            origin="idea",
            dictionary_cites=[DictionaryCite("dictionary/a.md", "swing-high")],
        )
    )
    graduated = _ok(graduate_mill_to_governed(layer1=layer1, layer2=layer2, hypothesis=hyp))
    writer = _ok(WriterId.try_create("host", "authoring", "bot-definition", "boot-1"))
    edge = _ok(stamp_promoted_from_edge(graduation=graduated, writer=writer))
    hosted = _ok(
        mint_host_candidate(
            candidate=graduated.candidate,
            seed_cite={"source_ref": "src", "snapshot_ref": "snap", "locator": "loc"},
            mill_graduation=graduated,
            promoted_from_edge=edge,
        )
    )
    assert hosted.seed_cite is not None
    assert hosted.promoted_from_edge is not None
    assert hosted.promoted_from_edge.to_ref == graduated.originating_research_ref
    assert "seed_cite" not in hosted.fp1_identity()
