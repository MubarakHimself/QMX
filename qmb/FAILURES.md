# qmb — failure register

Failure-register entries for `qmb`, per the workspace convention
(`conventions/failure-register.md`, NFR-11). Story 15.3 delivers orchestrator
cancel tokens and declared per-run limits whose breach is a typed `aborted`
refusal (AR-51, B-5, FM-6). Story 15.4 delivers the one-ledger-line law over
WriterId-scoped JSONL fragments (AR-51, AR-53, B-4). Story 15.5 delivers
per-run AD-14 operational logs streamed by the orchestrator (B-4, AR-35,
CT-11).

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
