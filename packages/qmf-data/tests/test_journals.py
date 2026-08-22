"""Tier-1 tests for the CT-13 journal vocabulary (Story 3.5; AC1-AC4).

Covers the seven event types, the decision event's mandatory closed outcome, fp1
identity with correlation_id / display_time excluded, cross-stream causal linkage as
typed edge records, and the gapless-sequence loss signal.
"""

from __future__ import annotations

from qmf.core import (
    DisplayTime,
    OrderingKey,
    World,
    WriterId,
    compare_causal,
    is_ok,
    is_refusal,
)
from qmf.data.journal import (
    CONTRACT_FORMAT_VERSION,
    CORRELATION_ID_EXCLUDED_FROM_FP1,
    DISPLAY_TIME_EXCLUDED_FROM_FP1,
    CausalEdge,
    DecisionOutcome,
    JournalEvent,
    JournalEventType,
    detect_sequence_gaps,
    select_decisions,
    veto_ledger,
)


def _writer(machine: str = "node-a", boot: str = "boot-1") -> WriterId:
    built = WriterId.try_create(machine, "data", "dq", boot)
    assert is_ok(built)
    return built.value


def _event(
    *,
    event_type: object = JournalEventType.DATA_QUALITY,
    sequence: int = 0,
    instant: object = 1_000,
    payload: dict[str, object] | None = None,
    outcome: object | None = None,
    correlation_id: object | None = None,
    display_time: object | None = None,
    writer: WriterId | None = None,
    world: object = World.LIVE,
) -> JournalEvent:
    built = JournalEvent.try_create(
        event_type=event_type,
        writer=writer if writer is not None else _writer(),
        sequence=sequence,
        instant=instant,
        world=world,
        payload=payload,
        outcome=outcome,
        correlation_id=correlation_id,
        display_time=display_time,
    )
    assert is_ok(built), built
    return built.value


# --- AC1: seven event types, addable never redefined ------------------------


def test_seven_ratified_event_types() -> None:
    assert {member.value for member in JournalEventType} == {
        "decision",
        "order",
        "fill",
        "risk transition",
        "promotion",
        "data quality",
        "control action",
    }


def test_event_type_outside_the_seven_is_invalid_input() -> None:
    result = JournalEvent.try_create(
        event_type="heartbeat",
        writer=_writer(),
        sequence=0,
        instant=1,
        world=World.LIVE,
    )
    assert is_refusal(result)
    assert result.category.value == "invalid input"
    assert result.context.get("field") == "event_type"


def test_each_of_the_seven_types_builds() -> None:
    for member in JournalEventType:
        payload: dict[str, object] = {}
        outcome: object | None = None
        if member is JournalEventType.DECISION:
            outcome = DecisionOutcome.AUTHORIZED
        built = JournalEvent.try_create(
            event_type=member,
            writer=_writer(),
            sequence=0,
            instant=1,
            world=World.LIVE,
            payload=payload,
            outcome=outcome,
        )
        assert is_ok(built), member


# --- AC3: the decision event's mandatory closed outcome ---------------------


def test_decision_requires_outcome() -> None:
    result = JournalEvent.try_create(
        event_type=JournalEventType.DECISION,
        writer=_writer(),
        sequence=0,
        instant=1,
        world=World.LIVE,
    )
    assert is_refusal(result)
    assert result.context.get("field") == "outcome"


def test_decision_outcome_is_a_closed_set() -> None:
    result = JournalEvent.try_create(
        event_type=JournalEventType.DECISION,
        writer=_writer(),
        sequence=0,
        instant=1,
        world=World.LIVE,
        outcome="maybe",
    )
    assert is_refusal(result)
    assert result.context.get("field") == "outcome"


def test_refused_by_door_requires_refusing_door_reference() -> None:
    result = JournalEvent.try_create(
        event_type=JournalEventType.DECISION,
        writer=_writer(),
        sequence=0,
        instant=1,
        world=World.LIVE,
        outcome=DecisionOutcome.REFUSED_BY_DOOR,
        payload={},
    )
    assert is_refusal(result)
    assert result.context.get("field") == "refusing_door"


def test_suppressed_requires_suppressing_authority_reference() -> None:
    result = JournalEvent.try_create(
        event_type=JournalEventType.DECISION,
        writer=_writer(),
        sequence=0,
        instant=1,
        world=World.LIVE,
        outcome=DecisionOutcome.SUPPRESSED,
        payload={},
    )
    assert is_refusal(result)
    assert result.context.get("field") == "suppressing_authority"


def test_authorized_decision_needs_no_refusing_reference() -> None:
    event = _event(
        event_type=JournalEventType.DECISION,
        outcome=DecisionOutcome.AUTHORIZED,
    )
    assert event.outcome is DecisionOutcome.AUTHORIZED


def test_non_decision_event_must_not_carry_an_outcome() -> None:
    result = JournalEvent.try_create(
        event_type=JournalEventType.ORDER,
        writer=_writer(),
        sequence=0,
        instant=1,
        world=World.LIVE,
        outcome=DecisionOutcome.AUTHORIZED,
    )
    assert is_refusal(result)
    assert result.context.get("field") == "outcome"


def test_projection_selects_on_declared_outcome_never_key_presence() -> None:
    authorized = _event(
        event_type=JournalEventType.DECISION, sequence=0, outcome=DecisionOutcome.AUTHORIZED
    )
    refused = _event(
        event_type=JournalEventType.DECISION,
        sequence=1,
        outcome=DecisionOutcome.REFUSED_BY_DOOR,
        payload={"refusing_door": "spread-door"},
    )
    suppressed = _event(
        event_type=JournalEventType.DECISION,
        sequence=2,
        outcome=DecisionOutcome.SUPPRESSED,
        payload={"suppressing_authority": "kill-switch"},
    )
    dq = _event(event_type=JournalEventType.DATA_QUALITY, sequence=3)
    events = [authorized, refused, suppressed, dq]

    assert select_decisions(events) == [authorized, refused, suppressed]
    assert select_decisions(events, outcome=DecisionOutcome.AUTHORIZED) == [authorized]
    assert veto_ledger(events) == [refused]


# --- AC4: fp1 identity, correlation_id / display_time excluded ---------------


def test_correlation_id_excluded_from_fp1() -> None:
    assert CORRELATION_ID_EXCLUDED_FROM_FP1 is True
    a = _event(correlation_id="corr-A")
    b = _event(correlation_id="corr-B")
    none = _event()
    assert a.fingerprint.value == b.fingerprint.value == none.fingerprint.value
    # ...but it is carried in the row and propagated.
    assert a.to_row()["correlation_id"] == "corr-A"
    assert "correlation_id" not in none.to_row()


def test_display_time_excluded_from_fp1() -> None:
    assert DISPLAY_TIME_EXCLUDED_FROM_FP1 is True
    dt = DisplayTime(text="1970-01-01T00:00:01.000000000Z", zone="UTC")
    with_dt = _event(display_time=dt)
    without = _event()
    assert with_dt.fingerprint.value == without.fingerprint.value
    assert with_dt.to_row()["display_time"] == {"text": dt.text, "zone": dt.zone}


def test_identity_folds_in_the_declared_parts() -> None:
    base = _event(sequence=5, instant=9, payload={"metric": "spread"})
    # A different sequence, instant, payload, or world changes identity.
    assert (
        base.fingerprint.value
        != _event(sequence=6, instant=9, payload={"metric": "spread"}).fingerprint.value
    )
    assert (
        base.fingerprint.value
        != _event(sequence=5, instant=10, payload={"metric": "spread"}).fingerprint.value
    )
    assert (
        base.fingerprint.value
        != _event(sequence=5, instant=9, payload={"metric": "depth"}).fingerprint.value
    )


def test_journal_stores_int64_ns_while_display_is_iso8601z() -> None:
    event = _event(instant=1_000_000_000)  # one second past the epoch
    assert event.to_row()["instant_ns"] == 1_000_000_000
    rendered = event.render_display_time()
    assert is_ok(rendered)
    assert rendered.value.text == "1970-01-01T00:00:01.000000000Z"
    assert rendered.value.zone == "UTC"


def test_ordering_key_carries_no_causal_meaning() -> None:
    event = _event(instant=5, sequence=2)
    key = event.ordering_key()
    assert isinstance(key, OrderingKey)
    assert key.sequence == 2
    # Two events at the same instant are concurrent: causality refuses to tie-break,
    # even though their ordering keys differ by sequence.
    other = _event(instant=5, sequence=3)
    causal = compare_causal(event.instant, other.instant)
    assert is_refusal(causal)
    assert causal.category.value == "policy rejection"


def test_to_row_round_trips_through_from_row() -> None:
    event = _event(
        event_type=JournalEventType.DECISION,
        sequence=7,
        instant=123,
        outcome=DecisionOutcome.REFUSED_BY_DOOR,
        payload={"refusing_door": "news-window"},
        correlation_id="corr-Z",
        display_time=DisplayTime(text="1970-01-01T00:00:00.000000123Z", zone="UTC"),
    )
    rebuilt = JournalEvent.from_row(event.to_row())
    assert is_ok(rebuilt)
    assert rebuilt.value.fingerprint.value == event.fingerprint.value
    assert rebuilt.value.outcome is DecisionOutcome.REFUSED_BY_DOOR
    assert rebuilt.value.correlation_id == "corr-Z"
    assert rebuilt.value.display_time == event.display_time


def test_tampered_row_is_refused_not_read_back_valid() -> None:
    event = _event(sequence=1, payload={"metric": "spread"})
    row = event.to_row()
    row["sequence"] = 2  # tamper: the stored fingerprint no longer matches
    result = JournalEvent.from_row(row)
    assert is_refusal(result)
    assert result.context.get("field") == "fingerprint"


def test_from_row_rejects_non_mapping_and_missing_fingerprint() -> None:
    assert is_refusal(JournalEvent.from_row("not-a-row"))
    row = _event().to_row()
    del row["fingerprint"]
    result = JournalEvent.from_row(row)
    assert is_refusal(result)
    assert result.context.get("field") == "fingerprint"


def test_float_in_payload_is_refused_at_identity() -> None:
    result = JournalEvent.try_create(
        event_type=JournalEventType.DATA_QUALITY,
        writer=_writer(),
        sequence=0,
        instant=1,
        world=World.LIVE,
        payload={"ratio": 1.5},
    )
    assert is_refusal(result)


def test_payload_is_deep_frozen() -> None:
    payload: dict[str, object] = {"nested": {"k": 1}}
    event = _event(payload=payload)
    payload["nested"] = "mutated"  # the caller's dict must not reach the frozen event
    assert dict(event.payload)["nested"] == {"k": 1}


def test_malformed_parts_are_invalid_input() -> None:
    assert is_refusal(
        JournalEvent.try_create(
            event_type=JournalEventType.DATA_QUALITY,
            writer="not-a-writer",
            sequence=0,
            instant=1,
            world=World.LIVE,
        )
    )
    assert is_refusal(
        JournalEvent.try_create(
            event_type=JournalEventType.DATA_QUALITY,
            writer=_writer(),
            sequence=-1,
            instant=1,
            world=World.LIVE,
        )
    )
    assert is_refusal(
        JournalEvent.try_create(
            event_type=JournalEventType.DATA_QUALITY,
            writer=_writer(),
            sequence=0,
            instant="noon",
            world=World.LIVE,
        )
    )
    assert is_refusal(
        JournalEvent.try_create(
            event_type=JournalEventType.DATA_QUALITY,
            writer=_writer(),
            sequence=0,
            instant=1,
            world="dreamland",
        )
    )
    assert is_refusal(
        JournalEvent.try_create(
            event_type=JournalEventType.DATA_QUALITY,
            writer=_writer(),
            sequence=0,
            instant=1,
            world=World.LIVE,
            correlation_id="   ",
        )
    )
    assert is_refusal(
        JournalEvent.try_create(
            event_type=JournalEventType.DATA_QUALITY,
            writer=_writer(),
            sequence=0,
            instant=1,
            world=World.LIVE,
            display_time="2020-01-01",
        )
    )


# --- AC4: cross-stream causal linkage rides only typed edge records ----------


def test_causal_edge_references_events_by_fp1() -> None:
    a = _event(sequence=0)
    b = _event(sequence=1)
    edge = CausalEdge.link("enacts", a, b)
    assert is_ok(edge)
    row = edge.value.to_row()
    assert row["edge_type"] == "enacts"
    assert row["from_ref"] == a.fingerprint.value
    assert row["to_ref"] == b.fingerprint.value
    assert row["contract_format_version"] == CONTRACT_FORMAT_VERSION


def test_causal_edge_link_uses_identity_fp1_not_correlation_id() -> None:
    # Two events differing only in correlation_id share one fp1, so a causal edge built
    # from either references the same identity — linkage never rides correlation_id.
    a = _event(sequence=0, correlation_id="corr-A")
    a_other = _event(sequence=0, correlation_id="corr-B")
    b = _event(sequence=1)
    edge_a = CausalEdge.link("supersedes", a, b)
    edge_b = CausalEdge.link("supersedes", a_other, b)
    assert is_ok(edge_a)
    assert is_ok(edge_b)
    assert edge_a.value.from_ref.value == edge_b.value.from_ref.value


def test_causal_edge_validation() -> None:
    a = _event(sequence=0)
    assert is_refusal(CausalEdge.link("", a, a))
    assert is_refusal(CausalEdge.link("enacts", "not-an-event", a))
    assert is_refusal(CausalEdge.link("enacts", a, "not-an-event"))
    assert is_refusal(
        CausalEdge.try_create(
            edge_type="enacts", from_ref="bad", to_ref=a.fingerprint, writer=_writer()
        )
    )
    assert is_refusal(
        CausalEdge.try_create(
            edge_type="enacts", from_ref=a.fingerprint, to_ref="bad", writer=_writer()
        )
    )
    assert is_refusal(
        CausalEdge.try_create(
            edge_type="enacts", from_ref=a.fingerprint, to_ref=a.fingerprint, writer="bad"
        )
    )


# --- AC2: gapless sequence, loss surfaced -----------------------------------


def test_gapless_sequence_passes() -> None:
    events = [_event(sequence=i) for i in range(4)]
    assert is_ok(detect_sequence_gaps(events))


def test_missing_sequence_signals_loss() -> None:
    events = [_event(sequence=0), _event(sequence=1), _event(sequence=3)]
    result = detect_sequence_gaps(events)
    assert is_refusal(result)
    assert result.category.value == "storage failure"
    assert result.context.get("signal") == "loss"
    assert result.context.get("expected_sequence") == 2
    assert result.context.get("found_sequence") == 3
    assert result.retryability.value == "no"


def test_duplicate_sequence_signals_loss() -> None:
    events = [_event(sequence=0), _event(sequence=0, instant=2)]
    result = detect_sequence_gaps(events)
    assert is_refusal(result)
    assert result.context.get("kind") == "duplicate"


def test_gap_check_is_per_writer_boot_epoch() -> None:
    # Two boot epochs, each gapless from 0, is not a gap even though sequences repeat.
    boot1 = _writer(boot="boot-1")
    boot2 = _writer(boot="boot-2")
    events = [
        _event(sequence=0, writer=boot1),
        _event(sequence=1, writer=boot1),
        _event(sequence=0, writer=boot2, instant=5),
        _event(sequence=1, writer=boot2, instant=6),
    ]
    assert is_ok(detect_sequence_gaps(events))


def test_gap_check_honors_expected_start() -> None:
    events = [_event(sequence=5), _event(sequence=6)]
    # From 0 this is a missing prefix; from 5 it is gapless.
    assert is_refusal(detect_sequence_gaps(events))
    assert is_ok(detect_sequence_gaps(events, expected_start=5))
