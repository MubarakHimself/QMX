# 24 — Data requirements

From integration design + article transfer notes. No live fetch in training.

| Need | Why | Source law |
|---|---|---|
| Sealed M5 OHLC (and ticks if SQS/exec) | Features + labels; SQS is tick/quote sampled | qmf-data rooms; design `bar_interval=M5` |
| Knowledge-time on every row | As-of; no post-event revision | L19/L20; design leakage |
| Session labels asia/london/NY with explicit TZ | Design sessions; SQS baseline window | Calendars named apart |
| News calendar PIT | CT-31 windows; not SQS | DEC-0152 |
| Instrument class records | SQS thresholds; not parsed from symbol | DEC-0107 |
| Spread series for SQS baseline | Block-only door | DEC-0153 |
| Train 730d, warm-up 120 bars | Design window | `DataWindowContract` |
| Holdout sealed, no shuffle | Leakage | `SplitStrategy` |
| Per-venue provenance | NQ/gold/FX/crypto do not pool silently | article transfer caveats |
| Tick volume ≠ traded volume | Most MQL5 “volume” | scalp notes |

**Not required for first experiments:** DOM (often BOOKDEPTH=0), options surfaces (23734 gold-vol title is a later transfer check), Lyapunov embeddings, TDA cubes.
