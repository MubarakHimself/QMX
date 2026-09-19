# Evidence index

## Code / law (current QMX)

| Claim | Locator |
|---|---|
| integration tip | `8510c032496bb870824ecc5c4f807e8a4e4f167e` |
| Snapshot consumers | `integration:qmn/src/qmn/mis/signal_snapshot.py` |
| Catalog + UA names | `integration:qmn/src/qmn/mis/catalog.py` |
| LightGBM design-only | `integration:qmn/src/qmn/mis/regime_design.py` `CHOSEN_MODEL_FAMILY` |
| Forward-range labels | `integration:qmn/src/qmn/mis/regime_labels.py` |
| Shadow isolation | `integration:qmn/src/qmn/mis/shadow.py` |
| SQS law | `docs/constitution.md` L23 |
| GAP-0051 | `docs/gap-report.md` |
| Fuller baseline writeup | `workroom/research/2026-09-15_unbounded-market-intelligence/05_CURRENT_QMX_BASELINE.md` |
| Capability matrix | `…/07_CURRENT_MIS_CAPABILITY_MAP.md` |

## Full-read corpus

| What | Locator |
|---|---|
| Pack work-list | `../PACKS.json`, `../WORKLIST.json` |
| Extract jsonl | `../extracts/*.jsonl` |
| Raw clustered dump | `../NEW_MIS_IDEAS.md` |
| Wizard series (68 articles) | `../SERIES_wizard_techniques.md` + `extracts/trading_systems_043_p00.jsonl`–`p05` |
| NN Made Easy (75 articles) | `../SERIES_neural_networks_made_easy.md` + `extracts/trading_systems_047_p00.jsonl`–`p06` |
| Sensing atlas (human) | `../MIS_SENSING_ATLAS.md` |
| Article markdown | `.worktrees/mql5-library/data/mql5-library/md/<id>.md` |

## Article IDs cited in 02-ADOPT

| ID | Article |
|---|---|
| 20996 | PA Toolkit market-state module (compression/transition/expansion, no orders) |
| 23043 / 23103 | CUSUM breakpoint Parts 1–2 |
| 23482 | BOCPD (UA cousin) |
| 17737 | Hierarchical vol-first 3-way (strip direction) |
| 10715 | ADX existence |
| 15332 | Lyapunov — negative finding on reversal |
| 16856 | Rejects discrete boxes; MA+ATR channel; win-rate not a certificate |
| Wizard 93–95 | suffix automaton, reservoir, DSU+DBN (see series note for IDs 22842, 22901, 22937) |

## Coverage facts

- Fetched ok articles in library: 3057. Unique `article_id` in extracts: 3050.
- Sensing idea lines: 2964. Honest `not_mis`: 1182.
- Examples “regime” lines include many EA buy/sell wrappers — **not** adopted; atlas and 02-ADOPT already filtered.
