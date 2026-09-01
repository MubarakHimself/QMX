"""Per-binding kill line over virtual-ledger marked equity (TN-8; Story 26.7).

``registry:kill_line_capital_floor`` IS AD-40 ``loss_floor`` — one registry key,
one value, read by both the sizing ladder and this breach test (DEC-0255). The
node never invents a numeric floor (FTR-07). Equity is the binding's virtual
ledger marked to the latest observed prices of its own virtual positions
(realized plus unrealized). A breach flattens THAT binding only under
``kill_line_flat``, enters binding state ``stood-down``, and routes to the
paired demo target; resume is operator-signature only (FR-057/077; DEC-0150).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Instant, Money, Ok, Result, TypedRefusal, VenueId, is_refusal
from qmf.risk.binding import BindingState
from qmf.risk.control_action import (
    AuthorityKind,
    CommandStreamKey,
    ControlActionKind,
    ControlActionRecord,
    KillLine,
    SubjectScope,
    close_reason_for,
    mint_control_action,
    mint_kill_line_breach,
)
from qmf.risk.exit_record import CloseReason
from qmf.risk.paper import BookMode, ExecutionResolution, ExecutionTarget
from qmf.risk.sizing import reconcile_loss_floor

from qmn.capital._refuse import clean_token, invalid, policy
from qmn.paper.demotion import ProtectiveDemotionKind, route_protective_demotion

__all__ = [
    "KILL_LINE_CAPITAL_FLOOR_REGISTRY_KEY",
    "LOSS_FLOOR_REGISTRY_KEY",
    "OPERATOR_KILL_LINE_RESUME",
    "KillLineBreachPackage",
    "KillLineCadence",
    "KillLineEvaluation",
    "KillLineRestore",
    "apply_kill_line_breach",
    "evaluate_kill_line",
    "marked_virtual_equity",
    "refuse_invented_kill_line_floor",
    "restore_kill_line_stand_down",
]


# Canonical registry key — IS AD-40 loss_floor (DEC-0255). No second name.
KILL_LINE_CAPITAL_FLOOR_REGISTRY_KEY: Final[str] = "kill_line_capital_floor"
LOSS_FLOOR_REGISTRY_KEY: Final[str] = "loss_floor"
OPERATOR_KILL_LINE_RESUME: Final[str] = "operator-signature"


class KillLineCadence(StrEnum):
    """Moments the kill line is evaluated (TN-8 / DEC-0210)."""

    FILL = "fill"
    HELD_INSTRUMENT_PRICE = "held-instrument-price"
    ACCOUNTING_ROLLOVER = "accounting-rollover"


@dataclass(frozen=True, slots=True)
class KillLineEvaluation:
    """Read-time breach test against one binding's marked virtual equity."""

    binding_scope_ref: str
    equity: Money
    kill_line_capital_floor: Money
    breached: bool
    cadence: KillLineCadence
    evaluated_at: Instant
    floor_registry_key: str = KILL_LINE_CAPITAL_FLOOR_REGISTRY_KEY

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "binding_scope_ref": self.binding_scope_ref,
                "breached": self.breached,
                "cadence": self.cadence.value,
                "equity": self.equity.fp1_identity(),
                "evaluated_at": self.evaluated_at.fp1_identity(),
                "floor_registry_key": self.floor_registry_key,
                "kill_line_capital_floor": self.kill_line_capital_floor.fp1_identity(),
            }
        )


@dataclass(frozen=True, slots=True)
class KillLineBreachPackage:
    """Flatten + stand-down + paper route for ONE breached binding."""

    evaluation: KillLineEvaluation
    control_action: ControlActionRecord
    close_reason: CloseReason
    binding_state: BindingState
    routing: ExecutionResolution
    book_mode: BookMode
    other_bindings_unaffected: bool = True

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "binding_state": self.binding_state.value,
                "book_mode": self.book_mode.value,
                "close_reason": self.close_reason.value,
                "control_action": self.control_action.fp1_identity(),
                "evaluation": self.evaluation.as_mapping(),
                "other_bindings_unaffected": self.other_bindings_unaffected,
                "routing": self.routing.fp1_identity(),
            }
        )


@dataclass(frozen=True, slots=True)
class KillLineRestore:
    """Operator-signed clear of a kill-line stand-down."""

    binding_scope_ref: str
    binding_state: BindingState
    cleared_by: str
    resume_action: ControlActionRecord

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "binding_scope_ref": self.binding_scope_ref,
                "binding_state": self.binding_state.value,
                "cleared_by": self.cleared_by,
                "resume_action": self.resume_action.fp1_identity(),
            }
        )


def refuse_invented_kill_line_floor(**extra: object) -> TypedRefusal:
    """FTR-07: the node never invents a kill-line numeric floor."""
    return policy(
        KILL_LINE_CAPITAL_FLOOR_REGISTRY_KEY,
        "kill_line_capital_floor is a Book-declared Money value identical to "
        "AD-40 loss_floor; the node never invents a numeric floor (FTR-07)",
        **extra,
    )


def marked_virtual_equity(
    *,
    realized_cash: object,
    unrealized_marks: object = (),
) -> Result[Money]:
    """Binding virtual-ledger equity = realized cash + unrealized marks (TN-25).

    ``book_capital`` (period-open, excluding unrealized) remains the sizing
    ladder's input only and is never this breach series.
    """
    if not isinstance(realized_cash, Money):
        return invalid(
            "realized_cash",
            "marked equity starts from exact Money realized cash",
            given=repr(realized_cash),
        )
    marks = _coerce_marks(unrealized_marks)
    if isinstance(marks, TypedRefusal):
        return marks

    equity = realized_cash
    for mark in marks:
        added = equity.add(mark)
        if is_refusal(added):
            return added
        equity = added.value
    return Ok(equity)


def evaluate_kill_line(
    *,
    binding_scope_ref: object,
    equity: object,
    kill_line_capital_floor: object,
    evaluated_at: object,
    cadence: object = KillLineCadence.HELD_INSTRUMENT_PRICE,
    loss_floor: object = None,
) -> Result[KillLineEvaluation]:
    """Breach test: equity crosses ``kill_line_capital_floor`` (DEC-0255).

    When ``loss_floor`` is supplied it must equal the kill-line floor — one
    value, one name. A blank/absent floor is refused; no default is invented.
    """
    scope = clean_token(binding_scope_ref)
    if scope is None:
        return invalid(
            "binding_scope_ref",
            "the kill line evaluates one binding scope by a non-empty reference",
            given=repr(binding_scope_ref),
        )
    if kill_line_capital_floor is None:
        return refuse_invented_kill_line_floor(given="None")
    if not isinstance(kill_line_capital_floor, Money):
        return refuse_invented_kill_line_floor(given=repr(kill_line_capital_floor))
    if not isinstance(equity, Money):
        return invalid(
            "equity",
            "the kill line reads marked virtual-ledger equity as Money",
            given=repr(equity),
        )
    if equity.currency != kill_line_capital_floor.currency:
        return invalid(
            "equity",
            "equity and kill_line_capital_floor must share the numeraire currency",
            equity=equity.currency,
            floor=kill_line_capital_floor.currency,
        )
    if not isinstance(evaluated_at, Instant):
        return invalid(
            "evaluated_at",
            "kill-line evaluation carries an Instant",
            given=repr(evaluated_at),
        )
    resolved_cadence = _coerce_cadence(cadence)
    if not isinstance(resolved_cadence, KillLineCadence):
        return resolved_cadence

    floor_alias = kill_line_capital_floor if loss_floor is None else loss_floor
    reconciled = reconcile_loss_floor(floor_alias, kill_line_capital_floor)
    if is_refusal(reconciled):
        return reconciled

    breached = equity.as_fraction() <= kill_line_capital_floor.as_fraction()
    return Ok(
        KillLineEvaluation(
            binding_scope_ref=scope,
            equity=equity,
            kill_line_capital_floor=kill_line_capital_floor,
            breached=breached,
            cadence=resolved_cadence,
            evaluated_at=evaluated_at,
        )
    )


def apply_kill_line_breach(
    evaluation: object,
    *,
    venue_id: object,
    account_id: object,
    live_target: object,
    paper_target: object,
    authority: object = "book-policy",
    rank: object = 1,
    book_mode: object = BookMode.LIVE,
    reason_class: object = "kill_line_breach",
) -> Result[KillLineBreachPackage]:
    """Flatten the breached binding under ``kill_line_flat`` and stand it down.

    Only ``evaluation.binding_scope_ref`` is affected — other bindings of the
    same Book definition are outside this package by construction. Routing
    follows the capital/authority demotion to the paired demo target while the
    Book may stay LIVE.
    """
    if not isinstance(evaluation, KillLineEvaluation):
        return invalid(
            "evaluation",
            "apply_kill_line_breach reads a KillLineEvaluation",
            given=repr(evaluation),
        )
    if not evaluation.breached:
        return policy(
            "evaluation",
            "apply_kill_line_breach requires a breached evaluation",
            breached=False,
        )
    if not isinstance(venue_id, VenueId):
        return invalid("venue_id", "kill-line flatten is scoped to a VenueId", given=repr(venue_id))
    account = clean_token(account_id)
    if account is None:
        return invalid(
            "account_id",
            "kill-line flatten is scoped to a non-empty account id",
            given=repr(account_id),
        )
    stream_r = CommandStreamKey.try_create(venue_id, account)
    if is_refusal(stream_r):
        return stream_r
    kill_line_r = KillLine.try_create(
        authority,
        evaluation.binding_scope_ref,
        stream_r.value,
        reason_class,
    )
    if is_refusal(kill_line_r):
        return kill_line_r
    action_r = mint_kill_line_breach(
        kill_line_r.value,
        rank=rank,
        issued_at=evaluation.evaluated_at,
    )
    if is_refusal(action_r):
        return action_r
    reason_r = close_reason_for(ControlActionKind.FLATTEN, AuthorityKind.BOOK_POLICY)
    if is_refusal(reason_r):
        return reason_r
    if reason_r.value is not CloseReason.KILL_LINE_FLAT:
        return policy(
            "close_reason",
            "kill-line flatten mints kill_line_flat apart from protection_forced_flat",
            given=repr(reason_r.value),
        )
    if not isinstance(live_target, ExecutionTarget) or not isinstance(paper_target, ExecutionTarget):
        return invalid(
            "execution_target",
            "kill-line stand-down routes between typed live and paper ExecutionTargets",
        )
    routing_r = route_protective_demotion(
        kind=ProtectiveDemotionKind.KILL_LINE_STAND_DOWN,
        live_target=live_target,
        paper_target=paper_target,
        book_mode=book_mode,
    )
    if is_refusal(routing_r):
        return routing_r
    resolved_mode = book_mode if isinstance(book_mode, BookMode) else BookMode.LIVE
    if isinstance(book_mode, str):
        try:
            resolved_mode = BookMode(book_mode)
        except ValueError:
            resolved_mode = BookMode.LIVE

    return Ok(
        KillLineBreachPackage(
            evaluation=evaluation,
            control_action=action_r.value,
            close_reason=CloseReason.KILL_LINE_FLAT,
            binding_state=BindingState.STOOD_DOWN,
            routing=routing_r.value,
            book_mode=resolved_mode,
            other_bindings_unaffected=True,
        )
    )


def restore_kill_line_stand_down(
    *,
    binding_scope_ref: object,
    venue_id: object,
    account_id: object,
    issued_at: object,
    operator_signature: object,
    authority: object = "operator",
    rank: object = 0,
) -> Result[KillLineRestore]:
    """Clear a kill-line stand-down — operator signature required (DEC-0150)."""
    scope = clean_token(binding_scope_ref)
    if scope is None:
        return invalid(
            "binding_scope_ref",
            "restore names the stood-down binding scope",
            given=repr(binding_scope_ref),
        )
    signature = clean_token(operator_signature)
    if signature is None:
        return policy(
            "operator_signature",
            "only an operator signature restores a kill-line stand-down; "
            "no clocked clear and no restart leave it",
            given=repr(operator_signature),
            clears_only_by=OPERATOR_KILL_LINE_RESUME,
        )
    if not isinstance(venue_id, VenueId):
        return invalid("venue_id", "resume is scoped to a VenueId", given=repr(venue_id))
    account = clean_token(account_id)
    if account is None:
        return invalid(
            "account_id",
            "resume is scoped to a non-empty account id",
            given=repr(account_id),
        )
    if not isinstance(issued_at, Instant):
        return invalid("issued_at", "resume carries an Instant", given=repr(issued_at))
    stream_r = CommandStreamKey.try_create(venue_id, account)
    if is_refusal(stream_r):
        return stream_r
    resume_r = mint_control_action(
        ControlActionKind.RESUME,
        authority,
        AuthorityKind.OPERATOR,
        SubjectScope.BINDING,
        scope,
        rank,
        "kill_line_restore",
        stream_r.value,
        issued_at,
    )
    if is_refusal(resume_r):
        return resume_r
    return Ok(
        KillLineRestore(
            binding_scope_ref=scope,
            binding_state=BindingState.LIVE,
            cleared_by=OPERATOR_KILL_LINE_RESUME,
            resume_action=resume_r.value,
        )
    )


def _coerce_marks(value: object) -> tuple[Money, ...] | TypedRefusal:
    if isinstance(value, Money):
        return (value,)
    if value is None:
        return ()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        items: list[Money] = []
        for index, item in enumerate(cast("Sequence[object]", value)):
            if not isinstance(item, Money):
                return invalid(
                    "unrealized_marks",
                    "each unrealized mark is exact Money",
                    index=index,
                    given=repr(item),
                )
            items.append(item)
        return tuple(items)
    if isinstance(value, Mapping):
        items = []
        for key, item in cast("Mapping[object, object]", value).items():
            if not isinstance(item, Money):
                return invalid(
                    "unrealized_marks",
                    "each unrealized mark is exact Money",
                    instrument=repr(key),
                    given=repr(item),
                )
            items.append(item)
        return tuple(items)
    return invalid(
        "unrealized_marks",
        "unrealized marks are Money, a sequence of Money, or an instrument map",
        given=repr(value),
    )


def _coerce_cadence(value: object) -> KillLineCadence | TypedRefusal:
    if isinstance(value, KillLineCadence):
        return value
    if isinstance(value, str):
        try:
            return KillLineCadence(value.strip().lower())
        except ValueError:
            return invalid(
                "cadence",
                "kill-line cadence is fill|held-instrument-price|accounting-rollover",
                given=repr(value),
                allowed=[m.value for m in KillLineCadence],
            )
    return invalid(
        "cadence",
        "kill-line cadence is a KillLineCadence",
        given=repr(value),
    )
