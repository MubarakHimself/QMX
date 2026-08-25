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
door later ships. CLI v1 does not wait on it.

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
