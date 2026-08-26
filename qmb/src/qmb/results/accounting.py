"""Suppression and veto accounting folded from CT-13 journals (Story 19.3).

Tallies are a distinct field group from the V1 returns/trade measure set.
Each count carries the AD-40 ``count`` unit-kind. Keys that did not fire still
emit explicit zeros — they are never omitted. Unresolvable authority or reason
is a typed refusal, never a drop or a silent bucket. Source is the run's own
CT-13 journal streams, never a parallel bespoke log.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final, cast

from qmf.core.exact import ExactRational, UnitKind
from qmf.core.fingerprint import World
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.data.journal import (
    DecisionOutcome,
    JournalEvent,
    JournalEventType,
    select_decisions,
    veto_ledger,
)
from qmf.risk.control_action import AuthorityKind
from qmf.risk.performance import SuppressionCount, VetoCount

from qmb._refuse import invalid, policy

__all__ = [
    "CONTROL_ACTION_SUPPRESSED_SUBTYPE",
    "SUPPRESSION_REASON_CLASSES",
    "TALLY_FIELD_GROUP",
    "TALLY_UNIT_KIND",
    "VETO_DOOR_IDENTITIES",
    "assemble_suppression_and_veto_accounting",
]

TALLY_FIELD_GROUP: Final[str] = "control-accounting"
TALLY_UNIT_KIND: Final[UnitKind] = UnitKind.COUNT
CONTROL_ACTION_SUPPRESSED_SUBTYPE: Final[str] = DecisionOutcome.SUPPRESSED.value

# Spine door roster (AD-36/DEC-0150): protection window, SQS, admission bar,
# bench, budget, capability. Quiet runs still list each key at zero.
VETO_DOOR_IDENTITIES: Final[tuple[str, ...]] = (
    "admission-bar",
    "bench",
    "budget",
    "capability",
    "control-window",
    "sqs",
)

# Arbitration-minted suppression reasons (DEC-0151). Other resolved reason
# classes from the journal are added, never folded into these two.
SUPPRESSION_REASON_CLASSES: Final[tuple[str, ...]] = (
    "collapse-same-mechanical-command",
    "conflict-higher-rank-wins",
)

_AUTHORITY_KEYS: Final[tuple[str, ...]] = (
    "suppressing_authority",
    "authority_kind",
    "authority",
)
_REASON_KEYS: Final[tuple[str, ...]] = ("reason_class", "reason")
_DOOR_KEYS: Final[tuple[str, ...]] = ("refusing_door", "door_identity", "door")
_SUBTYPE_KEYS: Final[tuple[str, ...]] = ("subtype", "kind")


def assemble_suppression_and_veto_accounting(
    journal_events: object = (),
    *,
    world: object = World.REPLAY,
) -> Result[tuple[tuple[SuppressionCount, ...], tuple[VetoCount, ...]]]:
    """Fold CT-13 streams into suppression and veto tallies (R-RPT-8).

    ``journal_events`` is one stream (a sequence of ``JournalEvent``) or several
    writer-scoped streams (a sequence of those). Parallel bespoke logs are
    refused. A quiet stream still emits the closed key roster at count zero.
    """
    resolved_world = _as_world(world)
    if is_refusal(resolved_world):
        return resolved_world
    events = _as_journal_events(journal_events)
    if is_refusal(events):
        return events
    scoped = _require_world(events.value, resolved_world.value)
    if is_refusal(scoped):
        return scoped
    suppression = _fold_suppressions(scoped.value)
    if is_refusal(suppression):
        return suppression
    veto = _fold_vetoes(scoped.value)
    if is_refusal(veto):
        return veto
    return Ok((suppression.value, veto.value))


def _fold_suppressions(events: tuple[JournalEvent, ...]) -> Result[tuple[SuppressionCount, ...]]:
    counts: dict[tuple[str, str], int] = {
        (authority.value, reason): 0
        for authority in AuthorityKind
        for reason in SUPPRESSION_REASON_CLASSES
    }
    for event in select_decisions(events, outcome=DecisionOutcome.SUPPRESSED):
        key = _suppression_key(event, field="suppressing_authority")
        if is_refusal(key):
            return key
        counts[key.value] = counts.get(key.value, 0) + 1
    for event in events:
        if not _is_suppressed_control_action(event):
            continue
        key = _suppression_key(event, field="authority")
        if is_refusal(key):
            return key
        counts[key.value] = counts.get(key.value, 0) + 1
    rows: list[SuppressionCount] = []
    for authority_token, reason in sorted(counts):
        minted = _suppression_row(authority_token, reason, counts[(authority_token, reason)])
        if is_refusal(minted):
            return minted
        rows.append(minted.value)
    return Ok(tuple(rows))


def _fold_vetoes(events: tuple[JournalEvent, ...]) -> Result[tuple[VetoCount, ...]]:
    counts: dict[str, int] = dict.fromkeys(VETO_DOOR_IDENTITIES, 0)
    for event in veto_ledger(events):
        door = _payload_token(event.payload, _DOOR_KEYS)
        if door is None:
            return invalid(
                "refusing_door",
                "a refused-by-door decision carries a resolvable refusing-door "
                "identity; unresolvable doors are a typed refusal, never dropped "
                "or silently bucketed (R-RPT-8, AR-13)",
                given=repr(dict(event.payload).get("refusing_door")),
            )
        counts[door] = counts.get(door, 0) + 1
    rows: list[VetoCount] = []
    for door in sorted(counts):
        minted = _veto_row(door, counts[door])
        if is_refusal(minted):
            return minted
        rows.append(minted.value)
    return Ok(tuple(rows))


def _suppression_key(event: JournalEvent, *, field: str) -> Result[tuple[str, str]]:
    authority = _resolve_authority(_payload_token(event.payload, _AUTHORITY_KEYS), field=field)
    if is_refusal(authority):
        return authority
    reason = _payload_token(event.payload, _REASON_KEYS)
    if reason is None:
        return invalid(
            "reason_class",
            "suppression accounting is keyed by reason class; an unresolvable "
            "reason is a typed refusal, never dropped or silently bucketed "
            "(R-RPT-8, AR-13)",
            given=repr(_first_payload(event.payload, _REASON_KEYS)),
        )
    return Ok((authority.value.value, reason))


def _resolve_authority(value: object, *, field: str) -> Result[AuthorityKind]:
    if isinstance(value, AuthorityKind):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(AuthorityKind(value))
        except ValueError:
            pass
    return invalid(
        field,
        "suppression accounting is keyed by issuing authority from the closed "
        "AD-36 vocabulary; an unresolvable authority is a typed refusal, never "
        "dropped or silently bucketed (R-RPT-8, AR-13)",
        given=repr(value),
        allowed=[member.value for member in AuthorityKind],
    )


def _suppression_row(authority: str, reason: str, count: int) -> Result[SuppressionCount]:
    quantity = _count_quantity(count)
    if is_refusal(quantity):
        return quantity
    return SuppressionCount.try_create(authority, reason, count)


def _veto_row(door: str, count: int) -> Result[VetoCount]:
    quantity = _count_quantity(count)
    if is_refusal(quantity):
        return quantity
    return VetoCount.try_create(door, count)


def _count_quantity(count: int) -> Result[ExactRational]:
    quantity = ExactRational.try_create(count, 1, TALLY_UNIT_KIND)
    if is_refusal(quantity):
        return quantity
    if quantity.value.unit_kind is not UnitKind.COUNT:
        return invalid(
            "unit_kind",
            "suppression and veto counts carry the AD-40 count unit-kind, never money",
            given=quantity.value.unit_kind.value,
        )
    return quantity


def _is_suppressed_control_action(event: JournalEvent) -> bool:
    if event.event_type is not JournalEventType.CONTROL_ACTION:
        return False
    subtype = _payload_token(event.payload, _SUBTYPE_KEYS)
    return subtype == CONTROL_ACTION_SUPPRESSED_SUBTYPE


def _payload_token(payload: Mapping[str, object], keys: Sequence[str]) -> str | None:
    for key in keys:
        raw = payload.get(key)
        if isinstance(raw, AuthorityKind):
            return raw.value
        if isinstance(raw, str) and raw.strip() != "":
            return raw
    return None


def _first_payload(payload: Mapping[str, object], keys: Sequence[str]) -> object:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _as_world(value: object) -> Result[World]:
    if isinstance(value, World):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(World(value))
        except ValueError:
            pass
    return invalid(
        "world",
        "journal streams are instantiated per world; a CT-32 tally names one World",
        given=repr(value),
        allowed=[member.value for member in World],
    )


def _require_world(
    events: tuple[JournalEvent, ...], world: World
) -> Result[tuple[JournalEvent, ...]]:
    for index, event in enumerate(events):
        if event.world is world:
            continue
        return policy(
            "world",
            "suppression and veto tallies read only the run's own CT-13 journal "
            "streams in the run's world; a cross-world event is a typed refusal "
            "(CT-13, DEC-0117)",
            index=index,
            given=event.world.value,
            expected=world.value,
        )
    return Ok(events)


def _as_journal_events(value: object) -> Result[tuple[JournalEvent, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, JournalEvent):
        return Ok((value,))
    parsed_one = _as_one_event(value, index=None)
    if not is_refusal(parsed_one):
        return Ok((parsed_one.value,))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "journal_events",
            "suppression and veto tallies derive only from the run's CT-13 journal "
            "streams, never a parallel bespoke log (R-RPT-8, B-4)",
            given=repr(type(value).__name__),
        )
    items = cast("Sequence[object]", value)
    if not items:
        return Ok(())
    if _looks_like_streams(items):
        return _flatten_streams(items)
    out: list[JournalEvent] = []
    for index, item in enumerate(items):
        parsed = _as_one_event(item, index=index)
        if is_refusal(parsed):
            return parsed
        out.append(parsed.value)
    return Ok(tuple(out))


def _looks_like_streams(items: Sequence[object]) -> bool:
    first = items[0]
    if isinstance(first, (JournalEvent, Mapping, str, bytes)):
        return False
    return isinstance(first, Sequence)


def _flatten_streams(items: Sequence[object]) -> Result[tuple[JournalEvent, ...]]:
    out: list[JournalEvent] = []
    for stream_index, stream in enumerate(items):
        if isinstance(stream, (str, bytes)) or not isinstance(stream, Sequence):
            return invalid(
                "journal_events",
                "each CT-13 journal stream is a sequence of JournalEvent values",
                stream_index=stream_index,
                given=repr(type(stream).__name__),
            )
        for index, item in enumerate(cast("Sequence[object]", stream)):
            parsed = _as_one_event(item, index=index, stream_index=stream_index)
            if is_refusal(parsed):
                return parsed
            out.append(parsed.value)
    return Ok(tuple(out))


def _as_one_event(
    value: object, *, index: int | None, stream_index: int | None = None
) -> Result[JournalEvent]:
    extra: dict[str, object] = {}
    if index is not None:
        extra["index"] = index
    if stream_index is not None:
        extra["stream_index"] = stream_index
    if isinstance(value, JournalEvent):
        return Ok(value)
    if isinstance(value, Mapping):
        rebuilt = JournalEvent.from_row(value)
        if is_refusal(rebuilt):
            return invalid(
                "journal_events",
                "suppression and veto tallies derive only from the run's CT-13 "
                "journal streams, never a parallel bespoke log (R-RPT-8, B-4)",
                given=repr(type(value).__name__),
                **extra,
            )
        return rebuilt
    return invalid(
        "journal_events",
        "suppression and veto tallies derive only from the run's CT-13 journal "
        "streams, never a parallel bespoke log (R-RPT-8, B-4)",
        given=repr(type(value).__name__),
        **extra,
    )
