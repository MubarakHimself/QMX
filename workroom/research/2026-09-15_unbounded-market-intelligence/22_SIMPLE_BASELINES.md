# 22 — Simple baselines (must challenge fancy candidates)

Integration `regime_eval` already names: majority-class, session-conditional-majority, rule-spread-state-proxy. Keep those, and add the cheap tape baselines the corpus actually implements.

| ID | Rule (causal, closed bars only) | Inputs | Emits | Must not |
|---|---|---|---|---|
| B0 | Majority class in train, constant | none live | one class | be reported as a model |
| B1 | Session-conditional majority | session_id | class | leak other sessions |
| B2 | Spread-state proxy | V1 `spread_state` | map extreme→stressed, elevated→elevated, else normal | pretend this is SQS |
| B3 | σ-ratio 3-way (17737 minus direction) | latest σ vs 20-bar mean; autocorr | volatile / trend / range | emit up/down |
| B4 | ADX existence (10715) | Wilder ADX, unfrozen threshold | adx, adx_rising, low/mid/high bin | freeze 25; put +DI/−DI here |
| B5 | Range-contraction (20996 compression test) | recent vs prior window ranges | compression / not | predict breakout |
| B6 | CUSUM stop (23043) | log-return z-score, window ending t−1 | break / no-break | treat as a side |
| B7 | SQS hard-block only | existing SQS | sit-out when blocked | add ATR into SQS |

**Ablation order (from 2026-09-09 miner, still right):** B4/B3/B7 first → add B6 as a *break* bit → only then LightGBM or HMM. Two vol encodings of the same thing will fail incremental-value.

**Downstream metric (not F1):** does gating entries on the baseline, vs ungated, improve a pre-registered Book-door task (fewer doomed entries, calibrated abstention, cost-aware) on a sealed holdout with purge/embargo.
