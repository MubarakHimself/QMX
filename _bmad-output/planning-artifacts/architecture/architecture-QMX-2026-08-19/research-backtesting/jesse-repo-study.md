# Jesse Framework — Deep Repo Study (shape study for QMX)

Reference copy: `C:/Users/Mubarak/Desktop/QMX/workroom/reference/repos/jesse` (git history removed).
Version **3.0.6** (`setup.py:6`). License **MIT** (`LICENSE:1-3`, "Copyright (c) 2020 Jesse.Trade"). Author Saleh Mir. All cites are `path:line` relative to the repo root unless noted.

> One-line orientation: Jesse 3.x is a **crypto-only, web-app-first, candle-driven backtest/live-trade framework**. A FastAPI backend + prebuilt Vue/Nuxt static GUI drive it; the CLI only launches the server. Hot numeric paths (indicators, candle generation) are pushed into an external compiled Rust crate `jesse-rust`. It now ships Optuna+Ray optimization, Monte-Carlo, bootstrap significance testing, a light sklearn ML layer, and an MCP server.

---

## 1. Package layout & module responsibilities

Top-level (`setup.py`, root `ls`):
- `jesse/` the package; `tests/`, `utils/`, `docs-perf/`, `assets/`; `Dockerfile`, `requirements.txt`, `setup.py`, `README.md`, `LICENSE`, `AGENTS.md`, `conftest.py`. No `pyproject.toml` — packaging is legacy `setup.py` + `find_packages()`.

`jesse/` subpackages (from directory scan):
- `strategies/` — `Strategy.py` base class (1874 lines) + ~40 `TestNN/` regression strategies and `RealStrategyRegression*`.
- `modes/` — the run modes: `backtest_mode.py` (1523 lines), `optimize_mode/`, `monte_carlo_mode/`, `significance_test_mode/`, `import_candles_mode/`, plus `data_provider.py`, `utils.py`.
- `store/` — in-memory singleton state (`__init__.py` `StoreClass`) with `state_app/candles/orders/positions/closed_trades/exchanges/trades/tickers/orderbook/logs`.
- `services/` — broker, order_service, position_service, candle_service, metrics, report, charts, db, redis, web (FastAPI app pieces), logger, migrator, multiprocessing, validators, transformers, etc.
- `models/` — peewee ORM models (`Candle`, `Order`, `Position`, `ClosedTrade`, `Route`, `FuturesExchange`, `SpotExchange`, `Exchange`) plus session records (`BacktestSession`, `OptimizationSession`, `MonteCarloSession`, `SignificanceTestSession`, `AiModel`, `LiveSession`, …).
- `controllers/` — HTTP/API controllers, one per feature: `backtest_controller`, `optimization_controller`, `monte_carlo_controller`, `significance_test_controller`, `live_controller`, `candles_controller`, `ai_model_controller`, `auth_controller`, `websocket_controller`, `lsp_controller`, etc.
- `research/` — pure-function public API for notebooks/scripts (see §6).
- `routes/` — the `RouterClass` singleton (`__init__.py`).
- `indicators/` — **175** indicator modules (`ls indicators/*.py | wc -l`), most delegating to `jesse_rust`.
- `candle_pipelines/` — synthetic-candle transforms: `gaussian_noise.py`, `gaussian_resampler.py`, `moving_block_bootstrap.py`, `base_candles.py` (used by Monte-Carlo-on-candles).
- `mcp/` — MCP server (§9).
- `exchanges/` — only `sandbox/Sandbox.py` (the paper/backtest exchange driver); live-trade exchange drivers live in the closed-source `jesse-live` plugin.
- `static/` — compiled `_nuxt` SPA (the web dashboard).
- `libs/`, `factories/`, `repositories/`, `enums/`, `exceptions/`, `info.py`, `config.py`, `helpers.py`, `constants.py`.

CLI is deliberately tiny (`jesse/cli.py`): only `install-live` and `run` (`cli.py:23,36`). `run` boots the FastAPI server (`jesse/__init__.py:15` imports the cli; `__init__.py` defines `lifespan`, `index`, FastAPI app). **There is no `jesse backtest` / `jesse optimize` CLI in 3.x** — those run through the web API / controllers / MCP, or the `research` functions in Python.

---

## 2. Strategy base class API (`strategies/Strategy.py`)

`class Strategy(ABC)` (`:49`). Instances get identity/config attrs (`name/symbol/exchange/timeframe/hp`) set by the router post-init (`:54-62`).

### Required (abstract) hooks
- `@abstractmethod should_long() -> bool` (`:861-863`)
- `@abstractmethod go_long() -> None` (`:812-814`)

### Optional decision hooks (default no-op / False)
- `should_short()` (`:865-866`), `go_short()` (`:816-817`), `should_cancel_entry()` (`:868-873`).
- `update_position()` (`:1050`) — user overrides to manage an open position each candle.
- `before()` (`:875-879`) and `after()` (`:881-885`) — run at the start/end of every execution.
- `filters()` (`:602-603`, returns `list`) — list of bound methods each returning bool; ALL must pass before an entry is submitted (`_execute_filters` `:786-810`, called inside `_execute_long/_execute_short`).
- `hyperparameters()` (`:605-606`, returns `list`) — list of dicts `{name, type('int'|'float'|'categorical'), min, max, default, options?, step?}`. Injected into `self.hp` in `_init_objects` when unset: `self.hp[dna['name']] = dna['default']` (`:476-479`).
- `dna()` (`:608-609`, returns `str`) — encoded hyperparameter string, decoded per-route in `_prepare_routes` (`backtest_mode.py:816`).
- `watch_list()` (`:1424`), `candles_pipeline()` (`:119`, hook returning an optional `BaseCandlesPipeline`).

### Position lifecycle callbacks (user-overridable, `on_*`)
`on_open_position(order)` (`:1203`), `on_close_position(order, closed_trade)` (`:1209`), `on_increased_position` (`:1242`), `on_reduced_position` (`:1262`), `on_cancel` (`:855`), `before_terminate`/`terminate` (`:1418/1421`). Cross-route variants: `on_route_open_position` / `_close` / `_increased` / `_reduced` / `_canceled` (`:1268-1306`) — how multi-symbol strategies react to each other.

### Order intent surface
User sets `self.buy` / `self.sell` / `self.stop_loss` / `self.take_profit` as `(qty, price)` tuples/lists inside `go_long`/`go_short`/`update_position`; each has a shadow `_x` copy so the engine diffs and re-submits when the user mutates them (`:71-82`, `_detect_and_handle_entry_and_exit_modifications` `:912-1048`). `liquidate()` (`:1685`) force-closes. Broker helpers via `self.broker`.

### Internal execution order (per candle)
`_execute()` (`:1308-1331`): `before()` → `_check()` → `after()` → (backtest only) `update_chart()` → clear caches → `index += 1`.
`_check()` (`:1061-1139`): cancel stale entries if `should_cancel_entry`; if position open → `_update_position()` (calls user `update_position`); `_simulate_market_order_execution()`; if flat and no entry orders → `_reset()`, evaluate `should_short()`/`should_long()` (mutually-exclusive guard `:1130`), then `_execute_long/_execute_short`. Spot cannot short (`:1122`).

### Data & metric accessors (properties)
`current_candle` (`:1439`), `open/close/high/low/volume/price` (`:1447-1511`), `candles` (`:1512-1519` → `candle_service.get_candles(exchange,symbol,timeframe)`), `metrics` (cached `metrics.trades(...)` `:1533-1542`), `balance/available_margin/leverage/fee_rate/position/is_long/is_short/is_open` etc. `portfolio_value` (`:1766`), `all_positions` (`:1759`), `daily_balances` (`:1839`).

### ML methods on the strategy (see §10)
`record_features(dict)` (`:122`), `record_label(name,value)` (`:143`), `export_ml_data()` (`:165`), `ml_features()` (`:265`), `ml_predict()` (`:299`), `ml_predict_proba()` (`:322`), `_load_ml_artifacts()` (`:235`). `ml_mode` attr defaults `'gather'` (`:96`).

### Chart annotation methods
`add_line_to_candle_chart` (`:371`), `add_horizontal_line_to_candle_chart` (`:401`), `add_extra_line_chart` (`:448`), `add_horizontal_line_to_extra_chart` (`:427`).

---

## 3. Multi-timeframe & multi-symbol mechanics

- **Routes** (`routes/__init__.py`, `RouterClass` singleton `router` `:159`). `initiate(routes, data_routes)` (`:18`). Each *trading* route = `{exchange, symbol, timeframe, strategy}` (`set_routes` `:81-108`). Each *data* route = `{exchange, symbol, timeframe}` with no strategy (`set_data_routes` `:110-113`) — this is the extra-candles feed for MTF/multi-symbol without trading it.
- Validation: each exchange-symbol pair traded **once** (`:29-41`); all trading routes must share the **same quote asset** (`:45-48`) so portfolio metrics are coherent.
- The router computes `considering_candles/exchanges/symbols/timeframes` unions and always injects `'1m'` into considering timeframes (`:69-79`). 1m is the mandatory base granularity.
- In-strategy access: `self.routes` / `self.data_routes` (`Strategy.py:1701-1709`), `self.get_candles(exchange, symbol, timeframe)` (`:1521-1531`) and `self.candles` (current route). `current_route_index` maps the running strategy to its route slot (`:1712-1721`).

---

## 4. Backtest engine internals (`modes/backtest_mode.py`)

- Entry: `simulator(..., fast_mode)` (`:529`) dispatches to `_step_simulator` (accurate, `:536`) or `_skip_simulator` (fast, `:1048`).
- **Candle-driven loop is 1-minute stepped.** `_step_simulator` builds `first_candles_set` from the reference pair, computes `length` in minutes (`:559`), prepares routes/pipelines (`_prepare_routes` `:776`), seeds initial daily balance, then `for i in range(length)` (`:644`):
  1. `store_app.time = first_candles_set[i,0] + 60_000` (`:646`).
  2. For each considering pair: take the `i`-th 1m candle (or synthetic candle from pipeline `:660`), gap-fix jumped candles (`_get_fixed_jumped_candle` / rust `fix_jumped_candles`), `add_candle(...,'1m')`, then `_simulate_price_change_effect(short_candle, exchange, symbol)` (`:680`) to fill orders inside that minute.
  3. Generate higher-timeframe candles from the last N 1m candles when `i_next % count == 0` (`:683-697`, via `candle_service.generate_candle_from_one_minutes`, rust-backed).
  4. For each trading route, call `strategy._execute()` on its timeframe boundary (1m every minute, else on modulo boundary) (`:706-716`); then `update_active_orders`.
  5. `execute_simulated_market_orders()` (`:720`); save daily portfolio balance every 1440 minutes (`:722`).
  - **Perf optimizations**: loop-invariant hoisting (`:574-595`); a "prefill" fast path that gap-fixes the whole 1m series once in Rust and bulk-copies into storage, then just bumps a storage index per minute when no pipeline is present (`:597-642`).
- **Order execution model** (`_simulate_price_change_effect` `:926-983`): finds orders whose price is inside the current 1m candle's range (`candle_includes_price`), `split_candle` at the order price, executes in sequence (`order_service.execute_order`), updating `position.current_price`. **No slippage model** — `grep -rln slippage` returns nothing across the whole package; limit/stop orders fill at their exact stated price, market orders at candle price. `_check_for_liquidations` (`:986-1018`) fires a market liquidation order at bankruptcy price when the candle crosses `liquidation_price` (isolated mode only, `:994`).
- **Fees**: single flat `fee` rate per exchange from config (`order_service.py:74-77,106-109`: `order.fee = fee_rate * notional`; `FuturesExchange.charge_fee` `:85-93`). No maker/taker split, no funding in backtest by default.
- **Leverage**: futures only; `futures_leverage` (int) + `futures_leverage_mode` `'cross'|'isolated'` (`FuturesExchange.py:18-34`, config `:36-38`). Available-margin math divides order notional by leverage (`FuturesExchange.py:115`). Spot leverage is always 1 (`Strategy.py:1723-1729`).
- **Warm-up candles**: `env.data.warmup_candles_num` (default **240** in `config.py:66`; code fallbacks reference 210/240). `load_candles` (`:449-492`) pulls `warmup_num` candles of the max timeframe before `start_date`; `_handle_warmup_candles` (`:495-527`) injects them into the store via `candle_service.inject_warmup_candles_to_store` so indicators are primed before trading begins. Missing warm-up raises a sync error with the earliest needed date (`_handle_sync_no_candles` `:274-299`).
- **State singletons** (`store/__init__.py`): `StoreClass` holds class-level `app/orders/closed_trades/logs/exchanges/candles/positions/tickers/trades/orderbooks`; `store.reset()` (`:29-40`) re-instantiates all of them per run. `store` is a process-global — this is why `research.backtest` uses `_isolated_backtest` to be pickle-safe for Ray/multiprocessing.

---

## 5. Optimize mode (`modes/optimize_mode/Optimize.py`, `fitness.py`)

- **Algorithm: Optuna (as study/trial store) + Ray (parallel evaluation) + a custom random sampler.** Imports `optuna` and `ray` (`Optimize.py:6-7`). `optuna.create_study(direction='maximize', storage=sqlite:///./storage/temp/optuna/optuna_study.db, load_if_exists=True)` (`:110-151`) — study persisted to SQLite; session-scoped `study_name` (`:114`). Ray is initialized with `cpu_cores` (`:154-161`); each trial is a `@ray.remote ray_evaluate_trial` task (`:23`) fed `ray.put()`-shared config/candles (`:481-504`).
- **Sampler is home-grown, not Optuna's TPE**: `_generate_trial_params` (`:226-259`) draws each hp with `np.random` respecting int/float/categorical + optional `step`, from the strategy's `hyperparameters()` space. Optuna trials are then reconstructed after the fact via `_create_optuna_trial` + `optuna.create_trial` / `study.add_trial` (`:261-333`) purely for persistence/analysis. So Optuna here is a results ledger + resumability layer, not the search driver.
- **Objective/fitness** (`fitness.py:get_fitness` `:23`): runs an isolated backtest on the **training** split; requires `>5` trades else score `0.0001` (`:46,104`); `objective_function` (config `env.optimization.objective_function`, default `'sharpe'`) selects the ratio — supported: sharpe, calmar, sortino, omega, serenity, smart sharpe, smart sortino (`:52-77`); score = `total_effect_rate * ratio_normalized` where `total_effect_rate = log10(total)/log10(optimal_total)` capped at 1 (`:47-48,97`). Negative ratio → unusable (`:80-83`). Then runs a **testing** split backtest (`:86-94`) for train/test (walk-forward-style) reporting. `_update_best_candidates` keeps `best_candidates_count` (default 20) tracking train/test metric (`:407-445`, config `:54-55`). Default `trials` = 200 (`config.py:53`).
- Termination watched via `timeloop` polling session status in the DB (`:163-174`).

---

## 6. Research module / Jupyter API (`jesse/research/`)

Pure-function public API re-exported in `research/__init__.py`:
- `backtest(config, routes, data_routes, candles, warmup_candles=None, ...)` (`backtest.py:15-82`) → wraps `_isolated_backtest` (`:85`). "Isolated / pure function … can be used in Python's multiprocessing without worrying about pickling issues" (`:34-36`). Flags: `generate_equity_curve`, `generate_charts`, `generate_csv/json/logs`, `generate_hyperparameters`, `benchmark`, `fast_mode`, custom `candles_pipeline_class`. `config` shape is documented inline (`:38-47`): `starting_balance, fee, type, futures_leverage, futures_leverage_mode, exchange, warm_up_candles`. Candles are `{ 'Exchange-SYM-QUOTE': {exchange, symbol, candles: np.ndarray} }` (`:55-62`).
- `get_candles / store_candles / fake_candle / fake_range_candles / candles_from_close_prices` (`research/candles.py`).
- `import_candles(...)` (`research/import_candles.py`).
- `monte_carlo_trades`, `monte_carlo_candles` (§8).
- `rule_significance_test`, `plot_significance_test` (§8).
- `optimize`, `print_optimize_summary` (`research/optimize/__init__.py:71,325`).
- ML: `gather_ml_data, train_model, load_ml_data_csv, load_ml_model` (§10).

These functions are the "notebook/scripting" surface; there is no Jesse-specific Jupyter kernel — it's ordinary importable Python returning dicts/np arrays.

---

## 7. Charts & report output

- **Metrics JSON** (`services/metrics.py`): `trades(closed_trades, daily_balance, final)` returns a flat dict — keys include `total, total_winning_trades, total_losing_trades, starting_balance, finishing_balance, win_rate, ratio_avg_win_loss, longs/shorts_count+percentage, fee, net_profit, net_profit_percentage, average_win/loss, expectancy(_percentage), average_holding_period, gross_profit/loss, max_drawdown, max_underwater_period, annual_return, sharpe_ratio, calmar_ratio, sortino_ratio, omega_ratio, serenity_index, total_open_trades, open_pl, winning/losing_streak, largest_winning/losing_trade, current_streak, avg_trades_per_day/week/month` (`metrics.py:410-453`). Empty result short-circuits to `{'total':0,'win_rate':0,'net_profit_percentage':0}` (`:311`).
- **Report** (`services/report.py`): `positions()` (`:17`), `candles()` (`:43`, returns last candle per route as `{time,open,close,high,low,volume}` with `time` in seconds), `livetrade()` (`:78`) — these feed the web dashboard/live view as JSON.
- **Charts** (`services/charts.py`): matplotlib with `Agg` backend (`:10-11`) → **PNG files**. Backtest chart set = `equity_curve, cumulative_returns, drawdown, underwater, monthly_heatmap, monthly_distribution, trade_pnl` (`:17`), each saved `{session_id}_{name}.png` at dpi 130 (`:238,283,316,338,400,461,513`). Light/dark themes (`_apply_chart_theme` `:146`).
- **Equity curve as data**: `equity_curve(benchmark=False)` (`:547`) returns a list of series `{name, color, data:[{time,value}]}` computed from `store.app.daily_balance` (`_calculate_equity_curve` `:517`), with optional per-symbol benchmark series (`:577`).

---

## 8. Monte Carlo & statistical significance (PRESENT)

- **Monte-Carlo — two flavors** (`research/monte_carlo/`):
  - `monte_carlo_trades` (`monte_carlo_trades.py:130`) — **trade-order shuffle test**: `random.shuffle` the realized trade PnLs, reconstruct equity curves, compute distribution of metrics (`_ray_run_scenario_monte_carlo:97`, seeded `:108`; `_reconstruct_equity_curve_from_trades:277`; `_calculate_confidence_intervals:367`; interpretation `:452`). Ray-parallel. Output types are richly typed (`ConfidenceIntervals`, `MetricPercentiles`, `MonteCarloTradesReturn` TypedDicts `:52-95`).
  - `monte_carlo_candles` (`monte_carlo_candles.py`) — re-runs the strategy on **synthetic candle series** produced by the `candle_pipelines/` transforms (`gaussian_noise`, `gaussian_resampler`, `moving_block_bootstrap`).
  - Backing controller/model: `controllers/monte_carlo_controller.py`, `models/MonteCarloSession.py`, `modes/monte_carlo_mode/`.
- **Rule significance testing** (`research/rule_significance_testing/`): `rule_significance_test(...)` (`rule_significance.py:40`) runs the strategy in a signal-only mode (`Strategy._execute_for_signal_test` `:1333`), collects per-bar log-returns, and does **bootstrap resampling** (`bootstrap.py:run_bootstrap_test:19`, `np.random.default_rng` per batch `:60`) to build a null sampling distribution of the mean; `p_value = mean(sim_means >= observed_mean)` (`rule_significance.py:215`), plus confidence output. Default 2000 resamples (`:84`). `plot_significance_test` renders it (`rule_significance_testing/plots.py`). Controller/model: `significance_test_controller.py`, `SignificanceTestSession.py`, `modes/significance_test_mode/`.

---

## 9. MCP server (PRESENT — `jesse/mcp/`)

- Built on the official `mcp` SDK (`mcp==1.28.1` in requirements) using **FastMCP**, `streamable-http` transport, `json_response=True` (`mcp/server.py:56`). Runs as a subprocess: `python -m jesse.mcp.server --port --api_url --password` (`server.py:11-52`); it is a **thin MCP wrapper that calls the Jesse HTTP API** (it holds `JESSE_API_URL`/`JESSE_PASSWORD`), intended for AI clients like Cursor (`server.py` docstring).
- Tool groups registered (`mcp/tools/__init__.py:35-79`): **strategy, backtest, config, candles, indicator, significance_test, monte_carlo, optimization**. E.g. `create_backtest_draft`, `run_backtest`, `get_backtest_session(s)`, `cancel_backtest` (`mcp/tools/backtest.py:42-511`).
- MCP **resources** are markdown docs served to the agent (`mcp/resources/*.md`: strategy, backtest_metrics, indicator, monte_carlo, significance_test, optimization, position_risk, configuration, charts, …). Also ships `agent_rules.md`, `usage_limits.py`/`USAGE_LIMITS.md`, `manager.py`.

---

## 10. ML / RL hooks

- **ML: PRESENT but light, sklearn-based supervised layer** (`research/ml.py`). `gather_ml_data` (`:52`) runs a backtest with the strategy in `ml_mode='gather'` collecting `record_features`/`record_label` points; `train_model` (`:141`) trains any sklearn estimator (`clone`, `StandardScaler`, `TimeSeriesSplit`, `cross_val_score`; SVC/SVR referenced) for `binary`/`multiclass`/`regression` tasks, computes feature importance via RFE + ANOVA F (`f_classif`/`f_regression`) + Spearman correlation (`:26-38,285`), and `joblib.dump`s `model.pkl`/`scaler.pkl`/`feature_importance.pkl` (`:362-364`). `load_ml_model(dir)` (`:444`) reloads them. Strategy-side: `record_features/record_label/export_ml_data/ml_features/ml_predict/ml_predict_proba` (§2). Models tracked in DB (`models/AiModel.py`, `controllers/ai_model_controller.py`). Deps: `scikit-learn`, `joblib`, `scipy`, `statsmodels` (requirements.txt).
- **RL: ABSENT.** No `gym`/`gymnasium`/`stable_baselines`/replay-buffer/policy-gradient imports anywhere (`grep -rn 'import gym|gymnasium|stable_baselines|ReplayBuffer' → empty`). (The only "PPO" hit is the Percentage Price Oscillator indicator.) No online-learning or agent-training loop; ML is offline supervised prediction feeding strategy signals.

---

## 11. Rust usage (`jesse-rust`)

- External **compiled crate pinned `jesse-rust==1.2.0`** (requirements.txt). Rust source is NOT in this repo (`find -name '*.rs' -o -name Cargo.toml` → empty); it's a pip-installed native extension (`setup.py` packages `*.so/*.dll/*.dylib`).
- Bound via plain `import jesse_rust` / `from jesse_rust import ...`. Which functions moved to Rust:
  - **Almost all indicators** — ~120+ of the 175 indicator modules import from `jesse_rust` (e.g. `ema`, `atr`, `adx`, `bollinger_bands`, `di`, `donchian`, `chop`, `cci`, `heikin_ashi`, `smma/shift/alligator`, `moving_std`, `*_last` variants) — the `_last` suffix functions return only the final value for live speed.
  - **Candle machinery**: `candle_from_one_minutes` (higher-timeframe generation) and `fix_jumped_candles` (`backtest_mode.py:30-31`, `candle_service.py:14`).
  - **Float-safe arithmetic**: `subtract_floats`, `sum_floats` in `helpers`/`utils.py:221,233`.
  - Futures math touches it too (`models/FuturesExchange.py:2 import jesse_rust as jr`).
- Python keeps the orchestration (loop, store, order lifecycle); Rust owns per-candle numeric kernels.

---

## 12. Data import, exchange drivers, storage

- **Crypto-only.** Candle-import drivers per exchange under `modes/import_candles_mode/drivers/`: **Apex, Binance, Bitfinex, Bybit, Coinbase, Gate, Hyperliquid, Kraken, KuCoin, Lighter**, each with spot/perpetual/testnet variants + `interface.py`. These are **hand-written REST drivers, not ccxt** (no ccxt dependency). Public entry `research.import_candles`.
- **Candle storage = PostgreSQL** via peewee. `services/db.py` opens a `playhouse.postgres_ext.PostgresqlExtDatabase` (`:3,19-44`) — "the shared PostgreSQL connection used by Jesse's models and services." `models/Candle.py`: `class Candle(peewee.Model)` with UUID PK, `open/close/high/low/volume` FloatFields, `exchange/symbol/timeframe` CharFields, composite indexes (`:11-30`). **Redis** (`aioredis`/`redis`) is used for pub/sub + caching (`services/redis.py`), not primary candle storage. Local caching driver default `'pickle'` (`config.py:11-13`).
- In-backtest candles are `np.ndarray` of shape `(n,6)`: `[timestamp_ms, open, close, high, low, volume]` (note **open, close, high, low** ordering — see `report.candles` `:64-68` and `current_candle` usage).

---

## 13. Config / env model

- **Runtime config** is a single nested dict `config` in `jesse/config.py:8-103`, mutated per mode. Sections: `env.caching`, `env.logging` (per-event booleans), `env.exchanges.<name>` (`fee, type('spot'|'futures'), futures_leverage_mode, futures_leverage, balance`), `env.optimization` (`objective_function='sharpe', trials=200, best_candidates_count=20`), `env.data` (`warmup_candles_num=240, generate_candles_from_1m=False, persistency=True`), and `app.*` runtime placeholders (considering/trading symbols/timeframes/exchanges, `trading_mode ∈ {backtest,livetrade,fitness}`, `debug_mode`, `is_unit_testing`). Read via `jh.get_config('env.x.y', default)`.
- **Infra env** from a `.env` file (`services/env.py`, `JESSE_ENV_FILE` override, `python-dotenv`): `POSTGRES_HOST/NAME/PORT/USERNAME/PASSWORD` (defaults `127.0.0.1/jesse_db/5432/jesse_user/password`), `REDIS_HOST/PORT/DB/PASSWORD` (`env.py:12-27`). No `.env.example` shipped in the copy.

---

## 14. Python version & key dependencies

- `python_requires='>=3.10'` (`setup.py:39`).
- Core deps (`requirements.txt`): `numpy~=1.26.4`, `pandas~=2.2.3`, `scipy~=1.15.0`, `statsmodels~=0.14.4`, `peewee~=3.14.8` + `psycopg2-binary~=2.9.9` (Postgres), `arrow`, `click~=8.0.3`, `pydash`, `fnc`, `requests`, `tabulate`, `timeloop`, `websocket-client`/`websockets`, `wsaccel`, `simplejson`, `redis~=4.1.4`/`aioredis~=1.3.1`, `fastapi~=0.128.0` + `uvicorn~=0.40.0` (web server), `python-dotenv`, `aiofiles`, `PyJWT`/`cryptography`/`ecdsa`/`eth-account`/`starkbank-ecdsa` (auth/live signing), `msgpack`, `joblib`, `matplotlib~=3.10.3`, `scikit-learn` (1.7/1.8 by py-version). **Optimization/ML/AI stack**: `optuna~=4.2.0`, `ray`, `mcp==1.28.1`. **Native kernel**: `jesse-rust==1.2.0`. `pytest~=6.2.5` for tests.

---

## Architecture takeaways for QMX
1. **Web-app-first, not library-first** in 3.x: the CLI only boots FastAPI; all modes run through controllers/HTTP + a bundled SPA + optional MCP. The clean *scripting* seam is `jesse.research.*` pure functions (isolated, pickle-safe) — that's the surface to imitate if QMX wants embeddable backtesting.
2. **Global mutable singletons** (`store`, `router`, `config`) are the backbone; isolation for parallelism is bolted on via `_isolated_backtest` + Ray `ray.put`. A cleaner design would pass explicit context objects.
3. **1m-driven simulation** with higher timeframes generated on the fly; **no slippage model** and a **flat single-rate fee** — realism gaps QMX may need to close (maker/taker, funding, slippage, partial-fill microstructure).
4. Optuna is used as a **persistence/ledger** layer while search is a custom `np.random` sampler + Ray fan-out — a pattern, not best-practice Bayesian optimization; QMX could genuinely use Optuna's samplers.
5. Statistical rigor is already present: **bootstrap significance testing** (p-value on per-bar returns) and **two Monte-Carlo methods** (trade-shuffle + synthetic-candle). Strong prior art for QMX's backtesting-significance sitting.
6. **Rust kernels** for indicators + candle generation are the performance play; the crate is external/pinned, source not vendored.
7. Crypto-only, Postgres-backed candles, per-exchange bespoke REST drivers (no ccxt), Redis for pub/sub — a heavier infra footprint than a self-contained backtester.
