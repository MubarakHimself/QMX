"""Per-command-stream loop driver over unforked QMB ``run_slice`` (TN-5).

One :class:`CommandStreamLoop` instance per ``(VenueId, account)`` stream. On
frontier close it calls QMB ``run_slice`` through the six pinned sub-phases and
commits the durable interpretation cursor only after the slice completes.
Forming bars stay never visible or actionable (DEC-0190; QMB B-2).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final

from qmb.runloop import (
    FORMING_BAR_ACTIONABLE,
    FORMING_BAR_VISIBLE,
    SUBPHASES,
    SliceHandler,
    SliceObservation,
    SliceOutcome,
    StreamSet,
    run_slice,
)
from qmf.core import (
    Clock,
    Duration,
    Instant,
    JournalSink,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_refusal,
)

from qmn.loop.accumulator import RecordingAccumulator
from qmn.loop.kinds import CycleBand, InboundObservation

__all__ = [
    "PINNED_SUBPHASES",
    "CommandStreamLoop",
    "InterpretationCursor",
    "SliceDriveResult",
    "forming_bars_actionable",
    "forming_bars_visible",
]


PINNED_SUBPHASES: Final[tuple[str, ...]] = SUBPHASES


def forming_bars_visible() -> bool:
    """QMB B-2 law: forming bars are never strategy-visible."""
    return FORMING_BAR_VISIBLE


def forming_bars_actionable() -> bool:
    """QMB B-2 law: forming bars are never actionable."""
    return FORMING_BAR_ACTIONABLE


@dataclass
class InterpretationCursor:
    """Durable interpretation cursor committing only at completed slice end.

    The pending position advances while a slice runs; the committed position
    updates only after ``run_slice`` returns successfully and the cursor row is
    journaled — never mid-slice (DEC-0190).
    """

    committed_observation_id: str | None = None
    committed_receive_wall_ns: int | None = None
    pending_observation_id: str | None = None
    pending_receive_wall_ns: int | None = None
    commit_count: int = 0

    @property
    def is_committed_through_pending(self) -> bool:
        """True when no uncommitted pending fold remains."""
        return (
            self.pending_observation_id is None
            or self.pending_observation_id == self.committed_observation_id
        )

    def begin_slice(self, *, observation_id: str, receive_wall_ns: int) -> None:
        """Mark the interpretation frontier the in-flight slice will cover."""
        self.pending_observation_id = observation_id
        self.pending_receive_wall_ns = receive_wall_ns

    def commit(
        self, journal_sink: JournalSink[Mapping[str, object]]
    ) -> Result[Mapping[str, object]]:
        """Persist the cursor after the slice completes; refuse mid-slice misuse."""
        if self.pending_observation_id is None or self.pending_receive_wall_ns is None:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "interpretation_cursor",
                    "reason": "commit requires a pending slice frontier; the cursor "
                    "never advances mid-slice without a completed run_slice",
                },
            )
        row = {
            "event_type": "control action",
            "kind": "interpretation-cursor-commit",
            "observation_id": self.pending_observation_id,
            "receive_wall_time_ns": self.pending_receive_wall_ns,
            "previous_observation_id": self.committed_observation_id,
            "previous_receive_wall_ns": self.committed_receive_wall_ns,
            "commit_index": self.commit_count + 1,
        }
        appended = journal_sink.append(MappingProxyType(dict(row)))
        if is_refusal(appended):
            return appended
        self.committed_observation_id = self.pending_observation_id
        self.committed_receive_wall_ns = self.pending_receive_wall_ns
        self.commit_count += 1
        self.pending_observation_id = None
        self.pending_receive_wall_ns = None
        return Ok(MappingProxyType(dict(row)))


@dataclass(frozen=True, slots=True)
class SliceDriveResult:
    """Outcome of one frontier-close drive through unforked ``run_slice``."""

    outcome: SliceOutcome
    subphases: tuple[str, ...]
    cycle_band: CycleBand
    cursor_committed: Mapping[str, object]
    elapsed_ns: int
    latency_breached: bool
    forming_visible: bool
    forming_actionable: bool


@dataclass
class CommandStreamLoop:
    """One unforked QMB loop instance behind a recording accumulator.

    Backtest, replay, and live differ only in which clock and VenueClientPort
    the composition root binds; this driver always calls ``run_slice`` and never
    a second loop implementation (DEC-0190).
    """

    accumulator: RecordingAccumulator
    stream_set: StreamSet
    clock: Clock
    max_slice_latency: Duration
    handler: SliceHandler | None = None
    cursor: InterpretationCursor = field(default_factory=InterpretationCursor)
    _frontier: Instant | None = None
    _resting: tuple[object, ...] = ()

    @classmethod
    def try_create(
        cls,
        *,
        accumulator: object,
        stream_set: object,
        clock: object,
        max_slice_latency: object,
        handler: object = None,
        cursor: object = None,
    ) -> Result[CommandStreamLoop]:
        """Validate and bind one per-stream loop driver."""
        if not isinstance(accumulator, RecordingAccumulator):
            return _invalid(
                "accumulator",
                "the loop drives behind a RecordingAccumulator",
                given=repr(type(accumulator).__name__),
            )
        declared = StreamSet.try_create(stream_set)
        if is_refusal(declared):
            return declared
        if not isinstance(clock, Clock):
            return _invalid(
                "clock",
                "the live frontier clock is qmf-core's injected Clock",
                given=repr(type(clock).__name__),
            )
        latency = _as_duration(max_slice_latency)
        if is_refusal(latency):
            return latency
        if latency.value.value_ns <= 0:
            return _invalid(
                "max_slice_latency",
                "max_slice_latency is a positive duration (registry:max_slice_latency)",
                given=latency.value.value_ns,
            )
        if handler is not None and not _looks_like_handler(handler):
            return _invalid(
                "handler",
                "handler implements the five SliceHandler hooks or is omitted",
                given=repr(type(handler).__name__),
            )
        resolved_cursor: InterpretationCursor
        if cursor is None:
            resolved_cursor = InterpretationCursor()
        elif isinstance(cursor, InterpretationCursor):
            resolved_cursor = cursor
        else:
            return _invalid(
                "cursor",
                "cursor is an InterpretationCursor or omitted",
                given=repr(type(cursor).__name__),
            )
        return Ok(
            cls(
                accumulator=accumulator,
                stream_set=declared.value,
                clock=clock,
                max_slice_latency=latency.value,
                handler=handler,  # type: ignore[arg-type]
                cursor=resolved_cursor,
            )
        )

    @property
    def pinned_subphases(self) -> tuple[str, ...]:
        """Identity-bearing six-phase order preserved verbatim from QMB."""
        return PINNED_SUBPHASES

    def close_frontier(self) -> Result[SliceDriveResult | None]:
        """Pull foldable observations and drive one unforked ``run_slice``.

        Returns ``Ok(None)`` when the accumulator has nothing foldable. The
        interpretation cursor commits only after ``run_slice`` completes.
        """
        batch = self.accumulator.pull_foldable()
        if not batch:
            return Ok(None)

        # Group by receive-wall instant — one EventSlice per shared frontier.
        by_ns: dict[int, list[SliceObservation]] = {}
        order: list[int] = []
        last = batch[-1]
        for item in batch:
            ns = item.receive_wall.value_ns
            if ns not in by_ns:
                by_ns[ns] = []
                order.append(ns)
            # One observation per stream_id per instant (EventSlice rule).
            existing_ids = {obs.stream_id for obs in by_ns[ns]}
            sid = item.stream_id
            if sid in existing_ids:
                # Prefer the latest closed observation for that stream.
                by_ns[ns] = [obs for obs in by_ns[ns] if obs.stream_id != sid]
            built = SliceObservation.try_create(sid, item.receive_wall, item.closed)
            if is_refusal(built):
                return built
            by_ns[ns].append(built.value)

        self.cursor.begin_slice(
            observation_id=last.observation_id,
            receive_wall_ns=last.receive_wall.value_ns,
        )

        start = self.clock.monotonic_now()
        if is_refusal(start):
            return start

        outcomes: list[SliceOutcome] = []
        for ns in order:
            observations = tuple(by_ns[ns])
            # Frontier is the accumulator receive-wall stamp carried on each
            # observation. Pass clock=None so run_slice advances via the pure
            # observation cursor (B-2); self.clock measures slice latency only.
            outcome = run_slice(
                observations,
                stream_set=self.stream_set,
                current_frontier=self._frontier,
                clock=None,
                handler=self.handler,
                resting=self._resting,
            )
            if is_refusal(outcome):
                # Cursor stays uncommitted — re-fold boundary remains prior commit.
                return outcome
            done = outcome.value
            # Forming bars from the outcome must never become visible/actionable.
            if done.forming and (FORMING_BAR_VISIBLE or FORMING_BAR_ACTIONABLE):
                return TypedRefusal(
                    category=RefusalCategory.POLICY_REJECTION,
                    retryability=Retryability.NO,
                    context={
                        "field": "forming",
                        "reason": "forming bars are never visible or actionable",
                        "forming_bar_visible": FORMING_BAR_VISIBLE,
                        "forming_bar_actionable": FORMING_BAR_ACTIONABLE,
                    },
                )
            self._frontier = done.frontier
            self._resting = done.resting
            outcomes.append(done)

        if not outcomes:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "event_slice",
                    "reason": "frontier close produced no runnable event slice",
                },
            )
        final_outcome = outcomes[-1]

        end = self.clock.monotonic_now()
        if is_refusal(end):
            return end
        elapsed = end.value.elapsed_since(start.value)
        if is_refusal(elapsed):
            return elapsed
        elapsed_ns = elapsed.value.value_ns
        latency_breached = elapsed_ns > self.max_slice_latency.value_ns
        if latency_breached:
            breach = self.accumulator.mark_latency_breach(
                elapsed_ns=elapsed_ns,
                bound_ns=self.max_slice_latency.value_ns,
            )
            if is_refusal(breach):
                return breach

        committed = self.cursor.commit(self.accumulator.journal_sink)
        if is_refusal(committed):
            return committed

        band = self.accumulator.cycle_band
        return Ok(
            SliceDriveResult(
                outcome=final_outcome,
                subphases=final_outcome.subphase_order(),
                cycle_band=band,
                cursor_committed=committed.value,
                elapsed_ns=elapsed_ns,
                latency_breached=latency_breached,
                forming_visible=FORMING_BAR_VISIBLE,
                forming_actionable=FORMING_BAR_ACTIONABLE,
            )
        )

    def push_from_port_observation(
        self,
        observation: Mapping[str, object],
        *,
        receive_wall: Instant | None = None,
    ) -> Result[InboundObservation]:
        """Admit one VenueClientPort observation mapping through the accumulator."""
        wall = receive_wall
        if wall is None:
            raw_ns = observation.get("receive_wall_time_ns")
            if isinstance(raw_ns, int) and not isinstance(raw_ns, bool):
                built_wall = Instant.try_create(raw_ns)
                if is_refusal(built_wall):
                    return built_wall
                wall = built_wall.value
            else:
                now = self.clock.wall_now()
                if is_refusal(now):
                    return now
                wall = now.value
        oid = observation.get("observation_id") or observation.get("native_id")
        if oid is None:
            oid = f"obs-{wall.value_ns}"
        sid = observation.get("stream_id")
        if not isinstance(sid, str) or not sid.strip():
            # Fall back to the first declared trading stream.
            sid = self.stream_set.stream_ids[0]
        venue_instant = None
        raw_venue = observation.get("venue_instant_ns")
        if isinstance(raw_venue, int) and not isinstance(raw_venue, bool):
            built_venue = Instant.try_create(raw_venue)
            if is_refusal(built_venue):
                return built_venue
            venue_instant = built_venue.value
        kind = (
            observation.get("wire_kind")
            or observation.get("kind")
            or observation.get("observation_kind")
        )
        closed_raw = observation.get("closed", True)
        return self.accumulator.push(
            observation_id=oid,
            stream_id=sid,
            receive_wall=wall,
            payload=observation,
            kind=kind,
            venue_instant=venue_instant,
            closed=bool(closed_raw),
        )


def _as_duration(value: object) -> Result[Duration]:
    if isinstance(value, Duration):
        return Ok(value)
    if isinstance(value, bool) or not isinstance(value, int):
        return _invalid(
            "max_slice_latency",
            "max_slice_latency is a Duration or int nanoseconds",
            given=repr(value),
        )
    return Duration.try_create(value)


def _looks_like_handler(handler: object) -> bool:
    required = (
        "update_stream",
        "scheduled_position_event",
        "execute_resting",
        "update_closed_data",
        "mint_intents",
    )
    return all(callable(getattr(handler, name, None)) for name in required)


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )
