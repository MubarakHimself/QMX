"""L27 reference usage: qma-daemon stdlib JSON-lines operator logs (Story 61.1)."""

from __future__ import annotations

import json
import logging
import tempfile
from io import StringIO
from pathlib import Path

from qma.daemon.journal.stores import CLOSED_INDEPENDENT_STORES, CLOSED_STORE_NAMES
from qma.daemon.operator_log import (
    EPIC_60_TIP_SHA,
    FOURTH_OBSERVABILITY_COMP_MINTED,
    LOGS_ARE_NOT_EVIDENCE,
    LOGS_ARE_NOT_JOURNALS,
    LOGS_ENTER_FP1_IDENTITY,
    OPERATOR_LOG_INSPECT_SHA,
    OPERATOR_LOG_JOIN_FIELDS,
    OPERATOR_LOG_REQUIRED_FIELDS,
    OPERATOR_LOG_SQLITE_CLASS_MINTED,
    OPERATOR_LOGGER_EXISTED_AT_EPIC_60_TIP,
    OPERATOR_LOGGER_EXISTED_AT_INSPECT_SHA,
    OTEL_REMAINS_EXPORT_PORT_ONLY,
    TELEMETRY_STORE_REMAINS_TRACE_METRIC_PLANE,
    claim_operator_logger_at_inspect_sha,
    configure_daemon_logging,
    emit_operator_event,
    fingerprint_operator_log,
    refuse_fourth_observability_comp,
    refuse_operator_log_sqlite_class,
    refuse_qmn_failures_extension,
)
from qma.daemon.plugins import research_corpus_plugin_load_config
from qma.daemon.process import DaemonProcess
from qma.daemon.telemetry import TelemetryStore
from qmf.core import is_ok, is_refusal


def _lines(stream: StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


def main() -> None:
    assert OPERATOR_LOGGER_EXISTED_AT_INSPECT_SHA is False
    assert OPERATOR_LOGGER_EXISTED_AT_EPIC_60_TIP is False
    assert OPERATOR_LOG_INSPECT_SHA == "34c148b"
    assert EPIC_60_TIP_SHA == "7223e1a"
    assert LOGS_ARE_NOT_JOURNALS is True
    assert LOGS_ARE_NOT_EVIDENCE is True
    assert LOGS_ENTER_FP1_IDENTITY is False
    assert FOURTH_OBSERVABILITY_COMP_MINTED is False
    assert OPERATOR_LOG_SQLITE_CLASS_MINTED is False
    assert TELEMETRY_STORE_REMAINS_TRACE_METRIC_PLANE is True
    assert OTEL_REMAINS_EXPORT_PORT_ONLY is True
    assert "operator_logs" not in CLOSED_STORE_NAMES
    assert "operator_logs" not in CLOSED_INDEPENDENT_STORES

    claimed = claim_operator_logger_at_inspect_sha(True)
    assert is_refusal(claimed)
    assert claimed.context["existed_at_inspect_sha"] is False
    assert is_ok(claim_operator_logger_at_inspect_sha(False))
    assert is_refusal(refuse_fourth_observability_comp())
    assert is_refusal(refuse_operator_log_sqlite_class())
    assert is_refusal(refuse_qmn_failures_extension())
    assert is_refusal(fingerprint_operator_log({"event": "nope"}))

    stream = StringIO()
    logger = configure_daemon_logging(
        handler=logging.StreamHandler(stream),
        logger_name="qma.daemon.operator.example",
    )
    written = emit_operator_event(
        logger,
        logging.INFO,
        "public_operation.run",
        correlation_id="corr-ex",
        instance_id="inst:1",
        op_id="qmb.analysis.project",
        logical_invocation_id="inv:1",
        graph_run_id="graph:1",
    )
    assert is_ok(written)
    secret = emit_operator_event(
        logger,
        logging.INFO,
        "public_operation.run",
        correlation_id="corr-ex",
        **{"secret_value": "leak"},
    )
    assert is_refusal(secret)
    payload = _lines(stream)[0]
    for field in OPERATOR_LOG_REQUIRED_FIELDS:
        assert field in payload
    for field in OPERATOR_LOG_JOIN_FIELDS:
        assert field in payload
    assert payload["is_journal"] is False
    assert payload["fp1_identity"] is False

    store = TelemetryStore()
    assert store.announcement_exempt is True
    assert store.store_name == "telemetry_store"

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        seed = root / "seed-corpus"
        seed.mkdir()
        daemon_stream = StringIO()
        composed = DaemonProcess.compose(
            root,
            machine="example-host",
            boot_epoch_id="boot-example-61-1",
            bind_port=0,
            plugin_load_configs=research_corpus_plugin_load_config(seed),
            log_handler=logging.StreamHandler(daemon_stream),
        )
        assert is_ok(composed), composed
        process = composed.value
        try:
            snap = process.snapshot()
            assert snap["operator_json_lines"] is True
            assert snap["operator_logs_are_journal"] is False
            assert snap["fourth_observability_comp"] is False
            assert is_refusal(process.mint_fourth_observability_comp())
            assert is_refusal(process.mint_operator_log_sqlite_class())
            rows = _lines(daemon_stream)
            assert rows
            assert all(field in rows[0] for field in OPERATOR_LOG_REQUIRED_FIELDS)
        finally:
            process.close()


if __name__ == "__main__":
    main()
