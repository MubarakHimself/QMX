# Deterministic Trading Node semantic delta

## Scope

This register answers one question: **what must be added, corrected, reconsidered, or deliberately left behind when the older GitBook is used to restart only the deterministic Trading Node?** It compares meaning, not Markdown wording or navigation.

Included are Book, BMS, MIS/SQS, KSA, Treasury, Records, Trading-side data/sync, Adapter/Connection Manager, paper/fail mechanisms, registration/promotion, QML's boundary with the Book, and the Console/Powers edge. Backend details appear only where they define a Trading Node contract. Agentic, Backtest/certification internals, and WF1/WF2 are excluded.

## 1. Already in GitBook — do not mistake these for recovered additions

| ID | `BASELINE` capability | Restart note |
| --- | --- | --- |
| B-01 | Authority model: bot proposes; Book owns admission, sizing, and accepted commands; BMS accounts for and constrains; KSA protects; Adapter executes mechanically; operator supplies final authority. | Preserve the non-agentic authority model without turning BMS into an inline allocator/executor. |
| B-02 | Seven Book doors and leash logic gate intents before execution. | Preserve the model; later sources refine inputs and placement, not the existence of the doors. |
| B-03 | Template/instance split with a seven-index form: Sections 0–5 are sealed and Section 6 is gap-bound/unsettled. | Later docs retain exact 0–5 ordinal meanings and decline to assert a current Section 6. |
| B-04 | BMS four-desk model: Treasury, Exposure, Records, Reporting. | Later docs sharpen ownership and journal boundaries. |
| B-05 | Treasury seed → trade → rollover sweep → re-seed cycles, with ledger segregation. | Later docs remove some transitions and define exact birth/sweep refusal behavior. |
| B-06 | MIS-Live/MIS-Archive split, information-only posture, snapshots, and SQS as a door-blocking quality signal. | Later docs fix placement, consumers, canonical feed, degradation, and archive semantics. |
| B-07 | KSA as a standalone protection authority with five levels and four trigger classes. | The full trigger-to-level matrix is still not settled. |
| B-08 | Platform-blind adapter shell and four core commands. | Later docs add Connection Manager/session constraints; amendment remains unfinished. |
| B-09 | Records as append-only evidence and the basis for deterministic reconstruction. | Later docs define exactly five streams, sole-writer behavior, and atomic state/evidence commits. |
| B-10 | Registry/formula authority and exact named variables/formulas. | Later docs retire or qualify some variables and expose remaining formula blockers. |
| B-11 | Named contracts for the principal component boundaries. | Later docs add CT-BOOK-03, make some directions explicit, and expose both schema-empty surfaces and still-unresolved routing conflicts. |
| B-12 | Golden scenarios for live operation, veto/protection, and rollover behavior. | Reuse as behavioral seeds, then update them for the later lifecycle and position decisions. |
| B-13 | Notification, paper, data, QML, and observability problem statements. | Several old mechanics beneath these statements are superseded; use the later dispositions below. |

The practical conclusion is that a restart should begin with the GitBook's conceptual skeleton. Rewriting that skeleton from scratch would create risk without recovering new information.

## 2. Later local architecture to carry forward

### 2.1 Scope, topology, and deterministic runtime

| ID | Later delta | Disposition | Precision boundary |
| --- | --- | --- | --- |
| K-01 | V1 is explicitly deterministic, algorithmic, and forex-only. Crypto, stocks, multi-venue expansion, quantitative research scope, and agentic execution are outside V1. | `KEEP` | Prop-firm may be a later within-grammar Book type; it is not a second runtime. |
| K-02 | Exactly three deterministic nodes: Trading Node, always-on Backend Node, and desktop Console. The agentic node is outside the count. | `KEEP` | Do not recover an “agentic server” into this architecture. |
| K-03 | Trading Node is one OS process containing bots, Books, BMS write side, MIS-Live, KSA, Adapter + Connection Manager, Records/data authority, and Powers API. | `KEEP` | Logical CT boundaries inside the process are direct module calls, not a microservice network. |
| K-04 | Backend is the read/evidence/cold/certification side and must never become a second Trading writer. Backend outage does not block the Trading hot path. | `KEEP` | Recover only this boundary; redesign Backend and examination internals elsewhere. |
| K-05 | Trading/Backend target Linux in London cloud; WSL2/laptop is bootstrap parity; Console is Windows UI-only. | `KEEP` | Deployment fact, not license to mix UI into Trading authority. |
| K-06 | Each Book has a deterministic sequencer for all Book-affecting events, including shared live/demo command ordering. | `KEEP` | Exact event taxonomy and recovery protocol still require contract work. |
| K-07 | Time is normalized and injected; monetary/quantity arithmetic is exact and canonicalized rather than float-dependent. | `KEEP` | Specify integer ticks/pips/units or Decimal scales in each contract; do not invent missing scales. |
| K-08 | Linux supervision is `systemd`, fail-closed stand-down preserves Powers reachability, and connections drain while sequencers refuse. | `KEEP` | Crash-loop thresholds `K` and `T` remain unset. |

### 2.2 Persistence, evidence, and synchronization

| ID | Later delta | Disposition | Precision boundary |
| --- | --- | --- | --- |
| K-09 | Four data classes: Class 1 entities/relations, Class 2 Records streams, Class 3 Parquet archive/history, Class 4 reconstructable in-memory hot state. | `KEEP` | Do not introduce an additional authority class casually. |
| K-10 | One Trading-node SQLite database in WAL mode is authoritative for Class 1 and Class 2. Required state and evidence commit atomically in one transaction. | `KEEP` | No per-Book databases. WAL must not live on a network filesystem. |
| K-11 | Records is the physical sole writer of exactly five streams: `veto_ledger`, `trade_journal`, `book_journal`, `ksa_audit_log`, `correlation_ledger`. | `KEEP` | Domain components remain logical event owners; a projected “bot journal” is never another writer. |
| K-12 | Backend PostgreSQL contains read replicas/CDC, stream replicas, certificate evidence, attribute history, sync ledger, and catalog metadata. | `KEEP` | This is distinct from the still-conditional future replacement of Trading SQLite under contention. |
| K-13 | Class-3 interchange is manifested Parquet, partitioned by pair/date/resolution; Backend is the sole finalizer and each process opens its own read-only DuckDB view. | `KEEP` | Do not share a DuckDB connection across processes. |
| K-14 | CT-SYNC is Trading→Backend, watermarked, idempotent, resumable, and verify-before-purge. ACK covers only durably stored, content-verified evidence. | `KEEP` | The wiki ratifies behavior, not all fields or transport choices. |
| K-15 | CT-SYNC heartbeat represents confirmed cross-stream consistency positions, not merely process liveness. | `KEEP` | Cadence and retention remain open. |
| K-16 | Backend may send a control-only re-request with durable watermarks after verification/restore failure; Trading re-pushes. | `KEEP` | This does not make sync bidirectional payload replication. |
| K-17 | Human promotion uses the only reverse payload path: a Trading-initiated, click-gated pull. | `KEEP` | CT-REG fields and transport details remain to ratify. |
| K-18 | SQLite backup uses the backup API and treats DB/WAL/SHM as one unit; Backend uses base backup plus WAL archive. | `KEEP` | Retention schedules are still open. |
| K-19 | Certificate live validity has one Trading Class-1 truth/read replica while the full evidence corpus remains Backend-side. | `KEEP` | Do not import certification pipeline mechanics into the Trading Node. |
| K-20 | AD-41's global stream register is only proposed. | `REOPEN` | Do not populate or call it ratified until operator countersign and Class-1 ownership fields are complete. |
| K-20A | CT-DATA-01 ownership gating requires exactly one matching row before a write; ownerless or ambiguous writes refuse before storage. The row is exactly dataset id, owner, write policy, optional retention, and optional schema reference. | `KEEP` | Placement is not ownership. Do not add store-placement fields to this contract casually. |
| K-20B | Backend PostgreSQL uses single-writer table families, forward-only contiguous migrations, SQL-hash drift detection, and in-flight-sync protection. | `KEEP` | Reconfirm the PostgreSQL version and fresh baseline DDL; resolve the wiki's open/closed wording. |

### 2.3 Registration, lifecycle, paper, and Treasury

| ID | Later delta | Disposition | Precision boundary |
| --- | --- | --- | --- |
| K-21 | Old birth-in-paper, warm-up, and examination-to-paper transitions moved out of Trading into certification. | `KEEP` | Drop the former six-transition Trading lifecycle and local `warm_up_days`. |
| K-22 | Successful human promotion triggers a Trading pull, revalidates at click time, and lands the unit in `ADMITTED`: definition/certificate/placement exist, but there are no intents and no ledger. | `KEEP` | Activation timing after admission is not final. |
| K-23 | Unified registration serves Book→BMS and bot→Book with schema, configuration, parity, and paired-demo checks; refusal is journaled; promotion stays human. | `KEEP` | CT-REG field schema remains incomplete. |
| K-24 | Once activation/birth is authorized, birth atomically creates the virtual ledger at seed `S`, emits CT-BMS-01 `re_seed` for cycle 1, and makes the unit live-ready rather than pre-live paper. | `KEEP` | The transition/timing from `ADMITTED` into birth is still unresolved; “next rollover” is only proposed. |
| K-25 | The later change is that Trading paper is **only** a fail-mechanism surface and that the GitBook's two paths are separated: Book kill-line `LIVE→PAPER` until cycle-boundary re-seed versus bot-seat breaker `LIVE→BENCHED→LIVE` with next-open auto-reset. | `KEEP` | These state-transition boundaries are ratified. Position fate/PE-7, admission activation timing, and the still-backlog runtime driver are separate open surfaces. |
| K-26 | Active Book modes are `LIVE` and `PAPER`; `BENCHED` is a roster-seat state; `STOOD_DOWN` is reserved. | `KEEP` | Current schemas mix namespaces and must be repaired before implementation. |
| K-27 | Every live account binding has a paired demo binding for fail-mechanism fills, while sensing stays on the pinned canonical live feed. | `KEEP` | No silent sibling-feed failover. |
| K-28 | `roster_capacity = 6` is provisional and distinct from `max_concurrent_live_bots = 3`. | `RECONFIRM` | Do not turn a provisional capacity into a hard-coded invariant. |
| K-29 | GitBook already had rollover-only/no-physical-withdrawal/top-up/remnant constraints. The later uncontested delta makes generic refund dormant. | `KEEP` | Failed-cycle closure, open-position behavior, and intraday-cap/sub-cap-rollover semantics remain unresolved. |
| K-29A | AD-10 ratifies missed-rollover handling as journaled catch-up/reconstruction rather than a silent skip. | `KEEP` semantics | Story 5.10 remained backlog, so the runtime driver/consumer was never completed. |
| K-29B | A later BMAD proof keeps a sweep in the same cycle, while GitBook/wiki scenario language implies reset into the next cycle. | `REOPEN` | Decide cycle-id transition/termination semantics; do not encode either reading from source precedence alone. |

### 2.4 Book grammar, attributes, risk, and positions

| ID | Later delta | Disposition | Precision boundary |
| --- | --- | --- | --- |
| K-30 | Sections 0–5 mean charter, footprint, money rules, entrance exam, leash chain, capacity/sweep. There is no current Section 6. | `KEEP` | Preserve ordinal meaning exactly. |
| K-31 | Book types are versioned JSON Schemas; Book instances are schema-validated definitions; behavior-shaping numeric values come from the registry under instance ownership. | `KEEP` | Avoid duplicating those values in an attribute store. |
| K-32 | CT-BOOK-03 adds typed filter columns plus a sparse attribute bag; it structurally refuses EAV and carries expression-index promotion metadata for hot attributes. | `KEEP` | This is the clearest high-value contract added after GitBook. |
| K-33 | Attribute definitions are immutable/versioned and inert until exact `(attr_id, version)` binding. Experimental attributes may be observed but not bound. | `KEEP` | CT-ATTR-01's register schema is still proposed. |
| K-34 | QML declarations of attributes are write-only metadata; runtime behavior reads the bot spec/config hash. A behavior-input change mints a new spec version. | `KEEP` | Prevent declaration metadata from becoming a hidden runtime channel. |
| K-35 | Dynamic SL/TP belongs to Book money-rule grammar, with BMS configuration authority and Adapter enforcement. A globally uniform stop service is rejected. | `KEEP` | Stop forms, computation owner, priority, exam pinning, and boundary position fate remain open. |
| K-36 | A 2026-07-28 planning ruling permits PE-7-neutral work: no automatic position action; open-position unrealized PnL makes reconciliation `unknown`; kill-line flip and demo routing can proceed without deciding flatten-vs-carry. | `KEEP` for scoping, `REOPEN` for position fate | The ruling was applied to current epics/status/context even though its source memo remains `RECOMMENDED` and the wiki log is incomplete. It does not resolve PE-7. |
| K-37 | Live Kelly sizing is intentionally incomplete until a trust-bounded, cost-aware input is ratified. | `REOPEN` | Never fill the gap with generic Kelly. |

### 2.5 MIS, SQS, protection, execution, and connections

| ID | Later delta | Disposition | Precision boundary |
| --- | --- | --- | --- |
| K-38 | **Operator correction, 2026-08-17:** SQS means **Spread Quality Sensor**. The legacy mechanism compares instrument-aware historical spread with current live spread, emits score/hard-block evidence, and grants MIS no trade authority. | `KEEP` ruling; exact mechanics `RECONFIRM` | GitBook already required unreachable-SQS hard block and MIS non-authority. The later “snapshot quality score” expansion is semantic drift, not closure. |
| K-39 | MIS uses one pinned live-account connection as canonical sensing feed; outage fails closed until that feed gap-replays. | `KEEP` | No silent failover to a sibling feed. |
| K-40 | BMS Exposure, not MIS, owns daily news import/compilation; affected currency expands to all containing pairs; sessions can widen but never narrow; unknown high-impact coverage blocks conservatively. | `KEEP` | News source/transport and exact calendar schema still need completion. |
| K-41 | Protection funnel is MIS senses → standalone KSA decides → Adapter enforces. KSA completion includes connection drain/quiescence. | `KEEP` | Preserve separation of information, decision, and enforcement authority. |
| K-42 | Connection Manager lives inside Adapter and is the sole owner of platform sessions, affinity, token buckets, OAuth refresh, arrival stamping, fill attribution, reconnect, and gap recovery. | `KEEP` | Do not create a second cTrader client in MIS, BMS, Book, or bot code. |
| K-43 | cTrader proof establishes application auth before account OAuth `trading`, broker `retryAfter`, explicit heartbeat/rate limits, and asynchronous fill reconciliation. | `KEEP` structure; `RECONFIRM` numbers | Recheck ≤10s heartbeat and 50/5 req/s against the current platform before treating them as fresh-project limits. This is not proof of a complete Adapter. |
| K-43A | Reconnect/retry is valid only under an accepted pool plan; recovered fills commit through Records before the connection becomes healthy; even a no-gap reconnect emits correlation evidence. | `KEEP` | Exact pool/retry/health constants remain `RECONFIRM`. |
| K-44 | cTrader amendment and partial close are feasible, but CT-ADAPTER-01 still defines only place/cancel/close-position/close-all. | `REOPEN` | `amend_order` and its semantics may not be smuggled through an opaque payload. |

### 2.6 BMS, monitoring, notification, and operator boundary

| ID | Later delta | Disposition | Precision boundary |
| --- | --- | --- | --- |
| K-46A | CT-MIS-02 direction is explicitly reconciled as Exam→MIS-Archive request and MIS-Archive→Exam result. | `KEEP` precision correction | This is a contract-direction repair, not a new Trading authority. |
| K-46B | CT-BMS-03 direction is explicitly Treasury→BMS; Adapter broker equity is upstream input to Treasury, not a CT-BMS-03 report producer. | `KEEP` precision correction | Preserve the separation between broker evidence, Treasury reconciliation calculation, and BMS verdict handling. |
| K-47 | GitBook already prohibited journal mutation. The later addition is that every state change and its required evidence commit atomically through the sole Records write path. | `KEEP` | Make owner/writer/transaction initiation explicit in the storage API. |
| K-48 | Actual notification classes are sweep, `re_seed`, refund, KSA/kill-switch, and supervision fail-closed. Other events are Console evidence/log. | `KEEP` | Delivery channels, retry, dedupe, quiet hours, and credentials remain open; refund is dormant. |
| K-49 | Prometheus/Grafana are external, read-only, and zero-authority; durable journal-commit latency is a required Trading canary. | `KEEP` | Dashboards, thresholds, alerts, and retention are not yet recovered defaults. |
| K-50 | Console commands go to Trading Powers API; stale Backend evidence cannot authorize; all click-time preconditions rerun server-side. | `KEEP` | Read/command schemas and the full powers catalog remain incomplete. |
| K-51 | Secrets use `systemd-creds`; `.env`, committed config, docs/chat, and generic plaintext stores are prohibited. | `KEEP` | Live credential provisioning/cutover remains separate work. |
| K-52 | QML is only the bot-authoring/runtime surface and stops at the Book. MIS/BMS/KSA/Adapter/Connection/Console/certification glue stays Python. | `KEEP` | CT-QML-01 currently registers zero interfaces; recovered donor API names are not authority. |
| K-53 | Empty cold start preserves required registry values as `null`, reports only `is_set:false` secret metadata, and refuses secret values through repo/chat/config/`.env`/CLI channels. | `KEEP` | Demo credential metadata is not live credential provisioning. |
| K-54 | Broker equity must be computed from balance plus quote-currency unrealized PnL because cTrader does not supply a direct equity field; per-message money precision and side-correct bid/ask valuation are evidence. | `KEEP` | Cross-currency conversion and current protocol scaling must be freshly ratified. |
| K-55 | Asynchronous fills correlate by client message id, attribute by label, and atomically update state plus CT-BMS-05 trade evidence. | `KEEP` | Reconfirm current broker label limits; this does not prove the missing command core. |

## 3. Later completed-story detail that must be re-ratified

These items are useful discoveries, but freshness is not the same as authority. They came from completed BMAD slices or generated standards and were not consistently reconciled back into the primary wiki.

| ID | BMAD-only or more-specific decision | Disposition and reason |
| --- | --- | --- |
| R-01 | CT-SYNC Class 1/2 transport is file-sync using JSONL spool + JSON manifest, temp→rename, manifest published last. | `RECONFIRM`: consistent with the ratified one-way behavior, but the wiki intentionally left transport open. |
| R-02 | Console evidence read, Console powers, and promotion pull use HTTP/JSON RPC on a trusted local channel. | `RECONFIRM`: useful V1 choice; pre-cloud authentication and venue remain unspecified. |
| R-03 | CT-SYNC envelope types are `BATCH`, `ACK`, `HEARTBEAT`, `RE_REQUEST`, `ERROR`, with shared headers and concrete proof fields. | `RECONFIRM`: serialization, hashing, cadence, retention, and auth still contain nulls; AD-41 remains proposed. |
| R-04 | Feature materialization uses DuckDB/pyarrow plus deterministic Python kernels and explicit `INSUFFICIENT_DATA`. | `RECONFIRM`: pandas, NumPy, TA-Lib, model training, and exact runtime ownership were not all ratified. |
| R-05 | Failure register schema and durable-commit metric exist, but a global failure-class catalog and thresholds do not. | `RECONFIRM`: carry schema shape only after the restart chooses its failure taxonomy. |
| R-06 | Powers proof exposes only `ratify_registry_value`. | `RECONFIRM`: this is a skeleton, not evidence that A1 resurrection, Sunday review, or promotion APIs exist. |
| R-07 | cTrader CM proof chooses app ceiling 8; per-account min/max 1/4; retry attempts 4 with 250/1000/4000/16000 ms backoff; recovery before healthy. | `RECONFIRM`: the wiki still says pool sizing, sharding, retry, and health policy are open. |
| R-08 | BMAD's `snapshot_quality_score_v1` and `sqs_weighted_component_floor_v1` define a six-component snapshot-health aggregate after SQS was mis-expanded. | `REOPEN`: it is not the Spread Quality Sensor. If a general snapshot-health aggregate is useful, specify it separately; do not rename or transplant it as SQS. |
| R-09 | MIS snapshots and degradation projection receive concrete versioned schemas, with Book/KSA seeing the same immutable evidence and missing classifiers degrading explicitly rather than becoming silent null/default values. | `RECONFIRM`: preserve determinism and provenance after first resolving the direct-consumer conflict. |
| R-09A | MIS archive proof uses manifest-gated visibility and `source_class / venue / pair / date / resolution` partitioning with a sole Backend finalizer. | `RECONFIRM`: keep authority/visibility semantics; the proof payload was not a complete Parquet runtime. |
| R-09B | CT-MIS-02 stays a five-field bounded request and hashes searched/hidden partitions plus emissions; a deferred mismatch leaves `emission_utc` placement open. | `RECONFIRM`: settle timestamp ownership in the public manifest/query contract. |
| R-09C | Materialization emits CT-MIS-shaped evidence under `source_class: materialized_backfill` while preserving source snapshot identity and making no live-fanout claim. | `RECONFIRM`: recover only the MIS lane, not Backtest/Examination machinery. |
| R-10 | Local Book identity is `book:{slug}` and stored in one SQLite DB with journaled slot values. | `RECONFIRM`: global identity policy remains unresolved. |
| R-11 | BMS owns the exact mode registry and later story standards encode concrete allowed/refused values. | `RECONFIRM`: those schemas currently blur Book mode, seat state, and reserved values. |
| R-12 | Treasury proof spells out exact birth, sweep, and closed-boundary refusal semantics. | `RECONFIRM`: the structural rules align with wiki; position fate and refund remain unclosed, while missed-rollover semantics are ratified but their runtime path was unimplemented. |
| R-13 | Paper proof accepts caller-supplied transition facts and explicitly omits detector/routing execution. | `RECONFIRM`: it proves journal semantics, not the still-backlog kill-line detector. |
| R-14 | CT-BMS-03 proof computes residual `broker - virtual - explained` and returns `reconciled`, `drift`, or `unknown`; only unexplained live drift causes technical kill and no automatic resume. | `RECONFIRM`: valuable exact semantics, but PE-7 open positions force `unknown` and resume authority is unbuilt. |
| R-15 | Fill reconciliation uses `clientMsgId`, a ≤100-character label, CT-BMS-05 trade journal, and atomic state/evidence. | `RECONFIRM`: useful cTrader proof detail; do not infer complete command-adapter or recovery behavior. |
| R-16 | A failure-register proof seeds eight sync classes: verification mismatch, backend ingest failure, backlog alert, unrecoverable gap, schema mismatch, money-encoding violation, auth failure, and transport error. | `RECONFIRM`: reuse their meanings if the new global failure taxonomy admits them; the global catalog is still open. |
| R-17 | CT-PAPER-01 proof adds frozen Decimal balance, trigger kind, paired-demo id, sensing/paper evidence, and live-drift exclusion. | `RECONFIRM`: Story 5.8 explicitly treats this as local proof shape, not global contract ratification. |
| R-18 | Story 2.3 recorded TrueFX as internal-only/no redistribution, excluded HistData for lack of a compatible grant, and left Dukascopy unresolved/restrictive. | `RECONFIRM`: preserve as 2026-07-26 acquisition provenance only, verify current source terms, and do not call it proof that data was acquired. |

## 4. Contradictions and false-completion traps

| ID | Conflict or hazard | Required handling |
| --- | --- | --- |
| C-01 | Wiki/AD-19 permits manifest-bounded bots or QML fields as MIS consumers; completed Story 3.2 permits only Book and KSA and explicitly forbids direct bot delivery. | `REOPEN`: choose one consumer boundary and update CT-MIS-01, Book manifest semantics, and tests together. |
| C-02 | Wiki prose says active Book modes are `LIVE/PAPER`, `BENCHED` is a seat state, and `STOOD_DOWN` reserved; current contract/story schemas mix the namespaces. | `REOPEN`: define separate enums before coding. |
| C-03 | Some pages summarize “18 ratified contracts” although several contract pages/fields are draft, schema-pending, proposed, or zero-entry. | Count contract identifiers separately from schema/readiness status. Never use the headline as implementation readiness. |
| C-04 | The 2026-07-28 position-boundary page lacks matching wiki log/front-matter provenance, although current BMAD epics/status/context apply its neutral scoping rule. | Keep the narrow proceed-without-position-action scope; verify provenance during redocumentation and leave final PE-7 position fate `REOPEN`. |
| C-05 | Some pages leave Trading SQLite→Postgres contention migration open while another architecture summary reads as closed. | Preserve SQLite for V1; make migration trigger/decision an explicit future ADR. |
| C-06 | Older security language refers generically to a secret store while operations later fixes `systemd-creds`. | Use `systemd-creds`; purge stale generic wording during redocumentation. |
| C-07 | BMS failure text appears to cite stale `GAP-0010`; the relevant gap is likely `GAP-0008`. | Repair the cross-reference only after checking the new gap registry. |
| C-08 | Domain pages call components “owner” of events while Records is the sole writer. | Document logical owner, physical writer, and transaction initiator as distinct columns. |
| C-09 | Topology is fixed as one Trading process, but recovered service-boundary pages propose Replay/Analytics/Decay/Records Read/Position Safety services. | Keep them proposed or drop them; do not make them current deployment topology. |
| C-10 | Acquisition stories prove governance and acceptance mechanics, not that a complete usable dataset was acquired. | Do not recover TrueFX/HistData/Dukascopy status as Trading runtime capability. |
| C-11 | Stories 4.4–4.7 prove equity/fills/demo/CM slices while base Adapter stories 4.1–4.3 remained backlog. | Do not claim a complete Adapter. Re-specify the command seam first. |
| C-12 | Story 5.8 proves paper-transition journaling while kill-line detector Story 5.7 remained backlog. | Do not claim the fail mechanism exists end-to-end. |
| C-13 | Story 5.9 proves reconciliation semantics while position fate and resume authority remain open. | Keep `unknown` behavior and human authority explicit; no automatic resume. |
| C-14 | Doors, KSA completion, QML, registration/promotion, reporting, and metrics epics contain extensive backlog despite detailed planning prose. | Planning prose is not implementation evidence. Start from contracts/invariants, not the old sprint's percent complete. |
| C-15 | Wiki Treasury prose says birth freezes paper balance at `S`; later Story 5.4 says birth is LIVE-ready/not PAPER; Story 5.8 freezes only on a later fail-mechanism transition. | `REOPEN`: decide admission→birth→activation→paper ordering explicitly. The post-AD-28 model is the stronger candidate, not automatic authority. |
| C-16 | The wiki's six-field CT-PAPER-01 shell differs from Story 5.8's richer local proof schema, which expressly avoided global field ratification. | `REOPEN`: ratify one public schema instead of copying the proof database shape. |
| C-17 | GitBook says Notification proposes severity, yet its incoming CT-NOTIFY-01 already requires `proposed_tier`; the later wiki narrows real notification events but does not close delivery ownership. | `REOPEN`: separate classification, candidate production, delivery, and journal evidence. |
| C-18 | GitBook says BMS owns KSA policy while KSA owns protection state, producing a cyclic dependency without explicit initialization/recovery ordering. | `REOPEN`: preserve the MIS→KSA→Adapter funnel and separately define policy source, state writer, recovery, and BMS read dependencies. |
| C-19 | GitBook's “bot is the only market-touching actor” can be read literally against Adapter's physical broker contact. | Clarify that bots own trade intent/entry-exit logic; Adapter alone owns the physical platform session and mechanical execution. |
| C-20 | GitBook formula names/units mix `R` and USD and cannot be normalized safely from prose. | `REOPEN`: define dimensions for every registry variable/formula before implementing money rules. |
| C-21 | GitBook routes Book-mode writes inconsistently among Book, Paper, and BMS even though BMS owns the authoritative mode map. | `REOPEN`: distinguish transition request, validation, authoritative write, event, and CT-BMS-02 read. |
| C-22 | GitBook uses CT-PAPER-01 both as a Scalper/Book→Paper request and a Paper→BMS transition. | `REOPEN`: the new global contract must separate requested facts from authoritative transition evidence. |
| C-23 | The later wiki corrects CT-BMS-01's event direction to Treasury→BMS Records, but the old path still conflates request, approved Treasury transaction, and recorded event. | Keep the corrected Records event direction; explicitly model any upstream invocation rather than overloading CT-BMS-01. |
| C-24 | GitBook defines a cycle as seed→cap and also requires kill-line paper until cycle-boundary re-seed, but never defines how a failed sub-cap cycle closes or what intraday cap contact followed by sub-cap rollover means. | `REOPEN`: reconcile the later same-cycle sweep rule with an explicit successful/failed cycle state machine and re-seed authority. |

## 5. Items to leave behind

| ID | `DROP` item | Reason |
| --- | --- | --- |
| D-01 | Agentic runtime, agent harness, WF1/WF2, and Backtest/certification internals. | Explicitly outside this recovery and slated for redesign. |
| D-02 | Donor-only DPR, slot machinery, workflow transitions, and recovered “attic” services. | Historical evidence was never made current Trading authority. |
| D-03 | Recovered QML module/type/API names. | CT-QML-01 has zero ratified interfaces. |
| D-04 | Separate passive cold-tier shelf. | Superseded by Backend cold storage. |
| D-05 | Microservice-per-component Trading topology. | Superseded by one deterministic Trading process. |
| D-06 | Birth-in-paper, pre-live warm-up, local examination-to-paper flow, and `warm_up_days`. | Moved to certification; not part of Trading lifecycle. |
| D-07 | Globally uniform stop service. | Superseded by Book money-rule grammar + BMS config + Adapter enforcement. |
| D-08 | EAV storage for Book attributes. | Structurally rejected by CT-BOOK-03. |
| D-09 | Any expansion of SQS as snapshot quality score, signal quality score, Simple Queue Service, or any use of SQS as execution authority. | Vocabulary is closed by the operator: **Spread Quality Sensor**. MIS transports; the Book door decides. |
| D-10 | Silent canonical-feed failover and independent live/demo ordering. | Violates pinned-feed and shared-sequencer rules. |
| D-11 | Automatic promotion, automatic resume after drift/kill, or stale Backend evidence authorizing actions. | Operator/Powers and click-time authority boundaries reject them. |
| D-12 | Per-Book databases, multiple journal writers, in-place journal correction, or Backend write authority. | Violates later persistence invariants. |
| D-13 | Old proof-local SQLite owner guards, spoofable write windows, or coupling owners to a private `RecordsStore._authorize`. | Deferred defects explicitly warn against recovering these implementation seams; design a public atomic owner/Records transaction boundary. |

## 6. Open frontier the new design must close deliberately

These are not missing recoveries; they are genuine architectural work that remained unfinished:

1. Stop-policy forms, SL/TP computation owner, close priority, exam pinning, and position fate at rollover/sweep/kill/paper boundaries.
2. Trust-bounded cost-aware Kelly input and any remaining money-rule formula domains.
3. Full KSA trigger→level matrix, especially connectivity and unknown-state handling.
4. Final platform-blind Adapter command contract, including `amend_order`, partial close, idempotency, timeout/retry, recovery, and exact error taxonomy.
5. Clean Book-mode, bot-seat-state, supervision-state, and admission/activation state machines.
6. MIS direct-consumer decision: Book/KSA only versus manifest-bounded bot delivery.
7. CT-SYNC serialization/hash/auth/cadence/retention, AD-41 countersign, and backlog/retention values.
8. CT-REG, CT-ATTR, CT-QML, Console/Powers, notification delivery, and monitoring schemas.
9. Canonical global Book identity and any cross-node identity namespaces.
10. Connection-pool sizing/sharding/recovery and product retry/health policy beyond broker proof constraints.
11. Crash-loop thresholds, journal latency thresholds, backend reachability at preflight, and failure-class catalog.
12. Missed-rollover catch-up runtime wiring, reconciliation with open positions, resume authority, and dormant refund semantics.
13. Canonical manifest serialization before any acquisition/archive hash becomes authority, plus the authoritative forex universe/source rather than a proof-local allow-list.
14. Reconciliation freshness bound, versioned Treasury as-of evidence, and the exact paper-binding exclusion identity.
15. Failed-cycle closure, intraday cap contact versus rollover qualification, and the authority for the next re-seed after kill-line stand-down.
16. The Story 3.5/3.6 replay-contract mismatch: interval replay requires `emission_utc`, but the archive manifest did not ratify where that value lives.
17. Maximum accepted length/canonical form for Treasury `amount_decimal` money text; no numeric default may be inferred from the old proof.

The safe restart is therefore **not** “copy the newest files.” It is: retain GitBook's conceptual core, apply the `KEEP` layer, explicitly ratify the `RECONFIRM` layer, resolve the `REOPEN` layer, and exclude every `DROP` item.
