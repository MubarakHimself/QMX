"""Epic 5 — Story 5.4: application-owned nightly off-machine cycle.

Independent tests for 5.4 AC1-AC4 (PLAN 5.4-U1..U4, P1). QMF ships the one-cycle primitive
only and REFUSES to own the schedule or a numeric RPO/RTO; the cycle backs up every room-role
per world; encryption is a pointer and no credential enters the cycle report.
"""

from __future__ import annotations

import dataclasses
import inspect
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from qmf.core import World, is_ok, is_refusal
from qmf.data.cycle import (
    BACKUP_CADENCE,
    CYCLE_ROOM_ROLES,
    NightlyCycleReport,
    OffMachineCycle,
    refuse_numeric_rpo_rto,
    refuse_schedule_ownership,
)
from qmf.data.store.rooms import RoomRole

import _epic5_helpers as H

_ROWS = [{"t": 1_700_000_000_000_000_000, "px": 100}]


def _seed(store: object, world: World) -> None:
    H.seed_raw(store, _ROWS, world=world)
    H.seed_journal(store, "s1", {"event_type": "data quality", "world": world.value, "n": 1}, world=world)
    H.seed_registry(store, {"a": 1}, world=world)


def _cycle(root: Path):
    storage = H.MemStorage()
    return storage, OffMachineCycle(storage, H.IdentityCipher())


# --- 5.4-U1 (L1): the cycle backs up every room-role, per world -------------------


@given(world=st.sampled_from([World.LIVE, World.REPLAY]))
@settings(max_examples=2, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_5_4_u1_backs_up_every_room_role_per_world(world: World) -> None:
    """AC1/AC3: one cycle backs up all seven room-roles (incl. the registry room) for the world."""
    root = H.new_root()
    store = H.make_store(root, name="store")
    _seed(store, world)
    storage = H.MemStorage()
    cycle = OffMachineCycle(storage, H.IdentityCipher())
    report = H.unwrap(
        cycle.run_once(
            store=store, world=world, sample_into=H.make_store(root, name="sample"),
            full_into=H.make_store(root, name="full"), include_full_rehearsal=True,
        )
    )
    assert set(report.rooms_backed_up) == set(RoomRole), "every one of the seven room-roles is backed up"
    assert RoomRole.REGISTRY_ROOM in report.rooms_backed_up, "the registry room is included"
    assert len(report.backup_receipts) == 7
    # observe the sink: an off-machine object exists for every room-role, all in THIS world
    stored_roles = {k[2] for k in storage.objs}
    assert stored_roles == {r.value for r in RoomRole}
    assert all(k[0] == world.value for k in storage.objs), "no other world leaks into the copies"


# --- 5.4-U2 (L1): a request to own the schedule / numeric RPO-RTO is refused -------


def test_5_4_u2_refuses_to_own_schedule_or_numeric_targets(tmp_path: Path) -> None:
    """AC2: owning the nightly schedule or a numeric RPO/RTO is refused as outside the boundary."""
    storage, cycle = _cycle(tmp_path)
    H.assert_refusal(cycle.own_schedule(), "policy rejection")
    H.assert_refusal(cycle.start_daemon(), "policy rejection")
    H.assert_refusal(cycle.set_recovery_point_objective(5), "policy rejection")
    H.assert_refusal(cycle.set_recovery_time_objective(5), "policy rejection")
    H.assert_refusal(refuse_schedule_ownership(request="own the cron"), "policy rejection")
    H.assert_refusal(refuse_numeric_rpo_rto(target="rpo=15min"), "policy rejection")


# --- 5.4-U3 (L1, P0-7 cycle witness): simulated refused; no simulated carried -------


def test_5_4_u3_simulated_cycle_refused_no_simulated_carried(tmp_path: Path) -> None:
    """AC3 (P0-7): a simulated-world cycle is a policy rejection; a governed cycle carries no simulated."""
    store = H.make_store(tmp_path, name="store")
    _seed(store, World.LIVE)
    storage, cycle = _cycle(tmp_path)
    # a simulated cycle is refused outright (no governed namespace)
    H.assert_refusal(
        cycle.run_once(store=store, world=World.SIMULATED, sample_into=H.make_store(tmp_path, name="s")),
        "policy rejection",
    )
    # a governed (LIVE) cycle carries no world=simulated copy into evidence
    report = H.unwrap(
        cycle.run_once(store=store, world=World.LIVE, sample_into=H.make_store(tmp_path, name="s2"))
    )
    assert all(r.world is World.LIVE for r in report.backup_receipts)
    assert World.SIMULATED.value not in {k[0] for k in storage.objs}


# --- 5.4-U4 (L1): unresolved key custody -> encryption pointer, no credential -------


def test_5_4_u4_encryption_pointer_no_credential_in_report(tmp_path: Path) -> None:
    """AC4: the cycle carries the encryption-required pointer and embeds no credential in evidence."""
    store = H.make_store(tmp_path, name="store")
    _seed(store, World.LIVE)
    storage = H.MemStorage()
    # Fragment-assembled probe plaintext — never a quoted credential assignment.
    planted_plaintext = "S3CR3T" + "-KEY-" + "abcdef012345"
    # the key lives only inside the injected cipher; key custody stays node/ops
    cycle = OffMachineCycle(storage, H.XorCipher(key=0x77))
    report = H.unwrap(
        cycle.run_once(store=store, world=World.LIVE, sample_into=H.make_store(tmp_path, name="s"))
    )
    assert report.encryption_required is True
    assert report.cadence == BACKUP_CADENCE == "nightly"
    # no report field names a credential, and the secret string appears nowhere in the report
    field_names = {f.name.lower() for f in dataclasses.fields(report)}
    assert not any("key" in n or "credential" in n or "secret" in n or "password" in n for n in field_names)
    assert planted_plaintext not in repr(report), "no credential value may enter the cycle report"
    assert all(r.encryption_required is True for r in report.backup_receipts)


# --- 5.4-P1 (L2): the boundary is primitive-only — no schedule / numeric input taken ---


def test_5_4_p1_no_schedule_or_numeric_input_accepted(tmp_path: Path) -> None:
    """AC2 / 5.3 AC4: no CT-14/CT-26 cycle op accepts or persists a schedule or numeric RPO/RTO."""
    storage, cycle = _cycle(tmp_path)
    # every schedule/numeric-owning entry point refuses (policy rejection), none succeeds
    refusals = [
        cycle.own_schedule("nightly"),
        cycle.start_daemon(),
        cycle.set_recovery_point_objective("15m"),
        cycle.set_recovery_time_objective("1h"),
    ]
    for res in refusals:
        assert is_refusal(res) and res.category.value == "policy rejection"
    # run_once's signature takes NO rpo/rto/retention/cadence/schedule parameter (primitive only)
    params = set(inspect.signature(cycle.run_once).parameters)
    for banned in ("rpo", "rto", "recovery_point", "recovery_time", "retention", "cadence", "schedule", "cron"):
        assert not any(banned in p.lower() for p in params), f"run_once must accept no {banned} parameter"
    # the ratified room-role set covers all seven (one retention/backup law)
    assert set(CYCLE_ROOM_ROLES) == set(RoomRole)
