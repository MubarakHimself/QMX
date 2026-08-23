"""Story 10.7 — CT-29 exit records, close reasons, attribution, and the bench fold.

Exactly **one immutable exit record per virtual (Book) position close** — the AD-40
Book-side noun, never the venue position (AD-41; DEC-0155, DEC-0154). The record
carries:

* the frozen ``original_risk_distance`` and ``original_risk_amount`` (admission-frozen
  R faces so ``r_multiple`` recomputes forever without re-reading admission);
* fill references, ``realized_pnl``, and an identity-bearing ``cost_components`` set;
* a **single-sourced** ``realized_r`` — a derived *display* of those frozen fields under
  the pinned formula, never a second governed implementation of the division (AD-23);
* exactly one typed :class:`CloseReason` from the closed-and-addable AD-33 taxonomy,
  with :class:`CloseMechanism` and :class:`CloseOutcome` as **separate** fields so no
  rule is ever written over the mechanism alone, and ``kill_line_flat`` minted apart
  from ``protection_forced_flat``;
* ``closing_authority`` plus the arbitration (or venue-observation) reference, and the
  account-binding role in the result-label parts.

**Whole-trade attribution** credits the Bot that opened the virtual position with the
full realized R regardless of who closed it — no counterfactual, no apportionment —
and reports partition by close reason. The **bench** is a read-time fold over the
exit-record stream bounded by the binding epoch: ``realized_r <= -q`` counts as a
``qualifying_loss_exit``; scratches and partial losses do not count by default; a
breakeven never counts under any ``q`` (own clustering metric). **Recording precedes
interpretation**: a later intent on the same ``(Book, Bot)`` seat refuses
``stale evidence`` unless the closing exit record is persisted and journaled first.
The V1 protective-stop ratchet is **move-to-breakeven only**, risk-non-increasing
against the frozen ``original_risk_distance``; R stays frozen so −1R keeps meaning a
full original loss (CT-23, CT-29).

qmf-risk imports **only** ``qmf-core`` (default-deny, L30/DEC-0120) and sibling
``qmf.risk`` modules; nothing imports ``qmf.risk``. Ratified ``defined-unwired``
surface — no live binding, order, or flatten is authorized here (DEC-0158).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    AccountRole,
    ExactRational,
    Fingerprint,
    Instant,
    Money,
    PriceDelta,
    Result,
    TypedRefusal,
    UnitKind,
    World,
    fingerprint,
    is_refusal,
)
from qmf.core import (
    Ok as _Ok,
)
from qmf.risk._common import (
    clean_str,
    coerce_enum,
    invalid,
    policy,
    stale,
    type_name,
    unavailable,
)
from qmf.risk.door import check_stop_not_widened
from qmf.risk.numeraire import V1_NUMERAIRE
from qmf.risk.r_faces import RFaces

__all__ = [
    "CLOSE_REASON_EVIDENCE_MAPPING",
    "CT29_CONTRACT_FORMAT_VERSION",
    "QUALIFYING_LOSS_THRESHOLD_VARIABLE",
    "VENUE_AUTHORED_CLOSE_REASONS",
    "AttributionReport",
    "BenchDisposition",
    "BenchFoldResult",
    "CloseOutcome",
    "CloseReason",
    "ClosingAuthority",
    "CostComponent",
    "ExitRecord",
    "ExitRecordStream",
    "ExitResultLabel",
    "TradeAttribution",
    "attribute_whole_trade",
    "check_move_to_breakeven_ratchet",
    "check_recording_precedes_interpretation",
    "classify_bench_disposition",
    "fold_bench",
    "mint_exit_record",
    "partition_by_close_reason",
    "realized_r_of",
]

# This module's own contract format version stamped into fp1 identity content; its
# meaning never mutates — an incompatible change mints the next version (L15).
CT29_CONTRACT_FORMAT_VERSION: Final[int] = 1

# Per-family UI-editable bench threshold ``q`` (r-multiple) — name only, no spine value
# (DEC-0155, DEC-0157).
QUALIFYING_LOSS_THRESHOLD_VARIABLE: Final[str] = "qualifying_loss_threshold"


# --- close-reason taxonomy and related closed sets ---------------------------


class CloseReason(StrEnum):
    """The ONE AD-33 close-reason taxonomy — closed-and-addable, never redefined.

    ``kill_line_flat`` is minted apart from ``protection_forced_flat`` because the kill
    line (a per-Book capital floor) and the kill switch (the global authority) are two
    different things (DEC-0147, DEC-0150). The bare word ``stop-out`` is banned —
    venue margin liquidation is :attr:`VENUE_LIQUIDATION` (DEC-0155).
    """

    PROTECTIVE_STOP_FILL = "protective_stop_fill"
    TARGET_FILL = "target_fill"
    PROTECTION_AMENDMENT_FILL = "protection_amendment_fill"
    BOT_INTENT = "bot_intent"
    HOLD_TIME_FORCE_FLAT = "hold_time_force_flat"
    BOUNDARY_FLAT = "boundary_flat"
    WINDOW_FORCED_FLAT = "window_forced_flat"
    PROTECTION_FORCED_FLAT = "protection_forced_flat"
    KILL_LINE_FLAT = "kill_line_flat"
    VENUE_LIQUIDATION = "venue_liquidation"
    VENUE_INITIATED_CLOSE = "venue_initiated_close"
    OPERATOR_CLOSE = "operator_close"


# Venue-authored closes carry a venue observation reference in place of a node
# arbitration record (CT-29 nullability; DEC-0151, DEC-0155).
VENUE_AUTHORED_CLOSE_REASONS: Final[frozenset[CloseReason]] = frozenset(
    {CloseReason.VENUE_LIQUIDATION, CloseReason.VENUE_INITIATED_CLOSE}
)


class ClosingAuthority(StrEnum):
    """Who produced the close — the arbitration winner, or the venue (CT-29; DEC-0150).

    Node authorities are the AD-36 issuing-authority set (``adapter_self`` never closes
    a position). ``venue`` names a venue-authored close.
    """

    OPERATOR = "operator"
    BOOK_POLICY = "book_policy"
    PROTECTION_AUTHORITY = "protection_authority"
    VENUE_DELEGATED = "venue-delegated"
    VENUE = "venue"


class CloseOutcome(StrEnum):
    """The realized sign/magnitude face — separate from mechanism (DEC-0155).

    A protective-stop fill may realize a full loss or a breakeven; a forced flat may
    realize either sign. No rule is written over the mechanism alone. A stamped
    :attr:`BREAKEVEN` never counts toward the bench under any ``q``, even when net
    ``realized_r`` is marginally negative after costs (SCN-0011).
    """

    BREAKEVEN = "breakeven"
    LOSS = "loss"
    GAIN = "gain"


class BenchDisposition(StrEnum):
    """How the bench fold treats one close (CT-29; DEC-0155, DEC-0157)."""

    QUALIFYING_LOSS_EXIT = "qualifying_loss_exit"
    SCRATCH_OR_PARTIAL_LOSS = "scratch-or-partial-loss"
    BREAKEVEN = "breakeven"
    GAIN = "gain"


# RECORDED EVIDENCE for reading pre-QMX artifacts — never a second taxonomy a
# producer emits (DEC-0179).
CLOSE_REASON_EVIDENCE_MAPPING: Final[MappingProxyType[str, str]] = MappingProxyType(
    {
        "SL_HIT": CloseReason.PROTECTIVE_STOP_FILL.value,
        "TP_HIT": CloseReason.TARGET_FILL.value,
        "TRAILING_SL_HIT": CloseReason.PROTECTION_AMENDMENT_FILL.value,
        "MANUAL_CLOSE": CloseReason.OPERATOR_CLOSE.value,
        "MANUAL": CloseReason.OPERATOR_CLOSE.value,
        "KS_FORCED_CLOSE": CloseReason.PROTECTION_FORCED_FLAT.value,
        "KILL_SWITCH_FLATTEN": CloseReason.PROTECTION_FORCED_FLAT.value,
        "TIMEOUT": CloseReason.HOLD_TIME_FORCE_FLAT.value,
        # SESSION_CLOSE / BROKER_CLOSE resolve per trigger — listed as evidence only.
        "SESSION_CLOSE": "window_forced_flat|boundary_flat|hold_time_force_flat",
        "BROKER_CLOSE": "venue_initiated_close|venue_liquidation",
        # HEDGE_CLOSE has no V1 successor.
    }
)


# --- cost components and the result-label parts ------------------------------


@dataclass(frozen=True, slots=True)
class CostComponent:
    """One identity-bearing cost — Money(numeraire) with a named source (DEC-0155).

    ``name`` is the declared component identity (``commission``, ``financing``, …);
    ``source`` names where the charge came from. The set's identity is fixed at
    declaration; an undeclared-but-charged component is a contract-format violation,
    never a silent addition.
    """

    name: str
    amount: Money
    source: str

    @classmethod
    def try_create(cls, name: object, amount: object, source: object) -> Result[CostComponent]:
        """Validate and build a :class:`CostComponent`, value-or-refusal."""
        token = clean_str(name)
        if token is None:
            return invalid(
                "name",
                "a cost component declares a non-blank name (commission, financing, …)",
                given=repr(name),
            )
        if not isinstance(amount, Money):
            return invalid(
                "amount",
                "a cost component is Money(numeraire)",
                given=repr(amount),
            )
        if amount.currency != V1_NUMERAIRE:
            return policy(
                "amount",
                "a cost component is denominated in the numeraire; a non-numeraire amount "
                "needs a ratified rate source and is refused (no silent conversion)",
                given=amount.currency,
                numeraire=V1_NUMERAIRE,
            )
        src = clean_str(source)
        if src is None:
            return invalid(
                "source",
                "a cost component names its source",
                given=repr(source),
            )
        return _Ok(cls(name=token, amount=amount, source=src))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this component."""
        return {
            "class": "cost-component",
            "name": self.name,
            "amount": self.amount.fp1_identity(),
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class ExitResultLabel:
    """AD-12 result-label parts carried on the exit record, including account role.

    A single result may never span account roles (DEC-0155, DEC-0143). The role rides
    here — not the binding tuple — so a paper excursion never re-mints the binding.
    """

    account_role: AccountRole
    world: World

    @classmethod
    def try_create(cls, account_role: object, world: object) -> Result[ExitResultLabel]:
        """Validate and build an :class:`ExitResultLabel`, value-or-refusal."""
        role = coerce_enum(AccountRole, account_role)
        if role is None:
            return invalid(
                "account_role",
                "the exit record carries exactly one account-binding role",
                given=repr(account_role),
                allowed=[member.value for member in AccountRole],
            )
        resolved_world = coerce_enum(World, world)
        if resolved_world is None:
            return invalid(
                "world",
                "the exit record's result-label parts name a world",
                given=repr(world),
                allowed=[member.value for member in World],
            )
        return _Ok(cls(account_role=role, world=resolved_world))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the result-label parts."""
        return {
            "class": "exit-result-label",
            "account_role": self.account_role.value,
            "world": self.world.value,
        }


# --- the exit record ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExitRecord:
    """One immutable CT-29 exit record per virtual (Book) position close (DEC-0155).

    Every field is frozen at write; corrections are annotations, never mutation.
    ``realized_r`` is **not** a stored field — call :meth:`realized_r` (or
    :func:`realized_r_of`) for the single-sourced derived display.
    """

    virtual_position_ref: Fingerprint
    opening_bot_id: str
    original_risk_distance: PriceDelta
    original_risk_amount: Money
    fill_references: tuple[Fingerprint, ...]
    realized_pnl: Money
    cost_components: tuple[CostComponent, ...]
    close_reason: CloseReason
    mechanism: CloseReason
    outcome: CloseOutcome
    closing_authority: ClosingAuthority
    arbitration_record_ref: Fingerprint | None
    venue_observation_ref: Fingerprint | None
    close_reason_mapping_version: int
    result_label: ExitResultLabel
    loss_predicate_format_version: int
    binding_epoch: Fingerprint
    recorded_at: Instant

    def r_faces(self) -> Result[RFaces]:
        """The frozen money-bearing R faces carried on this record."""
        return RFaces.try_create(self.original_risk_distance, self.original_risk_amount)

    def net_realized_pnl(self) -> Result[Money]:
        """Gross ``realized_pnl`` net of exactly the declared ``cost_components`` set."""
        net: Money = self.realized_pnl
        for component in self.cost_components:
            reduced = net.subtract(component.amount)
            if is_refusal(reduced):
                return reduced
            net = reduced.value
        return _Ok(net)

    def realized_r(self) -> Result[ExactRational]:
        """Single-sourced derived display: net result ÷ frozen ``original_risk_amount``.

        Never a second governed implementation of the division — delegates to
        :meth:`RFaces.r_multiple_of` over this record's own frozen fields (DEC-0155).
        """
        return realized_r_of(self)

    def fingerprint(self) -> Result[Fingerprint]:
        """Content fingerprint of this immutable exit record (fp1)."""
        return fingerprint(self.fp1_identity())

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — ``realized_r`` excluded.

        ``realized_r`` is a derived display and never enters identity as a stored
        independent value (DEC-0155, DEC-0158).
        """
        content: dict[str, object] = {
            "class": "exit-record",
            "virtual_position_ref": self.virtual_position_ref.value,
            "opening_bot_id": self.opening_bot_id,
            "original_risk_distance": self.original_risk_distance.fp1_identity(),
            "original_risk_amount": self.original_risk_amount.fp1_identity(),
            "fill_references": [fp.value for fp in self.fill_references],
            "realized_pnl": self.realized_pnl.fp1_identity(),
            "cost_components": [c.fp1_identity() for c in self.cost_components],
            "close_reason": self.close_reason.value,
            "mechanism": self.mechanism.value,
            "outcome": self.outcome.value,
            "closing_authority": self.closing_authority.value,
            "close_reason_mapping_version": self.close_reason_mapping_version,
            "result_label": self.result_label.fp1_identity(),
            "loss_predicate_format_version": self.loss_predicate_format_version,
            "binding_epoch": self.binding_epoch.value,
            "recorded_at": self.recorded_at.fp1_identity(),
            "format_version": CT29_CONTRACT_FORMAT_VERSION,
        }
        if self.arbitration_record_ref is not None:
            content["arbitration_record_ref"] = self.arbitration_record_ref.value
        if self.venue_observation_ref is not None:
            content["venue_observation_ref"] = self.venue_observation_ref.value
        return content


def realized_r_of(record: object) -> Result[ExactRational]:
    """Derive ``realized_r`` from an :class:`ExitRecord`'s frozen fields only.

    Net of exactly the declared ``cost_components``; refuses a stored independent
    value that would disagree with this pinned derivation by never accepting one
    (DEC-0155, DEC-0158).
    """
    if not isinstance(record, ExitRecord):
        return invalid(
            "record",
            "realized_r is derived from an ExitRecord's frozen fields",
            given=type_name(record),
        )
    faces = record.r_faces()
    if is_refusal(faces):
        return faces
    net = record.net_realized_pnl()
    if is_refusal(net):
        return net
    return faces.value.r_multiple_of(net.value)


def mint_exit_record(
    *,
    virtual_position_ref: object,
    opening_bot_id: object,
    original_risk_distance: object,
    original_risk_amount: object,
    fill_references: object,
    realized_pnl: object,
    cost_components: object,
    close_reason: object,
    mechanism: object,
    outcome: object,
    closing_authority: object,
    close_reason_mapping_version: object,
    result_label: object,
    loss_predicate_format_version: object,
    binding_epoch: object,
    recorded_at: object,
    arbitration_record_ref: object = None,
    venue_observation_ref: object = None,
) -> Result[ExitRecord]:
    """Validate and mint exactly one immutable :class:`ExitRecord` (CT-29; DEC-0155).

    Refuses a null or unrecognised close reason, a result spanning more than one
    account role (enforced by a single :class:`ExitResultLabel`), a non-numeraire
    money field, or a venue/node reference mismatch (venue-authored closes carry
    ``venue_observation_ref`` and no node arbitration record; node closes the reverse).
    """
    if not isinstance(virtual_position_ref, Fingerprint):
        return invalid(
            "virtual_position_ref",
            "the exit record closes the virtual (Book) position by fingerprint, never the "
            "venue position",
            given=repr(virtual_position_ref),
        )
    bot = clean_str(opening_bot_id)
    if bot is None:
        return invalid(
            "opening_bot_id",
            "whole-trade attribution credits the Bot that opened the virtual position",
            given=repr(opening_bot_id),
        )
    faces = RFaces.try_create(original_risk_distance, original_risk_amount)
    if is_refusal(faces):
        return faces
    fills = _coerce_fill_references(fill_references)
    if isinstance(fills, TypedRefusal):
        return fills
    if not isinstance(realized_pnl, Money):
        return invalid(
            "realized_pnl",
            "realized_pnl is Money(numeraire) — the gross realized result before costs",
            given=repr(realized_pnl),
        )
    if realized_pnl.currency != V1_NUMERAIRE:
        return policy(
            "realized_pnl",
            "realized_pnl is denominated in the numeraire",
            given=realized_pnl.currency,
            numeraire=V1_NUMERAIRE,
        )
    costs = _coerce_cost_components(cost_components)
    if isinstance(costs, TypedRefusal):
        return costs
    reason = coerce_enum(CloseReason, close_reason)
    if reason is None:
        return invalid(
            "close_reason",
            "close_reason is exactly one member of the AD-33 taxonomy and never null",
            given=repr(close_reason),
            allowed=[member.value for member in CloseReason],
        )
    mech = coerce_enum(CloseReason, mechanism)
    if mech is None:
        return invalid(
            "mechanism",
            "mechanism is the mechanical event that closed the position (AD-33 taxonomy member)",
            given=repr(mechanism),
            allowed=[member.value for member in CloseReason],
        )
    out = coerce_enum(CloseOutcome, outcome)
    if out is None:
        return invalid(
            "outcome",
            "outcome is the realized sign/magnitude face, separate from mechanism",
            given=repr(outcome),
            allowed=[member.value for member in CloseOutcome],
        )
    authority = coerce_enum(ClosingAuthority, closing_authority)
    if authority is None:
        return invalid(
            "closing_authority",
            "closing_authority is the arbitration winner or the venue",
            given=repr(closing_authority),
            allowed=[member.value for member in ClosingAuthority],
        )
    if (
        isinstance(close_reason_mapping_version, bool)
        or not isinstance(close_reason_mapping_version, int)
        or close_reason_mapping_version < 1
    ):
        return invalid(
            "close_reason_mapping_version",
            "the close-reason mapping version is a positive integer ordinal",
            given=repr(close_reason_mapping_version),
        )
    if not isinstance(result_label, ExitResultLabel):
        return invalid(
            "result_label",
            "the exit record carries ExitResultLabel parts including the account-binding role",
            given=repr(result_label),
        )
    if (
        isinstance(loss_predicate_format_version, bool)
        or not isinstance(loss_predicate_format_version, int)
        or loss_predicate_format_version < 1
    ):
        return invalid(
            "loss_predicate_format_version",
            "the Book-declared loss-predicate format version is a positive integer ordinal",
            given=repr(loss_predicate_format_version),
        )
    if not isinstance(binding_epoch, Fingerprint):
        return invalid(
            "binding_epoch",
            "the exit record is bounded by the binding epoch (the binding-record fingerprint)",
            given=repr(binding_epoch),
        )
    if not isinstance(recorded_at, Instant):
        return invalid(
            "recorded_at",
            "the exit record carries the Instant it was minted (injected; no clock below)",
            given=repr(recorded_at),
        )
    arb = _optional_fingerprint("arbitration_record_ref", arbitration_record_ref)
    if isinstance(arb, TypedRefusal):
        return arb
    venue_obs = _optional_fingerprint("venue_observation_ref", venue_observation_ref)
    if isinstance(venue_obs, TypedRefusal):
        return venue_obs
    refs = _check_authority_refs(reason, authority, arb.value, venue_obs.value)
    if isinstance(refs, TypedRefusal):
        return refs
    return _Ok(
        ExitRecord(
            virtual_position_ref=virtual_position_ref,
            opening_bot_id=bot,
            original_risk_distance=faces.value.original_risk_distance,
            original_risk_amount=faces.value.original_risk_amount,
            fill_references=fills.value,
            realized_pnl=realized_pnl,
            cost_components=costs.value,
            close_reason=reason,
            mechanism=mech,
            outcome=out,
            closing_authority=authority,
            arbitration_record_ref=arb.value,
            venue_observation_ref=venue_obs.value,
            close_reason_mapping_version=close_reason_mapping_version,
            result_label=result_label,
            loss_predicate_format_version=loss_predicate_format_version,
            binding_epoch=binding_epoch,
            recorded_at=recorded_at,
        )
    )


def _coerce_fill_references(value: object) -> Result[tuple[Fingerprint, ...]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return invalid(
            "fill_references",
            "fill_references is a sequence of AD-27 fill Fingerprints",
            given=type_name(value),
        )
    items: list[Fingerprint] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, Fingerprint):
            return invalid(
                "fill_references",
                "each fill reference is a Fingerprint",
                index=index,
                given=repr(item),
            )
        items.append(item)
    if not items:
        return invalid(
            "fill_references",
            "a close carries at least one fill reference",
        )
    return _Ok(tuple(items))


def _coerce_cost_components(value: object) -> Result[tuple[CostComponent, ...]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return invalid(
            "cost_components",
            "cost_components is a sequence of CostComponent values (empty only where the "
            "Book declares none)",
            given=type_name(value),
        )
    items: list[CostComponent] = []
    seen: set[str] = set()
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, CostComponent):
            return invalid(
                "cost_components",
                "each cost component is a CostComponent",
                index=index,
                given=repr(item),
            )
        if item.name in seen:
            return invalid(
                "cost_components",
                "cost component names are unique within the declared set",
                name=item.name,
            )
        seen.add(item.name)
        items.append(item)
    return _Ok(tuple(items))


def _optional_fingerprint(field: str, value: object) -> Result[Fingerprint | None]:
    if value is None:
        return _Ok(None)
    if not isinstance(value, Fingerprint):
        return invalid(field, f"{field} is a Fingerprint or absent", given=repr(value))
    return _Ok(value)


def _check_authority_refs(
    reason: CloseReason,
    authority: ClosingAuthority,
    arbitration_record_ref: Fingerprint | None,
    venue_observation_ref: Fingerprint | None,
) -> Result[None]:
    """Venue-authored closes carry venue observation; node closes carry arbitration."""
    if reason in VENUE_AUTHORED_CLOSE_REASONS or authority is ClosingAuthority.VENUE:
        if venue_observation_ref is None:
            return invalid(
                "venue_observation_ref",
                "a venue-authored close carries the venue observation reference in place of "
                "a node arbitration record",
                close_reason=reason.value,
                closing_authority=authority.value,
            )
        if arbitration_record_ref is not None:
            return invalid(
                "arbitration_record_ref",
                "a venue-authored close carries no node arbitration record",
                close_reason=reason.value,
            )
        if authority is not ClosingAuthority.VENUE:
            return invalid(
                "closing_authority",
                "a venue-authored close names closing_authority=venue",
                given=authority.value,
            )
        return _Ok(None)
    if arbitration_record_ref is None:
        return invalid(
            "arbitration_record_ref",
            "a node-originated close carries a reference to the same-tick arbitration record",
            close_reason=reason.value,
            closing_authority=authority.value,
        )
    if venue_observation_ref is not None:
        return invalid(
            "venue_observation_ref",
            "a node-originated close does not carry a venue observation reference in place "
            "of arbitration",
            close_reason=reason.value,
        )
    return _Ok(None)


# --- whole-trade attribution -------------------------------------------------


@dataclass(frozen=True, slots=True)
class TradeAttribution:
    """Full realized R credited to the opening Bot — no apportionment (DEC-0147)."""

    opening_bot_id: str
    realized_r: ExactRational
    close_reason: CloseReason
    virtual_position_ref: Fingerprint


@dataclass(frozen=True, slots=True)
class AttributionReport:
    """One dataset, two ways: by opening Bot and partitioned by close reason."""

    by_bot: MappingProxyType[str, tuple[TradeAttribution, ...]]
    by_close_reason: MappingProxyType[str, tuple[TradeAttribution, ...]]


def attribute_whole_trade(record: object) -> Result[TradeAttribution]:
    """Credit the full realized R to the Bot that opened the virtual position.

    Who closed it — venue stop, Book forced flat, operator — does not matter; there is
    no counterfactual and no apportionment (FR-032, CT-29).
    """
    if not isinstance(record, ExitRecord):
        return invalid(
            "record",
            "whole-trade attribution reads an ExitRecord",
            given=type_name(record),
        )
    realized = record.realized_r()
    if is_refusal(realized):
        return realized
    return _Ok(
        TradeAttribution(
            opening_bot_id=record.opening_bot_id,
            realized_r=realized.value,
            close_reason=record.close_reason,
            virtual_position_ref=record.virtual_position_ref,
        )
    )


def partition_by_close_reason(
    records: object,
) -> Result[MappingProxyType[str, tuple[TradeAttribution, ...]]]:
    """Partition attributions by ``close_reason`` — bot edge and gate cost, one dataset."""
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return invalid(
            "records",
            "partition_by_close_reason folds a sequence of ExitRecord values",
            given=type_name(records),
        )
    buckets: dict[str, list[TradeAttribution]] = {reason.value: [] for reason in CloseReason}
    for index, item in enumerate(cast("Sequence[object]", records)):
        attributed = attribute_whole_trade(item)
        if is_refusal(attributed):
            return invalid(
                "records",
                "every member must be an attributable ExitRecord",
                index=index,
                detail=attributed.context.get("reason"),
            )
        buckets[attributed.value.close_reason.value].append(attributed.value)
    return _Ok(
        MappingProxyType({key: tuple(value) for key, value in buckets.items() if value})
    )


# --- the bench fold ----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BenchFoldResult:
    """Read-time fold over the exit-record stream — never a mutable counter."""

    qualifying_loss_count: int
    breakeven_count: int
    scratch_or_partial_count: int
    gain_count: int
    threshold: int
    threshold_crossed: bool
    dispositions: tuple[BenchDisposition, ...]
    considered: tuple[ExitRecord, ...]


def classify_bench_disposition(
    record: object, *, q: object
) -> Result[BenchDisposition]:
    """Classify one close for the bench predicate (DEC-0155, DEC-0157).

    A stamped :attr:`CloseOutcome.BREAKEVEN` **never** counts under any ``q``. Else the
    predicate is ``realized_r <= -q`` → :attr:`BenchDisposition.QUALIFYING_LOSS_EXIT`;
    a lesser loss is a scratch/partial; a non-negative result is a gain.
    """
    if not isinstance(record, ExitRecord):
        return invalid(
            "record",
            "the bench disposition classifies an ExitRecord",
            given=type_name(record),
        )
    if not isinstance(q, ExactRational) or q.unit_kind is not UnitKind.R_MULTIPLE:
        return invalid(
            "q",
            "q (qualifying_loss_threshold) is an r-multiple ExactRational — a configurable "
            "UI-editable per-family variable, never a spine constant",
            given=repr(q),
        )
    if q.as_fraction() <= 0:
        return invalid(
            "q",
            "q is a positive r-multiple threshold (losses at or beyond -q count)",
            given=str(q.as_fraction()),
        )
    if record.outcome is CloseOutcome.BREAKEVEN:
        return _Ok(BenchDisposition.BREAKEVEN)
    realized = record.realized_r()
    if is_refusal(realized):
        return realized
    ratio = realized.value.as_fraction()
    threshold = -q.as_fraction()
    if ratio <= threshold:
        return _Ok(BenchDisposition.QUALIFYING_LOSS_EXIT)
    if ratio < 0:
        return _Ok(BenchDisposition.SCRATCH_OR_PARTIAL_LOSS)
    return _Ok(BenchDisposition.GAIN)


def fold_bench(
    records: object,
    *,
    binding_epoch: object,
    q: object,
    threshold: object,
    as_of: object = None,
) -> Result[BenchFoldResult]:
    """Read-time qualifying-loss fold over the exit-record stream (CT-29; DEC-0155).

    Bounded by ``binding_epoch`` (a new epoch starts the count at zero unless a signed
    ``carries-ledger`` edge spans it — spanning is the caller's filter). ``as_of`` is the
    optional knowledge-time bound (only records at or before it count). Measurement
    never acts: this publishes a count; the authority to bench belongs to the Book door.
    """
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return invalid(
            "records",
            "the bench fold reads a sequence of ExitRecord values",
            given=type_name(records),
        )
    if not isinstance(binding_epoch, Fingerprint):
        return invalid(
            "binding_epoch",
            "the bench fold is bounded by the binding epoch",
            given=repr(binding_epoch),
        )
    if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 1:
        return invalid(
            "threshold",
            "bench_consecutive_loss_threshold is a positive count — a configurable "
            "UI-editable per-family variable, never a spine constant",
            given=repr(threshold),
        )
    bound_ns: int | None = None
    if as_of is not None:
        if not isinstance(as_of, Instant):
            return invalid(
                "as_of",
                "the knowledge-time bound is an Instant",
                given=repr(as_of),
            )
        bound_ns = as_of.value_ns

    considered: list[ExitRecord] = []
    dispositions: list[BenchDisposition] = []
    qualifying = 0
    breakevens = 0
    scratches = 0
    gains = 0
    for index, item in enumerate(cast("Sequence[object]", records)):
        if not isinstance(item, ExitRecord):
            return invalid(
                "records",
                "every member of the exit-record stream is an ExitRecord",
                index=index,
                given=type_name(item),
            )
        if item.binding_epoch != binding_epoch:
            continue
        if bound_ns is not None and item.recorded_at.value_ns > bound_ns:
            continue
        disposition = classify_bench_disposition(item, q=q)
        if is_refusal(disposition):
            return disposition
        considered.append(item)
        dispositions.append(disposition.value)
        if disposition.value is BenchDisposition.QUALIFYING_LOSS_EXIT:
            qualifying += 1
        elif disposition.value is BenchDisposition.BREAKEVEN:
            breakevens += 1
        elif disposition.value is BenchDisposition.SCRATCH_OR_PARTIAL_LOSS:
            scratches += 1
        else:
            gains += 1
    return _Ok(
        BenchFoldResult(
            qualifying_loss_count=qualifying,
            breakeven_count=breakevens,
            scratch_or_partial_count=scratches,
            gain_count=gains,
            threshold=threshold,
            threshold_crossed=qualifying >= threshold,
            dispositions=tuple(dispositions),
            considered=tuple(considered),
        )
    )


# --- recording precedes interpretation ---------------------------------------


def check_recording_precedes_interpretation(
    *,
    closing_exit_record: object,
    persisted: object,
    journaled: object,
) -> Result[None]:
    """Refuse a later same-seat intent unless the closing exit is persisted and journaled.

    Recording precedes interpretation: a fill closing a virtual position must have its
    CT-29 record persisted and journaled before any later intent on the same
    ``(Book, Bot)`` seat is minted, else that intent refuses ``stale evidence`` so the
    (N+1)th entry never races the Nth exit record (DEC-0155, DEC-0158).
    """
    if closing_exit_record is None:
        return stale(
            "closing_exit_record",
            "a later same-seat intent refuses until the closing exit record is minted, "
            "persisted, and journaled (recording precedes interpretation)",
        )
    if not isinstance(closing_exit_record, ExitRecord):
        return invalid(
            "closing_exit_record",
            "the closing exit is an ExitRecord",
            given=type_name(closing_exit_record),
        )
    if not isinstance(persisted, bool):
        return invalid(
            "persisted",
            "persisted is a bool naming whether the exit record is persisted",
            given=repr(persisted),
        )
    if not isinstance(journaled, bool):
        return invalid(
            "journaled",
            "journaled is a bool naming whether the exit record is journaled",
            given=repr(journaled),
        )
    if not persisted or not journaled:
        return stale(
            "closing_exit_record",
            "a later same-seat intent refuses until the closing exit record is persisted "
            "and journaled (recording precedes interpretation)",
            persisted=persisted,
            journaled=journaled,
            virtual_position_ref=closing_exit_record.virtual_position_ref.value,
        )
    return _Ok(None)


# --- protective-stop / breakeven ratchet -------------------------------------


def check_move_to_breakeven_ratchet(
    *,
    original_risk_distance: object,
    proposed_risk_distance: object,
    breakeven_offset: object = None,
) -> Result[None]:
    """V1 dynamic SL/TP: move-to-breakeven only, risk-non-increasing (CT-29, CT-23).

    The proposed loss-direction distance must be ≤ the frozen ``original_risk_distance``
    (delegates to :func:`~qmf.risk.door.check_stop_not_widened`) and must land at the
    breakeven offset (default zero — stop at entry). R stays frozen on the exit record's
    faces so −1R keeps meaning a full original loss.
    """
    widened = check_stop_not_widened(
        original_risk_distance=original_risk_distance,
        proposed_risk_distance=proposed_risk_distance,
    )
    if is_refusal(widened):
        return widened
    if not isinstance(original_risk_distance, PriceDelta):
        return invalid(
            "original_risk_distance",
            "the frozen original_risk_distance is a PriceDelta",
            given=repr(original_risk_distance),
        )
    if not isinstance(proposed_risk_distance, PriceDelta):
        return invalid(
            "proposed_risk_distance",
            "the proposed stop distance is a PriceDelta",
            given=repr(proposed_risk_distance),
        )
    if breakeven_offset is None:
        # Zero-magnitude offset at the original instrument/scale: stop at entry.
        offset_result = PriceDelta.try_create(
            0, original_risk_distance.instrument, original_risk_distance.scale
        )
        if is_refusal(offset_result):
            return offset_result
        offset = offset_result.value
    elif isinstance(breakeven_offset, PriceDelta):
        if breakeven_offset.instrument != original_risk_distance.instrument:
            return invalid(
                "breakeven_offset",
                "the breakeven offset is a PriceDelta of the same instrument",
                left=repr(original_risk_distance.instrument),
                right=repr(breakeven_offset.instrument),
            )
        if breakeven_offset.as_fraction() < 0:
            return invalid(
                "breakeven_offset",
                "the breakeven offset is a non-negative magnitude",
                given=str(breakeven_offset.as_fraction()),
            )
        offset = breakeven_offset
    else:
        return invalid(
            "breakeven_offset",
            "the breakeven offset is a PriceDelta magnitude (or absent for a zero offset)",
            given=repr(breakeven_offset),
        )
    if proposed_risk_distance.as_fraction() != offset.as_fraction():
        return policy(
            "proposed_risk_distance",
            "V1 dynamic SL/TP is the move-to-breakeven ratchet only; the proposed stop "
            "distance must equal the declared breakeven offset",
            proposed=str(proposed_risk_distance.as_fraction()),
            breakeven_offset=str(offset.as_fraction()),
        )
    return _Ok(None)


# --- append-only exit-record stream ------------------------------------------


@dataclass(frozen=True, slots=True)
class _StreamEntry:
    """Internal stream row: the record plus persistence / journal flags."""

    record: ExitRecord
    record_fingerprint: Fingerprint
    persisted: bool
    journaled: bool


class ExitRecordStream:
    """Append-only exit-record stream with persistence flags (DEC-0155, DEC-0158).

    A pure reference structure — **not** the platform's store; governed records reach
    ``qmf-registry`` / ``qmf-data`` only through the composition root. One virtual
    position may mint **exactly one** exit record; re-minting the same
    ``virtual_position_ref`` is ``invalid input``.
    """

    def __init__(self) -> None:
        self._by_position: dict[str, _StreamEntry] = {}
        self._by_fingerprint: dict[str, _StreamEntry] = {}
        self._order: list[Fingerprint] = []

    def mint(self, record: object) -> Result[Fingerprint]:
        """Append one exit record; refuse a duplicate virtual-position close."""
        if not isinstance(record, ExitRecord):
            return invalid(
                "record",
                "the stream mints an ExitRecord",
                given=type_name(record),
            )
        pos = record.virtual_position_ref.value
        if pos in self._by_position:
            return invalid(
                "virtual_position_ref",
                "exactly one exit record per virtual-position close; a second mint for the "
                "same Book-side position is refused",
                virtual_position_ref=pos,
            )
        fp = record.fingerprint()
        if is_refusal(fp):
            return fp
        fp_value = fp.value.value
        if fp_value in self._by_fingerprint:
            return invalid(
                "record",
                "an exit record fingerprinting equal to an existing one is refused; the "
                "stream is append-only",
                exit_fingerprint=fp_value,
            )
        entry = _StreamEntry(
            record=record,
            record_fingerprint=fp.value,
            persisted=False,
            journaled=False,
        )
        self._by_position[pos] = entry
        self._by_fingerprint[fp_value] = entry
        self._order.append(fp.value)
        return _Ok(fp.value)

    def mark_persisted(self, record_fingerprint: object) -> Result[None]:
        """Mark an exit record persisted (composition-root / registry write ack)."""
        entry = self._require_entry(record_fingerprint)
        if isinstance(entry, TypedRefusal):
            return entry
        self._replace(entry.value, persisted=True, journaled=entry.value.journaled)
        return _Ok(None)

    def mark_journaled(self, record_fingerprint: object) -> Result[None]:
        """Mark an exit record journaled (composition-root / CT-13 write ack)."""
        entry = self._require_entry(record_fingerprint)
        if isinstance(entry, TypedRefusal):
            return entry
        self._replace(entry.value, persisted=entry.value.persisted, journaled=True)
        return _Ok(None)

    def is_recorded(self, virtual_position_ref: object) -> bool:
        """True when the position's exit is both persisted and journaled."""
        if not isinstance(virtual_position_ref, Fingerprint):
            return False
        entry = self._by_position.get(virtual_position_ref.value)
        return entry is not None and entry.persisted and entry.journaled

    def records(
        self, *, binding_epoch: object = None
    ) -> tuple[ExitRecord, ...]:
        """Every minted exit record, optionally filtered to one binding epoch."""
        items = [self._by_fingerprint[fp.value].record for fp in self._order]
        if binding_epoch is None:
            return tuple(items)
        if not isinstance(binding_epoch, Fingerprint):
            return ()
        return tuple(r for r in items if r.binding_epoch == binding_epoch)

    def check_seat_may_mint_intent(
        self, *, closed_virtual_position_ref: object
    ) -> Result[None]:
        """Refuse a later same-seat intent until the closing exit is fully recorded."""
        if closed_virtual_position_ref is None:
            return _Ok(None)
        if not isinstance(closed_virtual_position_ref, Fingerprint):
            return invalid(
                "closed_virtual_position_ref",
                "a closed virtual position is named by Fingerprint",
                given=repr(closed_virtual_position_ref),
            )
        entry = self._by_position.get(closed_virtual_position_ref.value)
        if entry is None:
            return check_recording_precedes_interpretation(
                closing_exit_record=None,
                persisted=False,
                journaled=False,
            )
        return check_recording_precedes_interpretation(
            closing_exit_record=entry.record,
            persisted=entry.persisted,
            journaled=entry.journaled,
        )

    def _require_entry(self, record_fingerprint: object) -> Result[_StreamEntry]:
        if not isinstance(record_fingerprint, Fingerprint):
            return invalid(
                "record_fingerprint",
                "persistence flags key by the exit record's Fingerprint",
                given=repr(record_fingerprint),
            )
        entry = self._by_fingerprint.get(record_fingerprint.value)
        if entry is None:
            return unavailable(
                "record_fingerprint",
                "no exit record with this fingerprint is on the stream",
                record_fingerprint=record_fingerprint.value,
            )
        return _Ok(entry)

    def _replace(self, entry: _StreamEntry, *, persisted: bool, journaled: bool) -> None:
        updated = _StreamEntry(
            record=entry.record,
            record_fingerprint=entry.record_fingerprint,
            persisted=persisted,
            journaled=journaled,
        )
        self._by_fingerprint[entry.record_fingerprint.value] = updated
        self._by_position[entry.record.virtual_position_ref.value] = updated
