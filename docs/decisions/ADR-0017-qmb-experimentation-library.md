---
id: ADR-0017
title: QMB — the experimentation/backtesting library and qmb CLI
type: adr
status: provisional
depends_on: [COMP-QMB, COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-RISK]
decisions: [DEC-0159, DEC-0160, DEC-0161, DEC-0162, DEC-0163, DEC-0164, DEC-0165, DEC-0166, DEC-0167, DEC-0168, DEC-0169, DEC-0170, DEC-0013, DEC-0083, DEC-0084, DEC-0085, DEC-0086, DEC-0087, DEC-0088]
sources: [DEC-0159, DEC-0160, DEC-0161, DEC-0162, DEC-0163, DEC-0164, DEC-0165, DEC-0166, DEC-0167, DEC-0168, DEC-0169, _bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md]
generated: 2026-08-21
verified: 2026-08-21
stale_after: 1y
---

# ADR-0017: QMB — the experimentation/backtesting library and qmb CLI

Date: 2026-08-21. Status: provisional pending operator ratification of the corpus. The design itself is ratified by operator delegation (2026-08-20, spine B-1..B-15 FINAL).

## Context

The glossary has carried a reserved slot — the "future backtesting library" — since the first corpus: a deferred, modular, on-demand QMF consumer for testing Bot-by-Book behavior, explicitly not a permanent central service, runtime engine, or Simulator UI (ADR-0011, DEC-0083, DEC-0087, DEC-0088). On 2026-08-20 the operator pulled that slot forward as an architecture question (ticket 008): he dictated a Lean-CLI-shaped CLI as the agent and operator backtesting interface, with a wants-list drawn from LEAN (local + sandbox runs, optimization, Jupyter research, data download, synthetic generation, algorithm reports) and Jesse (MCP, permutation testing, interactive charts, optimize mode, Monte Carlo and significance testing).

A four-ask ruling round redirected the session: nothing is adopted as code — the two donors were reverse-engineered into thirteen intake dossiers first ("understand the HOW by looking at the code; never use the code"), and the architecture was then run normally. The operator's own counter-model became the load-bearing mechanism: **config + logs/ledger** — creating or updating a Book or BMS materializes a config the CLI consumes; the wind tunnel is never swapped, only its variables change; backtests are logged, and completion saves exactly one ledger entry with the unbiased end result. The child sitting produced the QMB spine (B-1..B-15), gated through three reviewer rounds plus a docs-reconcile lens, and the operator ratified it by delegation the same night.

## Options considered

1. **Adopt or fork a donor engine (Jesse or LEAN).** Rejected on engineering grounds independent of the D1 build-our-own law: LEAN's CLI is a thin logic-free orchestrator over a C# engine in Docker (adopting it means adopting the engine); Jesse is crypto-only float arithmetic with module-global singletons, zero slippage, a flat fee model, and a paid closed-source live plugin. A costed fork-and-gut deletes the load-bearing ~90% and keeps the textbook ~10%, and the one thing QMX actually needs — a retail-forex fill model — is the one thing neither donor has. The engine-adoption options were already dead in the ledger (DEC-0085, DEC-0086) and stay dead.
2. **A permanent central backtesting service.** Dead since DEC-0084 and stays dead — B-15's passive file-sync hub is dumb storage, deliberately not a service, and the decision records that explicitly (DEC-0165).
3. **Keep deferring.** Rejected by the operator's ruling: the direction sitting ran, the spine is FINAL, and QMB now realizes the reserved slot at the planning level. Implementation authorization still arrives only through the factory pipeline.
4. **Build QMB — one pure library, thin doors, one impure orchestrator.** Selected (DEC-0159..DEC-0169).

## Ruling

QMB is the QMX experimentation/backtesting product: one pure library plus the `qmb` CLI (the product face), with a Python API door now and an MCP door after CLI v1 — an application-layer product built ON QMF, never a QMF roster package. The paradigm is hexagonal with config-composition: every run consumes exactly one resolved, read-only, fingerprinted run-config artifact (DEC-0160); the library's `run()` is pure and returns a CT-32 performance-result; one impure orchestrator owns all writes — per-run operational logs during, exactly one WriterId-scoped ledger line at completion (DEC-0161, DEC-0163). Bar verdicts are reader-derived per-requirement folds, never frozen (DEC-0162). Execution fidelity ships as ports with an honest `optimistic` taint until GAP-0048 rules the content, and the fill-model solve is calibration from QMX's own recorded evidence, never invention (DEC-0164). Registry state arrives as immutable as-of sets over a passive hub (DEC-0165); data acquisition is download-once with per-window license tags (DEC-0166); distribution is a pinned lockfile dependency (DEC-0167) with click and optuna pinned exactly (DEC-0168). The full spine, including the run loop, sampler, research-surface, stream-set, and validation-ladder rules, binds through DEC-0169.

## Reuse-or-new verdict

**new `COMP-QMB`** — with the inventory read and the alternatives named:

- `COMP-QMF-RISK` owns CT-32 and the Book/BMS vocabulary QMB consumes, but it is a definitions boundary — an edge module carrying contracts, forbidden by its own charter from running anything (DEC-0143, DEC-0158). It cannot carry a run loop.
- `COMP-QMF-DATA` owns rooms, splits, and the journal, not runs; B-11 makes QMB's data commands thin fronts over its contracts precisely so no second data layer grows (DEC-0166).
- `COMP-QMF-REGISTRY` owns records and lineage, not execution; B-15's as-of sets are a delivery mechanism for its records, not a second registry (DEC-0165).
- `COMP-QMF-CORE / INDICATORS / STRUCTURE` are pure primitives and producers QMB composes; none may own process management (AD-15 forbids the library layer spawning work).
- The dead list was checked and holds: the central service (DEC-0084) and engine adoption (DEC-0085/0086) stay dead; QMB revives neither — B-15 is explicitly fenced as not-DEC-0084, and no donor code enters the tree (D1, DEC-0013, ADR-0011).

What `COMP-QMB` owns that nothing else does: the event-slice run loop, the config compiler, the fill/cost/financing ports, the sampler and validation-ladder procedures, the run ledger, and the impure orchestrator. What it may never do: bench, promote, or bind (it publishes; the Book door and operator act — DEC-0162); redefine risk vocabulary (AD-29..41 consumed read-only); mint a second data or registry layer; run as a central service. No existing component's authority shrinks: QMB fills a slot the corpus had reserved empty, and it is the first sanctioned composition root where the defined-unwired risk contracts are legally wired in `world = replay`.

## Consequences

- The glossary's reserved entry is realized; the Simulator stays a separate deferred UI product that will consume QMB (DEC-0159). The experimentation/backtest rename is settled.
- Look-ahead **prevention** is delivered (B-2/B-8/B-12); the registration **gate** GAP-0016/0017 stays deferred per DEC-0121, its raw material now accruing by construction.
- GAP-0048 is partially closed: seams ruled, taxonomy values and calibration content still open in their own sitting. GAP-0049's thresholds and the staged funnel stay deferred; until they land, funnel stages run manually and nothing gates compute.
- QMB tests plain-Python bots until QML lands (GAP-0047); the QML sitting may run before the backtesting-content sitting per the operator's ordering lead.
- The Dukascopy data-licensing ops question, flagged to the operator by this increment, was RULED CLOSED by the operator (2026-08-21): the data is used at a personal level only — backtesting his own strategies — so no licensing blocker stands; the per-window license-tag mechanism stays in force unchanged, and the question reopens only if a future posture exceeds personal use (DEC-0170).
- Implementation authorization is unchanged: factory-pipeline-only. `world = simulated` stays reserved-unusable until GAP-0048.

## Blast radius

New component `COMP-QMB` and feature `FEAT-0029`; new registry rows for the QMB governor/limits/staleness variables and the click/optuna pins; CT-32 gains its declared QMB extensions and QMB as its intended producer; CT-13 gains the replay-world run-loop emission note; CT-11's operational-vs-evidence boundary is restated for per-run logs; glossary (QMB, future-backtesting-library, experimentation/backtest, Simulator, as-of set), overview, stack, gap report, index, AGENTS.md, and the qmf-risk/qmf-data/qmf-registry/dukascopy component specs take consumer-side notes. No QMF contract changes meaning; no dependency edge into QMF reverses direction.
