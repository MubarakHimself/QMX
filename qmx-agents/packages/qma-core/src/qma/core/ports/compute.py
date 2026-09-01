"""ComputeProvider port and ComputeRequirement (CT-46; AD-1, AD-17).

Agents declare a requirement — never a host or vendor. The daemon Compute
Router is the only placer. ``gpu`` is the one optional field.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Protocol, cast, runtime_checkable

from qma.core.ports.execution import (
    ExecutionEnvironmentDeclaration,
    is_pinned_single_slot_kind,
)
from qma.core.refusals import NoEnvironment
from qma.core.vocabulary.enums import (
    EnvironmentLifecycle,
    ExecutionEnvironmentKind,
    IsolationMode,
)
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result
from qmf.core.chrono import Duration
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "COMPUTE_REQUIREMENT_FIELDS",
    "ComputeProvider",
    "ComputeRequirement",
    "GpuRequirement",
    "environment_isolation",
    "match_compute_requirement",
    "parse_compute_requirement",
]


# CT-46 ComputeRequirement surface (FR-Q50). ``kind`` is the environment class,
# never a host. ``gpu`` is the one optional field.
COMPUTE_REQUIREMENT_FIELDS: Final[tuple[str, ...]] = (
    "kind",
    "cpu",
    "memory",
    "disk",
    "gpu",
    "capabilities",
    "timeout",
    "max_memory",
    "isolation",
)


@runtime_checkable
class ComputeProvider(Protocol):
    """Definitions-only ComputeProvider seam; one binding per compute kind.

    Cardinality: singleton, scope key ``kind`` (see ``PORT_CONTRACTS``).
    """


def _parse_positive_count(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise VocabularyError(f"{value!r} is not a positive count for {field} (CT-46; AD-17)")
    return value


def _parse_timeout(value: object) -> Duration:
    if isinstance(value, Duration):
        if value.value_ns <= 0:
            raise VocabularyError("timeout must be a positive span from a recorded UTC instant")
        return value
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise VocabularyError(f"{value!r} is not a positive nanosecond timeout span (CT-46; AD-17)")
    created = Duration.try_create(value)
    if not isinstance(created, Ok):
        raise VocabularyError("timeout must be a signed int64 nanosecond quantity (CT-02)")
    return created.value


def _tuple_of_str(values: Sequence[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(item.strip() for item in values if item.strip())


def _parse_gpu(value: object) -> GpuRequirement | None:
    if value is None:
        return None
    if isinstance(value, GpuRequirement):
        if value.count < 1:
            raise VocabularyError("gpu.count must be a positive count (CT-46; AD-17)")
        return value
    if isinstance(value, bool) or not isinstance(value, (int, Mapping)):
        raise VocabularyError(f"{value!r} is not a GpuRequirement (CT-46; AD-17)")
    if isinstance(value, int):
        return GpuRequirement(count=_parse_positive_count(value, "gpu.count"))
    mapping = cast(Mapping[str, object], value)
    count_raw = mapping.get("count", mapping.get("gpu"))
    kind_raw = mapping.get("kind")
    kind = str(kind_raw).strip() if isinstance(kind_raw, str) and str(kind_raw).strip() else None
    return GpuRequirement(count=_parse_positive_count(count_raw, "gpu.count"), kind=kind)


def _refuse_named_host(**named: object) -> None:
    if any(value not in (None, "") for value in named.values()):
        raise VocabularyError(
            "ComputeRequirement names no host, machine, or vendor (CT-46; AD-17; FR-Q50)"
        )


@dataclass(frozen=True, slots=True)
class GpuRequirement:
    """Optional GPU need: count plus an optional capability class, never a vendor."""

    count: int
    kind: str | None = None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {"count": self.count}
        if self.kind is not None:
            payload["kind"] = self.kind
        return MappingProxyType(payload)


@dataclass(frozen=True, slots=True)
class ComputeRequirement:
    """What an agent declares so the Compute Router can place work (CT-46; FR-Q50).

    ``kind`` is the closed environment class. Agents never name a machine or a
    vendor. ``gpu`` is the one optional field.
    """

    kind: ExecutionEnvironmentKind
    cpu: int
    memory: int
    disk: int
    capabilities: tuple[str, ...]
    timeout: Duration
    max_memory: int
    isolation: IsolationMode
    gpu: GpuRequirement | None = None

    @classmethod
    def try_parse(
        cls,
        *,
        kind: ExecutionEnvironmentKind | str,
        cpu: object,
        memory: object,
        disk: object,
        timeout: object,
        max_memory: object,
        isolation: IsolationMode | str,
        capabilities: Sequence[str] | tuple[str, ...] | None = (),
        gpu: object = None,
        host: object = None,
        machine: object = None,
        vendor: object = None,
        agent_machine: object = None,
        agent_vendor: object = None,
    ) -> ComputeRequirement:
        """Parse a closed requirement; invented values and host names fail."""
        _refuse_named_host(
            host=host,
            machine=machine,
            vendor=vendor,
            agent_machine=agent_machine,
            agent_vendor=agent_vendor,
        )
        if isinstance(kind, ExecutionEnvironmentKind):
            resolved_kind = kind
        else:
            resolved_kind = parse_closed(ExecutionEnvironmentKind, kind)
        resolved_isolation = (
            isolation
            if isinstance(isolation, IsolationMode)
            else parse_closed(IsolationMode, isolation)
        )
        cpu_n = _parse_positive_count(cpu, "cpu")
        memory_n = _parse_positive_count(memory, "memory")
        disk_n = _parse_positive_count(disk, "disk")
        max_memory_n = _parse_positive_count(max_memory, "max_memory")
        if max_memory_n < memory_n:
            raise VocabularyError("max_memory must be at least memory (CT-46; AD-17)")
        return cls(
            kind=resolved_kind,
            cpu=cpu_n,
            memory=memory_n,
            disk=disk_n,
            capabilities=_tuple_of_str(capabilities),
            timeout=_parse_timeout(timeout),
            max_memory=max_memory_n,
            isolation=resolved_isolation,
            gpu=_parse_gpu(gpu),
        )

    def surface(self) -> Mapping[str, object]:
        """CT-46 ComputeRequirement fields; no host or vendor."""
        return {
            "kind": self.kind.value,
            "cpu": self.cpu,
            "memory": self.memory,
            "disk": self.disk,
            "gpu": None if self.gpu is None else dict(self.gpu.to_payload()),
            "capabilities": self.capabilities,
            "timeout": self.timeout.value_ns,
            "max_memory": self.max_memory,
            "isolation": self.isolation.value,
        }

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(dict(self.surface()))


def parse_compute_requirement(
    *,
    kind: ExecutionEnvironmentKind | str,
    cpu: object,
    memory: object,
    disk: object,
    timeout: object,
    max_memory: object,
    isolation: IsolationMode | str,
    capabilities: Sequence[str] | tuple[str, ...] | None = (),
    gpu: object = None,
    host: object = None,
    machine: object = None,
    vendor: object = None,
    agent_machine: object = None,
    agent_vendor: object = None,
) -> Result[ComputeRequirement]:
    """Result-returning parse of a ComputeRequirement (CT-46; FR-Q50)."""
    try:
        return Ok(
            ComputeRequirement.try_parse(
                kind=kind,
                cpu=cpu,
                memory=memory,
                disk=disk,
                timeout=timeout,
                max_memory=max_memory,
                isolation=isolation,
                capabilities=capabilities,
                gpu=gpu,
                host=host,
                machine=machine,
                vendor=vendor,
                agent_machine=agent_machine,
                agent_vendor=agent_vendor,
            )
        )
    except VocabularyError as exc:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "compute_requirement",
                "reason": str(exc),
            },
        )


def environment_isolation(declaration: ExecutionEnvironmentDeclaration) -> IsolationMode:
    """Isolation the environment can provide. Pinned hosts are shared."""
    if is_pinned_single_slot_kind(declaration.kind):
        return IsolationMode.SHARED
    if declaration.lifecycle is EnvironmentLifecycle.PERSISTENT:
        return IsolationMode.SHARED
    return IsolationMode.REQUIRED


def _capacity_shortfall(
    required: int,
    available: int | None,
    field: str,
    unmet: list[str],
) -> None:
    if available is not None and required > available:
        unmet.append(field)


def match_compute_requirement(
    requirement: ComputeRequirement,
    declaration: ExecutionEnvironmentDeclaration,
) -> Result[ExecutionEnvironmentDeclaration]:
    """Match a requirement against one declared environment. Never broaden kind.

    Missing kind is ``NoEnvironment`` naming that kind. Capability, isolation,
    or resource shortfalls are the same refusal so the router does not place
    the work on another kind (CT-46; FR-Q50).
    """
    token = requirement.kind.value
    if declaration.kind is not requirement.kind:
        return NoEnvironment.of(kind=token, reason="kind_unbound")
    unmet: list[str] = []
    provided = frozenset(declaration.capabilities)
    needed = tuple(requirement.capabilities)
    missing_caps = tuple(item for item in needed if item not in provided)
    if missing_caps:
        unmet.append("capabilities")
    if environment_isolation(declaration) is not requirement.isolation:
        unmet.append("isolation")
    _capacity_shortfall(requirement.cpu, declaration.cpu, "cpu", unmet)
    _capacity_shortfall(requirement.memory, declaration.memory, "memory", unmet)
    _capacity_shortfall(requirement.disk, declaration.disk, "disk", unmet)
    _capacity_shortfall(requirement.max_memory, declaration.memory, "max_memory", unmet)
    if requirement.gpu is not None:
        gpu_ok = "gpu" in provided
        if declaration.gpu_count is not None:
            gpu_ok = declaration.gpu_count >= requirement.gpu.count
        if requirement.gpu.kind is not None and declaration.gpu_kind is not None:
            gpu_ok = gpu_ok and requirement.gpu.kind == declaration.gpu_kind
        if not gpu_ok:
            unmet.append("gpu")
    if unmet:
        return NoEnvironment.of(kind=token, reason="unmet", unmet=tuple(unmet))
    return Ok(declaration)
