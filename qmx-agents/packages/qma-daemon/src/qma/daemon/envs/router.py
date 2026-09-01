"""Compute Router slot governance (CT-46; AD-17; FR-Q49).

An ExecutionEnvironment instance grants at most one ``environment_lease`` per
slot. Capacity is the record-homed ``registry:environment.max_in_flight``
value on the declaration. Full occupancy queues; agents never choose a
machine or vendor. ``unknown`` jobs keep their slot until an explicit
recorded resolution.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType

from qma.core.ports.execution import (
    ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT,
    ENVIRONMENT_MAX_IN_FLIGHT_KEY,
    ExecutionEnvironmentDeclaration,
    is_pinned_single_slot_kind,
    max_in_flight_editability,
    resolve_max_in_flight,
)
from qma.core.refusals import NoEnvironment
from qma.core.vocabulary.enums import ExecutionEnvironmentKind, VariableEditability
from qma.daemon.envs.registry import EnvironmentLease, ExecutionEnvironmentRegistry
from qmf.core import Ok, Result, is_ok
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "ComputeRouter",
    "PlacementDecision",
    "QueuedPlacement",
]


def _kind_token(kind: ExecutionEnvironmentKind | str) -> str:
    return kind.value if isinstance(kind, ExecutionEnvironmentKind) else kind


@dataclass(frozen=True, slots=True)
class QueuedPlacement:
    """A placement request waiting for a free ``environment_lease`` slot."""

    task_id: str
    kind: str
    queue_position: int
    occupied: int
    max_in_flight: int

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "outcome": "queued",
                "lease": None,
                "task_id": self.task_id,
                "kind": self.kind,
                "queue_position": self.queue_position,
                "occupied": self.occupied,
                "max_in_flight": self.max_in_flight,
                "capacity_key": ENVIRONMENT_MAX_IN_FLIGHT_KEY,
            }
        )


@dataclass(frozen=True, slots=True)
class PlacementDecision:
    """Granted ``environment_lease`` or queued wait — never over-allocation."""

    kind: str
    max_in_flight: int
    occupied: int
    lease: EnvironmentLease | None = None
    queued: QueuedPlacement | None = None
    agent_choice_ignored: bool = False

    @property
    def granted(self) -> bool:
        return self.lease is not None

    @property
    def is_queued(self) -> bool:
        return self.queued is not None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "kind": self.kind,
            "max_in_flight": self.max_in_flight,
            "occupied": self.occupied,
            "capacity_key": ENVIRONMENT_MAX_IN_FLIGHT_KEY,
            "granted": self.granted,
            "queued": self.is_queued,
            "agent_choice_ignored": self.agent_choice_ignored,
        }
        if self.lease is not None:
            payload["environment_lease"] = dict(self.lease.to_payload())
            payload["outcome"] = "granted"
        if self.queued is not None:
            payload["queued_placement"] = dict(self.queued.to_payload())
            payload["outcome"] = "queued"
        return MappingProxyType(payload)


class ComputeRouter:
    """Places jobs onto declared environments under slot-occupancy law (FR-Q49)."""

    def __init__(
        self,
        environments: ExecutionEnvironmentRegistry | None = None,
    ) -> None:
        self._environments = (
            environments if environments is not None else ExecutionEnvironmentRegistry()
        )
        self._leases: dict[str, EnvironmentLease] = {}
        self._slots: dict[str, dict[int, str]] = {}
        self._queue: dict[str, list[str]] = {}
        self._unknown: set[str] = set()

    @property
    def environments(self) -> ExecutionEnvironmentRegistry:
        return self._environments

    def lease_for(self, task_id: str) -> EnvironmentLease | None:
        return self._leases.get(task_id)

    def is_unknown(self, task_id: str) -> bool:
        return task_id in self._unknown

    def occupied_count(self, kind: ExecutionEnvironmentKind | str) -> int:
        return len(self._slots.get(_kind_token(kind), {}))

    def queued_task_ids(self, kind: ExecutionEnvironmentKind | str) -> tuple[str, ...]:
        return tuple(self._queue.get(_kind_token(kind), ()))

    def capacity_for(self, kind: ExecutionEnvironmentKind | str) -> Result[int]:
        """Declared ``registry:environment.max_in_flight`` for a bound kind."""
        token = _kind_token(kind)
        stored = self._environments.declaration(token)
        if stored is None:
            return NoEnvironment.of(kind=token)
        return resolve_max_in_flight(stored.kind, stored.max_in_flight)

    def place_job(
        self,
        *,
        task_id: str,
        kind: ExecutionEnvironmentKind | str,
        agent_machine: str | None = None,
        agent_vendor: str | None = None,
        machine: str | None = None,
        vendor: str | None = None,
        host: str | None = None,
    ) -> Result[PlacementDecision]:
        """Grant one slot or queue. Agent machine/vendor choices are ignored."""
        if not task_id:
            return invalid_input("task_id", "environment_lease requires a task_id")
        ignored = any(
            value not in (None, "") for value in (agent_machine, agent_vendor, machine, vendor)
        )
        token = _kind_token(kind)
        eligible = self._environments.evaluate_environment_lease(
            task_id=task_id,
            kind=kind,
            host=host,
        )
        if not is_ok(eligible):
            return eligible
        capacity = self.capacity_for(kind)
        if not is_ok(capacity):
            return capacity
        existing = self._leases.get(task_id)
        if existing is not None and existing.kind == token:
            return Ok(
                PlacementDecision(
                    kind=token,
                    max_in_flight=capacity.value,
                    occupied=self.occupied_count(token),
                    lease=existing,
                    agent_choice_ignored=ignored,
                )
            )
        if task_id in self._queue.get(token, ()):
            return Ok(self._queued_decision(task_id, token, capacity.value, ignored))
        slot = self._first_free_slot(token, capacity.value)
        if slot is None:
            queue = self._queue.setdefault(token, [])
            queue.append(task_id)
            return Ok(self._queued_decision(task_id, token, capacity.value, ignored))
        lease = EnvironmentLease(
            task_id=task_id,
            kind=token,
            slot_id=f"slot:{token}:{slot}",
            provider_id=eligible.value.provider_id,
        )
        self._slots.setdefault(token, {})[slot] = task_id
        self._leases[task_id] = lease
        return Ok(
            PlacementDecision(
                kind=token,
                max_in_flight=capacity.value,
                occupied=self.occupied_count(token),
                lease=lease,
                agent_choice_ignored=ignored,
            )
        )

    def hold_unknown(self, task_id: str) -> Result[EnvironmentLease]:
        """Keep the occupying ``environment_lease`` for an ``unknown`` job."""
        lease = self._leases.get(task_id)
        if lease is None:
            return policy_rejection(
                "environment_lease",
                "unknown jobs hold an existing environment_lease slot; a job "
                "without a lease cannot occupy one by assumption (CT-46; FR-Q49)",
                task_id=task_id,
            )
        self._unknown.add(task_id)
        return Ok(lease)

    def release(self, task_id: str) -> Result[PlacementDecision | None]:
        """Free a known occupying slot. Refuses to drop an ``unknown`` hold."""
        if task_id in self._unknown:
            return policy_rejection(
                "environment_lease",
                "an unknown job holds its environment_lease until an explicit "
                "recorded resolution; release does not free the slot (CT-46; FR-Q49)",
                task_id=task_id,
            )
        return Ok(self._free_slot(task_id))

    def resolve_unknown(
        self,
        task_id: str,
        *,
        recorded: bool,
    ) -> Result[PlacementDecision | None]:
        """Explicit recorded resolution is the only path that frees an unknown slot."""
        if not recorded:
            return policy_rejection(
                "environment_lease",
                "an unknown job holds its environment_lease until an explicit "
                "recorded resolution (CT-46; FR-Q49)",
                task_id=task_id,
                recorded=False,
            )
        if task_id not in self._unknown:
            return policy_rejection(
                "environment_lease",
                "resolve_unknown requires a job already holding unknown occupancy",
                task_id=task_id,
            )
        self._unknown.discard(task_id)
        return Ok(self._free_slot(task_id))

    def retry_unknown(self, task_id: str) -> Result[EnvironmentLease]:
        """Retry must not invent a terminal outcome or free the slot."""
        return self._refuse_unknown_shortcut(task_id, action="retry")

    def assume_outcome(self, task_id: str, outcome: str) -> Result[EnvironmentLease]:
        """An assumed outcome must not free the unknown slot."""
        return self._refuse_unknown_shortcut(task_id, action="assume_outcome", outcome=outcome)

    def invent_terminal(self, task_id: str, state: str) -> Result[EnvironmentLease]:
        """A synthetic terminal result must not free the unknown slot."""
        return self._refuse_unknown_shortcut(task_id, action="invent_terminal", state=state)

    def write_max_in_flight(
        self,
        kind: ExecutionEnvironmentKind | str,
        value: object,
    ) -> Result[ExecutionEnvironmentDeclaration]:
        """Operator-facing declaration write of record-homed capacity (AD-26)."""
        token = _kind_token(kind)
        stored = self._environments.declaration(token)
        if stored is None:
            return NoEnvironment.of(kind=token)
        if is_pinned_single_slot_kind(stored.kind):
            return policy_rejection(
                "max_in_flight",
                "registry:environment.max_in_flight is pinned and uneditable for "
                "remote_host and desktop (CT-46; FR-Q49)",
                kind=token,
                editability=VariableEditability.UNEDITABLE.value,
                pinned=ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT,
                registry_key=ENVIRONMENT_MAX_IN_FLIGHT_KEY,
            )
        resolved = resolve_max_in_flight(stored.kind, value)
        if not is_ok(resolved):
            return resolved
        occupied = self.occupied_count(token)
        if occupied > resolved.value:
            return policy_rejection(
                "max_in_flight",
                "cannot shrink registry:environment.max_in_flight below occupied "
                "slots (CT-46; FR-Q49)",
                kind=token,
                occupied=occupied,
                given=resolved.value,
                registry_key=ENVIRONMENT_MAX_IN_FLIGHT_KEY,
            )
        updated = replace(stored, max_in_flight=resolved.value)
        written = self._environments.replace_declaration(updated)
        if not is_ok(written):
            return written
        return Ok(updated)

    def occupancy(self, kind: ExecutionEnvironmentKind | str) -> Mapping[str, object]:
        token = _kind_token(kind)
        stored = self._environments.declaration(token)
        capacity = stored.max_in_flight if stored is not None else None
        return MappingProxyType(
            {
                "kind": token,
                "occupied": self.occupied_count(token),
                "queued": len(self._queue.get(token, ())),
                "max_in_flight": capacity,
                "capacity_key": ENVIRONMENT_MAX_IN_FLIGHT_KEY,
                "editability": (
                    max_in_flight_editability(token).value if stored is not None else None
                ),
                "pinned_single_slot": is_pinned_single_slot_kind(token),
            }
        )

    def _refuse_unknown_shortcut(
        self,
        task_id: str,
        *,
        action: str,
        outcome: str | None = None,
        state: str | None = None,
    ) -> Result[EnvironmentLease]:
        lease = self._leases.get(task_id)
        occupying = task_id in self._unknown and lease is not None
        extra: dict[str, object] = {
            "task_id": task_id,
            "action": action,
            "occupying": occupying,
        }
        if outcome is not None:
            extra["outcome"] = outcome
        if state is not None:
            extra["state"] = state
        return policy_rejection(
            "environment_lease",
            "an unknown job holds its environment_lease until an explicit "
            "recorded resolution; retry, assumed outcome, or synthetic terminal "
            "state does not free the slot (CT-46; FR-Q49)",
            **extra,
        )

    def _queued_decision(
        self,
        task_id: str,
        kind: str,
        capacity: int,
        ignored: bool,
    ) -> PlacementDecision:
        queue = self._queue.get(kind, [])
        position = queue.index(task_id) + 1 if task_id in queue else len(queue) + 1
        occupied = self.occupied_count(kind)
        return PlacementDecision(
            kind=kind,
            max_in_flight=capacity,
            occupied=occupied,
            queued=QueuedPlacement(
                task_id=task_id,
                kind=kind,
                queue_position=position,
                occupied=occupied,
                max_in_flight=capacity,
            ),
            agent_choice_ignored=ignored,
        )

    def _first_free_slot(self, kind: str, capacity: int) -> int | None:
        used = self._slots.get(kind, {})
        for index in range(capacity):
            if index not in used:
                return index
        return None

    def _remove_from_queue(self, task_id: str) -> None:
        for queue in self._queue.values():
            while task_id in queue:
                queue.remove(task_id)

    def _free_slot(self, task_id: str) -> PlacementDecision | None:
        self._remove_from_queue(task_id)
        lease = self._leases.pop(task_id, None)
        self._unknown.discard(task_id)
        if lease is None:
            return None
        slots = self._slots.get(lease.kind, {})
        for index, holder in tuple(slots.items()):
            if holder == task_id:
                del slots[index]
                break
        return self._promote_queue(lease.kind)

    def _promote_queue(self, kind: str) -> PlacementDecision | None:
        queue = self._queue.get(kind, [])
        if not queue:
            return None
        capacity = self.capacity_for(kind)
        if not is_ok(capacity):
            return None
        slot = self._first_free_slot(kind, capacity.value)
        if slot is None:
            return None
        task_id = queue.pop(0)
        provider = None
        stored = self._environments.declaration(kind)
        if stored is not None and stored.provider_ref:
            provider = stored.provider_ref
        existing_probe = self._environments.evaluate_environment_lease(
            task_id=task_id,
            kind=kind,
        )
        if is_ok(existing_probe):
            provider = existing_probe.value.provider_id
        lease = EnvironmentLease(
            task_id=task_id,
            kind=kind,
            slot_id=f"slot:{kind}:{slot}",
            provider_id=provider,
        )
        self._slots.setdefault(kind, {})[slot] = task_id
        self._leases[task_id] = lease
        return PlacementDecision(
            kind=kind,
            max_in_flight=capacity.value,
            occupied=self.occupied_count(kind),
            lease=lease,
        )
