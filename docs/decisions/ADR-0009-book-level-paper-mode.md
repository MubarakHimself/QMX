---
id: ADR-0009
title: Book-level paper mode without Bot twins
type: adr
status: provisional
component: COMP-QMF-RISK
depends_on: [COMP-QMF-REGISTRY, COMP-QMF-DATA]
decisions: [DEC-0070]
sources: [DEC-0070, SRC-01-C0022, SRC-01-C0023]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 90d
---

# ADR-0009: Book-level paper mode without Bot twins

Date: 2026-08-18. Status: provisional and requires operator confirmation of the transcript recap.

## Context

A proposal ran live Bots beside paper twins or attached one Bot to several Books. The recorded correction moves paper operation to the Book and rejects the parallel-twin model.

## Options considered

1. **Parallel Bot paper twins** — dead because it duplicates Bot identity and Book attachment (DEC-0069).
2. **Special blackout simulator** — dead because ordinary recorders continue through blackout periods (DEC-0071).
3. **Book-level paper mode** — preserves one Bot-to-Book relationship and continuous evidence.

## Decision

Paper operation is a Book-level state: a Book that cannot trade live directs its attached Bot activity to the Book's paper account so evidence continues. (DEC-0070)

## Consequences

The direct operator wording is absent from the SRC-01-C0022 transcript export; DEC-0070 survives through the immediate SRC-01-C0023 recap. Account mapping, transitions, and duplicate prevention remain GAP-defined until the operator confirms the recap.
