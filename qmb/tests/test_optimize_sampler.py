"""Story 21.4 — the pure, generation-stepped TPE-class Optuna sampler (B-8, AR-50)."""

from __future__ import annotations

from fractions import Fraction
from typing import TypeVar, cast

from qmb.optimize import (
    DEFAULT_ROUNDING,
    SAMPLER_CONSULTS_OPTUNA_STORE,
    SAMPLER_FAMILY,
    SAMPLER_JOBS,
    SAMPLER_PARALLEL_ASK,
    SAMPLER_PIN_KEY,
    AdmittedStudy,
    ConvertedValue,
    ParameterBatch,
    PriorTrial,
    StudyParameterSpace,
    StudyStepper,
    admit_study,
    coerce_prior_trials,
    coerce_study_space,
    convert_sampled_value,
    generator_provenance,
    propose_generation,
    refuse_parallel_ask,
    refuse_sampler_contract_bump,
    sampler_identity,
    trial_label,
)
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort, SupersedesRef
from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import ExactRational, RoundingMode, UnitKind
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import RegistrationRecord

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_SEVERITY = "workspace-declared"
_R = UnitKind.DIMENSIONLESS_RATIO


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _writer() -> WriterId:
    return _ok(WriterId.try_create("node-a", "authoring", "study", "boot-1"))


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
                {
                    "name": "mode",
                    "type": "categorical",
                    "unit_kind": UnitKind.COUNT,
                    "options": ["trend", "range", "breakout"],
                    "default": "trend",
                    "ui": "ui-editable",
                },
                {
                    "name": "use_filter",
                    "type": "boolean",
                    "unit_kind": UnitKind.COUNT,
                    "default": True,
                    "ui": "ui-editable",
                },
            ]
        )
    )


def _priors(batch: ParameterBatch) -> list[dict[str, object]]:
    return [
        {
            "generation_index": batch.generation_index,
            "ask_index": trial.ask_index,
            "parameters": trial.assignment,
            "objective": Fraction(trial.ask_index + 1),
        }
        for trial in batch.proposals
    ]


def _atr(space: StudyParameterSpace) -> object:
    return next(spec for spec in space.parameters if spec.name == "atr_mult")


# --- AC1: the pure sampler port ----------------------------------------------


def test_propose_generation_is_a_deterministic_function_of_its_inputs() -> None:
    space = _space()
    first = _ok(propose_generation(space, 4242, [], 0, direction="max", batch_size=5))
    again = _ok(propose_generation(space, 4242, [], 0, direction="max", batch_size=5))
    assert first.size == 5
    assert _ok(first.fingerprint()) == _ok(again.fingerprint())
    # A different seed proposes a different batch.
    other = _ok(propose_generation(space, 4243, [], 0, direction="max", batch_size=5))
    assert _ok(other.fingerprint()) != _ok(first.fingerprint())


def test_history_read_from_the_ledger_view_is_order_independent() -> None:
    space = _space()
    gen0 = _ok(propose_generation(space, 7, [], 0, direction="max", batch_size=6))
    priors = _priors(gen0)
    ordered = _ok(propose_generation(space, 7, priors, 1, direction="max", batch_size=6))
    shuffled = _ok(
        propose_generation(space, 7, list(reversed(priors)), 1, direction="max", batch_size=6)
    )
    assert _ok(ordered.fingerprint()) == _ok(shuffled.fingerprint())


def test_the_sampler_never_consults_an_optuna_store_for_history() -> None:
    assert SAMPLER_CONSULTS_OPTUNA_STORE is False
    assert sampler_identity()["consults_optuna_store"] is False
    assert sampler_identity()["jobs"] == SAMPLER_JOBS == 1
    assert sampler_identity()["pin_key"] == SAMPLER_PIN_KEY == "qmb_sampler_pin"
    assert sampler_identity()["family"] == SAMPLER_FAMILY == "tpe-class"


def test_prior_trials_reject_duplicates_and_float_objectives() -> None:
    dup = coerce_prior_trials(
        [
            {"generation_index": 0, "ask_index": 0, "parameters": {"x": 1}, "objective": 1},
            {"generation_index": 0, "ask_index": 0, "parameters": {"x": 2}, "objective": 2},
        ]
    )
    assert is_refusal(dup)
    floated = coerce_prior_trials(
        [{"generation_index": 0, "ask_index": 0, "parameters": {"x": 1}, "objective": 1.5}]
    )
    assert is_refusal(floated)


def test_propose_generation_refuses_bad_inputs() -> None:
    space = _space()
    assert is_refusal(propose_generation(space, -1, [], 0, direction="max", batch_size=3))
    assert is_refusal(propose_generation(space, 1, [], -1, direction="max", batch_size=3))
    assert is_refusal(propose_generation(space, 1, [], 0, direction="sideways", batch_size=3))
    assert is_refusal(propose_generation(space, 1, [], 0, direction="max", batch_size=0))


# --- AC2: propose -> run -> barrier -> condition -----------------------------


def test_two_seeded_steppers_propose_identically_regardless_of_completion_order() -> None:
    space = _space()
    study_fp = _ok(fingerprint({"study": "s"}))

    def run(order: str) -> tuple[Fingerprint, Fingerprint]:
        stepper = StudyStepper(
            space=space, seed=13, direction="max", study_fp=study_fp, batch_size=4
        )
        after0, gen0 = _ok(stepper.ask())
        results = _priors(gen0)
        if order == "reversed":
            results = list(reversed(results))
        after_tell = _ok(after0.tell(results))
        after1, gen1 = _ok(after_tell.ask())
        del after1
        return (_ok(gen0.fingerprint()), _ok(gen1.fingerprint()))

    forward = run("forward")
    backward = run("reversed")
    assert forward == backward


def test_tell_barriers_the_whole_generation() -> None:
    space = _space()
    study_fp = _ok(fingerprint({"study": "s"}))
    stepper = StudyStepper(space=space, seed=1, direction="min", study_fp=study_fp, batch_size=4)
    after, gen0 = _ok(stepper.ask())
    partial = after.tell(_priors(gen0)[:2])
    assert is_refusal(partial)  # a partial generation cannot condition the sampler
    full = _ok(after.tell(_priors(gen0)))
    assert full.generation_index == 1
    assert len(full.completed) == 4
    # tell before any ask is refused
    assert is_refusal(stepper.tell(_priors(gen0)))


# --- AC3: parallel ask is unsupported ----------------------------------------


def test_second_ask_before_the_tell_is_unsupported_capability() -> None:
    space = _space()
    study_fp = _ok(fingerprint({"study": "s"}))
    stepper = StudyStepper(space=space, seed=5, direction="max", study_fp=study_fp, batch_size=3)
    after, _batch = _ok(stepper.ask())
    assert after.has_outstanding_generation is True
    refused = after.ask()
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert SAMPLER_PARALLEL_ASK is False
    # the standalone helper carries the same refusal
    helper = refuse_parallel_ask(0)
    assert is_refusal(helper)
    assert helper.category is RefusalCategory.UNSUPPORTED_CAPABILITY


# --- AC4: named AD-7/AD-22 conversion; the float never enters identity -------


def test_rational_float_enters_identity_only_through_the_named_conversion() -> None:
    space = _space()
    atr = _atr(space)
    converted = _ok(convert_sampled_value(atr, 1.7361, rounding=RoundingMode.HALF_EVEN))
    assert isinstance(converted, ConvertedValue)
    assert isinstance(converted.value, ExactRational)
    identity = converted.fp1_identity()
    assert identity["value"] == converted.value.fp1_identity()
    assert identity["conversion"] == {"rounding": "half-even", "scale": 1}
    # No binary float anywhere in identity, and the snapped value is on the step grid.
    assert not any(isinstance(part, float) for part in identity.values())
    grid = converted.value.as_fraction() / Fraction(1, 2)
    assert grid.denominator == 1  # a multiple of the 0.5 step


def test_missing_rounding_mode_is_refused() -> None:
    space = _space()
    atr = _atr(space)
    assert is_refusal(convert_sampled_value(atr, 1.5, rounding="not-a-mode"))
    # the default rounding mode is available without a caller declaration
    assert is_ok(convert_sampled_value(atr, 1.5))
    assert DEFAULT_ROUNDING is RoundingMode.HALF_EVEN


def test_integer_conversion_snaps_to_the_step_grid_as_a_plain_int() -> None:
    space = _space()
    lookback = next(spec for spec in space.parameters if spec.name == "lookback")
    converted = _ok(convert_sampled_value(lookback, 30.0))
    assert converted.value == 30  # already on the {2,4,...,40} grid, a plain int
    assert isinstance(converted.value, int)
    assert converted.fp1_identity()["conversion"] == {"rounding": "half-even", "scale": 0}
    # An off-grid float lands deterministically on the grid within bounds.
    off_grid = _ok(convert_sampled_value(lookback, 23.9))
    assert off_grid.value == 24
    assert isinstance(off_grid.value, int)
    # A float beyond the upper bound clamps to the top grid point.
    high = _ok(convert_sampled_value(lookback, 99.0))
    assert high.value == 40


def test_categorical_and_boolean_never_float() -> None:
    space = _space()
    mode = next(spec for spec in space.parameters if spec.name == "mode")
    flag = next(spec for spec in space.parameters if spec.name == "use_filter")
    cat = _ok(convert_sampled_value(mode, "range"))
    assert cat.value == "range"
    assert cat.conversion is None
    assert "conversion" not in cat.fp1_identity()
    boolean = _ok(convert_sampled_value(flag, False))
    assert boolean.value is False
    assert boolean.conversion is None
    assert is_refusal(convert_sampled_value(mode, "not-an-option"))


def test_every_proposed_numeric_value_is_identity_bearing_never_a_float() -> None:
    space = _space()
    batch = _ok(propose_generation(space, 314, [], 0, direction="max", batch_size=4))
    for proposal in batch.proposals:
        identity = proposal.fp1_identity()
        assert not _has_float(identity)
        for value in proposal.parameters:
            if isinstance(value.value, ExactRational):
                assert value.conversion is not None


# --- AC5: one frozen registry as-of, stamped into the Study label ------------


def _record(kind: str, body: object) -> RegistrationRecord:
    return _ok(RegistrationRecord.try_create(kind, 1, (), body, _writer(), 0, _instant()))


def _admitted_study(seed: int = 4242) -> tuple[AdmittedStudy, AsOfSet]:
    bot = _record("bot-definition", {"class": "bot-definition", "alias": "mean-reversion"})
    pointer = _ok(DatedPointer.try_create("mean-reversion", bot.stable_id, _instant()))
    as_of = _ok(AsOfSet.try_create(_instant(), records=(bot,), pointers=(pointer,)))
    hub = _ok(PassiveHub.try_create((as_of,)))
    port = _ok(RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY))
    admitted = _ok(admit_study(_space(), seed, port, bot=bot.stable_id, direction="max"))
    return (admitted, as_of)


def test_admission_freezes_one_as_of_and_stamps_it_into_the_study_label() -> None:
    admitted, as_of = _admitted_study()
    assert admitted.port.frozen is True
    assert admitted.registry_as_of == as_of.registry_as_of
    assert admitted.set_fingerprint == as_of.fingerprint
    stamp = admitted.label.registry_as_of_stamp()
    assert stamp["fingerprint"] == as_of.fingerprint.value
    assert stamp["value_ns"] == as_of.registry_as_of.value_ns
    # study_fp is a real fingerprint, present on the label and in the artifact.
    assert isinstance(admitted.study_fp, Fingerprint)
    assert _ok(admitted.artifact.fingerprint()) == admitted.study_fp


def test_after_admission_fragments_resolve_by_fingerprint_never_name_at_latest() -> None:
    admitted, _as_of = _admitted_study()
    assert is_refusal(admitted.port.resolve("mean-reversion"))
    assert is_refusal(admitted.port.resolve("mean-reversion@latest"))


def test_a_superseded_reference_at_admission_is_stale_evidence() -> None:
    bot_v1 = _record("bot-definition", {"class": "bot-definition", "alias": "v1"})
    bot_v2 = _record("bot-definition", {"class": "bot-definition", "alias": "v2"})
    supersedes = (_ok(SupersedesRef.try_create(bot_v2.stable_id, bot_v1.stable_id)),)
    as_of = _ok(
        AsOfSet.try_create(_instant(), records=(bot_v1, bot_v2), supersedes=supersedes)
    )
    hub = _ok(PassiveHub.try_create((as_of,)))
    port = _ok(RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY))
    refused = admit_study(_space(), 1, port, bot=bot_v1.stable_id, direction="max")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STALE_EVIDENCE


def test_the_admitted_study_seeds_a_stepper() -> None:
    admitted, _as_of = _admitted_study(seed=99)
    stepper = _ok(admitted.stepper(batch_size=3))
    assert stepper.seed == 99
    assert stepper.study_fp == admitted.study_fp
    after, batch = _ok(stepper.ask())
    del after
    assert batch.size == 3


# --- AC6: trial label + contract-versioning on an optuna bump ----------------


def test_trial_label_carries_sampler_identity_seed_provenance_and_study_fp() -> None:
    admitted, _as_of = _admitted_study(seed=4242)
    stepper = _ok(admitted.stepper(batch_size=3))
    after, _batch = _ok(stepper.ask())
    labels = _ok(after.trial_labels())
    assert len(labels) == 3
    label = labels[0]
    assert label["role"] == "trial"
    assert label["sampler_identity"] == sampler_identity()
    assert label["generator_provenance"] == generator_provenance()
    assert label["seed"] == 4242
    assert label["study_fp"] == admitted.study_fp.value
    assert is_ok(fingerprint(label))


def test_trial_label_is_reproducible_and_float_free() -> None:
    space = _space()
    study_fp = _ok(fingerprint({"study": "s"}))
    batch = _ok(propose_generation(space, 8, [], 0, direction="max", batch_size=2))
    label_a = _ok(trial_label(study_fp, 8, 0, batch.proposals[0]))
    label_b = _ok(trial_label(study_fp, 8, 0, batch.proposals[0]))
    assert _ok(fingerprint(label_a)) == _ok(fingerprint(label_b))
    assert not _has_float(label_a)


def test_a_future_optuna_major_bump_is_a_contract_versioning_event() -> None:
    provenance = generator_provenance()
    assert is_ok(refuse_sampler_contract_bump(provenance))
    bumped = {**provenance, "major_version": 999}
    refused = refuse_sampler_contract_bump(bumped)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refused.context["pin_key"] == SAMPLER_PIN_KEY
    # the runtime provenance names the pinned generator, read not hard-coded
    assert provenance["library"] == "optuna"
    assert provenance["sampler"] == "TPESampler"
    assert isinstance(provenance["major_version"], int)


def test_prior_trials_condition_the_model_the_winner_shifts_toward_good_regions() -> None:
    # A one-parameter integer study: reward small lookbacks and confirm the TPE model
    # conditions on the ledger view — later generations concentrate below the midpoint.
    space = _ok(
        coerce_study_space(
            [
                {
                    "name": "lookback",
                    "type": "exact integer",
                    "unit_kind": UnitKind.COUNT,
                    "bounds": {"min": 0, "max": 100},
                    "step": 1,
                    "default": 50,
                    "ui": "ui-editable",
                }
            ]
        )
    )
    priors: list[PriorTrial] = []
    for generation in range(4):
        batch = _ok(
            propose_generation(space, 2024, priors, generation, direction="min", batch_size=8)
        )
        for trial in batch.proposals:
            value = trial.assignment["lookback"]
            assert isinstance(value, int)
            # objective = the value itself; minimizing rewards small lookbacks
            priors.append(
                _ok(
                    PriorTrial.try_create(
                        generation, trial.ask_index, trial.assignment, Fraction(value)
                    )
                )
            )
    late_values: list[int] = []
    for prior in priors:
        if prior.generation_index != 3:
            continue
        value = prior.parameters["lookback"]
        assert isinstance(value, int)
        late_values.append(value)
    mean_late = sum(late_values) / len(late_values)
    assert mean_late < 50  # the model has concentrated below the midpoint


def _has_float(value: object) -> bool:
    if isinstance(value, float):
        return True
    if isinstance(value, dict):
        return any(_has_float(item) for item in cast("dict[object, object]", value).values())
    if isinstance(value, (list, tuple)):
        return any(_has_float(item) for item in cast("tuple[object, ...]", value))
    return False
