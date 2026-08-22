# qmf-data — failure register

Failure-register entries for `qmf-data`, per the workspace convention
(`conventions/failure-register.md`, NFR-11). One entry per designed failure mode,
written for someone who was not in the design room. Story 3.1 delivers the store
seam (`COMP-QMF-DATA-STORE`), FR-1 through FR-10; Story 3.2 delivers the CT-10
source-observation boundary, FR-11 through FR-14; Story 3.3 delivers the seven
room-roles per world (`WorldRooms`), the rebuildable-view rebuild pins, the
`(source, instrument, time-window)` series partition, and the keep-forever-vs-
deletion-licensed retention law, FR-15 through FR-17. Story 3.4 delivers the CT-12
dataset splits and the 12-month no-peek seal (`SplitManifest`, `HoldoutSeal`), FR-18
through FR-25. A CT-10 write that reaches storage inherits the store seam's
storage-failure translation (FR-1) and true-fp1-collision alarm (FR-2) unchanged —
the boundary funnels every observation write through the same `append_raw` seam, so
those two entries cover observation persistence too and are not restated below.
Story 3.3's `WorldRooms` operations likewise ride the same store seam, so a
`world = simulated` write (FR-4), a cross-world read (FR-5), and a storage-engine
failure (FR-1) are inherited unchanged for its rebuildable views and series placement
and are not restated below. Story 3.4's one authorized final look is written through
the CT-13 `JournalStore`, so an unpersistable final-look write inherits the store
seam's storage-failure translation (FR-1) and the one-writer discipline (FR-6)
unchanged, and they are not restated below. Story 3.5 delivers the durable journal
data-policy — the seven event types, the gapless per-writer sequence, the decision
outcome, the typed causal edge, and the `JournalWriter` producer — FR-26 through FR-31.
Its `JournalWriter` appends through the same CT-13 `JournalStore`, so a `world =
simulated` write (FR-4), a cross-world read (FR-5), a second distinct writer on a held
stream (FR-6), a true fp1 collision (FR-2), and the raw storage-failure translation
(FR-1) are inherited unchanged; FR-26 and FR-27 below build the block-on-unpersistable
*command-stream* discipline on top of that translation, which the store seam alone does
not provide. Story 3.6 delivers the CT-25 read-time entity-journal projections
(logbooks) — the Book/BMS/per-bot journals, the command-fingerprint join, the
role-scoped namespaces, and the legacy-five-stream mapping table — FR-32 through FR-36.
Story 3.6 is **read-only**: it resolves projections over the already-recorded streams and
writes nothing, so it introduces no new persistence failure and inherits no store-seam
entry; its designed failures are the value-level refusals a projection returns. Two later
entries, FR-37 and FR-38, are code-review amendments appended out of story order: FR-37
amends Story 3.3's retention law (the citation index fails closed) and FR-38 amends Story
3.4's dataset splits (the purge width is applied at partition time).

### FR-1: A store-engine failure is translated to a storage-failure refusal (AC4)

- **Failure class:** `storage failure` (a CT-04 refusal category).
- **Detection:** every engine (Parquet, DuckDB, SQLite, JSONL) wraps its library's
  exception — an `OSError` (disk full, locked, truncated), a `pyarrow` / `duckdb` /
  `sqlite3` error, a short read below the index-recorded length, a partial JSONL line
  **before the stream tail** — into one normalized `StoreEngineError`. Each of the four
  boundaries (CT-11 `AppendStore`, CT-13 `JournalStore`, CT-09 `RegistryRoom`, CT-26
  `BackupInput`) catches `StoreEngineError` at the seam and calls
  `translate_engine_failure`, returning a `storage failure` typed refusal. The
  exception is **never** propagated across the package boundary, and persistence
  success is never reported on failure.
- **Torn-tail recovery (the one exception to "any partial JSONL line is a failure").**
  A crash mid-append can leave the **last** line of the last rotation file without its
  LF terminator (the write's fsync never completed). This is a normal write-ahead-log
  tail, not corruption: on index rebuild the JSONL engine **quarantines** the torn tail
  to a `<ordinal>.jsonl.torn` sidecar (kept for evidence) and truncates the data file to
  the durable committed prefix, so every LF-terminated line before it stays readable and
  appendable. `read_stream`, `append`, AND `BackupInput.read_room` therefore all resume
  over the committed prefix rather than refusing forever. A torn (no-LF) line **anywhere
  but the tail** — in an earlier rotation file, which is only left behind once complete —
  is genuine corruption and stays a `storage failure` refusal (retryability `no`).
- **Auto-recovery / retry:** none automatic. A transient outage (a locked file, a
  disk that may free up) is `retryability = yes`; a corrupt or truncated store is
  `retryability = no`. The caller retries the same write once the condition clears
  (the block-on-unpersistable discipline; the same shape a `JournalSink` returns).
- **Visible degraded state:** the write did not land; a writer holding a stream must
  block its command stream until the store recovers rather than proceed on an
  unrecorded event. No half-written artifact is reported as stored.
- **Notification tier:** operator-visible (escalating to alarm on a prolonged
  outage). Durable storage being unavailable is an operational condition.
- **Product-user affordance:** an action could not be recorded because storage was
  unavailable or a file was corrupt, so the platform paused rather than pretending it
  saved. The refusal's `context` names the failing `engine` and detail. Once storage
  is restored the paused write is retried and, on success, the stream resumes.

### FR-2: A true fp1 collision on a store write is refused and alarmed (AC2)

- **Failure class:** `policy rejection` (a CT-04 refusal category), carrying
  `alarm: true`.
- **Detection:** the store keys every artifact on its `fp1:sha256:<hex>` fingerprint
  and admits a write through the shared identity guard (`admit`), which recomputes the
  fingerprint of the presented bytes and reconciles against the bytes already stored
  under that fingerprint via `qmf.core.reconcile_write`. A first write is `stored`; a
  byte-identical re-write is `idempotent`; the **same hash addressing differing
  bytes** is a true collision.
- **Auto-recovery / retry:** none, and the stored bytes are **never overwritten**. The
  collision returns a `policy rejection` (retryability `no`) whose `context` names the
  fingerprint and sets the alarm.
- **Visible degraded state:** none — the prior evidence is preserved untouched; the
  colliding write is rejected.
- **Notification tier:** alarm. A true collision is an identity-integrity event, not a
  routine input mistake.
- **Product-user affordance:** nothing an end user did caused this; two different byte
  sequences claimed one fingerprint. The write is refused and the original evidence is
  kept; an operator investigates the source that produced the colliding artifact.

### FR-3: A presented fingerprint that does not match the bytes is refused (AC2)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** when a caller presents a fingerprint alongside the content (a record
  that already carries its fp1), `admit` recomputes the fingerprint from the presented
  bytes **before storing** and refuses a mismatch — so admitting bytes under the wrong
  fingerprint can never masquerade as a collision.
- **Auto-recovery / retry:** none automatic; the refusal names the `given` and the
  `computed` fingerprint. Fix the pairing and retry.
- **Visible degraded state:** none; nothing is stored.
- **Notification tier:** silent-log. A wiring mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a component
  presented a record whose declared fingerprint did not match its bytes. Recompute the
  fingerprint from the exact bytes and retry.

### FR-4: A `world = simulated` write is a policy rejection (AC5)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `world = simulated` has no governed namespace in V1. Requesting a
  simulated `WorldStore` from `EvidenceStore.for_world` is refused, and each boundary
  additionally gates a write through `namespace_block` (via
  `qmf.core.governed_namespace`) before touching any engine. The CT-13 `JournalStore`
  additionally routes on the **event's own declared world** (`require_write_world`): a
  journal event whose `world` differs from the room's — a `simulated` or `replay` event
  reaching a `live` journal room — is a `policy rejection` and never lands, so world
  isolation holds on the event itself, not just on the store's own world (DEC-0110,
  DEC-0117). An event that declares no world inherits the room's world (the
  `JournalWriter` always stamps it).
- **Auto-recovery / retry:** none automatic; the refusal cites `GAP-0048`. Produce
  evidence in a supported world (`live` or `replay`).
- **Visible degraded state:** none; no bytes are written.
- **Notification tier:** silent-log. Attempting a reserved-unusable world is a policy
  mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime; a component tried to write
  synthetic-world evidence, which V1 does not admit into governed storage. Use a
  supported world.

### FR-5: A cross-world read is a policy rejection (AC5)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** a store boundary is bound to exactly one world's room instance, and the
  caller must **declare** the world it is reading as — `for_world` is a required argument
  on every read boundary (`read_raw`, `read_view`, `read_stream`, `get_record`,
  `read_lineage`, `read_room`), with no implicit same-world default, so the guard always
  evaluates and an accidental cross-world read can never slip through unchecked. A read
  naming a different world than the room's is refused by `require_same_world`; a missing
  declaration (`None`) is an `invalid input` refusal. World isolation is storage
  separation — one world's room never serves another's evidence.
- **Auto-recovery / retry:** none automatic; the refusal names the `requested` and the
  `room_world`. Read from the caller's own world (declare it explicitly).
- **Visible degraded state:** none; no evidence is returned.
- **Notification tier:** silent-log.
- **Product-user affordance:** nothing failed; a component asked one world's store for
  another world's evidence, or forgot to declare which world it is reading. Declare the
  correct world and read from that world's store.

### FR-6: A second writer on a held stream does not proceed (AC3)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** each JSONL append stream (journal, lineage edges) is held by exactly
  one writer — the hold identity is `(machine, role, acquired-stream)`, where the stream
  part is the stream actually being acquired (canonicalized case-insensitively), **not**
  the writer's own `stream` field, so one writer can never silently own many streams under
  a single token (M2). The identity is encoded injectively (a JSON array with control
  characters escaped, so no part can smuggle a separator into another, M1), recorded in a
  `.writer` lock taken by an **atomic** `O_CREAT | O_EXCL` create (so two writers racing a
  fresh stream can never both win, H1), and tracked in-process by `HeldStreams`. A restart
  under a new boot/epoch is the same writer and re-acquires; a **distinct** writer reaching
  for the same stream is refused and does not proceed (DEC-0113).
- **Auto-recovery / retry:** none automatic; the refusal names the `holder` and the
  `attempted` writer. The stream stays owned by its holder. A crashed writer's lock is
  reclaimed automatically by the **same** `(machine, role, stream)` writer on restart
  (the boot/epoch id is excluded from the token). See FR-9 for the takeover-recovery path
  when the original writer is genuinely gone.
- **Visible degraded state:** none for the holder; the second writer simply cannot
  write the stream.
- **Notification tier:** operator-visible. Two writers contending for one stream is a
  wiring/ownership fault worth surfacing.
- **Product-user affordance:** nothing an end user did caused this; two components tried
  to own the same journal stream. Give each producing component its own stream, or route
  the second writer's events to its own stream.

### FR-7: Malformed store input is an invalid-input refusal

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** the boundaries validate their inputs before storing — a binary float or
  null in identity content (via `qmf.core.canonical_bytes`), a stream/edge name that is
  not a plain token or attempts path traversal (`safe_segment`), a blank registry `kind`
  or a non-positive `format_version`, an **empty** raw artifact (see FR-10), a read key
  that is not a valid `fp1:sha256:<hex>` fingerprint string, and a read that omits its
  required `for_world` declaration. A well-formed fingerprint that names no stored
  artifact is **not** malformed input — it is a not-found miss (see FR-8).
- **Auto-recovery / retry:** none automatic; the refusal names the offending `field` and
  what is allowed. Correct the argument and retry.
- **Visible degraded state:** none; nothing is stored or returned.
- **Notification tier:** silent-log. A programming or wiring mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a component
  passed a bad argument — a float where an exact value belongs, a bad stream name, a
  blank kind, or a malformed fingerprint string. The refusal says which field was wrong;
  fix the call and retry.

### FR-8: A read for a fingerprint that names nothing is a stale-evidence refusal

- **Failure class:** `stale evidence` (a CT-04 refusal category).
- **Detection:** a fingerprint-keyed read (`read_raw`, `read_view`, `get_record`)
  presenting a **well-formed** `fp1:sha256:<hex>` fingerprint that no artifact is stored
  under is a not-found miss, returned by `missing_artifact`. This is deliberately distinct
  from a *malformed* fingerprint string, which is `invalid input` (FR-7): the argument
  parsed fine, the reference is simply absent/stale. The store's miss semantics are one
  documented rule (chosen for M5): **fingerprint-keyed reads refuse on a miss**
  (`stale evidence`), while **append streams read as `Ok([])` on a never-written stream**
  (`read_stream`, `read_lineage`) — streams are lazily created, so an absent stream is
  indistinguishable from an empty one and is not an error.
- **Auto-recovery / retry:** none automatic; retryability is `no` — the artifact is
  absent and retrying the same read will not conjure it. The refusal names the `given`
  fingerprint. Produce or cite the artifact first, then read.
- **Visible degraded state:** none; no evidence is returned and nothing is stored.
- **Notification tier:** silent-log.
- **Product-user affordance:** nothing failed at runtime for an end user; a component
  cited an artifact this world's room does not hold. Confirm the fingerprint and the
  world, or produce the artifact, and read again.

### FR-9: A crashed writer's stream is recovered without silently stealing it

- **Failure class:** operational recovery (no refusal category — a documented procedure).
- **Detection:** a `.writer` lock outlives the process that took it (a crash) — a stale
  lock. The same `(machine, role, stream)` writer re-acquires automatically on restart
  (the boot/epoch id is excluded from the hold token), so a routine crash-and-restart of
  the owning writer needs no intervention. A **different** writer is correctly refused
  (FR-6): the store never silently steals a held stream, because a silent steal could let
  two writers append to one append-only journal.
- **Auto-recovery / retry:** automatic for the same writer on restart. For a genuine
  takeover — the original machine/role is permanently gone — recovery is an explicit,
  operator-authorized step: confirm the original writer is dead, then remove that stream's
  `.writer` file (or call the holder's `release()` / the boundary's `close()` on a clean
  handoff). Only then may a new writer acquire the stream. There is no timeout-based
  auto-steal.
- **Visible degraded state:** the stream is unwritable by any other writer until the same
  writer returns or an operator clears the stale lock; readers are unaffected (unlimited
  readers).
- **Notification tier:** operator-visible. A persistently stuck writer lock is worth
  surfacing so an operator can decide whether a takeover is warranted.
- **Product-user affordance:** an evidence stream could not be written because its owning
  writer is (or appears) still alive elsewhere. If the original writer crashed and will
  return, it resumes on restart; if it is gone for good, an operator clears the lock after
  confirming, and writing resumes — the platform never quietly hands one stream to two
  writers.

### FR-10: An empty raw artifact or empty view is refused, never stored

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** `append_raw` with no rows is refused before any bytes are written —
  empty evidence is meaningless and would otherwise store a receipt for nothing (L5). The
  rule is **symmetric** across the two write seams: `materialize_view` with no rows is
  refused the same way, so a view of nothing never mints a rebuildable-view receipt either
  (L11). Both name the `rows` field.
- **Auto-recovery / retry:** none automatic; the refusal names the `rows` field. Present
  at least one row.
- **Visible degraded state:** none; nothing is stored.
- **Notification tier:** silent-log. A wiring mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a component
  tried to archive an empty artifact or materialize an empty view. Present the actual rows
  and retry.

### FR-11: An incomplete source observation does not enter governed evidence (AC4)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** the CT-10 fact law requires every observation to carry event-time,
  known-at, source, source-native id, revision, receive-wall-time, an AD-8 WriterId, a
  per-writer sequence, a world, and a *computable* fp1 identity.
  `SourceObservation.try_create` validates each part and refuses the first missing or
  malformed one; the fingerprint is computed by `qmf.core.fingerprint`, so a value that
  cannot be canonicalized (a binary float in identity content) also refuses. The boundary
  additionally refuses any value that is not a complete `SourceObservation` before it
  reaches storage (`SourceObservationBoundary.admit`), so a raw dict or a half-built
  record never becomes governed evidence (FM-1, DEC-0117, DEC-0109).
- **Auto-recovery / retry:** none automatic; the refusal names the offending `field`.
  Supply the missing part and rebuild.
- **Visible degraded state:** none; nothing is admitted or stored.
- **Notification tier:** silent-log. A producer wiring mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a source feed
  presented a fact missing a required bitemporal field (when it occurred, when it became
  knowable, who wrote it, or which provider it came from). The refusal says which field;
  the producer supplies it and resubmits.

### FR-12: A `world = simulated` observation write is a policy rejection (AC5)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** an observation carries its own `world`. `SourceObservationBoundary.admit`
  routes the write through `EvidenceStore.for_world(observation.world)`, and
  `world = simulated` has no governed namespace in V1 (`qmf.core.governed_namespace`), so
  the store refuses the world before any bytes are touched. The observation VALUE may
  exist with `world = simulated`; only *writing* it into governed evidence is refused
  (DEC-0110, DEC-0117).
- **Auto-recovery / retry:** none automatic; the refusal cites `GAP-0048`. Produce the
  observation in a supported world (`live` or `replay`).
- **Visible degraded state:** none; no evidence is written.
- **Notification tier:** silent-log. Attempting a reserved-unusable world is a policy
  mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime; a component tried to record a
  synthetic-world observation, which V1 does not admit into governed storage. Use a
  supported world.

### FR-13: A cross-world observation read is a policy rejection (AC5)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `SourceObservationBoundary.read` reaches the room of the declared
  `in_world` and passes the caller's declared `for_world` down to the store's `read_raw`,
  which refuses when they differ (`require_same_world`). World isolation is storage
  separation — one world's room never serves another world's evidence, and a
  `world = simulated` room has no governed namespace and is likewise refused (DEC-0117,
  DEC-0110).
- **Auto-recovery / retry:** none automatic; the refusal names the `requested` and the
  `room_world`. Read from the evidence's own world (declare it correctly).
- **Visible degraded state:** none; no evidence is returned.
- **Notification tier:** silent-log.
- **Product-user affordance:** nothing failed; a component asked one world's room for
  another world's observations, or declared the wrong world. Declare the correct world
  and read again.

### FR-14: A corrupt or tampered observation row is refused, never read back as valid

- **Failure class:** `invalid input` for a row whose recorded fp1 no longer matches its
  content; `storage failure` (retryability `no`) for an artifact that does not hold
  exactly one observation row.
- **Detection:** `SourceObservation.from_row` rebuilds the value through `try_create` and
  then recomputes its fp1, refusing when the recomputed fingerprint differs from the row's
  recorded `fingerprint` — so a corrupted or edited row can never round-trip as valid
  evidence. `SourceObservationBoundary.read` additionally refuses an archive artifact that
  does not hold exactly one row (a source observation is a single record), surfacing it as
  a corrupt-evidence `storage failure` (H5, DEC-0108).
- **Auto-recovery / retry:** none automatic; retryability is `no` — the stored bytes are
  wrong and retrying the same read will not fix them. Restore the artifact from backup or
  re-ingest the source fact.
- **Visible degraded state:** none; no evidence is returned, and the corrupt artifact is
  never presented as valid.
- **Notification tier:** operator-visible. Stored governed evidence that no longer matches
  its own fingerprint is an integrity event worth surfacing.
- **Product-user affordance:** a stored observation could not be read because its content
  no longer matches the fingerprint it was recorded under (corruption or tampering). The
  platform refuses it rather than return altered evidence; an operator restores it from an
  off-machine backup or the source is re-ingested.

### FR-15: A governed rebuildable view offered without valid rebuild pins is refused (AC2)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** a rebuildable analytics view is never evidence — an engine format break
  costs a rebuild — so a faithful rebuild must replay against the exact calendar the view
  was built under. `WorldRooms.materialize_view` therefore **requires** a `RebuildPins`
  value (a `qmf-core` `CalendarIdentity`, which itself pins the tzdata version); a value
  that is not a `RebuildPins` is refused before anything is materialized, and the view's
  receipt records both the calendar identity and the tzdata version alongside the engine
  major (DEC-0117, DEC-0103, DEC-0106). `RebuildPins.try_create` refuses a
  non-`CalendarIdentity` at construction with the same category.
- **Auto-recovery / retry:** none automatic; the refusal names the `pins` (or
  `calendar_identity`) field. Build `RebuildPins.try_create(calendar_identity)` from the
  calendar the view was computed under and retry.
- **Visible degraded state:** none; nothing is materialized.
- **Notification tier:** silent-log. A wiring mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a component
  tried to materialize a rebuildable view without recording which calendar a rebuild must
  pin. Supply the calendar identity and retry — so a later engine-format rebuild can never
  silently re-derive a session boundary or the seal under a newer tzdata release.

### FR-16: A malformed series partition or an empty series is an invalid-input refusal (AC5)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** time-series evidence is placed within its `(source, instrument,
  time-window)` partition. `WorldRooms.place_series` refuses a `partition` that is not a
  `SeriesPartition` (build it through `SeriesPartition.try_create`, which itself refuses a
  blank source, a non-`Instrument`, or a non-`Interval` window), and refuses an **empty**
  series before any bytes are written — an empty series is meaningless evidence, the same
  L5 rule the raw archive applies to an empty artifact (FR-10). It **also** refuses a row
  whose event-time (the int64 UTC-ns count under key `t`) is missing, malformed, or falls
  outside the declared partition window `[start, end)` — checked through
  `SeriesPartition.contains_event` — naming the offending row `index`. This keeps the stored
  window a truthful bound on its rows, so the split-governed research door can derive a
  no-peek seal position from the window that a caller cannot under-state to smuggle a
  sealed-period row behind an open-window front (FR-24; DEC-0119). The partition rides into
  the stored artifact's fp1 identity, so a valid placement resolves back to exactly its
  partition (DEC-0118, DEC-0117).
- **Auto-recovery / retry:** none automatic; the refusal names the offending `partition`
  or `rows` field. Build a valid partition, present at least one row, and retry.
- **Visible degraded state:** none; nothing is stored.
- **Notification tier:** silent-log. A programming or wiring mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a component tried
  to archive time-series evidence without a well-formed `(source, instrument, time-window)`
  partition, or with no rows. The refusal says which field; fix the call and retry.

### FR-17: A corrupt series envelope is a storage-failure refusal, never resolved as valid (AC5)

- **Failure class:** `storage failure` (a CT-04 refusal category), retryability `no`.
- **Detection:** `WorldRooms.resolve_series` reads a placed series back from the immutable
  raw archive and rebuilds it. A stored artifact that does not hold exactly one series
  envelope, an envelope missing its `partition` mapping or `series` list, a partition that
  no longer rebuilds (a corrupt venue token, a start after its end), or a series row that
  is not a mapping is surfaced as a corrupt-evidence `storage failure` — the stored bytes
  are wrong, so the evidence is never resolved as a valid series (H5, DEC-0108). A
  well-formed key that names no raw-archive artifact stays a `stale evidence` miss (FR-8),
  and a rebuildable view — which lives in the processed room, never the raw archive — is
  therefore never resolved as series evidence at all (it reads as a raw-archive miss).
- **Auto-recovery / retry:** none automatic; retryability is `no` — the stored bytes are
  wrong and retrying the same read will not fix them. Restore the artifact from an
  off-machine backup or re-place the series from its source.
- **Visible degraded state:** none; no series is returned, and the corrupt artifact is
  never presented as valid evidence.
- **Notification tier:** operator-visible. Stored governed evidence that no longer matches
  the series shape is an integrity event worth surfacing.
- **Product-user affordance:** a stored time-series artifact could not be read because its
  content no longer matches the series shape it was recorded under (corruption or
  tampering). The platform refuses it rather than return altered evidence; an operator
  restores it from an off-machine backup or the series is re-placed from its source.

### FR-18: A split or seal boundary that is a civil date is refused (AC1)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** split and seal boundaries are explicit stored TradingDates or Instants,
  never civil dates (a civil date carries no calendar identity). `SplitBoundary.try_create`
  accepts a `qmf-core` `TradingDate`, an `Instant`, or an int64 UTC-nanosecond count, and
  refuses a `CivilDate` with a pointed reason; any other type is likewise `invalid input`.
- **Auto-recovery / retry:** none automatic; the refusal names the `boundary` field. Present
  a TradingDate (calendar-aligned) or an Instant and retry.
- **Visible degraded state:** none; no manifest is built.
- **Notification tier:** silent-log. A wiring mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a component tried
  to build a split with a bare civil date, which pins no calendar. Supply a trading date or
  an instant and retry.

### FR-19: A non-time-ordered, mixed-kind, or empty segment set is refused (AC1)

- **Failure class:** `invalid input` for empty, non-sequence, non-`SplitSegment`, mixed-kind,
  or non-strictly-increasing segments; `policy rejection` for a segment boundary carrying a
  calendar identity different from the manifest's pinned one.
- **Detection:** `SplitManifest.try_create` validates the segment list before fingerprinting
  a manifest — it must be a non-empty sequence of `SplitSegment`, every boundary must share
  one kind (all trading-date or all instant), and boundaries must be strictly increasing so
  segments are time-ordered and non-overlapping. A trading-date segment boundary whose
  calendar identity differs from the pinned one is a `policy rejection` (never rescaled).
- **Auto-recovery / retry:** none automatic; the refusal names the `segments` field (and the
  offending `index`). Order the boundaries strictly, use one boundary kind, and pin one
  calendar identity, then retry.
- **Visible degraded state:** none; no manifest is built.
- **Notification tier:** silent-log. A wiring mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a component tried
  to build a split whose segments overlap, mix kinds, or cite a foreign calendar. The
  refusal says which; fix the segments and retry.

### FR-20: An omitted or under-covering purge/embargo width is refused (AC2)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** `purge_width` and `embargo_width` are required manifest fields that enter
  the split fingerprint. `SplitManifest.try_create` refuses an omitted (`None`) or negative
  width, and refuses a width shorter than the maximum warm-up-plus-confirmation-delay bound
  across every cited `ProducerHorizon` — a manifest that under-covers its own producers would
  leak the held-out period, so it is refused rather than built (DEC-0131).
- **Auto-recovery / retry:** none automatic; the refusal names the `purge_width` or
  `embargo_width` field and the `required_ns` bound. Compute the default with
  `ProducerHorizon.max_bound(...)`, set both widths to at least that, and retry.
- **Visible degraded state:** none; no manifest is built.
- **Notification tier:** silent-log. A wiring mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a component tried
  to build a split without declaring how much data to purge and embargo around the
  boundaries, or declared too little to cover its own producers. Supply widths that cover the
  widest cited producer and retry.

### FR-21: A split reused with a longer-horizon producer is refused (AC2)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** a manifest is fingerprinted with fixed purge and embargo widths. Reusing it
  with a producer whose warm-up-plus-confirmation horizon exceeds either declared width would
  leak the held-out period across a boundary. `SplitManifest.admits_producer` recomputes the
  producer's bound against the frozen widths and refuses when it exceeds them — the split
  refuses rather than leaks (DEC-0131).
- **Auto-recovery / retry:** none automatic; the refusal names the `producer` field and the
  `bound_ns` / `purge_ns` / `embargo_ns`. Mint a new manifest with widths that cover the
  longer-horizon producer (a new fingerprint, a new split id) and use that instead.
- **Visible degraded state:** none; the existing manifest is unchanged and still valid for
  the producers it already covers.
- **Notification tier:** operator-visible. Reusing a split with an artifact it was not built
  to cover is a research-hygiene fault worth surfacing.
- **Product-user affordance:** a longer-horizon indicator or structure was applied to a split
  that was not built with enough purge/embargo to hold it out safely. The platform refuses
  rather than leak; build a split sized for the new producer.

### FR-22: A record straddling a boundary beyond the embargo is refused (AC3)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** records partition into segments by knowledge time (confirmed-at for a
  structure object, the knowable-at of the last contributing input for an indicator result).
  `SplitManifest.partition_record` refuses a record whose `observed_at` precedes a segment
  boundary while its `knowledge_time` follows it — a straddle — unless the declared embargo
  width covers the gap (`knowledge_time - observed_at`). A record whose knowledge time falls
  beyond the split's last boundary, or a trading-date split (record placement is the calendar
  extension's job), is an `invalid input` refusal instead. The straddle gap is a non-negative
  span by construction: `KnowledgeRecord.try_create` refuses a record whose knowledge-time
  precedes its observed-at (a fact cannot become knowable before it becomes observable), and
  `partition_record` defends against a trusted-internal-constructed record the same way — a
  **negative** gap can never be covered by an embargo and would otherwise pass the embargo
  check and slip sealed-region data into an earlier segment (an `invalid input` refusal).
- **Auto-recovery / retry:** none automatic; the refusal names the `gap_ns` and the
  `embargo_ns`. Widen the embargo (a new manifest) or exclude the straddling record.
- **Visible degraded state:** none; the record is not placed in any segment.
- **Notification tier:** silent-log. A leak-prevention refusal surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a record whose
  information only became knowable after a split boundary would have leaked across it, and the
  declared embargo did not cover the gap. The platform refuses rather than leak; widen the
  embargo or drop the record.

### FR-23: A row of a foreign calendar identity is refused, never rescaled (AC5)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** a manifest and its seal pin exactly one calendar identity in-band.
  `SplitManifest.admits_calendar`, `SplitManifest.partition_record` (for a record carrying a
  calendar identity), and `HoldoutSeal.is_sealed` / `HoldoutSeal.guard` (for a trading-date
  read position) refuse any row whose calendar identity differs from the pinned one — it is
  refused, never silently rescaled to the pinned calendar (DEC-0106, DEC-0119).
- **Auto-recovery / retry:** none automatic; the refusal names the `pinned` and `given`
  identities. Re-express the row under the manifest's pinned calendar identity (a derived
  value carrying lineage), never a silent rescale, and retry.
- **Visible degraded state:** none; the row is not admitted.
- **Notification tier:** silent-log. A wiring mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a component offered
  a row aligned to a different market-hours calendar than the split pins. The platform refuses
  rather than quietly rescale it; align the row to the pinned calendar and retry.

### FR-24: A read into the sealed no-peek window is refused at every read boundary (AC4)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** the newest sealed window (`registry:historical_holdout_months`) is a no-peek
  lock, not retention — all history is kept regardless. A `HoldoutSeal` is **constructor-
  injected** into the read boundaries (through the store-neutral `ReadSeal` seam, so the
  dependency-free store never imports the CT-12 vocabulary) and **consulted on every read**,
  never an optional per-call argument a caller can skip. It is wired at each of the four named
  `ReadBoundary` values: the raw archive (`AppendStore.read_raw`), processed views
  (`AppendStore.read_view`), the split-governed research door (`WorldRooms.resolve_series`),
  and restored backups (`BackupInput.read_room`). `guard_sealed_read` is **fail-closed**: with
  a seal wired, a read that declares a knowledge position reaching into the sealed window is a
  `policy rejection`, and a read that declares **no** position is *also* a `policy rejection`
  (a positionless read cannot be proven outside the window, so it is refused rather than served
  fail-open — never the sealed bytes handed straight back). The three caller-facing boundaries
  therefore require their `at` position when a seal is wired. The research door cannot declare a
  position up front — it resolves a series only by reading the evidence — so it composes its
  read through `AppendStore.read_raw_self_guarded`, which reads the raw rows and guards the seal
  at a position **derived from the evidence itself**: the latest of the series' declared window
  end and the rows' own event-times (`WorldRooms.resolve_series`), so the seal cannot be bypassed
  by omitting a position nor by an under-stated window (which `place_series` also refuses at write
  time, FR-16), and no path returns sealed raw bytes unguarded. The research door consults the
  seal **whichever surface it is wired at**: a seal wired into the store's `AppendStore` is
  guarded by `read_raw_self_guarded`, and a seal wired into `WorldRooms.for_world` is consulted by
  `resolve_series` at the **same** derived position — so wiring the seal at either surface (or
  both) leaves no unguarded research door, and wiring it only at `WorldRooms` (over a store with no
  seal) is no longer a silently unguarded door. `HoldoutSeal.guard_read` compares
  the read's knowledge position against the frozen seal boundary and refuses a position at or
  after it with a `policy rejection` naming the boundary — **never** a silent empty result. It is
  enforced now, independent of the deferred look-ahead and attempt-counter gates
  (GAP-0016/GAP-0017, DEC-0121). The one authorized final look stays the journaled
  control-action path (FR-25), untouched by this read-boundary wiring.
- **Auto-recovery / retry:** none automatic; the refusal names the `boundary` and the
  `seal_boundary`. Read outside the sealed window, or take the one authorized final look (FR-25).
- **Visible degraded state:** none; no sealed evidence is returned, and the underlying history
  remains fully retained.
- **Notification tier:** operator-visible. A read reaching into the no-peek holdout is worth
  surfacing so the operator knows research tried to touch its own evaluation period.
- **Product-user affordance:** research tried to read into the newest sealed evaluation period,
  which is locked so results are not tuned on it. The platform refuses with a clear reason
  rather than returning an empty result that could be mistaken for "no data"; read outside the
  seal, or use the one authorized final look.

### FR-25: A second authorized final look at the sealed period is refused (AC6)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** the sealed period is entitled to exactly one authorized final look.
  `HoldoutSeal.authorize_final_look` scans the CT-13 control-action stream for an existing
  final look at this seal boundary (the named `sealed-period-final-look` control-action
  subtype) and refuses a second — the sealed set is never silently recycled into research, and
  the look does not unseal it, so `guard` still refuses research reads afterward (DEC-0119).
- **Auto-recovery / retry:** none automatic; the refusal names the `final_look` field and the
  `seal_boundary`. There is no second look; the one look is already journaled as evidence.
- **Visible degraded state:** none; the first look's journal record is preserved untouched.
- **Notification tier:** operator-visible. A second attempt to open the sealed period is a
  research-hygiene event worth surfacing.
- **Product-user affordance:** the one permitted final evaluation on the sealed period has
  already been taken and recorded; the platform refuses a repeat so the holdout cannot be
  re-used to tune results. The recorded final look stands as the evidence of that one look.

### FR-26: An unpersistable journal event blocks the command stream (AC5)

This is the block-on-unpersistable mode. Read it as the whole story, not a one-liner: it
is the rule that keeps a journal from ever quietly losing a state change when the durable
store hiccups.

- **Failure class:** `storage failure` (a CT-04 refusal category).
- **What "block-on-unpersistable" means, in plain terms.** A journal event records that
  something happened — a decision was made, a control action was taken, a data-quality
  problem was seen. If that record cannot be written to durable storage (the disk is full,
  the file is locked, the store is down), the component holding the `WriterId` must **stop
  and wait**, not keep going as if the record had been saved. "Keep going" would mean the
  system acted on a state change it never durably recorded — the exact silent-loss the
  journal exists to prevent. So a failed append **blocks the writer's command stream**: the
  event is kept in memory, no later event is accepted, and the writer stays blocked until
  the store recovers and the kept event is written for real.
- **Detection.** `JournalWriter.record` (and `record_multiroom` / `record_data_quality` /
  `record_control_action`) appends through the CT-13 `JournalStore`, which translates any
  engine failure to a `storage failure` refusal (FR-1). The writer recognizes it with
  `qmf.core.is_unpersistable` and, instead of advancing, enters a **blocked** state that
  retains the exact built event (`JournalWriter.blocked_event`). While blocked, every
  further `record` returns a `storage failure` refusal naming the `blocked_stream` and
  `blocked_sequence`, and **consumes no sequence** — so the per-`(writer, boot-epoch)`
  sequence stays gapless and the retry reuses the same number.
- **Auto-recovery / retry:** no automatic retry — the caller drives it. Once the store is
  back, the component holding the `WriterId` calls `JournalWriter.retry_blocked`, which
  re-runs the exact retained append. A journal append is content-addressed, so a
  byte-identical re-append is idempotent (no duplicate line); on success the previously
  unpersistable event **is journaled on recovery**, the writer unblocks, and the sequence
  advances by exactly one. If the store is still down the writer stays blocked and the
  refusal repeats — the event is never dropped and never double-written.
- **Visible degraded state:** the writer's command stream is **blocked** — no new journal
  event is written on that stream — until the retained event is durably journaled. Readers
  are unaffected (unlimited readers). The retained event is held in memory and is the first
  thing written on recovery, so nothing that was accepted-then-failed is ever lost.
- **Notification tier:** operator-visible, escalating to alarm on a prolonged outage. A
  blocked command stream means a producing component cannot record state; that is an
  operational condition worth surfacing.
- **Product-user affordance:** an action could not be recorded because durable storage was
  unavailable, so the platform paused that component's recording rather than pretending the
  action was saved. Nothing the end user did is lost — the pending record is held and
  written the moment storage returns, and the stream resumes exactly where it stopped. If
  the outage persists, an operator restores storage; there is no data to re-enter.

### FR-27: A partial multi-room journal write blocks the command stream (AC5)

- **Failure class:** `storage failure` (a CT-04 refusal category).
- **Detection:** some journal operations write to more than one room — a journal event plus
  a causal lineage edge that references it (a cross-stream link). `JournalWriter`
  runs the journal append first, then each secondary room write (an `EdgeWrite` thunk given
  the new event's fp1). If the journal event lands but a secondary write refuses — a
  **partial multi-room write** — the writer treats the whole operation as unpersistable and
  **blocks**, retaining the entire operation (the event and its secondary writes), exactly
  as FR-26 does for a single-room failure. The sequence does not advance on a partial write.
- **Auto-recovery / retry:** the caller calls `retry_blocked` once the failing room
  recovers; it re-runs the whole operation. Both the journal append and the lineage-edge
  append are content-addressed and idempotent, so re-running a partially-completed operation
  never double-writes the half that already landed — it simply completes the half that did
  not. On full success the writer unblocks and the sequence advances once.
- **Visible degraded state:** the command stream is blocked until every room in the
  operation has committed; a half-written link is never reported as done.
- **Notification tier:** operator-visible. A room that accepts the event but not its linked
  edge is an operational fault worth surfacing.
- **Product-user affordance:** a recorded action and its cross-reference must both be saved
  together; one saved without the other would leave a dangling link, so the platform pauses
  rather than report a half-saved operation. On recovery it finishes the missing half and
  resumes — nothing is lost or duplicated.

### FR-28: A detected sequence gap signals loss and is surfaced (AC2)

- **Failure class:** `storage failure` (a CT-04 refusal category), retryability `no`.
- **Detection:** a journal stream's sequence is strictly increasing and **gapless** per
  `(writer, boot-epoch)`. `detect_sequence_gaps` (and `JournalReader.read_checked`) groups a
  stream's events by `(machine, role, stream, boot_epoch_id)` and checks each group runs
  contiguously from an expected base; a missing sequence (a lost event) or a duplicate
  sequence is a `storage failure` refusal carrying `signal = loss`, the offending writer, and
  the `expected_sequence` / `found_sequence`. The loss is **surfaced**, never a silent success
  and never a silently-shortened stream. Two restart hazards are designed out (L10): (1) a
  writer restarting under the **same** boot-epoch discovers its resume point via
  `JournalWriter.resume`, which reads the recorded tail and starts one past the highest
  sequence it already persisted — so it never re-issues an on-disk sequence that would
  otherwise be reported as a permanent `duplicate` loss; and (2) `read_checked` **derives**
  the expected base from the stream's own minimum observed sequence (rather than assuming
  `0`), so a stream legitimately resumed from a non-zero start is not falsely alarmed for a
  "gap from 0", while every interior gap and duplicate is still surfaced. A caller may still
  pass an explicit `expected_start` to assert a specific base (e.g. `0` for a from-zero
  stream).
- **Auto-recovery / retry:** none — retryability is `no`, because a lost event will not
  reappear on a re-read. Recovery is to restore the stream from an off-machine backup or
  re-derive the missing evidence; the gap report says exactly which sequence is missing.
- **Visible degraded state:** the reader refuses the stream as incomplete rather than
  returning a truncated set that could be mistaken for the whole; other streams are
  unaffected.
- **Notification tier:** operator-visible. A gap in an append-only journal is an
  evidence-integrity event.
- **Product-user affordance:** a record of events came back with a hole in it, meaning at
  least one event was lost from durable storage. The platform refuses the incomplete stream
  rather than quietly hand back a partial history; an operator restores the missing records
  from backup.

### FR-29: A decision event without its mandatory closed outcome is refused (AC3)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** a `decision` event carries a mandatory closed `outcome` — `authorized |
  refused-by-door | suppressed`. `JournalEvent.try_create` refuses a decision event that
  omits the outcome, or gives one outside the closed set, or is `refused-by-door` /
  `suppressed` without the refusing-door / suppressing-authority reference in its payload;
  it also refuses any **non**-decision event that carries an outcome. This keeps every
  decision selectable on a declared field with a resolvable reference, so a projection (the
  legacy `veto_ledger` = `outcome = refused-by-door`) never selects on ad-hoc key presence.
- **Auto-recovery / retry:** none automatic; the refusal names the offending `field`
  (`outcome`, `refusing_door`, or `suppressing_authority`). Supply the closed outcome and
  its reference, then rebuild.
- **Visible degraded state:** none; the event is not built and nothing is journaled.
- **Notification tier:** silent-log. A producer wiring mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a component tried
  to journal a decision without saying how it was decided (allowed, refused by which door,
  or suppressed by which authority). The refusal says which part is missing; the producer
  supplies it and resubmits.

### FR-30: A journal event outside the seven types is refused (AC1)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** the journal records exactly seven event types — decision, order, fill, risk
  transition, promotion, data quality, control action — an enum addable in a later contract
  version but never redefined. `JournalEvent.try_create` refuses any `event_type` outside the
  set (the refusal lists the allowed values), so an ad-hoc "heartbeat" or "debug" record can
  never become journal evidence.
- **Auto-recovery / retry:** none automatic; the refusal names the `event_type` field and the
  allowed set. Use one of the seven types, or route the record to operator logging (which is
  a distinct thing from the journal), and retry.
- **Visible degraded state:** none; the event is not built and nothing is journaled.
- **Notification tier:** silent-log. A wiring mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a component tried
  to record a kind of event the journal does not carry. The refusal says which kinds are
  allowed; use one of them, or send diagnostic detail to the operator log instead.

### FR-31: A corrupt or tampered journal row is refused, never read back as valid (AC4)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** `JournalEvent.from_row` rebuilds the value through `try_create` and then
  recomputes its fp1, refusing when the recomputed fingerprint differs from the row's
  recorded `fingerprint` — so a corrupted or edited row (a changed sequence, instant, world,
  or payload) can never round-trip as valid evidence. `correlation_id` and `display_time` are
  excluded from identity, so editing those does not change the fingerprint (they are
  display/linking annotations, not evidence identity), while any identity field that was
  altered is caught. A row that is not a mapping, or that omits its fingerprint, is likewise
  refused.
- **Auto-recovery / retry:** none automatic; retryability is `no` — the stored bytes are
  wrong and retrying the read will not fix them. Restore the artifact from an off-machine
  backup or re-derive the event.
- **Visible degraded state:** none; no event is returned, and the corrupt row is never
  presented as valid evidence.
- **Notification tier:** operator-visible. Stored journal evidence that no longer matches its
  own fingerprint is an integrity event worth surfacing.
- **Product-user affordance:** a stored journal record could not be read because its content
  no longer matches the fingerprint it was recorded under (corruption or tampering). The
  platform refuses it rather than return altered evidence; an operator restores it from an
  off-machine backup.

### FR-32: An entity-journal projection spanning account roles without a declared cross-role read is refused (AC3)

This is the FM-11 paper-and-live separation mode. Read it as the whole story: it is the
rule that keeps a projection from silently mixing live money with paper/demo evidence.

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **What it means, in plain terms.** Paper and live are separated by construction: each
  account role (live, demo, paper-validation, paper-benched) resolves in its **own**
  role-scoped namespace, and `role = live` resolves in the live evidence namespace that
  admits only live rows (`role_namespace`). A projection that would combine rows of more
  than one role into one view is aggregating across roles — which is allowed **only** when
  the caller explicitly declares it, so live results are never silently blended with paper.
- **Detection:** `entity_journal` (and the `book_journal` / `bms_journal` / `bot_logbook`
  conveniences) collects the roles carried on the selected rows. When the caller passes
  neither a single `role` scope nor a declared `cross_role` read, and the selected rows span
  more than one role, it returns a `policy rejection` naming the `roles` found and the
  `selector`. Passing a single `role` resolves inside that one namespace (rows of other
  roles are simply outside it); passing both `role` and `cross_role` is a contradiction
  (`invalid input`).
- **Auto-recovery / retry:** none automatic; the refusal names the `roles` present. Read one
  role's namespace (`role=...`), or — only for the two declared exceptions — pass the
  cross-role read: the AD-35 decay-cohort read (`decay_cohort_read`) or the multi-role entity
  projection (`cross_role=MULTI_ROLE_ENTITY`), each carrying `role` on every row.
- **Visible degraded state:** none; no blended view is returned. There is **no write
  exception ever** — this projection layer writes nothing and never crosses roles on write.
- **Notification tier:** operator-visible. A projection reaching across account roles without
  declaring it is a governance event worth surfacing.
- **Product-user affordance:** a view tried to combine records from more than one account
  role (for example live and paper) without saying so; the platform refuses rather than mix
  live money with paper evidence. Ask for one role's logbook, or explicitly request the
  cross-role view the platform allows (the decay-cohort read or a single entity that ran in
  more than one role).

### FR-33: Book/Bot identity in a venue-authored payload is refused (AC2)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** the neutral venue port cannot carry Book identity and must not learn it —
  a Book projection joins venue-authored orders and fills to their authorizing decision
  through the command fingerprint, never by threading Book identity into the venue payload
  (which would create the `qmf-venue -> qmf-risk` coupling default-deny forbids).
  `guard_neutral_venue_payload` refuses a venue-authored event whose payload carries one of the
  `BOOK_IDENTITY_FIELDS` — `book_definition_fp`, `book_instance_id`, `bms_instance_id`,
  `bot_definition_fp`, `seat_binding` — naming the `leaked_fields`. `read_command_fingerprint`
  guards unconditionally; but the venue-join path of `entity_journal` applies the guard **only
  to an event actually matched into the requested projection** (its command fingerprint is
  indexed and its attribution matches the selected entity). This scoping is deliberate (L8): a
  leaked key on a **matched** event still refuses the read, but an unrelated venue event on
  **another** Book that happens to carry a leaked key does not poison this Book's clean
  projection — the leak stays a data-quality fault of the leaking producer's own stream to
  surface, not grounds to refuse an unrelated read.
- **Auto-recovery / retry:** none automatic; the refusal names the leaked fields. Remove the
  Book identity from the venue payload and carry it on the authorizing command record instead,
  then re-project.
- **Visible degraded state:** none; a matched leaked event is not projected, and the
  projection refuses rather than silently attribute a venue event by an identity that should
  not be there; an unrelated leaked event on another Book is simply not joined into this read.
- **Notification tier:** silent-log. A producer wiring mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a venue event was
  recorded with Book identity baked into it, which the design forbids. The refusal says which
  fields leaked; the producer keeps the venue payload neutral and lets the Book projection
  join through the command fingerprint.

### FR-34: A malformed or missing projection identity field is refused during selection (AC2, AC3)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** a risk-authored event that a projection matches must carry well-formed
  identity fields under the pinned CT-25 keys. During selection the projection refuses a
  **partial** binding identity (some of the four binding keys present, others missing or
  blank — `read_binding`), a **partial** per-bot identity (a Bot definition fp without its
  seat binding, or vice versa, or a malformed fingerprint — `read_bot_seat`), and a matched
  row that carries no declared `role` (`read_role`) — every projected row must carry a role.
  A risk-authored event that declares **no** binding at all (zero binding keys, e.g. a
  qmf-data control action) is not malformed — it simply does not match an entity selector and
  is skipped, never refused. The AD-35 decay-cohort read (`decay_cohort_read`) applies the same
  role rule with the same fail-closed edge (M7): an event carrying **no** `role` key is not a
  cohort row and is skipped, but an event that **declares** a `role` which is malformed
  (present but outside the closed `AccountRole` set — e.g. a typo'd `"LIVE"`) is refused, not
  silently dropped while sibling rows survive — exactly as `book_journal` refuses the same row.
- **Auto-recovery / retry:** none automatic; the refusal names the offending `field`
  (`book_instance_id`, `seat_binding`, `role`, …). Supply the missing part on the producing
  event and re-project.
- **Visible degraded state:** none; the projection is not returned. It fails closed rather
  than emit a row whose identity or role is half-declared.
- **Notification tier:** silent-log. A producer wiring mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a record that a
  logbook tried to attribute was missing part of its identity (which Book/bot it belongs to,
  or which account role it ran under). The refusal says which field; the producer supplies it
  and the logbook resolves.

### FR-35: A conflicting command-fingerprint attribution is refused (AC2)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** the command-fingerprint join is built by `CommandIndex.build` from the
  risk-authored events that carry a command fingerprint (the command records). One command
  fingerprint identifies one command, so it must attribute to exactly one binding. A repeated
  fingerprint with a **byte-identical** attribution is idempotent; a repeated fingerprint
  resolving to a **different** binding is refused, naming the `command_fingerprint` — one
  command must never map to two Books. A command record carrying a command fingerprint but no
  valid binding, or a malformed command fingerprint, is likewise refused.
- **Auto-recovery / retry:** none automatic; the refusal names the conflicting
  `command_fingerprint`. The conflict signals corrupt or mis-stamped command records; restore
  the affected records from an off-machine backup or re-derive them, then rebuild the index.
- **Visible degraded state:** none; the index is not built, so no venue event is joined under
  an ambiguous attribution.
- **Notification tier:** operator-visible. One command fingerprint attributing to two
  bindings is an evidence-integrity event worth surfacing.
- **Product-user affordance:** two command records claimed the same command identity but point
  at different Books; the platform refuses to build the join rather than attribute an order or
  fill to the wrong Book. An operator restores the affected records and the join rebuilds.

### FR-36: An unknown legacy Records projection name is refused (AC4)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** the legacy five Records streams survive as **projection names only** —
  `veto_ledger`, `trade_journal`, `book_journal`, `ksa_audit_log`, `correlation_ledger` —
  mapped onto the seven journal event types by the one versioned `RECORDS_STREAM_MAPPING`
  table. `records_stream` resolves only those five names (as a `RecordsStreamName` or its
  string); any other name is refused, naming the `allowed` set. No second event catalog is
  minted, and `veto_ledger` selects on the decision event's declared `outcome =
  refused-by-door` field, never on key presence.
- **Auto-recovery / retry:** none automatic; the refusal names the `given` name and the five
  allowed names. Use one of the five legacy projection names, or an entity-journal projection
  for a per-entity view.
- **Visible degraded state:** none; nothing is projected.
- **Notification tier:** silent-log. A wiring mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a component asked
  for a Records stream name the platform does not carry. The refusal lists the five names that
  exist; use one of them.

### FR-37: An unavailable citation index fails closed — deletion is never licensed (AC3)

Amends Story 3.3's keep-forever-vs-deletion-licensed retention law (grouped with FR-15
through FR-17).

- **Failure class:** `unavailable dependency` (a CT-04 refusal category), retryability `yes`.
- **Detection:** deletion is licensed **only** for a rebuildable analytics view that no result
  label cites, answered by the injected `CitationIndex` seam, which reaches the registry across
  the package boundary. That seam can be unreachable or raise (a `ConnectionError`, a timeout).
  `RetentionPolicy.verdict_for` returns a `Result`: it catches any failure of the citation
  read and returns an `unavailable dependency` typed refusal naming the `citations` field —
  **never** a raised exception across the package seam (CT-04, AR-13). Because deletion is
  licensed only on a *positive, successful* "no result label cites this" answer, a failed,
  unreachable, stale, or empty index yields **no** deletion licence: `may_delete` returns
  `False`. A retained-forever artifact (raw archive, journal, registry records, lineage) is
  decided by its receipt alone and never consults the seam, so it is unaffected. This closes a
  fail-**open** hole where a raising or empty index previously licensed deleting a cited
  input's view (Story 3.3 AC3: "no result's cited input is ever deleted").
- **Auto-recovery / retry:** retryability is `yes` — the dependency is transiently down.
  Restore the citation index (the registry seam) and re-ask; deletion stays refused until a
  successful "nothing cites this" answer is obtained.
- **Visible degraded state:** none; nothing is deleted. The verdict fails closed — the safe
  direction for an irreversible delete — so an artifact is retained rather than risked.
- **Notification tier:** operator-visible. A retention verdict that cannot consult the citation
  index is worth surfacing, since it stalls deletion housekeeping.
- **Product-user affordance:** nothing failed at runtime for an end user; a cleanup step could
  not confirm whether a rebuildable view is still cited by a result, so the platform keeps it
  rather than risk deleting an input a result depends on. It retries once the registry is back.

### FR-38: A record within the purge width of a split boundary is excluded from both segments (AC2, AC3)

Amends Story 3.4's CT-12 dataset splits (grouped with FR-18 through FR-25).

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `purge_width` is a required, fingerprinted manifest field; `partition_record`
  now **applies** it (previously only `embargo_width` was applied, so a fingerprinted purge
  width had no effect). A cleanly-placed record — one whose `observed_at` and `knowledge_time`
  fall in the same segment — whose knowledge time lands within `purge_width` of the boundary
  between two adjacent segments is excluded from **both**: its warm-up-plus-confirmation window
  brushes the boundary, so admitting it to either adjacent split would leak across it, and it
  is quarantined (refused) instead, naming the `boundary_ns`, `purge_ns`, and `distance_ns`. A
  record exactly `purge_width` away is at the edge and admitted; a zero purge width has no
  purge zone; the split's terminal boundary (the last segment's upper bound, beyond which a
  record is refused as out-of-range) is not an inter-segment boundary and is not a purge edge.
  A record that **straddles** a boundary (observed-at and knowledge-time in different segments)
  is governed by the embargo rule (FR-22), not the purge zone.
- **Auto-recovery / retry:** none automatic; the refusal names the `boundary_ns` and
  `purge_ns`. A boundary-adjacent record cannot be placed in either split without leaking;
  exclude it from training/evaluation, or mint a split whose boundaries do not fall within a
  purge width of it.
- **Visible degraded state:** none; the record is not placed in any segment.
- **Notification tier:** silent-log. A leak-prevention refusal surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a record sitting
  right on the edge of a split boundary would have leaked information across the held-out
  boundary. The platform excludes it from both adjacent splits rather than leak; drop the
  boundary-adjacent record or re-cut the split.

### FR-39: A stored journal row of a foreign world is refused on read, never served (AC5)

Amends Story 3.1's cross-world isolation (grouped with FR-4 the write-side world guard and FR-5
the cross-world read). This is the read-side, defense-in-depth counterpart to FR-4.

- **Failure class:** `storage failure` (a CT-04 refusal category), retryability `no`.
- **Detection:** world isolation is storage separation, enforced on **both** the write side and
  the read side. On the write side, `require_write_world` blocks a journal event whose declared
  world differs from the room's from ever landing (FR-4). On the read side, `JournalStore.read_stream`
  now re-checks **every stored row's own declared world** against the room's world
  (`guard_stored_row_world`) after loading the stream and before returning it. Because the write-side
  guard blocks a cross-world event on the way in, a stored row that declares a *different* world than
  the room's can only have arrived through **direct file tampering** — corrupt stored evidence, not a
  caller mistake — so it is surfaced exactly how a torn middle line or a sequence gap is (a
  `storage failure`, retryability `no`) and never served as valid. The refusal names the offending
  `row_index`, the `declared` world, and the `room_world`. A row that declares **no** world inherits
  the room's world (a bare physical row carries none), exactly as the write-side guard treats it, so
  a legitimately world-less row is never refused. `read_stream` is the store-seam choke point for
  every governed reader — `JournalReader.read` / `read_checked`, the seal's control-action stream
  scan, `JournalWriter.resume` — so all of them inherit the guard; the verbatim `BackupInput` copy
  path is deliberately not gated (a backup copies bytes as-is, tampered or not, for forensics).
- **Auto-recovery / retry:** none automatic; retryability is `no` — the stored bytes are wrong and
  retrying the same read will not fix them. Restore the stream from an off-machine backup or
  re-derive the affected records; the refusal says which row and which world.
- **Visible degraded state:** none; no evidence is returned, and the tampered row is never presented
  as valid. Other streams are unaffected.
- **Notification tier:** operator-visible. A stored journal row belonging to another world is an
  evidence-integrity event worth surfacing — governed storage separation was violated on disk.
- **Product-user affordance:** a record of events came back with a row belonging to a different
  world (live vs. replay) than the stream it was read from, which can only happen if the file was
  altered outside the platform. The platform refuses the stream rather than hand back mixed-world
  evidence; an operator restores it from an off-machine backup.

Story 5.3 delivers the CT-14 verify primitives — automated sample-restore and full-restore
rehearsal as the only source of a recoverability claim, plus the staged never-in-place
migration sequence — FR-40 through FR-42.

### FR-40: Recoverability is refused when asserted from a snapshot alone (AC1)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `refuse_snapshot_alone_claim` always refuses; `OffMachineVerify` issues a
  `RecoverabilityClaim` only after a successful sample-restore or full-restore rehearsal that
  read the restored evidence back against a documented restore path (SCN-0004, DEC-0118).
- **Auto-recovery / retry:** none — inventing a claim from an off-machine copy's existence is
  a governance mistake, not a transient fault. Run the verify primitive instead.
- **Visible degraded state:** none; no recoverability claim is returned.
- **Notification tier:** operator-visible (a caller attempted to short-circuit verification).
- **Product-user affordance:** having a backup file is not proof it can be restored. The
  platform will not declare recovery complete until a sample-restore or full-restore rehearsal
  confirms the restored evidence against a documented path.

### FR-41: A corrupt or mismatched verify restore is a storage failure with no claim (AC2)

- **Failure class:** `storage failure` (a CT-04 refusal category).
- **Detection:** `OffMachineVerify.sample_restore` / `full_restore_rehearsal` restore into a
  replacement store and compare the CT-26 re-export to the expected export. A failed decrypt,
  bad envelope, missing object, or fingerprint/canonical mismatch returns `storage failure`
  (`signal: corrupt-copy` or `signal: verify-mismatch`); no `RecoverabilityClaim` is issued.
- **Auto-recovery / retry:** none automatic. A transient unreachable bucket may carry
  `retryability = yes` from the underlying restore; a corrupt envelope or mismatch is
  `retryability = no`.
- **Visible degraded state:** recoverability is unproven; the source store and earlier
  off-machine versions are left untouched.
- **Notification tier:** operator-visible (escalating to alarm on repeated verification
  failures against the same version).
- **Product-user affordance:** the backup could not be proven restorable — the restored bytes
  were missing, corrupt, or did not match the documented evidence. The platform reports
  failure rather than a false recovery success; an operator investigates the off-machine copy
  or re-runs backup + verify.

### FR-42: An in-place or overlapping-root migration is refused (AC3)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `migrate_evidence` requires distinct filesystem roots for `source`,
  `destination`, and `verify_into`. A same-root source/destination is
  `signal: refuse-in-place-migration`; a verify target that collides with either is
  `signal: refuse-overlapping-verify-root`. The sequence is always preflight → backup-first →
  dry-run → migrate → verify (AR-32, DEC-0118).
- **Auto-recovery / retry:** none — re-run against a fresh destination and a distinct
  verify-rehearsal root.
- **Visible degraded state:** nothing is written; the source remains the intact documented
  restore path.
- **Notification tier:** operator-visible (wiring mistake).
- **Product-user affordance:** a migration that would overwrite the only good local copy is
  blocked. Point destination and verify rehearsal at separate empty store roots and retry;
  the source stays readable throughout.

Story 5.4 delivers the application-owned nightly off-machine cycle helper —
`OffMachineCycle.run_once` as a composition-root one-shot with no threads/cron/daemon
in `qmf-data` — FR-43 through FR-45.

### FR-43: Asking QMF to own the nightly schedule or a daemon is refused (AC2)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `refuse_schedule_ownership` and the `OffMachineCycle.own_schedule` /
  `start_daemon` helpers always refuse with `signal: refuse-schedule-ownership`.
  `qmf.data.cycle` imports no `threading` / `sched` / `asyncio` / cron machinery; the
  application calls `run_once` when `registry:backup_cadence` = nightly arrives
  (FM-6, FM-9, DEC-0118, DEC-0051).
- **Auto-recovery / retry:** none — schedule ownership is a governance mistake, not a
  transient fault. Drive each cycle from application/ops cron or supervision instead.
- **Visible degraded state:** none; no cycle runs and no daemon starts.
- **Notification tier:** operator-visible (a caller attempted to put scheduling inside
  the library).
- **Product-user affordance:** the backup library will not install a nightly job or
  background thread. Wire your own scheduler to call the one-cycle helper each night.

### FR-44: Asking QMF to own a numeric RPO/RTO/retention target is refused (AC2)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `refuse_numeric_rpo_rto` and `OffMachineCycle.set_recovery_point_objective`
  / `set_recovery_time_objective` always refuse with `signal: refuse-numeric-rpo-rto`.
  The node/ops pointers (`NODE_OPS_BACKUP_RECOVERY_POINT_OBJECTIVE` and kin) stay
  `None` and are never filled from a recommendation (DEC-0118).
- **Auto-recovery / retry:** none — set the numeric targets at the node/ops sitting,
  not through this boundary.
- **Visible degraded state:** none; no target is recorded.
- **Notification tier:** operator-visible (wiring mistake).
- **Product-user affordance:** recovery-point and recovery-time numbers are chosen by
  operations, not by the backup library. The library only ships the primitives that
  meet whatever targets ops later name.

### FR-45: A nightly cycle into `world = simulated` or an in-place sample root is refused (AC3)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `OffMachineCycle.run_once` refuses `world = simulated` (DEC-0110) and
  refuses a `sample_into` / `full_into` root that collides with the source archive
  (`signal: refuse-in-place-restore` / `refuse-overlapping-verify-root`). Cross-world
  CT-26 / CT-14 gates inside the cycle inherit the same policy-rejection path as the
  backup primitives (DEC-0117).
- **Auto-recovery / retry:** none for simulated/in-place; re-run against `live` or
  `replay` with distinct replacement store roots.
- **Visible degraded state:** no off-machine copies or restores are claimed; the source
  archive stays intact.
- **Notification tier:** operator-visible.
- **Product-user affordance:** simulated evidence is not backed up into the governed
  path, and a cycle will not overwrite the only local copy while verifying. Point the
  sample/full restore roots at empty directories and use `live` or `replay`.

Story 6.1 delivers the CT-15 external-source ingest seam (`COMP-QMF-DATA-INGEST` /
`ExternalSourceIngest`) — provider port ownership, idempotent
`(source, source-native id, revision)` intake into CT-10 producer values,
application-routed admission, and out-of-authority refusals — FR-46 through FR-49.

### FR-46: A malformed provider record or missing CT-03 mapping is refused (AC4)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** `ExternalSourceIngest.normalize` / `intake` require event-time,
  known-at, source, source-native id, revision, and a CT-03 `Instrument` mapping
  before minting a CT-10 `SourceObservation`. A blank or absent key part, a missing
  bitemporal field, or a record without an instrument mapping is refused naming the
  offending field; no observation is emitted (FM-2, FM-6, DEC-0109, DEC-0117).
- **Auto-recovery / retry:** none automatic; retryability is `no`. Supply the missing
  field or a valid `(venue, opaque-symbol)` instrument mapping and retry the bounded
  call.
- **Visible degraded state:** none; the ledger is unchanged and no CT-10 value exists
  for the bad record.
- **Notification tier:** silent-log (caller wiring / provider payload shape).
- **Product-user affordance:** incomplete or unmapped source material never becomes
  governed evidence. Fix the provider payload or the instrument map and re-fetch.

### FR-47: An unavailable or rate-limited source fabricates no observation (AC5)

- **Failure class:** `transient venue failure` (rate-limit) or `unavailable dependency`
  (source down) — returned by the injected `ExternalSourcePort`, propagated unchanged
  by `ExternalSourceIngest.fetch_and_intake`.
- **Detection:** the port returns a typed refusal; ingest emits no `ProviderRecord`
  and writes nothing to the intake ledger (FM-1, DEC-0109, DEC-0135). A read-only
  `source` presented as a `VenueId` is separately refused as `policy rejection`
  (`signal: refuse-source-as-venue`; FM-7, DEC-0117).
- **Auto-recovery / retry:** category-dependent — rate-limit may carry
  `after-condition`; unavailable dependency is typically retryable once the provider
  recovers. The application owns the retry loop (DEC-0119).
- **Visible degraded state:** no fabricated tick or news observation enters CT-10.
- **Notification tier:** operator-visible for sustained outages; silent-log for a
  single rate-limit hop the application will retry.
- **Product-user affordance:** a source outage fails closed. Wait / retry under
  application supervision; never treat silence as a fresh empty market.

### FR-48: Asking ingest to own a scheduler, daemon, or retry loop is refused (AC6)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `qmf.data.ingest.refuse_schedule_ownership` and
  `ExternalSourceIngest.start_scheduler` / `run_daemon` / `run_retry_loop` always
  refuse with `signal: refuse-schedule-ownership`. The seam is a called CT-15 port;
  scheduling, retries, supervision, and UI stay application-owned (FM-5, DEC-0119,
  DEC-0051).
- **Auto-recovery / retry:** none — schedule ownership is a governance mistake. Drive
  each bounded `fetch_and_intake` from application/ops cron or supervision instead.
- **Visible degraded state:** none; no downloader thread or daemon starts.
- **Notification tier:** operator-visible (a caller attempted to put lifecycle inside
  the library).
- **Product-user affordance:** ingest will not install a poller or background retry
  loop. Wire your own scheduler to call the seam for each bounded window.

### FR-49: A duplicate intake key is idempotent; a new revision is a new artifact (AC2)

- **Failure class:** not a failure — designed idempotent success
  (`IntakeOutcome.IDEMPOTENT`) or a distinct produced artifact for a new revision.
- **Detection:** `ExternalSourceIngest.intake` keys the in-process ledger on
  `IntakeKey(source, source_native_id, revision)`. A re-arrival under the same key
  returns the prior observation (never an erase or silent merge). A new `revision`
  mints a distinct CT-10 `fp1` (and may set `correction_of`); it is never treated as
  an fp1 collision (FM-3, DEC-0119, DEC-0108).
- **Auto-recovery / retry:** not applicable; re-submitting the same key is safe.
- **Visible degraded state:** none; earlier evidence remains readable and unchanged.
- **Notification tier:** silent-log for idempotent hits; normal for new revisions.
- **Product-user affordance:** replaying a provider page or a correction under a new
  revision is safe — duplicates collapse, corrections append.

Story 6.2 delivers bid/ask preservation and source-disagreement edges
(`TickQuote`, `relate_source_facts`, `link_revision`) — FR-50 through FR-52.

### FR-50: Collapsing bid/ask into a mid is refused (AC1)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `TickQuote.try_create` / `refuse_mid_merge` / ingest
  `_resolve_optional_tick_quote` refuse any presented `mid` with
  `signal: refuse-mid-merge`. Bid and ask stay separate scaled integers with their
  source timestamps; mid is never evidence on this seam (DEC-0119, DEC-0105). A
  tick record with only one of bid/ask is `invalid input`.
- **Auto-recovery / retry:** none — supply both sides and never a mid. Derive mid
  elsewhere under lineage if a consumer needs it.
- **Visible degraded state:** no tick quote is minted; the intake ledger is unchanged.
- **Notification tier:** silent-log (caller/payload shape).
- **Product-user affordance:** the platform will not store a blended mid as tick
  evidence. Keep bid and ask (and their timestamps) and re-submit.

### FR-51: Source disagreement is edged, never averaged (AC2)

- **Failure class:** not a failure — designed `corroborates` / `disagrees-with`
  `CausalEdge` values (CT-07-shaped) when two distinct sources report the same fact.
- **Detection:** `relate_source_facts` requires two `TickObservation` values from
  different sources sharing instrument + event-time. Matching bid/ask (+ present
  timestamps) yields `corroborates`; any difference yields `disagrees-with`. Both
  observation fingerprints remain; nothing is merged (FM-3, DEC-0119). Same-source
  or different-fact pairs are `invalid input`.
- **Auto-recovery / retry:** not applicable for the edge itself; fix wiring if the
  pair is refused as not-the-same-fact.
- **Visible degraded state:** none — both source observations stay inspectable.
- **Notification tier:** silent-log.
- **Product-user affordance:** conflicting feeds stay visible as lineage edges; the
  framework never picks a blended number for you.

### FR-52: A revision link requires a distinct new artifact (AC3)

- **Failure class:** `invalid input` when the pair is not a true revision.
- **Detection:** `link_revision` requires the same `(source, source-native id)`, a
  different `revision`, and distinct observation `fp1`s, then emits a `supersedes`
  edge (newer → earlier). Same revision or a different intake key is refused —
  evidence is never overwritten (DEC-0119, DEC-0108).
- **Auto-recovery / retry:** mint the later revision under a new revision token (and
  optionally `correction_of`) and link again.
- **Visible degraded state:** earlier evidence remains; no in-place edit occurs.
- **Notification tier:** silent-log.
- **Product-user affordance:** corrections append as new artifacts linked by
  lineage; the original quote stays readable forever.

Story 6.3 delivers the Dukascopy download-once historical tick adapter
(`COMP-DUKASCOPY` / `DukascopyAdapter`) — FR-53 through FR-56.

### FR-53: An unlicensed window cannot become governed evidence (AC2)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `offer_for_governed_evidence` requires a `LicensedSourceWindow`
  whose `LicenseTag` grants use (`internal-only` or `redistribution-ok`). Tags
  `denied`, `unknown`, or blank resolve to a refusal with
  `signal: refuse-unlicensed-window` (DEC-0166, DEC-0170). Intake may still catalogue
  the window; governed-evidence citation is what fails closed.
- **Auto-recovery / retry:** none automatic; record an authorizing usage right and
  re-offer. Retryability is `no`.
- **Visible degraded state:** the window remains catalogable for non-evidence use;
  no silent promotion into governed evidence.
- **Notification tier:** operator-visible when a run cites an unlicensed window.
- **Product-user affordance:** personal-use Dukascopy windows tagged `internal-only`
  pass; an untagged or denied window never quietly backs a claim.

### FR-54: Malformed bi5 / missing bounds / unmappable symbol are refused (AC3)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** `decode_bi5_ticks` refuses non-LZMA or truncated frames;
  `DukascopyAdapter.fetch` refuses missing `start_ns`/`end_ns` and symbols absent
  from the CT-03 instrument map — no `ProviderRecord` is emitted (FM-2, DEC-0109).
- **Auto-recovery / retry:** none; supply a valid bounded window and a mapped
  instrument. Retryability is `no`.
- **Visible degraded state:** none; the intake ledger is unchanged.
- **Notification tier:** silent-log (caller / payload shape).
- **Product-user affordance:** broken provider bytes and unmapped symbols never
  become CT-10 evidence. Fix the fixture or the instrument map and re-fetch.

### FR-55: Complete-corpus / oversized factory downloads are refused (AC4)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `refuse_complete_corpus_download`,
  `DukascopyAdapter.download_complete_corpus`, `bounds.complete_corpus=true`, and
  windows longer than `FACTORY_MAX_WINDOW_NS` refuse with
  `signal: refuse-complete-corpus`. No donor `dukascopy-node` code enters the tree;
  only bounded adapter evidence is permitted in this pass (FM-5, DEC-0051, DEC-0166).
- **Auto-recovery / retry:** none — shrink the window or run the install/runbook
  path outside this factory pass.
- **Visible degraded state:** no transport calls are made for refused bulk asks.
- **Notification tier:** operator-visible (caller attempted a corpus pull).
- **Product-user affordance:** use a bounded `[start_ns, end_ns)` under the
  factory max; bulk history stays an installation action.

### FR-56: External recovery / checkpoint / retry ownership are refused (AC5)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `refuse_external_recovery` and
  `DukascopyAdapter.checkpoint` / `recover_external` / `run_retry_loop` always
  refuse with `signal: refuse-external-recovery`. An unavailable transport
  propagates as `unavailable dependency` with no fabricated ticks (FM-1,
  DEC-0051, DEC-0119).
- **Auto-recovery / retry:** application-owned. QMF does not require the provider
  to recover and does not install a checkpoint supervisor.
- **Visible degraded state:** no fabricated observations; prior evidence unchanged.
- **Notification tier:** operator-visible for sustained source outages.
- **Product-user affordance:** drive each bounded fetch from application
  supervision; on outage, retry under your own checkpoint — not inside qmf-data.

Story 6.4 delivers the news-calendar feed as a governed CT-15 source
(`COMP-CALENDAR-FEED` / `CalendarFeedAdapter`, `CalendarFeedImport`) — FR-57
through FR-60.

### FR-57: A failed refresh / unknown coverage / missing exposure fails closed (AC4)

- **Failure class:** visible degradation journaled as CT-13 `data quality` (not a
  silent success); underlying provider outages surface as `unavailable dependency`
  / `transient venue failure` before the import folds them into fail-closed.
- **Detection:** `CalendarFeedImport.run` on transport refusal, `coverage_known=False`,
  or a missing key in `currency_exposures` when `require_exposures_for` is set builds
  a `FailClosedSignal` (`failed-refresh` | `unknown-coverage` |
  `missing-currency-exposure`) with `treated_as_affected=True` and `alarm=True`, then
  journals it via `journal_fail_closed` (SCN-0008, DEC-0152, FM-4).
- **Auto-recovery / retry:** none inside qmf-data. The standalone recorder owns
  retry/backoff; downstream CT-31 treats the instrument as affected until a healthy
  refresh and declared exposures restore coverage. Retryability of the *provider*
  refusal follows the transport; the fail-closed signal itself is not a live skip.
- **Visible degraded state:** no fabricated calendar observations; prior evidence
  unchanged; treated-as-affected downstream (blocks new entries at CT-31).
- **Notification tier:** alarm (payload `alarm: true`).
- **Product-user affordance:** a missed or uncertain news feed is never permission to
  trade. Fix the refresh / declare currency-exposure records / restore coverage;
  there is no live skip button (`refuse_live_skip`).

### FR-58: Asking for a live skip around calendar fail-closed is refused (AC4)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `refuse_live_skip` and `CalendarFeedAdapter.live_skip` always refuse
  with `signal: refuse-live-skip` and `treated_as_affected: true` (DEC-0152).
- **Auto-recovery / retry:** none — operator control is upstream configuration
  between sessions, never a click.
- **Visible degraded state:** fail-closed posture unchanged.
- **Notification tier:** operator-visible.
- **Product-user affordance:** you cannot click past a failed calendar refresh;
  configure exemptions as dated fingerprinted records consumed at compile time.

### FR-59: Minting a QMX severity scale over impact labels is refused (AC2)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `refuse_minted_severity_scale` and
  `CalendarFeedAdapter.mint_severity_scale` refuse with
  `signal: refuse-minted-severity`. Provider `impact` strings stay verbatim on
  `CalendarEvent.impact_label` (DEC-0152, DEC-0156).
- **Auto-recovery / retry:** none — severity-to-window is a declared node mapping
  outside this feed.
- **Visible degraded state:** none; evidence still carries the provider label.
- **Notification tier:** silent-log.
- **Product-user affordance:** High/Medium/Low (or any provider token) is stored as
  received; QMX does not invent its own severity ladder in V1.

### FR-60: Claiming operational retention authorization is refused (AC5)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `refuse_authorized_retention_claim` and
  `CalendarFeedAdapter.claim_retention_authorized` refuse with
  `signal: refuse-authorized-retention` and
  `legal_archiving_posture: open-operator-item`. Every import receipt and
  data-quality payload records that open posture — never an authorizing claim
  (FM-3, DEC-0119, DEC-0052).
- **Auto-recovery / retry:** none — the operator resolves legal archiving outside
  QMF.
- **Visible degraded state:** ingest may still run; retention is not attested as
  authorized.
- **Notification tier:** operator-visible when a caller asserts authorization.
- **Product-user affordance:** archiving the feed does not mean QMF licensed
  long-term retention; that remains an open operator item.

