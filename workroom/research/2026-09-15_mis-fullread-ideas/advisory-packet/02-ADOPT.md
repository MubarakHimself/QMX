# Adopt — sensing objects worth taking

Each row: **object**, **article home**, **QMX object to become**, **adopt how**. Ranked for discussion, not for a sitting.

Legend: **A** = adopt as shadow candidate now (experiment). **B** = adopt as a *baseline* the fancy models must beat. **C** = adopt only the encoding, freeze, no forecast head. **D** = Book/BMS, not MIS.

## A — new state vocabularies (compete with quiet|normal|elevated|stressed)

| ID | Object | Source | Become | How |
|---|---|---|---|---|
| A1 | Compression / transition / expansion | MQL5 20996 (PA Toolkit; non-trading EA, closed candles, no orders) | Alternate **class vocabulary** on shadow | Implement the article’s closed-bar range/CLV rules as a candidate labeler. Do not place orders. Compare to design classes on a **door** task (`04-EXPERIMENTS` E3). |
| A2 | Soft k-means membership | Neural Networks Made Easy (k-means atlas + softmax of inverted distances) | Soft regime vector on shadow | Offline cluster on as-of features; live = distance-to-frozen-centres. Emit membership + `insufficient_evidence`. Not a hard argmax unless a sitting asks. |
| A3 | Dual-horizon 3×3 state grid | Wizard Techniques (short×long maps before RL) | Discrete **state cell**, not a policy | Build the grid from two causal horizons. Stop before DQN/PPO. Snapshot may later carry `grid_cell_id`. |

## B — cheap baselines (must exist before LightGBM is interesting)

| ID | Object | Source | Become | How |
|---|---|---|---|---|
| B1 | Existence-of-trend (ADX / Alligator sleep→eat / kumo thickness) | Wizard + Indicators packs; 10715 in prior notes | Rule labeler **or** feature | Scalar + rising bit. No +DI/−DI on MIS. Thresholds not frozen at folklore 25. |
| B2 | σ-ratio 3-way (volatile / trend / range, **no direction**) | 17737 pattern minus up/down | Rule labeler | Latest σ vs 20-bar mean, then autocorr. Strip side. |
| B3 | Spread-state proxy | Already V1 `spread_state` | Control | Map extreme→stressed. This is the “do nothing new” baseline. |
| B4 | Session-conditional majority | `regime_eval` already names it | Control | Keep. |

## C — changeover as a **different field** (not a fourth class)

| ID | Object | Source | Become | How |
|---|---|---|---|---|
| C1 | Sequential break (CUSUM / BOCPD-class) | 23043+23103; 23482 (UA name) | `break_stop` or `cp_prob` on shadow | Causal window ending t−1. Book owns cooldown. Random-skip control required. CUSUM Part 2: empirical ARL ~5× theory — treat as **vol-break**, not directional mean-shift. |
| C2 | Familiarity vs integrity | Wizard 93: suffix automaton on {U,D,F} + AE reconstruction error | Two scalars: `path_familiarity`, `recon_error` | Frozen automaton/AE. High recon_error = structure broke. Not a side. |
| C3 | Break authenticity | Wizard 95: DSU clusters on ATR/BB expansion + DBN energy | `break_authenticity` | Score “real expansion vs stop-hunt.” Shadow only; heavy. |
| C4 | Plateau-aware cross vs touch | Examples/Indicators (MarkCrosses plateau walk) | Feature hygiene | When comparing two series, equal-value plateaus are touches, not crosses. Use in any change detector. |

## D — vol / activity coordinates (never fold into SQS)

| ID | Object | Source | Become | How |
|---|---|---|---|---|
| D1 | Tick-Δ rolling σ spike | Indicators/Trading packs | Optional vol coordinate | Bid/close Δ vs rolling σ. Closed ticks. |
| D2 | Volume ratio vs mean tick volume | spindle/VR articles | Activity bit | Tick volume ≠ traded volume. Recalibrate per venue. |
| D3 | Robust width (Theil–Sen / MAD) | 11126 | Feature replacing mean/MAD CCI | Offline recipe; live as-of. |
| D4 | Modular centre+width | 2888 | Feature family | Centre ∈ {AMA,FrAMA,TEMA,…}; width ∈ {ATR,StdDev,Donchian}. Width is the MIS piece. |
| D5 | Synchronized multi-symbol ATR + true-bar gate | 752 | Only if multi-instrument snapshot ever exists | Do not fake TF from hybrid history. |

## E — frozen latents (neural as sensor)

| ID | Object | Source | Become | How |
|---|---|---|---|---|
| E1 | Autoencoder bottleneck + latent Δ | NN Made Easy | Frozen embedding + `latent_delta` | Train offline, export text/ONNX-like artifact through existing register refuse-paths. Live = encode only. |
| E2 | Attention / MLKV / Skip-PAM | NN Made Easy late parts | Frozen sequence encoder | Same freeze rule. Reject next-bar head. |
| E3 | Reservoir sampling | Wizard 94 | Window construction | Fair streaming sample so live windows are not recency-biased. Use **before** any model. |
| E4 | ONNX export path | Integration section + NN series infra | Deployment of a **frozen** artifact | Matches “operator laptop train, node encode.” Not a live trainer. |

## F — venue-specific (adopt the *idea*, recalibrate)

| ID | Object | Caveat | How |
|---|---|---|---|
| F1 | Currency-cluster CCFp | FX majors closed set; sum-to-zero | Only on FX roster. Not crypto. |
| F2 | PnF / Kagi / Renko / TLB clocks | Brick size is a knob; clock ≠ calendar | Alternate **clock** for features, not a live chart type on the node unless QMF already has it. |
| F3 | Liquidity sweep vs expansion | PA Toolkit; often FX/index tape | Recalibrate; do not copy NQ DOM percentiles. |
| F4 | COT / WILLCO | Weekly, lagged, PIT calendar | Knowledge-time problem. Research lane only until a PIT series exists. |

## Do not “adopt the series”

Wizard Techniques and Neural Networks Made Easy are **curricula**. Adopt **one object per experiment**, not the EA stack that wraps it.
