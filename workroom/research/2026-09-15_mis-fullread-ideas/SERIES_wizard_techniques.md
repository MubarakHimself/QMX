# Series: MQL5 Wizard Techniques (full-read)

68 articles, 148 idea lines, packs `trading_systems_043_p00`–`p05`. Read as one series, consecutive slices. Not a title scan.

This series is mostly: take a classical indicator (or a data-structure “indicator”) and pair it with a **neural or RL head**. For MIS, the useful split is the **sensor**, not the Wizard EA wrapper.

## Sensing objects the series actually builds

- **State grids, not signals.** Dual-horizon 3×3 short×long maps, then DQN / SARSA / PPO / SAC / TD3 / TRPO on that grid. The MIS-shaped piece is the *grid*, not the policy.
- **Familiarity vs integrity.** Suffix automaton on {U,D,F} Price DNA (how known is this path) plus autoencoder reconstruction error (did structure break). Two different sensors.
- **Streaming / fair sample.** Reservoir sampling so a live window is not recency-biased.
- **Vol-cluster authenticity.** Disjoint-set clustering on ATR/BB expansion, then DBN energy: real break vs stop-hunt.
- **Latent encodings.** Wasserstein-VAE FSAR, RBM embeddings, Hopfield, Bayesian NN, CapsNet pose, UKF hidden price, ESN rhythm.
- **Structure DS as sensors.** Sparse table, monotonic queue, Fenwick, Bloom+RNN, skip list, B-tree — used as trailing/regime memory, not as “algorithms for algorithms.”
- **Classical regime bits still present.** ADX/DI bands, Ichimoku kumo twist/thickness, Alligator sleep→eat, SAR compression-flip, FrAMA flatten + Force Index expansion, envelope squeeze/fake-out, BB squeeze→expansion.

## What is *not* MIS in this series

Wizard money-management classes, entry Signal modules, and “CNN predicts the next bar” heads. Those are bot/Book. Several late parts are architecture papers (RQ-kernel CNN, MLKV) — neural **sensors** only if you freeze the embedding and stop using the forecast.

## Series holes

Pack notes: parts 33, 37, 44 and some others were not in the sqlite slice. `series_incomplete=true` on every line.

Extracts: `extracts/trading_systems_043_p00.jsonl` … `p05.jsonl`.
