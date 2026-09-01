"""Story 24.9 — TN-24b/i/j venue-edge dispositions."""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    Account,
    AccountRole,
    Duration,
    Instant,
    Instrument,
    MonotonicReading,
    Ok,
    Price,
    PriceDelta,
    Quantity,
    Result,
    SinkAck,
    SinkResult,
    VenueId,
    World,
    is_ok,
)
from qmf.venue.capabilities import ErrorMap, SubmissionOutcomeClass
from qmn.order import (
    CLOSING_AUTHORITY_VENUE,
    CT29_VENUE_INITIATED_CLOSE,
    CT29_VENUE_LIQUIDATION,
    DATA_QUALITY_EVENT_TYPE,
    SUPERSEDED_BY_TERMINAL_SUBJECT,
    AccountFillStore,
    CommandIdentityBinder,
    CommandOrdinalStore,
    ConnectionCommandPacer,
    Ct29VenueCloseReason,
    FillIngestDisposition,
    OrderPath,
    OrderPathSubmission,
    OrderPathTerminalResolution,
    resolve_node_close_against_subject,
)
from qmn.venue import (
    DEEP_HISTORY_NODE_SOURCE,
    Command,
    ConformanceDouble,
    DeepHistorySourceRole,
    InboundVenueEvent,
    ObservationKind,
    OrderParameters,
    OrderType,
    SubjectResolution,
    SubmissionOutcome,
    TimeInForce,
    VenueClientKind,
    VenueNativeIdentity,
    companion_source_implementation_allowed,
    deep_history_source_inventory,
    map_requote,
    requote_error_map_row,
)

T = TypeVar("T")

_BOOT = "boot-epoch-edge-24-9"
_SESSION = "session-epoch-24-9"
_WALL_NS = 1_725_400_000 * 1_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _venue(value: str = "conformance:edge-24-9") -> VenueId:
    return _ok(VenueId.try_create(value))


def _account(venue: VenueId | None = None) -> Account:
    return _ok(Account.try_create("acct-edge-1", venue or _venue(), AccountRole.DEMO))


def _instrument(venue: VenueId | None = None) -> Instrument:
    return _ok(Instrument.try_create(venue or _venue(), "EURUSD"))


def _instant(ns: int = _WALL_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _mono(ns: int = 1) -> MonotonicReading:
    return _ok(MonotonicReading.try_create(ns, _BOOT))


def _duration(ns: int) -> Duration:
    return _ok(Duration.try_create(ns))


def _price(value: int = 1_10000, scale: int = 5) -> Price:
    return _ok(Price.try_create(value, _instrument(), scale))


def _qty(value: int = 100, scale: int = 2) -> Quantity:
    return _ok(Quantity.try_create(value, "lot", scale))


def _delta(value: int = 100, scale: int = 5) -> PriceDelta:
    return _ok(PriceDelta.try_create(value, _instrument(), scale))


def _identity(native_id: str = "deal-1") -> VenueNativeIdentity:
    return _ok(VenueNativeIdentity.try_create("ctrader", native_id, 0))


def _close_by_venue(
    *,
    subject: str = "position-7",
    at_ns: int = _WALL_NS,
    close_reason: str = CT29_VENUE_LIQUIDATION,
) -> InboundVenueEvent:
    return _ok(
        InboundVenueEvent.try_create(
            ObservationKind.CLOSE_BY_VENUE,
            _identity(f"close-{subject}"),
            _instant(at_ns),
            _mono(at_ns),
            _SESSION,
            {"wire": "close-by-venue", "close_reason": close_reason},
            subject_native_id=subject,
            venue_instant=_instant(at_ns),
        )
    )


def _fill_obs(
    *,
    subject: str = "position-7",
    at_ns: int = _WALL_NS,
) -> InboundVenueEvent:
    return _ok(
        InboundVenueEvent.try_create(
            ObservationKind.FILL,
            _identity(f"fill-{subject}"),
            _instant(at_ns),
            _mono(at_ns),
            _SESSION,
            {"wire": "fill"},
            fill_price=_price(),
            fill_quantity=_qty(),
            venue_instant=_instant(at_ns),
            subject_native_id=subject,
        )
    )


class RecordingSink:
    def __init__(self) -> None:
        self.written: list[object] = []

    def write(self, record: object, /) -> SinkResult:
        self.written.append(record)
        return Ok(SinkAck())


def _client() -> ConformanceDouble:
    client = _ok(ConformanceDouble.try_create(World.LIVE, _venue()))
    assert client.kind is VenueClientKind.CONFORMANCE
    _ok(client.open_session(_account(client.venue_id)))
    _ok(client.verify_capabilities())
    return client


def _path() -> OrderPath:
    path = _ok(
        OrderPath.try_create(
            ordinal_store=_ok(
                CommandOrdinalStore.try_create(_venue(), _account(), RecordingSink())
            ),
            binder=_ok(
                CommandIdentityBinder.try_create(RecordingSink(), injective_total=False)
            ),
            pacer=_ok(
                ConnectionCommandPacer.try_create(
                    local_queue_bound=_duration(5_000_000_000),
                    protective_reserve_capacity=2,
                    general_capacity=1,
                )
            ),
            client=_client(),
            forms_per_order_type={"market": "entry-relative", "limit": "absolute"},
            submission_deadline_duration=_duration(2_000_000_000),
        )
    )
    store = path.ordinal_store
    _ok(store.recover(0))
    _ok(path.open_sequencer())
    return path


def _close_command(*, ordinal: int = 1) -> Command:
    venue = _venue()
    account = _account(venue)
    return _ok(
        Command.close_position(
            venue,
            account,
            _SESSION,
            ordinal,
            "instrument-within-binding",
            "position-7",
        )
    )


def _params(*, with_stop: bool = True) -> OrderParameters:
    kwargs: dict[str, object] = {}
    if with_stop:
        kwargs["protective_stop_distance"] = _delta()
    return _ok(
        OrderParameters.try_create(
            OrderType.MARKET, TimeInForce.GOOD_TILL_CANCEL, _qty(), **kwargs
        )
    )


# --- TN-24b duplicate fills -------------------------------------------------


def test_equal_duplicate_fill_is_idempotently_ignored() -> None:
    store = AccountFillStore()
    content = {"price": 1.1, "qty": 100, "side": "buy"}
    first = _ok(
        store.ingest(account_id="acct-1", venue_native_id="deal-9", content=content)
    )
    second = _ok(
        store.ingest(account_id="acct-1", venue_native_id="deal-9", content=dict(content))
    )
    assert first.disposition is FillIngestDisposition.ACCEPTED
    assert first.virtual_ledger_effect is True
    assert second.disposition is FillIngestDisposition.IDEMPOTENT_IGNORE
    assert second.virtual_ledger_effect is False
    assert second.data_quality_alarm is False
    assert store.virtual_ledger_effect_count == 1
    assert len(store.retained_for("acct-1", "deal-9")) == 1


def test_conflicting_duplicate_fill_alarms_preserves_both_no_second_ledger() -> None:
    store = AccountFillStore()
    first = _ok(
        store.ingest(
            account_id="acct-1",
            venue_native_id="exec-3",
            content={"price": 1.1, "qty": 100},
        )
    )
    conflict = _ok(
        store.ingest(
            account_id="acct-1",
            venue_native_id="exec-3",
            content={"price": 1.2, "qty": 100},
        )
    )
    assert first.disposition is FillIngestDisposition.ACCEPTED
    assert conflict.disposition is FillIngestDisposition.DATA_QUALITY_CONFLICT
    assert conflict.data_quality_alarm is True
    assert conflict.journal_event_type == DATA_QUALITY_EVENT_TYPE
    assert conflict.virtual_ledger_effect is False
    assert conflict.overwritten is False
    retained = store.retained_for("acct-1", "exec-3")
    assert len(retained) == 2
    assert retained[0].content["price"] == 1.1
    assert retained[1].content["price"] == 1.2
    assert store.virtual_ledger_effect_count == 1


def test_same_native_id_different_accounts_are_independent() -> None:
    store = AccountFillStore()
    _ok(store.ingest(account_id="a", venue_native_id="deal-1", content={"n": 1}))
    _ok(store.ingest(account_id="b", venue_native_id="deal-1", content={"n": 1}))
    assert store.virtual_ledger_effect_count == 2


# --- TN-24i requote + deep-history inventory --------------------------------


def test_requote_is_ordinary_mapped_rejected_by_venue() -> None:
    row = _ok(requote_error_map_row(venue_code="REQUOTE", context="place_order"))
    error_map = _ok(ErrorMap.try_create(1, [row]))
    mapped = _ok(map_requote(error_map, "REQUOTE", "place_order"))
    assert mapped.is_ordinary_rejection is True
    assert mapped.outcome_class is SubmissionOutcomeClass.REJECTED_BY_VENUE
    assert mapped.minted_outcome_type is None
    assert mapped.mapped is True


def test_requote_does_not_mint_requote_outcome_class() -> None:
    assert "requote" not in {m.value for m in SubmissionOutcome}
    assert SubmissionOutcomeClass.REJECTED_BY_VENUE.value == "rejected-by-venue"


def test_deep_history_inventory_dukascopy_node_companions_only() -> None:
    inventory = deep_history_source_inventory()
    assert inventory[DEEP_HISTORY_NODE_SOURCE] is DeepHistorySourceRole.NODE_SOURCE
    assert inventory["truefx"] is DeepHistorySourceRole.NONBLOCKING_COMPANION
    assert inventory["histdata"] is DeepHistorySourceRole.NONBLOCKING_COMPANION
    assert companion_source_implementation_allowed() is False


# --- TN-24j node close vs venue terminal ------------------------------------


def test_superseded_by_terminal_is_rejected_by_venue_never_unknown() -> None:
    close = _close_command()
    terminal = _close_by_venue(at_ns=_WALL_NS + 1_000)
    disposition = _ok(
        resolve_node_close_against_subject(
            close,
            observations=[terminal],
            submit_stamp=_instant(_WALL_NS),
            subject_present_at_submission=True,
            venue_close_reason=Ct29VenueCloseReason.VENUE_LIQUIDATION,
        )
    )
    assert disposition.resolution is SubjectResolution.SUPERSEDED_BY_TERMINAL_SUBJECT
    assert disposition.outcome is SubmissionOutcome.REJECTED_BY_VENUE
    assert disposition.outcome is not SubmissionOutcome.UNKNOWN
    assert disposition.is_unknown is False
    assert disposition.qualifier == SUPERSEDED_BY_TERMINAL_SUBJECT
    assert disposition.close_reason is Ct29VenueCloseReason.VENUE_LIQUIDATION
    assert disposition.closing_authority == CLOSING_AUTHORITY_VENUE
    assert disposition.resolving_evidence is not None
    assert disposition.resolving_evidence["named_resolving_evidence"] is True


def test_venue_initiated_close_reason_carries_venue_authority() -> None:
    close = _close_command()
    terminal = _close_by_venue(
        at_ns=_WALL_NS,
        close_reason=CT29_VENUE_INITIATED_CLOSE,
    )
    disposition = _ok(
        resolve_node_close_against_subject(
            close,
            observations=[terminal],
            submit_stamp=_instant(_WALL_NS),
            subject_present_at_submission=True,
            venue_close_reason=Ct29VenueCloseReason.VENUE_INITIATED_CLOSE,
        )
    )
    assert disposition.close_reason is Ct29VenueCloseReason.VENUE_INITIATED_CLOSE
    assert disposition.closing_authority == CLOSING_AUTHORITY_VENUE
    assert disposition.qualifier == SUPERSEDED_BY_TERMINAL_SUBJECT


def test_subject_absent_before_handoff_resolves_without_submission() -> None:
    path = _path()
    close = _close_command(ordinal=_ok(path.mint_ordinal()))
    result = _ok(
        path.submit_authorized(
            close,
            enqueued_at=_mono(10),
            now_mono=_mono(11),
            handed_off_at=_instant(),
            subject_present_at_submission=False,
            subject_observations=(),
        )
    )
    assert isinstance(result, OrderPathTerminalResolution)
    assert result.submitted is False
    assert result.is_naked_close is False
    assert result.disposition.resolution is SubjectResolution.RESOLVE_WITHOUT_SUBMISSION
    assert result.disposition.outcome is None
    assert result.disposition.submitted is False


def test_subject_terminal_before_handoff_resolves_without_submission() -> None:
    path = _path()
    close = _close_command(ordinal=_ok(path.mint_ordinal()))
    prior = _fill_obs(at_ns=_WALL_NS - 5_000)
    result = _ok(
        path.submit_authorized(
            close,
            enqueued_at=_mono(10),
            now_mono=_mono(11),
            handed_off_at=_instant(_WALL_NS),
            subject_present_at_submission=True,
            subject_observations=[prior],
        )
    )
    assert isinstance(result, OrderPathTerminalResolution)
    assert result.disposition.resolution is SubjectResolution.RESOLVE_WITHOUT_SUBMISSION
    assert result.is_naked_close is False


def test_live_subject_still_submits_on_order_path() -> None:
    path = _path()
    venue = _venue()
    account = _account(venue)
    place = _ok(
        Command.place_order(
            venue,
            account,
            _SESSION,
            _ok(path.mint_ordinal()),
            _params(with_stop=True),
        )
    )
    submitted = _ok(
        path.submit_authorized(
            place,
            enqueued_at=_mono(10),
            now_mono=_mono(11),
            handed_off_at=_instant(),
        )
    )
    assert isinstance(submitted, OrderPathSubmission)
    assert submitted.result.outcome is SubmissionOutcome.ACCEPTED_BY_VENUE
