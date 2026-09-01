"""Story 25.11 — closed alert allow-list and zero-authority liveness heartbeat."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar

import pytest
from qmf.core.refusal import Result, is_ok, is_refusal
from qmn.observability import (
    CAN_CALL_DOOR,
    CAN_CLOSE_POSITIONS,
    CAN_STOP_ENTRIES,
    DAILY_LIVENESS_DIGEST_EXISTS,
    HOLDS_INBOUND_NODE_PATH,
    HOLDS_ZERO_AUTHORITY,
    NFR11_REQUIRED_FIELDS,
    PUSH_ALERT_CLASSES,
    QUIET_HOURS_EXIST,
    UI_STREAMED_HEALTH_VIEW_IMPLEMENTED,
    AlertPublisher,
    LivenessHeartbeat,
    RecordingLivenessHttpSink,
    RecordingNotificationChannel,
    WatcherDouble,
    default_failures_path,
    generate_alert_allow_list,
    load_alert_allow_list,
    parse_failures_register,
    push_classes_for_tier,
)
from qmn.observability.failures_gate import validate_failures_completeness
from qmn.time import CLOCK_BAND_FAILURE_IDS

T = TypeVar("T")

_QMN_ROOT = Path(__file__).resolve().parents[1]
_OBS_SRC = _QMN_ROOT / "src" / "qmn" / "observability"
_FAILURES = _QMN_ROOT / "FAILURES.md"


def _try_symlink(link: Path, target: Path) -> None:
    """Create a symlink or skip where the platform forbids it (Windows without privilege)."""
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not permitted on this platform")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


# --- allow-list generation from FAILURES.md ---------------------------------


def test_failures_path_and_nfr11_shape() -> None:
    assert default_failures_path() == _FAILURES
    assert _FAILURES.is_file()
    assert NFR11_REQUIRED_FIELDS == (
        "Failure class",
        "Detection",
        "Auto-recovery / retry",
        "Visible degraded state",
        "Notification tier",
        "Product-user affordance",
    )


def test_parse_failures_register_has_all_six_fields() -> None:
    entries = _ok(parse_failures_register(_FAILURES))
    assert len(entries) >= 12
    fr_ids = {entry.fr_id for entry in entries}
    assert "FR-1" in fr_ids
    assert "FR-10" in fr_ids
    assert "FR-13" in fr_ids
    for entry in entries:
        mapping = entry.as_mapping()
        assert mapping["fr_id"] == entry.fr_id
        assert entry.failure_class
        assert entry.detection
        assert entry.auto_recovery
        assert entry.visible_degraded_state
        assert entry.notification_tier
        assert entry.product_user_affordance


def test_parse_failures_register_refuses_symlink_and_oversize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from qmn.observability import alerts as alerts_mod

    root = tmp_path / "qmn-root"
    root.mkdir()
    monkeypatch.setattr(alerts_mod, "_failures_root", lambda: root)

    outside = tmp_path / "outside.md"
    outside.write_text("# FR-99 Outside\n", encoding="utf-8")
    link = root / "FAILURES.md"
    _try_symlink(link, outside)
    refused = parse_failures_register(link)
    assert is_refusal(refused)
    assert "symlink" in str(refused.context["reason"])

    monkeypatch.setattr(alerts_mod, "_MAX_FAILURES_BYTES", 8)
    oversize = root / "FAILURES-big.md"
    oversize.write_text("x" * 32, encoding="utf-8")
    refused_size = parse_failures_register(oversize)
    assert is_refusal(refused_size)
    assert "size cap" in str(refused_size.context["reason"])


def test_parse_failures_register_uses_o_nofollow_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from qmn.observability import alerts as alerts_mod

    root = tmp_path / "qmn-root"
    root.mkdir()
    monkeypatch.setattr(alerts_mod, "_failures_root", lambda: root)

    regular = root / "FAILURES-ok.md"
    regular.write_text(
        "\n".join(
            (
                "### FR-1: Ok",
                "- **Failure class:** policy rejection",
                "- **Detection:** test detection",
                "- **Auto-recovery / retry:** none",
                "- **Visible degraded state:** refused",
                "- **Notification tier:** operator-visible (journaled)",
                "- **Product-user affordance:** retry as operator",
                "",
            )
        ),
        encoding="utf-8",
    )
    loaded = _ok(parse_failures_register(regular))
    assert len(loaded) == 1
    assert loaded[0].fr_id == "FR-1"

    monkeypatch.setattr(alerts_mod, "_MAX_FAILURES_BYTES", 8)
    oversize = root / "FAILURES-big.md"
    oversize.write_text("x" * 32, encoding="utf-8")
    refused_size = parse_failures_register(oversize)
    assert is_refusal(refused_size)
    assert "size cap" in str(refused_size.context["reason"])

    source = (_OBS_SRC / "alerts.py").read_text(encoding="utf-8")
    assert "O_NOFOLLOW" in source
    assert "os.open" in source
    assert "stat.S_ISREG" in source
    assert "path.read_text" not in source
    assert "path.stat()" not in source


def test_closed_push_classes_cover_three_accepted_classes() -> None:
    assert PUSH_ALERT_CLASSES == (
        "money-boundary",
        "protection-escalation",
        "silent-degradation",
    )
    allow_list = _ok(load_alert_allow_list())
    assert tuple(allow_list.by_class.keys()) == PUSH_ALERT_CLASSES
    # Every accepted class has at least one generated member (AR-82 / DEC-0261).
    assert allow_list.by_class["money-boundary"]
    assert allow_list.by_class["protection-escalation"]
    assert allow_list.by_class["silent-degradation"]
    assert "FR-13" in allow_list.by_class["money-boundary"]
    assert "FR-16" in allow_list.by_class["protection-escalation"]
    assert "FR-10" in allow_list.by_class["silent-degradation"]
    assert "clock.band.no_new_entry" in allow_list.by_class["silent-degradation"]
    # FR-11 spans silent-degradation and protection-escalation (stand-down).
    assert "FR-11" in allow_list.by_class["silent-degradation"]
    assert "FR-11" in allow_list.by_class["protection-escalation"]


def test_non_push_tiers_are_not_on_allow_list() -> None:
    allow_list = _ok(load_alert_allow_list())
    # FR-1 is operator-visible (journaled) — not a push class.
    assert "FR-1" not in allow_list.member_ids
    assert push_classes_for_tier("operator-visible (journaled)") == frozenset()
    assert push_classes_for_tier("silent-log") == frozenset()
    assert push_classes_for_tier("silent-degradation") == frozenset({"silent-degradation"})


def test_unregistered_failure_cannot_be_alerted() -> None:
    allow_list = _ok(load_alert_allow_list())
    channel = RecordingNotificationChannel()
    publisher = AlertPublisher(allow_list=allow_list, channel=channel)

    refused = publisher.publish(
        failure_id="not-a-registered-failure",
        summary="should never push",
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "failure_id"
    assert "unregistered" in str(refused.context["reason"])
    assert channel.delivered == []

    # Registered but non-push (operator-visible) also refuses.
    non_push = publisher.publish(failure_id="FR-1", summary="journal only")
    assert is_refusal(non_push)
    assert channel.delivered == []


def test_allow_listed_failure_publishes_through_channel() -> None:
    allow_list = _ok(load_alert_allow_list())
    channel = RecordingNotificationChannel()
    publisher = AlertPublisher(allow_list=allow_list, channel=channel)
    payload = _ok(
        publisher.publish(
            failure_id="FR-10",
            summary="clock band no-new-entry",
            correlation_id="corr-alert-1",
        )
    )
    assert payload.failure_id == "FR-10"
    assert payload.alert_class == "silent-degradation"
    assert payload.as_mapping()["authorizes"] is False
    assert payload.as_mapping()["erases_evidence_on_loss"] is False
    assert len(channel.delivered) == 1
    assert channel.delivered[0].correlation_id == "corr-alert-1"

    # Detection id alias also pushes.
    via_detection = _ok(
        publisher.publish(
            failure_id="clock.band.no_new_entry",
            summary="same class via detection id",
        )
    )
    assert via_detection.alert_class == "silent-degradation"


def test_typed_failure_ids_have_register_entries() -> None:
    """CI gate: every known typed failure id resolves in FAILURES.md (TN-23)."""
    report = _ok(validate_failures_completeness())
    allow_list = report.allow_list
    registered = allow_list.registered_ids()
    missing = [
        failure_id
        for failure_id in CLOCK_BAND_FAILURE_IDS.values()
        if failure_id not in registered
    ]
    assert missing == [], f"typed failure ids missing from FAILURES.md: {missing}"
    for entry in allow_list.entries:
        assert entry.fr_id in registered
    for failure_id in report.emitted_ids:
        assert failure_id in report.registered_ids or any(
            failure_id.startswith(f"{parent}.") for parent in report.registered_ids
        )


def test_generate_allow_list_rejects_empty() -> None:
    refused = generate_alert_allow_list(())
    assert is_refusal(refused)


def test_no_daily_digest_or_quiet_hours() -> None:
    from qmn.observability import alerts as alerts_mod
    from qmn.observability import liveness as liveness_mod

    assert DAILY_LIVENESS_DIGEST_EXISTS is False
    assert alerts_mod.DAILY_LIVENESS_DIGEST_EXISTS is False
    assert liveness_mod.DAILY_LIVENESS_DIGEST_EXISTS is False
    assert QUIET_HOURS_EXIST is False
    assert UI_STREAMED_HEALTH_VIEW_IMPLEMENTED is False
    # Rejected features must not appear as class definitions.
    banned_classes = ("DailyLivenessDigest", "QuietHours", "LivenessDigest")
    violations: list[str] = []
    for path in sorted(_OBS_SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token in banned_classes:
            if f"class {token}" in text:
                violations.append(f"{path.name}: defines {token}")
    assert violations == []


# --- liveness heartbeat (zero authority) ------------------------------------


def test_liveness_heartbeat_emits_on_cadence_through_injected_sink() -> None:
    watcher = WatcherDouble(cadence_ns=1_000_000_000)
    sink = RecordingLivenessHttpSink(watcher=watcher)
    heartbeat = _ok(
        LivenessHeartbeat.try_create(
            endpoint="https://watcher.example/ping/abc",
            cadence_ns=1_000_000_000,
            token_reference="cred-ref-liveness-hb-001",
            sink=sink,
        )
    )
    assert _ok(heartbeat.maybe_emit(0)) is True
    assert heartbeat.emissions == 1
    assert len(sink.posts) == 1
    assert sink.posts[0]["endpoint"] == "https://watcher.example/ping/abc"
    assert sink.posts[0]["token_reference"] == "cred-ref-liveness-hb-001"
    assert sink.posts[0]["carries_secret_value"] is False
    assert _ok(watcher.evaluate(500_000_000)) == "alive"

    # Inside cadence — no second ping.
    assert _ok(heartbeat.maybe_emit(500_000_000)) is False
    assert heartbeat.emissions == 1

    # Cadence elapsed — second ping.
    assert _ok(heartbeat.maybe_emit(1_000_000_000)) is True
    assert heartbeat.emissions == 2


def test_stopped_pings_produce_missing_notification_on_watcher_double() -> None:
    watcher = WatcherDouble(cadence_ns=1_000_000_000)
    sink = RecordingLivenessHttpSink(watcher=watcher)
    heartbeat = _ok(
        LivenessHeartbeat.try_create(
            endpoint="https://watcher.example/ping/abc",
            cadence_ns=1_000_000_000,
            token_reference="cred-ref-liveness-hb-001",
            sink=sink,
        )
    )
    _ok(heartbeat.maybe_emit(0))
    assert _ok(watcher.evaluate(100)) == "alive"
    assert watcher.missing_notifications == []

    # Pings stop; watcher evaluates past cadence → missing-ping notification.
    state = _ok(watcher.evaluate(1_000_000_001))
    assert state == "missing-ping"
    assert watcher.missing_notifications == [1_000_000_001]

    # Latched — one notification until a fresh ping clears it.
    assert _ok(watcher.evaluate(2_000_000_000)) == "missing-ping"
    assert watcher.missing_notifications == [1_000_000_001]

    _ok(heartbeat.maybe_emit(2_500_000_000))
    assert _ok(watcher.evaluate(2_500_000_000)) == "alive"


def test_liveness_holds_zero_authority_and_no_inbound_path() -> None:
    assert HOLDS_ZERO_AUTHORITY is True
    assert HOLDS_INBOUND_NODE_PATH is False
    assert CAN_STOP_ENTRIES is False
    assert CAN_CLOSE_POSITIONS is False
    assert CAN_CALL_DOOR is False
    assert LivenessHeartbeat.HOLDS_ZERO_AUTHORITY is True
    assert LivenessHeartbeat.CAN_CALL_DOOR is False

    sink = RecordingLivenessHttpSink()
    heartbeat = _ok(
        LivenessHeartbeat.try_create(
            endpoint="https://watcher.example/ping/abc",
            cadence_ns=10,
            token_reference="cred-ref-liveness-hb-001",
            sink=sink,
        )
    )
    surface = heartbeat.authority_surface()
    assert surface["holds_zero_authority"] is True
    assert surface["holds_inbound_node_path"] is False
    assert surface["can_stop_entries"] is False
    assert surface["can_close_positions"] is False
    assert surface["can_call_door"] is False
    assert surface["daily_liveness_digest_exists"] is False

    # No authority-bearing methods on the heartbeat surface.
    banned_methods = {
        "stop_entries",
        "close_positions",
        "close_position",
        "close_all",
        "flatten",
        "call_door",
        "enact_power",
        "suspend_new",
        "stand_down",
    }
    present = banned_methods & set(dir(heartbeat))
    assert present == set()


def test_liveness_module_never_imports_doors_or_trading_controls() -> None:
    banned_imports = {
        "qmn.doors",
        "qmn.doors.api",
        "qmn.doors.library",
        "qmn.doors.http",
        "qmn.order",
        "qmn.host.supervise",
    }
    banned_calls = {
        "stop_entries",
        "close_positions",
        "close_position",
        "close_all",
        "flatten",
        "enact_power",
        "handle_powers_call",
    }
    path = _OBS_SRC / "liveness.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called.add(func.id)
            elif isinstance(func, ast.Attribute):
                called.add(func.attr)
    assert not (imported & banned_imports), imported & banned_imports
    assert not (called & banned_calls), called & banned_calls


def test_liveness_try_create_refuses_blank_and_non_positive_cadence() -> None:
    sink = RecordingLivenessHttpSink()
    refused_ep = LivenessHeartbeat.try_create(
        endpoint=" ",
        cadence_ns=1,
        token_reference="cred-ref",
        sink=sink,
    )
    assert is_refusal(refused_ep)
    refused_cadence = LivenessHeartbeat.try_create(
        endpoint="https://watcher.example/ping",
        cadence_ns=0,
        token_reference="cred-ref",
        sink=sink,
    )
    assert is_refusal(refused_cadence)
