# qma-daemon — failure register

Failure-register entries for `qma-daemon`, per the workspace convention
(`conventions/failure-register.md`, NFR-Q15). One entry per designed failure
mode, written for someone who was not in the design room. Epic 42 opens this
register: Story 42.1 delivers the sole-writer persistence substrate (FR-1,
FR-2); Story 42.2 delivers the authoritative journal, closed store list, and
announcement law (FR-3 through FR-5); Story 42.3 delivers durable-clock and
fold-contract enforcement (FR-6 through FR-9).

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

### FR-6: Host-local time reads and worker-authored evidence timestamps are refused

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `refuse_host_local_time` / `refuse_worker_evidence_timestamp`
  and `DaemonClock.stamp_durable` / `stamp_evidence_record` /
  `AuthoritativeJournal.append_event` refuse any host-local time path and any
  worker-supplied evidence timestamp; durable stamps come only from the injected
  qmf-core clock (FR-Q25; AD-6).
- **Auto-recovery / retry:** none — callers must obtain time through the daemon
  clock facade.
- **Visible degraded state:** no durable row is written with a worker or host
  stamp; existing evidence is unchanged.
- **Notification tier:** operator-visible (caller / worker wiring bug).
- **Product-user affordance:** workers do not stamp evidence and components do
  not read the host clock. The daemon records `occurred_at` and `recorded_at`.

### FR-7: Wall-clock policies without a resolvable IANA zone are refused

- **Failure class:** `invalid input` (CT-04).
- **Detection:** `DaemonClock.wall_clock_policy` / `WallClockPolicy.resolve_zone`
  require a non-empty IANA zone that resolves in the tz database at evaluation
  time (FR-Q25; AD-6).
- **Auto-recovery / retry:** none — correct the zone name on the policy.
- **Visible degraded state:** the policy is not applied; no civil-time decision
  is taken under an implied host zone.
- **Notification tier:** operator-visible (misconfigured quiet hours / cron /
  rollup / ledger date index).
- **Product-user affordance:** every wall-clock policy must name its timezone
  explicitly (for example `America/New_York`). Host local time is never implied.

### FR-8: A fold outside the ratified v1 list is refused

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `FoldContractRegistry.register` /
  `AuthoritativeJournal.register_fold` accept only the AD-6 v1 fold ids; filtered
  projections (`per_scope_event_streams`, `ledger_quarantine_stream`) are not
  folds and cannot register a contract (FR-Q25; AD-6).
- **Auto-recovery / retry:** none — a new fold requires a spine amendment.
- **Visible degraded state:** no fold contract is committed; existing registered
  folds are unchanged.
- **Notification tier:** operator-visible (configuration / plugin error).
- **Product-user affordance:** only the ratified v1 folds may be exposed. Adding
  a fold is an architecture change, not a runtime declaration.

### FR-9: Announcement-bound evidence missing `journal_seq` is refused at stamp

- **Failure class:** `invalid input` (CT-04).
- **Detection:** `DaemonClock.stamp_evidence_record` with
  `announcement_bound=True` requires a positive announcement `journal_seq`;
  telemetry (`announcement_bound=False`) refuses an embedded `journal_seq`
  (FR-Q25; AD-6, AD-23).
- **Auto-recovery / retry:** none — allocate `journal_seq` via the authoritative
  journal announcement path first, or stamp telemetry without it.
- **Visible degraded state:** the evidence mapping is not stamped.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** announcement-bound evidence always carries its
  journal sequence; telemetry carries times only.
