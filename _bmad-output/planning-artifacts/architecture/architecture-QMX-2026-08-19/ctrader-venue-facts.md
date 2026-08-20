# cTrader venue facts — consolidated ratification sheet (2026-08-20)

Distilled from: ctrader-time-research.md (2026-08-19 original), ctrader-primary-verification.md (workflow synthesis, 5/7 questions + adversarial verify), ctrader-rate-limits-research.md, ctrader-tick-spot-mechanics-research.md, spotware-org-inventory.md. This sheet is the ratification target for the venue-facts portion of GAP-0037/0038.

## Bundle A — documentation-grade facts (primary-doc / primary-proto)

- **A1 Timestamps:** Unix ms UTC asserted per-field (no global statement exists). Exceptions: `ProtoOATrendbar.utcTimestampInMinutes` (minutes), `ProtoOAErrorRes.maintenanceEndTimestamp` (seconds), `ProtoOAHoliday.holidayDate` (days since epoch), schedule `startSecond`/`endSecond` (seconds from Sunday 00:00, broker zone). Four unit-less list-request fields provably ms via the 2147483646000 bound; `ProtoOASpotEvent.timestamp` unit genuinely undocumented (→ C1).
- **A2 No server clock** on the Open API — closed-set proof over the full payload-type enums (no ping/time/sync member; ProtoOAPingReq does not exist). Receive-time recording is mandatory, per AD-8. FIX API `SendingTime` = out-of-scope open item.
- **A3 Historical ticks selectable BID/ASK** (`ProtoOAQuoteType` required on `ProtoOAGetTickDataReq`) — hard API guarantee.
- **A4 Rate limits:** 50 req/s non-historical + 5 req/s historical, **per connection** (Getting-started verbatim). Breach codes: 108 REQUEST_FREQUENCY_EXCEEDED, ProtoErrorCode 11 BLOCKED_PAYLOAD_TYPE, 67 CONNECTIONS_LIMIT_EXCEEDED (numeric cap unpublished), 35 INCORRECT_BOUNDARIES (oversized spans), HTTP-style 429. No documented ban/backoff. Historical/non-historical message classification unpublished (→ C7).
- **A5 Tick history mechanics:** newest-first; timestamp delta-encoded after first absolute entry (documented); **price also delta-encoded but staff-demonstrated only, never documented** — adapter treats the decode as contract surface with a first-connection assertion; response capped at backend-configured `chunkSize`, paging on `hasMore` only (re-request with shifted `toTimestamp`); 1-week span cap documented on the symbol-data page (604800000 ms), runtime-enforced as error 35.
- **A6 Three independent numeric scale systems:** (i) market-data prices = uint64 in 1/100000 (SpotEvent bid/ask/sessionClose, relative SL/TP; the tick/trendbar divisor is docs-page-attested, not proto-attested); (ii) **execution prices are raw doubles** (position price, SL/TP, deal executionPrice, conversion rates) — uniform /100000 would corrupt the execution path; (iii) `moneyDigits` exponent on NINE messages (Trader, Position, Deal, ClosePositionDetail, DepositWithdraw, BonusDepositWithdraw, ExpectedMarginRes, MarginChangedEvent, GetPositionUnrealizedPnLRes — where it is `required`). Volumes in cents everywhere (incl. `lotSize`; DOM size ÷100). `ProtoOALightSymbol` carries NO scaling metadata — full `ProtoOASymbol` required before any price decode.
- **A7 Two broker-supplied non-UTC timezone axes:** symbol schedule (`scheduleTimeZone`, intervals in seconds from Sunday 00:00, endSecond exclusive) AND holidays (own `required scheduleTimeZone`, `holidayDate` in days, recurring flag). Nothing links these to bar boundaries (→ B1).
- **A8 Heartbeat:** proto tolerates 30s, FAQ demands 10s — primary sources contradict; the 10s figure is adopted as the safe bound. Inactivity disconnects are documented.
- **A9 Streaming behavior:** trendbars only exist where ticks exist (gappy by design, FAQ verbatim); spot events may carry one side or neither; spot timestamps are opt-in (`subscribeToSpotTimestamp`); subscribe yields a technical snapshot event; unsubscribe is not instantaneous; live trendbars ride inside `ProtoOASpotEvent.trendbar` — no dedicated event.
- **A10 Swap machinery:** `swapLong`/`swapShort` doubles + `swapCalculationType {PIPS, PERCENTAGE, POINTS}`, `swapTime` in minutes from 00:00 UTC; swap-free (`ProtoOATrader.swapFree`) accounts pay `rolloverCommission` (USD/lot daily, tripled on a declared UTC weekday) — confirms AD-8's note that swap-free ≠ no dated financing.

## Bundle B — demoted claims: broker-scoped empirical checks, never invariants

- **B1 17:00-NY daily boundary:** staff-only (one 2013 forum sentence), zero doc/proto corroboration, counter-evidence on record (a primary doc ties a different daily rollover to broker server time). Treatment: at first connection (and across DST transitions) the adapter derives the actual D1 boundary from `utcTimestampInMinutes` and stores it as **per-broker configuration**. QMF's own forex-17NY market-hours calendar (AD-8) remains OUR accounting rule, independent of venue bars; venue D1 bars are never assumed aligned to it. This empirically settles the 23h/25h DST question too.
- **B2 BID-derived trendbars:** genuine staff quote was cAlgo-scoped; the Open-API-specific claim was ex-staff; structural corroboration only (bar requests expose no quote-type field). Treatment: first-connection reconciliation of trendbar OHLC against BID tick history per broker + symbol class (live trendbars asserted separately — no source covers them); bar identity records the verified quote side or the bars are refused; permanent fallback: build bars from explicitly-BID/ASK ticks (A3).

## Bundle C — undocumented behaviors: verify-or-refuse adapter obligations

- **C1** `ProtoOASpotEvent.timestamp` unit: assert ms by magnitude at startup; refuse on mismatch.
- **C2** Spot coalescing/conflation: unknown — measure via timestamp opt-in on a liquid symbol; never assume every-tick delivery.
- **C3** Rate-limit window semantics: unknown — throttle conservatively at/below published rates; 108/11/429 map to `transient venue failure` typed refusals with backoff.
- **C4** Absent `moneyDigits`: typed refusal, never default to 2.
- **C5** `pipSize = 10^-pipPosition`: validate against known symbols at startup; assert, don't assume.
- **C6** Live-trendbar semantics (live-forming vs last-closed; cadence): primary sources contradict — resolve empirically before live bars enter evidence.
- **C7** Historical vs non-historical classification for the 5/50 split: adapter declares its own conservative classification.
- **C8** Trendbar per-period span caps: unpublished — discovered via error-35 handling, recorded as broker facts.

## Consequences on ratified law (no conflicts found)

- **AD-8** distrust clause resolves: cTrader ms fields trusted as UTC on per-field documentation; B1/B2 stay empirical; receive-time rule confirmed mandatory (A2).
- **AD-7** foreign-money-verbatim: A6 supplies the exact scales — venue adapter stores raw ints/doubles with declared scales verbatim, conversions derived with lineage.
- **AD-9/AD-21:** A6/A7 metadata surfaces enter the GAP-0037/0038 contracts (instrument-metadata snapshots are already typed configuration inputs per AD-22).
