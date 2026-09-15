"""Story 32.2 — tab-close cancels nothing; JobHandle.cancel is the only authority."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.cancel_authority import (
    COORDINATED_CANCEL_AUTHORITY,
    UNAUTHORIZED_CANCEL_WRITERS,
    record_ungoverned_caller_death,
)
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.jobs import JobHandle
from qma.core.ports.qmb import QMB_BACKTEST_TOOL_ID
from qma.core.refusals import UnauthorizedCancelWriter
from qma.core.vocabulary.enums import ExecutionEnvironmentKind, JobHandleState
from qma.daemon.backtest import BacktestingService, RecordingQmbDoorTransport
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.ledgers.experiment import ExperimentLedgerStore
from qma.wire.attach import AttachRequest, ClientAttachmentState, DetachRequest
from qmf.core import is_ok, is_refusal


def _owner() -> ActorId:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    return minted.value


def _jobs() -> JobHandleService:
    return JobHandleService()


def _queued() -> tuple[JobHandleService, JobHandle]:
    service = _jobs()
    submitted = service.submit(owner=_owner(), task_id="task-32-2")
    assert is_ok(submitted)
    return service, submitted.value


def _running() -> tuple[JobHandleService, JobHandle]:
    service, handle = _queued()
    started = service.start(handle.job_id)
    assert is_ok(started)
    return service, started.value


def _backtest() -> tuple[BacktestingService, RecordingQmbDoorTransport]:
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
    service = BacktestingService(
        jobs=JobHandleService(),
        environments=envs,
        transport=transport,
    )
    assert is_ok(service.install())
    return service, transport


def test_tab_close_leaves_queued_and_running_handles_unchanged() -> None:
    for factory in (_queued, _running):
        service, handle = factory()
        before = handle.state
        detached = service.on_client_detach(handle.job_id, event="tab_close")
        assert is_ok(detached)
        assert detached.value.state is before
        assert detached.value.state not in {
            JobHandleState.CANCELLED,
            JobHandleState.ABORTED,
            JobHandleState.FAILED,
            JobHandleState.DONE,
        }
        reread = service.handle_for(handle.job_id)
        assert reread is not None
        assert reread.state is before
        streamed = service.stream(handle.job_id)
        assert is_ok(streamed)
        kinds = [event.kind for event in streamed.value]
        assert "client_detach" in kinds
        assert "cancel" not in kinds


def test_ui_client_detach_and_wire_detach_do_not_cancel() -> None:
    attachment = ClientAttachmentState(quant_work_active=True)
    scope = (
        {"kind": "desk", "id": "analysis"},
        {"kind": "quant", "id": "notebook"},
    )
    request = AttachRequest.try_create(scope=scope, since_seq=1)
    assert is_ok(request)
    assert is_ok(attachment.attach(request.value))
    closed = attachment.tab_close()
    assert is_ok(closed)
    assert closed.value.invokes_job_handle_cancel is False
    assert closed.value.sets_cancelled is False
    assert closed.value.sets_aborted is False
    assert closed.value.sets_failed is False
    assert closed.value.sets_done is False
    assert closed.value.job_handle_state_unchanged is True
    assert attachment.quant_work_active is True
    assert attachment.attached_scopes == frozenset()

    again = _running()
    wire = DetachRequest.try_create(scope=scope)
    assert is_ok(wire)
    assert wire.value.cancels_job_handle is False
    assert wire.value.sets_terminal_job_handle is False
    unchanged = again[0].on_client_detach(again[1].job_id, event="wire.detach")
    assert is_ok(unchanged)
    assert unchanged.value.state is JobHandleState.RUNNING


def test_job_handle_cancel_is_the_only_coordinated_cancel() -> None:
    service, handle = _running()
    cancelled = service.cancel(handle.job_id)
    assert is_ok(cancelled)
    assert cancelled.value.state is JobHandleState.CANCELLED
    for writer in UNAUTHORIZED_CANCEL_WRITERS:
        other = _running()
        refused = other[0].cancel(other[1].job_id, writer=writer)
        assert is_refusal(refused)
        assert UnauthorizedCancelWriter.matches(refused)
        reread = other[0].handle_for(other[1].job_id)
        assert reread is not None
        assert reread.state is JobHandleState.RUNNING


def test_unauthorized_writers_cannot_set_terminal_or_qmb_ledger() -> None:
    terminals = (
        ("complete", JobHandleState.DONE),
        ("complete", JobHandleState.FAILED),
        ("abort", JobHandleState.ABORTED),
    )
    for writer in UNAUTHORIZED_CANCEL_WRITERS:
        for method, state in terminals:
            service, handle = _running()
            if method == "complete":
                refused = service.complete(handle.job_id, state, writer=writer)
            else:
                refused = service.abort(handle.job_id, reason="oom_kill", writer=writer)
            assert is_refusal(refused)
            assert UnauthorizedCancelWriter.matches(refused)
            reread = service.handle_for(handle.job_id)
            assert reread is not None
            assert reread.state is JobHandleState.RUNNING
    backtest, _transport = _backtest()
    for writer in UNAUTHORIZED_CANCEL_WRITERS:
        refused_ledger = backtest.append_run_ledger({"cancelled": True}, writer=writer)
        assert is_refusal(refused_ledger)
        assert UnauthorizedCancelWriter.matches(refused_ledger)


def test_recording_door_cancel_enters_cancelled_without_qmb_abort() -> None:
    service, transport = _backtest()
    placed = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=_owner(),
        task_id="task-bt-32-2",
        environment_ref="env:docker",
        experiment_spec_fp1="fp1:spec-32-2",
        evidence_ref="evidence:recorded",
    )
    assert is_ok(placed)
    assert placed.value.handle.state is JobHandleState.QUEUED
    assert transport.maps_cancel_to_qmb_abort is False
    assert service.maps_cancel_to_qmb_abort is False
    submit_count = len(transport.invocations)
    cancelled = service.cancel(placed.value.handle.job_id)
    assert is_ok(cancelled)
    assert cancelled.value.state is JobHandleState.CANCELLED
    assert len(transport.invocations) == submit_count
    assert transport.abort_invocations == ()
    live = transport.abort(placed.value.handle.job_id)
    assert is_refusal(live)
    assert live.context["field"] == "qmb_abort"
    assert "RecordingQmbDoorTransport" in str(live.context["reason"])
    assert transport.abort_invocations == ()
    authorized = service.cancel(placed.value.handle.job_id, writer=COORDINATED_CANCEL_AUTHORITY)
    assert is_ok(authorized)
    assert authorized.value.state is JobHandleState.CANCELLED


def test_ungoverned_process_death_writes_nothing_to_ledgers() -> None:
    store = ExperimentLedgerStore()
    before = tuple(store.announcements())
    death = store.on_ungoverned_caller_death()
    assert death.writes_nothing() is True
    assert death.qmb_ledger_writes == ()
    assert death.experiment_ledger_writes == ()
    assert death.cancel_record is None
    assert store.announcements() == before
    invented = store.invent_ungoverned_cancel_record()
    assert is_refusal(invented)
    core = record_ungoverned_caller_death()
    assert core.writes_nothing() is True


def test_reference_usage_example_runs() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "cancel_authority_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()
