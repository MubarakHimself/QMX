# 18 — Model and method candidate atlas

Every row: hypothesis, mechanism, QMX home, baseline to beat, falsifier. None is governed.

| ID | Hypothesis | Mechanism | Inputs | Outputs | Horizon | Markets | Failure | Baseline | QMX home | Falsify if |
|---|---|---|---|---|---|---|---|---|---|---|
| C-LGBM | Four vol/risk buckets improve sit-out vs simple tape rules | LightGBM multiclass, frozen text artifact | design feature_ids, as-of | quiet\|normal\|elevated\|stressed + insufficient_evidence | M5, 12-bar label horizon | FX majors first | Flicker; label≠door task; session holes | B0–B4 | Shadow then maybe snapshot | Gated door metric ≤ B3/B4 on sealed holdout |
| C-3WAY | Vol-first 3-way is enough | σ-ratio then autocorr | closed returns | volatile\|trend\|range **no direction** | bar | FX/crypto with recalibration | Thresholds are knobs | raw σ | MIS filter | Adds nothing over B4 |
| C-COMP | Compression/transition/expansion is the right *now* descriptor | Closed-candle range/CLV (20996) | OHLC closed | three states | local window | any OHLC venue | Analogies overfit; trend mixed in | B5 | Shadow | No door lift vs B3 |
| C-BOCPD | P(break) is a different object than class | Adams–MacKay run-length | log returns, λ | cp_prob, run_length | tick-to-bar | jumps yes, slow mean lag | λ prior; few events | random skip | MIS sensor; Book cooldown | Random skip matches DD cut |
| C-CUSUM | Page CUSUM is the cheap causal break detector | Dual accumulators on z_t, window t−1 | log returns | stop time | bar | cross-instrument via z-score | h calibration; variance breaks vs mean | B6 vs BOCPD | same as C-BOCPD | No extra door value vs B3 |
| C-HMMVOL | 2-state vol HMM beats raw σ | Frozen matrices, **filtered** decode only | rolling σ | MAP state + posterior | bar | author used XAUUSD H1 | Look-ahead; redundancy | raw σ (16830 caveat) | Shadow only | HMM ≈ σ threshold |
| C-CHAN | Discrete classes are the wrong object | MA+ATR channel (16856) | MA, ATR | position vs boundary | M1–D1 in source | EURUSD source | Playbook-in-EA; win-rate theatre | MA-cross | Bot/Book, **not MIS class** | Channel is just MA+ATR restated |
| C-ADX | Existence-of-trend is the cheap chop filter | Wilder ADX | OHLC | adx, rising, bin | bar | folklore on FX daily | Threshold folklore | none — it IS a baseline | MIS scalar | Fancy models never beat it on door task |
| C-ENT | Entropy/Hurst as slow chop coordinates | GHE, permutation/persistence entropy | returns/closes | scalar + not_ready | long window | scaling differs by venue | Too slow for M1; TDA heavy | ADX | Shadow / slow feature | No incremental value vs ADX |
| C-TE | Transfer entropy as information-flow feature | 15393 | two series | TE scalar | research | pair-specific | Nonstationary; compute | lagged corr | Ungoverned search | Unstable OOS |
| C-LYAP | Lyapunov as chaos coordinate | 15332 nearest-neighbour | embedding | local exponent | H1 in source | EURUSD tested | Coin-flip on reversal | none | **Not a candidate for authority** | Already fails source’s own table |

Governance for all: freeze offline, fingerprint, shadow first, no bot consumer, no size term.
