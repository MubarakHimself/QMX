"""Hypotheses stay on ``qml.research``; optional librarian; tab-close (Story 52.3).

Stage 0 hypotheses are not federated Library hits. They are found through the
QML research surface listing (Epic 50). An optional librarian is a QMA Skill /
Graph Template over ``search`` / ``retrieve`` / ``cite`` plus Stage 0 helpers —
never a compulsory wizard. Tab-close cancels nothing. json-render / MCP Apps,
if later used, present DTOs only; GAP-0081 stays deferred (FR-RES-16; UX-DR2;
UX-DR4; UX-DR7; NFR-RES-07; DEC-0390; AD-10; AD-12).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qma.core.control.primitives import ControlPrimitive, Skill
from qma.core.control.procedures import (
    REFUSED_WIZARD_SEQUENCE,
    refuse_linear_wizard,
)
from qma.core.ports.cancel_authority import (
    CLIENT_DETACH_EVENTS,
    ClientDetachEvent,
    client_detach_writes_terminal,
    is_client_detach_event,
    parse_client_detach_event,
)
from qma.wire.federated_discovery import (
    FEDERATED_HIT_CLASSES,
    viewing_cited_seed_mints_research_ref,
)
from qmf.core import Ok, Result, is_refusal
from qmf.core.refusal import TypedRefusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "GAP_0081_UI_CONTRACT",
    "HYPOTHESES_ARE_FEDERATED_HITS",
    "HYPOTHESIS_LISTING_SURFACE",
    "JSON_RENDER_EXECUTES",
    "JSON_RENDER_STORES",
    "LIBRARIAN_CONTROL_PRIMITIVES",
    "LIBRARIAN_IS_REQUIRED",
    "LIBRARIAN_IS_WIZARD",
    "LIBRARIAN_KNOWLEDGE_PORTS",
    "LIBRARIAN_PLUGIN_ID",
    "LIBRARIAN_SKILL_ID",
    "LIBRARIAN_SKILL_LOCAL_ID",
    "LIBRARIAN_STAGE0_HELPERS",
    "MCP_APPS_EXECUTES",
    "MCP_APPS_STORES",
    "PRESENTATION_CANDIDATES",
    "REFUSED_HYPOTHESIS_KIND_TOKENS",
    "LibrarianContribution",
    "federated_in_flight_on_tab_close",
    "hypotheses_are_federated_hits",
    "hypothesis_listing_surface",
    "optional_librarian_graph_template",
    "optional_librarian_skill",
    "presentation_candidates_identity",
    "refuse_federated_hypothesis_kwargs",
    "refuse_hypothesis_as_federated_hit",
    "refuse_hypothesis_kind_on_federated_search",
    "refuse_research_to_bot_wizard",
    "viewing_cited_seed_mints_research_ref",
]


HYPOTHESIS_LISTING_SURFACE: Final[str] = "qml.research"
HYPOTHESES_ARE_FEDERATED_HITS: Final[bool] = False

LIBRARIAN_PLUGIN_ID: Final[str] = "research-corpus"
LIBRARIAN_SKILL_LOCAL_ID: Final[str] = "librarian"
LIBRARIAN_SKILL_ID: Final[str] = f"{LIBRARIAN_PLUGIN_ID}:{LIBRARIAN_SKILL_LOCAL_ID}"
LIBRARIAN_IS_REQUIRED: Final[bool] = False
LIBRARIAN_IS_WIZARD: Final[bool] = False
LIBRARIAN_KNOWLEDGE_PORTS: Final[tuple[str, ...]] = ("search", "retrieve", "cite")
LIBRARIAN_STAGE0_HELPERS: Final[tuple[str, ...]] = (
    "qml.research.project_layout_demo",
    "qml.research.resolve_dictionary_entry",
    "qml.research.compile_graph",
)
LIBRARIAN_CONTROL_PRIMITIVES: Final[tuple[str, ...]] = (
    ControlPrimitive.SKILL.value,
    ControlPrimitive.GRAPH_TEMPLATE.value,
)

JSON_RENDER_STORES: Final[bool] = False
JSON_RENDER_EXECUTES: Final[bool] = False
MCP_APPS_STORES: Final[bool] = False
MCP_APPS_EXECUTES: Final[bool] = False
PRESENTATION_CANDIDATES: Final[tuple[str, ...]] = ("json-render", "mcp-apps")
GAP_0081_UI_CONTRACT: Final[str] = "GAP-0081"

_HYPOTHESIS_HIT_FIELDS: Final[tuple[str, ...]] = (
    "hypothesis",
    "hypotheses",
    "research_candidate",
    "research_candidates",
    "qml_candidate",
    "stage0_hypothesis",
    "research_ref",
)

REFUSED_HYPOTHESIS_KIND_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "hypothesis",
        "entry_hypothesis",
        "entry-hypothesis",
        "qml-research-hypothesis",
        "qml_research_hypothesis",
        "research_candidate",
        "research-candidate",
        "research candidate",
    }
)


def hypotheses_are_federated_hits() -> bool:
    """Stage 0 hypotheses are never KnowledgeHit / ArtifactHit rows."""
    return HYPOTHESES_ARE_FEDERATED_HITS


def hypothesis_listing_surface() -> str:
    """Hypotheses are listed on ``qml.research`` (Epic 50), not Library search."""
    return HYPOTHESIS_LISTING_SURFACE


def refuse_hypothesis_as_federated_hit(**extra: object) -> TypedRefusal:
    """Refuse federating Stage 0 drafts onto the Library discovery DTO."""
    field = str(extra.pop("field", "hypothesis"))
    return policy_rejection(
        field,
        "Stage 0 hypotheses are not federated Library hits; they are found "
        "through the qml.research listing surface, never as KnowledgeHit or "
        "ArtifactHit (AD-9; DEC-0389; FR-RES-07; Story 52.3)",
        listing_surface=HYPOTHESIS_LISTING_SURFACE,
        federated_hit_classes=sorted(FEDERATED_HIT_CLASSES),
        hypotheses_are_federated_hits=False,
        decision="DEC-0389",
        **extra,
    )


def refuse_hypothesis_kind_on_federated_search(**extra: object) -> TypedRefusal:
    """Refuse Artifact ``kind`` tokens that name Stage 0 / mill identity."""
    return refuse_hypothesis_as_federated_hit(field="kind", **extra)


def refuse_research_to_bot_wizard(**extra: object) -> TypedRefusal:
    """No compulsory research-to-bot wizard (FR-RES-16; UX-DR7; DEC-0390)."""
    given = extra.pop("given", "research-to-bot-wizard")
    refused = refuse_linear_wizard(given=given)
    context = dict(refused.context)
    context.update(
        {
            "decision": "DEC-0390",
            "librarian_required": LIBRARIAN_IS_REQUIRED,
            "librarian_is_wizard": LIBRARIAN_IS_WIZARD,
            "sequence": list(REFUSED_WIZARD_SEQUENCE),
            **extra,
        }
    )
    return TypedRefusal(
        category=refused.category,
        retryability=refused.retryability,
        context=context,
    )


@dataclass(frozen=True, slots=True)
class LibrarianContribution:
    """Optional librarian as Skill or Graph Template over existing ports."""

    qualified_id: str
    control_primitive: str
    knowledge_ports: tuple[str, ...] = LIBRARIAN_KNOWLEDGE_PORTS
    stage0_helpers: tuple[str, ...] = LIBRARIAN_STAGE0_HELPERS
    required: bool = False
    is_wizard: bool = False
    stores: bool = False
    executes: bool = False

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "control_primitive": self.control_primitive,
                "executes": self.executes,
                "is_wizard": self.is_wizard,
                "knowledge_ports": list(self.knowledge_ports),
                "qualified_id": self.qualified_id,
                "required": self.required,
                "stage0_helpers": list(self.stage0_helpers),
                "stores": self.stores,
            }
        )


def optional_librarian_skill(
    *,
    version: str = "1",
    summary: str = (
        "Optional contextual librarian over search/retrieve/cite plus "
        "qml.research Stage 0 helpers"
    ),
) -> Skill:
    """Build the optional librarian Skill (FR-RES-16; UX-DR7; DEC-0390)."""
    body = (
        "Ports: search, retrieve, cite. Stage 0 helpers live on qml.research. "
        "Not required. Not a research-to-bot wizard. Tab-close cancels nothing."
    )
    return Skill(
        qualified_id=LIBRARIAN_SKILL_ID,
        version=version,
        summary=summary,
        body=body,
        disclosures=LIBRARIAN_KNOWLEDGE_PORTS + LIBRARIAN_STAGE0_HELPERS,
    )


def optional_librarian_graph_template(
    *,
    local_id: str = LIBRARIAN_SKILL_LOCAL_ID,
) -> LibrarianContribution:
    """Optional librarian as a Graph Template over the same ports."""
    return LibrarianContribution(
        qualified_id=f"{LIBRARIAN_PLUGIN_ID}:{local_id}",
        control_primitive=ControlPrimitive.GRAPH_TEMPLATE.value,
        knowledge_ports=LIBRARIAN_KNOWLEDGE_PORTS,
        stage0_helpers=LIBRARIAN_STAGE0_HELPERS,
        required=False,
        is_wizard=False,
        stores=False,
        executes=False,
    )


def federated_in_flight_on_tab_close(
    event: ClientDetachEvent | str = ClientDetachEvent.TAB_CLOSE,
) -> Result[Mapping[str, object]]:
    """Tab-close during federated search / librarian cancels nothing (NFR-RES-07)."""
    parsed = parse_client_detach_event(event)
    if is_refusal(parsed):
        if not is_client_detach_event(event):
            return invalid_input(
                "event",
                "federated search / librarian tab-close admits only client-detach "
                "events; JobHandle.cancel is the sole coordinated cancel "
                "(NFR-RES-07; UX-DR4; DEC-0390)",
                given=repr(event),
                legal=sorted(CLIENT_DETACH_EVENTS),
            )
        return parsed
    return Ok(
        MappingProxyType(
            {
                "cancels_federated_search": False,
                "cancels_librarian": False,
                "event": parsed.value.value,
                "invokes_job_handle_cancel": False,
                "sets_cancelled": False,
                "writes_terminal": client_detach_writes_terminal(),
            }
        )
    )


def presentation_candidates_identity() -> Mapping[str, object]:
    """json-render / MCP Apps present DTOs; they do not store or execute."""
    return MappingProxyType(
        {
            "candidates": list(PRESENTATION_CANDIDATES),
            "gap_0081": GAP_0081_UI_CONTRACT,
            "json_render_executes": JSON_RENDER_EXECUTES,
            "json_render_stores": JSON_RENDER_STORES,
            "mcp_apps_executes": MCP_APPS_EXECUTES,
            "mcp_apps_stores": MCP_APPS_STORES,
            "qma_ui_contract": "stub",
            "ui_contribution_deferred": True,
        }
    )


def refuse_federated_hypothesis_kwargs(
    values: Mapping[str, object | None],
) -> TypedRefusal | None:
    """Refuse search kwargs that try to fold Stage 0 drafts into Library hits."""
    for name in _HYPOTHESIS_HIT_FIELDS:
        if values.get(name) is not None:
            return refuse_hypothesis_as_federated_hit(field=name, given=name)
    return None
