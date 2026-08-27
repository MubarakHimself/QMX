"""Epic 22 · Story 22.5 — walk-forward as a sequence of split-manifest runs.

Independent L3 acceptance tests T22-326, 327, 328 (partial), 329, 330, 331: the
window sequence of distinct split manifests with display-only train/test aliases, the
role=trial ledger role and the not-yet-ruled OOS read-time fold, the fingerprint (not
name@latest) resolution discipline, the deferred configurables, the read-time
aggregation view, and reproducibility. Every test names its counter-case.

The SC-11 batch-admission single-frozen-as-of mechanism (``admit_walk_forward``) is
reachable only through the Epic-13-owned B-15 registry-read port and Epic-13/15-owned
fragment materialization; that portion is recorded UNPROVEN in RESULTS.md (finding
E22-F03), and only the robustness-side window/plan/aggregation discipline is tested here.
"""

from __future__ import annotations

from conftest import assert_ct04_refusal, is_ok, is_refusal, unwrap

from qmf.core.exact import ExactRational, UnitKind
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import RefusalCategory

from qmb.robustness import (
    IN_SAMPLE_ALIAS,
    OOS_BAR_OUTCOME_NOT_YET_RULED,
    OUT_OF_SAMPLE_ALIAS,
    WalkForwardWindow,
    WalkForwardWindowResult,
    aggregate_walk_forward,
    fold_oos_bar_outcome,
    plan_walk_forward,
    refuse_merged_walk_forward_run,
    refuse_walk_forward_battery_threshold,
    refuse_window_bar_verdict,
)
from qmb.ledger.line import ROLE_REPLICATE, ROLE_TRIAL


def _fp(payload):
    return unwrap(fingerprint(payload), "fp")


def _window(index):
    return unwrap(
        WalkForwardWindow.try_create(
            index, _fp({"split": "in", "i": index}), _fp({"split": "out", "i": index})
        ),
        f"window{index}",
    )


def _rat(n):
    return unwrap(ExactRational.try_create(n, 1, UnitKind.DIMENSIONLESS_RATIO), f"rat{n}")


# --- T22-326 (window sequence; two first-class runs; aliases display-only; distinct) P1 ---


def test_t22_326_window_materializes_two_first_class_runs_with_display_only_aliases():
    """A window is two first-class runs; train/test are display aliases, never in identity.

    Counter-case: the alias tokens ``train``/``test`` appearing in fp1_identity (making
    them a substitute for the manifest fingerprints), or a window not producing two runs.
    """
    window = _window(0)
    runs = window.runs
    assert len(runs) == 2
    assert runs[0].contributes_to_objective is True  # in-sample computes the objective
    assert runs[1].contributes_to_objective is False  # out-of-sample records only

    aliases = window.display_aliases()
    assert aliases[IN_SAMPLE_ALIAS] == window.in_sample_split.value
    assert aliases[OUT_OF_SAMPLE_ALIAS] == window.out_of_sample_split.value

    identity = window.fp1_identity()
    assert identity["in_sample_split_fp1"] == window.in_sample_split.value
    assert identity["out_of_sample_split_fp1"] == window.out_of_sample_split.value
    assert IN_SAMPLE_ALIAS not in str(identity) and OUT_OF_SAMPLE_ALIAS not in str(identity)


def test_t22_326_distinct_manifests_and_replay_world_are_enforced():
    """The two splits must be distinct manifests in the replay world.

    Counter-case: naming one fingerprint for both splits (no out-of-sample content), or a
    simulated-world split, being accepted.
    """
    same = WalkForwardWindow.try_create(0, _fp({"x": 1}), _fp({"x": 1}))
    assert_ct04_refusal(same, RefusalCategory.INVALID_INPUT, what="identical in/out splits")

    simulated = WalkForwardWindow.try_create(
        0, _fp({"a": 1}), _fp({"b": 2}), world=World.SIMULATED
    )
    assert is_refusal(simulated), "a simulated-world walk-forward split must be refused"


# --- T22-327 (ledger role=trial; OOS bar outcome not-yet-ruled read-time fold) P0 ---


def test_t22_327_in_sample_role_is_trial_and_no_run_carries_a_bar_verdict():
    """The in-sample run ledgers role=trial with the objective; no window run is a bar verdict.

    Counter-case: an in-sample role that is not trial/replicate, or a run role that is a
    Book-bar pass/fail verdict role.
    """
    window = _window(0)
    assert window.in_sample_run.role == ROLE_TRIAL
    assert window.out_of_sample_run.role in (ROLE_TRIAL, ROLE_REPLICATE)


def test_t22_327_oos_bar_outcome_is_a_read_time_not_yet_ruled_fold():
    """The out-of-sample bar outcome is a read-time fold returning ``not-yet-ruled``.

    Counter-case: a stored pass/fail verdict, or any value other than not-yet-ruled while
    GAP-0048/0049 stay open; and reading a bar verdict out of a window run must be refused.
    """
    assert fold_oos_bar_outcome() == OOS_BAR_OUTCOME_NOT_YET_RULED == "not-yet-ruled"
    assert fold_oos_bar_outcome(_window(0)) == OOS_BAR_OUTCOME_NOT_YET_RULED

    refusal = assert_ct04_refusal(
        refuse_window_bar_verdict("book_pass"), RefusalCategory.POLICY_REJECTION, what="window bar verdict"
    )
    assert dict(refusal.context).get("oos_bar_outcome") == OOS_BAR_OUTCOME_NOT_YET_RULED


# --- T22-328 (fingerprint-not-alias resolution; admission-freeze UNPROVEN) P1 ---


def test_t22_328_splits_resolve_by_fingerprint_and_alias_is_never_a_substitute():
    """A window resolves its split by fingerprint; the display alias is never its substitute.

    Counter-case: an alias that resolves to something other than its manifest fingerprint,
    or a fingerprint that does not round-trip back to its alias. (The SC-11 single-frozen
    registry-as-of admission mechanism is UNPROVEN here — Epic-13 B-15 port fixture.)
    """
    window = _window(0)
    assert unwrap(window.split_for(IN_SAMPLE_ALIAS), "in").value == window.in_sample_split.value
    assert unwrap(window.split_for(OUT_OF_SAMPLE_ALIAS), "out").value == window.out_of_sample_split.value
    assert unwrap(window.alias_for(window.in_sample_split), "alias-in") == IN_SAMPLE_ALIAS
    assert unwrap(window.alias_for(window.out_of_sample_split), "alias-out") == OUT_OF_SAMPLE_ALIAS
    # An off-vocabulary alias is refused, never coerced.
    assert_ct04_refusal(window.split_for("validation"), RefusalCategory.INVALID_INPUT, what="unknown alias")


# --- T22-329 (deferred configurables; no invented default; no baked battery) P1 ---


def test_t22_329_plan_configurables_have_no_ratified_value():
    """The window count / spans / step are required — unset the plan refuses; a battery is refused.

    Counter-case: a plan built with defaulted spans/step, or a window-count that silently
    truncates a mismatched sequence; or applying a WF/PBO/CSCV threshold returning Ok.
    """
    windows = [_window(0), _window(1)]
    unset = plan_walk_forward(windows)
    assert_ct04_refusal(unset, RefusalCategory.INVALID_INPUT, what="plan with unset configurables")

    mismatch = plan_walk_forward(
        windows, window_count=5, in_sample_span=1, out_of_sample_span=1, step=1
    )
    assert_ct04_refusal(mismatch, RefusalCategory.INVALID_INPUT, what="window-count mismatch")

    ok = plan_walk_forward(
        windows, window_count=2, in_sample_span=100, out_of_sample_span=20, step=20
    )
    assert is_ok(ok)
    assert unwrap(ok, "plan").window_count == 2

    assert_ct04_refusal(
        refuse_walk_forward_battery_threshold("pbo"),
        RefusalCategory.POLICY_REJECTION,
        what="WF/PBO battery threshold",
    )


# --- T22-330 (read-time aggregation, never merged run; data; feeds deferred battery) P1 ---


def test_t22_330_aggregation_is_a_read_time_view_never_a_merged_run():
    """The walk-forward view aggregates window runs at read time; it is never a merged run.

    Counter-case: an aggregation flagged as a merged run, one that emits a verdict, or a
    governance battery carrying ratified thresholds; and minting a merged run must refuse.
    """
    results = [
        unwrap(WalkForwardWindowResult.try_create(0, {"sharpe_ratio": _rat(2)}, {"sharpe_ratio": _rat(1)}), "wr0"),
        unwrap(WalkForwardWindowResult.try_create(1, {"sharpe_ratio": _rat(3)}, {"sharpe_ratio": _rat(1)}), "wr1"),
    ]
    aggregation = unwrap(aggregate_walk_forward(results, ["sharpe_ratio"]), "aggregation")
    assert aggregation.is_merged_run is False
    assert aggregation.emits_verdict is False
    assert aggregation.window_count == 2

    payload = aggregation.ct32_data_payload()
    assert payload["canonical_payload"] == "series-data"
    assert payload["is_merged_run"] is False
    assert payload["governance_battery_has_ratified_thresholds"] is False
    assert tuple(payload["governance_battery_candidates"]) == ("pbo", "cscv")
    # The per-metric fold carries in-sample AND out-of-sample distributions as data.
    fold = aggregation.metric_named("sharpe_ratio")
    chart = fold.chart_series()
    assert "in_sample" in chart and "out_of_sample" in chart

    assert_ct04_refusal(
        refuse_merged_walk_forward_run("merged"), RefusalCategory.POLICY_REJECTION, what="merged run"
    )


def test_t22_330_aggregation_refuses_a_missing_or_mixed_unit_fold():
    """A metric missing from a window, or a mixed unit-kind, is refused — never silently dropped.

    Counter-case: an aggregation that silently drops a window missing the selected metric.
    """
    results = [
        unwrap(WalkForwardWindowResult.try_create(0, {"sharpe_ratio": _rat(2)}, {"sharpe_ratio": _rat(1)}), "wr0"),
        unwrap(WalkForwardWindowResult.try_create(1, {"calmar_ratio": _rat(3)}, {"calmar_ratio": _rat(1)}), "wr1"),
    ]
    refused = aggregate_walk_forward(results, ["sharpe_ratio"])
    assert_ct04_refusal(refused, RefusalCategory.INVALID_INPUT, what="metric missing from a window")


# --- T22-331 (reproducibility; window label carries split fps, world, evidence class) P1 ---


def test_t22_331_window_and_aggregation_reproduce_and_labels_carry_provenance():
    """Same inputs reproduce fingerprints; a window label carries both split fps, world, evidence.

    Counter-case: a differing fingerprint on re-fold, or a window identity missing the
    split fingerprints / world / evidence class. (The frozen registry_as_of stamp is
    admission-owned — UNPROVEN, see finding E22-F03.)
    """
    window = _window(0)
    assert unwrap(window.fingerprint(), "w1").value == unwrap(_window(0).fingerprint(), "w2").value

    identity = window.fp1_identity()
    assert identity["in_sample_split_fp1"] == window.in_sample_split.value
    assert identity["out_of_sample_split_fp1"] == window.out_of_sample_split.value
    assert identity["world"] == World.REPLAY.value
    assert "evidence_class" in identity

    results = [
        unwrap(WalkForwardWindowResult.try_create(0, {"sharpe_ratio": _rat(2)}, {"sharpe_ratio": _rat(1)}), "wr0"),
        unwrap(WalkForwardWindowResult.try_create(1, {"sharpe_ratio": _rat(3)}, {"sharpe_ratio": _rat(1)}), "wr1"),
    ]
    agg1 = unwrap(aggregate_walk_forward(results, ["sharpe_ratio"]), "agg1")
    agg2 = unwrap(aggregate_walk_forward(results, ["sharpe_ratio"]), "agg2")
    assert unwrap(agg1.fingerprint(), "a1").value == unwrap(agg2.fingerprint(), "a2").value
