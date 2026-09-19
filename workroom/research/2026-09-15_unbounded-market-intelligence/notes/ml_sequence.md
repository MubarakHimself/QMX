# ML / clustering / sequence / boosting / ONNX — corpus notes

**Date:** 2026-09-15  
**Family shard:** `ml_sequence`  
**Corpus:** `.worktrees/mql5-library/data/mql5-library/` (on-disk markdown only)  
**Outputs:** `extractions/ml_sequence.jsonl`, this file  
**Constraint:** no production code; read-only git; no mql5.com  

## QMX design anchor (evaluate against, do not force)

From `OPERATING_LINE.md` / integration design seams:

| Knob | Current design |
|---|---|
| Producer | `regime_classifier_v1` (GAP-0051; unbound) |
| Family | `lightgbm-multiclass` |
| Classes | `quiet \| normal \| elevated \| stressed` |
| Training | offline operator-laptop |
| Online / river | **no** |
| Authority from design | **no** (shadow/register only) |
| Recovered alternatives | Kronos / HMM / BOCPD / MS-GARCH — **unauthoritative** |

MIS emits labels to Book door + KSA. Classification ≠ edge. MIS does not size or switch playbooks.

Prior full-reads to go beyond (24 IDs): regime notes + scalp notes — **none** of the IDs below are in that set.

## Coverage method

- Coverage.md lists only **21** articles in section `Machine learning`. Most ML content is mis-sectioned under Trading systems / Trading / Examples / Tester / Integration / Statistics.
- Title lead map: ~370 ok articles touch ML-ish title/description needles.
- This pass **full-read 40** ML-ish articles (see jsonl), spanning boosting, labeling hygiene, clustering, ONNX, sequence/LSTM/GRU, Kronos, online learning, HMM, meta-labeling, self-supervised features.

## Brief table (selected)

Paths under `C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/`.

| id | method | vs lightgbm-multiclass | leakage / artifact watch | MIS cut |
|---|---|---|---|---|
| 14926 | LightGBM/XGBoost tutorial → ONNX | **Supports chosen family** (binary demo → needs multiclass+purge) | weak CV; ONNX good | shadow family confirm |
| 23488 | catch22 features + vol-regime labels | **Best parallel** to quiet…stressed | purge+embargo+train-only terciles | feature pack candidate |
| 20117 / 22040 / 21938 | purged HPO, nested CV, calibration | hygiene for LightGBM train/eval | purge present; no Sharpe-as-HPO | train/eval tooling |
| 19850 / 20059 / 23137 / 22912 | concurrency, sequential bootstrap, bagging regimes | not a family swap; sampler hygiene | overlapping labels without uniqueness leak | label/train weights |
| 18864 / 19253 / 22274–22755 | triple-barrier + meta-label filters | meta-label ≠ regime ontology | forward labels need purge | **bot/Book filter**, not MIS |
| 11147 / 8657 / 16487 | CatBoost (+ ONNX) | **sibling GBDT candidate** | **11147 shuffle=True** | bake-off only |
| 8642 | naive CatBoost | anti-pattern | **shuffle=True** hard fail | do not copy |
| 12373 / 12433 / 22474 / 13451 / 21954 | ONNX infra / LSTM pipeline | runtime path for frozen models | shuffle in MQ demos; double-scale trap | artifact parity |
| 23304 | Kronos native MQL5 port | **candidate family** (heavy) | flat `.bin` offline export; not ONNX | unauthoritative recovered |
| 23700 | online SGD logistic filter | **conflicts** with no-online design | online weights on host/VPS | reject for regime_v1 |
| 10785 / 10947 / 10943 / 11615 / 14548 / 12261 | k-means / HDBSCAN / SOM | label-discovery / features | time-ignorant clustering risk | exploratory; no auto-authority |
| 15033 | HMM JSON export | recovered alternative | **JSON not pickle** | unauthoritative shadow |
| 20343 | oscillator labels w/o look-ahead | label lesson for any family | look-ahead is the bug class | label design |
| 22516 | session Fourier features | feature pack for LightGBM | `shift(1)` on session vol | MIS time features |
| 24057 | denoise/detone/ONC cluster features | preprocess not classifier | MP effective-N trap | offline feature hygiene |
| 20514 | self-supervised corr features | feature candidate into LightGBM | author long-holdout claim | offline features |
| 23633 | Tsetlin machine | interpretable alt family | weak purge story | shadow bake-off |
| 14113 | GRU/LSTM ONNX | sequence forecast bots | shuffled split | not MIS regime |

## Findings vs chosen LightGBM design

### What supports keeping `lightgbm-multiclass`

1. **14926** (Statistics section, not Machine learning): GBDT still the practical tabular workhorse; ONNX export into MQL5 is documented. Maps cleanly to offline laptop train → frozen artifact → inference.
2. **Blueprint hygiene series** (19850, 20059, 20117, 21938, 22040, 21954, 22912, 23137): if QMX trains LightGBM on financial labels, it should inherit **purged/embargoed CV**, concurrency-aware weights, nested eval, and calibration — not sklearn `train_test_split`.
3. **23488**: vol-regime classification with catch22 features is the closest *task* match to `quiet|normal|elevated|stressed`. Leakage controls are explicit (chronological split, purge, embargo, stride, train-only thresholds). Prefer pairing those features/controls with LightGBM rather than inventing a new live family.
4. **22516** + **24057**: session-aware features and correlation denoising/clustering are **preprocess** upgrades, not reasons to abandon GBDT.

### Better / alternate families (candidates — with implications)

| Candidate | Why it appeared | Leakage implications | Authority implications |
|---|---|---|---|
| **CatBoost multiclass** | 8657, 11147, 13648, 16487 | Same as LightGBM if purged; **reject shuffled splits** (11147/8642) | Still frozen offline artifact; no auto-governed bind |
| **Kronos foundation / embeddings** (23304) | Native port; recovered name in OPERATING_LINE | Pretrain ≠ label leak, but forecast heads need honest OOS; weekday/TZ traps | **Unauthoritative**; heavy; MIS must not emit directional forecast as door truth |
| **Gaussian HMM** (15033; prior 16830) | JSON freeze-and-ship | Observation choice can correlate with state (author caveat in 16830) | Remains unauthoritative recovered |
| **k-means / HDBSCAN / SOM clusters** (10785–11615, 14548, 12261) | Unsupervised regime discovery | Time-ignorant cluster fit; cluster→trade maps leak if fit on futures | Clusters need design ratification; never silent playbook switch |
| **Online logistic / river-like** (23700) | Adapts under regime shift | Feedback loop OK for *trade filters*; wrong for PIT regime labels | **Reject for regime_classifier_v1** under no-online / no-VPS-training stance; authority drift hazard |
| **Tsetlin** (23633) | Interpretable rules | Needs same purge discipline as any supervised model | Interpretability ≠ authority |
| **Self-supervised features** (20514) | Broker-only pretext features | Pretext must be causal | Feature input to LightGBM only |
| **GRU/LSTM/Transformer forecast** (14113, 12373, 12433, 22474, …) | Sequence modeling common in corpus | Frequent shuffled splits in demos | Bot-layer forecast — not MIS 4-class state |

**Do not force every article into LightGBM.** The table above records real alternatives. None displace the design choice without a new sitting; several are useful as **features, hygiene, or shadow bake-offs**.

## Leakage / artifact watch (corpus patterns)

### Hard fails observed (do not copy)

- **`train_test_split(..., shuffle=True)` on bars:** `md/8642.md`, `md/11147.md`, and several ONNX demos (`12373`, `12433`, `14113`).
- **Naive future-move labels** without purge/embargo.
- **Partial pipeline parity:** Python scales/PCA one way, MQL5 another (`22474`, `21954` double-scale warning).

### Gold-standard patterns to steal for QMX

- Chronological split + **purge + embargo** + non-overlapping stride + **train-only** label thresholds (`23488`).
- PurgedKFold inside Optuna; forbid equity-Sharpe as HPO objective (`20117`).
- Nested CV so selection does not touch final test (`22040`).
- Label concurrency / uniqueness weights (`19850`, `20059`, `23137`).
- Explicit look-ahead-free labeling (`20343`, `22516` `shift(1)`).
- **Text/JSON/ONNX/flat-bin artifacts over pickle** for anything crossing into the terminal (`15033` JSON, `23304` `.bin`, ONNX series). Pickle may exist inside Python tooling only.

### VPS training

- QMX forbids training on VPS for this design.
- Corpus often shows MetaQuotes **VPS hosting chrome** adjacent to articles; that is not a method recommendation.
- **23700** is the substantive conflict: online updates wherever the EA runs (including VPS) — reject for `regime_classifier_v1`.

## Authority / placement cut

| Pattern in articles | QMX placement |
|---|---|
| Offline multiclass regime/vol-state scores | MIS shadow → maybe later governed labeler |
| Meta-label take/skip / bet sizing | **Bot / Book** — never MIS |
| Cluster id / HMM state / Kronos embedding | MIS only if design-ratified sensor; default shadow |
| Online self-updating weights | **Forbidden** for regime_classifier_v1 |
| ONNX/JSON/.bin freeze-and-ship | Required artifact discipline for any family |
| Playbook switch from model state | **Forbidden** inside MIS (seen as EA pattern in clustering “practical use”) |

## Mis-sectioned ML worth knowing

Machine learning section is tiny (21). High-signal ML for this shard lived in:

- **Trading systems:** Blueprint 8/12/16–20, Kronos, clustering practical, catch22, meta-label ADX/BB, session features, CatBoost CV/ONNX  
- **Statistics and analysis:** LightGBM/XGBoost (14926)  
- **Trading / Examples / Tester / Integration:** labeling parts, ONNX primers, GRU/LSTM, HMM, naive CatBoost  

## Full-read ID list (this shard)

```
10785 10943 10947 11147 11615 12261 12373 12433 13451 13648
13915 14113 14548 14926 15033 16487 18864 19253 19850 20059
20117 20343 20514 21938 21954 22040 22274 22474 22516 22754
22755 22912 23137 23304 23488 23633 23700 24057 8642 8657
```

**n = 40**, all beyond the prior-24 regime/scalp set. Structured rows: `extractions/ml_sequence.jsonl`.

## Bottom line for `regime_classifier_v1`

- **Keep** `lightgbm-multiclass` as the design family; corpus supports GBDT + ONNX/text freeze for tabular regime/vol-state labels.
- **Upgrade** train/eval with Blueprint + catch22 hygiene (purge/embargo/concurrency/train-only thresholds/session features/corr denoising) — these are not optional cosmetics.
- **Record** CatBoost, Kronos embeddings, HMM, HDBSCAN/k-means, Tsetlin, self-supervised features as **candidates** with the leakage/authority notes above; none are governed.
- **Reject** online-river/SGD-in-EA and shuffled bar splits for this producer.
- **Never** promote a classification score to Book authority, sizing, or playbook switch from MIS.
