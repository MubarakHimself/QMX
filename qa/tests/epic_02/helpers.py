"""Independent QA builders for the Epic 2 (qmf-registry) verification suite.

These construct valid domain objects through the PUBLIC qmf.core / qmf.registry
seams only. They are QA-side fixtures; they never import registry private helpers.
An injected clock/instant is used everywhere (never the system clock; AR-16).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar

from qmf.core import (
    Fingerprint,
    Instant,
    Result,
    World,
    WriterId,
    fingerprint,
    is_ok,
)
from qmf.data.store import EvidenceStore
from qmf.registry import (
    FieldSetKind,
    KindRegistry,
    RegistrationRecord,
    Registrar,
    RegistryPersistence,
)

T = TypeVar("T")

# A single injected instant used across the suite (never the system clock; AR-16).
_FIXED_NS = 1_700_000_000_000_000_000


def unwrap(result: Result[T], what: str = "") -> T:
    assert is_ok(result), f"{what}: expected Ok, got {result}"
    return result.value


def writer(machine: str = "node-a", role: str = "authoring",
           stream: str = "producer", boot: str = "boot-1") -> WriterId:
    return unwrap(WriterId.try_create(machine, role, stream, boot), "writer")


def instant(ns: int = _FIXED_NS) -> Instant:
    return unwrap(Instant.try_create(ns), "instant")


def fp(seed: object) -> Fingerprint:
    """A real fp1 fingerprint derived from ``seed`` (fp1-clean content)."""
    got = fingerprint({"seed": seed})
    return unwrap(got, "fp")


def record(
    body: Mapping[str, object],
    *,
    kind: str = "producer",
    version: int = 1,
    parents: list[Fingerprint] | None = None,
    writer_id: WriterId | None = None,
    sequence: int = 0,
    ns: int = _FIXED_NS,
) -> RegistrationRecord:
    return unwrap(
        RegistrationRecord.try_create(
            kind, version, parents or [], body, writer_id or writer(), sequence, instant(ns)
        ),
        "record",
    )


def field_set_registry(
    *, kind: str = "producer", required: tuple[str, ...] = (),
    optional: tuple[str, ...] = ("id", "period", "max_risk_pct", "cfg"),
    version: int = 1,
) -> KindRegistry:
    """A KindRegistry with one FieldSetKind contract registered (composition-root style)."""
    reg = KindRegistry()
    contract = unwrap(
        FieldSetKind.try_create(kind, version, required, optional), "field-set contract"
    )
    unwrap(reg.register(contract), "register contract")
    return reg


def registrar(**kw: object) -> Registrar:
    return Registrar(field_set_registry(**kw))  # type: ignore[arg-type]


def live_persistence(root: Path, world: World = World.LIVE) -> RegistryPersistence:
    store = EvidenceStore(root / "store")
    return unwrap(RegistryPersistence.open(store, world), "open persistence")
