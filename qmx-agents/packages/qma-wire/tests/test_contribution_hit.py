"""Story 53.1 — federated DTO gains ContributionHit on additive CT-40."""

from __future__ import annotations

from qma.wire import (
    CONTRIBUTION_AVAILABILITY,
    CONTRIBUTION_HIT_POINTS,
    CONTRIBUTION_HIT_WIRED_AT_INSPECT_SHA,
    FEDERATED_HIT_CLASSES,
    FEDERATED_HIT_CONTRACT,
    FEDERATED_HIT_DTO_OWNER,
    FEDERATED_HIT_INSPECT_SHA,
    FEDERATED_HIT_NEW_CT_MINTED,
    FEDERATED_HIT_REFUSED_CT,
    HIT_CLASS_ARTIFACT,
    HIT_CLASS_CONTRIBUTION,
    HIT_CLASS_KNOWLEDGE,
    HYPOTHESIS_LISTING_SURFACE,
    ArtifactHit,
    ContributionHit,
    parse_federated_hit,
    refuse_contribution_fp1_identity,
    refuse_hypothesis_hit_class,
    refuse_qml_candidate_hit,
    refuse_strats_hit_class,
    refuse_view_contribution_hit,
    validate_family_payload,
    validate_federated_hit,
)
from qmf.core import is_ok, is_refusal

_FP1 = "fp1:sha256:" + ("ab" * 32)

_LIVE = {
    "hit_class": "contribution",
    "plugin_id": "analysis-backtest",
    "point": "tool",
    "qualified_id": "analysis-backtest:qmb",
    "package_id": "analysis-backtest",
    "package_version": "0.1.0",
    "availability_revision": 12,
    "availability": "enabled",
}


def test_inspect_sha_did_not_wire_contribution_hit() -> None:
    """Claiming ContributionHit already existed at 270e992 fails the story."""
    assert FEDERATED_HIT_INSPECT_SHA == "270e992"
    assert CONTRIBUTION_HIT_WIRED_AT_INSPECT_SHA is False
    assert FEDERATED_HIT_NEW_CT_MINTED is False
    assert FEDERATED_HIT_REFUSED_CT == "CT-52"
    assert FEDERATED_HIT_DTO_OWNER == "COMP-QMA-WIRE"
    assert FEDERATED_HIT_CONTRACT == "CT-40"


def test_third_class_is_contribution_after_this_story() -> None:
    assert HIT_CLASS_CONTRIBUTION == "contribution"
    assert {
        HIT_CLASS_KNOWLEDGE,
        HIT_CLASS_ARTIFACT,
        HIT_CLASS_CONTRIBUTION,
    } == FEDERATED_HIT_CLASSES
    assert is_ok(validate_family_payload("facade_search", {"query": "qmb"}))
    assert is_ok(validate_family_payload("facade_get", {"hit_class": "contribution"}))

    checked = ContributionHit.try_create(
        plugin_id=_LIVE["plugin_id"],
        point=_LIVE["point"],
        qualified_id=_LIVE["qualified_id"],
        package_id=_LIVE["package_id"],
        package_version=_LIVE["package_version"],
        availability_revision=_LIVE["availability_revision"],
        availability=_LIVE["availability"],
    )
    assert is_ok(checked)
    hit = checked.value
    assert hit.hit_class == "contribution"
    assert hit.to_payload() == {
        "availability": "enabled",
        "availability_revision": 12,
        "hit_class": "contribution",
        "package_id": "analysis-backtest",
        "package_version": "0.1.0",
        "plugin_id": "analysis-backtest",
        "point": "tool",
        "qualified_id": "analysis-backtest:qmb",
    }
    assert "fp1" not in hit.to_payload()
    assert "kind" not in hit.to_payload()
    parsed = parse_federated_hit(hit.to_payload())
    assert is_ok(parsed)
    assert isinstance(parsed.value, ContributionHit)
    schema_ok = validate_federated_hit(dict(_LIVE))
    assert is_ok(schema_ok)
    assert isinstance(schema_ok.value, ContributionHit)


def test_contribution_identity_is_published_tuple_never_fp1() -> None:
    hit = ContributionHit.try_create(
        plugin_id="analysis-backtest",
        point="tool",
        qualified_id="analysis-backtest:qmb",
        package_id="analysis-backtest",
        package_version="0.1.0",
        availability_revision=12,
        availability="enabled",
    )
    assert is_ok(hit)
    assert hit.value.published_identity() == (
        "analysis-backtest",
        "tool",
        "analysis-backtest:qmb",
        "analysis-backtest",
        "0.1.0",
        12,
        "enabled",
    )
    assert "tool" in CONTRIBUTION_HIT_POINTS
    assert "enabled" in CONTRIBUTION_AVAILABILITY

    as_fp1 = parse_federated_hit({**_LIVE, "fp1": _FP1})
    assert is_refusal(as_fp1)
    assert as_fp1.context["decision"] == "DEC-0415"

    as_kind = ContributionHit.try_create(
        plugin_id="analysis-backtest",
        point="tool",
        qualified_id="analysis-backtest:qmb",
        package_id="analysis-backtest",
        package_version="0.1.0",
        availability_revision=12,
        availability="enabled",
        kind="bot-definition",
    )
    assert is_refusal(as_kind)

    fp1_version = ContributionHit.try_create(
        plugin_id="analysis-backtest",
        point="tool",
        qualified_id="analysis-backtest:qmb",
        package_id="analysis-backtest",
        package_version=_FP1,
        availability_revision=12,
        availability="enabled",
    )
    assert is_refusal(fp1_version)
    assert is_refusal(refuse_contribution_fp1_identity())

    artifact_kind = ArtifactHit.try_create(fp1=_FP1, kind="graph_template")
    assert is_refusal(artifact_kind)
    artifact_contribution = ArtifactHit.try_create(fp1=_FP1, kind="contribution")
    assert is_refusal(artifact_contribution)


def test_strats_qml_candidate_and_hypothesis_kinds_are_refused() -> None:
    strats = parse_federated_hit({**_LIVE, "hit_class": "strats"})
    assert is_refusal(strats)
    assert strats.context["decision"] == "DEC-0412"
    assert strats.context["dead"] is True

    candidate = parse_federated_hit({**_LIVE, "hit_class": "qml_candidate"})
    assert is_refusal(candidate)
    assert candidate.context["hit_class"] == "qml_candidate"
    assert candidate.context["listing_surface"] == HYPOTHESIS_LISTING_SURFACE == "qml.research"

    hypothesis = parse_federated_hit({**_LIVE, "hit_class": "hypothesis"})
    assert is_refusal(hypothesis)
    assert hypothesis.context["listing_surface"] == "qml.research"

    typed = parse_federated_hit({"type": "HypothesisHit", "hit_class": "contribution"})
    assert is_refusal(typed)

    hypo_point = ContributionHit.try_create(
        plugin_id="analysis-backtest",
        point="hypothesis",
        qualified_id="analysis-backtest:draft",
        package_id="analysis-backtest",
        package_version="0.1.0",
        availability_revision=1,
        availability="enabled",
    )
    assert is_refusal(hypo_point)

    assert is_refusal(refuse_strats_hit_class())
    assert is_refusal(refuse_qml_candidate_hit())
    assert is_refusal(refuse_hypothesis_hit_class())


def test_view_star_is_not_a_contribution_hit() -> None:
    view_point = parse_federated_hit({**_LIVE, "point": "view:heatmap"})
    assert is_refusal(view_point)
    assert view_point.context["gap"] == "GAP-0081"

    ui_view = ContributionHit.try_create(
        plugin_id="desk-ui",
        point="ui_view",
        qualified_id="desk-ui:panel",
        package_id="desk-ui",
        package_version="1.0.0",
        availability_revision=1,
        availability="enabled",
    )
    assert is_refusal(ui_view)
    assert ui_view.context["gap"] == "GAP-0081"

    view_class = parse_federated_hit({**_LIVE, "hit_class": "view"})
    assert is_refusal(view_class)
    assert is_refusal(refuse_view_contribution_hit())


def test_contribution_hit_rejects_bad_revision_and_availability() -> None:
    negative = ContributionHit.try_create(
        plugin_id="analysis-backtest",
        point="tool",
        qualified_id="analysis-backtest:qmb",
        package_id="analysis-backtest",
        package_version="0.1.0",
        availability_revision=-1,
        availability="enabled",
    )
    assert is_refusal(negative)

    as_bool = ContributionHit.try_create(
        plugin_id="analysis-backtest",
        point="tool",
        qualified_id="analysis-backtest:qmb",
        package_id="analysis-backtest",
        package_version="0.1.0",
        availability_revision=True,
        availability="enabled",
    )
    assert is_refusal(as_bool)

    occupancy = validate_federated_hit({**_LIVE, "occupancy": "none"})
    assert is_refusal(occupancy)
