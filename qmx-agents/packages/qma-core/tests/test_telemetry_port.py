"""Story 47.4 — TelemetryExportPort definitions (FR-Q67; AD-23)."""

from __future__ import annotations

from qma.core.ports import (
    GAP_0089_TRIM_WINDOW,
    GAP_0090_CONTEXT_COMPACTION,
    HARNESS_AUTHOR,
    TELEMETRY_FORBIDDEN_LEDGER_KEYS,
    TELEMETRY_KINDS,
    TELEMETRY_RETENTION_EXEMPT_KINDS,
    TELEMETRY_RETENTION_KEYS,
    TelemetryExportPort,
    TelemetryRecord,
    parse_telemetry_record,
    refuse_agent_authored_telemetry,
    refuse_context_compaction,
    refuse_ledger_back_reference,
    refuse_trim_window_decision,
)
from qmf.core import is_ok, is_refusal


def test_harness_authored_record_and_trace_ref_direction() -> None:
    parsed = parse_telemetry_record(
        {
            "kind": "trace",
            "correlation_id": "corr-1",
            "occurred_at": 10,
            "recorded_at": 11,
            "payload": {"name": "route"},
        }
    )
    assert is_ok(parsed)
    record = parsed.value
    assert record.authored_by == HARNESS_AUTHOR
    assert record.trace_ref.startswith("trace:")
    assert "journal_seq" not in record.to_payload()
    assert record.retention_exempt is False


def test_agent_authored_and_ledger_back_refs_refused() -> None:
    agent = parse_telemetry_record(
        {
            "kind": "log",
            "correlation_id": "corr-2",
            "authored_by": "agent",
            "occurred_at": 1,
            "recorded_at": 1,
        }
    )
    assert is_refusal(agent)
    assert agent.context["field"] == "authored_by"

    back = parse_telemetry_record(
        {
            "kind": "metric",
            "correlation_id": "corr-3",
            "occurred_at": 1,
            "recorded_at": 1,
            "payload": {"ledger_ref": "task-ledger:1"},
        }
    )
    assert is_refusal(back)
    assert back.context["field"] == "ledger_ref"

    top = parse_telemetry_record(
        {
            "kind": "metric",
            "correlation_id": "corr-4",
            "occurred_at": 1,
            "recorded_at": 1,
            "task_ledger_ref": "task-ledger:1",
        }
    )
    assert is_refusal(top)

    journaled = parse_telemetry_record(
        {
            "kind": "log",
            "correlation_id": "corr-5",
            "occurred_at": 1,
            "recorded_at": 1,
            "journal_seq": 9,
        }
    )
    assert is_refusal(journaled)
    assert journaled.context["field"] == "journal_seq"


def test_retention_exempt_kinds_and_deferred_gaps() -> None:
    assert frozenset({"trajectory", "session_replay"}) == TELEMETRY_RETENTION_EXEMPT_KINDS
    assert "trace" in TELEMETRY_KINDS
    assert all(key.startswith("registry:telemetry.") for key in TELEMETRY_RETENTION_KEYS)
    assert "ledger_ref" in TELEMETRY_FORBIDDEN_LEDGER_KEYS

    traj = parse_telemetry_record(
        {
            "id": "traj-1",
            "kind": "trajectory",
            "correlation_id": "corr-t",
            "occurred_at": 1,
            "recorded_at": 2,
        }
    )
    assert is_ok(traj)
    assert traj.value.retention_exempt is True

    assert refuse_trim_window_decision().context["gap"] == GAP_0089_TRIM_WINDOW
    assert refuse_context_compaction().context["gap"] == GAP_0090_CONTEXT_COMPACTION
    assert refuse_agent_authored_telemetry().context["author"] == HARNESS_AUTHOR
    assert refuse_ledger_back_reference(key="ledger_ref").context["field"] == "ledger_ref"


def test_export_port_is_protocol_not_runtime_port() -> None:
    assert TelemetryExportPort.__name__ == "TelemetryExportPort"
    assert hasattr(TelemetryExportPort, "export")
    assert hasattr(TelemetryExportPort, "flush")


def test_record_constructor_rejects_agent_author() -> None:
    try:
        TelemetryRecord(
            kind="log",
            correlation_id="c",
            authored_by="agent",
            occurred_at=1,
            recorded_at=1,
        )
    except ValueError as exc:
        assert "harness" in str(exc)
    else:
        raise AssertionError("expected ValueError for agent authored_by")
