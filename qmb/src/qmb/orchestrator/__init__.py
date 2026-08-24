"""Impure composition root: process spawn, governor, sinks, WriterId (B-4/B-5).

The library's ``run()`` is a pure function: it writes no log and no ledger.
This module is the one impure owner of injected sinks, process-per-run
spawn, and the ``min(cpu, memory)`` governor. The library never holds
module-global mutable state (DEC-0161).
"""

from __future__ import annotations

from typing import Final

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
    SpawnJob,
    collect_run,
    run_directory_name,
    spawn_concurrent,
    spawn_run,
    start_run,
    worker_main,
)

__all__ = [
    "DAEMON",
    "DOCKER",
    "IMPURE_OWNER",
    "ONE_WRITER_PER_STREAM",
    "PAYLOAD_NAME",
    "PROCESS_MANAGEMENT",
    "RAY",
    "RESULT_NAME",
    "SPAWN_MODEL",
    "WRITER_NAME",
    "IsolatedRun",
    "LiveSpawn",
    "SpawnJob",
    "collect_run",
    "orchestrator_identity",
    "run_directory_name",
    "spawn_concurrent",
    "spawn_run",
    "start_run",
    "worker_main",
]

IMPURE_OWNER: Final[str] = "orchestrator"
SPAWN_MODEL: Final[str] = "process-per-run"


def orchestrator_identity() -> dict[str, object]:
    """Identity-bearing orchestrator fields. Package SemVer is omitted."""
    return {
        "impure_owner": IMPURE_OWNER,
        "spawn_model": SPAWN_MODEL,
        "governor": "min-cpu-memory",
        "process_management": PROCESS_MANAGEMENT,
        "ray": RAY,
        "docker": DOCKER,
        "daemon": DAEMON,
        "one_writer_per_stream": ONE_WRITER_PER_STREAM,
    }
