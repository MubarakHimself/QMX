"""Group F — Anti-overfit parameter-sensitivity report (Story 21.6) -> R29-R33.

Public surfaces driven: ``build_sensitivity_report`` (the read-time fold) and
``refuse_search_quality_verdict``. Statistics are checked against an INDEPENDENT
recomputation; the whole report identity is scanned for the return-space float ban.
"""

from __future__ import annotations

import statistics
from fractions import Fraction

from conftest import (
    RefusalCategory,
    assert_ct04_refusal,
    collect_string_values,
    find_bytes,
    find_floats,
    is_ok,
    money_measure,
    run_id_of,
    trial_line,
    unwrap,
)

from qmb.optimize.sensitivity import (
    STABILITY_ISOLATED_SPIKE,
    STABILITY_STABLE_CLUSTER,
    build_sensitivity_report,
    refuse_search_quality_verdict,
)
from qmf.core.fingerprint import World


def _lines_and_params(rows):
    """Build (lines, parameters) from (seed, x, net_profit_minor) rows."""
    lines = [trial_line(seed, [money_measure("net_profit", minor)]) for seed, x, minor in rows]
    params = {run_id_of(seed): {"x": x} for seed, x, minor in rows}
    return lines, params


# --- T21-328 [R29] -----------------------------------------------------------


def test_t21_328_distribution_summary_and_parameter_slices() -> None:
    """The report carries per-parameter slices and a mean/std/min/max/median summary.

    Counter-case that would FAIL: a summary statistic disagreeing with an independent
    recomputation over the fed objectives, or the parameter slice missing.
    """
    rows = [("a", 1, 10000), ("b", 2, 30000), ("c", 3, 20000), ("d", 4, 50000), ("e", 5, 40000)]
    lines, params = _lines_and_params(rows)
    report = unwrap(
        build_sensitivity_report(lines, parameters=params, objective="net_profit", world=World.REPLAY, direction="max"),
        "report",
    )

    magnitudes = [Fraction(minor, 100) for _, _, minor in rows]  # money as_fraction at scale 2
    dist = report.distribution
    assert dist is not None
    assert dist.count == 5
    assert dist.mean == sum(magnitudes) / len(magnitudes), "mean matches independent recomputation"
    assert dist.minimum == min(magnitudes)
    assert dist.maximum == max(magnitudes)
    assert dist.median == Fraction(statistics.median(sorted(magnitudes))), "median matches independent recomputation"

    slice_names = {s.parameter for s in report.parameter_slices}
    assert "x" in slice_names, "a per-parameter objective slice is emitted for x"
    x_slice = next(s for s in report.parameter_slices if s.parameter == "x")
    assert len(x_slice.bins) == 5, "one slice bin per distinct value of x"


# --- T21-329 [R30] -----------------------------------------------------------


def test_t21_329_isolated_spike_vs_stable_cluster() -> None:
    """A winner alone in an unstable neighbourhood is isolated-spike; one in a cluster is stable.

    Counter-case that would FAIL: the two deliberately-constructed neighbourhoods
    producing the same stability flag (the flag failing to distinguish them).
    """
    # Stable: the max-objective winner (x=1) sits with adjacent favourable trials x=2,x=3.
    stable_rows = [("s1", 1, 100000), ("s2", 2, 90000), ("s3", 3, 80000), ("s4", 20, 10000), ("s5", 21, 20000)]
    stable_lines, stable_params = _lines_and_params(stable_rows)
    stable = unwrap(
        build_sensitivity_report(stable_lines, parameters=stable_params, objective="net_profit", world=World.REPLAY, direction="max"),
        "stable report",
    )
    assert stable.winner_stability.stability == STABILITY_STABLE_CLUSTER, (
        f"a winner amid adjacent favourable trials is a stable cluster, got {stable.winner_stability.stability!r}"
    )

    # Isolated spike: the winner (x=1, huge objective) has no favourable trial near it.
    spike_rows = [("k1", 1, 1000000), ("k2", 50, 50000), ("k3", 51, 60000), ("k4", 52, 70000), ("k5", 53, 80000)]
    spike_lines, spike_params = _lines_and_params(spike_rows)
    spike = unwrap(
        build_sensitivity_report(spike_lines, parameters=spike_params, objective="net_profit", world=World.REPLAY, direction="max"),
        "spike report",
    )
    assert spike.winner_stability.stability == STABILITY_ISOLATED_SPIKE, (
        f"a lone high winner far from any favourable trial is an isolated spike, got {spike.winner_stability.stability!r}"
    )
    assert spike.winner_stability.is_isolated_spike is True


# --- T21-330 [R31] -----------------------------------------------------------


def test_t21_330_no_search_quality_verdict_no_invented_threshold() -> None:
    """The report emits no SR*/search-quality pass/fail verdict and invents no threshold.

    Counter-case that would FAIL: reading a search-quality verdict out of the report
    succeeding (it must refuse), or a bare pass/fail verdict value present in identity.
    """
    # any attempt to read a search-quality verdict is refused (returned policy rejection).
    assert_ct04_refusal(
        refuse_search_quality_verdict("SR*"), RefusalCategory.POLICY_REJECTION, what="SR* verdict"
    )
    assert_ct04_refusal(
        refuse_search_quality_verdict("significance-pass"),
        RefusalCategory.POLICY_REJECTION,
        what="significance verdict",
    )
    # a blank verdict name is invalid input (a name is required to refuse it).
    assert_ct04_refusal(refuse_search_quality_verdict("  "), RefusalCategory.INVALID_INPUT, what="blank verdict")

    rows = [("a", 1, 10000), ("b", 2, 30000), ("c", 3, 20000)]
    lines, params = _lines_and_params(rows)
    report = unwrap(
        build_sensitivity_report(lines, parameters=params, objective="net_profit", world=World.REPLAY, direction="max"),
        "report",
    )
    # no bare pass/fail search-quality verdict VALUE appears anywhere in identity content.
    string_values = set(collect_string_values(report.fp1_identity()))
    assert not (string_values & {"pass", "fail", "sr_star", "search_quality"}), (
        f"the report carries a search-quality verdict value: {string_values & {'pass', 'fail', 'sr_star', 'search_quality'}}"
    )


# --- T21-331 [R32] -----------------------------------------------------------


def test_t21_331_chart_series_cite_exact_inputs_no_image_payload() -> None:
    """Chart series cite the exact parameter inputs; no image/binary is the canonical payload.

    Counter-case that would FAIL: a slice bin not carrying the exact value fed, or a
    bytes/image blob appearing as the canonical payload.
    """
    rows = [("a", 1, 10000), ("b", 2, 30000), ("c", 3, 20000)]
    lines, params = _lines_and_params(rows)
    report = unwrap(
        build_sensitivity_report(lines, parameters=params, objective="net_profit", world=World.REPLAY, direction="max"),
        "report",
    )
    x_slice = next(s for s in report.parameter_slices if s.parameter == "x")
    bin_values = {b.value for b in x_slice.bins}
    assert bin_values == {1, 2, 3}, "each series point cites the exact parameter value fed (data, not an image)"
    assert report.canonical_payload == "series-data"

    # no image/binary is the canonical payload anywhere in the report identity.
    assert find_bytes(report.fp1_identity()) == [], "no bytes/image blob is the canonical payload"


# --- T21-332 [R33] -----------------------------------------------------------


def test_t21_332_return_space_float_carveout_no_raw_float_in_identity() -> None:
    """P&L inputs stay exact-integer; the std is a scaled rational under a fixed contract; no raw float.

    Counter-case that would FAIL: any raw Python float appearing anywhere in the report
    identity (in particular the std stored as a binary float rather than a label-derived
    scaled rational).
    """
    rows = [("a", 1, 10000), ("b", 2, 30000), ("c", 3, 20000), ("d", 4, 55000)]
    lines, params = _lines_and_params(rows)
    report = unwrap(
        build_sensitivity_report(lines, parameters=params, objective="net_profit", world=World.REPLAY, direction="max"),
        "report",
    )
    # the std (the one float-domain statistic) is stored as an exact num/den scaled rational
    # under a fixed {rounding, scale} contract — never a raw float.
    std = report.distribution.fp1_identity()["std"]
    assert set(std) >= {"num", "den", "rounding", "scale"}
    assert isinstance(std["num"], int) and isinstance(std["den"], int) and not isinstance(std["num"], bool)

    # the entire report identity is float-free (the B-14 return-space carve-out honoured).
    floats = find_floats(report.fp1_identity())
    assert floats == [], f"a raw binary float reached identity content: {floats}"
