"""Epic 13 — L2 integration / component tests (T13-201..207).

Multiple qmb modules composed in-process: compiler <- registry-read port <-
fragment materializer; compile -> binding mint. A failing assertion is a FINDING.
"""

from __future__ import annotations

import pytest
from qmf.core.fingerprint import World
from qmf.core.refusal import RefusalCategory, is_ok, is_refusal

from _fixtures import DEFAULTS, SEED, base_run_spec, build_universe, unwrap
from qmb.config import (
    ledger_key,
    run_id_root,
)
from qmb.doors import api
from qmb.registryread import HUB_KIND, STATE_KIND, read_port_identity


# --- T13-201 -----------------------------------------------------------------
def test_t13_201_one_port_no_second_cache() -> None:
    """The ONE library-owned registry-read port is the sole resolution path; no
    door-side and no second cache. (13.2 AC1)"""
    from qmb.config import compile_run_config

    u = build_universe()
    # the compiler resolves only through a RegistryReadPort; a non-port is refused
    refused = compile_run_config(
        object(),
        book_fragment=u.book_fragment,
        bms_fragment=u.bms_fragment,
        run_spec=base_run_spec(),
        workspace_defaults=dict(DEFAULTS),
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT

    # door autocomplete resolves through this SAME port (no separate cache/index):
    # every completion candidate is one this port also resolves, to the same fp1.
    candidates = u.port.complete("", kind="book-definition")
    assert candidates, "expected at least one autocomplete candidate"
    for candidate in candidates:
        resolved = u.port.resolve(candidate.value)
        assert is_ok(resolved)
        assert resolved.value.cite() == candidate.cite()

    # neither shipped door holds a cache or computes a run id of its own
    import qmb.doors.api as api_door
    import qmb.doors.cli as cli_door

    assert cli_door.HOLDS_CACHE is False and cli_door.COMPUTES_RUN_ID is False
    assert api_door.HOLDS_CACHE is False and api_door.COMPUTES_RUN_ID is False


# --- T13-202 -----------------------------------------------------------------
def test_t13_202_passive_storage_immutable_no_live_service() -> None:
    """Registry state resolves from an immutable, fingerprinted as-of set delivered by
    passive storage — no live/central-service path; never a 'snapshot'. (13.2 AC5)"""
    u = build_universe()
    assert u.hub.kind == HUB_KIND == "passive-storage"
    assert STATE_KIND == "as-of set"
    identity = read_port_identity()
    assert identity["hub"] == "passive-storage"
    assert identity["state_kind"] == "as-of set"
    # immutable: the hub and its as-of set are frozen dataclasses
    with pytest.raises((AttributeError, TypeError)):
        u.hub.sets = ()  # type: ignore[misc]
    with pytest.raises((AttributeError, TypeError)):
        u.as_of.records = ()  # type: ignore[misc]
    # a set fingerprint not stored is an unavailable-dependency refusal, not a live fetch
    from _fixtures import book_definition
    from qmf.core.fingerprint import fingerprint

    absent = fingerprint({"not": "in-hub"})
    missing = u.hub.get(absent.value)
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    _ = book_definition  # imported for parity with other builders; not needed further


# --- T13-203 -----------------------------------------------------------------
def test_t13_203_sweep_freezes_one_as_of_then_fingerprint_only() -> None:
    """A batch/sweep admission freezes ONE as-of; thereafter fragments resolve by
    explicit fingerprint, never by alias or name@latest. (13.2 AC4 / SC-11)"""
    u = build_universe()
    frozen = u.port.admit_batch()
    assert frozen.frozen is True
    # after admission an explicit fp1 still resolves
    by_fp = frozen.resolve(u.book_record.stable_id)
    assert is_ok(by_fp)
    assert by_fp.value.cite() == u.book_record.stable_id.value
    # ...but a human alias no longer resolves
    by_alias = frozen.resolve("scalping")
    assert is_refusal(by_alias)
    assert by_alias.category is RefusalCategory.INVALID_INPUT
    # ...and name@latest is refused
    latest = frozen.resolve("scalping@latest")
    assert is_refusal(latest)
    assert latest.category is RefusalCategory.INVALID_INPUT


# --- T13-204 -----------------------------------------------------------------
def test_t13_204_fingerprint_is_run_id_root_and_ledger_key() -> None:
    """The resolved-config fingerprint is the run-id root and the ledger key; the
    artifact is written under a run-id-named directory; all doors compute the same
    fingerprint. (13.4 AC4)"""
    from qmb.config import compile_run_config

    u = build_universe()
    config = unwrap(
        compile_run_config(
            u.port,
            book_fragment=u.book_fragment,
            bms_fragment=u.bms_fragment,
            run_spec=base_run_spec(),
            workspace_defaults=dict(DEFAULTS),
        ),
        "compile",
    )
    assert run_id_root(config) == config.fingerprint == ledger_key(config) == config.run_id
    path = config.artifact_relative_path()
    assert path.endswith("/run-config.json")
    run_dir = path.split("/")[0]
    assert ":" not in run_dir
    assert run_dir == config.fingerprint.value.replace(":", "-")
    # single-source fingerprint agreement: the API door computes the SAME fp1
    door = unwrap(
        api.compile_run_config(
            u.port,
            book_fragment=u.book_fragment,
            bms_fragment=u.bms_fragment,
            run_spec=base_run_spec(),
            workspace_defaults=dict(DEFAULTS),
        ),
        "api door compile",
    )
    assert door.fingerprint == config.fingerprint


# --- T13-205 -----------------------------------------------------------------
def test_t13_205_mints_exactly_one_world_replay_binding() -> None:
    """Each run mints exactly ONE CT-28 binding with world=replay. (13.5 AC3)"""
    from qmb.config import compile_run_config

    u = build_universe()
    config = unwrap(
        compile_run_config(
            u.port,
            book_fragment=u.book_fragment,
            bms_fragment=u.bms_fragment,
            run_spec=base_run_spec(),
            workspace_defaults=dict(DEFAULTS),
        ),
        "compile",
    )
    assert config.replay_binding is not None
    assert config.replay_binding.world is World.REPLAY
    assert config.binding_fp1 == config.replay_binding.fingerprint
    # exactly one identity: same inputs -> the same single binding
    again = unwrap(
        compile_run_config(
            u.port,
            book_fragment=u.book_fragment,
            bms_fragment=u.bms_fragment,
            run_spec=base_run_spec(),
            workspace_defaults=dict(DEFAULTS),
        ),
        "recompile",
    )
    assert again.binding_fp1 == config.binding_fp1


# --- T13-206 -----------------------------------------------------------------
def test_t13_206_starting_capital_seeds_virtual_ledger() -> None:
    """starting_capital seeds the binding's virtual ledger. (13.5 AC1)"""
    from qmb.config import compile_run_config

    u = build_universe()
    config = unwrap(
        compile_run_config(
            u.port,
            book_fragment=u.book_fragment,
            bms_fragment=u.bms_fragment,
            run_spec=base_run_spec(seed=SEED),
            workspace_defaults=dict(DEFAULTS),
        ),
        "compile",
    )
    binding = config.replay_binding
    assert binding is not None
    assert binding.virtual_ledger.seed == SEED
    assert binding.virtual_ledger.equity == SEED
    assert binding.starting_capital == SEED


# --- T13-207 (PARTIAL — seam only; runtime is Epic 14, see PLAN §7.2) ---------
def test_t13_207_ct23_ct29_seam_bound_per_run_config_PARTIAL() -> None:
    """PARTIAL: sizing/R-freeze/exit resolution consumes the CT-23 inbound and CT-29
    exit seams, bound to the run's minted world=replay binding (not ambient discovery).
    Runtime open/exit execution is Epic 14. (13.5 AC4)"""
    from qmb.execution import (
        AMBIENT_DISCOVERY,
        BOUND_FROM_RESOLVED_CONFIG,
        admit_open,
        evaluate_exit,
        mint_replay_exit,
    )

    # the seam binds from the resolved config, not from ambient discovery
    assert BOUND_FROM_RESOLVED_CONFIG is True
    assert AMBIENT_DISCOVERY is False

    # the CT-23 / CT-29 seams refuse to act without the run's minted replay binding
    no_binding_open = admit_open(
        object(),
        intent=object(),
        entry_price=object(),
        exit_logic_ref=object(),
        module=object(),
        book_resolved_requested_r=object(),
    )
    assert is_refusal(no_binding_open)
    assert no_binding_open.category is RefusalCategory.INVALID_INPUT

    no_binding_exit = evaluate_exit(object(), object())
    assert is_refusal(no_binding_exit)
    assert no_binding_exit.category is RefusalCategory.INVALID_INPUT

    no_binding_mint = mint_replay_exit(
        object(),
        virtual_position_ref=object(),
        opening_bot_id="bot",
        original_risk_distance=object(),
        original_risk_amount=object(),
        fill_references=(),
        realized_pnl=object(),
        cost_components=(),
        close_reason=object(),
        mechanism=object(),
        outcome=object(),
        closing_authority=object(),
        close_reason_mapping_version=1,
        result_label=object(),
        loss_predicate_format_version=1,
        recorded_at=object(),
    )
    assert is_refusal(no_binding_mint)
    assert no_binding_mint.category is RefusalCategory.INVALID_INPUT


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
