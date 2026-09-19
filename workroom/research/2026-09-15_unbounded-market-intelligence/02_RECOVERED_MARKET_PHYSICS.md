# Recovered MIS / regime stack (in-repo)

**Recovery date:** 2026-09-15  
**Scope:** Content already inside `C:\Users\Mubarak\Desktop\QMX` only.  
**Centre:** regime, change/changeover analogues, market state, placement, filters, SQS, labelers, shadow — not physics.  
**Legend:** **FACT** = cited in-repo text; **INFERENCE** = synthesis across in-repo sources; **UNCERTAINTY** = conflict, absence, or OPERATING_LINE-only claim.

---

## 1. What MIS is (ratified)

**FACT —** MIS is the trading node's **labeler layer**. Per-instant outputs fold into one compute-once, versioned, immutable **signal snapshot** dispatched to a **closed consumer set: Book door and KSA only**. Bots never consume it (`docs/glossary.md` MIS; `docs/components/trading-node.md` TN-19; DEC-0204).

**FACT —** V1 MIS is a **seam**, not a bound trained model runtime: rule-based deterministic labelers in-process; producers read the world room **as of the slice frontier**, never wall-now; cannot-bound ⇒ `not_ready`; until live-path rung baseline exists every labeler is **heavy by default** (TN-19; glossary signal snapshot).

**FACT —** Kill switch / KSA is **sensor-fed** by the MIS signal snapshot and SQS; MIS/SQS are **inputs, never authorities** (glossary kill switch / KSA; tracker notes).

**FACT —** Protection funnel: **MIS senses → KSA decides (escalate-only) → Adapter enforces** (`archive/recovery/trading-node-delta/trading-node-delta.md` K-41; `tracker/trading-node-notes.md`).

**INFERENCE —** Early tracker language "MIS is an ML ensembler" / "MIS assembler" is historical operator phrasing; later audit says **"MIS assembler" never existed** as a component (`tracker/trading-node-notes.md`). Ratified docs use **labeler layer / signal snapshot**.

---

## 2. DEC-0262 eight-labeler catalog

**FACT —** Old corpus / DEC-0262 ratifies **eight** labelers (`docs/glossary.md` MIS; `docs/changelog.md`; `_docwork/gaps.yaml` GAP-0051 catalog_note):

| # | Kind | Name |
|---|---|---|
| 1–6 | rule-based | `identity`, `spread-state`, `gap-event`, `feed-state`, `SQS`, `degraded-sensors` |
| 7 | fitted | `liquidity_stress_v1` (CPU quantile fit) |
| 8 | trained | `regime_classifier_v1` — **no ratified model family, hyperparameters, label-generation method, or training location** (the design story) |

**FACT —** V1 binds rule-based + fitted `liquidity_stress_v1` only; **no trained model bound**. Training + shadow rollout of `regime_classifier_v1` is **GAP-0051**, last node epic, offline operator-run script on his machine (`docs/changelog.md`; ADR-0019).

**FACT —** Recovered candidates **Kronos, HMM, BOCPD, MS-GARCH** carry **no authority** until fresh ratification (DEC-0262).

**FACT —** Explicit snapshot fields named in current glossary/TN-19 payload list: per-instrument **SQS score + hard-block**, `feed_state` `live|degraded|dead`, `degraded_sensors`, labeler version stamps, readiness `ok|not_ready|unavailable|stale|refused`. Cataloged labelers (identity, spread-state, gap-event, liquidity_stress) are owed in the Epic 26 fold even when not every name appears in the short DEC-0204 payload list (`workroom/research/2026-09-09_mis-scalping-ideation.md` §1–2).

---

## 3. SQS = Spread Quality Sensor (not regime, not snapshot-quality)

**FACT —** Constitution L23 / DEC-0074 / DEC-0153: **SQS means Spread Quality Sensor**, distinct from news controls.

**FACT —** V1 formula (AD-39 / DEC-0153):  
`score = historical average spread for declared session window ÷ current live spread`  
Exact rational over two scaled-integer spreads; 1 = baseline; above 1 tighter; below 1 wider. Per-instrument-class hard-block threshold; hysteresis band; outlier guard; undefined/unreachable/stale/refused ⇒ **hard block**. Every parameter UI-editable, no spine defaults (`docs/glossary.md` SQS; `docs/gap-report.md` GAP-0043; tracker SQS V1 note).

**FACT —** Authority: SQS **computes**, MIS **transports** (inside the signal snapshot only), **Book door decides**. SQS never sizes, never authorizes, never is a regime model (`docs/glossary.md`; OPERATING_LINE; delta K-38).

**FACT —** Semantic zombies to leave dead: Snapshot Quality Sensor (DEC-0073), `snapshot_quality_score_v1` / `sqs_weighted_component_floor_v1` six-component aggregate (delta R-08 / D-09), AWS Simple Queue Service, SQS-as-execution-authority (`archive/recovery/trading-node-delta/*`; `_docwork/analysis/*`).

**FACT —** SQS baseline is a separate fingerprinted artifact keyed `(VenueId, environment, instrument)`; demo-conditioned baseline never satisfies live binding; session window may **condition** the baseline, not replace SQS (`docs/glossary.md` SQS baseline; MQL5 regime notes placement legend).

---

## 4. Shadow lane

**FACT —** Shadow-lane seam is **V1 node work** (DEC-0204 / DEC-0215), three pieces (`docs/glossary.md` shadow-lane seam; TN-19):

1. **Candidate labeler** registered into CANDIDATE role; governed consumers refuse it; identity enters separate `shadow_composition_fp` (not governed `composition_fp`); heavy; drop+journal if outside `registry:shadow_lane_publish_bound`.
2. **Shadow snapshot stream** on its own manifest prefix / WriterId; same per-instant schema and frontier-as-of rule.
3. **Ungoverned comparison read model** diffs shadow vs governed snapshot; **gates nothing**. Wiring a candidate into a governed consumer **refuses to boot**.

**FACT —** Research prior art (`08-mis-ml-regime-models.md`) independently recommends batch-fit / frozen artifact / promotion_state `candidate|shadow|live|retired` for shadow-compatible rollout — aligned with node shadow seam, not a second law.

**INFERENCE —** Epic 26 builds rule-based + fitted + shadow seam; Epic 30 drops a designed/trained `regime_classifier_v1` into that seam (`_bmad-output/planning-artifacts/epics.md`).

---

## 5. Regime / change / changeover analogues

### 5.1 Ratified vs recovered class vocabularies

| Vocabulary | Source | Status |
|---|---|---|
| `regime_classifier_v1` undesigned | DEC-0262 / GAP-0051 | **FACT** — design owed |
| GitBook optional `regime` `trend\|range\|chaos` + `regime_confidence` | `archive/recovery/.../gitbook-baseline.md`; ideation | **FACT** recovered baseline; **not** DEC-0204 live contract |
| GitBook `spread_state` `normal\|elevated\|extreme` | same | **FACT** recovered; cataloged V1 rule-based name `spread-state` |
| Research draft `CALM\|TURBULENT\|CRISIS` | `08-mis-ml-regime-models.md` MarketView sketch | **INFERENCE** / prior-art proposal only |
| Operator ideation `choppy vs trend vs news vs dead` | ideation §1.3 | **INFERENCE** — mixes statistical vs calendar ontologies; ideation warns not to put news/dead inside classifier |
| OPERATING_LINE `quiet\|normal\|elevated\|stressed` + family `lightgbm-multiclass` | `OPERATING_LINE.md` only | **UNCERTAINTY** — not found elsewhere in this checkout's ratified docs/epics; see §9 and `04_RECOVERY_UNCERTAINTIES.md` |

### 5.2 Literal "changeover"

**FACT / ABSENCE —** Token **`changeover`** as MIS/regime vocabulary is **ABSENT-IN-REPO** (content search). Closest ratified constructs:

- **`session_handover_buffer`** — CT-31 protection window around session handover (`pre-close|post-open|both`); calendar-derived; absent for 24/7; blocks new entries only (DEC-0152).
- **BOCPD / change-point** — recovered unauthorized candidate; MQL5 notes propose `cp_prob` / `run_length` as door/KSA **break sensor**, not direction (`2026-09-09_mql5-mis-regime-notes.md`).
- **Regime change language** in research (smoothed vs filtered labels; jump models; MS-GARCH) — method evidence / prior art, not ratified class names.

### 5.3 MQL5 method families already mined in-repo (PLAN evidence, untested)

From `2026-09-09_mql5-mis-regime-notes.md` + ideation (12+15 full reads; not the whole 3057):

| Family | In-repo primitive ideas | Placement cut |
|---|---|---|
| Hierarchical vol/trend/range (17737) | `regime_3way` without direction | MIS filter |
| Persistence entropy / TDA (23286) | H0/H1, loop-strength band | MIS heavy/shadow; fade = bot |
| Microstructure six-way (22940) | stressed-first rule reduction | shadow method; strip signed composite |
| Vol HMM filter (16830) | `hmm_vol_state` | unauthorized recovered; shadow candidate |
| GARCH(1,1) (15223) | `garch_sigma` fitted like liquidity_stress | not SQS |
| BOCPD (23482) | `cp_prob`, `run_length` | best door-sensor shape in set |
| Kalman gain (23016) | `kalman_gain` noise coordinate | MIS; smoothed price = bot |
| ADX (10715) | `adx` / `adx_rising` | cheap ablation baseline |
| Range σ YZ/GK (23454) | `vol_yz` / `vol_gk` | MIS vol feature; not SQS |
| Hurst/VRT/HL (14203) | slow persistence features | refresh or stale |
| Session id (19944) | `session_id` keys SQS baseline | coordinate |

**FACT —** Empirical status in those notes: **all rows untested in QMX**. Vendor EAs that switch playbooks or size from regime are **forbidden** as MIS behavior (DEC-0204).

### 5.4 Prior-art regime stack (`08-mis-ml-regime-models.md`)

**FACT (research file, not sitting law) —** Five families surveyed: HMM, Markov-switching, jump models, change-point (ruptures offline / BOCPD online), GARCH, clustering. Core trap: **smoothing / Viterbi / Kim smoother look-ahead**. Live-safe = filtered/predicted only; machine-checkable invariant `label(bars[0:t])[-1] == label(bars[0:t+n])[t]`.

**FACT (research) —** FX literature: regime models **not** credible as direction predictors; modest support as **risk filters / blend components**. Recommended posture: MIS as risk instrument, not alpha.

**FACT (research) —** Prefers batch-fit + freeze + LightGBM text artifact if supervised; river for **drift only**; FreqAI-style trust triple `confidence` / `novelty` / `staleness` as idea (GPL — idea only).

**INFERENCE —** File 08's "Books and bots read that answer" is **stale vs DEC-0204** (bots do not consume MIS); ideation already flags this.

---

## 6. Placement / filters / adjacent non-MIS authorities

**FACT —** Do **not** put into MIS:

- News windows, `daily_dead_zone`, `session_handover_buffer` → CT-31 / Book / KSA (`scheduled_news`).
- Direction, fade arrows, MA crosses, playbook switches → bot confluence.
- London-box **levels** / DOM resting clusters → SQS **blocks** (locations), not MIS labels (`2026-09-09_mql5-mis-scalp-notes.md`).
- Sizing, entries, exits → Book / bots.

**FACT —** Macro/micro research (`10-macro-micro-analysis-data.md`): highest-value free micro for prop trading is **spread hour-by-hour**; two-timestamp PIT (`event_time` + `available_at`) for any revisable feature feeding MIS/training.

**FACT —** Experimentation research (`09-...`): search/overfitting discipline (DSR/PBO/SPA) constrains any later regime-family search; not a MIS producer.

---

## 7. Physics-like language (one keyword family)

Searches run under `C:\Users\Mubarak\Desktop\QMX` (content, not Desktop-outside):

| Term | Result |
|---|---|
| `\bIsing\b` | **ABSENT-IN-REPO** as design content. Only listed as a **future corpus search keyword** in `tools/index_corpus.py`. |
| `physics_multiplier` | **ABSENT-IN-REPO** (zero hits). |
| `\bLyapunov\b` | **Not a QMX design.** Hits: MQL5 inventory title for article 15332 ("…Lyapunov exponent") in `09_CORPUS_INVENTORY.csv`; same keyword list in `index_corpus.py`; OPERATING_LINE mention that physics is not the centre. |
| `market physics` / econophysics / spin glass / Fokker-Planck / Kuramoto | Tool keyword list and/or corpus inventory only; **no QMX labeler, formula, or decision** recovered. |
| `physics` elsewhere | Unrelated uses (e.g. "fill physics" in backtesting recovery; English "raising"). |
| Entropy / Hurst / fractal / multifractal | **Present** as MQL5 **method evidence** in regime/scalp notes (persistence entropy, GHE, fractal-dimension leftovers) — statistical/TDA family, not Ising/Lyapunov market-physics stack. |

**INFERENCE —** In this repo, "physics-like" recoverable content is **thin**: corpus-search scaffolding + one MQL5 Lyapunov **title** + entropy/Hurst method notes. There is **no** recovered Ising, Lyapunov-based MIS producer, or `physics_multiplier` artifact.

---

## 8. Historical GitBook MIS payload (recovered, not live law)

**FACT —** `archive/recovery/trading-node-delta/work/gitbook-baseline.md` CT-MIS-01 required: `pair`, `resolution`, `snapshot_version`, `spread_state` (`normal|elevated|extreme`), `gap_event`, `liquidity_stress`, `feed_state` (`fresh|stale|dead`), `sqs_score`, `sqs_hard_block`, `degraded_sensors`; optional `regime` (`trend|range|chaos`), `regime_confidence`.

**FACT —** Drift vs current docs: `feed_state` enum renamed (`fresh|stale|dead` → `live|degraded|dead`); consumers narrowed to Book+KSA; SQS formula ratified; trained regime unbound (`2026-09-09_mis-scalping-ideation.md` §1.2).

**UNCERTAINTY —** Delta C-01 once recorded wiki allowing manifest-bounded bot MIS consumers vs Story 3.2 Book/KSA-only; **current ratified docs close on Book+KSA-only** (DEC-0204). Treat C-01 as historical conflict resolved in docs, unless a later sitting reopens it.

---

## 9. OPERATING_LINE vs ratified docs (integration claim)

**FACT —** `OPERATING_LINE.md` states (session truth for this folder):

- MIS → Book door + KSA only; bots never.
- SQS = Spread Quality Sensor, block-only.
- V1 producers: identity, spread-state, gap-event, feed-state, SQS, degraded-sensors, fitted `liquidity_stress_v1`.
- `regime_classifier_v1` design story; **"Integration already has design/corpus/labels/train/eval/register/shadow seams. Chosen family on integration is `lightgbm-multiclass`. Classes: quiet|normal|elevated|stressed."**
- Kronos/HMM/BOCPD/MS-GARCH unauthoritative.
- Classification score ≠ trading edge; MIS does not size/switch playbooks/own entries.

**UNCERTAINTY —** Content search of this checkout found **`lightgbm-multiclass` and class set `quiet|normal|elevated|stressed` only in OPERATING_LINE.md**. Ratified glossary/changelog/epics Story 30.1 still say the **model family is unruled / design story**. No production code was inspected for this recovery (forbidden); no integration-branch tree was assumed outside this folder.

**INFERENCE —** Treat OPERATING_LINE's lightgbm/class claim as **session operating claim about work elsewhere or in progress**, not as a recovered ratified DEC. Prefer DEC-0262 wording for authority until docs catch up or a sitting cites integration artifacts inside this repo.

---

## 10. One-sentence stack summary

**INFERENCE —** In-repo recovered MIS stack is: **eight named labelers (six rule + one fitted + one undesigned trained classifier) → compute-once signal snapshot → Book door + KSA**; **SQS is a block-only spread-ratio sensor inside that snapshot**; **shadow lane is the drop path for candidates**; **regime change is BOCPD/handover/window language, not a token `changeover`**; **physics (Ising/Lyapunov/physics_multiplier) is ABSENT as design**; method fuel lives in `08-…` and the 2026-09-09 MQL5 notes.
