"""Story 48.4 — five desk plugin packs on the core contribution surface (FR-Q71)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from qma.core.barriers.reachability import forbidden_reach_token_in_contribution
from qma.core.plugins import (
    DESK_PLUGIN_PACK_DESKS,
    DESK_PLUGIN_PACK_IDS,
    MEMORY_CANDIDATES_ARE_ADMITTED,
    PACK_ENTRYPOINT,
    PROMOTE_IS_HUMAN_OUTSIDE_QMA,
    REFINEMENT_PROPOSALS_ARE_APPLIED,
    ManifestError,
    assert_no_daemon_import,
    graph_template_payload,
    parse_plugin_manifest,
    require_desk_plugin_pack_id,
)
from qma.core.ports.cardinality import Cardinality
from qma.core.ports.qmb import ANALYSIS_BACKTEST_PLUGIN_ID, QMB_OWNED_CONCERNS

AGENTS_ROOT = Path(__file__).resolve().parents[3]
PLUGINS_ROOT = AGENTS_ROOT / "plugins"
CORE_SRC = Path(__file__).resolve().parents[1] / "src" / "qma" / "core"


def test_roster_is_five_desk_prefix_packs() -> None:
    assert DESK_PLUGIN_PACK_IDS == (
        "research-corpus",
        "analysis-backtest",
        "dev-factory",
        "trading-readonly",
        "pm-coordination",
    )
    assert ANALYSIS_BACKTEST_PLUGIN_ID == "analysis-backtest"
    for plugin_id, desk in DESK_PLUGIN_PACK_DESKS.items():
        assert require_desk_plugin_pack_id(plugin_id) == plugin_id
        assert plugin_id.startswith(f"{desk}-")
    with pytest.raises(ManifestError, match="five desk packs"):
        require_desk_plugin_pack_id("research-other")


def test_pack_manifests_parse_through_plugin_manifest() -> None:
    for plugin_id in DESK_PLUGIN_PACK_IDS:
        raw = json.loads((PLUGINS_ROOT / plugin_id / "manifest.json").read_text(encoding="utf-8"))
        manifest = parse_plugin_manifest(raw)
        assert manifest.id == plugin_id
        assert manifest.desk == DESK_PLUGIN_PACK_DESKS[plugin_id]
        assert manifest.entrypoint == PACK_ENTRYPOINT
        assert manifest.dependencies == ()
        assert manifest.permissions == ()
        assert manifest.migrations == ()
        assert manifest.rollback is None
        assert manifest.contributions  # packs declare contributions, not a private path
        for decl in manifest.contributions:
            if decl.cardinality is Cardinality.SINGLETON:
                assert decl.scope_key is not None
            else:
                assert decl.local_id is not None
                assert ":" not in decl.local_id


def test_analysis_backtest_declares_qmb_tool_and_owns_none_of_qmb() -> None:
    raw = json.loads(
        (PLUGINS_ROOT / "analysis-backtest" / "manifest.json").read_text(encoding="utf-8")
    )
    manifest = parse_plugin_manifest(raw)
    points = {(decl.point, decl.local_id) for decl in manifest.contributions}
    assert ("tool", "qmb") in points
    assert "intra_node_parallelism" in QMB_OWNED_CONCERNS
    assert "run_ledger" in QMB_OWNED_CONCERNS
    assert "artifact_contract" in QMB_OWNED_CONCERNS


def test_dec0345_verbs_and_no_daemon_import_from_packs() -> None:
    assert MEMORY_CANDIDATES_ARE_ADMITTED is True
    assert REFINEMENT_PROPOSALS_ARE_APPLIED is True
    assert PROMOTE_IS_HUMAN_OUTSIDE_QMA is True
    assert_no_daemon_import(PLUGINS_ROOT)
    assert_no_daemon_import(CORE_SRC)


def test_contribution_reach_scan_hits_qmf_venue_image_only() -> None:
    assert forbidden_reach_token_in_contribution({"image": "qmf-venue:latest"}) is not None
    assert forbidden_reach_token_in_contribution({"name": "search", "acts": ("search",)}) is None
    assert forbidden_reach_token_in_contribution({"summary": "never mention a broker here"}) is None


def test_graph_template_payload_is_stateless() -> None:
    payload = graph_template_payload(
        "research-corpus",
        "survey",
        nodes=({"id": "a", "kind": "task"},),
        edges=(),
    )
    assert payload["stateless"] is True
    assert payload["runtime_state"] is None
    assert payload["artifact_kind"] == "graph_template"
