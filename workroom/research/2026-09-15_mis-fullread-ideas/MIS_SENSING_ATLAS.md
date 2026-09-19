# MIS sensing atlas (full-read, not titles)

**Method.** 290 catalog packs (section + Part-N series). grok-4.5 readers opened the markdown. 19 `mis-fullread*` workflow waves + series subagents. Physics lane closed. Instruments and timeframes kept as the article used them.

**Coverage (on disk when the last Example wave was still finishing one agent).** 288–292 extract files, **3,050 / 3,057** fetched article IDs, **2,964** sensing lines, **1,182** honest `not_mis` after a full read (language tutorials, UI panels, interviews). Raw dump: `NEW_MIS_IDEAS.md`. Series notes: `SERIES_wizard_techniques.md`, `SERIES_neural_networks_made_easy.md`.

**Filter for this atlas.** A line is *not* a MIS idea if it is an EA entry, pending, or playbook switch. MIS is a snapshot for Book door + KSA. Below are **sensors**.

---

## 1. State without a side

These emit “what kind of tape is this,” not up/down.

| Sensor | What it actually computes | Why it is MIS-shaped |
|---|---|---|
| Compression / transition / expansion (Price Action Toolkit 20996) | Closed-candle range vs prior window + CLV; **no orders** | Closest cousin to a snapshot class |
| MTF Harmony Index / T-M-V vote (PA Toolkit) | Weighted multi-TF agreement | Slow coordinate, not a trigger |
| Soft k-means membership (NN Made Easy) | Softmax of inverted distances to cluster centres | Soft regime, not a hard box |
| Currency-cluster relative strength (CCFp / CFP) | Closed 8-currency Δ with sum-to-zero balance | Cross-pair *state*, FX-specific |
| PnF / Kagi / Renko / Three-Line-Break column | Time-free brick/column direction + reversal count | State on a different clock; do not import brick size from FX to crypto silently |
| ADX existence / Alligator sleep→eat / Ichimoku kumo thickness | Classical “is there a trend” bits | Cheap baselines any fancy class must beat |
| Quiet / session-clock buckets | Homogeneous bull/bear clock buckets over a rolling window | Calendar state, not SQS |

**Not MIS:** Triple-screen “buy only if all MAs slope up,” MACD DiffMain long/short, Wizard Signal modules.

---

## 2. Changeover (the tape just broke)

Separate object from a class.

| Sensor | Mechanism | Use |
|---|---|---|
| Price-DNA suffix automaton vs AE reconstruction | Familiarity of {U,D,F} path vs reconstruction error | Familiar vs *broken* structure |
| DSU vol-clusters + DBN energy | Cluster ATR/BB expansion, score real break vs stop-hunt | Authenticity of a break |
| CUSUM / BOCPD-class sequential stops | Online, window ending t−1 | Book cooldown, not a side |
| Plateau-aware oscillator cross vs touch | Walk equal-value plateaus; cross ≠ touch | Change event hygiene |
| Fractal / channel re-slope vs flip | New extremum past both datums → flip, else slope-only | Distinguishes rotate vs break |
| Inside-bar / outside-bar / mother-bar | Compression then expansion of range | Change *shape*, still not a direction for MIS |
| PCA portfolio expand / compress / twist | Set divergence, reconvergence, curve crossings | Basket change; Book/BMS research more than snapshot |

---

## 3. Volatility and activity (not spread)

SQS stays spread-only. These are other coordinates.

| Sensor | Notes |
|---|---|
| Multi-symbol synchronized ATR with true-bar gate | Don’t fake TF from hybrid history |
| Tick-delta rolling σ spike | Bid/close Δ vs rolling σ |
| Volume ratio vs mean tick volume | Activity, not traded volume |
| Modular centre+width channel (AMA/FrAMA/TEMA × ATR/StdDev/Donchian) | Width as a state, centre as another |
| Dual-moment ring buffer (mean, var, skew, kurtosis) | Cheap distribution sensor |
| Theil–Sen / MAD CCI | Robust width when outliers dominate |
| RBCI / PCCI normalized FATL–SATL residual | Channel extreme vs shock |
| Burke / Omega / LPM | Path-risk, not tape vol — Book more than MIS |
| Pivot-width too-narrow day skip | Low expected range gate |

---

## 4. Liquidity / participation (not SQS)

| Sensor | Notes |
|---|---|
| Liquidity-sweep vs vol-expansion filter (PA Toolkit) | Sweep reclaim vs genuine expansion |
| Tick VWAP / flow / STM tilt | Tick participation |
| CPI session acceptance/rejection | Session auction |
| DOM / spread articles in microstructure packs | Venue-specific; NQ ≠ FX spot |
| COT index / WILLCO / movement index | Weekly positioning; knowledge-time / lag is the whole problem |

---

## 5. Neural / latent sensors (freeze, don’t trade)

From **Neural Networks Made Easy** (75 parts) and **Wizard Techniques** (68 parts), read as series.

- LSTM/GRU memory; GPT-style causal attention; MLKV (shallow vs semantic KV); Skip-PAM multi-scale attention.
- Autoencoder bottleneck; successive latent Δ as a **dynamics** sensor.
- Wasserstein-VAE FSAR encodings; RBM embeddings; Hopfield; CapsNet pose; UKF hidden price; ESN rhythm; Bayesian NN.
- Reservoir sampling (fair streaming window).
- Dual-horizon 3×3 **state grid** — the grid is MIS; DQN/PPO/SAC on it is a bot.
- Suffix automaton + AE break (above).
- ONNX/OpenCL/Adam — **deployment**, not a live learner on the node.

Reject: next-bar forecast heads, VPS retraining, Wizard money-management classes.

---

## 6. What the Examples shelf taught (after actually reading it)

A large fraction of “regime” hits in Examples are **EA conditions**. Those went into jsonl because the pack was assigned; they are **not** MIS. The useful remainder is: alternate clocks (PnF/Kagi/Renko/TLB), currency clusters, COT, robust width, and a lot of `not_mis` UI/math.

---

## 7. What this does *not* recommend

- Restore Ising / Lyapunov / physics_multiplier. Still absent as a QMX object; chaos articles failed their own reversal tests.
- MIS-driven playbook switch (Wizard EA default). Illegal under DEC-0204.
- Replacing `regime_classifier_v1` by reading this atlas. The design-only LightGBM remains unbound. These sensors are **shadow-lane candidates**.
- Treating 2,964 jsonl lines as 2,964 independent inventions. Many are restatements of MA-slope and BB-squeeze.

---

## 8. Smallest next experiments (still no architecture)

1. **Door task bake-off:** ADX-low / σ-ratio / compression-expansion (20996) / k-means soft membership vs the integration LightGBM labels — gated sit-out, not F1.
2. **Change bit on top:** AE reconstruction error or CUSUM stop vs random skip.
3. **Frozen latent:** one autoencoder or WAE embedding, fingerprint, shadow only.

Reuse snapshot + shadow seam. No new subsystem.
