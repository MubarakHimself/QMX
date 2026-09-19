# Regime / market-state research notes (2026-09-15)

**Family:** regime detection · market state · trend / range / chop / volatile classification  
**Corpus:** `.worktrees/mql5-library/data/mql5-library/` only  
**Extractions:** `extractions/regime.jsonl` — **43 new full-reads** (none of the 24 already-read IDs)  
**Priors cited but not re-extracted:** 17737, 23286, 22940, 16830, 15223, 23482, 23016, 10715, 23454, 21003, 14203, 19944 (+ scalp-set 9804…22772)  
**Leftovers cleared this pass:** 15033, 17781, 15541, 23137, 23444, 22258, 23677, 22484, 23488, 22754, 16213, 3395, 20037, 21142, 752  

QMX law (operating line): MIS is information-only → Book door + KSA. Bots never consume the snapshot. SQS is spread-only. A class score is not an edge and does not size or switch playbooks inside MIS.

---

## Concept clusters

### 1. Explicit discrete market-state taxonomies (rule / hierarchical)

| Cluster member | Labels | Gate style |
|---|---|---|
| Prior 17737 + new **17781** | trend up/down · range · volatile | vol-ratio first, then \|trend\| |
| New **20996** | compression · transition · expansion (+ trend separate) | hierarchy: expansion → compression → trend → transition |
| New **21743** | TREND · TRANSITION · CHAOTIC | Shannon entropy thresholds 0.35 / 0.65 |
| New **23444** (+ **23149**) | cycle · trend | EBSW rail \|EBSW\|≥0.85 |
| New **22783** | bull · bear | hysteresis 200d high/low channel |
| New **23734** | four IV/RV-ratio states | heuristic cuts 1.20 / 1.05 / 0.95 |
| New **22807** | four ATR vol states + accum/exp/dist/rev | dual ATR depth bands |
| Prior 22940 | six micro regimes | priority rules on NQ M1 |

**MIS takeaway:** Prefer **unsigned** labels. Drop up/down, bull/bear side, and fade arrows. Keep hierarchical “stressed/volatile/expansion first” as door-friendly.

### 2. Latent-state / HMM / Markov

- **15033** — HMM primer: Baum-Welch, forward/backward, Viterbi; **freeze JSON → MQL5 inference**.
- **17917** — GaussianHMM ≈ GMMHMM ≈ Variational; prefer **3–5 states** + good priors over ~10 clusters; XAUUSD H1.
- **15541** — Nash metaphor + **10-state** GaussianHMM with even/odd→side map (weak operationalization; leakage-prone splits).
- **16830 (prior)** — 2-state **vol** HMM as filter; author suspects redundancy with raw σ.
- **11930 / 18097 / 18192** — *observable* Markov transition matrices / ATR-binned states (FLAT band \|Δ\|≤0.25 ATR-norm).
- **16030** — deep Markov (heavy; shadow only).

**MIS takeaway:** HMM remains a **shadow** `regime_classifier_v1` candidate (GAP-0051). Always ablate vs raw rolling-σ / ATR_z. Online self-learning Markov NNs are out of MIS.

### 3. Volatility-as-regime (parametric + asymmetric)

- Prior **15223** GARCH(1,1); new **22258** GJR/TARCH (equity leverage vs FX-robust); **23677** EGARCH (escapes positivity pin) + **Asymmetric Volatility Regime Oscillator**.
- **23488 catch22** — best new evidence: leak-free **LOW/MED/HIGH** forward-vol classification; COMBINED accuracy **0.444** > CLASSIC **0.404** > CATCH22-alone **0.348**.
- **23734** — options IV/RV (GLD→gold) as **forward-looking** vol regime (heuristic thresholds).
- **16213 / 752 / 22807** — ATR as cheap baseline / multi-symbol / regime-conditioned thresholds.
- **22638** — vol that “remembers” (long-memory vol).

**MIS takeaway:** Map toward QMX classes `quiet|normal|elevated|stressed`. catch22 + ATR ablation is the strongest *new* feature lead. IV/RV is a Book/KSA sensor if venue has options; crypto-spot may lack it.

### 4. Chop / flat / persistence / fractal

- **4534** — ten flat strategies; flat *identification* is Task 1; filters include **ADX** and **Ehlers fractal dimension**.
- **15222 / 2930 / 6834 / 22484 / 22553** — Hurst H≳0.5 trend persistence, H≲0.5 MR/chop; multifractal spectrum as fingerprint; prediction ability limited (6834; prior 14203 OOS fail).
- **21743 / 22220** — Shannon entropy chop/chaos (bar vs tick).
- Prior **23286** TDA persistence entropy (heavy).
- **23451** — ordinal pattern transition networks (symbolic dynamics cousin of catch22 motifs).

**MIS takeaway:** Cheap chop stack for ablation: ADX-low · entropy band · Hurst (slow) · 17737-range. TDA/MMAR stay heavy/shadow.

### 5. Change-point / breakpoint / bagging “regimes”

- Prior **23482** BOCPD (`cp_prob`, run length).
- **21142** L1 trend filter — piecewise-linear breakpoints as regime changes; **L1VolatilityRegime**; **causal trailing window required** for live MIS (batch L1 leaks).
- **21833** — CUSUM CPD + VolatilityGate (grid context; method reusable).
- **23137** — title trap: “Bagging Regimes” = **sampler regimes**, not market states. Result: throttle `max_samples` to average uniqueness; sequential bootstrap rule adds little on EURUSD; OOB inflated.

### 6. Playbook / strategy switch (source pattern; QMX-forbidden inside MIS)

- **17781** — trend / MR / breakout + per-regime lot/SL/TP.
- **23444** — cycle fade vs trend-follow MAMA/FAMA.
- **22783** — asymmetric bull swing vs bear DVO MR; exit-rule swap on regime change (not force-flat).
- **20414** ASMA — SMC + sentiment switching.
- **22754 / 22274** — meta-label + ADXR/RSI regime gates; sizing from secondary confidence.

**MIS takeaway:** These validate *demand* for a clean state label. The switch, size, and side live in **Book / bot confluence**, never in MIS.

### 7. Session / clock / bar representation

- **3395 / 20037** (+ prior 21003 / 19944) — time filters as coordinates.
- **23310** — bar family (time vs event) changes trending vs MR efficacy → **declare `bar_type` in provenance**.

---

## Surprises

1. **catch22 (23488)** is the cleanest *new* regime-ML article: explicit anti-leak protocol, numeric three-arm ablation, model-as-**gate** not signal. Directly usable as feature research for `regime_classifier_v1`.
2. **23137 Bagging Regimes** is *not* market regime — but its methodological lesson (decompose bundled changes; never trust OOB on overlapping labels) applies to any fitted MIS classifier.
3. **20996** separates **state (constraint/energy)** from **trend (direction structure)** — closest philosophical match to “MIS is not direction.”
4. **23734** shows a forward-looking vol regime from **options**, orthogonal to all price-only producers; thresholds honestly labeled heuristic.
5. **22783 hysteresis** is a strong anti-whipsaw idea rarely stated so clearly: path-dependent regime memory; change *exit rules* on flip rather than dump inventory.
6. **Ehlers stack (23149→23444)** gives an engineer-grade binary cycle/trend regime with published coefficients and closed-bar discipline — rare honesty about “demo not edge.”
7. No dedicated “Choppiness Index” title still; chop is reconstructed from ADX-low, entropy, Hurst, flat detectors, TDA.

## Contradictions / tensions

| Tension | Evidence |
|---|---|
| HMM helps vs HMM ≈ raw σ | 15033/17917 promote HMM; prior 16830 suspects σ threshold equivalence; 15541’s 10-state parity map is a cautionary anti-pattern |
| Sequential bootstrap necessary? | AFML says yes; **23137** on EURUSD says **count throttle** is the lever |
| GARCH family choice | Symmetric GARCH (15223) vs GJR equity vs TARCH FX vs EGARCH when params pin to boundary |
| Entropy thresholds | 21743 uses 0.35/0.65 on bar states; 22220 uses four tick-vol regimes — not interchangeable |
| Hurst as predictor | 15222 uses H to pick MA playbook; 6834/14203 show weak/failed OOS prediction — keep as **slow diagnostic**, not trigger |
| Flat vs compression vs range vs cycle | Overlapping English; different operationalizations (4534 channels, 20996 compression, 17737 range, 23444 cycle) |
| IV/RV high | 23734: protection expensive / quiet-chart trap — **not** the same as realized “volatile” in 17737 |

---

## Placement map (MIS snapshot vs SQS vs bot confluence vs Book door)

### MIS snapshot (information-only labels / coordinates)

Eligible if deterministic or freeze-and-ship, unsigned, door/KSA-consumable:

- `regime_3way` {trend, range, volatile} — 17737 family; **17781 is not MIS**
- `pa_state` {compression, transition, expansion} + optional `trend_flag` — **20996** (strip visualization)
- `entropy_band` {trend, transition, chaotic} + H — **21743** (strip buy/sell arrows)
- `ebsw_trend_mode` / `dominant_period_bars` — **23149/23444**
- `adx` / `adxr` / `adx_rising` / `di_separation` — **10715 + 22754** (no DI side)
- `atr` / `atr_z` / `atr_regime` — **16213 / 22807**
- `vol_garch` / `vol_gjr|tarch|egarch` + z — **15223 / 22258 / 23677** (fitted, `not_ready` on fail)
- `hmm_vol_state` + posterior — **15033 / 17917 / 16830** (shadow)
- `cp_prob` / `run_length` — prior BOCPD; L1 breakpoints only if **causal** — **21142**
- `hurst` / `fractal_dim` / `mf_width` — slow — **15222 / 22484 / 22553 / 4534#3**
- `catch22_vec` or selected subset — **23488** (shadow/heavy until rung)
- `iv_rv_ratio` + state — **23734** if options feed exists
- `session_id` / `tod_bucket` / `bar_type` — **3395 / 20037 / 23310**
- `kalman_gain` — prior 23016; residual mag from **17273** (not price line)

Publish `not_ready` until warm-up / fit / feed age OK.

### SQS (spread only)

**Unchanged.** Live spread ÷ session-window baseline.  
Session_id / tod_bucket may **key the baseline**. ATR, ADX, HMM, GARCH, entropy, IV/RV **do not enter SQS**.

### Bot confluence (direction, entries, playbooks)

- DI+/DI−, RSI fades, MAMA/FAMA crosses, EBSW fade entries — **23444 / 22754 / 22274**
- 17781 playbook switch and per-regime entries
- 22783 Value Chart / DVO / SVAPO legs
- 20414 SMC switches
- Kalman fair-value crosses — **17273 / 3886**
- catch22EA / meta-label **side** (gate OK as bot policy reading a copy of features — but **not** via MIS consumer path)

### Book door / KSA (policy on top of snapshot)

- Refuse / cool-down on `volatile` / `expansion` / `chaotic` / `cp_prob>θ` / high `iv_rv_ratio` during quiet ATR
- Class activation (which bot books may arm) from unsigned regime
- Hysteresis / smoothing of regime flips — **17781 / 22783** ideas as **Book policy**, not MIS
- Bet sizing from meta-label confidence — **22754** — Book, not MIS
- Grid VolatilityGate / CUSUM — **21833** method only

---

## Implications for `regime_classifier_v1` (lightgbm-multiclass on integration)

Chosen family on integration: `lightgbm-multiclass`, classes `quiet|normal|elevated|stressed`.

**Feature ablation order suggested by this pass + prior:**

1. ATR_z / range-σ ratio / ADX(+ADXR) / TOD bucket  
2. 17737-style vol-then-trend scores (unsigned)  
3. Shannon entropy band (21743)  
4. BOCPD `cp_prob` as break sensor feature  
5. catch22 subset (outlier timing, pNN40, Welch, DFA) — **23488**  
6. Only then shadow HMM / GARCH-asym / L1 residual vol / IV-RV  

**Training discipline from 23137:** uniqueness-aware sampling; purged CV; never select on OOB with overlapping labels; decompose “regime” changes in experiments.

**Label caution:** Source LOW/MED/HIGH forward-vol (23488), compression/expansion (20996), and IV/RV states (23734) are **not identical** to quiet|normal|elevated|stressed — need an explicit mapping table before training.

---

## Asset / venue dependencies to keep on every row

- NQ M1 microstructure lineage: prior 22940, new **23372** (514 NY sessions)  
- EURUSD: 23444 M30, 22754 H1, 23137 tick/M5, 22484 M5  
- XAUUSD: 17917 H1, 22220 ticks, 23734 gold via **GLD options**  
- Nasdaq equities daily: **22783** (AMZN best Sharpe in their opt)  
- S&P/SPY: GJR/EGARCH demos **22258 / 23677**  

No instrument ceiling: keep the idea; record the dependency; do not pretend NQ percentiles or GLD IV thresholds transfer to crypto-spot without recalibration.

---

## Testable hypotheses (priority)

1. catch22+classic > classic alone on QMX vol-stress labels (replicate 23488 ablation with purged CV).  
2. ADXR+DI-separation gate vs ADX>25 folklore for suppressing range whipsaw (22754).  
3. EBSW rail vs 17737 trend/range confusion matrix (23444).  
4. HMM-2 vol state vs ATR_z — incremental door precision (15033/16830).  
5. Hysteresis persistence vs raw label flip rate (22783/17781) as Book policy.  
6. Causal L1 breakpoints vs BOCPD agreement (21142 vs 23482).  
7. IV/RV>1.2 predicts forward RV elevation on XAUUSD (23734); skip if no options.

---

## Evidence hygiene

- Levels used in JSONL: **A** reproducible with numbers/protocol (23488, 23137); **B** detailed testable methods; **C** practitioner; **D** weak anecdote (3886); no **X** outright contradiction of a physical law — tensions listed above instead.  
- Formulas recorded only when stated or standard named (Wilder, Shannon, Ehlers coefficients, GARCH/GJR structure, R/S Hurst, Kalman). Image-only equations noted as “as in article figures/code.”  
- **Do not** treat vendor EA profit as QMX edge certification.
)
