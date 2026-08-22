"""Reference usage — CT-17 causal structure object mint, emission invariant, and the
append-only lifecycle with its read-time fold (COMP-QMF-STRUCTURE).

Executable::

    python packages/qmf-structure/examples/structure_usage.py

Shows what Stories 9.1 and 9.2 pin down.

Story 9.1 — the mint and the emission invariant:

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

Story 9.2 — the append-only lifecycle and the read-time fold:

5. Confirmation, invalidation, and interaction records are separate append-only typed
   records referencing the object by ``fp1``; "still valid at T" is a **read-time fold**
   over the record stream, never a stored field. Reading at a later T sees a later fact;
   reading before it does not (look-ahead-safe).
6. A refit mints a **new** artifact with a ``supersedes`` edge and keeps the lineage's
   first observed-at; the prior object is untouched — a correction never overwrites (FM-3).

Every ``fp1`` fingerprint is computed in qmf-core, and this module imports only qmf.core
and qmf.structure.
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
    ConfirmationRecord,
    ConfirmationRule,
    DeclaredFamily,
    FamilyIdentity,
    InvalidationRecord,
    LifecycleEdgeKind,
    StructureObject,
    check_emission_invariant,
    refit,
    resolve_state,
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


def lifecycle_state_is_a_read_time_fold() -> tuple[bool, bool]:
    """Confirmation/invalidation are append-only records; validity is a read-time fold."""
    obj = minted_object_has_derived_fingerprint()
    obj_fp = _unwrap(obj.content_fingerprint(), "object fp1")
    invalidation = _unwrap(
        InvalidationRecord.try_create(obj_fp, Instant(value_ns=1_700_000_360_000_000_000)),
        "invalidation record",
    )
    # Read before the invalidation instant: still valid. Read after it: no longer valid.
    before = _unwrap(
        resolve_state(obj, [invalidation], at=Instant(value_ns=1_700_000_300_000_000_000)),
        "state before",
    )
    after = _unwrap(
        resolve_state(obj, [invalidation], at=Instant(value_ns=1_700_000_400_000_000_000)),
        "state after",
    )
    assert not hasattr(obj, "still_valid")  # never a stored field
    assert before.still_valid is True
    assert after.still_valid is False
    return before.still_valid, after.still_valid


def confirmation_record_references_object_by_fingerprint() -> str:
    """A confirmation record references its object by fp1 and its instant is identity."""
    obj = minted_object_has_derived_fingerprint()
    obj_fp = _unwrap(obj.content_fingerprint(), "object fp1")
    record = _unwrap(
        ConfirmationRecord.try_create(obj_fp, Instant(value_ns=1_700_000_300_000_000_000)),
        "confirmation record",
    )
    assert record.object_ref == obj_fp
    return _unwrap(record.content_fingerprint(), "record fp1").value


def refit_mints_a_new_artifact_not_an_overwrite() -> tuple[str, str]:
    """A refit mints a new artifact with a supersedes edge; the prior object is untouched."""
    prior = minted_object_has_derived_fingerprint()
    prior_fp = _unwrap(prior.content_fingerprint(), "prior fp1")
    new_anchor = _unwrap(
        AnchorSpan.try_create(
            Instant(value_ns=1_700_000_000_000_000_000),
            Instant(value_ns=1_700_000_060_000_000_000),
            _price(108_100),  # a new fit
            _price(108_700),
        ),
        "refit anchor",
    )
    result = _unwrap(
        refit(prior, anchor=new_anchor, observed_at=Instant(value_ns=1_700_000_300_000_000_000)),
        "refit",
    )
    assert result.supersedes_edge.kind is LifecycleEdgeKind.SUPERSEDES
    assert result.superseded_ref == prior_fp
    assert _unwrap(prior.content_fingerprint(), "prior fp1 after") == prior_fp  # untouched
    return prior_fp.value, _unwrap(result.superseding.content_fingerprint(), "new fp1").value


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

    before, after = lifecycle_state_is_a_read_time_fold()
    print(f"still valid is a read-time fold (before={before}, after={after})")

    record_fp = confirmation_record_references_object_by_fingerprint()
    print(f"confirmation record references object by fp1: {record_fp[:19]}...")

    prior_fp, new_fp = refit_mints_a_new_artifact_not_an_overwrite()
    print(f"refit mints a new artifact, prior untouched: {prior_fp != new_fp}")


if __name__ == "__main__":
    main()
