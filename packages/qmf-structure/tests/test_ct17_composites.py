"""Tier-1/Tier-2 tests for CT-17 composite objects (Story 9.4).

Covers DEC-0129/DEC-0131/DEC-0115: composite instants are the maxima over children, the
confirmation-delay bound is the sum, order significance is identity-bearing, and lineage is
the children fingerprint set.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    EvidenceClass,
    ExactRational,
    Fingerprint,
    Instant,
    Result,
    UnitKind,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.structure import (
    CompositeChild,
    CompositeObject,
    ConfirmationRule,
    FamilyIdentity,
)

T = TypeVar("T")
_MINUTE = 60_000_000_000
_BASE = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    assert is_ok(result), f"expected {what}, got {result}"
    return result.value


def _fp(tag: str) -> Fingerprint:
    return _unwrap(fingerprint({"child": tag}), "fingerprint")


def _identity() -> FamilyIdentity:
    return _unwrap(FamilyIdentity.try_create("cluster", 1, "graph"), "identity")


def _rule() -> ConfirmationRule:
    return _unwrap(
        ConfirmationRule.try_create(
            "confirmed the moment every child is confirmed", confirmation_delay_bound=2
        ),
        "rule",
    )


def _child(
    tag: str, observed_min: int, confirmed_min: int | None = None, bound: int | None = 2
) -> CompositeChild:
    return _unwrap(
        CompositeChild.try_create(
            _fp(tag),
            Instant(value_ns=_BASE + observed_min * _MINUTE),
            confirmed_at=None
            if confirmed_min is None
            else Instant(value_ns=_BASE + confirmed_min * _MINUTE),
            confirmation_delay_bound=bound,
        ),
        "child",
    )


def _composite(children: list[CompositeChild], *, ordered: bool = True) -> CompositeObject:
    return _unwrap(
        CompositeObject.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            children=children,
            evidence_class=EvidenceClass.CONFIRMED,
            ordered=ordered,
        ),
        "composite",
    )


def test_composite_instants_are_the_maxima_over_children() -> None:
    composite = _composite([_child("a", 3, 5, 2), _child("b", 4, 9, 3)])
    assert composite.observed_at == Instant(value_ns=_BASE + 4 * _MINUTE)
    assert composite.confirmed_at == Instant(value_ns=_BASE + 9 * _MINUTE)
    # The confirmation-delay bound is the sum of the children's bounds.
    assert composite.confirmation_delay_bound == 5


def test_composite_is_unconfirmed_until_every_child_is_confirmed() -> None:
    composite = _composite([_child("a", 3, 5, 2), _child("b", 4, None, 3)])
    assert composite.confirmed_at is None


def test_composite_bound_is_unbounded_when_any_child_is_unbounded() -> None:
    composite = _composite([_child("a", 3, 5, 2), _child("b", 4, 9, None)])
    assert composite.confirmation_delay_bound is None


def test_ordered_composite_child_order_is_identity_bearing() -> None:
    a, b = _child("a", 3, 5, 2), _child("b", 4, 9, 3)
    forward = _unwrap(_composite([a, b]).content_fingerprint(), "forward fp")
    reverse = _unwrap(_composite([b, a]).content_fingerprint(), "reverse fp")
    assert forward != reverse


def test_unordered_composite_fingerprints_regardless_of_child_order() -> None:
    a, b = _child("a", 3, 5, 2), _child("b", 4, 9, 3)
    forward = _unwrap(_composite([a, b], ordered=False).content_fingerprint(), "forward fp")
    reverse = _unwrap(_composite([b, a], ordered=False).content_fingerprint(), "reverse fp")
    assert forward == reverse


def test_input_fingerprints_are_the_children_lineage() -> None:
    a, b = _child("a", 3, 5, 2), _child("b", 4, 9, 3)
    ordered = _composite([a, b])
    assert ordered.input_fingerprints() == (a.ref, b.ref)
    unordered = _composite([b, a], ordered=False)
    assert unordered.input_fingerprints() == tuple(sorted((a.ref, b.ref), key=lambda fp: fp.value))


def test_composite_may_carry_exact_rational_parameters() -> None:
    tolerance = _unwrap(ExactRational.try_create(1, 4, UnitKind.DIMENSIONLESS_RATIO), "tolerance")
    composite = _unwrap(
        CompositeObject.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            children=[_child("a", 3, 5, 2)],
            evidence_class=EvidenceClass.CONFIRMED,
            parameters={"tolerance": tolerance},
        ),
        "parameterized composite",
    )
    assert composite.parameters["tolerance"].denominator == 4
    assert is_ok(composite.content_fingerprint())


def test_composite_refuses_bad_construction() -> None:
    good_child = _child("a", 3, 5, 2)
    assert is_refusal(
        CompositeObject.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            children=[],
            evidence_class=EvidenceClass.CONFIRMED,
        )
    )
    assert is_refusal(
        CompositeObject.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            children=[object()],
            evidence_class=EvidenceClass.CONFIRMED,
        )
    )
    assert is_refusal(
        CompositeObject.try_create(
            family=object(),
            confirmation_rule=_rule(),
            children=[good_child],
            evidence_class=EvidenceClass.CONFIRMED,
        )
    )
    assert is_refusal(
        CompositeObject.try_create(
            family=_identity(),
            confirmation_rule=object(),
            children=[good_child],
            evidence_class=EvidenceClass.CONFIRMED,
        )
    )
    assert is_refusal(
        CompositeObject.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            children=[good_child],
            evidence_class="nonsense",
        )
    )
    assert is_refusal(
        CompositeObject.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            children=[good_child],
            evidence_class=EvidenceClass.CONFIRMED,
            ordered="yes",
        )
    )
    assert is_refusal(
        CompositeObject.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            children="not a sequence",
            evidence_class=EvidenceClass.CONFIRMED,
        )
    )
    assert is_refusal(
        CompositeObject.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            children=[good_child],
            evidence_class=EvidenceClass.CONFIRMED,
            parameters={"bad": 0.5},
        )
    )


def test_composite_child_validations() -> None:
    assert is_refusal(CompositeChild.try_create("not-an-fp", Instant(value_ns=_BASE)))
    assert is_refusal(CompositeChild.try_create(_fp("a"), 0))
    assert is_refusal(
        CompositeChild.try_create(_fp("a"), Instant(value_ns=_BASE), confirmed_at="soon")
    )
    # confirmed_at before observed_at
    assert is_refusal(
        CompositeChild.try_create(
            _fp("a"),
            Instant(value_ns=_BASE + 5 * _MINUTE),
            confirmed_at=Instant(value_ns=_BASE + 3 * _MINUTE),
        )
    )
    assert is_refusal(
        CompositeChild.try_create(_fp("a"), Instant(value_ns=_BASE), confirmation_delay_bound=-1)
    )
