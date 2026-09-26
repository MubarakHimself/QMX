"""Reference usage — Study resume from the ledger view and cost estimation (Story 21.5).

Executable::

    python qmb/examples/optimize_resume_usage.py

Shows the things B-8 / B-4 / OPT-17 / OPT-23 / OPT-24 / Story 21.5 pin down:

1. An interrupted Study resumes from its completed trials read off the LEDGER
   VIEW: the deterministic generation index resumes from the last completed
   generation, and already-completed trials are read, not re-run. No in-process
   optuna study, daemon, or optuna store is consulted.
2. A partially-completed generation resumes without re-running its done trials —
   the re-proposed generation is byte-identical because the sampler is a pure
   function of the completed prior generations.
3. A pre-flight cost estimate reports projected total trials x measured typical
   per-trial runtime / the governor concurrency cap WITHOUT spawning any trial.
4. With no measured per-trial baseline the estimate is 'not-yet-measured' rather
   than an invented figure (AD-13 measure-then-budget).
5. The estimate is reachable through the qmb CLI door.
"""

from __future__ import annotations

from fractions import Fraction
from typing import TypeVar

from qmb.doors.cli.tree import invoke_optimize_estimate
from qmf.core.chrono import Duration
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_R = UnitKind.DIMENSIONLESS_RATIO


def _ok(result: Result[T]) -> T:
    if not is_ok(result):
        raise AssertionError(result)
    return result.value


def _space() -> qmb.StudyParameterSpace:
    return _ok(
        qmb.coerce_study_space(
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


def _fresh() -> qmb.StudyStepper:
    return qmb.StudyStepper(
        space=_space(),
        seed=4242,
        direction="max",
        study_fp=_ok(fingerprint({"study": "resume-demo"})),
        batch_size=4,
    )


def _priors(batch: qmb.ParameterBatch, only: set[int] | None = None) -> list[dict[str, object]]:
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


def main() -> None:
    # (1) Drive a fresh Study one generation, then a second — capture gen-1 as the
    # deterministic target the resume must reproduce.
    stepper = _fresh()
    after0, gen0 = _ok(stepper.ask())
    told = _ok(after0.tell(_priors(gen0)))
    _after1, gen1 = _ok(told.ask())
    target_gen1 = _ok(gen1.fingerprint())

    # (2) Resume from the ledger view — only generation 0 completed.
    resumed, plan = _ok(qmb.resume_stepper(_fresh(), _priors(gen0)))
    print("study resume ok")
    print(
        f"completed_generations={plan.completed_generations} "
        f"resume_generation={plan.resume_generation}"
    )
    print("resumes from the last completed generation")
    print(f"ledger is the sole source: consults_optuna_store={qmb.RESUME_CONSULTS_OPTUNA_STORE}")
    _next, resumed_gen1 = _ok(resumed.ask())
    if _ok(resumed_gen1.fingerprint()) != target_gen1:
        raise AssertionError("resume must re-propose the same generation")
    print("completed trials are not re-run (re-proposal is byte-identical)")

    # (3) Partial generation: two of four asks of generation 1 already in the ledger.
    partial_plan = _ok(qmb.plan_study_resume(_priors(gen0) + _priors(gen1, {1, 3}), batch_size=4))
    print(
        f"partial resume: resumed_asks={partial_plan.resumed_asks} "
        f"pending_asks={partial_plan.pending_asks}"
    )

    # (4) Pre-flight cost estimate — measured baseline, spawns no trial.
    budget = _ok(qmb.TrialBudget.try_create("fixed", fixed_total=10))
    estimate = _ok(
        qmb.estimate_study_cost(
            budget,
            per_trial_runtime=_ok(Duration.try_create(2_000_000_000)),
            concurrency_cap=4,
        )
    )
    print(f"estimate status={estimate.status} projected_wall_ns={estimate.projected_wall_ns}")
    print(f"spawns no trial: spawns_trial={estimate.spawns_trial}")

    # (5) No measured baseline -> not-yet-measured, never an invented figure.
    blank = _ok(qmb.estimate_study_cost(budget, per_trial_runtime=None, concurrency_cap=4))
    if blank.projected_wall_ns is not None:
        raise AssertionError("an unmeasured baseline invents no wall")
    print(f"no baseline -> {blank.status}")

    # (6) Reachable through the qmb CLI door; a missing budget is a typed refusal.
    through_door = _ok(
        invoke_optimize_estimate(
            budget={"kind": "fixed", "fixed_total": 12},
            per_trial_runtime=1_000_000_000,
            concurrency_cap=6,
        )
    )
    if through_door.projected_total_trials != 12 or not is_refusal(
        invoke_optimize_estimate(concurrency_cap=4)
    ):
        raise AssertionError("the CLI door estimates and refuses a missing budget")
    print("through the qmb CLI door")


if __name__ == "__main__":
    main()
