# qmb — failure register

Failure-register entries for `qmb`, per the workspace convention
(`conventions/failure-register.md`, NFR-11). Story 15.3 delivers orchestrator
cancel tokens and declared per-run limits whose breach is a typed `aborted`
refusal (AR-51, B-5, FM-6). Story 15.4 delivers the one-ledger-line law over
WriterId-scoped JSONL fragments (AR-51, AR-53, B-4). Story 15.5 delivers
per-run AD-14 operational logs streamed by the orchestrator (B-4, AR-35,
CT-11). Story 16.2 delivers CLI refusal rendering: a typed refusal is
RETURNED by the library and rendered by the door as a nonzero exit plus
machine-readable stderr JSON (AR-58, CT-04). Story 16.3 delivers the Python
API door as a thin in-process re-export: refusals return verbatim, never
raised, and a direct library call writes no governed evidence (B-1, B-4,
AR-58). Story 16.4 delivers registry-enumeration autocomplete through the
one B-15 registry-read port: click native ``shell_complete``, never a
door-side cache, never a live service query. Story 16.5 delivers the
tier-2 door-parity contract test: identical function surface and
semantics across the shipped CLI and Python API doors, with per-transport
refusal rendering (CLI nonzero + stderr JSON; Python refusal union
verbatim). Story 16.6 scaffolds the MCP door as an unshipped sibling
over the same library: localhost-bound, never stacked over HTTP,
invocation is a typed ``unsupported capability`` refusal, and
``error.data`` is pinned to carry the refusal union verbatim when the
door later ships. CLI v1 does not wait on it. Story 18.1 delivers
``qmb data download`` as a thin front over CT-10/CT-15 with Dukascopy
adapter #1, typed provider refusals, and the runs-never-fetch policy.
Story 18.2 delivers the ship-no-corpus licensing gate: a pure read-time
check that turns each window's recorded licence tag into
value-or-typed-refusal for governed-evidence use, carries granting
authority into CT-07 lineage on pass, and asserts the wheel bundles
zero corpus bytes. Story 18.3 delivers ``qmb data list`` / ``catalog``
as a rebuildable DuckDB coverage view over Parquet rooms. Story 18.4
delivers ``qmb data verify`` window integrity: bid/ask presence,
monotonic int64 UTC-ns timestamps, exact scaled-integer prices, a
configurable unarmed-by-default edge guard, interior gaps reported
never filled, and CT-13 data-quality journaling of the factual
pass/fail verdict. Story 19.3 folds suppression and veto tallies from
the run's CT-13 journal streams into the CT-32 artifact; an unresolvable
authority or reason is a typed refusal, never a dropped or bucketed event.
Story 19.5 delivers pure downstream reads of that stored artifact: HTML and
markdown are token substitution only, interpretation skills refuse a
rendering, and re-executing a stored run id must reproduce the stored
CT-32 fingerprint or return a typed refusal.

### FR-1: Cancel or per-run limit breach aborts one OS process

- **Failure class:** `policy rejection` (CT-04), terminal `aborted`.
- **Detection:** the orchestrator watches each live child. A signalled
  `CancelToken`, elapsed monotonic time at `registry:qmb_run_time_limit`, or
  peak memory at `registry:qmb_run_memory_limit` fires the abort. The isolated
  worker also reuses in-loop `check_slice_boundary` (story 14.6) so a
  cooperative abort can land at a slice boundary; the parent still owns the
  OS-process kill when the child is past that seam or hung.
- **Auto-recovery / retry:** none. The aborted refusal is terminal
  (`retryability = no`). Re-running is a new isolated process with a new
  declared cancel token and limits.
- **Visible degraded state:** that run is dead. Its output directory remains.
  No governed IsolatedRun / CT-32 result is returned. Sibling processes keep
  running. The governor reservation is released so a queued run can admit.
- **Notification tier:** operator-visible typed refusal (category, cause,
  `time_limit_key` / `memory_limit_key`, pid, run id, output dir).
- **Product-user affordance:** this run stopped because you cancelled it or it
  breached the time or memory limit you declared for it. Nothing else was
  killed. There is no partial scoreboard row from this run; look in that run's
  directory for leftover files. Start a new run if you still want the work.

### FR-2: Aborting one run must not take siblings with it

- **Failure class:** `policy rejection` for the aborted run only.
- **Detection:** `abort_run` / the collect watchdog call `kill` on that
  `Popen` only (`start_new_session=True` so the child is its own group).
- **Auto-recovery / retry:** none for the aborted run. Siblings are collected
  as if the abort had not happened to them.
- **Visible degraded state:** one run directory holds an aborted process's
  leftovers; sibling directories continue to receive that sibling's writer and
  result files.
- **Notification tier:** operator-visible on the aborted run; siblings stay
  quiet unless they independently abort.
- **Product-user affordance:** killing run A never kills run B. If a batch
  returns `aborted`, check the other run directories — they were not reaped.

### FR-3: An aborted run never emits a partial governed result

- **Failure class:** `policy rejection`, `partial_governed_result=false`.
- **Detection:** the abort path returns a typed refusal and does not construct
  `IsolatedRun`. `result.json` is not required and is never treated as a
  CT-32 success after an OS kill.
- **Auto-recovery / retry:** none.
- **Visible degraded state:** files stay in the run's own directory (payload,
  writer, partial child output). Direct `run()` still writes no ledger.
- **Notification tier:** operator-visible refusal context
  (`writes_ledger=false`, `writes_log=false`).
- **Product-user affordance:** an aborted run is not a half-score. Do not
  quote a CT-32 fingerprint from it. The leftovers are that run's room only.
  When the orchestrator `finish_run` path observes the abort, it also appends
  the `aborted` ledger line with refusal context (story 15.4). Direct
  `abort_run` without a ledger sink still writes no line — governed evidence
  enters only through the orchestrator ledger sink.

### FR-4: A second ledger line for the same run is refused

- **Failure class:** `policy rejection` (CT-04), alarm.
- **Detection:** `LedgerSink.append` scans the WriterId-scoped fragment for the
  run id. Byte-identical re-presentation is an idempotent accept (one line
  remains). Differing bytes under the same run id are a collision.
- **Auto-recovery / retry:** none. The first committed line is the line. Do not
  overwrite. A new run is a new resolved-config fingerprint.
- **Visible degraded state:** the fragment still has exactly one line for that
  run. The merge view does not fork.
- **Notification tier:** operator-visible typed refusal (`alarm=True`).
- **Product-user affordance:** this run already has a scoreboard row. Starting
  it again under the same resolved config does not add a second row. Change
  the config if you want another run.

### FR-5: Append-with-fsync of a ledger fragment fails

- **Failure class:** `storage failure` (CT-04).
- **Detection:** `os.fsync` / write / mkdir on the WriterId-scoped JSONL
  fragment raises `OSError`. The orchestrator returns the failure; it never
  reports a successful ledger write.
- **Auto-recovery / retry:** none automatic. The line is not committed (no LF
  + fsync). A torn tail without LF is skipped on read, never treated as a
  line.
- **Visible degraded state:** that run has no governed ledger line yet. The
  isolated run directory is untouched. Sibling slots keep their own files.
- **Notification tier:** operator-visible typed refusal.
- **Product-user affordance:** the run may have finished in its own directory,
  but it is not on the scoreboard because the ledger disk write failed. Free
  space / permissions, then re-run (a new occurrence) or retry `finish_run`
  only if the first line never landed.

### FR-6: An aborted orchestrated run must not be silently absent from the ledger

- **Failure class:** `policy rejection` for the run; the ledger write is
  required.
- **Detection:** `finish_run` collects the live process. Any refusal (cancel,
  time/memory limit, dead child) mints `role=aborted` with refusal context
  and appends it before returning.
- **Auto-recovery / retry:** none for that run. The aborted line is the
  record. Re-running is a new process.
- **Visible degraded state:** Book-bar reads (`role=confirmation`) do not see
  the aborted line. The aborted merge view does. No CT-32 fingerprint is
  stored on the aborted line.
- **Notification tier:** operator-visible typed refusal with
  `writes_ledger=true` and `aborted_line_absent=false`.
- **Product-user affordance:** cancelling or blowing a limit still leaves a
  ledger row that says the run aborted and why. It is not a pass, not a fail,
  and not missing. Direct library `run()` in research still writes no ledger.

### FR-7: A crashed run's operational log must not leave its room

- **Failure class:** operational (AD-14); not CT-11 evidence.
- **Detection:** the orchestrator injects a one-writer log sink into the run
  directory (`run.log`) at spawn. The isolated worker streams JSONL records
  with `correlation_id`. Abort or crash appends a terminal operational record
  in that same file after the child is reaped.
- **Auto-recovery / retry:** none. The partial log is the diagnostic. A new
  run is a new directory and a new `correlation_id`.
- **Visible degraded state:** that run's directory holds a partial
  operational log. Sibling run directories and WriterId-scoped ledger
  fragments are not opened. `is_evidence` stays false; artifacts still cite
  only the raw archive and the journal (CT-11).
- **Notification tier:** operator-visible file in the run directory (tail-able
  JSONL, UTC ISO-8601 `Z` timestamps). Typed abort refusals carry
  `operational_log_is_evidence=false`.
- **Product-user affordance:** you can tail this run while it lives. If it
  dies, the leftover log is only in that run's folder. It is not a scoreboard
  row and not evidence. The other runs and the ledger are intact.

### FR-8: CLI command resources or config fragments are absent

- **Failure class:** `unavailable dependency` (CT-04).
- **Detection:** each `qmb` command declares its config/resource
  prerequisites (`port`, Book/BMS fragments, run spec, slices, output root,
  and kin). `require_prerequisites` returns before `compile_run_config` or
  `spawn_run` run.
- **Auto-recovery / retry:** none. Supply the missing resource and invoke
  again. The door does not prompt, cache, or invent a default.
- **Visible degraded state:** no run-config is compiled, no process is
  spawned, no ledger line is written. The command tree is otherwise intact.
- **Notification tier:** operator-visible typed refusal (`command`,
  `missing`, `required`) rendered by the CLI door as nonzero exit plus
  stderr JSON (story 16.2).
- **Product-user affordance:** this command cannot start because a required
  Book, BMS, bot, registry-read port, or output directory was not provided.
  Point it at those resources; the CLI will not guess. A successful
  backtest still takes its run id from the compiled config fingerprint —
  never from the door.

### FR-9: CLI door renders a typed refusal as stderr JSON

- **Failure class:** the library's CT-04 category, unchanged. The door does
  not mint a second category.
- **Detection:** `_transport` sees `is_refusal` on the library `Result` and
  encodes `category`, `context`, and `retryability` (plus
  `after_condition_descriptor` when retryability is `after-condition`).
- **Auto-recovery / retry:** none at the door. Retryability is a field on
  the JSON. The door does not retry, prompt, or swallow.
- **Visible degraded state:** the process exits nonzero. stdout has no
  success payload. stderr is one JSON object. The library function that
  produced the refusal still RETURNED it — nothing was raised.
- **Notification tier:** operator- and agent-visible stderr JSON.
- **Product-user affordance:** the command did not run. Read the JSON on
  stderr — `category` says what kind of miss, `context` names the facts,
  `retryability` says whether a retry can work. Do not parse prose. A
  crash (programmer error) is still an exception, not this JSON.

### FR-10: Python API door returns a typed refusal verbatim

- **Failure class:** the library's CT-04 category, unchanged. The door does
  not mint a second category and does not render JSON.
- **Detection:** a library function invoked through `qmb.doors.api` returns
  `Ok[T] | TypedRefusal`. `is_refusal` is true; nothing is raised.
- **Auto-recovery / retry:** none at the door. Retryability is a field on
  the refusal. The door does not retry, prompt, wrap, or swallow.
- **Visible degraded state:** the caller holds the same refusal object the
  library produced. No ledger line is written. No HTTP response exists —
  this door is in-process only.
- **Notification tier:** caller-visible return value (notebooks, UI backend).
- **Product-user affordance:** the call did not succeed. Inspect `category`,
  `context`, and `retryability` on the returned object. Do not catch it as
  an exception — a crash (programmer error) is still an exception, not a
  refusal. Direct `run()` in research still produces no governed evidence.

### FR-11: Autocomplete has no registry-read port

- **Failure class:** silent empty candidate set (not a CT-04 refusal on the
  completion channel). The library's `complete_registry` returns `()` when
  `port` is missing or is not the B-15 `RegistryReadPort`.
- **Detection:** click native `shell_complete` reads the injected port from
  the CLI context and calls `complete_registry`. No port, a non-port value,
  or a blank kind filter yields no candidates. The door does not query a
  live registry and does not fall back to a cached alias list.
- **Auto-recovery / retry:** none at the door. TAB again after the
  composition root injects a port bound to the hub's current as-of set. A
  newly created Book appears only as a fresher as-of set on that hub, never
  as a cache refresh.
- **Visible degraded state:** the shell offers no Book/BMS/bot aliases.
  Commands still run. Resolution through the same port (when later injected)
  remains the compiler's answer. A frozen sweep port offers explicit `fp1`
  tokens, never aliases.
- **Notification tier:** silent on the completion channel (empty
  candidates). Domain refusal still RETURNED by `resolve` / `compile` when
  those entry points run without a port.
- **Product-user affordance:** TAB did not list Books because this CLI
  process has no registry as-of set. That is not a stale cache and not a
  network miss. Point the CLI at the registry-read port (the same one the
  compiler uses). When a new Book shows up, it arrived as a newer as-of
  set — create nothing locally to "refresh" the CLI.

### FR-12: A capability exists on one shipped door but not the other

- **Failure class:** factory-gate contract failure (B-1 door parity), not a
  new CT-04 category. The underlying library refusal, when one exists, is
  unchanged and still rendered per transport (FR-9, FR-10).
- **Detection:** the tier-2 door-parity catalog (`qmb.doors.CAPABILITY_LIBRARY`)
  is compared to the CLI command tree and to the Python API door's names.
  `capability_gaps` reports `extra_cli`, `missing_cli`, or `missing_api`.
  Any non-empty tuple fails `poe test` / `poe check-integration`.
- **Auto-recovery / retry:** none. Add the capability to both shipped doors
  (CLI command + the same library function on `qmb.doors.api`) and to the
  catalog, or remove the one-door-only surface. MCP is not in the door-set
  until it ships.
- **Visible degraded state:** the work unit does not land. Existing doors
  keep serving the catalogued capabilities. No second cache, no second
  run-id, and no swallowed refusal is introduced to "paper over" the drift.
- **Notification tier:** factory-visible pytest failure on the parity
  contract test.
- **Product-user affordance:** agents and the operator must see the same
  function surface. If `qmb` gained a command the Python API cannot call
  (or the reverse), that is a bug — do not document it as a CLI-only
  feature. Put the capability in the library once and wrap it on every
  shipped door.

### FR-13: MCP door invocation before CLI v1 ships it

- **Failure class:** `unsupported capability` (CT-04).
- **Detection:** `qmb.doors.mcp.main` / `serve` return the typed refusal
  immediately. `is_shipped()` is False. The door is not a console script
  and is not in the V1 door-set.
- **Auto-recovery / retry:** none. The door ships after CLI v1 (SC-08).
  Retrying the same invocation does not start a server. Use the `qmb` CLI
  or the Python API door.
- **Visible degraded state:** no MCP listener binds. No HTTP stack is
  imported. CLI and Python API keep serving the catalog. When a refusal
  is later rendered on this door, JSON-RPC `error.data` is the same
  category / context / retryability union the CLI writes to stderr.
- **Notification tier:** caller-visible typed refusal (return value).
- **Product-user affordance:** MCP is not a V1 product face. Run `qmb`
  (the CLI) or `import qmb`. A future MCP door will wrap the same library
  on 127.0.0.1, never over HTTP, and will put the refusal JSON in
  `error.data` rather than swallowing it as InternalError.

### FR-14: Execution binds only from the resolved run-config

- **Failure class:** `invalid input` (CT-04).
- **Detection:** `bind_execution_ports` requires a `ResolvedRunConfig` naming
  `fill_adapter`, `slippage_adapter`, `cost_adapter`, and
  `financing_schedule`. A raw mapping, a port object stuffed in a key, or an
  adapter-id outside the closed catalog is refused. There is no ambient
  discovery.
- **Auto-recovery / retry:** none. Name catalog adapter-ids on the resolved
  run-config and bind again.
- **Visible degraded state:** no ports execute. No fill is stamped.
- **Notification tier:** operator-visible typed refusal (`field` is the
  missing or unknown key, `known` lists the catalog).
- **Product-user affordance:** execution modeling is assembled from the
  wind-tunnel config, not from whatever adapter happens to be importable.
  Put `declared-path` / `zero` / `zero` plus a financing-schedule reference
  on the resolved run-config.

### FR-15: Bot-sized orders and opens without a full-loss price

- **Failure class:** `invalid input` (CT-04).
- **Detection:** `BoundExecution.execute` requires a CT-23 `EntryIntent` or
  `ExitIntent`. A raw bot-sized order is refused before any port runs. An
  entry without an AD-40 full-loss price is refused before the fill port
  is invoked. A risk-reducing CT-23 exit is admitted without a new
  full-loss price.
- **Auto-recovery / retry:** none. Mint an authorized intent through the
  Book door; derive the full-loss price at that door.
- **Visible degraded state:** no fill, slippage, or cost runs.
- **Notification tier:** operator-visible typed refusal (`field=intent` or
  the full-loss refusal from CT-23).
- **Product-user affordance:** the bot does not size. Opens need a
  Book-resolved full-loss price. Closing or tightening does not require a
  new one.

### FR-16: Mixed-fidelity Book-bar comparison without override

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `compare_book_bar_fidelity` fingerprints the two
  `RunFidelity` labels. Differing labels without `override=True` refuse
  (LABEL-3). Ordinal ranks are not invented; a deferred taxonomy artifact
  is consumed when the caller already holds one (SC-07).
- **Auto-recovery / retry:** none automatic. Pass `override=True` only when
  the operator explicitly wants the mixed comparison.
- **Visible degraded state:** the two Book-bar results stay uncompared.
- **Notification tier:** operator-visible typed refusal (`field=fidelity`).
- **Product-user affordance:** do not rank a quote-real Book against an
  optimistic-tainted one unless you say so. Until GAP-0048 every fill is
  optimistic-tainted and cannot claim edge or spend split budget.

### FR-17: world=simulated or replay-on-synthetic at composition

- **Failure class:** `policy rejection` for `world=simulated`; `invalid
  input` for a replay clock bound to synthetic-tainted data (CT-04).
- **Detection:** `bind_execution_ports` checks clock and provenance before
  looking up adapters. Store-persisted synthetic data is
  `world=simulated` and a policy rejection for governed evidence until
  GAP-0048. Replay-on-synthetic is invalid input because B-7 wins.
- **Auto-recovery / retry:** none. Use recorded or procedure-ephemeral
  provenance with a replay clock for governed replay.
- **Visible degraded state:** no port-set is bound. Optimistic-tainted
  runs still cannot claim edge or spend split budget.
- **Notification tier:** operator-visible typed refusal (`field=world` or
  `field=clock`, `gap=GAP-0048`).
- **Product-user affordance:** generated store data is infrastructure
  stress only. It is not a backtest and it is not edge. A replay clock
  cannot be pointed at synthetic-tainted rooms.

### FR-18: Missing swap table never silently zeros financing

- **Failure class:** `unavailable dependency` (CT-04).
- **Detection:** the financing scheduler requires a versioned per-broker swap
  calibration at the accounting-rollover instant (sub-phase 2). Absence of
  the artifact, or of the instrument x direction cell, is refused. The
  rollover instant is answered by the bound broker market-hours calendar;
  a hardcoded wall time is never used.
- **Auto-recovery / retry:** none. Bind a fingerprinted swap-schedule
  calibration on the resolved run-config and re-run.
- **Visible degraded state:** no rollover cash event is journaled. Multi-day
  carry is not silently free. Fill, slippage, and commission still itemize
  on their own lines.
- **Notification tier:** operator-visible typed refusal (`field` is
  `financing_schedule` or `swap_table`, `gap=GAP-0048`).
- **Product-user affordance:** overnight financing is a scheduled cash
  event, never an order fill. Triple-swap weekday, multiplier, sign, and
  weekend/holiday handling come from the broker artifact. Cost drag
  decomposes fill P&L, slippage, commission, and financing.

### FR-19: Provider error never silently partial-ingests

- **Failure class:** `transient venue failure` (rate-limit) or
  `unavailable dependency` (maintenance / geo-block / HTTP-451-class) —
  CT-04 with retryability as the provider states.
- **Detection:** the injected Dukascopy transport / provider adapter returns
  a typed refusal from `fetch`; `qmb data download` propagates it unchanged
  and admits no CT-10 observations for that call.
- **Auto-recovery / retry:** category-dependent. Rate-limit carries
  `retryability=yes` for the application to back off; geo-block /
  entitlement miss is `no` until the operator changes posture.
- **Visible degraded state:** the raw room is unchanged for the refused
  window. No half-written bid/ask stream is catalogued as complete.
- **Notification tier:** operator-visible typed refusal (signal, source,
  retryability) on the supervising agent's channel.
- **Product-user affordance:** a provider outage or geo-block stops the
  download with a typed refusal. Re-run after the provider is reachable;
  overlapping success is idempotent via the CT-15 intake key.

### FR-20: Runs never fetch from a provider

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `refuse_run_provider_fetch` — any run loop / backtest /
  sweep / optimize path that attempts a provider fetch.
- **Auto-recovery / retry:** none. Acquire through `qmb data download`
  once, then read qmf-data rooms only.
- **Visible degraded state:** the run does not start a provider call. Prior
  rooms remain readable.
- **Notification tier:** operator-visible typed refusal
  (`sole_fetch_surface=qmb data download`).
- **Product-user affordance:** experimentation runs read the archive you
  already downloaded. They never phone the provider. Use `qmb data
  download` under your own entitlement when you need a new window.

### FR-21: Unlicensed window cited as governed evidence

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** `admit_governed_evidence` — read-time licensing gate over
  the recorded licence tag. `denied`, `unknown`, blank/absent, missing
  granting authority, or a recorded tag that disagrees with the venue
  policy / operator ruling refuses. Context carries
  `(venue, symbol, window)` and the tag state.
- **Auto-recovery / retry:** none automatic. Record an authorizing licence
  tag under a venue policy or operator ruling (never an adapter
  inference), then re-admit.
- **Visible degraded state:** the window remains ingestible and
  catalogable; infra-stress and strategy-logic-smoke non-evidence use
  stay allowed. Governed-evidence citation is blocked. The gate writes
  nothing.
- **Notification tier:** operator-visible typed refusal
  (`signal=refuse-unlicensed-window` or `field=granting_authority`).
- **Product-user affordance:** you can keep the window for stress/smoke
  work, but you cannot cite it as governed evidence until a usage right
  is recorded and a granting authority (policy or ruling) stamps it.
  QMB never ships a market-data corpus in the wheel.

### FR-22: Window integrity defect on ``qmb data verify``

- **Failure class:** `policy rejection` (CT-04) with
  `signal=window-integrity-defect`.
- **Detection:** `qmb data verify` — empty provider return, missing
  requested side when `both` was asked, non-integer / float price taint,
  non-monotonic timestamps, or edge offset beyond an *armed* edge
  tolerance. Blank tolerance leaves the edge guard un-armed and reports
  raw offsets only (no invented threshold).
- **Auto-recovery / retry:** none. Re-acquire or repair the window; never
  fabricate interior fill on the verify path (synthetic fill is
  `world=simulated` / Epic 23).
- **Visible degraded state:** the factual data-quality fail is journaled
  as a CT-13 ``data quality`` event with the propagated
  ``correlation_id``. Interior gaps are listed and never filled. No
  silent pass.
- **Notification tier:** operator-visible typed refusal carrying counts
  and defect codes in context.
- **Product-user affordance:** do not build on a truncated or corrupted
  window. Re-download or choose a clean range; verify again over the
  same immutable window to reproduce the same verdict.

### FR-23: Calendar-aware gap on ``qmb data gap-check``

- **Failure class:** `unavailable dependency` (CT-04) when the CT-02
  market-hours calendar cannot be resolved; `policy rejection` when a
  fill/fabricate request is attempted (`gap=GAP-0048`).
- **Detection:** `qmb data gap-check` — resolves expected sessions from
  the versioned trading calendar (qmf-calendar-forex for FX venues),
  computes expected-bars-minus-present-bars inside open sessions, and
  reports gaps as `(start, end, expected, present)`. Calendar-closed
  absence (weekend/holiday/half-day/late-open) is closure, not a gap.
  Always-open calendars treat every non-present interior interval as a
  genuine gap. An unknown calendar is never guessed as always-open.
- **Auto-recovery / retry:** none. Supply a resolvable CT-02 calendar or
  an explicit always-open calendar for 24/7 venues; never write interior
  fill on this path (synthetic fill is Epic 23 / `world=simulated`).
- **Visible degraded state:** gaps are reported only; the calendar
  version used is recorded so the same window + version reproduces the
  same gap set.
- **Notification tier:** operator-visible typed refusal for missing
  calendar or fill attempts; successful runs emit the gap set as a value.
- **Product-user affordance:** use the gap report to decide re-download
  targets. Closures need no repair; genuine open-session holes do.

### FR-24: Unresolvable suppression or veto journal key

- **Failure class:** `invalid input` (CT-04) for an unresolvable authority
  or reason class, or a parallel bespoke log; `policy rejection` for a
  cross-world journal event.
- **Detection:** `assemble_suppression_and_veto_accounting` — a suppressed
  decision or suppressed control-action whose issuing authority is not an
  AD-36 `AuthorityKind`, whose reason class is blank/missing, or a
  `refused-by-door` event whose refusing-door identity cannot be read.
  A mapping that is not a CT-13 journal row is refused as a parallel log.
- **Auto-recovery / retry:** none. Repair the journal event so authority,
  reason, and door resolve, then re-assemble. Never drop the event and
  never bucket it under `other`.
- **Visible degraded state:** no CT-32 artifact is minted. Prior journal
  streams remain readable.
- **Notification tier:** operator-visible typed refusal (`field` names
  the unresolvable key).
- **Product-user affordance:** control-window and admission-door accounting
  cannot be completed from a journal row that does not name who suppressed
  or which door refused. Fix the event; do not invent a bucket.

### FR-25: Stored CT-32 fingerprint does not reproduce

- **Failure class:** `policy rejection` (CT-04), field `ct32_fingerprint`.
- **Detection:** `verify_stored_reproduction` re-executes the stored run id
  under its resolved run-config and compares the recomputed CT-32 `fp1`
  to the fingerprint of `results/ct-32.json`. `require_reproduced_fingerprint`
  refuses on mismatch. A missing or unreadable stored artifact is a
  `storage failure`.
- **Auto-recovery / retry:** none. A mismatch is never silently tolerated.
  Repair the inputs so the re-run matches the stored artifact, or replace
  the stored file only by assembling a new isolated run.
- **Visible degraded state:** the stored artifact is left in place. No
  size, promotion, bench, bind, or mode change is performed.
- **Notification tier:** operator-visible typed refusal (`actual` /
  `expected` fingerprints and the run id).
- **Product-user affordance:** re-running this run id did not reproduce
  the stored CT-32 fingerprint. That is a bug in inputs or a tampered
  artifact, not a rounding difference. Do not accept the new numbers.

### FR-26: Interpretation handed a rendering instead of CT-32

- **Failure class:** `policy rejection` (CT-04), field `artifact`.
- **Detection:** `explain_run` / `compare_runs` / `flag_refusal_heavy`
  (and `as_ct32_artifact`) refuse HTML or the markdown report
  (`qmb-headline`, `<html`, `# world=`). Agents never parse HTML.
- **Auto-recovery / retry:** none. Pass the stored `results/ct-32.json`
  (or the run output directory that holds it), not `report.html`.
- **Visible degraded state:** no findings are produced. The rendering
  files remain display-only.
- **Notification tier:** caller-visible typed refusal.
- **Product-user affordance:** in-house skills read the machine-readable
  CT-32 artifact. Paste the JSON (or the run directory), not the HTML
  report.

### FR-27: Headline world or account-binding role is missing

- **Failure class:** `invalid input` (CT-04), field `world` or
  `account_binding_role`.
- **Detection:** `render_tokens` / `as_ct32_artifact` require the stored
  labels verbatim. A renderer never invents `replay` or `demo`.
- **Auto-recovery / retry:** none. Restore a well-formed CT-32 artifact
  and re-render.
- **Visible degraded state:** no HTML or markdown is written. The stored
  artifact is not overwritten.
- **Notification tier:** caller-visible typed refusal.
- **Product-user affordance:** the report headline must show world and
  account-binding role unmissably. If those fields are missing, the file
  is not a CT-32 result — do not pretty-print it as live.

### FR-28: Downstream read attempts to act on the result

- **Failure class:** `policy rejection` (CT-04), field `act`.
- **Detection:** `refuse_downstream_act` — size, allocate, promote, demote,
  bench, bind, or change_mode. Rendering, interpretation, and reproduction
  are publish-only (R-RPT-9, B-10).
- **Auto-recovery / retry:** none. Acting belongs to the Book door (bench)
  or the operator (promotion), never to a report or skill.
- **Visible degraded state:** the CT-32 artifact and any HTML/markdown
  stay as published evidence. No binding, mode, or size changes.
- **Notification tier:** caller-visible typed refusal.
- **Product-user affordance:** reading the report does not trade, promote,
  or bench. If you want an action, take it at the Book door as the
  operator.

### FR-29: A sweep axis is empty

- **Failure class:** `invalid input` (CT-04), field `instruments`,
  `timeframes`, or `parameters` (with the offending `parameter` named).
- **Detection:** `SweepDeclaration.try_create` / `expand_sweep` /
  `preflight_run_count` reject a zero-length instrument axis, a zero-length
  BarSpec axis, or any parameter whose value list is empty — before any
  Cartesian expansion or pre-flight count runs (AD-11; spec R9).
- **Auto-recovery / retry:** none. Declare at least one value on the named
  axis and re-declare the sweep.
- **Visible degraded state:** no run specs are produced, no count is
  reported, no batch is admitted, no process is spawned, no ledger line is
  written. Expansion is a pure inspection that never half-runs.
- **Notification tier:** caller-visible typed refusal.
- **Product-user affordance:** an empty axis is never a silent zero-combo
  batch — a sweep with an empty instrument, timeframe, or parameter list is
  refused by name. Add the missing value and re-run; nothing was spent.

### FR-30: A swept parameter value is a bare binary float or a malformed conversion

- **Failure class:** `invalid input` (CT-04), field `parameters` (with the
  offending `parameter` and list `index` named).
- **Detection:** `SweepDeclaration.try_create` normalizes every parameter
  value. A bare binary float is refused outright; a money/rational value must
  arrive through a named AD-7/AD-22 conversion mapping stating its `kind`,
  `rounding` mode, and target `scale` (with `currency`/`unit_kind`). A
  conversion whose `value` is not a float, that omits the rounding mode or
  scale, or that the CT-01 `from_float` boundary itself refuses (NaN,
  infinity, bad scale) is rejected (B-8; AR-15; FR-001; DEC-0105).
- **Auto-recovery / retry:** none. Supply an exact integer/categorical/boolean,
  an already-exact `Money`/`ExactRational`, or a well-formed conversion mapping,
  then re-declare the sweep.
- **Visible degraded state:** the declaration is not built; no run spec, count,
  or batch results. A binary float never reaches a run spec's identity content.
- **Notification tier:** caller-visible typed refusal.
- **Product-user affordance:** money and rational sweep values must cross a
  named rounding boundary before they enter a run — a raw decimal like `1.5`
  is refused so two runs can never disagree on a rounded amount. Declare the
  currency/unit, scale, and rounding, and re-run.
