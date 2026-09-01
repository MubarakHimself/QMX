"""Closed-and-addable wire packet vocabulary (CT-40; AD-5; DEC-0304; FR-Q21).

Ownership of every command, query, and event family name sits in ``qma-wire``.
New families are added only by editing this registry — never coined locally by a
client, worker, plugin, or daemon module.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

__all__ = [
    "ADDABLE_QUERY_COUNT",
    "SEED_COMMAND_COUNT",
    "SEED_EVENT_COUNT",
    "SEED_QUERY_COUNT",
    "SEED_VOCABULARY_COUNT",
    "WIRE_COMMANDS",
    "WIRE_EVENTS",
    "WIRE_QUERIES",
    "WIRE_VOCABULARY_OWNER",
    "MessageFamily",
    "WireCommand",
    "WireEvent",
    "WireQuery",
    "WireVocabularyError",
    "family_of",
    "parse_wire_type",
]


WIRE_VOCABULARY_OWNER: Final[str] = "qma-wire"

SEED_COMMAND_COUNT: Final[int] = 9
SEED_QUERY_COUNT: Final[int] = 7
SEED_EVENT_COUNT: Final[int] = 10
SEED_VOCABULARY_COUNT: Final[int] = SEED_COMMAND_COUNT + SEED_QUERY_COUNT + SEED_EVENT_COUNT
# Closed-and-addable extensions beyond the packet seed (FR-Q35; AD-11).
ADDABLE_QUERY_COUNT: Final[int] = 1


class MessageFamily(StrEnum):
    """The three wire message families (DEC-0304)."""

    COMMAND = "command"
    QUERY = "query"
    EVENT = "event"


class WireCommand(StrEnum):
    """The nine seed commands (packet nouns; DEC-0304).

    Wire ``type`` values are snake_case identifiers derived from the packet's
    English labels (``install/enable plugin`` → ``install_enable_plugin``).
    """

    START_MISSION = "start_mission"
    SEND_MESSAGE = "send_message"
    STEER_AGENT = "steer_agent"
    STOP_RUN = "stop_run"
    APPROVE_HOOK_ACTION = "approve_hook_action"
    INSTALL_ENABLE_PLUGIN = "install_enable_plugin"
    UPDATE_CONFIGURATION = "update_configuration"
    LAUNCH_TASK = "launch_task"
    RETRY_TASK = "retry_task"


class WireQuery(StrEnum):
    """Closed-and-addable queries (packet seed plus AD-11 extension).

    The seven packet-seed queries (DEC-0304, DEC-0331) plus ``list_mission_hooks``
    exposing Agent-authored Mission hook registrations (FR-Q35; AD-11). The
    packet seed ``get bot`` reads ``get_quant`` under the Bot-to-Quant rule.
    """

    GET_QUANT = "get_quant"
    LIST_MISSIONS = "list_missions"
    GET_GRAPH_STATE = "get_graph_state"
    INSPECT_LEDGER = "inspect_ledger"
    INSPECT_TRACE = "inspect_trace"
    LIST_INSTALLED_PLUGINS = "list_installed_plugins"
    GET_PROVIDER_HEALTH = "get_provider_health"
    LIST_MISSION_HOOKS = "list_mission_hooks"


class WireEvent(StrEnum):
    """The ten seed ``noun.verb`` events (DEC-0304).

    Hook control names (``before_<verb>`` / ``after_<verb>``) are not members.
    """

    AGENT_STARTED = "agent.started"
    MESSAGE_DELTA = "message.delta"
    TOOL_STARTED = "tool.started"
    TASK_COMPLETED = "task.completed"
    HOOK_BLOCKED = "hook.blocked"
    LEDGER_UPDATED = "ledger.updated"
    MISSION_UPDATED = "mission.updated"
    WORKER_DETACHED = "worker.detached"
    PROVIDER_COOLDOWN = "provider.cooldown"
    ARTIFACT_CREATED = "artifact.created"


WIRE_COMMANDS: Final[frozenset[str]] = frozenset(member.value for member in WireCommand)
WIRE_QUERIES: Final[frozenset[str]] = frozenset(member.value for member in WireQuery)
WIRE_EVENTS: Final[frozenset[str]] = frozenset(member.value for member in WireEvent)

_TYPE_TO_FAMILY: Final[dict[str, MessageFamily]] = {
    **dict.fromkeys(WIRE_COMMANDS, MessageFamily.COMMAND),
    **dict.fromkeys(WIRE_QUERIES, MessageFamily.QUERY),
    **dict.fromkeys(WIRE_EVENTS, MessageFamily.EVENT),
}


class WireVocabularyError(ValueError):
    """Raised when a wire type is not a member of the closed packet vocabulary."""


def _host_request_family(wire_type: str) -> MessageFamily | None:
    """Lazy lookup so host_request verbs ride as command/query types (AD-14)."""
    # Lazy: host_request → envelope → vocabulary; top-level import would cycle.
    from qma.wire.host_request import host_request_type_family  # noqa: PLC0415

    return host_request_type_family(wire_type)


def family_of(wire_type: str) -> MessageFamily:
    """Return the message family for a closed vocabulary member."""
    try:
        return _TYPE_TO_FAMILY[wire_type]
    except KeyError:
        host_family = _host_request_family(wire_type)
        if host_family is not None:
            return host_family
        raise WireVocabularyError(
            f"{wire_type!r} is not a member of the closed qma-wire vocabulary "
            f"(owner={WIRE_VOCABULARY_OWNER})"
        ) from None


def parse_wire_type(value: object) -> str:
    """Accept only a type declared in the closed-and-addable packet vocabulary.

    The packet seed (26 nouns) plus closed-and-addable ``host_request`` verbs
    (AD-14) are accepted; host_request verbs ride as command or query types.
    """
    if not isinstance(value, str) or not value:
        raise WireVocabularyError(f"{value!r} is not a wire message type")
    if value in _TYPE_TO_FAMILY:
        return value
    if _host_request_family(value) is not None:
        return value
    raise WireVocabularyError(
        f"{value!r} is not a member of the closed qma-wire vocabulary "
        f"(owner={WIRE_VOCABULARY_OWNER})"
    )
