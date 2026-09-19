# Experiments — what to try (not what to ship)

All runs: as-of features, time-ordered split, sealed holdout, purge/embargo, no shuffle, no profit-as-acceptance, no live bind. QMB ungoverned or MIS shadow. FX majors M5 first (design roster); gold/crypto-spot as **transfer checks**, not pooled training.

## E1 — LightGBM vs cheap tape (door task)

- **Question:** Does design `regime_classifier_v1` improve sit-out vs B1/B2/B3?
- **Hypothesis:** It does not, once costs and abstention count.
- **Labels:** design forward-range quantiles **and** A1 compression labels as sensitivity. If it only wins on its own label, the slot is an objective in disguise.
- **Metric:** gated vs ungated entry-*attempts* under a frozen dummy bot (no sizing search). Macro-F1 is diagnostic only.
- **Done when:** holdout door metric and calibration tables exist for LightGBM and B1–B3.

## E2 — Change bit on top of a frozen class

- **Question:** Does C1 (CUSUM/BOCPD) or C2 (recon_error) add door value **on top of** B2 or LightGBM?
- **Hypothesis:** Breaks are a different object; they help as cooldown, not as a fourth class.
- **Control:** random-frequency skip so “trade less” is not skill.
- **Done when:** incremental value vs random skip is reported.

## E3 — Vocabulary bake-off

- **Question:** quiet|normal|elevated|stressed vs A1 compression|transition|expansion vs B2 volatile|trend|range — which maps to the same sit-out task with less flicker?
- **Outputs:** transition matrix, dwell times, per-session calibration.
- **Done when:** one vocabulary is worse on flicker+calibration and can be dropped from V1 discussion.

## E4 — Frozen latent vs raw σ (optional, after E1)

- **Question:** E1 autoencoder latent-Δ vs the σ it is fed (NN series author’s own suspicion, analogue of HMM vs σ).
- **Hypothesis:** latent loses the ablation.
- **Done when:** incremental value table exists.

## Refuse as acceptance

Win-rate from an MQL5 tester, in-sample 86% channels (16856), “never lost” lookup tables, forming-bar signals, shuffled CV, VPS training.
