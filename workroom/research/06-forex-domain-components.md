# 06 — Forex Domain Components: Prior Art for QMF's Level / Trigger / Confirmation Library

Research date: **2026-08-17**. All maintenance states checked on that date unless noted.
Scope: what open-source code exists for the pieces of Mubarak's strategy formula
(`LEVEL + TRIGGER + CONFIRMATION = confluence`, framework owns `EXIT/risk/sizing`),
whether it is good enough to depend on, and what QMF must build itself.

---

## In plain words

1. Mubarak's way of describing a strategy — a **place** on the chart, a **trigger**, a **confirmation** — maps cleanly onto three kinds of software component. Nobody has published a good Python library that does all three well.
2. The one famous package for this style of trading, `smartmoneyconcepts` (order blocks, fair value gaps, break of structure), is popular (1,938 stars) but **has a serious flaw: it peeks at future candles**.
3. That is not our opinion — it is the package's own open bug list. One user measured a backtest "profit factor" falling from **7.32 to 1.82** once the peeking was removed. The fix has been proposed three separate times and is **still not merged**.
4. So: treat that package as a **reference for definitions, not as a dependency**. Read it, copy the ideas, rewrite the code.
5. For **support/resistance, supply & demand zones, liquidity pools** — there is essentially no serious, maintained, correctly-licensed Python library. The good implementations all live in TradingView's Pine Script, which we cannot import. QMF builds these.
6. For **candlestick patterns**, TA-Lib is real, fast, actively maintained, and gives us 61 patterns for free. But academic testing (Marshall, Young & Rose, 2006) found candlestick patterns alone have **no measurable edge** — so they belong in QMF as *confirmations*, never as the whole strategy.
7. For **swing highs/lows** (the backbone of market structure), the honest design rule is: a swing point exists at bar X but you only *know* it at bar X+N. Every QMF component must carry both timestamps. This single rule is what most retail code gets wrong.
8. For the **economic calendar**, there is a genuinely good free option: ForexFactory's own machine-readable feed at `nfs.faireconomy.media` (JSON/XML/CSV/ICS). I fetched it live today and it works. Scraping the ForexFactory *website* directly, by contrast, is blocked (403).
9. Caveat on that feed: it gives **schedule + forecast + previous only — no "actual" value**. So it is perfect for a "don't trade 30 minutes around Red news" filter, and useless for a "trade the surprise" strategy.
10. The professional "economic surprise index" (Citi CESI) is **not obtainable by a retail operator**. A free workalike must be computed by us from actual-vs-forecast data, which needs a paid or semi-paid calendar source.
11. The real **DXY** is ICE's private property. The free substitute is the Fed's broad dollar index on FRED — different basket, daily only, one-day lag. Fine for a slow filter, wrong for an intraday trigger.
12. **Pairs trading / cointegration** on FX: the statistics libraries (`statsmodels`, `arch`) are excellent and maintained. The problem is not code, it is that FX cointegration relationships break down out-of-sample. Treat it as a research capability, not a v1 strategy component.
13. **Overall verdict:** QMF depends on TA-Lib (patterns/indicators), `statsmodels`/`arch` (stats), and the FairEconomy calendar feed. Everything level-shaped and structure-shaped, QMF writes from scratch — maybe 1,500 lines of careful, tested Python.
14. The payoff for writing it ourselves is the thing an LLM strategy-author needs most: **every component honest about when it knew what**, so a backtest cannot lie.

---

## Findings

### 1. The SMC/ICT ecosystem — `smartmoneyconcepts` audited line by line

**Repo:** https://github.com/joshyattridge/smart-money-concepts · PyPI `smartmoneyconcepts`
**State (GitHub API, 2026-08-17):** 1,938 stars, 836 forks, 29 open issues, created 2023-09-21, **last push 2026-04-03**, MIT, not archived. Verdict: *nominally maintained, functionally stalled on its core defect.*

Public surface (`smartmoneyconcepts/smc.py`, 861 lines, classmethods on `smc`):

| Function | Signature | Verdict |
|---|---|---|
| `fvg` | `(ohlc, join_consecutive=False)` | Definition useful; output is lookahead-contaminated |
| `swing_highs_lows` | `(ohlc, swing_length=50)` | **Non-causal. Root of everything downstream.** |
| `bos_choch` | `(ohlc, swing_highs_lows, close_break=True)` | Causal *given* swings, but inherits swing contamination |
| `ob` | `(ohlc, swing_highs_lows, close_mitigation=False)` | Same; also slow (Python loops) |
| `liquidity` | `(ohlc, swing_highs_lows, range_percent=0.01)` | Same; sweep index scans forward |
| `previous_high_low` | `(ohlc, time_frame="1D")` | Cleanest function in the library |
| `sessions` | `(ohlc, session, start_time="", end_time="", time_zone="UTC")` | Row-by-row Python loop; correct but slow |
| `retracements` | `(ohlc, swing_highs_lows)` | Fragile boundary handling (`np.roll` + manual trimming) |

#### 1.1 The lookahead defect (load-bearing)

Verbatim from source, lines 151–163:

```python
swing_length *= 2
swing_highs_lows = np.where(
    ohlc["high"]
    == ohlc["high"].shift(-(swing_length // 2)).rolling(swing_length).max(),
    1,
    np.where(
        ohlc["low"]
        == ohlc["low"].shift(-(swing_length // 2)).rolling(swing_length).min(),
        -1, np.nan,
    ),
)
```

Two facts, both verified against the raw file
(https://raw.githubusercontent.com/joshyattridge/smart-money-concepts/master/smartmoneyconcepts/smc.py):

- **`shift(-(swing_length // 2))` reads bars that have not happened yet.** The value written at row `i` cannot be known until bar `i + swing_length//2` closes. Consuming this column row-by-row in a backtest is textbook lookahead bias.
- **`swing_length *= 2` on line 151 doubles the user's parameter.** Passing `swing_length=50` yields a ±50-bar centred window (100 bars total), i.e. 50 bars of future. Almost nobody reading the docstring ("look back and forward") expects the leak to be that deep.

This is not a subtle claim — it is the repo's own top complaint. Open, unmerged, as of today:

- **#101** (opened 2026-04-01, open): "Look-ahead bias in `swing_highs_lows()` — inflated backtest results". Reporter measured, on XAUUSD M15, ~10 years / 280k bars, **profit factor 7.32 → 1.82** after removing the bias. https://github.com/joshyattridge/smart-money-concepts/issues/101
- **#103** (2026-04-05) and **#108** (2026-05-27): two separate PRs titled "fix look-ahead bias in swing_highs_lows" — both still open.
- **#95** (2025-12-24): PR adding a `causal` parameter — still open. #101 notes it only shifts outputs forward rather than changing the detection window, so it does not actually fix the bias.
- **#34** "Lookahead methods" (2024-05-12) and **#59** "Live trading — swing function uses forward-looking logic" (2024-09-08): the issue has been known for **two years and three months** and is unfixed.

Two more contaminated surfaces found by reading the code:

- `fvg` (lines 72–83) tags the FVG on the **middle** candle `i`, but the condition reads `ohlc["low"].shift(-1)` — so row `i`'s flag is only knowable at `i+1`. Off-by-one leak if consumed naively.
- `fvg`'s `MitigatedIndex` (lines 113–122) is computed by scanning `ohlc["high"][i+2:]` over the **entire remaining series**. It is a full-history artefact: at bar `i` in live trading that column is unknowable. Same pattern in `liquidity` (`c_start = i + 1`, forward `np.argmax`).

#### 1.2 Secondary problems

- **Performance.** `ob()` and `bos_choch()` use Python-level loops with per-swing `np.searchsorted`. Issues **#35** (2024-05-13) and **#48** (2024-06-20) report ~20 s per `ob()` call, making a full backtest run into the ~day range. Issue **#111** (2026-07-10) is an optimisation PR, still open.
- **Index contract.** Functions return positionally-indexed `pd.Series` that must be manually aligned back to the caller's DatetimeIndex — see **#67** "swing high lows does not return index" (2025-01-12) and **#68** "NaN values on most indicators".
- **Non-determinism vs. reference implementations.** **#61** (2024-10-05) and **#76** (2025-03-08) report divergence from TradingView/LuxAlgo SMC. There is no canonical definition of an order block, so "correct" is undefined — a fact QMF must design around, not resolve.
- **DST.** **#46** (2024-06-13) — `sessions()` "daylight savings shifts out of sync".
- **Streaming.** **#93** (2025-11-22) — "Inconsistency in order blocks with incoming candles": outputs are not stable as bars arrive, which is the same disease as the lookahead.

#### 1.3 Forks and alternatives — all worse

Searched forks/derivatives: `SavviBrax/smartmoneyconcepts-py`, `jaydai81/…`, `smtlab/…`, `rafalsza/…`, `DACILAE1777/smart-money-concepts-1`, `Prasad1612/SMC-Screener`, `pypi.org/project/smart-money-concept/`. Every one is a copy or thin wrapper of the same `smc.py`; none has fixed the centred window. Copying a fork copies the bug.

The GitHub topic `order-block` filtered to Python contains **exactly 2 public repositories** (https://github.com/topics/order-block?l=python, checked 2026-08-17). The SMC ecosystem in Python is one file, forked 800 times.

**Verdict: to-rebuild.** Use `smc.py` as an executable specification of the *definitions* (its FVG and BOS/CHoCH conditions are reasonable and match community consensus), and reimplement causally. MIT licence means we may legally copy code; the reason not to is correctness, not law.

#### 1.4 Is SMC/ICT itself evidence-based?

**UNVERIFIED / no primary evidence found.** I searched for peer-reviewed work validating order blocks, fair value gaps, liquidity sweeps, or ICT killzones and found none — only vendor blogs, TradingView scripts, and educational content. Contrast with candlestick patterns, which at least have been formally tested (§4). QMF should therefore expose SMC components as *configurable hypotheses to be measured*, not as blessed primitives.

---

### 2. Market structure: swings, fractals, zigzag

#### 2.1 `jbn/ZigZag` — the one genuinely well-engineered primitive

**Repo:** https://github.com/jbn/ZigZag · BSD-3-Clause · 476 stars · **last push 2024-03-21** · 20 open issues. *Quiet but stable; Cython, tiny surface, no rot risk.*

Read the source (`zigzag/core.pyx`):

```python
def peak_valley_pivots(X, up_thresh, down_thresh)   # down_thresh MUST be negative
cpdef peak_valley_pivots_detailed(double[:] X, up_thresh, down_thresh,
                                  bint limit_to_finalized_segments,
                                  bint use_eager_switching_for_non_final)
cpdef int_t identify_initial_pivot(double[:] X, up_thresh, down_thresh)
def max_drawdown(X) -> float
```

Algorithm: a single forward pass holding `last_pivot_x` / `last_pivot_t`; a pivot is *committed* only when the ratio `x / last_pivot_x` crosses `up_thresh`/`down_thresh`. Two properties matter for QMF:

- **The loop is genuinely online.** Unlike a centred rolling window, this can be driven bar by bar. Its only non-causality is *retro-dating*: the pivot is written back to its historical index once confirmed. That is exactly the `origin_bar` vs `confirmed_at` distinction QMF should formalise.
- **Two documented edge behaviours** (docstring, verbatim): "The first and last elements are guaranteed to be annotated as peak or valley even if the segments formed do not have the necessary relative changes." And `identify_initial_pivot` scans the **whole series** to decide the first pivot's polarity. Both must be stripped in a live adaptation.

Weakness for FX: the threshold is **relative (percentage)**. FX ranges are better expressed in pips or in ATR multiples. QMF wants an ATR-normalised variant.

#### 2.2 Williams fractals and pivots

Trivially causal and trivially cheap: a Williams fractal is a 5-bar (or 2n+1-bar) centred extremum, confirmed n bars later. Deliberately **no library recommendation** — this is ~15 lines and every library that implements it (including `smc.py`) is the one place they leak the future. QMF writes it, and returns `(origin_bar, confirmed_at=origin_bar+n)`.

`scipy.signal.find_peaks` (https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html) is maintained and useful for *research/labelling* (it has `prominence`, `distance`, `width` which are good zone-strength proxies) but is inherently batch/offline. Use it in the research notebook, never in the live path.

#### 2.3 BOS / CHoCH

No credible standalone implementation exists outside `smc.py`. The definition is simple once swings are causal:
- **BOS** = close beyond the most recent swing in the *direction of the prevailing structural trend*.
- **CHoCH** = close beyond the most recent swing *against* it (first structural break of the opposite side).

`smc.py`'s `bos_choch(..., close_break=True)` distinction (break by close vs. by wick) is a genuinely good API idea worth copying verbatim as a QMF parameter.

---

### 3. Levels: S/R, supply & demand, liquidity pools

This is the **weakest part of the entire open-source landscape.**

| Project | State (2026-08-17) | Judgement |
|---|---|---|
| https://github.com/ednunezg/pytrendline | 140★, MIT, **last push 2024-11-13**, 1 open issue | Trendlines (sloped), not horizontal zones. Coherent code, plotting-oriented. Quiet ~21 months. Wrong shape for us. |
| https://github.com/day0market/support_resistance | 468★, **last push 2023-07-06**, 7 open issues, **no LICENSE file** | Agglomerative clustering over zigzag pivots. **Legally unusable — no licence means all rights reserved.** Abandoned 3 years. Read for the idea only. |
| https://github.com/kiruxan/support_resistance | fork of the above | same problem |
| https://github.com/boysugi20/python-stock-support-resistance | script, not a package | k-means + elbow over closes. Demo quality. |

**Supply & demand zones (RBR/DBR/RBD/DBD):** searched thoroughly — **no maintained Python library exists.** Every credible implementation is Pine Script on TradingView (e.g. https://www.tradingview.com/script/5L5seG7y/, https://www.luxalgo.com/library/indicator/rally-base-drop-signals/). Pine is not importable. The upside: the *definition* is mechanical and easy to port —
`leg-in (n consecutive same-direction candles) → base (m candles with small bodies / low range) → leg-out (n consecutive candles)`, zone = the base's high/low band.

**Liquidity pools / sweeps:** only `smc.py::liquidity`, whose approach (cluster swing levels within `range_percent` of total range, then find the first bar that pierces the band) is a reasonable spec — but its sweep detection scans forward from `i+1` over unknown-at-the-time data.

**Verdict: QMF builds all of §3.** Three algorithms, one interface:
1. **Pivot-cluster S/R** — cluster confirmed swing levels (from §2) by ATR-scaled proximity; zone strength = touch count × recency decay × rejection magnitude.
2. **Supply/demand zone** — leg/base/leg pattern scan, causal by construction.
3. **Reference levels** — previous day/week/month H/L, session H/L, round numbers. `smc.py::previous_high_low` is the cleanest function in that repo and is a fine model (resample + `np.searchsorted` + `groupby().cummax()`), but see §6 on which timezone defines "previous day".

---

### 4. Triggers & confirmations

#### 4.1 Candlestick patterns — TA-Lib

**Repo:** https://github.com/TA-Lib/ta-lib-python · 12,188★ · BSD-2-Clause · **last push 2026-07-29** · 137 open issues. **Actively maintained** (packaging modernised 2025, Rust core and streaming API in progress per https://ta-lib.org/). **Use it.**

- **61 `CDL*` pattern functions** (https://ta-lib.github.io/ta-lib-python/funcs.html). Output is an int series: 0 = absent, ±100 = present with direction, ±80 used by some patterns for weaker matches.
- **The trap — global mutable state.** All CDL functions judge "long body", "short shadow", "near", "equal" against thresholds set by `TA_SetCandleSettings(settingType, rangeType, avgPeriod, factor)`. Defaults (https://ta-lib.org/api/candle-settings/):

  | Setting | Range type | avgPeriod | factor |
  |---|---|---|---|
  | BodyLong | RealBody | 10 | 1.0 |
  | BodyVeryLong | RealBody | 10 | 3.0 |
  | BodyShort | RealBody | 10 | 1.0 |
  | BodyDoji | HighLow | 10 | 0.1 |
  | ShadowLong | RealBody | 0 | 1.0 |
  | ShadowVeryLong | RealBody | 0 | 2.0 |
  | ShadowShort | Shadows | 10 | 1.0 |
  | ShadowVeryShort | HighLow | 10 | 0.1 |
  | Near | HighLow | 5 | 0.2 |
  | Far | HighLow | 5 | 0.6 |
  | Equal | HighLow | 5 | 0.05 |

  These are **process-global**. A strategy that tunes `BodyLong` silently changes every other strategy in the same process. QMF must either (a) forbid touching them and pin the defaults, or (b) serialise access and snapshot/restore around each call. Option (a), documented as a constitution rule.

- **Evidential status.** Marshall, Young & Rose, *"Candlestick technical trading strategies: Can they create value for investors?"*, **Journal of Banking & Finance 30(8), 2006, 2303–2323** (https://ideas.repec.org/a/eee/jbfina/v30y2006i8p2303-2323.html) tested candlestick strategies on DJIA components 1992–2002 with a bootstrap that generates random OHLC, and found **no value**. Later work is mixed and market-specific (e.g. Thailand, https://journals.sagepub.com/doi/10.1177/2158244017736799). Nothing establishes an FX edge.
  → **Design consequence:** candlesticks are *confirmations only*, weighted, never a standalone strategy. QMF's defaults must not encourage "CDLENGULFING = buy".

#### 4.2 Indicator libraries — the pandas-ta situation

- **`twopirllc/pandas-ta` is gone.** `GET https://api.github.com/repos/twopirllc/pandas-ta` → **404** (checked 2026-08-17). Repo removed from GitHub and PyPI history wiped (community discussion: https://github.com/xgboosted/pandas-ta-classic/issues/30, salvage fork https://github.com/MerlinR/Pandas-ta-fork). **Do not depend on `pandas-ta`.**
- **`xgboosted/pandas-ta-classic`** — https://github.com/xgboosted/pandas-ta-classic · 419★ · MIT · **last push 2026-07-25**, 4 open issues, CI + Hypothesis property tests, TA-Lib used as a parity *oracle* not a backend. 224 indicators + **62 native-Python candlestick patterns (no TA-Lib needed)**. The community successor. Reasonable *fallback* if TA-Lib's C build proves painful on the Linux VPS.
- **`bukosabino/ta`** — https://github.com/bukosabino/ta · 5,142★ · MIT · last push 2026-03-18 · 156 open issues. Pure pandas, no candlestick patterns, slower. Third choice.

#### 4.3 Session filters

**No usable library.** `exchange_calendars` / `pandas_market_calendars` / `tradinghours` model *exchanges* (open/close/holidays); FX is a continuous 24/5 market with a different shape. `smc.py::sessions()` exists but is a per-row Python loop and carries an open DST bug (#46).

Facts QMF should encode itself, with `zoneinfo` (stdlib) — never fixed UTC offsets:
- Sessions are anchored to **local exchange time**, so their UTC boundaries shift twice a year and asymmetrically (US/EU/UK/AU DST transitions land on different dates).
- Approximate UTC windows in northern-hemisphere winter: Sydney 22:00–07:00, Tokyo 00:00–09:00, London 08:00–17:00, New York 13:00–22:00; London/NY overlap is the liquidity peak.
- "Killzones" (an ICT construct) are sub-windows of these, defined in **America/New_York** local time. Store them as `(tz, start_local, end_local)` triples, resolve to UTC per-day.
- FX week boundary (Sunday open / Friday close) is **broker-specific**, not a market constant. It must be a config value.

#### 4.4 Multi-timeframe confirmation

No library worth adopting. The correct primitive is small and QMF owns it: for each higher timeframe `H`, the value available at low-timeframe bar `t` is the last **closed** `H` bar strictly before `t`. In pandas that is `resample(H, label='left', closed='left').agg(...).shift(1).reindex(index, method='ffill')` — the `.shift(1)` is the whole game and is the #1 place MTF backtests leak. QMF should make this impossible to get wrong by making the resample a framework service, not a strategy-author responsibility.

---

### 5. Cross-pair: correlation, cointegration, DXY

#### 5.1 Statistics libraries — good, maintained, use them

- **`statsmodels`** — Engle–Granger two-step: `statsmodels.tsa.stattools.coint`. Johansen: `statsmodels.tsa.vector_ar.vecm.coint_johansen(endog, det_order, k_ar_diff)` where `det_order ∈ {-1: none, 0: constant, 1: linear trend}`; returns a `JohansenTestResult` with `trace_stat` / `trace_stat_crit_vals` and `max_eig_stat` / `max_eig_stat_crit_vals` (https://www.statsmodels.org/stable/generated/statsmodels.tsa.vector_ar.vecm.coint_johansen.html). Johansen is the right test for FX because it handles >2 series (needed for triangular relationships like EURUSD/GBPUSD/EURGBP).
- **`bashtage/arch`** — `arch.unitroot.cointegration.engle_granger` and Phillips–Ouliaris, with proper ADF critical values for residual-based tests (https://bashtage.github.io/arch/unitroot/cointegration.html). Actively maintained (docs at 8.0.0). Better critical values than rolling your own.

#### 5.2 The FX-specific caveat

The problem is not code, it is **stability**. Lemishko, Landi & Caicedo-Llano, *"Cointegration-Based Strategies in Forex Pairs Trading"* (SSRN 4771108, https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4771108) is the closest FX-specific primary source. The recurring finding across the literature is that pairs cointegrated in-sample frequently lose cointegration out-of-sample, so profitability depends on adaptive re-selection and hard risk limits rather than on the test itself.

**Design consequence:** cointegration belongs in QMF as a **Confirmation / regime filter** with an explicit rolling re-test and an expiry, not as a Level or a Trigger. E.g. "only take the EURUSD setup while EURUSD–GBPUSD z-score |z| < 2 and the pair passed Johansen at 95% within the last 60 days."

#### 5.3 Correlation monitoring

Rolling correlation is `pandas.DataFrame.pct_change().rolling(n).corr()` — no dependency needed. The open-source "currency strength meter" projects found (https://github.com/topics/currency-strength, https://github.com/Valtorim/MT5-Portfolio-Correlation-Matrix, `Spoofkapoof/freox`) are Streamlit/MT5 hobby dashboards, unmaintained-to-beta, MT5-coupled. **Nothing to adopt; the maths is five lines.**

What is genuinely worth building, because it is an *operator safety* feature rather than an indicator: **basket exposure**. Decompose open positions into per-currency net exposure (long EURUSD + long EURGBP = 2× long EUR) and refuse correlated stacking. That belongs in the framework's risk layer, not in a strategy.

#### 5.4 DXY and dollar proxies

- The real **DXY** (`DX-Y.NYB`) is administered by **ICE Data Indices** and is licensed/proprietary (https://developer.ice.com/fixed-income-data-services/catalog/ice-data-indices-currency-indices). Redistributing it, or building a product on scraped values, is a licensing exposure.
- **Free substitute:** FRED `DTWEXBGS` — Nominal Broad U.S. Dollar Index, published by the Federal Reserve Board, **public domain** (https://fred.stlouisfed.org/series/DTWEXBGS). Free API with a free key from https://fred.stlouisfed.org/docs/api/api_key.html.
- **They are not the same instrument.** DXY = 6 developed currencies with weights frozen since 1973. DTWEXBGS = ~26 currencies including EM, trade-weighted, **daily only, published with a one-business-day lag**. Usable as a slow macro regime filter; **unusable** as an intraday confirmation.
- **Practical alternative for intraday:** synthesise a dollar index from the broker's own quotes (geometric mean of USD legs across the majors you already stream from cTrader). Same shape, zero licence risk, tick-by-tick, and consistent with execution prices.

#### 5.5 Economic surprise indices

- **Citi CESI:** requires a Citi Velocity institutional account. Third-party chart views exist (https://en.macromicro.me/charts/45866/global-citi-surprise-index, https://cbonds.com/indexes/99130/) but as charts/Excel add-ins, not as a redistributable programmatic feed for a retail operator. **Not accessible. Treat as unavailable.**
- **Free academic analogue:** the **Scotti surprise index** — Chiara Scotti, *"Surprise and Uncertainty Indexes: Real-Time Aggregation of Real-Activity Macro Surprises"*, Fed IFDP 1093 / *Journal of Monetary Economics* 82 (2016) 1–19 (https://www.federalreserve.gov/econres/ifdp/surprise-and-uncertainty-indexes-real-time-aggregation-of-real-activity-macro-surprises.htm). Daily, for US/EA/UK/CA/JP. **But:** the Fed page states the series is updated and "available from the author upon request or at chiarascotti.com" — i.e. **manual download, not an API.** Suitable for research; not for an automated pipeline.
- **The buildable option:** a surprise index is just `z = (actual − consensus) / σ(historic surprises)` per release, weighted and decayed over a rolling window. QMF can compute this — **but only from a calendar source that publishes `actual`**, which is exactly what the free ForexFactory feed does not (§6.1).

---

### 6. News / economic calendar

#### 6.1 ForexFactory — the site is hostile, the feed is not

**Scraping the website: don't.** `GET https://www.forexfactory.com/robots.txt` with a non-browser User-Agent returned **HTTP 403 Forbidden** (tested 2026-08-17). The site is behind bot protection; every scraper repo (`ehsanrs2/forexfactory-scraper`, `AtaCanYmc/ForexFactoryScrapper`, `fizahkhalid/forex_factory_calendar_news_scraper`, `edofe99/forex-economic-calendar-webscraper`) drives Selenium against a moving DOM. Fragile, and ToS-exposed.

**The machine-readable feed, on the other hand, works and is intended to be consumed.** Fetched live 2026-08-17, all HTTP 200:

| URL | Status | Notes |
|---|---|---|
| `https://nfs.faireconomy.media/ff_calendar_thisweek.json` | 200, 12,960 B | JSON array |
| `https://nfs.faireconomy.media/ff_calendar_thisweek.xml` | 200, 33,835 B | windows-1252, `<weeklyevents>` |
| `https://nfs.faireconomy.media/ff_calendar_thisweek.csv` | 200, 11,826 B | header below |
| `https://nfs.faireconomy.media/ff_calendar_thisweek.ics` | 200, 43,998 B | iCal |
| `…_lastweek.json` / `…_nextweek.json` | **404** | this-week only |

Actual JSON record shape (verbatim from today's fetch):

```json
{"title":"BusinessNZ Services Index","country":"NZD",
 "date":"2026-08-16T18:30:00-04:00","impact":"Low",
 "forecast":"","previous":"50.6"}
```

CSV header (verbatim): `Title,Country,Date,Time,Impact,Forecast,Previous,URL`

Four things follow, and they are decisive:

1. **`impact` ∈ {Low, Medium, High}** and `country` is a **currency code** (NZD, GBP, JPY…), not an ISO country. Perfect for a "block trading around High-impact events for this pair's currencies" filter — QMF's exact need.
2. **There is no `actual` field.** The feed is a *schedule*, not an outcomes dataset. A news-avoidance filter: fully served. A surprise-index or news-trading strategy: **not served.**
3. **This-week only, no history.** QMF must **archive every poll to its own store** from day one; otherwise no historical news filter is backtestable. This is a first-week engineering task, not a later one.
4. **Rate limit.** Community-reported enforcement is a maximum of **2 downloads per 5 minutes across all formats**, with polling on tick/timer resulting in a block, and one download per IP (relevant to a shared VPS) — see the ForexFactory thread https://www.forexfactory.com/thread/1311021-mql45-programmers-this-weekly-news-download-code-solves. *Confidence: medium — community consensus in the vendor's own forum, not a published SLA.* Design for **one fetch per hour**, cached, with backoff.

Legal posture: the feed is served by ForexFactory's own CDN in four machine-readable formats and is the documented mechanism for MetaTrader news indicators, which is strong evidence of intended programmatic use. **UNVERIFIED:** I found no published written terms specifically governing `nfs.faireconomy.media`. Treat as "permitted for personal use at low frequency, attribute the source, never redistribute."

#### 6.2 The rest of the calendar landscape

| Source | State | Verdict |
|---|---|---|
| **`investpy`** (https://github.com/alvarobartt/investpy) | 1,849★, **244 open issues**, last PyPI release **1.0.8 on 2022-01-24**. README: *"investpy is not working fine currently due to some Investing.com changes in their APIs, so please use investiny in the meantime"* | **Dead for calendar use.** Do not adopt. |
| **`investiny`** (https://github.com/alvarobartt/investiny) | 428★, last push 2026-02-28 | Historical prices only — **no economic calendar**. Not a replacement for this purpose. |
| **`ecocal`** (https://github.com/lcsrodriguez/ecocal) | 29★, **last push 2023-12-25**, 4 open issues | **Abandoned.** Investing.com scraper; same fragility class. |
| **`market-calendar-tool`** (https://pypi.org/project/market-calendar-tool/) | MIT, **v0.2.2, 2024-10-28** | Scrapes ForexFactory / MetalsMine / EnergyExch / CryptoCraft into DataFrames. Same fragility as any HTML scraper; its own docs push ToS compliance onto you. Read for reference; prefer the feed. |
| **Trading Economics** (https://docs.tradingeconomics.com/economic_calendar/) | Commercial. `guest:guest` credentials exist with heavily restricted data; real access needs a paid key at developer.tradingeconomics.com | Has `actual`. The realistic paid option if surprise data is wanted. |
| **FMP** (https://site.financialmodelingprep.com/) | Free tier = **250 API requests/day** (https://site.financialmodelingprep.com/faqs) | Has an economics calendar endpoint. **UNVERIFIED** whether it is included on the free tier — their pricing page returns 403 to automated fetch; must be checked by hand in a browser. |
| **Finnhub** (https://finnhub.io/docs/api/economic-calendar) | **UNVERIFIED** — could not confirm whether `/calendar/economic` is free or premium; docs page did not render usable content. Widely reported as premium-gated. Verify manually before designing around it. |
| **OpenBB** (https://docs.openbb.co/platform/reference/economy/calendar) | Providers: **`fmp`, `fred`, `nasdaq`, `tradingeconomics`**. Standard fields include `date, country, category, event, importance, source, currency, unit, consensus, previous, revised, actual` | Useful as a **normalisation schema to copy**, and as an escape hatch if we later buy a provider. Adopting the whole OpenBB dependency tree for one endpoint is not worth it. |
| **FRED releases API** (https://fred.stlouisfed.org/docs/api/fred/releases_dates.html) | Free with a free API key; public domain data | **The most durable source of all** for US releases — official, versioned, never blocked, includes vintages. No forecasts/consensus, so no surprise calculation, but bulletproof for "when does NFP/CPI land". |

---

### 7. Timezone and bar-boundary facts specific to this stack

Verified from cTrader's Open API reference (https://help.ctrader.com/open-api/model-messages/):

- `ProtoOATrendbar.utcTimestampInMinutes` — *"The Unix time in minutes of the bar, equal to the timestamp of the open tick."* Bars from the Open API are **UTC-anchored**, and `ProtoOATickData.timestamp` is Unix ms.
- Available periods: `M1 M2 M3 M4 M5 M10 M15 M30 H1 H4 H12 D1 W1 MN1`. Note there is **no H2, H3, H6, H8** — a strategy config must validate against this enum, not accept arbitrary timeframes.

**Design consequence that will bite otherwise:** most retail brokers' *charts* draw daily candles on **EET (UTC+2/+3, with DST)**, so "yesterday's high" on the trader's screen is a different bar from "yesterday's high" computed from UTC-anchored Open API D1 data. Since Mubarak's levels include previous-day/week highs and lows, **the daily boundary must be an explicit, configurable parameter** (`daily_anchor_tz`, default `"EET"` to match what he sees), not an implicit UTC assumption. A cTrader community thread flags exactly this class of problem — UTC-based brokers fold Monday's early hours into a Sunday candle (https://community.ctrader.com/forum/announcements/993/).

---

## What QMF should copy / avoid

### Copy

1. **The `origin_bar` / `confirmed_at` dual-timestamp contract — this is the framework's single most valuable idea.** Every Level, Trigger and Confirmation emits both: where the feature *sits* on the chart, and the first bar at which it was *knowable*. The backtester reads only `confirmed_at`. Make it structurally impossible to read the other one during simulation (e.g. the simulation-time view object simply does not expose `origin_bar` for filtering). This alone prevents the class of error that inflated a real user's profit factor from 1.82 to 7.32.
2. **`smc.py`'s definitions, not its code.** Specifically worth porting: the FVG three-candle condition; the `close_break: bool` parameter on BOS/CHoCH (break by close vs. wick — a real, load-bearing distinction); the `close_mitigation: bool` parameter on order blocks; the zone-state machine implied by `MitigatedIndex`. MIT licence permits copying; correctness forbids it.
3. **jbn/ZigZag's commit-on-threshold loop** as the shape of every structure detector: single forward pass, mutable "pending" state, commit only on confirmation. Port it to Cython/numba with an **ATR-normalised threshold** instead of a percentage, and delete the "first and last element are always pivots" behaviour and the whole-series `identify_initial_pivot`.
4. **TA-Lib as a hard dependency for indicators and the 61 CDL patterns.** BSD-2, C-fast, actively maintained (last push 2026-07-29), builds fine on a Linux VPS. Wrap it so strategies address patterns by name.
5. **OpenBB's `EconomicCalendar` field set** as QMF's normalised calendar schema (`date, country, category, event, importance, source, currency, unit, consensus, previous, revised, actual`) — even where our v1 source can only fill half the fields. Costs nothing now, saves a migration later.
6. **`statsmodels.tsa.vector_ar.vecm.coint_johansen` and `arch.unitroot.cointegration`** for anything cointegration-shaped. Both maintained. Never hand-roll critical values.
7. **`zoneinfo` (stdlib) + IANA names everywhere.** Sessions and killzones stored as `(tz_name, local_start, local_end)` and resolved per-day. Never a fixed UTC offset, never a hardcoded hour.
8. **Archive the calendar feed on every poll from day one.** The free feed is this-week-only; historical news filtering is only backtestable if we have been saving.

### Avoid

1. **Do not `pip install smartmoneyconcepts`.** Two-year-old unfixed lookahead in the function every other function depends on, three open unmerged fixes, ~20 s/call performance, unstable under streaming bars. Vendoring a fork inherits all of it.
2. **Do not depend on `pandas-ta`** (`twopirllc/pandas-ta` → GitHub 404, PyPI history wiped). If a pandas-native TA layer is ever wanted, `pandas-ta-classic` is the successor — but TA-Lib is the better primary.
3. **Do not build on `investpy` or `ecocal`.** Last investpy release 2022-01-24, README self-declares broken, 244 open issues; ecocal untouched since 2023-12-25.
4. **Do not scrape forexfactory.com HTML.** It 403s automated requests; Selenium scrapers are a permanent maintenance tax and a ToS exposure. Use the `nfs.faireconomy.media` feed at ≤1 fetch/hour with caching and backoff.
5. **Do not copy `day0market/support_resistance`.** No LICENSE file = all rights reserved. Reading it for ideas is fine; copying code is not.
6. **Do not treat `DTWEXBGS` as DXY.** Different basket, daily, T-1 lag. And do not ship licensed ICE DXY values. Synthesise a dollar index from broker quotes for intraday use.
7. **Do not let `TA_SetCandleSettings` be reachable from strategy code.** It is process-global mutable state; one strategy tuning `BodyLong` silently changes every other strategy in the process. Pin the documented defaults and make them read-only.
8. **Do not ship candlestick patterns as standalone triggers with encouraging defaults.** Marshall/Young/Rose (2006) found no value in DJIA; there is no FX evidence either way. They are confirmations with weights.
9. **Do not treat SMC concepts as validated.** No peer-reviewed support was found for order blocks, FVGs, liquidity sweeps or killzones. They ship as measurable hypotheses with mandatory out-of-sample reporting, not as blessed primitives.
10. **Do not let strategy authors do their own `resample()`.** MTF alignment is where backtests leak. The framework owns the higher-timeframe view and hands strategies only closed bars.

### Proposed component taxonomy

Four component kinds, one event contract. Names are proposals; the shapes are the point.

```python
# --- shared spine -------------------------------------------------------
@dataclass(frozen=True)
class Provenance:
    origin_bar:   int          # where the feature sits on the chart
    confirmed_at: int          # first bar at which it was knowable  (>= origin_bar)
    timeframe:    Timeframe    # M1..MN1, validated against cTrader's enum
    symbol:       Symbol
```

**LEVEL — emits `Zone` (a price band with a lifecycle).**

```python
@dataclass(frozen=True)
class Zone:
    provenance: Provenance
    lower: Price; upper: Price          # a band, never a single price
    side: Literal["support", "demand", "resistance", "supply", "neutral"]
    kind: ZoneKind
    strength: float                     # 0..1, comparable across kinds
    state: Literal["fresh","touched","mitigated","broken","expired"]
```

| `ZoneKind` | Source | Build or borrow |
|---|---|---|
| `SwingCluster` | ATR-clustered confirmed swings | **QMF builds** (idea from `day0market`, code ours) |
| `SupplyDemand` | leg-in / base / leg-out scan | **QMF builds** (definition from Pine; no Python prior art) |
| `OrderBlock` | last opposing candle before displacement | **QMF builds** (definition from `smc.py::ob`) |
| `FairValueGap` | 3-candle imbalance | **QMF builds** (definition from `smc.py::fvg`) |
| `LiquidityPool` | equal highs/lows within ATR band | **QMF builds** (definition from `smc.py::liquidity`) |
| `PreviousPeriod` | prev D/W/M high-low; session high-low | **QMF builds**, `daily_anchor_tz` configurable (see §7) |
| `RoundNumber` | 00/50-pip grid | **QMF builds** — trivial |

**TRIGGER — emits `Signal` at a bar close; instantaneous, directional.**

| `TriggerKind` | Source |
|---|---|
| `CandlePattern(name)` | **TA-Lib**, 61 CDL functions, settings pinned |
| `ZoneInteraction(zone, mode)` | **QMF** — touch / reject / sweep-and-reclaim / close-through |
| `StructureBreak(BOS \| CHoCH)` | **QMF**, definition from `smc.py::bos_choch` incl. `close_break` |
| `LiquiditySweep` | **QMF** — pierce a `LiquidityPool` then close back inside |
| `IndicatorCross` | **TA-Lib** |

**CONFIRMATION — a scored predicate evaluated at the trigger bar; never generates entries.**

| `ConfirmationKind` | Source |
|---|---|
| `SessionWindow(tz, start, end)` | **QMF** + `zoneinfo`; killzones as presets |
| `NewsBlackout(impact, currencies, ±minutes)` | **QMF** + archived FairEconomy feed |
| `HigherTimeframeBias(tf, method)` | **QMF** framework-owned MTF view (closed bars only) |
| `VolatilityRegime(ATR percentile)` | **TA-Lib** ATR + QMF percentile logic |
| `MomentumFilter(RSI/ADX/…)` | **TA-Lib** |
| `CorrelationGuard(peer, window, max_ρ)` | **pandas** |
| `CointegrationRegime(peer, z, revalidate_every)` | **statsmodels / arch** |
| `DollarBias(index, lookback)` | **QMF** synthetic USD index (intraday) or **FRED DTWEXBGS** (slow) |
| `EconomicSurprise(currency, window)` | **BLOCKED** — needs an `actual`-bearing calendar source (§8) |

**CONFLUENCE — the composition object an LLM strategy-author actually writes.**

```python
Confluence(
    level         = Level,                 # exactly one
    trigger       = Trigger,               # exactly one
    confirmations = list[Confirmation],    # zero or more, all must pass (or weighted score ≥ θ)
    max_bars_between_level_touch_and_trigger = int,
)
```

**EXIT / SIZING — framework-owned, not author-visible as free-form code.** Author picks from typed policies (fixed-R, ATR-multiple stop, structure-invalidation stop, trailing-to-structure, partial-at-R) and supplies numbers. Position sizing, correlated-basket exposure limits, and daily-loss circuit breakers live entirely in the framework so an LLM cannot bypass them.

---

## Open questions

1. **Operator decision — what is a "level" to Mubarak, concretely?** Which of `SwingCluster`, `SupplyDemand`, `OrderBlock`, `FairValueGap`, `LiquidityPool`, `PreviousPeriod`, `RoundNumber` does he actually watch, and in what priority? Building all seven is ~3× the work of building the three he uses. This should be settled by screen-sharing his charts, not by reading more research.
2. **Operator decision — daily/weekly anchor timezone.** Is "previous day high" the EET broker-chart day he sees, or the UTC day the cTrader API returns? These differ by 2–3 hours and produce different levels. Default proposal: EET, configurable. Needs his confirmation against his own charts.
3. **Operator decision — does he want news *avoidance* only, or news *trading*?** Avoidance is free today (FairEconomy feed, §6.1). Trading the surprise requires `actual` values, which requires a paid source (Trading Economics, or FMP/Finnhub if their free tiers turn out to include it). This is the only place in this document where money is genuinely required.
4. **Verify by hand in a browser:** does the **FMP** free tier (250 req/day) include the economics calendar endpoint, and is **Finnhub**'s `/calendar/economic` free or premium? Both pages defeated automated fetching (403 / empty render). Ten minutes of manual checking closes this.
5. **UNVERIFIED — written terms for `nfs.faireconomy.media`.** No published ToS found governing the feed specifically. The 2-per-5-minutes rate limit is community-reported in ForexFactory's own forum, not a published SLA. Decide the risk posture: my recommendation is 1 fetch/hour with caching, source attribution, no redistribution.
6. **Research — is a causal swing detector's confirmation lag acceptable to his strategies?** A ±5-bar fractal is knowable 5 bars late. On M15 that is 75 minutes. If his entries depend on reacting *at* the swing, the honest framework will feel slower than the (leaky) charts and indicators he is used to. This needs an explicit conversation before it becomes a bug report.
7. **Research — order block definitional variance.** `smc.py` diverges from TradingView/LuxAlgo (issues #61, #76) and there is no canonical definition. QMF must either pick one and document it as *QMF's* definition, or expose the variants as parameters. Recommendation: pick one, name it, version it, and make backtests cite the version.
8. **Research — do we need tick or sub-M1 data for sweep detection?** "Wick pierced the pool then closed back inside" is resolution-dependent; the same bar can be a sweep on M15 and not on M5. Decide the canonical resolution per component and record it in the component's provenance.
9. **Deferred — Scotti surprise index ingestion.** Free and academically grounded, but manual download from chiarascotti.com, not an API. Worth a one-off historical pull for research; not worth automating unless a surprise-driven strategy is actually approved.
10. **Deferred — crypto reuse.** Sessions and the economic calendar are FX-only concepts. Levels, structure, and candlestick components port to crypto unchanged. Worth confirming that the `Confirmation` interface tolerates a no-op session filter rather than assuming one always exists.
