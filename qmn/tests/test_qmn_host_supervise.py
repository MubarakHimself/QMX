"""Story 25.6 — safe points, stand-down, watchdog, requested-restart, shutdown."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar

from qmf.core.refusal import Result, is_ok, is_refusal
from qmn.host import (
    ASYNC_ALLOWED_SURFACES,
    CLEAN_STOP_EXIT_CODE,
    DOMAIN_BACKGROUND_THREADS_ALLOWED,
    DRAIN_WINDOW_BREACH_EXIT_CODE,
    EVENT_LOOP_COUNT,
    NODE_RESURRECT_SUBTYPE,
    OPERATOR_PRINCIPAL,
    REQUESTED_RESTART_EXIT_CODE,
    REQUESTED_RESTART_REASON,
    SUPERVISION_SURFACE,
    CommandFate,
    CrashLoopFold,
    LifecycleState,
    LifecycleSupervisor,
    RecordingNotifyTransport,
    SafePointSnapshot,
    ShutdownKind,
    StandDownTrigger,
    SupervisionConfig,
    admit_under_lifecycle,
    evaluate_safe_point,
    notify_ready,
    notify_watchdog,
    notify_watchdog_trigger,
    sd_notify,
    supervision_process_model,
)
from qmn.host.supervise import BootAttemptStamp, StdlibSdNotifyTransport

T = TypeVar("T")

_QMN_SRC = Path(__file__).resolve().parents[1] / "src" / "qmn"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _config(
    *,
    k: int = 3,
    window_ns: int = 60_000_000_000,
    drain_ns: int = 30_000_000_000,
    watchdog_ns: int = 5_000_000_000,
    deadline_ns: int = 1_000_000_000,
    trip_multiple: int = 3,
) -> SupervisionConfig:
    return _ok(
        SupervisionConfig.try_create(
            crash_loop_max_boots=k,
            crash_loop_window_ns=window_ns,
            drain_window_ns=drain_ns,
            watchdog_interval_ns=watchdog_ns,
            seat_callback_deadline_ns=deadline_ns,
            slice_watch_trip_multiple=trip_multiple,
        )
    )


def _supervisor(**overrides: object) -> LifecycleSupervisor:
    notify = RecordingNotifyTransport()
    kwargs: dict[str, object] = {
        "config": _config(),
        "notify": notify,
        "boot_epoch_id": "boot-1",
    }
    kwargs.update(overrides)
    return LifecycleSupervisor(**kwargs)  # type: ignore[arg-type]


def test_process_model_constants_and_surface() -> None:
    model = supervision_process_model()
    assert SUPERVISION_SURFACE == "qmn.host"
    assert model["event_loop_count"] == EVENT_LOOP_COUNT == 1
    assert model["async_allowed_surfaces"] == ASYNC_ALLOWED_SURFACES == (
        "venue_edge",
        "doors",
    )
    assert model["domain_background_threads_allowed"] is DOMAIN_BACKGROUND_THREADS_ALLOWED
    assert DOMAIN_BACKGROUND_THREADS_ALLOWED is False
    assert model["sd_notify_owner"] == "supervisor_door_layer"
    assert model["watchdog_owner"] == "supervisor_door_layer"
    assert model["slice_progress_watch_owner"] == "supervisor_door_layer"
    assert model["requested_restart_exit_code"] == REQUESTED_RESTART_EXIT_CODE == 75
    assert model["clean_stop_exit_code"] == CLEAN_STOP_EXIT_CODE == 0
    assert model["drain_window_breach_exit_code"] == DRAIN_WINDOW_BREACH_EXIT_CODE == 76


def test_sd_notify_recording_and_unset_socket_noop() -> None:
    transport = RecordingNotifyTransport()
    assert is_ok(notify_ready(transport=transport))
    assert is_ok(notify_watchdog(transport=transport))
    assert is_ok(notify_watchdog_trigger(transport=transport))
    assert transport.messages == ["READY=1", "WATCHDOG=1", "WATCHDOG=trigger"]
    # Unset NOTIFY_SOCKET → stdlib transport is a no-op success.
    assert is_ok(sd_notify("READY=1", transport=StdlibSdNotifyTransport()))
    assert is_refusal(sd_notify("", transport=transport))


def test_no_python_systemd_or_sdnotify_dependency() -> None:
    banned = ("systemd", "sdnotify", "python_systemd")
    violations: list[str] = []
    for path in sorted((_QMN_SRC / "host").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".", 1)[0]
                    if root in banned:
                        violations.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".", 1)[0]
                if root in banned:
                    violations.append(f"{path.name}: from {node.module}")
    assert violations == []


def test_watchdog_keepalive_continues_through_stand_down() -> None:
    supervisor = _supervisor()
    notify = supervisor.notify
    assert isinstance(notify, RecordingNotifyTransport)
    _ok(supervisor.mark_ready())
    _ok(supervisor.enter_stand_down(trigger=StandDownTrigger.CLOCK_HALT))
    assert supervisor.state is LifecycleState.STAND_DOWN_ALIVE
    assert supervisor.doors_serving is True
    _ok(supervisor.tick_watchdog())
    assert "WATCHDOG=1" in notify.messages
    assert "READY=1" in notify.messages


def test_slice_progress_watch_stops_keepalive_with_trigger() -> None:
    supervisor = _supervisor()
    notify = supervisor.notify
    assert isinstance(notify, RecordingNotifyTransport)
    _ok(supervisor.publish_slice_start(mono_ns=0))
    # deadline 1s * multiple 3 = 3s; elapsed 3_000_000_001 trips.
    trip = _ok(supervisor.evaluate_slice_progress(now_mono_ns=3_000_000_001))
    assert trip is not None
    assert trip.notify_state == "WATCHDOG=trigger"
    assert trip.keepalive_stopped is True
    assert trip.alarm_class == "silent-degradation"
    assert supervisor.keepalive_enabled is False
    assert is_refusal(supervisor.tick_watchdog())
    assert "WATCHDOG=trigger" in notify.messages


def test_safe_point_requires_settled_commands_never_positions() -> None:
    snapshot = SafePointSnapshot(
        between_slices=True,
        suspend_new_enforced=True,
        command_fates={
            "cmd-1": CommandFate.TERMINAL,
            "cmd-2": CommandFate.UNKNOWN_MINTED,
        },
        sinks_flushed=True,
        positions_flat=False,
    )
    evaluated = _ok(evaluate_safe_point(snapshot))
    assert evaluated.is_safe_point is True
    assert evaluated.positions_flat is False

    unsafe = SafePointSnapshot(
        between_slices=True,
        suspend_new_enforced=True,
        command_fates={"cmd-open": CommandFate.UNRESOLVED},
        sinks_flushed=True,
        positions_flat=True,
    )
    assert _ok(evaluate_safe_point(unsafe)).is_safe_point is False


def test_stand_down_refuses_entries_passes_risk_non_increasing() -> None:
    assert _ok(
        admit_under_lifecycle(
            state=LifecycleState.STAND_DOWN_ALIVE,
            kind="place_order",
            risk_increasing=True,
        )
    ) == "refuse-entry"
    assert _ok(
        admit_under_lifecycle(
            state=LifecycleState.STAND_DOWN_ALIVE,
            kind="risk_increasing_amend_protection",
        )
    ) == "refuse-entry"
    assert _ok(
        admit_under_lifecycle(
            state=LifecycleState.STAND_DOWN_ALIVE,
            kind="close_position",
        )
    ) == "admit"
    assert _ok(
        admit_under_lifecycle(
            state=LifecycleState.STAND_DOWN_ALIVE,
            kind="flatten",
        )
    ) == "admit"
    assert _ok(
        admit_under_lifecycle(
            state=LifecycleState.STAND_DOWN_ALIVE,
            kind="risk_non_increasing_amend_protection",
        )
    ) == "admit"


def test_only_operator_resurrect_clears_stand_down_restart_does_not() -> None:
    supervisor = _supervisor()
    _ok(supervisor.enter_stand_down(trigger=StandDownTrigger.PREFLIGHT_REFUSAL))
    refused = supervisor.resurrect(
        principal="ops",
        scope="global",
        new_boot_epoch_id="boot-2",
    )
    assert is_refusal(refused)
    assert supervisor.state is LifecycleState.STAND_DOWN_ALIVE

    # A plain restart stamp does not clear stand-down.
    supervisor.state = LifecycleState.STAND_DOWN_ALIVE
    assert supervisor.stand_down_trigger is StandDownTrigger.PREFLIGHT_REFUSAL

    receipt = _ok(
        supervisor.resurrect(
            principal=OPERATOR_PRINCIPAL,
            scope="global",
            new_boot_epoch_id="boot-2",
        )
    )
    assert receipt.subtype == NODE_RESURRECT_SUBTYPE
    assert receipt.journals_ct30 is False
    assert receipt.clears_by_restart is False
    assert receipt.new_boot_epoch_id == "boot-2"
    assert supervisor.state is LifecycleState.RUNNING
    assert supervisor.boot_epoch_id == "boot-2"
    assert supervisor.stand_down_trigger is None
    assert any(
        event.get("kind") == NODE_RESURRECT_SUBTYPE for event in supervisor.journal_events
    )


def test_crash_loop_counts_unrequested_exits_not_requested_restart() -> None:
    fold = CrashLoopFold(max_boots=3, window_ns=60_000_000_000)
    base = 1_000_000_000_000
    for index in range(2):
        verdict = _ok(
            fold.record(
                BootAttemptStamp(
                    boot_epoch_id=f"boot-crash-{index}",
                    at_ns=base + index,
                    reason=None,
                    exited=True,
                )
            )
        )
        assert verdict.threshold_breached is False

    # Requested restart does not advance the fold.
    after_restart = _ok(
        fold.record(
            BootAttemptStamp(
                boot_epoch_id="boot-restart",
                at_ns=base + 2,
                reason=REQUESTED_RESTART_REASON,
                exited=True,
            )
        )
    )
    assert after_restart.counted_boots == 2
    assert after_restart.threshold_breached is False

    # Preflight stand-down without exit does not advance.
    after_alive = _ok(
        fold.record(
            BootAttemptStamp(
                boot_epoch_id="boot-preflight",
                at_ns=base + 3,
                reason="preflight-refusal",
                exited=False,
            )
        )
    )
    assert after_alive.counted_boots == 2

    breached = _ok(
        fold.record(
            BootAttemptStamp(
                boot_epoch_id="boot-crash-2",
                at_ns=base + 4,
                reason=None,
                exited=True,
            )
        )
    )
    assert breached.counted_boots == 3
    assert breached.threshold_breached is True


def test_crash_loop_threshold_enters_stand_down_alive() -> None:
    supervisor = _supervisor()
    base = 5_000_000_000_000
    for index in range(3):
        _ok(
            supervisor.record_boot_attempt(
                boot_epoch_id=f"boot-{index}",
                at_ns=base + index,
                reason=None,
                exited=True,
            )
        )
    assert supervisor.state is LifecycleState.STAND_DOWN_ALIVE
    assert supervisor.stand_down_trigger is StandDownTrigger.CRASH_LOOP
    assert supervisor.doors_serving is True


def test_requested_restart_exits_75_without_advancing_crash_loop() -> None:
    supervisor = _supervisor()
    notify = supervisor.notify
    assert isinstance(notify, RecordingNotifyTransport)
    _ok(supervisor.set_command_fate("cmd-a", CommandFate.TERMINAL))
    _ok(supervisor.set_command_fate("cmd-b", CommandFate.UNRESOLVED))
    _ok(supervisor.begin_drain(kind=ShutdownKind.REQUESTED_RESTART, now_mono_ns=0))
    assert supervisor.suspend_new_enforced is True
    assert _ok(
        admit_under_lifecycle(state=LifecycleState.DRAINING, kind="place_order")
    ) == "refuse-entry"

    outcome = _ok(
        supervisor.complete_drain(
            now_mono_ns=1_000_000,
            unresolved_command_ids=("cmd-b",),
            flush_ok=True,
        )
    )
    assert outcome.exit_code == REQUESTED_RESTART_EXIT_CODE == 75
    assert outcome.reached_safe_point is True
    assert outcome.flattened is False
    assert outcome.waited_for_flat is False
    assert outcome.sessions_closed is True
    assert outcome.unknown_minted_command_ids == ("cmd-b",)
    assert supervisor.command_fates["cmd-b"] is CommandFate.UNKNOWN_MINTED
    assert supervisor.state is LifecycleState.STOPPED

    # Next boot stamped requested-restart does not count toward crash-loop.
    fold = CrashLoopFold(max_boots=3, window_ns=60_000_000_000)
    verdict = _ok(
        fold.record(
            BootAttemptStamp(
                boot_epoch_id="boot-after-restart",
                at_ns=10,
                reason=REQUESTED_RESTART_REASON,
                exited=True,
            )
        )
    )
    assert verdict.counted_boots == 0


def test_sigterm_mints_unknown_flushes_never_flattens() -> None:
    supervisor = _supervisor()
    _ok(supervisor.set_command_fate("in-flight", CommandFate.UNRESOLVED))
    _ok(supervisor.set_command_fate("done", CommandFate.TERMINAL))
    _ok(supervisor.begin_drain(kind=ShutdownKind.SIGTERM, now_mono_ns=100))
    outcome = _ok(supervisor.complete_drain(now_mono_ns=200, flush_ok=True))
    assert outcome.kind is ShutdownKind.SIGTERM
    assert outcome.exit_code == CLEAN_STOP_EXIT_CODE
    assert outcome.unknown_minted_command_ids == ("in-flight",)
    assert outcome.flattened is False
    assert outcome.waited_for_flat is False
    assert outcome.lifecycle_stop_minted is True
    assert any(
        event.get("kind") == "lifecycle-stop" and event.get("flattened") is False
        for event in supervisor.journal_events
    )
    assert any(
        event.get("kind") == "UNKNOWN"
        and event.get("trigger") == "disconnect"
        and event.get("command_id") == "in-flight"
        for event in supervisor.journal_events
    )


def test_drain_window_breach_exits_neither_0_nor_75() -> None:
    supervisor = _supervisor()
    _ok(supervisor.begin_drain(kind=ShutdownKind.SIGTERM, now_mono_ns=0))
    # drain_window default 30s; breach at 30s+1ns.
    outcome = _ok(
        supervisor.complete_drain(now_mono_ns=30_000_000_001, flush_ok=True)
    )
    assert outcome.reached_safe_point is False
    assert outcome.exit_code == DRAIN_WINDOW_BREACH_EXIT_CODE
    assert outcome.exit_code not in {CLEAN_STOP_EXIT_CODE, REQUESTED_RESTART_EXIT_CODE}
    assert outcome.flattened is False


def test_flush_failure_refuses_clean_exit_stays_up() -> None:
    supervisor = _supervisor()
    _ok(supervisor.begin_drain(kind=ShutdownKind.SIGTERM, now_mono_ns=0))
    refused = supervisor.complete_drain(now_mono_ns=10, flush_ok=False)
    assert is_refusal(refused)
    assert supervisor.state is LifecycleState.DRAINING
    assert supervisor.sinks_flushed is False
    assert "silent-degradation" in supervisor.alarms
    assert supervisor.keepalive_enabled is True


def test_supervision_config_rejects_blank_bounds() -> None:
    assert is_refusal(
        SupervisionConfig.try_create(
            crash_loop_max_boots=0,
            crash_loop_window_ns=1,
            drain_window_ns=1,
            watchdog_interval_ns=1,
            seat_callback_deadline_ns=1,
            slice_watch_trip_multiple=1,
        )
    )
