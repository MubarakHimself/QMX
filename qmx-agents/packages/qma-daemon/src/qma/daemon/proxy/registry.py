"""Deployment Registry for ModelClass routing (CT-45; AD-15; FR-Q38/FR-Q39).

Plugin contributions register with ``model_family`` absent. Operator assignment
is a separate human-gate command; the registry never synthesizes a family.
Local-proxy Deployments are validated for loopback bind and ``auth_mode: none``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from types import MappingProxyType
from typing import Any

from qma.core.barriers.reachability import refuse_forbidden_model_adapter
from qma.core.ports.model import (
    MODEL_FAMILY_ASSIGN_COMMAND,
    PROXY_ALLOW_UNAUTHENTICATED_LOOPBACK_KEY,
    DeploymentRecord,
    assign_model_family,
    is_local_proxy_deployment,
)
from qma.core.vocabulary.enums import ModelClass, PrincipalClass
from qma.daemon.proxy.local_proxy import (
    ALLOW_UNAUTHENTICATED_LOOPBACK_DEFAULT,
    LocalProxyStartupEvidence,
    record_local_proxy_startup_evidence,
    validate_local_proxy_registration,
)
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal
from qmf.data.store.refusals import invalid_input

__all__ = [
    "DeploymentRegistry",
]


def _invalid_family_on_register(deployment_id: str) -> TypedRefusal:
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context={
            "field": "model_family",
            "reason": (
                "model_family is absent at registration and never synthesized; "
                "assign only via operator-principal model_family.assign (CT-45; AD-15)"
            ),
            "deployment_id": deployment_id,
        },
    )


class DeploymentRegistry:
    """In-memory multi Deployment catalog keyed by ``deployment_id``.

    Stage-one routing reads only records whose ``model_class`` matches the
    request. Registration refuses any non-``None`` ``model_family``. Local-proxy
    rows are validated against loopback bind and ``auth_mode: none`` (FR-Q40).
    """

    def __init__(
        self,
        *,
        allowed_families: Sequence[str] | None = None,
        allow_unauthenticated_loopback: bool = ALLOW_UNAUTHENTICATED_LOOPBACK_DEFAULT,
    ) -> None:
        self._by_id: dict[str, DeploymentRecord] = {}
        self._allowed_families: frozenset[str] = frozenset(allowed_families or ())
        self._wrr_cursors: dict[str, int] = {}
        self._allow_unauthenticated_loopback = bool(allow_unauthenticated_loopback)

    @property
    def allowed_families(self) -> frozenset[str]:
        return self._allowed_families

    @property
    def allow_unauthenticated_loopback(self) -> bool:
        """Current ``registry:proxy.allow_unauthenticated_loopback`` value."""
        return self._allow_unauthenticated_loopback

    @property
    def allow_unauthenticated_loopback_key(self) -> str:
        return PROXY_ALLOW_UNAUTHENTICATED_LOOPBACK_KEY

    def set_allowed_families(self, families: Sequence[str]) -> None:
        """Replace the closed ``registry:deployment.model_family`` vocabulary."""
        self._allowed_families = frozenset(families)

    def set_allow_unauthenticated_loopback(self, allowed: bool) -> None:
        """Update the cited ``registry:proxy.allow_unauthenticated_loopback`` value."""
        self._allow_unauthenticated_loopback = bool(allowed)

    def register(self, record: DeploymentRecord) -> Result[str]:
        """Register a Deployment with ``model_family`` absent (plugin path)."""
        if record.model_family is not None:
            return _invalid_family_on_register(record.deployment_id)
        openrouter = refuse_forbidden_model_adapter(record.adapter)
        if openrouter is not None:
            return openrouter
        if record.deployment_id in self._by_id:
            return invalid_input(
                "deployment_id",
                "Deployment id already registered (CT-45; AD-15)",
                given=record.deployment_id,
            )
        custody = validate_local_proxy_registration(
            record,
            allow_unauthenticated_loopback=self._allow_unauthenticated_loopback,
        )
        if not isinstance(custody, Ok):
            return custody
        # Force absence even if a caller passed an explicit None via replace.
        stored = replace(custody.value, model_family=None)
        self._by_id[stored.deployment_id] = stored
        return Ok(stored.deployment_id)

    def get(self, deployment_id: str) -> DeploymentRecord | None:
        return self._by_id.get(deployment_id)

    def catalog(self) -> tuple[DeploymentRecord, ...]:
        return tuple(self._by_id.values())

    def for_class(self, model_class: ModelClass) -> tuple[DeploymentRecord, ...]:
        return tuple(entry for entry in self._by_id.values() if entry.model_class is model_class)

    def round_robin_cursor(self, model_class: ModelClass) -> int:
        return self._wrr_cursors.get(model_class.value, 0)

    def set_round_robin_cursor(self, model_class: ModelClass, cursor: int) -> None:
        self._wrr_cursors[model_class.value] = cursor

    def assign_family(
        self,
        deployment_id: str,
        family: str,
        *,
        principal: PrincipalClass | str,
    ) -> Result[DeploymentRecord]:
        """Operator-only ``model_family`` write under the registry vocabulary."""
        record = self._by_id.get(deployment_id)
        if record is None:
            return invalid_input(
                "deployment_id",
                "unknown Deployment for model_family.assign",
                given=deployment_id,
                command=MODEL_FAMILY_ASSIGN_COMMAND,
            )
        outcome = assign_model_family(
            record,
            family,
            principal=principal,
            allowed_families=sorted(self._allowed_families),
        )
        if isinstance(outcome, Ok):
            self._by_id[deployment_id] = outcome.value
        return outcome

    def local_proxy_catalog(self) -> tuple[DeploymentRecord, ...]:
        return tuple(entry for entry in self._by_id.values() if is_local_proxy_deployment(entry))

    def startup_evidence(self) -> LocalProxyStartupEvidence:
        """Evidence entry naming each proxy Deployment and the loopback setting."""
        return record_local_proxy_startup_evidence(
            self.catalog(),
            allow_unauthenticated_loopback=self._allow_unauthenticated_loopback,
        )

    def snapshot(self) -> Mapping[str, Any]:
        return MappingProxyType(
            {
                "deployments": {
                    deployment_id: {
                        "model_class": record.model_class.value,
                        "model_family": record.model_family,
                        "context_tokens": record.context_tokens,
                        "supports_tools": record.supports_tools,
                        "supports_vision": record.supports_vision,
                        "supports_reasoning_effort": record.supports_reasoning_effort,
                        "supports_parallel_tool_calls": record.supports_parallel_tool_calls,
                        "weight": record.weight,
                        "quota_remaining": record.quota_remaining,
                        "credential_ref": record.credential_ref,
                        "adapter": record.adapter,
                        "auth_mode": record.auth_mode,
                        "bind_host": record.bind_host,
                        "bind_port": record.bind_port,
                        "accepts_unauthenticated": record.accepts_unauthenticated,
                    }
                    for deployment_id, record in self._by_id.items()
                },
                "allowed_families": sorted(self._allowed_families),
                "allow_unauthenticated_loopback": self._allow_unauthenticated_loopback,
                "allow_unauthenticated_loopback_key": PROXY_ALLOW_UNAUTHENTICATED_LOOPBACK_KEY,
            }
        )
