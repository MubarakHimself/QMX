"""Public operation descriptors and door matrix (Workflows AD-3 / AD-21).

Definitions only: complete versioned descriptors, closed vocabularies, and
``op_id``+version door admission. QMB remains the only operator CLI.
"""

from __future__ import annotations

from qma.core.operations.catalog import (
    PUBLIC_OPERATION_PAYLOADS,
    load_public_operation_descriptors,
    public_door_matrix,
    public_operation_descriptors,
)
from qma.core.operations.descriptor import (
    ERROR_REFUSAL_FAMILY,
    FORBIDDEN_DESCRIPTOR_FIELDS,
    OPERATION_DESCRIPTOR_CONTRACT,
    OPERATION_DESCRIPTOR_FIELDS,
    OPERATION_DESCRIPTOR_INSPECT_SHAS,
    OPERATION_DESCRIPTOR_NEW_CT_MINTED,
    OPERATION_DESCRIPTOR_OWNER,
    OPERATION_DESCRIPTOR_WIRED_AT_INSPECT_SHA,
    OPERATOR_CLI_ADAPTER,
    REQUIRED_REFUSAL_CODES,
    ErrorRefusalShape,
    OperationConfiguration,
    OperationDescriptor,
    ResourceNeeds,
    SupportedDoor,
    parse_operation_descriptor,
    publish_operation_descriptor,
)
from qma.core.operations.doors import (
    FORBIDDEN_OPERATOR_CLI_ADAPTERS,
    OPERATOR_CLI_ADAPTERS,
    QMA_OPERATOR_CLI,
    QMN_OPERATOR_CLI,
    admit_operation_door,
    descriptor_for,
    door_matrix,
    doors_for,
    is_operator_cli_adapter,
    owner_door_summary,
)

__all__ = [
    "ERROR_REFUSAL_FAMILY",
    "FORBIDDEN_DESCRIPTOR_FIELDS",
    "FORBIDDEN_OPERATOR_CLI_ADAPTERS",
    "OPERATION_DESCRIPTOR_CONTRACT",
    "OPERATION_DESCRIPTOR_FIELDS",
    "OPERATION_DESCRIPTOR_INSPECT_SHAS",
    "OPERATION_DESCRIPTOR_NEW_CT_MINTED",
    "OPERATION_DESCRIPTOR_OWNER",
    "OPERATION_DESCRIPTOR_WIRED_AT_INSPECT_SHA",
    "OPERATOR_CLI_ADAPTER",
    "OPERATOR_CLI_ADAPTERS",
    "PUBLIC_OPERATION_PAYLOADS",
    "QMA_OPERATOR_CLI",
    "QMN_OPERATOR_CLI",
    "REQUIRED_REFUSAL_CODES",
    "ErrorRefusalShape",
    "OperationConfiguration",
    "OperationDescriptor",
    "ResourceNeeds",
    "SupportedDoor",
    "admit_operation_door",
    "descriptor_for",
    "door_matrix",
    "doors_for",
    "is_operator_cli_adapter",
    "load_public_operation_descriptors",
    "owner_door_summary",
    "parse_operation_descriptor",
    "public_door_matrix",
    "public_operation_descriptors",
    "publish_operation_descriptor",
]
