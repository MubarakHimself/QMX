"""Tier-1 tests for store-level synthetic taint, provenance & world derivation (Story 23.3).

Covers the story acceptance criteria: the store-level ``origin = synthetic`` taint
recording process, seed, source-dataset id, config fp1, generation timestamp, and
generator version (AC1); world=simulated derived from provenance, never
caller-declared, and the governed-evidence policy rejection (AC2); the replay
clock / replay-live adapter refusal on synthetic-tainted data (AC3); non-promotable
synthetic artifacts and the closed backdoor (AC4); the procedure-ephemeral contrast
that creates no store partition (AC5); and the synthetic-tainted partition router
that never writes a governed/live namespace (AC6).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import TypeVar, cast

from qmb.data import (
    ARTIFACT_DERIVED_AGGREGATE,
    ARTIFACT_SERIES,
    ARTIFACT_TICK_SERIES,
    GENERATOR_VERSION,
    GOVERNED_EVIDENCE_NAMESPACES,
    STORE_ARTIFACT_KINDS,
    STORE_DATA_PROVENANCE,
    SYNTHETIC_ORIGIN,
    SYNTHETIC_STORE_PARTITION,
    EphemeralPerturbationTaint,
    StoreReadClassification,
    SyntheticStorePartition,
    SyntheticStoreProvenance,
    data_front_identity,
    derive_world_from_store_provenance,
    generate,
    procedure_ephemeral_taint,
    read_synthetic_store,
    refuse_ephemeral_as_admission_evidence,
    refuse_promote_synthetic,
    refuse_replay_clock_on_synthetic_store,
    refuse_synthetic_load,
    refuse_synthetic_write_into_governed_namespace,
    resolve_generator_config,
    resolve_store_clock_binding,
    route_synthetic_persist,
    store_taint_identity,
    synthetic_is_promotable,
    tag_synthetic_artifact,
)
from qmb.data.gap_check import AlwaysOpenCalendar, MarketHoursCalendar
from qmf.core import RefusalCategory, Result, World, is_ok, is_refusal
from qmf.core.chrono import CalendarIdentity
from qmf.core.fingerprint import governed_namespace

T = TypeVar("T")

_STEP = 60_000_000_000  # 1-minute bars
_START = 0
_END = 600_000_000_000  # ten 1-minute slots
_STAMP = 1_700_000_000_000_000_000  # a fixed injected generation timestamp (UTC-ns)


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _always_open() -> MarketHoursCalendar:
    identity = _ok(CalendarIdentity.try_create("always-open", "v1", "none"))
    return cast("MarketHoursCalendar", AlwaysOpenCalendar(identity=identity))


def _gbm_resources(**extra: object) -> dict[str, object]:
    body: dict[str, object] = {
        "process": "gbm",
        "venue": "dukascopy-fx",
        "symbol": "EURUSD",
        "scale": 5,
        "tick_size": 1,
        "resolution": "M1",
        "bar_step_ns": _STEP,
        "start_ns": _START,
        "end_ns": _END,
        "seed_price": 110_000,
        "volatility": "0.001",
        "seed": 7,
    }
    body.update(extra)
    return body


def _history_resources(process: str = "block-bootstrap", **extra: object) -> dict[str, object]:
    body: dict[str, object] = {
        "process": process,
        "venue": "dukascopy-fx",
        "symbol": "EURUSD",
        "scale": 5,
        "tick_size": 1,
        "resolution": "M1",
        "bar_step_ns": _STEP,
        "start_ns": _START,
        "end_ns": _END,
        "seed": 11,
        "block_length": 4,
        "source_dataset": {
            "venue": "dukascopy-fx",
            "symbol": "EURUSD",
            "resolution": "M1",
            "side": "bid",
        },
    }
    body.update(extra)
    return body


def _gbm_provenance(**extra: object) -> SyntheticStoreProvenance:
    config = _ok(resolve_generator_config(_gbm_resources()))
    return _ok(tag_synthetic_artifact(config, generation_timestamp_ns=_STAMP, **extra))


# --- AC1: the store-level origin=synthetic provenance record ------------------


def test_persisted_synthetic_carries_store_level_provenance_record() -> None:
    config = _ok(resolve_generator_config(_gbm_resources()))
    config_fp = _ok(config.fingerprint()).value
    provenance = _ok(tag_synthetic_artifact(config, generation_timestamp_ns=_STAMP))
    assert isinstance(provenance, SyntheticStoreProvenance)
    # origin=synthetic AT THE STORE LEVEL, and every AC1-enumerated field is recorded.
    assert provenance.origin == SYNTHETIC_ORIGIN
    assert provenance.process == "gbm"
    assert provenance.seed == 7
    assert provenance.source_dataset_id == "none"
    assert provenance.config_fp1 == config_fp
    assert provenance.generation_timestamp_ns == _STAMP
    assert provenance.generator_version == GENERATOR_VERSION
    record = provenance.as_record()
    for field in (
        "origin",
        "process",
        "seed",
        "source_dataset_id",
        "config_fp1",
        "generation_timestamp_ns",
        "generator_version",
    ):
        assert field in record
    assert record["origin"] == "synthetic"


def test_history_seeded_store_record_cites_source_dataset_id() -> None:
    config = _ok(resolve_generator_config(_history_resources()))
    provenance = _ok(tag_synthetic_artifact(config, generation_timestamp_ns=_STAMP))
    assert provenance.process == "block-bootstrap"
    assert provenance.source_dataset_id == "dukascopy-fx:EURUSD:M1:bid"


def test_store_taint_identity_excludes_timestamp_and_semver() -> None:
    # The wall-clock timestamp and the SemVer version are recorded provenance, never
    # fp1 identity (B-13): the same config taints to a byte-identical fingerprint
    # regardless of WHEN it was generated.
    config = _ok(resolve_generator_config(_gbm_resources()))
    early = _ok(tag_synthetic_artifact(config, generation_timestamp_ns=1))
    late = _ok(tag_synthetic_artifact(config, generation_timestamp_ns=_STAMP))
    assert early.generation_timestamp_ns != late.generation_timestamp_ns
    assert "generation_timestamp_ns" not in early.fp1_identity()
    assert "generator_version" not in early.fp1_identity()
    assert _ok(early.fingerprint()).value == _ok(late.fingerprint()).value


def test_tick_series_and_derived_aggregate_are_taggable_kinds() -> None:
    config = _ok(resolve_generator_config(_gbm_resources()))
    for kind in (ARTIFACT_SERIES, ARTIFACT_TICK_SERIES, ARTIFACT_DERIVED_AGGREGATE):
        provenance = _ok(
            tag_synthetic_artifact(config, artifact_kind=kind, generation_timestamp_ns=_STAMP)
        )
        assert provenance.artifact_kind == kind
    assert set(STORE_ARTIFACT_KINDS) == {
        ARTIFACT_SERIES,
        ARTIFACT_TICK_SERIES,
        ARTIFACT_DERIVED_AGGREGATE,
    }


def test_store_record_refuses_malformed_inputs() -> None:
    config = _ok(resolve_generator_config(_gbm_resources()))
    bad_kind = tag_synthetic_artifact(
        config, artifact_kind="mystery-blob", generation_timestamp_ns=_STAMP
    )
    assert is_refusal(bad_kind)
    assert bad_kind.category is RefusalCategory.INVALID_INPUT
    assert bad_kind.context["field"] == "artifact_kind"
    bad_stamp = tag_synthetic_artifact(config, generation_timestamp_ns=-1)
    assert is_refusal(bad_stamp)
    assert bad_stamp.context["field"] == "generation_timestamp_ns"
    not_a_config = tag_synthetic_artifact({"process": "gbm"}, generation_timestamp_ns=_STAMP)
    assert is_refusal(not_a_config)
    assert not_a_config.context["field"] == "config"


def test_generate_persists_store_level_taint_into_partition() -> None:
    # The taint is a STRUCTURED store-level record in the synthetic-tainted partition,
    # NOT merely a filename convention (AC1, AC6).
    with tempfile.TemporaryDirectory() as tmp:
        receipt = _ok(
            generate(
                _gbm_resources(),
                calendar=_always_open(),
                output_root=tmp,
                generated_at_ns=_STAMP,
            )
        )
        assert receipt.store_partition == SYNTHETIC_STORE_PARTITION
        assert receipt.store_provenance_written is True
        assert receipt.store_provenance["origin"] == "synthetic"
        assert receipt.store_provenance["config_fp1"] == receipt.config_fingerprint
        assert receipt.store_provenance["generation_timestamp_ns"] == _STAMP
        # The record lives on disk under the synthetic-tainted partition, run-scoped.
        assert receipt.store_provenance_path.startswith(SYNTHETIC_STORE_PARTITION + "/")
        written = Path(tmp) / receipt.store_provenance_path
        assert written.is_file()
        on_disk = json.loads(written.read_text(encoding="utf-8"))
        assert on_disk["origin"] == "synthetic"
        assert on_disk["world"] == World.SIMULATED.value
        assert on_disk["is_promotable"] is False


def test_generate_without_root_reports_partition_but_writes_nothing() -> None:
    receipt = _ok(generate(_gbm_resources(), calendar=_always_open(), generated_at_ns=_STAMP))
    assert receipt.store_partition == SYNTHETIC_STORE_PARTITION
    assert receipt.store_provenance_written is False
    assert receipt.store_provenance["origin"] == "synthetic"


# --- AC2: world derived from provenance; governed-evidence policy rejection ----


def test_reading_store_persisted_synthetic_derives_world_simulated() -> None:
    provenance = _gbm_provenance()
    assert _ok(derive_world_from_store_provenance(provenance)) is World.SIMULATED
    partition = _ok(route_synthetic_persist(provenance))
    assert _ok(derive_world_from_store_provenance(partition)) is World.SIMULATED
    # A store-read mapping carrying the taint derives the same world.
    read_map = {"origin": "synthetic", "process": "gbm"}
    assert _ok(derive_world_from_store_provenance(read_map)) is World.SIMULATED


def test_caller_declared_non_simulated_world_on_store_read_is_invalid() -> None:
    tainted_but_declared_replay = {
        "origin": "synthetic",
        "data_provenance": STORE_DATA_PROVENANCE,
        "world": "replay",
    }
    refusal = derive_world_from_store_provenance(tainted_but_declared_replay)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "world"


def test_store_read_is_policy_rejection_for_governed_evidence() -> None:
    classification = _ok(read_synthetic_store(_gbm_provenance()))
    assert isinstance(classification, StoreReadClassification)
    assert classification.world == World.SIMULATED.value
    assert classification.data_provenance == STORE_DATA_PROVENANCE
    assert classification.governed_evidence_admissible is False
    # infra-stress and logic-smoke ONLY until GAP-0048.
    assert classification.permittable_claim_classes == ("infra-stress", "logic-smoke")
    assert classification.gap == "GAP-0048"
    refusal = classification.refuse_governed_evidence()
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION


# --- AC3: replay clock / replay-live adapter on synthetic-tainted data ---------


def test_replay_clock_on_synthetic_store_is_invalid_input() -> None:
    provenance = _gbm_provenance()
    refusal = resolve_store_clock_binding(provenance, clock="replay")
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "clock"
    direct = refuse_replay_clock_on_synthetic_store("replay")
    assert direct.category is RefusalCategory.INVALID_INPUT
    assert direct.context["data_provenance"] == STORE_DATA_PROVENANCE


def test_replay_or_live_adapter_on_synthetic_store_is_invalid_input() -> None:
    provenance = _gbm_provenance()
    for adapter in ("replay", "live"):
        refusal = resolve_store_clock_binding(provenance, clock="simulated", adapters=[adapter])
        assert is_refusal(refusal)
        assert refusal.category is RefusalCategory.INVALID_INPUT
        assert refusal.context["field"] == "adapters"


def test_simulated_clock_binds_synthetic_store() -> None:
    provenance = _gbm_provenance()
    assert _ok(resolve_store_clock_binding(provenance, clock="simulated")) is World.SIMULATED
    assert (
        _ok(resolve_store_clock_binding(provenance, clock="simulated", adapters=["simulated"]))
        is World.SIMULATED
    )


# --- AC4: non-promotable; the closed synthetic backdoor -----------------------


def test_synthetic_is_non_promotable() -> None:
    assert synthetic_is_promotable() is False
    assert _gbm_provenance().is_promotable is False
    refusal = refuse_promote_synthetic("gbm-run-1")
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert refusal.context["is_promotable"] is False


def test_loading_synthetic_into_replay_or_live_refuses() -> None:
    for target in ("replay", "live"):
        refusal = refuse_synthetic_load(target)
        assert is_refusal(refusal)
        assert refusal.category is RefusalCategory.POLICY_REJECTION
        assert refusal.context["target_world"] == target
    # world=simulated is the synthetic data's legal home.
    assert is_ok(refuse_synthetic_load("simulated"))


# --- AC5: procedure-ephemeral perturbation creates no store partition ----------


def test_procedure_ephemeral_perturbation_stays_replay_no_partition() -> None:
    for procedure in ("block-bootstrap", "trade-shuffle"):
        taint = _ok(procedure_ephemeral_taint(procedure, 7))
        assert isinstance(taint, EphemeralPerturbationTaint)
        assert taint.world == World.REPLAY.value
        assert taint.data_provenance == "procedure-ephemeral"
        assert taint.claim_class == "robustness"
        assert taint.creates_store_partition is False
        # The procedure identity + seed enter the CT-32 label.
        assert taint.label_content() == {"procedure": procedure, "seed": 7}


def test_procedure_ephemeral_is_never_admission_evidence() -> None:
    refusal = refuse_ephemeral_as_admission_evidence("block-bootstrap")
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert refusal.context["claim_class"] == "robustness"


# --- AC6: partition routing never writes a governed/live namespace ------------


def test_synthetic_write_routes_only_into_tainted_partition() -> None:
    provenance = _gbm_provenance()
    partition = _ok(route_synthetic_persist(provenance))
    assert isinstance(partition, SyntheticStorePartition)
    assert partition.namespace == SYNTHETIC_STORE_PARTITION
    assert partition.is_governed_namespace is False
    assert partition.relative_path.startswith(SYNTHETIC_STORE_PARTITION + "/")
    assert partition.world is World.SIMULATED
    # An explicit request for the synthetic partition is fine.
    assert is_ok(route_synthetic_persist(provenance, requested_namespace=SYNTHETIC_STORE_PARTITION))


def test_synthetic_write_into_governed_namespace_refuses() -> None:
    provenance = _gbm_provenance()
    for namespace in sorted(GOVERNED_EVIDENCE_NAMESPACES):
        refusal = route_synthetic_persist(provenance, requested_namespace=namespace)
        assert is_refusal(refusal)
        assert refusal.category is RefusalCategory.POLICY_REJECTION
        assert refusal.context["field"] == "namespace"
    direct = refuse_synthetic_write_into_governed_namespace("live")
    assert direct.category is RefusalCategory.POLICY_REJECTION


def test_synthetic_partition_is_distinct_from_governed_namespaces() -> None:
    assert SYNTHETIC_STORE_PARTITION not in GOVERNED_EVIDENCE_NAMESPACES
    assert frozenset({"live", "replay"}) == GOVERNED_EVIDENCE_NAMESPACES
    # qmf-core independently refuses a governed write for world=simulated (FM-7).
    simulated = governed_namespace(World.SIMULATED)
    assert is_refusal(simulated)
    assert simulated.category is RefusalCategory.POLICY_REJECTION


# --- identity fold ------------------------------------------------------------


def test_store_taint_identity_is_folded_into_data_front_identity() -> None:
    identity = store_taint_identity()
    assert identity["synthetic_store_partition"] == SYNTHETIC_STORE_PARTITION
    assert identity["synthetic_is_promotable"] is False
    # The store-taint identity never leaks package SemVer (B-13).
    assert GENERATOR_VERSION not in identity.values()
    front = data_front_identity()
    for key, value in identity.items():
        assert front[key] == value
