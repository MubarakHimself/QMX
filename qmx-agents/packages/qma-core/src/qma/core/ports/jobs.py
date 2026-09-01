"""JobHandle definition — job id, owner, closed state, operations (CT-46; AD-17).

Declared here; the daemon Compute Router / JobHandle service implements
``submit``, ``JobHandle.attach``, ``wait``, ``JobHandle.reattach``, ``wake``,
``cancel`` and ``stream``. Mapping onto Task state is defined here and applied
only by the daemon (DEC-0316; FR-Q51).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qma.core.ontology import ActorId, Quant
from qma.core.vocabulary.enums import (
    JOB_HANDLE_TERMINAL_STATES,
    JobHandleState,
    TaskMissionState,
    is_job_handle_terminal,
    map_job_handle_to_task_state,
)
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "JOB_HANDLE_ABORT_TRIGGERS",
    "JOB_HANDLE_OPERATIONS",
    "JOB_HANDLE_UNKNOWN_RESOLVE_COMMAND",
    "JOB_HANDLE_UNKNOWN_TRIGGERS",
    "JobHandle",
    "is_abort_trigger",
    "is_unknown_trigger",
    "outcome_for_trigger",
    "parse_job_handle",
    "wake_mailbox_for",
]


# Qualified names: attach/reattach are the JobHandle axis, never wire.attach.
JOB_HANDLE_OPERATIONS: Final[tuple[str, ...]] = (
    "submit",
    "attach",
    "wait",
    "reattach",
    "wake",
    "cancel",
    "stream",
)

# Timeout, lost supervisor, unreachable environment, daemon restart → unknown.
JOB_HANDLE_UNKNOWN_TRIGGERS: Final[frozenset[str]] = frozenset(
    {
        "timeout",
        "lost_supervisor",
        "unreachable_environment",
        "daemon_restart",
    }
)

# Known non-completion by environment or supervisor → aborted, never cancelled.
JOB_HANDLE_ABORT_TRIGGERS: Final[frozenset[str]] = frozenset(
    {
        "oom_kill",
        "container_stop",
        "image_failure",
        "mount_failure",
    }
)

JOB_HANDLE_UNKNOWN_RESOLVE_COMMAND: Final[str] = "unknown.resolve"


def wake_mailbox_for(owner: ActorId | str) -> str:
    """Wake target stored on the handle at submit — owning Quant mailbox."""
    value = owner.value if isinstance(owner, ActorId) else owner
    return f"mailbox:{value}"


def is_unknown_trigger(trigger: object) -> bool:
    return isinstance(trigger, str) and trigger in JOB_HANDLE_UNKNOWN_TRIGGERS


def is_abort_trigger(trigger: object) -> bool:
    return isinstance(trigger, str) and trigger in JOB_HANDLE_ABORT_TRIGGERS


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def outcome_for_trigger(trigger: object) -> Result[JobHandleState]:
    """Map an environment/supervisor observation onto JobHandle state.

    Unknown-certainty triggers never become ``failed`` or ``aborted``.
    Known abort triggers never become ``cancelled``.
    """
    if is_unknown_trigger(trigger):
        return Ok(JobHandleState.UNKNOWN)
    if is_abort_trigger(trigger):
        return Ok(JobHandleState.ABORTED)
    return _invalid(
        "trigger",
        "trigger is not a closed unknown or abort observation (CT-46; FR-Q51)",
        given=repr(trigger),
    )


def _parse_owner(owner: object) -> Result[ActorId]:
    if isinstance(owner, ActorId):
        return Ok(owner)
    if isinstance(owner, Quant):
        return Ok(owner.actor_id)
    return ActorId.try_create(owner)


@dataclass(frozen=True, slots=True)
class JobHandle:
    """Durable job reference: id, owning Quant, exactly one closed state.

    Operations live on the daemon service. ``mapped_task_state`` is the AD-17
    definition; only the daemon applies it to a Task (DEC-0316; FR-Q51).
    """

    job_id: str
    owner: ActorId
    state: JobHandleState
    task_id: str
    wake_mailbox: str
    abort_reason: str | None = None
    unknown_trigger: str | None = None
    correlation_id: str = ""
    wake_armed: bool = False
    recorded_resolution: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if self.recorded_resolution is not None:
            object.__setattr__(
                self,
                "recorded_resolution",
                MappingProxyType(dict(self.recorded_resolution)),
            )

    @property
    def is_terminal(self) -> bool:
        return is_job_handle_terminal(self.state)

    @property
    def mapped_task_state(self) -> TaskMissionState:
        """Fixed JobHandle→Task pairing. Daemon-applied; agents must not author it."""
        return map_job_handle_to_task_state(self.state)

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "job_id": self.job_id,
            "owner": self.owner.value,
            "state": self.state.value,
            "task_id": self.task_id,
            "wake_mailbox": self.wake_mailbox,
            "is_terminal": self.is_terminal,
            "mapped_task_state": self.mapped_task_state.value,
            "wake_armed": self.wake_armed,
            "operations": list(JOB_HANDLE_OPERATIONS),
        }
        if self.abort_reason is not None:
            payload["abort_reason"] = self.abort_reason
        if self.unknown_trigger is not None:
            payload["unknown_trigger"] = self.unknown_trigger
        if self.correlation_id:
            payload["correlation_id"] = self.correlation_id
        if self.recorded_resolution is not None:
            payload["recorded_resolution"] = dict(self.recorded_resolution)
        return MappingProxyType(payload)

    def with_state(
        self,
        state: JobHandleState,
        *,
        abort_reason: str | None = None,
        unknown_trigger: str | None = None,
        wake_armed: bool | None = None,
        recorded_resolution: Mapping[str, object] | None = None,
    ) -> JobHandle:
        return JobHandle(
            job_id=self.job_id,
            owner=self.owner,
            state=state,
            task_id=self.task_id,
            wake_mailbox=self.wake_mailbox,
            abort_reason=self.abort_reason if abort_reason is None else abort_reason,
            unknown_trigger=(self.unknown_trigger if unknown_trigger is None else unknown_trigger),
            correlation_id=self.correlation_id,
            wake_armed=self.wake_armed if wake_armed is None else wake_armed,
            recorded_resolution=(
                self.recorded_resolution if recorded_resolution is None else recorded_resolution
            ),
        )

    @classmethod
    def try_create(
        cls,
        *,
        job_id: object,
        owner: object,
        state: object,
        task_id: object,
        wake_mailbox: object = None,
        abort_reason: object = None,
        unknown_trigger: object = None,
        correlation_id: object = "",
        wake_armed: bool = False,
        recorded_resolution: Mapping[str, object] | None = None,
    ) -> Result[JobHandle]:
        if not isinstance(job_id, str) or job_id.strip() == "":
            return _invalid("job_id", "JobHandle requires a durable job id")
        if not isinstance(task_id, str) or task_id.strip() == "":
            return _invalid("task_id", "JobHandle requires a task_id")
        parsed_owner = _parse_owner(owner)
        if not isinstance(parsed_owner, Ok):
            return parsed_owner
        try:
            resolved_state = (
                state if isinstance(state, JobHandleState) else parse_closed(JobHandleState, state)
            )
        except VocabularyError as exc:
            return _invalid("state", str(exc), given=repr(state))
        if resolved_state is JobHandleState.ABORTED:
            if not isinstance(abort_reason, str) or abort_reason.strip() == "":
                return _invalid(
                    "abort_reason",
                    "aborted JobHandle requires a recorded abort reason (DEC-0316)",
                )
            if is_unknown_trigger(abort_reason):
                return _policy(
                    "abort_reason",
                    "timeout, lost supervisor, unreachable environment, or daemon "
                    "restart resolves to unknown, never aborted (CT-46; FR-Q51)",
                    trigger=abort_reason,
                )
        elif abort_reason not in (None, ""):
            return _invalid(
                "abort_reason",
                "abort_reason is only legal on aborted JobHandle state",
                state=resolved_state.value,
            )
        trigger: str | None
        if unknown_trigger in (None, ""):
            trigger = None
        elif isinstance(unknown_trigger, str):
            trigger = unknown_trigger
        else:
            return _invalid("unknown_trigger", "unknown_trigger must be a closed token")
        if resolved_state is JobHandleState.UNKNOWN:
            if trigger is None:
                trigger = "lost_supervisor"
            if not is_unknown_trigger(trigger):
                return _invalid(
                    "unknown_trigger",
                    "unknown JobHandle requires a closed unknown trigger",
                    given=trigger,
                )
        elif trigger is not None:
            return _invalid(
                "unknown_trigger",
                "unknown_trigger is only legal on unknown JobHandle state",
                state=resolved_state.value,
            )
        if resolved_state in JOB_HANDLE_TERMINAL_STATES and trigger is not None:
            return _policy(
                "state",
                "an unknown-certainty trigger cannot mint a terminal JobHandle",
            )
        mailbox = (
            wake_mailbox.strip()
            if isinstance(wake_mailbox, str) and wake_mailbox.strip()
            else wake_mailbox_for(parsed_owner.value)
        )
        corr = correlation_id.strip() if isinstance(correlation_id, str) else ""
        reason = (
            abort_reason.strip()
            if resolved_state is JobHandleState.ABORTED and isinstance(abort_reason, str)
            else None
        )
        return Ok(
            cls(
                job_id=job_id.strip(),
                owner=parsed_owner.value,
                state=resolved_state,
                task_id=task_id.strip(),
                wake_mailbox=mailbox,
                abort_reason=reason,
                unknown_trigger=trigger,
                correlation_id=corr,
                wake_armed=wake_armed,
                recorded_resolution=recorded_resolution,
            )
        )

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> Result[JobHandle]:
        recorded = payload.get("recorded_resolution")
        resolution: Mapping[str, object] | None
        if recorded is None:
            resolution = None
        elif isinstance(recorded, Mapping):
            mapping = cast("Mapping[object, object]", recorded)
            resolution = {str(key): value for key, value in mapping.items()}
        else:
            return _invalid("recorded_resolution", "recorded_resolution must be an object")
        return cls.try_create(
            job_id=payload.get("job_id"),
            owner=payload.get("owner"),
            state=payload.get("state"),
            task_id=payload.get("task_id"),
            wake_mailbox=payload.get("wake_mailbox"),
            abort_reason=payload.get("abort_reason"),
            unknown_trigger=payload.get("unknown_trigger"),
            correlation_id=payload.get("correlation_id", ""),
            wake_armed=bool(payload.get("wake_armed", False)),
            recorded_resolution=resolution,
        )


def parse_job_handle(**fields: object) -> Result[JobHandle]:
    """Result-returning JobHandle constructor (CT-46; FR-Q51)."""
    recorded = fields.get("recorded_resolution")
    resolution: Mapping[str, object] | None
    if recorded is None:
        resolution = None
    elif isinstance(recorded, Mapping):
        mapping = cast("Mapping[object, object]", recorded)
        resolution = {str(key): value for key, value in mapping.items()}
    else:
        return _invalid("recorded_resolution", "recorded_resolution must be an object")
    return JobHandle.try_create(
        job_id=fields.get("job_id"),
        owner=fields.get("owner"),
        state=fields.get("state"),
        task_id=fields.get("task_id"),
        wake_mailbox=fields.get("wake_mailbox"),
        abort_reason=fields.get("abort_reason"),
        unknown_trigger=fields.get("unknown_trigger"),
        correlation_id=fields.get("correlation_id", ""),
        wake_armed=bool(fields.get("wake_armed", False)),
        recorded_resolution=resolution,
    )
