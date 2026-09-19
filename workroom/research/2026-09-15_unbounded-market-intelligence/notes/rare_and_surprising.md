# Rare terms & surprising findings — feed for `13_RARE_AND_SURPRISING_FINDINGS.md`

**Pass:** 2026-09-15 placement/filters researcher  
**Evidence:** full body sweep of 3057 fetched articles (`tools/rare_body_sweep.py` → `indexes/rare_body_hits.json`) + targeted full-reads  
**Extractions:** `extractions/rare_physics.jsonl`  
**Stance:** rare physics is a **search**, not the thesis. Negative findings are first-class.

QMX reminder: none of these rare objects authorize MIS playbook switching or sizing.

---

## A. Deliberate rare-term sweep (body)

| Term | Articles with real hits | Verdict |
|---|---|---|
| **Hawkes** | 0 | **Absent** |
| **Ising** | 0 | **Absent** |
| **Kuramoto** | 0 | **Absent** |
| **percolation** | 0 | **Absent** |
| **spin glass** | 0 | **Absent** |
| **Fokker–Planck** | 0 | **Absent** |
| **transfer entropy** | **1 real** (`15393`); others are sidebar links | Thin but real method article |
| **mutual information** | **29** title/body; flagship `16416` (MRMR feature select) | Present as **feature triage**, not sit-out |
| **Lyapunov** | **12**; real stack `15332`,`15445`,`17706` (+ link noise) | Present as chaos coordinate / indicator |
| **econophysics** | **3** (`6834`,`8038`,`16494`) | Name-check / framing only |
| **random matrix** | **1** (`24057` Marcenko–Pastur denoising) | Present as ML panel hygiene |
| **criticality** | 23 regex | **Mostly false positive** (“critical point” prose; logging). Real: Bak–Sneppen SOC as **optimizer metaphor** (`18755` et al.), not market criticality sensor |
| **information flow** | 56 regex | **Mostly NN architecture jargon**; market causality lives under TE |

### A.1 Negative finding (keep)

The MQL5 article corpus, as fetched, does **not** contain a Hawkes / Ising / Kuramoto / percolation / spin-glass / Fokker–Planck trading toolkit. Anyone proposing those as “standard MQL5 regime methods” is projecting outside this library. Econophysics is rhetorical varnish, not a stack.

### A.2 What *does* exist (short)

1. **`15393` Transfer entropy** — linear TE linked to Granger for Gaussians; nonlinear TE via bins + shuffle p/z. Scripts for lag detection. **Diagnostic of lead–lag / causality**, not a Book door.  
2. **`16416` Mutual information** — adaptive partitioning MI + stepwise MRMR. Use: choose features for a *later* filter model.  
3. **`15332`/`15445`/`17706` Lyapunov / chaos** — local λ indicator; nearest-neighbor chaos EA; Chaos Attractor Oscillator. Authors themselves hedge (“not Holy Grail”, mixed per pair).  
4. **`17351`/`17371` Attraos** — chaos-inspired NN forecasting; final part: results implementation-specific; original paper setup not retested.  
5. **`24057` RMT** — MP denoise/detone correlation before clustering feature importance; notes nonstationary corr ⇒ re-fit across regimes. Offline ML hygiene for a classifier panel — **not** a trade gate.  
6. **`6834`** — fractal index / Hurst with econophysics color; disorder/change detection claim at shorter scale than H.

**QMX cut for all of the above:** research/shadow only. Do not displace `regime_classifier_v1` design (`lightgbm-multiclass` on integration) with Lyapunov-as-authority.

---

## B. Surprising *placement* findings (non-physics)

These belong in the rare/surprising rollup because they puncture folklore harder than any Ising toy.

### B.1 Session beat regime (ablation)

**`22290`** — Three MACD filters on US_TECH100, five years broker H1: **regime filter alone ≈ no help; HTF alone ≈ no help; session filter did most of the work.**  
Surprising relative to the corpus’s heavy regime-switch rhetoric (`17781`,`23444`,`22783`) and to **`21351`** calling TOD filters brittle.

### B.2 Meta-label mainly buys less exposure

**`22274`** — Secondary filter removed 455/576 OOS RSI signals; P&L almost unchanged; max DD roughly halved; sizing then dominated further DD/loss reduction.  
“Filter edge” ≠ profitability; often **exposure control**. Aligns with QMX: Book owns size; classification score ≠ edge (`OPERATING_LINE.md`).

### B.3 Operational ≠ selection

**`23665`** — Block-permutation / placebo fixed-count test: a filter can improve portfolio metrics via occupancy without accepted trades being a special subset (and the reverse). Required thinking before promoting any door rule.

### B.4 Sit-out-after-losses can hurt

**`1441`** — Virtual-history pause filters underperformed the unfiltered EA on the author’s tests. Cooldown policies need the same skepticism as entry filters.

### B.5 L1 filter prefers exits

**`21142`** — Piecewise-linear L1 trend: author recommends it more for holding/exits than for entry gating.

### B.6 Authority split rare but crisp

**`21720` RiskGate** and **`23532` ExecutionGateway** state the QMX-shaped split (signal vs risk; strategy vs how-to-send) more cleanly than most “regime EA” articles. Surprising that these live under Examples/Trading systems while Interviews are almost empty.

### B.7 Taxonomy misses

- **Interviews** = only 3 ok articles; one (`22768`) is platform history, not an interview.  
- **Examples** hides both null cookbooks *and* high-signal work (`21142`,`22274`,`21720`,`652` multi-symbol anti-overfit).  
- Body family scan (`index_corpus.py`) shows `placement_filter` hits everywhere because `\bfilter\b` is ubiquitous — **title leads + manual read** still required; hit counts ≠ placement science.

### B.8 Look-ahead naming traps

- Calendar parameter **`LookAheadMin`** (`20037`) = minutes before news, not leakage.  
- Real leakage lectures cluster in meta-label feature pipes (`22755`) and CUSUM z-windows (`23043`), not in clock filters.  
- Many gate articles never say “look-ahead” at all — silence is common.

### B.9 “Quantum / chaos / econophysics” branding

**`21351`** “Quantum” gate = metaphor. Chaos/Lyapunov articles are earnest but sparse. Do not let branding inflate prevalence.

---

## C. Suggested bullets for `13_RARE_AND_SURPRISING_FINDINGS.md`

Copy/adapt:

1. Hawkes, Ising, Kuramoto, percolation, spin glass, Fokker–Planck: **zero** hits in 3057-article body sweep — negative finding.  
2. Transfer entropy: **one** real article (`15393`); mutual information: feature-selection tool (`16416`), not a door.  
3. Random matrix: **one** article (`24057`) for correlation denoising before ML clustering.  
4. “Criticality” / “information flow” regexes are polluted by English prose and NN jargon.  
5. Ablation surprise: session filter ≫ regime filter on TECH100 MACD (`22290`).  
6. Meta-label DD wins can be exposure, not selection edge (`22274` + test design `23665`).  
7. Corpus teaches playbook-switching from regimes; QMX MIS must not.  
8. Examples/Interviews shelves are unreliable recall indexes for placement science (`652`, `22768`).

---

## D. Files touched this pass

- `extractions/placement.jsonl` (50 rows: placement core + stratified 10)  
- `extractions/rare_physics.jsonl` (14 term rows)  
- `notes/placement.md`  
- `notes/rare_and_surprising.md` (this file)  
- `indexes/rare_body_hits.json`, `indexes/rare_body_ranked.json`  
- `indexes/hits_*.json`, `indexes/ranked_articles.json`, `indexes/deepread_shards.json` (from `tools/index_corpus.py`)
