"""Read-and-calculate parent-surface write gate (FR-Q42; AD-2; DEC-0347).

QMA may write only a content-addressed candidate artifact in the existing
``dev`` zone through ``qmf-registry``. Binding, Book, BMS, seat, control-action,
exit, protection, priority, and promotion records are refused, as is every zone
transition. This module mints no promotion command and no money-path value.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qma.core.barriers.parent_surfaces import (
    SOLE_PERMITTED_PARENT_WRITE,
    ParentLibrary,
    ParentSurfaceError,
    ParentSurfaceKind,
    ProhibitedMutation,
    ProhibitedRecordFamily,
    is_parent_surface_permitted,
    refuse_parent_money_path_write,
    refuse_unlisted_parent_surface,
    refuse_zone_transition_surface,
)
from qma.core.content import content_address
from qmf.core import Instant, Ok, Result, WriterId, is_refusal
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal
from qmf.data.store.refusals import policy_rejection
from qmf.registry import FieldSetKind, KindRegistry, Registrar

__all__ = [
    "CANDIDATE_KIND",
    "DEV_ZONE",
    "MONEY_PATH_VALUE_FIELDS",
    "DevZoneCandidate",
    "ParentSurfaceGate",
]

DEV_ZONE: Final[str] = "dev"
CANDIDATE_KIND: Final[str] = "qma-dev-zone-candidate"

# Field names that would mint a money-path value. This story mints none.
MONEY_PATH_VALUE_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "binding",
        "book",
        "bms",
        "seat",
        "control_action",
        "exit",
        "protection",
        "priority_rank",
        "promotion",
        "sizing",
        "size",
        "capital_floor",
        "kill_switch",
        "order",
        "position",
        "mode",
        "priority",
        "zone_transition",
    }
)

_CANDIDATE_REQUIRED: Final[tuple[str, ...]] = ("origin", "zone", "payload_fp1")
_CANDIDATE_OPTIONAL: Final[tuple[str, ...]] = ("lineage_predecessor", "summary")


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


@dataclass(frozen=True, slots=True)
class DevZoneCandidate:
    """Content-addressed candidate artifact in the existing ``dev`` zone."""

    origin: str
    zone: str
    payload_fp1: str
    stable_id: str
    lineage_predecessor: str | None = None
    summary: str | None = None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "origin": self.origin,
            "zone": self.zone,
            "payload_fp1": self.payload_fp1,
            "stable_id": self.stable_id,
        }
        if self.lineage_predecessor is not None:
            payload["lineage_predecessor"] = self.lineage_predecessor
        if self.summary is not None:
            payload["summary"] = self.summary
        return MappingProxyType(payload)


def _candidate_kind() -> Result[FieldSetKind]:
    return FieldSetKind.try_create(
        CANDIDATE_KIND,
        1,
        required_fields=list(_CANDIDATE_REQUIRED),
        optional_fields=list(_CANDIDATE_OPTIONAL),
    )


class ParentSurfaceGate:
    """Daemon gate over the default-deny qmf-registry / qmf-risk surface."""

    def __init__(self) -> None:
        kinds = KindRegistry()
        kind = _candidate_kind()
        if is_refusal(kind):
            msg = "qma-dev-zone-candidate kind contract must construct"
            raise RuntimeError(msg)
        registered = kinds.register(kind.value)
        if is_refusal(registered):
            msg = "qma-dev-zone-candidate kind must register"
            raise RuntimeError(msg)
        self._registrar = Registrar(kinds)
        self._sequence = 0
        writer = WriterId.try_create("qma-daemon", "authoring", "dev-zone-candidate", "boot-1")
        if is_refusal(writer):
            msg = "dev-zone candidate writer id must construct"
            raise RuntimeError(msg)
        self._writer = writer.value

    @property
    def permitted_write(self) -> tuple[str, str]:
        library, kind = SOLE_PERMITTED_PARENT_WRITE
        return (library.value, kind.value)

    @property
    def minted_promotion_command(self) -> None:
        """QMA mints no promotion command (FR-Q42; AD-18; AD-25)."""
        return None

    def attempt_write(
        self,
        *,
        family: ProhibitedRecordFamily | str,
        mutation: ProhibitedMutation | str = ProhibitedMutation.WRITE,
        library: ParentLibrary | str = ParentLibrary.QMF_REGISTRY,
    ) -> TypedRefusal:
        """Refuse a money-path record write through a permitted dependency surface."""
        _ = library
        return refuse_parent_money_path_write(family, mutation)

    def attempt_zone_transition(self) -> TypedRefusal:
        """Refuse every zone-transition surface call."""
        return refuse_zone_transition_surface()

    def attempt_parent_surface(
        self,
        library: ParentLibrary | str,
        kind: ParentSurfaceKind | str,
    ) -> Result[tuple[str, str]]:
        """Admit only enumerated parent surfaces; zone-transition is uncallable."""
        library_token = library.value if isinstance(library, ParentLibrary) else str(library)
        kind_token = kind.value if isinstance(kind, ParentSurfaceKind) else str(kind)
        if kind_token in {"zone_transition", "promotion"}:
            return refuse_zone_transition_surface()
        if is_parent_surface_permitted(library, kind):
            return Ok((library_token, kind_token))
        try:
            refuse_unlisted_parent_surface(library, kind)
        except ParentSurfaceError as exc:
            return policy_rejection(
                "parent_surface",
                str(exc),
                library=library_token,
                kind=kind_token,
            )
        return policy_rejection(
            "parent_surface",
            "parent surface is default-deny (DEC-0347)",
            library=library_token,
            kind=kind_token,
        )

    def write_dev_zone_candidate(
        self,
        payload: Mapping[str, object],
        *,
        origin: str = "qma",
        summary: str | None = None,
        lineage_predecessor: str | None = None,
        zone: str = DEV_ZONE,
    ) -> Result[DevZoneCandidate]:
        """Write the sole permitted parent-library artifact: a ``dev``-zone candidate."""
        admitted = self.attempt_parent_surface(
            ParentLibrary.QMF_REGISTRY,
            ParentSurfaceKind.DEV_ZONE_CANDIDATE_WRITE,
        )
        if is_refusal(admitted):
            return admitted
        if zone != DEV_ZONE:
            return refuse_zone_transition_surface()
        forbidden = sorted(key for key in payload if key in MONEY_PATH_VALUE_FIELDS)
        if forbidden:
            return _policy(
                "payload",
                ("dev-zone candidate may not mint a money-path value (FR-Q42; AD-2; DEC-0347)"),
                fields=forbidden,
            )
        addressed = content_address(dict(payload))
        if is_refusal(addressed):
            return addressed
        body: dict[str, object] = {
            "origin": origin,
            "zone": DEV_ZONE,
            "payload_fp1": addressed.value.value,
        }
        if summary is not None:
            body["summary"] = summary
        if lineage_predecessor is not None:
            body["lineage_predecessor"] = lineage_predecessor
        created = Instant.try_create((self._sequence + 1) * 1_000_000)
        if is_refusal(created):
            return created
        receipt = self._registrar.register(
            kind=CANDIDATE_KIND,
            body=body,
            writer=self._writer,
            sequence=self._sequence,
            created_at=created.value,
        )
        if is_refusal(receipt):
            return receipt
        self._sequence += 1
        stored = receipt.value.record
        return Ok(
            DevZoneCandidate(
                origin=origin,
                zone=DEV_ZONE,
                payload_fp1=addressed.value.value,
                stable_id=stored.stable_id.value,
                lineage_predecessor=lineage_predecessor,
                summary=summary,
            )
        )
