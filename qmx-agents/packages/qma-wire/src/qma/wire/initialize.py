"""MCP-style ``initialize`` handshake over JSON-RPC 2.0 (CT-40; AD-5; FR-Q13).

Negotiates a semver ``protocolVersion`` and capabilities, assigns the connection
its stable ``producer_id``, and gates every command / query / event family
message until the exchange completes.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, cast

from qma.wire.vocabulary import MessageFamily, family_of, parse_wire_type
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
)

__all__ = [
    "JSONRPC_VERSION",
    "SUPPORTED_PROTOCOL_VERSIONS",
    "WIRE_PROTOCOL_VERSION",
    "InitializeError",
    "InitializeParams",
    "InitializeResult",
    "JsonRpcRequest",
    "JsonRpcResponse",
    "WireConnection",
    "negotiate_initialize",
]


JSONRPC_VERSION: Final[str] = "2.0"
WIRE_PROTOCOL_VERSION: Final[str] = "1.0.0"
SUPPORTED_PROTOCOL_VERSIONS: Final[frozenset[str]] = frozenset({WIRE_PROTOCOL_VERSION})

_SEMVER: Final[re.Pattern[str]] = re.compile(
    r"\A(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\Z"
)
_INITIALIZE_METHOD: Final[str] = "initialize"


class InitializeError(ValueError):
    """Raised when the initialize exchange or session gate fails."""


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def _empty_caps() -> Mapping[str, object]:
    return MappingProxyType({})


@dataclass(frozen=True, slots=True)
class InitializeParams:
    """Client params for the MCP-style ``initialize`` request."""

    protocol_version: str
    capabilities: Mapping[str, object] = field(default_factory=_empty_caps)
    client_producer_id: str | None = None

    @classmethod
    def try_create(
        cls,
        *,
        protocol_version: object,
        capabilities: object = None,
        client_producer_id: object = None,
    ) -> Result[InitializeParams]:
        if not isinstance(protocol_version, str) or _SEMVER.match(protocol_version) is None:
            return _invalid(
                "protocolVersion",
                "protocolVersion must be a semver string",
                given=repr(protocol_version),
            )
        caps_map: dict[str, object]
        if capabilities is None:
            caps_map = {}
        elif isinstance(capabilities, Mapping):
            caps_map = {}
            for key_obj, value in cast("Mapping[object, object]", capabilities).items():
                if not isinstance(key_obj, str):
                    return _invalid("capabilities", "capability keys must be strings")
                if value is None:
                    return _invalid(
                        "capabilities",
                        "null is prohibited; omit absent optional capability keys",
                    )
                caps_map[key_obj] = value
        else:
            return _invalid("capabilities", "capabilities must be an object")
        caps: Mapping[str, object] = MappingProxyType(caps_map)
        producer: str | None
        if client_producer_id is None:
            producer = None
        elif isinstance(client_producer_id, str) and client_producer_id.strip() != "":
            producer = client_producer_id
        else:
            return _invalid(
                "producer_id",
                "client_producer_id must be a non-empty string when supplied",
            )
        return Ok(
            cls(
                protocol_version=protocol_version,
                capabilities=caps,
                client_producer_id=producer,
            )
        )

    def to_params(self) -> dict[str, object]:
        out: dict[str, object] = {
            "protocolVersion": self.protocol_version,
            "capabilities": dict(self.capabilities),
        }
        if self.client_producer_id is not None:
            out["producer_id"] = self.client_producer_id
        return out


@dataclass(frozen=True, slots=True)
class InitializeResult:
    """Server result: negotiated version, capabilities, assigned ``producer_id``."""

    protocol_version: str
    capabilities: Mapping[str, object]
    producer_id: str

    def to_result(self) -> dict[str, object]:
        return {
            "protocolVersion": self.protocol_version,
            "capabilities": dict(self.capabilities),
            "producer_id": self.producer_id,
        }


@dataclass(frozen=True, slots=True)
class JsonRpcRequest:
    """JSON-RPC 2.0 request frame for the initialize exchange."""

    method: str
    id: str | int
    params: Mapping[str, object]
    jsonrpc: str = JSONRPC_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": self.method,
            "params": dict(self.params),
        }


@dataclass(frozen=True, slots=True)
class JsonRpcResponse:
    """JSON-RPC 2.0 success response frame."""

    id: str | int
    result: Mapping[str, object]
    jsonrpc: str = JSONRPC_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "result": dict(self.result),
        }


def negotiate_initialize(
    params: InitializeParams,
    *,
    server_capabilities: Mapping[str, object] | None = None,
    assign_producer_id: str | None = None,
) -> Result[InitializeResult]:
    """Negotiate ``protocolVersion`` and capabilities; assign ``producer_id``."""
    if params.protocol_version not in SUPPORTED_PROTOCOL_VERSIONS:
        return _invalid(
            "protocolVersion",
            "unsupported protocolVersion",
            given=params.protocol_version,
            supported=sorted(SUPPORTED_PROTOCOL_VERSIONS),
        )
    caps = dict(server_capabilities or {})
    # Server capabilities win on overlap; client-only keys are retained additively.
    if not params.capabilities:
        negotiated = dict(caps)
    else:
        negotiated = {key: value for key, value in caps.items() if key in params.capabilities}
        for key, value in params.capabilities.items():
            negotiated.setdefault(key, value)

    producer_id = assign_producer_id or params.client_producer_id
    if producer_id is None or producer_id.strip() == "":
        return _invalid(
            "producer_id",
            "initialize must assign a stable non-empty producer_id",
        )
    return Ok(
        InitializeResult(
            protocol_version=params.protocol_version,
            capabilities=MappingProxyType(negotiated),
            producer_id=producer_id,
        )
    )


@dataclass(slots=True)
class WireConnection:
    """Per-connection handshake state. Family messages require completed initialize."""

    _initialized: bool = False
    _producer_id: str | None = None
    _protocol_version: str | None = None
    _capabilities: Mapping[str, object] = field(default_factory=_empty_caps)

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def producer_id(self) -> str | None:
        return self._producer_id

    @property
    def protocol_version(self) -> str | None:
        return self._protocol_version

    @property
    def capabilities(self) -> Mapping[str, object]:
        return self._capabilities

    def begin_initialize(self, request: Mapping[str, object]) -> Result[JsonRpcRequest]:
        """Parse a JSON-RPC initialize request; refuse non-initialize methods pre-gate."""
        if request.get("jsonrpc") != JSONRPC_VERSION:
            return _invalid("jsonrpc", "JSON-RPC version must be 2.0")
        method = request.get("method")
        if method != _INITIALIZE_METHOD:
            return _policy(
                "method",
                "a connection that has not completed initialize cannot issue a family message",
                given=repr(method),
            )
        req_id = request.get("id")
        if not isinstance(req_id, (str, int)) or isinstance(req_id, bool):
            return _invalid("id", "JSON-RPC id must be a string or number")
        raw_params_obj = request.get("params")
        if not isinstance(raw_params_obj, Mapping):
            return _invalid("params", "initialize params must be an object")
        raw_params = cast("Mapping[object, object]", raw_params_obj)
        built = InitializeParams.try_create(
            protocol_version=raw_params.get("protocolVersion"),
            capabilities=raw_params.get("capabilities"),
            client_producer_id=raw_params.get("producer_id"),
        )
        if not isinstance(built, Ok):
            return built
        return Ok(
            JsonRpcRequest(
                method=_INITIALIZE_METHOD,
                id=req_id,
                params=built.value.to_params(),
            )
        )

    def complete_initialize(
        self,
        params: InitializeParams,
        *,
        server_capabilities: Mapping[str, object] | None = None,
        assign_producer_id: str | None = None,
        request_id: str | int = 1,
    ) -> Result[JsonRpcResponse]:
        """Finish the handshake and unlock family messages on this connection."""
        negotiated = negotiate_initialize(
            params,
            server_capabilities=server_capabilities,
            assign_producer_id=assign_producer_id,
        )
        if not isinstance(negotiated, Ok):
            return negotiated
        result = negotiated.value
        self._initialized = True
        self._producer_id = result.producer_id
        self._protocol_version = result.protocol_version
        self._capabilities = MappingProxyType(dict(result.capabilities))
        return Ok(
            JsonRpcResponse(
                id=request_id,
                result=result.to_result(),
            )
        )

    def accept_family_message(self, wire_type: object) -> Result[MessageFamily]:
        """Gate: refuse family messages until initialize completes."""
        if not self._initialized or self._producer_id is None:
            return _policy(
                "initialize",
                "a connection that has not completed initialize cannot issue a family message",
                wire_type=repr(wire_type),
            )
        try:
            name = parse_wire_type(wire_type)
        except ValueError as exc:
            return _invalid("type", str(exc), given=repr(wire_type))
        return Ok(family_of(name))
