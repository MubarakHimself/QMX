"""Story 25.9 — live clock discipline and the three calendar kinds (TN-14)."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from qmf.core import (
    CalendarIdentity,
    CivilDate,
    Clock,
    Instant,
    MonotonicReading,
    TradingDate,
)
from qmf.core.refusal import Result, is_ok, is_refusal
from qmn.host import StandDownTrigger
from qmn.time import (
    CALENDAR_IDENTITIES,
    CALENDAR_TIMER_KINDS,
    CLOCK_BAND_FAILURE_IDS,
    TIME_SURFACE,
    VPS_CLOCK_SURFACE,
    ActivationSchedule,
    CalendarKind,
    ClockBand,
    ClockDriftThresholds,
    MachineVersusTruth,
    NodeVersusBrokerSkew,
    SyncPosture,
    VpsClock,
    WallMonotonicDivergenceDetector,
    activation_effective_trading_date,
    broker_skew_is_not_latency,
    calendar_identities,
    calendar_kind_from_token,
    clock_band_entry_side_refused,
    clock_band_preserves_protection,
    clock_band_requires_stand_down,
    evaluate_clock_band,
    evaluate_sync_posture,
    measurements_named_apart,
    named_time_rules,
    record_unsynchronized_interval,
    refuse_bare_calendar_token,
    refuse_time_substitute,
)

T = TypeVar("T")

_QMN_SRC = Path(__file__).resolve().parents[1] / "src" / "qmn"
_TIME_SRC = _QMN_SRC / "time"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int) -> Instant:
    return _ok(Instant.try_create(ns))


def _thresholds(
    *,
    warn: int = 25_000_000,
    nne: int = 100_000_000,
    halt: int = 250_000_000,
    unsync: int = 60_000_000_000,
) -> ClockDriftThresholds:
    return _ok(
        ClockDriftThresholds.try_create(
            warn_ns=warn,
            no_new_entry_ns=nne,
            halt_ns=halt,
            unsynchronized_after_ns=unsync,
        )
    )


def _truth(
    *,
    offset_ns: int = 0,
    sync_age_ns: int = 0,
    synchronized: bool = True,
    stratum: int = 2,
    step_count: int = 0,
) -> MachineVersusTruth:
    return _ok(
        MachineVersusTruth.try_create(
            offset_ns=offset_ns,
            stratum=stratum,
            sync_age_ns=sync_age_ns,
            step_count=step_count,
            synchronized=synchronized,
        )
    )


@dataclass
class _FakeDayBoundary:
    identity: CalendarIdentity
    next_ns: int

    def trading_date_for(self, instant: Instant) -> Result[TradingDate]:
        civil = _ok(CivilDate.try_create(2026, 9, 1))
        return TradingDate.try_create(self.identity, civil)

    def next_boundary_after(self, instant: Instant) -> Result[Instant]:
        del instant
        return Instant.try_create(self.next_ns)


def test_surface_and_three_calendar_kinds() -> None:
    assert TIME_SURFACE == VPS_CLOCK_SURFACE == "qmn.time"
    assert calendar_identities() == CALENDAR_IDENTITIES == (
        "market_hours_calendar",
        "day_boundary_calendar",
        "news_calendar",
    )
    assert "news_calendar_timer" in CALENDAR_TIMER_KINDS
    assert "market-hours calendar" in named_time_rules()
    assert "calendar timer" in named_time_rules()


def test_refuse_bare_calendar_and_time_substitutes() -> None:
    bare = refuse_bare_calendar_token("calendar")
    assert is_refusal(bare)
    assert bare.context["field"] == "calendar"

    assert _ok(calendar_kind_from_token("accounting calendar")) is CalendarKind.DAY_BOUNDARY
    assert _ok(calendar_kind_from_token("trading")) is CalendarKind.MARKET_HOURS
    assert _ok(calendar_kind_from_token("news_calendar")) is CalendarKind.NEWS

    local = refuse_time_substitute("local time")
    assert is_refusal(local)
    broker = refuse_time_substitute("broker server time")
    assert is_refusal(broker)
    assert _ok(refuse_time_substitute("market-hours calendar")) == "market-hours calendar"


def test_vps_clock_is_injected_clock_stamping_utc_ns() -> None:
    walls = iter([1_700_000_000_000_000_000, 1_700_000_000_000_000_100])
    monos = iter([10, 20])
    clock = _ok(
        VpsClock.try_create(
            boot_epoch_id="boot-1",
            wall_ns=lambda: next(walls),
            monotonic_ns=lambda: next(monos),
        )
    )
    assert isinstance(clock, Clock)
    wall = _ok(clock.wall_now())
    assert wall.value_ns == 1_700_000_000_000_000_000
    mono = _ok(clock.monotonic_now())
    assert mono.value_ns == 10
    assert mono.boot_epoch_id == "boot-1"
    assert _ok(clock.stamp_utc_ns()) == 1_700_000_000_000_000_100


def test_no_ambient_clock_reads_below_composition_root_factory() -> None:
    """Only VpsClock.from_host_os may read the host clock (marked ambient-scan)."""
    banned_attrs = {
        "time",
        "time_ns",
        "monotonic",
        "monotonic_ns",
        "perf_counter",
        "perf_counter_ns",
    }
    violations: list[str] = []
    for path in sorted(_QMN_SRC.rglob("*.py")):
        relative = path.relative_to(_QMN_SRC)
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        lines = source.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            attr: str | None = None
            if isinstance(func, ast.Attribute):
                attr = func.attr
            elif isinstance(func, ast.Name):
                attr = func.id
            if attr not in banned_attrs:
                continue
            line = lines[node.lineno - 1] if 0 < node.lineno <= len(lines) else ""
            if "ambient-scan: allow" in line and relative.parts[:1] == ("time",):
                # Composition-root factory lines only.
                continue
            violations.append(f"{relative}:{node.lineno}: {attr}")
    assert violations == [], f"ambient clock reads below composition root: {violations}"


def test_chrony_waitsync_blocks_trade_and_records_unsynchronized_interval() -> None:
    posture = _ok(evaluate_sync_posture(chrony_waitsync_passed=False))
    assert posture is SyncPosture.PREFLIGHT_BLOCKED

    sink: list[object] = []
    started = _instant(1_700_000_000_000_000_000)
    interval = _ok(
        record_unsynchronized_interval(
            started_at=started,
            reason="chrony-waitsync-failed",
            sink=sink,  # type: ignore[arg-type]
        )
    )
    assert interval.no_entry is True
    assert interval.as_mapping()["failure_id"] == CLOCK_BAND_FAILURE_IDS["unsynchronized"]
    assert len(sink) == 1

    truth = _truth(synchronized=False, offset_ns=0)
    decision = _ok(
        evaluate_clock_band(
            thresholds=_thresholds(),
            truth=truth,
            now=started,
        )
    )
    assert decision.sync_posture is SyncPosture.PREFLIGHT_BLOCKED
    assert decision.band is ClockBand.HALT
    assert decision.stand_down is True
    assert decision.unsynchronized_interval is not None
    assert decision.failure_id == CLOCK_BAND_FAILURE_IDS["unsynchronized"]


def test_clock_bands_ok_warn_no_new_entry_halt() -> None:
    thresholds = _thresholds()
    now = _instant(1_700_000_000_000_000_000)

    ok = _ok(evaluate_clock_band(thresholds=thresholds, truth=_truth(offset_ns=1_000_000), now=now))
    assert ok.band is ClockBand.OK
    assert ok.publish_evidence is False
    assert ok.silent_degradation is False

    warn = _ok(
        evaluate_clock_band(thresholds=thresholds, truth=_truth(offset_ns=30_000_000), now=now)
    )
    assert warn.band is ClockBand.WARN
    assert warn.publish_evidence is True
    assert warn.silent_degradation is False
    assert warn.failure_id == "clock.band.warn"

    nne = _ok(
        evaluate_clock_band(thresholds=thresholds, truth=_truth(offset_ns=150_000_000), now=now)
    )
    assert nne.band is ClockBand.NO_NEW_ENTRY
    assert nne.silent_degradation is True
    assert clock_band_entry_side_refused(nne.band, act="place_order") is True
    assert clock_band_entry_side_refused(nne.band, act="cancel_order") is False
    assert clock_band_preserves_protection(nne.band, act="close_position") is True

    halt = _ok(
        evaluate_clock_band(thresholds=thresholds, truth=_truth(offset_ns=300_000_000), now=now)
    )
    assert halt.band is ClockBand.HALT
    assert halt.stand_down is True
    assert clock_band_requires_stand_down(halt.band) is True
    assert halt.as_mapping()["stand_down_trigger"] == StandDownTrigger.CLOCK_HALT.value
    assert clock_band_preserves_protection(halt.band, act="amend_protection") is True


def test_machine_versus_truth_apart_from_broker_skew() -> None:
    assert measurements_named_apart() == (
        "machine-versus-truth",
        "node-versus-broker-skew",
    )
    truth = _truth(offset_ns=40_000_000)
    assert truth.measurement_kind == "machine-versus-truth"

    skew = _ok(
        NodeVersusBrokerSkew.try_create(
            venue_id="ctrader-demo",
            local_receive_minus_source_ns=(5_000_000, -2_000_000, 9_000_000),
        )
    )
    assert skew.measurement_kind == "node-versus-broker-skew"
    assert skew.windowed_min_abs_ns == 2_000_000
    assert broker_skew_is_not_latency() is True

    decision = _ok(
        evaluate_clock_band(
            thresholds=_thresholds(),
            truth=truth,
            broker_skew=skew,
            now=_instant(1),
        )
    )
    # Truth offset drives the band; skew is not merged or renamed latency.
    assert decision.measurement_kind == "machine-versus-truth"
    assert decision.drift_ns == 40_000_000
    assert decision.band is ClockBand.WARN


def test_unsynchronized_after_horizon_distinct_from_drift() -> None:
    thresholds = _thresholds(unsync=10_000_000_000)
    truth = _truth(offset_ns=0, sync_age_ns=20_000_000_000, synchronized=True)
    posture = _ok(
        evaluate_sync_posture(
            chrony_waitsync_passed=True,
            truth=truth,
            thresholds=thresholds,
        )
    )
    assert posture is SyncPosture.UNSYNCHRONIZED
    decision = _ok(
        evaluate_clock_band(
            thresholds=thresholds,
            truth=truth,
            now=_instant(99),
        )
    )
    assert decision.sync_posture is SyncPosture.UNSYNCHRONIZED
    assert decision.failure_id == CLOCK_BAND_FAILURE_IDS["unsynchronized"]


def test_wall_monotonic_divergence_marks_suspect_window() -> None:
    detector = _ok(WallMonotonicDivergenceDetector.try_create(tolerance_ns=5_000_000))
    boot = "boot-1"
    first = _ok(
        detector.observe(
            wall=_instant(1_000_000_000),
            monotonic=_ok(MonotonicReading.try_create(0, boot)),
        )
    )
    assert first is None
    # Wall jumps 50ms while monotonic advances 1ms → suspect.
    window = _ok(
        detector.observe(
            wall=_instant(1_050_000_000),
            monotonic=_ok(MonotonicReading.try_create(1_000_000, boot)),
        )
    )
    assert window is not None
    assert window.divergence_ns == 49_000_000
    assert window.as_mapping()["no_entry"] is True
    assert len(detector.suspect_windows) == 1


def test_activation_uses_account_day_boundary_calendar() -> None:
    identity = _ok(
        CalendarIdentity.try_create("account-day-boundary", "v1", "2026a")
    )
    port = _FakeDayBoundary(identity=identity, next_ns=2_000)
    schedule = _ok(
        activation_effective_trading_date(
            binding_id="binding-1",
            signed_at=_instant(1_000),
            day_boundary=port,
        )
    )
    assert isinstance(schedule, ActivationSchedule)
    assert schedule.calendar_kind is CalendarKind.DAY_BOUNDARY
    assert schedule.effective_at.value_ns == 2_000
    assert schedule.signed_at.value_ns == 1_000
    assert schedule.as_mapping()["day_boundary_rule_set"] == "account-day-boundary"

    too_soon = activation_effective_trading_date(
        binding_id="binding-1",
        signed_at=_instant(2_000),
        day_boundary=_FakeDayBoundary(identity=identity, next_ns=2_000),
    )
    assert is_refusal(too_soon)


def test_threshold_ordering_refused() -> None:
    bad = ClockDriftThresholds.try_create(
        warn_ns=100,
        no_new_entry_ns=50,
        halt_ns=200,
        unsynchronized_after_ns=1_000,
    )
    assert is_refusal(bad)
