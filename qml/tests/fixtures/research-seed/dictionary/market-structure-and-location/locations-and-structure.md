# Candidate Dictionary — Location / Level and Market-Structure Primitives

Worker A output. Scope: price references, zones, and structures that can serve as a *location* in a strategy, plus the market-structure vocabulary those locations are read from. This file contains **primitives only** — no role bindings, no strategy graphs, no edge claims.

## Coverage table

| Family | Entries | IDs |
|---|---|---|
| Swing points & structural ranges | 7 | swing-high, swing-low, swing-sequence, structural-range, break-of-structure, change-of-character, fractal-pivot |
| Support/resistance & supply/demand | 9 | support-level, resistance-level, horizontal-level, supply-zone, demand-zone, zone-base, zone-freshness, polarity-flip, round-number |
| Session/day/week/month-derived references | 9 | session-high, session-low, session-range, previous-day-high, previous-day-low, previous-week-extreme, previous-month-extreme, opening-range, daily-open |
| Liquidity, gaps, imbalances, blocks (SMC/ICT) | 13 | liquidity-pool, directional-liquidity, equal-highs-lows, liquidity-sweep, fair-value-gap, order-block, breaker-block, mitigation-block, rejection-block, price-gap, imbalance, liquidity-void, premium-discount |
| Dynamic/statistical references | 11 | moving-average, vwap, bollinger-bands, keltner-channel, donchian-channel, moving-average-envelope, atr, pivot-point, camarilla-pivot, fibonacci-retracement, trendline |
| Chart-pattern boundaries & event anchors | 3 | pattern-boundary, event-anchor, measured-move |
| Volume-profile references | 4 | volume-profile, point-of-control, value-area, volume-node |
| **Total** | **56** | |

Scope guardrails applied throughout:

- A **session/timeframe is not a price level.** Only session-derived *price references* (high, low, range, open) are entries here. The session itself is a context primitive (Worker C scope), not a location.
- A **session high/low** (an observable price) is distinct from a **session context** (a time window). Entries below are the former.
- An **observable price structure** (e.g. a swing high) is distinct from a **strategy-specific location role** (e.g. "my entry level"). The role is assigned later by a strategy binding; nothing here is permanently a "level" for any strategy.

---

## swing-high — Swing High

- **Family:** Swing points & structural ranges
- **Aliases:** pivot high, local high, reaction high, fractal high (Bill Williams)
- **Definition:** A local upper turning point: a bar (or small cluster) whose high is higher than the highs of a fixed number of bars on each side, after which price trades lower.
- **Boundaries:** Not a "resistance level" (a swing high is a single observed pivot; resistance is an interpretive role/zone). Not the same as a higher high (a swing high is one pivot; "higher high" is a *comparison* between two swing highs). Not a session high (which is time-anchored, not structure-anchored).
- **Observable inputs:** OHLC bar series; a lookback/strength parameter N.
- **Recognition semantics:** For a chosen N, mark bar t as a swing high when `high[t] > high[t±i]` for all `i in 1..N`. Confirmation is inherently lagged by N bars. Wicks vs bodies: most conventions use the high (wick extreme), not the close. No universal N; the same chart yields different pivots at different N.
- **Parameters/profiles:** `strength N` — `published-convention` fractal default N=2 (Bill Williams); `source-stated` N=3–5 typical on 5-min futures (dhawal.org); `unresolved` for a STRATS-wide default. `use-wick` vs `use-body` — `unresolved`.
- **Eligible roles:** location, trigger (break of a swing high), invalidation (stop reference), context (structure reading), confirmation.
- **Market/data constraints:** Pure OHLC; no volume needed. Timeframe-dependent — a swing high on M5 is not a swing high on H1. Repainting risk if evaluated intrabar.
- **Transfer notes:** Fully transferable to Forex spot and crypto spot (OHLC is universal). No venue-specific dependency.
- **Evidence/status:** https://sdk-trading.com/en/price-action/market-structure/swing-highs-and-swing-lows ; https://bharathshiksha.com/articles-html/market-structure-deep-dive.html ; https://dhawal.org/research/futures-ta/chapters/ch02-market-structure.html
- **Uncertainty/variants:** Fractal (N=2) vs "significant swing" (ATR-filtered, N=3–5) definitions conflict. Whether confirmation requires a close beyond the pivot or just a wick is discretionary.

## swing-low — Swing Low

- **Family:** Swing points & structural ranges
- **Aliases:** pivot low, local low, reaction low, fractal low
- **Definition:** A local lower turning point: a bar (or small cluster) whose low is lower than the lows of a fixed number of bars on each side, after which price trades higher.
- **Boundaries:** Not a "support level" (observed pivot vs interpretive role). Not a lower low (single pivot vs comparison). Not a session low (time-anchored).
- **Observable inputs:** OHLC bar series; lookback/strength N.
- **Recognition semantics:** Mirror of swing-high: mark bar t when `low[t] < low[t±i]` for `i in 1..N`. Same lag and N-sensitivity caveats.
- **Parameters/profiles:** `strength N` — `published-convention` N=2 fractal; `source-stated` N=3–5; `unresolved` STRATS default. `use-wick` vs `use-body` — `unresolved`.
- **Eligible roles:** location, trigger, invalidation, context, confirmation.
- **Market/data constraints:** Pure OHLC; timeframe-dependent; intrabar repainting.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** https://sdk-trading.com/en/price-action/market-structure/swing-highs-and-swing-lows ; https://bharathshiksha.com/articles-html/market-structure-deep-dive.html
- **Uncertainty/variants:** Same fractal-vs-significant-swing conflict as swing-high.

## swing-sequence — Higher High / Higher Low / Lower High / Lower Low

- **Family:** Swing points & structural ranges
- **Aliases:** HH/HL/LH/LL, market structure, trend structure, swing structure
- **Definition:** The ordered comparison of consecutive swing highs and swing lows, read as a sequence. HH = a swing high above the prior swing high; HL = a swing low above the prior swing low; LH = a swing high below the prior swing high; LL = a swing low below the prior swing low.
- **Boundaries:** This is a *sequence/relationship*, not a single price level. It is the raw material for trend/range classification but is not itself "the trend" (trend is an interpretation). Not to be confused with break-of-structure (a specific violation event).
- **Observable inputs:** A confirmed set of swing highs and swing lows (see swing-high/swing-low).
- **Recognition semantics:** After each newly confirmed swing, compare it to the most recent prior swing of the same kind. Uptrend = HH+HL sequence; downtrend = LH+LL; range = mixed/alternating. Minimum length for a trend label is typically two confirmed swings of each kind (four pivots).
- **Parameters/profiles:** `min-swings-for-trend` — `source-stated` 4 pivots (dhawal.org); `unresolved` STRATS default. Inherits swing `strength N`.
- **Eligible roles:** context (regime), filter, confirmation, location (the last HL/LL as a reference).
- **Market/data constraints:** OHLC only; depends entirely on the swing-detection parameterization; timeframe-dependent.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** https://bharathshiksha.com/articles-html/market-structure-deep-dive.html ; https://dhawal.org/research/futures-ta/chapters/ch02-market-structure.html
- **Uncertainty/variants:** "Trend" vs "range" threshold is discretionary; some pedagogies require closes, others wicks.

## structural-range — Trading Range / Consolidation

- **Family:** Swing points & structural ranges
- **Aliases:** range, consolidation, sideways market, balance, chop, box
- **Definition:** A region of price action where swing highs and swing lows alternate without a clean HH/HL or LH/LL sequence — price rotates between a roughly horizontal upper and lower boundary.
- **Boundaries:** A range is a *structure*, not a single level. Its upper/lower boundaries are the levels (see horizontal-level). Not the same as a supply/demand zone (a range is a two-sided structure; a zone is a one-sided origin of an impulse).
- **Observable inputs:** Swing sequence; optionally the high/low extremes of the range.
- **Recognition semantics:** Detect when the swing-sequence fails to produce a directional pattern over some window; the range is bounded by the most recent significant swing high (top) and swing low (bottom). "Balance" (market-profile language) is the same idea expressed as time/volume distribution.
- **Parameters/profiles:** `min-rotations` to declare a range — `unresolved`. `boundary-tolerance` — `unresolved`.
- **Eligible roles:** context (regime), location (range high/low as levels), filter, trigger (range breakout).
- **Market/data constraints:** OHLC only; timeframe-dependent; a range on one timeframe may be a trend on another.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** https://dhawal.org/research/futures-ta/chapters/ch02-market-structure.html
- **Uncertainty/variants:** No agreed minimum number of touches/rotations to declare a range; "range" vs "flag/consolidation within trend" boundary is discretionary.

## break-of-structure — Break of Structure (BOS)

- **Family:** Swing points & structural ranges
- **Aliases:** BOS, structure break, swing break
- **Definition:** Price trading through a prior swing point in the direction of the prevailing sequence — e.g. a close above the most recent swing high in an uptrend — confirming continuation of that structure.
- **Boundaries:** BOS is a *continuation* event (breaks in trend direction); change-of-character is a *reversal* event (breaks against trend). Not a level itself — it is an event that *validates or invalidates* levels. Not the same as a liquidity sweep (which is about taking out resting orders, though they often coincide).
- **Observable inputs:** Confirmed swing highs/lows; current price/close.
- **Recognition semantics:** In an uptrend, a BOS occurs when price closes (or trades, per convention) above the last confirmed swing high. In a downtrend, below the last confirmed swing low. Whether "break" requires a close or just a wick is a key discretionary split.
- **Parameters/profiles:** `break-basis` (close vs wick) — `unresolved`. Inherits swing `strength N`.
- **Eligible roles:** trigger, confirmation, context (structure state), invalidation.
- **Market/data constraints:** OHLC only; timeframe-dependent; close-vs-wick choice materially changes timing.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** https://oyamori.com/learning/smart-money-concepts-glossary/ ; https://thesimpleict.com/order-block-basics-ict-guide/
- **Uncertainty/variants:** SMC/ICT sources differ on whether BOS requires displacement/close beyond the pivot or a mere wick. "BOS" vs "MSS" terminology overlaps across educators.

## change-of-character — Change of Character (CHoCH) / Market Structure Shift (MSS)

- **Family:** Swing points & structural ranges
- **Aliases:** CHoCH, market structure shift, MSS, structure reversal
- **Definition:** Price trading through a prior swing point *against* the prevailing sequence — e.g. a close below the most recent higher low in an uptrend — signaling a potential reversal of structure.
- **Boundaries:** Reversal event vs BOS (continuation event). Not a level; an event that reclassifies structure. Not automatically a trade signal — it only marks a structural state change.
- **Observable inputs:** Confirmed swing highs/lows; current price/close.
- **Recognition semantics:** In an uptrend, a CHoCH occurs when price closes below the last confirmed higher low. In a downtrend, above the last confirmed lower high. Same close-vs-wick ambiguity as BOS.
- **Parameters/profiles:** `break-basis` — `unresolved`. Inherits swing `strength N`.
- **Eligible roles:** trigger, confirmation, context, invalidation.
- **Market/data constraints:** OHLC only; timeframe-dependent.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** https://oyamori.com/learning/smart-money-concepts-glossary/ ; https://thesimpleict.com/order-block-basics-ict-guide/
- **Uncertainty/variants:** "CHoCH" (ICT) and "MSS" (market structure shift) are used near-interchangeably but some educators reserve MSS for a specific displacement-based definition. Reversal vs mere pullback is not decidable from the event alone.

## fractal-pivot — Fractal Pivot

- **Family:** Swing points & structural ranges
- **Aliases:** Bill Williams fractal, up-fractal, down-fractal
- **Definition:** A five-bar pattern where the middle bar's high (up-fractal) or low (down-fractal) is the extreme of the five-bar window — a specific, fixed-strength (N=2) swing point.
- **Boundaries:** A fractal is a *specific parameterization* of a swing point (N=2), not a distinct concept. Not a "fractal" in the mathematical sense. Not a level by itself.
- **Observable inputs:** OHLC bar series.
- **Recognition semantics:** Up-fractal: `high[t] > high[t-2], high[t-1], high[t+1], high[t+2]`. Down-fractal is the mirror on lows. Confirms two bars after the pivot bar.
- **Parameters/profiles:** `strength N` fixed at 2 — `published-convention` (Bill Williams). No other parameters.
- **Eligible roles:** location, trigger, invalidation, context.
- **Market/data constraints:** OHLC only; timeframe-dependent; fixed N=2 makes it noisy on low timeframes.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** ontology-seed — needs source evidence (Bill Williams "Trading Chaos" fractal definition; not yet fetched from a primary source).
- **Uncertainty/variants:** Whether the middle bar must be strictly higher or merely the highest (ties) is unresolved.

## support-level — Support Level

- **Family:** Support/resistance & supply/demand
- **Aliases:** support, floor, demand floor
- **Definition:** A price level or zone where price has historically tended to stop falling and reverse or pause, interpreted as an area of latent buying interest.
- **Boundaries:** "Support" is an *interpretive role* assigned to an observed level, not a raw fact. Not the same as a demand zone (support is usually a line/level from repeated touches; a demand zone is the base of a single impulse). Not a swing low (observed pivot) — though swing lows are the usual raw material.
- **Observable inputs:** Historical price; prior swing lows, prior reaction points, round numbers, or indicator levels.
- **Recognition semantics:** Identify a price where multiple prior declines stalled/reversed. Strength is conventionally read from number of touches, time held, and reaction size — but these are heuristics, not algorithms.
- **Parameters/profiles:** `tolerance` (how wide a band counts as "the level") — `unresolved`. `min-touches` — `unresolved`.
- **Eligible roles:** location, invalidation, trigger (bounce/break), context, exit/target.
- **Market/data constraints:** OHLC only; discretionary; timeframe-dependent.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** https://trendspider.com/learning-center/what-are-support-and-resistance-in-trading/ (referenced from TrendSpider learning center)
- **Uncertainty/variants:** Line vs zone; "more touches = stronger" (classic TA) directly conflicts with supply/demand "more touches = weaker" (see zone-freshness). This contradiction is unresolved and must not be silently merged.

## resistance-level — Resistance Level

- **Family:** Support/resistance & supply/demand
- **Aliases:** resistance, ceiling, supply ceiling
- **Definition:** A price level or zone where price has historically tended to stop rising and reverse or pause, interpreted as an area of latent selling interest.
- **Boundaries:** Interpretive role, not raw fact. Not a supply zone (line vs impulse base). Not a swing high (observed pivot).
- **Observable inputs:** Historical price; prior swing highs, prior reaction points, round numbers, indicator levels.
- **Recognition semantics:** Mirror of support-level: identify a price where multiple prior rallies stalled/reversed.
- **Parameters/profiles:** `tolerance` — `unresolved`; `min-touches` — `unresolved`.
- **Eligible roles:** location, invalidation, trigger, context, exit/target.
- **Market/data constraints:** OHLC only; discretionary; timeframe-dependent.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** https://trendspider.com/learning-center/what-are-support-and-resistance-in-trading/
- **Uncertainty/variants:** Same line-vs-zone and touch-count conflicts as support-level.

## horizontal-level — Horizontal Support/Resistance Level

- **Family:** Support/resistance & supply/demand
- **Aliases:** static level, horizontal S/R, key level, prior high/low
- **Definition:** A fixed horizontal price reference derived from a prior significant high or low (or a cluster of them), used as a candidate support/resistance location.
- **Boundaries:** "Horizontal" distinguishes it from *dynamic* levels (moving averages, VWAP) and *diagonal* levels (trendlines). It is the raw price reference; support/resistance is the interpretive role. Not a zone (a zone has width; a level is a line or thin band).
- **Observable inputs:** Prior swing highs/lows, prior session/day/week/month extremes, round numbers.
- **Recognition semantics:** Project a prior significant extreme forward as a horizontal line. Clustering of multiple prior extremes at nearly the same price strengthens the reference (heuristic).
- **Parameters/profiles:** `cluster-tolerance` — `unresolved`. `source-extreme` (which prior high/low) — `unresolved`.
- **Eligible roles:** location, invalidation, trigger, context.
- **Market/data constraints:** OHLC only; discretionary; timeframe-dependent.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** Whether to use wick extremes or body/close extremes is unresolved.

## supply-zone — Supply Zone

- **Family:** Support/resistance & supply/demand
- **Aliases:** supply area, distribution zone, sell zone
- **Definition:** A price region (a base/consolidation) from which price departed sharply downward, interpreted as an area of unfilled sell orders that may react if price returns.
- **Boundaries:** A zone is an *area with width*, not a line. Distinct from resistance (line from repeated touches). Distinct from an order block (ICT-specific, single-candle, tied to liquidity sweep + BOS). The "unfilled orders" framing is an interpretation, not an observed fact.
- **Observable inputs:** OHLC; the base candles and the departure move. Volume (where available) is a secondary confirmation, not required.
- **Recognition semantics:** Identify a rally-base-drop (or rally-base-rally) structure: price rises into a tight base, then drops away sharply. The zone is the base's range. Strength heuristics: departure speed, base tightness (1–5 candles), freshness.
- **Parameters/profiles:** `base-width` (candles) — `source-stated` 1–5 tight base (snappchart); `unresolved` STRATS default. `departure-strength` — `unresolved`.
- **Eligible roles:** location, trigger, invalidation, context.
- **Market/data constraints:** OHLC only; discretionary; timeframe-dependent. Volume confirmation is venue-dependent (see transfer notes).
- **Transfer notes:** Fully transferable to Forex/crypto spot as a price-structure concept. Volume-based confirmation is NOT transferable to spot FX (no consolidated volume) and is exchange-specific in crypto.
- **Evidence/status:** https://www.snappchart.app/blog/technical-indicators/supply-and-demand-zones ; https://trendspider.com/learning-center/what-are-supply-and-demand-zones ; https://proptradingvibes.com/blog/supply-and-demand-trading
- **Uncertainty/variants:** Zone width and "how sharp is sharp enough" are discretionary. Supply/demand vs order-block boundaries are contested across educators.

## demand-zone — Demand Zone

- **Family:** Support/resistance & supply/demand
- **Aliases:** demand area, accumulation zone, buy zone
- **Definition:** A price region (a base/consolidation) from which price departed sharply upward, interpreted as an area of unfilled buy orders that may react if price returns.
- **Boundaries:** Area, not a line. Distinct from support (line from touches). Distinct from a bullish order block (ICT-specific). "Unfilled orders" is interpretation, not observation.
- **Observable inputs:** OHLC; base candles and departure move; optional volume.
- **Recognition semantics:** Identify a drop-base-rally (or dip-base-rally) structure: price falls into a tight base, then rallies away sharply. The zone is the base's range.
- **Parameters/profiles:** `base-width` — `source-stated` 1–5 tight base; `unresolved` default. `departure-strength` — `unresolved`.
- **Eligible roles:** location, trigger, invalidation, context.
- **Market/data constraints:** OHLC only; discretionary; timeframe-dependent.
- **Transfer notes:** Fully transferable as price structure; volume confirmation not transferable to spot FX.
- **Evidence/status:** https://www.snappchart.app/blog/technical-indicators/supply-and-demand-zones ; https://trendspider.com/learning-center/what-are-supply-and-demand-zones
- **Uncertainty/variants:** Same width/sharpness discretion as supply-zone.

## zone-base — Zone Base

- **Family:** Support/resistance & supply/demand
- **Aliases:** base, consolidation base, origin, launch pad
- **Definition:** The tight consolidation (the "base") immediately preceding a sharp departure move, which defines the width of a supply or demand zone.
- **Boundaries:** The base is the *origin* of a zone, not the zone's reaction area (the zone is the base's price range projected forward). Not a range (a range is a two-sided structure; a base is the one-sided origin of an impulse).
- **Observable inputs:** OHLC; the consolidation candles and the departure.
- **Recognition semantics:** Locate the last tight, low-volatility cluster of candles before a sharp directional move. The base's high/low bound the zone.
- **Parameters/profiles:** `base-width` — `source-stated` 1–5 candles (snappchart); `unresolved` default. `tightness` (range compression) — `unresolved`.
- **Eligible roles:** location (defines zone extent), context.
- **Market/data constraints:** OHLC only; discretionary.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** https://www.snappchart.app/blog/technical-indicators/supply-and-demand-zones
- **Uncertainty/variants:** "Tight" is not quantified in most sources; base vs "just a pause" boundary is discretionary.

## zone-freshness — Zone Freshness (Fresh vs Tested)

- **Family:** Support/resistance & supply/demand
- **Aliases:** fresh zone, untested zone, tested zone, spent zone
- **Definition:** A property of a supply/demand zone describing how many times price has returned to it since formation. A fresh zone has not been revisited; each revisit is assumed to consume some of the resting orders.
- **Boundaries:** This is an *attribute* of a zone, not a level itself. The "orders get consumed" model is an interpretation, not an observed fact. Directly conflicts with classic support/resistance "more touches = stronger".
- **Observable inputs:** The zone; subsequent price revisits.
- **Recognition semantics:** Count price returns into the zone's range after formation. Fresh = zero returns. Tested = one or more. Strength is conventionally read as decreasing with each test.
- **Parameters/profiles:** `test-count` — `unresolved` (no agreed threshold for "spent"). `revisit-depth` (wick vs close into zone) — `unresolved`.
- **Eligible roles:** filter, context, confirmation.
- **Market/data constraints:** OHLC only; discretionary.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** https://www.snappchart.app/blog/technical-indicators/supply-and-demand-zones ; https://proptradingvibes.com/blog/supply-and-demand-trading
- **Uncertainty/variants:** The freshness-vs-touches contradiction with classic S/R is a genuine unresolved taxonomy conflict (see dedup notes).

## polarity-flip — Polarity Flip (Support/Resistance Role Reversal)

- **Family:** Support/resistance & supply/demand
- **Aliases:** role reversal, S/R flip, broken support becomes resistance
- **Definition:** The observation that a level which previously acted as support may act as resistance after being broken (and vice versa).
- **Boundaries:** This is a *role transition* of a level, not a new level. Not the same as a breaker block (an ICT-specific failed order block). The flip is an interpretation, not a guaranteed behavior.
- **Observable inputs:** A broken horizontal level; subsequent price behavior at that level.
- **Recognition semantics:** After price closes through a support level, mark that level as a candidate resistance; observe whether subsequent rallies stall there.
- **Parameters/profiles:** `break-basis` (close vs wick) — `unresolved`. `flip-confirmation` (how many rejections to confirm) — `unresolved`.
- **Eligible roles:** location, context, confirmation.
- **Market/data constraints:** OHLC only; discretionary.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** https://proptradingvibes.com/blog/supply-and-demand-trading (contrasts S/R flip with zone depletion)
- **Uncertainty/variants:** Whether a flip requires a close beyond the level or a mere wick is unresolved; flip reliability is not validated.

## round-number — Round Number / Psychological Level

- **Family:** Support/resistance & supply/demand
- **Aliases:** psychological level, big figure, whole number, handle
- **Definition:** A price level at a "round" value (e.g. 1.1000 in EUR/USD, 50,000 in BTC) that traders treat as a reference, on the assumption that order clustering occurs there.
- **Boundaries:** A round number is a *candidate* reference, not an observed structure. The "order clustering" claim is an assumption, not an observed fact. Not a support/resistance level until price actually reacts there.
- **Observable inputs:** Price; the instrument's tick/quote convention (which determines what "round" means).
- **Recognition semantics:** Identify price levels at round increments of the instrument's natural unit (e.g. 100-pip "big figures" in FX majors, $1,000 or $10,000 steps in crypto). Reaction must be observed, not assumed.
- **Parameters/profiles:** `round-increment` — `unresolved` (instrument-specific). `big-figure` = 100 pips — `published-convention` in FX majors.
- **Eligible roles:** location, context, filter.
- **Market/data constraints:** Instrument-specific; the "round" convention differs between FX (pips/big figures) and crypto (dollar steps). No volume data needed.
- **Transfer notes:** Transferable but the round-increment must be re-derived per instrument/venue.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** No agreed increment; the psychological-order-clustering premise is unvalidated.

## session-high — Session High

- **Family:** Session/day/week/month-derived references
- **Aliases:** session high, intraday high, current session high
- **Definition:** The highest price traded within a defined trading session (e.g. London, New York, Asia, or a full 24h day) up to the current moment.
- **Boundaries:** This is a *price reference* (a level), NOT the session itself. The session (a time window) is a context primitive, not a location. Distinct from a swing high (structure-anchored) — a session high is time-anchored.
- **Observable inputs:** OHLC within the session window; the session definition (start/end times).
- **Recognition semantics:** Track the running maximum of `high` over bars whose timestamp falls inside the session window. Recomputes as the session progresses.
- **Parameters/profiles:** `session-definition` (start/end, timezone) — `unresolved` (venue/strategy-specific). `timezone` — `unresolved`.
- **Eligible roles:** location, trigger (break of session high), invalidation, context.
- **Market/data constraints:** Requires a session/timezone convention. Forex sessions are broker/UTC-convention dependent; crypto "day" is often UTC midnight.
- **Transfer notes:** Transferable, but the session boundary must be re-specified per market (FX sessions vs crypto 24/7 UTC day).
- **Evidence/status:** https://oyamori.com/learning/smart-money-concepts-glossary/ (lists "Session High / Low")
- **Uncertainty/variants:** Session boundaries (which timezone, which named session) are not standardized.

## session-low — Session Low

- **Family:** Session/day/week/month-derived references
- **Aliases:** session low, intraday low, current session low
- **Definition:** The lowest price traded within a defined trading session up to the current moment.
- **Boundaries:** Price reference, not the session itself. Distinct from a swing low (structure-anchored).
- **Observable inputs:** OHLC within the session window; session definition.
- **Recognition semantics:** Running minimum of `low` over bars inside the session window.
- **Parameters/profiles:** `session-definition` — `unresolved`; `timezone` — `unresolved`.
- **Eligible roles:** location, trigger, invalidation, context.
- **Market/data constraints:** Session/timezone convention required.
- **Transfer notes:** Transferable with re-specified session boundary.
- **Evidence/status:** https://oyamori.com/learning/smart-money-concepts-glossary/
- **Uncertainty/variants:** Same session-boundary ambiguity as session-high.

## session-range — Session Range

- **Family:** Session/day/week/month-derived references
- **Aliases:** session range, intraday range, day range
- **Definition:** The price span between the session high and session low (a derived width, not a single level).
- **Boundaries:** A range *measurement*, not a level. Distinct from a structural range (a two-sided consolidation structure). The session high/low are the levels; the range is their difference.
- **Observable inputs:** Session high and session low.
- **Recognition semantics:** `session-high − session-low`. Used to normalize other references (e.g. "price is at 60% of the session range").
- **Parameters/profiles:** none beyond session definition — `unresolved`.
- **Eligible roles:** context, filter, normalization basis.
- **Market/data constraints:** Session/timezone convention required.
- **Transfer notes:** Transferable with re-specified session boundary.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** None material beyond session-boundary ambiguity.

## previous-day-high — Previous Day High (PDH)

- **Family:** Session/day/week/month-derived references
- **Aliases:** PDH, prior day high, yesterday's high
- **Definition:** The highest price traded during the previous completed trading day.
- **Boundaries:** A fixed historical price reference (a level), not a session context. Distinct from current session high (which is still forming). Distinct from a swing high.
- **Observable inputs:** Prior day's OHLC; the day-boundary convention.
- **Recognition semantics:** Take the maximum `high` of all bars in the previous day's window. Fixed once the day closes.
- **Parameters/profiles:** `day-boundary` (UTC vs local vs exchange) — `unresolved`.
- **Eligible roles:** location, trigger (break of PDH), invalidation, context.
- **Market/data constraints:** Day-boundary convention required; differs between FX (broker server time) and crypto (UTC midnight).
- **Transfer notes:** Transferable; re-specify day boundary per market.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** Day-boundary (which timezone) is not standardized.

## previous-day-low — Previous Day Low (PDL)

- **Family:** Session/day/week/month-derived references
- **Aliases:** PDL, prior day low, yesterday's low
- **Definition:** The lowest price traded during the previous completed trading day.
- **Boundaries:** Fixed historical price reference, not a session context. Distinct from current session low and from a swing low.
- **Observable inputs:** Prior day's OHLC; day-boundary convention.
- **Recognition semantics:** Minimum `low` of all bars in the previous day's window.
- **Parameters/profiles:** `day-boundary` — `unresolved`.
- **Eligible roles:** location, trigger, invalidation, context.
- **Market/data constraints:** Day-boundary convention required.
- **Transfer notes:** Transferable; re-specify day boundary.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** Day-boundary ambiguity.

## previous-week-extreme — Previous Week High/Low (PWH/PWL)

- **Family:** Session/day/week/month-derived references
- **Aliases:** PWH, PWL, prior week high/low, last week's high/low
- **Definition:** The highest (PWH) and lowest (PWL) price traded during the previous completed trading week.
- **Boundaries:** Fixed historical price references, not a session context. Distinct from current week extremes (still forming) and from swing points.
- **Observable inputs:** Prior week's OHLC; week-boundary convention.
- **Recognition semantics:** Max/min of `high`/`low` over the previous week's bars. Fixed once the week closes.
- **Parameters/profiles:** `week-boundary` (e.g. Sunday open vs Monday open) — `unresolved`.
- **Eligible roles:** location, trigger, invalidation, context.
- **Market/data constraints:** Week-boundary convention required; differs across FX (5-day) and crypto (7-day).
- **Transfer notes:** Transferable; re-specify week boundary.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** Week start/end convention is not standardized.

## previous-month-extreme — Previous Month High/Low (PMH/PML)

- **Family:** Session/day/week/month-derived references
- **Aliases:** PMH, PML, prior month high/low, last month's high/low
- **Definition:** The highest (PMH) and lowest (PML) price traded during the previous completed calendar month.
- **Boundaries:** Fixed historical price references, not a session context. Distinct from current month extremes and swing points.
- **Observable inputs:** Prior month's OHLC; calendar-month convention.
- **Recognition semantics:** Max/min of `high`/`low` over the previous calendar month's bars.
- **Parameters/profiles:** `month-boundary` (calendar vs trading month) — `unresolved`.
- **Eligible roles:** location, trigger, invalidation, context.
- **Market/data constraints:** Calendar-month convention; crypto has no "trading month" distinction.
- **Transfer notes:** Transferable; calendar month is the natural convention in both markets.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** Calendar vs trading-month boundary.

## opening-range — Opening Range

- **Family:** Session/day/week/month-derived references
- **Aliases:** OR, opening range, initial balance, IB
- **Definition:** The high-low span of the first fixed period of a session (e.g. first 15/30/60 minutes), used as a reference range for the rest of the session.
- **Boundaries:** A *range* (two levels: OR high and OR low), not a single level. Distinct from the session range (full session) and from a structural range. The OR high/low are the levels; the OR itself is the span.
- **Observable inputs:** OHLC of the first N minutes of the session; session open time.
- **Recognition semantics:** Record the max high and min low of bars within the first N minutes after session open. Fixed once the window closes.
- **Parameters/profiles:** `or-length` — `published-convention` 15/30/60 min common; `unresolved` STRATS default. `session-open` — `unresolved`.
- **Eligible roles:** location (OR high/low), trigger (OR breakout), context.
- **Market/data constraints:** Requires a session-open convention; futures/equity-derived (RTH open) — transfer to FX/crypto requires choosing an open time.
- **Transfer notes:** Originates in futures/equity (regular trading hours). For FX/crypto spot there is no single "open"; the OR must be anchored to a chosen session start (e.g. London open, UTC midnight). Transfer status: assumed transferable with re-anchoring.
- **Evidence/status:** ontology-seed — needs source evidence (opening-range breakout is widely documented but no primary URL fetched this pass).
- **Uncertainty/variants:** OR length and anchor time are not standardized; "initial balance" (market profile) overlaps but is time/TPO-based.

## daily-open — Daily Open / Opening Price

- **Family:** Session/day/week/month-derived references
- **Aliases:** day open, daily open, opening price, midnight open (crypto)
- **Definition:** The first traded price of a trading day (or the price at the day-boundary rollover).
- **Boundaries:** A single price reference, not a session context. Distinct from the opening range (a span). In crypto, "midnight open" (UTC) is the common anchor.
- **Observable inputs:** First bar's open of the day; day-boundary convention.
- **Recognition semantics:** Record the open of the first bar after the day boundary. Fixed once the day starts.
- **Parameters/profiles:** `day-boundary` — `unresolved`.
- **Eligible roles:** location, context, normalization basis (e.g. distance from open).
- **Market/data constraints:** Day-boundary convention required; FX broker server time vs crypto UTC midnight differ.
- **Transfer notes:** Transferable; re-specify day boundary.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** Day-boundary ambiguity; "open" is ill-defined in 24/7 crypto without a chosen rollover.

## liquidity-pool — Liquidity Pool / Liquidity Level

- **Family:** Liquidity, gaps, imbalances, blocks (SMC/ICT)
- **Aliases:** liquidity, pool, resting liquidity, stop cluster
- **Definition:** A price area where a concentration of resting orders (notably stop-losses and breakout orders) is assumed to sit, typically just beyond a visible swing high/low or equal highs/lows.
- **Boundaries:** The "resting orders" premise is an *assumption about unobservable order flow*, not an observed fact in spot markets. Not a level that has reacted yet — it is a *candidate magnet*. Distinct from an actual support/resistance level.
- **Observable inputs:** Swing highs/lows, equal highs/lows, prior session extremes (the visible structures that imply where stops cluster).
- **Recognition semantics:** Mark zones just beyond obvious swing highs (buy-side) and swing lows (sell-side) where breakout/stop orders are assumed to rest. No direct observation of the orders is possible in spot FX/crypto.
- **Parameters/profiles:** `buffer` beyond the extreme — `unresolved`. `source-structure` (which swing) — `unresolved`.
- **Eligible roles:** context, filter, location (as a target/magnet), trigger (sweep).
- **Market/data constraints:** In spot FX there is no consolidated order book, so "liquidity" is inferred from price structure, not measured. In crypto, exchange order books exist but are venue-fragmented and not visible in OHLC alone.
- **Transfer notes:** The concept transfers as a *price-structure heuristic*, but the "liquidity" claim is weaker in spot FX (no central book) than in centralized futures/equity.
- **Evidence/status:** https://oyamori.com/learning/smart-money-concepts-glossary/ ; https://www.luxalgo.com/blog/ict-trader-concepts-order-blocks-unpacked/
- **Uncertainty/variants:** "Liquidity" is used loosely across SMC/ICT; whether it means stops, breakout orders, or both is unresolved.

## directional-liquidity — Buy-Side / Sell-Side Liquidity (BSL/SSL)

- **Family:** Liquidity, gaps, imbalances, blocks (SMC/ICT)
- **Aliases:** BSL, SSL, buyside liquidity, sellside liquidity, external range liquidity
- **Definition:** Buy-side liquidity (BSL) = assumed resting buy orders above a high (stops on shorts + breakout buys); sell-side liquidity (SSL) = assumed resting sell orders below a low (stops on longs + breakout sells).
- **Boundaries:** Two polarities of the same liquidity-pool concept. Not observed order flow — inferred from structure. Not a level that has reacted.
- **Observable inputs:** Swing highs (for BSL) and swing lows (for SSL); equal highs/lows.
- **Recognition semantics:** BSL sits above visible highs; SSL sits below visible lows. "External range liquidity" = beyond the range extremes; "internal range liquidity" = inside the range (ICT distinction).
- **Parameters/profiles:** `buffer` — `unresolved`. `internal/external` classification — `published-convention` (ICT).
- **Eligible roles:** context, filter, location (target), trigger (sweep).
- **Market/data constraints:** Same spot-FX inference limitation as liquidity-pool.
- **Transfer notes:** Transfers as a structure heuristic; "liquidity" claim weaker in spot FX.
- **Evidence/status:** https://www.luxalgo.com/blog/ict-trader-concepts-order-blocks-unpacked/ ; https://oyamori.com/learning/smart-money-concepts-glossary/
- **Uncertainty/variants:** Internal vs external range liquidity boundary is ICT-specific and not universally defined.

## equal-highs-lows — Equal Highs / Equal Lows (EQH/EQL)

- **Family:** Liquidity, gaps, imbalances, blocks (SMC/ICT)
- **Aliases:** EQH, EQL, equal highs, equal lows, double top/bottom (loose)
- **Definition:** Two or more swing highs (or lows) at approximately the same price, read as a sign of clustered resting orders just beyond that level.
- **Boundaries:** An *observed price pattern* (near-equal extremes), distinct from the *interpretation* (liquidity cluster). Not the same as a classic double top/bottom (a reversal pattern) — EQH/EQL is a liquidity reading, not a reversal signal.
- **Observable inputs:** Swing highs/lows; a tolerance for "equal".
- **Recognition semantics:** Detect two+ swing highs within a tolerance band. The tighter the equality, the stronger the assumed cluster (heuristic).
- **Parameters/profiles:** `equality-tolerance` — `unresolved`. `min-count` (usually 2) — `published-convention`.
- **Eligible roles:** context, filter, location (target), trigger (sweep of EQH/EQL).
- **Market/data constraints:** OHLC only; discretionary tolerance.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** https://oyamori.com/learning/smart-money-concepts-glossary/ (lists "Equal Highs / Lows")
- **Uncertainty/variants:** Tolerance for "equal" is not standardized; EQH/EQL vs double top/bottom boundary is contested.

## liquidity-sweep — Liquidity Sweep / Stop Hunt

- **Family:** Liquidity, gaps, imbalances, blocks (SMC/ICT)
- **Aliases:** sweep, stop hunt, stop grab, liquidity grab, inducement
- **Definition:** A brief move through a liquidity level (e.g. a swing high/low or equal highs/lows) that then reverses, interpreted as price "taking out" the resting orders before reversing.
- **Boundaries:** An *event* (a move + reversal), not a level. The "stop hunt" framing is an interpretation of intent, not an observed fact. Distinct from a genuine breakout (which holds beyond the level).
- **Observable inputs:** A liquidity level; the price move through it; the subsequent reversal.
- **Recognition semantics:** Price trades through a marked liquidity level, then closes back on the other side (rejection). The reversal distinguishes a sweep from a breakout.
- **Parameters/profiles:** `rejection-basis` (close back vs wick) — `unresolved`. `sweep-depth` — `unresolved`.
- **Eligible roles:** trigger, confirmation, context.
- **Market/data constraints:** OHLC only; the "intent" reading is unverifiable in spot markets.
- **Transfer notes:** Transfers as a price-action pattern; the "smart money intent" narrative is not transferable as fact.
- **Evidence/status:** https://www.luxalgo.com/blog/ict-trader-concepts-order-blocks-unpacked/ ; https://oyamori.com/learning/smart-money-concepts-glossary/
- **Uncertainty/variants:** Sweep vs breakout is only decidable in hindsight; "inducement" (ICT) is a related but distinct concept.

## fair-value-gap — Fair Value Gap (FVG) / Imbalance (SMC)

- **Family:** Liquidity, gaps, imbalances, blocks (SMC/ICT)
- **Aliases:** FVG, imbalance (SMC), inefficiency, price imbalance, three-candle gap
- **Definition:** A three-candle pattern where the first and third candles' wicks do not overlap, leaving a price band that was "skipped" by a fast move — interpreted as an area price may return to "fill".
- **Boundaries:** A *price band* (a zone), not a single level. Distinct from a classic price gap (a session-to-session discontinuity). Distinct from an order-flow imbalance (bid/ask volume lopsidedness — see imbalance entry). The "fill" tendency is a claim, not a validated rule.
- **Observable inputs:** Three consecutive candles' highs/lows.
- **Recognition semantics:** Bullish FVG: `low[candle3] > high[candle1]`; the gap is between `high[candle1]` and `low[candle3]`. Bearish FVG: `high[candle3] < low[candle1]`; gap between `low[candle1]` and `high[candle3]`. The middle candle is the displacement.
- **Parameters/profiles:** `fill-fraction` (50% "consequent encroachment" vs 100%) — `published-convention` (SMC); `unresolved` STRATS default. `mitigation` (partially filled = mitigated) — `published-convention`.
- **Eligible roles:** location, trigger, context, target.
- **Market/data constraints:** OHLC only; no volume needed. Timeframe-dependent.
- **Transfer notes:** Fully transferable to Forex/crypto spot (pure OHLC).
- **Evidence/status:** https://investisseur2-0.com/en/resources/fair-value-gap-fvg.html ; https://cryptorookie101.com/fair-value-gaps-crypto ; https://quantum-algo.com/blog/fair-value-gaps-trading-guide
- **Uncertainty/variants:** "Fill rate" claims (e.g. 70–75%) are source-stated, not validated. FVG vs liquidity-void vs imbalance terminology overlaps heavily across educators.

## order-block — Order Block (OB)

- **Family:** Liquidity, gaps, imbalances, blocks (SMC/ICT)
- **Aliases:** OB, bullish OB, bearish OB, institutional order block, demand/supply OB
- **Definition:** The last counter-trend candle (or small cluster) before a sharp displacement move, interpreted as the origin of institutional orders that may react if price returns.
- **Boundaries:** An ICT-specific, stricter variant of a supply/demand zone (single candle, tied to liquidity sweep + BOS/CHoCH). The "institutional orders" framing is interpretation, not observation. Not a breaker block (a failed OB).
- **Observable inputs:** OHLC; the counter-trend candle; the displacement; surrounding structure (sweep, BOS/CHoCH).
- **Recognition semantics:** Bullish OB = last down-candle before a strong up-move; bearish OB = last up-candle before a strong down-move. ICT validity criteria (displacement, BOS/CHoCH, liquidity taken, FVG left) are stricter than the naive "last candle" reading.
- **Parameters/profiles:** `validity-criteria` (displacement/BOS/sweep/FVG) — `published-convention` (ICT); `unresolved` STRATS default. `zone-extent` (body vs wick) — `unresolved`.
- **Eligible roles:** location, trigger, context.
- **Market/data constraints:** OHLC only; discretionary; the "institutional" narrative is unverifiable in spot markets.
- **Transfer notes:** Transfers as a price-structure pattern; the institutional-order-flow narrative is not transferable as fact.
- **Evidence/status:** https://thesimpleict.com/order-block-basics-ict-guide/ ; https://atas.net/blog/what-are-ict-order-blocks-and-breaker-blocks-in-trading/ ; https://oyamori.com/learning/smart-money-concepts-glossary/
- **Uncertainty/variants:** OB vs supply/demand zone boundary is contested; ICT's own definition has evolved (multiple "models"). Validity criteria vary by educator.

## breaker-block — Breaker Block

- **Family:** Liquidity, gaps, imbalances, blocks (SMC/ICT)
- **Aliases:** breaker, failed order block
- **Definition:** A former order block that price broke through (failed to hold), now treated as a level for the opposite direction (a broken bullish OB becomes resistance, etc.).
- **Boundaries:** A *state transition* of an order block, not a new structure. Distinct from polarity-flip (a general S/R concept) — breaker is ICT-specific and OB-anchored.
- **Observable inputs:** A prior order block; price breaking through it.
- **Recognition semantics:** When price trades through a bullish OB without reversing, reclassify it as a bearish breaker (resistance) and vice versa.
- **Parameters/profiles:** `break-basis` — `unresolved`. Inherits OB validity criteria.
- **Eligible roles:** location, trigger, context.
- **Market/data constraints:** OHLC only; discretionary.
- **Transfer notes:** Transfers as a price-structure pattern.
- **Evidence/status:** https://atas.net/blog/what-are-ict-order-blocks-and-breaker-blocks-in-trading/ ; https://oyamori.com/learning/smart-money-concepts-glossary/
- **Uncertainty/variants:** Breaker vs mitigation block vs rejection block boundaries are not consistently defined across educators.

## mitigation-block — Mitigation Block

- **Family:** Liquidity, gaps, imbalances, blocks (SMC/ICT)
- **Aliases:** mitigation, MB
- **Definition:** A zone where price is expected to return to "mitigate" (partially fill) unfilled orders left by a fast move — a looser, return-to-zone variant of the order-block idea.
- **Boundaries:** Overlaps heavily with order block and FVG; some educators treat it as the zone price returns to, others as a distinct block type. Not a breaker block.
- **Observable inputs:** OHLC; the fast move and the zone it left.
- **Recognition semantics:** Mark the zone left behind by a displacement move as a candidate return/mitigation area.
- **Parameters/profiles:** `zone-extent` — `unresolved`. `mitigation-fraction` — `unresolved`.
- **Eligible roles:** location, trigger, context.
- **Market/data constraints:** OHLC only; discretionary.
- **Transfer notes:** Transfers as a price-structure pattern.
- **Evidence/status:** https://oyamori.com/learning/smart-money-concepts-glossary/ ; https://tradingfinder.com/education/forex/ict-order-blocks/
- **Uncertainty/variants:** Mitigation block vs order block vs FVG is a major unresolved terminology overlap.

## rejection-block — Rejection Block

- **Family:** Liquidity, gaps, imbalances, blocks (SMC/ICT)
- **Aliases:** rejection, wick block
- **Definition:** A zone marked by the wick (not the body) of a strong rejection candle — a tighter, wick-based variant of an order block.
- **Boundaries:** Wick-anchored vs body-anchored (order block). Not a breaker block. The "rejection" reading is interpretation.
- **Observable inputs:** OHLC; a strong rejection candle's wick.
- **Recognition semantics:** Mark the wick extent of a candle that strongly rejected a level as the zone.
- **Parameters/profiles:** `wick-extent` — `unresolved`. `rejection-strength` — `unresolved`.
- **Eligible roles:** location, trigger, context.
- **Market/data constraints:** OHLC only; discretionary.
- **Transfer notes:** Transfers as a price-structure pattern.
- **Evidence/status:** https://oyamori.com/learning/smart-money-concepts-glossary/
- **Uncertainty/variants:** Rejection block vs order block (wick vs body) boundary is educator-specific.

## price-gap — Price Gap (Classic)

- **Family:** Liquidity, gaps, imbalances, blocks (SMC/ICT)
- **Aliases:** gap, common gap, breakaway gap, runaway gap, exhaustion gap, weekend gap
- **Definition:** A discontinuity where price opens away from the prior close with no trading in between — a blank region on the chart.
- **Boundaries:** A *session-to-session* discontinuity, distinct from an FVG (an intra-session three-candle skip). The four classic types (common/breakaway/runaway/exhaustion) are *interpretations* of where the gap sits in a trend, not distinct structures.
- **Observable inputs:** Prior close and current open; the gap region.
- **Recognition semantics:** Detect `open[t]` outside the prior bar's range (full gap) or outside the prior close (partial gap). Classify by trend position (range/start/mid/end).
- **Parameters/profiles:** `gap-type` classification — `published-convention` (classic TA). `full vs partial` — `published-convention`.
- **Eligible roles:** location, trigger, context, target (gap fill).
- **Market/data constraints:** In 24/5 Forex, intraday gaps are rare; the main gaps are weekend gaps (Fri close → Sun/Mon open). Crypto trades 24/7, so true gaps are rare and mostly exchange-specific (listing/delisting, halts).
- **Transfer notes:** Originates in equity/futures (daily opens). For Forex, only weekend gaps are common. For crypto spot, gaps are rare and venue-specific. Transfer status: limited.
- **Evidence/status:** https://eliteforextrading.com/price-gaps-explained ; http://investopedia.com/terms/g/gap.asp ; https://strefatradingu.pl/en/blog/types-of-gaps
- **Uncertainty/variants:** "Gaps always fill" is a tendency, not a rule (source-stated, not validated). Gap-type classification is discretionary.

## imbalance — Imbalance (Order-Flow)

- **Family:** Liquidity, gaps, imbalances, blocks (SMC/ICT)
- **Aliases:** order-flow imbalance, bid/ask imbalance, delta imbalance
- **Definition:** A lopsidedness in executed volume between the bid and ask sides at a price level (or within a bar), measured from order-flow/footprint data.
- **Boundaries:** This is the *order-flow* meaning, distinct from the SMC "imbalance" (which is a synonym for FVG). Requires real executed-volume data, not just OHLC. Not inferable from candles alone.
- **Observable inputs:** Footprint/order-flow data: bid vs ask volume per price level (or per bar), often with a ratio threshold.
- **Recognition semantics:** Compare ask-side vs bid-side executed volume; flag levels where one side exceeds the other by a threshold (e.g. 300–400%).
- **Parameters/profiles:** `imbalance-ratio` — `published-convention` 300–400% (traderprofesional); `unresolved` STRATS default.
- **Eligible roles:** confirmation, filter, context.
- **Market/data constraints:** Requires centralized order-flow/footprint data. NOT available in spot FX (no central book; only broker tick volume). In crypto, available per-exchange but venue-fragmented.
- **Transfer notes:** NOT transferable to spot FX. Partially transferable to crypto spot only with a specific exchange's order-flow feed. Must never be silently treated as a spot-FX fact.
- **Evidence/status:** https://traderprofesional.com/en/fair-value-gap-vs-imbalance
- **Uncertainty/variants:** The SMC "imbalance = FVG" usage collides with the order-flow "imbalance = bid/ask lopsidedness" usage; these are different concepts sharing a name.

## liquidity-void — Liquidity Void

- **Family:** Liquidity, gaps, imbalances, blocks (SMC/ICT)
- **Aliases:** void, liquidity gap
- **Definition:** A price band crossed so quickly that little trading occurred there — a single-candle wick-to-wick gap, read as an area price may return to fill.
- **Boundaries:** Overlaps with FVG; some educators distinguish void (single-candle wick gap) from FVG (three-candle gap). Not an order-flow imbalance (no volume data). Not a classic price gap.
- **Observable inputs:** OHLC; a large candle's wick-to-wick span vs neighbors.
- **Recognition semantics:** Identify a band between a candle's wick and the adjacent candle's wick where no overlap occurred.
- **Parameters/profiles:** `void-definition` (single vs three candle) — `unresolved`.
- **Eligible roles:** location, trigger, context, target.
- **Market/data constraints:** OHLC only; discretionary.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** https://oyamori.com/learning/smart-money-concepts-glossary/ (lists "Liquidity Void")
- **Uncertainty/variants:** Void vs FVG boundary is not standardized.

## premium-discount — Premium / Discount (Dealing Range)

- **Family:** Liquidity, gaps, imbalances, blocks (SMC/ICT)
- **Aliases:** premium, discount, equilibrium, dealing range, PD array context
- **Definition:** A location reading of where price sits within a defined range: above the midpoint = premium (expensive), below = discount (cheap), at the midpoint = equilibrium.
- **Boundaries:** A *relative location* within a range, not a level itself. The range (dealing range) is the anchor. Distinct from overbought/oversold (oscillator-based). The "premium = sell, discount = buy" framing is a strategy convention, not a fact.
- **Observable inputs:** A defined range (e.g. a swing high-to-low range); current price; the midpoint.
- **Recognition semantics:** Compute the range midpoint (often 50% of the range, or an OTE/equilibrium level); classify price as premium (above), discount (below), or equilibrium (at).
- **Parameters/profiles:** `range-anchor` (which swing-to-swing) — `unresolved`. `equilibrium-level` (50% vs OTE 62–79%) — `published-convention` (ICT OTE); `unresolved` default.
- **Eligible roles:** context, filter, location.
- **Market/data constraints:** OHLC only; depends on the chosen range anchor.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** https://thesimpleict.com/order-block-basics-ict-guide/ ; https://oyamori.com/learning/smart-money-concepts-glossary/
- **Uncertainty/variants:** Equilibrium definition (50% vs OTE) varies; the dealing-range anchor is discretionary.

## moving-average — Moving Average (SMA/EMA)

- **Family:** Dynamic/statistical references
- **Aliases:** MA, SMA, EMA, WMA, simple moving average, exponential moving average
- **Definition:** A rolling average of price over N periods, plotted as a dynamic line that trails price. SMA weights all periods equally; EMA weights recent periods more.
- **Boundaries:** A *derived indicator*, not a raw price fact. A dynamic level (moves with price), distinct from horizontal levels. Not a VWAP (which weights by volume).
- **Observable inputs:** OHLC (usually close); period N.
- **Recognition semantics:** SMA = mean of last N closes; EMA = recursive smoothing with factor `2/(N+1)`. The line is the reference; price above/below is the location reading.
- **Parameters/profiles:** `period N` — `published-convention` 20/50/200 common; `unresolved` STRATS default. `price-source` (close vs HLC3) — `published-convention` close. `type` (SMA/EMA/WMA) — `published-convention`.
- **Eligible roles:** location (dynamic S/R), context (trend filter), trigger (cross), confirmation.
- **Market/data constraints:** OHLC only; lag increases with N; timeframe-dependent.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** ontology-seed — needs source evidence (foundational; no dedicated primary URL fetched this pass).
- **Uncertainty/variants:** SMA vs EMA vs WMA choice is discretionary; "which MA matters" is strategy-specific, not intrinsic.

## vwap — Volume-Weighted Average Price (VWAP)

- **Family:** Dynamic/statistical references
- **Aliases:** VWAP, volume-weighted average price, session VWAP
- **Definition:** The cumulative average price weighted by volume over a session, resetting each session. `VWAP = Σ(typical price × volume) / Σ(volume)`.
- **Boundaries:** A *volume-weighted* dynamic level, distinct from a simple moving average (no volume) and from a horizontal level. Intraday-only by construction (resets daily). Not defined for daily/weekly periods.
- **Observable inputs:** Intraday OHLCV (typical price = (H+L+C)/3) and volume.
- **Recognition semantics:** Accumulate `typical price × volume` and `volume` from session open; the running ratio is VWAP. Price above/below VWAP is the location reading.
- **Parameters/profiles:** `session-anchor` (open time) — `unresolved`. `typical-price` = (H+L+C)/3 — `published-convention`. `period` = intraday only — `published-convention`.
- **Eligible roles:** location (dynamic S/R), context (bias), trigger (cross), confirmation.
- **Market/data constraints:** Requires volume. In spot FX there is no consolidated volume — VWAP is broker/venue-specific (tick volume proxy). In crypto, VWAP is exchange-specific. Originates in equities/futures (centralized volume).
- **Transfer notes:** NOT cleanly transferable to spot FX (no central volume; only broker tick-volume proxies). Partially transferable to crypto spot per-exchange. Must be labeled venue-specific.
- **Evidence/status:** https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/volume-weighted-average-price-vwap ; https://www.investopedia.com/terms/v/vwap.asp
- **Uncertainty/variants:** Tick-volume VWAP (FX) vs true-volume VWAP (centralized) are different quantities; the FX proxy is not equivalent.

## bollinger-bands — Bollinger Bands

- **Family:** Dynamic/statistical references
- **Aliases:** Bollinger Bands®, BB, volatility bands
- **Definition:** A volatility envelope: a middle N-period moving average with upper/lower bands at K standard deviations above/below it.
- **Boundaries:** A *derived envelope* (three dynamic lines), not a raw price fact. Distinct from Keltner (ATR-based) and Donchian (price-extreme-based) channels. The bands are relative high/low references, not absolute levels.
- **Observable inputs:** OHLC (close); period N; multiplier K.
- **Recognition semantics:** Middle = SMA(N); upper = SMA + K·σ(N); lower = SMA − K·σ(N). Band width reflects volatility.
- **Parameters/profiles:** `period N` = 20 — `published-convention`. `multiplier K` = 2 — `published-convention`. `σ` uses population divisor n — `published-convention` (Wikipedia).
- **Eligible roles:** location (band touches), context (volatility regime), trigger (band break), confirmation.
- **Market/data constraints:** OHLC only; no volume needed; timeframe-dependent.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** https://en.wikipedia.org/wiki/Bollinger_Bands ; https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/bollinger-bands ; https://www.investopedia.com/terms/b/bollingerbands.asp
- **Uncertainty/variants:** N and K are discretionary; "Bollinger Bands" is a registered trademark (name, not concept).

## keltner-channel — Keltner Channel

- **Family:** Dynamic/statistical references
- **Aliases:** Keltner channel, KC
- **Definition:** A volatility envelope: a middle EMA with upper/lower bands at a multiple of ATR above/below it.
- **Boundaries:** ATR-based envelope, distinct from Bollinger (σ-based) and Donchian (price-extreme-based). Not a raw price fact.
- **Observable inputs:** OHLC; EMA period; ATR period; multiplier.
- **Recognition semantics:** Middle = EMA(N); upper = EMA + M·ATR; lower = EMA − M·ATR.
- **Parameters/profiles:** `EMA period` = 20 — `published-convention`. `ATR period` = 10 (Raschke variant) — `published-convention`. `multiplier M` = 2 — `published-convention`.
- **Eligible roles:** location, context, trigger, confirmation.
- **Market/data constraints:** OHLC only; timeframe-dependent.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** https://www.investopedia.com/terms/k/keltnerchannel.asp ; https://www.investopedia.com/articles/forex/06/bandschannels.asp
- **Uncertainty/variants:** Original Keltner (1960) vs Raschke ATR variant differ; parameters are discretionary.

## donchian-channel — Donchian Channel

- **Family:** Dynamic/statistical references
- **Aliases:** Donchian channel, price channel, N-period high/low channel
- **Definition:** A channel of the highest high and lowest low over the last N periods, with an optional midline at their average.
- **Boundaries:** Price-extreme-based channel, distinct from Bollinger (σ) and Keltner (ATR). The bands are step-like (flat until a new extreme), not smooth. Not a raw price fact.
- **Observable inputs:** OHLC; period N.
- **Recognition semantics:** Upper = highest high of last N bars; lower = lowest low of last N bars; mid = (upper+lower)/2.
- **Parameters/profiles:** `period N` = 20 — `published-convention`. `midline` optional — `published-convention`.
- **Eligible roles:** location, trigger (breakout), context, invalidation.
- **Market/data constraints:** OHLC only; timeframe-dependent.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** https://en.wikipedia.org/wiki/Donchian_channel ; https://www.investopedia.com/donchian-channels-formula-8415235
- **Uncertainty/variants:** N is discretionary; "turtle" systems use specific N (e.g. 20/55) — source-stated, not universal.

## moving-average-envelope — Moving Average Envelope

- **Family:** Dynamic/statistical references
- **Aliases:** MA envelope, percentage envelope, envelope
- **Definition:** A moving average with fixed-percentage bands above and below it.
- **Boundaries:** Percentage-based envelope, distinct from Bollinger (σ), Keltner (ATR), and Donchian (extremes). Not a raw price fact.
- **Observable inputs:** OHLC; MA period; percentage offset.
- **Recognition semantics:** Upper = MA × (1 + p%); lower = MA × (1 − p%).
- **Parameters/profiles:** `MA period` — `unresolved`. `percentage p` — `unresolved` (no single convention).
- **Eligible roles:** location, context, trigger.
- **Market/data constraints:** OHLC only; timeframe-dependent.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** https://www.investopedia.com/articles/forex/06/bandschannels.asp (mentions MA envelopes)
- **Uncertainty/variants:** Percentage offset has no standard default.

## atr — Average True Range (ATR)

- **Family:** Dynamic/statistical references
- **Aliases:** ATR, average true range, true range
- **Definition:** A volatility measure: the N-period smoothed average of the true range (max of high−low, |high−prev close|, |low−prev close|).
- **Boundaries:** A *volatility measure*, not a price level or direction indicator. It is the *input* to ATR bands/STARC and Keltner channels, not a location by itself. Not a trend indicator.
- **Observable inputs:** OHLC; period N.
- **Recognition semantics:** TR = max(H−L, |H−C_prev|, |L−C_prev|); ATR = Wilder-smoothed mean of TR over N.
- **Parameters/profiles:** `period N` = 14 — `source-stated` (Wilder). `smoothing` = Wilder SMMA — `source-stated`.
- **Eligible roles:** context (volatility), filter, normalization basis (stop distance), parameter input.
- **Market/data constraints:** OHLC only; timeframe-dependent; ATR is in price units (instrument-specific).
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** https://en.wikipedia.org/wiki/Average_true_range ; https://www.investopedia.com/terms/a/atr.asp
- **Uncertainty/variants:** Wilder SMMA vs simple mean of TR differ; N is discretionary. ATR bands/STARC are a derived location use (see uncertainty).

## pivot-point — Classic Pivot Point (Floor Trader)

- **Family:** Dynamic/statistical references
- **Aliases:** pivot, PP, floor pivot, classic pivot, daily pivot
- **Definition:** A set of support/resistance levels derived from the prior period's high, low, and close: `PP = (H+L+C)/3`, with R1/S1, R2/S2, R3/S3 derived from PP and the range.
- **Boundaries:** A *derived* set of levels, not observed structure. Distinct from a swing pivot (an observed turning point) — same word, different concept. Distinct from Camarilla/Fibonacci/Woodie pivot variants.
- **Observable inputs:** Prior period's H, L, C; the period (day/week/month).
- **Recognition semantics:** Compute PP and the R/S ladder from the prior period's H/L/C. Levels are fixed for the current period.
- **Parameters/profiles:** `formula` = (H+L+C)/3 — `published-convention`. `levels` R1–R3/S1–S3 — `published-convention`. `period` (daily/weekly/monthly) — `published-convention`.
- **Eligible roles:** location, trigger, context.
- **Market/data constraints:** OHLC only; requires a period-boundary convention (day/week/month).
- **Transfer notes:** Fully transferable to Forex/crypto spot (re-anchor the period boundary).
- **Evidence/status:** https://www.tradealgo.com/trading-guides/technical-analysis/pivot-points-how-floor-traders-calculate-daily-support-and-resistance-levels ; https://coinswitch.co/switch/personal-finance/pivot-points
- **Uncertainty/variants:** Multiple named variants (classic, Fibonacci, Woodie, Camarilla, DeMark) with different formulas; "pivot point" is ambiguous without the variant.

## camarilla-pivot — Camarilla Pivot

- **Family:** Dynamic/statistical references
- **Aliases:** Camarilla, Camarilla levels, H1–H4/L1–L4
- **Definition:** A set of eight intraday levels (four resistance H1–H4, four support L1–L4) derived from the prior period's close plus a multiplier of the range, producing tighter bands around the close than classic pivots.
- **Boundaries:** A *variant* of pivot points, not a distinct concept family. Distinct from classic pivots (which anchor on the H/L/C average). Not observed structure.
- **Observable inputs:** Prior period's H, L, C.
- **Recognition semantics:** R1 = C + (H−L)×1.1/12; R2 = C + (H−L)×1.1/6; R3 = C + (H−L)×1.1/4; R4 = C + (H−L)×1.1/2; S1–S4 mirror below C.
- **Parameters/profiles:** `multiplier` 1.1/12, 1.1/6, 1.1/4, 1.1/2 — `published-convention`. `anchor` = prior close — `published-convention`.
- **Eligible roles:** location, trigger, context.
- **Market/data constraints:** OHLC only; intraday-oriented; period-boundary convention required.
- **Transfer notes:** Fully transferable to Forex/crypto spot (re-anchor period boundary).
- **Evidence/status:** https://www.litefinance.org/blog/for-beginners/trading-strategies/camarilla-pivot-points-strategy ; https://purepowerpicks.com/camarilla-support-and-resistance
- **Uncertainty/variants:** Some sources use different multipliers (e.g. 1.0833/1.1666/1.25/1.5); attribution (Nick Stott, 1989) is source-stated.

## fibonacci-retracement — Fibonacci Retracement

- **Family:** Dynamic/statistical references
- **Aliases:** Fib, Fibonacci levels, retracement levels, golden pocket
- **Definition:** Horizontal levels at Fibonacci ratios (23.6%, 38.2%, 50%, 61.8%, 78.6%) of a prior swing's range, drawn from a swing low to a swing high (or reverse), used as candidate pullback support/resistance.
- **Boundaries:** A *derived* set of levels anchored to two swing points, not observed structure. Distinct from Fibonacci *extensions* (projection beyond the swing, for targets). The 50% level is not a Fibonacci ratio but is conventionally included.
- **Observable inputs:** A swing high and swing low (the anchor points); the ratio set.
- **Recognition semantics:** Compute `level = swing_high − ratio × (swing_high − swing_low)` for each ratio. Levels are fixed once the anchors are chosen.
- **Parameters/profiles:** `ratios` 23.6/38.2/50/61.8/78.6 — `published-convention`. `anchors` (which swing) — `unresolved`. `golden pocket` = 61.8–65% — `published-convention` (SMC).
- **Eligible roles:** location, trigger, context, target (via extensions).
- **Market/data constraints:** OHLC only; anchor selection is discretionary; timeframe-dependent.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** https://investopedia.com/terms/f/fibonacciretracement.asp ; https://investopedia.com/articles/active-trading/091615/how-set-fibonacci-retracement-levels.asp
- **Uncertainty/variants:** Anchor-point selection is the main discretionary element; extension levels (127.2%, 161.8%, etc.) are a related but distinct tool folded here for now.

## trendline — Trendline

- **Family:** Dynamic/statistical references
- **Aliases:** trend line, diagonal support/resistance, channel line (parallel)
- **Definition:** A straight line connecting two or more swing lows (uptrend) or swing highs (downtrend), projected forward as a diagonal reference.
- **Boundaries:** A *diagonal* level, distinct from horizontal levels and from dynamic indicators (it is user-drawn, not formula-derived). Not observed structure — it is a construction over observed pivots. A parallel channel line (offset copy) is a related construction.
- **Observable inputs:** Two or more swing points; the line's slope.
- **Recognition semantics:** Connect two+ swing lows (support trendline) or highs (resistance trendline); extend forward. Validity is conventionally read from the number of touches.
- **Parameters/profiles:** `min-touches` (usually 2 to draw, 3 to "confirm") — `published-convention`. `touch-tolerance` — `unresolved`. `log vs linear scale` — `unresolved`.
- **Eligible roles:** location, trigger (break), context, invalidation.
- **Market/data constraints:** OHLC only; discretionary; scale-dependent (log vs linear changes the line).
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** Which pivots to connect is discretionary; "valid" trendline (touch count) is a heuristic, not a rule.

## pattern-boundary — Chart Pattern Boundary

- **Family:** Chart-pattern boundaries & event anchors
- **Aliases:** neckline, pattern boundary, triangle/wedge/flag boundary, breakout level
- **Definition:** The defining boundary line(s) of a recognized chart pattern (e.g. the neckline of a head-and-shoulders, the converging lines of a triangle/wedge, the parallel lines of a flag), whose break is the pattern's trigger.
- **Boundaries:** The boundary is a *construction over a pattern*, not the pattern itself. Distinct from a trendline (a boundary is pattern-specific). The pattern (head-and-shoulders, triangle, etc.) is a separate primitive family; this entry covers only the boundary-as-level.
- **Observable inputs:** The pattern's defining pivots; the boundary line(s).
- **Recognition semantics:** Draw the pattern's boundary from its defining pivots (e.g. neckline through the two troughs of a H&S). The boundary is the level; the break of it is the event.
- **Parameters/profiles:** `pattern-type` — `unresolved` (pattern-specific). `break-basis` (close vs wick) — `unresolved`.
- **Eligible roles:** location, trigger (breakout), invalidation, context.
- **Market/data constraints:** OHLC only; discretionary; pattern recognition itself is subjective.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** ontology-seed — needs source evidence (chart-pattern boundaries are standard TA; no primary URL fetched this pass).
- **Uncertainty/variants:** Pattern identification is subjective; boundary placement varies by analyst.

## event-anchor — Event-Anchored Level

- **Family:** Chart-pattern boundaries & event anchors
- **Aliases:** news candle high/low, event high/low, catalyst level, FOMC/NFP level
- **Definition:** A price reference anchored to a specific event's candle or move (e.g. the high/low of the candle that printed on a news release), used as a subsequent support/resistance reference.
- **Boundaries:** Anchored to an *event*, not to structure (swing) or time (session). Distinct from a swing high (no structural confirmation required). The event itself is a separate primitive; this entry is the price reference it leaves.
- **Observable inputs:** The event's timestamp; the high/low of the associated candle(s).
- **Recognition semantics:** Mark the high and low of the candle(s) around a known event timestamp as reference levels.
- **Parameters/profiles:** `event-window` (how many candles) — `unresolved`. `event-source` (calendar) — `unresolved`.
- **Eligible roles:** location, trigger, context.
- **Market/data constraints:** Requires an event calendar/timestamp; OHLC only.
- **Transfer notes:** Fully transferable to Forex/crypto spot (events differ per market).
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** Which candle(s) count as "the event candle" is discretionary.

## measured-move — Measured Move

- **Family:** Chart-pattern boundaries & event anchors
- **Aliases:** measured move, projection, swing projection, AB=CD (loose)
- **Definition:** A price projection derived from a prior swing's size, used as a target (e.g. project the height of a range/pattern from the breakout point).
- **Boundaries:** A *projection/target*, not a support/resistance level. Distinct from Fibonacci extensions (ratio-based) though related. Not observed structure — a construction.
- **Observable inputs:** A prior swing/range's height; the projection origin.
- **Recognition semantics:** Measure a prior move's height and project it from the breakout/reversal point in the move's direction.
- **Parameters/profiles:** `projection-ratio` (100% vs other) — `unresolved`. `source-swing` — `unresolved`.
- **Eligible roles:** target/exit, location.
- **Market/data constraints:** OHLC only; discretionary.
- **Transfer notes:** Fully transferable to Forex/crypto spot.
- **Evidence/status:** ontology-seed — needs source evidence.
- **Uncertainty/variants:** Projection ratio and source-swing selection are discretionary.

## volume-profile — Volume Profile

- **Family:** Volume-profile references
- **Aliases:** volume profile, VP, volume-by-price, horizontal volume
- **Definition:** A charting technique that plots traded volume distributed across price levels (a horizontal histogram) over a chosen period, revealing where volume concentrated.
- **Boundaries:** A *data visualization/derived distribution*, not a single level. Distinct from time-based volume (vertical bars) and from market profile (time-at-price/TPO). The levels it yields (POC, VAH, VAL, HVN, LVN) are separate primitives.
- **Observable inputs:** Price and volume per level over the profiled period.
- **Recognition semantics:** Bin executed volume by price level over the period; render as a horizontal histogram. Derived levels are read from the histogram.
- **Parameters/profiles:** `profile-period` (session/day/week/visible range) — `unresolved`. `bin-size` (rows) — `unresolved`. `value-area %` = 70% — `published-convention` (TradingView).
- **Eligible roles:** context, location (via derived levels), filter.
- **Market/data constraints:** Requires volume. In spot FX there is no consolidated volume — profiles are broker/venue-specific (tick volume). In crypto, profiles are exchange-specific and fragmented. Originates in centralized futures/equity.
- **Transfer notes:** NOT cleanly transferable to spot FX (no central volume). Partially transferable to crypto spot per-exchange. Must be labeled venue-specific; never silently treated as a spot-FX fact.
- **Evidence/status:** https://www.tradingview.com/support/solutions/43000502040-volume-profile-indicators-basic-concepts/ ; https://oyamori.com/learning/volume-profile-trading/
- **Uncertainty/variants:** Market profile (TPO/time-based) is a distinct but overlapping technique; "volume profile" vs "market profile" terminology is often conflated.

## point-of-control — Point of Control (POC)

- **Family:** Volume-profile references
- **Aliases:** POC, point of control, volume POC
- **Definition:** The single price level with the highest traded volume (or most time, in TPO terms) within a profiled period.
- **Boundaries:** A *derived level* from a volume/time profile, not observed structure. Distinct from a swing point. The "magnet" behavior is a claim, not a validated rule.
- **Observable inputs:** A volume profile (or market profile) over the period.
- **Recognition semantics:** Find the price row with the maximum volume (volume profile) or maximum TPO count (market profile).
- **Parameters/profiles:** `profile-period` — `unresolved`. `composite vs single-session` — `unresolved`.
- **Eligible roles:** location, context, target (mean-reversion), confirmation.
- **Market/data constraints:** Same volume-data limitation as volume-profile (spot FX = broker-specific; crypto = exchange-specific).
- **Transfer notes:** Same transfer limitation as volume-profile.
- **Evidence/status:** https://www.tradingview.com/support/solutions/43000502040-volume-profile-indicators-basic-concepts/ ; https://marketprofile.info/articles/value-area-explained
- **Uncertainty/variants:** Volume POC vs TPO POC differ; composite POC (multi-session) is a variant.

## value-area — Value Area (VA / VAH / VAL)

- **Family:** Volume-profile references
- **Aliases:** VA, value area, VAH, VAL, value area high, value area low
- **Definition:** The price band containing a specified percentage (typically 70%) of the profiled period's volume (or time), bounded by the Value Area High (VAH) and Value Area Low (VAL).
- **Boundaries:** A *range* (two levels: VAH and VAL), not a single level. Distinct from the POC (a single level) and from a structural range (swing-based). The "fair value" framing is interpretation.
- **Observable inputs:** A volume profile (or market profile); the value-area percentage.
- **Recognition semantics:** Starting at the POC, expand outward adding adjacent price rows (highest-volume side first) until the target percentage of total volume/time is captured; the outer bounds are VAH and VAL.
- **Parameters/profiles:** `value-area %` = 70% — `published-convention` (TradingView; trader-discretion). `expansion-rule` (POC-outward) — `published-convention`.
- **Eligible roles:** location (VAH/VAL), context (in/out of value), trigger (acceptance/rejection), target.
- **Market/data constraints:** Same volume-data limitation as volume-profile.
- **Transfer notes:** Same transfer limitation as volume-profile.
- **Evidence/status:** https://www.tradingview.com/support/solutions/43000502040-volume-profile-indicators-basic-concepts/ ; https://marketprofile.info/articles/value-area-explained
- **Uncertainty/variants:** 70% is a convention, not a law; TPO-based vs volume-based value areas differ.

## volume-node — High / Low Volume Node (HVN / LVN)

- **Family:** Volume-profile references
- **Aliases:** HVN, LVN, high-volume node, low-volume node, volume shelf, air pocket
- **Definition:** A local peak (HVN) or trough (LVN) in the volume-profile histogram away from the POC. HVN = a price level of heavy acceptance; LVN = a thin level price crossed quickly.
- **Boundaries:** *Derived levels* from a profile, not observed structure. Distinct from POC (the global max) — nodes are local extrema. The "sticky HVN / fast LVN" behavior is a claim, not a validated rule.
- **Observable inputs:** A volume profile; the histogram's local extrema.
- **Recognition semantics:** Identify local maxima (HVN) and minima (LVN) in the volume-by-price histogram, excluding the POC.
- **Parameters/profiles:** `node-detection` (local-extrema width) — `unresolved`. `profile-period` — `unresolved`.
- **Eligible roles:** location, target, context.
- **Market/data constraints:** Same volume-data limitation as volume-profile.
- **Transfer notes:** Same transfer limitation as volume-profile.
- **Evidence/status:** https://oyamori.com/learning/volume-profile-trading/ ; https://www.quantum-algo.com/blog/guides/volume-profile-trading-complete-guide/
- **Uncertainty/variants:** HVN/LVN detection thresholds are discretionary; LVN vs FVG (both "thin" zones) are conceptually adjacent but data-distinct.

---

## Deduplication notes

- **Swing high/low vs session high/low vs previous-day high/low:** kept distinct — swing points are structure-anchored, session/day/week/month references are time-anchored. They are different primitives even when they coincide in price.
- **Support/resistance vs supply/demand vs order block:** kept distinct as three layers — (1) classic S/R (line, repeated touches), (2) supply/demand zone (impulse base, area), (3) order block (ICT-specific single-candle variant). The freshness-vs-touches contradiction between (1) and (2) is recorded, not resolved.
- **FVG vs imbalance vs liquidity-void vs price-gap:** four distinct concepts sharing loose "gap" language. FVG = SMC three-candle skip; imbalance = order-flow bid/ask lopsidedness (data-distinct); liquidity-void = single-candle wick gap; price-gap = session-to-session discontinuity. Kept separate because their data requirements differ (OHLC-only vs order-flow data).
- **Bollinger vs Keltner vs Donchian vs MA-envelope:** four envelope constructions with different volatility bases (σ, ATR, price extremes, fixed %). Kept separate; not merged into one "envelope" entry.
- **Pivot point vs swing pivot:** same word, different concepts — classic pivot = derived H/L/C formula; swing pivot = observed turning point. Both present, disambiguated in boundaries.
- **Volume profile vs market profile:** market profile (TPO/time-at-price) folded into volume-profile's uncertainty/variants rather than a separate entry, to avoid near-duplication; the distinction is recorded.
- **Fibonacci extension, channel line, ATR band/STARC:** folded into their parent entries (fibonacci-retracement, trendline, atr) as named variants rather than separate entries, to stay non-duplicative.

## Unresolved taxonomy questions

1. **Freshness vs touches:** classic S/R says "more touches = stronger"; supply/demand says "more touches = weaker (spent)". These cannot both be true as stated. Needs a decision on whether they are different primitives, different regimes, or one is wrong.
2. **SMC/ICT block taxonomy:** order block / breaker / mitigation / rejection / propulsion blocks have no single authoritative definition; ICT's own teaching has evolved (multiple "models"). A STRATS normalization decision is needed on which are distinct primitives vs aliases.
3. **"Liquidity" in spot markets:** the liquidity-pool family is inferred from price structure in spot FX (no central book). Whether STRATS should model "liquidity" as a price-structure heuristic vs a data-dependent concept is unresolved.
4. **Session/day boundary conventions:** FX (broker server time) vs crypto (UTC midnight) vs futures (RTH) day boundaries are not standardized. A STRATS-wide convention is needed before session/day/week/month references are fully operational.
5. **Close-vs-wick break basis:** BOS/CHoCH, polarity-flip, and pattern-boundary all hinge on whether a "break" requires a close or a wick. This is unresolved and materially changes timing.
6. **Volume-dependent primitives in spot FX:** VWAP, volume profile, POC/VA/nodes, and order-flow imbalance all require volume that spot FX does not centrally provide. Whether STRATS treats these as "crypto/futures-only" or "broker-proxy" primitives is unresolved.
7. **Equilibrium definition:** premium/discount's equilibrium level (50% vs OTE 62–79%) is not standardized.
8. **Swing strength default:** no STRATS-wide N for swing detection exists; fractal N=2 vs significant-swing N=3–5 conflict.

## Evidence provenance note

All URLs above are real public pages retrieved during this pass via web search. They are cited for *terminology/definition* only. None of them, and nothing in this file, is claimed to demonstrate trading edge, profitability, or reliability. Where a source states a statistic (e.g. FVG fill rates, "80% rule"), it is recorded as a source-stated claim, not a validated fact. Entries without a URL are marked `ontology-seed — needs source evidence`.
