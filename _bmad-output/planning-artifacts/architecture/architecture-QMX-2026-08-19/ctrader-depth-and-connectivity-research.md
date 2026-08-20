# cTrader Open API — depth (DOM) and demo/live connectivity (2026-08-20)

Single-agent primary-source pass, prompted by operator questions (L3/order-flow availability; demo-as-failsafe + live simultaneously). Grades: primary-doc > primary-proto > staff-forum > community/inference. Research protocol: presented, not adopted.

## A. Market depth — Level-2-class, NOT a trade tape

**Messages exist [primary-proto, OpenApiMessages.proto + OpenApiModelMessages.proto]:** `ProtoOASubscribeDepthQuotesReq/Res` (2156/2157), `ProtoOAUnsubscribeDepthQuotesReq/Res` (2158/2159), `ProtoOADepthEvent` (2155) with `repeated ProtoOADepthQuote newQuotes` + `repeated uint64 deletedQuotes` (differential book updates), and:

```proto
message ProtoOADepthQuote {
    required uint64 id = 1;   // Quote ID.
    required uint64 size = 3; // Quote size in cents.
    optional uint64 bid = 4;  // Bid price for bid quotes.
    optional uint64 ask = 5;  // Ask price for ask quotes.
}
```

- Granularity: **resting-liquidity book of individual LP quotes with unique ids — Level-2-class**. The docs' own words: "you can also receive live depth or **Level II quotes** for a symbol" [primary-doc, https://help.ctrader.com/open-api/symbol-data/ "Depth quotes"].
- **No Level-3 / time-and-sales / executed-print stream for the market exists** — confirmed by exhaustive read of the ProtoOAPayloadType enum (2100–2188). All executed-trade data is the authenticated account's OWN deals (ProtoOAExecutionEvent, ProtoOADeal, deal lists). Trendbar `volume` is "Bar volume in ticks" — a tick count, not traded volume.
- Decoding: depth price = raw ÷ 100000 rounded to symbol digits [primary-doc]; size = ÷ 100 ("Quote size in cents" [primary-proto]). NOTE: the ÷100000 for depth is docs-attested only — DepthQuote field comments carry no scale note.
- Gaps: number of levels / depth cap / update cadence NOT stated; `NOT_SUBSCRIBED_TO_SPOTS = 112` implies spot subscription may be a prerequisite for depth (undocumented ordering dependency).

## B. Demo vs live connectivity

**Separate hosts, stated verbatim [primary-doc, https://help.ctrader.com/open-api/proxies-endpoints/]:**

| Live | Demo |
| --- | --- |
| `live.ctraderapi.com:5035` (Protobuf) | `demo.ctraderapi.com:5035` (Protobuf) |
| `live.ctraderapi.com:5036` (JSON) | `demo.ctraderapi.com:5036` (JSON) |

> "Demo and live environments are fully separated. If you connect to a live endpoint, you cannot use demo accounts in your application, and vice versa. If your application needs to operate on behalf of demo and live accounts simultaneously, you would need to establish and maintain two separate connections."

- Ports carry TCP or WebSocket; TCP must use SSL; hosts fronted by AWS Global Accelerator (region proxy redirect).
- **One connection = unlimited accounts of one environment** [primary-doc, connection Best practices]: "At most, you should create two connections: one for demo accounts and one for live accounts. Each connection can support an unlimited number of accounts of a certain type." Flow: one `ProtoOAApplicationAuthReq` per connection, then one `ProtoOAAccountAuthReq(ctidTraderAccountId, accessToken)` per account.
- `ProtoOACtidTraderAccount.isLive` [primary-proto]: "If TRUE then the account is belong to Live environment and live host must be used to authorize it" — one access token enumerates BOTH environments' accounts; the HOST is environment-specific, the token is not.
- Reconnect: app-auth before any message is mandatory per connection [primary-doc]; re-auth of app + each account after reconnect is inference from that rule. Session-termination signals: `ProtoOAAccountsTokenInvalidatedEvent` (2147), `ProtoOAAccountDisconnectEvent` (2164). Heartbeat every 10s [primary-doc]. Weekend maintenance windows exist [primary-doc FAQ].

## C. Token lifecycle facts (feeds GAP-0035) [primary-doc]

- Access token expiry: "2,628,000 seconds (approximately 30 days)". Renewable via refresh token, before or after expiry.
- **"The refresh token does not have an expiration period."** / FAQ: "The refresh token is valid forever until you use it to refresh an access token or if you re-authorise your cTrader ID and trading accounts."
- Refresh via REST (`openapi.ctrader.com/apps/token?grant_type=refresh_token`) or in-band `ProtoOARefreshTokenReq/Res` (2173/2174).
- Compromise-recovery anchor: re-authorizing the cTID invalidates outstanding refresh tokens.

## Gaps

1. Market trade tape / L3: NOT FOUND (definitive — closed payload catalog).
2. Depth levels count / cadence: NOT stated.
3. Depth price scale in proto comments: docs-only.
4. Literal "re-authenticate after reconnect" sentence: inference from mandatory app-auth rule.
5. Numeric per-connection account ceiling: "unlimited" per docs; connection-count ceiling exists (error 67) but number unpublished.
