"""Story 24.7 — amend atomicity and preserve every tightening act (QMX-F063)."""

from __future__ import annotations

from typing import TypeVar, cast

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
    RefusalCategory,
    Result,
    SinkAck,
    SinkResult,
    TypedRefusal,
    VenueId,
    World,
    is_ok,
    is_refusal,
)
from qmn.order import (
    AMEND_JOURNAL_KIND,
    CT19_CLOSED_KINDS,
    AmendAtomicity,
    AmendSequencePlan,
    BookDynamicProtectionPolicy,
    CommandIdentityBinder,
    CommandOrdinalStore,
    ConnectionCommandPacer,
    DynamicProtectionOrigin,
    OrderPath,
    admit_risk_non_increasing_amend_protection,
    ct19_kinds_are_closed,
    enforce_closed_ct19_vocabulary,
    gate_amend_protection,
    is_breakeven_ratchet_amendment,
    journal_amend_before_dispatch,
    refuse_close_partial,
    refuse_close_then_replace,
    refuse_invented_amend_sequence,
    resolve_amend_atomicity,
)
from qmn.venue import (
    Command,
    CommandKind,
    ConformanceDouble,
    OrderParameters,
    OrderType,
    ProtectionAmendment,
    ProtectionSide,
    TimeInForce,
    VenueClientKind,
)

T = TypeVar("T")

_BOOT = "boot-epoch-amend-24-7"
_SESSION = "session-epoch-24-7"
_WALL_NS = 1_725_300_000 * 1_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]) -> TypedRefusal:
    assert is_refusal(result), result
    return result


def _venue(value: str = "conformance:amend-24-7") -> VenueId:
    return _ok(VenueId.try_create(value))


def _account(venue: VenueId | None = None) -> Account:
    return _ok(Account.try_create("acct-amend-1", venue or _venue(), AccountRole.DEMO))


def _instrument(venue: VenueId | None = None) -> Instrument:
    return _ok(Instrument.try_create(venue or _venue(), "EURUSD"))


def _delta(value: int, scale: int = 5, venue: VenueId | None = None) -> PriceDelta:
    return _ok(PriceDelta.try_create(value, _instrument(venue), scale))


def _price(value: int = 1_10000, scale: int = 5, venue: VenueId | None = None) -> Price:
    return _ok(Price.try_create(value, _instrument(venue), scale))


def _qty(value: int = 100, scale: int = 2) -> Quantity:
    return _ok(Quantity.try_create(value, "lot", scale))


def _params(*, with_stop: bool = True) -> OrderParameters:
    kwargs: dict[str, object] = {}
    if with_stop:
        kwargs["protective_stop_distance"] = _delta(100)
    return _ok(
        OrderParameters.try_create(OrderType.MARKET, TimeInForce.GOOD_TILL_CANCEL, _qty(), **kwargs)
    )


def _stop_amendment(
    *,
    new_value: int = 0,
    original_value: int = 100,
    venue: VenueId | None = None,
) -> ProtectionAmendment:
    return _ok(
        ProtectionAmendment.try_create(
            ProtectionSide.STOP,
            _delta(new_value, venue=venue),
            _price(venue=venue),
            original_risk_distance=_delta(original_value, venue=venue),
        )
    )


def _amend(
    ordinal: int = 4,
    *,
    amendment: ProtectionAmendment | None = None,
    venue: VenueId | None = None,
) -> Command:
    v = venue or _venue()
    return _ok(
        Command.amend_protection(
            v,
            _account(v),
            _SESSION,
            ordinal,
            amendment if amendment is not None else _stop_amendment(venue=v),
            "position-1",
        )
    )


def _instant(ns: int = _WALL_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _mono(ns: int, boot: str = _BOOT) -> MonotonicReading:
    return _ok(MonotonicReading.try_create(ns, boot))


def _duration(ns: int) -> Duration:
    return _ok(Duration.try_create(ns))


class RecordingSink:
    def __init__(self) -> None:
        self.written: list[object] = []

    def write(self, record: object, /) -> SinkResult:
        self.written.append(record)
        return Ok(SinkAck())


class RecordingJournal:
    def __init__(self) -> None:
        self.appended: list[object] = []
        self.fail = False

    def append(self, event: object, /) -> SinkResult:
        if self.fail:
            from qmf.core import unpersistable

            return unpersistable("amend journal unavailable")
        self.appended.append(event)
        return Ok(SinkAck())


def _client() -> ConformanceDouble:
    built = ConformanceDouble.try_create(World.LIVE, _venue())
    client = _ok(built)
    assert client.kind is VenueClientKind.CONFORMANCE
    _ok(client.open_session(_account(client.venue_id)))
    _ok(client.verify_capabilities())
    return client


def _ordinal_store() -> CommandOrdinalStore:
    store = _ok(CommandOrdinalStore.try_create(_venue(), _account(), RecordingSink()))
    _ok(store.recover(0))
    return store


def _binder() -> CommandIdentityBinder:
    return _ok(CommandIdentityBinder.try_create(RecordingSink(), injective_total=False))


def _pacer() -> ConnectionCommandPacer:
    return _ok(
        ConnectionCommandPacer.try_create(
            local_queue_bound=_duration(5_000_000_000),
            protective_reserve_capacity=2,
            general_capacity=1,
        )
    )


def _path(
    *,
    atomicity: object = AmendAtomicity.UNMEASURED,
    policy: object = BookDynamicProtectionPolicy.SINGLE_SIDED_BREAKEVEN_RATCHET,
    journal: RecordingJournal | None = None,
) -> OrderPath:
    path = _ok(
        OrderPath.try_create(
            ordinal_store=_ordinal_store(),
            binder=_binder(),
            pacer=_pacer(),
            client=_client(),
            forms_per_order_type={"market": "entry-relative", "limit": "absolute"},
            submission_deadline_duration=_duration(2_000_000_000),
            amend_atomicity=atomicity,
            book_dynamic_protection_policy=policy,
            amend_journal=journal,
        )
    )
    _ok(path.open_sequencer())
    return path


# --- AC1: unmeasured amend atomicity → ratchet-only or refuse; never invent ---


def test_resolve_amend_atomicity_unmeasured_when_absent() -> None:
    assert resolve_amend_atomicity(None) is AmendAtomicity.UNMEASURED
    assert resolve_amend_atomicity("") is AmendAtomicity.UNMEASURED
    assert resolve_amend_atomicity({"other": "x"}) is AmendAtomicity.UNMEASURED
    assert resolve_amend_atomicity({"atomicity": "atomic"}) is AmendAtomicity.ATOMIC
    assert resolve_amend_atomicity("non-atomic") is AmendAtomicity.NON_ATOMIC
    assert resolve_amend_atomicity("undocumented") is AmendAtomicity.UNDOCUMENTED


def test_unmeasured_dynamic_protection_limited_to_breakeven_ratchet() -> None:
    venue = _venue()
    be = _amend(amendment=_stop_amendment(new_value=0, venue=venue), venue=venue)
    admitted = _ok(
        gate_amend_protection(
            be,
            atomicity=AmendAtomicity.UNMEASURED,
            book_policy=BookDynamicProtectionPolicy.SINGLE_SIDED_BREAKEVEN_RATCHET,
            origin=DynamicProtectionOrigin.BREAKEVEN_RATCHET,
        )
    )
    assert admitted.kind is CommandKind.AMEND_PROTECTION
    assert _ok(is_breakeven_ratchet_amendment(admitted.protection_amendment)) is True

    trailing = _amend(
        amendment=_stop_amendment(new_value=40, original_value=100, venue=venue),
        venue=venue,
    )
    refusal = _refusal(
        gate_amend_protection(
            trailing,
            atomicity=AmendAtomicity.UNMEASURED,
            book_policy=BookDynamicProtectionPolicy.SINGLE_SIDED_BREAKEVEN_RATCHET,
            origin=DynamicProtectionOrigin.BREAKEVEN_RATCHET,
        )
    )
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert "breakeven ratchet" in str(refusal.context["reason"])


def test_unmeasured_dynamic_protection_refuses_before_origination_per_book_policy() -> None:
    venue = _venue()
    be = _amend(amendment=_stop_amendment(new_value=0, venue=venue), venue=venue)
    refusal = _refusal(
        gate_amend_protection(
            be,
            atomicity=AmendAtomicity.UNDOCUMENTED,
            book_policy=BookDynamicProtectionPolicy.REFUSE_BEFORE_ORIGINATION,
            origin=DynamicProtectionOrigin.BREAKEVEN_RATCHET,
        )
    )
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert "before origination" in str(refusal.context["reason"])


def test_command_path_never_invents_amend_sequence() -> None:
    venue = _venue()
    cmd = _amend(venue=venue)
    refusal = _refusal(
        gate_amend_protection(
            cmd,
            atomicity=AmendAtomicity.ATOMIC,
            dual_side_requested=True,
        )
    )
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refusal.context["field"] == "amend_sequence"

    dual_unproven = _refusal(
        gate_amend_protection(
            cmd,
            atomicity=AmendAtomicity.NON_ATOMIC,
            dual_side_requested=True,
        )
    )
    assert dual_unproven.context["field"] == "amend_atomicity"

    invented = refuse_invented_amend_sequence(
        AmendSequencePlan(steps=("cancel_order", "place_order"), detail="cancel-replace")
    )
    assert invented.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert "cancel-then-place" in cast("list[str]", invented.context["forbidden"])


def test_bot_originated_single_sided_tighten_passes_when_unmeasured() -> None:
    # OR-01: bot may propose any risk-reducing tighten; breakeven limit is dynamic only.
    venue = _venue()
    tighten = _amend(
        amendment=_stop_amendment(new_value=50, original_value=100, venue=venue),
        venue=venue,
    )
    admitted = _ok(
        gate_amend_protection(
            tighten,
            atomicity=AmendAtomicity.UNMEASURED,
            origin=DynamicProtectionOrigin.BOT_PROPOSAL,
        )
    )
    assert admitted.kind is CommandKind.AMEND_PROTECTION


# --- AC2: amend_min_improvement never suppresses; journal before dispatch ---


def test_amend_min_improvement_never_suppresses_originated_amend() -> None:
    venue = _venue()
    cmd = _amend(
        amendment=_stop_amendment(new_value=1, original_value=100, venue=venue),
        venue=venue,
    )
    admitted = _ok(
        admit_risk_non_increasing_amend_protection(
            cmd, amend_min_improvement=0.5
        )
    )
    assert admitted is cmd

    path = _path(atomicity=AmendAtomicity.NON_ATOMIC)
    ordinal = _ok(path.mint_ordinal())
    path_cmd = _amend(
        ordinal,
        amendment=_stop_amendment(new_value=1, original_value=100, venue=venue),
        venue=venue,
    )
    submission = _ok(
        path.submit_authorized(
            path_cmd,
            enqueued_at=_mono(1_000),
            now_mono=_mono(2_000),
            handed_off_at=_instant(),
            amend_origin=DynamicProtectionOrigin.BOT_PROPOSAL,
            amend_min_improvement=0.99,  # would suppress if mis-sited as a path gate
        )
    )
    assert submission.command.kind is CommandKind.AMEND_PROTECTION


def test_amend_protection_journaled_before_dispatch() -> None:
    venue = _venue()
    journal = RecordingJournal()
    path = _path(atomicity=AmendAtomicity.UNMEASURED, journal=journal)
    ordinal = _ok(path.mint_ordinal())
    cmd = _amend(
        ordinal,
        amendment=_stop_amendment(new_value=0, venue=venue),
        venue=venue,
    )
    _ok(
        path.submit_authorized(
            cmd,
            enqueued_at=_mono(1_000),
            now_mono=_mono(2_000),
            handed_off_at=_instant(),
            amend_origin=DynamicProtectionOrigin.BREAKEVEN_RATCHET,
        )
    )
    assert len(journal.appended) == 1
    row = cast("dict[str, object]", journal.appended[0])
    assert row["kind"] == AMEND_JOURNAL_KIND
    assert row["phase"] == "before-dispatch"
    assert row["command_kind"] == CommandKind.AMEND_PROTECTION.value

    # Storage failure blocks dispatch rather than losing the intent.
    failing = RecordingJournal()
    failing.fail = True
    blocked_path = _path(journal=failing)
    blocked_ordinal = _ok(blocked_path.mint_ordinal())
    refusal = _refusal(
        blocked_path.submit_authorized(
            _amend(ordinal=blocked_ordinal, venue=venue),
            enqueued_at=_mono(3_000),
            now_mono=_mono(4_000),
            handed_off_at=_instant(_WALL_NS + 1),
        )
    )
    assert refusal.category is RefusalCategory.STORAGE_FAILURE


def test_journal_helper_records_before_dispatch() -> None:
    venue = _venue()
    journal = RecordingJournal()
    cmd = _amend(venue=venue)
    record = _ok(
        journal_amend_before_dispatch(
            cmd,
            journal=journal,
            journaled_at=_instant(),
            atomicity=AmendAtomicity.UNMEASURED,
            origin=DynamicProtectionOrigin.OPERATOR,
        )
    )
    assert record.kind == AMEND_JOURNAL_KIND
    assert record.origin == DynamicProtectionOrigin.OPERATOR.value


# --- AC3: close_partial refused; five CT-19 kinds remain closed ---


def test_close_partial_refused_and_never_emulated() -> None:
    refusal = refuse_close_partial()
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refusal.context["field"] == "close_partial"

    vocab = _refusal(enforce_closed_ct19_vocabulary("close_partial"))
    assert vocab.category is RefusalCategory.UNSUPPORTED_CAPABILITY

    emulate = refuse_close_then_replace()
    assert emulate.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert emulate.context["field"] == "close_then_replace"


def test_five_ct19_kinds_remain_closed() -> None:
    assert ct19_kinds_are_closed() is True
    assert {kind.value for kind in CommandKind} == set(CT19_CLOSED_KINDS)
    for kind in CommandKind:
        assert _ok(enforce_closed_ct19_vocabulary(kind)) == kind.value
    invent = _refusal(enforce_closed_ct19_vocabulary("amend_order"))
    assert invent.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_unknown_holds_amend_protection_as_standing_intent() -> None:
    """AC2: UNKNOWN holds a risk-non-increasing amend as standing intent."""
    from qmf.core import SecretRef, SecretValue, unpersistable
    from qmn.order import (
        CommandStreamUnknownBoundary,
        HeldProtectionAct,
        HoldDisposition,
        ProtectionIntentExtent,
    )
    from qmn.venue import (
        CommandObservation,
        ConnectionManager,
        JournalEvent,
        SubmissionOutcome,
        SubmissionResult,
        UnknownTrigger,
        venue_writer_id,
    )

    venue = _venue("conformance:amend-unknown-24-7")
    account = _account(venue)

    class _Secrets:
        def read(self, ref: SecretRef, /) -> Result[SecretValue]:
            del ref
            return unpersistable("unused")

        def atomic_replace(
            self, ref: SecretRef, new_value: SecretValue, /
        ) -> Result[SecretRef]:
            del new_value
            return Ok(ref)

    class _Obs:
        def emit(self, observation: object, /) -> SinkResult:
            del observation
            return Ok(SinkAck())

    journal = RecordingJournal()
    writer = _ok(
        venue_writer_id("vps-fra-01", "ctrader-adapter", venue, account, _BOOT)
    )
    cm = _ok(
        ConnectionManager.try_create(
            writer, _Secrets(), _Obs(), journal, RecordingSink()
        )
    )
    boundary = _ok(
        CommandStreamUnknownBoundary.try_create(
            venue_id=venue,
            account=account,
            connection_manager=cm,
            extent=_ok(ProtectionIntentExtent.try_create(4)),
        )
    )
    place = _ok(Command.place_order(venue, account, _SESSION, 1, _params()))
    fp = _ok(place.fingerprint())
    obs = CommandObservation(
        command_fp1=fp,
        kind=place.kind,
        outcome=SubmissionOutcome.UNKNOWN,
        receive_instant=_instant(),
        unknown_trigger=UnknownTrigger.TIMEOUT,
        monotonic_elapsed=_duration(750_000_000),
        submission_deadline=_instant(_WALL_NS + 5_000_000_000),
        detail="UNKNOWN is a state; amend held as standing intent",
    )
    unknown = SubmissionResult(
        command_fp1=fp,
        kind=place.kind,
        outcome=SubmissionOutcome.UNKNOWN,
        observation=obs,
        journal_event=JournalEvent.for_outcome(
            fp, place.kind, SubmissionOutcome.UNKNOWN
        ),
    )
    _ok(boundary.record_unknown(unknown))
    held = _ok(
        boundary.admit(
            _amend(ordinal=2, venue=venue),
            receive_instant=_instant(),
        )
    )
    assert isinstance(held, HeldProtectionAct)
    assert held.disposition is HoldDisposition.HELD
    assert held.kind is CommandKind.AMEND_PROTECTION
    assert len(boundary.standing_intents) == 1
