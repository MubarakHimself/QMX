# Spec — Research / Jupyter Surface

Reverse-engineering spec for QMX's research surface, derived from reading
QuantConnect Lean (Apache-2.0, C# engine + Python CLI) and Jesse (MIT, Python
v3.0.6). Mechanism understanding only — no third-party code is reused. All cites
are to the local read-only clones.

Clones referenced:
- Jesse: `C:/Users/Mubarak/Desktop/QMX/workroom/reference/repos/jesse`
- Lean CLI: `.../scratchpad/lean-cli`
- Lean engine (C#): `.../scratchpad/lean-engine`

---

## 1. Feature claim (verbatim, with URL)

### Jesse — "research" module
> "The 'research' module is a collection of Jesse's features (that you typically
> use via the GUI dashboard) made available via functions for research
> purposes."
>
> "You can use these functions in either your custom Python scripts, or in your
> Jupyter Notebooks for research purposes."

Source: https://docs.jesse.trade/docs/research.html (sidebar enumerates: Candles,
Indicators, Backtest, Monte Carlo, Optimization, Rule Significance Testing,
Machine Learning).

### Lean — Research Environment / QuantBook
> "Powerful notebooks attached to our massive data repository."
> "LEAN provides more than 100 pre-built technical indicators and candlestick
> patterns." The environment lets users "Request historical data," "Visualize
> data with charting libraries supported by Jupyter," and use a "File system
> that you can use in your notebook to save, read, and delete data" (Object
> Store).

Source: https://www.quantconnect.com/docs/v2/research-environment

### Lean CLI — local research
> "Starting local Jupyter Lab environments is a powerful feature of the Lean
> CLI."
> "These environments contain the same features as QuantConnect's research
> environment but run on your local machine."
> "When you run the Research Environment, the default data provider is your local
> machine."

Source: https://www.quantconnect.com/docs/v2/lean-cli/research

The shared marketed promise: **the same library that powers backtests is
callable interactively — for data pulls, indicators, exploratory analysis, and
programmatic re-runs — without the product GUI/cloud in the loop.**

---

## 2. Mechanism — how the code actually does it

### 2a. Lean — QuantBook is the algorithm engine, subclassed for a notebook

The load-bearing fact: the research surface is not a separate library. `QuantBook`
**is a `QCAlgorithm`** — the exact base class every Lean backtest/live algorithm
inherits.

`Research/QuantBook.cs:48`
```csharp
public class QuantBook : QCAlgorithm
```

Because of that inheritance, every method a quant uses in a notebook —
`AddEquity`, `AddCrypto`, `History`, `Indicator`, `Securities` — is the *same*
method the backtest uses. There is no parallel "research data path"; a notebook
is a live-instantiated algorithm object with the engine's real handlers wired up
but no trading loop running.

The constructor (`QuantBook.cs:91-226`) stands up the full engine spine:
- Detects whether it is running inside a Python notebook by probing for IPython
  in a static ctor (`:55-85`) — sets language to Python vs C#.
- Imports pandas and installs the pandas converter so results marshal to
  DataFrames (`:98`, `:117 SetPandasConverter()`).
- Builds `LeanEngineSystemHandlers` / `LeanEngineAlgorithmHandlers` with
  `researchMode: true` (`:125-128`).
- Wires a `HistoryProviderManager` (`:194-209`) — the identical history stack a
  backtest uses.
- Wires a `DataManager` over a **`NullDataFeed`** (`:184`) — i.e. no streaming
  feed/clock advances; data is pulled on demand by history requests rather than
  pushed by a simulation loop. This is the one structural difference from a
  running backtest.
- Initializes the `ObjectStore` with `AlgorithmMode.Research` (`:156-168`) — the
  notebook file system the marketing calls out.
- Sets `SetAlgorithmMode(AlgorithmMode.Research)` (`:219`).

Data flow for a history request:
`qb.History(symbols, 360, Resolution.Daily)` → inherited `QCAlgorithm.History`
→ `HistoryProviderManager` → zip data cache provider (`ZipDataCacheProvider`,
`:170`) reading the local data folder → results marshalled through the pandas
converter → **multi-index `pandas.DataFrame`** indexed by (Symbol, time). The
notebook template confirms the shape:

`Research/BasicQuantBookTemplate.ipynb` (cell-5)
```python
h1 = qb.History(qb.Securities.Keys, 360, Resolution.Daily)
h1.loc["SPY"]["close"].plot()
```

Research-only conveniences layered on top of the algorithm API:
- `Indicator(...)` overloads (`QuantBook.cs:550-687`) — run any indicator over
  history and return its full time series as a DataFrame (`.data_frame` in the
  template), rather than the single latest value a live algorithm sees.
- `GetFundamental(...)` (`:237-328`, now obsolete → `UniverseHistory`) and
  `UniverseHistory(...)` (`:747-802`) — historical universe/fundamental frames.
- `OptionHistory` / `FutureHistory` (`:357-534`) — contract-chain history.
- `GetPortfolioStatistics(dataFrame)` (`:802-864`) — feed an equity/benchmark
  DataFrame, get Sharpe, drawdown, alpha/beta, etc. computed by the engine's own
  `PortfolioStatistics` (`:841`). Lets a notebook score an arbitrary equity curve
  with the same statistics the backtest report uses.

**How the notebook binds to the C# engine (portability mechanism).**
`Research/start.py` sets the CoreCLR runtime for pythonnet, then
`from AlgorithmImports import *`, `Initializer.Start()`, and exposes an `api`
object:
```python
set_runtime(clr_loader.get_coreclr(runtime_config=... "QuantConnect.Lean.Launcher.runtimeconfig.json"))
from AlgorithmImports import *
Config.Reset(); Initializer.Start()
```
The notebook's first cell is `%run ../start.py` (template cell-2). So the Python
kernel is a thin shell over the compiled C# engine loaded in-process via
pythonnet. This is powerful but heavy: the notebook cannot run without the built
Lean assemblies + a CoreCLR runtimeconfig on disk.

**How Lean CLI ships this to a laptop.** `lean research <project>`
(`lean-cli/lean/commands/research.py:37-219`) does *not* run any of the above
directly — it launches a **Docker container** of the official research image:
- Builds a complete `lean_config` for the `backtesting` environment
  (`:112-141`).
- Default historical data provider is `Local` (`:40-43`); `--download-data`
  flips it to QuantConnect cloud (`:125-126`).
- Runs the research image, exposing container port 8888 → user's `--port`
  (`:175`), bind-mounts the project into `/…/Notebooks` (`:160-165`) and the
  config read-only (`:167-172`).
- Opens the browser when it sees `"is running at:"` in container output
  (`:33-34`, `:178-179`), and injects a CSP `frame-ancestors` header so
  notebooks can be embedded (`:186-187`).

So Lean's portability story is **Docker-first**. The readme
(`Research/readme.md`) documents a bare-metal path (pip install jupyterlab +
build Lean + `%run start.py`) but explicitly labels Docker "Recommended" and
flags the local path as fragile (`readme.md:101-108`: pythonnet/stubs path
issues on Windows).

### 2b. Jesse — research is pure functions over the same internal library

Jesse takes the opposite structural approach. `jesse/research/__init__.py` is a
flat namespace of **plain importable functions** that reach straight into the
same services the dashboard/CLI use, with no web server, DB-session, or
WebSocket in the call path:

`research/__init__.py`
```python
from .candles import get_candles, store_candles, fake_candle, fake_range_candles, candles_from_close_prices
from .backtest import backtest
from .monte_carlo import monte_carlo_trades, monte_carlo_candles
from .import_candles import import_candles
from .ml import gather_ml_data, train_model, load_ml_data_csv, load_ml_model
from .rule_significance_testing import rule_significance_test, plot_significance_test
from .optimize import optimize, print_optimize_summary
```

**`backtest()` — the isolated, pure engine entry.** `research/backtest.py:15-82`
is the canonical pattern. Its own docstring states the intent (`:34-36`):
> "An isolated backtest() function which is perfect for using in research, and AI
> training … Because of it being a pure function, it can be used in Python's
> multiprocessing without worrying about pickling issues."

Mechanism (`_isolated_backtest`, `:85-215`):
1. Force `trading_mode='backtest'` and inject a caller-supplied config via
   `set_config(_format_config(config))` (`:104-107`). `_format_config`
   (`:218-251`) translates the ergonomic research dict
   (`starting_balance/fee/type/exchange/futures_leverage…`) into Jesse's
   internal exchange config — i.e. the research function **materializes the same
   config the CLI consumes** (the wind-tunnel: change variables, same tunnel).
2. `router.initiate(routes, data_routes)` (`:110`) — routes are the strategy
   bindings `{exchange, strategy, symbol, timeframe}`.
3. `store.reset()`, init candle/exchange/order/position state (`:112-122`).
4. **Validates the caller passed 1-minute candles** (`:124-134`) — the engine's
   base resolution; higher timeframes are derived from 1m via the `timeframe`
   field on the route.
5. Optional warm-up candle injection (`:143-152`).
6. Runs the actual simulation via `simulator(...)` (`:155-168`) — the *same*
   backtest simulator the dashboard uses.
7. Returns a plain dict: always `metrics`, optionally `csv`, `json`,
   `equity_curve`, `hyperparameters`, `logs`, `charts_session_id`, and `trades`
   (`:183-209`).
8. **Resets config + store** so the process can run another backtest cleanly
   (`:212-213`) — this is what makes it safe to fan out.

Data structures (from `backtest.py` docstring `:38-62`): candles are passed as a
dict keyed `"<Exchange>-<SYMBOL>"` → `{exchange, symbol, candles: np.ndarray}`,
where each candle row is `[timestamp_ms, open, close, high, low, volume]`
(column order confirmed in `research/candles.py:52-63`).

**Candle access.** `research/candles.py`:
- `get_candles(...)` (`:8-23`) delegates to
  `candle_service.get_candles_from_db` (`services/candle_service.py:216`) — the
  same DB reader the engine uses — but **guards on being inside a Jesse project**
  (`:18-21`, requires a `.env` file). This is Jesse's portability limit: research
  functions assume a project dir + a populated SQLite/Postgres candle DB.
- `store_candles(...)` (`:26-66`) writes a 1m `np.ndarray` into that DB (validates
  1m spacing, `:45-50`) — the CSV-import path.
- `fake_candle` / `fake_range_candles` / `candles_from_close_prices`
  (`:69-88`) — synthetic candle generators for unit-style research with **no DB
  or network** (these are the only fully-portable candle helpers).

**`import_candles()`** (`research/import_candles.py:1-16`) wraps
`import_candles_mode.run(...)` — network fetch from an exchange driver into the
DB, headless (`running_via_dashboard=False`).

**Higher-order research functions all share the `backtest()` calling
convention** (`config, routes, data_routes, candles, warmup_candles, …`) and add
parallelism via **Ray**:
- `monte_carlo_trades(...)` (`monte_carlo/monte_carlo_trades.py:130`) — shuffles
  the realized trade order `num_scenarios=1000` times, reconstructs equity
  curves, returns confidence intervals. Spins up Ray with
  `cpu_cores = 80% of cores` by default (`common.py` DEFAULT_CPU_USAGE_RATIO).
- `monte_carlo_candles(...)` (`monte_carlo/monte_carlo_candles.py:103`) —
  re-runs the backtest against perturbed price paths via a pluggable
  `candles_pipeline_class` (`GaussianNoiseCandlesPipeline`,
  `MovingBlockBootstrapCandlesPipeline`, exported from `monte_carlo/__init__.py`).
- `optimize(...)` (`optimize/__init__.py:71`) — train/test split
  hyperparameter search. Docstring (`:80-84`): "A pure research function for
  running hyperparameter optimization without any dashboard, database, or
  WebSocket dependencies." Uses **Optuna** for sampling + **Ray** for parallel
  trials; objective ∈ {sharpe, calmar, sortino, omega}; returns ranked
  `best_trials` with train + test metrics and a DNA string.
- `rule_significance_test(...)`
  (`rule_significance_testing/rule_significance.py:40`) — bootstrap resampling
  (`n_simulations=2000`) to test whether a rule's edge is distinguishable from
  luck.
- ML: `gather_ml_data(...)` (`ml.py:52`) runs a backtest in "gather" mode and
  harvests `record_features({...})`/`record_label(name, value)` calls the
  strategy emits, writing a CSV; `train_model(...)` (`ml.py:141`),
  `load_ml_data_csv` (`:391`), `load_ml_model` (`:444`).

Jesse's mechanism summary: **the research module is the internal library with the
web/DB/WebSocket dependencies factored out of the hot path, exposed as
config-in/dict-out pure functions that are safe to `multiprocessing`/Ray
fan-out.**

---

## 3. Jesse vs Lean — which approach fits QMX and why

| Dimension | Lean (QuantBook) | Jesse (research funcs) | Fit for QMX |
|---|---|---|---|
| Structural model | Notebook object **is** the algorithm engine (`QuantBook : QCAlgorithm`) | Flat **pure functions** over the internal library | **Jesse.** QMX's research surface = importable pure functions over the QMF libraries the CLI already fronts. |
| Portability | Docker-first; bare-metal needs compiled C# + CoreCLR + pythonnet (fragile on Windows) | `pip`/`uv`-installable Python; synthetic helpers need no DB/net | **Jesse.** Matches "bare uv-installed package, no server, no Docker" requirement. |
| Parallel fan-out | Single in-process engine per kernel | `backtest()` is pure + store-resetting → Ray/`multiprocessing` safe | **Jesse.** Directly serves the 12–14 concurrent-task target. |
| Data coupling | History pulled through engine's `HistoryProvider` from local data folder | `get_candles` requires a project `.env` + populated DB; synthetic helpers don't | **Hybrid.** Adopt Jesse's function shape but remove the hard project/DB guard — QMX must let unsealed data load from a passed handle, not an implicit project dir. |
| Result parity | Same `History`/`Indicator`/statistics as backtest | Same `simulator`/`set_config` as CLI | **Both agree** — reuse one library, never a research-only reimplementation. This is the non-negotiable both projects prove. |
| Interactive data return | multi-index `pandas.DataFrame` | raw `np.ndarray` `[ts,o,c,h,l,v]` | **Lean's** DataFrame ergonomics for interactive/agent inspection; keep a typed/array fast path underneath. |
| Config as entry | Config dict → engine (`_format_config`) | Config dict → engine (`_format_config`) | **Both agree** — config-driven (operator's wind-tunnel). QMX research functions consume the same materialized Book/BMS config. |

**Verdict:** QMX takes **Jesse's architecture** (pure, importable,
fan-out-safe functions over the same library the CLI fronts) and **Lean's
interactive ergonomics** (pandas-DataFrame returns, an indicator-over-history
helper, a "score any equity curve" statistics function) — while fixing both
projects' portability defects: Lean's Docker/CoreCLR weight and Jesse's implicit
project-dir/DB coupling. QMX must run identically inside a sealed QMX sandbox and
on a bare laptop / plain VS Code after `uv pip install qmx`, with no server and
no Docker required.

---

## 4. QMX spec draft — requirements for QMX's research surface

Naming: **`qmx.research`** — a pure-function package over the QMF toolbox
(`qmf-core`, `qmf-data`, `qmf-indicators`, `qmf-structure`, `qmf-registry`,
`qmf-venue`, `qmf-risk`). It is the importable face of the same library the QMX
CLI fronts; it adds no engine of its own (mirrors Lean/Jesse's "one library"
law).

### R1 — Importable, server-free, Docker-free
- `from qmx import research` (or `import qmx.research as qr`) MUST work after a
  bare `uv pip install qmx` in any Python env — QMX sandbox, external laptop, or
  plain VS Code — with **no running QMX server, no daemon, no Docker, no browser,
  no notebook kernel required**. Notebook usage is one supported host, not a
  dependency.
- No function may require an implicit "project directory" or ambient `.env` to
  operate. (Fixes Jesse's `is_jesse_project()` guard,
  `research/candles.py:18-21.`) Data location, when needed, is passed explicitly
  or resolved from an explicit config handle.

### R2 — Config-driven, same tunnel as the CLI
- Research functions consume the **same materialized config** a Book/BMS
  produces (operator's wind-tunnel). Creating a Book/BMS materializes a config;
  `research.*` functions accept that config object/path as their first argument
  and change *variables*, never swap the engine. (Mirrors Jesse
  `_format_config`, `backtest.py:218-251`.)
- The function surface is config-in / typed-result-out. No hidden global state
  survives a call: every function MUST leave shared state clean so the next call
  (or a parallel worker) is unaffected (mirrors Jesse `reset_config()` +
  `store.reset()`, `backtest.py:212-213`).

### R3 — Day-one function set for a quant-agent
Minimum viable surface (names indicative), grouped:

Data:
- `history(config, instrument, timeframe, start, end, warmup=0) -> Frame` —
  read historical bars over the QMF data contract. MUST return both a typed
  array/records fast path and a pandas-DataFrame view for interactive/agent
  inspection (Lean's multi-index frame ergonomics; Jesse's `[ts,o,c,h,l,v]`
  array underneath).
- `store_bars(...)` / `import_bars(config, venue, instrument, start) -> summary`
  — write/ingest into the governed data store, headless (Jesse
  `store_candles`/`import_candles`). Subject to R7 governance.
- `synthetic_bars_from_closes(prices)`, `fake_bars(count)` — DB-free, network-
  free generators for tests and quick exploration (Jesse
  `candles_from_close_prices`, `fake_range_candles`, `candles.py:69-88`). These
  MUST work with zero data access.

Indicators:
- `indicator(config, spec, instrument, timeframe, window, start, end) -> Frame`
  — run any `qmf-indicators` indicator over history and return the **full time
  series** (not just the latest value), as a frame (Lean `Indicator(...)`,
  `QuantBook.cs:550-687`). Same indicator library the trading node uses.

Backtest + analysis:
- `backtest(config, routes, data_routes, bars, warmup=None, *, generate=...) -> Result`
  — the isolated, pure backtest (Jesse `backtest.py:15-82`). Pure and
  fan-out-safe by contract (R4).
- `portfolio_statistics(equity_curve, benchmark=None) -> stats` — score an
  arbitrary equity/benchmark series with QMX's own statistics (Lean
  `GetPortfolioStatistics`, `QuantBook.cs:802-864`).
- `monte_carlo_trades(...)`, `monte_carlo_paths(...)` — robustness via trade-
  shuffle and price-path perturbation with pluggable path pipelines (Jesse
  `monte_carlo_*`). Confidence intervals in the result.
- `optimize(config, routes, train_bars, test_bars, ...) -> ranked_trials` —
  train/test hyperparameter search with a declared objective; no dashboard/DB/
  socket in the path (Jesse `optimize/__init__.py:71`, docstring `:80-84`).
- `significance_test(...)` — bootstrap edge-vs-luck test (Jesse
  `rule_significance_test`).
- ML data/model helpers (`gather_ml_data`, `train_model`, load/save) — optional,
  behind an extra; MUST NOT be a core import dependency.

### R4 — Purity and concurrency (12–14 concurrent tasks)
- `backtest()` and every higher-order function built on it MUST be **pure**
  (deterministic given (config, data, seed)) and **process-safe** for
  `multiprocessing`/Ray-style fan-out without pickling hazards (Jesse's stated
  design goal, `backtest.py:34-36`).
- The surface MUST sustain the operator's **12–14 concurrent tasks** target.
  Parallelism primitives (worker count, seeds) are parameters with sane
  defaults, not global config. No function may assume it is the only one running
  in the process/host.

### R5 — QMF law compliance (result contract)
Every research result MUST honor QMF-core contracts:
- **Exact integer money** — monetary fields are integer minor units, never
  float. (Lean marshals decimals→double for pandas display,
  `QuantBook.cs:844-861`; QMX MUST keep the exact value authoritative and treat
  any float only as a display projection.)
- **UTC-nanosecond time** — all timestamps UTC-ns. (Jesse uses ms epochs,
  `candles.py:52-63`; QMX standardizes on UTC-ns per QMF law.)
- **Typed refusals** — invalid inputs (wrong bar resolution, empty routes,
  unknown objective, missing data) raise QMF typed refusals, not bare
  `ValueError`/`str`. (Jesse raises plain `ValueError`, `backtest.py:128-134`;
  QMX upgrades these to typed refusals.)
- **World-labeled results** — every result carries its `world` label ∈
  {live, replay, simulated}. Research/backtest outputs are `simulated`;
  history/data reads over recorded data are `replay`. The label is part of the
  returned record, never inferred by the caller. (No equivalent in either
  source — this is a QMX addition.)
- **Injected clock** — no research function reads the system clock; time comes
  from the config/data cursor (replay clock) or an injected clock, per the QMF
  composition-root rule. (Contrast Lean `QuantBook` ctor reading
  `DateTime.UtcNow`, `:103` — QMX MUST NOT.)

### R6 — Logged-then-ledgered results
- Per the operator model: results are **logged during** a research run and
  **saved at completion into a LEDGER** with an unbiased pass/fail end result.
  `research.*` functions MUST emit progress/log events during long runs (Jesse
  exposes `progress_callback`/`result_callback` on `monte_carlo_*`/`optimize`)
  and return a completion record suitable for ledger capture, carrying the
  world label (R5) and a deterministic result identity.

### R7 — Data governance across contexts (sealed vs unsealed)
- **Governed/sealed data stays in controlled rooms.** Inside a QMX sandbox,
  research functions may read sealed/governed datasets through the QMF data
  contract. On an external laptop / plain VS Code, the *same* function calls
  MUST resolve only **unsealed, split-governed** data; any attempt to reach
  sealed data outside a controlled room MUST produce a typed refusal, not a
  silent empty/partial result.
- Data access is mediated by the QMF data layer's permission/seam
  (`qmf-data`), analogous to Lean's `DataPermissionsManager`
  (`QuantBook.cs:154, 205`) — but enforced as a QMX governance boundary, not a
  billing gate.
- Synthetic/generator helpers (R3) are always available in every context, so a
  quant-agent on a bare laptop can always do methodology work without any
  governed data.

### R8 — MCP optional
- The research surface is plain Python importable functions. Any MCP exposure
  is an optional adapter layer over the same functions; MCP MUST NOT be required
  to use `qmx.research`.

### R9 — No third-party engine code
- QMX implements its own research surface over QMF. No Lean or Jesse code is
  vendored or copied; only the *mechanisms* above are reproduced.

---

## 5. Open questions

1. **Return type contract.** Adopt Lean-style multi-index pandas DataFrames as
   the interactive return, with a typed array/records fast path underneath — or
   make DataFrame an optional `.to_frame()` projection to keep pandas out of the
   core dependency set for bare-laptop installs? (Pandas is heavy; agents may
   prefer typed records.)
2. **Base resolution.** Both engines pin a base bar (Jesse: 1m, validated;
   Lean: `Resolution` enum). What is QMX's canonical base resolution and how are
   higher timeframes derived — engine-side aggregation like Jesse's route
   `timeframe`, or precomputed? Affects `history()`/`backtest()` input
   validation.
3. **Parallel backend.** Jesse standardizes on Ray for `monte_carlo`/`optimize`.
   Does QMX mandate a specific backend (Ray vs stdlib `multiprocessing` vs the
   factory's own concurrency), given the 12–14 task target and the "no server"
   constraint? Ray starts a local cluster — is that acceptable on a bare laptop?
4. **Config object identity.** What exactly does a materialized Book/BMS config
   look like as the first argument to `research.*` — a path, a typed object, or
   both? Needs to be pinned so the CLI and research surface share one schema.
5. **Ledger write path.** Do research functions write to the LEDGER directly, or
   only return a completion record that a caller/harness ledgers? (R6 assumes the
   latter for purity, but long unattended optimizations may need mid-run ledger
   checkpoints.)
6. **Sealed-data detection off-sandbox.** By what signal does `qmf-data` know it
   is "outside a controlled room" so R7's typed refusal fires — environment
   attestation, a config flag, a signed capability? Security-sensitive; must not
   be bypassable by copying a config file to a laptop.
7. **Optimization objectives + validation.** Jesse ships {sharpe, calmar,
   sortino, omega} with a train/test split. Which objectives are day-one for
   QMX, and is walk-forward/CV in scope for V1 or a later addition?
8. **ObjectStore analogue.** Lean markets a notebook file system (Object Store,
   `QuantBook.cs:156-168`). Does QMX expose a research-scoped, governed
   scratch/artifact store to quant-agents, and how does it interact with R7
   governance? (`COMP-OBJECT-STORAGE` exists in the QMF roster.)
