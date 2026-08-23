"""Tier-1/Tier-2 tests for the first governed family — the swing-point family (Story 9.4).

Covers CT-17 FM-2 (precise confirmation rule), FM-1 (look-ahead safety), FM-9 (no
trading-school name), and DEC-0133 (no privilege over operator-authored families).
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    EvidenceClass,
    Instant,
    Instrument,
    Price,
    Result,
    TypedRefusal,
    VenueId,
    is_ok,
    is_refusal,
)
from qmf.structure import (
    SWING_POINT_CONFIRMATION_RULE,
    ConfirmationRecord,
    ConfirmationRule,
    DeclaredFamily,
    FamilyIdentity,
    HighLowObservation,
    StructureFamily,
    SwingKind,
    SwingPointFamily,
    admit_to_governed_library,
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


def _obs(index: int, high: int, low: int, close: int, symbol: str = "EURUSD") -> HighLowObservation:
    return _unwrap(
        HighLowObservation.try_create(
            Instant(value_ns=_BASE + index * _MINUTE),
            _price(high, symbol),
            _price(low, symbol),
            _price(close, symbol),
        ),
        "observation",
    )


def _series() -> list[HighLowObservation]:
    # A swing high at index 2 (h 108900 exceeds both neighbours) and a swing low at index 4
    # (l 107500 undercuts both neighbours), for a left=1/right=1 window.
    return [
        _obs(0, 108_100, 107_900, 108_000),
        _obs(1, 108_300, 108_000, 108_200),
        _obs(2, 108_900, 108_400, 108_600),
        _obs(3, 108_500, 108_100, 108_300),
        _obs(4, 108_450, 107_500, 107_600),
        _obs(5, 108_400, 108_000, 108_350),
    ]


def _family() -> SwingPointFamily:
    return _unwrap(
        SwingPointFamily.create(left=1, right=1, confirmation_delay_bound=3), "swing family"
    )


def test_swing_family_is_a_structure_family_with_a_precise_rule() -> None:
    family = _family()
    assert isinstance(family, StructureFamily)
    assert family.identity.geometry == "point"
    assert family.confirmation_rule.descriptor == SWING_POINT_CONFIRMATION_RULE
    assert family.confirmation_rule.confirmation_delay_bound == 3
    # A precise "confirmed the moment X happens" rule is admitted to the governed library (FM-2).
    assert is_ok(admit_to_governed_library(family))


def test_swing_family_holds_no_privilege_over_operator_families() -> None:
    # An operator-authored family is admitted through the identical gate — no special path.
    operator_identity = _unwrap(
        FamilyIdentity.try_create("operator-zone", 1, "zone"), "operator identity"
    )
    operator_rule = _unwrap(
        ConfirmationRule.try_create("confirmed the moment price trades through the zone edge"),
        "operator rule",
    )
    operator_family = _unwrap(
        DeclaredFamily.try_create(operator_identity, operator_rule), "operator family"
    )
    assert is_ok(admit_to_governed_library(_family()))
    assert is_ok(admit_to_governed_library(operator_family))


def test_swing_family_names_no_trading_school() -> None:
    banned = (
        "ict",
        "order block",
        "fair value",
        "wyckoff",
        "elliott",
        "fibonacci",
        "smart money",
        "liquidity grab",
        "supply and demand",
    )
    family = _family()
    haystack = " ".join(
        [
            family.identity.family_id,
            family.identity.geometry,
            family.confirmation_rule.descriptor,
            SWING_POINT_CONFIRMATION_RULE,
        ]
    ).lower()
    for token in banned:
        assert token not in haystack


def test_detect_mints_a_swing_high_and_a_swing_low() -> None:
    swings = _unwrap(_family().detect(_series()), "detected swings")
    kinds = sorted(swing.kind.value for swing in swings)
    assert kinds == ["high", "low"]
    for swing in swings:
        assert swing.object.evidence_class is EvidenceClass.UNCONFIRMED
        assert swing.object.family.geometry == "point"
        assert set(swing.object.parameters) == {"left", "right", "swing_high"}


def test_detected_pivot_is_observed_at_the_right_window_bar_not_earlier() -> None:
    # A swing high at index 2 is not derivable until its right-window bar (index 3) exists:
    # observed_at is that bar's instant, so a repainting / look-ahead mint is impossible (FM-1).
    swings = _unwrap(_family().detect(_series()), "detected swings")
    high = next(swing for swing in swings if swing.kind is SwingKind.HIGH)
    assert high.object.observed_at == Instant(value_ns=_BASE + 3 * _MINUTE)
    # The anchor is a point frozen at the pivot bar (index 2), permitted to precede observed_at.
    assert high.object.anchor.start == Instant(value_ns=_BASE + 2 * _MINUTE)
    assert high.object.anchor.start == high.object.anchor.end


def test_swing_direction_flag_distinguishes_high_from_low() -> None:
    swings = _unwrap(_family().detect(_series()), "detected swings")
    high = next(swing for swing in swings if swing.kind is SwingKind.HIGH)
    low = next(swing for swing in swings if swing.kind is SwingKind.LOW)
    assert high.object.parameters["swing_high"].numerator == 1
    assert low.object.parameters["swing_high"].numerator == 0


def test_confirmation_fires_the_moment_a_later_bar_closes_beyond_the_break_level() -> None:
    family = _family()
    swings = _unwrap(family.detect(_series()), "detected swings")
    high = next(swing for swing in swings if swing.kind is SwingKind.HIGH)
    # Bar 4 closes at 107600, below the pivot bar's low (108400) — the confirming instant.
    record = _unwrap(family.confirmation_for(high, _series()), "confirmation")
    assert isinstance(record, ConfirmationRecord)
    assert record.at == Instant(value_ns=_BASE + 4 * _MINUTE)


def test_confirmation_returns_none_when_no_later_bar_confirms() -> None:
    family = _family()
    swings = _unwrap(family.detect(_series()), "detected swings")
    low = next(swing for swing in swings if swing.kind is SwingKind.LOW)
    # The low is observed at the last bar; nothing later in the series closes above its high.
    assert _unwrap(family.confirmation_for(low, _series()), "no confirmation") is None
    # A later bar closing above the break level does confirm it.
    later = [_obs(6, 108_700, 108_500, 108_600)]
    record = _unwrap(family.confirmation_for(low, later), "later confirmation")
    assert isinstance(record, ConfirmationRecord)
    assert record.at == Instant(value_ns=_BASE + 6 * _MINUTE)


def test_confirmation_respects_the_declared_delay_bound() -> None:
    family = _unwrap(
        SwingPointFamily.create(left=1, right=1, confirmation_delay_bound=1), "tight family"
    )
    swings = _unwrap(family.detect(_series()), "detected swings")
    high = next(swing for swing in swings if swing.kind is SwingKind.HIGH)
    # With a bound of 1, only bar 4 is examined (it confirms) — extend the gap to blow the bound.
    gapped = [_obs(10, 108_800, 108_600, 108_700), _obs(11, 108_300, 108_100, 108_200)]
    # bar 10 does not close below 108400; bar 11 would, but is beyond the 1-observation bound.
    assert _unwrap(family.confirmation_for(high, gapped), "bounded confirmation") is None


def test_detect_refuses_a_non_monotonic_series() -> None:
    out_of_order = [_obs(2, 108_900, 108_400, 108_600), _obs(1, 108_300, 108_000, 108_200)]
    result = _family().detect(out_of_order)
    assert is_refusal(result)
    assert result.category.value == "invalid input"


def test_detect_refuses_a_mixed_instrument_series() -> None:
    mixed = [
        _obs(0, 108_100, 107_900, 108_000),
        _obs(1, 108_300, 108_000, 108_200, symbol="GBPUSD"),
        _obs(2, 108_900, 108_400, 108_600),
    ]
    result = _family().detect(mixed)
    assert is_refusal(result)


def test_detect_refuses_a_bare_string_and_a_bad_element() -> None:
    assert is_refusal(_family().detect("not a sequence"))
    assert is_refusal(_family().detect([_obs(0, 108_100, 107_900, 108_000), object()]))


def test_create_refuses_bad_window_sizes_and_bound() -> None:
    assert is_refusal(SwingPointFamily.create(left=0, right=1, confirmation_delay_bound=3))
    assert is_refusal(SwingPointFamily.create(left=1, right=-1, confirmation_delay_bound=3))
    assert is_refusal(SwingPointFamily.create(left=1, right=1, confirmation_delay_bound=-1))
    # An unbounded family is legal (None bound) — for families excluded from split evidence.
    assert is_ok(SwingPointFamily.create(left=1, right=1, confirmation_delay_bound=None))


def test_confirmation_for_refuses_a_non_swing_pivot_and_bad_inputs() -> None:
    family = _family()
    assert is_refusal(family.confirmation_for(object(), _series()))
    swings = _unwrap(family.detect(_series()), "detected swings")
    assert is_refusal(family.confirmation_for(swings[0], "not a sequence"))


def test_high_low_observation_validations() -> None:
    good = HighLowObservation.try_create(
        Instant(value_ns=_BASE), _price(108_500), _price(108_000), _price(108_200)
    )
    assert is_ok(good)
    # low > high
    assert is_refusal(
        HighLowObservation.try_create(
            Instant(value_ns=_BASE), _price(108_000), _price(108_500), _price(108_200)
        )
    )
    # close outside [low, high]
    assert is_refusal(
        HighLowObservation.try_create(
            Instant(value_ns=_BASE), _price(108_500), _price(108_000), _price(109_000)
        )
    )
    # non-Instant instant
    assert is_refusal(
        HighLowObservation.try_create(0, _price(108_500), _price(108_000), _price(108_200))
    )
    # non-Price field
    assert is_refusal(
        HighLowObservation.try_create(Instant(value_ns=_BASE), 1, _price(108_000), _price(108_200))
    )
    # mixed instrument
    other = Price.try_create(
        108_200, Instrument(venue=VenueId(value="ctrader"), symbol="GBPUSD"), 5
    )
    assert is_ok(other)
    assert is_refusal(
        HighLowObservation.try_create(
            Instant(value_ns=_BASE), _price(108_500), _price(108_000), other.value
        )
    )


def test_detect_on_empty_series_finds_nothing() -> None:
    assert _unwrap(_family().detect([]), "empty detect") == ()


def test_refusals_are_returned_never_raised() -> None:
    result = _family().detect(42)
    assert isinstance(result, TypedRefusal)
