"""Pinned fill/slippage/cost Protocol seams (B-6, AR-56, Story 14.5).

Inbound execution is a CT-23 Book-resolved authorized intent or a typed
refusal — never a bot-sized order. Fill, slippage, and cost are SEPARATE
``typing.Protocol`` ports; Story 17.1 binds adapters from the resolved
run-config. Fill decides ``Fill | NoFill | PartialFill`` with partial
quantities first-class. Every fill carries an ``optimistic`` taint until
GAP-0048. Store-persisted synthetic data derives ``world=simulated`` and is
a ``policy rejection`` for governed evidence. Financing is a scheduled
position-level cash event, never an order fill. Nothing here imports
``qmf-venue``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from typing import Final, Protocol, TypeAlias, cast, runtime_checkable

from qmf.core.exact import Money, Price, Quantity
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.risk.door import EntryIntent, ExitIntent
from qmf.risk.exit_record import CostComponent, ExitRecord

from qmb._refuse import clean_token, invalid, policy
from qmb.config.compiler import (
    PROVENANCE_PROCEDURE_EPHEMERAL,
    PROVENANCE_RECORDED,
    PROVENANCE_SYNTHETIC_TAINTED,
    ResolvedRunConfig,
)
from qmb.execution.risk import (
    admit_open,
    evaluate_exit,
    mint_replay_exit,
    require_full_loss_before_open,
)

__all__ = [
    "CLAIMS_EDGE",
    "COMPOSITION_ORDER",
    "COMPOSITION_VERSION",
    "FILL_DECISIONS",
    "FINANCING_IS_ORDER_FILL",
    "GAP_0048_OPEN",
    "PORT_ROLES",
    "SPENDS_SPLIT_BUDGET",
    "TAINT_IS_IDENTITY",
    "TAINT_OPTIMISTIC",
    "AuthorizedIntent",
    "CostPort",
    "CostedFill",
    "ExecutionPorts",
    "Fill",
    "FillDecision",
    "FillKind",
    "FillPort",
    "Filled",
    "FinancingPort",
    "NoFill",
    "PartialFill",
    "SlicePath",
    "SlippagePort",
    "apply_execution_ports",
    "classify_fill_quantity",
    "derive_world_from_provenance",
    "execute_authorized",
    "fingerprint_ports",
    "ports_identity",
    "record_virtual_close",
    "refuse_optimistic_edge_claim",
    "refuse_store_synthetic_governed_evidence",
    "require_authorized_intent",
]

AuthorizedIntent: TypeAlias = EntryIntent | ExitIntent

PORT_ROLES: Final[tuple[str, ...]] = (
    "fill",
    "slippage",
    "cost",
    "financing",
)
COMPOSITION_ORDER: Final[tuple[str, ...]] = ("fill", "slippage", "cost")
COMPOSITION_VERSION: Final[int] = 1
TAINT_OPTIMISTIC: Final[str] = "optimistic"
TAINT_IS_IDENTITY: Final[bool] = False
GAP_0048_OPEN: Final[bool] = True
CLAIMS_EDGE: Final[bool] = False
SPENDS_SPLIT_BUDGET: Final[bool] = False
FINANCING_IS_ORDER_FILL: Final[bool] = False
_ADAPTER_BINDING: Final[str] = "resolved-run-config"
_LEGAL_PROVENANCE: Final[frozenset[str]] = frozenset(
    {
        PROVENANCE_RECORDED,
        PROVENANCE_SYNTHETIC_TAINTED,
        PROVENANCE_PROCEDURE_EPHEMERAL,
    }
)


class FillKind(StrEnum):
    """The fill port's three first-class decisions (B-6, AR-56)."""

    FILL = "fill"
    NO_FILL = "no-fill"
    PARTIAL_FILL = "partial-fill"


FILL_DECISIONS: Final[tuple[str, ...]] = (
    FillKind.FILL.value,
    FillKind.NO_FILL.value,
    FillKind.PARTIAL_FILL.value,
)


def ports_identity() -> dict[str, object]:
    """Identity-bearing execution-port fields. Package SemVer is omitted."""
    return {
        "adapter_binding": _ADAPTER_BINDING,
        "authorized_intent": (
            f"{EntryIntent.__module__}.{EntryIntent.__qualname__}",
            f"{ExitIntent.__module__}.{ExitIntent.__qualname__}",
        ),
        "claims_edge": CLAIMS_EDGE,
        "composition_order": COMPOSITION_ORDER,
        "composition_version": COMPOSITION_VERSION,
        "exit_record": f"{ExitRecord.__module__}.{ExitRecord.__qualname__}",
        "fill_decisions": FILL_DECISIONS,
        "financing_is_order_fill": FINANCING_IS_ORDER_FILL,
        "full_loss_before_open": True,
        "gap_0048_open": GAP_0048_OPEN,
        "port_roles": PORT_ROLES,
        "spends_split_budget": SPENDS_SPLIT_BUDGET,
        "taint_field": TAINT_OPTIMISTIC,
        "taint_is_identity": TAINT_IS_IDENTITY,
    }


def fingerprint_ports() -> Result[Fingerprint]:
    """``fp1`` over :func:`ports_identity`. Reordering ports changes it."""
    return fingerprint(ports_identity())


def require_authorized_intent(intent: object) -> Result[AuthorizedIntent]:
    """Inbound execution is a CT-23 intent, never a bot-sized order (B-6)."""
    if isinstance(intent, (EntryIntent, ExitIntent)):
        return Ok(intent)
    return invalid(
        "intent",
        "inbound execution is a CT-23 Book-resolved authorized intent or a typed "
        "refusal, never a bot-sized order (B-6, AR-56, DEC-0164)",
        given=repr(type(intent).__name__),
    )


def derive_world_from_provenance(data_provenance: object) -> Result[World]:
    """World is provenance-derived, never caller-declared (B-7)."""
    token = clean_token(data_provenance)
    if token is None or token not in _LEGAL_PROVENANCE:
        return invalid(
            "data_provenance",
            "world derives from a recorded, synthetic-tainted, or procedure-ephemeral "
            "provenance token (B-7, DEC-0164)",
            given=repr(data_provenance),
            allowed=sorted(_LEGAL_PROVENANCE),
        )
    if token == PROVENANCE_SYNTHETIC_TAINTED:
        return Ok(World.SIMULATED)
    return Ok(World.REPLAY)


def refuse_store_synthetic_governed_evidence(source: object) -> Result[World]:
    """Store-persisted synthetic data is ``world=simulated`` and refused (B-7).

    Legal for infrastructure stress and strategy-logic smoke tests only until
    GAP-0048. Procedure-ephemeral perturbation stays ``world=replay``.
    """
    provenance: str | None = None
    declared: World | None = None
    if isinstance(source, ResolvedRunConfig):
        provenance = source.data_provenance
        declared = source.world
    elif isinstance(source, World):
        declared = source
    else:
        token = clean_token(source)
        if token is None:
            return invalid(
                "data_provenance",
                "governed-evidence execution names data provenance, a resolved "
                "run-config, or a derived world (B-7)",
                given=repr(type(source).__name__),
            )
        provenance = token
    derived: World | None = None
    if provenance is not None:
        looked = derive_world_from_provenance(provenance)
        if is_refusal(looked):
            return looked
        derived = looked.value
    world = derived if derived is not None else declared
    if world is None:
        return invalid(
            "world",
            "governed-evidence execution needs a provenance-derived world (B-7)",
        )
    if declared is not None and derived is not None and declared is not derived:
        return invalid(
            "world",
            "world is provenance-derived, never caller-declared (B-7, FM-3)",
            given=declared.value,
            derived=derived.value,
        )
    if world is World.SIMULATED or derived is World.SIMULATED:
        return policy(
            "world",
            "a run that reads store-persisted synthetic data is world=simulated "
            "and a policy rejection for governed evidence until GAP-0048 "
            "(B-7, FM-2, SC-06)",
            world=World.SIMULATED.value,
            data_provenance=provenance,
            gap="GAP-0048",
        )
    return Ok(world)


def refuse_optimistic_edge_claim(
    *,
    taint: object = TAINT_OPTIMISTIC,
    claims_edge: bool = False,
    spends_split_budget: bool = False,
) -> Result[None]:
    """Optimistic-tainted fills spend no split budget and claim no edge (FM-9)."""
    token = clean_token(taint) if not isinstance(taint, str) else taint
    if token != TAINT_OPTIMISTIC:
        return invalid(
            "taint",
            "until GAP-0048 every fill carries the optimistic taint (B-6, SC-06)",
            given=repr(taint),
            gap="GAP-0048",
        )
    if claims_edge or spends_split_budget:
        return policy(
            "taint",
            "optimistic-tainted fills cannot spend split budget and cannot claim "
            "edge until GAP-0048 (B-6, SC-06, FM-9)",
            taint=TAINT_OPTIMISTIC,
            claims_edge=claims_edge,
            spends_split_budget=spends_split_budget,
            gap="GAP-0048",
        )
    return Ok(None)


def _require_optimistic_taint(taint: object) -> Result[str]:
    if taint is None:
        return Ok(TAINT_OPTIMISTIC)
    token = clean_token(taint)
    if token != TAINT_OPTIMISTIC:
        return policy(
            "taint",
            "until GAP-0048 every fill carries the optimistic taint; a different "
            "taint is a policy rejection (B-6, SC-06)",
            given=repr(taint),
            gap="GAP-0048",
        )
    return Ok(TAINT_OPTIMISTIC)


@dataclass(frozen=True, slots=True)
class SlicePath:
    """Declared intra-slice path the fill port crosses (B-6).

    Same (possibly gap-fixed) series the slice's bars consume — never a future
    or a divergent series. Adapters decide the crossing.
    """

    stream_id: str
    prints: tuple[Price, ...]

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        return {
            "class": "slice-path",
            "prints": [item.fp1_identity() for item in self.prints],
            "stream_id": self.stream_id,
        }

    @classmethod
    def try_create(cls, stream_id: object, prints: object) -> Result[SlicePath]:
        """Validate a declared intra-slice path."""
        token = clean_token(stream_id)
        if token is None:
            return invalid(
                "stream_id",
                "a slice path names a non-empty stream id",
                given=repr(stream_id),
            )
        if isinstance(prints, Price):
            return Ok(cls(stream_id=token, prints=(prints,)))
        if isinstance(prints, (str, bytes)) or not isinstance(prints, Sequence):
            return invalid(
                "prints",
                "a slice path is a sequence of exact Prices the fill port may cross",
                given=repr(type(prints).__name__),
            )
        parsed: list[Price] = []
        for index, raw in enumerate(cast("Sequence[object]", prints)):
            if not isinstance(raw, Price):
                return invalid(
                    "prints",
                    "each path print is an exact Price",
                    index=index,
                    given=repr(type(raw).__name__),
                )
            parsed.append(raw)
        return Ok(cls(stream_id=token, prints=tuple(parsed)))


@dataclass(frozen=True, slots=True)
class NoFill:
    """The fill or slippage port declined the crossing (B-6)."""

    reason: str
    kind: FillKind = FillKind.NO_FILL
    taint: str = TAINT_OPTIMISTIC

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. The taint field is omitted (DEC-0164)."""
        return {"class": "no-fill", "kind": self.kind.value, "reason": self.reason}

    @classmethod
    def try_create(cls, reason: object, *, taint: object = None) -> Result[NoFill]:
        """Validate a no-fill decision."""
        token = clean_token(reason)
        if token is None:
            return invalid(
                "reason",
                "a no-fill decision names why the path was not crossed",
                given=repr(reason),
            )
        stamped = _require_optimistic_taint(taint)
        if is_refusal(stamped):
            return stamped
        return Ok(cls(reason=token, taint=stamped.value))


@dataclass(frozen=True, slots=True)
class Fill:
    """A full fill of the requested quantity at a pre-slip price (B-6)."""

    quantity: Quantity
    requested_quantity: Quantity
    pre_slip_price: Price
    post_slip_price: Price | None = None
    kind: FillKind = FillKind.FILL
    taint: str = TAINT_OPTIMISTIC

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. The taint field is omitted (DEC-0164)."""
        content: dict[str, object] = {
            "class": "fill",
            "kind": self.kind.value,
            "pre_slip_price": self.pre_slip_price.fp1_identity(),
            "quantity": self.quantity.fp1_identity(),
            "requested_quantity": self.requested_quantity.fp1_identity(),
        }
        if self.post_slip_price is not None:
            content["post_slip_price"] = self.post_slip_price.fp1_identity()
        return content

    @classmethod
    def try_create(
        cls,
        quantity: object,
        requested_quantity: object,
        pre_slip_price: object,
        *,
        post_slip_price: object = None,
        taint: object = None,
    ) -> Result[Fill]:
        """Validate a full fill. Partial quantities belong on :class:`PartialFill`."""
        qty = _require_quantity(quantity, "quantity")
        if is_refusal(qty):
            return qty
        requested = _require_quantity(requested_quantity, "requested_quantity")
        if is_refusal(requested):
            return requested
        if qty.value.unit != requested.value.unit:
            return invalid(
                "quantity",
                "filled and requested quantities share one unit",
                filled=qty.value.unit,
                requested=requested.value.unit,
            )
        if qty.value.as_fraction() <= 0:
            return invalid(
                "quantity",
                "a fill quantity is a positive exact count; zero is NoFill",
                given=str(qty.value.as_fraction()),
            )
        if qty.value.as_fraction() != requested.value.as_fraction():
            return invalid(
                "quantity",
                "a Fill is the full requested quantity; a shortfall is PartialFill",
                filled=str(qty.value.as_fraction()),
                requested=str(requested.value.as_fraction()),
            )
        price = _require_price(pre_slip_price, "pre_slip_price")
        if is_refusal(price):
            return price
        slipped: Price | None = None
        if post_slip_price is not None:
            parsed = _require_price(post_slip_price, "post_slip_price")
            if is_refusal(parsed):
                return parsed
            slipped = parsed.value
        stamped = _require_optimistic_taint(taint)
        if is_refusal(stamped):
            return stamped
        return Ok(
            cls(
                quantity=qty.value,
                requested_quantity=requested.value,
                pre_slip_price=price.value,
                post_slip_price=slipped,
                taint=stamped.value,
            )
        )


@dataclass(frozen=True, slots=True)
class PartialFill:
    """A first-class partial fill — not a flag on :class:`Fill` (B-6, AR-56)."""

    quantity: Quantity
    requested_quantity: Quantity
    remaining_quantity: Quantity
    pre_slip_price: Price
    post_slip_price: Price | None = None
    kind: FillKind = FillKind.PARTIAL_FILL
    taint: str = TAINT_OPTIMISTIC

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. The taint field is omitted (DEC-0164)."""
        content: dict[str, object] = {
            "class": "partial-fill",
            "kind": self.kind.value,
            "pre_slip_price": self.pre_slip_price.fp1_identity(),
            "quantity": self.quantity.fp1_identity(),
            "remaining_quantity": self.remaining_quantity.fp1_identity(),
            "requested_quantity": self.requested_quantity.fp1_identity(),
        }
        if self.post_slip_price is not None:
            content["post_slip_price"] = self.post_slip_price.fp1_identity()
        return content

    @classmethod
    def try_create(
        cls,
        quantity: object,
        requested_quantity: object,
        pre_slip_price: object,
        *,
        remaining_quantity: object = None,
        post_slip_price: object = None,
        taint: object = None,
    ) -> Result[PartialFill]:
        """Validate a partial fill. Remaining is requested minus filled when omitted."""
        qty = _require_quantity(quantity, "quantity")
        if is_refusal(qty):
            return qty
        requested = _require_quantity(requested_quantity, "requested_quantity")
        if is_refusal(requested):
            return requested
        if qty.value.unit != requested.value.unit:
            return invalid(
                "quantity",
                "filled and requested quantities share one unit",
                filled=qty.value.unit,
                requested=requested.value.unit,
            )
        if qty.value.as_fraction() <= 0:
            return invalid(
                "quantity",
                "a partial-fill quantity is a positive exact count; zero is NoFill",
                given=str(qty.value.as_fraction()),
            )
        if qty.value.as_fraction() >= requested.value.as_fraction():
            return invalid(
                "quantity",
                "a PartialFill is a positive shortfall of the requested quantity; "
                "a full fill is Fill",
                filled=str(qty.value.as_fraction()),
                requested=str(requested.value.as_fraction()),
            )
        if remaining_quantity is None:
            leftover = requested.value.subtract(qty.value)
            if is_refusal(leftover):
                return leftover
            remaining = leftover.value
        else:
            parsed_remaining = _require_quantity(remaining_quantity, "remaining_quantity")
            if is_refusal(parsed_remaining):
                return parsed_remaining
            remaining = parsed_remaining.value
            expected = requested.value.subtract(qty.value)
            if is_refusal(expected):
                return expected
            if remaining.as_fraction() != expected.value.as_fraction():
                return invalid(
                    "remaining_quantity",
                    "remaining quantity is requested minus filled",
                    given=str(remaining.as_fraction()),
                    expected=str(expected.value.as_fraction()),
                )
        price = _require_price(pre_slip_price, "pre_slip_price")
        if is_refusal(price):
            return price
        slipped: Price | None = None
        if post_slip_price is not None:
            parsed = _require_price(post_slip_price, "post_slip_price")
            if is_refusal(parsed):
                return parsed
            slipped = parsed.value
        stamped = _require_optimistic_taint(taint)
        if is_refusal(stamped):
            return stamped
        return Ok(
            cls(
                quantity=qty.value,
                requested_quantity=requested.value,
                remaining_quantity=remaining,
                pre_slip_price=price.value,
                post_slip_price=slipped,
                taint=stamped.value,
            )
        )


Filled: TypeAlias = Fill | PartialFill
FillDecision: TypeAlias = Fill | NoFill | PartialFill


@dataclass(frozen=True, slots=True)
class CostedFill:
    """A post-slip fill with itemized exact-integer cash charges (B-6).

    Each partial carries its own pro-rated fee — adapters itemize;
    this type makes that per-fill cost set first-class.
    """

    fill: Fill | PartialFill
    costs: tuple[CostComponent, ...]
    taint: str = TAINT_OPTIMISTIC

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. The taint field is omitted (DEC-0164)."""
        return {
            "class": "costed-fill",
            "costs": [item.fp1_identity() for item in self.costs],
            "fill": self.fill.fp1_identity(),
        }

    @classmethod
    def try_create(cls, fill: object, costs: object) -> Result[CostedFill]:
        """Validate a costed fill. Taint is copied from the fill and must be optimistic."""
        if not isinstance(fill, (Fill, PartialFill)):
            return invalid(
                "fill",
                "cost itemizes a Fill or PartialFill; NoFill never reaches cost",
                given=repr(type(fill).__name__),
            )
        if fill.taint != TAINT_OPTIMISTIC:
            return policy(
                "taint",
                "until GAP-0048 every fill carries the optimistic taint (B-6, SC-06)",
                given=fill.taint,
                gap="GAP-0048",
            )
        parsed_costs = _as_cost_tuple(costs)
        if is_refusal(parsed_costs):
            return parsed_costs
        return Ok(cls(fill=fill, costs=parsed_costs.value, taint=fill.taint))


def classify_fill_quantity(
    *,
    requested: object,
    filled: object,
    position_cap: object,
    lot_step: object,
    pre_slip_price: object,
    post_slip_price: object = None,
) -> Result[Fill | NoFill | PartialFill]:
    """Cap by position size and lot step; classify Fill, PartialFill, or NoFill.

    Partial quantities are first-class. A zero after the lot-step snap is
    ``NoFill``. Adapters produce the raw filled count; this pins the
    composition invariant.
    """
    wanted = _require_quantity(requested, "requested_quantity")
    if is_refusal(wanted):
        return wanted
    raw = _require_quantity(filled, "quantity")
    if is_refusal(raw):
        return raw
    cap = _require_quantity(position_cap, "position_cap")
    if is_refusal(cap):
        return cap
    step = _require_quantity(lot_step, "lot_step")
    if is_refusal(step):
        return step
    price = _require_price(pre_slip_price, "pre_slip_price")
    if is_refusal(price):
        return price
    unit = wanted.value.unit
    for field, qty in (
        ("quantity", raw.value),
        ("position_cap", cap.value),
        ("lot_step", step.value),
    ):
        if qty.unit != unit:
            return invalid(
                field,
                "requested, filled, position-cap, and lot-step quantities share one unit",
                unit=unit,
                given=qty.unit,
            )
    if wanted.value.as_fraction() <= 0:
        return invalid(
            "requested_quantity",
            "a requested quantity is a positive exact count",
            given=str(wanted.value.as_fraction()),
        )
    if cap.value.as_fraction() <= 0:
        return invalid(
            "position_cap",
            "position size is a positive exact cap on a partial fill",
            given=str(cap.value.as_fraction()),
        )
    if step.value.as_fraction() <= 0:
        return invalid(
            "lot_step",
            "instrument lot step is a positive exact quantity",
            given=str(step.value.as_fraction()),
        )
    if raw.value.as_fraction() < 0:
        return invalid(
            "quantity",
            "a filled quantity is a non-negative exact count",
            given=str(raw.value.as_fraction()),
        )
    ceiling = min(
        raw.value.as_fraction(),
        wanted.value.as_fraction(),
        cap.value.as_fraction(),
    )
    snapped = _floor_to_step(ceiling, step.value)
    if is_refusal(snapped):
        return snapped
    if snapped.value.as_fraction() <= 0:
        none = NoFill.try_create("lot-step-snap-to-zero")
        if is_refusal(none):
            return none
        return _as_fill_decision(none.value)
    if snapped.value.as_fraction() == wanted.value.as_fraction():
        full = Fill.try_create(
            snapped.value,
            wanted.value,
            price.value,
            post_slip_price=post_slip_price,
        )
        if is_refusal(full):
            return full
        return _as_fill_decision(full.value)
    partial = PartialFill.try_create(
        snapped.value,
        wanted.value,
        price.value,
        post_slip_price=post_slip_price,
    )
    if is_refusal(partial):
        return partial
    return _as_fill_decision(partial.value)


@runtime_checkable
class FillPort(Protocol):
    """Pinned fill seam. Adapters bind from the resolved run-config (B-6, AR-56)."""

    def decide(
        self,
        intent: AuthorizedIntent,
        path: SlicePath,
        *,
        requested_quantity: Quantity,
    ) -> Result[Fill | NoFill | PartialFill]:  # pragma: no cover - protocol seam
        """Decide Fill, NoFill, or PartialFill and a pre-slip price by path crossing."""
        ...


@runtime_checkable
class SlippagePort(Protocol):
    """Pinned slippage seam. Maps pre-slip to post-slip; may veto (B-6)."""

    def apply(
        self,
        fill: Fill | PartialFill,
        path: SlicePath,
    ) -> Result[Fill | NoFill | PartialFill]:  # pragma: no cover - protocol seam
        """Map to a post-slip price, or NoFill when the slipped print is illegal."""
        ...


@runtime_checkable
class CostPort(Protocol):
    """Pinned cost seam. Itemizes exact-integer cash charges (B-6)."""

    def itemize(
        self,
        fill: Fill | PartialFill,
    ) -> Result[CostedFill]:  # pragma: no cover - protocol seam
        """Itemize commission (and kin) on the post-slip fill; each partial is its own fee."""
        ...


@runtime_checkable
class FinancingPort(Protocol):
    """Pinned financing seam — scheduled cash event, never an order fill (B-6)."""

    def schedule(
        self,
        *,
        stream_id: str,
        direction: object,
    ) -> Result[Money]:  # pragma: no cover - protocol seam
        """Sub-phase 2 position-level cash event at the accounting rollover."""
        ...


@dataclass(frozen=True, slots=True)
class ExecutionPorts:
    """The four bound ports. Composition of fills is fill → slippage → cost."""

    fill: FillPort
    slippage: SlippagePort
    cost: CostPort
    financing: FinancingPort

    @classmethod
    def try_create(
        cls,
        fill: object,
        slippage: object,
        cost: object,
        financing: object,
    ) -> Result[ExecutionPorts]:
        """Bind SEPARATE Protocol ports. Adapters bind from the resolved run-config."""
        if not isinstance(fill, FillPort):
            return invalid(
                "fill",
                "fill is a pinned FillPort Protocol seam; adapters bind from the resolved run-config",
                given=repr(type(fill).__name__),
            )
        if not isinstance(slippage, SlippagePort):
            return invalid(
                "slippage",
                "slippage is a pinned SlippagePort Protocol seam, separate from fill",
                given=repr(type(slippage).__name__),
            )
        if not isinstance(cost, CostPort):
            return invalid(
                "cost",
                "cost is a pinned CostPort Protocol seam, separate from fill and slippage",
                given=repr(type(cost).__name__),
            )
        if not isinstance(financing, FinancingPort):
            return invalid(
                "financing",
                "financing is a pinned FinancingPort Protocol seam; it is a scheduled "
                "cash event, never an order fill",
                given=repr(type(financing).__name__),
            )
        if id(fill) == id(slippage) or id(fill) == id(cost) or id(slippage) == id(cost):
            return invalid(
                "ports",
                "fill, slippage, and cost are SEPARATE pinned ports (B-6, AR-56)",
            )
        return Ok(
            cls(
                fill=fill,
                slippage=slippage,
                cost=cost,
                financing=financing,
            )
        )


def apply_execution_ports(
    ports: object,
    *,
    intent: object,
    path: object,
    requested_quantity: object,
    position_cap: object,
    lot_step: object,
) -> Result[CostedFill | NoFill]:
    """Run fill → slippage → cost. Financing is not an order fill.

    The fill port's quantity is capped by position size and lot step. Slippage
    may only map price or veto; it never resizes. Cost never resizes.
    """
    bound = _require_ports(ports)
    if is_refusal(bound):
        return bound
    authorized = require_authorized_intent(intent)
    if is_refusal(authorized):
        return authorized
    declared = _require_path(path)
    if is_refusal(declared):
        return declared
    requested = _require_quantity(requested_quantity, "requested_quantity")
    if is_refusal(requested):
        return requested
    cap = _require_quantity(position_cap, "position_cap")
    if is_refusal(cap):
        return cap
    step = _require_quantity(lot_step, "lot_step")
    if is_refusal(step):
        return step
    decided = bound.value.fill.decide(
        authorized.value,
        declared.value,
        requested_quantity=requested.value,
    )
    if is_refusal(decided):
        return decided
    classified = _classify_decision(
        decided.value,
        requested=requested.value,
        position_cap=cap.value,
        lot_step=step.value,
    )
    if is_refusal(classified):
        return classified
    if isinstance(classified.value, NoFill):
        return _as_outcome(classified.value)
    filled: Fill | PartialFill = classified.value
    slipped = bound.value.slippage.apply(filled, declared.value)
    if is_refusal(slipped):
        return slipped
    if isinstance(slipped.value, NoFill):
        return _as_outcome(slipped.value)
    resized = _quantity_changed(filled, slipped.value)
    if is_refusal(resized):
        return resized
    priced = _require_post_slip(slipped.value)
    if is_refusal(priced):
        return priced
    costed = bound.value.cost.itemize(priced.value)
    if is_refusal(costed):
        return costed
    resized_cost = _quantity_changed(priced.value, costed.value.fill)
    if is_refusal(resized_cost):
        return resized_cost
    if costed.value.taint != TAINT_OPTIMISTIC or costed.value.fill.taint != TAINT_OPTIMISTIC:
        return policy(
            "taint",
            "until GAP-0048 every fill carries the optimistic taint (B-6, SC-06)",
            gap="GAP-0048",
        )
    return _as_outcome(costed.value)


def execute_authorized(
    binding: object,
    *,
    intent: object,
    ports: object,
    path: object,
    requested_quantity: object,
    position_cap: object,
    lot_step: object,
    data_provenance: object,
    entry_price: object = None,
    exit_logic_ref: object = None,
    module: object = None,
    book_resolved_requested_r: object = None,
) -> Result[CostedFill | NoFill]:
    """Authorize a CT-23 intent, then run the pinned ports (B-6, AR-56, CT-23).

    Store-persisted synthetic provenance is refused for governed evidence.
    An entry requires an AD-40 full-loss price before any open. An exit is
    risk-monotonic. Ports execute the authorized intent and never re-size it.
    """
    world = refuse_store_synthetic_governed_evidence(data_provenance)
    if is_refusal(world):
        return world
    authorized = require_authorized_intent(intent)
    if is_refusal(authorized):
        return authorized
    if isinstance(authorized.value, EntryIntent):
        admitted = admit_open(
            binding,
            intent=authorized.value,
            entry_price=entry_price,
            exit_logic_ref=exit_logic_ref,
            module=module,
            book_resolved_requested_r=book_resolved_requested_r,
        )
        if is_refusal(admitted):
            return admitted
        checked = require_full_loss_before_open(admitted.value.declared_full_loss_price)
        if is_refusal(checked):
            return checked
    else:
        evaluated = evaluate_exit(binding, authorized.value)
        if is_refusal(evaluated):
            return evaluated
    return apply_execution_ports(
        ports,
        intent=authorized.value,
        path=path,
        requested_quantity=requested_quantity,
        position_cap=position_cap,
        lot_step=lot_step,
    )


def record_virtual_close(
    binding: object,
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
    recorded_at: object,
    closed_refs: object = (),
    arbitration_record_ref: object = None,
    venue_observation_ref: object = None,
) -> Result[ExitRecord]:
    """Mint exactly one CT-29 exit record per virtual-position close (FR-032)."""
    refs = _as_closed_refs(closed_refs)
    if is_refusal(refs):
        return refs
    if isinstance(virtual_position_ref, Fingerprint) and virtual_position_ref in refs.value:
        return policy(
            "virtual_position_ref",
            "exactly one CT-29 exit record is minted per virtual-position close "
            "against the run's world=replay binding (CT-29, FR-032)",
            virtual_position_ref=virtual_position_ref.value,
        )
    return mint_replay_exit(
        binding,
        virtual_position_ref=virtual_position_ref,
        opening_bot_id=opening_bot_id,
        original_risk_distance=original_risk_distance,
        original_risk_amount=original_risk_amount,
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
        recorded_at=recorded_at,
        arbitration_record_ref=arbitration_record_ref,
        venue_observation_ref=venue_observation_ref,
    )


def _require_ports(value: object) -> Result[ExecutionPorts]:
    if isinstance(value, ExecutionPorts):
        return Ok(value)
    return invalid(
        "ports",
        "execution binds ExecutionPorts of fill, slippage, cost, and financing",
        given=repr(type(value).__name__),
    )


def _require_path(value: object) -> Result[SlicePath]:
    if isinstance(value, SlicePath):
        return Ok(value)
    return invalid(
        "path",
        "the fill port crosses a declared SlicePath inside the slice",
        given=repr(type(value).__name__),
    )


def _require_quantity(value: object, field: str) -> Result[Quantity]:
    if isinstance(value, Quantity):
        return Ok(value)
    return invalid(
        field,
        "a fill quantity is an exact Quantity, never a binary float",
        given=repr(type(value).__name__),
    )


def _require_price(value: object, field: str) -> Result[Price]:
    if isinstance(value, Price):
        return Ok(value)
    return invalid(
        field,
        "a fill price is an exact Price, never a binary float",
        given=repr(type(value).__name__),
    )


def _as_cost_tuple(value: object) -> Result[tuple[CostComponent, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, CostComponent):
        return Ok((value,))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "costs",
            "cost itemizes a sequence of CT-29 CostComponent values",
            given=repr(type(value).__name__),
        )
    parsed: list[CostComponent] = []
    for index, raw in enumerate(cast("Sequence[object]", value)):
        if not isinstance(raw, CostComponent):
            return invalid(
                "costs",
                "each cost component is a CT-29 CostComponent in exact-integer money",
                index=index,
                given=repr(type(raw).__name__),
            )
        parsed.append(raw)
    return Ok(tuple(parsed))


def _as_closed_refs(value: object) -> Result[frozenset[Fingerprint]]:
    if value is None or value == ():
        return Ok(frozenset())
    if isinstance(value, Fingerprint):
        return Ok(frozenset({value}))
    if isinstance(value, ExitRecord):
        return Ok(frozenset({value.virtual_position_ref}))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "closed_refs",
            "closed_refs is a sequence of virtual-position fingerprints already closed",
            given=repr(type(value).__name__),
        )
    refs: list[Fingerprint] = []
    for index, raw in enumerate(cast("Sequence[object]", value)):
        if isinstance(raw, ExitRecord):
            refs.append(raw.virtual_position_ref)
        elif isinstance(raw, Fingerprint):
            refs.append(raw)
        else:
            return invalid(
                "closed_refs",
                "each closed ref is a Fingerprint or a prior CT-29 ExitRecord",
                index=index,
                given=repr(type(raw).__name__),
            )
    return Ok(frozenset(refs))


def _as_fill_decision(value: Fill | NoFill | PartialFill) -> Result[Fill | NoFill | PartialFill]:
    return Ok(value)


def _as_outcome(value: CostedFill | NoFill) -> Result[CostedFill | NoFill]:
    return Ok(value)


def _floor_to_step(magnitude: Fraction, step: Quantity) -> Result[Quantity]:
    step_mag = step.as_fraction()
    units = magnitude / step_mag
    snapped = step_mag * (units.numerator // units.denominator)
    scale = step.scale
    scaled = snapped * (10**scale)
    if scaled.denominator != 1:
        return invalid(
            "lot_step",
            "the lot-step snap must land on an exact scaled integer Quantity",
            given=str(snapped),
        )
    return Quantity.try_create(int(scaled), step.unit, scale)


def _classify_decision(
    decision: object,
    *,
    requested: Quantity,
    position_cap: Quantity,
    lot_step: Quantity,
) -> Result[Fill | NoFill | PartialFill]:
    if isinstance(decision, NoFill):
        if decision.taint != TAINT_OPTIMISTIC:
            return policy(
                "taint",
                "until GAP-0048 every fill carries the optimistic taint (B-6, SC-06)",
                given=decision.taint,
                gap="GAP-0048",
            )
        return _as_fill_decision(decision)
    if isinstance(decision, (Fill, PartialFill)):
        return classify_fill_quantity(
            requested=requested,
            filled=decision.quantity,
            position_cap=position_cap,
            lot_step=lot_step,
            pre_slip_price=decision.pre_slip_price,
            post_slip_price=decision.post_slip_price,
        )
    return invalid(
        "fill",
        "the fill port decides Fill, NoFill, or PartialFill; partial quantities "
        "are first-class (B-6, AR-56)",
        given=repr(type(decision).__name__),
        allowed=list(FILL_DECISIONS),
    )


def _quantity_changed(
    before: Fill | PartialFill,
    after: Fill | PartialFill,
) -> Result[None]:
    if before.quantity.as_fraction() != after.quantity.as_fraction():
        return invalid(
            "quantity",
            "slippage and cost map price and cash charges; they never re-size "
            "an authorized intent (B-6, AR-56)",
            before=str(before.quantity.as_fraction()),
            after=str(after.quantity.as_fraction()),
        )
    if before.kind is not after.kind:
        return invalid(
            "kind",
            "slippage and cost preserve Fill versus PartialFill; they never re-size",
            before=before.kind.value,
            after=after.kind.value,
        )
    return Ok(None)


def _require_post_slip(fill: Fill | PartialFill) -> Result[Fill | PartialFill]:
    if fill.post_slip_price is None:
        return invalid(
            "post_slip_price",
            "slippage maps the pre-slip price to a post-slip price before cost itemizes",
        )
    return Ok(fill)
