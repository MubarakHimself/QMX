"""Reference usage — hypotheses on qml.research; optional librarian (Story 52.3)."""

from __future__ import annotations

from qma.daemon.discovery import (
    GAP_0081_UI_CONTRACT,
    federated_in_flight_on_tab_close,
    hypotheses_are_federated_hits,
    hypothesis_listing_surface,
    optional_librarian_skill,
    presentation_candidates_identity,
    refuse_hypothesis_as_federated_hit,
    refuse_research_to_bot_wizard,
    viewing_cited_seed_mints_research_ref,
)
from qma.wire import resolve_knowledge_hit_display_alias
from qmf.core import is_ok, is_refusal


def main() -> None:
    assert hypotheses_are_federated_hits() is False
    assert hypothesis_listing_surface() == "qml.research"
    assert viewing_cited_seed_mints_research_ref() is False
    print("Stage 0 hypotheses list on qml.research; not Library hits")

    alias = resolve_knowledge_hit_display_alias("seed cite")
    assert is_ok(alias)
    banned = resolve_knowledge_hit_display_alias("hypothesis")
    assert is_refusal(banned)
    print("KnowledgeHit display aliases never say hypothesis / research candidate")

    skill = optional_librarian_skill()
    assert skill.qualified_id == "research-corpus:librarian"
    assert skill.is_loop is False
    assert is_refusal(refuse_research_to_bot_wizard())
    assert is_refusal(refuse_hypothesis_as_federated_hit())
    print(f"optional librarian skill={skill.qualified_id}; not a wizard")

    closed = federated_in_flight_on_tab_close("tab_close")
    assert is_ok(closed)
    assert closed.value["cancels_federated_search"] is False
    assert closed.value["cancels_librarian"] is False
    print("tab-close cancels nothing while federated search / librarian is in flight")

    presentation = presentation_candidates_identity()
    assert presentation["json_render_stores"] is False
    assert presentation["mcp_apps_executes"] is False
    assert presentation["gap_0081"] == GAP_0081_UI_CONTRACT
    print("json-render / MCP Apps present DTOs only; GAP-0081 stays")


if __name__ == "__main__":
    main()
