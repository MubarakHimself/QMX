"""Exhaustive closed vocabulary members declared in qma-core (FR-Q08)."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Final

__all__ = [
    "JOB_HANDLE_NONTERMINAL_STATES",
    "JOB_HANDLE_TERMINAL_STATES",
    "JOB_HANDLE_TO_TASK_STATE",
    "TASK_EMITTING_NODE_KINDS",
    "TASK_MISSION_NONTERMINAL_STATES",
    "TASK_MISSION_TERMINAL_STATES",
    "AskOnTimeout",
    "DeliveryState",
    "EnvironmentLifecycle",
    "ExecutionEnvironmentKind",
    "GovernedAct",
    "GraphArtifactKind",
    "HandleKind",
    "HookControl",
    "HookResultDecision",
    "HookVerb",
    "IsolationMode",
    "JobHandleState",
    "MemoryValidationState",
    "MessageKind",
    "ModelClass",
    "NetworkPolicy",
    "NodeKind",
    "PrincipalClass",
    "RefinementEditKind",
    "RoutingPolicy",
    "SessionAutonomy",
    "TaskMissionState",
    "VariableEditability",
    "VariableScope",
    "is_job_handle_terminal",
    "is_task_mission_terminal",
    "map_job_handle_to_task_state",
]


class HookVerb(StrEnum):
    """Twenty-three daemon-owned hook verbs (AD-10; DEC-0309).

    Each ships ``before_<verb>`` and ``after_<verb>`` events.
    """

    TOOL = "tool"
    TASK_CREATE = "task_create"
    TASK_COMPLETE = "task_complete"
    LEDGER_APPEND = "ledger_append"
    MEMORY_WRITE = "memory_write"
    SKILL_WRITE = "skill_write"
    ARTIFACT_REGISTER = "artifact_register"
    EXPERIMENT_REGISTER = "experiment_register"
    ENV_CREATE = "env_create"
    ENV_REMOVE = "env_remove"
    SUBAGENT_SPAWN = "subagent_spawn"
    MESSAGE_SEND = "message_send"
    GRAPH_TRANSITION = "graph_transition"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    MISSION_START = "mission_start"
    MISSION_COMPLETE = "mission_complete"
    PLUGIN_ACTIVATE = "plugin_activate"
    PLUGIN_DEACTIVATE = "plugin_deactivate"
    ROUTINE_FIRE = "routine_fire"
    HOOK_REGISTER = "hook_register"
    PROPOSAL_STAGE = "proposal_stage"
    PROPOSAL_APPLY = "proposal_apply"


class HookControl(StrEnum):
    """Phase-less blocking controls; only these two (AD-10; DEC-0309)."""

    AGENT_STOP = "agent_stop"
    REVIEW_REQUIRED = "review_required"


class HookResultDecision(StrEnum):
    """Six HookResult decisions in total precedence order (AD-10; DEC-0309).

    Precedence: ``block_stop > deny > defer > ask > allow > observe``.
    """

    BLOCK_STOP = "block_stop"
    DENY = "deny"
    DEFER = "defer"
    ASK = "ask"
    ALLOW = "allow"
    OBSERVE = "observe"


class HandleKind(StrEnum):
    """Six handle kinds; never extended by a plugin (AD-14; DEC-0313).

    Serialized as CamelCase type names. No kind identifies a live or writable
    money-path record: ``TradeLogHandle`` and ``MarketDataHandle`` address
    recorded read-only evidence only; ``StrategyHandle`` may mint only
    content-addressed dev-zone candidates.
    """

    BACKTEST_HANDLE = "BacktestHandle"
    EXPERIMENT_HANDLE = "ExperimentHandle"
    TRADE_LOG_HANDLE = "TradeLogHandle"
    STRATEGY_HANDLE = "StrategyHandle"
    KNOWLEDGE_HANDLE = "KnowledgeHandle"
    MARKET_DATA_HANDLE = "MarketDataHandle"


class JobHandleState(StrEnum):
    """Seven JobHandle states (AD-17; DEC-0316).

    Terminal states: ``done``, ``failed``, ``cancelled``, ``aborted``.
    """

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ABORTED = "aborted"
    UNKNOWN = "unknown"


class TaskMissionState(StrEnum):
    """Eight Task and Mission states (AD-12; DEC-0311).

    Terminal states: ``done``, ``failed``, ``cancelled``.
    """

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


JOB_HANDLE_TERMINAL_STATES: Final[frozenset[JobHandleState]] = frozenset(
    {
        JobHandleState.DONE,
        JobHandleState.FAILED,
        JobHandleState.CANCELLED,
        JobHandleState.ABORTED,
    }
)
JOB_HANDLE_NONTERMINAL_STATES: Final[frozenset[JobHandleState]] = frozenset(
    {
        JobHandleState.QUEUED,
        JobHandleState.RUNNING,
        JobHandleState.UNKNOWN,
    }
)
TASK_MISSION_TERMINAL_STATES: Final[frozenset[TaskMissionState]] = frozenset(
    {
        TaskMissionState.DONE,
        TaskMissionState.FAILED,
        TaskMissionState.CANCELLED,
    }
)
TASK_MISSION_NONTERMINAL_STATES: Final[frozenset[TaskMissionState]] = frozenset(
    {
        TaskMissionState.PENDING,
        TaskMissionState.READY,
        TaskMissionState.RUNNING,
        TaskMissionState.BLOCKED,
        TaskMissionState.UNKNOWN,
    }
)

# Fixed, total JobHandle → Task mapping applied by the daemon alone (DEC-0316).
JOB_HANDLE_TO_TASK_STATE: Final[Mapping[JobHandleState, TaskMissionState]] = MappingProxyType(
    {
        JobHandleState.QUEUED: TaskMissionState.RUNNING,
        JobHandleState.RUNNING: TaskMissionState.RUNNING,
        JobHandleState.DONE: TaskMissionState.DONE,
        JobHandleState.FAILED: TaskMissionState.FAILED,
        JobHandleState.ABORTED: TaskMissionState.FAILED,
        JobHandleState.CANCELLED: TaskMissionState.CANCELLED,
        JobHandleState.UNKNOWN: TaskMissionState.UNKNOWN,
    }
)


def is_job_handle_terminal(state: JobHandleState) -> bool:
    """True when ``state`` is a JobHandle terminal outcome (DEC-0316)."""
    return state in JOB_HANDLE_TERMINAL_STATES


def is_task_mission_terminal(state: TaskMissionState) -> bool:
    """True when ``state`` is a Task/Mission terminal outcome (DEC-0311)."""
    return state in TASK_MISSION_TERMINAL_STATES


def map_job_handle_to_task_state(state: JobHandleState) -> TaskMissionState:
    """Map a JobHandle state onto the closed Task state vocabulary (DEC-0316).

    ``aborted`` maps to Task ``failed`` (reason recorded by the daemon caller);
    ``aborted`` never becomes Task ``cancelled``.
    """
    return JOB_HANDLE_TO_TASK_STATE[state]


class MessageKind(StrEnum):
    """Seven mailbox MessageKind values (AD-20; DEC-0319)."""

    HANDOFF = "handoff"
    REPLY = "reply"
    NOTIFY = "notify"
    REVIEW_REQUEST = "review_request"
    STATUS = "status"
    QUESTION = "question"
    APPROVAL_REQUEST = "approval_request"


class DeliveryState(StrEnum):
    """Five DeliveryState values (AD-20; DEC-0319)."""

    DELIVERED = "delivered"
    QUEUED = "queued"
    WOKE = "woke"
    DEFERRED = "deferred"
    DEAD_LETTER = "dead_letter"


class ModelClass(StrEnum):
    """Four ModelClass values; SCREAMING_SNAKE wire form (AD-15; DEC-0314)."""

    REASONING_HIGH = "REASONING_HIGH"
    WORKHORSE_GENERAL = "WORKHORSE_GENERAL"
    CODING_HIGH = "CODING_HIGH"
    FAST_CHEAP = "FAST_CHEAP"


class RoutingPolicy(StrEnum):
    """Four routing policies (AD-15; DEC-0314)."""

    FAILOVER = "failover"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    QUOTA_LOWEST = "quota_lowest"
    FILL_FIRST = "fill_first"


class PrincipalClass(StrEnum):
    """Authenticated connection class: operator or machine only (AD-24; DEC-0323).

    A ``machine`` principal may never acquire, borrow, cache, or impersonate
    ``operator``.
    """

    OPERATOR = "operator"
    MACHINE = "machine"


class SessionAutonomy(StrEnum):
    """Session autonomy axis values (AD-14; DEC-0313).

    Durable Session record axis only — attachment is never persisted.
    """

    INTERACTIVE = "interactive"
    SEMI = "semi"
    AUTONOMOUS = "autonomous"


class AskOnTimeout(StrEnum):
    """Mission ``on_timeout`` disposition for an ``ask`` (AD-10; DEC-0309)."""

    DENY = "deny"
    ESCALATE = "escalate"


class MemoryValidationState(StrEnum):
    """Seven memory validation_state values (AD-18; DEC-0317)."""

    PROPOSED = "proposed"
    VALIDATED = "validated"
    ADMITTED = "admitted"
    SUPERSEDED = "superseded"
    INVALIDATED = "invalidated"
    EXPIRED = "expired"
    CONTRADICTED = "contradicted"


class NodeKind(StrEnum):
    """Ten Graph Template / Task Graph node kinds (AD-13; DEC-0312)."""

    TASK = "task"
    CONDITIONAL = "conditional"
    PARALLEL_BRANCH = "parallel_branch"
    JOIN = "join"
    APPROVAL_GATE = "approval_gate"
    HUMAN_GATE = "human_gate"
    DETERMINISTIC_SCRIPT = "deterministic_script"
    LOOP = "loop"
    AGENT = "agent"
    ARTIFACT_DEPENDENCY = "artifact_dependency"


TASK_EMITTING_NODE_KINDS: Final[frozenset[NodeKind]] = frozenset(
    {NodeKind.TASK, NodeKind.AGENT, NodeKind.LOOP}
)


class ExecutionEnvironmentKind(StrEnum):
    """Six ExecutionEnvironment kinds (AD-17; DEC-0316)."""

    LOCAL = "local"
    DOCKER = "docker"
    REMOTE_CONTAINER = "remote_container"
    REMOTE_HOST = "remote_host"
    BROWSER = "browser"
    DESKTOP = "desktop"


class NetworkPolicy(StrEnum):
    """Exactly two network values; no open default (AD-28; DEC-0327)."""

    NONE = "none"
    ALLOWLIST = "allowlist"


class EnvironmentLifecycle(StrEnum):
    """ExecutionEnvironment lifetime; docker-per-worker defaults to ephemeral (AD-17)."""

    EPHEMERAL = "ephemeral"
    PERSISTENT = "persistent"


class IsolationMode(StrEnum):
    """ComputeRequirement isolation; default ``required`` (AD-17; DEC-0316)."""

    REQUIRED = "required"
    SHARED = "shared"


class RefinementEditKind(StrEnum):
    """Nine RefinementProposal edit kinds; no ``variable`` kind (AD-22; DEC-0321)."""

    PROMPT = "prompt"
    MEMORY = "memory"
    SKILL = "skill"
    TOOLSET = "toolset"
    WORKER_TEMPLATE = "worker_template"
    HOOK = "hook"
    GRAPH_TEMPLATE = "graph_template"
    LOOP = "loop"
    ROLE = "role"


class VariableScope(StrEnum):
    """Eight configurable-variable scopes (AD-26; DEC-0325)."""

    GLOBAL = "global"
    DESK = "desk"
    ROLE = "role"
    QUANT = "quant"
    MISSION = "mission"
    PLUGIN = "plugin"
    EXECUTION_ENVIRONMENT = "execution_environment"
    ROUTINE = "routine"


class VariableEditability(StrEnum):
    """Exactly one editability flag per registered variable (AD-26; DEC-0325).

    ``ui-editable`` means configurable in the platform UI. ``uneditable`` is a
    recorded constant — never a ``variable.set`` target.
    """

    UI_EDITABLE = "ui-editable"
    UNEDITABLE = "uneditable"


class GraphArtifactKind(StrEnum):
    """Graph Template (authored, stateless) versus Task Graph (daemon state).

    Never interchanged (AD-13; DEC-0312).
    """

    GRAPH_TEMPLATE = "graph_template"
    TASK_GRAPH = "task_graph"


class GovernedAct(StrEnum):
    """Three closed verbs naming distinct acts (AD-18/22/25; DEC-0345).

    Memory candidates are admitted; RefinementProposals are applied; only a
    human outside QMA promotes a registered artifact into the live zone.
    """

    ADMIT = "admit"
    APPLY = "apply"
    PROMOTE = "promote"
