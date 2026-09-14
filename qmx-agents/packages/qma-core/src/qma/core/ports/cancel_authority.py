"""Coordinated cancel authority is JobHandle.cancel only (DEC-0278; FR-W36).

A UI client detach or tab close leaves JobHandle state unchanged and never
writes ``cancelled``, ``aborted``, ``failed``, or ``done``. A plugin, Routine,
worker, or UI widget cannot set a terminal JobHandle or QMB ledger state.
While the QMA→QMB door is ``RecordingQmbDoorTransport``, ``JobHandle.cancel``
still enters ``cancelled`` (Story 45.4) and does not map onto a live ``qmb``
abort (Epic 36). Ungoverned ``qmb.run()`` process death writes nothing to the
QMB ledger or Experiment Ledger and invents no ungoverned cancel record.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Literal

from qma.core.refusals.variants import UnauthorizedCancelWriter
from qma.core.vocabulary.enums import JOB_HANDLE_TERMINAL_STATES, JobHandleState
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "CLIENT_DETACH_EVENTS",
    "COORDINATED_CANCEL_AUTHORITY",
    "DAEMON_TERMINAL_WRITERS",
    "RECORDING_DOOR_MAPS_CANCEL_TO_QMB_ABORT",
    "UNAUTHORIZED_CANCEL_WRITERS",
    "UNGOVERNED_CANCEL_KIND",
    "ClientDetachEvent",
    "UngovernedProcessDeath",
    "authorize_coordinated_cancel",
    "authorize_terminal_writer",
    "client_detach_preserves_state",
    "client_detach_writes_terminal",
    "is_client_detach_event",
    "is_coordinated_cancel_authority",
    "is_unauthorized_cancel_writer",
    "parse_client_detach_event",
    "record_ungoverned_caller_death",
    "recording_door_maps_cancel_to_qmb_abort",
    "refuse_unauthorized_cancel",
]


COORDINATED_CANCEL_AUTHORITY: Final[str] = "JobHandle.cancel"
UNAUTHORIZED_CANCEL_WRITERS: Final[frozenset[str]] = frozenset(
    {
        "plugin",
        "routine",
        "worker",
        "ui_widget",
    }
)
DAEMON_TERMINAL_WRITERS: Final[frozenset[str]] = frozenset(
    {
        "daemon",
        "environment",
        "qmb_outcome",
    }
)
UNGOVERNED_CANCEL_KIND: Final[str] = "process_death"
RECORDING_DOOR_MAPS_CANCEL_TO_QMB_ABORT: Final[Literal[False]] = False


class ClientDetachEvent(StrEnum):
    """Client-only detach. Never a JobHandle.cancel and never a terminal write."""

    UI_CLIENT_DETACH = "ui_client_detach"
    TAB_CLOSE = "tab_close"
    WIRE_DETACH = "wire.detach"


CLIENT_DETACH_EVENTS: Final[frozenset[str]] = frozenset(
    member.value for member in ClientDetachEvent
)


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def is_coordinated_cancel_authority(writer: object) -> bool:
    """True only for the JobHandle.cancel verb (FR-W36; Story 45.4)."""
    return writer == COORDINATED_CANCEL_AUTHORITY


def is_unauthorized_cancel_writer(writer: object) -> bool:
    """Plugin, Routine, worker, and UI widget cannot cancel or set terminal state."""
    return isinstance(writer, str) and writer in UNAUTHORIZED_CANCEL_WRITERS


def is_client_detach_event(event: object) -> bool:
    return isinstance(event, str) and event in CLIENT_DETACH_EVENTS


def parse_client_detach_event(event: ClientDetachEvent | str) -> Result[ClientDetachEvent]:
    """Parse a client-detach token. Tab-close is not cancel."""
    try:
        return Ok(parse_closed(ClientDetachEvent, event))
    except VocabularyError as exc:
        return _invalid("event", str(exc), given=repr(event))


def client_detach_preserves_state(state: JobHandleState) -> JobHandleState:
    """Tab-close / UI detach returns the same JobHandle state."""
    return state


def client_detach_writes_terminal() -> bool:
    """No writer sets cancelled, aborted, failed, or done on client detach."""
    return False


def recording_door_maps_cancel_to_qmb_abort() -> bool:
    """RecordingQmbDoorTransport does not map cancel onto a live qmb abort."""
    return RECORDING_DOOR_MAPS_CANCEL_TO_QMB_ABORT


def refuse_unauthorized_cancel(
    *,
    writer: str,
    state: str | None = None,
    surface: str | None = None,
) -> UnauthorizedCancelWriter:
    """Typed refusal: only JobHandle.cancel is coordinated cancel authority."""
    return UnauthorizedCancelWriter.of(writer=writer, state=state, surface=surface)


def authorize_coordinated_cancel(writer: object) -> Result[str]:
    """Admit only JobHandle.cancel. Every other writer is refused."""
    if is_coordinated_cancel_authority(writer):
        return Ok(COORDINATED_CANCEL_AUTHORITY)
    token = writer if isinstance(writer, str) else repr(writer)
    surface = "job_handle"
    return refuse_unauthorized_cancel(writer=token, state="cancelled", surface=surface)


def authorize_terminal_writer(
    writer: object,
    *,
    state: JobHandleState,
) -> Result[str]:
    """Refuse plugin/Routine/worker/UI widget terminal writes.

    ``cancelled`` is admitted only for ``JobHandle.cancel``. Known daemon
    observation writers may set ``done``, ``failed``, or ``aborted``.
    """
    token = writer if isinstance(writer, str) else repr(writer)
    if is_unauthorized_cancel_writer(token):
        return refuse_unauthorized_cancel(
            writer=token,
            state=state.value,
            surface="job_handle",
        )
    if state is JobHandleState.CANCELLED:
        return authorize_coordinated_cancel(token)
    if state not in JOB_HANDLE_TERMINAL_STATES:
        return _invalid(
            "state",
            "authorize_terminal_writer applies only to terminal JobHandle states",
            given=state.value,
        )
    if token in DAEMON_TERMINAL_WRITERS:
        return Ok(token)
    return refuse_unauthorized_cancel(writer=token, state=state.value, surface="job_handle")


@dataclass(frozen=True, slots=True)
class UngovernedProcessDeath:
    """Ungoverned ``qmb.run()`` caller-process death. Writes nothing (FR-W04)."""

    kind: Literal["process_death"] = UNGOVERNED_CANCEL_KIND
    door: Literal["ungoverned"] = "ungoverned"
    lifetime: Literal["ungoverned_caller_process"] = "ungoverned_caller_process"
    qmb_ledger_writes: tuple[()] = ()
    experiment_ledger_writes: tuple[()] = ()
    cancel_record: None = None
    invented_cancel: Literal[False] = False

    def writes_nothing(self) -> bool:
        return (
            self.qmb_ledger_writes == ()
            and self.experiment_ledger_writes == ()
            and self.cancel_record is None
            and self.invented_cancel is False
        )

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "kind": self.kind,
                "door": self.door,
                "lifetime": self.lifetime,
                "qmb_ledger_writes": list(self.qmb_ledger_writes),
                "experiment_ledger_writes": list(self.experiment_ledger_writes),
                "cancel_record": self.cancel_record,
                "invented_cancel": self.invented_cancel,
                "writes_nothing": self.writes_nothing(),
            }
        )


def record_ungoverned_caller_death() -> UngovernedProcessDeath:
    """Process death of ungoverned ``qmb.run()`` — no ledger, no invented cancel."""
    return UngovernedProcessDeath()
