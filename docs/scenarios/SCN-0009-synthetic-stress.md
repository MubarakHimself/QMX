---
id: SCN-0009
title: Synthetic Stress Evidence Cannot Prove Trading Edge
type: scenario
status: ratified
component: COMP-QMF-DATA
depends_on: [COMP-QMF-CORE]
decisions: [DEC-0007, DEC-0042, DEC-0054, DEC-0096, DEC-0099, DEC-0101, DEC-0111]
sources: [docs/constitution.md, docs/components/qmf-data.md, docs/lenses/testing/fixtures-and-scenarios.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# SCN-0009: Synthetic Stress Evidence Cannot Prove Trading Edge

This scenario separates infrastructure testing from market-evidence claims. The runtime matrix, quality toolchain, and benchmark method are now ratified — CPython 3.14 pinned (DEC-0099), ruff/pyright/pytest with poe commands (DEC-0101), and measure-then-budget benchmarking (DEC-0111) — so the fixtures now run under a ratified toolchain; numeric performance budgets still await first measured baselines, and the epistemic boundary that synthetic data stresses infrastructure but never validates edge stands unchanged. Execution status: **toolchain ratified; epistemic boundary standing; numeric budgets await baselines**. [DEC-0054] [DEC-0096] [DEC-0111]

## Given

A deterministic synthetic generator produces controlled high-volume, malformed, missing, late, or out-of-order observations for parser and failure-path tests. The records are labelled synthetic and do not claim to be source evidence. The runtime matrix (DEC-0099), the ruff/pyright/pytest toolchain and its canonical `poe` commands (DEC-0101), and the measure-then-budget benchmark method (DEC-0111) are ratified, so the fixtures run under a defined, host-neutral toolchain. [DEC-0042] [DEC-0054] [DEC-0099] [DEC-0101]

## When

The fixtures exercise ingest, persistence, capacity, corruption, or recovery behavior and those infrastructure checks pass.

## Then

The results may support only the named infrastructure and failure-handling claims. They must not validate a strategy, trading edge, promotion decision, fill model, market realism, or production readiness. No fake Bot, strategy, or trading estate becomes a shipped QMF artifact, and benchmark and test data stay generated or held as controlled fixtures, never shipped as product artifacts. [DEC-0007] [DEC-0054] [DEC-0096] [DEC-0111]

## Worked numbers

Per-component numeric budgets are not invented: measure-then-budget records first real measurements as fingerprinted, (OS, CPU-class)-scoped baselines, and the roughly-forty-bot reference scenario with 10/40/100/200 load marks sizes the ladder (DEC-0111). Until those baselines exist, `registry:design_bot_concurrency` and the component budgets carry no ratified numeric target. A test-local seed may make a fixture reproducible, but it is not a QMF business threshold.
