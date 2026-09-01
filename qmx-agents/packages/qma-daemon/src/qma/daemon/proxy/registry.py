"""Deployment Registry for ModelClass routing (CT-45; AD-15; FR-Q38/FR-Q39).

Plugin contributions register with ``model_family`` absent. Operator assignment
is a separate human-gate command; the registry never synthesizes a family.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from types import MappingProxyType
from typing import Any

from qma.core.ports.model import (
    MODEL_FAMILY_ASSIGN_COMMAND,
    DeploymentRecord,
    assign_model_family,
)
from qma.core.vocabulary.enums import ModelClass, PrincipalClass
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
    request. Registration refuses any non-``None`` ``model_family``.
    """

    def __init__(self, *, allowed_families: Sequence[str] | None = None) -> None:
        self._by_id: dict[str, DeploymentRecord] = {}
        self._allowed_families: frozenset[str] = frozenset(allowed_families or ())
        self._wrr_cursors: dict[str, int] = {}

    @property
    def allowed_families(self) -> frozenset[str]:
        return self._allowed_families

    def set_allowed_families(self, families: Sequence[str]) -> None:
        """Replace the closed ``registry:deployment.model_family`` vocabulary."""
        self._allowed_families = frozenset(families)

    def register(self, record: DeploymentRecord) -> Result[str]:
        """Register a Deployment with ``model_family`` absent (plugin path)."""
        if record.model_family is not None:
            return _invalid_family_on_register(record.deployment_id)
        if record.deployment_id in self._by_id:
            return invalid_input(
                "deployment_id",
                "Deployment id already registered (CT-45; AD-15)",
                given=record.deployment_id,
            )
        # Force absence even if a caller passed an explicit None via replace.
        stored = replace(record, model_family=None)
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
                    }
                    for deployment_id, record in self._by_id.items()
                },
                "allowed_families": sorted(self._allowed_families),
            }
        )
