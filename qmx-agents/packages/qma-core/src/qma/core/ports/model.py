"""ModelDeployment port, ModelClass routing shapes, and ReviewPolicy (CT-45).

Definitions only: a ModelClassRequest never names a vendor or Deployment.
Eligibility is two-stage (class pool, then needs + min_context_tokens).
``model_family`` is optional, never defaulted or synthesized (FR-Q38/FR-Q39).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from typing import Final, Literal, Protocol, runtime_checkable

from qma.core.refusals.variants import (
    NoEligibleDeployment,
    NoEligibleReviewer,
    OperatorPrincipalRequired,
)
from qma.core.vocabulary.enums import ModelClass, PrincipalClass, RoutingPolicy
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "AUTH_MODE_NONE",
    "LOCAL_PROXY_ADAPTERS",
    "MODEL_FAMILY_ASSIGN_COMMAND",
    "OPENCODEX_ADAPTER",
    "PROXY_ALLOW_UNAUTHENTICATED_LOOPBACK_KEY",
    "DeploymentRecord",
    "ModelCapabilities",
    "ModelClassRequest",
    "ModelDeployment",
    "NeedsFlags",
    "ReviewPolicy",
    "RoutingDecision",
    "assign_model_family",
    "capabilities_for",
    "eligible_pool",
    "is_local_proxy_deployment",
    "resolve_model_request",
    "select_from_eligible",
    "select_reviewer",
    "unmet_constraint_for",
]

MODEL_FAMILY_ASSIGN_COMMAND: Final[str] = "model_family.assign"

# Local-proxy custody (CT-45; AD-15; FR-Q40). Spine mints only auth_mode: none.
AUTH_MODE_NONE: Final[str] = "none"
OPENCODEX_ADAPTER: Final[str] = "opencodex"
LOCAL_PROXY_ADAPTERS: Final[frozenset[str]] = frozenset({OPENCODEX_ADAPTER})
PROXY_ALLOW_UNAUTHENTICATED_LOOPBACK_KEY: Final[str] = (
    "registry:proxy.allow_unauthenticated_loopback"
)

NeedName = Literal[
    "tools",
    "vision",
    "reasoning_effort",
    "parallel_tool_calls",
    "min_context_tokens",
    "class_pool",
    "needs",
]


@runtime_checkable
class ModelDeployment(Protocol):
    """Definitions-only ModelDeployment seam; keyed ``<plugin_id>:<local_id>``.

    Cardinality: multi (see ``PORT_CONTRACTS``).
    """


@dataclass(frozen=True, slots=True)
class NeedsFlags:
    """Stage-two eligibility flags beside ``min_context_tokens`` (CT-45; AD-15)."""

    tools: bool = False
    vision: bool = False
    reasoning_effort: bool = False
    parallel_tool_calls: bool = False


@dataclass(frozen=True, slots=True)
class ModelClassRequest:
    """Harness-selected ModelClass request — never a vendor or Deployment id."""

    model_class: ModelClass
    needs: NeedsFlags = field(default_factory=NeedsFlags)
    min_context_tokens: int = 0

    def __post_init__(self) -> None:
        if self.min_context_tokens < 0:
            msg = "min_context_tokens must be >= 0 (CT-45)"
            raise VocabularyError(msg)


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    """Capabilities returned to the Context Compiler for the selected Deployment."""

    deployment_id: str
    model_class: ModelClass
    context_window: int
    supports_tools: bool
    supports_vision: bool
    supports_reasoning_effort: bool
    supports_parallel_tool_calls: bool
    model_family: str | None = None


@dataclass(frozen=True, slots=True)
class DeploymentRecord:
    """Core-defined Deployment catalog row (CT-45; AD-15).

    ``model_family`` is optional and never defaulted or synthesized. An
    unassigned family is routable but ineligible for every ReviewPolicy
    comparison (DEC-0314, DEC-0309). Registration leaves the field absent.

    A local-proxy Deployment (OpenCodex first) carries ``auth_mode: none``, a
    verified loopback bind, and never a QMA ``credential_ref`` (FR-Q40).
    """

    deployment_id: str
    model_class: ModelClass
    model_family: str | None = None
    supports_tools: bool = False
    supports_vision: bool = False
    supports_reasoning_effort: bool = False
    supports_parallel_tool_calls: bool = False
    context_tokens: int = 0
    weight: int = 1
    quota_remaining: int = 0
    fill_units: int = 0
    fill_capacity: int = 1
    credential_ref: str | None = None
    adapter: str | None = None
    auth_mode: str | None = None
    bind_host: str | None = None
    bind_port: int | None = None
    accepts_unauthenticated: bool = False

    def __post_init__(self) -> None:
        if self.deployment_id.strip() == "":
            msg = "deployment_id must be a non-empty string (CT-45)"
            raise VocabularyError(msg)
        if self.model_family is not None and self.model_family.strip() == "":
            msg = (
                "model_family must be a non-empty string when assigned; "
                "omit the field for an unassigned family (CT-45; AD-15)"
            )
            raise VocabularyError(msg)
        if self.context_tokens < 0:
            msg = "context_tokens must be >= 0 (CT-45)"
            raise VocabularyError(msg)
        if self.weight < 1:
            msg = "weight must be >= 1 (CT-45)"
            raise VocabularyError(msg)
        if self.fill_capacity < 1:
            msg = "fill_capacity must be >= 1 (CT-45)"
            raise VocabularyError(msg)
        if self.fill_units < 0:
            msg = "fill_units must be >= 0 (CT-45)"
            raise VocabularyError(msg)
        if self.auth_mode is not None and self.auth_mode != AUTH_MODE_NONE:
            msg = (
                "auth_mode mints only 'none' for local-proxy Deployments; "
                "QMA-owned credentials use credential_ref (CT-45; AD-15)"
            )
            raise VocabularyError(msg)
        if self.bind_port is not None and not (1 <= self.bind_port <= 65535):
            msg = "bind_port must be in 1..65535 when set (CT-45)"
            raise VocabularyError(msg)


def is_local_proxy_deployment(record: DeploymentRecord) -> bool:
    """True when the Deployment is a local-proxy implementation (FR-Q40)."""
    if record.adapter is not None and record.adapter in LOCAL_PROXY_ADAPTERS:
        return True
    if record.auth_mode == AUTH_MODE_NONE:
        return True
    return record.bind_host is not None


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    """Resolved ModelClass → Deployment step; Credential Broker is next (CT-45)."""

    deployment: DeploymentRecord
    capabilities: ModelCapabilities
    routing_policy: RoutingPolicy
    chain: tuple[str, ...] = ("ModelClass", "Deployment", "CredentialBroker")


@dataclass(frozen=True, slots=True)
class ReviewPolicy:
    """AD-10 ReviewPolicy: ``author_family != reviewer_family`` (FR-Q34; CT-45).

    Empty catalog or no qualifying reviewer returns ``NoEligibleReviewer``.
    """

    model_class: ModelClass | str = ModelClass.WORKHORSE_GENERAL

    def select_reviewer(
        self,
        author_family: str | None,
        catalog: Sequence[DeploymentRecord],
    ) -> Result[DeploymentRecord]:
        """Pick the first eligible reviewer under family inequality."""
        return select_reviewer(
            author_family,
            catalog,
            model_class=self.model_class,
        )


def capabilities_for(record: DeploymentRecord) -> ModelCapabilities:
    """Project a Deployment record into Context-Compiler capabilities."""
    return ModelCapabilities(
        deployment_id=record.deployment_id,
        model_class=record.model_class,
        context_window=record.context_tokens,
        supports_tools=record.supports_tools,
        supports_vision=record.supports_vision,
        supports_reasoning_effort=record.supports_reasoning_effort,
        supports_parallel_tool_calls=record.supports_parallel_tool_calls,
        model_family=record.model_family,
    )


def _class_pool(
    catalog: Sequence[DeploymentRecord],
    model_class: ModelClass,
) -> tuple[DeploymentRecord, ...]:
    return tuple(entry for entry in catalog if entry.model_class is model_class)


def unmet_constraint_for(
    request: ModelClassRequest,
    catalog: Sequence[DeploymentRecord],
) -> NeedName:
    """Name the first unmet constraint for an empty eligible pool (CT-45)."""
    class_pool = _class_pool(catalog, request.model_class)
    if not class_pool:
        return "class_pool"
    needs = request.needs
    if needs.tools and not any(entry.supports_tools for entry in class_pool):
        return "tools"
    if needs.vision and not any(entry.supports_vision for entry in class_pool):
        return "vision"
    if needs.reasoning_effort and not any(entry.supports_reasoning_effort for entry in class_pool):
        return "reasoning_effort"
    if needs.parallel_tool_calls and not any(
        entry.supports_parallel_tool_calls for entry in class_pool
    ):
        return "parallel_tool_calls"
    if request.min_context_tokens > 0 and not any(
        entry.context_tokens >= request.min_context_tokens for entry in class_pool
    ):
        return "min_context_tokens"
    # Combined filter empty while each flag alone has some match.
    return "needs"


def _passes_needs(entry: DeploymentRecord, needs: NeedsFlags) -> bool:
    if needs.tools and not entry.supports_tools:
        return False
    if needs.vision and not entry.supports_vision:
        return False
    if needs.reasoning_effort and not entry.supports_reasoning_effort:
        return False
    return not (needs.parallel_tool_calls and not entry.supports_parallel_tool_calls)


def eligible_pool(
    request: ModelClassRequest,
    catalog: Sequence[DeploymentRecord],
) -> tuple[DeploymentRecord, ...]:
    """Two-stage filter: class pool, then needs + min_context_tokens only."""
    pool = _class_pool(catalog, request.model_class)
    return tuple(
        entry
        for entry in pool
        if _passes_needs(entry, request.needs)
        and entry.context_tokens >= request.min_context_tokens
    )


def select_from_eligible(
    pool: Sequence[DeploymentRecord],
    policy: RoutingPolicy,
    *,
    round_robin_cursor: int = 0,
) -> tuple[DeploymentRecord, int]:
    """Load-balance within an already-eligible pool under a closed policy.

    Returns ``(selected, next_round_robin_cursor)``. Cursor advances only for
    ``weighted_round_robin``; other policies leave it unchanged.
    """
    if not pool:
        msg = "select_from_eligible requires a non-empty eligible pool"
        raise VocabularyError(msg)

    if policy is RoutingPolicy.FAILOVER:
        return pool[0], round_robin_cursor

    if policy is RoutingPolicy.QUOTA_LOWEST:
        _qi, selected = max(
            enumerate(pool),
            key=lambda pair: (pair[1].quota_remaining, -pair[0]),
        )
        return selected, round_robin_cursor

    if policy is RoutingPolicy.FILL_FIRST:
        unsaturated = [entry for entry in pool if entry.fill_units < entry.fill_capacity]
        candidates: Sequence[DeploymentRecord] = unsaturated if unsaturated else pool
        _fi, selected = max(
            enumerate(candidates),
            key=lambda pair: (pair[1].fill_units, -pair[0]),
        )
        return selected, round_robin_cursor

    if policy is RoutingPolicy.WEIGHTED_ROUND_ROBIN:
        expanded: list[DeploymentRecord] = []
        for entry in pool:
            expanded.extend([entry] * entry.weight)
        index = round_robin_cursor % len(expanded)
        return expanded[index], round_robin_cursor + 1

    msg = f"unsupported routing policy: {policy!r}"
    raise VocabularyError(msg)


def resolve_model_request(
    request: ModelClassRequest,
    catalog: Sequence[DeploymentRecord],
    *,
    policy: RoutingPolicy | str = RoutingPolicy.FAILOVER,
    round_robin_cursor: int = 0,
) -> Result[RoutingDecision]:
    """Resolve ModelClass → Deployment; never crosses a class boundary (FR-Q38)."""
    resolved_policy = (
        policy if isinstance(policy, RoutingPolicy) else parse_closed(RoutingPolicy, policy)
    )
    pool = eligible_pool(request, catalog)
    if not pool:
        return NoEligibleDeployment.of(
            model_class=request.model_class.value,
            unmet_constraint=unmet_constraint_for(request, catalog),
        )
    selected, _next_cursor = select_from_eligible(
        pool,
        resolved_policy,
        round_robin_cursor=round_robin_cursor,
    )
    return Ok(
        RoutingDecision(
            deployment=selected,
            capabilities=capabilities_for(selected),
            routing_policy=resolved_policy,
        )
    )


def assign_model_family(
    record: DeploymentRecord,
    family: str,
    *,
    principal: PrincipalClass | str,
    allowed_families: Sequence[str],
) -> Result[DeploymentRecord]:
    """Operator-only ``model_family`` assignment governed by the registry enum.

    Machine principals return ``OperatorPrincipalRequired``. Values outside
    ``registry:deployment.model_family`` are refused as invalid input.
    """
    command = MODEL_FAMILY_ASSIGN_COMMAND
    if isinstance(principal, PrincipalClass):
        resolved_principal = principal
    else:
        try:
            resolved_principal = PrincipalClass(principal)
        except ValueError:
            return OperatorPrincipalRequired.of(
                command=command,
                principal_class=str(principal),
            )
    if resolved_principal is not PrincipalClass.OPERATOR:
        return OperatorPrincipalRequired.of(
            command=command,
            principal_class=resolved_principal.value,
        )
    if family.strip() == "":
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "model_family",
                "reason": "model_family must be a non-empty registry member when assigned",
                "given": repr(family),
            },
        )
    allowed = frozenset(allowed_families)
    if family not in allowed:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "model_family",
                "reason": "model_family must be a member of registry:deployment.model_family",
                "given": family,
                "allowed": sorted(allowed),
            },
        )
    return Ok(replace(record, model_family=family))


def select_reviewer(
    author_family: str | None,
    catalog: Sequence[DeploymentRecord],
    *,
    model_class: ModelClass | str = ModelClass.WORKHORSE_GENERAL,
) -> Result[DeploymentRecord]:
    """Enforce ``author_family != reviewer_family`` over a core-defined catalog.

    Unassigned ``model_family`` (``None``) is ineligible as a reviewer. Empty
    catalog and no qualifying row both return ``NoEligibleReviewer``.
    """
    resolved_class = (
        model_class
        if isinstance(model_class, ModelClass)
        else parse_closed(ModelClass, model_class)
    )
    if author_family is not None and author_family.strip() == "":
        return NoEligibleReviewer.of(model_class=resolved_class.value)
    if not catalog:
        return NoEligibleReviewer.of(model_class=resolved_class.value)
    for entry in catalog:
        family = entry.model_family
        if family is None:
            continue
        if family == author_family:
            continue
        return Ok(entry)
    return NoEligibleReviewer.of(model_class=resolved_class.value)
