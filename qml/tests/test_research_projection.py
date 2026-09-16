"""Story 49.6 — read-only LAYOUT-DEMO projection preserves entry_hypothesis and F."""

from __future__ import annotations

import ast
import inspect
import sys
from collections.abc import Mapping
from dataclasses import fields
from pathlib import Path
from typing import TypeVar, cast

import pytest
from qmb.registryread.library import register_library_kind
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qml.conformance import admit_ungoverned_tunnel
from qml.research import (
    F_SLOTS,
    GRAPH_PLANE,
    LAYOUT_DEMO_PACKAGE_ID,
    POPULATION_INGEST_STARTED,
    PRODUCT_NOUNS,
    LayoutDemoProjection,
    compile_graph,
    complete_unresolved_f,
    mint_bot_from_projection,
    project_layout_demo,
    save_hypothesis,
    start_population_ingest,
)

from qml import research

_TESTS_DIR = str(Path(__file__).resolve().parent)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from research_vocab_helpers import (  # noqa: E402
    FIXTURE_SEED,
    read_contained,
    read_contained_bytes,
)

T = TypeVar("T")

STRAT_DIR = "strategies/STRAT-000001-asian-high-london-reversal"
IDENTITY_PATH = f"{STRAT_DIR}/identity.md"
GRAPH_PATH = f"{STRAT_DIR}/logic/graph.yaml"
F_PATH = f"{STRAT_DIR}/specification/invalidation-exits-and-management.md"
README_PATH = f"{STRAT_DIR}/README.md"
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
        "yaml",
        "qmb",
        "qmf.registry",
        "qmf.venue",
        "qml.declaration",
        "qml.declaration.bot",
        "qml.declaration.confluence",
        "qml.footprint",
        "qml.host",
    }
)
_INVENTED_KEYS = frozenset(
    {
        "research_ref",
        "stop_price",
        "take_profit",
        "take_profits",
        "close_reason",
        "confluence",
        "sides",
        "short",
        "protective_stop_fill",
        "target_fill",
    }
)
_CT29 = (
    "protective_stop_fill",
    "target_fill",
    "protection_amendment_fill",
    "bot_intent",
    "hold_time_force_flat",
    "boundary_flat",
    "window_forced_flat",
    "protection_forced_flat",
    "kill_line_flat",
    "venue_liquidation",
    "venue_initiated_close",
    "operator_close",
)


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _cited(relative: str) -> bytes:
    src = FIXTURE_SEED / relative
    if not src.is_file():
        pytest.fail(
            "AR-RES-10 requires fixtures/research-seed bytes copied from the "
            f"operator Stats tree — missing {relative}"
        )
    return read_contained_bytes(src, contain_within=FIXTURE_SEED)


def _cited_package() -> dict[str, bytes]:
    return {
        IDENTITY_PATH: _cited(IDENTITY_PATH),
        GRAPH_PATH: _cited(GRAPH_PATH),
        F_PATH: _cited(F_PATH),
        README_PATH: _cited(README_PATH),
    }


def _demo_view() -> LayoutDemoProjection:
    return _ok(project_layout_demo(_cited_package()))


def _payload_graph(
    view: LayoutDemoProjection,
) -> tuple[dict[str, object], dict[str, object]]:
    payload = dict(view.to_payload())
    graph = payload["graph"]
    assert isinstance(graph, dict)
    return payload, cast("dict[str, object]", graph)


def _import_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
        return [node.module]
    return []


def _is_open_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open"


def _name_is_banned(name: str, banned: frozenset[str]) -> bool:
    return name in banned or any(name.startswith(item + ".") for item in banned)


def _node_ban_hits(path: Path, node: ast.AST, banned: frozenset[str]) -> list[str]:
    if _is_open_call(node):
        return [f"{path}: open()"]
    return [
        f"{path}: imports {name}" for name in _import_names(node) if _name_is_banned(name, banned)
    ]


def _file_ban_violations(path: Path, banned: frozenset[str]) -> list[str]:
    tree = ast.parse(
        read_contained(path, contain_within=_QML_RESEARCH),
        filename=str(path),
    )
    found: list[str] = []
    for node in ast.walk(tree):
        found.extend(_node_ban_hits(path, node, banned))
    return found


def _research_ban_violations(banned: frozenset[str]) -> list[str]:
    found: list[str] = []
    for path in sorted(_QML_RESEARCH.rglob("*.py")):
        found.extend(_file_ban_violations(path, banned))
    return found


def _assert_absent_from_maps(
    maps: tuple[Mapping[str, object], ...],
    keys: frozenset[str],
) -> None:
    union_keys = set[str]().union(*(mapping.keys() for mapping in maps))
    assert keys.isdisjoint(union_keys)


def test_layout_demo_projection_preserves_entry_hypothesis_and_unresolved_f() -> None:
    view = _demo_view()
    assert isinstance(view, LayoutDemoProjection)
    assert view.package_id == LAYOUT_DEMO_PACKAGE_ID == "STRAT-000001"
    assert view.hypothesis_class == "entry_hypothesis"
    assert view.read_only is True
    assert tuple(view.f_labels) == F_SLOTS
    assert all(view.f_labels[slot] == "unresolved" for slot in F_SLOTS)
    payload = dict(view.to_payload())
    assert payload["class"] == "entry_hypothesis"
    assert payload["f_labels"] == dict.fromkeys(F_SLOTS, "unresolved")
    assert payload["read_only"] is True
    assert payload["direction"] == "long"
    assert payload["market"] == "forex"
    assert "futures" not in payload.values()


def test_projection_does_not_invent_exits_short_side_or_ct29() -> None:
    view = _demo_view()
    payload, graph = _payload_graph(view)
    _assert_absent_from_maps((payload, graph, view.f_labels), _INVENTED_KEYS)
    for reason in _CT29:
        assert reason not in payload
        assert reason not in graph
        assert reason not in view.f_labels.values()
    assert payload["direction"] == "long"
    assert payload.get("sides") is None
    refused = complete_unresolved_f(view)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["invented_exits"] is False
    assert refused.context["short_side"] is False
    assert refused.context["close_reason"] is None
    assert "stop" in str(refused.context["reason"])
    assert "CT-29" in str(refused.context["reason"])


def test_projection_does_not_return_research_ref_and_view_is_not_a_save() -> None:
    view = _demo_view()
    payload = dict(view.to_payload())
    names = {item.name for item in fields(LayoutDemoProjection)}
    assert "research_ref" not in names
    assert "research_ref" not in payload
    assert not hasattr(research, "research_ref")
    assert not hasattr(research, "mint_research_ref")
    saved = save_hypothesis(view)
    assert is_refusal(saved)
    assert saved.category is RefusalCategory.POLICY_REJECTION
    assert saved.context["field"] == "research_ref"
    assert saved.context["research_ref"] is None
    assert saved.context["read_only"] is True
    assert "not a save" in str(saved.context["reason"])


def _assert_compile_target_refused(view: LayoutDemoProjection, target: str) -> None:
    refused = compile_graph(view, into=target)
    assert is_refusal(refused), target
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "graph"
    assert refused.context["into"] == target
    assert refused.context["plane"] == "hypothesis"
    assert "run_slice" in str(refused.context["reason"])


def test_all_then_stay_on_hypothesis_graph_compile_to_run_slice_refused() -> None:
    view = _demo_view()
    _payload, graph = _payload_graph(view)
    assert "ALL" in view.graph_operators
    assert "THEN" in view.graph_operators
    assert graph["operators"] == list(view.graph_operators)
    assert graph["plane"] == GRAPH_PLANE == "hypothesis"
    assert "confluence" not in graph
    assert "Confluence" not in graph
    for target in ("run_slice", "graph-template", "order-adapter"):
        _assert_compile_target_refused(view, target)


def test_register_library_kind_strats_still_refused_no_ct33_ct34_mint() -> None:
    view = _demo_view()
    refused_kind = register_library_kind("strats")
    assert is_refusal(refused_kind)
    assert refused_kind.category is RefusalCategory.POLICY_REJECTION
    assert refused_kind.context["is_library_kind"] is False
    assert refused_kind.context["writes_registry_kinds"] is False
    minted = mint_bot_from_projection(view)
    assert is_refusal(minted)
    assert minted.context["mints_ct33"] is False
    assert minted.context["mints_ct34"] is False
    source = inspect.getsource(project_layout_demo)
    assert "mint_bot_definition" not in source
    assert "mint_confluence" not in source
    assert "mint_ct06" not in source


def test_population_ingest_is_not_started() -> None:
    assert POPULATION_INGEST_STARTED is False
    refused = start_population_ingest("yt-dlp")
    assert is_refusal(refused)
    assert refused.context["started"] is False
    assert refused.context["source"] == "yt-dlp"
    text = "\n".join(
        read_contained(path, contain_within=_QML_RESEARCH) for path in _QML_RESEARCH.rglob("*.py")
    )
    for name in ("yt-dlp", "n8n", "YouTube", "Hermes"):
        assert f"import {name}" not in text
        assert f"from {name}" not in text


def test_product_nouns_are_research_hypothesis_dictionary_entry_seed_corpus() -> None:
    assert PRODUCT_NOUNS == (
        "research",
        "hypothesis",
        "dictionary entry",
        "seed corpus",
    )
    view = _demo_view()
    payload, graph = _payload_graph(view)
    assert graph["plane"] == "hypothesis"
    assert "confluence" not in payload
    assert "Confluence" not in research.__all__
    assert "confluence" not in research.__all__
    assert not hasattr(research, "Confluence")
    assert not hasattr(research, "confluence")
    assert "graph" in payload
    module_text = read_contained(_QML_RESEARCH / "projection.py", contain_within=_QML_RESEARCH)
    init_text = read_contained(_QML_RESEARCH / "__init__.py", contain_within=_QML_RESEARCH)
    assert "dictionary entry" in module_text or "seed corpus" in init_text
    assert "never Confluence" in module_text


def test_ungoverned_python_skips_stage0_tunnel_stays_legal() -> None:
    access = _ok(admit_ungoverned_tunnel())
    assert access.fp1_identity()["ticket_required"] is False
    assert access.fp1_identity()["tunnel_open"] is True
    signature = inspect.signature(admit_ungoverned_tunnel)
    assert "projection" not in signature.parameters
    assert "research_ref" not in signature.parameters


def test_projection_performs_no_filesystem_io_threads_or_process() -> None:
    source = inspect.getsource(project_layout_demo)
    assert "open(" not in source
    assert _research_ban_violations(_BANNED_IMPORTS) == []


def test_missing_layout_demo_and_non_bytes_are_typed_refusals() -> None:
    missing = project_layout_demo({"notes/liquidity.md": b"# not a seed package\n"})
    assert is_refusal(missing)
    assert missing.context["field"] == "cited_bytes"

    not_bytes = project_layout_demo(object())
    assert is_refusal(not_bytes)
    assert not_bytes.context["field"] == "cited_bytes"
    assert "filesystem" in str(not_bytes.context["reason"])

    empty = project_layout_demo({})
    assert is_refusal(empty)

    identity_only = _ok(project_layout_demo({IDENTITY_PATH: _cited(IDENTITY_PATH)}))
    assert identity_only.hypothesis_class == "entry_hypothesis"
    assert identity_only.f_labels["stop"] == "unresolved"
    assert "ALL" in identity_only.graph_operators
    assert "THEN" in identity_only.graph_operators
