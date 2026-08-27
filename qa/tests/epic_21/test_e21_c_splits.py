"""Group C — Train/test split discipline (Story 21.3) -> R13-R17.

Public surfaces driven: ``plan_trial_runs``, ``admit_objective_run``,
``refuse_split_edge_or_budget``, ``admit_study_world``, ``coerce_study_splits``,
``study_warmup`` and ``trading_evidence_range``. Seal/embargo boundary ENFORCEMENT
is qmf-data / Epic 3 (out of scope); Epic 21 asserts fingerprint-only split
consumption, the world=replay-only rule, and warm-up-as-count.
"""

from __future__ import annotations

from conftest import (
    Duration,
    RefusalCategory,
    assert_ct04_refusal,
    collect_string_values,
    fp,
    is_ok,
    unwrap,
)

from qmb.optimize.splits import (
    admit_objective_run,
    admit_study_world,
    coerce_study_splits,
    plan_trial_runs,
    refuse_split_edge_or_budget,
    study_warmup,
    trading_evidence_range,
)
from qmf.core.chrono import Instant
from qmf.core.fingerprint import World


def _splits() -> object:
    train = fp("train-manifest").value
    test = fp("test-manifest").value
    return unwrap(coerce_study_splits({"train": train, "test": test}), "splits")


# --- T21-312 [R13] -----------------------------------------------------------


def test_t21_312_training_scores_objective_testing_records_only() -> None:
    """Training computes the objective; testing runs the identical params, records only.

    Counter-case that would FAIL: the testing run admitted to feed the objective, or the
    two runs not sharing one parameter-set fingerprint.
    """
    splits = _splits()
    param_set = fp("param-set")
    plan = unwrap(plan_trial_runs(splits, param_set), "trial plan")

    assert plan.train_run.contributes_to_objective is True
    assert plan.test_run.contributes_to_objective is False
    # both runs execute the IDENTICAL parameter set (identity, not convention).
    assert plan.parameter_set_fp1.value == param_set.value

    assert is_ok(admit_objective_run(plan.train_run)), "the training run feeds the objective"
    refused = admit_objective_run(plan.test_run)
    assert_ct04_refusal(refused, RefusalCategory.POLICY_REJECTION, what="testing feeds objective")


# --- T21-313 [R14] -----------------------------------------------------------


def test_t21_313_trial_label_carries_both_fingerprints_aliases_display_only() -> None:
    """Both split fingerprints ride the trial label; aliases are display-only, never substituted.

    Counter-case that would FAIL: an alias token stored where a fingerprint belongs, or a
    fingerprint missing from the label, or the aliases appearing in identity content.
    """
    train = fp("train-manifest")
    test = fp("test-manifest")
    splits = unwrap(coerce_study_splits({"train": train.value, "test": test.value}), "splits")
    plan = unwrap(plan_trial_runs(splits, fp("param-set")), "plan")

    label = plan.trial_label()
    assert label["train_split_fp1"] == train.value, "the actual train fingerprint rides, not 'train'"
    assert label["test_split_fp1"] == test.value, "the actual test fingerprint rides, not 'test'"
    # aliases live only in the display block, mapping to the same fingerprints.
    aliases = label["display"]["aliases"]  # type: ignore[index]
    assert aliases == {"train": train.value, "test": test.value}

    # identity content (fp1_identity) never substitutes an alias for a fingerprint:
    # the split-fp1 fields hold real fp1 strings.
    identity = plan.fp1_identity()
    assert identity["splits"]["train_split_fp1"] == train.value  # type: ignore[index]
    assert identity["splits"]["test_split_fp1"] == test.value  # type: ignore[index]
    # the display alias map is not part of identity content.
    assert "aliases" not in collect_string_values(identity)


# --- T21-314 [R15] -----------------------------------------------------------


def test_t21_314_optimistic_taint_no_edge_no_split_budget() -> None:
    """A split-trial fill is optimistic, spends no split budget, and claims no edge.

    Counter-case that would FAIL: an edge claim or split-budget spend permitted under
    the optimistic taint, or a non-optimistic taint accepted.
    """
    # The compliant call passes.
    assert is_ok(refuse_split_edge_or_budget(taint="optimistic", claims_edge=False, spends_split_budget=False))

    # Claiming edge or spending split budget under the optimistic taint is a policy rejection.
    assert_ct04_refusal(
        refuse_split_edge_or_budget(claims_edge=True), RefusalCategory.POLICY_REJECTION, what="edge claim"
    )
    assert_ct04_refusal(
        refuse_split_edge_or_budget(spends_split_budget=True),
        RefusalCategory.POLICY_REJECTION,
        what="split budget",
    )
    # A non-optimistic taint is invalid input until GAP-0048.
    assert_ct04_refusal(
        refuse_split_edge_or_budget(taint="pessimistic"), RefusalCategory.INVALID_INPUT, what="bad taint"
    )

    # The planned split runs carry the optimistic taint on their fills.
    plan = unwrap(plan_trial_runs(_splits(), fp("param-set")), "plan")
    assert plan.train_run.taint == "optimistic"
    assert plan.test_run.taint == "optimistic"


# --- T21-315 [R16] P0 evidence firewall --------------------------------------


def test_t21_315_world_simulated_is_policy_rejection() -> None:
    """A Study resolving to world=simulated is a policy rejection; replay is admitted.

    Counter-case that would FAIL: a simulated-world Study admitted, or a replay Study
    refused.
    """
    assert is_ok(admit_study_world(World.REPLAY)), "a replay Study is admitted"

    # store-tainted synthetic provenance derives world=simulated -> policy rejection.
    assert_ct04_refusal(
        admit_study_world("synthetic-tainted"), RefusalCategory.POLICY_REJECTION, what="synthetic provenance"
    )
    assert_ct04_refusal(
        admit_study_world(World.SIMULATED), RefusalCategory.POLICY_REJECTION, what="declared simulated"
    )

    # A split declaration naming world=simulated is refused at Study creation.
    train = fp("train-manifest").value
    test = fp("test-manifest").value
    sim_splits = coerce_study_splits({"train": train, "test": test, "world": "simulated"})
    assert_ct04_refusal(sim_splits, RefusalCategory.POLICY_REJECTION, what="simulated split")
    # ...and world=replay is admitted.
    assert is_ok(coerce_study_splits({"train": train, "test": test, "world": "replay"}))


# --- T21-316 [R17] -----------------------------------------------------------


def test_t21_316_warmup_is_observation_count_not_duration() -> None:
    """Warm-up is the embargo observation count (AD-22), never a Duration; evidence is trading-only.

    Counter-case that would FAIL: a Duration accepted as warm-up, a count rejected, or
    the evidence range starting before the first trading instant (covering warm-up).
    """
    embargo = unwrap(study_warmup(5, split_fp1=fp("train-manifest").value), "warmup")
    assert embargo.observation_count == 5

    duration = unwrap(Duration.try_create(1_000_000), "duration")
    assert_ct04_refusal(study_warmup(duration), RefusalCategory.INVALID_INPUT, what="duration warmup")

    # Evidence range is the trading interval only: it begins at the first TRADING instant,
    # warm-up instants omitted.
    t0 = unwrap(Instant.try_create(0), "t0")
    trade_start = unwrap(Instant.try_create(1_000), "trade start")
    trade_end = unwrap(Instant.try_create(2_000), "trade end")
    span = unwrap(trading_evidence_range([trade_start, trade_end], empty_at=t0), "evidence range")
    assert span.start.value_ns == trade_start.value_ns, "evidence range excludes warm-up"
    assert span.end.value_ns == trade_end.value_ns + 1
