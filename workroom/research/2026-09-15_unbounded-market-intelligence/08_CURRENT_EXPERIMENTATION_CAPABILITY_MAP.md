# 08 — Current experimentation capability map

What QMX can already do for **regime / placement / experiment** work, vs what is design-only or deferred. Docs + `integration` tree. No production code from this note. Pair with `06_QMX_AUTHORITY_AND_DATAFLOW.md` and `OPERATING_LINE.md`.

Stamp note: many contracts are `source-inspected` on `integration@1b451a8` (DEC-0286) — matching source exists; **not** end-to-end demonstrated. Remaining connect work is factory work.

---

## 1. Experiment lanes (product face)

| Lane | Door | Writes | Artifact | Use for regime research |
|---|---|---|---|---|
| **Ungoverned** | `qmb.run()` / ordinary Python / `import qml` | Nothing governed | Return values only | Prototype labelers, filters, notebooks |
| **Governed** | QMB orchestrator / CLI spawn (not CT-47) | 1 ledger line + 1 CT-32 | research-paper (`world=replay`) | Comparable Bot×Book runs; confirmation role when adapters match |
| **Coordinated** | QMA Backtesting Service → CT-47 → one `qmb` CLI/MCP per env | Same QMB evidence + Experiment Ledger `_ref` | Spec-bound campaign | Multi-run campaigns; QMA never `import qmb` |

Source: `docs/scenarios/SCN-0015-three-experiment-lanes.md`, DEC-0270, `docs/components/qmb.md` workbench section.

`workbench_lane` is **metadata** on ledger / Experiment Ledger — **not** a CT-32 field (DEC-0283).

---

## 2. QMB surfaces on `integration` (`qmb/src/qmb/`)

| Module | Capability | Regime/placement relevance |
|---|---|---|
| `runloop/` | Event-slice loop, frontier clock, warm-up, forming-bar lock | Same loop QMN drives via `run_slice` — placement parity seam |
| `config/` | Resolved run-config compiler; Book/BMS fragments; `assignment_is_canonical` | Bind Book doors (incl. SQS modeled-spread in replay — GAP-0048 open) |
| `execution/` | Fill / slip / cost / financing ports | Fidelity still `optimistic`-tainted until GAP-0048 |
| `optimize/` | Declared parameter space, Optuna adapter (`n_jobs=1`), sensitivity | Search over **bot params** (same `fp1`); not regime model search |
| `sweep/` | Axes, batch, admit, rank | Cartesian bot×symbol×BarSpec×params; `sweep.rank` = readout |
| `robustness/` | Shuffle, perturbation, significance, walk-forward | Robustness-only claim class; not edge |
| `analysis/` | `project`, `rerun`, `compare`, Book/BMS variants | Projection **forbids** size/R/Book rescale; path-dependent → `rerun` |
| `results/` | CT-32 producer | Admission evidence container |
| `ledger/` + `orchestrator/` | Pure run / impure spawn, governor, one ledger line | Lane boundary enforcement |
| `registryread/` + `library` | As-of sets; library projections over `fp1` kinds | Candidate Book/BMS/Bot discovery |
| `data/` | Thin fronts over `qmf-data` | Download-once rooms; no second store |
| `doors/` | CLI (product face), API, MCP stub | Platform single CLI = `qmb` |
| `workbench.py` / `paper.py` | Workbench composition helpers | Lane/paper trinity plumbing |

Examples present: `optimize_*`, `sweep_*`, `robustness_*`, `analysis_*`, `orchestrator_*`, `library_*` under `qmb/examples/`.

**Explicit non-capabilities (QMB):** no venue; no bench/promote/bind; no structure **generation** inside QMB (generation = QML); no CT-32 extension with `lane`/`analysis_method`.

---

## 3. QML surfaces on `integration` (`qml/src/qml/`)

| Module | Capability |
|---|---|
| `declaration/` | CT-33 / CT-34 author types |
| `families/` | Strategy-family helpers (key only) |
| `footprint/` | Producer bindings / templates |
| `protocol/` | Bot runtime protocol |
| `conformance/` | Layer-1/2 + prediction linter checks |
| `generation/` | Generation write-ownership seam (algorithm GAP-0063) |
| `logic/` / `host/` | Logic + host adapters |

**For regime research:** bots declare **footprint producers** (CT-16/CT-17). They do **not** declare MIS snapshot consumption. Putting regime into a bot footprint would violate the closed MIS consumer set unless the design is amended at spine level — out of scope for a research patch.

---

## 4. QMN / MIS surfaces on `integration` (`qmn/src/qmn/mis/`)

| File / area | Status for experimentation |
|---|---|
| `signal_snapshot.py` | Governed artifact shape; consumers Book door + KSA |
| `catalog.py` | V1 inventory: six rule-based + `liquidity_stress_v1`; refuses trained `regime_classifier_v1` bind; unauthoritative candidates named |
| `labelers.py` | Rule-based labeler implementations |
| `liquidity.py` | Fitted `liquidity_stress_v1` |
| `shadow.py` | Shadow-lane seam (candidate vs governed diff) |
| `regime_design.py` | Fingerprinted design: family `lightgbm-multiclass`; classes `quiet\|normal\|elevated\|stressed`; **mints no weights** |
| `regime_corpus.py` / `regime_labels.py` | Corpus / label seams |
| `regime_train.py` / `regime_eval.py` / `regime_register.py` | Train / eval / register seams (offline epic; GAP-0051) |

Related node modules (execution context, not experiment engines): `seats/`, `order/`, `protection/` (KSA), `venue/`, `replay/` (decision-diff only; no fill sim), `doors/`, `loop/`.

**OPERATING_LINE.md alignment:** integration has design/corpus/labels/train/eval/register/shadow seams; chosen family `lightgbm-multiclass`; recovered Kronos/HMM/BOCPD/MS-GARCH unauthoritative; classification ≠ edge.

---

## 5. QMF packages supporting experiments (`packages/` on `integration`)

| Package | Experiment-facing surface |
|---|---|
| `qmf-core` | Exact money/time, `fp1`, refusals, clock/sink protocols |
| `qmf-data` | Rooms, splits, journal, ingest, Dukascopy/calendar fronts |
| `qmf-registry` | Records, lineage, promotion skeleton; owns CT-33/34 kinds |
| `qmf-indicators` | CT-16 two-mode producers (SQS lives here as configured producer) |
| `qmf-structure` | CT-17 causal structure |
| `qmf-risk` | CT-22..32 value types: door, binding, exit, performance, paper, control |
| `qmf-venue` | CT-18..21 shapes; **only QMN wires** |

No QMF package trains MIS models (`docs/architecture/stack.md` — Model training: none).

---

## 6. Analysis methods (named)

| Method | Kind | May change size/R/Book? | Artifact |
|---|---|---|---|
| `analysis.project` | Projection saved view | **Forbidden** | Canonical JSON view; claim-class `projection` |
| `analysis.rerun` | Path-dependent new run | Yes (new run-config) | New CT-32 |
| `compare_runs` | Readout | No | Nothing stamped |

DEC-0273; `docs/components/qmb.md`.

---

## 7. Validation ladder (library; CLI coverage uneven)

Documented as QMB library functions (B-14): backtest, optimize, Monte Carlo (trade-shuffle / block-bootstrap), rule-significance, walk-forward.

On `integration@1b451a8` docs note: **robustness often library-only on CLI**; full sweep `batch`/`rank` CLI coverage may still be connect work (DEC-0281 / DEC-0286). Treat CLI gaps as wiring, not missing design.

---

## 8. What regime researchers can do *now* vs later

### Available now (design + source seams)

1. Prototype regime/placement **features** in ungoverned Python against `qmf-data` rooms / CT-16 producers.
2. Treat SQS / spread-state / gap / feed / liquidity_stress as **block-or-label** inputs to Book/KSA — not bot alpha.
3. Use QMB governed runs to measure **Bot×Book** behavior under different Book door policies (windows, SQS thresholds) — still not “regime owns size”.
4. Use shadow-lane design: register **candidate** labelers; compare to governed snapshot; gate nothing.
5. Author `regime_classifier_v1` **design/corpus/label/train/eval** offline scripts on the existing `qmn.mis.regime_*` surfaces (GAP-0051 epic posture).

### Not available / refused by law

1. Bot consumption of MIS snapshot.
2. Classifier-driven sizing or playbook switch.
3. Claiming edge from optimistic-tainted or synthetic (`world=simulated`) runs.
4. Binding trained `regime_classifier_v1` as governed producer without ratification → version bump → re-certification.
5. Treating Kronos/HMM/BOCPD/MS-GARCH as authoritative without fresh ratification.
6. QMA placing orders or “QMA-paper”.
7. Node replay as governed fill-simulation evidence (decision-diff only).

### Deferred content that blocks *claims*, not *exploration*

| Gap | Blocks |
|---|---|
| GAP-0048 | Honest fill/spread fidelity; unlocks non-optimistic claims; modeled-spread vs DEC-0153 freshness |
| GAP-0049 | SR* / search thresholds / pass batteries |
| GAP-0016/0017 | Registration causality *gate* (prevention already in QMB) |
| GAP-0051 | Live governed trained regime producer + promotion cadence |
| GAP-0050 | Concrete KSA effect-matrix values (shape exists) |

---

## 9. Suggested experiment shapes that respect authority

| Shape | Lane | Output | Does not claim |
|---|---|---|---|
| Label agreement study (rule vs candidate regime) | Ungoverned or shadow | Confusion / transition matrices | Edge, size |
| Entry-veto counterfactual via Book door thresholds | Governed `analysis.rerun` | New CT-32 under altered Book fragment | That MIS “found alpha” |
| Placement filter: session × spread-state × feed_state | Governed confirmation when ready | Per-requirement bar folds | Playbook ownership |
| Offline LightGBM train on recorded windows | Offline script (GAP-0051) | Registered model artifact + design `fp1` | Live bind until ratified |

---

## 10. Path checklist

- Docs: `docs/components/qmb.md`, `qml.md`, `trading-node.md`, `qmf-risk.md`, `qmf-indicators.md`
- Lanes: `docs/scenarios/SCN-0015-three-experiment-lanes.md`
- ADRs: `ADR-0017`, `ADR-0018`, `ADR-0019`, `ADR-0022`
- Gaps: `docs/gap-report.md` (GAP-0048/49, 0050/51, 0016/17, 0063, 0085)
- Code trees: `qmb/src/qmb/{runloop,optimize,sweep,robustness,analysis,orchestrator,results}`, `qml/src/qml/*`, `qmn/src/qmn/mis/*`, `packages/qmf-*`

---

## 11. Bottom line

Experimentation machinery for **Bot×Book replay**, sweeps, robustness, and **MIS labeler shadowing** exists as designed surfaces (much `source-inspected`). The regime classifier is a **fingerprinted design + offline seams**, not a live trading authority. Placement research should target **Book-door / KSA consumption of snapshot labels**, not bot-side profitability or sizing smuggling.
