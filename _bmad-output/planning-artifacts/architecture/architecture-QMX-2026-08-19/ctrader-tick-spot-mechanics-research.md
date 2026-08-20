# cTrader Open API — tick history & live spot delivery mechanics (re-research, 2026-08-20)

Single-agent primary-source pass (relaunched after the workflow researcher failed on output format). Grades: primary-doc > primary-proto > staff-forum > community/inference. Research protocol: presented, not adopted.

## 1. ProtoOAGetTickDataRes [primary-proto, OpenApiMessages.proto]

```proto
repeated ProtoOATickData tickData = 3; // The list of ticks is in chronological order (newest first). The first tick contains Unix time in milliseconds while all subsequent ticks have the time difference in milliseconds between the previous and the current one.
required bool hasMore = 4; // If TRUE then the number of records by filter is larger than chunkSize, the response contains the number of records that is equal to chunkSize.
```

`ProtoOATickData`: `timestamp` (ms, delta after first entry — documented), `tick` (`// Tick price.`).

- **Timestamp delta: documented** [primary-proto].
- **PRICE delta: real but never documented in prose.** Proto is silent. Demonstrated by Spotware staff amusleh (profile 46289), 2022-01-21, thread https://community.ctrader.com/forum/connect-api-support/37490/ — worked output shows first `tick` absolute (113052 = 1.13052×100000) then signed deltas; staff wrote "We will update the ProtoOATickData documentation to describe this" — still not done. Grade: staff-forum.
- **Sort order: newest-first.** Proto text "chronological order (newest first)" is internally contradictory; the parenthetical governs; staff corroborates "descending order".
- **hasMore/chunkSize:** `chunkSize` is named in the comment but is a server-side constant, not a field. Docs [primary-doc, https://help.ctrader.com/open-api/symbol-data/]: tick count limit "depends on the configuration of the cTrader backend"; page by re-requesting with `toTimestamp` = oldest received timestamp while `hasMore == true`. No cursor pagination exists.

## 2. ProtoOAGetTickDataReq span cap — CORRECTED

Proto fields carry only range bounds (>= 0 / <= 2147483646000), NO span clause. BUT the docs page states it [primary-doc, symbol-data]:

> "It is impossible to request historical tick data for a period larger than one week. As such, the difference between the specified `toTimestamp` and the `fromTimestamp` must not be larger than `604800000`."

Enforced at runtime as error 35 INCORRECT_BOUNDARIES. So: 1-week tick cap = documented (docs page), proto-silent.

## 3. ProtoOASpotEvent [primary-proto]

```proto
optional uint64 bid = 4;    // 1/100000 of unit of a price
optional uint64 ask = 5;    // 1/100000 of unit of a price
repeated ProtoOATrendbar trendbar = 6; // Returns live trend bar. Requires subscription on the trend bars.
optional uint64 sessionClose = 7;      // 1/100000
optional int64 timestamp = 8;          // The Unix time for spot.
```

- bid/ask are **optional** — an event may carry one side or none [primary-doc confirms: "you may not necessarily see ProtoOASpotEvent messages where both are specified"].
- **timestamp unit: NOT stated anywhere** — "The Unix time for spot." with no unit, in proto AND docs. Not even staff-grade. Milliseconds is inference by platform analogy.
- **subscribeToSpotTimestamp = 4** on ProtoOASubscribeSpotsReq: "If TRUE you will also receive the timestamp in ProtoOASpotEvent." Default = no server time on live spots at all.
- **Coalescing/conflation under load: NOT-FOUND** in any primary source. Any conflation claim is community/inference.
- Subscribe: "You'll receive technical ProtoOASpotEvent with current price shortly after this response" (snapshot event). Unsubscribe: "You may still occasionally receive ProtoOASpotEvents until request processing is complete" (not instantaneous). [primary-proto]

## 4. Live trendbars

- No dedicated event: live bars ride inside `ProtoOASpotEvent.trendbar` [primary-proto]. Requires spot subscription first, then `ProtoOASubscribeLiveTrendbarReq` (per period + symbol), "in that order" [primary-doc].
- **Genuine primary-source contradiction:** proto calls the field "live trend bar" (implies the forming bar); the symbol-data docs page says "use its `trendbar` field to get the data for the last closed bar." Update cadence never stated. The one on-point forum thread (41308, Jul 2023) has no reply. UNRESOLVED — empirical item.
- Bar decode [primary-doc + proto]: `low` absolute (÷100000 per docs), `deltaOpen`/`deltaClose`/`deltaHigh` added to low, `volume` in ticks, `utcTimestampInMinutes` = "timestamp of the open tick".

## Gaps

1. Tick PRICE delta documented nowhere in prose (staff-demonstrated only).
2. Max ticks per response = backend-configured, value undisclosed.
3. Spot coalescing: NOT-FOUND.
4. ProtoOASpotEvent.timestamp unit: not stated (ms = inference).
5. Live-trendbar semantics ambiguous (live vs last-closed; cadence unstated).
6. Trendbar per-period span caps unpublished (runtime error 35 only).
7. Proto's "chronological order (newest first)" wording never corrected.
