"""Reference usage — application-owned nightly off-machine cycle (Story 5.4).

Executable::

    python packages/qmf-data/examples/cycle_usage.py

Shows the four things Story 5.4 pins down:

1. The composition-root helper :class:`~qmf.data.OffMachineCycle` runs **one**
   CT-26 → CT-14 → sample-restore (+ optional full-restore rehearsal) cycle when
   the *application* calls :meth:`~qmf.data.OffMachineCycle.run_once` — no
   threads, cron, or daemon live in ``qmf-data``.
2. Asking QMF to own the nightly schedule or a numeric RPO/RTO is a typed
   ``policy rejection`` (FM-6, FM-9).
3. The cycle backs up every room-role including the registry room, per world; a
   cross-world / ``world = simulated`` request is a ``policy rejection``.
4. Encryption is required as a pointer; no credential enters the cycle report.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar

from qmf.core import (
    Ok,
    Result,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.data import (
    BACKUP_CADENCE,
    CYCLE_ROOM_ROLES,
    ENCRYPTION_REQUIRED,
    NODE_OPS_BACKUP_RECOVERY_POINT_OBJECTIVE,
    NODE_OPS_BACKUP_RECOVERY_TIME_OBJECTIVE,
    EvidenceStore,
    OffMachineCycle,
    StoragePutAck,
    VerifyKind,
    refuse_numeric_rpo_rto,
    refuse_schedule_ownership,
)
from qmf.data.store import RoomRole

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to succeed, got {result}")


def _require(condition: object, what: str) -> None:
    if not condition:
        raise AssertionError(f"expected {what}")


class _XorCipher:
    """Stand-in crypto adapter — real key custody is node/ops-owned (AC4)."""

    def encrypt(self, plaintext: bytes, /) -> Result[bytes]:
        return Ok(bytes(b ^ 0x5A for b in plaintext))

    def decrypt(self, ciphertext: bytes, /) -> Result[bytes]:
        return self.encrypt(ciphertext)


class _MemoryBucket:
    """Stand-in object storage — provider and credentials stay outside QMF (AC4)."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, int, str], bytes] = {}

    def put(
        self,
        *,
        world: str,
        copy_version: int,
        source_room_role: str,
        payload: bytes,
        format_version: int,
    ) -> Result[StoragePutAck]:
        del format_version
        self.objects[(world, copy_version, source_room_role)] = payload
        return Ok(StoragePutAck())

    def get(
        self,
        *,
        world: str,
        copy_version: int,
        source_room_role: str,
        format_version: int,
    ) -> Result[bytes]:
        del format_version
        return Ok(self.objects[(world, copy_version, source_room_role)])


def main() -> None:
    """Drive one application-owned nightly cycle end-to-end."""
    _require(BACKUP_CADENCE == "nightly", "design cadence pointer is nightly")
    _require(ENCRYPTION_REQUIRED is True, "encryption-required pointer is standing")
    _require(
        NODE_OPS_BACKUP_RECOVERY_POINT_OBJECTIVE is None
        and NODE_OPS_BACKUP_RECOVERY_TIME_OBJECTIVE is None,
        "numeric RPO/RTO stay null node/ops pointers",
    )
    print(
        f"cadence pointer={BACKUP_CADENCE}; encryption_required={ENCRYPTION_REQUIRED}; "
        "RPO/RTO null (node/ops-owned)"
    )

    schedule = refuse_schedule_ownership(request="install-nightly-cron")
    _require(is_refusal(schedule), "schedule ownership refuses")
    _require(
        is_refusal(schedule) and schedule.category.value == "policy rejection",
        "schedule ownership is policy rejection",
    )
    rpo = refuse_numeric_rpo_rto(target="backup_recovery_point_objective")
    _require(
        is_refusal(rpo) and rpo.category.value == "policy rejection",
        "numeric RPO ownership is policy rejection",
    )
    print("schedule / numeric RPO ask: policy rejection (primitives only)")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        store = EvidenceStore(root / "archive")
        live = _unwrap(store.for_world(World.LIVE), "live world store")
        _unwrap(
            live.append_store.append_raw([{"t": 1_700_000_000_000_000_000, "px": 42}]),
            "raw append",
        )
        writer = _unwrap(
            WriterId.try_create("node-a", "registry", "lineage", "boot-1"),
            "writer id",
        )
        _unwrap(
            live.registry_room.put_record({"kind": "producer"}, kind="producer", format_version=1),
            "registry record",
        )
        _unwrap(
            live.registry_room.append_lineage_edge("lineage", writer, {"edge": "a"}),
            "lineage edge",
        )
        jw = _unwrap(WriterId.try_create("node-a", "data", "dq", "boot-1"), "journal writer")
        _unwrap(
            live.journal.append("dq", jw, {"event_type": "data quality", "n": 0}),
            "journal append",
        )

        cycle = OffMachineCycle(_MemoryBucket(), _XorCipher())
        _require(
            is_refusal(cycle.own_schedule()) and is_refusal(cycle.start_daemon()),
            "cycle helpers refuse schedule/daemon ownership",
        )

        report = _unwrap(
            cycle.run_once(
                store=store,
                world=World.LIVE,
                sample_into=EvidenceStore(root / "sample"),
                full_into=EvidenceStore(root / "full"),
                include_full_rehearsal=True,
            ),
            "one nightly cycle",
        )
        _require(report.rooms_backed_up == CYCLE_ROOM_ROLES, "all seven room-roles backed up")
        _require(
            RoomRole.REGISTRY_ROOM in report.rooms_backed_up,
            "registry room included under one backup law",
        )
        _require(len(report.backup_receipts) == 7, "seven versioned off-machine copies")
        _require(report.encryption_required is True, "report carries encryption pointer")
        _require(
            "credential" not in report.__dataclass_fields__,
            "report embeds no credential field",
        )
        _require(
            report.sample_restore.kind is VerifyKind.SAMPLE_RESTORE,
            "sample-restore issued a recoverability claim",
        )
        full = report.full_restore
        _require(full is not None, "full-restore rehearsal ran this cycle")
        if full is None:  # narrow for type checkers; _require already guards
            raise AssertionError("expected full-restore rehearsal to run this cycle")
        _require(
            full.kind is VerifyKind.FULL_RESTORE_REHEARSAL,
            "full-restore rehearsal issued a recoverability claim",
        )
        print(
            f"cycle: rooms={len(report.rooms_backed_up)} including registry; "
            f"sample={report.sample_restore.kind.value}; "
            f"full={full.kind.value}; encrypted; no credentials"
        )

        simulated = cycle.run_once(
            store=store,
            world=World.SIMULATED,
            sample_into=EvidenceStore(root / "sim-sample"),
        )
        _require(is_refusal(simulated), "simulated world refuses")
        _require(
            is_refusal(simulated) and simulated.category.value == "policy rejection",
            "simulated is policy rejection",
        )
        print("cross-world / simulated path: policy rejection")


if __name__ == "__main__":
    main()
