# Spec: Fills, Slippage & Fees — How an Order Becomes a Costed Fill

Reverse-engineering spec for QMX. Feeds **GAP-0048** directly. Sources read read-only:
- Jesse v3.0.6 — `C:/Users/Mubarak/Desktop/QMX/workroom/reference/repos/jesse/jesse/`
- LEAN engine (C#) — sparse clone at `.../scratchpad/lean-engine/` (paths below are relative to that root)

Mechanism-understanding only. **No third-party code is proposed for reuse.** All QMX
requirements below map to QMF law: exact-integer money, UTC-ns time, typed refusals,
result labels carrying world = live/replay/simulated, config-driven runs (a Book/BMS
materializes a config the CLI consumes), logged-during / saved-at-completion into an
unbiased pass/fail ledger.

This spec covers the part QMX most lacks: **retail-forex/CFD fill has no reference
implementation in either engine.** Jesse has **no slippage at all** and a **single flat
fee**; LEAN has a rich fill/slippage/fee stack but its slippage models are equity/volume
oriented and **explicitly refuse or no-op on Forex/CFD**. QMX must therefore borrow the
*interfaces* from LEAN and *invent* the forex-CFD model catalog neither ships.

---

## 1. Feature claim (verbatim, with URL)

**LEAN — Trade fills** (https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/trade-fills/key-concepts):
> "If you trade US Equities, our built-in fill models can fill your orders at the
> official opening and closing auction prices."
> Fill models "work with the slippage model to add slippage into the fill price."
> "in live trading, your orders can partially fill" but "in backtests, the pre-built
> fill models assume orders completely fill."

Built-in fill models named: `EquityFillModel`, `FutureFillModel`, `FutureOptionFillModel`,
`ImmediateFillModel` (base for all other asset classes, including Forex/CFD).

**LEAN — Slippage** (https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/slippage/key-concepts):
> "Slippage is the difference between the fill price you expect to get for an order and
> the actual fill price."
> "Slippage models model slippage to make backtest results more realistic."
> Models named: `VolumeShareSlippageModel`, `NullSlippageModel`, `CustomSlippageModel`.
> **The page gives no forex/CFD slippage details** — ABSENT for FX in the marketing.

**LEAN — Transaction fees** (https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/transaction-fees/key-concepts):
> "LEAN uses transaction fee models in backtesting to model the live trading fees you
> would incur with the strategy."
> "The default brokerage model is the `DefaultBrokerageModel`, which set the
> ConstantFeeModel with **no fees for Forex, CFD, and Crypto assets** and sets the
> InteractiveBrokersFeeModel for the remaining asset classes."
> An `OrderFee` is "a cash amount in a currency."

**Jesse — Backtest** (https://docs.jesse.trade/docs/backtest.html):
> "Jesse's backtest engine is the most accurate available, simulating market conditions
> as faithfully as possible including fees, and order types."

Jesse markets **fees** as part of realism. It does **not** market slippage — and indeed
ships none (verified in §2). Fee rate is a single per-exchange config value
(`env.exchanges.{exchange}.fee`), e.g. `0.001` spot / `0.0006` futures
(`jesse/info.py:53,67`). ABSENT: any maker/taker split, minimums, per-share, tiers, or
slippage in Jesse.

---

## 2. Mechanism — how the code actually does it

### 2A. LEAN — the fill → slippage → fee pipeline

Three separate contracts, applied in order. Fill decides **whether/at-what-price**;
slippage **adjusts the price**; fee produces a **separate cash charge**.

**(i) Fill model — `IFillModel.Fill(FillModelParameters) → Fill`**
`Common/Orders/Fills/IFillModel.cs:30`. `Fill` wraps a `List<OrderEvent>` (one per leg;
`Common/Orders/Fills/Fill.cs`). The base `FillModel.Fill(...)` is a **switch on
`Order.Type`** dispatching to a per-order-type method
(`Common/Orders/Fills/FillModel.cs:59-127`):

| Order type | Method | Trigger / price rule (from code) |
|---|---|---|
| Market | `MarketFill` → `InternalMarketFill` (`FillModel.cs:273-338`) | Fill at `GetMarketFillPrice` = `prices.Current`, or **bar `Open`** if the order was resting before this bar opened (`FillModel.cs:1080-1091`); then apply slippage. |
| Limit | `LimitFill` → `InternalLimitFill` (`FillModel.cs:670-731`) | Buy fills iff `prices.Low < limit`, price = `min(High, limit)`; Sell iff `prices.High > limit`, price = `max(Low, limit)` — "worse price this bar or the limit." **No slippage added.** |
| StopMarket | `StopMarketFill` (`FillModel.cs:347-398`) | Sell triggers iff `Low < stop`, fill = `min(stop, Current − slip)`; Buy iff `High > stop`, fill = `max(stop, Current + slip)` — worst-case fill. Slippage applied. |
| TrailingStop | `TrailingStopFill` (`FillModel.cs:406-470`) | Same as stop, then re-computes the stop via `TrailingStopOrder.TryUpdateStopPrice(...)` from the bar extreme and `OnOrderUpdated`. |
| StopLimit | `StopLimitFill` (`FillModel.cs:486-557`) | Two-phase: sets `StopTriggered` once the stop is crossed, **then** fills as a limit bounded by the bar (`min(High,limit)` / `max(Low,limit)`) at the closing price. |
| LimitIfTouched | `LimitIfTouchedFill` (`FillModel.cs:576-660`) | Trigger touched by trade High/Low; then fill at `LimitPrice` gated by current **ask/bid**. |
| MarketOnOpen | `MarketOnOpenFill` (`FillModel.cs:739-792`) | Fills at next session `Open` + slippage; refuses if market never closes. |
| MarketOnClose | `MarketOnCloseFill` (`FillModel.cs:800-844`) | Fills at `Close` + slippage once local time reaches the next market close. |
| Combo* | `ComboMarketFill/ComboLimitFill/ComboLegLimitFill` (`FillModel.cs:136-265`) | **All-or-none across legs**: if any leg fails, the whole returned list is empty. |

Two guards recur in every method: **exchange-open check** (`IsExchangeOpen`,
`FillModel.cs:1097-1129,1207+`) and **stale-data guard** — market orders wait or warn if
the latest bar end is older than `Parameters.StalePriceTimeSpan` before `order.Time`
(`FillModel.cs:304-313`); resting order types simply "do not fill on stale data" when
`pricesEndTime <= order.Time` (`FillModel.cs:364,423,506,698`). Every fill starts at
`OrderFee.Zero` and fills the **full quantity** (`fill.FillQuantity = order.Quantity`) —
the marketed "backtests assume orders completely fill." No partial fills.

**Where the spread lives — `GetPrices` (`FillModel.cs:1150-1204`).** This is the single
most important forex detail. `GetPrices(asset, direction)` returns a `Prices` struct
(`Current, Open, High, Low, Close, Time, EndTime` — `Common/Orders/Fills/Prices.cs`) and
is **direction-aware**: for a Sell it takes the **bid**, for a Buy the **ask**, preferring
`Tick` → `QuoteBar` → `TradeBar` (`FillModel.cs:1168-1200`). So in LEAN the bid/ask spread
is modeled **only if the data feed carries quote data**; with trade-only bars there is no
spread and buys/sells fill at the same price. There is **no hour-of-day spread widening**
and **no synthetic spread** — spread is a property of the input data, not the fill model.

**(ii) Slippage — `ISlippageModel.GetSlippageApproximation(asset, order) → decimal`**
`Common/Orders/Slippage/ISlippageModel.cs:28` returns a **cash-per-unit price offset**
that the fill model adds/subtracts from the fill price (buy `+slip`, sell `−slip`;
`FillModel.cs:321-332`). Catalog:
- `NullSlippageModel` — zero. **Default for Forex/CFD** in practice.
- `ConstantSlippageModel(slippagePercent)` — `lastData.Value * pct`
  (`Slippage/ConstantSlippageModel.cs:39-45`). The only model that works without volume.
- `VolumeShareSlippageModel(volumeLimit=0.025, priceImpact=0.1)` —
  `slippagePct = min(qty/barVolume, volumeLimit)² × priceImpact`, times price
  (`Slippage/VolumeShareSlippageModel.cs:57-63`). **Explicitly returns 0 for
  Cfd/Forex/Crypto** because they report no bar volume, logging an error
  (`VolumeShareSlippageModel.cs:44-52`).
- `MarketImpactSlippageModel` — Almgren-style: `σ`, execution time, permanent + temporary
  impact, gaussian noise (`Slippage/MarketImpactSlippageModel.cs:55-82`). **Throws** for
  Forex/Cfd: "not supported as MarketImpactSlippageModel requires volume data"
  (`MarketImpactSlippageModel.cs:57-59`).
- `AlphaStreamsSlippageModel`.

**Net for forex CFD: LEAN's slippage catalog is empty of anything usable** — one no-op,
one percent-of-price, and two that refuse. This is the gap QMX inherits.

**(iii) Fee — `IFeeModel.GetOrderFee(OrderFeeParameters) → OrderFee`**
`Common/Orders/Fees/IFeeModel.cs:11`. `OrderFeeParameters` = `{Security, Order}`
(`Fees/OrderFeeParameters.cs`). `OrderFee` wraps a `CashAmount {Amount, Currency}` and
knows how to `ApplyToPortfolio` (`portfolio.CashBook[Currency].AddAmount(-Amount)`) —
fee is charged in **its own currency**, not forced into account currency
(`Fees/OrderFee.cs:31-48`). `OrderFee.Zero` uses `NullCurrency`. Base `FeeModel` returns
0 USD (`Fees/FeeModel.cs:29-34`). 30+ broker models exist; the two forex-relevant ones:
- **`FxcmFeeModel`** (the retail-forex reference): commission **per 1,000 units of base
  currency** — `0.04` USD/1k for a 7-pair major group, else `0.06` USD/1k;
  `fee = |rate × AbsoluteQuantity / 1000|` (`Fees/FxcmFeeModel.cs:38-49`).
- **`InteractiveBrokersFeeModel`** forex branch: `fee = max(minimumOrderFee,
  |commissionRate × orderValue|)`, with `commissionRate`/`minimum` **tiered by monthly
  USD volume** (`Fees/InteractiveBrokersFeeModel.cs:60-66`, schedule in
  `ProcessForexRateSchedule`). Note this is a **notional-proportional** commission with a
  **per-order minimum** — the shape QMX needs.

**(iv) Where the three combine.** The fill model sets `FillPrice`/`FillQuantity`+slippage;
the brokerage/transaction handler then calls `security.FeeModel.GetOrderFee(...)` and
attaches the `OrderFee` to the `OrderEvent`; the portfolio applies price×qty to holdings
and the fee to the cashbook. The same `FeeModel.GetOrderFee` is *also* called ahead of the
fill by the buying-power/margin models to **reserve** the fee before allowing the order
(`Common/Securities/BuyingPowerModel.cs:151,439`; `CashBuyingPowerModel.cs:153,300`;
`Future/FutureMarginModel.cs:135`). So the fee contract is queried twice: once for margin
admission, once for the actual charge.

**(v) Financing / swap / carry.** LEAN models overnight carry via
**`IMarginInterestRateModel.ApplyMarginInterestRate(MarginInterestRateParameters)`**
(`Common/Securities/IMarginInterestRateModel.cs`). The concrete
`BinanceFutureMarginInterestRateModel` shows the mechanism: on a **funding schedule**
(00:00/08:00/16:00 UTC), `funding = −interestRate × positionValue`, added straight to the
position's cash (`Common/Securities/CryptoFuture/BinanceFutureMarginInterestRateModel.cs:12-46`).
`Equity/ShortMarginInterestRateModel` does the analog for short borrow. **ABSENT: a
forex/CFD daily swap/rollover model** (no triple-swap-Wednesday, no per-symbol long/short
swap points) — CFD/Forex ship holdings + settlement classes but **no dedicated overnight
swap**. QMX must supply this.

### 2B. Jesse — fill inside the candle, flat fee, zero slippage

**Fill = "did the candle touch my price?"** In backtest, `_simulate_price_change_effect`
(`jesse/modes/backtest_mode.py:926-985`) walks the orders resting inside a 1-minute
candle. An order fills iff **`candle_includes_price(candle, order.price)`** —
literally `low ≤ price ≤ high` (`jesse/services/candle_service.py:84-85`). When it fills,
the fill price **is exactly `order.price`** — no slippage, no bar-worst-case, no spread.
This is *optimistic*: if the candle merely wicked through your limit, Jesse gives you that
exact price.

**`split_candle` — intra-candle sequencing** (`candle_service.py:88-150`). When an order
fills mid-candle, the candle is split at the fill price into an "earlier" and "later"
sub-candle (the branch chosen from bullish/bearish + where `price` sits in O/H/L/C). The
earlier part is stored; the loop re-collects still-eligible orders against the *remainder*
and repeats (`backtest_mode.py:940-966`). This is how Jesse orders **multiple fills within
one candle** into a plausible sequence without tick data — QMX's closest reference for
in-bar ordering.

**Gap handling — `_get_fixed_jumped_candle`** (`backtest_mode.py:902-923`). If a candle
opens away from the prior close, the current candle's open (and the relevant wick) is
**stretched back to the previous close** so an order sitting in the gap still fills. Crude
but it prevents gaps from silently swallowing stops.

**Market orders** are queued to `store.orders.to_execute` and drained by
`execute_simulated_market_orders` (`jesse/services/order_service.py:127-135`) — they fill
at the order's carried price, again with no slippage.

**Fee — one flat rate.** `execute_order` sets
`order.fee = fee_rate × (|filled_qty| × order.price)` where `fee_rate =
get_config('env.exchanges.{exchange}.fee')` (`order_service.py:73-77,105-109`). Spot
deducts the fee from the *received asset*: `assets[base] += |qty| × (1 − fee_rate)`
(`jesse/models/SpotExchange.py:89-102`); futures charges settlement currency via
`charge_fee` = `|amount| × fee_rate` (`jesse/models/FuturesExchange.py:85-93`). **One rate
covers maker and taker** — no distinction, no minimum, no tier, no per-lot.

**Partial fills — Jesse actually has them** (unlike LEAN backtest). `execute_order`
caps a `reduce_only` fill to the open position size (`order_service.py:63-71`), and
`execute_order_partially` (`order_service.py:100-135`) fills `filled_qty` with
`PARTIALLY_FILLED` status and pro-rated fee. So on partial fills Jesse > LEAN; on
price realism (slippage/spread) LEAN > Jesse.

**Liquidation** is modeled as a synthetic market order at bankruptcy price when
`candle_includes_price(candle, liquidation_price)` in isolated mode
(`backtest_mode.py:985-1020`).

---

## 3. Jesse vs LEAN — which approach fits QMX and why

| Dimension | Jesse | LEAN | QMX choice |
|---|---|---|---|
| Fill contract | implicit (`candle_includes_price` + `split_candle`) | explicit `IFillModel.Fill(params) → Fill(List<OrderEvent>)`, switch per order type | **LEAN's explicit interface** — a pluggable, per-order-type contract is the "swap a variable, not the tunnel" fit. |
| Fill price realism | exact `order.price` (optimistic) | bar-worst-case (`min(High,limit)` / `max(Low,limit)`), stop worst-of | **LEAN's worst-case** as the honest default; keep Jesse's exact-price as an explicit optimistic label. |
| Intra-candle sequencing | `split_candle` re-loop | none (one slice = one fill pass) | **Adopt Jesse's `split_candle`** idea for deterministic multi-fill ordering without ticks. |
| Spread | none | bid/ask **only if quote data present** (`GetPrices` direction-aware) | **LEAN's direction-aware bid/ask**, *plus* a QMX synthetic-spread model for trade-only data (neither has this). |
| Slippage | none | rich interface, but **all models refuse/no-op on FX/CFD** | **LEAN's `ISlippageModel` interface, empty catalog for FX** → QMX invents the FX catalog. |
| Fee contract | one flat `fee_rate × notional` | `IFeeModel.GetOrderFee → OrderFee(CashAmount)`, per-currency, broker catalog | **LEAN's typed `OrderFee` in its own currency** (maps to QMF exact-integer money); reject Jesse's single-float rate. |
| Forex fee shape | flat % | FXCM per-1k-units; IB `max(minimum, rate×notional)` tiered | **IB shape** (`max(minimum, rate×notional)`) as the general forex commission; FXCM per-1k as an alt. |
| Overnight carry | none | `IMarginInterestRateModel` (funding schedule) — but **no FX swap** | **Adopt the scheduled-application mechanism**; build the missing FX/CFD daily-swap model. |
| Partial fills | yes (`execute_order_partially`, reduce_only cap) | no (backtest fills full) | **Keep partial fills** — QMX targets realistic retail fills; Jesse is the reference here. |
| Money type | float | `decimal` / `CashAmount` | **QMF exact-integer money** — stronger than both. |

Verdict: **QMX takes LEAN's three-contract architecture (fill / slippage / fee as
separate pluggable models), Jesse's intra-candle `split_candle` sequencing and partial-fill
capping, and must originate the forex-CFD content that neither ships** (synthetic spread,
hour-of-day spread, gap fills, daily swap, partial lots).

---

## 4. QMX spec draft — requirements for our own version

Requirements (WHAT), not code design. IDs are local to this spec.

### 4.1 The fill-model interface
- **FILL-1.** A fill model MUST implement one contract:
  `fill(order, market_state) → Fill | NoFill`, where `Fill` carries
  `{fill_price, fill_qty, fee: Money, timestamp_utc_ns, fidelity_label}` and `NoFill`
  is a **typed refusal** carrying a reason code (`market_closed`, `stale_data`,
  `not_triggered`, `insufficient_liquidity`, `all_or_none_leg_failed`). No silent
  zero-fills. (QMF: typed refusals.)
- **FILL-2.** The contract MUST dispatch on order type and cover at minimum: Market,
  Limit, Stop (market), Stop-Limit, Trailing-Stop, Market-on-Open, Market-on-Close, and
  a bracket/OCO grouping. All-or-none groups fail as a unit (LEAN combo semantics).
- **FILL-3.** `market_state` MUST expose direction-aware **bid/ask** when quote data
  exists, and O/H/L/C + `current` + bar `[start,end]` in **UTC-ns**. When only trade
  bars exist, the model MUST obtain the spread from the QMX synthetic-spread model
  (§4.3), never silently fill buy=sell.
- **FILL-4.** Default fill price MUST be **bar-worst-case** (buy limit = `min(high,limit)`,
  sell limit = `max(low,limit)`; stop = worst of stop vs current±slip). An **optimistic
  "exact-price"** mode (Jesse-style) MUST be selectable but MUST stamp a distinct
  fidelity label (§4.5).
- **FILL-5.** Triggering rules MUST match honest OHLC semantics: limit fills only if the
  bar crosses the limit; stop triggers on `low<stop` (sell) / `high>stop` (buy);
  stop-limit is two-phase (trigger latches, then limit). A **stale-data guard** MUST
  refuse resting-order fills when the bar end precedes order submission, and MUST
  refuse/hold market fills beyond a configurable `stale_price_span`.
- **FILL-6.** **Intra-candle sequencing:** when multiple resting orders fall inside one
  bar, the engine MUST fill them in a deterministic order derived by splitting the bar at
  each fill price (Jesse `split_candle` mechanism) so results are reproducible without
  tick data.
- **FILL-7.** **Gap handling:** an order whose price sits in a between-bar gap MUST fill
  at the gapped price (bar open stretched to prior close), not be skipped. Gap fills MUST
  carry a `gap_fill` fidelity marker.
- **FILL-8.** **Partial fills & partial lots:** the model MUST support `filled_qty <
  order_qty`, MUST cap `reduce_only` fills to the open position size, and MUST support
  fractional/partial lot sizing per the instrument's lot step. Each partial fill emits its
  own `Fill` with its own pro-rated fee.

### 4.2 Slippage models (the forex-CFD catalog neither engine ships)
- **SLIP-1.** Slippage MUST be a pluggable model returning a **price offset in Money**
  applied against fill price (buy `+`, sell `−`), kept separate from the spread and the
  fee. It MUST NOT be applied to passive limit fills (LEAN convention) unless explicitly
  configured.
- **SLIP-2.** Catalog (config-selectable per Book/BMS):
  - **Zero** (label = optimistic).
  - **Constant / percent-of-price** (LEAN `ConstantSlippageModel` shape) — the volume-free
    baseline.
  - **Spread-crossing** — slippage = a configurable fraction of the *current* bid/ask
    spread; the retail-FX default (fills consume part/all of the spread).
  - **Gap/volatility** — slippage widens with bar range or realized vol, to model fills
    during news spikes and stop-runs.
  - **Size-tiered** — slippage steps up with order size relative to a notional liquidity
    band (a volume-free stand-in for LEAN's `VolumeShareSlippageModel`, which refuses FX).
- **SLIP-3.** Every slippage model MUST be pure w.r.t. `(order, market_state, params)` and
  reproducible under replay (same seed → same draw for any stochastic term).

### 4.3 Spread model (originated by QMX)
- **SPREAD-1.** A spread model MUST supply bid/ask when the feed lacks quotes, keyed by
  **instrument × hour-of-day (UTC) × session** — spreads widen at rollover / illiquid hours
  and around weekends. Config-driven (a table materialized into the Book/BMS config).
- **SPREAD-2.** When the feed *does* carry quotes, the real spread MUST take precedence and
  the run MUST be labeled higher-fidelity than a synthetic-spread run (§4.5).

### 4.4 Fee & financing models
- **FEE-1.** Fees MUST use a typed contract `order_fee(order, security) → Money` returning
  an amount **in its own currency** (LEAN `OrderFee`/`CashAmount` shape → QMF exact-integer
  money). No float rates.
- **FEE-2.** Catalog: **Zero**; **Flat/percent-of-notional** (Jesse shape); **Per-lot /
  per-1k-units** (FXCM shape); **Notional-proportional with per-order minimum, tiered by
  rolling volume** (IB shape) — the recommended forex-CFD default.
- **FEE-3.** The fee contract MUST be queryable **before** the fill for margin/buying-power
  admission *and* at fill time for the actual charge (LEAN's double-call), returning the
  same amount for the same inputs.
- **FEE-4.** **Financing / swap (daily carry):** a scheduled model MUST apply overnight
  swap to open positions on a configurable schedule, with **per-symbol, per-direction
  (long/short) swap points**, a **triple-swap day** (typically Wednesday) rule, and
  **weekend/holiday** handling. Applied as a Money debit/credit to the position, logged as
  a distinct ledger event (mechanism per LEAN `IMarginInterestRateModel`, content
  originated by QMX). Absence of a swap table MUST be a typed refusal, not a silent zero.
- **FEE-5.** Every cash effect (fill P&L, slippage cost, fee, swap) MUST be **logged during
  the run** and **saved at completion into the ledger** as separately attributable line
  items, so the unbiased pass/fail end result can decompose cost drag.

### 4.5 Fidelity labels (how fidelity attaches)
- **LABEL-1.** Every `Fill` MUST carry a **fidelity label** composed of: world
  (`live` / `replay` / `simulated`), price basis (`quote-real` > `quote-synthetic` >
  `trade-only`), fill basis (`worst-case` vs `optimistic-exact`), and whether
  slippage/fee/swap models were engaged. (QMF: result labels carry world.)
- **LABEL-2.** A run's saved ledger result MUST carry the **lowest** fidelity of any fill
  in it (a single trade-only optimistic fill downgrades the whole run's label), so the
  pass/fail verdict is never flattered by mixed fidelity.
- **LABEL-3.** Labels MUST be machine-comparable so the CLI can refuse to compare Books
  run at different fidelities without an explicit override.

---

## 5. Open questions

1. **Spread table provenance.** Where do per-instrument, per-hour retail-FX spread tables
   come from for `SPREAD-1` — broker tick history, a vendor, or operator-supplied config?
   Without a source, `quote-synthetic` fidelity is only as good as the table.
2. **Swap points source & sign convention.** FEE-4 needs per-symbol long/short swap points
   and the triple-swap weekday, which vary by broker. Operator-supplied table, or derived
   from interest-rate differentials? Confirm the sign convention (carry can be credit).
3. **Optimistic vs worst-case default.** Should QMX default to LEAN worst-case (honest,
   pessimistic) or offer Jesse-exact as an explicit "best-case bound," reporting both as a
   fill-quality band? A two-sided band may serve quant agents better than one number.
4. **Slippage seeding under 12-14 concurrent tasks.** Stochastic slippage (SLIP-3) needs a
   per-task deterministic seed so concurrent runs remain independently reproducible — how
   is the seed derived from the Book/BMS identity?
5. **Partial-fill liquidity model.** FILL-8 allows partial fills, but neither engine models
   *how much* fills without volume data. What volume-free liquidity proxy decides partial
   fill size for retail FX (size-tier bands? spread-implied depth?)?
6. **Margin/liquidation coupling.** Jesse models isolated-mode liquidation at bankruptcy
   price; LEAN routes carry through margin-interest models. How tightly should GAP-0048's
   fill/fee stack couple to the margin/liquidation spec, given swap changes equity daily?
7. **Fee currency conversion timing.** `OrderFee` in its own currency (FEE-1) must convert
   to account currency at *some* rate — fill-time FX rate vs end-of-run? Confirm to keep
   exact-integer money reconciliation deterministic.
