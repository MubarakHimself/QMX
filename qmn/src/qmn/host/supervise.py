"""Supervisor lifecycle: safe points, stand-down-alive, watchdog, shutdown (TN-4).

Story 25.6 / FR-053 / DEC-0189 / DEC-0226. The supervisor/door layer owns the
stdlib raw ``sd_notify`` wire protocol, the watchdog keepalive, and the
slice-progress watch. Domain work stays on the single asyncio loop's thread;
async is only at the venue edge and the doors. Unit tests inject notify and
time doubles — no real systemd host is required.
"""

from __future__ import annotations

import os
import socket
from collections.abc import Mapping, MutableSequence, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Literal, Protocol, cast

from qmf.core.refusal import Ok, Result, is_refusal

from qmn.host._refuse import clean_token, invalid, policy

__all__ = [
    "ASYNC_ALLOWED_SURFACES",
    "CLEAN_STOP_EXIT_CODE",
    "DOMAIN_BACKGROUND_THREADS_ALLOWED",
    "DRAIN_WINDOW_BREACH_EXIT_CODE",
    "EVENT_LOOP_COUNT",
    "NODE_RESURRECT_SUBTYPE",
    "OPERATOR_PRINCIPAL",
    "REQUESTED_RESTART_EXIT_CODE",
    "REQUESTED_RESTART_REASON",
    "SILENT_DEGRADATION_ALARM_CLASS",
    "SUPERVISION_SURFACE",
    "SUSPEND_NEW_AUTHORITY",
    "UNKNOWN_SHUTDOWN_TRIGGER",
    "BootAttemptStamp",
    "CommandFate",
    "CrashLoopFold",
    "CrashLoopVerdict",
    "DrainOutcome",
    "LifecycleState",
    "LifecycleSupervisor",
    "NotifyTransport",
    "RecordingNotifyTransport",
    "ResurrectReceipt",
    "SafePointSnapshot",
    "ShutdownKind",
    "SliceProgressTrip",
    "StandDownTrigger",
    "StdlibSdNotifyTransport",
    "SupervisionConfig",
    "admit_under_lifecycle",
    "evaluate_safe_point",
    "notify_ready",
    "notify_watchdog",
    "notify_watchdog_trigger",
    "sd_notify",
    "supervision_process_model",
]

SUPERVISION_SURFACE: Final[str] = "qmn.host"
EVENT_LOOP_COUNT: Final[int] = 1
ASYNC_ALLOWED_SURFACES: Final[tuple[str, ...]] = ("venue_edge", "doors")
DOMAIN_BACKGROUND_THREADS_ALLOWED: Final[bool] = False

REQUESTED_RESTART_EXIT_CODE: Final[int] = 75
CLEAN_STOP_EXIT_CODE: Final[int] = 0
DRAIN_WINDOW_BREACH_EXIT_CODE: Final[int] = 76
REQUESTED_RESTART_REASON: Final[str] = "requested-restart"

OPERATOR_PRINCIPAL: Final[str] = "operator"
NODE_RESURRECT_SUBTYPE: Final[str] = "node_resurrect"
SUSPEND_NEW_AUTHORITY: Final[str] = "adapter_self"
UNKNOWN_SHUTDOWN_TRIGGER: Final[str] = "disconnect"
SILENT_DEGRADATION_ALARM_CLASS: Final[str] = "silent-degradation"

# Entry-side intents refused in stand-down / under suspend_new (L39 / DEC-0189).
_ENTRY_KINDS: Final[frozenset[str]] = frozenset(
    {"place_order", "risk_increasing_amend_protection"}
)
_RISK_NON_INCREASING_KINDS: Final[frozenset[str]] = frozenset(
    {
        "cancel_order",
        "close_position",
        "close_all",
        "risk_non_increasing_amend_protection",
        "flatten",
        "standing_protection_intent",
    }
)


class LifecycleState(StrEnum):
    """Alive process lifecycle — stand-down is alive, not a CT-30 action."""

    RUNNING = "running"
    STAND_DOWN_ALIVE = "stand-down-alive"
    DRAINING = "draining"
    STOPPED = "stopped"


class StandDownTrigger(StrEnum):
    """Automatic stand-down causes (DEC-0189). Restart alone never clears them."""

    CRASH_LOOP = "crash-loop"
    PREFLIGHT_REFUSAL = "preflight-refusal"
    CLOCK_HALT = "clock-halt"


class ShutdownKind(StrEnum):
    """Drain origin — exit code differs; neither flattens."""

    SIGTERM = "sigterm"
    REQUESTED_RESTART = "requested-restart"


class CommandFate(StrEnum):
    """Per-command drain fate at a safe point."""

    TERMINAL = "terminal"
    UNKNOWN_MINTED = "unknown-minted"
    UNRESOLVED = "unresolved"


class NotifyTransport(Protocol):
    """Injectable sd_notify sink — production uses the stdlib AF_UNIX datagram."""

    def send(self, state: str, /) -> Result[None]:
        """Deliver one systemd notify state string (``KEY=value`` lines)."""
        ...


@dataclass
class RecordingNotifyTransport:
    """Test double that records notify payloads without touching a socket."""

    messages: MutableSequence[str] = field(default_factory=list[str])
    fail_next: bool = False

    def send(self, state: str, /) -> Result[None]:
        token = clean_token(state)
        if token is None:
            return invalid("state", "sd_notify state is a non-blank string")
        if self.fail_next:
            self.fail_next = False
            return policy("sd_notify", "injected notify transport failure")
        self.messages.append(token)
        return Ok(None)


@dataclass(frozen=True, slots=True)
class StdlibSdNotifyTransport:
    """Raw sd_notify over ``AF_UNIX`` ``SOCK_DGRAM`` (DEC-0189).

    Handles unset ``NOTIFY_SOCKET`` (no-op success), abstract sockets (leading
    ``@`` or NUL), and path sockets. Never depends on ``python-systemd`` /
    ``sdnotify``.
    """

    env_name: str = "NOTIFY_SOCKET"

    def send(self, state: str, /) -> Result[None]:
        token = clean_token(state)
        if token is None:
            return invalid("state", "sd_notify state is a non-blank string")
        notify_socket = os.environ.get(self.env_name)
        if notify_socket is None or notify_socket == "":
            return Ok(None)
        # AF_UNIX is Linux/VPS-native; getattr keeps Windows type-checkers honest.
        af_unix = getattr(socket, "AF_UNIX", None)
        if af_unix is None:
            return policy(
                "sd_notify",
                "AF_UNIX datagram notify unavailable on this platform",
            )
        address = _notify_address(notify_socket)
        try:
            with socket.socket(af_unix, socket.SOCK_DGRAM) as sock:
                sock.connect(address)
                sock.sendall(token.encode("utf-8"))
        except OSError as exc:
            return policy(
                "sd_notify",
                "AF_UNIX datagram notify send failed",
                errno=getattr(exc, "errno", None),
                detail=str(exc),
            )
        return Ok(None)


def _notify_address(notify_socket: str) -> str | bytes:
    """Map NOTIFY_SOCKET forms to a connectable AF_UNIX address."""
    if notify_socket.startswith("@"):
        # Abstract namespace: leading NUL + name without the '@'.
        return ("\0" + notify_socket[1:]).encode("utf-8")
    if notify_socket.startswith("\0"):
        return notify_socket.encode("utf-8")
    return notify_socket


def sd_notify(
    state: object,
    *,
    transport: NotifyTransport | None = None,
) -> Result[None]:
    """Send one raw sd_notify state string through the injected transport."""
    token = clean_token(state)
    if token is None:
        return invalid("state", "sd_notify state is a non-blank string")
    sink: NotifyTransport = transport if transport is not None else StdlibSdNotifyTransport()
    return sink.send(token)


def notify_ready(*, transport: NotifyTransport | None = None) -> Result[None]:
    """``READY=1`` — owned by the supervisor/door layer after readiness."""
    return sd_notify("READY=1", transport=transport)


def notify_watchdog(*, transport: NotifyTransport | None = None) -> Result[None]:
    """``WATCHDOG=1`` keepalive — continues through stand-down while enabled."""
    return sd_notify("WATCHDOG=1", transport=transport)


def notify_watchdog_trigger(*, transport: NotifyTransport | None = None) -> Result[None]:
    """``WATCHDOG=trigger`` — slice-progress watch stops the keepalive (TN-19)."""
    return sd_notify("WATCHDOG=trigger", transport=transport)


def supervision_process_model() -> Mapping[str, object]:
    """Declared process model constants (FR-053; TN-4) — no ambient probing."""
    return MappingProxyType(
        {
            "event_loop_count": EVENT_LOOP_COUNT,
            "async_allowed_surfaces": ASYNC_ALLOWED_SURFACES,
            "domain_background_threads_allowed": DOMAIN_BACKGROUND_THREADS_ALLOWED,
            "sd_notify_owner": "supervisor_door_layer",
            "watchdog_owner": "supervisor_door_layer",
            "slice_progress_watch_owner": "supervisor_door_layer",
            "requested_restart_exit_code": REQUESTED_RESTART_EXIT_CODE,
            "clean_stop_exit_code": CLEAN_STOP_EXIT_CODE,
            "drain_window_breach_exit_code": DRAIN_WINDOW_BREACH_EXIT_CODE,
        }
    )


@dataclass(frozen=True, slots=True)
class SupervisionConfig:
    """Injectable supervision bounds (registry evidence values in tests)."""

    crash_loop_max_boots: int
    crash_loop_window_ns: int
    drain_window_ns: int
    watchdog_interval_ns: int
    seat_callback_deadline_ns: int
    slice_watch_trip_multiple: int

    @classmethod
    def try_create(
        cls,
        *,
        crash_loop_max_boots: object,
        crash_loop_window_ns: object,
        drain_window_ns: object,
        watchdog_interval_ns: object,
        seat_callback_deadline_ns: object,
        slice_watch_trip_multiple: object,
    ) -> Result[SupervisionConfig]:
        """Validate positive bounds; blanks refuse (blocks-boot)."""
        k = _positive_int("node_crash_loop_max_boots", crash_loop_max_boots)
        if is_refusal(k):
            return k
        t = _positive_int("node_crash_loop_window", crash_loop_window_ns)
        if is_refusal(t):
            return t
        drain = _positive_int("drain_window", drain_window_ns)
        if is_refusal(drain):
            return drain
        wd = _positive_int("watchdog_interval", watchdog_interval_ns)
        if is_refusal(wd):
            return wd
        deadline = _positive_int("seat_callback_deadline", seat_callback_deadline_ns)
        if is_refusal(deadline):
            return deadline
        multiple = _positive_int("slice_watch_trip_multiple", slice_watch_trip_multiple)
        if is_refusal(multiple):
            return multiple
        return Ok(
            cls(
                crash_loop_max_boots=k.value,
                crash_loop_window_ns=t.value,
                drain_window_ns=drain.value,
                watchdog_interval_ns=wd.value,
                seat_callback_deadline_ns=deadline.value,
                slice_watch_trip_multiple=multiple.value,
            )
        )


def _positive_int(field: str, value: object) -> Result[int]:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return invalid(
            field,
            f"{field} is a positive int (blank blocks-boot)",
            given=repr(value),
        )
    return Ok(value)


@dataclass(frozen=True, slots=True)
class BootAttemptStamp:
    """Minimal boot-attempt projection the crash-loop fold reads."""

    boot_epoch_id: str
    at_ns: int
    reason: str | None
    exited: bool


@dataclass(frozen=True, slots=True)
class CrashLoopVerdict:
    """Outcome of folding unrequested exiting boots within the window."""

    counted_boots: int
    threshold_breached: bool
    counted_epoch_ids: tuple[str, ...]


@dataclass
class CrashLoopFold:
    """Counts unrequested exiting boots within ``(K, T)`` (DEC-0189 / DEC-0226).

    Requested-restart stamps never advance the fold. Detected preflight refusals
    that stay alive (no exit) also never advance it. Counters are durable: a
    process restart reloads stamps via :meth:`load` and never clears the fold by
    itself. Only an operator ``resurrect`` (or an explicit :meth:`reset_for_operator_cycle`)
    resets the fold so an unrequested crash cannot masquerade as a clean operator
    cycle (TN-4; QMX-F064 / Story 25.13).
    """

    max_boots: int
    window_ns: int
    _stamps: MutableSequence[BootAttemptStamp] = field(
        default_factory=list[BootAttemptStamp]
    )

    @classmethod
    def load(
        cls,
        *,
        max_boots: object,
        window_ns: object,
        stamps: object,
    ) -> Result[CrashLoopFold]:
        """Rebuild the fold from durable boot-attempt stamps (process-restart safe)."""
        k = _positive_int("node_crash_loop_max_boots", max_boots)
        if is_refusal(k):
            return k
        t = _positive_int("node_crash_loop_window", window_ns)
        if is_refusal(t):
            return t
        if not isinstance(stamps, Sequence) or isinstance(stamps, (str, bytes)):
            return invalid(
                "stamps",
                "crash-loop fold loads a sequence of BootAttemptStamp projections",
                given=type(stamps).__name__,
            )
        loaded: list[BootAttemptStamp] = []
        for index, raw in enumerate(cast("Sequence[object]", stamps)):
            if not isinstance(raw, BootAttemptStamp):
                return invalid(
                    "stamps",
                    "each durable stamp is a BootAttemptStamp",
                    index=index,
                    given=type(raw).__name__,
                )
            loaded.append(raw)
        return Ok(cls(max_boots=k.value, window_ns=t.value, _stamps=loaded))

    def record(self, stamp: object) -> Result[CrashLoopVerdict]:
        if not isinstance(stamp, BootAttemptStamp):
            return invalid(
                "stamp",
                "crash-loop fold reads BootAttemptStamp projections",
                given=type(stamp).__name__,
            )
        self._stamps.append(stamp)
        return Ok(self.evaluate(now_ns=stamp.at_ns))

    def reset_for_operator_cycle(self) -> None:
        """Clear counted stamps after an operator resurrect / new clean boot epoch.

        A mere process restart must call :meth:`load` instead — it never resets.
        """
        self._stamps.clear()

    @property
    def stamps(self) -> tuple[BootAttemptStamp, ...]:
        """Durable stamp projection — process restart reloads these, never drops them."""
        return tuple(self._stamps)

    def evaluate(self, *, now_ns: object) -> CrashLoopVerdict:
        if not isinstance(now_ns, int) or isinstance(now_ns, bool):
            return CrashLoopVerdict(
                counted_boots=0, threshold_breached=False, counted_epoch_ids=()
            )
        window_start = now_ns - self.window_ns
        counted: list[str] = []
        for stamp in self._stamps:
            if stamp.at_ns < window_start:
                continue
            if not stamp.exited:
                continue
            if stamp.reason == REQUESTED_RESTART_REASON:
                continue
            counted.append(stamp.boot_epoch_id)
        return CrashLoopVerdict(
            counted_boots=len(counted),
            threshold_breached=len(counted) >= self.max_boots,
            counted_epoch_ids=tuple(counted),
        )


@dataclass(frozen=True, slots=True)
class SafePointSnapshot:
    """Safe-point predicates — positions are never a wait condition (DEC-0189)."""

    between_slices: bool
    suspend_new_enforced: bool
    command_fates: Mapping[str, CommandFate]
    sinks_flushed: bool
    positions_flat: bool | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "command_fates", MappingProxyType(dict(self.command_fates))
        )

    @property
    def unresolved_command_ids(self) -> tuple[str, ...]:
        return tuple(
            command_id
            for command_id, fate in self.command_fates.items()
            if fate is CommandFate.UNRESOLVED
        )

    @property
    def is_safe_point(self) -> bool:
        """True when between slices, suspend_new held, commands settled, sinks flushed."""
        return (
            self.between_slices
            and self.suspend_new_enforced
            and not self.unresolved_command_ids
            and self.sinks_flushed
        )


def evaluate_safe_point(snapshot: object) -> Result[SafePointSnapshot]:
    """Validate and return a safe-point snapshot; never requires positions flat."""
    if not isinstance(snapshot, SafePointSnapshot):
        return invalid(
            "snapshot",
            "safe point is evaluated from a SafePointSnapshot",
            given=type(snapshot).__name__,
        )
    return Ok(snapshot)


@dataclass(frozen=True, slots=True)
class ResurrectReceipt:
    """Operator-only exit from stand-down — journals ``node_resurrect`` (DEC-0249)."""

    principal: str
    scope: str
    prior_boot_epoch_id: str
    new_boot_epoch_id: str
    subtype: str
    journals_ct30: bool
    clears_by_restart: bool


@dataclass(frozen=True, slots=True)
class SliceProgressTrip:
    """Door-layer slice-progress watch trip (TN-19 / DEC-0204)."""

    elapsed_ns: int
    trip_threshold_ns: int
    alarm_class: str
    keepalive_stopped: bool
    notify_state: str


@dataclass(frozen=True, slots=True)
class DrainOutcome:
    """Result of draining to a safe point (or breaching the drain window)."""

    kind: ShutdownKind
    reached_safe_point: bool
    exit_code: int
    suspend_new_enforced: bool
    sessions_closed: bool
    unknown_minted_command_ids: tuple[str, ...]
    sinks_flushed: bool
    flattened: bool
    waited_for_flat: bool
    lifecycle_stop_minted: bool


def admit_under_lifecycle(
    *,
    state: object,
    kind: object,
    risk_increasing: object = False,
) -> Result[Literal["admit", "refuse-entry", "hold-standing-intent"]]:
    """Entry-side-only admission under the current lifecycle state (DEC-0189)."""
    if not isinstance(state, LifecycleState):
        return invalid(
            "state",
            "lifecycle admission requires a LifecycleState",
            given=repr(state),
        )
    kind_token = clean_token(kind)
    if kind_token is None:
        return invalid("kind", "intent kind is a non-blank string")
    if not isinstance(risk_increasing, bool):
        return invalid(
            "risk_increasing",
            "risk_increasing is a boolean",
            given=repr(risk_increasing),
        )
    if state is LifecycleState.STOPPED:
        return policy("lifecycle", "stopped process admits no intents")
    if state is LifecycleState.DRAINING:
        if kind_token in _ENTRY_KINDS or risk_increasing:
            return Ok("refuse-entry")
        if kind_token in _RISK_NON_INCREASING_KINDS or not risk_increasing:
            return Ok("admit")
        return Ok("refuse-entry")
    if state is LifecycleState.STAND_DOWN_ALIVE:
        if kind_token in _ENTRY_KINDS or risk_increasing:
            return Ok("refuse-entry")
        # Risk-non-increasing acts remain enactable; if sessions quiesced the
        # caller may hold them as standing intents — never refuse them.
        return Ok("admit")
    # RUNNING
    if kind_token in _ENTRY_KINDS or risk_increasing:
        return Ok("admit")
    return Ok("admit")


@dataclass
class LifecycleSupervisor:
    """Supervisor/door-layer owner of watchdog, stand-down, safe-point, shutdown.

    Async domain work never moves onto an undeclared background thread; the
    keepalive continues through stand-down until a slice-progress trip stops it.
    """

    config: SupervisionConfig
    notify: NotifyTransport
    boot_epoch_id: str
    state: LifecycleState = LifecycleState.RUNNING
    stand_down_trigger: StandDownTrigger | None = None
    doors_serving: bool = True
    suspend_new_enforced: bool = False
    between_slices: bool = True
    sinks_flushed: bool = True
    sessions_closed: bool = False
    keepalive_enabled: bool = True
    slice_start_mono_ns: int | None = None
    command_fates: dict[str, CommandFate] = field(default_factory=dict[str, CommandFate])
    crash_loop: CrashLoopFold | None = None
    resurrect_receipts: MutableSequence[ResurrectReceipt] = field(
        default_factory=list[ResurrectReceipt]
    )
    journal_events: MutableSequence[Mapping[str, object]] = field(
        default_factory=list[Mapping[str, object]]
    )
    alarms: MutableSequence[str] = field(default_factory=list[str])
    drain_started_mono_ns: int | None = None
    shutdown_kind: ShutdownKind | None = None

    def __post_init__(self) -> None:
        if self.crash_loop is None:
            self.crash_loop = CrashLoopFold(
                max_boots=self.config.crash_loop_max_boots,
                window_ns=self.config.crash_loop_window_ns,
            )

    def mark_ready(self) -> Result[None]:
        """Announce readiness via ``READY=1`` once the process model is live."""
        if self.state is LifecycleState.STOPPED:
            return policy("lifecycle", "stopped process cannot announce READY")
        return notify_ready(transport=self.notify)

    def tick_watchdog(self) -> Result[None]:
        """Emit ``WATCHDOG=1`` when keepalive is enabled (including stand-down)."""
        if not self.keepalive_enabled:
            return policy(
                "watchdog",
                "keepalive stopped; slice-progress watch or shutdown disabled it",
            )
        if self.state is LifecycleState.STOPPED:
            return policy("watchdog", "stopped process does not keepalive")
        return notify_watchdog(transport=self.notify)

    def publish_slice_start(self, *, mono_ns: object) -> Result[None]:
        """Driver publishes the monotonic slice-start stamp for the progress watch."""
        if not isinstance(mono_ns, int) or isinstance(mono_ns, bool) or mono_ns < 0:
            return invalid(
                "mono_ns",
                "slice-start stamp is a non-negative monotonic nanosecond int",
                given=repr(mono_ns),
            )
        if self.state is LifecycleState.STOPPED:
            return policy("slice_start", "stopped process publishes no slice-start")
        self.between_slices = False
        self.slice_start_mono_ns = mono_ns
        return Ok(None)

    def clear_slice_start(self) -> None:
        """Slice completed — between-slices again."""
        self.slice_start_mono_ns = None
        self.between_slices = True

    def evaluate_slice_progress(self, *, now_mono_ns: object) -> Result[SliceProgressTrip | None]:
        """Trip when elapsed exceeds deadline × trip multiple; stop keepalive."""
        if not isinstance(now_mono_ns, int) or isinstance(now_mono_ns, bool):
            return invalid(
                "now_mono_ns",
                "slice-progress watch reads a monotonic nanosecond int",
                given=repr(now_mono_ns),
            )
        if self.slice_start_mono_ns is None:
            return Ok(None)
        elapsed = now_mono_ns - self.slice_start_mono_ns
        threshold = (
            self.config.seat_callback_deadline_ns * self.config.slice_watch_trip_multiple
        )
        if elapsed <= threshold:
            return Ok(None)
        triggered = notify_watchdog_trigger(transport=self.notify)
        if is_refusal(triggered):
            return triggered
        self.keepalive_enabled = False
        self.alarms.append(SILENT_DEGRADATION_ALARM_CLASS)
        trip = SliceProgressTrip(
            elapsed_ns=elapsed,
            trip_threshold_ns=threshold,
            alarm_class=SILENT_DEGRADATION_ALARM_CLASS,
            keepalive_stopped=True,
            notify_state="WATCHDOG=trigger",
        )
        return Ok(trip)

    def enter_stand_down(self, *, trigger: object) -> Result[LifecycleState]:
        """Enter stand-down-alive; doors keep serving; restart alone never clears."""
        if not isinstance(trigger, StandDownTrigger):
            return invalid(
                "trigger",
                "stand-down trigger is crash-loop | preflight-refusal | clock-halt",
                given=repr(trigger),
            )
        if self.state is LifecycleState.STOPPED:
            return policy("stand_down", "stopped process cannot enter stand-down-alive")
        if self.state is LifecycleState.DRAINING:
            return policy("stand_down", "draining process finishes the drain contract first")
        self.state = LifecycleState.STAND_DOWN_ALIVE
        self.stand_down_trigger = trigger
        self.doors_serving = True
        self.journal_events.append(
            MappingProxyType(
                {
                    "event_type": "control action",
                    "kind": "node-stand-down",
                    "trigger": trigger.value,
                    "boot_epoch_id": self.boot_epoch_id,
                    "doors_serving": True,
                }
            )
        )
        return Ok(self.state)

    def record_boot_attempt(
        self,
        *,
        boot_epoch_id: object,
        at_ns: object,
        reason: object = None,
        exited: object = True,
    ) -> Result[CrashLoopVerdict]:
        """Feed the crash-loop fold; auto-enter stand-down when ``(K, T)`` breaches."""
        epoch = clean_token(boot_epoch_id)
        if epoch is None:
            return invalid("boot_epoch_id", "boot epoch id is a non-blank string")
        if not isinstance(at_ns, int) or isinstance(at_ns, bool) or at_ns < 0:
            return invalid(
                "at_ns",
                "boot attempt stamp is a non-negative nanosecond int",
                given=repr(at_ns),
            )
        if not isinstance(exited, bool):
            return invalid("exited", "exited is a boolean", given=repr(exited))
        reason_token: str | None
        if reason is None:
            reason_token = None
        else:
            reason_token = clean_token(reason)
            if reason_token is None:
                return invalid("reason", "boot reason is None or a non-blank string")
        fold = self.crash_loop
        if fold is None:
            fold = CrashLoopFold(
                max_boots=self.config.crash_loop_max_boots,
                window_ns=self.config.crash_loop_window_ns,
            )
            self.crash_loop = fold
        verdict = fold.record(
            BootAttemptStamp(
                boot_epoch_id=epoch,
                at_ns=at_ns,
                reason=reason_token,
                exited=exited,
            )
        )
        if is_refusal(verdict):
            return verdict
        if verdict.value.threshold_breached and self.state is LifecycleState.RUNNING:
            stood = self.enter_stand_down(trigger=StandDownTrigger.CRASH_LOOP)
            if is_refusal(stood):
                return stood
        return verdict

    def resurrect(
        self,
        *,
        principal: object,
        scope: object,
        new_boot_epoch_id: object,
    ) -> Result[ResurrectReceipt]:
        """Operator-principal ``resurrect`` — the only exit from stand-down."""
        principal_token = clean_token(principal)
        if principal_token is None:
            return invalid("principal", "resurrect names a non-blank principal")
        if principal_token != OPERATOR_PRINCIPAL:
            return policy(
                "principal",
                "only the operator principal may resurrect from node stand-down",
                given=principal_token,
            )
        scope_token = clean_token(scope)
        if scope_token is None:
            return invalid("scope", "resurrect names the scope it reopens")
        new_epoch = clean_token(new_boot_epoch_id)
        if new_epoch is None:
            return invalid("new_boot_epoch_id", "resurrect opens a new lifecycle epoch")
        if self.state is not LifecycleState.STAND_DOWN_ALIVE:
            return policy(
                "lifecycle",
                "resurrect applies only while stand-down-alive",
                state=self.state.value,
            )
        if new_epoch == self.boot_epoch_id:
            return policy(
                "new_boot_epoch_id",
                "resurrect opens a new lifecycle epoch; it never reuses the stood-down epoch",
            )
        receipt = ResurrectReceipt(
            principal=principal_token,
            scope=scope_token,
            prior_boot_epoch_id=self.boot_epoch_id,
            new_boot_epoch_id=new_epoch,
            subtype=NODE_RESURRECT_SUBTYPE,
            journals_ct30=False,
            clears_by_restart=False,
        )
        self.journal_events.append(
            MappingProxyType(
                {
                    "event_type": "control action",
                    "kind": NODE_RESURRECT_SUBTYPE,
                    "scope": scope_token,
                    "principal": principal_token,
                    "prior_boot_epoch_id": self.boot_epoch_id,
                    "new_boot_epoch_id": new_epoch,
                    "journals_ct30": False,
                }
            )
        )
        self.resurrect_receipts.append(receipt)
        self.boot_epoch_id = new_epoch
        self.state = LifecycleState.RUNNING
        self.stand_down_trigger = None
        self.doors_serving = True
        # Operator resurrect is a clean cycle — reset the crash-loop fold so a
        # prior unrequested crash cannot masquerade as the new operator epoch.
        fold = self.crash_loop
        if fold is not None:
            fold.reset_for_operator_cycle()
        return Ok(receipt)

    def set_command_fate(self, command_id: object, fate: object) -> Result[None]:
        """Update one command's drain fate (terminal | unknown-minted | unresolved)."""
        cid = clean_token(command_id)
        if cid is None:
            return invalid("command_id", "command identity is a non-blank string")
        if not isinstance(fate, CommandFate):
            return invalid(
                "fate",
                "command fate is terminal | unknown-minted | unresolved",
                given=repr(fate),
            )
        self.command_fates[cid] = fate
        return Ok(None)

    def safe_point_snapshot(self) -> SafePointSnapshot:
        """Current safe-point projection — positions_flat is informational only."""
        return SafePointSnapshot(
            between_slices=self.between_slices,
            suspend_new_enforced=self.suspend_new_enforced,
            command_fates=dict(self.command_fates),
            sinks_flushed=self.sinks_flushed,
            positions_flat=None,
        )

    def begin_drain(
        self,
        *,
        kind: object,
        now_mono_ns: object,
    ) -> Result[LifecycleState]:
        """Start drain: enforce suspend_new; never flatten; never wait for flat."""
        if not isinstance(kind, ShutdownKind):
            return invalid(
                "kind",
                "shutdown kind is sigterm | requested-restart",
                given=repr(kind),
            )
        if not isinstance(now_mono_ns, int) or isinstance(now_mono_ns, bool):
            return invalid(
                "now_mono_ns",
                "drain start stamp is a monotonic nanosecond int",
                given=repr(now_mono_ns),
            )
        if self.state is LifecycleState.STOPPED:
            return policy("drain", "stopped process cannot begin drain")
        self.state = LifecycleState.DRAINING
        self.shutdown_kind = kind
        self.suspend_new_enforced = True
        self.drain_started_mono_ns = now_mono_ns
        self.journal_events.append(
            MappingProxyType(
                {
                    "event_type": "control action",
                    "kind": "lifecycle-stop",
                    "authority": SUSPEND_NEW_AUTHORITY,
                    "effect": "suspend_new",
                    "shutdown_kind": kind.value,
                    "boot_epoch_id": self.boot_epoch_id,
                    "flattened": False,
                }
            )
        )
        return Ok(self.state)

    def complete_drain(
        self,
        *,
        now_mono_ns: object,
        unresolved_command_ids: Sequence[object] | None = None,
        flush_ok: object = True,
    ) -> Result[DrainOutcome]:
        """Close sessions, mint UNKNOWN for unresolved, flush; exit 0 / 75 / 76.

        Positions are never waited on. Failure to flush refuses a clean exit and
        alarms silent-degradation while staying up.
        """
        if self.state is not LifecycleState.DRAINING or self.shutdown_kind is None:
            return policy("drain", "complete_drain requires an in-flight drain")
        if not isinstance(now_mono_ns, int) or isinstance(now_mono_ns, bool):
            return invalid(
                "now_mono_ns",
                "drain completion stamp is a monotonic nanosecond int",
                given=repr(now_mono_ns),
            )
        if not isinstance(flush_ok, bool):
            return invalid("flush_ok", "flush_ok is a boolean", given=repr(flush_ok))
        started = self.drain_started_mono_ns
        if started is None:
            return policy("drain", "drain start stamp missing; begin_drain first")
        elapsed = now_mono_ns - started
        window_breached = elapsed > self.config.drain_window_ns

        # Close sessions with no resubmission, then mint UNKNOWN under disconnect.
        self.sessions_closed = True
        minted: list[str] = []
        pending = (
            tuple(self.command_fates)
            if unresolved_command_ids is None
            else unresolved_command_ids
        )
        for raw_id in pending:
            cid = clean_token(raw_id)
            if cid is None:
                return invalid(
                    "unresolved_command_ids",
                    "each command identity is a non-blank string",
                )
            fate = self.command_fates.get(cid, CommandFate.UNRESOLVED)
            if fate is CommandFate.UNRESOLVED:
                self.command_fates[cid] = CommandFate.UNKNOWN_MINTED
                minted.append(cid)
                self.journal_events.append(
                    MappingProxyType(
                        {
                            "event_type": "execution",
                            "kind": "UNKNOWN",
                            "command_id": cid,
                            "trigger": UNKNOWN_SHUTDOWN_TRIGGER,
                            "boot_epoch_id": self.boot_epoch_id,
                        }
                    )
                )

        if not flush_ok:
            self.sinks_flushed = False
            self.alarms.append(SILENT_DEGRADATION_ALARM_CLASS)
            self.keepalive_enabled = True
            return policy(
                "flush",
                "flush cannot complete; node stays up, alarms silent-degradation, "
                "refuses clean exit",
                flattened=False,
                waited_for_flat=False,
            )

        self.sinks_flushed = True
        self.between_slices = True
        snapshot = self.safe_point_snapshot()
        reached = snapshot.is_safe_point and not window_breached
        if window_breached:
            exit_code = DRAIN_WINDOW_BREACH_EXIT_CODE
            reached = False
        elif self.shutdown_kind is ShutdownKind.REQUESTED_RESTART:
            exit_code = REQUESTED_RESTART_EXIT_CODE
        else:
            exit_code = CLEAN_STOP_EXIT_CODE

        self.state = LifecycleState.STOPPED
        self.keepalive_enabled = False
        outcome = DrainOutcome(
            kind=self.shutdown_kind,
            reached_safe_point=reached,
            exit_code=exit_code,
            suspend_new_enforced=True,
            sessions_closed=True,
            unknown_minted_command_ids=tuple(minted),
            sinks_flushed=True,
            flattened=False,
            waited_for_flat=False,
            lifecycle_stop_minted=True,
        )
        return Ok(outcome)
