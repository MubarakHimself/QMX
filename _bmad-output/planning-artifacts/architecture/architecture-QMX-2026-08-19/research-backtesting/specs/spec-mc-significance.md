# Spec: Monte Carlo + Rule Significance Testing

**Feature family:** Robustness toolkit — "test whether entry logic has an edge BEFORE spending hours building."
**Sources reverse-engineered:** Jesse v3.0.6 (MIT), QuantConnect Lean Engine (Apache-2.0).
**Rule:** mechanism understanding only — QMX builds its own; no third-party engine code is ever used.
**Date:** 2026-08-20.

---

## 1. Feature claim (verbatim, with URL)

### Jesse — Rule Significance Testing (the headline claim)

> "Ask the assistant to validate a new entry signal before you commit to building a full strategy around it. Jesse runs the rule against thousands of random-entry simulations and reports whether the signal has a real edge or is indistinguishable from luck."
> — https://docs.jesse.trade/docs/mcp/

> "By default, when you describe a brand-new strategy idea, the assistant will run this validation step first and only proceed to a full strategy build-out if the entry rule shows a real edge."
> — https://docs.jesse.trade/docs/mcp/example-workflow (paraphrase confirmed by web index; the MCP workflow gates the build on the RST result)

### Jesse — Monte Carlo Analysis

> "Trade-Order Shuffling — Tests whether the timing of your trades matters for your overall performance."
> "Candles-Based — Tests how well your strategy holds up under slightly different market conditions."
> "Monte Carlo analysis is an effective guard against overfitting."
> "If the original backtest is an outlier while most simulations perform worse, this indicates overfitting."
> Questions it answers: "Is my strategy's performance due to skill or just luck?" / "How well does my strategy work in different market conditions?" / "What range of results can I expect?"
> — https://docs.jesse.trade/docs/monte-carlo/ and https://docs.jesse.trade/docs/monte-carlo/interpreting-results

### Lean — no equivalent pre-build claim

QuantConnect/Lean markets **no** "test the rule before you build" feature. Its Monte Carlo and significance machinery are **post-hoc backtest diagnostics** surfaced as ranked findings after a full backtest completes (see §2, Lean). The marketed pre-build gate is **ABSENT** in Lean.

---

## 2. Mechanism — how the code actually does it

### 2A. Jesse — `rule_significance_test()` (the pre-build edge test)

Package: `jesse/research/rule_significance_testing/`. Public API: `rule_significance_test` and `plot_significance_test` (`__init__.py:12`).

Two phases (`rule_significance.py:40`):

**Phase 1 — Signal-only backtest** (`simulator.py:37`, `run_signal_only_backtest`)
- Runs Jesse's real candle engine but **submits zero orders**. It mirrors `_step_simulator()` initialisation (config, router, store, exchange/order/position state) but calls `candle_service.add_candle(..., with_execution=False, with_generation=False)` — no fills, no positions (`simulator.py:149`).
- At each completed bar it calls `route.strategy._execute_for_signal_test()` (`simulator.py:175`). That method (`jesse/strategies/Strategy.py:1333`) runs `before() / should_long() / should_short() / after()` exactly as a live bar would, then returns:
  - `+1` if `should_long()` is True, `-1` if `should_short()` is True, `0` otherwise; plus the bar close price (`Strategy.py:1368-1372`). The strategy stays permanently flat, so the test isolates the **raw entry signal**, not the position-management/exit logic.
- Returns three time-aligned arrays: `bar_timestamps` (int64 ms), `close_prices` (float64), `signals` (int8) (`simulator.py:190-194`).

**Phase 2 — Bootstrap significance** (`rule_significance.py:147-225`, `bootstrap.py`)
1. NaN/inf bars dropped with a warning (`rule_significance.py:137-145`).
2. **Log returns**: `log_returns = np.log(close[1:] / close[:-1])`; signals truncated to `signals[:-1]` so the signal at bar *t* is scored against the *next* bar's return — the first return not knowable at signal time (`rule_significance.py:152-153`). This is the look-ahead-safe alignment.
3. **Detrend by market mean**: `detrended = log_returns - log_returns.mean()` (`rule_significance.py:175-176`). Removes the market's drift so a rule with no skill has expected return 0 regardless of whether the market trended.
4. **Rule returns**: `rule_returns = signals * detrended`; neutral bars (signal 0) contribute 0 but stay in the count (`rule_significance.py:180`). `observed_mean = rule_returns.mean()` (`:181`).
5. **Bootstrap null** (`bootstrap.py:19` `run_bootstrap_test`):
   - `centered = rule_returns - observed_mean` — re-centre to zero to enforce H0: E[return]=0 (`bootstrap.py:37`).
   - Split `n_simulations` into `cpu_cores` batches (`_split_into_batches`, `bootstrap.py:80`). Per batch `i`: `rng = np.random.default_rng(random_seed + i)` (`:60`), then vectorised resample-with-replacement `idx = rng.integers(0, n, size=(batch_size, n)); batch_means = centered[idx].mean(axis=1)` (`:64-65`). Concatenate all batch means → the null sampling distribution.
   - **Seed provenance**: base seed defaults to 42 (`rule_significance.py:112`); each batch is `base + batch_index`, so the run is bit-reproducible given (seed, cpu_cores).
6. **p-value**: `p_value = mean(sim_means >= observed_mean)` — the one-tailed fraction of the null distribution at or above the observed edge (`rule_significance.py:215`).
7. **Annualisation**: `annualized_return = observed_mean * (minutes_per_365d_year / timeframe_minutes)` (`common.py:21-24`; crypto uses 365d, 24/7).

**Statistical shape:** a **stationary IID bar-level bootstrap** of a single "mean signed detrended log-return" statistic. Default `n_simulations = 2000` (`rule_significance.py:47`); warns below `MIN_OBSERVATIONS = 30` bars (`common.py:18`). Output dict: `observed_mean, annualized_return, simulated_means (ndarray), p_value, n_simulations, n_observations` (`rule_significance.py:218-225`).

**Known approximation:** resampling bars IID destroys autocorrelation/volatility clustering, so the null underestimates real-world variance of the mean → p-values are mildly optimistic for autocorrelated signals. Detrending is by simple arithmetic mean of log returns (not a benchmark).

### 2B. Jesse — Monte Carlo (two robustness modes, post-backtest)

Package `jesse/research/monte_carlo/`. Both default to **1000 scenarios** and parallelise with Ray (`ray.put` shared objects, 80% of cores — `common.py:11`, `DEFAULT_CPU_USAGE_RATIO`).

**Trade-order shuffle** (`monte_carlo_trades.py:130`)
- Run the real backtest once, extract `trades` + equity curve + starting balance (`:181-187`).
- Each Ray scenario (`_ray_run_scenario_monte_carlo`, `:96`): seed `BASE_RANDOM_SEED (42) + scenario_index` (`:106-108`), `random.shuffle(trades)` (`:110`), rebuild equity curve by re-applying shuffled PnL across the original time grid (`_reconstruct_equity_curve_from_trades`, `:277`), recompute metrics (`:305`).
- Confidence analysis (`_calculate_confidence_intervals`, `:367`) per metric ∈ {total_return, max_drawdown, sharpe_ratio, calmar_ratio}: percentiles 5/25/50/75/95, CI 90% (5–95) and 95% (2.5–97.5), and a p-value = `sum(sims >= original)/N` (reversed to `<=` for drawdown, `:414-417`). Significance flags at α=0.05 and α=0.01 (`common.py:34-35`). Tests only whether **trade ordering / path** drove results (sequence risk).

**Candles-based** (`monte_carlo_candles.py:103`)
- Scenario 0 = original; scenarios 1..N re-run the **full backtest** on **resampled candles** produced by a candle pipeline (`_ray_run_scenario_monte_carlo_candles`, `:49`).
- Default resampler: `MovingBlockBootstrapCandlesPipeline` (`jesse/candle_pipelines/moving_block_bootstrap.py`). It computes per-bar tuples `(Δclose, high-close, close-low)`, moving-block-bootstraps the 3-tuple rows (block length `max(10, batch_size//10)` clamped to data, `:27-29`; independent `np.random.default_rng(seed)` per instance, `:33`), then rebuilds a valid OHLC series by cumulative-summing bootstrapped Δclose onto `last_price` and enforcing high/low bounds + positivity (`:53-91`). Preserves short-horizon dependence while varying the path — tests **robustness to alternate market histories**.
- Same confidence-interval/p-value machinery (`_calculate_confidence_intervals_candles`, `:188`).

### 2C. Lean — post-hoc diagnostic battery (the closest comparable)

Lean has no pre-build signal test, but its **`ResultsAnalyzer`** runs a weight-ranked suite of diagnostics against a *completed* backtest and emits LLM-consumable **findings with suggested solutions** (`Engine/Results/Analysis/ResultsAnalyzer.cs:406-441`). Chain is weight-ordered, time-boxed (default 5s), capped at 10 findings, with in-run vs final modes and finding-muting after 3 reports (`ResultsAnalyzer.cs:214-258, 502-519`). Three members are directly comparable:

1. **`MonteCarloPercentileAnalysis`** (`Analyses/MonteCarloPercentileAnalysis.cs`)
   - Block bootstrap on **daily equity percent-change returns** (`:61`). `RunSimulation` (`:80`): `blockSize=20`, fixed `rng=Random(42)`, `nBlocks = n/blockSize + 1`, copy contiguous blocks from random starts to fill `n` returns, compound `∏(1+r)-1` → simulated total return (`:88-107`).
   - Flags "very optimistic / unusually lucky" when the backtest total return exceeds the **90th percentile** of simulated totals (`:73-75`). `Weight=69`, `RunsInRun=false` (needs the final equity curve, `:31`).
   - **Two code caveats worth noting as anti-patterns:** the caller passes `nSims: 5` (not the 5000 default) — only 5 paths (`:68`); and the percentile is `int Count / int Length * 100m` → **integer division** collapses to 0 or 100 (`:73`). QMX must not replicate either.

2. **`StatisticalSignificanceOfDailyReturnsAnalysis`** (`Analyses/StatisticalSignificanceOfDailyReturnsAnalysis.cs`)
   - Computes **excess daily returns over the SPY benchmark** and runs a **one-sample, one-tailed Student-t test** vs mean 0 (`OneSampleTAnalysis`, `:87`; `t = (mean-0)/(std/√n)`, two-tailed p from `MathNet StudentT`, halved for one-tailed positive direction, `:75-77, 104`). Flags when p>0.05 ("fail to reject H0 that mean excess return > 0"). `Weight=70`.
   - This is the **parametric** cousin of Jesse's bootstrap RST — but scored on realised strategy P&L vs benchmark, not on the raw entry signal, and only after a full backtest.

3. **`CrisisEventsAnalysis` + Report `Rolling`/`Crisis`** (`Report/Rolling.cs`, `Report/Crisis.cs`, `ReportElements/RollingSharpe*`, `RollingPortfolioBeta*`) — regime-window robustness (rolling Sharpe/beta, named crisis-period performance). Robustness reporting, **not** an edge/significance test.

**Verdict on Lean's pre-build claim:** ABSENT. Lean's MC + significance operate on a finished equity curve as a diagnostic; there is nothing that vets a bare entry rule before building.

---

## 3. Jesse vs Lean — which fits QMX

| Dimension | Jesse RST + MC | Lean ResultsAnalyzer |
|---|---|---|
| Pre-build edge gate | **Yes** — signal-only pass, then bar bootstrap. Direct match to the marketed claim | ABSENT |
| Null model for edge | IID bar bootstrap of signed detrended log-return; H0 via re-centring; empirical one-tailed p | Parametric one-sample t on excess-over-benchmark returns |
| MC path robustness | Trade-shuffle (sequence risk) + moving-block candle bootstrap (alternate histories); 1000 paths; per-metric CIs + p | Block bootstrap on daily returns, 90th-pctile "lucky" flag (5 paths as shipped) |
| Output shape | Numeric dict + sampling-distribution plot | **Ranked findings, each with a plain-language issue + suggested solutions**, weight-ordered, time-boxed, agent-facing |
| Reproducibility | Explicit seeds: base+batch_index (RST), 42+scenario_index (MC) | Fixed `Random(42)` |
| Cost | Cheap: one flat pass + vectorised numpy | Runs only after a full backtest |

**What QMX takes from each:**
- **From Jesse:** the *pre-build gate* is the money feature and the exact statistical procedure (signal-only isolation of the entry rule; next-bar look-ahead-safe alignment; detrend-then-recentre H0; empirical one-tailed p) — plus both MC modes (sequence risk vs alternate-history). This is what a quant agent needs to reject noise before burning compute.
- **From Lean:** the *agent-consumable governance layer* — weight-ranked findings that pair a verdict with a plain-language issue and concrete solutions, run under a time/finding budget, muteable. This is the right shape for QMX agents in sandboxes and for the ledger.
- **Reject:** Lean's shipped shortcuts (5 sims, integer-division percentile). Jesse's IID bootstrap is acceptable as the fast default but QMX should offer a **block/stationary bootstrap** variant so the null respects autocorrelation.

---

## 4. QMX spec draft (requirements — WHAT, not code design)

QMX ships one **Robustness Toolkit**: a config-driven battery the CLI materialises from the Book/BMS config (wind-tunnel: change variables, never swap the tunnel). Results are logged during the run and saved into the ledger with an unbiased pass/fail verdict. All procedures obey QMF law: exact integer money, UTC-ns time, typed refusals, result labels carrying the world (live/replay/simulated), seed provenance per run label (R-8).

### R-MC-1 — Rule Significance Gate (pre-build edge test) [PRIMARY]
- MUST evaluate a bare **entry rule** without executing any orders (signal-only pass over the config's data window), isolating the rule from exit/position logic.
- MUST align each signal to the **next** bar's return (no look-ahead), on log returns.
- MUST enforce H0 = "no edge" by (a) detrending returns by their in-sample mean and (b) re-centring the rule-return series to zero before resampling.
- MUST compute an empirical one-tailed p-value = fraction of null resamples with mean ≥ observed mean.
- MUST expose the resampling scheme as a config variable: `iid` (fast default, matching Jesse) and `block`/`stationary` (autocorrelation-respecting) with a configurable block length. Default iterations MUST be ≥ 2000.
- MUST return: `observed_mean` (exact-rational or documented float), `annualized_return`, `p_value`, `n_observations`, `n_simulations`, and the null distribution (for plotting/audit).
- MUST refuse (typed) when observations < a configured minimum (default 30) rather than silently returning; MUST emit a low-confidence warning label, not a hard number, below that floor.
- Result label MUST record world = `replay` (historical) or `simulated`, never `live`.
- The build pipeline MAY gate on this: a rule failing the gate at the configured α does not proceed to full build (evidence-based workflow), but the gate verdict is advisory to the operator, never an auto-merge.

### R-MC-2 — Monte Carlo path robustness (two modes)
- **Sequence-risk mode:** MUST re-order realised trades (shuffle) N times and re-derive the equity path and metrics, quantifying how much the *ordering* of trades drove the outcome. Money math MUST stay exact-integer through PnL re-accumulation.
- **Alternate-history mode:** MUST re-run the full backtest on resampled market paths generated by a **moving-block bootstrap of OHLC deltas** that preserves short-horizon dependence and always yields valid, strictly-positive OHLC. Scenario 0 = the true history.
- Both MUST report, per metric (return, max drawdown, Sharpe, Calmar, win rate, and any config-selected metric): percentiles (5/25/50/75/95), 90% and 95% confidence bands, and an empirical p-value / percentile rank of the original result within the simulated distribution (direction-aware: lower-is-better for drawdown).
- Default paths MUST be operator-configurable; **1000** is the baseline (see governance battery). MUST scale to the 12–14 concurrent-task load target via a worker pool; per-scenario seeds MUST be deterministic (`base_seed + scenario_index`) and recorded under R-8.

### R-MC-3 — Findings, not just numbers (agent/ledger layer, Lean-shaped)
- Each toolkit run MUST emit **structured findings**: `{verdict, metric, statistic, threshold, plain-language issue, suggested action, severity/weight}`.
- Findings MUST be weight-ranked, run under a configurable time/finding budget, and be de-duplicated/muteable across repeated runs so an agent is not re-flagged every poll.
- Findings and raw statistics MUST be logged during the run and **saved to the ledger at completion** with a single unbiased pass/fail end result per run label.
- Verdict vocabulary MUST map cleanly to QMF result labels and typed refusals (e.g. insufficient data → typed refusal, not a fabricated p-value).

### R-MC-4 — Provenance & reproducibility (R-8)
- Every stochastic procedure MUST record: RNG family, base seed, per-batch/per-scenario seed derivation, iteration count, resampling scheme + parameters, data window (UTC-ns bounds), and world label.
- Re-running with the same run label MUST reproduce the same distribution bit-for-bit.

### R-MC-5 — Governance battery integration (old QMX candidates)
The edge/robustness tools above are **feeders** into the standing governance battery. QMX MUST wire their outputs into:
- **MC 1000** — the 1000-path Monte Carlo baseline (R-MC-2) as the standard robustness sweep.
- **PBO bands** — Probability of Backtest Overfitting (Bailey/López de Prado): MUST be computable across the in-sample/out-of-sample metric distributions the toolkit produces; report PBO as a probability with confidence bands.
- **CSCV S=16** — Combinatorially-Symmetric Cross-Validation with 16 splits: MUST partition the evaluation window into 16 combinatorial train/test folds and report the rank-degradation / logit distribution feeding PBO.
- The Rule Significance Gate (R-MC-1) sits **upstream** of this battery (cheap pre-filter); MC/PBO/CSCV sit **downstream** on strategies that survive the gate and a full backtest. The ledger MUST show the chain: gate verdict → backtest → MC1000/PBO/CSCV verdict → final pass/fail.

---

## 5. Open questions

1. **Null model default** — ship IID bar bootstrap (Jesse parity, fast) or default to stationary/block bootstrap (more honest under autocorrelation) with IID as opt-in? Trade-off: speed vs p-value calibration.
2. **Money representation in the significance math** — RST operates on log returns (inherently float). How do we reconcile the "exact integer money" law with a log-return statistic? Proposal: exact integers for all PnL/equity paths (MC modes), float only inside the return-space statistic with documented precision and a fixed rounding contract.
3. **Detrend baseline** — Jesse detrends by the instrument's own mean; Lean tests excess-over-SPY. Does QMX want a benchmark-relative edge test (needs a benchmark series per Book) in addition to the self-detrended one?
4. **Multiple-testing / selection bias** — the pre-build gate invites running many rules and keeping winners. Should QMX auto-apply a multiplicity correction (e.g. Deflated Sharpe / BH-FDR across a session's tested rules) and record the number of trials in the ledger? This is where PBO/CSCV earn their place.
5. **PBO/CSCV inputs** — CSCV needs a per-fold performance metric surface across a parameter/strategy set. What is the canonical metric (Sharpe? the config's objective?) and how many parameter configs must exist before S=16 is meaningful?
6. **Exit-logic significance** — Jesse's RST tests only the entry signal (strategy stays flat). Do quant agents also need an "exit rule" or "full-strategy" significance variant, and what is its H0?
7. **Lean-style solutions text** — the suggested-action strings are valuable to agents but are hand-authored heuristics. Should QMX generate them from the finding type via a fixed catalogue, or leave them to the reviewing agent?
