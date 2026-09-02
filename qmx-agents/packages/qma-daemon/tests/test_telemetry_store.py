"""Story 47.4 — telemetry store, OTel export port, bounded trim (FR-Q67)."""

from __future__ import annotations

import ast
import runpy
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from qma.core.ontology import ActorId, DeskSlug, Quant, RoleName
from qma.core.ports.telemetry import (
    GAP_0089_TRIM_WINDOW,
    GAP_0090_CONTEXT_COMPACTION,
    HARNESS_AUTHOR,
    TELEMETRY_RETENTION_KEYS,
)
from qma.daemon import RetentionJob, TelemetryStore
from qma.daemon.bus import DELIVERY_RETENTION_KEYS, MailboxStore
from qma.daemon.telemetry import (
    DAEMON_CORE_OTEL_IMPORT_FORBIDDEN,
    DAEMON_JOB_TRIM_STREAMS,
    OpenTelemetryExportAdapter,
    RecordingTelemetryExporter,
)
from qma.wire.outbox import OutboxBounds, RemoteOutbox
from qmf.core import Ok, is_ok, is_refusal

TELEMETRY_SRC = (
    Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon" / "telemetry"
)


def _actor(slug: str) -> ActorId:
    minted = ActorId.mint(DeskSlug.RESEARCH, slug)
    assert is_ok(minted)
    return minted.value


def _quant(slug: str) -> Quant:
    return Quant(
        actor_id=_actor(slug),
        desk=DeskSlug.RESEARCH,
        quant_slug=slug,
        role=RoleName.RESEARCHER,
        name=f"Quant {slug}",
    )


def test_harness_store_distinct_and_no_journal_seq() -> None:
    store = TelemetryStore()
    appended = store.append(
        {
            "kind": "routing_decision",
            "correlation_id": "corr-route",
            "wire_id": "wire-1",
            "payload": {"deployment": "opencodex-local"},
        }
    )
    assert is_ok(appended)
    record = appended.value
    assert record.authored_by == HARNESS_AUTHOR
    assert "journal_seq" not in record.to_payload()
    assert store.announcement_exempt is True
    distinct = store.assert_distinct_from_evidence_stores()
    distinct_from = cast("tuple[str, ...]", distinct["distinct_from"])
    assert "event_journal" in distinct_from
    assert "task_ledger" in distinct_from
    assert "artifact_store" in distinct_from
    assert "staging_store" in distinct_from

    agent = store.append(
        {
            "kind": "log",
            "correlation_id": "corr-agent",
            "authored_by": "agent",
        }
    )
    assert is_refusal(agent)

    back = store.append(
        {
            "kind": "metric",
            "correlation_id": "corr-back",
            "payload": {"ledger_ref": "task-ledger:x"},
        }
    )
    assert is_refusal(back)


def test_otel_export_port_without_sdk_import() -> None:
    assert DAEMON_CORE_OTEL_IMPORT_FORBIDDEN is True
    store = TelemetryStore()
    adapter = OpenTelemetryExportAdapter()
    store.bind_exporter(adapter)
    assert is_ok(
        store.append(
            {
                "id": "t-1",
                "kind": "trace",
                "correlation_id": "corr-otel",
                "occurred_at": 100,
                "recorded_at": 101,
            }
        )
    )
    exported = store.export_pending()
    assert is_ok(exported)
    assert exported.value == 1
    payload = adapter.exported_payloads[0]
    attributes = cast("Mapping[str, object]", payload["attributes"])
    assert attributes["qma.correlation_id"] == "corr-otel"
    assert str(payload["trace_id"]).startswith("trace:")
    assert adapter.sdk_imported is False

    # Daemon telemetry package must not import opentelemetry.
    for path in TELEMETRY_SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("opentelemetry"), path
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                assert not node.module.startswith("opentelemetry"), path


def test_outbox_drops_telemetry_before_evidence(tmp_path: Path) -> None:
    bounds = OutboxBounds.try_create(max_depth=2, max_spool_bytes=10_000)
    assert isinstance(bounds, Ok)
    outbox = RemoteOutbox(directory=tmp_path / "bounded", bounds=bounds.value)
    assert is_ok(
        outbox.enqueue(
            producer_id="worker-1",
            id="ev-1",
            kind="evidence",
            payload={"entry": "ledger"},
        )
    )
    assert is_ok(
        outbox.enqueue(
            producer_id="worker-1",
            id="tel-1",
            kind="telemetry",
            payload={"kind": "metric"},
        )
    )
    tel = outbox.enqueue(
        producer_id="worker-1",
        id="tel-2",
        kind="telemetry",
        payload={"kind": "metric"},
    )
    assert is_refusal(tel)
    assert tel.context["field"] == "telemetry_discarded"
    blocked = outbox.enqueue(
        producer_id="worker-1",
        id="ev-2",
        kind="evidence",
        payload={"entry": "more"},
    )
    assert is_refusal(blocked)
    assert blocked.context["field"] == "dispatch_blocked"
    discarded = outbox.prefer_discard_telemetry()
    assert len(discarded) == 1
    assert discarded[0].kind == "telemetry"
    assert all(entry.kind == "evidence" for entry in outbox.pending())


def test_trim_telemetry_and_mailbox_only(tmp_path: Path) -> None:
    store = TelemetryStore()
    assert is_ok(
        store.append(
            {
                "id": "m-1",
                "kind": "metric",
                "correlation_id": "corr-trim",
                "occurred_at": 1,
                "recorded_at": 1,
            }
        )
    )
    assert is_ok(
        store.append(
            {
                "id": "traj-1",
                "kind": "trajectory",
                "correlation_id": "corr-trim",
                "occurred_at": 2,
                "recorded_at": 2,
            }
        )
    )
    assert is_ok(
        store.append(
            {
                "id": "replay-1",
                "kind": "session_replay",
                "correlation_id": "corr-trim",
                "occurred_at": 3,
                "recorded_at": 3,
            }
        )
    )

    mailbox = MailboxStore()
    sender = _quant("alpha")
    recipient = _quant("beta")
    assert is_ok(mailbox.open_for_quant(sender))
    assert is_ok(mailbox.open_for_quant(recipient))
    assert is_ok(
        mailbox.send(
            {
                "msg_id": "msg-keep",
                "from": sender.actor_id.value,
                "to": recipient.actor_id.value,
                "kind": "notify",
                "correlation_id": "corr-mail",
                "body": "hi",
                "priority": 0,
            }
        )
    )
    assert is_ok(mailbox.deliver("msg-keep"))
    assert is_ok(mailbox.ack(recipient, "msg-keep"))
    assert is_ok(
        mailbox.send(
            {
                "msg_id": "msg-ask",
                "from": sender.actor_id.value,
                "to": recipient.actor_id.value,
                "kind": "approval_request",
                "correlation_id": "corr-ask",
                "body": "approve?",
                "priority": 1,
            }
        )
    )
    assert is_ok(mailbox.deliver("msg-ask"))
    assert is_ok(mailbox.ack(recipient, "msg-ask"))

    job = RetentionJob(telemetry=store, mailbox=mailbox)
    report = job.run(correlation_id="corr-job", reason="bounded_retention")
    assert is_ok(report)
    body = report.value.to_payload()
    assert body["gap_0089"] == "deferred"
    assert body["gap_0090"] == "deferred"
    assert body["context_compaction"] is False
    assert report.value.telemetry is not None
    assert report.value.telemetry["trimmed_count"] == 1
    assert report.value.telemetry["retained_exempt_count"] == 2
    assert report.value.telemetry["window"] == "registry:telemetry.retention_window"
    assert report.value.telemetry["reason"] == "bounded_retention"
    assert report.value.telemetry["correlation_id"] == "corr-job"
    assert report.value.telemetry["retention"] == list(TELEMETRY_RETENTION_KEYS)
    assert report.value.mailbox_delivery is not None
    assert report.value.mailbox_delivery["correlation_id"] == "corr-job"
    assert report.value.mailbox_delivery["reason"] == "bounded_retention"
    assert report.value.mailbox_delivery["retention"] == list(DELIVERY_RETENTION_KEYS)
    assert mailbox.record_for("msg-keep") is None
    assert mailbox.record_for("msg-ask") is not None  # unanswered approval retained
    assert store.event_count() == 2
    assert {row.kind for row in store.records()} == {"trajectory", "session_replay"}

    foreign = job.run(correlation_id="corr-bad", streams=frozenset({"journal"}))
    assert is_refusal(foreign)
    assert foreign.context["stream"] == "journal"

    window = store.decide_trim_window()
    assert is_refusal(window)
    assert window.context["gap"] == GAP_0089_TRIM_WINDOW
    compact = store.compact_context()
    assert is_refusal(compact)
    assert compact.context["gap"] == GAP_0090_CONTEXT_COMPACTION
    assert frozenset({"mailbox.delivery", "telemetry"}) == DAEMON_JOB_TRIM_STREAMS

    cites = job.cite_retention_keys()
    assert cites["gap_0089"] == GAP_0089_TRIM_WINDOW
    assert cites["gap_0090"] == GAP_0090_CONTEXT_COMPACTION


def test_trim_outside_window_requires_operator() -> None:
    store = TelemetryStore()
    assert is_ok(
        store.append(
            {
                "kind": "log",
                "correlation_id": "c",
                "occurred_at": 1,
                "recorded_at": 1,
            }
        )
    )
    refused = store.trim(
        correlation_id="corr-out",
        inside_retention_window=False,
        operator_principal=False,
    )
    assert is_refusal(refused)
    allowed = store.trim(
        correlation_id="corr-op",
        inside_retention_window=False,
        operator_principal=True,
    )
    assert is_ok(allowed)


def test_recording_exporter_and_usage_example() -> None:
    store = TelemetryStore()
    sink = RecordingTelemetryExporter()
    store.bind_exporter(sink)
    assert is_ok(
        store.append(
            {
                "kind": "usage",
                "correlation_id": "corr-use",
                "occurred_at": 1,
                "recorded_at": 1,
                "payload": {"tokens": 12},
            }
        )
    )
    assert is_ok(store.export_pending())
    assert len(sink.exported) == 1
    assert is_ok(sink.flush())
    assert sink.flush_count == 1

    path = Path(__file__).resolve().parents[1] / "examples" / "telemetry_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()
