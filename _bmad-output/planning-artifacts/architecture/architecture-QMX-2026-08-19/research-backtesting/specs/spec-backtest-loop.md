# Spec: The Backtest Loop — How a Backtest Executes End to End

Reverse-engineering spec for QMX. Sources read read-only:
- Jesse v3.0.6 — `C:/Users/Mubarak/Desktop/QMX/workroom/reference/repos/jesse/jesse/modes/backtest_mode.py`
- LEAN engine (C#) — sparse clone at `.../scratchpad/lean-engine/` (paths below are relative to `Engine/`)

Mechanism-understanding only. No third-party code is proposed for reuse. All QMX
requirements below map to QMF law: exact-integer money, UTC-ns time, typed
refusals, result labels carrying world = live/replay/simulated, config-driven runs
(a Book/BMS materializes a config the CLI consumes), logged-during / saved-at-completion
into an unbiased pass/fail ledger.

---

## 1. Feature claim (verbatim, with URL)

**Jesse** (https://docs.jesse.trade/docs/backtest.html):
> "Jesse's backtest engine is the most accurate available, simulating market
> conditions as faithfully as possible including fees, and order types."
> "Jesse will simulate every candle in the selected range and execute your
> strategy logic candle by candle."

**LEAN — event handlers** (https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/event-handlers):
> "The OnData method is the primary event handler for receiving financial data
> events to your algorithm. It is triggered sequentially at the point in time the
> data is available; in backtesting and live."
> "all data for a given moment of time is grouped in a single event, including
> custom data types. This data is passed with the Slice object."
> "In backtesting, if your algorithm takes a long time to process a slice, the
> following slice objects queue up and the next event triggers when your algorithm
> finishes processing the current slice."
> "When fill-forward is enabled for your asset, the OnData event handler will be
> called regularly even if there was no new data. This is the default behavior."

**LEAN — warm-up** (https://www.quantconnect.com/docs/v2/writing-algorithms/historical-data/warm-up-periods):
> "SetWarmUp ... simulates winding back the date you deployed your algorithm by a
> specific time period. In backtests, it changes the start date of your algorithm
> to an earlier time."
> "You can't place trades during the warm-up period because the data feed is
> replaying historical data for setting algorithm state."
> "To check if the algorithm is currently in a warm up period, use the
> `IsWarmingUp` property."

Fine-grained marketing on 1m stepping / higher-TF generation / lookahead is **ABSENT**
from the fetched Jesse pages; the mechanism below is read straight from code, which is
the authority.

---

## 2. Mechanism — how the code actually does it

The two engines make the **opposite core choice**, and that is the central finding:

- **Jesse = fixed-step time stepping.** The clock is a `for i in range(length)` over a
  dense grid of 1-minute candles. Time is derived arithmetically; there is no data-driven
  frontier. Higher timeframes are *generated* by aggregation on stride boundaries.
- **LEAN = data-driven event slices.** The clock (the "frontier") is pulled forward to the
  minimum next-emit-time across all subscription enumerators. Time advances *to wherever the
  next datum is*; a `TimeSlice` bundles everything at that instant. Missing bars are
  synthesized by a fill-forward enumerator, not by a fixed grid.

### 2.A Jesse — fixed 1-minute stepping (`backtest_mode.py`)

**Entry / setup.** `run()` sets `trading_mode='backtest'` and calls `_execute_backtest`
(lines 34–73). `_execute_backtest` injects config, initializes the store, validates routes,
sizes the candle store (`store.candles.init_storage(5000)`, line 118), then loads candles
and hands off to `simulator()` (lines 134–169).

**Data unit & format.** Everything is a NumPy `float64` row `[timestamp_ms, open, close,
high, low, volume]` (note: **O, C, H, L, V** order, close before high — line 347–354,
902–923). Timestamps are epoch **milliseconds**. Candles live in per-(exchange,symbol,timeframe)
`DynamicNumpyArray` storage buffers.

**Warm-up.** `load_candles` (449–492) asks the DB for two arrays per pair: a **warm-up
array** (`warmup_num` candles, default `env.data.warmup_candles_num = 210`, at the
`max_timeframe` of the run — line 450–451) and the **trading array**. Warm-up candles are
injected into storage *before the loop* via `_handle_warmup_candles` →
`candle_service.inject_warmup_candles_to_store` (495–526). Warm-up is thus **out-of-band
pre-seeding of indicator history**, not a replay through the strategy. The loop only ever
iterates the trading array. Missing warm-up data raises a typed `CandlesNotFound` with the
exact date range to import (lines 286–333) — a good model for QMX typed refusals.

**Dispatch mode.** `simulator()` (529–533) forks: `fast_mode=True` → `_skip_simulator`
(gcd-stride stepping), else `_step_simulator` (strict 1-minute stepping). Both produce
bit-exact results by design (comment lines 664–671) but step at different granularity.

**The step loop** (`_step_simulator`, 536–753). Length = number of 1m candles in the first
route's set (556–559). Loop-invariant lookups are hoisted out of the hot loop (575–595).
The core (644–723), per minute `i`:

1. **Advance clock:** `store_app.time = first_candles_set[i, 0] + 60_000` (line 646).
   Time is set to the candle's *close* (open + 60s). This is the whole clock — pure
   arithmetic, no data query.
2. **Inject this minute's 1m candle** for each pair. A jumped-candle gap-fix aligns this
   open to the previous close (`_get_fixed_jumped_candle`, 902–923). The synthetic candle
   is written back into the array (671) so higher-TF generation is built from the *same*
   series that fills run on.
3. **Simulate intra-candle price path → order fills:** `_simulate_price_change_effect`
   (926–983). This is the fidelity core: for any active order whose price lies within
   `[low, high]` of the minute, the candle is *split* at the order price
   (`candle_service.split_candle`), the order executes, and remaining orders are
   re-evaluated against the residual candle in a while-loop. Multiple orders in one candle
   are ordered by a heuristic path model (`_sort_execution_orders`, 1481–1523: infer
   up-then-down vs down-then-up from red/green candle). Liquidations are checked against the
   candle's range too (`_check_for_liquidations`, 986–1018).
4. **Generate higher-TF candles on stride boundaries:** for each configured timeframe with
   `count` minutes, `if i_next % count == 0` aggregate the last `count` 1m rows into one
   higher-TF candle (683–697). So a 1h candle is emitted only every 60 minutes, built from
   the trailing 60 one-minute rows.
5. **Dispatch the strategy on its timeframe boundary:** per route, if timeframe is 1m call
   `strategy._execute()` every minute; else only when `i_next % count == 0` (706–716). Then
   `update_active_orders` per route (717) and `execute_simulated_market_orders()` once
   (720) — market orders fill *after* the candle is fully formed.
6. **Daily equity sampling:** every 1440 minutes, `save_daily_portfolio_balance()` (722–723).

**Finalization** (725–753): terminate strategies, flush remaining market orders, set
`ending_time`, compute metrics/trades/logs via `_generate_outputs`. This is Jesse's
"saved-at-completion" — the equivalent of QMX's ledger write.

**The skip loop** (`_skip_simulator`, 1048–1186). Same shape but the stride is
`candles_step = gcd of all route timeframes` (`_calculate_minimum_candle_step`, 1189–1199).
It processes `candles_step` minutes per iteration: `_simulate_new_candles` builds a single
aggregated "real candle" from the batch via a Rust kernel `candle_from_one_minutes_rust`
(1301–1303, valid for ≤4320 rows), then runs fills across the batch. This is the speed lane;
it only steps as finely as the coarsest common divisor of the timeframes actually needs.

**Determinism.** Fully deterministic by construction: dense integer index, fixed iteration
order over `router.routes`, arithmetic clock, gap-fix and aggregation are pure functions.
Both modes are documented to be bit-exact to each other. Optional `candles_pipeline` (Monte
Carlo) is the only injected variation point.

**Injected-clock seam.** Jesse has **none** — the clock is `store.app.time`, computed inline
from candle timestamps. There is no place to inject an external replay clock; live vs
backtest are entirely different code paths. This is the key gap for QMX.

### 2.B LEAN — data-driven time slices (`Engine/`)

**Handler composition (config-driven).** `Launcher/config.json` (lines 364–376) defines an
**environment** `"backtesting"` that names each pluggable handler by fully-qualified type:
```
setup-handler:       BacktestingSetupHandler
result-handler:      BacktestingResultHandler
data-feed-handler:   FileSystemDataFeed
real-time-handler:   BacktestingRealTimeHandler
history-provider:    SubscriptionDataReaderHistoryProvider
transaction-handler: BacktestingTransactionHandler
live-mode:           false
```
`"live-*"` environments swap the same slots for `LiveTradingDataFeed`, a real brokerage
transaction handler, etc. **The loop is identical; only the handlers change.** This is
exactly the operator's wind-tunnel analogy: change the variables (handlers via config), never
swap the tunnel (`AlgorithmManager.Run`). `Engine.Run` (`Engine.cs` 87–476) wires the chosen
handlers, builds the `DataManager`, `Synchronizer`, security services, history provider, runs
`Setup.Setup()` (executes user `Initialize()`), locks the algorithm (335), and hands off to
`algorithmManager.Run(...)` inside an `Isolator` with a runtime/memory limit (351–368).

**How time advances — the frontier clock.** This is the heart. Three layers:

1. `SubscriptionFrontierTimeProvider.UpdateCurrentTime()` (`DataFeeds/SubscriptionFrontierTimeProvider.cs`
   57–96): scans every subscription's `Current.EmitTimeUtc`, takes the **minimum** across all
   (`earlyBirdTicks = Math.Min(...)`, 87), and advances `_utcNow` to
   `max(earliest_next_datum, current_now)` (94) — monotonic, never rewinds. **Time jumps to
   the next datum**; empty gaps are skipped entirely (subject to fill-forward). The initial
   frontier is the earliest first-emit across subscriptions (`Synchronizer.GetInitialFrontierTime`,
   204–234).
2. `SubscriptionSynchronizer.Sync()` (`DataFeeds/SubscriptionSynchronizer.cs` 88–264): reads
   `frontierUtc = _timeProvider.GetUtcNow()` (101), then for each subscription drains all data
   with `EmitTimeUtc <= frontierUtc` into a `DataFeedPacket` (129–168). Packets → a `TimeSlice`
   via `_timeSliceFactory.Create(frontierUtc, data, changes, universeData)` (250). Universe
   selection runs first and can emit an empty **time pulse** to align algorithm time (229).
3. `Synchronizer.StreamData()` (`DataFeeds/Synchronizer.cs` 86–161): the outer generator.
   De-dupes identical emit times, injects a warm-up-end time pulse when the first post-warmup
   slice overshoots `WarmupEndUtc` (131–134), and yields `TimeSlice`s to the manager.

**The main loop.** `AlgorithmManager.Run()` (`AlgorithmManager.cs` 120–659). Note it does
`foreach (var timeSlice in Stream(...))` (188) — a pull over the synchronizer's enumerable.
Per slice, in strict order:

- Reset time-limit monitor; check status/cancellation (191–205).
- `time = timeSlice.Time; algorithm.SetDateTime(time)` (210, 241) — **the algorithm clock is
  set from the slice, i.e. from data.**
- If `timeSlice.IsTimePulse`: only advance time (and fire warmup-finished if aligned), then
  `continue` (244–250). Pulses carry no data.
- `algorithm.SetCurrentSlice(timeSlice.Slice)` (253).
- Apply universe/security changes (255–262); update each security with its new data
  (`security.Update(...)`, 265–273); scan settlement & margin-interest hourly (276–286);
  cash conversions, invalidate portfolio value (306–312).
- **Warm-up transition:** `CheckWarmupFinished()` (172–186, called at 316) — fires
  `OnWarmupFinished` once, *after* prices are updated so the callback sees current state, and
  re-captures the starting portfolio value. During warm-up, splits/dividends are skipped
  (positions already reflect them) and trading is blocked.
- Consolidator scan for elapsed bars (`ScanPastConsolidators`, 236; per-slice consolidator
  updates 452–481) — LEAN's equivalent of Jesse's higher-TF generation, but push-based via
  `consolidator.Update(dataPoint)` then `consolidator.Scan(localTime)`.
- Fire scheduled events, transactions synchronous events (fill non-market orders on the new
  data, 343), margin calls every 5 min (369–419), splits/dividends/delistings/custom-data
  events (444–574).
- **`algorithm.OnData(algorithm.CurrentSlice)`** — the single v3 event, only `if
  timeSlice.Slice.HasData` (579–583). Then `OnFrameworkData` always (586).
- `transactions.ProcessSynchronousEvents()` again to fill market orders (598),
  `results.ProcessSynchronousEvents()` for sampling (602), `algorithm.OnEndOfTimeStep()` (605).

At stream end: `OnEndOfAlgorithm`, final sampling, status → Completed (612–657). This is
LEAN's saved-at-completion.

**Data feed / slice building.** `FileSystemDataFeed` (`DataFeeds/FileSystemDataFeed.cs`) builds
one enumerator per subscription. Warm-up is realized as a **concatenated enumerator**: a
warm-up enumerator (at `WarmupResolution`, ending at the pivot = start date) then the normal
enumerator, joined by `ConcatEnumerator` (124–156). Fill-forward is a wrapping enumerator
(`FillForwardEnumerator`, 274–302) that synthesizes bars for gaps so `OnData` fires on a
regular cadence even without new trades — the marketed "called regularly even if there was no
new data." The frontier time provider is injected via
`dataFeedTimeProvider.FrontierTimeProvider` (76) — **this is the one clock seam**: in
backtest it is the `SubscriptionFrontierTimeProvider` (data-driven); `LiveSynchronizer`
(chosen at `Engine.cs` 115 when `_liveMode`) swaps in a real-time provider. Same loop,
different clock.

**Determinism.** LEAN forces determinism through: monotonic frontier (never rewinds, 94);
deterministic universe ordering (`OrderBy Resolution ThenBy Symbol.ID`, 233); fixed
sub-phase order within each slice; and time pulses to keep algorithm time aligned even when a
slice has no tradable data. Data points/sec and total counts are reported at the end
(`Engine.cs` 403–406).

### 2.C Key data structures

| Concept | Jesse | LEAN |
|---|---|---|
| Atomic datum | `float64[6]` `[ts_ms,O,C,H,L,V]` | `BaseData` subclasses (TradeBar/QuoteBar/Tick/custom) with `EmitTimeUtc` |
| Time bundle | none — one candle per pair per minute | `TimeSlice` (`Slice` + security updates + consolidator/custom/universe data + `IsTimePulse`) |
| Clock | `store.app.time` (int ms, `= candle_ts + 60000`) | frontier `DateTime` UTC (ticks), min next-emit across subs |
| Higher TF | generated by aggregation on `i % count == 0` | push-based consolidators + fill-forward enumerators |
| Warm-up | pre-seeded `warmup_candles` array (210 def.) | concatenated warm-up enumerator + `IsWarmingUp` gate |
| Handlers | hardcoded per mode | config `environment` names each handler type |

---

## 3. Jesse vs LEAN — which fits QMX and why

**Fixed-step (Jesse):** simple, trivially deterministic, cheap for uniform bar data, one code
path to reason about. Weakness: no clock injection seam (live and backtest diverge), tied to a
dense 1-minute grid (wasteful/awkward for sparse or tick data, event data, alternative data),
and intra-bar fill fidelity is a heuristic path model.

**Event-slice (LEAN):** one loop for backtest/live/paper (only the injected clock + handlers
change), handles heterogeneous/sparse/multi-asset data natively, has an explicit
`TimeSlice` contract, a clean warm-up boundary (`IsWarmingUp`), and — critically — a **single
injectable time-provider seam** that is the difference between replay and live worlds.

**Recommendation for QMX: adopt LEAN's event-slice architecture with an injected clock, and
borrow Jesse's intra-bar fill fidelity as the fill model inside a slice.** Rationale tied to
QMX law and context:
- The **injected replay clock** (`FrontierTimeProvider` seam) is exactly what lets one loop
  emit result labels of `world = replay` vs `live` vs `simulated` — the QMF requirement — with
  no forked engine. Jesse cannot express this without a rewrite.
- The **config-selected handler environment** *is* the wind-tunnel: a Book/BMS materializes a
  config that names the data feed, clock, execution/fill model, and result sink; the CLI
  consumes it. Same loop, swapped variables.
- Event slices scale to the operator's **12–14 concurrent tasks** with heterogeneous
  data/instruments far better than a per-minute grid.
- Jesse's split-candle intra-bar order path (`_simulate_price_change_effect`,
  `_sort_execution_orders`) is the more honest *fill* mechanism and should live inside QMX's
  per-slice execution handler — a fidelity detail, not the loop architecture.
- Keep Jesse's **UTC time discipline and pure-function aggregation**, but store time as
  **UTC-nanoseconds** (QMF law) not ms, and money as **exact integers** not float64.

---

## 4. QMX spec draft — requirements for QMX's own backtest run loop

Requirements (WHAT), not code design. Tagged to QMF contracts where obvious.

**R1 — One loop, injected clock (the seam).** QMX MUST have a single run-loop used for
backtest, replay, and live. The only difference between worlds is an **injected time
provider** and the handler set. The loop MUST read "now" solely from the injected clock.
`world` (live | replay | simulated) MUST be stamped on every result label produced by the run
(QMF result-label law). *(LEAN `Synchronizer.FrontierTimeProvider` seam; QMX must generalize
it so replay is a first-class world, not "backtest".)*

**R2 — Data-driven frontier, monotonic, UTC-ns.** In backtest/replay, the clock MUST advance
to the minimum next-event time across all active data subscriptions, and MUST be monotonic
non-decreasing (never rewind). Time MUST be represented as **UTC nanoseconds** (QMF time law).
Empty gaps MAY be skipped unless fill-forward is requested. *(LEAN
`SubscriptionFrontierTimeProvider.UpdateCurrentTime`, ticks → ns.)*

**R3 — Event slice as the unit of time.** All data valid at a given instant across all
instruments MUST be bundled into one immutable time-slice delivered to strategy code in a
single event. A slice with no tradable data (a **time pulse**) MUST still be able to advance
the clock and drive scheduled/consolidation logic without invoking trading callbacks. *(LEAN
`TimeSlice` / `CreateTimePulse`.)*

**R4 — Deterministic ordering.** For identical inputs and config, a run MUST be bit-for-bit
reproducible. This requires: (a) a fixed, documented sub-phase order within a slice
(data-update → corporate-actions → scheduled events → non-market fills → strategy event →
market fills → sampling); (b) deterministic iteration order over instruments/universes
(stable sort by a canonical id); (c) all aggregation/gap-fix/fill logic as pure functions.
The ledger MUST be able to assert reproduction as part of pass/fail. *(LEAN ordered sub-phases
+ `OrderBy Resolution ThenBy Symbol.ID`; Jesse dense-index determinism.)*

**R5 — Warm-up as pre-seed, trading-locked.** QMX MUST support a warm-up period specified as
either N bars or a duration. During warm-up the engine MUST feed historical data to build
indicator/model state but MUST **refuse orders** with a typed refusal (QMF typed-refusal law),
expose an `is_warming_up` flag, and fire a single `on_warmup_finished` transition *after* state
is current and *before* any post-warmup strategy code. Corporate actions during warm-up MUST be
skipped (positions already reflect them). Missing warm-up data MUST raise a typed refusal
naming the exact instrument + date range to import. *(LEAN concat warm-up enumerator +
`CheckWarmupFinished`; Jesse `warmup_candles` pre-seed + typed `CandlesNotFound`.)*

**R6 — Higher-timeframe / aggregation without lookahead.** Aggregated bars MUST be emitted
only on completed boundaries and MUST be built from the *same* (possibly gap-fixed) underlying
series that fills run on — never from a future or a divergent series. A bar MUST NOT be visible
to strategy code before its close time under the clock. *(Jesse write-back at line 671 + stride
gate; LEAN consolidator `Update`→`Scan`.)*

**R7 — Intra-bar fill fidelity.** Within a bar/slice, order fills MUST use an explicit,
documented intra-bar price-path model: an order fills only if its price lies within the bar's
range; the bar is split at the fill price; residual orders re-evaluate against the remainder;
multiple fills in one bar are sequenced by a declared path heuristic; liquidations are checked
against the full range. Fill prices, quantities, and cash effects MUST use **exact-integer
money** (QMF money law). *(Jesse `_simulate_price_change_effect`, `split_candle`,
`_sort_execution_orders`, `_check_for_liquidations`.)*

**R8 — Config-materialized handler set (wind tunnel).** The run loop MUST select its data
feed, clock/time-provider, execution/fill model, and result sink from a **config the CLI
consumes** (materialized when a Book/BMS is created). Switching backtest → replay → live MUST
be a config change, not a code change. *(LEAN `environments` in config.json + `Engine.Run`
handler wiring.)*

**R9 — Log-during, save-at-completion, unbiased verdict.** The loop MUST stream progress/logs
during the run and, at completion, write results (metrics, trades, equity samples, data-point
counts, execution duration) into the **ledger** with an unbiased pass/fail end result. Equity
MUST be sampled on a fixed cadence (e.g. daily) independent of trade activity. A run whose
portfolio value goes non-positive MUST halt with a typed terminal state, not hang. *(LEAN
`results.Sample` daily schedule + non-positive-value break at 213–219; Jesse
`save_daily_portfolio_balance` + `_generate_outputs`.)*

**R10 — Bounded, cancellable, observable runs.** Each run MUST enforce a per-step and total
time/memory limit, be cancellable via a token, and report data-points-processed throughput —
so 12–14 concurrent tasks fail fast and legibly rather than hang. Cancellation and limit
breaches MUST surface as typed refusals/terminal states in the ledger. *(LEAN
`AlgorithmTimeLimitManager`, `Isolator.ExecuteWithTimeLimit`, cancellation token; Jesse
`Timeloop` heartbeat + `exceptions.Termination`.)*

**R11 — Sparse / heterogeneous data first-class.** The unit of data MUST be a typed event with
its own emit-time, not a fixed 1-minute row — so ticks, quotes, bars of mixed resolution,
funding events, and alternative/agent-relevant data all flow through the same frontier and
slice machinery. Fill-forward MUST be opt-in per subscription. *(LEAN `BaseData.EmitTimeUtc` +
`FillForwardEnumerator`; contrast Jesse's mandatory dense 1m grid.)*

---

## 5. Open questions

1. **Replay vs backtest as distinct worlds.** LEAN collapses both into "not live"; QMF names
   `replay` and `simulated` separately. What exactly distinguishes them for QMX — recorded
   real order-book/tick replay (`replay`) vs synthetic/aggregated-bar simulation
   (`simulated`)? This determines whether R7's fill model even runs (replay may use recorded
   fills).
2. **Nanosecond clock vs bar data.** UTC-ns is required by QMF, but most historical bar data is
   ms/second-grained. Is the ns clock purely for tick/event replay and live, with bars mapped
   onto ns boundaries? Need the canonical mapping rule.
3. **Concurrency isolation.** 12–14 concurrent runs — one process with N isolated loops, or N
   processes? LEAN runs one algorithm per engine instance in an isolator; QMX's target load
   implies a scheduler above the loop. Out of scope here but constrains R10.
4. **Fill-model determinism across path heuristics.** Jesse's up-then-down/down-then-up
   heuristic (`_sort_execution_orders`) is a *guess* about intra-bar path. For an unbiased
   pass/fail ledger, is a documented heuristic acceptable, or does QMX need a
   worse-case/both-ways bound to avoid optimistic bias?
5. **Warm-up resolution mismatch.** LEAN warms up at a coarser `WarmupResolution` then
   concatenates. Does QMX allow warm-up at a different resolution than the trading feed, and
   how is the join point defined under the ns clock (Jesse fixes this by using `max_timeframe`
   for warm-up count)?
6. **Corporate actions / funding.** Jesse (crypto) mostly ignores splits/dividends; LEAN has a
   full splits/dividends/delisting pipeline inside the loop. Which of these (plus perp funding)
   are in scope for QMX's quant-agent users, and do they belong in the loop or a handler?
7. **Progress/heartbeat transport.** Jesse uses Redis `sync_publish`; LEAN uses a result
   handler thread. What is QMX's log-during transport, and how does it reconcile with the
   save-at-completion ledger write to avoid double-sourcing truth?
