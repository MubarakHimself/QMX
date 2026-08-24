"""Story 14.4 — in-loop warm-up with trading locked (SC-10, B-2)."""

from __future__ import annotations

from typing import TypeVar

from qmb.config import ResolvedRunConfig
from qmb.doors import api
from qmb.runloop import (
    EMBARGO_KEY,
    PRESEED_IS_WARMUP,
    STREAM_SET_KEY,
    SUBPHASES,
    WARMUP_ADDS_SECOND_WINDOW,
    WARMUP_MECHANISM,
    WARMUP_UNIT,
    RestingIntent,
    SilentSliceHandler,
    SliceObservation,
    SplitEmbargo,
    WarmupProgress,
    embargo_from_config,
    guard_trading,
    loop_identity,
    preseed_indicator_buffers,
    refuse_act_during_warmup,
    run,
    run_slice,
    trading_evidence_range,
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


def _intent(intent_id: str, stream_id: str) -> RestingIntent:
    return _ok(RestingIntent.try_create(intent_id, stream_id))


class _FillAlways:
    """Same adapter used in warm-up and trading; fills every eligible rest."""

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
        del stream_id, frontier
        return Ok(())


class _MintAlways:
    """Mints one intent per stream on every slice — acting during warm-up."""

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
        return Ok((_intent(f"new-{stream_id}", stream_id),))


class _MintAfterEmbargo:
    """Same adapter across the run; mints only after the embargo observation count."""

    def __init__(self, embargo: int) -> None:
        self._embargo = embargo
        self.calls = 0
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
        del observation, frontier
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
        self.calls += 1
        if self.calls <= self._embargo or stream_id in self._minted:
            return Ok(())
        self._minted.add(stream_id)
        return Ok((_intent(f"new-{stream_id}", stream_id),))


def test_warmup_identity_is_in_loop_locked_observation_count() -> None:
    identity = loop_identity()
    assert identity["warmup_mechanism"] == WARMUP_MECHANISM
    assert identity["warmup_unit"] == WARMUP_UNIT
    assert identity["warmup_adds_second_window"] is False
    assert identity["preseed_is_warmup"] is False
    assert identity["trading_locked_during_warmup"] is True
    assert WARMUP_MECHANISM == "in-loop-locked"
    assert WARMUP_UNIT == "observation-count"
    assert WARMUP_ADDS_SECOND_WINDOW is False
    assert PRESEED_IS_WARMUP is False
    assert EMBARGO_KEY == "embargo_width"
    assert qmb.WARMUP_MECHANISM is WARMUP_MECHANISM
    assert api.WARMUP_MECHANISM is qmb.WARMUP_MECHANISM
    assert api.preseed_indicator_buffers is qmb.preseed_indicator_buffers
    assert api.SplitEmbargo is qmb.SplitEmbargo


def test_warmup_uses_same_loop_and_subphases_with_trading_locked() -> None:
    handler = SilentSliceHandler()
    outcome = _ok(
        run(
            slices=(
                (_obs("eurusd", _NS),),
                (_obs("eurusd", _NS + 1),),
                (_obs("eurusd", _NS + 2),),
            ),
            stream_set=("eurusd",),
            handler=handler,
            embargo=2,
        )
    )
    assert len(outcome.slices) == 3
    for item in outcome.slices:
        assert item.subphase_order() == SUBPHASES
        assert item.trace[0].instrument_order == ("eurusd",)
    assert outcome.slices[0].is_warming_up is True
    assert outcome.slices[1].is_warming_up is True
    assert outcome.slices[2].is_warming_up is False
    assert outcome.is_warming_up is False
    assert outcome.warmup.embargo.observation_count == 2
    assert outcome.warmup.observations_processed == 3
    assert outcome.self_assessment["is_warming_up"] is False
    assert outcome.self_assessment["warmup_mechanism"] == WARMUP_MECHANISM
    assert outcome.self_assessment["evidence_covers_warmup"] is False


def test_minting_during_warmup_is_policy_rejection() -> None:
    refused = run(
        slices=((_obs("eurusd"),),),
        stream_set=("eurusd",),
        handler=_MintAlways(),
        embargo=2,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "warmup"
    assert refused.context["mechanism"] == WARMUP_MECHANISM
    also = refuse_act_during_warmup("entry")
    assert is_refusal(also)
    assert also.category is RefusalCategory.POLICY_REJECTION
    exit_act = refuse_act_during_warmup("exit")
    assert is_refusal(exit_act)
    assert exit_act.category is RefusalCategory.POLICY_REJECTION
    command = refuse_act_during_warmup("command")
    assert is_refusal(command)
    assert command.category is RefusalCategory.POLICY_REJECTION


def test_fill_during_warmup_is_policy_rejection() -> None:
    refused = run(
        slices=((_obs("eurusd"),),),
        stream_set=("eurusd",),
        handler=_FillAlways(),
        initial_resting=_intent("rest-1", "eurusd"),
        embargo=1,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "warmup"
    assert refused.context["action"] == "fill"


def test_trading_unlocks_after_embargo_observation_count() -> None:
    handler = _MintAfterEmbargo(2)
    outcome = _ok(
        run(
            slices=(
                (_obs("eurusd", _NS),),
                (_obs("eurusd", _NS + 1),),
                (_obs("eurusd", _NS + 2),),
                (_obs("eurusd", _NS + 3),),
            ),
            stream_set=("eurusd",),
            handler=handler,
            embargo=2,
        )
    )
    assert [item.is_warming_up for item in outcome.slices] == [True, True, False, False]
    assert outcome.slices[0].minted == ()
    assert outcome.slices[1].minted == ()
    assert outcome.slices[2].minted == ("new-eurusd",)
    assert outcome.slices[2].filled == ()
    assert outcome.slices[3].filled == ("new-eurusd",)
    assert outcome.filled == ("new-eurusd",)


def test_embargo_is_observation_count_never_a_duration() -> None:
    count = _ok(SplitEmbargo.try_create(3))
    assert count.observation_count == 3
    assert count.unit == WARMUP_UNIT
    named = _ok(
        SplitEmbargo.try_create({"embargo_width": 4, "split_fp1": "fp1:sha256:" + "ab" * 32})
    )
    assert named.observation_count == 4
    duration = _ok(Duration.try_create(1_000_000_000))
    refused = SplitEmbargo.try_create(duration)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == EMBARGO_KEY
    assert refused.context["unit"] == WARMUP_UNIT
    also = run(slices=((_obs("eurusd"),),), stream_set=("eurusd",), embargo=duration)
    assert is_refusal(also)
    assert also.context["field"] == EMBARGO_KEY


def test_loop_adds_no_second_window() -> None:
    second = SplitEmbargo.try_create({"embargo_width": 10, "warmup_bars": 5})
    assert is_refusal(second)
    assert second.context["warmup_adds_second_window"] is False
    only_warmup = SplitEmbargo.try_create({"warmup_bars": 5})
    assert is_refusal(only_warmup)
    assert only_warmup.context["field"] == "warmup"


def test_preseed_without_replay_is_not_warmup() -> None:
    refused = preseed_indicator_buffers({"eurusd": [1, 2, 3]})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "warmup"
    assert refused.context["preseed_is_warmup"] is False
    assert refused.context["mechanism"] == WARMUP_MECHANISM
    assert PRESEED_IS_WARMUP is False


def test_evidence_range_is_the_trading_interval_only() -> None:
    outcome = _ok(
        run(
            slices=(
                (_obs("eurusd", _NS),),
                (_obs("eurusd", _NS + 10),),
                (_obs("eurusd", _NS + 20),),
                (_obs("eurusd", _NS + 30),),
            ),
            stream_set=("eurusd",),
            embargo=2,
        )
    )
    assert outcome.slices[0].is_warming_up is True
    assert outcome.slices[1].is_warming_up is True
    trading = [item.frontier for item in outcome.slices if not item.is_warming_up]
    assert [item.value_ns for item in trading] == [_NS + 20, _NS + 30]
    assert outcome.evidence_range.start.value_ns == _NS + 20
    assert outcome.evidence_range.end.value_ns == _NS + 31
    assert outcome.evidence_range.start.value_ns != _NS
    empty = _ok(
        run(
            slices=((_obs("eurusd", _NS),), (_obs("eurusd", _NS + 1),)),
            stream_set=("eurusd",),
            embargo=3,
        )
    )
    assert [item.is_warming_up for item in empty.slices] == [True, True]
    assert empty.is_warming_up is True
    assert empty.evidence_range.start.value_ns == empty.evidence_range.end.value_ns
    assert empty.evidence_range.start.value_ns == _NS + 1


def test_forming_slice_does_not_count_as_an_observation() -> None:
    outcome = _ok(
        run(
            slices=(
                (_obs("eurusd", _NS, closed=False),),
                (_obs("eurusd", _NS + 1),),
                (_obs("eurusd", _NS + 2),),
            ),
            stream_set=("eurusd",),
            embargo=1,
        )
    )
    assert outcome.slices[0].is_warming_up is True
    assert outcome.slices[0].warmup is not None
    assert outcome.slices[0].warmup.observations_processed == 0
    assert outcome.slices[1].is_warming_up is True
    assert outcome.slices[1].warmup is not None
    assert outcome.slices[1].warmup.observations_processed == 1
    assert outcome.slices[2].is_warming_up is False


def test_embargo_from_resolved_run_config() -> None:
    stamp = _ok(fingerprint({"n": "warmup-cfg"}))
    config = ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd",), EMBARGO_KEY: 1},
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
    )
    extracted = _ok(embargo_from_config(config))
    assert extracted is not None
    assert extracted.observation_count == 1
    outcome = _ok(run(slices=((_obs("eurusd"),), (_obs("eurusd", _NS + 1),)), config=config))
    assert outcome.slices[0].is_warming_up is True
    assert outcome.slices[1].is_warming_up is False
    mismatch = run(
        slices=((_obs("eurusd"),),),
        config=config,
        embargo=9,
    )
    assert is_refusal(mismatch)
    assert mismatch.context["field"] == EMBARGO_KEY


def test_guard_trading_and_progress_helpers() -> None:
    assert is_ok(guard_trading(is_warming_up=False, action="mint"))
    locked = guard_trading(is_warming_up=True, action="command")
    assert is_refusal(locked)
    assert locked.category is RefusalCategory.POLICY_REJECTION
    progress = _ok(WarmupProgress.try_create(2))
    assert progress.is_warming_up is True
    stepped = _ok(progress.advance(1))
    assert stepped.is_warming_up is True
    done = _ok(stepped.advance(1))
    assert done.is_warming_up is False
    assert done.observations_processed == 2
    empty = _ok(trading_evidence_range((), empty_at=_instant()))
    assert empty.start.value_ns == empty.end.value_ns
    span = _ok(trading_evidence_range((_instant(_NS + 5), _instant(_NS + 8)), empty_at=_instant()))
    assert span.start.value_ns == _NS + 5
    assert span.end.value_ns == _NS + 9
    assert is_refusal(SplitEmbargo.try_create(-1))
    assert is_refusal(SplitEmbargo.try_create(True))
    assert is_refusal(embargo_from_config("nope"))
    stamp = _ok(fingerprint({"n": "omit-embargo"}))
    bare = ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd",)},
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
    )
    assert _ok(embargo_from_config(bare)) is None
    duration = _ok(Duration.try_create(5))

    class _Manifest:
        embargo_width = duration

    assert is_refusal(SplitEmbargo.try_create(_Manifest()))
    cited = _ok(SplitEmbargo.try_create(2, stamp))
    assert cited.split_fp1 == stamp.value
    assert is_refusal(SplitEmbargo.try_create(1, 0))
    assert is_refusal(SplitEmbargo.try_create({"observation_count": duration}))
    assert _ok(SplitEmbargo.try_create({"embargo": 7})).observation_count == 7
    assert is_refusal(run_slice((_obs("eurusd"),), stream_set=("eurusd",), embargo=Duration))
    assert is_refusal(run_slice((_obs("eurusd"),), stream_set=("eurusd",), warmup=object()))
    mismatch = run_slice(
        (_obs("eurusd"),),
        stream_set=("eurusd",),
        warmup=progress,
        embargo=9,
    )
    assert is_refusal(mismatch)
    assert _ok(progress.advance(0)).observations_processed == 0
    single = _ok(trading_evidence_range(_instant(_NS + 3), empty_at=_instant()))
    assert single.start.value_ns == _NS + 3
    assert is_refusal(trading_evidence_range((), empty_at=1))
    assert is_refusal(trading_evidence_range("nope", empty_at=_instant()))
    assert is_refusal(trading_evidence_range((1,), empty_at=_instant()))
    standalone = _ok(run_slice((_obs("eurusd"),), stream_set=("eurusd",), embargo=1))
    assert standalone.is_warming_up is True
    assert standalone.warmup is not None
    assert standalone.warmup.is_warming_up is False
    assert qmb.run is run
    assert "SplitEmbargo" in qmb.__all__
    assert "WarmupProgress" in qmb.__all__
    assert "preseed_indicator_buffers" in qmb.__all__
