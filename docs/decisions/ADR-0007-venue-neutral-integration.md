---
id: ADR-0007
title: Venue-neutral integration with cTrader first
type: adr
status: provisional
component: COMP-QMF-VENUE
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-CTRADER]
decisions: [DEC-0059, DEC-0060, DEC-0061]
sources: [DEC-0059, DEC-0060, DEC-0061, DEC-0064]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 1y
---

# ADR-0007: Venue-neutral integration with cTrader first

Date: 2026-08-18. Status: provisional pending operator ratification.

## Context

QMF needs a first broker connection without placing cTrader assumptions inside qmf-core or conflating connectivity with future backtesting parity.

## Options considered

1. **MQL implementation** — rejected in favor of the Python cTrader Open API path.
2. **One broker-exam bundle** — rejected; the term is dead and parity belongs to future backtesting.
3. **Small venue-neutral module with a first adapter** — selected.

## Decision

COMP-QMF-VENUE is a small Python integration module. Its first adapter targets cTrader Open API, and its public seam remains neutral enough for later stock and crypto adapters. (DEC-0059, DEC-0060, DEC-0061)

## Consequences

Capability discovery, command fields, order state, idempotency, reconciliation, and secrets remain GAP-defined. Connectivity does not authorize trading, size risk, or claim broker parity.
