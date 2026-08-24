"""Reference usage — the event-slice loop with six pinned sub-phases (Story 14.2).

Executable::

    python qmb/examples/event_slice_usage.py

Shows the things AR-57 / B-2 / FR-037 pin down:

1. One event-slice loop; per slice the six :data:`qmb.SUBPHASES` run in pinned order.
2. Instruments process in stream-set declaration order.
3. A new intent minted in sub-phase 5 never fills against this slice's path.
4. Indicators/structure update on closed data only (forming bars are skipped).
5. Changing sub-phase order is identity-bearing (``fp1`` changes).
6. ``run`` is pure: same inputs, same outcome; no log, no ledger.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.runloop import (
    SAME_SLICE_NEW_INTENT_FILL,
    SUBPHASES,
    RestingIntent,
    SilentSliceHandler,
    SliceObservation,
    fingerprint_loop,
    loop_identity,
    run,
    run_slice,
)
from qmf.core.chrono import Instant
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Ok, Result, is_ok

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int = _NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _obs(stream_id: str, ns: int = _NS, *, closed: bool = True) -> SliceObservation:
    return _unwrap(SliceObservation.try_create(stream_id, _instant(ns), closed), "observation")


class _FillAndMintOnce:
    """Fills eligible resting intents; mints one intent per stream on first slice."""

    def __init__(self) -> None:
        self._minted: set[str] = set()

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
        return Ok(True)

    def update_closed_data(
        self,
        stream_id: str,
        observation: SliceObservation,
        frontier: Instant,
    ) -> Result[None]:
        del stream_id, observation, frontier
        return Ok(None)

    def mint_intents(self, stream_id: str, frontier: Instant) -> Result[object]:
        del frontier
        if stream_id in self._minted:
            return Ok(())
        self._minted.add(stream_id)
        minted = _unwrap(RestingIntent.try_create(f"new-{stream_id}", stream_id), "intent")
        return Ok((minted,))


def pinned_order() -> None:
    """The six sub-phase strings are spine-pinned and identity-bearing."""
    assert SUBPHASES == (
        "frontier-advance",
        "scheduled-position-events",
        "resting-orders",
        "closed-data-indicators-structure",
        "strategy-callbacks",
        "new-intents-rest",
    )
    assert SAME_SLICE_NEW_INTENT_FILL is False
    canonical = _unwrap(fingerprint_loop(), "loop fp")
    permuted = dict(loop_identity())
    permuted["subphases"] = tuple(reversed(SUBPHASES))
    changed = _unwrap(fingerprint(permuted), "permuted fp")
    assert changed.value != canonical.value


def same_slice_ineligibility() -> None:
    """A newly minted intent rests; it fills only on a later slice."""
    handler = _FillAndMintOnce()
    outcome = _unwrap(
        run(
            slices=(
                (_obs("eurusd"), _obs("gbpusd")),
                (_obs("eurusd", _NS + 1), _obs("gbpusd", _NS + 1)),
            ),
            stream_set=("eurusd", "gbpusd"),
            handler=handler,
        ),
        "loop",
    )
    first, second = outcome.slices
    assert first.subphase_order() == SUBPHASES
    assert first.filled == ()
    assert set(first.ineligible) == {"new-eurusd", "new-gbpusd"}
    assert "rest:new-eurusd" in first.trace[5].actions
    assert set(second.filled) == {"new-eurusd", "new-gbpusd"}
    assert outcome.stream_order == ("eurusd", "gbpusd")


def forming_bar_is_not_closed_data() -> None:
    """Indicators/structure update on closed data only."""
    outcome = _unwrap(
        run_slice(
            (_obs("eurusd", closed=False),),
            stream_set=("eurusd",),
        ),
        "forming slice",
    )
    assert "skip-forming:eurusd" in outcome.trace[3].actions
    assert "closed:eurusd" not in outcome.trace[3].actions


def run_is_pure() -> None:
    """Same inputs yield the same loop outcome; nothing is written."""
    slices = ((_obs("eurusd"),),)
    first = _unwrap(run(slices=slices, stream_set=("eurusd",), handler=SilentSliceHandler()), "a")
    second = _unwrap(run(slices=slices, stream_set=("eurusd",), handler=SilentSliceHandler()), "b")
    assert first.fp1_identity() == second.fp1_identity()


def main() -> None:
    assert qmb.SUBPHASES == SUBPHASES
    assert qmb.run is run
    pinned_order()
    print("pinned sub-phase order is identity-bearing")
    same_slice_ineligibility()
    print("new intents rest; they never fill against this slice's path")
    forming_bar_is_not_closed_data()
    print("forming bar skipped: closed-data indicators/structure only")
    run_is_pure()
    print("event-slice loop ok; run is pure")


if __name__ == "__main__":
    main()
