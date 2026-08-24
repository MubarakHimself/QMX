"""Example conformant-bot logic — factory + callback on the runtime protocol.

A governed bot is two artifacts (DEC-0172). This module is the logic half:
a factory the host constructs with (declaration, resolved assignment, injected
read surfaces), returning a callback driven per evaluation instant (DEC-0177).

The callback consumes only declared-footprint evidence, never sizes, never
reads a clock, never performs I/O, and never carries Book exit logic. Entry
intents carry an advisory stop proposal; ``requested_r`` stays Book-resolved.
"""

from __future__ import annotations

from collections.abc import Mapping

from qmf.core.exact import PriceDelta
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.risk.door import Direction, EntryIntent, ReasonCode
from qmf.risk.paper import ExecutionTarget
from qml.protocol import FootprintEvidence, PresenceState

_VENUE = "ctrader"
_SYMBOL = "EURUSD"
_ACCOUNT = "acct-1"
_REASON = "breakout"
_FAMILY = "trend-follow"
_PRICE_SCALE = 5
_DEFAULT_LOOKBACK = 1
_DEFAULT_STOP = 500


def _as_int(value: object, default: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return value


def _build_entry(stop_distance: int) -> Result[EntryIntent]:
    """Pin example instrument identity; the golden slice carries series, not CT-03."""
    venue = VenueId.try_create(_VENUE)
    if is_refusal(venue):
        return venue
    instrument = Instrument.try_create(venue.value, _SYMBOL)
    if is_refusal(instrument):
        return instrument
    target = ExecutionTarget.try_create("live", venue.value, _ACCOUNT)
    if is_refusal(target):
        return target
    reason = ReasonCode.try_create(_REASON, _FAMILY)
    if is_refusal(reason):
        return reason
    stop = PriceDelta.try_create(stop_distance, instrument.value, _PRICE_SCALE)
    if is_refusal(stop):
        return stop
    return EntryIntent.try_create(
        instrument.value,
        Direction.LONG,
        reason.value,
        target.value,
        advisory_stop_proposal=stop.value,
    )


class BreakoutCallback:
    """Host-driven callback. State is a bounded tick count for snapshot/restore."""

    __slots__ = ("_entry", "_lookback", "_ticks")

    def __init__(self, lookback: int, entry: EntryIntent) -> None:
        self._lookback = lookback
        self._entry = entry
        self._ticks = 0

    def on_instant(self, evidence: FootprintEvidence, /) -> object:
        """Emit an entry with an advisory stop once lookback present samples land."""
        self._ticks += 1
        if self._ticks < self._lookback:
            return ()
        if not _declared_series_present(evidence):
            return ()
        return (self._entry,)

    def export_state(self) -> dict[str, object]:
        return {"ticks": self._ticks}

    def import_state(self, payload: Mapping[str, object]) -> None:
        self._ticks = _as_int(payload.get("ticks"), 0)


class BreakoutFactory:
    """Conformant factory: declaration + assignment + read surfaces -> callback."""

    def construct(
        self,
        *,
        declaration: object,
        assignment: Mapping[str, object],
        read_surfaces: Mapping[str, object],
    ) -> Result[BreakoutCallback]:
        del declaration, read_surfaces
        lookback = _as_int(assignment.get("lookback"), _DEFAULT_LOOKBACK)
        stop_distance = _as_int(assignment.get("stop_distance"), _DEFAULT_STOP)
        entry = _build_entry(stop_distance)
        if is_refusal(entry):
            return entry
        return Ok(BreakoutCallback(lookback, entry.value))


def _declared_series_present(evidence: FootprintEvidence) -> bool:
    """True when every injected series (declared-footprint keys only) is present."""
    if not evidence.series:
        return False
    for series in evidence.series.values():
        if not series.samples:
            return False
        if series.samples[-1].presence is not PresenceState.PRESENT:
            return False
    return True
