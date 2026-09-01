# qma-daemon — failure register

Failure-register entries for `qma-daemon`, per the workspace convention
(`conventions/failure-register.md`, NFR-Q15). One entry per designed failure
mode, written for someone who was not in the design room. Epic 42 opens this
register: Story 42.1 delivers the sole-writer persistence substrate (FR-1,
FR-2); Story 42.2 delivers the authoritative journal, closed store list, and
announcement law (FR-3 through FR-5); Story 42.3 delivers durable-clock and
fold-contract enforcement (FR-6 through FR-9); Story 42.4 delivers store-class
ownership and the governed variable registry (FR-10 through FR-13); Story 42.5
delivers versioned-store migration, backup, and controlled restoration (FR-14
through FR-17).

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

### FR-10: An unknown AD-8 store class has no ownership row

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `StoreOwnershipRegistry.get` / `assert_complete` accept only
  the eight FR-Q26 classes (journal, ledger, memory, knowledge, artifacts,
  context, telemetry, staging); each row requires writer, crossing, and
  retention, with context invocation-only (FR-Q26; AD-8).
- **Auto-recovery / retry:** none — inventing a store class is a spine change.
- **Visible degraded state:** no ownership rule is handed out.
- **Notification tier:** operator-visible (miswired persistence class).
- **Product-user affordance:** only the eight ratified store classes own state.
  Context is never durable; journal, ledgers, artifacts, staging, and ledger
  quarantine keep durable posture.

### FR-11: A definition-store change outside RefinementProposal / hook exception is refused

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `accept_definition_store_proposal` accepts only closed AD-22
  edit kinds (no `variable`); `ProposalGate.promote_refused` refuses promote;
  `register_mission_scoped_hook_exception` allows only
  `before_hook_register` observe-or-deny Mission hooks (FR-Q26; AD-8, AD-11,
  AD-22).
- **Auto-recovery / retry:** none — stage a RefinementProposal or use the sole
  Mission-scoped hook exception.
- **Visible degraded state:** no definition-store write occurs.
- **Notification tier:** operator-visible (agent / plugin attempt).
- **Product-user affordance:** agents propose refinements; operators apply them.
  Promote is a human live-zone act outside QMA.

### FR-12: `variable.set` is refused for uneditable, record-homed, or non-operator callers

- **Failure class:** `policy rejection` / `OperatorPrincipalRequired` (CT-04).
- **Detection:** `GovernedVariableRegistry.variable_set` requires an `operator`
  principal via AD-24 human-gate authorization, refuses `uneditable` and
  record-homed rows, and records a `variable.set` journal event only on success
  (FR-Q36; AD-24, AD-26).
- **Auto-recovery / retry:** none — use the owning record's operator write
  command for record-homed values, or present an operator principal.
- **Visible degraded state:** registry values and journal unchanged.
- **Notification tier:** operator-visible (unauthorized or illegal set).
- **Product-user affordance:** only an operator sets registry-homed variables.
  Record-homed values move with their record; uneditable rows are constants.

### FR-13: Agent / hook / Role / Mission configuration writes are refused

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** there is no `variable` `RefinementEditKind`;
  `refuse_non_operator_route` and proposal validation refuse every non-operator
  configuration-write path (FR-Q36; AD-26).
- **Auto-recovery / retry:** none — configuration changes go through
  `variable.set` (registry-homed) or the owning record's operator command.
- **Visible degraded state:** no value change; no alternate write path opens.
- **Notification tier:** operator-visible (agent / automation attempt).
- **Product-user affordance:** agents cannot edit operating limits. Operators
  own every registered number's write path.

### FR-14: Unknown or newer `store_schema_version` refuses open

- **Failure class:** `storage failure` / `StoreVersionMismatch` (CT-04).
- **Detection:** journal marker and SQLite `daemon_meta.store_schema_version`
  are validated at `PersistenceSubstrate.open` / `SingleSqliteWriter.start`
  before records are read; a stamp other than the known version is refused,
  naming the store and both versions (FR-Q37; AD-27; FM-17).
- **Auto-recovery / retry:** none — never read optimistically and never
  silently upgrade; run a five-step migration into a distinct destination.
- **Visible degraded state:** the substrate never opens; no durable reads or
  writes proceed against the mismatched store.
- **Notification tier:** operator-visible (startup / open refusal).
- **Product-user affordance:** this store's schema is newer or unknown to this
  daemon build. Restore from backup or migrate with the matching build.

### FR-15: In-place migration of the only copy is refused

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `DaemonStoreLifecycle.migrate` requires a destination root
  distinct from the source (documented restore path) and runs preflight →
  backup first → dry-run → migrate → verify in order (FR-Q37; AD-27).
- **Auto-recovery / retry:** none — choose a distinct migrate destination.
- **Visible degraded state:** source store untouched; no migrate write occurs.
- **Notification tier:** operator-visible (ops / migration tooling).
- **Product-user affordance:** migrations never rewrite the only copy. Back up
  first, migrate into a replacement root, then verify.

### FR-16: Sample/full restore into the live store is refused

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** sample-restore and full-restore rehearsal require a scratch
  root distinct from the live root and cite only
  `registry:store.sample_restore_test_cadence` /
  `registry:store.full_restore_rehearsal_cadence` (FR-Q37; AD-27).
- **Auto-recovery / retry:** none — point scratch at an isolated location.
- **Visible degraded state:** live store untouched; no recoverability claim.
- **Notification tier:** operator-visible (ops / rehearsal tooling).
- **Product-user affordance:** rehearsals restore into scratch and record
  verified evidence. Live restore is a separate operator act.

### FR-17: Live-store restore from a machine principal or background job is refused

- **Failure class:** `OperatorPrincipalRequired` / `policy rejection` (CT-04).
- **Detection:** `DaemonStoreLifecycle.restore_live` authorizes
  `store.restore_live` as an AD-24 human-gate command, refuses
  `as_background_job=True`, and records a `store.restore_live` journal event
  on success (FR-Q37; AD-24, AD-27). GAP-0088 deferred items stay exclusions.
- **Auto-recovery / retry:** none — present an operator principal over the
  wire; never schedule live restore as a daemon job.
- **Visible degraded state:** live store unchanged; no restore receipt.
- **Notification tier:** operator-visible (unauthorized restore attempt).
- **Product-user affordance:** only an operator restores the live store, and
  the act is journaled. Background automation cannot do it.
