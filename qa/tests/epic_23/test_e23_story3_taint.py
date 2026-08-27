"""Epic 23 · Story 23.3 — synthetic taint, store provenance, world derivation, namespace refusals.

Independent L3 acceptance tests T23-312..317. Each names the concrete counter-case that
would make it FAIL. Source is read-only evidence; a failing test is a FINDING.
"""

from __future__ import annotations

from conftest import (
    BASE_NS,
    assert_ct04_refusal,
    gbm_resources,
    is_ok,
    is_refusal,
    unwrap,
)

from qmf.core.fingerprint import World
from qmf.core.refusal import RefusalCategory
from qmb.data import (
    SYNTHETIC_STORE_PARTITION,
    derive_world_from_store_provenance,
    generate,
    procedure_ephemeral_taint,
    refuse_ephemeral_as_admission_evidence,
    refuse_promote_synthetic,
    refuse_synthetic_load,
    refuse_synthetic_write_into_governed_namespace,
    resolve_generator_config,
    resolve_store_clock_binding,
    route_synthetic_persist,
    tag_synthetic_artifact,
)

_SIX_PROVENANCE_FIELDS = (
    "process",
    "seed",
    "source_dataset_id",
    "config_fp1",
    "generation_timestamp_ns",
    "generator_version",
)


def _provenance():
    cfg = unwrap(resolve_generator_config(gbm_resources()), "config")
    return unwrap(tag_synthetic_artifact(cfg, generation_timestamp_ns=BASE_NS), "provenance")


# --- T23-312 (P0, R4/AR-14): origin=synthetic store-level record --------------


def test_t23_312_persisted_synthetic_carries_store_level_origin_and_six_fields() -> None:
    """A persisted synthetic artifact carries ``origin=synthetic`` at the store level (a structured
    record, not a filename) recording all six provenance fields, and its derived world is simulated.

    Counter-case that FAILS: the taint is only a filename convention; ``origin`` is not
    ``synthetic``; or any of the six provenance fields is absent from the store record.
    """
    provenance = _provenance()
    record = provenance.as_record()
    assert isinstance(record, dict)  # queryable store metadata, not a filename
    assert record["origin"] == "synthetic"
    assert record["world"] == "simulated"
    assert record["data_provenance"] == "synthetic-tainted"
    for field in _SIX_PROVENANCE_FIELDS:
        assert field in record, f"provenance record missing {field!r}"
        assert record[field] is not None

    # the same record rides the generate() receipt as store-level metadata.
    receipt = unwrap(generate(gbm_resources()), "generate")
    assert receipt.origin == "synthetic"
    assert isinstance(receipt.store_provenance, dict)
    assert receipt.store_provenance.get("origin") == "synthetic"
    for field in _SIX_PROVENANCE_FIELDS:
        assert field in receipt.store_provenance


# --- T23-313 (P0, B-7/SC-06): world derived from provenance, never declared ---


def test_t23_313_world_is_provenance_derived_not_caller_declared() -> None:
    """World is derived ``simulated`` from a synthetic store taint; a caller-declared
    non-simulated world on synthetic-tainted input RETURNS ``invalid input`` — a caller may not
    override the derivation.

    Counter-case that FAILS: a caller-declared ``world=replay`` on synthetic-tainted data is
    honored, or the derivation returns anything other than simulated.
    """
    provenance = _provenance()
    assert unwrap(derive_world_from_store_provenance(provenance), "derived world") is World.SIMULATED
    assert unwrap(derive_world_from_store_provenance({"origin": "synthetic"}), "mapping derive") is World.SIMULATED

    # a caller-declared world=replay on synthetic-tainted input is refused.
    assert_ct04_refusal(
        derive_world_from_store_provenance({"origin": "synthetic", "world": "replay"}),
        RefusalCategory.INVALID_INPUT,
        what="caller-declared world=replay override",
    )
    assert_ct04_refusal(
        derive_world_from_store_provenance({"origin": "synthetic", "world": "live"}),
        RefusalCategory.INVALID_INPUT,
        what="caller-declared world=live override",
    )
    # discriminator: a caller-declared world=simulated agrees with the derivation and passes.
    assert unwrap(
        derive_world_from_store_provenance({"origin": "synthetic", "world": "simulated"}),
        "agreeing declaration",
    ) is World.SIMULATED


# --- T23-314 (P0, B-2/B-3/B-7): replay-clock guard (top-level) ----------------


def test_t23_314_replay_clock_on_synthetic_returns_invalid_input() -> None:
    """Binding a replay clock (or a replay/live adapter) to synthetic-tainted store data RETURNS a
    typed ``invalid input`` — B-7 wins over B-2; a simulated clock binds it.

    Counter-case that FAILS: a replay clock (or replay/live adapter) on synthetic-tainted data is
    accepted, or a simulated clock is refused.
    """
    provenance = _provenance()
    assert_ct04_refusal(
        resolve_store_clock_binding(provenance, clock="replay"),
        RefusalCategory.INVALID_INPUT,
        what="replay clock on synthetic store",
    )
    assert_ct04_refusal(
        resolve_store_clock_binding(provenance, clock="simulated", adapters=["replay"]),
        RefusalCategory.INVALID_INPUT,
        what="replay adapter on synthetic store",
    )
    # the generator-config compilation path also refuses a flat replay clock.
    assert_ct04_refusal(
        resolve_generator_config(gbm_resources(clock="replay")),
        RefusalCategory.INVALID_INPUT,
        what="flat replay clock in generator config",
    )
    # discriminator: a simulated clock (no non-simulated adapter) binds and derives simulated.
    assert unwrap(
        resolve_store_clock_binding(provenance, clock="simulated"),
        "simulated clock binding",
    ) is World.SIMULATED


# --- T23-315 (P0, R4/R8): non-promotable synthetic artifacts ------------------


def test_t23_315_synthetic_is_non_promotable_into_replay_live_or_toward_money() -> None:
    """Loading synthetic data into a ``world=replay`` / ``world=live`` context, or promoting a
    synthetic artifact toward live money, RETURNS a typed refusal; ``world=simulated`` is its legal
    home.

    Counter-case that FAILS: a synthetic load into replay/live is admitted, or a promotion attempt
    succeeds.
    """
    assert_ct04_refusal(
        refuse_synthetic_load(World.REPLAY),
        RefusalCategory.POLICY_REJECTION,
        what="synthetic load into replay",
    )
    assert_ct04_refusal(
        refuse_synthetic_load(World.LIVE),
        RefusalCategory.POLICY_REJECTION,
        what="synthetic load into live",
    )
    assert_ct04_refusal(
        refuse_promote_synthetic("artifact-fp1"),
        RefusalCategory.POLICY_REJECTION,
        what="promote synthetic toward live money",
    )
    # discriminator: loading into world=simulated (its legal home) passes.
    assert is_ok(refuse_synthetic_load(World.SIMULATED))


# --- T23-316 (P1, B-7/B-14): procedure-ephemeral stays world=replay -----------


def test_t23_316_procedure_ephemeral_perturbation_stays_replay_no_partition() -> None:
    """A procedure-ephemeral perturbation that persists no synthetic series stays ``world=replay``,
    creates NO store partition, is robustness-only (never edge, never admission evidence), and its
    procedure identity + seed enter the CT-32 label.

    Counter-case that FAILS: an ephemeral perturbation derives world=simulated, creates a store
    partition, or is admissible as edge/admission evidence.
    """
    taint = unwrap(procedure_ephemeral_taint("block-bootstrap-shuffle", 5), "ephemeral taint")
    assert taint.world == World.REPLAY.value
    assert taint.creates_store_partition is False
    assert taint.claim_class == "robustness"
    assert taint.data_provenance == "procedure-ephemeral"
    # procedure identity + seed enter the label content.
    label = taint.label_content()
    assert label["procedure"] == "block-bootstrap-shuffle"
    assert label["seed"] == 5
    # citing it as admission evidence is refused.
    assert_ct04_refusal(
        refuse_ephemeral_as_admission_evidence("block-bootstrap-shuffle"),
        RefusalCategory.POLICY_REJECTION,
        what="ephemeral cited as admission evidence",
    )


# --- T23-317 (P0, AR-33/B-7): never write the governed/live namespace ---------


def test_t23_317_synthetic_write_routes_only_to_tainted_partition() -> None:
    """A synthetic persist routes only into the synthetic-tainted partition; a ``world=simulated``
    write aimed at a governed/live namespace RETURNS a refusal.

    Counter-case that FAILS: a synthetic write into the live or governed-evidence namespace is
    admitted, or the default route lands anywhere other than the synthetic-tainted partition.
    """
    provenance = _provenance()
    # default route -> the synthetic-tainted partition, never a governed namespace.
    partition = unwrap(route_synthetic_persist(provenance), "routed partition")
    assert partition.namespace == SYNTHETIC_STORE_PARTITION
    assert partition.is_governed_namespace is False

    # a write aimed at the live namespace is refused.
    assert_ct04_refusal(
        route_synthetic_persist(provenance, requested_namespace="live"),
        RefusalCategory.POLICY_REJECTION,
        what="synthetic write into live namespace",
    )
    # a write aimed at the governed replay namespace is refused.
    assert_ct04_refusal(
        route_synthetic_persist(provenance, requested_namespace="replay"),
        RefusalCategory.POLICY_REJECTION,
        what="synthetic write into governed replay namespace",
    )
    # the direct namespace-firewall refusal.
    assert_ct04_refusal(
        refuse_synthetic_write_into_governed_namespace("live"),
        RefusalCategory.POLICY_REJECTION,
        what="refuse_synthetic_write_into_governed_namespace",
    )
    # a real generation persists only into the synthetic-tainted partition.
    receipt = unwrap(generate(gbm_resources()), "generate")
    assert receipt.store_partition == SYNTHETIC_STORE_PARTITION
