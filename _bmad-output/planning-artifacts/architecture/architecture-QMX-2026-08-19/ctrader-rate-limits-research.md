# cTrader Open API — rate limits & historical-data caps (re-research, 2026-08-20)

Single-agent primary-source pass (relaunched after the workflow researcher failed on output format). Grades: primary-doc > primary-proto > staff-forum > community/inference. Research protocol: presented, not adopted.

## 1. The 50/5 req/s limits — CONFIRMED primary-doc

Verbatim, "Rate limiting" box, Getting started page (https://help.ctrader.com/open-api/ #essential-functionality):

> Note that some limits exist on how frequently you can perform certain requests to the cTrader backend.
> - You can perform a maximum of 50 requests per second per connection for any non-historical data requests.
> - You can perform a maximum of 5 requests per second per connection for any historical data requests.

Which messages count as "historical" vs "non-historical" is NOT enumerated anywhere — the classification is inference.

## 2. Scope — per connection (explicit)

"per connection" is the stated unit for both figures [primary-doc]. Per-account and per-clientId scoping of the request rate: NOT stated. Separate per-client limit exists for connections: `CONNECTIONS_LIMIT_EXCEEDED = 67; // Limit of connections is reached for this Open API client.` [primary-proto] — the numeric cap is unpublished.

## 3. Window semantics — NOT-FOUND

FAQ says only: "The 429 error response means that the user has sent too many requests in a given period." (https://help.ctrader.com/open-api/faq #why-do-i-get-the-429-error-response). Sliding vs fixed vs token bucket: undocumented.

## 4. Breach signals [primary-proto unless noted]

- `REQUEST_FREQUENCY_EXCEEDED = 108; // Request frequency is reached.` (ProtoOAErrorCode, OpenApiModelMessages.proto)
- `CHANNEL_IS_BLOCKED = 110; // Operations are not allowed for this account.`
- `CONNECTIONS_LIMIT_EXCEEDED = 67` (as above)
- `INCORRECT_BOUNDARIES = 35; // When requested period (from,to) is too large or invalid values are set to from/to.` (oversized history spans)
- `BLOCKED_PAYLOAD_TYPE = 11; // Message is blocked by server or rate limit is reached.` (ProtoErrorCode, OpenApiCommonModelMessages.proto — lower-level channel)
- HTTP-style 429 per FAQ [primary-doc].

Ban / cooldown / backoff / reconnect-after-breach policy: NOT-FOUND. The error-handling page carries no rate-limit content. Only reconnect-adjacent guidance is inactivity-based: "make sure that you send a heartbeat to the server at least once every 10 seconds." [primary-doc, FAQ]

## 5. Per-message span caps — proto verbatim (all primary-proto, OpenApiMessages.proto)

- `ProtoOAGetTickDataReq`: NO span clause. Only `fromTimestamp … >= 0` / `toTimestamp … <= 2147483646000`. (The 1-week tick cap IS documented, but on the symbol-data docs page — see tick-mechanics report; runtime enforcement via error 35.)
- `ProtoOAGetTrendbarsReq`: NO span clause, NO per-period table. `optional uint32 count = 7; // Limit number of trend bars in response back from toTimestamp.` The widely-cited per-period week caps are community lore, not primary.
- `ProtoOADealListReq` / `ProtoOAOrderListReq`: NO span clause; DealList has `maxRows`.
- `ProtoOACashFlowHistoryListReq`: HAS the cap — `required int64 fromTimestamp = 3; // … Validation: toTimestamp - fromTimestamp <= 604800000 (1 week).`

## 6. Connection / subscription caps

Connection ceiling per client exists (error 67) — number unpublished. Symbol-subscription-count cap: NOT-FOUND.

## Gaps

1. Window semantics (sliding/fixed/bucket + averaging interval) — undocumented.
2. Ban/backoff policy on breach — undocumented.
3. Historical vs non-historical message classification — never enumerated.
4. Numeric per-client connection cap — unpublished.
5. Symbol-subscription cap — not found.
6. Per-period trendbar span limits — not in proto; runtime error 35 only.

Proto files downloaded to session scratchpad for desk verification (OpenApiMessages.proto 795 lines, OpenApiModelMessages.proto 723 lines, OpenApiCommonModelMessages.proto 34 lines).
