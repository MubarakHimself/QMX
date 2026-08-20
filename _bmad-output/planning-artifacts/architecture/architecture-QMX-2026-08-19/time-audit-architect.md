# Time-model audit — senior-architect lens (2026-08-19)

Agent verdict: the proposed model matches the corpus's own GAP-0008 recommendation near-verbatim (gap-report.md:60; registry variables.yaml timestamp_precision). No conflict with any Law or live DEC. All findings are incompleteness, not contradiction. Five items would force a qmf-core change later if left unstated.

## A. Fit per consumer (13 examined)

Fit: source-observation admission (CT-10, + needs 4 clocks & sequence tie-break), indicators (CT-16, + calendar version in fingerprint), structure observed/confirmed (CT-17), causality gate (CT-08, + named decision-time), venue timestamps (CT-20, matches DEC-0053 no-silent-merge), journal (CT-13, + per-writer sequence), multi-session labels, correlation (+ alignment on instants + named calendar).
Misfit as stated: bar building (no calendar component exists in roster; bar identity lacks calendar version), news control (no Duration/Interval types — blackout windows untypeable), SQS seam (needs Duration + monotonic + receipt-instant + session query), kill-switch seam (instant alone gives no total order), dataset splits (boundary type undecided: civil vs trading date vs instant).

## B. Edge-case register (headline items)

1. BLOCKER — "extension" has no home: roster is frozen at 5+2; fix = CT-02 defines a calendar-provider PROTOCOL in core; forex calendar is a separate versioned package outside the roster.
2. BLOCKER — no Duration / half-open Interval types in core; Risk and node would each invent incompatible ones.
3. BLOCKER — no monotonic/elapsed clock concept; define as protocol only (measurable, never persisted).
4. BLOCKER — no total-order tie-break at equal instants; ms-resolution sources make ties routine; ordering key = (instant, per-writer sequence).
5. BLOCKER — calendar/tzdb version must participate in CT-05 fingerprints; tzdb bumps silently relabel historical trading dates otherwise.
6. Bar straddling DST-shifted 5pm-NY rollover: forex trading day is 23h once a year, 25h once.
7. US/EU/AU DST dates differ — ~3 weeks/year of shifted overlaps; each session window carries its own IANA zone.
8. Holidays absent from stated forex-calendar scope; holidays are DATA (drags calendar toward an evidence source).
9. Swap-Wednesday needs settlement dates (T+2 across both currencies' holiday calendars) — not derivable from session rollover; add SettlementDate or drop from V1.
10. Weekend boundaries are broker-specific — calendar must be venue-parameterized.
11. Crypto 24/7 still needs a rollover convention (every calendar must supply one).
12. Naming collision: COMP-CALENDAR-FEED = economic-calendar feed, not session calendar — rename before minting the extension.
13. Declare POSIX/no-leap-second semantics for "UTC nanoseconds".
14. Broker server-local timestamps with unknown DST policy: original representation + declared zone = required CT-10 field; unverified zone policy → typed refusal (lands in GAP-0037).
15. CT-10 needs FOUR times: source time as received, event instant (UTC ns), receipt instant (local clock), knowledge instant.
16. ns storage over ms sources: contract must not let consumers infer sub-ms ordering (sequence field carries it).
17. int64 ns range 1677–2262 — state once.
18. zoneinfo is stdlib but Windows has no system tzdb → calendar extension pins the tzdata PyPI package (extension is NOT zero-dep; core stays zero-dep).
19. Trading date must NEVER be a causality proxy — causality compares instants only.
20. Causality gate needs a named decision/cutoff instant field (CT-08).
21. Split boundaries: define on trading dates or instants, never civil dates (Sunday 17:00 NY session spans two civil dates).
22. Journal cross-writer ordering = (instant, per-writer sequence); time model does not supply cross-writer order by itself.

## C. Amendments required (the ratified list)

1. CT-02 defines a calendar-provider protocol; forex calendar = separate versioned package outside the roster.
2. Core gains Duration (signed int64 ns) and Interval (half-open [start,end) with contains/overlaps).
3. Monotonic/elapsed as protocol only — never persisted.
4. Ordering rule: CT-10 carries explicit sequence; instants alone never totally order.
5. Calendar identity incl. tzdb version enters CT-05 fingerprints.
6. POSIX/no-leap-second semantics declared.
7. Swap-Wednesday dropped from V1 calendar (settlement machinery deferred).
8. Holidays in forex-calendar scope (or explicitly gapped).
9. Calendars venue-parameterized; every calendar supplies a rollover rule (incl. 24/7).

## D. Node territory (seams QMF exposes instead)

- Kill switch state machine/priority → QMF gives Instant/Duration/Interval, typed refusals, journal shapes, venue command/event contracts.
- MIS → governed CT-10 reads, CT-12 releases, CT-16 light-indicator protocol.
- SQS runtime loop → evidence with event+receipt instants, session query, Duration; formula stays fenced in QMF registry.
- News-window evaluation loop → calendar-event evidence chain + Interval + blackout registry keys; runtime decision is node.
- Schedulers → one pure query: next_session_boundary(instant, calendar) → Instant; QMF holds no timer.
- Local-time display → node/UI only.
- Overnight/hold policy → per-Book in Risk; QMF gives session_bounds(trading_date, calendar).
- Wall-clock now() → Clock PROTOCOL in CT-02; node injects real clock, replay injects fixed one.

Files to touch at documentation time: ct-02-time-calendar.yaml, registry/variables.yaml (timestamp_precision), architecture/dependencies.yaml (extension rule), glossary (instant, civil date, trading date, session window — all new terms).
