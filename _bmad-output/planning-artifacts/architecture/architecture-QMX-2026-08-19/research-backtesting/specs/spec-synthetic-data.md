# Spec: Synthetic Data Generation

Reverse-engineering spec for QMX. Sources read read-only: QuantConnect Lean
(Apache-2.0, C# engine + Python CLI) and Jesse (MIT, Python v3.0.6). Mechanism
understanding only — no third-party code is proposed for reuse (QMF law).

Operator priority: "it might save us." Scope for QMX: **forex CFD**, quant
**agents in sandboxes**, config-driven CLI, exact-integer money / UTC-ns time,
result labels carrying `world = simulated`, synthetic-origin tagging at the
store level, and QMX **law L20**: synthetic data stresses *infrastructure and
robustness*, it does **not** validate *edge*.

---

## 1. Feature claim (verbatim, with URL)

### Lean — "Generating Random Data"

> "This generator uses a Brownian motion model to generate realistic market
> data."

> "It is capable of generating data for most of LEAN's supported security types
> and resolutions, which makes it a good solution to design and test algorithms
> without the need to buy real financial data."
> — https://www.quantconnect.com/docs/v2/lean-cli/datasets/generating-data

From the CLI command help string (source, not marketing):

> "This uses the random data generator in LEAN to generate realistic market data
> using a Brownian motion model."
> — `lean-cli/lean/commands/data/generate.py:139`

Densities claimed (`generate.py:151-154`):
> "Dense: at least one data point per resolution step. / Sparse: at least one
> data point per 5 resolution steps. / VerySparse: at least one data point per
> 50 resolution steps."

**Positioning of Lean synthetic data:** Lean markets random data as a *cost
substitute for real data during algorithm development* ("without the need to buy
real financial data"). It does **not** claim the data validates a strategy's
edge. The word "realistic" is marketing over what the code shows is a
percent-bounded random walk (see §2) — there is no volatility clustering, no fat
tails, no regime structure. **Claim-vs-code gap: "realistic" is ABSENT in the
mechanism** beyond a bounded random walk.

### Jesse — "Monte Carlo Analysis"

> "Monte Carlo analysis tests how robust your trading strategies really are. It
> helps you find out whether your backtest results are due to genuine skill or
> just luck."

> Trade-Order Shuffling: "Tests whether the timing of your trades matters for
> your overall performance."
> Candles-Based: "Tests how well your strategy holds up under slightly different
> market conditions."

> Monte Carlo helps answer whether "my strategy's performance is due to skill or
> just luck" and "what range of results can I expect," exposing results that
> "only work for the original historical path" (overfitting).
> — https://docs.jesse.trade/docs/monte-carlo/

Internal (source) label, `monte_carlo_candles.py:400`:
> "📈 MONTE CARLO CANDLES (market-path robustness test)"

**Positioning of Jesse synthetic data:** Jesse markets synthetic candles as a
**robustness / luck-vs-skill** test — a perturbation around a *real* historical
path, never a from-scratch fabrication. This is much closer to QMX law L20 than
Lean's positioning. Note the honest limitation surfaced by third-party review
(WebSearch): Gaussian synthetic data "hides Black Swan risks" because real
returns have fat tails — a limitation QMX must state explicitly.

---

## 2. Mechanism — how the code actually does it

### 2A. Lean random data generator (from-scratch fabrication)

Data flow: CLI → Docker → C# ToolBox.

1. **CLI plumbing** (`lean-cli/lean/commands/data/generate.py:171-213`). The
   command builds a `dotnet QuantConnect.ToolBox.dll --app randomdatagenerator`
   entrypoint with every knob as a `--flag`, mounts the data dir `rw`, and runs
   the engine image in Docker. Supported security types include `Forex` and
   `Cfd` (`generate.py:42`). `--random-seed` is only appended when truthy
   (`generate.py:198-199`) — **so determinism is opt-in**.

2. **Settings parse + defaults** (`RandomDataGeneratorSettings.cs:53-335`).
   Parses dates (`yyyyMMdd`), resolution, density, market, per-symbol event
   probabilities. `RandomSeedSet` becomes `false` when no seed string is given
   (`:235-239`) — determinism flag distinct from the seed value itself.

3. **Determinism seeding** (`RandomDataGenerator.cs:52-60`). Two RNGs are
   created: a bare `new Random()` and a `RandomValueGenerator`. If
   `RandomSeedSet`, both are re-created seeded with the same
   `_settings.RandomSeed`. **Reproducibility depends on .NET's `System.Random`
   algorithm being stable across runtimes** — a portability caveat for QMX.

4. **Symbol generation** (`BaseSymbolGenerator.cs`). Random tickers are 3-char
   uppercase strings (`:231-244`) or drawn from the symbol-properties DB when no
   wildcard exists (`:182-201`); duplicates are rejected via a
   `FixedSizeHashQueue<Symbol>(1000)` with tail-recursive retry (`:63,164-173`).
   For forex/CFD there is a fixed universe, so `GetAvailableSymbolCount()` caps
   the request (`RandomDataGenerator.cs:64-69`).

5. **The price process (the core "Brownian motion")** — this is the load-bearing
   mechanism, in `RandomValueGenerator.NextPrice()`
   (`RandomValueGenerator.cs:138-203`):
   - `deviation = referencePrice * maxPctDev * (NextDouble() - 0.5)` — a uniform
     `[-0.5,0.5)` step scaled by the reference price and a max-percent bound
     (`:168`). **This is a bounded random walk, not true GBM** (uniform
     increments, not Gaussian; additive, not log-normal). The comment even calls
     it "a simple model of browning [sic] motion."
   - Step is floored to `MinimumPriceVariation` and sign-preserved (`:169`),
     rounded to tick size (`:171,205-209`), and clamped: prices near the tick
     floor are invalidated and the up-probability nudged (`:173-186`); a hard
     ceiling `_maximumPriceAllowed = 1,000,000` (`:32,188-193`); up to 10 retries
     then fall back to the reference price (`:194-200`).
   - **Drift is mean-reverting toward staying inside `[20*tick, 1e6]`, not a
     financial drift term.** No volatility state, no autocorrelation.

6. **Tick emission** (`TickGenerator.cs`):
   - `RandomPriceGenerator.NextValue()` chains `NextPrice` off the security's
     *current* price (`RandomPriceGenerator.cs:52-53`), so each tick is a step
     from the prior — that is what makes it a *walk*.
   - `GenerateTicks()` (`:60-129`) walks from `Start` to `End`, optional delayed
     IPO (`:67-71`), max deviation scaling *parabolically* with resolution
     (`GetMaximumDeviation`, `:274-279`: lower frequency ⇒ larger per-step
     moves).
   - `NextTickTime()` (`:222-272`) spaces ticks by density: Dense `0.5*rand`,
     Sparse `5*rand`, VerySparse `50*rand` resolution-steps (`:230-247`), then
     snaps out-of-market-hours ticks to the next market open, recursing at a
     finer resolution (`:256-268`). **Market-hours awareness is real and comes
     from `MarketHoursDatabase`** — relevant for forex weekend gaps.
   - Quote ticks synthesize bid/ask by two more `NextPrice` draws mirrored around
     the trade price so bid<price<ask (`:162-178`); trade sizes are
     `NextInt(1,1500)` (`:159,175-177`). Quote/trade mix set by
     `QuoteTradeRatio` (`:103`). **For forex/CFD Lean emits Quote ticks only**
     (`generate.py:144-145`).

7. **Corporate actions (equity only)** (`DividendSplitMapGenerator.cs`). Random
   splits/dividends/renames driven by monthly Bernoulli trials
   (`:89-92,178-221`), with split factors bounded so the cumulative
   `FinalSplitFactor` never drops below 0.001 (`:246-249`). Writes LEAN
   `factor_files` and `map_files`. **Irrelevant to forex CFD** — QMX can drop
   this entire subsystem for its money path.

8. **Aggregation + persistence** (`RandomDataGenerator.cs:216-272`). Ticks are
   consolidated into the requested resolution via `TickAggregator` and written by
   `LeanDataWriter` to the LEAN on-disk format (zipped CSV per symbol/resolution)
   into the mounted data folder. **Output is plain data files — carrying no
   provenance tag distinguishing them from real data** (a gap QMX must close).

**Key Lean data structures/formats:** `Tick{Time, Symbol, TickType,
Value, BidPrice/Size, AskPrice/Size, Quantity}`; consolidated `TradeBar`/
`QuoteBar`; on disk = LEAN zipped-CSV. Determinism = single 32-bit seed → two
`System.Random` instances.

### 2B. Jesse synthetic candles (perturbation of real data)

Jesse never fabricates from scratch. It **transforms real 1-minute candles**
through a pluggable pipeline, then re-runs the backtest on the transformed path
many times (Monte Carlo).

**Candle format:** numpy `ndarray` shape `(n, 6)` = `[timestamp, open, close,
high, low, volume]` (note **open=col1, close=col2, high=col3, low=col4**, from
the pipeline index usage in every `process()`).

**Pipeline contract** (`candle_pipelines/base_candles.py`):
- `BaseCandlesPipeline(batch_size)` holds an output buffer and `last_price`
  (`:5-8`). `get_candles()` (`:10-25`) drives regeneration once per `batch_size`
  window: on window start it sets `last_price` (first window = first open;
  later = last close of previous output, `:12-16`) then calls `process()`. This
  **carries price continuity across batches** — the synthetic path does not jump
  at batch seams.
- `process(original_1m_candles, out) -> bool` returns True if it modified `out`
  (`:27-35`).

Three concrete generators:

1. **Gaussian noise** (`gaussian_noise.py`). Adds a **cumulative** Gaussian walk
   to the close: `noise = normal(mu, sigma, n).cumsum()`, `close += noise`
   (`:41-42`). Open = previous close (`:45-46`); high/low get independent
   Gaussian perturbations (`:49-54`); then OHLC bounds are re-enforced
   (`high = max(o,c,h,l)`, `low = min(...)`, positivity floor `eps`,
   `:57-61`). **User supplies sigma explicitly** — it is a stress *amplitude*
   knob, not derived from the data.

2. **Gaussian resampler** (`gaussian_resampler.py`). Estimates the real series'
   own step statistics — mean and std of close-to-close deltas (`:27-29`) — and,
   if `sigma is None`, derives a scale factor from the data's relative-return std
   (`:32-43`), then regenerates the close as `normal(mu_delta, std_close,
   n).cumsum() + last_price` (`:45`). High/low deltas are likewise resampled
   from the real high-close and close-low gap statistics (`:53-63`). **This
   preserves the real data's volatility magnitude** but assumes Gaussian,
   i.i.d. increments — **destroys autocorrelation, volatility clustering, and
   fat tails.**

3. **Moving-block bootstrap** (`moving_block_bootstrap.py`) — the most
   defensible for markets. Computes the 3-tuple `(delta_close, delta_high,
   delta_low)` per bar (`:61-66`), then **samples overlapping blocks of
   consecutive tuples** and stitches them (`_bootstrap_blocks`, `:35-51`) to a
   length-n series, rebuilding prices by cumsum + `last_price` (`:69-82`), then
   re-enforcing OHLC bounds/positivity (`:85-89`). Block size is derived as
   `max(10, batch_size//10)` clamped to `[1, batch_size-1]` (`:27-29`). **Blocks
   preserve short-horizon dependence (autocorrelation, local vol clustering)**
   while randomizing the macro path — the standard econometric answer to the
   i.i.d. problem. Per-instance RNG via `np.random.default_rng(seed)` (`:33`);
   **seed defaults to None (independent scenarios), seedable for reproducible
   tests** (`:6-21`).

**Monte Carlo orchestration** (`research/monte_carlo/monte_carlo_candles.py`):
- Fans out `num_scenarios` (default 1000) backtests over **Ray** across
  `cpu_count * DEFAULT_CPU_USAGE_RATIO` cores (`:103-145`).
- **Scenario 0 is the untouched original** (pipeline disabled for `index==0`,
  `:66-67`); scenarios `>0` run the pipeline. Results are tagged with
  `scenario_index` so original vs simulated is unambiguous regardless of Ray
  completion order (`:82-83`).
- Aggregation computes, per metric (net profit %, max DD, Sharpe, win rate,
  annual return, Calmar), **percentiles (5/25/50/75/95), 90%/95% confidence
  intervals, and a p-value** = fraction of simulations ≥ original (reversed for
  drawdown) (`:188-265`). Significance flags at 5%/1% (`:263-264`).
- Output verdict is a **robustness table + equity-curve fan chart**
  (`:388-475`), interpreting where the original path ranks among perturbed paths
  ("top 5%", "bottom 25%"). **This is exactly QMX's ledger pass/fail shape.**

**Key Jesse data structures/formats:** `(n,6)` float ndarray candles;
per-scenario `MonteCarloCandlesScenarioResult{scenario_index, metrics,
equity_curve, trades}`; aggregate confidence-analysis dict with p-values.
Determinism = per-pipeline `default_rng(seed)`.

---

## 3. Jesse vs Lean — which fits QMX and why

| Dimension | Lean RandomDataGenerator | Jesse candle pipelines |
|---|---|---|
| Paradigm | Fabricate from scratch | Perturb / resample **real** history |
| Process | Uniform bounded random walk (mislabeled "Brownian") | Cumulative Gaussian walk; Gaussian resample; **moving-block bootstrap** |
| Preserves real market structure | No (no vol clustering, no fat tails, no regimes) | Bootstrap: **yes** (short-horizon dependence); Gaussian: no |
| Marketed as | "test algorithms without buying data" (cost substitute) | "robustness / luck-vs-skill" (perturbation) |
| Fit to QMX law L20 | Weak (positions synthetic as dev data) | **Strong** (positions synthetic as robustness) |
| Verdict shape | Raw data files, no verdict | Percentile/p-value robustness table = **ledger-native** |
| Concurrency | Single Docker run | **Ray fan-out (1000 scenarios)** ≈ QMX 12–14 concurrent tasks |
| Provenance tagging | None | Only `scenario_index` in-memory; no store tag |
| Forex/CFD relevance | Quote-only, market-hours aware; equity corp-actions irrelevant | Native (crypto, but process is asset-agnostic on OHLC) |

**Recommendation for QMX: adopt the Jesse *positioning and mechanism* as the
primary model, take two ideas from Lean.**

- **Primary = perturb-real-history** (Jesse's three pipelines), because (a) it
  honors L20 — a perturbation around real data can legitimately claim
  *robustness*, whereas a from-scratch walk can only claim *infra stress*; (b)
  the moving-block bootstrap is the only method here that preserves the
  properties that make forex CFD backtests meaningful; (c) the Monte Carlo
  percentile/p-value output is already the unbiased pass/fail verdict QMX's
  ledger wants; (d) Ray-style fan-out matches the 12–14 concurrent-task target.
- **Take from Lean:** (1) the **market-hours-aware time grid** (forex weekend
  gaps, session boundaries) — Jesse's crypto lineage assumes 24/7; QMX forex CFD
  must model the Sunday-open / Friday-close gap. (2) The **from-scratch bounded
  walk as a pure *infra-stress* generator** — useful precisely because it needs
  *no* real data (smoke-test the pipeline before any dataset exists), as long as
  it is labeled infra-only and never robustness.

---

## 4. QMX spec draft — requirements for our own generator

Requirements (WHAT), mapped to QMF contracts. Not code design.

### R1 — Config-materialized, not a separate tool (wind-tunnel)
Creating a synthetic Book/BMS **materializes a generator config** the CLI
consumes; the operator changes variables (process, seed, sigma, scenario count,
date span, instrument), never swaps the engine. The config MUST be a first-class
artifact recorded in the ledger alongside the run it produced.

### R2 — Generator process menu (forex CFD)
The generator MUST support, selectable by config:
- **`block-bootstrap`** (moving-block, from real history) — **default and
  recommended.** Preserves autocorrelation / volatility clustering. Config: block
  length (or derive from batch), scenario count, seed.
- **`gaussian-resample`** (data-derived sigma) — robustness with matched
  volatility magnitude; MUST be labeled as destroying autocorrelation/fat-tails.
- **`gaussian-noise`** (explicit sigma) — amplitude stress knob for perturbation.
- **`gbm`** (true geometric Brownian motion, log-normal, Gaussian log-returns) —
  a *correct* GBM, unlike Lean's uniform walk; **infra-stress only**, needs no
  real data.
- **`regime-switching`** (OPEN, see §5) — a multi-state (e.g. trend/range/
  high-vol) process for stress under regime change; candidate, not required v1.
MUST refuse (typed refusal) any process×instrument combo it cannot honor (e.g.
requesting corporate-action events on a forex instrument).

### R3 — Law L20 claim-labeling (the central requirement)
Every synthetic run's ledger result MUST carry an explicit, machine-readable
**claim class** bounding what it may assert. Exactly one of:
- **`infra-stress`** — exercises the pipeline / concurrency / storage / money
  math under load. Allowed for **all** processes incl. from-scratch `gbm`.
- **`robustness`** — "does the strategy survive perturbed *real* paths?" Allowed
  **only** for processes seeded from real history (`block-bootstrap`,
  `gaussian-resample`, `gaussian-noise`). MUST NOT be emitted for from-scratch
  processes.
- **`logic-smoke`** — "does the strategy *run* without erroring / does its logic
  fire?" Allowed for all processes.
The result label MUST NOT, under any process, assert **edge / alpha /
validation**. The generator MUST emit a typed refusal if a caller requests an
edge/validation claim on synthetic data. (L20 encoded as a contract, not a
docstring.)

### R4 — Provenance discipline (store-level synthetic-origin tag)
Every synthetic artifact (candle series, tick series, derived aggregates) MUST
be tagged **`origin = synthetic`** at the **store level**, not merely in a
filename — closing the exact gap where Lean writes indistinguishable data files.
The tag MUST record: process id, seed, source-dataset id (or `none` for
from-scratch), generator config hash, generation timestamp (UTC-ns), and QMX
generator version. A synthetic artifact MUST be non-promotable to any
`world = replay`/`live` context; loading synthetic data into a live/replay run
MUST be a typed refusal. Any run consuming synthetic data inherits
`world = simulated` in its result label (QMF).

### R5 — Determinism & reproducibility
- Config MAY set a seed; when set, the full artifact MUST be
  bit-reproducible from `{process, seed, source-dataset id, config hash}`.
- The RNG MUST be a **QMX-owned, version-pinned generator** (do not depend on a
  runtime's stdlib `Random`, per Lean's portability caveat). RNG algorithm +
  version recorded in provenance (R4).
- Multi-scenario fan-out MUST derive each scenario's substream from the master
  seed deterministically (e.g. seed + scenario index), so scenario `k` is
  reproducible in isolation, and scenario 0 MUST be the **untouched original**
  (Jesse pattern) when a real source exists.

### R6 — Money & time contracts (QMF law)
- Prices/quotes MUST be produced and stored as **exact integer money** (minor
  units / pips as integers), never float. (Both references use floats/decimals —
  QMX MUST convert at the boundary and enforce tick-size quantization on
  integers.)
- All timestamps **UTC-ns**. The time grid MUST be **market-hours aware** for
  forex CFD (weekend gap, session boundaries) — port Lean's market-hours snap,
  drop its equity assumptions.
- OHLC invariants (`low ≤ open,close ≤ high`, positivity) MUST hold after every
  transform (both references re-enforce this; QMX MUST too, on integers).

### R7 — Concurrency & ledger output
- MUST fan out `N` scenarios across the **12–14 concurrent-task** budget;
  progress **logged during** the run, full result **saved at completion** to the
  ledger.
- For `robustness`-class runs, the ledger entry MUST include the Jesse-style
  **percentile band (5/25/50/75/95), 90%/95% CI, and p-value** of the real
  path's rank among perturbed paths, plus an **unbiased pass/fail** derived from
  a config-declared threshold (e.g. "original in top X% of drawdown" ⇒ pass) —
  the verdict decided *before* the run, recorded in config, not chosen after.
- Scenario failures MUST be captured, counted, and reported (typed), never
  silently dropped beyond an explicit filtered-count line (Jesse pattern,
  `:173-185`).

### R8 — Refusal surface (typed)
Typed refusals for: edge/validation claim on synthetic (R3); promoting synthetic
to live/replay (R4); process×instrument mismatch (R2); missing source dataset
for a history-seeded process; non-reproducible request (seed required but RNG
version unavailable); OHLC/money invariant violation post-transform.

---

## 5. Open questions

1. **Regime-switching (R2):** worth building for v1, or is moving-block
   bootstrap sufficient for forex CFD robustness? Bootstrap preserves *observed*
   regimes in the source window but cannot invent an unseen regime; a
   Markov-regime GBM could stress unseen regime transitions — but only as
   `infra-stress`/`logic-smoke`, never `robustness`. Decision needed.
2. **Fat tails:** both references assume Gaussian increments and thereby "hide
   Black Swan risk" (third-party critique, confirmed in code). Should QMX offer
   a heavy-tailed process (Student-t / jump-diffusion) as a distinct
   *stress* class, clearly outside `robustness`?
3. **Block-length policy:** Jesse derives block length from batch size heuristically
   (`max(10, batch//10)`). Should QMX expose block length as an explicit,
   ledger-recorded config variable tied to the strategy's holding horizon rather
   than to a buffer size?
4. **Integer-money perturbation:** adding Gaussian noise then re-quantizing to
   integer pips introduces rounding bias at small sigmas. What is QMX's
   canonical rounding rule, and does it need a minimum-sigma floor to stay
   meaningful under integer quantization?
5. **Forex quote microstructure:** Lean synthesizes bid/ask by mirroring a
   spread around a mid via two extra draws. Does QMX need a spread *model*
   (e.g. session-dependent spread widening) for forex CFD synthetic quotes, or is
   a fixed/config spread sufficient for infra-stress and robustness?
6. **Scenario count vs task budget:** Jesse defaults to 1000 scenarios; QMX's
   concurrency budget is 12–14 tasks. Is a run "N scenarios queued through 12–14
   workers," and what is the default N that yields stable percentile bands
   without exhausting the ledger?
7. **"Original" scenario when there is no real source:** Jesse's scenario-0
   = untouched real path anchors the p-value. For from-scratch `gbm`/`infra-stress`
   there is no real anchor — the ledger MUST NOT compute a robustness p-value.
   Confirm the from-scratch path emits only infra/logic verdicts, never a band.
