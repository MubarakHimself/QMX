"""``qmf.data.store`` — the dependency-free persistence seam (COMP-QMF-DATA-STORE).

The store physically persists the seven room-roles behind four QMF-owned contracts,
each over exactly one ratified local engine, with stdlib-typed boundary signatures and
no database server (AC1; DEC-0117):

* :class:`AppendStore` (CT-11) — evidence, over **Parquet** (raw archive) and **DuckDB**
  (rebuildable views);
* :class:`JournalStore` (CT-13) — durable journals, over **JSONL** append streams;
* :class:`RegistryRoom` (CT-09) — registry records over **SQLite** and lineage edges
  over **JSONL**;
* :class:`BackupInput` (CT-26) — a verbatim, read-only store-to-backup input.

:class:`EvidenceStore` wires all four per world. Every artifact is keyed on its fp1
fingerprint (idempotent re-write silent, true collision refused and alarmed); a
``world = simulated`` write and a cross-world read are policy rejections; an engine
failure is translated to a ``storage failure`` refusal at the boundary, never raised
across a package seam (AC2, AC4, AC5). The concrete engines and their owned-contract
Protocols are exported so a caller can inject an alternate engine — each stays
swappable behind its contract.
"""

from __future__ import annotations

from qmf.core import WriteOutcome
from qmf.data.store.append_store import AppendStore
from qmf.data.store.backup_input import BackupInput, RecordExport, RoomExport
from qmf.data.store.engines import (
    AnalyticsEngine,
    AppendLocation,
    AppendStreamEngine,
    AppendStreamOpener,
    ColumnarEngine,
    MetadataEngine,
    OccurrenceSink,
    StoreEngineError,
)
from qmf.data.store.engines.duckdb_views import DuckDbAnalyticsEngine
from qmf.data.store.engines.jsonl import JsonlAppendStream, jsonl_opener
from qmf.data.store.engines.parquet import ParquetColumnarEngine
from qmf.data.store.engines.sqlite_meta import SqliteMetadataEngine
from qmf.data.store.facade import EvidenceStore, WorldStore
from qmf.data.store.identity import Admission
from qmf.data.store.journal import JournalStore
from qmf.data.store.receipts import StoreReceipt
from qmf.data.store.registry_room import RegistryRoom
from qmf.data.store.rooms import (
    EVIDENCE_BEARING_ROLES,
    ROOM_ROLE_VALUES,
    ReadSeal,
    RoomRole,
    guard_sealed_read,
)

__all__ = [
    "EVIDENCE_BEARING_ROLES",
    "ROOM_ROLE_VALUES",
    "Admission",
    "AnalyticsEngine",
    "AppendLocation",
    "AppendStore",
    "AppendStreamEngine",
    "AppendStreamOpener",
    "BackupInput",
    "ColumnarEngine",
    "DuckDbAnalyticsEngine",
    "EvidenceStore",
    "JournalStore",
    "JsonlAppendStream",
    "MetadataEngine",
    "OccurrenceSink",
    "ParquetColumnarEngine",
    "ReadSeal",
    "RecordExport",
    "RegistryRoom",
    "RoomExport",
    "RoomRole",
    "SqliteMetadataEngine",
    "StoreEngineError",
    "StoreReceipt",
    "WorldStore",
    "WriteOutcome",
    "guard_sealed_read",
    "jsonl_opener",
]
