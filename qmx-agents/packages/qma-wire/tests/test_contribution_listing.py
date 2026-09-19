"""Story 53.4 — a hit is not a grant; listings distinguish published from healthy."""

from __future__ import annotations

from qma.wire import (
    CONTRIBUTION_HIT_IS_GRANT,
    CONTRIBUTION_LISTING_CONTRACT,
    CONTRIBUTION_LISTING_DTO_OWNER,
    CONTRIBUTION_LISTING_NEW_CT_MINTED,
    CONTRIBUTION_LISTING_OCCUPANCY,
    CONTRIBUTION_LISTING_REFUSED_CT,
    CONTRIBUTION_LISTING_SCHEMA,
    CONTRIBUTION_LISTING_SCHEMA_FILE,
    CONTRIBUTION_LISTING_SCHEMA_NAME,
    CONTRIBUTION_LISTING_STATUS_AXES,
    CONTRIBUTION_LISTING_WIRED_AT_INSPECT_SHA,
    FEDERATED_HIT_INSPECT_SHA,
    GRANTED_OPS_ARE_PACK_ENABLEMENT,
    PRODUCT_SESSION_MINTED,
    SCHEMA_FILES,
    ContributionHit,
    ContributionListing,
    parse_contribution_listing,
    refuse_collapsed_listing_status,
    refuse_granted_ops_as_pack_enablement,
    refuse_hit_as_grant,
    refuse_product_session_mint,
    validate_contribution_listing,
)
from qmf.core import is_ok, is_refusal

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


def _hit() -> ContributionHit:
    built = ContributionHit.try_create(
        plugin_id=_LIVE["plugin_id"],
        point=_LIVE["point"],
        qualified_id=_LIVE["qualified_id"],
        package_id=_LIVE["package_id"],
        package_version=_LIVE["package_version"],
        availability_revision=_LIVE["availability_revision"],
        availability=_LIVE["availability"],
    )
    assert is_ok(built)
    return built.value


def test_inspect_sha_and_no_product_session() -> None:
    assert FEDERATED_HIT_INSPECT_SHA == "270e992"
    assert CONTRIBUTION_LISTING_WIRED_AT_INSPECT_SHA is False
    assert CONTRIBUTION_LISTING_NEW_CT_MINTED is False
    assert CONTRIBUTION_LISTING_REFUSED_CT == "CT-52"
    assert CONTRIBUTION_LISTING_DTO_OWNER == "COMP-QMA-WIRE"
    assert CONTRIBUTION_LISTING_CONTRACT == "CT-40"
    assert CONTRIBUTION_HIT_IS_GRANT is False
    assert PRODUCT_SESSION_MINTED is False
    assert GRANTED_OPS_ARE_PACK_ENABLEMENT is False
    assert CONTRIBUTION_LISTING_OCCUPANCY == "none"
    assert SCHEMA_FILES[CONTRIBUTION_LISTING_SCHEMA_NAME] == CONTRIBUTION_LISTING_SCHEMA_FILE
    assert CONTRIBUTION_LISTING_SCHEMA == "qma.wire.contribution_listing.v1"
    assert CONTRIBUTION_LISTING_STATUS_AXES == (
        "published",
        "configured",
        "granted",
        "reachable",
        "healthy",
    )


def test_listing_distinguishes_five_axes_and_never_authorizes_invoke() -> None:
    listing = ContributionListing.try_create(
        hit=_hit(),
        published=True,
        configured=True,
        granted=True,
        reachable=True,
        healthy=True,
    )
    assert is_ok(listing)
    body = listing.value
    assert body.published is True
    assert body.configured is True
    assert body.granted is True
    assert body.reachable is True
    assert body.healthy is True
    assert body.authorizes_invoke is False
    assert body.occupancy == "none"
    assert body.tool_availability_intersection() is False
    payload = dict(body.to_payload())
    assert payload["authorizes_invoke"] is False
    assert payload["occupancy"] == "none"
    assert "product_session" not in payload
    assert "granted_ops" not in payload
    assert "grant_id" not in payload
    parsed = parse_contribution_listing(payload)
    assert is_ok(parsed)
    schema_ok = validate_contribution_listing(payload)
    assert is_ok(schema_ok)


def test_published_and_healthy_is_still_not_a_grant() -> None:
    as_grant = ContributionListing.try_create(
        hit=_hit(),
        published=True,
        configured=True,
        granted=False,
        reachable=False,
        healthy=True,
        authorizes_invoke=True,
    )
    assert is_refusal(as_grant)
    assert as_grant.context["decision"] == "DEC-0415"
    assert as_grant.context["branch"] == "B"
    assert as_grant.context["hit_is_grant"] is False
    assert is_refusal(refuse_hit_as_grant())


def test_product_session_and_granted_ops_are_refused() -> None:
    session = parse_contribution_listing(
        {
            "hit": dict(_LIVE),
            "published": True,
            "configured": True,
            "granted": False,
            "reachable": False,
            "healthy": False,
            "authorizes_invoke": False,
            "occupancy": "none",
            "product_session_id": "psess:1",
        }
    )
    assert is_refusal(session)
    assert session.context["product_session_minted"] is False
    assert session.context["epic"] == "55"

    ops = parse_contribution_listing(
        {
            "hit": dict(_LIVE),
            "published": True,
            "configured": True,
            "granted": False,
            "reachable": False,
            "healthy": False,
            "authorizes_invoke": False,
            "occupancy": "none",
            "granted_ops": ["grant:1"],
        }
    )
    assert is_refusal(ops)
    assert ops.context["granted_ops_are_pack_enablement"] is False
    assert is_refusal(refuse_product_session_mint())
    assert is_refusal(refuse_granted_ops_as_pack_enablement())


def test_collapsed_status_and_occupancy_and_hypotheses_refuse() -> None:
    collapsed = parse_contribution_listing(
        {
            "hit": dict(_LIVE),
            "published": True,
            "configured": True,
            "granted": False,
            "reachable": False,
            "healthy": False,
            "authorizes_invoke": False,
            "occupancy": "none",
            "status": "healthy",
        }
    )
    assert is_refusal(collapsed)
    assert collapsed.context["axes"] == CONTRIBUTION_LISTING_STATUS_AXES
    assert is_refusal(refuse_collapsed_listing_status())

    busy = ContributionListing.try_create(
        hit=_hit(),
        published=True,
        configured=True,
        granted=False,
        reachable=False,
        healthy=False,
        occupancy="run",
    )
    assert is_refusal(busy)
    assert busy.context["occupancy"] == "none"

    hypo = parse_contribution_listing(
        {
            "hit": dict(_LIVE),
            "published": True,
            "configured": True,
            "granted": False,
            "reachable": False,
            "healthy": False,
            "authorizes_invoke": False,
            "occupancy": "none",
            "research_ref": "fp1:sha256:" + ("ab" * 32),
        }
    )
    assert is_refusal(hypo)
    assert hypo.context["listing_surface"] == "qml.research"

    view = parse_contribution_listing(
        {
            "hit": dict(_LIVE),
            "published": True,
            "configured": True,
            "granted": False,
            "reachable": False,
            "healthy": False,
            "authorizes_invoke": False,
            "occupancy": "none",
            "view_id": "view:heatmap",
        }
    )
    assert is_refusal(view)
    assert view.context["gap"] == "GAP-0081"
