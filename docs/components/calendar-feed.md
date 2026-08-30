---
id: COMP-CALENDAR-FEED
title: News-Calendar Feed
type: component-spec
status: ratified
component: COMP-CALENDAR-FEED
depends_on: []
decisions: [DEC-0009, DEC-0038, DEC-0052, DEC-0065, DEC-0074, DEC-0106, DEC-0117, DEC-0119, DEC-0152, DEC-0156, DEC-0157, DEC-0158, DEC-0193, DEC-0198, DEC-0214, DEC-0236, DEC-0259]
sources: [DEC-0009, DEC-0038, DEC-0052, DEC-0065, DEC-0072, DEC-0074, DEC-0106, DEC-0117, DEC-0119, DEC-0152, DEC-0156, DEC-0157, DEC-0158, EXT-2030, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-NODE-2026-08-28/ARCHITECTURE-SPINE.md, _docwork/ledger.yaml, docs/components/trading-node.md, docs/architecture/dependencies.yaml, docs/contracts/ct-15-external-source-adapter.yaml, docs/contracts/ct-31-control-window.yaml]
generated: 2026-08-18
verified: 2026-08-29
stale_after: 30d
---

# News-Calendar Feed

`COMP-CALENDAR-FEED` is the external provider boundary consumed by the standalone news-calendar recorder. The feed supplies external event evidence; qmf-data owns no provider lifecycle, and the QMF risk module's news control is now the ratified control-window contract [CT-31](../contracts/ct-31-control-window.yaml), which maps this feed's event evidence to affected instruments and blocks new entries only — this feed defines no window and holds no permission. [DEC-0052] [DEC-0152]

This is the **news calendar** — one of three distinct named calendar concepts, and never to be conflated with the other two: the **market-hours calendar** (`COMP-QMF-CALENDAR-FOREX`, trading-hours rollover and session schedule) and the **day-boundary calendar** (an account-scoped accounting-boundary rule). `COMP-CALENDAR-FEED` answers only "what economic events happened, when, and how were they revised." [DEC-0106]

## Authority boundary

May, from QMF's perspective: supply provider-identified event records and revisions to `COMP-QMF-DATA-INGEST` through CT-15; the news-calendar recorder keeps the provider's native event identity and revisions through the idempotent `(source, source-native id, revision)` intake, where each revision is a new artifact and corrections are appended, never overwritten. [DEC-0052] [DEC-0119] [DEC-0117]

May never, from QMF's perspective: be described as QMF-owned; define risk policy or a news blackout by itself (the blackout is CT-31's, derived from this feed's evidence); schedule the recorder inside qmf-data; be assumed complete, timely, stable, or legally retainable; erase prior event revisions; act as a market-hours calendar or a day-boundary calendar; or be equated with SQS. [DEC-0009] [DEC-0052] [DEC-0152] [DEC-0074] [DEC-0106]

## Interfaces

| Interface | Direction | Contract | Peer |
|---|---|---|---|
| Economic-calendar request / response | request in, response out | [CT-15](../contracts/ct-15-external-source-adapter.yaml) | COMP-QMF-DATA-INGEST |

## Behavior

The news-calendar feed is an active external CT-15 provider. `COMP-QMF-DATA-INGEST` is the QMF owner and caller: it sends a bounded request to the provider and receives the response. `COMP-QMF-DATA` does not call or consume CT-15. The recorder that invokes the ingest path is a standalone application consuming QMF data contracts. Scheduling, supervision, retries, and operator UI stay outside the reusable qmf-data library. [DEC-0009] [DEC-0052] [DEC-0119]

Provider event identity and corrections remain source evidence written under the news-calendar recorder's own `WriterId` (AD-21 recorder identity): every external fact carries event-time, known-at, source, and revision, and corrections are appended, never overwriting prior evidence. The risk-side control that maps this evidence to affected instruments is the [CT-31](../contracts/ct-31-control-window.yaml) control-window mechanism — instrument scope resolves through dated per-instrument currency-exposure records, never by parsing a symbol; a window blocks new entries only on the instruments in scope, live and paper alike; and feed revisions that drive a window resolve widen-never-shrink at read time (a later revision may widen a not-yet-passed bound, never narrow a window that has had effect). News control is separate from SQS. [DEC-0117] [DEC-0158] [DEC-0152] [DEC-0074]

The news-calendar recorder discipline is ratified (DEC-0119): provider-native identity and revisions through the idempotent `(source, source-native id, revision)` intake, with scheduling owned by the standalone application. The provider selection and the legal archiving/retention posture remain the open operator items DEC-0119 records, carried forward and not resolved here. [DEC-0119]

The risk-side mechanism GAP-0042 once reserved is now ratified as [CT-31](../contracts/ct-31-control-window.yaml), and lives outside this feed: event severity is stored as the **provider's impact labels verbatim** (QMX mints no severity scale of its own in V1, and severity-to-window is a declared node mapping); currency-to-instrument mapping runs through **dated per-instrument currency-exposure records**, never by parsing a symbol; blackout windows are **entries-only control windows**, live and paper alike; open-position behavior is a Book's `window_forced_flat` declaration entering same-tick arbitration at rank 2, declaring none being the V1 posture; and window widths and buffers are configurable UI-editable variables with no spine value. This feed defines none of it. [DEC-0152] [DEC-0156] [DEC-0157]

<!-- no-diagram: this is one external CT-15 source boundary; the standalone recorder is a separate application outside the QMF component roster -->

## Trading-node increment (2026-08-29)

The trading node (`COMP-QMN`) is the runtime consumer of this news-calendar feed, and the 2026-08-28 trading-node sitting ruled its V1 source and refresh discipline; the feed's own authority boundary is unchanged — it defines no window and holds no permission — and the increment was ratified by operator delegation plus four direct rulings (DEC-0259). See [COMP-QMN](trading-node.md) for the node's own spec.

### Forex Factory's free weekly file is the sole V1 source (R4)

The operator ruled 2026-08-28 that the node never pays for news: **Forex Factory's free weekly file is the SOLE V1 news-calendar source, and no paid fallback slot exists anywhere, ever** (operator ruling R4) — the free file is chosen because it carries the impact label the news blackout needs (DEC-0214, DEC-0198). The later fallback path is named rather than left open: **a second free source, or an agent-scraped JSON delivered in the same CT-15 intake shape** — the intake shape is the seam, so a second source is an adapter and a config row, never a code path through the news blackout (DEC-0214, DEC-0198). The legal archiving posture stays an **open operator item recorded as personal use**, exactly as the historical source was (DEC-0214, DEC-0198).

### The recorder is a systemd timer with a configurable refresh cadence

At the node the recorder is re-homed from a Windows Scheduled Task to the systemd timer `qmn-news-calendar.timer` — named `qmn-news-calendar` for its kind, since the word alone would name three distinct calendar kinds — calling the ratified CT-15 ingest adapter with provider-native `(source, id, revision)` identity and revisions (DEC-0198). Because all three sessions are traded and timeliness matters, `registry:news_calendar_refresh_cadence` is a configurable node variable with a duration unit-kind (recorded evidence: every 2 h and before each session open), and the scheduler respects the free feed's roughly 2-downloads-per-5-minutes limit — a configured cadence that would breach it is refused at config compile, not silently throttled (DEC-0198, DEC-0214). The recorder's retry policy is declared, not left to the implementer: at most `registry:news_recorder_max_attempts` per timer firing with `registry:news_recorder_backoff`, counted against the same provider budget, and a provider rate-limit or block response is journaled `data quality`, alarmed on the silent-degradation class, and never retried inside the same firing — a retry loop on the sole V1 source could get the host blocked (DEC-0198).

### Fail-closed on staleness, and the widen-or-add-only revision rule

A failed refresh blocks entries fail-closed with no live skip button, and staleness fails closed by a **per-decision-cycle precondition, `registry:news_calendar_max_staleness`** — a value the timer does not send as a signal, so a silently dead timer fails entries closed by itself (DEC-0198, DEC-0193). A news-calendar CODE identity is sealed into `composition_fp` while the ingested snapshot DATA is a frontier-read observation, so a twice-hourly data refresh never requires a restart while a code change does (DEC-0198). A news-calendar revision **may only widen or add** an in-force or same-day window automatically; narrowing, downgrading, delaying or removing one takes effect no earlier than the superseded window's end and is otherwise an operator act on the powers channel citing both revisions (DEC-0193, DEC-0198, DEC-0236). The blackout the feed's evidence drives remains CT-31's — entries-only, live and paper alike — and this feed still defines none of it (DEC-0152).

## Configuration

| Variable | Registry key | Notes |
|---|---|---|
| Provider and event identity | — | Recorder discipline ratified: provider-native identity and revisions via idempotent `(source, source-native id, revision)` intake; provider selection and legal archiving posture remain open operator items. [DEC-0119] |
| News blackout before event | `registry:news_blackout_before` | A CT-31 window width — a configurable UI-editable variable with no spine value (recorded evidence: the plus-or-minus-15-minute news buffer is on record as withdrawn). It configures the CT-31 window, never the external feed. [DEC-0157] [DEC-0152] |
| News blackout after event | `registry:news_blackout_after` | A CT-31 window width — a configurable UI-editable variable with no spine value. It configures the CT-31 window, never the external feed. [DEC-0157] [DEC-0152] |

## Failure modes

| # | Condition | Behavior | Cites |
|---|---|---|---|
| FM-1 | The provider is unavailable, late, or rate-limits the recorder. | QMF cannot require the external provider to recover; retry, backoff, and observable refusal live in the standalone recorder, which owns scheduling and supervision. | DEC-0052, DEC-0119 |
| FM-2 | An event lacks stable provider identity or arrives as a correction/retraction. | The ingest seam must not overwrite prior evidence: the idempotent `(source, source-native id, revision)` intake keys each revision as a new artifact and corrections are appended. | DEC-0038, DEC-0117, DEC-0119 |
| FM-3 | Licence or long-term retention rights are unconfirmed. | The recorder must not be operationalized on an invented legal assumption; the legal archiving/retention posture is an open operator item DEC-0119 records, not resolved here. | DEC-0052, DEC-0119 |
| FM-4 | A consumer treats missing feed data as permission to trade. | The feed supplies no permission. Fail-closed unavailable/stale-data behavior is CT-31's, not the feed's: a failed calendar refresh, unknown coverage, or a missing per-instrument currency-exposure record blocks new entries (treated-as-affected), the absence journaled as data quality and alarmed. | DEC-0065, DEC-0152 |
| FM-5 | A consumer treats the feed as SQS input or as a universal trading stop. | The mapping is rejected: news control is separate from SQS, is entries-only (never a universal stop), and is scoped to affected instruments through CT-31 currency-exposure records, never to symbol-parsed pairs. | DEC-0152, DEC-0074 |

## Related

Decisions: DEC-0009, DEC-0038, DEC-0052, DEC-0065, DEC-0074, DEC-0106, DEC-0117, DEC-0119, DEC-0152, DEC-0158. (DEC-0072's pair-scoped news framing is superseded by DEC-0152 — the instrument scoping survives, re-mechanised through currency-exposure records; it remains in `sources:` as provenance.) Scenarios: [SCN-0002 source correction](../scenarios/SCN-0002-source-correction.md), [SCN-0008 news scope](../scenarios/SCN-0008-pair-scoped-news.md). Knowledge: none drafted.
