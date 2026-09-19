# 21 — Experiment portfolio

No production components. All runs: as-of features, sealed holdout, purge/embargo, no profit inference as acceptance, no live bind.

## E1 — Does a simple tape rule beat LightGBM on a *door* task?

- **Question:** For FX majors M5, does `regime_classifier_v1` (design family) improve sit-out vs B3/B4/B2 (`22_`)?
- **Hypothesis:** LightGBM adds little over σ-ratio + spread-state once costs and abstention are counted.
- **Target:** not class F1 as the decision; use (a) macro-F1 as a *diagnostic*, (b) gated vs ungated entry-attempt quality under a frozen dummy bot (no sizing search).
- **Labels:** design labels (forward range quantiles) **and** a competing compression/expansion label (20996) as a sensitivity — if E1 only wins on its own label, that is leakage of the objective, not a door win.
- **Splits:** time-ordered 60/20/20, holdout sealed, shuffle forbidden (already in design).
- **Refuse:** profit-as-proof; forming bars; post-event calendar revisions.

## E2 — Changeover sensor vs class

- **Question:** Does `cp_prob` (BOCPD) or CUSUM stop add door value **on top of** a frozen class (B3 or LightGBM)?
- **Hypothesis:** breaks are a different object; they help as a cooldown, not as a fourth class.
- **Policy:** Book owns “skip N bars after break”; MIS only emits the number.
- **Control:** random-frequency skip (23482 already used this idea) so “trade less” is not mistaken for skill.

## E3 — Vocabulary bake-off in shadow

- **Question:** quiet|normal|elevated|stressed vs compression|transition|expansion vs trend|range|volatile (no direction) — which maps to the same Book sit-out task with less flicker and better calibration?
- **Hypothesis:** vol-bucket and compression are closer to each other than either is to trend/range.
- **Outputs:** transition matrix, dwell times, per-session calibration. No money-path.

## E4 — HMM vs raw σ (author’s own suspicion)

- **Question:** 2-state vol HMM vs the σ observation it is fed (16830 caveat).
- **Hypothesis:** HMM loses the ablation.
- **If HMM wins:** only a **filtered** (causal) recursion is allowed in live/backtest.

## Datasets

Governed QMF/QMB sources only (design `source_law`). Asia + London + NY. FX majors roster. Do not fetch inside training. Demo SQS baseline never used as live.

## Multiple-testing

Pre-register E1–E3. Treat extra article-inspired features as a **search lane** (ungoverned) until a new design fingerprint.
