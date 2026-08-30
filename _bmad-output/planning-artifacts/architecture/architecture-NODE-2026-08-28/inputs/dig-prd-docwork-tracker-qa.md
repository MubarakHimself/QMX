# Node dig — PRD package, _docwork, tracker, and QA trace

Discovery dossier for the QMX trading-node architecture sitting (2026-08-28). Every
claim carries a `path:line` citation. Main-repo paths are relative to
`C:/Users/Mubarak/Desktop/QMX/`; QA-trace paths are relative to the integration
worktree and prefixed `QMX-worktrees/node-inventory/`. Vocabulary discipline
observed (banned words quoted only when citing a source).

The node is **Phase 2, build not started** — one product, two modes (paper/live),
VPS-resident, hosting Book/BMS runtime + QML bot seats + the cTrader order path over
qmf-venue, recording live data via qmf-data. The foundation (QMF + QMB + QML, 23
epics) is merged on `integration`; it built the *contracts and seams* the node
consumes but not the node runtime. The operator expects the node to be **rewritten
on QMF and everything built before it**.

---

## PART A — PRD (prd-QMX-2026-08-21/prd.md), node-relevant content

### A1. Node's platform slot, delivery sequence, rewrite expectation
- The node is one of six platform layers; corpus status **"GitBook design baseline; build not started"**, PRD treatment "Capability outline only (§6)" — `_bmad-output/planning-artifacts/prds/prd-QMX-2026-08-21/prd.md:82`.
- Vision: end-state is a **Bloomberg-terminal desktop app paired with a VPS-resident trading node that trades continuously**, plus later agent workers — `prd.md:58-61`.
- Delivery sequence (operator-ratified 2026-08-21): Phase 1 = QMF+QMB+QML through the factory; **Phase 2 = the trading node, "with a high chance it is rewritten using QMF and everything built before it."** QMA on its own track — `prd.md:87-94`.
- Sequencing constraint [MINED] for epics/stories: the **cTrader capability probe (CT-18 verify-or-refuse) belongs among the earliest factory work units** — venue feasibility (lot rounding, min lot, feasibility clamp, capability-declaration shape) cannot be designed on paper — `prd.md:96-100`.
- Operator note: the node is the **operationally intense phase** — MIS carries ML instances with training, shadow-rollout, and retraining cycles — which is why the **DevOps success lens (§9) is primary** — `prd.md:382-385`.

### A2. §3 Unattended doctrine + notification allow-list
- **Unattended doctrine.** No intraday human judgment. Notifications must never create intraday decision loops. Only a human-signed promotion occurrence crosses into live money (SCN-0007; ADR-0015; L17) — `prd.md:115-117`.
- **Notification allow-list [MINED]:** notifications fire only on a **closed, ratified event-class allow-list — sweep, re-seed, refund, kill-switch/KSA events, and supervision fail-closed; everything else is console evidence, never a push** — `prd.md:119-127`.
- **Two-plane rule:** authoritative system records (journals, veto ledger, lineage) and operator notification delivery are **separate layers with separate policies — losing a notification never erases the underlying evidence, and the notification channel is never a permission path back into live trading.** Delivery mechanics (channels, retries, dedupe, quiet hours, credentials) stay deferred to the node/terminal phases — `prd.md:122-127`.
- Forward-compat hook: one operator today but others (possibly open-source) later — action attribution stays named; no surface hard-bakes an anonymous single-user assumption — `prd.md:129-137`.

### A3. §4 Operator journeys (the node's operator-power surface)
- **Promote a bot to live** — human-signed promotion attesting the record's fingerprint; no agent or test result can do it (SCN-0007). [MINED] The promotion click **re-runs its full precondition battery server-side against fresh state — displayed-eligible is never a guarantee, stale evidence never authorizes; the crossing is a node-initiated pull, idempotent by artifact key, landing the unit ADMITTED (no intents, no ledger) with live activation a later, separate boundary** — `prd.md:144-150`.
- **Run the periodic review** [MINED] — the weekly Sunday review + the retirement (sunset) review, both operator power actions fed by read-model evidence (performance explanation, footprint/decay sensing, reconciliation status) — `prd.md:151-154`.
- **Survive venue uncertainty** — a lost order submission resolves to UNKNOWN and blocks the command stream until explicitly reconciled (SCN-0005) — `prd.md:158-159`.
- **Flip a Book to paper** — a dated binding-epoch change, not a new object (SCN-0006) — `prd.md:160-161`.
- **Ride out news** — pair-scoped news windows block entries fail-closed, live and paper alike; risk-reducing acts always pass (SCN-0008/0010) — `prd.md:162-163`.
- **Restore from disaster** — recoverability claimed only through verify primitives (SCN-0004) — `prd.md:166-167`.

### A4. §5E/5F — venue/risk FRs the node consumes (list)
Venue boundary (qmf-venue; cTrader):
- **FR-022** venue capabilities via two-artifact verify-or-refuse before any command (CT-18) — `prd.md:260-261`.
- **FR-023** exactly five command kinds under the four-outcome law; timeout≠rejection; **UNKNOWN is a state not an error and blocks its (venue,account) command stream until explicit reconciliation; never self-clear/auto-retry/auto-flatten** (CT-19; SCN-0005; L35) — `prd.md:262-266`.
- **FR-024** events recorded before interpreted; **reconciliation gates the command pipe only — market data keeps flowing** (CT-20) — `prd.md:267-269`.
- **FR-025** credentials as secret references never values, never leave the connection manager (CT-21; L34) — `prd.md:271-272`.
- **FR-026** cTrader Open API is the first venue adapter behind the venue-neutral port; platform stays venue-blind above the port (ADR-0007) — `prd.md:273-274`.
Risk/governance (qmf-risk):
- **FR-027** Books are chartered gatekeepers; BMS one per account, accounts+constrains but never trades/sizes/reaches inside a Book (CT-22/27; ADR-0008) — `prd.md:278-281`.
- **FR-028** Book owns sizing; requested_r Book-resolved; declared full-loss price required; three admission layers, no probation, no paper-performance gate; R frozen at admission (CT-23; ADR-0010) — `prd.md:282-286`.
- **FR-029** paper = Book-level standing evidence state entered by a dated binding-epoch change (CT-24; ADR-0009; SCN-0006) — `prd.md:288`.
- **FR-030** risk journals project Book/BMS state at read time (CT-25) — `prd.md:289`.
- **FR-031** a bot binds exactly one Book; bindings are dated epochs (CT-28) — `prd.md:290`.
- **FR-032** exits Book-owned and risk-monotonic; bots propose risk-reducing exits only; every virtual close mints one exit record (CT-29; L39) — `prd.md:292-294`.
- **FR-033** exit-preservation invariant — no control blocks a risk-reducing act; **kill-switch (global) and kill-line (per-Book floor) distinct; same-tick actions arbitrate by BMS rank on one stream; news windows block entries fail-closed by instrument scope** (CT-30/31; SCN-0008/0010; L39) — `prd.md:295-299`.
- **FR-034** performance publishes, never acts; no composite score gates money; benching is a read-time fold (CT-32; SCN-0011) — `prd.md:300-302`.
- **FR-035** numeraire USD-only V1; every risk/sizing/window/SQS value is a UI-editable configurable with no spine constant; **a blank value blocks live money while allowing registration and non-live binding** (L38) — `prd.md:304-306`.
- **FR-009** the only path to live money is a human-signed promotion occurrence with a mandatory plain-words summary as an identity field (ADR-0015; SCN-0007; L17) — `prd.md:206-208`.
- **FR-050** QML defines the bot runtime protocol that **QMB (and later the trading node) hosts** (QL-spine) — `prd.md:367`.
- Data the node records: **FR-017** Dukascopy first historical tick source, download-once, personal-use; **FR-018** news-calendar feed governed source, failed refresh degrades to fail-closed block (SCN-0008) — `prd.md:236-242`.

### A5. §6 Phase-2 trading node — outline + one ratified ruling + mined doctrine
- **Node = unattended VPS runtime hosting** Book/BMS runtime, order path over qmf-venue, **KSA (escalate-only global protection; only operator resurrection de-escalates)**, sizing-ladder evaluation, **ledger↔broker drift kill, retry/pool constants, and MIS-Live — the node-runtime labeler layer computing market-condition signals, compute-once, for Book and KSA**. Design baseline: the GitBook (authoritative for risk/sizing/live per L2/L37). **Explicitly out of QMF scope by ruling; build not started; expected to be rewritten on QMF** — `prd.md:374-385`.
- **Node doctrine already operator-ratified (2026-08-21, resolves DEC-0049): detector-pause scoping** — on a rare data-quality/drift event an automatic detector may pause, as an **entry-blocking control at the narrowest affected scope (instrument, currency cohort, Book, venue/broker, or system), never wider and never touching positions or exits (L39); inform-vs-pause posture UI-editable per L38** — `prd.md:387-392`.

Mined node doctrine — all [MINED], to ratify at node planning (`prd.md:394-441`):
- **Startup and recovery ordering.** A deterministic cold-start preflight gate runs *before any state mutation* (host/disk/network/pinned-version checks, fail-closed with a typed failure id), then a fixed per-Book order: **connect → reconnect gap recovery (fetch deals/positions since the last-seen execution event, commit recovered fills before reporting healthy) → missed rollover catch-up (boundary equity reconstructed from journals, sweep journaled as a correction-style append) → protection-state projection (breakers, budgets, exposure rebuilt from journals) → readiness gates → the sequencer accepts intents.** Invariant: **a crash never resets safety counters, because there are no safety counters — only journal projections** — `prd.md:396-405`.
- **Drift is reconciled-explained, never raw equality.** Broker-vs-virtual divergence decomposes into journaled components (swept-but-unwithdrawn cash, re-seed remnants, open unrealized P&L); **only the residual is drift. Verdicts: reconciled | drift | unknown. Unexplained live drift halts trading, and restart is not permission to resume — a fresh reconciliation review is. The paper/demo binding is excluded from the live drift check** — `prd.md:406-411`.
- **Rate limits are a design input.** One connection pool per account binding, per-account command affinity, token-bucket limiting; caps are per connection at protocol level, so synchronized bursts (mass invalidation-close plus re-amend) need sharding or a shared bucket; this is also the future multi-account load-balancer seam — `prd.md:412-416`.
- **Fail-closed stand-down is an alive state.** Past a crash-loop threshold the process boots into stand-down: sequencers refuse-and-journal, adapter connections quiesce and drain, and the operator-powers surface keeps serving — resurrection stays reachable. Paired rule: **a protection transition counts as enforced only after the account's connections have quiesced and drained** — `prd.md:418-422`.
- **Shadow lane shape.** Candidate labeler/model versions run as near-real-time replay over the captured canonical feed, off the hot path, to their own manifest prefix, never to live consumers, evaluated over one full affected-Book cycle; promotion is ratification → version bump → re-certification. **A recovered or pre-trained model carries no authority without fresh ratification (parameter identity + training + shadow evidence). Training is an offline job — it may seed its RNG provided the seed is recorded; the no-ambient-randomness invariant binds the live runtime** — `prd.md:424-431`.
- **The always-on evidence tier.** The node phase implicitly needs a placement and authority boundary for archive, captured feed, heavy analytics, and the shadow lane — **explicitly not a database server and not a second writer: the hot path never blocks on it (only disk physics fail-closes trading); sync is one-way, watermarked, idempotent, resumable, under verify-before-purge (the hot side purges only what the evidence side has durably persisted AND content-verified); recovery re-requests carry watermarks only, never payload backward; the only reverse crossing is the click-gated promotion pull.** A placement boundary, not a mandate for separately deployed services — `prd.md:432-441`.

### A6. §6 terminal (Phase 3) console spine — node-facing bits
Mined console spine [MINED], to ratify at terminal planning (`prd.md:449-500`):
- UI-only, never a second system of record; business authority, persistence, command validation stay server-side; the desktop app holds no trading secrets — `prd.md:451-456`.
- **Exactly two channels:** an evidence read channel and a powers action channel (resurrection, ratification/promotion, review actions) — `prd.md:457-459`.
- Anti-goals verbatim: no direct manual-trading surface; **no generic LIVE/PAPER toggle**; no single global health indicator hiding independent failure domains; no stale evidence authorizing an action; no editable setting without registry-backed configurability; no optimistic command success without server validation and evidence; no Prometheus/Grafana clone; **no assumption that a future venue is recolored forex** — `prd.md:460-466`.
- **State independence:** Safety, execution readiness, connection, reconciliation, data freshness, lifecycle, and sync are independent states that never collapse into one health color; **requested protection state displays separately from enforcement completion** — `prd.md:467-472`.
- Settings evidence-scoped in three scopes (system settings/secrets & bindings never registry numerics; component settings; instance values); **Book↔account bindings are console-configured, mutable, journaled, in system-settings scope**; note the variables registry carries `configurable` but **no value-status field** yet — `prd.md:478-489`.

### A7. §6 QMA + deferred products
- QMA agentic system on its own track, **research — ideation has not begun**; old agentic reqs scrapped. Track input [MINED]: an earlier ruling set the **agentic data-egress boundary as pull-only access to curated datasets, no live-service surfaces exposed to agents at all** — a harder governance stance to weigh vs current typed-doors posture — `prd.md:502-513`.
- Simulator UI and MIS remain deferred per ADR-0011 — distinct from the node's own **MIS-Live** labeler layer — `prd.md:85`, `prd.md:515-516`.

### A8. §7 Out of scope (V1) — node lives here
- **Trading node runtime and all its constants (kill-switch matrix, severity policy, retry/pool numbers, RPO/RTO); deploy/infra/ops** — `prd.md:520-521`.
- `world=simulated` reserved-unusable until GAP-0048 — `prd.md:525`.
- Margin-aware sizing, multi-currency/non-USD numeraire, prop-firm Book extension, L2 depth vocabulary, `close_partial`, swap-Wednesday handling — `prd.md:526-527`.

### A9. §8 NFR-01..11 (node-load-bearing)
- **NFR-01** CPython 3.14; tier-1 Win11 + Ubuntu LTS x86-64 (ADR-0012) — `prd.md:540`.
- **NFR-02** ruff + pyright-strict + pytest; coverage floor 80%, 100% branch on CT-01/CT-02; two tier-1 static scanners (money-path scanner; ambient-nondeterminism scanner forbidding `datetime.now/utcnow`, `time.time/monotonic/perf_counter`, `random.*`, `secrets.*`, `np.random`) — `prd.md:544-550`.
- **NFR-03** determinism / replay reproducibility a platform property — `prd.md:551-553`.
- **NFR-04** measure-then-budget: no invented numbers; benchmark speed+peak memory at 10/100/200 marks against the ~40-bot reference; only stated constraint qmf-core import <~1s — `prd.md:554-556`.
- **NFR-05** secrets as references only, tier-1 scan gate, encrypted off-machine backup; credentials never leave the connection manager (CT-21, CT-14; L34) — `prd.md:558-560`.
- **NFR-06** evidence append-only, retained forever; per-contract integer format versions keep old evidence readable — `prd.md:561-563`.
- **NFR-07** `configurable: true` means UI-editable always; blank risk values block live money — `prd.md:564-566`.
- **NFR-08** journals, lineage, memlogged decisions make every state change reconstructable — `prd.md:567-569`.
- **NFR-09** QMF spawns no concurrency; applications own it (QMB's governor is V1 instance); async only at venue edge — `prd.md:570-572`.
- **NFR-10 Operability & deployability (operator-ratified 2026-08-21):** works out of the box (`uv add`, no DB server, no Docker for QMB); a single person can deploy/monitor/repair. [MINED] **install, start, stop, back up, recover from one canonical checkout — never hunt across folders or reconstruct Git state.** Serve-both-layers: the monitoring/eval substrate for QMF/QMB is the same one that later serves QMA — never two stacks; any external plane (Prometheus/Grafana class) is **zero-authority** (consumes exported evidence, DEC-0112; "an alert is evidence, not permission", DEC-0041) — `prd.md:573-586`.
- **NFR-11 Failure-register discipline [MINED]:** every designed failure mode ships a register entry (failure class, detection, auto-recovery/retry, visible degraded state, notification tier, product-user affordance — what failed/why/can I retry/what a retry does), written for someone not in the design room; the operator is treated as a product user for failure rendering — `prd.md:587-594`.

### A10. §9 Success measures + §10 open items (node rows 11-15)
- Primary DevOps lens (gating): deployable out of the box (server deploy "unremarkable — the trading node phase will demand it: ML training, shadow rollouts, retraining under MIS"); one-person operability; external usability proves internal usability — `prd.md:598-626`. Fabrication counter-metric [MINED]: no factory agent may invent mock/synthetic/placeholder data — fail closed and land in the ledger — `prd.md:628-635`.
- **Row 11 [MINED] Alpha-decay signal catalog** — corpus ratifies concept + guardrails but no signal list; candidate inputs: breaker-door/leash-event fire density, MAE/MFE drift, drawdown decomposition, regime/session-conditioned performance drift, measured proximity to charter-death; measured quantities + registry formulas only, never a declared-weight composite score; decay informs the sunset review, never disposes — `prd.md:672`.
- **Row 12 [MINED] Node-phase position-safety cluster** — four questions neither old build nor corpus closed: (a) **stop-out taxonomy** — does a breakeven exit/forced flat count toward sizing (bench half ruled); (b) **position fate at money boundaries** — how unrealized P&L enters a sweep (boundaries leave positions alone; the accounting is unstated); (c) **dynamic SL/TP grammar** — Book grammar, BMS as config authority; (d) **amendment idempotency threshold** (UI-editable) suppressing tick-storm duplicate amends — `prd.md:673`.
- **Row 13 [MINED] Atomic decision-plus-evidence commit vs the store seam** — old build required decision-state-change + journal-append to commit atomically; corpus has WriterId ownership + gapless streams but no dual-write atomicity rule, and the store seam spans engines without transactions (Parquet/JSONL). Is atomic dual-write a journal-path requirement, does it constrain the seam? Corpus wins pending a ruling — `prd.md:674`.
- **Row 14 [MINED] News-provider selection evidence for DEC-0119** — Forex Factory free weekly JSON primary (rate-limited ~2 downloads/5 min); FMP/Trading Economics/FXStreet impact-carrying fallbacks; EODHD disqualified (no impact field); scraping rejected — `prd.md:675`.
- **Row 15 [MINED] Deep-history acquisition evidence** — TrueFX (16 majors, tick since 2009) + HistData (M1+tick) as Dukascopy companions; Databento carries no spot FX; venue-only backfill rate-capped into unviability, so the recent window needs a platform-continuity bridge — `prd.md:676`.

---

## PART B — PRD-package mining docs (node-relevant)

### B1. mine-node.md — the "later, more stable" old trading node (capability map only)
Source disposition: this is the 2026-07-20-generation node (`TRADING-NODE-SHIP-GOAL.md`, session ended 2026-08-10, old Epic 1-7 plan); a **different contract generation** (old CT-BMS-*/CT-MIS-*/CT-BOOK-*/CT-SYNC-* etc.); code deliberately "proof-shaped" (pure-data validators, no sockets/training). Node expected rewritten on QMF; **nothing carried as implementation** — only the capability map — `mine-node.md:12-41`.
- **Startup/preflight (1.1):** deterministic cold-start preflight before any state mutation — ordered `host_os_systemd_or_wsl2 → disk (≥1 GiB free) → network reachability (cTrader demo.ctraderapi.com:5035) → pinned-stack versions`, fail-closed, typed id `PREFLIGHT_FAILED`; startup version floor (`sqlite_version >= 3.53`); forward+reverse migrations with append-only stream triggers — `mine-node.md:52-64`.
- **Venue/order path (1.2):** cTrader connection manager — OAuth chain (app auth → demo-account discovery → per-account OAuth authorize-click surfaced as an operator *stop*), pool sizing + retry + reconnect + gap-recovery, polite rate limiting (**ratified ceiling ~5 req/s per connection**, backoff+jitter), broker-equity computation, **label-based fill attribution with journaled fills**, paired-demo-binding per live account binding; platform-blind command adapter (place/cancel/amend + fifth command) under the four-outcome law; time authority injected — `mine-node.md:66-83`.
- **Book/BMS/Treasury (1.3):** Book-type schema sections 0-5 (`charter, footprint, money_rules, entrance_exam[banned-word], leash_chain, capacity_and_sweep_mechanics`); BMS-owned book-mode registry (V1 `LIVE`/`PAPER`; `BENCHED`/`STOOD_DOWN` reserved); Treasury virtual-ledger with rollover-only sweep (`sweep/refund/re_seed`, `broker_server_rollover` boundary only; physical withdrawal prohibited; refund dormant); paper = frozen counterfactual; **reconciliation + technical-kill** (`reconciled/drift/unknown`; unexplained live drift → technical_kill → halt_trading; `reconciliation_epsilon = 0`, operator review before any non-zero; demo/paper excluded) — `mine-node.md:85-107`.
- **KSA (1.4):** 5 escalate-only levels `GREEN/YELLOW/ORANGE/RED/BLACK`, book profiles select behavior, only operator resurrection de-escalates; **level enum non-configurable; the target-level/effects matrix is left OPEN — do not invent it** — `mine-node.md:109-115`.
- **Records (1.5):** one SQLite-WAL writer over five streams (`veto_ledger, trade_journal, book_journal, ksa_audit_log, correlation_ledger`); append-only via DB triggers; **decision + required evidence committed in one transaction**; `synchronous=FULL` — `mine-node.md:117-122`.
- **Registry (1.6):** census 25 variables / 10 formulas / 8 architecture slots; each value carries configurable, DEC-link, source_status, constraints; null/unresolved values block — `mine-node.md:124-130`.
- **Operator powers (1.7):** RPC-HTTP/JSON, authenticated by **local-trusted-channel operator OS identity only; backend evidence can never authorize a power**; the three named powers = **resurrection, periodic (Sunday) review, promotion-pull** (in the old build `a1_resurrection`/`sunday_review`/`promotion_pull` were explicit unsupported *stops*) — `mine-node.md:132-141`.
- **Capacity/latency (1.8):** capacity micro-bench measures durable-commit latency through the real Records path; drivers = tick fan-out by pairs, labeler compute per snapshot, durable-commit rate, sync egress, archive growth/day, postgres read concurrency. **Latency budgets recorded as evidence (configurable): tick→MIS ceiling 35 ms; order path 10 ms (min, non-configurable) – 45 ms; end-to-end tick→order 100 ms; hot retention ~14 days; roster_capacity 6 vs max_concurrent_live_bots 3.** Several ops slots deliberately unresolved (`sync_interval`, `sync_backlog_alert_fraction`, `sync_heartbeat_cadence`) — `mine-node.md:143-156`.
- **Deployment/ops (2):** two systemd services via one `supervised_node_runner.py`; hardening `Restart=on-failure`, `RestartSec=5s`, `StartLimitBurst=3/StartLimitIntervalSec=60`, `DynamicUser=true`, `NoNewPrivileges=true`, `PrivateTmp=true`, `ProtectSystem=full`, templated prefix; secrets via **systemd-creds** only, references never values, cold-start returns unresolved metadata only, redaction markers; pinned stack (apsw ≥3.53.3.1, PostgreSQL 18.x [backend only], DuckDB 1.5.x per-process, pyarrow==25.0.0, cTrader client from spotware/openapi-proto-messages); typed failure surfaces (`VERIFICATION_MISMATCH, BACKEND_INGEST_FAILURE, SYNC_BACKLOG_ALERT, UNRECOVERABLE_GAP, SCHEMA_MISMATCH, MONEY_ENCODING_VIOLATION, AUTH_FAILURE, TRANSPORT_ERROR`); trading→backend CT-SYNC-01 v2 durable+content-verified ACK — `mine-node.md:160-204`.
- **MIS + ML (3):** 8 ratified labelers (6 rule-based: identity, spread-state, gap-event, feed-state, SQS, degraded-sensors; 1 fitted `liquidity_stress_v1`; 1 trained `regime_classifier_v1` whose model_family is literally `"..._placeholder"`, training_location `"unresolved"` — no ratified architecture/hyperparameters/label-gen). MIS-Live: CT-MIS-01 snapshot from bound labeler versions, **compute-once fan-out to Book + KSA over an in-process synchronous dispatcher (no queue/bus/RPC/HTTP/file-sync/cross-node hop)**, deterministic SQS weighted-floor with hard-block flag, degradation-visibility projection. MIS-Archive: Parquet temp-write-then-rename, reader visibility gated on manifest-hash+row-count. **Shadow lane = ratified CONCEPT ONLY, not built** (old Story 3.9 backlog; no model shadow-deployed). Recovered non-authority models — **Kronos, HMM, BOCPD, MS-GARCH** — carry `NO_CURRENT_AUTHORITY`; adoption requires fresh ratification + parameter identity + training + shadow evidence + L10 recert. **Training is an OFFLINE job** — may seed RNG and record the seed; no-ambient-time/randomness binds the live runtime; a trained artifact has zero MIS authority until admission + L10 recert; training location (local GPU vs cloud) unresolved — `mine-node.md:208-253`.
- **backend-node = superseded (4/5):** the server-side twin (PostgreSQL 18.x standing store: Class-1 CDC replicas, Class-2 stream replicas, certificates corpus, attribute history, sync watermark/ack ledger, catalog metadata; exam job-runners; MIS-Archive; Dukascopy acquisition). **The two-node + PostgreSQL-server standing store + trading↔backend CT-SYNC-01 sync is DEAD under "no DB server anywhere in V1" (FR-016, NFR-10, L30).** Only the placement/authority shape survives. Dukascopy acquisition survives conceptually in FR-017/FR-042 — `mine-node.md:266-298`.
- **Naming tension flagged:** §2 lists "MIS" among deferred consumer products (ADR-0011) while §6 has the node host MIS publication — **MIS-Live (node-runtime market intelligence for Book/KSA) is a distinct thing** — `mine-node.md:255-262`, `333-336`.

### B2. addendum.md — operator dictation depth
- **Form-factor:** earlier concept = backend node + database; current direction = **local desktop app + trading node on a VPS** so trading runs continuously and independently of the operator's machine — `addendum.md:6-14`.
- Agent workers may run locally or in server sandboxes (Modal/E2B class named — direction, no evaluation) — `addendum.md:11-14`.
- **Old-version lineage (3 generations):** (1) `Documents/Claude/QMX-discussion` — very old, planning-only, light-mine; (2) the GitBook (`elios-1.gitbook.io/qmx`) — the intermediary, mostly the trading node + rewrite of risk/position sizing; (3) `Documents/QMX` — the later better old version with an even more stable trading-node design, predates QMF — `addendum.md:52-68`.
- **Trading-node operational intensity:** MIS ML instances need training, **shadow-rollout** before promotion, periodic retraining — the concrete reason the DevOps lens is primary — `addendum.md:80-86`.
- GitBook frames QML conservatively (interfaces open under GAP-0013); `docs/` carries the richer QML increment; PRD treats **GitBook as stable governance baseline for risk/Book/BMS, `docs/` authoritative for QML** (L2/L37) — `addendum.md:88-95`.

### B3. correlate.md — the D-decision map (mined-into-PRD, with sources)
This file is the compact routing register (D1-D27) folding old-node mining into the PRD, plus a "confirms" table and a "deprecated/dead" list. Node-relevant D-rows:
- **D1 (MIS disambiguation):** rename §2 row to "consumer MIS product"; name the node's **MIS-Live** in §6 — `correlate.md:49`.
- **D5a:** operator power set = `resurrection` (only de-escalation authority), `periodic review`, `ratification/promotion-pull` — `correlate.md:51`.
- **D6a:** promotion click re-executes preconditions server-side at click time; node-initiated pull idempotent by artifact key; lands `ADMITTED` distinct from activation — `correlate.md:57`.
- **D9 startup/recovery ordering; D10 reconcile-explained-delta; D11 rate limits first-class; D12 fail-closed stand-down + drain-before-enforce; D13 MIS-Live + shadow lane; D14 always-on evidence tier (placement not deployment mandate)** — `correlate.md:81-85`, `correlate.md:87` (D14 wording), sources cite mine-node §1.1-3, mine-planning A1-A6.
- **D23:** one observability substrate two consumers; external plane zero-authority (DEC-0112, DEC-0041) — `correlate.md:109`.
- **D24:** install/start/stop/backup/recover from one canonical checkout; restart-on-failure with burst cap → stand-down — `correlate.md:110`.
- **D25b:** node-phase position-safety ratification cluster (four questions, = PRD row 12) — `correlate.md:118`.
- **D25c:** atomic decision+evidence commit vs store seam (= PRD row 13) — `correlate.md:119`.
- **D27:** QMA data-egress pull-only boundary (track input) — `correlate.md:120`.
- Confirms (already covered, some stricter): four-outcome venue law — **the corpus clears the UNKNOWN block only on an explicit typed `resolve_unknown`, never on a reconciliation verdict** — `correlate.md:131`; treasury cycle adds a fourth boundary kind `paper_epoch_reset` — `correlate.md:135`; news blocking stricter (dated per-instrument currency-exposure records, symbol parsing prohibited, widen-never-shrink) — `correlate.md:142`; node latency budgets are **evidence, not spine constants** — `correlate.md:149`.
- **Deprecated/dead (do not re-mine):** backend-node PostgreSQL standing store + two-node CT-SYNC-01 topology — `correlate.md:165`; four-node microservices topology — `correlate.md:166`; old contract namespaces (CT-BMS-*/CT-BOOK-*/CT-MIS-*/CT-SYNC-* etc., IDs do NOT line up, never cite an old ID as current) — `correlate.md:168`; DPR/PRS merit ranking, tiers, capital slots, slot auctions, opinion-weighted sizing — `correlate.md:171`; WF1/WF2/WF3 states, paper-to-live redemption loop, auto live→demo demotion — `correlate.md:172`; **`TIGHTEN` kill-switch level / "trade half-size through bad conditions" — explicitly dead (cites DEC-0019 in this doc)** — `correlate.md:173`; Examination Engine constants (6mo IS/1mo OOS/200 OOS trades/0.15R/1000 MC/PBO 0.25-0.50) — legacy scalper values, not corpus authority — `correlate.md:174`; recovered non-authority models — `correlate.md:178`; branch-lanes-as-evidence-classes — `correlate.md:182`; proof-shaped module style — `correlate.md:183`.
- Routing caution: node mechanics (pool sizing numbers, OAuth chains, migration rules, capacity-driver lists, systemd hardening, labeler catalog, SQS parameters) belong in `tracker/trading-node-notes.md`, not the PRD — `correlate.md:190-196`.

### B4. mine-planning.md — later old-version planning/standards layer (CARRIES list)
Grouped Phase-2 node design inputs (all old-ID traceback; nothing adopted):
- **A1** two-plane node + evidence-home + verify-before-purge sync ("sensing fans out; accounting concentrates"; hot node never blocks, one-way hot→evidence, backend-initiated re-request carries watermarks only, heartbeat watermarks) — `mine-planning.md:43-52`.
- **A2** startup recovery fixed ordering, everything a journal projection — `mine-planning.md:54-62`.
- **A3** reconciliation by explained-delta — `mine-planning.md:64-71`.
- **A4** connection-manager design + platform-rate-budget-fit (pool per binding, multiple connections per live account; **cTrader 50 req/s general + 5 req/s historical**; per-account command affinity; token-bucket; label fill attribution; clientMsgId correlation; OAuth refresh) — `mine-planning.md:73-82`.
- **A5** KSA transition barrier — quiesce/drain all connections before enforcement counts complete — `mine-planning.md:84-86`.
- **A6** fail-closed stand-down as an alive state; systemd Restart=on-failure + start-limit — `mine-planning.md:88-92`.
- **A7** observability tiering hot/warm/cold; **Prometheus + Grafana external, zero authority**; journal durable-commit latency a required hot-tier metric (GIL-contention canary, store-swap-trigger, capacity input) — `mine-planning.md:94-99`.
- **A8** notification firing set = sweep, re_seed, refund, KSA/kill-switch, supervision fail-closed; everything else console evidence — `mine-planning.md:101-104`.
- **A9** capacity model → minimum node spec (registry-owned, null until measured) — `mine-planning.md:106-110`.
- **A10** deployment + backup envelope (cloud/Linux target; node colocated near broker for latency; systemd-creds; SQLite db+wal+shm as one unit via backup API never file-copy; WAL never on network FS; RPO bounded by backup-age-minus-retention-overlap) — `mine-planning.md:112-119`.
- **B1** Treasury/cycle/rollover-sweep/seed/cap/kill-line model (cycle = seed→cap; compounding within a cycle only, knowledge persists; rollover-only sweep; closed book↔treasury boundary — only `sweep|refund|re_seed`; no automatic physical withdrawals; **kill line = floor that flips the book to paper until a cycle-boundary re_seed, fixed within a cycle**) — `mine-planning.md:123-131`.
- **B2** refund semantics (protective return after blocked/killed standstill of configurable duration T; dormant V1) — `mine-planning.md:133-136`.
- **B3** money-ladder sizing + cost-aware Kelly (daily loss budget re-derived at rollover, drains intraday; take = min(offer, trust-bounded cost-aware Kelly)) — `mine-planning.md:138-142`.
- **B4** position-safety cluster (= PRD row 12) — `mine-planning.md:144-151`.
- **C1** shadow rollout on the evidence node — `mine-planning.md:155-160`.
- **C2** labeler-materialization lane + disjoint source-class namespaces (live-recorded vs materialized-backfill in DISJOINT partition namespaces via a `source_class` key — a ready-made GAP-0048 fidelity primitive) — `mine-planning.md:162-168`.
- **C3** MIS labeler-catalog ratification discipline (trained/fitted/rule-based ratified explicitly; recovered models NO authority) — `mine-planning.md:170-174`.
- **D1** deep-history multi-source (Dukascopy + TrueFX + HistData; ≥5 years; Databento no spot FX; download→clean→maintain) — `mine-planning.md:178-184`.
- **D2** news-calendar multi-source redundancy + compilation invariants (Forex Factory JSON primary 2/5min; FMP/TE/FXStreet fallbacks; daily pre-trading-day refresh non-negotiable; **compilation = currency → ALL pairs containing it; session scoping may only WIDEN a block, never narrow it**; EODHD disqualified) — `mine-planning.md:186-193`.
- **E1** venue/platform/instrument three-axis identity — surfaces a modeling question: does QMF need a *platform* axis distinct from *venue* (differs from current CT-03 opaque `(venue, symbol)`)? — `mine-planning.md:197-205`.
- **F1-F5** terminal (console constitutionally-bounded control plane; click-time server-side revalidation; promotion evidence panel + human dedup; three settings scopes; per-bot dossier + auto placement) — `mine-planning.md:218-253`.
- **G1-G6** cross-cutting standards (behavior-anchored testing; **no-mock-data doctrine**; money-path + nondeterminism AST scanners; **atomic decision+evidence commit + single-writer-per-entity**; failure-register + operator-as-product-user; schema-evolution/migration-runner discipline) — `mine-planning.md:257-299`.

### B5. discovery-architecture-sessions.md — AD spine the node inherits
- Standing principle: everything downstream of QMF (trading node included) is built WITH QMF; **node runtime behaviour (doors, ledgers, counters, trigger matrices, kill-switch firing) deliberately EXCLUDED — QMF carries contracts and seams only** — `discovery-architecture-sessions.md:30`, `:37`.
- **AD-8** Clock injected at composition root, replay clock too, **nothing below the root reads the system clock**; three calendar kinds (market-hours/day-boundary/news) — `discovery-architecture-sessions.md:51`.
- **AD-9** broker identity is deployment configuration, never architecture; accounts carry roles (live/demo/paper-validation/paper-benched/prop-firm) — `discovery-architecture-sessions.md:52`.
- **AD-26** venue secret lifecycle (typed SecretRef, connection manager the only value-holder, one live refresher per credential, factory sandboxes never hold live secrets, credential-management UI is platform territory) — `discovery-architecture-sessions.md:75`.
- **AD-27** command stream = (VenueId, account); **five typed kinds** (place_order, cancel_order, close_position, close_all, amend_protection); four-outcome law; **command retry is prohibited**; reconciliation gates the command pipe only; fail-closed on outage — `discovery-architecture-sessions.md:76`.
- **AD-28** venue adapter contract: neutral port, four contracts CT-18/19/20/21, verify-or-refuse throughout, a measured daily-bar boundary mints a venue-scoped market-hours calendar identity; CCXT-class crypto slots in later — `discovery-architecture-sessions.md:77`.
- **AD-29** BMS account-facing, one per account serving many Books; Book binds exactly one BMS; Bot binds exactly one Book; world constant `live` for every V1 binding — `discovery-architecture-sessions.md:80`.
- **AD-30** templates as config artifacts; sections named `charter, footprint_requirements, money_rules, admission_bar, leash_grammar, capacity_and_sweep, exit_policy, control_policy, protection_windows, paper`; deferred-contract slots ship `pending(<gap>)` that pass registration and block live binding — `discovery-architecture-sessions.md:81`.
- **AD-33** Book owns exit policy; bot proposes risk-monotonic exits (close_full, tighten_protective_stop — direction+bound never a price); `requested_r` Book-resolved; `close_partial` not a V1 kind — `discovery-architecture-sessions.md:84`.
- **AD-34** `amend_protection` fifth command; never emulated by cancel-then-place; amend atomicity UNDOCUMENTED → verify-or-refuse (single-sided the only legal V1 path); **V1 dynamic SL/TP = move-to-breakeven ratchet only** — `discovery-architecture-sessions.md:85`.
- **AD-35** paper = Book-level dated mode; no Bot twins; one active paper-routing target per binding; `execution_target` resolved once at intent mint; a reset mints an operator-signed paper epoch; paper P&L never becomes Treasury cash — `discovery-architecture-sessions.md:86`.
- **AD-36** kill switch (global, stops all NEW trading incl. paper, escalates automatically, de-escalates only by a human, **effect chosen by node severity policy**) vs kill line (per-Book capital floor, auto-flattens, stands Book down); exit-preservation invariant; flatten authority assigned — `discovery-architecture-sessions.md:87`.
- **AD-37** same-tick priority ranks: 0 operator > 1 protection > 2 BMS/Book forced flats > 3 fast invalidation > 4 ordinary bot exits/amendments; BMS-declared per stream; cross-stream ordering a declared non-guarantee — `discovery-architecture-sessions.md:88`.
- **AD-38** protection windows (news/daily_dead_zone/session_handover_buffer); blocks new entries live AND paper; instrument scope via dated currency-exposure records; widen-never-shrink; **all widths/anchors/buffers configurable UI-editable with NO spine value** — `discovery-architecture-sessions.md:89`.
- **AD-39** SQS V1 = historical avg session-window spread ÷ current live spread; per-class threshold/hysteresis/outlier guard; sensor computes, transport carries, Book door decides; live binding requires a present baseline — `discovery-architecture-sessions.md:90`.
- **AD-40** R one relationship three faces frozen at admission; numeraire USD system-wide; margin sizing decided-deferred — `discovery-architecture-sessions.md:91`.
- **AD-41** "stop-out" banned (venue margin liquidation = `venue_liquidation`; breaker input = `qualifying_loss_exit` realized_r ≤ −q, q UI-editable ~1R); bench counter a read-time fold; alpha decay ships as evidence primitives only, math deferred, collection starts now — `discovery-architecture-sessions.md:92`.
- **QMF explicit node-territory (Deferred table):** kill-switch trigger→level→effect matrix, level state machine, Book/BMS runtime, MIS consumer boundary, pool/retry/health constants — all node authority, do-not-default, corpus numbers reconfirm-grade only — `discovery-architecture-sessions.md:102`; news-calendar auto-sync/UI/cron, full observability/monitoring design, deployment topology/infra/ops envelope, crypto calendar — later/node/ops — `discovery-architecture-sessions.md:108`; numeric latency/perf budgets await measured baselines — `discovery-architecture-sessions.md:109`.
- **QL-10** QML builds BEFORE the trading node, may build alongside QMB; natural order QMF core → QML+QMB → trading node — `discovery-architecture-sessions.md:162`.

### B6. sweep-signoff-mechanics.md — node-relevant residue
- The sign-off flip left **DEC-0049 open** at the time (detector notify-vs-mutate authority) — the one open ledger row — `sweep-signoff-mechanics.md:80-82`, `:214-216`. (Subsequently ruled ratified at sign-off — see PART C.)
- **SQS-formula memlog conflict** (SRC-03 memlog entry 118 "SQS formula stays open pending re-understanding pass" vs risk sitting GAP-0043/DEC-0153) — surfaced, unresolved — `sweep-signoff-mechanics.md:220-222`.
- Deferred gaps stay deferred: GAP-0016/0017, GAP-0048 content, GAP-0049 remain non-blocking, non-authorizing — `sweep-signoff-mechanics.md:223-225`.

---

## PART C — _docwork (gaps, enhancements, ledger, stage_state, coverage-exceptions)

### C1. gaps.yaml — node/live/ops gaps
- **GAP-0013 latency (answered):** "What concrete latency, throughput, memory, startup, persistence budgets under the ~40-bot scenario?" → **measure-then-budget, no invented numbers**; benchmark speed+peak memory at 10/100/200; first measurements = fingerprinted (OS, CPU-class) baselines gating tier-2; only stated constraint qmf-core import <1s (DEC-0111, AD-13). Numeric budgets intentionally await first baselines — `_docwork/gaps.yaml:122-130`.
- **GAP-0035 secret lifecycle (answered, AD-26/CT-21):** SecretRef references never values; binding identity (VenueId, AccountId, role, world); connection manager the only in-memory value holder via injected SecretStore; exactly one live refresher; rotate-before-discard, a failed store blocks the command pipe while sensing continues; compromise recovery a documented drill anchored on cTID re-authorization; testing uses demo credentials only — `_docwork/gaps.yaml:342-350`.
- **GAP-0036 order-state machine / flatten authority (answered, AD-27/CT-19/20):** four-outcome law; UNKNOWN blocks new commands until explicit `resolve_unknown`; reconciliation verdicts reconciled|drift|unknown gate the command pipe only; **outage fail-closed, command retry prohibited, retry/pool constants stay do-not-default node values; flatten authority assignment left to the risk/node sittings** — `_docwork/gaps.yaml:352-360`.
- **GAP-0037 first broker / trendbar basis (answered):** broker identity deployment config (IC Markets operator intent, not a framework commitment); **17:00-NY boundary and BID-derived trendbars demoted to 2013-forum-grade and NEVER hardcoded — adapter measures per broker at first connection + continuous monitor** — `_docwork/gaps.yaml:362-370`.
- **GAP-0041 paper scope (answered, AD-35):** paper a Book-level dated mode; no Bot twins; every trigger declares routes-to-paper|blocks-paper (market-risk controls block paper too; capital/authority controls route to paper); one active paper-routing target per live binding; `execution_target` resolved once at mint; **paper money frozen evidence, configurable starting balance, reset mints an operator-signed paper epoch, paper P&L never becomes Treasury cash and never buys a seat; return to live automatic only for clocked mechanical causes, anything touching real money needs an operator signature**; decay comparison R-denominated under `cohort_key` — `_docwork/gaps.yaml:402-410`.
- **GAP-0042 news control (answered, AD-38); GAP-0043 SQS (answered, AD-39); GAP-0044 R/sizing/FORM-0006 (answered, AD-40); GAP-0045 stop-out/bench/alpha-decay (answered, AD-41); GAP-0046 same-tick priority (answered, AD-36/37)** — `_docwork/gaps.yaml:412-460`. GAP-0043 records the SQS thresholds as evidence-only (0.60/0.55/0.45/0.65/0.50, band 0.05, 4-sigma) — `gaps.yaml:428`.
- **GAP-0048 backtesting content (DEFERRED):** fidelity taxonomy VALUES, forex fill/slippage/financing calibration content, parity contracts, **simulated-time typing (unlocks world=simulated)**; PARTIALLY closed by QMB (seams ruled: lowest-fidelity-wins, mixed-fidelity comparison a typed refusal, optimistic taint on every fill, calibration-not-invention) — `_docwork/gaps.yaml:473-481`.
- **GAP-0049 search-quality threshold (DEFERRED, answer null):** SR* definition/units/population/attempt-budget effect; raw material accrues by construction — `_docwork/gaps.yaml:483-491`.
- GAP-0016/0017 (causality registration gate + attempt counter) deferred per DEC-0121 — `_docwork/gaps.yaml:152-171`.

### C2. enhancements.yaml — node/live/ops ENH residue
The 71 ENH entries are documentation-factory increment corrections (all `status: deferred`/`pending`); ENH-0005 is unrelated (occurrence record) — `_docwork/enhancements.yaml:26-30`. Node-relevant residue:
- **ENH-0020:** CT-14/26/15 gained a schema-level `node_ops_pointer / still_open` note holding the residual — **object-key layout, RPO/RTO, key custody, cTrader wire schema** — rather than dropping it silently — `_docwork/enhancements.yaml:101-104`.
- ENH (line 33): the operational-clock-rules exclusion (chrony/slew-only/drift-bands/**no-trade-before-sync**) routed to `time-audit-devops.md` — `_docwork/enhancements.yaml:33`.
- ENH (line 328): the 57-rule DevOps time-audit condensed into an 8-row **NODE/OPS obligations table** in `runbook.md` — `_docwork/enhancements.yaml:328`.

### C3. ledger.yaml + stage_state.yaml — node rows
- **DEC-0049 (now ratified at sign-off):** "Automatic detectors may act, but only through the existing entry-blocking control vocabulary, scoped to the narrowest affected subject — instrument, currency cohort, Book, venue/broker, or system-wide — never wider... and never through any act on positions or exits (the L39 exit-preservation invariant holds). The response posture is operator-configurable and UI-editable per L38: inform when reachable, pause when not. Detector-raised pauses clear under the existing control rank/authority rules; these are rare, black-swan-class events." — `_docwork/ledger.yaml:458-463`.
- **DEC-0093 DPR/PRS revival = DEAD** ("operator marked both concepts legacy-only and warned against reviving them") — `_docwork/ledger.yaml:876-881`.
- **Node boundary ruling (DEC-0142):** `tracker/trading-node-notes.md` is the standing cross-session node ledger, referenced as a pointer, never absorbed; node order-path/flatten material kept out of QMF docs — `_docwork/stage_state.yaml:100`.
- Venue increment left residual `node_ops_pointer` items (object-key layout, RPO/RTO, key custody, cTrader wire schema) — `_docwork/stage_state.yaml:103`.
- Risk increment: kill switch/kill line named apart; flatten authority assigned; SQS adopted; USD; dead zones both kinds; DPR/PRS/paper-twins/blackout-simulator stay dead — `_docwork/stage_state.yaml:107`, `:90-92` (map addendum).
- Sign-off notes: DEC-0049 ruled at sign-off (scoped entry-blocking detector pause, L39 preserved, UI-editable per L38); ENH batch of 71 deferred post-V1 — `_docwork/stage_state.yaml:32`, `:183`.
- (Note: `sweep-signoff-mechanics.md` line 173 says constitution L29 stays load-bearing for the deferred gaps — the provisional-artifact caveat remains for node-phase gaps.)

### C4. coverage-exceptions.yaml
Nine chunks excluded as tool-output/workflow-diff/no-durable-decision (SRC-02 chunks + SRC-02-C0039) — none node-substantive — `_docwork/coverage-exceptions.yaml:1-19`.

---

## PART D — tracker (map.md, trading-node-notes.md, tickets)

### D1. trading-node-notes.md — the standing node ledger (verbatim rulings)
Standing instruction: anything about the trading node in ANY session gets noted here; append-only, dated — `tracker/trading-node-notes.md:3`.

Venue sitting (2026-08-20) facts the node inherits:
- Demo and live are separate cTrader hosts; **serving both simultaneously REQUIRES two connections (one demo, one live), each carrying unlimited accounts of its kind** — the mechanism for the paired-demo fail-safe (K-27) — `tracker/trading-node-notes.md:8`.
- Rate limits 50/5 req/s per connection; no documented ban/backoff → conservative throttle, typed transient refusals — `tracker/trading-node-notes.md:9`.
- **No server clock on the Open API — receive-time stamping mandatory; heartbeat every 10s; weekend maintenance windows exist** — `tracker/trading-node-notes.md:10`.
- Depth (L2 quote book) IS available; no L3 trade tape — `tracker/trading-node-notes.md:11`.
- **D1 bar boundary + bar price basis NEVER hardcoded** — first-deploy empirical check + continuous monitor, stored per-broker; ~1-week warm-up before live — `tracker/trading-node-notes.md:12`.
- Token lifecycle: access token ~30 days; refresh token NEVER expires until used or cTID re-authorized (compromise-recovery anchor); in-band (ProtoOARefreshTokenReq) or REST — `tracker/trading-node-notes.md:13`.
- Three independent numeric scale systems (1/100000 market prices; raw-double execution prices; per-message moneyDigits exponent on nine messages; volumes in cents); LightSymbol carries no scaling metadata — `tracker/trading-node-notes.md:14`.
- No direct equity field — equity derived (balance + quote-ccy unrealized PnL) (K-54) — `tracker/trading-node-notes.md:15`.
- **Dead zone:** ~45-min relax around session handover — pauses TRADING ONLY; data streaming continues; NOT kill-switch logic — `tracker/trading-node-notes.md:18`.
- Broker identity = deployment configuration; "account IDs are enough"; IC Markets operator intent, deliberately not a framework commitment — `tracker/trading-node-notes.md:19`.
- First deployment runs a warm-up week: empirical checks (timestamp unit, D1 boundary, BID-bar reconciliation, pip formula) with loud refusals — `tracker/trading-node-notes.md:21`.

Contradictions left open on the record (for node/risk sittings):
- **Latency:** operator ~50ms full-round-trip direction vs GitBook 35/10-45/100ms budgets — GAP-0013 forbids invented numbers; the **six-stage latency decomposition** (tick received → evidence write → indicator update → decision → risk evaluation → order submitted) recorded as **AD-13 rungs WITHOUT numbers until measured** — `tracker/trading-node-notes.md:24`.
- **Paper-mode scope:** fail-mechanism-only (K-25) vs standing-state feeding alpha-decay — risk-sitting item GAP-0041 — `tracker/trading-node-notes.md:25`.
- MIS consumer boundary: Book+KSA-only vs manifest-bounded bot consumers (C-01 REOPEN) — `tracker/trading-node-notes.md:26`.
- Pool sizing, retry constants, health thresholds: "do not default" standing; R-07 numbers RECONFIRM-grade only — `tracker/trading-node-notes.md:27`.

Order-path teaching (venue sitting round 3):
- The order path is a **chain of command** — "very many things can block a bot from trading": MIS (firing at startup), SQS gating, KSA, correlation ledger, BMS, Book doors, money rules — `tracker/trading-node-notes.md:30`.
- Audited vocabulary: **correlation ledger LIVE** (one of the five Records streams); **DPR + PRS DEAD (DEC-0093)**; **"MIS assembler" never existed** (operator's phrase was "MIS is an ML ensembler"); **"house of money" / "reverse house of money" NEVER FOUND** — a fresh design item if wanted, not a recovery — `tracker/trading-node-notes.md:31`.
- Order/data/startup mapped in `trading-node-order-path-study.md` — 15+ refusal classes on the order path; **startup reconciliation gates the COMMAND pipe only** (sensing/MIS flows from boot; K-39) — `tracker/trading-node-notes.md:32`.
- "Without the trading node, there is no QMX." — `tracker/trading-node-notes.md:33`.
- Secrets (AD-26): the surface is UI-driven — credential entry/management is a platform settings-panel concern; QMF carries only the reference-not-value seam — `tracker/trading-node-notes.md:35`.
- Crypto: CCXT-class, "crypto is not difficult"; cTrader stays on Open API — `tracker/trading-node-notes.md:36`.

Adapter corpus rules load-bearing (trading-node-corpus-brief.md):
- **K-42:** Connection Manager lives inside the Adapter and is the sole owner of platform sessions, token buckets, OAuth refresh, arrival stamping, fill attribution, reconnect, gap recovery — **no second cTrader client in MIS/BMS/Book/bot code** — `tracker/trading-node-notes.md:39`.
- Three-outcome order model ACCEPTED/REJECTED/UNKNOWN — timeout NEVER a rejection; reconciliation resolves UNKNOWN; startup reconciliation before any trading — `tracker/trading-node-notes.md:40`.
- Protection funnel: **MIS senses → KSA decides (escalate-only; human A1 de-escalates) → Adapter enforces as an effect**; flatten authority was explicitly unassigned at venue sitting, reserved as a human-authorized path (assignment landed in risk sitting) — `tracker/trading-node-notes.md:42`.
- Fills correlate by clientMsgId (≤100-char label); recovered fills commit through Records before the connection reports healthy — `tracker/trading-node-notes.md:43`.

Node-facing consequences of venue ADs (AD-26/27/28, gate-amended 2026-08-20):
- **The node (not the adapter) clears an UNKNOWN block, via explicit typed `resolve_unknown(command identity, resolution ∈ observed-accepted | observed-absent | operator-attested)`** — the block is per command stream = (VenueId, account), clears on resolution never on a reconciliation verdict — `tracker/trading-node-notes.md:46`.
- **The application injects and owns:** the submission deadline that triggers UNKNOWN, all retry/pool/health constants, the adapter's schedulable session duties (heartbeat/refresh/reconnect/monitors run on the app's scheduler), and the sink protocols (ObservationSink/JournalSink/RecordSink/SecretStore) — `tracker/trading-node-notes.md:47`.
- Protection commands (cancel/close/close_all) dispatch ahead of place_order on shared throttles; close_position/close_all carry a required typed scope (account | account-binding | instrument-within-binding) — **the node's kill path must state its scope** — `tracker/trading-node-notes.md:48`.
- Exactly one live refresher per credential (a workstation tool must never refresh a credential the VPS session owns — the refresh token dies on use) — `tracker/trading-node-notes.md:49`.
- Demo/paper evidence is role-scoped within world=live; sandbox-produced evidence carries provenance=sandbox and cannot merge into the operator store — `tracker/trading-node-notes.md:50`.

Risk sitting (2026-08-20) vocabulary rulings the node inherits:
- **KILL SWITCH = GLOBAL black-swan emergency:** stops ALL trading including paper; sensor-fed (MIS/SQS inputs); human de-escalates; operator phrased "cuts off actual connection" recorded as intent not bound; contract carries effects **suspend-new | drain | close-all, and which effect fires per severity is node authority** — `tracker/trading-node-notes.md:55`.
- **KILL LINE = per-Book capital floor** — a different thing; kill-line breach **auto-flattens that Book's scope (a 3am breach never waits for the operator)**; every other money boundary (rollover, sweep, re-seed, paper flip) leaves positions alone; the operator may flatten anything at any time (inalienable); **flatten authority now ASSIGNED** — `tracker/trading-node-notes.md:56`.
- BMS account-facing, one per account serving many Books; chain bot → Book → BMS → account; same-tick questions always account-scoped — `tracker/trading-node-notes.md:57`.
- News blackout INSTRUMENT-scoped, stops live AND paper entries on that instrument; would-have-been decisions journaled as suppressed-decision events — `tracker/trading-node-notes.md:60`.
- Dead zones: BOTH kinds (daily no-session band ~3h maintenance window AND per-handover ~45min buffers); new entries pause; exits/safety/data never blocked; widths configurable — `tracker/trading-node-notes.md:61`.
- **Fifth adapter command MINTED: amend_protection** (cTrader ProtoOAAmendPositionSLTPReq, CONFIRMED-PRIMARY, no cancel-replace; amend atomicity UNDOCUMENTED → verify-or-refuse); **V1 dynamic SL/TP = move-to-breakeven ratchet only**, risk-reducing, per-Book configurable — `tracker/trading-node-notes.md:62`.
- Bench counter counts stop-outs (~negative 1R); breakeven exits NEVER count; threshold per-bot configurable — `tracker/trading-node-notes.md:64`.
- SQS V1 = old ratio sensor adopted; hard-block lines per instrument class; hysteresis band; 4-sigma outlier guard; undefined ⇒ block; sensor computes, MIS transports, Book door decides — `tracker/trading-node-notes.md:65`.
- Paper Book-level (DEC-0070); multiple demo accounts; exactly one active paper-routing target per live binding; starting balance Book/family-scoped configurable — `tracker/trading-node-notes.md:66`.
- **Authority order for risk/position-sizing/live-trading: GitBook + trading-node docs (archive/recovery + Documents/QMX wiki); QMX-discussion's risk/sizing REPLACED — barred as a source there** — `tracker/trading-node-notes.md:70`.
- Numeraire USD system-wide — `tracker/trading-node-notes.md:71`.
- **Do not re-discuss trading-node internals with the operator; the corpus answers first, gaps second, new design only if all layers are silent** — `tracker/trading-node-notes.md:72`.
- Operator idea minted: the "prediction linter" — a static check showing whether a Book can actually register/execute a given bot, testable against demo in the UI — `tracker/trading-node-notes.md:74`.

### D2. map.md — node/VPS/topology/sync/bucket/kill-switch/MIS/paper/deploy entries (dated)
- Destination: QMF specified/factory-ready, **the trading node re-specified on QMF** — `tracker/map.md:10`.
- **Framework-vs-node split re-affirmed hard (2026-08-19):** kill switch, news windows, dynamic SL/TP, Book runtime behavior = trading-node/application territory; QMF carries only their contracts/seams — `tracker/map.md:30`.
- Foundation sitting AD-14 observability: correlation_id, health(), logs≠journals, Prometheus-class exportable — **stack choice = node/ops** — `tracker/map.md:31`.
- Operator leads banked (2026-08-20): **middle sync-server (Dropbox-like hub app↔node) + caching → ops sitting; MIS shadow-rollout = node-side pure Python** — `tracker/map.md:32`.
- **Live-money safety ruling — re-raise during trading-node spec sessions** — `tracker/map.md:61`.
- Bench/DPR/PRS dig (workroom/reference/10, for the node session): "benched" IS GitBook baseline; PRS = legacy Performance Rating Service, DPR = its rolling 10-day tier; current baseline 2 consecutive stop-outs bench a bot for the day (DEC-0032). **NODE-SESSION BLOCKERS: "stop-out" never defined; symbol `B` double duty; BENCHED lives in two namespaces** — `tracker/map.md:63`.
- **Storage architecture (proposed):** working Parquet archive on the workstation; **trading VPS runs the always-on tick recorder and syncs down; nightly backup to an object-storage bucket (B2/R2 class, ~$1-5/mo); no database server.** Backup is an INBUILT platform feature (historically backend-node's job). **Trading VPS exists by default; procuring it is Mubarak's side, core is Claude's** — `tracker/map.md:66`.
- **Kill switch specification — nowhere designed, incl. behaviour when it fires while the broker connection is down; the one component with unbounded failure cost** — `tracker/map.md:79` (resolved at contract level AD-36; behaviour stays node territory — `tracker/map.md:92`).
- Broker credential lifecycle + operational runbook: OAuth refresh rotation, secrets on the VPS, token expiry mid-challenge, **who flattens positions if the VPS dies** — `tracker/map.md:81`.
- FX time model: 5pm-NY rollover, week boundary, weekend gaps, triple-swap Wednesday, broker-server vs prop-firm DST desync — `tracker/map.md:80`.
- Session accord: two deployables (installable QMX app + one Trading VPS); middle node absorbed into the app (ML training ~quarterly in cloud sandboxes, shadow rollout); no central backtest engine — `tracker/map.md:50`.
- **Supersession (2026-08-20):** "while blocked, bots may continue in paper mode so alpha-decay data keeps flowing" is SUPERSEDED — a news blackout stops live AND paper entries on the affected instrument; the would-have-been decision is journaled instead — `tracker/map.md:92`.

### D3. tickets
- **002 qmf-minimal-core (closed):** operator dictation — heavy indicators (regime models, volatility forecasts, correlation matrices, ML inference) **live in the MIS**; kill switch news is PAIR-SCOPED; **paper trading is a STANDING STATE, not a waiting room, feeding ALPHA-DECAY sensing** (needs uninterrupted data points); promotion HUMAN-ONLY (Mubarak, daily); Books/BMS "very surgical, don't take for granted"; per-component data collection (what bots/Books/BMS/MIS/SQS/kill-switch each record); automatic detection with operator-set ranges; exit mechanisms "a whole world" (fast invalidation, dynamic SL/TP, correlation ledger) — `tracker/tickets/002-qmf-minimal-core.md:39-48`.
- **004 Trading node on QMF (OPEN):** "Re-specify the trading node (Books, BMS, bots, MIS/SQS, news, KSA, venue adapter) as a QMF application for the Trading VPS — using the GitBook as stable baseline and `archive/recovery/` deltas as candidates needing fresh ratification. Includes the parked live-money safety ruling (fixed-at-startup path, journaling, fail-closed unknowns)." — `tracker/tickets/004-trading-node-spec.md:11-12`.
- **005 Data architecture (OPEN, progress):** six layers L0-L5; stores-per-purpose (Parquet+DuckDB+SQLite-inbox; **PostgreSQL rejected**); ArcticDB NO for v1 (technical: transaction-time only, no valid-time axis); lineage graph-in-JSONL, graph DB deferred; **paper-twin permanently on for alpha-decay continuity**; auto-detection = operator-owned rules.yaml, flags notify but NEVER act; **keep ALL history; backup to a cloud bucket, nightly; news blackout systematic ±15 min, NOT the SQS**; recorders never stop — `tracker/tickets/005-data-architecture.md:16-18`. Sized for one operator, deployable on workstation + Linux VPS — `tracker/tickets/005-data-architecture.md:12`.
- **006 Spotware/broker (OPEN):** **IC Markets, likely swap-free (Islamic) account** — swap-free replaces overnight swap with an admin fee after N days, so the ledger's `financing` column models the fee not swap; confirm IC Markets cTrader demo+live both expose Open API; measure real tick-history retention; establish whether cTrader trendbars are BID- or mid-derived — `tracker/tickets/006-spotware-broker-setup.md:11-16`.

---

## PART E — QA trace (integration worktree node-inventory), node-territory

Consolidation of 23 per-epic L6 adjudications + machine battery against `integration@2c8d495`. **1,379 tests, 131 consolidated findings: 44 CONFIRMED, 64 UNPROVEN, 23 VERIFICATION-DEBT (4 critical, 48 high, 61 medium, 18 low)** — `QMX-worktrees/node-inventory/qa/_trace/proof_map.md:18-19`. All 44 CONFIRMED were fixed in Fix Round 1 (35 cards, all PROVEN) — the **64 UNPROVEN + 23 VERIFICATION-DEBT remain as verification debt** (not confirmed defects, but unverified — many node-facing).

### E1. proof_map.md — the 15 handoff P0/P1 assertions (node-facing verdicts)
Scoreboard: **0 PROVEN · 4 PARTIAL (4,8,10,13) · 1 UNPROVEN (5) · 10 FAILED** — `proof_map.md:47`. Not "broken in 10 places" — 10 assertions have at least one confirmed contradiction and the gate carrying them could not fail — `proof_map.md:49-53`. Node-facing:
- **#5 human promotion — UNPROVEN:** the human-only signer (Story 2.3 AC1, qmf-registry L21/L106, SCN-0007) was **deliberately not asserted** on a reading of DEC-0116 the authorities do not support; `PromotionCard.sign` is exported and never called with a non-human signer; "can an agent mint a card `authorize_live_promotion` accepts?" is unanswered; RESULTS reports P0-5 PASS (QMX-F045; CT-13 promotion event separately untested QMX-F046) — `proof_map.md:35`.
- **#8 charter doors / R frozen — PARTIAL:** full-loss half green; frozen-money-face half not (QMX-F068) — `proof_map.md:38`.
- **#9 no control blocks a risk-reducing act — FAILED (fixed FC-01):** `check_exit_preservation` had no caller; `resolve_execution_target` act-blind (QMX-F001/F002) — `proof_map.md:39`.
- **#10 venue UNKNOWN blocks (venue,account) stream — PARTIAL:** strong on a single stream but **granularity untested in both directions (QMX-F062)** — a whole-connection block and a submitting-binding-only block both pass every test — `proof_map.md:40`.
- **#6 sealed holdout at every boundary — FAILED (fixed FC-06):** seal consulted only caller-supplied `at` (QMX-F006); Epic-21 admission door untested (QMX-F091) — `proof_map.md:36`.
- **#7 cross-world reads + world=simulated refuse — FAILED (fixed FC-02):** nested-config replay-clock bypass reachable from CLI (QMX-F003) — `proof_map.md:37`.
- Machine battery: **ambient-scan FAIL** (download.py reads wall clock below composition root, QMX-F018, fixed FC-14); Skylos grade C+ (77), quality 8/F, security/secrets/ai_defects A+; coverage qml 65.96% / qmb 66.46% branch vs 80% floor — `proof_map.md:96-101`.

### E2. findings.csv — node-territory rows (id | epic | severity | status | one-line)
CONFIRMED (all fixed Fix Round 1):
- **QMX-F001 | E10 qmf-risk | critical | CONFIRMED** — `check_exit_preservation` has no caller; L39 exit-preservation enforced nowhere — `QMX-worktrees/node-inventory/qa/_trace/findings.csv:2`.
- **QMX-F002 | E10 qmf-risk | critical | CONFIRMED** — `resolve_execution_target` is act-blind under a BLOCKS_PAPER control; exits either blocked (L39 violation) or resolve no target (CT-24 gap) — `findings.csv:3`.
- **QMX-F007/F008/F009 | E6 qmf-data ingest | high/high/medium | CONFIRMED** — dukascopy/calendar_feed/ingest bare transport calls raise instead of returning a typed refusal; a calendar transport outage produces no journal entry and no alarm — `findings.csv:8-10`.
- **QMX-F018 | E18 qmb/data | high | CONFIRMED** — `download.py:127` reads `datetime.now` below the composition root; ambient-scan FAIL — `findings.csv:19`.
- **QMX-F020 | E8 qmf-venue | high | CONFIRMED** — `observation_journal_event_type` raises `ValueError` on a non-ObservationKind — `findings.csv:21`.
- **QMX-F109 | E8 qmf-venue/E1 qmf-core | medium | CONFIRMED** — `SecretRef.try_create` enforces ZERO opacity checks; CT-21 requires construction-time opacity refusal (never encoding venue/broker/account/environment/key) — `findings.csv:24`.
- **QMX-F023 | E8+E10 | medium | CONFIRMED** — neither qmf-venue nor qmf-risk ships a FAILURES.md (NFR-11) — `findings.csv:25`.
- **QMX-F025 | E8 qmf-venue | medium | CONFIRMED** — qmf-venue ships no examples/ (L27) — `findings.csv:27`.
- **QMX-F027 | E5 qmf-data-backup | medium | CONFIRMED** — backup copy_export/restore route an adapter refusal into `unpersistable` which RAISES on reserved key "reason" — `findings.csv:29`.
- **QMX-F004 | E18 qmb/data | critical | CONFIRMED** — download discards bid/ask money; no scaled-integer money reaches the raw archive after download-once — `findings.csv:5`.
Node-facing UNPROVEN (NOT fixed — verification debt):
- **QMX-F045 | E2 qmf-registry | high | UNPROVEN** — human-only promotion signer never asserted; `PromotionCard.sign(signer="agent:...")` never tested — `findings.csv:47`.
- **QMX-F046 | E2 qmf-registry | medium | UNPROVEN** — CT-13 promotion event (card fp1 + correlation_id only) entirely unverified — `findings.csv:48`.
- **QMX-F062 | E8 qmf-venue | high | UNPROVEN** — UNKNOWN block proven on exactly one stream; CT-19 (venue,account) granularity untested both directions (whole-connection vs submitting-binding) — `findings.csv:64`.
- **QMX-F063 | E8 qmf-venue | high | UNPROVEN** — CT-18 amend-atomicity verify-or-refuse rule has ZERO tests; dual-side amend refusal never driven — `findings.csv:65`.
- **QMX-F064 | E8 qmf-venue | medium | UNPROVEN** — Spotware/Twisted SDK ban, secret-scan gate, undeclared order-parameter refusal, boot sequence-reset all untested — `findings.csv:66`.
- **QMX-F067 | E10 qmf-risk | high | UNPROVEN** — five Epic-10 gaps: colliding-action collapse rank winner; window retro-invalidation; fingerprinted population; Layer-2 demo/paper shakedown never called; cardinality rules (Bot↔Book↔BMS↔account) untested — `findings.csv:69`.
- **QMX-F068 | E10 qmf-risk | high | UNPROVEN** — frozen-money-face R at admission proven only on a function the door path is never shown to call — `findings.csv:70`.
- **QMX-F069 | E10 qmf-risk | medium | UNPROVEN** — refusal-register completeness unfalsifiable; storage-failure-blocks-dispatch proven by passing the failure in, no happens-before (journal-before-dispatch) observed — `findings.csv:71`.
- **QMX-F053/F054/F055 | E4 qmf-calendar-forex | medium/medium/low | UNPROVEN** — TZPATH never observed; get_provider/register_forex_17ny not-ready branches on an unverified tzdb never executed; Swap-Wednesday not modeled (V1 swap-free) — `findings.csv:55-57`.
- **QMX-F056/F057 | E5 qmf-data-backup | medium | UNPROVEN** — backup boundary refusal-category set silently shrunk; int64-ns-verbatim-through-a-later-calendar-identity round trip never constructed — `findings.csv:58-59`.
- **QMX-F085 | E18 qmb/data | medium | UNPROVEN** — verify/gap-check never exercised over the rooms; **licence gate is an oracle-from-implementation; the four-state licence taxonomy never pinned** — `findings.csv:87`.
- **QMX-F030 | E17 qmb/execution | medium | CONFIRMED** — slippage `del seed`; AC6 stochastic reproduce clause has no implementation (blocked OR-11) — `findings.csv:32`.
- **QMX-F102 | E5 qmf-data-backup | low | UNPROVEN** — RPO/RTO/retention-depth/restore-verification-cadence/encryption-key-custody/object-storage-provider/object-key-layout **left at the node/ops sitting by DEC-0118**; behavioural residue green — `findings.csv:104`.
VERIFICATION-DEBT (node-facing owners):
- **QMX-D008 | E8 qmf-venue | high** — 15 missed clauses incl. CT-19 stream granularity, CT-18 amend atomicity, Spotware/Twisted ban, boot sequence-reset, five schedulable duties, continuous re-verification, venue-managed trailing, retry-after mapping — `findings.csv:118`.
- **QMX-D010 | E10 qmf-risk | high** — 19 missed clauses; 107/107 pass with an empty findings file; the two cross-cutting gates (P0-9, R-009) mechanized as assertions that cannot fail — `findings.csv:120`.
- **QMX-D002 | E2 qmf-registry | high** — CT-13 promotion event, human-only signer, signed-record immutability, treasury-boundary-event reserved kind untested; two permanently-red probes — `findings.csv:112`.
- **QMX-D005 | E5 qmf-data-backup | medium** — 8 missed clauses (backup) — `findings.csv:115`.
- **QMX-D006 | E6 qmf-data source intake | medium** — 7 missed clauses (recorder WriterId, bid/ask timestamps) — `findings.csv:116`.

### E3. operator-rulings-needed.md + rulings-corpus-verdicts.md — verdicts binding the node
Twelve open rulings; 7 closed by corpus, 5 residue for operator — `qa/_trace/rulings-corpus-verdicts.md:1-13`.
- **OR-01 (bot tighten stop vs breakeven) — RATIFIED, Option A:** a bot may propose ANY risk-non-increasing tighten (never a price); **"breakeven only" governs the Book's own AUTOMATIC dynamic stop, a separate machine**; direction of travel is toward more bot exit authority (DEC-0185); cites `ct-23:26`, `qmf-risk.md:95/103` — `rulings-corpus-verdicts.md:16-49`.
- **OR-03 (replay-clock exhaustion) — PARTIAL toward typed refusal:** `Clock` is a listed core CT-02 public seam, so CT-04's return-never-raise reaches it; residue is whether "script exhausted" counts as programmer error; fixed FC-32 in the Option-B direction — `rulings-corpus-verdicts.md:79-108`. (The **no-ambient-clock invariant binds the live node runtime**, AD-8.)
- **OR-06 (CT-33 mint relocation) — RATIFIED, Option A:** CT-33 `wiring_status: defined-unwired` is current; the shipped `qml.register_bot_definition` is unauthorized; **the mint moves to the composition root (QMB / the host), AD-25 root-mints pattern** — the node as host holds the WriterId and mints records, the pure library never does; cites `ct-33:9`, `ct-33:6`, `epics.md:2697` — `rulings-corpus-verdicts.md:174-203`. Fixed FC-05 (removed; mint built later at proper place) — `FIX-LEDGER.md:18`.
- **OR-11 (slippage seed) — PARTIAL, hybrid:** keep the seed threaded (do not `del`); **no ambient randomness — the invariant binds the live runtime**; an offline trainer may seed and record; do NOT build a stochastic model or pin a derivation now (GAP-0048); mark R23 deferred/UNPROVEN never green — `rulings-corpus-verdicts.md:333-364`. Fixed FC-30 (seam plumbed, draw stays UNPROVEN-by-design) — `FIX-LEDGER.md:43`.
- **OR-07 (financing → CT-13 event type) — RATIFIED, Option A:** map financing onto `risk transition` with a payload marker, following the treasury-boundary precedent (sweep/refund/re_seed/paper_epoch_reset already map there); `ct-13:19` — `rulings-corpus-verdicts.md:207-235`. Node treasury.
- **OR-05 (backup boundary refusal categories) — RATIFIED, Option A:** CT-14/CT-26 boundary categories are exactly {storage failure, policy rejection}; a cross-world restore read is a policy rejection (DEC-0117) — `rulings-corpus-verdicts.md:143-170`.
- **OR-02 (sweep = trial) — RATIFIED, Option B;** OR-04 (`logic/` admissible, `host/` impure → FC-17); OR-08/09 (door parity); OR-10 (Skylos gate numbers); OR-12 (qmf-structure deferrals) — `rulings-corpus-verdicts.md:53-77`, `112-141`, `239-329`, `368-402`.

### E4. FINAL-REPORT.md + FIX-LEDGER.md — what was proven, and node-deferred items
- **All 35 fix cards done and PROVEN** against `integration`; `poe check` fully green (3,932 passed, 86.86% coverage, all four tier-1 scanners clean); QA Battery + Skylos green on the final push (`e874256`); `main` moves only by the operator's squash-merge click — `QMX-worktrees/node-inventory/FINAL-REPORT.md:3-6`, `:48-74`, `:102-107`.
- Node-facing fixes now landed: FC-01 (L39 exit-preservation guard now called + exit intents survive BLOCKS_PAPER) — `FIX-LEDGER.md:14`; FC-05/OR-06 (unauthorized bot-register removed; **mint to be built later at the proper composition root**) — `FIX-LEDGER.md:18`; FC-06 (seal on every read path) — `FIX-LEDGER.md:19`; FC-07 (three transport seams return typed refusals) — `FIX-LEDGER.md:20`; FC-16/OR-03 (venue function typed refusal, 60-function boundary sweep) — `FIX-LEDGER.md:29`; FC-17/OR-04 (impure host runner moved to `qmb.host` composition root; both wheels verified) — `FIX-LEDGER.md:30`; FC-19 (SecretRef opacity gate; AccountBinding revalidates) — `FIX-LEDGER.md:32`; FC-20 (qmf-venue + qmf-risk FAILURES.md, six NFR-11 fields) — `FIX-LEDGER.md:33`; FC-23/OR-05 (backup adapter context namespaced, returns storage failure) — `FIX-LEDGER.md:36`; FC-30/OR-11 (slippage seed seam) — `FIX-LEDGER.md:43`; FC-32/OR-03 (shared Clock protocol returns Result, exhaustion → unavailable-dependency refusal never raises) — `FIX-LEDGER.md:45`.
- **Explicitly deferred / still node-facing:** stochastic slippage DRAW stays UNPROVEN-by-design (no stochastic model exists) — `FINAL-REPORT.md:82-84`; three rounding mutants equivalent — `FINAL-REPORT.md:85-86`; Skylos dead-code ratchet stays at 80 pending first CI run — `FINAL-REPORT.md:95-97`; **the 64 UNPROVEN + 23 VERIFICATION-DEBT findings were out of this fix-round scope** and remain the verification debt for the node phase to inherit (esp. human-signed promotion signer F045, venue UNKNOWN stream granularity F062, amend-atomicity F063, frozen-R F068, Epic-10 cardinality/collapse F067) — `proof_map.md:35-45`, `findings.csv:47/64/65/69/70`.

---

## PART F — epics.md (what the foundation DID NOT build)

### F1. Epic list (23 epics, all foundation — no node epic)
E1 qmf-core; E2 qmf-registry; E3 qmf-data (evidence store & journals); E4 qmf-calendar-forex; E5 qmf-data backup/restore/verify; E6 qmf-data source intake; E7 qmf-indicators; **E8 qmf-venue port + cTrader adapter**; E9 qmf-structure; **E10 qmf-risk (Books, BMS & governance)**; E11 QML authoring; E12 QML protocol & conformance; E13 QMB substrate; E14 QMB run loop & replay backtest; E15 QMB orchestrator/ledger/concurrency; E16 qmb CLI & doors; E17 QMB fill/slippage/fee/financing ports; E18 QMB data management; E19 QMB reports; E20 QMB multi-route sweeps; E21 QMB optimization studies; E22 QMB robustness ladder; E23 QMB synthetic data — `_bmad-output/planning-artifacts/epics.md:315-425`. **No trading-node epic exists.** The node consumes E8 (venue) and E10 (risk) contracts but the node runtime is unbuilt.

### F2. Story text deferring node / live / later-phase
- **FR-050:** the bot runtime protocol "QMB **(and later the trading node)** hosts" — `epics.md:104`, `epics.md:2495`.
- **SC-04:** QML builds **before the trading node** and may build alongside QMB — `epics.md:240`.
- **Live is deferred:** "backtest, replay, and **(deferred) live** share identical loop code — the loop is never forked" — `epics.md:2890`.
- **Node/ops-sitting items (Epic 5 backup):** encryption is required but **object-storage provider, object-key layout, numeric RPO/RTO/retention targets, encryption key custody, restore-verification cadence are node/ops-sitting items** (DEC-0118, AR-37, FM-7) — `epics.md:1219`, `epics.md:1275`, `epics.md:1305`.
- **Hardened OS-level runtime confinement** (restricted tokens/job objects on Windows, seccomp-class on Linux) is **"a named deferred dependency of the node/platform sitting, and V1 does not wait on it"** — `epics.md:2622-2625`.
- **GAP-0048 gating pervasive:** world=simulated writes refuse; every fill carries the `optimistic` taint; no verdict-bearing backtest and no split-budget spend; calibration content (fill/slippage/financing) deferred, no rate invented — `epics.md:242`, `epics.md:3373`, `epics.md:3431`, `epics.md:3522`, `epics.md:4324`.
- Epic 8 built the venue seam the node's order path will drive: capability probe against the live demo venue as the earliest work unit; in-house proto at Spotware tag 91; secret lifecycle + connection manager + injected sinks; five command kinds; record-before-interpret + on-demand reconciliation; **UNKNOWN blocks the command stream until explicit reconciliation**; per-broker configuration for the ratified venue facts — `epics.md:1610`, `1639`, `1663`, `1691`, `1723`, `1755`, `1787`, `1815`.

---

## PART G — Contradictions and open items surfaced by the dig

### G1. Source-vs-source contradictions
1. **MIS placement (PRD-internal):** §2 defers "MIS" among consumer products (ADR-0011) while §6 has the node host "MIS publication" — the node's **MIS-Live** (Book/KSA labeler) is distinct — `prd.md:85` vs `prd.md:374-379`; flagged D1 `correlate.md:49`, `mine-node.md:255-262`.
2. **Latency budgets:** operator ~50ms full-round-trip direction vs GitBook 35/10-45/100ms budgets — GAP-0013 forbids invented numbers; the node's numbers are **evidence, not spine constants** — `tracker/trading-node-notes.md:24` vs `mine-node.md:151-156` vs `_docwork/gaps.yaml:126-128`.
3. **Paper-mode framing:** old K-25 "fail-mechanism-only" vs the ratified standing-state feeding alpha-decay — resolved to standing-state (AD-35/GAP-0041) — `tracker/trading-node-notes.md:25` vs `_docwork/gaps.yaml:407-408`.
4. **News-and-paper:** 2026-08-18 "bots continue in paper mode during a blackout" SUPERSEDED — a blackout stops live AND paper entries; the decision is journaled — `tracker/map.md:44` (old) vs `tracker/map.md:92` / `_docwork/gaps.yaml:418`.
5. **News scope width:** old build "currency → all pairs containing it" is looser than the corpus's dated per-instrument currency-exposure records — do not merge — `mine-planning.md:190-193` vs `correlate.md:142`, `_docwork/gaps.yaml:418`.
6. **SQS formula:** SRC-03 memlog entry 118 "SQS formula stays open pending re-understanding pass" conflicts with the risk sitting's GAP-0043/DEC-0153 resolution — surfaced, unresolved — `sweep-signoff-mechanics.md:220-222`, `_docwork/stage_state.yaml:122`.
7. **Treasury boundary count:** old "exactly three kinds, a fourth fails validation" superseded by four (`paper_epoch_reset` added) — `correlate.md:135`, `correlate.md:201-202`.
8. **Fifth venue command:** old general `amend_order` superseded by the narrower `amend_protection` — `correlate.md:132`, `correlate.md:202-203`.
9. **Backend-node topology:** two-node + PostgreSQL-server standing store is DEAD under "no DB server anywhere in V1" — only the placement/authority shape survives — `mine-node.md:284-289`, `correlate.md:165`.
10. **Venue-vs-platform axis (open modeling question):** old three-axis `(venue, platform, instrument)` vs current CT-03 opaque `(venue, symbol)` — does QMF need a platform axis so a future MT5/multi-broker setup isn't a retrofit? Recorded, not adopted — `mine-planning.md:197-205`.

### G2. Open items the sources leave undecided (with where I looked)
- **Ticket 004 "Trading node on QMF" is OPEN** — the whole node re-spec, incl. the parked live-money safety ruling (fixed-at-startup path, journaling, fail-closed unknowns) — `tracker/tickets/004-trading-node-spec.md`.
- **KSA target-level/effects matrix is OPEN** — the level enum is fixed (5 escalate-only) but which effect (suspend-new | drain | close-all) fires per severity is **node authority, do-not-default** — `mine-node.md:113-115`, `_docwork/stage_state.yaml` risk row, `tracker/trading-node-notes.md:55`.
- **Kill-switch behaviour when the broker connection is down** — nowhere designed; unbounded failure cost — `tracker/map.md:79`, `tracker/map.md:92`.
- **Node-phase position-safety cluster (PRD row 12 / D25b / mine-planning B4):** stop-out taxonomy (breakeven/forced-flat toward sizing), position fate at money boundaries (unrealized P&L into a sweep), dynamic SL/TP grammar, amendment idempotency threshold — `prd.md:673`, `correlate.md:118`, `mine-planning.md:144-151`.
- **Atomic decision+evidence commit vs the swappable store seam (PRD row 13):** is atomic dual-write a journal-path requirement, does it constrain the seam? Corpus wins pending an architecture ruling — `prd.md:674`, `correlate.md:119`, `mine-planning.md:280-285`.
- **Pool sizing / retry / health constants:** do-not-default; corpus numbers reconfirm-grade only; application injects and owns them — `tracker/trading-node-notes.md:27`, `tracker/trading-node-notes.md:47`, `_docwork/gaps.yaml:358`.
- **Node/ops backup constants:** object-storage provider, object-key layout, RPO/RTO, retention depth, encryption key custody, restore-verification cadence — deferred to the node/ops sitting (DEC-0118) — `epics.md:1219/1275/1305`, `findings.csv:104`, `enhancements.yaml:101-104`.
- **Training location (local GPU vs cloud)** unresolved (old GAP-0003 remainder) — `mine-node.md:253`.
- **MIS consumer boundary** Book+KSA-only vs manifest-bounded bot consumers (C-01 REOPEN) — `tracker/trading-node-notes.md:26`.
- **News-provider selection (DEC-0119) and deep-history acquisition (TrueFX/HistData bridge)** are operator-ruling/FR-042-epics inputs, not decided — `prd.md:675-676`.
- **Human-signed promotion signer, venue UNKNOWN stream granularity, amend atomicity, frozen-R at admission, Epic-10 cardinality/collapse** are UNPROVEN in the foundation build (verification debt, not confirmed defects) — the node phase inherits the burden of proving them on the live path — `proof_map.md:35/38/40`, `findings.csv:47/62/63/68/69`.
- **Recovered ML models (Kronos/HMM/BOCPD/MS-GARCH) and `regime_classifier_v1`** carry no authority; MIS architecture/hyperparameters/label-gen method never ratified — `mine-node.md:238-241`, `correlate.md:178`, `mine-planning.md:170-174`.
