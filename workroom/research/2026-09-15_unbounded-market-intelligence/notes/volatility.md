# Volatility state and estimators — research notes

Date: 2026-09-15  
Corpus: `.worktrees/mql5-library/data/mql5-library/` (local markdown only)  
Output: `extractions/volatility.jsonl` (37 full-read articles, all outside the prior-set list)

Prior set excluded from this pass:  
`17737,23286,22940,16830,15223,23482,23016,10715,23454,21003,14203,19944,9804,23355,22938,22939,15748,19290,18867,1575,21235,16752,9231,22772`  
(Note: prior already covered **15223 GARCH** and **23454 range-vol / Parkinson–Garman–Klass–Yang–Zhang**. This pass deliberately went to leftover **GJR/EGARCH/FIGARCH** and many non-overlapping estimators.)

QMX constraint (from `OPERATING_LINE.md`): MIS may carry a **vol coordinate**; it **must not size**. Sizing belongs in Book.

---

## 1. What “vol use” means in this corpus

Every claim below is tagged by primary use. Many articles mix roles; the tag is the dominant mechanism.

| Use | Meaning for QMX | Corpus pattern |
| --- | --- | --- |
| **Forecast** | Predict future σ / P(high vol) | GARCH family, MMAR MC, ML extreme-vol classifier, IV |
| **Filter** | Allow/block or re-threshold other logic | ATR/CHV gates, catch22 regime filter, dual-ATR pullback depth, IV/RV ratio context |
| **Sizing (Book)** | Scale lots / risk budget by vol | Inverse-vol MM, multi-pair ATR lots, MMAR CI→lots, entropy risk multipliers |
| **Trigger** | Entry from vol expansion / breakout | Williams range/swing breakouts, ATR breakout, ORB+relative volume |

**Hard rule for QMX:** forecast/filter features may feed MIS labels. Sizing and (usually) triggers do **not** belong in MIS; triggers are bot/Book concerns, optionally *gated* by MIS state.

---

## 2. Estimator families (venue-aware)

### 2.1 Conditional variance / GARCH stack (Francis Dube)

Articles: **20589, 22258, 22714, 23171, 23677** (+ prior 15223).

| Model | Mechanism | Typical venue note |
| --- | --- | --- |
| ARCH/GARCH | Symmetric clustering | FX demos (AUDUSD); general |
| **GJR-GARCH / TARCH** | Sign asymmetry / leverage γ | Equity theory; FX γ often weaker; demo AUDUSD D1 |
| **EGARCH** | log(σ²), free of positivity constraints; γ sign | Equity γ&lt;0; **commodities/gold often γ&gt;0** |
| **FIGARCH / HARCH** | Long memory (hyperbolic or multi-horizon) | Need Hurst/GPH gate before use |
| SLSQP fit | Numeric parity with Python `arch` | Method-general |

**Vol use:** primarily **forecast** (+ z-score spike **filter**). Author demos also tempt risk tools; for QMX keep as state/forecast only.

**Transfer:** asymmetric γ and long-memory d are high-value MIS coordinates if fit is leak-free and optimizer-validated (22714).

### 2.2 Multifractal / MMAR alternative to GARCH (Muhammad Minhas Qamar)

Articles: **22438, 22484, 22476, 21299, 22519, 22521, 22537, 22539**.

- Venue: **EURUSD M5** (FX broker feed via MT5 Python / native MQL5).
- Claim arc: GARCH blind spots → confirm multifractality → H/spectrum → cascade+FBM → **Monte Carlo vol forecast with CI** → EA facade.
- **Vol use:** forecast (+ author proposes CI-based **sizing** in 22539 — Book only).
- Evidence: mixed **B/C**; strongest as a *pipeline*, weakest as a single-pair “MMAR beats GARCH” verdict without large OOS.

### 2.3 Realized / microstructure vol state vector (Max Brown)

Article: **22638** (strongest single article in this family for QMX).

- Venue: **NQ E-mini Nasdaq-100 futures (CME Globex) M1**, NY session, 514 sessions (2024-05→2026-05). Explicitly **not** US100 CFD.
- Bundle: realized vol, duration vol, fractional vol, **FIGARCH-inspired proxy (not fitted FIGARCH)**, clustering index, **GJR leverage ratio**, bipower jump intensity, MFDFA Δα+R².
- Empirical highlights: estimator corr &gt;0.97; mean jump intensity ~1.4%; median Δα ~0.875; **clustering falls in acute stress**; leverage can **invert** in tariff shock.
- **Vol use:** filter / state; article also shows adaptive **sizing** example — treat sizing as Book illustration only.
- Evidence: **A** (tables + clear venue + honest proxy disclaimers).

### 2.4 Range / ATR / Chaikin / swing range

Articles: **10748, 16213, 752, 14775, 19459, 20745, 20862, 16560, 23759, 18111, 22807, 18165**  
(+ prior **23454** for Parkinson / Garman–Klass / Yang–Zhang — not re-extracted here).

| Estimator | Venue notes | Dominant use |
| --- | --- | --- |
| ATR / TR | FX EURUSD educational; multi-symbol sync (752) | filter, trigger, Book geometry/sizing |
| Chaikin Volatility | EURUSD | filter / trigger |
| Session+ATR breakout | session FX/CFD | trigger + Book risk |
| Williams period/swing range | **XAUUSD**/commodities demos | trigger |
| Dual ATR pullback depth | structure systems | filter (depth gate) + Book stops |

Parkinson/GK/YZ remain the OHLC-efficiency complements (prior 23454); this pass’s ATR/CHV/swing pieces are the *trading-system* face of range vol.

### 2.5 Implied vol / VRP / surfaces / indexes

Articles: **23734, 23385, 15841**.

| Source | Venue | Use |
| --- | --- | --- |
| GLD options → 30d IV vs XAUUSD/GLD RV | Gold ETF options proxy, not spot-gold options | regime **filter**/context; Book sizing warning |
| MT5 option chain → 3D IV surface | Broker-dependent equity/FX options | skew/term features |
| FRED CBOE EVZ/GVZ | Euro & gold vol indexes vs MT5 metals/FX | exogenous ML features (**C** evidence) |

**Vol use:** forecast/context/filter. 23734 is careful: not a buy/sell signal; ratio heuristics configurable.

### 2.6 ML / entropy / catch22 regime features

Articles: **16960, 23488, 22220, 20309, 23226, 23676, 20168, 22338**.

- **23488 catch22**: EURUSD; leak-free ablation shows features help **vol-regime classification** but do not auto-improve an unrelated EA — evaluation gold standard (**A**).
- **16960**: high-vol **classifier** (~70% claimed) — treat as **C** until purged OOS.
- **22220**: XAUUSD entropy → four vol states + **sizing** — strip sizing for MIS.
- **23226**: US equity ORB + relative volume — venue-specific filter/trigger.
- **23676**: MAD/Theil-Sen robust scale — better tick-spike resistance than stdev bands (**B**).
- **22338**: inverse-vol money management — pure **Book**.

---

## 3. Role map (article → primary vol use)

| ID | Title cue | Forecast | Filter | Sizing (Book) | Trigger |
| --- | ---: | :---: | :---: | :---: | :---: |
| 20589 | Vol models I | ● | ○ | | |
| 22258 | GJR/TARCH | ● | ● | | ○ |
| 22714 | SLSQP | ● | | | |
| 23171 | FIGARCH/HARCH | ● | ○ | | |
| 23677 | EGARCH | ● | ○ | | |
| 22438–22539 | Beyond GARCH/MMAR | ● | ○ | ● (author) | |
| 22638 | Vol that remembers | ○ | ● | ● (example) | |
| 16960 | Python vol forecast | ● | ● | | |
| 23488 | catch22 regimes | | ● | | ○ |
| 23734 | Gold IV/RV monitor | ○ | ● | ● (advice) | |
| 23385 | IV surface | ○ | ● | | |
| 15841 | EVZ/GVZ | ○ | ● | | |
| 22220 | Entropy adaptive | ○ | ● | ● | ○ |
| 22807 | Pullback depth | | ● | ○ | ○ |
| 10748/16213/752 | ATR family | | ● | ● | ● |
| 14775 | CHV | | ● | | ● |
| 19459/20745/20862 | Vol breakouts | | ○ | ○ | ● |
| 16560 | Vol Navigator | | ○ | ○ (geometry) | |
| 18165/22338 | Risk/MM | | ○ | ● | |
| 23226 | ORB+RVOL | | ● | | ● |
| 23676 | Robust stats | | ● | | |
| 18111 | ATR BE | | | ○ | |
| 20309 | FVI | | ○ | | ● |
| 20168 | Multi-indicator | | ● | | |
| 23759 | ATR channel | | ● | | ○ |

● = primary/secondary explicit; ○ = present but secondary.

---

## 4. QMX MIS implications

### Overlap with current design

- `regime_classifier_v1` classes `quiet|normal|elevated|stressed` are a **vol-state taxonomy** in plain language.
- Closest corpus blueprint: **22638** vol-analysis struct + **23488** leak-free feature test + Dube **asymmetric/long-memory** conditional variance.
- SQS remains **spread** block-only — orthogonal to this family (another agent).

### Must-not-size reminder

Articles that push lot scaling from vol (22338, 18165, 22220, 22539, 23734 sizing section, 22638 example) are **Book patterns**. MIS may emit:

- vol level (RV/ATR/conditional σ)
- vol z-score / percentile
- clustering, leverage γ, jump intensity, Δα / H / d
- IV/RV ratio (metals)

…and must **not** compute lots, risk multipliers, or playbook switches.

### Highest-value gaps for QMX

1. **No fitted conditional-variance producer** (GARCH/GJR/EGARCH) with SLSQP-grade validation and rolling leak-free protocol.  
2. **No microstructure vol bundle** (RV, clustering, leverage, bipower jumps, Δα) as MIS coordinates — 22638 is the template.  
3. **No long-memory gate** (Hurst/GPH) before trusting short-memory features.  
4. **No options/IV path** for gold (23734) — forward vol blind.  
5. **No catch22-class orthogonal features** under purged evaluation (23488).  
6. **Asset-class leverage-sign prior** (EGARCH γ&gt;0 commodities vs γ&lt;0 equities) missing as metadata.

### Explicit non-goals

- Do not revive unauthoritative Kronos/HMM/BOCPD/MS-GARCH as production truth.  
- Do not treat MMAR EA sizing advice as MIS scope.  
- Do not conflate Williams/ORB **triggers** with MIS labels.

---

## 5. Testable hypotheses (priority)

1. Rolling **GJR γ/(α+γ+β)** on liquid FX vs XAUUSD: sign and magnitude differ as EGARCH commodity prior predicts (**23677**, **22258**, **22638**).  
2. **Clustering index** falls in stress while RV rises — replication on QMX symbols (**22638**).  
3. **IV30/RV30** on gold predicts next-week RV expansion better than ATR percentile alone (**23734**).  
4. Adding top **catch22** features to `lightgbm-multiclass` lifts OOS macro-F1 under purge/embargo (**23488**).  
5. When GPH **d&gt;0** on daily r², short-memory ATR understates duration of `elevated|stressed` labels (**23171**).  
6. Robust **MAD** scale vs stdev: fewer false elevated labels on bad-tick sessions (**23676** + feed-state).

---

## 6. Lookahead / leakage watchlist

- Sliding GARCH/MMAR fits that include the forecast bar (22258 claims exclusion — verify).  
- Full-sample Hurst/GPH/multifractal tests used as if known ex ante (23171, Beyond GARCH).  
- ML vol labels from future RV without shift/purge (16960 risk; 23488 shows the fix).  
- Session high/low breakouts using incomplete session (19459, 20745).  
- Unconfirmed swings (20862).  
- FRED vintage/revision alignment (15841).  
- Ex-post macro “stress episode” coloring in 22638 — fine for description, not for training labels without causality rules.

---

## 7. Evidence snapshot

| Level | Count (approx) | Examples |
| --- | ---: | --- |
| A | 3 | 22714 optimizer parity; 22638 NQ study; 23488 leak-free catch22 |
| B | ~18 | Dube series, IV gold monitor, robust stats, ORB equity cite, most MMAR ports |
| C | ~10 | Strategy EAs with backtests, ML accuracy claims, entropy system |
| D | ~6 | Educational ATR/CHV/navigator/FVI without rigorous edge tests |

---

## 8. Article IDs fully read this pass (37)

`752, 10748, 14775, 15841, 16213, 16560, 16960, 18111, 18165, 19459, 20168, 20309, 20589, 20745, 20862, 21299, 22220, 22258, 22338, 22438, 22476, 22484, 22519, 22521, 22537, 22539, 22638, 22714, 22807, 23171, 23226, 23385, 23488, 23676, 23677, 23734, 23759`

Clean working copies used for reading: `recovery_staging/vol_clean/*.txt` (base64 images stripped; originals remain the corpus of record under `md/`).

---

## 9. Bottom line

The local MQL5 library has a **complete modern vol stack** beyond the prior GARCH+range-vol notes: asymmetric GARCH (GJR/TARCH/EGARCH), long-memory (FIGARCH/HARCH), multifractal MC forecasts, futures microstructure vol states, options IV/RV regimes, and leak-free regime-feature methodology.  

For QMX, the actionable center is a **MIS vol coordinate vector** (level + asymmetry + memory + jumps + optional IV), evaluated like 23488, estimated carefully like 22714/22638 — and **never** wired to lot size.
