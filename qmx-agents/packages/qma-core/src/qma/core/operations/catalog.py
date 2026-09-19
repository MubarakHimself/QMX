"""Published public-operation descriptors (CONTRACTS §1 / §15; FR-WF-14).

Representative operations from the sitting door matrix. Each publishes a
complete versioned descriptor. Two operations of one owner may advertise
different doors.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final

from qma.core.operations.descriptor import (
    OperationDescriptor,
    SupportedDoor,
    parse_operation_descriptor,
)
from qma.core.operations.doors import door_matrix
from qmf.core import Ok

__all__ = [
    "PUBLIC_OPERATION_PAYLOADS",
    "load_public_operation_descriptors",
    "public_door_matrix",
    "public_operation_descriptors",
]


_REFUSAL_CODES: Final[list[str]] = [
    "INVALID_INPUT",
    "UNAVAILABLE",
    "UNSUPPORTED_DOOR",
    "STALE_OBSERVATION",
    "GRANT_MISMATCH",
]


def _shape(*, family: str = "CT-04") -> dict[str, object]:
    return {"family": family, "codes": list(_REFUSAL_CODES)}


PUBLIC_OPERATION_PAYLOADS: Final[tuple[Mapping[str, object], ...]] = (
    {
        "op_id": "qmb.analysis.project",
        "owner": "COMP-QMB",
        "version": 1,
        "input_schema": "qmb.analysis.project.v1",
        "output_shape": "artifact_ref",
        "input_cardinality": "one",
        "output_cardinality": "one",
        "empty_policy": "refuse",
        "configuration": {
            "defaults": {"as_of": None},
            "required_keys": ["run_fp1"],
            "optional_keys": ["as_of"],
        },
        "declared_operation_dependencies": [],
        "resource_needs": {
            "occupancy": "query",
            "memory_class": "light",
            "requires_environment": False,
        },
        "documentation_refs": ["docs/components/qmb.md#analysis-project"],
        "validation_class": "schema+semantic",
        "units": None,
        "compatibility": {"qmb": ">=0.1"},
        "effect_class": "read",
        "permission_requests": ["library.read"],
        "placement": "local-library",
        "error_refusal_shape": _shape(),
        "progress": True,
        "lifecycle_verbs": ["start", "query-state", "cancel", "await"],
        "supported_doors": [
            {"adapter": "library", "door": "qmb.analysis.project"},
            {"adapter": "qmb-cli", "door": "qmb analysis project"},
            {"adapter": "qma-wire", "door": "via CT-47"},
        ],
    },
    {
        "op_id": "qmb.backtest.run",
        "owner": "COMP-QMB",
        "version": 1,
        "input_schema": "qmb.backtest.run.v1",
        "output_shape": "job_handle",
        "input_cardinality": "one",
        "output_cardinality": "one",
        "empty_policy": "refuse",
        "configuration": {
            "defaults": {},
            "required_keys": ["run_fp1"],
            "optional_keys": ["as_of"],
        },
        "declared_operation_dependencies": [],
        "resource_needs": {
            "occupancy": "run",
            "memory_class": "heavy",
            "requires_environment": True,
        },
        "documentation_refs": ["docs/components/qmb.md#backtest-run"],
        "validation_class": "schema+semantic",
        "units": None,
        "compatibility": {"qmb": ">=0.1"},
        "effect_class": "place-run",
        "permission_requests": ["library.run"],
        "placement": "worker",
        "error_refusal_shape": _shape(),
        "progress": True,
        "lifecycle_verbs": ["start", "query-state", "cancel", "await"],
        "supported_doors": [
            {"adapter": "library", "door": "qmb.backtest.run"},
            {"adapter": "qmb-cli", "door": "qmb backtest run"},
            {"adapter": "qma-wire", "door": "via CT-47"},
            {"adapter": "qmn-run-slice", "door": "unforked run_slice"},
        ],
    },
    {
        "op_id": "qma.procedure.start",
        "owner": "COMP-QMA",
        "version": 1,
        "input_schema": "qma.procedure.start.v1",
        "output_shape": "job_handle",
        "input_cardinality": "one",
        "output_cardinality": "one",
        "empty_policy": "refuse",
        "configuration": {
            "defaults": {},
            "required_keys": ["procedure_id"],
            "optional_keys": ["cursor"],
        },
        "declared_operation_dependencies": [],
        "resource_needs": {
            "occupancy": "run",
            "memory_class": "light",
            "requires_environment": True,
        },
        "documentation_refs": ["docs/components/qma-core.md#procedure-start"],
        "validation_class": "schema+semantic",
        "units": None,
        "compatibility": {"qma-core": ">=0.1"},
        "effect_class": "place-run",
        "permission_requests": ["procedure.start"],
        "placement": "daemon",
        "error_refusal_shape": _shape(),
        "progress": True,
        "lifecycle_verbs": ["start", "query-state", "cancel", "await"],
        "supported_doors": [
            {"adapter": "library", "door": "qma.procedure.start"},
            {"adapter": "qma-wire", "door": "qma.procedure.start"},
        ],
    },
    {
        "op_id": "qmn.evidence.query",
        "owner": "COMP-QMN",
        "version": 1,
        "input_schema": "qmn.evidence.query.v1",
        "output_shape": "value",
        "input_cardinality": "one",
        "output_cardinality": "many",
        "empty_policy": "refuse",
        "configuration": {
            "defaults": {},
            "required_keys": ["query"],
            "optional_keys": ["as_of"],
        },
        "declared_operation_dependencies": [],
        "resource_needs": {
            "occupancy": "query",
            "memory_class": "light",
            "requires_environment": False,
        },
        "documentation_refs": ["docs/components/trading-node.md#evidence-query"],
        "validation_class": "schema+semantic",
        "units": None,
        "compatibility": {"qmn": ">=0.1"},
        "effect_class": "read",
        "permission_requests": ["evidence.read"],
        "placement": "node",
        "error_refusal_shape": _shape(),
        "progress": False,
        "lifecycle_verbs": ["query-state"],
        "supported_doors": [
            {"adapter": "library", "door": "qmn.evidence.query"},
            {"adapter": "evidence-http", "door": "evidence HTTP"},
            {"adapter": "node", "door": "node door"},
        ],
    },
    {
        "op_id": "qml.research.browse",
        "owner": "COMP-QML",
        "version": 1,
        "input_schema": "qml.research.browse.v1",
        "output_shape": "value",
        "input_cardinality": "one",
        "output_cardinality": "many",
        "empty_policy": "skip",
        "configuration": {
            "defaults": {},
            "required_keys": ["snapshot_ref"],
            "optional_keys": ["locator"],
        },
        "declared_operation_dependencies": [],
        "resource_needs": {
            "occupancy": "query",
            "memory_class": "light",
            "requires_environment": False,
        },
        "documentation_refs": ["docs/components/qml.md#research-browse"],
        "validation_class": "schema+semantic",
        "units": None,
        "compatibility": {"qml": ">=0.1"},
        "effect_class": "read",
        "permission_requests": ["library.read"],
        "placement": "local-library",
        "error_refusal_shape": _shape(),
        "progress": False,
        "lifecycle_verbs": ["start", "query-state"],
        "supported_doors": [
            {"adapter": "library", "door": "qml.research.browse"},
        ],
    },
)


class DescriptorCatalogError(RuntimeError):
    """Public catalog payloads must already satisfy CONTRACTS §1."""


def load_public_operation_descriptors(
    payloads: Sequence[Mapping[str, object]] | None = None,
) -> tuple[OperationDescriptor, ...]:
    """Parse published public operations; each must be a complete descriptor."""
    loaded: list[OperationDescriptor] = []
    for payload in PUBLIC_OPERATION_PAYLOADS if payloads is None else payloads:
        parsed = parse_operation_descriptor(payload)
        if not isinstance(parsed, Ok):
            raise DescriptorCatalogError(
                f"public operation {payload.get('op_id')!r} failed CONTRACTS §1: {parsed}"
            )
        loaded.append(parsed.value)
    return tuple(loaded)


def public_operation_descriptors() -> tuple[OperationDescriptor, ...]:
    """Sitting public operations with complete versioned descriptors."""
    return load_public_operation_descriptors()


def public_door_matrix() -> Mapping[tuple[str, int], tuple[SupportedDoor, ...]]:
    """Normative ``(op_id, version)`` door matrix for published operations."""
    return door_matrix(public_operation_descriptors())
