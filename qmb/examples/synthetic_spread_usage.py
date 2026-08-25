"""Reference usage — synthetic-spread model and SQS spread input (Story 17.2).

Executable::

    python qmb/examples/synthetic_spread_usage.py

Shows the things SPREAD-1 / SPREAD-2 / B-2 / B-6 / B-10 pin down:

1. Trade-only bars get bid/ask from a fingerprinted per-broker calibration
   keyed instrument × hour-UTC × session.
2. Missing calibration is a typed refusal, never a silent zero spread.
3. Equal buy/sell is refused; quotes are exact Prices, never binary floats.
4. Real quotes take precedence and stamp quote-real; ordinal ranks stay deferred.
5. The Book's non-live SQS door consumes this run's modeled-spread series.
6. The CT-32 result label declares the calibration fingerprint.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.config import CLOCK_REPLAY, PROVENANCE_RECORDED, mint_replay_binding
from qmb.execution import (
    PRICE_BASIS_QUOTE_REAL,
    PRICE_BASIS_QUOTE_SYNTHETIC,
    SPREAD_CALIBRATION_KEY,
    FidelityTaxonomy,
    SpreadCalibration,
    SpreadCell,
    SpreadFeed,
    SpreadSample,
    bind_spread_model,
    compare_book_bar_fidelity,
    hour_utc,
    lowest_fidelity,
    modeled_spread_series,
    quote_side,
    sqs_spread_input,
    stamp_price_basis,
)
from qmb.runloop import STREAM_SET_KEY, SilentSliceHandler, SliceObservation, run
from qmf.core.chrono import Instant
from qmf.core.exact import Money, Price
from qmf.core.fingerprint import World, fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.risk.door import Direction

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _fp(seed: str):
    return _unwrap(fingerprint({"seed": seed}), seed)


def _instant(ns: int = _NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _instrument(symbol: str = "EURUSD") -> Instrument:
    return Instrument(venue=VenueId(value="venue-replay"), symbol=symbol)


def _price(value: int, instrument: Instrument | None = None) -> Price:
    return _unwrap(Price.try_create(value, instrument or _instrument(), 5), "price")


def _resolved(keys: dict[str, object]) -> qmb.ResolvedRunConfig:
    book = _fp("book")
    bms = _fp("bms")
    bot = _fp("bot")
    binding = _unwrap(
        mint_replay_binding(
            book_fp1=book,
            bms_fp1=bms,
            bot_fp1=bot,
            starting_capital=Money(value=1_000_000, currency="USD", scale=2),
            seed_overridden=False,
            venue_id="venue-replay",
            account_id="acct-replay",
            clock=CLOCK_REPLAY,
            data_provenance=PROVENANCE_RECORDED,
            keys=keys,
        ),
        "binding",
    )
    identity = {
        "book_fp1": book.value,
        "clock": CLOCK_REPLAY,
        "keys": keys,
        "world": World.REPLAY.value,
    }
    return qmb.ResolvedRunConfig(
        format_version=1,
        book_fp1=book,
        bms_fp1=bms,
        bot_fp1=bot,
        book_fragment_fp1=_fp("book-frag"),
        bms_fragment_fp1=_fp("bms-frag"),
        keys=keys,
        clock=CLOCK_REPLAY,
        data_provenance=PROVENANCE_RECORDED,
        world=World.REPLAY,
        fingerprint=_unwrap(fingerprint(identity), "config fp"),
        binding_fp1=binding.fingerprint,
        replay_binding=binding,
    )


def main() -> None:
    inst = _instrument()
    hour = _unwrap(hour_utc(_instant()), "hour")
    cell = _unwrap(
        SpreadCell.try_create(inst, hour, "london", _price(1_10000, inst), _price(1_10012, inst)),
        "cell",
    )
    cal = _unwrap(SpreadCalibration.try_create("broker-a", (cell,)), "calibration")
    model = _unwrap(
        bind_spread_model(
            _resolved({SPREAD_CALIBRATION_KEY: cal.fingerprint.value}),
            calibration=cal,
        ),
        "model",
    )
    trade_only = _unwrap(SpreadFeed.try_create(inst), "trade-only")
    synthetic = _unwrap(model.resolve(trade_only, at=_instant(), session="london"), "synthetic")
    assert synthetic.price_basis == PRICE_BASIS_QUOTE_SYNTHETIC
    assert synthetic.bid.as_fraction() != synthetic.ask.as_fraction()
    assert _unwrap(quote_side(synthetic, Direction.LONG), "ask") is synthetic.ask
    print("trade-only bars use instrument x hour-UTC x session calibration")

    equal = SpreadCell.try_create(
        inst, hour, "london", _price(1_10000, inst), _price(1_10000, inst)
    )
    assert is_refusal(equal)
    print("equal buy/sell refused")
    missing = bind_spread_model(_resolved({}))
    assert is_refusal(missing)
    print("missing calibration is typed refusal, never zero spread")

    real_feed = _unwrap(
        SpreadFeed.try_create(inst, bid=_price(1_10000, inst), ask=_price(1_10030, inst)),
        "quotes",
    )
    real = _unwrap(model.resolve(real_feed, at=_instant(), session="london"), "real")
    assert real.price_basis == PRICE_BASIS_QUOTE_REAL
    assert real.ask.as_fraction() != synthetic.ask.as_fraction()
    print("real quotes take precedence")
    taxonomy = _unwrap(
        FidelityTaxonomy.try_create({PRICE_BASIS_QUOTE_REAL: 1, PRICE_BASIS_QUOTE_SYNTHETIC: 0}),
        "taxonomy",
    )
    assert taxonomy.ranks[PRICE_BASIS_QUOTE_REAL] > taxonomy.ranks[PRICE_BASIS_QUOTE_SYNTHETIC]
    ranked_real = _unwrap(
        lowest_fidelity(
            (_unwrap(stamp_price_basis(PRICE_BASIS_QUOTE_REAL), "real-id"),),
            taxonomy=taxonomy,
        ),
        "ranked-real",
    )
    ranked_synth = _unwrap(
        lowest_fidelity(
            (_unwrap(stamp_price_basis(PRICE_BASIS_QUOTE_SYNTHETIC), "synth-id"),),
            taxonomy=taxonomy,
        ),
        "ranked-synth",
    )
    mixed = compare_book_bar_fidelity(ranked_real, ranked_synth)
    assert is_refusal(mixed)
    print("quote-real ranks higher; ordinal taxonomy is not invented here")

    series = _unwrap(
        modeled_spread_series(
            model,
            (_unwrap(SpreadSample.try_create(trade_only, _instant(), "london"), "sample"),),
        ),
        "series",
    )
    consumed = _unwrap(sqs_spread_input(series, world=World.REPLAY), "sqs")
    assert consumed.points[0].quote.bid.__class__ is Price
    assert is_refusal(sqs_spread_input(series, world=World.LIVE))
    print("non-live SQS door consumes modeled-spread series of exact Prices")

    stamp = _unwrap(fingerprint({"n": "spread-label"}), "stamp")
    outcome = _unwrap(
        run(
            slices=(
                (
                    _unwrap(
                        SliceObservation.try_create("eurusd", _instant(), True),
                        "obs",
                    ),
                ),
            ),
            config=qmb.ResolvedRunConfig(
                format_version=1,
                book_fp1=stamp,
                bms_fp1=stamp,
                bot_fp1=stamp,
                book_fragment_fp1=stamp,
                bms_fragment_fp1=stamp,
                keys={STREAM_SET_KEY: ("eurusd",), SPREAD_CALIBRATION_KEY: cal.fingerprint},
                clock=CLOCK_REPLAY,
                data_provenance=PROVENANCE_RECORDED,
                world=World.REPLAY,
                fingerprint=stamp,
            ),
            handler=SilentSliceHandler(),
        ),
        "run",
    )
    assert cal.fingerprint in outcome.performance_result.result_label.input_fingerprints
    print("CT-32 label declares the spread calibration fingerprint")
    print("synthetic spread ok")


if __name__ == "__main__":
    main()
