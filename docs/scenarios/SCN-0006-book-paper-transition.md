---
id: SCN-0006
title: Book Paper Transition Requires Operator Confirmation
type: scenario
status: provisional
component: COMP-QMF-RISK
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA]
decisions: [DEC-0039, DEC-0041, DEC-0065, DEC-0067, DEC-0069, DEC-0070, DEC-0107, DEC-0110, DEC-0115, DEC-0116]
sources: [docs/components/qmf-risk.md, docs/contracts/ct-22-book-charter.yaml, docs/contracts/ct-23-risk-evaluation.yaml, docs/contracts/ct-24-book-mode.yaml, docs/decisions/ADR-0009-book-level-paper-mode.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# SCN-0006: Book Paper Transition Requires Operator Confirmation

This scenario protects live and paper destinations from an unconfirmed recap, the dead parallel-Bot paper-twin design, and an unwired state-transition contract. Several foundations are now ratified — paper and demo accounts are `world = live` via the account role, the Bot-Book-account binding is a separate dated record outside Bot identity, and re-binding (paper to live) never mints a new Bot so performance stays comparable — but the Book-mode transition contract, Book/BMS schema, and exit ownership remain unratified. Execution status: **blocked specification; binding and world facts ratified**. [DEC-0070] [DEC-0115]

## Given

A Book is described as live, with a bound Bot and possible in-flight or open venue exposure. Account roles are ratified — live, demo, paper-validation, paper-benched, prop-firm — and money-reality is carried by the account role, so a paper or demo account is `world = live` and stays comparable to live for alpha-decay sensing; a Book's paper mode is a change of the account a Bot's Book binds to, not a change of world. The Bot-Book-account binding is a separate dated binding record outside Bot identity: one Bot binds exactly one Book at a time, and re-binding never mints a new Bot. CT-24 remains evidence-only with no active Registry, Data, application, account, or execution consumer, and the direct operator wording behind Book-level paper mode is missing from the transcript export, so the immediate recap remains provisional. [DEC-0039] [DEC-0070] [DEC-0107] [DEC-0110] [DEC-0115]

`GAP(GAP-0039): Ratify Book and BMS schemas, ownership, lifecycle, compatibility, and cardinality (risk sitting).`

`GAP(GAP-0040): Resolve ordinary and forced exit ownership; DEC-0067 remains a conflict (risk sitting).`

`GAP(GAP-0041): Ratify state values, trigger, account binding, open-position handling, atomicity, rollback, duplicate prevention, continuity, and audit (risk sitting).`

## When

An agent or application requests a live-to-paper transition.

## Then

No transition occurs. The dead parallel-Bot paper-twin design remains dead (DEC-0069): no second Bot twin is created, and because re-binding never mints a new Bot (DEC-0115), a paper transition can only be a Book-mode change of the bound account, never a duplicated or abandoned exposure. The operator must first confirm the paper-mode ruling and ratify the CT-24 transition contract; where a live-to-live promotion is involved, only a human-signed promotion occurrence authorizes it (DEC-0116). [DEC-0041] [DEC-0069] [DEC-0070] [DEC-0115]

## Worked numbers

No account count, transition delay, or position-handling threshold is ratified. The executable scenario must use future CT-24 fields and a human-authorized occurrence rather than scenario-local constants. The account role (not a separate world label) carries whether the destination is paper or live per DEC-0110.
