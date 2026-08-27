"""The pure, generation-stepped Optuna TPE-class default sampler port (B-8, AR-50).

A parameter-optimization Study proposes trials with a genuinely adaptive
TPE-class sampler — the ``optuna`` adapter pinned by ``registry:qmb_sampler_pin``
(DEC-0168). Two facts govern how it is driven, and they are what this module
pins down:

* **The sampler port is PURE.** :func:`propose_generation` is a deterministic
  function of exactly ``(declared space, seed, prior trial results, generation
  index)`` — the same four inputs always yield the same batch. Trial history is
  read from the **ledger view** the caller passes in, never from an in-process
  optuna study, a daemon, or optuna's own store: the port holds no state between
  calls, and the transient in-memory study it builds per call is seeded
  deterministically and fed only the passed-in prior trials, canonically ordered
  so completion order cannot change the model (AR-50; DEC-0169).

* **Search steps in deterministic generations.** The orchestrator drives the
  Study *propose -> run -> barrier -> condition*: it proposes a generation, runs
  the batch process-per-run under the Epic 15 governor with the adapter pinned
  ``n_jobs=1``, barriers the whole generation, conditions the sampler on the
  completed generation, then proposes the next. Because a generation is proposed
  as a pure function of the completed prior generations, two runs of the same
  seeded Study propose identical trials regardless of completion order. A second
  ask before the outstanding generation's tell is refused ``unsupported
  capability`` for the TPE-class adapter (:class:`StudyStepper`; FM-5).

Two more disciplines ride here. The adapter may float internally, but a sampled
value enters the resolved run-config only through a **named AD-7/AD-22
conversion** — a declared rounding mode and target scale — and only the
converted exact value is identity-bearing; the internal float never enters
identity (:func:`convert_sampled_value`; AD-7/AD-22). And every trial ledgers as
``role = trial`` carrying **sampler identity + seed + generator provenance +
study_fp** on its label (:func:`trial_label`), so re-running the trial under its
resolved config reproduces its CT-32 fingerprint or refuses — and a future
optuna major bump is a contract-versioning event, never a transparent update
(:func:`refuse_sampler_contract_bump`; AR-29).

The pin *value* lives in the registry and the distribution manifest, never
restated here; this module references ``qmb_sampler_pin`` and reads the installed
optuna version at runtime as generator provenance (DEC-0168).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from fractions import Fraction
from importlib.metadata import PackageNotFoundError, version
from math import floor
from typing import Final, cast

import optuna
from optuna.distributions import (
    BaseDistribution,
    CategoricalDistribution,
    FloatDistribution,
    IntDistribution,
)
from optuna.samplers import TPESampler
from optuna.trial import create_trial
from qmf.core.chrono import Instant
from qmf.core.exact import MAX_SCALE, ExactRational, RoundingMode
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal
from qml.declaration.parameters import ParameterSpec, ParameterType

from qmb._refuse import clean_token, invalid, unsupported
from qmb.ledger.line import ROLE_TRIAL
from qmb.optimize.objective import DIRECTION_MAX, OBJECTIVE_DIRECTIONS
from qmb.optimize.space import StudyParameterSpace, coerce_study_space
from qmb.registryread import RegistryReadPort

# optuna logs "A new study created in memory ..." at INFO on every construction;
# the port builds one transient study per call, so silence that operational noise
# (a log, never evidence — L-logs). Verbosity is optuna-global and idempotent.
optuna.logging.set_verbosity(optuna.logging.WARNING)

__all__ = [
    "DEFAULT_RATIONAL_SCALE",
    "DEFAULT_ROUNDING",
    "GENERATION_SEED_CLASS",
    "PARAMETER_BATCH_CLASS",
    "PARAMETER_BATCH_FORMAT_VERSION",
    "PRIOR_TRIAL_CLASS",
    "PROPOSED_TRIAL_CLASS",
    "SAMPLED_VALUE_CLASS",
    "SAMPLER_CONSULTS_OPTUNA_STORE",
    "SAMPLER_FAMILY",
    "SAMPLER_GENERATOR",
    "SAMPLER_JOBS",
    "SAMPLER_LIBRARY",
    "SAMPLER_PARALLEL_ASK",
    "SAMPLER_PIN_KEY",
    "SAMPLER_STEPPING",
    "SAMPLER_TRIAL_ROLE",
    "STUDY_ARTIFACT_CLASS",
    "STUDY_ARTIFACT_FORMAT_VERSION",
    "STUDY_LABEL_CLASS",
    "TRIAL_LABEL_CLASS",
    "TRIAL_LABEL_FORMAT_VERSION",
    "AdmittedStudy",
    "ConvertedValue",
    "ParameterBatch",
    "PriorTrial",
    "ProposedTrial",
    "StudyArtifact",
    "StudyLabel",
    "StudyStepper",
    "admit_study",
    "coerce_prior_trials",
    "convert_sampled_value",
    "generator_provenance",
    "propose_generation",
    "refuse_parallel_ask",
    "refuse_sampler_contract_bump",
    "sampler_identity",
    "trial_label",
]

# The registry pin key for the default adapter — referenced, never restated as a
# spine value; its change is a contract-versioning event (DEC-0168, AR-29).
SAMPLER_PIN_KEY: Final[str] = "qmb_sampler_pin"

# Adapters run n_jobs=1: process fan-out belongs to the orchestrator, never the
# sampler (DEC-0168, DEC-0161).
SAMPLER_JOBS: Final[int] = 1

# The adaptive family and its optuna generator. The default sampler is genuinely
# adaptive (TPE-class), not a grid/Sobol adapter (DEC-0169).
SAMPLER_FAMILY: Final[str] = "tpe-class"
SAMPLER_LIBRARY: Final[str] = "optuna"
SAMPLER_GENERATOR: Final[str] = "TPESampler"

# Adaptive search steps in deterministic generations: propose -> barrier ->
# condition. A parallel ask without an intervening tell is unsupported for the
# TPE-class adapter (a grid/Sobol adapter could ask a declared batch) (FM-5).
SAMPLER_STEPPING: Final[str] = "generation-barrier"
SAMPLER_PARALLEL_ASK: Final[bool] = False

# Trial history is the ledger view, never optuna's own store (AR-50, DEC-0169).
SAMPLER_CONSULTS_OPTUNA_STORE: Final[bool] = False

# Every proposed trial is a first-class B-3/B-4 run with role = trial (DEC-0169).
SAMPLER_TRIAL_ROLE: Final[str] = ROLE_TRIAL

# The declared default rounding mode for the named AD-7/AD-22 conversion boundary.
# Half-to-even is the unbiased default; a caller may declare another mode. The
# mode is identity-bearing content of every converted value (AD-7/AD-22).
DEFAULT_ROUNDING: Final[RoundingMode] = RoundingMode.HALF_EVEN

# The fallback target scale for an exact-rational parameter whose step is not a
# terminating decimal; a terminating step derives its own exact scale.
DEFAULT_RATIONAL_SCALE: Final[int] = 12

GENERATION_SEED_CLASS: Final[str] = "qmb-generation-seed"
SAMPLED_VALUE_CLASS: Final[str] = "qmb-sampled-value"
PROPOSED_TRIAL_CLASS: Final[str] = "qmb-proposed-trial"
PARAMETER_BATCH_CLASS: Final[str] = "qmb-parameter-batch"
PARAMETER_BATCH_FORMAT_VERSION: Final[int] = 1
PRIOR_TRIAL_CLASS: Final[str] = "qmb-prior-trial"
STUDY_ARTIFACT_CLASS: Final[str] = "qmb-study-artifact"
STUDY_ARTIFACT_FORMAT_VERSION: Final[int] = 1
STUDY_LABEL_CLASS: Final[str] = "qmb-study-label"
TRIAL_LABEL_CLASS: Final[str] = "qmb-optimize-trial-label"
TRIAL_LABEL_FORMAT_VERSION: Final[int] = 1


# --- identity surfaces -------------------------------------------------------


def sampler_identity() -> dict[str, object]:
    """Identity-bearing sampler-port fields. The pin *value* and SemVer are omitted."""
    return {
        "class": "qmb-sampler",
        "consults_optuna_store": SAMPLER_CONSULTS_OPTUNA_STORE,
        "family": SAMPLER_FAMILY,
        "jobs": SAMPLER_JOBS,
        "parallel_ask": SAMPLER_PARALLEL_ASK,
        "pin_key": SAMPLER_PIN_KEY,
        "stepping": SAMPLER_STEPPING,
        "trial_role": SAMPLER_TRIAL_ROLE,
    }


def generator_provenance() -> dict[str, object]:
    """The generator provenance every trial label carries (AC6, AR-29).

    Names the optuna generator and the seed recipe, and records the *installed*
    optuna version read at runtime — so a future optuna major bump changes the
    provenance stamp, making the bump a visible contract-versioning event rather
    than a transparent update. The pin value is never restated; the runtime
    version is read, not hard-coded (DEC-0168).
    """
    runtime, major = _optuna_runtime_version()
    return {
        "library": SAMPLER_LIBRARY,
        "major_version": major,
        "pin_key": SAMPLER_PIN_KEY,
        "runtime_version": runtime,
        "sampler": SAMPLER_GENERATOR,
        "seed_recipe": "fp1(seed, generation_index)",
    }


def _optuna_runtime_version() -> tuple[str, int]:
    """The installed optuna version and its major, read at runtime (never hard-coded)."""
    try:
        runtime = version(SAMPLER_LIBRARY)
    except PackageNotFoundError:
        return ("unresolved", -1)
    head = runtime.split(".", 1)[0]
    major = int(head) if head.isdigit() else -1
    return (runtime, major)


# --- the named AD-7/AD-22 conversion -----------------------------------------


@dataclass(frozen=True, slots=True)
class ConvertedValue:
    """One sampled parameter value after the named AD-7/AD-22 conversion (AC4).

    ``value`` is the identity-bearing converted value — a plain ``int`` for an
    exact-integer (or money minor-unit) parameter, an :class:`ExactRational` for
    an exact-rational parameter, a token for a categorical, a ``bool`` for a
    boolean. ``conversion`` records the declared ``{rounding, scale}`` for a
    numeric parameter whose adapter representation was a float (identity-bearing),
    and is ``None`` for a categorical/boolean parameter that never floats. The
    internal float is discarded here — it never reaches :meth:`fp1_identity`.
    """

    name: str
    value: object
    conversion: Mapping[str, object] | None = None

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. The converted value rides; no float does."""
        content: dict[str, object] = {
            "class": SAMPLED_VALUE_CLASS,
            "name": self.name,
            "value": _value_identity(self.value),
        }
        if self.conversion is not None:
            content["conversion"] = dict(self.conversion)
        return content


def convert_sampled_value(
    spec: object,
    sampled: object,
    *,
    rounding: object = DEFAULT_ROUNDING,
    scale: object = None,
) -> Result[ConvertedValue]:
    """Convert one adapter-sampled value to its identity-bearing form (AC4, AD-7/AD-22).

    For an exact-integer or exact-rational parameter the value passes the named
    float conversion boundary under the declared ``rounding`` mode at the target
    ``scale`` (derived from the parameter's step when not given), then snaps to the
    declared step grid — so only the converted exact value, and the identity-bearing
    ``{rounding, scale}`` stamp, enter identity; the internal float never does. A
    categorical or boolean value never floats and is returned verbatim.
    """
    if not isinstance(spec, ParameterSpec):
        return invalid(
            "spec",
            "a sampled value is converted against its CT-33 ParameterSpec",
            given=repr(type(spec).__name__),
        )
    if spec.type is ParameterType.CATEGORICAL:
        return _convert_categorical(spec, sampled)
    if spec.type is ParameterType.BOOLEAN:
        return _convert_boolean(spec, sampled)
    mode = _coerce_rounding(rounding)
    if is_refusal(mode):
        return mode
    target_scale = _resolve_scale(spec, scale)
    if is_refusal(target_scale):
        return target_scale
    numeric = _coerce_float(sampled, spec.name)
    if is_refusal(numeric):
        return numeric
    converted = ExactRational.from_float(
        numeric.value,
        unit_kind=spec.unit_kind,
        scale=target_scale.value,
        rounding=mode.value,
    )
    if is_refusal(converted):
        return converted
    snapped = _snap_to_grid(converted.value.as_fraction(), spec)
    if is_refusal(snapped):
        return snapped
    stamp: dict[str, object] = {"rounding": mode.value.value, "scale": target_scale.value}
    if spec.type is ParameterType.EXACT_INTEGER:
        return Ok(ConvertedValue(name=spec.name, value=int(snapped.value), conversion=stamp))
    rebuilt = ExactRational.try_create(
        snapped.value.numerator, snapped.value.denominator, spec.unit_kind
    )
    if is_refusal(rebuilt):
        return rebuilt
    return Ok(ConvertedValue(name=spec.name, value=rebuilt.value, conversion=stamp))


def _convert_categorical(spec: ParameterSpec, sampled: object) -> Result[ConvertedValue]:
    token = clean_token(sampled)
    options = spec.bounds or ()
    if token is None or token not in options:
        return invalid(
            "value",
            "a categorical sample is one of the declared options",
            parameter=spec.name,
            given=repr(sampled),
            allowed=[str(item) for item in options],
        )
    return Ok(ConvertedValue(name=spec.name, value=token, conversion=None))


def _convert_boolean(spec: ParameterSpec, sampled: object) -> Result[ConvertedValue]:
    if not isinstance(sampled, bool):
        return invalid(
            "value",
            "a boolean sample is true or false",
            parameter=spec.name,
            given=repr(sampled),
        )
    return Ok(ConvertedValue(name=spec.name, value=sampled, conversion=None))


def _resolve_scale(spec: ParameterSpec, scale: object) -> Result[int]:
    if scale is not None:
        if isinstance(scale, bool) or not isinstance(scale, int) or scale < 0 or scale > MAX_SCALE:
            return invalid(
                "scale",
                "the target scale is an integer count of decimal places within the exact bound",
                given=repr(scale),
                max_scale=MAX_SCALE,
            )
        return Ok(scale)
    if spec.type is ParameterType.EXACT_INTEGER:
        return Ok(0)
    step_q = _fraction_of(spec.step)
    if step_q is None:
        return Ok(DEFAULT_RATIONAL_SCALE)
    places = _decimal_places(step_q)
    if places is None:
        return Ok(DEFAULT_RATIONAL_SCALE)
    return Ok(min(places, MAX_SCALE))


def _snap_to_grid(magnitude: Fraction, spec: ParameterSpec) -> Result[Fraction]:
    """Snap an exact magnitude to the declared step grid, clamped to bounds."""
    bounds = spec.bounds
    if bounds is None or len(bounds) != 2:
        return invalid(
            "bounds",
            "a numeric sampled parameter carries min/max bounds to snap against",
            parameter=spec.name,
        )
    low = _fraction_of(bounds[0])
    high = _fraction_of(bounds[1])
    step_q = _fraction_of(spec.step)
    if low is None or high is None or step_q is None or step_q <= 0:
        return invalid(
            "step",
            "a numeric sampled parameter carries an exact positive step to snap against",
            parameter=spec.name,
        )
    index = round((magnitude - low) / step_q)
    index_max = floor((high - low) / step_q)
    index = max(0, min(index, index_max))
    return Ok(low + index * step_q)


# --- prior trials (the ledger view) ------------------------------------------


@dataclass(frozen=True, slots=True)
class PriorTrial:
    """One prior trial result read from the ledger view (AC1).

    ``parameters`` is the trial's exact parameter assignment (name -> exact value);
    ``objective`` is the exact objective magnitude the training run computed.
    ``generation_index`` and ``ask_index`` place the trial in its generation so the
    pure port can order the history canonically — the model it builds is then
    independent of completion order (AR-50).
    """

    generation_index: int
    ask_index: int
    parameters: Mapping[str, object]
    objective: Fraction

    @property
    def sort_key(self) -> tuple[int, int]:
        """The canonical (generation, ask) order the sampler conditions on."""
        return (self.generation_index, self.ask_index)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. The exact objective rides as num/den."""
        return {
            "ask_index": self.ask_index,
            "class": PRIOR_TRIAL_CLASS,
            "generation_index": self.generation_index,
            "objective_den": self.objective.denominator,
            "objective_num": self.objective.numerator,
            "parameters": {
                name: _value_identity(value) for name, value in sorted(self.parameters.items())
            },
        }

    @classmethod
    def try_create(
        cls,
        generation_index: object,
        ask_index: object,
        parameters: object,
        objective: object,
    ) -> Result[PriorTrial]:
        """Validate one prior trial result, value-or-refusal."""
        generation = _non_negative_int(generation_index, "generation_index")
        if is_refusal(generation):
            return generation
        ask = _non_negative_int(ask_index, "ask_index")
        if is_refusal(ask):
            return ask
        if not isinstance(parameters, Mapping):
            return invalid(
                "parameters",
                "a prior trial's parameters are a name -> exact-value mapping",
                given=repr(type(parameters).__name__),
            )
        assignment = _clean_assignment(cast("Mapping[object, object]", parameters))
        if is_refusal(assignment):
            return assignment
        magnitude = _coerce_objective(objective)
        if is_refusal(magnitude):
            return magnitude
        return Ok(
            cls(
                generation_index=generation.value,
                ask_index=ask.value,
                parameters=assignment.value,
                objective=magnitude.value,
            )
        )


def coerce_prior_trials(value: object) -> Result[tuple[PriorTrial, ...]]:
    """Admit a ledger-view read of prior trial results (AC1).

    ``value`` is a sequence of :class:`PriorTrial` or ``{generation_index,
    ask_index, parameters, objective}`` mappings. The order given is irrelevant —
    the pure port sorts canonically — but ``(generation_index, ask_index)`` pairs
    must be unique so no two prior trials collide.
    """
    if value is None:
        return Ok(())
    if isinstance(value, PriorTrial):
        return Ok((value,))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "prior_trials",
            "prior trial results are a sequence read from the ledger view",
            given=repr(type(value).__name__),
        )
    out: list[PriorTrial] = []
    seen: set[tuple[int, int]] = set()
    for index, item in enumerate(cast("Sequence[object]", value)):
        parsed = _as_prior_trial(item, index)
        if is_refusal(parsed):
            return parsed
        key = parsed.value.sort_key
        if key in seen:
            return invalid(
                "prior_trials",
                "two prior trials share one (generation_index, ask_index); each trial "
                "is placed once (AR-50)",
                generation_index=key[0],
                ask_index=key[1],
            )
        seen.add(key)
        out.append(parsed.value)
    return Ok(tuple(out))


def _as_prior_trial(item: object, index: int) -> Result[PriorTrial]:
    if isinstance(item, PriorTrial):
        return Ok(item)
    if isinstance(item, Mapping):
        body = cast("Mapping[str, object]", item)
        return PriorTrial.try_create(
            body.get("generation_index"),
            body.get("ask_index"),
            body.get("parameters"),
            body.get("objective"),
        )
    return invalid(
        "prior_trials",
        "each prior trial is a PriorTrial or a {generation_index, ask_index, "
        "parameters, objective} mapping",
        index=index,
        given=repr(type(item).__name__),
    )


# --- the proposed batch ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProposedTrial:
    """One proposed trial: an ask index and its converted parameter assignment (AC1)."""

    ask_index: int
    parameters: tuple[ConvertedValue, ...]

    @property
    def assignment(self) -> dict[str, object]:
        """The name -> converted-value assignment this trial runs (identity values)."""
        return {item.name: item.value for item in self.parameters}

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Only converted values appear."""
        return {
            "ask_index": self.ask_index,
            "class": PROPOSED_TRIAL_CLASS,
            "parameters": [item.fp1_identity() for item in self.parameters],
        }


@dataclass(frozen=True, slots=True)
class ParameterBatch:
    """One generation's proposed batch — a pure function of the port's inputs (AC1, AC2).

    ``generation_index``, ``seed``, and ``direction`` plus the sorted prior trials
    fully determine ``proposals``; two runs of the same seeded Study produce a
    byte-identical batch, which :meth:`fingerprint` witnesses regardless of the
    order trials completed in (AR-50, NFR-03).
    """

    generation_index: int
    seed: int
    direction: str
    proposals: tuple[ProposedTrial, ...]

    @property
    def size(self) -> int:
        """The number of trials proposed in this generation."""
        return len(self.proposals)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical, fp1-clean identity content. No binary float enters here."""
        return {
            "class": PARAMETER_BATCH_CLASS,
            "direction": self.direction,
            "format_version": PARAMETER_BATCH_FORMAT_VERSION,
            "generation_index": self.generation_index,
            "proposals": [item.fp1_identity() for item in self.proposals],
            "seed": self.seed,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """Content fingerprint. Same seeded Study reproduces it (NFR-03, AR-50)."""
        return fingerprint(self.fp1_identity())


def propose_generation(
    space: object,
    seed: object,
    prior_trials: object,
    generation_index: object,
    *,
    direction: object,
    batch_size: object,
    rounding: object = DEFAULT_ROUNDING,
) -> Result[ParameterBatch]:
    """The pure sampler port: propose one generation's batch (AC1, AC2, AR-50).

    A deterministic function of exactly ``(space, seed, prior_trials,
    generation_index)`` plus the Study's ``direction`` and generation ``batch_size``.
    A fresh in-memory optuna study is seeded from ``fp1(seed, generation_index)``,
    the prior trials are replayed in canonical ``(generation, ask)`` order, and the
    batch is asked and its floats converted through the named AD-7/AD-22 boundary.
    No optuna store, daemon, or study persisted across calls is consulted — history
    is the passed-in ledger view (AR-50, DEC-0169).
    """
    parsed_space = coerce_study_space(space)
    if is_refusal(parsed_space):
        return parsed_space
    parsed_seed = _non_negative_int(seed, "seed")
    if is_refusal(parsed_seed):
        return parsed_seed
    parsed_generation = _non_negative_int(generation_index, "generation_index")
    if is_refusal(parsed_generation):
        return parsed_generation
    parsed_direction = _coerce_direction(direction)
    if is_refusal(parsed_direction):
        return parsed_direction
    parsed_batch = _positive_int(batch_size, "batch_size")
    if is_refusal(parsed_batch):
        return parsed_batch
    parsed_priors = coerce_prior_trials(prior_trials)
    if is_refusal(parsed_priors):
        return parsed_priors
    mode = _coerce_rounding(rounding)
    if is_refusal(mode):
        return mode
    gen_seed = _generation_seed(parsed_seed.value, parsed_generation.value)
    if is_refusal(gen_seed):
        return gen_seed
    sampled = _run_optuna(
        parsed_space.value,
        gen_seed.value,
        parsed_priors.value,
        parsed_direction.value,
        parsed_batch.value,
    )
    if is_refusal(sampled):
        return sampled
    proposals: list[ProposedTrial] = []
    for ask_index, raw in enumerate(sampled.value):
        built = _build_proposal(parsed_space.value, raw, ask_index, mode.value)
        if is_refusal(built):
            return built
        proposals.append(built.value)
    return Ok(
        ParameterBatch(
            generation_index=parsed_generation.value,
            seed=parsed_seed.value,
            direction=parsed_direction.value,
            proposals=tuple(proposals),
        )
    )


def _build_proposal(
    space: StudyParameterSpace,
    raw: Mapping[str, object],
    ask_index: int,
    rounding: RoundingMode,
) -> Result[ProposedTrial]:
    converted: list[ConvertedValue] = []
    for spec in space.parameters:
        if spec.name not in raw:
            return invalid(
                "proposal",
                "the sampler proposed no value for a declared parameter",
                parameter=spec.name,
            )
        result = convert_sampled_value(spec, raw[spec.name], rounding=rounding)
        if is_refusal(result):
            return result
        converted.append(result.value)
    return Ok(ProposedTrial(ask_index=ask_index, parameters=tuple(converted)))


# --- the optuna adapter (n_jobs=1, transient, seeded) ------------------------


def _run_optuna(
    space: StudyParameterSpace,
    gen_seed: int,
    priors: tuple[PriorTrial, ...],
    direction: str,
    batch_size: int,
) -> Result[tuple[Mapping[str, object], ...]]:
    """Build one transient seeded study, replay the ledger view, ask the batch.

    The study is in-memory and discarded on return; optuna's own store is never
    consulted for history — the replayed trials ARE the history (AR-50).
    """
    distributions = _optuna_distributions(space)
    if is_refusal(distributions):
        return distributions
    optuna_direction = "maximize" if direction == DIRECTION_MAX else "minimize"
    try:
        study = optuna.create_study(sampler=TPESampler(seed=gen_seed), direction=optuna_direction)
        for prior in sorted(priors, key=lambda item: item.sort_key):
            params = _optuna_params(space, prior)
            if is_refusal(params):
                return params
            study.add_trial(
                create_trial(
                    params=params.value,
                    distributions=distributions.value,
                    value=float(prior.objective),
                )
            )
        batch: list[Mapping[str, object]] = []
        for _ in range(batch_size):
            trial = study.ask(distributions.value)
            batch.append(dict(trial.params))
    except (ValueError, RuntimeError, TypeError) as error:
        return invalid(
            "sampler",
            "the TPE-class adapter could not condition on the prior trials",
            detail=str(error),
        )
    return Ok(tuple(batch))


def _optuna_distributions(space: StudyParameterSpace) -> Result[dict[str, BaseDistribution]]:
    out: dict[str, BaseDistribution] = {}
    for spec in space.parameters:
        if spec.type is ParameterType.EXACT_INTEGER:
            built = _int_distribution(spec)
            if is_refusal(built):
                return built
            out[spec.name] = built.value
        elif spec.type is ParameterType.EXACT_RATIONAL:
            built_float = _float_distribution(spec)
            if is_refusal(built_float):
                return built_float
            out[spec.name] = built_float.value
        elif spec.type is ParameterType.CATEGORICAL:
            options = [str(item) for item in (spec.bounds or ())]
            if not options:
                return invalid(
                    "space", "a categorical parameter declares options", parameter=spec.name
                )
            out[spec.name] = CategoricalDistribution(choices=options)
        else:
            out[spec.name] = CategoricalDistribution(choices=[False, True])
    return Ok(out)


def _int_distribution(spec: ParameterSpec) -> Result[BaseDistribution]:
    bounds = spec.bounds
    if bounds is None or len(bounds) != 2:
        return invalid("space", "an exact-integer parameter carries bounds", parameter=spec.name)
    low = _plain_int(bounds[0])
    high = _plain_int(bounds[1])
    step = _plain_int(spec.step)
    if low is None or high is None or step is None or step < 1:
        return invalid(
            "space",
            "an exact-integer parameter carries integer bounds and a positive step",
            parameter=spec.name,
        )
    return Ok(IntDistribution(low=low, high=high, step=step))


def _float_distribution(spec: ParameterSpec) -> Result[BaseDistribution]:
    bounds = spec.bounds
    if bounds is None or len(bounds) != 2:
        return invalid("space", "an exact-rational parameter carries bounds", parameter=spec.name)
    low = _fraction_of(bounds[0])
    high = _fraction_of(bounds[1])
    if low is None or high is None:
        return invalid(
            "space", "an exact-rational parameter carries exact bounds", parameter=spec.name
        )
    return Ok(FloatDistribution(low=float(low), high=float(high)))


def _optuna_params(space: StudyParameterSpace, prior: PriorTrial) -> Result[dict[str, object]]:
    out: dict[str, object] = {}
    for spec in space.parameters:
        if spec.name not in prior.parameters:
            return invalid(
                "prior_trials",
                "a prior trial is missing a declared parameter",
                parameter=spec.name,
            )
        value = prior.parameters[spec.name]
        native = _optuna_native(spec, value)
        if is_refusal(native):
            return native
        out[spec.name] = native.value
    return Ok(out)


def _optuna_native(spec: ParameterSpec, value: object) -> Result[object]:
    if spec.type is ParameterType.EXACT_INTEGER:
        parsed = _plain_int(value)
        if parsed is None:
            return invalid(
                "prior_trials", "an exact-integer prior value is an int", parameter=spec.name
            )
        return Ok(parsed)
    if spec.type is ParameterType.EXACT_RATIONAL:
        frac = _fraction_of(value)
        if frac is None:
            return invalid(
                "prior_trials",
                "an exact-rational prior value is an ExactRational or Fraction",
                parameter=spec.name,
            )
        return Ok(float(frac))
    if spec.type is ParameterType.CATEGORICAL:
        token = clean_token(value)
        if token is None:
            return invalid(
                "prior_trials", "a categorical prior value is an option token", parameter=spec.name
            )
        return Ok(token)
    if not isinstance(value, bool):
        return invalid("prior_trials", "a boolean prior value is a bool", parameter=spec.name)
    return Ok(value)


def _generation_seed(seed: int, generation_index: int) -> Result[int]:
    """Derive the per-generation optuna seed deterministically through the fp1 seam.

    A stable function of ``(seed, generation_index)`` computed only by the qmf-core
    fingerprint seam — never Python's hash, whose per-process randomization would
    break reproducibility (AR-50).
    """
    stamped = fingerprint(
        {
            "class": GENERATION_SEED_CLASS,
            "generation_index": generation_index,
            "seed": seed,
        }
    )
    if is_refusal(stamped):
        return stamped
    digest = stamped.value.value.rsplit(":", 1)[-1]
    return Ok(int(digest[:8], 16))


# --- the generation stepper (AC2, AC3) ---------------------------------------


@dataclass(frozen=True, slots=True)
class StudyStepper:
    """The propose -> barrier -> condition state machine for one Study (AC2, AC3).

    Immutable: :meth:`ask` returns a new stepper carrying the outstanding batch,
    and :meth:`tell` returns a new stepper with the completed generation folded
    into ``completed`` and the generation index advanced. A second :meth:`ask`
    while a generation is outstanding is refused ``unsupported capability`` — the
    TPE-class adapter steps in deterministic generations only (FM-5). Because a
    generation is proposed as a pure function of ``completed`` (canonically
    ordered), two runs that complete trials in different orders still propose
    identical trials (AR-50).
    """

    space: StudyParameterSpace
    seed: int
    direction: str
    study_fp: Fingerprint
    batch_size: int
    rounding: RoundingMode = DEFAULT_ROUNDING
    completed: tuple[PriorTrial, ...] = ()
    generation_index: int = 0
    outstanding: ParameterBatch | None = None

    @property
    def has_outstanding_generation(self) -> bool:
        """Whether a proposed generation is still awaiting its tell (barrier open)."""
        return self.outstanding is not None

    def ask(self) -> Result[tuple[StudyStepper, ParameterBatch]]:
        """Propose the next generation, refusing a second ask before the tell (AC3)."""
        if self.outstanding is not None:
            return refuse_parallel_ask(self.generation_index)
        batch = propose_generation(
            self.space,
            self.seed,
            self.completed,
            self.generation_index,
            direction=self.direction,
            batch_size=self.batch_size,
            rounding=self.rounding,
        )
        if is_refusal(batch):
            return batch
        return Ok((replace(self, outstanding=batch.value), batch.value))

    def tell(self, results: object) -> Result[StudyStepper]:
        """Barrier the whole generation, condition on it, advance (AC2).

        ``results`` are the outstanding generation's completed trials (each with its
        objective). The tell refuses unless every ask in the generation reported —
        the barrier is the whole generation, never a partial condition.
        """
        if self.outstanding is None:
            return invalid(
                "tell",
                "no generation is outstanding to condition on; ask a generation first",
            )
        told = _barrier_results(results, self.outstanding, self.generation_index)
        if is_refusal(told):
            return told
        return Ok(
            replace(
                self,
                completed=(*self.completed, *told.value),
                generation_index=self.generation_index + 1,
                outstanding=None,
            )
        )

    def trial_labels(self) -> Result[tuple[dict[str, object], ...]]:
        """The ledger labels for the outstanding generation's trials (AC6)."""
        if self.outstanding is None:
            return invalid("trial_labels", "no generation is outstanding to label")
        labels: list[dict[str, object]] = []
        for proposal in self.outstanding.proposals:
            built = trial_label(
                self.study_fp,
                self.seed,
                self.generation_index,
                proposal,
            )
            if is_refusal(built):
                return built
            labels.append(built.value)
        return Ok(tuple(labels))


def refuse_parallel_ask(
    generation_index: object = None,
) -> Result[tuple[StudyStepper, ParameterBatch]]:
    """A second ask before the outstanding generation's tell is unsupported (AC3, FM-5).

    The TPE-class adapter has no parallel-ask capability: adaptive search steps in
    deterministic propose -> barrier -> condition generations. A grid/Sobol adapter
    could ask a declared batch, but the default sampler is genuinely adaptive
    (DEC-0169).
    """
    context: dict[str, object] = {}
    parsed = _non_negative_int(generation_index, "generation_index")
    if not is_refusal(parsed):
        context["generation_index"] = parsed.value
    return unsupported(
        "ask",
        "a TPE-class sampler refuses a second ask before the outstanding generation's "
        "tell; adaptive search steps in deterministic propose/barrier/condition "
        "generations only (FM-5, DEC-0169)",
        family=SAMPLER_FAMILY,
        parallel_ask=SAMPLER_PARALLEL_ASK,
        **context,
    )


def _barrier_results(
    results: object,
    outstanding: ParameterBatch,
    generation_index: int,
) -> Result[tuple[PriorTrial, ...]]:
    parsed = coerce_prior_trials(results)
    if is_refusal(parsed):
        return parsed
    told = parsed.value
    expected = {proposal.ask_index for proposal in outstanding.proposals}
    got = {trial.ask_index for trial in told}
    for trial in told:
        if trial.generation_index != generation_index:
            return invalid(
                "tell",
                "a told trial belongs to a different generation than the outstanding one",
                expected_generation=generation_index,
                given_generation=trial.generation_index,
            )
    if got != expected:
        return invalid(
            "tell",
            "the tell barriers the WHOLE generation; every proposed ask must report "
            "before the sampler conditions (AC2)",
            expected=sorted(expected),
            given=sorted(got),
        )
    return Ok(told)


# --- the trial label (AC6) ---------------------------------------------------


def trial_label(
    study_fp: object,
    seed: object,
    generation_index: object,
    proposal: object,
) -> Result[dict[str, object]]:
    """The role=trial ledger label: sampler identity, seed, provenance, study_fp (AC6).

    Every trial ledgers as ``role = trial`` carrying enough identity to reproduce
    it: the sampler identity, the Study seed, the generator provenance (with the
    runtime optuna version), and ``study_fp`` — the study artifact before this ask.
    Re-running the trial under its resolved config reproduces its CT-32 fingerprint
    or refuses; a future optuna major bump changes the provenance stamp, making the
    bump a contract-versioning event (AR-29).
    """
    parsed_study_fp = _coerce_fingerprint(study_fp, "study_fp")
    if is_refusal(parsed_study_fp):
        return parsed_study_fp
    parsed_seed = _non_negative_int(seed, "seed")
    if is_refusal(parsed_seed):
        return parsed_seed
    parsed_generation = _non_negative_int(generation_index, "generation_index")
    if is_refusal(parsed_generation):
        return parsed_generation
    if not isinstance(proposal, ProposedTrial):
        return invalid(
            "proposal",
            "a trial label is stamped over a ProposedTrial",
            given=repr(type(proposal).__name__),
        )
    label: dict[str, object] = {
        "class": TRIAL_LABEL_CLASS,
        "format_version": TRIAL_LABEL_FORMAT_VERSION,
        "generation_index": parsed_generation.value,
        "generator_provenance": generator_provenance(),
        "parameters": [item.fp1_identity() for item in proposal.parameters],
        "role": SAMPLER_TRIAL_ROLE,
        "sampler_identity": sampler_identity(),
        "seed": parsed_seed.value,
        "study_fp": parsed_study_fp.value.value,
    }
    return Ok(label)


def refuse_sampler_contract_bump(recorded_provenance: object) -> Result[None]:
    """A future optuna major bump is a contract-versioning event, never transparent (AC6).

    ``recorded_provenance`` is a trial's stored :func:`generator_provenance`. If the
    installed optuna major version differs from the one recorded on the trial, the
    trial cannot be transparently re-sampled under the new generator — that is a
    contract-versioning event, refused ``unsupported capability`` (AR-29, DEC-0168).
    """
    if not isinstance(recorded_provenance, Mapping):
        return invalid(
            "recorded_provenance",
            "the recorded generator provenance is a mapping from the trial label",
            given=repr(type(recorded_provenance).__name__),
        )
    body = cast("Mapping[str, object]", recorded_provenance)
    recorded_major = body.get("major_version")
    _, current_major = _optuna_runtime_version()
    if not isinstance(recorded_major, int) or isinstance(recorded_major, bool):
        return invalid(
            "recorded_provenance",
            "the recorded provenance carries an integer optuna major_version",
            given=repr(recorded_major),
        )
    if recorded_major != current_major:
        return unsupported(
            "sampler",
            "a future optuna major bump is a contract-versioning event, never a "
            "transparent update; re-sampling this trial under a different major is "
            "refused (AR-29, DEC-0168)",
            recorded_major=recorded_major,
            current_major=current_major,
            pin_key=SAMPLER_PIN_KEY,
        )
    return Ok(None)


# --- Study admission: one frozen registry as-of (AC5) ------------------------


@dataclass(frozen=True, slots=True)
class StudyArtifact:
    """The frozen Study declaration, fingerprinted to study_fp (AC5, AC6).

    Carries the search-space fingerprint, seed, direction, the frozen registry
    as-of, and the resolved bot/Book/BMS context fingerprints, plus the optional
    criteria/splits fingerprints. Its fingerprint is ``study_fp`` — the study
    artifact before any ask — stamped into every trial label (AC6).
    """

    space_fp1: Fingerprint
    seed: int
    direction: str
    registry_as_of: Mapping[str, object]
    bot_fp1: Fingerprint
    book_fp1: Fingerprint | None = None
    bms_fp1: Fingerprint | None = None
    criteria_fp1: Fingerprint | None = None
    splits_fp1: Fingerprint | None = None

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. The sampler identity rides; SemVer is omitted."""
        content: dict[str, object] = {
            "bot_fp1": self.bot_fp1.value,
            "class": STUDY_ARTIFACT_CLASS,
            "direction": self.direction,
            "format_version": STUDY_ARTIFACT_FORMAT_VERSION,
            "registry_as_of": dict(self.registry_as_of),
            "sampler_identity": sampler_identity(),
            "seed": self.seed,
            "space_fp1": self.space_fp1.value,
        }
        if self.book_fp1 is not None:
            content["book_fp1"] = self.book_fp1.value
        if self.bms_fp1 is not None:
            content["bms_fp1"] = self.bms_fp1.value
        if self.criteria_fp1 is not None:
            content["criteria_fp1"] = self.criteria_fp1.value
        if self.splits_fp1 is not None:
            content["splits_fp1"] = self.splits_fp1.value
        return content

    def fingerprint(self) -> Result[Fingerprint]:
        """``study_fp`` — the study artifact before this ask (AC6)."""
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class StudyLabel:
    """The one label a Study stamps: study_fp plus the frozen registry as-of (AC5)."""

    study_fp: Fingerprint
    registry_as_of: Instant
    set_fingerprint: Fingerprint
    seed: int
    bot_fp1: Fingerprint
    book_fp1: Fingerprint | None = None
    bms_fp1: Fingerprint | None = None

    def registry_as_of_stamp(self) -> dict[str, object]:
        """The frozen as-of stamp (instant nanoseconds + set fingerprint)."""
        return {"fingerprint": self.set_fingerprint.value, "value_ns": self.registry_as_of.value_ns}

    def fp1_identity(self) -> dict[str, object]:
        """Canonical Study-label identity. Package SemVer is omitted."""
        content: dict[str, object] = {
            "bot_fp1": self.bot_fp1.value,
            "class": STUDY_LABEL_CLASS,
            "registry_as_of": self.registry_as_of.fp1_identity(),
            "sampler_identity": sampler_identity(),
            "seed": self.seed,
            "set_fingerprint": self.set_fingerprint.value,
            "study_fp": self.study_fp.value,
        }
        if self.book_fp1 is not None:
            content["book_fp1"] = self.book_fp1.value
        if self.bms_fp1 is not None:
            content["bms_fp1"] = self.bms_fp1.value
        return content


@dataclass(frozen=True, slots=True)
class AdmittedStudy:
    """A Study admitted over exactly one frozen registry as-of (AC5, B-15, SC-11).

    ``port`` is the single library-owned registry-read port, frozen at admission:
    after admission it resolves by explicit fingerprint only, and a fresher as-of
    set arriving on the hub never reaches a trial. ``artifact`` fingerprints to
    ``study_fp`` and ``label`` stamps the frozen as-of. A :class:`StudyStepper` is
    seeded from the admitted Study by :meth:`stepper`.
    """

    port: RegistryReadPort
    space: StudyParameterSpace
    artifact: StudyArtifact
    label: StudyLabel

    @property
    def study_fp(self) -> Fingerprint:
        """``study_fp`` — the study artifact before any ask (AC6)."""
        return self.label.study_fp

    @property
    def registry_as_of(self) -> Instant:
        """The one frozen as-of instant every trial shares."""
        return self.label.registry_as_of

    @property
    def set_fingerprint(self) -> Fingerprint:
        """The one frozen as-of set fingerprint every trial shares."""
        return self.label.set_fingerprint

    def registry_as_of_stamp(self) -> dict[str, object]:
        """The frozen as-of stamp every trial's label carries."""
        return self.label.registry_as_of_stamp()

    def stepper(
        self, *, batch_size: object, rounding: object = DEFAULT_ROUNDING
    ) -> Result[StudyStepper]:
        """Seed a generation stepper from this admitted Study (AC2)."""
        size = _positive_int(batch_size, "batch_size")
        if is_refusal(size):
            return size
        mode = _coerce_rounding(rounding)
        if is_refusal(mode):
            return mode
        return Ok(
            StudyStepper(
                space=self.space,
                seed=self.artifact.seed,
                direction=self.artifact.direction,
                study_fp=self.study_fp,
                batch_size=size.value,
                rounding=mode.value,
            )
        )


def admit_study(
    space: object,
    seed: object,
    port: object,
    *,
    bot: object,
    direction: object = DIRECTION_MAX,
    book: object = None,
    bms: object = None,
    criteria: object = None,
    splits: object = None,
) -> Result[AdmittedStudy]:
    """Admit a Study over exactly one frozen registry as-of (AC5, B-15, SC-11).

    Admission resolves the bot (and optional Book/BMS) context ONCE through the
    single library-owned registry-read port — detecting a superseded reference as
    an AD-11 stale-evidence refusal on the LIVE port — then freezes the port's
    as-of for every trial and stamps that one as-of, plus ``study_fp``, into the
    Study label. After admission the port resolves by explicit fingerprint only,
    never ``name@latest`` (B-15). Pass the live (unfrozen) port so admission can
    detect stale evidence before it freezes.
    """
    parsed_space = coerce_study_space(space)
    if is_refusal(parsed_space):
        return parsed_space
    parsed_seed = _non_negative_int(seed, "seed")
    if is_refusal(parsed_seed):
        return parsed_seed
    parsed_direction = _coerce_direction(direction)
    if is_refusal(parsed_direction):
        return parsed_direction
    if not isinstance(port, RegistryReadPort):
        return invalid(
            "port",
            "a Study admits its batch through the one library-owned registry-read port",
            given=repr(type(port).__name__),
        )
    space_fp = parsed_space.value.fingerprint()
    if is_refusal(space_fp):
        return space_fp
    bot_ref = port.resolve(bot)
    if is_refusal(bot_ref):
        return bot_ref
    book_fp = _optional_ref(port, book)
    if is_refusal(book_fp):
        return book_fp
    bms_fp = _optional_ref(port, bms)
    if is_refusal(bms_fp):
        return bms_fp
    criteria_fp = _optional_fingerprint(criteria, "criteria")
    if is_refusal(criteria_fp):
        return criteria_fp
    splits_fp = _optional_fingerprint(splits, "splits")
    if is_refusal(splits_fp):
        return splits_fp
    frozen = port.admit_batch()
    as_of = frozen.bound.registry_as_of
    set_fp = frozen.bound.fingerprint
    artifact = StudyArtifact(
        space_fp1=space_fp.value,
        seed=parsed_seed.value,
        direction=parsed_direction.value,
        registry_as_of={"fingerprint": set_fp.value, "value_ns": as_of.value_ns},
        bot_fp1=bot_ref.value.fingerprint,
        book_fp1=book_fp.value,
        bms_fp1=bms_fp.value,
        criteria_fp1=criteria_fp.value,
        splits_fp1=splits_fp.value,
    )
    study_fp = artifact.fingerprint()
    if is_refusal(study_fp):
        return study_fp
    label = StudyLabel(
        study_fp=study_fp.value,
        registry_as_of=as_of,
        set_fingerprint=set_fp,
        seed=parsed_seed.value,
        bot_fp1=bot_ref.value.fingerprint,
        book_fp1=book_fp.value,
        bms_fp1=bms_fp.value,
    )
    return Ok(AdmittedStudy(port=frozen, space=parsed_space.value, artifact=artifact, label=label))


def _optional_ref(port: RegistryReadPort, ref: object) -> Result[Fingerprint | None]:
    if ref is None:
        return Ok(None)
    resolved = port.resolve(ref)
    if is_refusal(resolved):
        return resolved
    result: Fingerprint | None = resolved.value.fingerprint
    return Ok(result)


def _optional_fingerprint(value: object, field: str) -> Result[Fingerprint | None]:
    if value is None:
        return Ok(None)
    derived = _content_fingerprint(value)
    if is_refusal(derived):
        return invalid(
            field,
            "a Study's criteria/splits are named by fingerprint or fp1-canonical content",
            given=repr(type(value).__name__),
        )
    result: Fingerprint | None = derived.value
    return Ok(result)


# --- coercion helpers --------------------------------------------------------


def _value_identity(value: object) -> object:
    if isinstance(value, ExactRational):
        return value.fp1_identity()
    return value


def _fraction_of(value: object) -> Fraction | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, ExactRational):
        return value.as_fraction()
    if isinstance(value, Fraction):
        return value
    return None


def _plain_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _decimal_places(frac: Fraction) -> int | None:
    den = frac.denominator
    twos = 0
    fives = 0
    while den % 2 == 0:
        den //= 2
        twos += 1
    while den % 5 == 0:
        den //= 5
        fives += 1
    if den != 1:
        return None
    return max(twos, fives)


def _coerce_rounding(value: object) -> Result[RoundingMode]:
    if isinstance(value, RoundingMode):
        return Ok(value)
    token = clean_token(value)
    if token is not None:
        try:
            return Ok(RoundingMode(token))
        except ValueError:
            pass
    return invalid(
        "rounding",
        "the named conversion boundary declares an explicit rounding mode",
        given=repr(value),
        allowed=[member.value for member in RoundingMode],
    )


def _coerce_direction(value: object) -> Result[str]:
    token = clean_token(value)
    if token is None or token not in OBJECTIVE_DIRECTIONS:
        return invalid(
            "direction",
            "the Study direction is min or max",
            given=repr(value),
            allowed=list(OBJECTIVE_DIRECTIONS),
        )
    return Ok(token)


def _coerce_objective(value: object) -> Result[Fraction]:
    if isinstance(value, bool):
        return invalid("objective", "a prior objective is an exact number, never a boolean")
    if isinstance(value, float):
        return invalid(
            "objective",
            "a prior objective magnitude is exact; a binary float is refused (AD-10)",
            given=repr(value),
        )
    if isinstance(value, int):
        return Ok(Fraction(value))
    if isinstance(value, Fraction):
        return Ok(value)
    if isinstance(value, ExactRational):
        return Ok(value.as_fraction())
    identity = getattr(value, "fp1_identity", None)
    if callable(identity):
        body = identity()
        if isinstance(body, Mapping):
            return _objective_from_mapping(cast("Mapping[str, object]", body))
    if isinstance(value, Mapping):
        return _objective_from_mapping(cast("Mapping[str, object]", value))
    return invalid(
        "objective",
        "a prior objective is an int, Fraction, ExactRational, or its fp1-canonical mapping",
        given=repr(type(value).__name__),
    )


def _objective_from_mapping(body: Mapping[str, object]) -> Result[Fraction]:
    num = body.get("num")
    den = body.get("den")
    if isinstance(num, bool) or not isinstance(num, int):
        return invalid("objective", "an exact objective carries an integer numerator")
    if isinstance(den, bool) or not isinstance(den, int) or den == 0:
        return invalid("objective", "an exact objective carries a non-zero integer denominator")
    return Ok(Fraction(num, den))


def _clean_assignment(mapping: Mapping[object, object]) -> Result[dict[str, object]]:
    out: dict[str, object] = {}
    for key, value in mapping.items():
        if not isinstance(key, str) or key.strip() == "":
            return invalid("parameters", "a parameter assignment is keyed by non-empty names")
        if isinstance(value, float):
            return invalid(
                "parameters",
                "an exact parameter value is never a binary float (AD-10)",
                parameter=key,
            )
        out[key] = value
    return Ok(out)


def _coerce_float(value: object, parameter: str) -> Result[float]:
    if isinstance(value, bool):
        return invalid("value", "a numeric sample is not a boolean", parameter=parameter)
    if isinstance(value, float):
        return Ok(value)
    if isinstance(value, int):
        return Ok(float(value))
    frac = _fraction_of(value)
    if frac is not None:
        return Ok(float(frac))
    return invalid(
        "value",
        "a numeric sample is a float, int, or exact value the conversion boundary accepts",
        parameter=parameter,
        given=repr(type(value).__name__),
    )


def _content_fingerprint(value: object) -> Result[Fingerprint]:
    """Fingerprint a criteria/splits reference from its fp1-canonical content.

    A StudyCriteria or StudySplits fingerprints through its ``fp1_identity`` — the
    same content its own ``fingerprint()`` folds — so a Fingerprint, an fp1 token,
    an fp1-identity-bearing object, or a raw mapping all reduce to one Fingerprint.
    """
    if isinstance(value, Fingerprint):
        return Ok(value)
    identity = getattr(value, "fp1_identity", None)
    if callable(identity):
        body = identity()
        if isinstance(body, Mapping):
            return fingerprint(cast("Mapping[str, object]", body))
    token = clean_token(value)
    if token is not None:
        return Fingerprint.try_create(token)
    if isinstance(value, Mapping):
        return fingerprint(cast("Mapping[str, object]", value))
    return invalid("value", "not fingerprintable content", given=repr(type(value).__name__))


def _coerce_fingerprint(value: object, field: str) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    token = clean_token(value)
    if token is not None:
        return Fingerprint.try_create(token)
    return invalid(field, "a fingerprint is the string fp1:sha256:<hex>", given=repr(value))


def _non_negative_int(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return invalid(field, "a non-negative exact integer is required", given=repr(value))
    return Ok(value)


def _positive_int(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return invalid(field, "a positive exact integer is required", given=repr(value))
    return Ok(value)
