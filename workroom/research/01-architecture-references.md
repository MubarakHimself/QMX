# 01 — Architecture References: How Existing Trading Frameworks Are Organized

Research date: **2026-08-17**. All maintenance facts checked against GitHub/PyPI on that date.
Scope: NautilusTrader, QuantConnect LEAN (+ LEAN CLI), vectorbt, backtrader, backtesting.py, hummingbot.
Purpose: decide what QMF (Quant Mind Framework) copies, and what it refuses to copy.

---

## In plain words

1. Six well-known trading frameworks already exist. None of them is QMX, but each solved a problem QMF will hit.
2. The strongest architectural idea, found in NautilusTrader and LEAN alike, is a **hard wall**: a small, boring surface the strategy is allowed to touch, and a large, fast, well-tested engine underneath it that the strategy cannot reach into.
3. NautilusTrader draws that wall between languages. The engine is Rust; the strategy is Python. A strategy author gets roughly a dozen `on_something(...)` methods and one `submit_order(...)`, and nothing else.
4. LEAN draws the wall between processes. Thousands of different people's algorithms run on one engine because the engine *loads* the algorithm, gives it a fixed time and memory budget, and survives if the algorithm crashes.
5. Both walls exist for the same reason QMF needs one: the code on the far side is not trusted. For LEAN that untrusted author is a stranger on the internet. For QMF it will be an LLM.
6. Hummingbot has already shipped the exact thing QMX is planning — an LLM that talks to a bot. Their rule is worth stealing verbatim: the model may *suggest* settings, but safety limits "can only be modified by the user, never by the agent."
7. Backtrader is the most-copied Python design of the last decade and it is **dead** — last code change April 2023. Do not build on it.
8. Backtesting.py is small, alive, and elegant, but licensed AGPL-3.0, which is contagious. Read it, do not import it.
9. Vectorbt is alive again (new 1.x line, Rust acceleration) but its licence forbids selling a product that is primarily vectorbt. It is a research tool, not a foundation.
10. None of the six has a **cTrader** adapter. Forex-first via cTrader is something QMX builds itself, from scratch, whatever else it borrows.
11. The organisational pattern that repeats everywhere and works: one *domain model* (instrument, order, position, money), one *event bus*, one *cache*, and venue code confined to a plug-in folder.
12. The organisational anti-pattern that repeats everywhere and hurts: letting the strategy base class grow until it is the whole platform. LEAN's `QCAlgorithm` is now eight source files of API surface. An LLM cannot be trusted with a surface that big.
13. The practical verdict: **copy NautilusTrader's shape, copy LEAN's containment, copy Hummingbot's agent boundary, copy backtesting.py's taste for a tiny API, and write your own broker layer.**
14. Nothing here should be vendored into QMX today. NautilusTrader is mid-rewrite (v2 is still a release candidate as of this week), so treating it as a dependency means adopting somebody else's breaking-change schedule.
15. Every claim below has a URL next to it. Anything I could not confirm from a primary source is marked UNVERIFIED.

---

## Findings

### 1. NautilusTrader — Python surface over a Rust core

**Repo / state.** <https://github.com/nautechsystems/nautilus_trader> — 25,654 stars, licence **LGPL-3.0**, default branch `develop`, 111 open issues, last push **2026-08-17** (same day as this research; commits landing hourly). Source: <https://api.github.com/repos/nautechsystems/nautilus_trader>.

**Version state is the headline.** `version.json` on `develop` reads `"message": "v2.0.0rc3"` (<https://raw.githubusercontent.com/nautechsystems/nautilus_trader/develop/version.json>), while the latest *stable* release on PyPI is **1.231.0**, `requires_python = ">=3.12,<3.15"` (<https://pypi.org/pypi/nautilus_trader/json>). The project is mid-cutover.

**What v2 changed** (<https://raw.githubusercontent.com/nautechsystems/nautilus_trader/develop/MIGRATION_V2.md>):
- The legacy **Cython** implementation is replaced by "a Rust core and PyO3 Python package."
- The tree reorganised into `crates/` (Rust) and `python/`. The old importable `nautilus_trader/` package directory no longer exists on `develop` (confirmed: <https://github.com/nautechsystems/nautilus_trader/tree/develop/nautilus_trader> returns 404).
- v1 moves to branch `develop_v1` for "approximately three months of critical security backports" only.
- Python-facing renames are extensive: `on_quote_tick` → `on_quote`, `subscribe_quote_ticks` → `subscribe_quotes`, `ActorConfig` → `DataActorConfig`, `TradingNodeConfig` → `LiveNodeConfig`, `Order.events` becomes callable, `Order.avg_px`/`slippage` become `decimal.Decimal` (so `Decimal("0.70000") == 0.7` is now `False`).
- Known gaps: v2 `BacktestNode` "does not yet support streaming/catalog iteration"; PostgreSQL persistence incomplete; some v1 config shapes have "no current public Python equivalent."

**Module organisation.** Root tree (<https://api.github.com/repos/nautechsystems/nautilus_trader/git/trees/develop>): `crates/`, `python/`, `docs/`, `examples/`, `schema/`, `scripts/`, `test_data/`, plus governance files including `ADAPTERS.md`, `ROADMAP.md`, `AI_POLICY.md`, `AGENTS.md`, `CLAUDE.md`.

Crates, verified from <https://github.com/nautechsystems/nautilus_trader/tree/develop/crates>:

```
adapters  analysis  backtest  cli  common  core  cryptography  data
event_store  execution  indicators  infrastructure  live  model
network  persistence  plugin  portfolio  pyo3  risk  serialization
system  testkit  trading
```

`crates/README.md` states the intent plainly: `nautilus-trader` is a thin container crate re-exporting `core`, `model`, `common`; consumers pick `nautilus-data` (data engine), `nautilus-backtest`, `nautilus-live`, `nautilus-trading` ("Strategy and actor APIs"), `nautilus-execution`, `nautilus-portfolio`, `nautilus-risk`. "Venue adapters publish as separate crates."

The docs describe the same thing as three layers (<https://nautilustrader.io/docs/latest/concepts/architecture>): **core/low-level** (`core`, `common`, `network`, `serialization`, `model`), **components** (`accounting`, `adapters`, `cache`, `data`, `execution`, `portfolio`, `risk`), **system implementations** (`backtest`, `live`, `system`).

**Runtime components** (same page): `NautilusKernel` ("the central orchestration component responsible for initializing and managing all system components"), `MessageBus` (pub/sub + request/response), `Cache` ("instruments, accounts, orders, positions"), `DataEngine`, `ExecutionEngine`, `RiskEngine` (pre-trade validation).

**Market data flow**, quoted from the architecture doc:
1. venue-specific client receives WebSocket data, constructs structured objects;
2. adapter sends events over an MPSC channel to the engine;
3. `DataEngine` dispatches to a specialised handler;
4. quote is written to `Cache`;
5. engine publishes on an instrument-specific `MessageBus` topic;
6. subscribed strategy handler runs.

The ordering is load-bearing and explicitly documented: "For quotes, trades, and bars the cache-then-publish order means your strategy handler can always read the latest value from the cache."

**Threading.** "Within a node, the kernel consumes and dispatches messages on a single thread" — message bus, strategies, risk checks and cache all on that thread; network I/O on separate threads/async runtimes feeding back through channels. Stated purpose: "deterministic event ordering and … backtest-live parity."

**Design principles** stated on the same page: Domain Driven Design, event-driven, **crash-only** ("systems which can recover cleanly from crashes are more robust than those with separate (and rarely tested) graceful shutdown paths"), **fail-fast** ("data corruption or invariant violations trigger immediate termination").

**Strategy API — the constrained surface.** `Strategy` inherits `Actor` (<https://nautilustrader.io/docs/latest/concepts/strategies>, <https://nautilustrader.io/docs/latest/concepts/actors>). The split is the containment mechanism:

| Capability | `Actor` | `Strategy` |
|---|---|---|
| subscribe/request data, timers, cache, portfolio read, msgbus, logging | yes | yes |
| submit / modify / cancel orders | **no** | yes |

Handlers are a closed set of `on_*` methods: `on_start`, `on_stop`, `on_resume`, `on_reset`, `on_dispose`; `on_bar`, `on_quote_tick`, `on_trade_tick`, `on_order_book`, `on_instrument`; `on_order_submitted/accepted/filled/rejected/canceled`; `on_position_opened/changed/closed`. Dispatch runs "from most specific to most general handler."

Minimal real strategy (verbatim from <https://nautilustrader.io/docs/latest/getting_started/quickstart>; note this is the *stable* v1-line docs, so v2 import paths differ per `MIGRATION_V2.md`):

```python
class EMACrossConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal
    fast_ema_period: int = 10
    slow_ema_period: int = 20


class EMACross(Strategy):
    def __init__(self, config: EMACrossConfig):
        super().__init__(config)
        self.fast_ema = ExponentialMovingAverage(config.fast_ema_period)
        self.slow_ema = ExponentialMovingAverage(config.slow_ema_period)

    def on_start(self):
        self.register_indicator_for_bars(self.config.bar_type, self.fast_ema)
        self.register_indicator_for_bars(self.config.bar_type, self.slow_ema)
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar):
        if not self.indicators_initialized():
            return
        if self.fast_ema.value >= self.slow_ema.value:
            if self.portfolio.is_flat(self.config.instrument_id):
                self.buy()
            elif self.portfolio.is_net_short(self.config.instrument_id):
                self.close_all_positions(self.config.instrument_id)
                self.buy()
        ...

    def buy(self):
        instrument = self.cache.instrument(self.config.instrument_id)
        order = self.order_factory.market(
            self.config.instrument_id, OrderSide.BUY,
            instrument.make_qty(self.config.trade_size),
        )
        self.submit_order(order)
```

Four containment properties worth naming explicitly:
- **Config is a frozen typed object**, separate from mutable strategy state. Parameters cannot be smuggled in as globals.
- **Orders are built by an injected `order_factory`**, not constructed freely; submitted orders route through `OrderEmulator` / `ExecAlgorithm` / `RiskEngine` depending on parameters.
- **Indicators are registered, not called.** `register_indicator_for_bars(bar_type, indicator)` — the engine drives updates; the strategy only reads `.value`. Indicators live in `crates/indicators` (Rust) and are exposed to Python.
- **Data arrives only by subscription.** No strategy-side I/O is part of the sanctioned pattern.

**Adapter pattern** (<https://nautilustrader.io/docs/latest/concepts/adapters>). A venue integration is five pieces: `InstrumentProvider` (venue instruments → Nautilus `Instrument`), `DataClient` (subscriptions + historical requests, normalised to Nautilus types), `ExecutionClient` (order commands → venue API; execution reports → Nautilus events), `HttpClient`, `WebSocketClient`. Plus config classes and factory functions. "The `ExecutionEngine` automatically routes commands to the correct execution client based on the order's venue." This is a textbook ports-and-adapters boundary and is the single most copyable thing in the project.

**Adapter governance** (<https://raw.githubusercontent.com/nautechsystems/nautilus_trader/develop/ADAPTERS.md>, last updated 2026-06-30). Tiers: **Official** (in-repo, maintainer-supported), **Community** (listed, not endorsed), **External**. Official list: Architect (AX), Betfair, Binance, Blockchain, BitMEX, Bybit, Coinbase, Databento, Deribit, Derive, dYdX, Hyperliquid, Interactive Brokers, Kraken, Lighter, OKX, Polymarket, Sandbox, Tardis. Community listings: `mt5-connect` (MetaTrader 5), `sinopac-nt-community`.

> **There is no cTrader adapter, official or community.** Forex retail brokerage is represented only by Interactive Brokers (official) and MetaTrader 5 (community). This is a direct, load-bearing finding for QMX.

Community listing criteria are also a good governance template: licence compatible with LGPL-3.0, identifiable maintainer, "repository shows activity within the last six months," install/usage docs.

**Roadmap / scope** (<https://raw.githubusercontent.com/nautechsystems/nautilus_trader/develop/ROADMAP.md>). Explicitly **out of scope**: UI dashboards or frontends; distributed/parallel backtest orchestration; "integrated hyper-parameter optimization or built-in AI/ML tooling"; extra cloud/database/monitoring integrations. Explicitly in scope: single-node backtest with live parity, single-node live trading. It is an **open-core** project with a stated "Python API Commitment" despite the Rust core. Maintainers state they have "limited bandwidth to support new official integrations" and require an RFC before an adapter PR.

**Maintenance verdict:** very actively maintained, but *unstable by design right now* — v2.0.0rc3, formal deprecations only arriving at 2.0.

---

### 2. QuantConnect LEAN — one engine, thousands of strategies

**Repo / state.** <https://github.com/QuantConnect/Lean> — 21,240 stars, licence **Apache-2.0**, primary language C#, 270 open issues, last push **2026-08-14** (<https://api.github.com/repos/QuantConnect/Lean>). Actively developed (an `Algorithm/` commit dated 2026-08-13 improving Python datetime error messages).

**Module organisation** — top-level projects (<https://api.github.com/repos/QuantConnect/Lean/contents/>):

```
Algorithm            Algorithm.CSharp     Algorithm.Framework   Algorithm.Python
AlgorithmFactory     Api                  Brokerages            Common
Compression          Configuration        Data                  DownloaderDataProvider
Engine               Indicators           Launcher              Logging
Messaging            Optimizer            Optimizer.Launcher    Queues
Report               Research             Tests                 ToolBox
```

The separation that matters: `Algorithm` (the user-facing surface), `Engine` (the runtime), `Brokerages` (adapters), `Indicators` (a standalone library), `AlgorithmFactory` (the loader/isolator), `Launcher` (the composition root and its `config.json`).

`Engine/` contents (<https://api.github.com/repos/QuantConnect/Lean/contents/Engine>): `Engine.cs`, `AlgorithmManager.cs`, `AlgorithmTimeLimitManager.cs`, `Initializer.cs`, `LeanEngineAlgorithmHandlers.cs`, `LeanEngineSystemHandlers.cs`, and folders `DataFeeds`, `HistoricalData`, `RealTime`, `Results`, `Setup`, `Storage`, `TransactionHandlers`, `Server`.

**Every seam is a config-named plug-in.** From `Launcher/config.json` (<https://raw.githubusercontent.com/QuantConnect/Lean/master/Launcher/config.json>) the top-level keys are literally class names:

```
"environment": "backtesting"
"algorithm-type-name", "algorithm-language", "algorithm-location"
"log-handler":        "QuantConnect.Logging.CompositeLogHandler"
"messaging-handler":  "QuantConnect.Messaging.Messaging"
"job-queue-handler":  "QuantConnect.Queues.JobQueue"
"api-handler":        "QuantConnect.Api.Api"
"map-file-provider", "factor-file-provider"
"data-provider":      "QuantConnect.Lean.Engine.DataFeeds.DefaultDataProvider"
"object-store":       "QuantConnect.Lean.Engine.Storage.LocalObjectStore"
"data-aggregator":    "QuantConnect.Lean.Engine.DataFeeds.AggregationManager"
```

and each *environment* block supplies `live-mode`, `setup-handler`, `result-handler`, `data-feed-handler`, `real-time-handler`, `transaction-handler`, `history-provider`, `data-queue-handler`. Backtest vs live is a **configuration swap of handlers**, not a different codebase. That is why "the same algorithm runs in backtest and live" is true in LEAN.

**Strategy authoring API.** One base class, `QCAlgorithm`, two required methods. Verbatim from <https://raw.githubusercontent.com/QuantConnect/Lean/master/Algorithm.Python/BasicTemplateAlgorithm.py>:

```python
from AlgorithmImports import *

class BasicTemplateAlgorithm(QCAlgorithm):
    '''Basic template algorithm simply initializes the date range and cash'''

    def initialize(self):
        self.set_start_date(2013,10, 7)
        self.set_end_date(2013,10,11)
        self.set_cash(100000)
        self.add_equity("SPY", Resolution.MINUTE)
        self.debug("numpy test >>> print numpy.pi: " + str(np.pi))

    def on_data(self, data):
        '''OnData event is the primary entry point for your algorithm.'''
        if not self.portfolio.invested:
            self.set_holdings("SPY", 1)
```

`initialize()` declares universe, cash, dates, resolution; `on_data(slice)` receives a `Slice` keyed by symbol and is where decisions happen. `from AlgorithmImports import *` is a single curated namespace — one import line is the whole vocabulary, which is exactly the property an LLM author needs.

**But the surface is enormous.** `Algorithm/` (<https://github.com/QuantConnect/Lean/tree/master/Algorithm>) shows `QCAlgorithm` split across partial classes: `QCAlgorithm.cs`, `.Trading.cs`, `.Indicators.cs`, `.History.cs`, `.Universe.cs`, `.Plotting.cs`, `.Framework.cs`, `.Framework.Python.cs`, `.Python.cs`, plus `Alphas/`, `Execution/`, `Portfolio/`, `Risk/`, `Selection/`. The containment is *not* achieved by keeping the API small.

**How LEAN actually contains thousands of strategies: the Loader + Isolator.** From <https://raw.githubusercontent.com/QuantConnect/Lean/master/AlgorithmFactory/Loader.cs>:

> "Loader creates and manages the memory and exception space of the algorithm, ensuring if it explodes the Lean Engine is intact."

Concretely:
- `TryCreateAlgorithmInstanceWithIsolator(assemblyPath, ramLimit, out instance, out error)` wraps instantiation in an `Isolator` with **both a RAM limit and a time limit** (default `TimeSpan.FromSeconds(10)`), reporting "Failed to create algorithm instance within 10 seconds."
- Type discovery is strict: exactly one non-abstract class that implements `IAlgorithm`, is not `QCAlgorithm`/`QCAlgorithmFramework`, and has a default constructor. Multiple candidates are an error unless a resolver picks one.
- Python algorithms are loaded via pythonnet: `PythonInitializer.Initialize(); algorithmInstance = new AlgorithmPythonWrapper(moduleName);` — the Python class is *wrapped* into the C# `IAlgorithm` interface. The engine only ever talks to `IAlgorithm`.
- By default (`mute-python-library-logging`) the loader executes `sys.stdout = open(os.devnull, 'w')` inside the algorithm's interpreter.
- `Engine/AlgorithmTimeLimitManager.cs` continues that budget enforcement into the run loop.

**This is the containment pattern QMF wants**: *the untrusted author writes a class conforming to one interface; the platform instantiates it under a resource budget, wraps it, and drives it.* The strategy never owns the loop.

**Algorithm Framework — reuse without a shared engine fork** (<https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/overview>). Five swappable model types composed in a fixed pipeline:

```
Universe Selection → Alpha → Portfolio Construction → Risk Management → Execution
                     Insight →  PortfolioTarget  →  (adjusted target) → orders
```

```python
class MyFrameworkAlgorithm(QCAlgorithm):
    def initialize(self) -> None:
        self.set_universe_selection(EmaCrossUniverseSelectionModel())
        self.add_alpha(RsiAlphaModel())
        self.set_portfolio_construction(EqualWeightingPortfolioConstructionModel())
        self.set_execution(ImmediateExecutionModel())
        self.add_risk_management(NullRiskManagementModel())
```

"The framework data output of each module flows into the following module." The typed hand-off objects (`Insight`, `PortfolioTarget`) are what make the modules interchangeable. **This is the single most important idea for LLM-authored strategies**: an LLM writing only an *Alpha model* emits `Insight` objects and physically cannot size a position or place an order — position sizing and risk are somebody else's module.

**Indicators** (<https://www.quantconnect.com/docs/v2/writing-algorithms/indicators/key-concepts>). Two modes: helper methods (`self.bb(symbol, 20, 2, Resolution.DAILY)`) that "automatically update as your algorithm receives new data," and manual construction (`BollingerBands(20, 2)`) requiring explicit updates. Warm-up is first-class: `Settings.AutomaticIndicatorWarmUp = True`, or `self.warm_up_indicator(symbol, indicator)`. Dynamic universes attach/detach indicators in `on_securities_changed`, with `deregister_indicator` to avoid leaks.

**Brokerage adapter pattern.** From <https://raw.githubusercontent.com/QuantConnect/Lean/master/Common/Interfaces/IBrokerage.cs>:

> "Brokerage interface that defines the operations all brokerages must implement. The IBrokerage implementation must have a matching IBrokerageFactory implementation."

The interface is events + commands + state:
- events: `OrderIdChanged`, `OrdersStatusChanged` (`List<OrderEvent>`), `OrderUpdated`, `OptionPositionAssigned`, `OptionNotification`, `NewBrokerageOrderNotification`, `DelistingNotification`, `AccountChanged`, `Message`;
- commands: `PlaceOrder(Order)`, `UpdateOrder(Order)`, `CancelOrder(Order)`, `Connect()`, `Disconnect()`;
- state/queries: `Name`, `IsConnected`, `GetOpenOrders()`, `GetAccountHoldings()`, `GetCashBalance()`, `AccountBaseCurrency`, `AccountInstantlyUpdated`, `GetHistory(HistoryRequest)`, `ConcurrencyEnabled`.

Live market data is a *separate* seam (`data-queue-handler`), and historical data a third (`history-provider`). Splitting execution / streaming data / historical data into three interfaces is deliberate and correct — a broker may be excellent at one and useless at another.

**LEAN CLI** (<https://github.com/QuantConnect/lean-cli>, Apache-2.0, 322 stars, last push **2026-08-12**; docs <https://www.quantconnect.com/docs/v2/lean-cli/key-concepts/getting-started>). "A cross-platform CLI which makes it easier to develop with the LEAN engine locally and in the cloud." Commands: `lean init`, `lean login`, `lean cloud pull` / `push`, `lean data generate`, `lean backtest`, `lean cloud backtest`, `lean live`, `lean research`, `lean optimize`. Local runs execute "in a Docker container containing the same packages as the ones used on QuantConnect.com." `lean init` creates `lean.json` (engine config) and `data/`.

That last point is the operational lesson: **the reproducibility guarantee is a container image, not a requirements file.**

**Maintenance verdict:** actively maintained, stable, permissively licensed. The heaviest of the six.

---

### 3. vectorbt — vectorised research, not an execution platform

**Repo / state.** <https://github.com/polakowo/vectorbt> — 8,705 stars, 136 open issues, last push **2026-08-02** (<https://api.github.com/polakowo/vectorbt> via `api.github.com/repos/polakowo/vectorbt`). The GitHub API reports licence as **"Other"** — see licence note below.

**Maintenance state, corrected.** The common belief that open-source vectorbt was abandoned for vectorbt PRO is **false as of 2026**. Commit history (<https://github.com/polakowo/vectorbt/commits/master>) shows sustained substantive work: `Add Python 3.14 and pandas 3 support` (2026-07-05, "tightening supported Python to >=3.11,<3.15", "aligns the Rust extension with newer pyo3/numpy/rand APIs"), `Release 1.1.0 and update CI metadata` (2026-07-05, "bumps vectorbt and vectorbt-rust to 1.1.0"), `Improve rolling std numerical stability` (2026-07-14, Welford/Kahan in both the Numba and Rust paths), plus merged community PRs. PyPI confirms **1.1.0 released 2026-07-05**, preceded by 1.0.0 (2026-04-22), 0.28.5 (2026-03-26), 0.28.4 (2026-01-26), 0.28.2 (2025-12-12) (<https://pypi.org/pypi/vectorbt/json>).

**Licence — the blocker.** README, verbatim: *"This work is fair-code distributed under the Apache 2.0 with Commons Clause license. The source code is publicly available, and everyone (individuals and organizations) may use it for free. However, you may not sell products or services that are primarily this software."* (<https://raw.githubusercontent.com/polakowo/vectorbt/master/README.md>). Commons Clause is **not** an OSI open-source licence. For a solo operator's internal use this is fine; for anything QMX might ever sell or offer as a service it is a live legal question.

**Execution model.** Fully **vectorised**, not event-driven. README: it "packs thousands of configurations into NumPy arrays, accelerates the hot path with Numba and Rust, and runs them all at once," versus "iterating through bars with one strategy at a time." Minimal example:

```python
import vectorbt as vbt

data = vbt.YFData.download("BTC-USD")
price = data.get("Close")

pf = vbt.Portfolio.from_holding(price, init_cash=100)
print(pf.total_profit())
```

The authoring surface is not a class with callbacks — it is **arrays in, `Portfolio` out** (`Portfolio.from_holding`, `from_signals`, `from_order_func`). There is a callback escape hatch (`from_order_func` with per-bar Numba callbacks, referenced in the 2026-07-04 `init_temp_records` commit) but the idiom is signal matrices.

**Module organisation** (<https://github.com/polakowo/vectorbt/tree/master/vectorbt>): `base/`, `data/`, `generic/`, `indicators/`, `labels/`, `messaging/`, `portfolio/`, `records/`, `returns/`, `signals/`, `templates/`, `utils/`, plus `_engine.py`, `_settings.py`, `ohlcv_accessors.py`, `px_accessors.py`, `root_accessors.py`. Note `records/` — trades/orders/logs are stored as structured record arrays, which is why post-analysis is fast.

**Indicators.** First-class `indicators/` module with an indicator *factory* (parameter grids expand into extra array dimensions), plus TA-Lib as an optional extra ("flatten the full/full-no-talib extras into a single 'full' extra that includes TA-Lib directly", commit 2026-07-04).

**Venue/broker adapters.** None. `data/` provides download sources; `messaging/` is Telegram notification only. vectorbt does not execute.

**Verdict:** excellent parameter-sweep research engine, alive, Rust-accelerated — and structurally incapable of being QMF's live core. Licence makes vendoring risky.

---

### 4. backtrader — the influential dead one

**Repo / state.** <https://github.com/mementum/backtrader> — 22,869 stars, licence **GPL-3.0**, 63 open issues, not archived. But `master`'s newest commit is **2023-04-19, "Version 1.9.78.123"** (<https://github.com/mementum/backtrader/commits/master>), and PyPI's newest release is **1.9.78.123, uploaded 2023-04-19** (<https://pypi.org/pypi/backtrader/json>). Commits before that are mostly matplotlib-compatibility patches from third parties.

> **Maintenance verdict: unmaintained since April 2023.** The repository's `pushed_at` of 2024-08-19 reflects non-`master` activity, not development. Do not build on it. (A community fork `backtrader2/backtrader` is referenced from backtrader commit messages; its current state is **UNVERIFIED** here.)

**Why it still matters:** its vocabulary is the one most Python trading code and most LLM training data uses. Concepts (<https://www.backtrader.com/docu/concepts/>):

- **Cerebro** — the engine/orchestrator; you `addstrategy`, `adddata`, `run`.
- **Data Feeds** — "automagically provided member variables to the strategy in the form of an array and shortcuts to the array positions": `self.datas[0]`, `self.data`, `self.data0`.
- **Lines** — declarative time series: `lines = ('sma',)`, indexed `[0]` = now, `[-1]` = previous.
- **Params** — `params = dict(period=20)`, read as `self.p.period`.
- **Strategy** — logic in `next()`, called once per bar. Doc: "Strategies do only get values. Indicators do also set values."
- **Indicators**, **Orders**, **Broker** (cash/commission/slippage), **Sizers** (position sizing as a separate pluggable object), **Analyzers** (Sharpe, drawdown), **Observers** (portfolio stats).

Two ideas worth stealing even from a dead project: **Sizer as a separate object** (position sizing is not the strategy's job) and **Analyzer as a separate object** (metrics are not the strategy's job).

Two ideas worth actively avoiding: the **metaclass/`lines` magic**, which makes the code opaque to humans and to static analysis; and **operator overloading that means different things in `__init__` than in `next()`** (hence backtrader's own `bt.And()`, `bt.Or()`, `bt.If()` workarounds because Python's `and`/`or` cannot be overloaded). An LLM writing against that API will get it subtly wrong.

---

### 5. backtesting.py — the small, tasteful one

**Repo / state.** <https://github.com/kernc/backtesting.py> — 8,859 stars, licence **AGPL-3.0**, 65 open issues, last push **2026-08-05** (<https://api.github.com/repos/kernc/backtesting.py>). PyPI `backtesting` **0.6.6, uploaded 2026-07-22**, `requires_python >=3.9` (<https://pypi.org/pypi/backtesting/json>). **Actively maintained.**

**Whole API in one example** (verbatim, <https://raw.githubusercontent.com/kernc/backtesting.py/master/README.md>):

```python
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from backtesting.test import SMA, GOOG

class SmaCross(Strategy):
    def init(self):
        price = self.data.Close
        self.ma1 = self.I(SMA, price, 10)
        self.ma2 = self.I(SMA, price, 20)

    def next(self):
        if crossover(self.ma1, self.ma2):
            self.buy()
        elif crossover(self.ma2, self.ma1):
            self.sell()

bt = Backtest(GOOG, SmaCross, commission=.002, exclusive_orders=True)
stats = bt.run()
bt.plot()
```

**Execution model:** event-driven at bar granularity, with a vectorised `init()` precomputation phase. `init()` declares indicators; `next()` decides. Indicator integration is one method — `self.I(func, *args, name=…, plot=…, overlay=…)` — and it is **BYO indicator library**: any callable returning an array works (README: "works with any indicator library"). No indicator zoo to maintain.

**API surface** (<https://kernc.github.io/backtesting.py/doc/backtesting/backtesting.html>): `Backtest(data, strategy, cash, spread, commission, margin, trade_on_close, hedging, exclusive_orders, finalize_trades)`; `run()` → stats `Series`; `optimize(maximize='SQN', method='grid'|'sambo', constraint=…)`; `plot()`. Strategy exposes `data`, `position`, `orders`, `trades`, `closed_trades`, `equity`, and `buy(size, limit, stop, sl, tp, tag)` / `sell(...)`. `Order`, `Trade`, `Position` are small value-ish objects.

**Documented limitations:** single instrument per `Backtest`; no intra-bar fills (market orders fill next bar open unless `trade_on_close=True`); the strategy starts only once all indicators are non-NaN.

**Adapters:** none. It is a backtester, full stop.

**Licence caution: AGPL-3.0 is the strongest copyleft of the six.** Linking QMF against it would put QMF's own source under AGPL obligations if QMX is ever network-served. Read it for API taste; do not import it.

---

### 6. hummingbot — connectors, executors, and a shipped LLM boundary

**Repo / state.** <https://github.com/hummingbot/hummingbot> — 19,486 stars, licence **Apache-2.0**, 145 open issues, last push **2026-08-16** (<https://api.github.com/repos/hummingbot/hummingbot>). Actively maintained. README claims "$34 billion in trading volume across 140+ venues in the past year" (<https://raw.githubusercontent.com/hummingbot/hummingbot/master/README.md>).

**Module organisation** (<https://api.github.com/repos/hummingbot/hummingbot/contents/hummingbot>): `cli/`, `client/`, `connector/`, `core/`, `data_feed/`, `logger/`, `model/`, `notifier/`, `remote_iface/`, `strategy/`, `strategy_v2/`, `templates/`, `user/`. Strategies live in a top-level `scripts/` directory outside the package (<https://github.com/hummingbot/hummingbot/tree/master/scripts>), which is how a user's strategy stays separate from the framework's code — a drop-in folder.

**Four-tier strategy model** (README):

| Tier | What it is |
|---|---|
| **Scripts** | single-file Python strategies |
| **Controllers (V2)** | reusable strategies with live-tunable configs and backtesting |
| **Executors** | self-contained blocks managing order lifecycles (position, DCA, grid, arbitrage, TWAP, LP) |
| **V1 Strategies** | legacy (Pure Market Making, Cross-Exchange MM) |

The **Executor** tier is the interesting one for QMF. An executor owns a *complete order lifecycle* (a DCA ladder, a grid, a trailing position with stop and take-profit). A controller does not place orders bar-by-bar; it emits **executor actions**. From `ControllerBase` (<https://raw.githubusercontent.com/hummingbot/hummingbot/master/hummingbot/strategy_v2/controllers/controller_base.py>) the contract is two overrides:
- `update_processed_data()` — "implement the logic to update the market data used by the controller";
- `determine_executor_actions()` — "implement the logic to determine the actions that the executors should take."

That is a *declare-intent* API rather than a *place-orders* API, and it is the crypto-native cousin of LEAN's `Insight` → `PortfolioTarget` pipeline.

**Minimal real strategy** (verbatim, <https://raw.githubusercontent.com/hummingbot/hummingbot/master/scripts/simple_pmm.py>), showing the script tier:

```python
class SimplePMMConfig(StrategyV2ConfigBase):
    script_file_name: str = os.path.basename(__file__)
    controllers_config: List[str] = []
    exchange: str = Field("binance_paper_trade")
    trading_pair: str = Field("ETH-USDT")
    order_amount: Decimal = Field(0.01)
    bid_spread: Decimal = Field(0.001)
    ask_spread: Decimal = Field(0.001)
    order_refresh_time: int = Field(15)
    price_type: str = Field("mid")

    def update_markets(self, markets: MarketDict) -> MarketDict:
        markets[self.exchange] = markets.get(self.exchange, set()) | {self.trading_pair}
        return markets


class SimplePMM(StrategyV2Base):
    def __init__(self, connectors: Dict[str, ConnectorBase], config: SimplePMMConfig):
        super().__init__(connectors, config)
        self.config = config
        self.price_source = PriceType.LastTrade if self.config.price_type == "last" else PriceType.MidPrice

    def on_tick(self):
        if self.create_timestamp <= self.current_timestamp:
            self.cancel_all_orders()
            proposal: List[OrderCandidate] = self.create_proposal()
            proposal_adjusted: List[OrderCandidate] = self.adjust_proposal_to_budget(proposal)
            self.place_orders(proposal_adjusted)
            self.create_timestamp = self.config.order_refresh_time + self.current_timestamp

    def adjust_proposal_to_budget(self, proposal):
        return self.connectors[self.config.exchange].budget_checker.adjust_candidates(proposal, all_or_none=True)

    def did_fill_order(self, event: OrderFilledEvent):
        ...
```

Three things to note: the driver is a **clock tick** (`on_tick`), not a data event; orders are proposed as **`OrderCandidate`** objects and then passed through a **`budget_checker`** before submission (an explicit affordability gate between intent and execution); and config is a Pydantic model that also declares which markets it needs (`update_markets`), so the framework knows what to connect to before the strategy runs.

**Connector (adapter) pattern.** `hummingbot/connector/` (<https://github.com/hummingbot/hummingbot/tree/master/hummingbot/connector>) splits by venue *kind*: `exchange/` (spot CEX), `derivative/`, `gateway/` (DEX via the TypeScript Gateway middleware), `other/`, plus shared machinery: `connector_base.pyx`/`.pxd` (Cython), `exchange_base.pyx`, `exchange_py_base.py`, `perpetual_derivative_py_base.py`, `budget_checker.py`, `client_order_tracker.py`, `trading_rule.pyx`, `time_synchronizer.py`, `markets_recorder.py`, and — importantly — `test_support/`, a shared conformance-test harness so every new connector is validated against the same suite. README classifies venues as **CLOB CEX / CLOB DEX / AMM DEX**.

**Condor — the LLM boundary, already shipped.** <https://hummingbot.org/blog/introducing-condor-the-open-source-harness-for-trading-agents/>, repo <https://github.com/hummingbot/condor>. Architecture, quoted:

| Layer | Role | Technology |
|---|---|---|
| Probabilistic (Agent) | interprets markets, reasons about strategy, decides actions | LLM (Claude, GPT, Gemini) |
| Deterministic (Execution) | converts decisions into orders with reliability | Hummingbot API |

Stated rationale, verbatim: **speed** — "deterministic systems handle time-critical trades (stop-losses, take-profits) without LLM latency"; **efficiency** — "deterministic code handles routine operations, reducing token consumption significantly"; **security** — "the execution layer constrains what an AI agent can actually perform."

Guardrail rule, verbatim: configuration parameters can be suggested by agents but require user approval, and safety limits "can *only* be modified by the user, never by the agent."

The agent reaches the platform through **MCP tools** against the Hummingbot API — i.e. a fixed tool schema, not arbitrary code. The Condor repo itself is a Telegram front end (`handlers/`, `hummingbot_api_client/`, `utils/`, `routines/`, `main.py`) with an `/agent` command supporting OpenAI, OpenRouter, or any OpenAI-compatible endpoint. Condor's own licence is **not stated in its README — UNVERIFIED**; hummingbot core is Apache-2.0.

---

### Comparative table

| | **NautilusTrader** | **LEAN** | **vectorbt** | **backtrader** | **backtesting.py** | **hummingbot** |
|---|---|---|---|---|---|---|
| Core language | Rust core + PyO3 Python | C# engine, Python via pythonnet | Python + Numba + Rust ext | pure Python | pure Python | Python + Cython |
| Execution model | event-driven, single-threaded kernel, deterministic | event-driven, handler-swapped per environment | **vectorised** (arrays, whole-grid) | event-driven, bar loop | event-driven, bar loop (+vectorised `init`) | event-driven + clock tick |
| Backtest↔live parity | same engine, same semantics; explicit design goal | same engine; environment swaps handlers | none (no live) | live feeds existed, now unmaintained | none (no live) | paper-trade connectors + V2 backtesting |
| Strategy base | `Strategy` (extends `Actor`) | `QCAlgorithm` | none (function/array) | `bt.Strategy` | `Strategy` | `StrategyV2Base` / `ControllerBase` |
| Author surface size | small, closed `on_*` set + `order_factory` | very large (8 partial classes) | n/a | medium + metaclass magic | **tiny** (`init`, `next`, `I`, `buy`, `sell`) | medium; controllers narrower than scripts |
| Config pattern | frozen typed `StrategyConfig` | `initialize()` imperative | function kwargs | `params = dict(...)` | class attrs / `run(**kwargs)` | Pydantic `StrategyV2ConfigBase` |
| Order gate before venue | `RiskEngine` (+`OrderEmulator`, exec algos) | Risk Management model / transaction handler | n/a | Broker + Sizer | internal broker sim | `budget_checker.adjust_candidates` |
| Venue adapter seam | `InstrumentProvider` + `DataClient` + `ExecutionClient` + factories | `IBrokerage` (+`IBrokerageFactory`), `data-queue-handler`, `history-provider` — three seams | none | broker/store/feed classes | none | `connector/` per venue kind + `test_support/` conformance suite |
| Adapter count/kinds | 19 official (crypto, IB, Betfair, Databento…); **no cTrader** | many brokerages incl. IB, Tradier, crypto | n/a | IB/Oanda/VC (stale) | n/a | 140+ venues claimed; CEX/DEX/AMM |
| Indicators | Rust `crates/indicators`, registered to bar types | `Indicators` project; auto or manual + warm-up | `indicators/` factory + TA-Lib extra | `lines`-based indicator objects | **BYO** via `self.I(func, …)` | `candles`/`data_feed` + external TA |
| Multi-strategy containment | one process, many strategies on one kernel; no OS-level isolation | **Loader + Isolator**: RAM cap, 10 s instantiation limit, `IAlgorithm` wrapper, engine survives crash | n/a | n/a | n/a | separate bot instances; API-mediated agents |
| Licence | **LGPL-3.0** | **Apache-2.0** | Apache-2.0 **+ Commons Clause** (not OSI) | **GPL-3.0** | **AGPL-3.0** | **Apache-2.0** |
| Latest release | v2.0.0**rc3** (dev); 1.231.0 stable on PyPI | continuous (`master`) | 1.1.0 (2026-07-05) | 1.9.78.123 (2023-04-19) | 0.6.6 (2026-07-22) | continuous (`master`) |
| Last activity | **2026-08-17** | **2026-08-14** | **2026-08-02** | **2023-04-19** | **2026-08-05** | **2026-08-16** |
| Maintenance verdict | very active, **mid-rewrite** | very active, stable | active, single-maintainer, PRO upsell | **abandoned** | active | very active |

---

## What QMF should copy / avoid

### Copy — structure

1. **Three-ring module layout, borrowed from NautilusTrader's layering.**
   `qmf/core` (identifiers, time, money, precision) → `qmf/model` (Instrument, Order, Position, Bar, Quote, Fill) → `qmf/engine` (data, execution, risk, portfolio, cache, bus) → `qmf/adapters/<venue>` → `qmf/runtime` (backtest / live kernels) → `qmf/strategies` (user + LLM code, importable *by* nothing else). Dependency arrows point one way only. Ref: <https://nautilustrader.io/docs/latest/concepts/architecture>.

2. **One domain model, defined once.** Every framework that survived has exactly one `Order`/`Position`/`Instrument` type that both the backtester and the live path use. This is what makes "same strategy, backtest and live" true rather than aspirational.

3. **Cache-then-publish ordering on the data path.** Write the tick/bar into the cache *before* publishing to subscribers, so a handler can always read consistent latest state. Copy this exactly; it is a subtle bug class eliminated by ordering. Ref: architecture doc, quoted above.

4. **Single-threaded deterministic kernel; all I/O on the edge.** Network clients run async on their own threads and push into a channel; the kernel drains it on one thread. Determinism is the entire reason backtest results mean anything.

5. **Three separate adapter seams, per LEAN, not one.** `ExecutionClient` (place/modify/cancel/account), `DataClient` (live streaming subscriptions), `HistoryProvider` (historical bars). cTrader may serve all three; a future data vendor will serve only the third. Ref: `IBrokerage.cs` + `Launcher/config.json` keys `data-queue-handler` / `history-provider`.

6. **Adapters expose events, not callbacks into strategies.** `IBrokerage` is a good shape to imitate: `OrdersStatusChanged`, `AccountChanged`, `Message` as events; `PlaceOrder/UpdateOrder/CancelOrder/Connect/Disconnect` as commands; `GetOpenOrders/GetAccountHoldings/GetCashBalance` as reconciliation queries. Reconciliation queries are not optional — a VPS restart needs them.

7. **A conformance test-kit for adapters, per hummingbot's `connector/test_support/`.** One shared suite every venue adapter must pass. With one operator and LLM contributors, this is the only affordable way to trust a second venue.

8. **Environment as configuration, per LEAN.** `backtest` / `paper` / `live` should differ by *which handler classes are named in config*, not by which code path is taken. Ref: `Launcher/config.json` environment blocks.

9. **Sizer and Analyzer as separate objects** (from backtrader). Position sizing and performance metrics are not strategy responsibilities. This directly shrinks what an LLM has to get right.

### Copy — the LLM containment design (the point of the exercise)

10. **Split the base class the way Nautilus splits `Actor`/`Strategy`.** Give LLM-authored code the *Actor-shaped* half: data subscriptions, timers, cache reads, indicator reads, logging — and **no order methods at all**. Let it emit intents. Ref: <https://nautilustrader.io/docs/latest/concepts/actors>.

11. **Make the intent a typed object, per LEAN's `Insight` → `PortfolioTarget`.** An LLM-authored alpha returns `Signal(instrument, direction, confidence, horizon)`. A *human-owned, non-LLM* sizing module turns signals into targets, a *human-owned* risk module clamps them, and a *human-owned* execution module places orders. The LLM cannot size a position because it never holds a quantity. This is the strongest single idea in this document. Ref: <https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/overview>.

12. **Load strategies like LEAN's `Loader`, not like an import.** Discover exactly one class implementing the strategy interface; instantiate under a wall-clock timeout and a memory cap; wrap it behind the interface; treat a crash as recoverable. Quote to keep in the design doc: *"Loader creates and manages the memory and exception space of the algorithm, ensuring if it explodes the Lean Engine is intact."* Ref: `AlgorithmFactory/Loader.cs`.

13. **Enforce a per-strategy time budget in the run loop**, not only at load (LEAN has `AlgorithmTimeLimitManager`). An LLM-authored `on_bar` that loops forever must be killed by the engine, not by the operator.

14. **Adopt Condor's guardrail rule verbatim as QMF policy:** the agent may propose configuration; safety limits are user-only and never agent-writable. Also adopt its layering: reasoning is probabilistic and offline-ish; execution is deterministic and owns stop-losses/take-profits so they do not depend on model latency. Ref: <https://hummingbot.org/blog/introducing-condor-the-open-source-harness-for-trading-agents/>.

15. **Give the agent a tool schema, not a Python file, wherever possible.** Condor uses MCP tools against a fixed API. A generated-code path should be the *narrower* of the two options, not the default — and generated code should be authored against a stub/typed surface small enough to fit in a prompt.

16. **Frozen typed config objects for every strategy** (Nautilus `StrategyConfig`, hummingbot's Pydantic `StrategyV2ConfigBase`). Two wins: the LLM fills a schema instead of inventing parameters, and the config is the audit record of what ran.

17. **A pre-trade gate between intent and venue.** Nautilus has `RiskEngine`; hummingbot has `budget_checker.adjust_candidates(proposal, all_or_none=True)`. QMF must have exactly one such choke point, and every order must pass through it — including orders from human-written strategies.

18. **`register_indicator_for_bars`-style indicator wiring.** The strategy declares which indicator follows which bar type; the engine updates it. The strategy never calls `.update()`. Removes an entire family of LLM lookahead/staleness bugs. Ref: <https://nautilustrader.io/docs/latest/concepts/strategies>.

19. **Indicator warm-up as a first-class engine concern**, per LEAN (`warm_up_indicator`, `AutomaticIndicatorWarmUp`, `indicators_initialized()` in Nautilus). Never let a strategy trade on a half-warm indicator; make that structurally impossible.

20. **Docker image as the reproducibility unit** (LEAN CLI). Windows dev box, Linux VPS deploy — the *only* reliable way to keep those identical is an image, not a lockfile.

21. **A `strategies/` drop-in directory outside the framework package** (hummingbot's `scripts/`). It keeps generated code physically separable, easy to diff, easy to quarantine, and easy to delete.

### Avoid

22. **Do not build on backtrader.** Unmaintained since 2023-04-19; GPL-3.0; metaclass `lines` magic defeats type checkers and confuses code-generating models; `__init__`-vs-`next()` operator semantics are a trap.

23. **Do not let the strategy base class become the platform.** LEAN's `QCAlgorithm` spans `QCAlgorithm.cs`, `.Trading`, `.Indicators`, `.History`, `.Universe`, `.Plotting`, `.Framework`, `.Framework.Python`, `.Python`. It is a fine deal for humans with docs and search; it is a poor deal for an LLM that must hold the surface in context. **Target: the entire QMF strategy API should fit on one printed page.** backtesting.py (`init`, `next`, `I`, `buy`, `sell`, `position`, `data`) is the size to aim at.

24. **Do not link AGPL or Commons-Clause code into QMF.** backtesting.py is AGPL-3.0; vectorbt is Apache-2.0 **plus Commons Clause** ("you may not sell products or services that are primarily this software"). Even LGPL-3.0 (NautilusTrader) imposes relinking/notice obligations if distributed. If QMX may ever be commercial or network-served, the safe pool is Apache-2.0 (LEAN, hummingbot) plus original code.

25. **Do not adopt NautilusTrader as a dependency this quarter.** It is at v2.0.0rc3 with a documented, sweeping rename list and stated feature gaps (no v2 catalog/streaming backtest iteration, incomplete Postgres persistence). Adopting it now means inheriting a migration. Copy the architecture; defer the dependency decision until 2.0 stable with formal deprecations lands (per `ROADMAP.md`).

26. **Do not build the live engine on a vectorised model.** vectorbt's array-at-once design cannot express order lifecycle, partial fills, or reconciliation after a VPS restart. Keep vectorisation confined to a *research* surface, and never let a research-only result be the thing that goes live.

27. **Do not let a strategy own the event loop, network access, filesystem, or clock.** Nautilus injects a clock and cache; LEAN mutes strategy stdout and caps its resources. An LLM-authored strategy calling `requests.get` or `time.sleep` in `on_bar` must fail at review, and ideally at import.

28. **Do not accept "the strategy places the order" as the default shape for agent-authored code.** Both LEAN (Insight/PortfolioTarget) and hummingbot V2 (executor actions) moved away from it deliberately. QMF should start where they ended up.

29. **Do not plan on inheriting a cTrader adapter.** No project surveyed has one. Budget for building and testing cTrader Open API data + execution + history against the QMF adapter contract, and treat that adapter as the riskiest single component in v1.

30. **Do not build a UI/dashboard into the framework.** NautilusTrader explicitly rules it out of scope as an unsustainable maintenance burden for a small team (`ROADMAP.md`). A solo operator has strictly less bandwidth than they do.

---

## Open questions

**Needs an operator decision**

1. **Licence posture for QMX.** Is QMX ever sold, offered as a service, or distributed? The answer decides whether LGPL-3.0 (Nautilus), AGPL-3.0 (backtesting.py) and Commons Clause (vectorbt) are usable at all. Until answered, default to Apache-2.0-only dependencies plus original code.
2. **Build vs. adopt for the engine.** Three coherent options: (a) write QMF's engine, borrowing shapes only; (b) build QMF as a thin opinionated layer *over* NautilusTrader v2 once stable, inheriting 19 adapters and a Rust core but also LGPL and their release cadence; (c) LEAN + LEAN CLI, inheriting the best containment story but a C#/Docker operational surface a non-technical operator must maintain. This document leans (a) for v1 with (b) reconsidered after Nautilus 2.0 stable.
3. **How much autonomy does the LLM get?** Condor's shipped answer — agent proposes, user approves, safety limits are user-only — is a defensible default. Confirm that QMX adopts it, and specifically confirm whether an agent may ever deploy a strategy to live without a human click.
4. **Generated code vs. tool calls.** Does the LLM author Python strategy classes, or fill a constrained schema (parameters over a fixed library of vetted strategy templates)? The schema route is dramatically safer and is what Condor chose; the code route is more expressive. This shapes the entire strategy API.
5. **Backtest fidelity target for forex.** Bar-close only (cheap, backtesting.py-grade) vs. quote/tick-level with spread and slippage modelling (Nautilus-grade). This determines the data storage and cost budget before any code is written.

**Needs further research (candidates for sibling briefs)**

6. **cTrader Open API**: protocol shape (protobuf over TCP/WebSocket), symbol/instrument metadata, historical bar limits, rate limits, order types supported, reconciliation-after-restart semantics, and Python client maturity. Nothing in this survey covers it.
7. **NautilusTrader v2.0 stable date and API-freeze commitment.** `ROADMAP.md` promises formal deprecations at 2.0 but gives no date. Worth watching `version.json` and `RELEASES.md` monthly.
8. **backtrader2 fork status** — referenced from backtrader commit messages; current maintenance state UNVERIFIED here. Low priority (backtrader should be avoided regardless), but relevant if any existing QMX code touches it.
9. **Condor's licence and whether its MCP tool schema is reusable** as a reference for QMF's agent surface. README lists no licence — UNVERIFIED.
10. **LEAN's `Isolator` implementation details** (how the RAM cap is enforced cross-platform, and whether that technique transfers to a pure-Python engine on Linux — likely `resource.setrlimit` + a watchdog thread, but this was not verified from source).
11. **Vectorbt PRO vs OSS feature delta**, if the research surface is ever built on vectorbt. The OSS 1.x line is healthier than its reputation, but PRO-only features are the upsell and were not enumerated here.
12. **Whether any framework's backtest engine models forex-specific mechanics well** — swap/rollover, weekend gaps, variable spread, partial-lot rounding, and margin/leverage per instrument. Nautilus models accounts/margin (`crates/portfolio`, `accounting`) but the forex specifics were not verified in this pass.
