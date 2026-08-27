"""L3 acceptance tests for Epic 9 — oracle = epics.md Epic 9 acceptance criteria.

Epic-specific CT-17 behaviour, one behaviour one level. Every effect is observed through
the public surface or an injected fake owned by the test; refusals are observed as returned
TypedRefusals (never raised); absence-of-effect is observed by inspecting the returned
value, not by trusting a flag. Covers QA-E09-L3-001..018.
"""

from __future__ import annotations

import dataclasses

import pytest
from qmf.core import (
    CalendarIdentity,
    Duration,
    EvidenceClass,
    Fingerprint,
    Instant,
    ResultLabel,
    World,
    is_ok,
    is_refusal,
)
from qmf.structure import (
    BenchmarkRung,
    CitationKind,
    ConfirmationRecord,
    ConfirmationRule,
    DeclaredBudget,
    DeclaredFamily,
    FamilyIdentity,
    IndicatorResultInput,
    InteractionRecord,
    InvalidationRecord,
    LifecycleEdgeKind,
    Measurement,
    ResolvedState,
    RoutingKind,
    StructureObject,
    admit_across_boundary,
    admit_to_governed_library,
    causally_precedes,
    check_emission_invariant,
    check_regression,
    consume_indicator_input,
    evaluate_citation,
    evaluate_light_claim,
    graduate_to_governed,
    may_consume,
    promote_scanned,
    read_confirmed,
    refit,
    required_embargo_width,
    resolve_cascade,
    resolve_state,
    route,
    structure_result_label,
    CalendarAnchoredLevel,
)

import _helpers as H


# ===========================================================================
# QA-E09-L3-001 (P0) — the flagship future-leak refusal
# ===========================================================================


def test_l3_001_observed_at_behind_a_consumed_input_is_refused() -> None:
    # A stamped observed-at earlier than an input actually consumed is a look-ahead mint.
    result = H.mint(observed_min=2, consumed=[H.inst(9)])
    assert is_refusal(result)
    assert result.category.value == "invalid input"
    assert result.context["field"] == "observed_at"


def test_l3_001_confirmed_before_observed_is_refused() -> None:
    # A confirmed-at referencing an instant not knowable at observation is refused.
    result = check_emission_invariant(
        anchor=H.anchor(0, 1), observed_at=H.inst(3), confirmed_at=H.inst(2)
    )
    assert is_refusal(result)
    assert result.context["field"] == "confirmed_at"


def test_l3_001_causality_refuses_at_equal_but_consumption_admits_at_equal() -> None:
    # The causality test between derived artifacts refuses at confirmed-at == T ...
    causal = causally_precedes(H.inst(5), later=H.inst(5))
    assert is_refusal(causal)
    assert causal.category.value == "policy rejection"
    # ... while a consumer at T with confirmed-at <= T (equality) is admitted.
    assert is_ok(may_consume(H.inst(5), at=H.inst(5)))


def _series():
    return [
        H.observation(0, high=108_100, low=108_000, close=108_050),
        H.observation(1, high=108_200, low=108_050, close=108_150),
        H.observation(2, high=108_500, low=108_100, close=108_400),
        H.observation(3, high=108_200, low=108_050, close=108_100),
        H.observation(4, high=108_100, low=108_000, close=108_050),
    ]


def test_l3_001_real_family_pivots_are_never_dated_before_their_payload() -> None:
    # A pivot is not derivable until its right-window bar exists: no minted pivot's
    # observed-at precedes its own anchor (a repainted / look-ahead swing is impossible).
    swings = H.ok(H.swing_family(left=1, right=1).detect(_series()))
    assert swings, "expected at least one detected pivot"
    for swing in swings:
        obj = swing.object
        assert obj.observed_at.value_ns >= obj.anchor.end.value_ns
        assert obj.observed_at.value_ns >= obj.anchor.start.value_ns


# ===========================================================================
# QA-E09-L3-002 (P0) — minted once, immutable, every field identity-bearing
# ===========================================================================


def test_l3_002_object_carries_every_identity_field_and_is_frozen() -> None:
    obj = H.minted()
    assert isinstance(obj.family, FamilyIdentity)
    assert obj.family.version == 1
    assert isinstance(obj.confirmation_rule, ConfirmationRule)
    assert "pivot_tolerance" in obj.parameters
    assert obj.observed_at.value_ns == H.inst(2).value_ns
    assert obj.evidence_class is EvidenceClass.UNCONFIRMED
    # Anchor span, observed-at, and evidence class are identity fields (in fp1 content).
    content = obj.fp1_identity()
    for key in ("family", "parameters", "confirmation_rule", "anchor_span", "observed_at", "evidence_class"):
        assert key in content
    with pytest.raises(dataclasses.FrozenInstanceError):
        obj.observed_at = H.inst(3)  # type: ignore[misc]


def test_l3_002_a_change_is_a_new_artifact_not_a_mutation() -> None:
    prior = H.minted(observed_min=2)
    changed = H.ok(refit(prior, anchor=H.anchor(low=108_100), observed_at=H.inst(8)))
    assert H.fp(changed.superseding) != H.fp(prior)  # every change mints a new fp


# ===========================================================================
# QA-E09-L3-003 (P0) — knowledge-time semantics; anchor excluded from causality
# ===========================================================================


def test_l3_003_anchor_may_precede_observed_at() -> None:
    # The anchor is payload geometry frozen at observation, permitted to precede observed-at.
    obj = H.ok(H.mint(anc=H.anchor(start_min=0, end_min=1), observed_min=10))
    assert obj.anchor.start.value_ns < obj.observed_at.value_ns


def test_l3_003_anchor_excluded_from_causal_test_but_observed_at_is_not() -> None:
    # A consumed input later than the anchor but <= observed-at is fine (anchor not compared);
    # a consumed input later than observed-at is a look-ahead refusal.
    ok_case = H.mint(anc=H.anchor(0, 1), observed_min=10, consumed=[H.inst(9)])
    leak = H.mint(anc=H.anchor(0, 1), observed_min=10, consumed=[H.inst(11)])
    assert is_ok(ok_case)
    assert is_refusal(leak)
    assert leak.context["field"] == "observed_at"


def test_l3_003_standing_object_declares_observed_at_as_config_instant() -> None:
    fam = H.family(geometry="level")
    level = H.ok(
        CalendarAnchoredLevel.try_create(
            family=fam.identity,
            confirmation_rule=fam.confirmation_rule,
            calendar=H.ok(CalendarIdentity.try_create("forex-17NY", "v3", "2024a")),
            sampling_policy="last-known-at-or-before",
            schedule_gap_policy="refuse",
            level=H.price(108_250),
            observed_at=H.inst(0),
            evidence_class=EvidenceClass.CONFIRMED,
        )
    )
    assert level.observed_at.value_ns == H.inst(0).value_ns  # config instant is observed-at


# ===========================================================================
# QA-E09-L3-004 (P0) — three separate append-only records, referenced by fp
# ===========================================================================


def test_l3_004_records_are_separate_kinds_referencing_object_by_fingerprint() -> None:
    obj = H.minted()
    ref = H.fp(obj)
    conf = H.ok(ConfirmationRecord.try_create(ref, H.inst(3)))
    inval = H.ok(InvalidationRecord.try_create(ref, H.inst(6)))
    inter = H.ok(InteractionRecord.try_create(ref, H.inst(4), H.price(108_100), "touch", H.rational(1, 10)))
    assert type(conf) is not type(inval) is not type(inter)
    for record in (conf, inval, inter):
        assert record.object_ref == ref  # each references the object by its fp1


def test_l3_004_each_record_instant_is_identity_bearing() -> None:
    ref = H.fp(H.minted())
    a = H.ok(ConfirmationRecord.try_create(ref, H.inst(3)))
    b = H.ok(ConfirmationRecord.try_create(ref, H.inst(4)))
    assert H.ok(a.content_fingerprint()) != H.ok(b.content_fingerprint())


def test_l3_004_records_are_frozen_no_in_place_edit() -> None:
    inter = H.ok(InteractionRecord.try_create(H.fp(H.minted()), H.inst(4), H.price(108_100), "touch", H.rational(1, 10)))
    with pytest.raises(dataclasses.FrozenInstanceError):
        inter.at = H.inst(0)  # type: ignore[misc]


# ===========================================================================
# QA-E09-L3-005 (P1) — still-valid-at-T is a read-time fold, never stored
# ===========================================================================


def _expected_still_valid(*, observed_min: int, invalidation_min: int | None, t_min: int) -> bool:
    exists = observed_min <= t_min
    invalidated = invalidation_min is not None and invalidation_min <= t_min
    return exists and not invalidated


def test_l3_005_still_valid_is_a_fold_matching_an_independent_oracle() -> None:
    obj = H.minted(observed_min=2)
    inval = H.ok(InvalidationRecord.try_create(H.fp(obj), H.inst(6)))
    # No stored state on the object.
    for attr in ("still_valid", "confirmed", "invalidated"):
        assert not hasattr(obj, attr)
    for t in (1, 2, 5, 6, 7):
        state = H.ok(resolve_state(obj, [inval], at=H.inst(t)))
        assert state.still_valid is _expected_still_valid(observed_min=2, invalidation_min=6, t_min=t)


# ===========================================================================
# QA-E09-L3-006 (P0) — no overwrite; a refit is a new artifact (FM-3)
# ===========================================================================


def test_l3_006_refit_mints_new_artifact_keeps_first_observed_at_prior_untouched() -> None:
    prior = H.minted(observed_min=2)
    prior_fp_before = H.fp(prior)
    result = H.ok(refit(prior, anchor=H.anchor(low=108_100, high=108_600), observed_at=H.inst(8)))
    # a new, distinct artifact with a supersedes edge from new -> prior
    assert H.fp(result.superseding) != prior_fp_before
    assert result.supersedes_edge.kind is LifecycleEdgeKind.SUPERSEDES
    assert result.supersedes_edge.from_ref == H.fp(result.superseding)
    assert result.supersedes_edge.to_ref == prior_fp_before
    # the lineage head keeps the FIRST observed-at
    assert result.first_observed_at.value_ns == H.inst(2).value_ns
    # the prior object is untouched immutable evidence
    assert H.fp(prior) == prior_fp_before
    assert prior.observed_at.value_ns == H.inst(2).value_ns


# ===========================================================================
# QA-E09-L3-007 (P0) — admissibility bar (FM-2)
# ===========================================================================


def test_l3_007_precise_and_clock_confirmed_admitted_imprecise_refused() -> None:
    precise = H.family()
    assert is_ok(admit_to_governed_library(precise))
    clock = H.family(descriptor="confirmed the instant it is derived", clock_confirmed=True, bound=0)
    assert is_ok(admit_to_governed_library(clock))
    # An imprecise (blank) rule hand-built past try_create is turned away into the research lane.
    blank_rule = ConfirmationRule(descriptor="   ", clock_confirmed=False, confirmation_delay_bound=None)
    imprecise = DeclaredFamily(
        identity=H.ok(FamilyIdentity.try_create("vague", 1, "zone")), confirmation_rule=blank_rule
    )
    refused = admit_to_governed_library(imprecise)
    assert is_refusal(refused)
    assert refused.category.value == "policy rejection"


# ===========================================================================
# QA-E09-L3-008 (P1) — invalidation never cascades automatically
# ===========================================================================


class _FiresWhenParentInvalidated:
    def cascades(self, *, parent: ResolvedState, child: ResolvedState, at: Instant) -> bool:
        return parent.invalidated


class _NeverFires:
    def cascades(self, *, parent: ResolvedState, child: ResolvedState, at: Instant) -> bool:
        return False


def _parent_and_child_states():
    parent = H.minted(observed_min=1)
    child = H.minted(observed_min=2, evidence_class=EvidenceClass.CONFIRMED)
    parent_inval = H.ok(InvalidationRecord.try_create(H.fp(parent), H.inst(6)))
    at = H.inst(10)
    return (
        H.ok(resolve_state(child, [], at=at)),
        H.ok(resolve_state(parent, [parent_inval], at=at)),
        at,
    )


def test_l3_008_childs_own_fold_does_not_cascade() -> None:
    child_state, parent_state, _ = _parent_and_child_states()
    assert parent_state.invalidated is True
    assert child_state.still_valid is True  # no automatic cascade


def test_l3_008_cascade_is_opt_in_and_read_time_only() -> None:
    child_state, parent_state, at = _parent_and_child_states()
    fired = H.ok(resolve_cascade(child_state, parent_state, _FiresWhenParentInvalidated(), at=at))
    assert fired.cascade_invalidated is True
    assert fired.still_valid is False
    assert child_state.still_valid is True  # the child's own read is unchanged
    idle = H.ok(resolve_cascade(child_state, parent_state, _NeverFires(), at=at))
    assert idle.still_valid is True


# ===========================================================================
# QA-E09-L3-009 (P1) — evidence class identity + confirmed-as edge
# ===========================================================================


def test_l3_009_evidence_class_identity_and_confirmed_as_edge() -> None:
    confirmed = H.minted(evidence_class=EvidenceClass.CONFIRMED)
    unconfirmed = H.minted(evidence_class=EvidenceClass.UNCONFIRMED)
    assert H.fp(confirmed) != H.fp(unconfirmed)  # class is identity-bearing
    successor = H.minted(evidence_class=EvidenceClass.CONFIRMED, observed_min=3)
    record = H.ok(ConfirmationRecord.try_create(H.fp(unconfirmed), H.inst(4), confirmed_as=H.fp(successor)))
    edges = H.ok(record.lineage_edges())
    confirmed_as = [e for e in edges if e.kind is LifecycleEdgeKind.CONFIRMED_AS]
    assert len(confirmed_as) == 1
    assert confirmed_as[0].from_ref == H.fp(unconfirmed)
    assert confirmed_as[0].to_ref == H.fp(successor)


# ===========================================================================
# QA-E09-L3-010 (P0) — confirmed read REFUSES unconfirmed rows, never filters
# ===========================================================================


def test_l3_010_confirmed_read_refuses_rather_than_silently_filtering() -> None:
    rows = [
        H.minted(evidence_class=EvidenceClass.CONFIRMED),
        H.minted(evidence_class=EvidenceClass.UNCONFIRMED, observed_min=3),
        H.minted(evidence_class=EvidenceClass.CONFIRMED, observed_min=4),
    ]
    result = read_confirmed(rows)
    # A silent filter would return a 2-tuple; the contract requires a refusal instead.
    assert is_refusal(result)
    assert not isinstance(result, tuple)
    assert result.category.value == "policy rejection"
    assert result.context["index"] == 1
    assert result.context["evidence_class"] == "unconfirmed"


def test_l3_010_all_confirmed_read_returns_every_row() -> None:
    rows = [H.minted(evidence_class=EvidenceClass.CONFIRMED, observed_min=2 + i) for i in range(3)]
    assert H.ok(read_confirmed(rows)) == tuple(rows)


# ===========================================================================
# QA-E09-L3-011 (P0) — consumption (<= T) vs the refuse-at-equal causality test
# ===========================================================================


def test_l3_011_consumption_admits_le_t_causality_refuses_at_equal() -> None:
    assert is_ok(may_consume(H.inst(5), at=H.inst(10)))  # strictly before T
    assert is_ok(may_consume(H.inst(10), at=H.inst(10)))  # equality is consumption
    lookahead = may_consume(H.inst(11), at=H.inst(10))
    assert is_refusal(lookahead) and lookahead.category.value == "policy rejection"
    assert H.ok(causally_precedes(H.inst(5), later=H.inst(10))) is True
    equal = causally_precedes(H.inst(7), later=H.inst(7))
    assert is_refusal(equal)  # the two rules DIFFER at equal


# ===========================================================================
# QA-E09-L3-012 (P0) — split-manifest embargo boundary refusal (FM-7)
# ===========================================================================


def _admit(*, boundary: int, observed: int, confirmed: int, embargo_min: int):
    return admit_across_boundary(
        boundary=H.inst(boundary),
        observed_at=H.inst(observed),
        confirmed_at=H.inst(confirmed),
        embargo_width=Duration(value_ns=embargo_min * H.MINUTE),
    )


def test_l3_012_straddle_beyond_embargo_refused_within_embargo_admitted() -> None:
    # observed < boundary < confirmed => straddle; gap = confirmed - observed.
    beyond = _admit(boundary=5, observed=3, confirmed=9, embargo_min=2)  # gap 6 > embargo 2
    assert is_refusal(beyond) and beyond.category.value == "policy rejection"
    within = H.ok(_admit(boundary=5, observed=4, confirmed=7, embargo_min=5))  # gap 3 <= 5
    assert within.straddles is True
    non_straddle = H.ok(_admit(boundary=10, observed=2, confirmed=4, embargo_min=0))
    assert non_straddle.straddles is False


def test_l3_012_unbounded_family_excluded_from_split_governed_evidence() -> None:
    result = required_embargo_width(
        H.family(bound=None).confirmation_rule, observation_width=Duration(value_ns=H.MINUTE)
    )
    assert is_refusal(result) and result.category.value == "policy rejection"


def test_l3_012_bound_derived_embargo_governs_the_boundary() -> None:
    embargo = H.ok(required_embargo_width(H.family(bound=3).confirmation_rule, observation_width=Duration(value_ns=H.MINUTE)))
    assert embargo.value_ns == 3 * H.MINUTE
    admitted = admit_across_boundary(boundary=H.inst(5), observed_at=H.inst(4), confirmed_at=H.inst(7), embargo_width=embargo)
    refused = admit_across_boundary(boundary=H.inst(5), observed_at=H.inst(3), confirmed_at=H.inst(8), embargo_width=embargo)
    assert is_ok(admitted)
    assert is_refusal(refused)


# ===========================================================================
# QA-E09-L3-013 (P1) — revised input yields a different label
# ===========================================================================


def test_l3_013_revised_input_changes_the_label_and_label_carries_every_part() -> None:
    obj = H.minted(evidence_class=EvidenceClass.CONFIRMED)
    input_a = H.fp(H.minted())
    input_b = H.fp(H.minted(anc=H.anchor(low=107_900)))
    assert input_a != input_b
    label_a = H.ok(structure_result_label(obj, world=World.LIVE, input_fingerprints=[input_a]))
    label_b = H.ok(structure_result_label(obj, world=World.LIVE, input_fingerprints=[input_b]))
    assert label_a.computation_identity != label_b.computation_identity  # no silent change
    # the label carries every result_identity_key part
    assert isinstance(label_a, ResultLabel)
    assert isinstance(label_a.producer_contract_identity, Fingerprint)
    assert label_a.producer_contract_format_version == 1
    assert label_a.evidence_class is EvidenceClass.CONFIRMED
    assert label_a.world is World.LIVE
    assert label_a.evidence_time_range is not None


# ===========================================================================
# QA-E09-L3-014 (P1) — governed-evidence citation law
# ===========================================================================


def test_l3_014_citation_law_and_confirmed_only_promotion() -> None:
    in_memory = H.ok(evaluate_citation(CitationKind.IN_MEMORY))
    assert in_memory.governed is False and in_memory.must_persist is False
    for kind in (CitationKind.JOURNAL_EVENT, CitationKind.RESULT_LABEL):
        verdict = H.ok(evaluate_citation(kind))
        assert verdict.governed is True and verdict.must_persist is True
    assert is_ok(promote_scanned(H.minted(evidence_class=EvidenceClass.CONFIRMED)))
    for cls in (EvidenceClass.UNCONFIRMED, EvidenceClass.PROVISIONAL):
        refused = promote_scanned(H.minted(evidence_class=cls))
        assert is_refusal(refused) and refused.category.value == "policy rejection"


# ===========================================================================
# QA-E09-L3-015 (P1) — first governed family: precise, unprivileged, no school
# ===========================================================================


def test_l3_015_seed_family_precise_unprivileged_consumes_declared_inputs_no_school() -> None:
    seed = H.swing_family()
    assert is_ok(admit_to_governed_library(seed))  # precise rule -> admitted
    # an operator-authored peer is admitted through the IDENTICAL gate (no privilege)
    operator = H.family(family_id="operator-zone", geometry="zone",
                        descriptor="confirmed the moment price trades through the zone edge")
    assert is_ok(admit_to_governed_library(operator))
    # consumes source/bar observations as declared inputs
    swings = H.ok(seed.detect(_series()))
    assert swings and all(s.object.family.geometry == "point" for s in swings)
    # no trading-school name in the family's own vocabulary
    haystack = " ".join([seed.identity.family_id, seed.confirmation_rule.descriptor]).lower()
    for token in ("wyckoff", "elliott", "ict", "smart money", "order block", "fibonacci"):
        assert token not in haystack


# ===========================================================================
# QA-E09-L3-016 (P1) — routing test (FM-6) and indicator-as-declared-input
# ===========================================================================


def test_l3_016_routing_admits_exactly_one_answer() -> None:
    assert H.ok(route(value_per_evaluation_instant=True, discrete_with_birth_and_lifetime=False)) is RoutingKind.VALUE_PER_INSTANT
    assert H.ok(route(value_per_evaluation_instant=False, discrete_with_birth_and_lifetime=True)) is RoutingKind.DISCRETE_OBJECT
    both = route(value_per_evaluation_instant=True, discrete_with_birth_and_lifetime=True)
    neither = route(value_per_evaluation_instant=False, discrete_with_birth_and_lifetime=False)
    assert is_refusal(both) and both.category.value == "invalid input"
    assert is_refusal(neither) and neither.category.value == "invalid input"


class _FakeIndicatorResult:
    def __init__(self, ref: Fingerprint) -> None:
        self._ref = ref

    @property
    def result_fingerprint(self) -> Fingerprint:
        return self._ref


def test_l3_016_indicator_consumed_as_declared_input_returns_its_fingerprint() -> None:
    indicator_fp = H.fp(H.minted())  # a stand-in governed indicator result fingerprint
    fake = _FakeIndicatorResult(indicator_fp)
    assert isinstance(fake, IndicatorResultInput)  # satisfies the declared-input seam
    consumed = consume_indicator_input(fake)
    assert H.ok(consumed) == indicator_fp  # the fp is recorded, never re-implemented inline


# ===========================================================================
# QA-E09-L3-017 (P1) — benchmark light-claim / regression gate (FM-8)
# ===========================================================================


def test_l3_017_benchmark_rungs_are_the_three_structure_rungs() -> None:
    assert {r.value for r in BenchmarkRung} == {
        "active-object-set-size",
        "objects-minted-per-bar",
        "interaction-records-per-bar",
    }


def _budget() -> DeclaredBudget:
    return H.ok(
        DeclaredBudget.try_create(
            per_update_cost_ceiling_ns=1_000,
            object_set_size_ceiling=100,
            scan_window_ceiling=50,
            synchronous_available=True,
        )
    )


def test_l3_017_light_claim_lacking_baseline_and_over_bound_refused() -> None:
    budget = _budget()
    # heavy by default: a light claim without a recorded baseline is refused
    no_baseline = evaluate_light_claim(budget, per_update_cost_ns=10, object_set_size=1, scan_window=1, has_baseline=False)
    assert is_refusal(no_baseline) and no_baseline.category.value == "policy rejection"
    # a measurement over a declared bound is refused
    over_bound = evaluate_light_claim(budget, per_update_cost_ns=2_000, object_set_size=1, scan_window=1, has_baseline=True)
    assert is_refusal(over_bound) and over_bound.category.value == "policy rejection"
    # a clean claim within every bound with a baseline is light
    assert is_ok(evaluate_light_claim(budget, per_update_cost_ns=10, object_set_size=1, scan_window=1, has_baseline=True))


def test_l3_017_peak_memory_regression_fails_exactly_as_a_slowdown() -> None:
    rung = BenchmarkRung.OBJECTS_MINTED_PER_BAR
    baseline = Measurement(rung=rung, seconds=1.0, peak_bytes=1_000)
    # seconds unchanged, memory regressed sharply -> refused just as a slowdown would be
    mem_regressed = Measurement(rung=rung, seconds=1.0, peak_bytes=2_000)
    result = check_regression(baseline, mem_regressed, tolerance_bps=100)
    assert is_refusal(result) and result.category.value == "policy rejection"
    assert result.context["memory_regressed"] is True
    # no regression on either signal -> passes
    steady = Measurement(rung=rung, seconds=1.0, peak_bytes=1_000)
    assert is_ok(check_regression(baseline, steady, tolerance_bps=100))


# ===========================================================================
# QA-E09-L3-018 (P1) — graduation through the extension shape with a lineage edge
# ===========================================================================


def test_l3_018_precise_family_graduates_with_promoted_from_edge() -> None:
    graduated_ref = H.fp(H.minted())
    experiment_ref = H.fp(H.minted(observed_min=3))
    grad = H.ok(
        graduate_to_governed(
            family=H.family(), graduated_ref=graduated_ref, originating_experiment_ref=experiment_ref
        )
    )
    edge = grad.promoted_from_edge
    assert edge.edge_type == "promoted-from"
    assert edge.from_ref == graduated_ref  # graduated governed artifact ...
    assert edge.to_ref == experiment_ref  # ... -> originating experiment


def test_l3_018_imprecise_concept_never_graduates() -> None:
    blank_rule = ConfirmationRule(descriptor="   ", clock_confirmed=False, confirmation_delay_bound=None)
    imprecise = DeclaredFamily(
        identity=H.ok(FamilyIdentity.try_create("vague", 1, "zone")), confirmation_rule=blank_rule
    )
    refused = graduate_to_governed(
        family=imprecise, graduated_ref=H.fp(H.minted()), originating_experiment_ref=H.fp(H.minted(observed_min=3))
    )
    assert is_refusal(refused)  # stays in the ungoverned research lane


def test_l3_018_graduation_requires_distinct_artifact_and_experiment() -> None:
    same = H.fp(H.minted())
    refused = graduate_to_governed(family=H.family(), graduated_ref=same, originating_experiment_ref=same)
    assert is_refusal(refused) and refused.category.value == "invalid input"
