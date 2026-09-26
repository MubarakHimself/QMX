"""Reference usage — in-loop warm-up with trading locked (Story 14.4).

Executable::

    python qmb/examples/warmup_usage.py

Shows the things SC-10 / B-2 / CT-12 pin down:

1. Warm-up is the same event-slice loop, same sub-phases, same adapters.
2. Acting (mint / fill / command) during warm-up is a typed policy rejection.
3. Warm-up length is the split-manifest embargo observation count, never a Duration.
4. The loop adds no second window; pre-seeding buffers is not warm-up.
5. ``is_warming_up`` is exposed; evidence range is the trading interval only.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.runloop import (
    PRESEED_IS_WARMUP,
    SUBPHASES,
    WARMUP_ADDS_SECOND_WINDOW,
    WARMUP_MECHANISM,
    WARMUP_UNIT,
    RestingIntent,
    SilentSliceHandler,
    SliceObservation,
    SplitEmbargo,
    loop_identity,
    preseed_indicator_buffers,
    run,
    run_slice,
)
from qmf.core.chrono import Duration, Instant
from qmf.core.refusal import Ok, Result, is_ok, is_refusal

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


class _MintAfterTwo:
    """Same adapter across warm-up and trading; mints only after two observations."""

    def __init__(self) -> None:
        self._calls = 0

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
        del frontier
        self._calls += 1
        if self._calls <= 2:
            return Ok(())
        minted = _unwrap(RestingIntent.try_create(f"new-{stream_id}", stream_id), "intent")
        return Ok((minted,))


class _MintNow:
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
        del frontier
        minted = _unwrap(RestingIntent.try_create(f"new-{stream_id}", stream_id), "intent")
        return Ok((minted,))


def same_loop_trading_locked() -> None:
    """Warm-up slices run the pinned sub-phases with ``is_warming_up`` set."""
    outcome = _unwrap(
        run(
            slices=(
                (_obs("eurusd", _NS),),
                (_obs("eurusd", _NS + 1),),
                (_obs("eurusd", _NS + 2),),
            ),
            stream_set=("eurusd",),
            handler=SilentSliceHandler(),
            embargo=2,
        ),
        "warmup loop",
    )
    assert [item.subphase_order() for item in outcome.slices] == [SUBPHASES] * 3
    assert [item.is_warming_up for item in outcome.slices] == [True, True, False]
    assert outcome.is_warming_up is False


def acting_is_policy_rejection() -> None:
    """Minting (an entry, an exit, any command) during warm-up is refused."""
    refused = run(
        slices=((_obs("eurusd"),),),
        stream_set=("eurusd",),
        handler=_MintNow(),
        embargo=3,
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "warmup"


def embargo_is_observation_count() -> None:
    """Length is the split-manifest embargo count; Duration and a second window refuse."""
    bound = _unwrap(SplitEmbargo.try_create(2), "embargo")
    assert bound.observation_count == 2
    assert bound.unit == WARMUP_UNIT
    duration = _unwrap(Duration.try_create(60_000_000_000), "duration")
    assert is_refusal(SplitEmbargo.try_create(duration))
    assert is_refusal(SplitEmbargo.try_create({"embargo_width": 8, "warmup_bars": 3}))
    assert WARMUP_ADDS_SECOND_WINDOW is False
    assert loop_identity()["warmup_mechanism"] == WARMUP_MECHANISM


def preseed_is_not_warmup() -> None:
    """Pre-seeding indicator buffers without replaying slices is not warm-up."""
    refused = preseed_indicator_buffers({"buffers": "hot"})
    assert is_refusal(refused)
    assert refused.context["preseed_is_warmup"] is False
    assert PRESEED_IS_WARMUP is False


def evidence_range_is_trading_interval() -> None:
    """The result label's evidence range starts at the first unlocked slice."""
    handler = _MintAfterTwo()
    outcome = _unwrap(
        run(
            slices=(
                (_obs("eurusd", _NS),),
                (_obs("eurusd", _NS + 5),),
                (_obs("eurusd", _NS + 9),),
            ),
            stream_set=("eurusd",),
            handler=handler,
            embargo=2,
        ),
        "trading interval",
    )
    assert outcome.evidence_range.start.value_ns == _NS + 9
    assert outcome.evidence_range.end.value_ns == _NS + 10
    assert outcome.slices[2].minted == ("new-eurusd",)
    locked = _unwrap(
        run_slice((_obs("eurusd"),), stream_set=("eurusd",), embargo=1),
        "warming slice",
    )
    assert locked.is_warming_up is True


def main() -> None:
    assert qmb.WARMUP_MECHANISM == WARMUP_MECHANISM
    same_loop_trading_locked()
    print("same event-slice loop during warm-up; trading locked")
    acting_is_policy_rejection()
    print("acting during warm-up is policy rejection")
    embargo_is_observation_count()
    print("embargo is an observation count, never a Duration; no second window")
    preseed_is_not_warmup()
    print("pre-seeding buffers is not warm-up")
    evidence_range_is_trading_interval()
    print("evidence range is the trading interval only")
    print("in-loop warm-up ok")


if __name__ == "__main__":
    main()
