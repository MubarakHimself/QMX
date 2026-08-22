"""Tier-1 tests for CT-17 Story 9.2: the append-only lifecycle and the read-time fold.

Covers the acceptance criteria:

* confirmation, invalidation, and interaction records are separate append-only typed
  records referencing the object's fingerprint, each instant an identity field of its own
  record; interaction records are the only permitted way an object's state evolves;
* "still valid at T" is a **read-time fold** over the object's record stream per CT-17's
  read-resolution rule, never a stored field;
* a correction/refit/state change that would overwrite an object or edge is prohibited:
  interaction records append, and a refit mints a new artifact with a ``supersedes`` edge,
  anchors frozen at each fit, the lineage head keeping the first observed-at, earlier
  evidence remaining (FM-3);
* a family whose confirmation rule cannot state "confirmed the moment X happens" is not
  admitted to the governed library; the concept stays free in the ungoverned research
  lane; clock-confirmed (degenerate) confirmation is legal (FM-2); and
* invalidation never cascades automatically; the reader may compute cascade at read time
  from lineage.
"""

from __future__ import annotations

import dataclasses
from typing import TypeVar

import pytest
from qmf.core import (
    EvidenceClass,
    ExactRational,
    Fingerprint,
    Instant,
    Instrument,
    Ok,
    Price,
    Result,
    TypedRefusal,
    UnitKind,
    VenueId,
    fingerprint,
    is_ok,
)
from qmf.structure import (
    CONTRACT_FORMAT_VERSION,
    AnchorSpan,
    CascadeResolution,
    ConfirmationRecord,
    ConfirmationRule,
    DeclaredFamily,
    FamilyIdentity,
    InteractionRecord,
    InvalidationPredicate,
    InvalidationRecord,
    LifecycleEdge,
    LifecycleEdgeKind,
    Refit,
    ResolvedState,
    StructureObject,
    admit_to_governed_library,
    refit,
    resolve_cascade,
    resolve_state,
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
    clock_confirmed: bool = False,
    bound: int | None = 3,
) -> DeclaredFamily:
    identity = _ok(FamilyIdentity.try_create(family_id, version, geometry))
    rule = _ok(
        ConfirmationRule.try_create(
            descriptor, clock_confirmed=clock_confirmed, confirmation_delay_bound=bound
        )
    )
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
) -> StructureObject:
    return _ok(
        StructureObject.try_create(
            _family(),
            {"pivot_tolerance": _rational(1, 4)} if parameters is None else parameters,
            _anchor() if anchor is None else anchor,
            Instant(value_ns=observed_at),
            evidence_class,
        )
    )


def _fp(obj: StructureObject) -> Fingerprint:
    return _ok(obj.content_fingerprint())


# --- lifecycle edge kinds ---------------------------------------------------


def test_lifecycle_edge_kinds_are_the_ct07_subset() -> None:
    assert {kind.value for kind in LifecycleEdgeKind} == {
        "confirmation",
        "invalidation",
        "interaction",
        "confirmed-as",
        "supersedes",
    }


def test_lifecycle_edge_fingerprintable_content() -> None:
    edge = LifecycleEdge(
        kind=LifecycleEdgeKind.CONFIRMATION,
        from_ref=_fp(_mint()),
        to_ref=_fp(_mint()),
    )
    content = edge.fp1_identity()
    assert content["class"] == "structure-lifecycle-edge"
    assert content["kind"] == "confirmation"
    assert content["format_version"] == CONTRACT_FORMAT_VERSION
    assert _ok(edge.content_fingerprint()).value.startswith("fp1:sha256:")


# --- ConfirmationRecord -----------------------------------------------------


def test_confirmation_record_carries_object_ref_and_instant() -> None:
    obj = _mint()
    record = _ok(ConfirmationRecord.try_create(_fp(obj), Instant(value_ns=_T0 + 3 * _MINUTE)))
    assert record.object_ref == _fp(obj)
    assert record.at.value_ns == _T0 + 3 * _MINUTE
    assert record.confirmed_as is None
    content = record.fp1_identity()
    assert content["class"] == "confirmation-record"
    assert content["object_ref"] == _fp(obj).value
    assert content["at"] == _T0 + 3 * _MINUTE
    assert "confirmed_as" not in content


def test_confirmation_record_accepts_fp_string_ref() -> None:
    obj = _mint()
    record = _ok(ConfirmationRecord.try_create(_fp(obj).value, Instant(value_ns=_T0 + 3 * _MINUTE)))
    assert record.object_ref == _fp(obj)


def test_confirmation_instant_is_identity_bearing() -> None:
    obj = _mint()
    a = _ok(ConfirmationRecord.try_create(_fp(obj), Instant(value_ns=_T0 + 3 * _MINUTE)))
    b = _ok(ConfirmationRecord.try_create(_fp(obj), Instant(value_ns=_T0 + 4 * _MINUTE)))
    # Each instant is an identity field of its own record — two instants, two facts.
    assert _ok(a.content_fingerprint()) != _ok(b.content_fingerprint())


def test_confirmation_record_confirmed_as_successor_and_edges() -> None:
    unconfirmed = _mint(evidence_class=EvidenceClass.UNCONFIRMED)
    successor = _mint(evidence_class=EvidenceClass.CONFIRMED)
    record = _ok(
        ConfirmationRecord.try_create(
            _fp(unconfirmed),
            Instant(value_ns=_T0 + 3 * _MINUTE),
            confirmed_as=_fp(successor),
        )
    )
    assert record.confirmed_as == _fp(successor)
    assert record.fp1_identity()["confirmed_as"] == _fp(successor).value
    edges = _ok(record.lineage_edges())
    kinds = {edge.kind for edge in edges}
    assert kinds == {LifecycleEdgeKind.CONFIRMATION, LifecycleEdgeKind.CONFIRMED_AS}
    confirmed_as_edge = next(e for e in edges if e.kind is LifecycleEdgeKind.CONFIRMED_AS)
    assert confirmed_as_edge.from_ref == _fp(unconfirmed)
    assert confirmed_as_edge.to_ref == _fp(successor)


def test_confirmation_record_plain_edge_is_record_to_object() -> None:
    obj = _mint()
    record = _ok(ConfirmationRecord.try_create(_fp(obj), Instant(value_ns=_T0 + 3 * _MINUTE)))
    edges = _ok(record.lineage_edges())
    assert len(edges) == 1
    assert edges[0].kind is LifecycleEdgeKind.CONFIRMATION
    assert edges[0].from_ref == _ok(record.content_fingerprint())
    assert edges[0].to_ref == _fp(obj)


def test_confirmation_record_with_and_without_successor_fingerprint_differently() -> None:
    obj = _mint()
    successor = _mint(evidence_class=EvidenceClass.CONFIRMED)
    plain = _ok(ConfirmationRecord.try_create(_fp(obj), Instant(value_ns=_T0 + 3 * _MINUTE)))
    withsucc = _ok(
        ConfirmationRecord.try_create(
            _fp(obj), Instant(value_ns=_T0 + 3 * _MINUTE), confirmed_as=_fp(successor)
        )
    )
    assert _ok(plain.content_fingerprint()) != _ok(withsucc.content_fingerprint())


def test_confirmation_record_refuses_bad_parts() -> None:
    obj = _mint()
    bad_ref = ConfirmationRecord.try_create("not-a-fp", Instant(value_ns=_T0 + 3 * _MINUTE))
    assert isinstance(bad_ref, TypedRefusal)
    assert bad_ref.context["field"] == "object_ref"
    bad_at = ConfirmationRecord.try_create(_fp(obj), object())
    assert isinstance(bad_at, TypedRefusal)
    assert bad_at.context["field"] == "at"
    bad_succ = ConfirmationRecord.try_create(
        _fp(obj), Instant(value_ns=_T0 + 3 * _MINUTE), confirmed_as="not-a-fp"
    )
    assert isinstance(bad_succ, TypedRefusal)
    assert bad_succ.context["field"] == "confirmed_as"


def test_confirmation_record_refuses_self_referential_confirmed_as() -> None:
    obj = _mint()
    result = ConfirmationRecord.try_create(
        _fp(obj), Instant(value_ns=_T0 + 3 * _MINUTE), confirmed_as=_fp(obj)
    )
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "confirmed_as"


# --- InvalidationRecord -----------------------------------------------------


def test_invalidation_record_carries_detection_instant() -> None:
    obj = _mint()
    record = _ok(InvalidationRecord.try_create(_fp(obj), Instant(value_ns=_T0 + 5 * _MINUTE)))
    assert record.object_ref == _fp(obj)
    assert record.at.value_ns == _T0 + 5 * _MINUTE
    content = record.fp1_identity()
    assert content["class"] == "invalidation-record"
    assert content["at"] == _T0 + 5 * _MINUTE
    edge = _ok(record.lineage_edge())
    assert edge.kind is LifecycleEdgeKind.INVALIDATION
    assert edge.to_ref == _fp(obj)


def test_invalidation_record_refuses_bad_parts() -> None:
    obj = _mint()
    bad_ref = InvalidationRecord.try_create(123, Instant(value_ns=_T0 + 5 * _MINUTE))
    assert isinstance(bad_ref, TypedRefusal)
    assert bad_ref.context["field"] == "object_ref"
    bad_at = InvalidationRecord.try_create(_fp(obj), 12345)
    assert isinstance(bad_at, TypedRefusal)
    assert bad_at.context["field"] == "at"


# --- InteractionRecord ------------------------------------------------------


def test_interaction_record_carries_price_and_measure() -> None:
    obj = _mint()
    record = _ok(
        InteractionRecord.try_create(
            _fp(obj),
            Instant(value_ns=_T0 + 4 * _MINUTE),
            _price(108_250),
            "penetration_depth",
            _rational(3, 10),
        )
    )
    assert record.measure == "penetration_depth"
    assert record.magnitude == _rational(3, 10)
    content = record.fp1_identity()
    assert content["class"] == "interaction-record"
    assert content["measure"] == "penetration_depth"
    edge = _ok(record.lineage_edge())
    assert edge.kind is LifecycleEdgeKind.INTERACTION
    assert edge.to_ref == _fp(obj)


def test_interaction_record_refuses_binary_float_price() -> None:
    obj = _mint()
    result = InteractionRecord.try_create(
        _fp(obj), Instant(value_ns=_T0 + 4 * _MINUTE), 1.0825, "depth", _rational(1, 2)
    )
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "price"


def test_interaction_record_refuses_binary_float_magnitude() -> None:
    obj = _mint()
    result = InteractionRecord.try_create(
        _fp(obj), Instant(value_ns=_T0 + 4 * _MINUTE), _price(108_250), "depth", 0.3
    )
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "magnitude"


@pytest.mark.parametrize("measure", ["", "   "])
def test_interaction_record_refuses_blank_measure(measure: str) -> None:
    obj = _mint()
    result = InteractionRecord.try_create(
        _fp(obj), Instant(value_ns=_T0 + 4 * _MINUTE), _price(108_250), measure, _rational(1, 2)
    )
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "measure"


def test_interaction_record_refuses_bad_ref_and_instant() -> None:
    obj = _mint()
    bad_ref = InteractionRecord.try_create(
        object(), Instant(value_ns=_T0 + 4 * _MINUTE), _price(1), "m", _rational(1, 2)
    )
    assert isinstance(bad_ref, TypedRefusal)
    assert bad_ref.context["field"] == "object_ref"
    bad_at = InteractionRecord.try_create(_fp(obj), object(), _price(1), "m", _rational(1, 2))
    assert isinstance(bad_at, TypedRefusal)
    assert bad_at.context["field"] == "at"


# --- records are immutable, unstamped fingerprintable content ----------------


def test_records_carry_no_writer_or_sequence() -> None:
    obj = _mint()
    record = _ok(ConfirmationRecord.try_create(_fp(obj), Instant(value_ns=_T0 + 3 * _MINUTE)))
    assert not hasattr(record, "writer")
    assert not hasattr(record, "sequence")
    assert not hasattr(record, "created_at")


def test_records_are_frozen_no_in_place_edit() -> None:
    obj = _mint()
    record = _ok(InvalidationRecord.try_create(_fp(obj), Instant(value_ns=_T0 + 5 * _MINUTE)))
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.at = Instant(value_ns=_T0)  # type: ignore[misc]


# --- resolve_state: the read-time fold --------------------------------------


def test_resolve_state_empty_stream_is_valid_when_observed() -> None:
    obj = _mint()
    state = _ok(resolve_state(obj, [], at=Instant(value_ns=_T0 + 10 * _MINUTE)))
    assert isinstance(state, ResolvedState)
    assert state.exists is True
    assert state.confirmed is False
    assert state.invalidated is False
    assert state.still_valid is True
    assert state.interactions == ()


def test_resolve_state_before_observation_does_not_exist() -> None:
    obj = _mint(observed_at=_T0 + 5 * _MINUTE)
    state = _ok(resolve_state(obj, [], at=Instant(value_ns=_T0 + 2 * _MINUTE)))
    assert state.exists is False
    assert state.still_valid is False


def test_resolve_state_confirmation_is_lookahead_safe() -> None:
    obj = _mint()
    conf = _ok(ConfirmationRecord.try_create(_fp(obj), Instant(value_ns=_T0 + 5 * _MINUTE)))
    # Read before the confirmation instant: not yet confirmed.
    early = _ok(resolve_state(obj, [conf], at=Instant(value_ns=_T0 + 4 * _MINUTE)))
    assert early.confirmed is False
    assert early.confirmed_at is None
    # Read at or after the confirmation instant: confirmed (equality is consumption).
    at_equal = _ok(resolve_state(obj, [conf], at=Instant(value_ns=_T0 + 5 * _MINUTE)))
    assert at_equal.confirmed is True
    assert at_equal.confirmed_at is not None
    assert at_equal.confirmed_at.value_ns == _T0 + 5 * _MINUTE


def test_resolve_state_invalidation_ends_validity() -> None:
    obj = _mint()
    inval = _ok(InvalidationRecord.try_create(_fp(obj), Instant(value_ns=_T0 + 6 * _MINUTE)))
    before = _ok(resolve_state(obj, [inval], at=Instant(value_ns=_T0 + 5 * _MINUTE)))
    assert before.still_valid is True
    assert before.invalidated is False
    after = _ok(resolve_state(obj, [inval], at=Instant(value_ns=_T0 + 7 * _MINUTE)))
    assert after.still_valid is False
    assert after.invalidated is True
    assert after.invalidated_at is not None
    assert after.invalidated_at.value_ns == _T0 + 6 * _MINUTE


def test_resolve_state_interactions_folded_in_order_up_to_t() -> None:
    obj = _mint()
    i1 = _ok(
        InteractionRecord.try_create(
            _fp(obj),
            Instant(value_ns=_T0 + 5 * _MINUTE),
            _price(108_100),
            "touch",
            _rational(1, 10),
        )
    )
    i2 = _ok(
        InteractionRecord.try_create(
            _fp(obj),
            Instant(value_ns=_T0 + 3 * _MINUTE),
            _price(108_200),
            "touch",
            _rational(2, 10),
        )
    )
    i3_future = _ok(
        InteractionRecord.try_create(
            _fp(obj),
            Instant(value_ns=_T0 + 9 * _MINUTE),
            _price(108_300),
            "touch",
            _rational(3, 10),
        )
    )
    state = _ok(resolve_state(obj, [i1, i2, i3_future], at=Instant(value_ns=_T0 + 6 * _MINUTE)))
    # i3 is in the future of T and excluded; i1/i2 are ordered by instant.
    assert [r.at.value_ns for r in state.interactions] == [_T0 + 3 * _MINUTE, _T0 + 5 * _MINUTE]


def test_resolve_state_earliest_confirmation_and_invalidation() -> None:
    obj = _mint()
    c1 = _ok(ConfirmationRecord.try_create(_fp(obj), Instant(value_ns=_T0 + 5 * _MINUTE)))
    c2 = _ok(ConfirmationRecord.try_create(_fp(obj), Instant(value_ns=_T0 + 4 * _MINUTE)))
    state = _ok(resolve_state(obj, [c1, c2], at=Instant(value_ns=_T0 + 10 * _MINUTE)))
    assert state.confirmed_at is not None
    assert state.confirmed_at.value_ns == _T0 + 4 * _MINUTE  # the earliest confirmation


def test_still_valid_is_not_a_stored_field_on_the_object() -> None:
    obj = _mint()
    # The object carries no resolved-state fields — "still valid" is a read-time fold only.
    assert not hasattr(obj, "still_valid")
    assert not hasattr(obj, "confirmed")
    assert not hasattr(obj, "invalidated")
    # It is available only by folding the record stream at a knowledge time.
    state = _ok(resolve_state(obj, [], at=Instant(value_ns=_T0 + 10 * _MINUTE)))
    assert state.still_valid is True


def test_resolve_state_refuses_foreign_record() -> None:
    obj = _mint()
    other = _mint(observed_at=_T0 + 2 * _MINUTE, evidence_class=EvidenceClass.CONFIRMED)
    foreign = _ok(InvalidationRecord.try_create(_fp(other), Instant(value_ns=_T0 + 6 * _MINUTE)))
    result = resolve_state(obj, [foreign], at=Instant(value_ns=_T0 + 10 * _MINUTE))
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "records"


def test_resolve_state_refuses_record_before_observation() -> None:
    obj = _mint(observed_at=_T0 + 5 * _MINUTE)
    # A lifecycle fact before the object was observed is causally impossible (FM-1).
    early = _ok(ConfirmationRecord.try_create(_fp(obj), Instant(value_ns=_T0 + 2 * _MINUTE)))
    result = resolve_state(obj, [early], at=Instant(value_ns=_T0 + 10 * _MINUTE))
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "invalid input"
    assert result.context["field"] == "records"


def test_resolve_state_refuses_bad_inputs() -> None:
    obj = _mint()
    bad_obj = resolve_state(object(), [], at=Instant(value_ns=_T0))
    assert isinstance(bad_obj, TypedRefusal)
    assert bad_obj.context["field"] == "obj"
    bad_at = resolve_state(obj, [], at=object())
    assert isinstance(bad_at, TypedRefusal)
    assert bad_at.context["field"] == "at"
    bad_seq = resolve_state(obj, "not-a-sequence", at=Instant(value_ns=_T0 + 10 * _MINUTE))
    assert isinstance(bad_seq, TypedRefusal)
    assert bad_seq.context["field"] == "records"
    bad_elem = resolve_state(obj, [object()], at=Instant(value_ns=_T0 + 10 * _MINUTE))
    assert isinstance(bad_elem, TypedRefusal)
    assert bad_elem.context["field"] == "records"


# --- refit: a new artifact with a supersedes edge (FM-3) --------------------


def test_refit_mints_new_artifact_with_supersedes_edge() -> None:
    prior = _mint(observed_at=_T0 + 2 * _MINUTE)
    result = _ok(
        refit(
            prior,
            anchor=_anchor(low=108_100, high=108_600),  # a new fit
            observed_at=Instant(value_ns=_T0 + 8 * _MINUTE),
        )
    )
    assert isinstance(result, Refit)
    # A new, distinct artifact.
    assert _fp(result.superseding) != _fp(prior)
    # A supersedes edge from the new artifact to the prior one.
    assert result.supersedes_edge.kind is LifecycleEdgeKind.SUPERSEDES
    assert result.supersedes_edge.from_ref == _fp(result.superseding)
    assert result.supersedes_edge.to_ref == _fp(prior)
    assert result.superseded_ref == _fp(prior)
    # The lineage keeps the first observed-at.
    assert result.first_observed_at.value_ns == _T0 + 2 * _MINUTE
    # The new artifact's anchors are frozen at the new fit.
    assert result.superseding.anchor.low.as_fraction() == _price(108_100).as_fraction()


def test_refit_leaves_prior_untouched_earlier_evidence_remains() -> None:
    prior = _mint(observed_at=_T0 + 2 * _MINUTE)
    prior_fp_before = _fp(prior)
    _ok(refit(prior, anchor=_anchor(low=108_100), observed_at=Instant(value_ns=_T0 + 8 * _MINUTE)))
    # The prior object is immutable — its fingerprint is unchanged, earlier evidence remains.
    assert _fp(prior) == prior_fp_before
    assert prior.observed_at.value_ns == _T0 + 2 * _MINUTE


def test_refit_carries_family_and_defaults_from_prior() -> None:
    prior = _mint(observed_at=_T0 + 2 * _MINUTE, evidence_class=EvidenceClass.UNCONFIRMED)
    result = _ok(
        refit(prior, anchor=_anchor(low=108_050), observed_at=Instant(value_ns=_T0 + 8 * _MINUTE))
    )
    # Same family identity + rule, and evidence class / parameters default to the prior's.
    assert result.superseding.family == prior.family
    assert result.superseding.confirmation_rule == prior.confirmation_rule
    assert result.superseding.evidence_class is EvidenceClass.UNCONFIRMED
    assert dict(result.superseding.parameters) == dict(prior.parameters)


def test_refit_chain_keeps_first_observed_at() -> None:
    prior = _mint(observed_at=_T0 + 2 * _MINUTE)
    first = _ok(
        refit(prior, anchor=_anchor(low=108_100), observed_at=Instant(value_ns=_T0 + 8 * _MINUTE))
    )
    # A second refit passes the lineage's original first observed-at explicitly.
    second = _ok(
        refit(
            first.superseding,
            anchor=_anchor(low=108_200),
            observed_at=Instant(value_ns=_T0 + 12 * _MINUTE),
            first_observed_at=first.first_observed_at,
        )
    )
    assert second.first_observed_at.value_ns == _T0 + 2 * _MINUTE


def test_refit_refuses_observed_at_before_prior() -> None:
    prior = _mint(observed_at=_T0 + 5 * _MINUTE)
    result = refit(
        prior, anchor=_anchor(low=108_100), observed_at=Instant(value_ns=_T0 + 2 * _MINUTE)
    )
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "observed_at"


def test_refit_refuses_first_observed_at_after_the_fit() -> None:
    prior = _mint(observed_at=_T0 + 2 * _MINUTE)
    result = refit(
        prior,
        anchor=_anchor(low=108_100),
        observed_at=Instant(value_ns=_T0 + 8 * _MINUTE),
        first_observed_at=Instant(value_ns=_T0 + 20 * _MINUTE),
    )
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "first_observed_at"


def test_refit_refuses_identical_fit() -> None:
    prior = _mint(observed_at=_T0 + 2 * _MINUTE)
    # Same anchor, observed_at, parameters, evidence class => same fact, not a new artifact.
    result = refit(prior, anchor=_anchor(), observed_at=Instant(value_ns=_T0 + 2 * _MINUTE))
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "anchor"


def test_refit_runs_the_emission_invariant() -> None:
    prior = _mint(observed_at=_T0 + 2 * _MINUTE)
    # Anchor end after the refit observed_at is an emission-invariant violation (FM-1).
    late_anchor = _anchor(start=_T0, end=_T0 + 30 * _MINUTE)
    result = refit(prior, anchor=late_anchor, observed_at=Instant(value_ns=_T0 + 8 * _MINUTE))
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "invalid input"


def test_refit_refuses_non_object_prior() -> None:
    result = refit(object(), anchor=_anchor(), observed_at=Instant(value_ns=_T0 + 8 * _MINUTE))
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "prior"


def test_refit_refuses_bad_observed_at_type() -> None:
    prior = _mint()
    result = refit(prior, anchor=_anchor(low=108_100), observed_at=object())
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "observed_at"


def test_refit_refuses_bad_first_observed_at_type() -> None:
    prior = _mint(observed_at=_T0 + 2 * _MINUTE)
    result = refit(
        prior,
        anchor=_anchor(low=108_100),
        observed_at=Instant(value_ns=_T0 + 8 * _MINUTE),
        first_observed_at="not-an-instant",
    )
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "first_observed_at"


# --- FM-2: admission to the governed library --------------------------------


def test_admit_accepts_precise_family() -> None:
    family = _family()
    admitted = _ok(admit_to_governed_library(family))
    assert admitted is family


def test_admit_accepts_clock_confirmed_degenerate() -> None:
    family = _family(
        descriptor="confirmed the instant it is derived", clock_confirmed=True, bound=0
    )
    admitted = _ok(admit_to_governed_library(family))
    assert admitted.confirmation_rule.clock_confirmed is True


def test_admit_refuses_imprecise_rule_as_policy_rejection() -> None:
    # A family hand-built with a blank descriptor (bypassing try_create) is turned away.
    identity = _ok(FamilyIdentity.try_create("vague-concept", 1, "zone"))
    blank_rule = ConfirmationRule(
        descriptor="   ", clock_confirmed=False, confirmation_delay_bound=None
    )
    family = DeclaredFamily(identity=identity, confirmation_rule=blank_rule)
    result = admit_to_governed_library(family)
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "policy rejection"
    assert result.context["field"] == "confirmation_rule"


def test_admit_refuses_non_family() -> None:
    result = admit_to_governed_library(object())
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "family"


def test_admit_refuses_family_with_wrong_rule_type() -> None:
    class _FakeFamily:
        def __init__(self, identity: object, confirmation_rule: object) -> None:
            self.identity = identity
            self.confirmation_rule = confirmation_rule

    fake = _FakeFamily(_ok(FamilyIdentity.try_create("f", 1, "point")), "not-a-rule")
    result = admit_to_governed_library(fake)
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "family"


def test_fm2_imprecise_concept_never_builds_a_rule() -> None:
    # The escape hatch: an imprecise (blank) concept never even produces a ConfirmationRule,
    # so it is never offered to admission — it stays free in the ungoverned research lane.
    result = ConfirmationRule.try_create("   ")
    assert isinstance(result, TypedRefusal)


# --- AC #4: invalidation never cascades automatically -----------------------


class _ParentInvalidatedPredicate:
    """A family invalidation predicate: the child cascades when its parent is invalidated."""

    def cascades(self, *, parent: ResolvedState, child: ResolvedState, at: Instant) -> bool:
        return parent.invalidated


class _NeverPredicate:
    def cascades(self, *, parent: ResolvedState, child: ResolvedState, at: Instant) -> bool:
        return False


def _child_and_invalidated_parent() -> tuple[ResolvedState, ResolvedState]:
    parent = _mint(observed_at=_T0 + 1 * _MINUTE)
    child = _mint(observed_at=_T0 + 2 * _MINUTE, evidence_class=EvidenceClass.CONFIRMED)
    parent_inval = _ok(
        InvalidationRecord.try_create(_fp(parent), Instant(value_ns=_T0 + 6 * _MINUTE))
    )
    at = Instant(value_ns=_T0 + 10 * _MINUTE)
    parent_state = _ok(resolve_state(parent, [parent_inval], at=at))
    child_state = _ok(resolve_state(child, [], at=at))
    return child_state, parent_state


def test_resolve_state_never_cascades_automatically() -> None:
    child_state, parent_state = _child_and_invalidated_parent()
    # The parent is invalidated, but the child's OWN fold does not cascade — it stays valid.
    assert parent_state.invalidated is True
    assert child_state.still_valid is True


def test_resolve_cascade_applies_predicate_at_read_time() -> None:
    child_state, parent_state = _child_and_invalidated_parent()
    at = Instant(value_ns=_T0 + 10 * _MINUTE)
    resolution = _ok(
        resolve_cascade(child_state, parent_state, _ParentInvalidatedPredicate(), at=at)
    )
    assert isinstance(resolution, CascadeResolution)
    assert resolution.still_valid_before_cascade is True
    assert resolution.cascade_invalidated is True
    assert resolution.still_valid is False
    # The child's own read is unchanged — cascade is layered on top, never stored.
    assert child_state.still_valid is True


def test_resolve_cascade_predicate_that_does_not_fire() -> None:
    child_state, parent_state = _child_and_invalidated_parent()
    at = Instant(value_ns=_T0 + 10 * _MINUTE)
    resolution = _ok(resolve_cascade(child_state, parent_state, _NeverPredicate(), at=at))
    assert resolution.cascade_invalidated is False
    assert resolution.still_valid is True


def test_resolve_cascade_refuses_bad_inputs() -> None:
    child_state, parent_state = _child_and_invalidated_parent()
    at = Instant(value_ns=_T0 + 10 * _MINUTE)
    bad_child = resolve_cascade(object(), parent_state, _NeverPredicate(), at=at)
    assert isinstance(bad_child, TypedRefusal)
    assert bad_child.context["field"] == "child_state"
    bad_parent = resolve_cascade(child_state, object(), _NeverPredicate(), at=at)
    assert isinstance(bad_parent, TypedRefusal)
    assert bad_parent.context["field"] == "parent_state"
    bad_at = resolve_cascade(child_state, parent_state, _NeverPredicate(), at=object())
    assert isinstance(bad_at, TypedRefusal)
    assert bad_at.context["field"] == "at"
    bad_pred = resolve_cascade(child_state, parent_state, object(), at=at)
    assert isinstance(bad_pred, TypedRefusal)
    assert bad_pred.context["field"] == "predicate"


def test_resolve_cascade_refuses_non_bool_predicate_result() -> None:
    child_state, parent_state = _child_and_invalidated_parent()
    at = Instant(value_ns=_T0 + 10 * _MINUTE)

    class _BadPredicate:
        def cascades(self, *, parent: ResolvedState, child: ResolvedState, at: Instant) -> bool:
            return "yes"  # type: ignore[return-value]

    result = resolve_cascade(child_state, parent_state, _BadPredicate(), at=at)
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "predicate"


def test_predicate_satisfies_the_protocol_seam() -> None:
    assert isinstance(_ParentInvalidatedPredicate(), InvalidationPredicate)


# --- integration: identical records deduplicate by fingerprint --------------


def test_identical_records_deduplicate_by_fingerprint() -> None:
    obj = _mint()
    a = _ok(ConfirmationRecord.try_create(_fp(obj), Instant(value_ns=_T0 + 3 * _MINUTE)))
    b = _ok(ConfirmationRecord.try_create(_fp(obj), Instant(value_ns=_T0 + 3 * _MINUTE)))
    assert _ok(a.content_fingerprint()) == _ok(b.content_fingerprint())


def test_lifecycle_records_reference_object_by_fingerprint() -> None:
    obj = _mint()
    obj_fp = _fp(obj)
    conf = _ok(ConfirmationRecord.try_create(obj_fp, Instant(value_ns=_T0 + 3 * _MINUTE)))
    inval = _ok(InvalidationRecord.try_create(obj_fp, Instant(value_ns=_T0 + 6 * _MINUTE)))
    inter = _ok(
        InteractionRecord.try_create(
            obj_fp, Instant(value_ns=_T0 + 4 * _MINUTE), _price(108_100), "touch", _rational(1, 10)
        )
    )
    assert conf.object_ref == obj_fp
    assert inval.object_ref == obj_fp
    assert inter.object_ref == obj_fp
    assert _ok(fingerprint(obj.fp1_identity())) == obj_fp
