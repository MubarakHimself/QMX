"""L2 contract tests for Epic 9 — oracle = docs/contracts/ct-17-causal-structure.yaml.

These pin the load-bearing CT-17 invariants that are contract facts (not epic-specific
AC behaviour): the open geometry set, the sloped/anchored + calendar clauses, the
composite max-rule, the typed-refusal category enumeration, the conformance register's
expressibility, and the "returns fingerprintable content, never stamps a record" rule.

Covers QA-E09-L2-001..006. Every effect is observed through the public surface
(fp1_identity / content_fingerprint / a returned refusal), never a private helper.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

import qmf.structure as structure
from qmf.core import (
    CalendarIdentity,
    Duration,
    EvidenceClass,
    Fingerprint,
    RoundingMode,
    World,
    is_ok,
    is_refusal,
)
from qmf.structure import (
    KNOWN_GEOMETRIES,
    AnchorPoint,
    CalendarAnchoredLevel,
    CompositeObject,
    ConfirmationRule,
    EvaluationRuleRef,
    FamilyIdentity,
    InteractionRecord,
    InvalidationRecord,
    LifecycleEdge,
    LifecycleEdgeKind,
    SamplingPolicy,
    ScheduleGapPolicy,
    SlopedObject,
    StructureObject,
    admit_across_boundary,
    causally_precedes,
    check_emission_invariant,
    may_consume,
    read_confirmed,
    refit,
    required_embargo_width,
    structure_result_label,
)

import _helpers as H

_WORKTREE = Path(structure.__file__).resolve().parents[5]  # .../packages/qmf-structure/src/qmf/structure


# --- QA-E09-L2-001: a family is a (type of chart object); geometry is OPEN -----


def test_l2_001_known_geometry_seed_set_is_the_ct17_six() -> None:
    assert set(KNOWN_GEOMETRIES) == {"point", "level", "zone", "span", "distribution", "graph"}


def test_l2_001_geometry_is_open_not_a_closed_enum() -> None:
    # CT-17: "geometry is family-declared and open" — a token outside the seed set is a new
    # declaration, ACCEPTED, not refused. (A blank geometry is the only refusal.)
    outside = FamilyIdentity.try_create("operator-family", 1, "channel")
    assert is_ok(outside)
    assert outside.value.geometry == "channel"


def test_l2_001_blank_geometry_is_refused() -> None:
    result = FamilyIdentity.try_create("f", 1, "   ")
    assert is_refusal(result)
    assert result.context["field"] == "geometry"


# --- QA-E09-L2-002: sloped anchors (slope derived, never stored) + calendar ----


def _sloped(*, rule_version: int = 1, observed_min: int = 5) -> SlopedObject:
    fam = H.family(geometry="span")
    return H.ok(
        SlopedObject.try_create(
            family=fam.identity,
            confirmation_rule=fam.confirmation_rule,
            anchor_points=[
                H.ok(AnchorPoint.try_create(H.inst(0), H.price(108_000))),
                H.ok(AnchorPoint.try_create(H.inst(1), H.price(108_400))),
            ],
            evaluation_rule=H.ok(EvaluationRuleRef.try_create("linear-two-point", rule_version)),
            target_scale=5,
            rounding=RoundingMode.HALF_EVEN,
            observed_at=H.inst(observed_min),
            evidence_class=EvidenceClass.UNCONFIRMED,
        )
    )


def test_l2_002_sloped_object_identity_has_anchors_and_rule_but_no_stored_slope() -> None:
    content = _sloped().fp1_identity()
    assert "anchor_points" in content
    assert content["evaluation_rule"] == {"rule_id": "linear-two-point", "version": 1}
    # Slope is derived at evaluation, never an identity field.
    assert "slope" not in content
    assert H.ok(_sloped().content_fingerprint()).value.startswith("fp1:sha256:")


def test_l2_002_versioned_evaluation_rule_is_identity_bearing() -> None:
    assert H.ok(_sloped(rule_version=1).content_fingerprint()) != H.ok(
        _sloped(rule_version=2).content_fingerprint()
    )


def _calendar_level(*, sampling: SamplingPolicy, gap: ScheduleGapPolicy) -> CalendarAnchoredLevel:
    fam = H.family(geometry="level")
    return H.ok(
        CalendarAnchoredLevel.try_create(
            family=fam.identity,
            confirmation_rule=fam.confirmation_rule,
            calendar=H.ok(CalendarIdentity.try_create("forex-17NY", "v3", "2024a")),
            sampling_policy=sampling,
            schedule_gap_policy=gap,
            level=H.price(108_250),
            observed_at=H.inst(0),  # a standing (a-priori) level: observed-at = config instant
            evidence_class=EvidenceClass.CONFIRMED,
        )
    )


def test_l2_002_calendar_level_declares_fingerprinted_policies() -> None:
    level = _calendar_level(
        sampling=SamplingPolicy.LAST_KNOWN_AT_OR_BEFORE, gap=ScheduleGapPolicy.CARRY_PREVIOUS_SESSION
    )
    content = level.fp1_identity()
    assert content["sampling_policy"] == "last-known-at-or-before"
    assert content["schedule_gap_policy"] == "carry-previous-session"


def test_l2_002_policy_is_identity_bearing() -> None:
    # Two levels differing only in sampling policy are distinct artifacts (fingerprinted).
    a = _calendar_level(sampling=SamplingPolicy.LAST_KNOWN_AT_OR_BEFORE, gap=ScheduleGapPolicy.REFUSE)
    b = _calendar_level(sampling=SamplingPolicy.REFUSE, gap=ScheduleGapPolicy.REFUSE)
    assert H.ok(a.content_fingerprint()) != H.ok(b.content_fingerprint())


def test_l2_002_policy_enums_are_the_ct17_closed_sets() -> None:
    assert {p.value for p in SamplingPolicy} == {"last-known-at-or-before", "refuse"}
    assert {p.value for p in ScheduleGapPolicy} == {
        "refuse",
        "nearest-open-instant",
        "carry-previous-session",
    }


# --- QA-E09-L2-003: composite max-rule, order-significance, lineage ------------


def _composite(*, children, ordered: bool = True, evidence_class=EvidenceClass.UNCONFIRMED):
    fam = H.family(geometry="graph")
    return CompositeObject.try_create(
        family=fam.identity,
        confirmation_rule=fam.confirmation_rule,
        children=children,
        evidence_class=evidence_class,
        ordered=ordered,
    )


def test_l2_003_instants_are_the_maxima_over_children() -> None:
    c1 = H.child(H.fp(H.minted()), observed_min=2, confirmed_min=5, bound=3)
    c2 = H.child(H.fp(H.minted(observed_min=3)), observed_min=4, confirmed_min=9, bound=2)
    comp = H.ok(_composite(children=[c1, c2]))
    # observed-at is the max of children's observed-at; confirmed-at the max of theirs.
    assert comp.observed_at.value_ns == H.inst(4).value_ns
    assert comp.confirmed_at is not None
    assert comp.confirmed_at.value_ns == H.inst(9).value_ns
    # never earlier than any child
    assert comp.confirmed_at.value_ns >= max(c.confirmed_at.value_ns for c in (c1, c2))
    # the confirmation-delay bound is the SUM of the children's bounds
    assert comp.confirmation_delay_bound == 5


def test_l2_003_unconfirmed_until_every_child_is_confirmed() -> None:
    confirmed = H.child(H.fp(H.minted()), observed_min=2, confirmed_min=5, bound=1)
    pending = H.child(H.fp(H.minted(observed_min=3)), observed_min=4, confirmed_min=None, bound=1)
    comp = H.ok(_composite(children=[confirmed, pending]))
    assert comp.confirmed_at is None  # not confirmed while any child is unconfirmed


def test_l2_003_unbounded_child_makes_composite_unbounded() -> None:
    a = H.child(H.fp(H.minted()), observed_min=2, confirmed_min=5, bound=3)
    unbounded = H.child(H.fp(H.minted(observed_min=3)), observed_min=4, confirmed_min=9, bound=None)
    comp = H.ok(_composite(children=[a, unbounded]))
    assert comp.confirmation_delay_bound is None


def test_l2_003_children_order_significant_by_default_unordered_when_declared() -> None:
    c1 = H.child(H.fp(H.minted()), observed_min=2, confirmed_min=5)
    c2 = H.child(H.fp(H.minted(observed_min=3)), observed_min=4, confirmed_min=9)
    ordered_ab = H.ok(_composite(children=[c1, c2], ordered=True))
    ordered_ba = H.ok(_composite(children=[c2, c1], ordered=True))
    # ordered: child order is identity-bearing -> reordering changes the fingerprint.
    assert H.ok(ordered_ab.content_fingerprint()) != H.ok(ordered_ba.content_fingerprint())
    unordered_ab = H.ok(_composite(children=[c1, c2], ordered=False))
    unordered_ba = H.ok(_composite(children=[c2, c1], ordered=False))
    # unordered (explicitly declared): the same set is one artifact however assembled.
    assert H.ok(unordered_ab.content_fingerprint()) == H.ok(unordered_ba.content_fingerprint())


def test_l2_003_composite_lineage_is_its_children_fingerprints() -> None:
    r1, r2 = H.fp(H.minted()), H.fp(H.minted(observed_min=3))
    comp = H.ok(_composite(children=[H.child(r1, observed_min=2), H.child(r2, observed_min=3)]))
    assert comp.input_fingerprints() == (r1, r2)


# --- QA-E09-L2-004: every CT-17 failure path returns a registry refusal code ---


def _registry_refusal_codes() -> set[str]:
    """Read the typed_refusal_codes list straight from the registry oracle."""
    text = (_WORKTREE / "docs" / "registry" / "variables.yaml").read_text(encoding="utf-8")
    block = text.split("name: typed_refusal_codes", 1)[1]
    listing = re.search(r"value:\s*\[([^\]]+)\]", block).group(1)
    return {token.strip() for token in listing.split(",")}


def _normalize(category_value: str) -> str:
    return category_value.replace(" ", "-")


def test_l2_004_all_ct17_refusals_are_registered_categories() -> None:
    codes = _registry_refusal_codes()
    assert {"invalid-input", "policy-rejection"} <= codes  # the categories CT-17 uses
    provoked = [
        # invalid-input: emission-invariant violation
        check_emission_invariant(anchor=H.anchor(0, 5), observed_at=H.inst(2)),
        # policy-rejection: confirmed read over an unconfirmed row
        read_confirmed([H.minted(evidence_class=EvidenceClass.UNCONFIRMED)]),
        # policy-rejection: look-ahead consumption
        may_consume(H.inst(11), at=H.inst(10)),
        # policy-rejection: causality refuse-at-equal
        causally_precedes(H.inst(7), later=H.inst(7)),
        # policy-rejection: simulated world into governed evidence
        structure_result_label(H.minted(), world=World.SIMULATED),
        # policy-rejection: unbounded family excluded from split-governed evidence
        required_embargo_width(
            H.family(bound=None).confirmation_rule, observation_width=Duration(value_ns=H.MINUTE)
        ),
        # policy-rejection: a straddle beyond the declared embargo
        admit_across_boundary(
            boundary=H.inst(5),
            observed_at=H.inst(3),
            confirmed_at=H.inst(9),
            embargo_width=Duration(value_ns=H.MINUTE),
        ),
    ]
    for refusal in provoked:
        assert is_refusal(refusal), f"expected a refusal, got {refusal}"
        assert _normalize(refusal.category.value) in codes  # a registered category, never novel
        assert isinstance(refusal.context, Mapping) and refusal.context  # machine-readable context
        assert refusal.retryability is not None  # retryability is carried


# --- QA-E09-L2-005: the concept-walk register stays expressible ---------------


def _build_retro_anchored_zone() -> Fingerprint:
    fam = H.family(geometry="zone")
    obj = H.minted(fam=fam, anc=H.anchor(start_min=0, end_min=1, low=108_000, high=108_600),
                   observed_min=5)  # zone anchored in the past (retro-anchored)
    # consumption state is expressible as an interaction record on the object
    H.ok(InteractionRecord.try_create(H.fp(obj), H.inst(6), H.price(108_100), "consumed", H.rational(1, 2)))
    return H.fp(obj)


def _build_born_from_invalidation() -> Fingerprint:
    parent = H.minted(observed_min=1)
    H.ok(InvalidationRecord.try_create(H.fp(parent), H.inst(4)))  # parent invalidation
    child = H.minted(fam=H.family(geometry="point"), observed_min=4)  # born at the invalidation
    return H.fp(child)


def _two_point_children(n: int = 2):
    return [H.child(H.fp(H.minted(observed_min=2 + i)), observed_min=2 + i, confirmed_min=6 + i)
            for i in range(n)]


def _build_tolerance_cluster() -> Fingerprint:
    fam = H.family(geometry="zone")
    comp = H.ok(CompositeObject.try_create(
        family=fam.identity, confirmation_rule=fam.confirmation_rule,
        children=_two_point_children(), evidence_class=EvidenceClass.UNCONFIRMED, ordered=False,
    ))
    return H.ok(comp.content_fingerprint())


def _build_threshold_breach_reversal() -> Fingerprint:
    obj = H.minted(fam=H.family(geometry="level"))
    H.ok(InteractionRecord.try_create(H.fp(obj), H.inst(6), H.price(108_600), "breach", H.rational(1, 1)))
    return H.fp(obj)


def _build_calendar_composite() -> Fingerprint:
    fam = H.family(geometry="graph")
    comp = H.ok(CompositeObject.try_create(
        family=fam.identity, confirmation_rule=fam.confirmation_rule,
        children=_two_point_children(3), evidence_class=EvidenceClass.UNCONFIRMED, ordered=True,
    ))
    return H.ok(comp.content_fingerprint())


def _build_multi_barspec_nest() -> Fingerprint:
    fam = H.family(geometry="graph")
    kids = [H.child(H.fp(H.minted()), observed_min=2, confirmed_min=6, bound=3),
            H.child(H.fp(H.minted(observed_min=3)), observed_min=3, confirmed_min=7, bound=15)]
    comp = H.ok(CompositeObject.try_create(
        family=fam.identity, confirmation_rule=fam.confirmation_rule,
        children=kids, evidence_class=EvidenceClass.UNCONFIRMED,
    ))
    return H.ok(comp.content_fingerprint())


def _build_cross_instrument_divergence() -> Fingerprint:
    eur = H.minted(anc=H.anchor(instrument=H.EURUSD))
    gbp = H.minted(anc=H.anchor(low=127_000, high=127_500, instrument=H.GBPUSD), observed_min=3)
    fam = H.family(geometry="graph")
    comp = H.ok(CompositeObject.try_create(
        family=fam.identity, confirmation_rule=fam.confirmation_rule,
        children=[H.child(H.fp(eur), observed_min=2, confirmed_min=6),
                  H.child(H.fp(gbp), observed_min=3, confirmed_min=7)],
        evidence_class=EvidenceClass.UNCONFIRMED,
    ))
    return H.ok(comp.content_fingerprint())


def _build_distribution_over_price() -> Fingerprint:
    return H.fp(H.minted(fam=H.family(geometry="distribution")))


def _build_a_priori_price_grid() -> Fingerprint:
    fam = H.family(geometry="level")
    # standing (a-priori) level objects: a point anchored at the configuration instant
    # (anchor.start == anchor.end == observed_at), grouped as a grid composite.
    grid = [
        H.child(
            H.fp(
                H.minted(
                    fam=fam,
                    anc=H.anchor(start_min=0, end_min=0, low=108_000 + i * 100, high=108_000 + i * 100),
                    observed_min=0,
                )
            ),
            observed_min=0,
            confirmed_min=0,
        )
        for i in range(3)
    ]
    comp = H.ok(CompositeObject.try_create(
        family=fam.identity, confirmation_rule=fam.confirmation_rule,
        children=grid, evidence_class=EvidenceClass.CONFIRMED, ordered=False,
    ))
    return H.ok(comp.content_fingerprint())


def _build_projected_level() -> Fingerprint:
    return H.ok(_sloped(observed_min=5).content_fingerprint())  # anchors precede observed-at


def _build_pattern_refit() -> Fingerprint:
    prior = H.minted(observed_min=2)
    result = H.ok(refit(prior, anchor=H.anchor(low=108_100), observed_at=H.inst(8)))
    return H.fp(result.superseding)


_CONCEPT_BUILDERS = {
    "RETRO_ANCHORED_ZONES": _build_retro_anchored_zone,
    "BORN_FROM_INVALIDATION": _build_born_from_invalidation,
    "TOLERANCE_CLUSTERS": _build_tolerance_cluster,
    "THRESHOLD_BREACH_REVERSAL": _build_threshold_breach_reversal,
    "CALENDAR_COMPOSITES": _build_calendar_composite,
    "MULTI_BARSPEC_NESTS": _build_multi_barspec_nest,
    "CROSS_INSTRUMENT_DIVERGENCE": _build_cross_instrument_divergence,
    "DISTRIBUTION_OVER_PRICE": _build_distribution_over_price,
    "A_PRIORI_PRICE_GRIDS": _build_a_priori_price_grid,
    "PROJECTED_LEVELS": _build_projected_level,
    "PATTERN_REFITS": _build_pattern_refit,
}


def test_l2_005_builder_set_matches_the_register_no_drift() -> None:
    register_keys = {item.name for item in structure.CONCEPT_WALK_REGISTER}
    assert set(_CONCEPT_BUILDERS) == register_keys, "concept-walk builders drifted from the register"


def test_l2_005_every_concept_walk_item_is_constructible() -> None:
    for name, builder in _CONCEPT_BUILDERS.items():
        artifact = builder()
        assert isinstance(artifact, Fingerprint), f"{name} did not build a fingerprintable artifact"
        assert artifact.value.startswith("fp1:sha256:")


# --- QA-E09-L2-006: the library returns fingerprintable content, never stamps --

_STAMP_ATTRS = ("writer", "writer_id", "sequence", "seq", "created_at", "created", "stamped_at")
_STAMP_KEYS = ("writer", "writer_id", "sequence", "seq", "created_at")


def test_l2_006_emissions_carry_no_writer_or_sequence() -> None:
    obj = H.minted()
    conf = H.ok(structure_result_label(obj, world=World.LIVE))  # a label is fingerprintable too
    inter = H.ok(InteractionRecord.try_create(H.fp(obj), H.inst(4), H.price(108_100), "touch", H.rational(1, 10)))
    edge = LifecycleEdge(kind=LifecycleEdgeKind.INTERACTION, from_ref=H.fp(obj), to_ref=H.fp(obj))
    for artifact in (obj, inter, edge):
        for attr in _STAMP_ATTRS:
            assert not hasattr(artifact, attr), f"{type(artifact).__name__} stamps {attr!r}"
    # No stamping key enters the object's / edge's fp1 identity content.
    for content in (obj.fp1_identity(), inter.fp1_identity(), edge.fp1_identity()):
        for key in _STAMP_KEYS:
            assert key not in content
    # ResultLabel does carry a producer identity but is built from the object, not stamped here.
    assert conf.producer_contract_identity is not None


def test_l2_006_content_fingerprint_is_deterministic() -> None:
    a, b = H.minted(), H.minted()
    assert H.fp(a) == H.fp(b)  # identical content -> one fp1 (dedup by construction, no writer)
