"""Tier-1/Tier-2 tests for CT-17 sloped/projected objects and calendar-anchored levels
(Story 9.4). Covers DEC-0129/DEC-0126/DEC-0105/DEC-0119."""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    CalendarIdentity,
    EvidenceClass,
    Instant,
    Instrument,
    Price,
    Result,
    RoundingMode,
    VenueId,
    is_ok,
    is_refusal,
)
from qmf.structure import (
    AnchorPoint,
    CalendarAnchoredLevel,
    ConfirmationRule,
    EvaluationRuleRef,
    FamilyIdentity,
    SamplingPolicy,
    ScheduleGapPolicy,
    SlopedObject,
)

T = TypeVar("T")
_MINUTE = 60_000_000_000
_BASE = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    assert is_ok(result), f"expected {what}, got {result}"
    return result.value


def _instrument(symbol: str = "EURUSD") -> Instrument:
    return Instrument(venue=VenueId(value="ctrader"), symbol=symbol)


def _price(value: int, symbol: str = "EURUSD") -> Price:
    return _unwrap(Price.try_create(value, _instrument(symbol), 5), "price")


def _identity(geometry: str = "level") -> FamilyIdentity:
    return _unwrap(FamilyIdentity.try_create("projected-line", 1, geometry), "identity")


def _rule() -> ConfirmationRule:
    return _unwrap(
        ConfirmationRule.try_create("confirmed the moment price touches the projection"),
        "rule",
    )


def _point(minute: int, value: int, symbol: str = "EURUSD") -> AnchorPoint:
    return _unwrap(
        AnchorPoint.try_create(Instant(value_ns=_BASE + minute * _MINUTE), _price(value, symbol)),
        "anchor point",
    )


def _eval_rule() -> EvaluationRuleRef:
    return _unwrap(EvaluationRuleRef.try_create("linear-two-point", 1), "eval rule")


def _sloped(observed_min: int = 2) -> Result[SlopedObject]:
    return SlopedObject.try_create(
        family=_identity(),
        confirmation_rule=_rule(),
        anchor_points=[_point(0, 108_000), _point(1, 108_200)],
        evaluation_rule=_eval_rule(),
        target_scale=5,
        rounding=RoundingMode.HALF_EVEN,
        observed_at=Instant(value_ns=_BASE + observed_min * _MINUTE),
        evidence_class=EvidenceClass.UNCONFIRMED,
    )


def test_sloped_object_is_a_projected_level_expressible() -> None:
    sloped = _unwrap(_sloped(), "sloped object")
    assert len(sloped.anchor_points) == 2
    assert sloped.evaluation_rule.rule_id == "linear-two-point"
    assert sloped.rounding is RoundingMode.HALF_EVEN
    # A projected level: anchors precede observed_at, and the object fingerprints (slope is
    # derived, never stored — no slope field exists).
    assert not hasattr(sloped, "slope")
    assert is_ok(sloped.content_fingerprint())


def test_sloped_object_fingerprint_is_derived_and_stable() -> None:
    a = _unwrap(_unwrap(_sloped(), "a").content_fingerprint(), "fp a")
    b = _unwrap(_unwrap(_sloped(), "b").content_fingerprint(), "fp b")
    assert a == b
    assert a.value.startswith("fp1:sha256:")


def test_sloped_object_refuses_bad_construction() -> None:
    # fewer than two anchor points
    assert is_refusal(
        SlopedObject.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            anchor_points=[_point(0, 108_000)],
            evaluation_rule=_eval_rule(),
            target_scale=5,
            rounding=RoundingMode.HALF_EVEN,
            observed_at=Instant(value_ns=_BASE + 2 * _MINUTE),
            evidence_class=EvidenceClass.UNCONFIRMED,
        )
    )
    # non-increasing instants
    assert is_refusal(
        SlopedObject.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            anchor_points=[_point(1, 108_000), _point(0, 108_200)],
            evaluation_rule=_eval_rule(),
            target_scale=5,
            rounding=RoundingMode.HALF_EVEN,
            observed_at=Instant(value_ns=_BASE + 2 * _MINUTE),
            evidence_class=EvidenceClass.UNCONFIRMED,
        )
    )
    # mixed instrument
    assert is_refusal(
        SlopedObject.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            anchor_points=[_point(0, 108_000), _point(1, 108_200, symbol="GBPUSD")],
            evaluation_rule=_eval_rule(),
            target_scale=5,
            rounding=RoundingMode.HALF_EVEN,
            observed_at=Instant(value_ns=_BASE + 2 * _MINUTE),
            evidence_class=EvidenceClass.UNCONFIRMED,
        )
    )
    # observed_at before the last anchor point
    assert is_refusal(_sloped(observed_min=0))
    # bad evaluation rule / target scale / rounding
    assert is_refusal(
        SlopedObject.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            anchor_points=[_point(0, 108_000), _point(1, 108_200)],
            evaluation_rule=object(),
            target_scale=5,
            rounding=RoundingMode.HALF_EVEN,
            observed_at=Instant(value_ns=_BASE + 2 * _MINUTE),
            evidence_class=EvidenceClass.UNCONFIRMED,
        )
    )
    assert is_refusal(
        SlopedObject.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            anchor_points=[_point(0, 108_000), _point(1, 108_200)],
            evaluation_rule=_eval_rule(),
            target_scale=-1,
            rounding=RoundingMode.HALF_EVEN,
            observed_at=Instant(value_ns=_BASE + 2 * _MINUTE),
            evidence_class=EvidenceClass.UNCONFIRMED,
        )
    )
    assert is_refusal(
        SlopedObject.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            anchor_points=[_point(0, 108_000), _point(1, 108_200)],
            evaluation_rule=_eval_rule(),
            target_scale=5,
            rounding="nonsense",
            observed_at=Instant(value_ns=_BASE + 2 * _MINUTE),
            evidence_class=EvidenceClass.UNCONFIRMED,
        )
    )


def test_sloped_object_refuses_bad_family_rule_class_and_params() -> None:
    assert is_refusal(
        SlopedObject.try_create(
            family=object(),
            confirmation_rule=_rule(),
            anchor_points=[_point(0, 108_000), _point(1, 108_200)],
            evaluation_rule=_eval_rule(),
            target_scale=5,
            rounding=RoundingMode.HALF_EVEN,
            observed_at=Instant(value_ns=_BASE + 2 * _MINUTE),
            evidence_class=EvidenceClass.UNCONFIRMED,
        )
    )
    assert is_refusal(
        SlopedObject.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            anchor_points="not a sequence",
            evaluation_rule=_eval_rule(),
            target_scale=5,
            rounding=RoundingMode.HALF_EVEN,
            observed_at=Instant(value_ns=_BASE + 2 * _MINUTE),
            evidence_class=EvidenceClass.UNCONFIRMED,
        )
    )
    assert is_refusal(
        SlopedObject.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            anchor_points=[_point(0, 108_000), _point(1, 108_200)],
            evaluation_rule=_eval_rule(),
            target_scale=5,
            rounding=RoundingMode.HALF_EVEN,
            observed_at=Instant(value_ns=_BASE + 2 * _MINUTE),
            evidence_class="nonsense",
        )
    )
    assert is_refusal(
        SlopedObject.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            anchor_points=[_point(0, 108_000), _point(1, 108_200)],
            evaluation_rule=_eval_rule(),
            target_scale=5,
            rounding=RoundingMode.HALF_EVEN,
            observed_at=Instant(value_ns=_BASE + 2 * _MINUTE),
            evidence_class=EvidenceClass.UNCONFIRMED,
            parameters={"bad": 0.5},
        )
    )


def test_anchor_point_and_evaluation_rule_validations() -> None:
    assert is_refusal(AnchorPoint.try_create(0, _price(108_000)))
    assert is_refusal(AnchorPoint.try_create(Instant(value_ns=_BASE), 1))
    assert is_refusal(EvaluationRuleRef.try_create("", 1))
    assert is_refusal(EvaluationRuleRef.try_create("linear", 0))
    assert is_refusal(EvaluationRuleRef.try_create("linear", True))


def _calendar() -> CalendarIdentity:
    return _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2024a"), "calendar")


def _level(
    sampling: SamplingPolicy = SamplingPolicy.LAST_KNOWN_AT_OR_BEFORE,
) -> Result[CalendarAnchoredLevel]:
    return CalendarAnchoredLevel.try_create(
        family=_identity(),
        confirmation_rule=_rule(),
        calendar=_calendar(),
        sampling_policy=sampling,
        schedule_gap_policy=ScheduleGapPolicy.CARRY_PREVIOUS_SESSION,
        level=_price(108_500),
        observed_at=Instant(value_ns=_BASE),
        evidence_class=EvidenceClass.CONFIRMED,
    )


def test_calendar_anchored_level_is_a_standing_object_expressible() -> None:
    level = _unwrap(_level(), "calendar level")
    # A standing (a-priori) level declares observed_at = its configuration instant.
    assert level.observed_at == Instant(value_ns=_BASE)
    assert level.sampling_policy is SamplingPolicy.LAST_KNOWN_AT_OR_BEFORE
    assert level.schedule_gap_policy is ScheduleGapPolicy.CARRY_PREVIOUS_SESSION
    assert is_ok(level.content_fingerprint())


def test_calendar_level_policies_are_fingerprinted_surface() -> None:
    a = _unwrap(
        _unwrap(_level(SamplingPolicy.LAST_KNOWN_AT_OR_BEFORE), "a").content_fingerprint(), "fp a"
    )
    b = _unwrap(_unwrap(_level(SamplingPolicy.REFUSE), "b").content_fingerprint(), "fp b")
    assert a != b


def test_calendar_level_refuses_bad_construction() -> None:
    assert is_refusal(
        CalendarAnchoredLevel.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            calendar=object(),
            sampling_policy=SamplingPolicy.REFUSE,
            schedule_gap_policy=ScheduleGapPolicy.REFUSE,
            level=_price(108_500),
            observed_at=Instant(value_ns=_BASE),
            evidence_class=EvidenceClass.CONFIRMED,
        )
    )
    assert is_refusal(
        CalendarAnchoredLevel.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            calendar=_calendar(),
            sampling_policy="nonsense",
            schedule_gap_policy=ScheduleGapPolicy.REFUSE,
            level=_price(108_500),
            observed_at=Instant(value_ns=_BASE),
            evidence_class=EvidenceClass.CONFIRMED,
        )
    )
    assert is_refusal(
        CalendarAnchoredLevel.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            calendar=_calendar(),
            sampling_policy=SamplingPolicy.REFUSE,
            schedule_gap_policy="nonsense",
            level=_price(108_500),
            observed_at=Instant(value_ns=_BASE),
            evidence_class=EvidenceClass.CONFIRMED,
        )
    )
    assert is_refusal(
        CalendarAnchoredLevel.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            calendar=_calendar(),
            sampling_policy=SamplingPolicy.REFUSE,
            schedule_gap_policy=ScheduleGapPolicy.REFUSE,
            level=1,
            observed_at=Instant(value_ns=_BASE),
            evidence_class=EvidenceClass.CONFIRMED,
        )
    )
    assert is_refusal(
        CalendarAnchoredLevel.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            calendar=_calendar(),
            sampling_policy=SamplingPolicy.REFUSE,
            schedule_gap_policy=ScheduleGapPolicy.REFUSE,
            level=_price(108_500),
            observed_at="now",
            evidence_class=EvidenceClass.CONFIRMED,
        )
    )
    assert is_refusal(
        CalendarAnchoredLevel.try_create(
            family=object(),
            confirmation_rule=_rule(),
            calendar=_calendar(),
            sampling_policy=SamplingPolicy.REFUSE,
            schedule_gap_policy=ScheduleGapPolicy.REFUSE,
            level=_price(108_500),
            observed_at=Instant(value_ns=_BASE),
            evidence_class=EvidenceClass.CONFIRMED,
        )
    )
    assert is_refusal(
        CalendarAnchoredLevel.try_create(
            family=_identity(),
            confirmation_rule=object(),
            calendar=_calendar(),
            sampling_policy=SamplingPolicy.REFUSE,
            schedule_gap_policy=ScheduleGapPolicy.REFUSE,
            level=_price(108_500),
            observed_at=Instant(value_ns=_BASE),
            evidence_class=EvidenceClass.CONFIRMED,
        )
    )
    assert is_refusal(
        CalendarAnchoredLevel.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            calendar=_calendar(),
            sampling_policy=SamplingPolicy.REFUSE,
            schedule_gap_policy=ScheduleGapPolicy.REFUSE,
            level=_price(108_500),
            observed_at=Instant(value_ns=_BASE),
            evidence_class="nonsense",
        )
    )
    assert is_refusal(
        CalendarAnchoredLevel.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            calendar=_calendar(),
            sampling_policy=SamplingPolicy.REFUSE,
            schedule_gap_policy=ScheduleGapPolicy.REFUSE,
            level=_price(108_500),
            observed_at=Instant(value_ns=_BASE),
            evidence_class=EvidenceClass.CONFIRMED,
            parameters={"bad": 0.5},
        )
    )


def test_string_valued_policies_and_evidence_class_coerce() -> None:
    level = _unwrap(
        CalendarAnchoredLevel.try_create(
            family=_identity(),
            confirmation_rule=_rule(),
            calendar=_calendar(),
            sampling_policy="refuse",
            schedule_gap_policy="nearest-open-instant",
            level=_price(108_500),
            observed_at=Instant(value_ns=_BASE),
            evidence_class="confirmed",
        ),
        "string-policy level",
    )
    assert level.sampling_policy is SamplingPolicy.REFUSE
    assert level.schedule_gap_policy is ScheduleGapPolicy.NEAREST_OPEN_INSTANT
