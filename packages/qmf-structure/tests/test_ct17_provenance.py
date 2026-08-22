"""Tier-1 tests for CT-17 Story 9.3: evidence class as identity, knowledge-time
provenance, and split-manifest governance.

Covers the acceptance criteria:

* evidence class (``confirmed | unconfirmed | provisional``) is a declared identity field
  and a named part of the result label; a read requesting confirmed evidence refuses an
  unconfirmed/provisional row with a ``policy rejection``, never a silent filter (FM-4);
* a decision at instant T may consume evidence with ``confirmed-at <= T`` (equality is
  consumption, not look-ahead), while the refuse-at-equal rule governs causality tests
  between derived artifacts, not consumption;
* a family's confirmation-delay bound feeds a split manifest's required embargo width; a
  manifest refuses a record whose observed-at precedes a boundary while its confirmed-at
  follows it, unless the declared embargo covers the gap (FM-7); an unbounded
  confirmation-delay declaration is excluded from split-governed evidence;
* an object computed on a revised input receives a different result label through its input
  fingerprints; the label carries producer contract identity, format version, input
  fingerprints, evidence time range, evidence class, and world; and
* live in-memory use persists nothing, but any object cited by a journal event or result
  label becomes governed evidence; scanners promote only confirmed objects.
"""

from __future__ import annotations

from typing import TypeVar

import pytest
from qmf.core import (
    Duration,
    EvidenceClass,
    ExactRational,
    Fingerprint,
    Instant,
    Instrument,
    Interval,
    Ok,
    Price,
    Result,
    ResultLabel,
    TypedRefusal,
    UnitKind,
    VenueId,
    World,
    is_ok,
)
from qmf.structure import (
    CONTRACT_FORMAT_VERSION,
    AnchorSpan,
    CitationKind,
    ConfirmationRule,
    DeclaredFamily,
    EvidenceRow,
    FamilyIdentity,
    GovernanceVerdict,
    SplitAdmission,
    StructureObject,
    admit_across_boundary,
    causally_precedes,
    evaluate_citation,
    may_consume,
    promote_scanned,
    read_confirmed,
    required_embargo_width,
    structure_result_label,
)

T = TypeVar("T")

_EURUSD = Instrument(venue=VenueId(value="ctrader"), symbol="EURUSD")

_T0 = 1_700_000_000_000_000_000
_MINUTE = 60_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), f"expected Ok, got {result}"
    assert isinstance(result, Ok)
    return result.value


def _price(value: int, scale: int = 5) -> Price:
    return _ok(Price.try_create(value, _EURUSD, scale))


def _rational(num: int, den: int) -> ExactRational:
    return _ok(ExactRational.try_create(num, den, UnitKind.DIMENSIONLESS_RATIO))


def _family(
    family_id: str = "swing-point",
    version: int = 1,
    geometry: str = "point",
    *,
    descriptor: str = "confirmed the moment a later bar closes beyond the pivot",
    bound: int | None = 3,
) -> DeclaredFamily:
    identity = _ok(FamilyIdentity.try_create(family_id, version, geometry))
    rule = _ok(ConfirmationRule.try_create(descriptor, confirmation_delay_bound=bound))
    return _ok(DeclaredFamily.try_create(identity, rule))


def _anchor(
    start: int = _T0,
    end: int = _T0 + _MINUTE,
    low: int = 108_000,
    high: int = 108_500,
) -> AnchorSpan:
    return _ok(
        AnchorSpan.try_create(
            Instant(value_ns=start), Instant(value_ns=end), _price(low), _price(high)
        )
    )


def _mint(
    *,
    observed_at: int = _T0 + 2 * _MINUTE,
    evidence_class: object = EvidenceClass.UNCONFIRMED,
    parameters: object | None = None,
    anchor: AnchorSpan | None = None,
    family: DeclaredFamily | None = None,
) -> StructureObject:
    return _ok(
        StructureObject.try_create(
            _family() if family is None else family,
            {"pivot_tolerance": _rational(1, 4)} if parameters is None else parameters,
            _anchor() if anchor is None else anchor,
            Instant(value_ns=observed_at),
            evidence_class,
        )
    )


def _inst(offset_minutes: int) -> Instant:
    return Instant(value_ns=_T0 + offset_minutes * _MINUTE)


# --- FM-4: evidence class is identity; the confirmed read refuses -----------


def test_evidence_class_is_a_declared_identity_field() -> None:
    confirmed = _mint(evidence_class=EvidenceClass.CONFIRMED)
    unconfirmed = _mint(evidence_class=EvidenceClass.UNCONFIRMED)
    # Evidence class is identity-bearing: two objects identical but for class fingerprint
    # differently, and it is a named part of the object's fp1 content.
    assert confirmed.fp1_identity()["evidence_class"] == "confirmed"
    assert _ok(confirmed.content_fingerprint()) != _ok(unconfirmed.content_fingerprint())


def test_structure_object_and_result_label_satisfy_the_evidence_row_seam() -> None:
    obj = _mint(evidence_class=EvidenceClass.CONFIRMED)
    label = _ok(structure_result_label(obj, world=World.REPLAY))
    assert isinstance(obj, EvidenceRow)
    assert isinstance(label, EvidenceRow)


def test_read_confirmed_returns_all_confirmed_rows() -> None:
    rows = [_mint(evidence_class=EvidenceClass.CONFIRMED) for _ in range(3)]
    result = _ok(read_confirmed(rows))
    assert result == tuple(rows)


def test_read_confirmed_empty_read_is_legal() -> None:
    assert _ok(read_confirmed([])) == ()


def test_read_confirmed_refuses_unconfirmed_row_not_filter() -> None:
    confirmed = _mint(evidence_class=EvidenceClass.CONFIRMED)
    unconfirmed = _mint(evidence_class=EvidenceClass.UNCONFIRMED)
    result = read_confirmed([confirmed, unconfirmed])
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "policy rejection"
    assert result.context["field"] == "rows"
    assert result.context["index"] == 1
    assert result.context["evidence_class"] == "unconfirmed"


def test_read_confirmed_refuses_provisional_row() -> None:
    provisional = _mint(evidence_class=EvidenceClass.PROVISIONAL)
    result = read_confirmed([provisional])
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "policy rejection"
    assert result.context["evidence_class"] == "provisional"


def test_read_confirmed_governs_result_label_rows() -> None:
    confirmed = _ok(
        structure_result_label(_mint(evidence_class=EvidenceClass.CONFIRMED), world=World.LIVE)
    )
    unconfirmed = _ok(
        structure_result_label(_mint(evidence_class=EvidenceClass.UNCONFIRMED), world=World.LIVE)
    )
    assert is_ok(read_confirmed([confirmed]))
    refused = read_confirmed([confirmed, unconfirmed])
    assert isinstance(refused, TypedRefusal)
    assert refused.category.value == "policy rejection"


def test_read_confirmed_refuses_non_sequence() -> None:
    result = read_confirmed("not-a-sequence")
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "invalid input"
    assert result.context["field"] == "rows"


def test_read_confirmed_refuses_non_evidence_row_element() -> None:
    result = read_confirmed([object()])
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "invalid input"
    assert result.context["field"] == "rows"


def test_read_confirmed_refuses_row_with_non_evidence_class() -> None:
    class _FakeRow:
        evidence_class = "confirmed"  # a bare string, not an EvidenceClass member

    result = read_confirmed([_FakeRow()])
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "invalid input"
    assert result.context["field"] == "rows"


# --- AC #2: knowledge-time consumption vs the causality test ----------------


def test_may_consume_allows_confirmed_at_before_t() -> None:
    result = _ok(may_consume(_inst(5), at=_inst(10)))
    assert result.value_ns == _inst(5).value_ns


def test_may_consume_equality_is_consumption() -> None:
    # confirmed-at == T is consumption, not look-ahead.
    result = _ok(may_consume(_inst(10), at=_inst(10)))
    assert result.value_ns == _inst(10).value_ns


def test_may_consume_refuses_lookahead() -> None:
    result = may_consume(_inst(11), at=_inst(10))
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "policy rejection"
    assert result.context["field"] == "confirmed_at"


def test_may_consume_refuses_bad_types() -> None:
    bad_conf = may_consume(object(), at=_inst(10))
    assert isinstance(bad_conf, TypedRefusal)
    assert bad_conf.context["field"] == "confirmed_at"
    bad_at = may_consume(_inst(5), at=object())
    assert isinstance(bad_at, TypedRefusal)
    assert bad_at.context["field"] == "at"


def test_causally_precedes_strictly_before_and_after() -> None:
    assert _ok(causally_precedes(_inst(5), later=_inst(10))) is True
    assert _ok(causally_precedes(_inst(10), later=_inst(5))) is False


def test_causally_precedes_refuses_at_equal() -> None:
    # Refuse-at-equal governs causality tests between derived artifacts (concurrent).
    result = causally_precedes(_inst(10), later=_inst(10))
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "policy rejection"


def test_causally_precedes_refuses_non_instant() -> None:
    result = causally_precedes(object(), later=_inst(10))
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "invalid input"


def test_consumption_and_causality_differ_at_equal() -> None:
    # The whole point of AC #2: equality is consumption but not a causal precedence.
    at_equal_consume = may_consume(_inst(7), at=_inst(7))
    at_equal_causal = causally_precedes(_inst(7), later=_inst(7))
    assert is_ok(at_equal_consume)
    assert isinstance(at_equal_causal, TypedRefusal)


# --- AC #4: the structure result label --------------------------------------


def test_structure_result_label_carries_every_part() -> None:
    obj = _mint(evidence_class=EvidenceClass.UNCONFIRMED)
    label = _ok(structure_result_label(obj, world=World.REPLAY))
    assert isinstance(label, ResultLabel)
    assert label.producer_contract_format_version == CONTRACT_FORMAT_VERSION
    assert label.evidence_class is EvidenceClass.UNCONFIRMED
    assert label.world is World.REPLAY
    # Default evidence time range is the object's anchor span.
    assert label.evidence_time_range.start.value_ns == obj.anchor.start.value_ns
    assert label.evidence_time_range.end.value_ns == obj.anchor.end.value_ns
    assert isinstance(label.producer_contract_identity, Fingerprint)


def test_result_label_producer_is_the_configured_family() -> None:
    # Two objects of the same configured family (same params) share a producer identity...
    a = _mint(evidence_class=EvidenceClass.CONFIRMED)
    b = _mint(evidence_class=EvidenceClass.CONFIRMED, anchor=_anchor(low=108_100))
    label_a = _ok(structure_result_label(a, world=World.LIVE))
    label_b = _ok(structure_result_label(b, world=World.LIVE))
    assert label_a.producer_contract_identity == label_b.producer_contract_identity


def test_result_label_differs_by_parameters() -> None:
    # ...but a different parameterization is a different producer identity.
    a = _mint(parameters={"pivot_tolerance": _rational(1, 4)})
    b = _mint(parameters={"pivot_tolerance": _rational(1, 2)})
    label_a = _ok(structure_result_label(a, world=World.LIVE))
    label_b = _ok(structure_result_label(b, world=World.LIVE))
    assert label_a.producer_contract_identity != label_b.producer_contract_identity


def test_revised_input_yields_a_different_label() -> None:
    obj = _mint(evidence_class=EvidenceClass.CONFIRMED)
    original_input = _ok(_mint().content_fingerprint())
    revised_input = _ok(_mint(anchor=_anchor(low=107_900)).content_fingerprint())
    label_original = _ok(
        structure_result_label(obj, world=World.LIVE, input_fingerprints=[original_input])
    )
    label_revised = _ok(
        structure_result_label(obj, world=World.LIVE, input_fingerprints=[revised_input])
    )
    # A revised input flows into a different computation identity — no silent change.
    assert original_input != revised_input
    assert label_original.computation_identity != label_revised.computation_identity


def test_identical_label_inputs_deduplicate() -> None:
    obj = _mint(evidence_class=EvidenceClass.CONFIRMED)
    inp = _ok(_mint().content_fingerprint())
    a = _ok(structure_result_label(obj, world=World.LIVE, input_fingerprints=[inp]))
    b = _ok(structure_result_label(obj, world=World.LIVE, input_fingerprints=[inp]))
    assert a.computation_identity == b.computation_identity


def test_structure_result_label_accepts_explicit_evidence_range() -> None:
    obj = _mint(evidence_class=EvidenceClass.CONFIRMED)
    rng = _ok(Interval.try_create(_inst(0), _inst(9)))
    label = _ok(structure_result_label(obj, world=World.LIVE, evidence_time_range=rng))
    assert label.evidence_time_range.end.value_ns == _inst(9).value_ns


def test_structure_result_label_refuses_simulated_world() -> None:
    obj = _mint(evidence_class=EvidenceClass.CONFIRMED)
    result = structure_result_label(obj, world=World.SIMULATED)
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "policy rejection"
    assert result.context["field"] == "world"


def test_structure_result_label_refuses_bad_inputs() -> None:
    obj = _mint(evidence_class=EvidenceClass.CONFIRMED)
    bad_obj = structure_result_label(object(), world=World.LIVE)
    assert isinstance(bad_obj, TypedRefusal)
    assert bad_obj.context["field"] == "obj"
    bad_world = structure_result_label(obj, world="not-a-world")
    assert isinstance(bad_world, TypedRefusal)
    assert bad_world.category.value == "invalid input"
    assert bad_world.context["field"] == "world"
    bad_range = structure_result_label(obj, world=World.LIVE, evidence_time_range=object())
    assert isinstance(bad_range, TypedRefusal)
    assert bad_range.context["field"] == "evidence_time_range"
    bad_input = structure_result_label(obj, world=World.LIVE, input_fingerprints=["not-a-fp"])
    assert isinstance(bad_input, TypedRefusal)
    assert bad_input.context["field"] == "input_fingerprints"


def test_structure_result_label_accepts_world_string() -> None:
    obj = _mint(evidence_class=EvidenceClass.CONFIRMED)
    label = _ok(structure_result_label(obj, world="replay"))
    assert label.world is World.REPLAY


# --- AC #5: the governed-evidence citation law ------------------------------


def test_in_memory_use_persists_nothing() -> None:
    verdict = _ok(evaluate_citation(CitationKind.IN_MEMORY))
    assert isinstance(verdict, GovernanceVerdict)
    assert verdict.governed is False
    assert verdict.must_persist is False


@pytest.mark.parametrize("citation", [CitationKind.JOURNAL_EVENT, CitationKind.RESULT_LABEL])
def test_citation_makes_object_governed_evidence(citation: CitationKind) -> None:
    verdict = _ok(evaluate_citation(citation))
    assert verdict.governed is True
    assert verdict.must_persist is True


def test_evaluate_citation_accepts_string_value() -> None:
    verdict = _ok(evaluate_citation("journal-event"))
    assert verdict.citation is CitationKind.JOURNAL_EVENT


def test_evaluate_citation_refuses_unknown_and_bad_type() -> None:
    unknown = evaluate_citation("promoted-by-magic")
    assert isinstance(unknown, TypedRefusal)
    assert unknown.category.value == "invalid input"
    assert unknown.context["field"] == "citation"
    bad_type = evaluate_citation(object())
    assert isinstance(bad_type, TypedRefusal)
    assert bad_type.context["field"] == "citation"


def test_promote_scanned_promotes_only_confirmed() -> None:
    confirmed = _mint(evidence_class=EvidenceClass.CONFIRMED)
    assert _ok(promote_scanned(confirmed)) is confirmed


@pytest.mark.parametrize("cls", [EvidenceClass.UNCONFIRMED, EvidenceClass.PROVISIONAL])
def test_promote_scanned_refuses_non_confirmed(cls: EvidenceClass) -> None:
    obj = _mint(evidence_class=cls)
    result = promote_scanned(obj)
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "policy rejection"
    assert result.context["field"] == "evidence_class"
    assert result.context["evidence_class"] == cls.value


def test_promote_scanned_refuses_non_object() -> None:
    result = promote_scanned(object())
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "obj"


# --- AC #3: the confirmation-delay bound feeds the embargo width -------------


def test_required_embargo_width_from_bound() -> None:
    rule = _family(bound=3).confirmation_rule
    width = _ok(required_embargo_width(rule, observation_width=Duration(value_ns=_MINUTE)))
    assert width.value_ns == 3 * _MINUTE


def test_required_embargo_width_zero_bound_is_zero_width() -> None:
    rule = _ok(
        ConfirmationRule.try_create("confirmed the instant derived", confirmation_delay_bound=0)
    )
    width = _ok(required_embargo_width(rule, observation_width=Duration(value_ns=_MINUTE)))
    assert width.value_ns == 0


def test_required_embargo_width_unbounded_family_excluded_from_splits() -> None:
    rule = _ok(ConfirmationRule.try_create("confirmed eventually", confirmation_delay_bound=None))
    result = required_embargo_width(rule, observation_width=Duration(value_ns=_MINUTE))
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "policy rejection"
    assert result.context["field"] == "confirmation_delay_bound"


def test_required_embargo_width_refuses_bad_inputs() -> None:
    rule = _family().confirmation_rule
    bad_rule = required_embargo_width(object(), observation_width=Duration(value_ns=_MINUTE))
    assert isinstance(bad_rule, TypedRefusal)
    assert bad_rule.context["field"] == "rule"
    bad_width = required_embargo_width(rule, observation_width=object())
    assert isinstance(bad_width, TypedRefusal)
    assert bad_width.context["field"] == "observation_width"
    non_positive = required_embargo_width(rule, observation_width=Duration(value_ns=0))
    assert isinstance(non_positive, TypedRefusal)
    assert non_positive.context["field"] == "observation_width"


# --- FM-7: the boundary-admission rule --------------------------------------


def _admit(*, boundary: int, observed: int, confirmed: int, embargo: int) -> Result[SplitAdmission]:
    return admit_across_boundary(
        boundary=_inst(boundary),
        observed_at=_inst(observed),
        confirmed_at=_inst(confirmed),
        embargo_width=Duration(value_ns=embargo * _MINUTE),
    )


def test_admit_non_straddling_record() -> None:
    # observed-at and confirmed-at both before the boundary — no straddle, admitted.
    admission = _ok(_admit(boundary=10, observed=2, confirmed=4, embargo=0))
    assert admission.straddles is False
    assert admission.partition_at.value_ns == _inst(4).value_ns


def test_admit_record_after_boundary() -> None:
    admission = _ok(_admit(boundary=2, observed=4, confirmed=6, embargo=0))
    assert admission.straddles is False


def test_admit_straddling_record_within_embargo() -> None:
    # observed-at before boundary, confirmed-at after; gap (3 min) <= embargo (5 min).
    admission = _ok(_admit(boundary=5, observed=4, confirmed=7, embargo=5))
    assert admission.straddles is True
    assert admission.gap_ns == 3 * _MINUTE
    assert admission.partition_at.value_ns == _inst(7).value_ns


def test_admit_refuses_straddle_beyond_embargo() -> None:
    # gap (6 min) > embargo (2 min): the record leaks across the boundary — refused.
    result = _admit(boundary=5, observed=3, confirmed=9, embargo=2)
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "policy rejection"
    assert result.context["field"] == "boundary"
    assert result.context["gap_ns"] == 6 * _MINUTE
    assert result.context["embargo_ns"] == 2 * _MINUTE


def test_admit_confirmed_at_equal_boundary_is_not_a_straddle() -> None:
    # confirmed-at == boundary does not "follow" it; the record partitions cleanly.
    admission = _ok(_admit(boundary=5, observed=3, confirmed=5, embargo=0))
    assert admission.straddles is False


def test_admit_observed_at_equal_boundary_is_not_a_straddle() -> None:
    # observed-at == boundary does not "precede" it.
    admission = _ok(_admit(boundary=5, observed=5, confirmed=8, embargo=0))
    assert admission.straddles is False


def test_admit_refuses_confirmed_before_observed() -> None:
    result = _admit(boundary=5, observed=8, confirmed=4, embargo=10)
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "invalid input"
    assert result.context["field"] == "confirmed_at"


def test_admit_refuses_bad_types() -> None:
    good: dict[str, object] = {
        "boundary": _inst(5),
        "observed_at": _inst(3),
        "confirmed_at": _inst(9),
        "embargo_width": Duration(value_ns=_MINUTE),
    }
    for field in ("boundary", "observed_at", "confirmed_at", "embargo_width"):
        result = admit_across_boundary(**{**good, field: object()})  # type: ignore[arg-type]
        assert isinstance(result, TypedRefusal)
        assert result.context["field"] == field


def test_admit_refuses_negative_embargo() -> None:
    result = admit_across_boundary(
        boundary=_inst(5),
        observed_at=_inst(3),
        confirmed_at=_inst(9),
        embargo_width=Duration(value_ns=-1),
    )
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "invalid input"
    assert result.context["field"] == "embargo_width"


# --- integration: the bound-derived embargo governs the boundary ------------


def test_bound_derived_embargo_admits_within_bound_refuses_beyond() -> None:
    # A family with a 3-observation delay bound at a 1-minute BarSpec => 3-minute embargo.
    rule = _family(bound=3).confirmation_rule
    embargo = _ok(required_embargo_width(rule, observation_width=Duration(value_ns=_MINUTE)))
    # A record confirmed within the bound (gap 3 min) straddling the boundary is admitted.
    within = admit_across_boundary(
        boundary=_inst(5), observed_at=_inst(4), confirmed_at=_inst(7), embargo_width=embargo
    )
    assert is_ok(within)
    # A record that took longer to confirm than declared (gap 5 min) is refused (FM-7).
    beyond = admit_across_boundary(
        boundary=_inst(5), observed_at=_inst(3), confirmed_at=_inst(8), embargo_width=embargo
    )
    assert isinstance(beyond, TypedRefusal)
    assert beyond.category.value == "policy rejection"
