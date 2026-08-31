"""Protection-priority connection pacer and wire-handoff timing (TN-6/TN-22).

Protective reserve capacity is unavailable to entry work. ``cancel_order``,
``close_position``, ``close_all``, and ``amend_protection`` dispatch ahead of
``place_order``. The submission deadline begins only at wire handoff. Time
awaiting pacer admission is a local queue whose breach is a door refusal on the
veto path naming the pacer — never UNKNOWN, never a stream block. No command is
retried after handoff (DEC-0191, DEC-0224).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final

from qmf.core import (
    Duration,
    Instant,
    MonotonicReading,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_refusal,
)

from qmn.venue import Command, CommandKind

__all__ = [
    "PACER_DOOR",
    "AdmissionClass",
    "ConnectionCommandPacer",
    "PacerAdmission",
    "WireHandoff",
    "admission_class_for",
    "local_queue_bound_refusal",
]


PACER_DOOR: Final[str] = "pacer"


class AdmissionClass(StrEnum):
    """Whether a command may consume protective reserve capacity."""

    PROTECTIVE = "protective"
    ENTRY = "entry"


@dataclass(frozen=True, slots=True)
class PacerAdmission:
    """One successful admission from the connection pacer."""

    admission_class: AdmissionClass
    enqueued_at: MonotonicReading
    admitted_at: MonotonicReading
    queue_wait: Duration
    used_protective_reserve: bool


@dataclass(frozen=True, slots=True)
class WireHandoff:
    """The instant the client transmits — submission deadline starts here.

    Distinct from command mint and from pacer enqueue. After handoff, retry is
    prohibited; uncertain fate becomes UNKNOWN under the submission deadline.
    """

    command_fp1: str
    handed_off_at: Instant
    submission_deadline: Instant
    retry_prohibited: bool = True


def admission_class_for(command: object) -> Result[AdmissionClass]:
    """Classify a command for protective-reserve admission."""
    if not isinstance(command, Command):
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "command",
                "reason": "pacer admission classifies a typed CT-19 Command",
                "given": type(command).__name__,
            },
        )
    if command.kind is CommandKind.PLACE_ORDER:
        return Ok(AdmissionClass.ENTRY)
    if command.kind in {
        CommandKind.CANCEL_ORDER,
        CommandKind.CLOSE_POSITION,
        CommandKind.CLOSE_ALL,
        CommandKind.AMEND_PROTECTION,
    }:
        return Ok(AdmissionClass.PROTECTIVE)
    return TypedRefusal(
        category=RefusalCategory.UNSUPPORTED_CAPABILITY,
        retryability=Retryability.NO,
        context={
            "field": "command_kind",
            "reason": "unknown command kind for pacer admission",
            "kind": command.kind.value,
        },
    )


def local_queue_bound_refusal(
    *,
    queue_wait: Duration,
    local_queue_bound: Duration,
    admission_class: AdmissionClass,
) -> TypedRefusal:
    """Door refusal on the veto path naming the pacer — never UNKNOWN."""
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.AFTER_CONDITION,
        context={
            "field": "local_queue_bound",
            "reason": "local queue-bound breach awaiting pacer admission is a door "
            "refusal on the veto path naming the pacer, never UNKNOWN and never "
            "a stream block",
            "door": PACER_DOOR,
            "path": "veto",
            "admission_class": admission_class.value,
            "queue_wait_ns": queue_wait.value_ns,
            "local_queue_bound_ns": local_queue_bound.value_ns,
            "outcome": "denied-locally",
        },
        after_condition_descriptor="pacer queue capacity within local_queue_bound",
    )


@dataclass
class ConnectionCommandPacer:
    """Per-connection admission with protective reserve and local-queue bound.

    ``protective_reserve_capacity`` slots are unavailable to entry work. Protective
    commands may consume general or reserve capacity; entries may only consume
    general (non-reserve) capacity. Dispatch prefers protective work.
    """

    local_queue_bound: Duration
    protective_reserve_capacity: int
    general_capacity: int = 1
    _protective_in_flight: int = 0
    _entry_in_flight: int = 0
    _handed_off: set[str] = field(default_factory=set[str])
    _pending_protective: int = 0
    _pending_entry: int = 0

    @classmethod
    def try_create(
        cls,
        *,
        local_queue_bound: object,
        protective_reserve_capacity: object,
        general_capacity: object = 1,
    ) -> Result[ConnectionCommandPacer]:
        if not isinstance(local_queue_bound, Duration) or local_queue_bound.value_ns <= 0:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "local_queue_bound",
                    "reason": "registry:local_queue_bound is a positive Duration",
                    "given": repr(local_queue_bound),
                },
            )
        if (
            not isinstance(protective_reserve_capacity, int)
            or isinstance(protective_reserve_capacity, bool)
            or protective_reserve_capacity < 0
        ):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "protective_reserve_capacity",
                    "reason": "registry:protective_reserve_capacity is a non-negative count",
                    "given": repr(protective_reserve_capacity),
                },
            )
        if (
            not isinstance(general_capacity, int)
            or isinstance(general_capacity, bool)
            or general_capacity < 1
        ):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "general_capacity",
                    "reason": "general pacer capacity is a positive count",
                    "given": repr(general_capacity),
                },
            )
        return Ok(
            cls(
                local_queue_bound=local_queue_bound,
                protective_reserve_capacity=protective_reserve_capacity,
                general_capacity=general_capacity,
            )
        )

    @property
    def protective_reserve_remaining(self) -> int:
        used = max(0, self._protective_in_flight - self.general_capacity)
        return max(0, self.protective_reserve_capacity - used)

    def enqueue(self, command: object) -> Result[AdmissionClass]:
        """Record pending work; protective pending is preferred at dispatch."""
        klass = admission_class_for(command)
        if is_refusal(klass):
            return klass
        if klass.value is AdmissionClass.PROTECTIVE:
            self._pending_protective += 1
        else:
            self._pending_entry += 1
        return klass

    def admit(
        self,
        command: object,
        *,
        enqueued_at: object,
        now: object,
    ) -> Result[PacerAdmission]:
        """Admit one command or refuse on local queue-bound / reserve rules."""
        klass_result = admission_class_for(command)
        if is_refusal(klass_result):
            return klass_result
        klass = klass_result.value
        if not isinstance(enqueued_at, MonotonicReading):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "enqueued_at",
                    "reason": "pacer queue wait is measured from a MonotonicReading",
                    "given": repr(enqueued_at),
                },
            )
        if not isinstance(now, MonotonicReading):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "now",
                    "reason": "pacer admission reads a caller-supplied MonotonicReading",
                    "given": repr(now),
                },
            )
        wait = now.elapsed_since(enqueued_at)
        if is_refusal(wait):
            return wait
        if wait.value.value_ns > self.local_queue_bound.value_ns:
            return local_queue_bound_refusal(
                queue_wait=wait.value,
                local_queue_bound=self.local_queue_bound,
                admission_class=klass,
            )

        total_in_flight = self._protective_in_flight + self._entry_in_flight
        used_reserve = False
        if klass is AdmissionClass.ENTRY:
            # Protective pending always blocks entry from consuming shared slots.
            if self._pending_protective > 0:
                return TypedRefusal(
                    category=RefusalCategory.POLICY_REJECTION,
                    retryability=Retryability.AFTER_CONDITION,
                    context={
                        "field": "protection_priority",
                        "reason": "protective commands dispatch ahead of place_order; "
                        "entry work waits",
                        "door": PACER_DOOR,
                        "path": "veto",
                        "pending_protective": self._pending_protective,
                    },
                    after_condition_descriptor="protective queue drains",
                )
            general_used = (
                min(self._protective_in_flight, self.general_capacity) + self._entry_in_flight
            )
            if general_used >= self.general_capacity:
                return TypedRefusal(
                    category=RefusalCategory.POLICY_REJECTION,
                    retryability=Retryability.AFTER_CONDITION,
                    context={
                        "field": "protective_reserve_capacity",
                        "reason": "protective reserve capacity is unavailable to entry "
                        "work; entry admission waits for general capacity",
                        "door": PACER_DOOR,
                        "path": "veto",
                        "protective_reserve_capacity": self.protective_reserve_capacity,
                        "general_capacity": self.general_capacity,
                        "entry_in_flight": self._entry_in_flight,
                        "protective_in_flight": self._protective_in_flight,
                    },
                    after_condition_descriptor="general pacer capacity available",
                )
            self._entry_in_flight += 1
            if self._pending_entry > 0:
                self._pending_entry -= 1
        else:
            # Protective may use general slots first, then reserve.
            if total_in_flight < self.general_capacity:
                used_reserve = False
            elif self.protective_reserve_remaining > 0:
                used_reserve = True
            else:
                return TypedRefusal(
                    category=RefusalCategory.POLICY_REJECTION,
                    retryability=Retryability.AFTER_CONDITION,
                    context={
                        "field": "pacer_capacity",
                        "reason": "no general or protective-reserve capacity available",
                        "door": PACER_DOOR,
                        "path": "veto",
                    },
                    after_condition_descriptor="pacer capacity available",
                )
            self._protective_in_flight += 1
            if self._pending_protective > 0:
                self._pending_protective -= 1

        return Ok(
            PacerAdmission(
                admission_class=klass,
                enqueued_at=enqueued_at,
                admitted_at=now,
                queue_wait=wait.value,
                used_protective_reserve=used_reserve,
            )
        )

    def release(self, admission_class: object) -> Result[bool]:
        """Release one in-flight admission slot."""
        if isinstance(admission_class, AdmissionClass):
            klass = admission_class
        elif isinstance(admission_class, str):
            try:
                klass = AdmissionClass(admission_class)
            except ValueError:
                return TypedRefusal(
                    category=RefusalCategory.INVALID_INPUT,
                    retryability=Retryability.NO,
                    context={
                        "field": "admission_class",
                        "reason": "release requires protective | entry",
                        "given": admission_class,
                    },
                )
        else:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "admission_class",
                    "reason": "release requires protective | entry",
                    "given": repr(admission_class),
                },
            )
        if klass is AdmissionClass.ENTRY:
            self._entry_in_flight = max(0, self._entry_in_flight - 1)
        else:
            self._protective_in_flight = max(0, self._protective_in_flight - 1)
        return Ok(True)

    def begin_wire_handoff(
        self,
        *,
        command_fp1: object,
        handed_off_at: object,
        submission_deadline: object,
    ) -> Result[WireHandoff]:
        """Start the submission deadline at wire handoff — never at command mint."""
        if not isinstance(command_fp1, str) or command_fp1.strip() == "":
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "command_fp1",
                    "reason": "wire handoff names the command fp1",
                    "given": repr(command_fp1),
                },
            )
        if not isinstance(handed_off_at, Instant):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "handed_off_at",
                    "reason": "wire handoff is a wall Instant",
                    "given": repr(handed_off_at),
                },
            )
        if not isinstance(submission_deadline, Instant):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "submission_deadline",
                    "reason": "submission deadline is a wall Instant starting at handoff",
                    "given": repr(submission_deadline),
                },
            )
        if submission_deadline.value_ns < handed_off_at.value_ns:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "submission_deadline",
                    "reason": "submission deadline must not precede wire handoff",
                    "handed_off_at_ns": handed_off_at.value_ns,
                    "submission_deadline_ns": submission_deadline.value_ns,
                },
            )
        fp = command_fp1.strip()
        if fp in self._handed_off:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "wire_handoff",
                    "reason": "no command is retried after wire handoff",
                    "command_fp1": fp,
                },
            )
        self._handed_off.add(fp)
        return Ok(
            WireHandoff(
                command_fp1=fp,
                handed_off_at=handed_off_at,
                submission_deadline=submission_deadline,
                retry_prohibited=True,
            )
        )

    def refuse_retry_after_handoff(self, command_fp1: object) -> Result[bool]:
        """Block any post-handoff retry attempt."""
        if not isinstance(command_fp1, str) or command_fp1.strip() == "":
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "command_fp1",
                    "reason": "retry gate names the command fp1",
                    "given": repr(command_fp1),
                },
            )
        fp = command_fp1.strip()
        if fp in self._handed_off:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "wire_handoff",
                    "reason": "no command is retried after wire handoff",
                    "command_fp1": fp,
                },
            )
        return Ok(True)
