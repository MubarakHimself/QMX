"""Story 50.1 — public qml.research Stage 0 types on QML's own format ladder."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import TypeVar

from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qml.conformance import CONFORMANCE_FORMAT_VERSION
from qml.protocol import PROTOCOL_FORMAT_VERSION
from qml.research import (
    F_SLOTS,
    RESEARCH_CONTRACT_CLASS,
    RESEARCH_FORMAT_VERSION,
    RESEARCH_LADDER,
    STAGE0_CITED_BY_GOVERNED_EVIDENCE,
    STAGE0_EMITS_CT23,
    STAGE0_IS_BOOK_SEAT,
    STAGE0_NEVER_SIZES,
    DictionaryCite,
    EvidenceClaim,
    Graph,
    RoleBinding,
    admit_research_format_version,
    mint_hypothesis,
    refuse_stage0_governed_citation,
    refuse_stage0_intent_emit,
    refuse_stage0_seat,
    refuse_stage0_sizing,
    research_contract_identity,
    restore_hypothesis,
)

from qml import research


def _load_research_stage0_helpers() -> ModuleType:
    path = Path(__file__).resolve().parent / "research_stage0_helpers.py"
    name = "qml.tests.research_stage0_helpers"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_helpers = _load_research_stage0_helpers()
assert_idea_fragment = _helpers.assert_idea_fragment
assert_source_agnostic_origins = _helpers.assert_source_agnostic_origins
assert_stage0_surface_constants = _helpers.assert_stage0_surface_constants
mint_idea_fragment = _helpers.mint_idea_fragment
research_purity_violations = _helpers.research_purity_violations

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def test_qml_research_is_public_submodule_with_own_format_ladder() -> None:
    assert RESEARCH_FORMAT_VERSION == 1
    assert isinstance(RESEARCH_FORMAT_VERSION, int)
    assert research.RESEARCH_FORMAT_VERSION is RESEARCH_FORMAT_VERSION
    assert not hasattr(research, "PROTOCOL_FORMAT_VERSION")
    assert not hasattr(research, "CONFORMANCE_FORMAT_VERSION")
    assert "PROTOCOL_FORMAT_VERSION" not in research.__all__
    assert "CONFORMANCE_FORMAT_VERSION" not in research.__all__
    assert RESEARCH_CONTRACT_CLASS == "qml-research-hypothesis"
    assert RESEARCH_LADDER == "qml-ad5-research"
    identity = research_contract_identity()
    assert identity["class"] == RESEARCH_CONTRACT_CLASS
    assert identity["contract_format_version"] == RESEARCH_FORMAT_VERSION
    assert identity["ladder"] == RESEARCH_LADDER
    # Ladder name is independent of QL-7 / QL-8 even when ordinals match.
    assert PROTOCOL_FORMAT_VERSION == 1
    assert CONFORMANCE_FORMAT_VERSION == 1
    assert RESEARCH_LADDER != "qml-ad5"
    assert "Confluence" not in research.__all__
    assert "confluence" not in research.__all__
    assert not hasattr(research, "Confluence")
    assert not hasattr(research, "confluence")


def test_stage0_types_cover_required_surfaces_and_source_agnostic_origins() -> None:
    assert_stage0_surface_constants()
    assert_idea_fragment(mint_idea_fragment())
    assert_source_agnostic_origins()


def test_stage0_never_sizes_intents_seats_or_governed_evidence() -> None:
    assert STAGE0_NEVER_SIZES is True
    assert STAGE0_EMITS_CT23 is False
    assert STAGE0_IS_BOOK_SEAT is False
    assert STAGE0_CITED_BY_GOVERNED_EVIDENCE is False
    sized = refuse_stage0_sizing()
    assert is_refusal(sized) and sized.category is RefusalCategory.POLICY_REJECTION
    assert sized.context["sizes"] is False
    intents = refuse_stage0_intent_emit()
    assert is_refusal(intents) and intents.context["emits_ct23"] is False
    seat = refuse_stage0_seat()
    assert is_refusal(seat) and seat.context["is_book_seat"] is False
    governed = refuse_stage0_governed_citation()
    assert is_refusal(governed) and governed.context["cited_by_governed_evidence"] is False


def test_graph_identifier_not_confluence_export() -> None:
    hyp = _ok(
        mint_hypothesis(
            hypothesis_class="composite",
            origin="journal",
            graph={"operators": ["sequence", "within"], "meaning": ["lifecycle"]},
        )
    )
    body = hyp.canonical_body()
    graph = body["graph"]
    assert "graph" in body
    assert "confluence" not in body
    assert isinstance(graph, dict)
    assert graph["plane"] == "hypothesis"
    refused = mint_hypothesis(
        hypothesis_class="fragment",
        origin="idea",
        graph={"confluence": [], "operators": []},
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "graph"


def test_unknown_research_format_version_is_unavailable_dependency() -> None:
    admitted = admit_research_format_version(RESEARCH_FORMAT_VERSION)
    assert is_ok(admitted)
    unknown = admit_research_format_version(RESEARCH_FORMAT_VERSION + 99)
    assert is_refusal(unknown)
    assert unknown.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert unknown.context["field"] == "contract_format_version"
    assert "version bump" in str(unknown.context["reason"])

    restored = restore_hypothesis(
        {
            "class": RESEARCH_CONTRACT_CLASS,
            "contract_format_version": RESEARCH_FORMAT_VERSION + 7,
            "body": {
                "class": "fragment",
                "origin": "idea",
                "dictionary_cites": [],
                "role_bindings": [],
                "graph": {"operators": [], "meaning": [], "plane": "hypothesis"},
                "evidence": [],
                "unknowns": [],
                "f_labels": {},
                "h_labels": {},
            },
        }
    )
    assert is_refusal(restored)
    assert restored.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_restore_round_trip_known_version() -> None:
    cite = DictionaryCite("dictionary/a.md", "swing-high")
    original = _ok(
        mint_hypothesis(
            hypothesis_class="entry_hypothesis",
            origin="seed_package",
            dictionary_cites=[cite],
            role_bindings=[RoleBinding(cite=cite, role="location")],
            graph=Graph(operators=("ALL", "THEN"), meaning=("boolean", "temporal")),
            evidence=[EvidenceClaim(claim="LAYOUT-DEMO sketch", locator="identity.md")],
            unknowns=("F unresolved",),
            f_labels=dict.fromkeys(F_SLOTS, "unresolved"),
            h_labels={"exits": "unresolved"},
            package_id="STRAT-000001",
            title="asian high london",
        )
    )
    envelope = {
        "class": RESEARCH_CONTRACT_CLASS,
        "contract_format_version": RESEARCH_FORMAT_VERSION,
        "body": original.canonical_body(),
    }
    restored = restore_hypothesis(envelope)
    assert is_ok(restored)
    assert restored.value.hypothesis_class == "entry_hypothesis"
    assert restored.value.origin == "seed_package"
    assert restored.value.package_id == "STRAT-000001"
    assert restored.value.canonical_body() == original.canonical_body()


def test_research_module_stays_pure_no_io_threads_process() -> None:
    assert research_purity_violations() == []
