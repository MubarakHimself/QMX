"""Story 36.1 — compose the asyncio daemon process from existing modules."""

from __future__ import annotations

import asyncio
import inspect
import runpy
import sqlite3
import sys
from pathlib import Path

from qma.core.plugins.packs import DESK_PLUGIN_PACK_IDS
from qma.core.ports.qmb import ANALYSIS_BACKTEST_PLUGIN_ID, QMB_BACKTEST_TOOL_ID
from qma.daemon.backtest import BacktestingService, CliQmbDoorTransport
from qma.daemon.process import (
    COMP_EXP_MINTED,
    HTTP_EXPERIMENT_SERVICE_MINTED,
    QMB_JSONL_MERGED_INTO_SQLITE,
    SIXTH_APPLICATION_MINTED,
    DaemonProcess,
)
from qma.wire.listener import DEFAULT_BIND_HOST, ListenerBindConfig
from qma.wire.schemas import SCHEMA_FILES
from qma.wire.vocabulary import WIRE_VOCABULARY_OWNER
from qmf.core import RefusalCategory, is_ok, is_refusal

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "daemon_process_usage.py"
PROCESS_SRC = Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon" / "process.py"


def _compose(tmp_path: Path, *, boot: str = "boot-36-1") -> DaemonProcess:
    result = DaemonProcess.compose(
        tmp_path,
        machine="test-host",
        boot_epoch_id=boot,
        bind_port=0,
    )
    assert is_ok(result), result
    return result.value


def test_compose_is_listener_sqlite_writer_and_pack_roster(tmp_path: Path) -> None:
    async def _run() -> None:
        process = _compose(tmp_path)
        try:
            bound = await process.bind()
            assert is_ok(bound), bound
            listener = bound.value
            assert listener.loopback is True
            assert listener.authentication_required is True
            assert listener.host in {DEFAULT_BIND_HOST, "127.0.0.1"}
            assert listener.port > 0
            assert listener.schema_owner == WIRE_VOCABULARY_OWNER
            assert listener.http_experiment_service is False
            assert process.sqlite_connection_count() == 1
            assert process.sqlite.thread_name == "qma-daemon-sqlite"
            assert process.sqlite.recorded_sqlite_version() == sqlite3.sqlite_version
            assert tuple(process.roster.loader.loaded_ids()) == DESK_PLUGIN_PACK_IDS
            assert process.backtesting.plugin_id == ANALYSIS_BACKTEST_PLUGIN_ID
            assert process.backtesting.tool_id == QMB_BACKTEST_TOOL_ID
            assert isinstance(process.backtesting, BacktestingService)
            assert isinstance(process.backtesting.transport, CliQmbDoorTransport)
            assert process.snapshot()["qmb_door_transport"] == "CliQmbDoorTransport"
            assert process.backtesting.scheduling_authority is None
            assert process.backtesting.parallelism is None
            assert process.backtesting.backtest_state is None
            snap = process.snapshot()
            assert snap["component"] == "COMP-QMA-DAEMON"
            assert snap["sixth_application"] is False
            assert snap["comp_exp"] is False
            assert snap["http_experiment_service"] is False
            assert snap["wire_schema_owner"] == "qma-wire"
            assert snap["wire_schema_files"] == dict(SCHEMA_FILES)
            _reader, writer = await asyncio.open_connection(listener.host, listener.port)
            writer.write(b"ping")
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            await asyncio.sleep(0.05)
            assert process.accepted_connections >= 1
        finally:
            await process.aclose()

    asyncio.run(_run())


def test_no_new_comp_http_experiment_service_or_second_runtime(tmp_path: Path) -> None:
    assert COMP_EXP_MINTED is False
    assert HTTP_EXPERIMENT_SERVICE_MINTED is False
    assert SIXTH_APPLICATION_MINTED is False
    first = _compose(tmp_path)
    try:
        refused = DaemonProcess.compose(
            tmp_path / "other",
            machine="test-host",
            boot_epoch_id="boot-36-1-b",
        )
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
        reason = str(refused.context.get("reason", "")).lower()
        assert "second" in reason and "daemon" in reason
        http = first.start_http_experiment_service()
        assert is_refusal(http)
        assert http.context["field"] == "http_experiment_service"
        assert http.context["minted"] is False
    finally:
        first.close()


def test_sqlite_stays_one_connection_and_qmb_jsonl_is_not_merged(tmp_path: Path) -> None:
    assert QMB_JSONL_MERGED_INTO_SQLITE is False
    process = _compose(tmp_path, boot="boot-36-1-sqlite")
    try:
        assert process.sqlite_connection_count() == 1
        process.sqlite.execute(
            "CREATE TABLE IF NOT EXISTS fold_probe (id INTEGER PRIMARY KEY, note TEXT)"
        )
        process.sqlite.checkpoint("PASSIVE")
        assert process.sqlite_connection_count() == 1
        assert process.qmb_jsonl_tables_present() == frozenset()
        merged = process.merge_qmb_jsonl(tmp_path / "qmb" / "run.jsonl")
        assert is_refusal(merged)
        assert merged.context["field"] == "qmb_jsonl"
        assert merged.context["merged"] is False
        owned = merged.context["qmb_owned"]
        assert isinstance(owned, (list, tuple))
        assert "run_ledger" in owned
        assert is_refusal(process.import_qmb_package())
        assert is_refusal(process.take_qmb_owned_concern("run_ledger"))
        source = PROCESS_SRC.read_text(encoding="utf-8")
        assert "import qmb" not in source
        assert "from qmb" not in source
        assert "http.server" not in source
        assert "COMP-EXP" in source
        assert inspect.getsource(DaemonProcess.compose)
    finally:
        process.close()


def test_unauthenticated_and_plaintext_non_loopback_are_startup_refusals(
    tmp_path: Path,
) -> None:
    unauth = ListenerBindConfig.try_create(require_authentication=False)
    assert is_ok(unauth)
    refused_auth = DaemonProcess.compose(
        tmp_path,
        machine="test-host",
        boot_epoch_id="boot-unauth",
        listener=unauth.value,
    )
    assert is_refusal(refused_auth)
    assert refused_auth.context["field"] == "require_authentication"
    assert refused_auth.context["startup"] is True

    plaintext = ListenerBindConfig.try_create(
        host="10.0.0.8",
        websocket_scheme="ws",
        query_scheme="http",
        require_authentication=True,
        operator_recorded_config=True,
    )
    assert is_ok(plaintext)
    refused_plain = DaemonProcess.compose(
        tmp_path,
        machine="test-host",
        boot_epoch_id="boot-plain",
        listener=plaintext.value,
    )
    assert is_refusal(refused_plain)
    assert refused_plain.context["startup"] is True
    assert "plaintext" in str(refused_plain.context["reason"])


def test_does_not_invent_a_second_wire_schema(tmp_path: Path) -> None:
    process = _compose(tmp_path, boot="boot-36-1-wire")
    try:
        assert process.wire_schema_owner == WIRE_VOCABULARY_OWNER
        assert dict(process.wire_schema_files) == dict(SCHEMA_FILES)
        assert "envelope" in process.wire_schema_files
        assert "experiment_http" not in process.wire_schema_files
        source = PROCESS_SRC.read_text(encoding="utf-8")
        assert "schema.json" not in source
        assert "from qma.wire.listener import" in source
        assert "from qma.wire.schemas import SCHEMA_FILES" in source
        assert "from qma.wire.vocabulary import WIRE_VOCABULARY_OWNER" in source
    finally:
        process.close()


def test_process_module_does_not_import_qmb() -> None:
    before = {name for name in sys.modules if name == "qmb" or name.startswith("qmb.")}
    import qma.daemon.process as proc

    after = {name for name in sys.modules if name == "qmb" or name.startswith("qmb.")}
    assert after == before
    assert "import qmb" not in inspect.getsource(proc)
    assert "from qmb" not in inspect.getsource(proc)


def test_example_script() -> None:
    namespace = runpy.run_path(str(EXAMPLE), run_name="__main__")
    assert namespace["main"] is not None
