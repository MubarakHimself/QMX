"""Door matrix keyed by ``op_id`` + version (Workflows AD-21; RC-17; FR-WF-26).

Owner-wide matrices are non-normative summaries only. Unsupported door returns
typed ``unsupported_door``. QMB remains the only operator CLI.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Final

from qma.core.operations.descriptor import (
    FORBIDDEN_OPERATOR_CLI_ADAPTERS,
    OPERATOR_CLI_ADAPTER,
    OperationDescriptor,
    SupportedDoor,
)
from qma.core.refusals.variants import UnsupportedDoor
from qma.core.vocabulary.enums import DoorAdapter
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "FORBIDDEN_OPERATOR_CLI_ADAPTERS",
    "OPERATOR_CLI_ADAPTER",
    "OPERATOR_CLI_ADAPTERS",
    "QMA_OPERATOR_CLI",
    "QMN_OPERATOR_CLI",
    "admit_operation_door",
    "descriptor_for",
    "door_matrix",
    "doors_for",
    "is_operator_cli_adapter",
    "owner_door_summary",
]


OPERATOR_CLI_ADAPTERS: Final[frozenset[str]] = frozenset({OPERATOR_CLI_ADAPTER})
QMA_OPERATOR_CLI: Final[bool] = False
QMN_OPERATOR_CLI: Final[bool] = False


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def is_operator_cli_adapter(adapter: object) -> bool:
    """True only for the QMB operator CLI adapter."""
    if isinstance(adapter, DoorAdapter):
        return adapter is DoorAdapter.QMB_CLI
    return isinstance(adapter, str) and adapter == OPERATOR_CLI_ADAPTER


def door_matrix(
    descriptors: Sequence[OperationDescriptor],
) -> Mapping[tuple[str, int], tuple[SupportedDoor, ...]]:
    """Normative matrix: ``(op_id, version)`` → supported doors. Not keyed by owner."""
    matrix: dict[tuple[str, int], tuple[SupportedDoor, ...]] = {}
    for descriptor in descriptors:
        matrix[descriptor.door_key] = descriptor.supported_doors
    return MappingProxyType(matrix)


def descriptor_for(
    descriptors: Sequence[OperationDescriptor],
    *,
    op_id: str,
    version: int,
) -> OperationDescriptor | None:
    """Return the descriptor for ``op_id`` + ``version``, or None."""
    for descriptor in descriptors:
        if descriptor.op_id == op_id and descriptor.version == version:
            return descriptor
    return None


def doors_for(
    descriptors: Sequence[OperationDescriptor],
    *,
    op_id: str,
    version: int,
) -> tuple[SupportedDoor, ...] | None:
    """Supported doors for one ``op_id`` + ``version``."""
    descriptor = descriptor_for(descriptors, op_id=op_id, version=version)
    if descriptor is None:
        return None
    return descriptor.supported_doors


def owner_door_summary(
    descriptors: Sequence[OperationDescriptor],
) -> Mapping[str, tuple[str, ...]]:
    """Non-normative owner-wide adapter union. Never a lookup key (CONTRACTS §15)."""
    grouped: dict[str, list[str]] = {}
    for descriptor in descriptors:
        adapters = grouped.setdefault(descriptor.owner, [])
        for door in descriptor.supported_doors:
            token = door.adapter.value
            if token not in adapters:
                adapters.append(token)
    return MappingProxyType({owner: tuple(adapters) for owner, adapters in grouped.items()})


def admit_operation_door(
    descriptors: Sequence[OperationDescriptor],
    *,
    op_id: str,
    version: int,
    adapter: object,
    door: str | None = None,
) -> Result[SupportedDoor]:
    """Admit a door for ``op_id`` + ``version``. Unsupported → ``UnsupportedDoor``."""
    adapter_token = adapter.value if isinstance(adapter, DoorAdapter) else adapter
    if not isinstance(adapter_token, str) or adapter_token.strip() == "":
        return _invalid("adapter", "door adapter must be a non-empty string", given=repr(adapter))
    adapter_token = adapter_token.strip()
    if adapter_token in FORBIDDEN_OPERATOR_CLI_ADAPTERS:
        return UnsupportedDoor.of(
            op_id=op_id,
            version=version,
            adapter=adapter_token,
            door=door,
        )
    descriptor = descriptor_for(descriptors, op_id=op_id, version=version)
    if descriptor is None:
        return _invalid(
            "op_id",
            "no published descriptor for op_id+version",
            op_id=op_id,
            version=version,
        )
    try:
        parsed_adapter = (
            adapter
            if isinstance(adapter, DoorAdapter)
            else parse_closed(DoorAdapter, adapter_token)
        )
    except VocabularyError:
        return UnsupportedDoor.of(
            op_id=op_id,
            version=version,
            adapter=adapter_token,
            door=door,
            owner=descriptor.owner,
        )
    for supported in descriptor.supported_doors:
        if supported.adapter is not parsed_adapter:
            continue
        if door is None or supported.door == door:
            return Ok(supported)
    return UnsupportedDoor.of(
        op_id=op_id,
        version=version,
        adapter=parsed_adapter.value,
        door=door,
        owner=descriptor.owner,
    )
