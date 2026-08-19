---
id: SCN-0008
title: News Control Is Pair-Scoped but Has No Live Window
type: scenario
status: provisional
component: COMP-QMF-RISK
depends_on: [COMP-QMF-CORE, COMP-QMF-DATA]
decisions: [DEC-0065, DEC-0068, DEC-0072]
sources: [docs/components/qmf-risk.md, docs/registry/variables.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-23-risk-evaluation.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# SCN-0008: News Control Is Pair-Scoped but Has No Live Window

This scenario preserves the pair-scoped control while refusing to turn a tentative window into a trading rule. Execution status: **blocked specification**. [DEC-0068] [DEC-0072]

## Given

A governed calendar observation may affect one currency represented in an Instrument. `registry:news_blackout_before` and `registry:news_blackout_after` are null. Event severity, currency mapping, open-position behavior, override authority, and stale-data behavior are not defined. [DEC-0072]

`GAP(GAP-0029): Ratify the economic-calendar source contract and correction semantics.`

`GAP(GAP-0042): Ratify windows, severity, mapping, open-position behavior, and overrides.`

## When

A caller asks whether the Book may act around that event.

## Then

QMF must not apply a global market blackout, copy the tentative window into configuration, or invent allow/deny behavior. A future rule must evaluate only the affected pair and must make unavailable or stale evidence explicit. [DEC-0065] [DEC-0068] [DEC-0072]

## Worked numbers

No before/after duration is authorized. The executable fixture must reference `registry:news_blackout_before` and `registry:news_blackout_after` after GAP-0042 is answered.
