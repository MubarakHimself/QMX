"""Reference usage — listings distinguish published from healthy (Story 53.4)."""

from __future__ import annotations

from qma.core.plugins import PluginContext
from qma.daemon.discovery import (
    CONTRIBUTION_HIT_IS_GRANT,
    CONTRIBUTION_LISTING_OCCUPANCY,
    PRODUCT_SESSION_MINTED,
    ContributionListingService,
    contribution_listing_identity,
)
from qma.daemon.plugins import DaemonPluginContext, PluginLoader
from qmf.core import is_ok, is_refusal


def _activate(ctx: PluginContext) -> None:
    assert isinstance(ctx, DaemonPluginContext)
    ctx.register_tool("inspect", {"name": "inspect"})


def main() -> None:
    identity = contribution_listing_identity()
    assert identity["occupancy"] == CONTRIBUTION_LISTING_OCCUPANCY == "none"
    assert identity["hit_is_grant"] is False is CONTRIBUTION_HIT_IS_GRANT
    assert identity["product_session_minted"] is False is PRODUCT_SESSION_MINTED
    print("listing occupancy=none; hit is not a grant; product_session unminted")

    loader = PluginLoader()
    enabled = loader.enable(
        {
            "id": "research-corpus",
            "version": "0.1.0",
            "qma_api": ">=0.1.0,<1.0.0",
            "desk": "research",
            "entrypoint": "research_corpus.activate",
            "contributions": [{"point": "tool", "local_id": "inspect"}],
            "contributes": [{"point": "tool", "local_id": "inspect"}],
        },
        activator=_activate,
    )
    assert is_ok(enabled)
    listings = ContributionListingService(loader)
    found = listings.list_contributions()
    assert is_ok(found)
    row = found.value[0]
    assert row.published is True
    assert row.configured is True
    assert row.granted is False
    assert row.healthy is False
    assert row.authorizes_invoke is False
    refused = listings.authorize_invoke(row)
    assert is_refusal(refused)
    print("published ≠ granted ≠ healthy; invoke refused (SCN-0018 Branch B)")


if __name__ == "__main__":
    main()
