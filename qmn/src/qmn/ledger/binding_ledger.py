"""Per-binding append-only exact-integer virtual ledger (TN-25; Story 26.4).

Each Book binding carries its own virtual-ledger record stream written by the
risk-domain writer ``(machine, risk role, binding)`` in the exact scaled-integer
domain at the account money exponent. Fills attributed through command identity
append here and fold the binding's virtual positions. Venue positions remain a
separate observation-derived fold (DEC-0210; FR-077). No float participates on
the money path.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from qmf.core import (
    Fingerprint,
    Instant,
    Money,
    Ok,
    Quantity,
    Result,
    is_refusal,
)
from qmf.risk.r_faces import RFaces

from qmn.ledger._refuse import clean_token, invalid, policy
from qmn.ledger.virtual import (
    AttributedFill,
    VirtualPosition,
    VirtualPositionStatus,
    guard_no_scale_in,
    mint_virtual_position,
    rebase_partial_entry,
)

__all__ = [
    "LEDGER_RECORD_KINDS",
    "BindingVirtualLedger",
    "FoldFillResult",
    "LedgerRecord",
    "LedgerRecordKind",
    "refuse_float_money",
    "seed_binding_ledger",
    "sum_virtual_quantities",
]


class LedgerRecordKind(StrEnum):
    """Append-only virtual-ledger record kinds (TN-25)."""

    SEED = "seed"
    FILL = "fill"
    REALIZED = "realized"
    BOUNDARY = "boundary"
    MARK = "mark"


LEDGER_RECORD_KINDS: Final[tuple[LedgerRecordKind, ...]] = tuple(LedgerRecordKind)


@dataclass(frozen=True, slots=True)
class LedgerRecord:
    """One append-only exact scaled-integer ledger row."""

    kind: LedgerRecordKind
    binding_epoch: Fingerprint
    sequence: int
    recorded_at: Instant
    cash_delta: Money | None
    position_ref: Fingerprint | None
    command_identity: Fingerprint | None
    money_scale: int
    note: str | None = None

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "binding_epoch": self.binding_epoch.value,
            "kind": self.kind.value,
            "money_scale": self.money_scale,
            "recorded_at": self.recorded_at.fp1_identity(),
            "sequence": self.sequence,
        }
        if self.cash_delta is not None:
            body["cash_delta"] = self.cash_delta.fp1_identity()
        if self.position_ref is not None:
            body["position_ref"] = self.position_ref.value
        if self.command_identity is not None:
            body["command_identity"] = self.command_identity.value
        if self.note is not None:
            body["note"] = self.note
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class FoldFillResult:
    """Outcome of folding one attributed fill into the binding ledger."""

    record: LedgerRecord
    position: VirtualPosition
    created: bool
    scale_in_refused: bool = False


@dataclass
class BindingVirtualLedger:
    """Binding-scoped exact-integer virtual ledger plus virtual-position fold.

    Venue positions are never stored here. Money arithmetic uses :class:`Money`
    scaled integers at the declared account money exponent.
    """

    binding_epoch: Fingerprint
    currency: str
    money_scale: int
    seed: Money
    realized_cash: Money
    _records: list[LedgerRecord] = field(default_factory=list[LedgerRecord])
    _positions: dict[str, VirtualPosition] = field(default_factory=dict[str, VirtualPosition])
    _by_ref: dict[str, VirtualPosition] = field(default_factory=dict[str, VirtualPosition])
    _sequence: int = 0

    @property
    def records(self) -> tuple[LedgerRecord, ...]:
        return tuple(self._records)

    @property
    def open_positions(self) -> tuple[VirtualPosition, ...]:
        return tuple(
            p for p in self._positions.values() if p.status is VirtualPositionStatus.OPEN
        )

    def position_snapshots(self) -> Mapping[str, tuple[str, Mapping[str, object]]]:
        """Public position identity snapshot for boundary-act invariants."""
        return MappingProxyType(
            {
                key: (pos.position_ref.value, MappingProxyType(pos.faces.fp1_identity()))
                for key, pos in self._positions.items()
            }
        )

    def has_open_virtual(self, instrument: object) -> bool:
        token = clean_token(instrument)
        if token is None:
            return False
        pos = self._positions.get(token)
        return pos is not None and pos.status is VirtualPositionStatus.OPEN

    def position_for(self, instrument: object) -> VirtualPosition | None:
        token = clean_token(instrument)
        if token is None:
            return None
        return self._positions.get(token)

    def position_by_ref(self, position_ref: object) -> VirtualPosition | None:
        if not isinstance(position_ref, Fingerprint):
            return None
        return self._by_ref.get(position_ref.value)

    def book_capital(self) -> Money:
        """Period-open capital excluding unrealized P&L — sizing input only."""
        return self.realized_cash

    def virtual_quantity(self, instrument: object) -> Quantity | None:
        pos = self.position_for(instrument)
        if pos is None or pos.status is not VirtualPositionStatus.OPEN:
            return None
        return pos.filled_quantity

    def refuse_entry_if_open(self, instrument: object) -> Result[None]:
        """No-scale-in guard over virtual positions (TN-25 / TN-6)."""
        return guard_no_scale_in(has_open_virtual_position=self.has_open_virtual(instrument))

    def fold_fill(
        self,
        *,
        fill: object,
        bot_id: object,
        admission_identity: object,
        faces: object,
        admitted_quantity: object,
        entry_terminal: object = False,
    ) -> Result[FoldFillResult]:
        """Append one attributed fill and fold the virtual position (Story 26.4).

        Preserves admission identity and frozen R faces. An entry on an
        instrument that already holds an open virtual position refuses as
        no-scale-in. A partial ENTRY at first terminal state re-bases
        ``original_risk_amount`` exactly once.
        """
        if not isinstance(fill, AttributedFill):
            return invalid(
                "fill",
                "the risk-domain writer folds an AttributedFill joined by command identity",
                given=repr(fill),
            )
        if fill.realized_cash is not None:
            refused = refuse_float_money(fill.realized_cash)
            if is_refusal(refused):
                return refused
            if fill.realized_cash.currency != self.currency:
                return invalid(
                    "realized_cash",
                    "fill cash must match the binding ledger currency",
                    ledger=self.currency,
                    fill=fill.realized_cash.currency,
                )
            if fill.realized_cash.scale != self.money_scale:
                return invalid(
                    "realized_cash",
                    "fill cash must use the declared account money scale",
                    ledger_scale=self.money_scale,
                    fill_scale=fill.realized_cash.scale,
                )

        existing = self._positions.get(fill.instrument)
        created = False
        position: VirtualPosition

        if existing is None or existing.status is VirtualPositionStatus.CLOSED:
            if not isinstance(faces, RFaces):
                return invalid("faces", "admission carries frozen RFaces", given=repr(faces))
            minted = mint_virtual_position(
                binding_epoch=self.binding_epoch,
                instrument=fill.instrument,
                bot_id=bot_id,
                admission_identity=admission_identity,
                command_identity=fill.command_identity,
                faces=faces,
                admitted_quantity=admitted_quantity,
                filled_quantity=fill.quantity,
                status=VirtualPositionStatus.OPEN,
            )
            if is_refusal(minted):
                return minted
            position = minted.value
            created = True
        else:
            # Open virtual position on this instrument → no scale-in.
            blocked = guard_no_scale_in(has_open_virtual_position=True)
            if is_refusal(blocked):
                return blocked
            position = existing

        if entry_terminal is True and not position.rebased:
            admitted_frac = position.admitted_quantity.as_fraction()
            filled_frac = fill.quantity.as_fraction()
            if 0 < filled_frac < admitted_frac:
                rebased = rebase_partial_entry(
                    position, filled_quantity=fill.quantity, terminal=True
                )
                if is_refusal(rebased):
                    return rebased
                position = rebased.value[0]

        if fill.realized_cash is not None:
            updated_cash = self.realized_cash.add(fill.realized_cash)
            if is_refusal(updated_cash):
                return updated_cash
            self.realized_cash = updated_cash.value

        self._sequence += 1
        record = LedgerRecord(
            kind=LedgerRecordKind.FILL,
            binding_epoch=self.binding_epoch,
            sequence=self._sequence,
            recorded_at=fill.recorded_at,
            cash_delta=fill.realized_cash,
            position_ref=position.position_ref,
            command_identity=fill.command_identity,
            money_scale=self.money_scale,
        )
        self._records.append(record)
        self._positions[position.instrument] = position
        self._by_ref[position.position_ref.value] = position
        return Ok(
            FoldFillResult(
                record=record,
                position=position,
                created=created,
            )
        )

    def close_position(
        self,
        *,
        instrument: object,
        realized_cash: object,
        recorded_at: object,
        command_identity: object,
    ) -> Result[LedgerRecord]:
        """Close an open virtual position and append a realized cash row."""
        pos = self.position_for(instrument)
        if pos is None or pos.status is not VirtualPositionStatus.OPEN:
            return invalid(
                "instrument",
                "close requires an open virtual position on the instrument",
                given=repr(instrument),
            )
        if not isinstance(realized_cash, Money):
            return invalid(
                "realized_cash",
                "realized cash is Money at the account scale",
                given=repr(realized_cash),
            )
        refused = refuse_float_money(realized_cash)
        if is_refusal(refused):
            return refused
        if realized_cash.currency != self.currency or realized_cash.scale != self.money_scale:
            return invalid(
                "realized_cash",
                "realized cash must match ledger currency and money scale",
            )
        if not isinstance(recorded_at, Instant):
            return invalid("recorded_at", "close carries an Instant", given=repr(recorded_at))
        if not isinstance(command_identity, Fingerprint):
            return invalid(
                "command_identity",
                "close joins by declared command identity",
                given=repr(command_identity),
            )
        updated_cash = self.realized_cash.add(realized_cash)
        if is_refusal(updated_cash):
            return updated_cash
        self.realized_cash = updated_cash.value
        closed = VirtualPosition(
            position_ref=pos.position_ref,
            binding_epoch=pos.binding_epoch,
            instrument=pos.instrument,
            bot_id=pos.bot_id,
            admission_identity=pos.admission_identity,
            command_identity=pos.command_identity,
            faces=pos.faces,
            admission_faces=pos.admission_faces,
            admitted_quantity=pos.admitted_quantity,
            filled_quantity=pos.filled_quantity,
            status=VirtualPositionStatus.CLOSED,
            rebased=pos.rebased,
            admission_plan_edge=pos.admission_plan_edge,
            execution_quality=pos.execution_quality,
        )
        self._positions[closed.instrument] = closed
        self._by_ref[closed.position_ref.value] = closed
        self._sequence += 1
        record = LedgerRecord(
            kind=LedgerRecordKind.REALIZED,
            binding_epoch=self.binding_epoch,
            sequence=self._sequence,
            recorded_at=recorded_at,
            cash_delta=realized_cash,
            position_ref=closed.position_ref,
            command_identity=command_identity,
            money_scale=self.money_scale,
        )
        self._records.append(record)
        return Ok(record)

    def append_boundary(
        self,
        *,
        cash_delta: object,
        recorded_at: object,
        note: object,
    ) -> Result[LedgerRecord]:
        """Append a treasury-boundary cash row — never touches positions."""
        if not isinstance(cash_delta, Money):
            return invalid("cash_delta", "boundary cash is Money", given=repr(cash_delta))
        refused = refuse_float_money(cash_delta)
        if is_refusal(refused):
            return refused
        if cash_delta.currency != self.currency or cash_delta.scale != self.money_scale:
            return invalid(
                "cash_delta",
                "boundary cash must match ledger currency and money scale",
            )
        if not isinstance(recorded_at, Instant):
            return invalid(
                "recorded_at",
                "boundary act carries an Instant",
                given=repr(recorded_at),
            )
        note_token = clean_token(note)
        if note_token is None:
            return invalid("note", "boundary act names its kind", given=repr(note))
        # Snapshot open positions — boundary must leave them untouched.
        before = {k: v.position_ref.value for k, v in self._positions.items()}
        updated = self.realized_cash.add(cash_delta)
        if is_refusal(updated):
            return updated
        self.realized_cash = updated.value
        after = {k: v.position_ref.value for k, v in self._positions.items()}
        if before != after:
            return policy(
                "positions",
                "a treasury boundary act never touches positions",
            )
        self._sequence += 1
        record = LedgerRecord(
            kind=LedgerRecordKind.BOUNDARY,
            binding_epoch=self.binding_epoch,
            sequence=self._sequence,
            recorded_at=recorded_at,
            cash_delta=cash_delta,
            position_ref=None,
            command_identity=None,
            money_scale=self.money_scale,
            note=note_token,
        )
        self._records.append(record)
        return Ok(record)


def refuse_float_money(value: object) -> Result[None]:
    """Refuse a binary float on the money path (FM-1 / DEC-0225)."""
    if isinstance(value, float):
        return invalid(
            "value",
            "no float on the money path; money is an exact scaled integer with a "
            "declared scale",
            given=repr(value),
        )
    if isinstance(value, Money):
        return Ok(None)
    if isinstance(value, int) and not isinstance(value, bool):
        return Ok(None)
    return Ok(None)


def seed_binding_ledger(
    *,
    binding_epoch: object,
    seed: object,
    recorded_at: object,
    currency: object = "USD",
    money_scale: object | None = None,
) -> Result[BindingVirtualLedger]:
    """Open a binding virtual ledger at an exact scaled-integer seed (TN-25)."""
    if not isinstance(binding_epoch, Fingerprint):
        return invalid(
            "binding_epoch",
            "the virtual ledger is scoped to the CT-28 binding epoch",
            given=repr(binding_epoch),
        )
    if isinstance(seed, float):
        return invalid(
            "seed",
            "no float on the money path; seed is Money at the account money scale",
            given=repr(seed),
        )
    if not isinstance(seed, Money):
        return invalid("seed", "ledger seed is Money", given=repr(seed))
    cur = clean_token(currency)
    if cur is None:
        return invalid("currency", "ledger currency is a non-blank tag", given=repr(currency))
    if seed.currency != cur:
        return invalid(
            "seed",
            "seed currency must match the ledger currency",
            seed=seed.currency,
            ledger=cur,
        )
    scale: int
    if money_scale is None:
        scale = seed.scale
    elif isinstance(money_scale, bool) or not isinstance(money_scale, int) or money_scale < 0:
        return invalid(
            "money_scale",
            "account money scale is a non-negative integer exponent",
            given=repr(money_scale),
        )
    else:
        scale = money_scale
    if seed.scale != scale:
        return invalid(
            "seed",
            "seed must use the declared account money scale",
            seed_scale=seed.scale,
            money_scale=scale,
        )
    if not isinstance(recorded_at, Instant):
        return invalid("recorded_at", "seed carries an Instant", given=repr(recorded_at))
    if seed.as_fraction() < 0:
        return invalid("seed", "ledger seed is non-negative", given=str(seed.as_fraction()))

    seed_record = LedgerRecord(
        kind=LedgerRecordKind.SEED,
        binding_epoch=binding_epoch,
        sequence=1,
        recorded_at=recorded_at,
        cash_delta=seed,
        position_ref=None,
        command_identity=None,
        money_scale=scale,
        note="seed",
    )
    return Ok(
        BindingVirtualLedger(
            binding_epoch=binding_epoch,
            currency=cur,
            money_scale=scale,
            seed=seed,
            realized_cash=seed,
            _records=[seed_record],
            _sequence=1,
        )
    )


def sum_virtual_quantities(
    ledgers: Sequence[BindingVirtualLedger],
    *,
    instrument: object,
) -> Result[Quantity | None]:
    """Sum open virtual quantities for one instrument across bindings."""
    inst = clean_token(instrument)
    if inst is None:
        return invalid("instrument", "instrument is a non-blank token", given=repr(instrument))
    total: Quantity | None = None
    for ledger in ledgers:
        qty = ledger.virtual_quantity(inst)
        if qty is None:
            continue
        if total is None:
            total = qty
            continue
        added = total.add(qty)
        if is_refusal(added):
            return added
        total = added.value
    return Ok(total)
