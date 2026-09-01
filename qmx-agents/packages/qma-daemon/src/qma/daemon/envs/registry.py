"""ExecutionEnvironment provider registry (CT-46; AD-17; FR-Q27).

An empty registry returns ``NoEnvironment`` for lease evaluation and never
blocks Mission compilation. Actual slot governance lands in Epic 45.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from qma.core.ports.execution import ExecutionEnvironment
from qma.core.refusals import NoEnvironment
from qma.core.vocabulary.enums import ExecutionEnvironmentKind
from qmf.core import Ok, Result
from qmf.data.store.refusals import invalid_input

__all__ = [
    "EnvironmentLease",
    "ExecutionEnvironmentRegistry",
]


@dataclass(frozen=True, slots=True)
class EnvironmentLease:
    """Per-slot environment lease distinct from ``dispatch_lease`` (AD-17)."""

    task_id: str
    kind: str
    slot_id: str
    provider_id: str | None = None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "lease": "environment_lease",
            "task_id": self.task_id,
            "kind": self.kind,
            "slot_id": self.slot_id,
        }
        if self.provider_id is not None:
            payload["provider_id"] = self.provider_id
        return MappingProxyType(payload)


class ExecutionEnvironmentRegistry:
    """In-memory singleton-per-kind registry for the ExecutionEnvironment port.

    Empty by default. Lease evaluation against an unbound kind returns
    ``NoEnvironment`` without affecting Mission compilation (FR-Q27).
    """

    def __init__(self) -> None:
        self._by_kind: dict[str, ExecutionEnvironment] = {}
        self._provider_ids: dict[str, str] = {}

    def register(
        self,
        kind: ExecutionEnvironmentKind | str,
        environment: ExecutionEnvironment,
        *,
        provider_id: str | None = None,
    ) -> Result[str]:
        """Bind one ExecutionEnvironment for ``kind`` (singleton cardinality)."""
        token = kind.value if isinstance(kind, ExecutionEnvironmentKind) else kind
        try:
            ExecutionEnvironmentKind(token)
        except ValueError:
            return invalid_input(
                "kind",
                "ExecutionEnvironment kind must be one of the six closed values (CT-46; AD-17)",
                given=repr(token),
            )
        if token in self._by_kind:
            return invalid_input(
                "kind",
                "ExecutionEnvironment is singleton per kind; duplicate binding refused (AD-1)",
                given=token,
            )
        self._by_kind[token] = environment
        if provider_id is not None:
            self._provider_ids[token] = provider_id
        return Ok(token)

    def get(self, kind: str) -> ExecutionEnvironment | None:
        return self._by_kind.get(kind)

    def is_empty(self) -> bool:
        return not self._by_kind

    def kinds(self) -> frozenset[str]:
        return frozenset(self._by_kind)

    def evaluate_environment_lease(
        self,
        *,
        task_id: str,
        kind: ExecutionEnvironmentKind | str,
    ) -> Result[EnvironmentLease]:
        """Issue an ``environment_lease`` or return ``NoEnvironment``.

        Does not mint durable placement state — Epic 45 owns slot governance.
        """
        if not task_id:
            return invalid_input("task_id", "environment_lease requires a task_id")
        token = kind.value if isinstance(kind, ExecutionEnvironmentKind) else kind
        if token not in self._by_kind:
            return NoEnvironment.of(kind=token)
        slot_id = f"slot:{token}:0"
        return Ok(
            EnvironmentLease(
                task_id=task_id,
                kind=token,
                slot_id=slot_id,
                provider_id=self._provider_ids.get(token),
            )
        )

    def snapshot(self) -> Mapping[str, Any]:
        return MappingProxyType(
            {
                "kinds": sorted(self._by_kind),
                "empty": self.is_empty(),
            }
        )
