"""Story 10.3 — the admission bar and blank-blocks-live money (COMP-QMF-RISK).

"The Book sets the bar." The ``admission_bar`` is a **set of named pass/fail
requirements**, never a composite score — each requirement passes or fails **on
its own terms** (AD-32; DEC-0146). This module defines that requirement grammar on
``qmf-core`` nouns:

* an opaque ``measure_identity`` (an AD-9 identity token — never parsed);
* a **mandatory unit** from the closed ``qmf-core`` :class:`~qmf.core.UnitKind`
  vocabulary;
* a ``comparison`` — exactly ``at-least | at-most | within-band`` (:class:`Comparison`);
* a **threshold as a discriminated union** — :class:`RuledThreshold` (an exact
  rational, or a :class:`Band` for ``within-band``) **or**
  :class:`~qmf.risk.grammar.NotYetRuled` (a blank carrying its gap reference) — with
  the **discriminant key always present**, so blankness is a declared value and never
  a key-presence test (AD-10 forbids nulls);
* ``evidence_requirements`` (:class:`EvidenceRequirements`) — the declared world,
  account role, minimum evidence window, required producer contract format versions,
  and the two format-2 bot-side evidence fields;
* and, for a **float-valued measure**, a :class:`ComparisonRule` declared in the
  requirement itself (target scale, rounding mode, tie disposition) that crosses the
  named analytic→exact boundary; **an undeclared comparison is ``invalid input``**
  (AC6; DEC-0146).

**No composite score, rating, tier band, or weighted aggregate may express a bar**
(AC2). The structure carries no weight and no aggregate; :func:`evaluate_bar`
returns a **per-requirement** verdict mapping, never one score; and
:func:`reject_bar_aggregate` makes the prohibition first-class — any attempt to
express a bar as a composite is a typed refusal.

**Blank blocks live money** (AC3; L38, DEC-0146): a bar holding any ``not-yet-ruled``
threshold or ``pending`` slot registers and binds to **non-live** roles freely, and
:func:`check_live_binding_admissible` makes binding to a ``role = live`` account a
``policy rejection``. **No paper role gates live money** (AC4):
:func:`check_no_paper_role_gates_live` refuses (``policy rejection``) any requirement
whose ``evidence_requirements.account_role`` names a paper role in a bar that gates a
live binding, so this field can never rebuild the paper-performance gate admission
exists to forbid.

Imports only ``qmf-core`` and sibling ``qmf.risk`` modules; nothing imports
``qmf.risk`` (default-deny, L30/DEC-0120). Ratified ``defined-unwired`` surface — no
wiring is authorized here (DEC-0158).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import (
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    ROUND_UP,
    Decimal,
)
from enum import StrEnum
from fractions import Fraction
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    AccountRole,
    Duration,
    ExactRational,
    Money,
    Price,
    PriceDelta,
    Quantity,
    RoundingMode,
    UnitKind,
    ValueFactor,
    World,
)
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
from qmf.risk.grammar import NotYetRuled

__all__ = [
    "PAPER_ACCOUNT_ROLES",
    "AdmissionBar",
    "AdmissionRequirement",
    "Band",
    "Comparison",
    "ComparisonRule",
    "EvidenceRequirements",
    "PendingSlot",
    "RequirementVerdict",
    "RuledThreshold",
    "Threshold",
    "TieDisposition",
    "bar_is_blank",
    "check_live_binding_admissible",
    "check_no_paper_role_gates_live",
    "evaluate_bar",
    "evaluate_requirement",
    "is_paper_role",
    "reject_bar_aggregate",
]

# This module's own contract format version stamped into fp1 identity content; its
# meaning never mutates — an incompatible change mints the next version (L15).
_ADMISSION_BAR_FORMAT_VERSION = 1

# CT-22 contract format versions this evidence surface understands (Story 11.7).
_EVIDENCE_FORMAT_1: Final[int] = 1
_EVIDENCE_FORMAT_2: Final[int] = 2
_EVIDENCE_KNOWN_FORMAT_VERSIONS: Final[frozenset[int]] = frozenset(
    {_EVIDENCE_FORMAT_1, _EVIDENCE_FORMAT_2}
)

# The documented maximum target scale a float->exact comparison crossing accepts,
# mirroring the money-path MAX_SCALE (CT-01; DEC-0105) so ``10**scale`` stays a cheap
# integer rather than a caller-supplied denial-of-service foot-gun.
_MAX_SCALE: Final[int] = 72

# The paper account roles, from the closed CT-03 AccountRole vocabulary (DEC-0107).
# A paper role may never gate live money (AC4; DEC-0146, DEC-0149).
PAPER_ACCOUNT_ROLES: Final[frozenset[AccountRole]] = frozenset(
    {AccountRole.PAPER_VALIDATION, AccountRole.PAPER_BENCHED}
)

_ROUNDING: Final[Mapping[RoundingMode, str]] = MappingProxyType(
    {
        RoundingMode.HALF_UP: ROUND_HALF_UP,
        RoundingMode.HALF_EVEN: ROUND_HALF_EVEN,
        RoundingMode.DOWN: ROUND_DOWN,
        RoundingMode.UP: ROUND_UP,
        RoundingMode.FLOOR: ROUND_FLOOR,
        RoundingMode.CEILING: ROUND_CEILING,
    }
)


class Comparison(StrEnum):
    """The admission-bar comparison set — exactly three members (AD-32; DEC-0146).

    A requirement is a pass/fail test, never a score: it compares one measure to one
    threshold under one of these comparisons. The set is deliberately closed — there
    is no ``weighted``, ``composite``, or ``aggregate`` comparison, because no
    composite score may express a bar.
    """

    AT_LEAST = "at-least"
    AT_MOST = "at-most"
    WITHIN_BAND = "within-band"


class TieDisposition(StrEnum):
    """How a measure landing exactly on a threshold is disposed (AC6; DEC-0146).

    A Sharpe sitting exactly on a threshold decides live money, so the tie is
    contract surface, not implementer choice. ``PASS_ON_TIE`` treats the boundary as
    inclusive (``at-least`` includes the threshold), ``FAIL_ON_TIE`` treats it as
    strict.
    """

    PASS_ON_TIE = "pass-on-tie"  # noqa: S105 (a tie disposition, not a secret)
    FAIL_ON_TIE = "fail-on-tie"


class RequirementVerdict(StrEnum):
    """A single requirement's verdict — evaluated on its own terms (AC2; DEC-0146).

    ``PASS`` / ``FAIL`` are the ruled outcomes; ``NOT_YET_RULED`` is the verdict of a
    blank requirement (its threshold is a :class:`~qmf.risk.grammar.NotYetRuled`), which
    is never a pass and blocks live money by the blank-blocks-live rule.
    """

    PASS = "pass"  # noqa: S105 (a verdict, not a secret)
    FAIL = "fail"
    NOT_YET_RULED = "not-yet-ruled"


def is_paper_role(role: object) -> bool:
    """True when ``role`` names a paper account role (AC4; DEC-0107, DEC-0146)."""
    resolved = coerce_enum(AccountRole, role)
    return resolved in PAPER_ACCOUNT_ROLES


@dataclass(frozen=True, slots=True)
class Band:
    """A ``within-band`` threshold's two exact bounds (AD-32; DEC-0146).

    Carries a ``lower`` and an ``upper`` :class:`~qmf.core.ExactRational` of the same
    unit-kind with ``lower < upper``; a measure is within-band when it lies between
    them (edge disposition governed by the requirement's :class:`TieDisposition`).
    """

    lower: ExactRational
    upper: ExactRational

    @classmethod
    def try_create(cls, lower: object, upper: object) -> _Result[Band]:
        """Validate and build a :class:`Band`, returning value-or-refusal.

        Both bounds are ``r-multiple``/exact rationals sharing one unit-kind, with
        ``lower`` strictly below ``upper`` (a zero-width or inverted band is not a
        band). No binary float anywhere.
        """
        if not isinstance(lower, ExactRational):
            return invalid("lower", "a band's lower bound is an ExactRational", given=repr(lower))
        if not isinstance(upper, ExactRational):
            return invalid("upper", "a band's upper bound is an ExactRational", given=repr(upper))
        if lower.unit_kind is not upper.unit_kind:
            return invalid(
                "band",
                "a band's bounds share one unit-kind",
                lower=lower.unit_kind.value,
                upper=upper.unit_kind.value,
            )
        if lower.as_fraction() >= upper.as_fraction():
            return invalid(
                "band",
                "a band's lower bound is strictly below its upper bound",
                lower=str(lower.as_fraction()),
                upper=str(upper.as_fraction()),
            )
        return _Ok(cls(lower=lower, upper=upper))

    @property
    def unit_kind(self) -> UnitKind:
        """The shared unit-kind of the band's two bounds."""
        return self.lower.unit_kind

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this band."""
        return {
            "class": "band",
            "lower": self.lower.fp1_identity(),
            "upper": self.upper.fp1_identity(),
            "format_version": _ADMISSION_BAR_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class RuledThreshold:
    """A ruled admission threshold — the ``ruled(exact-rational)`` union arm (DEC-0146).

    Carries a ``bound`` that is an exact-rational scalar (for ``at-least`` / ``at-most``)
    or a :class:`Band` (for ``within-band``). The other union arm is
    :class:`~qmf.risk.grammar.NotYetRuled`; the discriminant is the Python type, always
    present, so blankness is a declared value never a key-presence test.
    """

    bound: ExactRational | Band

    @classmethod
    def try_create(cls, bound: object) -> _Result[RuledThreshold]:
        """Validate and build a :class:`RuledThreshold`, value-or-refusal.

        The bound is an exact-rational scalar or a :class:`Band`; a binary float, a
        bare int, or a :class:`~qmf.risk.grammar.NotYetRuled` (that is the *other* arm,
        not a ruled bound) is ``invalid input``.
        """
        if isinstance(bound, (ExactRational, Band)):
            return _Ok(cls(bound=bound))
        return invalid(
            "bound",
            "a ruled threshold is an exact-rational scalar or a Band; a blank is the "
            "not-yet-ruled arm, and a binary float is refused",
            given=repr(bound),
        )

    @property
    def unit_kind(self) -> UnitKind:
        """The unit-kind of the ruled bound (scalar or band)."""
        return self.bound.unit_kind

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this ruled threshold."""
        return {
            "class": "ruled-threshold",
            "bound": self.bound.fp1_identity(),
            "format_version": _ADMISSION_BAR_FORMAT_VERSION,
        }


# The threshold discriminated union: a ruled bound or an explicit not-yet-ruled blank
# carrying its gap reference — the key (Python type) always present (DEC-0146).
Threshold = RuledThreshold | NotYetRuled


@dataclass(frozen=True, slots=True)
class ComparisonRule:
    """The declared analytic→exact comparison rule for a float measure (AC6; DEC-0146).

    A float-valued measure (a Sharpe, a drawdown) compared to an exact-rational
    threshold crosses AD-22's named analytic→exact boundary under this rule, declared
    in the requirement itself and identity-bearing: a ``target_scale`` (decimal
    places), a :class:`~qmf.core.RoundingMode`, and a :class:`TieDisposition`. An
    **undeclared comparison is ``invalid input``** — the crossing is contract surface.
    """

    target_scale: int
    rounding_mode: RoundingMode
    tie_disposition: TieDisposition

    @classmethod
    def try_create(
        cls, target_scale: object, rounding_mode: object, tie_disposition: object
    ) -> _Result[ComparisonRule]:
        """Validate and build a :class:`ComparisonRule`, value-or-refusal.

        The target scale is an integer count of decimal places in ``[0, MAX_SCALE]``;
        the rounding mode and tie disposition each name a member of their set. A bool
        (an int subclass) is not a scale.
        """
        if isinstance(target_scale, bool) or not isinstance(target_scale, int):
            return invalid(
                "target_scale",
                "a comparison rule's target scale is an integer count of decimal places",
                given=repr(target_scale),
            )
        if target_scale < 0 or target_scale > _MAX_SCALE:
            return invalid(
                "target_scale",
                f"a comparison target scale is an integer in [0, {_MAX_SCALE}]",
                given=repr(target_scale),
                max_scale=_MAX_SCALE,
            )
        resolved_rounding = coerce_enum(RoundingMode, rounding_mode)
        if resolved_rounding is None:
            return invalid(
                "rounding_mode",
                "a comparison rule declares a rounding mode",
                given=repr(rounding_mode),
                allowed=[member.value for member in RoundingMode],
            )
        resolved_tie = coerce_enum(TieDisposition, tie_disposition)
        if resolved_tie is None:
            return invalid(
                "tie_disposition",
                "a comparison rule declares a tie disposition",
                given=repr(tie_disposition),
                allowed=[member.value for member in TieDisposition],
            )
        return _Ok(
            cls(
                target_scale=target_scale,
                rounding_mode=resolved_rounding,
                tie_disposition=resolved_tie,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this comparison rule."""
        return {
            "class": "comparison-rule",
            "target_scale": self.target_scale,
            "rounding_mode": self.rounding_mode.value,
            "tie_disposition": self.tie_disposition.value,
            "format_version": _ADMISSION_BAR_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class EvidenceRequirements:
    """A requirement's declared evidence requirements (AD-32; DEC-0146, DEC-0178).

    Carries the ``world`` the evidence must come from, the ``account_role`` (a paper
    role here can never gate a live binding — AC4), the ``minimum_evidence_window``
    (a :class:`~qmf.core.Duration`), the required producer contract format versions
    (so a result whose producer versions differ does not satisfy the bar), and — from
    CT-22 contract format version 2 — the two bot-side evidence fields
    ``registered_conformant_bot_cite`` and ``canonical_assignment_evidence``
    (DEC-0178, DEC-0181).
    """

    world: World
    account_role: AccountRole
    minimum_evidence_window: Duration
    required_producer_contract_format_versions: Mapping[str, int]
    registered_conformant_bot_cite: bool = False
    canonical_assignment_evidence: bool = False
    contract_format_version: int = _EVIDENCE_FORMAT_2

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "required_producer_contract_format_versions",
            MappingProxyType(dict(self.required_producer_contract_format_versions)),
        )

    @classmethod
    def try_create(
        cls,
        world: object,
        account_role: object,
        minimum_evidence_window: object,
        required_producer_contract_format_versions: object,
        registered_conformant_bot_cite: object = False,
        canonical_assignment_evidence: object = False,
        contract_format_version: object = _EVIDENCE_FORMAT_2,
    ) -> _Result[EvidenceRequirements]:
        """Validate and build :class:`EvidenceRequirements`, value-or-refusal.

        The world and account role each name a member of their set; the minimum
        evidence window is a :class:`~qmf.core.Duration`; the required producer
        contract format versions are a mapping of ``contract_id -> int`` (a bool is
        not a version). The two bot-side flags exist **only** at CT-22 format 2
        (DEC-0181): asserting them at format 1 is ``invalid input`` so they cannot
        land as a silent AD-30 field addition a format-1 parser would ignore.
        """
        resolved_world = coerce_enum(World, world)
        if resolved_world is None:
            return invalid(
                "world",
                "evidence declares the world it comes from",
                given=repr(world),
                allowed=[member.value for member in World],
            )
        resolved_role = coerce_enum(AccountRole, account_role)
        if resolved_role is None:
            return invalid(
                "account_role",
                "evidence declares an account role",
                given=repr(account_role),
                allowed=[member.value for member in AccountRole],
            )
        if not isinstance(minimum_evidence_window, Duration):
            return invalid(
                "minimum_evidence_window",
                "the minimum evidence window is a Duration",
                given=repr(minimum_evidence_window),
            )
        versions = _coerce_producer_versions(required_producer_contract_format_versions)
        if isinstance(versions, _TypedRefusal):
            return versions
        if (
            isinstance(contract_format_version, bool)
            or not isinstance(contract_format_version, int)
            or contract_format_version not in _EVIDENCE_KNOWN_FORMAT_VERSIONS
        ):
            return unsupported(
                "contract_format_version",
                "an evidence_requirements contract format version this build does not "
                "understand; an unknown version is never best-effort read",
                given=repr(contract_format_version),
                understood=sorted(_EVIDENCE_KNOWN_FORMAT_VERSIONS),
            )
        if not isinstance(registered_conformant_bot_cite, bool):
            return invalid(
                "registered_conformant_bot_cite",
                "the registered-conformant-bot-cite flag is a bool (format-2 field)",
                given=repr(registered_conformant_bot_cite),
            )
        if not isinstance(canonical_assignment_evidence, bool):
            return invalid(
                "canonical_assignment_evidence",
                "the canonical-assignment-evidence flag is a bool (format-2 field)",
                given=repr(canonical_assignment_evidence),
            )
        if contract_format_version < _EVIDENCE_FORMAT_2 and (
            registered_conformant_bot_cite or canonical_assignment_evidence
        ):
            return invalid(
                "evidence_requirements",
                "registered_conformant_bot_cite and canonical_assignment_evidence land only "
                "through the CT-22 format-2 mint; a format-1 evidence_requirements cannot "
                "carry them — a silent field addition would let a format-1 parser ignore "
                "them and admit the evidence they exist to refuse",
                contract_format_version=contract_format_version,
            )
        return _Ok(
            cls(
                world=resolved_world,
                account_role=resolved_role,
                minimum_evidence_window=minimum_evidence_window,
                required_producer_contract_format_versions=versions,
                registered_conformant_bot_cite=registered_conformant_bot_cite,
                canonical_assignment_evidence=canonical_assignment_evidence,
                contract_format_version=contract_format_version,
            )
        )

    @property
    def names_paper_role(self) -> bool:
        """True when this requirement's evidence account role is a paper role (AC4)."""
        return self.account_role in PAPER_ACCOUNT_ROLES

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for these requirements.

        Format-1 identity **omits** the two bot-side fields so they cannot leak
        into a format-1 parser as ignored unknown keys (DEC-0178, DEC-0181).
        Format-2 identity includes them as declared values (even when false).
        """
        content: dict[str, object] = {
            "class": "evidence-requirements",
            "world": self.world.value,
            "account_role": self.account_role.value,
            "minimum_evidence_window": self.minimum_evidence_window.fp1_identity(),
            "required_producer_contract_format_versions": dict(
                self.required_producer_contract_format_versions
            ),
            "format_version": _ADMISSION_BAR_FORMAT_VERSION,
        }
        if self.contract_format_version >= _EVIDENCE_FORMAT_2:
            content["contract_format_version"] = self.contract_format_version
            content["registered_conformant_bot_cite"] = self.registered_conformant_bot_cite
            content["canonical_assignment_evidence"] = self.canonical_assignment_evidence
        return content


def _coerce_producer_versions(value: object) -> Mapping[str, int] | _TypedRefusal:
    """Resolve a ``contract_id -> format-version-int`` mapping, or a refusal."""
    if not isinstance(value, Mapping):
        return invalid(
            "required_producer_contract_format_versions",
            "the required producer contract format versions are a contract_id -> int mapping",
            given=repr(type(value).__name__),
        )
    mapping = cast("Mapping[object, object]", value)
    resolved: dict[str, int] = {}
    for key, version in mapping.items():
        token = clean_str(key)
        if token is None:
            return invalid(
                "required_producer_contract_format_versions",
                "a producer contract id is a non-empty string",
                given=repr(key),
            )
        if isinstance(version, bool) or not isinstance(version, int):
            return invalid(
                "required_producer_contract_format_versions",
                "a producer contract format version is an integer",
                contract_id=token,
                given=repr(version),
            )
        resolved[token] = version
    return MappingProxyType(resolved)


@dataclass(frozen=True, slots=True)
class AdmissionRequirement:
    """One admission-bar requirement — a pass/fail test on its own terms (AC2; DEC-0146).

    Carries an opaque ``measure_identity``, a mandatory ``unit``
    (:class:`~qmf.core.UnitKind`), a ``comparison`` (:class:`Comparison`), a
    ``threshold`` discriminated union (:class:`RuledThreshold` or
    :class:`~qmf.risk.grammar.NotYetRuled`, the key always present), the
    ``evidence_requirements``, a separate ``display_ordinal``, and — for a float
    measure — an optional :class:`ComparisonRule`. There is **no weight and no
    aggregate**: a requirement never contributes to a composite score.
    """

    measure_identity: str
    unit: UnitKind
    comparison: Comparison
    threshold: Threshold
    evidence_requirements: EvidenceRequirements
    display_ordinal: int
    comparison_rule: ComparisonRule | None = None

    @classmethod
    def try_create(
        cls,
        measure_identity: object,
        unit: object,
        comparison: object,
        threshold: object,
        evidence_requirements: object,
        display_ordinal: object,
        comparison_rule: object = None,
    ) -> _Result[AdmissionRequirement]:
        """Validate and build an :class:`AdmissionRequirement`, value-or-refusal.

        Refuses a blank ``measure_identity``; a missing/unknown ``unit`` (mandatory);
        a ``comparison`` outside the closed three-member set (a ``weighted`` or
        ``composite`` comparison is refused — no composite score may express a bar);
        a ``threshold`` that is neither a :class:`RuledThreshold` nor a
        :class:`~qmf.risk.grammar.NotYetRuled`; a ruled bound whose shape or unit-kind
        disagrees with the comparison/declared unit (``within-band`` needs a
        :class:`Band`, ``at-least``/``at-most`` a scalar); an ill-typed
        ``evidence_requirements``; a negative ``display_ordinal``; and an ill-typed
        ``comparison_rule``.
        """
        clean_id = clean_str(measure_identity)
        if clean_id is None:
            return invalid(
                "measure_identity",
                "a requirement declares a non-empty opaque measure_identity",
                given=repr(measure_identity),
            )
        resolved_unit = coerce_enum(UnitKind, unit)
        if resolved_unit is None:
            return invalid(
                "unit",
                "a requirement is missing its mandatory unit, or names one outside the "
                "closed AD-40 vocabulary",
                given=repr(unit),
                allowed=[member.value for member in UnitKind],
            )
        resolved_comparison = coerce_enum(Comparison, comparison)
        if resolved_comparison is None:
            return invalid(
                "comparison",
                "a requirement's comparison is exactly at-least | at-most | within-band; no "
                "composite, weighted, or aggregate comparison may express a bar",
                given=repr(comparison),
                allowed=[member.value for member in Comparison],
            )
        threshold_refusal = _validate_threshold(resolved_comparison, resolved_unit, threshold)
        if threshold_refusal is not None:
            return threshold_refusal
        if not isinstance(evidence_requirements, EvidenceRequirements):
            return invalid(
                "evidence_requirements",
                "a requirement carries an EvidenceRequirements value",
                given=repr(evidence_requirements),
            )
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
        if comparison_rule is not None and not isinstance(comparison_rule, ComparisonRule):
            return invalid(
                "comparison_rule",
                "a comparison_rule, when present, is a ComparisonRule value",
                given=repr(comparison_rule),
            )
        return _Ok(
            cls(
                measure_identity=clean_id,
                unit=resolved_unit,
                comparison=resolved_comparison,
                threshold=cast("Threshold", threshold),
                evidence_requirements=evidence_requirements,
                display_ordinal=display_ordinal,
                comparison_rule=comparison_rule,
            )
        )

    @property
    def is_blank(self) -> bool:
        """True when the threshold is an explicit :class:`~qmf.risk.grammar.NotYetRuled`."""
        return isinstance(self.threshold, NotYetRuled)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this requirement."""
        content: dict[str, object] = {
            "class": "admission-requirement",
            "measure_identity": self.measure_identity,
            "unit": self.unit.value,
            "comparison": self.comparison.value,
            "threshold": self.threshold.fp1_identity(),
            "evidence_requirements": self.evidence_requirements.fp1_identity(),
            "display_ordinal": self.display_ordinal,
            "format_version": _ADMISSION_BAR_FORMAT_VERSION,
        }
        if self.comparison_rule is not None:
            content["comparison_rule"] = self.comparison_rule.fp1_identity()
        return content


def _validate_threshold(
    comparison: Comparison, unit: UnitKind, threshold: object
) -> _TypedRefusal | None:
    """Validate a threshold against its comparison and declared unit-kind.

    Returns ``None`` when legal, or the refusal to return. A
    :class:`~qmf.risk.grammar.NotYetRuled` blank passes (blankness is a declared value
    that blocks live money elsewhere). A :class:`RuledThreshold` must carry a
    :class:`Band` for ``within-band`` and a scalar exact rational otherwise, and its
    unit-kind must equal the declared requirement unit.
    """
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
class PendingSlot:
    """A ``pending(<ref>)`` marker on a mandatory surface whose contract is deferred.

    Like a :class:`~qmf.risk.grammar.NotYetRuled` threshold, a pending slot is a
    declared blank: a bar holding one registers and binds non-live freely but blocks a
    live binding (AC3; DEC-0144, DEC-0146).
    """

    ref: str

    @classmethod
    def try_create(cls, ref: object) -> _Result[PendingSlot]:
        """Validate and build a :class:`PendingSlot`; the ref is a non-blank token."""
        token = clean_str(ref)
        if token is None:
            return invalid(
                "ref", "a pending slot declares its reference as a non-empty token", given=repr(ref)
            )
        return _Ok(cls(ref=token))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this pending slot."""
        return {"class": "pending-slot", "ref": self.ref}


@dataclass(frozen=True, slots=True)
class AdmissionBar:
    """ "The Book sets the bar" — a set of requirements, never a score (AC2; DEC-0146).

    Carries the ``requirements`` canonically ordered by ``measure_identity`` (the
    display ordinal is separate, on each requirement) and any ``pending_slots``. The
    set is consumer of no aggregate: there is **no weight, no composite score, no
    rating, no tier band** — :func:`evaluate_bar` returns a per-requirement verdict
    mapping, and each requirement passes or fails on its own terms.
    """

    requirements: tuple[AdmissionRequirement, ...]
    pending_slots: tuple[PendingSlot, ...]

    @classmethod
    def try_create(cls, requirements: object, pending_slots: object = ()) -> _Result[AdmissionBar]:
        """Validate and build an :class:`AdmissionBar`, value-or-refusal.

        ``requirements`` is a collection of :class:`AdmissionRequirement` with unique
        ``measure_identity`` (a bar is a set, not a bag — a duplicate identity is
        ``invalid input``); they are canonically ordered by ``measure_identity`` so two
        operators writing the same requirements in a different order get the same bar
        identity. ``pending_slots`` is a collection of :class:`PendingSlot`.
        """
        resolved_requirements = _coerce_requirements(requirements)
        if isinstance(resolved_requirements, _TypedRefusal):
            return resolved_requirements
        resolved_slots = _coerce_pending_slots(pending_slots)
        if isinstance(resolved_slots, _TypedRefusal):
            return resolved_slots
        return _Ok(cls(requirements=resolved_requirements, pending_slots=resolved_slots))

    @property
    def is_blank(self) -> bool:
        """True when any threshold is not-yet-ruled or any pending slot exists (AC3)."""
        return bool(self.pending_slots) or any(req.is_blank for req in self.requirements)

    def by_identity(self) -> Mapping[str, AdmissionRequirement]:
        """The requirements keyed by ``measure_identity`` (a read-only view)."""
        return MappingProxyType({req.measure_identity: req for req in self.requirements})

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — requirements in canonical order."""
        return {
            "class": "admission-bar",
            "requirements": [req.fp1_identity() for req in self.requirements],
            "pending_slots": [slot.fp1_identity() for slot in self.pending_slots],
            "format_version": _ADMISSION_BAR_FORMAT_VERSION,
        }


def _coerce_requirements(value: object) -> tuple[AdmissionRequirement, ...] | _TypedRefusal:
    """Resolve a collection of unique-identity requirements in canonical order."""
    given = type_name(value)
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        return invalid(
            "requirements",
            "an admission bar is a collection of AdmissionRequirement values",
            given=given,
        )
    seen: set[str] = set()
    items: list[AdmissionRequirement] = []
    for item in cast("Iterable[object]", value):
        if not isinstance(item, AdmissionRequirement):
            return invalid(
                "requirements", "each requirement is an AdmissionRequirement", given=repr(item)
            )
        if item.measure_identity in seen:
            return invalid(
                "requirements",
                "a bar is a set — a measure_identity appears at most once",
                measure_identity=item.measure_identity,
            )
        seen.add(item.measure_identity)
        items.append(item)
    items.sort(key=lambda req: req.measure_identity)
    return tuple(items)


def _coerce_pending_slots(value: object) -> tuple[PendingSlot, ...] | _TypedRefusal:
    """Resolve a collection of :class:`PendingSlot` values."""
    given = type_name(value)
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        return invalid(
            "pending_slots",
            "pending_slots is a collection of PendingSlot values",
            given=given,
        )
    items: list[PendingSlot] = []
    for item in cast("Iterable[object]", value):
        if not isinstance(item, PendingSlot):
            return invalid("pending_slots", "each pending slot is a PendingSlot", given=repr(item))
        items.append(item)
    return tuple(items)


def reject_bar_aggregate(construct: object) -> _TypedRefusal:
    """Refuse any attempt to express a bar as a composite (AC2; DEC-0146).

    No composite score, rating, tier band, or weighted aggregate may express a bar —
    each requirement passes or fails on its own terms. This makes the prohibition
    first-class: a caller reaching for a composite construct gets a ``policy
    rejection`` naming it, never a silent aggregation.
    """
    name = clean_str(construct) or "aggregate"
    return policy(
        "admission_bar",
        "no composite score, rating, tier band, or weighted aggregate may express a bar; "
        "each requirement passes or fails on its own terms",
        construct=name,
    )


def bar_is_blank(bar: object) -> bool:
    """True when a bar holds any not-yet-ruled threshold or pending slot (AC3)."""
    return isinstance(bar, AdmissionBar) and bar.is_blank


def check_live_binding_admissible(bar: object, target_role: object) -> _Result[None]:
    """Blank blocks live money (AC3; L38, DEC-0146).

    A bar holding any ``not-yet-ruled`` threshold or ``pending`` slot registers and
    binds to **non-live** roles freely, so a non-live ``target_role`` always passes.
    Binding a **blank** bar to a ``role = live`` account is a ``policy rejection`` —
    the container ships complete today with every number honestly blank, but blank
    blocks live money. A non-blank bar binding live passes here (other admission
    checks apply). An unknown ``target_role`` is ``invalid input``.
    """
    if not isinstance(bar, AdmissionBar):
        return invalid("bar", "the live-binding check reads an AdmissionBar", given=repr(bar))
    resolved_role = coerce_enum(AccountRole, target_role)
    if resolved_role is None:
        return invalid(
            "target_role",
            "the target binding account role names a member of the account-role set",
            given=repr(target_role),
            allowed=[member.value for member in AccountRole],
        )
    if resolved_role is AccountRole.LIVE and bar.is_blank:
        return policy(
            "admission_bar",
            "blank blocks live money: a bar holding a not-yet-ruled threshold or a pending "
            "slot registers and binds non-live freely, but binding to a live account is refused",
        )
    return _Ok(None)


def check_no_paper_role_gates_live(bar: object, binding_role: object) -> _Result[None]:
    """No paper role may gate live money (AC4; DEC-0146, DEC-0149).

    When ``binding_role`` is ``live``, a requirement whose
    ``evidence_requirements.account_role`` names a paper role is a ``policy
    rejection`` — this field can never rebuild the paper-performance gate admission
    exists to forbid. A non-live binding role passes (a paper role gating a non-live
    binding is fine). An unknown ``binding_role`` is ``invalid input``.
    """
    if not isinstance(bar, AdmissionBar):
        return invalid("bar", "the paper-role check reads an AdmissionBar", given=repr(bar))
    resolved_role = coerce_enum(AccountRole, binding_role)
    if resolved_role is None:
        return invalid(
            "binding_role",
            "the binding account role names a member of the account-role set",
            given=repr(binding_role),
            allowed=[member.value for member in AccountRole],
        )
    if resolved_role is not AccountRole.LIVE:
        return _Ok(None)
    for req in bar.requirements:
        if req.evidence_requirements.names_paper_role:
            return policy(
                "evidence_requirements",
                "no paper role may gate live money; a paper account role in a requirement "
                "gating a live binding is refused, so admission's own gate cannot return",
                measure_identity=req.measure_identity,
                account_role=req.evidence_requirements.account_role.value,
            )
    return _Ok(None)


def evaluate_requirement(requirement: object, measure: object) -> _Result[RequirementVerdict]:
    """Evaluate one requirement against one measure — on its own terms (AC2, AC6).

    A blank (not-yet-ruled) requirement returns ``NOT_YET_RULED`` regardless of the
    measure. A ruled requirement compares the measure to its threshold: an **exact**
    measure must share the requirement's unit-kind and compares directly; a **float**
    measure crosses the named analytic→exact boundary under the requirement's
    :class:`ComparisonRule` (target scale, rounding mode, tie disposition), and a
    float measure with **no declared comparison rule is ``invalid input``** (AC6). Ties
    resolve by the rule's :class:`TieDisposition` (or boundary-inclusive when a rule is
    absent for an exact measure). Returns the :class:`RequirementVerdict`.
    """
    if not isinstance(requirement, AdmissionRequirement):
        return invalid(
            "requirement", "evaluation reads an AdmissionRequirement", given=repr(requirement)
        )
    if requirement.is_blank:
        return _Ok(RequirementVerdict.NOT_YET_RULED)
    frac = _measure_fraction(requirement, measure)
    if isinstance(frac, _TypedRefusal):
        return frac
    tie = (
        requirement.comparison_rule.tie_disposition
        if requirement.comparison_rule is not None
        else TieDisposition.PASS_ON_TIE
    )
    ruled = cast("RuledThreshold", requirement.threshold)
    return _Ok(_compare(frac, requirement.comparison, ruled.bound, tie))


def evaluate_bar(bar: object, measures: object) -> _Result[Mapping[str, RequirementVerdict]]:
    """Evaluate every requirement independently — a per-requirement verdict map (AC2).

    Returns a mapping ``measure_identity -> RequirementVerdict``, **never a composite
    score**: each requirement passes or fails on its own terms. ``measures`` is a
    mapping ``measure_identity -> measure``; a blank requirement needs no measure, and
    a ruled requirement whose measure is absent is ``invalid input`` (a ruled bar
    cannot be judged without its measure). Any per-requirement evaluation refusal
    (e.g. an undeclared float comparison) propagates.
    """
    if not isinstance(bar, AdmissionBar):
        return invalid("bar", "bar evaluation reads an AdmissionBar", given=repr(bar))
    if not isinstance(measures, Mapping):
        return invalid(
            "measures",
            "measures are a measure_identity -> measure mapping",
            given=repr(type(measures).__name__),
        )
    measure_map = cast("Mapping[object, object]", measures)
    verdicts: dict[str, RequirementVerdict] = {}
    for req in bar.requirements:
        if req.is_blank:
            verdicts[req.measure_identity] = RequirementVerdict.NOT_YET_RULED
            continue
        if req.measure_identity not in measure_map:
            return invalid(
                "measures",
                "a ruled requirement cannot be judged without its measure",
                measure_identity=req.measure_identity,
            )
        verdict = evaluate_requirement(req, measure_map[req.measure_identity])
        if isinstance(verdict, _TypedRefusal):
            return verdict
        verdicts[req.measure_identity] = verdict.value
    return _Ok(MappingProxyType(verdicts))


def _measure_fraction(
    requirement: AdmissionRequirement, measure: object
) -> Fraction | _TypedRefusal:
    """Resolve a measure to an exact :class:`~fractions.Fraction`, or a refusal.

    A ``bool`` is not a measure. A ``float`` crosses the analytic→exact boundary under
    the requirement's :class:`ComparisonRule` (undeclared ⇒ ``invalid input``, AC6). An
    exact carrier must share the requirement's declared unit-kind.
    """
    if isinstance(measure, bool):
        return invalid("measure", "a measure is not a bool", given=repr(measure))
    if isinstance(measure, float):
        rule = requirement.comparison_rule
        if rule is None:
            return invalid(
                "comparison_rule",
                "a float-valued measure crosses the analytic->exact boundary under a "
                "comparison rule declared in the requirement (target scale, rounding mode, "
                "tie disposition); an undeclared comparison is refused",
                measure_identity=requirement.measure_identity,
            )
        if not math.isfinite(measure):
            return invalid(
                "measure",
                "a float measure must be finite to cross the analytic->exact boundary",
                given=repr(measure),
            )
        return _quantize_float(measure, rule)
    if isinstance(measure, (ExactRational, Money, Price, PriceDelta, Quantity, ValueFactor)):
        if measure.unit_kind is not requirement.unit:
            return invalid(
                "measure",
                "an exact measure's unit-kind must equal the requirement's declared unit",
                declared=requirement.unit.value,
                measure_unit=measure.unit_kind.value,
            )
        return measure.as_fraction()
    return invalid(
        "measure",
        "a measure is a finite float analytic value or an exact qmf-core carrier",
        given=repr(measure),
    )


def _quantize_float(measure: float, rule: ComparisonRule) -> Fraction:
    """Quantize a finite float to an exact Fraction at the rule's scale and mode."""
    quantum = Decimal(1).scaleb(-rule.target_scale)
    rounded = Decimal(measure).quantize(quantum, rounding=_ROUNDING[rule.rounding_mode])
    return Fraction(rounded)


def _compare(
    measure: Fraction, comparison: Comparison, bound: ExactRational | Band, tie: TieDisposition
) -> RequirementVerdict:
    """Compare an exact measure to a ruled bound under a comparison and tie disposition."""
    on_tie = (
        RequirementVerdict.PASS if tie is TieDisposition.PASS_ON_TIE else RequirementVerdict.FAIL
    )
    if comparison is Comparison.WITHIN_BAND:
        band = cast("Band", bound)
        lower = band.lower.as_fraction()
        upper = band.upper.as_fraction()
        if lower < measure < upper:
            return RequirementVerdict.PASS
        if measure in (lower, upper):
            return on_tie
        return RequirementVerdict.FAIL
    threshold = cast("ExactRational", bound).as_fraction()
    if comparison is Comparison.AT_LEAST:
        if measure > threshold:
            return RequirementVerdict.PASS
        if measure == threshold:
            return on_tie
        return RequirementVerdict.FAIL
    # AT_MOST
    if measure < threshold:
        return RequirementVerdict.PASS
    if measure == threshold:
        return on_tie
    return RequirementVerdict.FAIL
