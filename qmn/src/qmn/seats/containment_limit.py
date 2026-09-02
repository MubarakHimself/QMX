"""Story 26.16 / E15-F03: state the V1 seat-containment limit honestly.

V1 cooperative controls (CancelToken, LimitProbe, exception catch) and the
door-layer slice-progress watch are falsifiable. Hardened OS-level memory
and security confinement is **absent** and stays GAP-0054 deferred — this
module never invents a Job Object / rlimit / seccomp cap and never closes
that gap by assertion (DEC-0204, DEC-0236, DEC-0260).
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Final, Protocol, cast

from qmb.runloop import CancelToken, LimitProbe
from qmf.core import Instant, Ok, Result, is_ok, is_refusal

from qmn.seats._refuse import clean_token, invalid, policy
from qmn.seats.host import GovernedSeat, drive_governed_seat
from qmn.seats.state import (
    OPERATOR_SEAT_REINSTATE,
    GovernedSeatState,
    QuarantineTrigger,
    SeatTransitionStream,
    fold_seat_state,
    mint_quarantine_transition,
    mint_seat_reinstate,
)

__all__ = [
    "COMPENSATING_CONTROLS",
    "CONTAINMENT_LIMIT_SURFACE",
    "GAP_0054_ID",
    "GAP_0054_STATUS",
    "OS_CONFINEMENT_APIS_ABSENT",
    "PROTECTION_ESCALATION_ALARM_CLASS",
    "QUARANTINE_FAILURE_ID",
    "SILENT_DEGRADATION_ALARM_CLASS",
    "V1_HARDENED_OS_CONFINEMENT",
    "ContainmentInjection",
    "EnforcementClass",
    "LimitHonestyRecord",
    "SeatContainmentProof",
    "V1ContainmentDocsReport",
    "prove_v1_seat_containment",
    "refuse_invented_os_hard_cap",
    "scan_os_confinement_apis",
    "v1_containment_documentation_report",
    "v1_seat_containment_limits",
]

CONTAINMENT_LIMIT_SURFACE: Final[str] = "qmn.seats.containment_limit"
GAP_0054_ID: Final[str] = "GAP-0054"
GAP_0054_STATUS: Final[str] = "deferred"
V1_HARDENED_OS_CONFINEMENT: Final[bool] = False
OS_CONFINEMENT_APIS_ABSENT: Final[bool] = True
QUARANTINE_FAILURE_ID: Final[str] = "FR-19"
PROTECTION_ESCALATION_ALARM_CLASS: Final[str] = "protection-escalation"
SILENT_DEGRADATION_ALARM_CLASS: Final[str] = "silent-degradation"

COMPENSATING_CONTROLS: Final[tuple[str, ...]] = (
    "ql-8-static-scan",
    "capability-starvation",
    "host-process-isolation",
    "callback-deadline",
    "memory-ceiling",
    "quarantine",
)

_BANNED_OS_CONFINEMENT_NAMES: Final[frozenset[str]] = frozenset(
    {
        "setrlimit",
        "RLIMIT_AS",
        "RLIMIT_RSS",
        "RLIMIT_DATA",
        "CreateJobObject",
        "AssignProcessToJobObject",
        "JobObject",
        "SECCOMP",
        "seccomp",
        "PR_SET_SECCOMP",
        "prctl",
        "win32job",
    }
)

_BANNED_OS_CONFINEMENT_IMPORTS: Final[frozenset[str]] = frozenset(
    {
        "seccomp",
        "prctl",
        "win32job",
    }
)


class EnforcementClass(StrEnum):
    """Honest V1 enforcement — cooperative, last-resort, or absent (advisory)."""

    ENFORCED = "enforced"
    ADVISORY = "advisory"
    LAST_RESORT = "last-resort"


class ContainmentInjection(StrEnum):
    """Injected seat-execution failures Story 26.16 falsifies."""

    DEADLINE = "deadline"
    COOPERATIVE_MEMORY_PROBE = "cooperative-memory-probe"
    CALLBACK_EXCEPTION = "callback-exception"
    NON_RETURNING_CALLBACK = "non-returning-callback"


class _AlertSink(Protocol):
    def publish(
        self,
        *,
        failure_id: object,
        summary: object,
        correlation_id: object | None = None,
    ) -> Result[object]:
        """Push one allow-listed containment alarm."""
        ...


class _SliceWatch(Protocol):
    def evaluate_slice_progress(self, *, now_mono_ns: object) -> Result[object]:
        """Trip when elapsed exceeds deadline × trip multiple."""
        ...

    def publish_slice_start(self, *, mono_ns: object) -> Result[object]:
        """Driver publishes the monotonic slice-start stamp."""
        ...


@dataclass(frozen=True, slots=True)
class LimitHonestyRecord:
    """One V1 containment limit with its honest enforcement class."""

    name: str
    enforcement: EnforcementClass
    cooperative: bool
    os_level: bool
    gap_id: str | None
    gap_status: str | None
    closes_gap: bool
    compensating_controls: tuple[str, ...]

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "name": self.name,
                "enforcement": self.enforcement.value,
                "cooperative": self.cooperative,
                "os_level": self.os_level,
                "gap_id": self.gap_id,
                "gap_status": self.gap_status,
                "closes_gap": self.closes_gap,
                "compensating_controls": self.compensating_controls,
            }
        )


@dataclass(frozen=True, slots=True)
class SeatContainmentProof:
    """Falsifiable outcome of one injected V1 seat-containment failure."""

    injection: ContainmentInjection
    limit_name: str
    enforcement: EnforcementClass
    cancelled_cooperatively: bool
    quarantined: bool
    alarmed: bool
    alarm_classes: tuple[str, ...]
    last_resort_watchdog: bool
    last_resort_supervised_restart: bool
    os_level_confinement: bool
    gap_0054: str
    gap_0054_closed: bool
    trigger: str | None
    seat_id: str
    exit: str
    stream_failure: bool
    node_restart_on_cooperative_breach: bool
    restart_clears_quarantine: bool
    compensating_controls: tuple[str, ...]

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "surface": CONTAINMENT_LIMIT_SURFACE,
                "injection": self.injection.value,
                "limit_name": self.limit_name,
                "enforcement": self.enforcement.value,
                "cancelled_cooperatively": self.cancelled_cooperatively,
                "quarantined": self.quarantined,
                "alarmed": self.alarmed,
                "alarm_classes": self.alarm_classes,
                "last_resort_watchdog": self.last_resort_watchdog,
                "last_resort_supervised_restart": self.last_resort_supervised_restart,
                "os_level_confinement": self.os_level_confinement,
                "gap_0054": self.gap_0054,
                "gap_0054_closed": self.gap_0054_closed,
                "trigger": self.trigger,
                "seat_id": self.seat_id,
                "exit": self.exit,
                "stream_failure": self.stream_failure,
                "node_restart_on_cooperative_breach": (self.node_restart_on_cooperative_breach),
                "restart_clears_quarantine": self.restart_clears_quarantine,
                "compensating_controls": self.compensating_controls,
                "v1_hardened_os_confinement": V1_HARDENED_OS_CONFINEMENT,
            }
        )


@dataclass(frozen=True, slots=True)
class V1ContainmentDocsReport:
    """Honesty scan of release/security prose that describes containment."""

    gap_0054_status: str
    gap_0054_closed: bool
    documents: tuple[str, ...]
    missing_required: tuple[str, ...]

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "gap_0054_status": self.gap_0054_status,
                "gap_0054_closed": self.gap_0054_closed,
                "documents": self.documents,
                "missing_required": self.missing_required,
            }
        )


def v1_seat_containment_limits() -> tuple[LimitHonestyRecord, ...]:
    """Catalog the V1 limits. OS confinement is advisory/absent, never a cap."""
    compensating = COMPENSATING_CONTROLS
    return (
        LimitHonestyRecord(
            name="callback-deadline",
            enforcement=EnforcementClass.ENFORCED,
            cooperative=True,
            os_level=False,
            gap_id=None,
            gap_status=None,
            closes_gap=False,
            compensating_controls=compensating,
        ),
        LimitHonestyRecord(
            name="memory-ceiling",
            enforcement=EnforcementClass.ENFORCED,
            cooperative=True,
            os_level=False,
            gap_id=None,
            gap_status=None,
            closes_gap=False,
            compensating_controls=compensating,
        ),
        LimitHonestyRecord(
            name="callback-exception",
            enforcement=EnforcementClass.ENFORCED,
            cooperative=True,
            os_level=False,
            gap_id=None,
            gap_status=None,
            closes_gap=False,
            compensating_controls=compensating,
        ),
        LimitHonestyRecord(
            name="non-returning-callback",
            enforcement=EnforcementClass.LAST_RESORT,
            cooperative=False,
            os_level=False,
            gap_id=None,
            gap_status=None,
            closes_gap=False,
            compensating_controls=compensating,
        ),
        LimitHonestyRecord(
            name="os-memory-security-confinement",
            enforcement=EnforcementClass.ADVISORY,
            cooperative=False,
            os_level=False,
            gap_id=GAP_0054_ID,
            gap_status=GAP_0054_STATUS,
            closes_gap=False,
            compensating_controls=compensating,
        ),
    )


def refuse_invented_os_hard_cap(**extra: object) -> Result[None]:
    """FTR-07 / E15-F03: V1 never invents an OS memory or security cap."""
    return policy(
        "os_hard_cap",
        "V1 has no hardened OS-level memory or security confinement; "
        "GAP-0054 stays deferred and this story does not invent a Job Object, "
        "rlimit, or seccomp cap (E15-F03)",
        gap_id=GAP_0054_ID,
        gap_status=GAP_0054_STATUS,
        gap_0054_closed=False,
        os_level_confinement=False,
        **extra,
    )


def prove_v1_seat_containment(
    *,
    injection: object,
    seat: object,
    instant: object,
    stream: object,
    cancel: object,
    probe: object,
    supervisor: object | None = None,
    now_mono_ns: object | None = None,
    alerts: object | None = None,
    close_gap_0054: object = False,
    os_hard_cap_bytes: object = None,
) -> Result[SeatContainmentProof]:
    """Inject one V1 seat failure and record advisory versus enforced honestly."""
    invented = _refuse_invented_claims(
        close_gap_0054=close_gap_0054,
        os_hard_cap_bytes=os_hard_cap_bytes,
    )
    if is_refusal(invented):
        return invented
    kind = _coerce_injection(injection)
    if is_refusal(kind):
        return kind
    if not isinstance(seat, GovernedSeat):
        return invalid(
            "seat",
            "V1 containment proof drives a GovernedSeat",
            given=repr(type(seat).__name__),
        )
    if not isinstance(instant, Instant):
        return invalid(
            "instant",
            "the evaluation instant is an injected Instant",
            given=repr(instant),
        )
    if not isinstance(stream, SeatTransitionStream):
        return invalid(
            "stream",
            "containment proof journals onto a SeatTransitionStream",
            given=repr(type(stream).__name__),
        )
    if not isinstance(cancel, CancelToken):
        return invalid(
            "cancel",
            "cooperative deadline cancel uses a CancelToken",
            given=repr(type(cancel).__name__),
        )
    if not isinstance(probe, LimitProbe):
        return invalid(
            "probe",
            "cooperative memory/deadline uses an injected LimitProbe",
            given=repr(type(probe).__name__),
        )
    publisher = _as_alert_sink(alerts)
    if is_refusal(publisher):
        return publisher
    if kind.value is ContainmentInjection.NON_RETURNING_CALLBACK:
        return _prove_non_returning(
            seat=seat,
            instant=instant,
            stream=stream,
            supervisor=supervisor,
            now_mono_ns=now_mono_ns,
            alerts=publisher.value,
        )
    return _prove_cooperative(
        injection=kind.value,
        seat=seat,
        instant=instant,
        stream=stream,
        cancel=cancel,
        probe=probe,
        alerts=publisher.value,
    )


def scan_os_confinement_apis(src_root: object | None = None) -> tuple[str, ...]:
    """Return banned OS-confinement API hits; empty means V1 did not invent them."""
    root = _seats_src_root() if src_root is None else Path(str(src_root))
    hits: list[str] = []
    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_name = alias.name.split(".", 1)[0]
                    if root_name in _BANNED_OS_CONFINEMENT_IMPORTS:
                        hits.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                root_name = node.module.split(".", 1)[0]
                if root_name in _BANNED_OS_CONFINEMENT_IMPORTS:
                    hits.append(f"{path.name}: from {node.module}")
            elif isinstance(node, ast.Name) and node.id in _BANNED_OS_CONFINEMENT_NAMES:
                hits.append(f"{path.name}: {node.id}")
            elif isinstance(node, ast.Attribute) and node.attr in _BANNED_OS_CONFINEMENT_NAMES:
                hits.append(f"{path.name}: {node.attr}")
    return tuple(hits)


def v1_containment_documentation_report(
    repo_root: object | None = None,
) -> Result[V1ContainmentDocsReport]:
    """Scan release/security docs for the honest V1 limit and deferred GAP-0054."""
    root = _repo_root() if repo_root is None else Path(str(repo_root))
    documents = (
        root / "docs" / "lenses" / "security" / "security-model.md",
        root / "docs" / "components" / "qml.md",
        root / "docs" / "components" / "trading-node.md",
        root / "docs" / "lenses" / "ops" / "incident-playbook.md",
        root / "qmn" / "FAILURES.md",
        root / "docs" / "gap-report.md",
    )
    required = (
        "GAP-0054",
        "no hardened OS-level memory or security confinement",
        "ql-8-static-scan",
        "capability starvation",
        "host process isolation",
        "callback deadline",
        "memory ceiling",
        "quarantine",
    )
    # Security prose carries the full honesty sentence; compensating-control
    # tokens may be hyphenated in code and spaced in docs — accept both.
    security = documents[0]
    try:
        security_text = security.read_text(encoding="utf-8")
    except OSError as exc:
        return invalid("docs", f"cannot read security-model.md: {exc}")
    missing: list[str] = []
    lowered_security = security_text.lower()
    for phrase in required:
        needle = phrase.lower()
        spaced = needle.replace("-", " ")
        if needle not in lowered_security and spaced not in lowered_security:
            missing.append(f"{security.name}:{phrase}")
    gap_path = documents[-1]
    try:
        gap_text = gap_path.read_text(encoding="utf-8")
    except OSError as exc:
        return invalid("docs", f"cannot read gap-report.md: {exc}")
    row = _gap_0054_row(gap_text)
    if row is None:
        missing.append("gap-report.md:GAP-0054-row")
        status = "missing"
        closed = True
    else:
        status = "deferred" if "deferred" in row.lower() else "not-deferred"
        closed = "answered" in row.lower()
        if status != GAP_0054_STATUS:
            missing.append("gap-report.md:GAP-0054-deferred")
        if closed:
            missing.append("gap-report.md:GAP-0054-closed-by-assertion")
    for path in documents[1:-1]:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            return invalid("docs", f"cannot read {path.name}: {exc}")
        if GAP_0054_ID not in text:
            missing.append(f"{path.name}:GAP-0054")
    relative = tuple(
        path.relative_to(root).as_posix() if path.is_relative_to(root) else path.name
        for path in documents
    )
    return Ok(
        V1ContainmentDocsReport(
            gap_0054_status=status,
            gap_0054_closed=closed,
            documents=relative,
            missing_required=tuple(missing),
        )
    )


def _prove_cooperative(
    *,
    injection: ContainmentInjection,
    seat: GovernedSeat,
    instant: Instant,
    stream: SeatTransitionStream,
    cancel: CancelToken,
    probe: LimitProbe,
    alerts: _AlertSink | None,
) -> Result[SeatContainmentProof]:
    cancelled = False
    if injection is ContainmentInjection.DEADLINE and not cancel.is_cancelled:
        cancelled_result = cancel.cancel(QuarantineTrigger.DEADLINE_BREACH.value)
        if is_refusal(cancelled_result):
            return cancelled_result
        cancelled = True
    driven = drive_governed_seat(
        seat,
        instant,
        stream=stream,
        cancel=cancel,
        probe=probe,
        transition_instant=instant,
    )
    if not is_refusal(driven):
        return policy(
            "injection",
            "a cooperative containment injection must quarantine",
            injection=injection.value,
        )
    trigger = str(driven.context.get("trigger", "")) or None
    published = _publish_quarantine_alarm(
        alerts,
        seat_id=seat.seat_id,
        trigger=trigger or injection.value,
    )
    if is_refusal(published):
        return published
    folded = fold_seat_state(stream, seat.seat_id)
    if is_refusal(folded):
        return folded
    restart_exit = _restart_does_not_clear(seat=seat, instant=instant, stream=stream)
    if is_refusal(restart_exit):
        return restart_exit
    return Ok(
        _proof(
            injection=injection,
            enforcement=EnforcementClass.ENFORCED,
            cancelled_cooperatively=(
                cancelled
                if injection is ContainmentInjection.DEADLINE
                else injection is ContainmentInjection.COOPERATIVE_MEMORY_PROBE
            ),
            quarantined=folded.value is GovernedSeatState.QUARANTINED,
            alarm_classes=(PROTECTION_ESCALATION_ALARM_CLASS,),
            last_resort_watchdog=False,
            last_resort_supervised_restart=False,
            trigger=trigger,
            seat_id=seat.seat_id,
        )
    )


def _prove_non_returning(
    *,
    seat: GovernedSeat,
    instant: Instant,
    stream: SeatTransitionStream,
    supervisor: object | None,
    now_mono_ns: object | None,
    alerts: _AlertSink | None,
) -> Result[SeatContainmentProof]:
    """A non-returning callback is last-resort watchdog + supervised restart.

    The test never hangs the process: the wedge is injected as a published
    slice-start with no callback return, then elapsed past deadline × multiple.
    V1 cannot interrupt a live non-cooperative callback (GAP-0054).
    """
    watch = _as_slice_watch(supervisor)
    if is_refusal(watch):
        return watch
    started = getattr(supervisor, "slice_start_mono_ns", None)
    if started is None:
        published_start = watch.value.publish_slice_start(mono_ns=0)
        if is_refusal(published_start):
            return published_start
    elapsed = now_mono_ns
    if elapsed is None:
        config = getattr(supervisor, "config", None)
        deadline = getattr(config, "seat_callback_deadline_ns", None)
        multiple = getattr(config, "slice_watch_trip_multiple", None)
        if (
            isinstance(deadline, int)
            and not isinstance(deadline, bool)
            and isinstance(multiple, int)
            and not isinstance(multiple, bool)
        ):
            elapsed = deadline * multiple + 1
        else:
            return invalid(
                "now_mono_ns",
                "non-returning last-resort needs now_mono_ns or a supervisor "
                "config carrying seat_callback_deadline_ns and "
                "slice_watch_trip_multiple",
            )
    trip_result = watch.value.evaluate_slice_progress(now_mono_ns=elapsed)
    if is_refusal(trip_result):
        return trip_result
    trip = trip_result.value
    if trip is None:
        return policy(
            "injection",
            "a non-returning callback must trip the slice-progress watch",
        )
    keepalive_stopped = bool(getattr(trip, "keepalive_stopped", False))
    notify_state = str(getattr(trip, "notify_state", ""))
    if not keepalive_stopped or notify_state != "WATCHDOG=trigger":
        return policy(
            "watchdog",
            "last-resort supervised restart stops keepalive with WATCHDOG=trigger",
            keepalive_stopped=keepalive_stopped,
            notify_state=notify_state,
        )
    folded = fold_seat_state(stream, seat.seat_id)
    if is_refusal(folded):
        return folded
    current = folded.value
    if current is not GovernedSeatState.QUARANTINED:
        minted = mint_quarantine_transition(
            seat_id=seat.seat_id,
            binding_ref=seat.binding_ref,
            from_state=current,
            trigger=QuarantineTrigger.NON_RETURNING_CALLBACK.value,
            transition_instant=instant,
            breach_detail="non-returning-callback",
            stream=stream,
        )
        if is_refusal(minted):
            return minted
    published = _publish_quarantine_alarm(
        alerts,
        seat_id=seat.seat_id,
        trigger=QuarantineTrigger.NON_RETURNING_CALLBACK.value,
    )
    if is_refusal(published):
        return published
    after = fold_seat_state(stream, seat.seat_id)
    if is_refusal(after):
        return after
    restart_exit = _restart_does_not_clear(seat=seat, instant=instant, stream=stream)
    if is_refusal(restart_exit):
        return restart_exit
    alarm_classes = (
        PROTECTION_ESCALATION_ALARM_CLASS,
        SILENT_DEGRADATION_ALARM_CLASS,
    )
    return Ok(
        _proof(
            injection=ContainmentInjection.NON_RETURNING_CALLBACK,
            enforcement=EnforcementClass.LAST_RESORT,
            cancelled_cooperatively=False,
            quarantined=after.value is GovernedSeatState.QUARANTINED,
            alarm_classes=alarm_classes,
            last_resort_watchdog=True,
            last_resort_supervised_restart=True,
            trigger=QuarantineTrigger.NON_RETURNING_CALLBACK.value,
            seat_id=seat.seat_id,
        )
    )


def _proof(
    *,
    injection: ContainmentInjection,
    enforcement: EnforcementClass,
    cancelled_cooperatively: bool,
    quarantined: bool,
    alarm_classes: tuple[str, ...],
    last_resort_watchdog: bool,
    last_resort_supervised_restart: bool,
    trigger: str | None,
    seat_id: str,
) -> SeatContainmentProof:
    limit_name = {
        ContainmentInjection.DEADLINE: "callback-deadline",
        ContainmentInjection.COOPERATIVE_MEMORY_PROBE: "memory-ceiling",
        ContainmentInjection.CALLBACK_EXCEPTION: "callback-exception",
        ContainmentInjection.NON_RETURNING_CALLBACK: "non-returning-callback",
    }[injection]
    return SeatContainmentProof(
        injection=injection,
        limit_name=limit_name,
        enforcement=enforcement,
        cancelled_cooperatively=cancelled_cooperatively,
        quarantined=quarantined,
        alarmed=bool(alarm_classes),
        alarm_classes=alarm_classes,
        last_resort_watchdog=last_resort_watchdog,
        last_resort_supervised_restart=last_resort_supervised_restart,
        os_level_confinement=V1_HARDENED_OS_CONFINEMENT,
        gap_0054=GAP_0054_STATUS,
        gap_0054_closed=False,
        trigger=trigger,
        seat_id=seat_id,
        exit=OPERATOR_SEAT_REINSTATE,
        stream_failure=False,
        node_restart_on_cooperative_breach=False,
        restart_clears_quarantine=False,
        compensating_controls=COMPENSATING_CONTROLS,
    )


def _restart_does_not_clear(
    *,
    seat: GovernedSeat,
    instant: Instant,
    stream: SeatTransitionStream,
) -> Result[None]:
    inferred = mint_seat_reinstate(
        seat_id=seat.seat_id,
        binding_ref=seat.binding_ref,
        transition_instant=instant,
        operator_signature="sig-restart-must-not-clear",
        stream=stream,
        infer_from_restart=True,
    )
    if is_ok(inferred):
        return policy(
            "seat_reinstate",
            "a supervised restart must not infer seat_reinstate or clear quarantine",
        )
    return Ok(None)


def _publish_quarantine_alarm(
    alerts: _AlertSink | None,
    *,
    seat_id: str,
    trigger: str,
) -> Result[None]:
    if alerts is None:
        return Ok(None)
    published = alerts.publish(
        failure_id=QUARANTINE_FAILURE_ID,
        summary=(f"seat {seat_id} quarantined after {trigger}; only operator seat_reinstate exits"),
        correlation_id=seat_id,
    )
    if is_refusal(published):
        return published
    return Ok(None)


def _refuse_invented_claims(
    *,
    close_gap_0054: object,
    os_hard_cap_bytes: object,
) -> Result[None]:
    if close_gap_0054 is not False:
        return policy(
            "close_gap_0054",
            "no story closes GAP-0054 by assertion; V1 states the deferred "
            "OS-confinement limit honestly",
            given=repr(close_gap_0054),
            gap_id=GAP_0054_ID,
            gap_status=GAP_0054_STATUS,
        )
    if os_hard_cap_bytes is not None:
        return refuse_invented_os_hard_cap(given=repr(os_hard_cap_bytes))
    return Ok(None)


def _coerce_injection(
    value: object,
) -> Result[ContainmentInjection]:
    if isinstance(value, ContainmentInjection):
        return Ok(value)
    token = clean_token(value)
    if token is None:
        return invalid(
            "injection",
            "containment injection is deadline | cooperative-memory-probe | "
            "callback-exception | non-returning-callback",
            given=repr(value),
        )
    try:
        return Ok(ContainmentInjection(token))
    except ValueError:
        return invalid(
            "injection",
            "containment injection is deadline | cooperative-memory-probe | "
            "callback-exception | non-returning-callback",
            given=token,
            allowed=[item.value for item in ContainmentInjection],
        )


def _as_alert_sink(value: object) -> Result[_AlertSink | None]:
    if value is None:
        return Ok(None)
    publish = getattr(value, "publish", None)
    if not callable(publish):
        return invalid(
            "alerts",
            "containment alarms publish through an AlertPublisher-shaped sink",
            given=repr(type(value).__name__),
        )
    return Ok(cast("_AlertSink", value))


def _as_slice_watch(value: object) -> Result[_SliceWatch]:
    if value is None:
        return invalid(
            "supervisor",
            "non-returning last-resort uses the door-layer slice-progress watch",
        )
    evaluate = getattr(value, "evaluate_slice_progress", None)
    publish_start = getattr(value, "publish_slice_start", None)
    if not callable(evaluate) or not callable(publish_start):
        return invalid(
            "supervisor",
            "slice-progress watch exposes evaluate_slice_progress and publish_slice_start",
            given=repr(type(value).__name__),
        )
    return Ok(cast("_SliceWatch", value))


def _gap_0054_row(text: str) -> str | None:
    for raw in text.splitlines():
        stripped = raw.lstrip()
        if stripped.startswith("| **GAP-0054**") or stripped.startswith("| GAP-0054"):
            return raw
    return None


def _seats_src_root() -> Path:
    """``qmn/src/qmn`` — scan the node package, not only this module."""
    return Path(__file__).resolve().parents[1]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]
