# PRD Discovery — QMB (Backtesting / Experimentation) Spec Set

Role: PRD discovery extractor. Scope: user-facing features and capabilities
(candidate functional requirements), operator workflows, and scope rulings.
Capabilities only — implementation detail deliberately stripped.

Source set (all under
`_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/`):
- `backtesting-direction-position.md` (v2 position paper)
- `research-backtesting/rulings-for-backtesting.md` (inherited invariants)
- `research-backtesting/specs/INDEX.md` + 13 reverse-engineering specs
- `research-backtesting/specs/website-visuals.md` (competitor feature bar)

Note on status: this whole set is **pre-build direction**, not ratified product.
The spec authors reverse-engineered Jesse + QuantConnect Lean for *mechanism*,
then drafted QMX requirements. Verdict-bearing backtests are explicitly deferred
(GAP-0048/0049 + the backtesting sitting). Treat everything below as candidate
functional requirements for the PRD to select from, not settled scope.

---

## 0. Umbrella framing and naming (from the position paper)

- **The product is a library, not a framework/engine.** Operator vocabulary,
  ratified as direction: **"experimentation"** is the umbrella capability;
  **"backtesting"** is the verification stage within it. QMF stays the only
  "framework". (DC-5)
- **CLI command name = `qmx`.** (DC-5)
- **One library, many thin doors.** The same computation library is reachable
  three ways the operator/agents actually use: **Python API** (in-process /
  notebooks), **CLI** (one-shot process — the natural agent tool in factory
  sandboxes), and **MCP** (long-running server). A **UI backend** consumes the
  Python API. All doors expose the same capabilities. (DC-1)
- **Surfaces implied across the whole set:** (1) a **CLI**; (2) a **charts UI /
  web UI** (the "UI backend"); (3) a **website** (marketing/trust surface,
  informed by website-visuals); (4) **notebooks / research scripts** (Python
  API). MCP is an optional door, never required to use any capability.
- **State-sync as a first-class operator concern (DC-2).** Sandboxes and laptops
  carry a fingerprinted registry snapshot; a "sync hub" re-syncs when reachable;
  the operator gets **honest staleness** when offline (a stale-evidence refusal
  on a superseded reference). This is the "the CLI updates automatically" ask,
  scoped honestly.
- **Portability, scoped:** the tooling is a `uv`/`pip`-installable pure library
  that runs anywhere (sandbox, bare laptop, plain VS Code) with no server and no
  Docker. BUT governed/sealed evidence never leaves controlled rooms; external
  contexts get only unsealed, split-governed exports.

### Cross-cutting operator capabilities (appear in nearly every spec)

- **Wind-tunnel model:** creating/editing a **Book/BMS materializes a config**
  the CLI consumes. The operator changes *variables* (dials), never swaps the
  *tunnel* (engine). Editing a Book/BMS mints a new version, never mutates.
- **Log-during / save-at-completion:** every run streams progress/logs while
  live and writes one immutable result into a **ledger** at completion, with a
  single **unbiased pass/fail end result**.
- **World label on every result:** `live | replay | simulated`. `simulated` is
  reserved-unusable for edge/validation in V1; a paper/replay PASS must never be
  mistaken for a live one.
- **"Configurable" = UI-editable** everywhere (standing global rule): every
  configurable variable must surface as UI-editable at platform level.
- **Concurrency target: 12–14 concurrent tasks** is the recurring load figure
  the operator wants supported.

---

## 1. Inherited scope rulings (rulings-for-backtesting.md)

These are invariants the backtesting work inherits from the venue + risk
sittings. PRD-relevant capability/scope content only:

- **Binding chain = bot → Book → BMS → account.** The Book owns admission,
  sizing, doors, leash, profile selection; the BMS owns accounting, constraints,
  journals, KSA policy, reporting. Nothing above a bot touches the market.
- **Everything ships as Defaults + Versions + Copies.** GitBook shapes are
  default v1 templates; adding a broker account offers a *copy* of chosen
  defaults bound to that account. UI edits mint new versions, never mutate.
- **Book/BMS templates are structured config artifacts** where **every variable
  is declared UI-editable vs uneditable in the template itself.**
- **Kill switch vs kill line (operator-facing distinction):** kill switch =
  global black-swan emergency stopping ALL trading incl. paper (human
  de-escalates); kill line = per-Book capital floor that auto-flattens that
  Book's scope on breach. Operator may flatten anything at any time (inalienable).
- **Exit ownership (V1):** Book owns exit policy; bots *propose* risk-reducing
  exits through a versioned Book door; the Book executes or refuses with a
  recorded reason. Typed why-it-closed label on every close
  (SL/TP/trailing/session/hedge/KS/manual/broker).
- **Stop-out = exit at ~full planned loss (−1R).** Breakeven exits do NOT count
  toward the bench (recorded as their own metric). Bench counter counts
  stop-outs; threshold is per-bot and emphatically configurable.
- **Every position must declare its planned full-loss price BEFORE it opens** —
  no declared price ⇒ invalid-input refusal at admission. A strategy that
  deliberately runs with no planned loss point cannot trade in QMX.
- **USD is the system-wide numeraire;** non-USD account bindings refused in V1.
- **News blackout stops ALL trading on an instrument — live AND paper, no
  exceptions.** Multi-pair bots blocked per-instrument only. Dead zone (daily
  no-session band + per-handover buffers) pauses NEW entries only; exits/safety
  never blocked. Calendar-dependent, absent for 24/7 crypto.
- **"The Book sets the bar":** admission bar = named unit-carrying requirements;
  "not yet ruled" is an allowed state; the bar **blocks live money only**.
- **Book/BMS validation before live:** NO performance probation, but a technical
  shakedown precedes live — (a) config linters + a "prediction linter"
  (can-this-Book-register-this-bot static check); (b) demo/paper
  connection-and-execution shakedown; (c) one operator signature on one
  assembled page.
- **Paper accounts = world live; paper = standing evidence state.** Frozen paper
  money never buys seats. Book modes are LIVE|PAPER; bot seats are
  active|benched (benched is collectible as data). Multiple demo accounts exist.
  Paper starting balance is a Book/family-scoped configurable default, sized for
  data-collection realism. Suppressed-decision journaling: a blocked bot's
  would-have-been actions are still recorded ("recording is not trading").
- **Experimentation freedom vs pre-registration (direction, GAP-0017):** likely
  synthesis = **experimentation free** (run whatever, whenever; occurrences log
  as raw material), **promotion strict** (evidence offered toward a Book seat /
  live money must belong to a pre-registered campaign with charter + split +
  budget).
- **Graduation path:** a working ungoverned/plain-Python experiment graduates
  into a governed indicator/family via an extension shape, **with a lineage edge
  back to the originating experiment.** The plain-Python escape hatch "is the
  point."

---

## 2. Per-spec extract (operator capabilities · scope rulings · exclusions)

### 2.1 The backtest loop (`spec-backtest-loop.md`)

**What the operator can do:**
- Run one strategy over a historical window and get a costed, world-labeled
  result — the base backtest capability.
- Run the *same* configured strategy as a backtest, a replay, or live: the world
  is a config choice, not a different product path.
- Specify a **warm-up period** (N bars or a duration) that builds indicator state
  without placing trades; get a typed error naming the exact instrument + date
  range if warm-up data is missing.
- Trust intra-bar fill fidelity (orders fill only if price is within the bar's
  range; multiple fills in one bar sequenced deterministically).
- Watch runs progress (throughput/data-points), cancel a run, and see runs fail
  fast and legibly rather than hang.

**Key scope rulings:**
- One loop for backtest/replay/live; only the injected clock + handler set
  differ. `world` stamped on every result.
- Deterministic/reproducible runs are a product promise (bit-for-bit for
  identical inputs+config); the ledger can assert reproduction as pass/fail.
- Sparse/heterogeneous data is first-class (ticks, quotes, mixed-resolution
  bars, funding events) — not a fixed 1-minute grid.
- Warm-up is trading-locked with an `is_warming_up` flag and a single
  `on_warmup_finished` transition.

**Exclusions / deferred:** verdict-bearing backtests need the fill model +
fidelity taxonomy (GAP-0048) — deferred. Distinguishing `replay` vs `simulated`
worlds precisely, ns-clock-vs-bar-data mapping, and corporate-action/funding
scope are open questions.

### 2.2 Synthetic data (`spec-synthetic-data.md`)

**What the operator can do:**
- Generate synthetic market data selectable by process: **block-bootstrap**
  (default, perturbs real history), **gaussian-resample**, **gaussian-noise**,
  **gbm** (true GBM, infra-stress only), and a candidate **regime-switching**.
- Configure a synthetic Book/BMS (process, seed, sigma, scenario count, date
  span, instrument) and have it recorded in the ledger alongside its run.
- Fan out N synthetic scenarios and get a robustness verdict: percentile bands
  (5/25/50/75/95), 90/95% CIs, p-value of the real path's rank, and an unbiased
  pass/fail against a *pre-declared* threshold.

**Key scope rulings (the L20 spine, central):**
- **Every synthetic run carries a machine-readable claim class:** `infra-stress`,
  `robustness` (allowed ONLY for processes seeded from real history), or
  `logic-smoke`. It **MUST NOT** assert edge / alpha / validation — a request to
  do so is a typed refusal.
- **Synthetic-origin data is tagged at the store level** (not just a filename);
  it is non-promotable to any live/replay context; any run consuming it inherits
  `world = simulated`. This closes the "generate favourable candles and book a
  Sharpe" backdoor.
- Determinism: seedable, bit-reproducible, QMX-owned version-pinned RNG.
- Forex-CFD specific: market-hours-aware time grid (weekend gap / session
  boundaries).

**Exclusions:** Lean's from-scratch "Brownian" generator's positioning as edge
data is rejected. Fat-tail/heavy-tail processes, regime-switching for V1, and
spread microstructure modeling are open questions. Synthetic never validates
edge — the operator's "synthetic sorts our data problem" hope is bounded by L20.

### 2.3 Multi-timeframe / multi-symbol + permutation sweeps (`spec-multi-routes.md`)

**What the operator can do:**
- Declare a **stream set** for a run: trading streams + data-only streams, each
  `{venue, instrument, timeframe, strategy?}`. Trade multiple symbols and
  timeframes at once.
- Read any declared stream from a strategy (multi-symbol/multi-TF coordination),
  with cross-stream position-change callbacks (peer open/close/increase/reduce/
  cancel) as the multi-agent coordination primitive.
- Declare a **sweep** over axes: `instruments[]`, `timeframes[]`,
  `parameters{name: values[]}`; the system expands the full Cartesian product,
  **reports the total run count before committing**, and executes each
  combination as one isolated, labeled ledger run.
- Aggregate/rank across sweep combinations (best/worst, constraint filtering)
  without re-running. A single run is just a 1×1×1 sweep.

**Key scope rulings:**
- At most one open **position** per (venue, instrument) per run; the same
  instrument may appear at multiple timeframes as data, and as a trading stream
  across different runs in a sweep.
- All trading streams in one run share one settlement asset (exact-integer
  accounting).
- One combo's refusal must not abort the batch — recorded as that combo's
  labeled outcome. Concurrency must not change any single run's result.
- MCP may drive sweeps but must not be required.

**Exclusions / open:** two simultaneously-traded TF strategies on one instrument
in one run (forbidden pending a use-case); cross-venue trading streams with FX
between quote assets; forming-bar exposure policy; guarding cross-combo rankings
against multiple-comparisons overfitting.

### 2.4 Parameter optimization (`spec-optimization.md`)

**What the operator/agent can do:**
- Declare a typed parameter space (int/float/categorical, min/max/step/default/
  options) in the Book/BMS config; run an optimization "Study".
- Set the objective as `{metric, direction}` plus N hard **constraints**
  `{metric, op, value}` (e.g. "Drawdown ≤ 25%"), with an optional early-stop
  target value.
- Get **train / test / locked-validation** windows: score in-sample, report
  out-of-sample, and (optionally) require the winner to clear constraints on a
  reserved validation window for the unbiased pass/fail.
- Choose search mode (config field): a **Bayesian/TPE-class** sampler (default),
  exhaustive **Grid** for small spaces, or coordinate-refinement.
- Run bounded-concurrent trials (cap tuned to 12–14) with a pending queue;
  terminate a Study cleanly (partial results preserved); **resume** a Study
  without re-running completed work; get a dry-run **estimate** before committing.
- Read a completion ledger: ranked top-N candidates (params + reproducible
  fingerprint + train/test/validation metrics), and a **parameter-sensitivity /
  anti-overfit analysis** (per-parameter slices, clustering; isolated-spike
  winners flagged).

**Key scope rulings:**
- Objective is a named metric + direction (not a hardwired compound score). A
  minimum-trades gate is expressible as a constraint, default on.
- Every stochastic surface records seed/generator provenance; unresolvable
  metric names refuse at Study creation, not at trial time.
- Single-shot validation (don't leak the holdout).

**Exclusions / open:** multi-objective / Pareto fronts, mid-backtest pruning,
train-test-gap penalties, and a grid-explosion confirmation threshold are open
questions. Jesse's "Optuna" that is actually uniform random is explicitly
rejected as the model.

### 2.5 Research / Jupyter surface (`spec-research-jupyter.md`)

**What the operator/agent can do:**
- `uv pip install qmx`, then `import qmx.research` in any Python env (sandbox,
  bare laptop, plain VS Code) — **no server, no daemon, no Docker, no browser,
  no notebook kernel required.** Notebooks are one supported host, not a
  dependency.
- Call a day-one function set: `history()`, `store_bars()/import_bars()`,
  synthetic/`fake_bars` generators (work with zero data access), `indicator()`
  over history returning a full time series, `backtest()` (pure, fan-out-safe),
  `portfolio_statistics()` to score any equity curve, `monte_carlo_*`,
  `optimize()`, `significance_test()`, and optional ML helpers.
- Get results as both a typed array/records fast path and a pandas-DataFrame
  view for interactive/agent inspection.
- Fan out 12–14 concurrent tasks safely (pure, process-safe functions).

**Key scope rulings:**
- The research surface is the **same library** the CLI/engine use — never a
  research-only reimplementation.
- Data governance across contexts: sealed/governed data readable only inside
  controlled rooms; off-sandbox, the same calls resolve only unsealed
  split-governed data or produce a typed refusal (never a silent partial).
  Synthetic/generator helpers always available in every context.
- Every result carries QMF law: exact-integer money, UTC-ns time, typed
  refusals, world label, injected clock (no reading the system clock).
- MCP exposure is an optional adapter over the same functions.

**Exclusions / open:** whether pandas is a core dependency vs `.to_frame()`
projection; a research-scoped governed scratch/artifact store (ObjectStore
analogue); walk-forward/CV in V1; the exact sealed-data-detection signal
off-sandbox.

### 2.6 CLI + config model / the wind tunnel (`spec-cli-config.md`)

**What the operator/agent can do (proposed command tree):**
- `qmx init` (scaffold workspace); `qmx book|bms|bot create|show|list|version`;
  `qmx backtest <bot> --book <v> --bms <v> --from --to [--var k=v]`;
  `qmx optimize`; `qmx research`; `qmx report <run-id>`;
  `qmx data download|generate|status`; `qmx config get|set|list|unset`
  (global/secret layer only); `qmx ledger list|show|find`;
  `qmx self update|version`.
- Author Books/BMSs via CLI (the CLI is the only writer); a
  researcher-friendly input shape is accepted and compiled into the strict
  internal fragment ("author simple, compile to strict").
- Get **"test = can a bot fit the Book"** as a compile-time fit check that
  refuses with the offending constraint.
- Inspect a stable, human-readable **resolved run-config artifact** per run
  ("what was run"), find any run by **id** or by **fingerprint**, and rely on a
  run fingerprint that excludes secrets/non-semantic fields (enables
  dedupe/reproducibility claims).
- Update the CLI like npm: **`uv tool install qmx` / `uv tool upgrade qmx`**;
  on invocation a throttled outdated-check prints the exact upgrade command,
  never auto-upgrading; update checks fail open offline and never block a run.
- Shell autocomplete from the CLI framework's native completion.

**Key scope rulings:**
- The engine consumes exactly one fully-resolved, immutable config per task
  (config is read-only data the engine cannot mutate). Layering is deterministic:
  run flags > bot > BMS fragment > Book fragment > QMX defaults, and every
  layer's contribution is attributable.
- Secrets/infra live in a separate layer, out of the fingerprint region.
- Crash-safe, concurrency-safe writes under 12–14 concurrent tasks; per-run
  isolation (no shared mutable global config).

**Exclusions / open:** exact fingerprint field classification; fragment↔engine
schema migration policy; the isolation primitive (process/container/in-process);
whether "fit" is static-only or needs a probe run; whether the engine is
in-process Python or containerized; ledger storage substrate.

### 2.7 Data download + organization (`spec-data-mgmt.md`)

**What the operator/agent can do:**
- `data download`: acquire a window by `(venue, symbol[list], start, end,
  resolution, side={bid,ask,both})`; default end = today or an explicit end for
  reproducible windows; fetch through swappable provider adapters (Dukascopy
  primary); preserve **bid and ask** as distinct streams; idempotent re-runs;
  `--overwrite` forces a new revision.
- `data verify` / `data gap-check`: detect gaps against the venue calendar,
  distinguish real absence (venue closed) from missing data (venue open, bars
  absent), refuse/flag bad provider ranges, and write a pass/fail integrity
  verdict — never silently fabricate data.
- `data list` / `data catalog`: answer "do I already have this window?" —
  per (venue, symbol, resolution, side): covered range, bar count, gap summary,
  provenance, license tag, revision.
- Rely on **machine-observable progress** (percent, ETA, date-reached) so a
  supervising agent can watch a long import.
- Get split/corporate-action manifest awareness and a symbol-identity map
  (deferred-relevant for equities/futures); a venue calendar keyed by
  (venue, security-type[, symbol]) with sessions, holidays, half-days, and an
  always-open mode for 24/7 crypto/FX.

**Key scope rulings:**
- **Acquisition posture (licensing gate):** QMX ships/redistributes **no data
  corpus**; the agent fetches under its own entitlement. Every ingested window
  records provenance + a license tag; a source lacking a redistribution/usage
  right yields a typed refusal, not a silent ingest. (The old Dukascopy corpus
  failed the licensing gate.)
- Organization borrows Lean's rigor: venue/security-type/resolution/tickType
  addressing, map/factor manifests, market-hours calendar — over QMX contracts
  (Parquet/DuckDB rooms, bitemporal, UTC-ns, exact-integer money).
- Interior gap-fill, if offered at all, is an explicit, flagged, separately-
  labeled derived layer (world=simulated) — never written as observed.

**Exclusions / open:** whether QMX offers synthetic gap-fill at all; bitemporal
`--overwrite` semantics; the license-tag taxonomy and who asserts it; whether
map/factor rooms are scaffolded now or deferred; calendar sourcing/provenance.

### 2.8 Reports (`spec-reports.md`)

**What the operator/agent can do:**
- Get **one canonical machine-readable result artifact (CT-32)** per completed
  run that serves both admission-bar evidence and the human/agent report — one
  artifact, two audiences, no drift.
- Read a curated metric set: returns/growth (net profit, CAGR, start/end
  equity), risk-adjusted ratios (Sharpe, Sortino, Calmar; extended:
  probabilistic Sharpe, Omega, serenity/ulcer; benchmark-relative alpha/beta/
  info/Treynor only when a benchmark is declared), drawdown/downside (max DD,
  recovery/underwater, VaR), trade stats (counts, win rate incl. long/short
  split, profit factor, expectancy, avg/largest win/loss, gross P&L, fees,
  durations, streaks, MAE/MFE, turnover), rolling 1/3/6/12-month windows
  (extended), and **QMX-native suppression + veto accounting** (so the report
  never reads QMX's own arbitration/refusals as strategy decay).
- Get chart data **as machine-readable series, never images**: equity curve,
  cumulative returns (vs benchmark when declared), drawdown/underwater + top-5
  worst-periods table, monthly-returns grid, monthly + trade-P&L distributions,
  annual/daily/per-trade returns, asset allocation and long/short exposure over
  time, leverage utilization, rolling Sharpe/beta.
- Get exactly one **unbiased pass/fail ledger line** per run (structural, not a
  judgment): PASS iff the artifact satisfies the declared admission bar for its
  account role. A PASS means "admissible evidence," not "good strategy."
- Render HTML (operator, shareable) and markdown (agent-consumable, diffable) as
  pure downstream functions; QMX ships **skills** that read the artifact (not the
  HTML) and produce plain-language interpretation / compare two runs.
- Configure which metrics/charts/tiers, annualization basis, rf model, and
  benchmark appear — all UI-editable.

**Key scope rulings:**
- Metrics computed once in the producer, re-read by the report (never recomputed
  ad hoc). Each metric's arithmetic is governed and versioned; changing how
  Sharpe is computed is a format-version mint with before/after evidence.
- No single score / rating / tier band / composite may express the result.
- Exact-integer money, UTC-ns/typed-duration time, unit-kinded measures (null
  unit-kind is a refusal). Measurement publishes, never acts (no sizing/
  promoting/benching from producing a report). Paper-role result must not gate
  live money.

**Exclusions:** Lean's hard-coded US-equity crisis windows (rejected; maybe
later as operator-declared regime windows); estimated strategy capacity
(US-equity market-impact, deferred); formatted-string metric values with baked-in
%/$; magic divide-by-zero caps (emit typed "undefined" instead).

### 2.9 Fills, slippage & fees (`spec-fill-fees.md`) — the hard core, GAP-0048

**What the operator can do (target capability, deferred for verdicts):**
- Select per Book/BMS a **fill model** (dispatching on order type: market,
  limit, stop, stop-limit, trailing-stop, market-on-open/close, bracket/OCO),
  a **slippage model**, a **fee model**, a **spread model**, and a
  **financing/swap model** — swap variables, not the tunnel.
- Choose fill realism: **bar-worst-case** (honest default) or an explicit
  **optimistic exact-price** mode that stamps a distinct fidelity label.
- Get partial fills / partial lots, reduce-only capping, deterministic
  intra-candle sequencing, and gap fills (each carrying a fidelity marker).
- Model retail-forex reality neither reference ships: a **synthetic spread**
  keyed by instrument × hour-of-day × session (widening at rollover / illiquid
  hours / weekends), an FX slippage catalog (spread-crossing default, gap/vol,
  size-tiered), forex commissions (per-lot / notional-proportional-with-minimum),
  and **daily swap/carry** (per-symbol, per-direction points, triple-swap day,
  weekend/holiday handling) applied as a distinct ledger event.
- See every cash effect (fill P&L, slippage, fee, swap) logged separately so the
  pass/fail result can decompose cost drag.

**Key scope rulings:**
- Every fill carries a **fidelity label** (world; price basis quote-real >
  quote-synthetic > trade-only; fill basis worst-case vs optimistic-exact; which
  models engaged). A run's ledger result carries the **lowest** fidelity of any
  fill in it, so pass/fail is never flattered by mixed fidelity. The CLI refuses
  to compare Books run at different fidelities without an explicit override.
- **This is confirmed original QMX work — no donor engine has a usable
  retail-forex model.** GAP-0048 is the hard, reference-less core; fidelity + the
  result-key tuple are flagged irreversible. Any interim fill run carries a
  `fidelity=optimistic` taint: it cannot spend split budget and cannot claim edge.

**Exclusions / open:** spread-table and swap-points provenance; optimistic vs
worst-case default; partial-fill liquidity proxy without volume; fee-currency
conversion timing.

### 2.10 Monte Carlo + rule significance (`spec-mc-significance.md`)

**What the operator/agent can do:**
- **Rule Significance Gate (primary, pre-build):** validate a bare **entry rule**
  before building a full strategy — run it signal-only (no orders) over the data
  window and get an empirical one-tailed p-value of whether the edge is
  distinguishable from luck. Configurable resampling scheme (iid fast default /
  block-stationary), ≥2000 iterations default; refuses (typed) below a minimum
  observation floor. The build pipeline MAY gate on this, but the verdict is
  advisory to the operator, never an auto-merge.
- **Monte Carlo robustness (two modes):** trade-order shuffle (sequence risk)
  and alternate-history moving-block bootstrap; both report per-metric
  percentiles, 90/95% bands, and a p-value/percentile rank of the original.
- Read **structured findings** (Lean-shaped): `{verdict, metric, statistic,
  threshold, plain-language issue, suggested action, severity}` — weight-ranked,
  budgeted, de-duplicated/muteable across polls — plus raw statistics, logged
  during the run and saved to the ledger with one unbiased pass/fail per run.
- Reproduce any distribution bit-for-bit from the recorded seed provenance.

**Key scope rulings:**
- Rule gate world = replay/simulated, never live.
- The gate sits **upstream** (cheap pre-filter); MC/PBO/CSCV sit downstream on
  survivors. The ledger shows the chain: gate → backtest → MC1000/PBO/CSCV →
  final pass/fail.
- **Governance battery integration (named):** MC 1000-path baseline, **PBO
  bands** (Probability of Backtest Overfitting), **CSCV S=16** (combinatorially-
  symmetric cross-validation, 16 folds) are required downstream tools.

**Exclusions / open:** iid vs block default; reconciling exact-integer money with
float log-return statistics; benchmark-relative edge test; auto multiple-testing
correction (deflated Sharpe / FDR) and recording trial count; exit-rule /
full-strategy significance variants; whether suggested-action text is a fixed
catalogue.

### 2.11 Concurrent runs (`spec-concurrency.md`)

**What the operator can do:**
- Run 12–14 tasks at once; each run is isolated, writes to its own room, streams
  its own logs, and commits to the shared ledger exactly once at completion.
- Set a governed concurrency cap with **enqueue-on-full backpressure** — excess
  runs queue, never drop or silently oversubscribe; requesting more than the host
  can serve is a typed refusal, not a hang.
- Rely on determinism across the fan-out: a run in isolation vs alongside 13
  siblings produces byte-identical results and the same fingerprint.
- Abort/kill one run without touching siblings; a run that dies mid-flight never
  appends a half-written ledger row (its absence is itself a recordable outcome).

**Key scope rulings:**
- The library never spawns threads/processes/async tasks of its own; parallelism
  is the orchestrator's concern (isolation by process only for CPU parallelism,
  not correctness).
- Default cap derived from host cores (not hard-coded); **memory is the real
  limiter** — the governor sizes by min(cpu_budget, ram_budget) and refuses when
  projected peak memory exceeds budget. IO-bound phases may oversubscribe; the
  CPU-bound sim phase must not.

**Exclusions / open:** which component owns the pool/governor; sandbox-vs-process
topology (one sandbox × N processes vs N sandboxes × 1); cross-run shared candle
cache; memory-estimate source; look-ahead-counter increment semantics.

### 2.12 Interactive charts (`spec-charts-ui.md`)

**What the operator/agent can do:**
- Get **one renderer-agnostic chart-data JSON artifact per run, per bot (route)**
  at completion, alongside the pass/fail result — candlesticks + execution
  markers + indicator overlays + horizontal levels + extra stacked panes.
- Have the QMX UI render it later; an agent can `json.load` and reason over it
  directly (self-describing: schema_version, time_unit, price_scale, world, per-
  series units, a `columns` legend for positional arrays).
- Use a strategy-facing drawing API (line-on-candle, horizontal level, extra
  pane) that validates every plotted value is finite and warns/refuses naming the
  series rather than silently poisoning the chart.
- Execution markers are semantic (`side` ∈ buy/sell, `effect` ∈
  open/increase/reduce/close) with `order_id` joining the order/trade ledger — no
  orphan markers.

**Key scope rulings:**
- `world` field mandatory on every chart artifact and surfaced by the renderer.
- Exact-integer money for prices/PnL; NaN/inf scrubbed to null with a typed
  count of drops per series. UTC-ns as source of truth (seconds on the wire for
  renderer compatibility).
- **Downsampling is mandatory** before writing (a multi-year minute backtest must
  not emit millions of raw candles by default); artifact size bounded; full-
  resolution is an opt-in config toggle. One bot = one artifact.
- Chart emission is a config toggle on the Book, default on for backtest/replay.

**Exclusions / open:** live/streaming chart deltas out of scope for V1 (completion
snapshot only); portfolio-analytics charts (equity/drawdown/etc.) belong with the
report/ledger metrics, not this contract; downsampling target density; multi-bot
synchronized view; whether the drawing API lets a strategy force explicit
glyph/color.

### 2.13 Website visuals / competitor feature bar (`website-visuals.md`)

Not QMX requirements — this is the **feature bar QMX will be measured against**,
and trust framing for the QMX website/marketing surface.

**What it establishes for the PRD:**
- **The validation ladder is table stakes:** backtest → optimize (with
  train/test split + overfitting guard) → Monte Carlo → rule significance testing
  → walk-forward. QMX's backtesting surface will be judged against the full
  ladder, not just "does it backtest."
- **The load-bearing trust claim is provenance:** "Real results, not
  hallucinations — every number comes from the engine; the agent calls real
  tools and reads real outputs." This is the single most important positioning
  claim for QMX's agent story.
- **Local-first / self-hosted / private-by-default** is marketed as a feature by
  both competitors — aligns with QMX's privacy stance.
- Competitor feature inventory worth mirroring/beating: agent/MCP pipeline ("one
  prompt, full pipeline"), interactive charts, ML-on-backtest-data, benchmark /
  batch-compare across timeframes/symbols/strategies, exports to CSV/JSON, saved
  results, algorithm reports, data download with vendor redundancy, multi-symbol/
  timeframe, partial fills, risk management, comprehensive indicator library.

---

## 3. Direction candidates ratified as PRD-binding direction (position paper §8)

- **DC-1 — One library, thin doors** (Python API / CLI / MCP; UI backend
  consumes the Python API; door parity guaranteed; MCP localhost-default, never
  stacked over HTTP).
- **DC-2 — Snapshot + hub state model** (immutable fingerprinted registry
  snapshots, dumb sync hub, `registry_as_of` + snapshot fingerprint in every
  label, stale-evidence refusal on superseded refs, honest offline staleness).
- **DC-3 — Donors narrowed** (mechanism only; no third-party engine code ever;
  Jesse's optimize sampler, MCP topology, floats/singletons, and its absent fill
  model all rejected).
- **DC-4 — Provenance-derived world** (world comes from input provenance via
  store-level taint; synthetic = infra-stress only until GAP-0048; interim fills
  carry fidelity=optimistic).
- **DC-5 — Names** (CLI = `qmx`; **experimentation** the umbrella,
  **backtesting** the verification stage; it is a *library*, never a
  framework/engine).

## 4. Top-level exclusions to carry into the PRD

- **Verdict-bearing backtests do NOT ship yet.** The replay *mechanism* (clock,
  data cursor, split-governed reads), data download, report rendering,
  research/analysis functions, and the doors themselves ship under standing law;
  edge-claiming backtests wait on GAP-0048 (fill model + fidelity taxonomy),
  flagged irreversible.
- **Synthetic data never validates edge** (L20) — infra-stress / robustness /
  logic-smoke claim classes only.
- **No bundled/redistributed data corpus** — agent fetches under its own
  entitlement; licensing gate enforced with typed refusals.
- **No composite "strategy score"** anywhere in reports.
- **Live/streaming charts, ML helpers (behind an extra), regime/crisis windows,
  strategy-capacity metrics, multi-objective optimization** — deferred / out of
  V1 core.
- **The spine stays AD-1..41** — these specs mint no new spine ADs; the library
  is application-side, and door/fidelity cargo is minted at the backtesting
  sitting.
