"""CT-13 JournalEvent try_create resolvers and decision-payload law.

Split from :mod:`qmf.data.journal` so the public module stays under the Skylos
god-file limits. Callers keep importing :class:`~qmf.data.journal.JournalEvent`
from :mod:`qmf.data.journal`.
"""

from __future__ import annotations

from collections.abc import Mapping

from qmf.core import (
    DisplayTime,
    Instant,
    Ok,
    Result,
    World,
    WriterId,
    is_refusal,
)
from qmf.data.journal_types import (
    CONTRACT_FORMAT_VERSION,
    EMPTY_PAYLOAD,
    REFUSING_DOOR_KEY,
    SUPPRESSING_AUTHORITY_KEY,
    DecisionOutcome,
    JournalEventType,
    as_instant,
    coerce_decision_outcome,
    coerce_event_type,
    coerce_world,
    writer_identity,
)
from qmf.data.store.refusals import invalid_input


def validate_decision_payload(
    event_type: JournalEventType, outcome: DecisionOutcome | None, payload: Mapping[str, object]
) -> Result[DecisionOutcome | None]:
    """Enforce the decision-event outcome law (AC3; DEC-0158, DEC-0150).

    A ``decision`` event MUST carry a :class:`DecisionOutcome`, and a refused-by-door /
    suppressed decision MUST carry its refusing-door / suppressing-authority reference in
    the payload (a non-empty string), so a projection selects on the declared field with a
    resolvable reference. Any other event type MUST NOT carry an outcome. Returns the
    validated outcome (or ``None``), or an ``invalid input`` refusal.
    """
    if event_type is not JournalEventType.DECISION:
        if outcome is not None:
            return invalid_input(
                "outcome",
                "only a decision event carries an outcome; a non-decision event must not",
                event_type=event_type.value,
            )
        return Ok(None)
    if outcome is None:
        return invalid_input(
            "outcome",
            "a decision event carries a mandatory closed outcome: "
            "authorized | refused-by-door | suppressed (DEC-0158)",
        )
    return validate_decision_reference(outcome, payload)


def validate_decision_reference(
    outcome: DecisionOutcome, payload: Mapping[str, object]
) -> Result[DecisionOutcome | None]:
    """Refuse a refused-by-door / suppressed decision that lacks its payload reference."""
    if outcome is DecisionOutcome.REFUSED_BY_DOOR and not _has_reference(
        payload, REFUSING_DOOR_KEY
    ):
        return invalid_input(
            "refusing_door",
            "a refused-by-door decision carries the refusing-door reference in its payload "
            "so a projection resolves who refused, never on key presence (DEC-0158)",
        )
    if outcome is DecisionOutcome.SUPPRESSED and not _has_reference(
        payload, SUPPRESSING_AUTHORITY_KEY
    ):
        return invalid_input(
            "suppressing_authority",
            "a suppressed decision carries the suppressing-authority reference in its "
            "payload so a projection resolves who suppressed it (DEC-0150)",
        )
    return Ok(outcome)


def _has_reference(payload: Mapping[str, object], key: str) -> bool:
    """Whether ``payload`` carries a non-blank string reference under ``key``."""
    value = payload.get(key)
    return isinstance(value, str) and value.strip() != ""


def identity_content(
    *,
    event_type: JournalEventType,
    writer: WriterId,
    sequence: int,
    instant: Instant,
    world: World,
    payload: Mapping[str, object],
    outcome: DecisionOutcome | None,
) -> dict[str, object]:
    """The event's canonical ``fp1`` identity content — the parts that ARE its identity.

    Built identically by :meth:`JournalEvent.try_create` (to compute the fingerprint) and
    :meth:`JournalEvent.fp1_identity` (so a read-back re-fingerprints to the same value).
    ``correlation_id`` and ``display_time`` are **deliberately excluded** (the versioned
    declaration above); the instant is folded in as its int64-ns identity, and the outcome
    is present only for a decision event.
    """
    content: dict[str, object] = {
        "class": "journal-event",
        "event_type": event_type.value,
        "writer": writer_identity(writer),
        "sequence": sequence,
        "instant": instant.fp1_identity(),
        "world": world.value,
        "payload": dict(payload),
        "format_version": CONTRACT_FORMAT_VERSION,
    }
    if outcome is not None:
        content["outcome"] = outcome.value
    return content


def resolve_outcome(value: object | None) -> Result[DecisionOutcome | None]:
    """Resolve the optional decision outcome: ``None``, a member, or a refusal."""
    if value is None:
        return Ok(None)
    resolved = coerce_decision_outcome(value)
    if resolved is None:
        return invalid_input(
            "outcome",
            "a decision outcome is one of the closed set authorized | refused-by-door | suppressed",
            given=repr(value),
            allowed=[member.value for member in DecisionOutcome],
        )
    return Ok(resolved)


def resolve_display_time(value: object | None) -> Result[DisplayTime | None]:
    """Resolve the optional display time: ``None``, a :class:`~qmf.core.DisplayTime`,
    or a refusal. Excluded from identity, so it never affects the fingerprint."""
    if value is None:
        return Ok(None)
    if isinstance(value, DisplayTime):
        return Ok(value)
    return invalid_input(
        "display_time",
        "display_time is an optional qmf-core DisplayTime (ISO-8601-Z, display-only); it "
        "is excluded from identity (DEC-0112)",
        given=repr(value),
    )


def resolve_correlation_id(value: object | None) -> Result[str | None]:
    """Resolve the optional correlation_id: ``None`` or a non-blank string, else refuse.

    Excluded from fp1 identity by the versioned declaration, but still validated as a
    clean token so it round-trips and propagates without ambiguity (DEC-0112, DEC-0108).
    """
    if value is None:
        return Ok(None)
    if isinstance(value, str) and value.strip() != "":
        return Ok(value)
    return invalid_input(
        "correlation_id",
        "correlation_id, when present, is a non-blank linking annotation (or omitted); it "
        "is excluded from fp1 identity but propagated across boundaries (DEC-0112)",
        given=repr(value),
    )


def require_sequence(sequence: object) -> Result[int]:
    """A per-writer non-negative integer sequence, or ``invalid input``."""
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        return invalid_input(
            "sequence",
            "sequence is a per-writer non-negative strictly-increasing integer, "
            "gapless per (writer, boot-epoch) (DEC-0119)",
            given=repr(sequence),
        )
    return Ok(sequence)


def resolve_event_core(
    event_type: object,
    writer: object,
    sequence: object,
    instant: object,
    world: object,
) -> Result[tuple[JournalEventType, WriterId, int, Instant, World]]:
    """Resolve the required identity parts, or the first ``invalid input`` refusal."""
    resolved_type = coerce_event_type(event_type)
    if resolved_type is None:
        return invalid_input(
            "event_type",
            "a journal event is one of exactly seven types: decision, order, fill, "
            "risk transition, promotion, data quality, control action (DEC-0119)",
            given=repr(event_type),
            allowed=[member.value for member in JournalEventType],
        )
    if not isinstance(writer, WriterId):
        return invalid_input(
            "writer",
            "a journal event is written under an AD-8 WriterId with its boot/epoch id",
            given=repr(writer),
        )
    resolved_sequence = require_sequence(sequence)
    if is_refusal(resolved_sequence):
        return resolved_sequence
    resolved_instant = as_instant(instant)
    if resolved_instant is None:
        return invalid_input(
            "instant",
            "the event instant is an Instant or int64 UTC-nanosecond count (evidence "
            "encoding, never an ISO-8601 display string)",
            given=repr(instant),
        )
    resolved_world = coerce_world(world)
    if resolved_world is None:
        return invalid_input(
            "world",
            "world is one of the closed set live | replay | simulated",
            given=repr(world),
        )
    return Ok((resolved_type, writer, resolved_sequence.value, resolved_instant, resolved_world))


def resolve_event_extras(
    payload: Mapping[str, object] | None,
    outcome: object | None,
    correlation_id: object | None,
    display_time: object | None,
    event_type: JournalEventType,
) -> Result[tuple[Mapping[str, object], DecisionOutcome | None, str | None, DisplayTime | None]]:
    """Resolve optional parts and the decision-payload law, or refuse."""
    resolved_outcome = resolve_outcome(outcome)
    if is_refusal(resolved_outcome):
        return resolved_outcome
    resolved_display = resolve_display_time(display_time)
    if is_refusal(resolved_display):
        return resolved_display
    clean_correlation = resolve_correlation_id(correlation_id)
    if is_refusal(clean_correlation):
        return clean_correlation
    resolved_payload: Mapping[str, object] = payload if payload is not None else EMPTY_PAYLOAD
    checked_outcome = validate_decision_payload(
        event_type, resolved_outcome.value, resolved_payload
    )
    if is_refusal(checked_outcome):
        return checked_outcome
    return Ok(
        (resolved_payload, checked_outcome.value, clean_correlation.value, resolved_display.value)
    )
