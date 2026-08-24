# qmb — failure register

Failure-register entries for `qmb`, per the workspace convention
(`conventions/failure-register.md`, NFR-11). Story 15.3 delivers orchestrator
cancel tokens and declared per-run limits whose breach is a typed `aborted`
refusal (AR-51, B-5, FM-6).

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
