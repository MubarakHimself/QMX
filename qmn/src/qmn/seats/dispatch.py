"""Hosted-callback intents cross Book / BMS / protection / order, never CT-19.

Story 26.15 / FR-072: a seated callback may emit CT-23 intents only. Those
intents enter the Book door (requested_r Book-resolved, bot never sizes),
bind through the BMS instance named at admission, take the venue-resident
protective-stop gate, and mint CT-19 ``place_order`` from the authorized
intent. The callback cannot construct CT-19, cannot read clock/Book/venue/
signal-snapshot objects, and cannot skip a hop.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Instant, Ok, Result, TypedRefusal, is_refusal
from qmf.risk.door import EntryIntent

from qmn.order.door import (
    BOT_SIZE_FIELDS,
    AuthorizedIntent,
    admit_entry_at_book_door,
    mint_place_order_from_authorized,
    reject_bot_supplied_final_size,
)
from qmn.order.protection import require_venue_resident_protective_stop
from qmn.seats._refuse import invalid, policy
from qmn.seats.admission import AdmittedNodeSeat
from qmn.seats.host import GovernedSeat, drive_governed_seat
from qmn.venue import Command

__all__ = [
    "INTENT_PATH_HOPS",
    "BookPathContext",
    "SeatDispatchReceipt",
    "dispatch_hosted_intents",
    "dispatch_seat_intents",
    "refuse_bot_constructed_ct19",
]

INTENT_PATH_HOPS: Final[tuple[str, ...]] = ("book", "bms", "protection", "order")


@dataclass(frozen=True, slots=True)
class BookPathContext:
    """Inputs every hosted intent must cross — Book door, BMS, protection, order."""

    entry_price: object
    exit_logic_ref: object
    module: object
    book_resolved_requested_r: object
    r_unit_price: object
    value_factor: object
    money_scale: object
    account: object
    venue_id: object
    session_epoch: object
    ordering_ordinal: object
    bms_instance_id: str
    protective_stop_forms: object


@dataclass(frozen=True, slots=True)
class SeatDispatchReceipt:
    """Proof that hosted intents crossed Book / BMS / protection / order."""

    authorized: tuple[AuthorizedIntent, ...]
    commands: tuple[Command, ...]
    hops: tuple[str, ...]
    bms_instance_id: str
    seat_id: str

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "bms_instance_id": self.bms_instance_id,
                "command_count": len(self.commands),
                "hops": list(self.hops),
                "intent_count": len(self.authorized),
                "seat_id": self.seat_id,
            }
        )


def refuse_bot_constructed_ct19(payload: object = None, **extra: object) -> TypedRefusal:
    """A hosted callback cannot mint CT-19; the Book door mints after freeze."""
    given = type(payload).__name__ if payload is not None else "ct-19"
    return policy(
        "ct19",
        "a hosted callback cannot construct CT-19; place_order mints only from "
        "a Book-authorized intent after the BMS/protection/order path (FR-072)",
        given=given,
        **extra,
    )


def dispatch_hosted_intents(
    seat: object,
    intents: object,
    *,
    path: object,
) -> Result[SeatDispatchReceipt]:
    """Admit hosted CT-23 intents through Book / BMS / protection / order."""
    admitted = _as_admitted_seat(seat)
    if is_refusal(admitted):
        return admitted
    context = _as_path(path)
    if is_refusal(context):
        return context
    door = context.value
    if door.bms_instance_id != admitted.value.proof.bms_instance_id:
        return policy(
            "bms_instance_id",
            "hosted intents bind the BMS instance named at seat admission; "
            "the callback cannot skip or substitute the BMS hop",
            admitted=admitted.value.proof.bms_instance_id,
            given=door.bms_instance_id,
        )
    items = _as_intent_sequence(intents)
    if is_refusal(items):
        return items
    authorized: list[AuthorizedIntent] = []
    commands: list[Command] = []
    ordinal = door.ordering_ordinal
    if not isinstance(ordinal, int) or isinstance(ordinal, bool) or ordinal < 0:
        return invalid(
            "ordering_ordinal",
            "the order-path hop carries a non-negative command ordinal",
            given=repr(ordinal),
        )
    for index, item in enumerate(items.value):
        blocked = _refuse_sizing_or_ct19(item)
        if is_refusal(blocked):
            return blocked
        if not isinstance(item, EntryIntent):
            return policy(
                "intents",
                "a hosted callback emits CT-23 intents; only an entry intent "
                "crosses the Book door onto the order path",
                index=index,
                given=type(item).__name__,
            )
        frozen = admit_entry_at_book_door(
            intent=item,
            entry_price=door.entry_price,
            exit_logic_ref=door.exit_logic_ref,
            module=door.module,
            book_resolved_requested_r=door.book_resolved_requested_r,
            r_unit_price=door.r_unit_price,
            value_factor=door.value_factor,
            money_scale=door.money_scale,
        )
        if is_refusal(frozen):
            return frozen
        command = mint_place_order_from_authorized(
            frozen.value,
            venue_id=door.venue_id,
            account=door.account,
            session_epoch=door.session_epoch,
            ordering_ordinal=ordinal + index,
        )
        if is_refusal(command):
            return command
        protected = require_venue_resident_protective_stop(
            command.value,
            forms_per_order_type=door.protective_stop_forms,
        )
        if is_refusal(protected):
            return protected
        authorized.append(frozen.value)
        commands.append(command.value)
    return Ok(
        SeatDispatchReceipt(
            authorized=tuple(authorized),
            commands=tuple(commands),
            hops=INTENT_PATH_HOPS,
            bms_instance_id=door.bms_instance_id,
            seat_id=admitted.value.seat_id,
        )
    )


def dispatch_seat_intents(
    seat: object,
    instant: object,
    *,
    path: object,
    stream: object,
    cancel: object,
    probe: object,
    transition_instant: object = None,
) -> Result[SeatDispatchReceipt]:
    """Drive one hosted callback and send its intents through the money path."""
    admitted = _as_admitted_seat(seat)
    if is_refusal(admitted):
        return admitted
    if not isinstance(instant, Instant):
        return invalid(
            "instant",
            "the evaluation instant rides the callback; bots never read a clock",
            given=repr(instant),
        )
    intents = drive_governed_seat(
        admitted.value.seat,
        instant,
        stream=stream,
        cancel=cancel,
        probe=probe,
        transition_instant=transition_instant,
    )
    if is_refusal(intents):
        return intents
    return dispatch_hosted_intents(admitted.value, intents.value, path=path)


def _as_admitted_seat(value: object) -> Result[AdmittedNodeSeat]:
    if isinstance(value, AdmittedNodeSeat):
        return Ok(value)
    if isinstance(value, GovernedSeat):
        return policy(
            "seat",
            "hosted intents reach the Book/BMS/protection/order path only from "
            "a seat admitted through propose_node_seat; a raw QL-7 construct "
            "is not a money-path grant (E12-F05)",
            given="GovernedSeat",
        )
    return invalid(
        "seat",
        "the money path drives an AdmittedNodeSeat",
        given=type(value).__name__,
    )


def _as_path(value: object) -> Result[BookPathContext]:
    if isinstance(value, BookPathContext):
        if not value.bms_instance_id.strip():
            return invalid(
                "bms_instance_id",
                "the BMS hop is a non-empty instance id named at seat admission",
            )
        return Ok(value)
    return invalid(
        "path",
        "hosted intents cross a BookPathContext; the callback cannot skip "
        "Book, BMS, protection, or order",
        given=type(value).__name__,
        hops=list(INTENT_PATH_HOPS),
    )


def _as_intent_sequence(value: object) -> Result[tuple[object, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, (Command, EntryIntent)):
        return Ok((value,))
    if isinstance(value, Mapping):
        return Ok((cast("object", value),))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "intents",
            "a hosted callback returns zero-or-more CT-23 intents",
            given=type(value).__name__,
        )
    return Ok(tuple(cast("Sequence[object]", value)))


def _refuse_sizing_or_ct19(item: object) -> Result[None]:
    if isinstance(item, Command):
        return refuse_bot_constructed_ct19(item)
    if isinstance(item, Mapping):
        mapping = cast("Mapping[str, object]", item)
        sized = reject_bot_supplied_final_size(mapping)
        if is_refusal(sized):
            return sized
        if "place_order" in mapping or "venue_command" in mapping:
            return refuse_bot_constructed_ct19(mapping)
        extra = BOT_SIZE_FIELDS.intersection(mapping)
        if extra:
            return invalid(
                "size",
                "the bot never supplies final size; quantity is Book-derived",
                fields=tuple(sorted(extra)),
            )
    return Ok(None)
