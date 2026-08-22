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

from collections.abc import Callable, Mapping, Sequence

from qmf.core import Fingerprint, Ok, Result, World, is_refusal
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

        When a no-peek seal is wired into this boundary the seal is consulted on **every**
        read, never a per-call argument a caller can skip (AC4; DEC-0119). A read that
        declares its knowledge position ``at`` reaching into the sealed window is a ``policy
        rejection`` at the raw-archive boundary — never a silent empty result — and a read
        that declares **no** ``at`` while a seal is wired is *also* refused (fail-closed): a
        positionless read cannot be proven outside the sealed window. With no seal wired,
        ``at`` is irrelevant and the read proceeds. A caller that needs the raw bytes to
        derive its own seal position (the split-governed research door) uses
        :meth:`read_raw_self_guarded` instead, which derives the position from the evidence.
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
        return self._read_admitted_raw(key.value)

    def read_raw_self_guarded(
        self,
        fingerprint: object,
        *,
        for_world: object,
        boundary: str,
        derive_position: Callable[[list[dict[str, object]]], Result[object]],
    ) -> Result[list[dict[str, object]]]:
        """Read raw rows and guard the no-peek seal at a position derived from them (AC4).

        A caller-facing raw read declares its seal position up front (:meth:`read_raw`). A
        boundary that cannot — the split-governed research door resolves a series only by
        reading the evidence first — composes its read here instead: this seam reads the raw
        rows, calls ``derive_position`` on them to obtain the knowledge position, and guards
        the seal at ``boundary`` against **that** position. Because the position is derived
        from the evidence and never taken as a caller argument, the seal cannot be bypassed by
        omitting one, and there is no path that returns sealed raw bytes unguarded (the
        fail-open hole a plain positionless read would leave). ``derive_position`` returns the
        knowledge position, or a refusal (a corrupt or non-series artifact) that is surfaced
        unchanged. Cross-world and stale-evidence refusals apply exactly as :meth:`read_raw`.
        """
        gate = require_same_world(self._world, for_world)
        if is_refusal(gate):
            return gate
        key = resolve_fingerprint(fingerprint)
        if is_refusal(key):
            return key
        rows = self._read_admitted_raw(key.value)
        if is_refusal(rows):
            return rows
        position = derive_position(rows.value)
        if is_refusal(position):
            return position
        sealed = guard_sealed_read(self._seal, position.value, boundary=boundary)
        if sealed is not None:
            return sealed
        return rows

    def _read_admitted_raw(self, key: Fingerprint) -> Result[list[dict[str, object]]]:
        """Read raw-archive rows for a resolved fp1 ``key``, or a store refusal.

        The seal-neutral core shared by :meth:`read_raw` and :meth:`read_raw_self_guarded`:
        a miss is a ``stale evidence`` refusal, and an engine failure is translated to a
        ``storage failure`` refusal, never raised across the seam (AC4).
        """
        digest = key.digest
        try:
            if not self._raw.has(digest):
                return missing_artifact(
                    "fingerprint",
                    "no raw-archive artifact is stored under this fingerprint",
                    given=key.value,
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

        When a no-peek seal is wired the seal is consulted on **every** read (AC4; DEC-0119):
        a read declaring a knowledge position ``at`` that reaches into the sealed window is a
        ``policy rejection`` at the processed boundary — never a silent empty result — and a
        read that declares **no** ``at`` while a seal is wired is *also* refused (fail-closed),
        since a positionless read cannot be proven outside the sealed window.
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
