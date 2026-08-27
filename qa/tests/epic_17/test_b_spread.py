"""Epic 17 · Group B — synthetic-spread model & SQS spread input (Story 17.2, R13-R17).

Independent, requirements-derived assertions (T-17.2-a..e). Trade-only bars obtain
bid/ask from a fingerprinted per-broker calibration keyed instrument x hour-UTC x
session; real quotes win; absence is a typed refusal, never a silent zero or a
silent buy=sell (SPREAD-1/2, FILL-3, DEC-0135, SC-07, CT-01). A failing test is a
FINDING, never a licence to soften the assertion or edit source.
"""

from __future__ import annotations

from _e17 import inst, instrument, ok, price, refusal

from qmf.core.fingerprint import Fingerprint, World
from qmf.core.refusal import RefusalCategory, is_ok, is_refusal
from qmf.risk.door import Direction
from qmb.execution.spread import (
    PRICE_BASIS_QUOTE_REAL,
    PRICE_BASIS_QUOTE_SYNTHETIC,
    ModeledSpreadSeries,
    SpreadCalibration,
    SpreadCell,
    SpreadFeed,
    SpreadSample,
    SyntheticSpreadModel,
    hour_utc,
    modeled_spread_series,
    quote_side,
    resolve_spread,
    sqs_spread_input,
    stamp_price_basis,
)

_EUR = instrument("EURUSD")


def _cell(instr, hour, session, bid, ask):
    return ok(SpreadCell.try_create(instr, hour, session,
                                    price(bid, instr=instr), price(ask, instr=instr)))


def _calibration(instr=_EUR, *, session="london", bid=100_000, ask=100_020, broker="broker-x"):
    hour = ok(hour_utc(inst()))
    return ok(SpreadCalibration.try_create(broker, (_cell(instr, hour, session, bid, ask),)))


# --- T-17.2-a (L2) trade-only bars -> keyed synthetic bid/ask, never equal [R13] P0
def test_t172a_trade_only_supplies_keyed_bid_ask_never_equal() -> None:
    cal = _calibration()
    feed = ok(SpreadFeed.try_create(_EUR))  # trade-only: no quotes
    quote = ok(resolve_spread(feed, at=inst(), session="london", calibration=cal))
    assert quote.price_basis == PRICE_BASIS_QUOTE_SYNTHETIC
    # buy (ask) is strictly above sell (bid): the model never silently returns buy=sell.
    assert quote.bid.as_fraction() < quote.ask.as_fraction()
    assert ok(quote_side(quote, Direction.LONG)) == quote.ask
    assert ok(quote_side(quote, Direction.SHORT)) == quote.bid
    assert quote.ask != quote.bid
    # Counter-case: a calibration cell with buy==sell is itself refused (never built).
    hour = ok(hour_utc(inst()))
    assert is_refusal(
        SpreadCell.try_create(_EUR, hour, "london", price(100_000, instr=_EUR),
                              price(100_000, instr=_EUR))
    )


# --- T-17.2-b (L3) absent artifact for the instrument -> CT-04, never zero [R14] P0
def test_t172b_absent_calibration_refuses_never_silent_zero() -> None:
    # A calibration bound for a DIFFERENT instrument leaves this one uncovered.
    other = instrument("GBPUSD")
    cal = _calibration(other)
    feed = ok(SpreadFeed.try_create(_EUR))
    refused = refusal(resolve_spread(feed, at=inst(), session="london", calibration=cal))
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    # The calibration is versioned + fingerprinted per-broker (DEC-0135).
    assert isinstance(cal.fingerprint, Fingerprint)
    assert cal.broker_id == "broker-x" and cal.format_version >= 1
    # An empty calibration also refuses (never a zero spread).
    empty = ok(SpreadCalibration.try_create("broker-x", ()))
    assert is_refusal(resolve_spread(feed, at=inst(), session="london", calibration=empty))
    # Counter-case: a matching cell resolves (proves the refusal is not spurious).
    assert is_ok(resolve_spread(feed, at=inst(), session="london", calibration=_calibration(_EUR)))


# --- T-17.2-c (L2) real quotes take precedence, higher price-basis fidelity [R15] --
def test_t172c_real_quotes_take_precedence_over_synthetic() -> None:
    # The calibration would give 100000/100020; the real feed gives 100005/100015.
    cal = _calibration(bid=100_000, ask=100_020)
    real = ok(SpreadFeed.try_create(_EUR, bid=price(100_005), ask=price(100_015)))
    quote = ok(resolve_spread(real, at=inst(), session="london", calibration=cal))
    # Real quotes win: basis is quote-real and the values are the FEED's, not the model's.
    assert quote.price_basis == PRICE_BASIS_QUOTE_REAL
    assert quote.bid == price(100_005) and quote.ask == price(100_015)
    # The two bases are distinct fidelity tokens; the ordinal rank stays deferred (GAP-0048).
    real_id = ok(stamp_price_basis(PRICE_BASIS_QUOTE_REAL))
    synth_id = ok(stamp_price_basis(PRICE_BASIS_QUOTE_SYNTHETIC))
    assert real_id.adapter_id != synth_id.adapter_id


# --- T-17.2-d (L3) SQS door consumes the modeled series of exact Prices [R16] --
def test_t172d_sqs_door_consumes_modeled_series_exact_prices() -> None:
    model = SyntheticSpreadModel(calibration=_calibration())
    feed = ok(SpreadFeed.try_create(_EUR))
    sample = ok(SpreadSample.try_create(feed, inst(), "london"))
    series = ok(modeled_spread_series(model, (sample,)))
    assert isinstance(series, ModeledSpreadSeries) and len(series.points) == 1
    # The series cites exact Price values, never binary floats (CT-01, FR-001).
    from qmf.core.exact import Price

    for point in series.points:
        assert isinstance(point.quote.bid, Price) and isinstance(point.quote.ask, Price)
    # Non-live SQS consumes the modeled series; live SQS reads live quotes (refused).
    assert ok(sqs_spread_input(series, world=World.REPLAY)) is series
    live = refusal(sqs_spread_input(series, world=World.LIVE))
    assert live.category is RefusalCategory.POLICY_REJECTION
    # A non-series input is invalid input.
    assert is_refusal(sqs_spread_input("not-a-series", world=World.REPLAY))


# --- T-17.2-e (L3) run declares the spread calibration fingerprint in the label [R17]
def test_t172e_calibration_fingerprint_declared_in_label() -> None:
    cal = _calibration()
    model = SyntheticSpreadModel(calibration=cal)
    ident = ok(model.fidelity(price_basis=PRICE_BASIS_QUOTE_SYNTHETIC))
    # The fidelity label declares the calibration artifact fingerprint (B-10, B-13, AR-59).
    assert ident.calibration_ref == cal.fingerprint.value
    # The modeled series carries the same calibration fingerprint for the CT-32 label.
    feed = ok(SpreadFeed.try_create(_EUR))
    sample = ok(SpreadSample.try_create(feed, inst(), "london"))
    series = ok(modeled_spread_series(model, (sample,)))
    assert series.calibration_fingerprint == cal.fingerprint
    # A different calibration yields a different declared fingerprint (falsifiable).
    other = _calibration(bid=100_000, ask=100_050)
    assert other.fingerprint.value != cal.fingerprint.value
