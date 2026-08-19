---
id: SCN-0005
title: Uncertain Venue Submission Is Not Buildable
type: scenario
status: provisional
component: COMP-QMF-VENUE
depends_on: [COMP-QMF-CORE, COMP-QMF-DATA, COMP-CTRADER]
decisions: [DEC-0029, DEC-0059, DEC-0060, DEC-0061]
sources: [docs/components/qmf-venue.md, docs/components/ctrader.md, docs/contracts/ct-18-venue-capabilities.yaml, docs/contracts/ct-19-venue-command.yaml, docs/contracts/ct-20-venue-event.yaml, docs/contracts/ct-21-venue-secret-session.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# SCN-0005: Uncertain Venue Submission Is Not Buildable

This scenario prevents a timeout from being converted into an invented retry, success, failure, or flattening policy. Execution status: **blocked specification**. [DEC-0059] [DEC-0061]

## Given

CT-19 is reserved and unwired: no QMF V1 caller, authorization producer, or authorization-evidence owner is assigned. CT-20 is also reserved, so there is no ratified command identity, state machine, read-back query, event ordering, reconciliation completion rule, or evidence sink. [DEC-0029] [DEC-0059]

`GAP(GAP-0035): Ratify the credential and session lifecycle.`

`GAP(GAP-0036): Ratify idempotency, order states, reconciliation, retry, outage, journal-failure, and flattening authority.`

`GAP(GAP-0037): Ratify the first broker/account and price basis.`

`GAP(GAP-0038): Ratify the cross-venue adapter contract.`

## When

A future application submits a venue command and loses transport certainty before receiving a final external outcome.

## Then

There is no executable QMF behavior yet. An implementation must not retry, assume success, assume failure, flatten, resume new commands, or persist invented state. The sequence must remain blocked until CT-18 through CT-21 and GAP-0036 define every authority and terminal/uncertain transition. [DEC-0059] [DEC-0061]

## Worked numbers

No retry count, timeout, cursor, or reconciliation budget is ratified. The executable fixture must draw every such value from a future registry entry or contract field.
