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

## 2026-08-20 — risk sitting (architecture-QMX-2026-08-19 workspace; GAP-0039..0046 closed)

**Operator vocabulary rulings the node inherits (definitive):**
- **KILL SWITCH = GLOBAL black-swan emergency**: stops ALL trading including paper ("flips the entire thing off"); sensor-fed (MIS/SQS are its inputs); human de-escalates. Operator phrased its effect as "cuts off actual connection" — recorded as intent, not bound (closing positions requires the connection); the contract carries effects suspend-new | drain | close-all, and which effect fires per severity is node authority.
- **KILL LINE = per-Book capital floor** ("the amount of capital a book touches so that it stops trading") — a different thing from the kill switch. Kill-line breach auto-flattens that Book's scope (a 3am breach never waits for the operator). Every other money boundary (rollover, sweep, re-seed, paper flip) leaves positions alone. The operator may flatten anything at any time; that authority is inalienable. **Flatten authority is now ASSIGNED** (was the AD-27 leftover).
- **BMS is the account-facing layer**: one BMS instance per account (copied from a versioned default template), serving many Books; chain is bot → Book → BMS → account, verbatim from constitution L1. Risk domain = the account; same-tick questions are always account-scoped.

**Node behaviors ruled this sitting (QMF carries only the contracts):**
- News blackout is INSTRUMENT-scoped and stops live AND paper entries on that instrument ("I can't risk it. For now"). Multi-pair bots keep trading their unblocked instruments. Would-have-been decisions are journaled as suppressed-decision events (recording is not trading) so decay sensing keeps data.
- Dead zones: BOTH window kinds exist — the daily no-session band (~3h per QMX-discussion Flow 9, the maintenance window) AND per-handover buffers (~45min, operator's newer idea). New entries pause; exits/safety/data never blocked. Calendar-dependent; absent for 24/7 crypto. All widths configurable.
- Fifth adapter command MINTED: amend_protection (cTrader ProtoOAAmendPositionSLTPReq, CONFIRMED-PRIMARY, no cancel-replace; amend atomicity UNDOCUMENTED → verify-or-refuse; server-managed trailing exists as a capability fact). V1 dynamic SL/TP = move-to-breakeven ratchet only, risk-reducing, per-Book configurable — pairs with fast invalidation. K-44's four-command REOPEN is resolved by explicit mint, not smuggling.
- Exit ownership (DEC-0067 resolved): Book owns exit policy; bots PROPOSE risk-reducing exits through a versioned Book door. Later Book versions may delegate specific exit organs to specific bot families (version change, not rule break).
- Bench counter: counts stop-outs (exit at ~full planned loss, "negative 1R"); breakeven exits NEVER count (recorded as their own metric); threshold per-bot (2 = "perfect" for a scalper) and configurable per family.
- SQS V1 = the old ratio sensor ADOPTED (historical_avg_spread(symbol, session_window)/current_live_spread; hard-block lines per instrument class; hysteresis band; 4-sigma outlier guard; undefined ⇒ block). All parameters configurable. Authority boundary intact: SQS computes, MIS transports, Book door decides. v2 may use Open-API depth/L2 inputs (research lead).
- Paper: Book-level (DEC-0070 confirmed); multiple demo accounts exist; exactly one active paper-routing target per live binding (duplicate-order prevention); paper starting balance = Book/family-scoped configurable, resettable, sized for data realism.

**Standing operator rules recorded this sitting:**
- "Configurable" ALWAYS means configurable in the UI — every configurable variable minted anywhere must surface as UI-editable at platform level. Templates declare each variable UI-editable vs uneditable ("very important — carry forward to the UI build").
- Authority order for risk/position-sizing/live-trading: GitBook + trading-node docs (archive/recovery + Documents/QMX wiki). QMX-discussion's risk/sizing system was REPLACED — barred as a source there.
- Numeraire = USD, system-wide. "Why would I use anything other than USD?"
- Do not re-discuss trading-node internals with the operator; the corpus answers first, gaps second, new design only if all layers are silent.
- QML ("QML Shared Contract Library") was the original uniform-bot layer — dig: research-risk/qml-original-dig.md. Reusable atoms: ExitLogicRef {module_id, config}, CloseReason taxonomy (the typed why-it-closed label), template-grammar vs per-instance-values split. QML reconciliation = its own sitting (GAP-0047); it will change with the QMF re-basing.
- Operator idea minted this sitting: the "prediction linter" — a static check showing whether a Book can actually register/execute a given bot, testable against demo in the UI.

## 2026-08-28 — TRADING-NODE SITTING (architecture-NODE-2026-08-28 workspace; autonomous one-shot by operator delegation)

**Outcome:** the trading-node architecture spine is written — `_bmad-output/planning-artifacts/architecture/architecture-NODE-2026-08-28/ARCHITECTURE-SPINE.md` (TN-1..TN-25, child of AD-1..41 honoring B-1..15 and QL-1..10), with `.memlog.md` (every ruling, 20 gate rulings, four operator rulings, assumption register A1–A47), `inputs/` (parts-bin inventory of integration@ef9bb25 + corpus verdicts + ten dossiers) and `reviews/` (six-lens gate, fix pass, five-lens validation re-gate). Next-session prompts 13 (documentation factory, node increment) and 14 (epics) appended to `architecture-QMX-2026-08-19/next-session-prompts.md`.

**Ground truth (parts bin):** 154 node capabilities on integration@ef9bb25 = 78 as-is / 24 needs-live-adapter / 52 missing; effort-weighted 45–60% ("about half, not about 60%"): the LAW (risk/control/paper/venue-uncertainty) is ~60–80% built and tested; the RUNTIME (async driver, doors, config, observability, deployment, cTrader transport, equity derivation) is ~25–35%. The node is 100% of a runtime plus the wiring of a very complete rulebook.

**Operator rulings 2026-08-28 (dictated; quoted in the memlog):**
- NO operator command line for the node — control is the desktop UI over the node's API door (the same connection logic the agentic system will use); the node is a plug-in to the UI; deployment tooling is `just node-…` recipes only, never a trading control. "First, make the trading node work. Make sure it can execute."
- Soak = ONE FULL WEEK unattended on the demo account (= the ratified first-deploy warm-up week), live binding at its end; tracking is mandatory: Prometheus/Grafana-class as a SEPARATE zero-authority system ("like how big tech teams work"); a dedicated monitoring agent later.
- Promotion = a simple UI click after reviewed backtest evidence; sign and activate are two separate acts; the machinery runs silently.
- News: "I will not pay for news" — Forex Factory free weekly file is the sole V1 source; no paid fallback ever; a second free source or an agent-scraped JSON in the same intake shape later.
- MIS models do not exist and must be trained (download, clean, train, shadow-roll) — the LAST epic, run by agents in a sandbox or as a script on the operator's laptop; shadow rollout stands; Kronos-class pretrained candidates carry no authority without fresh ratification.
- The UI will exist and must be kept in mind everywhere (walk every operator moment as a UI story later); extensibility (new Books/BMSs/bots/versions = registry + config, never code) is a requirement; alpha decay stays at AD-41 primitives.

**Load-bearing node rulings (see the spine for the full text):** compose → fingerprint → seal boot ceremony (constructed — the named "three-tier composition" ruling exists in no corpus layer); one long-lived systemd service (fixed `qmx` account, `/var/lib/qmx` trees) hosting the trading loop AND live recording (cTrader allows one demo + one live connection); QMB's loop unforked via `run_slice` with a push-to-pull accumulator as the single first writer; stand-down-alive with doors up before preflight and an operator `resurrect` act; every command-stream block is entry-side only (L39); AD-36 never-auto predicates; KSA levels adopted from the GitBook baseline with the effect matrix blank-blocks-live (pre-soak ruling); kill line = `loss_floor` per binding on the virtual-ledger equity series; paper on the paired demo account, no twins; FOUR reconciliation verdicts; refresh keyed by credential reference (one refresher); secrets two-layer (systemd-creds host-key KEK + AEAD state), wizard over SSH stdin from Credential Manager `qmx/*`, backup payload key escrowed on the workstation + offline copy, VPS-loss runbook; Forex Factory only; nightly backup + nightly sample restore + monthly full restore + host-loss rehearsal; chrony bands as registry rows; alert allow-list + "stopped accepting entries / cannot persist evidence" class + external dead-man's switch; three doors (Python API, localhost HTTP evidence channel, unix-socket powers channel with SO_PEERCRED), no command line; `value-status` on every variable; VenueClientPort minted by the node with the cTrader transport increment landing in qmf-venue's ConnectionManager (A37, cheap veto); replay import port as the one sanctioned cross-world read; MIS = signal snapshot seam + shadow-lane seam now, training later.

**Still open / human-only:** Spotware app approval + sandbox token; VPS procurement (modest; the soak measures); live KYC; swap-free admin-fee schedule in writing; bucket account; backup-key escrow; notification-channel account; the KSA matrix values (pre-soak operator ratification); ticket 006's trendbar basis stays measured-per-broker (SECONDARY web evidence says BID).
