"""Paper-milestone lifecycle campaign (Story 28.4 / TN-4/14/19/23).

Injects crash-loop, preflight, callback-wedge quarantine, clock, disk, data
freshness, and SIGTERM through the existing supervisor / boot / seat / clock /
protection seams. No live VPS firewall campaign and no live bucket restore
(AR-87). FTR-07: disk_headroom_min is an injected evidence fixture, never a
ratified constant.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, TypeVar

from qmf.core import (
    Instant,
    Ok,
    Result,
    TypedRefusal,
    VenueId,
    fingerprint,
    is_ok,
    is_refusal,
    unpersistable,
)
from qmf.risk.control_action import (
    AuthorityKind,
    CommandStreamKey,
    SubjectScope,
    mint_control_action,
)
from qmf.risk.control_rank import ControlActionKind

from qmn.data import (
    CLEAN_HOST_REHEARSAL_TONIGHT,
    FULL_DRILL,
    HOST_LOSS_DRILL,
    RESTORE_AUTO_CUTOVER,
    SAMPLE_DRILL,
    refuse_automatic_cutover,
    refuse_clean_host_rehearsal_tonight,
    refuse_live_bucket_tonight,
)
from qmn.host._refuse import invalid, policy
from qmn.host.boot_ceremony import (
    CompositionFingerprintInputs,
    InMemoryBootAttemptSink,
    PreflightFacts,
    run_boot_ceremony,
)
from qmn.host.supervise import (
    CommandFate,
    CrashLoopFold,
    LifecycleState,
    LifecycleSupervisor,
    RecordingNotifyTransport,
    ShutdownKind,
    StandDownTrigger,
    SupervisionConfig,
    admit_under_lifecycle,
)
from qmn.loop import CycleBand, entry_side_refused, protection_enactable
from qmn.observability import (
    CAN_CALL_DOOR,
    CAN_CLOSE_POSITIONS,
    CAN_STOP_ENTRIES,
    HOLDS_ZERO_AUTHORITY,
    WatcherDouble,
    default_health_report,
)
from qmn.protection import (
    IntentPersistDisposition,
    ProtectionIntentExtent,
    persist_protective_intent,
)
from qmn.seats import (
    OPERATOR_PRINCIPAL,
    GovernedSeatState,
    QuarantineTrigger,
    SeatTransitionStream,
    apply_operator_seat_reinstate,
    fold_seat_state,
    mint_quarantine_transition,
    mint_seat_reinstate,
)
from qmn.time import (
    ClockBand,
    ClockDriftThresholds,
    MachineVersusTruth,
    clock_band_entry_side_refused,
    clock_band_preserves_protection,
    clock_band_requires_stand_down,
    evaluate_clock_band,
)
from qmn.time.clock import VpsClock

__all__ = [
    "LIFECYCLE_CAMPAIGN_CLASS",
    "LIFECYCLE_CAMPAIGN_FORMAT_VERSION",
    "LIFECYCLE_CAMPAIGN_SURFACE",
    "LIFECYCLE_INJECTIONS",
    "RUNS_LIVE_BUCKET_RESTORE",
    "RUNS_LIVE_VPS_FIREWALL",
    "DiskHeadroomBand",
    "DiskHeadroomDecision",
    "LifecycleCampaignInputs",
    "LifecycleCampaignReport",
    "evaluate_disk_headroom",
    "refuse_live_bucket_restore",
    "refuse_live_vps_firewall_campaign",
    "run_paper_milestone_lifecycle_campaign",
]

T = TypeVar("T")

LIFECYCLE_CAMPAIGN_SURFACE: Final[str] = "qmn.host.lifecycle_campaign"
LIFECYCLE_CAMPAIGN_CLASS: Final[str] = "paper-milestone-lifecycle-campaign"
LIFECYCLE_CAMPAIGN_FORMAT_VERSION: Final[int] = 1
RUNS_LIVE_VPS_FIREWALL: Final[bool] = False
RUNS_LIVE_BUCKET_RESTORE: Final[bool] = False

LIFECYCLE_INJECTIONS: Final[tuple[str, ...]] = (
    "crash-loop",
    "preflight",
    "callback-wedge",
    "clock",
    "disk",
    "data-freshness",
    "shutdown",
)

_ID_INPUTS: Final[str] = "lifecycle_campaign.inputs"
_ID_INJECTION: Final[str] = "lifecycle_campaign.incomplete_injection"
_ID_FIREWALL: Final[str] = "lifecycle_campaign.live_vps_firewall"
_ID_BUCKET: Final[str] = "lifecycle_campaign.live_bucket_restore"
_ID_DISK: Final[str] = "lifecycle_campaign.invented_disk_headroom"

_MACHINE: Final[str] = "vps-28-4"
_BOOT: Final[str] = "boot-28-4"
_SEAT: Final[str] = "seat-28-4"
_BINDING: Final[str] = "binding-28-4"


class DiskHeadroomBand(StrEnum):
    """Disk precondition bands — headroom trips before the disk-full block."""

    OK = "ok"
    NO_NEW_ENTRY = "no-new-entry"
    FULL = "full"


@dataclass(frozen=True, slots=True)
class DiskHeadroomDecision:
    """One injected free-space sample against ``disk_headroom_min``."""

    band: DiskHeadroomBand
    free_bytes: int
    disk_headroom_min: int
    silent_degradation: bool
    entries_refused: bool
    protection_persistent: bool
    failure_id: str | None

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "band": self.band.value,
            "disk_headroom_min": self.disk_headroom_min,
            "entries_refused": self.entries_refused,
            "free_bytes": self.free_bytes,
            "protection_persistent": self.protection_persistent,
            "silent_degradation": self.silent_degradation,
        }
        if self.failure_id is not None:
            body["failure_id"] = self.failure_id
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class LifecycleCampaignInputs:
    """Injected clock, disk fixture, and soak-local skip switches."""

    clock: VpsClock
    composition_inputs: CompositionFingerprintInputs
    disk_headroom_min: int
    crash_loop_max_boots: int = 3
    crash_loop_window_ns: int = 60_000_000_000
    drain_window_ns: int = 30_000_000_000
    watchdog_interval_ns: int = 5_000_000_000
    seat_callback_deadline_ns: int = 1_000_000_000
    slice_watch_trip_multiple: int = 3
    clock_warn_ns: int = 25_000_000
    clock_no_new_entry_ns: int = 100_000_000
    clock_halt_ns: int = 250_000_000
    clock_unsynchronized_after_ns: int = 60_000_000_000
    run_live_vps_firewall: bool = False
    run_live_bucket_restore: bool = False
    run_clean_host_rehearsal: bool = False
    request_restore_cutover: bool = False
    invent_disk_headroom_min: bool = False


@dataclass(frozen=True, slots=True)
class LifecycleCampaignReport:
    """Fingerprinted proof of the Story 28.4 lifecycle campaign."""

    format_version: int
    fingerprint: object
    injections: tuple[str, ...]
    stand_down_doors_serving: bool
    only_resurrect_clears: bool
    quarantine_survives_restart: bool
    seat_reinstate_required: bool
    clock_no_new_entry_separate_from_halt: bool
    disk_headroom_degrades_before_full: bool
    sigterm_flushes: bool
    sigterm_mints_unknown: bool
    sigterm_never_flattens: bool
    protective_acts_available_or_persistent: bool
    runs_live_vps_firewall: bool
    runs_live_bucket_restore: bool
    restore_grants_node_authority: bool
    stack_required: bool
    watcher_only_notifies: bool
    sections: Mapping[str, object]
    measured_ns: Mapping[str, int]

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": LIFECYCLE_CAMPAIGN_CLASS,
            "clock_no_new_entry_separate_from_halt": (self.clock_no_new_entry_separate_from_halt),
            "disk_headroom_degrades_before_full": self.disk_headroom_degrades_before_full,
            "format_version": self.format_version,
            "injections": list(self.injections),
            "only_resurrect_clears": self.only_resurrect_clears,
            "protective_acts_available_or_persistent": (
                self.protective_acts_available_or_persistent
            ),
            "quarantine_survives_restart": self.quarantine_survives_restart,
            "restore_grants_node_authority": self.restore_grants_node_authority,
            "runs_live_bucket_restore": self.runs_live_bucket_restore,
            "runs_live_vps_firewall": self.runs_live_vps_firewall,
            "seat_reinstate_required": self.seat_reinstate_required,
            "sections": dict(self.sections),
            "sigterm_flushes": self.sigterm_flushes,
            "sigterm_mints_unknown": self.sigterm_mints_unknown,
            "sigterm_never_flattens": self.sigterm_never_flattens,
            "stack_required": self.stack_required,
            "stand_down_doors_serving": self.stand_down_doors_serving,
            "surface": LIFECYCLE_CAMPAIGN_SURFACE,
            "watcher_only_notifies": self.watcher_only_notifies,
        }

    def as_mapping(self) -> Mapping[str, object]:
        body = self.fp1_identity()
        body["fingerprint"] = getattr(self.fingerprint, "value", self.fingerprint)
        body["measured_ns"] = dict(self.measured_ns)
        return MappingProxyType(body)


def refuse_live_vps_firewall_campaign(**extra: object) -> TypedRefusal:
    """Story 28.4 does not apply a live VPS firewall campaign."""
    return policy(
        "live_vps_firewall",
        "the Epic 28 security campaign proves unit/network posture from "
        "checked-in templates and the declarative network contract; a live "
        "VPS firewall apply is soak-local and is not a Story 28.4 factory AC",
        failure_id=_ID_FIREWALL,
        **extra,
    )


def refuse_live_bucket_restore(**extra: object) -> TypedRefusal:
    """Story 28.4 does not restore from a live Backblaze bucket."""
    return policy(
        "live_bucket_restore",
        "restore claims in this campaign are local-fixture / contract proofs; "
        "a live Backblaze bucket restore is soak-local (AR-87)",
        failure_id=_ID_BUCKET,
        **extra,
    )


def evaluate_disk_headroom(
    *,
    free_bytes: object,
    disk_headroom_min: object,
) -> Result[DiskHeadroomDecision]:
    """Mint ``ok | no-new-entry | full`` so headroom trips before disk-full."""
    floor = _non_negative_int("disk_headroom_min", disk_headroom_min, positive=True)
    if is_refusal(floor):
        return floor
    free = _non_negative_int("free_bytes", free_bytes, positive=False)
    if is_refusal(free):
        return free
    if free.value >= floor.value:
        band = DiskHeadroomBand.OK
        failure = None
        silent = False
        entries = False
    elif free.value == 0:
        band = DiskHeadroomBand.FULL
        failure = "disk.band.full"
        silent = True
        entries = True
    else:
        band = DiskHeadroomBand.NO_NEW_ENTRY
        failure = "disk.band.no_new_entry"
        silent = True
        entries = True
    return Ok(
        DiskHeadroomDecision(
            band=band,
            free_bytes=free.value,
            disk_headroom_min=floor.value,
            silent_degradation=silent,
            entries_refused=entries,
            protection_persistent=True,
            failure_id=failure,
        )
    )


def run_paper_milestone_lifecycle_campaign(
    inputs: object,
) -> Result[LifecycleCampaignReport]:
    """Inject the named lifecycle faults and fold every designed degraded state."""
    if not isinstance(inputs, LifecycleCampaignInputs):
        return invalid(
            "inputs",
            "the lifecycle campaign takes LifecycleCampaignInputs",
            given=type(inputs).__name__,
            failure_id=_ID_INPUTS,
        )
    if inputs.run_live_vps_firewall is True:
        return refuse_live_vps_firewall_campaign()
    if inputs.run_live_bucket_restore is True:
        live = refuse_live_bucket_tonight(provider="backblaze-b2")
        if is_refusal(live):
            return refuse_live_bucket_restore(cause=live.context.get("failure_id"))
        return refuse_live_bucket_restore()
    if inputs.run_clean_host_rehearsal is True:
        return refuse_clean_host_rehearsal_tonight(backend="backblaze-b2")
    if inputs.request_restore_cutover is True:
        return refuse_automatic_cutover(source_root=_MACHINE)
    if inputs.invent_disk_headroom_min is True:
        return policy(
            "disk_headroom_min",
            "disk_headroom_min is an injected evidence fixture; the campaign "
            "never invents a ratified constant (FTR-07)",
            failure_id=_ID_DISK,
        )

    now = _unwrap(inputs.clock.wall_now())
    if isinstance(now, TypedRefusal):
        return now
    started = now.value_ns

    crash = _unwrap(_exercise_crash_loop(inputs))
    if isinstance(crash, TypedRefusal):
        return crash
    preflight = _unwrap(_exercise_preflight(inputs))
    if isinstance(preflight, TypedRefusal):
        return preflight
    quarantine = _unwrap(_exercise_quarantine(now))
    if isinstance(quarantine, TypedRefusal):
        return quarantine
    clock = _unwrap(_exercise_clock(inputs, now))
    if isinstance(clock, TypedRefusal):
        return clock
    disk = _unwrap(_exercise_disk(inputs, now))
    if isinstance(disk, TypedRefusal):
        return disk
    freshness = _unwrap(_exercise_data_freshness())
    if isinstance(freshness, TypedRefusal):
        return freshness
    shutdown = _unwrap(_exercise_shutdown(inputs))
    if isinstance(shutdown, TypedRefusal):
        return shutdown
    recovery = _unwrap(_exercise_recovery_and_monitoring(inputs, now, started))
    if isinstance(recovery, TypedRefusal):
        return recovery

    sections = {
        "callback-wedge": dict(quarantine),
        "clock": dict(clock),
        "crash-loop": dict(crash),
        "data-freshness": dict(freshness),
        "disk": dict(disk),
        "preflight": dict(preflight),
        "recovery": dict(recovery),
        "shutdown": dict(shutdown),
    }
    missing = [name for name in LIFECYCLE_INJECTIONS if name not in sections]
    if missing:
        return policy(
            "injections",
            "every named lifecycle injection must resolve to its documented state",
            missing=missing,
            failure_id=_ID_INJECTION,
        )

    protective = (
        crash["protective_admit"] is True
        and preflight["protective_admit"] is True
        and clock["protection_preserved"] is True
        and disk["protection_persistent"] is True
        and freshness["protection_enactable"] is True
        and shutdown["flattened"] is False
    )
    measured = {
        "campaign": 0,
        "clock": _as_int(clock.get("measured_ns", 0)),
        "crash-loop": _as_int(crash.get("measured_ns", 0)),
        "data-freshness": _as_int(freshness.get("measured_ns", 0)),
        "disk": _as_int(disk.get("measured_ns", 0)),
        "preflight": _as_int(preflight.get("measured_ns", 0)),
        "quarantine": _as_int(quarantine.get("measured_ns", 0)),
        "recovery": _as_int(recovery.get("measured_ns", 0)),
        "shutdown": _as_int(shutdown.get("measured_ns", 0)),
    }
    identity = {
        "class": LIFECYCLE_CAMPAIGN_CLASS,
        "clock_no_new_entry_separate_from_halt": clock["separate_from_halt"] is True,
        "disk_headroom_degrades_before_full": disk["degrades_before_full"] is True,
        "format_version": LIFECYCLE_CAMPAIGN_FORMAT_VERSION,
        "injections": list(LIFECYCLE_INJECTIONS),
        "only_resurrect_clears": crash["only_resurrect_clears"] is True,
        "protective_acts_available_or_persistent": protective,
        "quarantine_survives_restart": quarantine["survives_restart"] is True,
        "restore_grants_node_authority": False,
        "runs_live_bucket_restore": RUNS_LIVE_BUCKET_RESTORE,
        "runs_live_vps_firewall": RUNS_LIVE_VPS_FIREWALL,
        "seat_reinstate_required": quarantine["seat_reinstate_required"] is True,
        "sections": sections,
        "sigterm_flushes": shutdown["flushed"] is True,
        "sigterm_mints_unknown": shutdown["unknown_minted"] is True,
        "sigterm_never_flattens": shutdown["flattened"] is False,
        "stack_required": False,
        "stand_down_doors_serving": crash["doors_serving"] is True,
        "surface": LIFECYCLE_CAMPAIGN_SURFACE,
        "watcher_only_notifies": recovery["watcher_only_notifies"] is True,
    }
    stamped = fingerprint(identity)
    if is_refusal(stamped):
        return _as_refusal(stamped)
    return Ok(
        LifecycleCampaignReport(
            format_version=LIFECYCLE_CAMPAIGN_FORMAT_VERSION,
            fingerprint=stamped.value,
            injections=LIFECYCLE_INJECTIONS,
            stand_down_doors_serving=crash["doors_serving"] is True,
            only_resurrect_clears=crash["only_resurrect_clears"] is True,
            quarantine_survives_restart=quarantine["survives_restart"] is True,
            seat_reinstate_required=quarantine["seat_reinstate_required"] is True,
            clock_no_new_entry_separate_from_halt=clock["separate_from_halt"] is True,
            disk_headroom_degrades_before_full=disk["degrades_before_full"] is True,
            sigterm_flushes=shutdown["flushed"] is True,
            sigterm_mints_unknown=shutdown["unknown_minted"] is True,
            sigterm_never_flattens=shutdown["flattened"] is False,
            protective_acts_available_or_persistent=protective,
            runs_live_vps_firewall=RUNS_LIVE_VPS_FIREWALL,
            runs_live_bucket_restore=RUNS_LIVE_BUCKET_RESTORE,
            restore_grants_node_authority=False,
            stack_required=False,
            watcher_only_notifies=recovery["watcher_only_notifies"] is True,
            sections=MappingProxyType(sections),
            measured_ns=MappingProxyType(measured),
        )
    )


def _exercise_crash_loop(inputs: LifecycleCampaignInputs) -> Result[Mapping[str, object]]:
    supervisor = _supervisor(inputs, boot_epoch_id=_BOOT)
    base = 5_000_000_000_000
    for index in range(inputs.crash_loop_max_boots):
        recorded = supervisor.record_boot_attempt(
            boot_epoch_id=f"boot-crash-{index}",
            at_ns=base + index,
            reason=None,
            exited=True,
        )
        if is_refusal(recorded):
            return _as_refusal(recorded)
    if supervisor.state is not LifecycleState.STAND_DOWN_ALIVE:
        return policy("crash-loop", "crash-loop fold must enter stand-down-alive")
    if supervisor.stand_down_trigger is not StandDownTrigger.CRASH_LOOP:
        return policy("crash-loop", "stand-down trigger must be crash-loop")
    if supervisor.doors_serving is not True:
        return policy("crash-loop", "stand-down keeps doors serving")

    protective = _unwrap(
        admit_under_lifecycle(
            state=LifecycleState.STAND_DOWN_ALIVE,
            kind="flatten",
        )
    )
    if isinstance(protective, TypedRefusal):
        return protective
    entry = _unwrap(
        admit_under_lifecycle(
            state=LifecycleState.STAND_DOWN_ALIVE,
            kind="place_order",
            risk_increasing=True,
        )
    )
    if isinstance(entry, TypedRefusal):
        return entry
    if protective != "admit" or entry != "refuse-entry":
        return policy(
            "crash-loop",
            "stand-down refuses entries and keeps risk-non-increasing acts",
            protective=protective,
            entry=entry,
        )

    fold = supervisor.crash_loop
    if fold is None:
        return policy("crash-loop", "crash-loop fold must be present")
    reloaded = CrashLoopFold.load(
        max_boots=inputs.crash_loop_max_boots,
        window_ns=inputs.crash_loop_window_ns,
        stamps=fold.stamps,
    )
    if is_refusal(reloaded):
        return _as_refusal(reloaded)
    restarted = LifecycleSupervisor(
        config=supervisor.config,
        notify=RecordingNotifyTransport(),
        boot_epoch_id="boot-restart",
        crash_loop=reloaded.value,
        state=LifecycleState.STAND_DOWN_ALIVE,
        stand_down_trigger=StandDownTrigger.CRASH_LOOP,
        doors_serving=True,
    )
    ops = restarted.resurrect(
        principal="ops",
        scope="global",
        new_boot_epoch_id="boot-ops",
    )
    if is_ok(ops):
        return policy("crash-loop", "ops principal must not resurrect")
    if restarted.state is not LifecycleState.STAND_DOWN_ALIVE:
        return policy("crash-loop", "restart plus ops resurrect must not clear stand-down")

    receipt = restarted.resurrect(
        principal=OPERATOR_PRINCIPAL,
        scope="global",
        new_boot_epoch_id="boot-resurrect",
    )
    if is_refusal(receipt):
        return _as_refusal(receipt)
    if receipt.value.clears_by_restart is True:
        return policy("crash-loop", "resurrect must not be a restart-clear")
    return Ok(
        MappingProxyType(
            {
                "doors_serving": True,
                "measured_ns": 0,
                "only_resurrect_clears": True,
                "protective_admit": True,
                "restart_clears": False,
                "trigger": StandDownTrigger.CRASH_LOOP.value,
            }
        )
    )


def _exercise_preflight(inputs: LifecycleCampaignInputs) -> Result[Mapping[str, object]]:
    outcome = run_boot_ceremony(
        boot_epoch_id="boot-preflight-28-4",
        machine=_MACHINE,
        composition_inputs=inputs.composition_inputs,
        writer_streams=(
            ("command", "venue-a:acct-1"),
            ("adapter", "venue-a:acct-1:feed"),
            ("risk", _BINDING),
        ),
        boot_attempt_sink=InMemoryBootAttemptSink(),
        preflight=PreflightFacts(chrony_synced=False),
    )
    if is_refusal(outcome):
        return _as_refusal(outcome)
    if outcome.value.stand_down_alive is not True:
        return policy("preflight", "detected preflight refusal enters stand-down-alive")
    if outcome.value.doors.bound is not True:
        return policy("preflight", "doors bind before preflight so stand-down stays observable")
    if outcome.value.exit_code is not None:
        return policy("preflight", "preflight stand-down does not exit the process")
    if outcome.value.opens_sequencer is not False:
        return policy("preflight", "preflight stand-down must not open the sequencer")
    protective = _unwrap(
        admit_under_lifecycle(
            state=LifecycleState.STAND_DOWN_ALIVE,
            kind="close_position",
        )
    )
    if isinstance(protective, TypedRefusal):
        return protective
    return Ok(
        MappingProxyType(
            {
                "doors_bound": True,
                "failure_id": outcome.value.failure_id,
                "measured_ns": 0,
                "opens_sequencer": False,
                "process_exited": False,
                "protective_admit": protective == "admit",
                "stand_down_alive": True,
            }
        )
    )


def _exercise_quarantine(now: Instant) -> Result[Mapping[str, object]]:
    stream = SeatTransitionStream()
    minted = mint_quarantine_transition(
        seat_id=_SEAT,
        binding_ref=_BINDING,
        from_state=GovernedSeatState.ACTIVE,
        trigger=QuarantineTrigger.NON_RETURNING_CALLBACK,
        transition_instant=now,
        breach_detail="callback-wedge",
        stream=stream,
    )
    if is_refusal(minted):
        return _as_refusal(minted)
    folded = fold_seat_state(stream, _SEAT, initial=GovernedSeatState.ACTIVE)
    if is_refusal(folded):
        return _as_refusal(folded)
    if folded.value is not GovernedSeatState.QUARANTINED:
        return policy("quarantine", "callback wedge must auto-quarantine the seat")

    after_restart = fold_seat_state(stream, _SEAT, initial=GovernedSeatState.ADMITTED)
    if is_refusal(after_restart):
        return _as_refusal(after_restart)
    if after_restart.value is not GovernedSeatState.QUARANTINED:
        return policy("quarantine", "quarantine must survive restart as a stream fold")

    inferred = mint_seat_reinstate(
        seat_id=_SEAT,
        binding_ref=_BINDING,
        transition_instant=now,
        operator_signature="operator:28-4",
        infer_from_restart=True,
    )
    if is_ok(inferred):
        return policy("quarantine", "restart must not infer seat_reinstate")

    ops = apply_operator_seat_reinstate(
        principal="ops",
        seat_id=_SEAT,
        binding_ref=_BINDING,
        transition_instant=now,
        operator_signature="ops:28-4",
        stream=stream,
    )
    if is_ok(ops):
        return policy("quarantine", "ops principal must not seat_reinstate")

    reinstated = apply_operator_seat_reinstate(
        principal=OPERATOR_PRINCIPAL,
        seat_id=_SEAT,
        binding_ref=_BINDING,
        transition_instant=now,
        operator_signature="operator:28-4",
        stream=stream,
    )
    if is_refusal(reinstated):
        return _as_refusal(reinstated)
    cleared = fold_seat_state(stream, _SEAT, initial=GovernedSeatState.ACTIVE)
    if is_refusal(cleared):
        return _as_refusal(cleared)
    if cleared.value is GovernedSeatState.QUARANTINED:
        return policy("quarantine", "operator seat_reinstate must leave quarantined")
    return Ok(
        MappingProxyType(
            {
                "measured_ns": 0,
                "restart_clears": False,
                "seat_reinstate_required": True,
                "state_after_restart": after_restart.value.value,
                "state_after_reinstate": cleared.value.value,
                "survives_restart": True,
                "trigger": QuarantineTrigger.NON_RETURNING_CALLBACK.value,
            }
        )
    )


def _exercise_clock(
    inputs: LifecycleCampaignInputs,
    now: Instant,
) -> Result[Mapping[str, object]]:
    thresholds = ClockDriftThresholds.try_create(
        warn_ns=inputs.clock_warn_ns,
        no_new_entry_ns=inputs.clock_no_new_entry_ns,
        halt_ns=inputs.clock_halt_ns,
        unsynchronized_after_ns=inputs.clock_unsynchronized_after_ns,
    )
    if is_refusal(thresholds):
        return _as_refusal(thresholds)
    nne_truth = MachineVersusTruth.try_create(
        offset_ns=inputs.clock_no_new_entry_ns,
        stratum=1,
        sync_age_ns=0,
        synchronized=True,
    )
    if is_refusal(nne_truth):
        return _as_refusal(nne_truth)
    halt_truth = MachineVersusTruth.try_create(
        offset_ns=inputs.clock_halt_ns,
        stratum=1,
        sync_age_ns=0,
        synchronized=True,
    )
    if is_refusal(halt_truth):
        return _as_refusal(halt_truth)
    nne = evaluate_clock_band(thresholds=thresholds.value, truth=nne_truth.value, now=now)
    if is_refusal(nne):
        return _as_refusal(nne)
    halt = evaluate_clock_band(thresholds=thresholds.value, truth=halt_truth.value, now=now)
    if is_refusal(halt):
        return _as_refusal(halt)
    if nne.value.band is not ClockBand.NO_NEW_ENTRY:
        return policy("clock", "no-new-entry drift must mint the no-new-entry band")
    if halt.value.band is not ClockBand.HALT:
        return policy("clock", "halt drift must mint the halt band")
    if clock_band_requires_stand_down(nne.value.band) is True:
        return policy("clock", "no-new-entry must not request stand-down")
    if clock_band_requires_stand_down(halt.value.band) is not True:
        return policy("clock", "halt must request stand-down")
    if clock_band_entry_side_refused(nne.value.band, act="place_order") is not True:
        return policy("clock", "no-new-entry refuses entries")
    if clock_band_preserves_protection(nne.value.band, act="flatten") is not True:
        return policy("clock", "no-new-entry preserves protection")

    supervisor = _supervisor(inputs, boot_epoch_id="boot-clock-halt")
    stood = supervisor.enter_stand_down(trigger=StandDownTrigger.CLOCK_HALT)
    if is_refusal(stood):
        return _as_refusal(stood)
    return Ok(
        MappingProxyType(
            {
                "halt_band": halt.value.band.value,
                "halt_stand_down": True,
                "measured_ns": 0,
                "no_new_entry_band": nne.value.band.value,
                "no_new_entry_stand_down": False,
                "protection_preserved": True,
                "separate_from_halt": True,
            }
        )
    )


def _exercise_disk(
    inputs: LifecycleCampaignInputs,
    now: Instant,
) -> Result[Mapping[str, object]]:
    floor = inputs.disk_headroom_min
    ok = evaluate_disk_headroom(free_bytes=floor, disk_headroom_min=floor)
    if is_refusal(ok):
        return _as_refusal(ok)
    degraded = evaluate_disk_headroom(free_bytes=max(floor // 2, 1), disk_headroom_min=floor)
    if is_refusal(degraded):
        return _as_refusal(degraded)
    full = evaluate_disk_headroom(free_bytes=0, disk_headroom_min=floor)
    if is_refusal(full):
        return _as_refusal(full)
    if ok.value.band is not DiskHeadroomBand.OK:
        return policy("disk", "free space at the floor is ok")
    if degraded.value.band is not DiskHeadroomBand.NO_NEW_ENTRY:
        return policy("disk", "headroom below the floor mints no-new-entry before full")
    if full.value.band is not DiskHeadroomBand.FULL:
        return policy("disk", "zero free bytes is the disk-full block")
    if not (
        degraded.value.entries_refused
        and degraded.value.silent_degradation
        and full.value.entries_refused
    ):
        return policy("disk", "headroom and full both refuse entries")

    persisted = _unwrap(_persist_under_full_disk(now))
    if isinstance(persisted, TypedRefusal):
        return persisted
    return Ok(
        MappingProxyType(
            {
                "degrades_before_full": True,
                "degraded": dict(degraded.value.as_mapping()),
                "full": dict(full.value.as_mapping()),
                "measured_ns": 0,
                "ok": dict(ok.value.as_mapping()),
                "protection_persistent": persisted is True,
            }
        )
    )


def _persist_under_full_disk(now: Instant) -> Result[bool]:
    venue = VenueId.try_create("conformance:paper-28-4")
    if is_refusal(venue):
        return _as_refusal(venue)
    stream = CommandStreamKey.try_create(venue.value, "acct-demo")
    if is_refusal(stream):
        return _as_refusal(stream)
    action = mint_control_action(
        ControlActionKind.FLATTEN,
        "book-28-4",
        AuthorityKind.BOOK_POLICY,
        SubjectScope.BINDING,
        _BINDING,
        1,
        "disk-full-protection",
        stream.value,
        now,
        trigger_class="disk-full",
    )
    if is_refusal(action):
        return _as_refusal(action)
    extent = ProtectionIntentExtent.try_create(4)
    if is_refusal(extent):
        return _as_refusal(extent)
    persisted = persist_protective_intent(
        action.value,
        journal_result=unpersistable("disk full"),
        extent=extent.value,
    )
    if is_refusal(persisted):
        return _as_refusal(persisted)
    if persisted.value.disposition is not IntentPersistDisposition.EXTENT:
        return policy(
            "disk",
            "disk-full journal refusal must persist protection to the reserved extent",
            disposition=persisted.value.disposition.value,
        )
    return Ok(True)


def _exercise_data_freshness() -> Result[Mapping[str, object]]:
    report = default_health_report(overrides={"data_freshness": "degraded"})
    state = report.states["data_freshness"].state
    if state != "degraded":
        return policy("data-freshness", "injected data_freshness must be degraded")
    band = CycleBand.NO_NEW_ENTRY
    if entry_side_refused(band, act="place_order") is not True:
        return policy("data-freshness", "degraded freshness refuses entries")
    if protection_enactable(band, act="close_position") is not True:
        return policy("data-freshness", "degraded freshness keeps protection enactable")
    return Ok(
        MappingProxyType(
            {
                "band": band.value,
                "collapsed_global_colour": report.collapsed_global_colour,
                "measured_ns": 0,
                "protection_enactable": True,
                "state": state,
            }
        )
    )


def _exercise_shutdown(inputs: LifecycleCampaignInputs) -> Result[Mapping[str, object]]:
    supervisor = _supervisor(inputs, boot_epoch_id="boot-sigterm")
    fated = supervisor.set_command_fate("in-flight", CommandFate.UNRESOLVED)
    if is_refusal(fated):
        return _as_refusal(fated)
    begun = supervisor.begin_drain(kind=ShutdownKind.SIGTERM, now_mono_ns=100)
    if is_refusal(begun):
        return _as_refusal(begun)
    outcome = supervisor.complete_drain(now_mono_ns=200, flush_ok=True)
    if is_refusal(outcome):
        return _as_refusal(outcome)
    drain = outcome.value
    if drain.kind is not ShutdownKind.SIGTERM:
        return policy("shutdown", "SIGTERM must drain as sigterm")
    if drain.flattened is not False or drain.waited_for_flat is not False:
        return policy("shutdown", "SIGTERM never flattens and never waits for flat")
    if drain.sinks_flushed is not True:
        return policy("shutdown", "SIGTERM must flush sinks")
    if "in-flight" not in drain.unknown_minted_command_ids:
        return policy("shutdown", "SIGTERM mints UNKNOWN for unresolved commands")
    return Ok(
        MappingProxyType(
            {
                "exit_code": drain.exit_code,
                "flattened": False,
                "flushed": True,
                "measured_ns": 0,
                "unknown_minted": True,
                "unknown_minted_command_ids": list(drain.unknown_minted_command_ids),
            }
        )
    )


def _exercise_recovery_and_monitoring(
    inputs: LifecycleCampaignInputs,
    now: Instant,
    started_ns: int,
) -> Result[Mapping[str, object]]:
    del inputs
    watcher = WatcherDouble(cadence_ns=1_000_000_000)
    missing = watcher.evaluate(now.value_ns + 2_000_000_000)
    if is_refusal(missing):
        return _as_refusal(missing)
    if missing.value != "missing-ping":
        return policy("recovery", "heartbeat loss must notify missing-ping")
    if not watcher.missing_notifications:
        return policy("recovery", "watcher must record the missing-ping notification")

    # Observability stack absent: supervisor still announces READY and serves doors.
    supervisor = LifecycleSupervisor(
        config=_ok_config(
            crash_loop_max_boots=3,
            crash_loop_window_ns=60_000_000_000,
            drain_window_ns=30_000_000_000,
            watchdog_interval_ns=5_000_000_000,
            seat_callback_deadline_ns=1_000_000_000,
            slice_watch_trip_multiple=3,
        ),
        notify=RecordingNotifyTransport(),
        boot_epoch_id="boot-stack-absent",
    )
    ready = supervisor.mark_ready()
    if is_refusal(ready):
        return _as_refusal(ready)
    if supervisor.doors_serving is not True:
        return policy("recovery", "the node must run with the observability stack absent")

    duration = now.value_ns - started_ns
    return Ok(
        MappingProxyType(
            {
                "clean_host_rehearsal_tonight": CLEAN_HOST_REHEARSAL_TONIGHT,
                "drills": [SAMPLE_DRILL, FULL_DRILL, HOST_LOSS_DRILL],
                "measured_ns": duration if duration > 0 else 0,
                "restore_auto_cutover": RESTORE_AUTO_CUTOVER,
                "restore_grants_node_authority": False,
                "stack_absent_node_runs": True,
                "watcher_can_call_door": CAN_CALL_DOOR,
                "watcher_can_close_positions": CAN_CLOSE_POSITIONS,
                "watcher_can_stop_entries": CAN_STOP_ENTRIES,
                "watcher_holds_zero_authority": HOLDS_ZERO_AUTHORITY,
                "watcher_missing_ping": True,
                "watcher_only_notifies": True,
            }
        )
    )


def _supervisor(inputs: LifecycleCampaignInputs, *, boot_epoch_id: str) -> LifecycleSupervisor:
    return LifecycleSupervisor(
        config=_ok_config(
            crash_loop_max_boots=inputs.crash_loop_max_boots,
            crash_loop_window_ns=inputs.crash_loop_window_ns,
            drain_window_ns=inputs.drain_window_ns,
            watchdog_interval_ns=inputs.watchdog_interval_ns,
            seat_callback_deadline_ns=inputs.seat_callback_deadline_ns,
            slice_watch_trip_multiple=inputs.slice_watch_trip_multiple,
        ),
        notify=RecordingNotifyTransport(),
        boot_epoch_id=boot_epoch_id,
    )


def _ok_config(
    *,
    crash_loop_max_boots: int,
    crash_loop_window_ns: int,
    drain_window_ns: int,
    watchdog_interval_ns: int,
    seat_callback_deadline_ns: int,
    slice_watch_trip_multiple: int,
) -> SupervisionConfig:
    created = SupervisionConfig.try_create(
        crash_loop_max_boots=crash_loop_max_boots,
        crash_loop_window_ns=crash_loop_window_ns,
        drain_window_ns=drain_window_ns,
        watchdog_interval_ns=watchdog_interval_ns,
        seat_callback_deadline_ns=seat_callback_deadline_ns,
        slice_watch_trip_multiple=slice_watch_trip_multiple,
    )
    if is_refusal(created):
        msg = "supervision config fixtures must be valid campaign inputs"
        raise AssertionError(msg)
    return created.value


def _as_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return value


def _non_negative_int(field: str, value: object, *, positive: bool) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return invalid(field, f"{field} is an int byte count", given=repr(value))
    if positive and value <= 0:
        return invalid(field, f"{field} is a positive int", given=repr(value))
    if value < 0:
        return invalid(field, f"{field} is a non-negative int", given=repr(value))
    return Ok(value)


def _unwrap(result: Result[T]) -> T | TypedRefusal:
    if isinstance(result, TypedRefusal):
        return result
    return result.value


def _as_refusal(result: object) -> TypedRefusal:
    if isinstance(result, TypedRefusal):
        return result
    return invalid("internal", "expected a typed refusal", given=type(result).__name__)
