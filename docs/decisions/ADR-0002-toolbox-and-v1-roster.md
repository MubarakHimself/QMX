---
id: ADR-0002
title: QMF toolbox boundary and V1 roster
type: adr
status: provisional
depends_on: []
decisions: [DEC-0008, DEC-0009, DEC-0011, DEC-0013, DEC-0017, DEC-0019, DEC-0024]
sources: [DEC-0008, DEC-0009, DEC-0011, DEC-0013, DEC-0017, DEC-0019, DEC-0024]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 1y
---

# ADR-0002: QMF toolbox boundary and V1 roster

Date: 2026-08-18. Status: provisional pending operator ratification.

## Context

Earlier designs alternated among a broad runtime kernel, a whole project called minimal core, and adoption of another trading framework's contracts. The later operator correction defines a reusable foundation with locally owned domain semantics.

## Options considered

1. **Application or runtime kernel** — rejected because loops, schedules, orchestration, and product UI belong to consuming applications.
2. **Foreign platform contract** — rejected because QMX must own its domain contracts while remaining free to wrap suitable dependencies.
3. **Open Python toolbox with a fixed V1 roster** — selected as the narrow reusable foundation.

## Decision

QMF V1 is an open Python toolbox composed of five libraries—qmf-core, qmf-registry, qmf-data, qmf-indicators, and qmf-structure—and two small modules—venue and risk. QML names a future Bot domain, not the framework. (DEC-0008, DEC-0009, DEC-0011, DEC-0013, DEC-0017, DEC-0019, DEC-0024)

## Consequences

Consumer applications own runtime lifecycle. QMF owns its stable domain contracts, permits suitable wrapped dependencies, and excludes application behavior unless a later ratified contract admits it.
