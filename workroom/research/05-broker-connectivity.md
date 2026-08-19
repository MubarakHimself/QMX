# 05 — Broker Connectivity: what a platform-blind QMF adapter layer must expose

Research date: **2026-08-17**. All load-bearing claims cite a primary source inline.
Anything I could not confirm against a primary source is marked **UNVERIFIED**.

---

## In plain words

- QMX will talk to a broker (cTrader first, MetaTrader 5 and crypto later). Every broker speaks its own dialect. QMF needs one translator layer so strategies never learn any dialect.
- cTrader's Open API is a proper network API: your program connects over the internet to Spotware's servers, logs in with OAuth, and gets prices and fills pushed to it live. No trading terminal app needs to be running. It works fine on a plain Linux VPS.
- MetaTrader 5's Python package is not really a network API. It is a remote control for a *running MT5 desktop program*. The Python package only ships Windows builds. On Linux you must run the Windows terminal inside Wine (a Windows emulator layer) and bridge into it — a ~4 GB container with a virtual desktop inside. It works, people do it daily, but it is a moving part that can silently die.
- MT5 also has no "push" — nothing tells your code a price changed. You must ask, in a loop, forever. cTrader pushes prices and fills to you as events. For a system that must never miss a fill, push beats polling.
- Recommendation in one line: **cTrader Open API is the right live-trading and data-collection spine for a Linux VPS; MT5 is a second-class, Windows-shaped fallback worth adding only for instruments or brokers cTrader cannot reach.**
- The catch: Spotware's official Python client (`ctrader-open-api` / OpenApiPy) has had **no commit since 2024-08-07** and no release since 2024-06-26, while the underlying protocol *was* changed in 2025. It is not abandoned-abandoned, but it is stale and pins ancient dependency versions.
- So QMF should treat that library as a thin, replaceable wire (or replace it outright), and put all the real logic — reconnection, re-authentication, order state, rate limiting — in QMF's own adapter.
- The proven pattern for "one surface, many venues" is ccxt (43k stars, commits today). Its lesson: unify the *names and shapes*, keep the raw venue payload attached, and publish a machine-readable capability map so callers can ask "does this venue support that?" instead of guessing.
- NautilusTrader's lesson is harder and more valuable: an order command has **three** possible outcomes, not two — accepted, rejected, and *unknown*. Most retail bots lose money on the third one. QMF must model "unknown" explicitly.
- LEAN's lesson: separate "how do I talk to the venue" (the brokerage) from "what will this venue actually let me do" (the brokerage model — order types, leverage, fees). Two objects, not one.
- Practical money-losing detail: cTrader never tells you your account equity. You must compute it. And it reports volumes in hundredths of a unit and prices in hundred-thousandths. If those quirks leak into strategy code, a strategy will one day trade 100x its intended size.

---

## Findings

### 1. cTrader Open API — the protocol (primary sources)

**Transport and endpoints.** Live is `live.ctraderapi.com`, demo is `demo.ctraderapi.com`. Protobuf **must** use port `5035`; JSON **must** use port `5036`; both ports accept TCP and WebSocket, and demo/live are "fully separated" so a single connection cannot serve both ([proxies & endpoints](https://help.ctrader.com/open-api/proxies-endpoints/)). The docs state "The TCP client connection must use SSL, otherwise you will not be able to connect", and recommend "at most, you should create two connections: one for demo accounts and one for live accounts" plus "Use a message queue for sending and receiving data to avoid concurrent send and receive events" ([establish a connection](https://help.ctrader.com/open-api/connection/)). Routing is via AWS Global Accelerator to the nearest proxy (same page).

The SDK hard-codes these: `AUTH_URI = https://openapi.ctrader.com/apps/auth`, `TOKEN_URI = https://openapi.ctrader.com/apps/token`, `PROTOBUF_PORT = 5035` ([endpoints.py](https://raw.githubusercontent.com/spotware/OpenApiPy/main/ctrader_open_api/endpoints.py)).

**Framing.** The official client uses Twisted's `Int32StringReceiver` — a 4-byte big-endian length prefix per message — with `MAX_LENGTH = 15000000` ([tcpProtocol.py](https://raw.githubusercontent.com/spotware/OpenApiPy/main/ctrader_open_api/tcpProtocol.py)). The envelope is `ProtoMessage{payloadType, payload, clientMsgId}`; `clientMsgId` is the client-assigned correlation id echoed in the response ([OpenApiCommonMessages.proto](https://raw.githubusercontent.com/spotware/openapi-proto-messages/main/OpenApiCommonMessages.proto)).

**Heartbeat — note the contradiction.** The help centre says "To keep a connection alive, keep sending a heartbeat event every 10 seconds" and "make sure that you send a heartbeat to the server at least once every 10 seconds" ([connection](https://help.ctrader.com/open-api/connection/), [FAQ](https://help.ctrader.com/open-api/faq/)). The `.proto` comment says the client "can send this message when he needs to keep the connection open for a period without other messages longer than 30 seconds" ([OpenApiCommonMessages.proto](https://raw.githubusercontent.com/spotware/openapi-proto-messages/main/OpenApiCommonMessages.proto)). The SDK actually sends a heartbeat only after **20 s** of send-idleness, and echoes any heartbeat the server sends (`tcpProtocol._sendStrings` / `stringReceived`). Three numbers, three sources. QMF should use the strictest (**10 s**).

**Authentication — two independent layers.**
1. *Application auth*: `ProtoOAApplicationAuthReq{clientId, clientSecret}` — per connection.
2. *Account auth*: `ProtoOAAccountAuthReq{ctidTraderAccountId, accessToken}` — **per trading account, per connection**.
OAuth details ([account authentication](https://help.ctrader.com/open-api/account-authentication/)): authorization code "expiration period is one minute"; access token "2,628,000 seconds (approximately 30 days)"; "The refresh token does not have an expiration period". Scopes are `accounts` (view only — "performing trading operations will be impossible") and `trading`.
The SDK's `Auth.getToken` / `Auth.refreshToken` perform the exchange with **`requests.get`**, i.e. `client_secret` and `refresh_token` travel in the query string ([auth.py](https://raw.githubusercontent.com/spotware/OpenApiPy/main/ctrader_open_api/auth.py)) — fine over TLS but query strings land in logs/proxies. Treat as a hygiene issue.

**Application registration is gated.** "Spotware carefully evaluates new Open API services"; proceed with coding "After receiving approval from Spotware" ([creating a new app](https://help.ctrader.com/open-api/creating-new-app/)). This is a real lead-time item for QMX.

**Rate limits.** "You can perform a maximum of 50 requests per second per connection for any non-historical data requests" and "a maximum of 5 requests per second per connection for any historical data requests" ([getting started](https://help.ctrader.com/open-api/)). These are **per connection regardless of how many accounts are authorized on it** ([forum, Spotware-adjacent moderator answer](https://community.ctrader.com/forum/connect-api-support/41177/)). HTTP-style `429` semantics are described in the [FAQ](https://help.ctrader.com/open-api/faq/). The current `ProtoOAErrorRes` carries `maintenanceEndTimestamp` and `retryAfter` — "When you hit rate limit with errorCode=BLOCKED_PAYLOAD_TYPE, this field will contain amount of seconds until related payload type will be unlocked" ([OpenApiMessages.proto](https://raw.githubusercontent.com/spotware/openapi-proto-messages/main/OpenApiMessages.proto)).

**Trading capability surface** (message names verified in [OpenApiMessages.proto](https://raw.githubusercontent.com/spotware/openapi-proto-messages/main/OpenApiMessages.proto) and [messages reference](https://help.ctrader.com/open-api/messages/)):

| Need | Message |
|---|---|
| New order | `ProtoOANewOrderReq` |
| Amend pending order | `ProtoOAAmendOrderReq` |
| Cancel pending order | `ProtoOACancelOrderReq` |
| Amend position SL/TP | `ProtoOAAmendPositionSLTPReq` |
| Close / **partial close** position | `ProtoOAClosePositionReq{positionId, volume}` |
| Snapshot open positions + pending orders | `ProtoOAReconcileReq{returnProtectionOrders}` |
| Order history | `ProtoOAOrderListReq` |
| Fill history | `ProtoOADealListReq`, `ProtoOADealListByPositionIdReq`, `ProtoOADealOffsetListReq` |
| Unrealized P&L | `ProtoOAGetPositionUnrealizedPnLReq` |
| Execution stream | `ProtoOAExecutionEvent` |
| Order-level error | `ProtoOAOrderErrorEvent{errorCode, orderId, positionId, description}` |

Order types (`ProtoOAOrderType`): `MARKET, LIMIT, STOP, STOP_LOSS_TAKE_PROFIT, MARKET_RANGE, STOP_LIMIT`. Time in force: `GOOD_TILL_DATE, GOOD_TILL_CANCEL, IMMEDIATE_OR_CANCEL, FILL_OR_KILL, MARKET_ON_OPEN`. Execution types: `ORDER_ACCEPTED, ORDER_FILLED, ORDER_REPLACED, ORDER_CANCELLED, ORDER_EXPIRED, ORDER_REJECTED, ORDER_CANCEL_REJECTED, SWAP, DEPOSIT_WITHDRAW, ORDER_PARTIAL_FILL, BONUS_DEPOSIT_WITHDRAW` ([model messages](https://help.ctrader.com/open-api/model-messages/)). `ProtoOAExecutionEvent.isServerEvent` — "If TRUE then the event generated by the server logic instead of the trader's request. (e.g. stop-out)" — is how you learn about liquidations.

Order-request quirks that matter: `volume` is "0.01 of a unit (e.g. 1000 = 10.00 units)"; absolute `stopLoss`/`takeProfit` are "Not supported for MARKET orders" — you must use `relativeStopLoss`/`relativeTakeProfit` "in 1/100000 of unit of price"; `comment` ≤512, `label` ≤100, `clientOrderId` ≤50 chars; `guaranteedStopLoss`, `trailingStopLoss`, `stopTriggerMethod` are booleans/enums on the same request ([messages reference](https://help.ctrader.com/open-api/messages/)).

**Position model is hedging, not netting.** Positions carry their own `positionId`, VWAP `price`, `usedMargin`, `swap`, `commission` ([model messages](https://help.ctrader.com/open-api/model-messages/)). This is the opposite of an exchange-style single net position and the opposite of MT5 netting accounts.

**Account state — equity is NOT provided.** `ProtoOATrader` gives `balance`, `leverageInCents`, `depositAssetId`, `moneyDigits`. Equity must be derived: the documented path is `ProtoOAGetPositionUnrealizedPnLReq` → gross/net unrealized P&L per position, with a documented cap of "a maximum of 50 such requests per second" and a recommendation to refresh every 2–3 s ([calculating profit/loss](https://help.ctrader.com/open-api/profit-loss-calculation/)). Margin changes arrive as `ProtoOAMarginChangedEvent`.

**Scaling quirks (all leak-prone).**
- Money: `moneyDigits` exponent — "moneyDigits = 8 must be interpret as business value multiplied by 10^8, then real balance would be 10053099944 / 10^8 = 100.53099944" ([proto](https://raw.githubusercontent.com/spotware/openapi-proto-messages/main/OpenApiMessages.proto)).
- Volume: cents (1/100 of a unit).
- Prices in spot events: `uint64` "Specified in 1/100000 of unit of a price".
- Leverage: `leverageInCents` ("1:50 then value = 5000").
- Symbol: `digits`, `pipPosition`, `lotSize` (in cents), `minVolume`/`stepVolume`/`maxVolume` (in cents).

**Market data.**
- `ProtoOASubscribeSpotsReq{repeated symbolId, subscribeToSpotTimestamp}`; the first `ProtoOASpotEvent` after subscribing carries the latest prices "even if market is closed", then updates stream. `bid` and `ask` are both **optional** in `ProtoOASpotEvent` — an event may update only one side.
- Live bars require a spot subscription first: `ProtoOASubscribeLiveTrendbarReq` "Requires subscription on the spot events".
- Depth: `ProtoOASubscribeDepthQuotesReq`.
- Unsubscribe is queued: "You may still occasionally receive ProtoOASpotEvents until request processing is complete."

**Historical data — the real constraints.**
- Bars: `ProtoOAGetTrendbarsReq{fromTimestamp, toTimestamp, period, symbolId, count}`; response carries `hasMore`. The `.proto` documents **no** span limit, but the help centre states "there are some constraints on the maximum possible distance between the `toTimestamp` and the `fromTimestamp`. These constraints depend on the specified `ProtoOATrendPeriod`" ([attain symbol data](https://help.ctrader.com/open-api/symbol-data/)), and a Spotware moderator states "There is a hard limit of 14000 bars" with roughly a 2-week window for M1 ([forum 24731](https://community.ctrader.com/forum/connect-api-support/24731/)). The exact per-period table is **not published** — QMF must discover it empirically and cache it.
- Ticks: "It is impossible to request historical tick data for a period larger than one week" (604,800,000 ms), and responses are chunked with a `hasMore` flag ([attain symbol data](https://help.ctrader.com/open-api/symbol-data/)).
- Tick encoding is delta-compressed: "The first tick contains Unix time in milliseconds while all subsequent ticks have the time difference in milliseconds between the previous and the current one" — and the same comment confusingly says "chronological order (newest first)" ([proto](https://raw.githubusercontent.com/spotware/openapi-proto-messages/main/OpenApiMessages.proto)). Decode carefully and verify direction against real data.
- Bar encoding is delta-compressed too: `ProtoOATrendbar{low, deltaOpen, deltaHigh, deltaClose, utcTimestampInMinutes, volume}` — open = low + deltaOpen, and the timestamp is in **minutes**, not milliseconds ([OpenApiModelMessages.proto](https://raw.githubusercontent.com/spotware/openapi-proto-messages/main/OpenApiModelMessages.proto)).
- Gaps are normal, not errors: "trend bars are only created if there are incoming ticks" ([FAQ](https://help.ctrader.com/open-api/faq/)).
- Throughput ceiling for backfill: 5 historical req/s × 14,000 bars ≈ 70k bars/s theoretical, but M1 caps at ~2 weeks (~20k bars) per request, so a 10-year M1 backfill of one symbol is ~260 requests ≈ ~1 minute of wall clock at the limit. Tick backfill is far worse: 1 week per request × chunking.

**Failure/lifecycle events QMF must handle** (all from the [proto](https://raw.githubusercontent.com/spotware/openapi-proto-messages/main/OpenApiMessages.proto)):
- `ProtoOAClientDisconnectEvent{reason}` — server killed the whole connection; "All the sessions for the traders' accounts will be terminated."
- `ProtoOAAccountDisconnectEvent{ctidTraderAccountId}` — "the established session for an account is dropped on the server side. A new session must be authorized for the account." Connection survives; the account does not.
- `ProtoOAAccountsTokenInvalidatedEvent{ctidTraderAccountIds, reason}` — "account was deleted, cTID was deleted, **token was refreshed**, token was revoked". Note: *refreshing your own token de-authorizes your live sessions.* Confirmed in [forum 36073](https://community.ctrader.com/forum/connect-api-support/36073/): "token expiration or refresh... can de-authorize accounts even when still connected".
- `ProtoOATraderUpdatedEvent`, `ProtoOAMarginChangedEvent`, `ProtoOASymbolChangedEvent` (symbol specs mutate at runtime → invalidate cached specs).
- Weekend maintenance: "Sometimes we do maintenance and upgrades during weekends, and the API is inaccessible during the maintenance period" ([FAQ](https://help.ctrader.com/open-api/faq/)); `ProtoErrorRes.maintenanceEndTimestamp` tells you when it ends.

**Error taxonomy** is a flat string enum: `ProtoOAErrorCode` includes `OA_AUTH_TOKEN_EXPIRED, ACCOUNT_NOT_AUTHORIZED, CONNECTIONS_LIMIT_EXCEEDED, REQUEST_FREQUENCY_EXCEEDED, SERVER_IS_UNDER_MAINTENANCE, NOT_SUBSCRIBED_TO_SPOTS, ALREADY_SUBSCRIBED, SYMBOL_NOT_FOUND, NO_QUOTES, NOT_ENOUGH_MONEY, MAX_EXPOSURE_REACHED, POSITION_NOT_FOUND, ORDER_NOT_FOUND, POSITION_LOCKED, TOO_MANY_POSITIONS, TRADING_BAD_VOLUME, TRADING_BAD_STOPS, TRADING_BAD_PRICES, PROTECTION_IS_TOO_CLOSE_TO_MARKET, TRADING_DISABLED, UNABLE_TO_CANCEL_ORDER, UNABLE_TO_AMEND_ORDER, ...` ([model messages](https://help.ctrader.com/open-api/model-messages/)). There is **no class hierarchy** — QMF must build the retryable/fatal/venue-rejection classification itself.

**Broker availability.** Marketing pages say Open API is "free, secure and public" ([Spotware dev resources](https://www.spotware.com/ctrader/dev-resources/open-api/)); third-party 2026 write-ups claim it is enabled by default on cTrader-affiliated broker accounts, but I could not confirm that on a Spotware primary page — **UNVERIFIED**. Broker-by-broker verification is an operator task.

---

### 2. OpenApiPy (`ctrader-open-api`) — maintenance state and what it actually does

**Health as of 2026-08-17:**
- GitHub `spotware/OpenApiPy`: 190 stars, MIT, **not archived**, `pushed_at = 2024-08-07`, 12 open issues ([GitHub API](https://api.github.com/repos/spotware/OpenApiPy)). Last 10 commits all fall between 2024-06-25 and 2024-08-07, ending on a *revert* of a message update ([commits](https://api.github.com/repos/spotware/OpenApiPy/commits?per_page=10)).
- PyPI: latest installable is **0.9.2 (2024-06-26)**; **0.9.3 (2024-08-06) is yanked** ([PyPI JSON](https://pypi.org/pypi/ctrader-open-api/json)).
- Spotware still calls it official: "This SDK is developed and maintained entirely by Spotware" ([Python SDK docs](https://help.ctrader.com/open-api/python-SDK/python-sdk-index/)).

**Meanwhile the protocol moved on.** `spotware/openapi-proto-messages` — which the FAQ itself names as the change-notification channel ("Please follow the Open API Proto message files repository and its releases") — has commits on **2025-07-16, 2025-08-06 (×2), and 2025-11-13**, including "Remove some payloads (#31)" and "Remove certain payloads" ([commit log](https://github.com/spotware/openapi-proto-messages/commits/main)).

**Concrete divergence, verified:** the current `ProtoOAErrorRes` has a `retryAfter` field; the generated messages bundled in OpenApiPy `main` do not. Grepping the shipped `OpenApiMessages_pb2.py` finds `maintenanceEndTimestamp` (1 hit) and `retryAfter` (**0 hits**). So an app built on the SDK as shipped is blind to the server's own rate-limit backoff hint.

**Dependency pins are hard `==` and old** ([PyPI metadata](https://pypi.org/pypi/ctrader-open-api/json)): `Twisted==24.3.0` (current Twisted is 26.4.0), `pyOpenSSL==24.1.0`, `protobuf==3.20.1`, `requests==2.32.3`, `inputimeout==1.0.4`; `requires_python >=3.8,<4.0`. `protobuf==3.20.1` publishes binary wheels only for cp36–cp310 plus a pure-Python `py2.py3-none-any` wheel ([PyPI](https://pypi.org/pypi/protobuf/3.20.1/json)). On Python ≥3.11 pip therefore falls back to the pure-Python protobuf runtime (slower) or a source build, and `protobuf==3.20.1` will conflict with anything in QMF wanting protobuf 4/5/6 (grpc, OpenTelemetry, many ML libs). Whether the 3.20.1 pure-Python runtime actually imports cleanly on Python 3.12/3.13 is **UNVERIFIED** — test before committing.

**What the SDK does well** (from source):
- Automatic reconnect via Twisted `ClientService` with a retry policy ([client.py](https://raw.githubusercontent.com/spotware/OpenApiPy/main/ctrader_open_api/client.py)).
- Automatic heartbeat when send-idle >20 s, and heartbeat echo on receipt ([tcpProtocol.py](https://raw.githubusercontent.com/spotware/OpenApiPy/main/ctrader_open_api/tcpProtocol.py)).
- Client-side outbound throttle: a 1-second `LoopingCall` drains at most `numberOfMessagesToSendPerSecond` (**default 5**) messages per tick.
- `clientMsgId` correlation with a per-request `Deferred` and a **5-second default response timeout**.

**What it does badly / dangerously** (from source — these are the things QMF must not inherit):
1. **Class-level mutable state.** `_send_queue = deque([])`, `_send_task = None`, `_lastSendMessageTime = None` are declared on the `TcpProtocol` *class*, not per instance. Two connections (the docs recommend exactly two: demo + live) share one outbound queue and one send task. This is a latent cross-connection message-mixing bug.
2. **A single 5 msg/s queue for everything.** Order submits queue behind bulk historical requests. There is no priority lane, and no distinction between the 50/s and 5/s server buckets.
3. **Pending requests are silently dropped on disconnect.** `_disconnected` calls `self._responseDeferreds.clear()` without erroring them back; callers only learn via the 5 s timeout. Every in-flight order submit at disconnect time becomes an *unknown outcome* with no explicit signal.
4. **No re-authentication after reconnect.** `ClientService` restores the socket; nothing re-sends `ProtoOAApplicationAuthReq` / `ProtoOAAccountAuthReq` or re-subscribes spots. That is 100% the application's job.
5. **Stringly-typed message construction.** `Protobuf.get("NewOrderReq", **params)` resolves by name at runtime, and messages are exported through wildcard imports — which is exactly why users report "OpenApiPy missing all Proto instances" as an IDE/static-analysis artifact ([forum 39535](https://community.ctrader.com/forum/connect-api-support/39535/)). Terrible for typed code and worse for LLM agents that rely on signatures.
6. Community reports of unresolved auth timeouts on the package ([forum 45875](https://community.ctrader.com/forum/connect-api-support/45875/), Dec 2024, no official resolution in-thread).

**Ecosystem alternatives** are thin: the only other notable cTrader Open API repos are Spotware's own `OpenAPI.Net` (C#, 92★, pushed 2024-06-28), a Rust port (3★), an Elixir port (0★), and a scattering of 0-star Python wrappers ([GitHub search](https://api.github.com/search/repositories?q=ctrader+openapi&sort=stars)). There is **no** actively-maintained community-grade async-Python cTrader client. QMF is on its own here.

**Note for the LLM-agent roadmap:** Spotware now ships "cTrader MCP servers" that let agents "Place orders, manage pending orders, modify and close positions" in natural language, with the warning "AI-generated actions may trigger real trades and result in losses" ([cTrader AI Agent Connect](https://help.ctrader.com/ctrader-ai-agent-connect/)). This is a *desktop/web platform* integration, not a substitute for a programmatic adapter, but it confirms Spotware's direction of travel.

---

### 3. MetaTrader 5 Python package — hard constraints, honestly

**It is actively maintained.** PyPI `MetaTrader5` latest is **5.0.6090, released 2026-08-01**, with a steady 2025–2026 cadence (5.0.5200 Aug 2025 → 5.0.5430 Nov 2025 → 5.0.5572 Jan 2026 → 5.0.5735 Apr 2026 → 5.0.6070 Jul 2026) ([PyPI release history](https://pypi.org/project/MetaTrader5/#history)). Classifiers and wheels: **Windows only, `win_amd64` only**, Python 3.6–3.14, depends on `numpy>=1.7` ([PyPI JSON](https://pypi.org/pypi/MetaTrader5/json)). So the *package* is healthier than OpenApiPy; the *architecture* is the problem.

**Constraint 1 — it is IPC to a running terminal, not a network API.** `initialize()` "Establish a connection with the MetaTrader 5 terminal", and "If required, the MetaTrader 5 terminal is launched to establish connection when executing the initialize() call" ([mt5initialize](https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py)). MetaQuotes describes it as "efficient and fast obtaining of exchange data via interprocessor communication, directly from MetaTrader 5" ([build 2085 news](https://www.metatrader5.com/en/news/2086)). No terminal → no API.

**Constraint 2 — there is no streaming/push.** The complete function list ([python_metatrader5](https://www.mql5.com/en/docs/python_metatrader5)) contains no callback, event-loop, or subscription-delivery primitive. `market_book_add()` subscribes the *terminal* to depth events, but you still retrieve via `market_book_get()`. Everything is request/response: `symbol_info_tick`, `copy_rates_from_pos`, `positions_get`, `orders_get`, `history_deals_get`. Live behaviour must be synthesized by polling — which means (a) you can miss intra-poll fills and must reconcile from `history_deals_get`, and (b) tick-accurate live data collection is not achievable, only tick *history* pulls.

**Constraint 3 — history is bounded by a GUI setting.** "MetaTrader 5 terminal provides bars only within a history available to a user on charts. The number of bars available to users is set in the 'Max. bars in chart' parameter" ([copy_rates_from](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesfrom_py)). A headless data collector's reach is therefore a terminal config value, not an API parameter. Ticks come via `copy_ticks_from`/`copy_ticks_range` with `COPY_TICKS_ALL/INFO/TRADE` flags, and the docs warn "Python uses the local time zone, while MetaTrader 5 stores tick and bar open time in UTC time zone (without the shift)" ([copy_ticks_from](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksfrom_py)).

**Constraint 4 — one process, one terminal, one account.** Community/forum consensus is that a Python process binds one terminal and one account at a time; multi-account means multiple terminal installs and multiple processes, with a platform ceiling around 32 terminals per Windows session and a practical ceiling lower ([MQL5 forum](https://www.mql5.com/en/forum/386667), [MQL5 forum](https://www.mql5.com/en/forum/478406)). I found no MetaQuotes primary page stating the limit — treat the "32" figure as **UNVERIFIED**, but treat "one account per process" as operationally true.

**Constraint 5 — the trade request is a flat struct with venue-shaped semantics.** `MqlTradeRequest{action, magic, order, symbol, volume, price, stoplimit, sl, tp, deviation, type, type_filling, type_time, expiration, comment, position, position_by}` with `action ∈ {TRADE_ACTION_DEAL, TRADE_ACTION_PENDING, TRADE_ACTION_SLTP, TRADE_ACTION_MODIFY, TRADE_ACTION_REMOVE, TRADE_ACTION_CLOSE_BY}` ([order_send](https://www.mql5.com/en/docs/python_metatrader5/mt5ordersend_py), [ENUM_TRADE_REQUEST_ACTIONS](https://www.mql5.com/en/docs/constants/tradingconstants/enum_trade_request_actions)). Closing a position is *not* a close call — it is an opposite `TRADE_ACTION_DEAL` carrying the `position` ticket; partial close is the same with a smaller `volume`. Volumes are in **lots** (contrast: cTrader's cents). Fill policy (`type_filling`: FOK/IOC/RETURN) is broker-dependent and a common source of `Unsupported filling mode` rejections.

**Linux VPS deployment — what people actually do.**
- MetaQuotes ships an official Wine-based Linux installer script for the *terminal*: "The platform runs on Linux using Wine… supports Ubuntu, Debian, Linux Mint and Fedora distributions", with the advice "It is highly recommended to always use the latest versions of the operating system and Wine" ([install on Linux](https://www.metatrader5.com/en/terminal/help/start_advanced/install_linux)). No liability/support statement about headless or automated use.
- The Python *package* has no Linux wheel. The working pattern is: **Windows Python inside Wine runs an RPyC server; your Linux Python talks to it.** `mt5linux` — "uses Wine, RPyC, and mt5server.exe" — is genuinely alive: 210★, MIT, GitHub pushed **2026-08-14**, PyPI **1.1.1 on 2026-08-04**, deps `rpyc>=6,<7` + `plumbum` ([GitHub API](https://api.github.com/repos/lucas-campagna/mt5linux), [PyPI](https://pypi.org/pypi/mt5linux/json)). `MT5LinuxEnhanced` is the stale fork (0.3.1, 2024-05-18, [PyPI](https://pypi.org/project/MT5LinuxEnhanced/)).
- The container route is `gmag11/MetaTrader5-Docker`: "a Docker image for running MetaTrader5 with remote access via VNC, based on the KasmVNC project", including an "RPyC server for remote access to Python MetaTrader Library" and mt5linux support; **x86/amd64 only**, and "container size is considerably bigger from about 600 MB to 4 GB" ([GitHub](https://github.com/gmag11/MetaTrader5-Docker)). Release notes record "Wine was updated to version 10, as Wine 9 is not supported by MT5" — i.e. the Wine/MT5 pairing is a *versioned compatibility surface that breaks*.

**Honest verdict on MT5 for QMX's Linux VPS:** it works, and thousands of people run it. But the live path is `Linux Python → RPyC → Wine → Windows Python → IPC → MT5 terminal GUI process → broker`. That is five failure domains where cTrader has one TLS socket. For a solo operator with no on-call engineer, each added domain is a night of downtime you will not notice until you check the P&L.

---

### 4. ccxt — the unified-adapter pattern worth stealing

Health: 43,651★, MIT, `pushed_at 2026-08-17` (today), 759 open issues, described as "A unified trading API with more than 100 crypto exchanges and prediction markets" ([GitHub API](https://api.github.com/repos/ccxt/ccxt)). Maximally alive.

Architecture worth copying (verified in [base/exchange.py](https://raw.githubusercontent.com/ccxt/ccxt/master/python/ccxt/base/exchange.py) and the [manual](https://docs.ccxt.com/docs/manual)):

1. **Three layers per venue**: base Exchange class (shared machinery) → venue-specific raw API (`publicGet*`, `privatePost*`, `sign`) → unified API. Strategy code only ever touches the third layer.
2. **A declarative capability map.** `describe()['has']` is a ~200-key dict whose values are `True` / `False` / `None` (= not supported) / `'emulated'` (= we synthesize it from other calls). Sample keys: `createOrder`, `createOrders`, `createStopLimitOrder`, `createTrailingPercentOrder`, `createOrderWithTakeProfitAndStopLoss`, `editOrder: 'emulated'`, `cancelOrderWithClientOrderId`, `fetchOHLCV`, `fetchPositions`, `fetchMyTrades`, `closePosition`, `sandbox`. The `'emulated'` sentinel is the single best idea in the whole design: it distinguishes "native" from "we fake it" without hiding either.
3. **A stable unified order shape**, produced by `safe_order()` — exact keys: `id, clientOrderId, timestamp, datetime, symbol, type, side, lastTradeTimestamp, lastUpdateTimestamp, price, amount, cost, average, filled, remaining, timeInForce, postOnly, trades, reduceOnly, stopPrice (deprecated → triggerPrice), triggerPrice, takeProfitPrice, stopLossPrice, status, fee`, plus `info`.
4. **`info` always carries the raw venue payload.** Unification never destroys evidence.
5. **A real exception hierarchy** (from [base/errors.py](https://raw.githubusercontent.com/ccxt/ccxt/master/python/ccxt/base/errors.py)) — the shape QMF should mirror:
   - `BaseError`
     - `ExchangeError` → `AuthenticationError` (→ `PermissionDenied` → `AccountNotEnabled`; `AccountSuspended`), `ArgumentsRequired`, `BadRequest` (→ `BadSymbol`), `OperationRejected` (→ `NoChange` → `MarginModeAlreadySet`; `MarketClosed`; `ManualInteractionNeeded`; `RestrictedLocation`), `InsufficientFunds`, `InvalidOrder` (→ `OrderNotFound`, `OrderNotCached`, `OrderImmediatelyFillable`, `OrderNotFillable`, `DuplicateOrderId`, `ContractUnavailable`), `NotSupported`
     - `OperationFailed` → `NetworkError` (→ `DDoSProtection`, `RateLimitExceeded`, `ExchangeNotAvailable` → `OnMaintenance`, `InvalidNonce` → `ChecksumError`, `RequestTimeout`), `BadResponse` → `NullResponse`, `CancelPending`
   - The key structural insight: **`ExchangeError` (the venue said no) and `OperationFailed` (we don't know) are siblings, not parent/child.** That maps exactly onto Nautilus's three-tier outcome model.
6. **Streaming mirrors REST 1:1.** Every `fetchX` has a `watchX` (`watchOrderBook`, `watchTrades`, `watchOHLCV`, `watchOrders`, `watchMyTrades`, `watchPositions`, `watchBalance`), and "connections are managed by CCXT Pro transparently to the user", with `streaming.keepAlive`, `maxPingPongMisses`, and automatic reconnection with exponential backoff ([Pro manual](https://docs.ccxt.com/docs/pro-manual)). Same names, same shapes, different delivery.
7. **Precision and limits live on the market/instrument object**, so rounding is a venue fact, not strategy code.

---

### 5. NautilusTrader — the correctness rules

Health: 25,654★, LGPL-3.0, `pushed_at 2026-08-17` ([GitHub API](https://api.github.com/repos/nautechsystems/nautilus_trader)). 19 stable integrations — Binance, Bybit, OKX, Kraken, Coinbase, BitMEX, Deribit, dYdX, Hyperliquid, Lighter, Derive, Interactive Brokers, Betfair, Polymarket, Databento, Tardis, AX ([integrations](https://nautilustrader.io/docs/latest/integrations/)). **No cTrader and no MetaTrader adapter exists** — QMF cannot borrow one, and this is itself a signal about how much retail-FX plumbing is missing from the OSS ecosystem.

Adapter contract ([adapters concept](https://nautilustrader.io/docs/latest/concepts/adapters/), [adapter developer guide](https://nautilustrader.io/docs/latest/developer_guide/adapters/)):
- Components: `InstrumentProvider`, `DataClient` (subscriptions + historical requests), `ExecutionClient` (order lifecycle + account state + reports), plus `HttpClient` / `WebSocketClient` transports and config factories.

Rules I would lift verbatim into QMF's spec:
- **Three-tier outcome classification.** "Definitive local failure: deterministic validation proves that a submit command cannot be sent. Emit `OrderDenied` before `OrderSubmitted`." / "Definitive venue result: a structured venue response or status explicitly accepts, updates, or rejects one command." / "Unknown outcome: the request may have reached the venue, but no definitive result is available. Keep the command in flight for stream updates, polling, queries, or reconciliation." And crucially: "Transport errors, timeouts, and disconnects typically leave outcomes unresolved rather than implying rejection."
- **Fill deduplication by venue identity.** "Use the venue trade or match ID for fills. Include account, instrument, or product identity when the venue does not guarantee global uniqueness"; share fill identity across live dispatch and reconciliation; keep bounded long-lived dedup state across reconnects.
- **Two timestamps, always.** "Use the venue timestamp for `ts_event` when the payload supplies one. Assign `ts_init` from the adapter clock when it receives or constructs the event."
- **Reconnect restores protocol state, not just the socket.** "Reauthenticate private sessions. Restore subscription intent and required instrument context. Reset sequence, snapshot, or gap state when the venue requires a fresh bootstrap." Subscription *intent* is tracked separately from subscription *confirmation*.
- **One conversion boundary.** Keep "raw models separate from Nautilus domain objects. Convert at one auditable boundary."

Reconciliation ([execution reconciliation](https://nautilustrader.io/docs/latest/concepts/reconciliation/), [live](https://nautilustrader.io/docs/latest/concepts/live/)): "At startup, reconciliation aligns cached order and position state with venue reports before trader components start", via exactly three adapter methods — `generate_order_status_reports`, `generate_fill_reports`, `generate_position_status_reports` — and continuous runtime checks governed by `reconciliation_lookback_mins`, `generate_missing_orders`, `open_check_interval_secs`, `open_check_threshold_ms`, `inflight_check_retries`, `max_single_order_queries_per_cycle`, `single_order_query_delay_ms`. Venue-originated positions with no local order become "external orders" attributed to an `EXTERNAL` strategy.

---

### 6. LEAN — the two-object split

Health: repo `QuantConnect/Lean` is the reference implementation; brokerage plugins live in separate repos (`Lean.Brokerages.InteractiveBrokers`, `Lean.Brokerages.TradingTechnologies`, …). Supported brokerages skew US-equity/IB/Oanda/Tradier/TradeStation; **no cTrader** ([brokerages](https://www.quantconnect.com/brokerages)).

`IBrokerage` ([IBrokerage.cs](https://raw.githubusercontent.com/QuantConnect/Lean/master/Common/Interfaces/IBrokerage.cs)) — inherits `IBrokerageCashSynchronizer, IDisposable`:
- Methods: `GetOpenOrders()`, `GetAccountHoldings()`, `GetCashBalance()`, `PlaceOrder(Order)`, `UpdateOrder(Order)`, `CancelOrder(Order)`, `Connect()`, `Disconnect()`, `GetHistory(HistoryRequest)`.
- Properties: `Name`, `IsConnected`, `AccountInstantlyUpdated`, `AccountBaseCurrency`, `ConcurrencyEnabled`.
- Events: `OrderIdChanged`, `OrdersStatusChanged`, `OrderUpdated`, `AccountChanged`, `Message`, `NewBrokerageOrderNotification`, `OptionPositionAssigned`, `OptionNotification`, `DelistingNotification`.

Two details worth copying: **`OrderIdChanged`** (venues reassign ids — model it as an event, not a surprise) and **`NewBrokerageOrderNotification`** (orders can appear that your engine never sent — manual trades, stop-outs; cTrader's `isServerEvent` is the same thing).

Documented brokerage responsibilities are a clean checklist: "Maintain Connection… Setup State (initialize the algorithm portfolio, open orders and cashbook)… Order Operations… Order Events… Account Events (cash deposits/removals)… Brokerage Events… Serve History Requests" ([creating the brokerage](https://www.quantconnect.com/docs/v2/lean-engine/contributions/brokerages/creating-the-brokerage)). Error policy: emit a `BrokerageMessageEvent` for soft failures (network); throw only on hard failures (auth, unsupported operation).

Separately, `BrokerageModel` answers "what will this venue *allow*": `CanSubmitOrder()`, `CanUpdateOrder()`, `CanExecuteOrder()`, `GetFeeModel()`, `GetFillModel()`, `GetSlippageModel()`, `GetSettlementModel()`, `GetBuyingPowerModel()`, plus supported order types, supported security types, default markets, leverage, account type, extended-hours support ([brokerages key concepts](https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/brokerages/key-concepts)). **This is the same idea as ccxt's `has` map, expressed as behaviour instead of data** — and it's what makes LEAN backtests match live.

---

### 7. Honest head-to-head: cTrader-via-OpenApiPy vs MT5-python

| Dimension | cTrader Open API | MetaTrader 5 Python |
|---|---|---|
| Runs on Linux VPS natively | **Yes** — TLS socket, nothing else | **No** — needs terminal under Wine + RPyC bridge, or a ~4 GB VNC container |
| Live price delivery | **Push** (`ProtoOASpotEvent`) | **Poll only** — no callbacks in the API surface |
| Live fill delivery | **Push** (`ProtoOAExecutionEvent`, incl. `isServerEvent` stop-outs) | Poll `positions_get` / `history_deals_get`; fills can be missed between polls |
| Auth model | OAuth2, 30-day access token, non-expiring refresh token, per-account auth | Broker login/password/server, stored in the terminal |
| Order types | MARKET, LIMIT, STOP, STOP_LIMIT, MARKET_RANGE, STOP_LOSS_TAKE_PROFIT | market + 4 pending types via `TRADE_ACTION_PENDING` |
| Amend order / amend position SL-TP | Distinct messages (`AmendOrderReq`, `AmendPositionSLTPReq`) | `TRADE_ACTION_MODIFY` / `TRADE_ACTION_SLTP` |
| Partial close | First-class (`ClosePositionReq{volume}`) | Opposite `TRADE_ACTION_DEAL` with `position` ticket + smaller volume |
| Position model | **Hedging** (many positions per symbol, own ids) | Netting **or** hedging, account-type dependent — a genuine semantic fork |
| Volume units | cents (1/100 unit) | lots |
| Price units | 1/100000 of price (ints) in spots | floats, `digits` from `symbol_info` |
| Account equity | **Not provided** — derive from balance + `GetPositionUnrealizedPnL` | `account_info().equity` provided directly |
| Historical bars | `GetTrendbarsReq`, ~14,000 bars/req, per-period span cap (~2 wks for M1), 5 req/s | `copy_rates_*`, capped by the terminal's "Max. bars in chart" GUI setting |
| Historical ticks | `GetTickDataReq`, **max 1 week/req**, chunked, delta-encoded | `copy_ticks_range`, generous, bounded by broker-supplied history |
| Rate limits | Explicit: 50/s general, 5/s historical, per connection | None documented; bounded by terminal + broker |
| Multi-account | Many accounts on one connection (auth each) | One account per terminal per process |
| Maintenance windows | Documented weekend maintenance + `maintenanceEndTimestamp` | Broker-dependent, undiscoverable programmatically |
| Official Python client health | **Stale**: last commit 2024-08-07, last release 2024-06-26, hard-pinned old deps | **Healthy**: 5.0.6090 on 2026-08-01, but Windows-only wheels |
| Failure domains in the live path | 1 (TLS socket) | 5 (RPyC → Wine → Win-Python → IPC → GUI terminal) |
| App approval needed | **Yes** — Spotware reviews new Open API apps | No |

**Verdict for QMX.**
- **Live trading: cTrader.** Push execution events, explicit rate limits, explicit disconnect/token-invalidation events, and no GUI process on the critical path. The SDK staleness is a *library* problem QMF can absorb; the MT5 Wine stack is an *architecture* problem QMF cannot.
- **Continuous data collection: cTrader for streaming, and cTrader for bar backfill; MT5 is the better bulk *tick*-history source** if you ever need multi-year tick archives, because cTrader caps tick requests at one week per call. Plan: run the cTrader collector as the always-on spot/bar recorder; if deep tick history is needed, do it as an offline, occasional, Windows-or-container job — never on the live trading host.
- **Do not put MT5 on the live path first.** Add it later, behind the same QMF adapter interface, as a second implementation whose only job is proving the interface is genuinely platform-blind.

---

## What QMF should copy / avoid

### The concrete surface `qmf.broker.BrokerAdapter` must expose

Names are suggestions; the *shape* is the point. Everything below is venue-agnostic and must be implementable by both cTrader and MT5.

**A. Identity, capability, and specs**
- `venue_id: str`, `account_id: str`, `account_mode: Literal["demo","live"]`
- `capabilities() -> Capabilities` — a **declarative dict** in ccxt's `has` style, values `SUPPORTED | UNSUPPORTED | EMULATED`. Minimum keys: `market_order, limit_order, stop_order, stop_limit_order, market_range_order, attach_sl_on_entry, attach_tp_on_entry, relative_sl_tp_only, trailing_stop, guaranteed_stop, amend_pending_order, amend_position_protection, partial_close, close_by_opposite, time_in_force_{gtc,gtd,ioc,fok}, client_order_id, position_netting, position_hedging, push_ticks, push_fills, push_account, depth_of_market, historical_bars, historical_ticks, account_equity_native`. Copy ccxt's `EMULATED` sentinel — QMF *will* emulate `close_position` on MT5 and `equity` on cTrader, and callers must be able to see that.
- `limits() -> VenueLimits` — `requests_per_second_general`, `requests_per_second_historical`, `max_bars_per_request`, `max_bar_span_per_period: dict[BarPeriod, timedelta]`, `max_tick_span`, `heartbeat_interval`, `max_symbols_per_subscription`.
- `instrument(symbol) -> Instrument` — `symbol` (QMF-canonical, e.g. `EURUSD.CTRADER`), `venue_symbol_id`, `price_precision`, `pip_size`, `lot_size`, `min_volume`, `max_volume`, `volume_step`, `base_currency`, `quote_currency`, `margin_currency`, `commission_model`, `swap_long/short`, `trading_session_schedule`, `raw`. **Volumes on this interface are always `Decimal` units of base currency; never cents, never lots.**
- Instruments must be invalidatable at runtime (cTrader sends `ProtoOASymbolChangedEvent`).

**B. Orders (commands)**
- `submit_order(OrderRequest) -> OrderAck`
- `amend_order(order_id | client_order_id, changes) -> OrderAck`
- `cancel_order(order_id | client_order_id) -> OrderAck`
- `amend_position_protection(position_id, stop_loss=None, take_profit=None, trailing=None) -> OrderAck`
- `close_position(position_id, volume=None) -> OrderAck`  (`volume=None` ⇒ full close; partial otherwise)
- `OrderRequest` fields: `client_order_id` (QMF-generated, always set), `symbol`, `side`, `order_type`, `volume`, `limit_price?`, `stop_price?`, `time_in_force`, `expire_at?`, `stop_loss?` / `take_profit?` (absolute prices — the adapter converts to relative where the venue demands it), `slippage_points?`, `label?`, `strategy_id`, `reduce_only?`.
- `OrderAck` MUST carry an explicit `outcome: ACCEPTED_BY_VENUE | REJECTED_BY_VENUE | DENIED_LOCALLY | UNKNOWN` — Nautilus's three-tier model plus local denial. **`UNKNOWN` is not an error; it is a state that reconciliation resolves.**

**C. Events (a single ordered async stream)**
`events() -> AsyncIterator[BrokerEvent]`, one stream, discriminated union:
- `OrderAccepted, OrderRejected(reason_code, reason_text), OrderAmended, OrderCancelled, OrderExpired, OrderPartiallyFilled, OrderFilled`
- `Fill{fill_id (venue trade/deal id), order_id, client_order_id, position_id, symbol, side, volume, price, commission, swap, ts_event, ts_init, raw}`
- `PositionOpened, PositionChanged, PositionClosed`
- `AccountStateChanged{balance, equity, margin_used, margin_free, currency, is_derived: bool}`
- `ExternalOrderDetected` / `ServerInitiatedAction{kind: STOP_OUT | LIQUIDATION | MARGIN_CALL}` — for cTrader `isServerEvent`, LEAN `NewBrokerageOrderNotification`, MT5 out-of-band closes
- `ConnectionStateChanged{state: CONNECTING|READY|DEGRADED|RECONNECTING|DISCONNECTED, reason}`
- `SubscriptionStateChanged{symbol, intent, confirmed}`
- `VenueMaintenance{ends_at?}`
- Every event carries **both** `ts_event` (venue clock, UTC ns) and `ts_init` (QMF clock) per Nautilus's rule.

**D. State queries (reconciliation primitives)** — copy Nautilus's exact triple, they are provably sufficient:
- `fetch_order_status_reports(since=None) -> list[OrderStatusReport]`
- `fetch_fill_reports(since=None) -> list[FillReport]`
- `fetch_position_status_reports() -> list[PositionStatusReport]`
- plus `fetch_account_state() -> AccountState` and `fetch_open_orders()`.
`reconcile(lookback: timedelta) -> ReconciliationResult` runs at startup **before** any strategy is allowed to trade, and periodically thereafter.

**E. Market data**
- `subscribe_quotes(symbols) / unsubscribe_quotes(symbols)`
- `subscribe_bars(symbol, period) / unsubscribe_bars(...)`
- `subscribe_depth(symbol)` (capability-gated)
- `request_bars(symbol, period, start, end) -> AsyncIterator[Bar]` — **the adapter owns pagination**, the 14,000-bar cap, the per-period span cap, the `hasMore` loop, and the historical rate bucket. Callers ask for ten years and get ten years.
- `request_ticks(symbol, start, end) -> AsyncIterator[Tick]` — same, with cTrader's 1-week window hidden inside.
- Subscriptions are **declarative intent**: QMF stores what it wants subscribed and the adapter re-establishes it after every reconnect, tracking intent separately from venue confirmation.

**F. Errors** — a QMF hierarchy mirroring ccxt's crucial split:
```
BrokerError
├── VenueRejection            # the venue said no — deterministic, do not blindly retry
│   ├── AuthError / PermissionError
│   ├── InsufficientFunds / MaxExposureReached
│   ├── InvalidOrder (BadVolume, BadStops, BadPrices, ProtectionTooClose, BadExpiration)
│   ├── NotFound (OrderNotFound, PositionNotFound, SymbolNotFound)
│   ├── MarketClosed / TradingDisabled
│   └── NotSupported
└── OperationFailed           # we do not know — retry / reconcile
    ├── TransportError (Timeout, Disconnected, TlsError)
    ├── RateLimited(retry_after)
    ├── VenueUnavailable(maintenance_ends_at)
    └── BadResponse
```
Every error carries `venue_code: str` and `raw`. The classification table from `ProtoOAErrorCode` → QMF error lives in the cTrader adapter and nowhere else.

**G. Lifecycle**: `connect()`, `disconnect()`, `health() -> Health`, plus an internal `RateLimiter` with **separate buckets** for general vs historical traffic, and a **priority lane so order commands never queue behind backfill**.

### Venue quirks that must NEVER leak past this interface

1. **Unit scaling.** cTrader cents/1e5-prices/`moneyDigits`, MT5 lots. QMF sees `Decimal` units and `Decimal` prices. Ever.
2. **`ctidTraderAccountId` on every message**, symbol *ids* vs symbol *names*, `payloadType` integers, protobuf class names.
3. **Absolute-vs-relative SL/TP.** cTrader forbids absolute SL/TP on MARKET orders and needs `relativeStopLoss` in 1/100000 units. The interface takes absolute prices; the adapter converts.
4. **Delta-encoded bars and ticks.** `low + deltaOpen`, `utcTimestampInMinutes`, tick timestamps as inter-arrival deltas. QMF sees plain OHLCV with UTC-nanosecond timestamps.
5. **Pagination and `hasMore`.** 14,000-bar caps, 1-week tick windows, per-period span limits, and the 5 req/s historical bucket are the adapter's problem.
6. **Two-stage auth and per-account auth.** Application auth, account auth, `ProtoOAAccountDisconnectEvent`, `ProtoOAAccountsTokenInvalidatedEvent`, token refresh invalidating live sessions — all invisible above `ConnectionStateChanged`.
7. **Heartbeats and framing.** No caller ever knows a heartbeat exists.
8. **Demo/live endpoint separation.** Two hosts and two connections is a cTrader fact; QMF sees `account_mode`.
9. **Netting vs hedging.** Pick hedging semantics as QMF's canonical model (cTrader is hedging; it is strictly more expressive) and have the MT5 netting adapter *emulate* position ids, declaring `position_netting: EMULATED`.
10. **Close-by-opposite-order.** MT5's "close = opposite DEAL with position ticket". QMF exposes `close_position`.
11. **Equity absence.** cTrader has no equity field. QMF's `AccountState.equity` is always populated, with `is_derived=True` when computed. Never expose "sometimes null".
12. **Missing bars.** "Trend bars are only created if there are incoming ticks" — the adapter must mark gaps as *no-data*, distinct from *not-yet-fetched* and from *error*.
13. **Terminal-shaped constraints.** MT5's "Max. bars in chart", one-account-per-process, Wine/RPyC topology — surfaced only through `limits()` and `health()`.
14. **Broker-dependent fill modes.** MT5 `type_filling` FOK/IOC/RETURN negotiation belongs in the adapter, keyed off `symbol_info`.

### Copy

- **ccxt's `has` map with an `EMULATED` value**, and **`raw`/`info` on every unified object.** These two together are what make a unified API honest.
- **ccxt's error hierarchy split** between "venue rejected" and "operation failed/unknown".
- **ccxt Pro's `subscribe*` ≡ `request*` symmetry** — same names, same payload shapes, different delivery.
- **Nautilus's three-tier order outcome** and its rule that timeouts/disconnects mean *unknown*, not *rejected*.
- **Nautilus's `ts_event` / `ts_init` dual timestamps** on every single event.
- **Nautilus's reconciliation triple** (`order_status` / `fill` / `position_status` reports) as the adapter's mandatory read side, run before strategies start.
- **Nautilus's "convert at one auditable boundary"** — a single `_parse.py` per adapter, and nothing venue-shaped past it.
- **LEAN's two-object split**: `BrokerAdapter` (transport + commands) vs `VenueModel` (allowed order types, fees, leverage, min/max, session hours) — so QMF backtests can be constrained by the same model that constrains live.
- **LEAN's `OrderIdChanged` and `NewBrokerageOrderNotification`** as first-class events.
- **LEAN's soft-failure-is-an-event, hard-failure-is-an-exception** policy.
- **cTrader's own `retryAfter`** field: honour it, which means regenerating protobuf messages from the current `.proto` rather than trusting the SDK's 2024 bundle.

### Avoid

- **Do not build on `ctrader-open-api` as-is.** Two years stale, `==` pins on Twisted/protobuf/requests that will fight the rest of QMF, generated messages missing current protocol fields, class-level mutable state in `TcpProtocol`, and pending requests silently cleared on disconnect. Either (a) vendor the current `.proto` files, run `protoc` yourself in CI, and write ~400 lines of asyncio transport (length-prefixed framing, heartbeat, auth, correlation, rate buckets) — my recommendation — or (b) fork it and fix the four defects above. Do not use `Protobuf.get("NewOrderReq", ...)` string lookup in QMF code; LLM agents need typed builders.
- **Avoid Twisted entirely if QMF is asyncio.** Bridging reactors is a permanent tax.
- **Do not run one shared 5-msg/s outbound queue** for orders and backfill. Separate buckets, order commands first.
- **Do not treat a request timeout as a rejection.** This is the single most expensive mistake available in this domain.
- **Do not expose venue enums** (`ProtoOAOrderType`, `ENUM_ORDER_TYPE_FILLING`) in QMF's public surface — the LLM-authored-strategy roadmap makes a stable, small, typed vocabulary non-negotiable.
- **Do not make MT5 the reference implementation.** Designing the interface around a polling, Windows-bound, terminal-hosted API will produce an interface that cannot express push semantics.
- **Do not put the MT5/Wine stack on the live trading VPS** in phase 1.
- **Do not refresh the cTrader access token casually** — refreshing invalidates active account sessions (`ProtoOAAccountsTokenInvalidatedEvent` reason includes "token was refreshed"). Refresh must be a deliberate, re-auth-everything operation.
- **Do not skip startup reconciliation.** Positions can be opened and closed by the venue (stop-out) while QMF is down.
- **Do not model equity as optional.**

---

## Open questions

1. **Which broker?** cTrader Open API access is account-and-broker dependent in practice; I could not verify on a Spotware primary page that every cTrader broker enables it. Operator decision: pick 1–2 candidate brokers, confirm Open API works on both a demo and a live account, and confirm their symbol set, minimum volumes, and swap/commission model.
2. **App approval lead time.** "Spotware carefully evaluates new Open API services" and approval precedes coding. How long does approval take, and can development proceed against demo accounts while pending? Needs a real submission to find out — start this early, it is the longest-pole external dependency.
3. **Build or fork the cTrader client?** My recommendation is a ~400-line in-house asyncio client over vendored protobufs. This is an operator cost/risk decision: in-house means QMF owns the wire; forking means inheriting Twisted.
4. **The undocumented per-period bar-span table.** Only "14,000 bars" and "~2 weeks for M1" are known, from a forum post. QMF needs an empirical probe that derives the real table per period per broker and caches it — should that be a one-off script or a self-healing runtime behaviour?
5. **Is one connection enough?** Docs recommend at most two (demo + live). If QMF later runs multiple strategies at high message rates against one account, the 50 req/s *per connection* ceiling is shared. Does QMX need Spotware's "dedicated proxy" offer ([Open API 2.0 announcement](https://www.spotware.com/news/ctrader-open-api-2-0-released-faster-apps-with-more-features/))? Needs a load estimate.
6. **Equity refresh cadence.** cTrader's docs suggest 2–3 s for `GetPositionUnrealizedPnL`. Is that fast enough for QMF's risk kill-switch, or must QMF compute equity locally from spot ticks + position VWAP + tick value? Local computation is faster but must be reconciled against the venue's number to catch drift.
7. **Do we ever need MT5 at all?** Concretely: is there an instrument, broker, or prop-firm account QMX needs that cTrader cannot reach? If no, MT5 support is a costly hedge. If yes (many prop firms are MT5-only), the Wine/RPyC operational burden must be budgeted — and probably isolated on its own VPS.
8. **Tick-history strategy.** cTrader's 1-week-per-request tick cap makes multi-year tick archives slow. Is a paid tick-data vendor (Dukascopy, TrueFX, Tardis for crypto) cheaper than engineering a long backfill crawler? Operator cost decision.
9. **Canonical symbol naming.** ccxt uses `BTC/USDT`, Nautilus uses `BTCUSDT-PERP.BINANCE`. QMF needs a scheme that survives cTrader symbol *ids*, MT5 broker-suffixed names (`EURUSD.m`, `EURUSDmicro`), and crypto pairs. Decide before the first adapter is written — this is very expensive to change later.
10. **Clock discipline.** cTrader timestamps are ms (and *minutes* for bars); MT5 is UTC seconds with a local-timezone trap; QMF should standardise on UTC nanoseconds. Does the VPS run NTP-disciplined time, and does QMF record clock skew alongside `ts_init`?
11. **Crypto phase interaction.** If crypto eventually arrives via ccxt, does QMF wrap ccxt behind the same `BrokerAdapter` (adapter-over-adapter), or does ccxt become a peer? Wrapping is cleaner for strategy code but doubles the translation layers.
12. **Wine/MT5 version drift.** `MetaTrader5-Docker` had to move to Wine 10 because "Wine 9 is not supported by MT5". If MT5 is adopted, who owns pinning and testing that pairing, and what is the rollback plan when a terminal auto-update breaks the container?
