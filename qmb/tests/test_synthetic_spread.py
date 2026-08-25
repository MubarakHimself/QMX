"""Story 17.2 — synthetic-spread model and SQS spread input."""

from __future__ import annotations

from typing import TypeVar

from qmb.config import CLOCK_REPLAY, PROVENANCE_RECORDED, mint_replay_binding
from qmb.doors import api
from qmb.execution import (
    FIDELITY_TAXONOMY_DEFERRED_TO,
    PRICE_BASIS_QUOTE_REAL,
    PRICE_BASIS_QUOTE_SYNTHETIC,
    REAL_QUOTES_TAKE_PRECEDENCE,
    SPREAD_ADAPTER_SYNTHETIC,
    SPREAD_CALIBRATION_KEY,
    SPREAD_CONTENT_DEFERRED_TO,
    SQS_LIVE_USES_MODELED_SERIES,
    SQS_NON_LIVE_CONSUMES_MODELED_SERIES,
    FidelityTaxonomy,
    SpreadCalibration,
    SpreadCell,
    SpreadFeed,
    SpreadQuote,
    SpreadSample,
    bind_spread_model,
    compare_book_bar_fidelity,
    hour_utc,
    lowest_fidelity,
    modeled_spread_series,
    quote_side,
    spread_identity,
    sqs_spread_input,
    stamp_price_basis,
)
from qmb.runloop import STREAM_SET_KEY, SilentSliceHandler, SliceObservation, run
from qmf.core.chrono import Instant
from qmf.core.exact import Money, Price
from qmf.core.fingerprint import World, fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.risk.door import Direction

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_VENUE = "venue-replay"
_ACCOUNT = "acct-replay"
_SESSION = "london"
_BROKER = "broker-a"
_SEED = Money(value=1_000_000, currency="USD", scale=2)


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _fp(seed: str):
    return _ok(fingerprint({"seed": seed}))


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _instrument(symbol: str = "EURUSD") -> Instrument:
    return Instrument(venue=VenueId(value=_VENUE), symbol=symbol)


def _price(value: int, instrument: Instrument | None = None) -> Price:
    return _ok(Price.try_create(value, instrument or _instrument(), 5))


def _cell(
    *,
    bid: int = 1_10000,
    ask: int = 1_10012,
    hour: int | None = None,
    session: str = _SESSION,
    symbol: str = "EURUSD",
) -> SpreadCell:
    inst = _instrument(symbol)
    when = hour if hour is not None else _ok(hour_utc(_instant()))
    return _ok(SpreadCell.try_create(inst, when, session, _price(bid, inst), _price(ask, inst)))


def _calibration(*cells: SpreadCell) -> SpreadCalibration:
    return _ok(SpreadCalibration.try_create(_BROKER, cells))


def _resolved(*, keys: dict[str, object] | None = None) -> qmb.ResolvedRunConfig:
    payload = dict(keys or {})
    book = _fp("book")
    bms = _fp("bms")
    bot = _fp("bot")
    binding = _ok(
        mint_replay_binding(
            book_fp1=book,
            bms_fp1=bms,
            bot_fp1=bot,
            starting_capital=_SEED,
            seed_overridden=False,
            venue_id=_VENUE,
            account_id=_ACCOUNT,
            clock=CLOCK_REPLAY,
            data_provenance=PROVENANCE_RECORDED,
            keys=payload,
        )
    )
    identity = {
        "book_fp1": book.value,
        "clock": CLOCK_REPLAY,
        "data_provenance": PROVENANCE_RECORDED,
        "keys": payload,
        "world": World.REPLAY.value,
    }
    return qmb.ResolvedRunConfig(
        format_version=1,
        book_fp1=book,
        bms_fp1=bms,
        bot_fp1=bot,
        book_fragment_fp1=_fp("book-frag"),
        bms_fragment_fp1=_fp("bms-frag"),
        keys=payload,
        clock=CLOCK_REPLAY,
        data_provenance=PROVENANCE_RECORDED,
        world=World.REPLAY,
        fingerprint=_ok(fingerprint(identity)),
        binding_fp1=binding.fingerprint,
        replay_binding=binding,
    )


def _obs(stream_id: str = "eurusd", ns: int = _NS) -> SliceObservation:
    return _ok(SliceObservation.try_create(stream_id, _instant(ns), True))


def test_spread_identity_excludes_semver_and_invented_ranks() -> None:
    payload = spread_identity()
    assert payload["adapter_id"] == SPREAD_ADAPTER_SYNTHETIC
    assert payload["key_parts"] == ("instrument", "hour-utc", "session")
    assert payload["per_broker"] is True
    assert payload["real_quotes_take_precedence"] is True is REAL_QUOTES_TAKE_PRECEDENCE
    assert payload["silent_zero_spread"] is False
    assert payload["silent_equal_buy_sell"] is False
    assert payload["content_deferred_to"] == SPREAD_CONTENT_DEFERRED_TO == "GAP-0048"
    assert payload["sqs_non_live_input"] == "modeled-spread-series"
    assert payload["sqs_live_uses_modeled_series"] is SQS_LIVE_USES_MODELED_SERIES is False
    assert SQS_NON_LIVE_CONSUMES_MODELED_SERIES is True
    assert qmb.__version__ not in payload.values()
    assert "rank" not in payload
    first = _ok(qmb.fingerprint_spread())
    second = _ok(qmb.fingerprint_spread())
    assert first.value == second.value


def test_trade_only_bars_use_instrument_hour_session_calibration() -> None:
    cell = _cell()
    cal = _calibration(cell)
    model = _ok(
        bind_spread_model(
            _resolved(keys={SPREAD_CALIBRATION_KEY: cal.fingerprint.value}),
            calibration=cal,
        )
    )
    feed = _ok(SpreadFeed.try_create(_instrument()))
    assert feed.has_real_quotes() is False
    quoted = _ok(model.resolve(feed, at=_instant(), session=_SESSION))
    assert quoted.price_basis == PRICE_BASIS_QUOTE_SYNTHETIC
    assert quoted.bid.as_fraction() == cell.bid.as_fraction()
    assert quoted.ask.as_fraction() == cell.ask.as_fraction()
    assert quoted.bid.as_fraction() != quoted.ask.as_fraction()
    long_px = _ok(quote_side(quoted, Direction.LONG))
    short_px = _ok(quote_side(quoted, Direction.SHORT))
    assert long_px.as_fraction() == quoted.ask.as_fraction()
    assert short_px.as_fraction() == quoted.bid.as_fraction()
    assert long_px.as_fraction() != short_px.as_fraction()
    hour = _ok(hour_utc(_instant()))
    other_hour = _ok(Instant.try_create(_NS + 3_600_000_000_000))
    assert _ok(hour_utc(other_hour)) != hour
    missing_hour = model.resolve(feed, at=other_hour, session=_SESSION)
    assert is_refusal(missing_hour)
    assert missing_hour.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_never_silent_equal_buy_sell() -> None:
    inst = _instrument()
    mid = _price(1_10000, inst)
    equal = SpreadCell.try_create(inst, 14, _SESSION, mid, mid)
    assert is_refusal(equal)
    assert equal.category is RefusalCategory.POLICY_REJECTION
    crossed = SpreadCell.try_create(
        inst, 14, _SESSION, _price(1_10012, inst), _price(1_10000, inst)
    )
    assert is_refusal(crossed)
    floated = SpreadQuote.try_create(inst, 1.1, 1.2, price_basis=PRICE_BASIS_QUOTE_SYNTHETIC)
    assert is_refusal(floated)
    assert floated.category is RefusalCategory.INVALID_INPUT


def test_missing_calibration_is_typed_refusal_never_zero() -> None:
    missing = bind_spread_model(_resolved())
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.INVALID_INPUT
    assert missing.context["field"] == SPREAD_CALIBRATION_KEY
    cited = _fp("spread-table-absent")
    model = _ok(bind_spread_model(_resolved(keys={SPREAD_CALIBRATION_KEY: cited.value})))
    assert model.calibration.cells == {}
    assert model.calibration.fingerprint == cited
    trade_only = _ok(SpreadFeed.try_create(_instrument()))
    refused = model.resolve(trade_only, at=_instant(), session=_SESSION)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refused.context["gap"] == "GAP-0048"
    other = _ok(SpreadFeed.try_create(_instrument("GBPUSD")))
    cal = _calibration(_cell())
    bound = _ok(
        bind_spread_model(
            _resolved(keys={SPREAD_CALIBRATION_KEY: cal.fingerprint.value}),
            calibration=cal,
        )
    )
    missing_inst = bound.resolve(other, at=_instant(), session=_SESSION)
    assert is_refusal(missing_inst)
    assert missing_inst.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_real_quotes_take_precedence_and_rank_higher_without_inventing_ordinals() -> None:
    cell = _cell(ask=1_10012)
    cal = _calibration(cell)
    model = _ok(
        bind_spread_model(
            _resolved(keys={SPREAD_CALIBRATION_KEY: cal.fingerprint.value}),
            calibration=cal,
        )
    )
    inst = _instrument()
    live_ask = _price(1_10030, inst)
    feed = _ok(SpreadFeed.try_create(inst, bid=_price(1_10000, inst), ask=live_ask))
    quoted = _ok(model.resolve(feed, at=_instant(), session=_SESSION))
    assert quoted.price_basis == PRICE_BASIS_QUOTE_REAL
    assert quoted.ask.as_fraction() == live_ask.as_fraction()
    assert quoted.ask.as_fraction() != cell.ask.as_fraction()
    real = _ok(stamp_price_basis(PRICE_BASIS_QUOTE_REAL, calibration_ref=cal.fingerprint.value))
    synth = _ok(
        stamp_price_basis(PRICE_BASIS_QUOTE_SYNTHETIC, calibration_ref=cal.fingerprint.value)
    )
    deferred = _ok(lowest_fidelity((real, synth)))
    assert deferred.taxonomy_deferred is True
    assert deferred.lowest_adapter_id is None
    assert FIDELITY_TAXONOMY_DEFERRED_TO == SPREAD_CONTENT_DEFERRED_TO
    taxonomy = _ok(
        FidelityTaxonomy.try_create({PRICE_BASIS_QUOTE_REAL: 1, PRICE_BASIS_QUOTE_SYNTHETIC: 0})
    )
    assert taxonomy.ranks[PRICE_BASIS_QUOTE_REAL] > taxonomy.ranks[PRICE_BASIS_QUOTE_SYNTHETIC]
    ranked_real = _ok(lowest_fidelity((real,), taxonomy=taxonomy))
    ranked_synth = _ok(lowest_fidelity((synth,), taxonomy=taxonomy))
    mixed = compare_book_bar_fidelity(ranked_real, ranked_synth)
    assert is_refusal(mixed)
    assert mixed.category is RefusalCategory.POLICY_REJECTION
    invented = stamp_price_basis("trade-only")
    assert is_refusal(invented)


def test_sqs_non_live_consumes_modeled_spread_series_of_exact_prices() -> None:
    cal = _calibration(_cell())
    model = _ok(
        bind_spread_model(
            _resolved(keys={SPREAD_CALIBRATION_KEY: cal.fingerprint.value}),
            calibration=cal,
        )
    )
    inst = _instrument()
    trade_only = _ok(SpreadFeed.try_create(inst))
    quoted_feed = _ok(
        SpreadFeed.try_create(inst, bid=_price(1_10000, inst), ask=_price(1_10040, inst))
    )
    samples = (
        _ok(SpreadSample.try_create(trade_only, _instant(), _SESSION)),
        _ok(SpreadSample.try_create(quoted_feed, _instant(_NS + 1), _SESSION)),
    )
    series = _ok(modeled_spread_series(model, samples))
    assert series.calibration_fingerprint == cal.fingerprint
    assert len(series.points) == 2
    assert series.points[0].quote.price_basis == PRICE_BASIS_QUOTE_SYNTHETIC
    assert series.points[1].quote.price_basis == PRICE_BASIS_QUOTE_REAL
    for point in series.points:
        assert isinstance(point.quote.bid, Price)
        assert isinstance(point.quote.ask, Price)
        assert point.quote.bid.as_fraction() != point.quote.ask.as_fraction()
    consumed = _ok(sqs_spread_input(series, world=World.REPLAY))
    assert consumed is series
    live = sqs_spread_input(series, world=World.LIVE)
    assert is_refusal(live)
    assert live.category is RefusalCategory.POLICY_REJECTION
    assert live.context["field"] == "world"


def test_ct32_label_declares_spread_calibration_fingerprint() -> None:
    cal = _calibration(_cell())
    stamp = _ok(fingerprint({"n": "spread-ct32"}))
    with_cal = qmb.ResolvedRunConfig(
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
    )
    without = qmb.ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd",)},
        clock=CLOCK_REPLAY,
        data_provenance=PROVENANCE_RECORDED,
        world=World.REPLAY,
        fingerprint=stamp,
    )
    labelled = _ok(
        run(
            slices=((_obs(),),),
            config=with_cal,
            handler=SilentSliceHandler(),
        )
    )
    baseline = _ok(
        run(
            slices=((_obs(),),),
            config=without,
            handler=SilentSliceHandler(),
        )
    )
    inputs = labelled.performance_result.result_label.input_fingerprints
    assert cal.fingerprint in inputs
    assert cal.fingerprint not in baseline.performance_result.result_label.input_fingerprints
    assert _ok(labelled.ct32_fingerprint()).value != _ok(baseline.ct32_fingerprint()).value


def test_api_door_matches_spread_surface() -> None:
    assert api.bind_spread_model is qmb.bind_spread_model is bind_spread_model
    assert api.SpreadCalibration is qmb.SpreadCalibration is SpreadCalibration
    assert api.sqs_spread_input is qmb.sqs_spread_input is sqs_spread_input
    assert api.SPREAD_CALIBRATION_KEY == qmb.SPREAD_CALIBRATION_KEY == SPREAD_CALIBRATION_KEY
    assert api.spread_identity() == qmb.spread_identity() == spread_identity()
    assert "version" not in qmb.spread_identity()
    assert qmb.__version__ not in qmb.spread_identity().values()
