"""Group D — Pure sampler in deterministic generations (Story 21.4) -> R18-R23.

Public surfaces driven: ``propose_generation`` (the pure port), ``StudyStepper.ask``,
``convert_sampled_value``, ``admit_study``, ``trial_label`` and
``refuse_sampler_contract_bump``. Trial history enters ONLY as the injected
``prior_trials`` argument sourced from the ledger view — the tests are blind to any
optuna internal store. CT-32 byte-reproduction machinery is Epic 14 (out of scope);
here R23 asserts label content + the reproduce-or-refuse contract.
"""

from __future__ import annotations

from conftest import (
    Fraction,
    RefusalCategory,
    UnitKind,
    assert_ct04_refusal,
    bot_universe,
    find_floats,
    int_param,
    is_ok,
    rational_param,
    unwrap,
)

from qmb.optimize.sampler import (
    StudyStepper,
    admit_study,
    convert_sampled_value,
    generator_provenance,
    propose_generation,
    refuse_sampler_contract_bump,
    trial_label,
)
from qmb.optimize.space import coerce_study_space
from qmf.core.exact import ExactRational
from qmf.core.fingerprint import fingerprint
from qml.declaration.parameters import ParameterSpec


def _space() -> object:
    return unwrap(
        coerce_study_space(
            [
                int_param("a", lo=0, hi=100, step=1, default=10),
                int_param("b", lo=0, hi=100, step=1, default=10),
            ]
        ),
        "space",
    )


def _priors(objective_of) -> list[dict[str, object]]:
    """14 completed generation-0 trials (exceeds TPE startup so history conditions)."""
    out: list[dict[str, object]] = []
    for i in range(14):
        a = (i * 7) % 100
        b = (i * 13) % 100
        out.append(
            {
                "generation_index": 0,
                "ask_index": i,
                "parameters": {"a": a, "b": b},
                "objective": Fraction(objective_of(i, a, b), 1),
            }
        )
    return out


# --- T21-317 [R18] P0 purity -------------------------------------------------


def test_t21_317_sampler_is_pure_function_of_its_inputs() -> None:
    """The batch is a deterministic function of exactly (space, seed, priors, generation).

    Falsifiability: history flows only through the injected argument, proven three ways —
    (1) identical inputs give an identical batch; (2) two empty-prior calls agree (no
    cross-call optuna store accumulates); (3) different prior objectives give a DIFFERENT
    batch (the argument IS consulted, so equality under (1)/(2) is a real signal).
    """
    space = _space()
    priors = _priors(lambda i, a, b: a + b)

    b1 = unwrap(propose_generation(space, 42, priors, 1, direction="max", batch_size=4))
    b2 = unwrap(propose_generation(space, 42, priors, 1, direction="max", batch_size=4))
    assert unwrap(b1.fingerprint()).value == unwrap(b2.fingerprint()).value, "same inputs -> same batch"

    e1 = unwrap(propose_generation(space, 42, [], 0, direction="max", batch_size=4))
    e2 = unwrap(propose_generation(space, 42, [], 0, direction="max", batch_size=4))
    assert unwrap(e1.fingerprint()).value == unwrap(e2.fingerprint()).value, (
        "two empty-prior calls agree -> no in-process optuna store accumulated across calls"
    )

    inverted = _priors(lambda i, a, b: 200 - (a + b))
    b3 = unwrap(propose_generation(space, 42, inverted, 1, direction="max", batch_size=4))
    assert unwrap(b3.fingerprint()).value != unwrap(b1.fingerprint()).value, (
        "different prior objectives -> different batch (history is read from the argument)"
    )


# --- T21-318 [R19] P0 order-invariance (concrete metamorphic) ----------------


def test_t21_318_same_seeded_study_order_invariant() -> None:
    """Feeding the same generation's results in different orders proposes identical trials.

    Counter-case that would FAIL: an order-dependent proposal (a sampler that fed the
    ledger view in wall-completion order rather than canonical (generation, ask) order).
    The content-sensitivity witness in T21-317 establishes that the batch DOES depend on
    the priors, so this equality under permutation is not trivially satisfied.
    """
    space = _space()
    priors = _priors(lambda i, a, b: a + b)

    forward = unwrap(propose_generation(space, 7, priors, 1, direction="max", batch_size=5))
    reversed_priors = list(reversed(priors))
    backward = unwrap(propose_generation(space, 7, reversed_priors, 1, direction="max", batch_size=5))
    # a non-trivial interleave, too.
    interleaved = priors[::2] + priors[1::2]
    mixed = unwrap(propose_generation(space, 7, interleaved, 1, direction="max", batch_size=5))

    fp_forward = unwrap(forward.fingerprint()).value
    assert unwrap(backward.fingerprint()).value == fp_forward, "reversed completion order -> identical batch"
    assert unwrap(mixed.fingerprint()).value == fp_forward, "interleaved completion order -> identical batch"


# --- T21-319 [R20] -----------------------------------------------------------


def test_t21_319_second_ask_before_tell_unsupported() -> None:
    """A second ask before the outstanding generation's tell is unsupported capability.

    Counter-case that would FAIL: the second ask returning a batch (a parallel-ask
    capability the TPE-class adapter does not have).
    """
    stepper = StudyStepper(
        space=_space(),
        seed=3,
        direction="max",
        study_fp=unwrap(fingerprint({"study": 1})),
        batch_size=2,
    )
    first = stepper.ask()
    assert is_ok(first), f"the first ask proposes a generation, got {first!r}"
    outstanding_stepper, _batch = first.value

    second = outstanding_stepper.ask()
    assert_ct04_refusal(second, RefusalCategory.UNSUPPORTED_CAPABILITY, what="parallel ask")


# --- T21-320 [R21] -----------------------------------------------------------


def test_t21_320_internal_float_converts_only_the_exact_value_into_identity() -> None:
    """A sampler internal float passes the named AD-7/AD-22 conversion; no float in identity.

    Counter-case that would FAIL: the raw binary float reaching the converted value's
    identity content, or the exact converted value being a float rather than int /
    ExactRational.
    """
    int_spec = unwrap(ParameterSpec.try_create(int_param("n", lo=0, hi=10, step=1, default=5)), "int spec")
    converted_int = unwrap(convert_sampled_value(int_spec, 4.7, rounding="half-even"), "int convert")
    assert isinstance(converted_int.value, int) and not isinstance(converted_int.value, bool)
    assert converted_int.conversion is not None, "the declared {rounding, scale} stamp is recorded"
    assert find_floats(converted_int.fp1_identity()) == [], "no raw float enters identity"

    rat_decl = rational_param("r", lo=(0, 1), hi=(1, 1), step=(1, 10), default=(1, 2))
    rat_spec = unwrap(ParameterSpec.try_create(rat_decl), "rational spec")
    converted_rat = unwrap(convert_sampled_value(rat_spec, 0.37, rounding="half-even"), "rat convert")
    assert isinstance(converted_rat.value, ExactRational), "an exact-rational parameter yields an ExactRational"
    assert find_floats(converted_rat.fp1_identity()) == [], "no raw float enters identity"


# --- T21-321 [R22] P0 one frozen registry as-of ------------------------------


def test_t21_321_admission_freezes_exactly_one_as_of_set() -> None:
    """Admission resolves exactly one registry as-of set, freezes it, and stamps the label.

    Counter-case that would FAIL: admission not freezing the port, or a post-admission
    alias / name@latest resolve still succeeding (fragments must resolve by explicit
    fingerprint only after admission, SC-11).
    """
    port, bot = bot_universe("mean-reversion")
    admitted = unwrap(admit_study(_space(), 42, port, bot="mean-reversion", direction="max"), "admitted")

    # exactly one frozen as-of set, stamped into the Study label.
    assert admitted.port.frozen is True, "admission froze the registry-read port for every trial"
    stamp = admitted.registry_as_of_stamp()
    assert stamp["fingerprint"] == admitted.set_fingerprint.value
    assert stamp["value_ns"] == admitted.registry_as_of.value_ns
    # the study label carries that one as-of set fingerprint in identity.
    label_identity = admitted.label.fp1_identity()
    assert label_identity["set_fingerprint"] == admitted.set_fingerprint.value
    assert label_identity["study_fp"] == admitted.study_fp.value

    # after admission, resolution is by explicit fingerprint only, never an alias/name@latest.
    assert_ct04_refusal(
        admitted.port.resolve("mean-reversion"), RefusalCategory.INVALID_INPUT, what="post-admit alias"
    )
    assert is_ok(admitted.port.resolve(bot.stable_id)), "an explicit fingerprint still resolves"


# --- T21-322 [R23] P0 trial label + reproduce-or-refuse ----------------------


def test_t21_322_trial_label_content_and_contract_versioning() -> None:
    """The trial label carries sampler identity, seed, provenance, study_fp; an optuna major bump refuses.

    Counter-case that would FAIL: a label missing sampler identity / seed / provenance /
    study_fp, or a differing optuna major version being transparently accepted (it must
    be a contract-versioning event), or a matching major being refused.
    """
    space = _space()
    batch = unwrap(propose_generation(space, 9, [], 0, direction="max", batch_size=2), "batch")
    study_fp = unwrap(fingerprint({"study": "s"}), "study_fp")
    label = unwrap(trial_label(study_fp, 9, 0, batch.proposals[0]), "trial label")

    assert label["role"] == "trial"
    assert label["seed"] == 9
    assert label["study_fp"] == study_fp.value
    assert isinstance(label["sampler_identity"], dict) and label["sampler_identity"], "sampler identity present"
    provenance = label["generator_provenance"]
    assert isinstance(provenance, dict) and "major_version" in provenance, "generator provenance present"

    # reproduce-or-refuse: a matching optuna major reproduces (Ok); a bumped major refuses.
    assert is_ok(refuse_sampler_contract_bump(generator_provenance())), "same optuna major re-samples"
    bumped = dict(generator_provenance())
    bumped["major_version"] = int(bumped["major_version"]) + 1
    assert_ct04_refusal(
        refuse_sampler_contract_bump(bumped), RefusalCategory.UNSUPPORTED_CAPABILITY, what="optuna major bump"
    )
