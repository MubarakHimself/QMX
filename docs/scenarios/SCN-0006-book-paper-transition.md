---
id: SCN-0006
title: Book Paper Transition Requires Operator Confirmation
type: scenario
status: provisional
component: COMP-QMF-RISK
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA]
decisions: [DEC-0039, DEC-0040, DEC-0041, DEC-0065, DEC-0067, DEC-0070]
sources: [docs/components/qmf-risk.md, docs/contracts/ct-22-book-charter.yaml, docs/contracts/ct-23-risk-evaluation.yaml, docs/contracts/ct-24-book-mode.yaml, docs/decisions/ADR-0009-book-level-paper-mode.md]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# SCN-0006: Book Paper Transition Requires Operator Confirmation

This scenario protects live and paper destinations from an unconfirmed recap, the dead parallel-Bot paper-twin design, and an unwired state-transition contract. Execution status: **blocked specification**. [DEC-0069] [DEC-0070]

## Given

A Book is described as live, with a bound Bot and possible in-flight or open venue exposure. CT-24 is evidence-only and has no active Registry, Data, application, account, or execution consumer. The direct operator wording behind Book-level paper mode is missing from the transcript export, so the immediate recap remains provisional evidence. [DEC-0039] [DEC-0070]

`GAP(GAP-0018): Resolve Bot/confluence cardinality and the one-Book binding schema; DEC-0040 remains a conflict.`

`GAP(GAP-0019): Ratify the signed human evidence required for live promotion and transitions.`

`GAP(GAP-0039): Ratify Book and BMS schemas, ownership, lifecycle, compatibility, and cardinality.`

`GAP(GAP-0040): Resolve exit ownership; DEC-0067 remains a conflict.`

`GAP(GAP-0041): Ratify state values, trigger, account binding, open-position handling, atomicity, rollback, duplicate prevention, continuity, and audit.`

## When

An agent or application requests a live-to-paper transition.

## Then

No transition occurs. The dead parallel-Bot paper-twin design remains dead: no second Bot twin is created, no destination is switched, and no existing exposure is abandoned or duplicated. The operator must first confirm the paper-mode ruling and ratify the transition contract. [DEC-0041] [DEC-0069] [DEC-0070]

## Worked numbers

No account count, transition delay, or position-handling threshold is ratified. The executable scenario must use future CT-24 fields and a human-authorized occurrence rather than scenario-local constants.
