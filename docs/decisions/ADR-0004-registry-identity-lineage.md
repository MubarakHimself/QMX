---
id: ADR-0004
title: Type-specific identity and graph-shaped lineage
type: adr
status: provisional
component: COMP-QMF-REGISTRY
depends_on: [COMP-QMF-CORE, COMP-QMF-DATA-STORE]
decisions: [DEC-0033, DEC-0035, DEC-0038, DEC-0039, DEC-0041]
sources: [DEC-0033, DEC-0035, DEC-0036, DEC-0038, DEC-0039, DEC-0040, DEC-0041]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 1y
---

# ADR-0004: Type-specific identity and graph-shaped lineage

Date: 2026-08-18. Status: provisional pending operator ratification.

## Context

QMF needs reproducible identity, variants, causal evidence, and promotion records across unlike domain objects. A universal all-fields card and a mandatory graph database were proposed and rejected.

## Options considered

1. **Universal recipe card** — rejected because unlike objects would be forced into one abstract schema (DEC-0034).
2. **Graph database mandate** — rejected for V1 even though lineage is graph-shaped (DEC-0037).
3. **Type-specific identities with append-only edges** — preserves narrow contracts and rebuildable lineage.

## Decision

qmf-registry owns identity, lineage, causality registration preconditions, and attempt gates. Results are content-addressed with event and knowledge time; Bots and Books retain variant lineage; only a human may promote an artifact into the live zone. (DEC-0033, DEC-0035, DEC-0038, DEC-0039, DEC-0041)

## Consequences

The registry kind catalog, edge schema, causality evidence, and attempt semantics remain GAP-defined. Bot-to-confluence cardinality remains the unresolved DEC-0040 conflict and cannot be fixed by this ADR.
