"""qma.wire — sole cross-boundary contract package.

Envelope, command/query/event families, protocol version, initialize handshake,
and the closed-and-addable ``host_request`` verb set. Owns no client
implementation and no alternate cross-boundary contract (DEC-0304; AR-Q04).
SemVer is display-only provenance in lockstep with the QMF workspace (AR-Q11).
"""

from __future__ import annotations

from qma.wire.envelope import (
    CORRELATION_MISSING_ANNOTATION,
    JOURNAL_SEQ_FIELD,
    SCOPE_KIND_ORDER,
    ScopePathError,
    ScopeSegment,
    WireEnvelope,
    WireEnvelopeError,
    is_scope_prefix,
    parse_scope_path,
)
from qma.wire.families import (
    FAMILY_CONTRACTS,
    FamilyContract,
    assert_client_close_safe,
    contract_for,
    contract_for_type,
    progress_is_authoritative,
    snapshots_are_authoritative,
)
from qma.wire.host_request import (
    HOST_REQUEST_OWNING_AD,
    HOST_REQUEST_VERBS,
    HOST_REQUEST_VOCABULARY_OWNER,
    HostRequestVerbError,
    parse_host_request_verb,
)
from qma.wire.initialize import (
    JSONRPC_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    WIRE_PROTOCOL_VERSION,
    InitializeError,
    InitializeParams,
    InitializeResult,
    JsonRpcRequest,
    JsonRpcResponse,
    WireConnection,
    negotiate_initialize,
)
from qma.wire.schemas import (
    SCHEMA_DIR,
    SCHEMA_FILES,
    SchemaValidationError,
    family_schema_name,
    load_schema,
    validate_family_payload,
    validate_instance,
    validate_wire_envelope_dict,
)
from qma.wire.vocabulary import (
    SEED_COMMAND_COUNT,
    SEED_EVENT_COUNT,
    SEED_QUERY_COUNT,
    SEED_VOCABULARY_COUNT,
    WIRE_COMMANDS,
    WIRE_EVENTS,
    WIRE_QUERIES,
    WIRE_VOCABULARY_OWNER,
    MessageFamily,
    WireCommand,
    WireEvent,
    WireQuery,
    WireVocabularyError,
    family_of,
    parse_wire_type,
)

__all__ = [
    "CORRELATION_MISSING_ANNOTATION",
    "FAMILY_CONTRACTS",
    "HOST_REQUEST_OWNING_AD",
    "HOST_REQUEST_VERBS",
    "HOST_REQUEST_VOCABULARY_OWNER",
    "JOURNAL_SEQ_FIELD",
    "JSONRPC_VERSION",
    "SCHEMA_DIR",
    "SCHEMA_FILES",
    "SCOPE_KIND_ORDER",
    "SEED_COMMAND_COUNT",
    "SEED_EVENT_COUNT",
    "SEED_QUERY_COUNT",
    "SEED_VOCABULARY_COUNT",
    "SUPPORTED_PROTOCOL_VERSIONS",
    "WIRE_COMMANDS",
    "WIRE_EVENTS",
    "WIRE_PROTOCOL_VERSION",
    "WIRE_QUERIES",
    "WIRE_VOCABULARY_OWNER",
    "FamilyContract",
    "HostRequestVerbError",
    "InitializeError",
    "InitializeParams",
    "InitializeResult",
    "JsonRpcRequest",
    "JsonRpcResponse",
    "MessageFamily",
    "SchemaValidationError",
    "ScopePathError",
    "ScopeSegment",
    "WireCommand",
    "WireConnection",
    "WireEnvelope",
    "WireEnvelopeError",
    "WireEvent",
    "WireQuery",
    "WireVocabularyError",
    "__version__",
    "assert_client_close_safe",
    "contract_for",
    "contract_for_type",
    "family_of",
    "family_schema_name",
    "is_scope_prefix",
    "load_schema",
    "negotiate_initialize",
    "parse_host_request_verb",
    "parse_scope_path",
    "parse_wire_type",
    "progress_is_authoritative",
    "snapshots_are_authoritative",
    "validate_family_payload",
    "validate_instance",
    "validate_wire_envelope_dict",
]

# Display-only provenance — never identity content (AR-Q11; DEC-0335).
__version__ = "0.1.0"
