"""Reference usage — cancel and observe a run while it is running (Story 14.6).

Executable::

    python qmb/examples/cancel_observe_usage.py

Shows the things FR-037 / B-4 / B-5 pin down:

1. A cancel token stops the loop cooperatively at a slice boundary.
2. The typed terminal is ``aborted``; no partial governed result is emitted.
3. Progress exposes data-points-processed and ``is_warming_up`` while running.
4. A time or memory limit breach is a typed ``aborted``, not a hang.
5. ``run`` writes no log and no ledger; Epic 15 renders the aborted ledger line.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.runloop import (
    CANCEL_AT,
    CAUSE_CANCEL,
    CAUSE_MEMORY_LIMIT,
    CAUSE_TIME_LIMIT,
    PARTIAL_GOVERNED_RESULT_ON_ABORT,
    TERMINAL_ABORTED,
    CancelToken,
    ProgressSink,
    RestingIntent,
    RunLimits,
    RunProgress,
    ScriptedLimitProbe,
    SliceObservation,
    loop_identity,
    run,
)
from qmf.core.chrono import Instant
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


def _obs(stream_id: str, ns: int = _NS) -> SliceObservation:
    return _unwrap(SliceObservation.try_create(stream_id, _instant(ns), True), "observation")


def _slices(count: int) -> tuple[tuple[SliceObservation, ...], ...]:
    return tuple((_obs("eurusd", _NS + index),) for index in range(count))


class _CancelAfter:
    def __init__(self, token: CancelToken, after: int) -> None:
        self.token = token
        self.after = after
        self.seen = 0

    def update_stream(
        self,
        stream_id: str,
        observation: SliceObservation | None,
        frontier: Instant,
    ) -> Result[None]:
        del stream_id, observation, frontier
        self.seen += 1
        if self.seen >= self.after:
            return self.token.cancel()
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


def cooperative_cancel_at_slice_boundary() -> None:
    """Signalled cancel stops before the next slice; abort is the terminal."""
    token = CancelToken()
    handler = _CancelAfter(token, after=2)
    refused = run(
        slices=_slices(4),
        stream_set=("eurusd",),
        handler=handler,
        cancel=token,
    )
    assert is_refusal(refused)
    assert refused.context["terminal"] == TERMINAL_ABORTED
    assert refused.context["cause"] == CAUSE_CANCEL
    assert refused.context["cancel_at"] == CANCEL_AT
    assert refused.context["ledger_role"] == "aborted"
    assert refused.context["partial_governed_result"] is False
    assert refused.context["writes_ledger"] is False
    assert handler.seen == 2
    assert PARTIAL_GOVERNED_RESULT_ON_ABORT is False
    assert loop_identity()["cancel_at"] == "slice-boundary"


def progress_while_running() -> None:
    """Observer sees data-points-processed and is_warming_up at each boundary."""
    token = CancelToken()
    sink = ProgressSink()

    class _Watch:
        def observe(self, progress: object) -> Result[None]:
            assert isinstance(progress, RunProgress)
            if progress.slices_completed == 1:
                assert progress.data_points_processed == 1
                assert progress.is_warming_up is True
                return token.cancel()
            return Ok(None)

    refused = run(
        slices=_slices(4),
        stream_set=("eurusd",),
        cancel=token,
        observer=_Watch(),
        embargo=3,
    )
    assert is_refusal(refused)
    completed = _unwrap(
        run(slices=_slices(3), stream_set=("eurusd",), observer=sink, embargo=1),
        "complete run",
    )
    assert completed.self_assessment["data_points_processed"] == 3
    assert sink.latest.data_points_processed == 3
    assert sink.latest.is_warming_up is False


def limit_breach_aborts() -> None:
    """Time and memory breaches surface aborted rather than hanging."""
    time_limit = _unwrap(RunLimits.try_create(time_limit=50), "time limit")
    timed_out = run(
        slices=_slices(4),
        stream_set=("eurusd",),
        limits=time_limit,
        probe=ScriptedLimitProbe(elapsed_ns=(0, 10, 100)),
    )
    assert is_refusal(timed_out)
    assert timed_out.context["cause"] == CAUSE_TIME_LIMIT
    assert timed_out.context["terminal"] == TERMINAL_ABORTED
    memory_limit = _unwrap(RunLimits.try_create(memory_limit_bytes=50), "memory limit")
    oom = run(
        slices=_slices(4),
        stream_set=("eurusd",),
        limits=memory_limit,
        probe=ScriptedLimitProbe(memory_bytes=(10, 999)),
    )
    assert is_refusal(oom)
    assert oom.context["cause"] == CAUSE_MEMORY_LIMIT
    assert oom.context["slices_completed"] == 1


def main() -> None:
    assert qmb.CANCEL_AT == CANCEL_AT
    assert qmb.TERMINAL_ABORTED == "aborted"
    cooperative_cancel_at_slice_boundary()
    print("cooperative cancel at a slice boundary")
    progress_while_running()
    print("progress data-points-processed and is_warming_up while running")
    limit_breach_aborts()
    print("time/memory limit breach is typed aborted, not a hang")
    print("no partial governed result; run writes no log or ledger")
    print("cancel and observe ok")


if __name__ == "__main__":
    main()
