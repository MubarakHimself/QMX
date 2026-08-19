---
id: ADR-0006
title: Separate wrapped indicators from causal structure
type: adr
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-DATA]
decisions: [DEC-0055, DEC-0056, DEC-0058]
sources: [DEC-0055, DEC-0056, DEC-0058]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 1y
---

# ADR-0006: Separate wrapped indicators from causal structure

Date: 2026-08-18. Status: provisional pending operator ratification.

## Context

Established arithmetic indicators and QMX-defined causal levels, zones, and market structure have different ownership, test oracles, and execution costs.

## Options considered

1. **Reimplement established formulas** — rejected because QMF can wrap suitable arithmetic libraries behind owned contracts.
2. **One library for all analytical work** — rejected because heavy research analytics and proprietary causal structure have different consumers.
3. **Separate indicator and structure libraries** — selected.

## Decision

qmf-indicators wraps TA-Lib-class arithmetic through QMF-owned interfaces and keeps light deterministic work separate from heavy MIS or research analysis. qmf-structure owns QMX-defined causal levels, zones, and market-structure components. (DEC-0055, DEC-0056, DEC-0058)

## Consequences

Indicator protocol, oracle, and tolerance remain GAP-defined. Structure families and confirmation rules remain GAP-defined. Neither library may import strategy-entry semantics or heavy MIS responsibilities.
