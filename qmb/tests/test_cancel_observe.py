"""Story 14.6 — cooperative cancel and observe while a run is running."""

from __future__ import annotations

from typing import TypeVar

from qmb.config import ResolvedRunConfig
from qmb.doors import api
from qmb.ledger import RUN_ROLES
from qmb.runloop import (
    CANCEL_AT,
    CAUSE_CANCEL,
    CAUSE_MEMORY_LIMIT,
    CAUSE_TIME_LIMIT,
    MEMORY_LIMIT_KEY,
    PARTIAL_GOVERNED_RESULT_ON_ABORT,
    STREAM_SET_KEY,
    TERMINAL_ABORTED,
    TERMINAL_COMPLETE,
    TIME_LIMIT_KEY,
    CancelToken,
    ProgressSink,
    RestingIntent,
    RunLimits,
    RunProgress,
    ScriptedLimitProbe,
    SliceObservation,
    check_slice_boundary,
    limits_from_config,
    loop_identity,
    refuse_aborted,
    run,
)
from qmf.core.chrono import Duration, Instant
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import Ok, RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _obs(stream_id: str, ns: int = _NS, *, closed: bool = True) -> SliceObservation:
    return _ok(SliceObservation.try_create(stream_id, _instant(ns), closed))


def _slices(count: int) -> tuple[tuple[SliceObservation, ...], ...]:
    return tuple((_obs("eurusd", _NS + index),) for index in range(count))


def _config(**keys: object) -> ResolvedRunConfig:
    stamp = _ok(fingerprint({"n": "cancel-cfg"}))
    payload: dict[str, object] = {STREAM_SET_KEY: ("eurusd",)}
    payload.update(keys)
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys=payload,
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
    )


class _CancelAfter:
    """Cancels from inside a slice so the next slice boundary sees the token."""

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


class _Watch:
    """Records every progress publication, including while the loop is running."""

    def __init__(self, token: CancelToken | None = None, cancel_after: int | None = None) -> None:
        self.token = token
        self.cancel_after = cancel_after
        self.seen: list[RunProgress] = []

    def observe(self, progress: RunProgress) -> Result[None]:
        self.seen.append(progress)
        if (
            self.token is not None
            and self.cancel_after is not None
            and progress.slices_completed == self.cancel_after
        ):
            return self.token.cancel()
        return Ok(None)


def test_cancel_and_limit_constants_are_the_pinned_tokens() -> None:
    assert CANCEL_AT == "slice-boundary"
    assert CAUSE_CANCEL == "cancel"
    assert CAUSE_TIME_LIMIT == "time-limit"
    assert CAUSE_MEMORY_LIMIT == "memory-limit"
    assert TERMINAL_ABORTED == "aborted"
    assert TERMINAL_COMPLETE == "complete"
    assert PARTIAL_GOVERNED_RESULT_ON_ABORT is False
    assert TIME_LIMIT_KEY == "qmb_run_time_limit"
    assert MEMORY_LIMIT_KEY == "qmb_run_memory_limit"
    assert TERMINAL_ABORTED in RUN_ROLES
    identity = loop_identity()
    assert identity["cancel_at"] == CANCEL_AT
    assert identity["partial_governed_result_on_abort"] is False
    assert qmb.CANCEL_AT is CANCEL_AT
    assert qmb.TIME_LIMIT_KEY == TIME_LIMIT_KEY
    assert api.CancelToken is qmb.CancelToken
    assert api.ProgressSink is qmb.ProgressSink
    assert api.ScriptedLimitProbe is qmb.ScriptedLimitProbe
    assert api.refuse_aborted is qmb.refuse_aborted
    assert api.run is qmb.run


def test_signalled_cancel_stops_at_slice_boundary_with_aborted_terminal() -> None:
    token = CancelToken()
    handler = _CancelAfter(token, after=2)
    sink = ProgressSink()
    refused = run(
        slices=_slices(4),
        stream_set=("eurusd",),
        handler=handler,
        cancel=token,
        observer=sink,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["terminal"] == TERMINAL_ABORTED
    assert refused.context["cause"] == CAUSE_CANCEL
    assert refused.context["cancel_at"] == CANCEL_AT
    assert refused.context["ledger_role"] == "aborted"
    assert refused.context["partial_governed_result"] is False
    assert refused.context["writes_ledger"] is False
    assert refused.context["writes_log"] is False
    assert refused.context["slices_completed"] == 2
    assert refused.context["data_points_processed"] == 2
    assert handler.seen == 2
    assert sink.latest.slices_completed == 2
    assert sink.latest.data_points_processed == 2


def test_pre_cancelled_token_runs_no_slice() -> None:
    token = CancelToken()
    _ok(token.cancel())
    handler = _CancelAfter(token, after=99)
    refused = run(
        slices=_slices(3),
        stream_set=("eurusd",),
        handler=handler,
        cancel=token,
    )
    assert is_refusal(refused)
    assert refused.context["terminal"] == TERMINAL_ABORTED
    assert refused.context["slices_completed"] == 0
    assert refused.context["data_points_processed"] == 0
    assert handler.seen == 0


def test_progress_exposes_data_points_and_is_warming_up_while_running() -> None:
    token = CancelToken()
    watch = _Watch(token, cancel_after=2)
    refused = run(
        slices=_slices(5),
        stream_set=("eurusd",),
        cancel=token,
        observer=watch,
        embargo=3,
    )
    assert is_refusal(refused)
    assert refused.context["is_warming_up"] is True
    assert [item.slices_completed for item in watch.seen] == [0, 1, 2]
    assert [item.data_points_processed for item in watch.seen] == [0, 1, 2]
    assert [item.is_warming_up for item in watch.seen] == [True, True, True]
    running = watch.seen[1]
    assert running.data_points_processed == 1
    assert running.is_warming_up is True


def test_completed_run_publishes_progress_and_complete_terminal() -> None:
    sink = ProgressSink()
    outcome = _ok(
        run(
            slices=_slices(3),
            stream_set=("eurusd",),
            observer=sink,
            embargo=1,
        )
    )
    assert outcome.self_assessment["terminal"] == TERMINAL_COMPLETE
    assert outcome.self_assessment["data_points_processed"] == 3
    assert outcome.data_points_processed == 3
    assert sink.latest.slices_completed == 3
    assert sink.latest.data_points_processed == 3
    assert sink.latest.is_warming_up is False
    assert outcome.is_warming_up is False
    assert sink.latest.frontier is not None
    assert sink.latest.frontier.value_ns == _NS + 2


def test_time_limit_breach_is_typed_aborted_not_a_hang() -> None:
    limits = _ok(RunLimits.try_create(time_limit=50))
    probe = ScriptedLimitProbe(elapsed_ns=(0, 10, 100, 200))
    sink = ProgressSink()
    refused = run(
        slices=_slices(4),
        stream_set=("eurusd",),
        observer=sink,
        limits=limits,
        probe=probe,
    )
    assert is_refusal(refused)
    assert refused.context["terminal"] == TERMINAL_ABORTED
    assert refused.context["cause"] == CAUSE_TIME_LIMIT
    assert refused.context["time_limit_key"] == TIME_LIMIT_KEY
    assert refused.context["slices_completed"] == 2
    assert sink.latest.slices_completed == 2
    assert sink.latest.elapsed is not None
    assert sink.latest.elapsed.value_ns == 10


def test_memory_limit_breach_is_typed_aborted() -> None:
    limits = _ok(RunLimits.try_create(memory_limit_bytes=50))
    probe = ScriptedLimitProbe(memory_bytes=(10, 20, 999))
    refused = run(
        slices=_slices(4),
        stream_set=("eurusd",),
        limits=limits,
        probe=probe,
    )
    assert is_refusal(refused)
    assert refused.context["cause"] == CAUSE_MEMORY_LIMIT
    assert refused.context["memory_limit_key"] == MEMORY_LIMIT_KEY
    assert refused.context["observed_bytes"] == 999
    assert refused.context["slices_completed"] == 2
    assert refused.context["partial_governed_result"] is False


def test_declared_limits_without_probe_are_invalid_input() -> None:
    refused = run(
        slices=_slices(2),
        stream_set=("eurusd",),
        limits=_ok(RunLimits.try_create(time_limit=1)),
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "probe"


def test_cancel_during_last_slice_still_completes() -> None:
    token = CancelToken()
    handler = _CancelAfter(token, after=2)
    outcome = _ok(
        run(
            slices=_slices(2),
            stream_set=("eurusd",),
            handler=handler,
            cancel=token,
        )
    )
    assert len(outcome.slices) == 2
    assert outcome.self_assessment["terminal"] == TERMINAL_COMPLETE
    assert outcome.data_points_processed == 2


def test_unknown_cancel_handle_is_refused() -> None:
    refused = run(slices=_slices(1), stream_set=("eurusd",), cancel=object())
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "cancel"
    assert refused.context["cancel_at"] == CANCEL_AT
    also = run(slices=_slices(1), stream_set=("eurusd",), observer=object())
    assert is_refusal(also)
    assert also.context["field"] == "observer"
    probe = run(slices=_slices(1), stream_set=("eurusd",), probe=object())
    assert is_refusal(probe)
    assert probe.context["field"] == "probe"


def test_limits_from_resolved_run_config() -> None:
    duration = _ok(Duration.try_create(80))
    config = _config(**{TIME_LIMIT_KEY: duration, MEMORY_LIMIT_KEY: 64})
    extracted = _ok(limits_from_config(config))
    assert extracted is not None
    assert extracted.time_limit is not None
    assert extracted.time_limit.value_ns == 80
    assert extracted.memory_limit_bytes == 64
    probe = ScriptedLimitProbe(elapsed_ns=(0, 100), memory_bytes=(1, 1))
    refused = run(slices=_slices(3), config=config, probe=probe)
    assert is_refusal(refused)
    assert refused.context["cause"] == CAUSE_TIME_LIMIT
    mismatch = run(
        slices=_slices(1),
        config=config,
        limits=_ok(RunLimits.try_create(time_limit=1)),
        probe=probe,
    )
    assert is_refusal(mismatch)
    assert mismatch.context["field"] == "limits"


def test_progress_and_limit_construction_refusals() -> None:
    assert is_refusal(RunProgress.try_create(-1, 0, True))
    assert is_refusal(RunProgress.try_create(0, 0, "warming"))
    assert is_refusal(RunLimits.try_create(time_limit=-8))
    assert is_refusal(RunLimits.try_create(memory_limit_bytes=-1))
    assert is_refusal(RunLimits.try_create(memory_limit_bytes=True))
    assert is_refusal(limits_from_config("nope"))
    zero = _ok(RunLimits.try_create())
    assert zero.bounded is False
    mapped = _ok(RunLimits.try_create({TIME_LIMIT_KEY: 12, MEMORY_LIMIT_KEY: 4}))
    assert mapped.time_limit is not None
    assert mapped.time_limit.value_ns == 12
    assert mapped.memory_limit_bytes == 4
    token = CancelToken()
    assert is_refusal(token.cancel(""))
    assert token.is_cancelled is False
    empty = _ok(RunProgress.try_create(0, 0, False))
    aborted = refuse_aborted(cause=CAUSE_CANCEL, progress=empty)
    assert aborted.context["terminal"] == TERMINAL_ABORTED
    boundary = check_slice_boundary(
        cancel=token,
        limits=zero,
        probe=None,
        progress=empty,
    )
    assert is_ok(boundary)
    _ok(token.cancel())
    stopped = check_slice_boundary(
        cancel=token,
        limits=zero,
        probe=None,
        progress=empty,
    )
    assert is_refusal(stopped)
    assert stopped.context["cause"] == CAUSE_CANCEL
