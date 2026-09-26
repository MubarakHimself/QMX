"""CT-25 projection engine: entity journals and the decay-cohort read.

Split from :mod:`qmf.data.logbooks` so the public module stays under the Skylos
god-file limits. Callers keep importing these names from :mod:`qmf.data.logbooks`.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from qmf.core import AccountRole, Ok, Result, is_refusal
from qmf.data.journal import JournalEvent
from qmf.data.logbooks_identity import (
    BindingIdentity,
    BotSeat,
    binding_presence,
    guard_neutral_venue_payload,
    optional_binding,
    optional_bot_seat,
    read_binding,
    read_bot_seat,
    read_role,
)
from qmf.data.logbooks_select import (
    CommandIndex,
    EntityKind,
    EntitySelector,
    binding_matches,
    bot_matches,
)
from qmf.data.logbooks_types import (
    COMMAND_FINGERPRINT_KEY,
    ROLE_KEY,
    CrossRoleRead,
    EventClass,
    coerce_cross_role,
    coerce_fingerprint,
    coerce_role,
    event_class_of,
)
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "Logbook",
    "ProjectedRow",
    "bms_journal",
    "book_journal",
    "bot_logbook",
    "decay_cohort_read",
    "entity_journal",
]


@dataclass(frozen=True, slots=True)
class ProjectedRow:
    """One row of a resolved projection (AC1, AC2, AC3).

    ``event`` is the underlying :class:`~qmf.data.journal.JournalEvent`; ``event_class`` is
    its CT-25 authoring class; ``role`` is the account role the row carries (on **every**
    row, AC3); ``binding`` is the binding identity the row resolved by (from the event for a
    risk-authored row, from the command attribution for a joined venue-authored row);
    ``bot_seat`` is the per-bot identity where one bot is concerned.
    """

    event: JournalEvent
    event_class: EventClass
    role: AccountRole
    binding: BindingIdentity | None = None
    bot_seat: BotSeat | None = None


@dataclass(frozen=True, slots=True)
class Logbook:
    """A resolved read-time projection over the recorded writer-scoped streams (AC1).

    Carries the projected :class:`ProjectedRow`\\ s (in stream order), the
    :class:`EntitySelector` it resolved by (``None`` for the cohort read), and the declared
    :class:`CrossRoleRead` when the projection spanned roles. A logbook is a **view**, never
    a stream: the same recorded set of streams yields many logbooks and no logbook writes.
    """

    rows: tuple[ProjectedRow, ...]
    selector: EntitySelector | None = None
    cross_role: CrossRoleRead | None = None

    @property
    def roles(self) -> frozenset[AccountRole]:
        """The distinct account roles present across the projected rows."""
        return frozenset(row.role for row in self.rows)

    @property
    def events(self) -> tuple[JournalEvent, ...]:
        """The underlying journal events of the projected rows, in order."""
        return tuple(row.event for row in self.rows)


def _match_risk_authored(
    event: JournalEvent, selector: EntitySelector
) -> Result[ProjectedRow | None]:
    """Project a risk-authored event if it matches the selector (value-or-refusal).

    Returns ``Ok(None)`` when the event does not match (including a risk-authored event that
    carries no binding, e.g. a qmf-data control action). A partial/malformed binding, a
    partial bot seat, or a matched row missing its role is a refusal.
    """
    bot_seat_result = read_bot_seat(event)
    if is_refusal(bot_seat_result):
        return bot_seat_result
    bot_seat = bot_seat_result.value

    binding: BindingIdentity | None = None
    if binding_presence(event.payload) != 0:
        built = read_binding(event)
        if is_refusal(built):
            return built
        binding = built.value

    if selector.kind is EntityKind.BOT:
        matched = bot_matches(selector, bot_seat)
    else:
        matched = binding is not None and binding_matches(selector, binding)
    if not matched:
        return Ok(None)

    role = read_role(event)
    if is_refusal(role):
        return role
    return Ok(
        ProjectedRow(
            event=event,
            event_class=EventClass.RISK_AUTHORED,
            role=role.value,
            binding=binding,
            bot_seat=bot_seat,
        )
    )


def _match_venue_authored(
    event: JournalEvent, selector: EntitySelector, command_index: CommandIndex
) -> Result[ProjectedRow | None]:
    """Project a venue-authored event via the command-fingerprint join (value-or-refusal).

    Joins the event's command fingerprint through the index, and — **only for an event that
    actually joins into this requested projection** — guards its neutral payload: a leaked
    Book/Bot identity on a *matched* event is a refusal (AC2). Returns ``Ok(None)`` when the
    event carries no command fingerprint, the command is not indexed, or the attribution does
    not match — the event is not part of this projection.

    The guard is scoped to matched events on purpose (L8): an unrelated venue event on
    *another* Book that happens to carry a leaked key must not poison this Book's clean read.
    Such a leak is still a producer wiring fault, but it is a data-quality concern for the
    leaking producer's own stream to surface — not grounds to refuse an unrelated projection.
    """
    command_fp = coerce_fingerprint(event.payload.get(COMMAND_FINGERPRINT_KEY))
    if command_fp is None:
        return Ok(None)
    attribution = command_index.attribution_for(command_fp)
    if attribution is None:
        return Ok(None)

    if selector.kind is EntityKind.BOT:
        matched = bot_matches(selector, attribution.bot_seat)
    else:
        matched = binding_matches(selector, attribution.binding)
    if not matched:
        return Ok(None)

    guard = guard_neutral_venue_payload(event)
    if is_refusal(guard):
        return guard

    role = read_role(event)
    if is_refusal(role):
        return role
    return Ok(
        ProjectedRow(
            event=event,
            event_class=EventClass.VENUE_AUTHORED,
            role=role.value,
            binding=attribution.binding,
            bot_seat=attribution.bot_seat,
        )
    )


def _select_rows(
    events: Iterable[JournalEvent],
    selector: EntitySelector,
    command_index: CommandIndex | None,
) -> Result[list[ProjectedRow]]:
    """Select every projected row matching the selector, in stream order (value-or-refusal)."""
    rows: list[ProjectedRow] = []
    for event in events:
        if event_class_of(event.event_type) is EventClass.RISK_AUTHORED:
            matched = _match_risk_authored(event, selector)
        elif command_index is not None:
            matched = _match_venue_authored(event, selector, command_index)
        else:
            # A venue-authored event with no join supplied is simply not included: a Book
            # projection without the command-fingerprint join holds decisions and control
            # actions but no orders or fills (exactly the AC2 point).
            continue
        if is_refusal(matched):
            return matched
        if matched.value is not None:
            rows.append(matched.value)
    return Ok(rows)


def _apply_role_scope(
    rows: list[ProjectedRow],
    selector: EntitySelector,
    role: object | None,
    cross_role: object | None,
) -> Result[Logbook]:
    """Resolve the role scope over the selected rows (AC3; FM-11, DEC-0145, DEC-0158).

    Exactly one of three scopes applies. A single ``role`` resolves inside that one
    role-scoped namespace (rows of other roles are simply outside it). A declared
    ``cross_role`` read admits every role, carrying ``role`` on each row. Neither given:
    rows of a single role (or none) are returned, but rows spanning more than one role are a
    ``policy rejection`` refusal (FM-11) — aggregating across roles requires an explicit
    declaration. Passing both ``role`` and ``cross_role`` is a contradiction (``invalid
    input``).
    """
    if role is not None and cross_role is not None:
        return invalid_input(
            "role",
            "declare either a single role-scoped namespace or a cross-role read, not both",
            role=repr(role),
            cross_role=repr(cross_role),
        )
    if role is not None:
        return _scope_single_role(rows, selector, role)
    if cross_role is not None:
        return _scope_cross_role(rows, selector, cross_role)
    return _scope_implicit_role(rows, selector)


def _scope_single_role(
    rows: list[ProjectedRow], selector: EntitySelector, role: object
) -> Result[Logbook]:
    """Keep rows inside one role-scoped namespace."""
    scoped = coerce_role(role)
    if scoped is None:
        return invalid_input(
            "role",
            "role is one of the closed AccountRole set",
            given=repr(role),
            allowed=[member.value for member in AccountRole],
        )
    in_scope = tuple(row for row in rows if row.role is scoped)
    return Ok(Logbook(rows=in_scope, selector=selector, cross_role=None))


def _scope_cross_role(
    rows: list[ProjectedRow], selector: EntitySelector, cross_role: object
) -> Result[Logbook]:
    """Admit every role under one of the two declared cross-role reads."""
    declared = coerce_cross_role(cross_role)
    if declared is None:
        return invalid_input(
            "cross_role",
            "a cross-role read is one of the two declared exceptions: the decay-cohort "
            "read or a multi-role entity projection (DEC-0145, DEC-0149)",
            given=repr(cross_role),
            allowed=[member.value for member in CrossRoleRead],
        )
    return Ok(Logbook(rows=tuple(rows), selector=selector, cross_role=declared))


def _scope_implicit_role(rows: list[ProjectedRow], selector: EntitySelector) -> Result[Logbook]:
    """Return the rows when they share one role; refuse an undeclared multi-role span."""
    distinct = frozenset(row.role for row in rows)
    if len(distinct) > 1:
        return policy_rejection(
            "role",
            "an entity-journal projection spans more than one account role; aggregating "
            "across roles requires an explicitly-declared cross-role read (the decay-cohort "
            "read or a multi-role entity projection), else it is refused (FM-11, DEC-0158)",
            roles=sorted(member.value for member in distinct),
            selector=selector.kind.value,
        )
    return Ok(Logbook(rows=tuple(rows), selector=selector, cross_role=None))


def entity_journal(
    events: Iterable[JournalEvent],
    *,
    selector: object,
    role: object | None = None,
    cross_role: object | None = None,
    command_index: CommandIndex | None = None,
) -> Result[Logbook]:
    """Resolve an entity journal as a read-time projection over recorded streams (AC1-AC3).

    Selects every event matching ``selector`` from the one recorded set of writer-scoped
    streams — risk-authored events by their declared identity fields, and (when a
    ``command_index`` is supplied) venue-authored orders and fills joined through the pinned
    command-fingerprint join. The result resolves inside one role-scoped namespace: pass a
    single ``role`` to read one namespace, a declared ``cross_role`` for the two permitted
    cross-role reads, or neither — in which case a projection spanning more than one role is
    an FM-11 ``policy rejection`` refusal (AC3). Every returned row carries ``role``. This
    never writes and mints no stream (AC1).
    """
    if not isinstance(selector, EntitySelector):
        return invalid_input(
            "selector",
            "an entity journal is selected by an EntitySelector (Book, BMS, Bot, or binding)",
            given=repr(selector),
        )
    selected = _select_rows(events, selector, command_index)
    if is_refusal(selected):
        return selected
    return _apply_role_scope(selected.value, selector, role, cross_role)


def book_journal(
    events: Iterable[JournalEvent],
    book_instance_id: object,
    *,
    role: object | None = None,
    cross_role: object | None = None,
    command_index: CommandIndex | None = None,
) -> Result[Logbook]:
    """The Book journal for one Book instance (AC1) — a convenience over :func:`entity_journal`.

    Selected by ``BookInstanceId``. Supply a ``command_index`` to include the Book's orders
    and fills via the command-fingerprint join; without one the projection holds the Book's
    decisions, risk transitions, control actions, and promotions.
    """
    selector = EntitySelector.for_book(book_instance_id)
    if is_refusal(selector):
        return selector
    return entity_journal(
        events,
        selector=selector.value,
        role=role,
        cross_role=cross_role,
        command_index=command_index,
    )


def bms_journal(
    events: Iterable[JournalEvent],
    bms_instance_id: object,
    *,
    role: object | None = None,
    cross_role: object | None = None,
    command_index: CommandIndex | None = None,
) -> Result[Logbook]:
    """The BMS journal for one BMS instance (AC1) — a convenience over :func:`entity_journal`."""
    selector = EntitySelector.for_bms(bms_instance_id)
    if is_refusal(selector):
        return selector
    return entity_journal(
        events,
        selector=selector.value,
        role=role,
        cross_role=cross_role,
        command_index=command_index,
    )


def bot_logbook(
    events: Iterable[JournalEvent],
    bot_definition_fp: object,
    seat_binding: object,
    *,
    role: object | None = None,
    cross_role: object | None = None,
    command_index: CommandIndex | None = None,
) -> Result[Logbook]:
    """The per-bot journal — the operator's logbook — for one bot seat (AC1).

    Selected by the CT-33 Bot definition ``fp1`` plus its AD-41 seat binding. Supply a
    ``command_index`` to include the bot's orders and fills via the command-fingerprint join.
    """
    selector = EntitySelector.for_bot(bot_definition_fp, seat_binding)
    if is_refusal(selector):
        return selector
    return entity_journal(
        events,
        selector=selector.value,
        role=role,
        cross_role=cross_role,
        command_index=command_index,
    )


def decay_cohort_read(events: Iterable[JournalEvent]) -> Result[Logbook]:
    """The AD-35 decay-cohort read — the first declared cross-role read (AC3; DEC-0149).

    One of the two — and only two — reads permitted to span account roles. It projects every
    cohort event that carries a ``role`` across roles (live and paper alike, so alpha-decay
    is sensed across the roles a strategy operated in), carrying ``role`` on every row and
    declaring :attr:`CrossRoleRead.DECAY_COHORT`. An event that carries **no** ``role`` key is
    not a cohort row and is skipped; but a row that **declares** a ``role`` which is
    malformed (present but outside the closed :class:`~qmf.core.AccountRole` set) is a refusal
    — the same fail-closed rule every other projection applies (FR-34), not a silent drop that
    would keep 1 of 3 rows while ``book_journal`` refuses the same row. This never writes and
    never crosses roles on write (DEC-0158).
    """
    rows: list[ProjectedRow] = []
    for event in events:
        role = read_role(event)
        if is_refusal(role):
            if ROLE_KEY not in event.payload:
                # No role key: this event is not a cohort row (the intended skip).
                continue
            # A role key IS present but does not resolve to a closed AccountRole — a
            # malformed declaration, refused rather than silently dropped (M7).
            return role
        rows.append(
            ProjectedRow(
                event=event,
                event_class=event_class_of(event.event_type),
                role=role.value,
                binding=optional_binding(event),
                bot_seat=optional_bot_seat(event),
            )
        )
    return Ok(Logbook(rows=tuple(rows), selector=None, cross_role=CrossRoleRead.DECAY_COHORT))
