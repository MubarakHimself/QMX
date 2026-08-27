"""Independent test helpers for the Epic 5 (qmf-data backup/restore/verify) lane.

Fakes, builders, and CT-04 refusal utilities used across the epic_05 suite. Every
fake here is owned by the TEST and observed independently: the object-storage doubles
record what crosses the CT-14 boundary, the ciphers transform bytes so ciphertext can
be distinguished from plaintext, and the fault doubles raise REAL third-party
exception types (ConnectionError / OSError / TimeoutError) or the store engines' own
normalized StoreEngineError at the true seam. Refusal assertions check the CT-04
``category`` value, never a parsed message string. Nothing here edits or weakens a
production assertion; a failing planned test is a FINDING.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from qmf.core import (
    CalendarIdentity,
    CivilDate,
    Instant,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TradingDate,
    TypedRefusal,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.data.backup import StoragePutAck
from qmf.data.seal import HoldoutSeal
from qmf.data.splits import SplitBoundary
from qmf.data.store import EvidenceStore
from qmf.data.store.backup_input import RecordExport, RoomExport
from qmf.data.store.engines import StoreEngineError
from qmf.data.store.rooms import RoomRole


# --- result / refusal harness (CT-04 category, never a parsed string) --------


def unwrap(result: object) -> object:
    """Assert ``result`` is Ok and return its value, with a helpful message on refusal."""
    if is_refusal(result):
        raise AssertionError(
            f"expected Ok, got refusal category={result.category.value!r} context={result.context!r}"
        )
    assert is_ok(result), f"expected Ok, got {result!r}"
    return result.value


def assert_refusal(result: object, category: str | None = None) -> object:
    """Assert ``result`` is a typed refusal (optionally of ``category``); return it."""
    if is_ok(result):
        raise AssertionError(f"expected a typed refusal, got Ok({result.value!r})")
    assert is_refusal(result), f"expected a typed refusal, got {result!r}"
    if category is not None:
        assert result.category.value == category, (
            f"expected refusal category {category!r}, got {result.category.value!r}; "
            f"context={result.context!r}"
        )
    return result


def new_root() -> Path:
    """A fresh temp directory root (fresh per call so property examples never bleed)."""
    return Path(tempfile.mkdtemp())


# --- ciphers (the injected PayloadCipher port) -------------------------------


class IdentityCipher:
    """A no-op cipher: the framed plaintext passes through so round-trips are exact."""

    def encrypt(self, plaintext: bytes, /) -> Result[bytes]:
        return Ok(plaintext)

    def decrypt(self, ciphertext: bytes, /) -> Result[bytes]:
        return Ok(ciphertext)


class XorCipher:
    """An invertible transform so ciphertext != plaintext — proves the payload is the
    cipher's OUTPUT, not the raw store plaintext (5.1-U4)."""

    def __init__(self, key: int = 0x5A) -> None:
        self._key = key

    def _xor(self, data: bytes) -> bytes:
        return bytes(b ^ self._key for b in data)

    def encrypt(self, plaintext: bytes, /) -> Result[bytes]:
        return Ok(self._xor(plaintext))

    def decrypt(self, ciphertext: bytes, /) -> Result[bytes]:
        return Ok(self._xor(ciphertext))


class RaisingCipher:
    """A cipher whose encrypt/decrypt raise a REAL exception (crypto adapter fault)."""

    def __init__(self, exc: BaseException | None = None) -> None:
        self._exc = exc if exc is not None else RuntimeError("cipher backend crashed")

    def encrypt(self, plaintext: bytes, /) -> Result[bytes]:
        raise self._exc

    def decrypt(self, ciphertext: bytes, /) -> Result[bytes]:
        raise self._exc


class RefusingCipher:
    """A cipher that RETURNS a typed refusal (e.g., a missing key) rather than raising."""

    def __init__(self, category: RefusalCategory = RefusalCategory.STORAGE_FAILURE) -> None:
        self._category = category

    def _refuse(self) -> TypedRefusal:
        return TypedRefusal(
            category=self._category,
            retryability=Retryability.NO,
            context={"field": "cipher", "reason": "encryption key unavailable"},
        )

    def encrypt(self, plaintext: bytes, /) -> Result[bytes]:
        return self._refuse()

    def decrypt(self, ciphertext: bytes, /) -> Result[bytes]:
        return self._refuse()


# --- object storage (the injected ObjectStorage port) ------------------------


def _key(world: object, copy_version: int, source_room_role: object) -> tuple[str, int, str]:
    w = world.value if isinstance(world, World) else str(world)
    r = source_room_role.value if isinstance(source_room_role, RoomRole) else str(source_room_role)
    return (w, copy_version, r)


class MemStorage:
    """An in-memory object-storage double; records every put so a test observes the
    bytes that crossed CT-14. put/get succeed by default."""

    def __init__(self) -> None:
        self.objs: dict[tuple[str, int, str], bytes] = {}
        self.put_calls: list[tuple[tuple[str, int, str], bytes]] = []

    def put(
        self, *, world: str, copy_version: int, source_room_role: str, payload: bytes,
        format_version: int,
    ) -> Result[StoragePutAck]:
        k = _key(world, copy_version, source_room_role)
        self.objs[k] = payload
        self.put_calls.append((k, payload))
        return Ok(StoragePutAck())

    def get(
        self, *, world: str, copy_version: int, source_room_role: str, format_version: int
    ) -> Result[bytes]:
        return Ok(self.objs[_key(world, copy_version, source_room_role)])


class UnreachableStorage(MemStorage):
    """An unreachable bucket: put/get raise a REAL ConnectionError (never a refusal)."""

    def put(self, **kw: object) -> Result[StoragePutAck]:
        raise ConnectionError("bucket unreachable")

    def get(self, **kw: object) -> Result[bytes]:
        raise ConnectionError("bucket unreachable")


class OSErrorStorage(MemStorage):
    """A transport interrupted mid-flight: put/get raise a REAL OSError."""

    def put(self, **kw: object) -> Result[StoragePutAck]:
        raise OSError("connection reset during upload")

    def get(self, **kw: object) -> Result[bytes]:
        raise OSError("connection reset during download")


class TimeoutStorage(MemStorage):
    """A stalled transfer: put/get raise a REAL TimeoutError."""

    def put(self, **kw: object) -> Result[StoragePutAck]:
        raise TimeoutError("upload timed out")

    def get(self, **kw: object) -> Result[bytes]:
        raise TimeoutError("download timed out")


class RejectingStorage(MemStorage):
    """A bucket that REJECTS the upload/download with a storage-failure refusal."""

    def put(self, **kw: object) -> Result[StoragePutAck]:
        return TypedRefusal(
            category=RefusalCategory.STORAGE_FAILURE,
            retryability=Retryability.YES,
            context={"field": "object-storage", "reason": "upload rejected"},
        )

    def get(self, **kw: object) -> Result[bytes]:
        return TypedRefusal(
            category=RefusalCategory.STORAGE_FAILURE,
            retryability=Retryability.YES,
            context={"field": "object-storage", "reason": "download rejected"},
        )


class WrongCategoryStorage(MemStorage):
    """A miswired adapter that returns a NON-storage-failure refusal; the CT-14 boundary
    must remap it to `storage failure` (backup.py AC4 remap)."""

    def put(self, **kw: object) -> Result[StoragePutAck]:
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={"field": "adapter", "reason": "miswired category"},
        )

    def get(self, **kw: object) -> Result[bytes]:
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={"field": "adapter", "reason": "miswired category"},
        )


class CorruptStorage(MemStorage):
    """A bucket that returns a corrupted (frame-broken) object on get."""

    def get(self, **kw: object) -> Result[bytes]:
        return Ok(b"\x00corrupt-not-a-backup-envelope\x00")


class EmptyStorage(MemStorage):
    """A bucket that returns an empty object on get (a vanished / missing copy)."""

    def get(self, **kw: object) -> Result[bytes]:
        return Ok(b"")


class TruncatingStorage(MemStorage):
    """A bucket that returns a truncated (partial) copy on get."""

    def get(self, *, world: str, copy_version: int, source_room_role: str, format_version: int) -> Result[bytes]:
        full = self.objs[_key(world, copy_version, source_room_role)]
        return Ok(full[: max(1, len(full) // 2)])


# --- CT-26 engine-seam fault doubles (StoreEngineError == the engines' contract) --


class RaisingColumnar:
    """A ColumnarEngine whose reads raise the store's normalized StoreEngineError —
    exactly what a concrete Parquet engine raises after wrapping a real pyarrow/OSError."""

    def __init__(self, *, retryable: bool = True) -> None:
        self._retryable = retryable

    def stored_keys(self) -> list[str]:
        raise StoreEngineError(
            "raw archive is locked" if self._retryable else "raw archive is corrupt",
            engine="parquet", retryable=self._retryable, detail={"path": "immutable-raw-archive"},
        )

    def read_canonical(self, key: str, /) -> bytes | None:
        raise StoreEngineError("read_canonical failed", engine="parquet", retryable=self._retryable)

    def write(self, key: str, rows: object, canonical: bytes, /) -> None:  # pragma: no cover
        raise StoreEngineError("write failed", engine="parquet", retryable=self._retryable)

    def read(self, key: str, /) -> list[dict[str, object]]:  # pragma: no cover
        raise StoreEngineError("read failed", engine="parquet", retryable=self._retryable)

    def has(self, key: str, /) -> bool:  # pragma: no cover
        raise StoreEngineError("has failed", engine="parquet", retryable=self._retryable)


class RaisingMetadata:
    """A MetadataEngine whose reads raise StoreEngineError (a corrupt SQLite store)."""

    def __init__(self, *, retryable: bool = False) -> None:
        self._retryable = retryable

    def digests(self) -> list[str]:
        raise StoreEngineError(
            "registry records store is corrupt", engine="sqlite",
            retryable=self._retryable, detail={"path": "records.sqlite"},
        )

    def get(self, digest: str, /) -> bytes | None:
        raise StoreEngineError("get failed", engine="sqlite", retryable=self._retryable)

    def put(self, digest: str, canonical: bytes, /, *, kind: str, format_version: int) -> None:  # pragma: no cover
        raise StoreEngineError("put failed", engine="sqlite", retryable=self._retryable)

    def meta(self, digest: str, /) -> object:  # pragma: no cover
        raise StoreEngineError("meta failed", engine="sqlite", retryable=self._retryable)


def _noop_opener(stream_dir: object, writer_token: str, /) -> object:  # pragma: no cover
    """A stream opener that is never reached in the raw/registry engine-fault tests."""
    raise StoreEngineError("stream opener unused", engine="jsonl", retryable=False)


# --- core value builders -----------------------------------------------------


def cal(version: str = "v3", tzdata: str = "2025a") -> CalendarIdentity:
    return unwrap(CalendarIdentity.try_create("forex-17NY", version, tzdata))


def civil(year: int, month: int, day: int) -> CivilDate:
    return unwrap(CivilDate.try_create(year, month, day))


def instant(value_ns: int) -> Instant:
    return unwrap(Instant.try_create(value_ns))


def instant_boundary(value_ns: int) -> SplitBoundary:
    return unwrap(SplitBoundary.try_create(instant(value_ns)))


def instant_seal(
    *, world: World = World.LIVE, seal_ns: int = 1_000_000, months: int = 12,
) -> HoldoutSeal:
    """A HoldoutSeal whose frozen boundary is an Instant, so integer read positions
    compare cleanly against it (no cross-kind refusal)."""
    return unwrap(
        HoldoutSeal.try_create(
            seal_boundary=instant_boundary(seal_ns),
            calendar_identity=cal(),
            world=world,
            holdout_months=months,
        )
    )


def writer(
    machine: str = "node-a", role: str = "data", stream: str = "s1", boot: str = "boot-1"
) -> WriterId:
    return unwrap(WriterId.try_create(machine, role, stream, boot))


# --- store builders + seeding ------------------------------------------------


def make_store(root: Path, *, name: str = "store", seal: object | None = None) -> EvidenceStore:
    return EvidenceStore(root / name, seal=seal)


def world_store(store: EvidenceStore, world: World = World.LIVE) -> object:
    return unwrap(store.for_world(world))


def seed_raw(store: EvidenceStore, rows: list[dict[str, object]], *, world: World = World.LIVE) -> object:
    """Append one raw-archive artifact; return its StoreReceipt."""
    return unwrap(world_store(store, world).append_store.append_raw(rows))


def seed_journal(
    store: EvidenceStore, stream: str, event: dict[str, object], *, world: World = World.LIVE
) -> object:
    return unwrap(world_store(store, world).journal.append(stream, writer(stream=stream), event))


def seed_registry(
    store: EvidenceStore, body: dict[str, object], *, kind: str = "k", fmt: int = 1,
    world: World = World.LIVE,
) -> object:
    return unwrap(world_store(store, world).registry_room.put_record(body, kind=kind, format_version=fmt))


def read_room(
    store: EvidenceStore, role: RoomRole, *, world: World = World.LIVE, at: object | None = None
) -> object:
    """Read a CT-26 export (returns the Result — Ok or refusal)."""
    return world_store(store, world).backup_input.read_room(role, for_world=world, at=at)


def export_of(
    store: EvidenceStore, role: RoomRole, *, world: World = World.LIVE, at: object | None = None
) -> RoomExport:
    return unwrap(read_room(store, role, world=world, at=at))


# --- independent record-set comparison (test-owned, not the impl's _exports_match) --


def record_keyset(export: RoomExport) -> frozenset[tuple[str, bytes, str | None]]:
    """The (fingerprint, canonical-bytes, stream) identity set of an export's records."""
    return frozenset((r.fingerprint, r.canonical, r.stream) for r in export.records)


def exports_identical(a: RoomExport, b: RoomExport) -> bool:
    """Byte/fingerprint-identical round-trip check, observed by the TEST."""
    return (
        a.world is b.world
        and a.source_room_role is b.source_room_role
        and a.record_count == b.record_count
        and record_keyset(a) == record_keyset(b)
    )
