---
id: COMP-QMF-VENUE
title: QMF Venue Module
type: component-spec
status: provisional
component: COMP-QMF-VENUE
depends_on: [COMP-QMF-CORE, COMP-QMF-DATA]
decisions: [DEC-0009, DEC-0029, DEC-0030, DEC-0031, DEC-0048, DEC-0059, DEC-0060, DEC-0061, DEC-0065]
sources: [DEC-0009, DEC-0029, DEC-0030, DEC-0031, DEC-0048, DEC-0059, DEC-0060, DEC-0061, DEC-0064, DEC-0065, docs/architecture/dependencies.yaml, docs/contracts/ct-01-money-quantity.yaml, docs/contracts/ct-02-time-calendar.yaml, docs/contracts/ct-03-instrument-identity.yaml, docs/contracts/ct-04-typed-refusal.yaml, docs/contracts/ct-05-version-fingerprint.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-13-journal.yaml, docs/contracts/ct-18-venue-capabilities.yaml, docs/contracts/ct-19-venue-command.yaml, docs/contracts/ct-20-venue-event.yaml, docs/contracts/ct-21-venue-secret-session.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# QMF Venue Module

`COMP-QMF-VENUE` is the provisional middleware seam intended to translate an external venue into QMF observations and reserved capability, command, event, and session shapes. Its first intended external peer is the cTrader Open API through Python; the backend shapes remain venue-neutral and unwired. [DEC-0059] [DEC-0060] [DEC-0061]

## Authority boundary

May, after the governing gaps are ratified: normalize venue capabilities and observations; resolve venue identities after CT-03 is completed; produce CT-10 source observations into `COMP-QMF-DATA`; reserve CT-18 through CT-21 shapes; and emit journal evidence through CT-13. CT-18 and CT-20 have no active QMF V1 consumer, and CT-19 has no assigned caller, authorization producer, or authorization-evidence owner. [DEC-0048] [DEC-0059] [DEC-0061]

May never: decide whether a trade is permitted; size a position; own Book, BMS, exit, or portfolio policy; manufacture an approval or fill; write a physical store directly; run the trading-node loop; use MQL for the first adapter; revive the dead bundled connection-and-parity design cited by DEC-0063; or absorb future backtesting work. [DEC-0009] [DEC-0060] [DEC-0063] [DEC-0064] [DEC-0065]

This provisional spec does not authorize a live connection, credential use, order submission, or deployment. Live-facing work remains blocked by GAP-0035 through GAP-0038 and by an operator-approved external test boundary.

## Interfaces

| Interface | Direction | Contract | Peer |
|---|---|---|---|
| Exact money, price, and quantity values | in | [CT-01](../contracts/ct-01-money-quantity.yaml) | COMP-QMF-CORE |
| Exact time and trading-calendar values | in | [CT-02](../contracts/ct-02-time-calendar.yaml) | COMP-QMF-CORE |
| Instrument and venue identity | in | [CT-03](../contracts/ct-03-instrument-identity.yaml) | COMP-QMF-CORE |
| Typed refusals | out | [CT-04](../contracts/ct-04-typed-refusal.yaml) | COMP-QMF-CORE |
| Version, fingerprint, and compatibility values | in/out | [CT-05](../contracts/ct-05-version-fingerprint.yaml) | COMP-QMF-CORE |
| Normalized source observations | out | [CT-10](../contracts/ct-10-source-observation.yaml) | COMP-QMF-DATA |
| Journal evidence | out (reserved) | [CT-13](../contracts/ct-13-journal.yaml) | Intended: COMP-QMF-DATA; not wired |
| Reserved venue capabilities; no active consumer | out (reserved) | [CT-18](../contracts/ct-18-venue-capabilities.yaml) | Intended: COMP-QMF-DATA, COMP-QMF-RISK |
| Reserved venue command transport; caller unassigned | in (reserved) | [CT-19](../contracts/ct-19-venue-command.yaml) | Eventual caller: out-of-scope QMX application |
| Reserved venue event and reconciliation evidence; no active consumer | out (reserved) | [CT-20](../contracts/ct-20-venue-event.yaml) | Intended: COMP-QMF-DATA, COMP-QMF-RISK |
| Reserved credential/session seam; no operation permitted | in/out (reserved) | [CT-21](../contracts/ct-21-venue-secret-session.yaml) | Intended: COMP-CTRADER |

## Behavior

The intended design is cTrader-first connectivity without putting cTrader objects, Forex-only assumptions, or deployment behavior into qmf-core. Later crypto and stock adapters are expected to use the same neutral seams rather than changing foundational contracts, but CT-18 through CT-21 remain reserved and unwired. [DEC-0031] [DEC-0059] [DEC-0061]

CT-19 reserves a transport shape for an eventual out-of-scope QMX application. No QMF V1 caller, authorization producer, or authorization-evidence owner is assigned; GAP-0036 and GAP-0039 therefore block every live command path. CT-20 likewise has no active downstream consumer. [DEC-0059] [DEC-0065]

CT-21 is an interim no-operation gate: no credential-bearing integration may proceed until GAP-0035 is ratified. Secret locations, storage, injection, redaction, and lifecycle behavior remain unresolved; this spec does not adopt the gap report's recommendation as an invariant. [DEC-0059] [DEC-0060]

The bundled connection-and-parity design is dead. Connection behavior remains separate from future broker-versus-simulation parity. [DEC-0063] [DEC-0064]

`GAP(GAP-0035): Ratify secret location, scope, expiry, refresh, rotation, revocation, compromise recovery, and safe test environment before CT-21 is implemented.`

`GAP(GAP-0036): Ratify the order state machine, idempotency, reconciliation, retry, outage, duplicate, and flattening-authority behavior before CT-19 or CT-20 is implemented.`

`GAP(GAP-0037): Confirm the first broker/account and price basis before cTrader market-data mapping is frozen.`

`GAP(GAP-0038): Ratify capability, command, event, and optional-feature schemas before the neutral port is implemented.`

<!-- no-diagram: CT-18 through CT-21 are reserved and unwired; drawing an active Risk-to-Venue, Venue-to-cTrader, or Venue-to-Data/Risk command-event graph would invent callers, authorization evidence, or consumers blocked by GAP-0035 through GAP-0039 -->

## Configuration

| Variable | Registry key | Notes |
|---|---|---|
| Trend-bar price basis | `registry:venue_trendbar_price_basis` | Null until GAP-0037 selects bid, ask, mid, or provider-native handling. |
| Instrument identity shape | `registry:instrument_identity_shape` | Null until GAP-0009 resolves venue qualification and aliases. |
| Typed refusal codes | `registry:typed_refusal_codes` | Null until GAP-0011 defines external and policy failure codes. |
| Secret/session configuration | — | `GAP(GAP-0035): Location, storage, injection, redaction, and lifecycle rules are unresolved; no credential-bearing operation may proceed.` |

## Failure modes

| # | Condition | Behavior | Cites |
|---|---|---|---|
| FM-1 | A future caller requests an unsupported capability or command. | No active CT-18 consumer or CT-19 caller exists, so no command is submitted. `GAP(GAP-0038): Define capability and refusal mapping before implementation.` | DEC-0029, DEC-0061 |
| FM-2 | A credential-bearing operation is requested. | The operation is a no-op while GAP-0035 is open. This spec defines neither credential storage nor recovery behavior. | DEC-0059, DEC-0060 |
| FM-3 | A future submission could have an uncertain outcome because a connection fails or times out. | Implementation is blocked. `GAP(GAP-0036): Define a complete command state table, allowed transitions, command identity, read-back and cursor semantics, retry and duplicate rules, terminal and uncertain states, new-command gating, journal evidence, and human flattening authority before any submission code exists.` | DEC-0059, DEC-0065 |
| FM-4 | The same future command is presented more than once. | No submission code may exist until GAP-0036 defines idempotency, duplicate behavior, and state transitions; this spec invents no recovery rule. | DEC-0029, DEC-0059 |
| FM-5 | A future acknowledgement, fill, or account state conflicts with local evidence. | CT-20 is reserved and unwired. `GAP(GAP-0036): Define the reconciliation result and consumer before implementation; no risk state is inferred.` | DEC-0048, DEC-0059 |
| FM-6 | Journal persistence is unavailable. | The module must not bypass qmf-data by writing a store directly. `GAP(GAP-0025): Define the caller-visible failure and safe continuation rule.` | DEC-0048 |

## Related

Live decisions: DEC-0009, DEC-0029, DEC-0030, DEC-0031, DEC-0048, DEC-0059, DEC-0060, DEC-0061, DEC-0065. Out-of-scope decision: DEC-0064. Dead decision: DEC-0063. Scenarios: [SCN-0005 uncertain venue submission](../scenarios/SCN-0005-uncertain-venue-submission.md), [SCN-0008 pair-scoped news](../scenarios/SCN-0008-pair-scoped-news.md). Knowledge: none drafted.
