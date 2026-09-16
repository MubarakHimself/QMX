"""Story 52.3 — hypotheses on qml.research; optional librarian; tab-close."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from qma.core.control import ControlPrimitive, is_skill_distinct_from_loop
from qma.daemon.discovery import (
    GAP_0081_UI_CONTRACT,
    HYPOTHESIS_LISTING_SURFACE,
    HYPOTHESES_ARE_FEDERATED_HITS,
    JSON_RENDER_EXECUTES,
    JSON_RENDER_STORES,
    LIBRARIAN_IS_REQUIRED,
    LIBRARIAN_IS_WIZARD,
    LIBRARIAN_KNOWLEDGE_PORTS,
    LIBRARIAN_SKILL_ID,
    LIBRARIAN_STAGE0_HELPERS,
    MCP_APPS_EXECUTES,
    MCP_APPS_STORES,
    FederatedDiscoveryService,
    federated_in_flight_on_tab_close,
    hypotheses_are_federated_hits,
    hypothesis_listing_surface,
    optional_librarian_graph_template,
    optional_librarian_skill,
    presentation_candidates_identity,
    refuse_hypothesis_as_federated_hit,
    refuse_research_to_bot_wizard,
    viewing_cited_seed_mints_research_ref,
)
from qma.daemon.hooks.registry import HookRegistry
from qma.daemon.knowledge import (
    KnowledgeService,
    KnowledgeSourceRegistry,
    PlainFileLibrarySource,
)
from qma.daemon.plugins.load_refusal import EXCLUDED_CONTRIBUTION_POINTS
from qma.wire import (
    ArtifactHit,
    KnowledgeHit,
    resolve_knowledge_hit_display_alias,
)
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.core.refusal import RefusalCategory


class _FakeArtifactPort:
    def search(
        self,
        *,
        kind: str | None = None,
        fp1: str | None = None,
        query: str | None = None,
    ) -> Result[Sequence[Mapping[str, object]]]:
        _ = (kind, fp1, query)
        return Ok(())


def _knowledge(tmp_path: Path) -> tuple[KnowledgeService, object]:
    root = tmp_path / "strats"
    root.mkdir()
    (root / "notes.md").write_text("swing-high near London\n", encoding="utf-8")
    registry = KnowledgeSourceRegistry()
    source = PlainFileLibrarySource(root_path=root, source_id="strats")
    assert is_ok(registry.bind("strats", source, plugin_id="research-strats"))
    service = KnowledgeService(registry, hooks=HookRegistry())
    snapped = service.snapshot("strats")
    assert is_ok(snapped)
    return service, snapped.value


def test_stage0_hypotheses_are_not_federated_hits(tmp_path: Path) -> None:
    assert hypotheses_are_federated_hits() is False
    assert HYPOTHESES_ARE_FEDERATED_HITS is False
    assert hypothesis_listing_surface() == "qml.research" == HYPOTHESIS_LISTING_SURFACE

    knowledge, snap = _knowledge(tmp_path)
    facade = FederatedDiscoveryService(knowledge=knowledge, artifacts=_FakeArtifactPort())

    found = facade.search("swing-high", source_id="strats", snapshot=snap)
    assert is_ok(found)
    assert all(isinstance(hit, (KnowledgeHit, ArtifactHit)) for hit in found.value.hits)
    assert not any(getattr(hit, "hit_class", None) == "hypothesis" for hit in found.value.hits)
    assert "research_ref" not in found.value.to_payload()

    refused = facade.search(
        "swing-high",
        source_id="strats",
        snapshot=snap,
        hypothesis={"class": "entry_hypothesis"},
    )
    assert is_refusal(refused)
    assert refused.context["listing_surface"] == "qml.research"
    assert refused.context["hypotheses_are_federated_hits"] is False

    candidate = facade.search(
        "swing-high",
        source_id="strats",
        snapshot=snap,
        research_candidate=True,
    )
    assert is_refusal(candidate)
    assert is_refusal(refuse_hypothesis_as_federated_hit())


def test_knowledge_hit_display_aliases_ban_hypothesis_nouns() -> None:
    allowed = resolve_knowledge_hit_display_alias("seed cite")
    assert is_ok(allowed)
    assert allowed.value == "seed cite"

    for banned in ("hypothesis", "research candidate", "research_candidate", "entry_hypothesis"):
        refused = resolve_knowledge_hit_display_alias(banned)
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
        assert refused.context["field"] == "display_alias"

    assert viewing_cited_seed_mints_research_ref() is False
    hit = KnowledgeHit.try_create(
        source_ref="strats",
        snapshot_ref="fp1:sha256:" + ("ab" * 32),
        locator="notes.md",
    )
    assert is_ok(hit)
    assert "research_ref" not in hit.value.to_payload()
    assert "hypothesis" not in hit.value.to_payload().values()


def test_optional_librarian_is_skill_not_wizard() -> None:
    skill = optional_librarian_skill()
    assert skill.qualified_id == LIBRARIAN_SKILL_ID
    assert skill.is_loop is False
    assert is_skill_distinct_from_loop(skill)
    assert LIBRARIAN_IS_REQUIRED is False
    assert LIBRARIAN_IS_WIZARD is False
    assert skill.to_payload()["control_primitive"] == ControlPrimitive.SKILL.value
    assert set(LIBRARIAN_KNOWLEDGE_PORTS) <= set(skill.disclosures)
    assert any(helper.startswith("qml.research.") for helper in LIBRARIAN_STAGE0_HELPERS)

    graph = optional_librarian_graph_template()
    assert graph.control_primitive == ControlPrimitive.GRAPH_TEMPLATE.value
    assert graph.required is False
    assert graph.is_wizard is False
    assert graph.stores is False
    assert graph.executes is False
    assert list(graph.knowledge_ports) == list(LIBRARIAN_KNOWLEDGE_PORTS)

    wizard = refuse_research_to_bot_wizard(given="research-to-bot-wizard")
    assert is_refusal(wizard)
    assert wizard.context["decision"] == "DEC-0390"
    assert wizard.context["librarian_required"] is False
    assert wizard.context["librarian_is_wizard"] is False


def test_tab_close_cancels_nothing_during_federated_or_librarian() -> None:
    closed = federated_in_flight_on_tab_close("tab_close")
    assert is_ok(closed)
    body = closed.value
    assert body["cancels_federated_search"] is False
    assert body["cancels_librarian"] is False
    assert body["invokes_job_handle_cancel"] is False
    assert body["sets_cancelled"] is False
    assert body["writes_terminal"] is False

    cancel = federated_in_flight_on_tab_close("JobHandle.cancel")
    assert is_refusal(cancel)


def test_json_render_and_mcp_apps_present_only_gap_0081_stays() -> None:
    identity = presentation_candidates_identity()
    assert identity["json_render_stores"] is False is JSON_RENDER_STORES
    assert identity["json_render_executes"] is False is JSON_RENDER_EXECUTES
    assert identity["mcp_apps_stores"] is False is MCP_APPS_STORES
    assert identity["mcp_apps_executes"] is False is MCP_APPS_EXECUTES
    assert identity["gap_0081"] == GAP_0081_UI_CONTRACT == "GAP-0081"
    assert identity["ui_contribution_deferred"] is True
    assert EXCLUDED_CONTRIBUTION_POINTS["ui_view"] == "GAP-0081"
