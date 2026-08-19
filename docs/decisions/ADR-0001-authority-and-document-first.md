---
id: ADR-0001
title: Authority and document-first delivery
type: adr
status: provisional
depends_on: []
decisions: [DEC-0001, DEC-0002, DEC-0003, DEC-0004]
sources: [DEC-0001, DEC-0002, DEC-0003, DEC-0004]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 1y
---

# ADR-0001: Authority and document-first delivery

Date: 2026-08-18. Status: provisional pending operator ratification.

## Context

QMF was reconstructed from current conversation, inherited plans, historical recovery material, and completed studies. These sources differ in authority and several later corrections reverse earlier designs.

## Options considered

1. **Flatten every source into one summary** — rejected because a historical proposal can silently override a later correction.
2. **Treat completed studies as adopted contracts** — rejected because research supplies evidence, not operator rulings.
3. **Use explicit authority and document before implementation** — preserves corrections, gaps, and deaths before code can harden them.

## Decision

Current direct operator rulings govern disagreements; historical material contributes only where later rulings have not changed it. Research never auto-adopts, and QMF documentation and review precede implementation. (DEC-0001, DEC-0002, DEC-0003, DEC-0004)

## Consequences

Every normative artifact traces to the decision ledger. Conflicts remain visible until the operator rules, and implementation cannot use a recommendation, completed study, or historical summary as if it were a signed contract.
