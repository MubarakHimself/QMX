# qmf-data — failure register

Failure-register entries for `qmf-data`, per the workspace convention
(`conventions/failure-register.md`, NFR-11). One entry per designed failure mode,
written for someone who was not in the design room. Story 3.1 delivers the store
seam (`COMP-QMF-DATA-STORE`); these are its designed failures.

### FR-1: A store-engine failure is translated to a storage-failure refusal (AC4)

- **Failure class:** `storage failure` (a CT-04 refusal category).
- **Detection:** every engine (Parquet, DuckDB, SQLite, JSONL) wraps its library's
  exception — an `OSError` (disk full, locked, truncated), a `pyarrow` / `duckdb` /
  `sqlite3` error, a short read below the index-recorded length, a partial trailing
  JSONL line — into one normalized `StoreEngineError`. Each of the four boundaries
  (CT-11 `AppendStore`, CT-13 `JournalStore`, CT-09 `RegistryRoom`, CT-26
  `BackupInput`) catches `StoreEngineError` at the seam and calls
  `translate_engine_failure`, returning a `storage failure` typed refusal. The
  exception is **never** propagated across the package boundary, and persistence
  success is never reported on failure.
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
  `qmf.core.governed_namespace`) before touching any engine.
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

### FR-10: An empty raw artifact is refused, never stored as evidence

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** `append_raw` with no rows is refused before any bytes are written —
  empty evidence is meaningless and would otherwise store a receipt for nothing (L5).
- **Auto-recovery / retry:** none automatic; the refusal names the `rows` field. Present
  at least one row.
- **Visible degraded state:** none; nothing is stored.
- **Notification tier:** silent-log. A wiring mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a component
  tried to archive an empty artifact. Present the actual rows and retry.
