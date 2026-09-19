# 15 — Evidence saturation (corpus scan)

**Stamp:** 2026-09-15. Corpus: `.worktrees/mql5-library/data/mql5-library/` (Firecrawl markdown, not live mql5.com).

## Inventory

| Count | What |
|---|---|
| 3315 | cataloged sqlite rows |
| 3057 | `fetch_status=ok` with markdown + sha256 |
| 258 | failed (Firecrawl 401/402; listed in `coverage.md`) |
| 0 | exact sha256 duplicate clusters among ok files |
| 1 | title-duplicate cluster (articles 1100 and 1400) |
| 1261 | series-tagged `Part N` titles |

Body scan covered **all 3057** ok files (`indexes/scan_summary.json`).

## How saturation is judged (not “we opened N files”)

1. **Catalog completeness:** 258 holes are key-exhaustion failures, mostly low IDs. Residual risk: early-years articles missing. Does not block method clusters that concentrate in 2024–2026 IDs.
2. **Title map vs body map:** title hits are sparse and high-precision. Body hits are huge because family regexes include `trend`, `range`, `filter`, `tick`, `session`, `eigenvalue`. **Do not treat body counts as independent regime literature.**
3. **Prior full-reads:** 24 articles in the 2026-09-09 miners. This run’s agents are tasked to go beyond those IDs. Saturation for *methods* requires those new full-reads, not the body-count.
4. **Rare-term deliberate search:** title-family `rare` = 12 (chaos/Lyapunov, transfer entropy, mutual information, Attraos, correlation-matrix detoning). Body `network_physics` = 951 is **inflated** (eigenvalue/susceptibility in unrelated tutorials, e.g. article 709 “Lists”). Title-only network_physics = 8 is the honest rare set.
5. **Changeover cluster is small and stable at title level:** 11 title hits (HMM, Markov, CUSUM, structural break, BOCPD). Additional body-only hits must be sampled, not trusted wholesale.

## Family counts (use the title column for precision)

| Family | Title hits | Body hits | Reading rule |
|---|---|---|---|
| regime | 91 | 2498 | Body inflated by trend/range/volatile tokens |
| changeover | 11 | 212 | Title set is the must-read list |
| volatility | 16 | 665 | Title undercounts GARCH-in-body; sample body |
| persistence | 52 | 747 | Title set is usable |
| microstructure | 53 | 2020 | Body inflated by tick/spread in every EA |
| session_calendar | 62 | 1506 | Body inflated by “session” in every backtest |
| ml_sequence | 285 | 1757 | Largest real cluster; section “Machine learning” is only 21 |
| placement_filter | 24 | 1685 | Body inflated by the word filter |
| information | 3 | 127 | Mutual information / transfer entropy are rare |
| network_physics | 8 | 951 | Title is the honest rare set |
| risk_portfolio | 48 | 1337 | Kelly/correlation mostly EA risk, not MIS |

## What is already stable (will not flip if we read another hundred generic EAs)

- MIS in current QMX is a snapshot for Book door + KSA; SQS is spread-only; `regime_classifier_v1` is unbound on the money path (`05_`, `07_`).
- In-repo physics (Ising, Lyapunov as QMX design, `physics_multiplier`) is **ABSENT** (`02_`, `04_`).
- Discrete regime boxes vs continuous “boundary” (16856) vs compression/transition/expansion (20996) vs sequential break detectors (CUSUM 23043, BOCPD 23482) are the real competing *problem formulations*.
- Vendor articles that *detect a regime then switch the EA playbook* are the forbidden MIS pattern (17781, 15406-adjacent series, 16856 as a single dynamic EA).

## Full-read this run (beyond the 24 prior-note articles)

Shard jsonl row counts (overlap exists across families): changeover 38, microstructure 45, ml_sequence 40, persistence 39, placement 50, rare_physics 14, regime 43, session_calendar 37, volatility 37. Merged unique `article_id` in `11_ARTICLE_CLAIMS.jsonl`: **239**. Leftovers named in the 2026-09-09 notes were cleared.

That is enough to stabilize the **problem formulations** (discrete class vs compression vs sequential break vs channel vs session-gate). It is **not** enough to pick a winner — that is E1–E3, not more articles.

## What is not saturated

- Whether LightGBM quiet|normal|elevated|stressed is a better *door* label than compression/expansion or trend/range/volatile.
- Cost/latency survival of TDA/entropy/HMM vs ADX/σ-ratio baselines.
- 258 failed fetches.

## Failed fetches

258 IDs, Firecrawl keys exhausted. Listed in `.worktrees/mql5-library/data/mql5-library/coverage.md`. Do not pretend those articles were read.
