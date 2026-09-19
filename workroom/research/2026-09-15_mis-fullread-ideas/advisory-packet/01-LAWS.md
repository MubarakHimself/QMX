# Laws — do not bargain these in the discussion

Sources are QMX docs + `integration` code. Article ideas do not override them.

| ID | Law | Source |
|---|---|---|
| L-SNAP | Compute-once signal snapshot. Format v1. Environment-keyed. | `qmn/mis/signal_snapshot.py`; TN-19; DEC-0204 |
| L-CONS | Governed consumers = `book_door`, `ksa` only. Any other consumer → `refuse_bot_consumer`. | same; tests `test_book_door_and_ksa_consume_bots_refused` |
| L-SHADOW | Shadow lane: candidate role, `shadow_composition_fp`, publish-only. Book/KSA refuse shadow snapshots. Wiring a candidate into a governed consumer refuses to boot. | `qmn/mis/shadow.py`; glossary shadow-lane seam |
| L-SQS | SQS = spread ratio `session-window baseline ÷ live`. Block-only. Non-ok ⇒ hard block, no last-known-good. | constitution L23; `evaluate_sqs` |
| L-NEWS | News/calendar = CT-31 windows, never SQS. | L23; CT-31 |
| L-TRAIN | `regime_classifier_v1` not on the money path. Catalog `refuse_trained_regime_classifier`. | `catalog.py`; GAP-0051 |
| L-DESIGN | Code already chose `lightgbm-multiclass` + classes `quiet\|normal\|elevated\|stressed` as **design-only**. `grants_money_path_authority=False`, `grants_governed_binding=False`. Docs still say “unchosen.” Both true at different altitudes. | `regime_design.py` |
| L-LABEL | Training labels may use a forward window; live features are as-of. Shuffle forbidden. | `regime_labels.py`; leakage laws |
| L-OFFLINE | Train/eval on operator laptop. No VPS, no cloud, no live net in training. | `regime_train.py` Story 30.4 |
| L-UA | Kronos / HMM / BOCPD / MS-GARCH are named **unauthoritative**. They may be re-tried as shadow science; they are not bound. | `UNAUTHORITATIVE_CANDIDATES`; DEC-0262 |
| L-RIVER | Online-river continuous learning is rejected in design eval. | `regime_design.evaluate_candidate_families` |
| L-KSA | Snapshot and SQS are KSA **inputs**, never authorities. KSA matrix shape closed; cell values GAP-0050. | TN-7 |
| L-SIZE | Sizing is R-ladder in qmf-risk. Do not add a sensor multiplier that sizes. | qmf-risk; recovery: no `physics_multiplier` in this repo |

If a discussant says “the article’s EA switches strategies when regime changes,” the QMX translation is: **Book door policy later, or bot confluence (CT-34)**. Never MIS switching bots.
