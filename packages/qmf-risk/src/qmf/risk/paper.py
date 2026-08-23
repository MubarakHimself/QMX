"""Story 10.5 — paper as a dated binding-epoch change (COMP-QMF-RISK).

Paper is a **Book-level standing evidence state**, expressed as a dated change of the
Book's execution binding — a record change, never a new object and never a Bot twin
(AD-35; DEC-0149, DEC-0143). This module defines that mechanism on ``qmf-core`` nouns,
the CT-24 Book-mode / binding-transition stream:

* the three never-interchanged vocabularies (:class:`BookMode` ``LIVE | PAPER``,
  :class:`SeatState` ``active | benched``, and — imported from
  :mod:`qmf.risk.binding` — the binding state ``live | paper | stood-down``), guarded by
  :func:`validate_book_mode`: a mode-field write that names a seat-state or binding-state
  word is an ``invalid input`` refusal (AC1; CT-24 invariant);
* the CT-24 :class:`BindingTransitionRecord` — a dated, append-only mode-change record
  over the Book's execution binding — and the :class:`BindingTransitionStream` whose
  :meth:`~BindingTransitionStream.current_mode` is the **read-time fold** over the stream
  under AD-36's fold contract (ordering key ``transition_instant``, a knowledge-time
  bound, a declared most-restrictive equal-instant disposition, and never a refusal on
  the trading path — it returns the most-restrictive :class:`BookMode.PAPER` and flags a
  data-quality fallback), never a stored mutable field (AC1; DEC-0149, DEC-0150);
* :func:`resolve_execution_target` — routing separated from binding: the per-intent
  :class:`ExecutionTarget` is resolved **once**, from ``(Book mode, seat state,
  active-control set)``, into exactly one target, so one intent never produces two
  submissions and a mode flip never replays a command; ``PAPER`` (or a benched seat, or a
  routes-to-paper control) selects the paired demo target **without changing the binding
  identity** (AC2, AC4; DEC-0149);
* the :class:`PaperTargetLog` — one active paper-routing target per live binding at an
  instant, re-pointable by a superseding dated record; no resolvable target is an
  ``unavailable dependency`` refusal and live trading is unaffected (AC3; DEC-0149);
* every :class:`TriggerKind` / :class:`ActiveControl` declares a mandatory
  :class:`TriggerDisposition` (``routes-to-paper | blocks-paper``): a market-risk control
  blocks paper too, a capital/authority control routes to paper, and what continues under
  any control is the **recording** — recording is not trading (AC4; DEC-0149, DEC-0150);
* paper money is **frozen evidence**: the :class:`PaperEpochRecord` freezes a
  configurable UI-editable starting balance at flip; a :func:`reset_paper_epoch` mints a
  new operator-signed ``paper_epoch_reset`` record with a fresh balance and a lineage
  edge (the running balance never mutated, the :class:`PaperEpochLog` append-only), and
  :func:`reject_paper_pnl_to_treasury` refuses any crossing of the money boundary (AC5;
  DEC-0149, DEC-0157, DEC-0158);
* :func:`authorize_return_to_live` — automatic only where the clearing cause is clocked
  and mechanical (minting a CT-24 transition, never a CT-30 resume); anything touching
  real money requires an operator signature and paper performance never authorizes a
  return (AC6; DEC-0149, DEC-0041, DEC-0150).

qmf-risk imports **only** ``qmf-core`` (default-deny, L30/DEC-0120) and sibling
``qmf.risk`` modules; nothing imports ``qmf.risk``. Ratified ``defined-unwired`` surface:
no live binding, order, mode transition, or flatten is authorized by this code — records
reach ``qmf-registry`` / ``qmf-data`` only through the composition root, and no clock is
read below it (every :class:`~qmf.core.Instant` is injected) (DEC-0158).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

from qmf.core import (
    AccountRole,
    Fingerprint,
    Instant,
    Money,
    Ok,
    Result,
    TypedRefusal,
    VenueId,
    fingerprint,
    is_refusal,
)
from qmf.risk._common import clean_str, coerce_enum, invalid, policy, type_name, unavailable
from qmf.risk.binding import BindingState, BookInstanceId
from qmf.risk.numeraire import V1_NUMERAIRE

__all__ = [
    "ActiveControl",
    "BindingTransitionRecord",
    "BindingTransitionStream",
    "BookMode",
    "ClearingCause",
    "ExecutionResolution",
    "ExecutionTarget",
    "ModeFoldResult",
    "PaperEpochLog",
    "PaperEpochRecord",
    "PaperTargetLog",
    "PaperTargetRecord",
    "ReturnMechanism",
    "ReturnToLiveOutcome",
    "RoutingOutcome",
    "SeatState",
    "TreasuryBoundaryKind",
    "TriggerDisposition",
    "TriggerKind",
    "authorize_return_to_live",
    "mint_return_to_live_transition",
    "reject_paper_pnl_to_treasury",
    "reset_paper_epoch",
    "resolve_execution_target",
    "validate_book_mode",
]

# This module's own contract format version stamped into fp1 identity content; its
# meaning never mutates — an incompatible change mints the next version (L15).
_PAPER_FORMAT_VERSION = 1


# --- the three never-interchanged vocabularies -------------------------------


class BookMode(StrEnum):
    """The whole Book-mode space, exactly ``LIVE | PAPER`` (CT-24; DEC-0149).

    The values are upper-case by deliberate discipline so a lower-case ``live`` or
    ``paper`` (the binding-state words) written into a mode field is caught as a
    vocabulary confusion, not silently accepted (:func:`validate_book_mode`). ``BENCHED``
    is a bot-seat word only and never appears here; there are no Bot twins, ever
    (DEC-0069 stays dead).
    """

    LIVE = "LIVE"
    PAPER = "PAPER"


class SeatState(StrEnum):
    """The bot-seat state, ``active | benched`` (CT-29/AD-41; DEC-0149, DEC-0155).

    One of the three vocabularies never interchanged — seat state here, Book mode
    :class:`BookMode`, and binding state :class:`~qmf.risk.binding.BindingState`. A
    benched seat routes its intents to the paired paper target without re-minting the
    binding; ``benched`` is never written into a Book-mode field.
    """

    ACTIVE = "active"
    BENCHED = "benched"


class TriggerDisposition(StrEnum):
    """Every trigger kind's mandatory disposition, ``routes-to-paper | blocks-paper``.

    An open trigger-kind set with no classification rule leaves the next minted kind
    undetermined, so the disposition is mandatory (DEC-0149). ``ROUTES_TO_PAPER`` covers
    **capital or authority** reasons (a kill-line stand-down, a benched seat) — activity
    keeps flowing to the paper target. ``BLOCKS_PAPER`` covers **market-risk** reasons (a
    protection window, the kill switch) — it blocks paper exactly as it blocks live,
    because those two produce non-interchangeable evidence.
    """

    ROUTES_TO_PAPER = "routes-to-paper"
    BLOCKS_PAPER = "blocks-paper"


class RoutingOutcome(StrEnum):
    """The outcome of resolving a per-intent execution target (AC2, AC4; DEC-0149).

    ``ROUTED_LIVE`` — the intent routes to the live target; ``ROUTED_PAPER`` — it routes
    to the single paired demo target (a paper excursion that never changes the binding
    identity); ``BLOCKED`` — a market-risk control blocks live and paper alike, so no
    submission is made and only the decision is recorded (recording is not trading).
    """

    ROUTED_LIVE = "routed-live"
    ROUTED_PAPER = "routed-paper"
    BLOCKED = "blocked"


class TreasuryBoundaryKind(StrEnum):
    """The AD-16 treasury boundary-event kinds; a paper reset is one (DEC-0158).

    ``PAPER_EPOCH_RESET`` mints a fresh paper epoch (a new declared balance and a lineage
    edge); ``SWEEP | REFUND | RE_SEED`` are the other money-boundary events. No money
    moves without one, and a boundary event never closes a position.
    """

    SWEEP = "sweep"
    REFUND = "refund"
    RE_SEED = "re_seed"
    PAPER_EPOCH_RESET = "paper_epoch_reset"


class ClearingCause(StrEnum):
    """Why a Book would return toward live, classified for AC6 (DEC-0149, DEC-0041).

    ``CLOCKED_MECHANICAL`` — the clearing cause is itself clocked and mechanical (a
    next-open bench reset, a day-boundary budget reset), so the return is **automatic**
    and mints a CT-24 transition, never a CT-30 resume. ``FIRST_LIVE_ENTRY`` — a first
    entry into live touches real money and requires an operator signature. ``CONTROL_
    STAND_DOWN`` — a control-action stand-down (a kill-line breach) clears **only** by an
    operator CT-30 resume, never a CT-24 transition.
    """

    CLOCKED_MECHANICAL = "clocked-mechanical"
    FIRST_LIVE_ENTRY = "first-live-entry"
    CONTROL_STAND_DOWN = "control-stand-down"


class ReturnMechanism(StrEnum):
    """The stream a return-to-live clears on (AC6; DEC-0149, DEC-0150).

    ``CT24_TRANSITION`` — a mode transition on the CT-24 stream (a clocked mechanical
    clear or a signed first-live-entry). ``CT30_RESUME`` — an operator resume on the
    distinct CT-30 control-action stream (a control stand-down). The two streams are
    distinct so AD-36's operator-only de-escalation is never quietly contradicted by an
    automatic return.
    """

    CT24_TRANSITION = "ct24-transition"
    CT30_RESUME = "ct30-resume"


_BOOK_MODE_VALUES: Final[frozenset[str]] = frozenset(mode.value for mode in BookMode)
_SEAT_STATE_WORDS: Final[frozenset[str]] = frozenset(state.value for state in SeatState)
_BINDING_STATE_WORDS: Final[frozenset[str]] = frozenset(state.value for state in BindingState)


def validate_book_mode(value: object) -> Result[BookMode]:
    """Resolve a Book-mode value, refusing a seat-state or binding-state word (AC1).

    Accepts a :class:`BookMode` member or its exact upper-case value. A value that names a
    **seat-state** word (``active | benched``) or a **binding-state** word (``live |
    paper | stood-down``) is an ``invalid input`` refusal — the three vocabularies are
    never interchanged and a mode-field write may not smuggle one in (CT-24 invariant;
    DEC-0149, DEC-0150). Any other unknown value is an ``invalid input`` refusal too — the
    whole mode space is exactly ``LIVE | PAPER``.
    """
    if isinstance(value, BookMode):
        return Ok(value)
    if isinstance(value, str):
        if value in _BOOK_MODE_VALUES:
            return Ok(BookMode(value))
        if value in _SEAT_STATE_WORDS or value in _BINDING_STATE_WORDS:
            return invalid(
                "mode",
                "a mode-field write named a seat-state or binding-state word; the three "
                "vocabularies are never interchanged — Book mode is exactly LIVE|PAPER, seat "
                "state is active|benched, binding state is live|paper|stood-down",
                given=repr(value),
                book_mode_space=sorted(_BOOK_MODE_VALUES),
            )
        return invalid(
            "mode",
            "an unknown Book mode; the whole mode space is exactly LIVE|PAPER",
            given=repr(value),
            allowed=sorted(_BOOK_MODE_VALUES),
        )
    return invalid("mode", "a Book mode is LIVE|PAPER", given=repr(value))


# --- trigger kinds, active controls, and execution targets -------------------


@dataclass(frozen=True, slots=True)
class TriggerKind:
    """An addable-never-redefined trigger kind with its mandatory disposition (DEC-0149).

    The ``name`` is an opaque token from an **open** set (never a closed enumeration);
    the :class:`TriggerDisposition` is mandatory, because an open kind set with no
    classification rule leaves the next minted kind undetermined.
    """

    name: str
    disposition: TriggerDisposition

    @classmethod
    def try_create(cls, name: object, disposition: object) -> Result[TriggerKind]:
        """Validate and build a :class:`TriggerKind`, value-or-refusal."""
        token = clean_str(name)
        if token is None:
            return invalid(
                "name",
                "a trigger kind names an opaque, addable-never-redefined token",
                given=repr(name),
            )
        resolved = coerce_enum(TriggerDisposition, disposition)
        if resolved is None:
            return invalid(
                "disposition",
                "every trigger kind declares a mandatory disposition, routes-to-paper|blocks-paper",
                given=repr(disposition),
                allowed=[member.value for member in TriggerDisposition],
            )
        return Ok(cls(name=token, disposition=resolved))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this trigger kind."""
        return {
            "class": "trigger-kind",
            "name": self.name,
            "disposition": self.disposition.value,
            "format_version": _PAPER_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class ActiveControl:
    """One control in force at intent-mint, carrying its disposition (AC4; DEC-0149).

    The ``control_id`` is an opaque token identifying the firing control; the
    :class:`TriggerDisposition` decides whether it routes the intent to paper (capital or
    authority reason) or blocks paper too (market-risk reason).
    """

    control_id: str
    disposition: TriggerDisposition

    @classmethod
    def try_create(cls, control_id: object, disposition: object) -> Result[ActiveControl]:
        """Validate and build an :class:`ActiveControl`, value-or-refusal."""
        token = clean_str(control_id)
        if token is None:
            return invalid(
                "control_id", "an active control names an opaque control id", given=repr(control_id)
            )
        resolved = coerce_enum(TriggerDisposition, disposition)
        if resolved is None:
            return invalid(
                "disposition",
                "an active control declares its disposition routes-to-paper|blocks-paper",
                given=repr(disposition),
                allowed=[member.value for member in TriggerDisposition],
            )
        return Ok(cls(control_id=token, disposition=resolved))


@dataclass(frozen=True, slots=True)
class ExecutionTarget:
    """A per-intent execution target — the ``(role, VenueId, account)`` it submits to.

    ``role`` rides the execution target (not the AD-29 binding tuple), which is what lets
    routing select the paired demo target without re-minting the binding (DEC-0149). Live
    and demo are distinct ``(VenueId, account)`` streams (:meth:`command_stream`), so an
    outstanding ``UNKNOWN`` on one never gates the other. This value enters the CT-19
    command record's identity (:meth:`fp1_identity`).
    """

    role: AccountRole
    venue_id: VenueId
    account_id: str

    @classmethod
    def try_create(
        cls, role: object, venue_id: object, account_id: object
    ) -> Result[ExecutionTarget]:
        """Validate and build an :class:`ExecutionTarget`, value-or-refusal."""
        resolved_role = coerce_enum(AccountRole, role)
        if resolved_role is None:
            return invalid(
                "role",
                "an execution target carries a CT-03 account role",
                given=repr(role),
                allowed=[member.value for member in AccountRole],
            )
        if not isinstance(venue_id, VenueId):
            return invalid(
                "venue_id",
                "an execution target names a VenueId — live and demo are distinct "
                "(VenueId, account) streams",
                given=repr(venue_id),
            )
        account = clean_str(account_id)
        if account is None:
            return invalid(
                "account_id", "an execution target names an account id", given=repr(account_id)
            )
        return Ok(cls(role=resolved_role, venue_id=venue_id, account_id=account))

    def command_stream(self) -> tuple[VenueId, str]:
        """The ``(VenueId, account)`` command stream this target submits to."""
        return (self.venue_id, self.account_id)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — enters the command identity."""
        return {
            "class": "execution-target",
            "role": self.role.value,
            "venue_id": self.venue_id.value,
            "account_id": self.account_id,
            "format_version": _PAPER_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class ExecutionResolution:
    """The single resolved routing outcome for one intent (AC2, AC4; DEC-0149).

    Carries exactly one :class:`RoutingOutcome`; the ``execution_target`` is present iff
    the outcome routed (never both a live and a paper target — one intent can never
    produce two submissions), and ``blocking_control_id`` is present iff ``BLOCKED``.
    :meth:`is_recording_only` marks the ``BLOCKED`` case, where what continues is the
    recording, not a trade.
    """

    outcome: RoutingOutcome
    routing_reason: str
    execution_target: ExecutionTarget | None = None
    blocking_control_id: str | None = None

    def is_recording_only(self) -> bool:
        """True when a market-risk control blocked the intent — record, never trade."""
        return self.outcome is RoutingOutcome.BLOCKED

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the resolution."""
        content: dict[str, object] = {
            "class": "execution-resolution",
            "outcome": self.outcome.value,
            "routing_reason": self.routing_reason,
            "format_version": _PAPER_FORMAT_VERSION,
        }
        if self.execution_target is not None:
            content["execution_target"] = self.execution_target.fp1_identity()
        if self.blocking_control_id is not None:
            content["blocking_control_id"] = self.blocking_control_id
        return content


def _coerce_active_controls(value: object) -> tuple[ActiveControl, ...] | TypedRefusal:
    """Resolve the active-control set to a tuple, or a refusal (empty is legal)."""
    given = type_name(value)
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        return invalid(
            "active_controls",
            "the active-control set is a collection of ActiveControl values (possibly empty)",
            given=given,
        )
    items: list[ActiveControl] = []
    for item in cast("Iterable[object]", value):
        if not isinstance(item, ActiveControl):
            return invalid(
                "active_controls", "each active control is an ActiveControl", given=repr(item)
            )
        items.append(item)
    return tuple(items)


def resolve_execution_target(
    *,
    book_mode: object,
    seat_state: object,
    active_controls: object,
    live_target: object,
    paper_target: object = None,
) -> Result[ExecutionResolution]:
    """Resolve the single per-intent execution target from the three inputs (AC2, AC4).

    Routing is separated from binding: the target is resolved **once**, at intent mint,
    from ``(Book mode, seat state, active-control set)`` and enters the command record's
    identity — the binding tuple is never touched, so a mode flip never replays a command
    and one intent can never produce two submissions (DEC-0149). The precedence, most
    restrictive first:

    1. **A ``blocks-paper`` control dominates** — a market-risk control (a protection
       window, the kill switch) blocks live and paper alike; the outcome is ``BLOCKED``
       and only the decision is recorded (recording is not trading);
    2. **route to paper** when the Book mode is ``PAPER``, the seat is ``benched``, or a
       ``routes-to-paper`` control fired — selecting the single paired demo target; no
       resolvable target is an ``unavailable dependency`` refusal (AC3);
    3. otherwise **route to live**.

    ``live_target`` must carry the ``live`` role and ``paper_target`` (when present) must
    not — live and demo are distinct streams.
    """
    resolved_mode = coerce_enum(BookMode, book_mode)
    if resolved_mode is None:
        return invalid(
            "book_mode",
            "routing reads a resolved Book mode (LIVE|PAPER) from the read-time fold",
            given=repr(book_mode),
        )
    resolved_seat = coerce_enum(SeatState, seat_state)
    if resolved_seat is None:
        return invalid(
            "seat_state",
            "routing reads a seat state (active|benched)",
            given=repr(seat_state),
            allowed=[member.value for member in SeatState],
        )
    controls = _coerce_active_controls(active_controls)
    if isinstance(controls, TypedRefusal):
        return controls
    if not isinstance(live_target, ExecutionTarget):
        return invalid(
            "live_target", "routing reads the live ExecutionTarget", given=repr(live_target)
        )
    if live_target.role is not AccountRole.LIVE:
        return invalid(
            "live_target",
            "the live execution target carries the live account role",
            given=live_target.role.value,
        )
    resolved_paper: ExecutionTarget | None
    if paper_target is None:
        resolved_paper = None
    elif isinstance(paper_target, ExecutionTarget):
        if paper_target.role is AccountRole.LIVE:
            return invalid(
                "paper_target",
                "the paper-routing target is a paired demo account, never the live account; "
                "live and demo are distinct streams",
                given=paper_target.role.value,
            )
        resolved_paper = paper_target
    else:
        return invalid(
            "paper_target",
            "the paper-routing target is an ExecutionTarget or None",
            given=repr(paper_target),
        )

    blocking = next((c for c in controls if c.disposition is TriggerDisposition.BLOCKS_PAPER), None)
    if blocking is not None:
        return Ok(
            ExecutionResolution(
                outcome=RoutingOutcome.BLOCKED,
                routing_reason=(
                    "a blocks-paper control blocks live and paper alike; the decision is "
                    "recorded, and recording is not trading"
                ),
                blocking_control_id=blocking.control_id,
            )
        )

    routes = next(
        (c for c in controls if c.disposition is TriggerDisposition.ROUTES_TO_PAPER), None
    )
    to_paper = (
        resolved_mode is BookMode.PAPER or resolved_seat is SeatState.BENCHED or routes is not None
    )
    if to_paper:
        if resolved_paper is None:
            return unavailable(
                "paper_target",
                "paper routing needs the single resolved paper-routing target for this binding; "
                "no resolvable target makes the paper transition an unavailable-dependency "
                "refusal, and live trading is unaffected",
            )
        if resolved_mode is BookMode.PAPER:
            reason = (
                "Book mode PAPER selects the paired target without changing the binding identity"
            )
        elif resolved_seat is SeatState.BENCHED:
            reason = "a benched seat routes to the paired target without re-minting the binding"
        else:
            control_id = routes.control_id if routes is not None else "routes-to-paper control"
            reason = f"a routes-to-paper control ({control_id}) routes to the paired target"
        return Ok(
            ExecutionResolution(
                outcome=RoutingOutcome.ROUTED_PAPER,
                routing_reason=reason,
                execution_target=resolved_paper,
            )
        )

    return Ok(
        ExecutionResolution(
            outcome=RoutingOutcome.ROUTED_LIVE,
            routing_reason="LIVE mode, active seat, and no routing control — route to live",
            execution_target=live_target,
        )
    )


# --- the CT-24 binding-transition record and the read-time mode fold ---------


@dataclass(frozen=True, slots=True)
class BindingTransitionRecord:
    """One dated, append-only CT-24 binding-transition record (AC1; DEC-0149, DEC-0143).

    A **record change, not a new object**: a flip mints a new binding epoch
    (``book_binding_ref``) over the same Book instance (``book_instance_id`` — never a new
    Book), appended to the stream. ``mode`` is the resulting Book mode; current mode is
    the read-time fold over the stream, never read off a single record. A PAPER-resulting
    transition carries the single resolved ``paper_target_ref`` and the ``paper_epoch_ref``
    in force; a LIVE-resulting transition omits both (present only for PAPER, never null).
    ``operator_signature`` is present where the transition touches real money (a return to
    live or a first live entry) and absent for a clocked mechanical clear.
    """

    book_instance_id: BookInstanceId
    book_binding_ref: Fingerprint
    mode: BookMode
    transition_instant: Instant
    trigger_kind: TriggerKind
    paper_target_ref: ExecutionTarget | None = None
    paper_epoch_ref: Fingerprint | None = None
    operator_signature: str | None = None

    @classmethod
    def try_create(
        cls,
        book_instance_id: object,
        book_binding_ref: object,
        mode: object,
        transition_instant: object,
        trigger_kind: object,
        *,
        paper_target_ref: object = None,
        paper_epoch_ref: object = None,
        operator_signature: object = None,
    ) -> Result[BindingTransitionRecord]:
        """Validate and build a :class:`BindingTransitionRecord`, value-or-refusal.

        Enforces the record types, the ``validate_book_mode`` guard (a seat/binding-state
        word in the mode field is ``invalid input``), and the mode-driven nullability: a
        PAPER transition requires ``paper_target_ref`` and ``paper_epoch_ref``, a LIVE
        transition omits both.
        """
        if not isinstance(book_instance_id, BookInstanceId):
            return invalid(
                "book_instance_id",
                "a transition names the Book instance it applies to — never a new Book",
                given=repr(book_instance_id),
            )
        if not isinstance(book_binding_ref, Fingerprint):
            return invalid(
                "book_binding_ref",
                "a transition cites the AD-29 binding epoch it mints/applies to, by fingerprint",
                given=repr(book_binding_ref),
            )
        resolved_mode = validate_book_mode(mode)
        if is_refusal(resolved_mode):
            return resolved_mode
        book_mode = resolved_mode.value
        if not isinstance(transition_instant, Instant):
            return invalid(
                "transition_instant",
                "a transition is dated with an injected Instant (never a clock read below the "
                "composition root)",
                given=repr(transition_instant),
            )
        if not isinstance(trigger_kind, TriggerKind):
            return invalid(
                "trigger_kind",
                "a transition carries the TriggerKind that occasioned it, with its mandatory "
                "disposition",
                given=repr(trigger_kind),
            )
        target: ExecutionTarget | None = None
        if paper_target_ref is not None:
            if not isinstance(paper_target_ref, ExecutionTarget):
                return invalid(
                    "paper_target_ref",
                    "the paper target is an ExecutionTarget when present",
                    given=repr(paper_target_ref),
                )
            if paper_target_ref.role is AccountRole.LIVE:
                return invalid(
                    "paper_target_ref",
                    "the paper-routing target is a paired demo account, never the live account",
                    given=paper_target_ref.role.value,
                )
            target = paper_target_ref
        epoch: Fingerprint | None = None
        if paper_epoch_ref is not None:
            if not isinstance(paper_epoch_ref, Fingerprint):
                return invalid(
                    "paper_epoch_ref",
                    "the paper epoch is cited by fingerprint when present",
                    given=repr(paper_epoch_ref),
                )
            epoch = paper_epoch_ref
        signature: str | None = None
        if operator_signature is not None:
            signature = clean_str(operator_signature)
            if signature is None:
                return invalid(
                    "operator_signature",
                    "an operator signature is a non-empty token when present",
                    given=repr(operator_signature),
                )
        if book_mode is BookMode.PAPER:
            if target is None:
                return invalid(
                    "paper_target_ref",
                    "a PAPER-resulting transition carries the single resolved paper-routing target",
                )
            if epoch is None:
                return invalid(
                    "paper_epoch_ref",
                    "a PAPER-resulting transition carries the paper epoch in force",
                )
        else:
            if target is not None:
                return invalid(
                    "paper_target_ref",
                    "a LIVE-resulting transition omits the paper target (present only for PAPER)",
                )
            if epoch is not None:
                return invalid(
                    "paper_epoch_ref",
                    "a LIVE-resulting transition omits the paper epoch (present only for PAPER)",
                )
        return Ok(
            cls(
                book_instance_id=book_instance_id,
                book_binding_ref=book_binding_ref,
                mode=book_mode,
                transition_instant=transition_instant,
                trigger_kind=trigger_kind,
                paper_target_ref=target,
                paper_epoch_ref=epoch,
                operator_signature=signature,
            )
        )

    @property
    def disposition(self) -> TriggerDisposition:
        """The occasioning trigger kind's mandatory disposition (a read, not a field)."""
        return self.trigger_kind.disposition

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — optional keys only when present."""
        content: dict[str, object] = {
            "class": "binding-transition-record",
            "book_instance_id": self.book_instance_id.value,
            "book_binding_ref": self.book_binding_ref.value,
            "mode": self.mode.value,
            "transition_instant": self.transition_instant.fp1_identity(),
            "trigger_kind": self.trigger_kind.fp1_identity(),
            "format_version": _PAPER_FORMAT_VERSION,
        }
        if self.paper_target_ref is not None:
            content["paper_target_ref"] = self.paper_target_ref.fp1_identity()
        if self.paper_epoch_ref is not None:
            content["paper_epoch_ref"] = self.paper_epoch_ref.value
        if self.operator_signature is not None:
            content["operator_signature"] = self.operator_signature
        return content

    def fingerprint(self) -> Result[Fingerprint]:
        """The transition record's ``fp1`` over its full canonical content."""
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class ModeFoldResult:
    """The result of the read-time mode fold — never a refusal (AC1; DEC-0149, DEC-0150).

    ``mode`` is the current Book mode; ``fail_closed`` is ``True`` when the fold could not
    resolve cleanly and returned the most-restrictive :class:`BookMode.PAPER` (no
    transition record, or an equal-instant tie with differing modes), with
    ``data_quality_reason`` naming why so the composition root journals ``data quality``
    and alarms. The fold **never refuses on the trading path**.
    """

    mode: BookMode
    fail_closed: bool
    data_quality_reason: str | None = None


class BindingTransitionStream:
    """An append-only CT-24 transition stream with the read-time mode fold (DEC-0149).

    A pure reference structure — **not** the platform's store; the governed transition
    records live in ``qmf-registry`` and reach it only through the composition root
    (DEC-0158). Transitions are grouped by Book instance (never a new Book across a flip),
    and :meth:`current_mode` folds one Book's stream at read time — current mode is never a
    stored mutable field.
    """

    def __init__(self) -> None:
        self._by_book: dict[str, list[BindingTransitionRecord]] = {}
        self._by_fingerprint: dict[str, BindingTransitionRecord] = {}
        self._order: list[Fingerprint] = []

    def mint(self, record: object) -> Result[Fingerprint]:
        """Append a transition record, refusing an equal-fingerprint re-mint.

        Returns the record's fingerprint. The stream is append-only, so a record
        fingerprinting equal to an existing one is ``invalid input``, never a silent
        idempotent accept.
        """
        if not isinstance(record, BindingTransitionRecord):
            return invalid(
                "record", "the stream mints a BindingTransitionRecord", given=repr(record)
            )
        fp = record.fingerprint()
        if is_refusal(fp):
            return fp
        fp_value = fp.value.value
        if fp_value in self._by_fingerprint:
            return invalid(
                "record",
                "a transition record fingerprinting equal to an existing one is refused; the "
                "stream is append-only, never a silent idempotent accept",
                transition_fingerprint=fp_value,
            )
        self._by_fingerprint[fp_value] = record
        self._by_book.setdefault(record.book_instance_id.value, []).append(record)
        self._order.append(fp.value)
        return Ok(fp.value)

    def transitions_for(self, book_instance_id: object) -> tuple[BindingTransitionRecord, ...]:
        """Every transition minted for one Book instance, in mint order (append-only)."""
        if not isinstance(book_instance_id, BookInstanceId):
            return ()
        return tuple(self._by_book.get(book_instance_id.value, ()))

    def current_mode(self, book_instance_id: object, *, as_of: object = None) -> ModeFoldResult:
        """The read-time mode fold over one Book's transition stream (AC1; DEC-0149).

        Under AD-36's fold contract: the ordering key is ``transition_instant``, the
        latest wins; ``as_of`` (an :class:`~qmf.core.Instant`, optional) is the
        knowledge-time bound — only transitions at or before it count; the declared
        equal-instant disposition on differing modes is the most-restrictive
        :class:`BookMode.PAPER`. The fold **never refuses**: an empty considered set (no
        record establishes a mode — a Book is never live without one) and a bad key or
        bound both fail closed to ``PAPER``, flagging ``fail_closed`` and a
        ``data_quality_reason`` for the caller to journal and alarm.
        """
        if not isinstance(book_instance_id, BookInstanceId):
            return ModeFoldResult(
                mode=BookMode.PAPER,
                fail_closed=True,
                data_quality_reason=(
                    "the mode fold received a non-BookInstanceId key; fail-closed to the "
                    "most-restrictive PAPER"
                ),
            )
        bound: int | None = None
        if as_of is not None:
            if not isinstance(as_of, Instant):
                return ModeFoldResult(
                    mode=BookMode.PAPER,
                    fail_closed=True,
                    data_quality_reason=(
                        "the mode fold's knowledge-time bound must be an Instant; fail-closed "
                        "to PAPER"
                    ),
                )
            bound = as_of.value_ns
        records = self._by_book.get(book_instance_id.value, [])
        considered = [r for r in records if bound is None or r.transition_instant.value_ns <= bound]
        if not considered:
            return ModeFoldResult(
                mode=BookMode.PAPER,
                fail_closed=True,
                data_quality_reason=(
                    "no transition record establishes a mode for this Book at the knowledge-time "
                    "bound; a Book is never live without a record — fail-closed to the "
                    "most-restrictive PAPER"
                ),
            )
        latest_instant = max(r.transition_instant.value_ns for r in considered)
        latest_modes = {
            r.mode for r in considered if r.transition_instant.value_ns == latest_instant
        }
        if len(latest_modes) == 1:
            return ModeFoldResult(mode=next(iter(latest_modes)), fail_closed=False)
        return ModeFoldResult(
            mode=BookMode.PAPER,
            fail_closed=True,
            data_quality_reason=(
                "two transitions share the latest instant with differing modes; the declared "
                "equal-instant disposition is the most-restrictive PAPER — journal data quality "
                "and alarm"
            ),
        )


# --- the single active paper-routing target per binding ----------------------


@dataclass(frozen=True, slots=True)
class PaperTargetRecord:
    """One dated paper-routing target for a binding, re-pointable by superseding (AC3).

    Points a live binding at exactly one paired demo target. A re-point mints a new record
    that supersedes the current one (:class:`PaperTargetLog`), because two possible
    destinations is how an order fires twice. ``supersedes`` is ``None`` for the first
    record on a binding.
    """

    binding_ref: Fingerprint
    paper_target: ExecutionTarget
    dated_at: Instant
    supersedes: Fingerprint | None = None

    @classmethod
    def try_create(
        cls,
        binding_ref: object,
        paper_target: object,
        dated_at: object,
        *,
        supersedes: object = None,
    ) -> Result[PaperTargetRecord]:
        """Validate and build a :class:`PaperTargetRecord`, value-or-refusal."""
        if not isinstance(binding_ref, Fingerprint):
            return invalid(
                "binding_ref",
                "a paper-target record cites the live binding epoch by fingerprint",
                given=repr(binding_ref),
            )
        if not isinstance(paper_target, ExecutionTarget):
            return invalid(
                "paper_target",
                "a paper-target record carries an ExecutionTarget",
                given=repr(paper_target),
            )
        if paper_target.role is AccountRole.LIVE:
            return invalid(
                "paper_target",
                "the paper-routing target is a paired demo account, never the live account",
                given=paper_target.role.value,
            )
        if not isinstance(dated_at, Instant):
            return invalid(
                "dated_at",
                "a paper-target record is dated with an injected Instant",
                given=repr(dated_at),
            )
        superseded: Fingerprint | None = None
        if supersedes is not None:
            if not isinstance(supersedes, Fingerprint):
                return invalid(
                    "supersedes",
                    "a superseding paper-target record names the prior record by fingerprint",
                    given=repr(supersedes),
                )
            superseded = supersedes
        return Ok(
            cls(
                binding_ref=binding_ref,
                paper_target=paper_target,
                dated_at=dated_at,
                supersedes=superseded,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the paper-target record."""
        content: dict[str, object] = {
            "class": "paper-target-record",
            "binding_ref": self.binding_ref.value,
            "paper_target": self.paper_target.fp1_identity(),
            "dated_at": self.dated_at.fp1_identity(),
            "format_version": _PAPER_FORMAT_VERSION,
        }
        if self.supersedes is not None:
            content["supersedes"] = self.supersedes.value
        return content

    def fingerprint(self) -> Result[Fingerprint]:
        """The paper-target record's ``fp1`` over its full canonical content."""
        return fingerprint(self.fp1_identity())


class PaperTargetLog:
    """An append-only log resolving one active paper-routing target per binding (AC3).

    A pure reference structure (the governed records live in ``qmf-registry`` via the
    composition root, DEC-0158). It enforces **exactly one active target per binding at an
    instant**: the first record for a binding carries no ``supersedes``; a re-point must
    supersede that binding's current active target, and a second record without a
    ``supersedes`` edge is refused (two possible destinations is how an order fires twice).
    """

    def __init__(self) -> None:
        self._records: dict[str, PaperTargetRecord] = {}
        self._active_by_binding: dict[str, str] = {}
        self._superseded: set[str] = set()
        self._order: list[Fingerprint] = []

    def mint(self, record: object) -> Result[Fingerprint]:
        """Append a paper-target record, enforcing one-active-target-per-binding.

        Returns the record's fingerprint. An equal-fingerprint re-mint is ``invalid
        input``; a dangling ``supersedes`` is ``unavailable dependency``; a ``supersedes``
        naming another binding's record, an already-superseded record, or not the current
        active target is ``invalid input``; and a second target for a binding without a
        ``supersedes`` edge is ``invalid input``.
        """
        if not isinstance(record, PaperTargetRecord):
            return invalid("record", "the log mints a PaperTargetRecord", given=repr(record))
        fp = record.fingerprint()
        if is_refusal(fp):
            return fp
        fp_value = fp.value.value
        if fp_value in self._records:
            return invalid(
                "record",
                "a paper-target record fingerprinting equal to an existing one is refused; the "
                "log is append-only",
                record_fingerprint=fp_value,
            )
        binding_key = record.binding_ref.value
        active = self._active_by_binding.get(binding_key)
        if record.supersedes is not None:
            prior_value = record.supersedes.value
            prior = self._records.get(prior_value)
            if prior is None:
                return unavailable(
                    "supersedes",
                    "a superseding paper-target record must name an existing prior record; a "
                    "supersedes edge never dangles",
                    given=prior_value,
                )
            if prior.binding_ref.value != binding_key:
                return invalid(
                    "supersedes",
                    "a paper-target record may supersede only the same binding's prior target",
                    binding_ref=binding_key,
                    prior_binding_ref=prior.binding_ref.value,
                )
            if prior_value in self._superseded:
                return invalid(
                    "supersedes",
                    "the named prior paper-target record is already superseded; the log is "
                    "append-only and a record is superseded at most once",
                    given=prior_value,
                )
            if active != prior_value:
                return invalid(
                    "supersedes",
                    "a re-point must supersede the binding's current active paper target",
                    given=prior_value,
                    current=active,
                )
        elif active is not None:
            return invalid(
                "record",
                "one active paper-routing target exists per binding at an instant; re-pointing "
                "mints a superseding dated record (two possible destinations is how an order "
                "fires twice)",
                binding_ref=binding_key,
                current=active,
            )
        self._records[fp_value] = record
        self._order.append(fp.value)
        if record.supersedes is not None:
            self._superseded.add(record.supersedes.value)
        self._active_by_binding[binding_key] = fp_value
        return Ok(fp.value)

    def resolve_active_target(self, binding_ref: object) -> Result[ExecutionTarget]:
        """The single active paper target for a binding, or an unavailable-dependency (AC3).

        No resolvable target makes the paper transition an ``unavailable dependency``
        refusal — and live trading is unaffected, since routing rides the execution target,
        not the binding.
        """
        if not isinstance(binding_ref, Fingerprint):
            return invalid(
                "binding_ref",
                "resolving the active paper target reads a binding epoch fingerprint",
                given=repr(binding_ref),
            )
        active = self._active_by_binding.get(binding_ref.value)
        if active is None:
            return unavailable(
                "paper_target",
                "no resolvable paper-routing target for this binding; the paper transition is an "
                "unavailable-dependency refusal, and live trading is unaffected",
                binding_ref=binding_ref.value,
            )
        return Ok(self._records[active].paper_target)


# --- paper epochs: frozen evidence, operator-signed resets -------------------


@dataclass(frozen=True, slots=True)
class PaperEpochRecord:
    """A paper epoch — a starting balance frozen at flip, append-only (AC5; DEC-0149).

    The ``starting_balance`` is a configurable UI-editable default (``registry:paper_
    starting_balance``, no spine value) frozen at flip and never hand-adjusted; it is
    :class:`~qmf.core.Money` in the V1 numeraire (USD). A reset is not an adjustment — it
    mints a **new** operator-signed record whose ``boundary_kind`` is
    :class:`TreasuryBoundaryKind.PAPER_EPOCH_RESET` and whose ``supersedes`` is the lineage
    edge to the epoch it follows; the first epoch at flip carries neither. The running
    balance is never mutated — the record is frozen and the :class:`PaperEpochLog` is
    append-only.
    """

    book_instance_id: BookInstanceId
    binding_ref: Fingerprint
    starting_balance: Money
    operator_signature: str
    dated_at: Instant
    boundary_kind: TreasuryBoundaryKind | None = None
    supersedes: Fingerprint | None = None

    @classmethod
    def try_create(
        cls,
        book_instance_id: object,
        binding_ref: object,
        starting_balance: object,
        operator_signature: object,
        dated_at: object,
        *,
        boundary_kind: object = None,
        supersedes: object = None,
    ) -> Result[PaperEpochRecord]:
        """Validate and build a :class:`PaperEpochRecord`, value-or-refusal.

        The balance is exact :class:`~qmf.core.Money` in USD (a non-USD balance is a
        ``policy rejection``; a non-positive balance is ``invalid input``). A reset carries
        both a ``supersedes`` edge and ``boundary_kind = paper_epoch_reset``; the first
        epoch carries neither — a mismatch is ``invalid input``.
        """
        if not isinstance(book_instance_id, BookInstanceId):
            return invalid(
                "book_instance_id",
                "a paper epoch names the Book instance it belongs to",
                given=repr(book_instance_id),
            )
        if not isinstance(binding_ref, Fingerprint):
            return invalid(
                "binding_ref",
                "a paper epoch cites the binding epoch it is in force for, by fingerprint",
                given=repr(binding_ref),
            )
        if not isinstance(starting_balance, Money):
            return invalid(
                "starting_balance",
                "a paper starting balance is exact Money (a scaled integer, never a binary float)",
                given=repr(starting_balance),
            )
        if starting_balance.currency != V1_NUMERAIRE:
            return policy(
                "starting_balance",
                "the paper starting balance is Money in the V1 numeraire (USD); a non-USD balance "
                "is refused — no rate source is ratified",
                given=starting_balance.currency,
                numeraire=V1_NUMERAIRE,
            )
        if starting_balance.value <= 0:
            return invalid(
                "starting_balance",
                "a paper starting balance is a positive amount sized for data-collection realism",
                given=starting_balance.value,
            )
        signature = clean_str(operator_signature)
        if signature is None:
            return invalid(
                "operator_signature",
                "a paper epoch is operator-signed; the signature is a non-empty token",
                given=repr(operator_signature),
            )
        if not isinstance(dated_at, Instant):
            return invalid(
                "dated_at", "a paper epoch is dated with an injected Instant", given=repr(dated_at)
            )
        resolved_kind: TreasuryBoundaryKind | None = None
        if boundary_kind is not None:
            resolved_kind = coerce_enum(TreasuryBoundaryKind, boundary_kind)
            if resolved_kind is None:
                return invalid(
                    "boundary_kind",
                    "a paper reset's boundary kind is paper_epoch_reset",
                    given=repr(boundary_kind),
                    allowed=[member.value for member in TreasuryBoundaryKind],
                )
        superseded: Fingerprint | None = None
        if supersedes is not None:
            if not isinstance(supersedes, Fingerprint):
                return invalid(
                    "supersedes",
                    "a paper reset names the epoch it follows by fingerprint (its lineage edge)",
                    given=repr(supersedes),
                )
            superseded = supersedes
        if superseded is not None:
            if resolved_kind is not TreasuryBoundaryKind.PAPER_EPOCH_RESET:
                return invalid(
                    "boundary_kind",
                    "a superseding paper epoch is a reset — its boundary kind is paper_epoch_reset",
                    given=repr(boundary_kind),
                )
        elif resolved_kind is not None:
            return invalid(
                "boundary_kind",
                "the first paper epoch at flip carries no supersedes edge and no reset boundary "
                "kind; only a reset is a treasury boundary event",
                given=repr(boundary_kind),
            )
        return Ok(
            cls(
                book_instance_id=book_instance_id,
                binding_ref=binding_ref,
                starting_balance=starting_balance,
                operator_signature=signature,
                dated_at=dated_at,
                boundary_kind=resolved_kind,
                supersedes=superseded,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the paper epoch."""
        content: dict[str, object] = {
            "class": "paper-epoch-record",
            "book_instance_id": self.book_instance_id.value,
            "binding_ref": self.binding_ref.value,
            "starting_balance": self.starting_balance.fp1_identity(),
            "operator_signature": self.operator_signature,
            "dated_at": self.dated_at.fp1_identity(),
            "format_version": _PAPER_FORMAT_VERSION,
        }
        if self.boundary_kind is not None:
            content["boundary_kind"] = self.boundary_kind.value
        if self.supersedes is not None:
            content["supersedes"] = self.supersedes.value
        return content

    def fingerprint(self) -> Result[Fingerprint]:
        """The paper epoch's ``fp1`` over its full canonical content."""
        return fingerprint(self.fp1_identity())


class PaperEpochLog:
    """An append-only log of paper epochs per binding (AC5; DEC-0149, DEC-0158).

    A pure reference structure (governed records live in ``qmf-registry`` via the
    composition root). The running balance is **never mutated**: a reset mints a new record
    superseding the current head, and the log holds every epoch forever. The first epoch
    for a binding carries no ``supersedes``; a reset must supersede that binding's current
    epoch.
    """

    def __init__(self) -> None:
        self._records: dict[str, PaperEpochRecord] = {}
        self._current_by_binding: dict[str, str] = {}
        self._superseded: set[str] = set()
        self._order: list[Fingerprint] = []

    def mint(self, record: object) -> Result[Fingerprint]:
        """Append a paper epoch, enforcing the reset lineage and append-only history.

        Returns the epoch's fingerprint. An equal-fingerprint re-mint is ``invalid
        input``; a dangling ``supersedes`` is ``unavailable dependency``; a ``supersedes``
        naming another binding's epoch, an already-superseded epoch, or not the current
        epoch is ``invalid input``; and a second first-epoch (no ``supersedes``) for a
        binding is ``invalid input`` — a reset must supersede.
        """
        if not isinstance(record, PaperEpochRecord):
            return invalid("record", "the log mints a PaperEpochRecord", given=repr(record))
        fp = record.fingerprint()
        if is_refusal(fp):
            return fp
        fp_value = fp.value.value
        if fp_value in self._records:
            return invalid(
                "record",
                "a paper epoch fingerprinting equal to an existing one is refused; the log is "
                "append-only and the running balance is never mutated",
                epoch_fingerprint=fp_value,
            )
        binding_key = record.binding_ref.value
        current = self._current_by_binding.get(binding_key)
        if record.supersedes is not None:
            prior_value = record.supersedes.value
            prior = self._records.get(prior_value)
            if prior is None:
                return unavailable(
                    "supersedes",
                    "a superseding paper epoch must name an existing prior epoch; a lineage edge "
                    "never dangles",
                    given=prior_value,
                )
            if prior.binding_ref.value != binding_key:
                return invalid(
                    "supersedes",
                    "a paper epoch may supersede only the same binding's prior epoch",
                    binding_ref=binding_key,
                    prior_binding_ref=prior.binding_ref.value,
                )
            if prior_value in self._superseded:
                return invalid(
                    "supersedes",
                    "the named prior epoch is already superseded; a reset supersedes at most once",
                    given=prior_value,
                )
            if current != prior_value:
                return invalid(
                    "supersedes",
                    "a reset must supersede the binding's current paper epoch",
                    given=prior_value,
                    current=current,
                )
        elif current is not None:
            return invalid(
                "record",
                "a binding has one first paper epoch; a fresh balance is a reset that supersedes "
                "the current epoch, never a second first-epoch (the running balance never mutates)",
                binding_ref=binding_key,
                current=current,
            )
        self._records[fp_value] = record
        self._order.append(fp.value)
        if record.supersedes is not None:
            self._superseded.add(record.supersedes.value)
        self._current_by_binding[binding_key] = fp_value
        return Ok(fp.value)

    def current_epoch(self, binding_ref: object) -> Result[PaperEpochRecord]:
        """The current (non-superseded) paper epoch for a binding, or unavailable."""
        if not isinstance(binding_ref, Fingerprint):
            return invalid(
                "binding_ref",
                "reading the current paper epoch reads a binding epoch fingerprint",
                given=repr(binding_ref),
            )
        current = self._current_by_binding.get(binding_ref.value)
        if current is None:
            return unavailable(
                "paper_epoch",
                "no paper epoch has been minted for this binding",
                binding_ref=binding_ref.value,
            )
        return Ok(self._records[current])

    def epochs(self) -> tuple[Fingerprint, ...]:
        """Every minted paper epoch, in mint order (append-only)."""
        return tuple(self._order)


def reset_paper_epoch(
    *,
    book_instance_id: object,
    binding_ref: object,
    prior_epoch_fingerprint: object,
    fresh_balance: object,
    operator_signature: object,
    dated_at: object,
) -> Result[PaperEpochRecord]:
    """Build a ``paper_epoch_reset`` record — a fresh balance with a lineage edge (AC5).

    A reset is not an adjustment: it mints a new operator-signed record carrying a fresh
    declared balance and a ``supersedes`` lineage edge to the epoch it follows. The prior
    epoch's balance is never touched (the log is append-only). Returns the record for the
    caller to :meth:`PaperEpochLog.mint`.
    """
    return PaperEpochRecord.try_create(
        book_instance_id,
        binding_ref,
        fresh_balance,
        operator_signature,
        dated_at,
        boundary_kind=TreasuryBoundaryKind.PAPER_EPOCH_RESET,
        supersedes=prior_epoch_fingerprint,
    )


def reject_paper_pnl_to_treasury(amount: object) -> TypedRefusal:
    """The money-boundary guard: paper P&L never crosses to real money (AC5; DEC-0149).

    Paper money is frozen evidence — paper P&L never becomes Treasury cash, never crosses
    the money boundary, and never buys a seat. Any attempt to move it across is a
    ``policy rejection``, returned (never raised).
    """
    return policy(
        "paper_pnl",
        "paper P&L is frozen evidence: it never becomes Treasury cash, never crosses the money "
        "boundary, and never buys a seat",
        amount=repr(amount),
    )


# --- return to live ----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReturnToLiveOutcome:
    """The authorized shape of a return toward live (AC6; DEC-0149, DEC-0041, DEC-0150).

    ``mechanism`` names the stream the return clears on (a CT-24 transition or a CT-30
    resume); ``operator_signature`` is present where the return touches real money and
    ``None`` for a clocked mechanical clear; ``is_resume`` is ``True`` only for a CT-30
    operator resume. The two streams are distinct, so an automatic clear never masquerades
    as an operator de-escalation and vice versa.
    """

    mechanism: ReturnMechanism
    clearing_cause: ClearingCause
    operator_signature: str | None
    is_resume: bool


def authorize_return_to_live(
    *,
    clearing_cause: object,
    operator_signature: object = None,
    justified_by_paper_performance: object = False,
) -> Result[ReturnToLiveOutcome]:
    """Authorize a return toward live under the AC6 asymmetry (DEC-0149, DEC-0041).

    The rules, in order:

    * **paper performance never authorizes a return** — ``justified_by_paper_performance``
      is a ``policy rejection``;
    * a **clocked mechanical** clear returns **automatically**, minting a CT-24 transition
      and carrying no operator signature — it is never a CT-30 resume (a signature passed
      here is ``invalid input``, since a signed return is a different clearing cause);
    * anything **touching real money** requires an operator signature (AD-18), absent it a
      ``policy rejection``: a **first live entry** is a signed CT-24 transition, and a
      **control stand-down** clears only by an operator CT-30 resume.
    """
    cause = coerce_enum(ClearingCause, clearing_cause)
    if cause is None:
        return invalid(
            "clearing_cause",
            "return-to-live reads a clearing cause (clocked-mechanical|first-live-entry|"
            "control-stand-down)",
            given=repr(clearing_cause),
            allowed=[member.value for member in ClearingCause],
        )
    if not isinstance(justified_by_paper_performance, bool):
        return invalid(
            "justified_by_paper_performance",
            "the paper-performance justification flag is a bool",
            given=repr(justified_by_paper_performance),
        )
    if justified_by_paper_performance:
        return policy(
            "return_to_live",
            "paper performance never authorizes a return to live; only a clocked mechanical clear "
            "(automatic) or an operator signature does",
        )
    signature: str | None = None
    if operator_signature is not None:
        signature = clean_str(operator_signature)
        if signature is None:
            return invalid(
                "operator_signature",
                "an operator signature is a non-empty token when present",
                given=repr(operator_signature),
            )
    if cause is ClearingCause.CLOCKED_MECHANICAL:
        if signature is not None:
            return invalid(
                "operator_signature",
                "a clocked mechanical clear carries no operator signature and mints a CT-24 "
                "transition, never a CT-30 resume; a signed return is a different clearing cause",
                given=repr(operator_signature),
            )
        return Ok(
            ReturnToLiveOutcome(
                mechanism=ReturnMechanism.CT24_TRANSITION,
                clearing_cause=cause,
                operator_signature=None,
                is_resume=False,
            )
        )
    if signature is None:
        return policy(
            "operator_signature",
            "a return touching real money requires an operator signature (AD-18); only a clocked "
            "mechanical clear returns automatically, and paper performance never authorizes it",
        )
    if cause is ClearingCause.FIRST_LIVE_ENTRY:
        return Ok(
            ReturnToLiveOutcome(
                mechanism=ReturnMechanism.CT24_TRANSITION,
                clearing_cause=cause,
                operator_signature=signature,
                is_resume=False,
            )
        )
    return Ok(
        ReturnToLiveOutcome(
            mechanism=ReturnMechanism.CT30_RESUME,
            clearing_cause=cause,
            operator_signature=signature,
            is_resume=True,
        )
    )


def mint_return_to_live_transition(
    *,
    outcome: object,
    book_instance_id: object,
    book_binding_ref: object,
    transition_instant: object,
    trigger_kind: object,
) -> Result[BindingTransitionRecord]:
    """Mint the CT-24 LIVE transition for an authorized return (AC6; DEC-0149, DEC-0150).

    Only a CT-24-mechanism outcome mints a transition: a ``CONTROL_STAND_DOWN`` return
    clears by an operator CT-30 resume on the distinct control-action stream, never a CT-24
    transition, so passing that outcome here is a ``policy rejection``. The resulting LIVE
    transition carries the outcome's operator signature (``None`` for a clocked mechanical
    clear, present for a first live entry).
    """
    if not isinstance(outcome, ReturnToLiveOutcome):
        return invalid(
            "outcome",
            "minting a return-to-live transition reads an authorize_return_to_live outcome",
            given=repr(outcome),
        )
    if outcome.mechanism is not ReturnMechanism.CT24_TRANSITION:
        return policy(
            "outcome",
            "a control stand-down return clears only by an operator CT-30 resume, never a CT-24 "
            "transition; the CT-24 and CT-30 streams are distinct",
            mechanism=outcome.mechanism.value,
        )
    return BindingTransitionRecord.try_create(
        book_instance_id,
        book_binding_ref,
        BookMode.LIVE,
        transition_instant,
        trigger_kind,
        operator_signature=outcome.operator_signature,
    )
