"""Story 27.2 — governed live intake through the recording accumulator."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import TypeVar, cast

import pytest
from qmf.core import (
    Account,
    AccountRole,
    Instant,
    Ok,
    RefusalCategory,
    Result,
    SinkAck,
    SinkResult,
    TypedRefusal,
    VenueId,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmn.data import (
    CANONICAL_LIVE_SOURCE,
    CT13_SEVEN_EVENT_TYPES,
    FTR01_BLOCKED_KINDS,
    OBSERVATION_JOURNAL_TYPE,
    GovernedLiveIntake,
    LiveIntakeOutcome,
    assert_no_eighth_journal_type,
    journal_event_for_kind,
    refuse_observation_journal_type,
)
from qmn.loop import (
    RecordingAccumulator,
    clear_first_writer_registry,
    first_writer_for,
)
from qmn.venue.live import LiveCTraderClient, WireKind, ftr01_position_balance_blocked

T = TypeVar("T")

_BOOT = "boot-epoch-data-27-2"
_WALL_NS = 1_725_100_000 * 1_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]) -> TypedRefusal:
    assert is_refusal(result), result
    return result


def _as_map(value: object) -> dict[str, object]:
    assert isinstance(value, Mapping)
    return dict(cast("Mapping[str, object]", value))


def _venue() -> VenueId:
    return _ok(VenueId.try_create("venue-ctrader-demo"))


def _account(venue: VenueId | None = None) -> Account:
    return _ok(Account.try_create("acct-data-1", venue or _venue(), AccountRole.DEMO))


def _writer(venue: VenueId, account: Account) -> WriterId:
    return _ok(
        WriterId.try_create(
            "vps-fra-01",
            "ctrader-adapter",
            f"{venue.value}:{account.account_id}",
            _BOOT,
        )
    )


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


def _intake() -> tuple[
    GovernedLiveIntake, RecordingAccumulator, FakeObservationSink, FakeJournalSink
]:
    venue = _venue()
    account = _account(venue)
    obs = FakeObservationSink()
    journal = FakeJournalSink()
    acc = _ok(
        RecordingAccumulator.try_create(
            venue_id=venue,
            account=account,
            writer_id=_writer(venue, account),
            observation_sink=obs,
            journal_sink=journal,
            accumulator_bound=8,
        )
    )
    intake = _ok(GovernedLiveIntake.try_create(accumulator=acc, world=World.LIVE))
    return intake, acc, obs, journal


def test_closed_seven_never_includes_observation() -> None:
    assert OBSERVATION_JOURNAL_TYPE not in CT13_SEVEN_EVENT_TYPES
    refused = _refusal(refuse_observation_journal_type())
    assert refused.context["ftr"] == "FTR-01"
    assert refused.context["failure_id"] == "data.intake.observation_journal_type"
    eighth = _refusal(assert_no_eighth_journal_type("observation"))
    assert eighth.context["ftr"] == "FTR-01"
    invented = _refusal(assert_no_eighth_journal_type("reconciliation"))
    assert invented.context["failure_id"] == "data.intake.observation_journal_type"


def test_journal_mapping_skips_ftr01_position_balance() -> None:
    for kind in FTR01_BLOCKED_KINDS:
        refused = _refusal(journal_event_for_kind(kind))
        assert refused.context["ftr"] == "FTR-01"
        assert refused.context["failure_id"] == "data.intake.ftr01_mapping"
    assert _ok(journal_event_for_kind("spot")) == "data quality"
    assert _ok(journal_event_for_kind("trendbar")) == "data quality"
    assert _ok(journal_event_for_kind("depth")) == "data quality"
    assert _ok(journal_event_for_kind("fill")) == "fill"
    assert _ok(journal_event_for_kind("lifecycle")) == "order"


def test_accumulator_is_single_first_writer_and_record_precedes_fold() -> None:
    intake, acc, obs, journal = _intake()
    assert first_writer_for(acc.venue_id, acc.account) == acc.writer_name
    wall = _instant(_WALL_NS)
    receipt = _ok(
        intake.record(
            observation_id="spot-1",
            stream_id="eurusd",
            receive_wall=wall,
            payload={"kind": "spot", "bid": 1, "ask": 2},
            kind="spot",
            source=CANONICAL_LIVE_SOURCE,
            source_native_id="spot-1",
            revision="r1",
            event_time=wall,
            known_at=wall,
            raw_payload={"bid": 1, "ask": 2},
        )
    )
    assert receipt.outcome is LiveIntakeOutcome.PRODUCED
    assert receipt.foldable is True
    assert receipt.journal_event_type == "data quality"
    assert receipt.identity.source == CANONICAL_LIVE_SOURCE
    assert receipt.identity.revision == "r1"
    assert receipt.raw_payload["bid"] == 1
    assert len(obs.emitted) == 1
    emitted = _as_map(obs.emitted[0])
    assert emitted["foldable"] is False
    assert emitted["source"] == CANONICAL_LIVE_SOURCE
    assert emitted["source_native_id"] == "spot-1"
    assert emitted["revision"] == "r1"
    assert emitted["event_time_ns"] == wall.value_ns
    assert emitted["known_at_ns"] == wall.value_ns
    assert _as_map(emitted["raw_payload"])["bid"] == 1
    assert acc.depth == 1
    journal_row = _as_map(journal.appended[0])
    assert journal_row["event_type"] == "data quality"
    assert journal_row["event_type"] in CT13_SEVEN_EVENT_TYPES
    foldable = acc.pull_foldable()
    assert len(foldable) == 1
    assert foldable[0].observation_id == "spot-1"


def test_fills_and_lifecycle_journal_onto_closed_seven() -> None:
    intake, acc, _obs, journal = _intake()
    wall = _instant(_WALL_NS)
    fill = _ok(
        intake.record(
            observation_id="fill-1",
            stream_id="eurusd",
            receive_wall=wall,
            payload={"kind": "fill"},
            kind="fill",
            source_native_id="deal-9",
            revision="r1",
        )
    )
    assert fill.journal_event_type == "fill"
    life = _ok(
        intake.record(
            observation_id="ack-1",
            stream_id="eurusd",
            receive_wall=_instant(_WALL_NS + 1_000_000),
            payload={"kind": "submission-acknowledgement"},
            kind="submission-acknowledgement",
            source_native_id="order-1",
            revision="r1",
        )
    )
    assert life.journal_event_type == "order"
    types = {_as_map(row)["event_type"] for row in journal.appended}
    assert types <= CT13_SEVEN_EVENT_TYPES
    assert "observation" not in types
    assert acc.depth == 2


def test_same_revision_is_idempotent_changed_revision_appends() -> None:
    intake, acc, obs, journal = _intake()
    wall = _instant(_WALL_NS)
    first = _ok(
        intake.record(
            observation_id="tick-1",
            stream_id="eurusd",
            receive_wall=wall,
            payload={"kind": "tick", "n": 1},
            kind="tick",
            source_native_id="EURUSD#1",
            revision="r1",
        )
    )
    again = _ok(
        intake.record(
            observation_id="tick-1",
            stream_id="eurusd",
            receive_wall=_instant(_WALL_NS + 1_000_000),
            payload={"kind": "tick", "n": 1},
            kind="tick",
            source_native_id="EURUSD#1",
            revision="r1",
        )
    )
    assert again.outcome is LiveIntakeOutcome.IDEMPOTENT
    assert again.foldable is False
    assert acc.depth == 1
    assert len(obs.emitted) == 1
    assert len(journal.appended) == 1
    revised = _ok(
        intake.record(
            observation_id="tick-1b",
            stream_id="eurusd",
            receive_wall=_instant(_WALL_NS + 2_000_000),
            payload={"kind": "tick", "n": 2},
            kind="tick",
            source_native_id="EURUSD#1",
            revision="r2",
        )
    )
    assert revised.outcome is LiveIntakeOutcome.REVISED
    assert revised.foldable is True
    assert acc.depth == 2
    assert first.identity.key != revised.identity.key


def test_sibling_feed_failover_is_refused() -> None:
    intake, acc, obs, journal = _intake()
    refused = _refusal(
        intake.record(
            observation_id="spot-x",
            stream_id="eurusd",
            receive_wall=_instant(_WALL_NS),
            payload={"kind": "spot"},
            kind="spot",
            feed="truefx",
        )
    )
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["failure_id"] == "data.intake.sibling_failover"
    assert acc.depth == 0
    assert obs.emitted == []
    assert journal.appended == []


def test_ftr01_position_balance_refused_without_eighth_type() -> None:
    intake, acc, obs, journal = _intake()
    blocked = ftr01_position_balance_blocked()
    assert blocked.context["ftr"] == "FTR-01"
    for kind in (WireKind.POSITION_READBACK, WireKind.BALANCE_READBACK, "position-read-back"):
        refused = _refusal(
            intake.record(
                observation_id="pos-1",
                stream_id="eurusd",
                receive_wall=_instant(_WALL_NS),
                payload={"kind": str(kind)},
                kind=kind,
            )
        )
        assert refused.context["ftr"] == "FTR-01"
        assert "eighth" in str(refused.context["reason"]) or "mapping" in str(
            refused.context["reason"]
        )
    assert acc.depth == 0
    assert obs.emitted == []
    assert journal.appended == []


def test_observation_journal_type_refused_on_accumulator_payload() -> None:
    _intake_obj, acc, obs, journal = _intake()
    refused = _refusal(
        acc.push(
            observation_id="obs-x",
            stream_id="eurusd",
            receive_wall=_instant(_WALL_NS),
            payload={"kind": "spot", "ct13_event_type": "observation"},
            kind="spot",
        )
    )
    assert refused.context["ftr"] == "FTR-01"
    assert refused.context["failure_id"] == "data.intake.observation_journal_type"
    assert acc.depth == 0
    assert obs.emitted == []
    assert journal.appended == []


def test_live_client_records_through_accumulator_when_intake_bound() -> None:
    from qmf.core import DataDrivenClock
    from qmf.venue.capabilities import ErrorMap

    intake, acc, obs, journal = _intake()
    walls = tuple(_instant(_WALL_NS + i * 1_000_000) for i in range(8))
    monos = tuple(9_000_000_000 + i * 1_000_000 for i in range(8))
    clock = DataDrivenClock(boot_epoch_id=_BOOT, wall_instants=walls, monotonic_ns=monos)
    client = _ok(
        LiveCTraderClient.try_create(
            World.LIVE,
            acc.venue_id,
            clock=clock,
            error_map=_ok(ErrorMap.try_create(1, [])),
            intake=intake,
        )
    )
    _ok(client.open_session(acc.account))
    recorded = _ok(
        client.receive(
            WireKind.SPOT,
            {"bid": 108_523, "ask": 108_525},
            native_id="spot-live-1",
        )
    )
    assert recorded["verbatim_recorded"] is True
    assert acc.depth == 1
    assert len(obs.emitted) == 1
    emitted = _as_map(obs.emitted[0])
    assert emitted["foldable"] is False
    assert emitted["source"] == CANONICAL_LIVE_SOURCE
    assert _as_map(journal.appended[0])["event_type"] in CT13_SEVEN_EVENT_TYPES
