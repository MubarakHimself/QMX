"""Tier-1/Tier-2 tests for the CT-17 light/heavy four-bound rule and benchmark gate (Story 9.4).

Covers FM-8/DEC-0128: the three structure rungs, a refused light claim, and a peak-memory
regression failing exactly as a slowdown does.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import Result, is_ok, is_refusal
from qmf.structure import (
    BenchmarkRung,
    DeclaredBudget,
    Measurement,
    check_regression,
    evaluate_light_claim,
)

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    assert is_ok(result), f"expected {what}, got {result}"
    return result.value


def _budget(*, synchronous: bool = True) -> DeclaredBudget:
    return _unwrap(
        DeclaredBudget.try_create(
            per_update_cost_ceiling_ns=1_000,
            object_set_size_ceiling=200,
            scan_window_ceiling=50,
            synchronous_available=synchronous,
        ),
        "budget",
    )


def test_rungs_are_the_three_structure_rungs() -> None:
    assert [rung.value for rung in BenchmarkRung] == [
        "active-object-set-size",
        "objects-minted-per-bar",
        "interaction-records-per-bar",
    ]


def test_light_claim_holds_when_all_bounds_are_proven_with_a_baseline() -> None:
    verdict = _unwrap(
        evaluate_light_claim(
            _budget(),
            per_update_cost_ns=500,
            object_set_size=100,
            scan_window=20,
            has_baseline=True,
        ),
        "light verdict",
    )
    assert verdict.light is True
    assert verdict.per_update_cost_ns == 500


def test_light_claim_is_refused_without_a_baseline() -> None:
    result = evaluate_light_claim(
        _budget(), per_update_cost_ns=500, object_set_size=100, scan_window=20, has_baseline=False
    )
    assert is_refusal(result)
    assert result.category.value == "policy rejection"


def test_light_claim_is_refused_when_not_synchronously_available() -> None:
    result = evaluate_light_claim(
        _budget(synchronous=False),
        per_update_cost_ns=500,
        object_set_size=100,
        scan_window=20,
        has_baseline=True,
    )
    assert is_refusal(result)


def test_light_claim_is_refused_when_a_bound_is_exceeded() -> None:
    for kwargs in (
        {"per_update_cost_ns": 2_000, "object_set_size": 100, "scan_window": 20},
        {"per_update_cost_ns": 500, "object_set_size": 300, "scan_window": 20},
        {"per_update_cost_ns": 500, "object_set_size": 100, "scan_window": 80},
    ):
        result = evaluate_light_claim(_budget(), has_baseline=True, **kwargs)
        assert is_refusal(result)
        assert result.category.value == "policy rejection"


def test_light_claim_refuses_bad_inputs() -> None:
    assert is_refusal(
        evaluate_light_claim(
            object(), per_update_cost_ns=1, object_set_size=1, scan_window=1, has_baseline=True
        )
    )
    assert is_refusal(
        evaluate_light_claim(
            _budget(), per_update_cost_ns=-1, object_set_size=1, scan_window=1, has_baseline=True
        )
    )
    assert is_refusal(
        evaluate_light_claim(
            _budget(), per_update_cost_ns=1, object_set_size="x", scan_window=1, has_baseline=True
        )
    )
    assert is_refusal(
        evaluate_light_claim(
            _budget(), per_update_cost_ns=1, object_set_size=1, scan_window=-1, has_baseline=True
        )
    )
    assert is_refusal(
        evaluate_light_claim(
            _budget(), per_update_cost_ns=1, object_set_size=1, scan_window=1, has_baseline="yes"
        )
    )


def test_declared_budget_refuses_bad_fields() -> None:
    assert is_refusal(
        DeclaredBudget.try_create(
            per_update_cost_ceiling_ns=-1,
            object_set_size_ceiling=1,
            scan_window_ceiling=1,
            synchronous_available=True,
        )
    )
    assert is_refusal(
        DeclaredBudget.try_create(
            per_update_cost_ceiling_ns=1,
            object_set_size_ceiling="x",
            scan_window_ceiling=1,
            synchronous_available=True,
        )
    )
    assert is_refusal(
        DeclaredBudget.try_create(
            per_update_cost_ceiling_ns=1,
            object_set_size_ceiling=1,
            scan_window_ceiling=-1,
            synchronous_available=True,
        )
    )
    assert is_refusal(
        DeclaredBudget.try_create(
            per_update_cost_ceiling_ns=1,
            object_set_size_ceiling=1,
            scan_window_ceiling=1,
            synchronous_available="yes",
        )
    )


def _baseline() -> Measurement:
    return Measurement(rung=BenchmarkRung.ACTIVE_OBJECT_SET_SIZE, seconds=1.0, peak_bytes=1_000)


def test_no_regression_passes() -> None:
    current = Measurement(rung=BenchmarkRung.ACTIVE_OBJECT_SET_SIZE, seconds=1.0, peak_bytes=1_000)
    verdict = _unwrap(check_regression(_baseline(), current, tolerance_bps=0), "regression verdict")
    assert verdict.regressed is False


def test_a_slowdown_fails_the_gate() -> None:
    current = Measurement(rung=BenchmarkRung.ACTIVE_OBJECT_SET_SIZE, seconds=2.0, peak_bytes=1_000)
    result = check_regression(_baseline(), current, tolerance_bps=0)
    assert is_refusal(result)
    assert result.category.value == "policy rejection"
    assert result.context["seconds_regressed"] is True
    assert result.context["memory_regressed"] is False


def test_a_peak_memory_regression_fails_exactly_as_a_slowdown_does() -> None:
    current = Measurement(rung=BenchmarkRung.ACTIVE_OBJECT_SET_SIZE, seconds=1.0, peak_bytes=2_000)
    result = check_regression(_baseline(), current, tolerance_bps=0)
    assert is_refusal(result)
    assert result.category.value == "policy rejection"
    assert result.context["memory_regressed"] is True
    assert result.context["seconds_regressed"] is False


def test_tolerance_allows_a_small_increase() -> None:
    current = Measurement(rung=BenchmarkRung.ACTIVE_OBJECT_SET_SIZE, seconds=1.05, peak_bytes=1_050)
    verdict = _unwrap(
        check_regression(_baseline(), current, tolerance_bps=1_000), "within-tolerance verdict"
    )
    assert verdict.regressed is False


def test_regression_refuses_bad_inputs_and_a_rung_mismatch() -> None:
    good = Measurement(rung=BenchmarkRung.ACTIVE_OBJECT_SET_SIZE, seconds=1.0, peak_bytes=1_000)
    assert is_refusal(check_regression(object(), good, tolerance_bps=0))
    assert is_refusal(check_regression(good, object(), tolerance_bps=0))
    assert is_refusal(check_regression(good, good, tolerance_bps=-1))
    mismatched = Measurement(
        rung=BenchmarkRung.OBJECTS_MINTED_PER_BAR, seconds=1.0, peak_bytes=1_000
    )
    result = check_regression(good, mismatched, tolerance_bps=0)
    assert is_refusal(result)
    assert result.category.value == "invalid input"
