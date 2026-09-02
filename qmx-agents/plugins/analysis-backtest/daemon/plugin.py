"""analysis-backtest daemon half — QMB door contribution surface (FR-Q71).

The Backtesting Service in ``qma-daemon`` is the runtime adapter behind this
pack. This module registers contributions through ``PluginContext`` from
``qma-core``. It never imports ``qma-daemon``, ``qmb``, or ``qmf-venue``.
"""

from __future__ import annotations

from qma.core.plugins import PluginContext, graph_template_payload, skill_payload
from qma.core.ports.qmb import (
    ANALYSIS_BACKTEST_PLUGIN_ID,
    QMB_BACKTEST_TOOL_LOCAL_ID,
    QMB_OWNED_CONCERNS,
    qmb_backtest_tool_record,
)


def activate(ctx: PluginContext) -> None:
    """Register the one QMB door tool plus authored analysis definitions."""
    record = qmb_backtest_tool_record()
    ctx.register_tool(
        QMB_BACKTEST_TOOL_LOCAL_ID,
        {
            "name": QMB_BACKTEST_TOOL_LOCAL_ID,
            "acts": tuple(sorted(record.acts)),
            "kind": record.kind.value,
            "tags": tuple(sorted(record.tags)),
            "schema": dict(record.schema),
            "scheduling_authority": None,
            "qmb_owned": sorted(QMB_OWNED_CONCERNS),
        },
    )
    ctx.register_skill(
        "replay",
        skill_payload(
            ANALYSIS_BACKTEST_PLUGIN_ID,
            "replay",
            summary="Place one qmb job per environment against recorded evidence",
            body="Replay only. QMB keeps parallelism, run ledger, and artifacts.",
        ),
    )
    ctx.register_graph_template(
        "notebook",
        graph_template_payload(
            ANALYSIS_BACKTEST_PLUGIN_ID,
            "notebook",
            nodes=(
                {"id": "prepare", "kind": "task"},
                {"id": "replay", "kind": "task"},
                {"id": "review", "kind": "task"},
            ),
            edges=(
                {"from": "prepare", "to": "replay"},
                {"from": "replay", "to": "review"},
            ),
        ),
    )
    ctx.register_toolset(
        "replay-tools",
        {
            "toolset_id": f"{ANALYSIS_BACKTEST_PLUGIN_ID}:replay-tools",
            "version": "0.1.0",
            "tool_ids": [f"{ANALYSIS_BACKTEST_PLUGIN_ID}:{QMB_BACKTEST_TOOL_LOCAL_ID}"],
        },
    )
