"""Story 25.10 — structured logs, qmn_ metrics, independent health (TN-15)."""

from __future__ import annotations

import ast
import json
import logging
from collections.abc import Mapping
from io import StringIO
from pathlib import Path
from typing import TypeVar, cast

from qmf.core.refusal import Result, is_ok
from qmn.doors import api
from qmn.doors.http.evidence import handle_evidence_request, render_evidence_http
from qmn.doors.library import DoorRuntime
from qmn.observability import (
    COLLAPSES_TO_GLOBAL_COLOUR,
    FORBIDDEN_LOG_KEYS,
    HEALTH_STATE_NAMES,
    LATENCY_RUNGS,
    LOGS_ARE_NOT_JOURNALS,
    LOGS_SATISFY_CT13_EVIDENCE,
    METRIC_FAMILY_GROUPS,
    METRIC_PREFIX,
    NODE_LOG_REQUIRED_FIELDS,
    OBSERVABILITY_SURFACE,
    SPAWNS_SERVER_THREAD,
    IndependentHealthReport,
    JsonLineFormatter,
    NodeLogContext,
    NodeMetricsRegistry,
    aggregate_health,
    bind_log_context,
    build_node_metrics,
    configure_node_logging,
    default_health_report,
    emit_node_event,
    family_group_names,
    health,
    log_record_is_journal_evidence,
    metric_names_for_group,
    reset_log_context,
)

T = TypeVar("T")

_OBS_SRC = Path(__file__).resolve().parents[1] / "src" / "qmn" / "observability"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _runtime(**kwargs: object) -> DoorRuntime:
    base: dict[str, object] = {
        "boot_epoch": "boot-1",
        "composition_fp": "fp1:composition",
        "knowledge_time_ns": 1_000,
        "watermark_ns": 900,
        "source_time_ns": 950,
        "receive_time_ns": 980,
        "evidence_channel_budget": 100,
    }
    base.update(kwargs)
    return DoorRuntime(**base)  # type: ignore[arg-type]


# --- surface / contracts -------------------------------------------------


def test_observability_surface_and_invariants() -> None:
    assert OBSERVABILITY_SURFACE == "qmn.observability"
    assert LOGS_ARE_NOT_JOURNALS is True
    assert LOGS_SATISFY_CT13_EVIDENCE is False
    assert log_record_is_journal_evidence() is False
    assert SPAWNS_SERVER_THREAD is False
    assert COLLAPSES_TO_GLOBAL_COLOUR is False
    assert METRIC_PREFIX == "qmn_"
    assert family_group_names() == METRIC_FAMILY_GROUPS
    assert len(METRIC_FAMILY_GROUPS) == 12
    assert set(HEALTH_STATE_NAMES) == {
        "safety",
        "execution_readiness",
        "connection",
        "reconciliation",
        "data_freshness",
        "lifecycle",
        "sync",
    }
    assert LATENCY_RUNGS == (
        "tick_received",
        "evidence_write",
        "indicator_update",
        "decision",
        "risk_evaluation",
        "order_submitted",
    )


def test_observability_never_starts_prometheus_http_server() -> None:
    banned = ("start_http_server", "start_wsgi_server", "make_wsgi_app")
    violations: list[str] = []
    for path in sorted(_OBS_SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "prometheus_client":
                for alias in node.names:
                    if alias.name in banned:
                        violations.append(f"{path.name}: imports {alias.name}")
            if isinstance(node, ast.Call):
                func = node.func
                name = ""
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                if name in banned:
                    violations.append(f"{path.name}: calls {name}")
    assert violations == [], violations


# --- structured logs -----------------------------------------------------


def test_json_line_formatter_emits_required_fields_one_object_per_line() -> None:
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLineFormatter())
    logger = logging.getLogger("qmn.test.logs")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    token = bind_log_context(
        NodeLogContext(
            boot_epoch="boot-9",
            composition_fp="fp1:comp",
            world="live",
            correlation_id="corr-1",
            stream="venue:opaque-a",
            account_opaque_id="acct-opaque-1",
            seat_id="seat-1",
            binding_id="bind-1",
        )
    )
    try:
        emit_node_event(
            logger,
            logging.WARNING,
            "typed_refusal",
            correlation_id="corr-1",
            failure_id="clock.band.warn",
            category="policy rejection",
            retryability="no",
            after_condition="clock band returns to ok",
        )
    finally:
        reset_log_context(token)

    lines = [line for line in stream.getvalue().splitlines() if line.strip()]
    assert len(lines) == 1
    payload = json.loads(lines[0])
    for field in NODE_LOG_REQUIRED_FIELDS:
        assert field in payload, field
    assert payload["ts"].endswith("Z")
    assert "T" in payload["ts"]
    assert payload["level"] == "WARNING"
    assert payload["logger"] == "qmn.test.logs"
    assert payload["event"] == "typed_refusal"
    assert payload["boot_epoch"] == "boot-9"
    assert payload["composition_fp"] == "fp1:comp"
    assert payload["world"] == "live"
    assert payload["stream"] == "venue:opaque-a"
    assert payload["account_opaque_id"] == "acct-opaque-1"
    assert payload["seat_id"] == "seat-1"
    assert payload["binding_id"] == "bind-1"
    assert payload["correlation_id"] == "corr-1"
    assert payload["failure_id"] == "clock.band.warn"
    assert payload["category"] == "policy rejection"
    assert payload["retryability"] == "no"
    assert payload["after_condition"] == "clock band returns to ok"
    assert payload["ct13_evidence"] is False
    assert payload["is_journal"] is False


def test_logs_forbid_secrets_and_never_are_ct13() -> None:
    assert "secret_value" in FORBIDDEN_LOG_KEYS
    assert "account_number" in FORBIDDEN_LOG_KEYS
    logger = configure_node_logging(handler=logging.NullHandler(), logger_name="qmn.test.scrub")
    try:
        emit_node_event(logger, logging.INFO, "ok", secret_value="leak")
        raise AssertionError("expected ValueError for secret_value")
    except ValueError as exc:
        assert "secret_value" in str(exc)


# --- metrics -------------------------------------------------------------


def test_registered_qmn_families_cover_all_groups_without_server_thread() -> None:
    registry = build_node_metrics()
    assert isinstance(registry, NodeMetricsRegistry)
    assert registry.spawns_server_thread is False
    assert SPAWNS_SERVER_THREAD is False
    names = registry.registered_metric_names()
    for group in METRIC_FAMILY_GROUPS:
        group_names = metric_names_for_group(group)
        assert group_names, group
        assert all(name.startswith("qmn_") for name in group_names)
        assert set(group_names).issubset(names), group

    registry.set_gauge("qmn_clock_chrony_offset_seconds", 0.001)
    registry.set_gauge("qmn_clock_band", 1.0, labels={"band": "ok"})
    registry.set_gauge("qmn_clock_venue_skew_seconds", 0.002, labels={"venue_id": "opaque-v"})
    registry.inc_counter("qmn_clock_step_total")
    registry.set_gauge("qmn_session_connection_state", 1.0, labels={"connection_id": "opaque-c"})
    registry.set_gauge("qmn_command_unknown_outstanding", 0.0, labels={"stream_id": "opaque-s"})
    registry.inc_counter(
        "qmn_command_outcomes_total",
        labels={"stream_id": "opaque-s", "outcome": "accepted-by-venue"},
    )
    registry.set_gauge(
        "qmn_reconcile_verdict",
        1.0,
        labels={"stream_id": "opaque-s", "verdict": "reconciled"},
    )
    registry.set_gauge("qmn_protection_ksa_level", 2.0, labels={"scope": "book:opaque-b"})
    for rung in LATENCY_RUNGS:
        registry.observe_histogram("qmn_latency_rung_seconds", 0.01, labels={"rung": rung})
    registry.set_gauge("qmn_data_feed_staleness_seconds", 1.5)
    registry.set_gauge("qmn_backup_age_seconds", 3600.0)
    registry.observe_histogram("qmn_seat_callback_seconds", 0.02, labels={"seat_id": "seat-1"})
    registry.set_gauge("qmn_evidence_channel_budget_occupancy", 0.1)
    registry.set_gauge("qmn_process_rss_bytes", 100_000_000.0)
    registry.inc_counter("qmn_liveness_heartbeat_emissions_total")

    text = registry.exposition_text()
    for group in METRIC_FAMILY_GROUPS:
        for name in metric_names_for_group(group):
            assert name in text, name
    assert "account_number" not in text
    assert 'secret="' not in text
    assert "raw_account" not in text


def test_metric_labels_reject_secrets() -> None:
    registry = build_node_metrics()
    try:
        registry.set_gauge(
            "qmn_session_connection_state",
            1.0,
            labels={"account_number": "12345"},
        )
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "account_number" in str(exc)


def test_metrics_door_serves_prometheus_exposition_on_evidence_listener() -> None:
    runtime = _runtime(metrics_registry=build_node_metrics())
    payload = _ok(handle_evidence_request(runtime, method="GET", path="/metrics"))
    assert payload["capability"] == "read_metrics"
    assert payload["spawns_server_thread"] is False
    assert payload["labels_bounded_non_secret"] is True
    assert set(cast("list[str]", payload["family_groups"])) == set(METRIC_FAMILY_GROUPS)
    exposition = cast("str", payload["exposition"])
    assert "qmn_clock_chrony_offset_seconds" in exposition
    assert "qmn_liveness_heartbeat_emissions_total" in exposition
    assert "qmn_seat_callback_seconds" in exposition
    assert "qmn_evidence_channel_budget_occupancy" in exposition

    rendered = render_evidence_http(
        api.read_metrics(_runtime(metrics_registry=build_node_metrics()))
    )
    assert rendered["scrape_format"] == "prometheus"
    assert rendered["http_body"] == rendered["exposition"]
    assert "text/plain" in str(rendered["http_content_type"])
    assert rendered["acts"] is False
    assert rendered["publishes"] is True


# --- independent health --------------------------------------------------


def test_health_states_are_independent_provenance_stamped_not_one_colour() -> None:
    report = default_health_report(
        authority_source="live-authoritative",
        source_time_ns=10,
        receive_time_ns=20,
        watermark_ns=5,
        lifecycle="running",
    )
    assert report.collapsed_global_colour is False
    assert report.health() is report
    mapping = report.as_mapping()
    assert mapping["collapsed_global_colour"] is False
    states = cast("Mapping[str, Mapping[str, object]]", mapping["states"])
    for name in HEALTH_STATE_NAMES:
        assert name in states
        assert states[name]["authority_source"] == "live-authoritative"
        assert states[name]["source_time_ns"] == 10
        assert states[name]["receive_time_ns"] == 20
        assert states[name]["watermark_ns"] == 5

    # Independent: one failed state does not rewrite the others.
    mixed = aggregate_health(
        authority_source="live-authoritative",
        source_time_ns=1,
        receive_time_ns=2,
        watermark_ns=0,
        component_states={
            "safety": "ok",
            "connection": "failed",
            "lifecycle": "stand-down",
        },
        requested_protection={"level": 2},
        enforced_protection={"level": 1},
    )
    mixed_states = cast("Mapping[str, Mapping[str, object]]", mixed.as_mapping()["states"])
    assert mixed_states["safety"]["state"] == "ok"
    assert mixed_states["connection"]["state"] == "failed"
    assert mixed_states["lifecycle"]["state"] == "stand-down"
    assert mixed.as_mapping()["requested_protection"] != mixed.as_mapping()["enforced_protection"]
    assert mixed.collapsed_global_colour is False

    via_module = health(mixed)
    assert via_module is mixed


def test_health_door_never_collapses_to_global_colour() -> None:
    runtime = _runtime(
        health_states={
            "safety": "ok",
            "execution_readiness": "degraded",
            "connection": "ok",
            "reconciliation": "ok",
            "data_freshness": "degraded",
            "lifecycle": "running",
            "sync": "ok",
        },
        requested_protection={"ksa": "elevated"},
        enforced_protection={"ksa": "normal"},
    )
    payload = _ok(api.read_health(runtime))
    assert payload["collapsed_global_colour"] is False
    states = cast("Mapping[str, Mapping[str, object]]", payload["states"])
    assert len(states) == 7
    assert states["execution_readiness"]["state"] == "degraded"
    assert states["safety"]["state"] == "ok"
    assert states["data_freshness"]["state"] == "degraded"
    assert "global_colour" not in payload
    assert "overall" not in payload
    requested = cast("Mapping[str, object]", payload["requested_protection"])
    enforced = cast("Mapping[str, object]", payload["enforced_protection"])
    assert requested["ksa"] == "elevated"
    assert enforced["ksa"] == "normal"

    # Injected IndependentHealthReport path.
    report = IndependentHealthReport(
        states=default_health_report(
            authority_source="replicated-evidence",
            source_time_ns=7,
            receive_time_ns=8,
            watermark_ns=6,
        ).states
    )
    injected = _ok(api.read_health(_runtime(health_report=report)))
    assert injected["collapsed_global_colour"] is False
    inj_states = cast("Mapping[str, Mapping[str, object]]", injected["states"])
    assert inj_states["safety"]["authority_source"] == "replicated-evidence"
