"""Story 61.1 — qma-daemon emits stdlib JSON-lines operator logs."""

from __future__ import annotations

import json
import logging
import runpy
from io import StringIO
from pathlib import Path

from qma.daemon.journal.stores import CLOSED_INDEPENDENT_STORES, CLOSED_STORE_NAMES
from qma.daemon.operator_log import (
    EPIC_60_TIP_SHA,
    FORBIDDEN_LOG_KEYS,
    FOURTH_OBSERVABILITY_COMP_MINTED,
    LOGS_ARE_NOT_EVIDENCE,
    LOGS_ARE_NOT_JOURNALS,
    LOGS_ENTER_FP1_IDENTITY,
    LOGS_SATISFY_CT13_EVIDENCE,
    OPERATOR_LOG_INSPECT_SHA,
    OPERATOR_LOG_JOIN_FIELDS,
    OPERATOR_LOG_REQUIRED_FIELDS,
    OPERATOR_LOG_SQLITE_CLASS_MINTED,
    OPERATOR_LOGGER_EXISTED_AT_EPIC_60_TIP,
    OPERATOR_LOGGER_EXISTED_AT_INSPECT_SHA,
    OTEL_REMAINS_EXPORT_PORT_ONLY,
    QMN_FAILURES_MD_EXTENDED,
    TELEMETRY_STORE_REMAINS_TRACE_METRIC_PLANE,
    OperatorLogContext,
    bind_log_context,
    claim_operator_logger_at_inspect_sha,
    configure_daemon_logging,
    emit_operator_event,
    fingerprint_operator_log,
    log_record_is_journal_evidence,
    refuse_fourth_observability_comp,
    refuse_operator_log_sqlite_class,
    refuse_qmn_failures_extension,
    reset_log_context,
)
from qma.daemon.plugins import research_corpus_plugin_load_config
from qma.daemon.process import DaemonProcess
from qma.daemon.telemetry import DAEMON_CORE_OTEL_IMPORT_FORBIDDEN, TelemetryStore
from qmf.core import is_ok, is_refusal

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "operator_log_usage.py"


def _lines(stream: StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


def _logger(stream: StringIO, name: str) -> logging.Logger:
    handler = logging.StreamHandler(stream)
    return configure_daemon_logging(handler=handler, logger_name=name)


def _compose(tmp_path: Path, *, boot: str, stream: StringIO) -> DaemonProcess:
    seed = tmp_path / "seed-corpus"
    seed.mkdir(exist_ok=True)
    result = DaemonProcess.compose(
        tmp_path,
        machine="test-host",
        boot_epoch_id=boot,
        bind_port=0,
        plugin_load_configs=research_corpus_plugin_load_config(seed),
        log_handler=logging.StreamHandler(stream),
    )
    assert is_ok(result), result
    return result.value


def test_inspect_sha_honesty_operator_logger_absent_at_34c148b_and_7223e1a() -> None:
    assert OPERATOR_LOG_INSPECT_SHA == "34c148b"
    assert EPIC_60_TIP_SHA == "7223e1a"
    assert OPERATOR_LOGGER_EXISTED_AT_INSPECT_SHA is False
    assert OPERATOR_LOGGER_EXISTED_AT_EPIC_60_TIP is False
    claimed = claim_operator_logger_at_inspect_sha(True)
    assert is_refusal(claimed)
    assert claimed.context["existed_at_inspect_sha"] is False
    assert claimed.context["inspect_sha"] == "34c148b"
    assert claimed.context["existed_at_epic_60_tip"] is False
    assert is_ok(claim_operator_logger_at_inspect_sha(False))
    bad = claim_operator_logger_at_inspect_sha("maybe")
    assert is_refusal(bad)


def test_json_lines_require_ts_level_event_correlation_id() -> None:
    stream = StringIO()
    logger = _logger(stream, "qma.daemon.operator.test.required")
    written = emit_operator_event(
        logger,
        logging.WARNING,
        "public_operation.failed",
        correlation_id="corr-1",
    )
    assert is_ok(written)
    rows = _lines(stream)
    assert len(rows) == 1
    payload = rows[0]
    for field in OPERATOR_LOG_REQUIRED_FIELDS:
        assert field in payload, field
    ts = payload["ts"]
    assert isinstance(ts, str)
    assert ts.endswith("Z")
    assert "T" in ts
    assert payload["level"] == "WARNING"
    assert payload["event"] == "public_operation.failed"
    assert payload["correlation_id"] == "corr-1"
    for field in OPERATOR_LOG_JOIN_FIELDS:
        assert field not in payload
    assert payload["is_journal"] is False
    assert payload["ct13_evidence"] is False
    assert payload["fp1_identity"] is False


def test_join_fields_appear_only_when_known() -> None:
    stream = StringIO()
    logger = _logger(stream, "qma.daemon.operator.test.join")
    written = emit_operator_event(
        logger,
        logging.INFO,
        "task_graph.run",
        correlation_id="corr-run",
        instance_id="inst:1",
        op_id="qmb.analysis.project",
        logical_invocation_id="inv:1",
        graph_run_id="graph:1",
    )
    assert is_ok(written)
    payload = _lines(stream)[0]
    assert payload["instance_id"] == "inst:1"
    assert payload["op_id"] == "qmb.analysis.project"
    assert payload["logical_invocation_id"] == "inv:1"
    assert payload["graph_run_id"] == "graph:1"

    stream_blank = StringIO()
    logger_blank = _logger(stream_blank, "qma.daemon.operator.test.join-blank")
    emit_operator_event(
        logger_blank,
        logging.INFO,
        "task_graph.run",
        correlation_id="corr-run",
        instance_id="",
        op_id=None,
    )
    blank = _lines(stream_blank)[0]
    assert "instance_id" not in blank
    assert "op_id" not in blank


def test_context_bind_stamps_join_fields() -> None:
    stream = StringIO()
    logger = _logger(stream, "qma.daemon.operator.test.ctx")
    token = bind_log_context(
        OperatorLogContext(
            correlation_id="corr-ctx",
            instance_id="inst:ctx",
            op_id="op.ctx",
        )
    )
    try:
        emit_operator_event(
            logger,
            logging.INFO,
            "public_operation.run",
            correlation_id="corr-ctx",
        )
    finally:
        reset_log_context(token)
    payload = _lines(stream)[0]
    assert payload["correlation_id"] == "corr-ctx"
    assert payload["instance_id"] == "inst:ctx"
    assert payload["op_id"] == "op.ctx"


def test_logs_never_secrets_journal_evidence_or_fp1() -> None:
    assert "secret_value" in FORBIDDEN_LOG_KEYS
    assert LOGS_ARE_NOT_JOURNALS is True
    assert LOGS_ARE_NOT_EVIDENCE is True
    assert LOGS_SATISFY_CT13_EVIDENCE is False
    assert LOGS_ENTER_FP1_IDENTITY is False
    assert log_record_is_journal_evidence() is False
    stream = StringIO()
    logger = _logger(stream, "qma.daemon.operator.test.secret")
    refused = emit_operator_event(
        logger,
        logging.INFO,
        "public_operation.run",
        correlation_id="corr-secret",
        secret_value="leak",
    )
    assert is_refusal(refused)
    keys = refused.context["keys"]
    assert isinstance(keys, (list, tuple))
    assert "secret_value" in keys
    assert _lines(stream) == []
    assert is_refusal(fingerprint_operator_log({"event": "public_operation.run"}))
    empty = emit_operator_event(
        logger,
        logging.INFO,
        "",
        correlation_id="corr-secret",
    )
    assert is_refusal(empty)
    missing = emit_operator_event(
        logger,
        logging.INFO,
        "public_operation.run",
        correlation_id="  ",
    )
    assert is_refusal(missing)


def test_refuse_fourth_observability_comp_sqlite_class_and_qmn_failures() -> None:
    assert FOURTH_OBSERVABILITY_COMP_MINTED is False
    assert OPERATOR_LOG_SQLITE_CLASS_MINTED is False
    assert QMN_FAILURES_MD_EXTENDED is False
    assert TELEMETRY_STORE_REMAINS_TRACE_METRIC_PLANE is True
    assert OTEL_REMAINS_EXPORT_PORT_ONLY is DAEMON_CORE_OTEL_IMPORT_FORBIDDEN
    assert "operator_logs" not in CLOSED_STORE_NAMES
    assert "operator_logs" not in CLOSED_INDEPENDENT_STORES
    fourth = refuse_fourth_observability_comp()
    assert is_refusal(fourth)
    assert fourth.context["minted"] is False
    sqlite = refuse_operator_log_sqlite_class()
    assert is_refusal(sqlite)
    assert sqlite.context["operator_logs_on_closed_list"] is False
    qmn = refuse_qmn_failures_extension()
    assert is_refusal(qmn)
    assert qmn.context["extended"] is False
    store = TelemetryStore()
    assert store.store_name == "telemetry_store"
    assert store.announcement_exempt is True


def test_daemon_process_emits_json_lines_for_compose_and_public_run(
    tmp_path: Path,
) -> None:
    stream = StringIO()
    process = _compose(tmp_path, boot="boot-61-1", stream=stream)
    try:
        snap = process.snapshot()
        assert snap["component"] == "COMP-QMA-DAEMON"
        assert snap["operator_json_lines"] is True
        assert snap["operator_logs_are_journal"] is False
        assert snap["operator_logs_enter_fp1"] is False
        assert snap["fourth_observability_comp"] is False
        assert snap["operator_log_sqlite_class"] is False
        assert snap["telemetry_store_remains"] is True
        composed_rows = _lines(stream)
        assert composed_rows
        first = composed_rows[0]
        for field in OPERATOR_LOG_REQUIRED_FIELDS:
            assert field in first
        assert first["event"] == "daemon.composed"
        assert first["correlation_id"] == "daemon-process:boot-61-1"
        assert first["is_journal"] is False

        ran = process.emit_operator_event(
            "public_operation.failed",
            correlation_id="corr-op",
            instance_id="inst:1",
            op_id="qmb.analysis.project",
            logical_invocation_id="inv:1",
            graph_run_id="graph:1",
            level=logging.ERROR,
        )
        assert is_ok(ran)
        rows = _lines(stream)
        public = [row for row in rows if row["event"] == "public_operation.failed"]
        assert len(public) == 1
        payload = public[0]
        assert payload["level"] == "ERROR"
        assert payload["instance_id"] == "inst:1"
        assert payload["op_id"] == "qmb.analysis.project"
        assert payload["logical_invocation_id"] == "inv:1"
        assert payload["graph_run_id"] == "graph:1"
        assert payload["fp1_identity"] is False
        assert is_refusal(process.mint_fourth_observability_comp())
        assert is_refusal(process.mint_operator_log_sqlite_class())
        assert is_refusal(process.extend_qmn_failures_md())
        assert is_refusal(process.fingerprint_operator_log(payload))
        assert process.sqlite_connection_count() == 1
    finally:
        process.close()


def test_example_script() -> None:
    namespace = runpy.run_path(str(EXAMPLE), run_name="__main__")
    assert namespace["main"] is not None
