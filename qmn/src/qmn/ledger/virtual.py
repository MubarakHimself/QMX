"""Exact virtual (Book) positions and the sole V1 partial-entry re-base (TN-25).

A virtual position is a fold over fills joined by declared command identity —
binding-scoped, Bot-attributed, minted at admission, carrying frozen R faces.
Venue positions are a separate observation-derived fold and never enter here
(DEC-0154, DEC-0210; Story 26.4 / FR-077).

V1 admits no scale-in: an entry against an instrument that already holds an open
virtual position is a ``policy rejection``. The sole ruled re-base of
``original_risk_amount`` is exactly once at a partial ENTRY's first terminal
state onto the filled quantity; the admission plan is retained via a lineage
edge and the short fill is execution-quality evidence. The node never tops up
a short fill (TN-24a; DEC-0154).
"""

from __future__ import annotations

from collections.abc import Mapping
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
    fingerprint,
    is_refusal,
)
from qmf.risk.r_faces import RFaces, check_no_scale_in

from qmn.ledger._refuse import clean_token, invalid, policy

__all__ = [
    "ADMISSION_PLAN_EDGE",
    "EXECUTION_QUALITY_SHORT_FILL",
    "POSITION_KIND_VENUE",
    "POSITION_KIND_VIRTUAL",
    "AttributedFill",
    "ExecutionQualityEvidence",
    "PartialEntryRebase",
    "PositionKind",
    "VenuePosition",
    "VenuePositionFold",
    "VirtualPosition",
    "VirtualPositionStatus",
    "fold_venue_observation",
    "guard_no_scale_in",
    "mint_virtual_position",
    "rebase_partial_entry",
    "refuse_top_up_short_fill",
]

ADMISSION_PLAN_EDGE: Final[str] = "admission-plan"
EXECUTION_QUALITY_SHORT_FILL: Final[str] = "short-fill"
POSITION_KIND_VIRTUAL: Final[str] = "virtual"
POSITION_KIND_VENUE: Final[str] = "venue"


class PositionKind(StrEnum):
    """Which position fold a risk record references (DEC-0154; TN-25)."""

    VIRTUAL = "virtual"
    VENUE = "venue"


class VirtualPositionStatus(StrEnum):
    """Lifecycle of one binding-scoped virtual position."""

    OPEN = "open"
    CLOSED = "closed"
    PENDING_ENTRY = "pending-entry"


@dataclass(frozen=True, slots=True)
class AttributedFill:
    """One fill attributed through declared command identity (TN-25)."""

    command_identity: Fingerprint
    venue_native_id: str
    instrument: str
    quantity: Quantity
    realized_cash: Money | None
    recorded_at: Instant

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "command_identity": self.command_identity.value,
            "instrument": self.instrument,
            "quantity": self.quantity.fp1_identity(),
            "recorded_at": self.recorded_at.fp1_identity(),
            "venue_native_id": self.venue_native_id,
        }
        if self.realized_cash is not None:
            body["realized_cash"] = self.realized_cash.fp1_identity()
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class ExecutionQualityEvidence:
    """Evidence that an ENTRY filled short of the admitted plan (TN-24a)."""

    kind: str
    admitted_quantity: Quantity
    filled_quantity: Quantity
    shortfall: Quantity

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "admitted_quantity": self.admitted_quantity.fp1_identity(),
                "filled_quantity": self.filled_quantity.fp1_identity(),
                "kind": self.kind,
                "shortfall": self.shortfall.fp1_identity(),
            }
        )


@dataclass(frozen=True, slots=True)
class PartialEntryRebase:
    """One-time re-base of ``original_risk_amount`` onto filled quantity.

    The admission faces remain the declared plan; a lineage edge records the
    relationship. Distance stays frozen; only the money face re-bases (AD-40).
    """

    admission_faces: RFaces
    rebased_faces: RFaces
    admission_plan_edge: str
    execution_quality: ExecutionQualityEvidence
    lineage_content: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class VirtualPosition:
    """One binding-scoped virtual (Book) position (TN-25; DEC-0154).

    Carries admission identity and frozen R faces. Money faces may re-base
    exactly once under :func:`rebase_partial_entry`; distance never re-bases.
    """

    position_ref: Fingerprint
    binding_epoch: Fingerprint
    instrument: str
    bot_id: str
    admission_identity: Fingerprint
    command_identity: Fingerprint
    faces: RFaces
    admission_faces: RFaces
    admitted_quantity: Quantity
    filled_quantity: Quantity
    status: VirtualPositionStatus
    rebased: bool
    position_kind: PositionKind = PositionKind.VIRTUAL
    admission_plan_edge: str | None = None
    execution_quality: ExecutionQualityEvidence | None = None

    def fp1_identity(self) -> dict[str, object]:
        body: dict[str, object] = {
            "admission_faces": self.admission_faces.fp1_identity(),
            "admission_identity": self.admission_identity.value,
            "admitted_quantity": self.admitted_quantity.fp1_identity(),
            "binding_epoch": self.binding_epoch.value,
            "bot_id": self.bot_id,
            "class": "virtual-position",
            "command_identity": self.command_identity.value,
            "faces": self.faces.fp1_identity(),
            "filled_quantity": self.filled_quantity.fp1_identity(),
            "instrument": self.instrument,
            "position_kind": self.position_kind.value,
            "position_ref": self.position_ref.value,
            "rebased": self.rebased,
            "status": self.status.value,
        }
        if self.admission_plan_edge is not None:
            body["admission_plan_edge"] = self.admission_plan_edge
        if self.execution_quality is not None:
            body["execution_quality"] = dict(self.execution_quality.as_mapping())
        return body


@dataclass(frozen=True, slots=True)
class VenuePosition:
    """Observation-derived venue position under ``netting | hedging`` (TN-25)."""

    account_id: str
    instrument: str
    quantity: Quantity
    position_model: str
    observed_at: Instant
    position_kind: PositionKind = PositionKind.VENUE

    def fp1_identity(self) -> dict[str, object]:
        return {
            "account_id": self.account_id,
            "class": "venue-position",
            "instrument": self.instrument,
            "observed_at": self.observed_at.fp1_identity(),
            "position_kind": self.position_kind.value,
            "position_model": self.position_model,
            "quantity": self.quantity.fp1_identity(),
        }


@dataclass
class VenuePositionFold:
    """Separate observation-derived venue-position fold (never virtual)."""

    _by_key: dict[tuple[str, str], VenuePosition] = field(
        default_factory=dict[tuple[str, str], VenuePosition]
    )

    def get(self, account_id: str, instrument: str) -> VenuePosition | None:
        return self._by_key.get((account_id, instrument))

    def put(self, position: VenuePosition) -> None:
        self._by_key[(position.account_id, position.instrument)] = position

    def all_positions(self) -> tuple[VenuePosition, ...]:
        return tuple(self._by_key.values())


def fold_venue_observation(
    fold: VenuePositionFold,
    *,
    account_id: object,
    instrument: object,
    quantity: object,
    position_model: object,
    observed_at: object,
) -> Result[VenuePosition]:
    """Fold one venue observation into the venue-position fold (TN-25)."""
    acct = clean_token(account_id)
    if acct is None:
        return invalid(
            "account_id",
            "venue position is scoped to an account",
            given=repr(account_id),
        )
    inst = clean_token(instrument)
    if inst is None:
        return invalid(
            "instrument",
            "venue position names an instrument",
            given=repr(instrument),
        )
    model = clean_token(position_model)
    if model is None or model not in {"netting", "hedging"}:
        return invalid(
            "position_model",
            "venue position model is netting|hedging",
            given=repr(position_model),
        )
    if not isinstance(quantity, Quantity):
        return invalid("quantity", "venue quantity is a Quantity", given=repr(quantity))
    if not isinstance(observed_at, Instant):
        return invalid(
            "observed_at",
            "venue observation carries an Instant",
            given=repr(observed_at),
        )
    pos = VenuePosition(
        account_id=acct,
        instrument=inst,
        quantity=quantity,
        position_model=model,
        observed_at=observed_at,
    )
    fold.put(pos)
    return Ok(pos)


def guard_no_scale_in(*, has_open_virtual_position: object) -> Result[None]:
    """Refuse an entry when the binding already holds an open virtual position."""
    return check_no_scale_in(has_open_virtual_position)


def mint_virtual_position(
    *,
    binding_epoch: object,
    instrument: object,
    bot_id: object,
    admission_identity: object,
    command_identity: object,
    faces: object,
    admitted_quantity: object,
    filled_quantity: object | None = None,
    status: object = VirtualPositionStatus.OPEN,
) -> Result[VirtualPosition]:
    """Mint a binding-scoped virtual position carrying frozen R faces (TN-25)."""
    if not isinstance(binding_epoch, Fingerprint):
        return invalid(
            "binding_epoch",
            "a virtual position is scoped to the CT-28 binding epoch",
            given=repr(binding_epoch),
        )
    inst = clean_token(instrument)
    if inst is None:
        return invalid(
            "instrument",
            "a virtual position names an instrument",
            given=repr(instrument),
        )
    bot = clean_token(bot_id)
    if bot is None:
        return invalid("bot_id", "a virtual position is Bot-attributed", given=repr(bot_id))
    if not isinstance(admission_identity, Fingerprint):
        return invalid(
            "admission_identity",
            "admission identity is an fp1 Fingerprint",
            given=repr(admission_identity),
        )
    if not isinstance(command_identity, Fingerprint):
        return invalid(
            "command_identity",
            "fills join the virtual fold by declared command identity",
            given=repr(command_identity),
        )
    if not isinstance(faces, RFaces):
        return invalid("faces", "frozen R faces are an RFaces value", given=repr(faces))
    if not isinstance(admitted_quantity, Quantity):
        return invalid(
            "admitted_quantity",
            "admitted quantity is a Quantity",
            given=repr(admitted_quantity),
        )
    if admitted_quantity.as_fraction() <= 0:
        return invalid(
            "admitted_quantity",
            "admitted quantity is strictly positive",
            given=str(admitted_quantity.as_fraction()),
        )
    filled: Quantity
    if filled_quantity is None:
        filled = admitted_quantity
    elif isinstance(filled_quantity, Quantity):
        filled = filled_quantity
    else:
        return invalid(
            "filled_quantity",
            "filled quantity is a Quantity",
            given=repr(filled_quantity),
        )
    if isinstance(status, VirtualPositionStatus):
        resolved_status = status
    elif isinstance(status, str):
        try:
            resolved_status = VirtualPositionStatus(status)
        except ValueError:
            return invalid(
                "status",
                "virtual position status is open|closed|pending-entry",
                given=repr(status),
            )
    else:
        return invalid(
            "status",
            "virtual position status is open|closed|pending-entry",
            given=repr(status),
        )

    content = {
        "admission_identity": admission_identity.value,
        "binding_epoch": binding_epoch.value,
        "bot_id": bot,
        "class": "virtual-position",
        "command_identity": command_identity.value,
        "instrument": inst,
    }
    ref = fingerprint(content)
    if is_refusal(ref):
        return ref
    return Ok(
        VirtualPosition(
            position_ref=ref.value,
            binding_epoch=binding_epoch,
            instrument=inst,
            bot_id=bot,
            admission_identity=admission_identity,
            command_identity=command_identity,
            faces=faces,
            admission_faces=faces,
            admitted_quantity=admitted_quantity,
            filled_quantity=filled,
            status=resolved_status,
            rebased=False,
        )
    )


def refuse_top_up_short_fill(*, attempt_top_up: object) -> Result[None]:
    """Refuse topping up a short ENTRY fill — V1 admits no scale-in (TN-24a)."""
    if not isinstance(attempt_top_up, bool):
        return invalid(
            "attempt_top_up",
            "top-up guard takes a bool naming whether a top-up was requested",
            given=repr(attempt_top_up),
        )
    if attempt_top_up:
        return policy(
            "attempt_top_up",
            "a short ENTRY fill is never topped up; any later tranche requires a "
            "new admission under a later Book version (V1 admits no scale-in)",
        )
    return Ok(None)


def rebase_partial_entry(
    position: object,
    *,
    filled_quantity: object,
    terminal: object = True,
) -> Result[tuple[VirtualPosition, PartialEntryRebase]]:
    """Re-base ``original_risk_amount`` exactly once at first terminal state.

    ``original_risk_distance`` stays frozen. The admission amount remains the
    declared plan under an ``admission-plan`` lineage edge. A short fill is
    recorded as execution-quality evidence. A second re-base, a non-terminal
    call, a full fill, or an overfill is refused (TN-24a; DEC-0154).
    """
    if not isinstance(position, VirtualPosition):
        return invalid(
            "position",
            "partial-entry re-base applies to a VirtualPosition",
            given=repr(position),
        )
    if not isinstance(terminal, bool):
        return invalid("terminal", "first-terminal-state flag is a bool", given=repr(terminal))
    if not terminal:
        return invalid(
            "terminal",
            "original_risk_amount re-bases only at the ENTRY's first terminal state",
        )
    if position.rebased:
        return policy(
            "rebased",
            "original_risk_amount re-bases exactly once; a second re-base is refused",
            position_ref=position.position_ref.value,
        )
    if not isinstance(filled_quantity, Quantity):
        return invalid(
            "filled_quantity",
            "filled quantity is a Quantity",
            given=repr(filled_quantity),
        )
    if filled_quantity.unit != position.admitted_quantity.unit:
        return invalid(
            "filled_quantity",
            "filled quantity must share the admitted quantity unit",
            admitted=position.admitted_quantity.unit,
            filled=filled_quantity.unit,
        )
    admitted_frac = position.admitted_quantity.as_fraction()
    filled_frac = filled_quantity.as_fraction()
    if filled_frac <= 0:
        return invalid(
            "filled_quantity",
            "filled quantity at terminal state is strictly positive",
            given=str(filled_frac),
        )
    if filled_frac > admitted_frac:
        return invalid(
            "filled_quantity",
            "filled quantity cannot exceed the admitted plan",
            admitted=str(admitted_frac),
            filled=str(filled_frac),
        )
    if filled_frac == admitted_frac:
        return invalid(
            "filled_quantity",
            "a full fill needs no re-base; original_risk_amount already matches "
            "the admitted quantity",
        )

    # Exact scaled-integer re-base: amount' = amount * filled / admitted.
    # Refuse rather than silently round when not representable at the amount scale.
    admission_amount = position.admission_faces.original_risk_amount
    product = admission_amount.as_fraction() * filled_frac / admitted_frac
    scale = admission_amount.scale
    scaled = product * (10**scale)
    if scaled.denominator != 1:
        return invalid(
            "scale",
            "re-based original_risk_amount is not exactly representable at the "
            "declared money scale; refuse rather than round on the money path",
            amount=str(product),
            scale=scale,
        )
    rebased_money = Money.try_create(
        scaled.numerator, admission_amount.currency, scale
    )
    if is_refusal(rebased_money):
        return rebased_money
    rebased_faces = RFaces.try_create(
        position.admission_faces.original_risk_distance,
        rebased_money.value,
    )
    if is_refusal(rebased_faces):
        return rebased_faces

    shortfall_q = position.admitted_quantity.subtract(filled_quantity)
    if is_refusal(shortfall_q):
        return shortfall_q
    evidence = ExecutionQualityEvidence(
        kind=EXECUTION_QUALITY_SHORT_FILL,
        admitted_quantity=position.admitted_quantity,
        filled_quantity=filled_quantity,
        shortfall=shortfall_q.value,
    )
    lineage = MappingProxyType(
        {
            "admission_faces": position.admission_faces.fp1_identity(),
            "edge": ADMISSION_PLAN_EDGE,
            "filled_quantity": filled_quantity.fp1_identity(),
            "position_ref": position.position_ref.value,
            "rebased_faces": rebased_faces.value.fp1_identity(),
        }
    )
    outcome = PartialEntryRebase(
        admission_faces=position.admission_faces,
        rebased_faces=rebased_faces.value,
        admission_plan_edge=ADMISSION_PLAN_EDGE,
        execution_quality=evidence,
        lineage_content=lineage,
    )
    updated = VirtualPosition(
        position_ref=position.position_ref,
        binding_epoch=position.binding_epoch,
        instrument=position.instrument,
        bot_id=position.bot_id,
        admission_identity=position.admission_identity,
        command_identity=position.command_identity,
        faces=rebased_faces.value,
        admission_faces=position.admission_faces,
        admitted_quantity=position.admitted_quantity,
        filled_quantity=filled_quantity,
        status=VirtualPositionStatus.OPEN,
        rebased=True,
        admission_plan_edge=ADMISSION_PLAN_EDGE,
        execution_quality=evidence,
    )
    return Ok((updated, outcome))
