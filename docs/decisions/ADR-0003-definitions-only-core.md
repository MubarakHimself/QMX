---
id: ADR-0003
title: Definitions-only qmf-core
type: adr
status: provisional
component: COMP-QMF-CORE
depends_on: []
decisions: [DEC-0022, DEC-0026, DEC-0027, DEC-0028, DEC-0029, DEC-0030, DEC-0031, DEC-0127, DEC-0134]
sources: [DEC-0022, DEC-0026, DEC-0027, DEC-0028, DEC-0029, DEC-0030, DEC-0031, DEC-0032, DEC-0127, DEC-0134]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 1y
---

# ADR-0003: Definitions-only qmf-core

Date: 2026-08-18. Status: provisional pending operator ratification.

## Context

Every later QMF component needs exact shared language without inheriting a broker, event loop, asset class, or deployment model.

## Options considered

1. **Broad kernel** — rejected; the term and runtime boundary are dead (DEC-0023).
2. **Asset-specific core** — rejected because later equities and crypto consumers must not force a foundational rewrite.
3. **Definitions-only library** — selected, with unresolved representation choices left as explicit gaps.

## Decision

qmf-core defines exact money and time primitives, asset-neutral market nouns, typed refusals, deterministic fingerprints, and version metadata. It contains no broker, event loop, backtest, downloader, trading-node runtime, or Forex-specific policy. (DEC-0022, DEC-0026, DEC-0027, DEC-0028, DEC-0029, DEC-0030, DEC-0031)

## Consequences

Later components share one versioned vocabulary. Four of the six freeze choices are now ratified (DEC-0106 time encoding, DEC-0107 instrument identity, DEC-0110 result label, DEC-0127 canonical indicator arithmetic); the remaining two are tracked by DEC-0134 (DEC-0032 and DEC-0124 superseded); no implementation may infer those fields or algorithms.
