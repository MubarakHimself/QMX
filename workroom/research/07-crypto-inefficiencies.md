# 07 — Crypto Scan: Inefficiencies, ccxt, Hummingbot, and What Crypto Will Demand From QMF

**Area:** Crypto (direction-level only — lighter than other research areas)
**Date:** 2026-08-17
**Purpose:** Make sure QMF V1's design (forex/cTrader first) does not *block* crypto later. Not a crypto design document.

---

## In plain words

Crypto is not a different trading skill; it is a different **plumbing** problem. The money-making ideas that have real published research behind them are boring and mechanical: collect the "funding" payment that crypto perpetual contracts force one side to pay the other, capture the gap between spot price and futures price, and exploit the fact that the same coin trades at slightly different prices on different exchanges. Academic work says these gaps have been large — carry above 10% a year on average, sometimes over 40% — but also that they are shrinking, and one recent paper shows the carry strategy's risk-adjusted return going *negative* in 2025. So crypto is a real opportunity, not a free one, and it decays.

The practical lesson for QMF today is about **shape, not strategy**. Forex through cTrader gives you one broker, a fixed list of pairs, fixed contract sizes, market hours, and a weekend. Crypto gives you many venues at once, thousands of markets that appear and disappear weekly, a different "smallest tradeable step" per market, no weekends, no closing bell, and a stream of live data pushed over a websocket rather than fetched on request. On top of that, every exchange counts your API requests differently and bans your server's IP address — not your account — when you go over.

If QMF V1 hardcodes any of the forex assumptions — one broker, one account, prices as floats, five-day weeks, "market is closed" logic, instrument details baked into config files — crypto will require a rewrite. If instead QMF treats "which venue", "what are this market's rules", "how many requests am I allowed", and "when is the market open" as *data the adapter supplies* rather than facts the framework knows, crypto becomes a new adapter rather than a new framework.

Nothing below asks you to build crypto now. It asks for roughly six seams to be left open.

---

## Findings

### 1. The documented inefficiencies (with primary sources)

#### 1.1 Perpetual futures funding — the best-documented crypto anomaly

The canonical academic treatment is **"Fundamentals of Perpetual Futures"**, He, Manela, Ross & von Wachter, arXiv:2212.06888 (latest version v6, 2024-08-21) — https://arxiv.org/abs/2212.06888. It derives no-arbitrage prices for perpetuals in frictionless markets and pricing bounds under trading costs. Verified claims from the abstract: perpetuals are "not guaranteed to converge to the spot price"; the funding rate is paid periodically from longs to shorts "proportional to this difference"; empirical deviations from no-arbitrage prices "are larger than those in traditional currency markets", "comove across cryptocurrencies", and "decrease over time"; an implied arbitrage strategy "yields high Sharpe ratios".

Mechanism, from the venue's own docs (Binance, https://www.binance.com/en/support/faq/detail/360033525031):
- Funding Rate = [Average Premium Index + clamp(Interest Rate − Premium Index, 0.05%, −0.05%)] / (8 / N)
- Default interest rate component 0.01% per funding interval.
- Default settlement every 8h at 00:00 / 08:00 / 16:00 UTC — **but** Binance switches to hourly settlement under extreme volatility, and since 2026-01-02 reverts to 4-hour intervals when |funding| ≤ 0.025% for 16 consecutive cycles.
- Caps are margin-linked: Cap = 0.75 × Maintenance Margin Ratio, Floor = −0.75 × MMR; ±0.3% for BTCUSDT, up to ±2% on other contracts.
- Funding is transferred **directly between traders**, only if the position is open at the settlement timestamp.

OKX independently confirms that funding intervals are *not* a constant: settlement periods of 8h / 4h / 2h / 1h exist, frequency **escalates automatically one level when the funding rate hits its cap or floor at settlement**, and reverts to the contract default only if every settlement in the preceding 12 consecutive hours was within ±0.20% — effective 2026-04-14 (https://www.okx.com/en-us/help/okx-to-enable-automatic-updates-for-funding-fee-settlement-period). OKX also normalises by an 8/N factor so daily-equivalent cost is comparable across cycles.

**Design consequence, load-bearing:** funding interval is per-market, mutable at runtime, and venue-specific. It cannot be a constant in code or config.

#### 1.2 Basis / carry

**BIS Working Paper No 1087, "Crypto Carry"**, Schmeling, Schrimpf & Todorov, April 2023, revised October 2025 — https://www.bis.org/publ/work1087.htm. Verified: carry (futures minus spot) "can reach exceptionally high levels, sometimes exceeding 40% per annum"; averages above 10% annually, "much larger than the carry of other financial assets such as equities, fixed income, currencies and commodities". Attributed to (a) demand from smaller trend-chasing investors seeking leveraged exposure and (b) limited arbitrage capital due to regulatory and margin frictions. Evidence of **market segmentation** between crypto venues and TradFi; traditional rate differentials explain little. Crucially: "a high crypto carry predicts future price crashes" and coincides with a rise in the price of crash-risk insurance.

**Decay is documented.** Borri, Liu, Tsyvinski & Wu, "Cryptocurrency as an Investable Asset Class: Coming of Age", arXiv:2510.14435 (v4, 2026-03-21) — https://arxiv.org/abs/2510.14435 — states verbatim: *"Over the full sample, which goes from 2020 to 2025, the annualized Sharpe ratio of the cryptocurrency carry is 6.45. Beginning in 2024, the Sharpe ratio falls to 4.06, and it turns negative in 2025."*

Applied/practitioner-grade evidence: **"Exploring risk and return profiles of funding rate arbitrage on CEX and DEX"**, Werapun et al., *Blockchain: Research and Applications* 7(4), DOI 10.1016/j.bcra.2025.100354 (open access) — https://www.sciencedirect.com/science/article/pii/S2096720925000818. Verified from the abstract: 60 arbitrage scenarios across Binance, BitMEX, ApolloX, Drift on BTC/ETH/XRP/BNB/SOL; best case "115.9% over six months while limiting the maximum drawdown to 1.92%" (Drift XRP, 7× leverage); weak correlation with HODL for XRP. Treat the headline number as a best-of-60 selection, not an expectation.

#### 1.3 Cross-exchange / cross-country arbitrage

**Makarov & Schoar, "Trading and Arbitrage in Cryptocurrency Markets"**, *Journal of Financial Economics* 135(2), 2020, 293–319 — open PDF: https://researchonline.lse.ac.uk/id/eprint/100409/1/Cryptocurrency_Markets_JFE_final_v4.pdf. Verified findings: large recurrent arbitrage opportunities across exchanges; deviations "much larger across than within countries" and smaller between cryptocurrencies, "highlighting the importance of capital controls for the movement of arbitrage capital"; deviations comove and widen during bitcoin appreciation; a common component of signed volume explains ~80% of bitcoin returns.

Updated to 2025 by Borri et al. (arXiv:2510.14435): across **510 BTC–fiat pairs on 165 centralized exchanges in 49 currencies**, verbatim — *"In the 2014–2025 sample, the 10th and 90th percentiles of Bitcoin price discounts are –1.8% and 3.7%, respectively. These figures remain virtually unchanged in the post-2020 period (–2.1% and 3.5%). Moreover, discounts are highly persistent, with a half-life of roughly 1.1 weeks in both samples."*

**Reading:** the persistent leg of cross-exchange dislocation is a *capital-mobility* story (fiat rails, capital controls, KYC), not a latency story. A solo operator with one VPS is not going to win the latency version. This matters for QMF: cross-venue arb needs multi-account/multi-venue *inventory* modelling, not a faster tick loop.

#### 1.4 Listing effects

Blockchain Research Lab working paper, "Exploring Market Reactions to Exchange Listings of Cryptocurrencies" — https://www.blockchainresearchlab.org/wp-content/uploads/2019/10/Exploring-Market-Reactions-to-Exchange-Listings-of-Cryptocurrencies-BRL-working-paper3.pdf (also on ResearchGate: https://www.researchgate.net/publication/335690724_Market_Reaction_to_Exchange_Listings_of_Cryptocurrencies). Reported figures: ~327 exchange listings; average abnormal return ~5.7% on listing day and ~9.2% over the [−3, +3] window; effects strongly exchange-dependent, up to ~25.5% on listing day for a few exchanges.

**UNVERIFIED:** PDF text extraction failed in this session (binary fetch, no local poppler). The numbers above come from search-engine extraction of that PDF and a ResearchGate abstract, not from my own read of the paper. Verify before any strategy relies on them. Related peer-reviewed follow-up exists (e.g. *Economics Letters*, "Market reactions to crypto-specific announcements", https://www.sciencedirect.com/science/article/abs/pii/S0165176525001429) — abstract not read in full.

**Reading:** listing effects are an *event-driven, news-ingestion* strategy, not a price-series strategy. It needs an announcement feed and sub-minute reaction. Structurally very different from everything else here — note it as a seam requirement (exogenous event source), not a V1 target.

#### 1.5 Weekend / session effects — weak, contested

Evidence is mixed and I would not build on it. "Bitcoin and the day-of-the-week effect", *Finance Research Letters* — https://www.sciencedirect.com/science/article/abs/pii/S1544612317307894 (abstract only; full text not read). Later work reports lower weekend volatility/volume, midweek peaks in liquidity commonality, and an Oeconomia Copernicana hourly event-study arguing the day-of-week effect is "not persistent daily phenomena but driven by limited intraday intervals" and is "localized and asset-specific" (https://oeconomia.pl/index.php/oc/article/view/2091). A 2025 preprint "Bitcoin's Weekend Effect: Returns, Volatility, and Volume (2014–2024)" exists on ResearchGate (https://www.researchgate.net/publication/396418897) — **UNVERIFIED**, preprint, not read.

**Reading for QMF:** the *design* consequence is real even if the anomaly is not — crypto has no session boundary, no weekend gap, no exchange holiday. Any QMF component that assumes "the market closes" must be venue-supplied behaviour, not framework truth.

---

### 2. The ccxt ecosystem — real coverage and real caveats

**Maintenance status: strongly maintained.** GitHub API, checked 2026-08-17: 43,651 stars, 759 open issues, `pushed_at` 2026-08-17T11:13:05Z, created 2017-05-14, MIT licence, not archived, default branch `master` (https://api.github.com/repos/ccxt/ccxt). Coverage claim on the repo/homepage: "100+ cryptocurrency and prediction-market exchanges", languages JavaScript/TypeScript/Python/PHP/C#/Go/Java (https://github.com/ccxt/ccxt, https://docs.ccxt.com/). A "CCXT Certified" subset is called out (Binance, OKX, Gate, KuCoin, Bybit, Bitget, HTX, MEXC, Crypto.com, CoinEx, HashKey, WOO X, WOOFI PRO, Hyperliquid, BitMEX, BingX) — i.e. **coverage breadth ≠ coverage quality**; the long tail is community-maintained.

#### 2.1 The unified market structure — this is the thing QMF should study

From `python/ccxt/base/types.py` (https://raw.githubusercontent.com/ccxt/ccxt/master/python/ccxt/base/types.py), verbatim field list of `MarketInterface`:

```python
id, numericId, uppercaseId, lowercaseId, symbol, base, quote, baseId, quoteId,
active, type, subType, spot, margin, swap, future, option, stock, prediction,
contract, settle, settleId, contractSize, linear, inverse, quanto,
expiry, expiryDatetime, strike, optionType,
taker, maker, percentage, tierBased, feeSide,
precision: Precision, marginModes, limits: MarketLimits, created, info, outcomes
```

```python
class Precision(TypedDict):   amount: Num; price: Num; cost: Num
class MinMax(TypedDict):      min: Num;    max: Num
class MarketLimits(TypedDict): amount|cost|leverage|price|market : MinMax | None
```

Funding is a first-class unified type:

```python
class FundingRate(TypedDict):
    symbol, info, timestamp, fundingRate, datetime, markPrice, indexPrice,
    interestRate, estimatedSettlePrice, fundingTimestamp, fundingDatetime,
    nextFundingTimestamp, nextFundingDatetime, nextFundingRate,
    previousFundingTimestamp, previousFundingDatetime, previousFundingRate,
    interval
class FundingRateHistory(TypedDict): info, symbol, fundingRate, timestamp, datetime
```

Note `interval: Str` — ccxt models funding interval as *per-market data*, confirming §1.1.

`Position` carries `contracts, contractSize, notional, leverage, collateral, entryPrice, markPrice, liquidationPrice, marginMode, hedged, initialMargin, maintenanceMargin, marginRatio, unrealizedPnl, realizedPnl, ...` — note `hedged` and `marginMode`: crypto accounts can hold simultaneous long and short in the same symbol.

#### 2.2 Precision is a tick size, not a digit count

From the manual (https://docs.ccxt.com/docs/manual#precision-mode), verbatim:

> `TICK_SIZE` – almost all exchanges use this precision mode. In this mode, the numbers in `market_or_currency['precision']` designate the minimal precision fractions (floats) for rounding or truncating.
> `SIGNIFICANT_DIGITS` – ... some exchanges (`bitfinex` and maybe a few other) implement this mode ...
> `DECIMAL_PLACES` (**DEPRECATED, CCXT no longer uses this mode anywhere**) ...

And, verbatim:

> The user is required to stay within all limits and precision! ... Order `cost` (`amount * price`) >= `limits['cost']['min']` ... The above values can be missing with some exchanges that don't provide info on limits from their API or don't have it implemented yet.

Rounding modes `ROUND` / `TRUNCATE`; padding `NO_PADDING` / `PAD_WITH_ZERO`; constants confirmed in `decimal_to_precision.py` (https://raw.githubusercontent.com/ccxt/ccxt/master/python/ccxt/base/decimal_to_precision.py): `TRUNCATE=0, ROUND=1, ROUND_UP=2, ROUND_DOWN=3, DECIMAL_PLACES=2, SIGNIFICANT_DIGITS=3, TICK_SIZE=4, NO_PADDING=5, PAD_WITH_ZERO=6`.

**This is the single most transferable lesson for QMF.** Forex via cTrader lets you get away with "5 digits, 100k units". Crypto does not: the quantiser is a per-market `Decimal` tick, and the *validity* of an order is a conjunction of six inequalities plus two precision constraints, all of which can be `None`.

#### 2.3 Data-quality caveats (all quoted from the ccxt manual, https://docs.ccxt.com/docs/manual)

- Capability is introspected, not assumed: `exchange.has['fetchOHLCV']` is `true` / `false` / `'emulated'`. The manual's example exchange structure shows `'fetchStatus': 'emulated'` alongside booleans. `timeframes` "is only populated when `has['fetchOHLCV']` is true".
- Gaps are normal: *"The returned list of candles may have one or more missing periods, if the exchange did not have any trades for the specified timerange and symbol. ... That is considered normal."*
- History depth is limited: *"**There's a limit on how far back in time your requests can go.** Most of exchanges will not allow to query detailed candlestick history (like those for 1-minute and 5-minute timeframes) too far in the past."* Workaround is your own REST-polled store.
- Partial last bar: *"Note that the info from the last (current) candle may be incomplete until the candle is closed (until the next candle starts)."*
- Non-deterministic defaults: *"If `since` is not specified the `fetchOHLCV` method will return the time range as is the default from the exchange itself. ... without specifying `since` the range of returned candles will be exchange-specific."*
- All timestamps are integer **UTC milliseconds**, everywhere, in all unified methods.
- Symbols are opaque: *"Attempting to parse the symbol string is highly discouraged, one should not rely on the symbol format, it is recommended to use market properties instead."* The same market is `btcusd` / `XBTUSD` / `XXBTZUSD` / `42` across venues.
- Rate limiting is your problem: *"**The user is required to implement own rate limiting or leave the built-in rate limiter enabled to avoid being banned from the exchange**."* `enableRateLimit` defaults `true`; `rateLimit` is a per-exchange millisecond spacing.

Independent data-integrity warning from the academic side (Borri et al., arXiv:2510.14435, verbatim): *"parts of the historical crypto data—especially in early years—may reflect manipulation or unreliable reporting, including alleged price manipulation on Mt. Gox in 2013, inflated or 'artificial' trading volume reported by some exchanges, and exchange-managed wash trading concentrated on 'unregulated' exchanges."*

#### 2.4 ccxt Pro (websockets) — the streaming assumptions

From https://docs.ccxt.com/docs/pro-manual (raw: https://raw.githubusercontent.com/ccxt/ccxt/master/wiki/ccxt.pro.manual.md):

- Public: `watchOrderBook(ForSymbols)`, `watchTicker(s)`, `watchTrades(ForSymbols)`, `watchOHLCV(ForSymbols)`, `watchBidsAsks`, `watchLiquidations`, `watchStatus`. Private: `watchBalance`, `watchOrders(ForSymbols)`, `watchMyTrades`, `watchPositions`, `watchMyLiquidations`, **`watchFundingRates`**. Plus `createOrderWs` / `cancelOrderWs` / `editOrderWs` and `unWatch*`.
- Deltas + local state: *"Updates coming from the exchange are also often called deltas ... those updates will contain just the changes between two states."* ccxt Pro merges into a local snapshot; caches default to 1000 entries, configurable via `exchange.options`.
- Reconnection is built in: *"Upon a critical exception, a disconnect or a connection timeout/failure, the next iteration of the tick function will call the watch method that will trigger a reconnection."* And: *"CCXT Pro applies the necessary rate-limiting and exponential backoff reconnection delays."*
- Latency guidance: for OHLCV, *"recalculating the 2nd order data from 1st order data on your own may be much faster"* — i.e. watch trades and build bars locally.

---

### 3. Hummingbot — what a purpose-built crypto connector layer reveals

**Maintenance status: strongly maintained.** GitHub API 2026-08-17: 19,486 stars, 145 open issues, `pushed_at` 2026-08-16T18:23:46Z, Apache-2.0, not archived (https://api.github.com/repos/hummingbot/hummingbot).

#### 3.1 Connector anatomy (https://hummingbot.org/connectors/connectors/architecture/)

| Component | Role |
|---|---|
| `Exchange` / `Derivative` (required) | inherits `ConnectorBase`; `Derivative` also inherits `PerpetualTrading`. Owns the trackers below. |
| `ConnectorAuth` (optional) | builds auth headers/payloads for restricted REST + WS channels; CEX-only (DEX auth is wallet-based). |
| `OrderBookTracker` (required) | holds `OrderBook` per pair; applies **snapshots + delta messages** from the data source. |
| `OrderBookTrackerDataSource` (required) | streams/parses/queues market data; handles **timestamp/nonce sequencing** so deltas apply in order. For perpetual connectors it **also maintains funding information**. |
| `UserStreamTracker` + `UserStreamTrackerDataSource` (optional) | account state: balances and order updates via private websocket. |
| `InFlightOrder` | "stores all details pertaining to the current state of an order". |
| `ClientOrderTracker` | owns `InFlightOrder`s, fires `trigger_event`, handles update/error paths. |
| `TradeFeeSchema` / `TradeFeeBase` / `AddedToCostTradeFee` / `DeductedFromReturnsTradeFee` | maker/taker percent fees, flat fees, **fee token**, and two different semantics for how a fee hits the position. |

Three things this architecture *asserts* about crypto venues:
1. **Websocket-first is not optional.** Order books are maintained as local state fed by deltas with sequence numbers; REST is for snapshots and fallback. Private order/balance state also arrives by push.
2. **Order identity must be client-side.** `InFlightOrder` + `ClientOrderTracker` exist because exchange order IDs arrive late, out of order, or after a reconnect. You need your own client order ID and a reconciliation loop.
3. **Fees are not one number.** Fee currency differs from quote currency (BNB/FTT-style discounts); "added to cost" vs "deducted from returns" changes realised size.

#### 3.2 Per-market trading rules (https://raw.githubusercontent.com/hummingbot/hummingbot/master/hummingbot/connector/trading_rule.pyx)

`TradingRule` fields: `trading_pair, min_order_size, max_order_size, min_price_increment, min_base_amount_increment, min_quote_amount_increment, min_notional_size, min_order_value, max_price_significant_digits, supports_limit_orders, supports_market_orders, buy_order_collateral_token, sell_order_collateral_token`.

Note what forex never forces you to model: **separate base and quote amount increments**, a **notional minimum**, a **significant-digits price rule**, per-side **collateral tokens**, and per-market **order-type support flags**.

#### 3.3 Rate limiting as a first-class object (https://raw.githubusercontent.com/hummingbot/hummingbot/master/hummingbot/core/api_throttler/data_types.py)

```python
@dataclass
class LinkedLimitWeightPair:  limit_id: str; weight: int = DEFAULT_WEIGHT
class RateLimit:             limit_id: str; limit: int; time_interval: float;
                             weight: int = 1; linked_limits: Optional[List[LinkedLimitWeightPair]]
@dataclass
class TaskLog:               timestamp: float; rate_limit: RateLimit; weight: int
```

Used per venue, e.g. Binance constants declare a pool `RateLimit(limit_id=REQUEST_WEIGHT, limit=6000, time_interval=ONE_MINUTE)` and per-endpoint entries linking into it with weights (`LinkedLimitWeightPair(REQUEST_WEIGHT, 2)` etc.), with `WS_HEARTBEAT_TIME_INTERVAL = 30` (https://github.com/hummingbot/hummingbot/blob/master/hummingbot/connector/exchange/binance/binance_constants.py).

Why this shape and not a simple sleep: from Binance's own docs (https://developers.binance.com/docs/binance-spot-api-docs/rest-api/limits) —
- *"Each route has a `weight` which determines for the number of requests each endpoint counts for."*
- **"The limits on the API are based on the IPs, not the API keys."**
- Order-count limits are per **account**, tracked separately via `X-MBX-ORDER-COUNT-*`; weight via `X-MBX-USED-WEIGHT-*`.
- HTTP **429** = rate-limit exceeded, honour `Retry-After`. HTTP **418** = auto-ban for continuing after 429s; ban duration scales **"from 2 minutes to 3 days"** for repeat offenders.

So a venue budget is: multiple *named pools*, weighted per endpoint, some scoped to IP and some to account, with a hard ban on violation. This is genuinely different from a broker connection with one FIX session.

#### 3.4 Connector economics (a maintenance warning)

https://hummingbot.org/exchanges/ lists 50+ exchanges / 318 tracked connectors across three families — **CLOB CEX** (spot + perp), **CLOB DEX** (Hyperliquid, Lighter), **Gateway DEX** (AMMs/aggregators) — and an explicit funding tier system: DIY Governance (free, "responsible for ongoing maintenance updates" to stay in releases), Bounty Management ($10,000+, one year maintenance), Foundation Sponsorship ($50,000+). Read that as: **unsponsored connectors rot.** Same risk applies to any ccxt long-tail exchange.

---

## What QMF should copy / avoid

### Copy — six seams to leave open in V1 (cheap now, expensive later)

1. **`Decimal` everywhere in the order/price/quantity path; never `float`.**
   Crypto tick sizes are `TICK_SIZE` fractions like `0.00001`, and cost minimums are multiplicative. Float rounding in the quantiser produces rejected orders. This is a V1 decision because retrofitting `Decimal` through a codebase is a total rewrite of the execution path.

2. **An `InstrumentSpec` / market-metadata port that the adapter supplies at runtime — not config, not constants.**
   Minimum viable field set, modelled on ccxt `MarketInterface` ∪ Hummingbot `TradingRule`:
   `venue, symbol, base, quote, settle, kind {spot|perp|future|forex_cfd}, active, contract_size, linear/inverse, price_increment, amount_increment (base), quote_amount_increment, min_amount, max_amount, min_notional, maker_fee, taker_fee, fee_currency, fee_is_percentage, tier_based, expiry|None, funding_interval|None, leverage_limits|None`.
   Every field must be **nullable** — ccxt says plainly these "can be missing with some exchanges". Forex fills a small subset; crypto fills more. V1 only needs to *read* what cTrader gives it, but the type must be the wider one.
   Refresh must be re-callable (`load_markets`-style): crypto markets are added and delisted continuously.

3. **Instrument identity is `(venue, symbol)`, and symbols are opaque tokens.**
   Do not encode meaning in the symbol string (no `symbol[:3]` base extraction, no regex). ccxt's guidance is explicit. And cross-exchange arbitrage — the strategy with the strongest empirical record (Makarov & Schoar; Borri et al.) — is *structurally impossible* if the framework assumes one venue.

4. **Session/calendar is a venue-supplied policy object, not framework truth.**
   Forex: 5-day week, session boundaries, weekend gap, rollover time. Crypto: 24/7, no gap, but a *funding calendar* of discrete settlement timestamps whose interval is per-market and mutable at runtime (Binance 8h→1h under stress; OKX 8/4/2/1h with automatic escalation, effective 2026-04-14). Give QMF a `TradingCalendar`/`SessionPolicy` interface with `is_open(t)`, `next_event(t)`, `bar_boundaries(...)` and let the forex adapter return the boring answer. **Do not** hardcode "skip weekends", "no bars on Saturday", or "day starts at 17:00 NY".

5. **Data-feed abstraction that is push-shaped, with pull as a special case.**
   Both ccxt Pro and Hummingbot are delta/snapshot streaming with sequence numbers, local book state, and automatic reconnection with exponential backoff. cTrader Open API is already streaming, so this costs nothing in V1 — just don't write a `while True: fetch_bars()` loop as the framework's only ingestion shape. Also plan for **bars built from trades locally** (ccxt Pro's own latency advice) and for **the current bar being incomplete** — a strategy contract that only fires on *closed* bars avoids an entire class of look-ahead bugs in both asset classes.

6. **A named-quota throttler at the adapter boundary, and client-generated order IDs.**
   Copy Hummingbot's `RateLimit` / `LinkedLimitWeightPair` shape: multiple named pools, weighted endpoints, per-IP *and* per-account scopes. Copy `InFlightOrder` + `ClientOrderTracker`: QMF generates the client order ID, tracks state locally, and reconciles after any disconnect. Both are useful for cTrader today and mandatory for crypto later. The Linux VPS deployment makes IP-scoped bans (418, up to 3 days) an operational risk worth designing for.

**Bonus (near-free):** make **funding/financing a first-class P&L component** distinct from commission and spread. Forex has swap/rollover; crypto has funding. If P&L is `entry/exit + commission` only, crypto's entire primary edge is invisible to the backtester and the reporting layer. Add a `financing` (or `carry`) line item now.

### Avoid

- **Do not make ccxt the framework's abstraction.** Wrap it behind QMF's own port as one adapter among several. Its return types are `TypedDict`s full of `Num`/`Str`/`Any` with an untyped `info: dict`; letting that leak into the strategy surface destroys the constrained API that LLM agents are supposed to author against — the whole point of QMF.
- **Do not model precision as "number of decimal places."** `DECIMAL_PLACES` is explicitly deprecated in ccxt and "no longer used anywhere". Tick size is the primitive; digit count is derived.
- **Do not assume one account / one position per symbol / long-or-short.** ccxt `Position` has `hedged` and `marginMode`; cross-venue delta-neutral carry needs simultaneous opposite legs on different venues. Even in V1, a position keyed by `(venue, account, symbol, side)` costs nothing extra.
- **Do not assume the quote currency is the fee currency or the settle currency.** Inverse perps settle in the base coin; fee discounts are paid in exchange tokens; Hummingbot needs per-side `collateral_token`.
- **Do not build a crypto adapter, a funding data type, or a cross-exchange router in V1.** Nothing above requires crypto code now. Leaving the seam is the whole deliverable.
- **Do not treat crypto edges as durable.** BIS documents 10%+ average carry; Borri et al. document the same carry's Sharpe going negative in 2025. Any QMF design that assumes a strategy stays live indefinitely (no decay monitoring, no automatic disable) is wrong for crypto specifically.
- **Do not plan around long-tail venues.** Both ccxt (certified vs non-certified) and Hummingbot (sponsored vs DIY) tell you the same thing: only the top ~15 venues are reliably maintained. A crypto plan should assume 1–3 venues.

---

## Open questions

1. **Operator decision — venue count.** Is crypto-in-QMX one exchange (simplest: perps on one venue, funding harvest only) or ≥2 (needed for the cross-exchange dislocation edge, and it multiplies custody, KYC, fiat-rail and reconciliation work)? This determines whether `(venue, symbol)` identity and multi-account position keys are *needed* or merely *nice*.
2. **Operator decision — custody and jurisdiction.** The persistent cross-exchange discount is a capital-controls/segmentation phenomenon (Makarov & Schoar). Whether Mubarak can actually access the segmented venues where the spread lives is a legal/banking question, not a code question, and it decides whether cross-exchange arb is even on the table.
3. **Spot vs perp-only.** Funding harvest classically needs long spot + short perp (two instruments, two balances, transfers). Perp-only variants (long perp on venue A, short perp on venue B) avoid spot custody but add basis risk between venues. Which shape QMF must support changes the position model.
4. **Does QMF V1 need a `financing`/`carry` P&L line, or can it be added later?** My recommendation is now (cheap); needs a decision because it touches the backtest ledger and reporting schema.
5. **Backtest data source for crypto — unresolved.** ccxt's `fetchOHLCV` history depth is explicitly limited and gap-prone, and academic sources warn about wash-traded volume on unregulated venues. Does QMX buy tick/trade data (Tardis.dev, Kaiko, CryptoTick — none evaluated here) or self-collect from websockets on the VPS from day one? Self-collection means the seam must exist *before* the strategy work. **Needs its own research pass.**
6. **Is Hummingbot a build-on or a study-only?** It is Apache-2.0 and actively maintained, and its connector layer is exactly the hard part. Whether QMF should ever *import* Hummingbot connectors (heavy, Cython, opinionated event loop) versus copy their design was not evaluated. Recommend study-only until a crypto decision exists.
7. **UNVERIFIED items to close before use:** the listing-effect abnormal-return figures (§1.4 — PDF not read directly), Bybit's per-contract funding intervals (fetch timed out; only Binance and OKX verified from primary docs), and the weekend-effect preprint (§1.5). None are load-bearing for the seam recommendations.
8. **Does the constrained LLM-authoring surface need to express "funding" at all?** If agents will eventually write strategies, a funding-carry strategy needs a vocabulary (`funding_rate`, `next_funding_time`, `basis`) in the strategy API. Deciding *not* to expose it is fine — but it should be a decision, not an accident.
