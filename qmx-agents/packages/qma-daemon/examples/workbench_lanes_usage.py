"""L27 reference usage: coordinated placement keeps two workbench_lane labels."""

from __future__ import annotations

from qma.core.content import content_address
from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.experiments import ExperimentSpec
from qma.core.ports.qmb import QMB_BACKTEST_TOOL_ID
from qma.core.vocabulary.enums import ExecutionEnvironmentKind
from qma.daemon.backtest import BacktestingService, RecordingQmbDoorTransport
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.experiments import ExperimentSpecService
from qma.daemon.taskgraph.records import DispatchLease
from qma.daemon.tools import ToolRegistry
from qmf.core import is_ok, is_refusal


def _fp(label: str) -> str:
    addressed = content_address({"label": label})
    assert is_ok(addressed)
    return addressed.value.value


def main() -> None:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    lease = DispatchLease(
        task_id="task-exp-1",
        holder_agent_id="agent-analyst-1",
        mission_id="mission-exp",
        owner=minted.value,
    )
    spec = ExperimentSpec.try_create(
        data_ref="data:eurusd",
        environment_ref="env:docker",
        seed=4,
        model_and_harness_version={"model": "analyst-v1", "harness": "qmb-1"},
        cost_assumptions={"spread_usd_cents": 10},
        resolved_config_ref=_fp("cfg-a"),
    )
    assert is_ok(spec)
    experiments = ExperimentSpecService()
    registered = experiments.register(
        spec.value,
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
    )
    assert is_ok(registered)
    envs = ExecutionEnvironmentRegistry()
    assert is_ok(
        envs.register_declaration(
            ExecutionEnvironmentDeclaration.isolated(
                ExecutionEnvironmentKind.DOCKER,
                provider_ref="local-docker",
            )
        )
    )
    service = BacktestingService(
        jobs=JobHandleService(),
        environments=envs,
        tools=ToolRegistry(),
        transport=RecordingQmbDoorTransport(),
        experiments=experiments,
    )
    assert is_ok(service.install())
    flagged = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=minted.value,
        task_id="task-flag",
        environment_ref="env:docker",
        experiment_spec_fp1=registered.value.spec.spec_fp1,
        evidence_ref="evidence:recorded-bars",
        workbench_lane="coordinated",
    )
    assert is_refusal(flagged)
    placed = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=minted.value,
        task_id="task-ok",
        environment_ref="env:docker",
        experiment_spec_fp1=registered.value.spec.spec_fp1,
        evidence_ref="evidence:recorded-bars",
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
        qmb_ledger_ref="qmb-ledger:run-1",
        ct32_ref=_fp("ct32-run"),
    )
    assert is_ok(placed)
    payload = placed.value.to_payload()
    assert payload["qmb_ledger_workbench_lane"] == "governed"
    assert payload["experiment_ledger_workbench_lane"] == "coordinated"
    assert "workbench_lane" not in payload
    ledger = experiments.resolve_ledger(registered.value.spec.spec_fp1)
    assert is_ok(ledger)
    assert ledger.value.entries[-1].body["workbench_lane"] == "coordinated"
    print("workbench lanes ok")
    print("qmb ledger workbench_lane=governed")
    print("experiment ledger workbench_lane=coordinated")


if __name__ == "__main__":
    main()
