# Cut: laptop-off remote continuation

**Sitting:** architecture only (QMX 2026-09-14).  
**Checkout:** `main` (planning). **Product tip:** `integration` @ `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2`.  
**Method:** `git ls-tree` / `git show integration:<path>` plus docs on this checkout. No implementation, commit, or branch switch.  
**Leads (verified, not treated as proof):** `workroom/research/2026-09-14-backend-baseline.md` Q3; `workroom/research/2026-09-14-qma-understanding.md`; `workroom/research/2026-09-14-qmb-understanding.md`; `inputs/code-qma.md` §5; `inputs/code-qmb.md`; `inputs/intent-durable.md` (agent continuation job).

Evidence levels: `user-intent` | `documented-design` | `source-inspected` | `behavior-demonstrated`  
Class: `reuse` | `connect` | `extend` | `new` | `undecided`

Spine AD-10 already adopted (`ARCHITECTURE-SPINE.md`): continuation is a daemon property; QMB process-per-run is not unattended continuation. This cut checks what that property actually covers when the **laptop sleeps**, versus tab-close, versus a remote worker finishing a job.

---

## Compact table

| Surface | Class | Evidence | What happens if the laptop sleeps (default placement) | Owner |
|---|---|---|---|---|
| QMA daemon host default | **reuse** (law) / **connect** (host) | documented-design + source-inspected | Default host is the workstation. Sleep suspends the sole writer, scheduler, and loopback listener. Nothing agentic *progresses*. | `COMP-QMA-DAEMON` |
| Wire listener bind | **reuse** | source-inspected | Default bind `127.0.0.1`. Remotes cannot reach a sleeping/loopback daemon even if they stay up. Non-loopback needs TLS + operator-recorded config. | `COMP-QMA-WIRE` |
| Remote dial-out | **reuse** | documented-design + source-inspected | Remotes dial out; daemon never dials in. If the daemon is unreachable, workers cannot deliver. | `COMP-QMA-WIRE` / `COMP-QMA-CORE` |
| Durable remote outbox | **reuse** | source-inspected | JSONL + fsync spool on the **worker** side. Survives partition as files; replays on reconnect; does **not** fire the next Task. | `qma.wire.outbox.RemoteOutbox` |
| Client attach/detach | **reuse** | documented-design + source-inspected | Tab-close never stops a run **if the daemon is still running**. Sleep is not detach. | CT-40 |
| Routines / scheduler | **reuse** | source-inspected | Fires only while the daemon evaluates the clock. Missed fires while down are **recorded, not replayed**. | CT-49 |
| Agent-run continuation (`block_stop`) | **reuse** | source-inspected | Next ready Task is dispatched **inside the daemon**. No daemon → no continuation. | CT-49 / `daemon.scheduler.continuation` |
| JobHandle `unknown` / `reattach` | **reuse** | source-inspected | Lost supervisor / unreachable env / daemon restart → `unknown`, never inferred `failed`/`aborted`. Operator resolves. | CT-46 |
| Task Ledger `unknown_tail` | **reuse** | documented-design + source-inspected | Lost env with non-empty outbox marks last acked id; never fabricates the tail. | CT-51 |
| Persistence substrate (JSONL + SQLite WAL) | **reuse** | source-inspected | On-disk stores survive sleep as files. Service maps (experiments, jobs, runs, sessions) are still in-process dicts unless folded through the journal. | `qma.daemon.persistence` |
| QMB orchestrator | **reuse** (as job) | source-inspected | `spawn_model=process-per-run`, `daemon=not-required`. Parent must stay alive to govern/collect. Isolated dirs + ledger fragments survive as files. | `COMP-QMB` |
| QMA→QMB door | **connect** | source-inspected | Default `RecordingQmbDoorTransport` does not spawn `qmb`. Even a live remote env is not a live backtest until the CLI transport is wired. | CT-47 |
| QMN live loop | **reuse** (different job) | documented-design | Trading continues on the VPS under systemd **independent of the laptop**. Not QMA continuation. QMA must not co-host there. | `COMP-QMN` |
| Always-on QMA host SKU / vendor | **undecided** (placement) | documented-design | Which machine is named is operator config (QMA AD-25/AD-26). That the **daemon** (not only a worker) must be on it is not optional. | ops over existing kinds |
| Fifth continuation runtime / QMB daemon | **new** — refused | documented-design | DEC-0084 stays dead; AD-1 forbids a second experiment daemon. | none |

**Overall class:** **connect**. The continuation *function* is already specified and largely library-coded. Laptop-off is missing **wiring of a reachable always-on daemon**, not a new engine.

---

## Source-linked findings

### 1. Three different “continue” events (do not collapse)

| Event | Designed outcome | Authority |
|---|---|---|
| UI / client closes (`wire.detach`) | Agent keeps running. Attachment is client state only; `stops_quant_work=False`. | `docs/components/qma-wire.md:17,67-68,137`; `git show integration:qmx-agents/packages/qma-wire/src/qma/wire/attach.py` (`AttachSubscription.stops_quant_work`, `ClientAttachmentState`) |
| Laptop **sleeps** with default placement | Workstation daemon, loopback listener, and `docker_on_host` workers freeze with the OS. Scheduler does not tick. Remotes cannot ack. | Default envelope below |
| Remote **partition** while daemon stays up | Worker durable outbox replays in order; daemon dedups `producer_id+id`; exhaustion blocks new dispatch (telemetry discarded first); lost env → `unknown_tail`. | `docs/components/qma-wire.md:65,137` (FM-8); `docs/components/qma-daemon.md:84` |

Intent wants both interactive local work and remote work that survives shutdown (`inputs/intent-durable.md` “Agent continuation”; `workroom/research/2026-09-14-backend-baseline.md` Q3). Tab-close is already the wire law. Laptop-off is **not** implied by outbox or by process-per-run.

### 2. Default placement puts the continuation owner on the sleeping machine

Documented:

- Daemon “runs on the operator's workstation by default and runs its workers in Docker on that host”; remotes dial out; daemon never dials in (`docs/components/qma-daemon.md:19,253`; DEC-0336).
- Trading-node VPS is untouched; no QMA workload there (`docs/components/qma-daemon.md:253`; DEC-0327).
- Listener binds loopback by default; non-loopback requires TLS **and** recorded operator config (`docs/components/qma-wire.md:65,133` FM-4).

Encoded on integration:

- `DEFAULT_DAEMON_HOST = "operator_workstation"`
- `DEFAULT_WORKER_ISOLATION = "docker_on_host"`
- `REMOTE_DIAL_DIRECTION = "out"` / `DAEMON_DIAL_DIRECTION = "never_in"`
  — `git show integration:qmx-agents/packages/qma-core/src/qma/core/ports/deployment.py`
- `DEFAULT_BIND_HOST = "127.0.0.1"`; plaintext or unauthenticated non-loopback is a hard startup refusal
  — `git show integration:qmx-agents/packages/qma-wire/src/qma/wire/listener.py`
- Dial-out validation refuses a deployed inbound listener or a second transport
  — `git show integration:qmx-agents/packages/qma-wire/src/qma/wire/reachability.py`

Consequence: **default QMA cannot continue through laptop sleep.** Local Docker workers live on the same host. A remote worker that is actually elsewhere can keep a CPU job running, but it cannot reach a loopback daemon on a sleeping laptop, cannot get the next Task, and cannot land evidence in the journal until the daemon is back.

### 3. What the durable outbox actually continues

`RemoteOutbox` is a real fsynced JSONL spool (`outbox.jsonl` + `outbox.meta.json`), not a sketch:

- Ordered append + `os.fsync`; replay in ordinal order; ack removes only after daemon ack.
- Bounds from `registry:wire.remote_outbox_depth` / `registry:wire.remote_spool_bytes`.
- Evidence/command: block dispatch rather than discard. Telemetry discarded first.
- `on_environment_lost()` → `UnknownTailRecord` (`manufactures_terminal_outcome=False`).

`git show integration:qmx-agents/packages/qma-wire/src/qma/wire/outbox.py`

This continues **undelivered messages**, not **orchestration**. Closing the laptop does not make the outbox a scheduler.

### 4. Routines and `block_stop` continuation live in the daemon process

Unattended fire is a v1 obligation of the **daemon scheduler**, not of workers (`docs/components/qma-daemon.md:164-168`; CT-49):

- Routine firing is deterministic, `machine` principal, no human-gate answers.
- **Missed fires while the daemon is down are recorded, not replayed**; catch-up is an operator-principal command (`AUTOMATIC_BACKFILL = False` in `git show integration:qmx-agents/packages/qma-daemon/src/qma/daemon/scheduler/routines.py`).
- Agent-run continuation: verifier-gated completion; `agent_stop` + `block_stop` returns the Agent to the next ready Task; budget exhaustion escalates to the Quant mailbox and stops; invented Tasks refused (`git show integration:qmx-agents/packages/qma-core/src/qma/core/ontology/continuation.py` and `.../qma/daemon/scheduler/continuation.py`).

Those counters (`AgentContinuation._runs`, `RoutineScheduler._records`) are in-process. Quiet hours never pause a run already under way (`docs/components/qma-daemon.md:163`) — that assumes the daemon is still executing.

### 5. JobHandle already names laptop-off as `unknown`, not failure

`JobHandleService.reattach(..., supervisor_reachable, environment_reachable, daemon_restarted)` maps lost supervisor / unreachable env / daemon restart to `unknown`. Retry / assumed outcome / inferred failure are refused. `unknown` holds the `environment_lease` until an operator-principal recorded resolution.

`git show integration:qmx-agents/packages/qma-daemon/src/qma/daemon/envs/jobs.py`  
CT-46 invariants (`docs/contracts/ct-46-qma-execution-environment-job.yaml:38-39`).

So a sleeping laptop that was the supervisor is **not** “the job failed.” It is `unknown` until a human resolves. That is correct L35 discipline; it is not automatic resume.

`JobHandleStore` has `snapshot()` / `restore()` — library-ready — but the live store is an in-memory `_by_id` dict unless a composer persists it through the journal/sqlite writer.

### 6. Persistence substrate exists; several continuation-relevant services are not on it yet

Present (source-inspected):

- `PersistenceSubstrate`: one process, one writer lock, JSONL journal via qmf-data, one SQLite WAL connection on thread `qma-daemon-sqlite`.
  — `git show integration:qmx-agents/packages/qma-daemon/src/qma/daemon/persistence/substrate.py`
- `AuthoritativeJournal.append_event` writes JSONL and allocates `journal_seq`.
- `SingleSqliteWriter` — `git show integration:qmx-agents/packages/qma-daemon/src/qma/daemon/persistence/sqlite_writer.py`

Still in-process maps (missing **wiring** onto that substrate, not missing store kinds):

- `ExperimentSpecService._specs` / `_leases` / `_lineage` — `git show integration:qmx-agents/packages/qma-daemon/src/qma/daemon/experiments/service.py`
- `JobHandleStore._by_id`
- `AgentContinuation._runs`
- `RoutineScheduler._records` (journal events optional; `_journal` may be `None`)
- `RuntimeService._sessions` / `_kernels` (durable Session snapshot exists as a payload helper; restore is a method, not a boot fold)

On-disk files survive sleep. In-memory orchestration does not, even after wake, unless recovered from the journal.

### 7. No composed asyncio daemon process on this revision

`qma.daemon.__init__` exports the service library (journal, compiler, dispatcher, persistence, hooks, …). There is no `asyncio.run` / websockets / uvicorn / aiohttp listener under `qma-daemon` or `qma-wire` src at `1b451a8` (`git grep` over those trees empty for those tokens).

Wire is a **contract library + posture validators**. Closing a client cannot be demonstrated as harmless until a live event stream exists. Same for remotes dialing a sleeping vs always-on host.

### 8. QMB is process-per-run, explicitly not a daemon

`git show integration:qmb/src/qmb/orchestrator/__init__.py`:

- `SPAWN_MODEL = "process-per-run"`
- `IMPURE_OWNER = "orchestrator"`
- identity includes `daemon: DAEMON`

`git show integration:qmb/src/qmb/orchestrator/spawn.py`:

- `PROCESS_MANAGEMENT = "stdlib.subprocess"`
- `RAY = "absent"`
- `DOCKER = "not-required"`
- `DAEMON = "not-required"`

Parent `start_run` / `collect_run` / `abort_run` must stay alive to enforce limits and append the one ledger line. `stop_study` accounts every already-spawned `LiveSpawn` with exactly one line and leaves a **resumable** stopped Study (`git show integration:qmb/src/qmb/orchestrator/study.py`) — resume is an operator/orchestrator act (`optimize.plan_study_resume`), not unattended laptop-off.

What **does** survive a dead parent as files: isolated output directories, WriterId-scoped ledger fragments, CT-32 artifacts. That is crash/stop durability, not continuation.

QMA must not grow a second backtest governor (DEC-0316, DEC-0348, spine AD-8). Occupancy is one `qmb` job per ExecutionEnvironment. The default transport **records** CLI/MCP invocations and does not spawn `qmb` (`RecordingQmbDoorTransport` in `git show integration:qmx-agents/packages/qma-daemon/src/qma/daemon/backtest/service.py`). Laptop-off backtests are therefore **doubly unwired**: no live door, and no always-on placer.

### 9. QMN already continues when the laptop is off — a different product job

The trading node is a systemd-supervised process on a Linux VPS (`docs/components/trading-node.md:17,125`; DEC-0189). Topology: “VPS PLANE (Linux, always on)” (`trading-node.md:117`). Workstation is provisioning/UI over SSH tunnel; installing `qmn` on the workstation refuses to compose (`trading-node.md:298,312`).

That is **live/paper node** continuation (spine AD-7 `node-paper` / live). It is not strategy-experimentation continuation. AD-28 forbids parking `qma-daemon` on that VPS (`docs/components/qma-daemon.md:349-372`).

### 10. Remote env kinds vs deferred vendors

CT-46 kinds: `local | docker | remote_container | remote_host | browser | desktop` (`docs/contracts/ct-46-qma-execution-environment-job.yaml:30`).

- Default: `docker` ephemeral on the daemon host.
- `remote_host` / `research_node` / `remote_workspace` are first-class deploy targets in `deployment.py`.
- `remote_container` placement is refused as GAP-0075 in `RuntimeService._refuse_deferred` (`git show integration:qmx-agents/packages/qma-daemon/src/qma/daemon/envs/runtime.py`).
- `desktop` is GAP-0070 (planned Windows VPS, not provisioned).
- External A2A mailbox transport is GAP-0079 — **not** required for laptop-off; remotes already dial the daemon.

Laptop-off does **not** wait on GAP-0075/0070/0079. It waits on putting `qma-daemon` on a host that does not sleep with the laptop, opening a TLS non-loopback listener under recorded config, and composing the process.

---

## (1) What already exists

**Designed (ratified):** unattended agents while the operator is away (ADR-0020; DEC-0328); client detach ≠ stop; remotes dial out; durable outbox + dedup; missed Routine fires recorded not auto-replayed; JobHandle `unknown` + operator resolution; Task Ledger survives the worker; QMB process-per-run with resumable Study stop; QMN VPS always-on for money-path.

**Library-coded on integration:** deployment envelope constants; listener/reachability validators; `RemoteOutbox`; attach/detach types; Routine scheduler; Agent continuation; JobHandle reattach/unknown; persistence substrate (JSONL + SQLite); QMB spawn/governor/study; QMA backtest **law** (no `import qmb`).

**Already continues through laptop sleep today (product, not QMA):** QMN on the trading VPS — live/demo loop, news timer, backups — provided that node is deployed. QMA must not be mixed into that host.

**Already continues through tab-close (design; process not composed):** any work the daemon already owns, **if** the daemon process is up.

**Already survives as files (no progress):** daemon journal/sqlite/artifacts; worker outbox spool; QMB isolated run dirs and ledger fragments.

---

## (2) Missing wiring vs missing function

| Missing **wiring** (function present as library/law) | Missing **function** |
|---|---|
| Compose one long-running asyncio `qma-daemon` process (listener + journal writer + scheduler tick + pack roster) | None. Do not mint a fifth runtime or a QMB daemon (AD-1, DEC-0084, QMB `DAEMON=not-required`). |
| Place that process on a host that does not sleep with the laptop; record non-loopback TLS bind | Always-on **SKU/vendor** (which box) — placement/config, not a new COMP. GAP-0075 vendors stay deferred. |
| Persist ExperimentSpec / JobHandle / Task Graph / Routine / continuation counters through the journal/sqlite writer (fold on boot) | Automatic replay of missed Routine fires — **explicitly refused** (`AUTOMATIC_BACKFILL=False`). Catch-up stays operator-gated. |
| Worker runtime that actually dials out, holds `RemoteOutbox`, and calls `JobHandle.reattach` | Inferring terminal state after sleep — **refused**; `unknown` + human resolution is the function. |
| Replace `RecordingQmbDoorTransport` with a real `qmb` CLI transport so a remote env can *run* the job the orchestrator already knows how to spawn | QMB becoming a permanent service so laptop-off backtests “just continue” |
| UI/operator command to name the always-on ExecutionEnvironment / daemon bind (human-gate list already includes env declaration + `variable.set`) | Co-hosting QMA on the trading-node VPS — **refused** (AD-28) |
| | External agent-to-agent relay (GAP-0079) — not this job |

Sleep of a laptop-hosted daemon is not a bug in the outbox. It is the default envelope. Wiring the existing daemon off that laptop is the product move.

---

## (3) Recommended architectural ownership

| Concern | Owner | Class |
|---|---|---|
| Unattended mission/task/routine/continuation | `COMP-QMA-DAEMON` | **reuse** library; **connect** process + host |
| Wire envelope, dial-out, outbox, attach | `COMP-QMA-WIRE` | **reuse** |
| Where a job runs | CT-46 `ExecutionEnvironment` (Compute Router) | **reuse**; default `docker_on_host` is interactive, not laptop-off |
| Governed backtest process lifetime | `COMP-QMB` orchestrator (job-scoped) | **reuse**; QMA places one job per env (AD-8 **connect**) |
| Live trading through laptop-off | `COMP-QMN` on its VPS | **reuse**; disjoint from QMA |
| Always-on QMA host identity | Operator-recorded QMA AD-25/AD-26 config over existing `remote_host` (or a workstation-adjacent always-on box running `qma-daemon`) | **connect** placement; **undecided** SKU |
| New COMP / QMB service / QMA-on-node | none | **new** refused |

Spine AD-10 stands. Tighten the one ambiguous clause (“daemon **or** a reachable remote env”) so builders cannot treat a remote worker + outbox as a substitute for a live daemon.

---

## (4) Open questions — AD vs Deferred

**Need an AD (one invariant; two builders would otherwise fork):**

Tighten AD-10:

> Laptop-off unattended work requires a **reachable always-on `qma-daemon`** (journal writer, scheduler, dispatcher). Remote ExecutionEnvironments plus the durable outbox preserve **in-flight job evidence** across partition; they do not dispatch the next Task, fire Routines, or replace the daemon. QMB orchestrator lifetime remains the **job**. Closing a UI tab still cancels nothing by itself. The daemon must not live only on the sleeping laptop if laptop-off is promised, and must not be placed on the trading-node VPS.

Without that tightening, builder A keeps the daemon on the laptop and sells “remote workers + outbox” as laptop-off; builder B moves the daemon; builder C daemonizes QMB. A/B/C are incompatible.

**Can stay Deferred / ops (not a new AD):**

- Exact machine name / provider for the always-on host (spine already: “host is QMA AD-25/AD-26 config”).
- GAP-0075 sandbox vendors; GAP-0070 desktop VPS; GAP-0079 external A2A; GAP-0081 UI SDK.
- Automatic missed-fire backfill (already refused).
- Windows-sleep semantics of Docker Desktop (OS fact; solved by moving the daemon, not by a new module).

---

*Checkout: `main` (planning only). Product cited: `git show integration:<path>` at `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2`. No implementation or branch switch performed.*
