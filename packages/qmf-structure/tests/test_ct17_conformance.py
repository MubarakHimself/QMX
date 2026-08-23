"""The CT-17 conformance harness (Story 9.4).

Binds to CT-17's concept-walk register (``qmf.structure.conformance.CONCEPT_WALK_REGISTER``)
and proves each item stays **expressible** on the public CT-17 surface — the tier-2
conformance suite of DEC-0131/DEC-0102. Each register member has exactly one builder that
constructs the concept from points, zones, levels, distributions, composites, sloped objects,
calendar-anchored levels, the append-only lifecycle, refits, and the result label. If any item
becomes inexpressible, or the register and the suite drift apart, the gate fails.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from qmf.core import (
    CalendarIdentity,
    EvidenceClass,
    ExactRational,
    Fingerprint,
    Instant,
    Instrument,
    Price,
    Result,
    RoundingMode,
    UnitKind,
    VenueId,
    World,
    is_ok,
)
from qmf.structure import (
    CONCEPT_WALK_REGISTER,
    AnchorPoint,
    AnchorSpan,
    CalendarAnchoredLevel,
    CompositeChild,
    CompositeObject,
    ConceptWalkItem,
    ConfirmationRule,
    DeclaredFamily,
    EvaluationRuleRef,
    FamilyIdentity,
    InteractionRecord,
    InvalidationRecord,
    SamplingPolicy,
    ScheduleGapPolicy,
    SlopedObject,
    StructureObject,
    refit,
    resolve_state,
    structure_result_label,
)

T = TypeVar("T")
_MINUTE = 60_000_000_000
_BASE = 1_700_000_000_000_000_000


def _ok(result: Result[T], what: str) -> T:
    assert is_ok(result), f"expected {what} to be expressible, got {result}"
    return result.value


def _instrument(symbol: str = "EURUSD") -> Instrument:
    return Instrument(venue=VenueId(value="ctrader"), symbol=symbol)


def _price(value: int, symbol: str = "EURUSD") -> Price:
    return _ok(Price.try_create(value, _instrument(symbol), 5), "price")


def _at(minute: int) -> Instant:
    return Instant(value_ns=_BASE + minute * _MINUTE)


def _family(
    family_id: str, geometry: str, descriptor: str, bound: int | None = 2
) -> DeclaredFamily:
    identity = _ok(FamilyIdentity.try_create(family_id, 1, geometry), "identity")
    rule = _ok(ConfirmationRule.try_create(descriptor, confirmation_delay_bound=bound), "rule")
    return _ok(DeclaredFamily.try_create(identity, rule), "family")


def _ratio(numerator: int, denominator: int = 1) -> ExactRational:
    return _ok(
        ExactRational.try_create(numerator, denominator, UnitKind.DIMENSIONLESS_RATIO), "ratio"
    )


def _object(
    *,
    family: DeclaredFamily,
    low: int,
    high: int,
    anchor_start_min: int,
    anchor_end_min: int,
    observed_min: int,
    evidence: EvidenceClass = EvidenceClass.UNCONFIRMED,
    params: dict[str, ExactRational] | None = None,
    symbol: str = "EURUSD",
) -> StructureObject:
    anchor = _ok(
        AnchorSpan.try_create(
            _at(anchor_start_min), _at(anchor_end_min), _price(low, symbol), _price(high, symbol)
        ),
        "anchor",
    )
    return _ok(
        StructureObject.try_create(family, params or {}, anchor, _at(observed_min), evidence),
        "structure object",
    )


def _fingerprint(obj: StructureObject) -> Fingerprint:
    return _ok(obj.content_fingerprint(), "fingerprint")


def _calendar() -> CalendarIdentity:
    return _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2024a"), "calendar")


def _standing_level(family_id: str, level: int) -> CalendarAnchoredLevel:
    return _ok(
        CalendarAnchoredLevel.try_create(
            family=_family(
                family_id, "level", "confirmed the moment price touches the level"
            ).identity,
            confirmation_rule=_family(
                family_id, "level", "confirmed the moment price touches the level"
            ).confirmation_rule,
            calendar=_calendar(),
            sampling_policy=SamplingPolicy.LAST_KNOWN_AT_OR_BEFORE,
            schedule_gap_policy=ScheduleGapPolicy.CARRY_PREVIOUS_SESSION,
            level=_price(level),
            observed_at=_at(0),
            evidence_class=EvidenceClass.CONFIRMED,
        ),
        "calendar-anchored level",
    )


def _child(
    ref: Fingerprint, observed_min: int, confirmed_min: int | None, bound: int | None
) -> CompositeChild:
    return _ok(
        CompositeChild.try_create(
            ref,
            _at(observed_min),
            confirmed_at=None if confirmed_min is None else _at(confirmed_min),
            confirmation_delay_bound=bound,
        ),
        "composite child",
    )


# --- one builder per concept-walk register item -----------------------------


def _retro_anchored_zone_with_consumption_state() -> None:
    # A zone whose anchor precedes observed_at (retro-anchored), its consumption state read as
    # a fold over an appended interaction record — never a stored field.
    family = _family("demand-zone", "zone", "confirmed the moment price returns to the zone")
    zone = _object(
        family=family,
        low=107_900,
        high=108_100,
        anchor_start_min=0,
        anchor_end_min=1,
        observed_min=5,
    )
    consumption = _ok(
        InteractionRecord.try_create(
            _fingerprint(zone), _at(9), _price(108_000), "consumed_fraction", _ratio(1, 2)
        ),
        "consumption record",
    )
    state = _ok(resolve_state(zone, [consumption], at=_at(10)), "resolved consumption state")
    assert len(state.interactions) == 1


def _object_born_from_invalidation() -> None:
    # A child object whose observed_at is the parent's invalidation instant, consuming the
    # parent's invalidation record fingerprint as a lineage input.
    parent = _object(
        family=_family(
            "break-level", "level", "confirmed the moment a bar closes beyond the level"
        ),
        low=108_500,
        high=108_500,
        anchor_start_min=0,
        anchor_end_min=1,
        observed_min=2,
    )
    invalidation = _ok(
        InvalidationRecord.try_create(_fingerprint(parent), _at(6)), "invalidation record"
    )
    child = _object(
        family=_family(
            "post-break", "level", "confirmed the moment price retests the broken level"
        ),
        low=108_400,
        high=108_400,
        anchor_start_min=6,
        anchor_end_min=6,
        observed_min=6,
    )
    label = _ok(
        structure_result_label(
            child,
            world=World.LIVE,
            input_fingerprints=[_ok(invalidation.content_fingerprint(), "invalidation fp")],
        ),
        "born-from-invalidation label",
    )
    assert child.observed_at == invalidation.at
    assert label.input_fingerprints


def _cluster_over_tolerance_grouped_extremes() -> None:
    extremes = [
        _object(
            family=_family("extreme", "point", "confirmed the moment the extreme prints"),
            low=108_000 + offset,
            high=108_000 + offset,
            anchor_start_min=offset,
            anchor_end_min=offset,
            observed_min=offset + 1,
        )
        for offset in (0, 1, 2)
    ]
    children = [
        _child(_fingerprint(obj), offset + 1, offset + 2, 2) for offset, obj in enumerate(extremes)
    ]
    cluster = _ok(
        CompositeObject.try_create(
            family=_ok(FamilyIdentity.try_create("cluster", 1, "graph"), "identity"),
            confirmation_rule=_ok(
                ConfirmationRule.try_create(
                    "confirmed the moment every clustered extreme confirms",
                    confirmation_delay_bound=2,
                ),
                "rule",
            ),
            children=children,
            evidence_class=EvidenceClass.CONFIRMED,
            parameters={"tolerance": _ratio(1, 4)},
        ),
        "tolerance cluster",
    )
    assert len(cluster.children) == 3


def _threshold_breach_then_reversal() -> None:
    family = _family(
        "breach-reversal",
        "point",
        "confirmed the moment price breaches the threshold and then a bar closes back across it",
    )
    obj = _object(
        family=family,
        low=108_500,
        high=108_500,
        anchor_start_min=0,
        anchor_end_min=1,
        observed_min=2,
    )
    breach = _ok(
        InteractionRecord.try_create(
            _fingerprint(obj), _at(3), _price(108_700), "breach", _ratio(1)
        ),
        "breach record",
    )
    reversal = _ok(
        InteractionRecord.try_create(
            _fingerprint(obj), _at(4), _price(108_400), "reversal", _ratio(1)
        ),
        "reversal record",
    )
    state = _ok(resolve_state(obj, [breach, reversal], at=_at(5)), "breach-reversal state")
    assert len(state.interactions) == 2


def _ordered_multi_phase_calendar_composite() -> None:
    phases = [_standing_level("session-open", 108_000), _standing_level("session-mid", 108_200)]
    children = [_child(_ok(phase.content_fingerprint(), "phase fp"), 0, 0, 1) for phase in phases]
    composite = _ok(
        CompositeObject.try_create(
            family=_ok(FamilyIdentity.try_create("session-phases", 1, "graph"), "identity"),
            confirmation_rule=_ok(
                ConfirmationRule.try_create(
                    "confirmed the moment the final phase confirms", confirmation_delay_bound=1
                ),
                "rule",
            ),
            children=children,
            evidence_class=EvidenceClass.CONFIRMED,
            ordered=True,
        ),
        "ordered calendar composite",
    )
    assert composite.ordered is True


def _multi_barspec_nest() -> None:
    # Children observed on different BarSpecs nest into one composite; the BarSpec is a property
    # of each child, and the composite holds them by fingerprint regardless.
    coarse = _object(
        family=_family(
            "htf-swing", "point", "confirmed the moment the higher-timeframe pivot prints"
        ),
        low=108_900,
        high=108_900,
        anchor_start_min=0,
        anchor_end_min=1,
        observed_min=2,
    )
    fine = _object(
        family=_family(
            "ltf-swing", "point", "confirmed the moment the lower-timeframe pivot prints"
        ),
        low=108_100,
        high=108_100,
        anchor_start_min=0,
        anchor_end_min=0,
        observed_min=1,
    )
    composite = _ok(
        CompositeObject.try_create(
            family=_ok(FamilyIdentity.try_create("nest", 1, "graph"), "identity"),
            confirmation_rule=_ok(
                ConfirmationRule.try_create(
                    "confirmed the moment both nested pivots confirm", confirmation_delay_bound=2
                ),
                "rule",
            ),
            children=[_child(_fingerprint(coarse), 2, 3, 2), _child(_fingerprint(fine), 1, 2, 1)],
            evidence_class=EvidenceClass.CONFIRMED,
        ),
        "multi-barspec nest",
    )
    assert len(composite.children) == 2


def _cross_instrument_divergence() -> None:
    left = _object(
        family=_family("eur-swing", "point", "confirmed the moment the pivot prints"),
        low=108_900,
        high=108_900,
        anchor_start_min=0,
        anchor_end_min=1,
        observed_min=2,
        symbol="EURUSD",
    )
    right = _object(
        family=_family("gbp-swing", "point", "confirmed the moment the pivot prints"),
        low=126_500,
        high=126_500,
        anchor_start_min=0,
        anchor_end_min=1,
        observed_min=2,
        symbol="GBPUSD",
    )
    divergence = _ok(
        CompositeObject.try_create(
            family=_ok(FamilyIdentity.try_create("divergence", 1, "graph"), "identity"),
            confirmation_rule=_ok(
                ConfirmationRule.try_create(
                    "confirmed the moment the two instruments' pivots both confirm",
                    confirmation_delay_bound=2,
                ),
                "rule",
            ),
            children=[_child(_fingerprint(left), 2, 3, 1), _child(_fingerprint(right), 2, 3, 1)],
            evidence_class=EvidenceClass.CONFIRMED,
        ),
        "cross-instrument divergence",
    )
    assert len(divergence.children) == 2


def _distribution_over_price() -> None:
    # A distribution-over-price object: geometry "distribution", parameters keyed by price bin.
    family = _family("volume-profile", "distribution", "confirmed the moment the session closes")
    obj = _object(
        family=family,
        low=108_000,
        high=108_500,
        anchor_start_min=0,
        anchor_end_min=5,
        observed_min=6,
        evidence=EvidenceClass.CONFIRMED,
        params={"bin_108000": _ratio(3), "bin_108250": _ratio(9), "bin_108500": _ratio(4)},
    )
    assert obj.family.geometry == "distribution"
    assert len(obj.parameters) == 3


def _a_priori_price_grid() -> None:
    # A grid of standing (a-priori) levels, each observed at its configuration instant, nested
    # into one grid composite.
    grid_levels = [_standing_level(f"grid-{step}", 108_000 + step * 100) for step in range(3)]
    children = [
        _child(_ok(level.content_fingerprint(), "grid fp"), 0, 0, 0) for level in grid_levels
    ]
    grid = _ok(
        CompositeObject.try_create(
            family=_ok(FamilyIdentity.try_create("price-grid", 1, "graph"), "identity"),
            confirmation_rule=_ok(
                ConfirmationRule.try_create(
                    "confirmed the moment the grid is configured", confirmation_delay_bound=0
                ),
                "rule",
            ),
            children=children,
            evidence_class=EvidenceClass.CONFIRMED,
        ),
        "a-priori price grid",
    )
    assert grid.observed_at == _at(0)


def _projected_level() -> None:
    projected = _ok(
        SlopedObject.try_create(
            family=_ok(FamilyIdentity.try_create("trendline", 1, "level"), "identity"),
            confirmation_rule=_ok(
                ConfirmationRule.try_create("confirmed the moment price touches the projection"),
                "rule",
            ),
            anchor_points=[
                _ok(AnchorPoint.try_create(_at(0), _price(108_000)), "p0"),
                _ok(AnchorPoint.try_create(_at(2), _price(108_200)), "p1"),
            ],
            evaluation_rule=_ok(EvaluationRuleRef.try_create("linear-two-point", 1), "eval rule"),
            target_scale=5,
            rounding=RoundingMode.HALF_EVEN,
            observed_at=_at(2),
            evidence_class=EvidenceClass.UNCONFIRMED,
        ),
        "projected level",
    )
    assert not hasattr(projected, "slope")  # slope is derived, never stored


def _pattern_refit() -> None:
    prior = _object(
        family=_family("pattern", "zone", "confirmed the moment the pattern completes"),
        low=108_000,
        high=108_200,
        anchor_start_min=0,
        anchor_end_min=1,
        observed_min=2,
    )
    new_anchor = _ok(
        AnchorSpan.try_create(_at(0), _at(1), _price(108_050), _price(108_250)), "refit anchor"
    )
    result = _ok(refit(prior, anchor=new_anchor, observed_at=_at(3)), "pattern refit")
    assert result.supersedes_edge.to_ref == _fingerprint(prior)


_BUILDERS: dict[ConceptWalkItem, Callable[[], None]] = {
    ConceptWalkItem.RETRO_ANCHORED_ZONES: _retro_anchored_zone_with_consumption_state,
    ConceptWalkItem.BORN_FROM_INVALIDATION: _object_born_from_invalidation,
    ConceptWalkItem.TOLERANCE_CLUSTERS: _cluster_over_tolerance_grouped_extremes,
    ConceptWalkItem.THRESHOLD_BREACH_REVERSAL: _threshold_breach_then_reversal,
    ConceptWalkItem.CALENDAR_COMPOSITES: _ordered_multi_phase_calendar_composite,
    ConceptWalkItem.MULTI_BARSPEC_NESTS: _multi_barspec_nest,
    ConceptWalkItem.CROSS_INSTRUMENT_DIVERGENCE: _cross_instrument_divergence,
    ConceptWalkItem.DISTRIBUTION_OVER_PRICE: _distribution_over_price,
    ConceptWalkItem.A_PRIORI_PRICE_GRIDS: _a_priori_price_grid,
    ConceptWalkItem.PROJECTED_LEVELS: _projected_level,
    ConceptWalkItem.PATTERN_REFITS: _pattern_refit,
}


def test_every_register_item_has_a_builder_and_none_extra() -> None:
    # The suite binds to the register: neither may drift from the other.
    assert set(_BUILDERS) == set(CONCEPT_WALK_REGISTER)
    assert len(CONCEPT_WALK_REGISTER) == 11


def test_the_whole_concept_walk_register_stays_expressible() -> None:
    for item in CONCEPT_WALK_REGISTER:
        _BUILDERS[item]()  # each constructs from the public CT-17 surface, or fails the gate


def test_register_values_match_ct17_conformance_register() -> None:
    assert ConceptWalkItem.PROJECTED_LEVELS.value == "projected levels"
    assert ConceptWalkItem.PATTERN_REFITS.value == "pattern refits"
    assert (
        ConceptWalkItem.CROSS_INSTRUMENT_DIVERGENCE.value == "cross-instrument divergence objects"
    )
