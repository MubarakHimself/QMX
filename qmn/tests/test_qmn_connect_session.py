"""Story 31.2 — production live sessions open through connect_open_api."""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from typing import TypeVar, cast

import pytest
import tomllib
from qmf.core import (
    Account,
    AccountRole,
    DataDrivenClock,
    Instant,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    SecretRef,
    SecretValue,
    SinkAck,
    SinkResult,
    TypedRefusal,
    VenueId,
    World,
    is_ok,
    is_refusal,
)
from qmf.venue.capabilities import ErrorMap
from qmf.venue.connection import (
    CTRADER_OPEN_API_PORT,
    AccountBinding,
    ConnectionManager,
    venue_writer_id,
)
from qmn.venue import (
    ConformanceDouble,
    LiveCTraderClient,
    ReplayAdapter,
    VenueClientKind,
    VenueClientPort,
    select_venue_client,
)
from qmn.venue.port import VenueClientPort as PortInVenuePort

T = TypeVar("T")

_BOOT = "boot-epoch-connect-31-2"
_WALL_NS = 1_724_000_000 * 1_000_000_000
_CRED_REF = "cred-ref-connect312"
_PLAINTEXT = "plaintext-refresh-token-value-xyz"
_QMN_ROOT = Path(__file__).resolve().parents[1]
_QMN_SRC = _QMN_ROOT / "src" / "qmn"
_WORKSPACE = _QMN_ROOT.parent
_VENUE_SRC = _WORKSPACE / "packages" / "qmf-venue" / "src" / "qmf" / "venue"
_PROTO_TAG = 91


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]) -> TypedRefusal:
    assert is_refusal(result), result
    return result


def _venue(value: str = "venue-ctrader-demo") -> VenueId:
    return _ok(VenueId.try_create(value))


def _account(venue: VenueId | None = None) -> Account:
    return _ok(Account.try_create("acct-live-1", venue or _venue(), AccountRole.DEMO))


def _clock(*, frames: int = 8) -> DataDrivenClock:
    walls = tuple(_ok(Instant.try_create(_WALL_NS + i * 1_000_000)) for i in range(frames))
    monos = tuple(5_000_000_000 + i * 1_000_000 for i in range(frames))
    return DataDrivenClock(boot_epoch_id=_BOOT, wall_instants=walls, monotonic_ns=monos)


def _error_map() -> ErrorMap:
    return _ok(ErrorMap.try_create(1, []))


def _secret_ref() -> SecretRef:
    return _ok(SecretRef.try_create(_CRED_REF))


class FakeSecretStore:
    def __init__(self) -> None:
        self._values: dict[SecretRef, SecretValue] = {}

    def preload(self, value: SecretValue) -> None:
        self._values[value.ref] = value

    def read(self, ref: SecretRef, /) -> Result[SecretValue]:
        if ref not in self._values:
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.NO,
                context={"field": "credential", "reason": "missing", "secret_ref": ref.value},
            )
        return Ok(self._values[ref])

    def atomic_replace(self, ref: SecretRef, new_value: SecretValue, /) -> Result[SecretRef]:
        self._values[ref] = new_value
        return Ok(ref)


class FakeSink:
    def emit(self, observation: object, /) -> SinkResult:
        del observation
        return Ok(SinkAck())

    def append(self, event: object, /) -> SinkResult:
        del event
        return Ok(SinkAck())

    def write(self, record: object, /) -> SinkResult:
        del record
        return Ok(SinkAck())


def _manager(venue: VenueId, account: Account, store: FakeSecretStore) -> ConnectionManager:
    writer = _ok(venue_writer_id("vps-fra-01", "ctrader-adapter", venue, account, _BOOT))
    sink = FakeSink()
    return _ok(ConnectionManager.try_create(writer, store, sink, sink, sink))


def _live_client(**kwargs: object) -> LiveCTraderClient:
    built = LiveCTraderClient.try_create(
        World.LIVE,
        _venue(),
        clock=_clock(),
        error_map=_error_map(),
        **kwargs,
    )
    return _ok(built)


def _walk_connect_open_api_calls(root: Path) -> list[str]:
    hits: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "connect_open_api"
            ):
                hits.append(str(path.relative_to(root)))
    return hits


def test_qmn_venue_live_is_production_caller_of_connect_open_api() -> None:
    hits = _walk_connect_open_api_calls(_QMN_SRC)
    live_hits = [item for item in hits if item.replace("\\", "/").endswith("venue/live.py")]
    assert live_hits, hits
    assert all(item.replace("\\", "/").startswith("venue/") for item in hits), hits


def test_live_client_never_constructs_a_loop_or_connection_manager() -> None:
    source = (_QMN_SRC / "venue" / "live.py").read_text(encoding="utf-8")
    assert "asyncio.run(" not in source
    assert "new_event_loop" not in source
    assert "set_event_loop" not in source
    tree = ast.parse(source, filename="live.py")
    constructions: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "try_create":
            owner = func.value
            if isinstance(owner, ast.Name) and owner.id == "ConnectionManager":
                constructions.append("ConnectionManager.try_create")
        if isinstance(func, ast.Name) and func.id == "ConnectionManager":
            constructions.append("ConnectionManager(...)")
    assert constructions == []
    assert "registry:venue_protocol_artifact" in source


def test_credential_free_open_session_does_not_call_connect_open_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    async def _fake(
        self: ConnectionManager,
        host: object,
        *,
        proto_tag: object,
        port: object = CTRADER_OPEN_API_PORT,
        ssl_context: object = None,
        server_hostname: object = None,
    ) -> Result[bool]:
        del self, ssl_context, server_hostname
        calls.append((host, proto_tag, port))
        return Ok(True)

    monkeypatch.setattr(ConnectionManager, "connect_open_api", _fake)
    client = _live_client()
    opened = _ok(client.open_session(_account(client.venue_id)))
    assert opened is True
    assert client.account is not None
    assert calls == []
    assert is_ok(client.close_session())


def test_tests_only_connection_manager_still_opens_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    async def _fake(
        self: ConnectionManager,
        host: object,
        *,
        proto_tag: object,
        port: object = CTRADER_OPEN_API_PORT,
        ssl_context: object = None,
        server_hostname: object = None,
    ) -> Result[bool]:
        del self, host, proto_tag, port, ssl_context, server_hostname
        calls.append(True)
        return Ok(True)

    monkeypatch.setattr(ConnectionManager, "connect_open_api", _fake)
    venue = _venue()
    account = _account(venue)
    store = FakeSecretStore()
    cm = _manager(venue, account, store)
    client = _live_client(connection_manager=cm)
    _ok(client.open_session(account))
    assert calls == []
    assert cm.transport_open is False
    assert cm.health().open_session_count == 0


def test_open_session_calls_connect_open_api_on_injected_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loop = asyncio.new_event_loop()
    calls: list[dict[str, object]] = []

    async def _fake(
        self: ConnectionManager,
        host: object,
        *,
        proto_tag: object,
        port: object = CTRADER_OPEN_API_PORT,
        ssl_context: object = None,
        server_hostname: object = None,
    ) -> Result[bool]:
        del ssl_context, server_hostname
        running = asyncio.get_running_loop()
        calls.append(
            {
                "host": host,
                "proto_tag": proto_tag,
                "port": port,
                "manager_id": id(self),
                "loop_id": id(running),
            }
        )
        return Ok(True)

    monkeypatch.setattr(ConnectionManager, "connect_open_api", _fake)
    venue = _venue()
    account = _account(venue)
    store = FakeSecretStore()
    ref = _secret_ref()
    store.preload(_ok(SecretValue.try_create(ref, _PLAINTEXT)))
    cm = _manager(venue, account, store)
    try:
        client = _live_client(
            connection_manager=cm,
            event_loop=loop,
            open_api_host="demo.ctraderapi.com",
            proto_tag=_PROTO_TAG,
            credential_ref=ref,
        )
        opened = _ok(client.open_session(account))
        assert opened is True
        assert calls == [
            {
                "host": "demo.ctraderapi.com",
                "proto_tag": _PROTO_TAG,
                "port": CTRADER_OPEN_API_PORT,
                "manager_id": id(cm),
                "loop_id": id(loop),
            }
        ]
        assert CTRADER_OPEN_API_PORT == 5035
        assert cm.holds_secret(ref) is True
        health = cm.health()
        assert ref.value in health.held_secret_ref_ids
        assert _PLAINTEXT not in repr(health)
        assert _PLAINTEXT not in repr(client)
        binding = _ok(AccountBinding.try_create(venue, account, World.LIVE, ref))
        identity = binding.fp1_identity()
        assert ref.value not in identity.values()
        assert _PLAINTEXT not in str(identity)
        assert is_ok(client.close_session())
        assert cm.holds_secret(ref) is False
    finally:
        loop.close()


def test_connect_refusal_does_not_leave_session_or_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loop = asyncio.new_event_loop()

    async def _fail(
        self: ConnectionManager,
        host: object,
        *,
        proto_tag: object,
        port: object = CTRADER_OPEN_API_PORT,
        ssl_context: object = None,
        server_hostname: object = None,
    ) -> Result[bool]:
        del self, proto_tag, ssl_context, server_hostname
        return TypedRefusal(
            category=RefusalCategory.TRANSIENT_VENUE_FAILURE,
            retryability=Retryability.AFTER_CONDITION,
            context={
                "field": "transport",
                "reason": "TLS open to the cTrader Open API failed",
                "host": host,
                "port": port,
                "error": "OSError",
            },
            after_condition_descriptor="network recovery or operator reconnect",
        )

    monkeypatch.setattr(ConnectionManager, "connect_open_api", _fail)
    venue = _venue()
    account = _account(venue)
    store = FakeSecretStore()
    ref = _secret_ref()
    store.preload(_ok(SecretValue.try_create(ref, _PLAINTEXT)))
    cm = _manager(venue, account, store)
    try:
        client = _live_client(
            connection_manager=cm,
            event_loop=loop,
            open_api_host="demo.ctraderapi.com",
            proto_tag=_PROTO_TAG,
            credential_ref=ref,
        )
        refused = _refusal(client.open_session(account))
        assert refused.category is RefusalCategory.TRANSIENT_VENUE_FAILURE
        assert _PLAINTEXT not in repr(refused.context)
        assert _PLAINTEXT not in str(refused.context)
        assert client.account is None
        assert cm.holds_secret(ref) is False
    finally:
        loop.close()


def test_secret_value_is_refused_as_credential_ref() -> None:
    ref = _secret_ref()
    value = _ok(SecretValue.try_create(ref, _PLAINTEXT))
    venue = _venue()
    account = _account(venue)
    store = FakeSecretStore()
    cm = _manager(venue, account, store)
    refused = _refusal(
        LiveCTraderClient.try_create(
            World.LIVE,
            venue,
            clock=_clock(),
            error_map=_error_map(),
            connection_manager=cm,
            credential_ref=value,
        )
    )
    assert refused.context["field"] == "credential_ref"
    assert refused.context["given"] == "SecretValue"
    assert _PLAINTEXT not in repr(refused.context)


def test_production_host_without_manager_or_loop_is_refused() -> None:
    loop = asyncio.new_event_loop()
    venue = _venue()
    account = _account(venue)
    cm = _manager(venue, account, FakeSecretStore())
    try:
        no_manager = _refusal(
            LiveCTraderClient.try_create(
                World.LIVE,
                venue,
                clock=_clock(),
                error_map=_error_map(),
                event_loop=loop,
                open_api_host="demo.ctraderapi.com",
                proto_tag=_PROTO_TAG,
            )
        )
        assert no_manager.context["field"] == "connection_manager"

        no_loop = _refusal(
            LiveCTraderClient.try_create(
                World.LIVE,
                venue,
                clock=_clock(),
                error_map=_error_map(),
                connection_manager=cm,
                open_api_host="demo.ctraderapi.com",
                proto_tag=_PROTO_TAG,
            )
        )
        assert no_loop.context["field"] == "event_loop"

        no_tag = _refusal(
            LiveCTraderClient.try_create(
                World.LIVE,
                venue,
                clock=_clock(),
                error_map=_error_map(),
                connection_manager=cm,
                event_loop=loop,
                open_api_host="demo.ctraderapi.com",
            )
        )
        assert no_tag.context["field"] == "proto_tag"
    finally:
        loop.close()


def test_conformance_double_session_lifecycle_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    async def _fake(
        self: ConnectionManager,
        host: object,
        *,
        proto_tag: object,
        port: object = CTRADER_OPEN_API_PORT,
        ssl_context: object = None,
        server_hostname: object = None,
    ) -> Result[bool]:
        del self, host, proto_tag, port, ssl_context, server_hostname
        calls.append(True)
        return Ok(True)

    monkeypatch.setattr(ConnectionManager, "connect_open_api", _fake)
    venue = _venue("conformance:ctrader-demo")
    client = _ok(ConformanceDouble.try_create(World.LIVE, venue))
    account = _account(venue)
    _ok(client.open_session(account))
    assert isinstance(client, VenueClientPort)
    assert calls == []
    assert is_ok(client.close_session())


def test_replay_compose_never_invokes_connect_open_api() -> None:
    selected = _ok(select_venue_client(World.REPLAY, _venue()))
    assert selected.kind is VenueClientKind.REPLAY
    adapter = _ok(ReplayAdapter.try_create(World.REPLAY, selected.venue_id))
    _ok(adapter.open_session(_account(selected.venue_id)))
    assert adapter.socket_opened is False
    assert adapter.credential_resolved is False
    live = LiveCTraderClient.try_create(
        World.REPLAY,
        selected.venue_id,
        clock=_clock(),
        error_map=_error_map(),
    )
    assert is_refusal(live)
    replay_roots = (_QMN_SRC / "replay", _QMN_SRC / "venue" / "replay.py")
    for root in replay_roots:
        paths = [root] if root.is_file() else sorted(root.rglob("*.py"))
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr == "connect_open_api":
                    raise AssertionError(f"replay invoked connect_open_api in {path}")


def test_venue_client_port_remains_node_minted() -> None:
    assert PortInVenuePort is VenueClientPort
    port_src = (_QMN_SRC / "venue" / "port.py").read_text(encoding="utf-8")
    assert "class VenueClientPort" in port_src
    for path in sorted(_VENUE_SRC.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
            if isinstance(node, ast.ClassDef) and node.name == "VenueClientPort":
                raise AssertionError(f"VenueClientPort realized in {path}")


def test_protobuf_runtime_remains_pinned_7_36_0() -> None:
    data = tomllib.loads(
        (_WORKSPACE / "packages" / "qmf-venue" / "pyproject.toml").read_text(encoding="utf-8")
    )
    deps = cast("list[str]", data["project"]["dependencies"])
    assert "protobuf==7.36.0" in deps
    assert not any(item.startswith("protobuf==7.36.1") for item in deps)


@pytest.mark.live
def test_live_session_smoke_against_demo_ctraderapi_com_is_separately_gated() -> None:
    """AR-C08: tagged live-session smoke is not a Story 31.2 credential-free gate."""
    pytest.skip("Spotware sandbox token not a Story 31.2 prerequisite (AR-C08)")
