"""ContributionHit listing status — additive CT-40 DTO (Story 53.4; FR-WF-12).

Listings distinguish published vs configured vs granted vs reachable vs
healthy as five independent booleans. A hit is not a grant: publishing or
discovering a ContributionHit does not authorize invoke, even when published
and healthy (SCN-0018 Branch B; DEC-0415; FR-WF-06). ``product_session`` /
``granted_ops`` stay a separate AD-8 state — this DTO does not mint them
(Epic 55). Occupancy on this path is none. Stage 0 hypotheses / ``research_ref``
are not hits here. No new CT number (do not mint CT-52).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Literal, cast

from qma.wire.federated_discovery import (
    CONTRIBUTION_HIT_IS_GRANT,
    CONTRIBUTION_HIT_WIRED_AT_INSPECT_SHA,
    ContributionHit,
    parse_federated_hit,
    refuse_hypothesis_hit_class,
    refuse_view_contribution_hit,
)
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_refusal,
)

__all__ = [
    "CONTRIBUTION_HIT_IS_GRANT",
    "CONTRIBUTION_LISTING_CONTRACT",
    "CONTRIBUTION_LISTING_DTO_OWNER",
    "CONTRIBUTION_LISTING_NEW_CT_MINTED",
    "CONTRIBUTION_LISTING_OCCUPANCY",
    "CONTRIBUTION_LISTING_REFUSED_CT",
    "CONTRIBUTION_LISTING_SCHEMA",
    "CONTRIBUTION_LISTING_SCHEMA_FILE",
    "CONTRIBUTION_LISTING_SCHEMA_NAME",
    "CONTRIBUTION_LISTING_STATUS_AXES",
    "CONTRIBUTION_LISTING_WIRED_AT_INSPECT_SHA",
    "GRANTED_OPS_ARE_PACK_ENABLEMENT",
    "PRODUCT_SESSION_MINTED",
    "ContributionListing",
    "parse_contribution_listing",
    "refuse_collapsed_listing_status",
    "refuse_granted_ops_as_pack_enablement",
    "refuse_hit_as_grant",
    "refuse_listing_occupancy",
    "refuse_product_session_mint",
    "validate_contribution_listing",
]


CONTRIBUTION_LISTING_WIRED_AT_INSPECT_SHA: Final[bool] = CONTRIBUTION_HIT_WIRED_AT_INSPECT_SHA
CONTRIBUTION_LISTING_DTO_OWNER: Final[str] = "COMP-QMA-WIRE"
CONTRIBUTION_LISTING_CONTRACT: Final[str] = "CT-40"
CONTRIBUTION_LISTING_NEW_CT_MINTED: Final[bool] = False
CONTRIBUTION_LISTING_REFUSED_CT: Final[str] = "CT-52"
CONTRIBUTION_LISTING_SCHEMA: Final[str] = "qma.wire.contribution_listing.v1"
CONTRIBUTION_LISTING_SCHEMA_NAME: Final[str] = "contribution_listing"
CONTRIBUTION_LISTING_SCHEMA_FILE: Final[str] = "contribution_listing.v1.schema.json"
CONTRIBUTION_LISTING_OCCUPANCY: Final[str] = "none"
PRODUCT_SESSION_MINTED: Final[bool] = False
GRANTED_OPS_ARE_PACK_ENABLEMENT: Final[bool] = False

CONTRIBUTION_LISTING_STATUS_AXES: Final[tuple[str, str, str, str, str]] = (
    "published",
    "configured",
    "granted",
    "reachable",
    "healthy",
)

_FORBIDDEN_LISTING_KEYS: Final[frozenset[str]] = frozenset(
    {
        "status",
        "state",
        "availability_status",
        "product_session",
        "product_session_id",
        "psess",
        "granted_ops",
        "grant_id",
        "GrantRecord",
        "research_ref",
        "fp1",
        "kind",
        "artifact_ref",
        "view_id",
        "ui_view",
        "hypothesis",
        "qml_candidate",
    }
)

_PRODUCT_SESSION_KEYS: Final[frozenset[str]] = frozenset(
    {
        "product_session",
        "product_session_id",
        "psess",
        "granted_ops",
        "GrantRecord",
    }
)

_COLLAPSED_STATUS_KEYS: Final[frozenset[str]] = frozenset(
    {"status", "state", "availability_status"}
)


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def refuse_hit_as_grant(**extra: object) -> TypedRefusal:
    """SCN-0018 Branch B — a published ContributionHit is not invoke authority."""
    field = str(extra.pop("field", "authorizes_invoke"))
    return _policy(
        field,
        "publishing or discovering a ContributionHit does not authorize invoke; "
        "a hit is not a grant even when published and healthy "
        "(DEC-0415; FR-WF-06; SCN-0018 Branch B)",
        decision="DEC-0415",
        scn="SCN-0018",
        branch="B",
        hit_is_grant=False,
        authorizes_invoke=False,
        product_session_minted=False,
        **extra,
    )


def refuse_collapsed_listing_status(**extra: object) -> TypedRefusal:
    """Listings must not collapse the five AD-15 axes into one status enum."""
    field = str(extra.pop("field", "status"))
    return _policy(
        field,
        "discovery listings distinguish published vs configured vs granted vs "
        "reachable vs healthy as independent axes; a collapsed status enum is "
        "refused (FR-WF-12; AD-15; DEC-0415)",
        decision="DEC-0415",
        axes=CONTRIBUTION_LISTING_STATUS_AXES,
        **extra,
    )


def refuse_product_session_mint(**extra: object) -> TypedRefusal:
    """Story 53.4 does not mint product_session (Epic 55; AD-8)."""
    field = str(extra.pop("field", "product_session"))
    return _policy(
        field,
        "product_session.granted_ops stay a separate AD-8 state; this listing "
        "DTO does not mint product_session (Epic 55; FR-WF-38; AD-8; AD-13)",
        decision="DEC-0421",
        product_session_minted=False,
        granted_ops_are_pack_enablement=False,
        epic="55",
        **extra,
    )


def refuse_granted_ops_as_pack_enablement(**extra: object) -> TypedRefusal:
    """Session-granted is AD-8, not pack enablement (AD-13; FR-WF-38)."""
    field = str(extra.pop("field", "granted_ops"))
    return _policy(
        field,
        "installed ≠ enabled ≠ session-granted; granted_ops is AD-8 state, not "
        "pack enablement (AD-13; FR-WF-38; DEC-0421)",
        decision="DEC-0421",
        granted_ops_are_pack_enablement=False,
        product_session_minted=False,
        **extra,
    )


def refuse_listing_occupancy(**extra: object) -> TypedRefusal:
    """Discovery occupancy on this path stays none (FR-WF-05)."""
    field = str(extra.pop("field", "occupancy"))
    return _policy(
        field,
        "discovery listings consume no occupancy; this path is never a door run "
        "(FR-WF-05; DEC-0449)",
        occupancy=CONTRIBUTION_LISTING_OCCUPANCY,
        is_door_run=False,
        **extra,
    )


def _parse_bool(value: object, field: str) -> Result[bool]:
    if not isinstance(value, bool):
        return _invalid(
            field,
            f"ContributionListing.{field} is a boolean axis (FR-WF-12; AD-15)",
            given=repr(value),
            axes=list(CONTRIBUTION_LISTING_STATUS_AXES),
        )
    return Ok(value)


def _parse_hit(value: object) -> Result[ContributionHit]:
    if isinstance(value, ContributionHit):
        return ContributionHit.try_create(
            plugin_id=value.plugin_id,
            point=value.point,
            qualified_id=value.qualified_id,
            package_id=value.package_id,
            package_version=value.package_version,
            availability_revision=value.availability_revision,
            availability=value.availability,
            hit_class=value.hit_class,
        )
    parsed = parse_federated_hit(value)
    if is_refusal(parsed):
        return parsed
    hit = parsed.value
    if not isinstance(hit, ContributionHit):
        return _policy(
            "hit",
            "a contribution listing describes a ContributionHit, not KnowledgeHit "
            "or ArtifactHit (FR-WF-12; DEC-0415)",
            given=type(hit).__name__,
        )
    return Ok(hit)


@dataclass(frozen=True, slots=True)
class ContributionListing:
    """Five-axis listing over a ContributionHit. Never invoke authority."""

    hit: ContributionHit
    published: bool
    configured: bool
    granted: bool
    reachable: bool
    healthy: bool
    authorizes_invoke: Literal[False] = False
    occupancy: str = CONTRIBUTION_LISTING_OCCUPANCY

    @classmethod
    def try_create(
        cls,
        *,
        hit: object,
        published: object,
        configured: object,
        granted: object,
        reachable: object,
        healthy: object,
        authorizes_invoke: object = False,
        occupancy: object = CONTRIBUTION_LISTING_OCCUPANCY,
        **extra: object,
    ) -> Result[ContributionListing]:
        """Validate a listing. Refuses grant-as-hit, product_session, collapsed status."""
        stolen = tuple(sorted(name for name in extra if name in _FORBIDDEN_LISTING_KEYS))
        if stolen:
            if any(key in _PRODUCT_SESSION_KEYS for key in stolen):
                if any(key in {"granted_ops", "GrantRecord"} for key in stolen):
                    return refuse_granted_ops_as_pack_enablement(fields=stolen, given=stolen)
                return refuse_product_session_mint(fields=stolen, given=stolen)
            if any(key in _COLLAPSED_STATUS_KEYS for key in stolen):
                return refuse_collapsed_listing_status(fields=stolen, given=stolen)
            if any(key in {"research_ref", "hypothesis", "qml_candidate"} for key in stolen):
                return refuse_hypothesis_hit_class(fields=stolen, given=stolen)
            if any(key in {"view_id", "ui_view"} for key in stolen):
                return refuse_view_contribution_hit(fields=stolen, given=stolen)
            return refuse_hit_as_grant(fields=stolen, given=stolen)
        if authorizes_invoke is True:
            return refuse_hit_as_grant(given=True, published=published, healthy=healthy)
        if authorizes_invoke not in {False, None}:
            return refuse_hit_as_grant(given=repr(authorizes_invoke))
        if occupancy != CONTRIBUTION_LISTING_OCCUPANCY:
            return refuse_listing_occupancy(given=repr(occupancy))
        parsed_hit = _parse_hit(hit)
        if is_refusal(parsed_hit):
            return parsed_hit
        pub = _parse_bool(published, "published")
        if is_refusal(pub):
            return pub
        conf = _parse_bool(configured, "configured")
        if is_refusal(conf):
            return conf
        grant = _parse_bool(granted, "granted")
        if is_refusal(grant):
            return grant
        reach = _parse_bool(reachable, "reachable")
        if is_refusal(reach):
            return reach
        health = _parse_bool(healthy, "healthy")
        if is_refusal(health):
            return health
        return Ok(
            cls(
                hit=parsed_hit.value,
                published=pub.value,
                configured=conf.value,
                granted=grant.value,
                reachable=reach.value,
                healthy=health.value,
                authorizes_invoke=False,
                occupancy=CONTRIBUTION_LISTING_OCCUPANCY,
            )
        )

    def tool_availability_intersection(self) -> bool:
        """AD-9 intersection cannot complete here — product_session is unminted."""
        return False

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "authorizes_invoke": False,
                "configured": self.configured,
                "granted": self.granted,
                "healthy": self.healthy,
                "hit": dict(self.hit.to_payload()),
                "occupancy": CONTRIBUTION_LISTING_OCCUPANCY,
                "published": self.published,
                "reachable": self.reachable,
            }
        )


def parse_contribution_listing(value: object) -> Result[ContributionListing]:
    """Parse a listing mapping. Extra grant / session / status keys refuse."""
    if isinstance(value, ContributionListing):
        return ContributionListing.try_create(
            hit=value.hit,
            published=value.published,
            configured=value.configured,
            granted=value.granted,
            reachable=value.reachable,
            healthy=value.healthy,
            authorizes_invoke=value.authorizes_invoke,
            occupancy=value.occupancy,
        )
    if not isinstance(value, Mapping):
        return _invalid(
            "listing",
            "ContributionListing is a mapping of a ContributionHit plus the five "
            "status axes (CT-40; FR-WF-12)",
            given=repr(value),
        )
    body = cast("Mapping[str, object]", value)
    stolen = sorted(key for key in _FORBIDDEN_LISTING_KEYS if key in body)
    extras = {key: body[key] for key in stolen} if stolen else {}
    return ContributionListing.try_create(
        hit=body.get("hit"),
        published=body.get("published"),
        configured=body.get("configured"),
        granted=body.get("granted"),
        reachable=body.get("reachable"),
        healthy=body.get("healthy"),
        authorizes_invoke=body.get("authorizes_invoke", False),
        occupancy=body.get("occupancy", CONTRIBUTION_LISTING_OCCUPANCY),
        **extras,
    )


def validate_contribution_listing(value: object) -> Result[ContributionListing]:
    """Schema-then-DTO validation for the listing overlay."""
    from qma.wire.schemas import validate_instance  # noqa: PLC0415

    if isinstance(value, ContributionListing):
        payload = dict(value.to_payload())
    elif isinstance(value, Mapping):
        payload = dict(cast("Mapping[str, object]", value))
    else:
        return parse_contribution_listing(value)
    checked = validate_instance(payload, CONTRIBUTION_LISTING_SCHEMA_NAME)
    if is_refusal(checked):
        return checked
    return parse_contribution_listing(checked.value)
