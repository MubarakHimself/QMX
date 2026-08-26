"""Story 21.5 — Study resume from the ledger view and pre-flight cost estimation."""

from __future__ import annotations

from fractions import Fraction
from typing import TypeVar

from qmb.doors import api
from qmb.doors.cli.tree import invoke_optimize_estimate
from qmb.optimize import (
    ESTIMATE_SPAWNS_TRIAL,
    ESTIMATE_STATUS_MEASURED,
    ESTIMATE_STATUS_NOT_YET_MEASURED,
    ESTIMATE_STATUS_OPEN_ENDED,
    RESUME_CONSULTS_OPTUNA_STORE,
    RESUME_SOURCE,
    TRIAL_BUDGET_FIXED,
    TRIAL_BUDGET_RUN_UNTIL,
    TRIAL_BUDGET_SCALE_WITH_PARAMS,
    CostEstimate,
    ParameterBatch,
    StudyParameterSpace,
    StudyStepper,
    TrialBudget,
    coerce_study_space,
    cost_estimate_identity,
    estimate_study_cost,
    plan_study_resume,
    resume_stepper,
    study_resume_identity,
)
from qmf.core.chrono import Duration
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

T = TypeVar("T")

_R = UnitKind.DIMENSIONLESS_RATIO


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _space() -> StudyParameterSpace:
    return _ok(
        coerce_study_space(
            [
                {
                    "name": "lookback",
                    "type": "exact integer",
                    "unit_kind": UnitKind.COUNT,
                    "bounds": {"min": 2, "max": 40},
                    "step": 2,
                    "default": 10,
                    "ui": "ui-editable",
                },
                {
                    "name": "atr_mult",
                    "type": "exact rational",
                    "unit_kind": _R,
                    "bounds": {
                        "min": {"num": 0, "den": 1, "unit_kind": _R},
                        "max": {"num": 30, "den": 10, "unit_kind": _R},
                    },
                    "step": {"num": 5, "den": 10, "unit_kind": _R},
                    "default": {"num": 10, "den": 10, "unit_kind": _R},
                    "ui": "ui-editable",
                },
            ]
        )
    )


def _study_fp() -> Fingerprint:
    return _ok(fingerprint({"study": "resume"}))


def _fresh(batch_size: int = 4) -> StudyStepper:
    return StudyStepper(
        space=_space(),
        seed=4242,
        direction="max",
        study_fp=_study_fp(),
        batch_size=batch_size,
    )


def _priors(batch: ParameterBatch, *, only: set[int] | None = None) -> list[dict[str, object]]:
    return [
        {
            "generation_index": batch.generation_index,
            "ask_index": trial.ask_index,
            "parameters": trial.assignment,
            "objective": Fraction(trial.ask_index + 1),
        }
        for trial in batch.proposals
        if only is None or trial.ask_index in only
    ]


# --- AC1 / AC2: resume from the ledger view ----------------------------------


def test_resume_resumes_the_generation_index_from_the_last_completed_generation() -> None:
    # Drive a fresh Study two generations, capturing the deterministic gen-1 batch.
    stepper = _fresh()
    after0, gen0 = _ok(stepper.ask())
    told = _ok(after0.tell(_priors(gen0)))
    _after1, gen1 = _ok(told.ask())
    original_gen1 = _ok(gen1.fingerprint())

    # Now resume from the ledger view: only generation 0 completed.
    history = _priors(gen0)
    resumed, plan = _ok(resume_stepper(_fresh(), history))
    assert plan.completed_generations == 1
    assert plan.resume_generation == 1
    assert plan.pending_asks == (0, 1, 2, 3)  # nothing of gen 1 is in the ledger yet
    assert plan.resumed_asks == ()
    assert len(plan.conditioned) == 4
    # The repositioned stepper re-proposes generation 1 byte-identically — the
    # completed trials are read, not re-run.
    _next_stepper, resumed_gen1 = _ok(resumed.ask())
    assert resumed_gen1.generation_index == 1
    assert _ok(resumed_gen1.fingerprint()) == original_gen1


def test_resume_skips_a_partially_completed_generation_without_re_running_it() -> None:
    stepper = _fresh()
    after0, gen0 = _ok(stepper.ask())
    told = _ok(after0.tell(_priors(gen0)))
    _after1, gen1 = _ok(told.ask())
    original_gen1 = _ok(gen1.fingerprint())

    # Generation 0 complete; generation 1 has two of four asks done in the ledger.
    history = _priors(gen0) + _priors(gen1, only={1, 3})
    plan = _ok(plan_study_resume(history, batch_size=4))
    assert plan.resume_generation == 1
    assert plan.resumed_asks == (1, 3)
    assert plan.pending_asks == (0, 2)  # only the missing asks are still to run
    assert plan.has_partial_resume_generation is True
    assert plan.total_completed_trials == 6

    resumed, _plan = _ok(resume_stepper(_fresh(), history))
    _after, resumed_gen1 = _ok(resumed.ask())
    # Re-proposing generation 1 is deterministic regardless of the partial state,
    # so the two already-done trials are never re-run.
    assert _ok(resumed_gen1.fingerprint()) == original_gen1


def test_resume_reads_only_the_ledger_view_never_an_optuna_store() -> None:
    assert RESUME_CONSULTS_OPTUNA_STORE is False
    identity = study_resume_identity()
    assert identity["consults_optuna_store"] is False
    assert identity["source"] == RESUME_SOURCE == "ledger-view"
    # An empty ledger resumes a brand-new Study at generation 0.
    plan = _ok(plan_study_resume([], batch_size=4))
    assert plan.resume_generation == 0
    assert plan.conditioned == ()
    assert plan.pending_asks == (0, 1, 2, 3)


def test_resume_refuses_an_inconsistent_ledger_read() -> None:
    # An ask index beyond the declared batch size is an inconsistent read.
    bad_ask = plan_study_resume(
        [{"generation_index": 0, "ask_index": 9, "parameters": {"x": 1}, "objective": 1}],
        batch_size=4,
    )
    assert is_refusal(bad_ask)
    assert bad_ask.category is RefusalCategory.POLICY_REJECTION
    # A trial ahead of the first incomplete generation cannot be conditioned on.
    ahead = plan_study_resume(
        [{"generation_index": 2, "ask_index": 0, "parameters": {"x": 1}, "objective": 1}],
        batch_size=4,
    )
    assert is_refusal(ahead)
    # resume_stepper insists on a fresh stepper.
    stepper = _fresh()
    after0, _gen0 = _ok(stepper.ask())
    assert is_refusal(resume_stepper(after0, []))


# --- AC3 / AC4: pre-flight cost estimation -----------------------------------


def test_fixed_budget_projects_wall_from_the_measured_baseline() -> None:
    budget = _ok(TrialBudget.try_create(TRIAL_BUDGET_FIXED, fixed_total=10))
    estimate = _ok(
        estimate_study_cost(
            budget,
            per_trial_runtime=_ok(Duration.try_create(2_000_000_000)),
            concurrency_cap=4,
        )
    )
    assert isinstance(estimate, CostEstimate)
    assert estimate.status == ESTIMATE_STATUS_MEASURED
    assert estimate.projected_total_trials == 10
    # 10 trials x 2s / 4 concurrency = 5s.
    assert estimate.projected_wall_ns == 10 * 2_000_000_000 // 4
    assert estimate.spawns_trial is ESTIMATE_SPAWNS_TRIAL is False
    duration = estimate.projected_wall_duration()
    assert duration is not None
    assert _ok(duration).value_ns == 5_000_000_000


def test_scale_with_params_budget_scales_by_the_declared_factor() -> None:
    budget = _ok(TrialBudget.try_create(TRIAL_BUDGET_SCALE_WITH_PARAMS, per_param_factor=200))
    estimate = _ok(
        estimate_study_cost(
            budget,
            param_count=3,
            per_trial_runtime=1_000_000_000,
            concurrency_cap=12,
        )
    )
    assert estimate.projected_total_trials == 600
    assert estimate.projected_wall_ns == 600 * 1_000_000_000 // 12


def test_no_measured_baseline_is_reported_not_yet_measured_never_invented() -> None:
    budget = _ok(TrialBudget.try_create(TRIAL_BUDGET_FIXED, fixed_total=50))
    estimate = _ok(estimate_study_cost(budget, per_trial_runtime=None, concurrency_cap=8))
    assert estimate.status == ESTIMATE_STATUS_NOT_YET_MEASURED
    assert estimate.measured is False
    assert estimate.projected_total_trials == 50
    assert estimate.per_trial_runtime_ns is None
    assert estimate.projected_wall_ns is None
    assert estimate.projected_wall_duration() is None
    # No invented figure rides in identity.
    assert "projected_wall_ns" not in estimate.fp1_identity()
    assert "per_trial_runtime_ns" not in estimate.fp1_identity()


def test_run_until_budget_is_open_ended_and_never_invents_a_count() -> None:
    budget = _ok(TrialBudget.try_create(TRIAL_BUDGET_RUN_UNTIL, runs_until_target=True))
    estimate = _ok(estimate_study_cost(budget, per_trial_runtime=500_000_000, concurrency_cap=4))
    assert estimate.status == ESTIMATE_STATUS_OPEN_ENDED
    assert estimate.projected_total_trials is None
    assert estimate.projected_wall_ns is None
    # A declared timeout ceiling rides as the wall bound.
    timed = _ok(TrialBudget.try_create(TRIAL_BUDGET_RUN_UNTIL, timeout_ns=60_000_000_000))
    estimate_timed = _ok(
        estimate_study_cost(timed, per_trial_runtime=500_000_000, concurrency_cap=4)
    )
    assert estimate_timed.projected_wall_ns == 60_000_000_000


def test_estimate_refuses_bad_inputs_and_never_spawns() -> None:
    assert cost_estimate_identity()["spawns_trial"] is False
    good = _ok(TrialBudget.try_create(TRIAL_BUDGET_FIXED, fixed_total=1))
    assert is_refusal(estimate_study_cost(good, per_trial_runtime=1, concurrency_cap=0))
    assert is_refusal(estimate_study_cost({"kind": "nonsense"}, concurrency_cap=1))
    # scale-with-params needs a positive param count.
    scale = _ok(TrialBudget.try_create(TRIAL_BUDGET_SCALE_WITH_PARAMS, per_param_factor=50))
    assert is_refusal(estimate_study_cost(scale, per_trial_runtime=1, concurrency_cap=1))
    # a binary-float runtime is refused (exact nanoseconds only).
    assert is_refusal(estimate_study_cost(good, per_trial_runtime=1.5, concurrency_cap=1))


# --- AC3: the estimate is reachable through the qmb CLI door ------------------


def test_estimate_through_the_cli_door_requires_a_budget_and_spawns_nothing() -> None:
    missing = invoke_optimize_estimate(concurrency_cap=4)
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert missing.context["command"] == "optimize.estimate"

    estimate = _ok(
        invoke_optimize_estimate(
            budget={"kind": TRIAL_BUDGET_FIXED, "fixed_total": 12},
            per_trial_runtime=2_000_000_000,
            concurrency_cap=6,
        )
    )
    assert estimate.status == ESTIMATE_STATUS_MEASURED
    assert estimate.projected_total_trials == 12
    assert estimate.spawns_trial is False


def test_estimate_through_the_cli_door_resolves_the_governor_concurrency_cap() -> None:
    # No explicit cap: the door resolves min(cpu, memory) from the governor budgets.
    estimate = _ok(
        invoke_optimize_estimate(
            budget={"kind": TRIAL_BUDGET_FIXED, "fixed_total": 20},
            per_trial_runtime=1_000_000_000,
            cpu_budget=8,
            memory_budget=4_000,
            projected_peak_memory=1_000,
        )
    )
    # cap = min(cpu=8, memory 4000/1000=4) = 4 → wall = 20 * 1e9 / 4.
    assert estimate.concurrency_cap == 4
    assert estimate.projected_wall_ns == 20 * 1_000_000_000 // 4
    # A bad declaration is refused rather than silently ignored.
    assert is_refusal(
        invoke_optimize_estimate(
            budget={"kind": TRIAL_BUDGET_FIXED, "fixed_total": 1},
            declaration={"not": "a-bot"},
            concurrency_cap=1,
        )
    )


def test_estimate_surface_is_on_both_doors() -> None:
    assert api.estimate_study_cost is estimate_study_cost
    assert api.TrialBudget is TrialBudget
    assert api.CostEstimate is CostEstimate
    assert api.plan_study_resume is plan_study_resume
    assert api.resume_stepper is resume_stepper


# --- validation and identity edges -------------------------------------------


def test_trial_budget_validation_and_identity() -> None:
    # An empty run-until budget has no stopping rule.
    assert is_refusal(TrialBudget.try_create(TRIAL_BUDGET_RUN_UNTIL))
    # A non-boolean target flag is refused.
    assert is_refusal(TrialBudget.try_create(TRIAL_BUDGET_RUN_UNTIL, runs_until_target="yes"))
    # A negative timeout is refused.
    assert is_refusal(TrialBudget.try_create(TRIAL_BUDGET_RUN_UNTIL, timeout_ns=-5))
    # An unknown kind is refused.
    assert is_refusal(TrialBudget.try_create("weekly"))

    fixed = _ok(TrialBudget.try_create(TRIAL_BUDGET_FIXED, fixed_total=7))
    assert fixed.fp1_identity() == {
        "class": "qmb-trial-budget",
        "kind": "fixed",
        "fixed_total": 7,
    }
    scale = _ok(TrialBudget.try_create(TRIAL_BUDGET_SCALE_WITH_PARAMS, per_param_factor=200))
    assert scale.fp1_identity()["per_param_factor"] == 200
    run_until = _ok(
        TrialBudget.try_create(TRIAL_BUDGET_RUN_UNTIL, timeout_ns=90, runs_until_target=True)
    )
    body = run_until.fp1_identity()
    assert body["timeout_ns"] == 90
    assert body["runs_until_target"] is True


def test_runtime_baseline_coercion_edges() -> None:
    budget = _ok(TrialBudget.try_create(TRIAL_BUDGET_FIXED, fixed_total=4))
    # A runtime mapping carrying value_ns coerces like a Duration.
    mapped = _ok(
        estimate_study_cost(budget, per_trial_runtime={"value_ns": 500}, concurrency_cap=2)
    )
    assert mapped.per_trial_runtime_ns == 500
    # A negative Duration baseline is refused.
    assert is_refusal(
        estimate_study_cost(
            budget, per_trial_runtime=_ok(Duration.try_create(-5)), concurrency_cap=1
        )
    )
    # A negative int, a boolean, and an unusable type are each refused.
    assert is_refusal(estimate_study_cost(budget, per_trial_runtime=-10, concurrency_cap=1))
    assert is_refusal(estimate_study_cost(budget, per_trial_runtime=True, concurrency_cap=1))
    assert is_refusal(estimate_study_cost(budget, per_trial_runtime="soon", concurrency_cap=1))
    # A non-mapping, non-TrialBudget budget is refused.
    assert is_refusal(estimate_study_cost(42, concurrency_cap=1))


def test_resume_plan_identity_is_fingerprintable() -> None:
    stepper = _fresh()
    _after0, gen0 = _ok(stepper.ask())
    plan = _ok(plan_study_resume(_priors(gen0), batch_size=4))
    identity = plan.fp1_identity()
    assert identity["class"] == "qmb-study-resume-plan"
    assert identity["source"] == RESUME_SOURCE
    assert identity["resume_generation"] == 1
    assert is_ok(fingerprint(identity))
