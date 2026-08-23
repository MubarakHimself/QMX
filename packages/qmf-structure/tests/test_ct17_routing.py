"""Tier-1/Tier-2 tests for the CT-17 routing test and FM-6 indicator consumption (Story 9.4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from qmf.core import Fingerprint, Result, fingerprint, is_ok, is_refusal
from qmf.structure import RoutingKind, consume_indicator_input, route

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    assert is_ok(result), f"expected {what}, got {result}"
    return result.value


def test_route_classifies_a_value_per_instant_as_ct16() -> None:
    kind = _unwrap(
        route(value_per_evaluation_instant=True, discrete_with_birth_and_lifetime=False), "route"
    )
    assert kind is RoutingKind.VALUE_PER_INSTANT


def test_route_classifies_a_discrete_object_as_ct17() -> None:
    kind = _unwrap(
        route(value_per_evaluation_instant=False, discrete_with_birth_and_lifetime=True), "route"
    )
    assert kind is RoutingKind.DISCRETE_OBJECT


def test_route_refuses_a_concept_expressible_both_ways() -> None:
    result = route(value_per_evaluation_instant=True, discrete_with_birth_and_lifetime=True)
    assert is_refusal(result)
    assert result.category.value == "invalid input"


def test_route_refuses_a_concept_that_is_neither() -> None:
    assert is_refusal(
        route(value_per_evaluation_instant=False, discrete_with_birth_and_lifetime=False)
    )


def test_route_refuses_non_bool_properties() -> None:
    assert is_refusal(
        route(value_per_evaluation_instant="yes", discrete_with_birth_and_lifetime=False)
    )
    assert is_refusal(
        route(value_per_evaluation_instant=True, discrete_with_birth_and_lifetime="no")
    )


@dataclass(frozen=True)
class _Indicator:
    """A stand-in indicator result exposing the FM-6 declared-input seam."""

    result_fingerprint: object


def test_consume_indicator_input_returns_the_result_fingerprint() -> None:
    fp = _unwrap(fingerprint({"indicator": "ema-20"}), "indicator fp")
    consumed = _unwrap(consume_indicator_input(_Indicator(result_fingerprint=fp)), "consumed")
    assert consumed == fp


def test_consume_indicator_input_parses_a_string_fingerprint() -> None:
    fp = _unwrap(fingerprint({"indicator": "rsi-14"}), "indicator fp")
    consumed = _unwrap(consume_indicator_input(_Indicator(result_fingerprint=fp.value)), "consumed")
    assert isinstance(consumed, Fingerprint)
    assert consumed == fp


def test_consume_indicator_input_refuses_a_non_seam_and_a_bad_fingerprint() -> None:
    assert is_refusal(consume_indicator_input(object()))
    assert is_refusal(consume_indicator_input(_Indicator(result_fingerprint="not-an-fp")))
