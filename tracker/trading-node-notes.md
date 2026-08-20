# Trading-node notes — running cross-session ledger

Standing operator instruction (2026-08-20, venue sitting): anything discussed in ANY session that concerns the trading node gets noted here, so node-era sessions inherit it without the operator repeating himself. Append-only; date every entry; cite the session/source.

## 2026-08-20 — venue sitting (architecture-QMX-2026-08-19 workspace)

**Ratified venue facts the node inherits** (full detail: `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ctrader-venue-facts.md` + research companions):
- Demo and live are separate cTrader hosts; serving both simultaneously REQUIRES two connections (one demo, one live), each carrying unlimited accounts of its kind. This is the mechanism for the corpus's paired-demo fail-safe rule (K-27).
- Rate limits 50/5 req/s are per connection; breach codes mapped; no documented ban/backoff → conservative throttle, typed transient refusals.
- No server clock exists on the Open API — receive-time stamping is mandatory; heartbeat every 10s; weekend maintenance windows exist.
- Depth (Level-2 quote book) IS available via the Open API; no Level-3 trade tape exists. Old corpus claims of "no depth — do not attempt" are overturned (see ctrader-depth-and-connectivity-research.md).
- D1 bar boundary + bar price basis are NEVER hardcoded: first-deploy empirical check + continuous background monitor, stored as per-broker configuration. System gets ~1-week warm-up before live trading.
- Token lifecycle: access token ~30 days; refresh token NEVER expires until used or cTID re-authorized (the compromise-recovery anchor). Refresh possible in-band (ProtoOARefreshTokenReq) or via REST.
- Three independent numeric scale systems (1/100000 market prices; raw-double execution prices; per-message moneyDigits exponent on nine messages; volumes in cents). Uniform /100000 would corrupt the execution path. LightSymbol carries no scaling metadata — full ProtoOASymbol needed before decoding.
- No direct equity field — equity must be derived (balance + quote-currency unrealized PnL) (K-54, corpus).

**Operator ideas/rulings filed for node/risk sittings:**
- Dead zone: ~45-minute relax around session handover (analysis-before-execution; from the first QMX version, operator-solved ~Dec 2025). Operator clarification 2026-08-20: the dead zone pauses TRADING ONLY — data streaming continues throughout; it is NOT kill-switch logic. Related note: real session activity starts later than nominal opens (e.g. Tokyo traders not active at the 7am nominal open) — session-open cross-referencing is a node-era refinement. Risk-sitting policy.
- Broker identity is deployment configuration, never architecture; "account IDs are enough". IC Markets is the operator's intent, deliberately not a framework commitment.
- Operator wants possibly all sessions traded; sessions resolved by calendar rules + tz database, never device/broker location.
- First deployment runs a warm-up week: empirical checks (spot timestamp unit, D1 boundary, BID-bar reconciliation, pip formula validation) run then, simple scripts, loud refusals.

**Node-relevant contradictions left open on the record (for the node/risk sittings):**
- Latency: operator ~50ms full-round-trip direction vs GitBook 35/10–45/100ms budgets — GAP-0013 forbids invented numbers; the six-stage latency decomposition (tick received → evidence write → indicator update → decision → risk evaluation → order submitted) is recorded as AD-13 rungs WITHOUT numbers until measured.
- Paper-mode scope: fail-mechanism-only (K-25 delta) vs standing-state feeding alpha-decay (tracker/map.md, ticket 002). Risk-sitting item (GAP-0041).
- MIS consumer boundary: Book+KSA-only vs manifest-bounded bot consumers (C-01 REOPEN).
- Pool sizing, retry constants, health thresholds: "do not default" standing; R-07 numbers are RECONFIRM-grade only.

**Operator teaching, venue sitting round 3 (2026-08-20, ~2am):**
- The order path is a chain of command: "there are very many things that can block a bot from trading" — MIS (already firing at startup), SQS gating, KSA, correlation ledger, BMS, Book doors, money rules. Any GAP-0036-class ruling must fit that chain, not assume a bare adapter.
- Vocabulary the operator half-remembered — AUDITED, definitive (order-path study, 2026-08-20): **correlation ledger LIVE** (one of the five Records streams); **DPR + PRS DEAD** by operator ruling DEC-0093 ("legacy-only; must not return as risk controls"); **"MIS assembler" never existed** (operator's own phrase was "MIS is an ML ensembler", tracker/map.md 2026-08-18); **"house of money" / "reverse house of money" NEVER FOUND in any corpus layer** — the concept was never written down; closest survivors are the money-rule grammar (book template Section 2) and the money ladder (FORM-0001..0005). If wanted, it is a fresh risk-sitting design item, not a recovery.
- Order path + data path + startup semantics now mapped with citations: `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/trading-node-order-path-study.md` — 15+ independent refusal classes on the order path; startup reconciliation gates the COMMAND pipe only (sensing/MIS flows from boot; K-39).
- "Without the trading node, there is no QMX." Order safety and the adapter contract were held back from ratification pending a Fable-grade deep read of the node docs (order path + data path + startup semantics) — study file: `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/trading-node-order-path-study.md` (in progress).
- Money rules / risk management / position sizing = "one of the hardest things to model… it seems simple, but it's abstract."
- Secrets (GAP-0035, now ratified as AD-26): operator notes the surface is UI-driven — credential entry/management is a platform settings-panel concern; QMF carries only the reference-not-value seam.
- Crypto reaffirmed: CCXT-class, "crypto is not difficult"; cTrader stays on Open API.

**Corpus rules reaffirmed as load-bearing for the adapter (from trading-node-corpus-brief.md):**
- K-42: the Connection Manager lives inside the Adapter and is the sole owner of platform sessions, token buckets, OAuth refresh, arrival stamping, fill attribution, reconnect, gap recovery. No second cTrader client in MIS/BMS/Book/bot code.
- Three-outcome order model: ACCEPTED / REJECTED / UNKNOWN — a timeout is NEVER a rejection; reconciliation resolves UNKNOWN; startup reconciliation before any trading.
- Adapter command vocabulary is exactly four (place_order, cancel_order, close_position, close_all); amend/partial-close may not be smuggled through an opaque payload (K-44 REOPEN).
- Protection funnel: MIS senses → KSA decides (escalate-only; human A1 de-escalates) → Adapter enforces as an effect. Flatten authority was explicitly unassigned — the venue sitting's GAP-0036 ruling reserves it as a human-authorized path, never assumed, never automatic (policy assignment lands in the risk/node sittings).
- Fills correlate by clientMsgId (≤100-char label); recovered fills commit through Records before the connection reports healthy.

**Node-facing consequences of the ratified venue ADs (AD-26/27/28, gate-amended 2026-08-20) — the node sitting inherits these:**
- The node (not the adapter) clears an UNKNOWN block, via an explicit typed `resolve_unknown(command identity, resolution ∈ observed-accepted | observed-absent | operator-attested)` call — the resolution is itself an observation. The block is per command stream = (VenueId, account) and clears on resolution, never on a reconciliation verdict (so PE-7's open-position `unknown` verdict cannot livelock the pipe).
- The application injects and owns: the submission deadline that triggers UNKNOWN (declared, do-not-default), all retry/pool/health constants, the adapter's schedulable session duties (heartbeat/refresh/reconnect/monitors run on the app's scheduler), and the sink protocols (ObservationSink/JournalSink/RecordSink/SecretStore).
- Protection commands (cancel/close/close_all) dispatch ahead of place_order on shared throttles; suspend-new takes local effect instantly. close_position/close_all carry a required typed scope (account | account-binding | instrument-within-binding) — the node's kill path must state its scope.
- Exactly one live refresher per credential (a workstation tool must never refresh a credential the VPS session owns — the refresh token dies on use).
- Demo/paper evidence is role-scoped within world=live; sandbox-produced evidence carries provenance=sandbox and cannot merge into the operator store.
