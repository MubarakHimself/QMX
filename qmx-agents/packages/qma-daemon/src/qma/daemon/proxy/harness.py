"""Milestone harness: Quant-scoped model request over the wire (FR-Q38/40/46).

Preserves ``scope_path`` and ``correlation_id``, resolves
ModelClass → Deployment → loopback OpenCodex (not the Credential Broker for
``auth_mode: none``), and returns a wire-safe result with honest routing
telemetry that never carries a resolved secret.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from qma.core.ports.model import (
    OPENCODEX_ADAPTER,
    ModelClassRequest,
    RoutingDecision,
    is_local_proxy_deployment,
)
from qma.core.vocabulary.enums import PrincipalClass, RoutingPolicy
from qma.daemon.proxy.opencodex import OpenCodexCallResult, OpenCodexDeployment
from qma.daemon.proxy.router import ModelRouter
from qma.wire.correlation import copy_correlation_id
from qma.wire.envelope import ScopePathError, ScopeSegment, parse_scope_path
from qmf.core import Ok, Result
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "ModelHarnessResult",
    "RoutingTelemetry",
    "execute_quant_model_request",
]


@dataclass(frozen=True, slots=True)
class RoutingTelemetry:
    """Honest routing-decision telemetry — never a resolved secret (AD-23)."""

    model_class: str
    deployment_id: str
    adapter: str | None
    auth_mode: str | None
    principal_class: str
    behind_credential_broker: bool
    chain: tuple[str, ...]

    def to_dict(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "model_class": self.model_class,
                "deployment_id": self.deployment_id,
                "adapter": self.adapter,
                "auth_mode": self.auth_mode,
                "principal_class": self.principal_class,
                "behind_credential_broker": self.behind_credential_broker,
                "chain": list(self.chain),
            }
        )


@dataclass(frozen=True, slots=True)
class ModelHarnessResult:
    """Wire-returnable model result with preserved provenance."""

    scope_path: tuple[ScopeSegment, ...]
    correlation_id: str
    principal_class: PrincipalClass
    routing: RoutingTelemetry
    model: OpenCodexCallResult

    def to_wire(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "scope_path": [seg.to_dict() for seg in self.scope_path],
                "correlation_id": self.correlation_id,
                "principal_class": self.principal_class.value,
                "routing": dict(self.routing.to_dict()),
                "model": dict(self.model.to_wire()),
            }
        )


def execute_quant_model_request(
    *,
    router: ModelRouter,
    request: ModelClassRequest,
    scope_path: Sequence[Mapping[str, str] | ScopeSegment] | Sequence[object],
    correlation_id: str,
    principal_class: PrincipalClass | str,
    prompt: str,
    deployments: Mapping[str, OpenCodexDeployment] | None = None,
    policy: RoutingPolicy | str = RoutingPolicy.FAILOVER,
) -> Result[ModelHarnessResult]:
    """Run the milestone ModelClass → OpenCodex path for an authenticated Quant."""
    try:
        parsed_scope = parse_scope_path(list(scope_path))
    except ScopePathError as exc:
        return invalid_input("scope_path", str(exc), given=repr(scope_path))

    if not any(seg.kind == "quant" for seg in parsed_scope):
        return invalid_input(
            "scope_path",
            "Quant-scoped model request requires a quant segment in scope_path",
            given=[seg.to_dict() for seg in parsed_scope],
        )

    copied = copy_correlation_id(correlation_id)
    if not isinstance(copied, Ok):
        return copied
    corr = copied.value

    if isinstance(principal_class, PrincipalClass):
        principal = principal_class
    else:
        try:
            principal = PrincipalClass(principal_class)
        except ValueError:
            return invalid_input(
                "principal_class",
                "principal_class must be operator or machine",
                given=repr(principal_class),
            )

    routed = router.resolve(request, policy=policy)
    if not isinstance(routed, Ok):
        return routed
    decision: RoutingDecision = routed.value
    record = decision.deployment

    if is_local_proxy_deployment(record):
        if record.adapter != OPENCODEX_ADAPTER:
            return policy_rejection(
                "adapter",
                "milestone harness reaches OpenCodex behind the Deployment contract; "
                f"unsupported local-proxy adapter {record.adapter!r}",
                deployment_id=record.deployment_id,
            )
        # Local-proxy path skips the Credential Broker entirely (FR-Q40).
        chain = ("ModelClass", "Deployment", "OpenCodex")
        behind_broker = False
    else:
        # Non-local path still names the Broker as the next chain step; this
        # harness's first milestone is the OpenCodex loopback path.
        return policy_rejection(
            "deployment",
            "milestone harness requires the OpenCodex local-proxy Deployment path",
            deployment_id=record.deployment_id,
        )

    pool = deployments or {}
    deployment = pool.get(record.deployment_id)
    if deployment is None:
        deployment = OpenCodexDeployment(record=record)

    call = deployment.call(request, prompt=prompt, resolved_secret=None)
    if not isinstance(call, Ok):
        return call

    telemetry = RoutingTelemetry(
        model_class=request.model_class.value,
        deployment_id=record.deployment_id,
        adapter=record.adapter,
        auth_mode=record.auth_mode,
        principal_class=principal.value,
        behind_credential_broker=behind_broker,
        chain=chain,
    )
    # Telemetry must never grow a secret field — surface check by construction.
    telemetry_payload = telemetry.to_dict()
    if "secret" in telemetry_payload or "credential_value" in telemetry_payload:
        msg = "routing telemetry must not carry secret or credential_value fields"
        raise RuntimeError(msg)

    return Ok(
        ModelHarnessResult(
            scope_path=parsed_scope,
            correlation_id=corr,
            principal_class=principal,
            routing=telemetry,
            model=call.value,
        )
    )
