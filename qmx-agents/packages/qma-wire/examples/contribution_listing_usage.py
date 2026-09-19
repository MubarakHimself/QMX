"""Reference usage — listing DTO and view:* are not grants (Story 53.4)."""

from __future__ import annotations

from qma.wire import (
    CONTRIBUTION_HIT_IS_GRANT,
    CONTRIBUTION_LISTING_OCCUPANCY,
    PRODUCT_SESSION_MINTED,
    VIEW_IS_CONTRIBUTION_HIT,
    ContributionHit,
    ContributionListing,
    ViewPresentation,
    parse_federated_hit,
    refuse_hit_as_grant,
)
from qmf.core import is_ok, is_refusal


def main() -> None:
    assert CONTRIBUTION_HIT_IS_GRANT is False
    assert PRODUCT_SESSION_MINTED is False
    assert VIEW_IS_CONTRIBUTION_HIT is False
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
    listing = ContributionListing.try_create(
        hit=hit.value,
        published=True,
        configured=True,
        granted=False,
        reachable=False,
        healthy=True,
    )
    assert is_ok(listing)
    assert listing.value.authorizes_invoke is False
    assert listing.value.occupancy == CONTRIBUTION_LISTING_OCCUPANCY == "none"
    assert is_refusal(refuse_hit_as_grant())

    view = ViewPresentation.try_create(
        view_id="view:heatmap",
        view_version=1,
        op_id="sector-intel.inspect",
        mount="mounted",
        parameter_binding={"schema": "sector-intel.inspect.v1", "values": {}},
        snapshot_cursor=9,
        stale=False,
    )
    assert is_ok(view)
    assert view.value.is_contribution_hit is False
    as_hit = parse_federated_hit(
        {
            "hit_class": "contribution",
            "plugin_id": "desk-ui",
            "point": "view:heatmap",
            "qualified_id": "desk-ui:heatmap",
            "package_id": "desk-ui",
            "package_version": "1.0.0",
            "availability_revision": 1,
            "availability": "enabled",
        }
    )
    assert is_refusal(as_hit)
    print("listing axes distinct; view:* is AD-17 DTO only; hit is not a grant")


if __name__ == "__main__":
    main()
