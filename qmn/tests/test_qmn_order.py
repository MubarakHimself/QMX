"""Story 24.5 — command identity, protection priority, submission timing."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar, cast

from qmf.core import (
    Account,
    AccountRole,
    Duration,
    Instant,
    Instrument,
    MonotonicReading,
    Ok,
    PriceDelta,
    Quantity,
    RefusalCategory,
    Result,
    SinkAck,
    SinkResult,
    TypedRefusal,
    VenueId,
    World,
    is_ok,
    is_refusal,
    unpersistable,
)
from qmn.order import (
    FTR02_COMPOUND_BLOCKED,
    PACER_DOOR,
    AdmissionClass,
    CommandIdentityBinder,
    CommandOrdinalStore,
    ConnectionCommandPacer,
    JournalSequenceCursor,
    OrderPath,
    admission_class_for,
    compound_all_rejected_acceptance_blocked,
    require_venue_resident_protective_stop,
)
from qmn.venue import (
    Command,
    CompoundCommand,
    ConformanceDouble,
    OrderParameters,
    OrderType,
    TimeInForce,
    VenueClientKind,
)

T = TypeVar("T")

_BOOT = "boot-epoch-order-24-5"
_SESSION = "session-epoch-24-5"
_WALL_NS = 1_725_100_000 * 1_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]) -> TypedRefusal:
    assert is_refusal(result), result
    return result


def _venue(value: str = "conformance:order-24-5") -> VenueId:
    return _ok(VenueId.try_create(value))


def _account(venue: VenueId | None = None) -> Account:
    return _ok(Account.try_create("acct-order-1", venue or _venue(), AccountRole.DEMO))


def _instrument(venue: VenueId | None = None) -> Instrument:
    return _ok(Instrument.try_create(venue or _venue(), "EURUSD"))


def _delta(value: int = 100, scale: int = 5) -> PriceDelta:
    return _ok(PriceDelta.try_create(value, _instrument(), scale))


def _qty(value: int = 100, scale: int = 2) -> Quantity:
    return _ok(Quantity.try_create(value, "lot", scale))


def _params(*, with_stop: bool = True) -> OrderParameters:
    kwargs: dict[str, object] = {}
    if with_stop:
        kwargs["protective_stop_distance"] = _delta()
    return _ok(
        OrderParameters.try_create(OrderType.MARKET, TimeInForce.GOOD_TILL_CANCEL, _qty(), **kwargs)
    )


def _duration(ns: int) -> Duration:
    return _ok(Duration.try_create(ns))


def _instant(ns: int = _WALL_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _mono(ns: int, boot: str = _BOOT) -> MonotonicReading:
    return _ok(MonotonicReading.try_create(ns, boot))


class RecordingSink:
    def __init__(self) -> None:
        self.written: list[object] = []

    def write(self, record: object, /) -> SinkResult:
        self.written.append(record)
        return Ok(SinkAck())


class FailingSink:
    def write(self, record: object, /) -> SinkResult:
        del record
        return unpersistable("ordinal or identity sink unavailable")


def _client() -> ConformanceDouble:
    built = ConformanceDouble.try_create(World.LIVE, _venue())
    client = _ok(built)
    assert client.kind is VenueClientKind.CONFORMANCE
    _ok(client.open_session(_account(client.venue_id)))
    _ok(client.verify_capabilities())
    return client


def _ordinal_store(
    sink: RecordingSink | FailingSink | None = None,
    *,
    prior: int = 0,
) -> CommandOrdinalStore:
    record_sink: RecordingSink | FailingSink = (
        sink if sink is not None else RecordingSink()
    )
    store = _ok(CommandOrdinalStore.try_create(_venue(), _account(), record_sink))
    _ok(store.recover(prior))
    return store


def _binder(sink: RecordingSink | FailingSink | None = None) -> CommandIdentityBinder:
    return _ok(
        CommandIdentityBinder.try_create(
            sink if sink is not None else RecordingSink(),
            injective_total=False,
        )
    )


def _pacer(
    *,
    bound_ns: int = 5_000_000_000,
    reserve: int = 2,
    general: int = 1,
) -> ConnectionCommandPacer:
    return _ok(
        ConnectionCommandPacer.try_create(
            local_queue_bound=_duration(bound_ns),
            protective_reserve_capacity=reserve,
            general_capacity=general,
        )
    )


def _path(
    *,
    store: CommandOrdinalStore | None = None,
    binder: CommandIdentityBinder | None = None,
    pacer: ConnectionCommandPacer | None = None,
    client: ConformanceDouble | None = None,
    forms: dict[str, object] | None = None,
) -> OrderPath:
    path = _ok(
        OrderPath.try_create(
            ordinal_store=store or _ordinal_store(),
            binder=binder or _binder(),
            pacer=pacer or _pacer(),
            client=client or _client(),
            forms_per_order_type=forms
            if forms is not None
            else {"market": "entry-relative", "limit": "absolute"},
            submission_deadline_duration=_duration(2_000_000_000),
        )
    )
    _ok(path.open_sequencer())
    return path


def test_ordinal_distinct_from_journal_sequence_and_recovers_before_sequencer() -> None:
    sink = RecordingSink()
    store = _ok(CommandOrdinalStore.try_create(_venue(), _account(), sink))
    assert store.is_distinct_from_journal_sequence is True
    assert is_refusal(store.require_recovered_for_sequencer())
    assert is_refusal(store.allocate())

    _ok(store.recover(7))
    _ok(store.require_recovered_for_sequencer())
    first = _ok(store.allocate())
    second = _ok(store.allocate())
    assert first == 8
    assert second == 9
    assert store.high_water == 9
    assert len(sink.written) == 2

    journal = JournalSequenceCursor(writer_id="w1", boot_epoch=_BOOT, next_seq=1)
    cursor, seq = journal.allocate()
    assert seq == 1
    restarted = _ok(cursor.restart_for_boot("boot-epoch-2"))
    assert restarted.next_seq == 1
    assert restarted.boot_epoch == "boot-epoch-2"
    # Journal sequence restarted; command ordinal high-water did not.
    assert store.high_water == 9


def test_unpersistable_ordinal_blocks_allocation() -> None:
    store = _ok(CommandOrdinalStore.try_create(_venue(), _account(), FailingSink()))
    _ok(store.recover(0))
    refusal = _refusal(store.allocate())
    assert refusal.category is RefusalCategory.STORAGE_FAILURE
    assert store.high_water == 0


def test_ordinal_reuse_blocks_submission() -> None:
    store = _ordinal_store(prior=3)
    assert is_refusal(store.refuse_reuse(2))
    assert is_refusal(store.mark_submitted(2))
    fresh = _ok(store.allocate())
    _ok(store.mark_submitted(fresh))
    assert is_refusal(store.mark_submitted(fresh))


def test_place_order_without_protective_stop_refused_before_submission() -> None:
    venue = _venue()
    account = _account(venue)
    bare = _ok(
        Command.place_order(venue, account, _SESSION, 1, _params(with_stop=False))
    )
    refusal = _refusal(
        require_venue_resident_protective_stop(
            bare,
            forms_per_order_type={"market": "entry-relative"},
        )
    )
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refusal.context["field"] == "protective_stop_distance"

    missing_forms = _refusal(
        require_venue_resident_protective_stop(
            bare,
            forms_per_order_type={},
        )
    )
    assert missing_forms.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_place_order_with_entry_relative_stop_passes_gate() -> None:
    venue = _venue()
    account = _account(venue)
    cmd = _ok(Command.place_order(venue, account, _SESSION, 1, _params(with_stop=True)))
    form = _ok(
        require_venue_resident_protective_stop(
            cmd,
            forms_per_order_type={"market": "entry-relative"},
        )
    )
    assert form == "entry-relative"
    cancel = _ok(Command.cancel_order(venue, account, _SESSION, 2, "order-1"))
    assert _ok(require_venue_resident_protective_stop(cancel, forms_per_order_type={})) == (
        "not-applicable"
    )


def test_protective_reserve_unavailable_to_entry_and_priority() -> None:
    pacer = _pacer(reserve=2, general=1)
    venue = _venue()
    account = _account(venue)
    entry = _ok(Command.place_order(venue, account, _SESSION, 1, _params()))
    protect = _ok(Command.cancel_order(venue, account, _SESSION, 2, "ord-1"))

    assert _ok(admission_class_for(entry)) is AdmissionClass.ENTRY
    assert _ok(admission_class_for(protect)) is AdmissionClass.PROTECTIVE

    # Fill general capacity with a protective command.
    _ok(pacer.enqueue(protect))
    admitted = _ok(
        pacer.admit(protect, enqueued_at=_mono(1_000), now=_mono(2_000))
    )
    assert admitted.admission_class is AdmissionClass.PROTECTIVE

    # Pending protective blocks entry.
    _ok(pacer.enqueue(protect))
    _ok(pacer.enqueue(entry))
    blocked = _refusal(pacer.admit(entry, enqueued_at=_mono(3_000), now=_mono(4_000)))
    assert blocked.context["field"] == "protection_priority"
    assert blocked.context["door"] == PACER_DOOR

    # Drain the pending protective into reserve; entry still cannot use reserve.
    reserved = _ok(pacer.admit(protect, enqueued_at=_mono(5_000), now=_mono(6_000)))
    assert reserved.used_protective_reserve is True
    refused_reserve = _refusal(
        pacer.admit(entry, enqueued_at=_mono(7_000), now=_mono(8_000))
    )
    assert refused_reserve.context["field"] == "protective_reserve_capacity"


def test_local_queue_bound_is_door_refusal_not_unknown() -> None:
    pacer = _pacer(bound_ns=1_000_000)
    venue = _venue()
    account = _account(venue)
    cmd = _ok(Command.cancel_order(venue, account, _SESSION, 1, "ord-1"))
    _ok(pacer.enqueue(cmd))
    refusal = _refusal(
        pacer.admit(cmd, enqueued_at=_mono(0), now=_mono(50_000_000))
    )
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert refusal.context["field"] == "local_queue_bound"
    assert refusal.context["door"] == PACER_DOOR
    assert refusal.context["path"] == "veto"
    assert refusal.context["outcome"] == "denied-locally"
    assert "never UNKNOWN" in str(refusal.context["reason"])
    assert refusal.category is not RefusalCategory.TRANSIENT_VENUE_FAILURE


def test_submission_deadline_starts_at_wire_handoff_no_retry() -> None:
    pacer = _pacer()
    handoff_at = _instant(_WALL_NS)
    deadline = _instant(_WALL_NS + 2_000_000_000)
    handoff = _ok(
        pacer.begin_wire_handoff(
            command_fp1="fp1-cmd-1",
            handed_off_at=handoff_at,
            submission_deadline=deadline,
        )
    )
    assert handoff.handed_off_at == handoff_at
    assert handoff.submission_deadline == deadline
    assert handoff.retry_prohibited is True
    assert is_refusal(pacer.refuse_retry_after_handoff("fp1-cmd-1"))
    assert is_refusal(
        pacer.begin_wire_handoff(
            command_fp1="fp1-cmd-1",
            handed_off_at=handoff_at,
            submission_deadline=deadline,
        )
    )


def test_unpersistable_identity_blocks_before_handoff() -> None:
    path = _path(binder=_binder(FailingSink()))
    ordinal = _ok(path.mint_ordinal())
    cmd = _ok(
        Command.place_order(
            path.client.venue_id,
            _account(path.client.venue_id),
            _SESSION,
            ordinal,
            _params(with_stop=True),
        )
    )
    refusal = _refusal(
        path.submit_authorized(
            cmd,
            enqueued_at=_mono(1_000),
            now_mono=_mono(2_000),
            handed_off_at=_instant(),
        )
    )
    assert refusal.category is RefusalCategory.STORAGE_FAILURE


def test_order_path_happy_path_bind_before_handoff() -> None:
    identity_sink = RecordingSink()
    ordinal_sink = RecordingSink()
    path = _path(
        store=_ordinal_store(ordinal_sink),
        binder=_binder(identity_sink),
    )
    ordinal = _ok(path.mint_ordinal())
    cmd = _ok(
        Command.place_order(
            path.client.venue_id,
            _account(path.client.venue_id),
            _SESSION,
            ordinal,
            _params(with_stop=True),
        )
    )
    submitted = _ok(
        path.submit_authorized(
            cmd,
            enqueued_at=_mono(1_000),
            now_mono=_mono(2_000),
            handed_off_at=_instant(),
        )
    )
    assert submitted.protective_stop_form == "entry-relative"
    assert submitted.handoff.retry_prohibited is True
    assert submitted.handoff.submission_deadline.value_ns == _WALL_NS + 2_000_000_000
    assert submitted.venue_client_id.startswith("qmn-")
    assert any(
        isinstance(row, Mapping)
        and cast("Mapping[str, object]", row).get("class") == "command-ordinal-high-water"
        for row in ordinal_sink.written
    )
    # Binding persisted (CommandIdBinding object) before handoff/submit.
    assert len(identity_sink.written) >= 1
    assert is_refusal(path.retry_after_handoff(submitted.handoff.command_fp1))
    # Ordinal reuse blocked on second presentation.
    assert is_refusal(
        path.submit_authorized(
            cmd,
            enqueued_at=_mono(3_000),
            now_mono=_mono(4_000),
            handed_off_at=_instant(_WALL_NS + 10),
        )
    )


def test_ftr02_compound_all_rejected_stays_blocked() -> None:
    blocked = compound_all_rejected_acceptance_blocked()
    assert blocked.context["ftr"] == FTR02_COMPOUND_BLOCKED
    assert blocked.context["all_rejected_rule"] == "blocked-until-ftr02-annotation"
    assert blocked.context["forbidden_choice"] == (
        "rejected-by-venue",
        "partially-executed",
    )

    path = _path()
    ordinal = _ok(path.mint_ordinal())
    parent = _ok(
        Command.close_all(
            path.client.venue_id,
            _account(path.client.venue_id),
            _SESSION,
            ordinal,
            "account",
            "acct-order-1",
        )
    )
    compound = _ok(CompoundCommand.fan_out(parent, [0, 1]))
    refusal = _refusal(
        path.submit_authorized(
            compound,
            enqueued_at=_mono(1_000),
            now_mono=_mono(2_000),
            handed_off_at=_instant(),
        )
    )
    assert refusal.context["ftr"] == "FTR-02"


def test_sequencer_refuses_open_without_recovered_ordinal() -> None:
    store = _ok(CommandOrdinalStore.try_create(_venue(), _account(), RecordingSink()))
    path = _ok(
        OrderPath.try_create(
            ordinal_store=store,
            binder=_binder(),
            pacer=_pacer(),
            client=_client(),
            forms_per_order_type={"market": "entry-relative"},
            submission_deadline_duration=_duration(1_000_000_000),
        )
    )
    assert is_refusal(path.open_sequencer())
    assert path.sequencer_open is False
