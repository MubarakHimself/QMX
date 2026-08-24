"""Author-side types for Bot-domain registry artifacts (QL-3/QL-5).

QML returns fingerprintable content; a host composition root holds the
``WriterId`` and mints stamped CT-06 records (DEC-0171). Package SemVer never
enters identity (DEC-0180).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core.refusal import Ok, Result
from qmf.registry.records import CONTRACT_FORMAT_VERSION as REGISTRY_ENVELOPE_FORMAT_VERSION

from qml._refuse import invalid, unsupported
from qml.declaration.bot import (
    BOT_DEFINITION_KIND_FORMAT_VERSION,
    FORBIDDEN_BOT_FIELDS,
    KIND_BOT_DEFINITION,
    PERMITTED_EXIT_INTENT_VOCABULARY,
    BotDefinition,
    ConfluenceCite,
    bot_definition_kind_contract,
    install_bot_definition_kind,
    mint_bot_definition,
    promote_tuned_assignment,
    register_bot_definition,
)
from qml.declaration.confluence import (
    CONFLUENCE_KIND_FORMAT_VERSION,
    FORBIDDEN_CONDITION_FIELDS,
    KIND_CONFLUENCE,
    LEG_ROLES,
    Confluence,
    ConfluenceLeg,
    ConfluenceOrdering,
    LegRole,
    confluence_kind_contract,
    install_confluence_kind,
    mint_confluence,
    parse_leg_role,
    parse_ordering,
    register_confluence,
    resolve_confluence_at_layer1,
)
from qml.declaration.parameters import (
    CONSTRAINT_OPS,
    PARAMETER_TYPES,
    HardConstraintFilter,
    ParameterSpec,
    ParameterType,
    UiFlag,
    parse_parameter_type,
    parse_ui_flag,
)
from qml.declaration.versioning import (
    BotVersionGraph,
    CurrentPointer,
    branches_from_edge,
    continues_performance_edge,
)

__all__ = [
    "BOT_DEFINITION_KIND_FORMAT_VERSION",
    "CONFLUENCE_KIND_FORMAT_VERSION",
    "CONSTRAINT_OPS",
    "FORBIDDEN_BOT_FIELDS",
    "FORBIDDEN_CONDITION_FIELDS",
    "KIND_BOT_DEFINITION",
    "KIND_CONFLUENCE",
    "LEG_ROLES",
    "PARAMETER_TYPES",
    "PERMITTED_EXIT_INTENT_VOCABULARY",
    "REGISTRY_ENVELOPE_FORMAT_VERSION",
    "AuthoredArtifact",
    "AuthoredKind",
    "BotDefinition",
    "BotVersionGraph",
    "Confluence",
    "ConfluenceCite",
    "ConfluenceLeg",
    "ConfluenceOrdering",
    "CurrentPointer",
    "HardConstraintFilter",
    "LegRole",
    "ParameterSpec",
    "ParameterType",
    "UiFlag",
    "bot_definition_kind_contract",
    "branches_from_edge",
    "confluence_kind_contract",
    "continues_performance_edge",
    "install_bot_definition_kind",
    "install_confluence_kind",
    "mint_bot_definition",
    "mint_confluence",
    "parse_leg_role",
    "parse_ordering",
    "parse_parameter_type",
    "parse_ui_flag",
    "promote_tuned_assignment",
    "register_bot_definition",
    "register_confluence",
    "resolve_confluence_at_layer1",
]

_EMPTY_BODY: Final[Mapping[str, object]] = MappingProxyType({})


class AuthoredKind(StrEnum):
    """The Bot-domain kinds QML authors; qmf-registry owns the records (DEC-0173)."""

    BOT_DEFINITION = "bot-definition"
    CONFLUENCE = "confluence"


def _freeze_body(value: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True)
class AuthoredArtifact:
    """Fingerprintable Bot-domain content returned to a host, never a stamped record.

    Identity is ``kind`` + kind ``format_version`` + ``body``. The qml distribution
    SemVer is display-only and is not a field here (DEC-0180).
    """

    kind: AuthoredKind
    format_version: int
    body: Mapping[str, object] = _EMPTY_BODY

    def __post_init__(self) -> None:
        object.__setattr__(self, "body", _freeze_body(self.body))

    @classmethod
    def try_create(
        cls,
        kind: object,
        format_version: object,
        body: object = None,
    ) -> Result[AuthoredArtifact]:
        """Validate and build fingerprintable content, value-or-refusal."""
        resolved_kind: AuthoredKind | None
        if isinstance(kind, AuthoredKind):
            resolved_kind = kind
        elif isinstance(kind, str):
            try:
                resolved_kind = AuthoredKind(kind)
            except ValueError:
                resolved_kind = None
        else:
            resolved_kind = None
        if resolved_kind is None:
            return unsupported(
                "kind",
                "QML authors bot-definition and confluence; any other kind is unknown",
                given=repr(kind),
            )
        if isinstance(format_version, bool) or not isinstance(format_version, int):
            return invalid(
                "format_version",
                "a kind format version is a positive integer; package SemVer never enters",
                given=repr(format_version),
            )
        if format_version < 1:
            return invalid(
                "format_version",
                "a kind format version is a positive integer ordinal",
                given=repr(format_version),
            )
        if body is None:
            frozen_body: Mapping[str, object] = _EMPTY_BODY
        elif isinstance(body, Mapping):
            frozen_body = _freeze_body(cast("Mapping[str, object]", body))
        else:
            return invalid(
                "body",
                "authored content is a mapping of identity-bearing fields",
                given=repr(body),
            )
        return Ok(cls(kind=resolved_kind, format_version=format_version, body=frozen_body))

    def identity_payload(self) -> dict[str, object]:
        """Canonical semantic content for ``fp1``. SemVer is never included."""
        return {
            "kind": self.kind.value,
            "format_version": self.format_version,
            "body": dict(self.body),
        }
