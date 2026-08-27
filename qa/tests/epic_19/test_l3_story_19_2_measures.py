"""L3 acceptance — Story 19.2: the ordered, unit-kinded, exact measure set.

Requirements R8, R11, R13. The set is ordered and unit-kinded, each metric's
arithmetic is pinned by its own format version, and no composite score/verdict is
ever stored (DEC-0162 — the negative Epic 19 owns).
"""

from __future__ import annotations

import json

import pytest

from conftest import UNIT_KIND_VALUES, config, interval, mint_args, money, ok

from qmf.core.refusal import is_ok
from qmf.risk.performance import PerformanceMeasure, PerformanceResult, UndefinedMeasure
from qmb.results.ct32 import mint_run_performance_result
from qmb.results.measures import MEASURE_IDENTITIES, emit_measure

# The V1 core roster the AC enumerates must all be present, by identity.
EXPECTED_CORE = {
    "net_profit", "cagr", "start_equity", "end_equity", "sharpe_ratio", "sortino_ratio",
    "calmar_ratio", "max_drawdown", "max_drawdown_recovery", "total_trades",
    "winning_trades", "losing_trades", "win_rate", "long_win_rate", "short_win_rate",
    "profit_factor", "expectancy", "average_win", "average_loss", "largest_win",
    "largest_loss", "gross_profit", "gross_loss", "fees", "winning_streak", "losing_streak",
}

# DEC-0162 / R-RPT-10 forbid any of these expressing a result.
FORBIDDEN = ("score", "grade", "tier", "weighted", "rating", "composite", "verdict")


def _mint() -> PerformanceResult:
    return ok(mint_run_performance_result(**mint_args(config())))


def _all_strings_and_keys(value: object) -> list[str]:
    out: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            out.append(str(key))
            out.extend(_all_strings_and_keys(item))
    elif isinstance(value, list):
        for item in value:
            out.extend(_all_strings_and_keys(item))
    elif isinstance(value, str):
        out.append(value)
    return out


# --- A8: ordered measure set, non-null AD-40 unit-kind, V1 core [R8] P0 -------


def test_a8_measure_set_is_ordered_and_covers_the_v1_core() -> None:
    artifact = _mint()
    order = [row.measure_identity for row in artifact.measure_set]
    # ordered exactly as the pinned roster — not a set, not collapsed
    assert order == list(MEASURE_IDENTITIES)
    assert EXPECTED_CORE.issubset(set(order))


def test_a8_every_computed_measure_carries_a_non_null_unit_kind() -> None:
    artifact = _mint()
    for row in artifact.measure_set:
        if isinstance(row, PerformanceMeasure):
            assert row.quantity.unit_kind is not None
            assert row.quantity.unit_kind.value in UNIT_KIND_VALUES
        else:
            # the alternative to a unit-kinded measure is a typed refusal slot,
            # never a bare number without a unit-kind
            assert isinstance(row, UndefinedMeasure)


# --- A9: metric_contract_format_version pins arithmetic [R11] P1 -------------


def test_a9_a_metric_format_version_change_moves_that_metric_identity() -> None:
    v1 = ok(emit_measure("net_profit", money(1234), 1, unit_kind="money(currency)"))
    v2 = ok(emit_measure("net_profit", money(1234), 2, unit_kind="money(currency)"))
    # same identity + same quantity, different pinned arithmetic version =>
    # a DIFFERENT measure identity content (an arithmetic change is a mint).
    assert v1.metric_contract_format_version == 1
    assert v2.metric_contract_format_version == 2
    assert v1.fp1_identity() != v2.fp1_identity()
    assert v1.fp1_identity()["metric_contract_format_version"] == 1
    assert v2.fp1_identity()["metric_contract_format_version"] == 2


def test_a9_every_stored_measure_pins_its_format_version() -> None:
    artifact = _mint()
    for row in artifact.measure_set:
        assert isinstance(row.metric_contract_format_version, int)
        assert row.metric_contract_format_version >= 1
        assert "metric_contract_format_version" in row.fp1_identity()


# --- A10: no composite score/verdict anywhere [R13] P0 -----------------------


def test_a10_no_composite_or_verdict_token_anywhere_in_artifact() -> None:
    # Falsifiability: the scanner flags a planted composite key/value.
    planted = _all_strings_and_keys({"quality_score": 7, "band": "gold"})
    assert any("score" in s.casefold() for s in planted)

    body = json.loads(json.dumps(_mint().fp1_identity()))
    tokens = [s.casefold() for s in _all_strings_and_keys(body)]
    for forbidden in FORBIDDEN:
        assert not any(forbidden in s for s in tokens), forbidden


def test_a10_the_set_is_not_collapsed_into_one_number() -> None:
    artifact = _mint()
    # the artifact presents the full ordered set (27 members), never a single
    # collapsed rating.
    assert len(artifact.measure_set) == len(MEASURE_IDENTITIES)
    assert len(artifact.measure_set) > 1
    # no top-level scalar verdict field on the container identity
    top = _mint().fp1_identity()
    assert "score" not in top and "verdict" not in top and "rating" not in top


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
