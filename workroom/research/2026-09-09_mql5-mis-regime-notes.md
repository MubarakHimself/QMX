# MQL5 corpus miner A — regime / volatility / filter method notes (PLAN)

**Date:** 2026-09-09  
**Scope:** Method evidence only, from the local MQL5 library. PLAN notes for QMX **MIS** scalping context (compute-once snapshot). No implementation, no `docs/` edits, no git commit, no Book/BMS redesign.  
**Do not hit mql5.com.** Evidence is on-disk markdown, not the origin. Vendor articles are method evidence, not an MT5/platform commitment. No futures execution as a QMX product.

**Complement:** miner B (`2026-09-09_mql5-mis-scalp-notes.md`) owns spread, news windows, DOM/tick, London-box execution. This file owns **regime, vol, chop/trend filters**. Overlap called out where it exists.

---

## QMX ownership (this brief)

Ratified seam, not an imagined intelligence bus:

- **MIS V1** is a compute-once, versioned, immutable per-instant **signal snapshot**. Closed consumers = **Book door and KSA only**. Bots never consume it (DEC-0204).
- **SQS** = **Spread Quality Sensor** (DEC-0074 / DEC-0153). Score = historical session-window spread ÷ live spread. Block-only. Reaches the door **only inside the snapshot**. Do **not** dump ATR/ADX/HMM/GARCH into SQS. Do **not** treat session ranges as SQS “blocks.”
- **Book door** uses the snapshot for admission / freshness / (later) class activation. **KSA** uses it as a sensor, never as an authority.
- **Bot confluence** (CT-34 legs: level | trigger | confirmation | filter) is declared bot logic. Direction, fade arrows, MA crosses, swing structure stay here.
- Catalog already names `regime_classifier_v1` with **no ratified family** (GAP-0051 / Epic 30). Recovered names Kronos / HMM / BOCPD / MS-GARCH have **no authority** until a sitting. This file is sitting fuel, not a binding.

**Empirical status:** all rows untested in QMX. Source backtests are not certificates. A vendor EA that *identifies a regime then switches playbooks or sizes* is a source claim; QMX forbids the second half inside MIS.

**Placement legend**

| Bucket | Put it here if… |
|---|---|
| **MIS snapshot** | Deterministic (or later shadowed-trained) label a door/KSA can use without direction: trend/range/vol, chop, change-point *probability*, vol estimate, session *id*. Heavy-by-default until a live-path rung baseline (AD-24). Cannot-bound ⇒ `not_ready`. |
| **SQS** | Live spread vs own session-window baseline only. Session *id* may **condition the SQS baseline**, not replace SQS. |
| **Bot confluence** | Anything that says *which way* or *enter here*: DI+/DI−, fade arrows, Kalman price line, LW breakout levels, session-range **breakout alerts**. |

---

## Corpus inventory

- Coverage: `C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/coverage.md` — cataloged 3315, fetched ok 3057, failed 258 (Firecrawl 401/402).
- Index: `.../index.sqlite` table `articles`.
- Title/tag keyword sweep (regime, HMM, GARCH, Kalman, ADX, ATR, chop, Hurst, entropy, session, filter, vol, Markov, wavelet, …): **483** ok-title hits.
- **Read fully (12).** Cap honoured.

**Read fully:** 17737, 23286, 22940, 16830, 15223, 23482, 23016, 10715, 23454, 21003, 14203, 19944.

**Not fully read (high-signal leftovers for a later pass):** 15033 HMM integration primer; 17781 regime EA (Part 2 — *bot* half of 17737); 15541 Nash+HMM filter; 22258 / 23677 GJR/EGARCH; 22484 fractal dimension; 23488 Catch22 on vol regimes; 22754 ADX meta-labeling; 16213 ATR wizard; 3395 / 20037 time filters; 21142 L1 trend filter; 752 multi-symbol vol; 23444 MAMA regime-switch EA. No dedicated “choppiness index” title in the catalog.

---

## Brief table

Paths under `C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/`.

| path | 1-line method | scalper would use it for | transfer caveat (FX MT5 → QMX crypto-spot later) | MIS vs SQS vs bot confluence |
|---|---|---|---|---|
| `md/17737.md` Custom Market Regime Detection (Part 1 Indicator), Bagdi, 2025-04-21 | Hierarchical 3-way regime: **vol first** (latest σ vs 20-bar mean × 1.5) then **trend** (\|autocorr/slope\| > 0.2) else **range**. Lookback ≥ 20 (default 100). Enum: UNDEFINED / TRENDING_UP / TRENDING_DOWN / RANGING / (volatile). | Chop vs trend vs “don’t even look” chaos **before** a scalp setup. Volatile beats trend so trend-followers sit out news/spike. | Thresholds 0.2 / 1.5 are researcher knobs on FX bars, not laws. Direction (up/down) is extra; crypto 24/7 vol clusters differently than FX session bars. | **MIS:** `regime ∈ {trend, range, volatile}` + `trend_strength` + `vol_ratio` **without direction**. **Not SQS.** **Bot:** up vs down, and the Part 2 EA playbook switch (`md/17781.md`, not fully read). |
| `md/23286.md` Persistence Entropy as a Market Regime Indicator, Dilber, 2026-07-15 | Sliding-window TDA: persistence entropy H0/H1 + **loop-strength** percentile band → REGIME_LOW/MID/HIGH. Fade arrows = local z-score extreme **and** REGIME_HIGH. Closed bars only; cube-cost so they grid-step the heavy Compute. | **Chop/range fingerprint** (loops → HIGH → fade-at-edges). Trend = elongated cloud, sparse marks. Volatile = H0 up, loop-strength spikes/collapses (no clean structure). | TDA on N closes is heavy (AD-24: refuse a “light” claim). Crypto tick-noise will inflate H0. Fade arrows are a mean-reversion **trigger**, not a door label. Warm-up = rank lookback × step. | **MIS:** H0, H1, loop-strength, `regime_band` (LOW/MID/HIGH) + `not_ready` until warm. **Not SQS.** **Bot confluence:** +1/−1 fade signal, hysteresis latch. |
| `md/22940.md` Microstructure Part 7 Regime Classification, Brown, 2026-07-01 | Priority **rule set** (not ML) over Parts 2–6 metrics → six labels: Normal, Stressed, Noisy, Informed, Trending, Mean-Reverting + confidence. Stressed first, Normal residual. Composite score is **signed** for Trending/Informed/MR only. | Door-level: **Stressed/Noisy → refuse scalp**; Trending vs MR as class activation. Author: not a direction predictor for Stressed (zero directional signal). | **NQ M1 futures**, 514 NY sessions, in-sample percentiles. VPIN/Roll/MFDFA inherit M1 aggregation error. **Not a QMX product path.** Recalibrate per instrument; OOS unvalidated in the article. | **MIS (shadow only):** discrete `micro_regime` + confidence, **drop the signed composite** (direction). Provenance must say `NQ_M1`. **Not SQS.** **Bot:** Informed/Trending sign if ever examined as confluence — not MIS. |
| `md/16830.md` HMM for Trend-Following Vol Prediction, 2025-01-16 | 2-state HMM on **50-bar return σ**, Viterbi current state, used as a **filter on an MA-cross backbone**. Train Python → paste matrices into MQL5. | Filter trend-scalps when the hidden state is the “wrong” vol regime; author reports ~70% trades dropped, IS PF 1.73 vs 1.48 on XAUUSD H1. | Author’s own caveat: observations (rolling σ) **are correlated with the states**, so a dumb σ threshold might have done the same. Markov memoryless. Matrices freeze-and-ship (good for QMX) but FX H1 ≠ crypto M1. Rolling 2004– OOS PF 1.10 is weak. | **MIS / `regime_classifier_v1` candidate (shadow, GAP-0051):** 2-state vol HMM posterior or MAP state. **Not SQS.** **Bot:** the MA-cross. Do not let MIS size. |
| `md/15223.md` Econometric tools: GARCH, Chernish, 2025-01-06 | Parametric **GARCH(1,1)** (ω, α, β; optional t-ν) via ALGLIB MinBLEIC MLE; σ²_t is itself stochastic. Contrasts with nonparametric rolling σ. | One-step **conditional vol** for “is this bar’s move large vs *today’s* σ, not vs a 20-bar SMA.” Scalp: size-of-move context, not a trigger. | In-slice MLE is **heavy** and can fail to converge → must publish `not_ready`, never a stale σ. Crypto has jumps GARCH(1,1) misses (GJR/EGARCH leftover). No mean model in this article. | **MIS:** fitted `garch_sigma` / `garch_params` as a **fitted** labeler (like `liquidity_stress_v1`), not V1 rule-based. Freeze params offline. **Not SQS.** **Not bot.** |
| `md/23482.md` BOCPD: one regime-break, three uses, Qamar, 2026-08-04 | Adams–MacKay **online** change-point: run-length posterior, Normal-Gamma on log returns. Output = P(break) + E[run length]. Three uses: monitor, self-resetting MA, **risk cooldown**. | Scalper: “the tape’s character just broke — **do not fire** for N bars.” Not which way. Overlay cut DD ~12% by skipping 4/97 trades vs a random-timed control that *worsened* DD. All three modes still lost (placeholder MA). | Detects sharp vol jumps fast; slow mean shifts lag. `lambda` (mean regime length) is a prior — M30 FX default ≠ crypto M1. Few-trade overlay. Causal and cheap once warmed — rare “light” candidate after a rung baseline. | **MIS:** `cp_prob`, `run_length`, `bocpd_status` (incl. not-ready). Natural KSA/Book **sensor** (“assumptions just died”). **Not SQS.** **Bot:** adaptive MA flush. Book (not MIS, not bot) owns de-risk cooldown policy. |
| `md/23016.md` Adaptive Kalman price smoother, 2026-06-22 | Scalar random-walk Kalman; **Q** = rolling return variance, **R** = rolling price variance; gain K_t ∈ [0,1]. EMA is the degenerate constant-K case. | **K_t high** = trust tape (trend/vol); **K_t low** = trust model (chop/noise). Smoothed *price* is a trigger line, not a door label. EURUSD H1: ~25% MAE/RMSE vs EMA(20), ~57% less lag. | Single-state RW ignores drift/autocorr (author). Crypto microstructure noise inflates R and can pin K. Warm-up max(W_Q, W_R)+1. | **MIS:** `kalman_gain` as noise/vol coordinate. **Not SQS.** **Bot confluence:** Kalman price vs close (cross/deviation). |
| `md/10715.md` Design a trading system by ADX, 2022-04-29 | Classic Wilder ADX: trend *existence* not direction. Simple systems: ADX>25 and rising → with-trend via +DI/−DI; ADX<25 path sketched as non-trend. | The only part a scalper needs as **context**: ADX as **chop filter** (low ADX → don’t trend-scalp). 25 is folklore, not measured here. | Tick-evaluated EA in the article (bad for QMX; bar-close only). ADX 14 / 25 calibrated on FX daily lore; crypto M1 will sit in different numeric ranges. +DI/−DI is direction. | **MIS:** `adx`, `adx_rising`, maybe `adx_bin {low, mid, high}` with **unfrozen** threshold. **Not SQS.** **Bot:** +DI vs −DI as confluence, never as MIS. |
| `md/23454.md` Range-based vol estimators, Gbadebo, 2026-08-05 | Four σ estimators on OHLC: close-to-close, Parkinson, Garman–Klass, **Yang–Zhang** (overnight + OC + Rogers–Satchell). YZ bands widen on the gap bar; BB lag. | Replace “ATR or close σ” as the **vol feature** behind regime/size-context. Author: use as vol-regime filter or scale by 1/σ (the latter is Book, not MIS). | **Spot FX near-continuous:** GK ≈ YZ. **Crypto 24/7:** “overnight” is a bar-boundary artifact, not a session gap — do not blindly annualize ×√252. Feed **closed** bars only. Zero/malformed OHLC → NaN guard. | **MIS:** `vol_park`, `vol_gk`, `vol_yz` (pick one per venue class). **Not SQS.** Book may later consume σ for R-distance; MIS does not size. |
| `md/21003.md` LW: vol + structure + time filters, Maroa, 2026-01-28 | Structure first (3-bar swing), then LW range projection (prev-bar range **or** swing range), optional **DOW / time-of-day** filter. Multipliers default 0.50. Gold EA. | Order of logic: **structure → vol threshold → clock**. Time filter as a coordinate, not a trigger. Range-projection entries are the scalp mechanic. | “Yesterday/3-days-ago” is **daily** LW language on whatever TF the EA is attached to — do not treat M1 bars as “days.” Gold vs crypto. Time-of-day is broker-server. | **MIS:** `tod_bucket`, `dow`, `working_range` (vol coordinate). **Not SQS.** **Bot:** swing detection + buy/sell projection levels. Book owns time-window admission if we ever map TOD to a door. |
| `md/14203.md` Generalized Hurst + Variance Ratio, Dube, 2024-02-08 | GHE (moment-q Hurst) + Lo–MacKinlay **VRT** + Chan **half-life**. Used to pick a **mean-reversion symbol**; Z-score EA then OOS-failed because “the market is in continuous flux.” | **Persistence vs MR diagnostic** for class activation (trend-scalp vs fade-scalp), not a live trigger. Half-life ≈ Z-score period in-sample — then decayed. | GHE window too long for M1 scalp unless computed as a slow coordinate. Crypto has different scaling than FX majors. Author’s OOS failure is the transfer lesson. | **MIS:** `ghe`, `vrt_stat`, `hl_bars` as slow features (or shadow). **Not SQS.** **Bot:** Z-score mean-reversion itself. |
| `md/19944.md` Tracking Forex Sessions and Breakouts, Benjamin, 2025-10-27 | Broker-time Asia / Tokyo / London / NY boxes; session OHLC labels; **alert when price breaks prior session extreme**. UI EA, not a model. | Session as a **coordinate** + prior-session range as a level. Overlaps miner B `md/18867.md` (London box) and `md/1575.md` (Asia myth). | FX session mythology. Crypto is 24/7; “London” is a liquidity cluster, not an exchange open. Broker TZ/DST. Breakout *alert* ≠ edge (miner B already falsified naive Asia continuation). | **MIS:** `session_id`, `session_ohlc`, `in_overlap`. **SQS baseline** may *key off* `session_id`. Prior-session H/L is a **level** (bot confluence / structure), **not SQS**. Breakout alert = **bot**. |

---

## Per-article notes (evidence)

### 1. `md/17737.md` — hierarchical vol/trend/range

Three regimes as statistical objects: trending (positive autocorr, shallow pullbacks), ranging (negative autocorr / mean-reversion), volatile (high σ, unclear direction). Author argument that MA/MACD/RSI/BB do not *classify* regimes is the scalper-context claim.

Classifier is **hierarchical**: latest volatility vs average volatility over past 20 bars × `m_volatilityThreshold` (default **1.5**) → volatile; else `|trend strength| > m_trendThreshold` (default **0.2**) → TRENDING_UP/DOWN from priceChange sign; else RANGING. Lookback clamped to ≥ 20.

**QMX cut:** emit `{volatile, trend, range}` + the two raw scores. Drop UP/DOWN from the snapshot (direction is bot). Volatile-first is the useful door rule (trend systems die in chaos). Part 2 EA (`md/17781.md`) is the forbidden “switch strategy from MIS” pattern.

### 2. `md/23286.md` — persistence entropy / loop-strength (chop)

H = −∑ p_i log p_i on persistence-bar lengths. Low entropy = one dominant bar (clean structure); high = many similar lengths. Loop-strength percentile band → LOW/MID/HIGH. Trend: few loops, H1 low, marks sparse. Range: loops, REGIME_HIGH, fade marks at edges. Volatile: H0 climbs, loop-strength unstable.

Signal layer (bot): z-score extreme **and** REGIME_HIGH, closed bars only, hysteresis latch. Cost: full TDA per window; they recompute every `InpStep` (5–20) bars and keep z-score every bar.

**QMX cut:** MIS may carry the band + entropies if a heavy labeler is accepted; fade arrows stay bot. Until a rung baseline, this is shadow-lane material (too expensive to pretend light).

### 3. `md/22940.md` — six-way microstructure regime (futures evidence)

Priority: Stressed → … → Normal residual (~50% of 514 NQ M1 NY sessions). Stressed: flow_confidence=0 (jump) **or** realized vol > P90 **or** (vol>P75 and …). Noisy: high noise + low flow confidence. Informed: high VPIN + low noise + clustering + flow. Trending: high clustering + narrow multifractal width. Mean-Reverting: ARFIMA d < P25 and low clustering.

Author limitations (quote the design, don’t launder them): thresholds are **in-sample percentiles on one instrument**; priority order is a **design choice** (conservative: Stressed first); **not OOS-validated** in the article; M1 Roll/VPIN are approximations.

**QMX cut:** keep as **method evidence** that a **rule-based** classifier (not a neural net) is how you reduce many metrics to one door label. Do not import NQ percentiles. Do not ship VPIN-OHLC as PIN. Signed composite score is direction — strip it from MIS.

### 4. `md/16830.md` — 2-state vol HMM as a filter

States {high vol, low vol} on 50-candle return σ; Gaussian emissions; Viterbi over last 50; freeze transition/emission matrices from a Python train. Backbone = dual MA trend-follow. XAUUSD H1: HMM filter dropped ~70% of trades, PF 1.73 vs 1.48; longer rolling walk-forward PF **1.10**.

Author limitation worth keeping verbatim in any sitting: the 50-period rolling σ observations and the high/low-vol hidden states are **somewhat correlated**, “leading to reduced prediction significance. This suggests that similar results might have been achieved by simply using the observation data as filters.” Also Markov memoryless; more states overfit.

**QMX cut:** if Epic 30 wants an HMM, it is a **vol-state** labeler (MAP state + posterior), freeze-and-ship, shadow first. Always ablate vs the raw rolling-σ threshold (author already suspects redundancy). Never a bot consumer.

### 5. `md/15223.md` — GARCH(1,1) as parametric vol

Nonparametric vol = rolling sample σ. GARCH: σ²_t = ω + α ε²_{t−1} + β σ²_{t−1}, ω>0, α,β≥0, α+β<1. MLE Gaussian or Student-t. Implementation = ALGLIB box-constrained optimizer.

**QMX cut:** a **fitted** producer, same family as `liquidity_stress_v1`, not a V1 rule-based labeler. Offline fit, fingerprint params, on-path only evaluate the recurrence. Failure to fit ⇒ `not_ready`. Leftover GJR/EGARCH articles exist if leverage/jumps matter for crypto.

### 6. `md/23482.md` — BOCPD (best “door sensor” in this set)

Online, causal, probabilistic: P(change-point now) and expected run length. Hazard H = 1/λ. Detects **mean or variance** breaks. Three uses:

1. Monitor (not a trade).
2. Flush a moving average on break (bot smoother).
3. Risk meta-layer: cooldown de-risk after break; **random-frequency control** to prove it isn’t just “trade less.”

Limitations the author states: sharp vol jumps yes, subtle mean shifts lag; overlay result rests on a **handful** of skips; **not direction**; λ and Normal-Gamma prior are inputs.

**QMX cut:** this is the cleanest recovered family already named in DEC-0262. Put `cp_prob` / `run_length` on the snapshot for Book/KSA. Cooldown **policy** (skip entries N bars) is Book, not MIS, not bot. Adaptive MA is bot confluence if a bot declares it.

### 7. `md/23016.md` — Kalman gain as chop/trend coordinate

K_t → 1: process noise dominates (volatile/trending, chase the measurement). K_t → 0: measurement noise dominates (chop, hold the state). Q from return variance, R from price variance, floors 1e−10.

**QMX cut:** snapshot `kalman_gain` (and maybe Q, R). Do not snapshot the smoothed price as a MIS level. Author already flags 2-state kinematic / IMM as the regime-switching extension — that would compete with HMM/BOCPD; don’t stack all three in V1.

### 8. `md/10715.md` — ADX as existence-of-trend filter

ADX rising = trend energy regardless of side. Folklore gate **ADX > 25** plus +DI/−DI for direction. Sideways defined as “not up and not down.”

**QMX cut:** MIS gets the scalar and a rising flag. The number 25 stays experiment-generated, not source-law. Directional DI cross is bot. This is the cheap, rule-based baseline any fancy regime model must **beat in ablation**.

### 9. `md/23454.md` — range-based σ (better than close σ / cousin of ATR)

Efficiency vs close-to-close: Parkinson ~5×, Garman–Klass ~7–8×, Yang–Zhang gap-robust. Author default: **YZ on gapped sessions; GK (or YZ, they coincide) on near-continuous FX.** Crypto-spot later is closer to the FX continuous case **if** bars have no artificial daily open; still do not annualize with 252. Closed-bar only.

**QMX cut:** one vol estimator per instrument class in the snapshot. This is the vol *input* to 17737-style ratios and to SQS-adjacent cost context (spread vs vol), but it is **not SQS**.

### 10. `md/21003.md` — structure, then vol, then time

Useful as a **role-binding** example: 3-bar swing = location/trigger (bot); working range = vol coordinate (MIS); DOW/TOD = filter coordinate (MIS or Book window). Default range multipliers 0.50 are researcher knobs. Gold EA — preserve asset class.

### 11. `md/14203.md` — Hurst / VRT / half-life

GHE as a scaling diagnostic; VRT as a statistical check; Chan half-life as an MR time-scale. Symbol-picker script → USDCHF looked best → Z-score EA optimized in-sample → **OOS failed** (“market is in continuous flux”). That failure is the MIS lesson: a Hurst label must be **continuously refreshed** (or marked stale), not a once-per-year symbol attribute.

No dedicated choppiness-index article showed up in titles; GHE + 23286 loop-strength + ADX-low are the chop cluster.

### 12. `md/19944.md` — session coordinate (weak vs miner B)

Asia/Tokyo/London/NY rectangles, session OHLC, prior-session breakout alerts, broker time. Overlaps miner B 18867/1575. Keep only: **named session_id as a coordinate** that (a) keys SQS baselines, (b) attaches to regime rules. Crypto-spot: replace with **liquidity-hour buckets** (UTC), not FX city names. Protection windows (`session_handover_buffer`) are CT-31, **absent for 24/7**, not MIS.

---

## MIS candidate primitives (labels only)

Coordinates attach to rules; none of these is a trigger.

| Primitive (working name) | Family | Eligible MIS role | Inputs | Do not |
|---|---|---|---|---|
| `regime_3way` {trend, range, volatile} | regime | filter / class-activation feature | returns, σ ratio, autocorr | emit up/down; let bots read it |
| `adx` / `adx_rising` | trend strength | filter | OHLC, Wilder 14 (unfrozen) | freeze 25 as law; put +DI/−DI here |
| `loop_strength_band` {low, mid, high} | chop / TDA | filter | window of closes (heavy) | fade arrows; claim light |
| `cp_prob` / `run_length` | change-point | filter, continuous; KSA sensor | log returns, λ prior | treat spike as a side; size from it |
| `vol_yz` or `vol_gk` | volatility | filter / cost context | closed OHLC | annualize 252 on M1 crypto; feed forming bar |
| `garch_sigma` | volatility (fitted) | filter | frozen (ω,α,β) + last ε,σ | MLE on the live slice |
| `hmm_vol_state` {low, high} | regime (trained, shadow) | filter | frozen matrices + rolling σ | skip ablation vs raw σ |
| `kalman_gain` | noise vs structure | filter | close, W_Q, W_R | snapshot smoothed price as a level |
| `ghe` / `vrt` / `hl_bars` | persistence | slow filter | returns, lags | treat as a static symbol property |
| `session_id` / `tod_bucket` | session coordinate | filter; **keys SQS baseline** | TZ-explicit clock | `Hour()` as London; SQS←range box |
| `micro_regime` 6-way | microstructure regime | shadow only | Parts 2–6 proxies | import NQ percentiles; VPIN as PIN |

**SQS stays SQS:** live spread vs fingerprinted session-window baseline. Vol/regime labels may sit **beside** SQS on the same snapshot; they do not enter the SQS formula.

**Book-only (not designed here):** door on `volatile` / `stressed` / `cp_prob>θ` / low ADX for trend books; cooldown after BOCPD; R-distance from `vol_*`. Do not redesign Book/BMS in this file.

**Bot-only:** DI direction, fade ±1, Kalman line, LW projections, session-breakout alerts, MA-cross backbone, Part 2 “switch EA.”

**Ablation order if Epic 30 sits:** (1) ADX-low vs 17737 3-way vs raw σ-ratio, (2) add BOCPD `cp_prob` as a **break sensor** not a class, (3) only then shadow HMM/GARCH/TDA. Two indicators encoding the same vol will fail incremental-value.

---

## Transfer rules (Forex now, crypto-spot later)

1. Preserve source asset class on every row. NQ Globex M1 (22940) and XAUUSD H1 (16830) are not BTC-USDT M1.
2. No futures execution product: 22940 is **method** (rule-based reduction of many metrics → one label), not a venue to copy.
3. FX sessions ≠ crypto 24/7. `session_id` must be a named calendar identity; CT-31 handover buffers are **absent** on 24/7. SQS still needs a conditioning window — define crypto buckets in UTC, don’t reuse “London.”
4. Gap-robust vol (Yang–Zhang) matters when bars have a real close-to-open; on 24/7 it collapses toward Garman–Klass. Author says so for “intraday forex or any near-continuous market.”
5. Trained/fitted labelers (HMM, GARCH, `regime_classifier_v1`): freeze-and-ship, shadow `shadow_composition_fp`, never on-path retrain, never bot-consumed (GAP-0051).
6. Heavy TDA / in-slice MLE start **heavy-by-default**. Prefer BOCPD + ADX + range-σ as the cheap cluster.
7. Direction never belongs on the snapshot. If a source emits a signed score (22940 composite, 10715 DI, 23286 fade), split: unsigned regime/vol → MIS; sign → bot or drop.

---

## Sitting questions (not answers)

1. Is `regime_classifier_v1` a **3-way rule-based** labeler (17737) with ADX/σ ablation, or a **trained** HMM/BOCPD family? Recovered names are unauthorized until this is answered.
2. Does Book want a **hard refuse** on `volatile`/`cp_prob` (door) or only a sensor for KSA?
3. Crypto-first: drop FX session features from the V1 snapshot schema, keep `tod_bucket` optional?
4. One vol estimator per class (GK vs YZ) as a registry choice, not four parallel fields.

---

## Sources (local corpus)

All claims above are from the twelve `md/*.md` files named in the table, plus `coverage.md` / `index.sqlite` inventory, plus ratified QMX law already in `docs/` (DEC-0204, DEC-0153, DEC-0074, GAP-0051). No mql5.com fetch this pass.
