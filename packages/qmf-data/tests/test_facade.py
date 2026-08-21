"""Tier-1 tests for the EvidenceStore facade (AC1, AC5)."""

from __future__ import annotations

from pathlib import Path

from qmf.core import World, is_ok, is_refusal
from qmf.data.store import EvidenceStore


def test_for_world_live_and_replay_resolve(store: EvidenceStore) -> None:
    live = store.for_world(World.LIVE)
    replay = store.for_world(World.REPLAY)
    assert is_ok(live)
    assert is_ok(replay)
    assert live.value.world is World.LIVE
    assert replay.value.world is World.REPLAY


def test_for_world_simulated_is_refused(store: EvidenceStore) -> None:
    result = store.for_world(World.SIMULATED)
    assert is_refusal(result)
    assert result.category.value == "policy rejection"


def test_for_world_is_cached(store: EvidenceStore) -> None:
    first = store.for_world(World.LIVE)
    second = store.for_world(World.LIVE)
    assert is_ok(first)
    assert is_ok(second)
    assert first.value is second.value


def test_world_store_bundles_four_boundaries(store: EvidenceStore) -> None:
    world = store.for_world(World.LIVE)
    assert is_ok(world)
    bundle = world.value
    assert bundle.append_store is not None
    assert bundle.journal is not None
    assert bundle.registry_room is not None
    assert bundle.backup_input is not None


def test_world_isolation_is_storage_separation(store: EvidenceStore) -> None:
    live = store.for_world(World.LIVE)
    replay = store.for_world(World.REPLAY)
    assert is_ok(live)
    assert is_ok(replay)
    receipt = live.value.append_store.append_raw([{"t": 1, "px": 100}])
    assert is_ok(receipt)
    # The same fingerprint is absent in the replay world's room — separate storage.
    read = replay.value.append_store.read_raw(receipt.value.fingerprint.value)
    assert is_refusal(read)
    assert read.category.value == "invalid input"


def test_root_property(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    store = EvidenceStore(root)
    assert store.root == root


def test_for_world_accepts_string(store: EvidenceStore) -> None:
    result = store.for_world("live")
    assert is_ok(result)
    assert result.value.world is World.LIVE
