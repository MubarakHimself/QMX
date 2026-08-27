"""Epic 14 · Group F — cancel & observe (Story 14.6, R26-R29).

FR-037/B-4/B-5: a signalled cancel token stops the loop cooperatively at a SLICE
BOUNDARY and returns a typed terminal state; the loop exposes progress
(data-points-processed) and an is_warming_up flag; an in-loop time/memory breach
surfaces a typed aborted terminal state (no hang); on cancellation the pure
run() returns a terminal refusal and writes nothing — no partial governed result.
Weak spot: loop.py exits (cyclomatic complexity 26 in the harness metrics).
"""

from __future__ import annotations

from _e14 import config, ok, slices

from qmf.core.chrono import Duration
from qmf.core.refusal import Ok, RefusalCategory, Result, is_refusal
from qmb.runloop import (
    CANCEL_AT,
    CAUSE_CANCEL,
    CAUSE_MEMORY_LIMIT,
    CAUSE_TIME_LIMIT,
    PARTIAL_GOVERNED_RESULT_ON_ABORT,
    TERMINAL_ABORTED,
    CancelToken,
    RunLimits,
    RunProgress,
    ScriptedLimitProbe,
    run,
)


class _CancelAfterFirstSlice:
    """A ProgressObserver that signals cancel once one slice has completed."""

    def __init__(self, token: CancelToken) -> None:
        self._token = token
        self.readings: list[RunProgress] = []

    def observe(self, progress: RunProgress) -> Result[None]:
        self.readings.append(progress)
        if progress.slices_completed == 1:
            self._token.cancel()
        return Ok(None)


class _Recorder:
    def __init__(self) -> None:
        self.readings: list[RunProgress] = []

    def observe(self, progress: RunProgress) -> Result[None]:
        self.readings.append(progress)
        return Ok(None)


# --- T-14.6-a (L2) cancel stops at the next slice boundary [R26] · P1 ---------
def test_t146a_cancel_stops_at_slice_boundary() -> None:
    # Cancel signalled before the run: aborts before any slice; typed terminal.
    pre = CancelToken()
    ok(pre.cancel())
    refused = run(slices=slices(("eurusd",), n=2), stream_set=("eurusd",), cancel=pre)
    assert is_refusal(refused) and refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["terminal"] == TERMINAL_ABORTED
    assert refused.context["cancel_at"] == CANCEL_AT == "slice-boundary"
    assert refused.context["cause"] == CAUSE_CANCEL
    # Mid-run cancel: the loop finishes the current slice and stops at the NEXT
    # boundary, not mid-slice — exactly one slice completed before the abort.
    token = CancelToken()
    observer = _CancelAfterFirstSlice(token)
    mid = run(
        slices=slices(("eurusd",), n=3),
        stream_set=("eurusd",),
        cancel=token,
        observer=observer,
    )
    assert is_refusal(mid)
    assert mid.context["terminal"] == TERMINAL_ABORTED
    assert mid.context["slices_completed"] == 1


# --- T-14.6-b (L2) progress exposes throughput and is_warming_up [R27] --------
def test_t146b_progress_is_observable() -> None:
    recorder = _Recorder()
    out = ok(run(slices=slices(("eurusd",), n=3), stream_set=("eurusd",), observer=recorder))
    assert recorder.readings, "observer was never called"
    points = [r.data_points_processed for r in recorder.readings]
    assert points == sorted(points)  # monotone non-decreasing throughput
    assert points[-1] == out.data_points_processed == 3
    for reading in recorder.readings:
        assert isinstance(reading.is_warming_up, bool)
        assert isinstance(reading.data_points_processed, int)


# --- T-14.6-c (L2) in-loop time/memory breach -> typed aborted, no hang [R28] P1
def test_t146c_limit_breach_surfaces_aborted() -> None:
    time_limited = run(
        slices=slices(("eurusd",), n=3),
        stream_set=("eurusd",),
        limits=ok(RunLimits.try_create(ok(Duration.try_create(1000)))),
        probe=ScriptedLimitProbe(elapsed_ns=(2000,)),
    )
    assert is_refusal(time_limited)
    assert time_limited.context["terminal"] == TERMINAL_ABORTED
    assert time_limited.context["cause"] == CAUSE_TIME_LIMIT
    mem_limited = run(
        slices=slices(("eurusd",), n=3),
        stream_set=("eurusd",),
        limits=ok(RunLimits.try_create(None, 100)),
        probe=ScriptedLimitProbe(memory_bytes=(999,)),
    )
    assert is_refusal(mem_limited)
    assert mem_limited.context["terminal"] == TERMINAL_ABORTED
    assert mem_limited.context["cause"] == CAUSE_MEMORY_LIMIT


# --- T-14.6-d (L2) abort writes nothing — no partial governed result [R29] · P1
def test_t146d_abort_emits_no_partial_governed_result() -> None:
    token = CancelToken()
    ok(token.cancel())
    aborted = run(slices=slices(), config=config(), cancel=token)
    assert is_refusal(aborted)
    assert PARTIAL_GOVERNED_RESULT_ON_ABORT is False
    assert "performance_result" not in aborted.context
    assert aborted.context["partial_governed_result"] is False
    assert aborted.context["writes_ledger"] is False
    assert aborted.context["writes_log"] is False
