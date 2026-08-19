# Backtest Engines — Three Generations Compared

**Study date:** 2026-08-17. **Author:** code-study agent for QMF.
**Material:** local clones under `C:/Users/Mubarak/Desktop/QMX/reference/repos/`. All file citations below are relative to that root, e.g. `backtrader/backtrader/brokers/bbroker.py:687`.
**Subjects:** `backtrader` (2015 generation), `zipline-reloaded` (2012 Quantopian lineage, forked 2020), `rqalpha` (2016 Ricequant, still shipping).
**Cross-references:** `research/01-architecture-references.md` (NautilusTrader, LEAN, vectorbt, backtesting.py, hummingbot) and `research/00-qmf-synthesis-module-map.md` (the ring map).
**Licence posture up front:** backtrader is GPL-3.0 and rqalpha forbids commercial use by any organisation without Ricequant's authorisation. **Both are design-study only. No code from either may enter QMX.** zipline-reloaded is Apache-2.0 and is the only one of the three whose code could legally be adapted.

---

## In plain words

1. Three Python backtest engines, built roughly five years apart, all trying to answer the same question: *how do you replay history through a strategy honestly?*
2. All three landed on the same skeleton — a clock that emits events, a book of open orders, a thing that decides which orders fill, an accounting ledger, and a report at the end. That skeleton is not in dispute. QMF will have it too.
3. What they disagree about is **where the seams go**, and that is the whole lesson. backtrader put the seam in the wrong place, zipline put it in a place that only works for US stocks, rqalpha put it in the right place and then filled it with Chinese market rules.
4. **backtrader's real gift** is that it will not let your strategy trade until every indicator it depends on has enough history. It works this out by itself, automatically, by walking the tree of indicators. That single feature prevents an entire family of silent, expensive bugs.
5. **backtrader's real sin** is cleverness. `a + b` means one thing when you write it in setup and a completely different thing when you write it inside the per-bar loop. A human learns this; a code-writing LLM will get it wrong forever.
6. **zipline's real gift** is that a computation can be labelled "safe to look back over" or "not safe", the label spreads automatically through anything built out of it, and building an unsafe combination is a hard error before any data is touched. That is a correctness property enforced by the type of the thing, not by discipline.
7. **zipline's real sin** is that its engine grew into its data store. It ships with about 28 hard dependencies including a *forked, resurrected* columnar file format, an HDF5 layer and a SQL database of stock identifiers. You cannot take the engine without taking the museum.
8. **rqalpha's real gift** is that almost everything is a plug-in — the broker, the clock, the fee model, the report — and the whole system is assembled at startup from a config file. Also: it carries **two clocks**, "what time is it on the wall" and "which trading day does this belong to", which is exactly the two-timestamp idea QMF arrived at independently.
9. **rqalpha's real sin** is that Chinese market structure is welded into the parts that should be neutral. The clock itself has 09:31 and 11:30 hard-coded in it.
10. None of the three models forex properly. None has variable spread, overnight swap as a first-class line, or a weekend gap. backtrader has an overnight *interest* hook that is the closest thing (`comminfo.py:258`) and it is the only forex-shaped affordance in all three engines.
11. Ageing verdict: backtrader is dead (last real commit April 2023) and was killed by its own metaclass magic — nobody could safely change it. zipline survives only because one person maintains a fork and keeps re-pinning numpy. rqalpha is alive and shipping monthly because its plug-in seam meant new features arrived as new modules, not as edits to old code.
12. The most useful thing in this whole comparison is not any one engine. It is that **each generation moved one more decision out of the engine and into a replaceable part**, and rqalpha moved the most. QMF should start where rqalpha ended up, and go one step further by making the simulator itself just another broker adapter.
13. Practical bottom line for QMX: build nothing that any of these three built. Borrow about a dozen *shapes* — listed in section 3 — and spend the saved time on the fill model, the financing line and the cTrader adapter, which none of them has.
14. Estimated honest cost of an industry-grade backtest capability for QMF, given the ring map already agreed: roughly 1,500 lines of new code across five small modules, plus a conformance test suite. Section 6 sequences it.

---

## How it is built

### 2.1 backtrader — the bar loop with an object graph over it

**Shape.** One package, 40-odd modules, no sub-packages for the engine itself: `cerebro.py` (1,716 lines) is the orchestrator, `brokers/bbroker.py` (1,237) is the simulator, everything else hangs off `lineiterator.py`/`linebuffer.py`.

**Event loop.** There are *four* loops, chosen at run time (`backtrader/cerebro.py:1291-1301`):

| Mode | Method | When used |
|---|---|---|
| `_runnext` | bar-by-bar, all objects step forward once per bar | live, replay, or `runonce=False` |
| `_runonce` | vectorised: every indicator computed over the full array first, then a fake per-bar walk | default backtest (`preload=True, runonce=True`) |
| `_runnext_old` / `_runonce_old` | legacy clock sync | `oldsync=True` |

`_runnext` (`cerebro.py:1494-1647`) is the interesting one. Per iteration it: notifies stores → notifies datas → advances every feed → picks `dt0 = min(datetimes)` and rewinds any feed that ran ahead → fires cheat-on-open timers → **`self._brokernotify()`** → fires normal timers → calls `strat._next()` for each strategy. Multi-timeframe is handled by sorting feeds by `(timeframe, compression)` and treating the finest as time master (`cerebro.py:1497-1499`).

The ordering is load-bearing and worth naming: **the broker matches orders *before* the strategy sees the new bar.** So an order placed on bar *N* is matched against bar *N+1*'s prices, which is the correct no-lookahead default.

**Order lifecycle and fills.** `BackBroker.next()` (`brokers/bbroker.py:1176`) is the pump: charge overnight interest → `_process_order_history` → drain the pending deque, calling `_try_exec(order)` on each → mark-to-market cash adjustment for futures → recompute account value. `_try_exec` (`bbroker.py:1040`) dispatches on `exectype` to six specialised matchers: `_try_exec_market`, `_try_exec_close`, `_try_exec_limit`, `_try_exec_stop`, `_try_exec_stoplimit`, `_try_exec_historical`. Each one reasons explicitly about gaps: for a buy stop, `popen >= pcreated` means "gapped through the trigger, fill at the open", `phigh >= pcreated` means "touched intrabar, fill at the trigger" (`bbroker.py:921-940`). That gap/touch distinction is the single most-copied piece of backtest logic in Python and it is correct.

**Slippage.** `_slip_up` / `_slip_down` (`bbroker.py:994-1039`). Percentage or fixed, applied to the reference price, then **clamped to the bar's high/low** — and, crucially, capable of **returning `None`, meaning "no price exists, do not fill"**. The `slip_match` / `slip_limit` / `slip_out` parameters let you choose between refusing, filling at the bar extreme, or filling at a price that never traded.

**Fill size.** Separate from slippage: `p.filler` (`fillers.py`) is a callable `(order, price, ago) -> size`. Three shipped: `FixedSize`, `FixedBarPerc` (a share of the bar's volume), `BarPointPerc` (distribute bar volume across the high-low range by tick, take a share of the price's slice). With no filler, orders fill entirely.

**Commission / financing.** `CommInfoBase` (`comminfo.py:30`) covers percentage vs fixed, stock-like vs futures-like, `mult` (contract multiplier), `margin`, `automargin`, `leverage`, and — the forex-relevant one — `get_credit_interest` / `_get_credit_interest` (`comminfo.py:258-303`), `days * rate * abs(size) * price`, with an `interest_long` flag so both sides can be charged. `cashadjust` (`comminfo.py:251`) implements daily futures mark-to-market. Note `_getcommission(size, price, pseudoexec)` (`comminfo.py:229`): the same function answers "what would this cost?" for sizing and "what did this cost?" for execution, distinguished by a flag.

**Accounting.** `_execute` (`bbroker.py:687-846`) is 160 lines doing position update, closed-vs-opened split, realised P&L, commission on each leg, leverage-adjusted cash, and a "not enough cash → nullify the opened part and margin-call the order" path. `Position.pseudoupdate` lets the broker ask "what would happen" without mutating.

**Warm-up — the best idea in the codebase.** `_minperiod` propagates automatically: a lines object takes the max of its datas' minperiods (`lineiterator.py:120-121`), then the max of its own lines' (`:134-135`), and a strategy takes the max over its indicators (`:174-176`). `_next` (`lineiterator.py:259-283`) then routes to `prenext()` while short, `nextstart()` exactly once at the boundary, and `next()` thereafter. **A strategy's `next()` is structurally incapable of running on a half-warm indicator.**

**One definition, two execution modes.** The same indicator class supplies `prenext/nextstart/next` (streaming) and `preonce/oncestart/once` (vectorised), and `_once` (`lineiterator.py:291-320`) drives the batch path with the same period arithmetic. This is exactly the "write it once in incremental form, replay for research" principle from `00-qmf-synthesis-module-map.md` §Ring 2 — already shipping in 2015.

**Multi-timeframe.** `resamplerfilter.py` (752 lines) has two classes. `Resampler` builds a larger bar from smaller ones and delivers it only when complete. `Replayer` (`resamplerfilter.py:563`) delivers the *partially formed* larger bar on every smaller tick — so a daily strategy can see the day forming. Replay disables preload and runonce (`cerebro.py:1066-1070`). This is the correct primitive for QMF's "M15 confluence evaluated on M1 ticks" case and neither zipline nor rqalpha has it.

**Extension points.** Analyzers (metrics), Observers (plottable state), Sizers (position sizing), Writers, Filters, Timers, Stores/Feeds/Brokers per venue. Analyzer (`analyzer.py:140-260`) receives the full lifecycle — `start/prenext/nextstart/next/stop` plus `notify_order/notify_trade/notify_cashvalue/notify_fund` — and returns whatever `get_analysis()` says.

**Why it aged the way it did.** Two causes, both visible in the source:

- *Metaclass depth.* `MetaBase` splits construction into `donew/dopreinit/doinit/dopostinit` (`metabase.py:66-100`); `MetaLineSeries`, `MetaLineIterator`, `MetaAnalyzer`, `MetaParams` each extend the chain and inject attributes (`analyzer.py:35-83` alone auto-creates `data`, `data0`, `data0_close`, `data_close`, … on every analyzer). Nothing here is visible to a type checker, an IDE, or a language model.
- *Operator overloading with phase-dependent meaning.* `LineRoot._operation` (`lineroot.py:83-94`) dispatches to `_operation_stage1` during `__init__` — returning a **new lines object** — or `_operation_stage2` during `next()` — returning a **float** (`lineroot.py:193-218`). Same `+`, two types, decided by when you wrote it. Python's `and`/`or` cannot be overloaded at all, which is why `bt.And`, `bt.Or`, `bt.If` exist.
- 169 `from __future__ import` statements survive across the package — the Python-2 compatibility layer was never removed.

The result: a design nobody could safely refactor, so nobody did. Last `master` commit 2023-04-19.

---

### 2.2 zipline-reloaded — a typed pipeline bolted to a session clock

**Shape.** `src/zipline/` with real sub-packages: `finance/` (blotter, slippage, commission, ledger, metrics, controls, execution), `data/` (portal, readers, bundles, fx), `gens/` (clock + simulation loop), `pipeline/` (a separate vectorised computation engine), `assets/` (a SQL database of instruments), `utils/`.

**Event loop.** Two objects, cleanly split.

`MinuteSimulationClock` (`zipline-reloaded/src/zipline/gens/sim_engine.pyx`) is a pure generator of `(timestamp, action)` pairs where action ∈ `{BAR, SESSION_START, SESSION_END, MINUTE_END, BEFORE_TRADING_START_BAR}`. It knows nothing about strategies, orders or data — only the exchange calendar. **The clock is a data structure, not a controller.**

`AlgorithmSimulator.transform()` (`gens/tradesimulation.py:99-256`) consumes it. Per `BAR`:

```
capital changes → set simulation_dt → blotter.get_transactions(current_data)
  → prune closed orders → metrics_tracker.process_transaction / process_order / process_commission
  → handle_data(algo, current_data, dt)   ← strategy runs LAST
  → collect blotter.new_orders → metrics_tracker.process_order
```

Same rule as backtrader: **orders from bar *N* are matched at the top of bar *N+1*, before the strategy is called.** `SESSION_START` handles splits and dividends; `SESSION_END` closes expired assets, runs the cancel policy, validates account controls and *yields a performance packet*. The loop is a **generator** — it yields one perf packet per period rather than accumulating state internally.

**Look-ahead containment.** `BarData` is constructed with a `simulation_dt_func` **callable**, not a timestamp (`gens/tradesimulation.py:88-95`, `src/zipline/_protocol.pyx:152-189`). The strategy holds a data object that can only ever answer questions about "now", where "now" is whatever the loop currently says. There is no API by which a strategy can name a future date. `_adjust_minutes` is a separate flag used only inside `before_trading_start` to shift the reference minute back.

**Order/fill simulation.** Three-layer separation:

- `ExecutionStyle` (`finance/execution.py`) — `MarketOrder`, `LimitOrder`, `StopOrder`, `StopLimitOrder`, each exposing only `get_limit_price(is_buy)` / `get_stop_price(is_buy)`. Order *intent* is a typed value object, not four booleans. Prices are run through `asymmetric_round_price` (`execution.py:171-205`), which rounds *in the trader's favour* to the instrument's tick size — a small piece of honesty most engines skip.
- `Blotter` (`finance/blotter/blotter.py:21`) — an ABC with `order / batch_order / cancel / cancel_all_orders_for_asset / reject / hold / process_splits / get_transactions / prune_orders`. `SimulationBlotter` is *one implementation*; the interface exists precisely so a live blotter can replace it. This is the closest any of the three gets to QMF's "the simulator is just another broker adapter".
- `SlippageModel` (`finance/slippage.py:81`) — the fill engine. `simulate(data, asset, orders_for_asset)` (`slippage.py:160-207`) resets `volume_for_bar`, checks bar volume, checks `order.check_triggers`, then calls the subclass's `process_order(data, order) -> (price, volume)` and creates a `Transaction`.

Four things about that contract are worth stealing:
- It returns **both a price and a size**, so partial fills are the default case, not a special case.
- It may raise `LiquidityExceeded` to say "stop processing this asset for this bar" (`slippage.py:44`).
- `volume_for_bar` is maintained *by the base class* across multiple orders on the same asset, so competing orders share one liquidity budget.
- `fill_price_worse_than_limit_price` (`slippage.py:47-77`) is a free function every model calls — **slippage may never push a fill through a limit price**. backtrader gets this partly wrong; rqalpha gets it wrong (see §4).

Shipped models: `NoSlippage`, `FixedSlippage` (half-spread), `VolumeShareSlippage` (impact = `volume_share² × price_impact × price`, `slippage.py:288-331`), `FixedBasisPointsSlippage` (default for equities), `VolatilityVolumeShare` (futures; impact from 20-day ADV and annualised volatility, `slippage.py:368-518`) with a documented fallback constant when history is missing (`NO_DATA_VOLATILITY_SLIPPAGE_IMPACT = 10bp`).

**Commission.** `CommissionModel.calculate(order, transaction) -> float` (`finance/commission.py:32`). The subtle part is `calculate_per_unit_commission` (`commission.py:106-143`): commission is computed **per order, not per fill**, so a minimum-per-trade charge is applied once and later fills top up the difference. Getting this wrong systematically overstates costs on partially-filled orders.

**Portfolio accounting.** `PositionTracker` + `Ledger` (`finance/ledger.py`). `Ledger` keeps an immutable `Portfolio`/`Account` behind a `MutableView` with a `_dirty_portfolio` flag (`ledger.py:344-404`) so the expensive recompute happens lazily and at most once per bar. `todays_returns` is computed **in returns space, not value space**, explicitly so that capital injections do not corrupt the series (`ledger.py:388-392`). `daily_returns_array` is a pre-allocated NaN array written by index — metrics read it directly rather than concatenating.

**Result objects — the strongest architecture in this file.** `finance/metrics/` is a **registry of metric sets** (`metrics/core.py`). Each metric is a small object implementing any subset of five hooks: `start_of_simulation`, `end_of_simulation`, `start_of_session`, `end_of_session`, `end_of_bar`. `MetricsTracker.__init__` (`metrics/tracker.py:122-141`) collects, per hook, every metric that implements it and builds one fan-out closure. The `default` set (`metrics/__init__.py:51-91`) is then a literal `set()` of ~30 tiny objects — `Returns()`, `PNL()`, `ReturnsStatistic(empyrical.sharpe_ratio, "sharpe")`, `DailyLedgerField("account.gross_leverage")`, … Adding a statistic is adding one object to a set. Swapping the whole reporting scheme is `register("my_metrics", fn)` plus a config string.

**Pipeline — a second engine.** `pipeline/` is a *vectorised, cross-sectional* computation DAG that runs alongside the event loop; `pipeline_output(name)` hands the strategy that day's row. Two ideas in it are directly relevant to QMF:

- **Terms are content-addressed.** `Term._static_identity(domain, dtype, missing_value, window_safe, ndim, params)` (`pipeline/term.py:255-267`) plus a cached `__new__` means two independently-constructed identical terms *are the same object*. Deduplication and DAG-sharing are free. This is QMF's `confluence_id = sha256(canonical_json(spec))` idea, implemented at the component level.
- **`window_safe` is a composing correctness flag.** A term is `window_safe` or not (`term.py:96`); composite terms compute theirs from their inputs (`pipeline/mixins.py:671-675`, `all(condition.window_safe, if_true.window_safe, if_false.window_safe)`); and using a non-window-safe term as the input to a windowed term raises `NonWindowSafeInput` — *"it's generally not safe to compose windowed functions on split/dividend adjusted data"* (`src/zipline/errors.py:495-503`). The check happens at graph construction, before any data is loaded.

Also `compute_extra_rows` (`term.py:328-355`): each term declares how much extra history it needs, the plan takes the max up the DAG, and the root mask is widened once (`pipeline/engine.py:388-395`). **Warm-up arithmetic propagating automatically through a composed graph** — the same idea backtrader has for indicators, generalised to a DAG.

**Bitemporality.** `DataPortal.get_adjusted_value(asset, field, dt, perspective_dt, ...)` (`data/data_portal.py:619-664`) — *"the value of `field` for `asset` at `dt` with any adjustments known by `perspective_dt` applied."* Two time axes, event time and knowledge time, in a 2013 codebase. Independent confirmation of the `Provenance` design.

**Trading controls.** `finance/controls.py` — `MaxOrderCount`, `MaxOrderSize`, `MaxPositionSize`, `LongOnly`, `RestrictedListOrder`, `AssetDateBounds`, plus account-level `MaxLeverage`/`MinLeverage`. Every control has `on_error ∈ {"fail", "log"}` (`controls.py:67-86`) and each is validated *exactly once per order* before submission. Account controls are validated at `SESSION_END` (`gens/tradesimulation.py:237`).

**Lifecycle-scoped API.** `utils/api_support.py` — `@api_method` exports a `QCAlgorithm`-style method into the module-level `zipline.api` namespace; `@require_not_initialized`, `@require_initialized`, and `@disallowed_in_before_trading_start` gate *when* a method may legally be called. `set_slippage`/`set_commission` are initialize-only, so the cost model cannot change mid-run.

**Why it aged the way it did.** Not the architecture — the substrate. 28 hard dependencies (`zipline-reloaded/pyproject.toml:37-67`) including `bcolz-zipline` (a *fork made to resurrect an abandoned columnar format*), `tables` (HDF5), `sqlalchemy>=2` + `alembic` (a migrating SQL asset database, `src/zipline/assets/asset_db_migrations.py`), `networkx`, `numexpr`, `patsy`, `statsmodels`, `six`. Plus Cython extensions (`_finance_ext.pyx`, `_protocol.pyx`, `_assets.pyx`, four more in `data/`). The engine cannot be lifted out of its data stack, and the maintenance work visible in the changelog is overwhelmingly "make it build against the new numpy/pandas". The domain model is US-equity-shaped too: `Equity`/`Future` are the asset types, slippage and commission models are keyed by `type(asset)` (`blotter/simulation_blotter.py:63-76`), and sessions come from `exchange_calendars`. A 24/5 forex instrument has no natural home.

---

### 2.3 rqalpha — everything is a mod

**Shape.** `rqalpha/core/` (event bus, executor, strategy, execution context), `rqalpha/model/` (Bar, Tick, Order, Trade, Instrument), `rqalpha/portfolio/` (Portfolio → Account → Position), `rqalpha/apis/` (the declared strategy surface), `rqalpha/interface.py` (769 lines of pure ABCs), and `rqalpha/mod/` — where the *actual engine lives*.

**The mod system is the architecture.** `ModHandler` (`rqalpha/rqalpha/mod/__init__.py:32-97`): read enabled mods from config → import each (`rqalpha.mod.rqalpha_mod_<name>` for system mods, `rqalpha_mod_<name>` for third-party) → merge each mod's `__config__` defaults under the user's overrides → **sort by `priority`** → `start_up(env, mod_config)` in order → `tear_down()` in *reverse* order, and **each teardown's return value becomes an entry in the run's result dict.** Seven system mods ship: `sys_accounts`, `sys_simulation`, `sys_risk`, `sys_analyser`, `sys_transaction_cost`, `sys_scheduler`, `sys_progress`. The simulator, the fee model, the risk gate and the report are all *plug-ins to their own framework*, on equal footing with anything a user writes.

**Event loop.** `AbstractEventSource.events(start, end, frequency)` is a generator (`interface.py:199-229`); `SimulationEventSource` supplies the backtest one and a live mod supplies the real one. `Executor.run` (`core/executor.py:37-99`) consumes it and does three things:

- Calls `_ensure_before_trading` to synthesise `BEFORE_TRADING` and `SETTLEMENT` events that the source did not emit, so day-boundary bookkeeping happens even if data is sparse.
- Calls `env.update_time(event.calendar_dt, event.trading_dt)` — **two clocks**. `calendar_dt` is wall time; `trading_dt` is which trading day the event belongs to. They differ for night sessions, where a 21:00 futures bar belongs to the *next* trading day.
- **Splits every event into three** via `EVENT_SPLIT_MAP` (`executor.py:84-99`): `BAR` becomes `PRE_BAR`, `BAR`, `POST_BAR`. Infrastructure subscribes to `PRE_`/`POST_`; the strategy sees only the middle one. So the matcher can update its state before the strategy runs and the analyser can record after, without either knowing the other exists.

`EventBus.publish_event` (`core/events.py:43-50`) keeps **two listener lists**: system listeners run first and **a system listener returning `True` stops propagation**; user listeners always run afterwards. A veto channel that user code cannot participate in.

**Order matching — a named template method with typed failure modes.** `BaseMatcher.match` (`mod/rqalpha_mod_sys_simulation/matcher/base.py`) documents its own seven steps and then executes them:

1. get the deal price;
2. validate limit-price crossing and limit-up/limit-down rules;
3. compute the liquidity-limited maximum fill;
4. for opening orders, reduce the fill to what available cash supports;
5. compute the close-today quantity;
6. create the `Trade` and publish `EVENT.TRADE`;
7. handle any unfilled remainder.

Failure is expressed as three exception types with distinct meanings (`matcher/base.py:26-38`): `OrderNotMatchable` → *order stays ACTIVE, try again next bar*; `OrderRejected` → *order goes REJECTED*; `OrderCancelled` → *order goes CANCELLED*. `match()` catches each and calls the matching `order.mark_*`. Subclasses (`DefaultBarMatcher`, `DefaultTickMatcher`, `CounterPartyOfferMatcher`, `SignalMatcher`) override only steps 1, 3 and 7.

Deal-price policy is itself a swap: `MATCHING_TYPE ∈ {CURRENT_BAR_CLOSE, NEXT_BAR_OPEN, VWAP, COUNTERPARTY_OFFER}` selects a decider function (`matcher/bar_matcher.py:20-49`). `CURRENT_BAR_CLOSE` sets `_match_immediately = True` in the broker (`simulation_broker.py:44`), so orders match inside the same bar — an explicit, named, opt-in look-ahead.

**Broker.** `SimulationBroker` (`mod/rqalpha_mod_sys_simulation/simulation_broker.py`) implements `AbstractBroker` (`submit_order`, `cancel_order`, `get_open_orders` — `interface.py:578-616`) *and* `Persistable`. It subscribes itself to `BEFORE_TRADING`, `BAR`, `TICK`, `AFTER_TRADING`, `PRE_SETTLEMENT` and keeps three queues (regular, auction, exercise). Matchers are resolved **per instrument type** through an LRU cache (`simulation_broker.py:64-78`), so a futures matcher and a stock matcher coexist in one run. Every order transition publishes an event: `ORDER_PENDING_NEW`, `ORDER_CREATION_PASS`, `ORDER_CREATION_REJECT`, `ORDER_PENDING_CANCEL`, `ORDER_CANCELLATION_PASS`, `ORDER_UNSOLICITED_UPDATE`, `TRADE`. A live broker mod emits the *same* events, so downstream accounting and reporting are identical between backtest and live.

**Slippage.** `BaseSlippage.get_trade_price(order, price) -> float` (`mod/rqalpha_mod_sys_simulation/slippage.py:53`). Three models: `PriceRatioSlippage` (proportional, clamped to limit-up/limit-down), `TickSizeSlippage` (in ticks), and `LimitPriceSlippage` — *"use the limit order's own price as the fill price, to simulate the worst case"*. That last one is a genuinely good idea: a deliberately pessimistic model you can run as a sanity check. `SlippageDecider` (`slippage.py:35-51`) resolves the model **by dotted import path from config**, so a user model needs no registration call.

**Transaction cost.** The best-shaped cost interface of the three (`interface.py:736-769`):

```python
class TransactionCostArgs(NamedTuple):
    instrument, price, quantity, side, position_effect, order_id, close_today_quantity

class TransactionCost(NamedTuple):
    commission: float; tax: float; other_fees: float
    @property
    def total(self) -> float: ...
    @classmethod
    def zero(cls) -> "TransactionCost": ...

class AbstractTransactionCostDecider(ABC):
    def calc(self, args: TransactionCostArgs) -> TransactionCost: ...
```

Cost is a **structured value, not a scalar**, and deciders are registered per `(INSTRUMENT_TYPE, MARKET)` (`environment.py:187-201`). Adding a new asset class or a new venue's fee schedule is registering one object.

**Pre-trade gate.** `AbstractFrontendValidator` (`interface.py:711-733`) with `validate_submission(order, account) -> Optional[str]` and `validate_cancellation(...)`. **Returning a reason string means denial; returning `None` means pass.** `Environment.can_submit_order` (`environment.py:207-221`) chains instrument-type-specific validators with default ones and publishes `ORDER_CREATION_REJECT` carrying the reason. `sys_risk` supplies `cash_validator`, `price_validator`, `is_trading_validator`, `self_trade_validator`. Cancels go through a *separate* method, so a policy can freeze new orders while still permitting exits — exactly QMF's `TradingState.REDUCING`.

**Portfolio accounting.** `Portfolio → Account (per DEFAULT_ACCOUNT_TYPE) → Position (per (order_book_id, direction))`. The P&L decomposition is the notable part (`portfolio/position.py:126-158`):

- `position_pnl` = `logical_old_quantity × (last_price − prev_close) × direction` — mark-to-market on the position carried in from yesterday;
- `trading_pnl` = `(trade_quantity × last_price − trade_cost) × direction` — P&L on today's trades relative to the current price;
- `pnl` = `(last_price − avg_price) × quantity × direction` — lifetime.

Three questions, three fields, no ambiguity about which "P&L" a report means. `unit_net_value` / `units` (`portfolio/__init__.py:150-171`) express the account as a fund with a NAV per unit, so capital injections do not corrupt the return series — the same problem zipline solves differently.

**Restart and reconciliation.** `Persistable` (`interface.py:686-708`) is a protocol with `get_state() -> bytes` / `set_state(bytes)` and a `__subclasshook__`, so any component opts in structurally. `main.py:92` snapshots every mod implementing it. `AbstractPersistProvider` additionally answers `should_resume()` and `should_run_init()`. And `Account.fast_forward(orders, trades)` (`portfolio/account.py:155-174`) rebuilds account state by **replaying the venue's order and trade history**, deduplicating against `_backward_trade_set`, processing opens before closes. That is a working reconciliation-after-restart design.

**The strategy surface.** There is *no base class*. `Strategy.__init__` (`core/strategy.py:40-65`) pulls `init`, `handle_bar`, `handle_tick`, `before_trading`, `after_trading`, `open_auction` out of the loaded module's namespace and subscribes only the ones that exist. Each is wrapped in an `ExecutionContext(phase)` and a user-exception translator.

`ExecutionContext` (`core/execution_context.py`) is a context-manager stack of `EXECUTION_PHASE` values, and `@ExecutionContext.enforce_phase(*phases)` (`:102-114`) is applied to **35+ API functions** — calling `order_shares` from `before_trading` raises *"You cannot call order_shares when executing [日内交易前]"*. Phases: `GLOBAL`, `ON_INIT`, `BEFORE_TRADING`, `OPEN_AUCTION`, `ON_BAR`, `ON_TICK`, `AFTER_TRADING`, `SCHEDULED`, `FINALIZED` (`const.py:44-53`).

`apis/api_abstract.py` is the sharpest single file in all three repos. Each API function is **declared, not implemented**:

```python
@export_as_api
@ExecutionContext.enforce_phase(OPEN_AUCTION, ON_BAR, ON_TICK, SCHEDULED, GLOBAL)
@apply_rules(assure_that('id_or_ins').is_valid_order_book_id(),
             verify_that('amount').is_number(), *common_rules)
@instype_singledispatch
def order_shares(id_or_ins, amount, price_or_style=None, ...) -> Optional[Order]:
    """<docstring with examples>"""
    raise NotImplementedError
```

Signature + phase gate + argument validation + documentation in one place, body empty. Asset-class mods then register implementations by instrument type: `stock_order_shares = cast_singledispatch(order_shares).register(INST_TYPE_IN_STOCK_ACCOUNT)(stock_order_shares)` (`mod/rqalpha_mod_sys_accounts/api/api_stock.py:166`). **The surface an author sees is one file; what it does is somebody else's problem.** This is precisely the `qmf.spec` shape the ring map asks for, already built.

**Reporting.** `sys_analyser` (`mod/rqalpha_mod_sys_analyser/mod.py`, 752 lines) subscribes to `TRADE`, `ORDER_CREATION_PASS`, `POST_SETTLEMENT` and accumulates records; `tear_down` builds a dict of DataFrames (`portfolio`, `stock_account`, `stock_positions`, `trades`, `benchmark_portfolio`, `positions_weight`, `plots`, `pressure_test`) plus a flat `summary` dict of ~60 named statistics at daily/weekly/monthly frequency, then optionally pickles it, renders an xlsx and plots it.

**Why it aged the way it did — and why it is still alive.** Alive because the mod seam meant options, dividends, capital-gains tax, VWAP orders and partial fills all arrived as *new modules*, not as edits to a 1,700-line loop; CHANGELOG shows steady releases to 6.3.0. But it is not portable, because Chinese market structure is welded into neutral parts:

- `SimulationEventSource._get_stock_trading_minutes` hard-codes `09:31`, `11:30`, `13:01`, `15:00` (`mod/rqalpha_mod_sys_simulation/simulation_event_source.py:50-67`), and `_get_day_bar_dt` hard-codes 15:00 (`:36`);
- limit-up/limit-down checking is inside the generic matcher (`matcher/base.py`, `reaches_limit`);
- T+1 settlement appears as `closable` vs `today_closable` on the abstract `AbstractPosition` interface (`interface.py:107-121`);
- `close_today_quantity` and `POSITION_EFFECT.CLOSE_TODAY` are in the *cost* interface (`interface.py:736-744`);
- `capital_gains_tax.py` sits in `portfolio/`.

The interfaces are excellent; the vocabulary is not neutral.

---

### 2.4 Comparative table

| | **backtrader** (2015) | **zipline-reloaded** (2012/2020) | **rqalpha** (2016) |
|---|---|---|---|
| Clock | inside `Cerebro`, four loop variants | separate generator, `(dt, action)` pairs | pluggable `AbstractEventSource` generator |
| Event vocabulary | implicit (method calls) | 5 actions | ~40 named events, each split PRE/·/POST |
| Two-timestamp support | no | yes, in the data portal (`perspective_dt`) | **yes, first-class** (`calendar_dt` / `trading_dt`) |
| Order match timing | broker before strategy, next bar | blotter before `handle_data`, next bar | configurable, incl. explicit same-bar mode |
| Fill contract | `_try_exec_*` per order type; filler for size | `process_order → (price, volume)` | 7-step template, 3 typed exceptions |
| Partial fills | via `filler` callable | native (`open_amount`) | native, incl. cash-limited partial |
| Slippage may refuse | yes (`_slip_*` returns `None`) | yes (`LiquidityExceeded`) | no |
| Slippage respects limit price | partially | **yes, enforced centrally** | **no — known defect, see §4** |
| Cost model shape | `CommInfoBase`, one float | `calculate(order, txn) -> float`, per-order minimum logic | `TransactionCost(commission, tax, other_fees)` NamedTuple |
| Financing / overnight | **yes** (`get_credit_interest`) | no | no (CN market has no retail swap) |
| Pre-trade gate | none (Sizer only) | `TradingControl` / `AccountControl` | `AbstractFrontendValidator` returning a **reason string** |
| Warm-up | **automatic `_minperiod` propagation** | `compute_extra_rows` in the Pipeline DAG | none (strategy's problem) |
| Multi-timeframe | **Resampler + Replayer** | one frequency per run | one frequency per run |
| Multi-asset | one `CommInfo` per feed | models keyed by `type(asset)` | deciders/matchers keyed by `(INSTRUMENT_TYPE, MARKET)` |
| Result object | Analyzer objects, `get_analysis()` dicts | **registered metric sets**, 5 hooks, perf packets | mod `tear_down()` returns a dict of DataFrames |
| Extension seam | subclass + metaclass | ABC + `@extensible` + registry | **mod system, config-assembled, priority-ordered** |
| Backtest↔live parity | separate broker classes, partial | `Blotter` ABC (live never shipped OSS) | same events, same accounting, broker swapped by mod |
| Restart / reconcile | no | no | **yes** (`Persistable` + `fast_forward`) |
| Author API surface | class + metaclass magic | 35 `@api_method`s | 35+ declared, phase-gated, singledispatched |
| Licence | GPL-3.0 | Apache-2.0 | Custom, non-commercial only |
| Last real activity | 2023-04-19 (`master`) | 2026-01-06 push | 2026-08-17 push |

---

## Mental models worth borrowing

### 1. Warm-up is an engine invariant, computed automatically, not a strategy responsibility

**Where it lives.** `backtrader/backtrader/lineiterator.py:120-135` (a lines object's `_minperiod` is the max over its inputs), `:174-176` (a strategy's is the max over its indicators), `:259-283` (`_next` routes to `prenext` / `nextstart` / `next`). Independently, zipline generalises the same idea to a DAG: `Term.compute_extra_rows` (`zipline-reloaded/src/zipline/pipeline/term.py:328-355`), max-propagated in `pipeline/engine.py:388-395`.

**Why it matters for QMF.** An LLM composing a `Confluence` out of a `Level`, a `Trigger` and three `Confirmation`s cannot be trusted to compute the combined warm-up — and the failure is silent: the first N trades of every backtest are made on garbage. The ring map already lists `warmup_bars` as a `ComponentDef` field; this makes it enforceable rather than declarative.

**How QMF implements it.** `ComponentDef.warmup_bars` is declared per component. `Confluence` resolution computes `warmup = max(component.warmup_bars) + max_bars_between_touch_and_trigger`. `qmf.runtime` refuses to dispatch `on_bar` to a confluence until `bars_seen > warmup`, and exposes a `pre_warm` hook for anything that needs to see the pre-warm bars. Making the warm path a *different method* rather than an `if` is the point: there is no branch an agent can forget.

### 2. A correctness property that composes automatically and is checked before any data is touched

**Where it lives.** zipline's `window_safe`: declared per term (`pipeline/term.py:96`), propagated through composites (`pipeline/mixins.py:671-675`), enforced as `NonWindowSafeInput` at graph construction (`src/zipline/errors.py:495-503`).

**Why it matters for QMF.** This is the general form of every rule in the ring map that is currently a doc paragraph: `causality ∈ {filtered, predicted}` must never be `smoothed` for a live component; `stability`/`path_dependent` must be visible; a component built out of a lookahead component is itself a lookahead component. zipline proves the pattern works: one boolean, one composition rule, one exception class, and the entire family of bugs is gone.

**How QMF implements it.** `ComponentDef` carries `causality` and `stability`. Composition rules are pure functions: a `Confluence`'s causality is the *worst* of its parts, its stability the *worst* of its parts. `qmf.registry.register()` evaluates them at registration and raises `CausalityViolation` — before a split is loaded, before budget is spent. The `smartmoneyconcepts` lookahead described in `00-qmf-synthesis-module-map.md` §Novel-1 becomes unregisterable rather than undetected.

### 3. The fill algorithm is a named, numbered pipeline whose failure modes are types

**Where it lives.** `rqalpha/rqalpha/mod/rqalpha_mod_sys_simulation/matcher/base.py` — `BaseMatcher.match` with its seven documented steps, and `OrderNotMatchable` (stay active) / `OrderRejected` / `OrderCancelled` as the three outcomes.

**Why it matters for QMF.** Fill simulation is where backtests lie, and it is the part a non-technical operator most needs to be able to read. A 160-line `_execute` (backtrader) cannot be audited; a seven-step list with named steps can. And the three exception types map one-to-one onto QMF's `outcome ∈ {ACCEPTED, REJECTED, DENIED_LOCALLY, UNKNOWN}` from `qmf.broker`, so simulated rejections and live rejections speak the same language.

**How QMF implements it.** `qmf.sim.FillModel.match(order, market_state) -> FillResult` implemented as a template method with named steps: *reference price → spread application → tradeability/session check → liquidity cap → slippage draw → limit-price clamp → cost application → fill or defer*. Failures raise the same `VenueRejection` subclasses the cTrader adapter raises, so the conformance suite (§Novel-2 of the ring map) tests both implementations with one set of assertions.

### 4. Cost is a structured value with named components, not a float

**Where it lives.** `rqalpha/rqalpha/interface.py:736-769` — `TransactionCost(commission, tax, other_fees)` with `.total` and `.zero()`, produced by `AbstractTransactionCostDecider.calc(TransactionCostArgs)`, deciders registered per `(INSTRUMENT_TYPE, MARKET)` (`rqalpha/rqalpha/environment.py:187-201`).

**Why it matters for QMF.** The ring map already commits to financing being a P&L line from day one (§Novel-8) because retrofitting it touches the ledger, every report and every stored result. The same argument applies to spread and slippage: if `cost` is one float, you can never later answer "how much of this strategy's decay is spread and how much is commission?" — which is exactly the question `10 §7.2`'s slippage-loop closure needs to answer.

**How QMF implements it.** `TradingCost(spread, commission, slippage, financing, other)` as a frozen dataclass with `.total`. `VenueModel.cost(CostArgs) -> TradingCost`, registered per `(asset_class, venue)`. The ledger stores all five columns. The metrics contract reports `edge_gross`, `edge_net` and the four deductions separately. Registration-time refusal of confluences whose edge is smaller than their spread (§Novel-3) then reads one field instead of re-deriving it.

### 5. Two clocks: wall time and business time

**Where it lives.** `rqalpha/rqalpha/environment.py:69-70, 203-205` (`calendar_dt`, `trading_dt`), set on every event by `Executor._split_and_publish` (`core/executor.py:93-99`). The reason is concrete: a 21:00 futures night-session bar is *wall-clock Monday* but *business-day Tuesday*. zipline's version is `get_adjusted_value(..., dt, perspective_dt, ...)` (`zipline-reloaded/src/zipline/data/data_portal.py:619-664`).

**Why it matters for QMF.** Four separate briefs invented the two-timestamp rule independently; here are two more prior-art implementations, one of them motivated by exactly QMX's problem shape. Forex has the same discontinuity: the 17:00 New York rollover, the Sunday open, and — critically — the prop-firm daily-loss anchor, which is a *business-day* boundary in a firm-specified timezone (`04` six-axis schema). Getting this wrong means a challenge fails on a technicality.

**How QMF implements it.** `qmf.core.Clock` exposes `wall_ts` (UTC nanoseconds) and `session_date` (the trading day this event belongs to, per the venue's session schedule). `Provenance` carries `ts_event` / `ts_init`. `qmf.bms`'s daily anchor reads `session_date`, never `wall_ts.date()`. One property test: for every event, `session_date` is derived only from `VenueModel.session_schedule` and `wall_ts` — never from local time.

### 6. Lifecycle phases gate the API, enforced by decorator

**Where it lives.** `rqalpha/rqalpha/core/execution_context.py:102-114` (`enforce_phase`), applied to 35+ functions in `rqalpha/apis/api_base.py` and `apis/api_abstract.py`; phases enumerated at `rqalpha/const.py:44-53`. zipline's narrower version: `@require_not_initialized` / `@require_initialized` / `@disallowed_in_before_trading_start` (`zipline-reloaded/src/zipline/utils/api_support.py:63-140`), which is why `set_slippage` cannot be called mid-run.

**Why it matters for QMF.** "What may I call, and when?" is half the surface area an LLM has to hold in context, and it is the half that is never in the type signature. Making it a decorator means the answer is *visible next to the function* and the failure is a clear runtime error naming both the function and the phase, not undefined behaviour.

**How QMF implements it.** `qmf.spec` declares phases: `ON_REGISTER`, `ON_WARM`, `ON_BAR`, `ON_TICK`, `ON_FILL`, `ON_SESSION_BOUNDARY`. Every surface function carries `@phase(...)`. The generated one-page agent surface prints the phase list beside each signature. Cost-model and sizing setters are `ON_REGISTER`-only, which structurally prevents a strategy from widening its own risk mid-run — the Condor guardrail from `01 §14` made mechanical.

### 7. Declare the API in one file; register implementations elsewhere

**Where it lives.** `rqalpha/rqalpha/apis/api_abstract.py` — signature + `@enforce_phase` + `@apply_rules` argument validation + docstring + `raise NotImplementedError`, with `@instype_singledispatch`. Implementations register from asset-class mods: `rqalpha/rqalpha/mod/rqalpha_mod_sys_accounts/api/api_stock.py:166-224`, `api/api_future.py:263-268`.

**Why it matters for QMF.** The ring map's target is "the entire QMF strategy API fits on one printed page" (`01 §23`). rqalpha shows how to *keep* it one page while the implementation grows: the page is a real, importable, checkable artifact, and forex-vs-crypto differences live in registered implementations rather than in `if venue == ...` branches inside the surface.

**How QMF implements it.** `qmf/spec/surface.py` holds every function an agent may call — declaration only. `qmf.venue_model` and asset-class modules register implementations keyed by `(asset_class, venue)`. CI asserts the rendered surface stays under a line budget, and the agent prompt is generated *from that file*, so prompt and code cannot drift.

### 8. Metrics are a registered set of small hook objects, and the set itself is named and versioned

**Where it lives.** `zipline-reloaded/src/zipline/finance/metrics/core.py` (the `register`/`unregister`/`load` registry over a `mappingproxy`), `metrics/tracker.py:122-141` (hook fan-out built once at construction), `metrics/__init__.py:51-91` (the `default` set as a literal `set()` of ~30 objects, each implementing some subset of `start_of_simulation`/`start_of_session`/`end_of_bar`/`end_of_session`/`end_of_simulation`).

**Why it matters for QMF.** `qmf.metrics` is specified as ~34 statistics with four input shapes and one versioned JSON contract. The registry pattern gives that contract a *version* for free: `metrics_set_id` becomes part of the result key alongside `confluence_id`, `split_id`, `data_fingerprint`. Change the statistics, get a new id, and old stored results do not silently become claims about the new definition — the same non-rotting property the confluence hash provides.

**How QMF implements it.** `qmf.metrics.register("qmf-v1", fn)` returning a set of metric objects. `Metric` is a Protocol with optional `on_start`, `on_bar`, `on_session_end`, `on_finish`. `MetricsTracker` binds hooks once. The result contract records `metrics_set_id`; the registry is content-hashed so an unrecorded edit is detectable.

### 9. Slippage must be allowed to say "no fill", and must never breach a limit price

**Where it lives.** zipline: `LiquidityExceeded` (`zipline-reloaded/src/zipline/finance/slippage.py:44`) plus the free function `fill_price_worse_than_limit_price(fill_price, order)` (`slippage.py:47-77`) that *every* model calls before returning. backtrader: `_slip_up` / `_slip_down` return `None` when the slipped price is outside the bar, unless `slip_match`/`slip_out` explicitly permits an impossible price (`backtrader/backtrader/brokers/bbroker.py:994-1039`).

**Why it matters for QMF.** A fill model that always fills is a fill model that lies, and it lies hardest exactly where the strategy is most fragile — news spikes, session opens, thin hours. QMX's `tradeability` score (`10` M2) exists precisely to identify those moments; the fill model must be able to act on it.

**How QMF implements it.** `FillModel.match(...) -> FillResult | NoFill(reason)`, where `reason` is a typed code (`SPREAD_TOO_WIDE`, `OUTSIDE_SESSION`, `NEWS_BLACKOUT`, `NO_LIQUIDITY`). A central `clamp_to_limit(price, order)` is applied by the framework after every model returns, so a model *cannot* breach a limit price even by mistake. `NoFill` counts are reported: a backtest that fills 100% of its orders in the hostile hours is visibly suspect.

### 10. Plug-ins are assembled from config, run in priority order, and their teardown value is the result

**Where it lives.** `rqalpha/rqalpha/mod/__init__.py:32-97` — enabled-from-config, `__config__` defaults merged under user overrides, `sort(key=priority)`, `start_up` forward, `tear_down` reversed, return values collected into the run's result dict. Compare LEAN, where backtest vs live is a swap of handler class names in `config.json` (`research/01-architecture-references.md` §2).

**Why it matters for QMF.** The ring map's central claim is that there is no backtest engine — one kernel, two sets of injected parts. rqalpha is the working proof at this scale, in Python, by a small team. And "the report is a plug-in's teardown return value" removes the last privileged component: the analyser is not special, so a prop-firm compliance report or a slippage-calibration report is the same kind of thing.

**How QMF implements it.** `qmf.runtime` composes from a config that names classes: `clock`, `broker`, `fill_model`, `cost_model`, `bms`, `recorders`. Backtest is `{clock: SimClock, broker: SimBroker}`; live is `{clock: WallClock, broker: CTraderBroker}`. Components implement `start(kernel)` and `finish() -> Any`; the run result is `{name: value}`. Priority is explicit, because the BMS must start before anything can submit an order.

### 11. Deny with a reason, and let cancels through a separate door

**Where it lives.** `rqalpha/rqalpha/interface.py:711-733` — `validate_submission(order, account) -> Optional[str]`, where a returned string *is* the denial and its content *is* the reason; and a separate `validate_cancellation`. Chained in `rqalpha/rqalpha/environment.py:207-221`, publishing `ORDER_CREATION_REJECT` with the reason attached. zipline's parallel: `TradingControl.handle_violation` with `on_error ∈ {"fail", "log"}` (`zipline-reloaded/src/zipline/finance/controls.py:67-86`).

**Why it matters for QMF.** `04 §4.5` found no prior art worth copying for prop-firm rules, and `qmf.bms` is flagged as genuinely greenfield. The *shape* is not greenfield: a chain of validators, each returning a typed reason, with cancellation on a separate path so a `REDUCING` state can block entries while permitting exits. That is the exact BMS semantics the ring map specifies, and rqalpha has it working.

**How QMF implements it.** `Gate.check_submit(intent, state) -> DenialReason | None` and `Gate.check_cancel(...)`, chained by `qmf.bms` in a fixed order with the *first* denial short-circuiting and the binding gate **named** in the result. Denial reasons are an enum, logged, counted, and surfaced to the operator UI. zipline's `on_error="log"` mode becomes QMF's dry-run mode for a new prop-firm ruleset: run the gate, record what it *would* have blocked, without blocking.

### 12. State that is not yet valid should explode informatively, not return `None`

**Where it lives.** `zipline-reloaded/src/zipline/utils/exploding_object.py` — `NamedExplodingObject(name, extra_message)` raises on *any* attribute access with a message naming the attribute and explaining when the field becomes valid. Used for `MetricsTracker._benchmark_source` before `handle_start_of_simulation` (`finance/metrics/tracker.py:100-104`).

**Why it matters for QMF.** A solo operator debugging a VPS at 3am gets either `AttributeError: 'NoneType' object has no attribute 'x'` or *"attempted to access `.returns` of ExplodingObject `self._benchmark_source`; not set until `handle_start_of_simulation` is called."* The second costs ten lines to build and saves hours, repeatedly. It is also a lifecycle-correctness check that costs nothing at run time.

**How QMF implements it.** `qmf.core.NotYet(name, available_after)` used for every field with a lifecycle: `broker` before connect, `market_view` before the MIS warms, `instrument` before the venue's instrument list loads, `account_state` before the first reconciliation. Combined with mental model 6, the two together make "you used it too early" a first-class, self-explaining error class.

### 13. Replay a partially-formed higher-timeframe bar

**Where it lives.** `backtrader/backtrader/resamplerfilter.py:563-702` (`Replayer`) versus `:435-562` (`Resampler`). Resample delivers the daily bar when the day closes; replay delivers *today's bar so far* on every intraday tick, so a daily strategy can react intraday with a bar whose high/low/close are still moving. Selecting replay disables preload and vectorised mode (`backtrader/backtrader/cerebro.py:1066-1070`) because the bar is being constructed live.

**Why it matters for QMF.** The strategy formula is Level + Trigger + Confirmation + Exit, and the components are declared at a `canonical_resolution` (`06` OQ8). But an exit must be able to act *inside* the bar, and a trigger defined on M15 evaluated only at M15 close is a different — usually much worse — strategy than the operator believes. Neither zipline nor rqalpha can express this; backtrader can, and names the cost honestly (no vectorisation).

**How QMF implements it.** `BarSpecification` gains a `delivery ∈ {on_close, forming}` field. `qmf.runtime` feeds `forming` bars from the tick stream, and components declare whether they accept them (`accepts_forming: bool` on `ComponentDef`). A `Level` accepts closed bars only; an `Exit` policy may accept forming bars. That distinction is checked at registration and is a documented difference between two backtests of the same confluence.

### 14. An order carries its own fill audit trail

**Where it lives.** `backtrader/backtrader/order.py:95-175` — `OrderData.exbits`, a deque of `OrderExecutionBit`s, each with size, price, value, commission, P&L, and the resulting position size/price, with two indices (`p1`, `p2`) tracking which bits have been notified so a cloned order carries only the new ones.

**Why it matters for QMF.** Reconciliation after a VPS restart requires answering "what did I already know about this order?" against what the venue reports. An order whose fills are a list attached to the order answers it directly; an order that is only a rolled-up `filled_qty` and `avg_price` cannot. rqalpha's `Account.fast_forward` (`rqalpha/rqalpha/portfolio/account.py:155-174`) needs the same thing at account level, deduplicating by `trade.exec_id`.

**How QMF implements it.** `Order.fills: tuple[Fill, ...]`, each `Fill` carrying `venue_exec_id`, `Provenance`, price, quantity and `TradingCost`. Reconciliation is a set difference on `venue_exec_id`. The simulator produces the same structure, so the reconciliation code path is exercised by every backtest rather than only in production.

---

## What to avoid

**A. Metaclass-driven attribute injection.** backtrader's `MetaBase.donew/dopreinit/doinit/dopostinit` chain (`backtrader/backtrader/metabase.py:66-100`) is extended by `MetaParams`, `MetaLineSeries` (`lineseries.py:305`), `MetaLineIterator` (`lineiterator.py:38`) and `MetaAnalyzer` (`analyzer.py:35`). `MetaAnalyzer.donew` alone synthesises `self.data`, `self.data0`, `self.data0_close`, `self.data_close`, `self.data1_1`, … on every analyzer instance (`analyzer.py:53-71`). None of it is visible to a type checker, an IDE, or a model reading the source. This is the proximate cause of backtrader's death: it could not be safely changed.
**QMF rule:** every attribute an agent or a human can reach is declared on a frozen dataclass or a Protocol. No `setattr` in a metaclass.

**B. Operator overloading whose meaning depends on execution phase.** `LineRoot._operation` (`backtrader/backtrader/lineroot.py:83-94`) dispatches on a `_stage` flag: in `__init__`, `a + b` builds a new lines object; in `next()`, it returns a float (`:193-218`). The library needs `bt.And`, `bt.Or`, `bt.If` as workarounds because Python's boolean operators cannot be overloaded at all.
**QMF rule:** an expression means one thing. Composition is explicit function calls or spec objects, never overloaded arithmetic.

**C. Coupling the engine to a bespoke data stack.** zipline-reloaded's 28 hard dependencies (`zipline-reloaded/pyproject.toml:37-67`) include `bcolz-zipline` — a fork created solely to keep an abandoned columnar format alive — plus `tables` (HDF5), `sqlalchemy>=2` and `alembic` (a *migrating* SQL database of stock identifiers, `src/zipline/assets/asset_db_migrations.py`), `networkx`, `numexpr`, `patsy`, `statsmodels`, `six`, and seven Cython extension modules. You cannot adopt the engine without adopting the museum, and the maintenance history is dominated by re-pinning numpy and pandas.
**QMF rule:** the trading lockfile stays small (the ring map's ≤30 deps / ≤50 MB CI assertion). The engine talks to storage through one narrow reader interface, and Parquet/DuckDB/Polars sit behind it.

**D. Market structure inside neutral components.** rqalpha hard-codes CN session minutes in the *event source* (`rqalpha/rqalpha/mod/rqalpha_mod_sys_simulation/simulation_event_source.py:50-67`: `09:31`, `11:30`, `13:01`, `15:00`; `:36`: day bar at 15:00). Limit-up/limit-down is in the generic matcher (`matcher/base.py`); T+1 `closable`/`today_closable` is on the *abstract* position interface (`interface.py:107-121`); `close_today_quantity` is in the abstract cost args (`interface.py:736-744`).
**QMF rule:** sessions, tick sizes, lot steps, rollover times, weekend gaps and price bands live in `VenueModel` and nowhere else. The clock asks `VenueModel` what time it is allowed to emit.

**E. Same-bar matching available as a plain config value.** rqalpha's `MATCHING_TYPE.CURRENT_BAR_CLOSE` sets `_match_immediately = True` (`mod/rqalpha_mod_sys_simulation/simulation_broker.py:44`), so `submit_order` matches inside the same bar the strategy just saw. It is the *default* in some configs. rqalpha at least names it; backtrader's `cheat_on_open` (`cerebro.py:1621-1626`) and `coc` (cheat-on-close) are the same trapdoor.
**QMF rule:** if a mode can produce impossible fills, it is not a config value — it taints the result. Any run using an optimistic matching mode records `fidelity: optimistic` in the result key, is refused promotion past `measured`, and cannot spend split budget.

**F. Slippage that can push a fill through its own limit price.** rqalpha applies the limit-crossing check to `deal_price` (`matcher/base.py`, step 2) and *then* computes the execution price through the slippage model (step 3 → `_get_execution_price`). With `PriceRatioSlippage`, a buy limit at 100 whose deal price is 100 can execute at 100.05. The model clamps to limit-up/limit-down but not to the order's own limit. zipline avoids this by making `fill_price_worse_than_limit_price` a mandatory check inside every model (`zipline-reloaded/src/zipline/finance/slippage.py:47-77`).
**QMF rule:** the framework applies the limit clamp after the model returns. A fill model cannot opt out.

**G. A single god-object registry.** rqalpha's `Environment` (`rqalpha/rqalpha/environment.py`) is a module-level singleton (`Environment._env`, `get_instance()`) holding data proxy, event bus, broker, portfolio, config, both clocks and every validator. Consequences visible in the source: `Position.prev_close` reaches out to `Environment.get_instance().data_proxy` mid-property (`portfolio/position.py:169-175`); `PriceRatioSlippage.get_trade_price` calls `Environment.get_instance()` to read the price board (`mod/rqalpha_mod_sys_simulation/slippage.py:57-66`). Nothing can be unit-tested without booting the world, and two runs cannot coexist in one process.
**QMF rule:** dependencies are injected into constructors. The kernel holds the wiring; components hold references to what they were given.

**H. A 750-line report builder that pickles its output.** `rqalpha/rqalpha/mod/rqalpha_mod_sys_analyser/mod.py` is 752 lines producing a flat `summary` dict of roughly 60 named floats (daily/weekly/monthly variants of alpha, beta, sharpe, sortino, ulcer index, tracking error, turnover…) and `pickle.dump`s the whole result. Pickle is version-fragile, unreadable without the code, and a deserialisation hazard.
**QMF rule:** the result contract is versioned JSON plus Parquet for the frames. No `pickle` in the runtime — the ring map already bans it for models; extend it to results.

**I. Four execution modes for one loop.** backtrader offers `runonce`/`runnext` × old/new sync × `preload` × `exactbars` × `replay`, with interactions resolved by a cascade of overrides in `run()` (`backtrader/backtrader/cerebro.py:1060-1076`). Determinism cannot be reasoned about because the mode is derived, not chosen.
**QMF rule:** one dispatch loop. Vectorised computation is a separate, explicitly named research surface (the `replay()` driver over the same incremental definitions), and its results carry a different fidelity tag.

**J. Letting the strategy read a raw datetime.** All three permit it. zipline is the only one that makes the *data* honest, by passing `BarData` a `simulation_dt_func` callable instead of a value (`gens/tradesimulation.py:88-95`) so there is no API for naming a future date — but the algorithm can still read `self.datetime` and do arithmetic with it.
**QMF rule:** the agent surface has no raw dates (already the ring map's position, `01 §23`). Data is reached only through `split_id` and `as_of(clock.now())`.

---

## Licence & maturity

| | **backtrader** | **zipline-reloaded** | **rqalpha** |
|---|---|---|---|
| Licence | **GPL-3.0** (`backtrader/LICENSE`, per-file headers e.g. `backtrader/backtrader/sizer.py:7-18`) | **Apache-2.0** (`zipline-reloaded/LICENSE`) | **Custom** (`rqalpha/LICENSE`, Chinese) |
| Practical effect for QMX | Contagious. Linking puts QMX under GPL. **Design study only.** | Permissive. The only one of the three whose code could legally be adapted, with attribution and notice. | Non-commercial use follows Apache-2.0; **commercial use by any individual is forbidden without Ricequant's authorisation, and use by any legal entity or organisation for any purpose is forbidden without it**. The text explicitly extends to "products or services that reference or draw upon this software's functionality or source code". **Design study only — and read the ideas, not the code.** |
| Stars / open issues | 22,869 / 63 | 1,922 / 43 | 6,696 / 30 |
| Latest release | 1.9.78.123 (2023-04-19) | 3.1.1 | 6.3.0 |
| Last `master`/`main` code change | **2023-04-19**; repo `pushed_at` 2024-08-19 reflects non-default-branch activity | push 2026-01-06 | push **2026-08-17** (today) |
| Python support | 2.7 + 3.x (169 `from __future__` imports remain) | ≥3.10 | ≥3.8 |
| Maintainer | single author, inactive | single maintainer (Stefan Jansen), fork of a company project shut down in 2020 | company-backed (Ricequant / 深圳米筐科技), commercially motivated |
| Verdict | **Abandoned.** Confirms `research/01-architecture-references.md` §4. Vocabulary still dominates LLM training data — expect agents to write backtrader idioms unprompted, and design the QMF surface to make that fail loudly rather than subtly. | **Maintained, but by one person, against a fragile substrate.** Architecturally the most instructive of the three. Apache-2.0 makes small, targeted adaptation legally viable — `slippage.py`'s model contract and `metrics/` registry are the two candidates. | **Actively developed and shipping.** The best *interface* design of the three and the closest to the QMF ring map. Legally untouchable for QMX. Read `interface.py`, `core/executor.py`, `apis/api_abstract.py` and `matcher/base.py`; write your own. |

One licensing note worth recording as a dated decision: the rqalpha licence's reach over derivative works that "reference or draw upon this software's functionality or source code" is broader than a normal copyright grant. Extracting *architectural patterns* from a published interface is standard practice and not what copyright protects, but the safe posture — and the one this study assumes — is: no rqalpha code, no rqalpha file structure, no rqalpha naming, and the patterns re-derived and re-expressed in QMF's own vocabulary. That is what section 3 does.

---

## The shortest honest path to an industry-grade backtest capability for QMF

The comparison makes one thing clear: **most of what these three engines are made of is not the backtest.** It is data storage, calendars, asset databases, plotting, reporting, CLI, mods and market-specific rules. The backtest itself — clock, order book, fill decision, ledger — is small. In rqalpha, the simulator that everything else exists to serve is `simulation_broker.py` (189 lines) + `matcher/base.py` + `matcher/bar_matcher.py` (~380 lines together) + `slippage.py` (114 lines). Under 700 lines.

Given the ring map already commits to (a) one domain model, (b) the simulator being an ordinary `BrokerAdapter`, and (c) no central backtest engine, the honest path is five steps and roughly 1,500 lines of new code.

**Step 0 — before anything (a decision, not code).** Fix the fidelity taxonomy now, because it becomes part of every stored result key and cannot be retrofitted. Three levels: `bar_close` (fills at next bar open, fixed spread), `bar_intrabar` (gap-vs-touch logic per backtrader's `_try_exec_stop`, spread from the measured profile), `tick` (quote-by-quote against recorded bid/ask). Result keys become `(confluence_id, split_id, data_fingerprint, qmf_version, venue_model_id, fidelity, metrics_set_id)`. Optimistic modes are tainted per §4-E.

**Step 1 — `qmf.sim.SimClock` (~150 lines).** A generator of `(wall_ts, session_date, EventKind)` driven by `VenueModel.session_schedule`, not by hard-coded hours (§4-D). Event kinds: `SESSION_START`, `BAR`, `TICK`, `SESSION_END`, `SETTLEMENT`, `ROLLOVER`. Nothing else. The clock knows nothing about orders, strategies or data — zipline's `MinuteSimulationClock` is the model, and its purity is the point. Test: the clock for a forex venue emits exactly one `ROLLOVER` per weekday and no events across the weekend gap.

**Step 2 — `qmf.sim.SimBroker` (~300 lines).** Implements the *same* `BrokerAdapter` port as cTrader will: `submit / modify / cancel`, `capabilities()`, `limits()`, `instrument()`, reconciliation queries, and one ordered event stream. It owns the open-order book and delegates every fill decision to a `FillModel`. **Write the adapter conformance suite first and make `SimBroker` implementation #1** (`00-qmf-synthesis-module-map.md` §Novel-2). If the suite passes against `SimBroker` before cTrader exists, backtest↔live parity is structural rather than aspirational, and the cTrader adapter — the riskiest component in v1 — arrives with its acceptance criteria already written.

**Step 3 — `qmf.sim.FillModel` (~400 lines), the part that actually matters.** Everything else in this study is scaffolding for this. The template method of §3-3, with:
- gap-vs-touch stop logic lifted in *shape* from backtrader (`bbroker.py:921-940`) — the one piece of fill logic all three engines agree about;
- a mandatory framework-applied limit clamp (§4-F);
- the ability to return `NoFill(reason)` (§3-9);
- spread drawn from `qmf.data.micro`'s measured per-pair-per-hour distribution, not a constant;
- `TradingCost(spread, commission, slippage, financing, other)` on every fill (§3-4);
- a `PessimisticFillModel` shipped alongside — rqalpha's `LimitPriceSlippage` idea generalised: always the worst plausible price, always the smallest plausible fill. Every promotion candidate runs under both; a strategy whose edge survives only the optimistic model is not a strategy.

This is where QMF must exceed all three references, because all three were built for markets QMX does not trade. Forex needs: variable spread by hour and event proximity, weekend gaps, swap/financing as a P&L line, partial-lot rounding to the venue's step, and margin per instrument. Only backtrader has *any* of these (`comminfo.py:258-303`), and only the interest one.

**Step 4 — `qmf.sim.Ledger` (~250 lines).** Position → Account → Portfolio, with rqalpha's three-way P&L split (`position_pnl` / `trading_pnl` / `pnl`, §2.3), zipline's returns-space return calculation so capital changes cannot corrupt the series (`ledger.py:388-392`), and the financing column present from the first commit (`00-qmf-synthesis-module-map.md` §Novel-8). One dirty flag, recompute at most once per bar.

**Step 5 — `qmf.metrics` (~400 lines, mostly statistics).** The registered-metric-set pattern of §3-8, `metrics_set_id` in the result key, versioned JSON contract out. Do not build a plotting or reporting layer inside the framework (`01 §30`); the research app renders the JSON.

**Then close the loop (§Novel-4 of the ring map).** Measure realised slippage live, conditioned on session and event proximity; feed the distribution back into `FillModel`'s parameters; report backtest-vs-live fill divergence as a tracked number. This is the one thing none of the three engines does, and it converts backtest fidelity from a constant somebody guessed once into a measured, improving quantity. It also puts a number on what the news-blackout gate is worth.

**What not to build, on this evidence:** a bundle system, an asset database, a calendar library, a plotting module, a CLI framework, a mod-discovery mechanism, a second vectorised engine, or an optimiser. Each of those is present in at least one of the three and each is a maintenance liability a solo operator cannot carry. Calendars come from the `VenueModel`; storage from Parquet + DuckDB; the search loop from Optuna behind `qmf.experiment`; plotting from the research app.

**The honest risk.** The fill model is the whole ballgame and it is the one component with no good reference implementation for retail forex. Budget for it to be wrong at first, instrument it so that being wrong is *visible* (the slippage loop), and never let a result produced under an unvalidated fill model spend split budget. That last rule is the difference between a backtest capability and a backtest theatre.
