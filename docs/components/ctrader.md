---
id: COMP-CTRADER
title: cTrader Open API
type: component-spec
status: provisional
component: COMP-CTRADER
depends_on: []
decisions: [DEC-0030, DEC-0031, DEC-0053, DEC-0059, DEC-0060, DEC-0061, DEC-0065, DEC-0105, DEC-0106, DEC-0107, DEC-0119, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0139, DEC-0141, DEC-0142, DEC-0148, DEC-0158]
sources: [DEC-0030, DEC-0031, DEC-0053, DEC-0059, DEC-0060, DEC-0061, DEC-0065, DEC-0105, DEC-0106, DEC-0107, DEC-0119, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0139, DEC-0141, DEC-0142, DEC-0148, DEC-0158, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ctrader-venue-facts.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ctrader-time-research.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ctrader-primary-verification.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ctrader-rate-limits-research.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ctrader-tick-spot-mechanics-research.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ctrader-depth-and-connectivity-research.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/research-risk/ctrader-sltp-amend-research.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/spotware-org-inventory.md, docs/architecture/dependencies.yaml, docs/contracts/ct-15-external-source-adapter.yaml, docs/contracts/ct-18-venue-capabilities.yaml, docs/contracts/ct-19-venue-command.yaml, docs/contracts/ct-20-venue-event.yaml, docs/contracts/ct-21-venue-secret-session.yaml]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# cTrader Open API

`COMP-CTRADER` is the external cTrader Open API boundary the first Python venue adapter is designed against. QMF owns the translation contracts around this system; QMF does not own cTrader behavior, availability, schemas, accounts, credentials, or execution outcomes. [DEC-0059] [DEC-0060]

The venue design that governs this boundary is ratified: AD-26 (secret lifecycle), AD-27 (venue commands and the uncertainty law), and AD-28 (adapter contract and capability discovery) are recorded as [DEC-0136], [DEC-0137], and [DEC-0138], with the consolidated cTrader venue facts ratified as [DEC-0135] and the cross-AD amendments as [DEC-0141]. Ratification of the design is not authorization to implement: a live or credential-bearing cTrader adapter is built only through the external factory pipeline, never from this document. [DEC-0135] [DEC-0138]

## Authority boundary

May, from QMF's perspective: expose the externally documented capability, observation, command-outcome, and reconciliation surfaces the four venue contracts define, once a per-venue adapter is implemented through the factory pipeline against an operator-approved account. CT-18 through CT-21 now carry ratified design; per-venue adapters implement them, nothing imports `qmf-venue`, and the composition root wires. [DEC-0138]

May never, from QMF's perspective: be described as QMF-owned or QMF-deployed; be assumed available or semantically stable; define QMF risk policy; make an acknowledgement equal risk approval; leak cTrader objects into `qmf-core`; act as an assigned CT-19 caller or authorization producer; or turn a ratified design into permission for a credential-bearing or live operation. Order-path internals, the protection funnel, startup semantics, and flatten authority are trading-node and risk-sitting territory, recorded in `tracker/trading-node-notes.md`, never absorbed here. [DEC-0031] [DEC-0059] [DEC-0061] [DEC-0065] [DEC-0142]

This document records the ratified contract surface and venue facts; it does not authorize credentials, a session, sandbox use, order submission, or live trading. Primary cTrader documentation and an operator-approved safe account remain required before adapter implementation proceeds through the factory. [DEC-0142]

## Interfaces

| Interface | Direction | Contract | Peer |
|---|---|---|---|
| Market-data source observations (ticks, bars, depth, gap-replay backfill, historical paging) | out via CT-10/CT-15 (ratified home; no adapter implemented) | [CT-15](../contracts/ct-15-external-source-adapter.yaml) | COMP-QMF-DATA-INGEST intake; no fifth contract, no new edge [DEC-0138] |
| Capability declaration + per-account venue-observation profile | ratified design; no adapter implemented | [CT-18](../contracts/ct-18-venue-capabilities.yaml) | Owner: COMP-QMF-VENUE |
| Venue command shape (five kinds) | ratified design; caller unassigned | [CT-19](../contracts/ct-19-venue-command.yaml) | Eventual caller: out-of-scope QMX application |
| Event + reconciliation shape | ratified design; no adapter implemented | [CT-20](../contracts/ct-20-venue-event.yaml) | Owner: COMP-QMF-VENUE |
| Secret / session seam | ratified design; no operation permitted | [CT-21](../contracts/ct-21-venue-secret-session.yaml) | Owner: COMP-QMF-VENUE |

## Behavior

cTrader is the first venue integration target, reached through its Open API from Python rather than MQL. The choice does not make cTrader a core assumption or the owner of QMF contracts: a CCXT-class crypto venue or a FIX venue slots in later by declaring a different record through the same neutral port. [DEC-0059] [DEC-0060] [DEC-0138]

Historical or live cTrader observations remain identified as cTrader-source evidence. They cannot be merged silently with a historical source or treated as interchangeable when values disagree. [DEC-0053]

### Platform versus broker

cTrader is a **platform**, not a broker. The platform fixes the protocol and the adapter; the broker fronting it is a per-deployment fact. Which broker fills a cTrader venue slot is deployment configuration, never architecture — opaque `VenueId`/`AccountId` identity and account bindings are sufficient, and no rule here names a broker. IC Markets is the operator's stated intent and deliberately **not** a framework commitment; account-type confirmation is config-time work per broker. A broker's measured behaviors (daily-bar boundary, trendbar price basis) live in the venue-observation profile and per-broker configuration, never in code. [DEC-0139]

### Protocol pinning and SDK stance

The venue protocol artifact is the Spotware `openapi-proto-messages` package, pinned in the AD-6 dependency register at its **integer release tag, currently 91**. A tag change mints a new capability declaration plus re-verification, and bumps a `CT-*` format version only where the wire change alters that contract's public shape. Only the proto **message definitions** are consumed — data, not code. The official OpenApiPy SDK is **reference-only**: its pinned Twisted reactor violates AD-6's platform-imposing prohibition, so **zero Spotware code runs in QMX** and the adapter owns its own transport. [DEC-0141]

### Venue facts — documentation-grade (Bundle A)

The consolidated venue-facts sheet (evidence: `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ctrader-venue-facts.md`, bundles A/B/C, distilled from the cited `ctrader-*.md` and `spotware-org-inventory.md` companions) is ratified as venue facts and standing adapter obligations. The following are documentation-grade and stated as ratified facts. [DEC-0135]

- **Timestamps** are Unix milliseconds UTC asserted **per field** — no global platform statement exists. Named epoch exceptions: trendbar `utcTimestampInMinutes` (minutes), `maintenanceEndTimestamp` (seconds), holiday `holidayDate` (days since epoch), and schedule `startSecond`/`endSecond` (seconds from Sunday 00:00 in the broker zone). The spot-event timestamp unit is genuinely undocumented and verify-or-refused. [DEC-0135]
- **No server clock** exists on the Open API — a closed-set proof over the full payload-type enums (no ping, time, or sync member). Recording the local receive instant is therefore **mandatory** on every inbound event, per AD-8. [DEC-0135]
- **Historical ticks are BID/ASK-selectable** (`ProtoOAQuoteType` required on the tick-data request) — a hard API guarantee. [DEC-0135]
- **Rate limits** are 50 requests/second non-historical plus 5 requests/second historical, **per connection**; breach codes are 108, 11, 67, and 35; no ban or backoff policy is documented. [DEC-0135]
- **Tick history** is newest-first and delta-encoded: the timestamp delta after a first absolute entry is documented; the price delta is staff-demonstrated only and is treated as contract surface with a first-connection assertion. Paging is on `hasMore` only (re-request with a shifted `toTimestamp`); the response is capped at a backend-configured chunk size; a **one-week span cap** is documented and runtime-enforced as error 35. [DEC-0135]
- **Three independent numeric scale systems** exist and must never be unified: (i) market-data wire prices are uint64 in **1/100000**; (ii) execution prices (position price, stop/target, deal execution price, conversion rates) are **raw doubles** crossing the foreign-float boundary — a uniform /100000 would corrupt the execution path; (iii) a `moneyDigits` exponent applies on nine messages (Trader, Position, Deal, ClosePositionDetail, DepositWithdraw, BonusDepositWithdraw, ExpectedMarginRes, MarginChangedEvent, GetPositionUnrealizedPnLRes). Volumes are in cents everywhere (including `lotSize`; depth size ÷100). `ProtoOALightSymbol` carries **no** scaling metadata, so the full `ProtoOASymbol` record is required before any price decode. [DEC-0135] [DEC-0141]
- **Two broker-supplied non-UTC timezone axes** exist: the symbol schedule (`scheduleTimeZone`, intervals in seconds from Sunday 00:00, end exclusive) and holidays (own required `scheduleTimeZone`, `holidayDate` in days, recurring flag). Nothing links either to bar boundaries. [DEC-0135]
- **Heartbeat** is adopted at the safe **10-second** bound (primary sources contradict between 30s proto tolerance and a 10s FAQ demand; the tighter figure wins). Inactivity disconnects are documented. [DEC-0135]
- **Trendbars are gappy by design** — a trendbar exists only where ticks exist. Live trendbars ride inside the spot event, with no dedicated event. [DEC-0135]
- **Swap-free accounts still pay a dated rollover commission** (USD/lot daily, tripled on a declared UTC weekday): "no swap" does not mean "no dated financing." [DEC-0135]

### Demoted claims — measured per broker (Bundle B)

Two claims carry **demoted** 2013-forum-grade evidence and are **never hardcoded**; the ratified treatment replaces each with a measure-per-broker adapter obligation. [DEC-0135]

- **The 17:00-New-York daily-bar boundary** was staff-only, had zero doc/proto corroboration, and carried counter-evidence tying a different daily rollover to broker server time. Treatment: at first connection (and across DST transitions) the adapter **measures** the actual D1 boundary from `utcTimestampInMinutes` and stores it as **per-broker configuration**, re-checking with a continuous background monitor. QMF's own forex 17:00-New-York market-hours calendar remains QMF's accounting rule, independent of venue bars; venue D1 bars are never assumed aligned to it. Once measured and verified, the boundary is minted as a **venue-scoped market-hours calendar identity**, giving venue-native bars a legal BarSpec anchor. [DEC-0135] [DEC-0141]
- **BID-derived trendbars** rested on a cAlgo-scoped staff quote and an ex-staff Open-API claim, with structural corroboration only (bar requests expose no quote-type field). Treatment: first-connection reconciliation of trendbar OHLC against BID tick history per broker and symbol class; the bar's recorded identity carries the verified quote side, or the bars are refused; the permanent fallback builds bars from explicitly BID/ASK-selected ticks. [DEC-0135]

### Verify-or-refuse obligations (Bundle C)

Every undocumented behavior is a **verify-or-refuse** adapter obligation, discharged by the first-connection verification suite and recorded in the venue-observation profile. "UNKNOWN" here is a state, never an error. [DEC-0135] [DEC-0138]

- Spot-event timestamp unit: assert milliseconds by magnitude at startup; an unverified unit **refuses spot evidence**.
- Spot coalescing/conflation: measure via the timestamp opt-in on a liquid symbol; never assume every-tick delivery.
- Rate-window semantics: unknown — throttle conservatively at or below the published per-connection rates; breach signals (108, 11, HTTP-style 429) map to `transient venue failure` typed refusals whose after-condition rides any venue-supplied retry hint. No ban or backoff policy is documented, and pacing/backoff constants are node values under do-not-default — command retry itself stays prohibited. [DEC-0135] [DEC-0137]
- Absent `moneyDigits`: a **typed refusal**, never a default to 2.
- Pip formula (`pipSize = 10^-pipPosition`): validate against known symbols at startup; a failed validation **refuses metadata-derived parameters**.
- Live-trendbar semantics (live-forming versus last-closed, cadence): primary sources contradict; resolve empirically before live bars enter evidence.
- Historical versus non-historical message classification for the 5/50 split: the adapter declares its own conservative classification.
- Trendbar per-period span caps: unpublished; discovered via error-35 handling and recorded as broker facts.

A failed bar-basis reconciliation **refuses bar evidence**; an unmeasured daily boundary leaves venue daily bars **ungoverned**; an absent money exponent **refuses that message's money decode**. Measurements and verification verdicts journal as `data quality`; adapter-initiated state changes (suspend-new, drain, session restart, throttle engaged, reconnect) journal as `control action`. The six-stage live-path latency decomposition is recorded as named rungs with **no numeric budgets** until measured. [DEC-0138]

### Protection amendment mechanics (SL/TP)

The cTrader Open API SL/TP amendment facts are CONFIRMED-PRIMARY and are the standing obligations behind the `amend_protection` command (the fifth CT-19 kind, AD-34) and the CT-18 protection-capability roster. Evidence pointer only: the primary-source study `research-risk/ctrader-sltp-amend-research.md` (messages reference, model messages, error-handling pages, and the Spotware `openapi-proto-messages` proto files); cite [DEC-0148], never the companion, in downstream work. [DEC-0148]

- **An open position's protection amends in one message with absolute prices** — `ProtoOAAmendPositionSLTPReq`, carrying absolute stop-loss and take-profit — **no cancel-replace**. This is the mechanism `amend_protection` maps onto for an open position; QMX never emulates it by cancel-then-place, which would open an unprotected window. [DEC-0148]
- **A pending order amends through its own message** — `ProtoOAAmendOrderReq` — carrying both the absolute and the entry-relative SL/TP forms, plus volume, price, and expiry, so protection on a resting order changes without cancel-replace. [DEC-0148]
- **No dedicated response message exists** for either amend. Confirmation arrives on the **ordinary execution-event surface** (`ProtoOAExecutionEvent`) and failure on the order-error surface (`ProtoOAOrderErrorEvent`); there is no `AmendPositionSLTPRes`/`AmendOrderRes`. The four-outcome law and CT-18's declared acknowledgement modes therefore apply unchanged, and the subject-terminal read-back rule (CT-20) resolves a stop that fills mid-amend as a named outcome rather than a stream-blocking UNKNOWN. [DEC-0148]
- **Absolute protection is documented as NOT SUPPORTED for MARKET orders** on the new-order message (`ProtoOANewOrderReq` absolute `stopLoss`/`takeProfit`), so the **entry-relative** form (`relativeStopLoss`/`relativeTakeProfit`, scaled 1/100000 of a unit of price, resolved against `entryPrice`) is the declared **placement** path for market orders. The reference price the relative distance derives from is declared CT-19 contract surface; because the resting stop may differ from the declared full-loss price by slippage, that declaration stays the plan and is never read back as the observed fill. [DEC-0148] [DEC-0158]
- **Native trailing exists but its algorithm is UNDOCUMENTED.** A server-managed trailing stop exists (the `trailingStopLoss` flag plus a dedicated server-push change event, `ProtoOATrailingSLChangedEvent`); its distance and step algorithm are undocumented in every primary source and **may never be assumed**. Venue-managed trailing is a CT-18 capability, legal only where declared and explicitly opted into by a Book — a **named delegated protection authority** (`authority_kind = venue-delegated`) whose pushed changes enter as ordinary observations and mint a CT-30 control-action record of kind `protection_amendment`. [DEC-0148]
- **Amend atomicity is UNDOCUMENTED** in every primary source — no page or proto comment states partial-failure or transactional behavior. It is therefore a `measured-at-connection` CT-18 field under verify-or-refuse: until the first-connection verification suite establishes it, a Book policy that amends **both** protection sides in one act refuses, and **single-sided amendment is the only legal V1 path**. [DEC-0148] [DEC-0158]
- **A guaranteed-stop class exists** where the account type offers one (the `guaranteedStopLoss` flag, French Risk / GSL-enabled accounts) and is declared as a CT-18 protection-capability field, never assumed. [DEC-0158]

### Depth and connectivity

The depth-and-connectivity findings (evidence: `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ctrader-depth-and-connectivity-research.md`) are ratified. [DEC-0135]

- A **Level-2 resting-liquidity book exists**: differential updates carrying unique quote ids, price in 1/100000, size in cents ÷100. Raw depth is recorded as the verbatim wire payload, never an invented encoding. [DEC-0135] [DEC-0138]
- **No Level-3 / time-and-sales tape exists** — a closed-catalog proof over the message set. [DEC-0135]
- **Demo and live are separate hosts**, requiring **two simultaneous connections**, each serving unlimited accounts of its own environment; the session topology follows this two-connection shape. [DEC-0135] [DEC-0138]

### Secret and token lifecycle

Credential handling follows AD-26: QMF components hold **secret references, never values**. A `SecretValue` never renders — repr, str, serialization, and logging all yield the reference id. The adapter's connection manager is the single component permitted to hold secret values in memory, for a session's lifetime, through a core-defined `SecretStore` port injected at the composition root; values never cross back out. A credential is a one-writer stream: exactly one live refresher per credential, and on rotation the new secret is stored atomically **before** the old is discarded. [DEC-0136]

The cTrader token lifecycle is a ratified venue fact: a **~30-day access token**, a **never-expiring refresh token** treated as the crown-jewel secret, and **cTID re-authorization** as the invalidation anchor. Compromise recovery is a documented, tested drill — cTID re-authorization (invalidating all outstanding refresh tokens), application-credential reset, store replacement, session restart — and testing uses demo credentials only. [DEC-0135] [DEC-0136]

### Foreign money, foreign time, and foreign floats are evidence

cTrader's raw values are foreign evidence stored verbatim, never trusted as framework values. Integer money and price fields keep their declared scales (the 1/100000 wire price scale, per-symbol `digits`, per-account `moneyDigits`); conversion into Money/Price/Quantity happens only at the venue adapter's named money-path conversion boundary with an explicitly stated rounding mode; corrections are annotations, never rewrites. Timestamps are stored verbatim with declared zone, offset, and resolution, and conversions are derived under lineage. [DEC-0105] [DEC-0106] [DEC-0135]

A cTrader value delivered as a **binary float is evidence, never identity**: it crosses AD-7's named boundary at receipt to a scaled integer at a per-value-class pinned target scale — execution price to the instrument's declared `digits`, money to the account's declared money exponent (an absent exponent being a refusal), market data to the declared wire scale — with a declared, identity-bearing rounding mode; the raw float is retained only as integrity-checked provenance and is never the value a consumer reads. [DEC-0141]

### Node boundary

Trading-node runtime material stays out of this spec. The order path, protection funnel, startup semantics, and flatten-authority assignment are node and risk-sitting territory; anything discussed about the trading node is durably held in `tracker/trading-node-notes.md`, and this document references it as a pointer only. The trading-node order-path study and node corpus brief remain reference-only evidence. [DEC-0142]

<!-- no-diagram: external system internals are outside QMF authority; only CT-15 and CT-18 through CT-21 are documented -->

## Configuration

| Variable | Registry key | Notes |
|---|---|---|
| Trend-bar price basis | `registry:venue_trendbar_price_basis` | Never hardcoded: measured per broker at first connection and re-checked by a continuous background monitor, stored in the venue-observation profile and per-broker configuration; the bar identity records the verified quote side or the bars are refused. [DEC-0135] |
| Venue daily-bar boundary | `registry:venue_daily_bar_boundary` | Measured per broker from `utcTimestampInMinutes` (and across DST), stored as per-broker configuration; once verified, minted as a venue-scoped market-hours calendar identity that anchors venue-native BarSpec. Until measured, venue daily bars are ungoverned observations. [DEC-0135] [DEC-0141] |
| Broker / venue identity | `registry:venue_broker_identity` | Deployment configuration, never architecture: opaque `VenueId`/`AccountId` identity and account bindings are sufficient; IC Markets is operator intent, not a commitment. [DEC-0139] |
| Instrument identity shape | `registry:instrument_identity_shape` | QMF identity is (venue, venue's own symbol), the symbol opaque and never parsed; external cTrader symbols do not become core identity automatically; the full `ProtoOASymbol` record is a prerequisite for price decode. [DEC-0107] [DEC-0135] |
| Venue protocol artifact | `registry:venue_protocol_artifact` | Spotware `openapi-proto-messages` integer release tag, currently 91, pinned in the AD-6 register; a tag change mints a new capability declaration plus re-verification. Message definitions only; zero Spotware code runs. [DEC-0141] |
| Submission deadline; retry / pool / health constants | — | Do-not-default: their declaration is mandatory, their numeric values are node configuration injected by the application, never QMF defaults. [DEC-0137] |
| Credentials and session material | — | Secret references not values, injected at the composition root from the deployment environment's protected store; the connection manager is the sole in-memory holder. No credential-bearing operation proceeds outside the factory pipeline. [DEC-0136] |

## Failure modes

| # | Condition | Behavior | Cites |
|---|---|---|---|
| FM-1 | A future cTrader adapter observes unavailability or a terminated session. | Fail-closed: in-flight commands become UNKNOWN; recovered fills commit through evidence before a session reports healthy; session recovery never resubmits a command. No adapter is implemented until the factory pipeline authorizes it. | DEC-0137 |
| FM-2 | A credential-bearing operation is requested. | Governed by the AD-26 secret lifecycle: references not values, single in-memory holder, one refresher per credential, store-before-discard on rotation. The operation proceeds only through the factory pipeline against an operator-approved account. | DEC-0136 |
| FM-3 | cTrader reports an unsupported capability, command, symbol, scope, or account mode. | The adapter must not emulate support silently; invoking anything undeclared is an `unsupported capability` refusal, and an unsupported close scope is never emulated at a wider scope. | DEC-0138 |
| FM-4 | A command acknowledgement is absent, duplicated, delayed, or inconsistent with read-back state. | Four-outcome law: every well-formed submission resolves to accepted-by-venue, rejected-by-venue, denied-locally, or UNKNOWN. A transport error, timeout, or disconnect yields UNKNOWN — a state, minted as an explicit observation carrying its trigger and the injected submission deadline. While UNKNOWN is outstanding the adapter refuses new commands on that stream and never clears its own block; unblocking is an explicit `resolve_unknown` call by the application. `denied-locally` is an outcome, never a refusal. | DEC-0137 |
| FM-5 | cTrader data disagrees with another source. | Both source identities and observations remain separate through CT-15/CT-10; no silent merge is permitted. Disagreements are recorded as CT-07 `corroborates` / `disagrees-with` edges. | DEC-0053, DEC-0119 |
| FM-6 | External API behavior changes without a QMF contract version change. | A Spotware release-tag change mints a new capability declaration plus re-verification; the adapter cannot claim conformance until the changed behavior is re-verified and any incompatible QMF mapping is versioned. | DEC-0138, DEC-0141 |
| FM-7 | A message carries an absent `moneyDigits`, an unverified spot-timestamp unit, or fails bar-basis/pip validation. | Verify-or-refuse: an absent money exponent refuses that message's money decode; an unverified spot-timestamp unit refuses spot evidence; a failed bar-basis reconciliation refuses bar evidence; a failed pip-formula validation refuses metadata-derived parameters. No value is defaulted. | DEC-0135, DEC-0138 |
| FM-8 | A sink write fails, or a partial multi-room write occurs, while the connection manager holds the WriterId. | A `storage failure` refusal blocks the command stream in the writer-holding component (the connection manager sees every sink refusal); the sensing pipe is unaffected; the partial write is journaled on recovery. | DEC-0138 |

## Related

Decisions: DEC-0053, DEC-0059, DEC-0060, DEC-0061, DEC-0105, DEC-0106, DEC-0107, DEC-0119, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0139, DEC-0141, DEC-0142, DEC-0148 (AD-34 `amend_protection` and the cTrader SL/TP amend facts), DEC-0158 (risk-gate cross-AD amendments: absolute-unsupported-for-MARKET placement, protection-capability roster, `converted_by = venue`). Scenarios: [SCN-0005 uncertain venue submission](../scenarios/SCN-0005-uncertain-venue-submission.md). Component: [COMP-QMF-VENUE](qmf-venue.md). Node pointer: `tracker/trading-node-notes.md`. Knowledge: none drafted. Evidence pointer (never cited in place of a DEC): `research-risk/ctrader-sltp-amend-research.md`.
