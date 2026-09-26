"""CT-25 entity selectors and the pinned command-fingerprint join.

Split from :mod:`qmf.data.logbooks` so the public module stays under the Skylos
god-file limits. Callers keep importing these names from :mod:`qmf.data.logbooks`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from qmf.core import Fingerprint, Ok, Result, is_refusal
from qmf.data.journal import JournalEvent
from qmf.data.logbooks_identity import (
    BindingIdentity,
    BotSeat,
    optional_bot_seat,
    read_binding,
)
from qmf.data.logbooks_types import (
    COMMAND_FINGERPRINT_KEY,
    EventClass,
    clean_token,
    coerce_fingerprint,
    event_class_of,
)
from qmf.data.store.refusals import invalid_input

__all__ = [
    "CommandAttribution",
    "CommandIndex",
    "EntityKind",
    "EntitySelector",
]


class EntityKind(StrEnum):
    """The kind of entity a projection is selected by (AC1; DEC-0145).

    ``BOOK`` / ``BMS`` resolve from the binding identity every risk-authored event carries;
    ``BOT`` resolves from the CT-33 Bot definition fp1 plus seat binding; ``BINDING`` is the
    combined view selected by the full binding tuple.
    """

    BOOK = "book"
    BMS = "bms"
    BOT = "bot"
    BINDING = "binding"


@dataclass(frozen=True, slots=True)
class EntitySelector:
    """The entity identity a read-time projection selects by (AC1; DEC-0145, DEC-0158).

    A selector is **not** a ``WriterId`` and names no stream — it is the identity a
    projection resolves over the recorded writer-scoped streams. Build one through a factory:
    :meth:`for_book`, :meth:`for_bms`, :meth:`for_bot`, or :meth:`for_binding` (the combined
    view). The unchecked constructor is the trusted-internal path.
    """

    kind: EntityKind
    book_instance_id: str | None = None
    bms_instance_id: str | None = None
    bot_seat: BotSeat | None = None
    binding: BindingIdentity | None = None

    @classmethod
    def for_book(cls, book_instance_id: object) -> Result[EntitySelector]:
        """Select the Book journal for one Book instance (AC1; DEC-0145)."""
        book = clean_token(book_instance_id)
        if book is None:
            return invalid_input(
                "book_instance_id",
                "a Book projection is selected by a non-blank BookInstanceId",
                given=repr(book_instance_id),
            )
        return Ok(cls(kind=EntityKind.BOOK, book_instance_id=book))

    @classmethod
    def for_bms(cls, bms_instance_id: object) -> Result[EntitySelector]:
        """Select the BMS journal for one BMS instance (AC1; DEC-0145)."""
        bms = clean_token(bms_instance_id)
        if bms is None:
            return invalid_input(
                "bms_instance_id",
                "a BMS projection is selected by a non-blank BmsInstanceId",
                given=repr(bms_instance_id),
            )
        return Ok(cls(kind=EntityKind.BMS, bms_instance_id=bms))

    @classmethod
    def for_bot(cls, bot_definition_fp: object, seat_binding: object) -> Result[EntitySelector]:
        """Select the per-bot journal (the operator's logbook) for one bot seat (AC1)."""
        fp = coerce_fingerprint(bot_definition_fp)
        if fp is None:
            return invalid_input(
                "bot_definition_fp",
                "a per-bot projection is selected by the CT-33 Bot definition fp1 "
                "(fp1:sha256:<hex>) plus its AD-41 seat binding (DEC-0173)",
                given=repr(bot_definition_fp),
            )
        seat = clean_token(seat_binding)
        if seat is None:
            return invalid_input(
                "seat_binding",
                "a per-bot projection is selected by a non-blank AD-41 seat binding "
                "alongside the Bot definition fp1 (DEC-0173)",
                given=repr(seat_binding),
            )
        return Ok(
            cls(kind=EntityKind.BOT, bot_seat=BotSeat(bot_definition_fp=fp, seat_binding=seat))
        )

    @classmethod
    def for_binding(cls, binding: object) -> Result[EntitySelector]:
        """Select the combined per-binding view for a full binding tuple (AC1; DEC-0145)."""
        if not isinstance(binding, BindingIdentity):
            return invalid_input(
                "binding",
                "a combined per-binding projection is selected by a BindingIdentity value",
                given=repr(binding),
            )
        return Ok(cls(kind=EntityKind.BINDING, binding=binding))


def binding_matches(selector: EntitySelector, binding: BindingIdentity) -> bool:
    """Whether a binding identity matches a Book / BMS / combined-binding selector.

    Only ever called for a non-BOT selector (a BOT selector is matched by :func:`bot_matches`
    on the per-bot identity); the trailing comparison serves the combined ``BINDING`` view.
    """
    if selector.kind is EntityKind.BOOK:
        return binding.book_instance_id == selector.book_instance_id
    if selector.kind is EntityKind.BMS:
        return binding.bms_instance_id == selector.bms_instance_id
    return binding == selector.binding


def bot_matches(selector: EntitySelector, bot_seat: BotSeat | None) -> bool:
    """Whether a per-bot identity matches a BOT selector."""
    return bot_seat is not None and bot_seat == selector.bot_seat


@dataclass(frozen=True, slots=True)
class CommandAttribution:
    """The binding (and optional bot) a command record attributes a venue event to (AC2).

    Built from a risk-authored event carrying the command's content fingerprint: the command
    record supplies the binding identity as an identity field, so a venue-authored event that
    shares the command fingerprint inherits that binding through the join, and never learns
    Book identity itself (DEC-0145, DEC-0143).
    """

    binding: BindingIdentity
    bot_seat: BotSeat | None = None


def _empty_command_index() -> Mapping[str, CommandAttribution]:
    """A shared-safe empty command-fingerprint map (the default for an unbuilt index)."""
    empty: dict[str, CommandAttribution] = {}
    return MappingProxyType(empty)


@dataclass(frozen=True, slots=True)
class CommandIndex:
    """The pinned versioned command-fingerprint join surface (AC2; DEC-0145, DEC-0143).

    Maps a command record's content fingerprint to the :class:`CommandAttribution` a
    venue-authored event inherits when it shares that fingerprint. Built from the
    risk-authored events that carry a command fingerprint (a decision or control action that
    authorized a command), so a Book projection joins orders and fills to their authorizing
    decision without threading Book identity into the neutral venue payload. The join key and
    table are CT-25 surface, not implementer judgment.
    """

    by_command: Mapping[str, CommandAttribution] = field(default_factory=_empty_command_index)

    @classmethod
    def build(cls, events: Iterable[JournalEvent]) -> Result[CommandIndex]:
        """Index every risk-authored event that carries a command fingerprint (AC2).

        A risk-authored event carrying the pinned :data:`COMMAND_FINGERPRINT_KEY` plus a
        binding is a command record; its ``command_fingerprint -> attribution`` entry is
        added. A repeated fingerprint with an **equal** attribution is idempotent; a repeated
        fingerprint with a **conflicting** attribution is an ``invalid input`` refusal — one
        command fingerprint must never attribute to two bindings (an integrity fault). A
        risk-authored event that carries a command fingerprint but no valid binding is
        refused; venue-authored events are ignored here (they consume the index, not build
        it).
        """
        index: dict[str, CommandAttribution] = {}
        for event in events:
            attributed = _index_risk_authored_command(index, event)
            if is_refusal(attributed):
                return attributed
        return Ok(cls(by_command=MappingProxyType(dict(index))))

    def attribution_for(self, command_fingerprint: Fingerprint) -> CommandAttribution | None:
        """The binding a venue-authored event inherits for this command fingerprint, or ``None``."""
        return self.by_command.get(command_fingerprint.value)


def _index_risk_authored_command(
    index: dict[str, CommandAttribution], event: JournalEvent
) -> Result[None]:
    """Add one risk-authored command record to ``index``, or refuse a conflict."""
    if event_class_of(event.event_type) is not EventClass.RISK_AUTHORED:
        return Ok(None)
    raw = event.payload.get(COMMAND_FINGERPRINT_KEY)
    if raw is None:
        return Ok(None)
    command_fp = coerce_fingerprint(raw)
    if command_fp is None:
        return invalid_input(
            "command_fingerprint",
            "a command record's command fingerprint is fp1:sha256:<hex> (DEC-0145)",
            given=repr(raw),
        )
    binding = read_binding(event)
    if is_refusal(binding):
        return binding
    attribution = CommandAttribution(binding=binding.value, bot_seat=optional_bot_seat(event))
    existing = index.get(command_fp.value)
    if existing is not None and existing != attribution:
        return invalid_input(
            "command_fingerprint",
            "one command fingerprint attributes to two different bindings; a command "
            "record must resolve to a single binding identity (DEC-0145, DEC-0143)",
            command_fingerprint=command_fp.value,
        )
    index[command_fp.value] = attribution
    return Ok(None)
