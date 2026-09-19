# MQL5 corpus miner B — scalping / microstructure / news method notes (PLAN)

**Date:** 2026-09-09  
**Scope:** Method evidence only, from the local MQL5 library. PLAN notes for QMX **MIS** (versioned information / labelers). No implementation, no `docs/` edits, no git commit.  
**Do not hit mql5.com.** Evidence is the on-disk markdown, not the origin.

**QMX ownership (this brief):**

- **MIS** snapshots labels/features to the Book door / KSA. MIS never owns entries, exits, pending orders, or bots.
- **SQS** is a separate **block-only** producer. Session *ranges* as locations may be SQS blocks; session *clocks* and quality flags are not.
- **Book** owns doors, admission, and **fast invalidation**. A MIS snapshot of “news window active” or “spread RED” is information; Book decides whether to invalidate.
- **Bot** is market-facing execution. Nothing in this file is a bot spec.

**Corpus inventory:** `C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/coverage.md` — cataloged 3315, fetched ok 3057, failed 258 (Firecrawl 401/402). Keyword scan of ok titles (~221 title hits) then 12 full reads.

**Read fully (12):** 9804, 23355, 22938, 22939, 15748, 19290, 18867, 1575, 21235, 16752, 9231, 22772.

**Not selected (high noise / wrong layer):** 15895 “Scalping Orderflow” is a mashup EA (tick-volume vs MA/ADX/RSI/BB), not tape/DOM. 1509 Comfortable Scalping is a UI helper. 18038 Grid-Mart scalping is toxic execution. Calendar UI series (18299…) is dashboard plumbing. DoEasy tick/DOM parts are library objects, not methods.

**Empirical status:** all rows untested in QMX. Source claims are not an edge.

---

## Brief table

| path | method | scalper use | transfer caveat | MIS vs SQS vs bot |
|---|---|---|---|---|
| `.../md/9804.md` Bid/Ask spread analysis (Kelly, 2021-09-07) | Per-bar **actual mean spread** from `CopyTicksRange` bid/ask vs broker **declared** spread. Round-trip cost as % of SL. Session/news/weekend spread multiples. | Gate tiny R: 5-pip scalp vs ~2-pip true spread ≈ 40% of stake; news ~3× declared; after 20:30 UK / weekend up to ~10×. Prefer majors vs USD. | Broker-specific tick archive; MT5 ticks only; “points vs pips” mix; ZigZag 7-pip swing claim is one EURUSD M1 sample, not a law. FX retail spread ≠ exchange quoted spread. | **MIS:** snapshot `spread_mean_bar`, `spread_vs_declared`, hour-of-week cost surface to Book door. **Book:** cheap/expensive door + fast invalidation on spike. **Not bot.** Not SQS (not a block). |
| `.../md/23355.md` Adaptive spread monitoring (Iorkumbul, 2026-07-28) | Rolling **histogram of spread in points**; percentile rank vs own recent ticks; GREEN ≤ P75, YELLOW, RED ≥ P95; WARMING until window filled. Gate = not RED/WARMING. | Static pip caps fail across pairs (EURUSD 0.5 vs GBPJPY 1.5). Scalp edge eaten before price moves. | Window is **tick-count**, not clock: thin overnight ticks span hours; no TOD weighting; clamp at `InpMaxSpreadPts` collapses tail; cannot tell regime shift vs spike. Defaults (5k ticks, P75/P95) are researcher knobs. | **MIS:** snapshot `spread_pct_rank`, `spread_median`, `spread_status`. **Book:** door uses status; hysteresis/cooldown is Book policy, not MIS. **Bot must not** own `IsOrderAllowed`. Not SQS. |
| `.../md/22938.md` Microstructure noise Part 5 (Brown, 2026-06-15) | Split variation into **information vs noise**. Roll implied spread; OHLC noise ratio (close-to-mid 40% + inverted body/range 40% + OC/range var 20%); range as quoted-spread **proxy**; close-in-range volume-weighted **imbalance** ∈ [−1,+1]. | High noise → bar-level mean reversion is bounce, not a scalp signal. Wide range-proxy → do not fire. | **NQ M1 futures**, 602 NY sessions, not FX/crypto spot. Roll spread ≈ 0 at M1 (intrabar discovery eats bounce). Range proxy **conflates spread with directional range**. Tick volume on FX is not traded volume. | **MIS:** snapshot `noise_ratio`, `quoted_spread_proxy`, `bar_imbalance` with venue=`NQ_M1` provenance. **Book:** may down-weight / refuse door when noise high. **Not a trigger.** Not SQS. Empirical NQ numbers do not transfer. |
| `.../md/22939.md` Microstructure order flow Part 6 (Brown, 2026-06-23) | OHLCV **VPIN proxy** (close-in-range × volume); signed flow imbalance; 20-session **trade intensity**; **Smart Money Index** (late minus early session return); flow momentum. Confidence gated by Part 5 noise (P75 0.632) and Part 4 jumps (P90 → confidence 0). | Directional **context** only. Source: VPIN-OHLC range 0.45–0.62 on NQ M1 — weak. Do not treat as PIN. | Canonical VPIN needs **volume buckets + aggressor flags**. Time bars lose activity-stationarity. Lee-Ready-from-OHLC is noisy. FX/crypto **tick volume ≠ volume**. SMI “informed late session” is a futures-session story. | **MIS:** snapshot `vpin_ohlc`, `flow_imbalance`, `trade_intensity`, `smi`, `flow_confidence` labelled **proxy**. **Book:** may ignore flow when confidence=0. **Never bot sizing from Kyle λ.** Not SQS. |
| `.../md/15748.md` Order-book indicator Part I (Santos, 2025-04-11) | DOM = resting limits, often cancelled. Depth = `SYMBOL_TICKS_BOOKDEPTH` (0 if no queue). Histogram of BookEvent; **tester has no native BookEvent** (custom-symbol simulation). | Liquidity **zones** as context, not a standalone scalp. Author: do not build a system **solely** on the book. | Most **spot FX / crypto-spot** retail books are thin, synthetic, or absent (`BOOKDEPTH=0`). Simulated BookEvent is not evidence. Cancelled size ≠ real liquidity. | **MIS:** only if venue actually streams depth — snapshot depth, bid/ask size imbalance, with venue provenance. If `BOOKDEPTH=0`, **do not emit fake DOM labels**. Resting clusters as **locations** → **SQS blocks**, not MIS. **Bot never.** |
| `.../md/19290.md` Tick-buffer VWAP + short-window imbalance (Benjamin, 2025-09-02) | Ring buffer of ticks → rolling **VWAP**; uptick/downtick **imbalance** and signed **flow** over N seconds; live spread vs ATR “cheap spread”; hysteresis alerts. Explicitly **not** DOM/tape. | Short-horizon fair-value + pressure when DOM missing. Filter when spread not cheap vs ATR. | Tick-count flow ≠ volume-weighted aggressor. Broker ticks ≠ tape. VWAP on FX tick volume is a **participation proxy**. Tester tick granularity ≠ live. Alert/lot/ATR-stop logic is bot-layer. | **MIS:** snapshot `tick_vwap`, `tick_imbalance`, `tick_flow`, `spread_pips`, `spread_vs_atr`. **Book:** cheap-spread door. Fast invalidation if spread blows. **Not bot alerts/markers.** VWAP is a coordinate, not an SQS block unless later promoted as a level. |
| `.../md/18867.md` London session breakout (Mutiiria, 2025-07-23) | Pre-London box (defaults **03:00–09:00** vs London start 09:00) high/low; trade only if range ∈ **[100, 300] points**; pending buy/sell stops with offset; delete opposite on fill. | Classic London-open scalp/intraday: range-too-small = noise, too-wide = already spent. Overlap with Asia/Europe is the event, not “London” as a trigger. | Hours are **broker server time**, DST-fragile (same warning as 1575). 100/300 points and 500-pt SL are EA defaults, not measured. False-breakout rate unquantified here. Pending-stop fill during spread spike is an execution problem. | **Pre-London H/L → SQS block** (location). **MIS:** snapshot `session_id`, `london_open_flag`, `pre_london_range_pts`, `range_in_band`. **Book:** admit only in-band; **fast invalidation** on failed break / news, not MIS. Pendings/trailing/DD halt → **bot + Book**, never MIS. |
| `.../md/1575.md` Asian-session myth check (Игорь, 2010-02-11, MT4) | Session bull/bear = open vs close; virtual TP from session close vs SL at session extreme; last **50 days**, TP 5/15/25 points, windows 03–13 / 03–09 / 09–13. | **Falsifies** “whole day follows Asia” for USDJPY, EURUSD, GBPJPY, NZDUSD. 5-pt continuation ~60–70% ≈ coin-flip except one EURUSD 5-pt cell at 100% on n=50. | n=50, Nov 2009, Moscow-ish hours, 4-digit era adjacent. Overlap 09–13 is not “pure Asia”. Server time / DST. Do not promote the 100% cell. | **MIS:** snapshot `asia_dir`, `asia_range`, `pure_asia_vs_overlap` clocks — as **features**, not a continuation trigger. **SQS:** Asia high/low as optional session blocks. **Book:** do not admit “Asia trend continuation” without a later certified candidate. **Not bot.** |
| `.../md/21235.md` Economic Calendar news windows Part 1 (Sunday, 2026-02-18) | Native calendar (no HTTP). Currency-aware relevance (FX base/quote; heuristic GOLD→USD, GER40→EUR). Importance filter. **Pre- and post-event buffers**. Block **new entries**; optional close-before-high-impact. 24h cache; tester can inject times. | Scalp dies on spike/spread/slippage/wicks. Stops often hit by **spread**, not price. Prop windows are compliance, not alpha. | Calendar completeness = **broker feed**. Heuristic symbol→currency. Server time vs event stamp / DST. 24h cache can miss. **Close-before-news is execution**, not a label. | **MIS:** snapshot `news_window_active`, `event_importance`, `event_currency_match`, `minutes_to_event`, `pre_buf`, `post_buf`. **Book owns fast invalidation** and whether the door shuts. Optional flatten → **bot/Book**, never MIS. Not SQS. |
| `.../md/16752.md` Calendar news-event breakout (Chen, 2025-01-21) | If high-impact news within next **5 minutes**, place buy-stop **and** sell-stop at deviation from bid; optional SL; flatten at session close. Tester needs **binary calendar dump** (live calendar not in tester). | Straddle the print. Author also lists **fade**, **filter** (our 21235), and **news scalping** as separate ideas. | Backtest PF 1.26 / 1604 trades on **SPIUSDc** 2019–2024 M5 — index CFD, not FX/crypto spot. News fills are slippage-dominated; author says stress-test high latency. Dual pending = bot. Surprise (actual−forecast) unused. | **MIS:** snapshot upcoming high-impact events + surprise fields **if** PIT actual/forecast exist. **Book:** may refuse **all** news-straddle admission (cost + invalidation). Dual stops / flatten → **bot**. Not SQS unless a pre-news range is explicitly a block. |
| `.../md/9231.md` Combination scalping (Besedin, 2021-05-26) | Fingerprint last 3 M1 bars (length, body, color; ignore wicks) × **expiration minutes** × TP distance; keep combos that **never** lost in that broker’s history. “Guaranteed” TP mostly **5–15 pips**. | Pure M1 scalp lookup. Author: history after 2009 5-digit only; longer TPs have empty stats. | **Severe overfit + leakage.** Combo DB is **broker- and symbol-specific** (shown dead on another broker). In-sample “never lost” is not OOS. 4.4e6 minutes still sparse. Promotional EA attached. Harmonious 37.5-pip grid is anecdote. | **Do not** ship combo tables as MIS labels. If ever examined: challenge **home broker vs analogue vs adversarial**, costs on. Time-stop expiry is **Book/bot policy**, not MIS. Not SQS. |
| `.../md/22772.md` Execution-noise filtering (Borotho, 2026-05-31) | Pre-signal **five filters**: spread expansion vs own mean+sd, tick velocity, quote gaps, micro-vol too low/high, slippage estimate; plus “unstable news / execution” state. Strategy (liquidity-sweep continuation) is **behind** the gate. “Does not predict direction; predicts whether a fill can keep the edge.” | The useful scalp primitive is the **gate**, not the sweep EA. Same failure mode as 9804/23355: live bleed is execution, not signal. | Thresholds live-vs-tester diverge (author admits tester ticks are artificial). XAUUSD/USDZAR in the demo mix. Sweep/BOS logic is a different candidate. 2-month default backtest is not evidence. | **MIS:** snapshot `exec_spread_z`, `tick_velocity`, `quote_gap`, `micro_vol`, `slip_est`, `exec_ok`. **Book:** AND-gate on `exec_ok`; **fast invalidation** if exec flips mid-life. Sweep structure → **SQS blocks** if used at all. Sweep entry → **bot**. |

Paths above are under `C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/`.

---

## MIS candidate primitives (labels only)

Coordinates, not triggers: timeframe, pair, session, regime attach to rules.

| Primitive (working name) | Family | Eligible MIS role | Inputs | Do not |
|---|---|---|---|---|
| `spread_mean_bar` / `spread_pct_rank` | cost / microstructure | filter (pre-trigger), continuous | ticks bid/ask, rolling window | fire entries; use one pip cap for all pairs |
| `spread_vs_declared` / `spread_vs_atr` | cost | filter | ticks + symbol spread + ATR | treat declared spread as truth |
| `session_clock` / `london_open` / `overlap_asia_eu` / `post_2030_uk` | session coordinate | filter | broker time **and** TZ/DST map | treat server hour as London |
| `pre_session_range_pts` | session | filter; **level construction is SQS** | OHLC in pre-window | pending stops from MIS |
| `news_window_active` + `minutes_to_event` | news / event | filter | calendar PIT + currency map + buffers | close positions; own invalidation |
| `tick_vwap` | fair-value coordinate | location **label** (not SQS unless promoted) | tick ring + tick volume | call it DOM |
| `tick_imbalance` / `tick_flow` | order-flow **proxy** | confirmation (weak) | uptick/downtick ± volume | Lee-Ready / real tape |
| `ohlc_noise_ratio` | microstructure noise | filter | OHLC | transfer NQ 0.60 mean to FX |
| `vpin_ohlc` | OF proxy | filter / weak confirmation | OHLCV | call it VPIN or PIN |
| `exec_ok` bundle | execution quality | filter, continuous | spread z, velocity, gaps, micro-vol | bot `IsOrderAllowed` inside MIS |

**SQS-only (not MIS):** pre-London high/low box; DOM resting clusters (if venue has a real book); liquidity-sweep structure. SQS produces blocks; it does not gate ticks.

**Book-only:** door on `spread_status` / `exec_ok` / `news_window_active`; **fast invalidation**; hysteresis; flatten-before-news.

**Bot-only (out of scope):** pendings, trailing, combo-DB entries, news straddles, lot math.

---

## Transfer rules (Forex + crypto spot)

1. Preserve source asset class on every row. NQ Globex M1, SPIUSDc, and broker FX ticks are different venues.
2. Never treat CEX/futures DOM, funding, or exchange volume as spot-FX/spot-crypto facts.
3. FX “volume” in these articles is usually **tick volume**.
4. Session methods are **timezone problems**. Snapshot a named session only with an explicit TZ source (not raw `Hour()`).
5. News: MIS may snapshot the window; Book invalidates. Do not encode “close all” in MIS.
6. Combination-scalping fingerprints are a **warning example** of in-sample scalp mining, not a labeler.

---

## Quoted evidence (verbatim, local files)

From `md/9804.md`: “If you are a smaller scale scalper, e.g. using SL of 5pips & TP 5pips … the percentage cost is now 40% of your stake/risk.” Also: “Don't even consider trading after 20:30 UK time … especially if you decide to hold onto your trading position over a weekend, which as you can see below is almost 10 times the standard 5 point spread.”

From `md/23355.md`: “A spread of 3 pips on an instrument that normally trades at 1 pip is a genuine anomaly. That same 3-pip spread on an instrument that normally sits at 3 pips is completely ordinary.” Limitation: “The rolling window forgets observations uniformly by tick count with no regard for time of day.”

From `md/22938.md`: “The Roll-implied spread returns values approaching zero on NQ M1 data. This is the empirically correct result, not a bug.” And: “the correlation between the enhanced noise ratio and realized vol from Part 4 is only 0.159 across 602 sessions.”

From `md/22939.md`: “The empirical study shows a total VPIN range of 0.45 to 0.62 across 602 sessions … This is a weak but directionally correct signal … must not be interpreted as a statistically calibrated probability of informed trading.”

From `md/15748.md`: “I believe it is not advisable to build a *trading* *system* solely based on the order book.” Also: “for assets that do not have an order queue, the value of this property is zero.”

From `md/19290.md`: “it doesn’t attempt to replicate a full order book or raw tape, it reconstructs the most actionable insights … using only tick data that every broker provides.”

From `md/18867.md`: “identifying the price range formed in the pre-London hours and placing pending orders to capture breakouts from that range.” Inputs include `MinRangePoints = 100`, `MaxRangePoints = 300`, `PreLondonStartHour` 3.

From `md/1575.md`: “the talks that \"The whole day trading depends on how the Asian session is traded\" is wrong, at least for these 4 currency pairs for the last 50 days.” And: “The probability of Take Profit execution with 5 points is near to 60-70%, in such a case I consider it as a probability of tossing a coin.”

From `md/21235.md`: “Most news filters for trading robots do only one thing — block new trades during news releases. That is not enough.” And: “stops are often triggered by spread widening rather than real price movement.”

From `md/16752.md`: “For each closed bar, we check if there is a high-impact news event within the next 5 minutes. If so, we place buy stop and sell stop orders within a given deviation from the current bid price.” Future-idea list includes fading, filtering, and news scalping as **separate** methods.

From `md/9231.md`: “the database of successful combinations will only be valid for the broker whose trading history was used.” And: “only candlesticks with the most popular size (5 to 40 pips) and \"guaranteed\" take profit distances of 5 to 15 pips have full statistical coverage.”

From `md/22772.md`: “The EA does not predict direction. It predicts whether the market can currently fill an order without destroying the edge.” Filters named: “spread expansion, tick velocity, quote gaps, micro-volatility, and execution stability.”

---

## PLAN implications (no build)

1. First MIS snapshots worth specifying later: **spread distribution**, **session clock + pre-session range size**, **news window**, **tick VWAP/imbalance**, **exec_ok**. All versioned; all venue-tagged.
2. London box **levels** wait for SQS, not MIS.
3. Do not prototype combo-scalp DBs or news straddles as MIS.
4. Fast invalidation stays Book-owned even when MIS already knows the news/spread state.
5. Any later candidate that uses these labels still needs challenge pairs, costs, and PIT calendar — not a tester screenshot from the article.

## Sources

Local corpus only:

- `C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/coverage.md`
- `C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/md/9804.md`
- `C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/md/23355.md`
- `C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/md/22938.md`
- `C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/md/22939.md`
- `C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/md/15748.md`
- `C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/md/19290.md`
- `C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/md/18867.md`
- `C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/md/1575.md`
- `C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/md/21235.md`
- `C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/md/16752.md`
- `C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/md/9231.md`
- `C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/md/22772.md`
