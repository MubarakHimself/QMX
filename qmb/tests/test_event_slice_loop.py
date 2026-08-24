"""Story 14.2 — event-slice loop with six pinned identity-bearing sub-phases."""

from __future__ import annotations

from typing import TypeVar

from qmb.config import CLOCK_SIMULATED, ResolvedRunConfig
from qmb.doors import api
from qmb.runloop import (
    SAME_SLICE_NEW_INTENT_FILL,
    STREAM_SET_KEY,
    SUBPHASES,
    DeclaredStream,
    EventSlice,
    FrontierClock,
    RestingIntent,
    SilentSliceHandler,
    SliceObservation,
    StreamSet,
    fingerprint_loop,
    loop_identity,
    run,
    run_slice,
    stream_set_from_config,
)
from qmf.core.chrono import Instant
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


def _streams(*ids: str) -> StreamSet:
    return _ok(StreamSet.try_create(ids))


class _RecordingHandler:
    """Fills every eligible resting intent; mints one new intent per stream once."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.closed: list[str] = []
        self._minted: set[str] = set()

    def update_stream(
        self,
        stream_id: str,
        observation: SliceObservation | None,
        frontier: Instant,
    ) -> Result[None]:
        del observation, frontier
        self.calls.append((SUBPHASES[0], stream_id))
        return Ok(None)

    def scheduled_position_event(self, stream_id: str, frontier: Instant) -> Result[None]:
        del frontier
        self.calls.append((SUBPHASES[1], stream_id))
        return Ok(None)

    def execute_resting(
        self,
        intent: RestingIntent,
        observation: SliceObservation | None,
        frontier: Instant,
    ) -> Result[bool]:
        del observation, frontier
        self.calls.append((SUBPHASES[2], intent.stream_id))
        return Ok(True)

    def update_closed_data(
        self,
        stream_id: str,
        observation: SliceObservation,
        frontier: Instant,
    ) -> Result[None]:
        del frontier
        assert observation.closed
        self.calls.append((SUBPHASES[3], stream_id))
        self.closed.append(stream_id)
        return Ok(None)

    def mint_intents(self, stream_id: str, frontier: Instant) -> Result[object]:
        del frontier
        self.calls.append((SUBPHASES[4], stream_id))
        if stream_id in self._minted:
            return Ok(())
        self._minted.add(stream_id)
        return Ok((_intent(f"new-{stream_id}", stream_id),))


def test_subphases_are_the_pinned_identity_bearing_strings() -> None:
    assert SUBPHASES == (
        "frontier-advance",
        "scheduled-position-events",
        "resting-orders",
        "closed-data-indicators-structure",
        "strategy-callbacks",
        "new-intents-rest",
    )
    assert qmb.SUBPHASES is SUBPHASES
    assert SAME_SLICE_NEW_INTENT_FILL is False
    assert qmb.SAME_SLICE_NEW_INTENT_FILL is False
    identity = loop_identity()
    assert identity["subphases"] == SUBPHASES
    assert identity["same_slice_new_intent_fill"] is False
    assert identity["instrument_order"] == "stream-set-declaration"
    assert identity["closed_data_only"] is True


def test_changing_subphase_order_is_identity_bearing() -> None:
    canonical = _ok(fingerprint_loop())
    again = _ok(fingerprint_loop())
    assert canonical.value == again.value
    permuted = dict(loop_identity())
    permuted["subphases"] = tuple(reversed(SUBPHASES))
    changed = _ok(fingerprint(permuted))
    assert changed.value != canonical.value
    fill_flipped = dict(loop_identity())
    fill_flipped["same_slice_new_intent_fill"] = True
    assert _ok(fingerprint(fill_flipped)).value != canonical.value


def test_run_slice_executes_subphases_in_pinned_order() -> None:
    handler = _RecordingHandler()
    streams = _streams("eurusd", "gbpusd", "usdjpy")
    outcome = _ok(
        run_slice(
            (_obs("eurusd"), _obs("gbpusd"), _obs("usdjpy")),
            stream_set=streams,
            handler=handler,
        )
    )
    assert outcome.subphase_order() == SUBPHASES
    assert len(outcome.trace) == 6
    for step in outcome.trace:
        assert step.instrument_order == streams.stream_ids
    indexes = [SUBPHASES.index(name) for name, _sid in handler.calls]
    assert indexes == sorted(indexes)
    assert [sid for name, sid in handler.calls if name == SUBPHASES[0]] == [
        "eurusd",
        "gbpusd",
        "usdjpy",
    ]


def test_instruments_process_in_stream_set_declaration_order() -> None:
    handler = _RecordingHandler()
    streams = _streams("usdjpy", "eurusd", "gbpusd")
    _ok(
        run_slice(
            (_obs("gbpusd"), _obs("usdjpy"), _obs("eurusd")),
            stream_set=streams,
            handler=handler,
        )
    )
    for name in (
        SUBPHASES[0],
        SUBPHASES[1],
        SUBPHASES[3],
        SUBPHASES[4],
    ):
        assert [sid for phase, sid in handler.calls if phase == name] == list(streams.stream_ids)


def test_new_intent_is_ineligible_to_fill_against_this_slice() -> None:
    handler = _RecordingHandler()
    streams = _streams("eurusd")
    first = _ok(
        run_slice(
            (_obs("eurusd"),),
            stream_set=streams,
            handler=handler,
        )
    )
    assert first.minted == ("new-eurusd",)
    assert first.ineligible == ("new-eurusd",)
    assert first.filled == ()
    assert "fill:new-eurusd" not in first.trace[2].actions
    assert "mint:new-eurusd" in first.trace[4].actions
    assert "rest:new-eurusd" in first.trace[5].actions
    assert [item.intent_id for item in first.resting] == ["new-eurusd"]

    second = _ok(
        run_slice(
            (_obs("eurusd", _NS + 1),),
            stream_set=streams,
            current_frontier=first.frontier,
            handler=handler,
            resting=first.resting,
        )
    )
    assert "fill:new-eurusd" in second.trace[2].actions
    assert second.filled == ("new-eurusd",)
    assert "new-eurusd" not in second.minted
    assert "new-eurusd" not in [item.intent_id for item in second.resting]


def test_run_carries_resting_intents_across_slices() -> None:
    handler = _RecordingHandler()
    outcome = _ok(
        run(
            slices=(
                (_obs("eurusd"), _obs("gbpusd")),
                (_obs("eurusd", _NS + 5), _obs("gbpusd", _NS + 5)),
            ),
            stream_set=("eurusd", "gbpusd"),
            handler=handler,
        )
    )
    assert len(outcome.slices) == 2
    assert outcome.slices[0].filled == ()
    assert set(outcome.slices[0].ineligible) == {"new-eurusd", "new-gbpusd"}
    assert set(outcome.slices[1].filled) == {"new-eurusd", "new-gbpusd"}
    assert outcome.filled == ("new-eurusd", "new-gbpusd")
    assert outcome.stream_order == ("eurusd", "gbpusd")
    assert outcome.self_assessment["terminal"] == "complete"
    assert outcome.self_assessment["same_slice_new_intent_fill"] is False
    assert outcome.self_assessment["subphases"] == list(SUBPHASES)


def test_forming_bar_never_updates_indicators_or_structure() -> None:
    handler = _RecordingHandler()
    outcome = _ok(
        run_slice(
            (_obs("eurusd", closed=False), _obs("gbpusd", closed=True)),
            stream_set=("eurusd", "gbpusd"),
            handler=handler,
        )
    )
    assert handler.closed == ["gbpusd"]
    closed_trace = outcome.trace[3]
    assert closed_trace.subphase == "closed-data-indicators-structure"
    assert "skip-forming:eurusd" in closed_trace.actions
    assert "closed:gbpusd" in closed_trace.actions
    assert "closed:eurusd" not in closed_trace.actions


def test_run_is_pure_same_inputs_same_outcome() -> None:
    slices = ((_obs("eurusd"), _obs("gbpusd")),)
    stream_set = ("gbpusd", "eurusd")
    first = _ok(run(slices=slices, stream_set=stream_set, handler=SilentSliceHandler()))
    second = _ok(run(slices=slices, stream_set=stream_set, handler=SilentSliceHandler()))
    assert first.fp1_identity() == second.fp1_identity()
    assert _ok(fingerprint(first)).value == _ok(fingerprint(second)).value
    assert first.self_assessment["loop_kind"] == "event-slice"


def test_stream_set_from_resolved_run_config() -> None:
    stamp = _ok(fingerprint({"n": "cfg"}))
    config = ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd", "usdjpy")},
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
    )
    extracted = _ok(stream_set_from_config(config))
    assert extracted.stream_ids == ("eurusd", "usdjpy")
    outcome = _ok(run(slices=((_obs("eurusd"), _obs("usdjpy")),), config=config))
    assert outcome.stream_order == ("eurusd", "usdjpy")
    mismatch = run(
        slices=((_obs("eurusd"), _obs("usdjpy")),),
        config=config,
        stream_set=("usdjpy", "eurusd"),
    )
    assert is_refusal(mismatch)
    assert mismatch.category is RefusalCategory.INVALID_INPUT


def test_unknown_stream_and_empty_inputs_refuse() -> None:
    missing = run_slice((_obs("gbpusd"),), stream_set=("eurusd",))
    assert is_refusal(missing)
    assert missing.context["field"] == "stream_id"

    empty_set = StreamSet.try_create(())
    assert is_refusal(empty_set)
    assert empty_set.context["field"] == "stream_set"

    empty_run = run(slices=(), stream_set=("eurusd",))
    assert is_refusal(empty_run)
    assert empty_run.context["field"] == "slices"

    mixed = EventSlice.try_create((_obs("eurusd", _NS), _obs("gbpusd", _NS + 1)))
    assert is_refusal(mixed)
    assert mixed.context["field"] == "event_slice"


def test_simulated_clock_advance_is_refused() -> None:
    clock = _ok(FrontierClock.try_create(boot_epoch_id="boot-sim", clock_binding=CLOCK_SIMULATED))
    refused = run_slice((_obs("eurusd"),), stream_set=("eurusd",), clock=clock)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["gap"] == "GAP-0048"


def test_handler_refusal_is_returned() -> None:
    class _Boom:
        def update_stream(
            self,
            stream_id: str,
            observation: SliceObservation | None,
            frontier: Instant,
        ) -> Result[None]:
            del stream_id, observation, frontier
            from qmb._refuse import invalid

            return invalid("update_stream", "injected refusal")

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

    refused = run_slice((_obs("eurusd"),), stream_set=("eurusd",), handler=_Boom())
    assert is_refusal(refused)
    assert refused.context["field"] == "update_stream"


def test_no_fill_empty_stream_and_validation_refusals() -> None:
    outcome = _ok(
        run_slice(
            (_obs("eurusd"),),
            stream_set=("eurusd", "gbpusd"),
            handler=SilentSliceHandler(),
            resting=_intent("rest-1", "eurusd"),
        )
    )
    assert "empty:gbpusd" in outcome.trace[0].actions
    assert "no-fill:rest-1" in outcome.trace[2].actions
    assert "empty:gbpusd" in outcome.trace[3].actions
    assert [item.intent_id for item in outcome.resting] == ["rest-1"]

    mapped_slice = _ok(
        EventSlice.try_create([{"stream_id": "eurusd", "instant": _instant(), "closed": True}])
    )
    mapped = _ok(
        run_slice(
            mapped_slice,
            stream_set=[{"stream_id": "eurusd", "instrument_id": "EURUSD", "role": "trading"}],
        )
    )
    assert mapped.subphase_order() == SUBPHASES
    assert _ok(DeclaredStream.try_create("eurusd")).role == "trading"

    assert is_refusal(run(slices=((_obs("eurusd"),),)))
    assert is_refusal(run_slice((_obs("eurusd"),), stream_set=("eurusd",), handler=object()))
    assert is_refusal(run(slices=((_obs("eurusd"),),), stream_set=("eurusd",), clock=object()))
    assert is_refusal(StreamSet.try_create(("dup", "dup")))
    assert is_refusal(DeclaredStream.try_create("a", role="live"))
    assert is_refusal(stream_set_from_config("nope"))
    assert is_refusal(run_slice((_obs("eurusd"),), stream_set=("eurusd",), current_frontier=1))
    assert is_refusal(
        run_slice((_obs("eurusd"),), stream_set=("eurusd",), resting=_intent("x", "nonesuch"))
    )
    rewind = run(
        slices=((_obs("eurusd", _NS + 10),), (_obs("eurusd", _NS),)),
        stream_set=("eurusd",),
    )
    assert is_refusal(rewind)
    assert rewind.category is RefusalCategory.INVALID_INPUT


class _MintForeign:
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
        return Ok((_intent("foreign", "nonesuch"),))


def test_minted_intent_must_name_a_declared_stream() -> None:
    refused = run_slice((_obs("eurusd"),), stream_set=("eurusd",), handler=_MintForeign())
    assert is_refusal(refused)
    assert refused.context["field"] == "stream_id"


def test_public_exports_and_door_parity() -> None:
    assert qmb.run is run
    assert qmb.run_slice is run_slice
    assert api.run is qmb.run
    assert api.run_slice is qmb.run_slice
    assert api.SUBPHASES is qmb.SUBPHASES
    assert api.fingerprint_loop is qmb.fingerprint_loop
    assert "run" in qmb.__all__
    assert "run_slice" in qmb.__all__
    assert "StreamSet" in qmb.__all__
    first = _ok(run(slices=((_obs("eurusd"),),), stream_set=("eurusd",)))
    assert first.slices[0].subphase_order() == SUBPHASES
