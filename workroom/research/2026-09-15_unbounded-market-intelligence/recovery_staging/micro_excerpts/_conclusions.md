# 22263: Market Microstructure in MQL5 (Part 1): Robust Foundation

## Sections

### Conclusion

The foundation implemented here removes the silent failure modes that make intraday microstructure unusable in practice. MicroStructure\_Foundation.mqh is a single include you add to any indicator or EA; it provides well‑defined guarantees so subsequent measurements can be trusted.

Practical outcome:

- safe math primitives (SafeDivide, SafeLog, SafeSqrt, SafeExp, SafeTanh) that prevent NaN/Inf and soft-clip overflows;
- validated market access and history reads (ValidateSymbolV2, SafeCopyClose) that reject non‑tradable symbols, anomalous spread, and non‑positive close prices;
- numerically stable statistical primitives (two‑pass variance, trimmed estimators, OLS slope) that tolerate fat tails and regime shifts;
- a single FFT implementation for consistent spectral calculations.

With these guarantees in place, microstructure metrics no longer “lie” at critical moments. Part 2 builds on this layer to implement three independent Hurst estimators combined by confidence weighting, relying on the defensive primitives supplied here.

### 

### References

- [Engle, R. (2000). The econometrics of ultra-high-frequency data. *Econometrica*, 68(1), 1–22.](https://www.jstor.org/stable/2999473 "https://www.jstor.org/stable/2999473")
- [Madhavan, A. (2000). Market microstructure: a survey. *Journal of Financial Markets*, 3, 205–258.](https://www.sciencedirect.com/science/article/abs/pii/S1386418100000070 "https://www.sciencedirect.com/science/article/abs/pii/S1386418100000070")
- [Dacorogna, M., Gencay, R., Muller, U., Olsen, R., and Pictet, O. (2001). *An Introduction to High-Frequency Finance*. Academic Press.](https://www.sciencedirect.com/book/monograph/9780122796715/an-introduction-to-high-frequency-finance "https://www.sciencedirect.com/book/monograph/9780122

## Key paras

You trade NQ around the New York open and therefore rely on minute‑level microstructure to stay ahead of fast price moves. At this frequency, standard calculations break quietly: NaN/Inf and overflows from divisions by near‑zero, log of non‑positive prices, zero or missing closes at the edge of history, and degenerate variance estimates from tiny samples. These are not compiler errors—they are plausible numbers that mislead decision logic and cost trades.

This article addresses that engineering gap. Its goal is practical and specific: provide a defensive MQL5 foundation that guarantees intraday measurements do not emit silent numerical failures. The target audience is MQL5 developers working with CopyClose/SymbolInfoDouble on intraday data (e.g., M1 NQ). Deliverable: a compilable include file that enforces minimum sample sizes, rejects invalid price data, bounds and validates mathematical operations, and supplies stable statistical and spectral primitives so downstream microstructure metrics are meaningful when it matters most.

Fat tails mean extreme values appear far more often than a normal distribution predicts. At the NY open on NQ, a single one-minute bar can move further than the previous hour of price action. Any calculation that assumes returns are normally distributed will be wrong in the moments that matter most.

GMT\_OFFSET\_HOURS of 2 reflects a broker on GMT+2. All session detection in Part 7 is built on this offset. If your broker runs on a different offset, change this constant once, and the entire time-aware system adjusts automatically.

Every field in OrderFlowSignal has a specific meaning. Strength is the directional imbalance; momentum is its rate of change; exhaustion captures fading flow; and smart\_money reflects the impact of high-volume bars. The direction\_numeric field exists specifically for use in mathematical expressions downstream—string comparisons have no place in a calculation pipeline.

TimeAwareSignal is the composite output of Part 7. It embeds an OrderFlowSignal and layers session context on top. The stop\_loss\_multiplier and max\_position\_size fields exist because position sizing should respond to signal quality—a high-confidence signal at the NY open warrants a different position size than the same signal during the Asian session.

Three attempts with a 10-millisecond pause between each. The spread check of less than 10,000 points is a sanity filter—a spread wider than this indicates either a data feed problem or a symbol that is not tradable. The function returns true immediately for the current chart symbol, avoiding a redundant market data request in the most common case.

This is the function that separates this toolkit from a naive implementation. The 10% symmetric trim removes the most extreme values before calculating mean and variance. On NQ M1 data at the NY open, those extreme values are real—they are not measurement errors—but they should not dominate a statistical estimate intended to characterize typical behavior. The function falls back to standard mean\_var if the dataset is too small to trim sensibly.

The skewness and kurtosis outputs are used in Part 4's volatility analysis. A dataset with high kurtosis confirms that fat tails are present—which on NQ at the NY open is almost always true.

- safe math primitives (SafeDivide, SafeLog, SafeSqrt, SafeExp, SafeTanh) that prevent NaN/Inf and soft-clip overflows; - validated market access and history reads (ValidateSymbolV2, SafeCopyClose) that reject non‑tradable symbols, anomalous spread, and non‑positive close prices; - numerically stable statistical primitives (two‑pass variance, trimmed estimators, OLS slope) that tolerate fat tails and regime shifts; - a single FFT implementation for consistent spectral calculations.

This article tests three common filters on a standard MACD crossover for US\_TECH100 H1 using five years of broker-native data. Filters are layered incrementally: regime, higher timeframe (HTF) alignment, and US session timing, to isolate each one's marginal impact. Results show session timing contributes far more than indicator refinements, while regime and HTF add little on their own. Includes a reproducible MQL5 regime classifier.

The article replaces hardcoded cost assumptions in triple-barrier labeling with measured inputs. An MQL5 script captures spread distribution, swap rates, and symbol metadata from your broker, and a Python model converts them into a broker-calibrated min ret you can pass to get events. Labels then reflect the actual round-trip friction for your instrument and holding period.

---

# 22553: Market Microstructure in MQL5 (Part 2): Measuring long memory in MQL5 with Hurst estimators

## Sections

### Empirical Study: What NQ M1 Data Shows

Theory specifies what H measures. Data specifies what H actually produces on a real instrument under real conditions. The two do not always agree, and when they diverge, the data takes precedence.

The study used 133 Globex trading sessions of NQ front-month futures from November 2025 to May 2026. All data is M1, timestamped in Eastern Time. The Python implementation of HurstExponentRobust() was coded from scratch to match the MQL5 spec: the same three estimators, the same confidence weighting, and the same log-return filter. It was cross-validated against the NT8 indicator output at a correlation of 0.60. The correlation is 0.60 because the NT8 version uses cross-day history while the Python study uses session-only history, demonstrating the session reset effect directly.

**Finding 1: NQ M1 operates near the random walk boundary**

Across 133 sessions, mean H\*(t) within the NY session ranges from 0.47 to 0.50, straddling the random walk boundary. When three estimators are applied to pooled post-open data (Figure 2), R/S gives H = 0.582, aggregated variance gives H = 0.479, and absolute moments gives H = 0.493—a confidence-weighted blend of 0.511. The rolling bar-by-bar average in Figure 4 sits slightly lower at 0.47–0.49, reflecting short-window estimation noise at the 90-bar lookback. Both measurements are consistent: NQ M1 operates close to the random walk boundary with no strong directional memory in either direction. This has a direct practical implication: H alone is not a reliable regime classifier for NQ M1. It becomes useful as a filter—confirming whether conditions are consistent with a signal generated by other means.

 stabilisation within the NY session. Panel A shows mean H*(t) ±1 SD by bar after the session re

### Reading the Output: Practical Thresholds

The empirical findings refine the theoretical regime boundaries. The following thresholds are derived from the NQ M1 data, not from textbook recommendations.

The baseline NQ M1 regime sits near the random walk boundary. The confidence-weighted blend from pooled post-open data gives H = 0.511; the rolling bar-by-bar mean gives H ≈ 0.48. Both are close to 0.5. Any reading in the 0.40–0.60 band carries no actionable directional information—it is the baseline, not a signal. A reading becomes meaningful only when it departs from that band in a sustained way.

A composite H above 0.60 with confidence above 0.30 indicates that the market is operating with positive long-range autocorrelation at the current bar count. Trend-following entry logic has a statistical foundation. A composite H below 0.40 with the same confidence threshold confirms the default anti-persistent regime is strengthening—mean-reversion strategies are appropriate. The transition zone from 0.40 to 0.60 warrants no directional commitment. Pass on the trade, tighten position sizing, or wait for the next measurement bar.

A confidence below 0.30 means fewer than 30% of the maximum possible regression points were valid. The H reading may be accurate, but there is insufficient data to rely on it. Treat it as no reading.




The variable bars\_since\_open must count only bars elapsed since the session opened at 09:30 ET. Using the full history lookback without a session reset will produce the contaminated H described in Finding 3 of the empirical study.

Part 3 of this series uses the composite H as the input to the ARFIMA fractional differencing parameter estimation. The empirical relationship between H and the differencing parameter d—specifically, d = H−0.5 for a f

### Conclusion

This article extended MicroStructure\_Foundation.mqh with four functions that implement confidence-weighted Hurst exponent estimation for intraday M1 data. The functions added are HurstExponentRS(), AdvancedHurstExponent(), HurstExponentRobust(), and PopulateHurstAnalysis(). No new include file is required: paste the Part 2 additions block before the closing #endif of the foundation header.

This implementation provides five guarantees:

1. No NaN or Inf is output from any estimator.
2. Degenerate scales are skipped.
3. A minimum of 40 bars is enforced before any H is returned.
4. Results are clamped to [0.01, 0.99].
5. Confidence is clamped to [0.0, 1.0].

The empirical study on 133 sessions of NQ M1 Globex futures established four findings that every practitioner using this code should understand. NQ M1 operates near the random walk boundary—the confidence-weighted blend from pooled data gives H = 0.511, and the rolling bar-by-bar mean gives H ≈ 0.48, with all three estimators straddling 0.5. The estimator requires 40 post-open bars before it activates. Pre-open and post-open data must not be mixed in the rolling window. The blended H does not significantly predict intraday trending in a 133-session sample, but it characterizes where the market sits relative to the random walk boundary—which is the correct use of the Hurst exponent as a regime filter.

The lightweight indicator HurstProfile.mq5 attaches to any M1 chart and plots H\*(t) in a sub-window with three reference lines and a regime histogram. This is the visualization tool for the MetaTrader 5 replication study: run it on CFD data and compare the intraday profile against the futures baseline established here.

### 

### References:

- [Hurst, H.E. (1951). Long-term storage capacity of reservoi

## Key paras

The question this article addresses is whether NQ M1 price data carries long-range dependence. Long-range dependence means that what happened an hour ago is still statistically relevant to what is happening now. If it exists, a trend-following framework is appropriate. If it does not, mean-reversion logic applies. Standard indicators do not answer this question. They treat each bar as if only the last few periods matter. That assumption is either wrong or right depending on the current regime, and a trader who cannot distinguish the two will apply the wrong framework at the wrong moment.

The article also includes an empirical study. Using 133 sessions of NQ M1 Globex futures data, we compute H\*(t) bar by bar across the full Globex day. The results differ from textbook expectations in several important respects. Those empirical findings drive the practical threshold recommendations in the final section.

The mean absolute value of block averages scales as E[|x̄(*m*)|] ∝ *m**H*−1. The log-log slope gives β and *H* = 1 + β. This estimator is more robust to heavy tails than the aggregated variance method. It remains stable when the return distribution is leptokurtic, the condition that prevails on NQ M1 around the NY open.

30 NY sessions · post-open bars only (10:10–12:00 ET) · session reset at 09:30 ET · Nov 2025 – May 2026

Returns whose absolute value exceeds 0.1 are discarded as data artifacts. On NQ M1, a genuine one-minute return of 10% does not occur—any value that large indicates a bad tick, a contract rollover, or a feed anomaly. The foundation's SafeLog() function handles the case where a close is non-positive before the subtraction is attempted.

One architectural decision requires explanation: the requirement to reset at the session boundary. When a rolling window spans the pre-open and post-open boundary, the return distribution has a structural break. At 09:33 ET, for example, a 90-bar lookback contains 86 pre-open bars and only 4 open bars. Pre-open NQ M1 data is thin, low-participation, and driven by overnight positioning. Post-open data is high participation and driven by institutional order flow. Mixing the two in a single regression produces an H reading that describes neither regime accurately. The empirical study in the next section demonstrates this effect explicitly. To avoid it, callers should limit the period parameter 

The study used 133 Globex trading sessions of NQ front-month futures from November 2025 to May 2026. All data is M1, timestamped in Eastern Time. The Python implementation of HurstExponentRobust() was coded from scratch to match the MQL5 spec: the same three estimators, the same confidence weighting, and the same log-return filter. It was cross-validated against the NT8 indicator output at a correlation of 0.60. The correlation is 0.60 because the NT8 version uses cross-day history while the Python study uses session-only history, demonstrating the session reset effect directly.

Across 133 sessions, mean H\*(t) within the NY session ranges from 0.47 to 0.50, straddling the random walk boundary. When three estimators are applied to pooled post-open data (Figure 2), R/S gives H = 0.582, aggregated variance gives H = 0.479, and absolute moments gives H = 0.493—a confidence-weighted blend of 0.511. The rolling bar-by-bar average in Figure 4 sits slightly lower at 0.47–0.49, reflecting short-window estimation noise at the 90-bar lookback. Both measurements are consistent: NQ M1 operates close to the random walk boundary with no strong directional memory in either direction. This has a direct practical implication: H alone is not a reliable regime classifier for NQ M1. It

stabilisation within the NY session. Panel A shows mean H*(t) ±1 SD by bar after the session reset at 09:30 ET. The estimator returns the fallback value of 0.5 for the first 40 bars. Panel B shows the estimator activation rate, which reaches 100 % at bar 40 (10:10 ET). NQ M1 Globex, 133 sessions, Nov 2025–May 2026")

With a 90-bar lookback and a session reset at 09:30 ET, the three-estimator blend requires at least 40 bars of session data before all three estimators can produce at least three valid log-log regression points. Before bar 40 (10:10 ET), the function returns the fallback value of 0.5 with confidence = 0.0. Figure 3, Panel B, shows this activation boundary precisely: the estimator activation rate jumps from 0% to 100% at exactly bar 40.

Without a session reset, the rolling window at 09:33 ET contains 86 pre-open bars and only 4 open bars. Mean H in this contaminated window drops to 0.37—0.09 points below the true post-open baseline. This is not a regime signal. It is a measurement artifact caused by the structural break between two different generating processes. The session reset corrects it by restarting the window at 09:30 ET. Callers must pass only bars elapsed since the session opened to HurstExponentRobust() when making intraday regime assessments.

This null result has a mechanistic explanation. It is more useful than a positive result in this context. Because NQ M1 operates near the random walk boundary (confidence-weighted H ≈ 0.51 on pooled data; rolling mean ≈ 0.48), the variation in H across sessions is largely noise around that boundary rather than a structured regime signal. The sessions that trend are anomalies; the Hurst estimator, which measures the average long-range correlation over a backward-looking window, does not reliably identify them in advance. The estimator’s value lies in characterizing where the market sits relative to the random walk boundary—not in predicting day-specific outcomes.

---

# 22598: Market Microstructure in MQL5 (Part 3): Estimating ARFIMA d with GPH

## Sections

### Empirical Study: GPH Applied to US100 M1

The same data used in Part 2 underpins this study: 72 NY sessions of US100 M1 Globex futures from January to May 2026. The New York session is defined as 09:30–16:00 Eastern Time. Returns are log differences of one‑minute closing prices. Returns with an absolute value above 0.1 (10%) are discarded as data artifacts; none were genuine in this dataset.

The Python implementation of GPHEstimator() matches the MQL5 specification exactly: the same bandwidth exponent (g = 0.65), the same minimum frequency count (m ≥ 15), the same DFT computation, and the same OLS regression. It was coded independently and cross‑checked against the MQL5 output in three sessions.

**Finding 1: The pooled d estimate is −0.006, consistent with the random walk boundary**

Applying GPH to all 27,930 NY session bars pooled together gives d = −0.006, implying H = 0.494. This is within 0.005 of the Part 2 pooled Hurst result (H = 0.511 by confidence‑weighted blend). The two estimators agree that US100 M1 operates near the random walk boundary. The R² of the pooled regression is 0.0001—effectively zero—confirming that the log‑periodogram has no meaningful linear slope near zero frequency.



Fig. 1: Distribution of session-level GPH d estimates (left) and d against implied H = d + 0.5 (right). 72 sessions, US100 M1, January–May 2026.

**Finding 2: Session‑level d is highly variable, with a mean near zero**

Across 72 sessions, the mean d is −0.016 and the median is −0.012. The standard deviation is 0.153. The interquartile range runs from −0.124 to 0.084. A small negative bias is present—consistent with the mild anti‑persistence suggested by Part 2's rolling mean of H ≈ 0.48—but it is not significant relative to the session‑to‑session variance.



Fig. 2: S

### Practical Interpretation and Trading Thresholds

The empirical findings translate into specific thresholds for the US100 M1 context.

d near zero (−0.1 to 0.1): No fractional differencing is needed beyond the standard log‑return transformation. The series is close enough to the random walk boundary that integer differencing (d = 1, log returns) is appropriate. This applies to approximately half of US100 M1 sessions. For machine learning feature engineering, log returns are the correct input. Applying fractional differencing with a non‑integer d to this series would be fitting noise.

d above 0.1: The log‑periodogram regression detects positive long‑memory structure at low frequencies. Trend‑following logic has a statistical foundation for this session. More practically, if you are building an ML feature from price data, a fractionally differenced series with d ≈ 0.2 will preserve more long‑range signal than standard log returns. Njoroge (2026b) describes an efficient MQL5 engine for applying a chosen d in O(width) computation per bar.

d below −0.1: Anti‑persistence dominates. Mean reversion at medium‑term lags is statistically supported. For this session type, standard log returns may slightly overrepresent short‑term reversals—an under‑differenced feature contains mean‑reverting structure. This has no practical consequence at d = −0.1 to −0.2, but at d approaching −0.4 (which appeared in two outlier sessions), the autocorrelation structure is meaningfully anti‑persistent.

Low R² (arfima\_confidence below 0.05): The log‑periodogram has no identifiable slope near zero frequency. This is not a failure—it is the expected result for a near‑random‑walk series. Low confidence means d cannot be distinguished from zero with the available data. Treat the d estimate as unin

### Conclusion

This article added GPHEstimator() and PopulateARFIMAAnalysis() to MicroStructure\_Foundation.mqh. Together they estimate the fractional differencing parameter d from the Geweke‑Porter‑Hudak log‑periodogram regression and write the result into RobustFractalAnalysis.arfima\_d. The five new constants— GPH\_MIN\_BARS, GPH\_BANDWIDTH\_EXP, GPH\_MIN\_FREQ, GPH\_CONF\_THRESHOLD, and GPH\_D\_CONSISTENCY—govern the estimator's behavior and can be adjusted for instruments with different characteristics.

The empirical study on 72 US100 M1 NY sessions confirms the central result: pooled d = −0.006, implied H = 0.494, consistent with Part 2's H ≈ 0.48–0.51. Session‑level d is highly variable (standard deviation 0.153), with 47% of sessions in the near‑zero band, 29% anti‑persistent, and 24% showing positive long memory. No fractional differencing beyond standard log returns is indicated for the average US100 M1 session, but individual sessions depart meaningfully from d = 0.

The struct now carries both hurst\_exponent and arfima\_d, with their respective confidence fields. The H‑d consistency check links the two measurements: a discrepancy above 0.1 triggers a diagnostic note, identifying sessions where short‑range autocorrelation or session mixing is distorting one of the two estimates. Readers who want to apply the estimated d to produce a fractionally differenced price series for use as an ML feature can do so using the engine described by Njoroge (2026b), which runs efficiently on live MetaTrader 5 feeds with O(width) computation per bar.

Part 4 uses both hurst\_exponent and arfima\_d as inputs to the volatility suite: a FIGARCH‑inspired realized volatility model that weights its memory structure by the long‑memory measurements established in Parts 2 and 3.

*

## Key paras

[Part 1](https://www.mql5.com/en/articles/22263 "Market Microstructure in MQL5: Robust Foundation (Part 1)") of this series built a defensive foundation: guarded math, validated price feeds, and stable statistical primitives. [Part 2](https://www.mql5.com/en/articles/22553/235308 "Market Microstructure in MQL5: Measuring Long Memory (Part 2)") added three Hurst estimators and established a key empirical result for US100 M1 Globex futures: the confidence‑weighted H hovers near 0.5, with the pooled post‑open estimate at 0.511 and the rolling bar‑by‑bar mean at approximately 0.48. All three estimators straddle the random walk boundary.

This article adds two functions to MicroStructure\_Foundation.mqh: GPHEstimator() and PopulateARFIMAAnalysis(). They estimate d via log‑periodogram regression, write the result to RobustFractalAnalysis.arfima\_d, and validate it against the Hurst output from Part 2. An empirical study on 72 NY sessions of US100 M1 data confirms that d is close to zero—consistent with Part 2—and quantifies the session‑to‑session variation.

For US100 M1 with H ≈ 0.48–0.51 from Part 2, the implied d ranges from approximately −0.02 to +0.01. This near‑zero value has an immediate practical implication: standard first differencing (log returns) is the correct transformation for this instrument and timeframe. Neither over‑differencing nor under‑differencing is indicated.

The bandwidth parameter m controls how many frequencies enter the regression. The theoretical recommendation from Geweke and Porter‑Hudak (1983) is m = floor(N^g) with g in (0.5, 1.0). The choice g = 0.65 is the conventional default. It is encoded as GPH\_BANDWIDTH\_EXP. For a 390‑bar NY session (09:30–16:00 ET on US100 M1), this gives m ≈ 36 frequency points.

The inner DFT loop runs in O(n · m) time. For a 390‑bar session with m = 36, this is approximately 14,000 floating‑point operations—negligible in an indicator's OnCalculate() context. The log and trigonometric calls use the foundation's SafeLog() and MQL5's MathSin() and MathCos().

Three validation layers guard the execution path before d is computed. First, ValidateSymbolV2() confirms that the symbol is tradable and the minimum period is met. Second, SafeCopyClose() handles the price fetch—the same function used by every Part 2 estimator, so its error behavior is already tested. Third, the return‑construction loop filters invalid prices and artifacts: returns above ±10% are discarded as tick errors or rollover artifacts. On US100 M1, genuine single‑minute moves of 10% do not occur.

The two most common causes of H‑d discrepancy are short‑range autocorrelation (which biases the Hurst R/S estimator upward, as described by Lo (1991)) and session mixing (described in Part 2 as Finding 3). Both produce an apparent H above 0.5, while GPH, which focuses on the low‑frequency behavior, returns d near zero.

The same data used in Part 2 underpins this study: 72 NY sessions of US100 M1 Globex futures from January to May 2026. The New York session is defined as 09:30–16:00 Eastern Time. Returns are log differences of one‑minute closing prices. Returns with an absolute value above 0.1 (10%) are discarded as data artifacts; none were genuine in this dataset.

Applying GPH to all 27,930 NY session bars pooled together gives d = −0.006, implying H = 0.494. This is within 0.005 of the Part 2 pooled Hurst result (H = 0.511 by confidence‑weighted blend). The two estimators agree that US100 M1 operates near the random walk boundary. The R² of the pooled regression is 0.0001—effectively zero—confirming that the log‑periodogram has no meaningful linear slope near zero frequency.

Fig. 1: Distribution of session-level GPH d estimates (left) and d against implied H = d + 0.5 (right). 72 sessions, US100 M1, January–May 2026.

Across 72 sessions, the mean d is −0.016 and the median is −0.012. The standard deviation is 0.153. The interquartile range runs from −0.124 to 0.084. A small negative bias is present—consistent with the mild anti‑persistence suggested by Part 2's rolling mean of H ≈ 0.48—but it is not significant relative to the session‑to‑session variance.

Fig. 2: Session-by-session GPH d across 72 sessions. Green: d below −0.1. Red: d above 0.1. Blue: near-zero d. Line: 5-session rolling mean.

---

# 22638: Market Microstructure in MQL5 (Part 4): Volatility That Remembers

## Sections

### Empirical Study: NQ M1 Volatility and Multifractal Width

All estimators were applied to 514 NY sessions of NQ E-mini Nasdaq 100 futures (CME Globex), covering May 2024 through May 2026. The NY session filter retains bars with open time in [14:30, 21:00) UTC. Sessions with fewer than 300 M1 bars are excluded. Data were sourced from a retail futures data provider with CME Group as the underlying exchange. The asymmetry (skewness) field is winsorized at the 1st and 99th percentiles (−1.39 and 1.85) to remove three sessions whose extreme skewness values (maximum 7.81) indicated intraday data artifacts not captured by the |r| < 0.1 return filter. All other fields use raw values. All 514 sessions pass the MFDFA minimum R² threshold of 0.65 (observed minimum R² = 0.851). The leverage values reported in this section come from the sign-conditioned variance proxy computed in the Python analysis script. In MQL5, LeverageEffect() uses GJR-GARCH(1,1,1) via the Dube library when USE\_GJR\_LEVERAGE is defined; in that mode it returns values in [0, 1] only. The proxy returns values in [−1, +1]; therefore, negative leverage can appear, as observed during the April 2025 tariff episode.



Figure 1 — Session realized volatility (annualized %) across 514 NQ sessions, May 2024–May 2026. Shaded regions mark identified stress episodes. The April 2025 tariff shock (dark red) is the dominant event at 38.2% mean annualized volatility, 3.1× the normal baseline.

**Table 1 – Summary Statistics (514 NY sessions, NQ M1 futures)**

| Metric | Mean | Std Dev | Min | 25% | Median | 75% | Max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Realized Vol (per bar) | 0.00042 | 0.00018 | 0.00013 | 0.00029 | 0.00038 | 0.00050 | 0.00310 |
| Duration Vol (annualized %) | 13.39% | 7.45% | 4.38% | 9.1

### Practical Interpretation and Trading Thresholds

All thresholds below are derived from the empirical distribution across 514 NQ M1 sessions, May 2024–May 2026. They are heuristic operational cutoffs based on empirical quantiles, not formal hypothesis-test critical values or decision-theoretically optimal boundaries. They are specific to NQ M1 and this sample period. Users should treat them as starting points and re-derive them on their own instrument, timeframe, and data window.

| Measure | Threshold | Basis | Interpretation | Action |
| --- | --- | --- | --- | --- |
| Clustering Index | > 0.20 | 75th pct | Strong ARCH effect; volatility predictable bar-to-bar | Use volatility-targeted sizing; prefer FIGARCH proxy |
| Clustering Index | < 0.08 | 25th pct | Weak clustering; returns near i.i.d. | Simpler realized vol sufficient |
| Leverage Effect (GJR) | > 0.13 | 75th pct | Significant asymmetry; negative shocks amplify vol more | Widen stops on short side; reduce long-entry size |
| Leverage Effect (GJR) | < −0.10 | — | Inverse asymmetry (stress snap-back regime) | Do not apply standard leverage logic; reduce size |
| Jump Intensity | > 2.1% | 90th pct | Elevated extreme returns | Scale back position; validate data feed |
| Jump Intensity | > 5% | — | Likely data artifact | Reject session data; do not trade |
| Δα (multifractal) | < 0.76 | 25th pct | Moderate mixing; H and d partially reliable | Fractional vol preferred; use H/d with caution |
| Δα (multifractal) | > 0.99 | 75th pct | Extreme mixing; H and d unreliable averages | Prefer the FIGARCH-inspired proxy; treat H/d as less informative |
| R² confidence | < 0.65 | — | MFDFA estimate unreliable (rare on NQ) | Treat Δα as unavailable |




### 

### Folder Structure and Include Path

All Part 4 functions are 

### Conclusion

This article revised and extended the volatility functions in MicroStructure\_Foundation.mqh, addressing the methodological weaknesses identified during moderator review.

Three principal changes distinguish this submission from the original. First, LeverageEffect() now fits a GJR-GARCH(1,1,1) model via the Dube library, returning the normalized asymmetry ratio γ/(α + γ + β) rather than a next-bar variance heuristic. Second, MultifractalSpectrum() now returns the Legendre-transform Δα with an R² confidence field, replacing the τ-spread proxy. Third, JumpIntensity() uses bipower variation as the baseline, making the threshold robust to the jump contamination it is designed to detect.

The empirical study on 514 NQ M1 futures sessions (May 2024–May 2026) confirms: the three volatility estimators track each other with pairwise correlations above 0.97; the bipower jump intensity averages 1.4% with no session exceeding 5%; the Legendre-transform Δα has median 0.875 with mean R² of 0.972; and all 514 sessions pass the R² confidence threshold of 0.65.

The practical outcome is a fully populated VolatilityAnalysis struct: realized\_vol and fractional\_vol measure level and memory; clustering\_index measures bar-to-bar predictability; leverage\_effect (GJR) measures asymmetric response; jump\_intensity flags contaminated sessions; asymmetry describes the return distribution; and the FIGARCH proxy gives a memory-adjusted conditional variance when Δα indicates strong regime mixing. Part 5 will use these measures as conditioning inputs to microstructure noise estimation and order flow analysis.

### 

### References

- [Andersen, T.G., Bollerslev, T. & Diebold, F.X. (2007). Roughing it up: Including jump components in the measurement, modeling, and forecasting of re

## Key paras

[Part 1](https://www.mql5.com/en/articles/22263 "Market Microstructure in MQL5: Robust Foundation (Part 1)") built a defensive foundation: guarded math, validated price feeds, and stable statistical primitives. [Part 2](https://www.mql5.com/en/articles/22553 "Market Microstructure in MQL5: Measuring Long Memory (Part 2)") added confidence-weighted Hurst estimation, establishing that US100 M1 Globex operates near the random-walk boundary (pooled H = 0.511, rolling H ≈ 0.48). [Part 3](https://www.mql5.com/en/articles/22598 "Market Microstructure in MQL5: Estimating ARFIMA d with GPH (Part 3)") added the GPH estimator for the fractional differencing parameter d, with pooled d = −0.006 and sessi

Standard volatility indicators — ATR and standard deviation of returns — treat each bar as independent. They ignore four empirical facts about financial volatility: clustering (large moves follow large moves), persistence (volatility shocks decay slowly), asymmetry (negative returns increase future volatility more than positive returns of the same magnitude), and regime mixing (the series may be a mixture of different scaling laws, making average measures like H and d misleading). On intraday US100 M1 data, these properties directly affect position sizing, stop-loss placement, and signal filtering. A trading system that ignores them is systematically miscalibrated.

This article adds two measurement families to MicroStructure\_Foundation.mqh: (1) a revised MFDFA-based multifractal spectrum that returns Δα with an R² confidence field, replacing the raw τ-spread proxy used in the original submission; (2) a volatility suite: RealizedVolatility(), DurationVolatility(), FractionalVolatility(), a FIGARCH-inspired proxy, VolatilityClusteringIndex(), LeverageEffect(), JumpIntensity(), and PopulateVolatilityAnalysis().

The empirical study in this article uses NQ E-mini Nasdaq 100 futures (CME Globex) rather than the US100 CFD instrument referenced in earlier drafts. NQ is the exchange-traded underlying contract; US100 is a retail CFD product whose price is derived from the index, not from actual futures order flow. The microstructure properties being measured — volatility clustering, leverage asymmetry, jump intensity, multifractal structure — are properties of price formation at the exchange level. Using the actual futures contract is therefore a more appropriate methodological choice for this analysis. The 2-year NQ M1 dataset (514 NY sessions, May 2024–May 2026) captures four macro stress episodes relev

FIGARCHVolatility() is **not** a fitted FIGARCH model. A proper FIGARCH estimation requires maximum-likelihood optimization over hundreds of observations and is computationally unsuitable for real-time MQL5 use. The function implemented here is a power-law weighted realized volatility, where the weights are derived from the GPH d estimate produced by Part 3. It is a FIGARCH-inspired engineering proxy. It captures the memory structure of the volatility process without the estimation overhead of a full FIGARCH specification.

Deliverable: eight functions updated or added to MicroStructure\_Foundation.mqh, a revised MFDFA returning Δα with R² confidence, and the VolatilityAnalysis struct fully populated with no placeholder fields. No new include file is created. The two companion SSRN working papers that document the empirical foundation for this series are available at [SSRN 6809080](https://papers.ssrn.com/abstract=6809080 "Measuring the Memory Structure of Intraday Returns") and [SSRN 6847024](https://papers.ssrn.com/abstract=6847024 "Intraday Microstructure Dynamics of E-mini S&P 500 Futures").

Volatility clustering means that large price changes tend to be followed by large price changes (of either sign), and small changes by small changes. Engle (1982) formalized this as the ARCH effect, for which he received the Nobel Prize. The lag-1 autocorrelation of squared returns is a direct measure of clustering. Values above 0.2 on daily data are typical; on intraday data, clustering is often stronger. VolatilityClusteringIndex() measures this directly. It is a diagnostic proxy, not a fitted model.

Volatility jumps are rare but consequential. Andersen, Bollerslev and Diebold (2007) proposed bipower variation (BPV = (π/2)·mean(|r t |·|r t−1 |)) as a jump-robust baseline. JumpIntensity() uses BPV as the threshold rather than the sample standard deviation, because a simple σ-threshold is contaminated by the very jumps it is trying to detect. On NQ M1, the 514-session empirical study shows a mean jump intensity of 1.4% with a 90th percentile of 2.1%. A value above 5% is likely to indicate data artifacts — bad ticks, contract rollovers, or feed anomalies — rather than genuine market jumps.

The MFDFA algorithm is unchanged in structure. The revision affects the output metric only: the raw τ-spread is replaced by the Legendre-transform Δα, and the function now accepts a confidence output parameter. The outlier filter (|r| ≥ 0.1) is retained; it removes contract rollovers and bad ticks that would otherwise distort the negative-q moments, where large fluctuations dominate the q-th power sum.

RealizedVolatility() returns the square root of the mean of squared log-returns. It is the benchmark estimator: it makes no assumption about memory or regime structure. DurationVolatility() annualizes RV using the bar duration. The original implementation used 252 × 86,400 seconds as the denominator, which assumes round-the-clock trading. The NY session runs 09:30–16:00 ET — 23,400 seconds per day. The corrected function uses 23,400 for M1 data and the full-day figure for daily and higher timeframes.

FIGARCHVolatility() is **not** a fitted FIGARCH model. A full FIGARCH requires maximum-likelihood estimation, which is computationally unsuitable for real-time M1 use on sessions of 390 bars. The function is a power-law weighted conditional variance proxy, where the weight recursion w j = w j−1 ·(j−1−d)/j is the truncated fractional differencing kernel of Baillie et al. (1996), applied directly to squared returns. The baseline variance uses bipower variation rather than the sample mean, making the floor robust to isolated jump returns. The original hardcoded omega = 1e-6 and beta = 0.85 are removed; the function now relies entirely on the GPH d from Part 3 and the bipower baseline.

All estimators were applied to 514 NY sessions of NQ E-mini Nasdaq 100 futures (CME Globex), covering May 2024 through May 2026. The NY session filter retains bars with open time in [14:30, 21:00) UTC. Sessions with fewer than 300 M1 bars are excluded. Data were sourced from a retail futures data provider with CME Group as the underlying exchange. The asymmetry (skewness) field is winsorized at the 1st and 99th percentiles (−1.39 and 1.85) to remove three sessions whose extreme skewness values (maximum 7.81) indicated intraday data artifacts not captured by the |r| < 0.1 return filter. All other fields use raw values. All 514 sessions pass the MFDFA minimum R² threshold of 0.65 (observed min

---

# 23372: Market Microstructure in MQL5 (Part 8): Micro-Trend Strength

## Sections

## Empirical Study: NQ M1, 514 Sessions

The composite score was computed bar-by-bar on 514 NY sessions of NQ M1 futures (May 2024–May 2026) using EMA periods 5/8/13 and ATR period 14. Sessions with fewer than 300 bars after the NY open filter were excluded, consistent with the Part 4–7 empirical methodology. The Part 7 regime classification was merged on session date to support the adaptive-threshold analysis.



Figure 1 - Distribution of session-mean micro-trend strength across 514 NQ M1 sessions (May 2024-May 2026), stacked by regime. The distribution is approximately symmetric around a slight positive mean (0.036). Trending sessions cluster toward positive values; Stressed and Noisy sessions are broadly distributed.



Figure 2 - Mean absolute micro-trend strength by regime. The Stressed regime has the highest absolute strength (0.673), reflecting wide swings in both directions with no net directional bias. The Mean-Reverting regime has the lowest (0.644).

### Table 1 — Signal frequency by regime (fixed thresholds: 0.70/0.30)

| Regime | Sessions | Mean strength | Strong up (%) | Strong down (%) | Flat (%) | Persistent (%) |
| --- | --- | --- | --- | --- | --- | --- |
| Normal | 257 | 0.042 | 8.3 | 6.1 | 48.2 | 12.4 |
| Stressed | 110 | 0.008 | 5.1 | 4.8 | 61.3 | 6.7 |
| Noisy | 51 | 0.031 | 7.2 | 5.9 | 53.8 | 9.1 |
| Informed | 38 | 0.187 | 14.6 | 4.2 | 39.5 | 18.3 |
| Trending | 37 | 0.241 | 18.9 | 3.7 | 33.1 | 23.6 |
| Mean-Reverting | 21 | -0.163 | 3.8 | 12.4 | 41.9 | 14.2 |

Three findings stand out. First, the Trending regime produces the highest strong-up rate (18.9%) and the highest persistence rate (23.6%) — consistent with Part 7's finding that Trending sessions have the highest clustering index (0.286) and the highest mean confidence (0.593). The micro-

## Practical Usage

The two-overload design means Part 8 can be used in two ways: as a standalone bar-by-bar trend score without requiring Parts 4–7, or as a regime-conditioned signal when the full measurement chain is in use.

Standalone usage, calling one bar behind the current bar to avoid lookahead:




Session-adaptive usage, with the full Part 7 measurement chain:

## Limitations

EMA-based composites are lagging by construction. The five-bar slope lookback and the ATR normalization reduce but do not eliminate the lag relative to underlying price action. At NQ M1 during a fast NY-open move, the composite will typically reach its peak reading two to four bars after the directional move has started.

The contradiction penalty addresses the most common form of false signal — alignment-price disagreement — but does not handle all false signals. A trending EMA structure with price above the fast EMA and high volume can still produce a positive score in a mean-reverting session. The regime classifier from Part 7 provides the correct tool for excluding such sessions at the session level; combining Part 8 with Part 7 via the adaptive overload is the intended use pattern for production trading.

The EMA period choice of 5/8/13 is not validated against alternative parameterizations. These are Fibonacci-sequence periods with harmonic relationships, which is the motivation for the choice, but other period triples may produce better signal quality on different instruments or timeframes. The threshold constants MT\_THRESH\_HIGH\_BASE (0.70) and MT\_THRESH\_LOW\_BASE (0.30) are calibrated to NQ M1 and the NY session; other environments may require different values.

The volume component uses tick volume rather than traded contract volume. On NQ M1, tick volume (the number of price updates per bar) is a reasonable proxy for trading activity, but it is not identical to the number of contracts traded. The proxy relationship is stable during normal sessions and degrades during data-feed anomalies, which are identified as Stressed sessions by Part 7 and which produce near-zero composite scores in any case.

## Key paras

[Parts 1 through 7](https://www.mql5.com/en/users/gcg26/publications) of this series build a complete measurement layer for NQ M1 microstructure. Part 1 hardened the mathematical foundation. Parts 2 and 3 measured whether price returns have memory. Part 4 measured how volatility persists. Part 5 decomposed price variation into signal and noise. Part 6 measured the direction of informed flow. Part 7 condensed those eleven measurements into a single regime label and confidence score. What none of them did was tell you, on the current bar, whether the short-term trend is up, down, or flat.

That is the gap Part 8 closes. A regime label describes the session environment at a 90-to-390-bar horizon. A scalper at the NY open needs a bar-by-bar answer to a narrower question: is the EMA structure currently aligned and accelerating in one direction, or is it conflicted and choppy? A standard moving average crossover gives a binary answer. What is needed is a continuous score that reflects the degree of alignment, not just its direction.

The new functions integrate with the Part 7 regime classifier through a session-adaptive threshold variant. When a RegimeAnalysis struct is available, the strong- and weak-signal cutoffs are scaled by reg.confidence . High-confidence sessions (Trending, Informed) loosen thresholds so signals fire more readily. Low-confidence sessions (Stressed, Noisy) tighten them. This is the first explicit downstream use of the Part 7 confidence field in the series.

The empirical study applies the composite to 514 NQ M1 NY sessions (May 2024–May 2026), the same dataset used in Part 7. The primary finding is that the signal distributes asymmetrically across regimes: Trending sessions produce the highest persistence rate (3+ consecutive same-direction bars), while Stressed sessions produce the most flat readings. The adaptive threshold transfers approximately 18% of Stressed-session signals into the no-signal zone compared to fixed thresholds, reducing false-signal exposure without requiring a rule change.

**Deliverable.** Four new functions added to MicroStructure\_Foundation.mqh : GetMicroTrendStrength() , GetTrendLabel() , GetBinarySignal() , and GetPersistentTrendDirection() . A new MicroTrendAnalysis struct and TREND\_LABEL enum. Two PopulateMicroTrendAnalysis() overloads — one standalone, one session-adaptive. All header additions are appended to the existing MicroStructure\_Foundation.mqh as a Part 8 section, following the convention established in Parts 2 through 7. Part 8 is also the first part of the series to produce a standalone indicator file, MicroTrendStrength.mq5 .

EMA crossovers are the most widely used trend signal in retail algorithmic trading, and they have a well-documented failure mode: when the fast EMA crosses the slow EMA, the signal fires at a point in time that is already in the past. The crossover is a lagging acknowledgment of a move that happened bars ago. On NQ M1 at the NY open, where a 300-point move can develop in under ten minutes, a lagging signal is often not actionable.

The distance from the current close to each EMA is normalized by the 14-period ATR and compressed by a hyperbolic tangent. This captures whether price is extended relative to each EMA or tightly bundled around it. The three distances are weighted 0.40 (fast), 0.30 (medium), 0.30 (slow). The tanh compression is important: without it, a session with an unusually large range would dominate the price-position sub-score and overwhelm the other components. The tanh maps any distance, however large, to the interval (−1, +1), so the price-position sub-score is always bounded and comparable across sessions.

Current bar tick volume is compared to the 20-bar rolling average. The ratio is mapped to [0.5, 1.5] via clip(0.5 + ratio, 0.5, 1.5) , which amplifies the composite when volume is above average and dampens it when volume is below average. The bounds prevent a single extreme-volume bar from dominating the score and prevent a low-volume session from producing a negative multiplier. This multiplier is applied after the additive combination of alignment, price position, and slope.

A seven-state TREND\_LABEL enumeration provides a descriptive classification from TREND\_STRONG\_DOWN (−3) to TREND\_STRONG\_UP (+3). The MicroTrendAnalysis struct carries the continuous strength score, the label, a binary signal (−1/0/+1), the persistent direction over N consecutive bars, and the session-adaptive threshold values that were used in classification.

GetTrendLabel() maps the continuous strength score to the seven-state TREND\_LABEL enum. GetBinarySignal() maps it to {−1, 0, +1}. Both accept optional threshold parameters so session-adaptive values from Part 7 can be passed in directly. GetPersistentTrendDirection() calls GetBinarySignal() on N consecutive prior bars and returns the common direction only if all N bars agree.

The composite score was computed bar-by-bar on 514 NY sessions of NQ M1 futures (May 2024–May 2026) using EMA periods 5/8/13 and ATR period 14. Sessions with fewer than 300 bars after the NY open filter were excluded, consistent with the Part 4–7 empirical methodology. The Part 7 regime classification was merged on session date to support the adaptive-threshold analysis.

Figure 1 - Distribution of session-mean micro-trend strength across 514 NQ M1 sessions (May 2024-May 2026), stacked by regime. The distribution is approximately symmetric around a slight positive mean (0.036). Trending sessions cluster toward positive values; Stressed and Noisy sessions are broadly distributed.

---

# 8818: Prices in DoEasy library (part 59): Object to store data of one tick

## Sections

### What's next?

In the next article we will start creating the tick data collection for one symbol.

All files of the current library version are attached below together with the test EA file for MQL5. You can download them and test everything.  
 Leave your comments, questions and suggestions in the comments to the article.

## Key paras

In the concept of tick data storage, the minimal unit of data volume shall be values of price structure on one tick. Such values are described with the use of a structure for storing the last prices by symbol [MqlTick](https://www.mql5.com/en/docs/constants/structures/mqltick). An object to store such values will possess additional properties: spread - the difference of Ask and Bid prices and the symbol the data of which one tick are described by the object.

The article describes the basic principles and methods that allow you to analyze any strategy using spreadsheets (Excel, Calc, Google). The obtained results are compared with MetaTrader 5 tester.

---

# 8912: Prices in DoEasy library (part 60): Series list of symbol tick data

## Sections

### What's next?

In the next article, we will create the collection class of tick data of all symbols used in the program and implement the update of all created lists in real time.

All files of the current version of the library are attached below together with the test EA file for MQL5 for you to test and download.   
 The tick data classes are under development, therefore their use in custom programs at this stage is strongly not recommended.  
 Leave your questions and suggestions in the comments.

## Key paras

---

# 8952: Prices in DoEasy library (part 61): Collection of symbol tick series

## Sections

### What's next?

In the next article, I will start creating realtime update and control of data events in the tick collection created today.

All files of the current version of the library are attached below together with the test EA file for MQL5 for you to test and download.   
 The tick series collection class is under development, therefore its use in custom programs at this stage is strongly not recommended.  
 Leave your questions and suggestions in the comments.

## Key paras

---

# 8988: Prices in DoEasy library (part 62): Updating tick series in real time, preparation for working with Depth of Market

## Sections

### What's next?

In the next article, I will start creating the library functionality allowing to work with symbol DOMs.

All files of the current version of the library are attached below together with the test EA file for MQL5 for you to test and download.   
 Leave your questions and suggestions in the comments.

## Key paras

To get the [BookEvent](https://www.mql5.com/en/docs/runtime/event_fire#bookevent) events for any symbol, simply subscribe to receive them for this symbol using the [MarketBookAdd()](https://www.mql5.com/en/docs/marketinformation/marketbookadd) function. To cancel subscription for receiving BookEvent for a certain symbol, call the [MarketBookRelease()](https://www.mql5.com/en/docs/marketinformation/marketbookrelease) function.

---

# 9010: Prices in DoEasy library (part 63): Depth of Market and its abstract request class

## Sections

### What's next?

In the next article, we will continue creating the functionality for working with DOM.

All files of the current version of the library are attached below together with the test EA file for MQL5 for you to test and download.   
 The classes for working with DOM are under development, therefore their use in custom programs at this stage is strongly not recommended.   
 Leave your questions and suggestions in the comments.

## Key paras

---

# 9044: Prices in DoEasy library (Part 64): Depth of Market, classes of DOM snapshot and snapshot series objects

## Sections

### What's next?

In the next article, I will create the collection of DOM snapshot series allowing users to fully work with DOMs of any symbols having active subscription to the DOM and enabled broadcast.

All files of the current version of the library are attached below together with the test EA file for MQL5 for you to test and download.   
 The classes for working with DOM are under development, therefore their use in custom programs at this stage is strongly not recommended.   
 Leave your questions and suggestions in the comments.

## Key paras

---

# 9095: Prices and Signals in DoEasy library (Part 65): Depth of Market collection and the class for working with MQL5.com Signals

## Sections

### What's next?

In the next article, I will create a collection of MQL5 signals.

All files of the current version of the library are attached below together with the test EA file for MQL5 for you to test and download.   
 Leave your questions and suggestions in the comments.

## Key paras

We have all the necessary objects for creating the DOM collection. Namely, we have the DOM order object represented by the [MqlBookInfo](https://www.mql5.com/en/docs/constants/structures/mqlbookinfo) structure in the terminal. When the [BookEvent](https://www.mql5.com/en/docs/runtime/event_fire#bookevent) event arrives, the [OnBookEvent()](https://www.mql5.com/en/docs/event_handlers/onbookevent) handler is called. A symbol, on which the DOM change event has occurred, is specified as its parameter. We are able to receive all current DOM data to the MqlBookInfo structure array. The collection of this data in the library is described by the DOM snapshot object featuring order objects we obtaine

To use the functionality of working with DOMs, we need to subscribe to receive DOM change events for each symbol. This feature is already present in the symbol object class. Besides, the DOM snapshot series object features the flag indicating the need to enable/disable handling of DOM change events. In other words, even if subscription to BookEvent events is active, we may temporarily disable working with DOM on this symbol using the flag. **Use the following method to set the flag indicating the necessity to handle BookEvent events by symbol:**

Add the new BookEvent event handler. In the method setting the list of used symbols in the symbol collection, apart from passing the number of days for the tick series, add passing the maximum number of DOM snapshots:

---

# 1179: MQL5 Cookbook: Handling BookEvent

## Sections

### Conclusion

This article is dedicated to another event of the Terminal - the Depth of Market event. This event is often at the core of high frequency trading algorithms (HFT). This type of trading is gaining popularity among traders.

I hope that traders starting to program on MQL5 will find included examples of handling the Depth of Market event useful. The source files attached to this article are convenient to be put into the project folder. In my case it is \MQL5\Projects\BookEvent.

Translated from Russian by MetaQuotes Ltd.   
Original article: <https://www.mql5.com/ru/articles/1179>

**Attached files** |

## Key paras

As is well known, the [MetaTrader 5](https://www.metatrader5.com/ "https://www.metatrader5.com/") trading terminal is a multi-market platform, that facilitates trading on Forex, stock markets, Futures and Contracts for Difference. According to the [Freelance](https://www.mql5.com/en/job) section stats, the number of traders trading not only on Forex market is growing.

In this article I would like to introduce novice MQL5 programmers to the [BookEvent](https://www.mql5.com/en/docs/runtime/event_fire#bookevent) handling. This event is connected with Depth of Market—an instrument for trading stock assets and their derivatives. Forex traders, however, may find Depth of Market useful too. In ECN accounts, liquidity providers supply data on the orders, though only within their aggregator model. These accounts are becoming more popular.

According to the [Documentation](https://www.mql5.com/en/docs), this event is generated when Depth of Market status changes. Let us agree that [BookEvent](https://www.mql5.com/en/docs/runtime/event_fire#bookevent) is a Depth of Market event.

The EA was launched for the [SBRF-12.14](http://www.moex.com/ru/contract.aspx?code=SBRF-12.14 "http://moex.com/ru/contract.aspx?code=SBRF-12.14") futures in a debug mode. The sequence of records in the Experts log will be as follows:

All programs, working with Depth of Market data, will have a form of either an Expert Advisor or an indicator, as only these MQL5 programs feature the [BookEvent](https://www.mql5.com/en/docs/runtime/event_fire#bookevent) event handler.

Then the handler of [BookEvent](https://www.mql5.com/en/docs/runtime/event_fire#bookevent) for the EA and, essentially, the indicator, will look as follows:

So, every time [BookEvent](https://www.mql5.com/en/docs/runtime/event_fire#bookevent) is generated, the panel will update its data. We are going to name the updated version of the program as BookEventProcessor2.mq5.

I hope that traders starting to program on MQL5 will find included examples of handling the Depth of Market event useful. The source files attached to this article are convenient to be put into the project folder. In my case it is \MQL5\Projects\BookEvent.

[BookEvent.zip](https://www.mql5.com/en/articles/download/1179/bookevent.zip "Download BookEvent.zip") (3.84 KB)

---

# 1793: MQL5 Cookbook: Implementing Your Own Depth of Market

## Sections

### Conclusion

The article turned out to be rather dynamic. We have analyzed Depth of Market from a technical perspective and proposed a high-performance class-container to work with it. As an example, we have created a Depth of Market indicator based on this class-container, which can be compactly displayed on the instrument's price chart.

Our Depth of Market indicator is very basic and it still lacks a number of things. However, the main objective was achieved - we made sure that with a CMarketBook class that we have created we can relatively quickly build complex Expert Advisors and indicators for analyzing current liquidity with the instrument. When designing the CMarketBook class a lot of attention has been paid to performance, since Depth of Market has a very dynamic table that changes hundreds of times per minute.

The class described in the article can become a solid base for your scalper or a high-frequency system. Feel free to add functionality specific to your system. To do this, simply create your Depth of Market class derived from CMarketBook, and write extension methods you will need. We do hope, however, that even those basic properties provided by Depth of Market will make your work easier and more reliable.

Translated from Russian by MetaQuotes Ltd.   
Original article: <https://www.mql5.com/ru/articles/1793>

**Attached files** |

## Key paras

- [Introduction](https://www.mql5.com/en/articles/1793#introduction) - [Chapter 1. Standard DOM in MetaTrader 5 and methods of using it](https://www.mql5.com/en/articles/1793#chapter_1_standard_depth_of_market_in_metatrader_5)   - [1.1. Standard Depth of Market in MetaTrader 5](https://www.mql5.com/en/articles/1793#c1_1)   - [1.2. Event model for working with Depth of Market](https://www.mql5.com/en/articles/1793#c1_2)   - [1.3. Receiving second level quotes with MarketBookGet functions and MqlBookInfo structure](https://www.mql5.com/en/articles/1793#c1_3) - [Chapter 2. CMarketBook class for easy access and operation with Depth of Market](https://www.mql5.com/en/articles/1793#chapter_2_cmark

- Buy and Sell limit orders, their price levels and volume (standard form of classical DOM); - current spread level and price levels occupied by limit orders (advanced mode); - tick chart and visualized Bid, Ask and last trade volumes; - total level of Buy and Sell orders (displayed as two lines at the tick chart's top and bottom, respectively).

The list provided confirms that Depth of Market features are more than impressive. Let's find out how to operate with data by getting access to it programmatically. First of all, you need to get an idea about how is Depth of Market established ​​and what is the key to its data organization. For more information read the article "[Principles of Exchange Pricing through the Example of Moscow Exchange's Derivatives Market](https://www.mql5.com/en/articles/1284)" in chapter "[13. Matching Sellers and Buyers. Exchange Depth of Market](https://www.mql5.com/en/articles/1284#c1_3)". We will not be spending much time on this table description, assuming that the reader has already sufficient knowledge

Since there are tens or even hundreds of different symbols available on the terminal with their own Depth of Market, the number of calls of OnBookEvent function can be enormous and resource intensive. In order to avoid this, the terminal must be notified in advance when running an indicator or an Expert Advisor from which instruments in particular it is required to obtain information about second level quotations (information provided by Depth of Market is also called this way). A special system function MarketBookAdd is used for such purposes. For example, if we want to obtain information about Depth of Marked based on instrument Si-9.15 (futures contract for USD/RUR with expiration in Sept

Apart from the actual indexes, it is often needed to know the average spread level for the current instrument. Spread is a difference between the best Bid and Ask prices. CMarketBook class allows to obtain the average value of this parameter using the InfoGetDouble method by calling it with the MBOOK\_AVERAGE\_SPREAD modifier. CMarketBook calculates the current spread in the Refresh method as well as its average value by memorizing the number of this method's calls.

Two Depth of Market are shown on Figure 3. The first of them is a futures contract DOM for two-year federal loan bonds (OFZ2-9.15). The second is a EUR/USD futures contract (ED-9.15). It shows that for OFZ2-9.15 the number of Buy price levels is four, while the number of Sell price levels is eight. On a more liquid ED-9.15 market the amount of both Buy and Sell levels is 12 for each of the parties. In case with ED-9.15 the method of determining indexes by diving in two would have worked, and with OFZ2 - it wouldn't.

Often Depth of Market is used by traders to determine the current market liquidity, *i.e. Depth of Market is used as an additional instrument to control risks*. If market liquidity is low, entering market through market orders can cause high slippage. Slippage always implies additional losses that may be of significant value.

To avoid such situations, the additional methods for controlling the market entry have to be used. For more information please read the article "[How to Secure Your Expert Advisor While Trading on the Moscow Exchange](https://www.mql5.com/en/articles/1683)". Therefore, we will not describe these methods in detail and will only mention, that by getting access to Depth of Market we can estimate the value of a potential slippage before entering a market. The size of a slippage depends on two factors:

Having access to Depth of Market allows us to see at what volume and prices our order will be executed. If we know the volume of our order, we can calculate the weighted average price for market entry. The difference between this price and the best Bid or Ask price (depending on the entrance direction) will be our slippage.

CMarketBook class includes a special method to calculate this characteristic - GetDeviationByVol. Since the deal's volume effects the slippage size, it is required to pass the volume expected to be executed on the market to the method. Since this method uses integer-valued arithmetic of volumes, as adopted on the Moscow Exchange futures market, the method takes volume as a long type value. In addition to that, the method needs to know for which side of liquidity the calculation has to be performed, therefore a special ENUM\_MBOOK\_SIDE enumeration is used:

One distinguishing feature of the Moscow Exchange is a transmission of information about the total number of limit orders in real time. This article highlights the operation of Depth of Market as such, without being addressed to any specific market. However, this information despite being specific (peculiar to a specific trading platform), is available at the terminal's system level. Moreover, it expands data provided by Depth of Market. It was therefore decided to extend the enumeration of property modifiers and to include the support of these properties directly to the Depth of Market CMarketBook class.

- number of Sell limit orders placed for instrument at the current time; - number of all Buy limit orders placed for instrument at the current time; - total volume of all Sell limit orders placed for instrument at the current time; - total amount of all Buy limit orders placed for instrument at the current time; - number of open positions and open interest (only for futures markets).

---

# 3336: Implementing a Scalping Market Depth Using the CGraphic Library

## Sections

### Conclusion

We have discussed the process of scalping Market Depth development.

- We have improved the appearance of the order book
- We have added to the panel a tick chart based on CGraphic and upgraded the graphical engine
- We have improved the Market Depth class and have implemented an algorithm for synchronizing ticks with the current order book.

However, even the current version of Market Depth is very far from a full-fledged scalping version. Of course, many users could be disappointed, having read the article up to this place and not seeing a full analog of a standard Market Depth or specialized programs like Bondar drive or QScalp. But any complex software product must go through a number of evolutionary steps in its development. Here's what can be added to the Market Depth in further versions:

- The ability to send limit orders straight from the Market Depth
- The ability to track large orders on the tick chart
- Differentiation of Last deals by volume and displaying them in different ways on the chart
- Displaying additional indicators with the tick chart. For example, below the tick chart we can display a histogram of the ratio of all Buy Limit orders to all Sell Limit orders.
- And, finally, the most important part is to download and save the Market Depth history, and to be able to create trading strategies with the offline testing mode.

All these ideas can be implemented. Probably such options will appear some day. If readers find this subject interesting, the series of articles will be continued.

Translated from Russian by MetaQuotes Ltd.   
Original article: <https://www.mql5.com/ru/articles/3336>

**Attached files** |

## Key paras

The order book is a dynamic structure, whose values may change dozens of times per second on volatile markets. To access the current state of the order book, you must handle a special BookEvent in the corresponding event handler, the OnBookEvent function. When the order book changes, the terminal calls OnBookEvent, indicating the symbol corresponding to changes. In the previous article, we developed the CMarketBook class that provided a convenient access to the current order book state. The current state of the order book could be obtained in this class by calling the Refresh() method in the OnBookEvent function. That's how it looked like:

In order to understand how ticks are formed, let's check the article [Principles of Exchange Pricing through the Example of Moscow Exchange's Derivatives Market](https://www.mql5.com/en/articles/1284) and consider a Market Depth for gold:

---

# 18821: Analyzing the Hourly Movement of Trading Symbols and Their Spreads in MetaTrader 5

## Sections

### Features of the trading symbols movement, **interpretation of ISI ProSpread SMA readings**

Key features of the indicator:

Multi-mode analysis (4 equations):

1. SMA Spread/Price — moving average of spread or price,
2. Price Difference — difference in prices (closing-opening),
3. Volatility Index — volatility index,
4. Candle Strength — candle strength.

Flexible settings:

- selecting trading hours (e.g. London session only),
- depth of analysis (number of history days),
- setting up spread coefficients,
- select a timeframe for analysis.

Visualization:

- indicator chart with zero line,
- dashboard with hourly statistics,
- color indication of bullish/bearish periods.

Operation algorithm:

1. collects historical data for a specified period;
2. analyzes price behavior for each hour of the selected range;
3. calculates statistical probabilities;
4. constructs an indicator curve using the selected formula;
5. displays a summary table with the analysis results.

This indicator will be especially useful for intraday traders, arbitrage strategies, seasonal pattern analysis, and confirmation of trading signals.

The figures 1 and 2 below show the hourly movement of the EURUSD trading symbol depending on the hour: at 9:00, EURUSD shows an upward bias with a 64% probability, as indicated by the second line of the dashboard in green.



 Fig. 1. Features of the hourly movement of EURUSD

The external input parameters shown correspond to formula type 2 of the indicator.



Fig. 2. Values of external variables for the EURUSD trading symbol

Figures 3 and 4 show the hourly movement of the GBPUSD trading symbol depending on the hour: at 9:00, EURUSD shows an upward bias with a 68% probability, as indicated by the second line of the dashboard in green.



Fig. 3. Features of 

### Conclusion

ISI ProSpread SMA is more than just an indicator; it is your personal 24/7 statistical analyst. It turns market noise into understandable and verifiable numbers, giving the trader a real statistical advantage. It does not offer a 100% guarantee on every trade, but it builds trading on the principles of probability and mathematical expectation, which is one of the surest paths to stable earnings in financial markets. Each indicator formula offers a unique perspective on market dynamics. In the following articles, we will move on to writing an automated trading approach using trading EAs based on the presented indicators, using MetaTrader 5.

Remember that no indicator gives 100% accurate signals. The ISI ProSpread SMA indicator works best as part of a comprehensive trading system complemented by fundamental analysis.

Translated from Russian by MetaQuotes Ltd.   
Original article: <https://www.mql5.com/ru/articles/18821>

**Attached files** |

## Key paras

Forex is very much like that ocean. For a beginner, this is a flickering of numbers and chaotic candlesticks, but for a professional, it is an orderly flow of capital, driven by fundamental forces, the main one of which is time. The foreign exchange market does not operate in a vacuum - its life cycle is determined by business activity in the world's key financial centers. As one center awakens and begins work, another is already closing. This creates a continuous cycle of liquidity surges, unidirectional price movements, volatility, and, most importantly for us, predictable price behavior patterns. In the [previous article](https://www.mql5.com/en/articles/15622), we assessed the quality of

- ISI — Index Seasonality Indicator (seasonality indicator), - Spread — spread (working with a pair of instruments), - SMA — Simple Moving Average.

A trading session is defined as a period of time during which banks and trading platforms of countries within the same geographic area are active in the foreign exchange market. Trading determines fluctuations in global currency prices, allowing traders to buy lower and sell higher, profiting from the difference.

A session is the official trading time of the exchanges, when most currency trades are carried out, orders for securities and other financial instruments are submitted and processed, as well as statistics and reports are published. The Forex market operates continuously because while evening falls and trading closes in one part of the world, it is already morning and the new business day in another. This allows for currency exchange around the clock, regardless of the local stock exchange opening hours.

Choosing the right time to trade is one of the factors that determines the success of a Forex trader. The Forex trading week starts on Monday morning and ends on Friday evening with the closing of the New York trading session. The start of work is considered to be the opening of the Pacific session in Wellington (New Zealand) on Monday morning local time. Greenwich Mean Time is used as a common reference point for all countries, from which time zones are measured, to avoid confusion when determining the start of trading in a particular geographic location.

| Financial center | Session "character" | Key instruments | | --- | --- | --- | | Sydney/Wellington | Calm, often sets the direction for the day | AUD, NZD, AUDNZD, AUDUSD | | Tokyo/Asia | Can enhance or correct movement | JPY, AUD, NZD, USDJPY | | London/Europe | The most volatile session, sets the main volume | EUR, GBP, CHF, EURUSD, GBPUSD | | New York/America | High volatility, reacts to news | USD    USD, CAD, USDCAD, USD pairs |

**Features of trading sessions**   For market participants, it is important to understand not only the start and end times of trading, but also their distinctive features. Each region has developed its own style and rules for conducting trades, transaction volumes, and distinctive strategies that distinguish them from other exchanges. Each session relies on its own currency pairs and reacts more sharply to external economic factors in its geographic zone than to events further afield. Common to all are the smooth movement of currency prices at night and the increase (sometimes explosive) in volatility during the day.

Asian session   Asian trading peaks between 8:00 a.m. and 12:00 p.m., when European financial centers open, traders determine currency movements, and open positions. However, its usual characteristics are low liquidity and volatility. Currency pairs remain within tight trading ranges, setting the stage for strong price movements in the future. The main ones, involving the pound sterling (GBP), the US dollar (USD), the euro (EUR) and the Swiss franc (CHF), are in a "dormant" state. The ones that are actively traded are:

The relative disadvantages of the session include low volatility of a few tens of points, which determines small profits for traders and forces brokers to set high spreads. If the price corridor is broken, this trend continues in subsequent trades.

European session   The trends that emerged in Asia are being picked up by the European Forex session. Its working hours are from 10:00 a.m. to 7:30 p.m. Main players: German, French and English exchanges in Paris, Zurich, Frankfurt and Luxembourg. London occupies a special place in the currency market due to its geographical location and the fact that all the world's largest financial groups have their offices there.

From the moment the London Stock Exchange opens, most market trends are formed and continue until the start of the American session. Since European trading overlaps with two other sessions, and the UK capital is the largest financial centre on the planet, this time period accounts for the largest share of transactions carried out on Forex. The distinctive features are large monetary movements and rapid changes in quotes, as well as high volatility.

American session   The American trading session is characterized by increased aggressiveness and unpredictability. The hottest time is considered to be the period of overlapping European and American trades. The latter open at 4:00 p.m. in New York and close at 1:00 a.m. in Chicago. The release of morning US statistics coincides with the release of afternoon reports in Europe, after which trading volumes increase and the market becomes saturated with liquidity.

---

# 20371: Formulating Dynamic Multi-Pair EA (Part 6): Adaptive Spread Sensitivity for High-Frequency Symbol Switching

## Sections

### **Back Test Results**

The testing was conducted across roughly a 2-month testing window from 19 November 2025 to 17 January 2026, with the following settings:



Now the equity curve and the backtest results:





###

### Conclusion

In summary, we designed and implemented an Adaptive Spread Sensitivity framework that operates as an execution-intelligence layer within a dynamic multi-pair EA. The system continuously monitors real-time spreads, normalizes them using volatility context, ranks symbols by cost efficiency, and dynamically activates or deactivates instruments based on current execution quality. By separating spread evaluation from trading logic, we ensured that symbol selection, prioritization, and protection mechanisms remain adaptive, lightweight, and scalable—allowing the EA to switch focus across symbols at high frequency without altering the underlying strategy rules.

In conclusion, this approach equips traders with a powerful tool to control trading costs and execution risk in fast-moving, multi-symbol environments. Instead of trading all pairs blindly, the EA intelligently concentrates activity on the most efficient markets at any given moment, reducing slippage, avoiding unfavorable spread conditions, and improving overall trade quality. For traders, this translates into cleaner execution, better capital efficiency, and a more resilient automated system that adapts to changing market microstructure rather than being constrained by static assumptions.

**Attached files** |

## Key paras

# Formulating Dynamic Multi-Pair EA (Part 6): Adaptive Spread Sensitivity for High-Frequency Symbol Switching

In  contrast, Part 6 shifts the focus away from specific trading entry and exit styles and instead zeroes in on the execution environment itself—especially the cost of trading as expressed through spreads. In Part 6, we now introduce a module that continuously monitors and adapts to real-time spread conditions across all symbols, using dynamic sensitivity thresholds to determine which symbols are currently optimal to trade. This high-frequency symbol switching based on adaptive spread evaluation complements the broader multi-pair architecture by prioritizing execution quality and cost efficiency over pure strategy mechanics.

The Adaptive Spread Sensitivity EA is a sophisticated multi-symbol trading system designed to optimize trade execution dynamically  across multiple financial instruments. At its core, the system continuously monitors real-time spreads for all configured symbols, ranking them based on cost-efficiency metrics to prioritize trading on instruments with the most favorable execution conditions.

Unlike traditional single-symbol EAs, this system implements intelligent spread filtering that temporarily disables symbols experiencing abnormally high spreads, preventing costly entries during poor liquidity conditions while automatically re-enabling them when spreads normalize. The adaptive architecture allows the EA to function as a "smart router" that dynamically switches between available symbols based on changing market microstructure, ensuring trades are always executed on the most economically efficient instrument at any given moment.

The trading strategy employs a straightforward yet effective technical analysis approach using dual moving average crossovers combined with RSI momentum confirmation. When spread conditions are favorable, the system generates buy signals when the fast EMA crosses above the slow EMA while RSI indicates oversold conditions, and sell signals when the fast EMA crosses below the slow EMA with RSI in overbought territory. This combination provides balanced entry timing—using moving averages for trend direction and RSI for entry precision.

Getting started, we establish a flexible configuration layer for our dynamic multi-pair Expert Advisor by grouping all user-defined inputs in a clean and modular way. We begin with the general trade control, such as the list of symbols to monitor, risk per trade, and a magic number for position tracking. From there, we introduce a dedicated Spread Sensitivity section, which is the core of the EA’s execution logic. These inputs define absolute and adaptive spread limits, ATR-normalized spread thresholds, temporary symbol disabling, and symbol ranking constraints, allowing the EA to intelligently decide which markets are cost-efficient enough to trade at any given moment. Importantly, this lay

Moving further, the code defines strategy-level inputs and supporting infrastructure that operate only after a symbol has passed the spread filter. The trading settings configure indicator parameters (EMA, RSI), risk boundaries (SL/TP, cooldowns, maximum positions), and optional ATR-based dynamic exits, enabling controlled and consistent trade execution. Below the inputs, global variables and the SpreadData structure form the EA’s internal state engine, tracking real-time spread metrics, symbol status, activity flags, trade statistics, and dashboard visuals. This structure allows the EA to rank symbols, disable and re-enable them dynamically, and present a live dashboard view of system behav

The OnInit() function handles the full startup preparation of the Expert Advisor by configuring symbols, internal data structures, and execution settings before trading begins. It starts by parsing the user-defined symbol list and validating that at least one tradable symbol is available, safely terminating initialization if none are found. The function then allocates and initializes the spreadData structure for each symbol, setting default values for spread metrics, trade state, statistics, and visual status indicators while also subscribing each symbol for real-time data updates. Finally, it configures trade execution parameters such as the magic number and slippage tolerance, initializes 

The OnTick() function, on the other hand, defines the EA’s real-time operational flow and is designed for efficiency in a multi-symbol environment. Instead of processing all symbols on every tick, it cycles through one symbol per tick using a modulo counter, reducing CPU load and avoiding execution bottlenecks. For each selected symbol, the EA updates spread data, verifies trade eligibility, enforces cooldown constraints, and then executes the trading logic if all conditions are met. Dashboard updates are throttled to occur periodically rather than on every tick, ensuring the interface remains responsive while maintaining performance stability in high-frequency symbol monitoring scenarios.

This block introduces a timer-driven spread monitoring system that operates independently of tick frequency, ensuring consistent and timely evaluation of all symbols. The OnTimer() function acts as the scheduler, periodically refreshing spread data across every configured symbol and optionally ranking them by spread efficiency when enabled. This design decouples spread analysis from price ticks, allowing the EA to remain responsive even during low-liquidity periods. The update flow cascades through UpdateAllSpreadData() and into UpdateSpreadData(), where real-time bid/ask prices are collected, spreads are calculated in pips, and volatility context is added by computing ATR values, forming th

The EvaluateTradeability() function then applies a layered decision process to determine whether each symbol is eligible for trading. It first enforces cooldown timeouts for previously disabled symbols, preventing rapid re-entry during unstable conditions. Next, it checks absolute spread limits and adaptive ATR-normalized thresholds, automatically disabling symbols that become too costly to trade and logging these events to the dashboard for transparency. When all spread conditions are satisfied, the symbol is marked tradeable and visually flagged as healthy, completing a robust protection mechanism that dynamically filters symbols based on real-time execution quality rather than static rule

Here we introduce a spread-efficiency ranking engine that determines which symbols are allowed to participate in trading at any given time. In RankSymbolsBySpread(), each symbol is assigned a composite spread score based on two execution-quality factors: the absolute spread and the spread-to-ATR ratio. Both components are inverted so that lower costs produce higher scores, then combined using weighted importance to emphasize raw spread while still accounting for volatility context. Once scores are calculated, the symbols are sorted in descending order, ensuring that the most cost-efficient instruments naturally rise to the top of the priority list.

---

# 22998: Measuring broker execution quality in MQL5: Why your live account doesn't match the backtest

## Sections

### Limitations

Let me be honest about what this tool does NOT do:

1. *Passive mode is an approximation.* Its reference is the quote observed when the OnTradeTransaction event is handled, not the price at the exact instant the order was sent. On fast markets it can over- or under-state, and even flip sign. For request-to-fill precision, use the probe.
2. *Requotes are counted for probes only.* The count comes from the return code of the tool's own trade calls; it is not an account-wide requote rate, and passive deals are not included in it.
3. *Statistics are deal-based, not order-based.* An order that fills in several parts becomes several samples; the tool does not reassemble order-level intent.
4. *It measures the whole path, not the broker in isolation* (see the caution above).
5. *The probe trades for real* (spread/commission cost), which is why a demo or the minimum lot is the right way to run it.
6. It does not replace a tick-by-tick analysis at the server level; it's a practical client-side diagnostic, and the CSV is your historical record for offline work.

### Conclusion

In my experience, the gap between a promising backtest and a disappointing live result is often not in the strategy, but in how orders are actually executed. Measuring it — instead of assuming it — lets you decide with data: pick a broker, drop an hour, move your VPS, or confirm the problem is somewhere else. I built the Execution Quality Monitor to put numbers on that hidden cost, with an honest split between a precise probe and an approximate passive mode. The full source is attached and compiles cleanly; try it on your account and compare what you measure against what your backtest assumes.

*Disclaimer: this tool is for diagnostics and analysis. It is not financial advice.*

**Attached files** |

## Key paras

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Tester](https://www.mql5.com/en/articles/mt5/strategy_tester) | 11 August 2026 at 06:49

If you code in MQL5, you have probably lived this: the Strategy Tester draws a beautiful, almost straight equity curve, and when you put the same Expert Advisor (EA) on a real account, the result is very different. I have hit that wall more than once. My first instinct used to be to blame the strategy — but very often the strategy is fine. What changed is the *execution quality*.

The Strategy Tester lives in an ideal world: it fills orders at (or near) the requested price, with a modeled spread and—unless configured otherwise—no delays or rejections. A live account is a different animal: the price moves between the moment you send the order and the moment it is filled, the spread widens exactly when it matters, and every now and then you get a requote, a price change, or a rejection. That friction has names: *slippage*, *spread* and *requotes*.

1. *Slippage.* The difference between the price you expected and the price your order was actually filled at. If you wanted to buy at the ask and you were filled higher, that excess is slippage against you. Same when you sell below the bid. I measure it in points (the symbol's smallest unit) and, by convention in this tool, *positive slippage means a worse fill*. 2. *Observed spread.* The bid-ask spread at the moment of measurement, in points. A quick note on terminology: in market-microstructure literature "effective spread" has a precise meaning (execution cost relative to the mid-price, often round-trip). I am *not* using it in that strict sense. Here it is simply the quoted spread observ

Let me make it concrete. Say the XAUUSD ask is 2000.00 when you send a buy, and you are filled at 2000.30. That is 30 points of entry slippage against you (with a 2-digit symbol, point = 0.01). If you then close and the bid was 2001.00 but you are filled at 2000.85, that is 15 points of exit slippage. The asymmetry is 30 − 15 = 15 points worse on entry. For a strategy that aims at 100 points per trade, that asymmetric cost is huge, and it appears in no standard backtest.

1. *Instant Execution:* the broker shows you a price and you ask to be filled at that exact price. If the price changed, the server answers with a *requote*. This is where you will see the most requotes and rejections. 2. *Market Execution:* you send the order and the broker fills it at the best available price. There is typically no requote at the request stage, but you can still get slippage — the fill price is whatever liquidity is there at that instant, so a thin book can move it against you. 3. *Exchange Execution:* the order goes to a centralized market (typical for stocks/futures), and the behavior depends on the order book.

Many modern forex accounts are Market Execution, where slippage tends to matter more than requotes — but this is a tendency, not a rule, and Instant accounts are still common, where requotes can be as damaging as slippage for high-frequency EAs. You can check your symbol's mode with SymbolInfoInteger(\_Symbol, SYMBOL\_TRADE\_EXEMODE) if you want to adapt.

- *Active mode (probe), precise-ish:* a button fires a round-trip test trade with the minimum lot. It records the reference quote *right before* sending the order and compares it with the actual fill, so this is the closest thing to a true request-to-fill measurement. It also times the round trip and reads the return code (requote/price change) of its own calls. - *Passive mode, approximate:* it listens to every deal on the account through the OnTradeTransaction event and compares the fill with the quote *observed when the event is handled*. This is an approximation, not a request-to-fill measurement: the event arrives *after* the trade, and the tick you read at that moment is not guaranteed

Let's start with the declaration. We include the standard trading library for the active mode, define the inputs, and the global arrays that accumulate the samples — note that we keep *every sample*, not just running sums, so we can later report the median and the 95th percentile, not only the mean.

The four slippage arrays are split on purpose: g\_pEntry/g\_pExit hold the precise probe measurements, while g\_aEntry/g\_aExit hold the approximate passive ones. We never mix them. PROBE\_MAGIC tags our own test trades so the passive handler skips them (otherwise we would count each probe twice).

The passive mode lives in the OnTradeTransaction handler. Every time a deal is added to the account, we read its fill price and compare it with the quote we observe at that instant. Read the comments carefully — this is exactly where the "approximate, not exact" caveat lives.

A few things worth highlighting. The latency we measure (ms1 - ms0) is the time between calling trade.Buy/Sell and getting the result back — that is *client-perceived per-leg latency* (the entry and the exit legs are timed separately), not pure server execution time, but it is exactly the friction you feel, and it often explains slippage. We capture the position ticket right after opening and close that ticket; because ProbeAllowed already guaranteed nothing else was on the symbol, the probe leg is unambiguous. IsRequote is a one-line helper (rc == TRADE\_RETCODE\_REQUOTE || rc == TRADE\_RETCODE\_PRICE\_CHANGED) and lives in the attached source. A caveat to be honest about: CTrade::ResultRet

---

# 23299: Execution Cost and Slippage Sensitivity Analyzer

## Sections

### Interpreting the Results

Run the script with no input file, and it analyzes the built-in sample of 200 deals. The strategy looks tradeable before cost: a net profit of 2031.14, a profit factor of 1.56, and a win rate of 61.0%, on a total of 67.90 lots. The edge per deal is 10.16, so the breakeven cost per deal is also 10.16.

Now apply the assumed cost of 12 units per lot. The average deal trades about 0.34 lots, the assumed cost averages 4.07 per deal, and the cushion works out to 2.49. In other words, the edge survives execution costs up to about two and a half times what we assumed, and no further. At the assumed cost, the net profit falls to 1216.34, which is 60% of the original; the other 40% is paid away. The profit factor drops from 1.56 to 1.31, and 6 of the 122 winners turn into losers. The composite score is 69.0, a grade of C.

The recommendations follow from those numbers. The cushion is below 3.0, so the tool warns that a modest rise in spread or slippage materially cuts the result. The profit factor at cost is below 1.4, so it flags that the edge is thin once realistic costs are paid. And because realistic costs erase 40% of the net profit, it says so plainly. The reading is clear: this strategy is not worthless, but it is cost-sensitive, and it needs a margin of safety, a cheaper broker, or fewer and larger trades before it goes live.

The same workflow ranks candidates. Run two strategies through the analyzer with the same assumed cost, and the one with the higher cushion is the one more likely to keep its edge on a real account. A cushion above 3.0 with a profit factor that stays healthy at cost earns the positive note and is the kind of result worth trading.

### Applicability and Limitations

The analyzer is a planning tool, not a guarantee. It needs a reasonable sample to be meaningful; below about 100 deals, the figures move too much from a single large trade, and the script refuses to run below 20. It works at the closing-deal level, the granularity MetaTrader 5 records, so a position closed in several partial exits is several rows, and the modeled cost is charged to each exit, which matches how a broker bills.

The cost model is intentionally simple: a fixed part plus a linear per-lot part, applied equally to every deal. Real slippage is not constant; it is worse in fast markets and around news, and it can depend on order type and size. Treat the assumed cost as a considered estimate and read the cushion as the margin over it, not as a promise that the cost will never exceed it. The cushion and the breakeven are exact for the linear model; the profit factor at cost and the win erosion depend on the distribution of your deals.

Finally, cost robustness is one dimension among several. It complements, rather than replaces, walk-forward testing, which checks that the edge persists out of sample, and Monte Carlo resampling, which checks how sensitive the result is to the order of trades. A strategy worth trading should pass all three: a stable edge, a tolerable spread of outcomes, and a comfortable margin over costs.

### Conclusion

We set out to answer a question that headline metrics hide: how much execution cost can the edge absorb? The analyzer answers it directly. It reads a record of closing deals, finds the breakeven cost per deal, measures the cushion over a realistic assumed cost, re-prices the whole record to show the net profit and profit factor at that cost, counts the winners the cost erases, and folds the three dimensions into a graded score with concrete advice. The sample strategy earned a C: profitable on paper, but with only a 2.49x cushion and 40% of its net profit lost to realistic costs.

All source files are attached and compile natively in MetaEditor, so a reader can run the analyzer on their own trades, see how close the edge sits to the cost line, and decide whether it is ready for a live account. The source code is available in the MQL5 CodeBase: [Execution Cost Sensitivity Analyzer in the MQL5 CodeBase](https://www.mql5.com/en/code/74663).

The following table describes the source files that accompany the article.

| **File Name** | **Description** |
| --- | --- |
| CostSens | The main script. It loads the deals, runs the engine and the scoring, and prints the full cost-robustness report with the cost curve. |
| CostLoader | Module 1 reads the input file (date, profit, and volume) and prints a quick summary for verification. |
| CostEngine | Module 2 re-prices the deals under a rising cost and computes the breakeven, the cushion, and the win erosion. |
| CostScore | Module 3 combines the three dimensions into a graded score and prints the recommendations. |
| ExportCost | A helper that exports a file of date, profit, and volume from the trade history. Copy its function into your Expert Advisor and call it from OnTester, or run it as a script. |
| MQL5.zip 

## Key paras

I once had a strategy that looked ready to trade. Over a two-year backtest, it showed a net profit above two thousand units, a profit factor near 1.6, and a win rate of 61%. The equity curve climbed in a calm, believable line. I funded a small account, switched it on, and watched the live result drift below the backtest week after week. Nothing was broken in the logic. The gap was cost. Each trade paid slightly more spread and slippage, plus a commission the backtest had treated as an afterthought. Those small amounts added up and consumed most of the edge.

This article asks one question: how much execution cost can a strategy absorb before its edge disappears? Net profit and profit factor are measured at the cost the backtest happened to assume. They do not tell you how close that result sits to the cost line or how much the spread would have to widen before a winning system turns into a losing one. A strategy with a wide margin over costs is one you can trade through a noisy broker and a fast market. A strategy that only wins because the test was cheap will not survive contact with a real account.

A backtest charges the costs you tell it to charge. The spread is often a fixed, optimistic value; commission may be left at zero; and slippage, the difference between the price you wanted and the price you got, is usually absent because the tester fills you at the modeled price. Live trading is not so kind. Spreads widen around news and at the session close. Fast markets fill market orders a few points away from the screen. A broker that looked cheap on a quiet pair can be expensive on the one you actually trade.

The fixed part stands for a per-ticket charge such as a minimum commission. The per-lot part stands for the spread, the variable commission, and the slippage, all of which grow with position size. This is a deliberately linear approximation. In reality, spread and slippage also depend on the instrument and on volatility, not on volume alone, but a linear model keeps the estimate transparent and configurable. With the default of 12 units per lot and no fixed part, a 0.50-lot deal pays 6 units, and a 0.10-lot deal pays 1.2 units.

**Edge per deal and the breakeven cost.** The net profit spread across the deals gives the average edge each deal carries:

To analyze a real strategy, you need its closing deals in the same format: date, profit, and volume. The helper reads the account or tester history, keeps only the buy and sell deals that close a position, and writes one row per closing deal. By default it exports the price result only, excluding the commission and swap already charged, so the analyzer can model the full execution cost on top without counting it twice. If you prefer to fold the charged fees back in, set the InpIncludeFees input. A clean approach is to set backtest commission to zero, export gross results, and let the tool apply realistic costs on top.

The recommendations follow from those numbers. The cushion is below 3.0, so the tool warns that a modest rise in spread or slippage materially cuts the result. The profit factor at cost is below 1.4, so it flags that the edge is thin once realistic costs are paid. And because realistic costs erase 40% of the net profit, it says so plainly. The reading is clear: this strategy is not worthless, but it is cost-sensitive, and it needs a margin of safety, a cheaper broker, or fewer and larger trades before it goes live.

The cost model is intentionally simple: a fixed part plus a linear per-lot part, applied equally to every deal. Real slippage is not constant; it is worse in fast markets and around news, and it can depend on order type and size. Treat the assumed cost as a considered estimate and read the cushion as the margin over it, not as a promise that the cost will never exceed it. The cushion and the breakeven are exact for the linear model; the profit factor at cost and the win erosion depend on the distribution of your deals.

Finally, cost robustness is one dimension among several. It complements, rather than replaces, walk-forward testing, which checks that the edge persists out of sample, and Monte Carlo resampling, which checks how sensitive the result is to the order of trades. A strategy worth trading should pass all three: a stable edge, a tolerable spread of outcomes, and a comfortable margin over costs.

In Part 2 we measure the market's dominant cycle using Ehlers' Hilbert-transform homodyne discriminator and wrap it as an indicator. We then build the MESA Adaptive Moving Average (MAMA) and its follower FAMA from that phase information. Finally, we combine MAMA/FAMA with the Even Better Sinewave to form a regime-switching Expert Advisor and test it on EURUSD in the Strategy Tester, giving you a complete, reproducible MQL5 implementation.

This article presents CSymbolMetaCache, an MQL5 layer that preloads contract specifications and trading-session schedules for monitored symbols at EA startup and then serves typed getters from memory. It explains which properties are safe to cache versus dynamic ones, including the semi-dynamic tick value on cross-currency pairs, and implements an in-memory IsMarketOpen() evaluator. A benchmark quantifies latency reduction across a set of twenty symbols.

---

# 23755: A Reusable Breakeven Manager in MQL5 with Spread Compensation

## Sections

### Section 9: Limitations

Limitations that affect breakeven correctness directly:

- The is\_moved flag prevents any subsequent adjustment once the level is set. If the spread widens permanently after modification, the level that was correct at that moment is never revisited.
- A failed modification leaves is\_moved false and retries on the next tick, but with no bounded retry count or backoff.

Limitations that are scope choices, not correctness gaps:

- The manager does not account for overnight swap costs.
- The activation threshold is a fixed pip count and does not adapt to volatility.

###

### Conclusion

The repository produced in this article delivers a practical, modular solution to the breakeven problem. CBreakevenManager and its supporting components (a position record, live spread sampler, pip-aware calculator, SL modification executor, demo EA, and a test script) guarantee the following properties: when a configured profit in real pips is reached, the manager samples the spread at modification time and issues a single SL update using the formula

- for BUY: new SL = open price + current spread + buffer pips \* pip\_size
- for SELL: new SL = open price - current spread - buffer pips \* pip\_size. The implementation converts pips correctly on 3- and 5-digit symbols, logs the split between spread and buffer, and exposes a minimal integration surface—call Register() once per position and call OnTick() each tick. A verification script exercises pip conversion, the long/short formulas, activation logic, and the is\_moved gating, providing reproducible proof of behavior.

Limitations remain explicit: the manager does not account for overnight swap costs, uses a fixed (non-adaptive) activation threshold, has no bounded retry/backoff on failed modifications, and marks a position final after one successful move (no automatic re-adjustments). These are deliberate design choices to keep the module simple and auditable; the article also outlines straightforward extensions (time-in-trade checks, multiple staged breakeven levels, logging to CSV, or integration with a trailing engine) for readers who need them.

**Programs used in the article:**

| # | Name | Type | Description |
| --- | --- | --- | --- |
| 1 | BreakevenRecord.mqh | Include File | CBreakevenRecord struct holding all engine-internal state for one registered position |
| 2 | SpreadSampler.mqh | Incl

## Key paras

You may have seen a familiar failure mode: an Expert Advisor moves a stop-loss "to breakeven" at the entry price and then, during a short spread spike (news or thin liquidity), the position is closed on that stop even though the market is barely retraced. The root causes are twofold and engineering-focused: (1) a breakeven check that ignores the fact that a trade is opened at ask but closed at bid—so the spread at modification time must be part of the breakeven level—and (2) a mistaken pip/point conversion on 3- and 5-digit symbols, which makes activation thresholds and buffers scale incorrectly. You need a small, testable module that (a) measures profit in real pips, (b) samples the live sp

Architecture of the breakeven manager. The Expert Advisor drives CBreakevenManager through Register() and OnTick(). On each tick, the manager reads the live spread, computes the breakeven level, and sends the modification, in that order, through OrderSend() with a TRADE\_ACTION\_SLTP request.

The spread has to be read at the exact moment the stop loss is about to be modified, not stored once at registration and reused. A position can sit registered for hours before it reaches its activation threshold. If the spread were captured once when Register() was called, the value used in the breakeven formula could be completely disconnected from the actual market condition by the time the position is finally profitable enough to move. CSpreadSampler exists purely to make that live read happen consistently.

GetCurrentSpread() reads SYMBOL\_ASK and SYMBOL\_BID for the given symbol and returns the spread in price terms: ask - bid. This is the raw value the breakeven formula needs, expressed in the same units as open\_price.

GetCurrentSpreadPips() exists as a convenience for logging and reporting, converting that same price-terms spread into a pip count. On 3-digit and 5-digit symbols, one pip equals ten points rather than one, so this method checks SYMBOL\_DIGITS and divides by ten times the point size rather than the raw point on those symbols. Dividing by the raw point on a 5-digit symbol would report ten times too many pips.

CBreakevenCalculator takes the pieces the manager gathers, the record and the live spread, and turns them into a single price: the breakeven level. It touches no live market data itself, which is what makes it possible to test with plain numbers instead of a real position.

ComputeLevel() implements the long formula open\_price + spread + buffer\_pips \* pip\_size, and its mirror for a short: open\_price - spread - buffer\_pips \* pip\_size. Adding the spread rather than ignoring it is the entire point of this article. It is what makes the resulting level genuinely break-even from the broker's perspective, since the position's true cost already includes the spread paid at entry.

Modify() needs four fields populated in the request: action set to TRADE\_ACTION\_SLTP, position set to the ticket, symbol set to the symbol, and sl set to the new breakeven level. The current take profit is read from the position and passed through unchanged, since omitting it would clear the take profit entirely rather than leaving it alone. Two extra parameters, spread\_component and buffer\_component, are never used inside the trade request itself. They exist purely so the log line can show exactly how much of the modification came from the live spread and how much came from the configured buffer. On failure, the log prints the attempted stop loss along with the retcode and comment the t

OnTick() is where everything comes together. It walks every registered record, skips any whose position can no longer be selected (already closed, so it deregisters and moves on), and skips any already marked is\_moved. For everything left, it reads the correct live price for that position's direction and asks the calculator whether the activation threshold has been reached. Only once it has, does it sample the live spread, compute the breakeven level, and hand both off to the executor. The logged buffer component uses the calculator's own PipSize(), so the number printed in the log always matches what ComputeLevel() actually used. The record is marked is\_moved only after the executor confi

Section 6 puts this to the test directly: a demo EA opens two identical positions side by side, one wired through CBreakevenManager, one left to a deliberately naive open-price-only stop, so the difference in survival during a spread spike is visible in the same log rather than described in the abstract.

NaiveBreakevenCheck() simulates the flawed approach described in the introduction directly: once the activation threshold is reached, the SL is moved to the exact open price with no spread component and no buffer. It uses the same real-pip conversion as CBreakevenCalculator::PipSize() for its own activation check, so both arms of the demo activate at the same true profit distance and differ only in spread compensation, never in timing.

Breakeven level drawn above the entry price, labeled with the buffer and spread that produced it.

---

# 2739: An Example of Developing a Spread Strategy for Moscow Exchange Futures

## Key paras

The MetaTrader 5 platform allows developing and testing trading robots that simultaneously trade multiple financial instruments. The built-in Strategy Tester automatically downloads required tick history from the broker's server taking into account contract specifications, so the developer does not need to do that manually. This makes it possible to easily and reliably reproduce trading environment conditions, including even millisecond intervals between the arrival of ticks on different symbols. In this article we will demonstrate the development and testing of a spread strategy on two [Moscow Exchange futures](http://www.moex.com/en/derivatives/select.aspx "http://moex.com/en/derivatives/s

Si-M.Y and RTS-M.Y futures are traded on Moscow Exchange. These futures types are tightly correlated. Here M.Y means contract expiration date:

Si is a futures contract on US dollar/Russian ruble exchange rate, RTS is a futures contract on the RTS index expressed in US dollars. The RTS index includes stocks of Russian companies, the prices of which are expressed in rubles, USD/RUR fluctuations also affect index fluctuations expressed in US dollars. Price charts show that when one asset grows, the second asset usually falls.

We have received linear regression coefficients and can draw a synthetic chart of type Y(RTS) = A\*RTS+B. Let us call the difference between the source asset and the synthetic sequence "a spread". This difference will vary at each bar from negative to positive values.

In order to visualize the spread, let us create the *TwoSymbolsSpread\_Ind.mql5* indicator that displays the histogram of spread on the last 500 bars. Positive values are drawn in blue, negative values are yellow.

### Creating a linear regression channel on the spread channel over the last 100 bars

The spread indicator shows that the difference between the Si futures and the synthetic symbol changes from time to time. In order to evaluate the current spread, let us create the *SpreadRegression\_Ind.mq5* indicator (spread with a linear regression on it) that draws a trend line on a spread chart. The line parameters are calculated using linear regression. Let us launch the two indicators on a chart for debugging.

The slope of the red trend line changes depending on the spread value on the last 100 bars. Now we have a minimum of required data and we can try to build a trading system.

Spread values in the *TwoSymbolsSpread\_Ind.mql5* indicator are calculated as the difference between Si and Y(RTS)=A\*RTS + B. You can easily check it by running the indicator in the [debugging](https://www.metatrader5.com/en/metaeditor/help/development/debug "https://www.metatrader5.com/en/metaeditor/help/development/debug") mode (F5 key).

Let us create a simple Expert Advisor that would monitor change of slope of the linear regression attached to a spread chart. Line slope is the A coefficient in the equation: Y=A\*X+B. If trend is positive on the spread chart, A>0. If trend is negative, A<0. The linear regression is calculated using the last 100 values of the spread chart. Here is a part of the Expert Advisor code *Strategy1\_AngleChange\_EA.mq5.*

#include <Trade\Trade.mqh>    //+------------------------------------------------------------------+    //| Spread strategy type                                             |    //+------------------------------------------------------------------+    enum SPREAD\_STRATEGY      {       BUY\_AND\_SELL\_ON\_UP,  // Buy 1-st, Sell 2-nd       SELL\_AND\_BUY\_ON\_UP,  // Sell 1-st, Buy 2-nd      };    //---    input int       LR\_length=100;                     // Number of bars for a regression on spread    input int       Spread\_length=500;                 // number of bars for spread calculation    input ENUM\_TIMEFRAMES  period=PERIOD\_M5;           // Time-frame    input string    symbol1="

input SPREAD\_STRATEGY strategy=SELL\_AND\_BUY\_ON\_UP; // Type of a spread strategy

---

# 14035: Forex spread trading using seasonality

## Sections

### Conclusion

The most important part of the pair trading strategy is correct selection of spread symbols for trading. It is important to understand that the strategy itself is not a "grail", but with the correct selection of correlating instruments it can bring possible profit with minimal risk. A more expanded concept of statistical arbitrage (pair trading) is trading a portfolio of symbols. Its scenario is built on similar principles described in this article. Also, in addition to the price of a point converted to USD terms, it is possible to calculate spread lots by adding the volatility ratios of the symbols included in the spread.

Seasonal spread analysis has natural limitations. For example, even the most reliable pattern may fail to form due to the influence of random or force majeure factors.

Translated from Russian by MetaQuotes Ltd.   
Original article: <https://www.mql5.com/ru/articles/14035>

**Attached files** |

## Key paras

In the previous [article](https://www.mql5.com/en/articles/12996), we considered the element of seasonality in the markets. Here we will have a look at the option of representing movements according to seasonal patterns in the form of symbol spread indicators. A trading method is considered, in which one symbol is bought and another is sold, thus, such an entry into the market is considered as a single (spread) position. Pair trading symbols should preferably have a correlation for greater trading efficiency.

In case of negative correlation, symbols move in opposite directions. For example, EURUSD and USDCHF. Both cases are examples of strong dependence. Notably, the reverse spread symbol is bought or sold in the same direction as the first spread symbol — EURUSD. Spread bought EURUSD in long position, while on USDCHF inverse spread symbol we enter a long position as well. Spread sold: we have a sell position on the first symbol of the spread EURUSD and we have a sell position on USDUCHF as well.

In pair trading, the spread of a pair of symbols is traded, that is, the difference between two trading instruments. If it is initially known that these symbols are moving in the same direction, then at the next divergence, they will most likely converge back.

The easiest way to illustrate the pair trading strategy is to use EURUSD and GBPUSD pairs. Thus, when the spread (difference) between two symbols widens to a certain threshold, the lagging instrument is purchased and the leading instrument is sold. When the instruments converge again, profit is fixed.

Fig. 3. The typical movement within the price range of the EURUSD and GBPUSD spread

As a result, it does not matter at all to the trader, in which direction a particular trading symbol moves. It is important that the symbols being traded in the spread converge, namely that their spread returns to zero. At this point, a profit is recorded, sometimes equal to the size of the discrepancy.

For such a strategy to be profitable, there must be a relationship between the symbols. EURUSD and GBPUSD have a fairly strong positive correlation. However, this dependence is not constant, which is why the spread can diverge by a large amount and not converge back for some time.

In essence, trading the EURUSD and GBPUSD spread is similar to trading their EURGBP cross.

One of the goals of spread trading is usually to eliminate the trend component in its movement for a more predictable version of its trading from the range boundaries. For this purpose, different volumes or, in the context of this article, weighting ratios of proportionality of spread symbols movement can be used to enter the market by spread symbols based on research.

Now let's move on to the practical part. It is time to construct a spread of two trading symbols.

We will use the custom indicators of the MetaTrader 5 trading platform to calculate the spread between two symbols. There are different ways to calculate the spread, each with slightly different end results. You are free to use whatever you see fit. As a rule, the spread of a pair of symbols is calculated by the difference. In other words, the spread equation for EURUSD and GBPUSD will look like EURUSD - GBPUSD.

You can also build a spread based on, say, EURUSD/GBPUSD. It is worth considering that the final signals may differ depending on the chosen method of spread calculation, but they do not have any fundamental difference.

---

# 15622: Evaluating the Quality of Forex Spread Trading Based on Seasonal Factors in MetaTrader 5

## Sections

### Conclusion

Advantages of the SpreadMultiYearComparison approach:

1. Risk reduction: spread trading essentially allows us to reduce risks by opening positions on two assets simultaneously.
2. Increased profit probability: Seasonality analysis helps identify times when the market is more likely to move in a particular direction.
3. Better trading decisions: The SpreadMultiYearComparison indicator provides visual information to help you make better and more informed trading decisions.
4. Flexibility: The approach can be adapted to different assets and trading styles.
5. Hedging risks: If one trading symbol goes against the position, the other can offset the loss. For example, we buy XAUUSD, sell XAGUSD - if gold falls, silver may rise. The spread, since the symbol quotes are traded against each other, is usually less volatile than individual symbols, allowing for more stringent risk management.
6. All signals can be additionally filtered using custom filters, for example, technical annotations. It is also possible to use the [Envelopes](https://www.mql5.com/en/code/7975) indicator considering and trading rebounds from the channel boundaries in the direction of seasonality.
7. We can use seasonal trading with technical analysis and work on trading signals in the short term in the direction of seasonality.

Thus, any forecast obtained by averaging historical values should be checked for the probability of its fulfillment. As a rule, only those signals are considered tradable that have a probability of a positive outcome exceeding 70%.

At first glance, it seems that there will be very few such trades, since the seasonal analysis is considered here exclusively for the daily timeframe (D1). Some potential entries are eliminated in this case, but this drawback is compensa

## Key paras

# Evaluating the Quality of Forex Spread Trading Based on Seasonal Factors in MetaTrader 5

Seasonality is recurring price movements associated with climatic, economic and behavioral factors. It is most prominent in commodity markets, but is also found in Forex and the stock market. Examples of seasonal effects: Christmas rally, summer rise in coffee prices, January effect.

The article considers the creation of an indicator for assessing the seasonality quality using [MQL5](https://www.metaquotes.net/en/metatrader5/algorithmic-trading/mql5 "https://www.metaquotes.net/en/metatrader5/algorithmic-trading/mql5"). It allows analyzing both the seasonality of a single symbol and the spread of two instruments. The indicator helps identify statistically significant seasonal movements, use weighting factors, and generate reports for a given month.

Spread trading is the simultaneous opening of long and short positions on related instruments. Profit is generated by changes in relative prices between assets. Unlike arbitrage, spread positions carry risk, but it is lower than trading a single asset because relative prices are more stable.

Using seasonal patterns in spread trading reduces the influence of external factors and increases predictability. The **SpreadMultiYearComparison** indicator for MetaTrader 5 helps identify and analyze such patterns. It is useful for both spread analysis and single asset analysis.

In the indicator, the spread is calculated as the difference between the opening prices of two instruments, with configurable weighting multipliers for each symbol, depending on the relative weight of its quotes within the spread.

1. Pattern analysis: study the indicator chart, identify periods of spread growth/decline that repeat from year to year. 2. Entry point selection: Open a position at the beginning of the month if the spread has historically risen during this period. For example, if you see that the spread tends to widen in a particular month, you might consider buying the spread (buying the first asset and selling the second) at the beginning of that month. 3. Risk management: set stop-loss and take-profit levels, and adjust position size to suit your risk profile.

The analysis method is as follows: we select a traded symbol or spread (for example, silver or EURUSD–GBPUSD) and study the history of movements for 15 years or more. We pay special attention to the repetition of behavior in the same months (for example, June, July). If in 75% of years the price has consistently fallen in June, this is a sign of strong seasonality. If the profit remains approximately the same in different years (for example, about +5% per month), then this pattern is considered stable.

Figure 8.1.1 shows the continuation of the change in Sep25 Silver futures contract quotes for the statistically justified probability for current year's June as a yellow area:

The current chart for the Sep 25 NASDAQ 100 E-Mini (CME) futures contract is shown in Figure 8.1.2 with a forecast upward movement for July.

This data is presented by [Moore Research Center](https://www.mql5.com/go?link=https://www.mrci.com/client/futures/strat/f6322.php "https://www.mrci.com/client/futures/strat/f6322.php") based on the movement of futures contracts by seasonality for the current month of the year.

The following two graphs show the seasonal pattern of the XAGUSD silver spread movement  and gold XAUUSD for January for 15 years of observations (the indicator is launched on silver):

---

# 17934: Advanced Order Execution Algorithms in MQL5: TWAP, VWAP, and Iceberg Orders

## Sections

### Backtest Results





1. Equity & Balance Curves

The green “Balance” stair-steps show your account’s book equity whenever the EA closes a position; the blue “Equity” line smooths in unrealized P&L between trades. We can see a clear upward trend from January through early March, with a few pullbacks—each drawdown topping out around 10–16% before your next series of wins restores the gain. That pattern suggests the system thrives in trending conditions but still suffers tolerable equity dips.

2. Volume & Risk Utilization

At the bottom, the “Deposit Load” triangles shrink gradually over time—this is your position size as a percentage of equity. It starts near 10% of your balance and tapers as your equity grows (with fixed-volume sizing), meaning ourrisk per trade actually decreases as the account climbs. That’s why drawdowns stay proportionally similar even as your dollar equity rises.

3. Key Profitability Metrics

- Initial deposit: $1,000
- Net profit: + $703 (a 70% return over ~2 months)
- Profit factor: 2.34 (you make $2.34 for every $1 lost)
- Expected payoff: $2.34 per trade on average
- Sharpe ratio: 5.47 (very high—strong risk-adjusted returns)

These figures tell us the strategy is not only profitable but earns a healthy buffer above its own volatility.

4. Drawdown & Recovery

- Max balance drawdown: 156 points or 9.99%
- Max equity drawdown: 228 points or 15.89%
- Recovery factor: 3.08 (net profit ÷ max drawdown)

A recovery factor above 2 is generally considered good, so at 3.08 you’re generating over three times your worst loss in gain.

5. Trade Distribution

- Total trades: 300 (600 deals, so every entry+exit counts as two)
- Win rate: 76% (228 winners vs. 72 losers)
- Average win: $5.39
- Average loss: – $7.31

Although your win rate and profit fact

### Conclusion

Imagine you’re a solo trader in a crowded market arena—every tick matters, every fill price whispers profit or loss. By weaving TWAP, VWAP and Iceberg Orders into your toolkit, you’re no longer just reacting to price swings; you’re orchestrating them. These once-elite, institutional-grade algorithms are now at your fingertips, slicing through liquidity like a laser and turning chaotic order books into opportunities.

TWAP becomes your steady metronome, pacing your size evenly across a set interval—perfect for when the tide is calm and you simply want a smooth ride. VWAP morphs you into a savvy volume-tracker, attacking the heaviest trading beats of the day and riding the market’s own pulse. And when you need to cloak your intentions, Iceberg Orders slip your true size beneath the surface, revealing just enough to get filled without spooking the big players.

But these aren’t just standalone tricks. With our modular MQL5 framework, you plug them into any strategy—trend followers, mean-reverters, breakout hunters—with the ease of snapping on a new lens. A single ExecutionManager façade lets you swap, combine or even layer algorithms mid-trade, while the PerformanceAnalyzer keeps score like a hawk, measuring slippage, shortfall and market impact down to the last pip.

What’s next? Think of execution as a living creature that adapts. Let your TWAP learn from volatility spikes. Route your VWAP slices to the deepest pools. Teach your Iceberg to sense where predators lurk and hide deeper. And why stop there? Inject machine-learning to predict the perfect microsecond to fire, or blend order types into bespoke hybrids that match your unique edge.

The trading world never stands still—and neither should your order execution. Dive in, experiment boldly, and turn ev

## Key paras

For decades, institutional heavyweights have quietly wielded sophisticated algorithms to slice, dice, and stealthily deploy their orders, all to dodge slippage and tame market impact. Now, thanks to the flexibility of MQL5, that same powerhouse playbook is within reach of every ambitious retail trader.

Execution algorithms are your antidote. By breaking a large order into a sequence of smaller, strategically timed slices, they smooth out your footprint on the order book. The result? Less slippage, tighter fills, and an overall improvement in your average execution price.

- Tame Slippage: Even modest orders can wander in choppy markets. - Sharpen Your Edge: Layered executions often land you a more favorable average price than a one-shot gamble. - Stay Zen: Automated workflows strip away the temptation to panic-buy or panic-sell. - Scale Seamlessly: As your account grows, your execution stays crisp—no matter how hefty your orders become. - Fly Under the Radar: Iceberg Orders, in particular, cloak your true order size, keeping prying algos guessing.

Today’s democratized landscape means the same execution tech that once demanded multi-million-dollar budgets can now run on your personal trading station. By dropping polished MQL5 code for TWAP, VWAP, and Iceberg strategies into your platform, you’ll arm yourself with institutional firepower—without ever leaving the retail domain.

- Sends orders at regular time intervals between start and end.      - Usually uses equal-sized orders (though you can add randomness to sizes).      - Follows a predetermined timetable, regardless of price moves.      - Spreads market impact evenly over time to keep slippage low.    - When to use:

- You need an average execution price over a specific timeframe.      - Liquidity is steady throughout the trading period.      - You have a fixed window to complete your order.      - You prefer a simple, predictable approach. 2. Volume-Weighted Average Price (VWAP): VWAP improves on TWAP by weighting order sizes according to expected volume. Instead of equal chunks, it sends larger trades when volume tends to be higher.       - How it works:

- Your performance is measured against VWAP.      - Volume follows a predictable daily pattern.      - You are trading in a market where liquidity varies through the session.      - You want to align with the market’s natural flow. 3. Iceberg Orders: Iceberg Orders focus on hiding the true size of a large order. Only a small “tip” is visible at any time; once it fills, the next portion appears.       - How it works:

This function builds and sends a market order by zero‐initializing an MqlTradeRequest and MqlTradeResult, filling in symbol, volume, order type, price, slippage and a magic number, then calling OrderSend. If the send fails or the broker’s return code isn’t TRADE\_RETCODE\_DONE, it logs the error and returns false. On success it updates internal counters (total/fill counts, executed and remaining volume), recalculates the average price, captures the ticket ID, and returns true.

This Execute method manages one slice of your TWAP run. First it aborts if the strategy isn’t active or if it isn’t yet time to trade. When it is, it picks either a fixed or randomized slice of your remaining volume (never exceeding what’s left), then looks up the current ask (for buys) or bid (for sells). It logs the interval, volume and price, builds an MqlTradeRequest with your symbol, volume, type, price, slippage and magic number, and calls OrderSend. If the send fails or the broker returns anything other than TRADE\_RETCODE\_DONE, it prints an error and returns false.

The VWAP algorithm is similar to TWAP but distributes order sizes based on historical volume patterns:

Like TWAP, VWAP also implements the CalculateNextExecutionTime method to ensure proper spacing of orders:

It then builds a pending‐order request ( TRADE\_ACTION\_PENDING ) with symbol, volume, limit price, slippage, and magic number, and calls OrderSend. On error or non-done return codes it logs and returns false; on success it saves the new ticket, marks the order active, records placement time, logs the details, and returns true.

---

# 22963: Implementing Anchored VWAP Indicator in MQL5: A Step-by-Step Guide

## Sections

### Conclusion

This article presented a complete step-by-step implementation of an Anchored VWAP indicator in MQL5, progressing from the mathematical foundation through buffer management, event handling, and core calculation logic. The deliverable supports fixed and session reset modes through a unified stateless calculation loop with O(1) boundary detection, optional standard deviation bands, a real-time draggable anchor line, transparent volume handling across asset classes, and safe multi-instance chart support through unique ID-based collision detection. Use the indicator as an all-in-one tool for execution benchmarking, technical trading, and accumulative analysis, and expand its utility further through multi-anchor and multi-instrument setups. The source code is attached as a downloadable *.mq5* file.

**Attached files** |

## Key paras

The Anchored VWAP is a technical indicator that calculates the volume-weighted price of an asset starting from a user-defined anchor point. It helps traders gauge trend strength, pinpoint entries and exits, analyze market-moving events, investigate swing highs/lows, and measure price extension using standard deviation bands. Unlike regular moving averages that forget beyond a fixed window length, the Anchored VWAP has real memory as it accumulates price and volume data from the anchor point forward.

In this article, we will build an Anchored VWAP indicator in MQL5. Users can set precise anchor times and drag an on-chart anchor line to adjust placement visually. We will implement two modes: a fixed anchor for single-event analysis and a session-reset mode. Session boundaries can be daily, weekly, or monthly. The indicator supports optional standard deviation bands and a selectable applied price. It also supports multiple instances to run several anchors on the same chart. We will focus on indicator architecture: buffer layout, anchor state management, chart object handling, and efficient recalculation.

A precursor of the Anchored VWAP is the standard VWAP, which has the same mathematical basis as the Anchored VWAP, but it starts the calculation at the session open and resets at the end of the trading day. By letting traders anchor VWAP beyond the standard session boundary, Anchored VWAP resolves the standard VWAP's main limitation. It also extends volume-weighted analysis to non-session-based use cases. This makes the Anchored VWAP suitable for:

> By placing the anchor at the start of the actual personal trading session, a trader can benchmark against an average that is indicative of the activity of the participants, analyze trends, and establish key levels pertaining to the session. > >  > > Custom session boundaries using Anchored VWAP

> The Anchored VWAP, when placed at the time of key market-moving events, can offer a view that is genuinely representative of the event-driven trading.

> By positioning the anchor at specific market points such as year starts, traders can gauge the overall state of the average market participant as the Anchored VWAP dynamically evolves over any timeframe.

It is safe to say that the Anchored VWAP is not just an improvement over the standard VWAP but a wholly new trading tool in its own right. With its benchmarking, technical, and analytical capabilities beyond the standard VWAP, the Anchored VWAP is a versatile all-in-one indicator.

The Anchored VWAP consists of the main volume-weighted average price and the standard deviation bands calculated cumulatively from the anchor point forward. The VWAP is given by the formula:

The typical price is the average of the high, low, and closing prices for a given period and is traditionally the price base over which the VWAP is calculated. The typical price is obtained using the formula:

Throughout the article, we will implement the Anchored VWAP to work with all price bases, including the typical price. The [Applied Price](https://www.mql5.com/en/articles/22963#applied_price "Applied Price") section will cover the computations of the price bases. The [Volume Types](https://www.mql5.com/en/articles/22963#volume_types "Volume Types") section will describe volume types and use tick volume as a practical proxy for trading activity in asset classes where real volume is inaccessible. The formulas from this section will be implemented in the [Indicator Calculation](https://www.mql5.com/en/articles/22963#indicator_calculation "Indicator Calculation") section.

| Function | Purpose | | --- | --- | | OnInit | Validate inputs, check object collisions, bind buffers, set globals and indicator properties, draw anchor line | | OnCalculate | Compute VWAP and standard deviation bands | | OnChartEvent | Handle changes when the anchor line gets dragged | | OnDeinit | Delete anchor line |

We will now focus on the [indicator properties](https://www.mql5.com/en/docs/customind/propertiesandfunctions "Indicator Properties"). We want the Anchored VWAP to be overlaid onto the regular chart, so we specify the *indicator\_chart\_window* property. Plots are visual representations of the values in the buffers. The three plots of the Anchored VWAP in their corresponding numerical ordering are as follows:

---

# 22990: Building an Object-Oriented Session VWAP Engine in MQL5

## Sections

### Introduction and Practical Pain Points

When I build intraday trading systems in MQL5, my first reflex is usually to drop a standard moving average on the chart to filter the short-term trend. This approach looks tolerable during dead market hours or tight ranges. However, live tests on liquid currency pairs reveal a major structural flaw. A major macro news candle can instantly shift the market baseline due to institutional volume. A simple moving average treats that heavy candle the same as a low-volume candle from the quiet night session because it only accounts for closing prices. This creates a dangerous trap for an automated robot. The Expert Advisor executes a trade at the moving average line, thinking it is a fair value pullback, but the real institutional volume anchor is left far behind.

The root of the error is that standard indicators entirely ignore tick volume arrays during their calculation passes. I wanted to replace this traditional approach with something much more adaptive that tracks where money is actually being spent. The Volume Weighted Average Price (VWAP) fulfills this role by weighting every price fluctuation by the absolute liquidity traded at that level. Standard MQL5 does not provide a native VWAP that resets daily and includes rolling deviation bands. This makes quick integration into automated strategies difficult. We will move the cumulative calculations into an include file. Then we will plot the baseline and volatility bands in a custom indicator for visual verification. Finally, we will integrate the module into an Expert Advisor for pullback trading.

### The Core Math and Daily Time Anchors

The mathematical calculation behind the VWAP is highly pragmatic and avoids the smoothing lag found in traditional technical indicators. In

### Conclusion and Reusable Artifacts

The development of this session engine provides a robust workspace that separates raw liquidity math from trade management. The core blueprint delivers a complete set of three unified files that work together to map intraday value. The VWAP\_Engine.mqh include file acts as the standalone core, containing the structural anchor checks and double-pass volume loops. The Ind\_Session\_VWAP.mq5 indicator instantiates this class to draw the visual baseline and volatility markers smoothly on the chart screen. Finally, the EA\_VWAP\_Pullback.mq5 robot plugs directly into the include methods, utilizing a strict timing filter to query data safely without risking terminal performance or cluttering memory. Developers can scale this framework by adding time-of-day filters and trailing stops. The same include class can also be reused across multiple symbols to build multi-asset intraday portfolios without changing the math.

The file structure is organized cleanly. VWAP\_Engine.mqh contains the source code for the object-oriented daily reset class. Ind\_Session\_VWAP.mq5 delivers the source code for the chart plotting indicator. EA\_VWAP\_Pullback.mq5 implements the trading logic for the automated pullback robot.

### File Structure Table

| File Name | Description |
| --- | --- |
| VWAP\_Engine.mqh | Source code for the object-oriented daily reset class and mathematical accumulation engine. |
| Ind\_Session\_VWAP.mq5 | Source code for the custom visualization indicator plotting the baseline and deviation bands. |
| EA\_VWAP\_Pullback.mq5 | Source code for the automated pullback trading Expert Advisor with closed bar filters. |

**Attached files** |

## Key paras

When I build intraday trading systems in MQL5, my first reflex is usually to drop a standard moving average on the chart to filter the short-term trend. This approach looks tolerable during dead market hours or tight ranges. However, live tests on liquid currency pairs reveal a major structural flaw. A major macro news candle can instantly shift the market baseline due to institutional volume. A simple moving average treats that heavy candle the same as a low-volume candle from the quiet night session because it only accounts for closing prices. This creates a dangerous trap for an automated robot. The Expert Advisor executes a trade at the moving average line, thinking it is a fair value pu

The root of the error is that standard indicators entirely ignore tick volume arrays during their calculation passes. I wanted to replace this traditional approach with something much more adaptive that tracks where money is actually being spent. The Volume Weighted Average Price (VWAP) fulfills this role by weighting every price fluctuation by the absolute liquidity traded at that level. Standard MQL5 does not provide a native VWAP that resets daily and includes rolling deviation bands. This makes quick integration into automated strategies difficult. We will move the cumulative calculations into an include file. Then we will plot the baseline and volatility bands in a custom indicator for 

The mathematical calculation behind the VWAP is highly pragmatic and avoids the smoothing lag found in traditional technical indicators. Instead of simply summing closing prices and dividing by a fixed lookback period, we extract the typical price of each candle by averaging its high, low, and close coordinates. We then multiply this typical price by the corresponding tick volume recorded for that specific bar. This product is accumulated sequentially from a fixed starting point. Finally, we divide this cumulative sum of price and volume by the total accumulated tick volume recorded over that identical historical span.

If the current market price trades close to the resulting VWAP line, the asset is considered to be fluctuating at its intraday fair value accepted by the majority of participants. When the price stretches significantly far from this benchmark, it enters an overbought or oversold condition relative to the daily liquidity distribution. To quantify this stretch dynamically, our engine will also calculate a volume-weighted standard deviation. This mathematical variance allows us to project upper and lower deviation bands that naturally expand and contract based on real intraday volatility shifts. I do not treat the resulting VWAP baseline as a magic support or resistance level. Financial markets

Before translating this mathematical architecture into MQL5 structures, we must establish a strict operational agreement for our execution layers. This signal contract defines exactly how and when our automated robot will read the VWAP metrics and authorize a market order. For our strategy blueprint, the entry threshold is defined by the first standard deviation boundaries. The contract dictates that the algorithm looks for a bullish entry if the price drops and touches the lower deviation band, assuming the broader market context supports a buy setup. Conversely, we look for a short execution if the price spikes directly into the upper deviation band.

Placing heavy statistical loops directly inside the main execution file of an Expert Advisor creates rigid, unscalable architecture. If you later decide to track multiple symbols or deploy the calculation across different timeframes, the code quickly becomes unmanageable. To ensure robust performance, we isolate the VWAP calculation engine inside a custom include file named VWAP\_Engine.mqh. This object-oriented approach achieves a clean separation between mathematical data processing and order routing mechanics. The visual chart indicator and the trading robot will call the same external include class, ensuring that our calculation output remains completely identical across both modules.

The most difficult engineering hurdle when building a session VWAP is identifying the starting point of the current trading day. In standard MQL5 development, you cannot simply look back a fixed number of bars like 20 or 200. On a standard 5-minute chart, a full day should theoretically contain 288 candlesticks. However, if the market closes early for a holiday, or if the broker server drops connection packets during low-liquidity hours, the actual number of bars will fluctuate unpredictably. Hardcoding a static lookback window will force the loops to pull data from the previous day, completely corrupting the intraday volume-weighting math.

The data loop relies on a strict double-pass linear profile. The first pass iterates through the synchronized rates memory to calculate the baseline VWAP. It sums the volume products and tracks total liquidity. One critical trap here involves zero-volume environments. During the weekly market rollover or sudden broker disconnections, the platform can print a phantom candle with absolute zero tick volume. Attempting to divide the cumulative price sum by a volume of zero will cause a fatal division-by-zero exception, instantly crashing the Expert Advisor. The engine intercepts this risk with a defensive validation check, dropping the current calculation step if the volume accumulator reads zer

The second pass targets the volume-weighted variance. It scans the same bar window again, subtracting the newly defined baseline VWAP from each bar's typical price. This difference is squared and multiplied by the tick volume of that specific candle to ensure high-liquidity spikes dominate the volatility rating. Finally, the square root of this average gives the standard deviation, allowing the engine to calculate the upper and lower bands dynamically.

No mathematical engine operates in a vacuum. During my validation runs in the Strategy Tester on five-minute charts using the 'Open prices only' modeling mode, I observed a critical constraint embedded in the daily session baseline model. Because the mathematical accumulators reset hard at midnight, the first few candles of a new broker day lack significant volume weight. During the Asian opening hours, the deviation bands become exceptionally tight and hypersensitive to low-liquidity market noise. Applying raw entries during this specific window results in erratic fills and excessive stop-outs.

The development of this session engine provides a robust workspace that separates raw liquidity math from trade management. The core blueprint delivers a complete set of three unified files that work together to map intraday value. The VWAP\_Engine.mqh include file acts as the standalone core, containing the structural anchor checks and double-pass volume loops. The Ind\_Session\_VWAP.mq5 indicator instantiates this class to draw the visual baseline and volatility markers smoothly on the chart screen. Finally, the EA\_VWAP\_Pullback.mq5 robot plugs directly into the include methods, utilizing a strict timing filter to query data safely without risking terminal performance or cluttering memor

The file structure is organized cleanly. VWAP\_Engine.mqh contains the source code for the object-oriented daily reset class. Ind\_Session\_VWAP.mq5 delivers the source code for the chart plotting indicator. EA\_VWAP\_Pullback.mq5 implements the trading logic for the automated pullback robot.

---

# 16984: Price Action Analysis Toolkit Development (Part 10): External Flow (II) VWAP

## Sections

### Conclusion

Having successfully configured the VWAP system, it is crucial to monitor market direction and use VWAP levels for confirmation. The VWAP level is highly respected by the market, often acting as a key support or resistance zone. Additionally, selecting the right timeframe to suit your trading strategy is essential. Shorter timeframes like M1-M15 capture intraday movements, M30 balances precision with a broader perspective, H1-H4 reveal multi-day trends, and daily/weekly charts provide insights into long-term market dynamics. Tailoring your approach to the appropriate timeframe ensures better alignment with your trading goals.

| Date | Tool Name | Description | Version | Updates | Notes |
| --- | --- | --- | --- | --- | --- |
| 01/10/24 | [Chart Projector](https://www.mql5.com/en/articles/16014) | Script to overlay the previous day's price action with ghost effect. | 1.0 | Initial Release | First tool in Lynnchris Tool Chest |
| 18/11/24 | [Analytical Comment](https://www.mql5.com/en/articles/15927) | It provides previous day's information in a tabular format, as well as anticipates the future direction of the market. | 1.0 | Initial Release | Second tool in the Lynnchris Tool Chest |
| 27/11/24 | [Analytics Master](https://www.mql5.com/en/articles/16434) | Regular Update of market metrics after every two hours | 1.01 | Second Release | Third tool in the Lynnchris Tool Chest |
| 02/12/24 | [Analytics Forecaster](https://www.mql5.com/en/articles/16559) | Regular Update of market metrics after every two hours with telegram integration | 1.1 | Third Edition | Tool number 4 |
| 09/12/24 | [Volatility Navigator](https://www.mql5.com/en/articles/16560) | The EA analyzes market conditions using the Bollinger Bands, RSI and ATR indicators | 1.0 | Initial Release 

## Key paras

This article presents a powerful tool built around the concept of Volume Weighted Average Price (VWAP) to deliver precise trading signals. Leveraging Python's advanced libraries for calculations enhances the accuracy of the analysis, resulting in highly actionable VWAP signals. We’ll start by exploring the strategy, then delve into the core logic of the MQL5 code and discuss the outcomes. Finally, we’ll wrap up with a conclusion. Let’s take a look at the table of contents below:

VWAP, or volume-weighted average price, is a technical analysis tool that reflects the ratio of an asset's price to its total trading volume. It gives traders and investors a sense of the average price at which a stock has been traded over a specific period. VWAP is often used as a benchmark by more passive investors, such as pension funds and mutual funds, who seek to evaluate the quality of their trades. It is also valuable for traders looking to determine whether an asset was bought or sold at an optimal price.     To calculate VWAP, the formula is:

The VWAP is typically calculated using orders placed during a single trading day. However, it can also be applied across multiple timeframes for a broader market analysis. On a chart, VWAP appears as a line, and it serves as a dynamic reference point. When the price is above the VWAP, the market is generally in an uptrend. Conversely, when the price is below the VWAP, the market is typically considered to be in a downtrend. In the image below, I have visualized the VWAP strategy by highlighting key levels where price tends to react around the VWAP. These marked levels show how the market often interacts with the VWAP line.

The VWAP Expert Advisor (EA) is designed to monitor charts and interact seamlessly with Python for advanced market analysis. It sends market data to Python and logs the received trading signals in the MetaTrader 5 Experts tab. The strategy utilizes the Volume-Weighted Average Price (VWAP) as its core indicator to provide precise and actionable insights. Below is a detailed breakdown of the strategy:

The Python script calculates VWAP using the received data and leverages advanced libraries for precise computation. Two libraries handle the core calculations and analysis: *Pandas* and *NumPy*. Pandas facilitates data manipulation, rolling averages, and cumulative calculations, while *NumPy* manages numerical operations, including conditional logic and vectorized computations. Together, they provide efficient and accurate processing for time-series data analysis.

- VWAP Calculation: Determines the average price weighted by volume over the selected timeframe. - Signal Generation: Provides trading signals (e.g., buy/sell) based on the relationship between current price and VWAP levels. - Explanations: Each signal includes a textual explanation to clarify why it was generated.

> | Python | MQL5 | > | --- | --- | > | Handles large datasets efficiently. | Monitors the market and integrates with the chart in real-time | > | Leverages robust libraries for advanced computation and modeling | Offers immediate alerts and notifications | > | Ensures better accuracy and flexibility in VWAP-based strategies | Using VWAP on MQL5 helps highlight key levels of market support and resistance. This allows traders to make decisions based on the market's reaction to VWAP, which often acts as a strong pivot point for price movements. |

HTTP POST is used here because it’s the best way to send data to a server without altering the URL. WebRequest() handles the communication with the Python server, where all the heavy lifting (i.e., VWAP calculations) happens. The timeout ensures the EA doesn’t hang if the server is unresponsive, maintaining smooth operation.

After sending the data, we need to handle the response from the Python server. This is where the real magic happens, as the Python server analyzes the data and provides a trading signal based on the VWAP (Volume Weighted Average Price). The response is returned in JSON format, and we use a helper function, *ExtractValueFromJSON()*, to extract the relevant values (VWAP and explanation) from the response.

Handling the response correctly is critical for interpreting the server’s analysis. The ExtractValueFromJSON() function ensures that we only retrieve the data we need (VWAP and signal explanation) from the potentially large JSON response. If the response is invalid or the expected data isn’t found, it’s important to handle errors and avoid acting on incorrect signals.

The script's flow is designed to preprocess data, calculate VWAP and relevant metrics, generate signals, and return meaningful information to the EA for decision-making. This includes determining the major and minor support/resistance levels, along with the VWAP and signal explanations. Let's follow the steps below:

The script calculates the VWAP (Volume Weighted Average Price) and additional metrics like typical price, average price, average volume, and support/resistance levels.

---

# 22063: Beyond the Clock (Part 1): Building Activity and Imbalance Bars in Python and MQL5

## Sections

### Conclusion

Time bars are the default because they are easy to construct, not because they are correct. Every assumption that makes financial ML harder — non-constant variance, serial correlation, overrepresentation of quiet periods — traces in part to the fixed-clock sampling convention. The bar types in *afml.data\_structures.bars* replace that convention with one grounded in market activity: dollar value, tick count, traded volume, or directional imbalance.

Four implementation details separate a working bar constructor from one that produces subtly wrong training data. The first is the zero-tick-volume filter for time bars: phantom bars from market closures and holidays look identical to real bars in the OHLC columns and must be explicitly removed. The second is automatic threshold calibration for imbalance bars: passing *target\_timeframe* to *make\_bars()* now derives E0[T] and E0[imbalance per tick] internally from the tick data, eliminating the manual warm-up pass that AFML leaves implicit. The third is unique to live deployment: the EWM state of imbalance bars must be persisted across EA restarts, with a staleness check so that a quiet Friday close does not set an inappropriate threshold for a Monday news open. The fourth is CSV append semantics in the EA: opening the output file in overwrite mode silently discards all bars produced before the last restart, which defeats the purpose of per-session logging.

The infrastructure layer — partitioned Parquet storage read via Dask — is not optional for anything beyond a small toy dataset. A single year of tick data for a single currency pair exceeds what most workstations can hold in memory, and the penalty for loading more than is needed grows with dataset size. Partitioning by year and month, combined with Dask

## Key paras

# Beyond the Clock (Part 1): Building Activity and Imbalance Bars in Python and MQL5

Four production problems in the pipeline are addressed explicitly: loading multi-year tick data without exceeding memory (partitioned Parquet storage read via Dask), cleaning broker-feed artifacts that corrupt bar construction (zero spreads, duplicate timestamps, NaT indices), calibrating the adaptive threshold for imbalance bars automatically so the first bar does not bias the EWM history, and persisting the EWM tracker across EA restarts so the threshold does not reset mid-session. A short parity test at the end verifies that the two implementations, fed the same tick stream, produce identical bars.

López de Prado formalizes this intuition in Chapter 1 of *Advances in Financial Machine Learning* (AFML). The core argument is that bars should close when a fixed amount of market activity has occurred, not when a fixed amount of time has elapsed. Activity can be measured in ticks, traded volume, or traded dollar value — each measure producing a different sampling scheme with different statistical properties. The most aggressive version of this idea, imbalance bars, closes a bar when the market's directional intent exceeds a threshold, capturing regime changes that none of the activity-based samplers can detect.

The first lesson learned during implementation had nothing to do with sampling theory. Tick data for a single currency pair over a single calendar year can exceed 50 million rows. Loading that into a pandas DataFrame at session start takes minutes and consumes several gigabytes of RAM. Two changes eliminate both problems: store raw tick data in columnar Parquet format partitioned by year and month, and load it out-of-core using Dask rather than pandas.

All four standard bar types share a single internal construction path. A grouper object partitions the tick DataFrame by bar membership; aggregation over each group produces OHLC prices, mean spread, and cumulative volume. The *\_make\_bar\_type\_grouper()* function encodes the partitioning logic for each type:

Time bars are the only bar type where the grouper can produce empty groups. A one-hour bar during a market holiday or a session close contains zero ticks. That empty bar is not a data point — it is an absence of data — and passing it downstream propagates a silent error: the OHLC values for an empty group are undefined (pandas returns NaN), and the bar's tick\_volume is zero, which causes division errors in any feature that normalizes by bar activity.

- Panel (a): hourly tick density for a typical FX pair, with UTC hours 00–07 highlighted as the zero-tick risk zone. These hours correspond to late US session/Asian session close for majors. - Panel (b): bar count before and after applying the zero-tick filter over a 5-day sample. 30 phantom bars are removed without affecting any tick that actually traded.

- Panel (a): time bars (blue), closing every 60 seconds. Boundaries are evenly spaced regardless of market activity. - Panel (b): tick bars (green), closing every 100 ticks. Boundaries are also regular but aligned to activity count rather than clock time. - Panel (c): volume bars (orange), closing when cumulative volume reaches a threshold. Boundaries cluster during high-volume periods and spread apart during quiet ones. - Panel (d): dollar bars (purple), closing when cumulative dollar value reaches a threshold. Similar to volume bars but price-weighted, making the threshold more stable across symbols with different price scales.

Standard bars close on activity. Information bars close on *directional* activity — the net imbalance between buyer-initiated and seller-initiated trades. The idea is that a bar that closes when the market has committed to a direction contains more decision-relevant information than one that closes when a volume threshold is crossed regardless of direction.

The tick rule is a proxy. It misclassifies a meaningful fraction of trades, particularly in markets where the bid-ask spread is wide relative to the tick size. The Lee-Ready algorithm improves classification accuracy for datasets that include the quoted bid and ask at each trade, but the tick rule is sufficient for the purposes of imbalance bar construction and avoids the additional complexity of mid-quote comparisons.

A tick imbalance bar closes when the cumulative signed metric θT exceeds a threshold derived from the expected bar length and the expected per-tick imbalance. For tick imbalance bars, the metric per tick is simply bt. For volume imbalance bars, it is bt · vt. For dollar imbalance bars, it is bt · pt · vt. The bar closes at tick T when:

The implementation in *\_detect\_imbalance\_boundaries()* maintains two incremental EWM scalars — one for the expected bar length, one for the expected absolute imbalance — updated with a single multiply-add at each bar close:

---

# 21825: Creating Custom Indicators in MQL5 (Part 9): Order Flow Footprint Chart with Price Level Volume Tracking

## Sections

### Conclusion

In conclusion, we have built a [footprint](https://en.wikipedia.org/wiki/Order_flow_trading "https://en.wikipedia.org/wiki/Order_flow_trading") chart indicator in MQL5 that tracks tick-by-tick volume at quantized price levels, separates buying and selling activity into bid versus ask and delta display modes, and renders volume-colored labels on a canvas overlay alongside trend line candles that update in real time.

The implementation covered price level quantization and volume accumulation into a structured footprint array, max value computation for color normalization, descending price level sorting, coordinate conversion from bar index and price to canvas pixels, and a chart-responsive redraw system that reacts to scroll, zoom, resize, and new tick events. After the article, you will be able to:

- Read the delta column on each bar to identify where buying or selling aggression was strongest at specific price levels, using a high positive delta near support as confirmation for long entries and a high negative delta near resistance as confirmation for short entries
- Switch to bid versus ask mode and scan for diagonal imbalances where ask volume at one level significantly outweighs bid volume at the level directly below it, treating stacked imbalances as directional pressure zones that price is likely to follow
- Identify price levels with the highest total volume inside a bar as that bar's point of control, and use revisits to those levels on subsequent bars as high-probability reference points for entries, exits, and stop placement

In the next part, we will enhance this footprint chart by adding a per-bar volume sentiment information box above each candle displaying the net delta, total volume, and buy and sell percentages with rounded corners, conf

## Key paras

In our [previous article (Part 8)](https://www.mql5.com/en/articles/21390), we enhanced the hybrid [Time Price Opportunity](https://snpedge.vicitradingsolutions.com/p/understanding-time-price-opportunity "https://snpedge.vicitradingsolutions.com/p/understanding-time-price-opportunity") market profile indicator in MQL5 by adding volume data to calculate the point of control, value areas, and volume-weighted average price with customizable highlights. In Part 9, we build an [order flow footprint](https://en.wikipedia.org/wiki/Order_flow_trading "https://en.wikipedia.org/wiki/Order_flow_trading") chart indicator that tracks tick-by-tick volume at quantized price levels, separates buying and sel

The [input](https://www.mql5.com/en/docs/basis/variables/inputvariables) section is organized into two groups. Under settings, we declare "displayMode" defaulting to "DELTA", "ticksPerPriceLevel" to control how many ticks wide each price row is, "maxBarsToRender" to limit memory usage by capping stored bars, "priceLevelFontSize" for text sizing on the canvas, and "useStrictPricePositions" to toggle whether overlapping price labels are spread apart or kept at their exact prices. Under colors, we declare five-step gradient inputs for upward volume, downward volume, and total volume — each ranging from the weakest shade to the strongest — plus a separate "candleWickColor" for the trend line wic

To handle the bid versus ask diagonal imbalance coloring, we define the "GetDiagonalVolumeColor" function, which uses a different ratio scale because it compares volumes across adjacent price levels rather than against a bar-wide maximum. Here, the thresholds are 1.5, 2, 3, and 4, reflecting the fact that a meaningful diagonal imbalance requires one side to be a multiple of the other rather than just a fraction. When the ask volume at a level is at least four times the bid volume at the level directly below it, the strongest up color is returned, signaling stacked buying pressure. The same logic applies in reverse for dominant bid volume, returning the strongest down color to highlight aggre

For "BID\_VS\_ASK" mode, an additional diagonal imbalance pass runs after the initial color assignment. It walks adjacent level pairs and checks whether the ask volume at the upper level or the bid volume at the lower level is significant enough — at least 30 percent of its bar-wide maximum — to warrant imbalance coloring. When the threshold is met, it computes the ratio of one side to the other with a small epsilon added to the denominator to prevent division by zero, then calls "GetDiagonalVolumeColor" to override the color for that specific label, highlighting the stacked pressure pattern visually.

In conclusion, we have built a [footprint](https://en.wikipedia.org/wiki/Order_flow_trading "https://en.wikipedia.org/wiki/Order_flow_trading") chart indicator in MQL5 that tracks tick-by-tick volume at quantized price levels, separates buying and selling activity into bid versus ask and delta display modes, and renders volume-colored labels on a canvas overlay alongside trend line candles that update in real time.

---

# 21829: Creating Custom Indicators in MQL5 (Part 10): Enhancing the Footprint Chart with Per-Bar Volume Sentiment Information Box

## Sections

### Conclusion

In conclusion, we have extended the [footprint](https://en.wikipedia.org/wiki/Order_flow_trading "https://en.wikipedia.org/wiki/Order_flow_trading") indicator from a level-centric display into a combined per-level and per-bar tool by adding cached bar fields — "boxColor", "textColor", "delta", "upPercentage", and "downPercentage" — to the "BarFootprintData" structure, computing them once per tick via "CalculateBarColorsAndPercentages" to keep redraws lightweight. We built a complete rendering pipeline covering delta-intensity color mapping, percentage-based text intensity, rounded rectangle geometry using scanline quadrilateral fill and precise arc stroking, an optional supersampling and box-filter downsampling pass, and per-pixel [Porter-Duff alpha compositing](https://en.wikipedia.org/wiki/Alpha_compositing "https://en.wikipedia.org/wiki/Alpha_compositing") so the sentiment box overlays the footprint without obscuring price level detail. All drawing is centralized in "RedrawCanvas" while the "OnCalculate" event handler remains responsible only for per-tick updates and cache maintenance. After the article, you will be able to:

- Read the sentiment box color and delta value above each candle to instantly judge whether buyers or sellers dominated that bar in aggregate, using strongly colored boxes with high delta as confirmation signals and weakly colored boxes as indecision markers before committing to a directional trade
- Use the percentage split in the sentiment box to distinguish bars where one side barely edged out the other from bars with heavily lopsided participation, treating high-percentage dominance near key levels as stronger evidence of absorption or aggression than a narrow split at the same price
- Scan the sentiment box colors across con

## Key paras

In our [previous article (Part 9)](https://www.mql5.com/en/articles/21825), we built an [order flow footprint](https://en.wikipedia.org/wiki/Order_flow_trading "https://en.wikipedia.org/wiki/Order_flow_trading") chart indicator in MQL5 that tracked tick-by-tick volume at quantized price levels, separated buying and selling activity into bid versus ask and delta display modes, and rendered volume-colored text labels on a canvas overlay alongside trend line candles with real-time updates. In Part 10, we add a per-bar sentiment box above each candle showing net delta, total volume, and buy and sell percentages with delta-intensity color coding, supersampled rendering for anti-aliased output, ro

A completed bar contains information that price level rows do not summarize well. Net delta shows which side was more aggressive in aggregate, total volume shows whether that aggression happened on meaningful participation or thin activity, and the buy and sell split reveals the degree of imbalance. When these three numbers are visible above every candle in a compact, color-coded box, a trader can scan across dozens of bars in seconds and immediately identify which bars were dominated by one side, which were balanced, and whether the dominance was backed by high or low volume, without reading a single price level row.

The text color derivation follows a different approach. Rather than using the delta-to-total ratio, it takes the dominant side's percentage, subtracts 50 to find how far above an even split it sits, clamps any negative result to zero, then divides by 50 to scale the excess into a zero-to-one ratio using the [MathCeil](https://www.mql5.com/en/docs/math/mathceil) function. This means a perfectly even 50-50 bar produces the weakest text color, while a heavily one-sided bar produces the strongest, making the text itself carry a visual signal about the degree of imbalance. With both colors and percentages cached in the structure, we can now build the geometry utilities that the rounded corner ren

In this version, the "RenderFootprint" function is simplified to handle only candle rendering, with all price level label drawing and information box logic moved into "RedrawCanvas" for centralized control. The redraw function now handles the complete per-bar pipeline — price level labels, diagonal imbalance coloring, and the new supersampled information box — all within a single loop over visible bars.

In "RedrawCanvas", we retain the same outer structure from the previous part — fetching high, low, and time arrays, erasing the canvas, and looping over visible bars — but now handle two major blocks per bar. In the first block, we build the "displayPrices" array, optionally spread overlapping labels using the new "minPriceLevelSpacing" multiplier, populate left and right text and color arrays per level based on the active display mode, apply diagonal imbalance coloring in bid versus ask mode, set the font with [FontSet](https://www.mql5.com/en/docs/standardlibrary/canvasgraphics/ccanvas/ccanvasfontset), compute the horizontal gap anchors, and draw each label pair with [TextOut](https://www.

---

# 21984: Creating Custom Indicators in MQL5 (Part 11): Enhancing the Footprint Chart with Market Structure and Order Flow Layers

## Sections

### Conclusion

We have enhanced the [footprint chart indicator](https://en.wikipedia.org/wiki/Order_flow_trading "https://en.wikipedia.org/wiki/Order_flow_trading") in MQL5 by adding twelve layered visual and analytical overlays, including a volume profile behind each bar, point of control and value area highlighting, stacked imbalance detection with directional icons, absorption zone classification, single print and unfinished business markers, a cumulative volume delta panel, and a per-bar delta histogram. The implementation covered the extended bar and price level structures, dedicated computation functions for point of control, value area expansion, imbalance streak detection, and absorption classification, a layered canvas redraw pipeline that draws each overlay in a defined sequence, and an updated calculation event handler that calls all new analytical functions and maintains the running cumulative delta on every tick. After reading this article, you will be able to:

- Use the point of control and value area overlay to identify the accepted price zone inside each bar, treating returns to the point of control from a deviation as mean-reversion reference points and using value area boundaries as support and resistance levels for the next bar's price action
- Identify stacked imbalance zones marked by the directional icons and use them as directional fuel indicators — entering in the direction of a stacked ask zone when price holds above it, or a stacked bid zone when price holds below it, and treating absorption bars at key levels as potential reversal candidates when the cumulative volume delta diverges from price direction
- Monitor the cumulative volume delta panel for sustained divergence from price direction as an early warning of exhaustion, and use the del

## Key paras

In our [previous article (Part 10)](https://www.mql5.com/en/articles/21829), we enhanced the MQL5 footprint chart indicator by adding a per-bar volume sentiment information box with delta-intensity color coding, supersampled rounded corners, and alpha compositing. In Part 11, we introduce volume profile bars, point of control and value area highlighting, stacked imbalance detection, absorption zone classification, single print markers, a cumulative volume delta panel, and a delta histogram. This article will cover the following topics:

Stacked imbalances occur when ask volume at a level significantly outweighs bid volume at the level directly below it, or vice versa, across multiple consecutive rows. When this pattern stacks three or more levels deep, it signals a directional pressure zone where one side was repeatedly aggressive without meaningful opposition. Absorption is the opposite condition — a bar with high total volume but a net delta close to zero, meaning that one side absorbed the aggression of the other without allowing the price to move, often preceding a reversal. The cumulative volume delta tracks the running sum of net delta across all bars, revealing whether buying or selling pressure is building or fading

The imbalance detection group adds toggles and thresholds for stacked row highlights, the minimum consecutive levels required to qualify as a stack, the ask-to-bid ratio that triggers detection, highlight transparency, directional triangle icons, absorption zone overlays, the delta-to-total ratio threshold for absorption classification, single print dashed borders, and unfinished business dotted markers at extreme one-sided levels.

The cumulative delta group introduces the cumulative volume delta panel toggle, panel height, positive and negative line colors, the per-bar delta histogram toggle, and its height. The colors group retains all existing inputs and adds dedicated colors for the point of control line, value area fill, stacked ask and bid imbalance highlights, absorption zones, and single print borders. The information box group retains all previous inputs and adds a toggle for the mini buy and sell percentage bar inside the box. Finally, the filters group adds a dynamic font size toggle that scales labels with zoom level, and a minimum volume threshold that hides levels below a configurable activity floor. With

The "BarFootprintData" structure retains all fields from the previous version and gains nine new ones to support the additional layers. We add the point of control index to reference the highest-volume level directly, value area high and low indices to define the accepted value boundary, and the cumulative delta to carry the running net delta total forward from bar to bar. Four fields track stacked imbalance detection: boolean flags for ask and bid stacking, and integer start indices that tell the renderer exactly where the imbalance zone begins. Finally, the absorption bar flag marks bars where high total volume produced a near-zero net delta, classifying them for the absorption overlay. Th

The new visual layers require smooth color transitions between states — for example, graduating volume profile bar colors or blending imbalance highlights against existing canvas content. Rather than snapping between fixed color values, we introduce a linear interpolation function that produces any shade between two colors based on a normalized factor.

When value area expansion is enabled, we compute the target volume as the configured percentage of the bar's total volume, initialize both bounds at the point of control, and enter an expansion loop. On each iteration, we sample the volume one level above the current upper bound and one level below the current lower bound, then extend whichever boundary would add more volume. This continues until the accumulated coverage meets or exceeds the target, or no further expansion is possible. The final upper and lower bound indices are stored in the structure for the rendering pipeline to use directly. With the point of control and value area computed, we now define the imbalance and absorption det

For imbalance detection, we walk adjacent level pairs and check the diagonal ask condition — ask volume at the upper level divided by bid volume at the level directly below it — against the configured ratio threshold. A consecutive streak counter increments on each passing pair and resets to zero on any failure. When the streak reaches the minimum stack depth, and no ask imbalance has been recorded yet, we set the flag and calculate the start index by offsetting back from the current position. The same process runs independently for the bid side, checking bid volume at the lower level against ask volume at the level above.

Absorption detection runs after the imbalance scan. We compute the absolute delta using [MathAbs](https://www.mql5.com/en/docs/math/mathabs) and divide it by the bar's total volume. If this ratio falls at or below the configured absorption threshold, the bar is marked as an absorption bar, indicating that one side absorbed the other's aggression without allowing meaningful price movement.

Layer 3 draws stacked imbalance row highlights when detected. For both the ask and bid sides, we loop from the imbalance start index through the configured number of levels plus a small extension, filling each row with a semi-transparent rectangle in the corresponding imbalance color. Layer 4 draws the absorption zone overlay when the bar is classified as absorption. We fill the full bar vertical extent with a very low opacity tint, then draw top and bottom border lines at higher opacity using [LineAA](https://www.mql5.com/en/docs/standardlibrary/canvasgraphics/ccanvas/ccanvaslineaa) to frame the zone without obscuring the levels beneath. Layer 5 draws the point of control dashed line at the

Layer 6 builds the left and right label text and color arrays for all levels, formatting them for delta mode or bid versus ask mode exactly as in the previous version, then applies diagonal imbalance color overrides in bid versus ask mode. Layer 7 draws the price level text labels, but first checks the minimum volume threshold and skips any level below it. For single print levels, it draws dashed top and bottom borders using "DrawDashedHLine". For unfinished business levels, it places dots at every fourth pixel across the bar width using the [PixelSet](https://www.mql5.com/en/docs/standardlibrary/canvasgraphics/ccanvas/ccanvaspixelset) method. The left and right labels are then drawn with [T

The calculation event handler retains its full structure from the previous version with two targeted additions: the new bar initialization block sets all the extra structure fields to clean starting values, and the per-tick volume processing block calls the two new analytical functions and updates the running cumulative delta after every volume change.

---

# 2612: Testing trading strategies on real ticks

## Sections

### Comparing results of different test modes

Test results in different modes are displayed in the table. The first thing that catches the eye is the difference in the number of trading operations. Thus, all other test results are also different. Testing in "1 minute OHLC" took 1.57 seconds which is 23 times faster than in "Every tick" mode. Such a difference is important when optimizing the trading system inputs.

In its turn, the mode "Every tick based on real ticks" has turned out to be even more time-consuming – 74 seconds as compared to 36.7 seconds in "Every tick" mode. This can be easily explained by the fact that more than 34 million ticks have been modeled when using real ticks which is almost two times more than in "Every tick" mode. Thus, the more ticks are used in tests, the more time is required for one pass in the strategy tester.

| Parameter | 1 minute OHLC | Every tick | Every tick   based on real ticks |
| --- | --- | --- | --- |
| Ticks | 731 466 | 18 983 485 | 34 099 141 |
| Net profit | 169.46 | -466.81 | -97.24 |
| Trades | 96 | 158 | 156 |
| Deals | 192 | 316 | 312 |
| Equity drawdown % | 311.35 (3.38%) | 940.18 (9.29%) | 625.79 (6.07%) |
| Balance drawdown | 281.25 (3.04%) | 882.58 (8.76) | 591.99 (5.76%) |
| Profitable trades (%) | 50 (52.08%) | 82 (51.90%) | 73 (46.79%) |
| Average consecutive wins | 2 | 2 | 2 |
| Testing time including tick generation time | **1.6** seconds | **36.7** seconds | **74** seconds (1 minute 14 seconds) |

Test reports of various modeling modes are displayed below as animated GIF images allowing you to compare the parameters.



The balance and equity graphs are different as well. As we can see, this simple strategy is not impressive – growth periods are followed by drawdowns and the test graphs look more like a ch

## Key paras

Comparing the results allows us to assess the quality in various modes, as well as helps us to use the tester more efficiently in order to receive results faster. "1 minute OHLC" mode allows receiving quick estimated test results, "Every tick" mode is closer to reality, while testing on real ticks is most accurate but time-consuming. Keep in mind that errors in a trading robot's logic may affect the number of trading operations making the strategy test results more susceptible to a selected test mode.

In its turn, the mode "Every tick based on real ticks" has turned out to be even more time-consuming – 74 seconds as compared to 36.7 seconds in "Every tick" mode. This can be easily explained by the fact that more than 34 million ticks have been modeled when using real ticks which is almost two times more than in "Every tick" mode. Thus, the more ticks are used in tests, the more time is required for one pass in the strategy tester.

MetaTrader 5 strategy tester allows checking trading strategies in four tick modeling modes described in the article ["The Fundamentals of Testing in MetaTrader 5".](https://www.mql5.com/en/articles/239) The fastest and most rough mode is "**Open prices only**", at which trading operations can be performed only at the opening of a new bar. No trading actions inside bars are available. The mode is most suitable for testing strategies that are not dependent on the price movements inside bars.

These two modes are suitable for testing a large set of trading strategies, since most traders develop robots for trading at a new bar opening. However, if you need to conduct a more accurate and detailed modeling of the incoming ticks, you will need "**Every tick"** mode. In this mode, the price behavior within each minute bar is additionally modeled. The ticks are generated according to complex (but predefined) laws. The price modeling mechanism for this mode is described in details in the article ["The Algorithm of Ticks' Generation within the Strategy Tester of the MetaTrader 5 Terminal".](https://www.mql5.com/en/articles/75)

If you need the most accurate representation of history data in the strategy tester, use "**Every tick based on real ticks**" mode. In this mode, the tester downloads real ticks from a broker's trade server and uses them to display the price development. In case real ticks are absent for some time intervals, the tester simulates the price just like in the "**Every tick**" mode. Thus, if the broker has all history of the required symbols, you can perform testing of real historical data without artificial modeling. The drawback of the mode is a significant increase in test time as shown in the comparison table above.

Trading servers accumulate real tick history for many years, and the MetaTrader 5 strategy tester is capable of downloading it automatically in "Every tick based on real ticks" mode. However, the more reliable the test, the more resources it requires. Therefore, you should always strike a balance between accuracy and speed.

---

# 11106: Developing a Replay System — Market simulation (Part 17): Ticks and more ticks (I)

## Sections

### Final considerations

The article is coming to an end because the required steps may lead to some confusion in the material already presented. So in the next article we will look at how to fix some things that are not working properly in the current system. However, you can use the system without fast forwarding or rewinding. If you do this, the tick data in the Market Watch or the price line information may not match the current situation on the replay/simulation chart.

As you see, I prefer just mini-index type contracts. So, I want you to test the system on other assets. This will clarify how the replay/simulation system will behave in relation to what we put into it. I just want to make one thing clear: there are still some flaws in the fast forwarding system. Therefore, I suggest that you, at least for now, avoid using this feature.

In these tests that I offer you, I want you to pay due attention to both the liquidity and volatility of the asset you choose. Check performances of different assets. Note that on assets with fewer trades in the 1-minute interval, the replay/simulation system seems to have difficulties. In a way, it's good to see this now because this part requires a fix. Although the design of bars seems to be correct. We'll make this fix soon. I want you, dear readers, to understand why the replay/simulator service seems strange before we fix this bug. This understanding is important if you really want to get into programming. Don't stop at creating only simple and easy programs. Real programmers are those who solve problems when they arise, not those who give up at the first sign of difficulty.

However, when observing the time in both the Market Watch window and the in value provided by the metrics system, the replay/simulator service is unable

## Key paras

Here we will begin to implement this system, but in the simplest possible way. First, we will make it appear in the Market Watch window (Fig. 01). After that, we will try to make it appear in other places. Getting it to appear in the Market Watch window will be a challenge. At the same time, it will be interesting, since when we implement and use the simulation of movements with an interval of 1 minute, the tick chart in the "Market Watch" window will display the RANDOM WALK created by the tester. This is all very interesting.

---

# 11113: Developing a Replay System — Market simulation (Part 18): Ticks and more ticks (II)

## Sections

### Conclusion

In this article, I showed you how to implement the system for setting and creating ticks on a chart with Market Watch. We started doing this in the previous article. As a result, we created a simulation system capable of simulating even direct orders. This was not part of our initial goals. We are still quite a long way from this being fully usable in some types of trading systems. But what we did today is just the beginning.

In the next article, we will continue our series on creating the market replay/simulation system. The attachment contains 4 different resources for testing and checking the system operation. Remember that I will provide both real tick data and 1-minute bars so you can see the difference between the simulated and real values. This will allow you to start analyzing things more deeply. To understand everything explained here, you will need to run the replay/simulation service in both modes. First check out the custom symbol when running the simulation, and then look at what it with the replay. But pay attention to the tick window, not the chart itself. You will see that the difference is really noticeable. At least regarding the contents of the Market Watch window.

Translated from Portuguese by MetaQuotes Ltd.   
Original article: <https://www.mql5.com/pt/articles/11113>

**Attached files** |

## Key paras

[MetaTrader 5](https://www.mql5.com/en/articles/mt5) — [Tester](https://www.mql5.com/en/articles/mt5/strategy_tester) | 8 December 2023 at 02:43

**NOTE:** So don't ever believe that you can and will always operate within the spread. Sometimes the system can go beyond the spread. It is important that you know this because when developing an order system, this information and its proper understanding will be critical.

This is simple yet functional. Pay attention that the BID value should not be allowed to collide with the ASK value (this is in the exchange market, as in the forex market it is a different story, but we will see this later). What causes the collision is the value of the last executed deal. What if we make a small change to the code shown above? Something very subtle. What happens if the BID or ASK value changes without actually changing the last deal price?

Look how interesting it is. By adding a certain level of randomness to the system, we have enabled the inclusion of direct orders. That is, of the orders that will be executed without changing the BID or ASK. In the real market, such orders do not occur very often, and not in the form in which the system will display them. But if we ignore this fact, we will already have a good system in which at times there will be a small spread between BID and ASK included. In other words, the simulator practically adapts to a much more common situation in the real market. However, we should beware of an overabundance of direct orders. To avoid this excess, we can make things a little less random.

Here we control the level of complexity of random generation. This is done to keep everything within a certain degree of contingency. We will have direct orders from time to time. But this will be done in more controlled quantities. To do this, we will simply adjust these values here. By adjusting them, we create a small window in which the spread is likely to be slightly larger than the minimum possible value. As a result, from time to time, we will deal with direct orders generated by the modeling system, something that was not possible in previous articles or until now.

---

# 23465: Exporting Symbol Tick Data to Binary Files in MQL5 for Offline Analysis

## Sections

### Limitations

CopyTicksRange() retrieves ticks from the terminal's local tick history cache. If the requested date range precedes the cache window, CopyTicksRange() returns fewer ticks than the date range implies, or returns zero, without raising an error. The terminal downloads tick history on demand when a chart for the symbol is open, but deep historical ranges may not be cached. The user must ensure the terminal has downloaded tick history for the requested period before running the export script.

For very large date ranges on active symbols, CopyTicksRange() may attempt to return tens of millions of ticks in a single call. Each MqlTick struct is approximately 64 bytes, so 10 million ticks requires around 640 MB of memory. The script does not chunk the request into smaller time windows, which means it can exhaust available memory for long date ranges on liquid symbols during active market sessions. Adding a chunked fetch that loops over sub-ranges and appends to the output file would address this, at the cost of additional code complexity.

The binary file format is little-endian, reflecting the byte order of x86 and x86-64 processors. Python and NumPy handle little-endian natively on the same hardware, but a reader on a big-endian system such as a SPARC or PowerPC workstation would need to byte-swap each field. The version field in the header provides a hook for detecting this in a future format revision.

The format stores MqlTick.volume as a ulong integer but does not store MqlTick.volume\_real, the floating-point real volume available for exchange instruments. Analysis of exchange order flow requires volume\_real, which would need a format version increment to add a double field to the tick record.

The script exports a snapshot: it reads the tick history at

### Conclusion

This article presents a complete, compilable implementation for exporting MetaTrader 5 tick history to a structured binary file. The reader leaves with four working components. CTickRecord defines the 48-byte binary layout of one tick on disk, with a FromMqlTick() method that converts the terminal's native MqlTick struct. CTickFileHeader defines the 64-byte file header carrying the magic number, symbol, decimal precision, millisecond range, and tick count. CTickExporter owns the complete pipeline: fetching tick data from the terminal with CopyTicksRange(), writing the header with FileWriteStruct(), and writing all records in a single FileWriteArray() call. TickDataExporter.mq5 provides the user-facing script with configurable symbol, date range, output filename, and tick count cap.

The concrete operational guarantees are these: the output file always begins with a 64-byte header whose magic number and version fields allow a reader to validate the format before processing. Every tick record is exactly 48 bytes, enabling random access to any tick by byte offset without scanning. Millisecond-precision timestamps are preserved from MqlTick.time\_msc. The flags bitmask is stored so a reader can filter by tick type after the fact. The Python reader provided in Section 10 loads the complete file into a NumPy structured array in a single frombuffer() call, ready for vectorized analysis.

The honest limitations are the dependency on the terminal's tick history cache being populated for the requested date range, the absence of chunked fetching for very large ranges, the little-endian-only format, the omission of volume\_real, and the static snapshot nature of the export.

**Programs used in the article:**

| # | Name | Type | Description |
| --- | --- | --- | ---

## Key paras

MetaTrader 5 stores complete tick history for every symbol in the terminal's data cache. Every bid change, ask change, and trade print that arrived during the terminal's connected lifetime is accessible through MQL5's tick history API. That data is valuable for offline analysis: spread distribution studies, microstructure research, feed quality audits, input generation for machine learning models, and backtesting at tick resolution with external tools. The problem is that extracting it in a form that external tools can read efficiently is not straightforward.

The obvious approach is to export ticks to CSV. A CSV file is human-readable and universally supported, but it has serious practical limitations for tick data. A single active trading day for a major forex pair can produce several million ticks. At around 60 bytes per tick in CSV format, one trading day fills roughly 180 MB. Reading and parsing that file in Python or R requires string-buffer allocations, delimiter splits, and per-field text-to-float conversion. Only then do you get usable numeric data. Floating-point values printed as text lose precision at the last decimal place. The parse step dominates the load time for any substantial tick history.

- time — server time in seconds (datetime) - bid — bid price (double) - ask — ask price (double) - last — last trade price (double) - volume — tick volume (ulong) - time\_msc — server time in milliseconds (long) - flags — bitmask indicating which fields changed in this tick (uint) - volume\_real — real volume (double, exchange instruments only)

The Python reader uses two mechanisms. struct.unpack() with the format string '<IHH20sqqQ12s' decodes the 64-byte header field by field, where < specifies little-endian byte order and each letter maps to a field type and size. np.frombuffer() with the TICK\_DTYPE structured dtype loads all tick records in a single call with no loop, producing a NumPy array whose columns are named and typed. Accessing ticks['bid'] returns a 64-bit float array over the entire tick set, enabling vectorized spread calculations, histogram binning, and percentile statistics without any Python-level iteration.

Terminal output of tick\_reader.py showing successful integrity verification, sample records, and vectorized spread statistics for 7.4 million binary-exported ticks.

| # | Name | Type | Description | | --- | --- | --- | --- | | 1 | TickRecord.mqh | Include File | Defines the 48-byte binary layout of one tick record on disk, with a method to populate it from an MqlTick struct. | | 2 | TickFileHeader.mqh | Include File | Defines the 64-byte file header carrying the magic number, symbol, precision, millisecond range, and tick count. | | 3 | TickExporter.mqh | Include File | Fetches tick history with CopyTicksRange(), converts records, and writes the complete binary file using FileWriteArray for efficiency. | | 4 | TickDataExporter.mq5 | Script | Entry-point script that accepts symbol, date range, output filename, and tick count cap as inputs and drives the 

---

# 22460: Creating a Custom Tick Chart in MQL5

## Sections

### **Conclusion**

By following the steps in this article, you obtain a practical, verifiable solution for tick‑based charting in MetaTrader 5. The delivered EA:

- creates or activates a custom symbol (eg, TICK\_101) with trading properties copied from the source instrument;
- optionally opens a dedicated chart for that symbol;
- collects incoming ticks and maintains open/high/low/close state while counting ticks;
- seals and sends a completed bar every N ticks with a unique timestamp;
- pushes the forming bar to the chart on every tick so it stays accurate.

Acceptance criteria you can check in the terminal: the custom symbol appears in Market Watch, its chart displays a continually updating live candle, and each candle closed contains exactly the configured number of ticks and an increasing timestamp. This architecture gives you an activity‑driven view of price action, improving visibility of momentum and micro‑structure. From here you can extend the EA with volume handling, persistent storage, different aggregation rules (eg, tick‑volume weighted), or hooks for strategy testing that require tick‑accurate bar boundaries.

The project is supported in [Algo Forge](https://forge.mql5.io/13467913/Article-22460-Custom-Tick-Chart-MQL5 "https://forge.mql5.io/13467913/Article-22460-Custom-Tick-Chart-MQL5").

**Attached files** |

## Key paras

MetaTrader 5 organizes price data using fixed time intervals, which often hides the true intensity of market activity. A one-minute candle formed from hundreds of ticks can appear identical to one created from only a few trades. For scalpers and tick-driven systems, this becomes a major limitation because MetaTrader 5 does not provide a native tick-bar chart.

To ensure uniformity across all bars, the tick volume is subsequently allocated depending on the predetermined number of ticks per candle. Since spread and real volume are not necessary in this unique tick-based structure, they are set to zero. Using CustomRatesUpdate, the finished candle is transmitted to the custom symbol. This crucial stage enables the candle to appear on the chart by pushing the completed OHLC data into TICK\_101. An error notice is given so that the problem can be found if this update fails for any reason.

---

# 18680: MetaTrader tick info access from MQL5 services to Python application using sockets

## Sections

### Conclusion

This article discusses using socket programming to send tick data from MetaTrader 5 to a python application using MetaTrader services and python server and client. As we can transport tick data as done in this article, we can transport other information about charts as well. I have used services, but we can use scripts, indicators or expert advisors too. And like python, we can use other programming languages too.

Moreover, this article also tries to eradicate the Windows OS dependency. MetaTrader and python library such as MetaTrader 5 all depend on Windows OS. Instead of using the MetaTrader 5 python library, we can use the socket protocol for data transfer from MetaTrader to a more convincing library for easy and advanced processing of MetaTrader data.

| File Name | Description |
| --- | --- |
| TickSocketService.mq5 | MQL file containing codes to connect to socket server at 9070 and then send tick data |
| tick\_server.py | python server socket opening port 9070 for MetaTrader and port 9071 for other clients |
| tick\_client.py | python client socket connecting to port 9071 and receives data sent by the server |

**Attached files** |

## Key paras

---

# 20327: Analytical Volume Profile Trading (AVPT): Liquidity Architecture, Market Memory, and Algorithmic Execution

## Sections

### **Back Test Results**

The back-testing was evaluated on the H4 timeframe across roughly a 2-month testing window (01 September 2025 to 03 November 2025), with the following settings:



Now here is the equity curve and the backtest results:

### Conclusion

In summary, we developed Analytical Volume Profile Trading (AVPT) by breaking down how liquidity architecture, volume distribution, and market memory shape the true structure behind price movements. We explored how volume nodes, high-liquidity shelves, and low-volume inefficiencies form a repeatable blueprint of where markets pause, expand, or reverse. We then translated this structural logic into algorithmic execution—mapping how an EA can read volume profile zones, anticipate liquidity events, and align entries with the deepest institutional footprints rather than surface-level price action.

In conclusion, AVPT gives traders a more intelligent and context-aware approach to execution: trades are no longer triggered solely by patterns or indicators, but by understanding where real liquidity sits and how markets “remember” past imbalances. By integrating market memory, volume clustering, and algorithmic decision-making, traders gain a framework that improves precision, enhances risk placement, and reduces noise-driven signals.

**Attached files** |

## Key paras

---

# 23550: Building a Volume-Based Liquidity Heatmap Indicator in MQL5

## Sections

### **Conclusion**

The Liquidity Heatmap presented in this article provides a reproducible MQL5 implementation that:

- detects high-volume candles using a volume SMA filter;
- estimates liquidation prices below bullish candles or above bearish candles using a user-defined leverage value;
- ranks signals through a rolling buffer using minimum, average, and maximum signal values, then maps relative strength to color and line width;
- visually represents zones using up to three tiers of bubble markers;
- extends each liquidation level forward until price sweeps it, after which the level remains fixed on the chart;
- manages chart clutter through configurable object limits and timestamp-based naming to prevent duplicates.

Important caveats: the displayed levels are probabilistic estimates derived from price and volume data only, not actual liquidation or open interest data. Therefore, they should be treated as one additional analytical layer to combine with market structure analysis, backtesting, and risk management. In practice, the indicator provides a lightweight and configurable approach for highlighting potential liquidity concentration areas and possible liquidity sweep zones that can support manual analysis or automated trading systems.

**Attached files** |

## Key paras

MetaTrader 5 provides OHLC price data and volume information, but it does not provide direct access to exchange-level liquidation data, open interest, or the distribution of leveraged positions. Therefore, an indicator running on MetaTrader 5 cannot identify actual liquidation events or confirm where forced position closures occur. To overcome this limitation, the Liquidity Heatmap indicator is designed as an estimation tool that uses available market data to identify areas where liquidity may be concentrated. Since direct liquidation information is unavailable, the indicator uses high-volume activity as a proxy for potential liquidity concentration.

Since direct liquidation data is unavailable, the indicator uses unusually high volume as a proxy for significant market activity.

- processes candles within the selected lookback range; - selects real volume or tick volume; - calculates the 14-period SMA of volume; - compares current volume against the SMA; - classifies candles with above-average volume as qualified signals.

After that, the program detects the opening time of the current chart bar and compares it with the opening time stored from the previous calculation. If the two values differ, it indicates that a new bar has formed. The indicator then updates the stored timestamp to the current bar's opening time, allowing subsequent calculations or chart updates to be performed only once per newly completed bar rather than on every incoming tick. This improves efficiency by preventing unnecessary repeated processing while the current bar is still forming. The program then processes each candle individually and retrieves its volume value. It first checks whether real volume is available and enabled by the us

---

# 22342: Building a Liquidity Spectrum Volume Profile Indicator in MQL5

## Sections

### **Conclusion**

Following the described design and engineering fixes, you get a complete, practical Liquidity Spectrum Volume Profile for MetaTrader 5 that is testable and configurable. The indicator:

- divides the lookback high/low range into configurable bins and assigns volume by candle close (tick volume preferred, real volume fallback);
- normalizes bin volumes and scales rectangles to a configurable maximum width to highlight relative strength;
- draws the profile as filled rectangles and highlights significant bins with Point-of-Control (POC) horizontal lines using a configurable threshold and width;
- uses barsAgo→datetime conversion to place drawings correctly in time (including a small projection into the future for visibility);
- manages chart objects safely using a unique prefix (so it does not delete other users' objects) and updates only when new data arrives;
- exposes parameters (lookback, number of bins, max width, POC threshold, toggles for profile/POC) so you can adapt behavior without rewriting logic.

Acceptance criteria for the implementation are straightforward: the profile and POC lines appear adjacent to the lookback zone, objects carry the indicator prefix, the indicator recalculates on new bars only, and removing the indicator cleans up only its own objects. The article provides a reproducible code structure (data retrieval → bins and accumulation → normalization → drawing utilities) and highlights practical improvements (prefix cleanup, explicit assumptions, and time-offset handling) that make the indicator reliable in real trading charts.

The project is supported on [Algo Forge](https://forge.mql5.io/13467913/Article-22342-Liquidity-Spectrum-Volume-Profile-Indicator "https://forge.mql5.io/13467913/Article-22342-Liquidity-Spectrum-Volum

## Key paras

Standard per-bar volumes under candles do not show how volume is distributed across price, so it is difficult to tell which exact price levels actually “hold” liquidity within a chosen lookback. This article reframes that problem with explicit assumptions and engineering constraints: the profile will assign volume to price bins using candle close prices, prefer tick volume with a fallback to real volume, and operate on a stable, explicitly copied dataset (Copy\* functions). In practice, three implementation hurdles must be solved to produce a reliable tool in MQL5:

The main function then begins the calculation process. Before doing anything, it first checks whether both visualization options are disabled. If they are, there is nothing to draw, so the function ends instantly. The code then calculates the number of bars that are accessible on the chart and makes sure that the lookback does not go beyond the available history. This keeps errors from attempting to access nonexistent data. The function quits if the lookback is too small because there isn't enough information to do useful computations. The code initializes price/time/volume arrays as series and copies the required lookback data. It uses tick volume first and falls back to real volume. If dat

- divides the lookback high/low range into configurable bins and assigns volume by candle close (tick volume preferred, real volume fallback); - normalizes bin volumes and scales rectangles to a configurable maximum width to highlight relative strength; - draws the profile as filled rectangles and highlights significant bins with Point-of-Control (POC) horizontal lines using a configurable threshold and width; - uses barsAgo→datetime conversion to place drawings correctly in time (including a small projection into the future for visibility); - manages chart objects safely using a unique prefix (so it does not delete other users' objects) and updates only when new data arrives; - exposes para

Mining central bank balance sheet data provides a picture of global liquidity in the Forex market and key currencies. We combine data from the Fed, ECB, BOJ and PBoC into a composite index and use machine learning to uncover hidden patterns. This approach turns raw data into real trading signals by combining fundamental and technical analysis.

Let's try mining CFTC data, downloading COT and TFF reports via Python, connecting all this with MetaTrader 5 quotes and an AI model, and get forecasts. What are COT reports in the Forex market? How to use COT and TFF reports for forecasting?

---

# 18661: Analyzing Price Time Gaps in MQL5 (Part II): Creating a Heat Map of Liquidity Distribution Over Time

## Sections

### Interpreting the results: What the colors mean

Red zones (1-25% presence) indicate areas that price passes through quickly. These are the potential time gap zones described in the previous article. Red zones often experience rebounds and false breakouts, so they require a cautious approach.

Orange and yellow zones (25-75%) represent areas of moderate activity. Here the price lingers periodically, but without obvious dominance. These are transition zones that can become support or resistance, depending on the market context. These are the zones where trend-following trades often work best.

The blue and light blue zones (75-100%) are the main focus of our analysis. This is where the price spends most of its time, indicating high trading activity. These levels have a strong magnetic force: the price regularly returns to them, using them as a support for movement or a barrier to overcome.

The most effective strategy is trading bounces from blue zones. When the price approaches the area of maximum presence, the probability of a reversal is significantly higher than average. This works especially well in sideways markets, where the blue zones clearly define the channel boundaries.

Breakouts through yellow zones often signal continued movement. If the price easily passes through the medium presence area on good volume, it indicates that there is no serious resistance ahead.

Reversal setups are often most effective in red zones.

Combination with volume analysis greatly enhances the signals. When the blue zone coincides in time with high volume in the volume profile, a zone of maximum significance is created.

### 

### Customization for different markets: Versatility through adaptation

Forex with its high liquidity requires large **AnalysisPeriod** (300-500 bars) an

### Conclusion: A new look at old truths

The indicator does not reveal new principles, it makes old ones clearer. Support and resistance levels have always existed, but now they can be measured and ranked by importance. The heat map shows where the market spends time, and therefore where the real strength lies.  
  
Combined with the time gap indicator, this provides a comprehensive picture of the behavior of major participants: where they act quickly and where they linger. Together, these tools allow us to better understand market structure and make decisions based on logic rather than intuition.  
  
 *In the next part, we will discuss how to combine all of this into a single trading system.*

Translated from Russian by MetaQuotes Ltd.   
Original article: <https://www.mql5.com/ru/articles/18661>

**Attached files** |

## Key paras

Forex with its high liquidity requires large **AnalysisPeriod** (300-500 bars) and **MaxHistory** (5000-8000 bars) values. The movements here are smoother, so a greater depth of analysis is needed to identify significant areas.

For stocks, moderate settings tend to work well: **AnalysisPeriod** 200-300 bars, **MaxHistory** 3000-5000 bars. The session structure creates natural pauses that are reflected well in the heat map.

---

# 21876: How to Detect Round-Number Liquidity in MQL5

## Sections

### Conclusion: The Blueprint for Professional S/R Trading

We converted the observation that price reacts to round numbers into a reproducible engineering and trading blueprint. We explained why modulo checks fail and how level significance scales with timeframe. We then introduced ZeroSize as a formal strength based on normalized price and counting trailing zeros in the string representation—to deliver deterministic detection in MQL5.

Practical deliverables include:

- the GetZeroCount function, which reduces floating-point false negatives via SYMBOL\_TRADE\_TICK\_SIZE normalization and DoubleToString;
- configurable filters (minZero and related inputs) mapped to trading styles and timeframes;
- visualization rules for major and minor levels;
- a basic, testable trading framework combining the level, momentum/confirmation, and risk-management rules (buffer, scaling, trailing stops).

This package can be integrated into indicators, alert systems or EAs and validated across symbols and Digits/TickSize configurations. Future work will add multi‑symbol scanning and real‑time alerting, but the current implementation already provides a robust, auditable method to detect and trade institutional liquidity clusters without the floating‑point and formatting pitfalls of naive approaches.

For further study and community interaction:

- Source Code (MQL5): The core implementation logic is provided as an attached file (RoundLevel\_Base.mq5) to this article for educational purposes.
- Future Development: I plan to further enhance this algorithm by integrating multi-symbol scanning and real-time alert systems in future updates.

**Attached files** |

## Key paras

Price often clusters and reverses at whole integers (psychological round-number levels). In practice, this creates operational issues. Some timeframes become cluttered with trivial lines, while on others, strong levels are indistinguishable from noise. Simple modulo tests also fail due to floating‑point artifacts and heterogeneous quote formats (Digits, TickSize) across FX, metals, indices, and crypto.

A basic mathematical modulo operation (price % step == 0) can tell you if a number is round, but not *how* round it is relative to others. To overcome this limitation, I developed an innovative string-parsing logic.

As seen in previous images (Figures 1-3), major and minor forex pairs consistently respect these zones, validating the applicability of the round level indicator for all currency traders.

- High-Value Assets (Bitcoin/Indices): For an asset like BTCUSD trading at 70,000, trailing zeros occur to the left of the decimal point. Our string-parsing logic treats the entire price string as a sequence, correctly identifying 70,000 as a ZeroSize 4 level. - Precious Metals & JPY Pairs: Symbols with 2 or 3 digits (like GOLD or USDJPY) are handled by the DoubleToString(price, \_Digits) function. This ensures that a level like 150.00 is identified with a strength of 2, which is psychologically equivalent to a ZeroSize 4 level on a 5-digit forex pair (e.g., 1.1000). - Floating-Point Artifacts: By normalizing the price to the SYMBOL\_TRADE\_TICK\_SIZE before conversion, we eliminate IEEE-754

As demonstrated in this chart of Gold M1, the price approached the ZeroSize 3 level during a high-volatility session and reacted with a perfect pin-bar rejection, confirming our theory.

We are going to create a matrix forecasting model based on a Markov chain. What are Markov chains, and how can we use a Markov chain for Forex trading?

---

# 15895: Scalping Orderflow for MQL5

## Sections

### Conclusion

Using cutting edge risk management tools, this expert advisor for MetaTrader 5 applies a complex Order Flow scalping approach. It uses a combination of various technical indicators, order flow analysis, and dynamic position size to find high-probability forex trading opportunities. Backtesting the EA on different timeframes for the EURUSD pair, especially on 15-minute and 5-minute intervals, indicates potential.

Still, the outcomes point to both advantages and disadvantages. Despite the strategy's high win rates and modest profitability, it may not be able to produce large returns due to its low profit factor and relatively minor gains over extended testing durations. Due to its propensity for frequent small wins to be offset by bigger, sporadic losses, the method may be susceptible to significant drawdowns in the event of unfavorable market conditions.

\*Remember to save mq5 file in the MQL5/Experters Advisors/    folder (or some where inside)

**Attached files** |

## Key paras

The emphasis on risk management in this EA is one of its main characteristics. Effective risk control is essential in the turbulent world of forex trading, especially when using scalping tactics. In order to safeguard capital and optimize possible returns, this system includes trailing stops, partial position closure methods, and dynamic position sizing.

It's crucial to understand that even though this EA trades automatically, it is not a "set and forget" solution. The basics of forex trading, the ideas behind OrderFlow, and the particular indicators included in this system should all be well understood by users. It is advisable to conduct routine monitoring and make necessary modifications to guarantee that the EA operates at its best under different market circumstances.

Using cutting edge risk management tools, this expert advisor for MetaTrader 5 applies a complex Order Flow scalping approach. It uses a combination of various technical indicators, order flow analysis, and dynamic position size to find high-probability forex trading opportunities. Backtesting the EA on different timeframes for the EURUSD pair, especially on 15-minute and 5-minute intervals, indicates potential.

---

# 20287: Automating Black-Scholes Greeks: Advanced Scalping and Microstructure Trading

## Sections

### **Back Test Results**

The back-testing was evaluated on the symbol 'EU50cash' on the 1H timeframe across roughly a 2-month testing window (14 February 2025 to 11 April 2025), with the following settings:



Now here is the equity curve and the backtest results:





From the results, we can see that the Gamma/Delta automation is functioning correctly as both a microstructure scalper and a hedging engine, generating many small, low-risk profits while keeping risk tightly controlled. The system is ideal for traders who prioritize capital preservation, market-neutral exposure, and steady compounding rather than aggressive profit-chasing.

### Conclusion

In summary, we brought the full automation pipeline of Black-Scholes Greeks into an actionable trading framework, bridging theoretical sensitivity measures with real-time market execution. We implemented fast numerical functions for Delta, Gamma, and time-to-expiry, built a dynamic frequency system driven by Gamma intensity, and developed hedge logic capable of maintaining Delta neutrality while opportunistically exploiting Gamma-scalping conditions. By combining Delta hedging, Gamma-based microstructure signals, expiry-aware logic, and a live on-chart monitoring dashboard, we transformed Greek analytics into a complete automated engine for EU50 and similar instruments.

In conclusion, this automated Greek-driven system offers traders a powerful tool for navigating short-term volatility and microstructure shifts with precision and reduced risk. By continuously recalculating sensitivities, adjusting hedge timing based on Gamma, and executing trades only when statistically justified, the model enables disciplined, data-driven decision-making—far beyond what manual trading can achieve. Whether used for hedging, scalping, or volatility harvesting, this approach empowers traders with institutional-grade risk control and tactical responsiveness.

**Attached files** |

## Key paras

[Overcoming The Limitation of Machine Learning (Part 7): Automatic Strategy Selection](https://www.mql5.com/en/articles/20256)

---

# 8136: Price series discretization, random component and noise

## Sections

### Conclusion

- The nature of the price series is discrete, which stems from the pricing structure.
- A market price is not a function of time, but it is a function of closely related economic processes and currently it is not possible to take them all into account.
- Discretization of a price series into time intervals introduces a significant random component; this distorts the real shape of the price chart, adds noise and non-stationarity to this complex process with unknown parameters.
- It is necessary to take into account the function of which parameter the price is, when developing price series discretization methods.
- The non-stationarity of a price series is formed, among other reasons, due to incorrect discretization parameters.
- Time discretized price charts can be analyzed in an effort to find patterns, but it is necessary to take into account the above aspects, in order to better understand the nature of a particular found pattern.
- The idea is to develop other price series discretization methods which introduce much less distortion in the original data. One of such methods is described in this article.
- Trading algorithms and statistical market studies should be developed taking into account the specific features of the used price series discretization.

Translated from Russian by MetaQuotes Ltd.   
Original article: <https://www.mql5.com/ru/articles/8136>

**Attached files** |

## Key paras

The question can be answered if we know the market price forming mechanism. I will not describe it in detail, as the description is provided in the article "[Principles of Exchange Pricing through the Example of Moscow Exchange's Derivatives Market](https://www.mql5.com/en/articles/1284)". Some participants place orders in the Market Depth, and other participants buy the required amount at the required price. This is what happens when a price chart is formed. The levels are discrete, i.e. it is possible to place an order at a price of 1, 2, 3 and so one, with certain accuracy. The volume set in bids and purchased by buyers is also discrete, because you can buy 1, 2, 3 or more units. Figure 3

I consider the third option most probable, stating that price is a function of redefining benefits. But it is impossible to calculate the benefit of each participant in order to discretize the series. In the first two cases, it is possible to calculate trading and non-trading operations in exchange markets, but there can also be difficulties. For example, an asset can be traded in two or more different exchanges. Or if derivatives of an asset exist, such as futures and options, do we need to calculate the operations which are indirectly connected with the asset? These questions require a separate large study. In any case, all the four cases are indirectly related to each other. The fourth op

1. Take tick volume data of 1-minute candlesticks (from a real account) for the same period and calculate the average number of ticks in a one-minute candlestick - the average number is 59.99 ticks per minute. 2. Load the tick data and find out the average tick size, it is equal to 0.000014378. 3. Calculate the theoretical size of a 1-minute candlestick as (59.99^0.5)\*0.00014378=0.000111363 4. Calculate the theoretical size of a one-hour candlestick as ((59.99\*60)^0.5)\* 0.000014378= 0.00086

Attentive traders may notice that the candlesticks in the market are conventionally divided into groups of "large" and "small" sized candlesticks (areas with high and low volatility), which means that the chart is not a random walk and there are patterns. If time discretization introduced strong distortions, then this effect would not be observed. However, this feature can be explained by the fact that the candlestick size depends on the number of trading operations executed inside this candlestick. How this can be checked? You can simply look at the chart with tick volumes - "small candlestick" periods are accompanied by low tick volumes, and "large candlestick" periods come alongside high 

The simple conclusion of the above analysis suggests that tick data is more suitable for processing and analysis, as they avoid discretization errors in a price series. If we need a larger scale, we will use blocks of 10 or 100 ticks. But the problem is that ticks themselves are also a method of discretization. This method is widely used, but it still can introduce distortions in the process because the price is not a function of received ticks. The price is at least a function of executed trades, while a trade may not always generate a tick. Ticks in an exchange are somehow connected with real trading. But in the Forex market, every company can provide any number of ticks and it is hard to 

Training the CatBoost classifier in Python and exporting the model to mql5, as well as parsing the model parameters and a custom strategy tester. The Python language and the MetaTrader 5 library are used for preparing the data and for training the model.

---

