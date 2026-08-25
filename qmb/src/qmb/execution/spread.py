"""Synthetic-spread model and SQS spread input (B-6, B-2, Story 17.2).

Trade-only bars obtain bid/ask from a versioned, fingerprinted per-broker
calibration artifact keyed instrument × hour-of-day (UTC) × session. Real
quotes take precedence. Absence is a typed refusal, never a silent zero
spread and never buy=sell. Calibration *content* stays deferred to GAP-0048
— this module never invents spread numbers. Non-live SQS (AD-39) consumes
this run's modeled-spread series of exact Prices. The calibration fingerprint
is declared on the CT-32 result label (B-10, B-13, AR-59).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.chrono import Instant
from qmf.core.exact import Price
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.identity import Instrument
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.risk.door import Direction

from qmb._refuse import clean_token, invalid, policy, unavailable
from qmb.config.compiler import ResolvedRunConfig
from qmb.execution.fidelity import FidelityIdentity, stamp_fidelity
from qmb.execution.ports import COMPOSITION_VERSION, TAINT_OPTIMISTIC

__all__ = [
    "PRICE_BASIS_QUOTE_REAL",
    "PRICE_BASIS_QUOTE_SYNTHETIC",
    "REAL_QUOTES_TAKE_PRECEDENCE",
    "SPREAD_ADAPTER_SYNTHETIC",
    "SPREAD_CALIBRATION_KEY",
    "SPREAD_CONTENT_DEFERRED_TO",
    "SQS_LIVE_USES_MODELED_SERIES",
    "SQS_NON_LIVE_CONSUMES_MODELED_SERIES",
    "ModeledSpreadPoint",
    "ModeledSpreadSeries",
    "SpreadCalibration",
    "SpreadCell",
    "SpreadFeed",
    "SpreadKey",
    "SpreadQuote",
    "SpreadSample",
    "SyntheticSpreadModel",
    "bind_spread_model",
    "fingerprint_spread",
    "hour_utc",
    "modeled_spread_series",
    "quote_side",
    "resolve_spread",
    "spread_calibration_fingerprint",
    "spread_identity",
    "sqs_spread_input",
    "stamp_price_basis",
]

SPREAD_CALIBRATION_KEY: Final[str] = "spread_calibration"
SPREAD_ADAPTER_SYNTHETIC: Final[str] = "synthetic-spread"
PRICE_BASIS_QUOTE_REAL: Final[str] = "quote-real"
PRICE_BASIS_QUOTE_SYNTHETIC: Final[str] = "quote-synthetic"
REAL_QUOTES_TAKE_PRECEDENCE: Final[bool] = True
SPREAD_CONTENT_DEFERRED_TO: Final[str] = "GAP-0048"
SQS_NON_LIVE_CONSUMES_MODELED_SERIES: Final[bool] = True
SQS_LIVE_USES_MODELED_SERIES: Final[bool] = False
_NS_PER_HOUR: Final[int] = 3_600_000_000_000
_LEGAL_BASIS: Final[frozenset[str]] = frozenset(
    {PRICE_BASIS_QUOTE_REAL, PRICE_BASIS_QUOTE_SYNTHETIC}
)


def spread_identity() -> dict[str, object]:
    """Identity-bearing spread-model fields. Package SemVer is omitted."""
    return {
        "adapter_id": SPREAD_ADAPTER_SYNTHETIC,
        "bound_from": "resolved-run-config",
        "calibration_key": SPREAD_CALIBRATION_KEY,
        "content_deferred_to": SPREAD_CONTENT_DEFERRED_TO,
        "key_parts": ("instrument", "hour-utc", "session"),
        "per_broker": True,
        "price_basis_quote_real": PRICE_BASIS_QUOTE_REAL,
        "price_basis_quote_synthetic": PRICE_BASIS_QUOTE_SYNTHETIC,
        "real_quotes_take_precedence": REAL_QUOTES_TAKE_PRECEDENCE,
        "silent_equal_buy_sell": False,
        "silent_zero_spread": False,
        "sqs_live_uses_modeled_series": SQS_LIVE_USES_MODELED_SERIES,
        "sqs_non_live_input": "modeled-spread-series",
        "taint_field": TAINT_OPTIMISTIC,
    }


def fingerprint_spread() -> Result[Fingerprint]:
    """``fp1`` over :func:`spread_identity`."""
    return fingerprint(spread_identity())


def hour_utc(instant: object) -> Result[int]:
    """Hour-of-day in UTC as an exact integer 0..23, never a binary float.

    Instant is an int64 UTC-nanosecond count. Integer division by the hour
    length is identity-bearing; display-zone rendering never enters.
    """
    if not isinstance(instant, Instant):
        return invalid(
            "at",
            "hour-of-day (UTC) is derived from an Instant, never a wall clock string",
            given=repr(type(instant).__name__),
        )
    return Ok(int((instant.value_ns // _NS_PER_HOUR) % 24))


def stamp_price_basis(
    price_basis: object,
    *,
    calibration_ref: object = None,
    composition_version: object = COMPOSITION_VERSION,
) -> Result[FidelityIdentity]:
    """Stamp quote-real or quote-synthetic fidelity. Ordinal ranks stay deferred."""
    token = clean_token(price_basis)
    if token not in _LEGAL_BASIS:
        return invalid(
            "price_basis",
            "price basis is quote-real or quote-synthetic; ordinal ranks are not "
            "invented here (SPREAD-2, SC-07, GAP-0048)",
            given=repr(price_basis),
            allowed=sorted(_LEGAL_BASIS),
            gap=SPREAD_CONTENT_DEFERRED_TO,
        )
    return stamp_fidelity(
        token,
        composition_version=composition_version,
        calibration_ref=calibration_ref,
    )


@dataclass(frozen=True, slots=True)
class SpreadKey:
    """Calibration lookup key: instrument × hour-of-day (UTC) × session (SPREAD-1)."""

    instrument: Instrument
    hour_utc: int
    session: str

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        return {
            "class": "spread-key",
            "hour_utc": self.hour_utc,
            "instrument": _instrument_content(self.instrument),
            "session": self.session,
        }

    @classmethod
    def try_create(
        cls,
        instrument: object,
        hour_utc: object,
        session: object,
    ) -> Result[SpreadKey]:
        """Validate a calibration key. Hour is 0..23; session is an opaque token."""
        inst = _require_instrument(instrument)
        if is_refusal(inst):
            return inst
        hour = _require_hour(hour_utc)
        if is_refusal(hour):
            return hour
        token = clean_token(session)
        if token is None:
            return invalid(
                "session",
                "a spread key names a non-empty session token; display-zone labels "
                "are never identity (SPREAD-1, DEC-0106)",
                given=repr(session),
            )
        return Ok(cls(instrument=inst.value, hour_utc=hour.value, session=token))


@dataclass(frozen=True, slots=True)
class SpreadQuote:
    """Direction-aware bid/ask as exact Prices. Buy never silently equals sell."""

    instrument: Instrument
    bid: Price
    ask: Price
    price_basis: str

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        return {
            "ask": self.ask.fp1_identity(),
            "bid": self.bid.fp1_identity(),
            "class": "spread-quote",
            "instrument": _instrument_content(self.instrument),
            "price_basis": self.price_basis,
        }

    @classmethod
    def try_create(
        cls,
        instrument: object,
        bid: object,
        ask: object,
        *,
        price_basis: object,
    ) -> Result[SpreadQuote]:
        """Validate a bid/ask pair. Equal or crossed quotes refuse; floats refuse."""
        inst = _require_instrument(instrument)
        if is_refusal(inst):
            return inst
        left = _require_price(bid, "bid")
        if is_refusal(left):
            return left
        right = _require_price(ask, "ask")
        if is_refusal(right):
            return right
        basis = clean_token(price_basis)
        if basis not in _LEGAL_BASIS:
            return invalid(
                "price_basis",
                "a spread quote is quote-real or quote-synthetic (SPREAD-2)",
                given=repr(price_basis),
                allowed=sorted(_LEGAL_BASIS),
            )
        quoted = _require_pair(inst.value, left.value, right.value)
        if is_refusal(quoted):
            return quoted
        bid_price, ask_price = quoted.value
        return Ok(
            cls(
                instrument=inst.value,
                bid=bid_price,
                ask=ask_price,
                price_basis=basis,
            )
        )


def quote_side(quote: object, direction: object) -> Result[Price]:
    """Direction-aware print: long/buy uses ask, short/sell uses bid (FILL-3)."""
    if not isinstance(quote, SpreadQuote):
        return invalid(
            "quote",
            "direction-aware pricing consumes a SpreadQuote of exact Prices",
            given=repr(type(quote).__name__),
        )
    if direction is Direction.LONG:
        return Ok(quote.ask)
    if direction is Direction.SHORT:
        return Ok(quote.bid)
    return invalid(
        "direction",
        "direction-aware bid/ask is LONG (ask) or SHORT (bid); buy never equals sell",
        given=repr(direction),
    )


@dataclass(frozen=True, slots=True)
class SpreadCell:
    """One measured bid/ask cell of a per-broker calibration artifact."""

    key: SpreadKey
    bid: Price
    ask: Price

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        return {
            "ask": self.ask.fp1_identity(),
            "bid": self.bid.fp1_identity(),
            "class": "spread-cell",
            "key": self.key.fp1_identity(),
        }

    @classmethod
    def try_create(
        cls,
        instrument: object,
        hour_utc: object,
        session: object,
        bid: object,
        ask: object,
    ) -> Result[SpreadCell]:
        """Validate one calibration cell of exact Prices. No invented defaults."""
        key = SpreadKey.try_create(instrument, hour_utc, session)
        if is_refusal(key):
            return key
        quoted = SpreadQuote.try_create(
            key.value.instrument,
            bid,
            ask,
            price_basis=PRICE_BASIS_QUOTE_SYNTHETIC,
        )
        if is_refusal(quoted):
            return quoted
        return Ok(cls(key=key.value, bid=quoted.value.bid, ask=quoted.value.ask))


@dataclass(frozen=True, slots=True)
class SpreadCalibration:
    """Versioned, fingerprinted per-broker spread table (DEC-0135, B-6).

    Content is measured bid/ask ticks, never invented numbers. Empty cells mean
    content is still deferred to GAP-0048: lookup refuses, it never zeros.
    """

    broker_id: str
    format_version: int
    cells: Mapping[SpreadKey, SpreadCell]
    fingerprint: Fingerprint

    def __post_init__(self) -> None:
        object.__setattr__(self, "cells", MappingProxyType(dict(self.cells)))

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. The derived fingerprint is omitted."""
        ordered = sorted(
            self.cells.values(),
            key=lambda cell: (
                cell.key.instrument.venue.value,
                cell.key.instrument.symbol,
                cell.key.hour_utc,
                cell.key.session,
            ),
        )
        return {
            "broker_id": self.broker_id,
            "cells": [cell.fp1_identity() for cell in ordered],
            "class": "spread-calibration",
            "format_version": self.format_version,
            "per_broker": True,
        }

    @classmethod
    def try_create(
        cls,
        broker_id: object,
        cells: object = (),
        *,
        format_version: object = 1,
        cited_fingerprint: object = None,
    ) -> Result[SpreadCalibration]:
        """Build a per-broker calibration. Empty cells are a bound, content-deferred artifact."""
        broker = clean_token(broker_id)
        if broker is None:
            return invalid(
                "broker_id",
                "a spread calibration is per-broker (DEC-0135); the broker id is a "
                "non-empty opaque token",
                given=repr(broker_id),
            )
        if not isinstance(format_version, int) or isinstance(format_version, bool):
            return invalid(
                "format_version",
                "a calibration format version is a positive integer ordinal",
                given=repr(format_version),
            )
        if format_version < 1:
            return invalid(
                "format_version",
                "a calibration format version is a positive integer ordinal",
                given=format_version,
            )
        parsed = _as_cells(cells)
        if is_refusal(parsed):
            return parsed
        identity = {
            "broker_id": broker,
            "cells": [
                cell.fp1_identity()
                for cell in sorted(
                    parsed.value.values(),
                    key=lambda cell: (
                        cell.key.instrument.venue.value,
                        cell.key.instrument.symbol,
                        cell.key.hour_utc,
                        cell.key.session,
                    ),
                )
            ],
            "class": "spread-calibration",
            "format_version": format_version,
            "per_broker": True,
        }
        derived = fingerprint(identity)
        if is_refusal(derived):
            return derived
        stamped = derived.value
        if cited_fingerprint is not None:
            cited = _as_fingerprint(cited_fingerprint)
            if is_refusal(cited):
                return cited
            if parsed.value and cited.value.value != stamped.value:
                return invalid(
                    "fingerprint",
                    "a calibration fingerprint must match the artifact's content; "
                    "spread numbers are never invented to force a match (SC-07)",
                    given=cited.value.value,
                    derived=stamped.value,
                )
            if not parsed.value:
                stamped = cited.value
        return Ok(
            cls(
                broker_id=broker,
                format_version=format_version,
                cells=parsed.value,
                fingerprint=stamped,
            )
        )


@dataclass(frozen=True, slots=True)
class SpreadFeed:
    """One stream observation: real quotes, or trade-only (both sides absent)."""

    instrument: Instrument
    bid: Price | None
    ask: Price | None

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Absent quotes omit the keys (DEC-0108)."""
        content: dict[str, object] = {
            "class": "spread-feed",
            "instrument": _instrument_content(self.instrument),
        }
        if self.bid is not None:
            content["bid"] = self.bid.fp1_identity()
        if self.ask is not None:
            content["ask"] = self.ask.fp1_identity()
        return content

    @classmethod
    def try_create(
        cls,
        instrument: object,
        *,
        bid: object = None,
        ask: object = None,
    ) -> Result[SpreadFeed]:
        """Validate a feed. One-sided quotes are invalid; both absent is trade-only."""
        inst = _require_instrument(instrument)
        if is_refusal(inst):
            return inst
        if bid is None and ask is None:
            return Ok(cls(instrument=inst.value, bid=None, ask=None))
        if bid is None or ask is None:
            return invalid(
                "quotes",
                "real quotes carry both bid and ask; a one-sided quote is not a "
                "spread and trade-only omits both (FILL-3, SPREAD-2)",
                bid_present=bid is not None,
                ask_present=ask is not None,
            )
        quoted = SpreadQuote.try_create(
            inst.value,
            bid,
            ask,
            price_basis=PRICE_BASIS_QUOTE_REAL,
        )
        if is_refusal(quoted):
            return quoted
        return Ok(cls(instrument=inst.value, bid=quoted.value.bid, ask=quoted.value.ask))

    def has_real_quotes(self) -> bool:
        """True when the feed carries both bid and ask."""
        return self.bid is not None and self.ask is not None


@dataclass(frozen=True, slots=True)
class SpreadSample:
    """One instant the spread model prices for the modeled-spread series."""

    feed: SpreadFeed
    at: Instant
    session: str

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        return {
            "at": self.at.fp1_identity(),
            "class": "spread-sample",
            "feed": self.feed.fp1_identity(),
            "session": self.session,
        }

    @classmethod
    def try_create(cls, feed: object, at: object, session: object) -> Result[SpreadSample]:
        """Validate one sample. Session is an opaque identity-bearing token."""
        if not isinstance(feed, SpreadFeed):
            return invalid(
                "feed",
                "a spread sample carries a SpreadFeed (trade-only or real quotes)",
                given=repr(type(feed).__name__),
            )
        if not isinstance(at, Instant):
            return invalid(
                "at",
                "a spread sample is taken at an Instant",
                given=repr(type(at).__name__),
            )
        token = clean_token(session)
        if token is None:
            return invalid(
                "session",
                "a spread sample names a non-empty session token (SPREAD-1)",
                given=repr(session),
            )
        return Ok(cls(feed=feed, at=at, session=token))


@dataclass(frozen=True, slots=True)
class ModeledSpreadPoint:
    """One exact bid/ask in this run's modeled-spread series (SQS input)."""

    at: Instant
    quote: SpreadQuote
    hour_utc: int
    session: str

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        return {
            "at": self.at.fp1_identity(),
            "class": "modeled-spread-point",
            "hour_utc": self.hour_utc,
            "quote": self.quote.fp1_identity(),
            "session": self.session,
        }


@dataclass(frozen=True, slots=True)
class ModeledSpreadSeries:
    """This run's modeled-spread series — exact Prices, never binary floats."""

    points: tuple[ModeledSpreadPoint, ...]
    calibration_fingerprint: Fingerprint

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        return {
            "calibration_fingerprint": self.calibration_fingerprint.value,
            "class": "modeled-spread-series",
            "points": [item.fp1_identity() for item in self.points],
        }


@dataclass(frozen=True, slots=True)
class SyntheticSpreadModel:
    """Bound synthetic-spread model. Adapters invent no numbers (SC-07)."""

    calibration: SpreadCalibration
    adapter_id: str = SPREAD_ADAPTER_SYNTHETIC
    composition_version: int = COMPOSITION_VERSION
    taint: str = TAINT_OPTIMISTIC

    def fidelity(self, *, price_basis: object) -> Result[FidelityIdentity]:
        """Stamp price-basis + composition-version + calibration fingerprint + taint."""
        return stamp_price_basis(
            price_basis,
            calibration_ref=self.calibration.fingerprint.value,
            composition_version=self.composition_version,
        )

    def resolve(self, feed: object, *, at: object, session: object) -> Result[SpreadQuote]:
        """Supply bid/ask. Real quotes win; trade-only looks up the calibration."""
        return resolve_spread(feed, at=at, session=session, calibration=self.calibration)


def resolve_spread(
    feed: object,
    *,
    at: object,
    session: object,
    calibration: object,
) -> Result[SpreadQuote]:
    """Resolve bid/ask for fill pricing (SPREAD-1, SPREAD-2, FILL-3).

    Real quotes take precedence. Trade-only bars look up instrument × hour-UTC
    × session on the bound calibration. Missing cells, missing artifacts, and
    equal buy/sell are typed refusals — never a silent zero spread.
    """
    observed = _require_feed(feed)
    if is_refusal(observed):
        return observed
    table = _require_calibration(calibration)
    if is_refusal(table):
        return table
    if observed.value.has_real_quotes():
        return SpreadQuote.try_create(
            observed.value.instrument,
            observed.value.bid,
            observed.value.ask,
            price_basis=PRICE_BASIS_QUOTE_REAL,
        )
    hour = hour_utc(at)
    if is_refusal(hour):
        return hour
    key = SpreadKey.try_create(observed.value.instrument, hour.value, session)
    if is_refusal(key):
        return key
    cell = table.value.cells.get(key.value)
    if cell is None:
        instrumented = any(
            item.key.instrument == key.value.instrument for item in table.value.cells.values()
        )
        if not table.value.cells or not instrumented:
            return unavailable(
                "spread_calibration",
                "no spread calibration artifact is bound for this instrument; "
                "absence is a typed refusal, never a silent zero spread "
                "(SPREAD-1, FILL-3, SC-07)",
                broker_id=table.value.broker_id,
                instrument=_instrument_content(key.value.instrument),
                hour_utc=key.value.hour_utc,
                session=key.value.session,
                gap=SPREAD_CONTENT_DEFERRED_TO,
            )
        return unavailable(
            "spread_calibration",
            "the bound calibration has no cell for this instrument x hour-UTC x "
            "session; missing content is never interpolated or zeroed (SPREAD-1, SC-07)",
            broker_id=table.value.broker_id,
            instrument=_instrument_content(key.value.instrument),
            hour_utc=key.value.hour_utc,
            session=key.value.session,
            gap=SPREAD_CONTENT_DEFERRED_TO,
        )
    return SpreadQuote.try_create(
        cell.key.instrument,
        cell.bid,
        cell.ask,
        price_basis=PRICE_BASIS_QUOTE_SYNTHETIC,
    )


def modeled_spread_series(model: object, samples: object) -> Result[ModeledSpreadSeries]:
    """Project this run's modeled-spread series of exact Prices (B-2, AC4)."""
    bound = _require_model(model)
    if is_refusal(bound):
        return bound
    parsed = _as_samples(samples)
    if is_refusal(parsed):
        return parsed
    points: list[ModeledSpreadPoint] = []
    for sample in parsed.value:
        quoted = bound.value.resolve(sample.feed, at=sample.at, session=sample.session)
        if is_refusal(quoted):
            return quoted
        hour = hour_utc(sample.at)
        if is_refusal(hour):
            return hour
        points.append(
            ModeledSpreadPoint(
                at=sample.at,
                quote=quoted.value,
                hour_utc=hour.value,
                session=sample.session,
            )
        )
    return Ok(
        ModeledSpreadSeries(
            points=tuple(points),
            calibration_fingerprint=bound.value.calibration.fingerprint,
        )
    )


def sqs_spread_input(series: object, *, world: object) -> Result[ModeledSpreadSeries]:
    """Book SQS door (AD-39) spread input for a non-live run (B-2).

    Live SQS reads live quotes, never this modeled series. The series cites
    exact ``Price`` values, never binary floats (CT-01, FR-001).
    """
    if not isinstance(series, ModeledSpreadSeries):
        return invalid(
            "series",
            "the Book's SQS door consumes this run's modeled-spread series of exact "
            "Prices (B-2, AD-39)",
            given=repr(type(series).__name__),
        )
    if not isinstance(world, World):
        token = clean_token(world)
        resolved: World | None = None
        if token is not None:
            for member in World:
                if member.value == token:
                    resolved = member
                    break
        if resolved is None:
            return invalid(
                "world",
                "SQS spread input is world-gated; world is live, replay, or simulated",
                given=repr(world),
            )
        world = resolved
    if world is World.LIVE:
        return policy(
            "world",
            "live SQS reads live quotes; the modeled-spread series is the non-live "
            "SQS door input only (B-2, AD-39, DEC-0169)",
            world=world.value,
            sqs_live_uses_modeled_series=SQS_LIVE_USES_MODELED_SERIES,
        )
    return Ok(series)


def bind_spread_model(
    config: object, *, calibration: object = None
) -> Result[SyntheticSpreadModel]:
    """Bind the synthetic-spread model from a resolved run-config (B-3, B-6).

    The config cites the calibration by fingerprint (or holds the artifact).
    When the artifact's cells are absent, lookup later refuses — content is
    deferred to GAP-0048, never silently zeroed.
    """
    if not isinstance(config, ResolvedRunConfig):
        return invalid(
            "config",
            "the spread model binds only from a resolved, read-only run-config (B-3, B-6)",
            given=repr(type(config).__name__),
        )
    raw = config.keys.get(SPREAD_CALIBRATION_KEY)
    if raw is None:
        return invalid(
            SPREAD_CALIBRATION_KEY,
            "the spread model consumes a versioned, fingerprinted per-broker "
            "calibration artifact; missing calibration is a typed refusal, never "
            "a silent zero spread (SPREAD-1, DEC-0135)",
            given=repr(raw),
        )
    artifact = calibration if calibration is not None else raw
    if isinstance(artifact, SpreadCalibration):
        bound = artifact
    else:
        cited = spread_calibration_fingerprint(artifact if artifact is not None else raw)
        if is_refusal(cited):
            return cited
        empty = SpreadCalibration.try_create(
            _citation_broker(raw, cited.value),
            (),
            cited_fingerprint=cited.value,
        )
        if is_refusal(empty):
            return empty
        bound = empty.value
    cited_fp = spread_calibration_fingerprint(raw) if raw is not None else Ok(bound.fingerprint)
    if is_refusal(cited_fp):
        return cited_fp
    if raw is not None and cited_fp.value.value != bound.fingerprint.value:
        return invalid(
            SPREAD_CALIBRATION_KEY,
            "the bound calibration fingerprint must match the resolved-config citation",
            given=cited_fp.value.value,
            bound=bound.fingerprint.value,
        )
    return Ok(SyntheticSpreadModel(calibration=bound))


def spread_calibration_fingerprint(value: object) -> Result[Fingerprint]:
    """Coerce a config citation or artifact to the calibration fingerprint."""
    if isinstance(value, SpreadCalibration):
        return Ok(value.fingerprint)
    return _as_fingerprint(value)


def _citation_broker(raw: object, cited: Fingerprint) -> str:
    if isinstance(raw, SpreadCalibration):
        return raw.broker_id
    token = clean_token(raw)
    if token is not None and not token.startswith("fp1:"):
        return token
    return cited.value


def _as_fingerprint(value: object) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    token = clean_token(value)
    if token is None:
        return invalid(
            SPREAD_CALIBRATION_KEY,
            "a spread calibration citation is an fp1 fingerprint, a per-broker "
            "token, or the calibration artifact (DEC-0135)",
            given=repr(type(value).__name__),
        )
    parsed = Fingerprint.try_create(token)
    if is_refusal(parsed):
        derived = fingerprint(
            {
                "class": "spread-calibration-citation",
                "ref": token,
            }
        )
        if is_refusal(derived):
            return derived
        return Ok(derived.value)
    return Ok(parsed.value)


def _require_instrument(value: object) -> Result[Instrument]:
    if isinstance(value, Instrument):
        return Ok(value)
    return invalid(
        "instrument",
        "spread keys and quotes are instrument-tagged (SPREAD-1, CT-03)",
        given=repr(type(value).__name__),
    )


def _require_hour(value: object) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return invalid(
            "hour_utc",
            "hour-of-day (UTC) is an exact integer 0..23, never a binary float (SPREAD-1)",
            given=repr(value),
        )
    if value < 0 or value > 23:
        return invalid(
            "hour_utc",
            "hour-of-day (UTC) is an exact integer 0..23 (SPREAD-1)",
            given=value,
        )
    return Ok(value)


def _require_price(value: object, field: str) -> Result[Price]:
    if isinstance(value, Price):
        return Ok(value)
    if isinstance(value, float):
        return invalid(
            field,
            "a spread quote is an exact Price, never a binary float (CT-01, FR-001, SC-07)",
            given=repr(value),
        )
    return invalid(
        field,
        "a spread quote is an exact Price, never a binary float (CT-01, FR-001)",
        given=repr(type(value).__name__),
    )


def _require_pair(
    instrument: Instrument,
    bid: Price,
    ask: Price,
) -> Result[tuple[Price, Price]]:
    if bid.instrument != instrument or ask.instrument != instrument:
        return invalid(
            "instrument",
            "bid and ask are Prices of the keyed instrument",
            instrument=_instrument_content(instrument),
        )
    if bid.as_fraction() == ask.as_fraction():
        return policy(
            "spread",
            "the spread model never returns an equal buy/sell price silently; "
            "absence of a spread source is surfaced, not zeroed (SPREAD-1, FILL-3)",
            bid=str(bid.as_fraction()),
            ask=str(ask.as_fraction()),
        )
    if ask.as_fraction() <= bid.as_fraction():
        return invalid(
            "spread",
            "ask is strictly above bid; a crossed or equal quote is not a spread "
            "the model will apply (FILL-3, SPREAD-1)",
            bid=str(bid.as_fraction()),
            ask=str(ask.as_fraction()),
        )
    return Ok((bid, ask))


def _require_feed(value: object) -> Result[SpreadFeed]:
    if isinstance(value, SpreadFeed):
        return Ok(value)
    return invalid(
        "feed",
        "spread resolution consumes a SpreadFeed (trade-only bars or real quotes)",
        given=repr(type(value).__name__),
    )


def _require_calibration(value: object) -> Result[SpreadCalibration]:
    if isinstance(value, SpreadCalibration):
        return Ok(value)
    return invalid(
        "calibration",
        "the spread model consumes a versioned, fingerprinted per-broker "
        "calibration artifact (DEC-0135, B-6)",
        given=repr(type(value).__name__),
    )


def _require_model(value: object) -> Result[SyntheticSpreadModel]:
    if isinstance(value, SyntheticSpreadModel):
        return Ok(value)
    return invalid(
        "model",
        "the modeled-spread series is projected by a bound SyntheticSpreadModel",
        given=repr(type(value).__name__),
    )


def _as_cells(value: object) -> Result[dict[SpreadKey, SpreadCell]]:
    if value is None:
        return Ok({})
    if isinstance(value, SpreadCell):
        return Ok({value.key: value})
    if isinstance(value, Mapping) and not isinstance(value, (str, bytes)):
        parsed: dict[SpreadKey, SpreadCell] = {}
        for raw_key, raw_cell in cast("Mapping[object, object]", value).items():
            cell = _coerce_cell(raw_cell, raw_key)
            if is_refusal(cell):
                return cell
            if cell.value.key in parsed:
                return invalid(
                    "cells",
                    "a calibration artifact has one cell per instrument x hour-UTC x session",
                    key=cell.value.key.fp1_identity(),
                )
            parsed[cell.value.key] = cell.value
        return Ok(parsed)
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "cells",
            "calibration cells are a sequence of SpreadCell values of exact Prices, "
            "never invented numbers (SC-07)",
            given=repr(type(value).__name__),
        )
    parsed_seq: dict[SpreadKey, SpreadCell] = {}
    for index, raw in enumerate(cast("Sequence[object]", value)):
        cell = _coerce_cell(raw, None)
        if is_refusal(cell):
            return cell
        if cell.value.key in parsed_seq:
            return invalid(
                "cells",
                "a calibration artifact has one cell per instrument x hour-UTC x session",
                index=index,
                key=cell.value.key.fp1_identity(),
            )
        parsed_seq[cell.value.key] = cell.value
    return Ok(parsed_seq)


def _coerce_cell(value: object, raw_key: object) -> Result[SpreadCell]:
    if isinstance(value, SpreadCell):
        if raw_key is not None and isinstance(raw_key, SpreadKey) and raw_key != value.key:
            return invalid(
                "cells",
                "a calibration map key must match the cell's instrument x hour-UTC x session",
            )
        return Ok(value)
    if isinstance(value, Mapping) and not isinstance(value, (str, bytes)):
        body = cast("Mapping[str, object]", value)
        return SpreadCell.try_create(
            body.get("instrument"),
            body.get("hour_utc"),
            body.get("session"),
            body.get("bid"),
            body.get("ask"),
        )
    return invalid(
        "cells",
        "each calibration cell is a SpreadCell of exact Prices, never a binary float",
        given=repr(type(value).__name__),
    )


def _as_samples(value: object) -> Result[tuple[SpreadSample, ...]]:
    if isinstance(value, SpreadSample):
        return Ok((value,))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "samples",
            "the modeled-spread series is projected from a sequence of SpreadSample values",
            given=repr(type(value).__name__),
        )
    parsed: list[SpreadSample] = []
    for index, raw in enumerate(cast("Sequence[object]", value)):
        if not isinstance(raw, SpreadSample):
            return invalid(
                "samples",
                "each modeled-spread sample is a SpreadSample",
                index=index,
                given=repr(type(raw).__name__),
            )
        parsed.append(raw)
    return Ok(tuple(parsed))


def _instrument_content(instrument: Instrument) -> dict[str, object]:
    return {"venue": instrument.venue.value, "symbol": instrument.symbol}
