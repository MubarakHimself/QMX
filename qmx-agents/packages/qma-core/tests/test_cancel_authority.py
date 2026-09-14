"""Story 32.2 — tab-close cancels nothing; JobHandle.cancel is the only authority."""

from __future__ import annotations

from qma.core.ports.cancel_authority import (
    CLIENT_DETACH_EVENTS,
    COORDINATED_CANCEL_AUTHORITY,
    RECORDING_DOOR_MAPS_CANCEL_TO_QMB_ABORT,
    UNAUTHORIZED_CANCEL_WRITERS,
    UNGOVERNED_CANCEL_KIND,
    ClientDetachEvent,
    authorize_coordinated_cancel,
    authorize_terminal_writer,
    client_detach_preserves_state,
    client_detach_writes_terminal,
    is_client_detach_event,
    is_coordinated_cancel_authority,
    is_unauthorized_cancel_writer,
    parse_client_detach_event,
    record_ungoverned_caller_death,
    recording_door_maps_cancel_to_qmb_abort,
)
from qma.core.refusals import UnauthorizedCancelWriter
from qma.core.vocabulary.enums import JobHandleState
from qmf.core import is_ok, is_refusal


def test_job_handle_cancel_is_the_only_coordinated_authority() -> None:
    assert COORDINATED_CANCEL_AUTHORITY == "JobHandle.cancel"
    assert is_coordinated_cancel_authority("JobHandle.cancel") is True
    admitted = authorize_coordinated_cancel("JobHandle.cancel")
    assert is_ok(admitted)
    assert admitted.value == "JobHandle.cancel"


def test_plugin_routine_worker_ui_widget_cannot_cancel() -> None:
    assert frozenset({"plugin", "routine", "worker", "ui_widget"}) == UNAUTHORIZED_CANCEL_WRITERS
    for writer in UNAUTHORIZED_CANCEL_WRITERS:
        assert is_unauthorized_cancel_writer(writer)
        refused = authorize_coordinated_cancel(writer)
        assert is_refusal(refused)
        assert UnauthorizedCancelWriter.matches(refused)
        assert refused.context["authority"] == "JobHandle.cancel"
        assert refused.context["writer"] == writer


def test_unauthorized_writers_cannot_set_terminal_job_handle_state() -> None:
    terminals = (
        JobHandleState.CANCELLED,
        JobHandleState.ABORTED,
        JobHandleState.FAILED,
        JobHandleState.DONE,
    )
    for writer in UNAUTHORIZED_CANCEL_WRITERS:
        for state in terminals:
            refused = authorize_terminal_writer(writer, state=state)
            assert is_refusal(refused)
            assert UnauthorizedCancelWriter.matches(refused)
            assert refused.context["state"] == state.value
            assert refused.context["surface"] == "job_handle"


def test_daemon_outcome_writers_may_set_done_failed_aborted_not_cancelled() -> None:
    done = authorize_terminal_writer("daemon", state=JobHandleState.DONE)
    assert is_ok(done)
    failed = authorize_terminal_writer("qmb_outcome", state=JobHandleState.FAILED)
    assert is_ok(failed)
    aborted = authorize_terminal_writer("environment", state=JobHandleState.ABORTED)
    assert is_ok(aborted)
    cancelled = authorize_terminal_writer("daemon", state=JobHandleState.CANCELLED)
    assert is_refusal(cancelled)
    assert UnauthorizedCancelWriter.matches(cancelled)


def test_tab_close_is_client_detach_and_writes_no_terminal() -> None:
    assert frozenset({"ui_client_detach", "tab_close", "wire.detach"}) == CLIENT_DETACH_EVENTS
    for event in CLIENT_DETACH_EVENTS:
        assert is_client_detach_event(event)
        parsed = parse_client_detach_event(event)
        assert is_ok(parsed)
    tab = parse_client_detach_event(ClientDetachEvent.TAB_CLOSE)
    assert is_ok(tab)
    assert tab.value is ClientDetachEvent.TAB_CLOSE
    for state in (JobHandleState.QUEUED, JobHandleState.RUNNING):
        assert client_detach_preserves_state(state) is state
    assert client_detach_writes_terminal() is False
    invented = parse_client_detach_event("cancel")
    assert is_refusal(invented)


def test_recording_door_does_not_map_cancel_to_live_qmb_abort() -> None:
    assert RECORDING_DOOR_MAPS_CANCEL_TO_QMB_ABORT is False
    assert recording_door_maps_cancel_to_qmb_abort() is False


def test_ungoverned_process_death_writes_nothing() -> None:
    death = record_ungoverned_caller_death()
    assert death.kind == UNGOVERNED_CANCEL_KIND
    assert death.door == "ungoverned"
    assert death.lifetime == "ungoverned_caller_process"
    assert death.qmb_ledger_writes == ()
    assert death.experiment_ledger_writes == ()
    assert death.cancel_record is None
    assert death.invented_cancel is False
    assert death.writes_nothing() is True
    payload = death.to_payload()
    assert payload["writes_nothing"] is True
    assert "cancelled" not in payload
