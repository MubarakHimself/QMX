# 22263: Market Microstructure in MQL5 (Part 1): Robust Foundation
HEADS: # Market Microstructure in MQL5 (Part 1): Robust Foundation | ### Introduction | ### | ### Why Intraday Data Is Different | ### | ### The Architecture of the Toolkit | ### | ### Constants and Configuration | ### | ### Data Structures | ### | ### Safe Math Functions | ### | ### Data Validation and Access

## Intro
# Market Microstructure in MQL5 (Part 1): Robust Foundation

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Trading systems](https://www.mql5.com/en/articles/mt5/trading_systems) | 8 May 2026 at 08:10

2 049 [ 0](https://www.mql5.com/en/forum/509457 "Comments")

[Max Brown](https://www.mql5.com/en/users/gcg26)

You trade NQ around the New York open and therefore rely on minute‑level microstructure to stay ahead of fast price moves. At this frequency, standard calculations break quietly: NaN/Inf and overflows from divisions by near‑zero, log of non‑positive prices, zero or missing closes at the edge of history, and degenerate variance estimates from tiny samples. These are not compiler errors—they are plausible numbers that mislead decision logic and cost trades.


## Key hits
**score 2:** Volatility clustering means large moves follow large moves and small moves follow small moves. This is not random noise—it is structure. But it also means that a volatility estimate built on a quiet period will be dangerously wrong when applied to an active period.

**score 2:** GMT\_OFFSET\_HOURS of 2 reflects a broker on GMT+2. All session detection in Part 7 is built on this offset. If your broker runs on a different offset, change this constant once, and the entire time-aware system adjusts automatically.

**score 2:** Every field in OrderFlowSignal has a specific meaning. Strength is the directional imbalance; momentum is its rate of change; exhaustion captures fading flow; and smart\_money reflects the impact of high-volume bars. The direction\_numeric field exists specifically for use in mathematical expressions downstream—string comparisons have no place in a calculation pipeline.

**score 2:** This is the function that separates this toolkit from a naive implementation. The 10% symmetric trim removes the most extreme values before calculating mean and variance. On NQ M1 data at the NY open, those extreme values are real—they are not measurement errors—but they should not dominate a statistical estimate intended to characterize typical behavior. The function falls back to standard mean\_var if the dataset is too small to trim sensibly.

**score 2:** This article tests three common filters on a standard MACD crossover for US\_TECH100 H1 using five years of broker-native data. Filters are layered incrementally: regime, higher timeframe (HTF) alignment, and US session timing, to isolate each one's marginal impact. Results show session timing contributes far more than indicator refinements, while regime and HTF add little on their own. Includes a reproducible MQL5 regime classifier.

**score 2:** The article replaces hardcoded cost assumptions in triple-barrier labeling with measured inputs. An MQL5 script captures spread distribution, swap rates, and symbol metadata from your broker, and a Python model converts them into a broker-calibrated min ret you can pass to get events. Labels then reflect the actual round-trip friction for your instrument and holding period.

**score 1:** You trade NQ around the New York open and therefore rely on minute‑level microstructure to stay ahead of fast price moves. At this frequency, standard calculations break quietly: NaN/Inf and overflows from divisions by near‑zero, log of non‑positive prices, zero or missing closes at the edge of history, and degenerate variance estimates from tiny samples. These are not compiler errors—they are plausible numbers that mislead decision logic and cost trades.

**score 1:** This article addresses that engineering gap. Its goal is practical and specific: provide a defensive MQL5 foundation that guarantees intraday measurements do not emit silent numerical failures. The target audience is MQL5 developers working with CopyClose/SymbolInfoDouble on intraday data (e.g., M1 NQ). Deliverable: a compilable include file that enforces minimum sample sizes, rejects invalid price data, bounds and validates mathematical operations, and supplies stable statistical and spectral primitives so downstream microstructure metrics are


## Tail
[MetaTrader 5 Machine Learning Blueprint (Part 14): Transaction Cost Modeling for Triple-Barrier Labels in MQL5](https://www.mql5.com/en/articles/22372)

The article replaces hardcoded cost assumptions in triple-barrier labeling with measured inputs. An MQL5 script captures spread distribution, swap rates, and symbol metadata from your broker, and a Python model converts them into a broker-calibrated min ret you can pass to get events. Labels then reflect the actual round-trip friction for your instrument and holding period.

[Beyond the Clock (Part 1): Building Activity and Imbalance Bars in Python and MQL5](https://www.mql5.com/en/articles/22063)

The article replaces clock-based sampling with López de Prado's alternative bar types and provides two aligned implementations: a unified Python module for batch tick histories and an object‑oriented MQL5 library for live EAs. It covers Parquet/Dask infrastructure, data cleaning, and a single API. Practical issues are solved explicitly: zero‑tick time‑bar filtering, imbalance threshold initialization, EWM state persistence, and parity between Python and MQL5 outputs.

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F1171%3Futm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Dbest.vps%26utm_content%3Drent.vps%26utm_campaign%3D0622.MQL5.com.Internal&a=nwegcasiojnqcoyrdlgofmjtfardztwf&s=d64d6f3c87f2458cba81f6d7b6694dd9e89dd354d4abc1d0584e405285806c9f&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=mqbtxvaafhtnkvwqrwxwtcdguriuyngg&ssn=1788778654375275931&ssn_dr=0&ssn_sr=0&fv_date=1788778654&ref=https%3A%2F%2Fwww.mql5.com%2Fen%2F


---
# 22553: Market Microstructure in MQL5 (Part 2): Measuring long memory in MQL5 with Hurst estimators
HEADS: # Market Microstructure in MQL5 (Part 2): Measuring long memory in MQL5 with Hurst estimators | ### Introduction | ### | ### What the Hurst Exponent Means for an NQ Trader | ### | ### Three Estimators, Three Lenses | ### | ### Implementation: HurstExponentRS() | ### | ### Implementation: AdvancedHurstExponent() | ### | ### Implementation: HurstExponentRobust() | ### | ### The HurstProfile Indicator

## Intro
# Market Microstructure in MQL5 (Part 2): Measuring long memory in MQL5 with Hurst estimators

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Indicators](https://www.mql5.com/en/articles/mt5/indicators) | 25 May 2026 at 08:11

1 547 [ 0](https://www.mql5.com/en/forum/510226 "Comments")

[Max Brown](https://www.mql5.com/en/users/gcg26)

[Part 1 of this series](https://www.mql5.com/en/articles/22263) built the defensive foundation: guarded math, validated price feeds, and stable statistical primitives. Every function there was designed to fail safely rather than silently. With that layer in place, we can begin the first measurement.


## Key hits
**score 6:** The empirical study on 133 sessions of NQ M1 Globex futures established four findings that every practitioner using this code should understand. NQ M1 operates near the random walk boundary—the confidence-weighted blend from pooled data gives H = 0.511, and the rolling bar-by-bar mean gives H ≈ 0.48, with all three estimators straddling 0.5. The estimator requires 40 post-open bars before it activates. Pre-open and post-open data must not be mixed in the rolling window. The blended H does not significantly predict intraday trending in a 133-ses

**score 5:** The article also includes an empirical study. Using 133 sessions of NQ M1 Globex futures data, we compute H\*(t) bar by bar across the full Globex day. The results differ from textbook expectations in several important respects. Those empirical findings drive the practical threshold recommendations in the final section.

**score 5:** profile, NQ M1 Globex futures. Mean H*(t) hovers near the random walk boundary of 0.5 throughout the Globex day, with the three estimators straddling 0.5 in both directions. The standard deviation band of approximately ±0.13 reflects substantial session-to-session variation around that boundary. 133 sessions, Nov 2025–May 2026")

**score 4:** The study used 133 Globex trading sessions of NQ front-month futures from November 2025 to May 2026. All data is M1, timestamped in Eastern Time. The Python implementation of HurstExponentRobust() was coded from scratch to match the MQL5 spec: the same three estimators, the same confidence weighting, and the same log-return filter. It was cross-validated against the NT8 indicator output at a correlation of 0.60. The correlation is 0.60 because the NT8 version uses cross-day history while the Python study uses session-only history, demonstrating

**score 4:** Across 133 sessions, mean H\*(t) within the NY session ranges from 0.47 to 0.50, straddling the random walk boundary. When three estimators are applied to pooled post-open data (Figure 2), R/S gives H = 0.582, aggregated variance gives H = 0.479, and absolute moments gives H = 0.493—a confidence-weighted blend of 0.511. The rolling bar-by-bar average in Figure 4 sits slightly lower at 0.47–0.49, reflecting short-window estimation noise at the 90-bar lookback. Both measurements are consistent: NQ M1 operates close to the random walk boundary wit

**score 4:** This null result has a mechanistic explanation. It is more useful than a positive result in this context. Because NQ M1 operates near the random walk boundary (confidence-weighted H ≈ 0.51 on pooled data; rolling mean ≈ 0.48), the variation in H across sessions is largely noise around that boundary rather than a structured regime signal. The sessions that trend are anomalies; the Hurst estimator, which measures the average long-range correlation over a backward-looking window, does not reliably identify them in advance. The estimator’s value li

**score 3:** One architectural decision requires explanation: the requirement to reset at the session boundary. When a rolling window spans the pre-open and post-open boundary, the return distribution has a structural break. At 09:33 ET, for example, a 90-bar lookback contains 86 pre-open bars and only 4 open bars. Pre-open NQ M1 data is thin, low-participation, and driven by overnight positioning. Post-open data is high participation and driven by institutional order flow. Mixing the two in a single regression produces an H reading that describes neither r

**score 3:** stabilisation within the NY session. Panel A shows mean H*(t) ±1 SD by bar after the session reset at 09:30 ET. The estimator returns the fallback value of 0.5 for the first 40 bars. Panel B shows the estimator activation rate, which reaches 100 % at bar 40 (10:10 ET). NQ M1 Globex, 133 sessions, Nov 2025–May 2026")


## Tail
[Evaluating the Quality of Forex Spread Trading Based on Seasonal Factors in MetaTrader 5](https://www.mql5.com/en/articles/15622)

The article examines the quality of a seasonal trading approach on a daily timeframe, both for individual symbols and for spreads. Particular attention is paid to identifying recurring monthly cycles and the possibilities of their application in trading within the current year.

Trade from your iPhone or Android device

You only need an internet connection to use the new powerful MetaTrader 5 Web terminal

Learn more](https://www.mql5.com/ff/go?link=https://trade.metatrader5.com/&a=wtigumvtenarnsocpyfoqnanxrilnbxx&s=ec8c539e52b83881ff2d16eaff6913b25803952eb277cac55f670a102b2edc1f&uid=&ref=https://www.mql5.com/en/articles/22553&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=6484239163682588950)


---
# 22598: Market Microstructure in MQL5 (Part 3): Estimating ARFIMA d with GPH
HEADS: # Market Microstructure in MQL5 (Part 3): Estimating ARFIMA d with GPH | ### Introduction | ### | ### The ARFIMA Connection: d, H, and What Each Measures | ### | ### The GPH Estimator: Log‑Periodogram Regression | ### | ### Implementation: GPHEstimator() | ### | ### Implementation: PopulateARFIMAAnalysis() | ### | ### Empirical Study: GPH Applied to US100 M1 | ### | ### Practical Interpretation and Trading Thresholds

## Intro
# Market Microstructure in MQL5 (Part 3): Estimating ARFIMA d with GPH

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Indicators](https://www.mql5.com/en/articles/mt5/examples_indicators) | 27 May 2026 at 10:17

1 262 [ 0](https://www.mql5.com/en/forum/510327 "Comments")

[Max Brown](https://www.mql5.com/en/users/gcg26)

[Part 1](https://www.mql5.com/en/articles/22263 "Market Microstructure in MQL5: Robust Foundation (Part 1)") of this series built a defensive foundation: guarded math, validated price feeds, and stable statistical primitives. [Part 2](https://www.mql5.com/en/articles/22553/235308 "Market Microstructure in MQL5: Measuring Long Memory (Part 2)") added three Hurst estimators and established a key empirical result for US100 M1 Globex futures: the confidence‑weighted H hovers near 0.5, with the pooled post‑open estimate at 0.511 and the rolling bar‑by‑bar mean at approximately 0.48. All three estimators straddle the random walk boundary.


## Key hits
**score 5:** [Part 1](https://www.mql5.com/en/articles/22263 "Market Microstructure in MQL5: Robust Foundation (Part 1)") of this series built a defensive foundation: guarded math, validated price feeds, and stable statistical primitives. [Part 2](https://www.mql5.com/en/articles/22553/235308 "Market Microstructure in MQL5: Measuring Long Memory (Part 2)") added three Hurst estimators and established a key empirical result for US100 M1 Globex futures: the confidence‑weighted H hovers near 0.5, with the pooled post‑open estimate at 0.511 and the rolling bar‑

**score 4:** The same data used in Part 2 underpins this study: 72 NY sessions of US100 M1 Globex futures from January to May 2026. The New York session is defined as 09:30–16:00 Eastern Time. Returns are log differences of one‑minute closing prices. Returns with an absolute value above 0.1 (10%) are discarded as data artifacts; none were genuine in this dataset.

**score 4:** d near zero (−0.1 to 0.1): No fractional differencing is needed beyond the standard log‑return transformation. The series is close enough to the random walk boundary that integer differencing (d = 1, log returns) is appropriate. This applies to approximately half of US100 M1 sessions. For machine learning feature engineering, log returns are the correct input. Applying fractional differencing with a non‑integer d to this series would be fitting noise.

**score 3:** This article adds two functions to MicroStructure\_Foundation.mqh: GPHEstimator() and PopulateARFIMAAnalysis(). They estimate d via log‑periodogram regression, write the result to RobustFractalAnalysis.arfima\_d, and validate it against the Hurst output from Part 2. An empirical study on 72 NY sessions of US100 M1 data confirms that d is close to zero—consistent with Part 2—and quantifies the session‑to‑session variation.

**score 3:** Applying GPH to all 27,930 NY session bars pooled together gives d = −0.006, implying H = 0.494. This is within 0.005 of the Part 2 pooled Hurst result (H = 0.511 by confidence‑weighted blend). The two estimators agree that US100 M1 operates near the random walk boundary. The R² of the pooled regression is 0.0001—effectively zero—confirming that the log‑periodogram has no meaningful linear slope near zero frequency.

**score 2:** The bandwidth parameter m controls how many frequencies enter the regression. The theoretical recommendation from Geweke and Porter‑Hudak (1983) is m = floor(N^g) with g in (0.5, 1.0). The choice g = 0.65 is the conventional default. It is encoded as GPH\_BANDWIDTH\_EXP. For a 390‑bar NY session (09:30–16:00 ET on US100 M1), this gives m ≈ 36 frequency points.

**score 2:** The confidence measure returned by GPHEstimator() is the R² of the log‑periodogram regression. A high R² means the low‑frequency periodogram points align well with the theoretical linear relationship, lending credibility to the d estimate. A low R²—which is the typical result for near‑random‑walk series—means the regression is fitting noise. The constant GPH\_CONF\_THRESHOLD is set to 0.05; estimates below this threshold are flagged as unreliable in the struct's validation message.

**score 2:** Three validation layers guard the execution path before d is computed. First, ValidateSymbolV2() confirms that the symbol is tradable and the minimum period is met. Second, SafeCopyClose() handles the price fetch—the same function used by every Part 2 estimator, so its error behavior is already tested. Third, the return‑construction loop filters invalid prices and artifacts: returns above ±10% are discarded as tick errors or rollover artifacts. On US100 M1, genuine single‑minute moves of 10% do not occur.


## Tail
[How to Detect and Normalize Chart Objects in MQL5 (Part 1): Building a Chart Object Detection Engine](https://www.mql5.com/en/articles/22540)

This article addresses the interpretative gap between visual chart objects and algorithmic execution. You will build a systematic detector that iterates over all chart objects, identifies analytical types, and normalises their geometric data (time and price coordinates) into a structured SChartObjectInfo array. The implementation uses raw MQL5 functions, a filter‑extract‑store pipeline, and a timer‑driven test EA, resulting in a reusable framework for rule‑based trading inputs.

[Trading with the MQL5 Economic Calendar (Part 12): SQLite Storage and Deduplication](https://www.mql5.com/en/articles/22608)

In this article, we replace the embedded CSV snapshot with a SQLite layer that persists calendar events and triggered trade IDs across restarts. The database lives in the common terminal folder and is shared by live charts and the strategy tester, so both modes read the same data without recompiling. An on-demand downloader with a canvas progress bar fetches history from the calendar API and stores it for offline reuse.

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F22768&a=asavypypfjiefdywsbundfnovsqdqrlg&s=822a63e372eca09eaaa973cc0f82be5093d6c353237035cd7209bf509f0bbb1e&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=rhrgzvkpfkwzexakbnswcosohzyfgixt&ssn=1788778189455535452&ssn_dr=0&ssn_sr=0&fv_date=1788778189&ref=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F22598&back_ref=https%3A%2F%2Fwww.google.com%2F&title=Market%20Microstructure%20in%20MQL5%20(Part%203)%3A%20Estimating%20ARFIMA%20d%20


---
# 22638: Market Microstructure in MQL5 (Part 4): Volatility That Remembers
HEADS: # Market Microstructure in MQL5 (Part 4): Volatility That Remembers | ### Introduction | ### | ### The Stylized Facts of Volatility | ### Implementation 1: Revised Multifractal Spectrum (MFDFA) | ### | ### Implementation 2: Realized and Duration-Adjusted Volatility | ### | ### Implementation 3: Fractional Volatility | ### | ### Implementation 4: FIGARCH-Inspired Proxy | ### | ### Implementation 5: Clustering Index, GJR Leverage Effect, Bipower Jump Intensity | ###

## Intro
# Market Microstructure in MQL5 (Part 4): Volatility That Remembers

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Indicators](https://www.mql5.com/en/articles/mt5/indicators) | 5 June 2026 at 06:59

1 474 [ 0](https://www.mql5.com/en/forum/510797 "Comments")

[Max Brown](https://www.mql5.com/en/users/gcg26)

[Part 1](https://www.mql5.com/en/articles/22263 "Market Microstructure in MQL5: Robust Foundation (Part 1)") built a defensive foundation: guarded math, validated price feeds, and stable statistical primitives. [Part 2](https://www.mql5.com/en/articles/22553 "Market Microstructure in MQL5: Measuring Long Memory (Part 2)") added confidence-weighted Hurst estimation, establishing that US100 M1 Globex operates near the random-walk boundary (pooled H = 0.511, rolling H ≈ 0.48). [Part 3](https://www.mql5.com/en/articles/22598 "Market Microstructure in MQL5: Estimating ARFIMA d with GPH (Part 3)") added the GPH estimator for the fractional differencing parameter d, with pooled d = −0.006 and sessi


## Key hits
**score 6:** The empirical study in this article uses NQ E-mini Nasdaq 100 futures (CME Globex) rather than the US100 CFD instrument referenced in earlier drafts. NQ is the exchange-traded underlying contract; US100 is a retail CFD product whose price is derived from the index, not from actual futures order flow. The microstructure properties being measured — volatility clustering, leverage asymmetry, jump intensity, multifractal structure — are properties of price formation at the exchange level. Using the actual futures contract is therefore a more approp

**score 6:** All estimators were applied to 514 NY sessions of NQ E-mini Nasdaq 100 futures (CME Globex), covering May 2024 through May 2026. The NY session filter retains bars with open time in [14:30, 21:00) UTC. Sessions with fewer than 300 M1 bars are excluded. Data were sourced from a retail futures data provider with CME Group as the underlying exchange. The asymmetry (skewness) field is winsorized at the 1st and 99th percentiles (−1.39 and 1.85) to remove three sessions whose extreme skewness values (maximum 7.81) indicated intraday data artifacts no

**score 4:** [Part 1](https://www.mql5.com/en/articles/22263 "Market Microstructure in MQL5: Robust Foundation (Part 1)") built a defensive foundation: guarded math, validated price feeds, and stable statistical primitives. [Part 2](https://www.mql5.com/en/articles/22553 "Market Microstructure in MQL5: Measuring Long Memory (Part 2)") added confidence-weighted Hurst estimation, establishing that US100 M1 Globex operates near the random-walk boundary (pooled H = 0.511, rolling H ≈ 0.48). [Part 3](https://www.mql5.com/en/articles/22598 "Market Microstructure 

**score 4:** Volatility jumps are rare but consequential. Andersen, Bollerslev and Diebold (2007) proposed bipower variation (BPV = (π/2)·mean(|r t |·|r t−1 |)) as a jump-robust baseline. JumpIntensity() uses BPV as the threshold rather than the sample standard deviation, because a simple σ-threshold is contaminated by the very jumps it is trying to detect. On NQ M1, the 514-session empirical study shows a mean jump intensity of 1.4% with a 90th percentile of 2.1%. A value above 5% is likely to indicate data artifacts — bad ticks, contract rollovers, or fee

**score 4:** Two findings from the regime comparison warrant comment. First, the clustering index is *lower* during acute stress regimes (0.107 for the tariff shock vs 0.147 for normal sessions). During acute stress, volatility becomes more erratic and less predictable bar-to-bar, not more clustered. The ARCH effect weakens precisely when it would be most useful for forecasting. Second, the leverage proxy is negative during the April 2025 tariff shock (−0.011), meaning upward moves amplified volatility more than downward moves. This is consistent with short

**score 4:** All 514 sessions produce valid MFDFA estimates with mean R² confidence of 0.972 (minimum 0.851). Every session exceeds the 0.65 confidence threshold, meaning no session needs to be flagged as unreliable on quality grounds. This is stronger than the US100 pilot study, where 7 of 72 sessions fell below the threshold — consistent with genuine futures microstructure tending to produce more regular scaling behavior than a CFD proxy, though other factors may also contribute to this difference.

**score 4:** The Δα values on NQ futures are substantially higher than those from the US100 CFD pilot study (median 0.875 vs 0.498). This is expected: genuine exchange-traded futures exhibit stronger multifractality than CFD proxies because they reflect actual order flow heterogeneity — the interaction of informed traders, market makers, HFT algorithms, and institutional flow creates richer scaling structure than a broker-constructed index-tracking product. This is consistent with the article's central claim: the near-zero H and d from Parts 2 and 3 are ave

**score 4:** Near-monofractal sessions (Δα < 0.30) are absent from the 2-year NQ sample. The minimum observed Δα is 0.460. This means the lower threshold from the US100 pilot study (Δα < 0.30 = near-monofractal) does not apply to NQ futures. All sessions exhibit at least moderate multifractality; the question is only how strong the mixing is.


## Tail
[Implementing a Breakeven Mechanism in MQL5 (Part 2): ATR- and RRR-Based Breakeven](https://www.mql5.com/en/articles/18111)

This article completes the implementation of ATR- and RRRR-based breakeven mechanisms in MQL5 and develops, from scratch, a class that makes it easy to switch breakeven modes without having to enter the parameters again. To evaluate the effectiveness of each breakeven type, several backtests are run, analyzing their advantages and disadvantages in the context of algorithmic trading.

[Market Simulation (Part 24): Getting Started with SQL (VII)](https://www.mql5.com/en/articles/13059)

In the previous article, we completed the necessary introduction to SQL. And, in my opinion, we properly clarified what we wanted to show and explain about SQL. This was done so that anyone who comes to look at the market replay/simulation system being built can at least get an idea of what may be happening there. The point is that there is no sense in programming things that SQL handles perfectly.

Explore your trading for free Updated statistics in MetaTrader 5 will help you to thoroughly evaluate results and reduce risks Learn more](https://www.mql5.com/ff/go?link=https://www.mql5.com/en/forum/454106&a=bkbqgaxtrafeuegfvjisjjwjohagrvnr&s=25c5856d7857fc6b6db7cffb15ae4ce40fd19d1ab594d8a900ad65673d9ffa0e&uid=&ref=https://www.mql5.com/en/articles/22638&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=5121798919469795459)


---
# 23372: Market Microstructure in MQL5 (Part 8): Micro-Trend Strength
HEADS: # Market Microstructure in MQL5 (Part 8): Micro-Trend Strength | ## Introduction | ## The micro-trend Problem | ## Theory: Four Sub-Scores and a Penalty | ### EMA alignment | ### ATR-normalized price position | ### Slope consistency | ### Volume confirmation | ### The contradiction penalty | ### The combination formula | ## Implementation | ### Enumeration and struct | ### GetMicroTrendStrength() | ### Classification functions

## Intro
# Market Microstructure in MQL5 (Part 8): Micro-Trend Strength

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Indicators](https://www.mql5.com/en/articles/mt5/examples_indicators) | 20 July 2026 at 10:32

1 138 [ 0](https://www.mql5.com/en/forum/513063 "Comments")

[Max Brown](https://www.mql5.com/en/users/gcg26)

[Parts 1 through 7](https://www.mql5.com/en/users/gcg26/publications) of this series build a complete measurement layer for NQ M1 microstructure. Part 1 hardened the mathematical foundation. Parts 2 and 3 measured whether price returns have memory. Part 4 measured how volatility persists. Part 5 decomposed price variation into signal and noise. Part 6 measured the direction of informed flow. Part 7 condensed those eleven measurements into a single regime label and confidence score. What none of them did was tell you, on the current bar, whether the short-term trend is up, down, or flat.


## Key hits
**score 5:** The volume component uses tick volume rather than traded contract volume. On NQ M1, tick volume (the number of price updates per bar) is a reasonable proxy for trading activity, but it is not identical to the number of contracts traded. The proxy relationship is stable during normal sessions and degrades during data-feed anomalies, which are identified as Stressed sessions by Part 7 and which produce near-zero composite scores in any case.

**score 4:** Current bar tick volume is compared to the 20-bar rolling average. The ratio is mapped to [0.5, 1.5] via clip(0.5 + ratio, 0.5, 1.5) , which amplifies the composite when volume is above average and dampens it when volume is below average. The bounds prevent a single extreme-volume bar from dominating the score and prevent a low-volume session from producing a negative multiplier. This multiplier is applied after the additive combination of alignment, price position, and slope.

**score 4:** The composite score was computed bar-by-bar on 514 NY sessions of NQ M1 futures (May 2024–May 2026) using EMA periods 5/8/13 and ATR period 14. Sessions with fewer than 300 bars after the NY open filter were excluded, consistent with the Part 4–7 empirical methodology. The Part 7 regime classification was merged on session date to support the adaptive-threshold analysis.

**score 3:** The empirical study applies the composite to 514 NQ M1 NY sessions (May 2024–May 2026), the same dataset used in Part 7. The primary finding is that the signal distributes asymmetrically across regimes: Trending sessions produce the highest persistence rate (3+ consecutive same-direction bars), while Stressed sessions produce the most flat readings. The adaptive threshold transfers approximately 18% of Stressed-session signals into the no-signal zone compared to fixed thresholds, reducing false-signal exposure without requiring a rule change.

**score 3:** Three findings stand out. First, the Trending regime produces the highest strong-up rate (18.9%) and the highest persistence rate (23.6%) — consistent with Part 7's finding that Trending sessions have the highest clustering index (0.286) and the highest mean confidence (0.593). The micro-trend composite agrees with the regime classification without being given it directly. Second, Stressed sessions produce by far the highest flat rate (61.3%), reflecting the noise and volume uncertainty that drives up noise ratio and depresses flow confidence i

**score 3:** This comparison has a limitation: the adaptive threshold is applied at the session level, not bar-by-bar. The adaptive threshold operates on session-level mean strength as a proxy, not on the bar-by-bar strength with bar-by-bar regime confidence. Part 7's confidence field is computed once per session, so the adaptation occurs at the session level: all bars within a Trending session use the same loosened thresholds. A fully bar-adaptive implementation would require computing regime confidence at every bar, which goes beyond the current Part 7 de

**score 3:** The empirical study on 514 NQ M1 sessions confirms that the composite is regime-coherent without being given the regime label: Trending sessions produce the highest strong-signal and persistence rates, Stressed sessions the lowest, and Mean-Reverting sessions the most negative mean strength. The session-adaptive threshold variant translates Part 7's confidence field into a tighter signal filter for adverse sessions and a looser one for high-confidence sessions.

**score 2:** [Parts 1 through 7](https://www.mql5.com/en/users/gcg26/publications) of this series build a complete measurement layer for NQ M1 microstructure. Part 1 hardened the mathematical foundation. Parts 2 and 3 measured whether price returns have memory. Part 4 measured how volatility persists. Part 5 decomposed price variation into signal and noise. Part 6 measured the direction of informed flow. Part 7 condensed those eleven measurements into a single regime label and confidence score. What none of them did was tell you, on the current bar, whether


## Tail
[Trust Your Backtest Data First: Building a Reproducible Historical Data Audit in Python for MetaTrader 5](https://www.mql5.com/en/articles/23070)

A reproducible, read-only Python audit for MetaTrader 5 that verifies history quality before any backtest. It exports M5 data from multiple terminals, detects gaps and synthetic bars by timestamp spacing, and reports coverage per year. The same deterministic strategy then runs on three broker feeds over a common window to quantify result drift and decompose it into spread, data/price, and trade effects.

[MetaTrader 5 Machine Learning Blueprint (Part 19): Bagging Regimes](https://www.mql5.com/en/articles/23137)

We test AFML's claim that the sequential bootstrap decorrelates bagged trees on overlapping triple‑barrier labels by isolating two levers: draw count and draw rule. One decision identical tree is bagged under four row‑sampling regimes and evaluated on EURUSD 2022–2023 for draw uniqueness, between‑tree correlation, AUC, and calibration. Decorrelation comes almost entirely from throttling max\_samples to average uniqueness; the sequential draw adds little. Out-of-bag inflation is largest under full-count sequential sampling.

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Fmarket%2Fmt5%2Fexpert%3Futm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Dtop.experts%26utm_content%3Dbuy.expert%26utm_campaign%3D0622.MQL5.com.Internal&a=widauvjabtsckwovwaperzkotrcrttvb&s=25ef75d39331f608a319410bf27ff02c1bd7986622ecc1eec8968a650f044731&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=wrcdjurxuqjpoquojfzezkaegictvqcr&ssn=1788777048317262317&ssn_dr=0&ssn_sr=0&fv_date=1788777048&ref=https%3A%2F%2Fwww.mql5.


---
# 9010: Prices in DoEasy library (part 63): Depth of Market and its abstract request class
HEADS: # Prices in DoEasy library (part 63): Depth of Market and its abstract request class | ### Contents | ### Concept | ### Class of the abstract order object in the Depth of Market | ### Descendant classes of the abstract order object | ### Test | ### What's next?

## Intro
# Prices in DoEasy library (part 63): Depth of Market and its abstract request class

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Examples](https://www.mql5.com/en/articles/mt5/examples) | 30 March 2021 at 07:48

9 593 [ 8](https://www.mql5.com/en/forum/366114 "Comments")

[Artyom Trishkin](https://www.mql5.com/en/users/artmedia70)

- [Concept](https://www.mql5.com/en/articles/9010#concept) - [Class of the abstract order object in the Depth of Market](https://www.mql5.com/en/articles/9010#class_of_the_abstract_order_object_in_the_depth_of) - [Descendant classes of the abstract order object](https://www.mql5.com/en/articles/9010#descendant_classes_of_the_abstract_order_object) - [Test](https://www.mql5.com/en/articles/9010#test) - [What's next?](https://www.mql5.com/en/articles/9010#what_s_next)


## Key hits
**score 2:** //--- CMarketBookOrd    MSG_MBOOK_ORD_TEXT_MBOOK_ORD,                      // Order in DOM    MSG_MBOOK_ORD_VOLUME,                              // Volume    MSG_MBOOK_ORD_VOLUME_REAL,                         // Extended accuracy volume    MSG_MBOOK_ORD_STATUS_BUY,                          // Buy side    MSG_MBOOK_ORD_STATUS_SELL,                         // Sell side    MSG_MBOOK_ORD_TYPE_SELL,                           // Sell order    MSG_MBOOK_ORD_TYPE_BUY,                            // Buy order     MSG_MBOOK_ORD_TYPE_SELL_MARKET,          

**score 2:** public: //+-------------------------------------------------------------------+  //|Methods of a simplified access to the DOM request object properties| //+-------------------------------------------------------------------+ //--- Return order (1) status, (2) type and (3) order volume    ENUM_MBOOK_ORD_STATUS Status(void)        const { return (ENUM_MBOOK_ORD_STATUS)this.GetProperty(MBOOK_ORD_PROP_STATUS);   }    ENUM_BOOK_TYPE    TypeOrd(void)           const { return (ENUM_BOOK_TYPE)this.GetProperty(MBOOK_ORD_PROP_TYPE);            }    long 

**score 1:** In this article, I will start implementing the functionality for working with the Depth of Market (DOM). Conceptually, classes for working with DOM will not differ from all previously implemented library classes. At the same time, we will have a mold of DOM featuring data about orders stored in DOM. The data is obtained by the [MarketBookGet()](https://www.mql5.com/en/docs/marketinformation/marketbookget) function when the [OnBookEvent()](https://www.mql5.com/en/docs/event_handlers/onbookevent) handler is activated. In case of any change in DOM

**score 1:** Thus, the DOM class structure is to be as follows:

**score 1:** 1. DOM order object class — the object describing data of one order out of multiple orders obtained from DOM when OnBookEvent() handler is triggered for one symbol; 2. DOM mold object class — the object describing data on all orders obtained from DOM simultaneously at a single activation of the OnBookEvent() handler for a single symbol — p1 set of objects making up the current DOM mold; 3. Timeseries class consisting of the p2 object sequence entered into the timeseries list at each OnBookEvent() activation for a single symbol; 4. Timeseries co

**score 1:** Today I will implement the order object class (1) and test obtaining DOM data when OnBookEvent() is activated for the current symbol.

**score 1:** The properties of each order are set in the [MqlBookInfo](https://www.mql5.com/en/docs/constants/structures/mqlbookinfo) structure providing data in DOM:

**score 1:** DOM may feature four order types (from the [ENUM\_BOOK\_TYPE](https://www.mql5.com/en/docs/constants/tradingconstants/enum_book_type) enumeration):


## Tail
I continue filling the algorithm with the minimum necessary functionality and testing the results. The profitability is quite low but the articles demonstrate the model of the fully automated profitable trading on completely different instruments traded on fundamentally different markets.

[Prices in DoEasy library (part 62): Updating tick series in real time, preparation for working with Depth of Market](https://www.mql5.com/en/articles/8988)

In this article, I will implement updating tick data in real time and prepare the symbol object class for working with Depth of Market (DOM itself is to be implemented in the next article).

[Running robots on virtual hosting is easy Follow our step-by-step MetaTrader VPS guide for beginners Read

](https://www.mql5.com/ff/go?link=https://www.mql5.com/en/articles/13586&a=uzpprdshbcrtxvjxpmescehprypbymxc&s=516438f25b531570d9b7d49dcfb29c82fa1021f5ede6571df8026dbfbafcd13f&uid=&ref=https://www.mql5.com/en/articles/9010&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=6467648413687768349)


---
# 9044: Prices in DoEasy library (Part 64): Depth of Market, classes of DOM snapshot and snapshot series objects
HEADS: # Prices in DoEasy library (Part 64): Depth of Market, classes of DOM snapshot and snapshot series objects | ### Contents | ### Concept | ### Improving library classes | ### Depth of Market snapshot object class | ### Depth of Market snapshot series object class | ### Test | ### What's next?

## Intro
# Prices in DoEasy library (Part 64): Depth of Market, classes of DOM snapshot and snapshot series objects

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Examples](https://www.mql5.com/en/articles/mt5/examples) | 13 April 2021 at 13:07

10 590 [ 6](https://www.mql5.com/en/forum/367161 "Comments")

[Artyom Trishkin](https://www.mql5.com/en/users/artmedia70)

- [Concept](https://www.mql5.com/en/articles/9044#concept) - [Improving library classes](https://www.mql5.com/en/articles/9044#improving_library_classes) - [Depth of Market snapshot object class](https://www.mql5.com/en/articles/9044#depth_of_market_snapshot_object_class) - [Depth of Market snapshot series object class](https://www.mql5.com/en/articles/9044#depth_of_market_snapshot_series_object_class) - [Test](https://www.mql5.com/en/articles/9044#test) - [What's next?](https://www.mql5.com/en/articles/9044#what_s_next)


## Key hits
**score 1:** # Prices in DoEasy library (Part 64): Depth of Market, classes of DOM snapshot and snapshot series objects

**score 1:** In the [previous article](https://www.mql5.com/en/articles/9010), I have created the class of the Depth of Market (DOM) abstract order object and its descendants. The multitude of these objects constitutes one DOM snapshot obtained during one call of the [MarketBookGet()](https://www.mql5.com/en/docs/marketinformation/marketbookget) function at the moment the [OnBookEvent()](https://www.mql5.com/en/docs/event_handlers/onbookevent) handler is activated. Data obtained by the MarketBookGet() function is set in the [MqlBookInfo](https://www.mql5.co

**score 1:** Here, I am going to create two classes — the class of DOM snapshot object of a single symbol and the class of DOM snapshot series of a single symbol. In the next article, I will create and test the class of DOM snapshot series collection.

**score 1:** //--- CMarketBookSnapshot    MSG_MBOOK_SNAP_TEXT_SNAPSHOT,                      // DOM snapshot

**score 1:** //--- CMBookSeries    MSG_MBOOK_SERIES_TEXT_MBOOKSERIES,                 // DOM snapshot series

**score 1:** To be able to specify the criterion for sorting by time when searching for the necessary DOM snapshot objects in the series list, we need to add a new property to the DOM order object — the time of receiving a snapshot in milliseconds. The order itself has no such property but we are able to track the time of receiving a DOM snapshot. To avoid introducing new enumerations for the DOM snapshot series list containing a single integer property (time of obtaining a snapshot in milliseconds), let's add this property to the DOM order object propertie

**score 1:** In \MQL5\Include\DoEasy\**Defines.mqh**, enter the parameters of the DOM snapshot series so that we able to set the necessary amount of data days and the maximum possible number of snapshots in the list:

**score 1:** I am not going to use the first parameter (number of days) yet — later on, I will try to link the data to the number of tick data days. Currently, I will use the second parameter only — maximum possible amount of DOM snapshot data.


## Tail
As the next step in studying neural networks, I suggest considering the methods of increasing convergence during neural network training. There are several such methods. In this article we will consider one of them entitled Dropout.

[Self-adapting algorithm (Part IV): Additional functionality and tests](https://www.mql5.com/en/articles/8859)

I continue filling the algorithm with the minimum necessary functionality and testing the results. The profitability is quite low but the articles demonstrate the model of the fully automated profitable trading on completely different instruments traded on fundamentally different markets.

Access our new hub for expert analytics, trading insights, global financial news, and more

Learn more](https://www.mql5.com/ff/go?link=https://www.metatrader.com%3Futm_source=www.mql5.com%26utm_medium=display%26utm_content=visit%26utm_campaign=visit.metatrader.com.426&a=anvvomolcquvlkemiiwazrokmauingca&s=5edb2ef4182c70fd6beca6df0a841244f4dc3eb3f7df8658c0aeadcf20882dba&uid=&ref=https://www.mql5.com/en/articles/9044&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=6342001700948829463)


---
# 9095: Prices and Signals in DoEasy library (Part 65): Depth of Market collection and the class for working with MQL5.com Signals
HEADS: # Prices and Signals in DoEasy library (Part 65): Depth of Market collection and the class for working with MQL5.com Signals | ### Contents | ### Concept | ### Improving library classes | ### DOM collection class | ### MQL5 signal object class | ### Test | ### What's next?

## Intro
# Prices and Signals in DoEasy library (Part 65): Depth of Market collection and the class for working with MQL5.com Signals

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Examples](https://www.mql5.com/en/articles/mt5/examples) | 20 April 2021 at 12:56

14 307 [ 5](https://www.mql5.com/en/forum/367627 "Comments")

[Artyom Trishkin](https://www.mql5.com/en/users/artmedia70)

- [Concept](https://www.mql5.com/en/articles/9095#concept) - [Improving library classes](https://www.mql5.com/en/articles/9095#improving_library_classes) - [DOM collection class](https://www.mql5.com/en/articles/9095#dom_collection_class) - [MQL5 signal object class](https://www.mql5.com/en/articles/9095#mql5_signal_object_class) - [Test](https://www.mql5.com/en/articles/9095#test) - [What's next?](https://www.mql5.com/en/articles/9095#what_s_next)


## Key hits
**score 1:** - [Concept](https://www.mql5.com/en/articles/9095#concept) - [Improving library classes](https://www.mql5.com/en/articles/9095#improving_library_classes) - [DOM collection class](https://www.mql5.com/en/articles/9095#dom_collection_class) - [MQL5 signal object class](https://www.mql5.com/en/articles/9095#mql5_signal_object_class) - [Test](https://www.mql5.com/en/articles/9095#test) - [What's next?](https://www.mql5.com/en/articles/9095#what_s_next)

**score 1:** We already have the functionality for working with a DOM of any symbol — in the previous articles, I have created the classes of the DOM abstract order objects and its descendants, the DOM snapshot class and the DOM snapshot series class. Now it remains to create a common storage for DOM snapshot series objects — the snapshot series collection class, which is to store all these series with a convenient access to any DOM snapshot stored in the collection lists and auto update (adding new snapshots and removing old ones) for supporting specified 

**score 1:** Apart from creating the DOM snapshot series collection class, I will also start the new library section — other library classes.     I will start with the functionality for working with the [MQL5.com signal service](https://www.mql5.com/en/signals), namely I will create the signal object class storing all data of a single signal broadcast by the MQL5.com Signals service.

**score 1:** //--- CMBookSeriesCollection    MSG_MB_COLLECTION_TEXT_MBCOLLECTION,               // DOM snapshot series collection

**score 1:** Since I am going to develop a new collection today, we need to set its ID. In the ID section in \MQL5\Include\DoEasy\**Defines.mqh**, add the DOM snapshot series collection ID:

**score 1:** Let's improve the file of the DOM snapshot series object class. In some instances, the object description should be displayed once, while sometimes, we need to display descriptions of all DOM snapshot series at once. In this case, the list looks more visually appealing if a hyphen is added before the description of each series. In the file of the DOM snapshot series class \MQL5\Include\DoEasy\Objects\Book\**MBookSeries.mqh**, add the changes in the description of the methods:

**score 1:** We have all the necessary objects for creating the DOM collection. Namely, we have the DOM order object represented by the [MqlBookInfo](https://www.mql5.com/en/docs/constants/structures/mqlbookinfo) structure in the terminal. When the [BookEvent](https://www.mql5.com/en/docs/runtime/event_fire#bookevent) event arrives, the [OnBookEvent()](https://www.mql5.com/en/docs/event_handlers/onbookevent) handler is called. A symbol, on which the DOM change event has occurred, is specified as its parameter. We are able to receive all current DOM data to 

**score 1:** The symbol DOM collection is to store constantly updated DOM snapshot lists allowing us to create the history of DOM changes for each symbol while the program is running. We will be able to get data on any snapshot present in the collection lists. Besides, we will retrieve any order out of each snapshot. We will be able to search for the required data, sort out the lists by specified criteria and conduct statistical studies with the available collection lists.


## Tail
In this article, I will create the signal collection class of the MQL5.com Signals service with the functions for managing signals. Besides, I will improve the Depth of Market snapshot object class for displaying the total DOM buy and sell volumes.

[Machine learning in Grid and Martingale trading systems. Would you bet on it?](https://www.mql5.com/en/articles/8826)

This article describes the machine learning technique applied to grid and martingale trading. Surprisingly, this approach has little to no coverage in the global network. After reading the article, you will be able to create your own trading bots.

[Running robots on virtual hosting is easy Follow our step-by-step MetaTrader VPS guide for beginners Read

](https://www.mql5.com/ff/go?link=https://www.mql5.com/en/articles/13586&a=uzpprdshbcrtxvjxpmescehprypbymxc&s=516438f25b531570d9b7d49dcfb29c82fa1021f5ede6571df8026dbfbafcd13f&uid=&ref=https://www.mql5.com/en/articles/9095&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=6428575184935609620)


---
# 8988: Prices in DoEasy library (part 62): Updating tick series in real time, preparation for working with Depth of Market
HEADS: # Prices in DoEasy library (part 62): Updating tick series in real time, preparation for working with Depth of Market | ### Contents | ### Concept | ### Improving library classes | ### Updating tick series | ### Improving the symbol class for working with the Depth of Market | ### Test | ### What's next?

## Intro
# Prices in DoEasy library (part 62): Updating tick series in real time, preparation for working with Depth of Market

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Examples](https://www.mql5.com/en/articles/mt5/examples) | 24 March 2021 at 09:57

8 164 [ 0](https://www.mql5.com/en/forum/365590 "Comments")

[Artyom Trishkin](https://www.mql5.com/en/users/artmedia70)

- [Concept](https://www.mql5.com/en/articles/8988#concept) - [Improving library classes](https://www.mql5.com/en/articles/8988#improving_library_classes) - [Updating tick series](https://www.mql5.com/en/articles/8988#updating_tick_series) - [Improving the symbol class for working with the Depth of Market](https://www.mql5.com/en/articles/8988#improving_the_symbol_class_for_working_with_the) - [Test](https://www.mql5.com/en/articles/8988#test) - [What's next?](https://www.mql5.com/en/articles/8988#what_s_next)


## Key hits
**score 2:** //--- Save integer properties    this.m_long_prop[SYMBOL_PROP_STATUS]                                             = symbol_status;    this.m_long_prop[SYMBOL_PROP_INDEX_MW]                                           = index;    this.m_long_prop[SYMBOL_PROP_VOLUME]                                             = (long)this.m_tick.volume;    this.m_long_prop[SYMBOL_PROP_SELECT]                                             = ::SymbolInfoInteger(this.m_name,SYMBOL_SELECT);    this.m_long_prop[SYMBOL_PROP_VISIBLE]                                        

**score 1:** Also, I will start preparations for working with the Depth of Market (DOM). I am going to introduce the ability to subscribe to the DOM broadcast in the symbol object class. In the next articles, I will start implementing the functionality for working with DOM.

**score 1:** To be able to understand whether we are subscribed to a DOM broadcast by a symbol, we need to add a parameter to the symbol properties indicating the subscription status. To achieve this, add yet another parameter to the symbol integer properties and increase the number of integer properties from 36 to **37**:

**score 1:** In the next article, I will start implementing the library functionality for working with DOM.

**score 1:** Each DOM connection should correspond to its disconnection. This can easily be done in the class — enable DOM in the constructor and disable it in the destructor. A separate symbol object is created for each symbol. For each of the symbol objects, we can clearly find out when DOM was connected and when it should be disabled.

**score 1:** Open the symbol object class in \MQL5\Include\DoEasy\Objects\Symbols\**Symbol.mqh** and add the necessary changes.     In the private class section, declare the variable for storing the flag of subscribing to DOM, while in the public section, declare the class destructor:

**score 1:** In the methods of the simplified access to symbol properties of the public class section, add the new method returning the status of subscription to DOM:

**score 1:** If the DOM subscription flag is enabled, unsubscribe from DOM broadcast.


## Tail
[Prices in DoEasy library (part 63): Depth of Market and its abstract request class](https://www.mql5.com/en/articles/9010)

In the article, I will start developing the functionality for working with the Depth of Market. I will also create the class of the Depth of Market abstract order object and its descendants.

[Prices in DoEasy library (part 60): Series list of symbol tick data](https://www.mql5.com/en/articles/8912)

In this article, I will create the list for storing tick data of a single symbol and check its creation and retrieval of required data in an EA. Tick data lists that are individual for each used symbol will further constitute a collection of tick data.

How AI helps create robots for MetaTrader 5 Learn from our book "Neural Networks in Algo Trading with MQL5" Read](https://www.mql5.com/ff/go?link=https://www.mql5.com/en/neurobook%3Futm_source=www.mql5.com%26utm_medium=display%26utm_term=read.neurobook%26utm_content=visit.page%26utm_campaign=neurobook.promo.04.2024&a=ghrobswocqgvhztzjldphupateyllpro&s=9929cb0b8629585b5a42fabc06c525e41f6c0ebdf3045d044a5413b93ea88b47&uid=&ref=https://www.mql5.com/en/articles/8988&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=5127362388176823671)


---
# 8818: Prices in DoEasy library (part 59): Object to store data of one tick
HEADS: # Prices in DoEasy library (part 59): Object to store data of one tick | ### Table of contents | ### Concept | ### Preparing data | ### Tick data object class | ### Testing tick data object | ### What's next?

## Intro
# Prices in DoEasy library (part 59): Object to store data of one tick

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Examples](https://www.mql5.com/en/articles/mt5/examples) | 2 February 2021 at 06:53

6 793 [ 1](https://www.mql5.com/en/forum/361846 "Comments")

[Artyom Trishkin](https://www.mql5.com/en/users/artmedia70)

- [Concept](https://www.mql5.com/en/articles/8818#concept) - [Preparing data](https://www.mql5.com/en/articles/8818#preparing_data) - [Tick data object class](https://www.mql5.com/en/articles/8818#tick_data_object_class) - [Testing tick data object](https://www.mql5.com/en/articles/8818#testing_tick_data_object) - [What's next?](https://www.mql5.com/en/articles/8818#what_s_next)


## Key hits
**score 2:** In the concept of tick data storage, the minimal unit of data volume shall be values of price structure on one tick. Such values are described with the use of a structure for storing the last prices by symbol [MqlTick](https://www.mql5.com/en/docs/constants/structures/mqltick). An object to store such values will possess additional properties: spread - the difference of Ask and Bid prices and the symbol the data of which one tick are described by the object.

**score 2:** //--- CTick    MSG_TICK_TEXT_TICK,                                // Tick    MSG_TICK_TIME_MSC,                                 // Time of the last update of prices in milliseconds    MSG_TICK_TIME,                                     // Time of the last update of prices    MSG_TICK_VOLUME,                                   // Volume for the current Last price    MSG_TICK_FLAGS,                                    // Flags    MSG_TICK_VOLUME_REAL,                              // Volume for the current Last price with greater accuracy    MSG_TICK

**score 2:** //--- CTick    {"Tick"},    {"Last price update time in milliseconds"},    {"Last price update time"},    {"Volume for the current Last price"},    {"Flags"},    {"Volume for the current \"Last\" price with increased accuracy"},    {"Spread"},    {"Changed data on a tick:"},    {"Bid price change"},    {"Ask price change"},    {"Last price change"},    {"Volume change"},

**score 2:** //--- Return tick’s (1) Bid, (2) Ask, (3) Last price, (4) volume with greater accuracy, (5) spread of the tick //--- size of the (9) candle upper, (10) lower wick    double            Bid(void)                                          const { return this.GetProperty(TICK_PROP_BID);                      }    double            Ask(void)                                          const { return this.GetProperty(TICK_PROP_ASK);                      }    double            Last(void)                                         const { return this.GetProper

**score 1:** - TICK\_FLAG\_BID — tick changed Bid price - TICK\_FLAG\_ASK — tick changed Ask price - TICK\_FLAG\_LAST — tick changed Last trade price - TICK\_FLAG\_VOLUME — tick changed volume - TICK\_FLAG\_BUY — tick resulted from Buy trade - TICK\_FLAG\_SELL — tick resulted from Sell trade

**score 1:** [Using spreadsheets to build trading strategies](https://www.mql5.com/en/articles/8699)

**score 1:** The article describes the basic principles and methods that allow you to analyze any strategy using spreadsheets (Excel, Calc, Google). The obtained results are compared with MetaTrader 5 tester.

**score 0:** In the method described, first the flag of flag presence within the variable is checked. Depending on whether such change is available or not the resulted text string shall be added with newline character + flag description or an empty string. After checking all flags, finally we have the compiled string which contains descriptions of the flags present in the variable. If several flags are available, the description of each flag will start from a new line in the journal.


## Tail
[Developing a self-adapting algorithm (Part I): Finding a basic pattern](https://www.mql5.com/en/articles/8616)

In the upcoming series of articles, I will demonstrate the development of self-adapting algorithms considering most market factors, as well as show how to systematize these situations, describe them in logic and take them into account in your trading activity. I will start with a very simple algorithm that will gradually acquire theory and evolve into a very complex project.

[Timeseries in DoEasy library (part 58): Timeseries of indicator buffer data](https://www.mql5.com/en/articles/8787)

In conclusion of the topic of working with timeseries organise storage, search and sort of data stored in indicator buffers which will allow to further perform the analysis based on values of the indicators to be created on the library basis in programs. The general concept of all collection classes of the library allows to easily find necessary data in the corresponding collection. Respectively, the same will be possible in the class created today.

Boost your trading experience Read our book "MQL5 Programming for Traders" Begin](https://www.mql5.com/ff/go?link=https://www.mql5.com/en/book%3Futm_source=www.mql5.com%26utm_medium=display%26utm_term=read.algobook%26utm_content=visit.page%26utm_campaign=algobook.promo.04.2024&a=heclgjpfbvfghpmyaciuaesdtswflupo&s=4255fbe1b8cbc4d1b40afbaebf4235e5ace8b5103cba60d996897a03d588556f&uid=&ref=https://www.mql5.com/en/articles/8818&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=6439689499440735685)


---
# 8912: Prices in DoEasy library (part 60): Series list of symbol tick data
HEADS: # Prices in DoEasy library (part 60): Series list of symbol tick data | ### Contents | ### Concept | ### Improving library classes | ### Tick data series object class | ### Testing the list creation and data retrieval | ### What's next?

## Intro
# Prices in DoEasy library (part 60): Series list of symbol tick data

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Examples](https://www.mql5.com/en/articles/mt5/examples) | 17 March 2021 at 06:33

8 298 [ 3](https://www.mql5.com/en/forum/365090 "Comments")

[Artyom Trishkin](https://www.mql5.com/en/users/artmedia70)

- [Concept](https://www.mql5.com/en/articles/8912#concept) - [Improving library classes](https://www.mql5.com/en/articles/8912#improving_library_classes) - [Tick data series object class](https://www.mql5.com/en/articles/8912#tick_data_series_object_class) - [Testing the list creation and data retrieval](https://www.mql5.com/en/articles/8912#testing_the_list_creation_and_data_retrieval) - [What's next?](https://www.mql5.com/en/articles/8912#what_s_next)


## Key hits
**score 2:** //--- Return (1) Bid, (2) Ask, (3) Last, (4) volume with increased accuracy, //--- (5) spread, (6) volume, (7) tick flags, (8) time, (9) time in milliseconds by index in the list    double            Bid(const uint index);    double            Ask(const uint index);    double            Last(const uint index);    double            VolumeReal(const uint index);    double            Spread(const uint index);    long              Volume(const uint index);    uint              Flags(const uint index);    datetime          Time(const uint index);   

**score 2:** //--- Return (1) Bid, (2) Ask, (3) Last, (4) volume with increased accuracy, //--- (5) spread, (6) volume, (7) tick flags by tick time in milliseconds    double            Bid(const ulong time_msc);    double            Ask(const ulong time_msc);    double            Last(const ulong time_msc);    double            VolumeReal(const ulong time_msc);    double            Spread(const ulong time_msc);    long              Volume(const ulong time_msc);    uint              Flags(const ulong time_msc);

**score 2:** //--- Return (1) Bid, (2) Ask, (3) Last, (4) volume with increased accuracy, //--- (5) spread, (6) volume and (7) tick flags by tick time    double            Bid(const datetime time);    double            Ask(const datetime time);    double            Last(const datetime time);    double            VolumeReal(const datetime time);    double            Spread(const datetime time);    long              Volume(const datetime time);    uint              Flags(const datetime time);

**score 2:** ============= Beginning of parameter list (Tick "EURUSD" 2021.01.06 14:25:32.156) ============= Last price update time in milliseconds: 2021.01.06 14:25:32.156 Last price update time: 2021.01.06 14:25:32 Volume for the current Last price: 0 Flags: 134 Changed data on the tick:  - Ask price change  - Bid price change ------ Bid price: 1.23494 Ask price: 1.23494 Last price: 0.00000 Volume for the current Last price with greater accuracy: 0.00 Spread: 0.00000 ------ Symbol: "EURUSD" ============= End of parameter list (Tick "EURUSD" 2021.01.06 14:

**score 2:** ============= Beginning of parameter list (Tick "EURUSD" 2021.01.07 12:51:40.632) ============= Last price update time in milliseconds: 2021.01.07 12:51:40.632 Last price update time: 2021.01.07 12:51:40 Volume for the current Last price: 0 Flags: 134 Changed data on the tick:  - Ask price change  - Bid price change ------ Bid price: 1.22452 Ask price: 1.22454 Last price: 0.00000 Volume for the current Last price with greater accuracy: 0.00 Spread: 0.00002 ------ Symbol: "EURUSD" ============= End of parameter list (Tick "EURUSD" 2021.01.07 12:

**score 1:** //--- Set standard sounds for trading objects of all used symbols    engine.SetSoundsStandart(); //--- Set the general flag of using sounds    engine.SetUseSounds(InpUseSounds); //--- Set the spread multiplier for symbol trading objects in the symbol collection    engine.SetSpreadMultiplier(InpSpreadMultiplier);

**score 1:** //--- Set controlled values for symbols    //--- Get the list of all collection symbols    CArrayObj *list=engine.GetListAllUsedSymbols();    if(list!=NULL && list.Total()!=0)      {       //--- In a loop by the list, set the necessary values for tracked symbol properties       //--- By default, the LONG_MAX value is set to all properties, which means "Do not track this property"        //--- It can be enabled or disabled (by setting the value less than LONG_MAX or vice versa - set the LONG_MAX value) at any time and anywhere in the program    

**score 1:** In this article, I will implement updating tick data in real time and prepare the symbol object class for working with Depth of Market (DOM itself is to be implemented in the next article).


## Tail
[Self-adapting algorithm (Part III): Abandoning optimization](https://www.mql5.com/en/articles/8807)

It is impossible to get a truly stable algorithm if we use optimization based on historical data to select parameters. A stable algorithm should be aware of what parameters are needed when working on any trading instrument at any time. It should not forecast or guess, it should know for sure.

metatrader.com: Your New Hub for Trading

A unified portal with global market news and analytics to help you trade smarter

Learn more](https://www.mql5.com/ff/go?link=https://www.metatrader.com%3Futm_source=www.mql5.com%26utm_medium=display%26utm_content=visit%26utm_campaign=visit.metatrader.com.426&a=nohacijjghimvcjzaekwvnuwufwnpswg&s=ee3b83e6d9917a3b0fdbb21e0b44c932faa82951112160b419f2890a2e1c30a8&uid=&ref=https://www.mql5.com/en/articles/8912&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=5127363835580802428)


---
# 8952: Prices in DoEasy library (part 61): Collection of symbol tick series
HEADS: # Prices in DoEasy library (part 61): Collection of symbol tick series | ### Contents | ### Concept | ### Class collection of tick data | ### Test | ### What's next?

## Intro
# Prices in DoEasy library (part 61): Collection of symbol tick series

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Examples](https://www.mql5.com/en/articles/mt5/examples) | 22 March 2021 at 04:28

7 064 [ 2](https://www.mql5.com/en/forum/365416 "Comments")

[Artyom Trishkin](https://www.mql5.com/en/users/artmedia70)

- [Concept](https://www.mql5.com/en/articles/8952#concept) - [Class collection of tick data](https://www.mql5.com/en/articles/8952#class_collection_of_tick_data) - [Test](https://www.mql5.com/en/articles/8952#test) - [What's next?](https://www.mql5.com/en/articles/8952#what_s_next)


## Key hits
**score 2:** ============= Beginning of parameter list (Tick "AUDUSD" 2021.01.19 10:06:53.387) ============= Last price update time in milliseconds: 2021.01.19 10:06:53.387 Last price update time: 2021.01.19 10:06:53 Volume for the current Last price: 0 Flags: 6 Changed data on the tick:  - Ask price change  - Bid price change ------ Bid price: 0.77252 Ask price: 0.77256 Last price: 0.00000 Volume for the current Last price with greater accuracy: 0.00 Spread: 0.00004 ------ Symbol: "AUDUSD" ============= End of parameter list (Tick "AUDUSD" 2021.01.19 10:06

**score 2:** ============= Beginning of parameter list (Tick "AUDUSD" 2021.01.18 11:51:48.662) ============= Last price update time in milliseconds: 2021.01.18 11:51:48.662 Last price update time: 2021.01.18 11:51:48 Volume for the current Last price: 0 Flags: 130 Changed data on the tick:  - Bid price change ------ Bid price: 0.76589 Ask price: 0.76593 Last price: 0.00000 Volume for the current Last price with greater accuracy: 0.00 Spread: 0.00004 ------ Symbol: "AUDUSD" ============= End of parameter list (Tick "AUDUSD" 2021.01.18 11:51:48.662) =========

**score 2:** ============= Beginning of parameter list (Tick "EURUSD" 2021.01.19 10:05:07.246) ============= Last price update time in milliseconds: 2021.01.19 10:05:07.246 Last price update time: 2021.01.19 10:05:07 Volume for the current Last price: 0 Flags: 6 Changed data on the tick:  - Ask price change  - Bid price change ------ Bid price: 1.21189 Ask price: 1.21189 Last price: 0.00000 Volume for the current Last price with greater accuracy: 0.00 Spread: 0.00000 ------ Symbol: "EURUSD" ============= End of parameter list (Tick "EURUSD" 2021.01.19 10:05

**score 2:** ============= Beginning of parameter list (Tick "EURUSD" 2021.01.18 14:57:53.847) ============= Last price update time in milliseconds: 2021.01.18 14:57:53.847 Last price update time: 2021.01.18 14:57:53 Volume for the current Last price: 0 Flags: 134 Changed data on the tick:  - Ask price change  - Bid price change ------ Bid price: 1.20536 Ask price: 1.20536 Last price: 0.00000 Volume for the current Last price with greater accuracy: 0.00 Spread: 0.00000 ------ Symbol: "EURUSD" ============= End of parameter list (Tick "EURUSD" 2021.01.18 14:

**score 2:** [](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F1171%3Futm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Dbest.vps%26utm_content%3Drent.vps%26utm_campaign%3D0622.MQL5.com.Internal&a=nwegcasiojnqcoyrdlgofmjtfardztwf&s=d64d6f3c87f2458cba81f6d7b6694dd9e89dd354d4abc1d0584e405285806c9f&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=adxwwdterodjejvqfxvdoxcpyzdwujoe&ssn=1788801914349032706&ssn_dr=0&ssn_sr=0&fv_date=1788801914&ref=https%3A%2F%2Fwww.mql5.com%2Fen%2F

**score 1:** If the number of tick data days is not set for at least one of the objects in the list, **res** stores false upon the loop completion. Thus, the method allows setting the number of days for all tick series in the collection and returns successful execution only if the number of days is set for each tick data object stored in the list.

**score 1:** If a tick series is not created for at least one of the objects in the list, **res** stores false upon the loop completion. Thus, the method allows creating tick series collections for all symbols and returns successful execution only if tick series are created for each tick data object stored in the list.

**score 1:** In this article, I will implement updating tick data in real time and prepare the symbol object class for working with Depth of Market (DOM itself is to be implemented in the next article).


## Tail
[Neural networks made easy (Part 11): A take on GPT](https://www.mql5.com/en/articles/9025)

Perhaps one of the most advanced models among currently existing language neural networks is GPT-3, the maximal variant of which contains 175 billion parameters. Of course, we are not going to create such a monster on our home PCs. However, we can view which architectural solutions can be used in our work and how we can benefit from them.

[Multilayer perceptron and backpropagation algorithm](https://www.mql5.com/en/articles/8908)

The popularity of these two methods grows, so a lot of libraries have been developed in Matlab, R, Python, C++ and others, which receive a training set as input and automatically create an appropriate network for the problem. Let us try to understand how the basic neural network type works (including single-neuron perceptron and multilayer perceptron). We will consider an exciting algorithm which is responsible for network training - gradient descent and backpropagation. Existing complex models are often based on such simple network models.

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F1171%3Futm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Dbest.vps%26utm_content%3Drent.vps%26utm_campaign%3D0622.MQL5.com.Internal&a=nwegcasiojnqcoyrdlgofmjtfardztwf&s=d64d6f3c87f2458cba81f6d7b6694dd9e89dd354d4abc1d0584e405285806c9f&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=adxwwdterodjejvqfxvdoxcpyzdwujoe&ssn=1788801914349032706&ssn_dr=0&ssn_sr=0&fv_date=1788801914&ref=https%3A%2F%2Fwww.mql5.com%2Fen%2F


---
# 1179: MQL5 Cookbook: Handling BookEvent
HEADS: # MQL5 Cookbook: Handling BookEvent | ### Introduction | ### 1. BookEvent | ### 2. Event Handler of BookEvent | ### 3. BookEvent Handling Template | ### 4. Depth of Market | ## | ### Conclusion

## Intro
[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Examples](https://www.mql5.com/en/articles/mt5/examples) | 22 October 2014 at 09:18

11 107 [ 26](https://www.mql5.com/en/forum/37110 "Comments")

[Denis Kirichenko](https://www.mql5.com/en/users/denkir)

As is well known, the [MetaTrader 5](https://www.metatrader5.com/ "https://www.metatrader5.com/") trading terminal is a multi-market platform, that facilitates trading on Forex, stock markets, Futures and Contracts for Difference. According to the [Freelance](https://www.mql5.com/en/job) section stats, the number of traders trading not only on Forex market is growing.

In this article I would like to introduce novice MQL5 programmers to the [BookEvent](https://www.mql5.com/en/docs/runtime/event_fire#bookevent) handling. This event is connected with Depth of Market—an instrument for trading stock assets and their derivatives. Forex traders, however, may find Depth of Market useful too. In ECN accounts, liquidity providers supply data on the orders, though only within their aggregator model. These accounts are becoming more popular.


## Key hits
**score 2:** For correct panel initialization, the exact Depth of Market or the number of levels has to be specified (the "DOM depth" parameter). This number differs from broker to broker.

**score 1:** As is well known, the [MetaTrader 5](https://www.metatrader5.com/ "https://www.metatrader5.com/") trading terminal is a multi-market platform, that facilitates trading on Forex, stock markets, Futures and Contracts for Difference. According to the [Freelance](https://www.mql5.com/en/job) section stats, the number of traders trading not only on Forex market is growing.

**score 1:** Depth of Market is an array of orders, which differ in direction (sell and buy), price and volume. Prices in Depth of Market are close to the market ones and therefore are considered as the best.

**score 1:** //--- get the book       if(MarketBookGet(_Symbol,last_bookArray))         {          //--- process book data          for(int idx=0;idx<ArraySize(last_bookArray);idx++)            {             MqlBookInfo curr_info=last_bookArray[idx];             //--- print             PrintFormat("Type: %s",EnumToString(curr_info.type));             PrintFormat("Price: %0."+IntegerToString(_Digits)+"f",curr_info.price);             PrintFormat("Volume: %d",curr_info.volume);            }         }      }   } ```

**score 1:** To do that, we are going to use the built-in function MarketBookGet(). It will return all the information about Depth of Market, namely the MqlBookInfo, array of structures, which contains Depth of Market records for the specified symbol. It should be noted, that this array will vary in size, depending on a broker.

**score 1:** The EA was launched for the [SBRF-12.14](http://www.moex.com/ru/contract.aspx?code=SBRF-12.14 "http://moex.com/ru/contract.aspx?code=SBRF-12.14") futures in a debug mode. The sequence of records in the Experts log will be as follows:

**score 1:** The source data in Depth of Market is the information that a trader analyses to work out a trading strategy. The simplest trading idea is that gathering and clustering orders with significant volumes at contiguous price levels create zones of support and resistance. In the following section, we shall create an indicator that will track changes in Depth of Market.

**score 1:** Let us create a short program that will be showing live Depth of Market data. At first we need to specify the data to be displayed. It will be a panel, with horizontal bars indicating the volume of the order. The size of the bars, however, will be of relative nature. Maximum volume of all current orders will be considered as 100%. Fig. 2 shows that the order at the price of 7507 Rub has the largest volume of 519 lots.


## Tail
[MQL5 Cookbook: Handling Custom Chart Events](https://www.mql5.com/en/articles/1163)

This article considers aspects of design and development of custom chart events system in the MQL5 environment. An example of an approach to the events classification can also be found here, as well as a program code for a class of events and a class of custom events handler.

metatrader.com: Your New Hub for Trading

A unified portal with global market news and analytics to help you trade smarter

Learn more](https://www.mql5.com/ff/go?link=https://www.metatrader.com%3Futm_source=www.mql5.com%26utm_medium=display%26utm_content=visit%26utm_campaign=visit.metatrader.com.426&a=nohacijjghimvcjzaekwvnuwufwnpswg&s=ee3b83e6d9917a3b0fdbb21e0b44c932faa82951112160b419f2890a2e1c30a8&uid=&ref=https://www.mql5.com/en/articles/1179&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=6360704604190702289)


---
# 1793: MQL5 Cookbook: Implementing Your Own Depth of Market
HEADS: # MQL5 Cookbook: Implementing Your Own Depth of Market | ### Table of Contents | ### Introduction | ### Chapter 1. Standard Depth of Market in MetaTrader 5 and methods of using it | ### Chapter 2. CMarketBook class for easy access and operation with Depth of Market | ### Chapter 3. Writing your own Depth of Market as a panel indicator | ### Chapter 4. Documentation for CMarketBook class | ### Conclusion

## Intro
# MQL5 Cookbook: Implementing Your Own Depth of Market

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Examples](https://www.mql5.com/en/articles/mt5/examples) | 9 October 2015 at 06:10

29 538 [ 44](https://www.mql5.com/en/forum/65168 "Comments")

[Vasiliy Sokolov](https://www.mql5.com/en/users/c-4)

- [Introduction](https://www.mql5.com/en/articles/1793#introduction) - [Chapter 1. Standard DOM in MetaTrader 5 and methods of using it](https://www.mql5.com/en/articles/1793#chapter_1_standard_depth_of_market_in_metatrader_5)   - [1.1. Standard Depth of Market in MetaTrader 5](https://www.mql5.com/en/articles/1793#c1_1)   - [1.2. Event model for working with Depth of Market](https://www.mql5.com/en/articles/1793#c1_2)   - [1.3. Receiving second level quotes with MarketBookGet functions and MqlBookInfo structure](https://www.mql5.com/en/articles/1793#c1_3) - [Chapter 2. CMarketBook class for easy access and operation with Depth of Market](https://www.mql5.com/en/articles/1793#chapter_2_cmark


## Key hits
**score 3:** - Buy and Sell limit orders, their price levels and volume (standard form of classical DOM); - current spread level and price levels occupied by limit orders (advanced mode); - tick chart and visualized Bid, Ask and last trade volumes; - total level of Buy and Sell orders (displayed as two lines at the tick chart's top and bottom, respectively).

**score 2:** - [Introduction](https://www.mql5.com/en/articles/1793#introduction) - [Chapter 1. Standard DOM in MetaTrader 5 and methods of using it](https://www.mql5.com/en/articles/1793#chapter_1_standard_depth_of_market_in_metatrader_5)   - [1.1. Standard Depth of Market in MetaTrader 5](https://www.mql5.com/en/articles/1793#c1_1)   - [1.2. Event model for working with Depth of Market](https://www.mql5.com/en/articles/1793#c1_2)   - [1.3. Receiving second level quotes with MarketBookGet functions and MqlBookInfo structure](https://www.mql5.com/en/article

**score 2:** Now the method of working with Depth of Market should be clear to us. MarketBookGet function returns an array of MqlBookInfo structures. Array index indicates the line of price table, and the index structure contains information about volume, price and order type. Knowing this, we will try to get access to the first DOM order, and for this reason we will slightly modify the OnBookEvent function of our Expert Advisor from the previous example:

**score 1:** MQL5 language is constantly evolving and offering more opportunities for operation with exchange information every year. One of such exchange data types is information about Depth of Market. It is a special table showing price levels and volumes of limit orders. MetaTrader 5 has a built-in Depth of Market for displaying limit orders, but it is not always sufficient. First of all, your Expert Advisor has to be given a simple and convenient access to Depth of Market. Certainly, MQL5 language has few special features for working with such informat

**score 1:** However, all intermediate calculations can be avoided. All you have to do is to write a special class for working with Depth of Market. All complex calculations will be carried out within Depth of Market, and the class itself will provide convenient ways for operation with DOM prices and levels. This class will enable an easy creation of the efficient panel in a form of an indicator, which will be promptly reflecting the current state of prices in Depth of Market:

**score 1:** This article demonstrates users how to utilize Depth of Market (DOM) programmatically and describes the operation principle of **CMarketBook** class, that can expand the Standard Library of MQL5 classes and offer convenient methods of using DOM.

**score 1:** The list provided confirms that Depth of Market features are more than impressive. Let's find out how to operate with data by getting access to it programmatically. First of all, you need to get an idea about how is Depth of Market established ​​and what is the key to its data organization. For more information read the article "[Principles of Exchange Pricing through the Example of Moscow Exchange's Derivatives Market](https://www.mql5.com/en/articles/1284)" in chapter "[13. Matching Sellers and Buyers. Exchange Depth of Market](https://www.mq

**score 1:** Any event occurring on the market, such as the arrival of a new tick or the execution of a trading transaction, can be processed by calling the corresponding function associated with it. For example, with the arrival of a new tick in MQL5, a special OnTick() event handler function is called. Resizing the chart or its position calls the OnChartEvent() function. This event model also applies to Depth of Market changes. For example, if someone places Sell or Buy limit orders in Depth of Market, its status will change and call a special OnBookEvent


## Tail
[Handling ZIP Archives in Pure MQL5](https://www.mql5.com/en/articles/1971)

The MQL5 language keeps evolving, and its new features for working with data are constantly being added. Due to innovation it has recently become possible to operate with ZIP archives using regular MQL5 tools without getting third party DLL libraries involved. This article focuses on how this is done and provides the CZip class, which is a universal tool for reading, creating and modifying ZIP archives, as an example.

[Drawing Resistance and Support Levels Using MQL5](https://www.mql5.com/en/articles/1742)

This article describes a method of finding four extremum points for drawing support and resistance levels based on them. In order to find extremums on a chart of a currency pair, RSI indicator is used. To give an example, we have provided an indicator code that displays support and resistance levels.

Learn to create your own robots Read our book "MQL5 Programming for Traders" Begin](https://www.mql5.com/ff/go?link=https://www.mql5.com/en/book%3Futm_source=www.mql5.com%26utm_medium=display%26utm_term=read.algobook%26utm_content=visit.page%26utm_campaign=algobook.promo.04.2024&a=rsxjstxkzbrlgjjrxaglpezpvrjflnvw&s=7224440013c3dbc50ba9cc078cd015fabca36df446b8e75028d6b30234663872&uid=&ref=https://www.mql5.com/en/articles/1793&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=6346231071209321357)


---
# 3336: Implementing a Scalping Market Depth Using the CGraphic Library
HEADS: # Implementing a Scalping Market Depth Using the CGraphic Library | ### Table of Contents | ### Introduction | ### Changes made since the release of previous version | ### Overview of the CPanel graphics library | ### Synchronizing the tick stream with the order book | ### CGraphic Basics | ### Integration of CGraphic with the CPanel library | ### Installation. Performance in dynamics. Comparative characteristics of Market Depth features | ### Conclusion

## Intro
# Implementing a Scalping Market Depth Using the CGraphic Library

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Examples](https://www.mql5.com/en/articles/mt5/examples) | 26 October 2017 at 06:30

31 266 [ 46](https://www.mql5.com/en/forum/218217 "Comments")

[Vasiliy Sokolov](https://www.mql5.com/en/users/c-4)

- [Introduction](https://www.mql5.com/en/articles/3336#introduction) - [Changes made since the release of previous version](https://www.mql5.com/en/articles/3336#changes_made_since_the_release_of_previous_version) - [Overview of the CPanel graphics library](https://www.mql5.com/en/articles/3336#overview_of_the_cpanel_graphics_library) - [Synchronizing the tick stream with the order book](https://www.mql5.com/en/articles/3336#synchronizing_the_tick_stream_with_the_order_book) - [CGraphic Basics](https://www.mql5.com/en/articles/3336#cgraphic_basics) - [Integration of CGraphic with the CPanel library](https://www.mql5.com/en/articles/3336#integration_of_cgraphic_with_the_cpanel_library) - [Ins


## Key hits
**score 1:** Now, during program execution, CLabel which is a pointer to the CElCahrt element is dynamically created. After creation and appropriate comfiguration, it is added to the Form. Now there is no need to display it using a separate Show command. Instead, it is enough to run the Show command for the Fon element, which is the main form of our app. Due to specifics, the command is executed for all sub-elements, including Label.

**score 1:** | The standard MetaTrader 5 Depth of Market | The Market Depth developed in this article | | --- | --- | | Last, Ask and Bid are not interrelated. The Last price can be at levels different from Ask and Bid. | Last, Ask, Bid are synchronized. Last price is always at the level of Ask or Bid. | | Last prices are shown as circles of different diameters which are directly proportional to the deal volume. A circle with the maximum diameter corresponds to a deal with the maximum volume performed for the last N ticks, where N is the period of the movin

**score 0:** - [Introduction](https://www.mql5.com/en/articles/3336#introduction) - [Changes made since the release of previous version](https://www.mql5.com/en/articles/3336#changes_made_since_the_release_of_previous_version) - [Overview of the CPanel graphics library](https://www.mql5.com/en/articles/3336#overview_of_the_cpanel_graphics_library) - [Synchronizing the tick stream with the order book](https://www.mql5.com/en/articles/3336#synchronizing_the_tick_stream_with_the_order_book) - [CGraphic Basics](https://www.mql5.com/en/articles/3336#cgraphic_bas

**score 0:** The previous library version consisted of two major modules: the **CMarketBook** class for working with the Market Depth and a graphical panel that rendered it. The code has been changed and improved greatly. A number of bugs have been fixed, while the graphics part of the Market Depth now has its own **CPanel** graphics library which is simple and lightweight.

**score 0:** After publishing the article "[MQL5 Cookbook: Implementing Your Own Depth of Market](https://www.mql5.com/en/articles/1793)", I used CMarketBook a lot in practice and found a number of errors in the code. I gradually modified the interface. Here are all changes and updates:

**score 0:** 1. The original graphics in the Market Depth window were very minimalistic. Order book table cells were displayed using a few elementary classes. After a while additional functionality was implemented in these classes, and their simplicity and lightness proved to be very convenient when designing other types of panels. As a results, the set of classes emerged into a separate independent project - the CPanel library. It is located in the Include folder. 2. The appearance of the Market Depth has also been improved. For example, a small triangle h

**score 0:** Example: let us draw a panel, as in figure 3. We need two elements: a background with a frame and a text with a frame. Both of them are instances of the same CElChart class. But two different graphical primitives are used in them: OBJ\_RECTANGLE\_LABEL and BJ\_BUTTON. Here is the resulting code:

**score 0:** The order book is a dynamic structure, whose values may change dozens of times per second on volatile markets. To access the current state of the order book, you must handle a special BookEvent in the corresponding event handler, the OnBookEvent function. When the order book changes, the terminal calls OnBookEvent, indicating the symbol corresponding to changes. In the previous article, we developed the CMarketBook class that provided a convenient access to the current order book state. The current state of the order book could be obtained in t


## Tail
In this article, we consider yet another custom trading strategy optimization criterion based on the balance graph analysis. The linear regression is calculated using the function from the ALGLIB library.

[Cross-Platform Expert Advisor: The CExpertAdvisor and CExpertAdvisors Classes](https://www.mql5.com/en/articles/3622)

This article deals primarily with the classes CExpertAdvisor and CExpertAdvisors, which serve as the container for all the other components described in this article-series regarding cross-platform expert advisors.

[Best articles and CodeBase updates in MQL5.community channels Follow us to ensure you never miss out on important updates

](https://www.mql5.com/ff/go?link=https://www.mql5.com/en/forum/455636%3Futm_source=www.mql5.com%26utm_medium=display%26utm_content=follow.channel%26utm_campaign=AAA380.mql5.socials&a=dgazvhktsxqakdvarucjbvmvzenwlyje&s=98a038fe082e458df8c4a1d8e116e3a6646fd5517f06e48b2356b7ee005817d6&uid=&ref=https://www.mql5.com/en/articles/3336&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=6414552400182013658)


---
# 18821: Analyzing the Hourly Movement of Trading Symbols and Their Spreads in MetaTrader 5
HEADS: # Analyzing the Hourly Movement of Trading Symbols and Their Spreads in MetaTrader 5 | ### Introduction | ### | ### **Choosing the right time to trade** | ### | ### Features of the trading symbols movement, **interpretation of ISI ProSpread SMA readings** | ### | ### **The magic of repetition: The phenomenon of intraday seasonality** | ### | ### **Detailed description of indicator formulas** | ### **Dashboard - How to read data** | ### | ### Instructions for using the indicator | ###

## Intro
# Analyzing the Hourly Movement of Trading Symbols and Their Spreads in MetaTrader 5

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Trading](https://www.mql5.com/en/articles/mt5/trading) | 14 July 2026 at 09:20

2 242 [ 2](https://www.mql5.com/en/forum/512730 "Comments")

[Roman Shiredchenko](https://www.mql5.com/en/users/r0man)

Imagine an ocean. Its waves appear chaotic and unpredictable to the casual observer. But an experienced sailor knows about tides - powerful, rhythmic and predictable forces that move the entire mass of water. These forces are subject to the laws of celestial mechanics and can be calculated with high accuracy.


## Key hits
**score 3:** The relative disadvantages of the session include low volatility of a few tens of points, which determines small profits for traders and forces brokers to set high spreads. If the price corridor is broken, this trend continues in subsequent trades.

**score 2:** | Financial center | Session "character" | Key instruments | | --- | --- | --- | | Sydney/Wellington | Calm, often sets the direction for the day | AUD, NZD, AUDNZD, AUDUSD | | Tokyo/Asia | Can enhance or correct movement | JPY, AUD, NZD, USDJPY | | London/Europe | The most volatile session, sets the main volume | EUR, GBP, CHF, EURUSD, GBPUSD | | New York/America | High volatility, reacts to news | USD    USD, CAD, USDCAD, USD pairs |

**score 2:** The European region has the largest volume of currency trades: at the opening of the London market, its share amounts to approximately 30% of all transactions per day. The market operates around the clock, but takes breaks on weekends and holidays when activity decreases. During such periods, there is a high probability of a sharp short-term change in the exchange rate due to the execution of client requests by one or more large banks in another region. The main thing is to choose the most convenient and profitable time for trading.

**score 2:** **Features of trading sessions**   For market participants, it is important to understand not only the start and end times of trading, but also their distinctive features. Each region has developed its own style and rules for conducting trades, transaction volumes, and distinctive strategies that distinguish them from other exchanges. Each session relies on its own currency pairs and reacts more sharply to external economic factors in its geographic zone than to events further afield. Common to all are the smooth movement of currency prices at 

**score 2:** American session   The American trading session is characterized by increased aggressiveness and unpredictability. The hottest time is considered to be the period of overlapping European and American trades. The latter open at 4:00 p.m. in New York and close at 1:00 a.m. in Chicago. The release of morning US statistics coincides with the release of afternoon reports in Europe, after which trading volumes increase and the market becomes saturated with liquidity.

**score 2:** Pacific session   Session overlap hours in this region are so quiet that some traders do not even consider Pacific trading to be a full session. Its operating hours are approximately from 12:00 a.m. to 9:00 a.m., and its main distinguishing features are small volumes and low volatility.

**score 2:** - selecting trading hours (e.g. London session only), - depth of analysis (number of history days), - setting up spread coefficients, - select a timeframe for analysis.

**score 2:** The problem is that it is almost impossible to see these patterns with the naked eye on a chart. They are drowned in the noise of random fluctuations. It is like trying to hear a melody by listening to just one note in a symphony. What is needed is an instrument that can "listen" to the entire symphony and identify the repeating harmonies within it.


## Tail
This article extends single-candlestick analysis to ordered double-candlestick patterns using an MQL5 script. The script encodes candles into symbols, extracts every consecutive two-symbol sequence (treating Aa and aA as different), counts occurrences and percentages, and writes sorted frequency tables to a text file. Readers can quickly identify the most recurrent transitions by symbol, timeframe, and lookback for further statistical testing.

[Measuring What Matters (Part 2): Building the Covariance Matrix: Eigenvalue Decomposition and Risk Factor Analysis in MQL5](https://www.mql5.com/en/articles/23314)

In Part 2, we introduce a reusable CCovarianceMatrix class that computes and stores a covariance matrix from raw return series using MQL5's native Cov() method. We verify symmetry, print a labeled matrix grid, and call Eig() to obtain eigenvalues and eigenvectors. Readers see how symbols co-move and which factors drive variance, enabling clearer portfolio diagnostics and reuse in scripts or EAs.

Trade with no restrictions from any mobile device, OS and web browser

Learn more](https://www.mql5.com/ff/go?link=https://trade.metatrader5.com/&a=fkjlpstbxdmrrwpblfatcsdjyrxbizyj&s=f462f051eb7aaec36d6b31792d312d60d3f5a50c83b12d0d66e85d5d61bd941b&uid=&ref=https://www.mql5.com/en/articles/18821&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=5124643278741451873)


---
# 20371: Formulating Dynamic Multi-Pair EA (Part 6): Adaptive Spread Sensitivity for High-Frequency Symbol Switching
HEADS: # Formulating Dynamic Multi-Pair EA (Part 6): Adaptive Spread Sensitivity for High-Frequency Symbol Switching | ### Introduction | ### System Overview and Strategic Approach | ### | ### Getting Started | ### **Back Test Results** | ### | ### Conclusion

## Intro
# Formulating Dynamic Multi-Pair EA (Part 6): Adaptive Spread Sensitivity for High-Frequency Symbol Switching

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Examples](https://www.mql5.com/en/articles/mt5/examples) | 30 January 2026 at 05:59

3 574 [ 0](https://www.mql5.com/en/forum/504437 "Comments")

[Hlomohang John Borotho](https://www.mql5.com/en/users/johnhlomohang)

1. [Introduction](https://www.mql5.com/en/articles/20371#introduction) 2. [System Overview and Strategic Approach](https://www.mql5.com/en/articles/20371#system_overview_and_strategic_approach) 3. [Getting Started](https://www.mql5.com/en/articles/20371#getting_started) 4. [Backtest Results](https://www.mql5.com/en/articles/20371#back_test_results) 5. [Conclusion](https://www.mql5.com/en/articles/20371#conclusion)


## Key hits
**score 3:** The OnInit() function handles the full startup preparation of the Expert Advisor by configuring symbols, internal data structures, and execution settings before trading begins. It starts by parsing the user-defined symbol list and validating that at least one tradable symbol is available, safely terminating initialization if none are found. The function then allocates and initializes the spreadData structure for each symbol, setting default values for spread metrics, trade state, statistics, and visual status indicators while also subscribing e

**score 2:** In  contrast, Part 6 shifts the focus away from specific trading entry and exit styles and instead zeroes in on the execution environment itself—especially the cost of trading as expressed through spreads. In Part 6, we now introduce a module that continuously monitors and adapts to real-time spread conditions across all symbols, using dynamic sensitivity thresholds to determine which symbols are currently optimal to trade. This high-frequency symbol switching based on adaptive spread evaluation complements the broader multi-pair architecture b

**score 2:** The Adaptive Spread Sensitivity EA is a sophisticated multi-symbol trading system designed to optimize trade execution dynamically  across multiple financial instruments. At its core, the system continuously monitors real-time spreads for all configured symbols, ranking them based on cost-efficiency metrics to prioritize trading on instruments with the most favorable execution conditions.

**score 2:** Getting started, we establish a flexible configuration layer for our dynamic multi-pair Expert Advisor by grouping all user-defined inputs in a clean and modular way. We begin with the general trade control, such as the list of symbols to monitor, risk per trade, and a magic number for position tracking. From there, we introduce a dedicated Spread Sensitivity section, which is the core of the EA’s execution logic. These inputs define absolute and adaptive spread limits, ATR-normalized spread thresholds, temporary symbol disabling, and symbol ra

**score 2:** Moving further, the code defines strategy-level inputs and supporting infrastructure that operate only after a symbol has passed the spread filter. The trading settings configure indicator parameters (EMA, RSI), risk boundaries (SL/TP, cooldowns, maximum positions), and optional ATR-based dynamic exits, enabling controlled and consistent trade execution. Below the inputs, global variables and the SpreadData structure form the EA’s internal state engine, tracking real-time spread metrics, symbol status, activity flags, trade statistics, and dash

**score 2:** The OnTick() function, on the other hand, defines the EA’s real-time operational flow and is designed for efficiency in a multi-symbol environment. Instead of processing all symbols on every tick, it cycles through one symbol per tick using a modulo counter, reducing CPU load and avoiding execution bottlenecks. For each selected symbol, the EA updates spread data, verifies trade eligibility, enforces cooldown constraints, and then executes the trading logic if all conditions are met. Dashboard updates are throttled to occur periodically rather 

**score 2:** The EvaluateTradeability() function then applies a layered decision process to determine whether each symbol is eligible for trading. It first enforces cooldown timeouts for previously disabled symbols, preventing rapid re-entry during unstable conditions. Next, it checks absolute spread limits and adaptive ATR-normalized thresholds, automatically disabling symbols that become too costly to trade and logging these events to the dashboard for transparency. When all spread conditions are satisfied, the symbol is marked tradeable and visually flag

**score 2:** Here we introduce a spread-efficiency ranking engine that determines which symbols are allowed to participate in trading at any given time. In RankSymbolsBySpread(), each symbol is assigned a composite spread score based on two execution-quality factors: the absolute spread and the spread-to-ATR ratio. Both components are inverted so that lower costs produce higher scores, then combined using weighted importance to emphasize raw spread while still accounting for volatility context. Once scores are calculated, the symbols are sorted in descendin


## Tail
Breadth First Search (BFS) uses level-order traversal to model market structure as a directed graph of price swings evolving through time. By analyzing historical bars or sessions layer by layer, BFS prioritizes recent price behavior while still respecting deeper market memory.

[Neural Networks in Trading: Hybrid Graph Sequence Models (Final Part)](https://www.mql5.com/en/articles/17310)

We continue exploring hybrid graph sequence models (GSM++), which integrate the advantages of different architectures, providing high analysis accuracy and efficient distribution of computing resources. These models effectively identify hidden patterns, reducing the impact of market noise and improving forecasting quality.

Log in with your mql5.com account to access trading insights, expert analytics, and news

Learn more](https://www.mql5.com/ff/go?link=https://www.metatrader.com%3Futm_source=www.mql5.com%26utm_medium=display%26utm_content=visit%26utm_campaign=visit.metatrader.com.426&a=fxfabzblydlbgbldhjsghkklqwkncbus&s=0e82b3bc88c853af98f8ff29a16d2a0fadf122814c10021b0538fb394951f7b4&uid=&ref=https://www.mql5.com/en/articles/20371&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=5122477756230799725)


---
# 22998: Measuring broker execution quality in MQL5: Why your live account doesn't match the backtest
HEADS: # Measuring broker execution quality in MQL5: Why your live account doesn't match the backtest | ### Introduction | ### What execution quality really is | ### MetaTrader 5 execution modes and why they matter | ### The approach: a diagnostic, not a filter | ### How to use it | ### A word of caution: what you are really measuring | ### Extending the tool | ### Limitations | ### Conclusion

## Intro
# Measuring broker execution quality in MQL5: Why your live account doesn't match the backtest

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Tester](https://www.mql5.com/en/articles/mt5/strategy_tester) | 11 August 2026 at 06:49

1 880 [ 0](https://www.mql5.com/en/forum/514346 "Comments")

[Walter Marcelo Rando](https://www.mql5.com/en/users/pipstats)

If you code in MQL5, you have probably lived this: the Strategy Tester draws a beautiful, almost straight equity curve, and when you put the same Expert Advisor (EA) on a real account, the result is very different. I have hit that wall more than once. My first instinct used to be to blame the strategy — but very often the strategy is fine. What changed is the *execution quality*.


## Key hits
**score 5:** 1. *Slippage.* The difference between the price you expected and the price your order was actually filled at. If you wanted to buy at the ask and you were filled higher, that excess is slippage against you. Same when you sell below the bid. I measure it in points (the symbol's smallest unit) and, by convention in this tool, *positive slippage means a worse fill*. 2. *Observed spread.* The bid-ask spread at the moment of measurement, in points. A quick note on terminology: in market-microstructure literature "effective spread" has a precise mean

**score 4:** 1. *Instant Execution:* the broker shows you a price and you ask to be filled at that exact price. If the price changed, the server answers with a *requote*. This is where you will see the most requotes and rejections. 2. *Market Execution:* you send the order and the broker fills it at the best available price. There is typically no requote at the request stage, but you can still get slippage — the fill price is whatever liquidity is there at that instant, so a thin book can move it against you. 3. *Exchange Execution:* the order goes to a cen

**score 3:** A few things worth highlighting. The latency we measure (ms1 - ms0) is the time between calling trade.Buy/Sell and getting the result back — that is *client-perceived per-leg latency* (the entry and the exit legs are timed separately), not pure server execution time, but it is exactly the friction you feel, and it often explains slippage. We capture the position ticket right after opening and close that ticket; because ProbeAllowed already guaranteed nothing else was on the symbol, the probe leg is unambiguous. IsRequote is a one-line helper (r

**score 3:** An average hides the tail, and the tail is where execution hurts: an average entry slippage of 5 points with a 95th percentile of 40 points is a very different account from a steady 5/6. So instead of keeping running sums, we keep the samples and compute the mean, the median and the p95 on demand.

**score 2:** # Measuring broker execution quality in MQL5: Why your live account doesn't match the backtest

**score 2:** The Strategy Tester lives in an ideal world: it fills orders at (or near) the requested price, with a modeled spread and—unless configured otherwise—no delays or rejections. A live account is a different animal: the price moves between the moment you send the order and the moment it is filled, the spread widens exactly when it matters, and every now and then you get a requote, a price change, or a rejection. That friction has names: *slippage*, *spread* and *requotes*.

**score 2:** This tool does not measure the broker in isolation. It measures the entire execution path (terminal/PC/VPS, network, broker gateway, venue liquidity), so poor results can come from any link. There is a dedicated section on this later; keep it in mind throughout.

**score 2:** Not all brokers fill the same way, and the execution type decides which friction you will see. MetaTrader 5 handles three main modes:


## Tail
[Generating a Per-Symbol Trade Analytics PDF Report from MQL5](https://www.mql5.com/en/articles/23502)

This article shows how to generate a dependency-free, single-page PDF report in MQL5 using only string assembly and the FILE\_BIN API. The script computes per-symbol trade statistics, then renders a labeled table and an equity curve with explicit PDF color and drawing operators. Statistics are calculated in a standalone module, so every value can be verified against synthetic data without relying on a live trading account.

[A Reinforcement Learning System for Algorithmic Trading in MQL5](https://www.mql5.com/en/articles/20122)

The article describes the development of a multi-agent machine learning system for algorithmic trading on MetaTrader 5 based on reinforcement learning. The system has a three-tier architecture: memory neurons store experience, agents make independent decisions, and the collective mind combines them through weighted voting. The system is continuously improved through Q-learning, pruning of ineffective neurons, and evolutionary reduction of exploration.

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F618%3Futm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Dsignal.advantage%26utm_content%3Dsubscribe.signal%26utm_campaign%3D0622.MQL5.com.Internal&a=bewozmaxwejekdopjicjtsbzmjgfjyvt&s=e49ac7e84b713650e3af82ec3c6b4d02fdf06617c5821011b1e499af5edd01f4&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=jwkrbgfusepyhpcwhclybjcvyfchixcd&ssn=1788777649095509929&ssn_dr=0&ssn_sr=0&fv_date=1788777649&ref=https%3A%2F%2Fwww.m


---
# 23299: Execution Cost and Slippage Sensitivity Analyzer
HEADS: # Execution Cost and Slippage Sensitivity Analyzer | ### Introduction | ### Why a Backtest Understates Costs | ### What Cost Sensitivity Measures | ### Architecture of the Execution Cost Sensitivity Analyzer | ### The Main Script: Putting It All Together | ### Exporting Your Own Trades | ### Interpreting the Results | ### Applicability and Limitations | ### Conclusion

## Intro
# Execution Cost and Slippage Sensitivity Analyzer

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Statistics and analysis](https://www.mql5.com/en/articles/mt5/statistics) | 23 July 2026 at 07:11

1 683 [ 0](https://www.mql5.com/en/forum/513281 "Comments")

[Cristian David Castillo Arrieta](https://www.mql5.com/en/users/thiabot)

I once had a strategy that looked ready to trade. Over a two-year backtest, it showed a net profit above two thousand units, a profit factor near 1.6, and a win rate of 61%. The equity curve climbed in a calm, believable line. I funded a small account, switched it on, and watched the live result drift below the backtest week after week. Nothing was broken in the logic. The gap was cost. Each trade paid slightly more spread and slippage, plus a commission the backtest had treated as an afterthought. Those small amounts added up and consumed most of the edge.


## Key hits
**score 5:** //--- Recommendations: each one is driven by a specific weakness    Print("\n--- RECOMMENDATIONS ---");    if(r.cushion < 2.0)       PrintFormat("!! The edge disappears below 2x the assumed cost (cushion %.2fx). Treat live results with great caution.", r.cushion);    else if(r.cushion < 3.0)       PrintFormat(">> The cushion is only %.2fx the assumed cost. A modest rise in spread or slippage materially cuts the result; build in margin before trading live.", r.cushion);    if(r.profitFactor > 0.0 && r.pfAtCost > 0.0 && r.pfAtCost < 1.4)       Pr

**score 4:** A backtest charges the costs you tell it to charge. The spread is often a fixed, optimistic value; commission may be left at zero; and slippage, the difference between the price you wanted and the price you got, is usually absent because the tester fills you at the modeled price. Live trading is not so kind. Spreads widen around news and at the session close. Fast markets fill market orders a few points away from the screen. A broker that looked cheap on a quiet pair can be expensive on the one you actually trade.

**score 3:** This article asks one question: how much execution cost can a strategy absorb before its edge disappears? Net profit and profit factor are measured at the cost the backtest happened to assume. They do not tell you how close that result sits to the cost line or how much the spread would have to widen before a winning system turns into a losing one. A strategy with a wide margin over costs is one you can trade through a noisy broker and a fast market. A strategy that only wins because the test was cheap will not survive contact with a real accoun

**score 3:** The fixed part stands for a per-ticket charge such as a minimum commission. The per-lot part stands for the spread, the variable commission, and the slippage, all of which grow with position size. This is a deliberately linear approximation. In reality, spread and slippage also depend on the instrument and on volatility, not on volume alone, but a linear model keeps the estimate transparent and configurable. With the default of 12 units per lot and no fixed part, a 0.50-lot deal pays 6 units, and a 0.10-lot deal pays 1.2 units.

**score 3:** The recommendations follow from those numbers. The cushion is below 3.0, so the tool warns that a modest rise in spread or slippage materially cuts the result. The profit factor at cost is below 1.4, so it flags that the edge is thin once realistic costs are paid. And because realistic costs erase 40% of the net profit, it says so plainly. The reading is clear: this strategy is not worthless, but it is cost-sensitive, and it needs a margin of safety, a cheaper broker, or fewer and larger trades before it goes live.

**score 2:** # Execution Cost and Slippage Sensitivity Analyzer

**score 2:** I once had a strategy that looked ready to trade. Over a two-year backtest, it showed a net profit above two thousand units, a profit factor near 1.6, and a win rate of 61%. The equity curve climbed in a calm, believable line. I funded a small account, switched it on, and watched the live result drift below the backtest week after week. Nothing was broken in the logic. The gap was cost. Each trade paid slightly more spread and slippage, plus a commission the backtest had treated as an afterthought. Those small amounts added up and consumed most

**score 2:** Before writing code, we need to define the measurements the analyzer reports. The tool models the execution cost of a single closing deal as a fixed part plus a part that scales with the deal volume:


## Tail
A structured MQL5 implementation of a multi‑symbol trading panel with clear separation of concerns: symbol handling, trading logic, and GUI. Integrated into an Expert Advisor, it validates symbols, exposes centralized controls for opening and positions managing across symbols, and applies SL/TP changes. Real‑time account and portfolio metrics help streamline routine operations from a single chart.

[A Symbol Metadata and Trading Hours Cache in MQL5: Eliminating Redundant SymbolInfo Calls in Multi-Symbol EAs](https://www.mql5.com/en/articles/23388)

This article presents CSymbolMetaCache, an MQL5 layer that preloads contract specifications and trading-session schedules for monitored symbols at EA startup and then serves typed getters from memory. It explains which properties are safe to cache versus dynamic ones, including the semi-dynamic tick value on cross-currency pairs, and implements an in-memory IsMarketOpen() evaluator. A benchmark quantifies latency reduction across a set of twenty symbols.

Use Git-powered tools in MetaEditor for structured, reliable development

Learn more](https://www.mql5.com/ff/go?link=https://forge.mql5.io%3Futm_source=www.mql5.com%26utm_medium=display%26utm_content=visit%26utm_campaign=visit.mql5.226&a=oygnrjjxveoqzycxkjkckcgtshfunvdu&s=1e458fdafe5955c82ea32b518845e77efbe1196295936353793e9e23a750f4d6&uid=&ref=https://www.mql5.com/en/articles/23299&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=6419732843705533665)


---
# 23755: A Reusable Breakeven Manager in MQL5 with Spread Compensation
HEADS: # A Reusable Breakeven Manager in MQL5 with Spread Compensation | ### Introduction | ### Section 1: The Breakeven Record | ### Section 2: Sampling the Live Spread | ### | ### Section 3: Computing the Breakeven Level | ### | ### Section 4: Executing the Modification | ### | ### Section 5: The Breakeven Manager | ### | ### Section 6: BreakevenEA.mq5 — Integration Demo | ### | ### Section 7: Verification, TestBreakevenManager.mq5

## Intro
# A Reusable Breakeven Manager in MQL5 with Spread Compensation

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Trading](https://www.mql5.com/en/articles/mt5/trading) | 1 September 2026 at 09:13

677 [ 0](https://www.mql5.com/en/forum/515465 "Comments")

[Ushana Kevin Iorkumbul](https://www.mql5.com/en/users/iorkumbulushana)

You may have seen a familiar failure mode: an Expert Advisor moves a stop-loss "to breakeven" at the entry price and then, during a short spread spike (news or thin liquidity), the position is closed on that stop even though the market is barely retraced. The root causes are twofold and engineering-focused: (1) a breakeven check that ignores the fact that a trade is opened at ask but closed at bid—so the spread at modification time must be part of the breakeven level—and (2) a mistaken pip/point conversion on 3- and 5-digit symbols, which makes activation thresholds and buffers scale incorrectly. You need a small, testable module that (a) measures profit in real pips, (b) samples the live sp


## Key hits
**score 2:** ComputeLevel() implements the long formula open\_price + spread + buffer\_pips \* pip\_size, and its mirror for a short: open\_price - spread - buffer\_pips \* pip\_size. Adding the spread rather than ignoring it is the entire point of this article. It is what makes the resulting level genuinely break-even from the broker's perspective, since the position's true cost already includes the spread paid at entry.

**score 1:** # A Reusable Breakeven Manager in MQL5 with Spread Compensation

**score 1:** You may have seen a familiar failure mode: an Expert Advisor moves a stop-loss "to breakeven" at the entry price and then, during a short spread spike (news or thin liquidity), the position is closed on that stop even though the market is barely retraced. The root causes are twofold and engineering-focused: (1) a breakeven check that ignores the fact that a trade is opened at ask but closed at bid—so the spread at modification time must be part of the breakeven level—and (2) a mistaken pip/point conversion on 3- and 5-digit symbols, which makes

**score 1:** Architecture of the breakeven manager. The Expert Advisor drives CBreakevenManager through Register() and OnTick(). On each tick, the manager reads the live spread, computes the breakeven level, and sends the modification, in that order, through OrderSend() with a TRADE\_ACTION\_SLTP request.

**score 1:** The spread has to be read at the exact moment the stop loss is about to be modified, not stored once at registration and reused. A position can sit registered for hours before it reaches its activation threshold. If the spread were captured once when Register() was called, the value used in the breakeven formula could be completely disconnected from the actual market condition by the time the position is finally profitable enough to move. CSpreadSampler exists purely to make that live read happen consistently.

**score 1:** //+------------------------------------------------------------------+ //| CSpreadSampler                                                   | //+------------------------------------------------------------------+ class CSpreadSampler   { public:                      CSpreadSampler(void);                     ~CSpreadSampler(void);

**score 1:** double            GetCurrentSpread(const string symbol) const;    double            GetCurrentSpreadPips(const string symbol) const;   };

**score 1:** //+------------------------------------------------------------------+ //| Constructor                                                      | //+------------------------------------------------------------------+ CSpreadSampler::CSpreadSampler(void)   {   }


## Tail
[Neural Networks in Trading: An End-to-End Multivariate Time Series Forecasting Model (GinAR)](https://www.mql5.com/en/articles/18854)

We invite you to explore an innovative approach to forecasting time series with missing data using the GinAR framework. The article demonstrates the implementation of key components using OpenCL, which ensures high performance. In our next publication, we will take a detailed look at how to integrate these solutions into MQL5. This will help understand how to apply the method in practice in trading.

[Motifs and Discords: Building a Matrix Profile from Scratch](https://www.mql5.com/en/articles/23754)

We build the Matrix Profile for MQL5 from the ground up and keep it numerically stable on real prices. The library includes rolling statistics, a radix-2 FFT powering MASS, and a STOMP self-join, with results matched to stumpy. A compact facade, an indicator that draws the profile and flags discords, and a demonstration Expert Advisor show how to read and use the signal in practice.

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F498%3Futm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Dhow.buy.expert%26utm_content%3Dbuy.expert%26utm_campaign%3D0622.MQL5.com.Internal&a=yiuacrhbffqmmulobpsgnypolteeimpt&s=949562ee5e6aca93c0231542844344e241ce4a26ab488f494b70624c190b74d7&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=vszqksnlobrgohajiimwqdfangblcclx&ssn=1788776413051475399&ssn_dr=0&ssn_sr=0&fv_date=1788776413&ref=https%3A%2F%2Fwww.mql5.com%


---
# 2739: An Example of Developing a Spread Strategy for Moscow Exchange Futures
HEADS: # An Example of Developing a Spread Strategy for Moscow Exchange Futures | ### Negative Correlation of Assets: Si and RTS | ### Calculating Linear Regression between Si and RTS | ### Drawing an indicator of spread between Si and a synthetic sequence | ### Creating a linear regression channel on the spread channel over the last 100 bars | ### Strategy #1: Linear regression slope change on a spread chart | ### Testing the trading Strategy #1 | ### Optimization of trading Strategy #1 | ### Strategy #2: Spread sign change on a completed bar | ### Strategy #3: Spread sign change on the current bar and confirmation over N ticks | ### Strategy 4: Spread reaches a preset percent value | ### MetaTrader 5 — Trading strategy developing environment | ### Important notes on the Strategies

## Intro
# An Example of Developing a Spread Strategy for Moscow Exchange Futures

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Examples](https://www.mql5.com/en/articles/mt5/examples) | 7 February 2017 at 03:32

11 011 [ 44](https://www.mql5.com/en/forum/169276 "Comments")

[MetaQuotes](https://www.mql5.com/en/users/metaquotes)

The MetaTrader 5 platform allows developing and testing trading robots that simultaneously trade multiple financial instruments. The built-in Strategy Tester automatically downloads required tick history from the broker's server taking into account contract specifications, so the developer does not need to do that manually. This makes it possible to easily and reliably reproduce trading environment conditions, including even millisecond intervals between the arrival of ticks on different symbols. In this article we will demonstrate the development and testing of a spread strategy on two [Moscow Exchange futures](http://www.moex.com/en/derivatives/select.aspx "http://moex.com/en/derivatives/s


## Key hits
**score 4:** The MetaTrader 5 platform allows developing and testing trading robots that simultaneously trade multiple financial instruments. The built-in Strategy Tester automatically downloads required tick history from the broker's server taking into account contract specifications, so the developer does not need to do that manually. This makes it possible to easily and reliably reproduce trading environment conditions, including even millisecond intervals between the arrival of ticks on different symbols. In this article we will demonstrate the developm

**score 3:** # An Example of Developing a Spread Strategy for Moscow Exchange Futures

**score 2:** Si-M.Y and RTS-M.Y futures are traded on Moscow Exchange. These futures types are tightly correlated. Here M.Y means contract expiration date:

**score 2:** The spread indicator shows that the difference between the Si futures and the synthetic symbol changes from time to time. In order to evaluate the current spread, let us create the *SpreadRegression\_Ind.mq5* indicator (spread with a linear regression on it) that draws a trend line on a spread chart. The line parameters are calculated using linear regression. Let us launch the two indicators on a chart for debugging.

**score 2:** In this article, we have considered 4 simple strategies for spread trading. Testing and optimization results produced by these strategies should not be used as a guide to action, because they were obtained in a limited interval and can be random to some extent. The original purpose of this article is to show how easy and convenient it is to test and debug trading ideas using MetaTrader 5.

**score 2:** For a balanced trading, you should select volume for each spread symbol. In this article, we only used a 1-lot volume for each symbol.

**score 1:** Si is a futures contract on US dollar/Russian ruble exchange rate, RTS is a futures contract on the RTS index expressed in US dollars. The RTS index includes stocks of Russian companies, the prices of which are expressed in rubles, USD/RUR fluctuations also affect index fluctuations expressed in US dollars. Price charts show that when one asset grows, the second asset usually falls.

**score 1:** ### Drawing an indicator of spread between Si and a synthetic sequence


## Tail
[Auto detection of extreme points based on a specified price variation](https://www.mql5.com/en/articles/2817)

Automation of trading strategies involving graphical patterns requires the ability to search for extreme points on the charts for further processing and interpretation. Existing tools do not always provide such an ability. The algorithms described in the article allow finding all extreme points on charts. The tools discussed here are equally efficient both during trends and flat movements. The obtained results are not strongly affected by a selected timeframe and are only defined by a specified scale.

[Patterns available when trading currency baskets](https://www.mql5.com/en/articles/2816)

Following up our previous article on the currency baskets trading principles, here we are going to analyze the patterns traders can detect. We will also consider the advantages and the drawbacks of each pattern and provide some recommendations on their use. The indicators based on Williams' oscillator will be used as analysis tools.

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F117%3Futm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Dorder.expert%26utm_content%3Dorder.freelance%26utm_campaign%3D0622.MQL5.com.Internal&a=tunpwtbhegzufrqocbwiszessdutnobs&s=d9e7484e15300021b4066b1df77a94a1352f9e7c326d5113006bb4f6476bafeb&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=vysjeeazibtrowqbsqskcxwtoepmawji&ssn=1788804766483880696&ssn_dr=0&ssn_sr=0&fv_date=1788804766&ref=https%3A%2F%2Fwww.mql5.c


---
# 14035: Forex spread trading using seasonality
HEADS: # Forex spread trading using seasonality | ### Introduction | ### 1. Pair trading on Forex | ### 2. Plotting a spread chart | ### | ### 3. Calculating the size of spread symbol positions | ### **4. Examples of seasonal analysis in spread trading** | ### 5. Providing data in the seasonal analysis of symbol spread movements | ### Conclusion

## Intro
# Forex spread trading using seasonality

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Indicators](https://www.mql5.com/en/articles/mt5/indicators) | 8 January 2025 at 09:15

5 286 [ 2](https://www.mql5.com/en/forum/479322 "Comments")

[Roman Shiredchenko](https://www.mql5.com/en/users/r0man)

In the previous [article](https://www.mql5.com/en/articles/12996), we considered the element of seasonality in the markets. Here we will have a look at the option of representing movements according to seasonal patterns in the form of symbol spread indicators. A trading method is considered, in which one symbol is bought and another is sold, thus, such an entry into the market is considered as a single (spread) position. Pair trading symbols should preferably have a correlation for greater trading efficiency.


## Key hits
**score 2:** One of the goals of spread trading is usually to eliminate the trend component in its movement for a more predictable version of its trading from the range boundaries. For this purpose, different volumes or, in the context of this article, weighting ratios of proportionality of spread symbols movement can be used to enter the market by spread symbols based on research.

**score 2:** input string Symbol2_Name = "GBPUSD";   //second spread symbol input bool   Symbol2_Reverse = false;    //inverse correlation input double Weighting_coefficients1 = 1;  // proportionality factor (position volume) of the first spread symbol input double Weighting_coefficients2 = 1;  // proportionality factor (position volume) of the first spread symbol ```

**score 2:** Another important aspect lies in the correct calculation of the size of positions opened on spread symbols. It would be logical to assume that two positions should be of equal volume, which means it is enough to open two positions with the same number of lots. But it is not that simple. If we calculate the difference between the traded symbols of the spread in points, then we assume that the points are equal for both instruments. In fact, to align positions we need to take into account the different point prices of the two symbols (spread instr

**score 2:** input double Weighting_coefficients1 = 1;  // proportionality factor (position volume) of the first spread symbol input double Weighting_coefficients2 = 1;  // proportionality factor (position volume) of the first spread symbol ```

**score 1:** # Forex spread trading using seasonality

**score 1:** In the previous [article](https://www.mql5.com/en/articles/12996), we considered the element of seasonality in the markets. Here we will have a look at the option of representing movements according to seasonal patterns in the form of symbol spread indicators. A trading method is considered, in which one symbol is bought and another is sold, thus, such an entry into the market is considered as a single (spread) position. Pair trading symbols should preferably have a correlation for greater trading efficiency.

**score 1:** In case of negative correlation, symbols move in opposite directions. For example, EURUSD and USDCHF. Both cases are examples of strong dependence. Notably, the reverse spread symbol is bought or sold in the same direction as the first spread symbol — EURUSD. Spread bought EURUSD in long position, while on USDCHF inverse spread symbol we enter a long position as well. Spread sold: we have a sell position on the first symbol of the spread EURUSD and we have a sell position on USDUCHF as well.

**score 1:** In pair trading, the spread of a pair of symbols is traded, that is, the difference between two trading instruments. If it is initially known that these symbols are moving in the same direction, then at the next divergence, they will most likely converge back.


## Tail
[News Trading Made Easy (Part 6): Performing Trades (III)](https://www.mql5.com/en/articles/16170)

In this article news filtration for individual news events based on their IDs will be implemented. In addition, previous SQL queries will be improved to provide additional information or reduce the query's runtime. Furthermore, the code built in the previous articles will be made functional.

[Neural Networks Made Easy (Part 96): Multi-Scale Feature Extraction (MSFformer)](https://www.mql5.com/en/articles/15156)

Efficient extraction and integration of long-term dependencies and short-term features remain an important task in time series analysis. Their proper understanding and integration are necessary to create accurate and reliable predictive models.

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F523%3Futm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Dchoose.signals%26utm_content%3Dsubscribe.signal%26utm_campaign%3D0622.MQL5.com.Internal&a=fyznzyduwsltgnhlftytumasbfgbwlqw&s=91bc0eca8f132d3df7d14cdb1baebac753aef179403d60dc83856af55a4d6769&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=qjxexjtnowdvbfryxlknaeiooruqylbx&ssn=1788796547585264545&ssn_dr=0&ssn_sr=0&fv_date=1788796547&ref=https%3A%2F%2Fwww.mql


---
# 15622: Evaluating the Quality of Forex Spread Trading Based on Seasonal Factors in MetaTrader 5
HEADS: # Evaluating the Quality of Forex Spread Trading Based on Seasonal Factors in MetaTrader 5 | ### Introduction | ### Seasonality and spread trading | ### | ### Seasonality analysis methodology | ### Seasonal spread trading: Description and graphical representation | ### | ### Applying the SpreadMultiYearComparison indicator | ### | ### Trading seasonality on the daily timeframe: general principles | ### **How to use the SpreadMultiYearComparison indicator** | ### Conclusion

## Intro
# Evaluating the Quality of Forex Spread Trading Based on Seasonal Factors in MetaTrader 5

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Trading](https://www.mql5.com/en/articles/mt5/trading) | 25 May 2026 at 07:15

1 866 [ 9](https://www.mql5.com/en/forum/510218 "Comments")

[Roman Shiredchenko](https://www.mql5.com/en/users/r0man)

Seasonality is recurring price movements associated with climatic, economic and behavioral factors. It is most prominent in commodity markets, but is also found in Forex and the stock market. Examples of seasonal effects: Christmas rally, summer rise in coffee prices, January effect.


## Key hits
**score 2:** Please note the symbol tickers for your broker, since they may differ. Also, we place the indicator on the chart of the first symbol of the WTI spread. Coefficients 1:1.

**score 1:** # Evaluating the Quality of Forex Spread Trading Based on Seasonal Factors in MetaTrader 5

**score 1:** The article considers the creation of an indicator for assessing the seasonality quality using [MQL5](https://www.metaquotes.net/en/metatrader5/algorithmic-trading/mql5 "https://www.metaquotes.net/en/metatrader5/algorithmic-trading/mql5"). It allows analyzing both the seasonality of a single symbol and the spread of two instruments. The indicator helps identify statistically significant seasonal movements, use weighting factors, and generate reports for a given month.

**score 1:** Spread trading is the simultaneous opening of long and short positions on related instruments. Profit is generated by changes in relative prices between assets. Unlike arbitrage, spread positions carry risk, but it is lower than trading a single asset because relative prices are more stable.

**score 1:** Using seasonal patterns in spread trading reduces the influence of external factors and increases predictability. The **SpreadMultiYearComparison** indicator for MetaTrader 5 helps identify and analyze such patterns. It is useful for both spread analysis and single asset analysis.

**score 1:** In the indicator, the spread is calculated as the difference between the opening prices of two instruments, with configurable weighting multipliers for each symbol, depending on the relative weight of its quotes within the spread.

**score 1:** 1. Pattern analysis: study the indicator chart, identify periods of spread growth/decline that repeat from year to year. 2. Entry point selection: Open a position at the beginning of the month if the spread has historically risen during this period. For example, if you see that the spread tends to widen in a particular month, you might consider buying the spread (buying the first asset and selling the second) at the beginning of that month. 3. Risk management: set stop-loss and take-profit levels, and adjust position size to suit your risk prof

**score 1:** The SpreadMultiYearComparison indicator is also useful for identifying seasonal patterns in the movement of a single asset. If you see that a certain asset (such as energy) tends to rise in price in December over many years, you can use this information to make a decision to buy that asset in December of the current year.


## Tail
[Market Microstructure in MQL5 (Part 2): Measuring long memory in MQL5 with Hurst estimators](https://www.mql5.com/en/articles/22553)

Part 2 focuses on practical long-memory detection for intraday data. Three complementary Hurst estimators are implemented and combined into a confidence‑weighted composite, with confidence tied to valid regression scales. The final H and confidence populate the shared analysis struct, enabling indicators to act only when H departs from the neutral 0.40–0.60 band and to select trend‑following above 0.60 or mean‑reversion below 0.40.

[MetaTrader 5: Build a Market to Suit Your Strategy — Renko/Range/Volume, Synthetics, and Stress Tests on Custom Symbols](https://www.mql5.com/en/articles/22391)

In this article, we demonstrate how to use API of the MetaTrader 5 custom symbols to transform your terminal into a data constructor for generating timeless Renko, Range, and Equal-Volume charts and assembling synthetic instruments. We will analyze tick aggregation and history modification for stress tests (spread widening, stop level changes) taking into account platform limitations. Besides, you will get some practice of handling CiCustomSymbol and routing orders to a real symbol through the CustomOrder wrapper with ready-made code fragments.

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F117%3Futm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Dorder.expert%26utm_content%3Dorder.freelance%26utm_campaign%3D0622.MQL5.com.Internal&a=tunpwtbhegzufrqocbwiszessdutnobs&s=d9e7484e15300021b4066b1df77a94a1352f9e7c326d5113006bb4f6476bafeb&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=kxrdyvvzhazdjytsalalckqaxdaykpxc&ssn=1788794238278863124&ssn_dr=0&ssn_sr=0&fv_date=1788794238&ref=https%3A%2F%2Fwww.mql5.c


---
# 17934: Advanced Order Execution Algorithms in MQL5: TWAP, VWAP, and Iceberg Orders
HEADS: # Advanced Order Execution Algorithms in MQL5: TWAP, VWAP, and Iceberg Orders | ### Introduction | ### | ### Understanding Execution Algorithms | ### Implementation in MQL5 | ### | ### Performance Analyzer Implementation | ### | ### | ### Comparing Algorithm Performance | ### | ### Integrating Execution Algorithms with Trading Strategies | ### Integration Examples | ### Integrated Strategy

## Intro
# Advanced Order Execution Algorithms in MQL5: TWAP, VWAP, and Iceberg Orders

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Trading systems](https://www.mql5.com/en/articles/mt5/trading_systems) | 15 May 2025 at 03:07

12 198 [ 6](https://www.mql5.com/en/forum/486550 "Comments")

[N Soumik](https://www.mql5.com/en/users/nsoumik102)

1. [Introduction](https://www.mql5.com/en/articles/17934#introduction) 2. [Understanding Execution Algorithms](https://www.mql5.com/en/articles/17934#understanding_execution_algorithms) 3. [Implementation in MQL5](https://www.mql5.com/en/articles/17934#section3) 4. [Performance Analyzer Implementation](https://www.mql5.com/en/articles/17934#performance_analyzer_implementation) 5. [Comparing Algorithm Performance](https://www.mql5.com/en/articles/17934#comparing_algorithm_performance) 6. [Integrating Execution Algorithms with Trading Strategies](https://www.mql5.com/en/articles/17934#integrating_execution_algorithms_with_trading) 7. [Integration Examples](https://www.mql5.com/en/articles/1793


## Key hits
**score 3:** Today’s democratized landscape means the same execution tech that once demanded multi-million-dollar budgets can now run on your personal trading station. By dropping polished MQL5 code for TWAP, VWAP, and Iceberg strategies into your platform, you’ll arm yourself with institutional firepower—without ever leaving the retail domain.

**score 3:** - Sends orders at regular time intervals between start and end.      - Usually uses equal-sized orders (though you can add randomness to sizes).      - Follows a predetermined timetable, regardless of price moves.      - Spreads market impact evenly over time to keep slippage low.    - When to use:

**score 3:** - You need an average execution price over a specific timeframe.      - Liquidity is steady throughout the trading period.      - You have a fixed window to complete your order.      - You prefer a simple, predictable approach. 2. Volume-Weighted Average Price (VWAP): VWAP improves on TWAP by weighting order sizes according to expected volume. Instead of equal chunks, it sends larger trades when volume tends to be higher.       - How it works:

**score 3:** - Your performance is measured against VWAP.      - Volume follows a predictable daily pattern.      - You are trading in a market where liquidity varies through the session.      - You want to align with the market’s natural flow. 3. Iceberg Orders: Iceberg Orders focus on hiding the true size of a large order. Only a small “tip” is visible at any time; once it fills, the next portion appears.       - How it works:

**score 3:** public:    // Constructor    CExecutionAlgorithm(string symbol, double volume, datetime startTime, datetime endTime, int slippage = 3);

**score 3:** This function builds and sends a market order by zero‐initializing an MqlTradeRequest and MqlTradeResult, filling in symbol, volume, order type, price, slippage and a magic number, then calling OrderSend. If the send fails or the broker’s return code isn’t TRADE\_RETCODE\_DONE, it logs the error and returns false. On success it updates internal counters (total/fill counts, executed and remaining volume), recalculates the average price, captures the ticket ID, and returns true.

**score 3:** public:    // Constructor    CTWAP(string symbol, double volume, datetime startTime, datetime endTime,           int intervals, ENUM_ORDER_TYPE orderType, bool useRandomization = false,           double randomizationFactor = 0.2, int slippage = 3, int initialDelay = 10);

**score 3:** // TWAP specific methods    void              CalculateIntervalVolume();    datetime          CalculateNextExecutionTime();    double            GetRandomizedVolume(double baseVolume);    bool              IsTimeToExecute(); }; ```


## Tail
Fibonacci retracements are a popular tool in technical analysis, helping traders identify potential reversal zones. In this article, we’ll explore how these retracement levels can be transformed into target variables for machine learning models to help them understand the market better using this powerful tool.

[Developing a Replay System (Part 68): Getting the Time Right (I)](https://www.mql5.com/en/articles/12309)

Today we will continue working on getting the mouse pointer to tell us how much time is left on a bar during periods of low liquidity. Although at first glance it seems simple, in reality this task is much more difficult. This involves some obstacles that we will have to overcome. Therefore, it is important that you have a good understanding of the material in this first part of this subseries in order to understand the following parts.

Full-featured MetaTrader 5 platform for any devices and web browsers

Learn more](https://www.mql5.com/ff/go?link=https://trade.metatrader5.com/&a=uyigsjnbfcdvysiynusmriwvhincciwd&s=c95531ae2fd8a81b0fac3def2e4cf820a67584bbf4b02f76ec75f808942dbbd2&uid=&ref=https://www.mql5.com/en/articles/17934&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=5124906478632319203)


---
# 22963: Implementing Anchored VWAP Indicator in MQL5: A Step-by-Step Guide
HEADS: # Implementing Anchored VWAP Indicator in MQL5: A Step-by-Step Guide | ### Introduction | ### Why Anchored VWAP Matters | ### Calculation Methodology | ### Indicator Template | ### Properties | ### Headers | ### Input Definition and Validation | ### Buffer Declaration | ### Initialization | ### The Anchor Line | ### Applied Price | ### Volume Types | ### Next Anchor Time

## Intro
# Implementing Anchored VWAP Indicator in MQL5: A Step-by-Step Guide

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Examples](https://www.mql5.com/en/articles/mt5/examples) | 11 August 2026 at 10:08

1 223 [ 1](https://www.mql5.com/en/forum/514362 "Comments")

[Prasad Fidelis Dsa](https://www.mql5.com/en/users/prasaddsa)

The Anchored VWAP is a technical indicator that calculates the volume-weighted price of an asset starting from a user-defined anchor point. It helps traders gauge trend strength, pinpoint entries and exits, analyze market-moving events, investigate swing highs/lows, and measure price extension using standard deviation bands. Unlike regular moving averages that forget beyond a fixed window length, the Anchored VWAP has real memory as it accumulates price and volume data from the anchor point forward.


## Key hits
**score 4:** A precursor of the Anchored VWAP is the standard VWAP, which has the same mathematical basis as the Anchored VWAP, but it starts the calculation at the session open and resets at the end of the trading day. By letting traders anchor VWAP beyond the standard session boundary, Anchored VWAP resolves the standard VWAP's main limitation. It also extends volume-weighted analysis to non-session-based use cases. This makes the Anchored VWAP suitable for:

**score 4:** Throughout the article, we will implement the Anchored VWAP to work with all price bases, including the typical price. The [Applied Price](https://www.mql5.com/en/articles/22963#applied_price "Applied Price") section will cover the computations of the price bases. The [Volume Types](https://www.mql5.com/en/articles/22963#volume_types "Volume Types") section will describe volume types and use tick volume as a practical proxy for trading activity in asset classes where real volume is inaccessible. The formulas from this section will be implemente

**score 3:** The [OnCalculate](https://www.mql5.com/en/docs/event_handlers/oncalculate "OnCalculate") function provides volume data in the form of two arrays—*volume* and *tick\_volume.* The *volume* array holds real volume that represents the actual number of contracts or lots traded during the specified period. Tick volume is the number of price changes (ticks) within the specified period. Let us define a function *GetVolume* to return the volume data for our indicator calculation. It will accept a reference to both the *volume* and *tick\_volume* arrays 

**score 2:** The Anchored VWAP is a technical indicator that calculates the volume-weighted price of an asset starting from a user-defined anchor point. It helps traders gauge trend strength, pinpoint entries and exits, analyze market-moving events, investigate swing highs/lows, and measure price extension using standard deviation bands. Unlike regular moving averages that forget beyond a fixed window length, the Anchored VWAP has real memory as it accumulates price and volume data from the anchor point forward.

**score 2:** In this article, we will build an Anchored VWAP indicator in MQL5. Users can set precise anchor times and drag an on-chart anchor line to adjust placement visually. We will implement two modes: a fixed anchor for single-event analysis and a session-reset mode. Session boundaries can be daily, weekly, or monthly. The indicator supports optional standard deviation bands and a selectable applied price. It also supports multiple instances to run several anchors on the same chart. We will focus on indicator architecture: buffer layout, anchor state 

**score 2:** > By placing the anchor at the start of the actual personal trading session, a trader can benchmark against an average that is indicative of the activity of the participants, analyze trends, and establish key levels pertaining to the session. > >  > > Custom session boundaries using Anchored VWAP

**score 2:** The Anchored VWAP consists of the main volume-weighted average price and the standard deviation bands calculated cumulatively from the anchor point forward. The VWAP is given by the formula:

**score 2:** //---    return(INIT_SUCCEEDED);   } //+------------------------------------------------------------------+ //| Custom indicator iteration function                              | //+------------------------------------------------------------------+ int OnCalculate(const int32_t rates_total,                 const int32_t prev_calculated,                 const datetime &time[],                 const double &open[],                 const double &high[],                 const double &low[],                 const double &close[],                 co


## Tail
The article examines a Williams five‑bar fractal feature pipeline and shows how a centered rolling window creates a true look‑ahead leak. It identifies two additional silent bugs—a hardcoded shift tied to the default n and a volatility threshold that ignores its input—and consolidates fixes under a single leak\_safe flag. Readers get leak‑free fractal, level, trend, and signal features, plus guidance on when unshifted columns remain valid for labeling.

[Generating a Per-Symbol Trade Analytics PDF Report from MQL5](https://www.mql5.com/en/articles/23502)

This article shows how to generate a dependency-free, single-page PDF report in MQL5 using only string assembly and the FILE\_BIN API. The script computes per-symbol trade statistics, then renders a labeled table and an equity curve with explicit PDF color and drawing operators. Statistics are calculated in a standalone module, so every value can be verified against synthetic data without relying on a live trading account.

Trade with no restrictions from any mobile device, OS and web browser

Learn more](https://www.mql5.com/ff/go?link=https://trade.metatrader5.com/&a=fkjlpstbxdmrrwpblfatcsdjyrxbizyj&s=f462f051eb7aaec36d6b31792d312d60d3f5a50c83b12d0d66e85d5d61bd941b&uid=&ref=https://www.mql5.com/en/articles/22963&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=5121678763464722169)


---
# 22990: Building an Object-Oriented Session VWAP Engine in MQL5
HEADS: # Building an Object-Oriented Session VWAP Engine in MQL5 | ### Introduction and Practical Pain Points | ### The Core Math and Daily Time Anchors | ### The VWAP Signal Contract | ### Architecting the Reusable Include File | ### Tracking Midnight via MqlDateTime | ### Implementing the Double-Pass Calculation Loop | ### Building the Visual Diagnostic Indicator | ### EA Integration and Execution Layer | ### Backtesting Constraints and Market Dynamics | ### Conclusion and Reusable Artifacts | ### File Structure Table

## Intro
# Building an Object-Oriented Session VWAP Engine in MQL5

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Trading systems](https://www.mql5.com/en/articles/mt5/trading_systems) | 29 June 2026 at 10:18

1 451 [ 9](https://www.mql5.com/en/forum/511914 "Comments")

[Amanda Vitoria De Paula Pereira](https://www.mql5.com/en/users/kayruyuta)

### Introduction and Practical Pain Points


## Key hits
**score 4:** The most difficult engineering hurdle when building a session VWAP is identifying the starting point of the current trading day. In standard MQL5 development, you cannot simply look back a fixed number of bars like 20 or 200. On a standard 5-minute chart, a full day should theoretically contain 288 candlesticks. However, if the market closes early for a holiday, or if the broker server drops connection packets during low-liquidity hours, the actual number of bars will fluctuate unpredictably. Hardcoding a static lookback window will force the l

**score 4:** The data loop relies on a strict double-pass linear profile. The first pass iterates through the synchronized rates memory to calculate the baseline VWAP. It sums the volume products and tracks total liquidity. One critical trap here involves zero-volume environments. During the weekly market rollover or sudden broker disconnections, the platform can print a phantom candle with absolute zero tick volume. Attempting to divide the cumulative price sum by a volume of zero will cause a fatal division-by-zero exception, instantly crashing the Expert

**score 4:** The second pass targets the volume-weighted variance. It scans the same bar window again, subtracting the newly defined baseline VWAP from each bar's typical price. This difference is squared and multiplied by the tick volume of that specific candle to ensure high-liquidity spikes dominate the volatility rating. Finally, the square root of this average gives the standard deviation, allowing the engine to calculate the upper and lower bands dynamically.

**score 3:** The root of the error is that standard indicators entirely ignore tick volume arrays during their calculation passes. I wanted to replace this traditional approach with something much more adaptive that tracks where money is actually being spent. The Volume Weighted Average Price (VWAP) fulfills this role by weighting every price fluctuation by the absolute liquidity traded at that level. Standard MQL5 does not provide a native VWAP that resets daily and includes rolling deviation bands. This makes quick integration into automated strategies di

**score 3:** The mathematical calculation behind the VWAP is highly pragmatic and avoids the smoothing lag found in traditional technical indicators. Instead of simply summing closing prices and dividing by a fixed lookback period, we extract the typical price of each candle by averaging its high, low, and close coordinates. We then multiply this typical price by the corresponding tick volume recorded for that specific bar. This product is accumulated sequentially from a fixed starting point. Finally, we divide this cumulative sum of price and volume by the

**score 3:** To prevent our trading robot from executing trades based on unconfirmed intraday noise, the calculation loop will operate exclusively on fully closed bars. We enforce this constraint across both the indicator and the advisor by passing a fixed bar shift parameter of 1 to our calculation methods. This ensures that the algorithm entirely ignores the active, unconfirmed fluctuations of candle index 0. Furthermore, the signal contract strictly mandates that the accumulation math resets to absolute zero at exactly 00:00 broker server time every sing

**score 2:** # Building an Object-Oriented Session VWAP Engine in MQL5

**score 2:** When I build intraday trading systems in MQL5, my first reflex is usually to drop a standard moving average on the chart to filter the short-term trend. This approach looks tolerable during dead market hours or tight ranges. However, live tests on liquid currency pairs reveal a major structural flaw. A major macro news candle can instantly shift the market baseline due to institutional volume. A simple moving average treats that heavy candle the same as a low-volume candle from the quiet night session because it only accounts for closing prices


## Tail
[MetaTrader 5 Machine Learning Blueprint (Part 18): Sequential Bootstrap, Corrected — Clone, Class Erasure, and the Comparison Toolkit](https://www.mql5.com/en/articles/22912)

The article diagnoses two defects that neutralize sequential bootstrap during cross‑validation: type erasure of SequentiallyBootstrappedBaggingClassifier and a fold‑level shape mismatch from cloning full samples info sets. It retains the classifier's identity, adds find seq bagging to re‑inject fold‑sliced t1 in CalibratorCV.fit, and resets state per split. A new bootstrap\_comparison module reports OOF and OOB metrics and memory, letting you verify that sequential sampling is applied correctly and quantify its impact.

[Forecasting in Trading Using Grey Models](https://www.mql5.com/en/articles/19012)

The article discusses the application of Grey models to forecasting financial time series. We will consider the operating principles of Grey models and the specifics of their application to financial series. We will also discuss the advantages and limitations of using these models in trading.

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F22768&a=tbhjnpuqwxhpclxcbddjqkjduncqomjn&s=79b3b7d43ab907fc7600c7b642473740cb615767dd449e8297031033d7b9547b&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=nrhkqzqwfbqpafnveoqxiiewrcfayfsm&ssn=1788777656674614667&ssn_dr=0&ssn_sr=0&fv_date=1788777656&ref=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F22990&back_ref=https%3A%2F%2Fwww.google.com%2F&title=Building%20an%20Object-Oriented%20Session%20VWAP%20Engine%20in%20MQL5%20-%20MQL5


---
# 16984: Price Action Analysis Toolkit Development (Part 10): External Flow (II) VWAP
HEADS: # Price Action Analysis Toolkit Development (Part 10): External Flow (II) VWAP | ### Introduction | ### Understanding the Strategy | ### Core Logic | # Ensure critical columns have no missing values | # Convert 'date' column to datetime | # Handle zero volume by replacing with NaN and dropping invalid rows | # Check if data exists after filtering | # Calculate VWAP and additional metrics | # Calculate strength and generate signals | # Generate Buy/Sell signals based on VWAP | # Signal explanation | # Return data with major and minor support/resistance levels included | ### Outcomes

## Intro
# Price Action Analysis Toolkit Development (Part 10): External Flow (II) VWAP

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Trading systems](https://www.mql5.com/en/articles/mt5/trading_systems) | 30 January 2025 at 08:37

6 682 [ 4](https://www.mql5.com/en/forum/480617 "Comments")

[Christian Benjamin](https://www.mql5.com/en/users/lynnchris)

In our [previous article](https://www.mql5.com/en/articles/16967), we introduced the integration of market data with external libraries, showcasing the ability to analyze markets through various automated systems. Python's robust framework offers powerful tools for advanced data analysis, predictive modeling, and visualization, while MQL5 focuses on seamless trade execution and chart-based operations. By combining these strengths, we achieve a flexible, efficient, and sophisticated system for market analysis and trading.


## Key hits
**score 2:** This article presents a powerful tool built around the concept of Volume Weighted Average Price (VWAP) to deliver precise trading signals. Leveraging Python's advanced libraries for calculations enhances the accuracy of the analysis, resulting in highly actionable VWAP signals. We’ll start by exploring the strategy, then delve into the core logic of the MQL5 code and discuss the outcomes. Finally, we’ll wrap up with a conclusion. Let’s take a look at the table of contents below:

**score 2:** VWAP, or volume-weighted average price, is a technical analysis tool that reflects the ratio of an asset's price to its total trading volume. It gives traders and investors a sense of the average price at which a stock has been traded over a specific period. VWAP is often used as a benchmark by more passive investors, such as pension funds and mutual funds, who seek to evaluate the quality of their trades. It is also valuable for traders looking to determine whether an asset was bought or sold at an optimal price.     To calculate VWAP, the for

**score 2:** VWAP = ∑(quantity of asset traded × asset price) / total volume traded that day

**score 2:** The VWAP Expert Advisor (EA) is designed to monitor charts and interact seamlessly with Python for advanced market analysis. It sends market data to Python and logs the received trading signals in the MetaTrader 5 Experts tab. The strategy utilizes the Volume-Weighted Average Price (VWAP) as its core indicator to provide precise and actionable insights. Below is a detailed breakdown of the strategy:

**score 2:** - VWAP Calculation: Determines the average price weighted by volume over the selected timeframe. - Signal Generation: Provides trading signals (e.g., buy/sell) based on the relationship between current price and VWAP levels. - Explanations: Each signal includes a textual explanation to clarify why it was generated.

**score 2:** After sending the data, we need to handle the response from the Python server. This is where the real magic happens, as the Python server analyzes the data and provides a trading signal based on the VWAP (Volume Weighted Average Price). The response is returned in JSON format, and we use a helper function, *ExtractValueFromJSON()*, to extract the relevant values (VWAP and explanation) from the response.

**score 2:** The script calculates the VWAP (Volume Weighted Average Price) and additional metrics like typical price, average price, average volume, and support/resistance levels.

**score 2:** - VWAP Calculation: The VWAP is calculated as a cumulative sum of the typical price weighted by the volume, divided by the cumulative volume. - Typical Price: The typical price is calculated as the average of high, low, and close for each period.


## Tail
[MQL5 Wizard Techniques you should know (Part 53): Market Facilitation Index](https://www.mql5.com/en/articles/17065)

The Market Facilitation Index is another Bill Williams Indicator that is intended to measure the efficiency of price movement in tandem with volume. As always, we look at the various patterns of this indicator within the confines of a wizard assembly signal class, and present a variety of test reports and analyses for the various patterns.

[Automating Trading Strategies in MQL5 (Part 4): Building a Multi-Level Zone Recovery System](https://www.mql5.com/en/articles/17001)

In this article, we develop a Multi-Level Zone Recovery System in MQL5 that utilizes RSI to generate trading signals. Each signal instance is dynamically added to an array structure, allowing the system to manage multiple signals simultaneously within the Zone Recovery logic. Through this approach, we demonstrate how to handle complex trade management scenarios effectively while maintaining a scalable and robust code design.

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Fsignals%2Fmt5%2Fpage1%3Fpreset%3D2%26utm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Dmax.profit.signals%26utm_content%3Dsubscribe.signal%26utm_campaign%3D0622.MQL5.com.Internal&a=hgyovyikvykcdukcncnktswvlctghemf&s=545653d14172edfb3c9c02ca8e948778c29f9c1b70be9a587e8d4b040fb23539&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=zuoyghikljzxwolaoejophgiwhqxxrcp&ssn=1788791848539844737&ssn_dr=0&ssn_sr=0&fv_date=1788791848&r


---
# 22063: Beyond the Clock (Part 1): Building Activity and Imbalance Bars in Python and MQL5
HEADS: # Beyond the Clock (Part 1): Building Activity and Imbalance Bars in Python and MQL5 | ### Table of Contents | ### Introduction | ### | ### The Problem with Sampling on the Clock | ### | ### Infrastructure: Parquet Storage and Dask Loading | ### | ### Cleaning Tick Data Before Bar Construction | ### | ### Standard Bars: Time, Tick, Volume, Dollar | ### | ### Information Bars: Sampling on Market Intent | # Preferred — auto-calibrated dollar imbalance bars targeting M15 cadence

## Intro
# Beyond the Clock (Part 1): Building Activity and Imbalance Bars in Python and MQL5

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Trading systems](https://www.mql5.com/en/articles/mt5/trading_systems) | 8 May 2026 at 07:19

2 212 [ 2](https://www.mql5.com/en/forum/509452 "Comments")

[Patrick Murimi Njoroge](https://www.mql5.com/en/users/patricknjoroge743)

1. [Introduction](https://www.mql5.com/en/articles/22213/#para0) 2. [The Problem with Sampling on the Clock](https://www.mql5.com/en/articles/22213/#para1) 3. [Infrastructure: Parquet Storage and Dask Loading](https://www.mql5.com/en/articles/22213/#para2) 4. [Cleaning Tick Data Before Bar Construction](https://www.mql5.com/en/articles/22213/#para3) 5. [Standard Bars: Time, Tick, Volume, Dollar](https://www.mql5.com/en/articles/22213/#para4) 6. [Information Bars: Sampling on Market Intent](https://www.mql5.com/en/articles/22213/#para5) 7. [The Unified API — *make\_bars()*](https://www.mql5.com/en/articles/22213/#para6) 8. [Bar Type Selection in Practice](https://www.mql5.com/en/articles/2221


## Key hits
**score 4:** Four production problems in the pipeline are addressed explicitly: loading multi-year tick data without exceeding memory (partitioned Parquet storage read via Dask), cleaning broker-feed artifacts that corrupt bar construction (zero spreads, duplicate timestamps, NaT indices), calibrating the adaptive threshold for imbalance bars automatically so the first bar does not bias the EWM history, and persisting the EWM tracker across EA restarts so the threshold does not reset mid-session. A short parity test at the end verifies that the two implemen

**score 3:** The tick rule is a proxy. It misclassifies a meaningful fraction of trades, particularly in markets where the bid-ask spread is wide relative to the tick size. The Lee-Ready algorithm improves classification accuracy for datasets that include the quoted bid and ask at each trade, but the tick rule is sufficient for the purposes of imbalance bar construction and avoids the additional complexity of mid-quote comparisons.

**score 3:** For volume and dollar imbalance bars, the calibrator scales the imbalance estimate by the mean tick volume or mean dollar value respectively, so the threshold has the correct units. The result is that a single *target\_timeframe='M15'* call produces bars that close at roughly the same cadence regardless of whether the metric is a direction, a volume, or a dollar value.

**score 2:** López de Prado formalizes this intuition in Chapter 1 of *Advances in Financial Machine Learning* (AFML). The core argument is that bars should close when a fixed amount of market activity has occurred, not when a fixed amount of time has elapsed. Activity can be measured in ticks, traded volume, or traded dollar value — each measure producing a different sampling scheme with different statistical properties. The most aggressive version of this idea, imbalance bars, closes a bar when the market's directional intent exceeds a threshold, capturin

**score 2:** Bar construction produces wrong results if the input tick stream is not clean. The most common issues in MetaTrader 5 tick exports are negative or zero spreads (a known artifact of certain broker feed configurations), duplicate timestamps from reconnection events, and ticks arriving with NaT index entries when the MetaTrader 5 terminal loses connectivity.

**score 2:** All four standard bar types share a single internal construction path. A grouper object partitions the tick DataFrame by bar membership; aggregation over each group produces OHLC prices, mean spread, and cumulative volume. The *\_make\_bar\_type\_grouper()* function encodes the partitioning logic for each type:

**score 2:** Time bars are the only bar type where the grouper can produce empty groups. A one-hour bar during a market holiday or a session close contains zero ticks. That empty bar is not a data point — it is an absence of data — and passing it downstream propagates a silent error: the OHLC values for an empty group are undefined (pandas returns NaN), and the bar's tick\_volume is zero, which causes division errors in any feature that normalizes by bar activity.

**score 2:** nzeros = eq_zero.sum()     if nzeros > 0:         logger.info(             f"Dropped {nzeros:,} of {ohlc_df.shape[0]:,} rows with zero tick volume."         ) ```


## Tail
[Market Microstructure in MQL5 (Part 1): Robust Foundation](https://www.mql5.com/en/articles/22263)

This article builds the foundation layer of a twelve-part MQL5 market microstructure toolkit. It implements guarded math helpers (SafeDivide, SafeLog, SafeSqrt, SafeExp, SafeTanh), robust data validation (ValidateSymbolV2, SafeCopyClose), trimmed statistical estimators (robust mean var), a linear regression slope, shared structs, and an FFT. You compile a single include file that hardens indicators and expert advisors against silent numerical failures and standardizes data flow for later parts.

[Engineering Trading Discipline into Code (Part 5): Account-Level Risk Enforcement in MQL5](https://www.mql5.com/en/articles/21995)

We introduce an MQL5 discipline engine that enforces risk consistently at the account level. It continuously scans positions from any source, validates SL/TP, equity-based exposure, and target R:R, and automatically corrects deviations by setting levels or adjusting volume. The result is uniform risk structure across manual and EA trades, supported by on-chart feedback and mode-based control.

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F1171%3Futm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Dbest.vps%26utm_content%3Drent.vps%26utm_campaign%3D0622.MQL5.com.Internal&a=nwegcasiojnqcoyrdlgofmjtfardztwf&s=d64d6f3c87f2458cba81f6d7b6694dd9e89dd354d4abc1d0584e405285806c9f&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=tiffjmhpgzcgsbixernxkcxvvbvpjiea&ssn=1788778892216580485&ssn_dr=0&ssn_sr=0&fv_date=1788778892&ref=https%3A%2F%2Fwww.mql5.com%2Fen%2F


---
# 21825: Creating Custom Indicators in MQL5 (Part 9): Order Flow Footprint Chart with Price Level Volume Tracking
HEADS: # Creating Custom Indicators in MQL5 (Part 9): Order Flow Footprint Chart with Price Level Volume Tracking | ### Introduction | ### Decoding the Footprint Chart - What Price Levels Reveal About Market Participation | ### Implementation in MQL5 | ### Backtesting | ### Conclusion

## Intro
# Creating Custom Indicators in MQL5 (Part 9): Order Flow Footprint Chart with Price Level Volume Tracking

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Trading](https://www.mql5.com/en/articles/mt5/trading) | 26 March 2026 at 06:27

7 167 [ 0](https://www.mql5.com/en/forum/507400 "Comments")

[Allan Munene Mutiiria](https://www.mql5.com/en/users/29210372)

Candlestick charts show where price went, but not who controlled each level. Without order flow data, you cannot see whether buyers or sellers dominated a specific price. You also miss whether a move was genuine or on low volume, or where real absorption and aggression happened inside each bar. This article is for [MetaQuotes Language 5](https://www.metaquotes.net/en/metatrader5/algorithmic-trading/mql5 "https://www.metaquotes.net/en/metatrader5/algorithmic-trading/mql5") (MQL5) developers and algorithmic traders looking to build a footprint chart indicator that exposes the volume activity inside every candle.


## Key hits
**score 4:** In live trading, use the delta column to identify where aggressive buyers or sellers stepped in — a bar with a high positive delta near a support level confirms buying conviction, making it a stronger candidate for a long entry. Watch for delta divergence where price makes a new high, but the delta weakens, signaling that buying aggression is fading and a reversal may follow. High total volume rows inside a bar often mark the point of control for that bar — price tends to return to these levels on retracements. In bid versus ask mode, look for 

**score 3:** The [input](https://www.mql5.com/en/docs/basis/variables/inputvariables) section is organized into two groups. Under settings, we declare "displayMode" defaulting to "DELTA", "ticksPerPriceLevel" to control how many ticks wide each price row is, "maxBarsToRender" to limit memory usage by capping stored bars, "priceLevelFontSize" for text sizing on the canvas, and "useStrictPricePositions" to toggle whether overlapping price labels are spread apart or kept at their exact prices. Under colors, we declare five-step gradient inputs for upward volum

**score 3:** To handle the bid versus ask diagonal imbalance coloring, we define the "GetDiagonalVolumeColor" function, which uses a different ratio scale because it compares volumes across adjacent price levels rather than against a bar-wide maximum. Here, the thresholds are 1.5, 2, 3, and 4, reflecting the fact that a meaningful diagonal imbalance requires one side to be a multiple of the other rather than just a fraction. When the ask volume at a level is at least four times the bid volume at the level directly below it, the strongest up color is returne

**score 2:** Candlestick charts show where price went, but not who controlled each level. Without order flow data, you cannot see whether buyers or sellers dominated a specific price. You also miss whether a move was genuine or on low volume, or where real absorption and aggression happened inside each bar. This article is for [MetaQuotes Language 5](https://www.metaquotes.net/en/metatrader5/algorithmic-trading/mql5 "https://www.metaquotes.net/en/metatrader5/algorithmic-trading/mql5") (MQL5) developers and algorithmic traders looking to build a footprint ch

**score 2:** In our [previous article (Part 8)](https://www.mql5.com/en/articles/21390), we enhanced the hybrid [Time Price Opportunity](https://snpedge.vicitradingsolutions.com/p/understanding-time-price-opportunity "https://snpedge.vicitradingsolutions.com/p/understanding-time-price-opportunity") market profile indicator in MQL5 by adding volume data to calculate the point of control, value areas, and volume-weighted average price with customizable highlights. In Part 9, we build an [order flow footprint](https://en.wikipedia.org/wiki/Order_flow_trading "

**score 2:** datetime         lastBarTime           = 0;    // Time of the last processed bar double           lastClosePrice        = 0.0;  // Close price from the previous tick long             lastTickVolume        = 0;    // Tick volume from the previous tick bool             lastTradeAtAsk        = true; // Whether the last trade hit the ask int              currentBarIndex       = -1;   // Index into barFootprints for the current bar

**score 2:** //+------------------------------------------------------------------+ //| Get diagonal volume color for bid/ask imbalance                  | //+------------------------------------------------------------------+ color GetDiagonalVolumeColor(bool isUp, double ratio)   {    //--- Select color tier for diagonal bid/ask imbalance using wider ratio range    if(isUp)      {       //--- Return up color based on ask-to-bid ratio threshold       if(ratio >= 4)   return upColor5;       else if(ratio >= 3)   return upColor4;       else if(ratio >= 2)   r

**score 1:** # Creating Custom Indicators in MQL5 (Part 9): Order Flow Footprint Chart with Price Level Volume Tracking


## Tail
​This article integrates the Optuna hyperparameter optimization (HPO) backend into a unified ModelDevelopmentPipeline. It adds joint tuning of model hyperparameters and sample-weight schemes, early pruning with Hyperband, and crash-resistant SQLite study storage. The pipeline auto-detects primary vs. secondary models, prepends a fitted column-dropping preprocessor for safe inference, supports sequential bootstrapping, generates an Optuna report, and includes bid/ask and LearnedStrategy links. Readers get faster, resumable runs and deployable, s

[MQL5 Trading Tools (Part 25): Expanding to Multiple Distributions with Interactive Switching](https://www.mql5.com/en/articles/21337)

In this article, we expand the MQL5 graphing tool to support seventeen statistical distributions with interactive cycling via a header switch icon. We add type-specific data loading, discrete and continuous histogram computation, and theoretical density functions for each model, with dynamic titles, axis labels, and parameter panels that adapt automatically. The result lets you overlay distribution models on the same sample and compare fit across families without reloading the tool.

Use Git-powered tools in MetaEditor for structured, reliable development

Learn more](https://www.mql5.com/ff/go?link=https://forge.mql5.io%3Futm_source=www.mql5.com%26utm_medium=display%26utm_content=visit%26utm_campaign=visit.mql5.226&a=oygnrjjxveoqzycxkjkckcgtshfunvdu&s=1e458fdafe5955c82ea32b518845e77efbe1196295936353793e9e23a750f4d6&uid=&ref=https://www.mql5.com/en/articles/21825&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=5122109982476209263)


---
# 21829: Creating Custom Indicators in MQL5 (Part 10): Enhancing the Footprint Chart with Per-Bar Volume Sentiment Information Box
HEADS: # Creating Custom Indicators in MQL5 (Part 10): Enhancing the Footprint Chart with Per-Bar Volume Sentiment Information Box | ### Introduction | ### Reading the Bar Story — What Per-Bar Volume Sentiment Reveals at a Glance | ### Implementation in MQL5 | ### Backtesting | ### Conclusion

## Intro
# Creating Custom Indicators in MQL5 (Part 10): Enhancing the Footprint Chart with Per-Bar Volume Sentiment Information Box

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Trading systems](https://www.mql5.com/en/articles/mt5/trading_systems) | 27 March 2026 at 07:34

3 060 [ 0](https://www.mql5.com/en/forum/507456 "Comments")

[Allan Munene Mutiiria](https://www.mql5.com/en/users/29210372)

A footprint chart shows volume at every price level inside each bar. Without a bar-level summary, you must manually aggregate levels to judge which side dominated, estimate how lopsided participation was, and compare sentiment across bars — a step that slows both human interpretation and algorithmic decision-making. This article is for [MetaQuotes Language 5](https://www.metaquotes.net/en/metatrader5/algorithmic-trading/mql5 "https://www.metaquotes.net/en/metatrader5/algorithmic-trading/mql5") (MQL5) developers and systematic traders looking to extend an existing footprint indicator with a per-bar sentiment box updated on every tick, kept lightweight at render time through cached bar metrics


## Key hits
**score 3:** A completed bar contains information that price level rows do not summarize well. Net delta shows which side was more aggressive in aggregate, total volume shows whether that aggression happened on meaningful participation or thin activity, and the buy and sell split reveals the degree of imbalance. When these three numbers are visible above every candle in a compact, color-coded box, a trader can scan across dozens of bars in seconds and immediately identify which bars were dominated by one side, which were balanced, and whether the dominance 

**score 3:** In live trading, use the net delta displayed in the sentiment box as a first filter — a bar closing higher with a strongly negative delta is a warning that sellers were absorbing the move, making it a weaker long candidate than a bar with a matching positive delta. Watch for consecutive bars where the delta direction conflicts with the price direction, as persistent delta divergence often precedes reversals. Use the total volume figure to separate conviction bars from noise — a large delta on low total volume carries less weight than the same d

**score 3:** For the box background color, it computes the absolute ratio of delta to total volume and passes it to "GetVolumeColor" with the direction flag set to true for positive delta and false for negative, producing a color whose intensity reflects how dominant one side was relative to the total activity. A zero delta assigns the neutral weakest shade directly.

**score 3:** The text color derivation follows a different approach. Rather than using the delta-to-total ratio, it takes the dominant side's percentage, subtracts 50 to find how far above an even split it sits, clamps any negative result to zero, then divides by 50 to scale the excess into a zero-to-one ratio using the [MathCeil](https://www.mql5.com/en/docs/math/mathceil) function. This means a perfectly even 50-50 bar produces the weakest text color, while a heavily one-sided bar produces the strongest, making the text itself carry a visual signal about 

**score 2:** A footprint chart shows volume at every price level inside each bar. Without a bar-level summary, you must manually aggregate levels to judge which side dominated, estimate how lopsided participation was, and compare sentiment across bars — a step that slows both human interpretation and algorithmic decision-making. This article is for [MetaQuotes Language 5](https://www.metaquotes.net/en/metatrader5/algorithmic-trading/mql5 "https://www.metaquotes.net/en/metatrader5/algorithmic-trading/mql5") (MQL5) developers and systematic traders looking to

**score 2:** In our [previous article (Part 9)](https://www.mql5.com/en/articles/21825), we built an [order flow footprint](https://en.wikipedia.org/wiki/Order_flow_trading "https://en.wikipedia.org/wiki/Order_flow_trading") chart indicator in MQL5 that tracked tick-by-tick volume at quantized price levels, separated buying and selling activity into bid versus ask and delta display modes, and rendered volume-colored text labels on a canvas overlay alongside trend line candles with real-time updates. In Part 10, we add a per-bar sentiment box above each cand

**score 2:** //--- Identify the dominant side percentage for text color derivation    double winningPercentage = (footprint.delta > 0) ? footprint.upPercentage : footprint.downPercentage;    //--- Compute how far the dominant side exceeds 50%    double percentAbove50 = winningPercentage - 50;    //--- Clamp to zero so values below 50% do not produce negative ratios    if(percentAbove50 < 0) percentAbove50 = 0;    //--- Scale the excess to a 0–1 ratio for color intensity    double textRatio = MathCeil(percentAbove50) / 50.0;    //--- Assign the text color ma

**score 2:** //--- Default delta color to the weakest down shade                color deltaColor = downColor1;                if(barFootprints[footprintIndex].maxDeltaValue > 0 && total > 0)                  {                   //--- Derive delta color from signed delta relative to bar maximum                   deltaColor = GetVolumeColor(                                  deltaValue >= 0,                                  MathAbs(deltaValue) / barFootprints[footprintIndex].maxDeltaValue);                  }


## Tail
[Price Action Analysis Toolkit Development (Part 65): Building an MQL5 System to Monitor and Analyze Manually Drawn Fibonacci Levels](https://www.mql5.com/en/articles/21890)

The Fibonacci retracement tool is an essential component of price action analysis, providing critical levels for potential market reactions. However, its effectiveness is often limited by the need for continuous human monitoring, which can lead to missed setups. In this part of our series, we introduce a tool that synchronizes and actively monitors manually drawn Fibonacci levels using MQL5, combining discretionary insight with automated oversight.

[Introduction to MQL5 (Part 43): Beginner Guide to File Handling in MQL5 (V)](https://www.mql5.com/en/articles/21728)

The article explains how to use MQL5 structures with binary files to persist Expert Advisor parameters. It covers defining structures, accessing members, and distinguishing simple from complex layouts, then writing and reading entire records using FileWriteStruct and FileReadStruct in FILE BIN mode. You will learn safe patterns for fixed-size data and how shared storage (FILE COMMON) enables reuse across sessions and terminals.

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F117%3Futm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Dorder.expert%26utm_content%3Dorder.freelance%26utm_campaign%3D0622.MQL5.com.Internal&a=tunpwtbhegzufrqocbwiszessdutnobs&s=d9e7484e15300021b4066b1df77a94a1352f9e7c326d5113006bb4f6476bafeb&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=rrvwaptpngkewrsnoeudjrbwflyzfzsv&ssn=1788779117839104076&ssn_dr=0&ssn_sr=0&fv_date=1788779117&ref=https%3A%2F%2Fwww.mql5.c


---
# 21984: Creating Custom Indicators in MQL5 (Part 11): Enhancing the Footprint Chart with Market Structure and Order Flow Layers
HEADS: # Creating Custom Indicators in MQL5 (Part 11): Enhancing the Footprint Chart with Market Structure and Order Flow Layers | ### Introduction | ### Layering the Market — How Structure and Order Flow Combine Inside Each Bar | ### Implementation in MQL5 | ### Backtesting | ### Conclusion

## Intro
# Creating Custom Indicators in MQL5 (Part 11): Enhancing the Footprint Chart with Market Structure and Order Flow Layers

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Trading systems](https://www.mql5.com/en/articles/mt5/trading_systems) | 9 April 2026 at 04:18

4 701 [ 1](https://www.mql5.com/en/forum/508110 "Comments")

[Allan Munene Mutiiria](https://www.mql5.com/en/users/29210372)

A [footprint](https://en.wikipedia.org/wiki/Order_flow_trading "https://en.wikipedia.org/wiki/Order_flow_trading") chart displays volume at each price level, but without market structure context it is difficult to identify where the most volume traded within a bar, where aggressive one-sided pressure occurred across consecutive levels, or whether a bar absorbed heavy volume without moving. This article is for [MetaQuotes Language 5](https://www.metaquotes.net/en/metatrader5/algorithmic-trading/mql5 "https://www.metaquotes.net/en/metatrader5/algorithmic-trading/mql5") (MQL5) developers and algorithmic traders looking to enhance the footprint chart with structural and order flow analytical lay


## Key hits
**score 2:** In our [previous article (Part 10)](https://www.mql5.com/en/articles/21829), we enhanced the MQL5 footprint chart indicator by adding a per-bar volume sentiment information box with delta-intensity color coding, supersampled rounded corners, and alpha compositing. In Part 11, we introduce volume profile bars, point of control and value area highlighting, stacked imbalance detection, absorption zone classification, single print markers, a cumulative volume delta panel, and a delta histogram. This article will cover the following topics:

**score 2:** The distribution of volume across price levels shows where participants were most active. The level with the highest combined volume is the point of control. It often acts as the bar's center of activity and a likely reaction level. The value area is the price range around the [point of control](https://optimusfutures.com/blog/point-of-control-explained-the-most-important-level-on-volume-profile-futurestrading-daytrading/ "https://optimusfutures.com/blog/point-of-control-explained-the-most-important-level-on-volume-profile-futurestrading-daytra

**score 2:** Stacked imbalances occur when ask volume at a level significantly outweighs bid volume at the level directly below it, or vice versa, across multiple consecutive rows. When this pattern stacks three or more levels deep, it signals a directional pressure zone where one side was repeatedly aggressive without meaningful opposition. Absorption is the opposite condition — a bar with high total volume but a net delta close to zero, meaning that one side absorbed the aggression of the other without allowing the price to move, often preceding a reversa

**score 2:** In live trading, use the point of control as a reference for mean-reversion entries — price returning to a prior bar's point of control after a deviation is a high-probability area for reaction. Watch for value area overlaps between consecutive bars to identify accepted price zones worth defending. Use stacked ask imbalances as directional fuel indicators, entering longs when price holds above a stacked ask zone. Flag absorption bars at key levels as potential reversal candidates, especially when the cumulative volume delta diverges from price 

**score 2:** input group "Colors" input color upColor1       = 0x8d8d8d; input color upColor2       = 0x6b8bb6; input color upColor3       = 0x5289d3; input color upColor4       = 0x2e7de6; input color upColor5       = 0x0077ff; input color downColor1     = 0x8d8d8d; input color downColor2     = 0xb87b6c; input color downColor3     = 0xd46d53; input color downColor4     = 0xec5732; input color downColor5     = 0xfe3300; input color volumeColor1   = 0x636363; input color volumeColor2   = 0x858585; input color volumeColor3   = 0xa3a3a3; input color volumeColo

**score 2:** The cumulative delta group introduces the cumulative volume delta panel toggle, panel height, positive and negative line colors, the per-bar delta histogram toggle, and its height. The colors group retains all existing inputs and adds dedicated colors for the point of control line, value area fill, stacked ask and bid imbalance highlights, absorption zones, and single print borders. The information box group retains all previous inputs and adds a toggle for the mini buy and sell percentage bar inside the box. Finally, the filters group adds a d

**score 2:** The "BarFootprintData" structure retains all fields from the previous version and gains nine new ones to support the additional layers. We add the point of control index to reference the highest-volume level directly, value area high and low indices to define the accepted value boundary, and the cumulative delta to carry the running net delta total forward from bar to bar. Four fields track stacked imbalance detection: boolean flags for ask and bid stacking, and integer start indices that tell the renderer exactly where the imbalance zone begin

**score 2:** The new visual layers require smooth color transitions between states — for example, graduating volume profile bar colors or blending imbalance highlights against existing canvas content. Rather than snapping between fixed color values, we introduce a linear interpolation function that produces any shade between two colors based on a normalized factor.


## Tail
[From Simple Close Buttons to a Rule-Based Risk Dashboard in MQL5](https://www.mql5.com/en/articles/21842)

Build a rule-based on-chart risk management panel in MetaTrader 5 using the MQL5 Standard Library. The guide covers a CAppDialog-based GUI, manual event routing, and an automated update loop. You will bind UI events to CTrade to execute conditional closures, show net floating P/L, and read automated targets directly from the chart.

[Building a Correlation-Aware Multi-EA Portfolio Scorer in MQL5](https://www.mql5.com/en/articles/21955)

Most algo traders optimize Expert Advisors individually but never measure how they behave together on a single account. Correlated strategies amplify drawdowns instead of reducing them, and coverage gaps leave portfolios blind during entire trading sessions. This article builds a complete portfolio scorer in MQL5 that reads daily P&L from backtest CSV files, computes a full Pearson correlation matrix, maps trading activity by hour and weekday, evaluates asset class diversity, and outputs a composite grade from A+ to F. All source code is includ

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F22768&a=asavypypfjiefdywsbundfnovsqdqrlg&s=822a63e372eca09eaaa973cc0f82be5093d6c353237035cd7209bf509f0bbb1e&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=oejizsheujfpsazlefyysrsothjcjuvb&ssn=1788778976637319800&ssn_dr=0&ssn_sr=0&fv_date=1788778976&ref=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F21984&back_ref=https%3A%2F%2Fwww.google.com%2F&title=Creating%20Custom%20Indicators%20in%20MQL5%20(Part%2011)%3A%20Enhancing%20the%20


---
# 2612: Testing trading strategies on real ticks
HEADS: # Testing trading strategies on real ticks | ### Trading strategy | ### Testing | ### Comparing results of different test modes | ### | ### Trading systems depending on ticks | ### | ### Four tick generation modes | ### Start developing a system with "1 minute OHLC" mode | ### Next step – debugging and "Every tick" mode | ### Accuracy vs speed

## Intro
# Testing trading strategies on real ticks

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Examples](https://www.mql5.com/en/articles/mt5/examples) | 4 August 2016 at 06:44

100 908 [ 8](https://www.mql5.com/en/forum/93267 "Comments")

[MetaQuotes](https://www.mql5.com/en/users/metaquotes)

The article provides the results of testing a simple trading strategy in three modes: "**1 minute OHLC**" using only Open, High, Low and Close prices of minute bars; [detailed modeling](https://www.mql5.com/en/articles/75) in "**Every tick**" mode, as well as the most accurate "**Every tick based on real ticks**" mode applying actual historical data.


## Key hits
**score 1:** If preliminary results are satisfactory, you can continue debugging and analyzing the trading system using more accurate simulation modes. Here is where the strategy debugging in test mode comes in handy allowing you to set breakpoints and check the status of variables as well as execution of built-in conditions. You may stumble upon unpleasant surprises here if you have not considered some nuances of your system beforehand.

**score 0:** The article provides the results of testing a simple trading strategy in three modes: "**1 minute OHLC**" using only Open, High, Low and Close prices of minute bars; [detailed modeling](https://www.mql5.com/en/articles/75) in "**Every tick**" mode, as well as the most accurate "**Every tick based on real ticks**" mode applying actual historical data.

**score 0:** Comparing the results allows us to assess the quality in various modes, as well as helps us to use the tester more efficiently in order to receive results faster. "1 minute OHLC" mode allows receiving quick estimated test results, "Every tick" mode is closer to reality, while testing on real ticks is most accurate but time-consuming. Keep in mind that errors in a trading robot's logic may affect the number of trading operations making the strategy test results more susceptible to a selected test mode.

**score 0:** An open position is closed after BarsForExit bars. As you can see, the rules are quite simple. See the screenshot below for more clarity:

**score 0:** Now, let's see how the EA test results change when applying one of the three different tick modeling modes.

**score 0:** ### Comparing results of different test modes

**score 0:** Test results in different modes are displayed in the table. The first thing that catches the eye is the difference in the number of trading operations. Thus, all other test results are also different. Testing in "1 minute OHLC" took 1.57 seconds which is 23 times faster than in "Every tick" mode. Such a difference is important when optimizing the trading system inputs.

**score 0:** The balance and equity graphs are different as well. As we can see, this simple strategy is not impressive – growth periods are followed by drawdowns and the test graphs look more like a chain of coincidences. The strategy is certainly not suitable for real trading since results are similar to a coin toss.


## Tail
[Graphical Interfaces VIII: The Calendar Control (Chapter 1)](https://www.mql5.com/en/articles/2537)

In the part VIII of the series of articles dedicated to creating graphical interfaces in MetaTrader, we will consider complex composite controls like calendars, tree view, and file navigator. Due to the large amount of information, there are separate articles written for every subject. The first chapter of this part describes the calendar control and its expanded version — a drop down calendar.

[The checks a trading robot must pass before publication in the Market](https://www.mql5.com/en/articles/2555)

Before any product is published in the Market, it must undergo compulsory preliminary checks in order to ensure a uniform quality standard. This article considers the most frequent errors made by developers in their technical indicators and trading robots. An also shows how to self-test a product before sending it to the Market.

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F523%3Futm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Dchoose.signals%26utm_content%3Dsubscribe.signal%26utm_campaign%3D0622.MQL5.com.Internal&a=fyznzyduwsltgnhlftytumasbfgbwlqw&s=91bc0eca8f132d3df7d14cdb1baebac753aef179403d60dc83856af55a4d6769&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=byguomegylvpbgvztbtncdhtczijqxhi&ssn=1788804932698147436&ssn_dr=0&ssn_sr=0&fv_date=1788804932&ref=https%3A%2F%2Fwww.mql


---
# 11106: Developing a Replay System — Market simulation (Part 17): Ticks and more ticks (I)
HEADS: # Developing a Replay System — Market simulation (Part 17): Ticks and more ticks (I) | ### Introduction | ### Implementing the first version | ### Modifying the C\_Replay class | ### Final considerations

## Intro
# Developing a Replay System — Market simulation (Part 17): Ticks and more ticks (I)

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Examples](https://www.mql5.com/en/articles/mt5/examples) | 30 November 2023 at 11:10

3 741 [ 2](https://www.mql5.com/en/forum/458282 "Comments")

[Daniel Jose](https://www.mql5.com/en/users/dj_tlog_831)

In the previous article "[Developing a Replay System — Market simulation (Part 16): New class system](https://www.mql5.com/en/articles/11095)", we have made the necessary changes to the C\_Replay class. These changes are intended to simplify several tasks that we will need to complete. Thus, the C\_Replay class, which was once too large, went through a simplification process in which its complexity was distributed among other classes. This makes it much simpler and easier to implement new functionality and improvements to the replay/simulation system. Starting with this article, these improvements will begin to appear and extend to the next seven articles.


## Key hits
**score 1:** Here we will begin to implement this system, but in the simplest possible way. First, we will make it appear in the Market Watch window (Fig. 01). After that, we will try to make it appear in other places. Getting it to appear in the Market Watch window will be a challenge. At the same time, it will be interesting, since when we implement and use the simulation of movements with an interval of 1 minute, the tick chart in the "Market Watch" window will display the RANDOM WALK created by the tester. This is all very interesting.

**score 1:** Print("Loading ticks for replay. Please wait...");                                 ArrayResize(m_Ticks.Info, def_MaxSizeArray, def_MaxSizeArray);                                 i0 = m_Ticks.nTicks;                                 while ((!FileIsEnding(m_File)) && (m_Ticks.nTicks < def_LIMIT) && (!_StopFlag))                                 {                                         ArrayResize(m_Ticks.Info, m_Ticks.nTicks + 1, def_MaxSizeArray);                                         szInfo = FileReadString(m_File) + " " + FileReadString(m_Fil

**score 1:** for(int c0 = 0; m_Ticks.Info[c0].volume_real == 0; c0++)                                         rate[0].close = m_Ticks.Info[c0].last;                                 rate[0].open = rate[0].high = rate[0].low = rate[0].close;                                 rate[0].tick_volume = 0;                                 rate[0].real_volume = 0;                                 rate[0].time = m_Ticks.Info[0].time - 60;                                 CustomRatesUpdate(def_SymbolReplay, rate);                                 m_ReplayCount = 0;          

**score 1:** if (m_MountBar.bNew = (m_MountBar.memDT != macroRemoveSec(m_Ticks.Info[m_ReplayCount].time)))                                 {                                         if (bViewMetrics)                                         {                                                 _mdt = (_mdt > 0 ? GetTickCount64() - _mdt : _mdt);                                                 i = (int) (_mdt / 1000);                                                 Print(TimeToString(m_Ticks.Info[m_ReplayCount].time, TIME_SECONDS), " - Metrica: ", i / 60, ":", i % 

**score 1:** if (m_MountBar.memDT != macroRemoveSec(m_Ticks.Info[m_ReplayCount].time))                                 {                                                                        if (bViewMetrics) Metrics();                                         m_MountBar.memDT = macroRemoveSec(m_Ticks.Info[m_ReplayCount].time);                                         def_Rate.real_volume = 0;                                         def_Rate.tick_volume = 0;                                 }                                 bNew = (def_Rate.tick_volume == 0);

**score 1:** We need to organize our work better. The code is growing, and if this is not done now, then it will become impossible. Let's divide and conquer. MQL5 allows the use of classes which will assist in implementing this task, but for this we need to have some knowledge about classes. Probably the thing that confuses beginners the most is inheritance. In this article, we will look at how to use these mechanisms in a practical and simple way.

**score 0:** This chart appears in several places in the MetaTrader 5 platform. To give you an idea of these places, I will mention a few places that are included in the standard version of MetaTrader 5. For example, the Market Watch window, as shown in Figure 01. The Depth of Market (Fig. 02), and the order system (Fig. 03).

**score 0:** Let's start implementing the craziest thing of all, given the degree of complexity. In the system that will be implemented, in the first moments we will not use simulated data. Therefore, the attachment to this articles contains **REAL** data for 2 days on 4 different assets so that we have at least a basis for experiments. You don't have to trust me, quite the contrary. I want you to collect real market data yourself and test it in the system yourself. This way we can draw our own conclusions about what is actually happening before we implemen


## Tail
[Neural networks made easy (Part 53): Reward decomposition](https://www.mql5.com/en/articles/13098)

We have already talked more than once about the importance of correctly selecting the reward function, which we use to stimulate the desired behavior of the Agent by adding rewards or penalties for individual actions. But the question remains open about the decryption of our signals by the Agent. In this article, we will talk about reward decomposition in terms of transmitting individual signals to the trained Agent.

[Neural networks made easy (Part 52): Research with optimism and distribution correction](https://www.mql5.com/en/articles/13055)

As the model is trained based on the experience reproduction buffer, the current Actor policy moves further and further away from the stored examples, which reduces the efficiency of training the model as a whole. In this article, we will look at the algorithm of improving the efficiency of using samples in reinforcement learning algorithms.

Speed up your trading Use our high-speed VPS for MetaTrader 4 and 5 Learn more](https://www.mql5.com/ff/go?link=https://www.mql5.com/en/vps&a=qtrrsuiwuicrscmckjynyanztbditglq&s=c617dc80d90cfd3783ec1345eec2b419b281f10fec6eac77b3218984ac337259&uid=&ref=https://www.mql5.com/en/articles/11106&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=6450785525975113554)


---
# 11113: Developing a Replay System — Market simulation (Part 18): Ticks and more ticks (II)
HEADS: # Developing a Replay System — Market simulation (Part 18): Ticks and more ticks (II) | ### Introduction | ### Implementing a correction for the 1-minute bar creation time | ### Implementing fixes in the quick navigation system | ### Using simulated data in Market Watch | ### Conclusion

## Intro
# Developing a Replay System — Market simulation (Part 18): Ticks and more ticks (II)

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Tester](https://www.mql5.com/en/articles/mt5/strategy_tester) | 8 December 2023 at 02:43

2 778 [ 0](https://www.mql5.com/en/forum/458656 "Comments")

[Daniel Jose](https://www.mql5.com/en/users/dj_tlog_831)

In the previous article, "[Developing a Replay System — Market simulation (Part 17): Ticks and more ticks (I)](https://www.mql5.com/en/articles/11106)", we have added the capability to display a tick chart in the Market Watch system. This was a very positive development, but in that article I mentioned that our system had some shortcomings. Therefore, I decided to disable some functions of the service until the shortcomings are corrected. Now we will fix many of the errors that arose when we started displaying the tick chart.


## Key hits
**score 2:** Look how interesting it is. By adding a certain level of randomness to the system, we have enabled the inclusion of direct orders. That is, of the orders that will be executed without changing the BID or ASK. In the real market, such orders do not occur very often, and not in the form in which the system will display them. But if we ignore this fact, we will already have a good system in which at times there will be a small spread between BID and ASK included. In other words, the simulator practically adapts to a much more common situation in t

**score 2:** Here we control the level of complexity of random generation. This is done to keep everything within a certain degree of contingency. We will have direct orders from time to time. But this will be done in more controlled quantities. To do this, we will simply adjust these values here. By adjusting them, we create a small window in which the spread is likely to be slightly larger than the minimum possible value. As a result, from time to time, we will deal with direct orders generated by the modeling system, something that was not possible in pr

**score 1:** if (m_MountBar.memDT != macroRemoveSec(m_Ticks.Info[m_ReplayCount].time))                                 {                                                                        if (bViewMetrics) Metrics();                                         m_MountBar.memDT = (datetime) macroRemoveSec(m_Ticks.Info[m_ReplayCount].time);                                         def_Rate.real_volume = 0;                                         def_Rate.tick_volume = 0;                                 }                                 bNew = (def_Rate.tick_vo

**score 1:** **NOTE:** So don't ever believe that you can and will always operate within the spread. Sometimes the system can go beyond the spread. It is important that you know this because when developing an order system, this information and its proper understanding will be critical.

**score 1:** ArrayResize(m_Ticks.Rate, (m_Ticks.nRate > 0 ? m_Ticks.nRate + 3 : def_BarsDiary), def_BarsDiary);                                 m_Ticks.Rate[++m_Ticks.nRate] = rate;                                 max = rate.tick_volume - 1;                                      v0 = 4.0;                                 v1 = (60000 - v0) / (max + 1.0);                                 for (int c0 = 0; c0 <= max; c0++, v0 += v1)                                 {                                         tick[c0].last = 0;                                         

**score 1:** if (m_MountBar.memDT != macroRemoveSec(m_Ticks.Info[m_ReplayCount].time))                                 {                                                                        if (bViewMetrics) Metrics();                                         m_MountBar.memDT = (datetime) macroRemoveSec(m_Ticks.Info[m_ReplayCount].time);                                         def_Rate.real_volume = 0;                                         def_Rate.tick_volume = 0;                                 }                                 bNew = (def_Rate.tick_vo

**score 1:** We have a pretty simple change here. This change is intended just for creating and displaying BID and ASK values. But keep in mind that this creation is based on the value of the last deal price and will only be done when we are dealing with simulated values. By running this code, we will get an internal representation of the graph generated by the RANDOM WALK system, just like we did when we used EXCEL to do it. When, in the article "[Developing a Replay System — Market simulation (Part 15): Birth of the SIMULATOR (V) - RANDOM WALK](https://ww

**score 1:** dSpread = m_PointsPerTick + ((iRand > 29080) && (iRand < 32767) ? ((iRand & 1) == 1 ? m_PointsPerTick : 0 ) : 0 );                                                 if (tick[0].last > ASK)                                                 {                                                         ASK = tick[0].ask = tick[0].last;                                                         BID = tick[0].bid = tick[0].last - dSpread;                                                         BID = tick[0].bid = tick[0].last - (m_PointsPerTick * ((rand() & 1)


## Tail
[Developing a Replay System — Market simulation (Part 19): Necessary adjustments](https://www.mql5.com/en/articles/11125)

Here we will prepare the ground so that if we need to add new functions to the code, this will happen smoothly and easily. The current code cannot yet cover or handle some of the things that will be necessary to make meaningful progress. We need everything to be structured in order to enable the implementation of certain things with the minimal effort. If we do everything correctly, we can get a truly universal system that can very easily adapt to any situation that needs to be handled.

[Data label for time series mining (Part 4)：Interpretability Decomposition Using Label Data](https://www.mql5.com/en/articles/13218)

This series of articles introduces several time series labeling methods, which can create data that meets most artificial intelligence models, and targeted data labeling according to needs can make the trained artificial intelligence model more in line with the expected design, improve the accuracy of our model, and even help the model make a qualitative leap!

Powerful analytics for traders of any level All the necessary trading reports for beginners and professionals](https://www.mql5.com/ff/go?link=https://www.mql5.com/en/forum/454106&a=muccpajyfystoakuukdobwigjejzmpqn&s=52daad60fa795e635264e6f94898f05493bca3b5124d4cca8eb7e82333c2ef12&uid=&ref=https://www.mql5.com/en/articles/11113&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=6403830018622512976)


---
# 23465: Exporting Symbol Tick Data to Binary Files in MQL5 for Offline Analysis
HEADS: # Exporting Symbol Tick Data to Binary Files in MQL5 for Offline Analysis | ### Introduction | ### | ### Why Binary for Tick Data | ### | ### The Binary File Format | ### | ### The MQL5 Tick Data API | ### | ### Binary File I/O in MQL5 | ### | ### Implementation — TickRecord.mqh | ### | ### Implementation — TickFileHeader.mqh

## Intro
# Exporting Symbol Tick Data to Binary Files in MQL5 for Offline Analysis

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Statistics and analysis](https://www.mql5.com/en/articles/mt5/statistics) | 6 August 2026 at 08:02

678 [ 0](https://www.mql5.com/en/forum/514071 "Comments")

[Ushana Kevin Iorkumbul](https://www.mql5.com/en/users/iorkumbulushana)

MetaTrader 5 stores complete tick history for every symbol in the terminal's data cache. Every bid change, ask change, and trade print that arrived during the terminal's connected lifetime is accessible through MQL5's tick history API. That data is valuable for offline analysis: spread distribution studies, microstructure research, feed quality audits, input generation for machine learning models, and backtesting at tick resolution with external tools. The problem is that extracting it in a form that external tools can read efficiently is not straightforward.


## Key hits
**score 2:** The obvious approach is to export ticks to CSV. A CSV file is human-readable and universally supported, but it has serious practical limitations for tick data. A single active trading day for a major forex pair can produce several million ticks. At around 60 bytes per tick in CSV format, one trading day fills roughly 180 MB. Reading and parsing that file in Python or R requires string-buffer allocations, delimiter splits, and per-field text-to-float conversion. Only then do you get usable numeric data. Floating-point values printed as text lose

**score 2:** - time — server time in seconds (datetime) - bid — bid price (double) - ask — ask price (double) - last — last trade price (double) - volume — tick volume (ulong) - time\_msc — server time in milliseconds (long) - flags — bitmask indicating which fields changed in this tick (uint) - volume\_real — real volume (double, exchange instruments only)

**score 2:** Tick record layout (48 bytes, little-endian):   int64    time_msc   millisecond timestamp   float64  bid        bid price   float64  ask        ask price   float64  last       last trade price (0 for forex)   uint64   volume     tick volume   uint32   flags      ENUM_TICK_FLAG bitmask   uint32   padding    always zero

**score 2:** # NumPy dtype matching the 48-byte CTickRecord binary layout TICK_DTYPE = np.dtype([     ('time_msc', '<i8'),   # 8 bytes: millisecond timestamp (signed)     ('bid',      '<f8'),   # 8 bytes: bid price     ('ask',      '<f8'),   # 8 bytes: ask price     ('last',     '<f8'),   # 8 bytes: last trade price     ('volume',   '<u8'),   # 8 bytes: tick volume (unsigned)     ('flags',    '<u4'),   # 4 bytes: ENUM_TICK_FLAG bitmask     ('padding',  '<u4'),   # 4 bytes: always zero ])  # total: 48 bytes per record

**score 2:** spread_points = (valid['ask'] - valid['bid']) / pip     print(f"\nSpread statistics ({len(valid)} ticks with bid and ask, in points):")     print(f"  min    = {spread_points.min():.1f}")     print(f"  p25    = {np.percentile(spread_points, 25):.1f}")     print(f"  median = {np.median(spread_points):.1f}")     print(f"  p75    = {np.percentile(spread_points, 75):.1f}")     print(f"  max    = {spread_points.max():.1f}")     print(f"  mean   = {spread_points.mean():.2f}")

**score 2:** The Python reader uses two mechanisms. struct.unpack() with the format string '<IHH20sqqQ12s' decodes the 64-byte header field by field, where < specifies little-endian byte order and each letter maps to a field type and size. np.frombuffer() with the TICK\_DTYPE structured dtype loads all tick records in a single call with no loop, producing a NumPy array whose columns are named and typed. Accessing ticks['bid'] returns a 64-bit float array over the entire tick set, enabling vectorized spread calculations, histogram binning, and percentile sta

**score 2:** The honest limitations are the dependency on the terminal's tick history cache being populated for the requested date range, the absence of chunked fetching for very large ranges, the little-endian-only format, the omission of volume\_real, and the static snapshot nature of the export.

**score 1:** MetaTrader 5 stores complete tick history for every symbol in the terminal's data cache. Every bid change, ask change, and trade print that arrived during the terminal's connected lifetime is accessible through MQL5's tick history API. That data is valuable for offline analysis: spread distribution studies, microstructure research, feed quality audits, input generation for machine learning models, and backtesting at tick resolution with external tools. The problem is that extracting it in a form that external tools can read efficiently is not s


## Tail
[Artificial Coronary Circulation Algorithm (ACCS)](https://www.mql5.com/en/articles/19861)

A metaheuristic algorithm that simulates the growth of coronary arteries in the human heart for optimization problems. It uses the principles of angiogenesis (the growth of new blood vessels), bifurcation (branching), and pruning of weak branches to find optimal solutions in a multidimensional space. Testing its effectiveness across a wide range of tasks yielded unexpected results.

[Neural Networks in Trading: Effective Feature Extraction for Accurate Classification (Building Objects)](https://www.mql5.com/en/articles/18307)

Mantis is a versatile tool for in-depth time series analysis that can be flexibly scaled to accommodate any financial scenario. Learn how a combination of patching, local convolutions, and cross-attention enables a highly accurate interpretation of market patterns.

Explore your trading for free Updated statistics in MetaTrader 5 will help you to thoroughly evaluate results and reduce risks Learn more](https://www.mql5.com/ff/go?link=https://www.mql5.com/en/forum/454106&a=bkbqgaxtrafeuegfvjisjjwjohagrvnr&s=25c5856d7857fc6b6db7cffb15ae4ce40fd19d1ab594d8a900ad65673d9ffa0e&uid=&ref=https://www.mql5.com/en/articles/23465&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=5121414300853470153)


---
# 22460: Creating a Custom Tick Chart in MQL5
HEADS: # Creating a Custom Tick Chart in MQL5 | ### Table of Contents | ### **Introduction** | ### **Project Overview and Implementation Plan** | ### **Creating a Custom Tick Chart in MQL5** | ### **Conclusion**

## Intro
[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Indicators](https://www.mql5.com/en/articles/mt5/examples_indicators) | 11 May 2026 at 11:34

3 145 [ 0](https://www.mql5.com/en/forum/509631 "Comments")

[Israel Pelumi Abioye](https://www.mql5.com/en/users/13467913)

- [Introduction](https://www.mql5.com/en/articles/22460#introduction) - [Project Overview and Implementation Plan](https://www.mql5.com/en/articles/22460#project_overview_and_implementation_plan)

- [What We Are Building](https://www.mql5.com/en/articles/22460#tag2a) - [Implementation Plan](https://www.mql5.com/en/articles/22460#tag2b)


## Key hits
**score 3:** To ensure uniformity across all bars, the tick volume is subsequently allocated depending on the predetermined number of ticks per candle. Since spread and real volume are not necessary in this unique tick-based structure, they are set to zero. Using CustomRatesUpdate, the finished candle is transmitted to the custom symbol. This crucial stage enables the candle to appear on the chart by pushing the completed OHLC data into TICK\_101. An error notice is given so that the problem can be found if this update fails for any reason.

**score 2:** //--- Final OHLC values for completed bar    rates[0].time        = bar_time;    rates[0].open        = open_price;    rates[0].high        = high_price;    rates[0].low         = low_price;    rates[0].close       = close_price;    rates[0].tick_volume = InpTicksPerBar;  // fixed tick count    rates[0].spread      = 0;    rates[0].real_volume = 0;

**score 2:** //--- Populate current candle structure    rates[0].time        = bar_time;    rates[0].open        = open_price;    rates[0].high        = high_price;    rates[0].low         = low_price;    rates[0].close       = close_price;    rates[0].tick_volume = (long)tick_count;  // number of ticks so far    rates[0].spread      = 0;    rates[0].real_volume = 0;

**score 1:** MetaTrader 5 organizes price data using fixed time intervals, which often hides the true intensity of market activity. A one-minute candle formed from hundreds of ticks can appear identical to one created from only a few trades. For scalpers and tick-driven systems, this becomes a major limitation because MetaTrader 5 does not provide a native tick-bar chart.

**score 1:** Acceptance criteria you can check in the terminal: the custom symbol appears in Market Watch, its chart displays a continually updating live candle, and each candle closed contains exactly the configured number of ticks and an increasing timestamp. This architecture gives you an activity‑driven view of price action, improving visibility of momentum and micro‑structure. From here you can extend the EA with volume handling, persistent storage, different aggregation rules (eg, tick‑volume weighted), or hooks for strategy testing that require tick‑

**score 0:** - [Conclusion](https://www.mql5.com/en/articles/22460#conclusion)

**score 0:** This article shows how to produce activity‑driven candles that close after N ticks instead of after a clock interval. You will get a clear, executable goal: an EA that creates and configures a separate custom symbol, aggregates incoming ticks into OHLC bars of a user‑defined size (ticks‑per‑bar), assigns monotonic bar timestamps, and updates the forming candle in real time using CustomRatesUpdate. Inputs include the custom symbol name, ticks‑per‑bar, and an option to auto‑open the chart. The result is a live tick chart in MetaTrader 5 where eac

**score 0:** This article was written by a user of the site and reflects their personal views. MetaQuotes Ltd is not responsible for the accuracy of the information presented, nor for any consequences resulting from the use of the solutions, strategies or recommendations described.


## Tail
[Exploring Conformal Forecasting of Financial Time Series](https://www.mql5.com/en/articles/18324)

In this article, we will consider conformal predictions and the MAPIE library that implements them. This approach is one of the most modern ones in machine learning and allows us to focus on risk management for existing diverse machine learning models. Conformal predictions, by themselves, are not a way to find patterns in data. They only determine the degree of confidence of existing models in predicting specific examples and allow filtering for reliable predictions.

[MetaTrader 5 Machine Learning Blueprint (Part 15): How to Calibrate Profit-Taking and Stop-Loss Targets from Synthetic Data](https://www.mql5.com/en/articles/22275)

This article applies the Optimal Trading Rule from AFML Chapter 13 to set profit targets and stop-losses without in-sample calibration. We model post-entry P&L with a discrete Ornstein–Uhlenbeck process, run a 100,000-path search, and implement Python, multiprocessing, and a Numba @njit parallel kernel (242× faster). The result is an optimal (PT, SL) under three forecast specifications, constrained by the prop-firm daily loss limit.

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Fsignals%2Fmt5%2Fpage1%3Fpreset%3D2%26utm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Dmax.profit.signals%26utm_content%3Dsubscribe.signal%26utm_campaign%3D0622.MQL5.com.Internal&a=hgyovyikvykcdukcncnktswvlctghemf&s=545653d14172edfb3c9c02ca8e948778c29f9c1b70be9a587e8d4b040fb23539&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=ujayiemwvtrmtatbigdetykgqdolanzw&ssn=1788778439619614097&ssn_dr=0&ssn_sr=0&fv_date=1788778439&r


---
# 18680: MetaTrader tick info access from MQL5 services to Python application using sockets
HEADS: # MetaTrader tick info access from MQL5 services to Python application using sockets | ### Introduction | ### Program Flow | ### Why services and python? | ### Services Program | ### Python Server Program | ### Python Client Program | ### Demo of Data Flow | ### Conclusion

## Intro
# MetaTrader tick info access from MQL5 services to Python application using sockets

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Trading systems](https://www.mql5.com/en/articles/mt5/trading_systems) | 28 July 2025 at 10:41

3 774 [ 5](https://www.mql5.com/en/forum/492029 "Comments")

[Ramesh Maharjan](https://www.mql5.com/en/users/lazymesh)

Sometimes everything is not programmable in the MQL5 language. And even if it is possible to convert existing advanced libraries in MQL5, it would be time-consuming. A better option is to integrate or utilize the existing libraries to achieve a task. For example, there are numerous machine-learning-libraries in python. It's not the best option for us to create identical copies in MQL5 form just to achieve a machine learning task for trading. It is better to export the data needed for that python machine learning library, do the necessary process in the python environment and import the result back into the MQL5 program. This article is about transporting such data from the MetaTrader termina


## Key hits
**score 1:** With the introduction of Berkeley sockets in the 4.2BSD Unix operating system in 1983, communication between machines became easy and widespread. More advanced application layer libraries and protocols all depend on transport level socket protocols, which we are going to use in this article.

**score 0:** Sometimes everything is not programmable in the MQL5 language. And even if it is possible to convert existing advanced libraries in MQL5, it would be time-consuming. A better option is to integrate or utilize the existing libraries to achieve a task. For example, there are numerous machine-learning-libraries in python. It's not the best option for us to create identical copies in MQL5 form just to achieve a machine learning task for trading. It is better to export the data needed for that python machine learning library, do the necessary proces

**score 0:** As you can see from the figure, the MetaTrader service program is connected to a python server listening on port 9070. All the tick data of the charts that are open in MetaTrader 5 terminal, will be sent to the python server at port 9070. The Python server then analyzes the data received from MetaTrader 5, does the necessary analysis on the data and distributes or better say broadcasts the tick info to the connected clients. The clients can then use the received data to perform necessary tasks or apply algorithms to achieve the desired result, 

**score 0:** I programmed the server in such a way that only one MetaTrader 5 is allowed to connect and communicate. This is done to avoid mismanagement and havoc conditions that may arise for multiple MetaTrader 5 connections. On the other hand, clients are to receive the tick data for further processing, the same data can be utilized by different clients for different algorithms to be applied to achieve the desired result. Thus, there is a need to manage the client connections.

**score 0:** Sending data to clients is straightforward. If an error occurs while sending data, then the client is removed from the connected clients list assuming the client is not connected and the dictionary is updated.

**score 0:** This article was written by a user of the site and reflects their personal views. MetaQuotes Ltd is not responsible for the accuracy of the information presented, nor for any consequences resulting from the use of the solutions, strategies or recommendations described.


## Tail
[Market Profile indicator (Part 2): Optimization and rendering on canvas](https://www.mql5.com/en/articles/16579)

The article considers an optimized version of the Market Profile indicator, where rendering with multiple graphical objects is replaced with rendering on a canvas - an object of the CCanvas class.

[Implementing Practical Modules from Other Languages in MQL5 (Part 03): Schedule Module from Python, the OnTimer Event on Steroids](https://www.mql5.com/en/articles/18913)

The schedule module in Python offers a simple way to schedule repeated tasks. While MQL5 lacks a built-in equivalent, in this article we’ll implement a similar library to make it easier to set up timed events in MetaTrader 5.

How AI helps create robots for MetaTrader 5 Learn from our book "Neural Networks in Algo Trading with MQL5" Read](https://www.mql5.com/ff/go?link=https://www.mql5.com/en/neurobook%3Futm_source=www.mql5.com%26utm_medium=display%26utm_term=read.neurobook%26utm_content=visit.page%26utm_campaign=neurobook.promo.04.2024&a=ghrobswocqgvhztzjldphupateyllpro&s=9929cb0b8629585b5a42fabc06c525e41f6c0ebdf3045d044a5413b93ea88b47&uid=&ref=https://www.mql5.com/en/articles/18680&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=6346153925006734624)


---
# 20327: Analytical Volume Profile Trading (AVPT): Liquidity Architecture, Market Memory, and Algorithmic Execution
HEADS: # Analytical Volume Profile Trading (AVPT): Liquidity Architecture, Market Memory, and Algorithmic Execution | ### Table of contents: | ### Introduction | ### | ### System Overview and Understanding | ### Getting Started | ### **Back Test Results** | ### Conclusion

## Intro
# Analytical Volume Profile Trading (AVPT): Liquidity Architecture, Market Memory, and Algorithmic Execution

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Examples](https://www.mql5.com/en/articles/mt5/examples) | 24 November 2025 at 03:32

11 291 [ 9](https://www.mql5.com/en/forum/500657 "Comments")

[Hlomohang John Borotho](https://www.mql5.com/en/users/johnhlomohang)

1. [Introduction](https://www.mql5.com/en/articles/20327#introduction) 2. [System Overview and Understanding](https://www.mql5.com/en/articles/20327#system_overview_and_understanding) 3. [Getting Started](https://www.mql5.com/en/articles/20327#getting_started) 4. [Backtest Results](https://www.mql5.com/en/articles/20327#back_test_results) 5. [Conclusion](https://www.mql5.com/en/articles/20327#conclusion)


## Key hits
**score 4:** In conclusion, AVPT gives traders a more intelligent and context-aware approach to execution: trades are no longer triggered solely by patterns or indicators, but by understanding where real liquidity sits and how markets “remember” past imbalances. By integrating market memory, volume clustering, and algorithmic decision-making, traders gain a framework that improves precision, enhances risk placement, and reduces noise-driven signals.

**score 3:** As algorithmic trading increasingly dominates global markets, understanding the distribution of volume across price levels becomes a decisive edge. AVPT combines microstructure analysis with automation, allowing traders to interpret liquidity imbalances in real time and execute with surgical precision. By turning raw volume into actionable structure, this approach transforms chaotic market activity into a readable blueprint for trend detection, breakout anticipation, and reversal timing.

**score 3:** We start by defining all the configurable inputs that shape how the Volume Profile engine and trading logic operate. The first group specifies profile-related parameters such as the number of lookback bars to analyze, the percentage used to compute the Value Area, and thresholds for identifying High-Volume Nodes and Low-Volume Nodes. The trading settings section then establishes risk and position-management controls—including lot size, ATR-based stop loss, risk-reward ratio, and trailing-stop behavior—giving the EA flexibility in adapting to vo

**score 2:** # Analytical Volume Profile Trading (AVPT): Liquidity Architecture, Market Memory, and Algorithmic Execution

**score 2:** With institutional order flow constantly redrawing the landscape of liquidity, traders must rely on methods that map the underlying structure of participation rather than the noise of price alone. Analytical Volume Profile Trading (AVPT) goes far beyond simple indicators by dissecting where the market actually traded, not just where it moved. Through the interplay of High-Volume Nodes, Low-Volume Nodes, Value Areas, and the all-important Point of Control, AVPT exposes the hidden layers of market memory—showing exactly where institutions agreed,

**score 2:** In the initialization phase, the EA sets up all essential components by first creating the ATR indicator used for volatility-based stop-loss calculations and validating that it loads correctly. It then prepares the volume profile arrays through a dedicated initialization function and establishes a repeating timer so the system can update its profile and logic every minute. During deinitialization, the EA safely releases the ATR indicator, stops the timer, and removes any chart objects created during execution to ensure a clean shutdown and prev

**score 2:** In the main execution loop, the EA continuously updates the ATR value on every tick to maintain accurate volatility metrics. When a new bar forms, it triggers core processing steps: refreshing the volume profile, recalculating key levels such as POC and Value Area boundaries, and updating the visual objects on the chart. After the structural analysis is refreshed, the EA evaluates whether any trade conditions are met based on the latest Volume Profile signals, and then separately manages all currently open positions to ensure stops, trailing lo

**score 2:** In summary, we developed Analytical Volume Profile Trading (AVPT) by breaking down how liquidity architecture, volume distribution, and market memory shape the true structure behind price movements. We explored how volume nodes, high-liquidity shelves, and low-volume inefficiencies form a repeatable blueprint of where markets pause, expand, or reverse. We then translated this structural logic into algorithmic execution—mapping how an EA can read volume profile zones, anticipate liquidity events, and align entries with the deepest institutional 


## Tail
[Developing a Trading Strategy: The Flower Volatility Index Trend-Following Approach](https://www.mql5.com/en/articles/20309)

The relentless quest to decode market rhythms has led traders and quantitative analysts to develop countless mathematical models. This article has introduced the Flower Volatility Index (FVI), a novel approach that transforms the mathematical elegance of Rose Curves into a functional trading tool. Through this work, we have shown how mathematical models can be adapted into practical trading mechanisms capable of supporting both analysis and decision-making in real market conditions.

[Automating Trading Strategies in MQL5 (Part 41): Candle Range Theory (CRT) – Accumulation, Manipulation, Distribution (AMD)](https://www.mql5.com/en/articles/20323)

In this article, we develop a Candle Range Theory (CRT) trading system in MQL5 that identifies accumulation ranges on a specified timeframe, detects breaches with manipulation depth filtering, and confirms reversals for entry trades in the distribution phase. The system supports dynamic or static stop-loss and take-profit calculations based on risk-reward ratios, optional trailing stops, and limits on positions per direction for controlled risk management.

Powerful analytics for traders of any level All the necessary trading reports for beginners and professionals](https://www.mql5.com/ff/go?link=https://www.mql5.com/en/forum/454106&a=muccpajyfystoakuukdobwigjejzmpqn&s=52daad60fa795e635264e6f94898f05493bca3b5124d4cca8eb7e82333c2ef12&uid=&ref=https://www.mql5.com/en/articles/20327&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=6353445546819719599)


---
# 23550: Building a Volume-Based Liquidity Heatmap Indicator in MQL5
HEADS: # Building a Volume-Based Liquidity Heatmap Indicator in MQL5 | ### **Introduction** | ### **Project Overview and Implementation Plan** | ### **Implementation in MQL5** | ### **Conclusion**

## Intro
# Building a Volume-Based Liquidity Heatmap Indicator in MQL5

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Indicators](https://www.mql5.com/en/articles/mt5/indicators) | 10 August 2026 at 06:35

3 280 [ 2](https://www.mql5.com/en/forum/514281 "Comments")

[Israel Pelumi Abioye](https://www.mql5.com/en/users/13467913)

MetaTrader 5 provides price and volume data but does not offer a built-in chart visualization layer for highlighting where clustered leveraged positions are likely to be concentrated. Since retail indicators cannot access exchange-level liquidation or open-interest data, this task becomes an engineering reconstruction that uses only OHLC and volume data to detect volume spikes, convert those spikes into estimated liquidation prices under an assumed leverage, rank the resulting zones by relative signal strength, and manage their lifecycle on the chart (create → extend forward → freeze once swept).


## Key hits
**score 3:** MetaTrader 5 provides OHLC price data and volume information, but it does not provide direct access to exchange-level liquidation data, open interest, or the distribution of leveraged positions. Therefore, an indicator running on MetaTrader 5 cannot identify actual liquidation events or confirm where forced position closures occur. To overcome this limitation, the Liquidity Heatmap indicator is designed as an estimation tool that uses available market data to identify areas where liquidity may be concentrated. Since direct liquidation informati

**score 3:** After that, the program detects the opening time of the current chart bar and compares it with the opening time stored from the previous calculation. If the two values differ, it indicates that a new bar has formed. The indicator then updates the stored timestamp to the current bar's opening time, allowing subsequent calculations or chart updates to be performed only once per newly completed bar rather than on every incoming tick. This improves efficiency by preventing unnecessary repeated processing while the current bar is still forming. The 

**score 2:** Since direct liquidation data is unavailable, the indicator uses unusually high volume as a proxy for significant market activity.

**score 2:** - processes candles within the selected lookback range; - selects real volume or tick volume; - calculates the 14-period SMA of volume; - compares current volume against the SMA; - classifies candles with above-average volume as qualified signals.

**score 2:** //--- Inputs input ENUM_HEATMAP_MODE   InpMode          = MODE_HD;        // Mode input ENUM_HEATMAP_SIDE   InpSide          = SIDE_BOTH;      // Display side input int                 InpLeverage      = 300;            // Leverage (25-300) input color               InpLongColor     = C'204,0,204';   // Long liquidation color input color               InpShortColor    = C'255,255,0';   // Short liquidation color input color               InpPeakColor     = C'255,255,255'; // Peak (max-volume) color input bool                InpShowBubbles  = tr

**score 2:** } //+------------------------------------------------------------------+ //| Custom indicator iteration function                              | //+------------------------------------------------------------------+ int OnCalculate(const int32_t rates_total,                 const int32_t prev_calculated,                 const datetime &time[],                 const double &open[],                 const double &high[],                 const double &low[],                 const double &close[],                 const long &tick_volume[],           

**score 2:** Similarly, the VolMax() function scans the buffer and returns the highest stored volume value. This identifies the strongest qualified volume event currently available and is later used to determine whether the current candle represents a peak volume signal. The VolAvg() function calculates the arithmetic mean of every stored value in the rolling buffer. Rather than comparing the current signal only against the strongest or weakest event, this average provides a benchmark that allows the indicator to determine whether the latest qualified signa

**score 2:** Once these statistics have been calculated, the indicator uses the GradientColor() function to convert the relative strength of the current signal into a display color. The function receives the current volume value together with the minimum and maximum values found in the rolling buffer, then calculates the signal's position within that range. A signal close to the minimum receives a color that is blended heavily toward white, making it appear less prominent, while a signal closer to the maximum receives a color much closer to the selected tar


## Tail
[Neural Networks in Trading: A Cross-Domain Time Series Forecasting Framework (TimeFound)](https://www.mql5.com/en/articles/18414)

In this article, we build the core of the TimeFound intelligent model step by step, adapting it to real-world time series forecasting tasks. If you are interested in the practical implementation of neural network patching algorithms in MQL5, you have come to the right place.

[Crystal Structure Algorithm (CryStAl)](https://www.mql5.com/en/articles/19899)

This article presents two versions of the Crystal Structure Algorithm: the original and the modified version. The Crystal Structure Algorithm (CryStAl), published in 2021 and inspired by the physics of crystal structures, was positioned as a parameter-free metaheuristic for global optimization. However, testing revealed a critical problem with the algorithm. A modified version, CryStAlm, is also presented; it addresses the original's key shortcomings.

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F523%3Futm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Dchoose.signals%26utm_content%3Dsubscribe.signal%26utm_campaign%3D0622.MQL5.com.Internal&a=fyznzyduwsltgnhlftytumasbfgbwlqw&s=91bc0eca8f132d3df7d14cdb1baebac753aef179403d60dc83856af55a4d6769&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=feoumarwruttwycukqydjkbpqkigifzz&ssn=1788776688380070618&ssn_dr=0&ssn_sr=0&fv_date=1788776688&ref=https%3A%2F%2Fwww.mql


---
# 22342: Building a Liquidity Spectrum Volume Profile Indicator in MQL5
HEADS: # Building a Liquidity Spectrum Volume Profile Indicator in MQL5 | ### **Introduction** | ### **Project Overview and Implementation Plan** | ### **Creating the Liquidity Spectrum Volume Profile Indicator in MQL5** | ### **Conclusion**

## Intro
# Building a Liquidity Spectrum Volume Profile Indicator in MQL5

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Indicators](https://www.mql5.com/en/articles/mt5/indicators) | 1 May 2026 at 12:12

5 041 [ 2](https://www.mql5.com/en/forum/509228 "Comments")

[Israel Pelumi Abioye](https://www.mql5.com/en/users/13467913)

1. [Introduction](https://www.mql5.com/en/articles/22342#introduction) 2. [Project Overview and Implementation Plan](https://www.mql5.com/en/articles/22342#project_overview_and_implementation_plan) 3. [Creating the Liquidity Spectrum Volume Profile Indicator in MQL5](https://www.mql5.com/en/articles/22342#creating_the_liquidity_spectrum_volume_profile) 4. [Conclusion](https://www.mql5.com/en/articles/22342#conclusion)


## Key hits
**score 3:** [](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F1171%3Futm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Dbest.vps%26utm_content%3Drent.vps%26utm_campaign%3D0622.MQL5.com.Internal&a=nwegcasiojnqcoyrdlgofmjtfardztwf&s=d64d6f3c87f2458cba81f6d7b6694dd9e89dd354d4abc1d0584e405285806c9f&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=lzmxtnxkrfxqnlpddcejmyhiukhahwae&ssn=1788778562086626465&ssn_dr=0&ssn_sr=0&fv_date=1788778562&ref=https%3A%2F%2Fwww.mql5.com%2Fen%2F

**score 2:** Standard per-bar volumes under candles do not show how volume is distributed across price, so it is difficult to tell which exact price levels actually “hold” liquidity within a chosen lookback. This article reframes that problem with explicit assumptions and engineering constraints: the profile will assign volume to price bins using candle close prices, prefer tick volume with a fallback to real volume, and operate on a stable, explicitly copied dataset (Copy\* functions). In practice, three implementation hurdles must be solved to produce a r

**score 2:** In this project, we are building a Liquidity Spectrum Volume Profile Indicator in MQL5. The main purpose of this indicator is to visualize how trading volume is distributed across different price levels within a specified lookback period. Instead of only showing price movement or a single volume value, the indicator breaks the market into multiple price ranges (bins). It then calculates how much volume occurred within each bin and represents that information visually on the chart. Each bin reflects a specific price zone, and its volume determin

**score 2:** //--- Copy required data from terminal    if(CopyHigh(_Symbol,_Period,0,lookback,hi)  < lookback)       return;    if(CopyLow(_Symbol,_Period,0,lookback,lo)  < lookback)       return;    if(CopyClose(_Symbol,_Period,0,lookback,cl)  < lookback)       return;    if(CopyTime(_Symbol,_Period,0,lookback,tm)  < lookback)       return; //--- Prefer tick volume, fallback to real volume    if(CopyTickVolume(_Symbol,_Period,0,lookback,vol) < lookback)       if(CopyRealVolume(_Symbol,_Period,0,lookback,vol) < lookback)          return;   } ```

**score 2:** The main function then begins the calculation process. Before doing anything, it first checks whether both visualization options are disabled. If they are, there is nothing to draw, so the function ends instantly. The code then calculates the number of bars that are accessible on the chart and makes sure that the lookback does not go beyond the available history. This keeps errors from attempting to access nonexistent data. The function quits if the lookback is too small because there isn't enough information to do useful computations. The code

**score 2:** //--- Copy required data from terminal    if(CopyHigh(_Symbol,_Period,0,lookback,hi)  < lookback)       return;    if(CopyLow(_Symbol,_Period,0,lookback,lo)  < lookback)       return;    if(CopyClose(_Symbol,_Period,0,lookback,cl)  < lookback)       return;    if(CopyTime(_Symbol,_Period,0,lookback,tm)  < lookback)       return; //--- Prefer tick volume, fallback to real volume    if(CopyTickVolume(_Symbol,_Period,0,lookback,vol) < lookback)       if(CopyRealVolume(_Symbol,_Period,0,lookback,vol) < lookback)          return;

**score 2:** //--- Copy required data from terminal    if(CopyHigh(_Symbol,_Period,0,lookback,hi)  < lookback)       return;    if(CopyLow(_Symbol,_Period,0,lookback,lo)  < lookback)       return;    if(CopyClose(_Symbol,_Period,0,lookback,cl)  < lookback)       return;    if(CopyTime(_Symbol,_Period,0,lookback,tm)  < lookback)       return; //--- Prefer tick volume, fallback to real volume    if(CopyTickVolume(_Symbol,_Period,0,lookback,vol) < lookback)       if(CopyRealVolume(_Symbol,_Period,0,lookback,vol) < lookback)          return;

**score 2:** //--- Copy required data from terminal    if(CopyHigh(_Symbol,_Period,0,lookback,hi)  < lookback)       return;    if(CopyLow(_Symbol,_Period,0,lookback,lo)  < lookback)       return;    if(CopyClose(_Symbol,_Period,0,lookback,cl)  < lookback)       return;    if(CopyTime(_Symbol,_Period,0,lookback,tm)  < lookback)       return; //--- Prefer tick volume, fallback to real volume    if(CopyTickVolume(_Symbol,_Period,0,lookback,vol) < lookback)       if(CopyRealVolume(_Symbol,_Period,0,lookback,vol) < lookback)          return;


## Tail
[CFTC Data Mining in Python and Building an AI Model](https://www.mql5.com/en/articles/18303)

Let's try mining CFTC data, downloading COT and TFF reports via Python, connecting all this with MetaTrader 5 quotes and an AI model, and get forecasts. What are COT reports in the Forex market? How to use COT and TFF reports for forecasting?

[MQL5 Wizard Techniques you should know (Part 87): Volatility-Scaled Money Management with Monotonic Queue in MQL5](https://www.mql5.com/en/articles/22338)

This article presents a custom MQL5 money management class that adapts position sizing to real-time volatility using a monotonic queue for O(N) sliding-window extremes. The class applies inverse volatility scaling and optionally validates risk with an RBF network. We show implementation details in the Optimize method and compare results with the inbuilt Size-Optimized class to assess latency and risk control benefits.

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F1171%3Futm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Dbest.vps%26utm_content%3Drent.vps%26utm_campaign%3D0622.MQL5.com.Internal&a=nwegcasiojnqcoyrdlgofmjtfardztwf&s=d64d6f3c87f2458cba81f6d7b6694dd9e89dd354d4abc1d0584e405285806c9f&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=lzmxtnxkrfxqnlpddcejmyhiukhahwae&ssn=1788778562086626465&ssn_dr=0&ssn_sr=0&fv_date=1788778562&ref=https%3A%2F%2Fwww.mql5.com%2Fen%2F


---
# 18661: Analyzing Price Time Gaps in MQL5 (Part II): Creating a Heat Map of Liquidity Distribution Over Time
HEADS: # Analyzing Price Time Gaps in MQL5 (Part II): Creating a Heat Map of Liquidity Distribution Over Time | ### | ### Mathematical foundation: From chaos to order | ### | ### Solution architecture: Modularity as the basis for reliability | ### | ### Algorithm: Math meets reality | ### | ### Color alchemy: Transforming numbers into images | ### | ### Visualization: From algorithm to chart | ### Interpreting the results: What the colors mean | ### | ### Customization for different markets: Versatility through adaptation

## Intro
# Analyzing Price Time Gaps in MQL5 (Part II): Creating a Heat Map of Liquidity Distribution Over Time

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Indicators](https://www.mql5.com/en/articles/mt5/examples_indicators) | 5 June 2026 at 05:24

1 971 [ 4](https://www.mql5.com/en/forum/510787 "Comments")

[Yevgeniy Koshtenko](https://www.mql5.com/en/users/koshtenko)

In the [first part](https://www.mql5.com/en/articles/18592), we examined the concept of time gaps and their connection with institutional trading activity. However, detecting these gaps is only half the task. To trade effectively, a trader needs to see the full picture: where the price spends a lot of time, where it spends little time, and how these zones interact with each other.


## Key hits
**score 1:** Orange and yellow zones (25-75%) represent areas of moderate activity. Here the price lingers periodically, but without obvious dominance. These are transition zones that can become support or resistance, depending on the market context. These are the zones where trend-following trades often work best.

**score 1:** For stocks, moderate settings tend to work well: **AnalysisPeriod** 200-300 bars, **MaxHistory** 3000-5000 bars. The session structure creates natural pauses that are reflected well in the heat map.

**score 1:** The 1000 level limit was introduced for a reason. MetaTrader 5 has limitations on the number of graphical objects, and exceeding reasonable limits leads to a slowdown in the interface without significantly improving the quality of analysis.

**score 1:** You have probably already heard about pointers when it comes to programming. But did you know that we can use this kind of data here in MQL5? Of course, this must be done in a way that keeps us in control and avoids strange program behavior during execution. Still, because this is a feature with a very specific purpose and aimed at particular kinds of tasks, it is rare to hear anyone discuss what a pointer is and how to use it in MQL5.

**score 0:** # Analyzing Price Time Gaps in MQL5 (Part II): Creating a Heat Map of Liquidity Distribution Over Time

**score 0:** The basic idea is simple: represent the entire price range as a set of micro-zones and, for each zone, calculate how long the price was in it. The longer the time, the "hotter" the zone, the more important it is for the market. The result is visualized through a color scheme from cool red to hot blue.

**score 0:** The key innovation was the use of a sliding analysis window. Instead of processing the entire available history (which could take seconds), we analyze only the latest **MaxHistory** bars through a window the size of **AnalysisPeriod**. This ensures that the results are relevant and the performance is acceptable.

**score 0:** The result is smooth color transitions that create a natural heat map of the market.


## Tail
In today's article, we will look at how to control some object properties in a simple way using code. We will also see how a custom application can place more than one object on the same chart. In addition, we will begin to understand the importance of assigning a short name to any indicator we plan to implement.

[Market Simulation (Part 23): Getting Started with SQL (VI)](https://www.mql5.com/en/articles/12987)

In this article, we will see how to visualize a database and, from that, understand how it is structured. This is done by analyzing the database’s internal structure. Although this may seem unnecessary at first, it is fully justified if we really want to become database administrators. After all, some people make a living maintaining and designing databases.

Access our new hub for expert analytics, trading insights, global financial news, and more

Learn more](https://www.mql5.com/ff/go?link=https://www.metatrader.com%3Futm_source=www.mql5.com%26utm_medium=display%26utm_content=visit%26utm_campaign=visit.metatrader.com.426&a=anvvomolcquvlkemiiwazrokmauingca&s=5edb2ef4182c70fd6beca6df0a841244f4dc3eb3f7df8658c0aeadcf20882dba&uid=&ref=https://www.mql5.com/en/articles/18661&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=6416303587197597013)


---
# 21876: How to Detect Round-Number Liquidity in MQL5
HEADS: # How to Detect Round-Number Liquidity in MQL5 | ### | ### Introduction: The Geometry of Institutional Liquidity | ### Theoretical Framework: The Psychology of Clustering at Zeros | ### The Custom Algorithm: Beyond Simple Modulo Math | ### | ### Technical Implementation: The Core MQL5 Logic | ### Case Studies: Universal Application Across Assets | ### Developing a Trading Strategy: Confluence is Key | ### Frequently Asked Questions (FAQ) | ### Risk Management and Position Sizing | ### | ### Conclusion: The Blueprint for Professional S/R Trading

## Intro
# How to Detect Round-Number Liquidity in MQL5

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Trading](https://www.mql5.com/en/articles/mt5/trading) | 23 April 2026 at 09:35

4 240 [ 0](https://www.mql5.com/en/forum/508823 "Comments")

[Mostafa Ghanbari](https://www.mql5.com/en/users/mghfx)

- [Introduction](https://www.mql5.com/en/articles/21876#introduction_the_geometry_of_institutional) - [Theoretical Framework](https://www.mql5.com/en/articles/21876#theoretical_framework_the_psychology_of_clustering) - [The Custom Algorithm](https://www.mql5.com/en/articles/21876#the_custom_algorithm_beyond_simple_modulo_math) - [Technical Implementation](https://www.mql5.com/en/articles/21876#technical_implementation_the_core_mql5_logic) - [Case Studies](https://www.mql5.com/en/articles/21876#para5) - [Developing a Trading Strategy](https://www.mql5.com/en/articles/21876#para6) - [FAQ](https://www.mql5.com/en/articles/21876#frequently_asked_questions_faq) - [Risk Management](https://www.mql


## Key hits
**score 3:** Price often clusters and reverses at whole integers (psychological round-number levels). In practice, this creates operational issues. Some timeframes become cluttered with trivial lines, while on others, strong levels are indistinguishable from noise. Simple modulo tests also fail due to floating‑point artifacts and heterogeneous quote formats (Digits, TickSize) across FX, metals, indices, and crypto.

**score 1:** [Mostafa Ghanbari](https://www.mql5.com/en/users/mghfx)

**score 1:** A crucial principle in round-number analysis is the scaling of significance across different timeframes. While a ZeroSize 2 level (e.g., 1.1020) might offer a valid scalping opportunity on a 5-minute chart, it often becomes 'market noise' on a daily or weekly chart.

**score 1:** A basic mathematical modulo operation (price % step == 0) can tell you if a number is round, but not *how* round it is relative to others. To overcome this limitation, I developed an innovative string-parsing logic.

**score 1:** To reduce chart clutter, the indicator uses dynamic scaling.Major levels (ZeroSize 4) are rendered with higher Z-order and thicker lines so they remain visible when zoomed out. Minor levels are automatically dimmed or converted to dashed lines to ensure that the trader's focus remains on the most critical liquidity pools. This hierarchical visualization is essential for maintaining "trading flow" and reducing cognitive load during high-volatility sessions.

**score 1:** As demonstrated in this chart of Gold M1, the price approached the ZeroSize 3 level during a high-volatility session and reacted with a perfect pin-bar rejection, confirming our theory.

**score 1:** Q3: Can I use round levels for crypto trading?

**score 1:** [Mostafa Ghanbari](https://www.mql5.com/en/users/mghfx "Mostafa Ghanbari")


## Tail
Create a traditional Renko indicator in MQL5 that converts candlestick closing prices into fixed-size blocks displayed on the main chart. We calculate the movement from the closing price of the last block, create new blocks of a user-defined size, confirm reversals using the two-block rule, manage block closing prices in a dynamic array, and display rectangles for visualizing the trend in real time.

[Building a Trade Analytics System (Part 1): Foundation and System Architecture](https://www.mql5.com/en/articles/22107)

We design a simple external trade analytics pipeline for MetaTrader 5 and implement its backend in Python with Flask and SQLite. The article defines the architecture, data model, and versioned API, and shows how to configure the environment, initialize the database, and run the server locally. As a result, you get a clean base to capture closed-trade records from MetaTrader 5 and store them for later analysis.

Use Git-powered tools in MetaEditor for structured, reliable development

Learn more](https://www.mql5.com/ff/go?link=https://forge.mql5.io%3Futm_source=www.mql5.com%26utm_medium=display%26utm_content=visit%26utm_campaign=visit.mql5.226&a=oygnrjjxveoqzycxkjkckcgtshfunvdu&s=1e458fdafe5955c82ea32b518845e77efbe1196295936353793e9e23a750f4d6&uid=&ref=https://www.mql5.com/en/articles/21876&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=6457453681745464350)


---
# 15895: Scalping Orderflow for MQL5
HEADS: # Scalping Orderflow for MQL5 | ### Introduction | ### The Code | ### Backtesting | ### Conclusion

## Intro
[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Examples](https://www.mql5.com/en/articles/mt5/examples) | 19 September 2024 at 13:20

16 499 [ 4](https://www.mql5.com/en/forum/473361 "Comments")

[Javier Santiago Gaston De Iriarte Cabrera](https://www.mql5.com/en/users/jsgaston)

An example of a sophisticated algorithmic trading system for MetaTrader 5 (MQL5) that uses the Scalping OrderFlow technique is this Expert Advisor (EA).

A short-term trading strategy known as "scalping order flow" focuses on identifying possible entry and exit points in the market by examining the real-time flow of orders. It makes quick trading decisions by combining the study of volume, price activity, and order book data. Typically, positions are held for a very short time—often within minutes or even seconds.


## Key hits
**score 2:** // Input parameters input int VolumeThreshold = 35000;  // Volume threshold to consider imbalance input int OrderFlowPeriod = 30;   // Number of candles to analyze order flow input double RiskPercent = 1.0;   // Risk percentage per trade input int ADXPeriod = 14;         // ADX Period input int ADXThreshold = 25;      // ADX threshold for strong trend input int MAPeriod = 200;         // Moving Average Period input ENUM_TIMEFRAMES Timeframe = PERIOD_M15;  // Timeframe for analysis input double MaxLotSize = 0.1;    // Maximum allowed lot size in

**score 1:** A short-term trading strategy known as "scalping order flow" focuses on identifying possible entry and exit points in the market by examining the real-time flow of orders. It makes quick trading decisions by combining the study of volume, price activity, and order book data. Typically, positions are held for a very short time—often within minutes or even seconds.

**score 1:** This EA finds trading opportunities based on order flow imbalances by using a variety of technical indicators and market analysis methodologies. Advanced risk management features including trailing stops, partial position closing, and dynamic position size are also included. In addition, the EA incorporates a method to prevent trading during significant news events and sets a limit on consecutive losses.

**score 1:** Predicting short-term price swings through the examination of real-time order book data and volume dynamics is the fundamental idea behind OrderFlow trading. By combining this idea with other established technical analysis indicators, this expert advisor develops a hybrid strategy that seeks to pinpoint high-probability trading opportunities.

**score 1:** // Verify input parameters     if(VolumeThreshold <= 0 || OrderFlowPeriod <= 0 || RiskPercent <= 0 || RiskPercent > 100 ||        ADXPeriod <= 0 || ADXThreshold <= 0 || MAPeriod <= 0 || MaxLotSize <= 0 || ATRPeriod <= 0 ||        ATRMultiplier <= 0 || RSIPeriod <= 0 || RSIOverbought <= RSIOversold || MAFastPeriod <= 0 ||        MASlowPeriod <= 0 || BollingerPeriod <= 0 || BollingerDeviation <= 0 || MaxConsecutiveLosses < 0 ||        MinBarsBetweenTrades < 0)     {         Print("Error: Invalid input parameters.");         return INIT_FAILED;   

**score 1:** The main trading logic is executed in the OnTick() function, which is called on each price tick. The EA first checks if a new bar has formed and if trading is allowed. It then analyzes the order flow by comparing buy and sell volumes over a specified period. The EA uses multiple technical indicators to confirm trading signals, including trend strength (ADX), price position relative to moving averages, and RSI levels.

**score 1:** double buyVolume = 0, sellVolume = 0;     AnalyzeOrderFlow(buyVolume, sellVolume);

**score 0:** An example of a sophisticated algorithmic trading system for MetaTrader 5 (MQL5) that uses the Scalping OrderFlow technique is this Expert Advisor (EA).


## Tail
[MQL5 Wizard Techniques you should know (Part 40): Parabolic SAR](https://www.mql5.com/en/articles/15887)

The Parabolic Stop-and-Reversal (SAR) is an indicator for trend confirmation and trend termination points. Because it is a laggard in identifying trends its primary purpose has been in positioning trailing stop losses on open positions. We, however, explore if indeed it could be used as an Expert Advisor signal, thanks to custom signal classes of wizard assembled Expert Advisors.

[Developing a Replay System (Part 46): Chart Trade Project (V)](https://www.mql5.com/en/articles/11737)

Tired of wasting time searching for that very file that you application needs in order to work? How about including everything in the executable? This way you won't have to search for the things. I know that many people use this form of distribution and storage, but there is a much more suitable way. At least as far as the distribution of executable files and their storage is concerned. The method that will be presented here can be very useful, since you can use MetaTrader 5 itself as an excellent assistant, as well as MQL5. Furthermore, it is 

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Fvps%3Futm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Duse.vps%26utm_content%3Drent.vps%26utm_campaign%3D0622.MQL5.com.Internal&a=rktadgjlwhobyedohbrepzshvpcqrlpo&s=a93cef75a53eb5da24c98e0068b3c2b96015191a0af0d1857f5b4dd22e55e7bf&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=aaumvbhyfbirgcwwtgmnnpvtcndudsld&ssn=1788793688449432285&ssn_dr=0&ssn_sr=0&fv_date=1788793688&ref=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F15


---
# 20287: Automating Black-Scholes Greeks: Advanced Scalping and Microstructure Trading
HEADS: # Automating Black-Scholes Greeks: Advanced Scalping and Microstructure Trading | ### Introduction | ### Automation Overview | ### Getting Started | ### **Back Test Results** | ### Conclusion

## Intro
# Automating Black-Scholes Greeks: Advanced Scalping and Microstructure Trading

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Examples](https://www.mql5.com/en/articles/mt5/examples) | 21 November 2025 at 04:29

5 006 [ 1](https://www.mql5.com/en/forum/500538 "Comments")

[Hlomohang John Borotho](https://www.mql5.com/en/users/johnhlomohang)

1. [Introduction](https://www.mql5.com/en/articles/20287#introduction) 2. [Automation Overview](https://www.mql5.com/en/articles/20287#automation_overview) 3. [Getting Started](https://www.mql5.com/en/articles/20287#getting_started) 4. [Back Results](https://www.mql5.com/en/articles/20287#back_test_results) 5. [Conclusion](https://www.mql5.com/en/articles/20287#conclusion)


## Key hits
**score 1:** The global variables prepare the EA for real-time computation and execution. The CTrade trade object handles all buy and sell operations on the underlying instrument used for hedging. currentDelta and currentGamma store the latest calculated Greeks, while portfolioDelta and targetDelta help track how far the current exposure is from the desired hedge state (usually near zero for delta-neutral strategies). lastHedgeTime and currentHedgeFrequency are used to regulate how often the system evaluates the hedge, ensuring that the algorithm does not o

**score 1:** This section of the code implements the core decision-making engine that turns Greek calculations into automated trading actions. The CalculateDynamicFrequency() function adjusts how frequently the algorithm checks for hedging opportunities based on current Gamma levels. High Gamma implies rapid changes in Delta, so the system increases monitoring to once per minute. Medium Gamma uses the base frequency defined by the user, while low Gamma relaxes the evaluation interval to five minutes. This dynamic timing control ensures responsiveness during

**score 1:** The OnTick() function acts as the main execution loop of the Expert Advisor, running every time a new market tick arrives. It begins by refreshing the on-chart display so the trader can visually monitor live Delta, Gamma, hedge frequency, and other key metrics. The function then checks whether enough time has passed since the last hedge cycle, using the dynamically adjusted frequency generated from Gamma levels. When the time condition is met, it initiates a full strategy cycle, logs the timestamp, and calls ExecuteCombinedStrategy()—which hand

**score 1:** In summary, we brought the full automation pipeline of Black-Scholes Greeks into an actionable trading framework, bridging theoretical sensitivity measures with real-time market execution. We implemented fast numerical functions for Delta, Gamma, and time-to-expiry, built a dynamic frequency system driven by Gamma intensity, and developed hedge logic capable of maintaining Delta neutrality while opportunistically exploiting Gamma-scalping conditions. By combining Delta hedging, Gamma-based microstructure signals, expiry-aware logic, and a live 

**score 1:** [Overcoming The Limitation of Machine Learning (Part 7): Automatic Strategy Selection](https://www.mql5.com/en/articles/20256)

**score 0:** 1. [Introduction](https://www.mql5.com/en/articles/20287#introduction) 2. [Automation Overview](https://www.mql5.com/en/articles/20287#automation_overview) 3. [Getting Started](https://www.mql5.com/en/articles/20287#getting_started) 4. [Back Results](https://www.mql5.com/en/articles/20287#back_test_results) 5. [Conclusion](https://www.mql5.com/en/articles/20287#conclusion)

**score 0:** We move beyond theoretical exposition and into implementation. Furthermore, we will cover how to systematically calculate Greeks in an algorithmic environment, integrate them into your MetaTrader 5 Expert Advisor framework, and use them as real-time triggers for scalping and microstructure strategies. We’ll explore how Delta and Gamma can be used not just for hedging but as powerful input signals in high-frequency contexts: identifying ultra-short-term liquidity shifts, and automating precise entries and exits in fast‐moving markets.

**score 0:** Finally, the TimeToExpiry function provides a clean, automated way to track remaining option life in years, which is critical for all option pricing and Greeks. By calculating the difference between the current server time and a fixed expiry date, and converting that into a fraction of a year, this utility enables the EA to continuously update Delta and Gamma as real time moves forward. Collectively, these functions allowed us to bridge theoretical Black-Scholes mathematics with practical, real-time algorithmic trading logic—setting the stage f


## Tail
This article is intended for algorithmic traders, quantitative analysts, and MQL5 developers interested in enhancing their understanding of candlestick pattern recognition through practical implementation. It provides an in‑depth exploration of the CandlePatternSearch.mq5 Expert Advisor—a complete framework for detecting, visualizing, and monitoring classical candlestick formations in MetaTrader 5. Beyond a line‑by‑line review of the code, the article discusses architectural design, pattern detection logic, GUI integration, and alert mechanisms

[Risk Management (Part 2): Implementing Lot Calculation in a Graphical Interface](https://www.mql5.com/en/articles/16985)

In this article, we will look at how to improve and more effectively apply the concepts presented in the previous article using the powerful MQL5 graphical control libraries. We'll go step by step through the process of creating a fully functional GUI. I'll be explaining the ideas behind it, as well as the purpose and operation of each method used. Additionally, at the end of the article, we will test the panel we created to ensure it functions correctly and meets its stated goals.

[Running robots on virtual hosting is easy Follow our step-by-step MetaTrader VPS guide for beginners Read

](https://www.mql5.com/ff/go?link=https://www.mql5.com/en/articles/13586&a=uzpprdshbcrtxvjxpmescehprypbymxc&s=516438f25b531570d9b7d49dcfb29c82fa1021f5ede6571df8026dbfbafcd13f&uid=&ref=https://www.mql5.com/en/articles/20287&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&fz_uniq=6413521500656767475)


---
# 8136: Price series discretization, random component and noise
HEADS: # Price series discretization, random component and noise | ### Introduction | ### | ### Signal Discretization Features | ### Is the Price Series Discrete or Continuous? | ### The Function of What Is the Price | ### Features of Price Series Discretization by Time Intervals and the Random Component | ### Density of Distribution of Price Series Increments | ### High and Low Volatility Areas | ### Alternative Price Series Discretization | ### Conclusion

## Intro
# Price series discretization, random component and noise

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Statistics and analysis](https://www.mql5.com/en/articles/mt5/statistics) | 23 November 2020 at 02:47

9 010 [ 21](https://www.mql5.com/en/forum/356318 "Comments")

[Maxim Romanov](https://www.mql5.com/en/users/223231)

The classical method of representing price series as time intervals (or time frames) appeared long ago, at the beginning of formation of financial markets, when there were no computers and when real goods were traded in real markets. Storing every price change during a day was difficult. Moreover, it was useless because prices were not changing quickly. Therefore, the obvious solution was to register price values at regular time intervals. Sounds logical: "Today wheat costs 90 cents, while yesterday it cost 80 cents." Everything is very clear: demand has grown and the price has risen. There were not many deals, as compared to today's market trading, that is why price was redefined rarely.


## Key hits
**score 3:** Attentive traders may notice that the candlesticks in the market are conventionally divided into groups of "large" and "small" sized candlesticks (areas with high and low volatility), which means that the chart is not a random walk and there are patterns. If time discretization introduced strong distortions, then this effect would not be observed. However, this feature can be explained by the fact that the candlestick size depends on the number of trading operations executed inside this candlestick. How this can be checked? You can simply look 

**score 2:** # Price series discretization, random component and noise

**score 2:** The question can be answered if we know the market price forming mechanism. I will not describe it in detail, as the description is provided in the article "[Principles of Exchange Pricing through the Example of Moscow Exchange's Derivatives Market](https://www.mql5.com/en/articles/1284)". Some participants place orders in the Market Depth, and other participants buy the required amount at the required price. This is what happens when a price chart is formed. The levels are discrete, i.e. it is possible to place an order at a price of 1, 2, 3 a

**score 2:** The Central Limit Theorem states that the sum of a sufficiently large number of weakly dependent random variables having approximately the same scales (none of the terms dominates or makes a determining contribution to the sum) is approximately normally distributed. As applied to our case, we can conclude from this theorem that, on average, our random process will pass for N steps a distance which is vertically proportional approximately to the square root of the number of steps. If one block is 1 step, then for 100 blocks the price will pass v

**score 2:** Further, using the obtained one-hour candlesticks, we actually combine and analyze a sequence of certain segments of a price series, the amplitude of which follows normal distribution law. Naturally, if we move to higher timeframes, we get all the same candlesticks, the size of which is proportional to the square root of the number of steps. Now get back to figure 2: if a series is incorrectly discretized, a random sequence is output as a result. In fact, by using time discretization, we convert a price series into a random sequence. Well, a ti

**score 2:** 1. Take tick volume data of 1-minute candlesticks (from a real account) for the same period and calculate the average number of ticks in a one-minute candlestick - the average number is 59.99 ticks per minute. 2. Load the tick data and find out the average tick size, it is equal to 0.000014378. 3. Calculate the theoretical size of a 1-minute candlestick as (59.99^0.5)\*0.00014378=0.000111363 4. Calculate the theoretical size of a one-hour candlestick as ((59.99\*60)^0.5)\* 0.000014378= 0.00086

**score 2:** - The nature of the price series is discrete, which stems from the pricing structure. - A market price is not a function of time, but it is a function of closely related economic processes and currently it is not possible to take them all into account. - Discretization of a price series into time intervals introduces a significant random component; this distorts the real shape of the price chart, adds noise and non-stationarity to this complex process with unknown parameters. - It is necessary to take into account the function of which paramete

**score 2:** [](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F523%3Futm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Dchoose.signals%26utm_content%3Dsubscribe.signal%26utm_campaign%3D0622.MQL5.com.Internal&a=fyznzyduwsltgnhlftytumasbfgbwlqw&s=91bc0eca8f132d3df7d14cdb1baebac753aef179403d60dc83856af55a4d6769&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=fhqzhaoaaqzebqdhqnpabufagpptgswe&ssn=1788802320602071648&ssn_dr=0&ssn_sr=0&fv_date=1788802320&ref=https%3A%2F%2Fwww.mql


## Tail
[What is a trend and is the market structure based on trend or flat?](https://www.mql5.com/en/articles/8184)

Traders often talk about trends and flats but very few of them really understand what a trend/flat really is and even fewer are able to clearly explain these concepts. Discussing these basic terms is often beset by a solid set of prejudices and misconceptions. However, if we want to make profit, we need to understand the mathematical and logical meaning of these concepts. In this article, I will take a closer look at the essence of trend and flat, as well as try to define whether the market structure is based on trend, flat or something else. I

[Gradient Boosting (CatBoost) in the development of trading systems. A naive approach](https://www.mql5.com/en/articles/8642)

Training the CatBoost classifier in Python and exporting the model to mql5, as well as parsing the model parameters and a custom strategy tester. The Python language and the MetaTrader 5 library are used for preparing the data and for training the model.

[](https://www.mql5.com/ff/go?link=https%3A%2F%2Fwww.mql5.com%2Fen%2Farticles%2F523%3Futm_source%3Dwww.mql5.com%26utm_medium%3Ddisplay.footer%26utm_term%3Dchoose.signals%26utm_content%3Dsubscribe.signal%26utm_campaign%3D0622.MQL5.com.Internal&a=fyznzyduwsltgnhlftytumasbfgbwlqw&s=91bc0eca8f132d3df7d14cdb1baebac753aef179403d60dc83856af55a4d6769&v=1&host=https%3A%2F%2Fwww.mql5.com%2Fff%2F&id=wdausxxqrpvhekbwjrjlhqjghyhesrqqau&uid=fhqzhaoaaqzebqdhqnpabufagpptgswe&ssn=1788802320602071648&ssn_dr=0&ssn_sr=0&fv_date=1788802320&ref=https%3A%2F%2Fwww.mql


---
