---
id: COMP-CTRADER
title: cTrader Open API
type: component-spec
status: provisional
component: COMP-CTRADER
depends_on: []
decisions: [DEC-0030, DEC-0031, DEC-0053, DEC-0059, DEC-0060, DEC-0061, DEC-0065]
sources: [DEC-0030, DEC-0031, DEC-0053, DEC-0059, DEC-0060, DEC-0061, DEC-0065, docs/architecture/dependencies.yaml, docs/contracts/ct-15-external-source-adapter.yaml, docs/contracts/ct-18-venue-capabilities.yaml, docs/contracts/ct-19-venue-command.yaml, docs/contracts/ct-20-venue-event.yaml, docs/contracts/ct-21-venue-secret-session.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# cTrader Open API

`COMP-CTRADER` is the external cTrader Open API boundary used by the first Python venue adapter. QMF owns the translation contracts around this system; QMF does not own cTrader behavior, availability, schemas, accounts, credentials, or execution outcomes. [DEC-0059] [DEC-0060]

## Authority boundary

May, from QMF's perspective and only after the operator authorizes an account/test boundary and the governing gaps are ratified: expose externally documented capability, observation, command-outcome, and reconciliation information to future adapters. CT-18 through CT-21 currently reserve shapes only; no active QMF V1 command, event, capability, or session handoff exists. [DEC-0053] [DEC-0059]

May never, from QMF's perspective: be described as QMF-owned or QMF-deployed; be assumed available or semantically stable; define QMF risk policy; make an acknowledgement equal risk approval; leak cTrader objects into qmf-core; act as an assigned CT-19 caller or authorization producer; or turn a provisional spec into permission for a credential-bearing or live operation. [DEC-0031] [DEC-0059] [DEC-0061] [DEC-0065]

This document does not verify external API details and does not authorize credentials, a session, sandbox use, order submission, or live trading. Primary cTrader documentation and an operator-approved safe account remain required before adapter implementation.

## Interfaces

| Interface | Direction | Contract | Peer |
|---|---|---|---|
| External market-data source observations | out (reserved) | [CT-15](../contracts/ct-15-external-source-adapter.yaml) | Intended: COMP-QMF-DATA-INGEST; not wired |
| Reserved capability shape; no active consumer | — (reserved) | [CT-18](../contracts/ct-18-venue-capabilities.yaml) | Intended normalization owner: COMP-QMF-VENUE |
| Reserved command shape; caller unassigned | — (reserved) | [CT-19](../contracts/ct-19-venue-command.yaml) | Eventual caller: out-of-scope QMX application |
| Reserved event/reconciliation shape; no active consumer | — (reserved) | [CT-20](../contracts/ct-20-venue-event.yaml) | Intended normalization owner: COMP-QMF-VENUE |
| Reserved credential/session seam; no operation permitted | — (reserved) | [CT-21](../contracts/ct-21-venue-secret-session.yaml) | Intended normalization owner: COMP-QMF-VENUE |

## Behavior

cTrader is the first venue integration target, accessed through its Open API from Python rather than MQL. The choice does not make cTrader a core assumption or the owner of QMF contracts. [DEC-0059] [DEC-0060] [DEC-0061]

Historical or live cTrader observations remain identified as cTrader-source evidence. They cannot be merged silently with a historical source or treated as interchangeable when values disagree. [DEC-0053]

The external system remains authoritative only for what it actually reports. `COMP-QMF-VENUE` is the intended owner of future normalization, but CT-18 through CT-21 are reserved and unwired; risk permission and CT-19 authorization evidence remain unassigned under GAP-0036 and GAP-0039. [DEC-0059] [DEC-0065]

CT-21 is an interim no-operation gate. No credential-bearing integration proceeds while GAP-0035 is open, and this spec adopts no secret-location, storage, injection, redaction, or lifecycle recommendation as a settled invariant. [DEC-0059] [DEC-0060]

`GAP(GAP-0035): Verify credential, token, expiry, refresh, rotation, revocation, and compromise behavior against primary cTrader documentation and a safe account.`

`GAP(GAP-0036): Verify command states, idempotency support, retry constraints, reconciliation reads, outage behavior, and failure outcomes.`

`GAP(GAP-0037): Confirm the broker, account type, safe test environment, symbol catalog, and trend-bar price basis.`

`GAP(GAP-0038): Ratify the QMF-neutral capability, subscription, command, event, and refusal mapping.`

<!-- no-diagram: external system internals are outside QMF authority; only CT-15 and CT-18 through CT-21 are documented -->

## Configuration

| Variable | Registry key | Notes |
|---|---|---|
| Trend-bar price basis | `registry:venue_trendbar_price_basis` | QMF mapping is null until GAP-0037; cTrader's external representation must be verified. |
| Instrument identity shape | `registry:instrument_identity_shape` | QMF identity is null until GAP-0009; external symbols do not become core identity automatically. |
| Credentials and session material | — | `GAP(GAP-0035): Location, storage, injection, redaction, and lifecycle rules are unresolved; no credential-bearing operation may proceed.` |

## Failure modes

| # | Condition | Behavior | Cites |
|---|---|---|---|
| FM-1 | A future cTrader adapter observes unavailability or a terminated session. | No adapter implementation is authorized. `GAP(GAP-0036): Define the complete state table and observable CT-20/refusal mapping before code exists.` | DEC-0059 |
| FM-2 | A credential-bearing operation is requested. | The operation is a no-op while GAP-0035 is open; this spec defines neither secret storage nor recovery. | DEC-0059, DEC-0060 |
| FM-3 | cTrader reports an unsupported capability, command, symbol, or account mode. | The adapter must not emulate support silently. `GAP(GAP-0038): Define the CT-18 and CT-04 result.` | DEC-0061 |
| FM-4 | A future command acknowledgement could be absent, duplicated, delayed, or inconsistent with read-back state. | Uncertain submission is implementation-blocking. `GAP(GAP-0036): Define command identity, every state and allowed transition, read-back and cursor semantics, retry and duplicate rules, terminal and uncertain states, new-command gating, journal evidence, and human flattening authority; no recovery behavior is inferred.` | DEC-0059, DEC-0065 |
| FM-5 | cTrader data disagrees with another source. | Both source identities and observations remain separate through CT-15/CT-10; no silent merge is permitted. `GAP(GAP-0030): Define comparison evidence.` | DEC-0053 |
| FM-6 | External API behavior changes without a QMF contract version change. | The adapter cannot claim conformance until the changed behavior is verified and any incompatible QMF mapping is versioned. | DEC-0030, DEC-0061 |

## Related

Decisions: DEC-0053, DEC-0059, DEC-0060, DEC-0061. Scenarios: [SCN-0005 uncertain venue submission](../scenarios/SCN-0005-uncertain-venue-submission.md). Knowledge: none drafted.
