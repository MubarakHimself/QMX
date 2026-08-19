# Deterministic Trading Node — wiki inventory and GitBook-to-wiki delta

> **Superseding vocabulary note, 2026-08-17:** this report accurately records that the later wiki called SQS “snapshot quality score.” The operator has since corrected the project meaning to **Spread Quality Sensor**. Treat the wiki expansion and all downstream `snapshot_quality_score_v1` references as semantic drift, not current authority. See `../recovery-lineage-addendum.md`.

## Purpose and scope

This is a scouting artifact, not replacement documentation, architecture, code, or a backlog. It inventories the current local wiki at `C:\Users\Mubarak\Documents\QMX\wiki` and isolates what the wiki says was added, changed, narrowed, or retired after the public GitBook capture.

Included: the deterministic/non-agentic Trading Node and its directly owned or load-bearing boundaries—books, BMS, Treasury, Records, MIS/SQS, KSA, broker adapter, connection manager, paper/fail mechanisms, registration, data placement and sync edge, notification, QML's bot-authoring boundary, exact arithmetic, and the trading-side operator/Powers boundary.

Excluded except where an interface constrains the Trading Node: Backtest Engine, examination internals, WF1/WF2/WF3 substance, agentic runtime/harness design, analytics/decay implementation, and agent-facing data consumers.

## Provenance and authority

The wiki is explicit that it is a reconstruction with layered authority. For this recovery, the safe order is:

1. the final July 2026 `ARCHITECTURE-SPINE.md` for architecture/mechanics;
2. the updated PRD and addendum for requirements, scope, vocabulary, and acceptance intent;
3. the authored wiki as the reconciled current description;
4. the 2026-07-18 GitBook capture for details that do not conflict;
5. approved recovered artifacts only according to their own labels (`binding`, `unratified`, `old-vault`, `re-anchor`, `proposal`, `unresolved`);
6. attic material as history only—never build authority.

Evidence labels remain binding: **Observed**, **Deduced**, **Proposed**, and **Unresolved**. A proposed identifier or a ratified behavior does not authorize unratified payload fields.

Primary provenance pages:

- `wiki/log.md`
- `wiki/sources/qmx-gitbook.md`
- `wiki/sources/local-cleaned-recovered-design-artifacts.md`
- `wiki/sources/bmad-planning-run-2026-07.md`
- `wiki/knowledge/evidence-model.md`
- `wiki/knowledge/traceability.md`

### Change chronology from `wiki/log.md`

| Date | Source layer | What happened | Recovery meaning |
| --- | --- | --- | --- |
| 2026-07-18 | GitBook ingest | Captured 67 Markdown pages and reconstructed the wiki from the public source. | Treat pages that remain GitBook-only as baseline, not later additions. |
| 2026-07-20 | Approved recovered donors | Ingested 13 local design artifacts and reconciled replay, lineage, analytics, position safety, QML, and a service proposal. | Mixed-authority donor evidence. Most old lifecycle/capital/service topology is not current. |
| 2026-07-21 | Operator-ratified planning delta | Reconciled scope, preliminary topology, lifecycle, data, connection manager, attributes, registration/promotion, protection/news, monitoring, vocabulary, arithmetic, and contract defects. | First major post-GitBook authority layer. |
| 2026-07-24 | Topology-v2 pass | Adopted the 45-decision architecture spine, three-node topology, backend evidence role, London/Linux target, revised paper/activation model, and CT-SYNC-01 v2 semantics. | Current architecture/topology authority. |
| 2026-07-27 | Story 5.1 | Ratified CT-BOOK-03, the versioned book-type schema contract. | New concrete book-schema boundary after GitBook. |

One active page also contains an explicitly dated **2026-07-28** “operator-ratified” interim position-boundary rule, but `wiki/log.md` stops at 2026-07-27 and that page's front matter still says `updated: 2026-07-21`. Treat the rule as a strong late wiki assertion that requires provenance confirmation before being promoted into fresh canonical docs.

## Executive finding

The user's estimate is borne out: the GitBook appears to contain most of the Trading Node's domain behavior. The local wiki's high-value additions are concentrated in:

- physical topology and node placement;
- authoritative storage, replication, and synchronization rules;
- replacement of the old trading-node paper/lifecycle model with `ADMITTED` plus fail-mechanism paper;
- unified registration/promotion and click-time revalidation;
- explicit connection-manager placement and cTrader session/recovery constraints;
- book-type/attribute schema discipline;
- exact arithmetic and precise vocabulary;
- refined news-protection, notification, monitoring, and operator-console boundaries;
- contract-direction corrections and a set of schema-pending contract surfaces;
- a recovered position-safety problem statement, without a ratified implementation.

The core GitBook model survives: bot → book → BMS → operator authority; seven book doors; MIS as information-only; KSA as protection authority; adapter as platform-blind executor; Treasury seed-to-cap cycles and rollover-only sweep; Records append-only evidence; registry/formula authority; and the three golden scenarios.

## GitBook → local wiki delta ledger

The “delta” column below means the wiki attributes the item to `bmad-planning-run-2026-07`, `local-cleaned`, a later story, or an explicit post-ingest reconciliation—not that this inventory independently diffed every raw GitBook page.

### A. Scope and topology

| Delta | Current status | Recovery disposition | Evidence |
| --- | --- | --- | --- |
| Deterministic V1 is explicitly **forex-only** and **algorithmic**, not quantitative, multi-venue, crypto-adaptable, or agentic. Crypto/stocks are outside V1; prop-firm is a deferred within-grammar book type. | Operator-ratified, active. | Carry forward as a hard scope boundary. | `overview.md`; `architecture/system-context.md`; `sources/bmad-planning-run-2026-07.md` |
| V1 has exactly three deterministic nodes: Trading Node, always-on Backend Node, and desktop Console. The agentic node is outside that count and out of scope. | Operator-ratified, active. | Carry forward. Do not revive a separate “agentic server” inside Trading Node docs. | `architecture/system-context.md`; `architecture/runtime.md` |
| Trading Node is one OS process containing bots, books, BMS write side, MIS-Live, KSA, broker adapter + connection manager, and Powers API. In-node CT boundaries are direct module calls. | Operator-ratified, active. | Carry forward as current V1 placement; do not convert every logical component into a service. | `architecture/runtime.md`; `architecture/components.md` |
| Backend Node is an always-on multi-process set: one Python service, one standing PostgreSQL server, and examination job runners under one supervisor. It hosts replicas/evidence, sync ingestion, Reporting/metrics, Parquet archive/captured feed, and certification pipeline. | Operator-ratified, active; backend internals otherwise out of this recovery. | Retain only to define the Trading Node's sync/evidence boundary. | `architecture/runtime.md`; `components/data-layer.md` |
| Separate passive cold-tier shelf is retired; long-horizon storage is Backend Node cold storage. Backend outage must not block the Trading hot path. | Operator-ratified, active. | Carry forward; delete any new design that assumes the old shelf. | `overview.md`; `architecture/runtime.md`; `knowledge/gap-report.md` |
| Trading and Backend target London cloud on Linux; laptop/WSL2 is bootstrap parity. Console remains Windows UI-only. | Operator-ratified, active. | Carry forward as deployment target, not as application architecture. | `architecture/system-context.md`; `lenses/operations.md` |
| Linux node services use `systemd`, `Restart=on-failure`, start-limit counters, and `systemd-creds`; crash-loop thresholds `K`/`T` remain null. Fail-closed stand-down keeps Powers API reachable. | Ratified behavior, unresolved numeric thresholds. | Carry the behavior; keep `K` and `T` open. | `lenses/operations.md` |
| Recovered Replay/Analytics/Decay/Records Read/Position Safety microservices are only candidates. | `needs-review`, explicitly proposed. | Do not carry as deployed services. At most retain as future design questions. | `architecture/proposed-service-boundaries.md`; attic reconciliation |

### B. Persistence, evidence, and synchronization

| Delta | Current status | Recovery disposition | Evidence |
| --- | --- | --- | --- |
| Four data classes are fixed: Class 1 entities/relations; Class 2 Records streams; Class 3 archive/historical Parquet; Class 4 in-memory hot state rebuilt from evidence. | Operator-ratified, active. | Carry forward. | `architecture/data-and-contracts.md`; `components/data-layer.md` |
| Trading-node SQLite in WAL mode is authoritative for Class 1 + Class 2. Required state and its evidence commit atomically in one transaction. | Operator-ratified, active. | Carry forward as a central Trading Node invariant. | `architecture/runtime.md`; `components/data-layer.md`; `contracts/ct-bms-05-journal-append.md` |
| Records is the sole writer for exactly five append-only streams: `veto_ledger`, `trade_journal`, `book_journal`, `ksa_audit_log`, and `correlation_ledger`. “Bot trading journal” is a read-model projection, never a writer. | Operator-ratified, active. | Carry forward exactly. | `architecture/data-and-contracts.md`; `lenses/observability.md` |
| Backend PostgreSQL stores CDC/read replicas, stream replicas, certificate corpus/dossiers, attribute history, sync ledger, and catalog metadata. It is never a second writer and is distinct from the AD-12 Trading SQLite→Postgres contention swap. | Operator-ratified, active. | Carry forward only as a boundary contract. | `components/data-layer.md`; `architecture/runtime.md` |
| Certificate validity has one live truth in the Trading Class-1 index and its read replica; the full evidence corpus lives on Backend. | Operator-ratified, active. | Carry forward if certificate references enter registration; do not import examination internals. | `architecture/data-and-contracts.md`; `components/data-layer.md` |
| Class-3 interchange is manifested Parquet partitioned by pair/date/resolution. Backend service is sole finalizer; each process opens its own read-only DuckDB view. | Operator-ratified, active. | Carry forward at the Trading-to-Backend edge; do not share DuckDB across processes. | `components/data-layer.md` |
| CT-SYNC-01 v2 is Trading→Backend, one-way, watermarked, idempotent, resumable, and verify-before-purge. Backend acknowledges only durably persisted, content-verified data. | Semantics ratified; field schema pending. | Carry behavior, not invented fields or transport. | `architecture/data-and-contracts.md`; `contracts/index.md` |
| Heartbeats carry confirmed cross-stream consistency positions, not mere liveness. A backend restore/verification failure may issue a reverse **control-only** re-request containing durable watermarks; Trading re-pushes data. | Operator-ratified behavior; schema pending. | Carry behavior. Keep control message schema open. | `architecture/runtime.md`; `components/data-layer.md` |
| AD-40 promotion pull is the only reverse payload crossing and is Trading-initiated/click-gated; continuous sync remains one-way. | Operator-ratified; CT-REG fields pending. | Carry boundary only. | `architecture/system-context.md`; `topics/registration-and-promotion.md` |
| AD-41 stream-register draft would govern every Trading-produced stream. | Proposed, pending operator countersign. | Do not treat as ratified or fill rows. | `architecture/data-and-contracts.md`; `contracts/index.md` |
| `hot_retention_days`, `sync_interval`, backlog alert fraction, and heartbeat cadence remain null/unruled. Approx. 14 days is only indicated, not a default. | Unresolved. | Preserve as null. | `registry/variables.md`; `knowledge/gap-report.md` |
| SQLite backup uses the backup API and treats `db + wal + shm` as one unit; WAL may not live on a network filesystem. Backend backup is base backup + WAL archive. | Operator-ratified behavior. | Carry forward. | `components/data-layer.md` |

### C. Lifecycle, paper mode, registration, and activation

| Delta | Current status | Recovery disposition | Evidence |
| --- | --- | --- | --- |
| The former six-transition Trading Node lifecycle is superseded. Birth-in-paper, warm-up, and examination-to-paper moved to certification. | Operator-ratified, active. | Carry forward. Do not recover old WF/paper transitions. | `system/lifecycle.md`; `components/paper-mode-system.md` |
| Human promotion triggers a Trading-initiated pull, reruns preconditions at click time, and lands successful units in `ADMITTED`: definition/certificate references/placement exist, but no intents and no ledger. | Operator-ratified behavior; CT-REG field schema pending. | Carry behavior, keep fields open. | `topics/registration-and-promotion.md`; `architecture/system-context.md` |
| Birth atomically creates virtual ledger at registry seed `S`, emits CT-BMS-01 `re_seed` for cycle 1, and enters `LIVE`; the unit trades live from its first order. | Operator-ratified behavior. | Carry forward. | `system/lifecycle.md`; `components/treasury-desk.md` |
| Activation after `ADMITTED` at **next rollover** is only Proposed pending operator confirmation. | Unresolved/proposed. | Do not implement or state as final. | `system/lifecycle.md`; `contracts/ct-book-02-book-mode-state.md` |
| Trading-node paper is limited to fail mechanisms: book kill-line `LIVE→PAPER` until cycle-boundary re-seed; bot-seat breaker `LIVE→BENCHED→LIVE` with next-open auto-reset. | Operator-ratified. | Carry forward, keeping book mode and seat state separate. | `components/paper-mode-system.md`; `contracts/ct-paper-01-paper-mode-transition.md` |
| V1 book modes are `LIVE` and `PAPER`; `BENCHED` is a bot roster-seat state. Wider enum values `BENCHED`/`STOOD_DOWN` are reserved, not active book behavior. | Operator-ratified, but current contract schemas mix namespaces. | Carry semantics; redesign/ratify schemas before coding. | `contracts/ct-book-02-book-mode-state.md`; `contracts/ct-bms-02-mode-registry-read.md` |
| One unified gate serves book→BMS and bot→book registration. Four autonomous checks are schema, configuration, parity, and paired-demo binding; failures refuse and journal. Human promotion remains mandatory. | Operator-ratified; CT-REG-01 gate ratified, fields pending. | Carry behavior. | `topics/registration-and-promotion.md`; `components/book-template.md` |
| Each live account binding has a paired demo binding for fail-mechanism/paper fills while sensing remains on the pinned canonical live feed. | Operator-ratified. | Carry forward. | `components/connection-manager.md`; `components/paper-mode-system.md` |
| `warm_up_days` is retired from Trading registry scope. `roster_capacity = 6` is provisional and distinct from `max_concurrent_live_bots = 3`. | Retired/provisional. | Do not revive warm-up locally; preserve roster qualifier. | `registry/variables.md`; `topics/registration-and-promotion.md` |

### D. Book grammar, attributes, risk, and position safety

| Delta | Current status | Recovery disposition | Evidence |
| --- | --- | --- | --- |
| Template ordinal meanings are fixed at Sections 0–5: charter, footprint, money rules, entrance exam, leash chain, capacity/sweep. No current Section 6 is asserted. | Operator-ratified, active. | Carry exactly. | `components/book-template.md`; `decisions/adr-0002-template-and-instance-split.md` |
| Book types are versioned JSON Schemas; instances are schema-validated definitions. Numeric values live in the registry under instance ownership. | Operator-ratified. | Carry forward. | `components/book-template.md`; CT-BOOK-03 |
| CT-BOOK-03 was added by Story 5.1. It enforces typed filter columns, sparse inert/measured/informational attribute bag, expression-index promotion metadata for hot attributes, and structural refusal of EAV. | Ratified/active, 2026-07-27. | High-value post-GitBook addition; carry forward. | `contracts/ct-book-03-book-type-schema.md`; `wiki/log.md` |
| Attributes are immutable/versioned definitions and inert until exact `(attr_id, version)` binding. Experimental attributes are observable but unbindable. Behavior-shaping numeric values migrate to registry; nonnumeric pair/session scope becomes typed core data. | Operator-ratified model; CT-ATTR-01 schema still proposed. | Carry rules; do not invent the register schema. | `topics/attribute-model.md` |
| QML bot code may declare attributes but may not read those declarations at runtime; behavior inputs belong in bot spec/config hash and changing one mints a new spec version. | Operator-ratified. | Carry as a QML/book boundary rule. | `topics/attribute-model.md`; `components/qml-library-layer.md` |
| Dynamic SL/TP placement is now book money-rule grammar, with BMS configuration authority and adapter enforcement. The old globally uniform stop service is rejected. | Placement ratified; mechanics unresolved. | Carry placement only. | `topics/position-safety-and-sltp-authority.md`; `components/book-template.md` |
| Stop-out taxonomy, stop-policy forms, exam pinning, post-entry computation owner, close priority, and position fate at rollover/sweep/kill/paper boundaries remain open. | PE-3/PE-7 and contract work unresolved. | Do not fill from donor policy. | `knowledge/gap-report.md`; position-safety topic |
| Late interim rule says PE-7-neutral handling: no flatten/carry action at boundaries; caller supplies boundary equity; unrealized PnL is an `unknown` reconciliation item blocking ledger-reconciles; kill-line flip takes no position action. | Page says operator-ratified on 2026-07-28, but log/front matter provenance is inconsistent. | Preserve as a verification-required late delta, not unquestioned authority. | `topics/position-safety-and-sltp-authority.md` |
| Trust-bounded cost-aware Kelly input is missing, so FORM-0005 live sizing is incomplete by design. | PE-4 blocker. | Preserve the gap; never substitute generic Kelly. | `registry/formulas.md`; `knowledge/gap-report.md` |

### E. MIS, SQS, protection, adapter, and connections

| Delta | Current status | Recovery disposition | Evidence |
| --- | --- | --- | --- |
| The inspected wiki called SQS **snapshot quality score**, not a queueing service. An unreachable SQS causes a hard book-door block; MIS itself remains information-only. | Historical wiki claim, superseded in vocabulary by the 2026-08-17 operator correction. | Carry the hard-block/non-authority behavior; replace the expansion with **Spread Quality Sensor** and reopen the later aggregate. | `components/market-intelligence-service.md`; `glossary/index.md`; `../recovery-lineage-addendum.md` |
| CT-MIS-01 serves Book, KSA, and only manifest-bounded bot consumers. One pinned live-account connection is the canonical sensing feed; outage fails closed until that same feed gap-replays—no silent sibling failover. | Ratified behavior; CT-MIS-01 page remains draft. | Carry behavior. | `contracts/ct-mis-01-mis-live-snapshot.md` |
| BMS Exposure, not MIS, owns daily news-calendar import and compilation. Affected currency expands to every pair containing it; `affected_pairs[]` is a hint; sessions may widen but never narrow. Unknown high-impact coverage blocks conservatively. | Operator-ratified. | Carry forward. | `contracts/ct-bms-04-news-block-directive.md`; `components/book-management-system.md` |
| Protection funnel is explicit: MIS senses → standalone KSA decides → adapter enforces. KSA drains/quiesces account connections before enforcement is complete. | Operator-ratified. | Carry forward. | `components/kill-switch-authority.md`; `components/connection-manager.md` |
| KSA still has five levels and four trigger classes, but the full trigger→target-level matrix remains GAP-0015, especially connectivity/unknown state. | Baseline plus unresolved delta. | Preserve the levels and fail-closed behavior; do not invent mappings. | `contracts/ct-ksa-01-kill-switch-state-event.md`; `knowledge/gap-report.md` |
| Connection Manager is inside Adapter and is sole platform-session owner: pools, affinity, token buckets, OAuth refresh, arrival stamping, fill attribution, reconnect/gap recovery. | Operator-ratified, active. | High-value post-GitBook addition; carry forward. | `components/connection-manager.md`; `components/broker-adapter.md` |
| cTrader proof values: application auth before per-account OAuth `trading`; heartbeat ≤10000 ms; 50 req/s general and 5 req/s historical per connection; throttle uses broker `retryAfter`; fills are async/fire-and-reconcile. | Ratified proof values. | Carry as platform constraints, not internal latency guarantees. | `components/connection-manager.md` |
| Pool size, shard count, detailed recovery, live retry policy beyond throttle proof, and health thresholds beyond heartbeat proof remain unratified. | Unresolved. | Do not default. | `components/connection-manager.md`; `open-questions.md` |
| cTrader amendment/partial-close feasibility is confirmed, but CT-ADAPTER-01 still has only `place_order`, `cancel_order`, `close_position`, `close_all`. `amend_order` and semantics are pending and may not hide inside `payload`. | Capability confirmed; contract unresolved. | Do not implement amendment from prose. | `contracts/ct-adapter-01-broker-adapter-command.md`; position-safety topic |

### F. BMS, operations, notifications, monitoring, and operator boundary

| Delta | Current status | Recovery disposition | Evidence |
| --- | --- | --- | --- |
| CT-MIS-02 direction is corrected to Exam→Archive request, Archive→Exam result. CT-BMS-03 direction is corrected to Treasury→BMS; Adapter broker equity is upstream Treasury input. | Operator-ratified defect fixes. | Carry exact directions. | `contracts/index.md`; CT-MIS-02; CT-BMS-03 |
| Corrections are new Records entries referencing old entries; no in-place journal mutation. A state change and required evidence commit together. | Operator-ratified. | Carry forward. | CT-BMS-05; `architecture/data-and-contracts.md` |
| Real notifications are limited to sweep, `re_seed`, refund, KSA/kill-switch, and supervision fail-closed; everything else is Console evidence/log. Refund itself is dormant V1. | Event classes ratified; delivery design unresolved. | Carry classes; leave channels/retry/dedupe/quiet hours/credentials open. | `components/notification-system.md`; CT-NOTIFY-01 |
| Prometheus + Grafana are external, read-only, zero-authority monitoring; Loki optional. Journal durable-commit latency is required as a Trading hot-tier metric/canary. | Substrate ratified; dashboards/retention/alerts open. | Carry boundary, not product UI or authority. | `lenses/observability.md` |
| Console commands go to Trading-node Powers API; stale Backend evidence cannot authorize. Named powers include A1 resurrection, promotion/ratification, and Sunday review. Preconditions rerun server-side at click time. | Behavior ratified; command/read schemas unresolved. | Carry boundary. Do not invent a console API. | `architecture/system-context.md`; `decisions/trading-console-alignment.md` |
| Powers API stays reachable in fail-closed stand-down while sequencers refuse and connections drain. | Operator-ratified. | Carry as recovery invariant. | `lenses/operations.md`; trading-console register |

### G. QML boundary

| Delta | Current status | Recovery disposition | Evidence |
| --- | --- | --- | --- |
| QML is narrowed to bot authoring and stops at the Book boundary. MIS/BMS/KSA/adapter/connection/console/certification glue remain Python. It is not an agentic runtime surface. | Operator-ratified, active. | Carry boundary. | `components/qml-library-layer.md`; CT-QML-01 |
| Candidate QML duties include typed market inputs, deterministic feature ladders, safety hooks, intent emission, attribute declaration, once-per-tick contracts, and explicit `INSUFFICIENT_DATA` degradation. | Current boundary description informed by donor evidence; interface details not ratified. | Carry only as design intent pending QML session. | `components/qml-library-layer.md` |
| CT-QML-01 register has **zero interfaces**. Recovered types/modules do not populate it. | Explicit unresolved GAP-0013. | Do not recover API names/fields as current. | CT-QML-01; attic QML baseline |

## Component catalogue: current Trading Node view

| Component/boundary | Current responsibility | Key invariants/failure posture | Current unresolved surface | Document status |
| --- | --- | --- | --- | --- |
| QML-authored Bot boundary | Consumes canonical feed + manifest-bounded MIS fields; emits CT-BOOK-01 intent. | Bot owns entry/exit logic but cannot self-authorize sizing/admission or see broker/KSA. | First QML interface set; compiler/lint/runtime. | QML component `active`; CT-QML-01 `draft`, zero entries. |
| Book Template | Versioned grammar, roster, seven ordered doors, leash, sizing, profile, type/instance boundary. | Every refusal appends veto evidence; no in-cycle budget redistribution; no hardcoded load-bearing numbers. | Kelly term; stop-out taxonomy; position fate; first attribute bindings. | `active`. |
| Scalper Book | First book instance; money ladder, daily budget drain, breaker seat bench, rollover sweep. | Kill line fixed in cycle; cap checked/swept at rollover; paper gains are evidence; profile does not redefine global infrastructure. | Exact post-entry stop policy; complete book-specific tests. | `active`. |
| MIS-Live / SQS | Publishes typed/versioned, information-only snapshots and visible degradation. | Dead feed prevents new entry; unreachable SQS hard-blocks via Book; labeler-version drift invalidates parity. | Concrete labeler implementation; retained/archive timing; some budgets live only in registry. | `active`; CT-MIS-01 `draft`. |
| BMS | Treasury, Exposure, Records, Reporting; accounts for/constrains books; mode/news/policy boundaries. | Sole Records write path; Reporting zero authority; unexplained drift technical-kills; news applies live+paper. | Exposure v2/cross-book authority; some read/command schemas. | `active`; several BMS contracts `draft`. |
| Treasury | Virtual capital ledger; sweep/refund/re-seed boundary and reconciliation report. | Rollover-only sweep; no mid-cycle top-up/remnant restart; refund dormant; drift technical-kills. | Refund reserve; ledger/reconciliation details; position-inclusive boundary semantics. | `active`. |
| KSA | Global protection state; consumes BMS/MIS and commands Adapter effects. | Auto-escalate only; A1 de-escalates; news blocks live+paper; unknown blocks execution. | Trigger→level matrix; competing close/amend priority. | Component `draft`; CT-KSA-01 `draft`. |
| Broker Adapter | Platform-blind command translation, account binding, execution effects, drift visibility. | Does not choose permission; unknown/stale broker state blocks; no bot platform access. | `amend_order`; minimum stop; confirmation/idempotency; auth hardening. | `active`; CT-ADAPTER-01 `draft`. |
| Connection Manager | Sole platform-session owner inside Adapter. | Per-account affinity; rate limiting; OAuth; async fill attribution; reconnect recovery before healthy; drain on KSA transition. | Pool/shard sizing; recovery detail; retry/health thresholds; optional CT-ADAPTER-02. | `active`. |
| Paper/fail mechanisms | Frozen counterfactual behavior for kill-line book and breaker seat only. | Book mode and seat state distinct; no generic toggle; paired demo fills; no remnant restart. | Activation boundary; reserved book modes; PE-7 position fate. | Component + CT-PAPER-01 `active`, amended schema still pending. |
| Data/Records | Four-class placement, SQLite authority, append-only streams, provenance, sync edge. | Owner before write; state/evidence atomic; rebuild hot state before intents; verify before purge. | CT-SYNC fields/register; retention/cadence; canonical manifest serialization; Postgres policy conflict noted below. | Data component `active`; CT-DATA-01 `draft`. |
| Notification | Records-derived operator delivery for small ratified event set. | No intraday human judgment or trading authority. | Channels, credentials, retry, dedupe, quiet hours, receipts. | `needs-review`; CT-NOTIFY-01 `draft`. |
| Powers/Console boundary | Exceptional operator commands to Trading Node; evidence read is separate. | Server-side click-time validation; no stale Backend authorization; Console holds no trading secrets. | Command envelope, evidence-read channel, auth/authz, acknowledgements/audit. | Alignment register `draft`. |

## Contract inventory and status

The contract index calls all 18 listed CT surfaces “ratified,” but document status and schema status are more nuanced. The safe interpretation is: a boundary/behavior may be ratified while its existing page remains draft or its amended field schema remains pending.

| Contract | Boundary | Wiki page status | Delta/status note |
| --- | --- | --- | --- |
| CT-BOOK-01 | Bot → Book intent | `draft`; GitBook-only | Baseline schema; `requested_r` is a proposal, not final sizing. |
| CT-BOOK-02 | Book → BMS mode | `active` | Semantics amended for `ADMITTED`/fail-paper; page says amended field schema pending. |
| CT-BOOK-03 | Book-type definition | `active` | New Story 5.1 ratified contract (2026-07-27). |
| CT-MIS-01 | MIS-Live → Book/KSA/manifest-bounded Bot | `draft` | Consumer boundary/canonical-feed rules refined by planning. |
| CT-MIS-02 | Exam ↔ Archive request/result | `draft` | Direction defect resolved; outside hot path. |
| CT-BMS-01 | Treasury → Records event | `active` | Birth/re-seed/refund-dormant semantics refined. |
| CT-BMS-02 | BMS → KSA mode read | `active` | V1 book rows LIVE/PAPER; seat BENCHED separated. |
| CT-BMS-03 | Treasury → BMS reconciliation | `draft` | Producer direction corrected. |
| CT-BMS-04 | BMS Exposure → KSA news directive | `draft` | Currency compile/session widening/current refresh policy added. |
| CT-BMS-05 | Components → Records append | `draft` | Sole writer, five exact streams, atomicity made explicit. |
| CT-KSA-01 | KSA → Adapter state event | `draft`; GitBook-only schema | Full mapping still GAP-0015. |
| CT-ADAPTER-01 | Book → Adapter command | `draft` | Connection Manager added inside boundary; amendment still excluded. |
| CT-PAPER-01 | Paper/seat transition → BMS | `active` | AD-28 narrows semantics; amended field schema pending. |
| CT-NOTIFY-01 | Records-derived event → Notification | `draft` | Ratified event classes; delivery remains open. |
| CT-DATA-01 | Ownership register | `draft` | Four-class placement/CT-SYNC behavior are architecture rules, not added fields. |
| CT-QML-01 | QML interface register | `draft` | Zero entries; GAP-0013. |

CT-EXAM-01/02 are intentionally omitted from this Trading Node catalogue beyond their certificate-reference integration boundary.

### Named but schema-pending/proposed surfaces

- **CT-REG-01** — unified registration/promotion gate ratified; AD-40 pull/artifact-tuple semantics ratified; field schema pending.
- **CT-SYNC-01 v2** — sync semantics ratified; fields/transport and AD-41 stream register pending.
- **CT-ATTR-01** — proposed attribute-register contract.
- **CT-ADAPTER-02** — optional/proposed connection-session state.
- **CT-SEC-01 or CT-DATA-01 extension** — proposed secrets register.
- **CT-ADAPTER-01 amendment** — `amend_order` fields, confirmation, idempotency, stop-distance behavior, and priority pending.

## Baseline that appears to remain GitBook-derived

These are important, but should not be mislabeled as later local additions:

- authority chain: bot → book → BMS → operator;
- bots trade; books control; BMS accounts/constrains; nothing above bot touches market;
- seven ordered doors: footprint, viability veto, `R_max`, daily budget, breaker, exposure ledger, kill switch;
- MIS-Live/MIS-Archive split and information-only MIS principle;
- KSA five levels and automated escalation/A1 de-escalation law;
- Treasury seed-to-cap cycles, rollover-only sweep, no mid-cycle top-up, no remnant restart;
- template/instance separation and dormant sockets;
- Registry as numeric truth, 25 baseline variables and 10 formulas;
- exact scalper baseline values (`S=500`, `K=200`, cap multiplier `2.5`, runway divisor `5`, breaker `2`, budget factor `2`, live concurrency `3`) with qualifiers preserved;
- formulas FORM-0001 through FORM-0010, including unresolved Kelly and refund inputs;
- three golden scenarios: money ladder, rollover sweep, news block live/paper parity;
- dead decisions DEC-0018 through DEC-0025;
- baseline CT field tables, subject to later semantic amendments and draft status.

## Active versus attic/archive

### Active/current navigation

The current wiki routes readers to the active overview, system, architecture, component, contract, registry, registration, attribute, position-safety, gap, and open-question pages. Current authority is not identical to front-matter `status`: several active behaviors are documented on `draft` or `needs-review` pages.

Important non-active statuses:

- `components/kill-switch-authority.md` — `draft`;
- `components/notification-system.md` — `needs-review`;
- `topics/position-safety-and-sltp-authority.md` — `needs-review`;
- `architecture/proposed-service-boundaries.md` — `needs-review`, explicitly proposal only;
- many CT pages and Registry pages — `draft` despite some ratified behavior/values;
- `decisions/trading-console-alignment.md` — `draft` evidence/alignment register, not console API authority.

### Attic — never build from this

`wiki/attic/README.md` says: “Ruled-out material — never build from this.” The published topic paths are tombstones pointing readers to current pages.

| Attic page | What may be remembered | What must not be rebuilt |
| --- | --- | --- |
| `recovered-design-reconciliation.md` | The three-layer evidence-reading method and useful generic patterns. | Its stale assertion that topology was unratified; microservice names; old lifecycle/capital authorities. |
| `qml-recovered-baseline.md` | Types-first discipline, deterministic once-per-tick contracts, visible degradation, `INSUFFICIENT_DATA`, validation ideas. | Candidate APIs/types as current CT-QML entries; slot/DPR/WF/session/circuit-breaker couplings. |
| `bot-registry-and-lineage.md` | Immutable identity/lineage vocabulary and dossier intent, now partly reflected in data-class design. | Old WF states, registry writer topology, promotion/redemption, global pool mechanics. |
| `alpha-decay-and-performance-analytics.md` | Read-only measurement should not acquire capital/lifecycle authority. | DPR/PRS ranks, global bot pool, continuous merit allocation, WF3 mechanics. |

The recovered SL/TP material is not attic-only because the active position-safety page mines it as donor evidence. Its exact +1R/breakeven/trailing policy, WAL service, and failure behaviors remain **unratified candidates**, not current requirements.

## Open decision frontier for a fresh Trading Node

### Blocks correct risk/execution behavior

1. **PE-3 stop-out taxonomy** — what exits count for breaker projection and measured `Lbar`.
2. **PE-4 Kelly term** — missing trust-bounded cost-aware Kelly input leaves final live sizing incomplete.
3. **PE-7 position fate** — rollover, sweep, kill-line, and paper-transition handling; verify the late interim no-position-action rule.
4. KSA trigger→level matrix, including connectivity and unknown state (GAP-0015).
5. CT-ADAPTER-01 amendment fields, confirmation, idempotency, minimum-stop-distance handling, and close/amend priority.
6. Interleaving among KSA, hold-time force-flat, broker stops, and normal amendments.

### Blocks complete runtime/data contracts

1. CT-SYNC-01 v2 field schema and transport; AD-41 stream-register countersign.
2. `hot_retention_days`, `sync_interval`, sync/backlog/heartbeat alert values.
3. canonical manifest serialization for reproducible `data_snapshot_id`.
4. CT-REG-01 and CT-ATTR-01 field schemas; first ratified attribute definitions/bindings.
5. activation boundary after `ADMITTED` (next rollover is still proposed).
6. Connection pool/shard sizing, recovery details, retry policy, and health thresholds.
7. Trading Console evidence-read channel and Powers API command envelope/auth/audit.

### Other Trading-owned unresolved surfaces

- BMS Exposure authority beyond currency-news compilation (GAP-0008);
- notification delivery channels, credentials, retries, dedupe, quiet hours, receipts (GAP-0002);
- refund estimator inputs `rho`, `N_cycles_month`, and standstill `T`; refund remains dormant;
- chorus frequency `F_CHORUS`;
- crash-loop thresholds `K` restarts in `T` minutes;
- QML first interface set and internal compiler/lint/runtime rules.

## Conflicts, stale references, and precision hazards

1. **“18 ratified contracts” vs draft/schema-pending pages.** The index calls all 18 surfaces ratified, while many individual pages are `draft`, and CT-BOOK-02/CT-PAPER-01 say amended schemas remain pending. Carry boundary semantics only until schema status is reconciled.
2. **Book mode vs bot-seat state.** CT-BOOK-02/CT-BMS-02/CT-PAPER-01 enum tables still include `BENCHED`/`STOOD_DOWN`, but current V1 book modes are only `LIVE`/`PAPER`; breaker `BENCHED` is seat state. Fresh schemas should not preserve this namespace ambiguity accidentally.
3. **Late position-safety ruling lacks matching chronology metadata.** The active topic says “operator-ratified” on 2026-07-28, while its `updated` field is 2026-07-21 and the append-only log ends 2026-07-27. Confirm source before treating it as final.
4. **Backend PostgreSQL migration discipline conflicts.** `components/data-layer.md`, `knowledge/gap-report.md`, and `open-questions.md` say backend PostgreSQL schema-migration discipline remains unresolved; the final paragraph of `architecture/data-and-contracts.md` says the standing role and migration discipline are no longer open architecture questions. This needs a ruling/source check.
5. **Security secret-store page is stale against later operations authority.** `lenses/security.md` says no secret store is defined, while `lenses/operations.md` later fixes node-service secrets to `systemd-creds`. Treat the later planning source as higher authority, but the secrets contract/schema remains unresolved.
6. **BMS failure table likely carries a stale gap ID.** It says unclear desk authority should preserve “GAP-0010,” yet GAP-0010 is closed registration/promotion; unresolved Exposure authority is GAP-0008.
7. **Logical event owner vs physical writer.** Observability labels `ksa_audit_log` owner as KSA/BMS, while Records is the sole physical writer. Fresh docs should distinguish originating authority from writer ownership.
8. **Three-node topology does not ratify internal microservices.** Statements that transport/service decomposition are unresolved do not undo the fixed node/process placement. Preserve both levels of description.
9. **Acquisition stories prove governance/design, not acquired data.** The Data page explicitly says Story 2.1–2.8 do not establish that real market history was downloaded, cleaned, merged, or published.
10. **Historical state at inventory time:** the wiki treated `SQS` as snapshot quality score. **Superseded:** the current operator ruling defines **Spread Quality Sensor**; it is still never a queueing subsystem.

## Surgical handoff: what to carry first

For a fresh Trading Node documentation pass, the smallest high-confidence recovery set is:

1. Authority/invariants and the GitBook core behavior.
2. Single-process Trading Node placement and exact included modules.
3. SQLite Class-1/2 authority, five Records streams, atomic state+evidence, startup rebuild.
4. CT-SYNC-01 v2 behavior at the Backend boundary, leaving fields/transport open.
5. `ADMITTED` plus fail-mechanism-only paper model, with activation boundary explicitly unresolved.
6. Unified registration/promotion gate and click-time Trading revalidation.
7. Connection Manager inside Adapter, including proven cTrader rate/heartbeat/recovery constraints.
8. CT-BOOK-03, type/instance split, inert attributes, registry ownership, and no EAV.
9. MIS/SQS exact semantics and BMS-owned news compile.
10. Position-safety placement only; retain PE-3/PE-4/PE-7 and amendment ordering as blockers.
11. QML's narrow bot-authoring boundary with an empty CT-QML register.
12. Notifications, monitoring, and Powers as non-authoritative/evidence boundaries with incomplete delivery/API schemas.

Do **not** carry old WF lifecycle, DPR/PRS, global pools/slots, paper redemption, microservice topology, agentic APIs/MCP, QML donor interfaces, crypto-adaptable V1 grammar, second journal writers, or globally uniform book values.
