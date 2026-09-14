"""L27 reference usage: tab-close cancels nothing; JobHandle.cancel is authority."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.cancel_authority import UNAUTHORIZED_CANCEL_WRITERS
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.qmb import QMB_BACKTEST_TOOL_ID
from qma.core.refusals import UnauthorizedCancelWriter
from qma.core.vocabulary.enums import ExecutionEnvironmentKind, JobHandleState
from qma.daemon.backtest import BacktestingService, RecordingQmbDoorTransport
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.ledgers.experiment import ExperimentLedgerStore
from qma.wire.attach import ClientAttachmentState
from qmf.core import is_ok, is_refusal


def main() -> None:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    jobs = JobHandleService()
    submitted = jobs.submit(owner=minted.value, task_id="task-32-2")
    assert is_ok(submitted)
    assert is_ok(jobs.start(submitted.value.job_id))
    attachment = ClientAttachmentState(quant_work_active=True)
    closed = attachment.tab_close()
    assert is_ok(closed)
    assert closed.value.invokes_job_handle_cancel is False
    detached = jobs.on_client_detach(submitted.value.job_id, event="tab_close")
    assert is_ok(detached)
    assert detached.value.state is JobHandleState.RUNNING
    plugin = jobs.cancel(submitted.value.job_id, writer="plugin")
    assert is_refusal(plugin)
    assert UnauthorizedCancelWriter.matches(plugin)
    assert UNAUTHORIZED_CANCEL_WRITERS
    cancelled = jobs.cancel(submitted.value.job_id)
    assert is_ok(cancelled)
    assert cancelled.value.state is JobHandleState.CANCELLED

    envs = ExecutionEnvironmentRegistry()
    assert is_ok(
        envs.register_declaration(
            ExecutionEnvironmentDeclaration.isolated(
                ExecutionEnvironmentKind.DOCKER,
                provider_ref="local-docker",
            )
        )
    )
    transport = RecordingQmbDoorTransport()
    door = BacktestingService(jobs=JobHandleService(), environments=envs, transport=transport)
    assert is_ok(door.install())
    placed = door.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=minted.value,
        task_id="task-bt-32-2",
        environment_ref="env:docker",
        experiment_spec_fp1="fp1:spec",
        evidence_ref="evidence:recorded",
    )
    assert is_ok(placed)
    door_cancel = door.cancel(placed.value.handle.job_id)
    assert is_ok(door_cancel)
    assert door_cancel.value.state is JobHandleState.CANCELLED
    assert transport.maps_cancel_to_qmb_abort is False
    assert transport.abort_invocations == ()
    death = ExperimentLedgerStore().on_ungoverned_caller_death()
    assert death.writes_nothing() is True


if __name__ == "__main__":
    main()
