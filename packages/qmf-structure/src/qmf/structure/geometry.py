"""CT-17 — sloped/continuous objects and calendar-anchored levels (COMP-QMF-STRUCTURE).

Two geometry shapes CT-17 names that the point/zone anchor of Story 9.1 does not by itself
express: the **sloped or continuous object** (projected levels, trendlines, channels) and
the **calendar-anchored level** (a level pinned to a market-hours calendar). Both are needed
to keep the CT-17 conformance register expressible (DEC-0129, DEC-0126, DEC-0105).

**A sloped object is anchors plus a versioned evaluation rule; slope is derived, never
stored (DEC-0129, DEC-0126, DEC-0105).** :class:`SlopedObject` is identified by an ordered
set of :class:`AnchorPoint` (instant, exact Price) pairs plus a declared
:class:`EvaluationRuleRef` — a versioned evaluation rule id — and the fingerprinted
analytic-to-exact return surface it will evaluate through: a target scale and an explicit
rounding mode. The slope itself is **never** an identity field; it is derived at evaluation
time by the one qmf-core analytic-to-exact boundary (DEC-0105), which this package never
re-implements — so a **projected level** is a sloped object whose anchors lie in the past and
whose evaluation projects forward.

**A calendar-anchored level declares its sampling and schedule-gap policies (DEC-0129,
DEC-0119).** :class:`CalendarAnchoredLevel` pins a level to a market-hours calendar identity
and declares — as fingerprinted surface — how it samples (last-known-at-or-before, or refuse)
and how it handles a schedule gap (refuse, nearest-open-instant, or carry-previous-session).
A **standing (a-priori) object** declares ``observed_at = its configuration instant``. Both
policies enter identity, so two levels differing only in policy are distinct artifacts.

Default-deny holds: this module imports **only** ``qmf.core`` and the sibling
``qmf.structure`` value types. Every ``fp1`` is computed in qmf-core; these types return
fingerprintable content, never stamped records. Public value types are frozen dataclasses,
and every operation succeeds or RETURNS a CT-04 :class:`~qmf.core.TypedRefusal`; domain
failure is never raised across the boundary (DEC-0101, DEC-0109, DEC-0113).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from itertools import pairwise
from types import MappingProxyType
from typing import cast

from qmf.core import (
    CalendarIdentity,
    EvidenceClass,
    ExactRational,
    Fingerprint,
    Instant,
    Ok,
    Price,
    RefusalCategory,
    Result,
    Retryability,
    RoundingMode,
    TypedRefusal,
    fingerprint,
)
from qmf.structure.objects import (
    CONTRACT_FORMAT_VERSION,
    ConfirmationRule,
    FamilyIdentity,
)

__all__ = [
    "AnchorPoint",
    "CalendarAnchoredLevel",
    "EvaluationRuleRef",
    "SamplingPolicy",
    "ScheduleGapPolicy",
    "SlopedObject",
]


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a geometry operation returns (CT-04; DEC-0109)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _coerce_evidence_class(value: object) -> EvidenceClass | None:
    if isinstance(value, EvidenceClass):
        return value
    if isinstance(value, str):
        try:
            return EvidenceClass(value)
        except ValueError:
            return None
    return None


def _coerce_rounding(value: object) -> RoundingMode | None:
    if isinstance(value, RoundingMode):
        return value
    if isinstance(value, str):
        try:
            return RoundingMode(value)
        except ValueError:
            return None
    return None


def _coerce_parameters(value: object) -> dict[str, ExactRational] | TypedRefusal:
    if not isinstance(value, Mapping):
        return _invalid(
            "parameters",
            "the parameter set is a name->ExactRational mapping (exact rationals only)",
            given=repr(type(value).__name__),
        )
    mapping = cast("Mapping[object, object]", value)
    out: dict[str, ExactRational] = {}
    for key, item in mapping.items():
        if not isinstance(key, str) or key.strip() == "":
            return _invalid(
                "parameters", "each parameter name is a non-empty string", given=repr(key)
            )
        if not isinstance(item, ExactRational):
            return _invalid(
                "parameters",
                "each parameter value is an ExactRational (never a binary float)",
                name=key,
                given=repr(item),
            )
        out[key] = item
    return out


def _calendar_content(calendar: CalendarIdentity) -> dict[str, object]:
    """The calendar identity's canonical parts for fingerprint content (CT-02; DEC-0106)."""
    return {
        "rule_set": calendar.rule_set,
        "rule_set_version": calendar.rule_set_version,
        "tzdata_version": calendar.tzdata_version,
    }


# --- the sloped / continuous object -----------------------------------------


@dataclass(frozen=True, slots=True)
class AnchorPoint:
    """One (instant, exact Price) anchor of a sloped object (CT-17; DEC-0129, DEC-0105)."""

    instant: Instant
    price: Price

    @classmethod
    def try_create(cls, instant: object, price: object) -> Result[AnchorPoint]:
        """Validate and build an :class:`AnchorPoint`, returning value-or-refusal."""
        if not isinstance(instant, Instant):
            return _invalid("instant", "an anchor point instant is an Instant", given=repr(instant))
        if not isinstance(price, Price):
            return _invalid("price", "an anchor point price is an exact Price", given=repr(price))
        return Ok(cls(instant=instant, price=price))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this anchor point."""
        return {"instant_ns": self.instant.value_ns, "price": self.price.fp1_identity()}


@dataclass(frozen=True, slots=True)
class EvaluationRuleRef:
    """A declared, versioned evaluation rule id for a sloped object (CT-17; DEC-0129).

    The evaluation rule (how the object's value at an instant is derived from its anchors) is
    identity-bearing and versioned; the concrete evaluation crosses the qmf-core
    analytic-to-exact boundary and is never re-implemented here.
    """

    rule_id: str
    version: int

    @classmethod
    def try_create(cls, rule_id: object, version: object) -> Result[EvaluationRuleRef]:
        """Validate and build an :class:`EvaluationRuleRef`, returning value-or-refusal."""
        if not isinstance(rule_id, str) or rule_id.strip() == "":
            return _invalid(
                "rule_id", "an evaluation rule id is a non-empty token", given=repr(rule_id)
            )
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            return _invalid(
                "version", "an evaluation rule version is a positive integer", given=repr(version)
            )
        return Ok(cls(rule_id=rule_id, version=version))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this evaluation rule."""
        return {"rule_id": self.rule_id, "version": self.version}


@dataclass(frozen=True, slots=True)
class SlopedObject:
    """A sloped or continuous object: ordered anchors plus a versioned evaluation rule (CT-17;
    DEC-0129, DEC-0126, DEC-0105).

    ``anchor_points`` is an ordered tuple of two or more :class:`AnchorPoint` of one instrument,
    strictly increasing in time; ``evaluation_rule`` names how a value at an instant is derived;
    ``target_scale`` and ``rounding`` are the fingerprinted analytic-to-exact return surface the
    evaluation will use. Slope is **derived, never stored**. A projected level is a sloped object
    whose anchors precede ``observed_at`` and whose evaluation projects forward.
    """

    family: FamilyIdentity
    confirmation_rule: ConfirmationRule
    anchor_points: tuple[AnchorPoint, ...]
    evaluation_rule: EvaluationRuleRef
    target_scale: int
    rounding: RoundingMode
    observed_at: Instant
    evidence_class: EvidenceClass
    parameters: Mapping[str, ExactRational]

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))

    @classmethod
    def try_create(
        cls,
        *,
        family: object,
        confirmation_rule: object,
        anchor_points: object,
        evaluation_rule: object,
        target_scale: object,
        rounding: object,
        observed_at: object,
        evidence_class: object,
        parameters: object = None,
    ) -> Result[SlopedObject]:
        """Validate and build a :class:`SlopedObject`, returning value-or-refusal."""
        if not isinstance(family, FamilyIdentity):
            return _invalid(
                "family", "a sloped object carries a FamilyIdentity", given=repr(family)
            )
        if not isinstance(confirmation_rule, ConfirmationRule):
            return _invalid(
                "confirmation_rule",
                "a sloped object declares a ConfirmationRule",
                given=repr(confirmation_rule),
            )
        if isinstance(anchor_points, (str, bytes)) or not isinstance(anchor_points, Sequence):
            return _invalid(
                "anchor_points",
                "anchor points are a sequence of AnchorPoint",
                given=repr(anchor_points),
            )
        points = cast("Sequence[object]", anchor_points)
        if len(points) < 2:
            return _invalid(
                "anchor_points",
                "a sloped object needs two or more anchor points",
                given=len(points),
            )
        resolved_points: list[AnchorPoint] = []
        for index, point in enumerate(points):
            if not isinstance(point, AnchorPoint):
                return _invalid(
                    "anchor_points", "each anchor is an AnchorPoint", index=index, given=repr(point)
                )
            resolved_points.append(point)
        instrument = resolved_points[0].price.instrument
        for index, point in enumerate(resolved_points):
            if point.price.instrument != instrument:
                return _invalid("anchor_points", "anchor points are of one instrument", index=index)
        for earlier, later in pairwise(resolved_points):
            if earlier.instant.value_ns >= later.instant.value_ns:
                return _invalid(
                    "anchor_points",
                    "anchor points are strictly increasing in time",
                    earlier=earlier.instant.value_ns,
                    later=later.instant.value_ns,
                )
        if not isinstance(evaluation_rule, EvaluationRuleRef):
            return _invalid(
                "evaluation_rule",
                "the evaluation rule is an EvaluationRuleRef",
                given=repr(evaluation_rule),
            )
        if isinstance(target_scale, bool) or not isinstance(target_scale, int) or target_scale < 0:
            return _invalid(
                "target_scale",
                "the target scale is a non-negative integer",
                given=repr(target_scale),
            )
        resolved_rounding = _coerce_rounding(rounding)
        if resolved_rounding is None:
            return _invalid(
                "rounding",
                "the analytic-to-exact return declares an explicit rounding mode",
                given=repr(rounding),
                allowed=[member.value for member in RoundingMode],
            )
        if not isinstance(observed_at, Instant):
            return _invalid("observed_at", "observed-at is an Instant", given=repr(observed_at))
        if observed_at.value_ns < resolved_points[-1].instant.value_ns:
            return _invalid(
                "observed_at",
                "a sloped object's observed-at is at or after its last anchor point (the anchors "
                "are frozen payload, never later than the observation that derived them)",
                last_anchor=resolved_points[-1].instant.value_ns,
                observed_at=observed_at.value_ns,
            )
        resolved_class = _coerce_evidence_class(evidence_class)
        if resolved_class is None:
            return _invalid(
                "evidence_class",
                "the evidence class is one of the closed set",
                given=repr(evidence_class),
                allowed=[member.value for member in EvidenceClass],
            )
        resolved_parameters = _coerce_parameters({} if parameters is None else parameters)
        if isinstance(resolved_parameters, TypedRefusal):
            return resolved_parameters
        return Ok(
            cls(
                family=family,
                confirmation_rule=confirmation_rule,
                anchor_points=tuple(resolved_points),
                evaluation_rule=evaluation_rule,
                target_scale=target_scale,
                rounding=resolved_rounding,
                observed_at=observed_at,
                evidence_class=resolved_class,
                parameters=resolved_parameters,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content; slope is derived, never identity."""
        content: dict[str, object] = {
            "class": "sloped-structure-object",
            "family": self.family.fp1_identity(),
            "confirmation_rule": self.confirmation_rule.fp1_identity(),
            "anchor_points": [point.fp1_identity() for point in self.anchor_points],
            "evaluation_rule": self.evaluation_rule.fp1_identity(),
            "target_scale": self.target_scale,
            "rounding": self.rounding.value,
            "observed_at": self.observed_at.value_ns,
            "evidence_class": self.evidence_class.value,
            "format_version": CONTRACT_FORMAT_VERSION,
        }
        if self.parameters:
            content["parameters"] = {
                name: value.fp1_identity() for name, value in self.parameters.items()
            }
        return content

    def content_fingerprint(self) -> Result[Fingerprint]:
        """The sloped object's ``fp1`` fingerprint, computed in qmf-core (DEC-0108)."""
        return fingerprint(self.fp1_identity())


# --- the calendar-anchored level --------------------------------------------


class SamplingPolicy(StrEnum):
    """A calendar-anchored level's declared sampling policy (CT-17; DEC-0129)."""

    LAST_KNOWN_AT_OR_BEFORE = "last-known-at-or-before"
    REFUSE = "refuse"


class ScheduleGapPolicy(StrEnum):
    """A calendar-anchored level's declared schedule-gap policy (CT-17; DEC-0129)."""

    REFUSE = "refuse"
    NEAREST_OPEN_INSTANT = "nearest-open-instant"
    CARRY_PREVIOUS_SESSION = "carry-previous-session"


@dataclass(frozen=True, slots=True)
class CalendarAnchoredLevel:
    """A level pinned to a market-hours calendar, with declared sampling/gap policies (CT-17;
    DEC-0129, DEC-0119).

    ``calendar`` is the market-hours calendar identity; ``sampling_policy`` and
    ``schedule_gap_policy`` are fingerprinted declared surface; ``level`` the exact Price; and
    ``observed_at`` the knowledge time — a standing (a-priori) level declares its configuration
    instant here. Every field is identity-bearing and the object is never mutated.
    """

    family: FamilyIdentity
    confirmation_rule: ConfirmationRule
    calendar: CalendarIdentity
    sampling_policy: SamplingPolicy
    schedule_gap_policy: ScheduleGapPolicy
    level: Price
    observed_at: Instant
    evidence_class: EvidenceClass
    parameters: Mapping[str, ExactRational]

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))

    @classmethod
    def try_create(
        cls,
        *,
        family: object,
        confirmation_rule: object,
        calendar: object,
        sampling_policy: object,
        schedule_gap_policy: object,
        level: object,
        observed_at: object,
        evidence_class: object,
        parameters: object = None,
    ) -> Result[CalendarAnchoredLevel]:
        """Validate and build a :class:`CalendarAnchoredLevel`, returning value-or-refusal."""
        if not isinstance(family, FamilyIdentity):
            return _invalid(
                "family", "a calendar-anchored level carries a FamilyIdentity", given=repr(family)
            )
        if not isinstance(confirmation_rule, ConfirmationRule):
            return _invalid(
                "confirmation_rule",
                "a calendar-anchored level declares a ConfirmationRule",
                given=repr(confirmation_rule),
            )
        if not isinstance(calendar, CalendarIdentity):
            return _invalid(
                "calendar", "the calendar is a market-hours CalendarIdentity", given=repr(calendar)
            )
        sampling = _coerce_sampling(sampling_policy)
        if sampling is None:
            return _invalid(
                "sampling_policy",
                "the sampling policy is one of the closed set",
                given=repr(sampling_policy),
                allowed=[member.value for member in SamplingPolicy],
            )
        schedule_gap = _coerce_schedule_gap(schedule_gap_policy)
        if schedule_gap is None:
            return _invalid(
                "schedule_gap_policy",
                "the schedule-gap policy is one of the closed set",
                given=repr(schedule_gap_policy),
                allowed=[member.value for member in ScheduleGapPolicy],
            )
        if not isinstance(level, Price):
            return _invalid("level", "the level is an exact Price", given=repr(level))
        if not isinstance(observed_at, Instant):
            return _invalid(
                "observed_at",
                "observed-at is an Instant (a standing level's configuration instant)",
                given=repr(observed_at),
            )
        resolved_class = _coerce_evidence_class(evidence_class)
        if resolved_class is None:
            return _invalid(
                "evidence_class",
                "the evidence class is one of the closed set",
                given=repr(evidence_class),
                allowed=[member.value for member in EvidenceClass],
            )
        resolved_parameters = _coerce_parameters({} if parameters is None else parameters)
        if isinstance(resolved_parameters, TypedRefusal):
            return resolved_parameters
        return Ok(
            cls(
                family=family,
                confirmation_rule=confirmation_rule,
                calendar=calendar,
                sampling_policy=sampling,
                schedule_gap_policy=schedule_gap,
                level=level,
                observed_at=observed_at,
                evidence_class=resolved_class,
                parameters=resolved_parameters,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — every part is identity."""
        content: dict[str, object] = {
            "class": "calendar-anchored-level",
            "family": self.family.fp1_identity(),
            "confirmation_rule": self.confirmation_rule.fp1_identity(),
            "calendar": _calendar_content(self.calendar),
            "sampling_policy": self.sampling_policy.value,
            "schedule_gap_policy": self.schedule_gap_policy.value,
            "level": self.level.fp1_identity(),
            "observed_at": self.observed_at.value_ns,
            "evidence_class": self.evidence_class.value,
            "format_version": CONTRACT_FORMAT_VERSION,
        }
        if self.parameters:
            content["parameters"] = {
                name: value.fp1_identity() for name, value in self.parameters.items()
            }
        return content

    def content_fingerprint(self) -> Result[Fingerprint]:
        """The calendar-anchored level's ``fp1`` fingerprint, computed in qmf-core (DEC-0108)."""
        return fingerprint(self.fp1_identity())


def _coerce_sampling(value: object) -> SamplingPolicy | None:
    if isinstance(value, SamplingPolicy):
        return value
    if isinstance(value, str):
        try:
            return SamplingPolicy(value)
        except ValueError:
            return None
    return None


def _coerce_schedule_gap(value: object) -> ScheduleGapPolicy | None:
    if isinstance(value, ScheduleGapPolicy):
        return value
    if isinstance(value, str):
        try:
            return ScheduleGapPolicy(value)
        except ValueError:
            return None
    return None
