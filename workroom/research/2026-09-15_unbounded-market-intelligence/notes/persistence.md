# Persistence / chop / trend-existence / scaling — MQL5 family notes

**Date:** 2026-09-15  
**Corpus:** `.worktrees/mql5-library/data/mql5-library/md/` only  
**Output:** `extractions/persistence.jsonl` (39 full-reads, all beyond the prior-24 ID set)  
**Authority fence:** `OPERATING_LINE.md` + `06_QMX_AUTHORITY_AND_DATAFLOW.md` — MIS labels Book door + KSA only; no sizing; no playbook switch; SQS = Spread Quality Sensor only.

## Evidence-level key (this file)

| Level | Meaning |
|---|---|
| **A** | Causal/closed-bar (or explicitly train-only future labels) + honest empirics (OOS / walk-forward / ablation / leak-free) and a clear transferable mechanism |
| **B** | Implemented method with real data demos; mechanism clear; validation narrower or single-instrument |
| **C** | Tutorial / wizard / construction; transferable idea but weak validation or mixed placement |
| **D** | Thin conceptual residue |
| **X** | Wrong family after read, or actively misleading if placed in MIS |

Physics-like language (FBM, Hölder, Nile R/S, cascades) is recorded **only** when the article uses it as a persistence/chop/scaling diagnostic — never as a sizing multiplier.

## MIS vs bot (standing cut for this family)

| Goes to **MIS** (undirected) | Stays **bot** / Book |
|---|---|
| Hurst / GHE / local fractal μ / Δα spectrum width | Price vs MA / Z-score / spread entries |
| ADX / ADXR / DI **separation** / ADX slope (existence) | +DI vs −DI, DI crossover side, Extreme Point stops |
| ApEn / Shannon / permutation / ordinal-network complexity | Fade arrows, entropy-of-up-vs-down “signals” |
| Kalman **gain** / innovation variance | Kalman price line crosses |
| EBSW mode / dominant cycle period / MAMA alpha | MAMA/FAMA crosses; cycle fades; **playbook switch EA** |
| Catch22 / DFA–R/S subset (shadow) | Regime-filter EA that still owns entries |
| Half-life as research/eligibility coordinate | HL→volume (Book); live Z entries |

**Do not freeze folklore thresholds as law:** ADX/ADXR 25, H bands 0.4/0.6, ApEn 0.5/1.2, EBSW rails, μ 0.5 — instrument/TF knobs until recalibrated.

## Full-read set (39) — beyond prior 24

Prior-24 excluded: `17737,23286,22940,16830,15223,23482,23016,10715,23454,21003,14203,19944,9804,23355,22938,22939,15748,19290,18867,1575,21235,16752,9231,22772`.

**Leftovers (named):** 2930, 22484, 23488, 22754, 21142 — all full-read.

**Also full-read:** 22553, 15222, 6834, 22438, 22476, 21299, 22519, 22539, 22638, 23171, 21743, 21742, 22220, 22756, 23077, 23351, 23451, 11487, 6351, 17273, 3886, 23112, 23149, 23444, 16085, 18453, 23565, 23657, 16747, 23013, 20173, 5451, 12129, 2118.

Machine records: `extractions/persistence.jsonl`.

---

## Cluster synthesis

### 1. Hurst / long memory / fractal dimension

- **2930 (C):** Classical R/S primer; H>0.5 persist / <0.5 anti / ≈0.5 RW; V-stat cycles + memory depth. Good vocabulary, weak empirics.
- **22553 (A):** Best Hurst *engineering* piece — three estimators, confidence blend, NaN guards, **honest near-null**: NQ M1 H≈0.51 and does **not** predict intraday trend. Mid-band = filter zone. Futures provenance.
- **15222 (C):** Hurst×MA wizard; author doubts vs raw autocorr control → **always ablate**.
- **6834 (B):** Local fractal index μ (min cover area) reacts faster than global H; μ as local chop/trend existence.
- **22484 / 22438 / 22476 / 21299 / 22519 / 22539 (B/C):** Beyond-GARCH MMAR series — partition → H + multifractality score → spectrum fit → MC vs GARCH → MQL5 library → EA. Transfer = **applicability gate** + spectrum width; refuse live MMAR Monte Carlo on MIS path (22539).
- **22638 (B):** Corrected MFDFA **Δα + R²** on 514 NQ sessions — the metric prior 22940 gestured at.
- **23171 (B):** FIGARCH/HARCH — persistence **of volatility** diagnosed via Hurst/GPH; distinct from return-Hurst.
- **23565 / 23657 / 18453 (B/C):** Fractal feature packs for ML (Python→MQL5).

**QMX cut:** shadow `hurst_blend` + confidence + optional `fractal_mu` / `mf_delta_alpha`; never size; recalibrate off NQ before any FX/crypto claim.

### 2. Catch22 / DFA / canonical fingerprints

- **23488 (A):** Standout. Native catch22 (incl. DFA & R/S fluctuation features), pycatch22 parity, **purge/embargo/stride**, train-only terciles, ablation shows orthogonal value for **vol-regime** classification, then honest EA lesson: good features ≠ automatic edge on a mismatched strategy.

**QMX cut:** shadow feature panel (or DFA/entropy subset) for `regime_classifier_v1` research; steal the leak-free methodology even if the full 22 stay offline.

### 3. ADX / trend existence (not direction)

- **22754 (A):** DI crossover fails in range; Wilder ADXR≥25 is folklore; Optuna gate on ADXR × DI period × min DI separation; RF meta-label; walk-forward EURUSD H1. **Sizing by confidence = Book, not MIS.**
- **16085 (C):** Wizard ADX patterns — strip DI side.
- **2118 (C):** Optimize flat vs trend subsets separately — regime-conditional evaluation idea for QMB.

**QMX cut:** `adx`, `adxr`, `adx_rising`, `di_separation` undirected; **do not freeze 25**; +DI/−DI remain bot (same cut as prior 10715).

### 4. L1 trend / breakpoints

- **21142 (B):** Piecewise-linear L1 trend; breakpoints ≈ regime changes; λ = coef·λmax. **Lookahead risk:** batch L1 on a window that includes future bars, plus endpoint repaint as history grows — causal prefix only.

**QMX cut:** causal `l1_breakpoint_rate` / `|slope|` as structure features if ever shadowed; slope sign is bot.

### 5. Entropy / ordinal complexity / efficiency

- **23351 (B):** ApEn on closed-bar log returns as **strategy gate** (high ApEn → abstain). O(N²), N≥100 lore, thresholds unfrozen.
- **23451 (B):** Ordinal pattern transition networks — permutation/ordinal complexity cheaper cousin of TDA persistence entropy (prior 23286).
- **21743 / 21742 (B/C):** Market Shannon entropy indicator vs EA automation — split MIS feature vs bot entries.
- **22220 (B):** Entropy-adaptive volatility.
- **22756 / 23077 (B):** Entropy feature engineering Python→MQL5.
- **11487 (C):** Shannon tutorial then **up-vs-down entropy as side** — anti-pattern for MIS.
- **12129 (B):** Indicator information / MI — feature prune tool, not a regime label.
- **6351 (B):** Fractional differentiation to keep memory while seeking stationarity (AFML-style).

**QMX cut:** prefer ApEn / ordinal complexity / undirected Shannon as gates; ban signed entropy-as-side in snapshot schema.

### 6. Kalman gain as noise/structure

- **17273 (B):** Fixed Q/R Kalman for FX MR; gain/residual split matches prior **23016** adaptive-gain lesson.
- **3886 (C):** Direction prediction framing — weak for MIS.
- **23112 (C):** UKF+CNN wizard — heavy; innovation stats only if anything.

**QMX cut:** standardize `kalman_gain` (already in prior notes); residual = bot.

### 7. Ehlers / cycle vs trend

- **23149 (B):** EhlersDSP library — SuperSmoother, Roofing, EBSW; closed-bar replay.
- **23444 (B):** Dominant cycle + MAMA/FAMA + **regime-switching EA** (trend vs cycle playbooks). Engineering is excellent (Ready(), no iCustom, closed bars). **Playbook switch is exactly what MIS must not do.**

**QMX cut:** `cycle_period`, `ebsw_mode`, maybe `mama_alpha` as coordinates; EA playbooks stay bot/operator.

### 8. Half-life / autocorr controls

- **20173 (B):** OU half-life as basket scoring eliminator; Infinity discard; HL→holding risk; author flags volume use (Book). Same spirit as prior 14203 Chan HL + OOS decay.
- **5451 (C):** Autocorr heatmaps — cheap control feature beside Hurst.

---

## Cross-cutting lookahead risks

1. **Batch fractal / L1 / spectrum / MMAR fits** on a slice that includes bars after decision time.
2. **Train-only constructs** (triple-barrier, tercile edges, HPO gates, ADF-chosen fractional d) leaking into live if not frozen.
3. **Session mixing** (NQ Globex pre/post open) biasing Hurst/MFDFA.
4. **Endpoint repaint** on causal-looking smoothers (L1, some wavelets, IIR without full replay).
5. **Heavy O(N²) ApEn / MFDFA / catch22** on M1 without not_ready / shadow-lane cost class (AD-24).

## Highest-value transferable mechanisms (ranked)

1. **Leak-free feature ablation + catch22 panel** (23488) for shadow regime features.  
2. **Confidence-weighted multi-Hurst + honest null** (22553) — characterization not predictor.  
3. **ADX existence gate with unfrozen thresholds + meta-label secondary** (22754) — strip sizing & DI side.  
4. **ApEn / ordinal complexity as efficiency/chop gates** (23351, 23451).  
5. **Multifractality applicability gate + Δα** (22484, 22638) before any MMAR-like complexity.  
6. **Ehlers mode/period as cycle-vs-trend coordinates** without MIS playbook switch (23149/23444).  
7. **Kalman gain as noise coordinate** (17273 ∪ prior 23016).  
8. **Half-life as eligibility/speed metric** (20173 ∪ prior 14203) — Book/research, not live scalp MIS.

## qmx_overlap (short)

- Prior regime notes already own hierarchical vol/trend/range (17737), persistence-entropy TDA (23286), ADX tutorial (10715), GHE+VRT+HL (14203), adaptive Kalman gain (23016), microstructure six-way (22940).  
- This pass **fills leftovers** and deepens Hurst multi-estimator honesty, catch22, ADX meta-label, ApEn/ordinal, Ehlers mode, MMAR/MFDFA stack, FIGARCH vol-memory, fractal ML features.

## qmx_possible_gap (short list)

1. No governed or shadow **Hurst multi-estimator + confidence**.  
2. No **catch22 / DFA subset** (or leak-free ablation harness) on the MIS training path.  
3. No **calibrated ADX/ADXR gate** with unfrozen thresholds; folklore 25 still informal.  
4. No **ApEn / ordinal-network** chop-efficiency producers.  
5. No **mf_delta_alpha / multifractality_score** applicability gate.  
6. No **Ehlers cycle_period / ebsw_mode** coordinates.  
7. No explicit schema ban on **signed entropy / DI direction / fade arrows / playbook switch / confidence→size** inside MIS.  
8. No **regime-conditional QMB evaluation** slices (2118 idea) wired to snapshot labels.

## What not to do

- Do not treat H, ADX, or ApEn thresholds from articles as universal law.  
- Do not put +DI/−DI, fade arrows, MAMA crosses, or EA playbook switches in the signal snapshot.  
- Do not let MIS size from meta-label confidence or half-life.  
- Do not run MMAR Monte Carlo or full catch22 on the live decision path without a heavy/shadow rung.  
- Do not confuse vol-persistence (FIGARCH) with return-persistence (Hurst) — both useful, different nouns.

## Counts

| Item | N |
|---|---|
| Full-reads this family (beyond prior 24) | **39** |
| Named leftovers covered | **5 / 5** |
| Evidence A | 3 (23488, 22754, 22553) |
| Evidence B | majority method ports / empirics |
| Evidence C | wizards / EA halves / intros |
| Production code written | **0** |
