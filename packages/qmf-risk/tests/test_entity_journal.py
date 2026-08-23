"""Story 10.10 — CT-25 entity journals as read-time projections."""

from __future__ import annotations

from qmf.core import (
    AccountRole,
    Instant,
    RefusalCategory,
    WriterId,
    fingerprint,
    is_ok,
    is_refusal,
    is_unpersistable,
    unpersistable,
)
from qmf.risk.control_action import (
    AuthorityKind,
    CommandStreamKey,
    SubjectScope,
    mint_control_action,
)
from qmf.risk.control_rank import ControlActionKind
from qmf.risk.journal import (
    CT25_COMMAND_FINGERPRINT_JOIN_VERSION,
    CT25_CONTRACT_FORMAT_VERSION,
    CT25_MAPPING_TABLE_VERSION,
    LEGACY_PROJECTION_NAMES,
    RECORDS_STREAM_MAPPING,
    RISK_AUTHORED_EVENT_TYPES,
    VENUE_AUTHORED_EVENT_TYPES,
    DecisionOutcome,
    EntityKind,
    EntitySelector,
    EventClass,
    JournalEventType,
    LegacyProjectionName,
    RiskAuthoredEvent,
    RiskWriterUnit,
    VenueAuthoredEvent,
    WriterScopedStream,
    block_dispatch_on_journal_failure,
    event_class_of,
    join_via_command_fingerprint,
    map_legacy_projection,
    project_entity_journal,
    project_legacy,
    reject_book_identity_in_venue_payload,
    reject_cross_role_silent_union,
    reject_entity_as_writer,
)


def _fp(label: str):
    result = fingerprint({"label": label})
    assert is_ok(result)
    return result.value


def _instant(ns: int = 1_000_000_000) -> Instant:
    result = Instant.try_create(ns)
    assert is_ok(result)
    return result.value


def _risk_event(
    *,
    event_type: JournalEventType = JournalEventType.DECISION,
    book: object = None,
    binding: object = None,
    role: AccountRole = AccountRole.LIVE,
    sequence: int = 0,
    outcome: DecisionOutcome | None = DecisionOutcome.AUTHORIZED,
    bot: object = None,
    seat: object = None,
    refusing: object = None,
    suppressing: object = None,
) -> RiskAuthoredEvent:
    book_fp = _fp("book-v1") if book is None else book
    binding_fp = _fp("binding-1") if binding is None else binding
    result = RiskAuthoredEvent.try_create(
        event_type,
        book_fp,
        binding_fp,
        role,
        sequence,
        _instant(1_000_000_000 + sequence),
        _fp(f"payload-{sequence}"),
        decision_outcome=outcome if event_type is JournalEventType.DECISION else None,
        bot_identity=bot,
        seat_binding=seat,
        refusing_door_ref=refusing,
        suppressing_authority_ref=suppressing,
    )
    assert is_ok(result), result
    return result.value


def _venue_event(
    *,
    event_type: JournalEventType = JournalEventType.ORDER,
    command: object = None,
    role: AccountRole = AccountRole.LIVE,
    sequence: int = 10,
) -> VenueAuthoredEvent:
    command_fp = _fp("cmd-1") if command is None else command
    result = VenueAuthoredEvent.try_create(
        event_type,
        command_fp,
        role,
        sequence,
        _instant(2_000_000_000 + sequence),
        _fp(f"venue-payload-{sequence}"),
    )
    assert is_ok(result), result
    return result.value


def test_contract_versions_and_mapping_table() -> None:
    assert CT25_CONTRACT_FORMAT_VERSION == 1
    assert CT25_MAPPING_TABLE_VERSION == 1
    assert CT25_COMMAND_FINGERPRINT_JOIN_VERSION == 1
    assert set(LEGACY_PROJECTION_NAMES) == set(LegacyProjectionName)
    assert set(RECORDS_STREAM_MAPPING) == set(LegacyProjectionName)
    assert RISK_AUTHORED_EVENT_TYPES.isdisjoint(VENUE_AUTHORED_EVENT_TYPES)
    assert set(JournalEventType) == RISK_AUTHORED_EVENT_TYPES | VENUE_AUTHORED_EVENT_TYPES


def test_legacy_mapping_covers_five_names_no_second_catalog() -> None:
    for name in LegacyProjectionName:
        mapped = map_legacy_projection(name)
        assert is_ok(mapped)
        assert mapped.value == RECORDS_STREAM_MAPPING[name]
        assert mapped.value <= set(JournalEventType)
    assert is_refusal(map_legacy_projection("orders_stream"))


def test_event_class_split() -> None:
    for event_type in RISK_AUTHORED_EVENT_TYPES:
        assert is_ok(event_class_of(event_type))
        assert event_class_of(event_type).value is EventClass.RISK_AUTHORED  # type: ignore[union-attr]
    for event_type in VENUE_AUTHORED_EVENT_TYPES:
        assert event_class_of(event_type).value is EventClass.VENUE_AUTHORED  # type: ignore[union-attr]


def test_entity_holds_no_writer_id() -> None:
    selector = EntitySelector.try_create(EntityKind.BOOK, _fp("book-v1"))
    assert is_ok(selector)
    assert is_ok(reject_entity_as_writer(selector.value))
    writer = WriterId.try_create("m1", "risk", "decisions", "boot-1")
    assert is_ok(writer)
    refused = reject_entity_as_writer(writer.value)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_risk_authored_carries_book_and_binding() -> None:
    event = _risk_event()
    assert event.book_definition_fingerprint == _fp("book-v1")
    assert event.binding_identity == _fp("binding-1")
    assert event.event_class is EventClass.RISK_AUTHORED
    # Decision outcome is mandatory and closed.
    assert is_refusal(
        RiskAuthoredEvent.try_create(
            JournalEventType.DECISION,
            _fp("book-v1"),
            _fp("binding-1"),
            AccountRole.LIVE,
            0,
            _instant(),
            _fp("p"),
            decision_outcome=None,
        )
    )


def test_venue_authored_never_carries_book_identity() -> None:
    refused = VenueAuthoredEvent.try_create(
        JournalEventType.ORDER,
        _fp("cmd-1"),
        AccountRole.LIVE,
        0,
        _instant(),
        _fp("p"),
        book_identity=_fp("book-v1"),
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    direct = reject_book_identity_in_venue_payload(_fp("book-v1"))
    assert direct.category is RefusalCategory.POLICY_REJECTION


def test_command_fingerprint_join() -> None:
    command = _fp("cmd-join")
    binding = _fp("binding-1")
    decision = _risk_event(binding=binding, outcome=DecisionOutcome.AUTHORIZED)
    venue = _venue_event(command=command)
    joined = join_via_command_fingerprint(
        venue,
        command_fingerprint=command,
        binding_identity=binding,
        risk_decision=decision,
    )
    assert is_ok(joined)
    assert joined.value.join_version == CT25_COMMAND_FINGERPRINT_JOIN_VERSION
    # Mismatched command fingerprint refuses.
    assert is_refusal(
        join_via_command_fingerprint(
            venue,
            command_fingerprint=_fp("other-cmd"),
            binding_identity=binding,
            risk_decision=decision,
        )
    )


def test_project_book_journal_role_scoped() -> None:
    book = _fp("book-v1")
    binding = _fp("binding-1")
    live_decision = _risk_event(book=book, binding=binding, role=AccountRole.LIVE, sequence=0)
    paper_decision = _risk_event(
        book=book, binding=binding, role=AccountRole.PAPER_VALIDATION, sequence=1
    )
    unit = RiskWriterUnit.try_create("m1", "risk", binding, "boot-1")
    assert is_ok(unit)
    writer = unit.value.as_writer_id("decisions")
    assert is_ok(writer)
    stream = WriterScopedStream.try_create(writer.value, (live_decision, paper_decision))
    assert is_ok(stream)
    selector = EntitySelector.try_create(EntityKind.BOOK, book)
    assert is_ok(selector)

    silent = project_entity_journal(
        selector.value, (stream.value,), role_scope=AccountRole.LIVE, cross_role_declared=False
    )
    assert is_refusal(silent)
    assert silent.category is RefusalCategory.INVALID_INPUT

    live_only = project_entity_journal(
        selector.value,
        (WriterScopedStream.try_create(writer.value, (live_decision,)).value,),  # type: ignore[union-attr]
        role_scope=AccountRole.LIVE,
    )
    assert is_ok(live_only)
    assert len(live_only.value.rows) == 1
    assert live_only.value.rows[0].role is AccountRole.LIVE

    cross = project_entity_journal(
        selector.value,
        (stream.value,),
        role_scope=AccountRole.LIVE,
        cross_role_declared=True,
    )
    assert is_ok(cross)
    assert len(cross.value.rows) == 2
    assert {row.role for row in cross.value.rows} == {
        AccountRole.LIVE,
        AccountRole.PAPER_VALIDATION,
    }


def test_veto_ledger_selects_refused_by_door_never_key_presence() -> None:
    book = _fp("book-v1")
    binding = _fp("binding-1")
    authorized = _risk_event(book=book, binding=binding, outcome=DecisionOutcome.AUTHORIZED)
    refused = _risk_event(
        book=book,
        binding=binding,
        sequence=1,
        outcome=DecisionOutcome.REFUSED_BY_DOOR,
        refusing=_fp("door-ct23"),
    )
    writer = WriterId.try_create("m1", "risk", "decisions", "boot-1")
    assert is_ok(writer)
    stream = WriterScopedStream.try_create(writer.value, (authorized, refused))
    assert is_ok(stream)
    selector = EntitySelector.try_create(EntityKind.BOOK, book)
    assert is_ok(selector)
    projected = project_legacy(
        LegacyProjectionName.VETO_LEDGER,
        (stream.value,),
        selector=selector.value,
        role_scope=AccountRole.LIVE,
    )
    assert is_ok(projected)
    assert len(projected.value.rows) == 1
    source = projected.value.rows[0].source
    assert isinstance(source, RiskAuthoredEvent)
    assert source.decision_outcome is DecisionOutcome.REFUSED_BY_DOOR


def test_bot_journal_requires_seat_binding() -> None:
    assert is_refusal(EntitySelector.try_create(EntityKind.BOT, _fp("bot-1")))
    bot = _fp("bot-1")
    seat = _fp("seat-1")
    selector = EntitySelector.try_create(EntityKind.BOT, bot, seat)
    assert is_ok(selector)
    event = _risk_event(bot=bot, seat=seat)
    writer = WriterId.try_create("m1", "risk", "decisions", "boot-1")
    assert is_ok(writer)
    stream = WriterScopedStream.try_create(writer.value, (event, _risk_event(sequence=2)))
    assert is_ok(stream)
    projected = project_entity_journal(selector.value, (stream.value,), role_scope=AccountRole.LIVE)
    assert is_ok(projected)
    assert len(projected.value.rows) == 1


def test_block_dispatch_on_storage_failure() -> None:
    from qmf.core import VenueId

    venue = VenueId.try_create("ctrader")
    assert is_ok(venue)
    stream = CommandStreamKey.try_create(venue.value, "acct-1")
    assert is_ok(stream)
    minted = mint_control_action(
        ControlActionKind.SUSPEND_NEW,
        "op-1",
        AuthorityKind.OPERATOR,
        SubjectScope.BOOK,
        "book-1",
        0,
        "protection",
        stream.value,
        _instant(),
    )
    assert is_ok(minted)
    blocked = block_dispatch_on_journal_failure(
        minted.value, journal_result=unpersistable("disk full")
    )
    assert is_refusal(blocked)
    assert is_unpersistable(blocked)
    ok = block_dispatch_on_journal_failure(minted.value, journal_result=True)
    assert is_ok(ok)


def test_cross_role_helper() -> None:
    assert is_ok(
        reject_cross_role_silent_union(
            role_scope=AccountRole.LIVE,
            observed_roles=(AccountRole.LIVE,),
            cross_role_declared=False,
        )
    )
    assert is_refusal(
        reject_cross_role_silent_union(
            role_scope=AccountRole.LIVE,
            observed_roles=(AccountRole.LIVE, AccountRole.DEMO),
            cross_role_declared=False,
        )
    )
