# Mining extract — later trading-node + deployment/ops corpus

Source scanned (all under `C:/Users/Mubarak/Documents/QMX/`):
`trading-node/qmx_trading_node/` (all 21 `.py` + census), `backend-node/qmx_backend_node/`
(skim), `TRADING-NODE-SHIP-GOAL.md`, `ops/` (systemd + ml-training), `stack/`.
Judged against the current PRD at
`_bmad-output/planning-artifacts/prds/prd-QMX-2026-08-21/prd.md` (esp. §6 Phase-2
node outline, §9 DevOps success lens).

---

## 0. What this source is, and its disposition

This is the **later, "more stable" generation of the trading node** the operator
referenced — the one that ran under a `/goal`-driven software-factory night
(`TRADING-NODE-SHIP-GOAL.md`, session ending 2026-08-10, targeting Epics 1–7 of an
old plan). It is **a different documentation/contract generation** from today's
`docs/` corpus:

- It builds against the **2026-07-20** architecture spine and PRD, an **AD-1..N /
  CT-BMS-* / CT-MIS-* / CT-BOOK-* / CT-SYNC-* / CT-DATA-* / CT-SEC-* / CT-PAPER-*
  / CT-ATTR-*** contract namespace, and an **Epic 1–10 / Story x.y** plan. Today's
  corpus uses **CT-01..CT-34 + DEC-0001..0185 + AD-spine + L1..L39** and will
  regenerate epics/stories from the new PRD. The two ID systems do not line up;
  treat every old ID here as prior-generation evidence, not a current citation.
- The code is deliberately **"proof-shaped"**: most modules model decisions as
  pure data validated against `standards/*.json`, explicitly *not* opening
  sockets, training models, or trading. The ship-goal's own thesis is that the
  plan terminated at "proof altitude" and needed wiring into a runnable node.

**Disposition for the PRD:** the operator already expects the node to be
**rewritten on QMF** (PRD §6, §2 Phase-2). So nothing here is carried as
implementation. What is genuinely valuable is the **capability map** — this
generation is the most complete enumeration anywhere of *what the node must do*,
what its **runtime seams**, **operational values**, **deployment shape**, and
**MIS/ML lifecycle** are. That enriches PRD §6 (node capability outline) and §9
(DevOps lens) without importing a single old contract. The **two-node +
PostgreSQL-server** shape (backend-node) is the one architecturally load-bearing
idea that is *superseded* by today's "no DB server anywhere in V1" ruling and
should be recorded as dead.

---

## 1. Trading-node capability outline (enriches PRD §6 Phase 2) — capability level only

Today's §6 node paragraph is one sentence listing: Book/BMS runtime, order path
over qmf-venue, KSA, sizing-ladder eval, ledger↔broker drift kill, retry/pool
constants, MIS publication. The node code confirms and **decomposes** that into a
concrete runtime-seam list. Each below is a capability the Phase-2 node must
carry; none is new scope — they refine the existing outline.

### 1.1 Startup, preflight, and supervision
- **Deterministic cold-start preflight gate** run *before any state mutation*:
  ordered checks `host_os_systemd_or_wsl2 → disk (≥1 GiB free) → network
  reachability (cTrader Open API demo.ctraderapi.com:5035) → pinned-stack
  versions`, fail-closed, emitting a typed failure register id
  (`PREFLIGHT_FAILED`). On pass it hands off to a fixed bootstrap plan:
  `cold-start bootstrap → SQLite migrations → PostgreSQL migrations`.
  (`backend-node/…/preflight_gate.py`.)
- **Startup version floor**: node refuses to start below a ratified SQLite floor
  (`sqlite_version >= 3.53`). (`trading-node/…/main.py`.)
- **Schema-migration discipline**: forward+reverse SQL, reversibility evidence,
  expected-columns and required-trigger assertions, append-only stream triggers
  (`records_only_insert / no_update / no_delete`). (`schema_migrations.py`.)

### 1.2 Venue / order path (the qmf-venue live embodiment)
- **cTrader connection manager**: OAuth auth chain (app auth → demo-account
  discovery → per-account OAuth authorize-click surfaced as an operator *stop*),
  **connection-pool sizing + retry + reconnect + gap-recovery**, polite rate
  limiting (ratified ceiling ~5 req/s per connection, backoff+jitter),
  **broker-equity computation**, **label-based fill attribution with journaled
  fills**, and **paired-demo-binding per live account binding**.
  (`connection_manager.py` covers old stories 2.4/4.4/4.5/4.6/4.7;
  `dev_credentials_oauth.py`, `historical_backfill.py`.)
- **Platform-blind command adapter** (place/cancel/amend + a ratified fifth
  command) with acknowledgements, and the **four-outcome law**: timeout ≠
  rejection, **UNKNOWN is a state not an error**, an UNKNOWN blocks its
  `(venue,account)` command stream until explicit reconciliation; no self-clear,
  auto-retry, or auto-flatten. (Confirms current FR-022..026 / CT-18..21 /
  SCN-0005 as the node's live surface.)
- **Time authority injected**; platform timestamps normalized only at the venue
  boundary (matches current CT-02 "nothing below the composition root reads the
  clock").

### 1.3 Book / BMS / Treasury runtime (the qmf-risk live embodiment)
- **Book-type schema** as a template of **sections 0–5**: `charter, footprint,
  money_rules, entrance_exam, leash_chain, capacity_and_sweep_mechanics`
  (`book_type_schema.py`, old CT-BOOK-03) — a useful concrete decomposition of
  what a Book carries.
- **Book definitions** as Class-1 records keyed on stable `book_id`, with
  registry-numeric slot values. (`book_definitions.py`.)
- **BMS-owned authoritative book-mode registry**: V1 modes `LIVE`/`PAPER`;
  `BENCHED`/`STOOD_DOWN` reserved; transitions carry reason + trigger-decision
  (birth-in-paper, warm-up-to-live, exam-to-paper, breaker-bench, activation,
  treasury-boundary, sweep, re-seed). (`mode_registry.py`, old Story 5.3.)
- **Treasury virtual-ledger** birth + **rollover-only sweep** (`sweep / refund /
  re_seed`, `broker_server_rollover` boundary only; physical withdrawal
  prohibited; refund dormant). (`treasury.py`, old CT-BMS-01.)
- **Paper mode = frozen counterfactual**: a Book-level standing state entered by a
  dated transition, freezing a balance while sensing/paper-trading continue.
  (`paper_mode.py`, old CT-PAPER-01 — confirms current CT-24 / SCN-0006.)
- **Reconciliation + technical-kill**: reconciliation reports over broker-equity
  vs virtual-ledger, verdict `reconciled / drift / unknown`; an unexplained live
  **drift → `technical_kill` → `halt_trading`** (old law L14). `reconciliation_
  epsilon = 0`, operator review mandatory before any non-zero. Demo/paper
  bindings are **excluded** from the live-drift kill. (`reconciliation.py`, old
  CT-BMS-03 — this is the live "ledger↔broker drift kill" §6 names.)

### 1.4 KSA (Kill-Switch Authority) — global protection
- **5 escalate-only levels `GREEN / YELLOW / ORANGE / RED / BLACK`** as a global
  capability; **book profiles select behavior**; only operator resurrection
  de-escalates. The level *enum* is non-configurable; the **target-level/effects
  matrix is left open** (an acknowledged gap — do not invent it). (registry
  census `ksa_levels`, old DEC-0043; matches current §6 "escalate-only global
  protection; only operator resurrection de-escalates".)

### 1.5 Records (single journal writer)
- One SQLite-WAL writer over **five streams**: `veto_ledger, trade_journal,
  book_journal, ksa_audit_log, correlation_ledger`; append-only enforced by
  DB triggers; **decision + required evidence committed in one transaction**;
  `synchronous=FULL` on the journal path. (`records.py`, old Story 1.5 —
  confirms current CT-13.)

### 1.6 Registry (governed numbers)
- Governed numeric values with a published **census (25 variables, 10 formulas,
  8 architecture slots)**; each value carries `configurable`, DEC-link, component,
  `source_status` (observed/measured/unresolved/retired), constraints; changes go
  through operator-review + DEC-linked governance; null/unresolved values block.
  (`registry.py` + `registry_census.json` — confirms current L38 / FR-035 and
  gives the node's concrete configurable set.)

### 1.7 Operator powers surface
- **Powers API** as RPC-HTTP/JSON request/response, authenticated by
  **local-trusted-channel operator OS identity only**; **backend evidence can
  never authorize** a power. At its story the *only* live power was
  `ratify_registry_value`; **`a1_resurrection`, `sunday_review`, and
  `promotion_pull` were explicitly unsupported boundaries** — i.e. the
  human-signed promotion path is preserved as a *stop*, not automated
  (`powers_api.py`; confirms current SCN-0007 / ADR-0015 / L17). These three name
  the node's real operator-power set: resurrection, periodic (Sunday) review, and
  promotion-pull — matching PRD §1 "resurrection, periodic review, ratification".

### 1.8 Capacity / performance instrumentation
- **Capacity micro-bench**: measures durable-commit latency through the real
  Records path; roles = `gil_contention_canary`, swap-trigger signal,
  capacity-model input; named capacity drivers = tick fan-out by pairs, labeler
  compute per snapshot, durable-commit rate, sync egress, archive growth/day,
  postgres read concurrency. (`capacity_bench.py` — the node's built-in
  measure-then-budget hook, matching current NFR-04.)
- **Concrete latency budgets recorded as evidence** (registry census, all
  `configurable` unless noted): tick→MIS ceiling **35 ms**; order path
  **10 ms (min, non-configurable) – 45 ms**; end-to-end tick→order **100 ms**;
  hot retention **~14 days** (indication only); `roster_capacity 6` vs
  `max_concurrent_live_bots 3`. Several ops slots are deliberately **unresolved**
  (`sync_interval`, `sync_backlog_alert_fraction`, `sync_heartbeat_cadence`) —
  no value inferred.

---

## 2. Deployment / ops / monitoring patterns (feeds PRD §9 DevOps lens)

The current PRD §7 puts "deploy/infra/ops" and all node constants out of V1
scope, but §9 makes the **DevOps lens primary** and says the node phase "will
demand" server deployment (ML training, shadow rollouts, retraining). This
generation is where the deployment shape actually exists. Capture as patterns:

- **Two systemd services** (`qmx-trading-node.service`, `qmx-backend-node.service`)
  both launched via a single `tools/supervised_node_runner.py --node {trading|
  backend}`. Hardening baseline worth carrying forward: `Restart=on-failure`,
  `RestartSec=5s`, `StartLimitBurst=3 / StartLimitIntervalSec=60`,
  `DynamicUser=true`, `NoNewPrivileges=true`, `PrivateTmp=true`,
  `ProtectSystem=full`, `PYTHONUNBUFFERED=1`, `@@QMX_PREFIX@@` templated prefix.
  This is exactly the "one person can deploy/monitor/repair" posture §9 asks for:
  crash-restart with a burst cap so a crash-loop stops instead of thrashing.
- **Secrets via `systemd-creds`** only; secret **references never values**; a
  **cold-start returns unresolved metadata only**, dev credential entered once and
  never echoed; redaction markers (`[REDACTED_BY_SECRETS_STORE]`) in the
  connection manager. (Confirms current CT-21 / L34 / NFR-05.) Rotation required
  before any production use.
- **Pinned application stack** (`stack/pinned-stack.json`,
  `application-dependencies.json`): Python (unpinned host language), **apsw ≥
  3.53.3.1** (SQLite WAL, `synchronous=FULL`), **PostgreSQL 18.x** (backend
  standing store only), **DuckDB 1.5.x** (per-process analytics over Parquet,
  *never a shared writable file*), **pyarrow == 25.0.0**, **cTrader Open API
  client generated from `spotware/openapi-proto-messages`** (stale official
  wrappers rejected), **systemd + systemd-creds** (distro-current), **no external
  cache tier**. Preflight asserts these versions at cold start.
- **Monitoring/evaluation built-in, not bolted-on** (the §9 counter-metric): the
  node's failure surfaces are *typed* — preflight failure register
  (`PREFLIGHT_FAILED`), sync failure classes (`VERIFICATION_MISMATCH,
  BACKEND_INGEST_FAILURE, SYNC_BACKLOG_ALERT, UNRECOVERABLE_GAP, SCHEMA_MISMATCH,
  MONEY_ENCODING_VIOLATION, AUTH_FAILURE, TRANSPORT_ERROR`), reconciliation
  verdicts, KSA levels, MIS degradation visibility, the capacity canary — every
  failure lands as journal evidence + refusal, matching §9 "failures surface as
  typed refusals and journal evidence, not archaeology".
- **Backup/restore/sync durability**: trading→backend **CT-SYNC-01 v2** with
  **durable + content-verified ACK** (watermarks received/durable/verified,
  purge frontier advanced only on verified, rerequest reasons `backend_restore /
  verification_failure / gap_detected / reconnect_resync`). Recoverability is
  claimed only through verification — matches current SCN-0004 / CT-14 posture.
- **Install/start/stop/backup/recovery from one canonical checkout** is an
  explicit shipment requirement in the ship-goal (Outcome-A item 12): the operator
  must not "hunt across folders or reconstruct Git state." That is the plain-words
  form of §9 "deployable out of the box / one-person operability."

---

## 3. MIS + ML shadow-rollout material (the operationally intense §9 driver)

MIS = **Market Intelligence Service** (old Epic 3): a labeler layer that computes
market-condition signals and publishes them to Book and KSA. This is the
"machine-learning instances with training, shadow-rollout, and retraining" that
PRD §6/§9 flag as *why* the DevOps lens is primary. The honest state:

- **8 ratified labelers** (`labeler-catalog-ratification.json`): 6 **rule-based**
  (identity, spread-state, gap-event, feed-state, SQS, degraded-sensors — no
  training), 1 **fitted** (`liquidity_stress_v1`, CPU quantile fit), 1 **trained**
  (`regime_classifier_v1`) whose `model_family` is literally
  `"..._placeholder"` and `training_location` is `"unresolved"` — **no ratified
  architecture, hyperparameters, or label-generation method exists.**
- **MIS-Live runtime**: CT-MIS-01 snapshot assembled from bound labeler versions,
  **compute-once fan-out to Book + KSA over an in-process synchronous dispatcher**
  (explicitly *no* queue/bus/RPC/HTTP/file-sync/cross-node hop), a deterministic
  **SQS (snapshot-quality-score)** weighted-floor with a hard-block flag, and a
  **degradation-visibility** projection naming failed labelers.
  (`mis_live_snapshot.py`, `mis_live_fanout.py`, `mis_degradation_visibility.py`.)
- **MIS-Archive** (backend): Parquet emission via **temp-write-then-rename**,
  reader visibility gated on **manifest hash + row-count match**, bounded
  **CT-MIS-02 replay** over manifest-visible artifacts. (`mis_archive_storage.py`.)
- **Shadow lane = ratified CONCEPT ONLY, not built.** Design: runs on the
  **backend node**, replays over a **captured canonical feed**, uses an **isolated
  manifest prefix**, and a **one-affected-book-cycle evaluation window**. The
  story that builds it (old 3.9, "raw canonical-feed capture + backend shadow-lane
  readiness") is **backlog**. **No model is currently shadow-deployed.**
- **Recovered non-authority models** — **Kronos** (pull-pretrained foundation
  model), **HMM**, **BOCPD**, **MS-GARCH** — all carry `no_current_authority` /
  refusal `NO_CURRENT_AUTHORITY`. Downloads/prior-training/popularity do **not**
  authorize adoption; adoption requires **fresh ratification + parameter identity
  + training evidence + shadow-evaluation evidence + L10 recertification impact**.
  Their `no_current_authority` is because they are *unratified recovered names*,
  **not** because they are "trained-but-shadowed."
- **Overnight training scaffold** (`ops/ml-training/`, self-labeled DRAFT,
  untracked, never run): Windows-GPU orchestrator (`overnight-train.ps1`) doing
  venv + opt-in deps → GPU/CUDA probe (`nvidia-smi`, torch CUDA check) → data
  validation that **never downloads or fabricates** data → per-model
  checkpoint/log/resume → run manifest with a recorded deterministic **seed**.
  Only `liquidity_stress` is genuinely runnable (CPU); `regime` runs as a
  placeholder; `bocpd` is disabled behind `-EnableUnratifiedBOCPD`. Key doctrine
  worth carrying: **training is an OFFLINE job** — the no-ambient-time/randomness
  invariant applies to the live runtime, so an offline trainer may seed RNG *and
  record the seed* for reproducibility; and **a trained artifact has zero MIS
  authority until it passes admission + L10 recertification**. Training location
  (local GPU vs cloud) is **unresolved** (old GAP-0003 remainder).

This whole MIS/ML surface is a **Phase-2 node capability**, not V1 — but it is the
concrete content behind §6's "MIS publication" and §9's "ML training, shadow
rollouts, retraining." Note a naming tension to resolve in the PRD: §2's table
lists "MIS" among *deferred consumer products (ADR-0011)*, while §6 has the node
*host MIS publication*. These are two different things — **MIS-Live labelers
(node-runtime market intelligence for Book/KSA)** vs any consumer-facing MIS
product. The §6 node outline should name MIS-Live explicitly so the reader does
not read §7's deferral as excluding it.

---

## 4. What backend-node represents historically

`backend-node` is the **server-side twin** of a **two-node architecture** the
operator has since moved away from:

- **Role**: the "evidence home" / **standing store**. `PostgreSQL 18.x` holds
  **Class-1 CDC replicas, Class-2 stream replicas, the certificates corpus +
  dossiers, attribute history, the sync watermark/ack ledger, and catalog
  metadata**; the backend also runs **exam job-runners**, the **MIS-Archive**
  (Parquet), and the **Dukascopy deep-history acquisition pipeline**. Authoritative
  Class-1/2 writes stayed on the **trading-node SQLite WAL**; backend was replica
  + analytics + exam + archive, fed by **CT-SYNC-01 v2** durable+verified sync.
  It is explicitly **NOT** the "AD-12 SQLite→Postgres swap."
- **Its own history**: the ship-goal notes `backend-node` was mostly *uncommitted
  concurrent work* at snapshot time; the acquisition pipeline was a real, running
  Dukascopy download. It reads as a later, more-built cousin of an even earlier
  "backend" concept the operator had already been drifting away from.
- **Why it's superseded**: today's corpus collapses to a **single QMF framework**
  with **"no database server anywhere in V1"** (FR-016, NFR-10), the registry
  persisting **through qmf-data only** as the single ratified inter-library edge
  (FR-008, L30), over a **dependency-free store seam on swappable local engines**.
  The two-node **PostgreSQL-server standing store + trading↔backend sync** model is
  the one **architecturally load-bearing idea here that is dead** under the new
  ruling. Record it as superseded, not carried.
- **What survives from backend-node's scope**: the **Dukascopy acquisition**
  concept survives conceptually in current **FR-017** (Dukascopy first historical
  tick source, download-once, personal-use licensing honored, ship-no-corpus) and
  **FR-042** (data-mgmt download/verify/gap-check/catalog behind a licensing gate).
  The old pipeline even encodes the same **licensing-unresolved fail-closed
  posture** (`SOURCE_LICENSE_NOT_CANONICAL_USABLE` until operator upgrades the
  posture with agreement evidence) — consistent with today's ship-no-corpus gate.
  In the QMF rebuild this belongs to **qmf-data-ingest / QMB data-mgmt**, not a
  separate backend node.

---

## 5. Consistency check vs current corpus

**Confirms / reinforces current FRs (no change needed, evidence that the current
capability list is right):** four-outcome venue law + UNKNOWN-blocks-stream
(FR-023/024); Book owns money/sizing/stops, BMS accounts+constrains (FR-027/028);
paper = dated frozen standing state (FR-029/SCN-0006); Records single append-only
writer, decision+evidence one txn (FR-013); registry governed configurable numbers,
blank blocks live (FR-035/L38); secrets as references never leaving the connection
manager (FR-025); human-signed promotion the only path to live, resurrection/
review/promotion-pull as the operator power set (SCN-0007); KSA escalate-only 5
levels, operator-only de-escalation (§6); Dukascopy download-once personal-use
(FR-017/042); measure-then-budget performance with the node carrying concrete
latency numbers as *evidence* not spine constants (NFR-04).

**Superseded / dead (do not carry):**
- Two-node split + **PostgreSQL server standing store** + trading↔backend
  **CT-SYNC-01** sync → killed by "no DB server anywhere in V1" (FR-016/NFR-10).
- Old **CT-BMS-*/CT-MIS-*/CT-BOOK-*/CT-SYNC-*/CT-DATA-*/CT-SEC-*/CT-PAPER-*/
  CT-ATTR-*** contract namespace and **AD-12/17/44 / L14** law numbering →
  re-derived into current CT-01..34 / DEC / AD-spine / L1..39.
- **Epic 1–10 / Story x.y** plan and **`sprint-status.yaml` / `dev-auto` /
  BMAD-loop** factory route → this project's factory is the external epic-factory
  / queue lane; epics/stories regenerate from the new PRD.
- **"Proof-shaped" module style** (pure-data validators against `standards/*.json`,
  no sockets/training) → an artifact of the interrupted old build; node "likely
  rewritten on QMF."
- 2026-07-20 spine + PRD, and the whole `TRADING-NODE-SHIP-GOAL.md` Epic-7 mission
  → superseded by the 2026-08-21 corpus and this PRD.
- `regime_classifier_v1` placeholder + recovered models (Kronos/HMM/BOCPD/MS-GARCH)
  carry **no authority**; MIS itself is Phase-2 node scope, not V1.

**Tension to flag (not resolve here):** §2 lists "MIS" as a deferred consumer
product while §6 has the node host "MIS publication" — the node's **MIS-Live**
labeler layer (market intelligence to Book/KSA) is a distinct thing and should be
named in §6 so the deferral isn't misread.
