"""ONE event-slice loop with six pinned identity-bearing sub-phases (B-2).

Per slice the sub-phases run in :data:`SUBPHASES` order. Changing that order is
identity-bearing. Within a phase, instruments process in the stream-set
declaration order from the resolved run-config. A new intent minted in
sub-phase 5 is never eligible to fill against this slice's path — it rests for
a later slice. Higher-BarSpec bars derive from the finest declared base stream
and emit only on a completed boundary; a forming bar is never visible or
actionable. Warm-up is in-loop with trading locked for the split-manifest
embargo observation count; acting during warm-up is a typed policy rejection.
Cancel and time/memory limits are cooperative at slice boundaries and return
a typed ``aborted`` refusal — never a partial governed result. ``run`` is a
pure function: it writes no log and no ledger. A completed run under a
resolved run-config mints a CT-32 fingerprint witness (no HTML, no charts).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Final, Protocol, cast, runtime_checkable

from qmf.core.chrono import Clock, Duration, Instant, Interval
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.risk.performance import PerformanceResult

from qmb._refuse import clean_token, invalid
from qmb.config.compiler import ResolvedRunConfig
from qmb.results.ct32 import (
    CONCURRENCY_IS_SCHEDULING_ONLY,
    RESULT_CONTRACT,
    mint_run_performance_result,
    require_reproduced_fingerprint,
)
from qmb.runloop.bars import (
    COMPLETED_BOUNDARY_ONLY,
    COMPLETENESS_COMPLETED,
    COMPLETENESS_FORMING,
    FORMING_BAR_ACTIONABLE,
    FORMING_BAR_VISIBLE,
    LOOKAHEAD_PREVENTION_INDEPENDENT_OF_GAP_0048,
    DerivedBar,
    FormingBarState,
    SameSliceConsumption,
    SeriesSample,
    consume_stream_plans,
)
from qmb.runloop.frontier import (
    CLOCK_DOES_NOT_CHOOSE_WORLD,
    FrontierClock,
    StreamNextEmit,
    advance_frontier,
)
from qmb.runloop.observe import (
    CANCEL_AT,
    MEMORY_LIMIT_KEY,
    PARTIAL_GOVERNED_RESULT_ON_ABORT,
    TERMINAL_COMPLETE,
    TIME_LIMIT_KEY,
    CancelToken,
    LimitProbe,
    ProgressObserver,
    RunLimits,
    RunProgress,
    check_slice_boundary,
    limits_from_config,
)
from qmb.runloop.warmup import (
    EMBARGO_KEY,
    PRESEED_IS_WARMUP,
    WARMUP_ADDS_SECOND_WINDOW,
    WARMUP_MECHANISM,
    WARMUP_UNIT,
    SplitEmbargo,
    WarmupProgress,
    embargo_from_config,
    guard_trading,
    trading_evidence_range,
)

__all__ = [
    "LOOP_KIND",
    "SAME_SLICE_NEW_INTENT_FILL",
    "STREAM_ROLE_DATA_ONLY",
    "STREAM_ROLE_TRADING",
    "STREAM_SET_KEY",
    "SUBPHASES",
    "DeclaredStream",
    "EventSlice",
    "LoopOutcome",
    "RestingIntent",
    "SilentSliceHandler",
    "SliceHandler",
    "SliceObservation",
    "SliceOutcome",
    "StreamSet",
    "SubphaseTrace",
    "fingerprint_loop",
    "frontier_clock_name",
    "loop_identity",
    "reproduce_run",
    "run",
    "run_slice",
    "stream_set_from_config",
]

LOOP_KIND: Final[str] = "event-slice"
SUBPHASES: Final[tuple[str, ...]] = (
    "frontier-advance",
    "scheduled-position-events",
    "resting-orders",
    "closed-data-indicators-structure",
    "strategy-callbacks",
    "new-intents-rest",
)
SAME_SLICE_NEW_INTENT_FILL: Final[bool] = False
STREAM_SET_KEY: Final[str] = "stream_set"
STREAM_ROLE_TRADING: Final[str] = "trading"
STREAM_ROLE_DATA_ONLY: Final[str] = "data-only"
_LEGAL_ROLES: Final[frozenset[str]] = frozenset({STREAM_ROLE_TRADING, STREAM_ROLE_DATA_ONLY})
_INSTRUMENT_ORDER: Final[str] = "stream-set-declaration"


def frontier_clock_name() -> str:
    """Qualified name of the injected frontier clock protocol (AD-8)."""
    return f"{Clock.__module__}.{Clock.__qualname__}"


def loop_identity() -> dict[str, object]:
    """Identity-bearing loop fields. Package SemVer is omitted."""
    return {
        "loop_kind": LOOP_KIND,
        "frontier_clock": frontier_clock_name(),
        "subphases": SUBPHASES,
        "clock_chooses_world": False,
        "clock_does_not_choose_world": CLOCK_DOES_NOT_CHOOSE_WORLD,
        "same_slice_new_intent_fill": SAME_SLICE_NEW_INTENT_FILL,
        "instrument_order": _INSTRUMENT_ORDER,
        "closed_data_only": True,
        "completed_boundary_only": COMPLETED_BOUNDARY_ONLY,
        "forming_bar_actionable": FORMING_BAR_ACTIONABLE,
        "forming_bar_visible": FORMING_BAR_VISIBLE,
        "higher_barspec_from_finest_base": True,
        "same_series_bars_and_fills": True,
        "lookahead_prevention_independent_of_gap_0048": (
            LOOKAHEAD_PREVENTION_INDEPENDENT_OF_GAP_0048
        ),
        "preseed_is_warmup": PRESEED_IS_WARMUP,
        "trading_locked_during_warmup": True,
        "warmup_adds_second_window": WARMUP_ADDS_SECOND_WINDOW,
        "warmup_mechanism": WARMUP_MECHANISM,
        "warmup_unit": WARMUP_UNIT,
        "cancel_at": CANCEL_AT,
        "concurrency_is_scheduling_only": CONCURRENCY_IS_SCHEDULING_ONLY,
        "partial_governed_result_on_abort": PARTIAL_GOVERNED_RESULT_ON_ABORT,
        "pure_run_independent_of_siblings": True,
    }


def fingerprint_loop() -> Result[Fingerprint]:
    """``fp1`` over :func:`loop_identity`. Permuting :data:`SUBPHASES` changes it."""
    return fingerprint(loop_identity())


@dataclass(frozen=True, slots=True)
class DeclaredStream:
    """One stream-set member. Declaration order is identity (B-12)."""

    stream_id: str
    instrument_id: str
    role: str = STREAM_ROLE_TRADING

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        return {
            "instrument_id": self.instrument_id,
            "role": self.role,
            "stream_id": self.stream_id,
        }

    @classmethod
    def try_create(
        cls,
        stream_id: object,
        instrument_id: object = None,
        role: object = STREAM_ROLE_TRADING,
    ) -> Result[DeclaredStream]:
        """Validate and build one declared stream."""
        token = clean_token(stream_id)
        if token is None:
            return invalid(
                "stream_id",
                "a declared stream names a non-empty stream id",
                given=repr(stream_id),
            )
        instrument = token if instrument_id is None else clean_token(instrument_id)
        if instrument is None:
            return invalid(
                "instrument_id",
                "a declared stream names a non-empty instrument id",
                given=repr(instrument_id),
            )
        role_token = clean_token(role)
        if role_token is None or role_token not in _LEGAL_ROLES:
            return invalid(
                "role",
                "a declared stream role is trading or data-only",
                given=repr(role),
                allowed=sorted(_LEGAL_ROLES),
            )
        return Ok(cls(stream_id=token, instrument_id=instrument, role=role_token))


@dataclass(frozen=True, slots=True)
class StreamSet:
    """Ordered stream-set declaration. Order is identity content (B-2, B-12)."""

    streams: tuple[DeclaredStream, ...]

    @property
    def stream_ids(self) -> tuple[str, ...]:
        """Declaration-order stream ids — the per-phase instrument order."""
        return tuple(item.stream_id for item in self.streams)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Declaration order is significant."""
        return {
            "class": "stream-set",
            "streams": [item.fp1_identity() for item in self.streams],
        }

    @classmethod
    def try_create(cls, streams: object) -> Result[StreamSet]:
        """Validate an ordered stream-set declaration."""
        if isinstance(streams, StreamSet):
            return Ok(streams)
        if isinstance(streams, (str, bytes)) or not isinstance(streams, Sequence):
            return invalid(
                "stream_set",
                "a stream set is a sequence of declared streams; declaration "
                "order is identity content of the resolved run-config (B-12)",
                given=repr(type(streams).__name__),
            )
        parsed: list[DeclaredStream] = []
        seen: set[str] = set()
        for index, raw in enumerate(cast("Sequence[object]", streams)):
            member = _coerce_declared_stream(raw)
            if is_refusal(member):
                return member
            stream_id = member.value.stream_id
            if stream_id in seen:
                return invalid(
                    "stream_set",
                    "stream-set declaration order names each stream id once",
                    index=index,
                    stream_id=stream_id,
                )
            seen.add(stream_id)
            parsed.append(member.value)
        if not parsed:
            return invalid(
                "stream_set",
                "a run declares one or more streams; an empty stream set cannot "
                "drive an event slice (B-12)",
            )
        return Ok(cls(streams=tuple(parsed)))


def stream_set_from_config(config: object) -> Result[StreamSet]:
    """Read declaration-order stream set from the resolved run-config (B-12)."""
    if not isinstance(config, ResolvedRunConfig):
        return invalid(
            "config",
            "instrument order is the stream-set declaration on a resolved run-config",
            given=repr(type(config).__name__),
        )
    raw = config.keys.get(STREAM_SET_KEY)
    if raw is None:
        return invalid(
            STREAM_SET_KEY,
            "the resolved run-config declares its stream set; declaration order "
            "is identity content (B-2, B-12)",
        )
    return StreamSet.try_create(raw)


@dataclass(frozen=True, slots=True)
class SliceObservation:
    """One stream's observation at a slice instant.

    ``closed=False`` is forming: indicators and structure never see it (B-2).
    """

    stream_id: str
    instant: Instant
    closed: bool = True

    @property
    def completeness(self) -> str:
        """Inspectable completeness. Forming is ``closed=False`` (B-2)."""
        return COMPLETENESS_COMPLETED if self.closed else COMPLETENESS_FORMING

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        return {
            "closed": self.closed,
            "completeness": self.completeness,
            "instant_ns": self.instant.value_ns,
            "stream_id": self.stream_id,
        }

    @classmethod
    def try_create(
        cls,
        stream_id: object,
        instant: object,
        closed: object = True,
    ) -> Result[SliceObservation]:
        """Validate one slice observation."""
        token = clean_token(stream_id)
        if token is None:
            return invalid(
                "stream_id",
                "a slice observation names a non-empty stream id",
                given=repr(stream_id),
            )
        if not isinstance(instant, Instant):
            return invalid(
                "instant",
                "a slice observation carries an Instant",
                given=repr(type(instant).__name__),
            )
        if not isinstance(closed, bool):
            return invalid(
                "closed",
                "observation completeness is a bool; forming is closed=False (B-2)",
                given=repr(closed),
            )
        return Ok(cls(stream_id=token, instant=instant, closed=closed))


@dataclass(frozen=True, slots=True)
class EventSlice:
    """Time-ordered observations that share one frontier instant."""

    observations: tuple[SliceObservation, ...]

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        return {
            "class": "event-slice",
            "observations": [item.fp1_identity() for item in self.observations],
        }

    @classmethod
    def try_create(cls, observations: object) -> Result[EventSlice]:
        """Validate one event slice. Mixed instants are refused."""
        if isinstance(observations, EventSlice):
            return Ok(observations)
        if isinstance(observations, (str, bytes)) or not isinstance(observations, Sequence):
            return invalid(
                "event_slice",
                "an event slice is a sequence of stream observations at one Instant",
                given=repr(type(observations).__name__),
            )
        parsed: list[SliceObservation] = []
        seen: set[str] = set()
        instant_ns: int | None = None
        for index, raw in enumerate(cast("Sequence[object]", observations)):
            item = _coerce_observation(raw)
            if is_refusal(item):
                return item
            obs = item.value
            if obs.stream_id in seen:
                return invalid(
                    "event_slice",
                    "a slice names each stream id once",
                    index=index,
                    stream_id=obs.stream_id,
                )
            if instant_ns is None:
                instant_ns = obs.instant.value_ns
            elif obs.instant.value_ns != instant_ns:
                return invalid(
                    "event_slice",
                    "every observation in one event slice shares one Instant; "
                    "mixed instants are separate slices",
                    index=index,
                    instant_ns=obs.instant.value_ns,
                    slice_instant_ns=instant_ns,
                )
            seen.add(obs.stream_id)
            parsed.append(obs)
        if not parsed:
            return invalid(
                "event_slice",
                "an event slice carries at least one stream observation so the "
                "frontier can advance",
            )
        return Ok(cls(observations=tuple(parsed)))


@dataclass(frozen=True, slots=True)
class RestingIntent:
    """An intent token that rests until a later slice may fill it (B-2)."""

    intent_id: str
    stream_id: str

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        return {"intent_id": self.intent_id, "stream_id": self.stream_id}

    @classmethod
    def try_create(cls, intent_id: object, stream_id: object) -> Result[RestingIntent]:
        """Validate one resting intent token."""
        iid = clean_token(intent_id)
        if iid is None:
            return invalid(
                "intent_id",
                "a resting intent names a non-empty intent id",
                given=repr(intent_id),
            )
        sid = clean_token(stream_id)
        if sid is None:
            return invalid(
                "stream_id",
                "a resting intent names a non-empty stream id",
                given=repr(stream_id),
            )
        return Ok(cls(intent_id=iid, stream_id=sid))


@dataclass(frozen=True, slots=True)
class SubphaseTrace:
    """One sub-phase of one slice. Instrument order is stream-set declaration."""

    subphase: str
    instrument_order: tuple[str, ...]
    actions: tuple[str, ...]

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        return {
            "actions": list(self.actions),
            "instrument_order": list(self.instrument_order),
            "subphase": self.subphase,
        }


@dataclass(frozen=True, slots=True)
class SliceOutcome:
    """Pure result of processing one event slice through :data:`SUBPHASES`."""

    frontier: Instant
    trace: tuple[SubphaseTrace, ...]
    filled: tuple[str, ...]
    minted: tuple[str, ...]
    ineligible: tuple[str, ...]
    resting: tuple[RestingIntent, ...]
    emitted_bars: tuple[DerivedBar, ...] = ()
    forming: tuple[FormingBarState, ...] = ()
    fill_path: tuple[SeriesSample, ...] = ()
    series_fp1: tuple[str, ...] = ()
    is_warming_up: bool = False
    warmup: WarmupProgress | None = None

    def subphase_order(self) -> tuple[str, ...]:
        """Sub-phase names in the order they ran."""
        return tuple(step.subphase for step in self.trace)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        content: dict[str, object] = {
            "filled": list(self.filled),
            "frontier_ns": self.frontier.value_ns,
            "ineligible": list(self.ineligible),
            "is_warming_up": self.is_warming_up,
            "minted": list(self.minted),
            "resting": [item.fp1_identity() for item in self.resting],
            "trace": [item.fp1_identity() for item in self.trace],
        }
        if self.emitted_bars:
            content["emitted_bars"] = [item.fp1_identity() for item in self.emitted_bars]
        if self.forming:
            content["forming"] = [item.fp1_identity() for item in self.forming]
        if self.fill_path:
            content["fill_path"] = [item.fp1_identity() for item in self.fill_path]
        if self.series_fp1:
            content["series_fp1"] = list(self.series_fp1)
        if self.warmup is not None:
            content["warmup"] = self.warmup.fp1_identity()
        return content


@dataclass(frozen=True, slots=True)
class LoopOutcome:
    """Pure result of the event-slice loop. Not a ledger line.

    A completed run under a resolved run-config carries the CT-32
    ``performance_result`` used as the fingerprint witness. The loop-outcome
    ``fp1`` does not fold that artifact in (the CT-32 cites it as an input).
    Abort never emits a partial governed result.
    """

    slices: tuple[SliceOutcome, ...]
    resting: tuple[RestingIntent, ...]
    filled: tuple[str, ...]
    stream_order: tuple[str, ...]
    warmup: WarmupProgress
    evidence_range: Interval
    data_points_processed: int = 0
    performance_result: PerformanceResult | None = None

    @property
    def is_warming_up(self) -> bool:
        """True when the run ended still inside the embargo (trading locked)."""
        return self.warmup.is_warming_up

    @property
    def self_assessment(self) -> Mapping[str, object]:
        """Returned with the outcome; never written to a log or ledger (B-4)."""
        payload: dict[str, object] = {
            "cancel_at": CANCEL_AT,
            "closed_data_only": True,
            "completed_boundary_only": COMPLETED_BOUNDARY_ONLY,
            "concurrency_is_scheduling_only": CONCURRENCY_IS_SCHEDULING_ONLY,
            "data_points_processed": self.data_points_processed,
            "evidence_covers_warmup": False,
            "forming_bar_actionable": FORMING_BAR_ACTIONABLE,
            "forming_bar_visible": FORMING_BAR_VISIBLE,
            "is_warming_up": self.is_warming_up,
            "lookahead_prevention_independent_of_gap_0048": (
                LOOKAHEAD_PREVENTION_INDEPENDENT_OF_GAP_0048
            ),
            "loop_kind": LOOP_KIND,
            "partial_governed_result_on_abort": PARTIAL_GOVERNED_RESULT_ON_ABORT,
            "preseed_is_warmup": PRESEED_IS_WARMUP,
            "same_slice_new_intent_fill": SAME_SLICE_NEW_INTENT_FILL,
            "slice_count": len(self.slices),
            "subphases": list(SUBPHASES),
            "terminal": TERMINAL_COMPLETE,
            "warmup_adds_second_window": WARMUP_ADDS_SECOND_WINDOW,
            "warmup_mechanism": WARMUP_MECHANISM,
            "warmup_unit": WARMUP_UNIT,
        }
        if self.performance_result is not None:
            stamped = self.performance_result.fingerprint()
            payload["result_contract"] = RESULT_CONTRACT
            if not is_refusal(stamped):
                payload["ct32_fingerprint"] = stamped.value.value
        return MappingProxyType(payload)

    def ct32_fingerprint(self) -> Result[Fingerprint]:
        """The CT-32 ``fp1`` when this outcome minted a governed result."""
        if self.performance_result is None:
            return invalid(
                "performance_result",
                "CT-32 is minted when run() completes under a resolved run-config; "
                "an aborted or config-less loop emits no governed result",
                result_contract=RESULT_CONTRACT,
            )
        return self.performance_result.fingerprint()

    def fp1_identity(self) -> dict[str, object]:
        """Canonical loop-outcome identity. The CT-32 artifact is not folded in."""
        return {
            "class": "event-slice-loop-outcome",
            "data_points_processed": self.data_points_processed,
            "evidence_range": self.evidence_range.fp1_identity(),
            "filled": list(self.filled),
            "is_warming_up": self.is_warming_up,
            "resting": [item.fp1_identity() for item in self.resting],
            "slice_count": len(self.slices),
            "slices": [item.fp1_identity() for item in self.slices],
            "stream_order": list(self.stream_order),
            "subphases": list(SUBPHASES),
            "warmup": self.warmup.fp1_identity(),
        }


@runtime_checkable
class SliceHandler(Protocol):
    """Injected per-slice ports. Later stories bind financing, fill, and CT-16/17."""

    def update_stream(
        self,
        stream_id: str,
        observation: SliceObservation | None,
        frontier: Instant,
    ) -> Result[None]:  # pragma: no cover - protocol seam
        """Sub-phase 1 stream update after frontier advance."""
        ...

    def scheduled_position_event(
        self,
        stream_id: str,
        frontier: Instant,
    ) -> Result[None]:  # pragma: no cover - protocol seam
        """Sub-phase 2 financing / scheduled position-level events."""
        ...

    def execute_resting(
        self,
        intent: RestingIntent,
        observation: SliceObservation | None,
        frontier: Instant,
    ) -> Result[bool]:  # pragma: no cover - protocol seam
        """Sub-phase 3: ``True`` fills the eligible resting intent against this path."""
        ...

    def update_closed_data(
        self,
        stream_id: str,
        observation: SliceObservation,
        frontier: Instant,
    ) -> Result[None]:  # pragma: no cover - protocol seam
        """Sub-phase 4: indicators/structure on closed data only."""
        ...

    def mint_intents(
        self,
        stream_id: str,
        frontier: Instant,
    ) -> Result[object]:  # pragma: no cover - protocol seam
        """Sub-phase 5: strategy callbacks return zero-or-more resting intent tokens."""
        ...


@dataclass(frozen=True, slots=True)
class SilentSliceHandler:
    """Default ports: no financing side effects, no fills, no minted intents."""

    def update_stream(
        self,
        stream_id: str,
        observation: SliceObservation | None,
        frontier: Instant,
    ) -> Result[None]:
        del stream_id, observation, frontier
        return Ok(None)

    def scheduled_position_event(self, stream_id: str, frontier: Instant) -> Result[None]:
        del stream_id, frontier
        return Ok(None)

    def execute_resting(
        self,
        intent: RestingIntent,
        observation: SliceObservation | None,
        frontier: Instant,
    ) -> Result[bool]:
        del intent, observation, frontier
        return Ok(False)

    def update_closed_data(
        self,
        stream_id: str,
        observation: SliceObservation,
        frontier: Instant,
    ) -> Result[None]:
        del stream_id, observation, frontier
        return Ok(None)

    def mint_intents(self, stream_id: str, frontier: Instant) -> Result[object]:
        del stream_id, frontier
        return Ok(())


def run_slice(
    event_slice: object,
    *,
    stream_set: object,
    current_frontier: object = None,
    clock: object = None,
    handler: object = None,
    resting: object = (),
    series: object = None,
    bar_plan: object = None,
    embargo: object = None,
    warmup: object = None,
) -> Result[SliceOutcome]:
    """Process one event slice through the pinned :data:`SUBPHASES` order (B-2).

    Resting intents present at slice start may fill in sub-phase 3. Intents
    minted in sub-phase 5 are recorded as ineligible for this slice's path and
    rest for a later slice. When ``series`` and ``bar_plan`` are supplied,
    higher-BarSpec bars derive from the finest base stream in sub-phase 1 and
    emit only on a completed boundary. Warm-up uses this same loop with trading
    locked for the split-manifest embargo observation count. Domain failure is
    a typed refusal, returned never raised. Pure: no log, no ledger write.
    """
    declared = StreamSet.try_create(stream_set)
    if is_refusal(declared):
        return declared
    slice_ = EventSlice.try_create(event_slice)
    if is_refusal(slice_):
        return slice_
    bound = _bind_observations(declared.value, slice_.value)
    if is_refusal(bound):
        return bound
    observations = bound.value
    intents = _as_resting_tuple(resting, declared.value)
    if is_refusal(intents):
        return intents
    ports = _as_handler(handler)
    if is_refusal(ports):
        return ports
    if current_frontier is not None and not isinstance(current_frontier, Instant):
        return invalid(
            "current_frontier",
            "the current frontier is an Instant or None",
            given=repr(type(current_frontier).__name__),
        )
    pulled = _pull_frontier(
        clock=clock,
        current=current_frontier,
        observations=slice_.value.observations,
    )
    if is_refusal(pulled):
        return pulled
    derived = _derive_if_requested(
        series=series,
        bar_plan=bar_plan,
        frontier=pulled.value,
        stream_ids=declared.value.stream_ids,
    )
    if is_refusal(derived):
        return derived
    progress = _resolve_warmup(embargo=embargo, warmup=warmup, config=None)
    if is_refusal(progress):
        return progress
    acc = _Acc(
        frontier=pulled.value,
        remaining=list(intents.value),
        filled=[],
        minted=[],
        traces=[],
        observations=observations,
        stream_ids=declared.value.stream_ids,
        handler=ports.value,
        consumptions=derived.value,
        warmup=progress.value,
        slice_warming=progress.value.is_warming_up,
    )
    for name in SUBPHASES:
        stepped = _run_one_phase(name, acc)
        if is_refusal(stepped):
            return stepped
        acc = stepped.value
    advanced = acc.warmup.advance(_closed_observation_count(acc.observations))
    if is_refusal(advanced):
        return advanced
    minted_ids = tuple(item.intent_id for item in acc.minted)
    emitted = tuple(bar for item in acc.consumptions for bar in item.emitted)
    forming = tuple(state for item in acc.consumptions for state in item.forming)
    fill_path = tuple(sample for item in acc.consumptions for sample in item.fill_path)
    series_fp1 = tuple(item.series_fp1 for item in acc.consumptions)
    return Ok(
        SliceOutcome(
            frontier=acc.frontier,
            trace=tuple(acc.traces),
            filled=tuple(acc.filled),
            minted=minted_ids,
            ineligible=minted_ids,
            resting=tuple(acc.remaining + acc.minted),
            emitted_bars=emitted,
            forming=forming,
            fill_path=fill_path,
            series_fp1=series_fp1,
            is_warming_up=acc.slice_warming,
            warmup=advanced.value,
        )
    )


def run(
    *,
    slices: object,
    stream_set: object = None,
    config: object = None,
    clock: object = None,
    handler: object = None,
    initial_resting: object = (),
    series: object = None,
    bar_plan: object = None,
    embargo: object = None,
    cancel: object = None,
    observer: object = None,
    limits: object = None,
    probe: object = None,
) -> Result[LoopOutcome]:
    """PURE event-slice loop (B-2, B-4, B-5).

    Consumes time-ordered event slices and the stream-set declaration order
    (from the resolved run-config when ``config`` is supplied). Warm-up is the
    same loop with trading locked for the split-manifest embargo observation
    count. A signalled cancel token, or an in-loop time/memory limit breach,
    stops the loop at the next slice boundary and returns a typed ``aborted``
    refusal — never a partial governed result. Progress (data-points-processed
    and ``is_warming_up``) is published to the caller-owned observer. Writes no
    log and no ledger. The same underlying series is replayed as-of each
    frontier so later prints cannot complete an earlier bar. A resolved
    run-config mints a CT-32 fingerprint witness; concurrency is scheduling
    only and does not enter identity.
    """
    declared = _resolve_stream_set(stream_set=stream_set, config=config)
    if is_refusal(declared):
        return declared
    events = _as_slice_sequence(slices)
    if is_refusal(events):
        return events
    ports = _as_handler(handler)
    if is_refusal(ports):
        return ports
    if clock is not None and not isinstance(clock, FrontierClock):
        return invalid(
            "clock",
            "the loop advances an injected FrontierClock, or the pure "
            "advance_frontier pull when clock is omitted (B-2)",
            given=repr(type(clock).__name__),
        )
    resting_tokens = _as_resting_tuple(initial_resting, declared.value)
    if is_refusal(resting_tokens):
        return resting_tokens
    progress = _resolve_warmup(embargo=embargo, warmup=None, config=config)
    if is_refusal(progress):
        return progress
    token = _as_cancel_token(cancel)
    if is_refusal(token):
        return token
    sink = _as_observer(observer)
    if is_refusal(sink):
        return sink
    bound_limits = _resolve_limits(limits=limits, config=config)
    if is_refusal(bound_limits):
        return bound_limits
    meter = _as_probe(probe, bound_limits.value)
    if is_refusal(meter):
        return meter
    current: Instant | None = None if clock is None else clock.current
    resting = resting_tokens.value
    outcomes: list[SliceOutcome] = []
    filled: list[str] = []
    warmup = progress.value
    data_points = 0
    published = _progress_at(
        data_points_processed=0,
        slices_completed=0,
        is_warming_up=warmup.is_warming_up,
        frontier=None,
        elapsed=None,
    )
    if is_refusal(published):
        return published
    watching = published.value
    noted = _publish(sink.value, watching)
    if is_refusal(noted):
        return noted
    for event in events.value:
        boundary = check_slice_boundary(
            cancel=token.value,
            limits=bound_limits.value,
            probe=meter.value,
            progress=watching,
        )
        if is_refusal(boundary):
            return boundary
        outcome = run_slice(
            event,
            stream_set=declared.value,
            current_frontier=current,
            clock=clock,
            handler=ports.value,
            resting=resting,
            series=series,
            bar_plan=bar_plan,
            warmup=warmup,
        )
        if is_refusal(outcome):
            return outcome
        done = outcome.value
        outcomes.append(done)
        current = done.frontier
        resting = done.resting
        filled.extend(done.filled)
        if done.warmup is not None:
            warmup = done.warmup
        data_points += len(event.observations)
        published = _progress_at(
            data_points_processed=data_points,
            slices_completed=len(outcomes),
            is_warming_up=warmup.is_warming_up,
            frontier=done.frontier,
            elapsed=boundary.value,
        )
        if is_refusal(published):
            return published
        watching = published.value
        noted = _publish(sink.value, watching)
        if is_refusal(noted):
            return noted
    spanned = trading_evidence_range(
        tuple(item.frontier for item in outcomes if not item.is_warming_up),
        empty_at=outcomes[-1].frontier,
    )
    if is_refusal(spanned):
        return spanned
    outcome = LoopOutcome(
        slices=tuple(outcomes),
        resting=resting,
        filled=tuple(filled),
        stream_order=declared.value.stream_ids,
        warmup=warmup,
        evidence_range=spanned.value,
        data_points_processed=data_points,
    )
    if not isinstance(config, ResolvedRunConfig):
        return Ok(outcome)
    minted = mint_run_performance_result(
        config,
        evidence_range=outcome.evidence_range,
        stream_order=outcome.stream_order,
        slice_count=len(outcome.slices),
        filled_count=len(outcome.filled),
        resting_count=len(outcome.resting),
        data_points_processed=outcome.data_points_processed,
        outcome_identity=outcome.fp1_identity(),
    )
    if is_refusal(minted):
        return minted
    return Ok(replace(outcome, performance_result=minted.value))


def reproduce_run(
    *,
    run_id: object,
    config: object,
    expected_fingerprint: object,
    slices: object,
    stream_set: object = None,
    clock: object = None,
    handler: object = None,
    initial_resting: object = (),
    series: object = None,
    bar_plan: object = None,
    embargo: object = None,
    cancel: object = None,
    observer: object = None,
    limits: object = None,
    probe: object = None,
) -> Result[PerformanceResult]:
    """Re-run ``run_id`` under its resolved config and require the CT-32 fingerprint.

    The run id IS the resolved-config fingerprint (B-3). A completed re-run
    that does not reproduce ``expected_fingerprint`` is a typed ``policy
    rejection`` (FM-11). Abort still returns the aborted refusal and never a
    partial governed result. Pure: no log, no ledger.
    """
    if not isinstance(config, ResolvedRunConfig):
        return invalid(
            "config",
            "reproduction re-runs under a resolved run-config; the config "
            "fingerprint is the run-id root (B-3, FM-11)",
            given=repr(type(config).__name__),
        )
    if not isinstance(run_id, Fingerprint):
        return invalid(
            "run_id",
            "the run id is the resolved-config fingerprint",
            given=repr(type(run_id).__name__),
        )
    if run_id != config.fingerprint:
        return invalid(
            "run_id",
            "the run id is the resolved-config fingerprint; reproducing under a "
            "different config is a caller mistake, not a fingerprint mismatch",
            config_fingerprint=config.fingerprint.value,
            run_id=run_id.value,
        )
    outcome = run(
        slices=slices,
        stream_set=stream_set,
        config=config,
        clock=clock,
        handler=handler,
        initial_resting=initial_resting,
        series=series,
        bar_plan=bar_plan,
        embargo=embargo,
        cancel=cancel,
        observer=observer,
        limits=limits,
        probe=probe,
    )
    if is_refusal(outcome):
        return outcome
    stamped = outcome.value.ct32_fingerprint()
    if is_refusal(stamped):
        return stamped
    matched = require_reproduced_fingerprint(
        expected_fingerprint,
        stamped.value,
        run_id=run_id,
    )
    if is_refusal(matched):
        return matched
    result = outcome.value.performance_result
    if result is None:
        return invalid(
            "performance_result",
            "a reproduced run under a resolved config must mint a CT-32 artifact",
            result_contract=RESULT_CONTRACT,
        )
    return Ok(result)


@dataclass(slots=True)
class _Acc:
    frontier: Instant
    remaining: list[RestingIntent]
    filled: list[str]
    minted: list[RestingIntent]
    traces: list[SubphaseTrace]
    observations: Mapping[str, SliceObservation | None]
    stream_ids: tuple[str, ...]
    handler: SliceHandler
    consumptions: tuple[SameSliceConsumption, ...]
    warmup: WarmupProgress
    slice_warming: bool


def _run_one_phase(name: str, acc: _Acc) -> Result[_Acc]:
    """Dispatch one pinned sub-phase. Unknown names refuse closed (AR-57)."""
    if name == "frontier-advance":
        return _phase_frontier_advance(acc)
    if name == "scheduled-position-events":
        return _phase_scheduled(acc)
    if name == "resting-orders":
        return _phase_resting_orders(acc)
    if name == "closed-data-indicators-structure":
        return _phase_closed_data(acc)
    if name == "strategy-callbacks":
        return _phase_strategy(acc)
    if name == "new-intents-rest":
        return _phase_new_intents_rest(acc)
    return invalid(
        "subphases",
        "every SUBPHASES entry must have a runner; changing the pinned order "
        "is identity-bearing (AR-57, B-2)",
        given=name,
        pinned=list(SUBPHASES),
    )


def _phase_frontier_advance(acc: _Acc) -> Result[_Acc]:
    actions: list[str] = []
    derived = {item.stream_id: item for item in acc.consumptions}
    for stream_id in acc.stream_ids:
        observation = acc.observations[stream_id]
        updated = acc.handler.update_stream(stream_id, observation, acc.frontier)
        if is_refusal(updated):
            return updated
        actions.append(f"empty:{stream_id}" if observation is None else f"update:{stream_id}")
        consumption = derived.get(stream_id)
        if consumption is None:
            continue
        if consumption.emitted:
            actions.append(f"emit-completed:{stream_id}")
        if consumption.forming:
            actions.append(f"hold-forming:{stream_id}")
    acc.traces.append(_trace("frontier-advance", acc.stream_ids, actions))
    return Ok(acc)


def _phase_scheduled(acc: _Acc) -> Result[_Acc]:
    actions: list[str] = []
    for stream_id in acc.stream_ids:
        scheduled = acc.handler.scheduled_position_event(stream_id, acc.frontier)
        if is_refusal(scheduled):
            return scheduled
        actions.append(f"scheduled:{stream_id}")
    acc.traces.append(_trace("scheduled-position-events", acc.stream_ids, actions))
    return Ok(acc)


def _phase_resting_orders(acc: _Acc) -> Result[_Acc]:
    actions: list[str] = []
    kept: list[RestingIntent] = []
    for stream_id in acc.stream_ids:
        observation = acc.observations[stream_id]
        for intent in [item for item in acc.remaining if item.stream_id == stream_id]:
            filled = acc.handler.execute_resting(intent, observation, acc.frontier)
            if is_refusal(filled):
                return filled
            if filled.value:
                locked = guard_trading(is_warming_up=acc.slice_warming, action="fill")
                if is_refusal(locked):
                    return locked
                acc.filled.append(intent.intent_id)
                actions.append(f"fill:{intent.intent_id}")
            else:
                kept.append(intent)
                actions.append(f"no-fill:{intent.intent_id}")
    acc.remaining = kept
    acc.traces.append(_trace("resting-orders", acc.stream_ids, actions))
    return Ok(acc)


def _phase_closed_data(acc: _Acc) -> Result[_Acc]:
    actions: list[str] = []
    for stream_id in acc.stream_ids:
        observation = acc.observations[stream_id]
        if observation is None:
            actions.append(f"empty:{stream_id}")
            continue
        if not observation.closed:
            actions.append(f"skip-forming:{stream_id}")
            continue
        updated = acc.handler.update_closed_data(stream_id, observation, acc.frontier)
        if is_refusal(updated):
            return updated
        actions.append(f"closed:{stream_id}")
    acc.traces.append(_trace("closed-data-indicators-structure", acc.stream_ids, actions))
    return Ok(acc)


def _phase_strategy(acc: _Acc) -> Result[_Acc]:
    actions: list[str] = []
    known = {item.intent_id for item in acc.remaining}
    known.update(acc.filled)
    known.update(item.intent_id for item in acc.minted)
    for stream_id in acc.stream_ids:
        minted = acc.handler.mint_intents(stream_id, acc.frontier)
        if is_refusal(minted):
            return minted
        tokens = _as_resting_tuple(minted.value, None)
        if is_refusal(tokens):
            return tokens
        if tokens.value:
            locked = guard_trading(is_warming_up=acc.slice_warming, action="mint")
            if is_refusal(locked):
                return locked
        for intent in tokens.value:
            if intent.intent_id in known:
                return invalid(
                    "intent_id",
                    "a minted intent id must be unique in the run's resting set",
                    intent_id=intent.intent_id,
                )
            if intent.stream_id not in acc.stream_ids:
                return invalid(
                    "stream_id",
                    "a minted intent names a stream in the declared stream set",
                    stream_id=intent.stream_id,
                    declared=list(acc.stream_ids),
                )
            known.add(intent.intent_id)
            acc.minted.append(intent)
            actions.append(f"mint:{intent.intent_id}")
    acc.traces.append(_trace("strategy-callbacks", acc.stream_ids, actions))
    return Ok(acc)


def _phase_new_intents_rest(acc: _Acc) -> Result[_Acc]:
    actions: list[str] = []
    for intent in acc.minted:
        actions.append(f"rest:{intent.intent_id}")
    acc.traces.append(_trace("new-intents-rest", acc.stream_ids, actions))
    return Ok(acc)


def _derive_if_requested(
    *,
    series: object,
    bar_plan: object,
    frontier: Instant,
    stream_ids: tuple[str, ...],
) -> Result[tuple[SameSliceConsumption, ...]]:
    """Sub-phase 1: fold higher BarSpecs from the finest base when declared."""
    if series is None and bar_plan is None:
        return Ok(())
    if series is None or bar_plan is None:
        return invalid(
            "bar_plan",
            "completed-boundary derivation needs both the underlying series "
            "and the declared BarSpec plan so bars and fills cannot diverge",
        )
    return consume_stream_plans(
        plans=bar_plan,
        series=series,
        frontier=frontier,
        stream_ids=stream_ids,
    )


def _trace(name: str, instrument_order: tuple[str, ...], actions: Sequence[str]) -> SubphaseTrace:
    return SubphaseTrace(
        subphase=name,
        instrument_order=instrument_order,
        actions=tuple(actions),
    )


def _pull_frontier(
    *,
    clock: object,
    current: Instant | None,
    observations: Sequence[SliceObservation],
) -> Result[Instant]:
    cursors = tuple(
        StreamNextEmit(stream_id=item.stream_id, next_emit=item.instant) for item in observations
    )
    if clock is None:
        return advance_frontier(current, cursors)
    if not isinstance(clock, FrontierClock):
        return invalid(
            "clock",
            "the loop advances an injected FrontierClock, or the pure "
            "advance_frontier pull when clock is omitted (B-2)",
            given=repr(type(clock).__name__),
        )
    return clock.advance(cursors)


def _bind_observations(
    stream_set: StreamSet,
    event_slice: EventSlice,
) -> Result[Mapping[str, SliceObservation | None]]:
    bound: dict[str, SliceObservation | None] = {}
    for sid in stream_set.stream_ids:
        bound[sid] = None
    for obs in event_slice.observations:
        if obs.stream_id not in bound:
            return invalid(
                "stream_id",
                "a slice observation must name a stream in the declared stream set",
                stream_id=obs.stream_id,
                declared=list(stream_set.stream_ids),
            )
        bound[obs.stream_id] = obs
    return Ok(MappingProxyType(bound))


def _resolve_stream_set(*, stream_set: object, config: object) -> Result[StreamSet]:
    from_config: StreamSet | None = None
    if config is not None:
        extracted = stream_set_from_config(config)
        if is_refusal(extracted):
            return extracted
        from_config = extracted.value
    if stream_set is None:
        if from_config is None:
            return invalid(
                "stream_set",
                "the loop needs the stream-set declaration order from the "
                "resolved run-config (B-2, B-12)",
            )
        return Ok(from_config)
    provided = StreamSet.try_create(stream_set)
    if is_refusal(provided):
        return provided
    if from_config is not None and provided.value.stream_ids != from_config.stream_ids:
        return invalid(
            "stream_set",
            "caller stream_set must match the resolved run-config declaration "
            "order; the config order is identity (B-12)",
            config=list(from_config.stream_ids),
            given=list(provided.value.stream_ids),
        )
    return Ok(from_config if from_config is not None else provided.value)


def _closed_observation_count(observations: Mapping[str, SliceObservation | None]) -> int:
    """One completed event slice counts as one observation; forming-only is 0."""
    for observation in observations.values():
        if observation is not None and observation.closed:
            return 1
    return 0


def _resolve_warmup(
    *,
    embargo: object,
    warmup: object,
    config: object,
) -> Result[WarmupProgress]:
    """Resolve in-loop warm-up from progress, embargo, or the resolved config."""
    if warmup is not None:
        if not isinstance(warmup, WarmupProgress):
            return invalid(
                "warmup",
                "in-loop warm-up progress is a WarmupProgress; pre-seeding is not warm-up",
                given=repr(type(warmup).__name__),
            )
        if embargo is not None:
            bound = SplitEmbargo.try_create(embargo)
            if is_refusal(bound):
                return bound
            if bound.value.observation_count != warmup.embargo.observation_count:
                return invalid(
                    EMBARGO_KEY,
                    "caller embargo must match the in-loop warm-up progress",
                    given=bound.value.observation_count,
                    progress=warmup.embargo.observation_count,
                )
        return Ok(warmup)
    from_config: SplitEmbargo | None = None
    if config is not None:
        extracted = embargo_from_config(config)
        if is_refusal(extracted):
            return extracted
        from_config = extracted.value
    if embargo is None:
        bound = from_config if from_config is not None else SplitEmbargo(observation_count=0)
        return WarmupProgress.try_create(bound)
    parsed = SplitEmbargo.try_create(embargo)
    if is_refusal(parsed):
        return parsed
    if from_config is not None and from_config.observation_count != parsed.value.observation_count:
        return invalid(
            EMBARGO_KEY,
            "caller embargo must match the resolved run-config split-manifest embargo",
            config=from_config.observation_count,
            given=parsed.value.observation_count,
        )
    return WarmupProgress.try_create(parsed.value)


def _as_handler(handler: object) -> Result[SliceHandler]:
    if handler is None:
        return Ok(SilentSliceHandler())
    if not isinstance(handler, SliceHandler):
        return invalid(
            "handler",
            "a slice handler provides update_stream, scheduled_position_event, "
            "execute_resting, update_closed_data, and mint_intents",
            given=repr(type(handler).__name__),
        )
    return Ok(handler)


def _as_cancel_token(cancel: object) -> Result[CancelToken | None]:
    if cancel is None:
        return Ok(None)
    if not isinstance(cancel, CancelToken):
        return invalid(
            "cancel",
            "cooperative cancel is a CancelToken inspected at slice boundaries; "
            "not a thread event (B-4, AD-15)",
            given=repr(type(cancel).__name__),
            cancel_at=CANCEL_AT,
        )
    return Ok(cancel)


def _as_observer(observer: object) -> Result[ProgressObserver | None]:
    if observer is None:
        return Ok(None)
    if not isinstance(observer, ProgressObserver):
        return invalid(
            "observer",
            "in-loop observation is a ProgressObserver updated at slice "
            "boundaries with data-points-processed and is_warming_up (FR-037)",
            given=repr(type(observer).__name__),
        )
    return Ok(observer)


def _as_probe(probe: object, limits: RunLimits) -> Result[LimitProbe | None]:
    if probe is None:
        if limits.bounded:
            return invalid(
                "probe",
                "in-loop time or memory limit detection needs an injected "
                "LimitProbe; the library never reads the system clock or a "
                "process meter (AR-16, AD-15, B-5)",
                time_limit_key=TIME_LIMIT_KEY,
                memory_limit_key=MEMORY_LIMIT_KEY,
            )
        return Ok(None)
    if not isinstance(probe, LimitProbe):
        return invalid(
            "probe",
            "a LimitProbe supplies monotonic elapsed Duration and a memory byte "
            "count; the library never reads the system clock (AR-16, B-5)",
            given=repr(type(probe).__name__),
        )
    return Ok(probe)


def _resolve_limits(*, limits: object, config: object) -> Result[RunLimits]:
    from_config: RunLimits | None = None
    if config is not None:
        extracted = limits_from_config(config)
        if is_refusal(extracted):
            return extracted
        from_config = extracted.value
    if limits is None:
        return Ok(from_config if from_config is not None else RunLimits())
    parsed = RunLimits.try_create(limits)
    if is_refusal(parsed):
        return parsed
    if from_config is not None and parsed.value != from_config:
        return invalid(
            "limits",
            "caller limits must match the resolved run-config per-run time and memory bounds (B-5)",
            config=from_config.fp1_identity(),
            given=parsed.value.fp1_identity(),
            time_limit_key=TIME_LIMIT_KEY,
            memory_limit_key=MEMORY_LIMIT_KEY,
        )
    return Ok(parsed.value)


def _progress_at(
    *,
    data_points_processed: int,
    slices_completed: int,
    is_warming_up: bool,
    frontier: Instant | None,
    elapsed: Duration | None,
) -> Result[RunProgress]:
    return RunProgress.try_create(
        data_points_processed,
        slices_completed,
        is_warming_up,
        frontier,
        elapsed,
    )


def _publish(observer: ProgressObserver | None, progress: RunProgress) -> Result[None]:
    if observer is None:
        return Ok(None)
    return observer.observe(progress)


def _as_slice_sequence(slices: object) -> Result[tuple[EventSlice, ...]]:
    if isinstance(slices, (str, bytes)) or not isinstance(slices, Sequence):
        return invalid(
            "slices",
            "run consumes a sequence of event slices",
            given=repr(type(slices).__name__),
        )
    parsed: list[EventSlice] = []
    for index, raw in enumerate(cast("Sequence[object]", slices)):
        item = EventSlice.try_create(raw)
        if is_refusal(item):
            return invalid(
                "slices",
                "each run entry is one event slice",
                index=index,
                cause=dict(item.context),
            )
        parsed.append(item.value)
    if not parsed:
        return invalid("slices", "the event-slice loop consumes one or more slices")
    return Ok(tuple(parsed))


def _as_resting_tuple(
    value: object,
    stream_set: StreamSet | None,
) -> Result[tuple[RestingIntent, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, RestingIntent):
        items: tuple[RestingIntent, ...] = (value,)
    elif isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "resting",
            "resting intents are a sequence of intent tokens",
            given=repr(type(value).__name__),
        )
    else:
        parsed: list[RestingIntent] = []
        seen: set[str] = set()
        for index, raw in enumerate(cast("Sequence[object]", value)):
            item = _coerce_resting(raw)
            if is_refusal(item):
                return invalid(
                    "resting",
                    "each resting entry is an intent token",
                    index=index,
                    cause=dict(item.context),
                )
            if item.value.intent_id in seen:
                return invalid(
                    "intent_id",
                    "resting intent ids are unique",
                    intent_id=item.value.intent_id,
                    index=index,
                )
            seen.add(item.value.intent_id)
            parsed.append(item.value)
        items = tuple(parsed)
    if stream_set is None:
        return Ok(items)
    declared = set(stream_set.stream_ids)
    unknown = [item.stream_id for item in items if item.stream_id not in declared]
    if unknown:
        return invalid(
            "stream_id",
            "a resting intent names a stream in the declared stream set",
            stream_id=unknown[0],
            declared=list(stream_set.stream_ids),
        )
    ordered: list[RestingIntent] = []
    for stream_id in stream_set.stream_ids:
        ordered.extend(item for item in items if item.stream_id == stream_id)
    return Ok(tuple(ordered))


def _coerce_declared_stream(raw: object) -> Result[DeclaredStream]:
    if isinstance(raw, DeclaredStream):
        return Ok(raw)
    if isinstance(raw, str):
        return DeclaredStream.try_create(raw)
    if isinstance(raw, Mapping):
        mapping = cast("Mapping[str, object]", raw)
        stream_id = mapping.get("stream_id", mapping.get("id"))
        instrument = mapping.get("instrument_id", mapping.get("instrument", stream_id))
        role = mapping.get("role", STREAM_ROLE_TRADING)
        return DeclaredStream.try_create(stream_id, instrument, role)
    return invalid(
        "stream_set",
        "each stream-set entry is a stream id, a DeclaredStream, or a mapping",
        given=repr(type(raw).__name__),
    )


def _coerce_observation(raw: object) -> Result[SliceObservation]:
    if isinstance(raw, SliceObservation):
        return Ok(raw)
    if not isinstance(raw, Mapping):
        return invalid(
            "observation",
            "a slice observation is a SliceObservation or a mapping",
            given=repr(type(raw).__name__),
        )
    mapping = cast("Mapping[str, object]", raw)
    return SliceObservation.try_create(
        mapping.get("stream_id"),
        mapping.get("instant"),
        mapping.get("closed", True),
    )


def _coerce_resting(raw: object) -> Result[RestingIntent]:
    if isinstance(raw, RestingIntent):
        return Ok(raw)
    if not isinstance(raw, Mapping):
        return invalid(
            "resting",
            "a resting intent is a RestingIntent or a mapping with intent_id and stream_id",
            given=repr(type(raw).__name__),
        )
    mapping = cast("Mapping[str, object]", raw)
    return RestingIntent.try_create(mapping.get("intent_id"), mapping.get("stream_id"))
