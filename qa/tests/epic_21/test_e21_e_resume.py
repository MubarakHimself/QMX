"""Group E — Study resume & cost estimation (Story 21.5) -> R24-R28.

Public surfaces driven: ``plan_study_resume``, ``resume_stepper``,
``estimate_study_cost``, ``compute_winner_set`` (the one-line-per-run law). Includes
REGRESSION PIN-2 (T21-326). The process-per-run governor + concurrency cap are
Epic 15 (out of scope); the cap is a value passed in, never computed here.
"""

from __future__ import annotations

from conftest import (
    Fraction,
    RefusalCategory,
    aborted_line,
    assert_ct04_refusal,
    fp,
    int_param,
    is_ok,
    is_refusal,
    money_measure,
    run_id_of,
    trial_line,
    unwrap,
)

from qmb.optimize.resume import (
    ESTIMATE_STATUS_MEASURED,
    ESTIMATE_STATUS_NOT_YET_MEASURED,
    TrialBudget,
    estimate_study_cost,
    plan_study_resume,
    resume_stepper,
)
from qmb.optimize.objective import StudyObjective, StudyCriteria, compute_winner_set
from qmb.optimize.sampler import StudyStepper, propose_generation
from qmb.optimize.space import coerce_study_space
from qmf.core.fingerprint import World, fingerprint


def _space() -> object:
    return unwrap(
        coerce_study_space([int_param("a", lo=0, hi=100, step=1, default=10)]),
        "space",
    )


def _history(batch_size: int, complete_generations: int, partial: int = 0) -> list[dict[str, object]]:
    """A ledger-view read: `complete_generations` full generations + `partial` extra asks."""
    out: list[dict[str, object]] = []
    for g in range(complete_generations):
        for k in range(batch_size):
            out.append({"generation_index": g, "ask_index": k, "parameters": {"a": (g * 10 + k) % 100}, "objective": Fraction(g * 10 + k, 1)})
    for k in range(partial):
        out.append({"generation_index": complete_generations, "ask_index": k, "parameters": {"a": k}, "objective": Fraction(k, 1)})
    return out


# --- T21-323 [R24] -----------------------------------------------------------


def test_t21_323_resume_skips_completed_and_resumes_generation_index() -> None:
    """Completed trials are read from the ledger and not re-run; the index resumes forward.

    Counter-case that would FAIL: the resume generation index staying at 0 despite a
    full completed generation, or a resumed ask appearing in the pending (re-run) set.
    """
    batch_size = 4
    history = _history(batch_size, complete_generations=2, partial=1)  # gens 0,1 full; gen 2 ask 0 done
    plan = unwrap(plan_study_resume(history, batch_size=batch_size), "resume plan")

    assert plan.completed_generations == 2, "two full generations completed"
    assert plan.resume_generation == 2, "the deterministic index resumes from the last completed generation"
    assert plan.resumed_asks == (0,), "the one already-done ask of gen 2 is read, not re-run"
    assert set(plan.pending_asks) == {1, 2, 3}, "only the not-yet-run asks are pending"
    assert 0 not in plan.pending_asks, "a completed ask is never scheduled to re-run"


# --- T21-324 [R25] -----------------------------------------------------------


def test_t21_324_resume_uses_only_the_ledger_view() -> None:
    """Resume repositions from the ledger view alone; the pure port reproduces its proposal.

    Falsifiability: the resumed stepper's next ask is reconstructed BYTE-FOR-BYTE by the
    pure port fed the same conditioned history. If resume consulted a hidden optuna
    store/daemon, the reconstruction would diverge.
    """
    batch_size = 3
    history = _history(batch_size, complete_generations=1)  # gen 0 full
    base = StudyStepper(space=_space(), seed=5, direction="max", study_fp=unwrap(fingerprint({"s": 1})), batch_size=batch_size)

    stepper, plan = unwrap(resume_stepper(base, history), "resume stepper")
    assert stepper.generation_index == plan.resume_generation == 1
    assert len(stepper.completed) == batch_size, "the completed generation is conditioned on"

    # the repositioned stepper's ask equals a fresh pure-port proposal over the same history.
    resumed_batch = unwrap(stepper.ask(), "resumed ask")[1]
    reconstructed = unwrap(
        propose_generation(_space(), 5, list(stepper.completed), 1, direction="max", batch_size=batch_size),
        "reconstruction",
    )
    assert unwrap(resumed_batch.fingerprint()).value == unwrap(reconstructed.fingerprint()).value


# --- T21-325 [R26] -----------------------------------------------------------


def test_t21_325_cost_estimate_with_measured_baseline_uses_the_formula() -> None:
    """With a measured baseline, the estimate is total x runtime / cap, spawning no trial.

    Counter-case that would FAIL: a projected wall other than the exact formula value, or
    a status other than measured, or the estimate claiming to have spawned a trial.
    """
    budget = unwrap(TrialBudget.try_create("fixed", fixed_total=40), "budget")
    cap = 4
    runtime_ns = 1_000_000
    estimate = unwrap(estimate_study_cost(budget, per_trial_runtime=runtime_ns, concurrency_cap=cap), "estimate")

    assert estimate.status == ESTIMATE_STATUS_MEASURED
    assert estimate.projected_total_trials == 40
    assert estimate.projected_wall_ns == 40 * runtime_ns // cap, "wall = total x runtime // concurrency cap"
    assert estimate.spawns_trial is False, "an estimate spawns no trial"


# --- T21-326 [R27] P0 REGRESSION PIN-2 (invented peak-memory / not-yet-measured) --


def test_t21_326_no_baseline_is_not_yet_measured_never_invented() -> None:
    """With no measured baseline the estimate is not-yet-measured, never an invented figure.

    PIN-2 [R-013/R-017]. Counter-case that would FAIL: a synthesized projected wall (or
    any invented figure) returned in place of not-yet-measured. Expected to FAIL against
    current source if the finding is real; the actual outcome is recorded honestly. (The
    peak-memory sub-clause has no surface in this estimator — recorded UNPROVEN in
    RESULTS: memory budgeting is the Epic 15 governor, not the Study cost estimator.)
    """
    budget = unwrap(TrialBudget.try_create("fixed", fixed_total=100), "budget")
    estimate = unwrap(estimate_study_cost(budget, per_trial_runtime=None, concurrency_cap=8), "estimate")

    assert estimate.status == ESTIMATE_STATUS_NOT_YET_MEASURED, "no baseline -> not-yet-measured"
    assert estimate.per_trial_runtime_ns is None, "no per-trial runtime is invented"
    assert estimate.projected_wall_ns is None, "no projected wall is synthesized"
    # the identity carries no invented figure for the unmeasured projections.
    identity = estimate.fp1_identity()
    assert "per_trial_runtime_ns" not in identity
    assert "projected_wall_ns" not in identity


# --- T21-327 [R28] P0 R-010 one ledger line per spawned run ------------------


def test_t21_327_exactly_one_ledger_line_per_spawned_run() -> None:
    """Each spawned run is counted exactly once — an aborted run is kept, a collision refused.

    Counter-case that would FAIL: a spawned-but-aborted run silently dropped (zero lines),
    a byte-identical duplicate double-counting, or a second differing line for one run id
    being silently overwritten instead of refused (R-010: never zero, never two).
    """
    objective = unwrap(StudyObjective.try_create("net_profit", "max"))
    criteria = unwrap(StudyCriteria.try_create(objective), "criteria")

    completed_a = trial_line("a", [money_measure("net_profit", 10000)])
    completed_b = trial_line("b", [money_measure("net_profit", 20000)])
    aborted_c = aborted_line("c")  # spawned but terminated -> exactly one aborted line, never zero

    ws = unwrap(compute_winner_set([completed_a, completed_b, aborted_c], criteria, world=World.REPLAY), "ws")
    counted = {t.run_id.value for t in ws.winners} | {t.run_id.value for t in ws.incomplete}
    assert run_id_of("a") in counted and run_id_of("b") in counted
    assert run_id_of("c") in {t.run_id.value for t in ws.incomplete}, "the aborted run is kept, never zero lines"

    # a byte-identical duplicate collapses to one (never two).
    dup = unwrap(compute_winner_set([completed_a, completed_a], criteria, world=World.REPLAY), "dup ws")
    assert dup.winner_count == 1, "a byte-identical duplicate line collapses to one run"

    # a SECOND, DIFFERING line for one run id is a collision (never a silent overwrite / two lines).
    differing = trial_line("a", [money_measure("net_profit", 99999)])
    collision = compute_winner_set([completed_a, differing], criteria, world=World.REPLAY)
    assert_ct04_refusal(collision, RefusalCategory.POLICY_REJECTION, what="one-line-per-run collision")
