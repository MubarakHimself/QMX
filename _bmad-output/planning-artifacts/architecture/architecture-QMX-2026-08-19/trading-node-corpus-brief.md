# Venue-relevant constraints on the future trading node — corpus mining brief (2026-08-20)

Explore-agent sweep over the QMX corpus, operator-requested before wrapping the venue sitting. Reference only — nothing designed here. Corpus authority order (tracker/map.md line 23): current operator rulings > GitBook baseline (workroom/reference/05-trading-node-primer.md) > wiki/BMAD claim-by-claim > archive/recovery/ = evidence requiring fresh ratification.

## 1. How the node connects to the venue

- **~50ms full-round-trip target** — operator direction, explicitly uncertain (memlog line 38). GitBook baseline uses different numbers: "tick-to-MIS 35 ms, order 10–45 ms, end-to-end 100 ms" (05-trading-node-primer.md:465; gitbook-baseline.md:157). **Contradiction: neither supersedes the other; GAP-0013 forbids invented numbers. The 50ms is a direction, not a budget.** The six-stage latency decomposition is THIS sitting's assignment (spine Deferred table).
- **K-42 (operator-ratified delta):** "Connection Manager lives inside Adapter and is the sole owner of platform sessions, affinity, token buckets, OAuth refresh, arrival stamping, fill attribution, reconnect, and gap recovery… Do not create a second cTrader client in MIS, BMS, Book, or bot code." (archive/recovery/trading-node-delta/trading-node-delta.md)
- **K-43/K-43A:** cTrader connection facts carried as platform constraints, numbers flagged RECONFIRM; "recovered fills commit through Records before the connection becomes healthy; even a no-gap reconnect emits correlation evidence."
- Pool size, shard count, retry constants, health thresholds: **"Do not default"** (wiki-inventory.md:138). R-07 proof numbers (app ceiling 8, per-account 1/4, retries 250/1000/4000/16000 ms) marked RECONFIRM, not authority.
- workroom/research/05-broker-connectivity.md: Spotware's own "at most two connections: one demo, one live"; streaming-beats-polling is a decided stance ("push beats polling" for never missing a fill); open question 5: is one connection enough under the shared 50 req/s ceiling — load-dependent.
- Broker identity ruled out of architecture (operator, this sitting). First-connection + continuous D1-boundary detection = standing node behavior (operator, this sitting).

## 2. Demo-vs-live: fail-safe, paper, multi-account

- **K-27 (operator-ratified; hardest adapter constraint in the corpus):** "Every live account binding has a paired demo binding for fail-mechanism fills, while sensing stays on the pinned canonical live feed. KEEP — No silent sibling-feed failover."
- **K-06:** one deterministic per-Book sequencer for all Book-affecting events "including shared live/demo command ordering". D-10 forbids independent live/demo ordering.
- **K-25 (later delta):** trading-node paper = fail-mechanism surface only; Book kill-line LIVE→PAPER until cycle-boundary re-seed; bot-seat breaker LIVE→BENCHED→LIVE. **Contradiction on record (C-15):** GitBook treats paper as a general diagnostic mode; tracker/map.md:46 + ticket 002:45 say paper is a *standing state* feeding alpha-decay continuously. Neither re-ratified — risk-sitting item (GAP-0041).
- Book-level paper mode operator-ratified 2026-08-18 (archive/qmx-2.txt~2835): Book switches to paper/demo account, bots keep trading, no parallel paper twins; multiple demo accounts expected (paper-mode Books + post-backtest validation).
- Ratified vocabulary: account roles live/demo/paper-validation/paper-benched/prop-firm (docs/components/qmf-risk.md:61); paper/demo = world=live (SCN-0006); duplicate-order prohibition (GAP-0041 open).
- Ticket 006: "confirm IC Markets cTrader demo + live both expose Open API."
- Shadow rollout: ENH-0005 named, detail not published.
- **Open mechanism question:** whether the paired demo binding is a second connection / second account / second adapter instance — nothing states it; Spotware's two-connection shape is the only one on record (now verified primary: demo+live REQUIRE two connections).

## 3. MIS wiring — what it consumes from the venue

- **K-39:** MIS uses ONE pinned live-account connection as canonical sensing feed; outage fails closed until that feed gap-replays; no silent failover.
- CT-MIS-01 snapshot payload (gitbook-baseline §4.2): pair, resolution, snapshot_version, spread_state (normal|elevated|extreme), gap_event, liquidity_stress, feed_state (fresh|stale|dead), sqs_score, sqs_hard_block, degraded_sensors; optional regime + regime_confidence. Compute-once fan-out. Ingest schema = published gap.
- **K-38/D-09:** SQS = Spread Quality Sensor (historical vs live spread comparison, instrument-aware) — adapter must deliver per-instrument bid/ask spread evidence.
- Heavy = MIS-side (regime detection, GARCH, correlation matrices, ML inference), computed once, fanned out (operator words, qmf-4.txt~331; ratified per-configuration in AD-24). MIS live-data collection = node-side pure Python, explicitly NOT QMF.
- MIS consumer-boundary conflict open (C-01: bots direct delivery forbidden vs manifest-bounded bot consumers).
- Per corpus, MIS consumes: ticks (bid/ask for spread), bar/resolution data, feed liveness. No depth, no trade prints.

## 4. Kill switch / flatten / emergency

- **K-41 protection funnel:** MIS senses → standalone KSA decides → Adapter enforces (as an effect, never advice a bot reads). KSA completion includes connection drain/quiescence.
- KSA: five levels GREEN/YELLOW/ORANGE/RED/BLACK; trigger classes scheduled_news, black_swan, connectivity, unknown_state; **L8: automatic transitions escalate only; de-escalation requires A1 human authority.** Trigger-to-level matrix deliberately empty (GitBook GAP-0015 — "do not invent target state here").
- **Adapter command vocabulary is exactly four: place_order, cancel_order, close_position, close_all.** Unknown startup state emits unknown_state and blocks broker execution until reconciled.
- **Flatten authority explicitly unassigned** (GAP-0036; map.md:79 "who flattens positions if the VPS dies"; K-36/PE-7: "no automatic position action… without deciding flatten-vs-carry"). SCN-0005: on lost certainty an implementation must NOT retry, assume success/failure, flatten, resume, or persist invented state — typed refusal only.
- Kill switch "nowhere designed, incl. behaviour when it fires while the broker connection is down; the one component with unbounded failure cost" (map.md:77). News blocks are pair-scoped; blocked bots may continue in paper.
- Fail-closed stand-down keeps the operator door (Powers API) reachable while sequencers refuse and connections drain.
- reconciliation_epsilon = 0; CT-BMS-03 drift = technical kill, no automatic resume. Clock-drift bands (time-audit-devops): ok ≤10ms / warn ≥25ms / no-new-entry ≥100ms / halt ≥250ms.
- Operator dead-zone idea (~45min no-trade around session handover) filed for risk sitting (this sitting's memlog).

## 5. Order lifecycle, retries, reconciliation, idempotency, partial fills

- GAP-0036 recommendation on record: client-generated idempotency keys; append-only order observations; reconcile after every uncertainty. FM-4: no submission code until GAP-0036; spec invents no recovery rule.
- **Three-tier outcome model (05-broker-connectivity.md, most load-bearing borrowed rule):** an order command has THREE outcomes — accepted, rejected, UNKNOWN. "Transport errors, timeouts, and disconnects typically leave outcomes unresolved rather than implying rejection." OrderAck outcome: ACCEPTED_BY_VENUE | REJECTED_BY_VENUE | DENIED_LOCALLY | UNKNOWN — "UNKNOWN is not an error; it is a state that reconciliation resolves." **"Do not treat a request timeout as a rejection — the single most expensive mistake available in this domain."**
- Reconciliation triple: fetch_order_status_reports / fetch_fill_reports / fetch_position_status_reports; reconcile(lookback) at startup BEFORE any strategy trades ("positions can be opened and closed by the venue (stop-out) while QMF is down").
- **K-55:** fills correlate by client message id (clientMsgId, ≤100 chars label), attribute by label, atomically update state + CT-BMS-05 evidence.
- **K-44:** cTrader amendment + partial close feasible but CT-ADAPTER-01 defines only the four commands; amend_order may not be smuggled through an opaque payload — REOPEN item.
- **K-54:** broker equity must be computed (balance + quote-currency unrealized PnL) — cTrader supplies no direct equity field.
- R-14: reconciliation verdicts reconciled | drift | unknown; only unexplained live drift causes technical kill.
- Partial fills exist as venue events (ORDER_PARTIAL_FILL; isServerEvent marks server-generated e.g. stop-out).
- qmf-venue spec: order/fill = two of the seven journal event types, gapless per-writer streams; journal-unavailable = typed refusal; venue edge = the single place async exists; adapter boundary = named money-path conversion boundary.

## 6. DOM/depth ambitions — contradiction resolved this sitting

- Old corpus positions: "order-book imbalance / depth — NO — do not attempt" (research/10 M12); fill-simulation study assumed "no order-book depth and no trade prints". **OVERTURNED by primary research this sitting:** depth IS on the Open API — Level-2-class quote book (ProtoOASubscribeDepthQuotesReq / ProtoOADepthEvent / ProtoOADepthQuote; vendor's own words "Level II quotes"); NO L3/tape exists (closed payload-catalog proof). See ctrader-depth-and-connectivity-research.md.
- Ratified ambition stands: core nouns must later support order flow/DOM/tape (ledger line 261; ticket 002:40); AD-22 defers the governed series form; raw recording possible now.

## Nothing in the corpus on

- A ratified venue latency budget (six-stage decomposition = this sitting's assignment to record).
- Pool sizing/shard/retry/health numbers (do-not-default standing).
- The paired-demo mechanism (two connections now verified as the required shape).
- Crash-loop thresholds K/T, journal-latency thresholds, preflight backend reachability (trading-node-delta §6 item 11).
