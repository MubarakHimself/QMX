# 13 — Rare and surprising findings

## Rare-term title set (`indexes/title_leads.json` family `rare`, n=12)

| ID | Title | First-pass note |
|---|---|---|
| 15332 | Chaos theory Part 1 — Lyapunov | Implemented; EURUSD H1 sign ≈ useless for reversal vs continuation |
| 15445 | Chaos theory Part 2 | Sequel; not a QMX restore |
| 15393 | Causal analysis using transfer entropy | Information-flow method; research feature |
| 16416 | Mutual information stepwise feature selection | Feature selection, not a regime class |
| 17351 / 17371 | Chaos theory in NN (Attraos) | Heavy sequence model |
| 17706 | Overbought/oversold via chaos approaches | Practitioner |
| 24057 | Denoise/detone/cluster correlation matrix | Portfolio / feature graph, not MIS |
| 3398, 13835, 14630, 21518 | Weak/false title hits | “promising” / “wedge” — not physics |

**Ising:** no title hit. Full-body sweep (3057 files): **Hawkes, Ising, Kuramoto, percolation, spin glass, Fokker–Planck = 0 real hits.** Body `network_physics` count 951 is inflated; do not cite it. Source: `notes/rare_and_surprising.md`.

## Surprises that change the problem statement

1. **20996** uses a matter-state analogy but the *implementation* is ordinary closed-candle range/CLV. It is a **placement-shaped classifier** (observe, don’t trade). Better MIS cousin than most regime EAs.
2. **16856** argues the literature on *how markets switch* is thin, then **avoids classification** with a channel. That is a genuine alternative to GAP-0051’s discrete classes.
3. **Changeover as a word** is absent in QMX law; the article corpus’s real change objects are CUSUM, BOCPD, HMM, structural-break tests — three different statistical jobs.
4. **Docs lag integration** on LightGBM. Easy to miss if you only grep `main`.
5. **Keyword “regime” in body is not a literature.** 2498 hits. Title 91 / changeover title 11 are the honest cores.

## Sidebar pollution

Related-article footers inject Lyapunov/regime titles into unrelated markdown (e.g. 15406 is a FOR-loop tutorial). Full-read the file before counting a hit.
