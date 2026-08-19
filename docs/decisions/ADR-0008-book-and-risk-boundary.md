---
id: ADR-0008
title: Book and BMS risk boundary
type: adr
status: provisional
component: COMP-QMF-RISK
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA]
decisions: [DEC-0065, DEC-0066, DEC-0068, DEC-0080]
sources: [DEC-0065, DEC-0066, DEC-0067, DEC-0068, DEC-0080, DEC-0095]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 1y
---

# ADR-0008: Book and BMS risk boundary

Date: 2026-08-18. Status: provisional pending operator ratification.

## Context

Entry logic, money permission, position sizing, exit behavior, and reusable Book patterns must not collapse into one Bot or one universal scalping cycle.

## Options considered

1. **Put risk and money quantity in the Bot** — rejected by the directional separation between confluence and Book policy.
2. **Treat one Scalping Book as universal** — rejected because other strategies require other Book forms.
3. **Versioned Book and BMS risk domain** — accepted directionally, with detailed grammar deferred.

## Decision

COMP-QMF-RISK owns versioned Book and BMS semantics, money and position-sizing policy, surgical risk controls, and correlation evidence. The recovered Scalping Book is one pattern rather than a global law. (DEC-0065, DEC-0066, DEC-0068, DEC-0080)

## Consequences

Exit ownership remains the DEC-0067 conflict. Book/BMS schemas and BMS cardinality remain GAP-defined. No risk implementation may begin from this provisional boundary alone.
