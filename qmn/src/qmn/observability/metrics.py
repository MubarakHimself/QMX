"""Prometheus-class ``qmn_`` metric families — exposition only (TN-15 / DEC-0200).

``prometheus_client`` is the registry and text exposition format. The node's
evidence door serves ``/metrics``; this module never starts a library HTTP
server thread. Labels carry opaque ids only — never secrets or raw accounts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

__all__ = [
    "CONTENT_TYPE_LATEST",
    "LATENCY_RUNGS",
    "METRIC_FAMILY_GROUPS",
    "METRIC_PREFIX",
    "SPAWNS_SERVER_THREAD",
    "NodeMetricsRegistry",
    "build_node_metrics",
    "family_group_names",
    "metric_names_for_group",
]

METRIC_PREFIX: Final[str] = "qmn_"
SPAWNS_SERVER_THREAD: Final[bool] = False

# Story 25.10 / AR-81 — twelve named family groups (nine spine + three
# implementation-gate). Names are minted here; rename only with registry notes.
METRIC_FAMILY_GROUPS: Final[tuple[str, ...]] = (
    "clock",
    "session",
    "command_stream",
    "reconciliation",
    "protection",
    "latency",
    "data",
    "backup",
    "seat",
    "evidence_channel",
    "process",
    "liveness_heartbeat",
)

LATENCY_RUNGS: Final[tuple[str, ...]] = (
    "tick_received",
    "evidence_write",
    "indicator_update",
    "decision",
    "risk_evaluation",
    "order_submitted",
)

_FAMILY_METRIC_NAMES: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "clock": (
            "qmn_clock_chrony_offset_seconds",
            "qmn_clock_chrony_stratum",
            "qmn_clock_sync_age_seconds",
            "qmn_clock_step_total",
            "qmn_clock_venue_skew_seconds",
            "qmn_clock_band",
        ),
        "session": (
            "qmn_session_connection_state",
            "qmn_session_heartbeat_age_seconds",
            "qmn_session_pacer_occupancy",
            "qmn_session_reconnects_total",
        ),
        "command_stream": (
            "qmn_command_unknown_outstanding",
            "qmn_command_unknown_age_seconds",
            "qmn_command_sequence_gaps_total",
            "qmn_command_outcomes_total",
        ),
        "reconciliation": (
            "qmn_reconcile_verdict",
            "qmn_reconcile_quantity_residual",
            "qmn_reconcile_cash_residual",
            "qmn_reconcile_age_seconds",
        ),
        "protection": (
            "qmn_protection_ksa_level",
            "qmn_protection_standing_intent_count",
            "qmn_protection_standing_intent_age_seconds",
            "qmn_protection_book_mode",
            "qmn_protection_binding_state",
            "qmn_protection_seat_state",
            "qmn_protection_bench_count",
        ),
        "latency": (
            "qmn_latency_rung_seconds",
            "qmn_latency_slice_seconds",
        ),
        "data": (
            "qmn_data_feed_staleness_seconds",
            "qmn_data_sqs_marker",
            "qmn_data_news_calendar_age_seconds",
            "qmn_data_news_staleness_margin_seconds",
            "qmn_data_accumulator_depth",
            "qmn_data_journal_write_latency_seconds",
            "qmn_data_disk_headroom_bytes",
        ),
        "backup": (
            "qmn_backup_age_seconds",
            "qmn_backup_last_drill_outcome",
            "qmn_backup_measured_rto_seconds",
        ),
        "seat": ("qmn_seat_callback_seconds",),
        "evidence_channel": ("qmn_evidence_channel_budget_occupancy",),
        "process": (
            "qmn_process_rss_bytes",
            "qmn_process_loop_lag_seconds",
            "qmn_process_slice_latency_seconds",
        ),
        "liveness_heartbeat": ("qmn_liveness_heartbeat_emissions_total",),
    }
)

_FORBIDDEN_LABEL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "secret",
        "secret_value",
        "password",
        "token",
        "credential",
        "account_number",
        "raw_account",
        "api_key",
    }
)


def family_group_names() -> tuple[str, ...]:
    return METRIC_FAMILY_GROUPS


def metric_names_for_group(group: str) -> tuple[str, ...]:
    return _FAMILY_METRIC_NAMES.get(group, ())


def _reject_secret_labels(labels: Mapping[str, str]) -> None:
    for key in labels:
        lowered = key.lower()
        if lowered in _FORBIDDEN_LABEL_KEYS or "account_number" in lowered:
            msg = f"metric labels forbid secret/raw-account key {key!r}"
            raise ValueError(msg)


@dataclass
class NodeMetricsRegistry:
    """Isolated ``CollectorRegistry`` holding every ``qmn_`` family.

    Never calls ``start_http_server`` / ``start_wsgi_server``. Exposition is a
    pure string for the evidence door to serve.
    """

    registry: CollectorRegistry = field(default_factory=CollectorRegistry)
    _gauges: dict[str, Gauge] = field(default_factory=dict[str, Gauge], repr=False)
    _counters: dict[str, Counter] = field(default_factory=dict[str, Counter], repr=False)
    _histograms: dict[str, Histogram] = field(default_factory=dict[str, Histogram], repr=False)

    def __post_init__(self) -> None:
        self._register_families()

    @property
    def spawns_server_thread(self) -> bool:
        return SPAWNS_SERVER_THREAD

    def family_groups(self) -> tuple[str, ...]:
        return METRIC_FAMILY_GROUPS

    def registered_metric_names(self) -> frozenset[str]:
        names: set[str] = set()
        for group_names in _FAMILY_METRIC_NAMES.values():
            names.update(group_names)
        return frozenset(names)

    def exposition(self) -> bytes:
        """Prometheus text exposition (no server thread)."""
        return generate_latest(self.registry)

    def exposition_text(self) -> str:
        return self.exposition().decode("utf-8")

    def content_type(self) -> str:
        return CONTENT_TYPE_LATEST

    def set_gauge(
        self,
        name: str,
        value: float,
        *,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        gauge = self._gauges[name]
        if labels:
            _reject_secret_labels(labels)
            gauge.labels(**dict(labels)).set(value)
        else:
            gauge.set(value)

    def inc_counter(
        self,
        name: str,
        *,
        amount: float = 1.0,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        counter = self._counters[name]
        if labels:
            _reject_secret_labels(labels)
            counter.labels(**dict(labels)).inc(amount)
        else:
            counter.inc(amount)

    def observe_histogram(
        self,
        name: str,
        value: float,
        *,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        hist = self._histograms[name]
        if labels:
            _reject_secret_labels(labels)
            hist.labels(**dict(labels)).observe(value)
        else:
            hist.observe(value)

    def as_evidence_payload(self) -> Mapping[str, object]:
        """Door-facing payload: scrape text plus family census."""
        return MappingProxyType(
            {
                "exposition": self.exposition_text(),
                "content_type": self.content_type(),
                "metric_prefix": METRIC_PREFIX,
                "family_groups": list(METRIC_FAMILY_GROUPS),
                "metric_names": sorted(self.registered_metric_names()),
                "spawns_server_thread": False,
                "labels_bounded_non_secret": True,
            }
        )

    def _gauge(self, name: str, documentation: str, labelnames: Sequence[str] = ()) -> Gauge:
        metric = Gauge(name, documentation, labelnames=labelnames, registry=self.registry)
        self._gauges[name] = metric
        return metric

    def _counter(self, name: str, documentation: str, labelnames: Sequence[str] = ()) -> Counter:
        metric = Counter(name, documentation, labelnames=labelnames, registry=self.registry)
        self._counters[name] = metric
        return metric

    def _histogram(
        self, name: str, documentation: str, labelnames: Sequence[str] = ()
    ) -> Histogram:
        metric = Histogram(name, documentation, labelnames=labelnames, registry=self.registry)
        self._histograms[name] = metric
        return metric

    def _register_families(self) -> None:
        # clock
        self._gauge("qmn_clock_chrony_offset_seconds", "Chrony offset versus truth source")
        self._gauge("qmn_clock_chrony_stratum", "Chrony stratum")
        self._gauge("qmn_clock_sync_age_seconds", "Age of last successful chrony sync")
        self._counter("qmn_clock_step_total", "Clock step events observed")
        self._gauge(
            "qmn_clock_venue_skew_seconds",
            "Node-versus-broker skew (opaque venue id)",
            ("venue_id",),
        )
        self._gauge(
            "qmn_clock_band",
            "Clock band indicator (1 for active band)",
            ("band",),
        )
        # session
        self._gauge(
            "qmn_session_connection_state",
            "Connection state (1=up) per opaque connection",
            ("connection_id",),
        )
        self._gauge(
            "qmn_session_heartbeat_age_seconds",
            "Heartbeat age per opaque connection",
            ("connection_id",),
        )
        self._gauge(
            "qmn_session_pacer_occupancy",
            "Command pacer occupancy per opaque connection",
            ("connection_id",),
        )
        self._counter(
            "qmn_session_reconnects_total",
            "Reconnect count per opaque connection",
            ("connection_id",),
        )
        # command streams
        self._gauge(
            "qmn_command_unknown_outstanding",
            "Outstanding UNKNOWN count per opaque stream",
            ("stream_id",),
        )
        self._gauge(
            "qmn_command_unknown_age_seconds",
            "Age of oldest outstanding UNKNOWN per opaque stream",
            ("stream_id",),
        )
        self._counter(
            "qmn_command_sequence_gaps_total",
            "Sequence gaps per opaque stream",
            ("stream_id",),
        )
        self._counter(
            "qmn_command_outcomes_total",
            "Command outcomes per opaque stream",
            ("stream_id", "outcome"),
        )
        # reconciliation
        self._gauge(
            "qmn_reconcile_verdict",
            "Last reconciliation verdict indicator (1=active)",
            ("stream_id", "verdict"),
        )
        self._gauge(
            "qmn_reconcile_quantity_residual",
            "Quantity residual (separate from cash)",
            ("stream_id",),
        )
        self._gauge(
            "qmn_reconcile_cash_residual",
            "Cash residual (separate from quantity)",
            ("stream_id",),
        )
        self._gauge(
            "qmn_reconcile_age_seconds",
            "Age of last reconciliation verdict",
            ("stream_id",),
        )
        # protection
        self._gauge(
            "qmn_protection_ksa_level",
            "KSA level per enforcement scope",
            ("scope",),
        )
        self._gauge("qmn_protection_standing_intent_count", "Standing protection intent count")
        self._gauge(
            "qmn_protection_standing_intent_age_seconds",
            "Age of oldest standing protection intent",
        )
        self._gauge(
            "qmn_protection_book_mode",
            "Book mode indicator (1=active)",
            ("book_id", "mode"),
        )
        self._gauge(
            "qmn_protection_binding_state",
            "Binding state indicator (1=active)",
            ("binding_id", "state"),
        )
        self._gauge(
            "qmn_protection_seat_state",
            "Seat state indicator (1=active)",
            ("seat_id", "state"),
        )
        self._gauge(
            "qmn_protection_bench_count",
            "Bench qualifying-loss count",
            ("binding_id",),
        )
        # latency (six AD-13 rungs + slice; no budgets until baselines)
        self._histogram(
            "qmn_latency_rung_seconds",
            "Monotonic latency rung histogram",
            ("rung",),
        )
        self._histogram("qmn_latency_slice_seconds", "Slice latency histogram")
        # data
        self._gauge("qmn_data_feed_staleness_seconds", "Canonical feed staleness")
        self._gauge("qmn_data_sqs_marker", "SQS marker value")
        self._gauge("qmn_data_news_calendar_age_seconds", "News calendar age")
        self._gauge(
            "qmn_data_news_staleness_margin_seconds",
            "News calendar staleness margin",
        )
        self._gauge("qmn_data_accumulator_depth", "Push-to-pull accumulator depth")
        self._histogram(
            "qmn_data_journal_write_latency_seconds",
            "Journal write latency",
        )
        self._gauge("qmn_data_disk_headroom_bytes", "Disk headroom remaining")
        # backup
        self._gauge("qmn_backup_age_seconds", "Age of last successful backup")
        self._gauge(
            "qmn_backup_last_drill_outcome",
            "Last restore-drill outcome indicator (1=active)",
            ("outcome",),
        )
        self._gauge("qmn_backup_measured_rto_seconds", "Measured restore RTO")
        # seat (implementation-gate family)
        self._histogram(
            "qmn_seat_callback_seconds",
            "Per-seat callback time",
            ("seat_id",),
        )
        # evidence channel (implementation-gate family)
        self._gauge(
            "qmn_evidence_channel_budget_occupancy",
            "Evidence-channel budget occupancy (0..1)",
        )
        # process
        self._gauge("qmn_process_rss_bytes", "Process resident set size")
        self._gauge("qmn_process_loop_lag_seconds", "Event-loop lag")
        self._gauge("qmn_process_slice_latency_seconds", "Last slice latency")
        # liveness heartbeat (implementation-gate family; emission only)
        self._counter(
            "qmn_liveness_heartbeat_emissions_total",
            "Outbound liveness heartbeat alive-ping emissions",
        )


def build_node_metrics() -> NodeMetricsRegistry:
    """Construct a fresh isolated registry with every ``qmn_`` family registered."""
    return NodeMetricsRegistry()
