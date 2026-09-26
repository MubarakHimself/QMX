"""Reference usage — the pure, generation-stepped TPE-class sampler (Story 21.4).

Executable::

    python qmb/examples/optimize_sampler_usage.py

Shows the things B-8 / AR-50 / Story 21.4 pin down:

1. The sampler port is a PURE function of exactly (space, seed, prior trial
   results, generation index): the same inputs always propose the same batch, and
   trial history is read from the ledger view the caller passes in — no in-process
   optuna study, daemon, or optuna store is consulted for history.
2. Search steps in deterministic generations (propose -> run -> barrier ->
   condition): conditioning on the completed generation is order-independent, so
   two runs of the same seeded Study propose identical trials regardless of the
   order trials completed in.
3. A second ask before the outstanding generation's tell is refused
   ``unsupported capability`` for the TPE-class adapter.
4. The adapter may float internally, but a sampled value enters identity only
   through a named AD-7/AD-22 conversion (declared rounding mode + target scale);
   only the converted exact value is identity-bearing — the internal float never is.
5. Study admission resolves exactly one registry as-of through the single B-15
   registry-read port, freezes it for every trial, and stamps it plus study_fp into
   the Study label; after admission fragments resolve by explicit fingerprint.
6. Every trial label carries sampler identity, seed, generator provenance, and
   study_fp, and a future optuna major bump is a contract-versioning event.
"""

from __future__ import annotations

from fractions import Fraction
from typing import TypeVar

from qmb.doors import api
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import ExactRational, RoundingMode, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import RegistrationRecord

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_SEVERITY = "workspace-declared"
_R = UnitKind.DIMENSIONLESS_RATIO


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int = _NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _writer() -> WriterId:
    return _unwrap(WriterId.try_create("node-a", "authoring", "study", "boot-1"), "writer")


def _space() -> qmb.StudyParameterSpace:
    return _unwrap(
        api.coerce_study_space(
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
            ]
        ),
        "study space",
    )


def main() -> None:
    space = _space()

    # 1. The pure port: the same (space, seed, priors, generation) yields the same batch.
    first = _unwrap(
        api.propose_generation(space, 4242, [], 0, direction="max", batch_size=6), "gen0"
    )
    again = _unwrap(
        api.propose_generation(space, 4242, [], 0, direction="max", batch_size=6), "gen0"
    )
    assert _unwrap(first.fingerprint(), "fp") == _unwrap(again.fingerprint(), "fp")
    assert first.size == 6
    assert api.SAMPLER_CONSULTS_OPTUNA_STORE is False
    print("pure sampler port: same (space, seed, priors, generation) proposes the identical batch")

    # 2. Condition on a completed generation; order of completion cannot change the model.
    priors = [
        {
            "generation_index": 0,
            "ask_index": trial.ask_index,
            "parameters": trial.assignment,
            "objective": Fraction(trial.ask_index + 1),
        }
        for trial in first.proposals
    ]
    ordered = _unwrap(
        api.propose_generation(space, 4242, priors, 1, direction="max", batch_size=6), "g1"
    )
    shuffled = _unwrap(
        api.propose_generation(
            space, 4242, list(reversed(priors)), 1, direction="max", batch_size=6
        ),
        "g1-shuffled",
    )
    assert _unwrap(ordered.fingerprint(), "fp") == _unwrap(shuffled.fingerprint(), "fp")
    print(
        "identical trials regardless of completion order: "
        "a shuffled ledger view proposes the same batch"
    )

    # 3. A second ask before the outstanding tell is unsupported for the TPE-class adapter.
    study_fp = _unwrap(fingerprint({"study": "demo"}), "study fp")
    stepper = qmb.StudyStepper(
        space=space, seed=99, direction="max", study_fp=study_fp, batch_size=4
    )
    asked = _unwrap(stepper.ask(), "ask")
    outstanding_stepper, batch = asked
    refused = outstanding_stepper.ask()
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    print("a second ask before the outstanding generation's tell is unsupported capability")

    # The barrier is the whole generation: condition on it, then the next ask advances.
    results = [
        {
            "generation_index": 0,
            "ask_index": trial.ask_index,
            "parameters": trial.assignment,
            "objective": Fraction(10 - trial.ask_index),
        }
        for trial in batch.proposals
    ]
    conditioned = _unwrap(outstanding_stepper.tell(results), "tell")
    partial = outstanding_stepper.tell(results[:1])
    assert is_refusal(partial)  # the barrier refuses a partial generation
    advanced = _unwrap(conditioned.ask(), "ask gen1")
    assert advanced[1].generation_index == 1
    print(
        "propose -> run -> barrier -> condition: "
        "a partial tell is refused; a full generation advances"
    )

    # 4. An internal float enters identity only through the named AD-7/AD-22 conversion.
    atr = next(spec for spec in space.parameters if spec.name == "atr_mult")
    converted = _unwrap(
        api.convert_sampled_value(atr, 1.734820, rounding=RoundingMode.HALF_EVEN), "conv"
    )
    identity = converted.fp1_identity()
    assert isinstance(converted.value, ExactRational)  # exact, never a float
    assert identity["value"] == converted.value.fp1_identity()
    assert identity["conversion"] == {"rounding": "half-even", "scale": 1}
    assert not any(isinstance(part, float) for part in identity.values())
    missing_mode = api.convert_sampled_value(atr, 1.734820, rounding="not-a-mode")
    assert is_refusal(missing_mode)
    print(
        "an internal float enters identity only through a named AD-7/AD-22 conversion; "
        "the float never does"
    )

    # 5. Study admission: one registry as-of resolved through the B-15 port, frozen for every trial.
    bot_record = _record("bot-definition", {"class": "bot-definition", "alias": "mean-reversion"})
    pointer = _unwrap(
        DatedPointer.try_create("mean-reversion", bot_record.stable_id, _instant()), "pointer"
    )
    as_of = _unwrap(
        AsOfSet.try_create(_instant(), records=(bot_record,), pointers=(pointer,)), "as-of"
    )
    hub = _unwrap(PassiveHub.try_create((as_of,)), "hub")
    port = _unwrap(RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY), "port")
    admitted = _unwrap(
        api.admit_study(space, 4242, port, bot=bot_record.stable_id, direction="max"), "admitted"
    )
    assert admitted.port.frozen is True
    assert admitted.registry_as_of == as_of.registry_as_of
    assert admitted.set_fingerprint == as_of.fingerprint
    assert admitted.label.registry_as_of_stamp()["fingerprint"] == as_of.fingerprint.value
    print(
        "one registry as-of resolved through the B-15 port, frozen for every trial, "
        "stamped into the study label"
    )

    assert is_refusal(admitted.port.resolve("mean-reversion"))
    assert is_refusal(admitted.port.resolve("mean-reversion@latest"))
    print("after admission, fragments resolve by explicit fingerprint, never name@latest")

    # 6. Every trial label carries sampler identity, seed, generator provenance, and study_fp.
    admitted_stepper = _unwrap(admitted.stepper(batch_size=4), "stepper")
    admitted_asked = _unwrap(admitted_stepper.ask(), "ask")
    labels = _unwrap(admitted_asked[0].trial_labels(), "labels")
    label = labels[0]
    assert label["role"] == "trial"
    assert label["sampler_identity"] == qmb.sampler_identity()
    assert label["generator_provenance"] == qmb.generator_provenance()
    assert label["seed"] == 4242
    assert label["study_fp"] == admitted.study_fp.value
    assert is_ok(fingerprint(label))
    print("every trial label carries sampler identity, seed, generator provenance, and study_fp")

    # A future optuna major bump is a contract-versioning event, never a transparent update.
    provenance = qmb.generator_provenance()
    assert is_ok(api.refuse_sampler_contract_bump(provenance))
    bumped = {**provenance, "major_version": 999}  # a future optuna major
    refused_bump = api.refuse_sampler_contract_bump(bumped)
    assert is_refusal(refused_bump)
    assert refused_bump.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    print("a future optuna major bump is a contract-versioning event, never a transparent update")

    # The qmb door is a thin wrapper over the one pure library sampler surface.
    assert api.propose_generation is qmb.propose_generation
    assert api.admit_study is qmb.admit_study
    assert api.convert_sampled_value is qmb.convert_sampled_value
    print("the qmb door is a thin wrapper over one pure library sampler surface")

    print(f"qmb {qmb.__version__}")
    print("optuna TPE-class sampler ok")


def _record(kind: str, body: object) -> RegistrationRecord:
    return _unwrap(
        RegistrationRecord.try_create(kind, 1, (), body, _writer(), 0, _instant()),
        "record",
    )


if __name__ == "__main__":
    main()
