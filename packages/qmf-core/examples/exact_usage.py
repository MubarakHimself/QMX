"""Reference usage — CT-01 exact money, price, and quantity values (COMP-QMF-CORE).

Executable::

    python packages/qmf-core/examples/exact_usage.py

Shows the five things CT-01 pins down:

1. Money, Price, and Quantity are exact **scaled integers**, and a binary float
   on the money path is refused — a float re-enters only through the named
   :meth:`Money.from_float` boundary, which states its rounding mode explicitly.
2. Mixed-scale arithmetic on the same currency auto-promotes losslessly to the
   finer scale; a different currency is refused, never silently converted.
3. Subtracting two Prices yields a first-class :class:`PriceDelta`, distinct from
   Price; a pip/point comes from an instrument-metadata record, never hardcoded.
4. Converting a delta to money needs an instrument value-factor; an absent one is
   an ``unavailable dependency`` refusal, never a silent conversion.
5. Two encodings of the same amount share one canonical ``fp1`` fingerprint by
   construction — equal value implies equal identity.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core.exact import Money, Price, PriceDelta, Quantity, RoundingMode, UnitKind, ValueFactor
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import Result, TypedRefusal, is_ok

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    """Tiny demo helper: a construction we assert must succeed here."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def scaled_integers_ban_float() -> tuple[Money, Money]:
    """A float is refused on the money path; it re-enters only at the boundary."""
    exact = _unwrap(Money.try_create(150, "USD", 2), "exact money")  # 1.50 USD

    refused = Money.try_create(1.5, "USD", 2)
    assert isinstance(refused, TypedRefusal)

    # The named boundary: a float becomes exact money under an explicit rounding.
    converted = _unwrap(
        Money.from_float(1.499, currency="USD", scale=2, rounding=RoundingMode.HALF_UP),
        "boundary-converted money",
    )
    return exact, converted


def mixed_scale_promotes(currency_a: Money) -> Money:
    """1.50 + 0.2500 promotes losslessly to scale 4; cross-currency is refused."""
    fine = _unwrap(Money.try_create(2500, "USD", 4), "fine money")  # 0.2500 USD
    total = _unwrap(currency_a.add(fine), "promoted sum")

    cross = currency_a.add(_unwrap(Money.try_create(150, "EUR", 2), "eur money"))
    assert isinstance(cross, TypedRefusal)
    return total


def price_minus_price_is_a_delta(instrument: Instrument) -> PriceDelta:
    """Subtracting two Prices yields a first-class PriceDelta."""
    high = _unwrap(Price.try_create(108930, instrument, 5), "high price")
    low = _unwrap(Price.try_create(108925, instrument, 5), "low price")
    delta = _unwrap(high.subtract(low), "price delta")
    assert isinstance(delta, PriceDelta)
    return delta


def delta_needs_metadata(delta: PriceDelta, instrument: Instrument) -> Money:
    """A pip and a value-factor come from metadata; an absent one is refused."""
    # An absent value-factor is an unavailable-dependency refusal.
    absent = delta.to_money(None, _unwrap(Quantity.try_create(1, "lot", 0), "qty"), scale=2)
    assert isinstance(absent, TypedRefusal)

    # The pip size is metadata, never hardcoded: here 0.00001 (one point at digit 5).
    pip = _unwrap(PriceDelta.try_create(1, instrument, 5), "pip size")
    pips = _unwrap(delta.in_pips(pip), "pip count")
    assert pips.unit_kind is UnitKind.DIMENSIONLESS_RATIO

    # With a value-factor from metadata, the delta converts to exact money.
    value_factor = _unwrap(ValueFactor.try_create(100000, 1, instrument, "USD"), "value-factor")
    quantity = _unwrap(Quantity.try_create(2, "lot", 0), "quantity")
    return _unwrap(delta.to_money(value_factor, quantity, scale=2), "delta money")


def equal_value_equal_fingerprint() -> bool:
    """The same amount at two scales shares one canonical fingerprint content."""
    a = _unwrap(Money.try_create(150, "USD", 2), "money a").fp1_identity()  # 1.50
    b = _unwrap(Money.try_create(15000, "USD", 4), "money b").fp1_identity()  # 1.5000
    return a == b


def main() -> None:
    venue = _unwrap(VenueId.try_create("venue-ic-markets-01"), "venue")
    instrument = _unwrap(Instrument.try_create(venue, "EURUSD"), "instrument")

    exact, converted = scaled_integers_ban_float()
    print(f"exact money 1.50 stored as {exact.value} at scale {exact.scale}")
    print(f"float refused; boundary-converted to {converted.value} at scale {converted.scale}")

    total = mixed_scale_promotes(exact)
    print(f"mixed-scale sum promoted to {total.value} at scale {total.scale}")

    delta = price_minus_price_is_a_delta(instrument)
    print(f"price delta is a {type(delta).__name__} of {delta.value} at scale {delta.scale}")

    money = delta_needs_metadata(delta, instrument)
    print(
        f"delta converted via value-factor to {money.value} {money.currency} at scale {money.scale}"
    )

    print(f"equal value equal fingerprint: {equal_value_equal_fingerprint()}")


if __name__ == "__main__":
    main()
