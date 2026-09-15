"""Story 36.4 — coordinated placement keeps two honest workbench_lane labels."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.content import content_address
from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.experiments import (
    EXPERIMENT_LEDGER_WORKBENCH_LANE,
    QMB_LEDGER_WORKBENCH_LANE,
    ExperimentSpec,
)
from qma.core.ports.qmb import QMB_BACKTEST_TOOL_ID
from qma.core.vocabulary.enums import ExecutionEnvironmentKind
from qma.daemon.backtest import BacktestingService, RecordingQmbDoorTransport
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.experiments import ExperimentSpecService
from qma.daemon.process import DaemonProcess
from qma.daemon.taskgraph.records import DispatchLease
from qma.daemon.tools import ToolRegistry
from qmf.core import is_ok, is_refusal


def _fp(label: str) -> str:
    addressed = content_address({"label": label})
    assert is_ok(addressed)
    return addressed.value.value


def _owner() -> ActorId:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    return minted.value


def _lease(*, task_id: str = "task-exp-36-4") -> DispatchLease:
    return DispatchLease(
        task_id=task_id,
        holder_agent_id="agent-analyst-1",
        mission_id="mission-exp",
        owner=_owner(),
    )


def _spec() -> ExperimentSpec:
    created = ExperimentSpec.try_create(
        data_ref="data:eurusd",
        environment_ref="env:docker",
        seed=36,
        model_and_harness_version={"model": "analyst-v1", "harness": "qmb-1"},
        cost_assumptions={"spread_usd_cents": 10},
        resolved_config_ref=_fp("cfg-36-4"),
    )
    assert is_ok(created)
    return created.value


def _envs() -> ExecutionEnvironmentRegistry:
    registry = ExecutionEnvironmentRegistry()
    assert is_ok(
        registry.register_declaration(
            ExecutionEnvironmentDeclaration.isolated(
                ExecutionEnvironmentKind.DOCKER,
                provider_ref="local-docker",
            )
        )
    )
    return registry


def test_placement_exposes_two_labels_not_one_field() -> None:
    service = BacktestingService(
        tools=ToolRegistry(),
        jobs=JobHandleService(),
        environments=_envs(),
        transport=RecordingQmbDoorTransport(),
    )
    assert is_ok(service.install())
    placed = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=_owner(),
        task_id="task-lane-1",
        environment_ref="env:docker",
        experiment_spec_fp1=_fp("unregistered"),
        evidence_ref="evidence:recorded-bars",
    )
    assert is_ok(placed)
    payload = placed.value.to_payload()
    assert payload["qmb_ledger_workbench_lane"] == QMB_LEDGER_WORKBENCH_LANE
    assert payload["experiment_ledger_workbench_lane"] == EXPERIMENT_LEDGER_WORKBENCH_LANE
    assert payload["qmb_ledger_workbench_lane"] != payload["experiment_ledger_workbench_lane"]
    assert "workbench_lane" not in payload
    labels = payload["labels"]
    assert isinstance(labels, dict)
    assert labels["qmb_ledger_workbench_lane"] == "governed"
    assert labels["experiment_ledger_workbench_lane"] == "coordinated"
    flagged = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=_owner(),
        task_id="task-lane-flag",
        environment_ref="env:local",
        experiment_spec_fp1=_fp("unregistered-2"),
        evidence_ref="evidence:recorded-bars",
        workbench_lane="coordinated",
    )
    assert is_refusal(flagged)
    extra = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=_owner(),
        task_id="task-lane-extra",
        environment_ref="env:local",
        experiment_spec_fp1=_fp("unregistered-3"),
        evidence_ref="evidence:recorded-bars",
        extra={"lane": "governed"},
    )
    assert is_refusal(extra)


def test_registered_spec_records_coordinated_ledger_and_governed_qmb_label(
    tmp_path: Path,
) -> None:
    experiments = ExperimentSpecService()
    lease = _lease()
    registered = experiments.register(
        _spec(),
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
    )
    assert is_ok(registered)
    spec_fp1 = registered.value.spec.spec_fp1
    service = BacktestingService(
        tools=ToolRegistry(),
        jobs=JobHandleService(),
        environments=_envs(),
        transport=RecordingQmbDoorTransport(),
        experiments=experiments,
    )
    assert is_ok(service.install())
    unknown = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=_owner(),
        task_id="task-unknown-spec",
        environment_ref="env:docker",
        experiment_spec_fp1=_fp("missing-spec"),
        evidence_ref="evidence:recorded-bars",
    )
    assert is_refusal(unknown)
    placed = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=_owner(),
        task_id="task-coord-1",
        environment_ref="env:docker",
        experiment_spec_fp1=spec_fp1,
        evidence_ref="evidence:recorded-bars",
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
        qmb_ledger_ref="qmb-ledger:run-36-4",
        ct32_ref=_fp("ct32-36-4"),
    )
    assert is_ok(placed)
    assert placed.value.qmb_ledger_workbench_lane == "governed"
    assert placed.value.experiment_ledger_workbench_lane == "coordinated"
    ledger = experiments.resolve_ledger(spec_fp1)
    assert is_ok(ledger)
    assert ledger.value.entries
    body = dict(ledger.value.entries[-1].body)
    assert body["workbench_lane"] == "coordinated"
    assert body["qmb_ledger_ref"] == "qmb-ledger:run-36-4"
    assert body["ct32_ref"] == _fp("ct32-36-4")
    assert "ct32" not in body
    assert "jsonl" not in body
    collapsed = experiments.record_coordinated_run(
        spec_fp1=spec_fp1,
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
        workbench_lane="governed",
    )
    assert is_refusal(collapsed)

    process = DaemonProcess.compose(
        tmp_path,
        machine="test-host",
        boot_epoch_id="boot-36-4",
        bind_port=0,
    )
    assert is_ok(process)
    composed = process.value
    try:
        assert composed.backtesting.experiments is composed.experiments
    finally:
        composed.close()


def test_reference_usage_example_runs() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "workbench_lanes_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()
