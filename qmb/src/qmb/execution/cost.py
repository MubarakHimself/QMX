"""Exact-integer itemized commissions (FEE-1..FEE-3, FEE-5, Story 17.4).

The cost port returns a typed fee in its own currency as ``Money``. Each
partial carries its own pro-rated commission line, never folded into fill
P&L. Catalog shapes are parameterized by a versioned per-broker calibration
whose rate content is deferred to GAP-0048 — missing calibration is a typed
refusal, never a silent zero. Admission query and fill-time charge share one
formula, so the same inputs return the identical amount.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType
from typing import Final

from qmf.core.exact import (
    MAX_SCALE,
    MONEY_STORAGE_SCALE,
    ExactRational,
    Money,
    PriceDelta,
    Quantity,
    UnitKind,
    ValueFactor,
)
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.risk.exit_record import CostComponent

from qmb._refuse import clean_token, invalid, unavailable
from qmb.execution.fidelity import FidelityIdentity, stamp_fidelity
from qmb.execution.ports import (
    COMPOSITION_VERSION,
    TAINT_OPTIMISTIC,
    CostedFill,
    CostPort,
    Fill,
    PartialFill,
)

__all__ = [
    "COST_ADAPTER_CATALOG",
    "COST_ADAPTER_NOTIONAL_MINIMUM",
    "COST_ADAPTER_PERCENT_OF_NOTIONAL",
    "COST_ADAPTER_PER_LOT",
    "COST_ADAPTER_ZERO",
    "COST_CALIBRATION_KEY",
    "COST_COMPONENT_COMMISSION",
    "COST_CONTENT_DEFERRED_TO",
    "COST_MODELS",
    "CommissionCalibration",
    "NotionalProportionalMinimumCostAdapter",
    "PerLotCostAdapter",
    "PercentOfNotionalCostAdapter",
    "ZeroCostAdapter",
    "charge_commission",
    "cost_identity",
    "fingerprint_cost",
    "itemize_commission",
]

COST_ADAPTER_ZERO: Final[str] = "zero"
COST_ADAPTER_PERCENT_OF_NOTIONAL: Final[str] = "percent-of-notional"
COST_ADAPTER_PER_LOT: Final[str] = "per-lot/per-1k-units"
COST_ADAPTER_NOTIONAL_MINIMUM: Final[str] = "notional-proportional-with-per-order-minimum"
COST_MODELS: Final[tuple[str, ...]] = (
    COST_ADAPTER_ZERO,
    COST_ADAPTER_PERCENT_OF_NOTIONAL,
    COST_ADAPTER_PER_LOT,
    COST_ADAPTER_NOTIONAL_MINIMUM,
)
COST_CALIBRATION_KEY: Final[str] = "cost_calibration"
COST_COMPONENT_COMMISSION: Final[str] = "commission"
COST_CONTENT_DEFERRED_TO: Final[str] = "GAP-0048"
_ZERO_CURRENCY: Final[str] = "USD"
_ZERO_SCALE: Final[int] = 2
_PER_1K: Final[Fraction] = Fraction(1000)


def cost_identity() -> dict[str, object]:
    """Identity-bearing cost-port fields. Package SemVer is omitted."""
    return {
        "admission_matches_charge": True,
        "calibration_key": COST_CALIBRATION_KEY,
        "component_name": COST_COMPONENT_COMMISSION,
        "content_deferred_to": COST_CONTENT_DEFERRED_TO,
        "folded_into_fill_pnl": False,
        "models": COST_MODELS,
        "per_broker": True,
        "silent_zero_on_missing_calibration": False,
        "taint_field": TAINT_OPTIMISTIC,
    }


def fingerprint_cost() -> Result[Fingerprint]:
    """``fp1`` over :func:`cost_identity`."""
    return fingerprint(cost_identity())


@dataclass(frozen=True, slots=True)
class CommissionCalibration:
    """Versioned per-broker commission parameters. Rates are never invented (SC-07)."""

    model: str
    broker_id: str
    format_version: int
    fingerprint: Fingerprint
    currency: str | None = None
    percent: ExactRational | None = None
    per_lot: Money | None = None
    per_1k_units: Money | None = None
    units_per_lot: Quantity | ExactRational | None = None
    minimum: Money | None = None
    value_factor: ValueFactor | None = None
    money_scale: int | None = None

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. The derived fingerprint is omitted."""
        content: dict[str, object] = {
            "broker_id": self.broker_id,
            "class": "commission-calibration",
            "format_version": self.format_version,
            "model": self.model,
            "per_broker": True,
        }
        if self.currency is not None:
            content["currency"] = self.currency
        if self.percent is not None:
            content["percent"] = self.percent.fp1_identity()
        if self.per_lot is not None:
            content["per_lot"] = self.per_lot.fp1_identity()
        if self.per_1k_units is not None:
            content["per_1k_units"] = self.per_1k_units.fp1_identity()
        if self.units_per_lot is not None:
            content["units_per_lot"] = self.units_per_lot.fp1_identity()
        if self.minimum is not None:
            content["minimum"] = self.minimum.fp1_identity()
        if self.value_factor is not None:
            content["value_factor"] = self.value_factor.fp1_identity()
        if self.money_scale is not None:
            content["money_scale"] = self.money_scale
        return content

    @classmethod
    def try_create(
        cls,
        model: object,
        broker_id: object,
        *,
        format_version: object = 1,
        currency: object = None,
        percent: object = None,
        per_lot: object = None,
        per_1k_units: object = None,
        units_per_lot: object = None,
        minimum: object = None,
        value_factor: object = None,
        money_scale: object = None,
        cited_fingerprint: object = None,
    ) -> Result[CommissionCalibration]:
        """Build a fingerprinted calibration. No default numeric content is filled in."""
        token = clean_token(model)
        if token not in COST_MODELS:
            return invalid(
                "model",
                "commission model is zero, percent-of-notional, per-lot/per-1k-units, "
                "or notional-proportional-with-per-order-minimum (FEE-2)",
                given=repr(model),
                allowed=list(COST_MODELS),
            )
        broker = clean_token(broker_id)
        if broker is None:
            return invalid(
                "broker_id",
                "a commission calibration is per-broker (DEC-0135)",
                given=repr(broker_id),
            )
        if (
            not isinstance(format_version, int)
            or isinstance(format_version, bool)
            or format_version < 1
        ):
            return invalid(
                "format_version",
                "calibration format version is a positive integer",
                given=repr(format_version),
            )
        tagged = _optional_currency(currency)
        if is_refusal(tagged):
            return tagged
        pct = _optional_ratio(percent, "percent")
        if is_refusal(pct):
            return pct
        lot_fee = _optional_money(per_lot, "per_lot")
        if is_refusal(lot_fee):
            return lot_fee
        per_1k = _optional_money(per_1k_units, "per_1k_units")
        if is_refusal(per_1k):
            return per_1k
        units = _optional_units(units_per_lot)
        if is_refusal(units):
            return units
        floor = _optional_money(minimum, "minimum")
        if is_refusal(floor):
            return floor
        factor = _optional_value_factor(value_factor)
        if is_refusal(factor):
            return factor
        scale = _optional_scale(money_scale)
        if is_refusal(scale):
            return scale
        if lot_fee.value is not None and per_1k.value is not None:
            return invalid(
                "cost_calibration",
                "per-lot and per-1k-units are alternate parameterizations of one shape",
            )
        currency_token = tagged.value
        for field, amount in (
            ("per_lot", lot_fee.value),
            ("per_1k_units", per_1k.value),
            ("minimum", floor.value),
        ):
            checked = _currency_agrees(currency_token, amount, field)
            if is_refusal(checked):
                return checked
            if currency_token is None and amount is not None:
                currency_token = amount.currency
        if factor.value is not None:
            if currency_token is None:
                currency_token = factor.value.currency
            elif factor.value.currency != currency_token:
                return invalid(
                    "currency",
                    "commission currency must match the value-factor currency; "
                    "no silent conversion (FEE-1)",
                    given=currency_token,
                    value_factor=factor.value.currency,
                )
        pending = cls(
            model=token,
            broker_id=broker,
            format_version=format_version,
            fingerprint=Fingerprint(value="fp1:sha256:" + ("0" * 64)),
            currency=currency_token,
            percent=pct.value,
            per_lot=lot_fee.value,
            per_1k_units=per_1k.value,
            units_per_lot=units.value,
            minimum=floor.value,
            value_factor=factor.value,
            money_scale=scale.value,
        )
        if isinstance(cited_fingerprint, Fingerprint):
            stamped = cited_fingerprint
        else:
            derived = fingerprint(pending.fp1_identity())
            if is_refusal(derived):
                return derived
            stamped = derived.value
        return Ok(
            cls(
                model=pending.model,
                broker_id=pending.broker_id,
                format_version=pending.format_version,
                fingerprint=stamped,
                currency=pending.currency,
                percent=pending.percent,
                per_lot=pending.per_lot,
                per_1k_units=pending.per_1k_units,
                units_per_lot=pending.units_per_lot,
                minimum=pending.minimum,
                value_factor=pending.value_factor,
                money_scale=pending.money_scale,
            )
        )


def charge_commission(
    fill: Fill | PartialFill,
    *,
    model: str,
    calibration: CommissionCalibration | None,
) -> Result[Money]:
    """Exact-integer commission in the fee's own currency. Same inputs → same amount."""
    if model == COST_ADAPTER_ZERO:
        return _zero_money(calibration)
    if calibration is None:
        return unavailable(
            "cost_calibration",
            "non-zero commission is parameterized by a versioned per-broker "
            "calibration artifact; absence never silently zeros (FEE-1, B-6, SC-07)",
            model=model,
            gap=COST_CONTENT_DEFERRED_TO,
        )
    if calibration.model != model:
        return invalid(
            "cost_calibration",
            "calibration model must match the bound cost adapter",
            bound=model,
            given=calibration.model,
        )
    if model == COST_ADAPTER_PERCENT_OF_NOTIONAL:
        return _percent_of_notional(fill, calibration)
    if model == COST_ADAPTER_PER_LOT:
        return _per_lot_or_1k(fill, calibration)
    if model == COST_ADAPTER_NOTIONAL_MINIMUM:
        return _notional_with_minimum(fill, calibration)
    return invalid(
        "model",
        "commission model is zero, percent-of-notional, per-lot/per-1k-units, "
        "or notional-proportional-with-per-order-minimum (FEE-2)",
        given=model,
        allowed=list(COST_MODELS),
    )


def itemize_commission(
    fill: Fill | PartialFill,
    *,
    model: str,
    calibration: CommissionCalibration | None,
    source: str,
) -> Result[CostedFill]:
    """Wrap the quoted commission as its own cost line. Does not resize the fill."""
    quoted = charge_commission(fill, model=model, calibration=calibration)
    if is_refusal(quoted):
        return quoted
    if model == COST_ADAPTER_ZERO:
        return CostedFill.try_create(fill, ())
    component = CostComponent.try_create(COST_COMPONENT_COMMISSION, quoted.value, source)
    if is_refusal(component):
        return component
    return CostedFill.try_create(fill, (component.value,))


@dataclass(frozen=True, slots=True)
class ZeroCostAdapter:
    """Named ``zero`` commission shape (FEE-2). No invented rate; no silent default."""

    adapter_id: str = COST_ADAPTER_ZERO
    composition_version: int = COMPOSITION_VERSION
    taint: str = TAINT_OPTIMISTIC
    calibration: CommissionCalibration | None = None

    def fidelity(self) -> Result[FidelityIdentity]:
        """Stamp adapter-id + composition-version + optimistic taint."""
        ref = None if self.calibration is None else self.calibration.fingerprint.value
        return stamp_fidelity(
            f"cost.{self.adapter_id}",
            composition_version=self.composition_version,
            calibration_ref=ref,
        )

    def quote(self, fill: Fill | PartialFill) -> Result[Money]:
        """Admission query: named zero, not an absent model."""
        return charge_commission(
            fill,
            model=COST_ADAPTER_ZERO,
            calibration=self.calibration,
        )

    def itemize(self, fill: Fill | PartialFill) -> Result[CostedFill]:
        """Itemize no commission lines — the named zero shape, not an absent model."""
        return itemize_commission(
            fill,
            model=COST_ADAPTER_ZERO,
            calibration=self.calibration,
            source=self.adapter_id,
        )


@dataclass(frozen=True, slots=True)
class PercentOfNotionalCostAdapter:
    """Jesse-shaped percent of fill notional (FEE-2). Requires calibration."""

    adapter_id: str = COST_ADAPTER_PERCENT_OF_NOTIONAL
    composition_version: int = COMPOSITION_VERSION
    taint: str = TAINT_OPTIMISTIC
    calibration: CommissionCalibration | None = None

    def fidelity(self) -> Result[FidelityIdentity]:
        """Stamp adapter-id + composition-version + calibration ref + taint."""
        ref = None if self.calibration is None else self.calibration.fingerprint.value
        return stamp_fidelity(
            f"cost.{self.adapter_id}",
            composition_version=self.composition_version,
            calibration_ref=ref,
        )

    def quote(self, fill: Fill | PartialFill) -> Result[Money]:
        """Admission query: percent × notional in the fee's own currency."""
        return charge_commission(
            fill,
            model=COST_ADAPTER_PERCENT_OF_NOTIONAL,
            calibration=self.calibration,
        )

    def itemize(self, fill: Fill | PartialFill) -> Result[CostedFill]:
        """Fill-time charge: the quoted amount as a commission line."""
        return itemize_commission(
            fill,
            model=COST_ADAPTER_PERCENT_OF_NOTIONAL,
            calibration=self.calibration,
            source=self.adapter_id,
        )


@dataclass(frozen=True, slots=True)
class PerLotCostAdapter:
    """FXCM-shaped per-lot or per-1k-units commission (FEE-2). Requires calibration."""

    adapter_id: str = COST_ADAPTER_PER_LOT
    composition_version: int = COMPOSITION_VERSION
    taint: str = TAINT_OPTIMISTIC
    calibration: CommissionCalibration | None = None

    def fidelity(self) -> Result[FidelityIdentity]:
        """Stamp adapter-id + composition-version + calibration ref + taint."""
        ref = None if self.calibration is None else self.calibration.fingerprint.value
        return stamp_fidelity(
            f"cost.{self.adapter_id}",
            composition_version=self.composition_version,
            calibration_ref=ref,
        )

    def quote(self, fill: Fill | PartialFill) -> Result[Money]:
        """Admission query: per-lot or per-1k-units × this fill's quantity."""
        return charge_commission(
            fill,
            model=COST_ADAPTER_PER_LOT,
            calibration=self.calibration,
        )

    def itemize(self, fill: Fill | PartialFill) -> Result[CostedFill]:
        """Fill-time charge: the quoted amount as a commission line."""
        return itemize_commission(
            fill,
            model=COST_ADAPTER_PER_LOT,
            calibration=self.calibration,
            source=self.adapter_id,
        )


@dataclass(frozen=True, slots=True)
class NotionalProportionalMinimumCostAdapter:
    """IB-shaped max(per-order minimum, percent × notional) (FEE-2). Requires calibration."""

    adapter_id: str = COST_ADAPTER_NOTIONAL_MINIMUM
    composition_version: int = COMPOSITION_VERSION
    taint: str = TAINT_OPTIMISTIC
    calibration: CommissionCalibration | None = None

    def fidelity(self) -> Result[FidelityIdentity]:
        """Stamp adapter-id + composition-version + calibration ref + taint."""
        ref = None if self.calibration is None else self.calibration.fingerprint.value
        return stamp_fidelity(
            f"cost.{self.adapter_id}",
            composition_version=self.composition_version,
            calibration_ref=ref,
        )

    def quote(self, fill: Fill | PartialFill) -> Result[Money]:
        """Admission query: pro-rated per-order minimum vs percent of this fill's notional."""
        return charge_commission(
            fill,
            model=COST_ADAPTER_NOTIONAL_MINIMUM,
            calibration=self.calibration,
        )

    def itemize(self, fill: Fill | PartialFill) -> Result[CostedFill]:
        """Fill-time charge: the quoted amount as a commission line."""
        return itemize_commission(
            fill,
            model=COST_ADAPTER_NOTIONAL_MINIMUM,
            calibration=self.calibration,
            source=self.adapter_id,
        )


COST_ADAPTER_CATALOG: Final[MappingProxyType[str, type[CostPort]]] = MappingProxyType(
    {
        COST_ADAPTER_ZERO: ZeroCostAdapter,
        COST_ADAPTER_PERCENT_OF_NOTIONAL: PercentOfNotionalCostAdapter,
        COST_ADAPTER_PER_LOT: PerLotCostAdapter,
        COST_ADAPTER_NOTIONAL_MINIMUM: NotionalProportionalMinimumCostAdapter,
    }
)


def _zero_money(calibration: CommissionCalibration | None) -> Result[Money]:
    currency = _ZERO_CURRENCY
    scale = _ZERO_SCALE
    if calibration is not None:
        if calibration.currency is not None:
            currency = calibration.currency
        if calibration.money_scale is not None:
            scale = calibration.money_scale
    return Money.try_create(0, currency, scale)


def _percent_of_notional(
    fill: Fill | PartialFill,
    calibration: CommissionCalibration,
) -> Result[Money]:
    if calibration.percent is None:
        return unavailable(
            "percent",
            "percent-of-notional commission reads percent from its calibration "
            "artifact; absence never silently zeros (FEE-1, SC-07)",
            gap=COST_CONTENT_DEFERRED_TO,
        )
    if calibration.percent.as_fraction() < 0:
        return invalid("percent", "a commission percent is a non-negative exact ratio")
    notional = _notional(fill.quantity, fill, calibration)
    if is_refusal(notional):
        return notional
    tagged = _require_currency(calibration)
    if is_refusal(tagged):
        return tagged
    fee = notional.value.as_fraction() * calibration.percent.as_fraction()
    return _money_from_fraction(fee, tagged.value, scale=_scale(calibration, notional.value.scale))


def _per_lot_or_1k(
    fill: Fill | PartialFill,
    calibration: CommissionCalibration,
) -> Result[Money]:
    tagged = _require_currency(calibration)
    if is_refusal(tagged):
        return tagged
    if calibration.per_lot is not None:
        fee = calibration.per_lot.as_fraction() * fill.quantity.as_fraction()
        return _money_from_fraction(
            fee,
            tagged.value,
            scale=_scale(calibration, calibration.per_lot.scale),
        )
    if calibration.per_1k_units is None:
        return unavailable(
            "per_lot",
            "per-lot/per-1k-units commission reads per_lot or per_1k_units from "
            "its calibration artifact; absence never silently zeros (FEE-1, SC-07)",
            gap=COST_CONTENT_DEFERRED_TO,
        )
    if calibration.units_per_lot is None:
        return unavailable(
            "units_per_lot",
            "per-1k-units commission reads units-per-lot from its calibration "
            "artifact; absence never invents a contract size (FEE-2, SC-07)",
            gap=COST_CONTENT_DEFERRED_TO,
        )
    units = fill.quantity.as_fraction() * calibration.units_per_lot.as_fraction()
    fee = calibration.per_1k_units.as_fraction() * units / _PER_1K
    return _money_from_fraction(
        fee,
        tagged.value,
        scale=_scale(calibration, calibration.per_1k_units.scale),
    )


def _notional_with_minimum(
    fill: Fill | PartialFill,
    calibration: CommissionCalibration,
) -> Result[Money]:
    if calibration.percent is None:
        return unavailable(
            "percent",
            "notional-proportional commission reads percent from its calibration "
            "artifact; absence never silently zeros (FEE-1, SC-07)",
            gap=COST_CONTENT_DEFERRED_TO,
        )
    if calibration.minimum is None:
        return unavailable(
            "minimum",
            "notional-proportional commission reads the per-order minimum from "
            "its calibration artifact; absence never silently zeros (FEE-1, SC-07)",
            gap=COST_CONTENT_DEFERRED_TO,
        )
    if calibration.percent.as_fraction() < 0:
        return invalid("percent", "a commission percent is a non-negative exact ratio")
    if calibration.minimum.as_fraction() < 0:
        return invalid("minimum", "a per-order minimum is a non-negative exact Money")
    notional = _notional(fill.quantity, fill, calibration)
    if is_refusal(notional):
        return notional
    tagged = _require_currency(calibration)
    if is_refusal(tagged):
        return tagged
    proportional = notional.value.as_fraction() * calibration.percent.as_fraction()
    ratio = fill.quantity.as_fraction() / fill.requested_quantity.as_fraction()
    prorated_min = calibration.minimum.as_fraction() * ratio
    fee = proportional if proportional >= prorated_min else prorated_min
    return _money_from_fraction(
        fee,
        tagged.value,
        scale=_scale(calibration, calibration.minimum.scale),
    )


def _notional(
    quantity: Quantity,
    fill: Fill | PartialFill,
    calibration: CommissionCalibration,
) -> Result[Money]:
    if calibration.value_factor is None:
        return unavailable(
            "value_factor",
            "notional commission reads the instrument value-factor from its "
            "calibration artifact; absence never invents a conversion (FEE-2, SC-07)",
            gap=COST_CONTENT_DEFERRED_TO,
        )
    price = fill.post_slip_price if fill.post_slip_price is not None else fill.pre_slip_price
    # Price is affine; notional uses a same-tagged PriceDelta of equal magnitude.
    delta = PriceDelta.try_create(price.value, price.instrument, price.scale)
    if is_refusal(delta):
        return delta
    if calibration.money_scale is not None:
        return delta.value.to_money(
            calibration.value_factor,
            quantity,
            scale=calibration.money_scale,
        )
    last: Result[Money] | None = None
    for candidate in range(0, MONEY_STORAGE_SCALE + 1):
        minted = delta.value.to_money(
            calibration.value_factor,
            quantity,
            scale=candidate,
        )
        if not is_refusal(minted):
            return minted
        last = minted
    if last is not None:
        return last
    return invalid("notional", "notional is not exactly representable as Money")


def _require_currency(calibration: CommissionCalibration) -> Result[str]:
    if calibration.currency is not None:
        return Ok(calibration.currency)
    return unavailable(
        "currency",
        "commission is a typed fee in its own currency (FEE-1); the calibration "
        "artifact names that currency",
        gap=COST_CONTENT_DEFERRED_TO,
    )


def _scale(calibration: CommissionCalibration, fallback: int) -> int:
    if calibration.money_scale is not None:
        return calibration.money_scale
    return fallback


def _money_from_fraction(
    amount: Fraction,
    currency: str,
    *,
    scale: int,
) -> Result[Money]:
    if amount < 0:
        return invalid(
            "commission",
            "commission is a non-negative exact-integer Money",
            given=str(amount),
        )
    scaled = amount * (10**scale)
    if scaled.denominator == 1:
        return Money.try_create(scaled.numerator, currency, scale)
    for candidate in range(scale + 1, MONEY_STORAGE_SCALE + 1):
        finer = amount * (10**candidate)
        if finer.denominator == 1:
            return Money.try_create(finer.numerator, currency, candidate)
    return invalid(
        "commission",
        "commission is not exactly representable as scaled-integer Money; "
        "no silent rounding (CT-01, FR-001)",
        amount=str(amount),
        scale=scale,
    )


def _optional_currency(value: object) -> Result[str | None]:
    if value is None:
        return Ok(None)
    token = clean_token(value)
    if token is None:
        return invalid(
            "currency",
            "commission is a typed fee in its own currency (FEE-1)",
            given=repr(value),
        )
    return Ok(token)


def _optional_ratio(value: object, field: str) -> Result[ExactRational | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, ExactRational):
        if value.unit_kind is not UnitKind.DIMENSIONLESS_RATIO:
            return invalid(
                field,
                "a commission ratio is an ExactRational with unit-kind dimensionless-ratio",
                given=value.unit_kind.value,
            )
        return Ok(value)
    return invalid(
        field,
        "a commission ratio is an ExactRational, never a binary float",
        given=repr(type(value).__name__),
    )


def _optional_money(value: object, field: str) -> Result[Money | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, Money):
        return Ok(value)
    return invalid(
        field,
        "a commission amount is exact-integer Money, never a binary float",
        given=repr(type(value).__name__),
    )


def _optional_value_factor(value: object) -> Result[ValueFactor | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, ValueFactor):
        return Ok(value)
    return invalid(
        "value_factor",
        "a value-factor is a ValueFactor from instrument metadata, never a binary float",
        given=repr(type(value).__name__),
    )


def _optional_units(value: object) -> Result[Quantity | ExactRational | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, Quantity):
        return Ok(value)
    if isinstance(value, ExactRational):
        if value.unit_kind not in (UnitKind.COUNT, UnitKind.DIMENSIONLESS_RATIO):
            return invalid(
                "units_per_lot",
                "units-per-lot is a Quantity or an ExactRational count/ratio",
                given=value.unit_kind.value,
            )
        return Ok(value)
    return invalid(
        "units_per_lot",
        "units-per-lot is an exact Quantity or ExactRational, never a binary float",
        given=repr(type(value).__name__),
    )


def _optional_scale(value: object) -> Result[int | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, bool) or not isinstance(value, int):
        return invalid(
            "money_scale",
            "money scale is a non-negative integer, never a binary float",
            given=repr(type(value).__name__),
        )
    if value < 0 or value > MAX_SCALE:
        return invalid(
            "money_scale",
            "money scale is a non-negative integer at or below MAX_SCALE",
            given=value,
        )
    return Ok(value)


def _currency_agrees(currency: str | None, amount: Money | None, field: str) -> Result[None]:
    if currency is None or amount is None or amount.currency == currency:
        return Ok(None)
    return invalid(
        field,
        "commission Money is denominated in the calibration's own currency; "
        "no silent conversion (FEE-1)",
        given=amount.currency,
        currency=currency,
    )
