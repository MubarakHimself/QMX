---
id: SCN-0009
title: Synthetic Stress Evidence Cannot Prove Trading Edge
type: scenario
status: provisional
component: COMP-QMF-DATA
depends_on: [COMP-QMF-CORE]
decisions: [DEC-0007, DEC-0042, DEC-0054, DEC-0096]
sources: [docs/constitution.md, docs/components/qmf-data.md, docs/lenses/testing/fixtures-and-scenarios.md]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# SCN-0009: Synthetic Stress Evidence Cannot Prove Trading Edge

This scenario separates infrastructure testing from market-evidence claims. Execution status: **blocked until the test toolchain is ratified**, but its epistemic boundary is already decided. [DEC-0054] [DEC-0096]

## Given

A deterministic synthetic generator produces controlled high-volume, malformed, missing, late, or out-of-order observations for parser and failure-path tests. The records are labelled synthetic and do not claim to be source evidence. [DEC-0042] [DEC-0054]

`GAP(GAP-0001): Ratify the runtime matrix.`

`GAP(GAP-0003): Ratify the test runner and canonical commands.`

`GAP(GAP-0013): Ratify measurable performance budgets and the benchmark workload.`

## When

The fixtures exercise ingest, persistence, capacity, corruption, or recovery behavior and those infrastructure checks pass.

## Then

The results may support only the named infrastructure and failure-handling claims. They must not validate a strategy, trading edge, promotion decision, fill model, market realism, or production readiness. No fake Bot, strategy, or trading estate becomes a shipped QMF artifact. [DEC-0007] [DEC-0054] [DEC-0096]

## Worked numbers

Load volume and timing remain unspecified because `registry:design_bot_concurrency` and the component performance budgets are null under GAP-0013. A test-local seed may make a fixture reproducible, but it is not a QMF business threshold.
