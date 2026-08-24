"""CT-23 intent door at the bot runtime boundary (QL-7).

The callback returns zero-or-more CT-23 intents. The door carries only the entry
and exit families. An inbound ``requested_r`` is ``invalid input`` — the bot may
not size. Venue commands never enter. The advisory stop proposal is advisory;
the declared full-loss price is Book-side and is never carried inbound
(DEC-0177, DEC-0182).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final, cast

from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal
from qmf.risk.door import (
    EntryIntent,
    ExitIntent,
    ExitKind,
    parse_inbound_intent,
    reject_close_partial,
    reject_inbound_requested_r,
)

from qml._refuse import invalid, unsupported
from qml.protocol.contract import PROTOCOL_FORMAT_VERSION

__all__ = [
    "BOOK_SIDE_FIELDS",
    "VENUE_COMMAND_FIELDS",
    "accept_intents",
    "intent_identity",
]

BotIntent = EntryIntent | ExitIntent

VENUE_COMMAND_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "venue_command",
        "place",
        "cancel",
        "amend",
        "flatten",
        "amend_protection",
        "new_order",
        "close_position",
        "submit_order",
        "order_request",
    }
)

BOOK_SIDE_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "requested_r",
        "declared_full_loss_price",
        "full_loss_price",
        "original_risk_distance",
        "original_risk_amount",
    }
)

_CLOSE_PARTIAL: Final[str] = "close_partial"


def _unwrap_ok(raw: object) -> object:
    if isinstance(raw, Ok):
        return cast("Ok[object]", raw).value
    return raw


def intent_identity(intent: BotIntent) -> dict[str, object]:
    """fp1 identity of a CT-23 intent — used for deterministic replay compares."""
    return intent.fp1_identity()


def accept_intents(
    raw: object,
    *,
    permitted_exit_intents: object = (),
    protocol_format_version: object = PROTOCOL_FORMAT_VERSION,
) -> Result[tuple[BotIntent, ...]]:
    """Admit zero-or-more CT-23 intents; reject sizing and venue commands.

    ``protocol_format_version`` is accepted so hosts can stamp the QML ladder
    they are speaking; it does not select a CT-23 reader (CT-23 is owned by
    qmf-risk). Unknown protocol versions are refused by the factory, not here.
    """
    del protocol_format_version
    permitted = _permitted_exit_names(permitted_exit_intents)
    if is_refusal(permitted):
        return permitted
    if isinstance(raw, TypedRefusal):
        return raw
    payload = _unwrap_ok(raw)
    if payload is None:
        return Ok(())
    items = _as_intent_sequence(payload)
    if is_refusal(items):
        return items
    accepted: list[BotIntent] = []
    for item in items.value:
        one = _accept_one(item, permitted.value)
        if is_refusal(one):
            return one
        accepted.append(one.value)
    return Ok(tuple(accepted))


def _permitted_exit_names(value: object) -> Result[frozenset[str]]:
    if value is None:
        return Ok(frozenset())
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "permitted_exit_intents",
            "permitted EXIT-intent kinds are a sequence of CT-23 exit kind names",
            given=type(value).__name__,
        )
    names: list[str] = []
    for item in cast("Sequence[object]", value):
        if isinstance(item, ExitKind):
            names.append(item.value)
            continue
        if isinstance(item, str):
            names.append(item)
            continue
        return invalid(
            "permitted_exit_intents",
            "permitted EXIT-intent kinds lie within the ratified CT-23 vocabulary",
            given=repr(item),
        )
    return Ok(frozenset(names))


def _as_intent_sequence(value: object) -> Result[tuple[object, ...]]:
    if isinstance(value, (EntryIntent, ExitIntent)):
        return Ok((value,))
    if isinstance(value, Mapping):
        return Ok((cast("object", value),))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "intents",
            "the callback returns zero-or-more CT-23 intents (entry | exit)",
            given=type(value).__name__,
        )
    return Ok(tuple(cast("Sequence[object]", value)))


def _accept_one(item: object, permitted: frozenset[str]) -> Result[BotIntent]:
    if isinstance(item, EntryIntent):
        return _guard_entry(item)
    if isinstance(item, ExitIntent):
        return _guard_exit(item, permitted)
    if not isinstance(item, Mapping):
        name = type(item).__name__
        if "Venue" in name or "Command" in name:
            return unsupported(
                "intents",
                "the door carries only the entry and exit intent families; a venue "
                "command never enters the Book through CT-23",
                given=name,
            )
        return invalid(
            "intents",
            "the door carries only CT-23 entry and exit intents",
            given=name,
        )
    mapping = cast("Mapping[str, object]", item)
    venue = VENUE_COMMAND_FIELDS.intersection(mapping)
    if venue:
        return unsupported(
            "intents",
            "the door carries only the entry and exit intent families; a venue "
            "command never enters the Book through CT-23",
            fields=tuple(sorted(venue)),
        )
    book_side = BOOK_SIDE_FIELDS.intersection(mapping)
    if "requested_r" in book_side:
        guarded = reject_inbound_requested_r(mapping)
        if is_refusal(guarded):
            return guarded
        return invalid(
            "requested_r",
            "requested_r is Book-resolved and never carried inbound; the bot may not size",
        )
    if book_side:
        return invalid(
            "declared_full_loss_price",
            "the declared full-loss price is derived Book-side at the door; the bot "
            "never carries or is handed the Book's exit logic",
            fields=tuple(sorted(book_side)),
        )
    kind = mapping.get("kind", mapping.get("exit_kind"))
    if kind == _CLOSE_PARTIAL:
        return reject_close_partial()
    guard = reject_inbound_requested_r(mapping)
    if is_refusal(guard):
        return guard
    parsed = parse_inbound_intent(mapping)
    if is_refusal(parsed):
        return parsed
    request = parsed.value
    if request.entry is not None:
        return _guard_entry(request.entry)
    if request.exit is not None:
        return _guard_exit(request.exit, permitted)
    return invalid("intents", "a request is exactly one of two families — entry or exit")


def _guard_entry(entry: EntryIntent) -> Result[BotIntent]:
    if hasattr(entry, "requested_r"):
        return invalid(
            "requested_r",
            "requested_r is Book-resolved and never carried inbound; the bot may not size",
        )
    if hasattr(entry, "declared_full_loss_price") or hasattr(entry, "full_loss_price"):
        return invalid(
            "declared_full_loss_price",
            "the declared full-loss price is derived Book-side at the door",
        )
    return Ok(entry)


def _guard_exit(exit_intent: ExitIntent, permitted: frozenset[str]) -> Result[BotIntent]:
    if exit_intent.kind.value not in permitted:
        return unsupported(
            "kind",
            "an exit intent kind must be in the bot's declared permitted EXIT-intent "
            "subset; an empty subset is an entry-only bot",
            given=exit_intent.kind.value,
            permitted=tuple(sorted(permitted)),
        )
    return Ok(exit_intent)
