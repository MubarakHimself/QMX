"""Node observability surface (TN-15): logs, metrics, health, alerts, liveness.

Logs ≠ journals. Metrics are Prometheus-class exposition only (no library HTTP
server). Health states stay independent and never collapse to one colour.
Alerts are a closed allow-list generated from FAILURES.md. The liveness
heartbeat is an outbound alive-ping holding zero authority (DEC-0261).
"""

from __future__ import annotations

from typing import Final

from qmn.observability.alerts import (
    NFR11_REQUIRED_FIELDS,
    PUSH_ALERT_CLASSES,
    QUIET_HOURS_EXIST,
    AlertAllowList,
    AlertPayload,
    AlertPublisher,
    FailureRegisterEntry,
    NotificationChannel,
    RecordingNotificationChannel,
    default_failures_path,
    generate_alert_allow_list,
    load_alert_allow_list,
    parse_failures_register,
    push_classes_for_tier,
)
from qmn.observability.health import (
    AUTHORITY_LIVE,
    AUTHORITY_REPLICATED,
    AUTHORITY_SOURCES,
    COLLAPSES_TO_GLOBAL_COLOUR,
    HEALTH_STATE_NAMES,
    HealthProvenance,
    HealthStateName,
    HealthStatus,
    IndependentHealthReport,
    IndependentHealthState,
    aggregate_health,
    default_health_report,
    health,
)
from qmn.observability.liveness import (
    CAN_CALL_DOOR,
    CAN_CLOSE_POSITIONS,
    CAN_STOP_ENTRIES,
    HOLDS_INBOUND_NODE_PATH,
    HOLDS_ZERO_AUTHORITY,
    UI_STREAMED_HEALTH_VIEW_IMPLEMENTED,
    LivenessHeartbeat,
    LivenessHttpSink,
    RecordingLivenessHttpSink,
    WatcherDouble,
)
from qmn.observability.logging import (
    FORBIDDEN_LOG_KEYS,
    LOGS_ARE_NOT_JOURNALS,
    LOGS_SATISFY_CT13_EVIDENCE,
    NODE_LOG_REQUIRED_FIELDS,
    JsonLineFormatter,
    NodeLogContext,
    bind_log_context,
    configure_node_logging,
    emit_node_event,
    get_log_context,
    log_record_is_journal_evidence,
    reset_log_context,
)
from qmn.observability.metrics import (
    CONTENT_TYPE_LATEST,
    LATENCY_RUNGS,
    METRIC_FAMILY_GROUPS,
    METRIC_PREFIX,
    SPAWNS_SERVER_THREAD,
    NodeMetricsRegistry,
    build_node_metrics,
    family_group_names,
    metric_names_for_group,
)

__all__ = [
    "AUTHORITY_LIVE",
    "AUTHORITY_REPLICATED",
    "AUTHORITY_SOURCES",
    "CAN_CALL_DOOR",
    "CAN_CLOSE_POSITIONS",
    "CAN_STOP_ENTRIES",
    "COLLAPSES_TO_GLOBAL_COLOUR",
    "CONTENT_TYPE_LATEST",
    "DAILY_LIVENESS_DIGEST_EXISTS",
    "FORBIDDEN_LOG_KEYS",
    "HEALTH_STATE_NAMES",
    "HOLDS_INBOUND_NODE_PATH",
    "HOLDS_ZERO_AUTHORITY",
    "LATENCY_RUNGS",
    "LOGS_ARE_NOT_JOURNALS",
    "LOGS_SATISFY_CT13_EVIDENCE",
    "METRIC_FAMILY_GROUPS",
    "METRIC_PREFIX",
    "NFR11_REQUIRED_FIELDS",
    "NODE_LOG_REQUIRED_FIELDS",
    "OBSERVABILITY_SURFACE",
    "PUSH_ALERT_CLASSES",
    "QUIET_HOURS_EXIST",
    "SPAWNS_SERVER_THREAD",
    "UI_STREAMED_HEALTH_VIEW_IMPLEMENTED",
    "AlertAllowList",
    "AlertPayload",
    "AlertPublisher",
    "FailureRegisterEntry",
    "HealthProvenance",
    "HealthStateName",
    "HealthStatus",
    "IndependentHealthReport",
    "IndependentHealthState",
    "JsonLineFormatter",
    "LivenessHeartbeat",
    "LivenessHttpSink",
    "NodeLogContext",
    "NodeMetricsRegistry",
    "NotificationChannel",
    "RecordingLivenessHttpSink",
    "RecordingNotificationChannel",
    "WatcherDouble",
    "aggregate_health",
    "bind_log_context",
    "build_node_metrics",
    "configure_node_logging",
    "default_failures_path",
    "default_health_report",
    "emit_node_event",
    "family_group_names",
    "generate_alert_allow_list",
    "get_log_context",
    "health",
    "load_alert_allow_list",
    "log_record_is_journal_evidence",
    "metric_names_for_group",
    "parse_failures_register",
    "push_classes_for_tier",
    "reset_log_context",
]

OBSERVABILITY_SURFACE: Final[str] = "qmn.observability"

# Rejected by DEC-0261 — daily liveness digest does not exist.
DAILY_LIVENESS_DIGEST_EXISTS: Final[bool] = False
