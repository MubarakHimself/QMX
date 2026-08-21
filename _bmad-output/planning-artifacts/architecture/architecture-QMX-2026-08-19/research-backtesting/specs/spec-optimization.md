# Spec: Parameter Optimization ("for any X strategy, Y optimizations at time t")

Reverse-engineered from QuantConnect Lean (Apache-2.0) and Jesse (MIT). Mechanism
understanding only — no third-party engine code is proposed for QMX. All cites are
to the local read-only clones:

- **Jesse** (Python, v3.0.6): `workroom/reference/repos/jesse/`
- **Lean CLI** (Python orchestrator): `scratchpad/lean-cli/`
- **Lean Engine** (C#): `scratchpad/lean-engine/`

---

## 1. Feature claim (verbatim, with URL)

### Jesse

> "Jesse optimizes parameters using Optuna, a hyperparameter optimization framework, accelerated with Ray for parallel processing."
> — https://docs.jesse.trade/docs/optimize/

> "By default, Jesse optimizes for the Sharpe ratio, which measures the risk-adjusted return of your strategy. This can be changed in the settings to other metrics such as Calmar ratio, Sortino ratio, or Omega ratio."
> — https://docs.jesse.trade/docs/optimize/

> "Jesse will search through the parameter space defined by the `min`, `max`, and `step` values (for numeric parameters) or through the available options (for categorical parameters) to find the optimal combination."
> — https://docs.jesse.trade/docs/optimize/hyperparameters

> "Each trial evaluates a set of parameters on both the training and testing periods, generating metrics for each. … Training Period (60-70%) … Testing Period (15-20%) … Validation Period (15-20%) not used in optimization at all."
> — https://docs.jesse.trade/docs/optimize/ (train/test/validation guidance)

**The load-bearing claim to test against code:** "using Optuna, a hyperparameter
optimization framework." See §2 — this is materially misleading. Optuna in Jesse
is a **storage ledger only**; the search itself is uniform random.

### Lean

> "Project parameters are parameters that are defined in your project's configuration file. These parameters are a replacement for constants in your algorithm and can be optimized using one of LEAN's optimization strategies either locally or in the cloud."
> — https://www.lean.io/docs/v2/lean-cli/optimization/parameters

> **Grid Search**: "runs through all possible combinations of parameters."
> **Euler Search**: "performs an Euler-like [search] which gradually works towards smaller optimizations."
> Targets: Sharpe Ratio, Compounding Annual Return, Probabilistic Sharpe Ratio, Drawdown (each minimize or maximize).
> Constraints: e.g. "Drawdown <= 0.25"; operators: `<`, `<=`, `>`, `>=`, `=`, `!=`.
> — https://www.quantconnect.com/docs/v2/lean-cli/optimization/deployment

---

## 2. Mechanism — how the code actually does it

### 2.A Jesse

**Parameter space declaration.** A strategy declares its space by overriding
`hyperparameters()`, which returns a list of dicts. Default is empty
(`jesse/strategies/Strategy.py:605-606`). Schema example
(`jesse/strategies/TestDefaultHyperparameters/__init__.py:9-13`):

```python
def hyperparameters(self):
    return [
        {'name': 'qty_w',         'type': int, 'min': 10, 'max': 95, 'default': 70},
        {'name': 'profit_target', 'type': int, 'min': 1,  'max': 40, 'default': 5},
    ]
```

Supported `type`: `int`, `float`, `categorical` (categorical uses `'options': [...]`
instead of min/max); optional `'step'`. At strategy init, if no DNA/hp is injected,
each param falls back to its `default` (`Strategy.py:476-479`).

**The sampler is uniform random — NOT Optuna/TPE.** `Optimizer._generate_trial_params()`
(`jesse/modes/optimize_mode/Optimize.py:226-259`) draws each parameter independently:
- `int` with step: `min + np.random.randint(0, steps) * step` (`Optimize.py:240-245`)
- `int` no step: `np.random.randint(min, max+1)` (`Optimize.py:243-244`)
- `float`: stepped index or `np.random.uniform(min, max)` (`Optimize.py:246-252`)
- `categorical`: `options[np.random.randint(0, len(options))]` (`Optimize.py:253-255`)

There is **no surrogate model, no acquisition function, no exploitation of past
trials.** Every trial is drawn i.i.d. from a uniform prior. This is functionally
random search.

**What Optuna actually does here (ledger only).** After a trial finishes, the score
is written into an Optuna study purely for persistence/resume:
`_create_optuna_trial()` builds `optuna.distributions.*` matching each param and calls
`optuna.create_trial(params, distributions, value=score, user_attrs={train,test metrics})`
then `self.study.add_trial(trial)` (`Optimize.py:261-318`). The study lives in SQLite:
`sqlite:///./storage/temp/optuna/optuna_study.db`, study_name keyed by
`{strategy}_optuna_ray_{session_id}` (`Optimize.py:110-114,146-151`,
`load_if_exists=True`). Optuna's samplers/pruners are never invoked to *choose*
parameters. **This is the marketing-vs-code gap** the operator asked to flag.

**Objective = compound "fitness", not the raw ratio.** `get_fitness()`
(`jesse/modes/optimize_mode/fitness.py:23-125`):
1. Run an isolated backtest on the **training** window with the sampled hp
   (`fitness.py:35-43`; `_isolated_backtest` from `jesse.research.backtest`).
2. Gate: if `training_metrics['total'] <= 5` trades → `score = 0.0001`, discard
   (`fitness.py:46,104-106`).
3. `total_effect_rate = log10(total) / log10(optimal_total)`, clamped to 1
   (`fitness.py:47-48`). This rewards *trade count* up to a target `optimal_total`.
4. Pick the ratio by `env.optimization.objective_function` (default `sharpe`;
   also calmar/sortino/omega/serenity/smart sharpe/smart sortino) and **normalize**
   it into ~[0,1] with hard-coded bounds, e.g. `jh.normalize(sharpe, -0.5, 5)`,
   `calmar → (-0.5, 30)`, `sortino → (-0.5, 15)` (`fitness.py:49-77`).
5. If the raw ratio < 0 → `score = 0.0001` (unusable) (`fitness.py:80-83`).
6. Run a **testing** (out-of-sample) backtest with the *same* hp for reporting
   (`fitness.py:86-94`).
7. **Final score = `total_effect_rate * ratio_normalized`** (`fitness.py:97`);
   NaN → 0.0001. The test metrics do **not** enter the score — they are recorded
   for the user to eyeball train-vs-test overfit (`Optimize.py:424-435` builds the
   `"train / test"` display string).

**Fan-out via Ray.** `Optimizer.run()` (`Optimize.py:462-614`):
- Big shared inputs are put in Ray's object store once via `ray.put(...)` (config,
  routes, all four candle sets, strategy_hp) (`Optimize.py:481-488`).
- Concurrency window: `max_workers = min(cpu_cores * 2, n_trials - completed)`
  (`Optimize.py:490`). A dispatch loop keeps `active_refs` full, launching
  `ray_evaluate_trial.options(num_cpus=1).remote(...)` per trial (`Optimize.py:501-522`).
- `ray.wait(..., num_returns=1, timeout=0.5)` collects finished trials and refills
  the window (`Optimize.py:529-537`) — a bounded work-stealing pipeline, not a fixed
  batch.
- `n_trials = solution_len * env.optimization.trials(default 200)` — i.e. trial
  budget scales with the *number of parameters* (`Optimize.py:133`).
- Ray init: `ray.init(num_cpus=cpu_cores)`, falls back to 1 CPU on failure
  (`Optimize.py:154-161`). Termination is polled every 1s via `timeloop`; if the
  client session dies it raises `exceptions.Termination` (`Optimize.py:164-175`).

**What gets LOGGED per trial.** `logger.log_optimize_mode(...)` writes human lines
per trial: usable/negative-ratio/nan/`<5 trades`, plus ratio, total, pnl%, win-rate
(`fitness.py:82,99,102-105`; `Optimize.py:62-63,75-80`). Live dashboard pushes via
`sync_publish`: `general_info` (started_at, `trial X/Y`, objective, exchange type,
leverage, cpu_cores), `progressbar` (current, ETA seconds), and `best_candidates`
(`Optimize.py:336-351,407-449`).

**What the completion LEDGER records.** Two layers:
1. **Optuna SQLite study** — every trial's params, distributions, value (score),
   and `user_attrs` (full train + test metrics) (`Optimize.py:302-313`).
2. **`OptimizationSession` DB rows** — `update_optimization_session_trials(session_id,
   completed_trials, best_trials, n_trials)` flushed every 5 trials and at the end
   (`Optimize.py:398-405,563-569`); status transitions `running → finished/stopped`
   (`Optimize.py:572,584,589`); exceptions persisted via `add_session_exception`
   (`Optimize.py:590-591`); strategy source code snapshotted at start
   (`__init__.py:66-97`). `best_trials` is a sorted top-N (default
   `best_candidates_count = 20`, `Optimize.py:377-391`), each entry carrying `trial`,
   `params`, `fitness` (rounded), `dna` (base64 of sorted-JSON params,
   `Optimize.py:355-357`), and train/test metrics. Only `score > 0.0001` trials are
   kept (`Optimize.py:354`).

**Resume.** On restart the session's `completed_trials` and `best_trials` (JSON)
are reloaded, `inf` scrubbed to null, progressbar/counter fast-forwarded
(`Optimize.py:180-224`).

### 2.B Lean

**Parameter space declaration.** Parameters live in the project config
(`config.json parameters{}`), surfaced as `QCParameter(key,value)`. For optimization
each is turned into an `OptimizationStepParameter(name, min, max, step[, minStep])`
(`Common/Optimizer/Parameters/OptimizationStepParameter.cs:24-113`) or a
`StaticOptimizationParameter` (pinned constant). CLI wire form:
`--parameter <name> <min> <max> <step>` (`lean-cli/lean/commands/optimize.py:92-95,
188-190`). Validation is strict: `min <= max`, `step > 0`, `minStep > 0`,
`step >= minStep` (`OptimizationStepParameter.cs:62-109`).

**Objective/constraint model.** Both derive from `Objective(target, targetValue)`
(`Common/Optimizer/Objectives/Objective.cs`), where `target` is a **JSON path** into
the backtest result (bare names default to `Statistics.<name>`, `Objective.cs:68-73`;
path resolved case-insensitively by `Target.GetTokenInJsonBacktest`,
`Objectives/Target.cs:106-129`).
- **Target** carries an `Extremum` (a `Func<decimal,decimal,bool>` comparer —
  Maximization/Minimization, `Objectives/Extremum.cs:26-46`). `MoveAhead(json)`
  reads the target token and returns true iff it beats the incumbent
  (`Target.cs:72-93`); an optional `targetValue` lets the run **stop early** once
  reached (`Target.cs:98-104,131`, wired to `Reached`→`TriggerOnEndEvent`,
  `LeanOptimizer.cs:117-121`).
- **Constraint** carries a `ComparisonOperatorTypes` operator; `IsMet(json)` reads
  its token and compares to `targetValue` (`Objectives/Constraint.cs:61-77`).
  Constraints are hard filters — a violating backtest is simply dropped
  (`StepBaseOptimizationStrategy.cs:162`).

**Search strategies (deterministic, exhaustive-family).**
- **GridSearch** (`Optimizer/Strategies/GridSearchOptimizationStrategy.cs`): on the
  seed result it emits the **entire** Cartesian product at once via `Step(params)`
  → `Recursive(...)` (`StepBaseOptimizationStrategy.cs:178-234`); each subsequent
  result only updates the incumbent (`ProcessNewResult`, lines 47-51). Total count is
  `∏ floor((max-min)/step)+1` (`GetTotalBacktestEstimate`, lines 113-146).
- **EulerSearch** (`Optimizer/Strategies/EulerSearchOptimizationStrategy.cs`):
  a multi-resolution refinement. Run the current grid; once all in-flight sets
  finish, if any parameter's `step > minStep`, build a **finer, narrower** grid
  centered on the best point (`newStep = max(minStep, step/segments)`,
  window `±(newStep * segments/2)`, lines 92-121) and recurse; stop when no
  parameter can shrink further (lines 123-127). This is coordinate zooming toward a
  local optimum — cheaper than full grid, but still local and gradient-free.
- Step defaulting: if a param omits `step`, it's computed as
  `|max-min| / DefaultSegmentAmount` and `minStep = step/10`
  (`StepBaseOptimizationStrategy.cs:191-200`); CLI default `default-segment-amount = 10`
  (`optimize.py:262-265`).

**Fan-out + aggregation.** The abstract `LeanOptimizer`
(`Optimizer/LeanOptimizer.cs`) is the engine:
- Strategy raises `NewParameterSet` → `LaunchLeanForParameterSet` (lines 130-139).
- Concurrency is capped by `NodePacket.MaximumConcurrentBacktests`; over the cap,
  sets go to a `ConcurrentQueue PendingParameterSet` (lines 442-456). Each finished
  backtest dequeues exactly one pending set — a steady-state pipeline (lines 258-261).
- Each parameter set becomes a **separate Lean backtest process** via the abstract
  `RunLean(...)` (line 224); `ConsoleLeanOptimizer` (Optimizer.Launcher) launches OS
  processes. The CLI runs the whole Optimizer.Launcher inside **one Docker container**
  (`optimize.py:333-343`); default `max-concurrent-backtests = floor(cpu_count/2)`
  (`optimize.py:279`). **Note:** joblib appears in lean-cli only for *data download*
  (`components/cloud/data_downloader.py:111-117`), **not** for optimization fan-out.
- Results arrive on many threads → `NewResult(json, backtestId)` under a lock
  matches the id back to its `ParameterSet`, increments completed/failed counters,
  extracts metrics, drops the heavy JSON, and calls `Strategy.PushNewResults`
  (lines 239-300). When `RunningParameterSetForBacktest` empties, `TriggerOnEndEvent`
  fires (lines 291-293).
- **Aggregation/analysis.** On end, `OptimizationAnalyzer.Run(...)` builds an
  `OptimizationAnalysis` over all completed backtests: Sharpe summary
  (mean/std/min/max/median), best backtest, **per-parameter slicing**, **clustering**,
  **modes**, and **failed-backtest** breakdown
  (`Optimizer/Analysis/OptimizationAnalyzer.cs:33-70`). This is a genuine
  overfitting/sensitivity report Jesse lacks.

**What gets LOGGED / the LEDGER.** Runtime stats dict — Completed, Failed, Running,
In Queue, Average Length, Total Runtime (`LeanOptimizer.cs:326-342`) — pushed every
`optimization-update-interval` (default 10s) via `SendUpdate` (lines 36,415-434).
The winner is logged as `Result for <target>: … ParameterSet: (...) backtestId '...'`
(lines 179-181); the CLI greps that line and loads `<optimal_id>.json` to print the
optimal parameters + full statistics table (`optimize.py:379-397`). Each backtest's
own result JSON is persisted to the output folder. `--estimate` computes total
backtests × last runtime ÷ concurrency without running (`optimize.py:367-377`).

---

## 3. Jesse vs Lean — which fits QMX

| Dimension | Jesse | Lean | Fit for QMX |
|---|---|---|---|
| Space declaration | `hyperparameters()` dicts (int/float/categorical, min/max/step, default) | `OptimizationStepParameter` (numeric min/max/step) + static | **Jesse's schema** — categoricals + defaults + typed params map cleanly to a config block; Lean has no native categorical. |
| Search | Uniform random (`np.random`), Optuna = ledger only | Grid (exhaustive) + Euler (multi-res refine); deterministic | **Neither is state-of-the-art.** QMX should adopt **real Optuna/TPE-class** search (see §5). Keep Grid as an optional exhaustive mode for small spaces + reproducibility. |
| Objective | Compound `total_effect_rate * ratio_normalized`, single scalar, opinionated | Any result JSON-path, min/max, optional early-stop target | **Lean's model** — target = a named metric + direction is cleaner and less opinionated than Jesse's baked-in fitness. Offer Jesse's trade-count gate as an *optional constraint*, not a hardwired multiplier. |
| Constraints | None (only ratio<0 / <5-trades gates) | First-class `metric op value` filters | **Lean's constraints** — essential for quant agents ("Drawdown < 25%"). |
| Train/test | In-sample score + out-of-sample reported (not scored) | Single window | **Jesse's split** — out-of-sample reporting is exactly what an agent needs to judge overfit; go further and reserve a locked validation window. |
| Fan-out | Ray, object-store shared inputs, sliding window (`cpu*2`) | Separate processes, `MaxConcurrentBacktests`, pending queue | **Hybrid:** Lean's bounded queue + Jesse's shared-immutable-inputs idea. For 12-14 concurrent, a work-stealing pool with a hard concurrency cap. |
| Post-hoc analysis | Top-N table + train/test string | Slicing, clustering, modes, failed-backtest, Sharpe distribution | **Lean's analyzer** — QMX should ship parameter-sensitivity + clustering as the anti-overfit deliverable. |
| Persistence/resume | Optuna SQLite + `OptimizationSession` rows, resume from N | Per-backtest JSON + winner log line | **Jesse's session/resume** semantics fit QMX's LEDGER + long unattended runs. |

**Verdict:** QMX takes **Jesse's parameter schema + train/test/resume/session
model**, **Lean's target+constraint objective model + post-hoc sensitivity analysis**,
and **replaces both search cores** with a proper Bayesian/TPE sampler (Optuna used as
an *actual sampler*, not a ledger), with Grid as an optional exhaustive fallback.

---

## 4. QMX spec draft (requirements, mapped to QMF where obvious)

**QMX framing:** optimization is a config-materialized Study over a Book/BMS — the
operator's wind-tunnel: the strategy is the model, the parameter space + windows +
objective are the dials. A quant *agent* in a sandbox declares the space and reads an
unbiased pass/fail LEDGER at the end.

### 4.1 Parameter space (config-driven)
- **OPT-1** A Book/BMS config MUST declare a parameter space as a list of typed
  parameters: `int`, `float`, `categorical`. Numeric params carry
  `min`, `max`, optional `step`, `default`; categorical carries `options`, `default`.
  (Adopt Jesse's schema; reject Lean's numeric-only limitation.)
- **OPT-2** The space MUST be part of the materialized config the CLI consumes
  (creating the Study writes it) — never a code edit to swap the "tunnel."
- **OPT-3** Numeric ranges MUST validate `min <= max`, `step > 0`,
  `step <= (max-min)`; categorical `options` non-empty. Invalid space → **typed
  refusal** (QMF), not a silent clamp.
- **OPT-4** Any numeric parameter that is money MUST be exact integer minor units
  (QMF exact-integer-money); step/min/max for money params are integers.

### 4.2 Objective + constraints
- **OPT-5** The objective MUST be `{ metric, direction(min|max) }` referencing a named
  result metric (Lean's model), NOT a hardwired compound score. Optional
  `target_value` MAY stop the Study early when reached.
- **OPT-6** The config MUST support N hard **constraints** `{ metric, op, value }`
  with ops `< <= > >= = !=`; a trial violating any constraint is **excluded** from the
  winner set but still LOGGED (with the violated constraint named).
- **OPT-7** A minimum-trades gate MUST be expressible as a constraint (Jesse's `<5`
  rule generalized), defaulting on so degenerate zero-trade fits never win.
- **OPT-8** Every objective/constraint metric MUST resolve against the run's result
  record; an unresolvable metric name → typed refusal at Study creation, not at
  trial time.

### 4.3 Train / test / validation
- **OPT-9** Each trial MUST score on an **in-sample (training)** window and MUST also
  run and RECORD an **out-of-sample (testing)** window with identical params; the
  objective is computed on training only, testing is reported for overfit judgment
  (Jesse's split).
- **OPT-10** The config MUST support a third **locked validation window** never touched
  during the Study; the LEDGER's final pass/fail MAY require the winner to also clear
  constraints on validation (QMX's "unbiased end result").
- **OPT-11** All window boundaries MUST be UTC-ns (QMF time law); warm-up candle
  counts MUST be explicit and reported.

### 4.4 Search + fan-out (12-14 concurrent)
- **OPT-12** QMX MUST provide a **Bayesian/TPE-class sampler** as the default search
  (real Optuna semantics: past trials inform the next), NOT uniform random.
  Rationale: Jesse's `np.random` sampler (Optimize.py:226-259) is naive random search
  mislabeled as "Optuna"; industry norm is TPE/CMA-ES/Bayesian.
- **OPT-13** QMX MUST also offer an exhaustive **Grid** mode for small spaces (Lean
  GridSearch) and SHOULD offer a **coordinate-refinement** mode (Lean Euler) for
  cheap local zoom; the chosen mode is a config field.
- **OPT-14** The engine MUST run a bounded concurrent pool with a hard cap
  (`max_concurrent_trials`, default tuned to **12-14**) and a pending queue: launch up
  to the cap, and each completed trial dequeues the next (Lean's pending-queue
  pipeline, Jesse's sliding window). No unbounded fan-out.
- **OPT-15** Large immutable inputs (candle sets, config, routes) MUST be shared
  once across workers, not re-serialized per trial (Jesse's `ray.put` pattern).
- **OPT-16** Each trial MUST run in isolation; one trial's crash MUST be counted as
  **failed** and MUST NOT abort the Study (Lean's failed-count semantics,
  LeanOptimizer.cs:250-254).
- **OPT-17** The trial budget policy MUST be explicit in config (fixed N, or
  scale-with-#params like Jesse's `params * 200`, or run-until-target/timeout).
- **OPT-18** A running Study MUST be terminable by the operator, transitioning to a
  clean `stopped` state with partial results preserved (Jesse's termination poll).

### 4.5 Logged-per-trial vs completion LEDGER
- **OPT-19 (LOG, during run)** Per trial the system MUST LOG: trial id, sampled
  params, world label (`live|replay|simulated` — QMF result-label law; optimization is
  **simulated/replay**), objective value, key train metrics (pnl%, win-rate, trade
  count, chosen ratio), constraint pass/fail, and status (usable / negative /
  nan / below-min-trades / failed). Progress MUST publish current/total + ETA.
- **OPT-20 (LEDGER, at completion)** The Study MUST SAVE a durable ledger record:
  Study id, strategy id, full parameter space, objective+constraints, all three window
  bounds (UTC-ns), sampler + mode, total/completed/failed counts, runtime, and the
  ranked **top-N candidates** each with params, a reproducible parameter fingerprint
  (Jesse's base64 "DNA" generalized to a stable content hash), train metrics, test
  metrics, and validation metrics if run.
- **OPT-21 (Unbiased pass/fail)** The ledger MUST record a single **pass/fail verdict**
  for the winner determined by objective + constraints on the reserved validation
  window (or explicitly "not validated"), so the result is unbiased by the in-sample
  fit — the operator's "unbiased end result."
- **OPT-22 (Sensitivity/anti-overfit)** The completion record MUST include a
  **parameter-sensitivity analysis** over all completed trials: per-parameter slices,
  objective distribution (mean/std/min/max/median), and clustering of good regions
  (Lean's OptimizationAnalyzer). A winner that is an isolated spike (unstable
  neighborhood) MUST be flagged.
- **OPT-23 (Resume)** A Study MUST be resumable from its persisted trials without
  re-running completed work (Jesse's session resume).
- **OPT-24 (Estimate)** The system SHOULD offer a dry-run estimate (total trials ×
  typical trial runtime ÷ concurrency) before committing (Lean `--estimate`).
- **OPT-25 (Refusals)** All failure surfaces (missing candles for any window, bad
  space, unknown metric, cpu/concurrency out of range) MUST be QMF **typed refusals**
  with actionable messages — mirroring Jesse's hard-won fix where a candle shortage
  used to hang API callers (optimize_mode/__init__.py:32-144).

---

## 5. Open questions

1. **Sampler choice.** TPE (Optuna default) vs CMA-ES vs GP-Bayesian vs Hyperband/
   ASHA pruning — which default, and do we prune unpromising trials mid-backtest
   (Jesse/Lean never prune)? Pruning needs intermediate objective values per trial.
2. **Objective on train vs test.** Jesse scores on train and only *reports* test.
   Should QMX optionally score on a train/test blend or penalize train-test gap to
   fight overfit directly, rather than leaving it to the human?
3. **Multi-objective.** Lean and Jesse are both single-scalar. Do quant agents need
   Pareto-front multi-objective (e.g. maximize Sharpe AND minimize drawdown)? Optuna
   supports NSGA-II; both references do not.
4. **Money-metric normalization.** Jesse hardcodes normalization bounds
   (`sharpe→(-.5,5)`). QMX with exact-integer money must define how ratios/returns are
   computed and bounded without float drift.
5. **Concurrency unit.** Jesse = Ray tasks in-process; Lean = separate processes/
   Docker. For QMX's 12-14 target, are trials threads, processes, or sandboxed
   containers — and how does that interact with the QMX sandbox isolation model?
6. **DNA/fingerprint stability.** Jesse's base64-of-sorted-JSON is fragile across
   float formatting. QMX needs a canonical, stable parameter fingerprint for
   dedup/resume/ledger cross-reference.
7. **Validation-window governance.** Who sets the locked validation window, and is the
   pass/fail verdict allowed to be computed more than once (which would leak the
   holdout)? Single-shot validation is the honest choice.
8. **Grid explosion guard.** Lean will happily enumerate millions of sets. Should QMX
   refuse/require confirmation above a configurable grid-size threshold?
