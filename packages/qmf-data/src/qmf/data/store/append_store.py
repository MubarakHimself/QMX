"""CT-11 — the evidence-persistence append-store boundary (AC1, AC2, AC4).

The public seam through which evidence is persisted, over swappable engines with
stdlib-typed signatures. It writes two room-roles for one world:

* the **immutable raw archive** — columnar time-series evidence, physically Parquet,
  evidence-bearing and kept forever; and
* the **processed** room — rebuildable analytics views, physically DuckDB, never
  evidence-bearing, deletion licensed when no result label cites them.

Every artifact is keyed on its fp1 fingerprint: a byte-identical re-write is
idempotent (silent), a true collision is refused and alarmed (AC2). A cross-world
read is a ``policy rejection`` (AC5). Any engine failure is translated to a
``storage failure`` refusal at this boundary, never raised across the seam, and no
success is reported (AC4). The engines are injected as their owned-contract
Protocols, so each is swappable.

Stdlib + qmf-core; the engine libraries never appear in a signature here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from qmf.core import Ok, Result, World, is_refusal
from qmf.data.store.engines import AnalyticsEngine, ColumnarEngine, StoreEngineError
from qmf.data.store.identity import admit, resolve_fingerprint
from qmf.data.store.receipts import StoreReceipt
from qmf.data.store.refusals import invalid_input, translate_engine_failure
from qmf.data.store.rooms import RoomRole, namespace_block, require_same_world

__all__ = ["AppendStore"]


class AppendStore:
    """The CT-11 append-store for one world, over a columnar and an analytics engine."""

    def __init__(
        self,
        world: World,
        *,
        raw_engine: ColumnarEngine,
        view_engine: AnalyticsEngine,
    ) -> None:
        self._world = world
        self._raw = raw_engine
        self._views = view_engine

    @property
    def world(self) -> World:
        """The world whose room instances this boundary writes and reads."""
        return self._world

    # --- immutable raw archive (Parquet, evidence-bearing) ------------------

    def append_raw(
        self,
        rows: Sequence[Mapping[str, object]],
        *,
        presented_fingerprint: object | None = None,
    ) -> Result[StoreReceipt]:
        """Persist columnar time-series ``rows`` into the immutable raw archive.

        The rows are content-addressed on their fp1 fingerprint and written by the
        Parquet engine. A byte-identical re-write is idempotent; a true collision is
        refused and alarmed; a float/null in identity content is an ``invalid input``
        refusal; an engine failure is a ``storage failure`` refusal (AC2, AC4).
        """
        blocked = namespace_block(self._world)
        if blocked is not None:
            return blocked
        engine = self._raw
        materialized = list(rows)
        try:
            admission = admit(
                materialized,
                existing_bytes=engine.read_canonical,
                persist=lambda fp, canonical: engine.write(fp.digest, materialized, canonical),
                presented_fingerprint=presented_fingerprint,
            )
        except StoreEngineError as exc:
            return translate_engine_failure(exc)
        if is_refusal(admission):
            return admission
        admitted = admission.value
        return Ok(
            StoreReceipt(
                outcome=admitted.outcome,
                fingerprint=admitted.fingerprint,
                world=self._world,
                room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE,
                engine="parquet",
                is_evidence_bearing=True,
                retained_forever=True,
            )
        )

    def read_raw(
        self, fingerprint: object, *, for_world: object | None = None
    ) -> Result[list[dict[str, object]]]:
        """Read raw-archive rows by fp1 fingerprint; a cross-world read refuses (AC5)."""
        gate = require_same_world(self._world, for_world)
        if is_refusal(gate):
            return gate
        key = resolve_fingerprint(fingerprint)
        if is_refusal(key):
            return key
        digest = key.value.digest
        try:
            if not self._raw.has(digest):
                return invalid_input(
                    "fingerprint",
                    "no raw-archive artifact is stored under this fingerprint",
                    given=key.value.value,
                )
            return Ok(self._raw.read(digest))
        except StoreEngineError as exc:
            return translate_engine_failure(exc)

    # --- processed room (DuckDB, rebuildable views) -------------------------

    def materialize_view(
        self,
        rows: Sequence[Mapping[str, object]],
        *,
        presented_fingerprint: object | None = None,
    ) -> Result[StoreReceipt]:
        """Materialize a rebuildable analytics view over ``rows`` via the DuckDB engine.

        The view is never evidence-bearing: its pinned engine major is recorded on the
        receipt so a format break costs a rebuild, never evidence (DEC-0103, DEC-0117).
        """
        blocked = namespace_block(self._world)
        if blocked is not None:
            return blocked
        engine = self._views
        materialized = list(rows)
        try:
            admission = admit(
                materialized,
                existing_bytes=engine.read_canonical,
                persist=lambda fp, canonical: engine.materialize(
                    fp.digest, materialized, canonical
                ),
                presented_fingerprint=presented_fingerprint,
            )
        except StoreEngineError as exc:
            return translate_engine_failure(exc)
        if is_refusal(admission):
            return admission
        admitted = admission.value
        return Ok(
            StoreReceipt(
                outcome=admitted.outcome,
                fingerprint=admitted.fingerprint,
                world=self._world,
                room_role=RoomRole.PROCESSED,
                engine="duckdb",
                is_evidence_bearing=False,
                retained_forever=False,
                engine_major=self._views.engine_major(),
            )
        )

    def read_view(
        self, fingerprint: object, *, for_world: object | None = None
    ) -> Result[list[dict[str, object]]]:
        """Query a materialized analytics view by fp1 fingerprint (cross-world refuses)."""
        gate = require_same_world(self._world, for_world)
        if is_refusal(gate):
            return gate
        key = resolve_fingerprint(fingerprint)
        if is_refusal(key):
            return key
        digest = key.value.digest
        try:
            if not self._views.has(digest):
                return invalid_input(
                    "fingerprint",
                    "no analytics view is materialized under this fingerprint",
                    given=key.value.value,
                )
            return Ok(self._views.query(digest))
        except StoreEngineError as exc:
            return translate_engine_failure(exc)
