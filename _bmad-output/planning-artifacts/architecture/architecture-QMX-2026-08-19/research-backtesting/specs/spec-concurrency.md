# Spec — Concurrent Runs (12–14 tasks at a go)

Reverse-engineering spec for QMX. Sources read read-only:
- Jesse v3.0.6 — `C:/Users/Mubarak/Desktop/QMX/workroom/reference/repos/jesse`
- Lean CLI (Python orchestrator) — `…/scratchpad/lean-cli`
- Lean Engine (C#) — `…/scratchpad/lean-engine`

Operator's direct question: *"12–14 tasks at a go — which system handles it?"* Short answer below,
mechanism proof in §2, verdict in §3, QMX requirements in §4.

**Both systems achieve concurrency by the same primitive: one OS process per run, never threads
inside one interpreter.** Neither runs N concurrent backtests inside a single process — because
both keep mutable global state that would collide. That collision (and how each avoids it) is the
whole story, and it validates the QMF law that a library never spawns threads.

---

## 1. Feature claim (verbatim, with URL)

**Jesse** — the product does not headline concurrency; it headlines accuracy, and treats
parallelism as an optimizer/dashboard convenience:
- Homepage: *"The **most accurate** backtesting engine — No look-ahead bias, detailed logs, etc."*
  — https://jesse.trade/
- Changelog 0.12.2: *"Added the `--cpu` option for the optimize mode to specify the number of cpu
  cores to use when running the optimize mode."* — https://docs.jesse.trade/docs/changelog
- Changelog (dashboard): *"[NEW FEATURE] Ability to open multiple tabs (inside the dashboard
  itself) and run multiple candle importing and backtests in parallel."* — same URL.
- The research API's own docstring markets the isolation directly (see §2): *"An isolated
  backtest() function … Because of it being a pure function, it can be used in Python's
  multiprocessing without worrying about pickling issues."*

**Lean** — concurrency is an explicit, first-class optimizer option:
- Lean CLI API reference: *"To set the maximum number of concurrent backtests to run, use the
  `--max-concurrent-backtests` option."* — https://www.quantconnect.com/docs/v2/lean-cli/api-reference/lean-optimize
- `lean backtest` help: *"`--output DIRECTORY`  Directory to store results in (defaults to
  PROJECT/backtests/TIMESTAMP)"* and *"`-d, --detach`  Run the backtest in a detached Docker
  container and return immediately"* — https://github.com/QuantConnect/lean-cli
- User-confirmed real-world load (forum): *"I run 16 backtest same time with LEAN CLI (different
  algorithm). It enables you to use parallel processing. It has significantly sped up my …"* —
  https://www.quantconnect.com/forum/discussion/11225

No public claim in either project promises "12–14 concurrent runs" as a supported number. That
figure is the operator's target load; the code tells us what actually bounds it (§2), and QMX must
set its own governed cap (§4).

---

## 2. Mechanism — how the code actually does it

### 2.1 Jesse: process-global state forces process isolation

Jesse's entire simulation reads and writes **module-global singletons**. There is no run handle you
pass around; the run *is* the process's global state.

- The store is one module-global object:
  `store = StoreClass()` — `jesse/store/__init__.py:42`. Its ten sub-states (orders, positions,
  candles, closed_trades, logs, exchanges, tickers, trades, orderbooks, app) are **class-level
  attributes** (`jesse/store/__init__.py:14–23`), and `reset()` rebuilds every one of them
  (`jesse/store/__init__.py:29–39`).
- Config is likewise a module-global with a saved backup:
  `config = {…}` (`jesse/config.py:8`), mutated by `set_config` (`:116`), restored by
  `reset_config` → `config = backup_config.copy()` (`:173–175`).

The "isolated" backtest is isolated **in time, not in space** — it brackets a run with resets:

```
jesse/research/backtest.py:104   jesse_config['app']['trading_mode'] = 'backtest'
                          :107   set_config(_format_config(config))     # mutate global config
                          :110   router.initiate(routes, data_routes)   # mutate global router
                          :113   store.reset()                          # rebuild global store
                          :118   exchange_service.initialize_exchanges_state()
                          :155   backtest_result = simulator(...)       # runs against globals
                          :212   reset_config()                         # restore global config
                          :213   store.reset()                          # rebuild global store
```

Consequence, stated plainly: **two `_isolated_backtest` calls in the same process cannot overlap** —
the second's `store.reset()` / `set_config` would clobber the first's live state mid-run. Sequential
reuse in one process is safe (that is what the pre/post resets buy). True parallelism *requires
separate processes*, each carrying its own copy of the module globals. The docstring says exactly
this (`jesse/research/backtest.py:34–36`): "a pure function … can be used in Python's
multiprocessing without worrying about pickling issues." The Monte-Carlo / rule-significance
simulator uses the identical bracket (`store.reset()` … `reset_config(); store.reset()` —
`jesse/research/rule_significance_testing/simulator.py:78, 187–188`).

**Optimize mode — how Jesse actually fans out (Ray):**
- CPU sizing: `available = cpu_count()`; `self.cpu_cores = cpu_cores if cpu_cores <= available else
  available` (`jesse/modes/optimize_mode/Optimize.py:129–130`). The public entry validates and
  refuses over-subscription: raises if `cpu_cores > max_cpu_cores` (`optimize_mode/__init__.py:39–41`).
- Ray boot: `ray.init(num_cpus=self.cpu_cores, ignore_reinit_error=True)`
  (`Optimize.py:154–156`), with a documented fallback to `num_cpus=1` on failure (`:158–161`).
- Each trial is a **Ray remote task pinned to one core**: `ray_evaluate_trial.options(num_cpus=1)
  .remote(...)` (`Optimize.py:504`). The remote worker is a separate process; inside it, it calls
  `get_fitness` → `isolated_backtest` (`fitness.py:35, 86`) — so each worker gets its own module
  globals and the collision problem disappears.
- Bounded in-flight window (this is the concurrency governor):
  `max_workers = min(self.cpu_cores * 2, self.n_trials - self.completed_trials)` (`Optimize.py:490`),
  and the dispatch loop keeps `len(active_refs) < max_workers` (`:501`), harvesting with
  `ray.wait(..., num_returns=1, timeout=0.5)` (`:529`). Note the `*2` over-subscription — Jesse
  intentionally keeps ~2× cores in flight so a blocked/IO trial does not idle a core.
- Zero-copy input sharing: big candle arrays and config go through Ray's object store once via
  `ray.put(...)` (`Optimize.py:481–488`); workers receive plain dereferenced objects.
- Optuna holds the trial ledger/state out-of-process (`optuna.create_study(storage=…,
  load_if_exists=True)`, `Optimize.py:146–151`) — so trial results survive/aggregate independent of
  any single worker.

**What breaks at N parallel runs in Jesse:** nothing, *as long as each run is its own process*. The
moment two runs share an interpreter (e.g. threads, or two `backtest()` calls awaited concurrently
in one async loop) they corrupt each other through `store` and `config`. Jesse never does this; it
pays the process-spawn + candle-copy cost per run instead. Data structures worth noting: candles are
`np.ndarray` copied defensively per run (`np.copy(v['candles'])`, `backtest.py:137, 140`), so a run
never mutates the caller's arrays.

### 2.2 Lean: one OS process per run, one output directory per run

Lean's local optimizer is the cleanest statement of the model, and its comments name the exact
hazard the operator cares about (log/stream collision).

- **Concurrency bound** lives on the node packet: `int MaximumConcurrentBacktests`
  (`Optimizer/OptimizationNodePacket.cs:74`). Default is **half the cores**:
  `MaximumConcurrentBacktests = Config.GetInt("maximum-concurrent-backtests",
  Math.Max(1, Environment.ProcessorCount / 2))` (`Optimizer.Launcher/Program.cs:63`); the shipped
  example config suggests `10` (`Optimizer.Launcher/config.example.json:49`).
- **Admission control**: launching is gated under a lock; over the cap, the parameter set is
  queued, not dropped:
  ```
  Optimizer/LeanOptimizer.cs:449  lock (RunningParameterSetForBacktest)
                          :451    if (MaximumConcurrentBacktests != 0 &&
                                     RunningParameterSetForBacktest.Count >= MaximumConcurrentBacktests)
                          :454        PendingParameterSet.Enqueue(parameterSet);   // backpressure
                          :461    var backtestId = RunLean(parameterSet, backtestName);
  ```
  In-flight and pending sets are `ConcurrentDictionary` / `ConcurrentQueue`
  (`LeanOptimizer.cs:71, 77, 125–126`); completion counters use `Interlocked` and result lists are
  guarded by their own lock (`:250, 272, 280–281`) because "backtest results can arrive on different
  threads."
- **Each run is a separate OS process in its own directory** — this is the money quote for the
  operator's per-run-isolation and one-writer-per-stream concerns:
  ```
  Optimizer.Launcher/ConsoleLeanOptimizer.cs:84
      // start each lean instance in its own directory so they store their logs & results,
      // else they fight for the log.txt file
      :85  var resultDirectory = Path.Combine(_rootResultDirectory, backtestId);
      :86  Directory.CreateDirectory(resultDirectory);
      :89  var startInfo = new ProcessStartInfo { FileName = _leanLocation,
      :93      Arguments = $"--results-destination-folder \"{resultDirectory}\"
                            --algorithm-id \"{backtestId}\" … --parameters {parameterSet} …",
      :119 process.Start();
  ```
  `backtestId = Guid.NewGuid()` (`:82`); the run's process is tracked in
  `_processByBacktestId` (`:35, 102`) so it can be killed on abort (`AbortLean` → `process.Kill()`,
  `:128–135`).
- **Completion is the single write-back moment.** Nothing is aggregated while a run is live; when
  the process exits, Lean reads that run's one result file and hands it up:
  ```
  ConsoleLeanOptimizer.cs:104  process.Exited += (…) => {
                          :113      var backtestResult = $"{backtestId}.json";
                          :114      var resultJson = Path.Combine(_rootResultDirectory, backtestId, backtestResult);
                          :115      NewResult(File.Exists(resultJson) ? File.ReadAllText(resultJson) : null, backtestId);
  ```
  `NewResult` (in `LeanOptimizer.cs`) folds that JSON into the strategy's running best under lock and
  then pulls the next `PendingParameterSet` off the queue — a strict "finish → append → admit next"
  cycle. This is structurally identical to the operator's "log during the run, save once at the end
  into the ledger" model.

- **lean-cli (single backtest / manual fan-out):** each `lean backtest` writes to its own timestamped
  directory — `output = algorithm_file.parent / "backtests" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")`
  (`lean/commands/backtest.py:326`), created before the run (`:376–377`). Each run is a Docker
  container with a **unique name**: `run_options["name"] = lean_config.get("container-name",
  f"lean_cli_{uuid4().hex}")` (`lean/components/docker/lean_runner.py:327`), and that container name
  is recorded into the run's own output config (`:335`). `--detach` (`lean_runner.py:163–169`) lets a
  user hand-launch many containers that run independently — this is how the forum user ran "16
  backtests at the same time": 16 containers, 16 output dirs, no shared writer.
- **Cloud parallel model (context, ABSENT from local code):** QuantConnect cloud sells "nodes" — a
  run occupies a node, N nodes = N concurrent runs, billed. Local Lean reproduces this with
  `MaximumConcurrentBacktests` as the node-count analogue. The cloud node scheduler itself is
  server-side and **not present** in these clones; treat it as a commercial capacity model, not a
  mechanism QMX must copy.

### 2.3 The shared invariant

| Question | Jesse | Lean |
|---|---|---|
| Unit of isolation | OS process (Ray worker / `multiprocessing`) | OS process (`process.Start()` / Docker container) |
| Why not threads? | module-global `store` + `config` collide | shared `log.txt` / result files collide |
| Concurrency cap | `min(cpu_cores*2, remaining)` (`Optimize.py:490`) | `MaximumConcurrentBacktests`, default `cores/2` (`Program.cs:63`) |
| Backpressure | in-flight window loop (`Optimize.py:501`) | enqueue over cap (`LeanOptimizer.cs:454`) |
| Per-run output | Ray result objects; Optuna study db | per-run dir keyed by `backtestId`/timestamp |
| Write-back moment | worker returns → main folds into study | `process.Exited` → read `{id}.json` → `NewResult` |
| Input sharing | `ray.put()` zero-copy object store | files on disk + CLI args |

Both prove the QMF law empirically: **the thing that runs a strategy must not hold shared mutable
state, and if it does, you isolate by process.** QMF removes the state entirely (immutable/pure),
which makes the process boundary a *choice for CPU parallelism* rather than a *correctness crutch*.

---

## 3. Jesse vs Lean — which fits QMX and why

**Lean's local-optimizer model fits QMX better**, with one Jesse idea grafted on.

- **Adopt from Lean:** process-per-run + **one isolated output directory per run**, keyed by a
  content/run id; a hard `MaximumConcurrentBacktests`-style governor with **enqueue-on-full
  backpressure**; and **completion-triggered single write-back** (`process.Exited → read one result
  file → append`). This is almost exactly the operator's wind-tunnel + ledger model already, and its
  central comment ("else they fight for the log.txt file") is the operator's one-writer-per-stream
  law discovered independently in production C#.
- **Adopt from Jesse:** the *pure-function run* framing (`_isolated_backtest` as a function of its
  inputs with no ambient dependencies) — QMF goes further than Jesse by making purity real
  (immutable values, no globals to reset) instead of simulated by `reset()` brackets. Also adopt
  Jesse's **defensive input copy** discipline (candles copied per run) — in QMX this is free because
  values are immutable. Jesse's `cpu_cores*2` over-subscription is a useful knob for IO-bound phases
  (data load) but should default off for CPU-bound sim.
- **Reject from both:** Jesse's module-global `store`/`config` (the anti-pattern QMF already bans —
  AD-15); Lean's Docker-container-per-run (heavyweight; QMX's "sandbox" is already the isolation
  boundary, a nested container per run is redundant); Lean/QC's billed cloud-node scheduler (out of
  scope). Ray itself is optional — QMX can start with a plain process pool and adopt Ray-class object
  sharing only if candle-array copy cost dominates.

Why not Jesse's whole model: Ray adds a heavy dependency and an object-store daemon, and its
`store.reset()` correctness scaffolding is dead weight once QMF values are immutable. Why not Lean's
whole model: Docker-per-run and the cloud-node economics don't match "quant agents in disposable
sandboxes." The sweet spot is Lean's *disk-and-process discipline* over QMF's *pure-value core*.

---

## 4. QMX spec draft — the concurrency model for sandboxes

Requirements (WHAT, not code design). Anchored to **AD-15 concurrency (immutable/pure,
one-writer-per-stream, async only at the venue edge)** and the run-ledger rulings.

**C-1 — Library never spawns.** The QMF backtesting library (a pure library, not an engine) MUST NOT
create threads, processes, or async tasks of its own. A single run is a pure computation: `run =
f(inputs)`, deterministic, no ambient/global state. *(QMF law; contrast Jesse's global `store` reset
brackets, which exist only because it broke this rule.)* Parallelism is the caller's concern.

**C-2 — Isolation by process, owned by the orchestrator.** Concurrent runs MUST be separate OS
processes, each executing one pure run. Because QMF values are immutable and there is no shared
mutable state (no `store`, no `config` singleton), the process boundary exists **only for CPU
parallelism**, not for correctness. Two runs in one interpreter MUST still be forbidden by
convention (no threads touching a run), matching one-writer-per-stream.

**C-3 — Per-run isolated output room.** Every run MUST write only into its own directory/namespace,
keyed by its run id (content fingerprint, `fp1:sha256`, per AD-16). No two live runs may share a
writer for any file or stream — the explicit Lean lesson ("else they fight for the log.txt file").
Maps to AD-19 data rooms and one-writer-per-stream journals.

**C-4 — Streamed run logs, per run.** While a run is live, its logs/metrics MUST stream to its own
per-run log stream (the operator's "logged during the run"). These are **logs, not journals** (AD-14)
— tail-able, not the system of record. A crashed/aborted run leaves a partial log in its own room and
never corrupts any other run or the ledger.

**C-5 — Ledger append is the single write-back moment.** A run's result is committed to the shared
**LEDGER exactly once, at completion** (the operator's "save when experimentation is done"; Lean's
`process.Exited → read {id}.json → NewResult`). The append MUST carry the 5-part result label
(contract-format version, inputs, range, computation-id vs occurrence, **world ∈ {live, replay,
simulated}** — backtests are `world=simulated`) and a typed pass/fail end result. Content-addressed
runs from many sandboxes MUST merge into one ledger without coordination beyond append (append-only
typed lineage edges, pinned JSONL — AD-16). No partial or mid-run writes to the ledger.

**C-6 — Governed concurrency cap with backpressure.** The orchestrator MUST enforce a maximum number
of simultaneously-running runs (Lean's `MaximumConcurrentBacktests`). Excess runs MUST queue
(enqueue-on-full), never be dropped and never oversubscribe silently. Requesting more than the host
can serve MUST yield a **typed refusal** (returned, not raised — the 6-category refusal contract),
not a hang. On finish, admit the next queued run ("finish → append → admit next").

**C-7 — CPU-bound fan-out sizing (Ryzen-9-class sandbox, target 12–14).** The default cap MUST be
derived from host cores, not hard-coded. For a CPU-bound sim, a run saturates ~1 core; both
references default conservatively (Lean `cores/2`). A Ryzen 9 (e.g. 12C/24T) comfortably serves the
operator's **12–14 concurrent runs** if runs are ~1 core each and RAM per run × N fits physical RAM.
Requirements:
  - Default cap ≈ physical cores (not threads); allow operator override up to a validated ceiling
    (Jesse refuses `cpu_cores > cpu_count()` — `optimize_mode/__init__.py:40`). QMX MUST refuse over
    the ceiling with a typed refusal.
  - **Memory is the real limiter, not cores.** Each run holds its candle set(s) in RAM; N runs = N×
    working set. The governor MUST size the cap by `min(cpu_budget, ram_budget)` and refuse when
    projected peak memory exceeds budget (peak memory is already a gated metric per the perf ruling).
  - An IO-bound phase (data load) MAY over-subscribe (Jesse's `cores*2`); the CPU-bound sim phase
    MUST NOT. Sizing SHOULD be phase-aware, not a single global number.
  - Zero-copy input sharing across sibling runs (Ray-`put` analogue) is an OPTIONAL optimization;
    since QMF values are immutable, shared read-only mmap of candle rooms is the natural form and
    avoids Jesse's per-run `np.copy` cost. Not required for V1.

**C-8 — Determinism across the fan-out.** Running the same run in isolation vs alongside 13 siblings
MUST produce byte-identical results and the same fingerprint. Concurrency is purely a scheduling
decision; it MUST NOT touch any value the run computes. (This is what QMF purity buys that Jesse's
`reset()` scaffolding only approximates.)

**C-9 — Abort / crash containment.** The orchestrator MUST be able to kill one run's process without
touching siblings (Lean `AbortLean`), and a run that dies mid-flight MUST NOT append to the ledger —
its absence is itself a recordable typed outcome (storage/other refusal category). No half-written
ledger rows.

---

## 5. Open questions

1. **Orchestrator location.** C-1 forbids the *library* from spawning. Which QMX component owns the
   process pool and the C-6 governor — the CLI/sandbox runner, or a separate "run conductor"? (Lean
   puts it in `ConsoleLeanOptimizer`; Jesse in `optimize_mode`. QMX has no engine, so it must live in
   the app/CLI layer. Needs a ruling — likely the backtesting sitting.)
2. **Sandbox vs process granularity.** Is the operator's "12–14 tasks" one sandbox running 12–14
   processes, or 12–14 sandboxes each running one? The ledger merge (C-5) is designed for the
   many-sandboxes case (content-addressed runs merging from many sandboxes — kernel ruling). If it's
   one sandbox × N processes, the cap governor (C-6/C-7) is intra-sandbox. Both may coexist; needs
   the operator to confirm the topology.
3. **`world=simulated` is RESERVED-locked** until the backtesting sitting (spine ruling). C-5's label
   requirement assumes it unlocks there; confirm the sim-world semantics before finalizing the ledger
   row shape.
4. **Cross-run shared candle cache.** C-7's optional mmap sharing implies a read-only candle room
   siblings can map. Does AD-19's data-room contract already permit concurrent readers on one room?
   (Believed yes — immutable + one-writer means many-reader is safe — but confirm at contract level.)
5. **Memory budget source.** C-7 gates on projected peak memory. Where does the per-run memory
   estimate come from — a declared budget on the run's inputs, a measured prior, or a static
   heuristic per candle count? The perf ruling gates peak memory but doesn't say who predicts it.
6. **Look-ahead gate under concurrency (GAP-0016/0017, deferred to backtesting sitting).** The
   look-ahead test and attempt counter interact with the ledger append (C-5). Does the attempt
   counter increment per process-start or per ledger-append? Deferred, flagged here so the two
   sittings stay consistent.
7. **Optuna-analogue for optimizer runs.** Jesse externalizes trial state to Optuna so it survives
   workers. If QMX later fans out an *optimizer* (not just independent backtests), does the shared
   trial-suggestion state live in the ledger, or a separate coordinator? Out of V1 scope but on the
   horizon.
