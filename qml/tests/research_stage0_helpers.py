"""Shared helpers for qml.research Stage 0 tests."""

from __future__ import annotations

import ast
from pathlib import Path

from qmf.core.refusal import is_ok
from qml.research import (
    F_LABELS,
    F_SLOTS,
    GRAPH_MEANING_KINDS,
    GRAPH_PLANE,
    HYPOTHESIS_CLASSES,
    HYPOTHESIS_ORIGINS,
    STAGE0_SURFACES,
    DictionaryCite,
    EvidenceClaim,
    Graph,
    Hypothesis,
    mint_hypothesis,
)

_QML_RESEARCH = Path(__file__).resolve().parents[1] / "src" / "qml" / "research"

_BANNED_IMPORTS = frozenset(
    {
        "asyncio",
        "concurrent",
        "http",
        "multiprocessing",
        "os",
        "pathlib",
        "socket",
        "subprocess",
        "threading",
        "urllib",
        "qmf.registry",
        "qmf.venue",
        "qml.declaration",
        "qml.host",
    }
)


def assert_stage0_surface_constants() -> None:
    assert set(STAGE0_SURFACES) >= {
        "dictionary_cites",
        "role_bindings",
        "graph",
        "evidence",
        "unknowns",
        "f_labels",
        "h_labels",
        "class",
    }
    assert HYPOTHESIS_CLASSES == frozenset(
        {
            "entry_hypothesis",
            "fragment",
            "descriptive_pattern",
            "composite",
            "complete",
        }
    )
    assert HYPOTHESIS_ORIGINS == frozenset({"idea", "chart", "journal", "seed_package"})
    assert GRAPH_MEANING_KINDS == frozenset({"boolean", "temporal", "lifecycle"})
    assert GRAPH_PLANE == "hypothesis"
    assert F_SLOTS == ("invalidation", "stop", "targets", "exit", "management")
    assert F_LABELS == frozenset(
        {"source_defined", "external_policy", "deliberately_open", "unresolved"}
    )


def mint_idea_fragment() -> Hypothesis:
    idea = mint_hypothesis(
        hypothesis_class="fragment",
        origin="idea",
        dictionary_cites=[{"file_path": "notes/local.md", "id": "my-level"}],
        role_bindings=[
            {
                "cite": {"file_path": "notes/local.md", "id": "my-level"},
                "role": "location",
            }
        ],
        graph={
            "operators": ["ALL"],
            "meaning": ["boolean", "temporal"],
            "plane": "hypothesis",
        },
        evidence=[{"claim": "sketched on a whiteboard", "locator": None}],
        unknowns=("pair unresolved",),
        f_labels=dict.fromkeys(F_SLOTS, "unresolved"),
        h_labels={"pair": "unresolved"},
        title="whiteboard sketch",
    )
    assert is_ok(idea)
    return idea.value


def assert_idea_fragment(hyp: Hypothesis) -> None:
    assert isinstance(hyp, Hypothesis)
    assert hyp.origin == "idea"
    assert hyp.hypothesis_class == "fragment"
    assert hyp.dictionary_cites[0] == DictionaryCite("notes/local.md", "my-level")
    assert hyp.role_bindings[0].role == "location"
    assert isinstance(hyp.graph, Graph)
    assert hyp.graph.meaning == ("boolean", "temporal")
    assert hyp.evidence[0] == EvidenceClaim(claim="sketched on a whiteboard")
    assert "pair unresolved" in hyp.unknowns


def assert_source_agnostic_origins() -> None:
    for origin in ("chart", "journal", "seed_package"):
        minted = mint_hypothesis(hypothesis_class="entry_hypothesis", origin=origin)
        assert is_ok(minted), origin
        assert minted.value.origin == origin


def _import_is_banned(name: str) -> bool:
    if name in _BANNED_IMPORTS:
        return True
    return any(name.startswith(item + ".") for item in _BANNED_IMPORTS)


def _collect_import_hits(path: Path, tree: ast.AST) -> list[str]:
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _import_is_banned(alias.name):
                    hits.append(f"{path.name}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            if _import_is_banned(node.module):
                hits.append(f"{path.name}: from {node.module}")
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "open"
        ):
            hits.append(f"{path.name}: open()")
    return hits


def research_purity_violations() -> list[str]:
    hits: list[str] = []
    for path in sorted(_QML_RESEARCH.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        hits.extend(_collect_import_hits(path, tree))
    return hits
