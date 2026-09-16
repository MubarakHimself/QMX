# Worker C — Context, Filter, Confirmation & Indicator Primitives

Candidate dictionary entries for market-context measures, pre-trigger filters,
synchronous/post-trigger confirmations, and continuous conditions. None of
`filter`, `confirmation`, or `confluence` is treated here as an intrinsic
permanent class: all three are possible *bindings* a strategy can assign to any
entry below, and timing eligibility is recorded per entry where meaningful.

Status tags used throughout: `source-stated`, `published-convention`,
`STRATS-standardized`, `inferred`, `unresolved`. Evidence citations are real
URLs located during this wave; they support terminology/definitions only and
are **not** claimed to demonstrate trading edge.

---

## Coverage table

| Family | Entries | Count |
|---|---|---|
| Trend & regime | trend-direction, trend-strength, higher-timeframe-trend-bias, market-regime, moving-average-trend, moving-average-crossover, market-structure-break, range-bound-state | 8 |
| Momentum | momentum, rate-of-change, rsi, macd, stochastic-oscillator, momentum-divergence | 6 |
| Volatility | average-true-range, bollinger-bands, realized-volatility, implied-volatility, donchian-channel, keltner-channel, average-daily-range | 7 |
| Indicator family & operations | moving-average, oscillator, band-envelope, ichimoku-cloud, crossover, indicator-divergence | 6 |
| Session / time-window / higher-timeframe | trading-session, session-overlap, session-open-price, time-of-day-window, day-of-week-window, higher-timeframe-reference | 6 |
| Spread / liquidity / cost / data health | bid-ask-spread, spread-widening-condition, market-depth, slippage, trading-cost, data-health-feed, rollover-swap-cost | 7 |
| Volume / profile / order-flow / DOM | exchange-volume, volume-profile, vwap, order-book-depth, footprint-order-flow, cumulative-delta, absorption, fair-value-gap, order-block, supply-demand-zone, liquidity-sweep, spot-fx-tick-volume | 12 |
| Intermarket / currency / correlation | currency-pair-correlation, dollar-index, currency-strength, intermarket-risk-regime, safe-haven-demand | 5 |
| News / event-state (durable) | economic-calendar-event, news-event-window, news-event-class | 3 |
| Pattern quality / distance / viability | support-resistance, distance-to-level, reward-risk-distance, confluence-count, pattern-quality-grade, timeframe-alignment | 6 |

**Total: 66 entries**

---

## trend-direction

- **Family:** Trend & regime
- **Aliases:** trend, directional bias, higher-high/lower-low structure, market bias
- **Definition:** The dominant direction of price travel over a chosen lookback, usually expressed as up / down / sideways and identified from a sequence of rising or falling swing highs and lows.
- **Boundaries:** Direction is a property of price structure, not of any single indicator; an oscillator reading or a moving-average slope is a *proxy* for it. Do not confuse trend-direction with momentum strength — a market can trend down while a momentum oscillator rises on a pullback.
- **Observable inputs:** OHLC price series; swing-high/swing-low pivots; optionally a moving average or trendline overlay.
- **Recognition semantics:** Compare consecutive swing highs and lows. A sequence of higher highs and higher lows is an uptrend; lower lows and lower highs a downtrend; interleaved/equal pivots a sideways or ranging state. Trendlines and moving-average slope are common shortcuts but must be labelled as proxies, not the definition.
- **Parameters/profiles:** lookback (number of swings or bars) — `unresolved`; pivot-detection strength (e.g. fractal left/right count 2–5) — `published-convention`; minimum bar count for a valid swing sequence — `inferred`.
- **Eligible roles:** context, pre-trigger filter (trade only with trend), confirmation (resumption), invalidation (structure break), exit trigger (trend reversal).
- **Market/data constraints:** Timeframe-relative: a "trend" on M5 may be noise on D1. Requires a decision on which timeframe defines the bias. Works on any OHLC venue (forex and crypto spot included) without special data.
- **Transfer notes:** Fully transferable between forex spot and crypto spot; no venue-specific data needed. Futures/equity trend *definitions* transfer, but their session/halt gaps do not.
- **Evidence/status:** `ontology-seed — needs source evidence` for a single canonical algorithm; the higher-high/lower-low formulation is widely documented in technical-analysis textbooks (e.g. Dow Theory) but no single URL was fixed this wave.
- **Uncertainty/variants:** "Bias" sometimes means a multi-timeframe conclusion, not one-timeframe direction; "structural bias" (ICT/SMC) adds liquidity-sweep context. Pivot-detection thresholds are discretionary and vary by tool.

## trend-strength

- **Family:** Trend & regime
- **Aliases:** trend quality, directional strength, ADX level
- **Definition:** A measure of how strongly directional (vs. flat) price movement is over a lookback, independent of the trend's sign.
- **Boundaries:** Strength is not direction: the ADX line rises whether the trend is up or down. Not the same as momentum (speed of change) nor volatility (size of range) — a market can be volatile but non-trending (low ADX, high ATR).
- **Observable inputs:** OHLC series feeding an ADX-type calculation, or a trend-strength statistic.
- **Recognition semantics:** ADX is the canonical proxy. Rising ADX = strengthening trend; falling ADX = weakening/flattening. Threshold conventions (below ~20 = no trend; above ~25 = strong) are published rules of thumb, not universal laws.
- **Parameters/profiles:** ADX period 14 — `source-stated` (Wilder default); no-trend threshold 20 and strong-trend threshold 25 — `published-convention`; smoothing method (Wilder's) — `source-stated`.
- **Eligible roles:** pre-trigger filter (require a minimum strength before acting), confirmation, regime classifier, exit signal (strength exhaustion).
- **Market/data constraints:** Lagging and smooth; weak at catching very short scalping turns. Same formula applies across forex and crypto spot.
- **Transfer notes:** ADX originates in Wilder's 1978 work for commodities; transfers directly to forex/crypto spot as a price-only statistic with no venue dependency.
- **Evidence/status:** Wilder, *New Concepts in Technical Trading Systems* (1978); Investopedia DMI article https://www.investopedia.com/articles/technical/02/050602.asp
- **Uncertainty/variants:** Thresholds vary (some use 15/20, some 20/25); `+DI`/`-DI` crossings are a separate directional signal frequently conflated with ADX strength.

## higher-timeframe-trend-bias

- **Family:** Trend & regime
- **Aliases:** HTF bias, top-down bias, directional context
- **Definition:** The trend-direction and/or regime read from a timeframe longer than the entry timeframe, used to constrain which setups are eligible on the lower timeframe.
- **Boundaries:** This is a *coordination* primitive (one timeframe conditioning another), not a new kind of trend. It is not a trigger by itself; it narrows the set of acceptable lower-timeframe triggers.
- **Observable inputs:** Two or more OHLC series (higher + lower timeframe), or a single series resampled to the higher timeframe.
- **Recognition semantics:** Evaluate a trend primitive (e.g. trend-direction, moving-average-trend, structure) on the higher timeframe and require agreement with the intended lower-timeframe trade direction. Disagreement marks the setup as counter-trend and typically excluded or down-weighted.
- **Parameters/profiles:** higher-to-lower timeframe ratio (e.g. D1→H1→M15, or H4→M15) — `inferred`, strategy-specific; bias source (structure vs. MA vs. oscillator) — `unresolved`.
- **Eligible roles:** pre-trigger filter, context, confluence weight, invalidation (HTF bias flips).
- **Market/data constraints:** Requires multi-timeframe data for the same instrument; in crypto spot, higher timeframes are continuous (24/7) whereas forex higher timeframes inherit session-based weekly gaps.
- **Transfer notes:** Universally applicable across forex and crypto spot; the *method* transfers, the *specific timeframe ladder* is a strategy decision.
- **Evidence/status:** `ontology-seed — needs source evidence`; multi-timeframe analysis is standard practice but no single canonical URL was fixed.
- **Uncertainty/variants:** Whether "bias" is binary (with/against) or graded (strong/moderate/weak) is unresolved; ratio of timeframes is discretionary.

## market-regime

- **Family:** Trend & regime
- **Aliases:** regime, market state, trending vs. ranging, choppiness regime
- **Definition:** A categorical classification of the current market state — commonly trending, ranging/consolidating, breakout, or high-volatility — intended to select which strategy families are appropriate.
- **Boundaries:** Regime is broader than trend-direction: a range has no direction but is a distinct regime. Regime is a *classification of conditions*, not a specific tradeable event. Do not confuse a regime label with a live directional prediction.
- **Observable inputs:** OHLC; volatility and trend-strength statistics (ATR, ADX); optionally range-detection (e.g. Donchian width, Bollinger width, ADR percentile).
- **Recognition semantics:** Combine signals: ADX below threshold + narrow bands ⇒ ranging; ADX above threshold + directional structure ⇒ trending; band/range breakout ⇒ breakout. Regime detection is explicitly multi-indicator and heuristic; there is no single authoritative algorithm.
- **Parameters/profiles:** thresholds for "narrow/wide" (band-width percentile, ATR percentile) — `unresolved`/`inferred`; classification scheme (2/3/4-state) — `unresolved`.
- **Eligible roles:** context, pre-trigger filter (mean-reversion vs. trend-following gate), regime switch as invalidation.
- **Market/data constraints:** Regime is timeframe-dependent (a range on M5 can be a trend on H1). Crypto spot and forex spot both support it from OHLC alone.
- **Transfer notes:** Fully transferable; no centralized-exchange data required. Regime *switching* frequency differs across markets but the primitive is market-agnostic.
- **Evidence/status:** `ontology-seed — needs source evidence`; the trending/range dichotomy is textbook, but a canonical regime taxonomy is not standardized.
- **Uncertainty/variants:** Many named variants (e.g. "quiet/volatile", "breakout/trend/range"); exact state boundaries are discretionary.

## moving-average-trend

- **Family:** Trend & regime
- **Aliases:** MA trend, price-above-MA, moving-average slope
- **Definition:** Use of a moving average (typically a longer-period SMA/EMA) as a reference for trend: price above and MA rising = up, price below and MA falling = down.
- **Boundaries:** A moving average is a lagging *smoothing* of price, not a direct structural measurement; it is a trend proxy. Distinct from moving-average-crossover (which needs two averages).
- **Observable inputs:** OHLC series; one moving-average line.
- **Recognition semantics:** Compute the MA. Trend is up when close is above a rising MA and down when close is below a falling MA. The slope and price-relative-to-MA conditions are often combined.
- **Parameters/profiles:** MA type (SMA/EMA/WMA) — `published-convention` (EMA common for intraday); period — strategy-specific `inferred` (common references: 20, 50, 200); slope lookback — `unresolved`.
- **Eligible roles:** context, pre-trigger filter (price on correct side), dynamic support/resistance reference, trailing-exit reference.
- **Market/data constraints:** Price-only; no venue restriction. Lag increases with period; poorly suited to very fast scalping as a standalone.
- **Transfer notes:** Directly transferable to forex and crypto spot. Longer periods (e.g. 200) that reference equity calendars transfer only as *bar counts*, not as calendar meaning.
- **Evidence/status:** `published-convention` — moving averages are core technical-analysis material; see e.g. StockCharts ChartSchool moving-average entries. No single URL fixed this wave.
- **Uncertainty/variants:** EMA vs. SMA vs. WMA choice is discretionary; "above a rising MA" vs. "MA slope only" are competing definitions.

## moving-average-crossover

- **Family:** Trend & regime
- **Aliases:** golden cross / death cross, MA cross, dual-MA signal
- **Definition:** A transition event where a shorter-period moving average crosses a longer-period moving average, read as a trend-regime change (up-cross = golden cross; down-cross = death cross).
- **Boundaries:** The crossover is a *lagging event* that often fires after much of the move is done; it is a regime confirmation, not an early trigger. Not the same as price crossing a single MA.
- **Observable inputs:** OHLC series; two moving averages of different periods.
- **Recognition semantics:** Compute fast and slow MAs. Crossover occurs when fast crosses above (golden) or below (death) slow. Directional confirmation depends on slope/alignment; in choppy markets crossovers whipsaw.
- **Parameters/profiles:** fast/slow periods — `published-convention` for 50/200 (daily equities) but `unresolved` for intraday crypto/forex; MA type SMA/EMA — `published-convention`.
- **Eligible roles:** confirmation (post-trigger regime confirmation), pre-trigger filter, trend-following trigger, exit signal.
- **Market/data constraints:** Price-only. The 50/200 daily convention is an equity-index legacy; its meaning does not automatically carry to forex/crypto spot without re-parameterization.
- **Transfer notes:** The *operation* transfers; the *parameters* must be re-derived per market/timeframe and are not portable defaults.
- **Evidence/status:** Investopedia golden/death cross https://www.investopedia.com/ask/answers/121114/what-difference-between-golden-cross-and-death-cross-pattern.asp ; CMC Markets golden/death cross explainer https://www.cmcmarkets.com/en-gb/technical-analysis/golden-cross-and-death-cross-explained
- **Uncertainty/variants:** "Golden/death cross" strictly means the 50/200 daily pair in equity media; generalized crossover means any fast/slow pair. Lag is a documented limitation.

## market-structure-break

- **Family:** Trend & regime
- **Aliases:** break of structure (BOS), change of character (CHoCH), swing break, structure shift
- **Definition:** A decisive price break of a prior swing high (in an uptrend) or swing low (in a downtrend), used to confirm continuation or signal a potential reversal of market structure.
- **Boundaries:** A structure break is a *discrete event* on swing geometry, distinct from an indicator crossover and from a mere wick poke (whether a break counts on close vs. intrabar is a binding decision). Not an order; it is an observable transition.
- **Observable inputs:** OHLC series; swing-high/low pivots.
- **Recognition semantics:** In an uptrend, price closing above the most recent swing high = bullish break; in a downtrend, closing below the most recent swing low = bearish break. CHoCH is the first counter-trend break against the prevailing structure.
- **Parameters/profiles:** close-based vs. intrabar confirmation — `unresolved` (strategy-specific); swing-pivot strength — `inferred`; whether a CHoCH or only a BOS is used — `unresolved`.
- **Eligible roles:** trigger (breakout entry), confirmation (post-trigger), invalidation (opposing structure break), exit.
- **Market/data constraints:** Price-only; timeframe-relative. Works identically in forex and crypto spot.
- **Transfer notes:** Fully transferable. ICT/SMC vocabulary (BOS/CHoCH) originates in retail futures/forex commentary but the geometry is venue-independent.
- **Evidence/status:** `ontology-seed — needs source evidence`; terminology is SMC/ICT-standard but is largely a re-labelling of classical Dow-theory structure.
- **Uncertainty/variants:** BOS vs. CHoCH boundary; intrabar vs. close confirmation; whether wick or body defines the swing extreme. All unresolved.

## range-bound-state

- **Family:** Trend & regime
- **Aliases:** sideways market, consolidation, ranging, chop, no-trend state
- **Definition:** A market state where price oscillates within a horizontal band without a persistent directional swing structure, so trend-following logic is weak.
- **Boundaries:** A range is not a trend and not a single consolidation pattern; it is a *condition*. Distinct from a breakout (the moment the range is resolved). Chop can coexist with high volatility — ranging does not imply calm.
- **Observable inputs:** OHLC; band/range detection (Donchian, Bollinger width, ADR percentile, ADX).
- **Recognition semantics:** Low ADX with bounded price between recent swing extremes; band width narrow/stable; no new highs/lows over N bars. Heuristic, multi-signal.
- **Parameters/profiles:** bars without a new high/low — `unresolved`; ADX threshold — `published-convention` (~<20/25); band-width percentile — `inferred`.
- **Eligible roles:** pre-trigger filter (suppress trend strategies, enable mean-reversion), context, invalidation (range resolves into trend).
- **Market/data constraints:** Timeframe-relative. Crypto spot ranges are continuous; forex spot ranges inherit session pauses.
- **Transfer notes:** Fully transferable; price/volatility only.
- **Evidence/status:** `ontology-seed — needs source evidence`.
- **Uncertainty/variants:** "Range" vs. "chop" vs. "distribution/accumulation" terminology is inconsistent across sources.

## momentum

- **Family:** Momentum
- **Aliases:** MTM, momentum indicator, price velocity
- **Definition:** A measure of the rate/speed of price change over a lookback; the base indicator is the difference between the current price and the price N periods ago.
- **Boundaries:** Momentum is about *speed of change*, not direction persistence (trend) nor range size (volatility). The raw MTM indicator is distinct from its normalized relatives (ROC, RSI, MACD).
- **Observable inputs:** OHLC series (closing prices).
- **Recognition semantics:** MTM = close(t) − close(t−N). Positive = upward momentum, negative = downward; zero-line crossings mark momentum sign changes; magnitude indicates strength.
- **Parameters/profiles:** lookback N (14 common) — `published-convention`; price field (close) — `published-convention`.
- **Eligible roles:** confirmation, trigger (zero-line cross), divergence source, filter.
- **Market/data constraints:** Price-only; no venue restriction. Unit-bound (in price terms), so not comparable across instruments — use ROC for that.
- **Transfer notes:** Directly transferable to forex/crypto spot.
- **Evidence/status:** Wikipedia momentum/ROC https://en.wikipedia.org/wiki/Momentum_(technical_analysis) ; Investopedia ROC https://www.investopedia.com/terms/p/pricerateofchange.asp
- **Uncertainty/variants:** MTM vs. ROC are frequently conflated; some platforms label ROC as "momentum".

## rate-of-change

- **Family:** Momentum
- **Aliases:** ROC, price rate of change
- **Definition:** The percentage change of price over a lookback, normalizing momentum so values are comparable across instruments and timeframes.
- **Boundaries:** ROC is momentum expressed as a percentage; the raw momentum (MTM) is the absolute difference. Do not treat ROC as a bounded oscillator — it is unbounded and has no fixed overbought/oversold band.
- **Observable inputs:** OHLC series (closing prices).
- **Recognition semantics:** ROC = (close(t) − close(t−N)) / close(t−N) × 100. Positive/negative around a zero line; zero-crossings and divergences are the standard readings.
- **Parameters/profiles:** lookback N (e.g. 10–14) — `published-convention`; price field close — `published-convention`.
- **Eligible roles:** confirmation, divergence source, filter, trigger.
- **Market/data constraints:** Price-only; venue-agnostic.
- **Transfer notes:** Directly transferable; percentage form makes cross-market comparison possible.
- **Evidence/status:** Investopedia ROC https://www.investopedia.com/terms/p/pricerateofchange.asp
- **Uncertainty/variants:** Overbought/oversold "levels" (e.g. ±30%) are arbitrary conventions, not intrinsic.

## rsi

- **Family:** Momentum
- **Aliases:** Relative Strength Index, Wilder's RSI
- **Definition:** A bounded momentum oscillator (0–100) comparing average gains to average losses over a lookback, used to flag overbought/oversold conditions and momentum divergences.
- **Boundaries:** RSI is bounded and normalized (unlike ROC). It measures momentum, not trend. Overbought/oversold readings do not mean "sell/buy now" — in strong trends RSI can stay extreme for extended periods.
- **Observable inputs:** OHLC series (closing prices).
- **Recognition semantics:** RSI = 100 − 100/(1+RS), RS = average gain / average loss over N periods. Convention: >70 overbought, <30 oversold. Divergence (price extreme not confirmed by RSI) is a widely cited reversal signal.
- **Parameters/profiles:** period 14 — `source-stated` (Wilder); overbought 70 / oversold 30 — `published-convention` (Wilder's own thresholds); smoothing method — `source-stated`.
- **Eligible roles:** filter, confirmation, divergence source, trigger (threshold cross / centerline cross).
- **Market/data constraints:** Price-only; venue-agnostic. Oscillator, so best-behaved in ranges; threshold reading is regime-dependent.
- **Transfer notes:** Originates in Wilder's 1978 commodities work; transfers directly to forex/crypto spot.
- **Evidence/status:** Wilder, *New Concepts in Technical Trading Systems* (1978); StockCharts RSI https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi
- **Uncertainty/variants:** Thresholds 70/30 are convention (some use 80/20 in strong trends); "failure swing" vs. "divergence" terminology varies.

## macd

- **Family:** Momentum
- **Aliases:** Moving Average Convergence Divergence
- **Definition:** A trend-following momentum indicator built from the difference between two EMAs (the MACD line) plus a signal line (its EMA) and a histogram of their difference.
- **Boundaries:** MACD is a *trend-following, lagging* momentum tool — it confirms moves, it does not forecast them. Distinct from RSI (bounded, gain/loss ratio) and from raw momentum/ROC.
- **Observable inputs:** OHLC series (closing prices).
- **Recognition semantics:** MACD line = EMA(fast) − EMA(slow); signal line = EMA(MACD line); histogram = MACD line − signal. Crossovers, zero-line crossings, and divergences are the canonical readings.
- **Parameters/profiles:** fast 12 / slow 26 / signal 9 — `source-stated` (Gerald Appel's defaults); EMA type — `published-convention`.
- **Eligible roles:** confirmation, trigger (crossover), divergence source, filter, exit.
- **Market/data constraints:** Price-only; venue-agnostic. Default 12/26/9 assumes a specific bar cadence; intraday re-parameterization is normal.
- **Transfer notes:** Originates in equities (Appel); transfers directly to forex/crypto spot as a price-only statistic.
- **Evidence/status:** Investopedia MACD https://www.investopedia.com/terms/m/macd.asp ; Wikipedia MACD https://en.wikipedia.org/wiki/MACD
- **Uncertainty/variants:** "Divergence" is an overloaded term (MACD-line-vs-signal divergence vs. price-vs-MACD divergence); histogram-vs-crossover signal conventions differ.

## stochastic-oscillator

- **Family:** Momentum
- **Aliases:** Stochastic, %K/%D, Lane's stochastic
- **Definition:** A bounded momentum oscillator comparing the current close to its recent high–low range, used for overbought/oversold reads and (per its author) primarily for divergence.
- **Boundaries:** Stochastic is a *position-in-range* measure, not a trend or velocity measure. Its overbought/oversold bands (80/20) are convention. Distinct from RSI, which uses gain/loss ratios rather than range position.
- **Observable inputs:** OHLC series.
- **Recognition semantics:** %K = (close − lowest low(N)) / (highest high(N) − lowest low(N)) × 100; %D = smoothed %K. Crossovers and divergence are the primary signals.
- **Parameters/profiles:** %K period (14 fast / 5 fast) and %D smoothing (3) — `published-convention`; slow-stochastic variant applies further smoothing — `published-convention`; thresholds 80/20 — `published-convention`.
- **Eligible roles:** confirmation, divergence source, filter, trigger.
- **Market/data constraints:** Price-only; venue-agnostic. Regime-sensitive: extremes persist in trends.
- **Transfer notes:** Originates in George Lane's 1950s work; transfers directly to forex/crypto spot.
- **Evidence/status:** Wikipedia stochastic oscillator https://en.wikipedia.org/wiki/Stochastic_oscillator
- **Uncertainty/variants:** Fast vs. slow vs. full stochastic are distinct variants; Lane emphasized divergence over threshold trading, which is often lost in popularized accounts.

## momentum-divergence

- **Family:** Momentum
- **Aliases:** divergence, RSI divergence, MACD divergence, oscillator divergence
- **Definition:** A condition where price makes a new extreme but a momentum oscillator fails to confirm it, read as weakening momentum behind the move.
- **Boundaries:** Divergence is a *relationship between price and an oscillator*, not the oscillator itself. It is a discretionary/interpretive signal, not an algorithm with one universal form. Bullish (price lower low, oscillator higher low) vs. bearish (price higher high, oscillator lower high) must be distinguished.
- **Observable inputs:** OHLC series; a momentum oscillator (RSI/MACD/stochastic).
- **Recognition semantics:** Align price swing extremes with oscillator swing extremes over the same window; a non-confirming oscillator extreme is the divergence. Requires a defined swing-detection rule to be reproducible.
- **Parameters/profiles:** oscillator choice — `unresolved`; swing-detection strength — `inferred`; lookback window — `unresolved`.
- **Eligible roles:** confirmation (post-trigger), pre-trigger filter, reversal trigger, exit warning.
- **Market/data constraints:** Price-only; venue-agnostic. Divergence can persist through long trends, so it is unreliable as a standalone timing tool.
- **Transfer notes:** Fully transferable; no venue-specific data.
- **Evidence/status:** `published-convention`; documented for RSI/MACD/stochastic at StockCharts/Investopedia. No single URL fixed.
- **Uncertainty/variants:** Hidden vs. regular divergence; whether wicks or closes define extremes; how many bars constitute a "new extreme" are all unresolved.

## average-true-range

- **Family:** Volatility
- **Aliases:** ATR, Wilder's volatility
- **Definition:** A smoothed measure of per-period price range (accounting for gaps via true range), used to quantify volatility and to size stops/targets in price terms.
- **Boundaries:** ATR measures volatility, not trend direction or momentum. It is a magnitude, expressed in price units (or pips), and carries no sign.
- **Observable inputs:** OHLC series.
- **Recognition semantics:** TR = max(high−low, |high−prev close|, |low−prev close|); ATR = smoothed mean of TR (Wilder's smoothing). Higher ATR = more volatile; used for volatility-scaled distances (e.g. stops at k×ATR).
- **Parameters/profiles:** period 14 — `source-stated` (Wilder); smoothing — `source-stated`; multiplier k for stop distance (e.g. 1.5–3) — `inferred`/strategy-specific.
- **Eligible roles:** context (volatility regime), filter (minimum/maximum volatility), parameter base for stops/targets, distance normalizer.
- **Market/data constraints:** Price-only; venue-agnostic. ATR is absolute per instrument — not comparable across pairs without normalization (e.g. ATR%).
- **Transfer notes:** Originates in Wilder's commodities work; transfers directly to forex/crypto spot. In forex, ATR is often quoted in pips.
- **Evidence/status:** Investopedia ATR https://www.investopedia.com/terms/a/atr.asp ; Wilder, *New Concepts in Technical Trading Systems* (1978).
- **Uncertainty/variants:** Wilder smoothing vs. simple vs. EMA of TR; ATR% normalization is a common but non-standard variant.

## bollinger-bands

- **Family:** Volatility
- **Aliases:** Bollinger Bands, BB, volatility bands
- **Definition:** A price envelope of a moving average ± k standard deviations, expanding with volatility and contracting when it falls; used for relative-high/low reads and volatility-regime detection.
- **Boundaries:** Bands measure *relative* price position and volatility, not trend direction. Not a standalone signal; Bollinger himself frames them as a context tool to combine with other signals. Distinct from ATR (no mean-reversion centerline) and from Keltner (ATR-based).
- **Observable inputs:** OHLC series (closing prices).
- **Recognition semantics:** Middle = SMA(N); upper/lower = middle ± k×stdev(N). Band width proxies volatility (squeeze = low vol); price touching/exceeding bands marks relative extremes.
- **Parameters/profiles:** period 20 and k 2.0 — `source-stated` (Bollinger's defaults); longer-term profile 50 / 2.5 — `published-convention`.
- **Eligible roles:** context (volatility regime / squeeze), filter, confirmation, mean-reversion trigger at bands.
- **Market/data constraints:** Price-only; venue-agnostic. Assumes roughly stationary volatility; breaks down across extreme regime shifts.
- **Transfer notes:** Originates in equities (Bollinger, 1980s); transfers directly to forex/crypto spot.
- **Evidence/status:** Fidelity Bollinger Bands https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/bollinger-bands ; TradingView BB https://www.tradingview.com/support/solutions/43000501840-bollinger-bands-bb
- **Uncertainty/variants:** %B and bandwidth are derived metrics frequently bundled under "Bollinger" and should be listed as separate primitives if used.

## realized-volatility

- **Family:** Volatility
- **Aliases:** historical volatility, statistical volatility, HV, RV
- **Definition:** The actual variability of past returns, usually the annualized standard deviation of (log) returns over a lookback.
- **Boundaries:** Realized/historical volatility is *backward-looking*; it must not be confused with implied volatility (forward-looking, from options) or with ATR (a price-range average, not a return dispersion).
- **Observable inputs:** Price series (closes or returns).
- **Recognition semantics:** Compute returns over a window; take their standard deviation; annualize (×√252 or venue-appropriate). Higher = more volatile. Used as a baseline against forward-looking measures and for regime detection.
- **Parameters/profiles:** lookback (10/20/30/60/252) — `published-convention`; annualization factor — `published-convention` (equity) but `unresolved` for 24/7 crypto; log vs. simple returns — `published-convention`.
- **Eligible roles:** context (volatility regime), filter, baseline for implied-vs-realized comparison.
- **Market/data constraints:** Requires return history; no special venue data. In spot FX/crypto there is no options-implied analog unless a separate options market is available (crypto has options; spot FX IV is usually absent).
- **Transfer notes:** Transferable, but the annualization convention and whether "historical" = "realized" naming differ by source.
- **Evidence/status:** Investopedia implied vs. historical volatility https://www.investopedia.com/articles/investing-strategy/071616/implied-vs-historical-volatility-main-differences.asp
- **Uncertainty/variants:** "Historical" vs. "realized" are used interchangeably by some and distinguished (realized = intraday/high-frequency) by others.

## implied-volatility

- **Family:** Volatility
- **Aliases:** IV, expected volatility, option-implied volatility
- **Definition:** The market's forward-looking volatility expectation, backed out from option prices (e.g. solving Black–Scholes for the volatility input).
- **Boundaries:** IV is *forward-looking* and options-derived, unlike realized volatility (past) or ATR (price range). It is a *sentiment/expectation* measure, not an observed price statistic. In spot FX there is usually no IV; the VIX is an equity index IV proxy, not a currency measure.
- **Observable inputs:** Options prices (or an IV index like VIX/DVOL); otherwise unavailable.
- **Recognition semantics:** Solve an options-pricing model for the volatility consistent with observed option prices. High IV = market expects turbulence; low IV = calm. VIX expresses this for the S&P 500.
- **Parameters/profiles:** pricing model (Black–Scholes) — `published-convention`; maturity window (VIX ≈ 30-day) — `published-convention`.
- **Eligible roles:** intermarket/risk context, filter (risk-on/off), volatility-regime input.
- **Market/data constraints:** Only exists where a liquid options market exists. Not available for spot FX directly; available for crypto via options/derivatives (e.g. DVOL). Not available from pure spot OHLC.
- **Transfer notes:** As a *risk-regime* signal it transfers to forex/crypto spot only as a correlated external input, and only where such data exists — must be labelled as intermarket, not native.
- **Evidence/status:** Investopedia VIX https://www.investopedia.com/terms/v/vix.asp ; Investopedia IV vs HV https://www.investopedia.com/articles/investing-strategy/071616/implied-vs-historical-volatility-main-differences.asp
- **Uncertainty/variants:** VIX is equity-specific; crypto IV indices (DVOL) are separate; FX "volatility" typically refers to realized measures or broker-quoted FX options, not a clean IV index.

## donchian-channel

- **Family:** Volatility
- **Aliases:** Donchian channel, price channel, N-bar high/low channel
- **Definition:** A channel drawn from the highest high and lowest low over N periods, used to detect breakouts and to bound ranges.
- **Boundaries:** Donchian is *price-extreme*-based (rigid, step-like), unlike Keltner (ATR-based) or Bollinger (stdev-based). It signals new N-period highs/lows, not volatility directly.
- **Observable inputs:** OHLC series.
- **Recognition semantics:** Upper = max high(N), lower = min low(N), mid = average. A close above the upper band = new N-bar high (breakout); price within channel = range.
- **Parameters/profiles:** period N (20 common; 55 for the turtle-trading 20/55 dual system) — `published-convention`.
- **Eligible roles:** trigger (breakout), filter, context (range definition), trailing stop reference.
- **Market/data constraints:** Price-only; venue-agnostic.
- **Transfer notes:** Originates in futures trend-following (Richard Donchian / turtle traders); transfers directly to forex/crypto spot.
- **Evidence/status:** `published-convention`; Donchian channel is widely documented (e.g. Investopedia bands/channels article https://www.investopedia.com/articles/forex/06/bandschannels.asp).
- **Uncertainty/variants:** Single vs. dual-channel (20/55) systems; whether breakout is close-based or intrabar.

## keltner-channel

- **Family:** Volatility
- **Aliases:** Keltner channel, ATR channel
- **Definition:** A volatility band around an EMA where band width is a multiple of ATR, used for trend framing and volatility-aware support/resistance.
- **Boundaries:** Keltner uses ATR (volatility) for band width, unlike Bollinger (stdev) or Donchian (price extremes). It is a *trend + volatility* overlay, not a breakout detector per se.
- **Observable inputs:** OHLC series.
- **Recognition semantics:** Middle = EMA(N); upper/lower = middle ± k×ATR(M). Bands widen/contract with ATR; price position between bands frames trend health.
- **Parameters/profiles:** EMA period 20, ATR period 10–20, multiplier k 2 — `published-convention` (values vary by source).
- **Eligible roles:** context (trend/volatility framing), filter, confirmation, dynamic stop/target reference.
- **Market/data constraints:** Price-only; venue-agnostic.
- **Transfer notes:** Originates in commodity futures (Chester Keltner, 1960s); transfers directly to forex/crypto spot.
- **Evidence/status:** `published-convention`; see Investopedia bands/channels https://www.investopedia.com/articles/forex/06/bandschannels.asp and Keltner-vs-Donchian comparisons.
- **Uncertainty/variants:** Parameter conventions differ by platform; some variants use SMA middle line.

## average-daily-range

- **Family:** Volatility
- **Aliases:** ADR, daily range, ADR%
- **Definition:** The average high−low range over a recent window of days (or sessions), used to judge whether a move or a target distance is "normal" for the instrument.
- **Boundaries:** ADR is a *calendared* average range, distinct from ATR (per-bar, gap-adjusted) and from realized volatility (return dispersion). ADR is session-based and so inherits session boundaries.
- **Observable inputs:** Daily OHLC series.
- **Recognition semantics:** ADR = mean(high−low) over N days. Compare current range or a proposed stop/target distance to ADR (and to intraday range elapsed vs. ADR) to gauge room remaining.
- **Parameters/profiles:** lookback N (5–20 days) — `inferred`; percent-of-ADR thresholds — `unresolved`.
- **Eligible roles:** context (volatility expectation), filter (distance-to-target feasibility), stop/target sanity check.
- **Market/data constraints:** Needs a defined "day"; forex "day" is broker/server-defined (usually NY close), crypto "day" is usually UTC. This is a session-boundary dependency.
- **Transfer notes:** Transferable, but the "day" boundary convention differs between forex (NY close) and crypto (UTC), which changes ADR values.
- **Evidence/status:** `ontology-seed — needs source evidence`; ADR is a widely used retail concept without a single canonical citation.
- **Uncertainty/variants:** Day-boundary convention; N-bar window; whether to use body-only or full range.

## moving-average

- **Family:** Indicator family & operations
- **Aliases:** MA, SMA, EMA, WMA, HMA
- **Definition:** An indicator family that smooths a price series into a lagged trend line by averaging past values; SMA, EMA, WMA, and HMA are the common members.
- **Boundaries:** This entry is the *family/operation*, not any specific trend reading. A moving average alone is not a signal; it becomes one only when bound (cross, slope, price-relative). Distinct from oscillators and bands.
- **Observable inputs:** OHLC series.
- **Recognition semantics:** Compute the chosen average over N periods. SMA weights all equally; EMA weights recent bars more. Member choice changes lag and responsiveness.
- **Parameters/profiles:** type (SMA/EMA/WMA/HMA) — `published-convention`; period N — strategy-specific `inferred`.
- **Eligible roles:** context, filter, dynamic level, component of other primitives (MACD, Bollinger, Keltner).
- **Market/data constraints:** Price-only; venue-agnostic.
- **Transfer notes:** Fully transferable to forex/crypto spot.
- **Evidence/status:** `published-convention` — core technical-analysis material (StockCharts/Investopedia moving-average articles).
- **Uncertainty/variants:** Type selection (SMA vs. EMA) is discretionary; "moving average" as a primitive should be parameterized, not assumed.

## oscillator

- **Family:** Indicator family & operations
- **Aliases:** momentum oscillator, bounded oscillator
- **Definition:** An indicator family whose values oscillate around a centerline or within a bounded range (0–100), used to read momentum, overbought/oversold, and divergence.
- **Boundaries:** This is the *family*, not any member. An oscillator is a *derived* indicator, not a raw price/volume fact. Bounded (RSI, stochastic) vs. unbounded (ROC, MACD histogram) must be distinguished.
- **Observable inputs:** OHLC series (most members).
- **Recognition semantics:** Members transform price into an oscillating series; readings are interpreted via thresholds, centerline crosses, and divergence.
- **Parameters/profiles:** member-specific periods; threshold conventions (70/30, 80/20) — `published-convention`.
- **Eligible roles:** confirmation, filter, divergence source, trigger.
- **Market/data constraints:** Price-only; regime-sensitive (extremes persist in trends).
- **Transfer notes:** Fully transferable to forex/crypto spot.
- **Evidence/status:** `published-convention` — see StockCharts oscillator taxonomy.
- **Uncertainty/variants:** The boundary between "oscillator" and "band indicator" is loose (Bollinger is sometimes classed as an oscillator on some platforms).

## band-envelope

- **Family:** Indicator family & operations
- **Aliases:** envelope, band, channel
- **Definition:** An indicator family that draws upper/lower bounds around a centerline, where the bounds expand with a volatility or extreme measure; members include Bollinger, Keltner, Donchian, and simple percentage envelopes.
- **Boundaries:** This is the *family*. A band is not itself a signal — it supplies relative-high/low and volatility context. Band type is defined by its width rule (stdev vs. ATR vs. extreme vs. %).
- **Observable inputs:** OHLC series.
- **Recognition semantics:** Compute centerline and width; interpret price position relative to bounds and band width (expansion = volatility rise, squeeze = fall).
- **Parameters/profiles:** member-specific; see individual entries.
- **Eligible roles:** context, filter, confirmation, mean-reversion trigger.
- **Market/data constraints:** Price-only; venue-agnostic.
- **Transfer notes:** Fully transferable.
- **Evidence/status:** `published-convention` — see Investopedia bands/channels https://www.investopedia.com/articles/forex/06/bandschannels.asp
- **Uncertainty/variants:** "Channel" vs. "band" vs. "envelope" naming is inconsistent across platforms.

## ichimoku-cloud

- **Family:** Indicator family & operations
- **Aliases:** Ichimoku Kinko Hyo, Kumo, Ichimoku
- **Definition:** A composite Japanese overlay of five lines (Tenkan, Kijun, Senkou A/B forming the "cloud"/Kumo, Chikou) that jointly encode trend, momentum, and forward support/resistance.
- **Boundaries:** Ichimoku is a *multi-component system*, not a single oscillator. Its cloud is *forward-projected* support/resistance, unlike backward-looking moving averages. Designed for medium/higher timeframes; weak in chop/scalping.
- **Observable inputs:** OHLC series.
- **Recognition semantics:** Tenkan = mid(high,low,9); Kijun = mid(high,low,26); Senkou A = (Tenkan+Kijun)/2 plotted 26 ahead; Senkou B = mid(high,low,52) plotted 26 ahead; Chikou = close plotted 26 behind. Price above a rising cloud = bullish context; Tenkan/Kijun cross = signal; Chikou position = confirmation.
- **Parameters/profiles:** 9/26/52 — `source-stated` (Hosoda's defaults).
- **Eligible roles:** context (trend/cloud side), filter, confirmation (Chikou), trigger (cross / cloud breakout), stop/target reference (Kijun/cloud boundary).
- **Market/data constraints:** Price-only; venue-agnostic. Forward projection means recent bars lack cloud (a known display gap).
- **Transfer notes:** Originates in Japanese equities (Goichi Hosoda, ~1930s); transfers directly to forex/crypto spot as a price-only system.
- **Evidence/status:** R ichimoku reference manual (line definitions) https://cran.r-project.org/web/packages/ichimoku/vignettes/reference.html ; Investopedia Ichimoku https://www.investopedia.com/terms/i/ichimokuchart.asp
- **Uncertainty/variants:** Defaults are sometimes cited as 9/26/52 (equity) with alternative intraday sets; exact signal hierarchy varies by school.

## crossover

- **Family:** Indicator family & operations
- **Aliases:** cross, line cross, signal-line cross
- **Definition:** An indicator *operation*: the event where one line/indicator crosses another (or a fixed level), used as a discrete transition to trigger or confirm.
- **Boundaries:** A crossover is a generic operation, not a specific indicator. It must be bound to named lines (fast/slow MA, MACD/signal, oscillator/threshold). It is an event, not a state.
- **Observable inputs:** Two indicator series or an indicator and a level.
- **Recognition semantics:** Detect sign change of (lineA − lineB) between consecutive bars. Up-cross vs. down-cross are distinct events. Bar-close vs. intrabar evaluation must be specified.
- **Parameters/profiles:** evaluation timing (close vs. intrabar) — `unresolved` (binding decision); confirmation bar requirement — `unresolved`.
- **Eligible roles:** trigger, confirmation (synchronous/post), exit.
- **Market/data constraints:** Indicator-dependent; venue-agnostic. Crossovers whipsaw in ranges.
- **Transfer notes:** Fully transferable; the *operation* is universal, the *parameters* are not.
- **Evidence/status:** `published-convention` — crossovers are standard indicator vocabulary (see MACD/MA articles above).
- **Uncertainty/variants:** Whether a touch counts as a cross; intrabar vs. close; repaint behavior of some platforms' indicators.

## indicator-divergence

- **Family:** Indicator family & operations
- **Aliases:** price-indicator divergence, non-confirmation
- **Definition:** The general *operation* of comparing price swing extremes against an indicator's swing extremes to detect non-confirmation (see momentum-divergence for the momentum case).
- **Boundaries:** This is the generic operation; momentum-divergence is its most common instance. Divergence can also be read on volume, breadth, or cumulative flow measures. It is interpretive, not algorithmic by default.
- **Observable inputs:** Price series + a paired indicator/measure.
- **Recognition semantics:** Overlap swing structure of price and the paired measure; a price extreme unconfirmed by the measure is divergence.
- **Parameters/profiles:** swing-detection rule — `inferred`; paired measure — `unresolved`.
- **Eligible roles:** confirmation, filter, reversal warning, exit.
- **Market/data constraints:** Depends on the paired measure; venue-agnostic for price-derived measures.
- **Transfer notes:** Fully transferable.
- **Evidence/status:** `published-convention` (see momentum-divergence sources).
- **Uncertainty/variants:** Regular vs. hidden divergence; the term is frequently overloaded (e.g. "MACD divergence" can mean line-vs-signal, not price-vs-MACD).

## trading-session

- **Family:** Session / time-window / higher-timeframe
- **Aliases:** session, market session, London/New York/Tokyo/Sydney session
- **Definition:** A named, geographically-anchored trading window (Tokyo/Asia, London/Europe, New York/US, Sydney) with distinct liquidity and volatility character.
- **Boundaries:** A session is a *time coordinate*, not a price level and not a bias. "The London session" is not a level; "the London-session high" is (that high is a separate location primitive).
- **Observable inputs:** Clock/time with a defined timezone; session schedule (with DST handling).
- **Recognition semantics:** Classify current UTC/ET time into the named session per a fixed schedule. Session boundaries are conventions and shift with DST.
- **Parameters/profiles:** session hours (e.g. London 8:00–17:00 GMT/BST, New York 8:00–17:00 ET, Tokyo) — `published-convention`; timezone/DST handling — `unresolved` (platform-dependent).
- **Eligible roles:** context, pre-trigger filter (trade only in session X), timing constraint, higher-timeframe context.
- **Market/data constraints:** Forex is 24/5, so sessions are about liquidity shifts, not market open/close. Crypto spot is 24/7, so "sessions" are heuristic liquidity waves, not venue hours — a real semantic difference.
- **Transfer notes:** Forex sessions transfer to crypto only as *liquidity/volatility heuristics*, since crypto has no session close; the mapping is approximate and must be labelled.
- **Evidence/status:** Babypips session overlaps https://www.babypips.com/learn/forex/session-overlaps ; Investopedia 3-session system https://www.investopedia.com/articles/forex/08/3-market-system.asp
- **Uncertainty/variants:** Session-hour conventions vary (London open cited as 7:00 or 8:00 UTC); DST handling is a persistent ambiguity.

## session-overlap

- **Family:** Session / time-window / higher-timeframe
- **Aliases:** London–New York overlap, overlap window
- **Definition:** A time window where two major sessions are simultaneously active, conventionally the highest-liquidity/volatility part of the forex day.
- **Boundaries:** Overlap is a *sub-window* of two sessions, not a session itself. Its "best to trade" status is a heuristic, not a data fact.
- **Observable inputs:** Clock/time; session schedules.
- **Recognition semantics:** Identify intersection of two sessions (e.g. London+New York ≈ 13:00–16:00 UTC; London+Tokyo ≈ 8:00–9:00 UTC).
- **Parameters/profiles:** overlap hours — `published-convention` (London/NY 8:00–12:00 ET or 13:00–16:00 UTC).
- **Eligible roles:** context, filter (prefer/higher-liquidity window), timing constraint.
- **Market/data constraints:** Forex-specific concept; crypto has no true session overlap, only aggregate activity peaks.
- **Transfer notes:** Transfers to crypto only as an activity-peak heuristic (roughly aligned to when both London and NY participants are active); label as approximate.
- **Evidence/status:** Babypips session overlaps https://www.babypips.com/learn/forex/session-overlaps ; Myfxbook market hours https://www.myfxbook.com/market-hours
- **Uncertainty/variants:** Exact UTC windows vary by DST and source; some treat "overlap" as 13:00–17:00 UTC.

## session-open-price

- **Family:** Session / time-window / higher-timeframe
- **Aliases:** session open, daily open, London open, weekly open, opening range
- **Definition:** The price at the start of a named session or calendar period, used as a reference level against which subsequent price is measured.
- **Boundaries:** This is a *location* derived from a *time boundary* — it is a price reference, not the session itself. Distinct from the session-open *range* (a zone built from the first N bars).
- **Observable inputs:** Time boundary + the price at that boundary (or first print after it).
- **Recognition semantics:** Record the first traded price at/after the session start. Used as a magnet/decision line; price above/below the open is a common intraday framing.
- **Parameters/profiles:** which session/day boundary — strategy-specific `inferred`; whether to use first tick or first bar close — `unresolved`.
- **Eligible roles:** location/level reference, context, filter, trigger (break of open), target.
- **Market/data constraints:** Needs a defined boundary; forex "daily open" usually = NY 5pm ET; crypto "daily open" usually = 00:00 UTC. This changes the reference.
- **Transfer notes:** Transferable, but the boundary convention must be pinned per market (NY close vs. UTC midnight) or the level is meaningless.
- **Evidence/status:** `ontology-seed — needs source evidence`; widely used in intraday practice (e.g. "London open" trading) without a canonical URL fixed this wave.
- **Uncertainty/variants:** Open price vs. opening range; boundary convention; whether gaps across the boundary are included.

## time-of-day-window

- **Family:** Session / time-window / higher-timeframe
- **Aliases:** time filter, session-hours filter, kill-zone window
- **Definition:** A fixed clock-time window during which a strategy is permitted (or prohibited) from acting, independent of any named session semantics.
- **Boundaries:** A pure time gate, not a market condition. It constrains *when*, not *whether*, a setup is valid. Distinct from session (which carries liquidity meaning).
- **Observable inputs:** Clock/time.
- **Recognition semantics:** Compare current time against an allowed window (e.g. "no entries 15:55–16:05 ET around news").
- **Parameters/profiles:** start/end times + timezone — `unresolved` (strategy-specific); DST handling — `unresolved`.
- **Eligible roles:** pre-trigger filter (hard gate), timing constraint.
- **Market/data constraints:** Purely temporal; venue-agnostic but timezone/DST is the key error source.
- **Transfer notes:** Fully transferable (time is universal); only the *choice* of window is market/strategy-specific.
- **Evidence/status:** `ontology-seed — needs source evidence`.
- **Uncertainty/variants:** Timezone/DST ambiguity is the dominant failure mode; "kill zones" (ICT) are a named variant.

## day-of-week-window

- **Family:** Session / time-window / higher-timeframe
- **Aliases:** weekday filter, trading-day filter
- **Definition:** A calendar-day filter restricting activity to specific weekdays, used to avoid low-liquidity days or to target recurring patterns.
- **Boundaries:** A pure calendar gate, not a market condition. Distinct from time-of-day (hour) and from session (liquidity semantics).
- **Observable inputs:** Calendar date/day-of-week.
- **Recognition semantics:** Compare current weekday against an allowed set.
- **Parameters/profiles:** allowed/blocked weekdays — `unresolved` (strategy-specific); calendar/timezone for "day" start — `unresolved`.
- **Eligible roles:** pre-trigger filter, timing constraint.
- **Market/data constraints:** Forex has a weekend gap (Fri close → Sun open); crypto trades 24/7, so "weekend" has different meaning. Day-of-week boundary depends on the "day" convention.
- **Transfer notes:** Transferable, but the weekend and day-boundary semantics differ materially between forex and crypto.
- **Evidence/status:** `ontology-seed — needs source evidence`.
- **Uncertainty/variants:** Whether the trading "day" starts at NY close or UTC midnight changes weekday membership.

## higher-timeframe-reference

- **Family:** Session / time-window / higher-timeframe
- **Aliases:** HTF level, HTF close, higher-timeframe structure reference
- **Definition:** A price reference (level, close, or structure) taken from a longer timeframe and applied as context to the entry timeframe.
- **Boundaries:** This is a *coordination* primitive (pulling a location/measure down from a longer timeframe), not a new measure. Distinct from higher-timeframe-trend-bias (which is directional, not a level).
- **Observable inputs:** Multi-timeframe OHLC (or resampled series).
- **Recognition semantics:** Resample/align a longer timeframe and extract its levels (session high/low, prior close, structure) as context for the shorter timeframe.
- **Parameters/profiles:** timeframe pair — strategy-specific `inferred`; which reference (high/low/close/structure) — `unresolved`.
- **Eligible roles:** context, filter, level reference, confluence weight.
- **Market/data constraints:** Needs consistent multi-timeframe data; bar alignment across timeframes matters (crypto continuous vs. forex session gaps).
- **Transfer notes:** Transferable; the specific ladder and reference choice are strategy decisions.
- **Evidence/status:** `ontology-seed — needs source evidence`.
- **Uncertainty/variants:** How bars align across timeframes; whether references use wick or close extremes.

## bid-ask-spread

- **Family:** Spread / liquidity / cost / data health
- **Aliases:** spread, bid/ask spread, bid-offer spread
- **Definition:** The difference between the best ask and best bid quote for an instrument; the immediate transaction cost of a round-trip and a liquidity proxy.
- **Boundaries:** Spread is a *cost/liquidity* fact, not a direction signal. In spot FX, the spread is broker/venue-quoted (not a centralized exchange fact); in crypto spot it is exchange-specific per trading pair/venue.
- **Observable inputs:** Bid and ask quotes (top of book) from a specific venue/broker.
- **Recognition semantics:** spread = ask − bid (in price units or pips). Tighter = more liquid/cheaper; wider = less liquid/costlier. Quote provenance (which broker/venue) is essential.
- **Parameters/profiles:** pip convention (0.0001 for most majors, 0.01 JPY pairs) — `published-convention`; no numeric default for spread width itself (instrument/time-dependent) — `unresolved`.
- **Eligible roles:** filter (max-spread gate before entry), context (liquidity), cost input.
- **Market/data constraints:** Spot FX has no consolidated book — spread is broker-specific and can include markup. Crypto spread is per-exchange and per-pair; cross-venue comparison requires aggregation choice.
- **Transfer notes:** Concept transfers, but the *data source* differs fundamentally: broker-quoted FX vs. exchange-book crypto. Never treat one as the other.
- **Evidence/status:** Wikipedia bid–ask spread https://en.wikipedia.org/wiki/Bid%E2%80%93ask_spread ; Babypips what-is-a-spread https://www.babypips.com/learn/forex/what-is-a-spread-in-forex-trading
- **Uncertainty/variants:** Fixed vs. variable spread; broker markup vs. interbank spread; which side is "cost" depends on trade direction.

## spread-widening-condition

- **Family:** Spread / liquidity / cost / data health
- **Aliases:** spread expansion, liquidity drying up
- **Definition:** A transient condition where the spread widens well beyond its normal level, typically around news, rollover, or thin liquidity, signaling degraded execution quality.
- **Boundaries:** A *dynamic condition* over time, not the spread level itself. Not a direction signal. Widening is always venue/broker-specific.
- **Observable inputs:** A time series of the spread for the same instrument/venue.
- **Recognition semantics:** Compare current spread to a rolling baseline (e.g. median/percentile over N minutes). A spike above a threshold = widening. Often bound as a pre-entry gate.
- **Parameters/profiles:** baseline window — `inferred`; spike threshold (e.g. 2–3× baseline) — `inferred`; percentile — `unresolved`.
- **Eligible roles:** pre-trigger filter (block entries during widening), context, execution-quality warning.
- **Market/data constraints:** Venue-specific; FX widening is broker-dependent, crypto widening is exchange/pair-dependent. News/rollover are the classic triggers.
- **Transfer notes:** Transferable as a *condition*, but baselines differ per market and venue.
- **Evidence/status:** `ontology-seed — needs source evidence`; the news-widening mechanism is documented in spread articles (e.g. CMC/Babypips above).
- **Uncertainty/variants:** Baseline method and threshold are discretionary; "normal" spread varies by session and pair.

## market-depth

- **Family:** Spread / liquidity / cost / data health
- **Aliases:** depth, order-book depth, level-2 depth, DOM depth
- **Definition:** The quantity of resting buy/sell orders across price levels in an order book, indicating a market's ability to absorb size without large price impact.
- **Boundaries:** Depth is a *centralized-order-book* concept. Spot FX has no consolidated depth — brokers may show indicative depth from their own liquidity providers, which is not a market-wide truth. Depth ≠ traded volume (resting orders vs. executed trades).
- **Observable inputs:** An order book (L2 data: price levels + aggregated resting size).
- **Recognition semantics:** Sum/compare resting size on bid vs. ask sides and across levels. Thin book near the touch = low depth = higher slippage risk for market orders.
- **Parameters/profiles:** number of levels (top 5/10/full) — `published-convention` (L2 feed); aggregation (by price vs. by order) — `published-convention` (L2 vs. L3).
- **Eligible roles:** context (liquidity), filter, execution-quality input.
- **Market/data constraints:** Native to centralized exchanges (crypto spot, futures, equities). For spot FX, only broker-provided indicative depth exists — label as broker-specific, not market-wide.
- **Transfer notes:** Centralized-crypto depth must NOT be silently translated into spot-FX depth. Spot FX depth is broker/venue-specific and usually unavailable as true market depth.
- **Evidence/status:** Investopedia market depth https://www.investopedia.com/terms/m/marketdepth.asp ; KX Level 1/2/3 data https://kx.com/glossary/level-1-level-2-and-level-3-market-data/
- **Uncertainty/variants:** L2 vs. L3 (aggregated vs. order-level); hidden/iceberg orders are invisible to L2; "DOM" vs. "depth" naming.

## slippage

- **Family:** Spread / liquidity / cost / data health
- **Aliases:** fill deviation, price improvement/deterioration
- **Definition:** The difference between the expected execution price and the actual fill price of an order.
- **Boundaries:** Slippage is an *execution outcome*, not a market property — it arises from volatility, thin depth, and latency. It can be positive or negative. Distinct from spread (a quoted cost, paid regardless).
- **Observable inputs:** Expected vs. actual fill prices (order records).
- **Recognition semantics:** slippage = fill − expected (signed). Occurs when price moves between order intent and execution, especially with market orders in fast/low-liquidity conditions.
- **Parameters/profiles:** none intrinsic; magnitude is a per-execution observation — `unresolved`.
- **Eligible roles:** execution-quality context, cost input, post-hoc filter (flag venues/conditions with excess slippage).
- **Market/data constraints:** Both forex and crypto spot exhibit slippage; crypto on thin books/low-liquidity pairs can be severe; forex slippage concentrates around news/rollover.
- **Transfer notes:** Fully transferable as a concept; the *magnitudes and causes* differ by market/venue.
- **Evidence/status:** Investopedia slippage https://www.investopedia.com/terms/s/slippage.asp
- **Uncertainty/variants:** Positive vs. negative slippage; whether "slippage" includes commission/spread or is pure fill deviation.

## trading-cost

- **Family:** Spread / liquidity / cost / data health
- **Aliases:** transaction cost, all-in cost, fees
- **Definition:** The total cost of a round-trip trade: spread + commission + (in some venues) funding/swap, expressed per trade or per notional.
- **Boundaries:** Cost is an *economic* fact, not a signal. It aggregates multiple distinct primitives (spread, commission, swap). Must not be confused with slippage (an execution outcome).
- **Observable inputs:** Spread, commission schedule, swap/rollover rates, order size.
- **Recognition semantics:** Sum the applicable cost components for a planned round-trip size and instrument.
- **Parameters/profiles:** commission basis (per-lot/per-notional) — `published-convention` (venue schedule); none standardized across venues.
- **Eligible roles:** filter (cost-too-high veto), context, parameter base for target/stop feasibility.
- **Market/data constraints:** Venue-specific. Spot FX costs live in the spread + possible commission + swap; crypto spot costs are taker/maker fees per exchange + possible withdrawal.
- **Transfer notes:** Structure differs: FX spread-inclusive vs. crypto fee-schedule-inclusive; always record venue.
- **Evidence/status:** `published-convention` — see spread and slippage sources; no single canonical cost URL fixed.
- **Uncertainty/variants:** Maker vs. taker fee tiers (crypto); whether swap/rollover is included in "cost".

## data-health-feed

- **Family:** Spread / liquidity / cost / data health
- **Aliases:** feed health, data staleness, quote sanity, gap detection
- **Definition:** A condition flag on the integrity of the incoming market data: stale ticks, gaps, inverted quotes, missing bars, or feed disconnects.
- **Boundaries:** A *meta-condition* about data quality, not a market signal. An inverted bid>ask or a sudden price gap may indicate a feed fault, not a tradeable event.
- **Observable inputs:** Timestamps, quote/price stream, bar series, connectivity status.
- **Recognition semantics:** Detect staleness (no update beyond a timeout), inverted quotes, implausible gaps, or bar-count gaps. Bind as a hard gate before any trigger is evaluated.
- **Parameters/profiles:** staleness timeout — `unresolved`; gap threshold — `unresolved`; retry policy — `unresolved`.
- **Eligible roles:** pre-trigger filter (hard veto), context.
- **Market/data constraints:** Applies to any venue; forex quotes can invert transiently during news (broker-dependent); crypto feeds can diverge across exchanges.
- **Transfer notes:** Fully transferable as a guard; thresholds are venue-specific.
- **Evidence/status:** `ontology-seed — needs source evidence`; informed by bid–ask spread material (inverted quote = feed fault) above.
- **Uncertainty/variants:** Distinguishing real market gaps from feed faults is inherently ambiguous.

## rollover-swap-cost

- **Family:** Spread / liquidity / cost / data health
- **Aliases:** swap, rollover, overnight fee, tom-next
- **Definition:** The interest/rollover adjustment applied to a position held past the daily rollover time, reflecting the interest-rate differential (in FX) or, for crypto, venue-specific funding-like charges on leveraged/margin products.
- **Boundaries:** This is a *cost/credit* tied to holding a position across a time boundary, not a market condition and not a signal. In spot FX it stems from interest-rate differentials; in crypto *spot* there is no funding rate (funding is a perpetual-futures concept — see the intermarket note), though brokers may charge margin swap.
- **Observable inputs:** Swap/rollover rates for the instrument/side (long/short), position size, holding time.
- **Recognition semantics:** Identify the rollover time and the signed swap rate; a long-held position accrues the rate per day held.
- **Parameters/profiles:** rollover time (NY close, ~5pm ET, or venue-specific) — `published-convention`; triple-swap day (Wednesday in FX) — `published-convention`.
- **Eligible roles:** cost input, filter (avoid holding across rollover), context.
- **Market/data constraints:** FX swap is rate-differential-driven and broker-quoted; crypto spot has no universal swap — margin products have their own financing. Do not conflate FX swap with crypto funding rates.
- **Transfer notes:** Not directly transferable: FX swap ≠ crypto funding. Record each market's actual charge mechanism.
- **Evidence/status:** `ontology-seed — needs source evidence`; the FX rollover mechanism is standard broker documentation (e.g. Babypips rollover lessons).
- **Uncertainty/variants:** Triple-swap day; whether swap is symmetric long/short; broker-specific rates.

## exchange-volume

- **Family:** Volume / profile / order-flow / DOM
- **Aliases:** volume, traded volume, tick volume (see note)
- **Definition:** The quantity of an instrument traded over a period, aggregated per bar or per level, as recorded by a centralized exchange.
- **Boundaries:** TRUE volume exists only on centralized venues. Spot FX has NO consolidated volume — "volume" in FX is usually tick volume (number of price changes) from a single broker/feed, which is not real traded volume. This entry is the *centralized* truth; see spot-fx-tick-volume for the broker view.
- **Observable inputs:** Executed-trade records aggregated by bar/level (exchange tape).
- **Recognition semantics:** Sum traded quantity per bar. Rising volume accompanying a move is read as participation/conviction (interpretive); volume alone is not directional.
- **Parameters/profiles:** aggregation unit (bar/level/session) — `published-convention`; no intrinsic numeric default.
- **Eligible roles:** confirmation, context (participation), divergence source, filter.
- **Market/data constraints:** Centralized-exchange only (crypto spot, futures, equities). NOT a spot-FX fact.
- **Transfer notes:** Do NOT transfer centralized volume to spot FX. Crypto-spot volume is real (per exchange); FX "volume" is a broker tick-count proxy and must be relabelled.
- **Evidence/status:** `published-convention` — volume is core TA vocabulary (Investopedia volume).
- **Uncertainty/variants:** Whether off-exchange/OTC volume is counted; exchange vs. aggregated (e.g. CoinMarketCap-style) volume.

## volume-profile

- **Family:** Volume / profile / order-flow / DOM
- **Aliases:** volume-at-price, market profile (related), VP
- **Definition:** A histogram of traded volume (or, in FX, time/ticks) at each price level over a session or window, surfacing point of control (POC), value area (VA), value-area high/low (VAH/VAL), and high/low-volume nodes.
- **Boundaries:** Volume profile is a *distribution of activity across price*, not a time-series indicator and not market profile's TPO/time-based variant (related but distinct). POC/VA are derived *locations*, not signals.
- **Observable inputs:** Volume-at-price data (exchange) or tick-at-price (FX proxy).
- **Recognition semantics:** Bin traded volume per price level. POC = level with most volume; VA = range containing ~70% of volume; VAH/VAL = its bounds; low-volume nodes = thin spots price may traverse quickly.
- **Parameters/profiles:** value-area percent 70 (or 80) — `published-convention`; window (session/day/visible range) — `published-convention`/platform-dependent.
- **Eligible roles:** context (fair-value zones), level reference (POC/VAH/VAL), filter, target/stops reference.
- **Market/data constraints:** Centralized-exchange volume for crypto/futures. In spot FX, only tick/time-based profiles exist (broker-specific) — must be labelled as a proxy.
- **Transfer notes:** Volume profile transfers to crypto spot directly (exchange volume); to spot FX only as a tick/TIME-based proxy, not true volume-at-price.
- **Evidence/status:** thinkorswim VolumeProfile https://toslc.thinkorswim.com/center/reference/Tech-Indicators/studies-library/V-Z/VolumeProfile ; Schwab volume profile https://www.schwab.com/learn/story/using-volume-profile-indicator
- **Uncertainty/variants:** 70% vs. 80% value area; "naked/virgin POC"; market profile (TPO) vs. volume profile distinction.

## vwap

- **Family:** Volume / profile / order-flow / DOM
- **Aliases:** Volume-Weighted Average Price
- **Definition:** The cumulative volume-weighted average traded price over a session, used as a session-level fair-value benchmark and intraday level.
- **Boundaries:** VWAP is a *cumulative session benchmark* (resets each session), not a trend indicator and not a simple moving average. It requires volume weighting, so its meaning depends on having real volume.
- **Observable inputs:** Price and volume (per trade/bar) over the session.
- **Recognition semantics:** VWAP = Σ(price×volume)/Σ(volume) since session start. Price above VWAP read as bullish intraday context (and vice versa); VWAP acts as a magnet/level.
- **Parameters/profiles:** session anchor (day/session start) — `published-convention`; rolling vs. session reset — `published-convention` (session reset standard).
- **Eligible roles:** context, level reference, filter, execution benchmark, mean-reversion reference.
- **Market/data constraints:** Centralized-exchange volume for crypto. In spot FX there is no market-wide VWAP — only broker/venue-specific VWAP from that broker's flow, not the whole market.
- **Transfer notes:** Transfers to crypto spot directly; to spot FX only as a broker-specific proxy. Do not claim a market-wide FX VWAP.
- **Evidence/status:** Wikipedia VWAP https://en.wikipedia.org/wiki/Volume-weighted_average_price ; Investopedia VWAP https://www.investopedia.com/terms/v/vwap.asp
- **Uncertainty/variants:** Session-anchor convention; whether volume includes only public trades; "anchored VWAP" variant.

## order-book-depth

- **Family:** Volume / profile / order-flow / DOM
- **Aliases:** L2, depth of market, DOM
- **Definition:** The visible resting limit orders at multiple price levels on each side of an exchange's book (aggregated size per level = L2; individual orders = L3).
- **Boundaries:** This is the *structure of resting liquidity*, not executed volume. L2 shows aggregated size only (no queue position); L3 shows order-level detail. Spot FX has no true public order book.
- **Observable inputs:** Exchange book snapshots/feeds.
- **Recognition semantics:** Read bid/ask ladders; compare near-book depth; large resting size ("walls") is visible but can be cancelled/iceberged, so it is an observation, not a guarantee.
- **Parameters/profiles:** levels shown (top N / full) — `published-convention`; aggregation by price (L2) vs. by order (L3) — `published-convention`.
- **Eligible roles:** context (liquidity), execution-quality input, filter.
- **Market/data constraints:** Centralized exchanges only (crypto spot). Not available for spot FX as a market-wide fact.
- **Transfer notes:** Crypto-spot order books are real per exchange; spot FX has no equivalent — broker "depth" is indicative only.
- **Evidence/status:** KX Level 1/2/3 https://kx.com/glossary/level-1-level-2-and-level-3-market-data/ ; Investopedia market depth https://www.investopedia.com/terms/m/marketdepth.asp
- **Uncertainty/variants:** Hidden/iceberg orders; L2 vs. L3; spoofing/cancel-replace makes visible depth unreliable.

## footprint-order-flow

- **Family:** Volume / profile / order-flow / DOM
- **Aliases:** footprint chart, bid×ask, number bars, cluster chart
- **Definition:** A per-bar, per-price-level breakdown of traded volume into aggressive-buy (ask) vs. aggressive-sell (bid) components, revealing where and how aggressively each side traded inside a bar.
- **Boundaries:** Footprint is *executed* order flow (trades), not resting depth (order book). It requires tick/trade data with aggressor classification. Absent in spot FX (no consolidated trades).
- **Observable inputs:** Tick/trade data with buy/sell aggressor flags, per price level.
- **Recognition semantics:** For each price level in a bar, record bid-volume and ask-volume; delta = ask − bid. Imbalances, stacked imbalances, and absorption are read from these per-level splits.
- **Parameters/profiles:** bar type (time/tick/range/renko) — `published-convention`; imbalance threshold (e.g. 2–4×) — `published-convention` (platform-dependent).
- **Eligible roles:** confirmation, context (aggression/absorption), filter, timing refinement.
- **Market/data constraints:** Centralized-exchange tick data only (crypto spot, futures). Not available for spot FX.
- **Transfer notes:** NOT transferable to spot FX (no true order-flow data). Crypto-spot footprint is valid per exchange.
- **Evidence/status:** OrderFlow Labs footprint guide https://orderflowlabs.com/blogs/theblog/footprint-chart-guide ; Tape Delta footprint guide https://tapedelta.com/blog/what-is-a-footprint-chart-complete-guide
- **Uncertainty/variants:** Aggressor classification convention (buyer-maker vs. buyer-taker); bar-type choice; bid/ask label inversion confusion.

## cumulative-delta

- **Family:** Volume / profile / order-flow / DOM
- **Aliases:** CVD, session delta, cumulative volume delta
- **Definition:** The running session sum of delta (ask-volume minus bid-volume), used to compare aggressive buying/selling pressure against price action.
- **Boundaries:** CVD is *derived* order flow, not raw volume. It measures aggression, not direction; price-vs-CVD divergence is the common reading. Not available in spot FX.
- **Observable inputs:** Delta series (from footprint/order-flow data).
- **Recognition semantics:** CVD = cumulative Σ(ask−bid). Rising CVD with flat/falling price (or price making a new high on lower CVD) is read as divergence/exhaustion.
- **Parameters/profiles:** session anchor — `published-convention`; reset cadence — `published-convention`.
- **Eligible roles:** confirmation, divergence source, context.
- **Market/data constraints:** Centralized-exchange order-flow only. Not a spot-FX concept.
- **Transfer notes:** Not transferable to spot FX; crypto-spot CVD is valid per exchange.
- **Evidence/status:** Satotrades footprint guide (CVD section) https://satotrades.com/guides/footprint-charts-explained
- **Uncertainty/variants:** Delta sign convention; whether bar-level or session-level; CVD-vs-price divergence thresholds are discretionary.

## absorption

- **Family:** Volume / profile / order-flow / DOM
- **Aliases:** absorption, passive absorption, liquidity absorption
- **Definition:** An order-flow condition where large aggressive volume on one side fails to move price (or price reverses), implying the opposite side is passively absorbing it.
- **Boundaries:** Absorption is an *interpretive* order-flow read, not a raw fact. It is inferred from volume-vs-price-response mismatch. Not available in spot FX.
- **Observable inputs:** Order-flow/volume + price response (footprint, tape).
- **Recognition semantics:** Large bid/ask volume at a level without commensurate price advance/decline = absorption by resting liquidity. Read as a possible reversal/context cue.
- **Parameters/profiles:** volume threshold and price-response criterion — `unresolved`/`inferred`.
- **Eligible roles:** confirmation (fade/exit), context, timing refinement.
- **Market/data constraints:** Centralized-exchange order-flow only.
- **Transfer notes:** Not transferable to spot FX; crypto-spot only.
- **Evidence/status:** OrderFlow Labs footprint guide (absorption) https://orderflowlabs.com/blogs/theblog/footprint-chart-guide
- **Uncertainty/variants:** Distinguishing genuine absorption from order replenishment is inherently ambiguous.

## fair-value-gap

- **Family:** Volume / profile / order-flow / DOM
- **Aliases:** FVG, imbalance (SMC), price imbalance
- **Definition:** A three-candle zone where price moved so fast it left an untested gap between the first candle's extreme and the third candle's extreme, read as an imbalance price may return to "fill."
- **Boundaries:** FVG is an *inference from candle shape* (price-only), not measured order flow — despite the "imbalance" name, it is not the same as a footprint volume imbalance. Distinct from an order block (a single candle) and from a supply/demand zone (a basing area).
- **Observable inputs:** OHLC series.
- **Recognition semantics:** In a bullish FVG, candle-3's low is above candle-1's high, leaving an open gap. Price retracing into the gap is read as "mitigation/fill."
- **Parameters/profiles:** none intrinsic (gap exists or not); fill level (50% vs. 100%) — `inferred`/strategy-specific; displacement strength threshold — `unresolved`.
- **Eligible roles:** level reference, trigger (retrace into gap), context, target (gap fill).
- **Market/data constraints:** Price-only; venue-agnostic (works in forex and crypto spot).
- **Transfer notes:** Fully transferable (price-only). Originates in ICT/SMC retail commentary.
- **Evidence/status:** Real Backtesting FVG explainer https://realbacktesting.com/academy/order-blocks-and-fair-value-gaps-explained.html
- **Uncertainty/variants:** FVG vs. footprint "imbalance" are different concepts; fill depth (50%/100%) is discretionary; wick-vs-body definitions vary.

## order-block

- **Family:** Volume / profile / order-flow / DOM
- **Aliases:** OB, institutional order block, demand/supply block (SMC)
- **Definition:** A single candle — the last opposite-direction candle before an impulsive displacement — treated as a zone where large orders were left unfilled and to which price may return.
- **Boundaries:** An order block is *one candle*, distinct from a supply/demand zone (a multi-candle base) and from an FVG (a wick gap). Despite the name, it is an *inference about institutional orders*, not a recorded order — there is no data proving who placed orders there.
- **Observable inputs:** OHLC series.
- **Recognition semantics:** Identify the last opposite-close candle before a displacement that breaks structure; draw its open-to-extreme range. First return is read as "mitigation"; each retest degrades it.
- **Parameters/profiles:** candle-range definition (body vs. full wick; 50% "mean threshold") — `unresolved`/`published-convention` within SMC; displacement/break requirements — `inferred`.
- **Eligible roles:** level reference, trigger (return to OB), context, stop reference.
- **Market/data constraints:** Price-only; venue-agnostic. Works in forex and crypto spot without order data.
- **Transfer notes:** Fully transferable; originates in ICT/SMC retail forex/futures commentary.
- **Evidence/status:** LiquidityScan order-block vs. S/D https://liquidityscan.io/blog/order-block-vs-supply-and-demand-zone-the-real-difference ; FXOpen order blocks https://fxopen.com/blog/en/order-blocks-and-breaker-blocks-of-the-smart-money-concept/
- **Uncertainty/variants:** The "institutional intent" framing is unverifiable narrative; boundaries (open-to-high vs. open-to-close vs. full range) vary by school.

## supply-demand-zone

- **Family:** Volume / profile / order-flow / DOM
- **Aliases:** S/D zone, supply/demand area, basing zone
- **Definition:** A horizontal area of prior consolidation (a "base") from which price departed with force, treated as a zone where unfilled orders may remain and where price may react on return.
- **Boundaries:** A zone is a *multi-candle base*, distinct from an order block (single candle) and an FVG (wick gap). It is chart-inferred, not measured order flow.
- **Observable inputs:** OHLC series.
- **Recognition semantics:** Mark the base (1–6 consolidation candles) before an imbalanced departure; the zone spans base extreme to base edge (distal/proximal lines). Return to the zone is the reaction setup.
- **Parameters/profiles:** base width (1–6 candles) — `published-convention` (Sam Seiden school); proximal/distal line convention — `published-convention`; freshness (untested zones preferred) — `inferred`.
- **Eligible roles:** level reference, trigger, context, stop reference.
- **Market/data constraints:** Price-only; venue-agnostic.
- **Transfer notes:** Fully transferable; popularized by Sam Seiden / Online Trading Academy for FX.
- **Evidence/status:** LiquidityScan S/D vs. OB https://liquidityscan.io/blog/order-block-vs-supply-and-demand-zone-the-real-difference
- **Uncertainty/variants:** Zone boundaries are discretionary (unlike the candle-precise OB); rally-base-drop/drop-base-rally taxonomy is Seiden-specific.

## liquidity-sweep

- **Family:** Volume / profile / order-flow / DOM
- **Aliases:** stop hunt, liquidity grab, sweep of highs/lows, equal highs/lows
- **Definition:** A price excursion that briefly breaks a cluster of equal highs/lows (assumed stop/limit clusters) before reversing, interpreted in SMC as institutions clearing liquidity to fuel a move.
- **Boundaries:** A liquidity sweep is an *interpretation of price touching a level cluster*, not measured order data — the "stop hunt" narrative is unverifiable from OHLC alone. Distinct from a genuine breakout that holds.
- **Observable inputs:** OHLC series; identified equal-high/equal-low clusters.
- **Recognition semantics:** Detect a wick beyond equal highs/lows followed by rapid reversal into the prior range. The reversal-after-poke distinguishes a sweep from a breakout.
- **Parameters/profiles:** cluster tolerance (how "equal") — `inferred`; reversal confirmation (close back inside) — `unresolved`.
- **Eligible roles:** context, trigger (sweep-and-reverse), invalidation (breakout holds = not a sweep), confluence weight.
- **Market/data constraints:** Price-only; venue-agnostic. Works in forex and crypto spot.
- **Transfer notes:** Fully transferable (price-only); the institutional-stop-hunt *narrative* is not evidenced by the data itself.
- **Evidence/status:** `ontology-seed — needs source evidence`; the equal-high/low liquidity-pool concept is SMC-standard (see forex-basics SMC https://forex-basics.com/analysis/smart-money-concepts-smc/).
- **Uncertainty/variants:** The causal "institution hunts your stop" story is heavily contested and not empirically established; distinguish the observable (poke+reversal) from the narrative.

## spot-fx-tick-volume

- **Family:** Volume / profile / order-flow / DOM
- **Aliases:** tick volume, FX volume proxy
- **Definition:** The broker/feed-specific count of price changes (ticks) over a period, used in spot FX as a *proxy* for activity because true traded volume is not consolidated.
- **Boundaries:** This is NOT real volume — it is a tick-count from one broker/feed, which varies by provider and is not comparable across brokers. It must be explicitly separated from centralized-exchange volume.
- **Observable inputs:** A tick/quote stream from a specific FX broker/feed.
- **Recognition semantics:** Count ticks per bar. Used as an activity proxy in the absence of consolidated volume; interpretations are weaker and broker-relative.
- **Parameters/profiles:** none intrinsic; the feed source is the critical parameter — `unresolved`.
- **Eligible roles:** weak context/confirmation proxy (activity), filter.
- **Market/data constraints:** Spot-FX-only. Meaning is broker/feed-dependent; never treat as market-wide volume.
- **Transfer notes:** This is the *FX-specific* counterpart to exchange-volume; the two must never be merged. Crypto spot has real volume, so tick-volume proxies are unnecessary there.
- **Evidence/status:** `ontology-seed — needs source evidence`; the tick-vs-real-volume distinction is standard FX broker education (e.g. Babypips volume lessons).
- **Uncertainty/variants:** Some brokers provide "real" aggregated volume from LPs; whether a feed is tick-count or aggregated real volume must be confirmed per provider.

## currency-pair-correlation

- **Family:** Intermarket / currency / correlation
- **Aliases:** pair correlation, FX correlation, correlation coefficient
- **Definition:** The statistical tendency of two instruments' returns to move together (positive) or oppositely (negative), measured by a correlation coefficient in [−1, +1].
- **Boundaries:** Correlation is a *statistical relationship*, not a causal one and not a directional signal by itself. It is window/timeframe-dependent and unstable. Distinct from currency-strength (a single-currency measure) and from exposure (portfolio-level).
- **Observable inputs:** Return series of two (or more) instruments.
- **Recognition semantics:** Compute Pearson correlation of returns over a window. |r| > ~0.7 is commonly treated as "significant" positive/negative. Used to flag double-counted risk or to confirm a move via a correlated pair.
- **Parameters/profiles:** window (days/periods) — `inferred`; significance threshold (±0.7) — `published-convention`; timeframe — `inferred`.
- **Eligible roles:** filter (avoid correlated over-exposure), confirmation (correlated pair follows through), context.
- **Market/data constraints:** Return-based; venue-agnostic. Correlations drift and can invert during crises; they are not stable properties.
- **Transfer notes:** Transferable to crypto as inter-asset correlation (e.g. BTC–alts), but FX pair correlations (e.g. EUR/USD–GBP/USD) are FX-specific; crypto correlations are to BTC/USD and risk assets.
- **Evidence/status:** Titan FX currency correlation https://research.titanfx.com/forex-trading/currency-correlation
- **Uncertainty/variants:** |r| threshold; window length; whether computed on levels or returns (returns correct); stability over time is poor.

## dollar-index

- **Family:** Intermarket / currency / correlation
- **Aliases:** DXY, USDX, US Dollar Index, Dixie
- **Definition:** A weighted index of the US dollar against a basket of six currencies (EUR, JPY, GBP, CAD, SEK, CHF), used as a broad USD-strength gauge and intermarket context for USD pairs.
- **Boundaries:** DXY is a *synthetic index*, not a traded spot pair, and its weights (EUR 57.6%) are fixed/legacy — it is a USD proxy, not a pure "dollar strength" truth. Distinct from any specific pair and from crypto USD pairs (which have no index counterpart).
- **Observable inputs:** The index value (published/derived) or its component pairs.
- **Recognition semantics:** Rising DXY = broad USD strength; falling = USD weakness. Used to contextualize USD-pair direction and to filter/confirm USD exposure.
- **Parameters/profiles:** weights (EUR 57.6%, JPY 13.6%, GBP 11.9%, CAD 9.1%, SEK 4.2%, CHF 3.6%) — `source-stated` (ICE); indexing factor 50.1435 — `source-stated`.
- **Eligible roles:** context, filter, confirmation (USD bias), intermarket reference.
- **Market/data constraints:** Computed/published by ICE; not directly tradable as spot. Only relevant to USD-denominated analysis; crypto/USD has no analogous index.
- **Transfer notes:** Relevant to spot FX (USD pairs) as context; of limited direct use for crypto spot except as a macro USD view. Do not treat DXY as a crypto signal.
- **Evidence/status:** Wikipedia U.S. Dollar Index https://en.wikipedia.org/wiki/U.S._Dollar_Index ; Investopedia USDX https://www.investopedia.com/terms/u/usdx.asp
- **Uncertainty/variants:** Fixed legacy weights vs. trade-weighted Fed indexes; DXY vs. trade-weighted dollar are different measures.

## currency-strength

- **Family:** Intermarket / currency / correlation
- **Aliases:** currency strength meter, relative currency strength
- **Definition:** A per-currency measure of relative strength derived from a currency's performance across its pairs, used to identify the strongest/weakest currencies at a point in time.
- **Boundaries:** Currency strength is *synthesized from multiple pairs*, not a single price series; its value depends entirely on the construction method and pair basket. Distinct from a single pair's direction and from DXY (USD-only).
- **Observable inputs:** Multiple pair series sharing the target currency.
- **Recognition semantics:** Aggregate a currency's returns across its pairs (e.g. average normalized momentum) into a single strength score; compare currencies to pick strong-vs-weak pairings.
- **Parameters/profiles:** construction (momentum window, normalization, basket) — `unresolved`/`inferred`; no standardized formula.
- **Eligible roles:** context, filter (trade strong-vs-weak), confirmation, universe selection.
- **Market/data constraints:** FX-specific (needs multiple currency pairs). Crypto has no direct analog except alt/BTC relative strength.
- **Transfer notes:** FX-specific; transfers to crypto only as a loose "relative strength vs. BTC/USD" idea, not as a currency-strength meter.
- **Evidence/status:** `ontology-seed — needs source evidence`; currency-strength meters are common broker tools but lack a single canonical construction.
- **Uncertainty/variants:** Construction method is the dominant ambiguity; no standard basket or window.

## intermarket-risk-regime

- **Family:** Intermarket / currency / correlation
- **Aliases:** risk-on / risk-off, RORO, cross-asset risk
- **Definition:** A broad market state where correlated "risk" assets move together (risk-on) or money rotates into havens (risk-off), used as macro context for FX and crypto.
- **Boundaries:** RORO is a *correlation/regime* read across asset classes, not a single-instrument signal. It is a heuristic classification, not a precise statistic. Distinct from a single instrument's trend.
- **Observable inputs:** Cross-asset series (equity index, VIX, yields, commodity/FX havens, crypto).
- **Recognition semantics:** Classify risk-on/off from co-movement of risk proxies (e.g. equities up + VIX down + carry currencies up = risk-on). Multiple proxies, heuristic.
- **Parameters/profiles:** proxy set — `inferred`; thresholds — `unresolved`.
- **Eligible roles:** context, filter (trade direction per regime), confirmation, exposure guard.
- **Market/data constraints:** Needs cross-asset data; for crypto, BTC often acts as a risk asset but the relationship is unstable. VIX is equity-specific.
- **Transfer notes:** The *concept* transfers to crypto, but the proxy set and the stability of relationships differ; label correlations as unstable.
- **Evidence/status:** `ontology-seed — needs source evidence`; RORO is standard macro vocabulary without a single canonical URL fixed this wave.
- **Uncertainty/variants:** Proxy selection and regime thresholds are discretionary; crypto's risk-asset status has shifted over time.

## safe-haven-demand

- **Family:** Intermarket / currency / correlation
- **Aliases:** haven bid, flight to safety, safe-haven flow
- **Definition:** The observable shift of flows into traditional safe-haven instruments (USD, JPY, CHF, gold, sometimes US Treasuries) during risk-off episodes.
- **Boundaries:** Haven demand is a *flow/regime observation across assets*, not a single-instrument signal and not a property of any one currency. Distinct from a currency's own trend. The identity of "safe havens" is conventional, not guaranteed.
- **Observable inputs:** Cross-asset price series (USD/JPY/CHF/gold/VIX/equities).
- **Recognition semantics:** Detect simultaneous strength in conventional havens + weakness in risk assets; read as flight-to-safety context.
- **Parameters/profiles:** haven basket (USD/JPY/CHF/gold) — `published-convention` (may be outdated); thresholds — `unresolved`.
- **Eligible roles:** context, filter, confirmation (haven moves confirm risk-off), intermarket reference.
- **Market/data constraints:** Cross-asset; the "haven" classification can break down in specific regimes (e.g. 2022 USD-yen moves).
- **Transfer notes:** Transfers to crypto as context (e.g. gold/JPY vs. BTC during stress), but crypto's haven status is contested; label as inference.
- **Evidence/status:** `ontology-seed — needs source evidence`; safe-haven classification is standard macro convention without a single fixed citation this wave.
- **Uncertainty/variants:** Which assets count as havens shifts by era; the relationship is not stable.

## economic-calendar-event

- **Family:** News / event-state (durable)
- **Aliases:** news event, scheduled release, data release, high-impact event
- **Definition:** A scheduled macroeconomic/central-bank release (NFP, CPI, rate decision, etc.) with an expected time and impact rating, treated as a durable *schedule primitive* rather than a live snapshot.
- **Boundaries:** This is the *schedule/classification* of an event, not live data, not the actual released number, and not a directional view. It is a time-anchored risk marker, not a market condition that exists "now" in the price.
- **Observable inputs:** A calendar feed (event id, time, currency, impact class, forecast/previous fields).
- **Recognition semantics:** Look up the next/current scheduled events; classify by impact (high/medium/low) and proximity. Bind as a window-avoidance or event-trading gate.
- **Parameters/profiles:** impact classification (high/medium/low) — `published-convention`; avoidance window (e.g. ±15–30 min) — `inferred`.
- **Eligible roles:** pre-trigger filter (avoid/target windows), context, timing constraint.
- **Market/data constraints:** Event times are venue/calendar-specific; "high impact" is a provider rating, not an intrinsic property. Applies to FX (macro) more than crypto (which has its own event types, e.g. unlocks, listings).
- **Transfer notes:** The *schedule primitive* transfers, but crypto's "high-impact events" are different (halvings, unlocks, regulatory headlines), not the same FX calendar.
- **Evidence/status:** PipJournal economic calendar https://pipjournal.ai/learn/glossary/economic-calendar
- **Uncertainty/variants:** Impact ratings vary by provider; "high impact" is a convention, not a measurement.

## news-event-window

- **Family:** News / event-state (durable)
- **Aliases:** news blackout window, pre/post-release window, event window
- **Definition:** A time window around a scheduled event during which a strategy restricts or modifies behavior (spreads widen, liquidity thins, price becomes erratic).
- **Boundaries:** This is a *timing guard tied to an event*, not the event itself and not a market condition in the price. Distinct from a generic time-of-day window (it is event-anchored).
- **Observable inputs:** Event schedule + current time.
- **Recognition semantics:** Define a pre/post interval around event time; suppress or alter entries/parameters within it.
- **Parameters/profiles:** window (e.g. −15/+15 min) — `inferred`; behavior (block vs. widen stops vs. allow limit-only) — `unresolved`.
- **Eligible roles:** pre-trigger filter (hard gate), context, execution-quality modifier.
- **Market/data constraints:** Event-schedule dependent; FX windows are well-defined (calendar), crypto windows depend on the event type.
- **Transfer notes:** Transferable as a *guard*; the event set and window length are market-specific.
- **Evidence/status:** `ontology-seed — needs source evidence`; the widening/avoidance practice is documented in economic-calendar sources above.
- **Uncertainty/variants:** Window length and behavior are discretionary; some events (FOMC) need much wider windows than others.

## news-event-class

- **Family:** News / event-state (durable)
- **Aliases:** event type, release category
- **Definition:** A durable classification of scheduled events by type (rate decision, inflation, employment, growth, central-bank speech, and crypto-specific types like unlock/halving), used to route different handling.
- **Boundaries:** A *taxonomy* of event types, not a live event and not a directional view. Kept as a durable primitive (type identity) while live values/snapshots are excluded.
- **Observable inputs:** Event metadata (type tag).
- **Recognition semantics:** Map an event to its class to select the appropriate window/behavior (e.g. rate decisions → widest window; minor surveys → narrow).
- **Parameters/profiles:** class taxonomy — `unresolved`/`inferred` (no standard cross-market taxonomy).
- **Eligible roles:** context, filter routing, timing constraint.
- **Market/data constraints:** Class sets differ between FX (macro) and crypto (protocol/market events); keep them separate.
- **Transfer notes:** The *idea* of event classes transfers, but the class vocabularies are market-specific.
- **Evidence/status:** `ontology-seed — needs source evidence`; informed by economic-calendar impact taxonomies above.
- **Uncertainty/variants:** No standard cross-market taxonomy; class boundaries (e.g. "medium vs. high impact") are provider-defined.

## support-resistance

- **Family:** Pattern quality / distance / viability
- **Aliases:** S/R, support level, resistance level, horizontal level
- **Definition:** A price level or zone where price has historically reversed or stalled (support below, resistance above), treated as a candidate reaction area.
- **Boundaries:** S/R is a *location*, not a signal — a reaction is a hypothesis, not a guarantee. Distinct from a session (time) and from a moving average (dynamic vs. horizontal). It is chart-derived, not an order-flow fact.
- **Observable inputs:** OHLC series (swing pivots).
- **Recognition semantics:** Identify price zones of repeated rejection/rotation. Levels are usually drawn at swing highs/lows; "strength" is graded by number of touches, recency, and confluence.
- **Parameters/profiles:** pivot-detection strength — `inferred`; zone vs. line (tolerance) — `unresolved`; touch-count grading — `inferred`.
- **Eligible roles:** location/level, filter, trigger (breakout/bounce), stop/target reference, context.
- **Market/data constraints:** Price-only; venue-agnostic. Subjective — different traders draw different levels.
- **Transfer notes:** Fully transferable to forex and crypto spot.
- **Evidence/status:** `published-convention` — S/R is foundational TA (Investopedia support/resistance).
- **Uncertainty/variants:** Zone width, wick-vs-body extremes, and level strength grading are all discretionary.

## distance-to-level

- **Family:** Pattern quality / distance / viability
- **Aliases:** proximity to level, distance to entry, room to level
- **Definition:** The price distance from the current price to a target reference level (entry, support/resistance, target), used to judge whether a setup has sufficient "room."
- **Boundaries:** A *spatial measure*, not a signal. It compares two locations; it says nothing about probability. Distinct from reward-risk-distance (which compares two distances).
- **Observable inputs:** Current price + a reference level.
- **Recognition semantics:** distance = |price − level| (in price units or normalized by ATR/ADR). Used to reject setups where the target is too close or the stop too far.
- **Parameters/profiles:** normalization (raw/ATR%/ADR%) — `inferred`; minimum-distance threshold — `unresolved`.
- **Eligible roles:** filter (setup viability), context, parameter base.
- **Market/data constraints:** Price-only; venue-agnostic.
- **Transfer notes:** Fully transferable.
- **Evidence/status:** `ontology-seed — needs source evidence`.
- **Uncertainty/variants:** Raw vs. volatility-normalized distance; threshold is discretionary.

## reward-risk-distance

- **Family:** Pattern quality / distance / viability
- **Aliases:** risk-reward ratio, R:R, R-multiple, reward-to-risk
- **Definition:** The ratio of the distance from entry to target versus entry to stop, used to express a setup's potential payoff per unit of risk.
- **Boundaries:** R:R is a *geometry of planned exit distances*, not a probability and not a live outcome. It is computed from three prices (entry, stop, target), so it depends on those being defined. Distinct from a win rate and from realized return.
- **Observable inputs:** Entry price, stop price, target price.
- **Recognition semantics:** R:R = |target − entry| / |entry − stop|. Higher = more reward per risk. Used as a setup-viability gate.
- **Parameters/profiles:** minimum acceptable R:R (e.g. ≥2) — `published-convention` (common rule of thumb, not universal); no intrinsic default.
- **Eligible roles:** filter (viability), context, parameter base.
- **Market/data constraints:** Price-only; venue-agnostic; depends on having defined stop/target (which may be unresolved in source strategies).
- **Transfer notes:** Fully transferable.
- **Evidence/status:** Investopedia risk/reward ratio https://www.investopedia.com/terms/r/riskrewardratio.asp
- **Uncertainty/variants:** Convention order (risk:reward vs. reward:risk) is frequently reversed across sources; the 1:2/1:3 "minimums" are rules of thumb, not proven.

## confluence-count

- **Family:** Pattern quality / distance / viability
- **Aliases:** confluence, signal agreement, stacking
- **Definition:** A measure of how many independent signals/levels agree at a point (e.g. a level that is simultaneously a Fibonacci, a prior high, and a moving average), used as a setup-quality gate.
- **Boundaries:** Confluence is a *composition/count of agreeing signals*, not a signal itself. It is a candidate binding (AND/score), not an intrinsic class. Distinct from any single level or indicator.
- **Observable inputs:** Multiple level/indicator primitives evaluated at the same price/time.
- **Recognition semantics:** Count (or score) distinct primitives agreeing at a price. Higher count = "stronger" confluence (a heuristic, not an empirical probability).
- **Parameters/profiles:** minimum count/score — `unresolved`; whether primitives must be independent — `unresolved`; weighting scheme — `unresolved`.
- **Eligible roles:** filter, confirmation, context, setup-quality gate.
- **Market/data constraints:** Depends on the constituent primitives; venue-agnostic where constituents are price-only.
- **Transfer notes:** Fully transferable.
- **Evidence/status:** `ontology-seed — needs source evidence`; "confluence" is ubiquitous in trading commentary (see Fibonacci confluence discussion above) without a canonical URL.
- **Uncertainty/variants:** Independence of signals (many "confluences" are the same signal restated); count vs. weighted score; whether confluence is a first-class concept at all.

## pattern-quality-grade

- **Family:** Pattern quality / distance / viability
- **Aliases:** setup quality, signal strength, grade/score
- **Definition:** An ordinal grade assigned to a detected pattern/setup summarizing how well it satisfies its defining criteria (e.g. A/B/C or high/medium/low).
- **Boundaries:** A quality grade is a *subjective/normalized assessment*, not a raw fact and not a probability. It must not be confused with empirical edge. It is a downstream/normalization choice, not intrinsic to any pattern.
- **Observable inputs:** The pattern detection result + its defining criteria.
- **Recognition semantics:** Score a setup against its checklist (confluence, displacement, alignment); bucket into an ordinal grade.
- **Parameters/profiles:** grading scale — `unresolved`; checklist/weights — `unresolved`.
- **Eligible roles:** filter (minimum grade), confirmation weight, context.
- **Market/data constraints:** Venue-agnostic; quality criteria are strategy-specific.
- **Transfer notes:** Fully transferable.
- **Evidence/status:** `ontology-seed — needs source evidence`; grading appears in SMC/ICT teaching but has no canonical formula.
- **Uncertainty/variants:** Grade scales and weights are entirely discretionary; risk of dressing subjective judgment as objective score.

## timeframe-alignment

- **Family:** Pattern quality / distance / viability
- **Aliases:** multi-timeframe alignment, MTF confluence
- **Definition:** The condition that two or more timeframes agree on direction or setup state, used to raise/lower confidence in a lower-timeframe setup.
- **Boundaries:** Alignment is a *coordination condition across timeframes*, not a signal on one timeframe. Distinct from higher-timeframe-trend-bias (a specific directional constraint) — alignment can be any measure, and can be partial.
- **Observable inputs:** Multi-timeframe OHLC (or resampled).
- **Recognition semantics:** Evaluate the same or related primitives on multiple timeframes and require agreement (e.g. all aligned bullish).
- **Parameters/profiles:** timeframe set — strategy-specific `inferred`; which measure must align — `unresolved`; partial-agreement tolerance — `unresolved`.
- **Eligible roles:** filter, confirmation, context.
- **Market/data constraints:** Needs multi-timeframe data; alignment quality differs between forex (session gaps) and crypto (continuous).
- **Transfer notes:** Transferable; the timeframe ladder is a strategy decision.
- **Evidence/status:** `ontology-seed — needs source evidence`.
- **Uncertainty/variants:** How many timeframes must align; whether partial alignment "counts"; whether alignment is binary or graded.

---

## Deduplication notes

- **Volume vs. tick volume:** `exchange-volume` (centralized truth) and `spot-fx-tick-volume` (broker proxy) are deliberately split; they must never be merged. `volume-profile`, `vwap`, `order-book-depth`, `footprint-order-flow`, `cumulative-delta`, and `absorption` all depend on centralized-exchange data and carry explicit spot-FX non-transferability notes.
- **Order block vs. supply-demand-zone vs. fair-value-gap:** kept as three entries because they are geometrically distinct (single candle vs. multi-candle base vs. wick gap) even though they overlap in practice and often mark the same area.
- **Momentum family:** `momentum`, `rate-of-change`, `rsi`, `macd`, `stochastic-oscillator` are distinct members; `oscillator` is the family, `momentum-divergence` and `indicator-divergence` are the operations. `indicator-divergence` generalizes `momentum-divergence`.
- **Moving-average family:** `moving-average` (family), `moving-average-trend` (one-MA reading), `moving-average-crossover` (two-MA event) are separate; `crossover` is the generic operation.
- **Volatility family:** ATR (range), Bollinger (stdev band), realized-volatility (return dispersion), implied-volatility (forward/options), Donchian (extremes), Keltner (ATR band), ADR (session range) are distinct measures; `band-envelope` is their family.
- **Correlation vs. strength vs. regime:** `currency-pair-correlation` (pair relationship), `currency-strength` (single currency across pairs), `dollar-index` (USD basket), `intermarket-risk-regime` and `safe-haven-demand` (cross-asset states) are distinct levels of aggregation.
- **Confluence:** treated as a candidate composition (`confluence-count`), not a permanent class, consistent with the shared contract's provisional stance.

## Unresolved taxonomy questions

1. Whether `confluence` should be a first-class binding type or only an AND/score composition over other bindings (shared-contract question 1) remains open; `confluence-count` is offered as the measurable version.
2. The exact boundary between "filter" and "confirmation" — and whether timing (pre-trigger vs. synchronous vs. post-trigger) should be a schema field on every binding — is unresolved; timing eligibility is recorded per-entry here as a stopgap.
3. `market-regime` has no standardized state taxonomy (2/3/4-state schemes vary); a STRATS-standardized regime vocabulary would need a decision.
4. `news-event-class` has no cross-market taxonomy; FX macro event classes and crypto event classes likely need separate vocabularies.
5. Standardized numeric defaults (RSI 70/30, ADX 20/25, R:R ≥2, correlation ±0.7) are recorded as `published-convention` only; whether STRATS adopts them as standardized defaults is a deliberate decision left open.
6. `realized-volatility` vs. `historical-volatility` naming (interchangeable vs. distinct) is source-dependent and unresolved.
7. Whether `session-open-price` and `higher-timeframe-reference` belong here or in the location/level worker's scope is a boundary question — they are included as context/filter references but flagged as location-derived.
