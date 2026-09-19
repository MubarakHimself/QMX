# PASS I — sequence scenario families (Luna)

Scope: derived only from the authorized `pass1-sources` files. These are challenge scenarios, not implementation requirements. IDs are local and deduplicated.

## Scenario-family matrix

| ID | Family / participants | Composition and payload | Lifecycle / state sequence | Feasible preconditions | Observable success | Forbidden effect / trap | Recovery + oracle |
|---|---|---|---|---|---|---|---|
| SF-01 | Install/discover (operator, extension registry, app shell, copilot) | Manifest → typed capabilities: resources, ops, apps, streams, jobs, widgets; owner/version/scopes/cost | validate → index rebuild → available/unavailable | package present; IDs/version/schema declared | rows expose owner, version, health, unavailable reason | manifest text self-grants; duplicate IDs silently overwrite; fourth Library kind | retain prior index atomically; diagnostics and manifest-validation evidence |
| SF-02 | Data query (user, provider adapter, catalog) | `DataResource` + provider + symbols/window/fields/limits → typed result envelope | discover → preflight → preview → query/export | provider coverage and entitlement known | schema, units, timezone, freshness, provenance, truncation visible | silent provider merge; raw/adjusted ambiguity; hidden entitlement failure | field-level unsupported/empty/quota/timeout state; provider request/response + checksum |
| SF-03 | Recipe/reproducibility (researcher, QMF/QMB/QML) | versioned recipe binds snapshots, transforms, calendar, costs, split, executor, seed | draft → validate/leakage check → save immutable version → run | source snapshots and transform schemas available | same inputs yield comparable artifacts with lineage | look-ahead leakage; later revisions rewrite old run; incomparable metrics | reject with precise reason; pin original resource/run; recipe + run manifest oracle |
| SF-04 | Job/artifact lifecycle (operator, runner, quota/audit, artifact store) | immutable run request → job events/logs/metrics/artifact refs | validate → estimate/approve → queue → running → terminal | budget/quota, permissions, definition versions resolved | stable run ID, progress, terminal reason, checksum/expiry | hidden retry; cancellation reported as success; partial artifacts implied complete | explicit failed/cancelled/unknown/expired; resume/retry policy and event log |
| SF-05 | Workflow composition (author, graph runtime) | typed nodes with fan-out mode (broadcast/zip/keyed/cartesian), selected subgraph | draft board → selected execution → checkpoint/branch → complete | input/output schemas and edge semantics valid | attempted/skipped/failed branches and join cardinality inspectable | draft ≠ runnable whole; accidental Cartesian explosion; implicit join | reject invalid edge; quota preflight; run trace is oracle |
| SF-06 | Copilot authority (authoring user, app-use user, QMA tools) | authoring diff vs app-scoped query/action; tool side-effect/scope metadata | propose → diff/validate/preview → explicit save; app-use query → approval if risky | session role and capability token granted | exact diff/result, approval and audit records | app-use gains authoring/credential/trading scope; citation retargets command | deny and explain; stale-base rebase; audit event + no-mutation oracle |
| SF-07 | Package/template composition (owner, importer, workspace assets) | package/template + target + bindings → new identities/provenance graph | preview → dependency preflight → clone/import → private test → publish | compatible versions, permissions, credentials separated | source/version link, new IDs, migration log | partial clone hidden; credentials/chats copied; source mutation | atomic rollback or explicit partial inventory; clone log/hash |
| SF-08 | Cross-app shared context (app A, app B, router, widgets) | typed symbol/date/universe/resource edges; export operation envelope | bind → invoke versioned export → render/update dependent view | exported operation declared and authorized | recipient records source version and parameter values | global mutable parameters; cycle/conflicting writer; app A private API access | reject cycle/stale binding; sender/receiver traces and owner labels |
| SF-09 | Replay/live streams (research app, feed, event bus, operator) | subscription + cursor/replay window → event envelope with event/receive times | authorize → replay → explicit handoff → live → unsubscribe | channel entitlement; replay cursor available | phase, cursor, ordering, gap/dedup and heartbeat visible | replay treated as live; duplicate/out-of-order trade-driving event | reconnect/gap replay and phase remains explicit; event sequence oracle |
| SF-10 | Trading authority (strategy, BMS/SQS/MIS, broker, operator) | complete system + sizing policy + model binding/absence → decision/intent | configure → validate → supervised approval → submit → reconcile | explicit trading scope, market session, risk policy | attributed intent/order/fill; Book/BMS regression preserved | research/backtest authority crosses into live; model silently mandatory; rescaling old trades | flat/stopped handover; reject unauthorized action; broker/audit ledger oracle |
| SF-11 | Recovery/placement (operator, scheduler, worker, backup) | environment, quota, entitlement, checkpoint, backup snapshot | preflight → run → worker loss/unknown → inspect → resume/restore | checkpoint/backup verification available | unfinished vs unknown vs complete distinct; placement profile recorded | global green dashboard; restore “success” without consistency proof | retry/restore on disposable data; compare hashes, events and artifacts |
| SF-12 | Failure/security challenge (malicious/buggy extension, policy, user) | malformed schema, overbroad request, stale resource, secret/cost/trade action | detect → classify → deny/quarantine → explain → recover | conformance/red-team suite enabled | no unauthorized mutation; actionable diagnostic with scope | install causes core edits; sensitive payload leaks; hidden paid compute | quarantine extension/index; revoke token; policy/audit trace is oracle |

## BDD-style scenario outlines

### BDD-01 Capability index is truthful
**Given** an extension has a versioned manifest with one valid resource and one unavailable provider
**When** the manifest is validated and the capability index is rebuilt
**Then** both capabilities appear with owner/version and the unavailable reason, and the prior index remains intact on failure.

### BDD-02 Data preview preserves provenance
**Given** two providers disagree on a symbol and one result is adjusted
**When** the user previews and queries the resource
**Then** provider, adjustment label, units, timezone, coverage, warnings and truncation are explicit; no silent merge occurs.

### BDD-03 Reproducible recipe pins revisions
**Given** a recipe references a dated snapshot and executor version
**When** the provider later revises history and the recipe is rerun
**Then** the original run remains unchanged, the new run is separately linked, and comparison flags changed inputs.

### BDD-04 Jobs expose honest terminal state
**Given** a queued run loses its worker after producing one artifact
**When** the operator inspects or retries it
**Then** status is `unknown`/`failed` with partial-artifact inventory, never `succeeded`; retry policy and event history are visible.

### BDD-05 Fan-out semantics are declared
**Given** a workflow joins a three-item list to a two-item list
**When** the author selects zip, keyed, or Cartesian mode
**Then** cardinality and missing-key behavior are shown before execution, and invalid/over-budget plans are rejected.

### BDD-06 Copilot scopes do not cross
**Given** an app-use session has read-only data tools but no authoring or trading token
**When** the user asks it to edit a manifest or place an order
**Then** the request is denied with required scope, no mutation occurs, and the denial is audited.

### BDD-07 Clone is provenance-safe
**Given** a template contains files, widgets and an agent but also credentials
**When** it is cloned into another workspace
**Then** new identities retain source/version links, credentials are excluded or rebound explicitly, and a failed dependency causes rollback or a precise partial report.

### BDD-08 Shared parameters are typed edges
**Given** app A exports a versioned operation consumed by app B
**When** a date or universe changes
**Then** only declared bindings update, stale/unauthorized bindings are rejected, and source ownership/version remains visible.

### BDD-09 Replay cannot masquerade as live
**Given** a stream request includes a historical cursor
**When** replay completes and live handoff occurs
**Then** events carry phase/provenance, handoff is explicit, duplicates/gaps are detectable, and reconnect does not fabricate continuity.

### BDD-10 Trading requires explicit authority
**Given** a backtest result and an optional MIS/model are available
**When** a user attempts live submission without trading approval
**Then** no order is sent; the system records the blocked intent and keeps research/backtest authority separate from broker authority.

### BDD-11 Restore is evidence-backed
**Given** an operation is interrupted and a backup exists
**When** the operator restores to disposable storage
**Then** state/artifact hashes and lineage are compared, inconsistency is reported, and only verified state can resume.

### BDD-12 Extension failure is contained
**Given** a package declares a duplicate ID, missing dependency, or overbroad scope
**When** install/conformance checks run
**Then** activation is rejected or quarantined, core contracts remain unchanged, and diagnostics identify the exact violation and recovery action.

## High-order trap checklist

- Participant trap: authoring, app-use, broker, worker, and copilot identities are not interchangeable.
- Composition trap: federated Knowledge + Artifact discovery is a concatenated view, not a new store or Library kind.
- Payload trap: every result carries provenance, version, scope, units/timezone, truncation and sensitivity; citations do not become commands.
- Lifecycle trap: draft, queued, running, paused, awaiting approval, unknown, cancelled, expired and succeeded are distinct.
- State trap: stale cache, provider revision, replay phase, partial artifact and migration-in-progress are visible rather than normalized away.
- Execution trap: selected subgraph and declared fan-out only; no accidental whole-board execution or hidden retries.
- Authority trap: manifest text cannot self-grant; research cannot place trades; paid compute/external mutation requires policy approval.
- Market trap: replay is not live; Book/BMS/SQS/MIS arrangement remains regression-protected; handover is stopped/flat and attributed.
- Policy trap: denial/quarantine/revocation are observable outcomes with audit records, not generic errors.
- Impossible exclusions: silent merges, hidden capability loss, credential copying, old-run rewriting, fake green dashboards, unbounded fan-out, and “success” with unknown/partial state.
