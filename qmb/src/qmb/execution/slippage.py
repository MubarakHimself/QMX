"""FX slippage catalog (SLIP-1..SLIP-3, Story 17.3).

Maps a pre-slip fill price to a post-slip price (buy ``+``, sell ``−``) or
vetoes with NoFill when the slipped print is not legal on the slice. Passive
limit fills are skipped unless explicitly configured. Calibration content is
never invented; missing parameters are a typed refusal. Stochastic draws use
a per-run seed derived from run identity so replay reproduces the same draw.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Final, cast

from qmf.core.exact import PRICE_STORAGE_SCALE, ExactRational, Price, PriceDelta, Quantity, UnitKind
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.risk.door import Direction

from qmb._refuse import clean_token, invalid, unavailable
from qmb.execution.fidelity import FidelityIdentity, stamp_fidelity
from qmb.execution.fill import FILL_BASIS_KEY
from qmb.execution.ports import (
    COMPOSITION_VERSION,
    TAINT_OPTIMISTIC,
    Fill,
    NoFill,
    PartialFill,
    SlicePath,
    restamp_filled,
)

__all__ = [
    "SLIPPAGE_ADAPTER_CONSTANT_PERCENT",
    "SLIPPAGE_ADAPTER_GAP_VOLATILITY",
    "SLIPPAGE_ADAPTER_SIZE_TIERED",
    "SLIPPAGE_ADAPTER_SPREAD_CROSSING",
    "SLIPPAGE_ADAPTER_ZERO",
    "SLIPPAGE_APPLY_TO_PASSIVE_KEY",
    "SLIPPAGE_CALIBRATION_KEY",
    "SLIPPAGE_MODELS",
    "SLIPPAGE_SEED_KEY",
    "ConstantPercentSlippageAdapter",
    "GapVolatilitySlippageAdapter",
    "SizeTieredSlippageAdapter",
    "SlippageCalibration",
    "SpreadCrossingSlippageAdapter",
    "ZeroSlippageAdapter",
    "derive_slippage_seed",
    "legal_print",
    "slip_fill",
    "slippage_identity",
]

SLIPPAGE_ADAPTER_ZERO: Final[str] = "zero"
SLIPPAGE_ADAPTER_CONSTANT_PERCENT: Final[str] = "constant-percent"
SLIPPAGE_ADAPTER_SPREAD_CROSSING: Final[str] = "spread-crossing"
SLIPPAGE_ADAPTER_GAP_VOLATILITY: Final[str] = "gap-volatility"
SLIPPAGE_ADAPTER_SIZE_TIERED: Final[str] = "size-tiered"
SLIPPAGE_MODELS: Final[tuple[str, ...]] = (
    SLIPPAGE_ADAPTER_ZERO,
    SLIPPAGE_ADAPTER_CONSTANT_PERCENT,
    SLIPPAGE_ADAPTER_SPREAD_CROSSING,
    SLIPPAGE_ADAPTER_GAP_VOLATILITY,
    SLIPPAGE_ADAPTER_SIZE_TIERED,
)
SLIPPAGE_CALIBRATION_KEY: Final[str] = "slippage_calibration"
SLIPPAGE_APPLY_TO_PASSIVE_KEY: Final[str] = "slippage_apply_to_passive_limits"
SLIPPAGE_SEED_KEY: Final[str] = "slippage_seed"
_LEGAL_PRINT: Final[str] = "illegal-print"


def slippage_identity() -> dict[str, object]:
    """Identity-bearing slippage-pipeline fields. Package SemVer is omitted."""
    return {
        "apply_to_passive_key": SLIPPAGE_APPLY_TO_PASSIVE_KEY,
        "calibration_key": SLIPPAGE_CALIBRATION_KEY,
        "fill_basis_key": FILL_BASIS_KEY,
        "models": SLIPPAGE_MODELS,
        "passive_limits_default": False,
        "seed_key": SLIPPAGE_SEED_KEY,
        "taint_field": TAINT_OPTIMISTIC,
        "veto_illegal_print": True,
    }


def derive_slippage_seed(run_identity: object, *parts: object) -> Result[int]:
    """Per-run seed from run identity so replay reproduces the same draw (SLIP-3)."""
    payload: dict[str, object] = {"class": "slippage-seed", "run": _identity_token(run_identity)}
    if parts:
        payload["parts"] = [_identity_token(item) for item in parts]
    stamped = fingerprint(payload)
    if is_refusal(stamped):
        return stamped
    digest = stamped.value.value.rsplit(":", 1)[-1]
    return Ok(int(digest[:16], 16))


@dataclass(frozen=True, slots=True)
class SlippageCalibration:
    """Versioned per-broker slippage parameters. Content is never invented (SC-07)."""

    model: str
    broker_id: str
    format_version: int
    fingerprint: Fingerprint
    percent: ExactRational | None = None
    spread_fraction: ExactRational | None = None
    range_fraction: ExactRational | None = None
    spread: PriceDelta | None = None
    bid: Price | None = None
    ask: Price | None = None
    tiers: tuple[tuple[Quantity, PriceDelta], ...] = ()

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. The derived fingerprint is omitted."""
        content: dict[str, object] = {
            "broker_id": self.broker_id,
            "class": "slippage-calibration",
            "format_version": self.format_version,
            "model": self.model,
            "per_broker": True,
        }
        if self.percent is not None:
            content["percent"] = self.percent.fp1_identity()
        if self.spread_fraction is not None:
            content["spread_fraction"] = self.spread_fraction.fp1_identity()
        if self.range_fraction is not None:
            content["range_fraction"] = self.range_fraction.fp1_identity()
        if self.spread is not None:
            content["spread"] = self.spread.fp1_identity()
        if self.bid is not None:
            content["bid"] = self.bid.fp1_identity()
        if self.ask is not None:
            content["ask"] = self.ask.fp1_identity()
        if self.tiers:
            content["tiers"] = [
                {"quantity": qty.fp1_identity(), "offset": offset.fp1_identity()}
                for qty, offset in self.tiers
            ]
        return content

    @classmethod
    def try_create(
        cls,
        model: object,
        broker_id: object,
        *,
        format_version: object = 1,
        percent: object = None,
        spread_fraction: object = None,
        range_fraction: object = None,
        spread: object = None,
        bid: object = None,
        ask: object = None,
        tiers: object = (),
        cited_fingerprint: object = None,
    ) -> Result[SlippageCalibration]:
        """Build a fingerprinted calibration. No default numeric content is filled in."""
        token = clean_token(model)
        if token not in SLIPPAGE_MODELS:
            return invalid(
                "model",
                "slippage model is zero, constant-percent, spread-crossing, "
                "gap-volatility, or size-tiered (SLIP-2)",
                given=repr(model),
                allowed=list(SLIPPAGE_MODELS),
            )
        broker = clean_token(broker_id)
        if broker is None:
            return invalid(
                "broker_id",
                "a slippage calibration is per-broker (DEC-0135)",
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
        pct = _optional_ratio(percent, "percent")
        if is_refusal(pct):
            return pct
        frac = _optional_ratio(spread_fraction, "spread_fraction")
        if is_refusal(frac):
            return frac
        rfrac = _optional_ratio(range_fraction, "range_fraction")
        if is_refusal(rfrac):
            return rfrac
        delta = _optional_delta(spread, "spread")
        if is_refusal(delta):
            return delta
        left = _optional_price(bid, "bid")
        if is_refusal(left):
            return left
        right = _optional_price(ask, "ask")
        if is_refusal(right):
            return right
        parsed_tiers = _as_tiers(tiers)
        if is_refusal(parsed_tiers):
            return parsed_tiers
        pending = cls(
            model=token,
            broker_id=broker,
            format_version=format_version,
            fingerprint=Fingerprint(value="fp1:sha256:" + ("0" * 64)),
            percent=pct.value,
            spread_fraction=frac.value,
            range_fraction=rfrac.value,
            spread=delta.value,
            bid=left.value,
            ask=right.value,
            tiers=parsed_tiers.value,
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
                percent=pending.percent,
                spread_fraction=pending.spread_fraction,
                range_fraction=pending.range_fraction,
                spread=pending.spread,
                bid=pending.bid,
                ask=pending.ask,
                tiers=pending.tiers,
            )
        )


def legal_print(price: object, path: object) -> Result[bool]:
    """Whether ``price`` is a legal print on the slice (low..high or a path print)."""
    if not isinstance(price, Price):
        return invalid(
            "price",
            "a legal-print test consumes an exact Price",
            given=repr(type(price).__name__),
        )
    if not isinstance(path, SlicePath):
        return invalid(
            "path",
            "legal prints are judged against the declared SlicePath",
            given=repr(type(path).__name__),
        )
    magnitude = price.as_fraction()
    for print_ in path.prints:
        if print_.as_fraction() == magnitude:
            return Ok(True)
    high = path.high
    low = path.low
    if high is None or low is None:
        if path.prints:
            high = max(path.prints, key=lambda item: item.as_fraction())
            low = min(path.prints, key=lambda item: item.as_fraction())
        else:
            return Ok(False)
    return Ok(low.as_fraction() <= magnitude <= high.as_fraction())


def slip_fill(
    fill: Fill | PartialFill,
    path: SlicePath,
    *,
    model: str,
    calibration: SlippageCalibration | None,
    apply_to_passive_limits: bool,
    seed: int | None = None,
) -> Result[Fill | NoFill | PartialFill]:
    """Map pre-slip → post-slip or veto. Never resizes."""
    del seed
    if fill.passive and not apply_to_passive_limits:
        return _as_slip(restamp_filled(fill, post_slip_price=fill.pre_slip_price))
    if model == SLIPPAGE_ADAPTER_ZERO:
        return _as_slip(restamp_filled(fill, post_slip_price=fill.pre_slip_price))
    offset = _offset_for(model, fill, path, calibration)
    if is_refusal(offset):
        return offset
    slipped = _apply_offset(fill.pre_slip_price, offset.value, side=fill.side)
    if is_refusal(slipped):
        return slipped
    legal = legal_print(slipped.value, path)
    if is_refusal(legal):
        return legal
    if not legal.value:
        none = NoFill.try_create(_LEGAL_PRINT)
        if is_refusal(none):
            return none
        vetoed: Fill | NoFill | PartialFill = none.value
        return Ok(vetoed)
    return _as_slip(restamp_filled(fill, post_slip_price=slipped.value))


def _as_slip(
    stamped: Result[Fill | PartialFill],
) -> Result[Fill | NoFill | PartialFill]:
    if is_refusal(stamped):
        return stamped
    decision: Fill | NoFill | PartialFill = stamped.value
    return Ok(decision)


@dataclass(frozen=True, slots=True)
class ZeroSlippageAdapter:
    """Named ``zero`` slippage shape (SLIP-2). Post-slip equals pre-slip."""

    adapter_id: str = SLIPPAGE_ADAPTER_ZERO
    composition_version: int = COMPOSITION_VERSION
    taint: str = TAINT_OPTIMISTIC
    calibration: SlippageCalibration | None = None
    apply_to_passive_limits: bool = False
    seed: int | None = None

    def fidelity(self) -> Result[FidelityIdentity]:
        """Stamp adapter-id + composition-version + optimistic taint."""
        return stamp_fidelity(
            f"slippage.{self.adapter_id}",
            composition_version=self.composition_version,
        )

    def apply(
        self,
        fill: Fill | PartialFill,
        path: SlicePath,
    ) -> Result[Fill | NoFill | PartialFill]:
        """Map pre-slip to post-slip with no invented offset; never resize."""
        return slip_fill(
            fill,
            path,
            model=SLIPPAGE_ADAPTER_ZERO,
            calibration=self.calibration,
            apply_to_passive_limits=self.apply_to_passive_limits,
            seed=self.seed,
        )


@dataclass(frozen=True, slots=True)
class ConstantPercentSlippageAdapter:
    """LEAN-shaped constant percent-of-price (SLIP-2). Requires calibration."""

    adapter_id: str = SLIPPAGE_ADAPTER_CONSTANT_PERCENT
    composition_version: int = COMPOSITION_VERSION
    taint: str = TAINT_OPTIMISTIC
    calibration: SlippageCalibration | None = None
    apply_to_passive_limits: bool = False
    seed: int | None = None

    def fidelity(self) -> Result[FidelityIdentity]:
        """Stamp adapter-id + composition-version + calibration ref + taint."""
        ref = None if self.calibration is None else self.calibration.fingerprint.value
        return stamp_fidelity(
            f"slippage.{self.adapter_id}",
            composition_version=self.composition_version,
            calibration_ref=ref,
        )

    def apply(
        self,
        fill: Fill | PartialFill,
        path: SlicePath,
    ) -> Result[Fill | NoFill | PartialFill]:
        """Buy +, sell − by the calibrated percent of pre-slip price."""
        return slip_fill(
            fill,
            path,
            model=SLIPPAGE_ADAPTER_CONSTANT_PERCENT,
            calibration=self.calibration,
            apply_to_passive_limits=self.apply_to_passive_limits,
            seed=self.seed,
        )


@dataclass(frozen=True, slots=True)
class SpreadCrossingSlippageAdapter:
    """Retail-FX default: a calibrated fraction of the current spread (SLIP-2)."""

    adapter_id: str = SLIPPAGE_ADAPTER_SPREAD_CROSSING
    composition_version: int = COMPOSITION_VERSION
    taint: str = TAINT_OPTIMISTIC
    calibration: SlippageCalibration | None = None
    apply_to_passive_limits: bool = False
    seed: int | None = None

    def fidelity(self) -> Result[FidelityIdentity]:
        """Stamp adapter-id + composition-version + calibration ref + taint."""
        ref = None if self.calibration is None else self.calibration.fingerprint.value
        return stamp_fidelity(
            f"slippage.{self.adapter_id}",
            composition_version=self.composition_version,
            calibration_ref=ref,
        )

    def apply(
        self,
        fill: Fill | PartialFill,
        path: SlicePath,
    ) -> Result[Fill | NoFill | PartialFill]:
        """Offset by spread × fraction; missing spread/calibration refuses."""
        return slip_fill(
            fill,
            path,
            model=SLIPPAGE_ADAPTER_SPREAD_CROSSING,
            calibration=self.calibration,
            apply_to_passive_limits=self.apply_to_passive_limits,
            seed=self.seed,
        )


@dataclass(frozen=True, slots=True)
class GapVolatilitySlippageAdapter:
    """Widens with bar range (news spikes / stop-runs) (SLIP-2)."""

    adapter_id: str = SLIPPAGE_ADAPTER_GAP_VOLATILITY
    composition_version: int = COMPOSITION_VERSION
    taint: str = TAINT_OPTIMISTIC
    calibration: SlippageCalibration | None = None
    apply_to_passive_limits: bool = False
    seed: int | None = None

    def fidelity(self) -> Result[FidelityIdentity]:
        """Stamp adapter-id + composition-version + calibration ref + taint."""
        ref = None if self.calibration is None else self.calibration.fingerprint.value
        return stamp_fidelity(
            f"slippage.{self.adapter_id}",
            composition_version=self.composition_version,
            calibration_ref=ref,
        )

    def apply(
        self,
        fill: Fill | PartialFill,
        path: SlicePath,
    ) -> Result[Fill | NoFill | PartialFill]:
        """Offset by bar-range × calibrated fraction."""
        return slip_fill(
            fill,
            path,
            model=SLIPPAGE_ADAPTER_GAP_VOLATILITY,
            calibration=self.calibration,
            apply_to_passive_limits=self.apply_to_passive_limits,
            seed=self.seed,
        )


@dataclass(frozen=True, slots=True)
class SizeTieredSlippageAdapter:
    """Volume-free size tiers (SLIP-2). Offset steps up with order quantity."""

    adapter_id: str = SLIPPAGE_ADAPTER_SIZE_TIERED
    composition_version: int = COMPOSITION_VERSION
    taint: str = TAINT_OPTIMISTIC
    calibration: SlippageCalibration | None = None
    apply_to_passive_limits: bool = False
    seed: int | None = None

    def fidelity(self) -> Result[FidelityIdentity]:
        """Stamp adapter-id + composition-version + calibration ref + taint."""
        ref = None if self.calibration is None else self.calibration.fingerprint.value
        return stamp_fidelity(
            f"slippage.{self.adapter_id}",
            composition_version=self.composition_version,
            calibration_ref=ref,
        )

    def apply(
        self,
        fill: Fill | PartialFill,
        path: SlicePath,
    ) -> Result[Fill | NoFill | PartialFill]:
        """Pick the first tier whose quantity ceiling covers the fill."""
        return slip_fill(
            fill,
            path,
            model=SLIPPAGE_ADAPTER_SIZE_TIERED,
            calibration=self.calibration,
            apply_to_passive_limits=self.apply_to_passive_limits,
            seed=self.seed,
        )


def _offset_for(
    model: str,
    fill: Fill | PartialFill,
    path: SlicePath,
    calibration: SlippageCalibration | None,
) -> Result[PriceDelta]:
    if calibration is None:
        return unavailable(
            "slippage_calibration",
            "non-zero FX slippage is parameterized by a versioned per-broker "
            "calibration artifact; absence never invents a number (SLIP-2, SC-07)",
            model=model,
            gap="GAP-0048",
        )
    if calibration.model != model:
        return invalid(
            "slippage_calibration",
            "calibration model must match the bound slippage adapter",
            bound=model,
            given=calibration.model,
        )
    if model == SLIPPAGE_ADAPTER_CONSTANT_PERCENT:
        if calibration.percent is None:
            return unavailable(
                "percent",
                "constant-percent slippage reads percent from its calibration artifact",
                gap="GAP-0048",
            )
        return _percent_offset(fill.pre_slip_price, calibration.percent.as_fraction())
    if model == SLIPPAGE_ADAPTER_SPREAD_CROSSING:
        spread = _spread_delta(path, calibration)
        if is_refusal(spread):
            return spread
        if calibration.spread_fraction is None:
            return unavailable(
                "spread_fraction",
                "spread-crossing slippage reads its fraction from the calibration artifact",
                gap="GAP-0048",
            )
        return _scale_delta(spread.value, calibration.spread_fraction.as_fraction())
    if model == SLIPPAGE_ADAPTER_GAP_VOLATILITY:
        if calibration.range_fraction is None:
            return unavailable(
                "range_fraction",
                "gap-volatility slippage reads range_fraction from its calibration artifact",
                gap="GAP-0048",
            )
        bar_range = _bar_range(path, fill.pre_slip_price)
        if is_refusal(bar_range):
            return bar_range
        return _scale_delta(bar_range.value, calibration.range_fraction.as_fraction())
    if model == SLIPPAGE_ADAPTER_SIZE_TIERED:
        if not calibration.tiers:
            return unavailable(
                "tiers",
                "size-tiered slippage reads quantity ceilings from its calibration artifact",
                gap="GAP-0048",
            )
        qty = fill.quantity.as_fraction()
        for ceiling, offset in calibration.tiers:
            if qty <= ceiling.as_fraction():
                return Ok(offset)
        return Ok(calibration.tiers[-1][1])
    return invalid("model", "unknown slippage model", given=model)


def _apply_offset(
    price: Price,
    offset: PriceDelta,
    *,
    side: Direction | None,
) -> Result[Price]:
    if side is None:
        return invalid(
            "side",
            "slippage buy + / sell - needs the fill's Direction (SLIP-1)",
        )
    delta = (
        offset
        if side is Direction.LONG
        else PriceDelta(
            value=-offset.value,
            instrument=offset.instrument,
            scale=offset.scale,
        )
    )
    return price.add(delta)


def _percent_offset(price: Price, percent: Fraction) -> Result[PriceDelta]:
    if percent < 0:
        return invalid("percent", "a slippage percent is a non-negative exact ratio")
    mag = price.as_fraction() * percent
    return _delta_from_fraction(mag, price)


def _scale_delta(delta: PriceDelta, fraction: Fraction) -> Result[PriceDelta]:
    if fraction < 0:
        return invalid("fraction", "a slippage fraction is a non-negative exact ratio")
    mag = abs(delta.as_fraction()) * fraction
    return _delta_from_fraction(mag, delta)


def _delta_from_fraction(
    magnitude: Fraction,
    sample: Price | PriceDelta,
) -> Result[PriceDelta]:
    for scale in range(sample.scale, PRICE_STORAGE_SCALE + 1):
        scaled = magnitude * (10**scale)
        if scaled.denominator == 1:
            return PriceDelta.try_create(int(scaled), sample.instrument, scale)
    return invalid(
        "offset",
        "a slippage offset must land on an exact scaled-integer PriceDelta",
        given=str(magnitude),
    )


def _spread_delta(path: SlicePath, calibration: SlippageCalibration) -> Result[PriceDelta]:
    if calibration.spread is not None:
        return Ok(calibration.spread)
    bid = path.bid if path.bid is not None else calibration.bid
    ask = path.ask if path.ask is not None else calibration.ask
    if bid is None or ask is None:
        return unavailable(
            "spread",
            "spread-crossing slippage needs bid/ask on the path or in the calibration "
            "artifact; absence never invents a spread (SLIP-2, SC-07)",
            gap="GAP-0048",
        )
    return ask.subtract(bid)


def _bar_range(path: SlicePath, sample: Price) -> Result[PriceDelta]:
    high = path.high
    low = path.low
    if high is None or low is None:
        if not path.prints:
            return invalid(
                "path",
                "gap-volatility slippage needs OHLC or prints to measure bar range",
            )
        high = max(path.prints, key=lambda item: item.as_fraction())
        low = min(path.prints, key=lambda item: item.as_fraction())
    return high.subtract(low)


def _optional_ratio(value: object, field: str) -> Result[ExactRational | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, ExactRational):
        if value.unit_kind is not UnitKind.DIMENSIONLESS_RATIO:
            return invalid(
                field,
                "a slippage ratio is an ExactRational with unit-kind dimensionless-ratio",
                given=value.unit_kind.value,
            )
        return Ok(value)
    return invalid(
        field,
        "a slippage ratio is an ExactRational, never a binary float",
        given=repr(type(value).__name__),
    )


def _optional_delta(value: object, field: str) -> Result[PriceDelta | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, PriceDelta):
        return Ok(value)
    return invalid(
        field,
        "a slippage offset is an exact PriceDelta",
        given=repr(type(value).__name__),
    )


def _optional_price(value: object, field: str) -> Result[Price | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, Price):
        return Ok(value)
    return invalid(field, "a quote is an exact Price", given=repr(type(value).__name__))


def _as_tiers(value: object) -> Result[tuple[tuple[Quantity, PriceDelta], ...]]:
    if value is None or value == ():
        return Ok(())
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "tiers",
            "size-tiered calibration is a sequence of (quantity, PriceDelta) pairs",
            given=repr(type(value).__name__),
        )
    parsed: list[tuple[Quantity, PriceDelta]] = []
    for index, raw in enumerate(cast("Sequence[object]", value)):
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            return invalid(
                "tiers",
                "each size tier is (quantity ceiling, PriceDelta offset)",
                index=index,
            )
        pair = cast("Sequence[object]", raw)
        if len(pair) != 2:
            return invalid(
                "tiers",
                "each size tier is (quantity ceiling, PriceDelta offset)",
                index=index,
            )
        qty, offset = pair[0], pair[1]
        if not isinstance(qty, Quantity) or not isinstance(offset, PriceDelta):
            return invalid(
                "tiers",
                "each size tier is an exact Quantity ceiling and PriceDelta offset",
                index=index,
            )
        parsed.append((qty, offset))
    return Ok(tuple(parsed))


def _identity_token(value: object) -> object:
    if isinstance(value, Fingerprint):
        return value.value
    identity = getattr(value, "fp1_identity", None)
    if callable(identity):
        return identity()
    if isinstance(value, str):
        return value
    return repr(type(value).__name__)
