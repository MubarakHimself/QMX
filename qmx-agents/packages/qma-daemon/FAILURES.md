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
through FR-17). Epic 43 Story 43.2 adds closed Task/Mission state with
evidence-bound terminal outcomes (FR-18 through FR-21). Epic 45 Story 45.4
adds durable JobHandle operations and daemon-only Task mapping (FR-29
through FR-31).

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

### FR-18: LLM/Mission Director terminal proposal without JobHandle evidence is refused

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `validate_proposed_transition` / `apply_proposed_transition`
  refuse any proposed `done`/`failed`/`cancelled` transition; terminal
  authorship is only via `apply_job_handle_evidence` with a terminal
  `JobHandleEvidence` (FR-Q28; AD-12; L35; FM-20).
- **Auto-recovery / retry:** none — supply daemon JobHandle evidence, never an
  LLM-authored terminal.
- **Visible degraded state:** Task remains non-terminal; Mission state is
  recomputed from Tasks and stays non-terminal.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** agents can propose progress but cannot close a
  Task. Completion waits on JobHandle evidence the daemon alone applies.

### FR-19: Dispatched Task terminal transition without terminal JobHandle is refused

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `cancel_never_dispatched` refuses when the Task was
  dispatched; `apply_job_handle_evidence` requires dispatched status and
  accepts terminal outcomes only from terminal JobHandle states (FR-Q28).
- **Auto-recovery / retry:** none — wait for or record terminal JobHandle
  evidence (or resolve `unknown` explicitly).
- **Visible degraded state:** Task stays `running`/`blocked`/`unknown`; leases
  retained when handle is `unknown`.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** a started Task closes only when its job
  evidences a terminal outcome. Cancel-without-handle is only for work that
  never started.

### FR-20: JobHandle `unknown` blocks completion and holds both leases

- **Failure class:** designed degraded state (not a refusal on entry).
- **Detection:** `apply_job_handle_evidence` for `JobHandleState.UNKNOWN` maps
  the Task to `unknown`, retains `dispatch_lease` and `environment_lease`, and
  refuses further terminal outcomes until `resolve_unknown_job_handle` records
  terminal evidence (FR-Q28; AD-12; FM-6).
- **Auto-recovery / retry:** none — no component invents a terminal outcome;
  only an explicit recorded resolution clears the block.
- **Visible degraded state:** Task `unknown`; Mission containing it is
  `unknown` (never `failed`); both leases held; completion blocked.
- **Notification tier:** operator-visible (unresolved job / FM-6).
- **Product-user affordance:** the job outcome is not known. Do not treat it as
  failed; resolve the handle explicitly when evidence arrives.

### FR-21: Second terminal transition on the same Task is refused

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `validate_unique_terminal` refuses any further terminal (or
  post-terminal) transition once a Task is `done`/`failed`/`cancelled`
  (FR-Q28; AD-12).
- **Auto-recovery / retry:** none — a Task has exactly one terminal state.
- **Visible degraded state:** Task remains at its first terminal state;
  Mission aggregation unchanged by the refused attempt.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** that Task already finished. Start a new Task
  rather than rewriting the closed outcome.

### FR-22: A tool matching the act-level money-path deny-list is refused at registration

- **Failure class:** `ProhibitedMoneyPathTool` / `policy rejection` (CT-04).
- **Detection:** `ToolRegistry.register_tool` evaluates the code-declared
  act-level deny-list (families plus enumerated verbs) before `check_fn` for
  every tool kind, including a tool tagged paper-only (FR-Q42; AD-16; SCN-0014).
- **Auto-recovery / retry:** none — the deny-list is code, not a setting.
  Role, Mission, hook, toolset, `tool_adapter`, and `check_fn` cannot lift it.
- **Visible degraded state:** the tool is not stored; its schema never reaches
  a model.
- **Notification tier:** operator-visible (startup / registration refusal).
- **Product-user affordance:** that tool would submit, amend, or otherwise
  write the money path. QMA has no execution tool at any account role, paper
  included. Remove the act; do not retry under a different permission.

### FR-23: An MCP server advertising one money-path tool is refused whole

- **Failure class:** `ProhibitedMoneyPathTool` / `policy rejection` (CT-04).
- **Detection:** `ToolRegistry.register_adapter` / `register_mcp_server`
  passes every advertised tool through the same deny-list; one match refuses
  the adapter and binds none of its tools (FR-Q42; AD-16).
- **Auto-recovery / retry:** none — fix the server's advertised set.
- **Visible degraded state:** the MCP server is unbound; no partial catalog.
- **Notification tier:** operator-visible (startup / adapter registration).
- **Product-user affordance:** that MCP server advertised a prohibited
  trading act. Unbind it entirely; a partial server is not installed.

### FR-24: A money-path write through the parent-library surface is refused

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `ParentSurfaceGate.attempt_write` / `attempt_zone_transition`
  refuse binding, Book, BMS, seat, control-action, exit, protection, priority,
  and promotion records and every zone transition. The sole admitted write is
  a content-addressed candidate in the existing `dev` zone (FR-Q42; AD-2).
- **Auto-recovery / retry:** none — QMA mints no promotion command and no
  money-path value. A human promotes outside QMA.
- **Visible degraded state:** no money-path record is written; no zone
  changes.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** QMA may only stage a content-addressed
  candidate in the `dev` zone. Binding, sizing, protection, and promotion
  stay with the trading node and a human.

### FR-25: An incomplete or invented ExecutionEnvironment declaration is refused at registration

- **Failure class:** `ProhibitedReachability` / `policy rejection` (CT-04).
- **Detection:** `ExecutionEnvironmentRegistry.register` / `register_declaration`
  require the CT-46 surface (kind, provider ref, image, mounts, env-var
  allowlist, capabilities, required `network`, lifecycle). Invented kind or
  lifecycle values, a missing provider ref, and a container image without a
  name are refused before the binding is stored (FR-Q48; AD-17).
- **Auto-recovery / retry:** none — correct the declaration; the registry
  stays empty for that kind.
- **Visible degraded state:** the environment is unbound; placement of that
  kind returns `NoEnvironment`.
- **Notification tier:** operator-visible (declaration write / startup).
- **Product-user affordance:** that environment record is not a closed
  `ExecutionEnvironment`. Use one of the six kinds and `ephemeral` or
  `persistent`; do not invent a lifetime or skip the required `network`.

### FR-26: A shared dirty filesystem is refused at registration

- **Failure class:** `ProhibitedReachability` / `policy rejection` (CT-04).
- **Detection:** a mount that is both `shared` and writable (`rw`) is refused
  by `validate_declaration_surface` during registration. Docker-per-worker
  ephemeral is the ordinary worker and ships no shared writable mounts
  (FR-Q48; AD-17).
- **Auto-recovery / retry:** none — drop the shared writable mount or make
  it read-only.
- **Visible degraded state:** the environment is not bound; no worker
  inherits leftover files from another worker.
- **Notification tier:** operator-visible (declaration write).
- **Product-user affordance:** workers do not share a dirty filesystem.
  Ordinary Docker workers are one container per worker and ephemeral.

### FR-27: An environment-variable allowlist used as a control channel is refused

- **Failure class:** `ProhibitedReachability` / `policy rejection` (CT-04).
- **Detection:** `environment_allowlist` must be declared env-var names.
  Assignments (`NAME=value`) and control-channel names (`QMA_CONTROL_CHANNEL`
  and kin) are refused at registration (FR-Q48; AD-17).
- **Auto-recovery / retry:** none — list names only; the allowlist is not a
  command path.
- **Visible degraded state:** the environment is unbound.
- **Notification tier:** operator-visible (declaration write).
- **Product-user affordance:** the environment allowlist names which
  variables a worker may see. It cannot carry commands, control sockets, or
  values.

### FR-28: Venue/broker/exchange/trading-node reachability is refused at registration, not by a hook

- **Failure class:** `ProhibitedReachability` / `policy rejection` (CT-04).
- **Detection:** `ExecutionEnvironmentRegistry.register` runs the AD-28
  barrier before the binding is stored. A deny-listed host, OpenRouter
  destination, forbidden image, or money-path capability is a registration
  (or placement) refusal — never a runtime hook deny (FR-Q48; SCN-0014).
- **Auto-recovery / retry:** none — Role, Mission, plugin, permission, and
  hook cannot lift the host denial.
- **Visible degraded state:** the environment never hosts work; no money-path
  act is minted.
- **Notification tier:** operator-visible (declaration write / placement).
- **Product-user affordance:** that environment would reach a venue, broker,
  exchange, trading node, or OpenRouter. QMA refuses it up front. The
  trading desk stays read-only.

### FR-29: Timeout, lost supervisor, unreachable environment, or restart is `unknown`

- **Failure class:** designed state, not a refusal (CT-46 / L35). Retry,
  assumed outcome, and inferred failure of an `unknown` job are
  `policy rejection` (CT-04).
- **Detection:** `JobHandleService.mark_unknown` / `observe_lost_certainty`
  / `JobHandle.reattach` after a lost supervisor, unreachable environment,
  timeout, or daemon restart. `abort` refuses those triggers so they cannot
  become `aborted` or `failed` (FR-Q51; DEC-0316).
- **Auto-recovery / retry:** none — `retry`, `infer_failure`, and
  `assume_outcome` are refused; the job holds its `environment_lease` until
  an explicit recorded resolution.
- **Visible degraded state:** JobHandle and Task are `unknown`; the slot
  stays occupied; completion is blocked.
- **Notification tier:** operator-visible (human-gate `unknown.resolve`).
- **Product-user affordance:** the job's outcome is not known. Do not retry
  or assume it failed. An operator records a resolution.

### FR-30: `unknown` resolution requires an operator-principal recorded action

- **Failure class:** `OperatorPrincipalRequired` / `policy rejection` (CT-04).
- **Detection:** `JobHandleService.resolve_unknown` authorizes
  `unknown.resolve` (AD-24). A `machine` principal is refused. `recorded=False`
  is refused even for an operator (FR-Q51; DEC-0323).
- **Auto-recovery / retry:** none — no headless, scripted, scheduled, or
  agent path resolves `unknown`.
- **Visible degraded state:** the JobHandle stays `unknown` and keeps its
  slot; Task stays `unknown`.
- **Notification tier:** operator-visible (human-gate refusal).
- **Product-user affordance:** only an interactive operator can resolve an
  unknown job, and the resolution must be recorded. A worker or scheduler
  cannot.

### FR-31: Known environment/supervisor non-completion is `aborted`, not `cancelled`

- **Failure class:** designed state (CT-46). Illegal transitions after a
  terminal JobHandle are `policy rejection`.
- **Detection:** `JobHandleService.abort` records `oom_kill`,
  `container_stop`, `image_failure`, or `mount_failure` as `aborted`. The
  daemon maps `aborted` to Task `failed` with the reason on the Task Ledger
  and never to `cancelled` (FR-Q51; DEC-0316).
- **Auto-recovery / retry:** none — terminal JobHandle states are exactly
  `done`, `failed`, `cancelled`, and `aborted`.
- **Visible degraded state:** the Task is `failed` with the abort reason;
  leases are released.
- **Notification tier:** silent-log (caller receives the mapped Task state).
- **Product-user affordance:** the environment or supervisor stopped the
  job. That is not an explicit cancel. The abort reason is on the Task.
