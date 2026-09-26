"""CT-25 binding identity, bot seat, and pinned payload readers.

Split from :mod:`qmf.data.logbooks` so the public module stays under the Skylos
god-file limits. Callers keep importing these names from :mod:`qmf.data.logbooks`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from qmf.core import (
    AccountRole,
    Fingerprint,
    Ok,
    Result,
    VenueId,
    World,
    is_ok,
    is_refusal,
)
from qmf.data.journal import JournalEvent
from qmf.data.logbooks_types import (
    ACCOUNT_ID_KEY,
    BINDING_KEYS,
    BMS_INSTANCE_ID_KEY,
    BOOK_IDENTITY_FIELDS,
    BOOK_INSTANCE_ID_KEY,
    BOT_DEFINITION_FP_KEY,
    COMMAND_FINGERPRINT_KEY,
    CT25_CONTRACT_FORMAT_VERSION,
    ROLE_KEY,
    SEAT_BINDING_KEY,
    VENUE_ID_KEY,
    clean_token,
    coerce_fingerprint,
    coerce_role,
    coerce_venue_id,
    coerce_world,
)
from qmf.data.store.refusals import invalid_input

__all__ = [
    "BindingIdentity",
    "BotSeat",
    "guard_neutral_venue_payload",
    "read_binding",
    "read_bot_seat",
    "read_command_fingerprint",
    "read_role",
]


@dataclass(frozen=True, slots=True)
class BindingIdentity:
    """The binding identity ``(BookInstanceId, BmsInstanceId, VenueId, AccountId, world)``
    carried by every risk-authored event as identity fields (AC2; DEC-0145, DEC-0143).

    Modelled generically on ``qmf-core`` nouns — :class:`~qmf.core.VenueId` and
    :class:`~qmf.core.World` are qmf-core types; the Book and BMS instance ids and the
    account id are opaque tokens (the same shape qmf-core uses for account and venue
    tokens). No risk/QML type is imported: those arrive in later epics, and this value is
    the generic carrier a projection resolves by. The unchecked constructor is the
    trusted-internal path; :meth:`try_create` validates every part.
    """

    book_instance_id: str
    bms_instance_id: str
    venue_id: VenueId
    account_id: str
    world: World

    @classmethod
    def try_create(
        cls,
        *,
        book_instance_id: object,
        bms_instance_id: object,
        venue_id: object,
        account_id: object,
        world: object,
    ) -> Result[BindingIdentity]:
        """Validate and build a :class:`BindingIdentity`, returning value-or-refusal."""
        parts = _binding_identity_parts(
            book_instance_id=book_instance_id,
            bms_instance_id=bms_instance_id,
            venue_id=venue_id,
            account_id=account_id,
            world=world,
        )
        if is_refusal(parts):
            return parts
        book, bms, venue, account, resolved_world = parts.value
        return Ok(
            cls(
                book_instance_id=book,
                bms_instance_id=bms,
                venue_id=venue,
                account_id=account,
                world=resolved_world,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The binding's canonical ``fp1`` identity content (the parts that ARE its identity)."""
        return {
            "class": "binding-identity",
            "book_instance_id": self.book_instance_id,
            "bms_instance_id": self.bms_instance_id,
            "venue_id": self.venue_id.value,
            "account_id": self.account_id,
            "world": self.world.value,
            "format_version": CT25_CONTRACT_FORMAT_VERSION,
        }


def _binding_identity_parts(
    *,
    book_instance_id: object,
    bms_instance_id: object,
    venue_id: object,
    account_id: object,
    world: object,
) -> Result[tuple[str, str, VenueId, str, World]]:
    """Resolve every binding-identity part, or the first ``invalid input`` refusal."""
    book = clean_token(book_instance_id)
    if book is None:
        return invalid_input(
            "book_instance_id",
            "a binding identity carries a non-blank opaque BookInstanceId",
            given=repr(book_instance_id),
        )
    bms = clean_token(bms_instance_id)
    if bms is None:
        return invalid_input(
            "bms_instance_id",
            "a binding identity carries a non-blank opaque BmsInstanceId",
            given=repr(bms_instance_id),
        )
    venue = coerce_venue_id(venue_id)
    if venue is None:
        return invalid_input(
            "venue_id",
            "a binding identity carries a valid qmf-core VenueId (or its opaque token)",
            given=repr(venue_id),
        )
    account = clean_token(account_id)
    if account is None:
        return invalid_input(
            "account_id",
            "a binding identity carries a non-blank opaque AccountId",
            given=repr(account_id),
        )
    resolved_world = coerce_world(world)
    if resolved_world is None:
        return invalid_input(
            "world",
            "a binding identity carries one of the closed set live | replay | simulated",
            given=repr(world),
        )
    return Ok((book, bms, venue, account, resolved_world))


@dataclass(frozen=True, slots=True)
class BotSeat:
    """A per-bot identity — the CT-33 Bot definition ``fp1`` plus its AD-41 seat binding
    (AC2; DEC-0145, DEC-0173).

    Carried on a risk-authored event **where one bot is concerned**, and the identity a
    per-bot journal (the operator's logbook) resolves by. The Bot definition ``fp1`` is a
    qmf-core :class:`~qmf.core.Fingerprint`; the seat binding is an opaque AD-41 token — no
    QML type is imported.
    """

    bot_definition_fp: Fingerprint
    seat_binding: str


def read_role(event: JournalEvent) -> Result[AccountRole]:
    """Read the account ``role`` a projected row carries (AC3; DEC-0158).

    Every projected row carries ``role`` under the pinned :data:`ROLE_KEY`, so a projection
    can never silently aggregate across roles. A missing or out-of-set role is an ``invalid
    input`` refusal — a matched row without a declared role must not be projected.
    """
    resolved = coerce_role(event.payload.get(ROLE_KEY))
    if resolved is None:
        return invalid_input(
            "role",
            "every projected journal row carries a closed AccountRole under the pinned "
            "'role' key so a projection never aggregates across roles silently (DEC-0158)",
            given=repr(event.payload.get(ROLE_KEY)),
            allowed=[member.value for member in AccountRole],
        )
    return Ok(resolved)


def read_binding(event: JournalEvent) -> Result[BindingIdentity]:
    """Read the binding identity a risk-authored event carries (AC2; DEC-0145, DEC-0143).

    Reads the four binding tokens from the event's payload under the pinned keys and folds
    in the event's own ``world`` as the binding's world (the event already carries world in
    identity, so it is never duplicated into the payload). A missing or malformed part is an
    ``invalid input`` refusal; callers that must tolerate a risk-authored event carrying no
    binding at all (e.g. a qmf-data control action) check presence first.
    """
    payload = event.payload
    return BindingIdentity.try_create(
        book_instance_id=payload.get(BOOK_INSTANCE_ID_KEY),
        bms_instance_id=payload.get(BMS_INSTANCE_ID_KEY),
        venue_id=payload.get(VENUE_ID_KEY),
        account_id=payload.get(ACCOUNT_ID_KEY),
        world=event.world,
    )


def read_bot_seat(event: JournalEvent) -> Result[BotSeat | None]:
    """Read the optional per-bot identity a risk-authored event carries (AC2; DEC-0173).

    Returns ``Ok(None)`` when neither bot key is present (the act concerns no single bot),
    ``Ok(BotSeat)`` when both are present and valid, and an ``invalid input`` refusal for a
    **partial** bot identity (one key without the other, or a malformed fingerprint / blank
    seat) — a half-declared bot seat is a producer wiring mistake, not an omitted key.
    """
    fp_raw = event.payload.get(BOT_DEFINITION_FP_KEY)
    seat_raw = event.payload.get(SEAT_BINDING_KEY)
    if fp_raw is None and seat_raw is None:
        return Ok(None)
    fp = coerce_fingerprint(fp_raw)
    if fp is None:
        return invalid_input(
            "bot_definition_fp",
            "a per-bot identity carries the CT-33 Bot definition fp1 (fp1:sha256:<hex>) "
            "alongside its AD-41 seat binding (DEC-0173)",
            given=repr(fp_raw),
        )
    seat = clean_token(seat_raw)
    if seat is None:
        return invalid_input(
            "seat_binding",
            "a per-bot identity carries a non-blank AD-41 seat binding alongside the "
            "Bot definition fp1 (DEC-0173)",
            given=repr(seat_raw),
        )
    return Ok(BotSeat(bot_definition_fp=fp, seat_binding=seat))


def guard_neutral_venue_payload(event: JournalEvent) -> Result[None]:
    """Refuse a venue-authored event whose payload carries Book/Bot identity (AC2; DEC-0145).

    The neutral venue port cannot carry Book identity and must not learn it: Book identity
    is joined through the command fingerprint (:class:`CommandIndex`), never threaded into
    the venue payload — doing so would create the ``qmf-venue -> qmf-risk`` coupling
    default-deny forbids (DEC-0120). Any :data:`BOOK_IDENTITY_FIELDS` key found in the
    payload is an ``invalid input`` refusal naming the leaked fields.
    """
    leaked = sorted(key for key in BOOK_IDENTITY_FIELDS if key in event.payload)
    if leaked:
        return invalid_input(
            "payload",
            "a venue-authored event's neutral payload must never carry Book/Bot identity; "
            "Book identity is joined through the command fingerprint (CT-25), never threaded "
            "into the venue payload (DEC-0145, DEC-0120)",
            leaked_fields=leaked,
            event_type=event.event_type.value,
        )
    return Ok(None)


def read_command_fingerprint(event: JournalEvent) -> Result[Fingerprint]:
    """Read the command record's content fingerprint a venue-authored event carries (AC2).

    First guards the neutral payload (:func:`guard_neutral_venue_payload`) — a leaked Book
    identity is refused — then reads the command fingerprint under the pinned
    :data:`COMMAND_FINGERPRINT_KEY`. A missing or malformed fingerprint is an ``invalid
    input`` refusal. This is the venue half of the pinned versioned command-fingerprint join
    (DEC-0145, DEC-0143).
    """
    guard = guard_neutral_venue_payload(event)
    if is_refusal(guard):
        return guard
    fp = coerce_fingerprint(event.payload.get(COMMAND_FINGERPRINT_KEY))
    if fp is None:
        return invalid_input(
            "command_fingerprint",
            "a venue-authored event carries the command record's content fingerprint "
            "(fp1:sha256:<hex>), the join key to its risk-authored decision (DEC-0145)",
            given=repr(event.payload.get(COMMAND_FINGERPRINT_KEY)),
        )
    return Ok(fp)


def binding_presence(payload: Mapping[str, object]) -> int:
    """How many of the four binding-identity keys the payload carries."""
    return sum(1 for key in BINDING_KEYS if key in payload)


def optional_binding(event: JournalEvent) -> BindingIdentity | None:
    """The binding identity if the event carries all four keys validly, else ``None``.

    A risk-authored event that declares no binding (zero binding keys) is not attributable
    to a binding and returns ``None``; a fully-present, valid binding is returned. A partial
    binding is treated as absent here (the strict :func:`read_binding` surfaces the malformed
    case where the selection path needs it).
    """
    if binding_presence(event.payload) == 0:
        return None
    built = read_binding(event)
    return built.value if is_ok(built) else None


def optional_bot_seat(event: JournalEvent) -> BotSeat | None:
    """The per-bot identity if validly present, else ``None`` (a malformed seat reads None)."""
    built = read_bot_seat(event)
    return built.value if is_ok(built) else None
