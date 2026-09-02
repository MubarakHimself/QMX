"""L27 reference usage: Agent → QMA backtest tool → Backtesting Service → qmb door."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.qmb import QMB_BACKTEST_TOOL_ID, QMB_ROUTE
from qma.core.vocabulary.enums import ExecutionEnvironmentKind, JobHandleState
from qma.daemon.backtest import BacktestingService, RecordingQmbDoorTransport
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.envs.jobs import JobHandleService
from qmf.core import is_ok, is_refusal


def main() -> None:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    envs = ExecutionEnvironmentRegistry()
    assert is_ok(
        envs.register_declaration(
            ExecutionEnvironmentDeclaration.isolated(
                ExecutionEnvironmentKind.DOCKER,
                provider_ref="local-docker",
            )
        )
    )
    assert is_ok(
        envs.register_declaration(
            ExecutionEnvironmentDeclaration.isolated(
                ExecutionEnvironmentKind.LOCAL,
                provider_ref="local-host",
            )
        )
    )
    transport = RecordingQmbDoorTransport()
    service = BacktestingService(
        jobs=JobHandleService(),
        environments=envs,
        transport=transport,
    )
    installed = service.install()
    assert is_ok(installed)
    assert installed.value.tool_id == QMB_BACKTEST_TOOL_ID
    first = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=minted.value,
        task_id="task-bt-1",
        environment_ref="env:docker",
        experiment_spec_fp1="fp1:sha256:" + ("a" * 64),
        evidence_ref="evidence:recorded-bars",
    )
    assert is_ok(first)
    assert first.value.route == QMB_ROUTE
    assert first.value.invocation.import_edge is False
    assert service.jobs.router.lease_for("task-bt-1") is None
    second = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=minted.value,
        task_id="task-bt-2",
        environment_ref="env:docker",
        experiment_spec_fp1="fp1:sha256:" + ("b" * 64),
        evidence_ref="evidence:recorded-bars",
    )
    assert is_refusal(second)
    other = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=minted.value,
        task_id="task-bt-3",
        environment_ref="env:local",
        experiment_spec_fp1="fp1:sha256:" + ("c" * 64),
        evidence_ref="evidence:recorded-bars",
    )
    assert is_ok(other)
    assert is_ok(service.observe_outcome(first.value.handle.job_id, JobHandleState.DONE))
    retry = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=minted.value,
        task_id="task-bt-4",
        environment_ref="env:docker",
        experiment_spec_fp1="fp1:sha256:" + ("d" * 64),
        evidence_ref="evidence:recorded-bars",
    )
    assert is_ok(retry)
    assert is_refusal(service.set_parallelism(4))
    assert is_refusal(service.import_qmb_package())
    paper = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=minted.value,
        task_id="task-bt-paper",
        environment_ref="env:docker",
        experiment_spec_fp1="fp1:sha256:" + ("e" * 64),
        evidence_ref="evidence:recorded-bars",
        world="paper",
    )
    assert is_refusal(paper)


if __name__ == "__main__":
    main()
