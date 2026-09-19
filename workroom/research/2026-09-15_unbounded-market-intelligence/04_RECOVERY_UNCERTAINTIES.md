# Recovery uncertainties — MIS / regime stack

Distinguishes **recovered fact**, **inference**, and **uncertainty**. Scope = this QMX folder only. No Desktop-outside leads assumed.

---

## U1. OPERATING_LINE lightgbm / class vocabulary vs ratified docs

- **Claim (OPERATING_LINE):** integration already has design/corpus/labels/train/eval/register/shadow seams; chosen family `lightgbm-multiclass`; classes `quiet|normal|elevated|stressed`.
- **Counter-fact (docs/epics):** `regime_classifier_v1` has **no ratified model family**; Epic Story 30.1 still requires choosing family/class vocabulary before training.
- **Search:** `lightgbm-multiclass` and the quiet|normal|elevated|stressed **set** appear **only** in `OPERATING_LINE.md` in this checkout (LightGBM appears as prior-art recommendation in `08-mis-ml-regime-models.md`, not as a ratified family).
- **Status (recovery pass):** **UNCERTAINTY on `main` checkout** — recovery agent grepped the working tree, which does not contain `qmn/`.
- **Status (orchestrator follow-up, still in-folder):** **RESOLVED as design-only code, not ratified law.** `git show integration:qmn/src/qmn/mis/regime_design.py` at `8510c032496bb870824ecc5c4f807e8a4e4f167e` sets `CHOSEN_MODEL_FAMILY = "lightgbm-multiclass"` and `RegimeClass` `quiet|normal|elevated|stressed`, with `grants_money_path_authority=False` and `grants_governed_binding=False`. Glossary/GAP-0051 remain correct as **ratification** statements. See `05_CURRENT_QMX_BASELINE.md` §4.

---

## U2. Competing regime class vocabularies (none ratified for classifier)

| Source | Classes | Status |
|---|---|---|
| GitBook CT-MIS-01 optional | `trend\|range\|chaos` | Recovered baseline |
| GitBook spread_state | `normal\|elevated\|extreme` | Recovered; may fold as rule-based spread-state |
| File 08 MarketView sketch | `CALM\|TURBULENT\|CRISIS` | Research proposal |
| Operator ideation | choppy/trend/news/dead | Mixes calendar + statistical |
| OPERATING_LINE | quiet/normal/elevated/stressed | Session claim only |
| MQL5 17737 / 22940 | trend/range/volatile; six micro states | Method evidence |

**Uncertainty:** which closed set Epic 30 adopts is still a **sitting/design** question in-repo; multiple inventories exist.

---

## U3. Literal "changeover"

- **ABSENT** as a MIS/regime token.
- Closest ratified: `session_handover_buffer` (calendar), BOCPD-style break probability (unauthorized recovered candidate), research "regime change" prose.
- **Uncertainty:** whether operators using "changeover" mean handover windows, BOCPD breaks, or classifier class transitions — in-repo does not fix one synonym.

---

## U4. Physics family (Ising / Lyapunov / physics_multiplier)

Searches run (content under QMX):

1. `\bIsing\b` / case-insensitive Ising  
2. `physics_multiplier`  
3. `\bLyapunov\b` / Lyapunov  
4. `market physics` / econophysics / spin glass / Fokker / Kuramoto / percolation (via keyword tool + targeted greps)  
5. Broad `physics` (mostly false positives)

**Result:** **ABSENT-IN-REPO** as QMX design. Survivors are: search keywords in `tools/index_corpus.py`; MQL5 **article title** 15332 in `09_CORPUS_INVENTORY.csv`; OPERATING_LINE instruction not to fixate on physics. Entropy/Hurst/fractal appear only as MQL5 method notes.

**Uncertainty:** whether a sibling Desktop project held Ising/Lyapunov work — **out of scope**; this recovery must not invent it.

---

## U5. Consumer boundary history (C-01)

- Archive delta listed REOPEN: wiki/AD-19 manifest-bounded bots as MIS consumers vs Story 3.2 Book/KSA-only.
- Current ratified docs (DEC-0204, glossary, TN-19, OPERATING_LINE) = **Book + KSA only**.
- **Uncertainty residual:** only if a future sitting reopens bots-as-consumers; treat as **resolved in docs** for recovery purposes, with archive conflict noted.

---

## U6. What "V1 governed producers" already ship in code

- OPERATING_LINE and docs name the seven V1 producers (six rule + fitted).
- This recovery was **docs/research/archive content**, not a production-code inventory (no production code written; git read-only).
- **Uncertainty:** which of identity / spread-state / gap-event / feed-state / SQS / degraded-sensors / liquidity_stress_v1 are **implemented vs designed** on any branch — not verified here beyond planning/docs claims (e.g. tracker parts-bin % is node-wide, not MIS-labeler-specific).

---

## U7. SQS thresholds / hysteresis / outlier numbers

- **Fact:** formula shape and fail-closed sentinel ratified; parameters UI-editable with **no spine defaults**.
- Corpus numbers (e.g. tracker "4-sigma") are **evidence, non-authoritative**.
- **Uncertainty:** operator-chosen live values remain blank/provisional until settings countersign.

---

## U8. Recovered model names without design

Kronos, HMM, BOCPD, MS-GARCH:

- Named repeatedly as **unauthorized** recovered candidates.
- MQL5 notes and file 08 supply **method** detail for HMM/BOCPD/GARCH/MS-GARCH; Kronos is named with **near-zero in-repo design** (tracker + DEC-0262 name only).
- **Uncertainty:** Kronos meaning (pretrained time-series repo vs something else) is not specified in recovered docs.

---

## U9. File 08 stale relative to DEC-0204

- File 08 says Books **and bots** read MIS / MarketView.
- Later law: bots never consume signal snapshot.
- **Inference:** use file 08 for families, look-ahead, registry ideas; **do not** copy its consumer sentence into a sitting.

---

## U10. Scope limits of this recovery

- Did **not** inventory Desktop outside QMX.
- Did **not** hit mql5.com; MQL5 evidence is via existing research notes + local inventory CSV titles.
- Did **not** fully re-read all 3057 corpus articles (prior miners capped at 12+12; ideation +15).
- Did **not** treat `.worktrees/` article bodies as newly mined beyond what research notes already cite.
- `recovery_staging/` was empty at start; no external copies imported.

---

## Confidence summary

| Topic | Confidence |
|---|---|
| MIS = labeler → signal snapshot → Book+KSA | High (ratified) |
| Eight-labeler DEC-0262 catalog | High (ratified) |
| SQS = spread ratio block-only | High (ratified) |
| Shadow lane three-piece seam | High (ratified) |
| Kronos/HMM/BOCPD/MS-GARCH unauthorized | High (ratified) |
| GitBook CT-MIS-01 field inventory | High (archive recovery) |
| MQL5 method primitives | Medium (PLAN notes; untested) |
| lightgbm-multiclass + quiet\|…\|stressed | Low as law (OPERATING_LINE only) |
| Ising / physics_multiplier / Lyapunov design | High **absence** |
| Literal changeover token | High **absence** |
