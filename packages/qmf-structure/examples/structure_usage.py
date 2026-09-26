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

Story 9.3 — evidence class, knowledge-time provenance, and split-manifest governance:

7. A read requesting confirmed evidence refuses an unconfirmed row with a ``policy
   rejection`` — never a silent filter (FM-4).
8. A decision at T may consume evidence with ``confirmed-at <= T`` (equality is
   consumption); the refuse-at-equal rule is for causality tests, not consumption.
9. A structure object computed on a revised input receives a **different result label**
   through its input fingerprints, rather than silently changing.
10. A citation by a journal event or result label makes an object governed evidence; and a
    family's confirmation-delay bound feeds a split embargo that refuses a straddling
    record beyond it (FM-7).

Story 9.4 — the first governed family, the routing test, and the light/heavy benchmark:

11. The swing-point family (the first governed family) detects pivots from declared source/bar
    observations, mints them look-ahead-safe (observed at the right-window bar), and confirms
    one the moment a later bar closes beyond its break level — admitted through the same gate
    as any operator-authored peer, with no privilege (DEC-0133).
12. The routing test separates the libraries: a value per evaluation instant is CT-16, a
    discrete object with a birth and a lifetime is CT-17.
13. A light claim is policed: exceeding a declared bound (or lacking a baseline) is refused,
    and a peak-memory regression fails exactly as a slowdown does (FM-8).

Every ``fp1`` fingerprint is computed in qmf-core, and this module imports only qmf.core
and qmf.structure.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    Duration,
    EvidenceClass,
    ExactRational,
    Instant,
    Instrument,
    Price,
    Result,
    TypedRefusal,
    UnitKind,
    VenueId,
    World,
    fingerprint,
    is_ok,
)
from qmf.structure import (
    AnchorSpan,
    BenchmarkRung,
    CitationKind,
    ConfirmationRecord,
    ConfirmationRule,
    DeclaredBudget,
    DeclaredFamily,
    FamilyIdentity,
    HighLowObservation,
    InvalidationRecord,
    LifecycleEdgeKind,
    Measurement,
    RoutingKind,
    StructureObject,
    SwingKind,
    SwingPointFamily,
    admit_across_boundary,
    admit_to_governed_library,
    causally_precedes,
    check_emission_invariant,
    check_regression,
    evaluate_citation,
    evaluate_light_claim,
    may_consume,
    read_confirmed,
    refit,
    required_embargo_width,
    resolve_state,
    route,
    structure_result_label,
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


def _minted(evidence_class: EvidenceClass, low: int = 108_000) -> StructureObject:
    """Mint an object with a chosen evidence class (a Story 9.3 identity field)."""
    anchor = _unwrap(
        AnchorSpan.try_create(
            Instant(value_ns=1_700_000_000_000_000_000),
            Instant(value_ns=1_700_000_060_000_000_000),
            _price(low),
            _price(low + 500),
        ),
        "anchor span",
    )
    return _unwrap(
        StructureObject.try_create(
            _family(),
            _tolerance(),
            anchor,
            Instant(value_ns=1_700_000_120_000_000_000),
            evidence_class,
        ),
        "minted object",
    )


def confirmed_read_refuses_unconfirmed() -> str:
    """A read requesting confirmed evidence refuses an unconfirmed row — never a filter."""
    confirmed = _minted(EvidenceClass.CONFIRMED)
    unconfirmed = _minted(EvidenceClass.UNCONFIRMED, low=108_100)
    result = read_confirmed([confirmed, unconfirmed])
    assert isinstance(result, TypedRefusal)  # not a silent filter — a refusal (FM-4)
    assert result.category.value == "policy rejection"
    return result.category.value


def consumption_vs_causality() -> tuple[bool, bool]:
    """Equality is consumption; the causality test refuses equal (concurrent) instants."""
    t = Instant(value_ns=1_700_000_120_000_000_000)
    consumed = is_ok(may_consume(t, at=t))  # confirmed-at == T is consumption
    causal = causally_precedes(t, later=t)  # equal instants: refuse-at-equal
    causal_refused = isinstance(causal, TypedRefusal)
    assert consumed is True
    assert causal_refused
    return consumed, causal_refused


def revised_input_gives_a_different_label() -> bool:
    """A structure object computed on a revised input receives a different result label."""
    obj = _minted(EvidenceClass.CONFIRMED)
    original = _unwrap(_minted(EvidenceClass.CONFIRMED, low=107_500).content_fingerprint(), "in")
    revised = _unwrap(_minted(EvidenceClass.CONFIRMED, low=107_600).content_fingerprint(), "in")
    label_a = _unwrap(
        structure_result_label(obj, world=World.LIVE, input_fingerprints=[original]), "label a"
    )
    label_b = _unwrap(
        structure_result_label(obj, world=World.LIVE, input_fingerprints=[revised]), "label b"
    )
    return label_a.computation_identity != label_b.computation_identity


def citation_makes_object_governed_evidence() -> bool:
    """In-memory use persists nothing; a result-label citation makes it governed evidence."""
    in_memory = _unwrap(evaluate_citation(CitationKind.IN_MEMORY), "in-memory verdict")
    cited = _unwrap(evaluate_citation(CitationKind.RESULT_LABEL), "cited verdict")
    assert in_memory.governed is False
    assert cited.governed is True
    return cited.governed and not in_memory.governed


def split_embargo_refuses_a_straddling_record() -> str:
    """A family's confirmation-delay bound feeds a split embargo that refuses a leak (FM-7)."""
    minute = 60_000_000_000
    rule = _family().confirmation_rule  # a 3-observation delay bound
    embargo = _unwrap(
        required_embargo_width(rule, observation_width=Duration(value_ns=minute)), "embargo"
    )
    base = 1_700_000_000_000_000_000
    # A record confirmed later than its declared bound straddles the boundary and leaks.
    result = admit_across_boundary(
        boundary=Instant(value_ns=base + 5 * minute),
        observed_at=Instant(value_ns=base + 3 * minute),
        confirmed_at=Instant(value_ns=base + 9 * minute),
        embargo_width=embargo,
    )
    assert isinstance(result, TypedRefusal)
    return result.category.value


def _bar(index: int, high: int, low: int, close: int) -> HighLowObservation:
    """A declared source/bar observation the swing-point family consumes as a declared input."""
    return _unwrap(
        HighLowObservation.try_create(
            Instant(value_ns=1_700_000_000_000_000_000 + index * 60_000_000_000),
            _price(high),
            _price(low),
            _price(close),
        ),
        "observation",
    )


def swing_family_detects_confirms_and_holds_no_privilege() -> tuple[str, bool]:
    """The first governed family: detect a look-ahead-safe pivot, confirm it, and prove no
    privilege — it is admitted through the same gate as any operator-authored family."""
    family = _unwrap(
        SwingPointFamily.create(left=1, right=1, confirmation_delay_bound=3), "swing family"
    )
    series = [
        _bar(0, 108_100, 107_900, 108_000),
        _bar(1, 108_300, 108_000, 108_200),
        _bar(2, 108_900, 108_400, 108_600),  # a swing high
        _bar(3, 108_500, 108_100, 108_300),
        _bar(4, 108_450, 107_500, 107_600),  # closes below the pivot low: confirms the high
        _bar(5, 108_400, 108_000, 108_350),
    ]
    swings = _unwrap(family.detect(series), "detected swings")
    high = next(swing for swing in swings if swing.kind is SwingKind.HIGH)
    # Observed at the right-window bar (index 3), never at the pivot bar (index 2): no repaint.
    assert high.object.observed_at == Instant(
        value_ns=1_700_000_000_000_000_000 + 3 * 60_000_000_000
    )
    record = _unwrap(family.confirmation_for(high, series), "confirmation")
    assert isinstance(record, ConfirmationRecord)
    # No privilege: the seed family is admitted exactly as any operator-authored peer.
    admitted = is_ok(admit_to_governed_library(family))
    return str(record.at.value_ns), admitted


def routing_test_separates_the_libraries() -> tuple[str, str]:
    """A value per evaluation instant is CT-16; a discrete object with a lifetime is CT-17."""
    indicator = _unwrap(
        route(value_per_evaluation_instant=True, discrete_with_birth_and_lifetime=False), "ct16"
    )
    structure = _unwrap(
        route(value_per_evaluation_instant=False, discrete_with_birth_and_lifetime=True), "ct17"
    )
    assert indicator is RoutingKind.VALUE_PER_INSTANT
    assert structure is RoutingKind.DISCRETE_OBJECT
    return indicator.value, structure.value


def light_claim_is_policed_and_memory_regresses_like_a_slowdown() -> tuple[bool, bool]:
    """A light claim without a baseline is refused; a peak-memory regression fails the gate."""
    budget = _unwrap(
        DeclaredBudget.try_create(
            per_update_cost_ceiling_ns=1_000,
            object_set_size_ceiling=200,
            scan_window_ceiling=50,
            synchronous_available=True,
        ),
        "budget",
    )
    no_baseline = evaluate_light_claim(
        budget, per_update_cost_ns=500, object_set_size=100, scan_window=20, has_baseline=False
    )
    baseline = Measurement(rung=BenchmarkRung.ACTIVE_OBJECT_SET_SIZE, seconds=1.0, peak_bytes=1_000)
    regressed = check_regression(
        baseline,
        Measurement(rung=BenchmarkRung.ACTIVE_OBJECT_SET_SIZE, seconds=1.0, peak_bytes=2_000),
        tolerance_bps=0,
    )
    return isinstance(no_baseline, TypedRefusal), isinstance(regressed, TypedRefusal)


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

    refused = confirmed_read_refuses_unconfirmed()
    print(f"confirmed read refuses an unconfirmed row: {refused}")

    consumed, causal_refused = consumption_vs_causality()
    print(f"equality is consumption ({consumed}), causality refuses equal ({causal_refused})")

    print(
        f"revised input yields a different result label: {revised_input_gives_a_different_label()}"
    )

    print(f"citation makes object governed evidence: {citation_makes_object_governed_evidence()}")

    split_refused = split_embargo_refuses_a_straddling_record()
    print(f"split embargo refuses a straddling record: {split_refused}")

    confirmed_at, admitted = swing_family_detects_confirms_and_holds_no_privilege()
    print(
        f"swing-point family confirms a pivot at {confirmed_at} (admitted={admitted}, no privilege)"
    )

    ct16, ct17 = routing_test_separates_the_libraries()
    print(f"routing test: value-per-instant is {ct16}, discrete-object is {ct17}")

    no_baseline_refused, memory_regression_refused = (
        light_claim_is_policed_and_memory_regresses_like_a_slowdown()
    )
    print(
        f"light claim without a baseline refused: {no_baseline_refused}; "
        f"peak-memory regression fails like a slowdown: {memory_regression_refused}"
    )


if __name__ == "__main__":
    main()
