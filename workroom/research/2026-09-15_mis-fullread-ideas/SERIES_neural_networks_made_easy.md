# Series: Neural Networks Made Easy (full-read)

75 articles, 103 idea lines, packs `trading_systems_047_p00`–`p06`. One series, consecutive slices. Not a title scan.

This is the library’s long neural-methods curriculum. For MIS the useful objects are **sensors and state encodings**, not “train a net to buy.”

## Sensing objects the series actually builds

- **Sequence memory.** LSTM/GRU gated memory for non-Markov paths; later Transformer / GPT-style causal attention; MLKV cross-layer KV sharing (superficial vs semantic layers); Skip-PAM multi-scale attention.
- **Unsupervised state.** k-means pattern atlas + per-cluster outcome tables; softmax of inverted distances as **soft regime membership**; autoencoder bottleneck; successive latent-state difference as a **dynamics** sensor.
- **Compression / co-occurrence.** PCA 99% orthogonal features; FP-Growth / association rules from binned indicators (treat as research, not a live miner).
- **Infra, not a sensor.** OpenCL training, Adam, ONNX export — deployment path for a frozen artifact, not a live learner on the node.

## What is *not* MIS here

Forecast heads that emit next-bar direction, online retraining on a VPS, and architecture-only parts with no market object. Several lines are `not_mis` after a full read (pure backprop pedagogy).

Extracts: `extracts/trading_systems_047_p00.jsonl` … `p06.jsonl`.
