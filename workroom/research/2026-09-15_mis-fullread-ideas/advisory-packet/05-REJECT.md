# Reject or defer — if it comes up in the discussion

| Proposal | Disposition | Why |
|---|---|---|
| Restore Ising / Lyapunov / `physics_multiplier` | **Reject as recovery** | Absent in this repo. 15332’s own EURUSD H1 table ≈ coin-flip for reversal vs continuation. Sizing is R-ladder. |
| MIS switches bot playbooks (Wizard EA default) | **Reject** | L-CONS / DEC-0204 |
| Bots consume the snapshot | **Reject** | `refuse_bot_consumer` |
| Fold ATR/ADX/news into SQS | **Reject** | L-SQS / L-NEWS |
| Online-river / VPS retrain | **Reject** | L-RIVER / L-OFFLINE |
| hmmlearn `predict`/`predict_proba` on a window as history labels | **Reject for backtest features** | Smoothing look-ahead (prior file 08) |
| `ruptures` whole-series breakpoints as live features | **Reject** | Future leak |
| New `qmf-mis` library / CT-MIS-01 | **Reject** | DEC-0089; gitbook contracts superseded |
| Snapshot-quality weighted SQS | **Reject name** | DEC-0073 |
| TDA / persistence entropy as V1 | **Defer to shadow** | Heavy; AD-24 |
| Kronos weights | **Defer** | UA until a sitting |
| COT/WILLCO as live snapshot | **Defer** | PIT/lag |
| NQ VPIN percentiles on FX | **Defer / likely reject transfer** | Venue |
| Discrete boxes as the *only* formulation | **Do not freeze yet** | A1 and C1 are live alternatives; E3 decides |
| Ensemble of article methods | **Reject until E1–E3** | Multiple-testing |

Hawkes / Ising / Kuramoto / percolation / spin glass / Fokker–Planck: **zero real hits** in 3,057 bodies. Do not invent a physics stack from this library.
