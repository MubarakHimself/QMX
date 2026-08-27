"""Shared fixtures and builders for the Epic 22 (qmb-robustness) independent QA suite.

Every assertion in this suite states what a *requirement* of Epic 22 demands (the
B-14 spine, the CT-* contracts, the constitution), never what the source happens to
do. A failing test is a FINDING; source is read-only evidence and is never edited to
make a test pass. Builders below construct only shape-faithful, exact-integer inputs
(Money, Price, Instant, Interval, Candle, SignalBar) — no product mock market data,
no default strategies. Instants span a realistic multi-hundred-day window so the
Epic-14/19 measure set (which computes CAGR over the period) does not itself overflow
on a nanoscale window; the robustness procedures under test are exact-integer.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar

import pytest

from qmf.core.chrono import Instant, Interval
from qmf.core.exact import Money, Price
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_ok,
    is_refusal,
)

T = TypeVar("T")

# The worktree root (this file is at <root>/qa/tests/epic_22/conftest.py).
WORKTREE_ROOT = Path(__file__).resolve().parents[3]

# A realistic UTC-ns epoch base (~2020-09) and a one-day step, so a data window of a
# few hundred days keeps CAGR finite in the Epic-14/19 measure assembler.
_DAY_NS = 86_400 * 10**9
_BASE_NS = 1_600_000_000 * 10**9


def unwrap(result: Result[T], what: str = "value") -> T:
    """Unwrap an ``Ok`` or fail loudly — used only to build *inputs*, never to assert."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got refusal: {result!r}")


def instant(day_offset: int) -> Instant:
    """An Instant ``day_offset`` days after the fixture epoch (int64 UTC ns)."""
    return unwrap(Instant.try_create(_BASE_NS + day_offset * _DAY_NS), f"instant@{day_offset}")


def interval(start_day: int, end_day: int) -> Interval:
    """A closed data-window Interval over two day offsets."""
    return unwrap(Interval.try_create(instant(start_day), instant(end_day)), "interval")


def usd(minor_units: int) -> Money:
    """Exact USD Money at scale 2 (cents); never a float."""
    return unwrap(Money.try_create(minor_units, "USD", 2), f"money@{minor_units}")


@pytest.fixture(scope="session")
def instr() -> Instrument:
    """A shape-faithful Instrument for building exact Price closes."""
    venue = unwrap(VenueId.try_create("SIM"), "venue")
    return unwrap(Instrument.try_create(venue, "EURUSD"), "instrument")


def price(value: int, instrument: Instrument, scale: int = 5) -> Price:
    """An exact scaled-integer Price for ``instrument``; never a float."""
    return unwrap(Price.try_create(value, instrument, scale), f"price@{value}")


# --- CT-04 refusal harness ---------------------------------------------------


def assert_ct04_refusal(
    result: object,
    expected: RefusalCategory,
    *,
    what: str = "operation",
) -> TypedRefusal:
    """Assert ``result`` is a RETURNED CT-04 typed refusal of ``expected`` category.

    Checks the four things the CT-04 contract pins for a refusal value: it is a
    ``TypedRefusal`` returned (not raised), its ``category`` is one of the seven and is
    the expected one, its ``retryability`` is a valid enum member, and its ``context``
    is present and non-null. No assertion ever parses the refusal's prose.
    """
    assert is_refusal(result), f"{what}: expected a RETURNED CT-04 refusal, got {result!r}"
    refusal = result
    assert isinstance(refusal, TypedRefusal)
    assert isinstance(refusal.category, RefusalCategory)
    assert refusal.category is expected, (
        f"{what}: expected category {expected.value!r}, got {refusal.category.value!r}"
    )
    assert isinstance(refusal.retryability, Retryability)
    assert isinstance(refusal.context, Mapping)
    assert refusal.context is not None
    return refusal


def is_exact_quantity(value: object) -> bool:
    """True when ``value`` is an exact quantity (Money/ExactRational), never a float."""
    from qmf.core.exact import ExactRational

    return isinstance(value, (Money, ExactRational)) and not isinstance(value, float)


__all__ = [
    "Ok",
    "RefusalCategory",
    "Retryability",
    "TypedRefusal",
    "WORKTREE_ROOT",
    "assert_ct04_refusal",
    "instant",
    "instr",
    "interval",
    "is_exact_quantity",
    "is_ok",
    "is_refusal",
    "price",
    "unwrap",
    "usd",
]
