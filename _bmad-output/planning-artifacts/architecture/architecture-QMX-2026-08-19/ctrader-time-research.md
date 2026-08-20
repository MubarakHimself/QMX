# cTrader Open API — time handling research (2026-08-19)

Web research against primary sources (Spotware proto files, help.ctrader.com) + staff-authoritative forum replies. Feeds GAP-0037 / ticket 006 / the venue sitting. Research protocol: findings presented, NOT auto-adopted.

## Findings

1. **Timestamps**: platform-wide standard is **Unix milliseconds, UTC** (deals, orders, positions, tick data, request ranges) [PRIMARY: spotware/openapi-proto-messages]. Exception: `ProtoOATrendbar.utcTimestampInMinutes` = Unix **minutes** UTC [PRIMARY]. `ProtoOASpotEvent.timestamp` unit unstated in proto; empirically ms [SECONDARY]; only present if `subscribeToSpotTimestamp=true`.
2. **Timezone policy**: platform is UTC-based (not broker-set like MT4) [staff]. **Daily bar boundary pinned to 17:00 America/New_York (EST/EDT)** — same for all brokers [official 2013 announcement + 2019 staff reaffirmation]. So the UTC hour of the day boundary shifts 1h twice a year on US DST dates. Symbols carry their own `scheduleTimeZone` for trading intervals [PRIMARY]. UNVERIFIED: rule not stated in Open-API-specific primary docs, only platform-general threads.
3. **Trendbars are BID-derived** — consistent Spotware staff confirmations across years ("bid prices are used for drawing the chart. You cannot switch"; live trendbar close = latest bid) [SECONDARY staff-authoritative; a documentation gap on Spotware's side — no primary doc page states it]. RESOLVES the tracker's open "bid vs mid" question at best-available level. Historical tick data lets caller request BID or ASK explicitly per call (`ProtoOAQuoteType`) [PRIMARY].
4. **No server-clock primitive**: heartbeat carries no timestamp; no get-server-time message exists; staff non-answer confirms. Client-side receive-time recording is the ONLY desync detector — validates the three-times-per-foreign-event rule.
5. **DST gotchas**: historical UTC timestamps never shift (good); but the 17:00-NY day boundary means daily bars are 23h/25h once a year each. FIX-API (not Open API) report of server SendingTime jumping ~5min after reconnect — infra clock anomalies observed in the wild [SECONDARY, unverified for Open API].
6. **Rate limits** [PRIMARY]: 50 req/s per connection non-historical; 5 req/s historical; historical tick requests capped at 1-week span each. Sliding vs fixed window UNVERIFIED.
7. **Granularity**: millisecond everywhere; no sub-ms exists in the protocol. Live spots per price update (server-side coalescing policy UNVERIFIED); historical ticks delta-compressed, newest-first, chunked (`hasMore`, chunk size UNVERIFIED).

## Implications for ratified rulings (all consistent)

- ns storage over ms sources = headroom, ties routine → (instant, per-writer sequence) ordering rule validated.
- 17:00-NY rollover matches the ratified forex market-hours calendar exactly.
- Receive-time-alongside-source-time rule is mandatory, not optional (no server clock to query).
- BID-basis of bars must be recorded as source metadata (bar identity: venue + BID-derived) when qmf-data bar contracts are specified.
- Venue adapter must respect 5 req/s historical + 1-week-span chunking in ingest design (qmf-data-ingest / dukascopy-class backfill planning).

## Unverified list (for the venue sitting)

(a) spot-event timestamp unit per proto text; (b) 17:00-NY rule in Open-API primary docs; (c) server-side spot coalescing; (d) tick chunk size; (e) rate-limit window semantics; (f) absence of clock-sync primitive (confirmed-absent by staff non-answer).
