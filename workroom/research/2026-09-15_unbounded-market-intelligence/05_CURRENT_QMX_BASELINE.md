# 05 — Current QMX baseline: Market Intelligence / regime / placement

**Scope:** Prove the CURRENT QMX MIS / regime / placement baseline from ratified docs and `integration` code. No production edits. No recovered Kronos/HMM/BOCPD/MS-GARCH treated as bound.

**Integration tip (FACT):** `8510c032496bb870824ecc5c4f807e8a4e4f167e`  
(`git rev-parse integration`, 2026-09-15; subject: `story S1: contain generation-gaps test reads against SKY-D325`)

**Main tip at research time (FACT):** `f722694e3c2bd190ce01ea933d7f68f6f9dd66b7` (working tree was `main`; MIS packages live on `integration`).

**How to read this file:** `[FACT]` = cited from docs or `git show integration:…`. `[INFERENCE]` = synthesis across those sources. Code citations use `integration:` paths.

---

## 1. What MIS is (and is not)

| Claim | Grade | Source |
|---|---|---|
| MIS is the trading node's **labeler layer**: per-instant outputs folded into a compute-once **signal snapshot** | FACT | `docs/glossary.md` § MIS; `docs/components/trading-node.md` TN-19 |
| Snapshot consumers are a **closed set**: Book door + KSA **only**; bots never receive it | FACT | glossary § signal snapshot, § MIS; `integration:qmn/src/qmn/mis/signal_snapshot.py` `GovernedConsumer`, `refuse_bot_consumer`; tests `test_book_door_and_ksa_consume_bots_refused` |
| MIS is **not** a QMF V1 library and is **not** `qmf-indicators` | FACT | glossary § MIS |
| MIS does **not** size, switch playbooks, or own entries; a classification score is not a trading edge | FACT / OPERATING_LINE | OPERATING_LINE.md; SQS/AD-39 "sensor computes, transport carries, Book door decides"; regime eval refuses profit/live-authority inference |
| SQS means **Spread Quality Sensor**, distinct from news controls | FACT | `docs/constitution.md` **L23** (DEC-0074); glossary § SQS |

---

## 2. Authority boundaries

### 2.1 Signal snapshot consumers

**[FACT]** Closed enum in code:

- `GovernedConsumer.BOOK_DOOR = "book_door"`
- `GovernedConsumer.KSA = "ksa"`
- `GOVERNED_CONSUMERS = frozenset(GovernedConsumer)`

Source: `integration:qmn/src/qmn/mis/signal_snapshot.py`.

**[FACT]** `consume_signal_snapshot` refuses any other consumer as policy rejection (`refuse_bot_consumer`). Shadow-lane snapshots (`SnapshotLane.SHADOW`) are publish-only — Book door / KSA refuse them.

**[FACT]** Docs: TN-19 — "bots NEVER consume the snapshot — QL-7 callbacks receive only declared footprint evidence" (`docs/components/trading-node.md`).

### 2.2 What SQS may and may not be

| May | May not |
|---|---|
| Be a CT-16 configured producer: `score = historical session-window average ÷ live spread` (exact rational) | Be a regime model, snapshot-quality score, or sizing authority |
| Emit readiness `ok \| not_ready \| unavailable \| stale \| refused` | Use last-known-good on non-ok (non-ok ⇒ hard block) |
| Drive a per-instrument-class **hard-block** with hysteresis + outlier guard | Authorize, size, or block itself — "V1 blocks only" |
| Reach Book door / KSA **only inside** the signal snapshot (one value per instant) | Have a second delivery path |

Sources: constitution L23; glossary § SQS / § SQS baseline; gap-report GAP-0043 (AD-39); `integration:qmn/src/qmn/mis/labelers.py` (`score = baseline ÷ live spread`); TN-8 / TN-19 in trading-node.md.

### 2.3 KSA vs MIS

**[FACT]** KSA = Kill Switch Authority (levels `GREEN|YELLOW|ORANGE|RED|BLACK`). Kill switch is KSA at blocking levels — "sensor-fed, with the MIS snapshot and SQS as **inputs and never authorities**" (glossary § KSA; trading-node TN-7).

**[FACT]** KSA matrix **shape** closed (TN-7); cell **values** still deferred under **GAP-0050**.

### 2.4 Shadow-lane seam

**[FACT]** Three pieces (glossary § shadow-lane seam; TN-19; `integration:qmn/src/qmn/mis/shadow.py`):

1. Candidate registration → CANDIDATE role; identity enters `shadow_composition_fp` only; heavy by construction; not counted toward `max_slice_latency`; drop + `data quality` if past `shadow_lane_publish_bound`.
2. Shadow snapshot stream: own `WriterId`, manifest prefix `mis/shadow/`.
3. Ungoverned comparison projection on evidence channel — gates nothing.

**[FACT]** Wiring a candidate into a governed consumer refuses to boot (`refuse_shadow_governed_wiring`, `SHADOW_ISOLATION_FAILURE_ID`). `SHADOW_HAS_MONEY_PATH_AUTHORITY = False`.

---

## 3. V1 governed producers vs unbound trained classifier

### 3.1 Ratified catalog (docs + code inventory)

**[FACT]** Eight-labeler catalog (DEC-0262 / GAP-0051 / glossary § MIS / ADR-0019):

| # | Producer id | Nature | V1 status |
|---|---|---|---|
| 1 | `identity` | rule-based | **governed** |
| 2 | `spread_state` | rule-based | **governed** |
| 3 | `gap_event` | rule-based | **governed** |
| 4 | `feed_state` | rule-based | **governed** |
| 5 | `sqs` | rule-based (Spread Quality Sensor) | **governed** |
| 6 | `degraded_sensors` | rule-based | **governed** |
| 7 | `liquidity_stress_v1` | fitted (CPU nearest-rank quantile) | **governed** |
| 8 | `regime_classifier_v1` | trained (design story) | **unbound** |

Code constants: `RULE_BASED_PRODUCER_IDS`, `FITTED_PRODUCER_IDS`, `V1_GOVERNED_PRODUCER_IDS`, `REGIME_CLASSIFIER_PRODUCER_ID` in `integration:qmn/src/qmn/mis/catalog.py`.

**[FACT]** `v1_mis_inventory()` returns `regime_classifier_bound: False`, `trained_model_selected: False`, `trained_unbound: ["regime_classifier_v1"]`.

**[FACT]** `refuse_trained_regime_classifier` and governed registration refuse binding `regime_classifier_v1` in V1.

### 3.2 Unauthoritative recovered names

**[FACT]** `UNAUTHORITATIVE_CANDIDATES = {"kronos", "hmm", "bocpd", "ms-garch"}`.  
`refuse_unauthoritative_candidate` policy-rejects them. DEC-0262 / GAP-0051 / ADR-0019: no authority without fresh ratification. **Do not treat as bound.**

---

## 4. `regime_classifier_v1` design on integration (Stories 30.1–30.6)

Docs still say the trained labeler "carries no ratified model family…" (glossary, TN-19, GAP-0051). That is the **ratification / governed-binding** statement.

**[FACT]** On `integration`, Story 30.1 mints a fingerprinted **design-only** artifact that *does* choose a family — without granting money-path or governed binding:

| Dimension | Value | Module |
|---|---|---|
| Chosen family | `lightgbm-multiclass` (`CHOSEN_MODEL_FAMILY`) | `regime_design.py` |
| Design authority | `authority="design-only"`; `grants_money_path_authority=False`; `grants_governed_binding=False` | same |
| Class vocabulary | `quiet \| normal \| elevated \| stressed` | `RegimeClass` / `REGIME_CLASS_VOCABULARY` |
| Exclusion class | `insufficient_evidence` | `LabelContract` / `regime_labels.py` |
| Sessions | `asia`, `london`, `new_york` | `TradingSession` / `DECLARED_TRADING_SESSIONS` |
| Label method | `forward-realized-range-quantile-buckets` | horizon 12 M5 bars; quantile edges 0.25/0.50/0.75 |
| Bar interval / lookback | M5; 730 calendar days; warm-up 120 bars | `DataWindowContract` |
| Instruments scope | `fx-majors-declared-roster` | same |
| Splits | time-ordered non-overlapping 60/20/20; holdout sealed; shuffle forbidden | `SplitStrategy` |
| Leakage laws | as-of only; no future bars; no forming bar; no sealed-holdout peek; no post-event revision; no live outcome in train; purge=12; embargo=12; synthetic edge forbidden; calendars named apart (market-hours / day-boundary / news) | `LeakageControls` |
| Imbalance | `class-weight-balanced` + `exclude-insufficient-evidence` | |
| Training location | `operator-machine-offline-script` | also `regime_train.TRAINING_LOCATION` |
| Default seed / RNG | `DEFAULT_TRAINING_SEED = 30_04_2026`; `RNG_ALGORITHM = "python-random-Random"` | `regime_train.py` |
| Recovered families | Kronos/HMM/BOCPD/MS-GARCH evaluated, `authority="none"`, not selected; online-river rejected | `evaluate_candidate_families()` |
| Eval refusals | refuse profit inference; refuse live-authority inference; refuse holdout leak; refuse post-hoc threshold | `EvaluationContract` / `regime_eval.py` |
| Registration | may record artifacts; **forbidden** statuses `governed\|ratified\|active`; never mutates `composition_fp`; no live consumer binding | `regime_register.py` |

**[INFERENCE]** Docs "no ratified model family" and code `CHOSEN_MODEL_FAMILY` are consistent if "ratified" means governed/live authority. Design selection ≠ governed binding. GAP-0051 remains the gap for training/shadow-rollout **promotion into live**.

---

## 5. ALREADY_IMPLEMENTED vs DESIGNED_BUT_NOT_GOVERNED vs GENUINE_GAP

### ALREADY_IMPLEMENTED (on `integration` code + ratified V1 docs)

- Signal snapshot mint / freshness / consume (`signal_snapshot.py`, Story 26.3).
- Six rule-based labelers + SQS hard-block path (`labelers.py`, Story 26.17).
- Fitted `liquidity_stress_v1` (`liquidity.py`).
- Governed producer catalog + refuse trained/unauthoritative (`catalog.py`).
- Shadow seam: candidate catalog, publish, compare, isolation refusals (`shadow.py`, Story 26.18 / TN-19).
- Authority tests: bots refused; shadow not consumed; composition_fp stable when candidates change; Kronos/HMM/BOCPD/MS-GARCH refused (`test_qmn_mis_*.py`).
- Constitutional L23 SQS naming; AD-39 formula posture in docs.

### DESIGNED_BUT_NOT_GOVERNED (code exists; no money-path / governed binding)

- Fingerprinted `regime_classifier_v1` design (`regime_design.py`, Story 30.1).
- Offline corpus acquire/clean/split (`regime_corpus.py`, 30.2).
- Deterministic label generation + audit (`regime_labels.py`, 30.3).
- Offline train script + provenance / refusals for VPS/cloud/live-network/credentials (`regime_train.py`, 30.4).
- Offline evaluation separated from train (`regime_eval.py`, 30.5).
- Registry lineage registration as **sandbox / non-authoritative** candidate (`regime_register.py`, 30.6).
- Shadow lane ready to receive a candidate drop without re-architecture (TN-19 / DEC-0204).

### GENUINE_GAP (deferred / open; not closed by Stories 30.x alone)

| Gap | Status | Content |
|---|---|---|
| **GAP-0051** | deferred | MIS labeler train + shadow-rollout: data window/seed/fp1 recording, model registration, **promotion cadence**, re-certification over one affected-Book cycle; ML on live path; quarterly cloud training |
| **GAP-0050** | deferred | KSA effect-matrix **values** (shape closed) |
| **GAP-0058** | open (in scope) | Placement variants (single-machine co-location with agentic system, self-setup) |
| Glossary / TN-19 wording | tension | Still says trained labeler has "no ratified model family" while integration holds a design-only family choice — update owed when/if design is ratified into governed process |

**[FACT]** GAP-0051 recommendation: last trading-node epic; offline operator-machine script; parallel branch OK until shadow consumes candidate (`docs/gap-report.md`, ADR-0019 DEC-0261/0262).

---

## 6. Placement (related, not MIS core)

**[FACT]** V1 node placement: Trading VPS systemd service; evidence tier co-located; second VPS deferred (GAP-0055). Single-machine variant open under GAP-0058 (DEC-0262). MIS training explicitly **not** on trading VPS (`refuse_vps_or_cloud_training`).

---

## 7. Source index

| Kind | Path |
|---|---|
| Glossary | `docs/glossary.md` — MIS, signal snapshot, SQS, SQS baseline, candidate labeler, shadow-lane seam, KSA |
| Gap | `docs/gap-report.md` — GAP-0043 (SQS), GAP-0050, **GAP-0051**, GAP-0058 |
| Constitution | `docs/constitution.md` — **L23** |
| Component | `docs/components/trading-node.md` — TN-7 KSA, TN-8 SQS, **TN-19** MIS/shadow |
| ADR | `docs/decisions/ADR-0019-trading-node.md` |
| Code (integration) | `qmn/src/qmn/mis/{__init__,catalog,signal_snapshot,labelers,liquidity,shadow,regime_design,regime_corpus,regime_labels,regime_train,regime_eval,regime_register}.py` |
| Tests (integration) | `qmn/tests/test_qmn_mis_{signal_snapshot,producers,shadow,regime_design,regime_register,…}.py` |

---

## 8. One-paragraph baseline

**[INFERENCE from facts above]** QMX MIS today is a **governed sensor/labeler seam**, not a regime trading brain. V1 money-path producers are six rule-based labelers plus fitted `liquidity_stress_v1`, folded into an immutable frontier-bound signal snapshot that only the Book door and KSA may consume; SQS is block-only Spread Quality Sensor. The shadow-lane seam is built. `regime_classifier_v1` has a full offline design/train/eval/register pipeline on integration with chosen family `lightgbm-multiclass` and classes `quiet|normal|elevated|stressed`, but remains unbound and non-authoritative on the live path. GAP-0051 still owns promotion into governed/shadow-live use. Recovered Kronos/HMM/BOCPD/MS-GARCH stay unauthoritative.
