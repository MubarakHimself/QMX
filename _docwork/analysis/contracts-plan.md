# Stage 5 contracts and dependency plan — QMF V1

**Internal planning artifact.** This proposes the smallest honest machine-checkable skeleton for Stage 5. It does not create `docs/`, ratify studies, choose schemas, or change the five-libraries-plus-two-modules product roster.

## 1. Layering law

- Manifest dependency edges run `middleware → backend → data`; same-layer and skip-layer edges are permitted; edges touching `external` are exempt.
- Data flow and dependency direction are not identical. A backend command may travel to a middleware adapter, but the adapter depends on the backend-owned port contract—not the backend on the adapter implementation.
- `qmf-core`, registry policy, indicator logic, structure logic, and risk rules are `backend` concerns. They do not render and do not know UI exists.
- External-source/broker adapters, authentication shaping, capability discovery, rate limiting, and validation sit in `middleware`. They do not own trading, split, holdout, promotion, or risk laws.
- Physical stores, migrations, retention implementation, and backup media sit in `data`. Stores do not own holdout, promotion, or risk rules through triggers/views.
- No UI component or UI contract belongs in QMF V1; Simulator/operator UI is deferred.

## 2. Proposed component manifest

The first seven rows are the **final public roster**. Supporting seam components below them are internal implementation boundaries, not extra QMF libraries.

| Component ID | Kind | Layer | Public roster role | Source-backed responsibility | Must remain GAP/provisional |
|---|---|---:|---|---|---|
| `COMP-QMF-CORE` | `library` | `backend` | `qmf-core` | Exact-money/time direction; asset-neutral domain nouns; typed refusals; canonical serialization/fingerprints; versions mint rather than overwrite; no loop/broker/backtest/download. | Public API, money precision/rounding, calendars, instrument identity, refusal enum, serialization bytes, fingerprint algorithm/evolution, compatibility policy, and the six frozen choices. |
| `COMP-QMF-REGISTRY` | `library` | `backend` | `qmf-registry` | Identity and graph-shaped lineage in principle; registration causality/look-ahead and attempt-count gates. | Exact kinds, fields, charter/occurrence rules, Bot career/variant semantics, edge enum, transactions, gate inputs/results, counter scope/reset, and persistence format. Fingerprint/charter/occurrence is study-derived. |
| `COMP-QMF-DATA` | `library` | `backend` | `qmf-data` policy/API portion | Data contracts; raw-versus-processed distinction; journal; split/holdout rules; keep all history; newest-year seal; access to research data; backup requirement. | Exact six layers, record schemas, bitemporal fields, split registry, stream list/cadence/retention, store selection, migration, backup/restore, and app-vs-QMF lifecycle seam. |
| `COMP-QMF-INDICATORS` | `library` | `backend` | `qmf-indicators` | Light/incremental indicator direction; wrap suitable libraries rather than reinvent; heavy MIS work is outside. | Protocol, input/output schema, warmup/stability metadata, replay equivalence, canonical arithmetic/oracles, wrapper list, and versioning. |
| `COMP-QMF-STRUCTURE` | `library` | `backend` | `qmf-structure` | QMX-owned causal levels/zones/market-structure components; research ideologies but no code transplantation. | Family taxonomy, Level/Trigger/Confirmation schemas, composition/cardinality, causal proof envelope, and first supported families. |
| `COMP-VENUE-ADAPTER` | `middleware` | `middleware` | Venue module | Small Python cTrader Open API seam now; later crypto/equity adapters; connection is separate from backtesting parity. | Port shape, commands/events, auth lifecycle, capabilities, price basis, idempotency, reconciliation, rate limits, outages, tick retention, and approval status. It is not a broker runtime loop. |
| `COMP-RISK` | `library` | `backend` | Risk module | Versioned/updatable Books+BMS V1 direction; money/risk allocation, exits, correlation concerns; Book-level paper mode direction. | Book schema, BMS multiplicity, money formulas, exit ownership, transition rules, account binding, seat/bench semantics, same-tick priority, SQS/news interaction, and all detailed node mechanics. |
| `COMP-QMF-DATA-INGEST` | `middleware` | `middleware` | Internal to `qmf-data` | Source adaptation, validation, and normalized handoff into QMF data policy/API. | Which sources ship in V1, adapter plugin/extension mechanism, scheduling ownership, retry/rate semantics, and ingest envelope fields. |
| `COMP-QMF-DATA-STORE` | `store` | `data` | Internal to `qmf-data` | Persistence seam for raw evidence, processed records, journal, registry records, and lineage as ratified later. | Physical engines, tables/files, columns/types/nullability, indexes/partitions, migrations, retention, JSONL decision, and valid-time/known-time implementation. Do not assume Parquet/DuckDB/SQLite yet. |
| `COMP-QMF-DATA-BACKUP` | `process` | `data` | Internal to `qmf-data` | Nightly off-site backup direction and restore responsibility. | Provider, object layout, encryption, cadence exactness, retention, verification, recovery objectives, and restore receipt schema. |
| `COMP-CTRADER` | `external` | `external` | External dependency | Current real venue direction through cTrader Open API. | Approval, exact API version/capabilities, authentication facts, BID-vs-mid trendbars, limits, and guarantees. |
| `COMP-DUKASCOPY` | `external` | `external` | External dependency | Historical backfill source; plumbing now, bulk download at first install. | Instrument coverage, data quality/licence, limits, gaps, and exact ingestion contract. |
| `COMP-CALENDAR-FEED` | `external` | `external` | External dependency | Calendar forward snapshots support news blackout; feed lacks actual-release values. | Legal archival posture, schema stability, source identity, rate limits as contractual guarantee, and future paid source. |
| `COMP-OBJECT-STORAGE` | `external` | `external` | Conditional external dependency | Off-site bucket direction. | Provider and every operational/security property. Do not select B2/R2 from study prose. |

### Conditional/context-only component

`COMP-CALENDAR-RECORDER` may be recorded as `kind: process`, `layer: middleware` only if the final ledger treats the already-running standalone recorder as part of the documented system rather than operating context. It remains **outside QMF** and must not be disguised as a sixth library or a `qmf-data` scheduler. It would depend on `COMP-CALENDAR-FEED` and hand observations to `COMP-QMF-DATA` through the ingest contract.

### Components intentionally absent

- No `COMP-QMF-MIS`: MIS is a future trading-node consumer, not a QMF library.
- No QML/Bot library, researcher/backtesting component, agent surface/harness, UI/Simulator, prop-firm Book, or trading-node runtime in the V1 dependency manifest.
- No graph-database component unless Stage 4 reverses the direct “no graph” ruling.
- No generic `COMP-QMF-RUNTIME`; it would resurrect the retired kernel.

## 3. Proposed dependency graph

This is the maximum safe graph supported by current evidence; optional edges stay out until a contract proves them necessary.

```text
COMP-QMF-CORE

COMP-QMF-REGISTRY
  -> COMP-QMF-CORE
  -> COMP-QMF-DATA-STORE       # persistence seam only; never qmf-data policy/API

COMP-QMF-DATA
  -> COMP-QMF-CORE
  -> COMP-QMF-REGISTRY         # dataset/record identities and registration gates
  -> COMP-QMF-DATA-STORE

COMP-QMF-DATA-INGEST
  -> COMP-QMF-DATA
  -> COMP-QMF-CORE
  -> COMP-DUKASCOPY / COMP-CALENDAR-FEED (external, conditional by adapter)

COMP-QMF-DATA-BACKUP
  -> COMP-QMF-DATA-STORE
  -> COMP-OBJECT-STORAGE (external)

COMP-QMF-INDICATORS
  -> COMP-QMF-CORE
  -> COMP-QMF-DATA             # only through a ratified observation/data-view contract

COMP-QMF-STRUCTURE
  -> COMP-QMF-CORE
  -> COMP-QMF-DATA             # only through causal observation/data-view contract
  -> COMP-QMF-REGISTRY         # only if registration/lineage is in the first slice

COMP-VENUE-ADAPTER
  -> COMP-QMF-CORE             # backend-owned port/domain contracts
  -> COMP-QMF-DATA             # normalized event/journal intake, not direct store access
  -> COMP-CTRADER (external)

COMP-RISK
  -> COMP-QMF-CORE
  -> COMP-QMF-REGISTRY
  -> COMP-QMF-DATA             # journal/snapshot API, not physical store knowledge
```

### Dependency prohibitions

- `COMP-QMF-CORE` depends on none of the other owned components.
- `COMP-RISK` does **not** depend on `COMP-VENUE-ADAPTER`; that would be a backend→middleware upward edge. A future application orchestrator consumes risk decisions and a backend-owned venue port while the middleware adapter implements the port.
- `COMP-QMF-INDICATORS` and `COMP-QMF-STRUCTURE` never depend on MIS or the trading node; those are consumers.
- `COMP-QMF-DATA-STORE` never depends on `COMP-QMF-DATA`, registry policy, or risk rules. Doing so would put business law in the data layer and create cycles.
- Registry must not depend on the `qmf-data` policy API if `qmf-data` depends on registry. Both may depend downward on the neutral store seam. This is the cleanest way to avoid a registry↔data package cycle.
- Ingest and venue middleware never own holdout, split, promotion, SQS, news, or risk rules; they validate/translate and hand off.

## 4. Contract inventory

IDs are proposed routing labels only. No field becomes real until the ledger supplies it or a GAP is ratified.

### Core same-layer contracts

| ID | Seam | Source-backed semantics | Keep GAP |
|---|---|---|---|
| `CT-01` Money/Quantity | `backend → backend` | Money/time must be exact; `R` is one unit of original pre-trade risk in later risk context. | Currency/asset field, decimal representation, precision, rounding, quantity/price units, negative/zero rules, overflow, serialization. |
| `CT-02` Time/Trading Calendar | `backend → backend` | Exact time; FX rollover/week/weekend/DST facts; two-timestamp anti-look-ahead requirement. | Field names, timestamp precision, UTC-ns choice, timezone/calendar IDs, session/open rules for Forex/crypto/equity, valid-time vs known-time encoding. |
| `CT-03` Instrument/Venue Identity | `backend → backend` | Foundation must be asset neutral and order-flow capable; `(venue,symbol)` opaque identity is a pending candidate. | Identity tuple, symbol normalization, asset-class enum, venue IDs, contract/spot/perp/equity details, equality/version rules. |
| `CT-04` Typed Refusal | `backend → backend` | Typed refusals belong in qmf-core; money-path behavior fails closed directionally. | Refusal code enum, message/details, retryability, causality/provenance, serialization, exception mapping. |
| `CT-05` Definition Version/Stamp | `backend → backend` | Canonical serialization/fingerprint; definitions version from birth; changes mint new versions; results are content-addressed. | Canonical byte format, hash, collision policy, version syntax, mutable metadata, compatibility/deprecation, result-key tuple. |

### Registry contracts

| ID | Seam | Source-backed semantics | Keep GAP |
|---|---|---|---|
| `CT-06` Registration | `backend → backend` | Identity/lineage accepted in principle; registration runs causality/look-ahead and attempt gates. | Request/result fields, kind enum, atomicity, refusal codes, operator signature, idea-origin timing, opaque Python definition handling. |
| `CT-07` Lineage Edge | `backend → backend` | Lineage is graph-shaped; Bot revisions/variants require relationships directionally. | Edge enum, endpoints, cardinality, DAG/cycle rules, temporal fields, amendment/deletion semantics. Do not copy the study's 16-edge catalog automatically. |
| `CT-08` Gate Evidence | `backend → backend` | Causality/look-ahead test and attempt counting are retained registration preconditions. | Test input, evidence artifact, pass/fail schema, attempt scope/budget/reset, oracle identity, human override. |
| `CT-09` Registry Persistence | `backend → data` | Identities, versions, lineage, and occurrences require persistence. | Every record field/type/nullability, append-only guarantee, transaction boundary, JSONL/table/files, compaction, recovery, migrations. |

### Data contracts

| ID | Seam | Source-backed semantics | Keep GAP |
|---|---|---|---|
| `CT-10` Source Observation | `middleware → backend` | Raw evidence differs from processed data; calendar/tick observations must retain provenance and known-time semantics. | Schema, required timestamps, source/venue IDs, quality flags, units, duplicate keys, ordering, nullability, raw payload retention. |
| `CT-11` Evidence Persistence | `backend → data` | Keep all obtainable history/raw evidence; processed and journal records are distinct concerns. | Tables/files/columns, partition keys, indexes, compression, migration, bitemporal representation, retention per class. |
| `CT-12` Dataset/Split/Holdout View | `backend → backend` | Splits are supplied by default; newest ~12 months are sealed from experiments while all history remains stored. | Dataset identity, split enum, date arithmetic, one-look authorization/log, leakage rules, refresh/reseal, live-performance eligibility for training. |
| `CT-13` Journal Append/Read | `backend → data` | Trading journal and per-component evidence are required; metrics should expose why strategies fail. | Stream enum, event schema, cadence, retention, ordering, correlation IDs, component snapshots, read/query contract. The study's 12 streams are not yet authoritative. |
| `CT-14` Backup/Restore | `data → external` | Off-site/nightly backup direction and restore responsibility. | Provider API, object manifest, encryption, credentials, RPO/RTO, verification, retention, deletion, restore receipt. |
| `CT-15` External Source Adapter | `external → middleware` | Dukascopy historical backfill and calendar forward capture are named sources; calendar lacks actual values. | Exact external schemas, version guarantees, legal terms, limits, retries, provenance, and capability differences. This contract documents what QMF can rely on, not what it can change. |

### Indicators and structure

| ID | Seam | Source-backed semantics | Keep GAP |
|---|---|---|---|
| `CT-16` Indicator Component | `backend → backend` | Light indicators are Bot/strategy-level and may wrap permitted libraries; heavy ensemble/regime work belongs to MIS outside V1. | Definition/input/output fields, warmup, stability, state checkpointing, incremental/replay equivalence, reference arithmetic, versioning, errors. |
| `CT-17` Causal Structure Component | `backend → backend` | QMX-owned Level/Zone/Trigger/Confirmation building blocks; Trigger is the exact trade-entry event; causality is load-bearing. | Family enum, fields, timeframes, one/many composition, evidence/look-ahead proof, invalidation, versioning, output shape. |

### Venue seam

| ID | Seam | Source-backed semantics | Keep GAP |
|---|---|---|---|
| `CT-18` Venue Capabilities | `middleware → backend` | Current adapter targets cTrader Open API and future venue plurality. | Capability enum, symbol catalog, time/price basis, order types, account modes, limits, version negotiation. |
| `CT-19` Venue Command | `backend → middleware` | A backend-owned port lets future orchestration request venue work without binding to cTrader. | Command enum and every field, idempotency key, quantity/price semantics, deadlines, refusal/error mapping, auth context. **Manifest dependency remains middleware→backend despite payload flow.** |
| `CT-20` Venue Event/Reconciliation | `middleware → backend` | Real venue outcomes must be normalized for consumers/journal; connection is separate from backtest parity. | Event enum, order/fill/position schemas, sequence/order guarantees, deduplication, reconciliation cursors, outage/reconnect behavior, BID-vs-mid basis. |
| `CT-21` Venue Secret/Session Boundary | `external → middleware` | OAuth refresh, VPS secrets, token expiry, and broker outages are named operational concerns. | Secret locations/rotation, scopes, expiry, refresh, revocation, fail behavior, flattening responsibility. Never record values. |

### Risk seam—placeholder contracts only

These IDs reserve seams; Stage 5 must not fabricate their schemas before the node/Book reconciliation.

| ID | Seam | Source-backed semantics | Keep GAP |
|---|---|---|---|
| `CT-22` Book Charter/Configuration | `backend → backend` | A Book is specific, has a GitBook schema, variables/default/editability, operator-in-loop deployment, and versioned variants. | Entire machine-readable schema, money math, config mutability, inheritance/version rules, signatures, BMS link. |
| `CT-23` Risk Evaluation/Refusal | `backend → backend` | Book/BMS own money permission, sizing/risk, exits directionally; Bots do not carry money quantity. | Inputs, outputs, sizing math, exit ownership, priorities, refusal enum, correlation inputs, failure modes. |
| `CT-24` Book Mode/Account Transition | `backend → backend` | Recorded ruling: paper mode is Book-level; one Bot binds one Book; no Bot twin; promotion is human-only. | Direct-evidence confirmation, state enum, transition triggers, account binding, demo-account roles, result continuity, rollback. |
| `CT-25` Risk/Book Journal | `backend → backend` | Book/BMS/MIS/SQS/kill-switch evidence should be collected and diagnosable. | Snapshot/event fields, cadence, correlation, retention, quantities, alpha-decay signals, privacy/security. It hands to `COMP-QMF-DATA`, never writes the store directly. |

## 5. Values/formulas registry plan

### Enter as known or bounded values only if their ledger decisions survive Stage 4

| Proposed registry name | Value/class | Component | Status note |
|---|---|---|---|
| `original_risk_unit` (`R`) | `1`, units `risk-unit`, type `ratio` or domain value | `COMP-RISK` | Meaning is source-backed; detailed formula/use is later. Do not revive broken FORM-0006. |
| `historical_holdout_months` | approximately `12`, units `months`, type `duration` | `COMP-QMF-DATA` | Direction selected, but exact boundary/date arithmetic and configurability require ratification. Prefer `value: null` + GAP if “~12” cannot be represented honestly. |
| `news_blackout_before` | candidate `15`, units `minutes` | `COMP-RISK` | Provisional: operator said “I think/believe.” |
| `news_blackout_after` | candidate `15`, units `minutes` | `COMP-RISK` | Provisional for the same reason. |
| `design_bot_concurrency` | approximately `40`, units `bots`, type `count` | cross-cutting/performance | Real scenario, not a measured 95th-percentile SLO. Use notes; do not claim exact capacity. |
| `fx_rollover_time` | `17:00 America/New_York`, type `string/time` | `COMP-QMF-CORE` | Domain input; exact DST/session semantics remain GAP. |
| `triple_swap_day` | `Wednesday`, type `enum` | `COMP-QMF-CORE` or risk | Domain input, but swap-free account context means financing may be admin fee. Confirm whether V1 needs this variable. |
| `bench_stopout_threshold` | `2`, units `consecutive-stop-outs`, type `count` | `COMP-RISK` | Deferred risk/node variable; unusable until `stop-out` is defined. |
| `bench_reset_boundary` | `next_open`, type `enum` | `COMP-RISK` | Deferred risk/node value. |
| `calendar_recorder_schedule` | `06:00,18:00 local`, operational enum/string | conditional recorder | Existing process fact, not QMF library config; timezone is missing. |
| `calendar_feed_rate_limit` | approximately `2 per 5 minutes`, external constraint | conditional recorder | Observed/feed constraint, not a promise QMF owns. |

### Create null-valued registry entries backed by GAPs

- `timestamp_precision` / `timestamp_unit` — UTC nanoseconds is proposed, not ratified.
- `instrument_identity_shape` — `(venue, symbol)` opaque symbol is proposed, not ratified.
- `backtest_fidelity` — candidate enum `bar_close | intrabar | tick`, outside V1 except neutral result labels.
- `strategy_quality_threshold` (`SR*`) — value absent and backtesting deferred.
- `result_identity_key` — tuple fields absent.
- `canonical_indicator_reference` — TA-Lib-as-canonical is pending even though wrappers are directionally accepted.
- `sqs_formula` and every SQS threshold — formula unratified.
- Money precision, rounding mode, quantity precision, and currency normalization.
- Backup RPO/RTO/retention and restore-verification threshold.
- Attempt budget/reset/window for registry gates.

### Never enter as live variables

- PRS six weights, 0–100 score, three tiers, or DPR ten-day tier: dead legacy evidence.
- FORM-0006: dimensionally broken and explicitly never implement as-is.
- Recorder snapshot counts `96`/`8`: ephemeral observations.
- `100–150 factory-days`, `~5 papers`, `~quarterly ML training`, and `~2 rebuilds/year`: estimates/process ambitions, not runtime configuration.
- “95th percentile”: assistant shorthand, not a measured percentile variable.

## 6. High-risk layer modeling traps

### `qmf-data` is not one layer

The package name does not make every concern `layer: data`. Source adaptation is middleware; split/holdout/journal policy is backend; physical storage/migration/retention implementation is data. Modeling one `COMP-QMF-DATA` store that “also ingests and decides splits” would:

- hide an external→middleware contract;
- put leakage/holdout business law into tables/triggers;
- make adapters directly reach stores;
- blur backup mechanics with backup policy;
- create a registry↔data dependency cycle; and
- silently ratify the six-layer study and exact stack.

Keep the public `qmf-data` library component for policy/API, then draw ingest, store, and backup support components behind explicit contracts.

### Venue adapter cannot own trading or risk

The venue module is middleware because it adapts cTrader/external systems. It may validate shape, discover capabilities, rotate credentials, translate commands/events, rate-limit, and reconcile. It must not decide promotion, Book mode, sizing, news blackout, SQS, or kill-switch business behavior. Risk and future orchestration own those laws.

Do not make risk depend on venue middleware. Define a backend-owned venue port; the adapter depends on and implements it. Command payload may flow backend→middleware without reversing the manifest dependency.

### Risk module is backend, not an adapter or store

Risk owns business rules and may depend downward on qmf-data contracts. It should emit journal/snapshot events through `COMP-QMF-DATA`, not write physical stores. It should not absorb broker auth/session lifecycle merely because both were called “two small modules.” The risk module must remain a placeholder until the Book schema and exit conflicts are reconciled.

### Registry persistence must not force JSONL/Neo4j

Graph shape is a domain property; graph database is rejected for V1. Append-only JSONL is a study proposal, not yet a contract. `CT-09` should describe persistence semantics only after ratification; the store implementation remains behind `COMP-QMF-DATA-STORE`.

### Support components do not change the public roster

Splitting `qmf-data` across layer seams adds manifest nodes, not product libraries. Documentation must still say “five libraries plus two modules.” Conversely, using the public roster as an excuse to collapse middleware/backend/data into seven monolith nodes would violate Stage 5’s split-along-the-seam rule.

## 7. Stage 5 stop conditions

Do not generate contract schemas until Stage 4 resolves at least:

1. six frozen technical choices;
2. dependency/licence law;
3. Bot confluence cardinality;
4. qmf-data/app acquisition seam;
5. registry/data study details selected versus deferred;
6. C0022-derived Book-level paper/one-Bot-one-Book confirmation; and
7. whether risk-module placeholder contracts are allowed before the dedicated node/Book session.

If those remain open, Stage 5 may safely emit component IDs, layers, dependency directions, empty schema skeletons linked to GAPs, and glossary seeds—but not invented fields, enums, formulas, or sample payloads.
