"""Canonical CT-32 result artifact, metrics, and chart-series home (B-10).

Every run emits one canonical machine-readable result artifact, and that
artifact IS a CT-32 performance-result. Package SemVer is display-only
provenance on the occurrence record, never identity (DEC-0163, DEC-0167).
Chart series and HTML are Epic 19 and are excluded from ``fp1``.
"""

from __future__ import annotations

from qmf.risk.performance import PerformanceResult

from qmb.results.ct32 import (
    ACCOUNT_ROLE_KEY,
    CALENDAR_KEY,
    CHART_SERIES_IN_IDENTITY,
    CONCURRENCY_IS_SCHEDULING_ONLY,
    HTML_PAYLOAD,
    MEASURE_CONTRACT_FORMAT_VERSION,
    MEASURE_IDENTITIES,
    QMB_REPLAY_CALENDAR_RULE_SET,
    QMB_REPLAY_CALENDAR_RULE_SET_VERSION,
    QMB_REPLAY_CALENDAR_TZDATA,
    RESULT_CONTRACT,
    mint_run_performance_result,
    require_reproduced_fingerprint,
    result_identity,
)

__all__ = [
    "ACCOUNT_ROLE_KEY",
    "CALENDAR_KEY",
    "CHART_SERIES_IN_IDENTITY",
    "CONCURRENCY_IS_SCHEDULING_ONLY",
    "HTML_PAYLOAD",
    "MEASURE_CONTRACT_FORMAT_VERSION",
    "MEASURE_IDENTITIES",
    "QMB_REPLAY_CALENDAR_RULE_SET",
    "QMB_REPLAY_CALENDAR_RULE_SET_VERSION",
    "QMB_REPLAY_CALENDAR_TZDATA",
    "RESULT_CONTRACT",
    "PerformanceResult",
    "mint_run_performance_result",
    "require_reproduced_fingerprint",
    "result_identity",
]
