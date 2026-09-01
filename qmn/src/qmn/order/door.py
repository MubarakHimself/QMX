"""Book door on the actual order path: freeze R before command mint (Story 26.12).

QL-7 seats emit CT-23 intents. The node calls this door: ``requested_r`` is
Book-resolved, the declared full-loss price is derived at the door, dimensional
and unit checks pass, and the three R faces freeze into an authorized intent
*before* CT-19 ``place_order`` mint. The bot never supplies final size
(QMX-F068; CT-23; DEC-0147, DEC-0154).

After admission, fills, protection amendments, rollover, configuration changes,
and treasury acts leave frozen R unchanged except the one ratified
terminal-partial-entry rebase, which is journaled and idempotent. Later
``realized_r`` is recomputed from persisted original risk (TN-24/25).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    Account,
    ExactRational,
    Fingerprint,
    Instant,
    JournalSink,
    Money,
    Ok,
    PriceDelta,
    Quantity,
    RefusalCategory,
    Result,
    Retryability,
    SinkResult,
    TypedRefusal,
    UnitKind,
    ValueFactor,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.risk.dimensional import LADDER_FORMULAS, check_formula
from qmf.risk.door import (
    CT23_ACTIVE_FORMAT_VERSION,
    AdmittedEntry,
    EntryIntent,
    RiskEvaluationRequest,
    admit_entry_intent,
    check_stop_not_widened,
    parse_inbound_intent,
    reject_inbound_requested_r,
)
from qmf.risk.exit_record import ExitRecord, mint_exit_record, realized_r_of
from qmf.risk.r_faces import RFaces, admit_entry_r_faces, r_to_money

from qmn.ledger.treasury import refuse_boundary_rebase_of_r
from qmn.ledger.virtual import (
    ADMISSION_PLAN_EDGE,
    EXECUTION_QUALITY_SHORT_FILL,
    ExecutionQualityEvidence,
    PartialEntryRebase,
    VirtualPosition,
    mint_virtual_position,
    rebase_partial_entry,
)
from qmn.venue import Command, OrderParameters, OrderType, TimeInForce

__all__ = [
    "BOT_SIZE_FIELDS",
    "PARTIAL_ENTRY_REBASE_JOURNAL_KIND",
    "POSITION_RISK_AMOUNT_FORMULA_ID",
    "AuthorizedIntent",
    "FrozenRPreservation",
    "PartialEntryRebaseJournal",
    "PartialEntryRebaseJournalRecord",
    "PostAdmissionKind",
    "admit_entry_at_book_door",
    "check_door_dimensional_units",
    "journal_terminal_partial_entry_rebase",
    "mint_ct29_from_frozen_r",
    "mint_place_order_from_authorized",
    "mint_virtual_from_authorized",
    "preserve_frozen_r",
    "refuse_command_mint_without_frozen_r",
    "reject_bot_supplied_final_size",
]


BOT_SIZE_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "lots",
        "original_risk_amount",
        "position_risk_amount",
        "quantity",
        "requested_r",
        "size",
        "volume",
    }
)
PARTIAL_ENTRY_REBASE_JOURNAL_KIND: Final[str] = "partial-entry-rebase"
POSITION_RISK_AMOUNT_FORMULA_ID: Final[str] = "FORM-position-risk-amount"
_DOOR_FORMAT_VERSION: Final[int] = 1


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context={"field": field, "reason": reason, **extra},
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context={"field": field, "reason": reason, **extra},
    )


class PostAdmissionKind(StrEnum):
    """Events that must not re-base frozen R except terminal partial entry."""

    FILL = "fill"
    PARTIAL_ENTRY_FILL = "partial-entry-fill"
    PROTECTION_AMENDMENT = "protection-amendment"
    ROLLOVER = "rollover"
    CONFIGURATION_CHANGE = "configuration-change"
    TREASURY_ACT = "treasury-act"


@dataclass(frozen=True, slots=True)
class AuthorizedIntent:
    """Book-admitted entry with R faces frozen before command mint (QMX-F068)."""

    admitted: AdmittedEntry
    faces: RFaces
    requested_r: ExactRational
    admitted_quantity: Quantity
    r_unit_price: ExactRational
    original_risk_amount: Money

    def fp1_identity(self) -> dict[str, object]:
        return {
            "admitted": self.admitted.fp1_identity(),
            "admitted_quantity": self.admitted_quantity.fp1_identity(),
            "class": "authorized-intent",
            "faces": self.faces.fp1_identity(),
            "format_version": _DOOR_FORMAT_VERSION,
            "original_risk_amount": self.original_risk_amount.fp1_identity(),
            "r_unit_price": self.r_unit_price.fp1_identity(),
            "requested_r": self.requested_r.fp1_identity(),
        }


@dataclass(frozen=True, slots=True)
class PartialEntryRebaseJournalRecord:
    """One journaled terminal-partial-entry rebase (idempotent by position_ref)."""

    kind: str
    position_ref: str
    filled_quantity: Quantity
    admission_faces: RFaces
    rebased_faces: RFaces
    journaled_at_ns: int
    lineage: Mapping[str, object]

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "admission_faces": self.admission_faces.fp1_identity(),
                "filled_quantity": self.filled_quantity.fp1_identity(),
                "journaled_at_ns": self.journaled_at_ns,
                "kind": self.kind,
                "lineage": dict(self.lineage),
                "position_ref": self.position_ref,
                "rebased_faces": self.rebased_faces.fp1_identity(),
            }
        )


@dataclass
class PartialEntryRebaseJournal:
    """Append-only index of journaled terminal-partial-entry rebases."""

    sink: JournalSink[Mapping[str, object]] | None = None
    _by_ref: dict[str, PartialEntryRebaseJournalRecord] = field(
        default_factory=dict[str, PartialEntryRebaseJournalRecord]
    )

    @property
    def records(self) -> tuple[PartialEntryRebaseJournalRecord, ...]:
        return tuple(self._by_ref.values())

    def record_for(self, position_ref: object) -> PartialEntryRebaseJournalRecord | None:
        if isinstance(position_ref, Fingerprint):
            return self._by_ref.get(position_ref.value)
        if isinstance(position_ref, str):
            return self._by_ref.get(position_ref)
        return None

    def remember(self, record: PartialEntryRebaseJournalRecord) -> None:
        self._by_ref[record.position_ref] = record


@dataclass(frozen=True, slots=True)
class FrozenRPreservation:
    """Outcome of applying one post-admission event to frozen R."""

    position: VirtualPosition
    kind: PostAdmissionKind
    rebased: bool
    journaled: bool
    faces: RFaces
    rebase: PartialEntryRebase | None = None


def reject_bot_supplied_final_size(fields: object) -> Result[None]:
    """Refuse bot-supplied size — the bot never sizes (CT-23; DEC-0147)."""
    sized = reject_inbound_requested_r(fields)
    if is_refusal(sized):
        return sized
    if not isinstance(fields, Mapping):
        return _invalid(
            "fields",
            "the bot-size guard reads the inbound field mapping",
            given=type(fields).__name__,
        )
    mapping = cast("Mapping[str, object]", fields)
    for key in BOT_SIZE_FIELDS:
        if key in mapping and key != "requested_r":
            return _invalid(
                key,
                "the bot never supplies final size; quantity is Book-derived from "
                "frozen original_risk_amount after requested_r is Book-resolved",
            )
    return Ok(None)


def check_door_dimensional_units(
    *,
    requested_r: object,
    r_unit_price: object,
) -> Result[None]:
    """Refuse unit-kind mismatches on the Book-resolved sizing crossing."""
    if (
        not isinstance(requested_r, ExactRational)
        or requested_r.unit_kind is not UnitKind.R_MULTIPLE
    ):
        return _invalid(
            "book_resolved_requested_r",
            "requested_r is Book-resolved — a dimensionless r-multiple, never a "
            "bot-supplied size or a count",
            given=repr(requested_r),
        )
    if not isinstance(r_unit_price, ExactRational) or r_unit_price.unit_kind is not UnitKind.RATE:
        return _invalid(
            "r_unit_price",
            "a Money<->R crossing names a rate; r_unit_price is rate(money-per-r)",
            given=repr(r_unit_price),
        )
    for spec in LADDER_FORMULAS:
        if spec.formula_id != POSITION_RISK_AMOUNT_FORMULA_ID:
            continue
        checked = check_formula(spec)
        if is_refusal(checked):
            return checked
        return Ok(None)
    return _invalid(
        "dimensional",
        "FORM-position-risk-amount is required on the Book door sizing path",
    )


def _quantity_from_risk_amount(
    *,
    amount: Money,
    distance: PriceDelta,
    value_factor: ValueFactor,
    quantity_unit: object,
    quantity_scale: object,
) -> Result[Quantity]:
    if not isinstance(quantity_unit, str) or quantity_unit.strip() == "":
        return _invalid(
            "quantity_unit",
            "Book-derived quantity names an opaque unit (lot, contract)",
            given=repr(quantity_unit),
        )
    if isinstance(quantity_scale, bool) or not isinstance(quantity_scale, int):
        return _invalid(
            "quantity_scale",
            "Book-derived quantity scale is an integer count of decimal places",
            given=repr(quantity_scale),
        )
    divisor = distance.as_fraction() * value_factor.as_fraction()
    if divisor == 0:
        return _invalid(
            "original_risk_distance",
            "a zero risk distance cannot size a quantity",
        )
    qty_frac = amount.as_fraction() / divisor
    scaled = qty_frac * (10**quantity_scale)
    if scaled.denominator != 1:
        return _invalid(
            "admitted_quantity",
            "Book-derived quantity is not exactly representable at this scale; "
            "refuse rather than round on the money path",
            amount=str(qty_frac),
            scale=quantity_scale,
        )
    return Quantity.try_create(scaled.numerator, quantity_unit.strip(), quantity_scale)


def _as_entry_intent(intent: object, *, ct23_format_version: object) -> Result[EntryIntent]:
    if isinstance(intent, EntryIntent):
        return Ok(intent)
    if isinstance(intent, RiskEvaluationRequest):
        if intent.entry is None:
            return _invalid(
                "intent_family",
                "the Book door freezes R on an entry intent",
            )
        return Ok(intent.entry)
    if isinstance(intent, Mapping):
        mapping = cast("Mapping[str, object]", intent)
        sized = reject_bot_supplied_final_size(mapping)
        if is_refusal(sized):
            return sized
        parsed = parse_inbound_intent(mapping, ct23_format_version=ct23_format_version)
        if is_refusal(parsed):
            return parsed
        if parsed.value.entry is None:
            return _invalid(
                "intent_family",
                "the Book door freezes R on an entry intent",
            )
        return Ok(parsed.value.entry)
    return _invalid(
        "intent",
        "the Book door admits a CT-23 EntryIntent or inbound field mapping",
        given=type(intent).__name__,
    )


def admit_entry_at_book_door(
    *,
    intent: object,
    entry_price: object,
    exit_logic_ref: object,
    module: object,
    book_resolved_requested_r: object,
    r_unit_price: object,
    value_factor: object,
    money_scale: object,
    quantity_unit: object = "lot",
    quantity_scale: object = 0,
    ct23_format_version: object = CT23_ACTIVE_FORMAT_VERSION,
    has_open_virtual_position: object = False,
) -> Result[AuthorizedIntent]:
    """Admit at the Book door and freeze the three R faces before command mint."""
    units = check_door_dimensional_units(
        requested_r=book_resolved_requested_r,
        r_unit_price=r_unit_price,
    )
    if is_refusal(units):
        return units
    entry = _as_entry_intent(intent, ct23_format_version=ct23_format_version)
    if is_refusal(entry):
        return entry
    if not isinstance(has_open_virtual_position, bool):
        return _invalid(
            "has_open_virtual_position",
            "the scale-in guard takes a bool over the open virtual position",
            given=repr(has_open_virtual_position),
        )
    admitted = admit_entry_intent(
        intent=entry.value,
        entry_price=entry_price,
        exit_logic_ref=exit_logic_ref,
        module=module,
        book_resolved_requested_r=book_resolved_requested_r,
        ct23_format_version=ct23_format_version,
        has_open_position=has_open_virtual_position,
    )
    if is_refusal(admitted):
        return admitted
    amount = r_to_money(book_resolved_requested_r, r_unit_price, scale=money_scale)
    if is_refusal(amount):
        return amount
    if not isinstance(value_factor, ValueFactor):
        return _invalid(
            "value_factor",
            "a value-factor is a ValueFactor(instrument, currency) from venue "
            "instrument-metadata; V1 never sizes by margin",
            given=repr(value_factor),
        )
    quantity = _quantity_from_risk_amount(
        amount=amount.value,
        distance=admitted.value.original_risk_distance,
        value_factor=value_factor,
        quantity_unit=quantity_unit,
        quantity_scale=quantity_scale,
    )
    if is_refusal(quantity):
        return quantity
    faces = admit_entry_r_faces(
        entry_price,
        admitted.value.declared_full_loss_price,
        admitted.value.direction,
        quantity.value,
        value_factor,
        money_scale=money_scale,
    )
    if is_refusal(faces):
        return faces
    if faces.value.original_risk_amount.fp1_identity() != amount.value.fp1_identity():
        return _invalid(
            "original_risk_amount",
            "frozen original_risk_amount must equal requested_r x r_unit_price",
        )
    if not isinstance(book_resolved_requested_r, ExactRational):
        return _invalid(
            "book_resolved_requested_r",
            "requested_r is Book-resolved",
            given=repr(book_resolved_requested_r),
        )
    if not isinstance(r_unit_price, ExactRational):
        return _invalid("r_unit_price", "r_unit_price is a named rate", given=repr(r_unit_price))
    return Ok(
        AuthorizedIntent(
            admitted=admitted.value,
            faces=faces.value,
            requested_r=book_resolved_requested_r,
            admitted_quantity=quantity.value,
            r_unit_price=r_unit_price,
            original_risk_amount=amount.value,
        )
    )


def refuse_command_mint_without_frozen_r(authorized: object) -> TypedRefusal:
    """Refuse CT-19 mint when R has not frozen on the Book door."""
    return _invalid(
        "authorized",
        "place_order mints only from a Book-authorized intent with frozen R faces; "
        "the bot never supplies final size",
        given=type(authorized).__name__,
    )


def mint_place_order_from_authorized(
    authorized: object,
    *,
    venue_id: object,
    account: object,
    session_epoch: object,
    ordering_ordinal: object,
    order_type: object = OrderType.MARKET,
    time_in_force: object = TimeInForce.GOOD_TILL_CANCEL,
    bot_quantity: object = None,
) -> Result[Command]:
    """Mint ``place_order`` from frozen R. Bot-supplied quantity is refused."""
    if not isinstance(authorized, AuthorizedIntent):
        return refuse_command_mint_without_frozen_r(authorized)
    if bot_quantity is not None:
        return _invalid(
            "quantity",
            "the bot never supplies final size; place_order quantity is the "
            "Book-derived admitted quantity frozen with the R faces",
            given=repr(bot_quantity),
        )
    if not isinstance(account, Account):
        return _invalid(
            "account",
            "place_order mints against a typed Account",
            given=type(account).__name__,
        )
    params = OrderParameters.try_create(
        order_type,
        time_in_force,
        authorized.admitted_quantity,
        protective_stop_distance=authorized.faces.original_risk_distance,
    )
    if is_refusal(params):
        return params
    return Command.place_order(
        venue_id,
        account,
        session_epoch,
        ordering_ordinal,
        params.value,
    )


def mint_virtual_from_authorized(
    authorized: object,
    *,
    binding_epoch: object,
    bot_id: object,
    command_identity: object,
    filled_quantity: object | None = None,
) -> Result[VirtualPosition]:
    """Mint the virtual position carrying the door-frozen R faces."""
    if not isinstance(authorized, AuthorizedIntent):
        return refuse_command_mint_without_frozen_r(authorized)
    admission_identity = fingerprint(authorized.fp1_identity())
    if is_refusal(admission_identity):
        return admission_identity
    return mint_virtual_position(
        binding_epoch=binding_epoch,
        instrument=authorized.admitted.instrument.symbol,
        bot_id=bot_id,
        admission_identity=admission_identity.value,
        command_identity=command_identity,
        faces=authorized.faces,
        admitted_quantity=authorized.admitted_quantity,
        filled_quantity=filled_quantity,
    )


def _outcome_from_rebased(position: VirtualPosition) -> Result[PartialEntryRebase]:
    evidence = position.execution_quality
    if evidence is None:
        shortfall = position.admitted_quantity.subtract(position.filled_quantity)
        if is_refusal(shortfall):
            return shortfall
        evidence = ExecutionQualityEvidence(
            kind=EXECUTION_QUALITY_SHORT_FILL,
            admitted_quantity=position.admitted_quantity,
            filled_quantity=position.filled_quantity,
            shortfall=shortfall.value,
        )
    lineage = MappingProxyType(
        {
            "admission_faces": position.admission_faces.fp1_identity(),
            "edge": position.admission_plan_edge or ADMISSION_PLAN_EDGE,
            "filled_quantity": position.filled_quantity.fp1_identity(),
            "position_ref": position.position_ref.value,
            "rebased_faces": position.faces.fp1_identity(),
        }
    )
    return Ok(
        PartialEntryRebase(
            admission_faces=position.admission_faces,
            rebased_faces=position.faces,
            admission_plan_edge=position.admission_plan_edge or ADMISSION_PLAN_EDGE,
            execution_quality=evidence,
            lineage_content=lineage,
        )
    )


def _append_rebase_journal(
    journal: PartialEntryRebaseJournal,
    record: PartialEntryRebaseJournalRecord,
) -> Result[PartialEntryRebaseJournalRecord]:
    if journal.sink is not None:
        appended: SinkResult = journal.sink.append(dict(record.as_mapping()))
        if is_refusal(appended):
            return appended
        if not is_ok(appended):
            return cast("Result[PartialEntryRebaseJournalRecord]", appended)
    journal.remember(record)
    return Ok(record)


def journal_terminal_partial_entry_rebase(
    position: object,
    *,
    filled_quantity: object,
    journal: object,
    journaled_at: object,
    terminal: object = True,
) -> Result[tuple[VirtualPosition, PartialEntryRebase, PartialEntryRebaseJournalRecord]]:
    """Journal then apply the one V1 rebase; a repeat of the same fill is a no-op."""
    if not isinstance(position, VirtualPosition):
        return _invalid(
            "position",
            "terminal-partial-entry rebase applies to a VirtualPosition",
            given=repr(position),
        )
    if not isinstance(journal, PartialEntryRebaseJournal):
        return _invalid(
            "journal",
            "the terminal-partial-entry rebase is journaled on a PartialEntryRebaseJournal",
            given=type(journal).__name__,
        )
    if not isinstance(journaled_at, Instant):
        return _invalid(
            "journaled_at",
            "the rebase journal stamp is a wall Instant",
            given=repr(journaled_at),
        )
    if not isinstance(filled_quantity, Quantity):
        return _invalid(
            "filled_quantity",
            "filled quantity is a Quantity",
            given=repr(filled_quantity),
        )

    existing = journal.record_for(position.position_ref)
    if existing is not None:
        if existing.filled_quantity.fp1_identity() != filled_quantity.fp1_identity():
            return _policy(
                "rebased",
                "original_risk_amount re-bases exactly once; a second distinct re-base is refused",
                position_ref=position.position_ref.value,
            )
        if position.rebased:
            outcome = _outcome_from_rebased(position)
            if is_refusal(outcome):
                return outcome
            return Ok((position, outcome.value, existing))
        applied = rebase_partial_entry(position, filled_quantity=filled_quantity, terminal=terminal)
        if is_refusal(applied):
            return applied
        return Ok((applied.value[0], applied.value[1], existing))

    if position.rebased:
        if position.filled_quantity.fp1_identity() != filled_quantity.fp1_identity():
            return _policy(
                "rebased",
                "original_risk_amount re-bases exactly once; a second distinct re-base is refused",
                position_ref=position.position_ref.value,
            )
        outcome = _outcome_from_rebased(position)
        if is_refusal(outcome):
            return outcome
        record = PartialEntryRebaseJournalRecord(
            kind=PARTIAL_ENTRY_REBASE_JOURNAL_KIND,
            position_ref=position.position_ref.value,
            filled_quantity=filled_quantity,
            admission_faces=position.admission_faces,
            rebased_faces=position.faces,
            journaled_at_ns=journaled_at.value_ns,
            lineage=outcome.value.lineage_content,
        )
        stored = _append_rebase_journal(journal, record)
        if is_refusal(stored):
            return stored
        return Ok((position, outcome.value, stored.value))

    preview = rebase_partial_entry(position, filled_quantity=filled_quantity, terminal=terminal)
    if is_refusal(preview):
        return preview
    updated, outcome = preview.value
    record = PartialEntryRebaseJournalRecord(
        kind=PARTIAL_ENTRY_REBASE_JOURNAL_KIND,
        position_ref=updated.position_ref.value,
        filled_quantity=filled_quantity,
        admission_faces=outcome.admission_faces,
        rebased_faces=outcome.rebased_faces,
        journaled_at_ns=journaled_at.value_ns,
        lineage=outcome.lineage_content,
    )
    stored = _append_rebase_journal(journal, record)
    if is_refusal(stored):
        return stored
    return Ok((updated, outcome, stored.value))


def preserve_frozen_r(
    position: object,
    *,
    kind: object,
    filled_quantity: object = None,
    terminal: object = False,
    proposed_stop_distance: object = None,
    journal: object = None,
    journaled_at: object = None,
) -> Result[FrozenRPreservation]:
    """Keep frozen R unchanged except the journaled terminal-partial-entry rebase."""
    if not isinstance(position, VirtualPosition):
        return _invalid(
            "position",
            "frozen-R preservation applies to a VirtualPosition",
            given=repr(position),
        )
    if isinstance(kind, PostAdmissionKind):
        resolved = kind
    elif isinstance(kind, str):
        try:
            resolved = PostAdmissionKind(kind)
        except ValueError:
            return _invalid(
                "kind",
                "post-admission kind is fill|partial-entry-fill|protection-amendment|"
                "rollover|configuration-change|treasury-act",
                given=repr(kind),
            )
    else:
        return _invalid(
            "kind",
            "post-admission kind is a PostAdmissionKind",
            given=repr(kind),
        )

    if resolved is PostAdmissionKind.PARTIAL_ENTRY_FILL:
        if journal is None or journaled_at is None:
            return _invalid(
                "journal",
                "the terminal-partial-entry rebase is journaled and idempotent",
            )
        rebased = journal_terminal_partial_entry_rebase(
            position,
            filled_quantity=filled_quantity,
            journal=journal,
            journaled_at=journaled_at,
            terminal=True if terminal is False else terminal,
        )
        if is_refusal(rebased):
            return rebased
        updated, outcome, _ = rebased.value
        return Ok(
            FrozenRPreservation(
                position=updated,
                kind=resolved,
                rebased=True,
                journaled=True,
                faces=updated.faces,
                rebase=outcome,
            )
        )

    if resolved is PostAdmissionKind.PROTECTION_AMENDMENT:
        widened = check_stop_not_widened(
            original_risk_distance=position.faces.original_risk_distance,
            proposed_risk_distance=proposed_stop_distance,
        )
        if is_refusal(widened):
            return widened
        return Ok(
            FrozenRPreservation(
                position=position,
                kind=resolved,
                rebased=False,
                journaled=False,
                faces=position.faces,
            )
        )

    if resolved in {
        PostAdmissionKind.ROLLOVER,
        PostAdmissionKind.CONFIGURATION_CHANGE,
        PostAdmissionKind.TREASURY_ACT,
    }:
        guarded = refuse_boundary_rebase_of_r(
            faces_before=position.faces,
            faces_after=position.faces,
        )
        if is_refusal(guarded):
            return guarded
        return Ok(
            FrozenRPreservation(
                position=position,
                kind=resolved,
                rebased=False,
                journaled=False,
                faces=position.faces,
            )
        )

    return Ok(
        FrozenRPreservation(
            position=position,
            kind=resolved,
            rebased=False,
            journaled=False,
            faces=position.faces,
        )
    )


def mint_ct29_from_frozen_r(
    position: object,
    *,
    realized_pnl: object,
    fill_references: object,
    cost_components: object,
    close_reason: object,
    mechanism: object,
    outcome: object,
    closing_authority: object,
    close_reason_mapping_version: object,
    result_label: object,
    loss_predicate_format_version: object,
    recorded_at: object,
    arbitration_record_ref: object = None,
    venue_observation_ref: object = None,
) -> Result[ExitRecord]:
    """Mint CT-29 from persisted original risk on the virtual position."""
    if not isinstance(position, VirtualPosition):
        return _invalid(
            "position",
            "CT-29 closes the virtual (Book) position carrying frozen R faces",
            given=repr(position),
        )
    record = mint_exit_record(
        virtual_position_ref=position.position_ref,
        opening_bot_id=position.bot_id,
        original_risk_distance=position.faces.original_risk_distance,
        original_risk_amount=position.faces.original_risk_amount,
        fill_references=fill_references,
        realized_pnl=realized_pnl,
        cost_components=cost_components,
        close_reason=close_reason,
        mechanism=mechanism,
        outcome=outcome,
        closing_authority=closing_authority,
        close_reason_mapping_version=close_reason_mapping_version,
        result_label=result_label,
        loss_predicate_format_version=loss_predicate_format_version,
        binding_epoch=position.binding_epoch,
        recorded_at=recorded_at,
        arbitration_record_ref=arbitration_record_ref,
        venue_observation_ref=venue_observation_ref,
    )
    if is_refusal(record):
        return record
    derived = realized_r_of(record.value)
    if is_refusal(derived):
        return derived
    net = record.value.net_realized_pnl()
    if is_refusal(net):
        return net
    recomputed = position.faces.r_multiple_of(net.value)
    if is_refusal(recomputed):
        return recomputed
    if derived.value.fp1_identity() != recomputed.value.fp1_identity():
        return _invalid(
            "realized_r",
            "realized_r must recompute from persisted original_risk_amount",
        )
    return record
