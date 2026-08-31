"""Story 24.3 — live cTrader client: decode, record-before-interpret, expose."""

from __future__ import annotations

from typing import TypeVar, cast

import pytest
from qmf.core import (
    Account,
    AccountRole,
    DataDrivenClock,
    Instant,
    Instrument,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    RoundingMode,
    SecretRef,
    SecretValue,
    SinkAck,
    SinkResult,
    TypedRefusal,
    VenueId,
    World,
    is_ok,
    is_refusal,
    unpersistable,
)
from qmf.venue.capabilities import ErrorMap, ErrorMapRow, SubmissionOutcomeClass
from qmf.venue.connection import ConnectionManager, venue_writer_id
from qmf.venue.events import EventRecorder, ObservationKind
from qmn.venue import (
    CT13_SEVEN_EVENT_TYPES,
    FTR01_BLOCKED_KINDS,
    VOLUME_WIRE_SCALE_EXPONENT,
    LiveCTraderClient,
    VenueClientKind,
    VenueClientPort,
    WireKind,
    conformance_measured_facts,
    ct13_journal_event_type,
    ctrader_static_declaration,
    decode_volume,
    ftr01_position_balance_blocked,
    select_venue_client,
)
from qmn.venue.verify import VenueFactVerifier

T = TypeVar("T")

_BOOT = "boot-epoch-live-24-3"
_WALL_NS = 1_724_000_000 * 1_000_000_000
# Venue event time deliberately offset from the injected receive wall.
_VENUE_MS = 1_724_000_001_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]) -> TypedRefusal:
    assert is_refusal(result), result
    return result


def _venue(value: str = "venue-ctrader-demo") -> VenueId:
    return _ok(VenueId.try_create(value))


def _account(venue: VenueId | None = None) -> Account:
    return _ok(Account.try_create("acct-live-1", venue or _venue(), AccountRole.DEMO))


def _instrument(venue: VenueId | None = None) -> Instrument:
    return _ok(Instrument.try_create(venue or _venue(), "EURUSD"))


def _instant(ns: int = _WALL_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _clock(*, frames: int = 32) -> DataDrivenClock:
    walls = tuple(_instant(_WALL_NS + i * 1_000_000) for i in range(frames))
    monos = tuple(5_000_000_000 + i * 1_000_000 for i in range(frames))
    return DataDrivenClock(boot_epoch_id=_BOOT, wall_instants=walls, monotonic_ns=monos)


def _error_map(*, mapped_code: str | None = "11") -> ErrorMap:
    rows: list[ErrorMapRow] = []
    if mapped_code is not None:
        rows.append(
            _ok(
                ErrorMapRow.try_create(
                    mapped_code,
                    "place_order",
                    RefusalCategory.TRANSIENT_VENUE_FAILURE,
                    Retryability.AFTER_CONDITION,
                    SubmissionOutcomeClass.UNKNOWN,
                    after_condition="rate-window-regained",
                )
            )
        )
    return _ok(ErrorMap.try_create(1, rows))


class FakeSecretStore:
    def __init__(self) -> None:
        self._values: dict[SecretRef, SecretValue] = {}

    def read(self, ref: SecretRef, /) -> Result[SecretValue]:
        if ref not in self._values:
            return unpersistable("no such credential")
        return Ok(self._values[ref])

    def atomic_replace(self, ref: SecretRef, new_value: SecretValue, /) -> Result[SecretRef]:
        self._values[ref] = new_value
        return Ok(ref)


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


class FakeRecordSink:
    def __init__(self) -> None:
        self.written: list[object] = []

    def write(self, record: object, /) -> SinkResult:
        self.written.append(record)
        return Ok(SinkAck())


class _Sinks:
    def __init__(self) -> None:
        self.store = FakeSecretStore()
        self.obs = FakeObservationSink()
        self.journal = FakeJournalSink()
        self.record = FakeRecordSink()


def _manager(sinks: _Sinks, venue: VenueId, account: Account) -> ConnectionManager:
    writer = _ok(venue_writer_id("vps-fra-01", "ctrader-adapter", venue, account, _BOOT))
    return _ok(
        ConnectionManager.try_create(writer, sinks.store, sinks.obs, sinks.journal, sinks.record)
    )


def _client(
    *,
    with_sinks: bool = False,
    frames: int = 32,
) -> tuple[LiveCTraderClient, _Sinks | None]:
    venue = _venue()
    account = _account(venue)
    sinks: _Sinks | None = None
    cm = None
    recorder = None
    if with_sinks:
        sinks = _Sinks()
        cm = _manager(sinks, venue, account)
        recorder = _ok(EventRecorder.try_create(cm))
    built = LiveCTraderClient.try_create(
        World.LIVE,
        venue,
        clock=_clock(frames=frames),
        error_map=_error_map(),
        connection_manager=cm,
        recorder=recorder,
    )
    client = _ok(built)
    _ok(client.open_session(account))
    return client, sinks


def _accept_verification(client: LiveCTraderClient) -> None:
    account = client.account
    assert account is not None
    decl = _ok(ctrader_static_declaration())
    verifier = _ok(VenueFactVerifier.try_create(decl, client.venue_id, account))
    bundle = _ok(conformance_measured_facts(received_at=_instant()))
    outcome = _ok(verifier.verify(bundle, received_at=_instant()))
    _ok(client.accept_verification(outcome))
    _ok(client.verify_capabilities())


def test_selection_resolves_ctrader_kind_for_live_venue() -> None:
    selected = select_venue_client(World.LIVE, _venue())
    assert is_ok(selected)
    assert selected.value.kind is VenueClientKind.CTRADER


def test_live_client_is_venue_client_port() -> None:
    client, _ = _client()
    assert isinstance(client, VenueClientPort)
    assert client.kind is VenueClientKind.CTRADER
    assert client.auto_retry_enabled is False
    assert client.commands_retried == 0


def test_ftr01_blocks_position_and_balance_without_eighth_type() -> None:
    client, _ = _client()
    blocked = ftr01_position_balance_blocked()
    assert blocked.context["ftr"] == "FTR-01"
    assert WireKind.POSITION_READBACK in FTR01_BLOCKED_KINDS
    assert WireKind.BALANCE_READBACK in FTR01_BLOCKED_KINDS

    for kind in (WireKind.POSITION_READBACK, WireKind.BALANCE_READBACK, "balance-readback"):
        refused = _refusal(client.receive(kind, {"wire": 1}, native_id="pos-1"))
        assert refused.context["ftr"] == "FTR-01"
        assert "eighth" in str(refused.context["reason"])

    mapping = _refusal(ct13_journal_event_type(WireKind.POSITION_READBACK))
    assert mapping.context["ftr"] == "FTR-01"
    # Closed seven unchanged — no invented observation journal type.
    assert "observation" not in CT13_SEVEN_EVENT_TYPES


def test_record_before_interpret_for_spot_and_trendbar_and_depth() -> None:
    client, sinks = _client(with_sinks=True)
    assert sinks is not None
    inst = _instrument(client.venue_id)

    spot = dict(
        _ok(
            client.receive(
                WireKind.SPOT,
                {"bid": 108_523, "ask": 108_525},
                native_id="spot-1",
                instrument=inst,
                venue_time_raw=_VENUE_MS,
                market_price_wire=108_523,
            )
        )
    )
    assert spot["verbatim_recorded"] is True
    assert spot["interpreted"] is True
    assert spot["times_retained_separately"] is True
    assert "receive_wall_time_ns" in spot and "venue_instant_ns" in spot
    assert spot["receive_wall_time_ns"] != spot["venue_instant_ns"]
    mapping = cast("dict[str, object]", spot["journal_mapping"])
    assert mapping["event_type"] == "data quality"
    market_price = cast("dict[str, object]", spot["market_price"])
    assert market_price["scale"] == 5

    trend = dict(
        _ok(
            client.receive(
                WireKind.TRENDBAR_IN_SPOT,
                {"open": 108_500, "high": 108_600, "low": 108_400, "close": 108_523},
                native_id="tb-1",
                instrument=inst,
                venue_time_raw=28_733_333,
                venue_time_unit="minutes",
                market_price_wire=108_523,
            )
        )
    )
    assert trend.get("kind") == "trendbar-in-spot"
    trend_mapping = cast("dict[str, object]", trend["journal_mapping"])
    assert trend_mapping["event_type"] in CT13_SEVEN_EVENT_TYPES

    depth = dict(
        _ok(
            client.receive(
                WireKind.DEPTH,
                {"quote_id": "q-1", "price": 108_523, "size": 250},
                native_id="depth-1",
                instrument=inst,
                market_price_wire=108_523,
                depth_size_wire=250,
            )
        )
    )
    volume = cast("dict[str, object]", depth["volume"])
    assert volume["scale"] == VOLUME_WIRE_SCALE_EXPONENT
    assert volume["value"] == 250

    # Verbatim then journal mapping hit the sinks before interpretation completed.
    assert len(sinks.obs.emitted) >= 3
    assert len(sinks.journal.appended) >= 3
    first_obs = cast("dict[str, object]", sinks.obs.emitted[0])
    assert first_obs["interpreted"] is False
    first_journal = cast("dict[str, object]", sinks.journal.appended[0])
    assert first_journal["event_type"] == "data quality"


def test_fill_and_lifecycle_journal_onto_ct13_seven() -> None:
    client, sinks = _client(with_sinks=True)
    assert sinks is not None
    inst = _instrument(client.venue_id)

    fill = dict(
        _ok(
            client.receive(
                WireKind.FILL,
                {"deal_id": "d-1", "volume": 100},
                native_id="fill-1",
                instrument=inst,
                venue_time_raw=_VENUE_MS,
                fill_price_wire=108_523,
                fill_volume_wire=100,
            )
        )
    )
    assert fill["ct13_event_type"] == "fill"
    fill_mapping = cast("dict[str, object]", fill["journal_mapping"])
    assert fill_mapping["event_type"] == "fill"
    assert fill["multi_room_committed"] is True

    life = dict(
        _ok(
            client.receive(
                WireKind.LIFECYCLE,
                {"order_id": "o-1", "status": "accepted"},
                native_id="life-1",
                venue_time_raw=_VENUE_MS,
                lifecycle_kind=ObservationKind.SUBMISSION_ACKNOWLEDGEMENT,
            )
        )
    )
    assert life["ct13_event_type"] == "order"
    assert life["observation_kind"] == "submission-acknowledgement"


def test_float_without_rounding_is_refused() -> None:
    client, _ = _client()
    inst = _instrument(client.venue_id)
    refused = _refusal(
        client.receive(
            WireKind.FILL,
            {"deal_id": "d-float"},
            native_id="fill-float",
            instrument=inst,
            venue_time_raw=_VENUE_MS,
            fill_price_wire=1.08523,
            fill_price_is_execution_double=True,
            fill_digits=5,
            fill_rounding=None,
            fill_volume_wire=100,
        )
    )
    assert refused.context["field"] == "fill_rounding"

    also = _refusal(decode_volume(1.5))
    assert also.context["field"] == "wire_value"

    crossed = dict(
        _ok(
            client.receive(
                WireKind.FILL,
                {"deal_id": "d-ok"},
                native_id="fill-ok",
                instrument=inst,
                venue_time_raw=_VENUE_MS,
                fill_price_wire=1.08523,
                fill_price_is_execution_double=True,
                fill_digits=5,
                fill_rounding=RoundingMode.HALF_EVEN,
                fill_volume_wire=100,
            )
        )
    )
    fill_price = cast("dict[str, object]", crossed["fill_price"])
    assert fill_price["value"] == 108_523


def test_unmapped_venue_error_alarmed_unknown_no_auto_retry() -> None:
    client, _ = _client()
    resolved = _ok(client.resolve_venue_error("99999", "place_order"))
    assert resolved.mapped is False
    assert resolved.alarm is True
    assert resolved.retryability is Retryability.NO
    assert resolved.refusal_category is RefusalCategory.TRANSIENT_VENUE_FAILURE
    assert resolved.outcome_class is SubmissionOutcomeClass.UNKNOWN
    assert resolved.venue_code == "99999"

    obs = _ok(client.observations())
    error_rows = [row for row in obs if row.get("kind") == "venue-error"]
    assert error_rows
    assert error_rows[-1]["raw_code_retained"] == "99999"
    assert error_rows[-1]["auto_retry"] is False
    assert client.commands_retried == 0
    assert client.auto_retry_enabled is False


def test_mapped_error_still_never_auto_retries() -> None:
    client, _ = _client()
    resolved = _ok(client.resolve_venue_error("11", "place_order"))
    assert resolved.mapped is True
    assert client.auto_retry_enabled is False
    assert client.commands_retried == 0


def test_reconcile_blocked_under_ftr01() -> None:
    client, _ = _client()
    refused = _refusal(client.reconcile())
    assert refused.context["ftr"] == "FTR-01"


def test_submit_sensing_only_no_retry() -> None:
    client, _ = _client()
    _accept_verification(client)
    from qmf.venue.commands import Command

    account = client.account
    assert account is not None
    command = _ok(Command.cancel_order(client.venue_id, account, "ep", 1, "sub-1"))
    refused = _refusal(client.submit(command))
    assert refused.context["auto_retry"] is False
    assert client.commands_retried == 0


def test_credential_free_path_needs_no_spotware_token() -> None:
    """Tier-1 gate: no network, no Spotware token (SC-13; AR-87)."""
    client, _ = _client()
    _accept_verification(client)
    inst = _instrument(client.venue_id)
    _ok(
        client.receive(
            WireKind.SPOT,
            {"bid": 100_000},
            native_id="spot-cred-free",
            instrument=inst,
            market_price_wire=100_000,
            venue_time_raw=_VENUE_MS,
        )
    )
    assert is_ok(client.observations())


@pytest.mark.live
def test_live_client_conformance_separately_tagged() -> None:
    """Live-client conformance is tagged extra; not the credential-free gate."""
    pytest.skip("Spotware sandbox token not a Story 24.3 prerequisite")
