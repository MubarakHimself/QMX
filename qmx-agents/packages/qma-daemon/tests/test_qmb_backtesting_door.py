"""Story 45.8 — Backtesting Service and the single QMB door (FR-Q55)."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.qmb import (
    ANALYSIS_BACKTEST_PLUGIN_ID,
    QMB_BACKTEST_TOOL_ID,
    QMB_CLI_ARGV,
    QMB_CLI_PROGRAM,
    QMB_ROUTE,
    QMB_WORLD_REPLAY,
    QmbDoorKind,
)
from qma.core.ports.tools import ToolKind
from qma.core.refusals import NoEnvironment
from qma.core.vocabulary.enums import ExecutionEnvironmentKind, JobHandleState
from qma.daemon.backtest import BacktestingService, RecordingQmbDoorTransport
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.plugins import DaemonPluginContext
from qma.daemon.tools import ToolRegistry
from qmf.core import is_ok, is_refusal


def _owner() -> ActorId:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    return minted.value


def _envs(*kinds: ExecutionEnvironmentKind) -> ExecutionEnvironmentRegistry:
    registry = ExecutionEnvironmentRegistry()
    for kind in kinds:
        assert is_ok(
            registry.register_declaration(
                ExecutionEnvironmentDeclaration.isolated(
                    kind,
                    provider_ref=f"local-{kind.value}",
                )
            )
        )
    return registry


def _service(
    *kinds: ExecutionEnvironmentKind,
) -> tuple[BacktestingService, RecordingQmbDoorTransport]:
    if not kinds:
        kinds = (ExecutionEnvironmentKind.DOCKER,)
    envs = _envs(*kinds)
    jobs = JobHandleService()
    transport = RecordingQmbDoorTransport()
    tools = ToolRegistry()
    service = BacktestingService(
        tools=tools,
        jobs=jobs,
        environments=envs,
        transport=transport,
    )
    installed = service.install()
    assert is_ok(installed)
    return service, transport


def test_installs_one_analysis_backtest_tool_registry_entry() -> None:
    tools = ToolRegistry()
    ctx = DaemonPluginContext(ANALYSIS_BACKTEST_PLUGIN_ID)
    service = BacktestingService(tools=tools, environments=_envs(ExecutionEnvironmentKind.DOCKER))
    first = service.install(context=ctx)
    assert is_ok(first)
    assert first.value.tool_id == QMB_BACKTEST_TOOL_ID
    assert first.value.kind is ToolKind.BACKTEST
    again = service.install(context=ctx)
    assert is_ok(again)
    backtest = [tool for tool in tools.catalog() if tool.plugin_id == ANALYSIS_BACKTEST_PLUGIN_ID]
    assert len(backtest) == 1
    snap = ctx.snapshot()
    assert ("tool", QMB_BACKTEST_TOOL_ID) in snap["multis"]
    wrong = BacktestingService(tools=ToolRegistry()).install(
        context=DaemonPluginContext("research-corpus"),
    )
    assert is_refusal(wrong)


def test_route_is_agent_tool_service_door_qmb() -> None:
    service, transport = _service()
    assert service.plugin_id == ANALYSIS_BACKTEST_PLUGIN_ID
    assert service.tool_id == QMB_BACKTEST_TOOL_ID
    assert service.route == QMB_ROUTE
    placed = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=_owner(),
        task_id="task-bt-1",
        environment_ref="env:docker",
        experiment_spec_fp1="fp1:sha256:" + ("a" * 64),
        evidence_ref="evidence:recorded-bars",
    )
    assert is_ok(placed)
    payload = placed.value.to_payload()
    assert payload["route"] == list(QMB_ROUTE)
    assert payload["plugin_id"] == ANALYSIS_BACKTEST_PLUGIN_ID
    assert payload["tool_id"] == QMB_BACKTEST_TOOL_ID
    assert payload["world"] == QMB_WORLD_REPLAY
    assert payload["program"] == QMB_CLI_PROGRAM
    assert payload["argv"] == list(QMB_CLI_ARGV)
    assert payload["import_edge"] is False
    assert payload["compute_router_used"] is False
    assert payload["qma_re_specifies"] is False
    assert len(transport.invocations) == 1
    assert transport.invocations[0].kind is QmbDoorKind.CLI
    assert service.jobs.router.lease_for("task-bt-1") is None


def test_one_qmb_job_per_environment_further_job_refused() -> None:
    service, _transport = _service(ExecutionEnvironmentKind.DOCKER, ExecutionEnvironmentKind.LOCAL)
    owner = _owner()
    first = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=owner,
        task_id="task-bt-1",
        environment_ref="env:docker",
        experiment_spec_fp1="fp1:spec-1",
        evidence_ref="evidence:recorded-1",
    )
    assert is_ok(first)
    assert service.occupying_job("env:docker") == first.value.handle.job_id
    second = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=owner,
        task_id="task-bt-2",
        environment_ref="env:docker-analysis",
        experiment_spec_fp1="fp1:spec-2",
        evidence_ref="evidence:recorded-2",
    )
    assert is_refusal(second)
    assert second.context["field"] == "qmb_job"
    other = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=owner,
        task_id="task-bt-3",
        environment_ref="env:local",
        experiment_spec_fp1="fp1:spec-3",
        evidence_ref="evidence:recorded-3",
    )
    assert is_ok(other)
    completed = service.observe_outcome(first.value.handle.job_id, JobHandleState.DONE)
    assert is_ok(completed)
    assert service.occupying_job("docker") is None
    retry = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=owner,
        task_id="task-bt-4",
        environment_ref="env:docker",
        experiment_spec_fp1="fp1:spec-4",
        evidence_ref="evidence:recorded-4",
    )
    assert is_ok(retry)


def test_unbound_environment_and_wrong_tool_are_refused() -> None:
    service, _transport = _service(ExecutionEnvironmentKind.DOCKER)
    missing = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=_owner(),
        task_id="task-bt-x",
        environment_ref="env:desktop",
        experiment_spec_fp1="fp1:spec",
        evidence_ref="evidence:recorded",
    )
    assert is_refusal(missing)
    assert NoEnvironment.matches(missing)
    wrong_tool = service.invoke(
        "analysis-backtest:other",
        owner=_owner(),
        task_id="task-bt-y",
        environment_ref="env:docker",
        experiment_spec_fp1="fp1:spec",
        evidence_ref="evidence:recorded",
    )
    assert is_refusal(wrong_tool)


def test_venue_account_request_is_refused() -> None:
    service, transport = _service()
    refused = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=_owner(),
        task_id="task-bt-v",
        environment_ref="env:docker",
        experiment_spec_fp1="fp1:spec",
        evidence_ref="evidence:recorded",
        world="paper",
    )
    assert is_refusal(refused)
    account = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=_owner(),
        task_id="task-bt-a",
        environment_ref="env:docker",
        experiment_spec_fp1="fp1:spec",
        evidence_ref="evidence:recorded",
        extra={"account_id": "venue-acct"},
    )
    assert is_refusal(account)
    assert transport.invocations == ()


def test_service_holds_no_scheduling_parallelism_or_backtest_state() -> None:
    service, _transport = _service()
    assert service.scheduling_authority is None
    assert service.parallelism is None
    assert service.backtest_state is None
    assert is_refusal(service.set_parallelism(8))
    assert is_refusal(service.append_run_ledger({"line": 1}))
    assert is_refusal(service.store_artifact({"ct32": True}))
    assert is_refusal(service.import_qmb_package())
    owned = service.qmb_owned_concerns()
    assert "intra_node_parallelism" in owned
    assert "run_ledger" in owned
    assert "artifact_contract" in owned


def test_reference_usage_example_runs() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "qmb_door_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()
