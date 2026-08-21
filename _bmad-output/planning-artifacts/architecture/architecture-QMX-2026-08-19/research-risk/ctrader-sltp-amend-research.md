# cTrader Open API — Native SL/TP Amend Research (Position & Pending Order)

Research date: 2026-08-20
Question: How does the cTrader Open API amend Stop-Loss/Take-Profit on an OPEN POSITION and on a PENDING ORDER natively, without cancel-and-replace?

Primary sources used:
- https://help.ctrader.com/open-api/messages/ (Messages reference)
- https://help.ctrader.com/open-api/model-messages/ (Model messages reference)
- https://help.ctrader.com/open-api/ (Getting started — rate limits)
- https://help.ctrader.com/open-api/error-handling/ (Error handling)
- https://github.com/spotware/openapi-proto-messages — `OpenApiMessages.proto`, `OpenApiModelMessages.proto` (raw, via raw.githubusercontent.com)

Secondary sources (community forum, orientation only, never used alone for a verdict):
- https://community.ctrader.com/forum/connect-api-support/36902/
- https://community.ctrader.com/forum/fix-api/37634/
- https://community.ctrader.com/forum/ctrader-support/42913/

---

## 1. Amending SL/TP on an OPEN POSITION — `ProtoOAAmendPositionSLTPReq`

**STATUS: CONFIRMED-PRIMARY**

Source: `OpenApiMessages.proto` (raw, main branch) — https://github.com/spotware/openapi-proto-messages/blob/main/OpenApiMessages.proto ; cross-checked against https://help.ctrader.com/open-api/messages/

```protobuf
message ProtoOAAmendPositionSLTPReq {
    optional ProtoOAPayloadType payloadType = 1 [default = PROTO_OA_AMEND_POSITION_SLTP_REQ];
    required int64 ctidTraderAccountId = 2;   // Unique identifier of the trader's account.
    required int64 positionId = 3;            // The unique ID of the position to amend.
    optional double stopLoss = 4;             // Absolute Stop Loss price (1.23456 for example).
    optional double takeProfit = 5;           // Absolute Take Profit price (1.26543 for example).
    optional bool guaranteedStopLoss = 7;     // If TRUE then the Stop Loss is guaranteed. Available for the French Risk or the Guaranteed Stop Loss Accounts.
    optional bool trailingStopLoss = 8;       // If TRUE then the Trailing Stop Loss is applied.
    optional ProtoOAOrderTriggerMethod stopLossTriggerMethod = 9 [default = TRADE]; // The Stop trigger method for the Stop Loss/Take Profit order.
}
```

Field notes (all CONFIRMED-PRIMARY, same sources):
- `stopLoss` / `takeProfit`: **absolute price**, `double`, un-scaled decimal (e.g. `1.23456`) — not an integer/pip-scaled field. No documented "clear the field" sentinel value was found; the field is simply `optional`, so omitting it in a request presumably leaves that side untouched (not explicitly documented — see §3).
- `guaranteedStopLoss`: `bool`, gates Guaranteed Stop Loss / French Risk accounts.
- `trailingStopLoss`: `bool` — the flag that turns the position's stop loss into a server-tracked trailing stop (see §4).
- `stopLossTriggerMethod`: enum `ProtoOAOrderTriggerMethod` — `TRADE` (default), `OPPOSITE`, `DOUBLE_TRADE`, `DOUBLE_OPPOSITE` (definitions confirmed from the same proto file: buy triggered by ask vs bid, single vs double-tick confirmation).
- There is **no `relativeStopLoss`/`relativeTakeProfit` field on this message** — those relative fields exist only on `ProtoOANewOrderReq` and `ProtoOAAmendOrderReq` (§5). Amending an existing position's SL/TP is absolute-price only.
- Field 6 is skipped in the numbering (goes 5 → 7); no field 6 is defined or documented anywhere found — noted but not material.

**No dedicated `ProtoOAAmendPositionSLTPRes` message exists.** CONFIRMED-PRIMARY (absence) — verified by full-text inspection of `OpenApiMessages.proto`, which contains no such message, and by https://help.ctrader.com/open-api/messages/, which documents no response type for this request.

**Response/error surface** (CONFIRMED-PRIMARY, https://help.ctrader.com/open-api/error-handling/ + proto):
- Success is confirmed asynchronously via **`ProtoOAExecutionEvent`** (the generic execution-event stream also used for new orders, cancels, closes), carrying the updated `position`/`order` snapshot.
- Failure is reported via **`ProtoOAOrderErrorEvent`**, defined as:
```protobuf
message ProtoOAOrderErrorEvent {
    optional ProtoOAPayloadType payloadType = 1 [default = PROTO_OA_ORDER_ERROR_REQ];
    required int64 ctidTraderAccountId = 5;
    required string errorCode = 2;   // ProtoErrorCode name or custom code (e.g. ProtoCHErrorCode)
    optional int64 orderId = 3;
    optional int64 positionId = 6;
    optional string description = 7;
}
```
  (source: `OpenApiMessages.proto`, raw). The error-handling page (https://help.ctrader.com/open-api/error-handling/) states `ProtoOAOrderErrorEvent` is sent for problems on order/deal/position operations (e.g. modifying while market closed, modifying an order mid-execution), distinct from the generic `ProtoErrorRes` used for request/domain-layer errors.
- A full enumerated `ProtoErrorCode` list with SL/TP-specific codes (e.g. an "invalid stop" code) was **not** located on the fetched pages within this pass — UNDOCUMENTED at the depth reached; the mechanism (which event fires, and that `errorCode` is a `ProtoErrorCode` name) is CONFIRMED-PRIMARY, the exhaustive code list is not confirmed here.

---

## 2. Amending a PENDING ORDER — `ProtoOAAmendOrderReq`

**STATUS: CONFIRMED-PRIMARY**

Source: `OpenApiMessages.proto` (raw) — same repo, cross-checked against https://help.ctrader.com/open-api/messages/

```protobuf
message ProtoOAAmendOrderReq {
    optional ProtoOAPayloadType payloadType = 1 [default = PROTO_OA_AMEND_ORDER_REQ];
    required int64 ctidTraderAccountId = 2;
    required int64 orderId = 3;                       // The unique ID of the order.
    optional int64 volume = 4;                        // 0.01 of a unit (1000 = 10.00 units)
    optional double limitPrice = 5;                   // LIMIT orders only
    optional double stopPrice = 6;                    // STOP / STOP_LIMIT orders only
    optional int64 expirationTimestamp = 7;            // Unix ms, for Good-Till-Date orders
    optional double stopLoss = 8;                      // Absolute SL price. Not supported for MARKET orders.
    optional double takeProfit = 9;                    // Absolute TP price. Not supported for MARKET orders.
    optional int32 slippageInPoints = 10;               // MARKET_RANGE / STOP_LIMIT
    optional int64 relativeStopLoss = 11;               // 1/100000 of a unit of price
    optional int64 relativeTakeProfit = 12;             // 1/100000 of a unit of price
    optional bool guaranteedStopLoss = 13;              // French Risk / Guaranteed SL accounts
    optional bool trailingStopLoss = 14;                // If TRUE, trailing SL applied
    optional ProtoOAOrderTriggerMethod stopTriggerMethod = 15 [default = TRADE]; // STOP/STOP_LIMIT trigger
}
```

**Yes — SL/TP can be set and changed on a pending order via this single message.** CONFIRMED-PRIMARY. It carries both the absolute (`stopLoss`, `takeProfit`) and relative (`relativeStopLoss`, `relativeTakeProfit`) forms, plus `guaranteedStopLoss`, `trailingStopLoss`, and `stopTriggerMethod` — the same protection knobs as position-side amend, plus order-specific fields (`volume`, `limitPrice`, `stopPrice`, `expirationTimestamp`, `slippageInPoints`) so price/size/expiry/SL/TP can all be amended in one call without cancel-and-replace.

Relative-field mechanics (CONFIRMED-PRIMARY, exact wording from `OpenApiMessages.proto`):
> "Specified in 1/100000 of a unit of price. (e.g. 123000 in protocol means 1.23, 53423782 means 534.23782) For BUY stopLoss = entryPrice − relativeStopLoss, for SELL stopLoss = entryPrice + relativeStopLoss." (and the mirror-image formula for `relativeTakeProfit`.)

**No `ProtoOAAmendOrderRes` message exists** — CONFIRMED-PRIMARY (absence), same method as §1: full-text check of the proto file plus the messages page shows no dedicated response; confirmation/failure surface is the same `ProtoOAExecutionEvent` / `ProtoOAOrderErrorEvent` pair described in §1.

---

## 3. Is the amend atomic server-side (position never left unprotected)?

**STATUS: UNDOCUMENTED**

No page fetched — https://help.ctrader.com/open-api/messages/, https://help.ctrader.com/open-api/model-messages/, https://help.ctrader.com/open-api/, https://help.ctrader.com/open-api/error-handling/, nor the raw `.proto` comment blocks for `ProtoOAAmendPositionSLTPReq`, `ProtoOAAmendOrderReq`, or `ProtoOAExecutionEvent` — contains any statement about atomicity, transactional/ordering guarantees, or partial-failure behavior (e.g., SL updates but TP fails, or the position is briefly unprotected mid-amend). The request messages carry both `stopLoss` and `takeProfit` as a single message with a single `errorCode` surface (`ProtoOAOrderErrorEvent` keyed by `positionId`/`orderId`, not by field), which is circumstantial (the wire protocol looks like one atomic call), but nothing in the primary docs asserts atomicity explicitly. **Ruling should treat this as UNDOCUMENTED and not assume atomicity without further confirmation (e.g., direct query to Spotware support or empirical broker-side testing).**

---

## 4. Native TRAILING stop support

**STATUS: CONFIRMED-PRIMARY — native flag exists, and trailing is server-managed, not client-driven amend-looping.**

Evidence:
- `trailingStopLoss` (`bool`) is a field on `ProtoOAAmendPositionSLTPReq` (field 8), `ProtoOAAmendOrderReq` (field 14), and `ProtoOANewOrderReq` (field 22) — source: `OpenApiMessages.proto` raw, confirmed above.
- `trailingStopLoss` (`bool`) also exists on the model messages `ProtoOAPosition` (field 16) and `ProtoOAOrder` (field 23) — source: `OpenApiModelMessages.proto` raw (https://github.com/spotware/openapi-proto-messages/blob/main/OpenApiModelMessages.proto), so the flag is queryable/readable back off the position/order snapshot, not just settable.
- A dedicated **server-push event** exists for trailing updates:
```protobuf
// payloadType default = PROTO_OA_TRAILING_SL_CHANGED_EVENT (2107)
message ProtoOATrailingSLChangedEvent {
    optional ProtoOAPayloadType payloadType = 1;
    required int64 ctidTraderAccountId = 2;
    required int64 positionId = 3;
    required int64 orderId = 4;
    required double stopPrice = 5;          // New value of the Stop Loss price.
    required int64 utcLastUpdateTimestamp = 6;
}
```
  Documented description (https://help.ctrader.com/open-api/messages/, CONFIRMED-PRIMARY): "Event that is sent when the level of the Trailing Stop Loss is changed due to the price level changes." This is direct primary-source evidence that trailing-stop recalculation is performed **server-side** — the server itself moves the stop as price moves favorably and pushes a change notification; the client does not need to poll or keep re-sending `ProtoOAAmendPositionSLTPReq`/`ProtoOAAmendOrderReq` calls to trail the price.
- Corroborating secondary source (community, Spotware staff reply, orientation-only): https://community.ctrader.com/forum/fix-api/37634/ — Spotware staff (amusleh) states "trailing stop loss is a cTrader specific feature not part of FIX standards," confirming trailing SL is a cTrader-side (Open API) capability, not something FIX-API or the client must emulate.

**Gap — UNDOCUMENTED**: the exact algorithm/step-size for how the trailing distance is computed or held (e.g., whether the initial distance between entry/current-SL at the moment `trailingStopLoss=true` is set becomes the fixed trailing distance, what tick/step triggers a re-price, or whether it's re-derived from `relativeStopLoss`) is not stated on any fetched primary page or in the proto comments. Secondary/community evidence (non-authoritative, mark SECONDARY-ONLY): https://community.ctrader.com/forum/ctrader-support/42913/ — a community member (not Spotware staff) states there is no API to query the "original" trailing distance after the fact, i.e., a caller must track the distance itself client-side if it needs to know/report it; this is consistent with (but does not prove) a "fixed distance, server re-prices on favorable ticks" model. **Treat the trailing algorithm's mechanics as UNDOCUMENTED for any ruling that depends on the precise step behavior.**

---

## 5. SL/TP at placement time on a market order — `ProtoOANewOrderReq`

**STATUS: CONFIRMED-PRIMARY**

Source: `OpenApiMessages.proto` raw (same repo), cross-checked against https://help.ctrader.com/open-api/messages/

```protobuf
message ProtoOANewOrderReq {
    optional ProtoOAPayloadType payloadType = 1 [default = PROTO_OA_NEW_ORDER_REQ];
    required int64 ctidTraderAccountId = 2;
    required int64 symbolId = 3;
    required ProtoOAOrderType orderType = 4;   // MARKET, LIMIT, STOP, MARKET_RANGE, STOP_LIMIT
    required ProtoOATradeSide tradeSide = 5;   // BUY, SELL
    required int64 volume = 6;                 // 0.01 of a unit
    optional double limitPrice = 7;
    optional double stopPrice = 8;
    optional ProtoOATimeInForce timeInForce = 9 [default = GOOD_TILL_CANCEL];
    optional int64 expirationTimestamp = 10;
    optional double stopLoss = 11;             // Absolute SL price (e.g. 1.23456). NOT supported for MARKET orders.
    optional double takeProfit = 12;           // Absolute TP price (e.g. 1.23456). NOT supported for MARKET orders.
    optional string comment = 13;              // MaxLength = 512
    optional double baseSlippagePrice = 14;
    optional int32 slippageInPoints = 15;
    optional string label = 16;                // MaxLength = 100
    optional int64 positionId = 17;            // reference to an existing position, if modifying it
    optional string clientOrderId = 18;        // MaxLength = 50
    optional int64 relativeStopLoss = 19;      // 1/100000 of a unit of price
    optional int64 relativeTakeProfit = 20;    // 1/100000 of a unit of price
    optional bool guaranteedStopLoss = 21;     // required TRUE for Limited Risk accounts w/ GSL-enabled symbol
    optional bool trailingStopLoss = 22;       // If TRUE, Stop Loss is Trailing
    optional ProtoOAOrderTriggerMethod stopTriggerMethod = 23 [default = TRADE];
}
```

Key mechanics (CONFIRMED-PRIMARY, exact proto comment text):
- **Both absolute (`stopLoss`/`takeProfit`, `double`, e.g. `1.23456`) and relative (`relativeStopLoss`/`relativeTakeProfit`, `int64`, scaled 1/100000-of-price-unit) forms exist on the same request.** They are alternatives ("Relative Stop Loss that can be specified **instead of** the absolute one").
- **Explicit documented restriction: `stopLoss`/`takeProfit` (the absolute fields) are "Not supported for MARKET orders."** This is a direct, load-bearing primary-source finding — for a `MARKET` order type, the documented path to attach protection at placement is the **relative** fields (`relativeStopLoss`/`relativeTakeProfit`), not the absolute ones. (The relative-field comments do not carry the same "not supported for MARKET" caveat, and their formula — `stopLoss = entryPrice ∓ relativeStopLoss` — is specifically phrased in terms of `entryPrice`, i.e., designed for orders, including market orders, whose fill price isn't known until execution.)
- Relative formula (exact, both `ProtoOANewOrderReq` and `ProtoOAAmendOrderReq`): "For BUY stopLoss = entryPrice − relativeStopLoss, for SELL stopLoss = entryPrice + relativeStopLoss" and "For BUY takeProfit = entryPrice + relativeTakeProfit, for SELL takeProfit = entryPrice − relativeTakeProfit."
- `guaranteedStopLoss` and `trailingStopLoss` flags are present at placement time too, so a market order can be opened already flagged for GSL or server-side trailing.
- `positionId` field allows a `ProtoOANewOrderReq` to reference an existing position (partial add), separate from the SL/TP mechanics.

---

## 6. Rate-limit class of amend commands

**STATUS: CONFIRMED-PRIMARY for the two numeric buckets; the classification of amend/trade commands specifically into the "non-historical" bucket is a reasonable inference, not an explicit primary statement — marked accordingly.**

Source: https://help.ctrader.com/open-api/ (Getting Started), exact quoted text:
> "You can perform a maximum of 50 requests per second per connection for any non-historical data requests. You can perform a maximum of 5 requests per second per connection for any historical data requests."

This is the only rate-limit statement found on the primary docs surface reached in this pass. It does **not** explicitly enumerate which payload types are "historical" vs "non-historical" (e.g., it does not name `ProtoOAGetTrendbarsReq`/`ProtoOAGetTickDataReq` as historical, nor `ProtoOAAmendPositionSLTPReq`/`ProtoOAAmendOrderReq`/`ProtoOANewOrderReq` as non-historical). "Historical data requests" most plausibly refers to the bar/tick-history retrieval endpoints by name, which would put trading/amend commands in the 50 req/s bucket by elimination — **but this is an inference, not a quoted classification**, so it is marked SECONDARY-ONLY / inferred rather than CONFIRMED-PRIMARY for the specific bucket assignment of amend commands. A generic 429/`BLOCKED_PAYLOAD_TYPE` rate-limit error surface (with `retryAfter` seconds field on `ProtoOAErrorRes`) is documented on https://help.ctrader.com/open-api/faq/ and in `OpenApiMessages.proto` (CONFIRMED-PRIMARY for the mechanism, not for which numeric bucket applies to amend calls specifically).

---

## Summary table

| # | Question | Verdict |
|---|---|---|
| 1 | `ProtoOAAmendPositionSLTPReq` fields/units/response | CONFIRMED-PRIMARY |
| 2 | `ProtoOAAmendOrderReq` fields, SL/TP settable | CONFIRMED-PRIMARY |
| 3 | Atomic server-side amend (never unprotected) | UNDOCUMENTED |
| 4a | Native trailing-stop flag exists | CONFIRMED-PRIMARY |
| 4b | Trailing is server-side (push event on change) | CONFIRMED-PRIMARY |
| 4c | Trailing distance/step algorithm details | UNDOCUMENTED (secondary color only) |
| 5 | SL/TP at placement on `ProtoOANewOrderReq`; absolute vs relative | CONFIRMED-PRIMARY (absolute NOT supported for MARKET; relative is the documented path) |
| 6 | Rate-limit numeric buckets exist (50/s, 5/s) | CONFIRMED-PRIMARY |
| 6b | Amend commands fall in the non-historical (50/s) bucket | Inferred / SECONDARY-ONLY (not explicitly named in the docs reached) |
