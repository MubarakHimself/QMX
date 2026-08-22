"""Reference usage — CT-17 causal structure object mint and emission invariant
(COMP-QMF-STRUCTURE).

Executable::

    python packages/qmf-structure/examples/structure_usage.py

Shows the five things Story 9.1 pins down:

1. A structure object is minted **once at observation** against a declared family,
   carrying family identity + version, exact-rational parameters, its confirmation rule,
   its anchor span, ``observed_at`` (knowledge time), and its evidence class — and it
   returns fingerprintable content whose ``fp1`` is derived, never minted.
2. Identical work from two sandboxes deduplicates: the same fact minted twice lands on
   one ``fp1``, so evidence merges by construction.
3. The object is immutable — a frozen, minted-once fact — and carries no writer, no
   sequence, no created-at; the composition root stamps the registry record.
4. The emission invariant is checked in-component: an anchor whose end follows
   ``observed_at``, and an ``observed_at`` behind a consumed input's evidence time, are
   each ``invalid input`` refusals (FM-1). Equal instants are legal (consumption, not
   look-ahead).
5. Every ``fp1`` fingerprint is computed in qmf-core, and this module imports only
   qmf.core and qmf.structure.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    EvidenceClass,
    ExactRational,
    Instant,
    Instrument,
    Price,
    Result,
    TypedRefusal,
    UnitKind,
    VenueId,
    fingerprint,
    is_ok,
)
from qmf.structure import (
    AnchorSpan,
    ConfirmationRule,
    DeclaredFamily,
    FamilyIdentity,
    StructureObject,
    check_emission_invariant,
)

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    """Tiny demo helper: a construction we assert must succeed here."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instrument() -> Instrument:
    return Instrument(venue=VenueId(value="ctrader"), symbol="EURUSD")


def _price(value: int) -> Price:
    return _unwrap(Price.try_create(value, _instrument(), 5), "price")


def _family() -> DeclaredFamily:
    """A swing-point family: geometry declared, confirmation rule precise."""
    identity = _unwrap(FamilyIdentity.try_create("swing-point", 1, "point"), "family identity")
    rule = _unwrap(
        ConfirmationRule.try_create(
            "confirmed the moment a later bar closes beyond the pivot",
            confirmation_delay_bound=3,
        ),
        "confirmation rule",
    )
    return _unwrap(DeclaredFamily.try_create(identity, rule), "declared family")


def _tolerance() -> dict[str, ExactRational]:
    return {
        "pivot_tolerance": _unwrap(
            ExactRational.try_create(1, 4, UnitKind.DIMENSIONLESS_RATIO), "tolerance"
        )
    }


def minted_object_has_derived_fingerprint() -> StructureObject:
    """A structure object minted at observation, its fp1 derived from its content."""
    anchor = _unwrap(
        AnchorSpan.try_create(
            Instant(value_ns=1_700_000_000_000_000_000),
            Instant(value_ns=1_700_000_060_000_000_000),
            _price(108_000),
            _price(108_500),
        ),
        "anchor span",
    )
    obj = _unwrap(
        StructureObject.try_create(
            _family(),
            _tolerance(),
            anchor,
            # observed-at is at or after the anchor end and the newest consumed input.
            Instant(value_ns=1_700_000_120_000_000_000),
            EvidenceClass.UNCONFIRMED,
            consumed_input_times=[Instant(value_ns=1_700_000_090_000_000_000)],
        ),
        "minted object",
    )
    derived = _unwrap(obj.content_fingerprint(), "content fingerprint")
    assert derived.value.startswith("fp1:sha256:")
    assert derived == _unwrap(fingerprint(obj.fp1_identity()), "recomputed fingerprint")
    return obj


def two_sandboxes_deduplicate() -> tuple[str, str]:
    """The same fact minted twice lands on one fp1 — evidence merges by construction."""
    first = minted_object_has_derived_fingerprint()
    second = minted_object_has_derived_fingerprint()
    a = _unwrap(first.content_fingerprint(), "first fp1")
    b = _unwrap(second.content_fingerprint(), "second fp1")
    assert a == b
    return a.value, b.value


def object_is_immutable_and_unstamped() -> None:
    """The minted object is frozen evidence and carries no writer/sequence/created-at.

    Immutability is shown two ways: the parameter mapping is snapshot at mint, so a later
    mutation of the caller's dict can never reach into the frozen fact; and the object
    exposes no stamping fields — the composition root, not the library, holds the
    ``WriterId`` and the per-writer sequence.
    """
    mutable = _tolerance()
    anchor = _unwrap(
        AnchorSpan.try_create(
            Instant(value_ns=1_700_000_000_000_000_000),
            Instant(value_ns=1_700_000_060_000_000_000),
            _price(108_000),
            _price(108_500),
        ),
        "anchor span",
    )
    obj = _unwrap(
        StructureObject.try_create(
            _family(),
            mutable,
            anchor,
            Instant(value_ns=1_700_000_120_000_000_000),
            EvidenceClass.UNCONFIRMED,
        ),
        "minted object",
    )
    mutable["pivot_tolerance"] = _unwrap(
        ExactRational.try_create(9, 10, UnitKind.DIMENSIONLESS_RATIO), "tampered tolerance"
    )
    assert obj.parameters["pivot_tolerance"].numerator == 1  # unchanged by the mutation
    assert not hasattr(obj, "writer")
    assert not hasattr(obj, "sequence")
    assert not hasattr(obj, "created_at")


def emission_invariant_refuses_lookahead() -> tuple[TypedRefusal, TypedRefusal]:
    """An anchor end after observed-at, and observed-at behind a consumed input, are FM-1."""
    late_anchor = _unwrap(
        AnchorSpan.try_create(
            Instant(value_ns=1_700_000_000_000_000_000),
            Instant(value_ns=1_700_000_500_000_000_000),  # end AFTER observed-at below
            _price(108_000),
            _price(108_500),
        ),
        "late anchor",
    )
    ordering = check_emission_invariant(
        anchor=late_anchor,
        observed_at=Instant(value_ns=1_700_000_120_000_000_000),
    )
    assert isinstance(ordering, TypedRefusal)
    assert ordering.category.value == "invalid input"

    good_anchor = _unwrap(
        AnchorSpan.try_create(
            Instant(value_ns=1_700_000_000_000_000_000),
            Instant(value_ns=1_700_000_060_000_000_000),
            _price(108_000),
            _price(108_500),
        ),
        "good anchor",
    )
    lookahead = check_emission_invariant(
        anchor=good_anchor,
        observed_at=Instant(value_ns=1_700_000_120_000_000_000),
        consumed_input_times=[
            Instant(value_ns=1_700_000_500_000_000_000)
        ],  # newer than observed-at
    )
    assert isinstance(lookahead, TypedRefusal)
    assert lookahead.category.value == "invalid input"
    return ordering, lookahead


def main() -> None:
    obj = minted_object_has_derived_fingerprint()
    fp = _unwrap(obj.content_fingerprint(), "fp1")
    print(f"minted at observation, derived fp1: {fp.value[:19]}...")

    a, b = two_sandboxes_deduplicate()
    print(f"two sandboxes deduplicate: {a == b}")

    object_is_immutable_and_unstamped()
    print("object immutable and unstamped (no writer/sequence/created-at)")

    ordering, lookahead = emission_invariant_refuses_lookahead()
    print(f"anchor end after observed-at refused: {ordering.category.value}")
    print(f"observed-at behind consumed input refused: {lookahead.category.value}")


if __name__ == "__main__":
    main()
