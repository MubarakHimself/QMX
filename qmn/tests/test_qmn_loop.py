"""Story 24.4 — recording accumulator + unforked QMB run_slice loop."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import TypeVar, cast

import pytest
from qmb.runloop import SUBPHASES, DeclaredStream, SilentSliceHandler, StreamSet
from qmf.core import (
    Account,
    AccountRole,
    DataDrivenClock,
    Instant,
    Ok,
    RefusalCategory,
    Result,
    SinkAck,
    SinkResult,
    TypedRefusal,
    VenueId,
    WriterId,
    is_ok,
    is_refusal,
)
from qmn.loop import (
    DATA_QUALITY_EVENT_TYPE,
    PINNED_SUBPHASES,
    CommandStreamLoop,
    CycleBand,
    ObservationClass,
    RecordingAccumulator,
    classify_observation,
    clear_first_writer_registry,
    entry_side_refused,
    first_writer_for,
    forming_bars_actionable,
    forming_bars_visible,
    protection_enactable,
    stream_key,
)

T = TypeVar("T")

_BOOT = "boot-epoch-loop-24-4"
_WALL_NS = 1_725_000_000 * 1_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]) -> TypedRefusal:
    assert is_refusal(result), result
    return result


def _as_map(value: object) -> dict[str, object]:
    assert isinstance(value, Mapping)
    return dict(cast("Mapping[str, object]", value))


def _venue(value: str = "venue-ctrader-demo") -> VenueId:
    return _ok(VenueId.try_create(value))


def _account(venue: VenueId | None = None) -> Account:
    return _ok(Account.try_create("acct-loop-1", venue or _venue(), AccountRole.DEMO))


def _writer(venue: VenueId, account: Account) -> WriterId:
    return _ok(
        WriterId.try_create(
            "vps-fra-01",
            "ctrader-adapter",
            f"{venue.value}:{account.account_id}",
            _BOOT,
        )
    )


def _clock(*, frames: int = 64, mono_step_ns: int = 1_000_000) -> DataDrivenClock:
    walls = tuple(_ok(Instant.try_create(_WALL_NS + i * 1_000_000)) for i in range(frames))
    monos = tuple(7_000_000_000 + i * mono_step_ns for i in range(frames))
    return DataDrivenClock(boot_epoch_id=_BOOT, wall_instants=walls, monotonic_ns=monos)


def _instant(ns: int) -> Instant:
    return _ok(Instant.try_create(ns))


class FakeObservationSink:
    def __init__(self) -> None:
        self.emitted: list[object] = []

    def emit(self, observation: object, /) -> SinkResult:
        self.emitted.append(observation)
        return Ok(SinkAck())


class FakeJournalSink:
    def __init__(self) -> None:
        self.appended: list[object] = []

    def append(self, event: object, /) -> SinkResult:
        self.appended.append(event)
        return Ok(SinkAck())


@pytest.fixture(autouse=True)
def reset_first_writer_registry() -> Iterator[None]:
    clear_first_writer_registry()
    yield
    clear_first_writer_registry()


def _accumulator(
    *,
    bound: int = 8,
    venue: VenueId | None = None,
    account: Account | None = None,
    writer_name: str = "recording-accumulator",
) -> tuple[RecordingAccumulator, FakeObservationSink, FakeJournalSink]:
    v = venue or _venue()
    a = account or _account(v)
    obs = FakeObservationSink()
    journal = FakeJournalSink()
    acc = _ok(
        RecordingAccumulator.try_create(
            venue_id=v,
            account=a,
            writer_id=_writer(v, a),
            observation_sink=obs,
            journal_sink=journal,
            accumulator_bound=bound,
            writer_name=writer_name,
        )
    )
    return acc, obs, journal


def _stream_set(stream_id: str = "eurusd") -> StreamSet:
    return _ok(StreamSet.try_create([_ok(DeclaredStream.try_create(stream_id))]))


def _loop(
    *,
    bound: int = 8,
    max_slice_latency_ns: int = 50_000_000,
    mono_step_ns: int = 1_000_000,
) -> tuple[CommandStreamLoop, RecordingAccumulator, FakeObservationSink, FakeJournalSink]:
    acc, obs, journal = _accumulator(bound=bound)
    loop = _ok(
        CommandStreamLoop.try_create(
            accumulator=acc,
            stream_set=_stream_set(),
            clock=_clock(mono_step_ns=mono_step_ns),
            max_slice_latency=max_slice_latency_ns,
            handler=SilentSliceHandler(),
        )
    )
    return loop, acc, obs, journal


def test_pinned_subphases_are_qmb_unforked_identity() -> None:
    assert PINNED_SUBPHASES == SUBPHASES
    assert len(PINNED_SUBPHASES) == 6
    assert PINNED_SUBPHASES[0] == "frontier-advance"
    assert PINNED_SUBPHASES[-1] == "new-intents-rest"
    assert forming_bars_visible() is False
    assert forming_bars_actionable() is False


def test_single_first_writer_registry_refuses_sibling() -> None:
    venue = _venue()
    account = _account(venue)
    acc, _, _ = _accumulator(venue=venue, account=account, writer_name="primary")
    assert first_writer_for(venue, account) == "primary"
    assert stream_key(venue, account) == acc.key

    sibling = RecordingAccumulator.try_create(
        venue_id=venue,
        account=account,
        writer_id=_writer(venue, account),
        observation_sink=FakeObservationSink(),
        journal_sink=FakeJournalSink(),
        accumulator_bound=4,
        writer_name="sibling-feed",
    )
    refused = _refusal(sibling)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert "single first writer" in str(refused.context["reason"])


def test_record_before_foldable_through_governed_intake() -> None:
    acc, obs, journal = _accumulator()
    wall = _instant(_WALL_NS)
    pushed = _ok(
        acc.push(
            observation_id="spot-1",
            stream_id="eurusd",
            receive_wall=wall,
            payload={"kind": "spot", "bid": 1},
            kind="spot",
        )
    )
    assert pushed.observation_class is ObservationClass.MARKET_DATA
    assert len(obs.emitted) == 1
    emitted = _as_map(obs.emitted[0])
    assert emitted["kind"] == "governed-intake"
    assert emitted["foldable"] is False
    assert len(journal.appended) == 1
    journal_row = _as_map(journal.appended[0])
    assert journal_row["event_type"] == DATA_QUALITY_EVENT_TYPE
    writer = _as_map(journal_row["writer"])
    assert writer["stream"] == acc.writer_id.stream
    assert acc.depth == 1
    foldable = acc.pull_foldable()
    assert len(foldable) == 1
    assert foldable[0].observation_id == "spot-1"
    assert acc.depth == 0


def test_close_frontier_runs_unforked_slice_and_commits_cursor_after() -> None:
    loop, acc, _obs, journal = _loop()
    wall = _instant(_WALL_NS)
    _ok(
        acc.push(
            observation_id="spot-1",
            stream_id="eurusd",
            receive_wall=wall,
            payload={"kind": "spot"},
            kind="spot",
        )
    )
    assert loop.cursor.committed_observation_id is None
    assert loop.cursor.pending_observation_id is None

    driven = _ok(loop.close_frontier())
    assert driven is not None
    assert driven.subphases == PINNED_SUBPHASES
    assert driven.forming_visible is False
    assert driven.forming_actionable is False
    assert driven.latency_breached is False
    assert loop.cursor.committed_observation_id == "spot-1"
    assert loop.cursor.committed_receive_wall_ns == wall.value_ns
    assert loop.cursor.pending_observation_id is None
    assert loop.cursor.commit_count == 1
    commits = [
        row
        for row in (_as_map(item) for item in journal.appended)
        if row.get("kind") == "interpretation-cursor-commit"
    ]
    assert len(commits) == 1
    assert commits[0]["observation_id"] == "spot-1"


def test_cursor_does_not_commit_when_slice_refuses() -> None:
    loop, acc, _obs, journal = _loop()
    # Push an observation for a stream id NOT in the declared stream set → run_slice refuses.
    _ok(
        acc.push(
            observation_id="alien-1",
            stream_id="gbpusd",
            receive_wall=_instant(_WALL_NS),
            payload={"kind": "spot"},
            kind="spot",
        )
    )
    refused = _refusal(loop.close_frontier())
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert loop.cursor.committed_observation_id is None
    assert loop.cursor.pending_observation_id == "alien-1"
    assert not any(
        _as_map(row).get("kind") == "interpretation-cursor-commit" for row in journal.appended
    )


def test_market_data_coalesce_emits_data_quality_and_no_new_entry() -> None:
    acc, _obs, journal = _accumulator(bound=1)
    _ok(
        acc.push(
            observation_id="spot-1",
            stream_id="eurusd",
            receive_wall=_instant(_WALL_NS),
            payload={"kind": "spot", "n": 1},
            kind="spot",
            coalesce_key="eurusd",
        )
    )
    _ok(
        acc.push(
            observation_id="spot-2",
            stream_id="eurusd",
            receive_wall=_instant(_WALL_NS + 1_000_000),
            payload={"kind": "spot", "n": 2},
            kind="spot",
            coalesce_key="eurusd",
        )
    )
    assert acc.depth == 1
    assert acc.pull_foldable()[0].observation_id == "spot-2"
    assert acc.cycle_band is CycleBand.NO_NEW_ENTRY
    coalesce_rows = [
        row
        for row in (_as_map(item) for item in journal.appended)
        if row.get("kind") == "market-data-coalesce"
    ]
    assert len(coalesce_rows) == 1
    assert coalesce_rows[0]["event_type"] == DATA_QUALITY_EVENT_TYPE
    assert entry_side_refused(CycleBand.NO_NEW_ENTRY, act="place_order") is True
    assert entry_side_refused(CycleBand.NO_NEW_ENTRY, act="cancel_order") is False
    assert protection_enactable(CycleBand.NO_NEW_ENTRY, act="close_position") is True
    assert protection_enactable(CycleBand.NO_NEW_ENTRY, act="amend_protection") is True


def test_execution_never_dropped_under_pressure() -> None:
    acc, _obs, journal = _accumulator(bound=1)
    _ok(
        acc.push(
            observation_id="spot-1",
            stream_id="eurusd",
            receive_wall=_instant(_WALL_NS),
            payload={"kind": "spot"},
            kind="spot",
        )
    )
    _ok(
        acc.push(
            observation_id="fill-1",
            stream_id="eurusd",
            receive_wall=_instant(_WALL_NS + 1_000_000),
            payload={"kind": "fill"},
            kind="fill",
        )
    )
    batch = acc.pull_foldable()
    assert len(batch) == 1
    assert batch[0].observation_id == "fill-1"
    assert batch[0].observation_class is ObservationClass.EXECUTION
    assert acc.cycle_band is CycleBand.NO_NEW_ENTRY
    assert any(_as_map(row).get("kind") == "market-data-coalesce" for row in journal.appended)


def test_system_never_dropped_when_bound_full_of_execution() -> None:
    acc, _obs, _journal = _accumulator(bound=1)
    _ok(
        acc.push(
            observation_id="fill-1",
            stream_id="eurusd",
            receive_wall=_instant(_WALL_NS),
            payload={"kind": "fill"},
            kind="fill",
        )
    )
    refused = _refusal(
        acc.push(
            observation_id="sys-1",
            stream_id="eurusd",
            receive_wall=_instant(_WALL_NS + 1_000_000),
            payload={"kind": "heartbeat"},
            kind="heartbeat",
        )
    )
    assert refused.category is RefusalCategory.STORAGE_FAILURE
    assert acc.cycle_band is CycleBand.NO_NEW_ENTRY
    assert acc.pull_foldable()[0].observation_id == "fill-1"


def test_slice_latency_breach_journals_data_quality_and_no_new_entry() -> None:
    # Each monotonic read advances 40ms; start→end elapsed is one step (40ms) > 10ms bound.
    loop, acc, _obs, journal = _loop(max_slice_latency_ns=10_000_000, mono_step_ns=40_000_000)
    _ok(
        acc.push(
            observation_id="spot-1",
            stream_id="eurusd",
            receive_wall=_instant(_WALL_NS),
            payload={"kind": "spot"},
            kind="spot",
        )
    )
    driven = _ok(loop.close_frontier())
    assert driven is not None
    assert driven.latency_breached is True
    assert driven.cycle_band is CycleBand.NO_NEW_ENTRY
    breach_rows = [
        row
        for row in (_as_map(item) for item in journal.appended)
        if row.get("kind") == "slice-latency-breach"
    ]
    assert len(breach_rows) == 1
    assert breach_rows[0]["event_type"] == DATA_QUALITY_EVENT_TYPE
    assert breach_rows[0]["entry_side_only"] is True
    assert entry_side_refused(driven.cycle_band, act="place_order") is True
    assert protection_enactable(driven.cycle_band, act="close_all") is True


def test_forming_observation_still_preserves_invisible_actionable_law() -> None:
    loop, acc, _obs, _journal = _loop()
    _ok(
        acc.push(
            observation_id="forming-1",
            stream_id="eurusd",
            receive_wall=_instant(_WALL_NS),
            payload={"kind": "bar", "completeness": "forming"},
            kind="bar",
            closed=False,
        )
    )
    driven = _ok(loop.close_frontier())
    assert driven is not None
    assert driven.forming_visible is False
    assert driven.forming_actionable is False
    assert driven.subphases == PINNED_SUBPHASES


def test_push_from_port_observation_uses_accumulator_only() -> None:
    loop, acc, obs, journal = _loop()
    _ok(
        loop.push_from_port_observation(
            {
                "native_id": "wire-9",
                "stream_id": "eurusd",
                "wire_kind": "spot",
                "receive_wall_time_ns": _WALL_NS,
                "bid": 110,
            }
        )
    )
    assert acc.depth == 1
    assert len(obs.emitted) == 1
    assert len(journal.appended) == 1
    driven = _ok(loop.close_frontier())
    assert driven is not None
    assert loop.cursor.committed_observation_id == "wire-9"


def test_classify_observation_tokens() -> None:
    assert classify_observation("spot") is ObservationClass.MARKET_DATA
    assert classify_observation("fill") is ObservationClass.EXECUTION
    assert classify_observation("heartbeat") is ObservationClass.SYSTEM
