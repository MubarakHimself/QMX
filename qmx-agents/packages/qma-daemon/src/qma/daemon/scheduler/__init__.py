"""Routines, cron, continuation budget and escalation (AD-29).

Task Graph scheduling and ``dispatch_lease`` / ``environment_lease`` evaluation
for FR-Q27 live in ``qma.daemon.taskgraph`` (AD-12). Quant ``WakePolicy``
evaluation at mailbox delivery time lives here (AD-20; FR-Q61). Quant-owned
Routines fire deterministically from this package (AD-29; FR-Q62). Agent-run
continuation stays inside the three registry bounds (AD-29; FR-Q63).
"""

from __future__ import annotations

from qma.daemon.scheduler.continuation import (
    CONTINUATION_BOUND_KEYS,
    CONTINUATION_BUDGET_KEY,
    CONTINUATION_ESCALATION_TARGET_KEY,
    CONTINUATION_MAX_CONSECUTIVE_KEY,
    AgentContinuation,
    AgentRunState,
    AgentStopOutcome,
    TaskCompletionVerdict,
)
from qma.daemon.scheduler.cron import (
    due_instants,
    next_occurrence_after,
    slot_end_ns,
    validate_schedule_zone,
)
from qma.daemon.scheduler.routines import (
    AUTOMATIC_BACKFILL,
    MAX_CONCURRENT_REGISTRY_KEY,
    MISSED_FIRE_DISPOSITION,
    ROUTINE_CATCH_UP_COMMAND,
    ROUTINE_FIRE_PRINCIPAL,
    ROUTINE_RECORDS_FOLD_ID,
    ROUTINE_RECORDS_STORE_NAME,
    ROUTINE_WRITE_COMMAND,
    CatchUpResult,
    MissedFire,
    RoutineFire,
    RoutineScheduler,
    RoutineTickResult,
    machine_principal_may_answer_human_gate,
)
from qma.daemon.scheduler.wake import (
    WAKE_EXEMPTIONS,
    WakeDecision,
    WakeExemption,
    civil_window_id,
    evaluate_delivery_wake,
    in_quiet_hours,
    next_quiet_hours_end,
    resolve_iana_zone,
    routine_fire_suppressed_by_quiet_hours,
    running_agent_paused_by_quiet_hours,
)

__all__ = [
    "AUTOMATIC_BACKFILL",
    "CONTINUATION_BOUND_KEYS",
    "CONTINUATION_BUDGET_KEY",
    "CONTINUATION_ESCALATION_TARGET_KEY",
    "CONTINUATION_MAX_CONSECUTIVE_KEY",
    "MAX_CONCURRENT_REGISTRY_KEY",
    "MISSED_FIRE_DISPOSITION",
    "ROUTINE_CATCH_UP_COMMAND",
    "ROUTINE_FIRE_PRINCIPAL",
    "ROUTINE_RECORDS_FOLD_ID",
    "ROUTINE_RECORDS_STORE_NAME",
    "ROUTINE_WRITE_COMMAND",
    "WAKE_EXEMPTIONS",
    "AgentContinuation",
    "AgentRunState",
    "AgentStopOutcome",
    "CatchUpResult",
    "MissedFire",
    "RoutineFire",
    "RoutineScheduler",
    "RoutineTickResult",
    "TaskCompletionVerdict",
    "WakeDecision",
    "WakeExemption",
    "civil_window_id",
    "due_instants",
    "evaluate_delivery_wake",
    "in_quiet_hours",
    "machine_principal_may_answer_human_gate",
    "next_occurrence_after",
    "next_quiet_hours_end",
    "resolve_iana_zone",
    "routine_fire_suppressed_by_quiet_hours",
    "running_agent_paused_by_quiet_hours",
    "slot_end_ns",
    "validate_schedule_zone",
]
