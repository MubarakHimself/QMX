"""Traces, metrics, trajectories, OTel export port (AD-23; FR-Q67).

Harness-authored telemetry store, swappable OpenTelemetry export adapters that
never import the OTel SDK into the daemon core, and the daemon-job retention
path that trims only the telemetry store and mailbox delivery projection.
"""

from __future__ import annotations

from qma.daemon.telemetry.export import (
    DAEMON_CORE_OTEL_IMPORT_FORBIDDEN,
    NullTelemetryExporter,
    OpenTelemetryExportAdapter,
    RecordingTelemetryExporter,
    otel_shaped_payload,
)
from qma.daemon.telemetry.retention import RetentionJob, RetentionJobReport
from qma.daemon.telemetry.store import (
    DAEMON_JOB_TRIM_STREAMS,
    GAP_0089_TRIM_WINDOW,
    GAP_0090_CONTEXT_COMPACTION,
    TELEMETRY_RETENTION_KEYS,
    TELEMETRY_STORE_NAME,
    TelemetryStore,
    TrimReceipt,
)

__all__ = [
    "DAEMON_CORE_OTEL_IMPORT_FORBIDDEN",
    "DAEMON_JOB_TRIM_STREAMS",
    "GAP_0089_TRIM_WINDOW",
    "GAP_0090_CONTEXT_COMPACTION",
    "TELEMETRY_RETENTION_KEYS",
    "TELEMETRY_STORE_NAME",
    "NullTelemetryExporter",
    "OpenTelemetryExportAdapter",
    "RecordingTelemetryExporter",
    "RetentionJob",
    "RetentionJobReport",
    "TelemetryStore",
    "TrimReceipt",
    "otel_shaped_payload",
]
