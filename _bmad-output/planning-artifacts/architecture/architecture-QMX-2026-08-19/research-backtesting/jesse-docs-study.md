# Jesse — Documented Feature Surface (Web Study)

Compiled 2026-08-20. Sources are the official docs (docs.jesse.trade), the
GitHub repo (github.com/jesse-ai/jesse), and the docs changelog. Every
load-bearing claim is cited to a URL. "AS DOCUMENTED" throughout — this is what
Jesse claims/ships per its own docs, not independent verification.

## Current release

- **Version 3.0.7, dated 19 August 2026** — the top entry of the docs
  changelog. Prior: 3.0.6 (16 Aug 2026), 3.0.5 (8 Aug 2026). Source:
  https://docs.jesse.trade/docs/changelog
- GitHub **Releases page is empty** ("There aren't any releases here") — Jesse
  does not cut GitHub release tags; version tracking lives in the docs changelog
  and on PyPI. Repo shows ~8.3k stars, ~1.2k forks. Source:
  https://github.com/jesse-ai/jesse/releases
- PyPI page (pypi.org/project/jesse/) failed to load during this study —
  ABSENT (could not confirm PyPI version/date independently).

## What Jesse is / license

Python cryptocurrency algo-trading framework: research, define, backtest,
optimize, live-trade custom strategies. **Licensed MIT** (open source,
self-hosted, privacy-first). Source: repo README via
https://github.com/jesse-ai/jesse

README-claimed feature headline set: Simple Python strategy syntax; 300+
technical indicators; **Rust-powered indicators** (performance); market/limit/
stop "smart ordering"; multiple timeframes & symbols without look-ahead bias;
leveraged trading + short-selling; partial fills; risk-management + metrics;
debug mode; optimize mode (Optuna); Jesse MCP (Claude/Codex/Cursor/VS Code/Zed);
interactive charts; Rule Significance Testing; Monte Carlo; ML pipeline;
Research API + Jupyter; **Reinforcement Learning marked "Coming Soon."**

## Backtest + full metrics list

Backtesting = simulate strategy against historical candles. Result charts,
benchmark (run multiple configs side-by-side in a comparison table), exports,
tabs. Docs stress realistic fees. Sources:
https://docs.jesse.trade/docs/backtest ,
https://docs.jesse.trade/docs/backtest/benchmark

**Full reported metrics** (source: https://docs.jesse.trade/docs/backtest/results):
Total Closed Trades; Total Net Profit; Start => Finish Balance; Open Trades;
Total Paid Fees; Max Drawdown; Max Underwater Period; Annual Return; Expectancy;
Avg Win; Avg Loss; Ratio Avg Win / Avg Loss; Win-rate; Win-rate Shorts; Win-rate
Longs; Longs (proportion); Shorts (proportion); Avg Holding Time; Winning Avg
Holding Time; Losing Avg Holding Time; **Sharpe Ratio; Calmar Ratio; Sortino
Ratio; Omega Ratio**; Winning Streak; Losing Streak; Largest Winning Trade;
Largest Losing Trade; Total Winning Trades; Total Losing Trades.

## Optimize mode

- **Engine: Optuna, accelerated with Ray for parallel processing** — intelligent
  search (not random/grid). Source: https://docs.jesse.trade/docs/optimize
- **Objective/fitness functions**: default **Sharpe ratio**; configurable to
  **Calmar Ratio, Sortino Ratio, Omega Ratio, Serenity Index**. Source:
  https://docs.jesse.trade/docs/optimize/executing-the-optimize-mode
- **Hyperparameters** defined via a `hyperparameters()` method returning a list
  of dicts; types **int, float, categorical, boolean** (with `min/max/default/
  step` or `options`); accessed at runtime via `self.hp['name']`. Source:
  https://docs.jesse.trade/docs/optimize/hyperparameters . DNA usage exists as a
  compact encoding: https://docs.jesse.trade/docs/optimize/dna-usage
- **Train/test split**: Training period searches params, Testing period
  validates on unseen data; recommended 70–80% training. Runs to a set number of
  trials, pausable. "The more cores you allocate, the faster."
- **Local vs cloud**: docs do NOT state a cloud service — Ray implies local
  parallel/distributed compute; runs on the user's machine. No hosted-cloud
  optimize offering documented (ABSENT). Dedicated **overfitting** guidance page
  exists ("Be aware of overfitting!"):
  https://docs.jesse.trade/docs/optimize/overfitting

## Research API (Jupyter)

"The 'research' module is a collection of Jesse's features (that you typically
use via the GUI dashboard) made available via functions for research purposes."
Import `from jesse import research`. Works in plain Python scripts and Jupyter.
Covers: backtest, candles, indicators, Monte Carlo, optimize, rule significance
testing, ML (binary/multiclass/regression/meta-labeling). Part of the
open-source framework. Source: https://docs.jesse.trade/docs/research (+
/research/jupyter, /research/backtest, /research/candles, /research/indicators)

## Machine Learning pipeline

Source: https://docs.jesse.trade/docs/research/ml (+ subpages binary, multiclass,
regression, meta-labeling, gathering-data, deploying, stationarity).
- Tasks: **Binary classification** (accuracy, ROC AUC, MCC, calibration,
  precision/threshold sweeps); **Multiclass** (per-class metrics, confusion
  matrices); **Regression** (MAE, RMSE, R², Spearman); **Meta-labeling**
  (secondary model learning bet *size* on a primary directional signal).
- Stack: **scikit-learn-compatible estimators**, `StandardScaler`. Workflow:
  gather labeled data during backtest → `train_model()` → deploy via
  `ml_predict()` / `ml_predict_proba()` in live strategies.
- **Stationarity** emphasized: transform raw financial data into stationary
  inputs before modeling.
- **Reinforcement Learning**: NOT present in ML docs; README lists RL as
  **"Coming Soon"** (not shipped).

## Monte Carlo analysis

Source: https://docs.jesse.trade/docs/monte-carlo (+ trade-order-shuffling,
candles-based, candle-pipelines, interpreting-results). Tests whether backtest
results are "genuine skill or just luck." Two methods:
**Trade-Order Shuffling** (randomize trade sequence) and **Candles-Based**
(alternate historical scenarios). Compares original result vs many simulated
results; if most sims underperform the original, flags curve-fitting. Available
programmatically via research module.

## Rule Significance Testing (significance testing)

Source: https://docs.jesse.trade/docs/rule-significance-testing (+ /bootstrap,
/interpreting-results, /usage). Pre-backtest filter examining entry signals in
isolation (no orders placed). Phase 1 records entry signals (+1/-1/0) + closing
prices; Phase 2 runs a **bootstrap** — resamples the rule's bar-level returns
**with replacement** N times to build a null distribution; returns are
**detrended** by subtracting market mean return. Null hypothesis: rule has no
predictive power. Output is **p-values** (fraction of sims ≥ actual);
thresholds: **p ≤ 0.05 significant, p > 0.10 consistent with random chance.**

## Interactive charts

Source: https://docs.jesse.trade/docs/charts/interactive-charts. "Interactive
charts combine candlesticks, execution markers, and indicators drawn by your
strategy. Backtests show the complete simulated history, while paper and live
charts update as the session runs and remain available afterward." Strategy API
helpers: `add_line_to_candle_chart()`, `add_horizontal_line_to_candle_chart()`,
`add_extra_line_chart()` (separate indicator panes, e.g. RSI/ADX),
`add_horizontal_line_to_extra_chart()`. Hover OHLC, toggle indicators, pan/zoom
synced panes, collapse panes, export as images, fullscreen (paper/live). A
"Trade Chart" reviews completed trades with executions, sortable by performance.

## MCP server / agent integration

Sources: https://docs.jesse.trade/docs/mcp , /mcp/setup, /mcp/connect-*,
/mcp/example-workflow, /mcp/mcp-rules.
- **What**: MCP = "shared language between your AI assistant … and applications
  you trust, such as Jesse." Jesse runs an **MCP service alongside the app, on
  the user's computer**, exposing **actions** and shipping **short guides** for
  context. "MCP is an add-on to that, not a separate cloud service."
- **Transport/host/port**: **HTTP**, binds `0.0.0.0`, default **port 9002**;
  connect at `http://localhost:9002/mcp`. Env vars: **`MCP_PORT`** (default
  9002), **`MCP_LOG_IN_TERMINAL`**. **Requires Jesse to be running** locally —
  not standalone, not cloud.
- **Clients**: Claude Code, Codex, Cursor, VS Code, Zed (dedicated connect
  pages each).
- **Capabilities exposed**: run backtests + modify strategies; rule significance
  testing; Monte Carlo; parameter optimization with overfitting detection;
  historical data management / coverage verification.
- **Open-source vs paid**: docs do NOT explicitly gate MCP behind the paid
  license; setup treats it as an integrated component of the local framework.
  Setup terminal output references "Live Plugin v2.1.2" but licensing of MCP
  itself is not stated — treat as INTEGRATED/open per docs framing, unconfirmed
  whether the live plugin is a hard dependency (ABSENT explicit statement).

## Live trading — open-source vs paid

Source: https://docs.jesse.trade/docs/livetrade.
**Live AND paper trading ship as a paid, closed-source official plugin**, NOT in
the MIT framework. "Live and paper trading functionality is supported by Jesse
via an official plugin." "The package is pre-built and the access is limited to
those with an active license." Requires: register on jesse.trade for a **license
key**, generate an **API token**, install the plugin (auto in Docker; `jesse
install-live` for native). Paper trade is a toggle on the Live page (same plugin
infrastructure). Disclaimer: "We do NOT guarantee profitable trading results …
USE THE SOFTWARE AT YOUR OWN RISK."

## Supported exchanges (crypto-only)

Source: https://docs.jesse.trade/docs/supported-exchanges. **Crypto exchanges
only — no stocks, no forex.**
- **Backtest (12)**: Binance Spot, Binance US Spot, Binance Perpetual Futures,
  Bitfinex Spot, Coinbase Spot (Advanced), Bybit USDT Perp, Bybit USDC Perp,
  Bybit Spot, Gate.io Perpetual Futures, KuCoin USDT Perp, KuCoin Spot, Kraken
  Pro Futures.
- **Live (~15–16)**: Lighter, Apex Omni, Kraken Pro Futures, Kraken Pro Spot,
  KuCoin USDT Perp, KuCoin Spot, Hyperliquid, Bybit USDT Perp, Bybit USDC Perp,
  Bybit Spot, Binance Perpetual Futures, Binance Spot, Binance US Spot, Coinbase
  Spot (Advanced), Gate.io Perpetual Futures, Gate.io Spot.
- Candle "Spot"/"Futures" labels = data source, not backtest mode; both spot and
  futures backtests can run off either candle type.

## Open-source vs closed/paid split (summary)

| Component | Status |
|---|---|
| Core framework (backtest, optimize, research, ML, Monte Carlo, RST, indicators, charts, MCP service) | MIT / open-source, self-hosted |
| **Live + paper trading plugin** | **Paid, closed-source, license-gated** |
| Reinforcement Learning | Announced "Coming Soon" — not shipped |

## Open questions / ABSENT

- PyPI version + license line could not be loaded independently (page error) —
  version 3.0.7 rests on the docs changelog only.
- Whether the MCP server hard-requires the paid live plugin, or runs on the pure
  MIT core, is not explicitly stated in docs.
- Optimize mode: no documented hosted-cloud offering; local/Ray only (no cloud
  compute service claimed).
