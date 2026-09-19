# Recovered artifact index — MIS / regime / SQS / shadow

Indexed by theme. Paths are absolute under `C:\Users\Mubarak\Desktop\QMX`. All entries are in-repo-only.

---

## A. Ratified law (docs/)

| Artifact | What it recovers |
|---|---|
| `docs/glossary.md` — MIS, signal snapshot, shadow-lane seam, candidate labeler, SQS, SQS baseline, window kinds | Canonical vocabulary + DEC-0262 eight-labeler catalog |
| `docs/components/trading-node.md` — TN-19 | MIS seam mechanics; shadow pieces; SQS-in-snapshot; consumers |
| `docs/changelog.md` — DEC-0262 block | Labeler catalog; training last; unauthorized Kronos/HMM/BOCPD/MS-GARCH |
| `docs/gap-report.md` — GAP-0051, GAP-0043, GAP-0042, DEC-0073 | Training deferred; SQS formula; handover windows; dead Snapshot Quality reading |
| `docs/decisions/ADR-0019-trading-node.md` | MIS training + catalog restatement |
| `docs/constitution.md` L23 | SQS = Spread Quality Sensor ≠ news |
| `docs/AGENTS.md` | Node ratified vs deferred (incl. GAP-0051) |
| `docs/contracts/ct-31-control-window.yaml` | `news` / `daily_dead_zone` / `session_handover_buffer` |
| `docs/registry/variables.yaml` | `session_handover_buffer_*`, SQS-related node variables |
| `docs/scenarios/SCN-0008-pair-scoped-news.md` | Window kinds in scenario form |
| `docs/architecture/overview.md` | Placement variants + risk/SQS pointers |

---

## B. Research / PLAN notes (workroom/research/)

| Artifact | What it recovers |
|---|---|
| `workroom/research/08-mis-ml-regime-models.md` | Five regime families; look-ahead trap; LightGBM/registry/shadow prior art; MarketView draft |
| `workroom/research/2026-09-09_mql5-mis-regime-notes.md` | 12 MQL5 full reads; MIS candidate primitives; SQS boundary; ablation order |
| `workroom/research/2026-09-09_mql5-mis-scalp-notes.md` | 12 MQL5 scalp/micro reads; spread/news/session/exec_ok primitives |
| `workroom/research/2026-09-09_mis-scalping-ideation.md` | Ratified vs GitBook vs ideation; Epic 26/30 split; class-vocab conflicts |
| `workroom/research/00-qmf-synthesis-module-map.md` | `qmf.mis` synthesis map (stale bot-consumer sentence flagged elsewhere) |
| `workroom/research/09-experimentation-search-overfitting.md` | Search discipline for later regime experiments |
| `workroom/research/10-macro-micro-analysis-data.md` | Spread as micro priority; PIT two-timestamp rule |
| `workroom/research/2026-09-15_unbounded-market-intelligence/OPERATING_LINE.md` | This-session operating corrections + integration claim |
| `workroom/research/2026-09-15_unbounded-market-intelligence/09_CORPUS_INVENTORY.csv` | Local MQL5 inventory (incl. Lyapunov article **title** row 15332) |
| `workroom/research/2026-09-15_unbounded-market-intelligence/tools/index_corpus.py` | Keyword list including Ising/Lyapunov (search tool only) |

---

## C. Archive recovery (trading-node-delta + transcripts)

| Artifact | What it recovers |
|---|---|
| `archive/recovery/trading-node-delta/trading-node-delta.md` | B-06 MIS/SQS baseline; K-38..K-42; R-08/R-09; C-01; D-09 |
| `archive/recovery/trading-node-delta/recovery-lineage-addendum.md` | SQS ratio formula candidate; reject snapshot-quality aggregate |
| `archive/recovery/trading-node-delta/restart-handoff.md` | Restart constraints + open MIS-consumer question |
| `archive/recovery/trading-node-delta/work/gitbook-baseline.md` | CT-MIS-01 field inventory (`spread_state`, optional `regime`) |
| `archive/recovery/trading-node-delta/work/bmad-supplement.md` | Story notes: regime_classifier_v1 degradation; snapshot_quality_score_v1 |
| `archive/trading-node.txt` | Dictation: MIS training last; Kronos; shadow; SQS; assembler dead |
| `archive/qmf-5.txt` | Order-path / MIS-firing / SQS / assembler vocabulary dig |

---

## D. Tracker

| Artifact | What it recovers |
|---|---|
| `tracker/trading-node-notes.md` | SQS V1 adopted; MIS→KSA funnel; MIS models last epic; Kronos unauthorized; MIS assembler never existed |
| `tracker/map.md` | Early MIS/SQS/Kronos+BOCPD leads (partially superseded) |
| `tracker/tickets/001-qmf-research-sweep.md` | Points at research file 08 as MIS/ML dig |
| `tracker/tickets/002-qmf-minimal-core.md` | Heavy indicators in MIS; SQS separate from news |
| `tracker/tickets/004-trading-node-spec.md` | Node re-spec includes MIS/SQS |
| `tracker/tickets/005-data-architecture.md` | MIS snapshots kept raw; news ≠ SQS |
| `tracker/tickets/008-backtesting-framework.md` | SQS reverse-engineered into backtest conditions (ticket note) |

---

## E. Docwork / harvest / planning

| Artifact | What it recovers |
|---|---|
| `_docwork/gaps.yaml` — GAP-0051 | Catalog note with eight labelers |
| `_docwork/extractions.yaml` — EXT-2171 area | DEC-0262 MIS models + training script shape |
| `_docwork/ledger.yaml` — DEC-0262 | Placement variants + MIS catalog |
| `_docwork/analysis/cross-source-reconciliation.md` | MIS node-owned; SQS semantic correction |
| `_docwork/analysis/qmf1-supersession-audit.md` | Snapshot-quality SQS zombie dead |
| `_docwork/harvest/SRC-02-extractions.yaml` | SQS; Kronos/BOCPD; book-specific MIS models question |
| `_bmad-output/planning-artifacts/epics.md` — Epic 26 / Epic 30 | Shadow seam + regime_classifier_v1 design/train/shadow/recert |
| `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/trading-node-corpus-brief.md` | CT-MIS-01 recovered payload restatement |

---

## F. Absences (explicit)

| Missing design object | Searches / notes |
|---|---|
| Ising model / spin-glass MIS | `\bIsing\b` — only `tools/index_corpus.py` keyword |
| `physics_multiplier` | Zero hits |
| Lyapunov as QMX producer | Inventory title 15332 + keyword list only |
| Literal token `changeover` | Absent; use `session_handover_buffer` / BOCPD |
| Ratified `lightgbm-multiclass` + `quiet\|normal\|elevated\|stressed` | Only in `OPERATING_LINE.md` in this checkout |

---

## G. This recovery folder outputs

| Artifact | Role |
|---|---|
| `01_RECOVERY_MANIFEST.csv` | Path inventory with confidence/type |
| `02_RECOVERED_MARKET_PHYSICS.md` | Full stack writeup (physics section = absences + thin hits) |
| `03_RECOVERED_ARTIFACT_INDEX.md` | This index |
| `04_RECOVERY_UNCERTAINTIES.md` | Conflicts, absences, OPERATING_LINE vs docs |
