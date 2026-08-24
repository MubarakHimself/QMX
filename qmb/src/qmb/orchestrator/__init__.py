"""Impure composition root: process spawn, governor, sinks, WriterId (B-4/B-5).

The library's ``run()`` is a pure function: it writes no log and no ledger.
This module is the one impure owner of injected sinks, process-per-run
spawn, the ``min(cpu, memory)`` governor, and OS-process abort on cancel or
per-run limit breach. The library never holds module-global mutable state
(DEC-0161).
"""

from __future__ import annotations

from typing import Final

from qmb.orchestrator.governor import (
    CPU_BUDGET_KEY,
    DECISION_ADMITTED,
    DECISION_QUEUED,
    MEMORY_BUDGET_KEY,
    ON_FULL_ENQUEUE,
    ON_FULL_REFUSE,
    SANDBOX_CONCURRENT_MOTIVATING_REFERENCE,
    Admission,
    GovernedRequest,
    GovernorBudgets,
    ResourceGovernor,
    governor_identity,
)
from qmb.orchestrator.spawn import (
    DAEMON,
    DOCKER,
    ONE_WRITER_PER_STREAM,
    PAYLOAD_NAME,
    PROCESS_MANAGEMENT,
    RAY,
    RESULT_NAME,
    WRITER_NAME,
    IsolatedRun,
    LiveSpawn,
    ProcessLimitProbe,
    SpawnJob,
    abort_run,
    collect_run,
    run_directory_name,
    spawn_concurrent,
    spawn_governed,
    spawn_run,
    start_run,
    worker_main,
)
from qmb.orchestrator.watch import (
    ABORT_KILLS_SIBLINGS,
    ENFORCEMENT,
)
from qmb.runloop.observe import (
    MEMORY_LIMIT_KEY,
    PARTIAL_GOVERNED_RESULT_ON_ABORT,
    TIME_LIMIT_KEY,
)

__all__ = [
    "ABORT_KILLS_SIBLINGS",
    "CPU_BUDGET_KEY",
    "DAEMON",
    "DECISION_ADMITTED",
    "DECISION_QUEUED",
    "DOCKER",
    "ENFORCEMENT",
    "IMPURE_OWNER",
    "MEMORY_BUDGET_KEY",
    "ONE_WRITER_PER_STREAM",
    "ON_FULL_ENQUEUE",
    "ON_FULL_REFUSE",
    "PAYLOAD_NAME",
    "PROCESS_MANAGEMENT",
    "RAY",
    "RESULT_NAME",
    "SANDBOX_CONCURRENT_MOTIVATING_REFERENCE",
    "SPAWN_MODEL",
    "WRITER_NAME",
    "Admission",
    "GovernedRequest",
    "GovernorBudgets",
    "IsolatedRun",
    "LiveSpawn",
    "ProcessLimitProbe",
    "ResourceGovernor",
    "SpawnJob",
    "abort_run",
    "collect_run",
    "governor_identity",
    "orchestrator_identity",
    "run_directory_name",
    "spawn_concurrent",
    "spawn_governed",
    "spawn_run",
    "start_run",
    "worker_main",
]

IMPURE_OWNER: Final[str] = "orchestrator"
SPAWN_MODEL: Final[str] = "process-per-run"


def orchestrator_identity() -> dict[str, object]:
    """Identity-bearing orchestrator fields. Package SemVer is omitted."""
    identity: dict[str, object] = {
        "impure_owner": IMPURE_OWNER,
        "spawn_model": SPAWN_MODEL,
        "governor": "min-cpu-memory",
        "process_management": PROCESS_MANAGEMENT,
        "ray": RAY,
        "docker": DOCKER,
        "daemon": DAEMON,
        "one_writer_per_stream": ONE_WRITER_PER_STREAM,
        "abort_kills_siblings": ABORT_KILLS_SIBLINGS,
        "enforcement": ENFORCEMENT,
        "time_limit_key": TIME_LIMIT_KEY,
        "memory_limit_key": MEMORY_LIMIT_KEY,
        "partial_governed_result_on_abort": PARTIAL_GOVERNED_RESULT_ON_ABORT,
        "cancel_token": True,
    }
    identity.update(governor_identity())
    return identity
