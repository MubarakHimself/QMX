"""ContributionHit listings — published vs healthy; a hit is not a grant (53.4).

COMP-QMA-DAEMON query overlay over live ``published_contributions()``. Five
status axes stay independent. Publishing or discovering a hit does not
authorize invoke (SCN-0018 Branch B). ``view:*`` is AD-17 wire DTO only
(GAP-0081). Stage 0 hypotheses / ``research_ref`` stay off this DTO.
Occupancy remains none. ``product_session.granted_ops`` stay a separate AD-8
state — this module does not mint ``product_session`` (Epic 55). Host grants
are an injected overlay, never pack enablement.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, cast

from qma.core.ports.qmb import QMB_OPENS_DAEMON_SQLITE, qmb_opens_daemon_sqlite
from qma.daemon.discovery.federated import FEDERATED_SEARCH_OCCUPANCY
from qma.daemon.discovery.research_surface import (
    HYPOTHESES_ARE_FEDERATED_HITS,
    HYPOTHESIS_LISTING_SURFACE,
    refuse_federated_hypothesis_kwargs,
)
from qma.daemon.plugins.loader import PluginLoader
from qma.wire.contribution_listing import (
    CONTRIBUTION_HIT_IS_GRANT,
    CONTRIBUTION_LISTING_OCCUPANCY,
    CONTRIBUTION_LISTING_STATUS_AXES,
    CONTRIBUTION_LISTING_WIRED_AT_INSPECT_SHA,
    GRANTED_OPS_ARE_PACK_ENABLEMENT,
    PRODUCT_SESSION_MINTED,
    ContributionListing,
    refuse_granted_ops_as_pack_enablement,
    refuse_hit_as_grant,
    refuse_listing_occupancy,
    refuse_product_session_mint,
)
from qma.wire.federated_discovery import ContributionHit
from qma.wire.view_presentation import (
    VIEW_IS_CONTRIBUTION_HIT,
    VIEW_IS_PLUGIN_CONTRIBUTION_POINT,
    refuse_view_as_contribution_hit,
)
from qmf.core import Ok, Result, is_refusal
from qmf.core.refusal import TypedRefusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "CONTRIBUTION_HIT_IS_GRANT",
    "CONTRIBUTION_LISTING_OCCUPANCY",
    "CONTRIBUTION_LISTING_STATUS_AXES",
    "CONTRIBUTION_LISTING_WIRED_AT_INSPECT_SHA",
    "GRANTED_OPS_ARE_PACK_ENABLEMENT",
    "LISTING_IS_DOOR_RUN",
    "LISTING_OPENS_FOURTH_STORE",
    "LISTING_OWNER",
    "PRODUCT_SESSION_MINTED",
    "VIEW_IS_CONTRIBUTION_HIT",
    "VIEW_IS_PLUGIN_CONTRIBUTION_POINT",
    "ContributionListingService",
    "contribution_listing_identity",
    "refuse_hit_as_grant",
    "refuse_product_session_mint",
]


LISTING_OWNER: Final[str] = "COMP-QMA-DAEMON"
LISTING_IS_DOOR_RUN: Final[bool] = False
LISTING_OPENS_FOURTH_STORE: Final[bool] = False

_HYPOTHESIS_KWARGS: Final[tuple[str, ...]] = (
    "hypothesis",
    "hypotheses",
    "research_candidate",
    "research_candidates",
    "qml_candidate",
    "stage0_hypothesis",
    "research_ref",
)


def contribution_listing_identity() -> dict[str, object]:
    """Identity-bearing listing fields. Package SemVer is omitted."""
    return {
        "axes": list(CONTRIBUTION_LISTING_STATUS_AXES),
        "hit_is_grant": CONTRIBUTION_HIT_IS_GRANT,
        "hypotheses_are_federated_hits": HYPOTHESES_ARE_FEDERATED_HITS,
        "hypothesis_listing_surface": HYPOTHESIS_LISTING_SURFACE,
        "is_door_run": LISTING_IS_DOOR_RUN,
        "occupancy": CONTRIBUTION_LISTING_OCCUPANCY,
        "opens_fourth_store": LISTING_OPENS_FOURTH_STORE,
        "owner": LISTING_OWNER,
        "product_session_minted": PRODUCT_SESSION_MINTED,
        "granted_ops_are_pack_enablement": GRANTED_OPS_ARE_PACK_ENABLEMENT,
        "qmb_opens_daemon_sqlite": QMB_OPENS_DAEMON_SQLITE,
        "view_is_contribution_hit": VIEW_IS_CONTRIBUTION_HIT,
        "view_is_plugin_contribution_point": VIEW_IS_PLUGIN_CONTRIBUTION_POINT,
        "wired_at_inspect_sha": CONTRIBUTION_LISTING_WIRED_AT_INSPECT_SHA,
    }


def _row_field(row: object, name: str) -> object:
    if isinstance(row, Mapping):
        return cast("Mapping[str, object]", row).get(name)
    return getattr(row, name, None)


def _hit_from_row(row: object) -> Result[ContributionHit | None]:
    qualified = _row_field(row, "qualified_id")
    if not isinstance(qualified, str) or qualified.strip() == "":
        return Ok(None)
    package_id = _row_field(row, "package_id")
    plugin_id = _row_field(row, "plugin_id")
    built = ContributionHit.try_create(
        plugin_id=plugin_id,
        point=_row_field(row, "point"),
        qualified_id=qualified,
        package_id=package_id if package_id is not None else plugin_id,
        package_version=_row_field(row, "package_version"),
        availability_revision=_row_field(row, "availability_revision"),
        availability=_row_field(row, "availability") or "enabled",
    )
    if is_refusal(built):
        return built
    hit: ContributionHit | None = built.value
    return Ok(hit)


def _disabled_hit(hit: ContributionHit) -> Result[ContributionHit]:
    if hit.availability != "enabled":
        return Ok(hit)
    return ContributionHit.try_create(
        plugin_id=hit.plugin_id,
        point=hit.point,
        qualified_id=hit.qualified_id,
        package_id=hit.package_id,
        package_version=hit.package_version,
        availability_revision=hit.availability_revision,
        availability="disabled",
    )


@dataclass
class ContributionListingService:
    """Host listing overlay. A hit is never a grant; occupancy stays none."""

    loader: PluginLoader
    _configured: dict[str, ContributionHit] = field(
        default_factory=dict[str, ContributionHit], init=False
    )
    _granted: set[str] = field(default_factory=set[str], init=False)
    _reachable: set[str] = field(default_factory=set[str], init=False)
    _healthy: set[str] = field(default_factory=set[str], init=False)

    @property
    def occupancy(self) -> str:
        return CONTRIBUTION_LISTING_OCCUPANCY

    @property
    def hit_is_grant(self) -> bool:
        return CONTRIBUTION_HIT_IS_GRANT

    @property
    def product_session_minted(self) -> bool:
        return PRODUCT_SESSION_MINTED

    @property
    def granted_ops_are_pack_enablement(self) -> bool:
        return GRANTED_OPS_ARE_PACK_ENABLEMENT

    def note_configured(self, hit: ContributionHit) -> None:
        """Record bytes-present / configured independently of live publication."""
        self._configured[hit.qualified_id] = hit

    def note_host_grant(self, qualified_id: str) -> None:
        """Host grant overlay — not product_session.granted_ops (Epic 55)."""
        self._granted.add(qualified_id)

    def note_reachable(self, qualified_id: str) -> None:
        self._reachable.add(qualified_id)

    def note_healthy(self, qualified_id: str) -> None:
        self._healthy.add(qualified_id)

    def mint_product_session(self, **extra: object) -> TypedRefusal:
        """Refused — Story 53.4 does not mint product_session (Epic 55)."""
        return refuse_product_session_mint(**extra)

    def authorize_invoke(self, listing: ContributionListing | ContributionHit) -> TypedRefusal:
        """SCN-0018 Branch B — listings / hits never authorize invoke."""
        extra: dict[str, object] = {"occupancy": CONTRIBUTION_LISTING_OCCUPANCY}
        if isinstance(listing, ContributionListing):
            extra.update(
                {
                    "published": listing.published,
                    "configured": listing.configured,
                    "granted": listing.granted,
                    "reachable": listing.reachable,
                    "healthy": listing.healthy,
                    "qualified_id": listing.hit.qualified_id,
                }
            )
        else:
            extra["qualified_id"] = listing.qualified_id
        return refuse_hit_as_grant(**extra)

    def describe(
        self,
        listing: ContributionListing,
        *,
        treat_as_grant: bool = False,
        prose: str | None = None,
    ) -> Result[Mapping[str, object]]:
        """Copilot / skill / listing prose. Treating a hit as a grant is forbidden."""
        if treat_as_grant:
            return refuse_hit_as_grant(field="prose", given=prose or "treat_as_grant")
        if prose is not None:
            folded = prose.casefold()
            if any(
                token in folded
                for token in (
                    "authorized to invoke",
                    "may invoke",
                    "grant to invoke",
                    "hit is a grant",
                    "published is permission",
                )
            ):
                return refuse_hit_as_grant(field="prose", given=prose)
        return Ok(
            MappingProxyType(
                {
                    "authorizes_invoke": False,
                    "axes": {
                        "configured": listing.configured,
                        "granted": listing.granted,
                        "healthy": listing.healthy,
                        "published": listing.published,
                        "reachable": listing.reachable,
                    },
                    "hit_is_grant": False,
                    "occupancy": CONTRIBUTION_LISTING_OCCUPANCY,
                    "qualified_id": listing.hit.qualified_id,
                }
            )
        )

    def list_contributions(
        self,
        *,
        occupancy: object = CONTRIBUTION_LISTING_OCCUPANCY,
        hypothesis: object = None,
        hypotheses: object = None,
        research_candidate: object = None,
        research_candidates: object = None,
        qml_candidate: object = None,
        stage0_hypothesis: object = None,
        research_ref: object = None,
        view_id: object = None,
        ui_view: object = None,
        product_session: object = None,
        product_session_id: object = None,
        granted_ops: object = None,
        status: object = None,
    ) -> Result[tuple[ContributionListing, ...]]:
        """Render five-axis listings. Occupancy none. A hit is not a grant."""
        if occupancy != CONTRIBUTION_LISTING_OCCUPANCY:
            return refuse_listing_occupancy(given=repr(occupancy))
        hypothesis_refusal = refuse_federated_hypothesis_kwargs(
            {
                "hypothesis": hypothesis,
                "hypotheses": hypotheses,
                "research_candidate": research_candidate,
                "research_candidates": research_candidates,
                "qml_candidate": qml_candidate,
                "stage0_hypothesis": stage0_hypothesis,
                "research_ref": research_ref,
            }
        )
        if hypothesis_refusal is not None:
            return hypothesis_refusal
        if view_id is not None or ui_view is not None:
            return refuse_view_as_contribution_hit(
                field="view_id" if view_id is not None else "ui_view",
                given=repr(view_id if view_id is not None else ui_view),
            )
        if product_session is not None or product_session_id is not None:
            return refuse_product_session_mint(given=repr(product_session or product_session_id))
        if granted_ops is not None:
            return refuse_granted_ops_as_pack_enablement(given=repr(granted_ops))
        if status is not None:
            return policy_rejection(
                "status",
                "discovery listings distinguish published vs configured vs granted "
                "vs reachable vs healthy as independent axes (FR-WF-12; AD-15)",
                given=repr(status),
                axes=list(CONTRIBUTION_LISTING_STATUS_AXES),
            )

        live: dict[str, ContributionHit] = {}
        for row in self.loader.published_contributions():
            mapped = _hit_from_row(row)
            if is_refusal(mapped):
                return mapped
            hit = mapped.value
            if hit is None:
                continue
            live[hit.qualified_id] = hit
            self._configured[hit.qualified_id] = hit

        rows: list[ContributionListing] = []
        seen: set[str] = set()
        for qualified_id, hit in live.items():
            listing = ContributionListing.try_create(
                hit=hit,
                published=hit.availability == "enabled",
                configured=True,
                granted=qualified_id in self._granted,
                reachable=qualified_id in self._reachable,
                healthy=qualified_id in self._healthy,
                authorizes_invoke=False,
                occupancy=CONTRIBUTION_LISTING_OCCUPANCY,
            )
            if is_refusal(listing):
                return listing
            rows.append(listing.value)
            seen.add(qualified_id)

        for qualified_id, hit in self._configured.items():
            if qualified_id in seen:
                continue
            unpublished = _disabled_hit(hit)
            if is_refusal(unpublished):
                return unpublished
            listing = ContributionListing.try_create(
                hit=unpublished.value,
                published=False,
                configured=True,
                granted=qualified_id in self._granted,
                reachable=qualified_id in self._reachable,
                healthy=qualified_id in self._healthy,
                authorizes_invoke=False,
                occupancy=CONTRIBUTION_LISTING_OCCUPANCY,
            )
            if is_refusal(listing):
                return listing
            rows.append(listing.value)

        if FEDERATED_SEARCH_OCCUPANCY != CONTRIBUTION_LISTING_OCCUPANCY:
            return refuse_listing_occupancy(given=FEDERATED_SEARCH_OCCUPANCY)
        if qmb_opens_daemon_sqlite():
            return invalid_input(
                "sqlite",
                "QMB never opens daemon sqlite on the listing path (FR-WF-05)",
            )
        return Ok(tuple(rows))
