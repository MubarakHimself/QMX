---
id: SCN-0005
title: Uncertain Venue Submission Resolves to UNKNOWN
type: scenario
status: provisional
component: COMP-QMF-VENUE
depends_on: [COMP-QMF-CORE, COMP-QMF-DATA, COMP-CTRADER]
decisions: [DEC-0029, DEC-0059, DEC-0060, DEC-0061, DEC-0109, DEC-0135, DEC-0137, DEC-0138, DEC-0142]
sources: [docs/components/qmf-venue.md, docs/components/ctrader.md, docs/contracts/ct-18-venue-capabilities.yaml, docs/contracts/ct-19-venue-command.yaml, docs/contracts/ct-20-venue-event.yaml, docs/contracts/ct-21-venue-secret-session.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# SCN-0005: Uncertain Venue Submission Resolves to UNKNOWN

This scenario fixes what happens when a venue submission loses transport certainty before a final external outcome arrives: the outcome is `UNKNOWN` — a recorded state, never an error, a retry, a success, a failure, or a flatten. AD-27's four-outcome law and uncertainty protocol are ratified (DEC-0137): a lost-certainty submission is minted as an explicit `UNKNOWN` observation, the command stream blocks, and only an explicit application `resolve_unknown` call clears it. The cTrader venue facts underpinning the transport behavior are ratified (DEC-0135). Execution status: **ratified design; implementation is authorized only through the factory pipeline, never from these docs alone.** [DEC-0137]

## Given

CT-19 (command) and CT-20 (event and reconciliation) are defined by qmf-venue on qmf-core nouns, and per-venue adapters implement them under one neutral port (DEC-0138). The command stream — the unit of `UNKNOWN` blocking, of WriterId ownership, and of the gapless per-writer sequence — is the `(VenueId, account)` pair, coarser than an account binding and strictly finer than a connection; a session-epoch id rides every venue observation (DEC-0137). Every well-formed submission resolves to exactly one of four outcomes — `accepted-by-venue | rejected-by-venue | denied-locally | UNKNOWN` — and every outcome mints an observation record and a journal event; `denied-locally` is an outcome, never a refusal (DEC-0137).

The shared failure shape is ratified: every public venue boundary succeeds or returns a typed refusal carrying category, machine-readable context, and retryability, with `transient venue failure` reserved for a venue failing transiently (DEC-0029) (DEC-0109). The venue exposes no server clock (closed-set proof over the payload-type enums), so receive-time recording is mandatory (DEC-0135). The submission deadline is a declared adapter parameter the application injects — its existence and declaration are mandatory, its value is not QMF's (do-not-default) (DEC-0137). The venue module is the venue-neutral seam whose first adapter targets the cTrader Open API in Python (DEC-0059) (DEC-0060) (DEC-0061).

## When

A future application submits a venue command on a `(VenueId, account)` command stream, and a transport error, timeout, or disconnect occurs before a final external outcome is received.

## Then

The submission resolves to `UNKNOWN` — a state, not an error (DEC-0137). The adapter mints an explicit `UNKNOWN` observation carrying its trigger (`timeout | transport-error | disconnect`), the monotonic elapsed measurement, the wall receive instant, and the submission deadline in force; the observation is recorded verbatim and journaled before any state evaluation (recording precedes interpretation) (DEC-0137).

While the `UNKNOWN` is outstanding, the adapter refuses new commands on that command stream (`transient venue failure`, after-condition = resolution), and `suspend-new` takes local effect instantly; no QMF component retries, assumes an outcome, flattens, or invents a terminal state (DEC-0137). The adapter never clears its own block. The application resolves the `UNKNOWN` from reconciliation read-back evidence — a complete read-back of venue orders, fills, positions, and balance over a stated lookback, with verdict vocabulary `reconciled | drift | unknown` — and makes an explicit typed `resolve_unknown(command identity, resolution ∈ observed-accepted | observed-absent | operator-attested)` call, itself recorded as an observation (DEC-0137).

The order-state machine remains a read-time fold over the recorded observation stream under CT-20's read-resolution rule, never a gate on recording; an observation with no legal transition is recorded, annotated with a typed `out-of-sequence` edge, and forces the owning command to `UNKNOWN` (DEC-0137). Throughout, the sensing pipe never blocks — `UNKNOWN` and reconciliation gate the command pipe only (DEC-0137). Flatten is `close_position`/`close_all` executed mechanically and never adapter-initiated; its authority assignment (VPS-death included) is risk/node-sitting territory, referenced only as a pointer (`tracker/trading-node-notes.md`), never absorbed here (DEC-0142).

## Worked numbers

No retry count, pool size, or submission-deadline value is a QMF constant: the deadline's existence is mandatory but its value is an application-injected adapter parameter under do-not-default, and command retry is prohibited outright — retryability rides typed refusals, a venue `retryAfter` becoming the after-condition (DEC-0137). The ratified cTrader venue facts may be cited as evidence (DEC-0135): 50 requests/second non-historical plus 5 requests/second historical per connection, a 10-second heartbeat bound, an approximately 30-day access token with a never-expiring refresh token, and a one-week historical tick-span cap. The 17:00-New-York daily-bar boundary and BID-derived trend bars that earlier evidence asserted are never hardcoded — they are measured per broker at first connection and re-verified by a continuous monitor, stored as per-broker configuration (`registry:venue_trendbar_price_basis`) (DEC-0135).
