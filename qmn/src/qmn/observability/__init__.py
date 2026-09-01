"""Node observability surface (TN-15): structured logs, metrics, health.

Logs ≠ journals. Metrics are Prometheus-class exposition only (no library HTTP
server). Health states stay independent and never collapse to one colour.
Alerts and the liveness watcher sink land in later stories; this package codes
the export contracts.
"""

from __future__ import annotations

from typing import Final

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
    "COLLAPSES_TO_GLOBAL_COLOUR",
    "CONTENT_TYPE_LATEST",
    "FORBIDDEN_LOG_KEYS",
    "HEALTH_STATE_NAMES",
    "LATENCY_RUNGS",
    "LOGS_ARE_NOT_JOURNALS",
    "LOGS_SATISFY_CT13_EVIDENCE",
    "METRIC_FAMILY_GROUPS",
    "METRIC_PREFIX",
    "NODE_LOG_REQUIRED_FIELDS",
    "OBSERVABILITY_SURFACE",
    "SPAWNS_SERVER_THREAD",
    "HealthProvenance",
    "HealthStateName",
    "HealthStatus",
    "IndependentHealthReport",
    "IndependentHealthState",
    "JsonLineFormatter",
    "NodeLogContext",
    "NodeMetricsRegistry",
    "aggregate_health",
    "bind_log_context",
    "build_node_metrics",
    "configure_node_logging",
    "default_health_report",
    "emit_node_event",
    "family_group_names",
    "get_log_context",
    "health",
    "log_record_is_journal_evidence",
    "metric_names_for_group",
    "reset_log_context",
]

OBSERVABILITY_SURFACE: Final[str] = "qmn.observability"
