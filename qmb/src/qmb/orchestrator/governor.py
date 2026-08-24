"""Resource governor: min(cpu, memory) admission with enqueue-on-full (B-5, FM-6).

Budgets are the registry keys ``qmb_governor_cpu_budget`` (count) and
``qmb_governor_memory_budget`` (bytes). Both are declared-per-machine and
UI-editable; this module never bakes a spine number. 12-14 concurrent runs
on sandbox hardware is a motivating reference under AD-13, never a validated
budget (DEC-0161, DEC-0157).

Admission is the more constraining of the two remaining capacities: a run
is admitted only when ``reserved_cpu + cpu_cost <= cpu_budget`` AND
``reserved_memory + projected_peak <= memory_budget``. A run whose projected
peak exceeds the declared total memory budget is a typed refusal (it can
never fit). A run that exceeds only *remaining* budget enqueues (enqueue-on-
full) or, when ``on_full=refuse``, returns a typed refusal — never silent
oversubscription. When a run finishes, the next queued run is admitted.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_refusal,
)

from qmb._refuse import invalid, policy

__all__ = [
    "CPU_BUDGET_KEY",
    "DECISION_ADMITTED",
    "DECISION_QUEUED",
    "MEMORY_BUDGET_KEY",
    "ON_FULL_ENQUEUE",
    "ON_FULL_REFUSE",
    "SANDBOX_CONCURRENT_MOTIVATING_REFERENCE",
    "Admission",
    "GovernedRequest",
    "GovernorBudgets",
    "ResourceGovernor",
    "governor_identity",
]

CPU_BUDGET_KEY: Final[str] = "qmb_governor_cpu_budget"
MEMORY_BUDGET_KEY: Final[str] = "qmb_governor_memory_budget"
ON_FULL_ENQUEUE: Final[str] = "enqueue"
ON_FULL_REFUSE: Final[str] = "refuse"
DECISION_ADMITTED: Final[str] = "admitted"
DECISION_QUEUED: Final[str] = "queued"
SANDBOX_CONCURRENT_MOTIVATING_REFERENCE: Final[str] = "not-a-validated-budget"
_BOUND: Final[str] = "min-cpu-memory"
_ON_FULL_VALUES: Final[frozenset[str]] = frozenset({ON_FULL_ENQUEUE, ON_FULL_REFUSE})
_AFTER_FINISH: Final[str] = "a running run finishes and remaining min(cpu, memory) covers this run"


def governor_identity() -> dict[str, object]:
    """Identity-bearing governor fields. Budget *values* are omitted (DEC-0157)."""
    return {
        "bound": _BOUND,
        "cpu_budget_key": CPU_BUDGET_KEY,
        "memory_budget_key": MEMORY_BUDGET_KEY,
        "on_full_default": ON_FULL_ENQUEUE,
        "sandbox_concurrent_motivating_reference": SANDBOX_CONCURRENT_MOTIVATING_REFERENCE,
        "silent_oversubscription": False,
    }


@dataclass(frozen=True, slots=True)
class GovernorBudgets:
    """Declared-per-machine CPU count and memory-byte budgets. No spine default."""

    cpu_budget: int
    memory_budget: int

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity names the registry keys; values stay per-machine."""
        return {
            "bound": _BOUND,
            "cpu_budget": self.cpu_budget,
            "cpu_budget_key": CPU_BUDGET_KEY,
            "memory_budget": self.memory_budget,
            "memory_budget_key": MEMORY_BUDGET_KEY,
        }

    def parallelism_bound(
        self,
        projected_peak_memory: object,
        cpu_cost: object = 1,
    ) -> Result[int]:
        """``min(cpu_budget // cpu_cost, memory_budget // projected_peak)``.

        Zero means the run can never be admitted under these declared budgets.
        """
        peak = _positive_int("projected_peak_memory", projected_peak_memory)
        if is_refusal(peak):
            return peak
        cost = _positive_int("cpu_cost", cpu_cost)
        if is_refusal(cost):
            return cost
        cpu_slots = self.cpu_budget // cost.value
        memory_slots = self.memory_budget // peak.value
        return Ok(min(cpu_slots, memory_slots))

    @classmethod
    def try_create(
        cls,
        cpu_budget: object = None,
        memory_budget: object = None,
    ) -> Result[GovernorBudgets]:
        """Validate declared budgets. Both are required; there is no default."""
        if isinstance(cpu_budget, GovernorBudgets):
            if memory_budget is not None:
                return invalid(
                    "budgets",
                    "a GovernorBudgets value is the complete pair; do not also pass memory_budget",
                )
            return Ok(cpu_budget)
        if isinstance(cpu_budget, Mapping):
            if memory_budget is not None:
                return invalid(
                    "budgets",
                    "a mapping already carries both budgets; do not also pass memory_budget",
                )
            mapping = cast("Mapping[object, object]", cpu_budget)
            return cls.try_create(
                _mapping_value(mapping, CPU_BUDGET_KEY, "cpu_budget"),
                _mapping_value(mapping, MEMORY_BUDGET_KEY, "memory_budget"),
            )
        cpu = _positive_int(CPU_BUDGET_KEY, cpu_budget)
        if is_refusal(cpu):
            return cpu
        memory = _positive_int(MEMORY_BUDGET_KEY, memory_budget)
        if is_refusal(memory):
            return memory
        return Ok(cls(cpu_budget=cpu.value, memory_budget=memory.value))


@dataclass(frozen=True, slots=True)
class GovernedRequest:
    """One run's declared CPU-slot cost and projected peak memory."""

    run_id: Fingerprint
    projected_peak_memory: int
    cpu_cost: int = 1

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        return {
            "cpu_cost": self.cpu_cost,
            "projected_peak_memory": self.projected_peak_memory,
            "run_id": self.run_id.value,
        }

    @classmethod
    def try_create(
        cls,
        run_id: object,
        projected_peak_memory: object,
        cpu_cost: object = 1,
    ) -> Result[GovernedRequest]:
        """Validate a per-run projection. Peak and cpu cost are positive integers."""
        parsed_id = _as_run_id(run_id)
        if is_refusal(parsed_id):
            return parsed_id
        peak = _positive_int("projected_peak_memory", projected_peak_memory)
        if is_refusal(peak):
            return peak
        cost = _positive_int("cpu_cost", cpu_cost)
        if is_refusal(cost):
            return cost
        return Ok(
            cls(
                run_id=parsed_id.value,
                projected_peak_memory=peak.value,
                cpu_cost=cost.value,
            )
        )


@dataclass(frozen=True, slots=True)
class Admission:
    """The governor's decision for one submit or a newly admitted queued run."""

    decision: str
    run_id: Fingerprint
    remaining_cpu: int
    remaining_memory: int
    reserved_cpu: int
    reserved_memory: int
    queue_depth: int
    limiting_factor: str

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        return {
            "bound": _BOUND,
            "cpu_budget_key": CPU_BUDGET_KEY,
            "decision": self.decision,
            "limiting_factor": self.limiting_factor,
            "memory_budget_key": MEMORY_BUDGET_KEY,
            "queue_depth": self.queue_depth,
            "remaining_cpu": self.remaining_cpu,
            "remaining_memory": self.remaining_memory,
            "reserved_cpu": self.reserved_cpu,
            "reserved_memory": self.reserved_memory,
            "run_id": self.run_id.value,
        }


class ResourceGovernor:
    """Instance-owned admission state. Never module-global (DEC-0161, AD-15).

    Holds the reserved running set and the FIFO enqueue-on-full queue. One
    instance per orchestrator; two instances never share a queue.
    """

    __slots__ = ("_budgets", "_on_full", "_queue", "_running")

    def __init__(self, budgets: GovernorBudgets, on_full: str) -> None:
        self._budgets = budgets
        self._on_full = on_full
        self._running: dict[str, GovernedRequest] = {}
        self._queue: list[GovernedRequest] = []

    @classmethod
    def try_create(
        cls,
        cpu_budget: object = None,
        memory_budget: object = None,
        *,
        budgets: object = None,
        on_full: object = ON_FULL_ENQUEUE,
    ) -> Result[ResourceGovernor]:
        """Bind declared budgets. ``on_full`` is ``enqueue`` (default) or ``refuse``."""
        token = _on_full_token(on_full)
        if is_refusal(token):
            return token
        parsed = _resolve_budgets(cpu_budget, memory_budget, budgets)
        if is_refusal(parsed):
            return parsed
        return Ok(cls(parsed.value, token.value))

    @property
    def budgets(self) -> GovernorBudgets:
        """The declared-per-machine budgets this governor was constructed with."""
        return self._budgets

    @property
    def on_full(self) -> str:
        """``enqueue`` or ``refuse`` when remaining min(cpu, memory) is insufficient."""
        return self._on_full

    @property
    def running(self) -> tuple[GovernedRequest, ...]:
        """Currently admitted (reserved) runs, in admission order."""
        return tuple(self._running.values())

    @property
    def queued(self) -> tuple[GovernedRequest, ...]:
        """FIFO queue of runs waiting for remaining budget (enqueue-on-full)."""
        return tuple(self._queue)

    @property
    def running_count(self) -> int:
        """Number of currently admitted runs."""
        return len(self._running)

    @property
    def queue_depth(self) -> int:
        """Number of runs waiting for a finish-then-admit."""
        return len(self._queue)

    @property
    def reserved_cpu(self) -> int:
        """CPU slots held by currently admitted runs."""
        return sum(item.cpu_cost for item in self._running.values())

    @property
    def reserved_memory(self) -> int:
        """Projected peak memory reserved by currently admitted runs."""
        return sum(item.projected_peak_memory for item in self._running.values())

    @property
    def remaining_cpu(self) -> int:
        """CPU slots still free under the declared cpu budget."""
        return self._budgets.cpu_budget - self.reserved_cpu

    @property
    def remaining_memory(self) -> int:
        """Bytes still free under the declared memory budget."""
        return self._budgets.memory_budget - self.reserved_memory

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        content = governor_identity()
        content["on_full"] = self._on_full
        content["queue_depth"] = self.queue_depth
        content["remaining_cpu"] = self.remaining_cpu
        content["remaining_memory"] = self.remaining_memory
        content["reserved_cpu"] = self.reserved_cpu
        content["reserved_memory"] = self.reserved_memory
        content["running_count"] = self.running_count
        return content

    def parallelism_bound(
        self,
        projected_peak_memory: object,
        cpu_cost: object = 1,
    ) -> Result[int]:
        """Homogeneous concurrent-run cap: ``min(cpu slots, memory slots)``."""
        return self._budgets.parallelism_bound(projected_peak_memory, cpu_cost)

    def submit(self, request: object) -> Result[Admission]:
        """Admit, enqueue, or refuse one run. Never silently oversubscribe (FM-6)."""
        parsed = _as_request(request)
        if is_refusal(parsed):
            return parsed
        item = parsed.value
        token = item.run_id.value
        if token in self._running or any(queued.run_id.value == token for queued in self._queue):
            return policy(
                "run_id",
                "the governor never admits two live reservations for one run id",
                run_id=token,
                cpu_budget_key=CPU_BUDGET_KEY,
                memory_budget_key=MEMORY_BUDGET_KEY,
            )
        if not self._fits_total(item):
            return _never_fits(item, self._budgets)
        if self._fits_remaining(item):
            self._running[token] = item
            return Ok(self._admission(DECISION_ADMITTED, item.run_id))
        if self._on_full == ON_FULL_REFUSE:
            return _remaining_refusal(item, self)
        self._queue.append(item)
        return Ok(self._admission(DECISION_QUEUED, item.run_id))

    def release(self, run_id: object) -> Result[tuple[Admission, ...]]:
        """Free a finished run's reservation, then admit the next queued run(s).

        FIFO: the head of the queue is admitted when it fits remaining
        ``min(cpu, memory)``; a later job is not skipped ahead of a head that
        still does not fit.
        """
        parsed = _as_run_id(run_id)
        if is_refusal(parsed):
            return parsed
        token = parsed.value.value
        if token not in self._running:
            return invalid(
                "run_id",
                "release finishes an admitted run; this run id is not reserved",
                run_id=token,
            )
        del self._running[token]
        admitted: list[Admission] = []
        while self._queue:
            head = self._queue[0]
            if not self._fits_remaining(head):
                break
            self._queue.pop(0)
            self._running[head.run_id.value] = head
            admitted.append(self._admission(DECISION_ADMITTED, head.run_id))
        return Ok(tuple(admitted))

    def _fits_total(self, item: GovernedRequest) -> bool:
        return (
            item.cpu_cost <= self._budgets.cpu_budget
            and item.projected_peak_memory <= self._budgets.memory_budget
        )

    def _fits_remaining(self, item: GovernedRequest) -> bool:
        return (
            self.reserved_cpu + item.cpu_cost <= self._budgets.cpu_budget
            and self.reserved_memory + item.projected_peak_memory <= self._budgets.memory_budget
        )

    def _admission(self, decision: str, run_id: Fingerprint) -> Admission:
        return Admission(
            decision=decision,
            run_id=run_id,
            remaining_cpu=self.remaining_cpu,
            remaining_memory=self.remaining_memory,
            reserved_cpu=self.reserved_cpu,
            reserved_memory=self.reserved_memory,
            queue_depth=self.queue_depth,
            limiting_factor=_limiting_factor(self),
        )


def _resolve_budgets(
    cpu_budget: object,
    memory_budget: object,
    budgets: object,
) -> Result[GovernorBudgets]:
    if budgets is not None:
        if cpu_budget is not None or memory_budget is not None:
            return invalid(
                "budgets",
                "pass GovernorBudgets or cpu_budget and memory_budget, not both",
            )
        return GovernorBudgets.try_create(budgets)
    return GovernorBudgets.try_create(cpu_budget, memory_budget)


def _on_full_token(value: object) -> Result[str]:
    if value is None:
        return Ok(ON_FULL_ENQUEUE)
    if not isinstance(value, str) or value not in _ON_FULL_VALUES:
        return invalid(
            "on_full",
            "on_full is enqueue (enqueue-on-full) or refuse (typed refusal); "
            "never silent oversubscription (B-5, FM-6)",
            given=repr(value),
            allowed=(ON_FULL_ENQUEUE, ON_FULL_REFUSE),
        )
    return Ok(value)


def _as_request(value: object) -> Result[GovernedRequest]:
    if isinstance(value, GovernedRequest):
        return Ok(value)
    if not isinstance(value, Mapping):
        return invalid(
            "request",
            "submit takes a GovernedRequest or a mapping with run_id and projected_peak_memory",
            given=repr(type(value).__name__),
        )
    mapping = cast("Mapping[str, object]", value)
    return GovernedRequest.try_create(
        mapping.get("run_id"),
        mapping.get("projected_peak_memory"),
        mapping.get("cpu_cost", 1),
    )


def _as_run_id(value: object) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    if isinstance(value, str):
        return Fingerprint.try_create(value)
    return invalid(
        "run_id",
        "the run id is the resolved-config fingerprint",
        given=repr(type(value).__name__),
    )


def _mapping_value(mapping: Mapping[object, object], key: str, alias: str) -> object:
    if key in mapping:
        return mapping[key]
    if alias in mapping:
        return mapping[alias]
    return None


def _positive_int(field: str, value: object) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        reason = (
            "qmb_governor_cpu_budget is a positive declared-per-machine count "
            "(no spine default; 12-14 concurrent is a motivating reference, "
            "never a validated budget)"
            if field == CPU_BUDGET_KEY
            else (
                "qmb_governor_memory_budget is a positive declared-per-machine "
                "byte count (no spine default)"
                if field == MEMORY_BUDGET_KEY
                else "a governor quantity is a positive integer declared by the caller"
            )
        )
        return invalid(
            field,
            reason,
            given=repr(value),
            cpu_budget_key=CPU_BUDGET_KEY,
            memory_budget_key=MEMORY_BUDGET_KEY,
        )
    return Ok(value)


def _limiting_factor(governor: ResourceGovernor) -> str:
    cpu_left = governor.remaining_cpu
    memory_left = governor.remaining_memory
    if cpu_left == 0 and memory_left == 0:
        return _BOUND
    if cpu_left == 0:
        return "cpu"
    if memory_left == 0:
        return "memory"
    cpu_budget = governor.budgets.cpu_budget
    memory_budget = governor.budgets.memory_budget
    if cpu_left * memory_budget <= memory_left * cpu_budget:
        return "cpu"
    return "memory"


def _never_fits(item: GovernedRequest, budgets: GovernorBudgets) -> TypedRefusal:
    memory_exceeded = item.projected_peak_memory > budgets.memory_budget
    field = "projected_peak_memory" if memory_exceeded else "cpu_cost"
    return policy(
        field,
        "a run whose projected peak exceeds the declared total "
        "min(cpu, memory) budget can never be admitted; enqueue-on-full "
        "does not apply (B-5, FM-6)",
        cpu_budget=budgets.cpu_budget,
        cpu_budget_key=CPU_BUDGET_KEY,
        cpu_cost=item.cpu_cost,
        memory_budget=budgets.memory_budget,
        memory_budget_key=MEMORY_BUDGET_KEY,
        projected_peak_memory=item.projected_peak_memory,
        run_id=item.run_id.value,
        retryability=Retryability.NO.value,
    )


def _remaining_refusal(item: GovernedRequest, governor: ResourceGovernor) -> TypedRefusal:
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.AFTER_CONDITION,
        context={
            "field": "remaining_budget",
            "reason": (
                "projected peak exceeds remaining min(cpu, memory) budget; "
                "on_full=refuse so this is a typed refusal, never silent "
                "oversubscription (B-5, FM-6)"
            ),
            "cpu_budget_key": CPU_BUDGET_KEY,
            "cpu_cost": item.cpu_cost,
            "limiting_factor": _limiting_factor(governor),
            "memory_budget_key": MEMORY_BUDGET_KEY,
            "on_full": ON_FULL_REFUSE,
            "projected_peak_memory": item.projected_peak_memory,
            "remaining_cpu": governor.remaining_cpu,
            "remaining_memory": governor.remaining_memory,
            "run_id": item.run_id.value,
        },
        after_condition_descriptor=_AFTER_FINISH,
    )
