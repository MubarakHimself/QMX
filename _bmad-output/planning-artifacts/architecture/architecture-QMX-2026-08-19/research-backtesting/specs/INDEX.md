# QMB reverse-engineering specs — index

date: 2026-08-20 | campaign: 13 agents, all delivered | method: operator-ruled SDD (mechanism from code, never code adoption)
Sources: Jesse v3.0.6 local copy; lean-cli + LEAN engine sparse clones (scratchpad); both docs sites. Every spec carries file:line cites.

## The one-line verdicts

| Spec | Key finding |
|---|---|
| `spec-backtest-loop.md` | The engines diverge on ONE axis: Jesse steps a fixed 1-minute grid with **no clock seam** (live and backtest are separate code); LEAN advances a **data-driven frontier clock, injected**, so one loop serves backtest/live by swapping config-named handlers. That single seam is what lets QMB stamp world=replay/live/simulated without forking the engine. Adopt LEAN's slice+clock architecture; borrow Jesse's split-candle intra-bar fill fidelity. 11 requirements drafted. |
| `spec-fill-fees.md` | **Neither engine has a usable retail-forex model.** LEAN's slippage models no-op without volume data and ship no FX swap; Jesse fills at exact order price, zero slippage. Take LEAN's three pluggable interfaces (fill/slippage/fee) + Jesse's split_candle sequencing; QMX must originate the forex spread/slippage/swap content itself. GAP-0048 confirmed as real, original work. |
| `spec-optimization.md` | Jesse's marketed "Optuna optimization" is **uniform np.random with Optuna as a SQLite ledger** — functionally random search; Lean ships grid/Euler-zoom. Neither is Bayesian. QMB's differentiator: a genuinely adaptive sampler (TPE-class) + Lean-style post-hoc parameter-sensitivity for overfit detection. |
| `spec-synthetic-data.md` | **Vindicates L20 with evidence.** LEAN's "Brownian" generator is a bounded UNIFORM random walk (no GBM, no vol clustering, no fat tails) — can only claim infra-stress; and its output carries **no provenance tag** (indistinguishable from real data — the exact backdoor QMB taints against). Jesse's moving-block bootstrap (perturbing real history) is the only method that can legitimately claim robustness. Rule: a synthetic run's claim class derives from whether its process was seeded from real data. |
| `spec-reports.md` | Both engines compute chart data then throw it away into PNGs/formatted strings. QMB inverts: ONE canonical unit-kinded exact-money artifact (CT-32), chart series as data, HTML rendering a pure downstream function. |
| `spec-research-jupyter.md` | Both prove the same law: the research surface must be the SAME library the engine uses. Jesse ships it as pure importable functions (portable, uv-installable); Lean binds it to Docker/CoreCLR. Take Jesse's function architecture with Lean's DataFrame ergonomics. |
| `spec-data-mgmt.md` | Clean split: Jesse's "ship no data, fetch at run-time under the user's own exchange relationship" is the acquisition posture that **clears QMX's licensing gate**; Lean's map-files/factor-files/market-hours-DB is the organization model for (venue,symbol)+calendar. |
| `spec-cli-config.md` | **Lean's CLI is a config COMPILER** — the engine only ever reads one fully-resolved, read-only config.json per run; that artifact is simultaneously the run definition, the fingerprint source, and the ledger key. This is the operator's Book/BMS-as-config wind tunnel, validated by mechanism. Precedence: flag > project config > workspace config > defaults. |
| `spec-multi-routes.md` | Jesse: every TF folded from a single 1-minute spine (one clock, many TFs); Lean: consolidators + Cartesian parameter sweep. QMB: Jesse's declarative routes for the per-run stream set + Lean's Cartesian batch generalized to symbol×TF×params — each combo one isolated, labeled ledger run. |
| `spec-mc-significance.md` | Jesse's "test the edge before you build": a signal-only pass through the real engine with **orders disabled** (strategy stays flat, emits +1/-1/0), then bootstrap of signal×next-bar detrended log-returns against a zero null. Lean has no pre-build test at all. |
| `spec-charts-ui.md` | Jesse's chart JSON is coupled to TradingView Lightweight-Charts field names and never downsamples; Lean keeps a renderer-agnostic domain model with wire converters + SeriesSampler. Copy Lean's separation; emit self-describing per-bot chart JSON agents read directly. |
| `spec-concurrency.md` | Both engines isolate runs by OS process **because** they hold mutable globals. QMF's immutable core makes process-per-run a free CPU-parallelism choice, not a crutch. The operator's log-during/save-at-completion ledger is literally Lean's process-exit → read result.json → record cycle. Answers the 12–14-concurrent-runs question: process-per-run, bounded by cores. |
| `website-visuals.md` + `screens/` | 5 screenshots saved. Trust axis both platforms market: **provenance** — Jesse's "Real results, not hallucinations: every number comes from the engine; the agent calls real tools." The validation ladder (backtest → optimize → MC → significance → walk-forward) is table stakes. |

## What this changes

1. The **wind-tunnel seam is real and named**: injected frontier clock + config-named handlers (LEAN) — one loop, worlds differ only by what's plugged in.
2. The **fill engine is confirmed as QMX's original work** — no donor has it. GAP-0048 is the hard core.
3. **L20 survives contact with the reference platforms**: LEAN's own generator can't validate edge and doesn't even tag provenance — QMB's store-level taint is ahead of both donors.
4. The operator's three intuitions (config-as-interface, logs-then-ledger, npm-style distribution) each map to a **verified mechanism** in the donor code, not just an analogy.
