"""Reference usage — CT-03 instrument, venue, and account identity (COMP-QMF-CORE).

Executable::

    python packages/qmf-core/examples/identity_usage.py

Shows the four things CT-03 pins down:

1. An :class:`Instrument` is the opaque pair ``(venue, symbol)`` and the symbol
   is never parsed — two brokers' ``EURUSD`` are two distinct instruments because
   their :class:`VenueId`\\ s differ, and a prop firm white-labeling cTrader is
   its own venue.
2. An :class:`Account` carries exactly one role from the fixed set, and Books
   bind to accounts, never to venues.
3. A rename is a **new** :class:`DatedRecord` pointing at the identity — stored
   history never rewrites, so a correction is appended, never edited in place.
4. Every construction is value-or-refusal: a missing or invalid part comes back
   as a CT-04 ``TypedRefusal``, never a default, and null is never a field.
"""

from __future__ import annotations

from datetime import date
from typing import TypeVar

from qmf.core.identity import (
    Account,
    AccountRole,
    DatedRecord,
    Instrument,
    VenueId,
)
from qmf.core.refusal import Result, TypedRefusal, is_ok

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    """Tiny demo helper: a construction we assert must succeed here."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def two_brokers_never_mix() -> tuple[Instrument, Instrument]:
    """The same venue symbol on two venues is two distinct instruments."""
    broker_a = _unwrap(VenueId.try_create("venue-ic-markets-01"), "VenueId A")
    prop_firm = _unwrap(VenueId.try_create("venue-propfirm-ctrader-01"), "VenueId B")

    eurusd_a = _unwrap(Instrument.try_create(broker_a, "EURUSD"), "Instrument A")
    eurusd_b = _unwrap(Instrument.try_create(prop_firm, "EURUSD"), "Instrument B")
    # Identical opaque symbols, different venues => not equal.
    assert eurusd_a != eurusd_b
    return eurusd_a, eurusd_b


def account_carries_one_role(venue: VenueId) -> Account:
    """An account carries exactly one role from the fixed set."""
    return _unwrap(
        Account.try_create("acct-77213", venue, AccountRole.DEMO),
        "Account",
    )


def rename_is_a_new_record(venue: VenueId) -> list[DatedRecord]:
    """A correction is a new dated record appended to history, never an edit."""
    history: list[DatedRecord] = []
    first = _unwrap(
        DatedRecord.try_create(venue, date(2024, 1, 5), {"name": "IC Markets"}),
        "first name record",
    )
    history.append(first)

    # The broker rebrands. History is append-only: a new dated record, never a
    # mutation of the old one (the old one is frozen anyway).
    corrected = _unwrap(
        DatedRecord.try_create(venue, "2025-03-20", {"name": "IC Markets Global"}),
        "rename record",
    )
    history.append(corrected)
    return history


def refusals_never_default() -> tuple[TypedRefusal, TypedRefusal]:
    """A missing venue and a null metadata field each come back as a refusal."""
    missing_venue = Instrument.try_create(None, "EURUSD")
    assert isinstance(missing_venue, TypedRefusal)

    venue = _unwrap(VenueId.try_create("venue-x"), "VenueId")
    null_field = DatedRecord.try_create(venue, "2025-01-01", {"asset_class": None})
    assert isinstance(null_field, TypedRefusal)
    return missing_venue, null_field


def main() -> None:
    eurusd_a, eurusd_b = two_brokers_never_mix()
    print(f"two venues, one symbol, distinct instruments: {eurusd_a != eurusd_b}")

    account = account_carries_one_role(eurusd_a.venue)
    print(f"account {account.account_id} role={account.role.value}")

    history = rename_is_a_new_record(eurusd_a.venue)
    print(f"rename appended a new record; history has {len(history)} entries")

    missing_venue, null_field = refusals_never_default()
    print(
        f"missing venue refused: {missing_venue.category.value} / {missing_venue.context['field']}"
    )
    print(f"null field refused: {null_field.category.value} / {null_field.context['field']}")


if __name__ == "__main__":
    main()
