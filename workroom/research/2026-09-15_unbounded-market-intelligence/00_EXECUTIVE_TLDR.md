# 00 — Executive TL;DR

Research date 2026-09-15. Folder-only. Regime / changeover / placement first; physics searched, not centred.

## 1. What market-physics material was recovered?

**None as QMX design, inside this folder.** No Ising, no `physics_multiplier`, no Lyapunov producer. Recovery greps are in `01_` / `02_` / `04_`. Chaos/Lyapunov exist only as **MQL5 articles** (15332 and sequels).

## 2. What was not recovered?

A named `MarketPhysicsSensor`. Estimators for Ising/Lyapunov/eigenvalue-spread as QMX law. Any in-repo code path that sizes from “physics.” Desktop vaults were **not** searched this run (operator: stay in this folder).

## 3. What does QMX already have?

On `integration@8510c03`: compute-once **signal snapshot** to **Book door + KSA only**; SQS = spread ratio, block-only; six rule-based labelers + fitted `liquidity_stress_v1`; **shadow seam** empty of models. `regime_classifier_v1` has a **design-only** LightGBM contract (classes `quiet|normal|elevated|stressed`, forward-range quantile labels, leakage laws) and **no governed bind**. QMB already has sweep/optimize/robustness/three experiment lanes. Details: `05_`, `07_`, `08_`.

## 4. What is the real missing capability, if any?

Not “a physics engine.” The unpaid named gap is **GAP-0051**: a **causal, abstaining market-state label** that can drop into the **existing shadow seam**, then maybe the snapshot after a sitting — used as a **sit-out / family-compatibility input**, not a direction or size knob. Competing formulations (discrete vol buckets vs compression/expansion vs sequential break sensors vs a continuous channel) are still open. See `16_`.

## 5. Most surprising findings

- Docs still say the trained family is unchosen; **integration code already chose LightGBM** (design-only). Docs lag code (`04_` U1 vs `05_` §4).
- Title-level **changeover literature is small** (11 titles). **PELT, MS-GARCH, and a named Hamilton filter are absent** from this library. CUSUM Part 2 (23103): empirical ARL ~5× worse than Siegmund; it behaves as a **vol-break detector**, not a directional mean-shift detector.
- **Hawkes / Ising / Kuramoto / percolation / spin glass / Fokker–Planck: zero real hits** in 3057 bodies (`notes/rare_and_surprising.md`).
- 20996 compression/transition/expansion is a **non-trading** classifier. 17781/23444/22783 **switch playbooks** — the corpus default, and **illegal for MIS**.
- 22290: on TECH100 MACD, **session filter beat regime/HTF**. 22274/23665: many “filter” DD cuts are just **less exposure**.
- 22553: NQ M1 Hurst ≈ 0.51 and **does not** predict intraday trend (honest near-null).
- 23488 catch22 + leak-free vol-regime eval is the closest *task* match to quiet|normal|elevated|stressed.
- DST/broker-server clocks are first-class bugs (16171, 23388, 22516). Asia continuation remains unproven.
- Exact sha256 duplicates: **zero**. ~239 unique full-read extraction rows in `11_` (plus 24 prior-note reads).

## 6. Three directions that deserve immediate experiments

1. **Simple causal baselines vs the integration design:** ADX-low / σ-ratio 3-way / spread-state proxy vs LightGBM quiet|normal|elevated|stressed, evaluated on **downstream sit-out / door behaviour**, not F1 alone (`21_`, `22_`).
2. **Changeover as a separate sensor:** CUSUM (23043) and BOCPD (23482) `P(break)` + run length on the snapshot; cooldown policy stays Book.
3. **Alternate state vocabulary in shadow only:** 20996 compression/transition/expansion (no direction) vs current four vol buckets — same Book-door task, ablate.

## 7. Three attractive ideas to reject or postpone

1. Restore Ising / `physics_multiplier` / Lyapunov as live authority (`19_`).
2. MIS-driven playbook switch (17781 and kin) — **incompatible** with DEC-0204.
3. Online-river / VPS retraining / hmmlearn `predict_proba` history labels — look-ahead or irreproducible (`08` prior art; `regime_design` already rejects river).

## 8. Still uncertain

- 258 Firecrawl-failed IDs unread (early catalog; method clusters are mostly fetched).
- Whether forward-range **labels** (next 12 M5 bars) are the right target for a *live* sit-out decision vs a *now* descriptor (compression/expansion). E1/E3 in `21_`.
- Operator meaning of “changeover”: calendar handover vs CUSUM/BOCPD break vs class transition (`04_` U3, `27_`).
- ~14 malformed jsonl lines were dropped in the merge; shard notes remain the authority for those rows.
- Crypto-spot transfer of FX session enums and CUSUM ARL — untested.
