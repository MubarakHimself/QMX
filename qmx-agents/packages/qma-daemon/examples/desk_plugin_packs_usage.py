"""L27 reference usage: register the five desk plugin packs (FR-Q71)."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug
from qma.core.plugins import DESK_PLUGIN_PACK_IDS, assert_no_daemon_import
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.qmb import QMB_BACKTEST_TOOL_ID
from qma.core.vocabulary.enums import ExecutionEnvironmentKind, JobHandleState
from qma.daemon.plugins import DeskPluginRoster, default_plugins_root
from qmf.core import is_ok, is_refusal


def main() -> None:
    root = default_plugins_root()
    assert_no_daemon_import(root)
    roster = DeskPluginRoster(plugins_root=root)
    loaded = roster.activate()
    assert is_ok(loaded)
    assert tuple(roster.loader.loaded_ids()) == DESK_PLUGIN_PACK_IDS

    published = {row.qualified_id or row.point for row in roster.loader.published_contributions()}
    assert "research-corpus:search" in published
    assert "analysis-backtest:qmb" in published
    assert roster.backtesting.scheduling_authority is None
    assert roster.backtesting.parallelism is None
    assert is_refusal(roster.refuse_promote())

    docker = ExecutionEnvironmentDeclaration.isolated(
        ExecutionEnvironmentKind.DOCKER, provider_ref="local-docker"
    )
    assert is_ok(roster.backtesting.environments.register_declaration(docker))
    owner = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(owner)
    placed = roster.backtesting.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=owner.value,
        task_id="task-example-1",
        environment_ref="env:docker",
        experiment_spec_fp1="fp1:example",
        evidence_ref="evidence:recorded",
    )
    assert is_ok(placed)
    again = roster.backtesting.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=owner.value,
        task_id="task-example-2",
        environment_ref="env:docker",
        experiment_spec_fp1="fp1:example-2",
        evidence_ref="evidence:recorded-2",
    )
    assert is_refusal(again)
    assert is_ok(
        roster.backtesting.observe_outcome(placed.value.handle.job_id, JobHandleState.DONE)
    )


if __name__ == "__main__":
    main()
