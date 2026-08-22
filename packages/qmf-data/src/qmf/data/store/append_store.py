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
from qmf.data.store.refusals import invalid_input, missing_artifact, translate_engine_failure
from qmf.data.store.rooms import (
    ReadSeal,
    RoomRole,
    guard_sealed_read,
    namespace_block,
    require_same_world,
)

__all__ = ["AppendStore"]

# The CT-12 read-boundary names this store consults the injected seal at (DEC-0119). Held
# as plain strings so the dependency-free store seam never imports the ReadBoundary enum;
# they are the pinned ReadBoundary values and the seal coerces them back (M3).
_RAW_ARCHIVE_BOUNDARY = "raw archive"
_PROCESSED_BOUNDARY = "processed"


class AppendStore:
    """The CT-11 append-store for one world, over a columnar and an analytics engine."""

    def __init__(
        self,
        world: World,
        *,
        raw_engine: ColumnarEngine,
        view_engine: AnalyticsEngine,
        seal: ReadSeal | None = None,
    ) -> None:
        self._world = world
        self._raw = raw_engine
        self._views = view_engine
        self._seal = seal

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
        Parquet engine. An empty artifact (no rows) is an ``invalid input`` refusal —
        empty evidence is meaningless and would otherwise store a receipt for nothing
        (L5). A byte-identical re-write is idempotent; a true collision is refused and
        alarmed; a float/null in identity content is an ``invalid input`` refusal; an
        engine failure is a ``storage failure`` refusal (AC2, AC4).
        """
        blocked = namespace_block(self._world)
        if blocked is not None:
            return blocked
        engine = self._raw
        materialized = list(rows)
        if not materialized:
            return invalid_input(
                "rows",
                "an evidence artifact must carry at least one row; an empty artifact is "
                "refused rather than stored as evidence for nothing (L5)",
            )
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
        self, fingerprint: object, *, for_world: object, at: object | None = None
    ) -> Result[list[dict[str, object]]]:
        """Read raw-archive rows by fp1 fingerprint; a cross-world read refuses (AC5).

        ``for_world`` is required (M4). A well-formed fingerprint that no artifact is
        stored under is a ``stale evidence`` not-found refusal, not ``invalid input``
        (M5). The rows round-trip exactly and re-fingerprint to the same fp1 (H5).

        When a no-peek seal is wired into this boundary and the caller declares its read
        knowledge position ``at``, a read reaching into the sealed window is a ``policy
        rejection`` at the raw-archive boundary — never a silent empty result (AC4;
        DEC-0119). No wired seal, or no declared position, reads normally.
        """
        gate = require_same_world(self._world, for_world)
        if is_refusal(gate):
            return gate
        key = resolve_fingerprint(fingerprint)
        if is_refusal(key):
            return key
        sealed = guard_sealed_read(self._seal, at, boundary=_RAW_ARCHIVE_BOUNDARY)
        if sealed is not None:
            return sealed
        digest = key.value.digest
        try:
            if not self._raw.has(digest):
                return missing_artifact(
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
        rebuild_calendar_identity: str | None = None,
        rebuild_tzdata_version: str | None = None,
    ) -> Result[StoreReceipt]:
        """Materialize a rebuildable analytics view over ``rows`` via the DuckDB engine.

        The view is never evidence-bearing: its pinned engine major is recorded on the
        receipt so a format break costs a rebuild, never evidence (DEC-0103, DEC-0117).
        ``rebuild_calendar_identity`` and ``rebuild_tzdata_version`` are the original
        calendar identity and tzdata version a rebuild must pin; they ride onto the
        receipt verbatim so a format break replays against the exact calendar the view
        was built under (CT-11; DEC-0117, DEC-0103). Both are stdlib strings — the
        boundary never learns the ``qmf-core`` ``CalendarIdentity`` value type, so the
        engine seam stays value-neutral (the data-policy ``WorldRooms`` surface derives
        them from the calendar identity and requires them for a governed view).

        An empty view (no rows) is an ``invalid input`` refusal, symmetric with
        :meth:`append_raw`: a view of nothing carries no analytics and would otherwise mint
        a receipt for a view of nothing (L5, L11).
        """
        blocked = namespace_block(self._world)
        if blocked is not None:
            return blocked
        engine = self._views
        materialized = list(rows)
        if not materialized:
            return invalid_input(
                "rows",
                "an analytics view must materialize over at least one row; an empty view is "
                "refused rather than minting a receipt for a view of nothing (L5, L11)",
            )
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
                rebuild_calendar_identity=rebuild_calendar_identity,
                rebuild_tzdata_version=rebuild_tzdata_version,
            )
        )

    def read_view(
        self, fingerprint: object, *, for_world: object, at: object | None = None
    ) -> Result[list[dict[str, object]]]:
        """Query a materialized analytics view by fp1 fingerprint (cross-world refuses).

        ``for_world`` is required (M4). A well-formed fingerprint that no view is
        materialized under is a ``stale evidence`` not-found refusal, not
        ``invalid input`` (M5).

        When a no-peek seal is wired and the caller declares its read knowledge position
        ``at``, a read reaching into the sealed window is a ``policy rejection`` at the
        processed boundary — never a silent empty result (AC4; DEC-0119).
        """
        gate = require_same_world(self._world, for_world)
        if is_refusal(gate):
            return gate
        key = resolve_fingerprint(fingerprint)
        if is_refusal(key):
            return key
        sealed = guard_sealed_read(self._seal, at, boundary=_PROCESSED_BOUNDARY)
        if sealed is not None:
            return sealed
        digest = key.value.digest
        try:
            if not self._views.has(digest):
                return missing_artifact(
                    "fingerprint",
                    "no analytics view is materialized under this fingerprint",
                    given=key.value.value,
                )
            return Ok(self._views.query(digest))
        except StoreEngineError as exc:
            return translate_engine_failure(exc)
