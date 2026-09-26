"""Story 3.6 — read-time entity-journal projections (logbooks) over the recorded streams.

Covers AC1 (entity journals are read-time projections selected by entity identity, never
writers), AC2 (the risk-authored / venue-authored identity split and the pinned
command-fingerprint join, with Book identity kept out of the neutral venue payload), AC3
(role-scoped namespaces, the FM-11 cross-role guard, and the two declared exceptions), and
AC4 (the legacy five Records streams as projection names over the one versioned mapping
table, veto_ledger on the declared outcome).
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    LIVE_EVIDENCE_NAMESPACE,
    AccountRole,
    Fingerprint,
    Result,
    World,
    WriterId,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.core.refusal import RefusalCategory
from qmf.data import (
    BOOK_IDENTITY_FIELDS,
    CT25_CONTRACT_FORMAT_VERSION,
    RECORDS_STREAM_MAPPING,
    BindingIdentity,
    BotSeat,
    CommandAttribution,
    CommandIndex,
    CrossRoleRead,
    DecisionOutcome,
    EntityKind,
    EntitySelector,
    EventClass,
    JournalEvent,
    JournalEventType,
    Logbook,
    ProjectedRow,
    RecordsStreamName,
    RecordsStreamRule,
    bms_journal,
    book_journal,
    bot_logbook,
    decay_cohort_read,
    entity_journal,
    event_class_of,
    guard_neutral_venue_payload,
    read_binding,
    read_bot_seat,
    read_command_fingerprint,
    read_role,
    records_stream,
    role_namespace,
)

T = TypeVar("T")

_VENUE = "venue-1"
_BOOK = "book-7"
_BMS = "bms-3"
_ACCOUNT = "acct-42"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _fp(content: object) -> Fingerprint:
    return _ok(fingerprint(content))


_BOOK_DEF = _fp({"book": "def"})
_BOT_DEF = _fp({"bot": "def"})
_CMD_A = _fp({"cmd": "a"})
_CMD_B = _fp({"cmd": "b"})


def _writer(stream: str = "s") -> WriterId:
    return _ok(WriterId.try_create("m", "r", stream, "boot-1"))


def _binding_fields(role: AccountRole = AccountRole.LIVE, **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "book_instance_id": _BOOK,
        "bms_instance_id": _BMS,
        "venue_id": _VENUE,
        "account_id": _ACCOUNT,
        "book_definition_fp": _BOOK_DEF.value,
        "role": role.value,
    }
    payload.update(extra)
    return payload


def _event(
    event_type: str,
    payload: dict[str, object],
    *,
    outcome: DecisionOutcome | None = None,
    world: World = World.LIVE,
    sequence: int = 0,
    instant: int = 1_000,
) -> JournalEvent:
    return _ok(
        JournalEvent.try_create(
            event_type=event_type,
            writer=_writer(),
            sequence=sequence,
            instant=instant,
            world=world,
            payload=payload,
            outcome=outcome,
        )
    )


# --- AC2: event class -------------------------------------------------------


def test_event_class_covers_all_seven_types() -> None:
    risk = {
        JournalEventType.DECISION,
        JournalEventType.RISK_TRANSITION,
        JournalEventType.CONTROL_ACTION,
        JournalEventType.PROMOTION,
    }
    venue = {JournalEventType.ORDER, JournalEventType.FILL, JournalEventType.DATA_QUALITY}
    for event_type in JournalEventType:
        expected = EventClass.RISK_AUTHORED if event_type in risk else EventClass.VENUE_AUTHORED
        assert event_class_of(event_type) is expected
    assert risk | venue == set(JournalEventType)


# --- AC3: role-scoped namespaces --------------------------------------------


def test_role_namespace_live_is_the_live_evidence_namespace() -> None:
    assert _ok(role_namespace(AccountRole.LIVE)) == LIVE_EVIDENCE_NAMESPACE


def test_role_namespace_gives_each_other_role_its_own_namespace() -> None:
    demo = _ok(role_namespace(AccountRole.DEMO))
    benched = _ok(role_namespace("paper-benched"))
    validation = _ok(role_namespace(AccountRole.PAPER_VALIDATION))
    assert demo == "demo"
    assert benched == "paper-benched"
    assert len({demo, benched, validation, LIVE_EVIDENCE_NAMESPACE}) == 4


def test_role_namespace_refuses_a_non_role() -> None:
    refused = role_namespace("not-a-role")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


# --- AC2: binding identity + bot seat ---------------------------------------


def test_binding_identity_round_trips_and_fingerprints() -> None:
    binding = _ok(
        BindingIdentity.try_create(
            book_instance_id=_BOOK,
            bms_instance_id=_BMS,
            venue_id=_VENUE,
            account_id=_ACCOUNT,
            world=World.LIVE,
        )
    )
    assert binding.venue_id.value == _VENUE
    assert binding.world is World.LIVE
    identity = binding.fp1_identity()
    assert identity["book_instance_id"] == _BOOK
    assert identity["format_version"] == CT25_CONTRACT_FORMAT_VERSION
    # It is a canonical value: qmf-core can fingerprint it.
    assert is_ok(fingerprint(binding))


def test_binding_identity_refuses_each_missing_part() -> None:
    base: dict[str, object] = {
        "book_instance_id": _BOOK,
        "bms_instance_id": _BMS,
        "venue_id": _VENUE,
        "account_id": _ACCOUNT,
        "world": World.LIVE,
    }
    for field_name in ("book_instance_id", "bms_instance_id", "venue_id", "account_id", "world"):
        broken = dict(base)
        broken[field_name] = "" if field_name != "world" else "no-such-world"
        refused = BindingIdentity.try_create(**broken)  # type: ignore[arg-type]
        assert is_refusal(refused), field_name
        assert refused.context["field"] == field_name


def test_read_bot_seat_none_both_and_partial() -> None:
    assert (
        _ok(
            read_bot_seat(_event("decision", _binding_fields(), outcome=DecisionOutcome.AUTHORIZED))
        )
        is None
    )

    both = _event(
        "decision",
        _binding_fields(bot_definition_fp=_BOT_DEF.value, seat_binding="seat-1"),
        outcome=DecisionOutcome.AUTHORIZED,
    )
    seat = _ok(read_bot_seat(both))
    assert seat == BotSeat(bot_definition_fp=_BOT_DEF, seat_binding="seat-1")

    partial_fp = _event(
        "decision",
        _binding_fields(bot_definition_fp=_BOT_DEF.value),
        outcome=DecisionOutcome.AUTHORIZED,
    )
    assert is_refusal(read_bot_seat(partial_fp))

    partial_seat = _event(
        "decision", _binding_fields(seat_binding="seat-1"), outcome=DecisionOutcome.AUTHORIZED
    )
    assert is_refusal(read_bot_seat(partial_seat))

    bad_fp = _event(
        "decision",
        _binding_fields(bot_definition_fp="not-a-fp", seat_binding="seat-1"),
        outcome=DecisionOutcome.AUTHORIZED,
    )
    assert is_refusal(read_bot_seat(bad_fp))


def test_read_role_and_binding() -> None:
    event = _event(
        "decision", _binding_fields(AccountRole.DEMO), outcome=DecisionOutcome.AUTHORIZED
    )
    assert _ok(read_role(event)) is AccountRole.DEMO
    binding = _ok(read_binding(event))
    assert binding.book_instance_id == _BOOK

    no_role = _event(
        "promotion",
        {
            "book_instance_id": _BOOK,
            "bms_instance_id": _BMS,
            "venue_id": _VENUE,
            "account_id": _ACCOUNT,
        },
    )
    assert is_refusal(read_role(no_role))

    bad_role = _event("promotion", _binding_fields() | {"role": "nope"})
    assert is_refusal(read_role(bad_role))

    partial_binding = _event("promotion", {"book_instance_id": _BOOK, "role": "live"})
    assert is_refusal(read_binding(partial_binding))


# --- AC2: neutral venue payload + command fingerprint -----------------------


def test_guard_neutral_venue_payload_rejects_each_book_identity_field() -> None:
    for leaked in sorted(BOOK_IDENTITY_FIELDS):
        event = _event("order", {"command_fingerprint": _CMD_A.value, "role": "live", leaked: "x"})
        refused = guard_neutral_venue_payload(event)
        assert is_refusal(refused), leaked
        assert leaked in refused.context["leaked_fields"]  # type: ignore[operator]

    clean = _event("order", {"command_fingerprint": _CMD_A.value, "role": "live"})
    assert is_ok(guard_neutral_venue_payload(clean))


def test_read_command_fingerprint_valid_missing_and_leaked() -> None:
    ok = _event("fill", {"command_fingerprint": _CMD_A.value, "role": "live"})
    assert _ok(read_command_fingerprint(ok)) == _CMD_A

    missing = _event("fill", {"role": "live"})
    assert is_refusal(read_command_fingerprint(missing))

    leaked = _event(
        "fill", {"command_fingerprint": _CMD_A.value, "role": "live", "book_instance_id": _BOOK}
    )
    assert is_refusal(read_command_fingerprint(leaked))


# --- AC1: entity selectors --------------------------------------------------


def test_entity_selector_factories_and_refusals() -> None:
    assert _ok(EntitySelector.for_book(_BOOK)).kind is EntityKind.BOOK
    assert _ok(EntitySelector.for_bms(_BMS)).kind is EntityKind.BMS
    bot = _ok(EntitySelector.for_bot(_BOT_DEF, "seat-1"))
    assert bot.kind is EntityKind.BOT
    assert bot.bot_seat == BotSeat(bot_definition_fp=_BOT_DEF, seat_binding="seat-1")
    binding = _ok(
        BindingIdentity.try_create(
            book_instance_id=_BOOK,
            bms_instance_id=_BMS,
            venue_id=_VENUE,
            account_id=_ACCOUNT,
            world=World.LIVE,
        )
    )
    assert _ok(EntitySelector.for_binding(binding)).kind is EntityKind.BINDING

    assert is_refusal(EntitySelector.for_book(""))
    assert is_refusal(EntitySelector.for_bms(" "))
    assert is_refusal(EntitySelector.for_bot("bad-fp", "seat"))
    assert is_refusal(EntitySelector.for_bot(_BOT_DEF, ""))
    assert is_refusal(EntitySelector.for_binding("not-a-binding"))


# --- AC2: command index + join ----------------------------------------------


def test_command_index_build_lookup_conflict_and_bad_fp() -> None:
    decision = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_A.value),
        outcome=DecisionOutcome.AUTHORIZED,
    )
    index = _ok(CommandIndex.build([decision]))
    attribution = index.attribution_for(_CMD_A)
    assert attribution is not None
    assert attribution.binding.book_instance_id == _BOOK
    assert index.attribution_for(_CMD_B) is None

    # A byte-identical duplicate command record is idempotent.
    assert is_ok(CommandIndex.build([decision, decision]))

    # A conflicting attribution for one command fingerprint is refused.
    other = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_A.value) | {"book_instance_id": "other-book"},
        outcome=DecisionOutcome.AUTHORIZED,
    )
    assert is_refusal(CommandIndex.build([decision, other]))

    # A malformed command fingerprint on a command record is refused.
    bad = _event(
        "decision", _binding_fields(command_fingerprint="nope"), outcome=DecisionOutcome.AUTHORIZED
    )
    assert is_refusal(CommandIndex.build([bad]))

    # A command record carrying a command fp but no binding is refused.
    no_binding = _event("promotion", {"command_fingerprint": _CMD_A.value, "role": "live"})
    assert is_refusal(CommandIndex.build([no_binding]))

    # An empty index (default) resolves nothing.
    assert CommandIndex().attribution_for(_CMD_A) is None


# --- AC1/AC2: entity_journal projections ------------------------------------


def test_entity_journal_requires_a_selector() -> None:
    refused = entity_journal([], selector="book-7")  # type: ignore[arg-type]
    assert is_refusal(refused)
    assert refused.context["field"] == "selector"


def test_book_journal_risk_authored_only_without_join() -> None:
    decision = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_A.value),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    control = _event(
        "control action", _binding_fields() | {"control_action_subtype": "kill"}, sequence=1
    )
    order = _event("order", {"command_fingerprint": _CMD_A.value, "role": "live"}, sequence=2)
    logbook = _ok(book_journal([decision, control, order], _BOOK, role=AccountRole.LIVE))
    # No command_index -> venue order is not joined; only the two risk-authored events.
    assert [row.event.event_type for row in logbook.rows] == [
        JournalEventType.DECISION,
        JournalEventType.CONTROL_ACTION,
    ]
    assert all(row.event_class is EventClass.RISK_AUTHORED for row in logbook.rows)


def test_book_journal_joins_orders_and_fills_through_command_fingerprint() -> None:
    decision = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_A.value),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    order = _event("order", {"command_fingerprint": _CMD_A.value, "role": "live"}, sequence=1)
    fill = _event("fill", {"command_fingerprint": _CMD_A.value, "role": "live"}, sequence=2)
    unrelated = _event("order", {"command_fingerprint": _CMD_B.value, "role": "live"}, sequence=3)
    events = [decision, order, fill, unrelated]
    index = _ok(CommandIndex.build(events))
    logbook = _ok(book_journal(events, _BOOK, role=AccountRole.LIVE, command_index=index))
    classes = [row.event_class for row in logbook.rows]
    assert classes == [
        EventClass.RISK_AUTHORED,
        EventClass.VENUE_AUTHORED,
        EventClass.VENUE_AUTHORED,
    ]
    # The joined venue rows carry the binding they inherited, never from their own payload.
    assert all(
        row.binding is not None and row.binding.book_instance_id == _BOOK for row in logbook.rows
    )


def test_bms_and_binding_projections() -> None:
    event = _event("risk transition", _binding_fields(), sequence=0)
    other = _event(
        "risk transition", _binding_fields() | {"bms_instance_id": "other-bms"}, sequence=1
    )
    bms = _ok(bms_journal([event, other], _BMS, role=AccountRole.LIVE))
    assert [row.event for row in bms.rows] == [event]

    binding = _ok(read_binding(event))
    selector = _ok(EntitySelector.for_binding(binding))
    combined = _ok(entity_journal([event, other], selector=selector, role=AccountRole.LIVE))
    assert [row.event for row in combined.rows] == [event]


def test_bot_logbook_matches_risk_and_joined_venue() -> None:
    decision = _event(
        "decision",
        _binding_fields(
            bot_definition_fp=_BOT_DEF.value,
            seat_binding="seat-1",
            command_fingerprint=_CMD_A.value,
        ),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    order = _event("order", {"command_fingerprint": _CMD_A.value, "role": "live"}, sequence=1)
    other_bot = _event(
        "decision",
        _binding_fields(bot_definition_fp=_fp({"bot": "other"}).value, seat_binding="seat-2"),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=2,
    )
    events = [decision, order, other_bot]
    index = _ok(CommandIndex.build(events))
    logbook = _ok(
        bot_logbook(events, _BOT_DEF, "seat-1", role=AccountRole.LIVE, command_index=index)
    )
    assert [row.event for row in logbook.rows] == [decision, order]
    assert logbook.rows[1].bot_seat == BotSeat(bot_definition_fp=_BOT_DEF, seat_binding="seat-1")


def test_risk_authored_event_without_binding_is_skipped() -> None:
    # A qmf-data control action with no binding does not match any entity selector.
    control = _event("control action", {"control_action_subtype": "seal-look", "role": "live"})
    decision = _event("decision", _binding_fields(), outcome=DecisionOutcome.AUTHORIZED, sequence=1)
    logbook = _ok(book_journal([control, decision], _BOOK, role=AccountRole.LIVE))
    assert [row.event for row in logbook.rows] == [decision]


def test_partial_binding_and_partial_bot_are_refused_during_selection() -> None:
    partial = _event(
        "decision", {"book_instance_id": _BOOK, "role": "live"}, outcome=DecisionOutcome.AUTHORIZED
    )
    assert is_refusal(book_journal([partial], _BOOK, role=AccountRole.LIVE))

    bad_bot = _event(
        "decision",
        _binding_fields(bot_definition_fp="bad", seat_binding="seat-1"),
        outcome=DecisionOutcome.AUTHORIZED,
    )
    assert is_refusal(book_journal([bad_bot], _BOOK, role=AccountRole.LIVE))


def test_matched_row_missing_role_is_refused() -> None:
    no_role = _event(
        "decision",
        {
            "book_instance_id": _BOOK,
            "bms_instance_id": _BMS,
            "venue_id": _VENUE,
            "account_id": _ACCOUNT,
        },
        outcome=DecisionOutcome.AUTHORIZED,
    )
    refused = book_journal([no_role], _BOOK, role=AccountRole.LIVE)
    assert is_refusal(refused)


def test_venue_leak_in_join_path_refuses() -> None:
    decision = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_A.value),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    leaked_order = _event(
        "order",
        {"command_fingerprint": _CMD_A.value, "role": "live", "book_instance_id": _BOOK},
        sequence=1,
    )
    events = [decision, leaked_order]
    index = _ok(CommandIndex.build(events))
    assert is_refusal(book_journal(events, _BOOK, role=AccountRole.LIVE, command_index=index))


def test_venue_leak_on_another_book_does_not_poison_this_projection() -> None:
    # L8: a leaked-key venue event that joins to a DIFFERENT book must not refuse THIS book's
    # clean projection. The neutral-payload guard is scoped to events matched into the
    # requested read; an unrelated leaky producer on another book is not grounds to refuse.
    decision = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_A.value),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    other_decision = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_B.value) | {"book_instance_id": "other-book"},
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=1,
    )
    leaked_other_order = _event(
        "order",
        {"command_fingerprint": _CMD_B.value, "role": "live", "book_instance_id": "other-book"},
        sequence=2,
    )
    events = [decision, other_decision, leaked_other_order]
    index = _ok(CommandIndex.build(events))
    logbook = _ok(book_journal(events, _BOOK, role=AccountRole.LIVE, command_index=index))
    # The unrelated leaked order attributes to other-book, is not matched here, and is simply
    # not joined — never a refusal that would poison this Book's read.
    assert [row.event for row in logbook.rows] == [decision]


def test_venue_event_with_untracked_command_is_skipped() -> None:
    decision = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_A.value),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    order_untracked = _event(
        "order", {"command_fingerprint": _CMD_B.value, "role": "live"}, sequence=1
    )
    order_no_cmd = _event("data quality", {"role": "live", "metric": "spread"}, sequence=2)
    events = [decision, order_untracked, order_no_cmd]
    index = _ok(CommandIndex.build(events))
    logbook = _ok(book_journal(events, _BOOK, role=AccountRole.LIVE, command_index=index))
    assert [row.event for row in logbook.rows] == [decision]


# --- AC3: role scoping ------------------------------------------------------


def _multi_role_events() -> list[JournalEvent]:
    live = _event(
        "decision",
        _binding_fields(AccountRole.LIVE),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    benched = _event(
        "decision",
        _binding_fields(AccountRole.PAPER_BENCHED),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=1,
    )
    return [live, benched]


def test_single_role_scope_filters_to_one_namespace() -> None:
    logbook = _ok(book_journal(_multi_role_events(), _BOOK, role=AccountRole.LIVE))
    assert logbook.roles == frozenset({AccountRole.LIVE})
    assert len(logbook.rows) == 1


def test_multi_role_without_declaration_is_fm11_policy_rejection() -> None:
    refused = book_journal(_multi_role_events(), _BOOK)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert set(refused.context["roles"]) == {"live", "paper-benched"}  # type: ignore[arg-type]


def test_declared_multi_role_entity_read_spans_roles() -> None:
    logbook = _ok(
        book_journal(_multi_role_events(), _BOOK, cross_role=CrossRoleRead.MULTI_ROLE_ENTITY)
    )
    assert logbook.roles == frozenset({AccountRole.LIVE, AccountRole.PAPER_BENCHED})
    assert logbook.cross_role is CrossRoleRead.MULTI_ROLE_ENTITY


def test_single_role_matches_all_when_uniform() -> None:
    live = _event("decision", _binding_fields(AccountRole.LIVE), outcome=DecisionOutcome.AUTHORIZED)
    logbook = _ok(book_journal([live], _BOOK))
    assert logbook.roles == frozenset({AccountRole.LIVE})


def test_role_and_cross_role_together_is_invalid() -> None:
    refused = book_journal(
        _multi_role_events(),
        _BOOK,
        role=AccountRole.LIVE,
        cross_role=CrossRoleRead.MULTI_ROLE_ENTITY,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_invalid_role_and_invalid_cross_role() -> None:
    assert is_refusal(book_journal(_multi_role_events(), _BOOK, role="nope"))
    assert is_refusal(book_journal(_multi_role_events(), _BOOK, cross_role="not-declared"))


def test_decay_cohort_read_spans_roles_and_carries_role() -> None:
    events = _multi_role_events()
    no_role = _event("data quality", {"metric": "spread"}, sequence=2)
    # A cohort row that carries a role but declares no binding (a venue-authored data-quality
    # row) still projects, with binding None.
    role_no_binding = _event("data quality", {"metric": "spread", "role": "live"}, sequence=3)
    logbook = _ok(decay_cohort_read([*events, no_role, role_no_binding]))
    assert logbook.cross_role is CrossRoleRead.DECAY_COHORT
    assert logbook.selector is None
    assert logbook.roles == frozenset({AccountRole.LIVE, AccountRole.PAPER_BENCHED})
    # The event carrying no role is not a cohort row; the role-without-binding one is.
    assert len(logbook.rows) == 3
    assert any(row.binding is None for row in logbook.rows)
    assert all(isinstance(row.role, AccountRole) for row in logbook.rows)


def test_decay_cohort_absent_role_skipped_malformed_role_refused() -> None:
    # M7: an event with NO role key is not a cohort row and is skipped (pinned behavior),
    # but an event that DECLARES a role which is malformed (present but outside the closed
    # AccountRole set) is refused — matching every other projection — not silently dropped.
    absent = _event("data quality", {"metric": "spread"}, sequence=0)
    ok = _ok(decay_cohort_read([absent]))
    assert ok.rows == ()  # the absent-role event contributes no cohort row

    malformed = _event("data quality", {"metric": "spread", "role": "LIVE"}, sequence=0)
    refused = decay_cohort_read([malformed])
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context.get("field") == "role"


def test_decay_cohort_malformed_role_refused_like_book_journal() -> None:
    # The same malformed-role row book_journal refuses is refused by decay_cohort_read too,
    # rather than silently kept in the cohort read (the M7 parity the finding names).
    malformed = _event(
        "decision",
        _binding_fields() | {"role": "LIVE"},
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    assert is_refusal(book_journal([malformed], _BOOK))
    assert is_refusal(decay_cohort_read([malformed]))


def test_convenience_wrappers_propagate_selector_refusals() -> None:
    assert is_refusal(book_journal([], ""))
    assert is_refusal(bms_journal([], ""))
    assert is_refusal(bot_logbook([], "bad-fp", "seat"))


# --- AC4: legacy Records streams --------------------------------------------


def test_records_stream_veto_ledger_selects_on_declared_outcome() -> None:
    authorized = _event(
        "decision", _binding_fields(), outcome=DecisionOutcome.AUTHORIZED, sequence=0
    )
    refused = _event(
        "decision",
        _binding_fields(refusing_door="spread-door"),
        outcome=DecisionOutcome.REFUSED_BY_DOOR,
        sequence=1,
    )
    veto = _ok(records_stream([authorized, refused], "veto_ledger"))
    assert veto == [refused]
    assert _ok(records_stream([authorized, refused], RecordsStreamName.VETO_LEDGER)) == [refused]


def test_records_stream_maps_each_legacy_name_onto_event_types() -> None:
    order = _event("order", {"command_fingerprint": _CMD_A.value, "role": "live"}, sequence=0)
    fill = _event("fill", {"command_fingerprint": _CMD_A.value, "role": "live"}, sequence=1)
    decision = _event("decision", _binding_fields(), outcome=DecisionOutcome.AUTHORIZED, sequence=2)
    transition = _event("risk transition", _binding_fields(), sequence=3)
    promotion = _event("promotion", _binding_fields(), sequence=4)
    control = _event(
        "control action", _binding_fields() | {"control_action_subtype": "kill"}, sequence=5
    )
    events = [order, fill, decision, transition, promotion, control]

    # records_stream preserves input order, so compare ordered lists (events are unhashable).
    assert _ok(records_stream(events, "trade_journal")) == [order, fill]
    assert _ok(records_stream(events, "book_journal")) == [decision, transition, promotion]
    assert _ok(records_stream(events, "ksa_audit_log")) == [control]
    assert _ok(records_stream(events, "correlation_ledger")) == [transition]


def test_records_stream_unknown_name_is_refused() -> None:
    refused = records_stream([], "not_a_records_stream")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_records_stream_mapping_is_the_one_versioned_table() -> None:
    assert set(RECORDS_STREAM_MAPPING) == set(RecordsStreamName)
    veto_rule = RECORDS_STREAM_MAPPING[RecordsStreamName.VETO_LEDGER]
    assert isinstance(veto_rule, RecordsStreamRule)
    assert veto_rule.outcome is DecisionOutcome.REFUSED_BY_DOOR
    assert veto_rule.event_types == frozenset({JournalEventType.DECISION})
    # Every mapped type is one of the seven; no second catalog exists.
    mapped: set[JournalEventType] = set()
    for rule in RECORDS_STREAM_MAPPING.values():
        mapped |= rule.event_types
    assert mapped <= set(JournalEventType)


# --- value-type surface -----------------------------------------------------


def test_logbook_and_projected_row_properties() -> None:
    event = _event("decision", _binding_fields(), outcome=DecisionOutcome.AUTHORIZED)
    binding = _ok(read_binding(event))
    row = ProjectedRow(
        event=event, event_class=EventClass.RISK_AUTHORED, role=AccountRole.LIVE, binding=binding
    )
    logbook = Logbook(rows=(row,))
    assert logbook.events == (event,)
    assert logbook.roles == frozenset({AccountRole.LIVE})
    assert logbook.selector is None
    assert logbook.cross_role is None


def test_venue_join_binding_mismatch_is_skipped() -> None:
    # The command is indexed to book-7, but we project a different book: the joined venue
    # event's inherited binding does not match the selector, so it is skipped.
    decision = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_A.value),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    order = _event("order", {"command_fingerprint": _CMD_A.value, "role": "live"}, sequence=1)
    events = [decision, order]
    index = _ok(CommandIndex.build(events))
    logbook = _ok(book_journal(events, "other-book", role=AccountRole.LIVE, command_index=index))
    assert logbook.rows == ()


def test_joined_venue_row_missing_role_is_refused() -> None:
    decision = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_A.value),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    order_no_role = _event("order", {"command_fingerprint": _CMD_A.value}, sequence=1)
    events = [decision, order_no_role]
    index = _ok(CommandIndex.build(events))
    assert is_refusal(book_journal(events, _BOOK, role=AccountRole.LIVE, command_index=index))


def test_decay_cohort_read_treats_partial_binding_as_absent() -> None:
    partial = _event("risk transition", {"book_instance_id": _BOOK, "role": "live"})
    logbook = _ok(decay_cohort_read([partial]))
    assert len(logbook.rows) == 1
    assert logbook.rows[0].binding is None


def test_coercer_fallthroughs_refuse_wrong_typed_inputs() -> None:
    from qmf.core import VenueId

    assert is_refusal(
        BindingIdentity.try_create(
            book_instance_id=_BOOK,
            bms_instance_id=_BMS,
            venue_id=123,
            account_id=_ACCOUNT,
            world=World.LIVE,
        )
    )
    assert is_refusal(
        BindingIdentity.try_create(
            book_instance_id=_BOOK,
            bms_instance_id=_BMS,
            venue_id=VenueId(""),
            account_id=_ACCOUNT,
            world=World.LIVE,
        )
    )
    assert is_refusal(
        BindingIdentity.try_create(
            book_instance_id=_BOOK,
            bms_instance_id=_BMS,
            venue_id=_VENUE,
            account_id=_ACCOUNT,
            world=123,
        )
    )
    assert is_refusal(book_journal([], _BOOK, cross_role=123))
    assert is_refusal(records_stream([], 123))


def test_command_attribution_value() -> None:
    binding = _ok(
        BindingIdentity.try_create(
            book_instance_id=_BOOK,
            bms_instance_id=_BMS,
            venue_id=_VENUE,
            account_id=_ACCOUNT,
            world=World.LIVE,
        )
    )
    attribution = CommandAttribution(binding=binding)
    assert attribution.bot_seat is None
    assert attribution.binding.book_instance_id == _BOOK
