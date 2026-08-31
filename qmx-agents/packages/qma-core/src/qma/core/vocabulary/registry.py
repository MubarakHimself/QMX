"""Closed-vocabulary registry metadata and parse helpers (FR-Q08)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from qma.core.vocabulary.enums import (
    DeliveryState,
    ExecutionEnvironmentKind,
    GovernedAct,
    GraphArtifactKind,
    HandleKind,
    HookControl,
    HookResultDecision,
    HookVerb,
    JobHandleState,
    MemoryValidationState,
    MessageKind,
    ModelClass,
    NetworkPolicy,
    NodeKind,
    PrincipalClass,
    RefinementEditKind,
    RoutingPolicy,
    TaskMissionState,
    VariableScope,
)

__all__ = [
    "CLOSED_VOCABULARIES",
    "HOST_REQUEST_OWNING_AD",
    "HOST_REQUEST_VOCABULARY_OWNER",
    "ClosedVocabulary",
    "VocabularyError",
    "parse_closed",
]

# host_request verb set is closed-and-addable under qma-wire (AD-14; DEC-0313).
HOST_REQUEST_VOCABULARY_OWNER: Final[str] = "qma-wire"
HOST_REQUEST_OWNING_AD: Final[str] = "AD-14"


class VocabularyError(ValueError):
    """Raised when a value is not a member of a closed QMA vocabulary."""


@dataclass(frozen=True, slots=True)
class ClosedVocabulary:
    """One closed-and-addable vocabulary with its owning architecture decision."""

    name: str
    owning_ad: str
    members: type[StrEnum]
    decision: str


CLOSED_VOCABULARIES: Final[tuple[ClosedVocabulary, ...]] = (
    ClosedVocabulary("hook_verb", "AD-10", HookVerb, "DEC-0309"),
    ClosedVocabulary("hook_control", "AD-10", HookControl, "DEC-0309"),
    ClosedVocabulary("hook_result_decision", "AD-10", HookResultDecision, "DEC-0309"),
    ClosedVocabulary("handle_kind", "AD-14", HandleKind, "DEC-0313"),
    ClosedVocabulary("job_handle_state", "AD-17", JobHandleState, "DEC-0316"),
    ClosedVocabulary("task_mission_state", "AD-12", TaskMissionState, "DEC-0311"),
    ClosedVocabulary("message_kind", "AD-20", MessageKind, "DEC-0319"),
    ClosedVocabulary("delivery_state", "AD-20", DeliveryState, "DEC-0319"),
    ClosedVocabulary("model_class", "AD-15", ModelClass, "DEC-0314"),
    ClosedVocabulary("routing_policy", "AD-15", RoutingPolicy, "DEC-0314"),
    ClosedVocabulary("principal_class", "AD-24", PrincipalClass, "DEC-0323"),
    ClosedVocabulary("memory_validation_state", "AD-18", MemoryValidationState, "DEC-0317"),
    ClosedVocabulary("node_kind", "AD-13", NodeKind, "DEC-0312"),
    ClosedVocabulary("execution_environment_kind", "AD-17", ExecutionEnvironmentKind, "DEC-0316"),
    ClosedVocabulary("network_policy", "AD-28", NetworkPolicy, "DEC-0327"),
    ClosedVocabulary("refinement_edit_kind", "AD-22", RefinementEditKind, "DEC-0321"),
    ClosedVocabulary("variable_scope", "AD-26", VariableScope, "DEC-0325"),
    ClosedVocabulary("graph_artifact_kind", "AD-13", GraphArtifactKind, "DEC-0312"),
    ClosedVocabulary("governed_act", "AD-18", GovernedAct, "DEC-0345"),
)


def parse_closed[EnumT: StrEnum](enum_type: type[EnumT], value: object) -> EnumT:
    """Parse ``value`` as a member of ``enum_type``; inventing a value fails."""
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        try:
            return enum_type(value)
        except ValueError as exc:
            raise VocabularyError(
                f"{value!r} is not a member of closed vocabulary {enum_type.__name__}"
            ) from exc
    raise VocabularyError(f"{value!r} is not a member of closed vocabulary {enum_type.__name__}")
