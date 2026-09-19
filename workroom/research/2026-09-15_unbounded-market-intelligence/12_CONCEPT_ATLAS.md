# 12 — Concept atlas (regime / changeover / placement)

Not a model shopping list. Problem formulations the evidence actually supports. Physics is one row, not the map.

## A. What is being estimated?

| Cluster | Question | Typical outputs | QMX home if ever |
|---|---|---|---|
| **State (descriptive)** | What kind of tape is this *now*? | Discrete class or continuous coordinates | MIS snapshot (information) |
| **Changeover** | Did the generating process just break? | P(break), run length, CUSUM stop | MIS sensor / KSA input; **not** a side |
| **Compatibility / placement** | Should this *family* fire, sit out, or wait? | Admit / abstain / later class-activation | Book door policy, not MIS authority |
| **Cost / execution state** | Can a fill keep an edge? | spread rank, exec_ok | SQS + Book; not regime |
| **Calendar state** | Which session / news window? | session_id, news_window_active | SQS baseline key; CT-31 windows |
| **Direction / trigger** | Which way / where? | DI, fade, breakout | **Bot confluence only** |

## B. Discrete state families seen

| Family | Classes | Mechanism | Transfer notes | Evidence |
|---|---|---|---|---|
| Integration design | quiet, normal, elevated, stressed | LightGBM on features; labels = forward 12-bar range quantiles | FX majors, M5, asia/london/NY | `integration:qmn/mis/regime_design.py` — **design-only** |
| Hierarchical vol-first | volatile, trend, range (+up/down in source) | σ vs 20-bar mean × 1.5, then autocorr/slope | Direction must be stripped for MIS | MQL5 17737 (prior full read) |
| Microstructure priority | Stressed, Noisy, Informed, Trending, Mean-Reverting, Normal | Rule stack over proxies | NQ M1 in-sample percentiles | 22940 (prior) |
| Matter-state analogy | compression, transition, expansion (+ trend as structure) | Closed-candle range contraction, CLV, no orders | Explicitly **not directional**; good MIS shape | 20996 (this run) |
| HMM vol | high-vol / low-vol hidden states | Gaussian HMM on rolling σ | Author suspects raw σ threshold may suffice; look-ahead in Viterbi | 16830 (prior) |
| GitBook optional | trend, range, chaos | unspecified | **Not** on V1 snapshot | archive gitbook-baseline |

## C. Changeover / sequential break

| Family | Online? | Causal? | Role | Evidence |
|---|---|---|---|---|
| BOCPD (Adams–MacKay) | yes | yes if run-length posterior at t uses ≤ t | Break sensor; cooldown is Book | 23482 (prior) |
| CUSUM (Page 1954) | yes | yes if μ,σ from window ending t−1 | Same role; industrial QC | 23043 + 23103 title set |
| Structural-break tests (Python/MQL5) | usually offline | often uses whole sample | Research labels; **not** live | 20946, 23158, 23159 |
| HMM / Markov matrix as switch | mixed | Viterbi/smoothing leak unless filtered | Often used as playbook switch (forbidden in MIS) | 15033, 15541, 17917, 16030 |
| “Markets never settle” continuous channel | n/a | if channel uses closed bars | Rejects discrete boxes | 16856 |

## D. Persistence / chop coordinates (not classes)

Hurst / GHE / VRT / half-life, ADX existence-of-trend, Kalman gain, permutation/persistence entropy, Catch22, fractal dimension, Yang–Zhang/GK vol. Slow coordinates or filters. Folklore thresholds (ADX 25) are not law. Title cluster ~52 articles (`indexes/title_leads.json`).

## E. Placement patterns (the operator’s “where to put it”)

1. **Sit-out gate:** volatile / stressed / cp_prob high / exec_ok false / news window → Book refuses new entries. MIS emits the label; Book owns the door.
2. **Family compatibility:** trend-family vs fade-family vs “don’t scalp.” Current law forbids MIS from switching the EA. Compatibility is Book class-activation *later* or bot confluence declared in CT-34.
3. **Continuous boundary:** trade relative to a channel instead of classifying (16856). Likely bot+Book, not a snapshot class.
4. **Playbook switch inside the EA (17781 and kin):** **INCOMPATIBLE** with DEC-0204.

## F. Physics-like language

| Item | Status |
|---|---|
| Ising / physics_multiplier as QMX | ABSENT-IN-REPO |
| Lyapunov / chaos series in MQL5 | 15332, 15445, 17351, 17371, 17706 — practitioner; 15332’s own EURUSD H1 stats show Lyapunov sign ≈ coin-flip for reversal vs continuation |
| Transfer entropy | 15393 |
| Mutual information feature selection | 16416 |
| Eigenvalue / correlation matrix | 23314, 24057 (risk-factor / detoning — portfolio, not MIS class) |

A metaphor (20996 matter states, 15332 chaos) is allowed as *explanation*. It is not an implementation candidate until there is a causal estimator, an abstention, and a downstream decision test.
