"""Default-deny enumeration of qmf-registry / qmf-risk surfaces (FR-Q07; DEC-0347).

The daemon may reach only the surfaces listed here. Unlisted surfaces are not
callable; adding one is a spine amendment, not a local code change.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

__all__ = [
    "PARENT_SURFACE_LIBRARIES",
    "PERMITTED_PARENT_SURFACES",
    "PROHIBITED_RECORD_FAMILIES",
    "ParentLibrary",
    "ParentSurfaceError",
    "ParentSurfaceKind",
    "ProhibitedMutation",
    "ProhibitedRecordFamily",
    "assert_no_zone_transition",
    "assert_record_family_immutable",
    "is_parent_surface_permitted",
    "refuse_unlisted_parent_surface",
]


class ParentLibrary(StrEnum):
    """Parent libraries whose edges the daemon may declare (AD-2)."""

    QMF_REGISTRY = "qmf-registry"
    QMF_RISK = "qmf-risk"


class ParentSurfaceKind(StrEnum):
    """Categories of parent-library surface the daemon may reach."""

    VALUE_TYPE = "value_type"
    TYPED_REFUSAL = "typed_refusal"
    PURE_CALCULATION = "pure_calculation"
    DEV_ZONE_CANDIDATE_WRITE = "dev_zone_candidate_write"


class ProhibitedRecordFamily(StrEnum):
    """Record families QMA may never construct, write, amend, or delete."""

    BINDING = "binding"
    BOOK = "book"
    BMS = "bms"
    SEAT = "seat"
    CONTROL_ACTION = "control_action"
    EXIT = "exit"
    PROTECTION = "protection"
    PRIORITY_RANK = "priority_rank"
    PROMOTION = "promotion"


class ProhibitedMutation(StrEnum):
    """Mutation verbs refused against every prohibited record family."""

    CONSTRUCT = "construct"
    WRITE = "write"
    AMEND = "amend"
    DELETE = "delete"


PARENT_SURFACE_LIBRARIES: Final[frozenset[ParentLibrary]] = frozenset(ParentLibrary)

# Default-deny allowlist. qmf-risk has no write surface; the single write is the
# content-addressed dev-zone candidate artifact through qmf-registry (AD-14).
PERMITTED_PARENT_SURFACES: Final[frozenset[tuple[ParentLibrary, ParentSurfaceKind]]] = frozenset(
    {
        (ParentLibrary.QMF_REGISTRY, ParentSurfaceKind.VALUE_TYPE),
        (ParentLibrary.QMF_REGISTRY, ParentSurfaceKind.TYPED_REFUSAL),
        (ParentLibrary.QMF_REGISTRY, ParentSurfaceKind.PURE_CALCULATION),
        (ParentLibrary.QMF_REGISTRY, ParentSurfaceKind.DEV_ZONE_CANDIDATE_WRITE),
        (ParentLibrary.QMF_RISK, ParentSurfaceKind.VALUE_TYPE),
        (ParentLibrary.QMF_RISK, ParentSurfaceKind.TYPED_REFUSAL),
        (ParentLibrary.QMF_RISK, ParentSurfaceKind.PURE_CALCULATION),
    }
)

PROHIBITED_RECORD_FAMILIES: Final[frozenset[ProhibitedRecordFamily]] = frozenset(
    ProhibitedRecordFamily
)


class ParentSurfaceError(ValueError):
    """Raised when a caller asks for an unlisted or prohibited parent surface."""


def _resolve_library(library: ParentLibrary | str) -> ParentLibrary:
    if isinstance(library, ParentLibrary):
        return library
    try:
        return ParentLibrary(library)
    except ValueError as exc:
        raise ParentSurfaceError(f"{library!r} is not a declared parent library") from exc


def _resolve_kind(kind: ParentSurfaceKind | str) -> ParentSurfaceKind:
    if isinstance(kind, ParentSurfaceKind):
        return kind
    try:
        return ParentSurfaceKind(kind)
    except ValueError as exc:
        raise ParentSurfaceError(f"{kind!r} is not a parent surface kind") from exc


def is_parent_surface_permitted(
    library: ParentLibrary | str,
    kind: ParentSurfaceKind | str,
) -> bool:
    """True only when ``(library, kind)`` is on the default-deny allowlist."""
    try:
        resolved = (_resolve_library(library), _resolve_kind(kind))
    except ParentSurfaceError:
        return False
    return resolved in PERMITTED_PARENT_SURFACES


def refuse_unlisted_parent_surface(
    library: ParentLibrary | str,
    kind: ParentSurfaceKind | str,
) -> None:
    """Refuse any parent surface not on the enumerated allowlist."""
    resolved_library = _resolve_library(library)
    resolved_kind = _resolve_kind(kind)
    if (resolved_library, resolved_kind) not in PERMITTED_PARENT_SURFACES:
        raise ParentSurfaceError(
            f"parent surface {resolved_library.value!r}/{resolved_kind.value!r} "
            "is default-deny (not enumerated in qma-core; DEC-0347)"
        )


def assert_record_family_immutable(
    family: ProhibitedRecordFamily | str,
    mutation: ProhibitedMutation | str = ProhibitedMutation.WRITE,
) -> None:
    """Refuse construct/write/amend/delete of every prohibited record family."""
    try:
        resolved_family = (
            family if isinstance(family, ProhibitedRecordFamily) else ProhibitedRecordFamily(family)
        )
    except ValueError as exc:
        raise ParentSurfaceError(f"{family!r} is not a prohibited record family") from exc
    try:
        resolved_mutation = (
            mutation if isinstance(mutation, ProhibitedMutation) else ProhibitedMutation(mutation)
        )
    except ValueError as exc:
        raise ParentSurfaceError(f"{mutation!r} is not a prohibited mutation") from exc
    if resolved_family not in PROHIBITED_RECORD_FAMILIES:
        raise ParentSurfaceError(
            f"record family {resolved_family.value!r} is not on the prohibited set"
        )
    raise ParentSurfaceError(
        f"QMA cannot {resolved_mutation.value} {resolved_family.value!r} records "
        "(FR-Q07; DEC-0301; DEC-0347)"
    )


def assert_no_zone_transition() -> None:
    """Refuse every zone-transition surface call."""
    raise ParentSurfaceError(
        "QMA cannot call any zone-transition surface (FR-Q07; DEC-0301; DEC-0347)"
    )
