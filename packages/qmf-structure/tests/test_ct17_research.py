"""Tier-1/Tier-2 tests for the escape hatch and graduation to governed evidence (Story 9.4).

Covers L33/DEC-0129/DEC-0133: an imprecise concept stays in the ungoverned research lane, and
graduation carries a promoted-from lineage edge to the originating experiment.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import Fingerprint, Result, fingerprint, is_ok, is_refusal
from qmf.structure import (
    ConfirmationRule,
    DeclaredFamily,
    FamilyIdentity,
    Graduation,
    GraduationEdge,
    SwingPointFamily,
    graduate_to_governed,
)

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    assert is_ok(result), f"expected {what}, got {result}"
    return result.value


def _fp(tag: str) -> Fingerprint:
    return _unwrap(fingerprint({"artifact": tag}), "fingerprint")


def _family() -> DeclaredFamily:
    identity = _unwrap(FamilyIdentity.try_create("graduated-zone", 1, "zone"), "identity")
    rule = _unwrap(
        ConfirmationRule.try_create("confirmed the moment price trades through the zone edge"),
        "rule",
    )
    return _unwrap(DeclaredFamily.try_create(identity, rule), "family")


def test_an_imprecise_concept_never_leaves_the_research_lane() -> None:
    # The escape hatch: an imprecise concept has no precise confirmation rule, so it cannot even
    # produce a ConfirmationRule — it stays freely usable in plain Python, never governed (FM-2).
    assert is_refusal(ConfirmationRule.try_create(""))
    assert is_refusal(ConfirmationRule.try_create("   "))


def test_graduation_admits_and_carries_a_promoted_from_edge() -> None:
    graduated = _fp("governed-family")
    experiment = _fp("originating-experiment")
    result = _unwrap(
        graduate_to_governed(
            family=_family(), graduated_ref=graduated, originating_experiment_ref=experiment
        ),
        "graduation",
    )
    assert isinstance(result, Graduation)
    assert result.promoted_from_edge.edge_type == "promoted-from"
    assert result.promoted_from_edge.from_ref == graduated
    assert result.promoted_from_edge.to_ref == experiment
    assert is_ok(result.promoted_from_edge.content_fingerprint())


def test_the_swing_family_graduates_identically_no_privilege() -> None:
    family = _unwrap(
        SwingPointFamily.create(left=1, right=1, confirmation_delay_bound=3), "swing family"
    )
    result = graduate_to_governed(
        family=family,
        graduated_ref=_fp("swing-governed"),
        originating_experiment_ref=_fp("swing-experiment"),
    )
    assert is_ok(result)


def test_graduation_refuses_a_non_family_and_bad_refs() -> None:
    assert is_refusal(
        graduate_to_governed(
            family=object(), graduated_ref=_fp("a"), originating_experiment_ref=_fp("b")
        )
    )
    assert is_refusal(
        graduate_to_governed(
            family=_family(), graduated_ref="not-an-fp", originating_experiment_ref=_fp("b")
        )
    )
    assert is_refusal(
        graduate_to_governed(
            family=_family(), graduated_ref=_fp("a"), originating_experiment_ref="not-an-fp"
        )
    )


def test_graduation_refuses_linking_an_artifact_to_itself() -> None:
    same = _fp("same-artifact")
    assert is_refusal(
        graduate_to_governed(family=_family(), graduated_ref=same, originating_experiment_ref=same)
    )


def test_graduation_edge_fingerprint_is_derived_and_tagged() -> None:
    edge = GraduationEdge(from_ref=_fp("a"), to_ref=_fp("b"))
    identity = edge.fp1_identity()
    assert identity["class"] == "structure-graduation-edge"
    assert identity["edge_type"] == "promoted-from"
    assert _unwrap(edge.content_fingerprint(), "edge fp").value.startswith("fp1:sha256:")
