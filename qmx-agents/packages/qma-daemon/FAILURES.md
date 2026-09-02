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
through FR-31). Epic 45 Story 45.6 adds daemon-resolved evidence handles
and StrategyHandle candidate artifacts (FR-32 through FR-35). Epic 45
Story 45.7 adds content-addressed ExperimentSpec identity, append-only
CT-07 lineage, and Experiment Ledger authorship (FR-36 through FR-39).
Epic 45 Story 45.8 adds the single QMB backtesting door: one analysis-backtest
Tool Registry entry, one ``qmb`` job per environment, recorded-evidence
replay only, and no package-import edge (FR-40 through FR-43). Epic 45
Story 45.9 adds the deployment envelope: workstation Docker workers, remote
dial-out only, trading-node host-identity refusal, computer-use exclusion,
and read-only dev/paper except the dev-zone candidate (FR-44 through FR-47).
Epic 46 Story 46.1 adds the Task-owned Task Ledger under ``dispatch_lease``
(FR-48 through FR-50). Epic 46 Story 46.2 adds ``before_ledger_append`` as a
validating gate that never discards evidence (FR-51 through FR-53).

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

### FR-32: A plugin or invented handle kind is refused

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `EvidenceHandleService.mint` / `register_plugin_handle_kind`
  accept only the six closed `qma-core` kinds. `DaemonPluginContext.register_handle_kind`
  and a plugin contribution point `handle_kind` are refused (FR-Q53; AD-14).
- **Auto-recovery / retry:** none — extending handle kinds is a spine
  amendment, never a plugin contribution.
- **Visible degraded state:** no handle is minted; no plugin binding is
  stored.
- **Notification tier:** operator-visible (plugin load / mint refusal).
- **Product-user affordance:** that handle kind is not in the closed set.
  Plugins cannot add one.

### FR-33: A live or writable money-path handle is not minted

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** mint refuses an open order, open position, binding, Book,
  seat, BMS record, control action, kill switch, or venue session target,
  and refuses `live` or `writable` flags. `TradeLogHandle` and
  `MarketDataHandle` additionally require recorded, closed, read-only
  evidence (FR-Q53; CT-47; SCN-0014).
- **Auto-recovery / retry:** none — those records are not handleable.
- **Visible degraded state:** no handle exists; agents cannot address the
  live money-path record.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** QMA handles recorded evidence only. Open
  orders, positions, Books, and venue sessions have no handle.

### FR-34: A money_path_relevant approval lacks the named field-level diff

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `emit_approval_request` refuses a `money_path_relevant`
  candidate whose payload is missing, unnamed, or not exactly the touched
  risk/sizing/exit/protection/binding/priority fields under
  `qma.wire.money_path_field_diff.v1`. Creating a candidate that would fill
  an unset money-path field is refused at write (FR-Q53; DEC-0313).
- **Auto-recovery / retry:** none — supply the exact named diff, or leave
  unset money-path fields unset for a human.
- **Visible degraded state:** the candidate stays in the `dev` zone; no
  `approval_request` is emitted.
- **Notification tier:** operator-visible (approval-channel refusal).
- **Product-user affordance:** a candidate that touches money-path fields
  cannot go to approval without an exact field-level diff. QMA will not
  invent a missing sizing, exit, or binding value.

### FR-35: Promotion and zone transition are uncallable

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `EvidenceHandleService.promote` and `transition_zone`
  return the zone-transition refusal. StrategyHandle writes only the
  existing `dev` zone and mints no promotion command (FR-Q53; L17).
- **Auto-recovery / retry:** none — a human promotes outside QMA.
- **Visible degraded state:** the candidate remains a `dev`-zone artifact.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** QMA cannot promote or change zones. A human
  promotes the candidate outside this system.

### FR-36: A parameter change carries a git branch or code ref

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `ExperimentSpec.with_change(change="resolved_config")` refuses
  a `code_ref` and any git branch or commit used as `resolved_config_ref`.
  `code_ref` is admitted only as `git:commit:<40-hex>` on a code change
  (FR-Q54; CT-47; DEC-0376).
- **Auto-recovery / retry:** none — identify the change with a resolved-config
  `fp1`, or mint a code-change spec with a git commit object id.
- **Visible degraded state:** no successor spec is stored; the predecessor is
  unchanged.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** parameter sweeps are not git branches. Change
  the resolved config, or commit code and cite that commit.

### FR-37: An ExperimentSpec is mutated in place

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `ExperimentSpecService.mutate_in_place` always refuses.
  Successors are new `fp1` records; CT-07 `branches-from` edges append to the
  lineage stream and never rewrite either spec (FR-Q54; CT-07).
- **Auto-recovery / retry:** none — construct a successor spec.
- **Visible degraded state:** stored specs and edges are unchanged.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** experiments are immutable snapshots. Record a
  new spec and a lineage edge instead of editing the old one.

### FR-38: A second Task authors the Experiment Ledger

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `append_evidence` requires the `dispatch_lease` of the Task
  that registered the Experiment. A different Task, or a different Agent than
  that lease holder, is refused. Duplicate `fp1` registration keeps the first
  author (FR-Q54; DEC-0308).
- **Auto-recovery / retry:** none — append as the registering Task's lease
  holder.
- **Visible degraded state:** the ledger is unchanged; no second author exists.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** one Experiment has one notebook author: the
  Agent holding the registering Task. Another Task cannot co-author it.

### FR-39: Typed strategy-mechanism fields on ExperimentSpec

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** construction and successor minting refuse `EntryMechanism`,
  `ExitMechanism`, `Filter`, `SessionRule`, `PositionRule`, and
  `InvalidationRule` (GAP-0085; FR-Q54).
- **Auto-recovery / retry:** none — those nouns stay with QML / qmf-registry.
- **Visible degraded state:** no spec is minted; GAP-0085 remains deferred.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** QMA records experiment identity and lineage.
  It does not decompose strategy mechanisms.

### FR-40: A second `qmb` job in one environment is refused

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `BacktestingService.submit` admits occupancy with
  `admit_qmb_job`. ExecutionEnvironment is singleton per kind, so a second
  in-flight `qmb` job for that kind is refused. CT-47 mints no new named
  variant (FR-Q55; DEC-0316).
- **Auto-recovery / retry:** none while the occupying job is queued, running,
  or unknown. After a terminal outcome the slot is free.
- **Visible degraded state:** the first job remains occupying; no second door
  invocation is issued.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** one backtest at a time per environment. Wait
  for the current `qmb` job to finish, or use a different environment.

### FR-41: A backtest that names a venue account or a non-replay world is refused

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `QmbBacktestRequest.try_create` requires `world=replay`, a
  recorded evidence reference, and no venue/account/paper/live fields
  (CT-47; SCN-0014; FR-Q55).
- **Auto-recovery / retry:** none — resubmit against recorded evidence and
  QMB replay.
- **Visible degraded state:** no `qmb` job is placed; the door is not invoked.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** QMA backtests recorded evidence in replay.
  Paper and live are venue account roles, not a sandbox for this door.

### FR-42: The Backtesting Service will not schedule, parallelise, or store QMB state

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `set_parallelism`, `append_run_ledger`, and `store_artifact`
  always refuse. QMB keeps intra-node parallelism, its run ledger, and its
  artifact contract; this service holds none of those (CT-47; FR-Q55).
- **Auto-recovery / retry:** none — those concerns stay on QMB.
- **Visible degraded state:** QMA occupancy and JobHandle records are
  unchanged; no QMB ledger line or artifact is minted here.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** QMA places one job. QMB runs the backtest.

### FR-43: A package-import edge to QMB is refused

- **Failure class:** `policy rejection` (CT-04) at the door; build-time
  `DependencyBoundaryError` on source scan.
- **Detection:** `import_qmb_package` always refuses. `assert_no_qmb_import`
  scans QMA packages, workers, and plugins for `import qmb`. Daemon
  `pyproject.toml` must not declare `qmb` (CT-47; DEC-0347; FR-Q55).
- **Auto-recovery / retry:** none — talk to QMB through the CLI or MCP door.
- **Visible degraded state:** no import is bound; the runtime door is the
  only path.
- **Notification tier:** silent-log (caller / CI).
- **Product-user affordance:** QMA does not import QMB. It invokes `qmb`
  as a program.

### FR-44: A deployed side that listens inbound or is dialed by the daemon is refused

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `DeploymentBoundary.deploy` validates the core dial-out
  declaration and the `qma-wire` remote posture. A remote that does not
  dial out, exposes an inbound listener, opens a second transport, or asks
  the daemon to dial in is refused before the environment binds
  (CT-46; AD-25; FR-Q56).
- **Auto-recovery / retry:** none — the deployed side must dial out to the
  daemon address and must not open a port.
- **Visible degraded state:** no remote environment is registered; the
  workstation Docker worker remains the ordinary placement.
- **Notification tier:** operator-visible (deployment refusal).
- **Product-user affordance:** remotes call the daemon. The daemon never
  calls them, and the deployed box has no inbound port.

### FR-45: A trading-node or credentialed host is refused by identity

- **Failure class:** `policy rejection` (CT-04) as `ProhibitedReachability`.
- **Detection:** registration of a remote workspace, research node, or
  sandbox that names the trading-node VPS, or a host carrying a trading
  credential or a running node, is refused at the reachability barrier
  (SCN-0014; AD-28; FR-Q56).
- **Auto-recovery / retry:** none — choose a host that is not the trading
  node and carries no trading credential.
- **Visible degraded state:** no QMA workload is placed on that host; the
  trading-node VPS stays untouched.
- **Notification tier:** operator-visible (registration refusal).
- **Product-user affordance:** QMA cannot run on the trading-node VPS or
  any host that holds a trading login or a running node.

### FR-46: Computer-use stays excluded while the desktop host is unprovisioned

- **Failure class:** `unavailable dependency` (CT-04) as `NoEnvironment`
  at placement; computer-use `check_fn` returns false.
- **Detection:** `DeploymentBoundary.start` never registers `desktop`.
  Computer-use tools fail availability preflight; a `desktop`
  `ComputeRequirement` returns `NoEnvironment`; Windows VPS provision is
  refused as Deferred GAP-0070 (DEC-0324; FR-Q56).
- **Auto-recovery / retry:** none in this story — GAP-0070 stays deferred.
- **Visible degraded state:** computer-use schemas never reach a model;
  Docker workers on the workstation still run.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** computer-use is not available until a
  desktop environment is registered against a provisioned host.

### FR-47: Dev and paper writes, promotion, and zone transition are refused

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `access_zone` admits read of `dev` and `paper` and the
  content-addressed `dev` candidate write. Paper writes, live access,
  `promote`, and `zone_transition` are refused. Treating paper as a
  sandbox is refused. After a human promotes outside QMA the daemon
  records only the artifact reference (AD-25; SCN-0014; L17; FR-Q56).
- **Auto-recovery / retry:** none — a human promotes outside QMA.
- **Visible degraded state:** the candidate remains in the `dev` zone;
  paper remains a real-venue account role.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** QMA can write a research candidate in
  `dev`. It cannot promote, change zones, or treat paper as a sandbox.

### FR-48: A Task Ledger append without that Task's `dispatch_lease` is refused

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `TaskLedgerStore.append` requires a named `dispatch_lease` for
  the same Task whose holder matches `authored_by`. An `environment_lease` or
  `quant_ledger_lease`, a different Task's lease, or a non-holder Agent is
  refused (CT-51; FR-Q57).
- **Auto-recovery / retry:** none — append as the Agent holding that Task's
  `dispatch_lease`.
- **Visible degraded state:** the Task Ledger is unchanged; no entry is
  written.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** Task Ledger append rights follow
  `dispatch_lease` only. Holding an environment slot or the Quant Ledger
  does not author the Task's account.

### FR-49: A non-daemon Task Ledger entry missing required authorship is refused

- **Failure class:** `invalid input` (CT-04).
- **Detection:** `parse_task_ledger_entry` requires `attempt_no`, `authored_by`
  with an Agent ref plus the owning Quant `ActorId`, and
  `model_deployment_ref`. Optional `trace_ref`, `artifact_ref`,
  `experiment_ref`, and `knowledge_ref` must be reference strings — embedded
  trace/artifact/experiment/knowledge objects are refused as shared
  semantics (CT-51; FR-Q57).
- **Auto-recovery / retry:** none — correct the entry and append again.
- **Visible degraded state:** the Task Ledger is unchanged.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** every Agent-authored line names who wrote it,
  which Quant owns the work, which model was used, and cites evidence by
  reference.

### FR-50: A worker-stamped Task Ledger `recorded_at` is refused

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `TaskLedgerStore.persist_via_wire` refuses an inbound
  `recorded_at`. The daemon stamps UTC nanoseconds from the injected
  qmf-core clock so the ledger survives the worker (FR-Q25; FR-Q57).
- **Auto-recovery / retry:** none — omit `recorded_at`; the daemon records
  it.
- **Visible degraded state:** the entry is not persisted; the worker cannot
  back-date evidence.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** workers send the work; the daemon writes the
  clock. Do not timestamp your own ledger evidence.

### FR-51: A schema-invalid or non-holder Task Ledger append is quarantined

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `before_ledger_append` (`evaluate_before_ledger_append` /
  `TaskLedgerStore.append`) refuses only a schema-invalid entry or one not
  authored by the holder of the named append right. The refused mapping is
  written verbatim to `ledger_quarantine_stream`. The first explicit denial
  materializes that projection (CT-51; FR-Q58; L39).
- **Auto-recovery / retry:** none — correct the schema or append as the
  holder of `dispatch_lease`. Daemon `reassigned` / `unknown_tail` and a
  hook-returned `ledger_entry` (`authored_by: daemon` plus the hook registry
  id) are the only lease-check exemptions and remain schema-validated.
- **Visible degraded state:** the Task Ledger is unchanged; the attempted
  entry remains inspectable on the quarantine stream; `discarded` is always
  false.
- **Notification tier:** silent-log (caller receives the typed refusal).
- **Product-user affordance:** that append was not a valid Task Ledger line.
  The attempt is kept in quarantine so nothing is lost. Fix the entry or
  wait until you hold the Task's `dispatch_lease`.

### FR-52: An incomplete TaskCompleted append refuses completion only

- **Failure class:** `policy rejection` (CT-04) of the completion transition.
- **Detection:** `TaskLedgerStore.propose_completion` writes the
  TaskCompleted append even when any of the five fields (what was done, what
  changed, evidence and artifact refs, unresolved issues, next
  recommendation) is omitted, then refuses the completion transition
  (CT-51; FR-Q58).
- **Auto-recovery / retry:** none for the transition — supply the five-field
  structured append and propose completion again. The incomplete entry stays
  on the Task Ledger.
- **Visible degraded state:** Task remains non-terminal; the incomplete
  append is on the ledger and is never discarded.
- **Notification tier:** silent-log (caller receives `completion_admitted=False`
  plus the typed refusal).
- **Product-user affordance:** the Task is not done until the five-field
  account is complete. The partial write is kept so the work is not lost.

### FR-53: A `before_ledger_append` timeout never discards the entry

- **Failure class:** designed evidence-preserving timeout (not a refusal of
  well-formed evidence).
- **Detection:** a `before_ledger_append` timeout resolves to `allow` with
  the entry recorded and annotated `hook_timeout`. Schema-invalid or
  non-holder denials still quarantine rather than drop the mapping
  (CT-51; FR-Q58; DEC-0309).
- **Auto-recovery / retry:** none — the annotated or quarantined record is
  the evidence.
- **Visible degraded state:** well-formed evidence is on the Task Ledger
  with `hook_timeout`; invalid attempts sit on the quarantine stream.
- **Notification tier:** silent-log.
- **Product-user affordance:** a slow validation hook cannot erase what the
  Agent tried to record. Look for the `hook_timeout` annotation or the
  quarantine stream.
