# qma-daemon — failure register

Failure-register entries for `qma-daemon`, per the workspace convention
(`conventions/failure-register.md`, NFR-Q15). One entry per designed failure
mode, written for someone who was not in the design room. Epic 42 opens this
register: Story 42.1 delivers the sole-writer persistence substrate (FR-1,
FR-2); Story 42.2 delivers the authoritative journal, closed store list, and
announcement law (FR-3 through FR-5).

### FR-1: A second daemon or writer is refused at the persistence boundary

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `PersistenceSubstrate.open` holds an in-process singleton gate
  and an on-disk sole-writer lock (`DaemonWriterLock`). A second open in the
  same process, or a distinct lock token on the same root, is refused before
  any alternate durable-write path is handed out (FR-Q22; AD-4, AD-6).
- **Auto-recovery / retry:** none — a second writer must not exist; stop the
  conflicting process or choose another root.
- **Visible degraded state:** the new substrate never opens; the incumbent
  sole writer continues.
- **Notification tier:** operator-visible (startup / open refusal).
- **Product-user affordance:** another daemon already owns this evidence root.
  Do not start a second writer; shut down the other process or point this one
  at a different root.

### FR-2: A fold process may never checkpoint

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `FoldSqliteReader.checkpoint` always returns a policy
  rejection; the handle is opened read-only with `query_only` (FR-Q22; AD-6).
- **Auto-recovery / retry:** none — folds rebuild read-only and never write.
- **Visible degraded state:** fold rebuild continues for reads; no checkpoint
  or write is performed.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** fold rebuilds are read-only. Checkpointing is
  owned only by the daemon's single writable SQLite connection.

### FR-3: A store outside the closed AD-6 list may not be declared

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `StoreRegistry.declare` / `AuthoritativeJournal.declare_store`
  accept only the closed projection and independent-store vocabulary; any other
  name is refused (FR-Q23; AD-6, AD-8).
- **Auto-recovery / retry:** none — extend the closed list only via a spine
  amendment, never at runtime.
- **Visible degraded state:** no declaration is committed; existing declared
  stores are unchanged.
- **Notification tier:** operator-visible (configuration / plugin error).
- **Product-user affordance:** that store name is not on the closed list. Use
  a ratified store or projection name; inventing a new store is not allowed.

### FR-4: Telemetry appends emit no journal announcement

- **Failure class:** not a refusal — designed exemption (AD-23 / FR-Q24).
- **Detection:** `AuthoritativeJournal.announce_evidence_append` for
  `telemetry_store` returns `AnnouncementOutcome(status="exempted")` without
  allocating `journal_seq` or appending (the journal must never grow with a
  bounded telemetry stream).
- **Auto-recovery / retry:** n/a — exemption is success without announcement.
- **Visible degraded state:** none; telemetry remains ordered by `recorded_at`
  and `correlation_id` alone.
- **Notification tier:** silent-log.
- **Product-user affordance:** telemetry is not journal evidence. Cross-store
  folds do not wait on telemetry announcements.

### FR-5: Announcing an unknown or non-evidence store is refused

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `announce_evidence_append` refuses a store outside the closed
  list, and refuses closed stores that are not announcement-bound evidence
  stores (ledger / artifact / staging / MemoryProvider) (FR-Q24; AD-6).
- **Auto-recovery / retry:** none — fix the caller to name a bound evidence
  store, or skip announcement for telemetry via the exemption path.
- **Visible degraded state:** no journal announcement is written.
- **Notification tier:** operator-visible (caller bug / miswired store).
- **Product-user affordance:** only ledger, artifact, staging, and admitted
  MemoryProvider appends are announced. Telemetry is exempt; other names are
  invalid announcement targets.
