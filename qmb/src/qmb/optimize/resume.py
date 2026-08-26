"""Study resume from the ledger view and pre-flight cost estimation (B-8, B-4).

Two pure capabilities ride here, both spending no compute and spawning no trial.

**Resume (OPT-23, AC1/AC2).** An interrupted Study resumes from its completed
trials read off the **ledger view** — the same ``prior_trials`` shape the pure
sampler already conditions on (:func:`qmb.optimize.coerce_prior_trials`). No
in-process optuna study, daemon, or optuna store is consulted: the ledger is the
sole source of trial history (:data:`RESUME_SOURCE`). :func:`plan_study_resume`
folds the history into a :class:`StudyResumePlan` — how many generations fully
completed, which generation the deterministic index resumes from, and which asks
of the resume generation are already done (never re-run) versus still pending.
:func:`resume_stepper` repositions a fresh :class:`~qmb.optimize.StudyStepper` to
that point; because :func:`~qmb.optimize.propose_generation` is a pure function of
the completed prior generations, the repositioned stepper re-proposes the resume
generation byte-identically, so already-completed trials are skipped rather than
re-run (DEC-0169, AR-50).

**Estimate (OPT-17/OPT-24, AD-13, AC3/AC4).** Given an explicit trial-budget
policy — fixed N, scale-with-#params, or run-until-target/timeout
(:class:`TrialBudget`) — :func:`estimate_study_cost` reports the projected wall
cost as ``projected total trials x measured typical per-trial runtime / the
governor concurrency cap`` **without spawning any trial** (:data:`ESTIMATE_SPAWNS_TRIAL`).
Per AD-13 measure-then-budget: when no per-trial runtime baseline has yet been
measured the estimate is returned as :data:`ESTIMATE_STATUS_NOT_YET_MEASURED`
rather than an invented figure (NFR-04). The governor concurrency cap is the
caller's ``min(cpu, memory)`` parallelism bound, passed in — this pure port never
reads a budget value of its own (DEC-0157, DEC-0161).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Final, cast

from qmf.core.chrono import Duration
from qmf.core.refusal import Ok, Result, is_refusal

from qmb._refuse import clean_token, invalid, policy
from qmb.optimize.sampler import PriorTrial, StudyStepper, coerce_prior_trials

__all__ = [
    "COST_ESTIMATE_CLASS",
    "COST_ESTIMATE_FORMAT_VERSION",
    "ESTIMATE_SPAWNS_TRIAL",
    "ESTIMATE_STATUS_MEASURED",
    "ESTIMATE_STATUS_NOT_YET_MEASURED",
    "ESTIMATE_STATUS_OPEN_ENDED",
    "RESUME_CONSULTS_OPTUNA_STORE",
    "RESUME_SOURCE",
    "STUDY_RESUME_PLAN_CLASS",
    "STUDY_RESUME_PLAN_FORMAT_VERSION",
    "TRIAL_BUDGET_CLASS",
    "TRIAL_BUDGET_FIXED",
    "TRIAL_BUDGET_KINDS",
    "TRIAL_BUDGET_RUN_UNTIL",
    "TRIAL_BUDGET_SCALE_WITH_PARAMS",
    "CostEstimate",
    "StudyResumePlan",
    "TrialBudget",
    "cost_estimate_identity",
    "estimate_study_cost",
    "plan_study_resume",
    "resume_stepper",
    "study_resume_identity",
]

# Resume reads trial history from the ledger view only — never an in-process
# optuna study, daemon, or optuna's own store (AC2, B-4, AR-50, DEC-0169).
RESUME_SOURCE: Final[str] = "ledger-view"
RESUME_CONSULTS_OPTUNA_STORE: Final[bool] = False

STUDY_RESUME_PLAN_CLASS: Final[str] = "qmb-study-resume-plan"
STUDY_RESUME_PLAN_FORMAT_VERSION: Final[int] = 1

# The explicit trial-budget policy vocabulary (OPT-17). Every kind is declared in
# config; the budget policy is never inferred and no count is invented.
TRIAL_BUDGET_FIXED: Final[str] = "fixed"
TRIAL_BUDGET_SCALE_WITH_PARAMS: Final[str] = "scale-with-params"
TRIAL_BUDGET_RUN_UNTIL: Final[str] = "run-until-target-or-timeout"
TRIAL_BUDGET_KINDS: Final[tuple[str, ...]] = (
    TRIAL_BUDGET_FIXED,
    TRIAL_BUDGET_SCALE_WITH_PARAMS,
    TRIAL_BUDGET_RUN_UNTIL,
)
TRIAL_BUDGET_CLASS: Final[str] = "qmb-trial-budget"

COST_ESTIMATE_CLASS: Final[str] = "qmb-study-cost-estimate"
COST_ESTIMATE_FORMAT_VERSION: Final[int] = 1

# The estimate is a pure inspection — it spawns no trial and spends no compute
# (AC3, OPT-24).
ESTIMATE_SPAWNS_TRIAL: Final[bool] = False

# A concrete projected wall was computed from a measured baseline.
ESTIMATE_STATUS_MEASURED: Final[str] = "measured"
# No per-trial runtime baseline has been measured — never an invented figure
# (AC4, AD-13 measure-then-budget, NFR-04).
ESTIMATE_STATUS_NOT_YET_MEASURED: Final[str] = "not-yet-measured"
# A run-until-target policy has no fixed trial count; the wall is open-ended
# unless a timeout ceiling is declared.
ESTIMATE_STATUS_OPEN_ENDED: Final[str] = "open-ended"


def study_resume_identity() -> dict[str, object]:
    """Identity-bearing resume-port fields. Package SemVer is omitted (AC2)."""
    return {
        "class": "qmb-study-resume",
        "consults_optuna_store": RESUME_CONSULTS_OPTUNA_STORE,
        "source": RESUME_SOURCE,
    }


def cost_estimate_identity() -> dict[str, object]:
    """Identity-bearing estimate-port fields. Package SemVer is omitted (AC3)."""
    return {
        "budget_kinds": TRIAL_BUDGET_KINDS,
        "class": "qmb-study-cost-estimator",
        "formula": "projected_total_trials * per_trial_runtime_ns // concurrency_cap",
        "measure_then_budget": True,
        "spawns_trial": ESTIMATE_SPAWNS_TRIAL,
    }


# --- resume from the ledger view (AC1, AC2) ----------------------------------


@dataclass(frozen=True, slots=True)
class StudyResumePlan:
    """How an interrupted Study resumes from its completed ledger-view trials (AC1).

    ``completed_generations`` counts the fully-complete generations read from the
    ledger (a contiguous prefix under the barrier discipline); ``resume_generation``
    is the deterministic generation index the sampler resumes from — the same value
    as ``completed_generations``, named separately because it is the *next* index to
    propose. ``resumed_asks`` are the ask indices of the resume generation already
    present in the ledger (**not re-run**); ``pending_asks`` are the ones still to
    run. ``conditioned`` is the prior-trial history from the fully-complete
    generations the repositioned stepper conditions on.
    """

    batch_size: int
    completed_generations: int
    resume_generation: int
    conditioned: tuple[PriorTrial, ...]
    resumed_asks: tuple[int, ...]
    pending_asks: tuple[int, ...]
    total_completed_trials: int

    @property
    def has_partial_resume_generation(self) -> bool:
        """Whether the resume generation carries some completed trials already."""
        return bool(self.resumed_asks)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Deterministic over the ledger read (NFR-03)."""
        return {
            "batch_size": self.batch_size,
            "class": STUDY_RESUME_PLAN_CLASS,
            "completed_generations": self.completed_generations,
            "conditioned": [item.fp1_identity() for item in self.conditioned],
            "format_version": STUDY_RESUME_PLAN_FORMAT_VERSION,
            "pending_asks": list(self.pending_asks),
            "resume_generation": self.resume_generation,
            "resumed_asks": list(self.resumed_asks),
            "source": RESUME_SOURCE,
            "total_completed_trials": self.total_completed_trials,
        }


def plan_study_resume(history: object, *, batch_size: object) -> Result[StudyResumePlan]:
    """Plan a Study resume from its completed ledger-view trials (AC1, AC2, OPT-23).

    ``history`` is the ledger view's completed trials — a sequence of
    :class:`~qmb.optimize.PriorTrial` or ``{generation_index, ask_index, parameters,
    objective}`` mappings, in any order. A generation is *complete* once all
    ``batch_size`` asks report; the resume generation is the first not-yet-complete
    generation (or the count of complete generations when none is partial). No trial
    is re-run and no optuna store is consulted — the ledger is the sole source
    (DEC-0169).
    """
    size = _positive_int(batch_size, "batch_size")
    if is_refusal(size):
        return size
    parsed = coerce_prior_trials(history)
    if is_refusal(parsed):
        return parsed
    priors = parsed.value
    by_generation: dict[int, set[int]] = {}
    for trial in priors:
        if trial.ask_index >= size.value:
            return policy(
                "history",
                "a completed trial's ask index is within the declared generation "
                "batch size; a larger index is an inconsistent ledger read (AR-50)",
                generation_index=trial.generation_index,
                ask_index=trial.ask_index,
                batch_size=size.value,
            )
        by_generation.setdefault(trial.generation_index, set()).add(trial.ask_index)
    resume_generation = 0
    while len(by_generation.get(resume_generation, set())) == size.value:
        resume_generation += 1
    ahead = sorted(gen for gen in by_generation if gen > resume_generation)
    if ahead:
        return policy(
            "history",
            "a completed trial sits in a generation ahead of the first incomplete "
            "one; the barrier discipline forbids conditioning on it — an inconsistent "
            "ledger read (AR-50, DEC-0169)",
            resume_generation=resume_generation,
            ahead_generations=ahead,
        )
    conditioned = tuple(trial for trial in priors if trial.generation_index < resume_generation)
    resumed = tuple(sorted(by_generation.get(resume_generation, set())))
    pending = tuple(index for index in range(size.value) if index not in set(resumed))
    return Ok(
        StudyResumePlan(
            batch_size=size.value,
            completed_generations=resume_generation,
            resume_generation=resume_generation,
            conditioned=conditioned,
            resumed_asks=resumed,
            pending_asks=pending,
            total_completed_trials=len(priors),
        )
    )


def resume_stepper(base: object, history: object) -> Result[tuple[StudyStepper, StudyResumePlan]]:
    """Reposition a fresh stepper to its resume point from the ledger view (AC1, AC2).

    ``base`` is a fresh :class:`~qmb.optimize.StudyStepper` (generation index 0, no
    completed trials, no outstanding generation) seeded from the admitted Study;
    ``history`` is the ledger-view read of completed trials. The returned stepper
    carries the fully-complete generations as ``completed`` and its generation index
    advanced to the resume generation, so its next ``ask`` re-proposes that
    generation deterministically. Pair it with the plan's ``pending_asks`` to run
    only the trials the ledger does not already hold — completed trials are not
    re-run (OPT-23).
    """
    if not isinstance(base, StudyStepper):
        return invalid(
            "base",
            "a resume repositions a fresh StudyStepper seeded from the admitted Study",
            given=repr(type(base).__name__),
        )
    if base.generation_index != 0 or base.completed or base.outstanding is not None:
        return invalid(
            "base",
            "a resume starts from a fresh stepper — generation index 0, no completed "
            "trials, no outstanding generation; the ledger view supplies the history",
            generation_index=base.generation_index,
            completed=len(base.completed),
            has_outstanding=base.outstanding is not None,
        )
    plan = plan_study_resume(history, batch_size=base.batch_size)
    if is_refusal(plan):
        return plan
    stepper = replace(
        base,
        completed=plan.value.conditioned,
        generation_index=plan.value.resume_generation,
    )
    return Ok((stepper, plan.value))


# --- pre-flight cost estimation (AC3, AC4) -----------------------------------


@dataclass(frozen=True, slots=True)
class TrialBudget:
    """An explicit trial-budget policy declared in config (OPT-17, AC3).

    Exactly one kind: ``fixed`` carries ``fixed_total`` (N); ``scale-with-params``
    carries ``per_param_factor`` and scales as ``factor x #params``; the
    ``run-until-target-or-timeout`` kind has no fixed trial count and carries an
    optional ``timeout_ns`` wall ceiling and/or ``runs_until_target``. No factor
    or count is invented — every field is caller-declared (NFR-07).
    """

    kind: str
    fixed_total: int | None = None
    per_param_factor: int | None = None
    timeout_ns: int | None = None
    runs_until_target: bool = False

    @classmethod
    def try_create(
        cls,
        kind: object,
        *,
        fixed_total: object = None,
        per_param_factor: object = None,
        timeout_ns: object = None,
        runs_until_target: object = False,
    ) -> Result[TrialBudget]:
        """Validate one explicit trial-budget policy, value-or-refusal (OPT-17)."""
        token = clean_token(kind)
        if token is None or token not in TRIAL_BUDGET_KINDS:
            return invalid(
                "kind",
                "a trial-budget policy is fixed, scale-with-params, or run-until-target-or-timeout",
                given=repr(kind),
                allowed=list(TRIAL_BUDGET_KINDS),
            )
        if not isinstance(runs_until_target, bool):
            return invalid(
                "runs_until_target",
                "runs_until_target is a boolean flag",
                given=repr(runs_until_target),
            )
        if token == TRIAL_BUDGET_FIXED:
            total = _positive_int(fixed_total, "fixed_total")
            if is_refusal(total):
                return total
            return Ok(cls(kind=token, fixed_total=total.value))
        if token == TRIAL_BUDGET_SCALE_WITH_PARAMS:
            factor = _positive_int(per_param_factor, "per_param_factor")
            if is_refusal(factor):
                return factor
            return Ok(cls(kind=token, per_param_factor=factor.value))
        timeout: int | None = None
        if timeout_ns is not None:
            parsed_timeout = _positive_int(timeout_ns, "timeout_ns")
            if is_refusal(parsed_timeout):
                return parsed_timeout
            timeout = parsed_timeout.value
        if timeout is None and not runs_until_target:
            return invalid(
                "run_until",
                "a run-until policy declares a target, a timeout, or both; an empty "
                "run-until budget has no stopping rule",
            )
        return Ok(cls(kind=token, timeout_ns=timeout, runs_until_target=runs_until_target))

    def projected_total_trials(self, param_count: object) -> Result[int | None]:
        """The projected total trials for this policy, or ``None`` when open-ended.

        ``fixed`` returns N; ``scale-with-params`` returns ``factor x #params`` for a
        positive parameter count; ``run-until-target-or-timeout`` returns ``None`` —
        its trial count is open-ended and never invented (OPT-17, OPT-24).
        """
        if self.kind == TRIAL_BUDGET_FIXED:
            return Ok(self.fixed_total)
        if self.kind == TRIAL_BUDGET_SCALE_WITH_PARAMS:
            count = _positive_int(param_count, "param_count")
            if is_refusal(count):
                return count
            factor = self.per_param_factor if self.per_param_factor is not None else 0
            return Ok(factor * count.value)
        return Ok(None)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Only the declared fields ride."""
        content: dict[str, object] = {"class": TRIAL_BUDGET_CLASS, "kind": self.kind}
        if self.fixed_total is not None:
            content["fixed_total"] = self.fixed_total
        if self.per_param_factor is not None:
            content["per_param_factor"] = self.per_param_factor
        if self.timeout_ns is not None:
            content["timeout_ns"] = self.timeout_ns
        if self.kind == TRIAL_BUDGET_RUN_UNTIL:
            content["runs_until_target"] = self.runs_until_target
        return content


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """A pre-flight cost estimate — computed, never measured by spawning (AC3, AC4).

    ``projected_total_trials`` is the budget's trial count (``None`` for an
    open-ended run-until policy); ``per_trial_runtime_ns`` is the measured typical
    baseline (``None`` when not yet measured); ``concurrency_cap`` is the governor's
    ``min(cpu, memory)`` parallelism bound; ``projected_wall_ns`` is
    ``projected_total_trials x per_trial_runtime_ns // concurrency_cap`` — ``None``
    while the baseline is unmeasured (:data:`ESTIMATE_STATUS_NOT_YET_MEASURED`) or
    the budget is open-ended with no timeout ceiling. ``spawns_trial`` is always
    false.
    """

    status: str
    budget_kind: str
    projected_total_trials: int | None
    per_trial_runtime_ns: int | None
    concurrency_cap: int
    projected_wall_ns: int | None
    timeout_ns: int | None = None
    spawns_trial: bool = ESTIMATE_SPAWNS_TRIAL

    @property
    def measured(self) -> bool:
        """Whether a per-trial runtime baseline was available (AC4)."""
        return self.status != ESTIMATE_STATUS_NOT_YET_MEASURED

    def projected_wall_duration(self) -> Result[Duration] | None:
        """The projected wall as a :class:`Duration`, or ``None`` when unprojectable."""
        if self.projected_wall_ns is None:
            return None
        return Duration.try_create(self.projected_wall_ns)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. No binary float enters here (AD-10)."""
        content: dict[str, object] = {
            "budget_kind": self.budget_kind,
            "class": COST_ESTIMATE_CLASS,
            "concurrency_cap": self.concurrency_cap,
            "format_version": COST_ESTIMATE_FORMAT_VERSION,
            "spawns_trial": self.spawns_trial,
            "status": self.status,
        }
        if self.projected_total_trials is not None:
            content["projected_total_trials"] = self.projected_total_trials
        if self.per_trial_runtime_ns is not None:
            content["per_trial_runtime_ns"] = self.per_trial_runtime_ns
        if self.projected_wall_ns is not None:
            content["projected_wall_ns"] = self.projected_wall_ns
        if self.timeout_ns is not None:
            content["timeout_ns"] = self.timeout_ns
        return content


def estimate_study_cost(
    budget: object,
    *,
    param_count: object = None,
    per_trial_runtime: object = None,
    concurrency_cap: object,
) -> Result[CostEstimate]:
    """Estimate a Study's wall cost before committing compute (AC3, AC4, OPT-24).

    Reports ``projected total trials x measured typical per-trial runtime / the
    governor concurrency cap`` **without spawning any trial**. When no per-trial
    runtime baseline has been measured the estimate is
    :data:`ESTIMATE_STATUS_NOT_YET_MEASURED` rather than an invented figure (AD-13
    measure-then-budget, NFR-04). ``concurrency_cap`` is the caller's governor
    ``min(cpu, memory)`` parallelism bound; ``per_trial_runtime`` is a
    :class:`Duration`, a non-negative nanosecond int, or ``None``.
    """
    parsed_budget = _coerce_budget(budget)
    if is_refusal(parsed_budget):
        return parsed_budget
    cap = _positive_int(concurrency_cap, "concurrency_cap")
    if is_refusal(cap):
        return cap
    total = parsed_budget.value.projected_total_trials(param_count)
    if is_refusal(total):
        return total
    baseline = _coerce_runtime_ns(per_trial_runtime)
    if is_refusal(baseline):
        return baseline
    budget_value = parsed_budget.value
    if baseline.value is None:
        # AD-13 measure-then-budget: never invent a per-trial runtime (AC4).
        return Ok(
            CostEstimate(
                status=ESTIMATE_STATUS_NOT_YET_MEASURED,
                budget_kind=budget_value.kind,
                projected_total_trials=total.value,
                per_trial_runtime_ns=None,
                concurrency_cap=cap.value,
                projected_wall_ns=None,
                timeout_ns=budget_value.timeout_ns,
            )
        )
    if total.value is None:
        # A run-until-target policy has no fixed count; the wall ceiling is the
        # declared timeout, if any — otherwise open-ended, never invented.
        return Ok(
            CostEstimate(
                status=ESTIMATE_STATUS_OPEN_ENDED,
                budget_kind=budget_value.kind,
                projected_total_trials=None,
                per_trial_runtime_ns=baseline.value,
                concurrency_cap=cap.value,
                projected_wall_ns=budget_value.timeout_ns,
                timeout_ns=budget_value.timeout_ns,
            )
        )
    projected_wall_ns = total.value * baseline.value // cap.value
    return Ok(
        CostEstimate(
            status=ESTIMATE_STATUS_MEASURED,
            budget_kind=budget_value.kind,
            projected_total_trials=total.value,
            per_trial_runtime_ns=baseline.value,
            concurrency_cap=cap.value,
            projected_wall_ns=projected_wall_ns,
            timeout_ns=budget_value.timeout_ns,
        )
    )


# --- coercion helpers --------------------------------------------------------


def _coerce_budget(value: object) -> Result[TrialBudget]:
    if isinstance(value, TrialBudget):
        return Ok(value)
    if isinstance(value, Mapping):
        body = cast("Mapping[str, object]", value)
        return TrialBudget.try_create(
            body.get("kind"),
            fixed_total=body.get("fixed_total"),
            per_param_factor=body.get("per_param_factor"),
            timeout_ns=body.get("timeout_ns"),
            runs_until_target=body.get("runs_until_target", False),
        )
    return invalid(
        "budget",
        "a trial-budget policy is a TrialBudget or a {kind, ...} mapping",
        given=repr(type(value).__name__),
    )


def _coerce_runtime_ns(value: object) -> Result[int | None]:
    """Coerce a measured per-trial runtime baseline to nanoseconds, or ``None``.

    ``None`` means no baseline has been measured (AC4). A :class:`Duration` or a
    non-negative int is accepted; a binary float is refused — the estimate identity
    carries exact nanoseconds only (AD-10).
    """
    if value is None:
        return Ok(None)
    if isinstance(value, Duration):
        return _non_negative_ns(value.value_ns)
    if isinstance(value, bool):
        return invalid(
            "per_trial_runtime",
            "a measured per-trial runtime is a Duration or nanosecond int, never a boolean",
        )
    if isinstance(value, float):
        return invalid(
            "per_trial_runtime",
            "a measured per-trial runtime baseline is exact nanoseconds; a binary float "
            "is refused (AD-10)",
            given=repr(value),
        )
    if isinstance(value, int):
        return _non_negative_ns(value)
    if isinstance(value, Mapping):
        raw = cast("Mapping[str, object]", value).get("value_ns")
        if isinstance(raw, bool) or not isinstance(raw, int):
            return invalid(
                "per_trial_runtime",
                "a runtime mapping carries value_ns as a nanosecond int",
                given=repr(raw),
            )
        return _non_negative_ns(raw)
    return invalid(
        "per_trial_runtime",
        "a measured per-trial runtime is a Duration, a nanosecond int, or None",
        given=repr(type(value).__name__),
    )


def _non_negative_ns(value: int) -> Result[int | None]:
    if value < 0:
        return invalid(
            "per_trial_runtime",
            "a measured per-trial runtime is a non-negative nanosecond quantity",
            given=value,
        )
    result: int | None = value
    return Ok(result)


def _positive_int(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return invalid(field, "a positive exact integer is required", given=repr(value))
    return Ok(value)
