"""Wire compatibility law — sole authority in ``qma-wire`` (CT-40; AD-5; FR-Q14).

Same-major evolution is additive-only: new fields and message types may appear;
older clients ignore unknown fields and types. Deprecations remain served for
``registry:wire.deprecation_minors`` minor releases before removal. Family
``protocolVersion`` and format declarations keep old evidence readable.
No package other than ``qma-wire`` may declare compatibility policy.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Literal

from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
)

__all__ = [
    "COMPATIBILITY_AUTHORITY",
    "DEPRECATION_MINORS_DEFAULT",
    "DEPRECATION_MINORS_REGISTRY_KEY",
    "CompatibilityError",
    "CompatibilityVerdict",
    "FamilyFormatDeclaration",
    "ProtocolVersion",
    "SchemaEvolutionProposal",
    "assert_sole_compatibility_authority",
    "evaluate_deprecation_removal",
    "evaluate_schema_evolution",
    "ignore_unknown_fields",
    "ignore_unknown_types",
    "parse_protocol_version",
]


COMPATIBILITY_AUTHORITY: Final[str] = "qma-wire"
DEPRECATION_MINORS_REGISTRY_KEY: Final[str] = "wire.deprecation_minors"
# Registry default (docs/registry/variables.yaml); runtime value is registry-homed.
DEPRECATION_MINORS_DEFAULT: Final[int] = 2

_SEMVER: Final[re.Pattern[str]] = re.compile(
    r"\A(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\Z"
)


class CompatibilityError(ValueError):
    """Raised when a compatibility declaration cannot be constructed."""


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


@dataclass(frozen=True, slots=True)
class ProtocolVersion:
    """Parsed semver ``protocolVersion`` (major.minor.patch)."""

    major: int
    minor: int
    patch: int
    raw: str

    def same_major(self, other: ProtocolVersion) -> bool:
        return self.major == other.major

    def minor_distance(self, earlier: ProtocolVersion) -> int:
        """Non-negative minor delta when ``earlier`` precedes ``self`` on the same major."""
        if not self.same_major(earlier):
            raise CompatibilityError("minor_distance requires the same major")
        return self.minor - earlier.minor


def parse_protocol_version(value: object) -> Result[ProtocolVersion]:
    """Parse a semver ``protocolVersion`` string."""
    if not isinstance(value, str) or _SEMVER.match(value) is None:
        return _invalid(
            "protocolVersion",
            "protocolVersion must be a semver string",
            given=repr(value),
        )
    core = value.split("+", 1)[0].split("-", 1)[0]
    major_s, minor_s, patch_s = core.split(".")
    return Ok(
        ProtocolVersion(
            major=int(major_s),
            minor=int(minor_s),
            patch=int(patch_s),
            raw=value,
        )
    )


@dataclass(frozen=True, slots=True)
class FamilyFormatDeclaration:
    """``protocolVersion`` + family format stamp that keeps old evidence readable.

    Deprecated families stay served until the configured minor window elapses;
    their declarations remain so historical envelopes stay interpretable.
    """

    family_name: str
    protocol_version: str
    format_version: int
    deprecated_at_protocol_version: str | None = None
    removed: bool = False

    def leaves_old_evidence_readable(self) -> bool:
        """Format and protocol stamps remain after deprecation so old evidence reads."""
        return self.protocol_version != "" and self.format_version >= 1


@dataclass(frozen=True, slots=True)
class SchemaEvolutionProposal:
    """Proposed same-lineage schema change for the compatibility verifier."""

    base_protocol_version: str
    proposed_protocol_version: str
    base_fields: frozenset[str]
    proposed_fields: frozenset[str]
    base_types: frozenset[str]
    proposed_types: frozenset[str]
    declaring_package: str = COMPATIBILITY_AUTHORITY

    @classmethod
    def of(
        cls,
        *,
        base_protocol_version: str,
        proposed_protocol_version: str,
        base_fields: Sequence[str],
        proposed_fields: Sequence[str],
        base_types: Sequence[str],
        proposed_types: Sequence[str],
        declaring_package: str = COMPATIBILITY_AUTHORITY,
    ) -> SchemaEvolutionProposal:
        return cls(
            base_protocol_version=base_protocol_version,
            proposed_protocol_version=proposed_protocol_version,
            base_fields=frozenset(base_fields),
            proposed_fields=frozenset(proposed_fields),
            base_types=frozenset(base_types),
            proposed_types=frozenset(proposed_types),
            declaring_package=declaring_package,
        )

    @property
    def added_fields(self) -> frozenset[str]:
        return self.proposed_fields - self.base_fields

    @property
    def removed_fields(self) -> frozenset[str]:
        return self.base_fields - self.proposed_fields

    @property
    def added_types(self) -> frozenset[str]:
        return self.proposed_types - self.base_types

    @property
    def removed_types(self) -> frozenset[str]:
        return self.base_types - self.proposed_types


@dataclass(frozen=True, slots=True)
class CompatibilityVerdict:
    """Accepted additive (or same-schema) evolution within one major."""

    base: ProtocolVersion
    proposed: ProtocolVersion
    added_fields: frozenset[str]
    added_types: frozenset[str]
    kind: Literal["unchanged", "additive"]
    authority: str = COMPATIBILITY_AUTHORITY


def assert_sole_compatibility_authority(package: str) -> Result[str]:
    """Only ``qma-wire`` may declare wire compatibility policy."""
    if package != COMPATIBILITY_AUTHORITY:
        return _policy(
            "compatibility_authority",
            "no package other than qma-wire may declare wire compatibility policy",
            given=package,
            authority=COMPATIBILITY_AUTHORITY,
        )
    return Ok(COMPATIBILITY_AUTHORITY)


def evaluate_schema_evolution(
    proposal: SchemaEvolutionProposal,
) -> Result[CompatibilityVerdict]:
    """Accept same-major additive fields/types only; refuse removals and foreign policy."""
    authority = assert_sole_compatibility_authority(proposal.declaring_package)
    if not isinstance(authority, Ok):
        return authority

    base = parse_protocol_version(proposal.base_protocol_version)
    if not isinstance(base, Ok):
        return base
    proposed = parse_protocol_version(proposal.proposed_protocol_version)
    if not isinstance(proposed, Ok):
        return proposed

    if not base.value.same_major(proposed.value):
        return _policy(
            "protocolVersion",
            "same-major compatibility verifier does not accept a major bump; "
            "mint a new major outside additive evolution",
            base=base.value.raw,
            proposed=proposed.value.raw,
        )

    if proposed.value.minor < base.value.minor or (
        proposed.value.minor == base.value.minor and proposed.value.patch < base.value.patch
    ):
        return _invalid(
            "protocolVersion",
            "proposed protocolVersion must not regress within the major",
            base=base.value.raw,
            proposed=proposed.value.raw,
        )

    if proposal.removed_fields:
        return _policy(
            "fields",
            "same-major evolution accepts additive fields only; removals require "
            f"deprecation for {DEPRECATION_MINORS_REGISTRY_KEY} minors then a removal proposal",
            removed=sorted(proposal.removed_fields),
        )
    if proposal.removed_types:
        return _policy(
            "types",
            "same-major evolution accepts additive types only; removals require "
            f"deprecation for {DEPRECATION_MINORS_REGISTRY_KEY} minors then a removal proposal",
            removed=sorted(proposal.removed_types),
        )

    added_fields = proposal.added_fields
    added_types = proposal.added_types
    kind: Literal["unchanged", "additive"] = (
        "unchanged" if not added_fields and not added_types else "additive"
    )
    return Ok(
        CompatibilityVerdict(
            base=base.value,
            proposed=proposed.value,
            added_fields=added_fields,
            added_types=added_types,
            kind=kind,
        )
    )


def ignore_unknown_fields(
    payload: Mapping[str, object],
    known_fields: Sequence[str],
) -> dict[str, object]:
    """Older-client view: drop fields not in the client's known set."""
    known = frozenset(known_fields)
    return {key: value for key, value in payload.items() if key in known}


def ignore_unknown_types(
    message_type: object,
    known_types: Sequence[str],
) -> str | None:
    """Older-client view: unknown types are ignored (return None), never fatal."""
    if not isinstance(message_type, str):
        return None
    if message_type in frozenset(known_types):
        return message_type
    return None


def evaluate_deprecation_removal(
    declaration: FamilyFormatDeclaration,
    *,
    current_protocol_version: str,
    deprecation_minors: object = None,
) -> Result[FamilyFormatDeclaration]:
    """Require a deprecated family to remain served for the configured minor window.

    ``protocolVersion`` and family format declarations on the declaration leave
    old evidence readable after the family is marked deprecated.
    """
    if not declaration.leaves_old_evidence_readable():
        return _invalid(
            "family_format",
            "protocolVersion and family format declarations must leave old evidence readable",
            family=declaration.family_name,
        )

    if deprecation_minors is None:
        window = DEPRECATION_MINORS_DEFAULT
    elif (
        isinstance(deprecation_minors, int)
        and not isinstance(deprecation_minors, bool)
        and deprecation_minors >= 0
    ):
        window = deprecation_minors
    else:
        return _invalid(
            DEPRECATION_MINORS_REGISTRY_KEY,
            "deprecation_minors must be a non-negative integer",
            given=repr(deprecation_minors),
        )

    if declaration.deprecated_at_protocol_version is None:
        return _policy(
            "deprecation",
            "a family must be marked deprecated before removal is proposed",
            family=declaration.family_name,
            registry_key=DEPRECATION_MINORS_REGISTRY_KEY,
        )

    deprecated_at = parse_protocol_version(declaration.deprecated_at_protocol_version)
    if not isinstance(deprecated_at, Ok):
        return deprecated_at
    current = parse_protocol_version(current_protocol_version)
    if not isinstance(current, Ok):
        return current

    if not deprecated_at.value.same_major(current.value):
        return _policy(
            "protocolVersion",
            "deprecation window is measured in minors within the same major",
            deprecated_at=deprecated_at.value.raw,
            current=current.value.raw,
        )

    elapsed = current.value.minor_distance(deprecated_at.value)
    if elapsed < window:
        return _policy(
            "deprecation",
            "deprecated family must remain served for "
            f"{DEPRECATION_MINORS_REGISTRY_KEY} minors before removal",
            family=declaration.family_name,
            elapsed_minors=elapsed,
            required_minors=window,
            registry_key=DEPRECATION_MINORS_REGISTRY_KEY,
        )

    # Window satisfied: removal may proceed; format stamps stay for evidence.
    return Ok(
        FamilyFormatDeclaration(
            family_name=declaration.family_name,
            protocol_version=declaration.protocol_version,
            format_version=declaration.format_version,
            deprecated_at_protocol_version=declaration.deprecated_at_protocol_version,
            removed=True,
        )
    )
