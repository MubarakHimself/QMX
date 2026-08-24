"""Injected frontier clock — AD-8 ``Clock`` driven by stream next-emit (B-2).

Time advances only through an injected frontier clock that IS qmf-core's AD-8
``Clock`` protocol. Replay advance is a pure function of the data cursor:
monotonically non-decreasing, pulled to the minimum next-emit instant across
declared streams, never rewinding. Emitted instants are wall/replay
``Instant``\\ s — never the AD-8 monotonic diagnostic kind. The clock does
not choose ``world`` (B-7 / the compiler does via ``CLOCK_REPLAY`` /
``CLOCK_SIMULATED``). Asserting a simulated Instant as wall/replay is refused
until GAP-0048. Nothing here reads the system clock (AR-16).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final, Protocol, cast, runtime_checkable

from qmf.core.chrono import Clock, DataDrivenClock, Instant, MonotonicReading
from qmf.core.refusal import Ok, Result, is_refusal

from qmb._refuse import clean_token, invalid, policy, unsupported
from qmb.config import CLOCK_REPLAY, CLOCK_SIMULATED

__all__ = [
    "CLOCK_DOES_NOT_CHOOSE_WORLD",
    "FrontierClock",
    "NextEmitStream",
    "StreamNextEmit",
    "advance_frontier",
    "as_wall_replay_instant",
    "min_next_emit",
    "read_frontier",
    "script_replay_clock",
]

CLOCK_DOES_NOT_CHOOSE_WORLD: Final[bool] = True

_LEGAL_BINDINGS: Final[frozenset[str]] = frozenset({CLOCK_REPLAY, CLOCK_SIMULATED})


@runtime_checkable
class NextEmitStream(Protocol):
    """A declared stream's next-emit cursor (B-2 / B-12).

    ``next_emit`` is ``None`` when the stream is exhausted. The frontier pull
    ignores exhausted streams.
    """

    @property
    def stream_id(self) -> str:  # pragma: no cover - protocol seam
        """Opaque stream identity from the resolved stream-set declaration."""
        ...

    @property
    def next_emit(self) -> Instant | None:  # pragma: no cover - protocol seam
        """The next wall/replay Instant this stream will emit, or ``None``."""
        ...


@dataclass(frozen=True, slots=True)
class StreamNextEmit:
    """Frozen next-emit cursor for one declared stream."""

    stream_id: str
    next_emit: Instant | None

    @classmethod
    def try_create(cls, stream_id: object, next_emit: object) -> Result[StreamNextEmit]:
        """Validate and build a stream cursor, returning value-or-refusal."""
        token = clean_token(stream_id)
        if token is None:
            return invalid(
                "stream_id",
                "a stream next-emit cursor names a non-empty stream id",
                given=repr(stream_id),
            )
        if next_emit is None:
            return Ok(cls(stream_id=token, next_emit=None))
        if not isinstance(next_emit, Instant):
            return invalid(
                "next_emit",
                "a stream next-emit is an Instant or None; a MonotonicReading "
                "is never a wall Instant (AR-16)",
                given=repr(next_emit),
            )
        return Ok(cls(stream_id=token, next_emit=next_emit))


def min_next_emit(streams: object) -> Result[Instant]:
    """Pure: the minimum next-emit Instant across all non-exhausted streams.

    Deterministic: equal Instants compare by ``value_ns``; stream declaration
    order does not affect the chosen Instant (the min value is unique as an
    Instant even when several streams share it). Exhausted streams (``None``)
    are ignored. No remaining emits is ``unavailable dependency``.
    """
    if not isinstance(streams, Sequence) or isinstance(streams, (str, bytes)):
        return invalid(
            "streams",
            "min_next_emit takes a sequence of declared stream next-emit cursors",
            given=repr(streams),
        )
    candidates: list[Instant] = []
    for index, stream in enumerate(cast("Sequence[object]", streams)):
        if not isinstance(stream, NextEmitStream):
            return invalid(
                "streams",
                "each entry must provide stream_id and next_emit (NextEmitStream)",
                index=index,
                given=repr(stream),
            )
        nxt = stream.next_emit
        if nxt is None:
            continue
        candidates.append(nxt)
    if not candidates:
        return unsupported(
            "streams",
            "no stream has a next-emit Instant; the frontier cannot advance",
        )
    chosen = candidates[0]
    for candidate in candidates[1:]:
        if candidate.value_ns < chosen.value_ns:
            chosen = candidate
    return Ok(chosen)


def advance_frontier(
    current: object,
    streams: object,
) -> Result[Instant]:
    """Pure replay advance: pull to min next-emit; never rewind (B-2, FR-037).

    When ``current`` is ``None``, the initial frontier is the min next-emit.
    When a pulled Instant is strictly before ``current``, the advance is an
    ``invalid input`` refusal — the frontier never rewinds. Equal Instants are
    allowed (monotonically non-decreasing).
    """
    if current is not None and not isinstance(current, Instant):
        return invalid(
            "current",
            "the frontier current is an Instant or None",
            given=repr(current),
        )
    pulled = min_next_emit(streams)
    if is_refusal(pulled):
        return pulled
    nxt = pulled.value
    if current is not None and nxt.value_ns < current.value_ns:
        return invalid(
            "next_emit",
            "frontier advance refuses rewind; the min next-emit is strictly "
            "before the current frontier Instant (B-2, FR-037)",
            current=current.value_ns,
            next_emit=nxt.value_ns,
        )
    return Ok(nxt)


def as_wall_replay_instant(
    candidate: object,
    *,
    clock_binding: object,
) -> Result[Instant]:
    """Accept a wall/replay Instant for frontier emission; refuse the rest.

    A ``MonotonicReading`` is never a wall Instant (AR-16). Asserting a
    simulated Instant as wall/replay is refused until GAP-0048 — the loop seam
    may exist; the assertion may not (B-2, SC-06). ``CLOCK_REPLAY`` accepts a
    plain ``Instant``. The clock binding is supplied by the compiler (B-3/B-7);
    this function does not choose ``world``.
    """
    binding = clean_token(clock_binding)
    if binding is None or binding not in _LEGAL_BINDINGS:
        return invalid(
            "clock_binding",
            "frontier emission names CLOCK_REPLAY or CLOCK_SIMULATED; the "
            "compiler chooses the binding, never the clock (B-7)",
            given=repr(clock_binding),
            allowed=sorted(_LEGAL_BINDINGS),
        )
    if isinstance(candidate, MonotonicReading):
        return invalid(
            "candidate",
            "a MonotonicReading is never a wall/replay Instant; frontier "
            "emission uses AD-8 wall Instants only (AR-16, B-2)",
            kind=candidate.kind.value,
        )
    if not isinstance(candidate, Instant):
        return invalid(
            "candidate",
            "frontier emission accepts an Instant only",
            given=repr(candidate),
        )
    if binding == CLOCK_SIMULATED:
        return policy(
            "candidate",
            "asserting a simulated Instant as a wall/replay Instant is refused "
            "until GAP-0048; the loop seam may exist, the assertion may not "
            "(B-2, SC-06)",
            clock_binding=binding,
            gap="GAP-0048",
        )
    return Ok(candidate)


def read_frontier(clock: object) -> Instant:
    """Read the current wall Instant from the injected frontier ``Clock``.

    The only approved time read below the composition root (AR-16). Callers
    pass the injected ``Clock``; nothing here touches the system clock.
    """
    if not isinstance(clock, Clock):
        raise TypeError("read_frontier requires an injected qmf.core.chrono.Clock")
    return clock.wall_now()


def script_replay_clock(
    *,
    boot_epoch_id: str,
    wall_instants: Sequence[Instant],
    monotonic_ns: Sequence[int] | None = None,
) -> DataDrivenClock:
    """Reuse ``DataDrivenClock`` as the injected frontier ``Clock`` for scripts.

    Scripted replay binds the same AD-8 ``Clock`` protocol the live/replay loop
    reads — no second clock type (B-2). When ``monotonic_ns`` is omitted, a
    zero-filled diagnostic script matching the wall length is supplied so the
    ``Clock`` seam stays complete without inventing wall time from monotonic
    readings.
    """
    walls = tuple(wall_instants)
    if monotonic_ns is None:
        mono: tuple[int, ...] = tuple(0 for _ in walls)
    else:
        mono = tuple(monotonic_ns)
    return DataDrivenClock(
        boot_epoch_id=boot_epoch_id,
        wall_instants=walls,
        monotonic_ns=mono,
    )


class FrontierClock:
    """Stream-driven frontier ``Clock`` for replay (B-2).

    Wall time advances only via :meth:`advance`, a pure function of the data
    cursor (min next-emit, never rewind). Conforms to ``qmf.core.chrono.Clock``.
    Does not choose ``world``. Never reads the system clock.
    """

    def __init__(
        self,
        *,
        boot_epoch_id: str,
        clock_binding: str,
        initial: Instant | None,
        monotonic_ns: tuple[int, ...],
    ) -> None:
        self.boot_epoch_id: str = boot_epoch_id
        self._clock_binding: str = clock_binding
        self._current: Instant | None = initial
        self._monotonic: tuple[int, ...] = monotonic_ns
        self._monotonic_cursor: int = 0

    @classmethod
    def try_create(
        cls,
        *,
        boot_epoch_id: object,
        clock_binding: object = CLOCK_REPLAY,
        initial: object = None,
        monotonic_ns: object = (),
    ) -> Result[FrontierClock]:
        """Validate and build a frontier ``Clock``, returning value-or-refusal."""
        boot = clean_token(boot_epoch_id)
        if boot is None:
            return invalid(
                "boot_epoch_id",
                "a frontier clock carries a non-empty boot/epoch id (AD-8)",
                given=repr(boot_epoch_id),
            )
        binding = clean_token(clock_binding)
        if binding is None or binding not in _LEGAL_BINDINGS:
            return invalid(
                "clock_binding",
                "a frontier clock is bound as CLOCK_REPLAY or CLOCK_SIMULATED; "
                "the compiler chooses the binding, never the clock (B-7)",
                given=repr(clock_binding),
                allowed=sorted(_LEGAL_BINDINGS),
            )
        if initial is not None and not isinstance(initial, Instant):
            return invalid(
                "initial",
                "an initial frontier is an Instant or None",
                given=repr(initial),
            )
        if not isinstance(monotonic_ns, Sequence) or isinstance(monotonic_ns, (str, bytes)):
            return invalid(
                "monotonic_ns",
                "monotonic script entries are a sequence of int nanosecond readings",
                given=repr(monotonic_ns),
            )
        mono: list[int] = []
        for index, value in enumerate(cast("Sequence[object]", monotonic_ns)):
            if isinstance(value, bool) or not isinstance(value, int):
                return invalid(
                    "monotonic_ns",
                    "monotonic script entries are int nanosecond readings",
                    index=index,
                    given=repr(value),
                )
            mono.append(value)
        if initial is not None:
            accepted = as_wall_replay_instant(initial, clock_binding=binding)
            if is_refusal(accepted):
                return accepted
            seeded = accepted.value
        else:
            seeded = None
        return Ok(
            cls(
                boot_epoch_id=boot,
                clock_binding=binding,
                initial=seeded,
                monotonic_ns=tuple(mono),
            )
        )

    @property
    def clock_binding(self) -> str:
        """Compiler-chosen clock binding; the clock does not choose world."""
        return self._clock_binding

    @property
    def current(self) -> Instant | None:
        """The current frontier Instant, or ``None`` before the first advance."""
        return self._current

    def advance(self, streams: Sequence[NextEmitStream]) -> Result[Instant]:
        """Pull the frontier to the min next-emit; refuse rewind and simulated assertion."""
        pulled = advance_frontier(self._current, streams)
        if is_refusal(pulled):
            return pulled
        accepted = as_wall_replay_instant(pulled.value, clock_binding=self._clock_binding)
        if is_refusal(accepted):
            return accepted
        self._current = accepted.value
        return Ok(accepted.value)

    def wall_now(self) -> Instant:
        """The current wall/replay Instant (AD-8); raise if not yet advanced."""
        if self._current is None:
            raise LookupError(
                "frontier clock has no current Instant; advance from stream next-emit cursors first"
            )
        return self._current

    def monotonic_now(self) -> MonotonicReading:
        """Next scripted monotonic diagnostic; raise once the script is spent."""
        if self._monotonic_cursor >= len(self._monotonic):
            raise LookupError("frontier clock exhausted its scripted monotonic readings")
        value = self._monotonic[self._monotonic_cursor]
        self._monotonic_cursor += 1
        return MonotonicReading(value_ns=value, boot_epoch_id=self.boot_epoch_id)
