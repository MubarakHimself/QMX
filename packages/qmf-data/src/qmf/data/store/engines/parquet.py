"""Parquet columnar time-series engine — the evidence-bearing raw archive (AC1).

The concrete :class:`~qmf.data.store.engines.ColumnarEngine`. A columnar artifact —
an ordered set of JSON-native rows — is written as one content-addressed Parquet
file, ``<fp1-digest>.parquet``, via a temp-file + atomic-rename so a torn write never
leaves a half file under a real key. The exact fp1 canonical bytes are embedded in
the Parquet **schema metadata** and are the artifact's authoritative, evidence-bearing
form: :meth:`read` decodes those canonical bytes, so the raw archive round-trips
**exactly** — heterogeneous row schemas are not unified into a common column with
``None`` backfilled, and an arbitrary-precision integer (qmf-core canonicalizes big
ints by design — the money path) survives rather than overflowing an inferred int64
column, so a read-back always re-fingerprints to the same fp1 (H4, H5; DEC-0108). The
columnar table stores each row's canonical JSON as a string column, so pyarrow never
infers a numeric column a big int could overflow; a corrupt/truncated file surfaces as
a ``storage failure`` rather than a silent wrong answer.

Parquet (pyarrow) is a store engine declared only in qmf-data's pyproject; it never
appears in a boundary signature. Every pyarrow / ``OSError`` failure is wrapped into
the one :class:`~qmf.data.store.engines.StoreEngineError` so the boundary translates
it without importing a pyarrow exception type (AC4).

pyarrow ships no type stubs; the four unknown-type rules are disabled at file scope
here — the one module that touches the untyped columnar library — so the rest of the
package stays strictly typed.
"""

# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

import pyarrow as pa
import pyarrow.parquet as pq
from qmf.data.store.engines import StoreEngineError

__all__ = ["ParquetColumnarEngine"]

_SUFFIX = ".parquet"
_CANONICAL_KEY = b"qmf_fp1_canonical"
_ROW_COLUMN = "qmf_row"


class ParquetColumnarEngine:
    """Content-addressed Parquet storage for columnar time-series evidence.

    Bound to one room directory; each artifact is ``<digest>.parquet``. The engine
    owns physical persistence only — identity, world routing, and idempotency live in
    the boundary and the guard.
    """

    def __init__(self, room_dir: Path) -> None:
        self._dir = room_dir

    def _path(self, key: str) -> Path:
        return self._dir / f"{key}{_SUFFIX}"

    def write(self, key: str, rows: Sequence[Mapping[str, object]], canonical: bytes, /) -> None:
        """Write ``rows`` to ``<key>.parquet`` with ``canonical`` embedded (raises).

        The authoritative artifact is the ``canonical`` bytes embedded in the schema
        metadata; the columnar table stores each row's canonical JSON as a **string**,
        so pyarrow never infers a numeric column an arbitrary-precision int could
        overflow, and a heterogeneous row schema is never unified with ``None``
        backfilled (H4, H5). A serialization or overflow error at this boundary is
        translated to a ``storage failure`` rather than crossing the seam (AC4).
        """
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            # The canonical bytes ARE the list of rows in canonical JSON; decode once
            # to store each row as a JSON string (JSON-native by construction, since
            # canonical_bytes produced it — no big-int overflow, no schema unification).
            decoded = cast("list[object]", json.loads(canonical))
            payloads = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in decoded]
            column = pa.array(payloads, type=pa.string())
            table = pa.table({_ROW_COLUMN: column})
            table = table.replace_schema_metadata({_CANONICAL_KEY: canonical})
            target = self._path(key)
            tmp = target.with_suffix(_SUFFIX + ".tmp")
            pq.write_table(table, str(tmp))
            os.replace(tmp, target)
        except (OSError, pa.ArrowException, ValueError, TypeError, OverflowError) as exc:
            raise StoreEngineError(
                "could not write the Parquet columnar artifact",
                engine="parquet",
                detail={"key": key, "error": str(exc)},
            ) from exc

    def read(self, key: str, /) -> list[dict[str, object]]:
        """Read the rows stored under ``key`` (raises if absent or corrupt).

        Decodes the embedded fp1 canonical bytes — the authoritative, lossless form —
        so the read-back is byte-for-byte the stored artifact and re-fingerprints to
        the same fp1 (H5; DEC-0108). A missing or corrupt file, or metadata that no
        longer carries the canonical bytes, is a ``storage failure``.
        """
        canonical = self.read_canonical(key)
        if canonical is None:
            raise StoreEngineError(
                "could not read the Parquet columnar artifact (missing or missing its "
                "canonical identity bytes)",
                engine="parquet",
                retryable=False,
                detail={"key": key},
            )
        try:
            decoded = json.loads(canonical)
        except ValueError as exc:
            raise StoreEngineError(
                "the Parquet columnar artifact carries corrupt canonical bytes",
                engine="parquet",
                retryable=False,
                detail={"key": key, "error": str(exc)},
            ) from exc
        return cast("list[dict[str, object]]", decoded)

    def read_canonical(self, key: str, /) -> bytes | None:
        """The embedded fp1 canonical bytes for ``key``, or ``None`` if absent."""
        path = self._path(key)
        if not path.is_file():
            return None
        try:
            schema = pq.read_schema(str(path))
        except (OSError, pa.ArrowException) as exc:
            raise StoreEngineError(
                "could not read the Parquet schema (locked or corrupt)",
                engine="parquet",
                retryable=False,
                detail={"key": key, "error": str(exc)},
            ) from exc
        metadata = cast("dict[bytes, bytes] | None", schema.metadata)
        if metadata is None:
            return None
        return metadata.get(_CANONICAL_KEY)

    def has(self, key: str, /) -> bool:
        """Whether ``<key>.parquet`` exists."""
        return self._path(key).is_file()

    def stored_keys(self) -> list[str]:
        """Every stored artifact key (the rebuildable content index)."""
        if not self._dir.is_dir():
            return []
        return sorted(p.name[: -len(_SUFFIX)] for p in self._dir.glob(f"*{_SUFFIX}"))
