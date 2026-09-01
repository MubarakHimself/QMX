"""Loop-and-state contract, session axes, and runtime scoping (AD-14; FR-Q52).

One daemon-owned loop-and-state contract with two implementations:

* **Dialogue Runtime** — available to every desk.
* **RLM Runtime v1** — scoped by desk to Analysis (``analysis-*``), never by
  Role. Analyst is the Role; Analysis is the desk.

The RLM kernel is a persistent Python interpreter inside the worker's Docker
container. Host calls use the typed ``qma-wire`` ``host_request`` family, never
a second channel. Spawn depth cites ``registry:rlm.depth_cap``.

Durable Session records carry execution-model and autonomy only. Attachment is
client state. There is no separate background-session type.

Definitions only — the daemon implements both runtimes.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from qma.core.ontology.actor_id import ActorId
from qma.core.ontology.desks import DESK_SLUG_VALUES, DeskSlug
from qma.core.ontology.records import Quant, Session
from qma.core.vocabulary.enums import ExecutionModel, SessionAttachment, SessionAutonomy
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "ANALYSIS_NOTEBOOK_TOOL_ID",
    "BACKGROUND_SESSION_TYPES",
    "CLIENT_SESSION_AXIS",
    "DEFERRED_RUNTIME_EXCLUSIONS",
    "DIALOGUE_RUNTIME_DESKS",
    "DURABLE_SESSION_AXES",
    "HOSTED_NOTEBOOK_SERVICES",
    "LOOP_AND_STATE_CONTRACT",
    "LOOP_AND_STATE_SURFACES",
    "RLM_DEPTH_CAP_REGISTRY_KEY",
    "RLM_HOST_TRANSPORT",
    "RLM_KERNEL_INTERPRETER",
    "RLM_KERNEL_PLACEMENT",
    "RLM_RUNTIME_DESK",
    "available_execution_models",
    "durable_session_payload",
    "is_analysis_desk",
    "is_rlm_runtime_in_scope",
    "mint_durable_session",
    "parse_session_attachment",
    "select_execution_model",
]


LOOP_AND_STATE_CONTRACT: Final[str] = "daemon-owned-loop-and-state"

# Both runtimes share these daemon-owned surfaces (DEC-0313). Compaction remains
# a named shared surface; its implementation is a separate deferred row.
LOOP_AND_STATE_SURFACES: Final[tuple[str, ...]] = (
    "model_proxy",
    "credential_broker",
    "tool_registry",
    "capability_registry",
    "hooks",
    "policy",
    "ledgers",
    "memory",
    "knowledge",
    "context_compiler",
    "compaction",
    "mission",
    "task_graph",
    "compute_router",
    "agent_bus",
    "telemetry",
)

DIALOGUE_RUNTIME_DESKS: Final[frozenset[str]] = DESK_SLUG_VALUES
RLM_RUNTIME_DESK: Final[DeskSlug] = DeskSlug.ANALYSIS

RLM_KERNEL_INTERPRETER: Final[str] = "persistent_python"
RLM_KERNEL_PLACEMENT: Final[str] = "worker_docker_container"
RLM_HOST_TRANSPORT: Final[str] = "qma-wire"
RLM_DEPTH_CAP_REGISTRY_KEY: Final[str] = "registry:rlm.depth_cap"

DURABLE_SESSION_AXES: Final[tuple[str, ...]] = ("execution_model", "autonomy")
CLIENT_SESSION_AXIS: Final[str] = "attachment"

# Invented session kinds are refused — detached + autonomous is not a type.
BACKGROUND_SESSION_TYPES: Final[frozenset[str]] = frozenset(
    {
        "background",
        "background_session",
        "bg",
        "batch_session",
    }
)

ANALYSIS_NOTEBOOK_TOOL_ID: Final[str] = "qma-inhouse:analysis-notebook"
HOSTED_NOTEBOOK_SERVICES: Final[frozenset[str]] = frozenset(
    {
        "colab",
        "google_colab",
        "hosted_jupyter",
        "jupyterhub_saas",
        "sagemaker_studio",
        "databricks_notebook",
        "kaggle_notebook",
    }
)

# Explicit Deferred exclusions — never invent implementations here (FR-Q52).
DEFERRED_RUNTIME_EXCLUSIONS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "GAP-0080": (
            "RLM beyond the Analysis desk and spawn depth above registry:rlm.depth_cap — deferred"
        ),
        "GAP-0076": "RLM kernel performance envelope — deferred measurement obligation",
        "GAP-0075": (
            "sandbox and compute vendors beyond local Docker "
            "(remote_container; desktop beyond the planned VPS) — deferred"
        ),
        "GAP-0078": "browser stack for browser-heavy missions — deferred",
    }
)


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


def is_analysis_desk(desk: object) -> bool:
    """True for the Analysis desk slug or an ``analysis-*`` plugin prefix.

    Never matches the Analyst Role name.
    """
    if desk is DeskSlug.ANALYSIS:
        return True
    if isinstance(desk, DeskSlug):
        return False
    if not isinstance(desk, str):
        return False
    token = desk.strip().casefold()
    if token == DeskSlug.ANALYSIS.value:
        return True
    return token.startswith(f"{DeskSlug.ANALYSIS.value}-")


def is_rlm_runtime_in_scope(desk: object) -> bool:
    """RLM Runtime v1 is Analysis-desk only (DEC-0313)."""
    return is_analysis_desk(desk)


def available_execution_models(desk: object) -> frozenset[ExecutionModel]:
    """Dialogue everywhere; RLM added only for Analysis."""
    models = {ExecutionModel.DIALOGUE}
    if is_rlm_runtime_in_scope(desk):
        models.add(ExecutionModel.RLM)
    return frozenset(models)


def select_execution_model(
    desk: object,
    requested: object = None,
) -> Result[ExecutionModel]:
    """Select a runtime implementation of the shared loop-and-state contract.

    Default is Dialogue. Requesting RLM outside Analysis cites deferred
    GAP-0080 rather than extending the runtime.
    """
    if requested in BACKGROUND_SESSION_TYPES:
        return _policy(
            "session_type",
            "there is no separate background-session type; attachment and "
            "autonomy are orthogonal axes (AD-14; DEC-0313)",
            given=requested,
        )
    if requested is None or requested == "":
        return Ok(ExecutionModel.DIALOGUE)
    try:
        model = (
            requested
            if isinstance(requested, ExecutionModel)
            else parse_closed(ExecutionModel, requested)
        )
    except VocabularyError as exc:
        return _invalid("execution_model", str(exc), given=repr(requested))
    if model is ExecutionModel.DIALOGUE:
        return Ok(model)
    if is_rlm_runtime_in_scope(desk):
        return Ok(model)
    return _policy(
        "execution_model",
        "RLM Runtime v1 is scoped by desk to Analysis (analysis-*), never by "
        "Role; expansion beyond Analysis is deferred (GAP-0080)",
        desk=repr(desk) if not isinstance(desk, DeskSlug) else desk.value,
        requested=model.value,
        gap="GAP-0080",
        gap_status="deferred",
        contract=LOOP_AND_STATE_CONTRACT,
    )


def _parse_owner(owner: object) -> Result[ActorId]:
    if isinstance(owner, ActorId):
        return Ok(owner)
    if isinstance(owner, Quant):
        return Ok(owner.actor_id)
    return ActorId.try_create(owner)


def mint_durable_session(
    *,
    session_id: object,
    owner: object,
    execution_model: object = ExecutionModel.DIALOGUE,
    autonomy: object = SessionAutonomy.INTERACTIVE,
    attachment: object = None,
    session_type: object = None,
    payload: Mapping[str, object] | None = None,
) -> Result[Session]:
    """Mint a durable Session record with execution-model and autonomy only.

    ``attachment`` is refused — it is client state and is never persisted.
    """
    if session_type in BACKGROUND_SESSION_TYPES:
        return _policy(
            "session_type",
            "there is no separate background-session type (AD-14; DEC-0313)",
            given=session_type,
        )
    if attachment is not None:
        return _policy(
            "attachment",
            "attachment is client state, never daemon state and never persisted (AD-14; DEC-0313)",
            given=repr(attachment),
            client_axis=CLIENT_SESSION_AXIS,
        )
    if payload is not None:
        forbidden = {CLIENT_SESSION_AXIS, "attached", "detached", "session_type"}
        present = forbidden.intersection(payload)
        if present:
            return _policy(
                "payload",
                "durable Session payload carries execution_model and autonomy "
                "only; attachment stays client state (AD-14; DEC-0313)",
                given=sorted(present),
                durable_axes=list(DURABLE_SESSION_AXES),
            )
    if not isinstance(session_id, str) or session_id.strip() == "":
        return _invalid("session_id", "Session requires a non-empty id")
    parsed_owner = _parse_owner(owner)
    if not isinstance(parsed_owner, Ok):
        return parsed_owner
    try:
        model = (
            execution_model
            if isinstance(execution_model, ExecutionModel)
            else parse_closed(ExecutionModel, execution_model)
        )
        auto = (
            autonomy
            if isinstance(autonomy, SessionAutonomy)
            else parse_closed(SessionAutonomy, autonomy)
        )
    except VocabularyError as exc:
        return _invalid("session_axis", str(exc))
    return Ok(
        Session(
            id=session_id.strip(),
            owner=parsed_owner.value,
            execution_model=model,
            autonomy=auto,
        )
    )


def durable_session_payload(session: Session) -> Mapping[str, object]:
    """Serialize durable axes only — attachment is never a key."""
    return MappingProxyType(
        {
            "id": session.id,
            "owner": session.owner.value,
            "execution_model": session.execution_model.value,
            "autonomy": session.autonomy.value,
            "contract": LOOP_AND_STATE_CONTRACT,
        }
    )


def parse_session_attachment(value: object) -> Result[SessionAttachment]:
    """Parse client-only attachment; never a durable Session field."""
    try:
        return Ok(
            value
            if isinstance(value, SessionAttachment)
            else parse_closed(SessionAttachment, value)
        )
    except VocabularyError as exc:
        return _invalid("attachment", str(exc), given=repr(value))
