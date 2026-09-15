"""Closed first-party desk plugin pack roster (FR-Q71; FEAT-0046; CT-42).

Definitions only. Pack authors import contribution types from ``qma-core``
and declare them on ``PluginManifest``. The daemon loader activates those
declarations through ``PluginContext`` — never a daemon-private path.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from qma.core.ontology.desks import DESK_PREFIX_TOKENS
from qma.core.plugins.manifest import ManifestError, require_desk_prefix_plugin_id
from qma.core.ports.qmb import ANALYSIS_BACKTEST_PLUGIN_ID, QMB_OWNED_CONCERNS

__all__ = [
    "ANALYSIS_BACKTEST_PLUGIN_ID",
    "DESK_PLUGIN_PACK_DESKS",
    "DESK_PLUGIN_PACK_IDS",
    "MEMORY_CANDIDATES_ARE_ADMITTED",
    "PACK_ENTRYPOINT",
    "PROMOTE_IS_HUMAN_OUTSIDE_QMA",
    "QMB_OWNED_CONCERNS",
    "REFINEMENT_PROPOSALS_ARE_APPLIED",
    "analysis_procedure_graph_payload",
    "analysis_procedure_skill_payload",
    "graph_template_payload",
    "require_desk_plugin_pack_id",
    "skill_payload",
]


# Spine structural seed — five first-party desk packs (DEC-0320, DEC-0337).
DESK_PLUGIN_PACK_IDS: Final[tuple[str, ...]] = (
    "research-corpus",
    "analysis-backtest",
    "dev-factory",
    "trading-readonly",
    "pm-coordination",
)

DESK_PLUGIN_PACK_DESKS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "research-corpus": "research",
        "analysis-backtest": "analysis",
        "dev-factory": "dev",
        "trading-readonly": "trading",
        "pm-coordination": "pm",
    }
)

# Relative to the pack root; loaded by the daemon, never imported from daemon.
PACK_ENTRYPOINT: Final[str] = "daemon.plugin:activate"

# DEC-0345 verbs: admit memory, apply refinements, promote stays human/outside.
MEMORY_CANDIDATES_ARE_ADMITTED: Final[bool] = True
REFINEMENT_PROPOSALS_ARE_APPLIED: Final[bool] = True
PROMOTE_IS_HUMAN_OUTSIDE_QMA: Final[bool] = True


def require_desk_plugin_pack_id(plugin_id: str) -> str:
    """Accept only a named first-party desk pack id using its desk prefix."""
    desk = DESK_PLUGIN_PACK_DESKS.get(plugin_id)
    if desk is None:
        raise ManifestError(
            f"plugin id {plugin_id!r} is not one of the five desk packs "
            f"{list(DESK_PLUGIN_PACK_IDS)}"
        )
    if desk not in DESK_PREFIX_TOKENS:
        raise ManifestError(f"desk {desk!r} is not a desk prefix token")
    return require_desk_prefix_plugin_id(plugin_id, desk)


def graph_template_payload(
    plugin_id: str,
    local_id: str,
    *,
    version: str = "0.1.0",
    nodes: tuple[Mapping[str, object], ...] = (),
    edges: tuple[Mapping[str, object], ...] = (),
) -> dict[str, object]:
    """Authored, versioned, stateless Graph Template mapping (AD-13)."""
    require_desk_plugin_pack_id(plugin_id)
    return {
        "qualified_id": f"{plugin_id}:{local_id}",
        "version": version,
        "artifact_kind": "graph_template",
        "stateless": True,
        "runtime_state": None,
        "composition": "non_linear",
        "is_experiment_spec": False,
        "nodes": [dict(node) for node in nodes],
        "edges": [dict(edge) for edge in edges],
    }


def skill_payload(
    plugin_id: str,
    local_id: str,
    *,
    summary: str,
    version: str = "0.1.0",
    body: str = "",
) -> dict[str, object]:
    """Skill contribution mapping — knowledge only, never a capability grant."""
    require_desk_plugin_pack_id(plugin_id)
    return {
        "qualified_id": f"{plugin_id}:{local_id}",
        "version": version,
        "summary": summary,
        "body": body,
        "control_primitive": "skill",
        "is_loop": False,
        "grants_capability": False,
        "composition": "non_linear",
        "is_experiment_spec": False,
    }


def analysis_procedure_graph_payload() -> dict[str, object]:
    """analysis-backtest Graph Template: QMB door steps, any may be first."""
    from qma.core.control.procedures import (  # noqa: PLC0415
        ANALYSIS_PROCEDURE_LOCAL_ID,
        QMB_PROCEDURE_DOOR_STEPS,
    )

    return graph_template_payload(
        ANALYSIS_BACKTEST_PLUGIN_ID,
        ANALYSIS_PROCEDURE_LOCAL_ID,
        nodes=tuple(dict(node) for node in QMB_PROCEDURE_DOOR_STEPS),
        edges=(),
    )


def analysis_procedure_skill_payload() -> dict[str, object]:
    """analysis-backtest Skill: reusable door-step knowledge, never a wizard."""
    from qma.core.control.procedures import ANALYSIS_PROCEDURE_SKILL_LOCAL_ID  # noqa: PLC0415

    return skill_payload(
        ANALYSIS_BACKTEST_PLUGIN_ID,
        ANALYSIS_PROCEDURE_SKILL_LOCAL_ID,
        summary="Reusable QMB door steps as a Skill, never a QMB workflow",
        body="Any door step may be the first placement. Run-steps occupy the "
        "CT-47 qmb door. Query-steps call Epic 35/33 door queries and consume "
        "no occupancy. The procedure is not an ExperimentSpec. QMB does not "
        "grow a task graph.",
    )
