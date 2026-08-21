# Reference-Platform Website Visuals — Jesse & QuantConnect Lean CLI

Captured 2026-08-20 for the QMX backtesting architecture sitting. Full-page
screenshots taken with Firecrawl (screenshot format), saved under `./screens/`.
Marketed feature lists are transcribed **verbatim** (bullet claims) from each
page's rendered content. Screenshots succeeded on the first attempt for all
five pages — no text-only fallback was needed.

All five images verified as valid PNGs.

---

## 1. Jesse — Homepage

- **Filename:** `screens/jesse-homepage.png`
- **Page URL:** https://jesse.trade/ (title: "Jesse - The Open-source Python Bot For Trading Cryptocurrencies")

**What the page shows / claims.** The marketing homepage. Hero headline:
"Start algo-trading in **minutes, not months!**" with subhead "The most
accurate, simple, and powerful trading framework for Python you can find.
Self-hosted and privacy-focused." Social proof strip: avatars + "Trusted by
+14,000 algo-traders." A live promo banner (SUMMER30 code, countdown timer).

The page's spine is a **two-column "with vs. without Jesse" comparison**, then a
prominent **"NEW — Jesse MCP"** section, then a features grid, a founder story,
video embeds, a large testimonial wall, community stats, and an FAQ.

**Marketed feature list (verbatim bullet claims):**

*"Algo-trading with Jesse" column:*
- Clear framework for your strategies
- Stupid simple syntax + AI
- The flexibility of Python
- Clean documentation, video tutorials, starter strategies
- The most accurate backtesting engine — No look-ahead bias, detailed logs, etc.
- Built-in MCP server — your AI agent researches, backtests, and validates strategies for you
- Instantly start implementing, testing, and deploying your trading ideas
- Keep your privacy by running your strategies on a self-hosted software that's easy to set up
- Countless more time-saving benefits

*"Your AI agent just became a quant" (Jesse MCP) — four claims:*
- **One prompt, full pipeline** — "Your agent researches, writes the strategy, imports data, backtests, optimizes, and validates — without you touching the dashboard."
- **Real results, not hallucinations** — "Every number comes from Jesse's backtesting engine — the agent calls real tools and reads real outputs."
- **Works with your favorite agent** — "Claude Code, Cursor, VS Code, Codex, Zed — anything that speaks MCP connects in seconds."
- **100% local and private** — "The MCP server runs on your machine. Your strategies, data, and results never leave it."

*"Complete framework for algo-Trading" features grid:*
- **Stupid Simple** — "Craft complex trading strategies with remarkably simple Python. Access 300+ indicators, multi-symbol/timeframe support, spot/futures trading, partial fills, and risk management tools. Focus on logic, not boilerplate." (shown with a `GoldenCross(Strategy)` code sample)
- **Backtest** — "Execute highly accurate and fast backtests without look-ahead bias. Utilize debugging logs, interactive charts with indicator support, and detailed performance metrics to validate your strategies thoroughly."
- **Live/Paper Trading** — "Deploy strategies live with robust monitoring tools. Supports paper trading, multiple accounts, real-time logs & notifications (Telegram, Slack, Discord), interactive charts, spot/futures, DEX, and a built-in code editor."
- **Benchmark** — "Accelerate research using the benchmark feature. Run batch backtests, compare across timeframes, symbols, and strategies. Filter and sort results by key performance metrics for efficient analysis."
- **AI** — "Leverage our AI assistant even with limited Python knowledge. Get help writing and improving strategies, implementing ideas, debugging, optimizing, and understanding code. Your personal AI quant."
- **Simple Machine Learning** — "Train ML models on your backtest data and deploy them inside your strategies — all with just a few lines of code. No PhD required."
- **Rule Significance Testing** — "Don't waste time on signals that are no different than pure luck. Statistically validate your entry timing, filter out noise, and trade like a mathematician — with ease."
- **Optimize Your Strategies** — "Unsure about optimal parameters? Let the optimization mode decide using simple syntax. Fine-tune any strategy parameter with the Optuna library and easy cross-validation."

Community stats claimed: +7,400 GitHub stars, +6,000 Discord members, +14,000 users.

---

## 2. Jesse — Documentation Landing

- **Filename:** `screens/jesse-docs-landing.png`
- **Page URL:** https://docs.jesse.trade/ (VitePress site, title: "Jesse")

**What the page shows / claims.** The docs home, built as a feature-tile
landing rather than a plain TOC. Hero: "Jesse — The Advanced Algo-Trading
Framework in Python / Research, validate, and deploy strategies with Python, a
visual dashboard, or your AI assistant — all self-hosted." Primary CTAs: Get
Started, Connect an AI Assistant, Join the Community. Below are large feature
cards followed by a dense grid of short feature callouts.

**Marketed feature list (verbatim):**

*Large cards:*
- **🔌 Jesse MCP** — "Connect Claude, Codex, Cursor, VS Code, Zed, or any MCP-compatible assistant directly to your local Jesse project. Let it work with strategies and candles, run backtests, optimize parameters, perform significance tests and Monte Carlo analysis, and link you to the saved dashboard results."
- **🧠 Machine Learning** — "Use Jesse's end-to-end ML pipeline to gather labelled training data from backtests, train and evaluate scikit-learn models for classification or regression, and deploy predictions directly inside your strategies."
- **🔬 Rule Significance Testing** — "Statistically validate your entry logic before building a complete strategy. Bootstrap resampling helps determine whether a rule's historical edge is genuine or could have appeared by chance."
- **🎲 Monte Carlo Analysis** — "Stress-test strategies with trade-order shuffling and candles-based simulations to distinguish skill from luck, understand the range of possible outcomes, and guard against overfitting."
- **🧪 Research API and Jupyter** — "Run candle workflows, backtests, optimization, significance tests, Monte Carlo analysis, indicators, and machine learning from Python scripts or Jupyter notebooks for reproducible and automated research."
- **📊 Interactive Trading Charts** — "Inspect candlesticks, strategy indicators, horizontal levels, orders, and completed trades in synchronized charts across backtest, paper, and live sessions — including saved chart history after a session ends."
- **🦀 Rust-Powered Indicators** — "Native Rust implementations make indicator-heavy strategies and large research runs substantially faster. Jesse's benchmarked indicator suite became 3.4× faster after the Rust migration."
- **🔧 Optimize Mode** — "Search strategy parameters efficiently with Optuna and parallel processing powered by Ray, including separate training and testing periods to measure generalization."

*Short feature callouts:*
- 📝 Simple Syntax
- 📊 Comprehensive Indicator Library
- 📈 Smart Ordering — "Supports market, limit, and stop orders, automatically choosing the best one for you."
- ⏰ Multiple Timeframes and Symbols — "Backtest and livetrade multiple timeframes and symbols simultaneously without look-ahead bias."
- 🔒 Self-Hosted and Privacy-First
- 🛡️ Risk Management
- 📋 Metrics System
- 🔍 Debug Mode
- 📈 Leveraged and Short-Selling
- 🔀 Partial Fills
- 🔔 Advanced Alerts
- 🧹 Data Cleaning — "Automatic handling of importing candles and cleaning data."
- 📈 First-Class Support for Trading Futures and Spot
- 🔐 Support for Decentralized Exchanges (DEX)
- 🤖 Reinforcement Learning — Coming Soon

A standing risk disclaimer runs in the footer ("USE THE SOFTWARE AT YOUR OWN
RISK… Be aware of overfitting!").

---

## 3. Jesse — Backtest Docs Page (deeper feature page)

- **Filename:** `screens/jesse-docs-backtest.png`
- **Page URL:** https://docs.jesse.trade/docs/backtest/ (title: "Backtest | Jesse")

**What the page shows / claims.** A docs article inside the full left-sidebar
navigation (which itself reveals the product's whole feature taxonomy:
Getting Started, Essentials, Backtest, Strategies, Indicators, Charts, Live
Trading, Supported Exchanges, Strategy Optimization, Monte Carlo Analysis,
Rule Significance Testing, Research Module, Machine Learning, MCP).

Body claims:
- "Jesse's backtest engine is the most accurate available, simulating market conditions as faithfully as possible including fees, and order types."
- Prerequisites flow: create a strategy → import historical candles → configure routes and date range → press Start. "Jesse will simulate every candle in the selected range and execute your strategy logic candle by candle."
- Results panel metrics named verbatim: "net profit, win rate, max drawdown, Sharpe/Calmar/Sortino ratios, annual return, and many more."
- Chart set named: "cumulative returns vs a benchmark, drawdown periods, the underwater plot, a monthly returns heatmap, and trade P&L distribution."
- Section index: Tabs (multiple simultaneous backtest sessions), Results, Charts, Interactive Charts, Exports (CSV and JSON), Benchmark (running multiple configs simultaneously and comparing).

---

## 4. Jesse — Strategy Optimization Docs Page (deeper feature page)

- **Filename:** `screens/jesse-docs-optimize.png`
- **Page URL:** https://docs.jesse.trade/docs/optimize/ (title: "Strategy Optimization | Jesse")

**What the page shows / claims.** Docs article, same sidebar chrome. Claims:
- "The optimize mode allows you to tune your strategy's parameters (or 'hyperparameters')… It is way more powerful than that."
- Engine: "Jesse optimizes parameters using **Optuna**… accelerated with **Ray** for parallel processing. The optimization process systematically searches through the parameter space to find optimal combinations that maximize your strategy's performance." Efficient search "compared to random or grid search methods."
- Objective: "By default, Jesse optimizes for the Sharpe ratio… This can be changed in the settings to other metrics such as Calmar ratio, Sortino ratio, or Omega ratio."
- Flexibility claim: "You can use it to optimize *anything* that is written inside your strategy file" — e.g. an EMA period, the choice of which indicator to use (RSI vs Stochastic vs SRSI), or choosing between multiple entry rules.
- Sub-pages: Hyperparameters, Executing the Optimize Mode, DNA Usage, Overfitting (dedicated page on guarding against it).

---

## 5. QuantConnect Lean — CLI Feature Page

- **Filename:** `screens/lean-cli-page.png`
- **Page URL:** https://www.lean.io/cli/ (title: "CLI - LEAN Algorithmic Trading Engine - QuantConnect.com")

**What the page shows / claims.** The Lean CLI marketing/feature page. Hero:
"Lean CLI — Local Development, Cloud Backtesting / An easy-to-install and use
distribution of LEAN; research, backtest, optimize, and live-trade on-premises
with no dependency hassles." Shows a terminal-style command list
(`lean init`, `lean create-project "My Project"`, `lean backtest "My Project"`)
and `pip install lean`. Portable downloads for Windows/Mac/Linux. Positions the
CLI as the bridge between **local dev and cloud compute**.

The page's spine is a series of alternating feature bands, each anchored by a
mock terminal (`>_ lean backtest`, `>_ lean cloud backtest`, `>_ lean cloud
push`, `>_ lean cloud pull`), a data-vendor logo wall, and a plugins section.

**Marketed feature/claim list (verbatim):**

*Section headers & claims:*
- **Harness The Power of LEAN Locally or in The Cloud** — "Seamlessly develop locally in your favorite development environment, with full autocomplete and debugging support…" / "Cross-check your local backtests by running the same strategy in the cloud or spin up dozens of servers for batch processing a parameter optimization." Supported IDEs shown: VS Code, Visual Studio, PyCharm, Rider.
- **Easy Synchronization** — "With a simple command you can synchronize your projects to the cloud… Want more processing power than your local environment? Push your code to cloud and then spin up a cluster to run your backtesting. Or pull the code down to your local computer to store backups and code version control."
- **Fully Featured Tool** — "LEAN CLI is a feature-complete tool… We carefully implement every new feature for our cloud and the CLI, ensuring the LEAN project can stand alone."

*The explicit ">_ Feature List" (verbatim):*
- Local / cloud backtesting
- Autocomplete and debugging environments
- Local / cloud optimization
- Local / cloud live trading
- Jupyter research environments
- Generate or download data
- Synchronize projects with cloud
- Create algorithm reports

*Download Financial Data:*
- "Download QuantConnect's peer-reviewed cloud financial data to run backtests and research with LEAN locally. Data is packaged and sold per symbol-day to keep costs low…"
- **Vendor Redundancy** — "Multiple vendors for each dataset giving you leverage to switch if needed."
- **Eliminate Data Wrangling** — "Eliminate 'Extract, transform, load' processes and focus on the search for alpha."
- **Cleaned and Linked to Assets** — "All data is linked to underlying securities and automatically handles corporate actions."
- (Large vendor logo wall: AlgoSeek, Kavout, Brain, ExtractAlpha, Quiver, Kraken, Binance, OANDA, Bitfinex, Coinbase, TickData, Morningstar, CoinGecko, US Treasury, SEC, Tiingo, Nasdaq, etc.)

*Upgrade LEAN with Plugins:*
- "Supercharge your LEAN CLI installation with plugins from QuantConnect to popular institutional data sources and markets."
- Bloomberg (Terminal Link) — Data Source + Brokerage: "Research, Backtest, and Live Data Sources / Live Trade with LEAN through EMSX Network / 1300+ Execution Destinations."
- Trading Technologies — Data Source + Brokerage: "Route to 30+ Brokerage Destinations / Stateful Restart of Portfolio / UAT or Live Mode Support."

Community stats claimed: LEAN GitHub 21,273 stars / 5,180 forks; "chosen by more
than 275,000 quants and engineers" (site meta).

---

## Cross-cutting observations for the QMX sitting

- **Both platforms make "local-first / self-hosted" the headline trust claim.**
  Jesse: "100% local and private… never leave it." Lean: "Local Development,
  Cloud Backtesting… on-premises with no dependency hassles." The private-by-
  default posture is marketed as a feature, not a limitation — directly
  relevant to QMX's privacy stance.
- **Jesse leads with an agent/MCP narrative** ("Your AI agent just became a
  quant"), and its strongest anti-competitor claim is **provenance**: "Real
  results, not hallucinations — Every number comes from Jesse's backtesting
  engine — the agent calls real tools and reads real outputs." This is the
  single most load-bearing claim for QMX (see key_insight).
- **Both frame backtest accuracy as the core credibility axis.** Jesse: "most
  accurate… No look-ahead bias." Lean: cloud/local cross-check of the *same*
  strategy for validation. Verifiability, not raw speed, is the marketed trust
  anchor.
- **The full validation stack is treated as table stakes**: backtest → optimize
  (Optuna/Ray) → Monte Carlo → rule significance testing → walk-forward /
  train-test split → overfitting warnings. QMX's backtesting surface will be
  measured against this full ladder, not just "does it backtest."
- **Reproducible research surface** (Research API + Jupyter, exports to CSV/JSON,
  saved dashboard results, algorithm reports) is marketed on both — an
  agent-consumable, re-runnable artifact trail.
