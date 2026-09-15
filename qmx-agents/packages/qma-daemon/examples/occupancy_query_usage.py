"""L27 reference usage: occupancy versus queries; cancel maps to QMB abort."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from qma.core.content import content_address
from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.experiments import ANALYSIS_PUBLISHED_KIND, ExperimentSpec
from qma.core.ports.qmb import QMB_BACKTEST_TOOL_ID, QMB_OCCUPANCY_QUERY
from qma.core.vocabulary.enums import ExecutionEnvironmentKind, JobHandleState
from qma.daemon.backtest import (
    BacktestingService,
    CliQmbDoorTransport,
    cli_qmb_test_double_argv0,
)
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.experiments import ExperimentSpecService
from qma.daemon.taskgraph.records import DispatchLease
from qma.wire.vocabulary import SEED_EVENT_COUNT, WIRE_EVENTS
from qmf.core import is_ok, is_refusal


def main() -> None:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    owner = minted.value
    envs = ExecutionEnvironmentRegistry()
    assert is_ok(
        envs.register_declaration(
            ExecutionEnvironmentDeclaration.isolated(
                ExecutionEnvironmentKind.DOCKER,
                provider_ref="local-docker",
            )
        )
    )
    addressed = content_address({"label": "cfg-36-5"})
    assert is_ok(addressed)
    spec = ExperimentSpec.try_create(
        data_ref="data:eurusd",
        environment_ref="env:docker",
        seed=5,
        model_and_harness_version={"model": "analyst-v1", "harness": "qmb-1"},
        cost_assumptions={"spread_usd_cents": 10},
        resolved_config_ref=addressed.value.value,
    )
    assert is_ok(spec)
    lease = DispatchLease(
        task_id="task-36-5",
        holder_agent_id="agent-analyst-1",
        mission_id="mission-exp",
        owner=owner,
    )
    experiments = ExperimentSpecService()
    registered = experiments.register(
        spec.value,
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
    )
    assert is_ok(registered)
    assert len(WIRE_EVENTS) == SEED_EVENT_COUNT
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        transport = CliQmbDoorTransport(
            argv0=cli_qmb_test_double_argv0(root / "qmb_double.py"),
            receipt_path=str(root / "receipt.json"),
            ledger_path=str(root / "aborted.json"),
            hang=True,
        )
        service = BacktestingService(
            jobs=JobHandleService(),
            environments=envs,
            transport=transport,
            experiments=experiments,
            artifact_root=root,
        )
        try:
            assert is_ok(service.install())
            query = service.place_query(
                "analysis.project",
                owner=owner,
                task_id="task-project",
                environment_ref="env:docker",
                persist_projection=True,
                experiment_spec_fp1=registered.value.spec.spec_fp1,
                dispatch_lease=lease,
                model_deployment_ref="deploy:analyst-v1",
            )
            assert is_ok(query)
            assert query.value.occupancy == QMB_OCCUPANCY_QUERY
            assert query.value.published is not None
            assert query.value.published.kind == ANALYSIS_PUBLISHED_KIND
            assert Path(query.value.published.json_path).is_file()
            run = service.invoke(
                QMB_BACKTEST_TOOL_ID,
                owner=owner,
                task_id="task-run",
                environment_ref="env:docker",
                experiment_spec_fp1=registered.value.spec.spec_fp1,
                evidence_ref="evidence:recorded-bars",
            )
            assert is_ok(run)
            child = service.admit_process_per_run_child(
                "docker",
                child_job_id="qmb:docker:child",
            )
            assert is_ok(child)
            assert service.occupying_job("docker") == run.value.handle.job_id
            assert is_ok(service.jobs.start(run.value.handle.job_id))
            cancelled = service.cancel(run.value.handle.job_id)
            assert is_ok(cancelled)
            assert cancelled.value.state is JobHandleState.CANCELLED
            aborted = json.loads((root / "aborted.json").read_text(encoding="utf-8"))
            assert aborted["state"] == "aborted"
            assert aborted["writer"] == "qmb"
            assert is_refusal(service.append_run_ledger({"role": "aborted"}, writer="daemon"))
            assert is_refusal(experiments.mint_query_successor())
            assert service.qmb_opened_daemon_sqlite() is False
        finally:
            transport.close()


if __name__ == "__main__":
    main()
