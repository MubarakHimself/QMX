"""ContributionHit pin tuple — additive CT-40 DTO (Story 53.3; FR-WF-07).

A pin stores exactly ``(qualified_id, package_version, availability_revision)``.
It is never a descriptor digest, never fp1, never a grant, and was not on the
wire at inspect SHA ``270e992`` (DEC-0415, DEC-0443, DEC-0450; SCN-0018).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_refusal,
)

__all__ = [
    "CONTRIBUTION_PIN_CONTRACT",
    "CONTRIBUTION_PIN_DTO_OWNER",
    "CONTRIBUTION_PIN_IS_GRANT",
    "CONTRIBUTION_PIN_NEW_CT_MINTED",
    "CONTRIBUTION_PIN_PERSISTENCE_STORE",
    "CONTRIBUTION_PIN_REFUSED_CT",
    "CONTRIBUTION_PIN_SCHEMA",
    "CONTRIBUTION_PIN_SCHEMA_FILE",
    "CONTRIBUTION_PIN_SCHEMA_NAME",
    "CONTRIBUTION_PIN_SIXTH_STORE_MINTED",
    "CONTRIBUTION_PIN_WIRED_AT_INSPECT_SHA",
    "FEDERATED_HIT_INSPECT_SHA",
    "PIN_TUPLE_FIELDS",
    "ContributionPin",
    "parse_contribution_pin",
    "refuse_contribution_pin_digest",
    "refuse_contribution_pin_fp1",
    "refuse_contribution_pin_grant",
    "validate_contribution_pin",
]


FEDERATED_HIT_INSPECT_SHA: Final[str] = "270e992"
CONTRIBUTION_PIN_WIRED_AT_INSPECT_SHA: Final[bool] = False
CONTRIBUTION_PIN_DTO_OWNER: Final[str] = "COMP-QMA-WIRE"
CONTRIBUTION_PIN_CONTRACT: Final[str] = "CT-40"
CONTRIBUTION_PIN_NEW_CT_MINTED: Final[bool] = False
CONTRIBUTION_PIN_REFUSED_CT: Final[str] = "CT-52"
CONTRIBUTION_PIN_SCHEMA: Final[str] = "qma.wire.contribution_pin.v1"
CONTRIBUTION_PIN_SCHEMA_NAME: Final[str] = "contribution_pin"
CONTRIBUTION_PIN_SCHEMA_FILE: Final[str] = "contribution_pin.v1.schema.json"
# Pin leases live on the existing plugin-install projection (DEC-0429; AR-WF-05).
CONTRIBUTION_PIN_PERSISTENCE_STORE: Final[str] = "plugin_install_records"
CONTRIBUTION_PIN_SIXTH_STORE_MINTED: Final[bool] = False
CONTRIBUTION_PIN_IS_GRANT: Final[bool] = False

PIN_TUPLE_FIELDS: Final[tuple[str, str, str]] = (
    "qualified_id",
    "package_version",
    "availability_revision",
)

_FORBIDDEN_PIN_IDENTITY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "fp1",
        "kind",
        "artifact_ref",
        "source_ref",
        "snapshot_ref",
        "locator",
        "research_ref",
        "digest",
        "descriptor_digest",
        "descriptor_hash",
        "content_hash",
        "tree_digest",
        "grant_id",
        "granted_ops",
        "GrantRecord",
        "hit_class",
        "plugin_id",
        "point",
        "package_id",
        "availability",
    }
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


def refuse_contribution_pin_fp1(**extra: object) -> TypedRefusal:
    """A pin is never fp1 / Artifact-rail identity (SCN-0018 Branch C)."""
    field = str(extra.pop("field", "identity"))
    return _policy(
        field,
        "ContributionHit pin stores (qualified_id, package_version, "
        "availability_revision) and is never fp1, never a registry kind, and "
        "never ArtifactHit.kind (DEC-0415; FR-WF-07; SCN-0018)",
        decision="DEC-0415",
        pin_is_grant=False,
        **extra,
    )


def refuse_contribution_pin_digest(**extra: object) -> TypedRefusal:
    """A pin is never a descriptor digest (cheap-veto A4; FR-WF-07)."""
    field = str(extra.pop("field", "digest"))
    return _policy(
        field,
        "ContributionHit pin stores (qualified_id, package_version, "
        "availability_revision), not a descriptor digest (DEC-0415; FR-WF-07; "
        "cheap-veto A4)",
        decision="DEC-0415",
        pin_is_grant=False,
        **extra,
    )


def refuse_contribution_pin_grant(**extra: object) -> TypedRefusal:
    """A pin is not a grant (SCN-0018 Then 1; Branch B)."""
    field = str(extra.pop("field", "grant"))
    return _policy(
        field,
        "a ContributionHit pin is not a grant; matching live tuple may proceed "
        "to grant checks later (Stories 54/55) (DEC-0415; FR-WF-06; FR-WF-08; "
        "SCN-0018)",
        decision="DEC-0415",
        pin_is_grant=False,
        grant_checks_pending=True,
        **extra,
    )


def _looks_like_fp1(value: str) -> bool:
    return value.strip().casefold().startswith("fp1:")


def _looks_like_digest(value: str) -> bool:
    folded = value.strip().casefold()
    if folded.startswith("sha256:"):
        return True
    return len(folded) == 64 and all(ch in "0123456789abcdef" for ch in folded)


def _parse_nonempty_str(value: object, field: str) -> Result[str]:
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(
            field,
            f"ContributionPin.{field} is a non-empty string (CT-40; FR-WF-07)",
            given=repr(value),
        )
    token = value.strip()
    if _looks_like_fp1(token):
        return refuse_contribution_pin_fp1(field=field, given=token)
    if field == "package_version" and _looks_like_digest(token):
        return refuse_contribution_pin_digest(field=field, given=token)
    return Ok(token)


def _parse_availability_revision(value: object) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return _invalid(
            "availability_revision",
            "ContributionPin.availability_revision is a non-negative integer (CT-40; FR-WF-07)",
            given=repr(value),
        )
    if value < 0:
        return _invalid(
            "availability_revision",
            "ContributionPin.availability_revision is a non-negative integer (CT-40; FR-WF-07)",
            given=value,
        )
    return Ok(value)


@dataclass(frozen=True, slots=True)
class ContributionPin:
    """Pinned ContributionHit identity — the three-tuple only (FR-WF-07)."""

    qualified_id: str
    package_version: str
    availability_revision: int

    @classmethod
    def try_create(
        cls,
        *,
        qualified_id: object,
        package_version: object,
        availability_revision: object,
        **extra: object,
    ) -> Result[ContributionPin]:
        """Validate a pin. Refuses fp1, digest, grant, and hit identity extras."""
        stolen = tuple(sorted(name for name in extra if name in _FORBIDDEN_PIN_IDENTITY_KEYS))
        if stolen:
            if any(key in {"fp1", "kind", "artifact_ref", "research_ref"} for key in stolen):
                return refuse_contribution_pin_fp1(fields=stolen, given=stolen)
            if any("digest" in key or key.endswith("_hash") for key in stolen):
                return refuse_contribution_pin_digest(fields=stolen, given=stolen)
            if any(key.startswith("grant") or key == "GrantRecord" for key in stolen):
                return refuse_contribution_pin_grant(fields=stolen, given=stolen)
            return refuse_contribution_pin_fp1(fields=stolen, given=stolen)
        qualified = _parse_nonempty_str(qualified_id, "qualified_id")
        if is_refusal(qualified):
            return qualified
        version = _parse_nonempty_str(package_version, "package_version")
        if is_refusal(version):
            return version
        revision = _parse_availability_revision(availability_revision)
        if is_refusal(revision):
            return revision
        return Ok(
            cls(
                qualified_id=qualified.value,
                package_version=version.value,
                availability_revision=revision.value,
            )
        )

    @classmethod
    def from_hit(cls, hit: object) -> Result[ContributionPin]:
        """Store only the pin tuple from a live ContributionHit — never fp1."""
        return cls.try_create(
            qualified_id=getattr(hit, "qualified_id", None),
            package_version=getattr(hit, "package_version", None),
            availability_revision=getattr(hit, "availability_revision", None),
        )

    def as_tuple(self) -> tuple[str, str, int]:
        """``(qualified_id, package_version, availability_revision)``."""
        return (self.qualified_id, self.package_version, self.availability_revision)

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "availability_revision": self.availability_revision,
                "package_version": self.package_version,
                "qualified_id": self.qualified_id,
            }
        )


def parse_contribution_pin(value: object) -> Result[ContributionPin]:
    """Parse a pin mapping. Extra identity keys refuse (SCN-0018 Branch C)."""
    if isinstance(value, ContributionPin):
        return ContributionPin.try_create(
            qualified_id=value.qualified_id,
            package_version=value.package_version,
            availability_revision=value.availability_revision,
        )
    if not isinstance(value, Mapping):
        return _invalid(
            "pin",
            "ContributionPin is a mapping of (qualified_id, package_version, "
            "availability_revision) (CT-40; FR-WF-07)",
            given=repr(value),
        )
    body = cast("Mapping[str, object]", value)
    stolen = sorted(key for key in _FORBIDDEN_PIN_IDENTITY_KEYS if key in body)
    if stolen:
        return ContributionPin.try_create(
            qualified_id=body.get("qualified_id"),
            package_version=body.get("package_version"),
            availability_revision=body.get("availability_revision"),
            **{key: body[key] for key in stolen},
        )
    unknown = sorted(key for key in body if key not in PIN_TUPLE_FIELDS)
    if unknown:
        return refuse_contribution_pin_digest(fields=unknown, given=unknown)
    return ContributionPin.try_create(
        qualified_id=body.get("qualified_id"),
        package_version=body.get("package_version"),
        availability_revision=body.get("availability_revision"),
    )


def validate_contribution_pin(value: object) -> Result[ContributionPin]:
    """Schema-facing alias of ``parse_contribution_pin``."""
    return parse_contribution_pin(value)
