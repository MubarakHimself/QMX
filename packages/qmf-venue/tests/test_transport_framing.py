"""cTrader Open API framing + async exemption surface (Story 24.1 / DEC-0196)."""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path

from qmf.core import (
    Account,
    AccountRole,
    Ok,
    SinkAck,
    VenueId,
    is_ok,
    is_refusal,
)
from qmf.venue.connection import (
    ASYNC_CONFORMANCE_EXEMPTION,
    CTRADER_OPEN_API_PORT,
    ConnectionManager,
    decode_framed_payload,
    encode_framed_payload,
    venue_writer_id,
)

_VENUE_SRC = Path(__file__).resolve().parents[1] / "src" / "qmf" / "venue"


def test_exemption_constant_is_exact_module_name() -> None:
    assert ASYNC_CONFORMANCE_EXEMPTION == "qmf.venue.connection"


def test_open_api_port_is_5035() -> None:
    assert CTRADER_OPEN_API_PORT == 5035


def test_frame_round_trip() -> None:
    payload = b"\x08\x91\x12\x04abcd"
    framed = encode_framed_payload(payload)
    assert is_ok(framed)
    decoded = decode_framed_payload(framed.value)
    assert is_ok(decoded)
    assert decoded.value == payload


def test_frame_rejects_non_bytes_and_truncated() -> None:
    assert is_refusal(encode_framed_payload("not-bytes"))
    assert is_refusal(decode_framed_payload("not-bytes"))
    assert is_refusal(decode_framed_payload(b"\x00"))


def test_async_only_allowed_in_connection_module() -> None:
    """Roster async-conformance: only qmf.venue.connection may use asyncio/async def."""
    offenders: list[str] = []
    for path in sorted(_VENUE_SRC.rglob("*.py")):
        if path.name == "connection.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                offenders.append(f"{path.name}: async def {node.name}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "asyncio" or alias.name.startswith("asyncio."):
                        offenders.append(f"{path.name}: import {alias.name}")
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and (node.module == "asyncio" or node.module.startswith("asyncio."))
            ):
                offenders.append(f"{path.name}: from {node.module}")
    assert offenders == [], f"async outside exemption module: {offenders}"


def test_connection_module_imports_asyncio_and_ssl() -> None:
    tree = ast.parse(
        (_VENUE_SRC / "connection.py").read_text(encoding="utf-8"),
        filename="connection.py",
    )
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    assert "asyncio" in names
    assert "ssl" in names


class _MemStore:
    def read(self, ref: object, /) -> object:
        raise AssertionError("unused")

    def atomic_replace(self, ref: object, value: object, /) -> object:
        raise AssertionError("unused")


class _MemSink:
    def emit(self, observation: object, /) -> Ok[SinkAck]:
        return Ok(SinkAck())

    def append(self, event: object, /) -> Ok[SinkAck]:
        return Ok(SinkAck())

    def write(self, record: object, /) -> Ok[SinkAck]:
        return Ok(SinkAck())


def _manager() -> ConnectionManager:
    venue = VenueId.try_create("venue-ctrader-demo")
    assert is_ok(venue)
    account = Account.try_create("acct-1", venue.value, AccountRole.DEMO)
    assert is_ok(account)
    writer = venue_writer_id("machine", "role", venue.value, account.value, "boot-1")
    assert is_ok(writer)
    sink = _MemSink()
    built = ConnectionManager.try_create(writer.value, _MemStore(), sink, sink, sink)
    assert is_ok(built)
    return built.value


def test_attach_and_framed_io_on_loopback() -> None:
    async def _run() -> None:
        manager = _manager()
        assert manager.transport_open is False
        assert is_refusal(manager.attach_transport(object(), object(), proto_tag=91))

        received: list[bytes] = []

        async def _handle(
            client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter
        ) -> None:
            header = await client_reader.readexactly(4)
            length = int.from_bytes(header, "big")
            body = await client_reader.readexactly(length)
            received.append(body)
            client_writer.write(header + body)
            await client_writer.drain()
            client_writer.close()
            await client_writer.wait_closed()

        server = await asyncio.start_server(_handle, "127.0.0.1", 0)
        assert server.sockets is not None
        port = server.sockets[0].getsockname()[1]
        client_reader, client_writer = await asyncio.open_connection("127.0.0.1", port)
        attached = manager.attach_transport(client_reader, client_writer, proto_tag=91)
        assert is_ok(attached)
        assert manager.transport_open is True
        assert manager.proto_tag == 91
        sent = await manager.send_framed(b"ping-payload")
        assert is_ok(sent)
        echoed = await manager.recv_framed()
        assert is_ok(echoed)
        assert echoed.value == b"ping-payload"
        assert received == [b"ping-payload"]
        closed = await manager.close_transport()
        assert is_ok(closed)
        assert manager.transport_open is False
        server.close()
        await server.wait_closed()

    asyncio.run(_run())


def test_connect_open_api_never_creates_a_loop() -> None:
    """connect_open_api requires a running loop; it never creates one (DEC-0243)."""
    manager = _manager()
    source = (_VENUE_SRC / "connection.py").read_text(encoding="utf-8")
    assert "asyncio.run(" not in source
    assert "new_event_loop" not in source
    assert "set_event_loop" not in source
    # Proto tag must be injected, never hardcoded as the sole source of truth.
    assert "registry:venue_protocol_artifact" in source
    assert manager.transport_open is False
