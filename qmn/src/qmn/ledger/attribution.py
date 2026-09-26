"""Netting fill-to-virtual-position attribution partition (TN-22/TN-25; CT-28).

Where CT-18 declares ``netting``, attribution declarations across every binding
on one account must be jointly exhaustive and disjoint — a partition proved at
compile / bind time. Absence or overlap is refused. Overlapping Books on a
netted account require the operator's shared-flatten signature. The sum of
virtual positions then reconciles arithmetically to the venue position
(Story 26.4).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import cast

from qmf.core import Ok, Quantity, Result, is_refusal

from qmn.ledger._refuse import clean_token, invalid, policy, unsupported
from qmn.ledger.binding_ledger import BindingVirtualLedger, sum_virtual_quantities
from qmn.ledger.virtual import VenuePosition

__all__ = [
    "AttributionDeclaration",
    "AttributionPartition",
    "PositionModelKind",
    "QuantityReconcileResult",
    "prove_attribution_partition",
    "reconcile_virtual_to_venue_quantity",
]


class PositionModelKind(StrEnum):
    """CT-18 position model read at bind time."""

    NETTING = "netting"
    HEDGING = "hedging"


@dataclass(frozen=True, slots=True)
class AttributionDeclaration:
    """One Book binding's fill-to-virtual-position attribution set."""

    binding_id: str
    instruments: frozenset[str]
    attribution_instruments: frozenset[str] | None
    shared_flatten_signature: str | None = None

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "binding_id": self.binding_id,
            "instruments": sorted(self.instruments),
        }
        if self.attribution_instruments is not None:
            body["attribution_instruments"] = sorted(self.attribution_instruments)
        if self.shared_flatten_signature is not None:
            body["shared_flatten_signature"] = self.shared_flatten_signature
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class AttributionPartition:
    """Proved jointly-exhaustive disjoint attribution cover for one account."""

    account_key: str
    position_model: PositionModelKind
    covered: frozenset[str]
    declarations: tuple[AttributionDeclaration, ...]


@dataclass(frozen=True, slots=True)
class QuantityReconcileResult:
    """Arithmetic quantity residual between virtual sum and venue picture."""

    instrument: str
    virtual_quantity: Quantity
    venue_quantity: Quantity
    residual: Quantity
    reconciled: bool


def prove_attribution_partition(
    *,
    account_key: object,
    position_model: object,
    declarations: object,
) -> Result[AttributionPartition]:
    """Prove attribution declarations are a partition on a netted account.

    Hedging accounts skip the partition requirement (each binding owns its
    venue-visible legs). On netting: absence is a policy rejection; overlap or
    gap is invalid input; overlapping instrument sets across Books require a
    shared-flatten signature on every overlapping Book.
    """
    key = clean_token(account_key)
    if key is None:
        return invalid("account_key", "account key is venue::account", given=repr(account_key))
    model_token = clean_token(position_model)
    if model_token is None:
        return invalid(
            "position_model",
            "position model is netting|hedging",
            given=repr(position_model),
        )
    try:
        model = PositionModelKind(model_token)
    except ValueError:
        return invalid(
            "position_model",
            "position model is netting|hedging",
            given=repr(position_model),
        )
    if not isinstance(declarations, Sequence) or isinstance(declarations, (str, bytes)):
        return invalid(
            "declarations",
            "attribution declarations are a sequence of AttributionDeclaration",
            given=repr(type(declarations).__name__),
        )
    resolved_decls: list[AttributionDeclaration] = []
    for item in cast("Sequence[object]", declarations):
        if not isinstance(item, AttributionDeclaration):
            return invalid(
                "declarations",
                "each item is an AttributionDeclaration",
                given=repr(item),
            )
        resolved_decls.append(item)
    decls = tuple(resolved_decls)

    if model is PositionModelKind.HEDGING:
        covered: set[str] = set()
        for decl in decls:
            covered |= set(decl.instruments)
        return Ok(
            AttributionPartition(
                account_key=key,
                position_model=model,
                covered=frozenset(covered),
                declarations=decls,
            )
        )

    # --- netting -------------------------------------------------------------
    for decl in decls:
        if decl.attribution_instruments is None:
            return policy(
                "attribution_instruments",
                "where CT-18 declares netting, the fill-to-virtual-position "
                "attribution declaration is mandatory; absence is a bind-time "
                "policy rejection",
                account=key,
                binding_id=decl.binding_id,
            )
        if not decl.attribution_instruments:
            return invalid(
                "attribution_instruments",
                "netting attribution declaration must name a non-empty instrument set",
                account=key,
                binding_id=decl.binding_id,
            )
        if not decl.attribution_instruments <= decl.instruments:
            return invalid(
                "attribution_instruments",
                "attribution instruments must be a subset of the Book's declared instruments",
                account=key,
                binding_id=decl.binding_id,
            )

    if len(decls) > 1:
        for i, left in enumerate(decls):
            for right in decls[i + 1 :]:
                overlap = left.instruments & right.instruments
                if overlap and (
                    left.shared_flatten_signature is None
                    or right.shared_flatten_signature is None
                ):
                    return unsupported(
                        "shared_flatten_signature",
                        "a second Book on a netting account whose live bindings "
                        "may trade an overlapping instrument set needs the "
                        "operator's signed shared-flatten limitation; one Book "
                        "per netted account is the V1 default",
                        account=key,
                        overlapping=sorted(overlap),
                    )

    covered_set: set[str] = set()
    for decl in decls:
        attrib = decl.attribution_instruments
        if attrib is None:
            continue
        clash = covered_set & attrib
        if clash:
            return invalid(
                "attribution_instruments",
                "netting attribution declarations on one account must be jointly "
                "disjoint; overlap is an invalid input refusal at compose, never "
                "a trade-time discovery",
                account=key,
                overlapping=sorted(clash),
                binding_id=decl.binding_id,
            )
        covered_set |= attrib

    universe: set[str] = set()
    for decl in decls:
        universe |= decl.instruments
    missing = universe - covered_set
    if missing:
        return invalid(
            "attribution_instruments",
            "netting attribution declarations on one account must be jointly "
            "exhaustive over every instrument the bindings may trade; gaps are "
            "an invalid input refusal at compose",
            account=key,
            missing=sorted(missing),
        )

    return Ok(
        AttributionPartition(
            account_key=key,
            position_model=model,
            covered=frozenset(covered_set),
            declarations=decls,
        )
    )


def reconcile_virtual_to_venue_quantity(
    *,
    ledgers: object,
    venue_position: object,
    instrument: object | None = None,
) -> Result[QuantityReconcileResult]:
    """Prove virtual-quantity sum equals venue quantity (exact integer arithmetic).

    Residual is exact scaled-integer Quantity subtraction — never float.
    """
    if not isinstance(ledgers, Sequence) or isinstance(ledgers, (str, bytes)):
        return invalid(
            "ledgers",
            "ledgers is a sequence of BindingVirtualLedger",
            given=repr(type(ledgers).__name__),
        )
    resolved_ledgers: list[BindingVirtualLedger] = []
    for item in cast("Sequence[object]", ledgers):
        if not isinstance(item, BindingVirtualLedger):
            return invalid(
                "ledgers",
                "each ledger is a BindingVirtualLedger",
                given=repr(item),
            )
        resolved_ledgers.append(item)
    if not isinstance(venue_position, VenuePosition):
        return invalid(
            "venue_position",
            "venue side is a VenuePosition observation",
            given=repr(venue_position),
        )
    inst = venue_position.instrument if instrument is None else clean_token(instrument)
    if not isinstance(inst, str) or inst == "":
        return invalid("instrument", "instrument is a non-blank token", given=repr(instrument))
    if inst != venue_position.instrument:
        return invalid(
            "instrument",
            "reconcile instrument must match the venue position instrument",
            virtual=inst,
            venue=venue_position.instrument,
        )

    summed = sum_virtual_quantities(tuple(resolved_ledgers), instrument=inst)
    if is_refusal(summed):
        return summed
    virtual_qty = summed.value
    if virtual_qty is None:
        zero = Quantity.try_create(0, venue_position.quantity.unit, venue_position.quantity.scale)
        if is_refusal(zero):
            return zero
        virtual_qty = zero.value

    residual_r = venue_position.quantity.subtract(virtual_qty)
    if is_refusal(residual_r):
        return residual_r
    residual = residual_r.value
    return Ok(
        QuantityReconcileResult(
            instrument=inst,
            virtual_quantity=virtual_qty,
            venue_quantity=venue_position.quantity,
            residual=residual,
            reconciled=residual.as_fraction() == 0,
        )
    )
