# Fill Simulation — `hftbacktest` deep study

**Assignment:** deep-study `reference/repos/hftbacktest` (Rust core + Python binding). Focus: how a queue-position-aware fill model actually works — per-price-level state, the limit-order fill decision against tick data, latency modelling — and which parts transfer *down* to QMX's retail-forex-on-cTrader context, where the broker supplies no order-book depth and no trade prints.

**Licence:** MIT (`reference/repos/hftbacktest/LICENSE`, "Copyright (c) 2022 nkaz001@protonmail.com"). A second identical `LICENSE` sits in `py-hftbacktest/`. MIT is inside the ratified dependency pool from `00-qmf-synthesis-module-map.md` §Decide-next A1 — code could legally be vendored. This study still recommends **mental models only**, for reasons given under "What to avoid".

**Method:** read-only. Nothing was built, installed, or executed. No `.git` directory exists in the clone, so maintenance state was checked against internal evidence (crate version, Rust edition) plus one web fetch of the GitHub landing page.

---

## In plain words

1. `hftbacktest` answers one question with unusual care: *if I had left a limit order sitting at this price, would it actually have been filled?* Everything else in the project exists to serve that question.
2. Its answer has two halves. If the market **traded through** your price, you filled — that half is certain. If the market only **traded at** your price, you filled *only if the queue in front of you had already been eaten* — and that half is a guess, so the project makes the guess explicit, parameterised and swappable.
3. To make that guess it keeps one number per order: how much quantity sits ahead of you at your price level. Trades at your price shrink it. Cancellations at your price shrink it *partially*, by a probability that depends on where in the queue you are.
4. The most conservative model assumes every cancellation happened *behind* you, so only real trades move you forward. The realistic models assume some cancellations were in front. The gap between those two is a tunable dial, and the project's stated method is to **turn that dial until the backtest equity curve matches your live equity curve**, trading small.
5. That calibration loop — fill model has a free parameter, parameter is fitted against live results rather than guessed once — is the single most valuable idea here, and it is exactly what QMX's module map already called "close the slippage loop" (Novel Idea #4).
6. The second most valuable idea is structural: every market event carries **two timestamps** (when the exchange produced it, when your machine received it), and the same data file is replayed **twice** — once for the simulated exchange in exchange-time order, once for the strategy in local-time order. The strategy therefore *cannot* see what the exchange sees. Lookahead is prevented by data layout, not by discipline.
7. Latency is modelled as a real journey with three legs — feed, order entry, order response — and orders travel on a timestamped bus, so the market moves while your order is in flight. Nothing is instant. There is even a knob to charge yourself for your own Python's thinking time.
8. Almost all the *quantity* machinery is HFT-only and does not transfer. A retail cTrader broker is your counterparty; there is no shared queue to hold a position in, no depth feed, and no trade prints with sizes. Building a `QueuePos` for cTrader would be modelling a fiction.
9. What does transfer is the *shape* of the decision: touching a price is not filling at it; equality needs a probability; buys fill at the ask and sells at the bid, always; and the pessimistic default should be the one you ship until live data earns you a relaxation.
10. Quality verdict: high, and honest about its own limits — but with one glaring hole. The single most consequential line in the whole project, the queue-advance formula at `queue.rs:203`, has no unit test.

---

## Findings per repo

Only one repo was assigned. It is covered in depth below, broken into the sub-systems the assignment named.

### `hftbacktest` — Rust workspace + PyO3/numba Python binding

**Licence:** MIT. **Version:** `hftbacktest` crate `0.9.4`, `edition = "2024"`, `rust-version = "1.91.1"` (`reference/repos/hftbacktest/hftbacktest/Cargo.toml:1-20`). Requiring Rust 1.91 means the codebase was touched after that toolchain shipped — recent by construction. **Popularity/maintenance:** 4.4k stars, ~1,038 commits, open issues and PRs, CI workflows present (`.github/workflows/`), external contributors credited in-repo (`ROADMAP.md` credits `@roykim98` for the fee-model work). Primary author `nkaz001` throughout. This is **not** one of the days-old single-author repos the wave-1 catalog flagged; it is a multi-year project with a real user base.

**Overall quality verdict: HIGH — study it, do not vendor it.** Reasons for each half are at the end of this section.

---

#### 1. What state it tracks per price level

The unit of state is **per order**, not per price level, and it is deliberately tiny. The whole queue-position abstraction is a four-method trait:

```
reference/repos/hftbacktest/hftbacktest/src/backtest/models/queue.rs:25-40
  trait QueueModel<MD> {
      fn new_order(&self, order, depth);                       // seed the estimate
      fn trade(&self, order, qty, depth);                      // a trade printed at my price
      fn depth(&self, order, prev_qty, new_qty, depth);         // level quantity changed
      fn is_filled(&self, order, depth) -> f64;                 // how much of me executed
  }
```

Four events, one hidden state variable. For the conservative model that state is a single `f64` (`queue.rs:73` — `order.q = Box::new(front_q_qty)`); for the probability model it is two numbers (`queue.rs:99-103`):

```rust
pub struct QueuePos {
    front_q_qty: f64,      // estimated quantity ahead of me at my price
    cum_trade_qty: f64,    // trades seen at my price since the last book update
}
```

Seeding: when the exchange accepts your order, `front_q_qty` is set to the **entire visible quantity currently at your price level** (`queue.rs:165-173`). You join the back of the queue. That is the only honest assumption available from a Market-By-Price feed.

The `cum_trade_qty` field exists solely to prevent double-counting, and it is the subtlest thing in the file. A crypto exchange sends you a trade print *and*, separately, a book update showing the level shrank. Naively you would advance the queue twice for one event. So `trade()` accumulates (`queue.rs:175-179`), and `depth()` subtracts that accumulation from the observed shrink before attributing the remainder to cancellations, then resets it (`queue.rs:181-188`):

```rust
let mut chg = prev_qty - new_qty;
chg -= q.cum_trade_qty;      // trades already moved me; don't move me again
q.cum_trade_qty = 0.0;
```

#### 2. The queue-advance formula — the heart of the project

`reference/repos/hftbacktest/hftbacktest/src/backtest/models/queue.rs:190-205`:

```rust
if chg < 0.0 {                                   // level GREW
    q.front_q_qty = q.front_q_qty.min(new_qty);  // new quantity joins behind me
    return;
}
let front = q.front_q_qty;
let back  = prev_qty - front;                    // quantity behind me
let prob  = self.prob.prob(front, back);         // P(a cancellation came from behind me)
let est_front = front - (1.0 - prob) * chg + (back - prob * chg).min(0.0);
q.front_q_qty = est_front.min(new_qty);
```

Read term by term:

- `chg` is the non-trade shrink at the level — i.e. **cancellations**.
- `prob` is the modelled probability a given cancellation came from *behind* you.
- `(1 - prob) * chg` is therefore the share that came from *in front* of you, and it advances you.
- `(back - prob*chg).min(0.0)` is an **overflow correction**: if the model attributes more cancellations to the queue behind you than actually exists behind you, the surplus must have come from in front, so it advances you further. Zero when the model is self-consistent.
- `.min(new_qty)` clamps you to a physical bound — you cannot be behind more quantity than the level contains.

That shape — *a state variable, a set of events that move it, one probability parameter, and a clamp to a physically impossible bound* — is the general shape of any fill model, including one for retail FX where the state variable will mean something entirely different.

`is_filled` (`queue.rs:207-216`) is the payoff: once `front_q_qty` goes **negative**, the magnitude of the negative is your executed quantity, rounded to lot size. Elegant: one signed number encodes both "how far back am I" and "how much of me went through".

The probability functions are a family, all satisfying "P(0)=0 at the head, P(1)=1 at the tail" (`docs/order_fill.rst:163-168`):

| Model | Formula | Where |
|---|---|---|
| `PowerProbQueueFunc(n)` | `back^n / (back^n + front^n)` | `queue.rs:236-240` |
| `PowerProbQueueFunc2(n)` | `back^n / (back+front)^n` | `queue.rs:303-307` |
| `PowerProbQueueFunc3(n)` | `1 - (front/(front+back))^n` | `queue.rs:326-330` |
| `LogProbQueueFunc` | `log(1+back) / (log(1+back)+log(1+front))` | `queue.rs:258-262` |
| `LogProbQueueFunc2` | `log(1+back) / log(1+back+front)` | `queue.rs:280-284` |

And the conservative extreme, `RiskAdverseQueueModel` (`queue.rs:63-96`), which does not use a probability at all — its `depth()` is simply `front_q_qty = front_q_qty.min(new_qty)`: **all cancellations are assumed to come from the tail, so only real trades move you forward.** That is the "assume the worst" model, and it is the right default shape for QMX.

#### 3. How the limit-order fill decision is actually made

There are two exchange processors. `NoPartialFillExchange` is the default. Its contract is stated at the top of the file (`reference/repos/hftbacktest/hftbacktest/src/backtest/proc/nopartialfillexchange.rs:44-62`) and mirrored in `docs/order_fill.rst:25-44`:

> Buy order in the order book:
> - Your order price **>=** the best ask price
> - Your order price **>** sell trade price
> - Your order is at the front of the queue **&&** your order price **==** sell trade price

The load-bearing detail is the **strict inequality on the middle line and the `&&` on the third**. Trading *through* your price is an unconditional fill. Trading *at* your price is a fill only if the queue model says you were at the front. The code enforces this with a three-way comparison (`nopartialfillexchange.rs:139-162`):

```rust
match order.price_tick.cmp(&price_tick) {
    Ordering::Greater => { /* traded through -> unconditional fill */ }
    Ordering::Less    => { /* nothing */ }
    Ordering::Equal   => {                       // traded AT my price
        self.queue_model.trade(order, qty, &self.depth);
        if self.queue_model.is_filled(order, &self.depth) > 0.0 { /* fill */ }
    }
}
```

Separately, when the **best price crosses** your resting order, you are filled regardless of queue state (`nopartialfillexchange.rs:242-312`): if the best ask falls to or below your resting buy, the market has moved through you and you are done. The code has a nice performance detail here — it iterates whichever set is smaller, the price ladder between old and new best, or the open-order map (`:253-254`, `:289-290`).

Order acceptance is where several honest venue rules live (`nopartialfillexchange.rs:314-434`):

- A buy limit priced at or above the best ask is **not** placed. Under `GTX` (post-only) it is **Expired**; under `GTC/FOK/IOC` it immediately **takes** at the best ask. Marketable limits are never allowed to rest.
- A taker fill sets `maker = false` and executes at the *opposing best*, whereas a maker fill executes at *your own price* (`nopartialfillexchange.rs:178-183`). Fee models later branch on that same `maker` flag.
- `FOK`/`IOC` that cannot take are Expired, not rested.
- **Modify resets queue position.** If the price changed or the quantity increased, `ack_modify` performs cancel-then-new, which re-seeds `front_q_qty` to the whole level (`nopartialfillexchange.rs:468-514`). Only a pure quantity *decrease* keeps your place. This matches real matching-engine behaviour and is the kind of rule a naive simulator silently gets wrong.

`PartialFillExchange` (`reference/repos/hftbacktest/hftbacktest/src/backtest/proc/partialfillexchange.rs:39-77`) relaxes the third condition: at equality, the fill quantity is `min(is_filled(), leaves_qty)`, and the remainder stays resting as `PartiallyFilled` with lot-size rounding on the leftover (`:208-245`):

```rust
order.exec_qty = exec_qty;
order.leaves_qty -= exec_qty;
if (order.leaves_qty / self.depth.lot_size()).round() > 0f64 { Status::PartiallyFilled } else { Status::Filled }
```

Both files state their own unrealism plainly in their docstrings — "Regardless of the quantity at the best, liquidity-taking orders will be fully executed at the best. Be aware that this may cause unrealistic fill simulations if you attempt to execute a large quantity" (`nopartialfillexchange.rs:58-62`). This kind of self-disclosure is rare and is a large part of the quality verdict.

An L3 Market-By-Order variant exists (`queue.rs:382-1128`) where no estimation is needed at all — market-feed orders and backtest orders live in one real `VecDeque` per price tick, and your order fills when the market-feed order *behind* it fills (`fill_market_feed_order`, `queue.rs:974-1077`). It also documents a deliberately conservative doctrine: on a book-clear message, all backtest orders are dropped because queue position information is irrecoverable (`queue.rs:455-470`). Irrelevant to cTrader, but the doctrine — *when you lose the information the model depends on, drop the position rather than pretend* — generalises.

#### 4. Latency modelling

Three latencies, named and separated (`reference/repos/hftbacktest/docs/latency_models.rst:12-25`): **feed** latency (exchange→you), **order entry** latency (you→matching engine), **order response** latency (matching engine→you).

Feed latency is not a model at all — it is *data*. Every `Event` carries both timestamps (`reference/repos/hftbacktest/hftbacktest/src/types.rs:314-331`):

```rust
pub struct Event {
    pub ev: u64,          // flags, including EXCH_EVENT (1<<31) and LOCAL_EVENT (1<<30)
    pub exch_ts: i64,     // when it happened at the exchange
    pub local_ts: i64,    // when it arrived at my machine
    pub px: f64, pub qty: f64, pub order_id: u64, pub ival: i64, pub fval: f64,
}
```

Order latency is a two-method trait (`reference/repos/hftbacktest/hftbacktest/src/backtest/models/latency.rs:14-20`) with two implementations: `ConstantLatency` (`:22-55`) and `IntpOrderLatency` (`:97-274`), which **linearly interpolates between recorded real latency samples**. The sample format is three timestamps per row (`latency.rs:57-69`): `req_ts` (you sent), `exch_ts` (engine processed), `resp_ts` (you received). The documented way to collect them is operationally trivial and directly copyable: *"You can collect the latency data by submitting unexecutable orders regularly"* (`docs/latency_models.rst:48`) — i.e. place a limit far from market, log the three timestamps, cancel it.

If you have no order-latency data, there is a bootstrap: `generate_order_latency` synthesises it from *feed* latency by an affine map, `entry = mul_entry * feed_latency + offset_entry` (`reference/repos/hftbacktest/py-hftbacktest/hftbacktest/data/utils/feed_order_latency.py:20-99`), resampled to 1 s. Crude, and admitted to be crude, but it means you are never stuck with zero.

The mechanism that makes latency *bite* is the order bus (`reference/repos/hftbacktest/hftbacktest/src/backtest/order.rs`). Orders are not delivered; they are **appended to a queue with a delivery timestamp** and only handed over when the clock reaches it:

```
order.rs:139-156   request():  exch_recv_ts = local_ts + entry_latency  -> to_exch bus
order.rs:92-96     respond():  local_recv_ts = exch_ts + response_latency -> to_local bus
order.rs:34-47     append():   timestamp = timestamp.max(latest_in_bus)   // monotonicity enforced
```

That `.max(latest_in_bus)` is a deliberate simplification, documented in the comment: real REST-based crypto venues can reorder requests, but the sim forces FIFO. Worth knowing as a stated limitation rather than a bug.

Rejection is encoded as **negative latency** (`latency.rs:78-86`, `order.rs:147-152`): if the recorded `exch_ts` is zero (venue overloaded, dropped the order), the model returns `-latency`, and the caller interprets the sign as "rejected, and here is how long until you find out". Ingenious and compact; see "What to avoid" for why QMF should not copy it.

#### 5. The two-clock replay — the strongest structural idea in the project

The same data file is consumed by **two independent processors with two independent clocks**:

- The simulated exchange (`nopartialfillexchange.rs:525-527`) accepts an event only if `event.is(EXCH_EVENT)`, and stamps it at `exch_ts`.
- The strategy-facing local model (`reference/repos/hftbacktest/hftbacktest/src/backtest/proc/local.rs:284-286`) accepts an event only if `event.is(LOCAL_EVENT)`, and stamps it at `local_ts`.

Each maintains its **own** `MarketDepth`. The strategy's book is therefore always the stale one. There is no code path by which the strategy can read the exchange's book. Lookahead is structurally impossible rather than merely discouraged.

When an event's two orderings disagree — event A happened first at the exchange but arrived second locally — the row is **split into two rows**, one flagged `EXCH_EVENT` only and one flagged `LOCAL_EVENT` only, so that each stream stays monotone in its own clock (`reference/repos/hftbacktest/py-hftbacktest/hftbacktest/data/validation.py:53-136`, `correct_event_order`; described in `docs/data.rst:204-239`). A companion validator refuses data that violates the invariant (`validation.py:139-152`):

```python
if np.sum(np.diff(data['exch_ts'][exch_ev]) < 0) > 0:  raise ValueError('exchange events are out of order.')
if np.sum(np.diff(data['local_ts'][local_ev]) < 0) > 0: raise ValueError('local events are out of order.')
```

And a third utility detects the pathology of **negative feed latency** (local clock ahead of exchange clock, i.e. broken time sync) and offsets the whole file to remove it (`validation.py:15-50`, `correct_local_timestamp`).

The scheduler that drives all this is 106 lines (`reference/repos/hftbacktest/hftbacktest/src/backtest/evs.rs`): four timestamp slots per asset — `LocalData`, `LocalOrder`, `ExchData`, `ExchOrder` — and `next()` is a linear scan for the minimum (`evs.rs:43-63`). The main loop pops the earliest of the four, forever (`reference/repos/hftbacktest/hftbacktest/src/backtest/mod.rs:755-863`). Deterministic, single-threaded, trivially auditable. This is the same shape as QMF's planned `qmf.runtime` kernel and is worth reading as a 100-line existence proof that it need not be complicated.

#### 6. Accounting, fees, asset types

- `State::apply_fill` (`reference/repos/hftbacktest/hftbacktest/src/backtest/state.rs:37-46`) is nine lines: position, balance, fee, trade count, volume, value. Fee is delegated to a `FeeModel`; notional is delegated to an `AssetType`.
- `FeeModel` (`reference/repos/hftbacktest/hftbacktest/src/backtest/models/fee.rs:47-153`) is a 2×3 matrix: `{CommonFees(maker,taker), DirectionalFees(+buyer,+seller)}` × `{TradingValue, TradingQty, FlatPerTrade}`. `DirectionalFees` exists for stamp-duty-style venues.
- `AssetType` (`reference/repos/hftbacktest/hftbacktest/src/backtest/assettype.rs`) is two implementations, `LinearAsset` and `InverseAsset`, each just `amount()` and `equity()` — 54 lines total to cover both linear and inverse crypto contracts.
- **There is no financing/funding/swap line anywhere.** Equity is `balance + contract_size * position * price - fee` (`assettype.rs:28-30`). For a project doing perpetual futures this is a real omission; for QMX it confirms the module map's Novel Idea #8 (financing as a P&L line from day one) is genuinely unaddressed prior art.

#### 7. The configuration surface — relevant to Mubarak's Simulator UI

The Python builder composes five orthogonal pluggables (`reference/repos/hftbacktest/py-hftbacktest/src/lib.rs:164-500`):

```
BacktestAsset()
  .data(...).tick_size(...).lot_size(...)
  .linear_asset(1.0)                      # or .inverse_asset(...)
  .intp_order_latency(files, offset)      # or .constant_latency(entry, resp)
  .power_prob_queue_model(3.0)            # or .risk_adverse_queue_model() / .log_prob... / .l3_fifo...
  .no_partial_fill_exchange()             # or .partial_fill_exchange()
  .trading_value_fee_model(maker, taker)  # or .trading_qty... / .flat_per_trade...
```

Every choice is a **named model plus a small set of numeric parameters** — serialisable, hashable, renderable as a UI form. That is precisely what QMF's result key needs as its `venue_model_id`.

The runtime interface is identical between backtest and live (`reference/repos/hftbacktest/hftbacktest/src/types.rs:936-962`, one `Bot` trait) — the same strategy source runs both. But note the **contrast with QMF's chosen design**: hftbacktest is *pull*-based. The strategy body is `while hbt.elapse(10_000_000) == 0:` — the strategy asks for time to pass. QMF has committed to a *push* kernel that dispatches events to handlers (`00-...-module-map.md` Ring 6). Both achieve backtest≡live; the pull model is friendlier to numba and to a market maker's fixed requote cadence, the push model is friendlier to bar-close strategies and to LLM-authored components that must not contain a loop. QMF's choice is right for QMX; this is noted so the difference is deliberate rather than accidental.

One genuinely borrowable oddity: `elapse_bt()` — *"Elapses time only in backtesting. In live mode, it is ignored"* (`types.rs:938-951`). It exists so a strategy can charge itself for its own compute time, which is real in live and free in a backtest.

#### 8. Quality verdict, with the reservations

**Strengths.** Trait boundaries are narrow and correct — `QueueModel` is four methods, `LatencyModel` is two, `FeeModel` is one, `AssetType` is two. Each exchange model's docstring states its own falsehoods up front (`nopartialfillexchange.rs:39-63`, `partialfillexchange.rs:39-77`, `docs/order_fill.rst:8-18`). The two-clock design makes an entire bug class unrepresentable. The data-validation utilities show a project that has been bitten by real data and wrote the check down. The README's thesis (`README.rst`, "Why Accurate Backtesting Matters — Not Just Conservative Approach") argues that *pessimism is also a form of inaccuracy* — a position most retail backtesting content never reaches.

**Reservations, and they are real:**

- **Test coverage is thin where it matters most.** 27 `#[test]` functions in the entire Rust tree. The queue-model tests (`queue.rs:1130-1366`) cover only the L3 FIFO path — `fill_by_crossing` and `fill_in_queue`. The `ProbQueueModel` advance formula at `queue.rs:203`, which is the most consequential line in the project and the one every backtest result depends on, has **no unit test at all**. Its own roadmap lists "Increase documentation and test coverage" as open (`ROADMAP.md`, Others).
- **Liberal `unsafe`.** The order bus wraps its `VecDeque` in `Rc<UnsafeCell<..>>` with raw deref on every access (`order.rs:9`, `:20-67`); the scheduler uses `get_unchecked` and a `mem::transmute::<usize, EventIntentKind>` (`evs.rs:45`, `:57`); the main loop uses `get_unchecked_mut` per event (`mod.rs:777`, `:800`, `:822`, `:845`). Justifiable in a hot loop, but it is performance debt paid in safety, and it is not a trade QMX needs to make.
- **`unreachable!()` on `Side::None | Side::Unsupported` in roughly a dozen places** (`queue.rs:634`, `:730`, `:771`, `:871`, `:968`, `:1075`, `:1124`; `fee.rs:85`, `:128`). Any malformed input becomes a panic, not a typed error.
- **The Python layer is a liability pattern, not a model.** `py-hftbacktest/hftbacktest/binding.py` is 2,390 lines of numba `@jitclass`-style wrappers over raw `voidptr`s, with the entire Bot API duplicated four times (HashMap/ROIVector × backtest/live) — see the four near-identical method blocks at `binding.py:650-984`, `:1093-1424`, `:1612-1946`, `:2055-2386`. That is copy-paste at scale, driven by numba's inability to do dynamic dispatch. QMF must not imitate it.
- **No financing/swap concept** (see §6), and no session/weekend-gap concept — reasonable for 24/7 crypto, absent for FX.
- **Single-primary-author risk**, mitigated by 4.4k stars and an active issue tracker but not eliminated.

---

## Mental models worth borrowing

| Idea | Where in hftbacktest | Why for QMF | How QMF implements it |
|---|---|---|---|
| **Touching a price is not filling at it.** A resting limit fills unconditionally only when price trades *through* it; at exact equality the fill is a *modelled probability*, never a certainty. | `nopartialfillexchange.rs:139-162` (three-way `Ordering` match); `docs/order_fill.rst:28-38` (strict `>` on the trade-price line, `&&` on the equality line) | This is *the* retail backtest bug. "The bar's low equals my limit, therefore filled" inflates every mean-reversion and every limit-entry strategy QMX will ever test. The `Level`+`Trigger` formula is limit-entry-heavy by construction, so QMX is maximally exposed to it. | `qmf.sim.FillModel` exposes `fill_at_touch_prob ∈ [0,1]`, default **0.0** (nothing fills on a touch). A resting buy limit at P fills unconditionally only when a quote tick's **ask** prints strictly below P. When the ask prints exactly P, draw against `fill_at_touch_prob` using the run's registered seed. On bar data (no ticks), equality is never a fill — the bar must have traded through. Register the probability in `venue_model_id` so results are keyed to it. |
| **Ship the conservative model; earn the relaxation with live data.** The library's default extreme (`RiskAdverse`) advances your queue *only* on real trades; every relaxation is opt-in and parameterised. | `queue.rs:63-96` (`RiskAdverseQueueModel::depth` is literally `front.min(new_qty)`); the `Power`/`Log` families at `queue.rs:219-330` are the opt-in relaxations | QMX has an LLM-agent search loop. An optimistic default fill model means agents will discover strategies that exist only in the simulator, and spend real split budget doing it. The pessimistic default is the only safe starting point when the searcher is tireless. | `qmf.venue_model` ships **one** fill model by default, the pessimistic one. Relaxations are separate named `VenueModel` instances with their own ids. A `Confluence` backtested under a relaxed model records that in its result key and cannot be compared against a conservative-model result — the ids differ, so `qmf.registry` treats them as different claims. |
| **The fill model has a free parameter, and that parameter is *fitted to live results*, not guessed.** The stated method: trade small, plot backtest and live equity/position on one chart, tune the queue model until they agree. | `docs/debugging_backtesting_and_live_discrepancies.rst:1-36` (the whole doc); the tunable is `PowerProbQueueFunc::n` at `queue.rs:221-240`; `README.rst` "Why Accurate Backtesting Matters" | This is the module map's Novel Idea #4 ("close the slippage loop") arrived at independently by a project that actually trades. It converts backtest fidelity from a constant guessed once into a **measured, improving quantity** — and it is the only thing that makes a prop-firm attempt defensible. | `qmf.sim.FillModel` parameters (`fill_at_touch_prob`, the slippage distribution, the requote rate) are **fitted**, not configured: `qmf.metrics` records realised fill price vs. intended price per live fill, conditioned on session and event proximity per `qmf.data.micro`; a fitting routine re-estimates the parameters weekly and writes a new `venue_model_id`. Old results keep pointing at the old id. Add one operator report: backtest-vs-live equity on one axis. |
| **Two timestamps per event, and *two replays of the same tape* — the sim reads one clock, the strategy reads the other.** Each keeps its own market state; there is no code path from the strategy to the exchange's view. | `types.rs:314-331` (`exch_ts`/`local_ts`); `types.rs:186-189` (`EXCH_EVENT`/`LOCAL_EVENT` flags); `nopartialfillexchange.rs:525-527` vs `local.rs:284-286` (the two filters); `mod.rs:755-863` (both driven from one event set) | QMF's `Provenance` already *has* the two fields (`00-...-module-map.md` Ring 0). hftbacktest shows how to make them **load-bearing** rather than decorative: if the simulator reads `ts_event` and the strategy reads `ts_init`, lookahead stops being a thing you test for and becomes a thing that cannot be expressed. This is the cheapest possible enforcement of the module map's single most-repeated idea. | `qmf.runtime` dispatches to `SimBroker` on `ts_event` order and to the strategy on `ts_init` order, from one merged event set. `qmf.data.facts.as_of(t)` uses `known_at`, the strategy's clock. The strategy holds its own `MarketView`; `SimBroker` holds the venue's. They are different objects and the type system does not connect them. Same mechanism gates news/calendar facts. |
| **Split a row into two rows when its two clocks disagree — and refuse data that violates monotonicity in either clock.** | `validation.py:53-136` (`correct_event_order` duplicates the row, flagging one `EXCH_EVENT` and one `LOCAL_EVENT`); `validation.py:139-152` (`validate_event_order` raises); `docs/data.rst:209-239` | QMX is recording its own tick stream from day one (module map Novel Idea #6), and a tick archive with a broken ordering invariant silently corrupts every backtest that ever reads it. The check is ~10 lines and can run at ingest, when the fix is still free. | `qmf.data.ingest` terminates every adapter in this check alongside its `pandera` schema check: `ts_event` monotone over event-ordered rows, `ts_init` monotone over arrival-ordered rows, `ts_init >= ts_event`. Violations quarantine the partition rather than land it. Record the per-partition result in the sha256 manifest. |
| **Negative feed latency means your clocks are broken, not that you have a time machine.** Detect it, measure the worst case, offset the file, and say so out loud. | `validation.py:15-50` (`correct_local_timestamp`, including the `print('local_timestamp is ahead of exch_timestamp by', -latency)`); `docs/data.rst:219-223` | Mubarak's tick recorder runs on a Windows research box and a Linux VPS with no PTP. `ts_init < ts_event` will happen. Silently keeping such rows means the strategy sees ticks before the venue produced them — a lookahead bug that no amount of `Provenance` discipline catches, because the discipline is correct and the *data* is wrong. | `qmf.data.ingest` computes `min(ts_init - ts_event)` per partition. If negative, quarantine, log the magnitude, and require an explicit dated operator decision to offset — never silently. Also run NTP on the VPS and record clock offset as a fact in `qmf.data.facts`. |
| **Latency is a journey on a timestamped bus, not a slippage constant. Entry and response are separate legs, and the market moves in between.** | `order.rs:139-156` (`request()` → `exch_recv_ts = local_ts + entry`); `order.rs:92-96` (`respond()` → `local_recv_ts = exch_ts + response`); `order.rs:34-47` (monotonic bus); `latency.rs:14-20` (the two-method trait) | For QMX this is mostly *cheap insurance* rather than a live concern — 30-300 ms on a retail cTrader link is irrelevant to an M15 confluence. It matters intensely in exactly three places: stop-loss execution during fast moves, news spikes, and rollover. Those are also the three places prop-firm accounts die. And retrofitting a bus into a sim that fills instantly is expensive. | `qmf.sim.SimBroker` never fills synchronously. Orders go onto a delivery-timestamped queue; the sim clock delivers them. `LatencyModel` has `entry()` and `response()` as separate methods from the start, even if v1 returns constants. Feed latency is data, from `ts_init - ts_event`. |
| **Collect real latency by submitting unexecutable orders on a schedule.** Three timestamps per sample: sent, engine-processed, received. | `docs/latency_models.rst:48` (the practice); `latency.rs:57-69` (`OrderLatencyRow` — the whole schema is three `i64`s); `latency.rs:170-274` (interpolate between samples) | Free, and it is the only way `LatencyModel` ever becomes honest. Same argument as the module map's "ingest before consumers": every day not collecting is a day permanently lost. It doubles as a cTrader connectivity heartbeat and as evidence for a broker complaint. | A VPS cron places a limit ~200 pips from market on the smallest lot, records `(req_ts, exch_ts, resp_ts)` from the `ProtoOAExecutionEvent`, cancels it, appends to a Parquet partition in `qmf.data.lake`. Ships with `qmf.broker.ctrader`, before any strategy exists. Also record `resp_ts` for *fills* separately — fill notification latency is what a stop-loss actually experiences. |
| **Buys fill at the ask, sells fill at the bid — and the maker/taker distinction chooses *which* price the fill records.** | `nopartialfillexchange.rs:178-183` (maker → own price, taker → `exec_price_tick`); `:334-340`, `:372`, `:391-397`, `:429` (takers execute at `best_ask_tick`/`best_bid_tick`) | Retail FX sims run off a single close series or a mid series and then wonder why live underperforms by exactly one spread per round trip. On a 0.8-pip EURUSD spread and a 10-pip target, that is 16% of gross edge — enough to invert a strategy's sign. It also makes the module map's Novel Idea #3 (refuse a confluence whose edge is smaller than its spread) computable inside the sim rather than only as a pre-check. | `qmf.sim` fills every buy at the ask and every sell at the bid, from stored two-sided quote ticks — never from mid, never from a single series. `qmf.data.lake` stores bid and ask as separate columns on every tick. Bar data carries bid-OHLC plus a spread series; a bar-based sim reconstructs the ask side rather than assuming a constant spread. |
| **Marketable limits never rest; post-only marketable limits are rejected, not silently converted.** And a modify that changes price or increases size loses your place. | `nopartialfillexchange.rs:322-342` (buy at/above best ask: `GTX` → `Expired`, `GTC/FOK/IOC` → immediate take); `:468-514` (`ack_modify` = cancel + new unless quantity strictly decreased) | These are `VenueModel` rules, not fill-model rules, and they are exactly the class of thing an LLM-authored `Trigger` will get wrong — "place a limit at the current price" is a natural thing for an agent to emit and a nonsensical thing to simulate as a resting order. cTrader has its own version of each rule. | `qmf.venue_model` owns them and both `SimBroker` and `qmf.broker.ctrader` consult the same object, so the adapter conformance suite tests them once. A marketable limit is a typed `VenueRejection` with a named code, surfaced to the agent through `qmf.errors`, not a silent conversion. |
| **Fill state is `exec_qty` / `leaves_qty` / `exec_price` with a lot-size-rounded remainder — even when v1 never partially fills.** | `partialfillexchange.rs:208-245` (the remainder arithmetic and the `PartiallyFilled` status); `state.rs:37-46` (`apply_fill` consumes exactly these fields) | Retail FX partial fills are rare but not absent (large size, thin hours, prop accounts with size). The *field shape* costs nothing now and touches the ledger, every report and every stored result if retrofitted — the same argument the module map makes for the `financing` column. | `qmf.model.Fill` and `Order` carry `exec_qty`, `leaves_qty`, `exec_price`, `status ∈ {..., PartiallyFilled, ...}` from v1. `SimBroker` may always fill fully; the *types* permit partial, so the ledger and metrics never need to change. |
| **`req` (pending request) is a separate field from `status` (venue state), and a second request while one is in flight is a typed rejection.** | `local.rs:193-194`, `:222-223` (`if order.req != Status::None { return Err(OrderRequestInProcess) }`); `local.rs:106-133` (reconciling a response against local state, including the rejection path that restores the pre-modify price/qty) | The double-cancel and cancel-while-filling races are the two ways a live trading loop loses money without any strategy being wrong. QMF's three-tier outcome vocabulary already anticipates this; hftbacktest shows the minimum state needed to enforce it, and that the *same* enforcement belongs in the simulator so the race is discoverable in backtest. | `qmf.model.Order` carries both `req` and `status`. `qmf.broker` rejects a second in-flight command with a named `OperationFailed` code. The adapter conformance suite tests the race against `SimBroker` and cTrader identically. `qmf.bms` reads `req` when computing exposure, so an in-flight order counts against limits. |
| **Charge the strategy for its own thinking time — a sim-only clock advance, ignored live.** | `types.rs:938-951` (`elapse_bt`: *"Elapses time only in backtesting. In live mode, it is ignored"*) | An LLM-authored `Confluence` with a dozen `Confirmation` components is not free to evaluate. Live, the order leaves at bar-close + compute + network. In a naive sim it leaves at bar-close exactly. On fast bars that difference is the whole trade. Costs one number. | `qmf.runtime` measures wall-clock per strategy dispatch in *live* and records it as a fact; `qmf.sim` replays the measured distribution as a clock advance before the order reaches `SimBroker`. Ties into the same live→sim calibration loop as slippage. |
| **A venue configuration is a small set of orthogonal named models with numeric parameters — serialisable, hashable, form-renderable.** | `py-hftbacktest/src/lib.rs:217-500` (the `BacktestAsset` builder: asset type × latency model × queue model × exchange model × fee model × tick/lot size) | This is directly the shape of Mubarak's Simulator UI ("backtest engine + Book + conditions via UI") *and* of the `venue_model_id` component in QMF's result key. One structure serves the human form and the reproducibility hash. | `qmf.venue_model.VenueModel` is a frozen dataclass of named sub-model choices plus parameters; `venue_model_id = sha256(canonical_json(...))`. The Simulator UI renders its fields directly. Changing any fill parameter changes the id, so old results do not silently become claims about the new model — the same trick `confluence_id` already plays. |
| **When you lose the information a model depends on, drop the position — do not pretend.** | `queue.rs:455-470` (on a book-clear message, *all* backtest orders are cleared, with a written justification that queue position is irrecoverable and this deliberately differs from real exchange behaviour) | QMX's equivalents are the weekend gap, the rollover window, a feed disconnect, and a data-partition quarantine. The tempting behaviour is to carry the resting order across the discontinuity; the honest behaviour is to void it and record why. | `qmf.sim` voids resting orders across any interval where the tick stream has a documented gap, and `qmf.metrics` reports voided-order count as a data-quality statistic, not silently. `qmf.data.micro`'s weekend-gap and rollover-window detection supplies the boundaries. |

---

## What to avoid

- **Do not build a queue-position model for cTrader.** There is no queue. A retail CFD broker is your counterparty; your limit order sits on the broker's book, not a shared one, and no depth or trade-print feed exists to estimate a position within it. Every quantity-based mechanism in `queue.rs` — `front_q_qty`, `cum_trade_qty`, the `Power`/`Log` probability families, `is_filled` going negative — models information QMX will never have. Porting it would produce a model whose parameters cannot be identified from data, which is worse than a crude model, because it looks rigorous. (cTrader's Open API does expose depth quotes for some brokers, but they are broker-dependent, aggregated, and **not available historically** — so they cannot inform a backtest even where they exist live.)
- **Do not port the L3 machinery** (`queue.rs:332-1128`, `proc/l3_local.rs`, `proc/l3_nopartialfillexchange.rs`) — it needs a per-order Market-By-Order feed. Nor `depth/fuse.rs` (1,361 lines merging multiple depth streams by per-level timestamp), `depth/roivectormarketdepth.rs`, or the snapshot/clear protocol. All are order-book reconstruction, and QMX has no order book.
- **Do not copy "negative latency means rejection."** `latency.rs:78-86` and `order.rs:147-152` overload a single signed integer with a mode flag. It is compact and it is a trap: every consumer must remember the convention, and a sign error becomes a silently wrong fill time rather than a crash. QMF has already chosen better — a typed `outcome ∈ {ACCEPTED, REJECTED, DENIED_LOCALLY, UNKNOWN}` (`00-...-module-map.md` Ring 0/5). Keep it; return latency and outcome as separate values.
- **Do not copy the maker/taker fee dichotomy as the primary fee axis.** `fee.rs` is built around maker rebates versus taker fees, which is a crypto/exchange structure. Retail FX pays *spread* (already in the data, if you store bid and ask) plus a per-lot commission, and owes **swap/rollover**, which hftbacktest has no concept of at all (`assettype.rs:28-30`, `state.rs:37-46` — equity has no financing term). `TradingQtyFeeModel` is the closest analogue to per-lot commission; take that shape and add financing as a first-class line, per module-map Novel Idea #8.
- **Do not imitate the Python layer.** `py-hftbacktest/hftbacktest/binding.py` duplicates the entire Bot API four times across 2,390 lines (`:650-984`, `:1093-1424`, `:1612-1946`, `:2055-2386`) because numba cannot dispatch dynamically. QMF is a Python framework whose whole design premise is deep modules and narrow interfaces; this is the opposite, and it exists for a constraint QMX does not have.
- **Do not treat "it has a queue model" as meaning "it is validated."** The `ProbQueueModel` advance formula at `queue.rs:203` — the line every non-L3 backtest result in the project flows through — has no unit test. The only queue tests exercise the L3 FIFO path (`queue.rs:1130-1366`). Whatever QMF builds for the at-touch fill decision must arrive with property tests from day one: monotonicity in the parameter, correct behaviour at both extremes, and the invariant that a strictly-pessimistic model never fills more than a relaxed one on the same data.
- **Do not adopt the pull-based `while hbt.elapse(...)` strategy loop.** It suits numba and a market maker's fixed requote cadence. It puts a loop inside the strategy, which is precisely what `qmf.spec` exists to prevent — an LLM agent filling a typed schema must not be authoring control flow. QMF's push-kernel choice is correct; this is recorded so the divergence stays deliberate.
- **Do not carry over the `unsafe`/`unreachable!()` habits.** `Rc<UnsafeCell<VecDeque>>` with raw deref on every access (`order.rs:9-67`), `mem::transmute` in the scheduler (`evs.rs:57`), `get_unchecked_mut` per event (`mod.rs:777-845`), and ~a dozen `unreachable!()` panics on malformed `Side` (`queue.rs:634`, `:730`, `:771`, `:871`, `:968`, `:1075`, `:1124`; `fee.rs:85`, `:128`). These buy nanoseconds QMX does not need and cost the typed-error discipline QMF has committed to.
- **Do not assume the two-clock replay is free at the storage layer.** `correct_event_order` allocates `data.shape[0] * 2` rows and can genuinely emit close to double (`validation.py:72`). On a multi-year FX tick archive that matters. QMX's better path: store each tick **once** with both timestamps, and let the *scheduler* present it twice — the split only needs materialising when the two orderings actually disagree, which for a low-latency single-venue feed is rare.
- **Do not read this project's precision as transferable confidence.** Its own README argues correctly that over-pessimism is a form of inaccuracy — but that argument is made for a venue with a full order book and trade prints, where the honest model is *knowable*. In retail FX the honest model is genuinely uncertain, and until the live-vs-backtest comparison has been run on real fills, the pessimistic default is the defensible one. Adopt the calibration loop, not the confidence that precedes it.

---

## Cross-references into the existing record

- Confirms and sharpens **Novel Idea #4** (`00-qmf-synthesis-module-map.md`) — "close the slippage loop." hftbacktest arrived at the same conclusion independently and supplies a method: one tunable parameter in the fill model, fitted against live equity, plotted side by side.
- Confirms **Novel Idea #2** — the simulator as an ordinary adapter. hftbacktest's `Bot` trait is one interface over `Backtest` and `LiveBot` (`types.rs:936-962`), and it works; the strategy source is unchanged between them.
- Supplies a concrete mechanism for **Idea one** of the synthesis (every fact carries two times): not just the fields, but *two consumers reading different fields*, which is what makes the invariant enforceable rather than aspirational.
- Independently corroborates the **`10` §7.2 finding** that "LEAN *simulates* slippage and nobody *measures* it back": hftbacktest measures order latency back (via collected samples) but likewise never measures *fill quality* back into the fill model — the calibration is manual, by eye, on a chart. Closing that automatically is still open ground for QMX.
- Adds to **Ring 5 `qmf.venue_model`**: the five-orthogonal-pluggables shape (asset type × latency × fill × exchange rules × fees) is a directly usable interface sketch, and the fact that it serialises to a UI form *and* to a reproducibility hash resolves an open question about how the Simulator UI and the result key relate.
- Leaves **financing/swap** exactly where the module map left it: unaddressed by prior art, still QMX's own work.
