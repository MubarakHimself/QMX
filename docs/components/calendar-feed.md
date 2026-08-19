---
id: COMP-CALENDAR-FEED
title: Economic-Calendar Feed
type: component-spec
status: provisional
component: COMP-CALENDAR-FEED
depends_on: []
decisions: [DEC-0009, DEC-0038, DEC-0052, DEC-0065, DEC-0072, DEC-0074]
sources: [DEC-0009, DEC-0038, DEC-0052, DEC-0065, DEC-0072, DEC-0074, docs/architecture/dependencies.yaml, docs/contracts/ct-15-external-source-adapter.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# Economic-Calendar Feed

`COMP-CALENDAR-FEED` is the external provider boundary consumed by the standalone economic-calendar recorder. The feed supplies external event evidence; qmf-data owns no provider lifecycle, and the QMF risk module owns any later pair-scoped control only after its contracts are ratified. [DEC-0052] [DEC-0072]

## Authority boundary

May, from QMF's perspective: supply provider-identified event records and revisions to `COMP-QMF-DATA-INGEST` through CT-15 after provider, legal, identity, correction, and rate-limit rules are ratified. [DEC-0052]

May never, from QMF's perspective: be described as QMF-owned; define risk policy or a news blackout by itself; schedule the recorder inside qmf-data; be assumed complete, timely, stable, or legally retainable; erase prior event revisions; or be equated with SQS. [DEC-0009] [DEC-0052] [DEC-0072] [DEC-0074]

## Interfaces

| Interface | Direction | Contract | Peer |
|---|---|---|---|
| Economic-calendar request / response | request in, response out | [CT-15](../contracts/ct-15-external-source-adapter.yaml) | COMP-QMF-DATA-INGEST |

## Behavior

Calendar Feed is an active external CT-15 provider. `COMP-QMF-DATA-INGEST` is the QMF owner and caller: it sends a bounded request to the provider and receives the response. `COMP-QMF-DATA` does not call or consume CT-15. The recorder that invokes the ingest path is a standalone application consuming QMF data contracts. Scheduling, supervision, retries, and operator UI stay outside the reusable qmf-data library. [DEC-0009] [DEC-0052]

Provider event identity and corrections remain source evidence. Any later risk control maps that evidence to affected instruments through CT-25 rules that remain unresolved. News control is pair-scoped and separate from SQS. [DEC-0072] [DEC-0074]

`GAP(GAP-0029): Select the provider and ratify event identity, revision/correction behavior, deduplication, schedule, rate limits, licence, retention, retries, and legal posture.`

`GAP(GAP-0042): Define risk-side event severity, currency-to-instrument mapping, blackout windows, open-position behavior, and overrides separately from this feed.`

<!-- no-diagram: this is one external CT-15 source boundary; the standalone recorder is a separate application outside the QMF component roster -->

## Configuration

| Variable | Registry key | Notes |
|---|---|---|
| Provider and event identity | — | `GAP(GAP-0029): No provider, identifier, or correction contract is ratified.` |
| News blackout before event | `registry:news_blackout_before` | Risk-side value is null and does not configure the external feed. |
| News blackout after event | `registry:news_blackout_after` | Risk-side value is null and does not configure the external feed. |

## Failure modes

| # | Condition | Behavior | Cites |
|---|---|---|---|
| FM-1 | The provider is unavailable, late, or rate-limits the recorder. | QMF cannot require the external provider to recover. `GAP(GAP-0029): Define retry, backoff, and observable refusal behavior in the standalone recorder.` | DEC-0052 |
| FM-2 | An event lacks stable provider identity or arrives as a correction/retraction. | The ingest seam must not overwrite prior evidence. `GAP(GAP-0029): Define revision and deduplication semantics.` | DEC-0038, DEC-0052 |
| FM-3 | Licence or long-term retention rights are unconfirmed. | The recorder must not be operationalized on an invented legal assumption. `GAP(GAP-0029): Record the approved posture.` | DEC-0052 |
| FM-4 | A consumer treats missing feed data as permission to trade. | The feed supplies no permission. `GAP(GAP-0042): Define the risk module's unavailable/stale-data behavior.` | DEC-0065, DEC-0072 |
| FM-5 | A consumer treats the feed as SQS input or as a universal trading stop. | The mapping is rejected: news control is separate from SQS and scoped to affected pairs. | DEC-0072, DEC-0074 |

## Related

Decisions: DEC-0009, DEC-0038, DEC-0052, DEC-0065, DEC-0072, DEC-0074. Scenarios: [SCN-0002 source correction](../scenarios/SCN-0002-source-correction.md), [SCN-0008 pair-scoped news](../scenarios/SCN-0008-pair-scoped-news.md). Knowledge: none drafted.
