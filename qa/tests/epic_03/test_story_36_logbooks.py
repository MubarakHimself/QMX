"""Epic 3 — Story 3.6: read-time entity-journal projections / logbooks (FR-013 / CT-13, CT-25).

Independent tests from Story 3.6 AC1-AC4 and PLAN Section 4 (3.6-U1..U4, P1, C1). CT-25 is a
ratified-but-defined-unwired surface: contract-shape conformance and the venue-side join /
mapping table are testable; a runtime proof over real risk-authored streams is BLOCKED
(PLAN Section 8, U-B) — no such assertion is made here.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from qmf.core import AccountRole, World, is_ok, is_refusal
from qmf.data.journal import DecisionOutcome, JournalEvent, JournalEventType
from qmf.data.logbooks import (
    RECORDS_STREAM_MAPPING,
    BindingIdentity,
    CommandIndex,
    CrossRoleRead,
    EventClass,
    RecordsStreamName,
    book_journal,
    decay_cohort_read,
    entity_journal,
    event_class_of,
    guard_neutral_venue_payload,
    read_command_fingerprint,
    records_stream,
    role_namespace,
)

import _epic3_helpers as H

_BOOK = "book-1"
_BMS = "bms-1"


def _risk_event(
    event_type: JournalEventType = JournalEventType.RISK_TRANSITION,
    *,
    book: str = _BOOK,
    role: str = "live",
    world: World = World.LIVE,
    sequence: int = 0,
    command_fp: str | None = None,
    outcome: DecisionOutcome | None = None,
    extra: dict | None = None,
) -> JournalEvent:
    payload: dict[str, object] = {
        "book_instance_id": book,
        "bms_instance_id": _BMS,
        "venue_id": "cTrader",
        "account_id": "acct-1",
        "role": role,
    }
    if command_fp is not None:
        payload["command_fingerprint"] = command_fp
    if extra:
        payload.update(extra)
    return H.unwrap(
        JournalEvent.try_create(
            event_type=event_type,
            writer=H.writer(role="risk", stream="book-stream"),
            sequence=sequence,
            instant=1_000 + sequence,
            world=world,
            payload=payload,
            outcome=outcome,
        )
    )


def _venue_event(
    event_type: JournalEventType = JournalEventType.ORDER,
    *,
    role: str = "live",
    command_fp: str,
    sequence: int = 0,
    leak: dict | None = None,
) -> JournalEvent:
    payload: dict[str, object] = {"role": role, "command_fingerprint": command_fp}
    if leak:
        payload.update(leak)
    return H.unwrap(
        JournalEvent.try_create(
            event_type=event_type,
            writer=H.writer(role="venue", stream="venue-stream"),
            sequence=sequence,
            instant=2_000 + sequence,
            world=World.LIVE,
            payload=payload,
        )
    )


# --- 3.6-U1 (L1): an entity journal is a read-time projection, mints no stream --


def test_3_6_u1_entity_journal_is_projection() -> None:
    """AC1: a Book journal is extracted on demand from the recorded streams; no entity mints a stream."""
    events = [
        _risk_event(JournalEventType.RISK_TRANSITION, sequence=0),
        _risk_event(JournalEventType.PROMOTION, sequence=1),
        _risk_event(JournalEventType.RISK_TRANSITION, book="book-2", sequence=2),
    ]
    logbook = H.unwrap(book_journal(events, _BOOK))
    # the projection selects only the requested Book's rows from the ONE recorded set
    assert len(logbook.rows) == 2
    assert all(r.binding is not None and r.binding.book_instance_id == _BOOK for r in logbook.rows)
    # a projection is a view, never a writer/stream
    assert logbook.selector is not None
    assert all(r.event_class is EventClass.RISK_AUTHORED for r in logbook.rows)


# --- 3.6-U2 (L1): a Book projection joins venue events by command fingerprint ---


def test_3_6_u2_command_fingerprint_join() -> None:
    """AC2: venue orders/fills join the Book via the command fingerprint; Book identity never enters the venue payload."""
    cmd_fp = H.fp("c").value
    decision = _risk_event(
        JournalEventType.DECISION, sequence=0, command_fp=cmd_fp, outcome=DecisionOutcome.AUTHORIZED
    )
    order = _venue_event(JournalEventType.ORDER, command_fp=cmd_fp, sequence=0)
    fill = _venue_event(JournalEventType.FILL, command_fp=cmd_fp, sequence=1)
    events = [decision, order, fill]
    index = H.unwrap(CommandIndex.build(events))
    logbook = H.unwrap(book_journal(events, _BOOK, command_index=index))
    classes = sorted({r.event_class.value for r in logbook.rows})
    assert classes == ["risk-authored", "venue-authored"]  # decision + joined order/fill
    # the venue events carry ONLY the command fingerprint, never Book identity
    for ve in (order, fill):
        assert is_ok(guard_neutral_venue_payload(ve))
        assert read_command_fingerprint(ve).value.value == cmd_fp
    # a venue payload that leaks Book identity is refused
    leaky = _venue_event(JournalEventType.ORDER, command_fp=cmd_fp, leak={"book_instance_id": _BOOK})
    H.assert_refusal(guard_neutral_venue_payload(leaky), "invalid input")


# --- 3.6-U3 (L1): cross-role aggregation without a declared read is refused -----


def test_3_6_u3_cross_role_refused_without_declaration() -> None:
    """AC3/FM-11: aggregating across account roles without a declared cross-role read is a policy rejection."""
    events = [
        _risk_event(sequence=0, role="live"),
        _risk_event(sequence=1, role="paper-validation"),
    ]
    # no declared scope + rows spanning two roles -> policy rejection
    H.assert_refusal(book_journal(events, _BOOK), "policy rejection")
    # one of the two declared exceptions (a multi-role entity projection) admits both, carrying role
    spanned = H.unwrap(book_journal(events, _BOOK, cross_role=CrossRoleRead.MULTI_ROLE_ENTITY))
    assert spanned.cross_role is CrossRoleRead.MULTI_ROLE_ENTITY
    assert {r.role for r in spanned.rows} == {AccountRole.LIVE, AccountRole.PAPER_VALIDATION}
    assert all(r.role is not None for r in spanned.rows)  # role on every row
    # a single role-scoped read returns only that namespace's rows
    live_only = H.unwrap(book_journal(events, _BOOK, role="live"))
    assert {r.role for r in live_only.rows} == {AccountRole.LIVE}


def test_3_6_u3_role_namespaces_separate_paper_and_live() -> None:
    """AC3/DEC-0158: live resolves to the live namespace; every other role gets its own — paper never shares live's."""
    live_ns = H.unwrap(role_namespace(AccountRole.LIVE))
    for role in (AccountRole.DEMO, AccountRole.PAPER_VALIDATION, AccountRole.PAPER_BENCHED, AccountRole.PROP_FIRM):
        ns = H.unwrap(role_namespace(role))
        assert ns != live_ns, f"{role.value} must not share the live evidence namespace"
    H.assert_refusal(role_namespace("not-a-role"), "invalid input")


# --- 3.6-U4 (L1): legacy Records names map via the one CT-25 table -------------


def test_3_6_u4_legacy_records_streams_map_via_one_table() -> None:
    """AC4/DEC-0145: the legacy five names resolve via the one versioned table; veto_ledger selects on outcome."""
    refused = _risk_event(
        JournalEventType.DECISION, sequence=0, outcome=DecisionOutcome.REFUSED_BY_DOOR,
        extra={"refusing_door": "door-1"},
    )
    authorized = _risk_event(
        JournalEventType.DECISION, sequence=1, outcome=DecisionOutcome.AUTHORIZED
    )
    control = _risk_event(JournalEventType.CONTROL_ACTION, sequence=2, extra={"control_action_subtype": "kill"})
    events = [refused, authorized, control]
    # veto_ledger selects on decision.outcome = refused-by-door, never key presence
    veto = H.unwrap(records_stream(events, RecordsStreamName.VETO_LEDGER))
    assert veto == [refused]
    # ksa_audit_log maps onto control-action events
    ksa = H.unwrap(records_stream(events, RecordsStreamName.KSA_AUDIT_LOG))
    assert ksa == [control]
    # exactly the legacy five names are in the ONE mapping table (no second catalog)
    assert set(RECORDS_STREAM_MAPPING) == set(RecordsStreamName)
    assert len(RECORDS_STREAM_MAPPING) == 5
    # an unknown projection name is refused
    H.assert_refusal(records_stream(events, "unknown_ledger"), "invalid input")


# --- 3.6-P1 (L2 property, FM-11): the seven event classes never write cross-role


@settings(max_examples=40, deadline=None)
@given(event_type=st.sampled_from(list(JournalEventType)))
def test_3_6_p1_event_class_total_and_stable(event_type: JournalEventType) -> None:
    """AC2/AC3: every event type maps to exactly one CT-25 class; the projection surface never writes.

    FM-11's "no write ever crosses roles" is upheld by construction: the logbooks module is
    read-only. This asserts the event-class map is total (every one of the seven types resolves)
    and that risk-/venue-authored is a clean partition — the property the role-scope guard rests on.
    """
    cls = event_class_of(event_type)
    assert cls in (EventClass.RISK_AUTHORED, EventClass.VENUE_AUTHORED)
    # venue-authored is exactly {order, fill, data quality}; the rest are risk-authored
    if event_type in (JournalEventType.ORDER, JournalEventType.FILL, JournalEventType.DATA_QUALITY):
        assert cls is EventClass.VENUE_AUTHORED
    else:
        assert cls is EventClass.RISK_AUTHORED


def test_3_6_p1_decay_cohort_is_the_only_other_cross_role_read() -> None:
    """AC3: the decay-cohort read is the second declared cross-role read, carrying role on every row."""
    events = [_risk_event(sequence=0, role="live"), _risk_event(sequence=1, role="paper-benched")]
    cohort = H.unwrap(decay_cohort_read(events))
    assert cohort.cross_role is CrossRoleRead.DECAY_COHORT
    assert {r.role for r in cohort.rows} == {AccountRole.LIVE, AccountRole.PAPER_BENCHED}
    assert all(r.role is not None for r in cohort.rows)
    # exactly two declared cross-role reads exist
    assert {m.value for m in CrossRoleRead} == {"decay-cohort", "multi-role-entity"}


# --- 3.6-C1 (L3 contract, defined-unwired): join + mapping table round-trip -----


def test_3_6_c1_ct25_shape_conformance_only() -> None:
    """CT-25 (defined-unwired): the command-fingerprint join and legacy mapping table round-trip at contract level.

    No runtime assertion over real risk-authored streams is made — that is BLOCKED (PLAN U-B)
    until the node wires qmf-risk. This checks only the contract shape qmf-data owns today.
    """
    cmd_fp = H.fp("e").value
    decision = _risk_event(JournalEventType.DECISION, command_fp=cmd_fp, outcome=DecisionOutcome.AUTHORIZED)
    index = H.unwrap(CommandIndex.build([decision]))
    attribution = index.attribution_for(H.unwrap(_fp_value(cmd_fp)))
    assert attribution is not None
    assert attribution.binding.book_instance_id == _BOOK
    # one command fingerprint attributing to two DIFFERENT bindings is an integrity refusal
    conflict = _risk_event(
        JournalEventType.DECISION, book="book-OTHER", command_fp=cmd_fp, outcome=DecisionOutcome.AUTHORIZED
    )
    H.assert_refusal(CommandIndex.build([decision, conflict]), "invalid input")
    # every legacy Records rule maps onto a subset of the seven event types (no second catalog)
    for name, rule in RECORDS_STREAM_MAPPING.items():
        assert rule.event_types <= set(JournalEventType)
        assert isinstance(name, RecordsStreamName)


def _fp_value(value: str) -> object:
    from qmf.core import Fingerprint

    return Fingerprint.try_create(value)


# --- entity_journal input-guard (contract-shape): a non-selector is refused ----


def test_3_6_entity_journal_requires_selector() -> None:
    """AC1: an entity journal is selected by an EntitySelector; anything else is invalid input."""
    H.assert_refusal(entity_journal([], selector="book-1"), "invalid input")
