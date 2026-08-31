# Code inventory — `qmf-venue` (the venue seam + cTrader translation)

- **Source of truth:** worktree `QMX-worktrees/node-inventory`, branch `integration@ef9bb25`
  (commit "FIX-ROUND-1: seal the final report with the green CI verdicts").
- **Package root:** `packages/qmf-venue/`. Imports as `qmf.venue` (PEP-420 namespace).
- **Dependency direction (load-bearing):** imports only `qmf-core`; **nothing imports
  `qmf-venue`** — the default-deny edge (L30/DEC-0120). `packages/qmf-venue/README.md:3`,
  `packages/qmf-venue/src/qmf/venue/__init__.py:4`.
- **Only third-party dependency:** `protobuf==7.36.0` — declared HERE ONLY, for the in-house
  proto compilation; the Spotware OpenApiPy SDK is reference-only and its pinned Twisted
  reactor is *rejected*. `packages/qmf-venue/pyproject.toml:9-18`.
- **README is stale:** says "Scaffold (Story 1.1)… Public contracts arrive in later stories"
  (`packages/qmf-venue/README.md:10-13`) but the package is **~9,180 src LOC** across Stories
  8.1–8.8 (see `src/qmf/venue/__init__.py:7-141` for the per-story map). Trust the code, not
  the README.

## Size / test counts

| Module | LOC | Role |
|---|---|---|
| `src/qmf/venue/commands.py` | 1588 | CT-19 five commands, four-outcome resolver, compound, id-binding |
| `src/qmf/venue/events.py` | 1559 | CT-20 record-before-interpret, order-state fold, reconciliation |
| `src/qmf/venue/ctrader.py` | 1084 | cTrader adapter #1: decoders, pacer, topology, tokens, duties, recovery |
| `src/qmf/venue/capabilities.py` | 986 | CT-18 two-artifact capability declaration + discovery + error map |
| `src/qmf/venue/blocking.py` | 914 | CT-19 UNKNOWN gate, resolve_unknown, standing intents, throttle order |
| `src/qmf/venue/probe.py` | 860 | CT-18 first-connection verify-or-refuse probe (five checks) |
| `src/qmf/venue/connection.py` | 732 | CT-21 connection manager, secret lifecycle, sink wiring |
| `src/qmf/venue/proto.py` | 491 | Story 8.2 in-house proto compile + decode + pin-change governance |
| `src/qmf/venue/observation.py` | 474 | CT-18 measured-fact profile, three-valued verdict, evidence gate |
| `src/qmf/venue/__init__.py` | 441 | public surface (per-story docstring is the spine map) |
| `src/qmf/venue/_bench.py` | 50 | placeholder benchmark harness (deliberate stub) |
| **src total** | **9179** | |

- **Tests:** 407 test functions across 10 files (all `def test_*`, no `class Test*`):
  `tests/test_commands_ct19.py` 84, `tests/test_capabilities_ct18.py` 62, `tests/test_probe_ct18.py` 59,
  `tests/test_events_ct20.py` 58, `tests/test_ctrader_dec0135.py` 46, `tests/test_proto_tag91.py` 32,
  `tests/test_connection_ct21.py` 32, `tests/test_blocking_ct19.py` 30, `tests/test_venue_examples.py` 2,
  `tests/test_venue.py` 2.
- **Examples (2, reference-only, non-network):** `examples/account_binding_usage.py` (120 LOC, CT-21
  bindings), `examples/observation_events_usage.py` (76 LOC, CT-20 cardinality law).
- **FAILURES.md:** 6 typed-refusal register entries FR-1..FR-6 covering invalid-input,
  unsupported-capability, unavailable-dependency, policy-rejection, transient-venue-failure (UNKNOWN),
  storage-failure. `packages/qmf-venue/FAILURES.md:9-124`.

---

## Capability-by-capability inventory

Status legend: **exists-as-is** = the contract/logic is fully present and pure (deterministic,
no live wire); **exists-needs-live-adapter** = the shape/law is present but needs the node to
supply live transport, a scheduler, or a caller-side comparison; **does-not-exist** = no code.

| Capability | Where (path:line) | Status | What the node must add |
|---|---|---|---|
| **CT-18 capability DECLARATION (two-artifact)** — static, credential-free, adapter-version-scoped, carries protocol-artifact identity + error map + per-field marking + identity-bearing fingerprint | `capabilities.py:587` `CapabilityDeclaration`; roster of **23** field names `capabilities.py:130-166`; `FieldMarking` static/measured-at-connection `capabilities.py:91-102`; `fingerprint()` `capabilities.py:769` | exists-as-is | Compose the declaration from data: `CTraderAdapter.static_capability_facts()` returns only **4 of 23** fields (`ctrader.py:1048-1084` — RATE_LIMITS, SPAN_CAPS_AND_PAGING, TOKEN_LIFECYCLE_CLASS, SERVER_CLOCK_AVAILABILITY=False). Node/composition-root must supply the other 19 field markings + the pinned `ErrorMap` rows. |
| **CT-18 verify-or-refuse PROBE** — first-connection suite, throwaway transport, records profile + findings note | `probe.py:359` `CapabilityProbe`; `.run()` `probe.py:470`; five checks `probe.py:538,583,625,677,722` (spot-timestamp-unit, daily-boundary, bar-basis, pip-formula, money-exponent); `ProbeCheck` `observation.py:67-78` | exists-needs-live-adapter | Probe drives an injected `ProbeTransport` **Protocol** (`probe.py:224-266`) — the *only* Protocol in the package. **No concrete transport ships**; the node must implement `ProbeTransport` against the real cTrader demo host (proto tag pinned; `try_create` refuses a tag mismatch `probe.py:448`). Probe exposes **no submit path** (never places an order, `probe.py:366-368`). |
| **CT-18 fixed-order gate + evidence gate** — declaration present at construction; profile must exist before first command / evidence-bearing decode | `CapabilityDiscovery` `capabilities.py:784`; `.require_ready_for_command()` `capabilities.py:862`; `.require_evidence()` `capabilities.py:879`; three-valued verdict `observation.py:81-93` (VERIFIED/UNVERIFIED/REFUSED) | exists-as-is | Node reads these gates before dispatch. measured-before-profile → `unavailable dependency`; measured-but-unverified in evidence work → `policy rejection`; undeclared/unsupported-scope → `unsupported capability` (never widened). |
| **CT-18 error map fail-closed default** — `(venue code, context) → (category, retryability, after-condition, outcome)`; unmapped ⇒ transient-venue-failure, retryable=no, outcome=UNKNOWN, +alarm | `ErrorMap.resolve()` `capabilities.py:451-499`; `SubmissionOutcomeClass` `capabilities.py:118-127`; rows validated at `ErrorMapRow.try_create` `capabilities.py:288` | exists-as-is | Node injects the pinned rows. Only a declared row yields `rejected-by-venue`; every other code (incl. every unmapped one) resolves UNKNOWN. |
| **CT-19 the five commands typed on core nouns + required scope** — `place_order, cancel_order, close_position, close_all, amend_protection`; no free-form payload; fractional/partial close = unsupported-capability | `CommandKind` `commands.py:126-140`; per-kind factories `Command.place_order/cancel_order/close_position/close_all/amend_protection` `commands.py:701,732,764,794,875`; close carries required typed `CloseScope` `commands.py:822`, scopes `capabilities.py:105-115` (account / account-binding / instrument-within-binding); partial refusal `commands.py:764-838` | exists-as-is | Node builds Commands and picks a declared close scope. amend_protection is stop-side risk-non-increasing only (`ProtectionAmendment` `commands.py:506`, `ProtectionSide` `commands.py:171-181`). "Kinds addable, never redefined; the fifth minted through **AD-27's own explicit-later-mint clause**" `commands.py:5-6,131`. |
| **CT-19 outcome model** accepted \| rejected \| denied-locally \| UNKNOWN | `SubmissionOutcome` `commands.py:183-201`; `FOUR_OUTCOME_LAW` (the 4, PARTIALLY_EXECUTED excluded) `commands.py:204-212`; `is_success` = accepted-only `commands.py:214-222`; producers `CommandOutcomeResolver.accepted/denied_locally/venue_error/transport_unknown` `commands.py:1070,1085,1115,1153` | exists-as-is | The resolver **classifies a venue response the caller already holds** — it does not talk to the venue. Node decides which producer to call. `denied-locally` = outcome never refusal; `UNKNOWN` = state never error; timeout never routed to `venue_error` (never read as rejection) `commands.py:1121-1127`. `UnknownTrigger` = timeout/transport-error/disconnect `commands.py:224-238`. |
| **CT-19 UNKNOWN command-stream block + resolve_unknown** | `blocking.py:464` `UnknownGate`; `.record_unknown` `blocking.py:567`; `.admit` `blocking.py:625`; `.resolve_unknown(command_fp1, resolution, *, receive_instant)` `blocking.py:767`; `ResolveResolution` `blocking.py:275-286` (observed-accepted \| observed-absent \| operator-attested) | exists-as-is | **resolve_unknown MECHANISM lives in `qmf-venue`** (UnknownGate), but it is **"an explicit typed call by the application"** — the node originates the resolution (per AD-27 / the app clears the block: `ctrader.py:793` "the application later clears the block through an explicit resolve_unknown call"; `InFlightResolution` `ctrader.py:787-799`). Block clears **on the recorded resolution, never on a reconciliation verdict alone**. Refused risk-reducing acts preserved as `StandingProtectionIntent` (`blocking.py:372`, held/journaled before dispatch `blocking.py:698`), re-decided against `reconciled` only `blocking.py:829`. suspend-new is local/instant, no venue round-trip `blocking.py:744`. Risk-reducing kinds dispatch ahead of place_order on a shared throttle `blocking.py:164` `order_for_shared_throttle`. |
| **CT-20 venue events (record-before-interpret)** — inbound event stored verbatim w/ receive wall time + boot-scoped monotonic stamp; journaled before any state eval; multi-room (raw-archive/journal/registry-room) atomic-or-recovery | `InboundVenueEvent` `events.py:476`; `EventRecorder.record/record_multi_room/recover` `events.py:1157,1172,1241`; `MultiRoomWrite` `events.py:999`, `WriteRoom` `events.py:173-179`, `TransactionBoundary` `events.py:166-171`; `PartialWriteRecovery` `events.py:1072` | exists-as-is | Node injects the three sink rooms. A partial multi-room write = storage-failure refusal that blocks the command pipe (sensing pipe unaffected) and is journaled on recovery. |
| **CT-20 journal event TYPES / "seven incl. order/fill/partial fill/position/balance"** | `ObservationKind` = **6** members `events.py:127-142` (submission-acknowledgement, fill, cancel-acknowledgement, expiry, close-by-venue, out-of-sequence[derived]); command journal `command.<kind>.<outcome>` `commands.py:994`; observation journal `observation.<kind>` `events.py:767` | **partial / gap** | The code models the **order-lifecycle five** (+ out-of-sequence annotation) as first-class journaled kinds. **Partial fill** is not a separate observation kind — it is the `PARTIALLY_FILLED` *fold* order state (`events.py:158`). **Position and balance are NOT first-class venue-event/journal kinds** — they appear only as (a) money-decode messages `ProtoOAPosition/…` `ctrader.py:144-155` and (b) reconciliation read-back evidence keys `events.py:1335,1367`. If the CT-20 spec calls for seven journaled types including position/balance streams, the node/adapter must add position- and balance-event ingestion (or the architecture must reconcile the count). |
| **CT-20 order-state machine (UNKNOWN-is-a-state)** — read-time fold, never a stored field | `OrderState` `events.py:144-165` (prefix: client-submitted, venue-accepted, venue-rejected, **UNKNOWN**; terminal: partially-filled, filled, cancelled, expired, closed-by-venue); `fold_order_state` `events.py:878`; terminal set `events.py:215-224`; legal-prior table `events.py:238-280`; `is_legal_transition` `events.py:811`; out-of-sequence forces owning command UNKNOWN `detect_out_of_sequence` `events.py:826`, `OutOfSequenceEdge` `events.py:429` | exists-as-is | Terminal state decided **only** by fills + venue lifecycle events, never from a command outcome or absence. Command outcome and order state are separate streams. Adapters never synthesize an observation. |
| **CT-20 reconciliation triple + verdict vocabulary** reconciled \| drift \| unknown \| out-of-lookback | `ReconciliationVerdict` `events.py:181-194`; `ReconciliationReadback` `events.py:1304` (evidence mapping = "orders/fills/positions/balance" `events.py:1335,1367`); `.verdict(expected, observed)` `events.py:1391`; `Reconciliation` gating `events.py:1264`; `covers_declared_lookback` `events.py:1387`; subject-terminal `resolve_subject_terminal` `events.py:1452`, `SubjectResolution` `events.py:196-213` | exists-needs-live-adapter | Verdict vocabulary + gating fully present. But `.verdict()` **takes caller-supplied `expected_state` / `observed_state`** — the node must actually **read the venue back and fold the orders/fills/positions/balance triple into an observed state**; the package only carries the evidence mapping and computes the verdict. Lookback is **do-not-default** (`declared_lookback` mandatory, value is node's `events.py:1307-1308,1349`). `out-of-lookback` never read as "position closed". Reconciliation gates the command pipe only, never sensing. |
| **CT-21 secret: SecretRef / SecretStore port** | ports imported from `qmf-core` (`SecretStore`, `SecretRef`, `SecretValue`) `connection.py:51-72`; `AccountBinding.secret_ref` occurrence/display-only, excluded from fp1 `connection.py:199-215,277-291`; probe holds `SecretRef` never value `probe.py:375,422` | exists-as-is | Node/composition-root injects a real `SecretStore` (read + atomic_replace). Ports live in `qmf-core`, not here. Credential never renders (no getter/log/health field carries plaintext `connection.py:338-359`). |
| **CT-21 secret lifecycle** — single in-memory holder; open/close/rotate store-before-discard | `ConnectionManager` `connection.py:361`; `.open_session` `connection.py:527`; `.close_session` `connection.py:570`; `.rotate_secret` (atomic_replace before discard; failure keeps old + blocks command pipe) `connection.py:588`; `.holds_secret` boolean-only `connection.py:564`; `BlockCause` STORAGE_FAILURE/ROTATION_STORE_FAILURE `connection.py:312-322` | exists-as-is | Node injects the store + three sinks. Rotation-store failure blocks command pipe until successful store or operator re-provision; sensing pipe unaffected. |
| **CT-21 session state machine / heartbeat / refresh / reconnect as app-schedulable** | `SessionDuty` `ctrader.py:742-755` (heartbeat, token-refresh, reconnect, gap-replay, verification-monitor); `SESSION_DUTIES` `ctrader.py:778-784`; `SchedulableDuty.venue_bound_seconds` (only heartbeat=10s `ctrader.py:757-775`); `SessionRecovery.on_disconnect` (every in-flight → UNKNOWN, **never resubmits**) `ctrader.py:802-851`; command/sensing pipe state `connection.py:305-337` | exists-needs-live-adapter | **There is no connection/session state-machine enum** (no CONNECTED/RECONNECTING/DISCONNECTED states). "Session state machine" here = the **duties are declared, the app runs them**: "The adapter *defines* the work; the application *runs* it" `ctrader.py:745`. The node must build the scheduler that fires heartbeats (≤10s), refreshes the ~30-day token, reconnects, replays gaps, and runs verification monitors. `on_disconnect` is a pure decision fn (returns UNKNOWN resolutions), **not** a socket handler. |
| **rate-limit token buckets** — 50/s non-historical + 5/s historical per connection | `RatePacer` (sliding one-second window over injected `MonotonicReading`) `ctrader.py:507-590`; ceilings `NON_HISTORICAL_RATE_LIMIT_PER_SECOND=50`, `HISTORICAL_RATE_LIMIT_PER_SECOND=5` `ctrader.py:131-132`; `RequestClass` `ctrader.py:487`; `.admit` `ctrader.py:541`; historical one-week span cap `tick_span_within_cap` (`HISTORICAL_TICK_SPAN_CAP_MS`) `ctrader.py:591,139` | exists-as-is | Node instantiates one pacer per connection (`CTraderAdapter.new_pacer()` `ctrader.py:1043`) and supplies the monotonic stamps + drives the below-ceiling cadence (a node value, do-not-default `ctrader.py:130,516`). At/above ceiling = transient-venue-failure. |
| **command-stream ownership + gapless per-writer sequence** — `(VenueId, account)` is the WriterId ownership unit + gapless sequence | `venue_command_stream` `connection.py:152`; `venue_writer_id` at `(machine, adapter role, VenueId, account, boot_epoch_id)` `connection.py:162`; `ConnectionManager.next_command_key` mints strictly-increasing per-writer `OrderingKey` via `WriterSequencer` `connection.py:511,417`; command carries caller `ordering_ordinal` `commands.py:685-695` | exists-as-is | **"the node owns the sequencer and QMF carries the field"** `commands.py:692`. Node owns the sequencer; each `(VenueId, account)` is one writer; restart visible via new boot_epoch_id without changing writer identity. |
| **clientMsgId correlation** | `CommandIdBinding` `(venue_client_id, command fp1, account, session epoch)` durable before submission `commands.py:1291-1315`; `CommandIdBindingRegistry.bind_before_submission` (idempotent re-present, alarmed collision) `commands.py:1317-1426`; injective-total check `command_id_mapping_is_injective_total` `commands.py:1249`; `InboundVenueEvent.correlation_id` (occurrence/display-only, excluded from fp1) `events.py:505,616,655` | exists-needs-live-adapter | The **binding discipline** exists (persist a durable id-binding before submission when the venue client-id mapping is not injective-and-total). But the **wire-level request/response clientMsgId matching** (generate a clientMsgId on an outbound ProtoOA request, match the inbound response) **does not exist** — `correlation_id` is only stored verbatim as provenance. Node's live adapter must generate + match clientMsgId on the wire. |
| **three numeric scale systems: (1) 1/100000 prices** | `decode_market_data_price` (uint64, exact scale-5 integer, never a /100000 float) `ctrader.py:339-362`; `MARKET_DATA_WIRE_SCALE_EXPONENT=5` `ctrader.py:127` | exists-as-is | Decoded here. Node calls with wire value + Instrument. |
| **three numeric scale systems: (2) moneyDigits exponent** | `decode_money` (per-account exponent on the **nine** money-bearing messages; **absent exponent refuses**, never defaults to 2) `ctrader.py:438-486`; `MONEY_BEARING_MESSAGES` (9) `ctrader.py:144-159`; execution prices via `decode_execution_price` raw-double crossing at instrument digits `ctrader.py:365-437` | exists-as-is | Decoded here. Node supplies the per-account `moneyDigits` (from probe/profile) + declared rounding mode. |
| **three numeric scale systems: (3) cents volumes** | *(none)* — grep for volume/cents/lot across `src/` returns **no volume decoder** | **does-not-exist** | The cTrader volume-in-cents (1/100 lot) scale is **not decoded anywhere**. Node/adapter must add a volume decoder (wire cents ↔ `qmf-core Quantity`). Only price + money scales are implemented. |
| **equity derivation (balance + unrealized)** | `EQUITY_NATIVENESS` is a capability **field NAME only** `capabilities.py:151`; `ProtoOAGetPositionUnrealizedPnLRes` is a money-bearing **message name only** `ctrader.py:154` | **does-not-exist** | **No equity-derivation function exists.** No `balance`, `unrealized`, or `equity` computation anywhere in `src/` (grep confirms). Node must derive equity = balance + unrealized PnL from decoded money messages. |
| **the cTrader ADAPTER itself** | `CTraderAdapter` (frozen-dataclass **facade**) `ctrader.py:981`; binds `CTraderBrokerConfiguration` `ctrader.py:853` + `SessionTopology` + `TokenLifecycle`; exposes `session_duties`, `recovery`, `new_pacer`, `static_capability_facts` `ctrader.py:1033-1084` | **exists-needs-live-adapter (contracts + decoders only; NO wire client)** | See "Adapter reality check" below — **there is no protobuf transport, no socket, no fake/in-memory venue, no submit path.** Node must build the entire live wire client. |
| **proto decode (in-house)** | `compile_descriptor_set` (isolated descriptor pool from a serialized FileDescriptorSet — *data*) `proto.py:329`; `CompiledProto.decode` (bytes → Message) `proto.py:276`; `descriptor_set_digest` `proto.py:162`; pin governance `assess_tag_change` `proto.py:412`, `ProtoArtifact` `proto.py:177` | exists-needs-live-adapter | Real protobuf **decode of a single message from bytes the caller already received**. **No descriptor-set/.proto file ships in the package** (find confirms none) — the node/composition-root supplies the compiled Spotware `openapi-proto-messages` descriptor bytes. **No message ENCODE / request-builder** (e.g. place_order → ProtoOANewOrderReq) exists. |
| **adapter injection (protocols) + sinks** | only Protocol in package = `ProbeTransport` `probe.py:224`; sinks injected into `ConnectionManager`: `ObservationSink`, `JournalSink`, `RecordSink` `connection.py:391-405`, `SecretStore` `connection.py:391`; `CommandIdBindingRegistry` takes a `RecordSink` `commands.py:1339` | exists-needs-live-adapter | **There is NO `VenuePort` / `OrderPort` / `VenueAdapter` Protocol** and **no submit/dispatch/send method** in `src/` (grep confirms). The "venue-neutral port" is realized as concrete typed contracts, not an injectable interface. Expected sinks: `ObservationSink` (command + sensing), `JournalSink` (gapless per-writer), `RecordSink` (registry records + id-bindings), `SecretStore`. Node wires all four at the composition root + supplies the live transport that fills `InboundVenueEvent`s and calls the `CommandOutcomeResolver`. |
| **demo/live host distinction** | `VenueEnvironment` DEMO/LIVE `ctrader.py:624-629`; `ConnectionEndpoint` (opaque host_ref, no broker named) `ctrader.py:631-643`; `SessionTopology.endpoint_for` `ctrader.py:695` | exists-as-is (declaration only) | Demo and live are separate hosts. `World` live/replay/simulated on the binding `connection.py:199-215`. Node opens the actual connections; topology only names endpoints. |
| **paired-demo / second-connection** | `SessionTopology` requires **exactly one demo + one live** endpoint; `required_connection_count = 2` (ClassVar) `ctrader.py:645-706` | exists-as-is (declaration only) | "Demo and live are separate hosts requiring **two simultaneous connections**." The requirement is declared; **no code opens or holds two connections** — node must run both simultaneously. |
| **depth / L2 / order book** | *(none)* — grep depth/L2/orderbook/ladder/spread returns nothing; "bid/ask" appears only as the tick-history quote-side selector for bar-basis reconciliation `probe.py:172-192,252` | **does-not-exist** | No market-depth / Level-2 code. Market-data surface is spot/tick/trendbar samples in the probe only (`SpotSample`, `Tick`, `Trendbar`, `TickHistorySample`, `SymbolMetadataRecord`, `AccountMoneyRecord` `probe.py:139-223`). If the node needs L2/depth, it is greenfield. |

---

## Adapter reality check (the load-bearing question)

**Verdict: contracts + decoders + a thin facade — NOT a live client.** grep across `src/` for
`twisted|websocket|ssl|socket|asyncio|reactor|tcp|tls|connect(|sendall|recv|aiohttp|requests|urllib`
returns **only**:
- `ProtoOA*` as **string message names** in `MONEY_BEARING_MESSAGES` `ctrader.py:146-154`;
- `twisted` in a **comment** stating the reactor is *rejected* `proto.py:10`, `pyproject.toml:13-16`;
- `on_disconnect` = a pure recovery-decision method `ctrader.py:814` (no socket).

What exists:
- **Decoders** (timestamp/market-price/execution-price/money) — pure functions `ctrader.py:289-486`.
- **Self-pacer** `RatePacer` — pure, injected monotonic stamps `ctrader.py:507`.
- **Declared session topology / token lifecycle / schedulable duties / session recovery** — data +
  decision functions `ctrader.py:624-851`.
- **`CTraderAdapter`** — a frozen-dataclass facade assembling the above `ctrader.py:981`.
- **`CompiledProto.decode`** — real single-message protobuf decode from caller-supplied bytes `proto.py:276`.

What is **absent** (node must build):
- No socket / TLS / framing / length-prefix / message loop.
- No outbound ProtoOA **request encoding** (only decode).
- No **submit/dispatch** path that transmits a Command to the venue (grep: none).
- No **fake / in-memory venue** — the sole seam is the `ProbeTransport` Protocol (credential-free
  demo probe), with **no concrete implementation in the package** (tests inject their own).
- No wire-level **clientMsgId** generate/match, no heartbeat pinger, no reconnect loop, no token-refresh
  executor — those are declared `SESSION_DUTIES`, not implemented.
- No **volume/cents** decoder, no **equity** derivation, no **position/balance** event ingestion,
  no **depth/L2**.

## Cross-cutting spine facts (quote-exact, load-bearing)

- "the caller's ordering ordinal is a non-negative integer; **the node owns the sequencer and QMF
  carries the field**" `commands.py:691-693`.
- resolve_unknown: "Unblocking is **an explicit typed call by the application**… the block clears **on
  that resolution** — **never on a reconciliation verdict alone**" `blocking.py:772-778`.
- reconciliation lookback: "its existence and declaration are QMF's and **its value is node's**, so it
  is a mandatory construction argument, never defaulted" `events.py:1307-1308`.
- submission deadline: "a declared, application-injected parameter under do-not-default (its value is
  never QMF's…)" `commands.py:1167`, `commands.py:47`.
- money decode absent exponent: "the moneyDigits exponent is absent; this message's money decode is
  refused, **never defaulted to 2**" `ctrader.py:474-478`.
- fifth command: "minted through **AD-27's own explicit-later-mint clause**" `commands.py:6`.
- session recovery: "Session recovery… **never resubmits a command**" (`resubmits_command = False`
  ClassVar) `ctrader.py:808-810`.
- server clock: "recording a local receive instant is mandatory; **the Open API exposes no server
  clock**" `ctrader.py:333-335`, and `SERVER_CLOCK_AVAILABILITY: False` `ctrader.py:1083`.
- pin integrity: a descriptor-set change under an unchanged tag = "a silent update the pin exists to
  prevent — re-verify and re-mint, and alarm" `proto.py:441-460`.

## Node-owned / app-schedulable / do-not-default markers (grep census, 33 hits in src)

Every duty/cadence/value the package deliberately leaves to the node:
- Schedulable duties driven by the app: `ctrader.py:31-32,743-745,762-764,776-784,1033-1034`,
  `__init__.py:134-135`.
- Pacing/backoff cadence = node value (do-not-default): `ctrader.py:130,135,516`.
- resolve_unknown originated by the application: `blocking.py:772`, `ctrader.py:793`.
- Reconciliation lookback value = node's (do-not-default): `events.py:38,52,1307-1308,1334,1349`.
- Submission deadline injected by app (do-not-default): `commands.py:47,978,1167,1194`.
- Sequencer owned by node: `commands.py:692`.
- Explicit-later-mint (new command kinds / partial close): `commands.py:6,18,131`.
- `_bench.py` workload is "a deliberate placeholder" `_bench.py:7`.
- "Public contracts arrive in later stories" is **stale README text** `__init__.py:14` refers to the
  probe's Story-8.1 isolation, not missing contracts.

## Bottom line for the trading node

`qmf-venue` delivers the **complete venue-neutral law and the pure cTrader translation layer**
(capability discovery, the five commands, the four-outcome resolver, record-before-interpret events,
the order-state fold, reconciliation verdicts, the UNKNOWN gate + resolve_unknown, secret/session
lifecycle, rate pacing, proto decode, pin governance) — all deterministic, injected-clock, no-float-on-
money, value-or-refusal. It delivers **none of the live wire**: no socket/protobuf transport, no
request encoding, no submit/dispatch path, no scheduler, no fake venue, and it is **missing three
concrete pieces the node needs**: a **cents/volume decoder**, an **equity derivation** (balance +
unrealized), and **position/balance event ingestion** (the CT-20 "seven journaled types" gap). The
node is the composition root that (1) implements `ProbeTransport` + a live cTrader transport, (2) wires
the four `qmf-core` sinks + `SecretStore`, (3) supplies the 23-field capability declaration data + error
map, (4) owns the sequencer, the scheduler for the five session duties, and the do-not-default values
(deadlines, lookback, cadences), and (5) originates resolve_unknown and drives the reconciliation
read-back that folds orders/fills/positions/balance into an observed state.
