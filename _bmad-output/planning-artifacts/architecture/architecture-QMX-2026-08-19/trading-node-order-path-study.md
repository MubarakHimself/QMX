# Trading-node order-path study — GAP-0036/0038 deep read (2026-08-20)

Operator-requested deep read before ratifying order safety and the adapter contract. Sources, in corpus authority order (tracker/map.md): current operator rulings > GitBook baseline (local immutable capture 2026-07-18 at `Documents/QMX/raw/online/qmx-gitbook/captures/2026-07-18T141659Z/`, mirrored in `workroom/reference/05-trading-node-primer.md`; live-book baseline `archive/recovery/trading-node-delta/work/gitbook-baseline.md`) > wiki claim-by-claim (`work/wiki-inventory.md`) > BMAD supplement (`work/bmad-supplement.md`) > `trading-node-delta.md` KEEP/RECONFIRM/REOPEN/DROP register. Citations: `[capture/…]` = GitBook capture page; `K-nn`/`C-nn`/`R-nn`/`D-nn` = delta register; `B-nn`/`E-nn`/`M-nn`/`F-nn` = BMAD supplement; `T-nn` = baseline tensions. **This study maps the node; it designs nothing node-internal.**

---

## a. The order path — bot intent to broker fill

The operator is right: an order passes a chain of command, and "very many things can block a bot from trading." Here is the full chain as the corpus states it.

### Standing preconditions (before any intent exists)

| Gate | Rule | Source |
|---|---|---|
| Node booted, startup gates passed | see §b | `[capture/lenses/ops-runbook.md]` |
| Bot certified for THIS book | exam certifies against a specific book; exam/live labeler versions must match (L10) or the certificate is invalid | `[capture/components/examination-engine.md]`, DEC-0055, L10 |
| Bot admitted + activated | promotion → `ADMITTED` (no intents, no ledger) → birth creates virtual ledger at seed S, LIVE-ready; activation timing after ADMITTED is OPEN | K-22, K-24, B-04 |
| Book mode = LIVE | BMS mode registry is authoritative (`CT-BMS-02`); kill-line stand-down = PAPER until cycle-boundary re-seed | `[capture/contracts/ct-bms-02]`, DEC-0023, K-25 |
| Roster/seat state | breaker-benched bot = `BENCHED` seat until next-open auto-reset; `max_concurrent_live_bots = 3` (scalper) | DEC-0032, K-26/K-28 |
| KSA level permits | five levels GREEN→BLACK; automatic transitions escalate only; A1 human de-escalates; trigger→level matrix = node GAP-0015, deliberately empty | `[capture/components/kill-switch-authority.md]`, L8 |
| No news block on the pair | BMS Exposure compiles the news calendar; affected currency expands to all containing pairs; applies to live AND paper; sessions widen, never narrow | K-40, `[capture/contracts/ct-bms-04]`, SCN-0003, L9 |
| Feed and SQS healthy | `feed_state: dead` prevents new entries; unreachable SQS (Spread Quality Sensor — operator-corrected vocabulary, K-38/D-09) = hard door block; degraded sensors are visible, never silent | `[capture/contracts/ct-mis-01]`, DEC-0042 |

### The path itself

```mermaid
sequenceDiagram
    participant MIS as MIS-Live (senses)
    participant Bot as Bot (proposes)
    participant Book as Book: 7 doors + sizing (decides)
    participant KSA as KSA (protection)
    participant AD as Adapter + Connection Mgr (executes)
    participant V as cTrader venue
    participant REC as Records (evidence)
    MIS->>Bot: CT-MIS-01 snapshot (consumer boundary OPEN, C-01)
    Bot->>Book: CT-BOOK-01 intent (book_id, bot_id, pair, side, requested_r, footprint_version, snapshot_version, timestamp_utc)
    Note over Book: doors in fixed order:<br/>footprint → viability veto → R_max →<br/>daily budget → breaker → exposure ledger → kill switch
    Book--xREC: any refusal signs veto ledger (L11, CT-BMS-05)
    Note over Book: sizing: offer = D/(B·b·Lbar); take = min(offer, Kelly[OPEN PE-4])
    Book->>AD: CT-ADAPTER-01 command (command_id, type ∈ 4, account_binding, payload)
    KSA-->>AD: state as EFFECTS, never bot-readable advice
    Note over AD: per-Book sequencer ordering (K-06, incl. shared live/demo)<br/>clientMsgId assigned (≤100-char label)<br/>token bucket 50/5 per connection
    AD->>V: broker-specific execution over pinned session
    V-->>AD: async execution events (fills, partial fills, server events e.g. stop-out)
    AD->>REC: fill correlates by clientMsgId, attributes by label;<br/>state + trade evidence commit ATOMICALLY (K-10, K-55)
```

Step-by-step with every refusal point:

1. **Bot proposes** — emits `CT-BOOK-01` only; never sees broker or KSA (L1, L7). Fields verbatim: `book_id, bot_id, pair, side (BUY|SELL), requested_r (R), footprint_version, snapshot_version, timestamp_utc` `[capture/contracts/ct-book-01]`. The intent pins WHICH snapshot informed it.
2. **Seven doors, fixed order** (DEC-0035, `[capture/components/book-template.md]`): footprint gate (intent inside the book's MEASURED envelope) → viability veto (`round_trip_cost_R/expected_edge_R ≤ 0.10`, FORM-0007) → R_max (`≤ B·b·Lbar`, FORM-0006, Lbar measured per bot at exam) → daily budget (`D = U/n`, drains intraday, FORM-0003) → breaker (B=2 consecutive stop-outs → bench to paper) → exposure ledger (BMS Exposure measurement; cross-book caps = node GAP-0008, open) → kill switch (KSA). **Every refusal signs the veto ledger** (L11; "a no is not journaled → violation").
3. **Sizing (money ladder)** — the book OFFERS a seat (FORM-0004); the take is `min(offer, trust-bounded cost-aware Kelly)` — **the Kelly input is deliberately unfinished (PE-4/K-37; never substitute generic Kelly)**. Doors, not the clock, own permission (dead DEC-0025).
4. **Platform-blind command** — `CT-ADAPTER-01`: `command_id`, `command_type ∈ {place_order, cancel_order, close_position, close_all}`, `account_binding`, `payload` (payload unconstrained = baseline tension T-18). Amendment/partial-close feasible on cTrader but **excluded from the contract; may not be smuggled through the payload** (K-44 REOPEN). Each Book has a deterministic sequencer ordering ALL Book-affecting events, including shared live/demo command ordering (K-06); the paired-demo merge is solely by `book_sequencer_sequence` (E-03).
5. **KSA constrains enforcement** — delivered at the Adapter as effects; KSA completion includes connection drain/quiescence (K-41). MIS senses → KSA decides → Adapter enforces; the three authorities never merge.
6. **Adapter/Connection Manager executes** — the CM lives inside the Adapter and is the SOLE owner of platform sessions, affinity, token buckets, OAuth refresh, arrival stamping, fill attribution, reconnect, and gap recovery (K-42); no second cTrader client anywhere. Rate limits 50/5 req/s per connection (ratified venue fact); throttle honors broker `retryAfter` (K-43).
7. **Asynchronous outcome (fire-and-reconcile)** — fills (incl. `ORDER_PARTIAL_FILL`) and server-initiated events (stop-out; `isServerEvent`) arrive async; a fill correlates by `clientMsgId`, attributes by `label` (≤100 chars), and updates state + trade evidence **atomically in one transaction** (K-55/R-15, K-10/K-47). Recovered fills commit through Records BEFORE the connection reports healthy; even a no-gap reconnect emits correlation evidence (K-43A). Broker equity is DERIVED (balance + quote-currency unrealized PnL; no native field, K-54). Reconciliation (`CT-BMS-03`, direction Treasury→BMS, K-46B): four-part explained delta, verdict `reconciled|drift|unknown`; **unexplained drift = technical kill, halt, no auto-resume** (L14, R-14, D-11); open positions force `unknown` (PE-7 interim: no automatic position action, K-36).

**Count of independent refusal classes on the path: 15+** (certification/parity, admission/activation, book mode, seat state, seven doors ×7, news window, KSA level, feed state, SQS hard-block, sequencer refusal in stand-down, connection unknown_state, rate throttle, journal-unavailable). The operator's instinct was correct and is now mapped.

---

## b. The data path and the startup sequence

### Data path

```
cTrader feed ──> Connection Manager (arrival stamping; K-42)
      │  ONE pinned live-account connection = canonical sensing feed (K-39;
      │  outage FAILS CLOSED until that same feed gap-replays; no sibling failover, D-10)
      ▼
MIS-Live: computes each (labeler, version, parameter-set, pair, resolution) ONCE (DEC-0041)
      ▼ fan-out (consumer set = OPEN conflict C-01/M-02: Book+KSA only vs manifest-bounded bots)
CT-MIS-01 snapshots: spread_state, gap_event, liquidity_stress, feed_state(fresh|stale|dead),
sqs_score, sqs_hard_block, degraded_sensors, [regime, regime_confidence]
      ▼                                  ▼
Book doors consume                MIS-Archive (immutable emissions; Backend is sole finalizer;
                                   manifested Parquet; replay never in the hot path)
      ▼
Records: sole physical writer, exactly five append-only streams
(veto_ledger, trade_journal, book_journal, ksa_audit_log, correlation_ledger; K-11)
— state + evidence commit atomically in one Trading SQLite/WAL transaction (K-10)
      ▼
CT-SYNC one-way Trading→Backend, watermarked, idempotent, verify-before-purge (K-14, F-04)
```

SQS = **Spread Quality Sensor** (operator correction 2026-08-17, K-38/D-09): compares instrument-aware historical spread with current live spread; emits score/hard-block evidence; grants MIS no trade authority. Any "snapshot quality score" expansion is semantic drift (R-08/M-01) — reopened under a different name if ever wanted.

### Startup, as the corpus actually states it

1. `systemd` starts the ONE Trading process (bots, Books, BMS write side, MIS-Live, KSA, Adapter+CM, Records, Powers API — direct module calls, K-03/K-08).
2. Class-4 hot state is REBUILT from evidence before intents flow (wiki: "rebuild hot state before intents").
3. Runbook Start gates `[capture/lenses/ops-runbook.md]`: (1) BMS virtual ledger reconciles with broker reality; (2) KSA state is not unknown; (3) MIS labeler versions match active exam certificates (L10); (4) adapter account binding + broker connection confirmed.
4. Adapter with unknown broker state emits `unknown_state` and **blocks broker execution until reconciled** `[capture/components/broker-adapter.md FM-1]`; the target KSA level for that trigger is node GAP-0015 (deliberately empty).
5. Only after all four gates pass can the first `CT-ADAPTER-01` command legally reach the broker.

### The operator's tension, resolved

He objected: *"reconciliation mandatory at startup makes no sense because the MIS is already firing."* **Both are true because they gate different pipes.** Startup reconciliation blocks the **command pipe** (nothing reaches the broker while ledger/broker state is unknown); it never blocks the **sensing pipe** — MIS connects, streams, computes, and publishes from the moment its pinned feed is up, and its own outage rule is separate (fail closed until the same feed gap-replays, K-39). At boot the node is *sensing first, trading later*: data flows immediately; execution unlocks only when the ledger reconciles, KSA is known, parity holds, and binding is confirmed. The earlier draft's phrase "reconciliation at startup before any trading" survives **only with this scoping** — it gates commands, never data. Reconciliation is also not a one-shot event: it re-runs after every uncertainty window (reconnect, UNKNOWN outcome, gap), and its verdict gates the command pipe continuously. One deliberate openness remains: an open position at reconciliation forces verdict `unknown` (PE-7), and what `unknown` permits beyond kill-line-flip/demo-routing is unresolved by design — resume authority is human, never automatic (D-11).

---

## c. Vocabulary audit — definitive per-term answers

| Term | Verdict | Evidence |
|---|---|---|
| **Correlation ledger** | **LIVE, ratified.** One of exactly five Records streams (K-11). Content: chorus observations + cohort references `[capture/lenses/logging-spec.md]`. Feeds the chorus-flag leash rung (DEC-0048); its frequency rule is registry-null (node GAP-0012). | K-11; logging spec |
| **DPR** | **DEAD.** DEC-0093 "DPR and PRS revival" = dead: "Legacy-only; must not return as current risk controls" (EXT-0256). DEC-0079: auctions, DPR tables, slot machinery = donor-only legacy. Survives only in the wiki attic ("never build from this"). | `_docwork/ratification-packet.md:157,162,344`; wiki attic |
| **PRS** | **DEAD.** Same DEC-0093 ruling. Attic context: "DPR/PRS ranks, global bot pool, continuous merit allocation, WF3 mechanics" — explicitly never-build. | same |
| **MIS assembler** | **NEVER EXISTED as a component name.** Two near-misses explain the memory: (1) the operator's own 2026-08-18 words in `tracker/map.md:45` — MIS is "an **ML ensembler**"; (2) the wiki's AD-19 phrase "QML input **assembles** bot inputs" — the bot-input assembly surface whose fate is the open MIS-consumer conflict (C-01/M-02). No corpus layer defines an "MIS assembler". | tracker/map.md; wiki-inventory M-02 |
| **House of money** | **NEVER FOUND — in any layer.** Searched Desktop QMX (all), the wiki (all pages incl. attic), the full GitBook capture, and the old `Documents/QMX/_bmad-output`. Zero hits. The closest surviving concepts are the **money-rule grammar** (book template Section 2) and the **money ladder** (FORM-0001..0005, SCN-0001). If the operator wants the concept, it is a fresh risk-sitting design item, not a recovery. | exhaustive rg sweep 2026-08-20 |
| **Reverse house of money** | **NEVER FOUND.** Same sweep, zero hits. | same |

---

## d. Corrected GAP-0036 closure proposal (QMF slice only)

### The boundary line, stated first

The node owns the chain of command: doors, leash, KSA, sequencer, BMS verdicts, Records streams, and every "when/who" decision. **QMF's venue seam owns only the shapes**: what a venue command looks like (CT-19), what venue observations and reconciliation evidence look like (CT-20), and the laws that make those shapes safe to build against. GAP-0036's QMF half closes on the six rules below; every "node-internal authority" item stays with its named owner.

### Audit of the rejected five-law draft against the map

| Draft law | Verdict | Correction |
|---|---|---|
| 1. Four commands only | **SURVIVES, strengthened** | Matches CT-ADAPTER-01 verbatim; K-44 confirms amend/partial-close are excluded and may not hide in the payload. Correction: QMF defines the command SHAPE; the CALLER stays unassigned in QMF (CT-19 stub: "caller unassigned; eventual out-of-scope QMX application") — the node's Book-after-doors is that caller, assigned at the node sitting. |
| 2. Fingerprint idempotency IDs | **SURVIVES, grounded** | The venue client-identity field is cTrader `clientMsgId`; corpus already correlates fills by it and attributes by ≤100-char label (K-55/R-15). Addition: the command also carries the node's `book_sequencer_sequence` as ordering evidence (K-06/E-03) — QMF carries the field; the node owns the sequencer. |
| 3. UNKNOWN is a legal outcome | **SURVIVES verbatim** | Matches SCN-0005, the three-tier outcome model, and PE-7 neutrality exactly. |
| 4. "Reconciliation mandatory at startup before any trading" | **CORRECTED — the operator's objection was right** | Reconciliation gates the COMMAND pipe, never the SENSING pipe (see §b). And the reconciliation VERDICT is node/BMS authority (CT-BMS-03); QMF supplies only the evidence read-back and the verdict vocabulary. |
| 5. Flatten = mechanical command, authority reserved | **SURVIVES, sharpened** | Flatten IS `close_position`/`close_all` — already in the four. The protection funnel (MIS senses → KSA decides → Adapter enforces; A1 de-escalates) plus PE-7 ("no automatic position action") plus the empty GAP-0015 matrix confirm: authority assignment belongs to the risk/node sittings; QMF binds only "the adapter executes flatten mechanically and never initiates it." |

### The closure — AD-27 candidate rules (each cited)

1. **Command vocabulary (CT-19):** exactly four kinds — `place_order, cancel_order, close_position, close_all` — adopted from CT-ADAPTER-01 as the platform-blind vocabulary; kinds addable-never-redefined (AD-5), so `amend_order` arrives only by explicit later mint with its own semantics (K-44: never through an opaque payload). Payload is NOT free-form at the QMF layer: command fields are typed per kind on qmf-core nouns (exact prices/quantities per AD-7, instrument identity per AD-9) — this closes baseline tension T-18 at the framework level.
2. **Command identity:** every command carries a client-generated identity derived from the command record's `fp1` fingerprint (AD-10); the adapter maps it into the venue's client-id field, with the mapping and any length bound (cTrader: ≤100 chars) declared in the capability record (CT-18). Re-presenting the same command = same identity = idempotent accept (AD-10's idempotent-rewrite split); a differing command under a reused identity is refused and alarmed. The command additionally carries the caller's ordering evidence (`book_sequencer_sequence`-class field, opaque to QMF).
3. **Three-outcome law (CT-20):** every submission resolves to `ACCEPTED_BY_VENUE | REJECTED_BY_VENUE | DENIED_LOCALLY | UNKNOWN`. A transport error, timeout, or disconnect NEVER implies rejection or success — it yields `UNKNOWN`, which is a state, not an error ("do not treat a request timeout as a rejection — the single most expensive mistake in this domain", broker-connectivity study; SCN-0005 codified). While an `UNKNOWN` is outstanding on an account-binding stream, the adapter refuses new commands on that stream (`transient venue failure`, after-condition = reconciliation) — mirroring `unknown_state` blocks-until-reconciled `[capture FM-1]`. No QMF component retries, assumes, flattens, or invents terminal state on `UNKNOWN`.
4. **Order-state observations (CT-20):** venue order/fill/position events are first-class, append-only observations on qmf-core nouns — states: client-submitted → venue-accepted | venue-rejected | UNKNOWN; venue-accepted → partially-filled* → filled | cancelled | expired | closed-by-venue; server-initiated events (stop-out class, `isServerEvent`) are observations of the same shape, never errors. Every observation stores venue payloads verbatim (AD-7 foreign-money, AD-8 foreign-time + receive stamps) and emits AD-21 `order`/`fill` journal events in gapless per-writer streams; an unpersistable journal event = typed refusal + block new commands (venue spec FM-6). *(Flag, not design: the node's five Records streams and QMF's seven journal event types are two taxonomies; their bridge is a node-sitting documentation item.)*
5. **Reconciliation evidence (CT-20):** the adapter must produce, on demand, a complete read-back of venue orders, fills, positions, and account balance over a stated lookback (the reconciliation triple + equity inputs; equity DERIVED per K-54 — nativeness declared in CT-18). QMF defines the evidence shapes and the verdict vocabulary (`reconciled | drift | unknown`) that CT-BMS-03-class consumers use; WHEN reconciliation runs (startup gate, post-reconnect, post-UNKNOWN) and WHAT verdicts trigger (technical kill, halt, no auto-resume, PE-7 unknown handling) are node/BMS authority already stated in the node corpus. The sensing pipe is never blocked by command-pipe reconciliation.
6. **Outage + flatten:** fail-closed. On disconnect, in-flight commands become `UNKNOWN`; recovered fills commit through evidence before the session reports healthy, and even a no-gap reconnect emits correlation evidence (K-43A). QMF never auto-retries a command whose outcome may be `UNKNOWN`; retryability rides typed refusals (broker `retryAfter` → after-condition); retry/pool/health constants are node values under the do-not-default standing — **no numbers invented (GAP-0013)**. Flatten: the adapter exposes `close_position`/`close_all` mechanically and may never initiate them; no automatic position action on uncertainty (PE-7); flatten-authority assignment (including VPS-death) = risk/node sittings + GAP-0015 matrix.

---

## e. Corrected GAP-0038 closure proposal (QMF slice only)

Checked against how the node actually consumes the adapter:

1. **One neutral port, four contracts.** CT-18 (capability), CT-19 (command), CT-20 (event/reconciliation), CT-21 (secret/session — shaped by ratified AD-26) are defined by qmf-venue on qmf-core nouns; per-venue adapters implement them; nothing imports qmf-venue (default-deny stands); the composition root wires. The Connection Manager is inside the adapter and is the sole session owner (K-42) — in QMF terms, the adapter's CM holds the `WriterId` for every venue-session stream (AD-15 one-writer), and no other component may construct a venue client (enforced by default-deny + composition-root wiring).
2. **Capability discovery (CT-18)** — a versioned, fingerprinted fact-sheet per adapter, consumed before use; invoking anything undeclared = `unsupported capability` refusal. Declared surface (from the ratified venue facts + node consumption): market-data kinds (ticks bid/ask, live bars, depth-L2, spot-timestamp opt-in, trade-tape yes/no); **canonical-sensing-feed support** (a designated connection/account as the pinned sensing source with gap-replay backfill — K-39's requirement made a declared capability); order kinds (the four; amend absent); session topology (demo/live separation, connections required for both, accounts per connection); rate limits + the adapter's declared conservative window model; span caps and paging model (`hasMore`-class); token lifecycle class (per AD-26); equity nativeness (cTrader: derived); server-clock availability (cTrader: none → receive-stamping mandatory); instrument-metadata surface (digits, pipPosition, moneyDigits, lotSize units, schedule + holiday timezones); protection-enforcement primitives (suspend-new, drain, close_all — KSA's enforcement surface; deciding when = node).
3. **Instrument resolution:** venue-native symbols map to opaque `(venue, symbol)` identity (AD-9); the adapter emits instrument/account metadata snapshots as registry records — the typed configuration inputs AD-22 already consumes; full-metadata prerequisite declared (cTrader: LightSymbol insufficient, full ProtoOASymbol required before price decode).
4. **Foreign values verbatim + error mapping:** all venue payloads stored raw with declared scales (the three ratified cTrader scale systems); conversions cross the named AD-7 money boundary with lineage; every venue error code maps to the seven AD-11 categories through a versioned per-adapter table (429/108/11 → `transient venue failure` with `retryAfter` as after-condition; 35 → `invalid input`; 67 → `unavailable dependency`); unmapped codes → `transient venue failure` + alarm, never invented categories.
5. **Sessions and the paired-demo mechanism:** simultaneous demo+live = two connections (ratified venue fact), unlimited accounts per connection; paired-demo bindings are secret-reference-only records (E-03, AD-26); shared-account order-lifecycle merge is solely by the caller's sequencer evidence (E-03) — QMF carries the field, the node owns the merge. No silent sibling-feed failover (D-10).
6. **Protocol pinning + verification:** the venue protocol artifact (Spotware proto release tag) is pinned in the AD-6 register; a tag change is a gated re-verification event (AD-5 second ladder). The ratified first-connection verification suite (bundle B/C: spot-timestamp magnitude, D1-boundary measurement + continuous monitor, BID-bar reconciliation, pip formula, moneyDigits refusal) is a NAMED part of the adapter contract, its assertions journaled as `data-quality`/`control-action` events.
7. **Latency:** the six-stage decomposition (tick received → evidence write → indicator update → decision → risk evaluation → order submitted) is recorded as named AD-13 rungs **with no numbers** (GAP-0013; the ~50ms operator direction and the GitBook 35/100ms budgets stay non-authoritative until measured); the adapter owns the arrival/submit stamps for its stages (K-42 arrival stamping).
8. **Where CCXT-class crypto slots in later:** a crypto adapter declares a different fact-sheet through the same port — 24/7 calendar identity, native trade tape (L3 exists there), API-key token class instead of OAuth, native equity, maker/taker fee model, possibly funding-rate event kinds — all expressible because CT-18 fields are declarations, not cTrader assumptions, and event/command kinds are addable-never-redefined (AD-5). Nothing in the cTrader adapter's specifics leaks into qmf-core (the stubs' own invariant).

---

## f. Operator questions — the minimal set

The deep read shrank the required set to **two confirmations, both with safe defaults** — everything else is either settled by the corpus, ratified tonight, or already deferred by design to a named sitting (flatten policy → risk sitting; KSA matrix → node GAP-0015; MIS consumer boundary → node sitting C-01; paper-scope conflict → risk sitting GAP-0041; Kelly → PE-4).

| # | Question | Recommended default |
|---|---|---|
| 1 | Adopt the node's four-command vocabulary (`place_order, cancel_order, close_position, close_all`) as QMF's CT-19 command kinds NOW (amend arriving only by explicit later mint)? | **Yes** — it is the operator-ratified CT-ADAPTER-01 vocabulary; kinds are addable-never-redefined, so nothing is foreclosed. |
| 2 | Confirm the corrected reconciliation scoping: reconciliation gates the command pipe only; sensing/MIS never blocks on it; verdict consequences stay node/BMS authority? | **Yes** — this is exactly what the runbook + K-39 + FM-1 already say, now stated so no builder misreads "before any trading" as "before any data." |

---

## Appendix — open items this study leaves with their owners (none block GAP-0036/0038 QMF closure)

Node sitting: MIS consumer boundary (C-01/M-02); Records-streams ↔ AD-21 journal-taxonomy bridge; KSA trigger→level matrix (GAP-0015); pool/retry/health constants (do-not-default); startup-gate wiring (old Epic 4.1–4.3 never built). Risk sitting: flatten-vs-carry (PE-7) + flatten authority incl. VPS-death; paper-scope conflict (K-25 vs standing-state); money-rule formula dimensional repair (C-20/T-12); Kelly input (PE-4); dead-zone policy. Backtesting sitting: GAP-0016/0017 as already deferred. Never revive: DPR/PRS (DEC-0093), slot machinery (DEC-0079), session-windows-as-authority, TIGHTEN half-size, mid-cycle top-up, remnant restart, uniform book values, human chorus loop.
