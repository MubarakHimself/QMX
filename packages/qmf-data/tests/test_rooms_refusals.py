"""Tier-1 tests for room-roles, world routing, and the refusal builders."""

from __future__ import annotations

from qmf.core import RefusalCategory, Retryability, World, is_ok, is_refusal
from qmf.data.store.engines import StoreEngineError
from qmf.data.store.refusals import (
    invalid_input,
    policy_rejection,
    storage_failure,
    translate_engine_failure,
)
from qmf.data.store.rooms import (
    EVIDENCE_BEARING_ROLES,
    ROOM_ROLE_VALUES,
    RoomRole,
    namespace_block,
    namespace_for_write,
    require_same_world,
    require_write_world,
)


def test_room_role_vocabulary_matches_ct11_order() -> None:
    assert ROOM_ROLE_VALUES == (
        "ingest door",
        "immutable raw archive",
        "processed",
        "journal",
        "split-governed research door",
        "backup",
        "registry room",
    )


def test_only_raw_archive_and_journal_are_evidence_bearing() -> None:
    assert frozenset({RoomRole.IMMUTABLE_RAW_ARCHIVE, RoomRole.JOURNAL}) == EVIDENCE_BEARING_ROLES


def test_namespace_for_write_routes_live_and_replay_apart() -> None:
    live = namespace_for_write(World.LIVE)
    replay = namespace_for_write(World.REPLAY)
    assert is_ok(live)
    assert is_ok(replay)
    assert live.value != replay.value


def test_namespace_for_write_refuses_simulated() -> None:
    result = namespace_for_write(World.SIMULATED)
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_namespace_block_none_for_writable_refusal_for_simulated() -> None:
    assert namespace_block(World.LIVE) is None
    assert namespace_block(World.REPLAY) is None
    blocked = namespace_block(World.SIMULATED)
    assert blocked is not None
    assert blocked.category is RefusalCategory.POLICY_REJECTION


def test_require_same_world_requires_declaration_and_allows_same() -> None:
    # M4: an omitted (None) world declaration is refused (invalid input) so the guard
    # always evaluates; declaring the room's own world (member or string) is allowed.
    none_declared = require_same_world(World.LIVE, None)
    assert is_refusal(none_declared)
    assert none_declared.category is RefusalCategory.INVALID_INPUT
    assert is_ok(require_same_world(World.LIVE, World.LIVE))
    assert is_ok(require_same_world(World.LIVE, "live"))


def test_require_same_world_refuses_cross_world() -> None:
    result = require_same_world(World.LIVE, World.REPLAY)
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context.get("requested") == "replay"


def test_require_same_world_rejects_unknown_world_string_and_type() -> None:
    assert is_refusal(require_same_world(World.LIVE, "banana"))
    assert is_refusal(require_same_world(World.LIVE, 42))


# --- H1: require_write_world routes a write on the payload's own declared world ---


def test_require_write_world_passes_none_and_matching() -> None:
    # A payload that declares no world inherits the room's world (the writer stamps it).
    assert require_write_world(World.LIVE, None) is None
    # A matching declared world — a World member or its string — passes.
    assert require_write_world(World.LIVE, World.LIVE) is None
    assert require_write_world(World.LIVE, "live") is None


def test_require_write_world_refuses_mismatch_and_simulated() -> None:
    replay = require_write_world(World.LIVE, "replay")
    assert replay is not None
    assert replay.category is RefusalCategory.POLICY_REJECTION
    assert replay.context.get("field") == "world"
    assert replay.context.get("declared") == "replay"
    simulated = require_write_world(World.LIVE, World.SIMULATED)
    assert simulated is not None
    assert simulated.category is RefusalCategory.POLICY_REJECTION


def test_require_write_world_refuses_malformed() -> None:
    bad_str = require_write_world(World.LIVE, "nowhere")
    assert bad_str is not None
    assert bad_str.category is RefusalCategory.INVALID_INPUT
    bad_type = require_write_world(World.LIVE, 7)
    assert bad_type is not None
    assert bad_type.category is RefusalCategory.INVALID_INPUT


def test_refusal_builders_carry_expected_categories() -> None:
    assert invalid_input("f", "why").category is RefusalCategory.INVALID_INPUT
    assert policy_rejection("f", "why").category is RefusalCategory.POLICY_REJECTION
    sf = storage_failure("disk full")
    assert sf.category is RefusalCategory.STORAGE_FAILURE
    assert sf.retryability is Retryability.YES


def test_translate_engine_failure_maps_retryable_and_corrupt() -> None:
    transient = translate_engine_failure(StoreEngineError("locked", engine="sqlite"))
    assert transient.category is RefusalCategory.STORAGE_FAILURE
    assert transient.retryability is Retryability.YES
    assert transient.context.get("engine") == "sqlite"

    corrupt = translate_engine_failure(
        StoreEngineError("malformed", engine="parquet", retryable=False, detail={"key": "abc"})
    )
    assert corrupt.retryability is Retryability.NO
    assert corrupt.context.get("key") == "abc"
