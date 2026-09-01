"""Story 41.1 — initialize handshake and family gate (FR-Q13)."""

from __future__ import annotations

from typing import cast

from qma.wire import (
    JSONRPC_VERSION,
    WIRE_PROTOCOL_VERSION,
    InitializeParams,
    MessageFamily,
    WireConnection,
    WireEnvelope,
    load_schema,
    validate_family_payload,
    validate_instance,
    validate_wire_envelope_dict,
)
from qmf.core.refusal import Ok, is_ok, is_refusal

_TEST_CRED_REF = "cred://models/openai"


def _authed_conn() -> WireConnection:
    conn = WireConnection()
    authed = conn.authenticate(_TEST_CRED_REF, principal_class="operator")
    assert isinstance(authed, Ok)
    return conn


def test_initialize_negotiates_semver_and_assigns_producer_id() -> None:
    conn = _authed_conn()
    assert conn.initialized is False
    assert conn.authenticated is True
    assert conn.credential_ref == _TEST_CRED_REF

    params = InitializeParams.try_create(
        protocol_version=WIRE_PROTOCOL_VERSION,
        capabilities={"commands": True, "events": True},
        client_producer_id="hint-client",
    )
    assert isinstance(params, Ok)

    response = conn.complete_initialize(
        params.value,
        server_capabilities={"commands": True, "events": True, "queries": True},
        assign_producer_id="producer-stable-1",
        request_id=7,
    )
    assert isinstance(response, Ok)
    body = response.value.to_dict()
    result = body["result"]
    assert isinstance(result, dict)
    assert body["jsonrpc"] == JSONRPC_VERSION
    assert body["id"] == 7
    assert result["protocolVersion"] == WIRE_PROTOCOL_VERSION
    assert result["producer_id"] == "producer-stable-1"
    assert conn.initialized is True
    assert conn.producer_id == "producer-stable-1"


def test_jsonrpc_initialize_request_round_trip() -> None:
    conn = _authed_conn()
    raw = {
        "jsonrpc": "2.0",
        "id": "init-1",
        "method": "initialize",
        "params": {
            "protocolVersion": WIRE_PROTOCOL_VERSION,
            "capabilities": {"commands": True},
        },
    }
    parsed = conn.begin_initialize(raw)
    assert isinstance(parsed, Ok)
    assert parsed.value.method == "initialize"
    built = InitializeParams.try_create(
        protocol_version=WIRE_PROTOCOL_VERSION,
        capabilities={"commands": True},
    )
    assert isinstance(built, Ok)
    finished = conn.complete_initialize(
        built.value,
        assign_producer_id="p-9",
        request_id="init-1",
    )
    assert is_ok(finished)


def test_family_message_refused_before_initialize() -> None:
    conn = _authed_conn()
    refused = conn.accept_family_message("start_mission")
    assert is_refusal(refused)
    assert refused.context["field"] == "initialize"

    # Non-initialize JSON-RPC methods are also blocked pre-handshake.
    blocked = conn.begin_initialize(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "start_mission",
            "params": {},
        }
    )
    assert is_refusal(blocked)


def test_protocol_bytes_refused_before_authentication() -> None:
    conn = WireConnection()
    assert conn.authenticated is False
    refused = conn.begin_initialize(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": WIRE_PROTOCOL_VERSION},
        }
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "authentication"


def test_family_message_accepted_after_initialize_and_schema_validated() -> None:
    conn = _authed_conn()
    params = InitializeParams.try_create(protocol_version=WIRE_PROTOCOL_VERSION)
    assert isinstance(params, Ok)
    assert is_ok(
        conn.complete_initialize(params.value, assign_producer_id="producer-a", request_id=1)
    )
    accepted = conn.accept_family_message("start_mission")
    assert isinstance(accepted, Ok)
    assert accepted.value is MessageFamily.COMMAND
    assert conn.protocol_version is not None
    assert conn.producer_id is not None

    envelope = WireEnvelope.try_create(
        v=conn.protocol_version,
        type="start_mission",
        id="cmd-1",
        producer_id=conn.producer_id,
        correlation_id="corr-1",
        scope_path=[{"kind": "desk", "id": "research"}],
        payload={"goal": "scout"},
    )
    assert isinstance(envelope, Ok)
    assert is_ok(validate_wire_envelope_dict(envelope.value.to_dict()))
    assert is_ok(validate_family_payload("start_mission", {"goal": "scout"}))
    assert is_ok(validate_family_payload("list_missions", {}))
    assert is_ok(validate_family_payload("mission.updated", {"state": "running"}))


def test_initialize_and_family_schemas_load() -> None:
    init_schema = load_schema("initialize")
    assert init_schema["required"] == ["protocolVersion"]
    assert "credential_ref" in cast(dict[str, object], init_schema["properties"])
    assert is_ok(
        validate_instance(
            {
                "protocolVersion": WIRE_PROTOCOL_VERSION,
                "capabilities": {},
                "credential_ref": _TEST_CRED_REF,
            },
            "initialize",
        )
    )

    def _name_enum(schema_name: str) -> list[object]:
        props_obj = load_schema(schema_name)["properties"]
        assert isinstance(props_obj, dict)
        props = cast(dict[str, object], props_obj)
        name_obj = props["name"]
        assert isinstance(name_obj, dict)
        name_schema = cast(dict[str, object], name_obj)
        enum_obj = name_schema["enum"]
        assert isinstance(enum_obj, list)
        return cast(list[object], enum_obj)

    assert len(_name_enum("command")) == 9
    assert len(_name_enum("query")) == 8
    assert len(_name_enum("event")) == 10
