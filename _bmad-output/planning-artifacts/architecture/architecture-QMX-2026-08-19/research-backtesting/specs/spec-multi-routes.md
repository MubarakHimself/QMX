# Spec: Multi-Timeframe + Multi-Symbol Testing (Routes / Universe / Permutation Sweeps)

Reverse-engineered from QuantConnect Lean (Apache-2.0, C#) and Jesse (MIT, Python v3.0.6).
Mechanism understanding only — no third-party code is used in QMX. All cites are file:line into the local read-only clones.

Clone roots:
- Jesse: `C:/Users/Mubarak/Desktop/QMX/workroom/reference/repos/jesse/jesse`
- Lean engine (C#): `.../scratchpad/lean-engine`

---

## 1. Feature claim (verbatim, with URL)

**Jesse** — https://docs.jesse.trade/docs/routes.html
- "Jesse allows trading more than one symbol at the same time."
- "Data routes look a lot like trading routes, except that you don't assign a strategy to them."
- "The `exchange` and `symbol` pairs must be unique. That means you CANNOT trade `BTC-USDT` in `Binance` on both `1h` and `4h` timeframes at the same time."
- "you cannot have more than one position open for the same symbol."
- Doc shows concurrent routes across different symbols/timeframes (e.g. BTC-USDT @ 1h + ETH-USDT @ 4h).
- `get_candles` cross-route access and `on_route_*` callbacks: **ABSENT from the marketing docs** (documented only in code — see §2). The routes page makes no verbatim claim about either.

**Lean** — https://www.quantconnect.com/docs/v2/writing-algorithms/consolidating-data/getting-started
- "Consolidating data allows you to create bars of any length from smaller bars."
- "Consolidation is commonly used to combine one-minute price bars into longer bars such as 10-20 minute bars."
- "Consolidated bars are helpful because price movement over a longer period can sometimes contain less noise ... so they may present more opportunities to capture alpha."
- Multi-resolution "without requiring separate subscriptions" — consolidators transform an existing subscription's data into custom timeframes.

**Framing note:** "lots of combinations and permutations" of *symbols and timeframes as separate labeled runs* is a claim neither project markets as such. Jesse combines symbols+TFs *inside one backtest* (routes); Lean combines resolutions *inside one algorithm* (consolidators) and separately sweeps *numeric parameters* as many backtests (Optimizer). The permutation-sweep-as-batch is QMX's own composition (§4).

---

## 2. Mechanism — how the code actually does it

### 2.A Jesse: routes are a declared set; 1m is the master clock; higher TFs are derived

**Declaration & validation.** The `RouterClass` holds two lists — `routes` (trading, strategy-bearing) and `data_routes` (data-only, no strategy) — and `initiate()` validates and expands them into config sets (`routes/__init__.py:11-89`):
- Each route is `(exchange, symbol, timeframe, strategy)`; data routes are `(exchange, symbol, timeframe, None)` (`routes/__init__.py:114, 118-120`; `models/Route.py:7-23`).
- **Uniqueness rule:** each `(exchange, symbol)` pair may be traded only once — enforced by a count loop that raises `InvalidRoutes` (`routes/__init__.py:31-45`). This is *per pair*, not per pair+TF, which is why the same symbol on two timeframes is forbidden as two trading routes.
- **Same-quote-asset rule:** all trading routes must share one quote asset "because otherwise we cannot calculate the correct performance metrics" (`routes/__init__.py:47-52`). This is a *portfolio-accounting* constraint, not a data constraint.
- **1m injection:** the union of all route timeframes is collected into `considering_timeframes`, and `considering_timeframes.add('1m')` forces the 1-minute stream to always exist (`routes/__init__.py:63-77`). Everything downstream is built from 1m.
- Output config sets: `considering_candles` (the (exchange,symbol) pairs to *load*), `considering_symbols/timeframes/exchanges` (everything needed for data+generation), and `trading_*` (the subset that actually trades) — `routes/__init__.py:77-85`. Data routes widen the "considering" sets without widening the "trading" sets.

**Candle format.** A candle is a 6-column float64 row: `[timestamp_ms, open, close, high, low, volume]` — note **O,C,H,L order**, not OHLC (`services/candle_service.py:46-53, 295`).

**Higher timeframes are generated, never subscribed.** `generate_candle_from_one_minutes(timeframe, one_min_block)` folds N 1m rows into one: open = first row's open, close = last row's close, high = max, low = min, volume = sum (`services/candle_service.py:17-43`). N = `timeframe_to_one_minutes(tf)`.

**The simulator loop** (`modes/backtest_mode.py:_step_simulator`, 536-720) is the heart:
- One master length in minutes; `store.app.time` advances by 60_000 ms per iteration off the first route's 1m series (`612-614`).
- Per minute, for **each** (exchange,symbol): append that minute's 1m candle to storage, apply price-change/fill effects, then **for each bigger timeframe, if `i_next % count == 0`** generate the completed higher-TF candle and add it (`641-692`). `count` = minutes-per-bar; the modulo is the bar-boundary test.
- Then, for each **trading route**, call `strategy._execute()` only on its own bar boundary: `count == 1` every minute, else `if i_next % count == 0` (`695-709`). So a 4h strategy's logic fires once per 240 one-minute steps, on aligned candles built from the same 1m spine every other route also sees.
- A fast path (`_skip_simulator`) and an upfront prefill/gap-fix optimization exist but are bit-exact equivalents (`596-655`).

**Cross-route reads.** A strategy reads *any* stream — its own or another route's — through `self.get_candles(exchange, symbol, timeframe)` → `candle_service.get_candles` (`strategies/Strategy.py:1521-1531`). That function is a plain storage dict lookup keyed `f'{exchange}-{symbol}-{tf}'`; for non-1m TFs it returns completed bars and, in backtest only, synthesizes the *forming* bar on demand from the tail of the 1m array (`services/candle_service.py:631-679`). Cross-route access therefore needs no wiring — any (exchange,symbol,tf) already materialized in the considering-set is readable. `self.candles` is just `get_candles(self.exchange, self.symbol, self.timeframe)` (`Strategy.py:1512-1519`). Missing key → `RouteNotFound` (typed refusal).

**Cross-route event callbacks.** When any strategy changes position, `_broadcast(msg)` iterates `router.routes`, skips self, and calls the peer's `on_route_open_position / on_route_close_position / on_route_increased_position / on_route_reduced_position / on_route_canceled` (`strategies/Strategy.py:499-518`). Default bodies are no-ops for the strategy author to override (`Strategy.py:1268-1305`). This is Jesse's multi-strategy coordination primitive (e.g. a portfolio route reacting to a signal route).

### 2.B Lean: one subscription per (symbol,resolution); consolidators fan it up to any TF

**Subscription config.** Each data stream is a `SubscriptionDataConfig`: `{Type, Symbol, TickType, Resolution, Increment(TimeSpan), FillDataForward, ExtendedMarketHours, IsInternalFeed, IsCustomData, ...}` (`Common/Data/SubscriptionDataConfig.cs:42-178`). `SubscriptionManager.Add(...)` registers one per (symbol, resolution, tick type) (`Common/Data/SubscriptionManager.cs:89-160`). Multiple symbols and multiple resolutions of the same symbol are simply multiple configs — Lean has **no same-symbol/same-quote restriction**; it is security-object + portfolio accounting, not a route list.

**Consolidators = Lean's higher-TF mechanism.** Rather than subscribe a second stream for a bigger bar, you attach a consolidator to an existing subscription: `SubscriptionManager.AddConsolidator(symbol, consolidator)` finds matching subscriptions and pipes their data into the consolidator, wrapping it in a `ConsolidatorWrapper` with the subscription's `Increment` and exchange timezone (`SubscriptionManager.cs:165-210`). The data feed pushes each incoming bar into every attached consolidator; when a period closes, the consolidator fires `DataConsolidated`. Time-driven scanning is handled by `ScanPastConsolidators(newUtcTime, algorithm)`, a priority queue ordered by each consolidator's next scan time (`SubscriptionManager.cs:301-345`). Consolidator families cover every bar style: `TradeBarConsolidator`, `QuoteBarConsolidator`, `TickConsolidator`, `RenkoConsolidator`, `RangeConsolidator`, `SequentialConsolidator` (chained), calendar/session-aware, etc. (`Common/Data/Consolidators/`). `ResolveConsolidator(symbol, resolution|timespan)` auto-builds the right one so indicators can register at any TF (`Algorithm/QCAlgorithm.Indicators.cs:3676-3761`). Universe selection adds/removes subscriptions dynamically at runtime (`Common/Data/UniverseSelection/`), which is Lean's "many symbols by rule" story.

### 2.C Lean Optimizer: permutation sweeps as many labeled backtests

Lean's sweep engine is *parameter*-based, but its structure is exactly the batch model QMX needs. `GridSearchOptimizationStrategy` calls `Step(OptimizationParameters)` (`Optimizer/Strategies/GridSearchOptimizationStrategy.cs:53`), whose `Recursive(Queue<OptimizationParameter>)` produces the full **Cartesian product** of every parameter's value list, yielding one `ParameterSet` per combination (`Optimizer/Strategies/StepBaseOptimizationStrategy.cs:178-243`). `GetTotalBacktestEstimate()` = product of each parameter's step count (`:113-146`). Each `ParameterSet` becomes one `OptimizationNodePacket` = one independent backtest; results stream back and are ranked against a `Target` under `Constraints` (`Optimizer/LeanOptimizer.cs`, `Optimizer/OptimizationResult.cs`, `Strategies/StepBaseOptimizationStrategy.cs:151-170`). Each backtest is fully isolated with its own result artifact — the direct analog of "each combo = one labeled run, aggregated in the ledger."

---

## 3. Jesse vs Lean — which fits QMX and why

| Concern | Jesse | Lean | QMX choice |
|---|---|---|---|
| Instrument+TF set declaration | Explicit `routes` + `data_routes` lists, validated | Imperative `AddSecurity`/`AddConsolidator` in code | **Jesse-style declarative** — a config the CLI materializes (wind-tunnel), no imperative setup code |
| Higher timeframes | Generated from a single 1m spine, on bar-boundary modulo | Consolidators fan one subscription to any period | **Jesse's 1m-spine generation** as the deterministic core; adopt **Lean's consolidator generality** (Renko/range/session) as future bar-types |
| Cross-stream reads | `get_candles(ex,sym,tf)` dict lookup, zero wiring | Register indicator/consolidator per stream | **Jesse's uniform read API** — any declared stream readable by key |
| Multi-strategy coordination | `on_route_*` broadcast callbacks | Framework alpha/portfolio models | **Jesse's `on_route_*`** — simplest primitive for agent strategies |
| Same-symbol-two-TF | Forbidden (1 pair = 1 trade route) | Allowed | **Relax toward Lean**: forbid two *positions* per (venue,instrument), but allow the same instrument at many TFs as *data*, and across *separate runs* in a sweep |
| Quote-asset uniformity | Required (accounting) | Not required | **Keep as a per-run accounting invariant** (QMF exact-integer money needs one settlement unit per book) |
| Permutation sweep | Not native (one route-set per backtest) | Native Cartesian over parameters → N isolated backtests | **Lean's Cartesian-batch model**, generalized to sweep symbol×TF×params, each node one labeled QMX run in the ledger |

**Verdict.** QMX's per-run *inside-the-tunnel* model = **Jesse routes** (declarative, 1m-derived, uniform reads, route callbacks) with a **relaxed uniqueness rule**. QMX's *across-runs* sweep model = **Lean's optimizer Cartesian product**, but the axes are (symbol, timeframe, parameters), not parameters alone — each combination is one isolated labeled run written to the ledger.

---

## 4. QMX spec draft (requirements — WHAT, mapped to QMF contracts)

### 4.1 Run instrument+timeframe set (per-run, "inside the tunnel")
- **R1.** A Book/BMS config MUST declare a **stream set**: a list of `trading_streams` and an optional list of `data_streams`. Each stream = `{venue, instrument, timeframe, strategy?}`. `strategy` present ⇒ trading stream; absent ⇒ data-only stream. (Jesse routes vs data_routes.) The CLI materializes this from the Book config — no imperative setup code (operator wind-tunnel law).
- **R2.** The engine MUST always materialize a **1-minute (or the venue's finest native) base stream** for every `(venue, instrument)` referenced, and derive every higher timeframe from it by folding: open=first, close=last, high=max, low=min, volume=sum. Higher-TF bars MUST only be emitted on aligned period boundaries (modulo the base-bar count).
- **R3.** Canonical candle contract: `[time, open, high, low, close, volume]` with **time as UTC-ns integer** and **prices/volume as exact-integer money/quantity** (QMF law — do NOT copy Jesse's float64 O,C,H,L ordering). Bar timestamp = period-open, aligned to the boundary.
- **R4. Uniqueness (relaxed from Jesse):** at most one open **position** per `(venue, instrument)` within a run; but the same instrument MAY appear at multiple timeframes as data streams, and MAY be a trading stream at different timeframes across *different runs* in a sweep. Violations return a **typed refusal** (`DuplicatePositionStream`), not a crash.
- **R5. Settlement uniformity:** all *trading* streams in one run MUST share one quote/settlement asset (required for exact-integer portfolio accounting). Violation ⇒ typed refusal (`MixedSettlementAsset`).

### 4.2 Reading other streams from a strategy
- **R6.** A strategy MUST read any declared stream by key: `get_bars(venue, instrument, timeframe) -> bars`. Its own stream is the default (`self.bars`). Lookup of an undeclared stream MUST return a **typed refusal** (`StreamNotFound`) — never silent empty/None. (Jesse `RouteNotFound`.)
- **R7.** In replay/backtest, a *forming* (incomplete) higher-TF bar MAY be exposed on demand; in live/replay-of-live it MUST NOT fabricate future data. The bar's completeness state MUST be inspectable so agents cannot accidentally act on a forming bar. Result labels carry the world tag (live/replay/simulated) per QMF law.
- **R8.** Cross-stream **event callbacks**: when any strategy in a run changes position, the engine MUST broadcast to peer strategies `on_peer_open / on_peer_close / on_peer_increase / on_peer_reduce / on_peer_cancel` (Jesse `on_route_*`), skipping the originator. Default no-op; override optional. This is the multi-agent coordination primitive.

### 4.3 Permutation sweeps ("lots of combinations and permutations")
- **R9.** A **sweep** MUST be declarable as axes: `instruments[]`, `timeframes[]`, and `parameters{name: values[]}`. The engine MUST expand the full **Cartesian product** of the axes (Lean grid recursion), each combination = one **run spec**. Pre-flight MUST report the total run count (product of axis lengths) before execution — the operator sees the size before committing.
- **R10.** Each combination MUST execute as **one isolated, labeled run** — one Book/BMS config instance (same tunnel, different variables). Runs share nothing mutable. Label MUST encode the combo: `{sweep_id, instrument, timeframe, param-hash}` plus the world tag.
- **R11.** During each run, results are **logged**; at completion they are **saved into the ledger** with an unbiased pass/fail end result and the run's metrics — one ledger row per combo (Lean's per-node result artifact). The ledger MUST support **aggregation/ranking across combos** in a sweep (best/worst, constraint filtering — Lean's Target+Constraints), without re-running.
- **R12.** The scheduler MUST run combos **concurrently up to the target load (12-14 tasks)**; concurrency MUST NOT change any single run's result (determinism). Each combo run independently emits its typed refusals; one combo's refusal MUST NOT abort the batch — it is recorded as that combo's labeled outcome.
- **R13.** A run and a sweep are the same object at different scale: a single run = a 1×1×1 sweep. The CLI creates the sweep config the same way it creates a Book config; MCP is optional (may drive sweeps) but MUST NOT be required.

### 4.4 QMF contract mapping (summary)
- Time → UTC-ns integer (R3, R7). Money/qty → exact integers (R3, R5, R11).
- Typed refusals → R4, R5, R6, R12 (`DuplicatePositionStream`, `MixedSettlementAsset`, `StreamNotFound`).
- Result labels with world (live/replay/simulated) → R7, R10, R11.
- No third-party engine code → the 1m-spine folding, Cartesian expansion, and callback broadcast are re-specified here as requirements, implemented natively.

---

## 5. Open questions

1. **Finest base resolution per venue.** Jesse hardcodes 1m. QMX venues may offer tick or sub-minute; does the "base stream" become tick-based (Lean-style), and how does that interact with exact-integer bar folding and the 12-14 concurrency budget (tick storage cost)?
2. **Cross-*venue* streams in one run.** Jesse allows multiple exchanges in the considering set but requires one quote asset. Can a QMX run legitimately hold trading streams across venues with FX between quote assets, or is that always a separate sweep axis? (Affects R5.)
3. **Forming-bar exposure policy.** Should agents ever see forming higher-TF bars (R7), or is that a foot-gun that should be refused by default and opt-in only? Determinism vs realism tradeoff.
4. **Sweep axis independence.** Are symbol×TF×param axes always independent (full Cartesian), or does QMX need *coupled* axes (e.g. TF list per-instrument, or Lean's Euler/adaptive search) to avoid combinatorial blowup beyond the concurrency budget?
5. **Ledger aggregation semantics.** What is the canonical unbiased pass/fail rule per combo, and how are cross-combo rankings kept unbiased (guard against overfitting / multiple-comparisons across a large sweep)? Lean has Target+Constraints; QMX's unbiased-ledger law needs an explicit statistic.
6. **Same-instrument multi-TF trading in one run.** R4 relaxes Jesse's ban to *data* streams and *across-run* sweeps but still forbids two positions on one (venue,instrument). Confirm no agent use-case needs two simultaneously-traded TF strategies on the same instrument within a single run (would require sub-position accounting).
