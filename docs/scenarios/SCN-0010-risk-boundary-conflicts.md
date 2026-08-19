---
id: SCN-0010
title: Risk Evaluation Stops at Unresolved Book Boundaries
type: scenario
status: provisional
component: COMP-QMF-RISK
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA]
decisions: [DEC-0039, DEC-0040, DEC-0065, DEC-0066, DEC-0067, DEC-0068, DEC-0076, DEC-0078, DEC-0095]
sources: [docs/components/qmf-risk.md, docs/registry/variables.yaml, docs/contracts/ct-22-book-charter.yaml, docs/contracts/ct-23-risk-evaluation.yaml, docs/decisions/ADR-0008-book-and-risk-boundary.md, docs/decisions/ADR-0010-risk-vocabulary-clean-start.md]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# SCN-0010: Risk Evaluation Stops at Unresolved Book Boundaries

This scenario prevents a build agent from resolving Bot cardinality, exit ownership, Book/BMS shape, or risk arithmetic by convenience. Execution status: **blocked specification**. [DEC-0040] [DEC-0067]

## Given

A proposed Bot, Book, BMS, entry signal, and possible exit signal are presented for evaluation. CT-22 and CT-23 are reserved and unwired. R may be referenced only through `registry:original_risk_unit`; dead FORM-0006 is inadmissible. [DEC-0039] [DEC-0065] [DEC-0066] [DEC-0076] [DEC-0077] [DEC-0078]

`GAP(GAP-0018): Resolve Bot/confluence cardinality and Book binding; DEC-0040 remains a conflict.`

`GAP(GAP-0039): Ratify Book/BMS schemas, lifecycle, ownership, compatibility, and multiplicity; DEC-0095 remains open.`

`GAP(GAP-0040): Resolve ordinary and forced exit ownership; DEC-0067 remains a conflict.`

`GAP(GAP-0044): Ratify dimensionally valid risk formulas and capital concepts.`

`GAP(GAP-0046): Ratify deterministic same-tick action priority and overnight interaction.`

## When

A caller requests a risk authorization, position size, exit action, or venue-ready command.

## Then

No risk evaluation or venue authorization is produced. The caller cannot choose a conflict branch, revive the dead FORM-0006, treat the recovered Scalping Book as universal, or assign a CT-23 consumer. The fenced reconciliation must produce ratified one-pass features first. [DEC-0040] [DEC-0067] [DEC-0077] [DEC-0095]

## Worked numbers

`registry:original_risk_unit` supplies the meaning of R, but no formula may be derived from that single reference value. Position size, stop-out, priority, and Book/BMS counts remain undefined by the governing gaps.
