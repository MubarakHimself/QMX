"""Deterministic ModelClass → Deployment router (CT-45; AD-15; FR-Q38).

The harness selects one closed ModelClass. Agents never name a vendor or choose
a Deployment. Credential Broker resolution is the next chain step (FR-Q40).
"""

from __future__ import annotations

from qma.core.ports.model import (
    ModelClassRequest,
    RoutingDecision,
    capabilities_for,
    eligible_pool,
    select_from_eligible,
    unmet_constraint_for,
)
from qma.core.refusals import NoEligibleDeployment
from qma.core.vocabulary.enums import RoutingPolicy
from qma.core.vocabulary.registry import parse_closed
from qma.daemon.proxy.registry import DeploymentRegistry
from qmf.core import Ok, Result

__all__ = [
    "ModelRouter",
]


class ModelRouter:
    """Two-stage ModelClass router over a DeploymentRegistry."""

    def __init__(self, registry: DeploymentRegistry) -> None:
        self._registry = registry

    @property
    def registry(self) -> DeploymentRegistry:
        return self._registry

    def resolve(
        self,
        request: ModelClassRequest,
        *,
        policy: RoutingPolicy | str = RoutingPolicy.FAILOVER,
    ) -> Result[RoutingDecision]:
        """Resolve ModelClass → Deployment and return ModelCapabilities.

        Empty eligible pool → ``NoEligibleDeployment`` naming class and unmet
        constraint. Never crosses a class boundary or substitutes a lower class.
        """
        resolved_policy = (
            policy if isinstance(policy, RoutingPolicy) else parse_closed(RoutingPolicy, policy)
        )
        catalog = self._registry.catalog()
        pool = eligible_pool(request, catalog)
        if not pool:
            return NoEligibleDeployment.of(
                model_class=request.model_class.value,
                unmet_constraint=unmet_constraint_for(request, catalog),
            )
        cursor = self._registry.round_robin_cursor(request.model_class)
        selected, next_cursor = select_from_eligible(
            pool,
            resolved_policy,
            round_robin_cursor=cursor,
        )
        if resolved_policy is RoutingPolicy.WEIGHTED_ROUND_ROBIN:
            self._registry.set_round_robin_cursor(request.model_class, next_cursor)
        return Ok(
            RoutingDecision(
                deployment=selected,
                capabilities=capabilities_for(selected),
                routing_policy=resolved_policy,
            )
        )
