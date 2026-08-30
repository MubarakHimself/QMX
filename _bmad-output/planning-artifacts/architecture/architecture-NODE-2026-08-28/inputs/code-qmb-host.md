# Code inventory — QMB host machinery (backtesting library + CLI) for the trading node

Read-only inventory of `C:/Users/Mubarak/Desktop/QMX-worktrees/node-inventory/qmb/src/qmb`.
Every claim carries a `path:line` citation (repo-relative to the `qmb/` worktree root,
i.e. paths begin `src/qmb/...` or `tests/...` or top-level files). Vocabulary discipline
observed: banned words appear only inside quoted source.

Purpose: judge, per host capability, whether the trading node can **import and reuse it
as-is** (library call), **reuse it with a live adapter**, or **must build it new**.

---

## 0. Scale, dependencies, and the one load-bearing boundary

- Package total: **59,117 LOC** across `src/qmb/*.py`; in-scope host modules (runloop,
  execution, orchestrator, doors, host, config, registryread, ledger, results, plus the
  three top-level helpers) total **34,062 LOC** (`wc -l` over the named files).
- Tests: **63 test files, 27,584 LOC** in `tests/` (`tests/` listing; `find … | wc -l`).
- Runtime deps (`pyproject.toml:8-19`): `qmf-core, qmf-registry, qmf-data,
  qmf-indicators, qmf-structure, qmf-risk, qml, click==8.4.2, optuna==4.9.0`. Python
  `>=3.14,<3.15`. Console script `qmb = "qmb.doors.cli:main"` (`pyproject.toml:22`).
- **The boundary the node lives on the other side of** — `src/qmb/_backends.py:3`:
  "Never `qmf-venue` — live adapters are trading-node territory (DEC-0169)." `VENUE_PACKAGE
  = "qmf-venue"` is *named but not imported* (`src/qmb/_backends.py:32`). The compiler
  restates it: a run-config "binds clock replay or simulated; live venue clocks are
  trading-node territory and QMB V1 does not bind them" (`src/qmb/config/compiler.py:538-540`).
- QMB is designed as ONE never-forked loop across worlds. `src/qmb/runloop/__init__.py:3-6`:
  "The loop is never forked: backtest, replay, and live differ only by which clock and
  adapters the run-config binds (DEC-0169)." This single sentence is the node's charter:
  the node is expected to reuse this loop by injecting a live clock + live adapters.

The GAP-0048 marker recurs as the seam between "seam exists" and "live assertion allowed":
`GAP_0048_OPEN = True` (`src/qmb/execution/ports.py:97`); every fill carries an
`optimistic` taint until GAP-0048 (`ports.py:7,95`); asserting a simulated Instant as
wall/replay is a policy rejection until GAP-0048 (`src/qmb/runloop/frontier.py:196-204`).

---

## 1. Capability table

| # | Capability | Anchor path:line | Status | What the node must add |
|---|---|---|---|---|
| 1 | Run loop / evaluation-instant driver | `src/qmb/runloop/loop.py:794` (`run`), `:687` (`run_slice`) | exists-needs-live-adapter | An async/push driver that appends live samples and calls `run_slice` per new frontier; the batch `run()` is pull-over-a-materialized-Sequence |
| 2 | Bar/tick feed | `src/qmb/runloop/bars.py:324` (`UnderlyingSeries`), `:635` (`consume_same_slice`) | exists-needs-live-adapter | A push-to-pull accumulator (append incoming ticks to an appendable series); tick/volume BarSpecs already supported |
| 3 | Execution ports (fill sim vs venue) | `src/qmb/execution/ports.py:905/920/933/952` (Fill/Slippage/Cost/Financing ports) | does-not-exist (venue-shaped) | A `LiveExecutionPort` consuming the same CT-23 `AuthorizedIntent` but routing to qmf-venue/cTrader instead of crossing a `SlicePath` |
| 4 | Book/BMS wiring in loop (CT-23) | `src/qmb/execution/binder.py:235` (`bind_execution_ports`), `:211` (`BoundExecution.execute`), `src/qmb/execution/handler.py:70` (`ExecutionSliceHandler`) | exists-needs-live-adapter | Live routing decision (paper vs live) + the Book-side CT-23 resolution lives in qmf-risk, not QMB |
| 5 | `resolve_execution_target` / paper routing | (absent — grep found none) | does-not-exist | Entire paper-vs-live routing layer is node-new |
| 6 | Cost port (admission==fill parity) | `src/qmb/execution/cost.py:1-8` | exists-as-is | Live broker commission calibration (rate content deferred to GAP-0048) |
| 7 | QL-7 bot adapter + plain-Python bridge | `src/qmb/host/adapter.py:33/62/73` | exists-as-is | Nothing (pure, reusable directly); live driving reuses `drive_instant` |
| 8 | Footprint injection / snapshot-restore | `src/qmb/host/adapter.py:45-46`, `:40-41`; `src/qmb/host/runner.py:446-447` | exists-as-is | Live per-seat state persistence across restarts (snapshot lives in qml.protocol.state) |
| 9 | Composition root: compose→fingerprint→seal | `src/qmb/config/compiler.py:474` (`compile_run_config`), `:731` (`_finish`) | exists-needs-live-adapter | A live composition root that reads the wall clock at the edge and binds live adapters |
| 10 | Replay-binding / CT-33 mint (OR-06 relocation) | `src/qmb/config/compiler.py:623` (`mint_replay_binding` call), `src/qmb/config/qml_compile.py:37` | exists-as-is (replay only) | A world=live binding mint (QMB "never mints a live binding", `config/replay.py:119`) |
| 11 | Clock (data-driven, OR-03 refusal) | `src/qmb/runloop/frontier.py:248` (`FrontierClock`), `:208` (`read_frontier`) | exists-needs-live-adapter | A live wall-clock `Clock` + lift of the GAP-0048 `CLOCK_SIMULATED` refusal |
| 12 | Wall-clock port (below comp root) | (absent by design — `frontier.py:208-219`) | does-not-exist | The one wall read is at the door (`doors/cli/__init__.py:263`); node reads at its own edge and injects |
| 13 | Governor (admission control) | `src/qmb/orchestrator/governor.py:75` (`ResourceGovernor`) | exists-as-is | Nothing for admission; long-lived seats differ from finite runs |
| 14 | Process spawn / isolation | `src/qmb/orchestrator/spawn.py:179` (`spawn_run`), `:203` (`spawn_governed`) | exists-as-is | A long-lived process supervisor (runs here are finite, one process each) |
| 15 | OS hard cap on processes | (absent — deferred) | does-not-exist | Hardened OS confinement is "a named deferred dependency of the node/platform sitting" (`host/runner.py:10-13`) |
| 16 | Real limit probe (memory) | `src/qmb/orchestrator/watch.py` (`ProcessLimitProbe`, `/proc` VmHWM) | exists-as-is | Node reuses; extend for long-lived RSS watch |
| 17 | Cancel / cooperative abort | `src/qmb/runloop/observe.py:60` (`CancelToken`), `:365` (`check_slice_boundary`) | exists-as-is | Node reuses at slice boundaries; "No threads" model |
| 18 | CLI door | `src/qmb/doors/cli/__init__.py:1` (click), tree `src/qmb/doors/cli/tree.py:93` | exists-as-is (research) | Live/paper operator commands (start/stop/status) — new command group |
| 19 | Python API door | `src/qmb/doors/api/__init__.py:1` | exists-as-is | In-process re-export; node's UI-later backend reuses it |
| 20 | MCP door | `src/qmb/doors/mcp/__init__.py:1` | exists-as-is (scaffold) | Ships after CLI v1; agent-door for node control |
| 21 | Ledger (B-4 roles) | `src/qmb/ledger/line.py:54-63`, `src/qmb/orchestrator/ledger.py:1-7` | exists-as-is | Live-trade evidence stream (distinct from backtest CT-32) |
| 22 | CT-32 result artifact | `src/qmb/results/ct32.py:1-10` | exists-as-is | Live-run result recording is node-shaped; CT-29 exit records for live closes |
| 23 | registryread port | `src/qmb/registryread/port.py:1-6` | exists-as-is | Nothing to read records; store cadence/location is node/ops |
| 24 | Promotion records / human-signed check | (absent) | does-not-exist | Registry authoring + human-signed promotion is registry/node territory |
| 25 | Typed refusal surface | `src/qmb/_refuse.py:1-5` | exists-as-is | Node uses the same `Result[T]` discipline |
| 26 | Logging (operational) | `src/qmb/orchestrator/log.py:1-9` | exists-as-is | Per-run JSONL is "tail-able" — already live-shaped; node needs a long-lived log stream |
| 27 | Journals (evidence) | `src/qmb/data/verify.py:22` (qmf.data JournalWriter) | exists-as-is | CT-13 data-quality journal; live-tick journal is qmf-data territory |
| 28 | Live/streaming data ingest | `src/qmb/data/ports.py:1-6` (batch `ProviderAdapter`) | does-not-exist | A live streaming ingest adapter; QMB's port is batch download-once |

---

## 2. Detail per capability

### 2.1 The run loop — pull-based over a materialized series (NOT push)

`run()` (`src/qmb/runloop/loop.py:794`) is a **pure function** that consumes a
fully-materialized **`Sequence` of event slices**: `_as_slice_sequence` refuses anything
that is not a `Sequence` and materializes a tuple up front (`loop.py:1530-1550`), and the
driver loop is a plain `for event in events.value:` over that tuple (`loop.py:877`). It
"Writes no log and no ledger" (`loop.py:817-819`). This is **pull-based over a
pre-materialized series** — the antithesis of a push feed.

Per-slice, six pinned identity-bearing sub-phases run in order (`loop.py:112-119`,
`SUBPHASES`): `frontier-advance, scheduled-position-events, resting-orders,
closed-data-indicators-structure, strategy-callbacks, new-intents-rest`. "Changing that
order is identity-bearing" (`loop.py:3`). A new intent minted in sub-phase 5 is
**never** eligible to fill against this slice (`SAME_SLICE_NEW_INTENT_FILL = False`,
`loop.py:120`; enforced `loop.py:1256-1261`) — it rests for a later slice.

Bars/ticks are fed by deriving from a pre-materialized, fingerprinted
`UnderlyingSeries` (`src/qmb/runloop/bars.py:324`: `samples: tuple[SeriesSample, ...]`,
`fingerprint: Fingerprint`), read **as-of the frontier**: "Samples after `frontier` are
not consumed — look-ahead prevention by construction, independent of GAP-0048"
(`bars.py:640-643`). BarSpec kinds include `tick-count, volume-threshold,
notional-threshold` etc. (`bars.py:50-59`) so ticks are a first-class base — but still
supplied as a materialized series, not a stream.

**Can it be driven by a live feed?** Not `run()` as-is. But `run_slice()`
(`loop.py:687`) is a **single-slice pure function** that threads `current_frontier` and
`resting` in and out (`loop.py:691-698`, returns `SliceOutcome` with `resting`/`frontier`
at `loop.py:776-791`). A node's async event loop can call `run_slice` once per incoming
live slice, carrying `current` and `resting` between calls — exactly what `run()` does
internally (`loop.py:886-902`). So the **slice primitive is reusable as a library call**;
the **batch driver must be built new** (an async event-loop driver that appends to the
series and advances one slice at a time).

Ports into the loop are the `SliceHandler` Protocol (`loop.py:599-644`): `update_stream,
scheduled_position_event, execute_resting, update_closed_data, mint_intents`. Its
docstring flags the seam as forward-looking: "Later stories bind financing, fill, and
CT-16/17" (`loop.py:601`). Default `SilentSliceHandler` (`loop.py:647`) does nothing —
the node injects its own handler, just as backtest injects `ExecutionSliceHandler`.

Reproduction: `reproduce_run` (`loop.py:952`) and `verify_stored_reproduction`
(`loop.py:1035`) re-run a run-id under its resolved config and require the CT-32
fingerprint (FM-11, DEC-0163). A completed run mints a CT-32 witness (`loop.py:937-949`).

### 2.2 Execution ports — fill SIMULATION, not a venue shape

`src/qmb/execution/ports.py:10-11`: "Nothing here imports `qmf-venue`." The four ports are
`typing.Protocol` seams (`ports.py:905` FillPort, `:920` SlippagePort, `:933` CostPort,
`:952` FinancingPort), composed fill→slippage→cost (`COMPOSITION_ORDER`, `ports.py:93`).

Crucially, `FillPort.decide(intent, path, *, requested_quantity)` crosses a **`SlicePath`**
— a declared intra-slice OHLC/quote path (`ports.py:289-312`: prints, open/high/low/close,
bid/ask, bar bounds, session flags). This is **simulation-shaped**: it decides
`Fill | NoFill | PartialFill` by crossing a bar's declared path (`ports.py:909-916`), not
by sending an order to a broker and awaiting an ack. There is **no `ExecutionPort`
protocol shaped like the venue adapter** anywhere in QMB.

What IS reusable is the **inbound seam**: execution consumes a CT-23 `AuthorizedIntent =
EntryIntent | ExitIntent` (`ports.py:85`, from `qmf.risk.door`), enforced by
`require_authorized_intent` (`ports.py:163-172`): "inbound execution is a CT-23
Book-resolved authorized intent or a typed refusal, never a bot-sized order (B-6, AR-56,
DEC-0164)." `execute_authorized` (`ports.py:1120`) authorizes then runs the ports;
`apply_execution_ports` (`ports.py:1025`) and `slip_then_cost` (`ports.py:1082`) are the
composed tail. A live venue exit already has a placeholder: `record_virtual_close` and
`mint_replay_exit` carry a `venue_observation_ref` param (`ports.py:1197`,`:1228`).

**Node build:** a `LiveExecutionPort` (does-not-exist) that implements the *same
AuthorizedIntent-in contract* but routes to qmf-venue/cTrader. It slots at
`bind_execution_ports` / `execute_authorized` — the CT-23 authorization, full-loss check,
and risk-monotonic exit evaluation (`ports.py:1142-1165`) are reusable around it.

### 2.3 Book/BMS wiring in the loop — where CT-23 is invoked per intent

`src/qmb/execution/binder.py` composes the ports **only from the resolved run-config**
(`binder.py:1-5`, "never by ambient discovery or a code change"). `bind_execution_ports`
(`binder.py:235`) returns a `BoundExecution` whose `.execute(intent)` (`binder.py:211`)
requires a CT-23 authorized intent then calls `execute_authorized(self.config.replay_binding,
intent=…, …)` (`binder.py:212-220`). `src/qmb/execution/handler.py:70`
`ExecutionSliceHandler` is the `SliceHandler` that wires **sub-phase 2 financing** +
**sub-phase 3 fill→slippage→cost** into the loop (`handler.py:1-5`, `:192-238`).

**Where CT-23 evaluation actually happens:** QMB **consumes an already-authorized** CT-23
intent (`EntryIntent`/`ExitIntent` from `qmf.risk.door`). The Book/BMS resolution of a
bot-sized order → authorized intent lives in **qmf-risk (the Book/BMS runtime), not QMB**.
QMB hosts the loop and the fill side; it does not host a Book. The node's Book/BMS runtime
therefore reuses qmf-risk and hands QMB-style execution an authorized intent.

**`resolve_execution_target` / paper routing: DOES NOT EXIST in QMB.** A full-tree grep for
`resolve_execution_target|paper|routing|route` returns only (a) data-store synthetic
partition routing (`src/qmb/data/store_taint.py:444`) and (b) a config fragment category
`"paper": "sizing"` (`src/qmb/config/fragments.py:77`) — neither is paper *trading*. The
paper-vs-live execution target router is entirely node-new.

**Cost port F015 (admission==fill parity): LANDED.** `src/qmb/execution/cost.py:6-8`:
"Admission query and fill-time charge share one formula, so the same inputs return the
identical amount," and "missing calibration is a typed refusal, never a silent zero"
(`cost.py:4-6`). `CostPort.quote` (admission query) and `CostPort.itemize` (post-slip
charge) are the two methods (`ports.py:937-949`). Rate content deferred to GAP-0048.

### 2.4 QL-7 bot adapter + plain-Python bridge

`src/qmb/host/adapter.py` is the **pure** QL-7 runtime-protocol adapter at QMB's
composition root (`adapter.py:1-7`, DEC-0177). Construction:
`construct_conformant_bot(factory, declaration, assignment, read_surfaces, …)`
(`adapter.py:33`) delegates to `qml.protocol.construct_bot` / `FunctionFactory` /
`HostedBot` (`adapter.py:18`). Driving: `drive_instant(hosted, instant)` (`adapter.py:62`)
calls `hosted.on_instant(instant)` — "Drive a hosted CT-33 bot at one evaluation instant
(QL-7, AR-65)."

**Footprint injection:** "Hosts inject only declared-footprint evidence. No Book module,
clock, or venue command surface is ever passed through" (`adapter.py:45-46`).

**Plain-Python bridge:** `ConformantSliceHandler(SilentSliceHandler)` (`adapter.py:73`)
mints from a `HostedBot` on one declared stream in sub-phase 5 (`adapter.py:85-94`);
QL-7 callbacks return zero-or-more CT-23 intents, converted to deterministic
`RestingIntent` tokens by fingerprint (`adapter.py:97-127`). Ungoverned plain-Python bots
"never require this path (QL-1)" (`adapter.py:6`, `host/__init__.py:5`).

**Snapshot/restore:** carried as `state_scope` / `state_bound` params (`adapter.py:40-41`,
threaded at `:55-58`). The actual snapshot/restore mechanism lives in `qml.protocol.state`
(`BotStateScope`, imported `host/runner.py:55`); QMB's sandbox only *observes* it —
`state_bound_holds=True, restore_equivalent=True` are Layer-2 observations
(`host/runner.py:446-447`). Status **exists-as-is** for the adapter; the node reuses
`construct_conformant_bot` + `drive_instant` directly and relies on qml for live-seat
state persistence.

### 2.5 Composition root(s) — compose → fingerprint → seal

Two composition roots exist:

**(a) Run-config composition (`src/qmb/config/compiler.py`).** `compile_run_config`
(`compiler.py:474`) merges explicit layers with fixed precedence
(`LAYER_PRECEDENCE`, `compiler.py:81-87`: invocation-flags > run-spec > bms-fragment >
book-fragment > workspace-defaults), refuses Book/BMS key collisions (`merge_book_bms_keys`,
`compiler.py:657`), derives `world` from clock+provenance (never caller-declared,
`compiler.py:525-533`), resolves the bot cite **through the one registry-read port**
(`compiler.py:555`), then **mints exactly one world=replay CT-28 binding**
(`mint_replay_binding`, `compiler.py:623`; `config/replay.py:3` "Every QMB run mints
exactly one AD-29/CT-28 binding with `world = replay`"). `_finish` (`compiler.py:731`)
then "Fingerprint[s] identity content and freeze[s] the resolved artifact" (`compiler.py:734`)
— this **is** the compose → fingerprint → seal sequence. The fingerprint is the run-id
root AND the ledger key (`compiler.py:178-182`, `run_id_root`/`ledger_key`). The
`ResolvedRunConfig` is frozen and its mappings re-frozen in `__post_init__`
(`compiler.py:225-229`). "Same inputs yield a byte-identical artifact" (`compiler.py:11`).

**(b) Impure host/orchestrator composition.** `src/qmb/orchestrator/__init__.py:1`:
"Impure composition root: process spawn, governor, sinks, WriterId (B-4/B-5)." And
`src/qmb/host/runner.py` `run_sandbox` (`runner.py:115`) is the Layer-2 conformance
composition root (spawns an isolated child, injects read surfaces only, never a Book).

**OR-06 CT-33 mint relocation:** the CT-33/binding mint is performed at the compiler
composition root — `apply_ct33_compiler_extensions` stamps the CT-33 assignment
(`compiler.py:610-621`; `config/qml_compile.py:3` "When a run cites a CT-33 Bot
definition, the compiler stamps…") and `mint_replay_binding` mints the binding there
(`compiler.py:623`). The literal token "OR-06" does not appear in source (grep clean);
this dossier reads the relocation as *the mint living inside `compile_run_config`* rather
than in the loop or a door. Node caveat: QMB "never mints a live binding — Always `replay`"
(`config/replay.py:119`); a `world=live` binding mint is node-new, and QMB even provides
`check_incomparable_to_live` (`config/replay.py:369`) to refuse cross-world reads.

### 2.6 The clock — data-driven, OR-03 typed refusal on exhaustion, no wall port

`src/qmb/runloop/frontier.py:1-4`: "Time advances only through an injected frontier clock
that IS qmf-core's AD-8 `Clock` protocol." `FrontierClock` (`frontier.py:248`) conforms to
`qmf.core.chrono.Clock`; `script_replay_clock` (`frontier.py:222`) reuses
`DataDrivenClock`. Advance is a **pure function of the data cursor**: pull to the minimum
next-emit, never rewind (`advance_frontier`, `frontier.py:129-158`; `min_next_emit`,
`frontier.py:90`). "The clock does not choose `world`" (`frontier.py:37`,
`CLOCK_DOES_NOT_CHOOSE_WORLD = True`) — the compiler does (B-7).

**OR-03 typed refusal on exhaustion (present):** `wall_now()` returns an `unavailable
dependency` refusal before the first advance (`frontier.py:355-368`, "advance from stream
next-emit cursors before reading (OR-03)"); `monotonic_now()` returns `unavailable` once
the scripted script is spent (`frontier.py:370-383`, "the replay was under-provisioned
(OR-03)"). Value-or-refusal, never raised.

**Any wall-clock port?** None below the composition root. `read_frontier` (`frontier.py:208`)
is "The only approved time read below the composition root (AR-16)" and it reads the
**injected** `Clock`, never the system clock (`frontier.py:217-219` raises `TypeError` for
a non-`Clock`). Live wall assertion is explicitly deferred: `as_wall_replay_instant` with
`CLOCK_SIMULATED` returns a policy rejection "until GAP-0048; the loop seam may exist, the
assertion may not" (`frontier.py:196-204`). Nothing here reads the system clock (`AR-16`,
`frontier.py:10`).

**Node build:** the Clock seam is ready and *designed* for live ("backtest, replay, and
live differ only by which clock"), but a live wall-clock-driven `Clock` adapter and the
lift of the `CLOCK_SIMULATED` GAP-0048 refusal are node/GAP-0048 work. Status
**exists-needs-live-adapter**.

### 2.7 Governor + process spawning

`src/qmb/orchestrator/governor.py:1` `ResourceGovernor`: **min(cpu, memory) admission with
enqueue-on-full** (B-5, FM-6). Budgets are registry keys `qmb_governor_cpu_budget` (count)
and `qmb_governor_memory_budget` (bytes), "declared-per-machine and UI-editable; this
module never bakes a spine number" (`governor.py:2-7`). "12-14 concurrent runs on sandbox
hardware is a motivating reference … never a validated budget" (`governor.py:5-7`,
`SANDBOX_CONCURRENT_MOTIVATING_REFERENCE = "not-a-validated-budget"`, `governor.py:57`).

**Accounting (F0xx ledger-accounting fix — landed by construction):** `reserved_cpu` and
`reserved_memory` are **derived** by summing `cpu_cost` / `projected_peak_memory` over the
live `_running` dict (`governor.py:reserved_cpu`/`reserved_memory` properties, ~lines
128-146) — there is **no separate mutable counter to double-count**. `submit` admits /
enqueues / refuses (`governor.py:_submit`, "Never silently oversubscribe (FM-6)"), and
`release` frees then FIFO-admits from the queue. Because reservation reads the running set,
the double-count class of accounting bug cannot occur here; combined with **exactly one
ledger line per run** (FR-33, `ledger/__init__.py:3`), the accounting invariant holds.

**OS hard cap: DOES NOT EXIST (deferred).** No `setrlimit` / `RLIMIT` / job objects /
`cpu_count` / `nproc` anywhere in `orchestrator/` (grep clean). Hardened OS-level
confinement (Windows restricted tokens / job objects, Linux seccomp) is "a named deferred
dependency of the node/platform sitting — V1 does not wait on it" (`host/runner.py:10-13`;
`V1_DEFERRED_OS_CONFINEMENT`, `host/runner.py:77-81`). The governor is a *soft* admission
control over declared budgets, not an OS-enforced cap.

**Spawn:** `spawn_run` (`spawn.py:179`) → `start_run` → `subprocess.Popen([sys.executable,
…], start_new_session=True)` (`spawn.py:402-409`); `spawn_governed` (`spawn.py:203`) runs
the batch under the governor. Each run is "a separate OS process writing only into a
directory named by the run id. Concurrent runs never share a writer" (`spawn.py:1-8`).
`kill_owned_process` "Terminate[s] one `Popen` process. Does not walk or signal siblings"
(`watch.py:127-128`). Real memory probe: `ProcessLimitProbe` reads Linux `/proc/<pid>`
VmHWM, Windows peak working set, or `rusage` (`watch.py:~100-125`) — the impure real
`LimitProbe` the orchestrator injects (vs the library's `ScriptedLimitProbe`,
`observe.py:280`).

Node note: QMB spawns **finite** one-shot processes. A trading node needs a **long-lived
process supervisor** (the seats and order path run continuously), which is new; but the
governor's admission math, the process-isolation posture, and `ProcessLimitProbe` are
reusable.

### 2.8 The CLI

`src/qmb/doors/cli/__init__.py:1-9`: thin `qmb` CLI door, "Adaptation only." Framework =
**click** (`import click`, `cli/__init__.py:18`), pinned by `registry:qmb_cli_pin`
(`cli/__init__.py:6-7`); autocomplete uses "click's native `shell_complete` — no bespoke
completion machinery" (`cli/__init__.py:6`). The door "holds no cache and computes no
run-id of its own" (`COMPUTES_RUN_ID=False`, `HOLDS_CACHE=False`, `cli/tree.py:86-87`).

**Command list** (`command_tree`, `cli/tree.py:93-102`): `backtest run`; `data
{download,verify,gap-check,list,catalog,generate}`; `optimize {run,space,estimate}`;
`sweep count`; `ledger {merge,bar}`; `config {compile,show}`. Orchestrator entry is
`qmb.orchestrator.spawn_run` (`cli/tree.py:88`). **All research/backtest — no live, paper,
node, start, or stop commands exist.**

**Config file format:** there is **no bespoke config file**. Inputs are Book/BMS
**fragments** and a **run-spec**, resolved through the registry-read port and merged by the
compiler; the emitted artifact is `run-config.json` in a run-id-named directory
(`compiler.py:93`, `RUN_CONFIG_ARTIFACT_NAME`; `artifact_relative_path`, `compiler.py:187`).
`config compile` / `config show` operate on the `ResolvedRunConfig`. Prereqs per command
are declared in `_COMMAND_PREREQS` (`cli/tree.py:113-131`).

**Paths & secrets injection:** paths (`output_root`, `destination`, `archive`) come as
flags; run outputs land in a dir named by the run-id (`run_directory_name`,
`spawn.py:171`). **No secrets/credentials are handled** anywhere in the door (no `getenv`
for a token, no credential path). No credential material was seen in any file read.

**Ambient reads (audited):** exactly **one** `datetime.now` in the whole package —
`doors/cli/__init__.py:263`, tagged `# ambient-scan: allow`, with the load-bearing comment:
"The CLI door IS the composition root: when `--end` is omitted, the real clock is read HERE
and injected under the library's `now` key, so the library below never reads the ambient
wall clock (FR-002, DEC-0106)." This is the **exact pattern the node must mirror**: read
the wall clock at the composition edge, inject it down. Exactly **one** `os.environ` read —
`orchestrator/ledger.py:52`, `FACTORY_SANDBOX_ENV = "QMB_FACTORY_SANDBOX"` (stamps
`provenance=sandbox`). `orchestrator/log.py` uses `time`/`secrets` for correlation-id and
timestamps (impure sink, excluded from fp1). `host/runner.py` reads `os.environ` to build
the child env (`_child_env`, `runner.py:581-588`) and uses one `uuid4` tagged
`# ambient-scan: allow` (`runner.py:241`). No other ambient clock/env/randomness in-scope.

### 2.9 Ledger (B-4 roles) + CT-32 results

**Ledger** (`src/qmb/ledger/line.py`, `src/qmb/orchestrator/ledger.py`). "one AD-12
labelled object, never a stored verdict (B-4). The orchestrator is the only writer.
Direct library `run()` mints no line" (`line.py:1-3`). B-4 roles: `confirmation, trial,
replicate, aborted` (`RUN_ROLES`, `line.py:58-63`); the Book-bar read selects
`role=confirmation` only (`BOOK_BAR_READ_ROLE`, `line.py:64`). `STORES_VERDICT = False`
(`line.py:66`): a ledger line "stores raw unit-kinded measures — never a stored pass/fail.
The bar verdict is a read-time fold" (`ledger/__init__.py:4-5`). One line per run
(`ONE_LINE_PER_RUN`, `line.py:65`), on a **WriterId-scoped JSONL fragment** per `(machine,
role, worker-slot)`, LF-terminated, appended with fsync (`orchestrator/ledger.py:1-7`).
Reads are a world-and-role-scoped merge view (`read_merge_view`, `read_book_bar`,
`ledger.py __all__`). Mint functions: `mint_completed_line` (`line.py:262`),
`mint_aborted_line`. A completed run never ledgers `aborted`; aborted lines carry refusal
context (`line.py:286-291`, `:200-227`).

**CT-32** (`src/qmb/results/ct32.py:1-10`): "A completed pure `run()` return is assembled
into exactly one CT-32 container in the run output directory. That container IS the
canonical artifact — no second report JSON." `fp1` is label-derived via qmf-core only;
float bytes never enter identity; re-running must reproduce or return a typed refusal
(FM-11, DEC-0163). Chart series + HTML are declared QMB extensions, AD-10-excluded from
`fp1` (`results/__init__.py:5-8`). In-house skills read CT-32, never a rendering
(`results/__init__.py:8-10`). Live-close evidence is CT-29 exit records via
`record_virtual_close`/`mint_replay_exit` (`execution/ports.py:1177`,`:1210`) — a live
exit-record path is node-shaped.

Node note: reusable as-is for governed **backtest** evidence. Live-trade recording is a
distinct evidence stream (real fills, real broker acks) the node designs on top.

### 2.10 registryread — read port; no promotion / no signing

`src/qmb/registryread/__init__.py:1-7`: "Single library-owned registry-read port over
immutable as-of sets (B-15). Registry state reaches a machine as an immutable,
fingerprinted as-of set of records and fragments. Doors enumerate through this port; the
compiler resolves through it. No door-side or second cache exists (DEC-0165). The hub is
dumb passive storage." `RegistryReadPort` reads `qmf.registry` `KindRegistry` /
`RegistrationRecord` (`port.py:16`, `port_home`, `port.py:41-42`). `AsOfSet`,
`DatedPointer`, `RegistryFragment`, `SupersedesRef` (`registryread/as_of.py`). Stale
evidence is an AD-11 refusal keyed by `registry:qmb_stale_evidence_severity`
(`port.py:39`, `_refuse.py:64-70`).

**Promotion records / human-signed promotion check: DO NOT EXIST in QMB.** Grep for
`promot|signed|signature|attestation|countersign` returns only data-store
non-promotability (synthetic data "never promotes toward live money",
`data/store_taint.py:229-230`, `refuse_promote_synthetic:685`) and one replay-epoch comment
("Carry would need a signed edge", `config/replay.py:148`). There is **no registration
promotion record and no human-signed promotion gate** in QMB — that is registry-authoring /
node-ops territory: "File-sync cadence and where the store lives are node/ops sitting
territory" (`registryread/hub.py:5`).

### 2.11 Typed-refusal surface + logging

**Refusal surface** (`src/qmb/_refuse.py:1-5`): every public qmb op returns `Result[T] =
Ok[T] | TypedRefusal`; "domain failure is never raised across the boundary (CT-04;
DEC-0109)." Builders: `invalid` (invalid input), `policy` (policy rejection), `unsupported`
(unsupported capability), `unavailable` (unavailable dependency), `storage` (storage
failure), `stale` (AD-11 stale evidence) (`_refuse.py:39-70`). `clean_token` is
presence-only, opaque-token discipline (`_refuse.py:22-30`).

**Logging:** **no stdlib `logging`** in the product code (grep: only
`optuna.logging.set_verbosity` in `optimize/sampler.py:76`). The **operational log** is
`src/qmb/orchestrator/log.py:1-9` (AD-14): "Per-run … JSONL records streamed into the run's
output directory, flushed so a **live run is tail-able**. Logs are never evidence … The
library's `run()` writes no log." Correlation-id crosses package boundaries and is excluded
from fp1 (`log.py:6-8`, `CORRELATION_ID_EXCLUDED_FROM_FP1`). A crashed run "leaves a partial
log in its own room and never writes a sibling directory or the ledger" (`log.py:8-9`).
Events: `EVENT_RUN_STARTED/COMPLETED/ABORTED/CRASHED/REFUSED/SPAWNED`. The
"tail-able live run" framing means the operational-log design is **already live-shaped**.

**Journals** are a *separate* concept: CT-13 **data-quality evidence** written via
`qmf.data.journal_producer.JournalWriter` in `data/verify.py:22`,`:679` (pass/fail
data-quality verdict journaled, `data/verify.py:7`). The sandbox `_journal` helper tags a
refusal for the AD-14 log stream (`host/runner.py:623-632`). So QMB has: refusals
(returned, in-band), operational logs (orchestrator JSONL, tail-able, not evidence), and
data-quality journals (qmf-data, CT-13 evidence).

### 2.12 The `doors/` package — what "doors" means here

`src/qmb/doors/__init__.py:1-6`: "Thin doors over the library (B-1). Every capability
exists once, in the library, as a pure function. Doors carry only adaptation logic. The
`qmb` CLI is the product face; the Python API exposes the same surface in-process (never
HTTP); the MCP door is scaffolded and ships after CLI v1." So **"doors" = operator/agent
control surfaces (product faces)** — CLI, Python API, MCP — **not** the qmf-risk Book/BMS
"door".

- **CLI** — `doors/cli/` (click; §2.8). The product face; console script `qmb`.
- **Python API** — `doors/api/__init__.py:1-8`: "the same pure-function surface as `import
  qmb` … In-process re-export for the UI backend and for research. No second cache, no
  run-id of its own, never stacked over HTTP (DEC-0159). Direct calls … produce no governed
  evidence (B-4). Refusals … returned verbatim (AR-58)." This is the **UI-later backend
  seam** the node reuses.
- **MCP** — `doors/mcp/__init__.py:1-7`: "scaffolded, not shipped until after CLI v1
  (B-1, SC-08). A sibling wrapper over the same library, never stacked over HTTP,
  localhost-bound by default." `SHIPPED=False`, `LOCALHOST_BOUND=True`,
  `BIND_HOST="127.0.0.1"` (`doors/mcp/__init__.py:37-43`). Present so the structural-seed
  tree is complete; `serve`/`main` return `unsupported` until it ships. This is the
  **agent-door** scaffold the node's agent control would extend.
- **Door parity** — `doors/parity.py:1-14`: CLI and API surfaces are **DERIVED
  programmatically and reconciled**, "never asserted from a hand-maintained capability map
  (R-006; OR-08 2026-08-27)." The retired hand catalog "is exactly what masked the
  `data.generate` API-door gap (QMX-F016/QMX-F017)" — i.e. those F-fixes landed by
  replacing the catalog with derivation (`parity.py:9-12`).

Read models: doors render CT-32 / ledger via `doors/cli/render.py`, `doors/mcp/render.py`,
`doors/cli/tree.py` (`render_refusal` as stderr JSON, `cli/render.py`).

---

## 3. Every 'node' / 'live' / 'later' / 'deferred' comment (verbatim, cited)

- `src/qmb/_backends.py:3` — "Never `qmf-venue` — live adapters are trading-node territory
  (DEC-0169)."
- `src/qmb/config/compiler.py:538-540` — "a run-config binds clock replay or simulated;
  live venue clocks are trading-node territory and QMB V1 does not bind them."
- `src/qmb/config/replay.py:119` — "Always `replay` — QMB never mints a live binding."
- `src/qmb/config/replay.py:156-158` — "Replay is not a live binding: no live-path rung and
  no SQS live baseline."
- `src/qmb/config/replay.py:369-411` — `check_incomparable_to_live`: "Refuse a cross-world
  read of a replay binding against a live binding … must fingerprint apart from any live
  binding."
- `src/qmb/host/runner.py:10-13` — "Hardened OS-level confinement (restricted tokens / job
  objects on Windows, seccomp-class on Linux) is a named deferred dependency of the
  node/platform sitting — V1 does not wait on it. A dynamically-evasive malicious bot is
  out of V1's threat model."
- `src/qmb/host/runner.py:77-82` — `V1_DEFERRED_OS_CONFINEMENT`, `V1_OUT_OF_SCOPE`.
- `src/qmb/registryread/hub.py:5` — "File-sync cadence and where the store lives are
  node/ops sitting territory."
- `src/qmb/orchestrator/log.py:4-5` — "flushed so a **live** run is tail-able."
- `src/qmb/runloop/__init__.py:3-6` / `loop.py` — "backtest, replay, and **live** differ
  only by which clock and adapters the run-config binds (DEC-0169)."
- `src/qmb/runloop/frontier.py:196-204` — asserting a simulated Instant as wall/replay is
  refused "until GAP-0048 … the loop seam may exist, the assertion may not."
- `src/qmb/execution/ports.py:7-11` — "Every fill carries an `optimistic` taint until
  GAP-0048 … Nothing here imports `qmf-venue`."
- `src/qmb/execution/handler.py:1-5` (financing "content deferred to" — see
  `FINANCING_CONTENT_DEFERRED_TO`, imported `handler.py:29`).
- `src/qmb/execution/cost.py:4-6` — commission "rate content [is] deferred to GAP-0048."
- `src/qmb/data/store_taint.py:27-42` — replay/**live** adapter world separation;
  world=simulated never enters a live namespace.
- `src/qmb/doors/mcp/__init__.py:1-7` — MCP "scaffolded, not shipped until after CLI v1."

---

## 4. Node-reuse verdict — what `import qmb` already gives the node

All the load-bearing building blocks are exported from the top-level package
(`src/qmb/__init__.py` `__all__`): `run` (`:2153`), `run_slice` (`:2161`),
`compile_run_config` (`:1976`), `ResolvedRunConfig` (`:1833`), `RegistryReadPort`
(`:1827`), `bind_execution_ports` (`:1954`), `BoundExecution` (`:1712`), `ExecutionPorts`
(`:1749`), `ExecutionSliceHandler` (`:1750`), `apply_execution_ports` (`:1943`),
`execute_authorized` (`:2006`), `ConformantSliceHandler` (`:1721`),
`construct_conformant_bot` (`:1980`), `drive_instant` (`:2000`), `FrontierClock`
(`:1764`), `script_replay_clock` (`:2167`), `read_frontier` (`:2103`), `spawn_run`
(`:2177`). The package docstring frames itself: "an application-layer product built on QMF,
never a roster package … never `qmf-venue`" (`src/qmb/__init__.py:1-5`).

**Reuse as-is (library call):** QL-7 adapter (`host/adapter.py`), governor
(`orchestrator/governor.py`), process spawn/isolation + real memory probe
(`orchestrator/spawn.py`, `watch.py`), cancel/abort (`observe.py`), ledger schema +
WriterId-scoped fragments (`ledger/`, `orchestrator/ledger.py`), CT-32 assembly
(`results/ct32.py`), registry-read port (`registryread/`), refusal surface (`_refuse.py`),
tail-able operational log (`orchestrator/log.py`), CLI/API/MCP door pattern (`doors/`),
the `run_slice` single-slice primitive (`loop.py:687`).

**Reuse with a live adapter:** the run loop as a live driver (inject a live clock +
handler, drive `run_slice` per push) — `loop.py`; the Clock seam (a live wall `Clock`) —
`frontier.py`; the Book/BMS execution wiring around a live execution port — `binder.py`,
`handler.py`; the composition root (a live variant that reads the wall clock at its edge) —
`compiler.py` + the CLI's inject-`now` pattern (`doors/cli/__init__.py:263`).

**Must build new (node):** a `LiveExecutionPort` over qmf-venue/cTrader (there is no
venue-shaped execution port; `ports.py:11`); the paper-vs-live `resolve_execution_target`
router (absent); a `world=live` binding mint (QMB never mints one; `config/replay.py:119`);
a live/streaming data-ingest adapter (QMB's `ProviderAdapter` is batch download-once;
`data/ports.py:1-6`); a long-lived process supervisor + OS hard cap (deferred;
`host/runner.py:10-13`); registration promotion records + a human-signed promotion check
(absent); a live-trade evidence stream distinct from backtest CT-32; the live operator
door commands (start/stop/status) on the CLI/API/MCP faces.

---

## 5. Open items / caveats

- "OR-06" and specific "F0xx" fix IDs from the task are **not tokens present in this
  source**. This dossier maps them to observed invariants: OR-06 ≈ the CT-33/replay-binding
  mint living inside `compile_run_config` (`compiler.py:610-623`); the cost-port "F015" ≈
  the admission==fill-charge parity now enforced (`cost.py:6-8`); the spawn "F0xx
  ledger-accounting fix" ≈ reservation-derived-from-running-set + one-line-per-run
  (`governor.py` reserved_* properties; FR-33). The FAILURES register uses `FR-N` IDs
  (`FAILURES.md`), and door-parity fixes carry `QMX-F016/QMX-F017` (`parity.py:10`); no
  `OR-06`/`F015` string exists to confirm the exact card.
- `sweep/`, `optimize/`, `robustness/` (skimmed): research/permutation layers over the same
  never-forked loop — `sweep/__init__.py:1-3` ("each combination is one isolated run of the
  same never-forked run loop … the batch merges nothing (DEC-0169)"), `optimize/__init__.py`
  (TPE sampler `n_jobs=1`, fan-out is the orchestrator's), `robustness/__init__.py` (pure
  B-14 ladder functions). Not host machinery the node mirrors; they consume `run()`/`spawn`.
- `data/` (skimmed): `data/ports.py` is a batch `ProviderAdapter` (Jesse CandleExchange
  shape: fetch/earliest_available/list_symbols/batch_count/rate_limit), persistence stays
  in qmf-data CT-10/CT-15 (`data/download.py:1-6`). No live/streaming/websocket feed port
  exists (grep clean) — live recording is a node + qmf-data concern.
- No credential/token material was encountered in any file. (One env read:
  `QMB_FACTORY_SANDBOX`, `orchestrator/ledger.py:52` — a boolean flag, not a secret.)
