"""Live clock discipline: sync gate, four bands, two named measurements (TN-14).

Machine-versus-truth (chrony) and node-versus-broker skew stay named apart and
are never merged. Bands ``ok | warn | no-new-entry | halt`` are per-decision-cycle
preconditions — never standing CT-30 actions. Unsynchronized is distinct from
measured drift (DEC-0199).
"""

from __future__ import annotations

from collections.abc import Mapping, MutableSequence, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Instant, MonotonicReading, Ok, Result
from qmf.core.refusal import is_refusal

from qmn.time._refuse import clean_token, invalid

__all__ = [
    "CLOCK_BAND_FAILURE_IDS",
    "SILENT_DEGRADATION_ALARM_CLASS",
    "STAND_DOWN_TRIGGER_CLOCK_HALT",
    "ClockBand",
    "ClockBandDecision",
    "ClockDriftThresholds",
    "MachineVersusTruth",
    "NodeVersusBrokerSkew",
    "SuspectWindow",
    "SyncPosture",
    "UnsynchronizedInterval",
    "WallMonotonicDivergenceDetector",
    "broker_skew_is_not_latency",
    "clock_band_entry_side_refused",
    "clock_band_preserves_protection",
    "clock_band_requires_stand_down",
    "evaluate_clock_band",
    "evaluate_sync_posture",
    "measurements_named_apart",
    "record_unsynchronized_interval",
]

SILENT_DEGRADATION_ALARM_CLASS: Final[str] = "silent-degradation"
STAND_DOWN_TRIGGER_CLOCK_HALT: Final[str] = "clock-halt"

CLOCK_BAND_FAILURE_IDS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "warn": "clock.band.warn",
        "no-new-entry": "clock.band.no_new_entry",
        "halt": "clock.band.halt",
        "unsynchronized": "clock.sync.unsynchronized",
        "chrony_waitsync": "preflight.clock.chrony",
        "step_suspect": "clock.divergence.suspect_window",
    }
)


class ClockBand(StrEnum):
    """Per-decision-cycle clock precondition bands (TN-14 / DEC-0199)."""

    OK = "ok"
    WARN = "warn"
    NO_NEW_ENTRY = "no-new-entry"
    HALT = "halt"


class SyncPosture(StrEnum):
    """Chrony / time-source posture — unsynchronized is not a drift band."""

    SYNCHRONIZED = "synchronized"
    UNSYNCHRONIZED = "unsynchronized"
    PREFLIGHT_BLOCKED = "preflight-blocked"


@dataclass(frozen=True, slots=True)
class ClockDriftThresholds:
    """Injected registry band thresholds (evidence values, never ratified constants).

    Rows: ``clock_drift_warn``, ``clock_drift_no_new_entry``, ``clock_drift_halt``,
    ``clock_unsynchronized_after`` (DEC-0199, DEC-0256). Ordering
    ``0 < warn < no_new_entry < halt`` is required; unsynchronized_after is the
    distinct no-source horizon.
    """

    warn_ns: int
    no_new_entry_ns: int
    halt_ns: int
    unsynchronized_after_ns: int

    @classmethod
    def try_create(
        cls,
        *,
        warn_ns: object,
        no_new_entry_ns: object,
        halt_ns: object,
        unsynchronized_after_ns: object,
    ) -> Result[ClockDriftThresholds]:
        """Validate injected band thresholds (strictly increasing positive ints)."""
        warn = _positive_ns(warn_ns, "warn_ns")
        if is_refusal(warn):
            return warn
        nne = _positive_ns(no_new_entry_ns, "no_new_entry_ns")
        if is_refusal(nne):
            return nne
        halt = _positive_ns(halt_ns, "halt_ns")
        if is_refusal(halt):
            return halt
        unsync = _positive_ns(unsynchronized_after_ns, "unsynchronized_after_ns")
        if is_refusal(unsync):
            return unsync
        if not (warn.value < nne.value < halt.value):
            return invalid(
                "thresholds",
                "clock bands require 0 < warn < no_new_entry < halt (nanoseconds)",
                warn_ns=warn.value,
                no_new_entry_ns=nne.value,
                halt_ns=halt.value,
            )
        return Ok(
            cls(
                warn_ns=warn.value,
                no_new_entry_ns=nne.value,
                halt_ns=halt.value,
                unsynchronized_after_ns=unsync.value,
            )
        )


@dataclass(frozen=True, slots=True)
class MachineVersusTruth:
    """Chrony machine-versus-truth sample — never merged with broker skew."""

    offset_ns: int
    stratum: int
    sync_age_ns: int
    step_count: int
    synchronized: bool

    @classmethod
    def try_create(
        cls,
        *,
        offset_ns: object,
        stratum: object,
        sync_age_ns: object,
        step_count: object = 0,
        synchronized: object = True,
    ) -> Result[MachineVersusTruth]:
        """Build one machine-versus-truth sample from injected chrony facts."""
        offset = _int_ns(offset_ns, "offset_ns", allow_negative=True)
        if is_refusal(offset):
            return offset
        age = _int_ns(sync_age_ns, "sync_age_ns", allow_negative=False)
        if is_refusal(age):
            return age
        if isinstance(stratum, bool) or not isinstance(stratum, int) or stratum < 0:
            return invalid(
                "stratum",
                "chrony stratum is a non-negative int",
                given=repr(stratum),
            )
        if isinstance(step_count, bool) or not isinstance(step_count, int) or step_count < 0:
            return invalid(
                "step_count",
                "step counter is a non-negative int",
                given=repr(step_count),
            )
        if not isinstance(synchronized, bool):
            return invalid(
                "synchronized",
                "synchronized is a bool (chronyc waitsync posture)",
                given=repr(synchronized),
            )
        return Ok(
            cls(
                offset_ns=offset.value,
                stratum=stratum,
                sync_age_ns=age.value,
                step_count=step_count,
                synchronized=synchronized,
            )
        )

    @property
    def measurement_kind(self) -> str:
        return "machine-versus-truth"

    def abs_offset_ns(self) -> int:
        return abs(self.offset_ns)


@dataclass(frozen=True, slots=True)
class NodeVersusBrokerSkew:
    """Per-venue node-versus-broker skew — never auto-corrected, never latency.

    Rolling ``local_receive − source`` series; the band input is the windowed
    minimum absolute skew (DEC-0199).
    """

    venue_id: str
    samples_ns: tuple[int, ...]
    windowed_min_abs_ns: int

    @classmethod
    def try_create(
        cls,
        *,
        venue_id: object,
        local_receive_minus_source_ns: object,
    ) -> Result[NodeVersusBrokerSkew]:
        """Build skew from a sequence of ``local_receive − source`` nanosecond deltas."""
        vid = clean_token(venue_id)
        if vid is None:
            return invalid(
                "venue_id",
                "broker skew is scoped to a non-empty VenueId",
                given=repr(venue_id),
            )
        if not isinstance(local_receive_minus_source_ns, Sequence) or isinstance(
            local_receive_minus_source_ns, (str, bytes)
        ):
            return invalid(
                "local_receive_minus_source_ns",
                "skew samples are a sequence of int nanosecond deltas",
                given=repr(type(local_receive_minus_source_ns).__name__),
            )
        samples: list[int] = []
        for index, raw in enumerate(cast("Sequence[object]", local_receive_minus_source_ns)):
            if isinstance(raw, bool) or not isinstance(raw, int):
                return invalid(
                    "local_receive_minus_source_ns",
                    "each skew sample is an int nanosecond delta",
                    index=index,
                    given=repr(raw),
                )
            samples.append(raw)
        if not samples:
            return invalid(
                "local_receive_minus_source_ns",
                "broker skew requires at least one local_receive - source sample",
            )
        windowed = min(abs(value) for value in samples)
        return Ok(
            cls(
                venue_id=vid,
                samples_ns=tuple(samples),
                windowed_min_abs_ns=windowed,
            )
        )

    @property
    def measurement_kind(self) -> str:
        return "node-versus-broker-skew"


@dataclass(frozen=True, slots=True)
class UnsynchronizedInterval:
    """Explicit no-trade data-gap record for an unsynchronized/stepped/paused window."""

    started_at: Instant
    ended_at: Instant | None
    reason: str
    no_entry: bool = True

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "kind": "unsynchronized-interval",
            "started_at_ns": self.started_at.value_ns,
            "reason": self.reason,
            "no_entry": self.no_entry,
            "failure_id": CLOCK_BAND_FAILURE_IDS["unsynchronized"],
        }
        if self.ended_at is not None:
            body["ended_at_ns"] = self.ended_at.value_ns
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class SuspectWindow:
    """Wall-versus-monotonic divergence marked while the node must be stopped for a step."""

    detected_at_wall: Instant
    wall_delta_ns: int
    mono_delta_ns: int
    divergence_ns: int

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "kind": "suspect-window",
                "detected_at_wall_ns": self.detected_at_wall.value_ns,
                "wall_delta_ns": self.wall_delta_ns,
                "mono_delta_ns": self.mono_delta_ns,
                "divergence_ns": self.divergence_ns,
                "failure_id": CLOCK_BAND_FAILURE_IDS["step_suspect"],
                "no_entry": True,
            }
        )


@dataclass(frozen=True, slots=True)
class ClockBandDecision:
    """Result of one per-decision-cycle clock-band evaluation."""

    band: ClockBand
    sync_posture: SyncPosture
    measurement_kind: str
    drift_ns: int
    failure_id: str | None
    publish_evidence: bool
    silent_degradation: bool
    stand_down: bool
    unsynchronized_interval: UnsynchronizedInterval | None = None

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "band": self.band.value,
            "sync_posture": self.sync_posture.value,
            "measurement_kind": self.measurement_kind,
            "drift_ns": self.drift_ns,
            "publish_evidence": self.publish_evidence,
            "silent_degradation": self.silent_degradation,
            "stand_down": self.stand_down,
            "stand_down_trigger": STAND_DOWN_TRIGGER_CLOCK_HALT if self.stand_down else None,
        }
        if self.failure_id is not None:
            body["failure_id"] = self.failure_id
        if self.unsynchronized_interval is not None:
            body["unsynchronized_interval"] = dict(self.unsynchronized_interval.as_mapping())
        return MappingProxyType(body)


@dataclass
class WallMonotonicDivergenceDetector:
    """Detect a wall step against monotonic elapsed — marks a suspect window (TN-14)."""

    tolerance_ns: int
    _last_wall: Instant | None = None
    _last_mono: MonotonicReading | None = None
    suspect_windows: MutableSequence[SuspectWindow] = field(default_factory=list[SuspectWindow])

    @classmethod
    def try_create(cls, *, tolerance_ns: object) -> Result[WallMonotonicDivergenceDetector]:
        tol = _positive_ns(tolerance_ns, "tolerance_ns")
        if is_refusal(tol):
            return tol
        return Ok(cls(tolerance_ns=tol.value))

    def observe(
        self,
        *,
        wall: object,
        monotonic: object,
    ) -> Result[SuspectWindow | None]:
        """Feed one (wall, monotonic) pair; return a suspect window on divergence."""
        if not isinstance(wall, Instant):
            return invalid(
                "wall",
                "divergence observes an Instant",
                given=repr(type(wall).__name__),
            )
        if not isinstance(monotonic, MonotonicReading):
            return invalid(
                "monotonic",
                "divergence observes a MonotonicReading",
                given=repr(type(monotonic).__name__),
            )
        if self._last_wall is None or self._last_mono is None:
            self._last_wall = wall
            self._last_mono = monotonic
            return Ok(None)
        wall_delta = wall.value_ns - self._last_wall.value_ns
        elapsed = monotonic.elapsed_since(self._last_mono)
        if is_refusal(elapsed):
            return elapsed
        mono_delta = elapsed.value.value_ns
        divergence = abs(wall_delta - mono_delta)
        self._last_wall = wall
        self._last_mono = monotonic
        if divergence > self.tolerance_ns:
            window = SuspectWindow(
                detected_at_wall=wall,
                wall_delta_ns=wall_delta,
                mono_delta_ns=mono_delta,
                divergence_ns=divergence,
            )
            self.suspect_windows.append(window)
            return Ok(window)
        return Ok(None)


def measurements_named_apart() -> tuple[str, ...]:
    """The two TN-14 measurements — never substituted for one another."""
    return ("machine-versus-truth", "node-versus-broker-skew")


def broker_skew_is_not_latency() -> bool:
    """Node-versus-broker skew is never called latency (DEC-0199)."""
    return True


def evaluate_sync_posture(
    *,
    chrony_waitsync_passed: object,
    truth: object | None = None,
    thresholds: object | None = None,
    now: object | None = None,
) -> Result[SyncPosture]:
    """Fail-closed sync posture for preflight and live (no trade before sync)."""
    if not isinstance(chrony_waitsync_passed, bool):
        return invalid(
            "chrony_waitsync_passed",
            "chronyc waitsync posture is a bool",
            given=repr(chrony_waitsync_passed),
        )
    if not chrony_waitsync_passed:
        return Ok(SyncPosture.PREFLIGHT_BLOCKED)
    if truth is None:
        return Ok(SyncPosture.SYNCHRONIZED)
    if not isinstance(truth, MachineVersusTruth):
        return invalid(
            "truth",
            "live sync posture reads MachineVersusTruth when supplied",
            given=repr(type(truth).__name__),
        )
    if not truth.synchronized:
        return Ok(SyncPosture.UNSYNCHRONIZED)
    if thresholds is not None:
        if not isinstance(thresholds, ClockDriftThresholds):
            return invalid(
                "thresholds",
                "unsynchronized horizon uses ClockDriftThresholds",
                given=repr(type(thresholds).__name__),
            )
        if truth.sync_age_ns > thresholds.unsynchronized_after_ns:
            return Ok(SyncPosture.UNSYNCHRONIZED)
    del now  # reserved for interval stamping by the caller
    return Ok(SyncPosture.SYNCHRONIZED)


def record_unsynchronized_interval(
    *,
    started_at: object,
    reason: object,
    ended_at: object = None,
    sink: MutableSequence[UnsynchronizedInterval] | None = None,
) -> Result[UnsynchronizedInterval]:
    """Record an unsynchronized/stepped/paused window as an explicit data-gap."""
    if not isinstance(started_at, Instant):
        return invalid(
            "started_at",
            "unsynchronized intervals stamp an Instant start",
            given=repr(type(started_at).__name__),
        )
    end: Instant | None
    if ended_at is None:
        end = None
    elif isinstance(ended_at, Instant):
        end = ended_at
    else:
        return invalid(
            "ended_at",
            "unsynchronized interval end is an Instant or omitted",
            given=repr(type(ended_at).__name__),
        )
    token = clean_token(reason)
    if token is None:
        return invalid(
            "reason",
            "unsynchronized interval names a non-empty reason",
            given=repr(reason),
        )
    interval = UnsynchronizedInterval(
        started_at=started_at,
        ended_at=end,
        reason=token,
        no_entry=True,
    )
    if sink is not None:
        sink.append(interval)
    return Ok(interval)


def evaluate_clock_band(
    *,
    thresholds: object,
    truth: object,
    broker_skew: object | None = None,
    now: object | None = None,
) -> Result[ClockBandDecision]:
    """Evaluate ``ok | warn | no-new-entry | halt`` for one decision cycle.

    Machine-versus-truth drives the band. Broker skew is accepted only as a
    separately named measurement and never mixed into the truth offset. Warn
    publishes evidence; no-new-entry is entry-side only; halt requests stand-down.
    """
    if not isinstance(thresholds, ClockDriftThresholds):
        return invalid(
            "thresholds",
            "band evaluation requires ClockDriftThresholds from the resolved config",
            given=repr(type(thresholds).__name__),
        )
    if not isinstance(truth, MachineVersusTruth):
        return invalid(
            "truth",
            "band evaluation requires MachineVersusTruth (chrony)",
            given=repr(type(truth).__name__),
        )
    if broker_skew is not None and not isinstance(broker_skew, NodeVersusBrokerSkew):
        return invalid(
            "broker_skew",
            "broker skew is NodeVersusBrokerSkew or omitted — never merged into truth",
            given=repr(type(broker_skew).__name__),
        )

    posture = evaluate_sync_posture(
        chrony_waitsync_passed=truth.synchronized,
        truth=truth,
        thresholds=thresholds,
        now=now,
    )
    if is_refusal(posture):
        return posture

    if posture.value is not SyncPosture.SYNCHRONIZED:
        if not isinstance(now, Instant):
            return invalid(
                "now",
                "unsynchronized posture stamps the interval start from an Instant "
                "on the injected VPS clock",
                given=repr(type(now).__name__ if now is not None else None),
            )
        interval = UnsynchronizedInterval(
            started_at=now,
            ended_at=None,
            reason="chrony-unsynchronized",
            no_entry=True,
        )
        return Ok(
            ClockBandDecision(
                band=ClockBand.HALT,
                sync_posture=posture.value,
                measurement_kind="machine-versus-truth",
                drift_ns=truth.abs_offset_ns(),
                failure_id=CLOCK_BAND_FAILURE_IDS["unsynchronized"],
                publish_evidence=True,
                silent_degradation=True,
                stand_down=True,
                unsynchronized_interval=interval,
            )
        )

    drift = truth.abs_offset_ns()
    band = _band_for_drift(drift, thresholds)
    publish = band is not ClockBand.OK
    silent = band in {ClockBand.NO_NEW_ENTRY, ClockBand.HALT}
    stand_down = band is ClockBand.HALT
    failure = None if band is ClockBand.OK else CLOCK_BAND_FAILURE_IDS[band.value]
    # Broker skew remains evidence-only here; never auto-correct or rename as latency.
    del broker_skew
    return Ok(
        ClockBandDecision(
            band=band,
            sync_posture=SyncPosture.SYNCHRONIZED,
            measurement_kind="machine-versus-truth",
            drift_ns=drift,
            failure_id=failure,
            publish_evidence=publish,
            silent_degradation=silent,
            stand_down=stand_down,
        )
    )


def clock_band_entry_side_refused(band: ClockBand, *, act: object) -> bool:
    """True when ``band`` refuses an entry-side act for this cycle (L39)."""
    if band not in {ClockBand.NO_NEW_ENTRY, ClockBand.HALT}:
        return False
    token = str(act).strip().lower().replace("-", "_")
    return token in {
        "place_order",
        "risk_increasing_amend",
        "risk_increasing_amend_protection",
        "entry",
    }


def clock_band_preserves_protection(band: ClockBand, *, act: object) -> bool:
    """True when exits/protection remain enactable under ``band`` (L39)."""
    del band
    token = str(act).strip().lower().replace("-", "_")
    return token in {
        "cancel_order",
        "close_position",
        "close_all",
        "amend_protection",
        "risk_non_increasing_amend_protection",
        "close_full",
        "tighten_protective_stop",
        "flatten",
        "standing_protection_intent",
    }


def clock_band_requires_stand_down(band: ClockBand) -> bool:
    """Halt enters stand-down-alive; only operator resurrect leaves (TN-4)."""
    return band is ClockBand.HALT


def _band_for_drift(drift_ns: int, thresholds: ClockDriftThresholds) -> ClockBand:
    if drift_ns >= thresholds.halt_ns:
        return ClockBand.HALT
    if drift_ns >= thresholds.no_new_entry_ns:
        return ClockBand.NO_NEW_ENTRY
    if drift_ns >= thresholds.warn_ns:
        return ClockBand.WARN
    return ClockBand.OK


def _positive_ns(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return invalid(
            field,
            f"{field} is a positive int nanosecond duration from the resolved config",
            given=repr(value),
        )
    return Ok(value)


def _int_ns(value: object, field: str, *, allow_negative: bool) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return invalid(field, f"{field} is an int nanosecond quantity", given=repr(value))
    if not allow_negative and value < 0:
        return invalid(field, f"{field} is a non-negative int nanosecond quantity", given=value)
    return Ok(value)
