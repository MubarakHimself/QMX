"""Story 11.7 — CT-22 format-2 ``footprint_requirements`` requirement-set shape.

Format 1 reserved ``footprint_requirements`` as ``pending(GAP-0047)``. Format 2
**fills that reserved pending slot** with a SET of typed requirements over CT-33
footprint fields, under ``admission_bar``'s grammar discipline: requirement kind +
comparison + a ruled exact-rational value or an explicit ``not-yet-ruled`` tag
(DEC-0174, DEC-0181). Values live in Book templates only, never in this contract
module. A requirement left ``not-yet-ruled`` (GAP-0048/GAP-0049) still passes
registration and blocks live binding — the prediction linter is definable, but
blank still blocks live money (DEC-0144, DEC-0146, DEC-0178).

qmf-risk never imports ``qml``: CT-33 footprint fields are opaque tokens plus a
closed, addable field-kind vocabulary. Imports only ``qmf-core`` and sibling
``qmf.risk`` modules (L30/DEC-0120).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import AccountRole, ExactRational, UnitKind
from qmf.core import (
    Ok as _Ok,
)
from qmf.core import (
    Result as _Result,
)
from qmf.core import (
    TypedRefusal as _TypedRefusal,
)
from qmf.risk._common import clean_str, coerce_enum, invalid, policy, type_name, unsupported
from qmf.risk.admission_bar import (
    Band,
    Comparison,
    PendingSlot,
    RuledThreshold,
    Threshold,
)
from qmf.risk.grammar import NotYetRuled
from qmf.risk.migrations import THRESHOLD_GAPS_BEHIND_NEW_ADMISSION_BAR_FIELDS

__all__ = [
    "FOOTPRINT_REQUIREMENTS_CONTRACT_FORMAT_VERSION",
    "FORMAT_1_FOOTPRINT_REQUIREMENTS_PENDING",
    "FootprintFieldKind",
    "FootprintRequirement",
    "FootprintRequirements",
    "check_footprint_requirements_live_binding",
]

FOOTPRINT_REQUIREMENTS_CONTRACT_FORMAT_VERSION: Final[int] = 2

# Format 1 carried this pending slot; format 2 fills it. The marker remains so a
# format-1 Book is still describable as holding the reserved pending surface.
FORMAT_1_FOOTPRINT_REQUIREMENTS_PENDING_REF: Final[str] = "GAP-0047"
FORMAT_1_FOOTPRINT_REQUIREMENTS_PENDING: Final[PendingSlot] = PendingSlot(
    ref=FORMAT_1_FOOTPRINT_REQUIREMENTS_PENDING_REF
)


class FootprintFieldKind(StrEnum):
    """CT-33 footprint fields a Book may constrain — closed, addable never redefined.

    The three members are the footprint's consumption-manifest loci (DEC-0174): the
    nested stream set, required calendars, and producer bindings. Values that fill
    a requirement live in the Book template, never here.
    """

    STREAM_SET = "stream_set"
    CALENDARS = "calendars"
    PRODUCER_BINDINGS = "producer_bindings"


@dataclass(frozen=True, slots=True)
class FootprintRequirement:
    """One typed requirement over a CT-33 footprint field (DEC-0174, DEC-0181).

    Carries the closed ``field_kind``, an opaque ``field_identity``, a mandatory
    ``unit``, a ``comparison`` (the admission-bar three-member set), a ``threshold``
    discriminated union (ruled | not-yet-ruled, key always present), and a separate
    ``display_ordinal``.
    """

    field_kind: FootprintFieldKind
    field_identity: str
    unit: UnitKind
    comparison: Comparison
    threshold: Threshold
    display_ordinal: int

    @classmethod
    def try_create(
        cls,
        field_kind: object,
        field_identity: object,
        unit: object,
        comparison: object,
        threshold: object,
        display_ordinal: object,
    ) -> _Result[FootprintRequirement]:
        """Validate and build a :class:`FootprintRequirement`, value-or-refusal."""
        resolved_kind = coerce_enum(FootprintFieldKind, field_kind)
        if resolved_kind is None:
            return invalid(
                "field_kind",
                "a footprint requirement names a CT-33 footprint field kind "
                "(stream_set | calendars | producer_bindings)",
                given=repr(field_kind),
                allowed=[member.value for member in FootprintFieldKind],
            )
        token = clean_str(field_identity)
        if token is None:
            return invalid(
                "field_identity",
                "a footprint requirement declares a non-empty opaque CT-33 field identity",
                given=repr(field_identity),
            )
        resolved_unit = coerce_enum(UnitKind, unit)
        if resolved_unit is None:
            return invalid(
                "unit",
                "a footprint requirement is missing its mandatory unit, or names one outside "
                "the closed AD-40 vocabulary",
                given=repr(unit),
                allowed=[member.value for member in UnitKind],
            )
        resolved_comparison = coerce_enum(Comparison, comparison)
        if resolved_comparison is None:
            return invalid(
                "comparison",
                "a footprint requirement's comparison is exactly at-least | at-most | "
                "within-band under admission_bar grammar discipline",
                given=repr(comparison),
                allowed=[member.value for member in Comparison],
            )
        threshold_refusal = _validate_threshold(resolved_comparison, resolved_unit, threshold)
        if threshold_refusal is not None:
            return threshold_refusal
        if isinstance(display_ordinal, bool) or not isinstance(display_ordinal, int):
            return invalid(
                "display_ordinal",
                "a display ordinal is an integer (separate from the canonical order)",
                given=repr(display_ordinal),
            )
        if display_ordinal < 0:
            return invalid(
                "display_ordinal", "a display ordinal is non-negative", given=repr(display_ordinal)
            )
        return _Ok(
            cls(
                field_kind=resolved_kind,
                field_identity=token,
                unit=resolved_unit,
                comparison=resolved_comparison,
                threshold=cast("Threshold", threshold),
                display_ordinal=display_ordinal,
            )
        )

    @property
    def is_blank(self) -> bool:
        """True when the threshold is an explicit :class:`~qmf.risk.grammar.NotYetRuled`."""
        return isinstance(self.threshold, NotYetRuled)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this requirement."""
        return {
            "class": "footprint-requirement",
            "field_kind": self.field_kind.value,
            "field_identity": self.field_identity,
            "unit": self.unit.value,
            "comparison": self.comparison.value,
            "threshold": self.threshold.fp1_identity(),
            "display_ordinal": self.display_ordinal,
            "format_version": FOOTPRINT_REQUIREMENTS_CONTRACT_FORMAT_VERSION,
        }


def _validate_threshold(
    comparison: Comparison, unit: UnitKind, threshold: object
) -> _TypedRefusal | None:
    """Admission-bar threshold grammar: discriminant always present; shape matches comparison."""
    if threshold is None:
        return invalid(
            "threshold",
            "a threshold's discriminant key is always present; blankness is an explicit "
            "NotYetRuled marker, never a null (AD-10)",
        )
    if isinstance(threshold, NotYetRuled):
        return None
    if not isinstance(threshold, RuledThreshold):
        return invalid(
            "threshold",
            "a threshold is a RuledThreshold or a NotYetRuled blank",
            given=repr(threshold),
        )
    bound = threshold.bound
    if comparison is Comparison.WITHIN_BAND:
        if not isinstance(bound, Band):
            return invalid(
                "threshold",
                "a within-band comparison's ruled threshold is a Band (two bounds)",
                given=repr(bound),
            )
    elif not isinstance(bound, ExactRational):
        return invalid(
            "threshold",
            "an at-least/at-most comparison's ruled threshold is a scalar ExactRational",
            given=repr(bound),
        )
    if bound.unit_kind is not unit:
        return invalid(
            "threshold",
            "a ruled threshold's unit-kind must equal the requirement's declared unit",
            declared=unit.value,
            threshold_unit=bound.unit_kind.value,
        )
    return None


@dataclass(frozen=True, slots=True)
class FootprintRequirements:
    """The format-2 footprint_requirements set — fills the reserved pending slot (DEC-0181).

    Canonically ordered by ``field_identity``. An empty set is legal (the Book
    constrains nothing). Any ``not-yet-ruled`` member is a declared blank: the
    container registers, and live binding is a ``policy rejection``.
    """

    requirements: tuple[FootprintRequirement, ...]
    contract_format_version: int = FOOTPRINT_REQUIREMENTS_CONTRACT_FORMAT_VERSION

    @classmethod
    def try_create(
        cls,
        requirements: object,
        *,
        contract_format_version: object = FOOTPRINT_REQUIREMENTS_CONTRACT_FORMAT_VERSION,
    ) -> _Result[FootprintRequirements]:
        """Validate and build :class:`FootprintRequirements` — format 2 only.

        Format 1 does not have this shape (it holds
        :data:`FORMAT_1_FOOTPRINT_REQUIREMENTS_PENDING`). A format-1
        ``contract_format_version`` is ``unsupported capability``.
        """
        if (
            isinstance(contract_format_version, bool)
            or not isinstance(contract_format_version, int)
            or contract_format_version != FOOTPRINT_REQUIREMENTS_CONTRACT_FORMAT_VERSION
        ):
            return unsupported(
                "contract_format_version",
                "footprint_requirements' requirement-set shape exists only at CT-22 "
                "contract format version 2; format 1 carries the reserved pending(GAP-0047) "
                "slot instead",
                given=repr(contract_format_version),
                understood=FOOTPRINT_REQUIREMENTS_CONTRACT_FORMAT_VERSION,
            )
        resolved = _coerce_requirements(requirements)
        if isinstance(resolved, _TypedRefusal):
            return resolved
        return _Ok(cls(requirements=resolved, contract_format_version=contract_format_version))

    @property
    def is_blank(self) -> bool:
        """True when any requirement's threshold is not-yet-ruled (blocks live money)."""
        return any(req.is_blank for req in self.requirements)

    def by_identity(self) -> Mapping[str, FootprintRequirement]:
        """Requirements keyed by ``field_identity`` (a read-only view)."""
        return MappingProxyType({req.field_identity: req for req in self.requirements})

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity — requirements in canonical order."""
        return {
            "class": "footprint-requirements",
            "contract_format_version": self.contract_format_version,
            "requirements": [req.fp1_identity() for req in self.requirements],
        }


def _coerce_requirements(value: object) -> tuple[FootprintRequirement, ...] | _TypedRefusal:
    """Resolve a collection of unique-identity footprint requirements in canonical order."""
    given = type_name(value)
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        return invalid(
            "requirements",
            "footprint_requirements is a collection of FootprintRequirement values",
            given=given,
        )
    seen: set[str] = set()
    items: list[FootprintRequirement] = []
    for item in cast("Iterable[object]", value):
        if not isinstance(item, FootprintRequirement):
            return invalid(
                "requirements",
                "each footprint requirement is a FootprintRequirement",
                given=repr(item),
            )
        if item.field_identity in seen:
            return invalid(
                "requirements",
                "footprint_requirements is a set — a field_identity appears at most once",
                field_identity=item.field_identity,
            )
        seen.add(item.field_identity)
        items.append(item)
    items.sort(key=lambda req: req.field_identity)
    return tuple(items)


def check_footprint_requirements_live_binding(
    requirements: object, target_role: object
) -> _Result[None]:
    """Blank footprint_requirements block live money (DEC-0144, DEC-0146, DEC-0181).

    A not-yet-ruled requirement (thresholds stay GAP-0048/GAP-0049) registers and
    binds non-live freely; binding to ``role = live`` is a ``policy rejection``.
    Format 1's pending(GAP-0047) slot is also a declared blank that blocks live.
    """
    resolved_role = coerce_enum(AccountRole, target_role)
    if resolved_role is None:
        return invalid(
            "target_role",
            "the target binding account role names a member of the account-role set",
            given=repr(target_role),
            allowed=[member.value for member in AccountRole],
        )
    is_blank = False
    if isinstance(requirements, FootprintRequirements):
        is_blank = requirements.is_blank
    elif isinstance(requirements, PendingSlot):
        is_blank = True
    else:
        return invalid(
            "requirements",
            "the live-binding check reads FootprintRequirements or the format-1 pending slot",
            given=repr(requirements),
        )
    if resolved_role is AccountRole.LIVE and is_blank:
        return policy(
            "footprint_requirements",
            "blank blocks live money: a not-yet-ruled footprint_requirements threshold "
            f"({', '.join(THRESHOLD_GAPS_BEHIND_NEW_ADMISSION_BAR_FIELDS)}) or the "
            "format-1 pending(GAP-0047) slot registers and binds non-live freely, but "
            "binding to a live account is refused",
        )
    return _Ok(None)
