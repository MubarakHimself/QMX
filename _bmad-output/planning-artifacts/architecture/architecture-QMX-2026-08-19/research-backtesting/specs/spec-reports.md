# Spec — Algorithm Reports (reverse-engineered from Lean & Jesse)

Reverse-engineering spec for QMX. Two source platforms read for mechanism only
(no code reuse, ever): **QuantConnect Lean** (Apache-2.0, C# engine + Python CLI)
and **Jesse** (MIT, Python, v3.0.6). Purpose: understand *how each marketed
report feature is actually achieved by reading the code*, then spec QMX's own
version — a canonical machine-readable result artifact that both quant **agents**
and the operator can read, with in-house skills interpreting it.

Cite key: Lean engine clone paths shown as `lean-engine/...`; Lean CLI clone as
`lean-cli/...`; Jesse as `jesse/...`. All under the local read-only clones named
in the task.

---

## 1. Feature claim (verbatim, with URL)

### Lean
From <https://www.lean.io/docs/v2/lean-cli/reports> (LEAN Report Creator):

> "The LEAN Report Creator is a program included with LEAN which allows you to
> quickly generate polished, professional-grade reports"
> "we hope that you can use these reports to share your strategy performance with
> prospective investors"

Report contents claimed — KPIs: *"Runtime Days," "Turnover," "CAGR," "Markets,"
"Trades per day," "Drawdown," "Probabilistic SR," "Sharpe Ratio," "Information
Ratio," and "Strategy Capacity."* Charts: returns-per-trade histogram, daily
returns bar chart, monthly returns heat map, annual returns bar chart,
cumulative returns equity curve, asset-allocation pie, drawdown with top-5
periods marked, rolling beta (6/12-mo), rolling Sharpe (6/12-mo), leverage
utilization over time, long-short exposure by asset class. Crisis events: *"The
report only contains the crisis event that occurred during your algorithm's
backtest period"* (16 named periods, DotCom 2000 → AI Boom 2022-present).
Generation: `lean report` → `./report.html` by default.

### Jesse
From <https://docs.jesse.trade/docs/backtest.html>:

> "Jesse's backtest engine is the most accurate available, simulating market
> conditions as faithfully as possible including fees, and order types."

A *"comprehensive results panel"* with *"net profit, win rate, max drawdown,
Sharpe/Calmar/Sortino ratios, annual return, and many more."* Charts give a
*"visual breakdown of performance from multiple angles"*: cumulative returns vs
benchmark, drawdown periods, underwater plot, monthly returns heatmap, trade P&L
distribution. Plus *"visually inspecting every trade entry and exit on a
candlestick chart"* and export to CSV/JSON.

---

## 2. Mechanism — how the code actually does it

### 2A. Lean — a **two-stage** pipeline (compute in engine, render in a separate tool)

The single most load-bearing fact: **Lean's report tool computes almost no
metrics.** The heavy statistics are computed *inside the backtest run* by the
engine and serialized into the result JSON; the Report Creator re-reads that JSON
and mostly renders it.

**Stage 1 — engine computes statistics during the run.**
`StatisticsBuilder.Generate(...)` (`lean-engine/Common/Statistics/StatisticsBuilder.cs:51-79`)
takes closed trades, a per-trade profit/loss record, and three time-series
(daily `equity`, algorithm `performance` = daily % change, `benchmark`) plus
`portfolioTurnover`, `startingCapital`, `totalFees`, `totalOrders`,
`estimatedStrategyCapacity`, a risk-free-rate model, and `tradingDaysPerYear`. It
returns a `StatisticsResults` (`StatisticsResults.cs:23-51`) with three parts:
- `TotalPerformance` — an `AlgorithmPerformance` holding a `PortfolioStatistics`
  and a `TradeStatistics`.
- `RollingPerformances` — the same, recomputed over rolling **1, 3, 6, 12-month**
  windows (`StatisticsBuilder.cs:185-197`; period ranges built at
  `GetPeriodRanges` `:265-291`).
- `Summary` — a flat `Dictionary<string,string>` of display-formatted KPIs
  (`GetSummary` `:205-246`).

`PortfolioStatistics` (constructor `PortfolioStatistics.cs:211-320`) is the
equity-curve metric bundle. Every field carries `[JsonConverter(JsonRoundingConverter)]`.
Computed: `AverageWinRate`/`AverageLossRate`/`ProfitLossRatio` from cumulative
per-trade returns against *running* capital (`:244-264`); `WinRate`/`LossRate`/
`Expectancy = WinRate*ProfitLossRatio − LossRate` (`:274-277`); `TotalNetProfit
= endEquity/startCapital − 1` (`:281`); `CompoundingAnnualReturn` (CAGR) over
`fractionOfYears = days/365` (`:284-285`); `AnnualVariance` &
`AnnualStandardDeviation` (`:287-288`); `SharpeRatio = SharpeRatio(annualPerf,
annualStdDev, riskFreeRate)` (`:294`); `SortinoRatio` = same formula but using
**annual downside deviation** (`:296-297`); `Beta` = cov(perf,bench)/var(bench)
(`:299-300`); `Alpha` (`:302`); `TrackingError` (`:304`); `InformationRatio =
(annualPerf − benchAnnualPerf)/trackingError` (`:306`); `TreynorRatio` (`:308`);
`ProbabilisticSharpeRatio` vs a de-annualized 1.0 benchmark Sharpe (`:310-312`);
`ValueAtRisk99`/`ValueAtRisk95` via inverse-normal CDF over the daily-return
sample (`:314-315`, `GetValueAtRisk` `:363-374`); `PortfolioTurnover` = mean of
daily turnover samples (`:226-229`); `Drawdown` + `DrawdownRecovery` from
`Statistics.CalculateDrawdownMetrics(equity, 3)` (`:317-319`); `StartEquity`/
`EndEquity` (`:223-224`).

`TradeStatistics` (constructor `TradeStatistics.cs:276-433`) is the trade-list
bundle, accumulated in a single pass with running/online means and variances.
Fields (`:28-270`): counts (total/winning/losing), P&L totals
(TotalProfitLoss/TotalProfit/TotalLoss), largest profit/loss, average
profit/loss/P&L, **durations** (average + median for all/winning/losing), max
consecutive winners/losers, `ProfitLossRatio`, `WinLossRatio` (capped at 10 when
no losers `:417`), WinRate/LossRate, **MAE/MFE** (max adverse/favorable
excursion, avg + largest), `MaximumClosedTradeDrawdown`,
`MaximumIntraTradeDrawdown`, `MaximumEndTradeDrawdown`, `AverageEndTradeDrawdown`,
`ProfitLossStandardDeviation`, `ProfitLossDownsideDeviation`, `ProfitFactor`
(=TotalProfit/|TotalLoss|, capped 10 `:420`), trade-level Sharpe/Sortino
(avg P&L ÷ std/downside-dev `:421-422`), `ProfitToMaxDrawdownRatio`,
`MaximumDrawdownDuration` (longest gap between equity highs `:335-336`),
`TotalFees`. Note the ITM-options adjustment: a losing-money option assignment
still counts as a *win* for the win/loss counts (`:363-372`, `:411-414`).

The `Summary` dict (`StatisticsBuilder.cs:216-245`) is the ~25 KPIs actually
shown; keys come from the `PerformanceMetrics` string constants
(`lean-engine/Common/Statistics/PerformanceMetrics.cs:21-165`) — e.g. `"Sharpe
Ratio"`, `"Probabilistic Sharpe Ratio"`, `"Compounding Annual Return"`,
`"Drawdown"`, `"Net Profit"`, `"Total Fees"`, `"Estimated Strategy Capacity"`,
`"Portfolio Turnover"`, `"Drawdown Recovery"`. Values are pre-formatted strings
with `%` and currency symbols baked in — a display artifact, not clean numbers.

**Stage 2 — the Report Creator renders.** `lean report`
(`lean-cli/lean/commands/report.py:89-278`) builds a `config.json`
(`:160-195`) pointing at `backtest-data-source-file.json`, bind-mounts it into a
Docker container, and runs `dotnet QuantConnect.Report.dll`
(`:208-233`), copying the produced `/tmp/report.html` to the destination. The CLI
computes nothing — it is pure orchestration. Default output `./report.html`
(`:51-54`); optional `--live-results` overlay, `--css`, custom `--html`,
`--pdf`, `--strategy-name/-version/-description`.

Inside the tool, `Report` (`lean-engine/Report/Report.cs:55-163`) reads
`template.html` (`:57`), extracts the crisis/parameters sub-templates by regex
(`:58-59`), builds equity/benchmark series and per-order lists from the result
JSON via `ResultsUtil.EquityPoints`/`BenchmarkPoints`
(`lean-engine/Report/ResultsUtil.cs:33-100` — pulls the `"Strategy Equity"`
chart's `"Equity"` series and the `"Benchmark"` chart), and reconstructs
**point-in-time portfolios** from the order stream with
`PortfolioLooper.FromOrders(...)` (`Report.cs:75-77`) — this is how the report
derives holdings/leverage/exposure/allocation over time from orders alone. Daily
point-in-time portfolios are also written out as their own JSON
(`Report.cs:84-108`).

The report body is a **list of `IReportElement`** (`Report.cs:112-147`): text
elements (name/description/version/stylesheet), ~13 KPI elements, and ~12 plot
elements, plus optional Parameters and Crisis pages. `Compile(out html, out
reportStatistics)` (`Report.cs:169-190`) walks the list, does string token
replacement (`html.Replace(element.Key, element.Render())`), and for every
non-text/non-crisis element records `statistics[reportElement.JsonKey] =
reportElement.Result` — serialized to `report-statistics.json`
(`StatisticsFileName`, `Report.cs:42`, `:189`). Injection tokens are `{{$...}}`
constants in `ReportKey.cs:23-60` (e.g. `{{$KPI-SHARPE}}`, `{{$PLOT-DRAWDOWN}}`);
`JsonKey` is derived by stripping `KPI-`/`$`/`{}` and lowercasing
(`ReportElement.cs:36`).

Most KPI elements just **read the precomputed engine stat** — e.g.
`SharpeRatioReportElement.BacktestResultValue =>
BacktestResult.TotalPerformance.PortfolioStatistics.SharpeRatio`
(`lean-engine/Report/ReportElements/SharpeRatioReportElement.cs:49`), returning
`"F1"` string or `-` when null (`:75-76`). (Live mode recomputes a trailing
6-month Sharpe from the live equity curve, `:79-103`.) `EstimatedCapacityReportElement`
parses the currency string out of the Summary dict
(`EstimatedCapacityReportElement.cs:48-67`).

**Charts are opaque images, not data.** Every plot element derives from
`ChartReportElement` (`lean-engine/Report/ReportElements/ChartReportElement.cs:22-42`),
which imports the Python module `ReportCharts` through `Py.GIL()` and calls
matplotlib. `Render()` returns a **base64-encoded PNG string** embedded in the
HTML (e.g. `CumulativeReturnsReportElement.cs:143`, `return base64`). The C# side
does the pandas-equivalent series math (cumulative-returns splicing of backtest +
live is documented inline at `CumulativeReturnsReportElement.cs:78-131`) then
hands `Keys`/`Values` lists to Python purely for pixels. So the chart *data* is
computed but discarded into an image; only the KPI scalars survive into
`report-statistics.json`.

`Metrics.cs` (`lean-engine/Report/Metrics.cs:36-201`) supplies the derived
time-series the plots need from the reconstructed portfolios: `LeverageUtilization`
(`:36-62`), `AssetAllocations` (per-symbol % of total value over time, `:71-114`),
and `Exposure` (a Deedle `Frame` keyed by `(SecurityType, OrderDirection)`,
forward-filled, `:126-201`).

**Crisis analysis** (`lean-engine/Report/Crisis.cs:24-107`): a static dictionary
of 17 named events with hard-coded start/end `DateTime`s (`:29-48`). The
`CrisisReportElement` plots strategy cumulative return within each window that
overlaps the backtest period; non-overlapping crises are omitted. This is a US-
equities-flavored feature (DotCom, GFC, Flash Crash, COVID…).

Result JSON shape consumed: `result.Charts["Strategy Equity"].Series["Equity"]`
(ChartPoint `{x: unix seconds, y: value}` or Candlestick), `result.Charts
["Benchmark"].Series["Benchmark"]`, `result.Orders`, `result.
AlgorithmConfiguration` (holds `TradingDaysPerYear`), and the precomputed
`result.TotalPerformance` / `result.Statistics` dict.

### 2B. Jesse — one-stage, in-process, returns a metrics **dict** + renders PNGs

Jesse computes metrics at the end of a run in a single function.
`jesse/services/metrics.py::trades(trades_list, daily_balance, final)`
(`metrics.py:302-454`) builds a pandas DataFrame from closed trades and returns a
flat dict of **~45 keys** (`return {...}` `:409-454`). Contents: `total`,
`total_winning_trades`, `total_losing_trades`, `starting_balance`,
`finishing_balance`, `win_rate`, `win_rate_longs`, `win_rate_shorts`,
`ratio_avg_win_loss`, `longs_count`, `longs_percentage`, `shorts_count`,
`shorts_percentage`, `fee`, `net_profit`, `net_profit_percentage`,
`average_win`, `average_loss`, `expectancy`, `expectancy_percentage`,
`expected_net_profit_every_100_trades`, `average_holding_period`,
`average_winning_holding_period`, `average_losing_holding_period`,
`gross_profit`, `gross_loss`, `max_drawdown`, `max_underwater_period`,
`annual_return`, `sharpe_ratio`, `calmar_ratio`, `sortino_ratio`, `omega_ratio`,
`serenity_index`, `total_open_trades`, `open_pl`, `winning_streak`,
`losing_streak`, `largest_losing_trade`, `largest_winning_trade`,
`current_streak`, `avg_trades_per_day`, `avg_trades_per_week`,
`avg_trades_per_month`.

Ratio math lives in the same file and is a lightly-adapted **quantstats**
lineage, all operating on a daily-return series (`daily_balance` →
`pct_change` `:373`):
- `sharpe_ratio` = mean/std(ddof=1) × √periods (`:67-83`).
- `sortino_ratio` = mean/downside-dev × √periods, downside = √(Σ min(r,0)²/N)
  (`:86-107`).
- `calmar_ratio` = CAGR/|maxDD| (`:120-153`).
- `omega_ratio` (`:230-248`), `serenity_index` (`:251-260`, uses ulcer index ×
  pitfall from CVaR), `ulcer_index` (`:263-268`), `cagr` (`:201-227`),
  `max_drawdown` (`:156-164`), `conditional_value_at_risk` (`:280-299`),
  `calculate_max_underwater_period` (days below peak, `:167-198`).
- **Crypto convention:** `periods=365` (calendar days, not 252 trading days) —
  passed explicitly (`:399-407`). Contrast Lean's `tradingDaysPerYear` default
  252 (`Report.cs:72`).
- Guards: any ratio is `NaN` when `len(daily_return) < 2`; `safe_convert`
  (`:389-397`) coerces types and preserves NaN.

`jesse/services/report.py` assembles the *live/dashboard* view — `positions()`,
`candles()`, `livetrade()`, `trades()`, `orders()`, `portfolio_metrics()`
(delegates to `metrics.trades`, `:196-200`), plus strategy-drawn overlay lines
for the live chart. It is JSON-first (all dict/list returns).

Charts: `jesse/services/charts.py` names **7** backtest charts (`:17`):
`equity_curve`, `cumulative_returns`, `drawdown`, `underwater`,
`monthly_heatmap`, `monthly_distribution`, `trade_pnl`. `_plot_backtest_charts`
(`:170-514`) renders each to a **PNG file** via matplotlib (`Agg` backend),
themed light/dark (`_THEMES` `:20-61`), named `{session_id}_{chart}.png`. Helper
series builders are pure and reusable: `_compute_drawdown_series` (`:64-74`),
`_find_worst_drawdown_periods` (top-5, with start/bottom/recovery, `:77-119`),
`_compute_monthly_returns` (keyed `(year,month)`, `:122-143`). Crucially, Jesse
*also* exposes chart **data** as JSON: `equity_curve(benchmark)`
(`:547-579`) returns a list of `{name, color, data:[{time, value, color}]}` series
(point builder `_calculate_equity_curve` `:517-528`) — machine-readable, unlike
Lean's base64 PNGs. Benchmark series are the route symbols' own buy-and-hold
daily returns (`prices_to_returns` over daily candles, `:209-223`).

Jesse has **no crisis-period feature** and **no rolling-window statistics** —
ABSENT in the code. Its distribution charts (monthly + trade P&L) with KDE
overlays (`:412-514`) are richer than Lean's on the return-distribution axis.

---

## 3. Jesse vs Lean — which approach fits QMX

| Dimension | Lean | Jesse | QMX choice |
|---|---|---|---|
| Where metrics compute | In engine during run; report re-reads JSON | End-of-run single dict | **Engine/producer computes; report re-reads** (Lean model). Metrics are AD-23 governed producers (CT-32) — never recomputed ad-hoc by a renderer. |
| Metric surface | ~25 summary + full PortfolioStats + TradeStats + rolling 1/3/6/12mo | ~45-key flat dict | **Union, curated** (§4). Lean's rolling windows + Jesse's distribution/streak/holding-period metrics both worth keeping. |
| Annualization | 252 trading days (configurable) | 365 calendar days (crypto) | **Configurable per Book/instrument-calendar** — QMX spans crypto + others; must be a declared parameter, pinned into metric identity. |
| Chart output | base64 PNG (opaque) | PNG files **and** JSON series (`equity_curve`) | **JSON series first, always** (Jesse's `equity_curve` path is the right instinct). Agents read data, not pixels. Rendering is downstream and derived. |
| Risk-free rate | Interest-rate model, excess returns | rf=0 default | **Declared rf model**, recorded in label so Sharpe is reproducible. |
| Crisis analysis | 17 hard-coded US-equity windows | none | **Deprioritize / reframe** — hard-coded windows are nonsense for a venue-neutral crypto-first tool. Optionally support *operator-declared* named regime windows later; do not ship the US-equity list. |
| Machine-readability | Weak (formatted strings w/ `%`, `$`; charts as PNG) | Medium (clean-ish dict; some NaN/inf) | **Strong** — CT-32 exact-integer money, unit-kinded measures, typed refusals, no float in identity. |
| Money type | `decimal` (good) but serialized rounded strings in Summary | Python float (lossy) | **Exact integer money at declared scale** (QMF law), never float. |

**Verdict.** Adopt **Lean's architecture** (compute-once-in-producer,
render-from-artifact, token-templated HTML) but **Jesse's data-exposure instinct**
(chart series as JSON, distribution charts, streak/holding-period/long-short
splits). Reject both platforms' fatal flaw for an agent audience: **charts
serialized as images**. Reject Lean's formatted-string Summary and Jesse's
float money. QMX's report is a **canonical machine-readable artifact first**
(CT-32), from which HTML/markdown is a pure rendering.

---

## 4. QMX spec draft — requirements (WHAT, not code design)

QMX report = **one canonical result artifact (CT-32 performance-result
container), rendered to human HTML/markdown by a downstream skill.** Requirements
below are numbered `R-RPT-*`. Mapping to QMF contracts noted inline; where a claim
maps to CT-32 it is authoritative.

### 4.1 The artifact (machine-readable core)

- **R-RPT-1 (one artifact, two audiences).** A completed run MUST emit exactly
  one CT-32 performance-result container that serves both the AD-32 admission-bar
  evidence and the agent/operator report — one kind, two readers (CT-32
  invariant 1). No separate "report JSON" that could drift from the evidence.
- **R-RPT-2 (full result label).** Every artifact MUST carry the full AD-12
  label: producer contract identity + format version, input fingerprints,
  evidence time range, computation/occurrence identity, evidence class
  (confirmed|unconfirmed|provisional), **world (live|replay|simulated)**, and the
  account-binding role (CT-32 field `result_label`). The report's headline MUST
  show the world label verbatim — the operator's rule: result labels state
  live/replay/simulated. `simulated` is reserved-unusable in V1.
- **R-RPT-3 (measure set is ordered + unit-kinded).** Every emitted metric is a
  member of an ordered `measure_set`; each quantity carries a non-null unit-kind
  from the closed AD-40 vocabulary (CT-32 `measure_set`; invariant 6). A null
  unit-kind is an invalid-input **typed refusal**, never a default.
- **R-RPT-4 (exact money, exact time).** Money metrics (net profit, fees, gross
  profit/loss, largest win/loss, start/end equity) MUST be exact integers at the
  declared currency scale — never binary float (QMF law; CT-32 units). Time
  metrics (durations, underwater period, drawdown recovery) MUST be int64 UTC-ns
  or typed `duration`. The period is an AD-8 Interval with calendar identity +
  version + knowledge-time bound (CT-32 `period`).
- **R-RPT-5 (metric arithmetic is governed + versioned).** Each metric's
  arithmetic is canonical and pinned by its own producer contract format version
  (CT-32 invariant 9, field `metric_contract_format_version`). Changing how
  Sharpe is computed is a **format-version mint with before/after evidence**, not
  a silent code change. This directly fixes the Lean/Jesse divergence (252 vs 365,
  ddof, rf handling) by making the convention part of the metric's identity.
- **R-RPT-6 (float identity ban).** A Sharpe or drawdown takes label-derived
  identity (AD-10), never a hash of float bytes (CT-32 invariant on float
  discipline).
- **R-RPT-7 (single account role).** One artifact never spans account roles; a
  multi-role result is a policy rejection / typed refusal (CT-32 invariant 8).
- **R-RPT-8 (suppression + veto accounting).** The artifact MUST carry
  suppression accounting (actions suppressed, keyed by authority + reason) and
  veto accounting (door refusals, keyed by door), defaulting to explicit zero
  counts, never omitted keys (CT-32 fields; nullability rule). Rationale: so the
  report never reads QMX's own arbitration/refusals as strategy decay. This is a
  QMX-native metric with **no analogue** in Lean or Jesse.
- **R-RPT-9 (measurement publishes, never acts).** Producing the report MUST NOT
  size, allocate, promote, demote, bench, or change a mode (CT-32 invariant 12).
  The report is read-only evidence; acting on it is the Book door's or operator's
  job.
- **R-RPT-10 (no composite score).** No single score, rating, tier band, or
  weighted composite may express the result (CT-32 invariant 13). The report
  presents the measure set; it never collapses it into one number. (This
  explicitly rejects any "strategy grade" temptation.)

### 4.2 The metric set worth computing (curated union, minus nonsense)

Grouped; each maps to an AD-40 unit-kind. **Bold** = ship in V1 core.

**Returns / growth**
- **Net profit** — money(currency). *(Lean `TotalNetProfit`% + Jesse
  `net_profit`/`net_profit_percentage`.)* Emit both the money amount and a
  dimensionless-ratio percent.
- **CAGR / compounding annual return** — dimensionless-ratio. *(Lean
  `CompoundingAnnualReturn`; Jesse `annual_return`.)* Annualization basis is a
  declared parameter (R-RPT-5).
- **Start equity / End equity** — money(currency). *(Both.)*

**Risk-adjusted ratios**
- **Sharpe ratio** — dimensionless-ratio, with declared rf model + annualization
  basis in the metric's format version. *(Both.)*
- **Sortino ratio** — dimensionless-ratio. *(Both.)*
- **Calmar ratio** — dimensionless-ratio. *(Jesse; = CAGR/|maxDD|.)*
- Probabilistic Sharpe ratio — dimensionless-ratio. *(Lean; useful, keep as
  extended.)*
- Omega ratio, Serenity index, Ulcer index — dimensionless-ratio. *(Jesse;
  extended tier.)*
- Information ratio, Treynor ratio, Alpha, Beta, Tracking error — require a
  **benchmark**; ship only when a benchmark is declared (see R-RPT-15). *(Lean.)*

**Drawdown / downside**
- **Max drawdown** — dimensionless-ratio (percent). *(Both.)*
- **Max drawdown recovery / underwater period** — duration. *(Lean
  `DrawdownRecovery`; Jesse `max_underwater_period`.)*
- Value-at-risk 95 / 99 — money(currency) or dimensionless-ratio. *(Lean;
  extended.)*
- Annual standard deviation / variance — dimensionless-ratio. *(Lean.)*

**Trade statistics**
- **Total / winning / losing trade counts** — count. *(Both.)*
- **Win rate** (+ long/short split) — dimensionless-ratio. *(Jesse adds
  long/short split — keep it.)*
- **Profit factor** — dimensionless-ratio (gross profit / |gross loss|). *(Lean
  `ProfitFactor`.)*
- **Profit-loss ratio / expectancy** — dimensionless-ratio + money. *(Both.)*
- **Average win / average loss / largest win / largest loss** — money(currency).
  *(Both.)*
- **Gross profit / gross loss / total fees** — money(currency). *(Both.)*
- Average / median trade duration (all / winning / losing) — duration. *(Lean +
  Jesse holding periods.)*
- **Max consecutive winners / losers (streaks)** — count. *(Both;
  winning_streak/losing_streak/current_streak.)*
- Avg trades per day/week/month — dimensionless-ratio (rate). *(Jesse.)*
- MAE / MFE (avg + largest) — money(currency). *(Lean; extended — valuable for
  agents doing stop analysis.)*
- Portfolio turnover — dimensionless-ratio. *(Lean.)*

**QMX-native (no source analogue)**
- **Suppression count** by (authority, reason) — count. (R-RPT-8)
- **Veto count** by door — count. (R-RPT-8)
- Open positions / open P&L at close — count / money. *(Jesse `total_open_trades`,
  `open_pl`.)*

**Rolling windows** — recompute the core ratio set over rolling 1/3/6/12-month
windows *(Lean `RollingPerformances`)*. Ship as an extended tier; each window is
its own labeled sub-measure-set.

**Explicitly rejected as nonsense for QMX:**
- Lean's **hard-coded crisis windows** (US-equity dates; meaningless for
  venue-neutral crypto). Reframe later as operator-declared regime windows if
  ever wanted.
- Lean's **Estimated Strategy Capacity / Lowest Capacity Asset** — US-equity
  market-impact model; ABSENT-equivalent for QMX's target. Defer.
- Formatted-string metric values with baked-in `%`/`$` (Lean Summary) — QMX emits
  numbers + unit-kinds, formatting is the renderer's job.
- `WinLossRatio`/`ProfitFactor` **magic cap of 10** on divide-by-zero (Lean
  `:417,:420`) — QMX MUST emit a typed "undefined / no losers" rather than a
  fake 10.

### 4.3 Chart-data series format (data, never pixels)

- **R-RPT-11 (series as data).** Every chart MUST be emitted as a
  machine-readable series in the artifact, not as an image. Rendering to
  PNG/SVG/HTML is a separate downstream step over that data. (Adopts Jesse's
  `equity_curve()` JSON instinct; rejects both platforms' base64/PNG default.)
- **R-RPT-12 (series shape).** A chart series is
  `{ name, unit_kind, points: [{ t, v }] }` where `t` is int64 UTC-ns and `v`
  is the unit-kinded value (exact-integer money or exact rational ratio). No
  color/style in the data (that is renderer concern — contrast Jesse embedding
  `color` in points, `charts.py:519-523`).
- **R-RPT-13 (chart set worth shipping).** Union minus nonsense:
  - **Equity curve** (portfolio balance over time) — money. *(Both.)*
  - **Cumulative returns** (vs benchmark when declared) — dimensionless-ratio.
    *(Both.)*
  - **Drawdown / underwater** (drawdown % over time) — dimensionless-ratio, plus
    a **top-5 worst-periods** table `{start, bottom, recovery, max_drawdown}`
    *(Jesse `_find_worst_drawdown_periods`; Lean top-5 marking).*
  - **Monthly returns** as a `(year, month) → return` grid + annual-total column
    *(both; Jesse `_compute_monthly_returns` + heatmap).* Renderer draws the
    heatmap.
  - **Monthly-return distribution** and **trade-P&L distribution** as
    histogram-ready arrays (raw values + suggested bins), optional KDE downstream
    *(Jesse).*
  - **Annual returns**, **daily returns**, **returns-per-trade** — bar-chartable
    arrays *(Lean).*
  - **Asset allocation over time** (per-instrument % of portfolio) and
    **long/short exposure** by instrument/asset-class — *(Lean Metrics.cs;
    reconstructed from the order/position stream).* Ship when multi-instrument.
  - **Leverage utilization over time** — *(Lean).* Ship for leveraged Books.
  - Rolling Sharpe / rolling beta series — extended tier *(Lean).*
- **R-RPT-14 (derive from the position/order stream).** Time-varying
  holdings/leverage/exposure/allocation series MUST be derivable from QMX's own
  ordered position/fill record (as Lean's `PortfolioLooper.FromOrders` does,
  `Report.cs:75-77`) — not from a parallel bespoke log that could disagree with
  the ledger.
- **R-RPT-15 (benchmark optional + labeled).** Benchmark-relative metrics/charts
  (alpha, beta, info ratio, tracking error, cumulative-vs-benchmark) ship only
  when a benchmark is declared in the Book/BMS config; the benchmark identity is
  recorded in the artifact. Absent benchmark ⇒ those measures are omitted with an
  explicit "no benchmark declared" note, never faked.

### 4.4 The pass/fail LEDGER line (operator's unbiased end result)

- **R-RPT-16 (logged during, saved at completion).** Metrics are **logged**
  incrementally during a run and the final CT-32 artifact is **saved at
  completion** into the ledger (operator's wind-tunnel model; QMF ledger). The
  saved artifact is immutable evidence.
- **R-RPT-17 (one unbiased pass/fail line).** At completion the ledger MUST
  record exactly one pass/fail end-result line for the run. Its determination
  MUST be **structural, not a judgment call**: PASS iff the artifact satisfies
  the declared AD-32 admission bar for its account role — i.e. the run completed,
  produced a well-formed CT-32 artifact with no unresolved typed refusal, and its
  metric contract format versions match the bar's declared requirements (CT-32
  invariant: "Parity with the admission bar is structural"). FAIL otherwise, with
  the failing reason as a typed code.
- **R-RPT-18 (pass/fail is not a score).** The pass/fail line is a gate outcome,
  never a quality rating or composite (consistent with R-RPT-10). A PASS means
  "admissible evidence," not "good strategy." Interpretation of the measures is
  left to the reader (operator or agent + skill).
- **R-RPT-19 (parity guard).** A paper-account-role result MUST NOT gate live
  money, and a result whose metric format versions differ from the bar's does not
  satisfy it (CT-32 invariant 13/parity). The ledger line MUST make the world
  label and account role unmissable so a replay/paper PASS is never mistaken for
  a live one.
- **R-RPT-20 (ledger line content).** The line MUST carry, at minimum: run /
  computation identity, world, account role, period, PASS|FAIL, and (on FAIL) the
  typed refusal/parity code. It points to (does not inline) the full CT-32
  artifact.

### 4.5 Rendering + skills (human + agent consumption)

- **R-RPT-21 (render is pure + downstream).** HTML/markdown rendering is a pure
  function of the CT-32 artifact — like Lean's `{{$KEY}}` token replacement over
  `template.html` (`Report.cs:169-190`), but the renderer computes nothing and
  reads only the artifact. Two render targets: HTML (operator, shareable) and
  markdown (agent-consumable, diffable).
- **R-RPT-22 (in-house interpretation skills).** QMX ships skills that read the
  CT-32 artifact (not the HTML) and produce plain-language interpretation for the
  operator and structured findings for agents. Because the artifact is
  unit-kinded and labeled, a skill can safely compare two runs, explain a drop,
  or flag a refusal-heavy period — without re-deriving numbers.
- **R-RPT-23 (config-driven).** Which metrics/charts/tiers appear, the
  annualization basis, rf model, and benchmark are all read from the Book/BMS
  config the CLI materializes (operator's wind-tunnel: change variables, never
  swap the tunnel) — configurable means UI-editable (L38).
- **R-RPT-24 (concurrency-safe).** Report/artifact production MUST be per-run
  isolated so 12-14 concurrent tasks each save their own ledger line + artifact
  without contention (target load). No shared mutable render state (contrast
  Jesse's global `store`-coupled `report.py`, which is single-session).

---

## 5. Open questions

1. **Annualization basis as identity.** R-RPT-5 makes 252-vs-365 part of a
   metric's format version. Does QMX pin one basis per instrument-calendar (AD-8),
   or per Book? A cross-instrument portfolio (crypto + equity) needs a rule for
   the blended Sharpe — unresolved.
2. **Rolling windows vs decay primitives.** CT-32 defers alpha-decay mathematics
   but collects primitives now. Are Lean-style rolling 1/3/6/12-month
   sub-measure-sets the right primitive to collect, or does the deferred decay
   design want a different cohort/window shape? Needs the backtesting/decay
   sitting.
3. **Benchmark model.** Jesse uses each route's own buy-and-hold; Lean uses a
   declared benchmark security. What is QMX's benchmark primitive for a
   multi-instrument Book, and does it need its own contract? (R-RPT-15.)
4. **MAE/MFE + intra-trade drawdown.** These need per-trade high-water tracking
   during the run (Lean `TradeStatistics` accumulates it live). Confirm QMX's
   fill/position record captures enough to compute MAE/MFE, or scope them out of
   V1.
5. **Distribution-chart binning.** Ship raw values only and let the renderer bin
   (cleanest for identity), or emit suggested bins (Jesse computes
   Freedman-Diaconis bins, `charts.py:420-425`)? Binning in the artifact risks
   baking a display choice into evidence.
6. **Operator-declared regime windows.** Is there appetite to replace Lean's
   hard-coded crisis list with operator-declared named periods, and if so does
   that belong in the Book config or a separate registry?
7. **Metric provenance under refusal.** When a metric can't be computed (e.g. <2
   daily samples, no losers), CT-32 says emit a typed refusal. Confirm the report
   renderer/skill treats "refused metric" distinctly from "zero" everywhere
   (Jesse conflates via NaN→0 `safe_convert`; Lean via magic-10 — both wrong for
   QMX).
8. **Capacity / turnover relevance.** Portfolio turnover is cheap and kept;
   estimated strategy capacity is a US-equity market-impact model. Is any
   capacity/liquidity metric wanted for crypto venues, computed how? Deferred.
