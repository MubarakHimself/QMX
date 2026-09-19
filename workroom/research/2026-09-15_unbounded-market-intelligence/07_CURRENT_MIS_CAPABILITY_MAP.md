# 07 — Current MIS capability map

**Companion to:** `05_CURRENT_QMX_BASELINE.md`  
**Integration SHA (FACT):** `8510c032496bb870824ecc5c4f807e8a4e4f167e`  
**Legend:** `AI` = ALREADY_IMPLEMENTED · `DNG` = DESIGNED_BUT_NOT_GOVERNED · `GG` = GENUINE_GAP · `UA` = UNAUTHORITATIVE (must not be treated as bound)

---

## A. Capability matrix

| Capability | Status | Evidence (path / DEC) | Notes |
|---|---|---|---|
| Signal snapshot mint (immutable, environment-keyed, frontier-bound) | **AI** | `integration:qmn/src/qmn/mis/signal_snapshot.py`; TN-19; DEC-0204/0230 | Format version 1; requires SQS slot on governed lane |
| Snapshot freshness = Book `decision_freshness_bound` only | **AI** | `check_snapshot_freshness`; glossary § signal snapshot | No second bound; stale ⇒ refuse |
| Consume: Book door | **AI** | `GovernedConsumer.BOOK_DOOR`; TN-19 | Closed set |
| Consume: KSA | **AI** | `GovernedConsumer.KSA`; TN-7 | Snapshot/SQS are inputs never authorities |
| Consume: bots | **refused** | `refuse_bot_consumer`; tests | Policy rejection |
| Consume: shadow snapshot by Book/KSA | **refused** | `SnapshotLane.SHADOW` path in `consume_signal_snapshot` | Publish-only |
| Producer: `identity` | **AI** | `labelers.py` / `catalog.py` | Rule-based |
| Producer: `spread_state` (`normal\|elevated\|extreme`) | **AI** | same | Rule-based |
| Producer: `gap_event` | **AI** | same | Rule-based |
| Producer: `feed_state` (`live\|degraded\|dead`) | **AI** | same + snapshot `CanonicalFeedState` | Rule-based |
| Producer: `sqs` (Spread Quality Sensor) | **AI** | `evaluate_sqs`; L23; AD-39; GAP-0043 | Block-only; baseline÷live |
| Producer: `degraded_sensors` | **AI** | `evaluate_degraded_sensors` | Rule-based |
| Producer: `liquidity_stress_v1` | **AI** | `liquidity.py` | Fitted CPU quantile — **not** trained ML |
| Producer: `regime_classifier_v1` governed bind | **DNG / refused on V1 catalog** | `refuse_trained_regime_classifier`; `v1_mis_inventory` | Unbound |
| Shadow candidate registration | **AI** | `shadow.py` `register_shadow_candidate` | Separate `shadow_composition_fp` |
| Shadow publish + comparison projection | **AI** | `publish_shadow_snapshot`, `compare_shadow_to_governed` | Ungoverned; gates nothing |
| Shadow → money-path wiring | **refused** | `refuse_shadow_money_path`, `refuse_shadow_governed_wiring` | Boot isolation |
| Regime design artifact (family, labels, leakage, sessions) | **DNG** | `regime_design.py` Story 30.1 | Design-only authority |
| Regime corpus acquire/clean/split | **DNG** | `regime_corpus.py` Story 30.2 | Offline; no train |
| Regime label generation/audit | **DNG** | `regime_labels.py` Story 30.3 | Deterministic buckets |
| Regime offline train script | **DNG** | `regime_train.py` Story 30.4 | Operator machine; no VPS/cloud/live net |
| Regime offline eval | **DNG** | `regime_eval.py` Story 30.5 | No profit / live authority |
| Regime registry lineage (sandbox / candidate) | **DNG** | `regime_register.py` Story 30.6 | Forbidden: governed/ratified/active |
| Trained model on live path / promotion cadence | **GG** | GAP-0051 | Deferred last node epic |
| KSA matrix cell values | **GG** | GAP-0050 | Shape closed; values open |
| Placement variant (single-machine) | **GG** | GAP-0058 open | Not MIS math; placement |
| Kronos / HMM / BOCPD / MS-GARCH | **UA** | `UNAUTHORITATIVE_CANDIDATES`; DEC-0262 | Evaluated & rejected for authority |

---

## B. Dataflow (governed vs shadow)

```
FrontierFrame (as-of slice frontier; never wall-now)
        │
        ├─► V1 governed producers (6 rule-based + liquidity_stress_v1)
        │         │
        │         ▼
        │   SignalSnapshot  lane=governed
        │         │
        │         ├─► Book door (CT-23)  — e.g. SQS hard-block read
        │         └─► KSA fold          — sensor input only
        │
        └─► Shadow candidates (optional; heavy; own WriterId)
                  │
                  ▼
            SignalSnapshot  lane=shadow   prefix mis/shadow/
                  │
                  ├─► evidence comparison projection (ungoverned)
                  └─► ✗ Book door / KSA / bots / venue / command folds
```

**[FACT]** SQS reaches doors only inside the snapshot (one value per instant).  
**[FACT]** Replay reads the **recorded** snapshot; does not recompute SQS (TN-21).

---

## C. Regime classifier design card (integration, design-only)

| Field | Value | Grade |
|---|---|---|
| Producer id | `regime_classifier_v1` | FACT |
| Chosen family | `lightgbm-multiclass` | FACT (design-only) |
| Classes | quiet, normal, elevated, stressed | FACT |
| Exclusion | insufficient_evidence | FACT |
| Label method | forward-realized-range-quantile-buckets | FACT |
| Horizon | 12 × M5 bars | FACT |
| Quantile edges | 0.25, 0.50, 0.75 | FACT |
| Sessions | asia, london, new_york | FACT |
| Window | 730d lookback; warm-up 120 bars; fx-majors-declared-roster | FACT |
| Leakage | as-of; no future/forming; purge/embargo 12; sealed holdout; no shuffle; calendars apart | FACT |
| Train locus | operator-machine-offline-script | FACT |
| Seed default | 30042026 (`30_04_2026`) | FACT |
| Money-path authority | **false** | FACT |
| Governed binding | **false** | FACT |
| Docs "no ratified model family" | Still true as **ratification** claim | FACT (glossary/TN-19/GAP-0051) vs design selection on code |

Rejected / unauthoritative families (FACT): kronos, hmm, bocpd, ms-garch (`authority=none`); online-river rejected for reproducibility.

---

## D. SQS capability card

| Field | Value |
|---|---|
| Name law | Spread Quality Sensor only (constitution **L23**) |
| Formula | `score = baseline_average ÷ live_spread` (exact rational) |
| Pass rule | at-or-above hard-block threshold passes; strictly below blocks |
| Sentinel | undefined / missing / stale / refused / not_ready ⇒ hard block (never last-known-good) |
| Baseline key | `(VenueId, environment, instrument)` — demo baseline ≠ live |
| Cadence | tick/quote; bar sampling refused |
| Authority | computes only; Book door decides; never sizes |
| Not | regime model; snapshot-quality metric; playbook switch |

---

## E. Authority refuse surface (sampled tests on integration)

| Test / refuse | Proves |
|---|---|
| `test_book_door_and_ksa_consume_bots_refused` | Bots policy-rejected |
| `test_shadow_lane_snapshot_is_not_consumed_by_book_door_or_ksa` | Shadow publish-only |
| `test_candidate_output_never_reaches_money_path_consumers` | book_door/ksa/bot/venue/command/control refused |
| `test_registering_candidates_does_not_alter_governed_composition_fp` | Candidates → `shadow_composition_fp` only |
| `test_regime_classifier_not_selected_trained_registered_or_bound` | V1 catalog refuses trained id |
| `test_unauthoritative_candidates_have_no_authority` | kronos/hmm/bocpd/ms-garch |
| `test_candidate_evaluation_grants_no_authority_to_recovered_names` | Design eval ≠ authority |
| `test_silent_design_change_and_authority_claims_refuse` | Design cannot claim money-path |
| register tests: `refuse_governed_or_active_status`, `refuse_live_consumer_binding`, `refuse_composition_fp_mutation` | Registration stays non-live |

---

## F. Story → module map (`integration:qmn/src/qmn/mis/`)

| Story | Module | Role |
|---|---|---|
| 26.3 | `signal_snapshot.py` | Governed snapshot |
| 26.17 | `catalog.py`, `labelers.py`, `liquidity.py` | V1 producers |
| 26.18 | `shadow.py` | Zero-authority seam (TN-19) |
| 30.1 | `regime_design.py` | Fingerprinted design |
| 30.2 | `regime_corpus.py` | Corpus + splits |
| 30.3 | `regime_labels.py` | Labels + audit |
| 30.4 | `regime_train.py` | Offline train |
| 30.5 | `regime_eval.py` | Offline eval |
| 30.6 | `regime_register.py` | Non-authoritative registry lineage |
| — | `_refuse.py`, `__init__.py` | Shared refusals / surface exports |

---

## G. What this map deliberately excludes

- Treating recovered Kronos/HMM/BOCPD/MS-GARCH as production regime engines.
- Treating a classification F1 / Brier score as a trading edge.
- Claiming GAP-0051 closed because Stories 30.1–30.6 exist (pipeline ≠ live promotion).
- Claiming MIS sizes risk or selects bot playbooks.

---

## H. Short verdict

**[INFERENCE]** Current QMX MIS capability is a **governed block/sensor snapshot** plus a **ready shadow drop-zone**, with an **offline regime-classifier factory** that is design-complete on `integration` but **not governed on the money path**. Next authority step remains GAP-0051 (train → register → shadow consume → human/recertify → only then any governed bind), not inventing a new in-process ML stack on the VPS.
