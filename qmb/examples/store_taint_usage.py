"""Reference usage — store-level synthetic taint, provenance & world derivation (Story 23.3).

Executable::

    python qmb/examples/store_taint_usage.py

Shows the things AC1-AC6 pin down for store-persisted synthetic data:

1. A persisted synthetic artifact carries origin=synthetic at the STORE level — a
   structured provenance record (process, seed, source-dataset id, config fp1,
   generation timestamp, generator version), not merely a filename.
2. A run that reads store-persisted synthetic data derives world=simulated from
   provenance (never caller-declared) and is a policy rejection for governed
   evidence until GAP-0048 — infra-stress and logic-smoke only.
3. A replay clock — or a replay/live adapter — bound to synthetic-tainted data is
   invalid input; B-7 wins over B-2.
4. A synthetic artifact is non-promotable: loading it into a world=replay or
   world=live context, or promoting it toward live money, is refused.
5. A procedure-ephemeral perturbation persists no synthetic series, so world stays
   replay, the procedure identity + seed enter the label, and the claim is
   robustness-only — never admission evidence.
6. A generation persists only into the synthetic-tainted store partition, never
   the live or governed-evidence namespace.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.data import (
    GOVERNED_EVIDENCE_NAMESPACES,
    SYNTHETIC_STORE_PARTITION,
    ResolvedGeneratorConfig,
    derive_world_from_store_provenance,
    procedure_ephemeral_taint,
    read_synthetic_store,
    refuse_promote_synthetic,
    refuse_synthetic_load,
    resolve_generator_config,
    resolve_store_clock_binding,
    route_synthetic_persist,
    synthetic_is_promotable,
    tag_synthetic_artifact,
)
from qmf.core import RefusalCategory, Result, World, is_ok, is_refusal

T = TypeVar("T")

_STAMP = 1_700_000_000_000_000_000


def _ok(result: Result[T]) -> T:
    if not is_ok(result):
        raise AssertionError(result)
    return result.value


def _gbm_config() -> ResolvedGeneratorConfig:
    return _ok(
        resolve_generator_config(
            {
                "process": "gbm",
                "venue": "dukascopy-fx",
                "symbol": "EURUSD",
                "scale": 5,
                "tick_size": 1,
                "resolution": "M1",
                "bar_step_ns": 60_000_000_000,
                "start_ns": 0,
                "end_ns": 600_000_000_000,
                "seed_price": 110_000,
                "volatility": "0.001",
                "seed": 7,
            }
        )
    )


def main() -> None:
    config = _gbm_config()

    # 1. store-level origin=synthetic provenance record (AC1)
    provenance = _ok(tag_synthetic_artifact(config, generation_timestamp_ns=_STAMP))
    record = provenance.as_record()
    assert record["origin"] == "synthetic"
    assert record["config_fp1"] == _ok(config.fingerprint()).value
    assert record["generation_timestamp_ns"] == _STAMP
    assert record["source_dataset_id"] == "none"
    print("store-level origin=synthetic record: process, seed, config fp1, timestamp, version")

    # 2. world derived from provenance; governed-evidence policy rejection (AC2)
    assert _ok(derive_world_from_store_provenance(provenance)) is World.SIMULATED
    classification = _ok(read_synthetic_store(provenance))
    assert classification.governed_evidence_admissible is False
    gate = classification.refuse_governed_evidence()
    assert is_refusal(gate) and gate.category is RefusalCategory.POLICY_REJECTION
    print("store read derives world=simulated; governed evidence refused until GAP-0048")
    print("simulated permits:", " ".join(classification.permittable_claim_classes))

    # 3. replay clock / replay-live adapter on synthetic-tainted data is invalid input (AC3)
    replay_clock = resolve_store_clock_binding(provenance, clock="replay")
    assert is_refusal(replay_clock) and replay_clock.category is RefusalCategory.INVALID_INPUT
    live_adapter = resolve_store_clock_binding(provenance, clock="simulated", adapters=["live"])
    assert is_refusal(live_adapter) and live_adapter.category is RefusalCategory.INVALID_INPUT
    assert _ok(resolve_store_clock_binding(provenance, clock="simulated")) is World.SIMULATED
    print("replay clock or replay/live adapter on synthetic data is invalid input; B-7 wins")

    # 4. non-promotable; the closed synthetic backdoor (AC4)
    assert synthetic_is_promotable() is False
    for target in ("replay", "live"):
        refusal = refuse_synthetic_load(target)
        assert is_refusal(refusal) and refusal.category is RefusalCategory.POLICY_REJECTION
    assert is_ok(refuse_synthetic_load("simulated"))
    promote = refuse_promote_synthetic("gbm-run")
    assert promote.category is RefusalCategory.POLICY_REJECTION
    print("synthetic is non-promotable; loading into replay/live or promoting to live refused")

    # 5. procedure-ephemeral perturbation persists no synthetic series (AC5)
    ephemeral = _ok(procedure_ephemeral_taint("block-bootstrap", 7))
    assert ephemeral.world == World.REPLAY.value
    assert ephemeral.creates_store_partition is False
    assert ephemeral.claim_class == "robustness"
    assert ephemeral.label_content() == {"procedure": "block-bootstrap", "seed": 7}
    print("procedure-ephemeral perturbation stays world=replay, no partition, robustness-only")

    # 6. a generation persists only into the synthetic-tainted partition (AC6)
    partition = _ok(route_synthetic_persist(provenance))
    assert partition.namespace == SYNTHETIC_STORE_PARTITION
    assert partition.is_governed_namespace is False
    for governed in sorted(GOVERNED_EVIDENCE_NAMESPACES):
        refusal = route_synthetic_persist(provenance, requested_namespace=governed)
        assert is_refusal(refusal) and refusal.category is RefusalCategory.POLICY_REJECTION
    print("synthetic write routes only into the synthetic-tainted partition, never live/governed")

    print("store taint ok")


if __name__ == "__main__":
    main()
