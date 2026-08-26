"""Story 21.6 — anti-overfit parameter-sensitivity report over a completed Study."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from fractions import Fraction
from typing import TypeVar, cast

from qmb._refuse import unavailable
from qmb.ledger import LedgerLine
from qmb.optimize import (
    EXCLUDED_REASONS,
    REPORT_INVENTS_THRESHOLD,
    REPORT_MAKES_EDGE_CLAIM,
    REPORT_MAKES_SEARCH_QUALITY_VERDICT,
    SENSITIVITY_CANONICAL_PAYLOAD,
    SENSITIVITY_OBJECTIVE_UNDEFINED,
    SENSITIVITY_REPORT_CLASS,
    SENSITIVITY_STAT_DDOF,
    SENSITIVITY_STAT_SCALE,
    SENSITIVITY_TRIAL_REFUSED,
    SENSITIVITY_UNMAPPED,
    STABILITY_ISOLATED_SPIKE,
    STABILITY_NO_WINNER,
    STABILITY_STABLE_CLUSTER,
    WINNER_STABILITIES,
    ObjectiveDistribution,
    SensitivityReport,
    build_sensitivity_report,
    refuse_search_quality_verdict,
    sensitivity_identity,
)
from qmb.results import emit_measure
from qmf.core.exact import ExactRational, Money, UnitKind
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.risk.performance import UndefinedMeasure

T = TypeVar("T")

_BAR = fingerprint({"class": "book-bar", "id": "bar-1"})


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _fp(*parts: object) -> Fingerprint:
    return _ok(fingerprint({"parts": list(parts)}))


def _net_profit(minor: int) -> dict[str, object]:
    measure = _ok(emit_measure("net_profit", Money(value=minor, currency="USD", scale=2)))
    return measure.fp1_identity()


def _max_drawdown(num: int, den: int) -> dict[str, object]:
    quantity = _ok(ExactRational.try_create(num, den, UnitKind.DIMENSIONLESS_RATIO))
    return _ok(emit_measure("max_drawdown", quantity)).fp1_identity()


def _undefined(identity: str) -> dict[str, object]:
    refusal = unavailable(identity, "insufficient sample", code="undefined")
    return _ok(UndefinedMeasure.try_create(identity, 1, refusal)).fp1_identity()


def _trial(
    run: str,
    *,
    measures: tuple[dict[str, object], ...],
    world: World = World.REPLAY,
    role: str = "trial",
) -> LedgerLine:
    return LedgerLine(
        run_id=_fp("run", run),
        role=role,
        world=world,
        result_label={"class": "result-label", "world": world.value, "run": run},
        book_bar_fp1=_ok(_BAR),
        measures=measures,
        ct32_fingerprint=_fp("ct32", run),
    )


def _aborted(run: str) -> LedgerLine:
    return LedgerLine(
        run_id=_fp("run", run),
        role="aborted",
        world=World.REPLAY,
        result_label={"class": "result-label", "world": World.REPLAY.value, "run": run},
        book_bar_fp1=_ok(_BAR),
        measures=(),
        ct32_fingerprint=None,
        refusal={"category": "invalid input", "field": "terminal", "reason": "trial refused"},
    )


def _run_id(run: str) -> str:
    return _fp("run", run).value


def _profit_trial(
    run: str, minor: int, fast: int, slow: int
) -> tuple[LedgerLine, dict[str, object]]:
    line = _trial(run, measures=(_net_profit(minor),))
    return line, {"fast": fast, "slow": slow}


def _report(
    lines: list[LedgerLine],
    parameters: Mapping[str, Mapping[str, object]],
    **kwargs: object,
) -> SensitivityReport:
    return _ok(
        build_sensitivity_report(
            lines,
            parameters=parameters,
            objective=kwargs.get("objective", "net_profit"),
            world=World.REPLAY,
            direction=kwargs.get("direction", "max"),
            neighbourhood_size=kwargs.get("neighbourhood_size"),
        )
    )


def _has_float(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, float):
        return True
    if isinstance(value, dict):
        return any(_has_float(item) for item in cast("dict[object, object]", value).values())
    if isinstance(value, (list, tuple)):
        return any(_has_float(item) for item in cast("Sequence[object]", value))
    return False


# --- AC1: objective distribution summary + per-parameter slices ---------------


def test_report_summarizes_objective_over_all_completed_trial_lines() -> None:
    lines: list[LedgerLine] = []
    params: dict[str, dict[str, object]] = {}
    for run, minor, fast in (("a", 100, 10), ("b", 200, 11), ("c", 300, 12)):
        line, assignment = _profit_trial(run, minor, fast, 20)
        lines.append(line)
        params[_run_id(run)] = assignment
    report = _report(lines, params)
    distribution = report.distribution
    assert distribution is not None
    assert distribution.count == 3
    # objective magnitudes are 1, 2, 3 (dollars), reconstructed exact from exact Money.
    assert distribution.mean == Fraction(2)
    assert distribution.minimum == Fraction(1)
    assert distribution.maximum == Fraction(3)
    assert distribution.median == Fraction(2)
    assert distribution.unit_kind == UnitKind.MONEY.value
    assert distribution.currency == "USD"


def test_distribution_std_matches_population_deviation() -> None:
    lines: list[LedgerLine] = []
    params: dict[str, dict[str, object]] = {}
    for run, minor in (("a", 100), ("b", 200), ("c", 300)):
        line, assignment = _profit_trial(run, minor, 10, 20)
        lines.append(line)
        params[_run_id(run)] = assignment
    distribution = _report(lines, params).distribution
    assert distribution is not None
    # population variance of {1,2,3} is 2/3; std ~ 0.816496...
    assert abs(float(distribution.std) - math.sqrt(Fraction(2, 3))) < 1e-9
    assert distribution.std_scale == SENSITIVITY_STAT_SCALE
    assert distribution.std_rounding == "half-even"
    assert SENSITIVITY_STAT_DDOF == 0


def test_single_trial_group_has_zero_std() -> None:
    line, assignment = _profit_trial("a", 100, 10, 20)
    distribution = _report([line], {_run_id("a"): assignment}).distribution
    assert distribution is not None
    assert distribution.count == 1
    assert distribution.std == Fraction(0)


def test_per_parameter_slices_group_objective_by_value() -> None:
    lines: list[LedgerLine] = []
    params: dict[str, dict[str, object]] = {}
    rows = (("a", 100, 10, 20), ("b", 300, 10, 21), ("c", 200, 11, 20))
    for run, minor, fast, slow in rows:
        line, _ = _profit_trial(run, minor, fast, slow)
        lines.append(line)
        params[_run_id(run)] = {"fast": fast, "slow": slow}
    report = _report(lines, params)
    slices = {item.parameter: item for item in report.parameter_slices}
    assert set(slices) == {"fast", "slow"}
    fast_slice = slices["fast"]
    # fast=10 groups runs a and b (objectives 1 and 3); fast=11 groups run c.
    bins = {bin_.value: bin_ for bin_ in fast_slice.bins}
    assert set(bins) == {10, 11}
    assert bins[10].distribution.count == 2
    assert bins[10].distribution.mean == Fraction(2)
    assert bins[10].run_ids == (_run_id("a"), _run_id("b"))
    assert bins[11].distribution.count == 1


def test_slices_are_chart_series_as_data_never_an_image() -> None:
    line, assignment = _profit_trial("a", 100, 10, 20)
    report = _report([line], {_run_id("a"): assignment})
    assert report.canonical_payload == SENSITIVITY_CANONICAL_PAYLOAD == "series-data"
    assert report.emits_image_payload is False
    for slice_ in report.parameter_slices:
        assert slice_.canonical_payload == "series-data"


# --- AC2: good regions clustered, described as data ---------------------------


def _spike_fixture() -> tuple[list[LedgerLine], dict[str, dict[str, object]]]:
    lines: list[LedgerLine] = []
    params: dict[str, dict[str, object]] = {}
    dense = (
        ("d0", 130, 10, 20),
        ("d1", 132, 11, 20),
        ("d2", 134, 10, 21),
        ("d3", 136, 11, 21),
        ("d4", 138, 12, 22),
    )
    low = (("l0", 10, 50, 90), ("l1", 12, 51, 91), ("l2", 14, 52, 92))
    for run, minor, fast, slow in (*dense, *low):
        line, _ = _profit_trial(run, minor, fast, slow)
        lines.append(line)
        params[_run_id(run)] = {"fast": fast, "slow": slow}
    spike, _ = _profit_trial("spike", 200, 500, 900)
    lines.append(spike)
    params[_run_id("spike")] = {"fast": 500, "slow": 900}
    return lines, params


def test_good_regions_are_clustered_and_described_as_data() -> None:
    lines, params = _spike_fixture()
    report = _report(lines, params)
    assert report.cluster_count >= 1
    for cluster in report.clusters:
        assert cluster.size == len(cluster.member_run_ids)
        # each cluster carries its own objective distribution and exact param ranges.
        assert cluster.distribution.count == cluster.size
        for name in ("fast", "slow"):
            body = cluster.parameter_ranges[name]
            assert body["kind"] == "numeric"
            low = body["minimum"]
            assert isinstance(low, dict)
            assert isinstance(low["num"], int) and isinstance(low["den"], int)
    winners = [cluster for cluster in report.clusters if cluster.contains_winner]
    assert len(winners) == 1


# --- AC3: isolated-spike vs stable-cluster winner -----------------------------


def test_isolated_spike_winner_is_flagged() -> None:
    lines, params = _spike_fixture()
    report = _report(lines, params)
    stability = report.winner_stability
    assert stability.winner_run_id == _run_id("spike")
    assert stability.stability == STABILITY_ISOLATED_SPIKE
    assert stability.is_isolated_spike is True
    assert stability.cluster_size == 1
    assert stability.good_neighbour_count == 0


def test_stable_cluster_winner_is_flagged_distinctly() -> None:
    lines: list[LedgerLine] = []
    params: dict[str, dict[str, object]] = {}
    # the best objective now sits inside the dense good cluster, not off on a spike.
    dense = (
        ("d0", 130, 10, 20),
        ("d1", 500, 11, 20),
        ("d2", 134, 10, 21),
        ("d3", 136, 11, 21),
        ("d4", 138, 12, 22),
    )
    low = (("l0", 10, 50, 90), ("l1", 12, 51, 91), ("l2", 14, 52, 92))
    for run, minor, fast, slow in (*dense, *low):
        line, _ = _profit_trial(run, minor, fast, slow)
        lines.append(line)
        params[_run_id(run)] = {"fast": fast, "slow": slow}
    report = _report(lines, params)
    stability = report.winner_stability
    assert stability.winner_run_id == _run_id("d1")
    assert stability.stability == STABILITY_STABLE_CLUSTER
    assert stability.is_isolated_spike is False
    assert stability.cluster_size >= 2


def test_lone_trial_is_an_isolated_spike() -> None:
    line, assignment = _profit_trial("only", 100, 10, 20)
    report = _report([line], {_run_id("only"): assignment})
    assert report.winner_stability.stability == STABILITY_ISOLATED_SPIKE
    assert report.winner_stability.cluster_size == 1


def test_no_completed_trials_gives_no_winner() -> None:
    report = _ok(
        build_sensitivity_report(
            [_aborted("x")],
            parameters={},
            objective="net_profit",
            world=World.REPLAY,
        )
    )
    assert report.winner_stability.stability == STABILITY_NO_WINNER
    assert report.distribution is None
    assert report.analysed_count == 0
    assert report.excluded_count == 1
    assert WINNER_STABILITIES == (
        STABILITY_ISOLATED_SPIKE,
        STABILITY_STABLE_CLUSTER,
        STABILITY_NO_WINNER,
    )


# --- AC4: no SR*/search-quality verdict, no invented threshold ----------------


def test_report_emits_no_verdict_and_invents_no_threshold() -> None:
    lines, params = _spike_fixture()
    report = _report(lines, params)
    assert report.makes_search_quality_verdict is REPORT_MAKES_SEARCH_QUALITY_VERDICT is False
    assert report.invents_threshold is REPORT_INVENTS_THRESHOLD is False
    assert report.makes_edge_claim is REPORT_MAKES_EDGE_CLAIM is False
    identity = report.fp1_identity()
    for banned in ("pass", "fail", "verdict", "sr", "sr_star", "rated", "significance"):
        assert banned not in identity


def test_search_quality_verdict_is_refused() -> None:
    refusal = refuse_search_quality_verdict("SR*")
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert refusal.context["deferred_to"] == "GAP-0049"
    blank = refuse_search_quality_verdict("  ")
    assert is_refusal(blank)
    assert blank.category is RefusalCategory.INVALID_INPUT


def test_neighbourhood_size_is_recorded_as_data() -> None:
    lines, params = _spike_fixture()
    report = _report(lines, params, neighbourhood_size=2)
    assert report.neighbourhood_size == 2


# --- AC5: exact-integer inputs, float only inside the statistic ---------------


def test_pnl_inputs_stay_exact_integer() -> None:
    line, assignment = _profit_trial("a", 12345, 10, 20)
    measure = line.measures[0]
    quantity = measure["quantity"]
    assert isinstance(quantity, dict)
    # the P&L input is an exact scaled integer, never a binary float.
    assert isinstance(quantity["num"], int)
    assert isinstance(quantity["den"], int)
    distribution = _report([line], {_run_id("a"): assignment}).distribution
    assert distribution is not None
    assert distribution.mean == Fraction(12345, 100)


def test_std_takes_label_derived_identity_never_a_raw_float() -> None:
    lines: list[LedgerLine] = []
    params: dict[str, dict[str, object]] = {}
    for run, minor in (("a", 100), ("b", 250), ("c", 375)):
        line, assignment = _profit_trial(run, minor, 10, 20)
        lines.append(line)
        params[_run_id(run)] = assignment
    report = _report(lines, params)
    distribution = report.distribution
    assert distribution is not None
    std_slot = distribution.fp1_identity()["std"]
    assert isinstance(std_slot, dict)
    assert isinstance(std_slot["num"], int)
    assert isinstance(std_slot["den"], int)
    assert std_slot["rounding"] == "half-even"
    assert std_slot["scale"] == SENSITIVITY_STAT_SCALE
    # not a single raw binary float appears anywhere in the report identity.
    assert not _has_float(report.fp1_identity())


def test_report_is_reproducible() -> None:
    lines, params = _spike_fixture()
    first = _report(lines, params)
    second = _report(lines, params)
    assert _ok(first.fingerprint()).value == _ok(second.fingerprint()).value
    assert first.fp1_identity()["class"] == SENSITIVITY_REPORT_CLASS


# --- excluded trials, never coerced to zero -----------------------------------


def test_aborted_undefined_and_unmapped_trials_are_excluded() -> None:
    lines = [
        _trial("good", measures=(_net_profit(100),)),
        _aborted("ab"),
        _trial("undef", measures=(_undefined("net_profit"),)),
        _trial("nomap", measures=(_net_profit(120),)),
    ]
    params = {_run_id("good"): {"fast": 1, "slow": 2}}
    report = _report(lines, params)
    assert report.analysed_count == 1
    reasons = {item.run_id: item.reason for item in report.excluded}
    assert reasons[_run_id("ab")] == SENSITIVITY_TRIAL_REFUSED
    assert reasons[_run_id("undef")] == SENSITIVITY_OBJECTIVE_UNDEFINED
    assert reasons[_run_id("nomap")] == SENSITIVITY_UNMAPPED
    assert set(reasons.values()) <= set(EXCLUDED_REASONS)


def test_excluded_trials_keep_optimistic_taint() -> None:
    report = _report(
        [_trial("g", measures=(_net_profit(100),)), _aborted("ab")],
        {_run_id("g"): {"fast": 1, "slow": 2}},
    )
    for item in report.excluded:
        assert item.taint == "optimistic"


# --- refusals -----------------------------------------------------------------


def test_objective_must_be_a_roster_identity() -> None:
    line, assignment = _profit_trial("a", 100, 10, 20)
    refusal = build_sensitivity_report(
        [line], parameters={_run_id("a"): assignment}, objective="not_a_metric", world=World.REPLAY
    )
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT


def test_direction_outside_min_max_is_refused() -> None:
    line, assignment = _profit_trial("a", 100, 10, 20)
    refusal = build_sensitivity_report(
        [line],
        parameters={_run_id("a"): assignment},
        objective="net_profit",
        world=World.REPLAY,
        direction="ascending",
    )
    assert is_refusal(refusal)
    assert refusal.context["field"] == "direction"


def test_aborted_role_is_refused() -> None:
    line, assignment = _profit_trial("a", 100, 10, 20)
    refusal = build_sensitivity_report(
        [line],
        parameters={_run_id("a"): assignment},
        objective="net_profit",
        world=World.REPLAY,
        role="aborted",
    )
    assert is_refusal(refusal)
    assert refusal.context["field"] == "role"


def test_binary_float_parameter_value_is_refused() -> None:
    line = _trial("a", measures=(_net_profit(100),))
    refusal = build_sensitivity_report(
        [line],
        parameters={_run_id("a"): {"fast": 1.5, "slow": 2}},
        objective="net_profit",
        world=World.REPLAY,
    )
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT


def test_cross_currency_objective_mix_is_refused() -> None:
    usd = _trial("a", measures=(_net_profit(100),))
    eur_measure = _ok(emit_measure("net_profit", Money(value=100, currency="EUR", scale=2)))
    eur = _trial("b", measures=(eur_measure.fp1_identity(),))
    refusal = build_sensitivity_report(
        [usd, eur],
        parameters={_run_id("a"): {"fast": 1}, _run_id("b"): {"fast": 2}},
        objective="net_profit",
        world=World.REPLAY,
    )
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION


def test_mixed_parameter_space_is_refused() -> None:
    a = _trial("a", measures=(_net_profit(100),))
    b = _trial("b", measures=(_net_profit(200),))
    refusal = build_sensitivity_report(
        [a, b],
        parameters={_run_id("a"): {"fast": 1}, _run_id("b"): {"speed": 2}},
        objective="net_profit",
        world=World.REPLAY,
    )
    assert is_refusal(refusal)
    assert refusal.context["field"] == "parameters"


# --- min direction and categorical parameters ---------------------------------


def test_min_direction_reads_favourable_side_from_the_median() -> None:
    lines: list[LedgerLine] = []
    params: dict[str, dict[str, object]] = {}
    # objective is a drawdown to minimize; the best (smallest) sits in a cluster.
    rows = (("d0", 5, 10), ("d1", 4, 11), ("d2", 6, 10), ("h0", 90, 80), ("h1", 92, 81))
    for run, dd, fast in rows:
        line = _trial(run, measures=(_max_drawdown(dd, 100),))
        lines.append(line)
        params[_run_id(run)] = {"fast": fast}
    report = _ok(
        build_sensitivity_report(
            lines,
            parameters=params,
            objective="max_drawdown",
            world=World.REPLAY,
            direction="min",
        )
    )
    assert report.winner_stability.winner_run_id == _run_id("d1")
    assert report.winner_stability.stability == STABILITY_STABLE_CLUSTER


def test_categorical_and_boolean_parameters_slice_and_cluster() -> None:
    lines: list[LedgerLine] = []
    params: dict[str, dict[str, object]] = {}
    rows = (
        ("a", 300, "trend", True),
        ("b", 280, "trend", True),
        ("c", 20, "range", False),
    )
    for run, minor, regime, active in rows:
        line = _trial(run, measures=(_net_profit(minor),))
        lines.append(line)
        params[_run_id(run)] = {"regime": regime, "active": active}
    report = _report(lines, params)
    slices = {item.parameter: item for item in report.parameter_slices}
    assert slices["regime"].kind == "categorical"
    assert slices["active"].kind == "boolean"
    regime_bins = {bin_.value: bin_ for bin_ in slices["regime"].bins}
    assert regime_bins["trend"].distribution.count == 2
    assert regime_bins["range"].distribution.count == 1


# --- identity seed ------------------------------------------------------------


def test_sensitivity_identity_excludes_semver_and_names_the_contract() -> None:
    identity = sensitivity_identity()
    assert identity["class"] == SENSITIVITY_REPORT_CLASS
    assert identity["canonical_payload"] == "series-data"
    assert identity["makes_search_quality_verdict"] is False
    assert identity["invents_threshold"] is False
    assert identity["verdict_deferred_to"] == "GAP-0049"
    assert _ok(fingerprint(identity)).value.startswith("fp1:sha256:")


def test_distribution_is_a_frozen_dataclass() -> None:
    line, assignment = _profit_trial("a", 100, 10, 20)
    distribution = _report([line], {_run_id("a"): assignment}).distribution
    assert isinstance(distribution, ObjectiveDistribution)
