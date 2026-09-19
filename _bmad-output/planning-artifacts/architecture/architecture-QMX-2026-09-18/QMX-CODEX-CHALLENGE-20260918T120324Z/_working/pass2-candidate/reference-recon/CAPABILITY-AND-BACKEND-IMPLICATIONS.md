# Capability and backend implications

This document records public capability relationships, not inferred donor architecture. “QMX implication” means a contract worth evaluating during a later repository audit.

## 1. Resource and operation model

| Relationship | Evidence | Public capability shape | QMX implication to investigate |
|---|---|---|---|
| Catalogue → metadata → preview → export | LSE catalogue/builder/API; OpenBB provider coverage | Discover a resource, inspect schema/coverage, preview a bounded slice, then request a larger artifact | A typed `DataResource` plus separate `PreviewQuery` and `ExportJob`; do not make a synchronous preview endpoint carry bulk workloads |
| Provider → shared query model → normalized result | OpenBB provider docs and architecture | Provider chosen explicitly or by preference; shared query fields; provider extras; transform query/extract/normalize | Extension-owned providers with declared credentials, coverage, symbol rules, normalized schema, source warnings, and provenance |
| Dataset recipe → derived table/artifact | LSE dataset builder | Source/window/resolution plus transforms/features/filters/output columns | Versioned recipe input and immutable run output; include transform versions, time alignment, leakage-sensitive fields, and lineage |
| App declaration → operations/views/layout | OpenBB `widgets.json`/`apps.json`; Taskade app kits | Capability declarations bind endpoints to views and compose them into layouts or kits | Keep operation implementation, capability declaration, and user layout/state separate; allow an extension to add an app without core edits |
| Workspace → projects/assets/agents/flows/apps | Taskade Workspace DNA and MCP taxonomy | Apps operate over workspace-scoped structured data, media, agents, and automations | Explicit scope graph, owner, permissions, live-versus-snapshot semantics, and versioned references |

## 2. Proposed canonical resource envelope

A later QMX design exercise should test whether one envelope can describe market series, event/reference tables, files, derived datasets, project records, model artifacts, and reports:

```text
resource_id
kind                 # series, table, event_feed, file, recipe, model, report, project
provider/extension
schema + semantic roles
coverage             # symbols/series, fields, resolution, date range, geography
access                # preview/query/export/stream capabilities
entitlement + quota
provenance + licensing
freshness + updated_at
live_or_snapshot
version/content_hash
owner/scope/permissions
```

This is a `QMX_ADAPTATION_PROPOSAL`; donors do not establish the correct QMX storage or type system.

## 3. Long-running operations and artifacts

LSE’s bulk export docs make an important boundary explicit: submission, status, artifact retrieval, expiry, and failure are separate. ML training, optimisation, backtests, large transforms, and report builds need the same general shape even if their executors differ.

Candidate operation contract:

```text
operation_definition -> run_request -> job_handle
job_handle: run_id, state, created_at, progress, owner, budget, cancelability
state: queued | running | awaiting_approval | succeeded | failed | cancelled | expired
events/logs: timestamp, step, severity, message, structured payload
artifacts: type, schema, uri/ref, checksum, expiry, provenance
failure: stable code, human message, retryability, partial outputs
```

Required failure journeys include invalid input, missing entitlement/credential, empty data, quota or compute budget exhausted, provider timeout, partial/truncated output, cancellation, artifact expiry, stale dependency, and incompatible schema/version. The Taskade public material establishes workflow shape but leaves durable run IDs, idempotency, retry, and per-step results unverified; QMX should make these contracts explicit if workflows can mutate or consume paid resources.

## 4. Historical replay and live streams

LSE documents one connection transitioning from replay to live, with a replay marker and `replay_complete`. That suggests the following QMX concerns:

- Event time and receive time must be distinct.
- Every event needs source/provider and replay/live provenance.
- Subscription state needs requested symbols/channels, acknowledged state, quotas, and error detail.
- A transition boundary or cursor must be explicit; reconnect must define whether gaps are replayed, duplicated, or surfaced.
- Backpressure, heartbeat, ordering, deduplication, and gap detection are contract questions, not UI details.
- A stream subscription is not a trading permission. Market-data access, strategy evaluation, and broker/exchange action must remain separate capabilities.

## 5. Declarative apps, widgets and shared parameters

OpenBB’s public schemas provide concrete evidence for a declaration layer:

```text
widget/app id + version
operation endpoint/tool/job kind
typed parameters and option sources
typed output and supported views
layout/grid hints and initial state
refresh/staleness/raw/export policies
capability/tool binding
shared-parameter bindings
permission/entitlement requirements
```

Shared parameters should be represented as typed dataflow edges rather than implicit UI coupling. The edge needs source field, target parameter, optional displayed-versus-identity field mapping, update mode, validation, and source-refetch behavior. Cycles, missing targets, conflicting writers, stale options, and unauthorized downstream operations need deterministic error states.

OpenBB’s HTML/iframe extension points also imply a trust boundary. QMX should investigate sandboxing, content security policy, origin/auth handoff, allowed bridge messages, and capability-scoped host APIs before supporting arbitrary embedded code.

## 6. Capability discovery and extension ownership

Across OpenBB providers, Taskade MCP tools/templates, and LSE catalogues, discovery is part of the product contract. A QMX capability index could be generated from installed extensions and report:

- resource kinds and provider coverage;
- commands/operations with typed inputs and outputs;
- streaming, job, export and artifact support;
- widgets/apps/templates/recipes supplied;
- required credentials, scopes, plan/entitlement and costs;
- owning extension and version;
- health/availability and rebuild/migration requirements.

The index should describe unavailable states rather than hiding capabilities or implying access. OpenBB’s documented rebuild step after extension changes is evidence that generated/static registries need version and invalidation discipline.

## 7. Workspace assets, templates and knowledge links

Taskade evidence supports treating structured projects, files/media, templates, agent knowledge, and apps as related but distinct assets. For QMX, investigate:

- live reference versus snapshot attachment;
- immutable version/content hash for reproducibility;
- schema/custom-field evolution;
- template clone provenance, parameter substitution and upgrade path;
- ownership, sharing, deletion and retention;
- whether an agent reads, proposes, or may mutate an asset;
- audit events for every externally visible or irreversible change.

A copied template should receive a new identity and retain its source/version link. Import or clone failures should be atomic or clearly report partial objects and rollback instructions.

## 8. Experiment, backtest and model boundaries

The observed LSE backtester and ML Studio show configuration breadth, but they do not prove a unified execution model. QMX should preserve at least four separate concepts:

1. **Definition:** strategy/model/recipe source and parameters.
2. **Data binding:** exact resource snapshot or reproducible provider query, timezone/calendar, costs and transforms.
3. **Run:** immutable inputs, executor version, seed, budget, status, logs and metrics.
4. **Artifacts:** trades, equity/diagnostics, predictions, model, plots/reports and comparison links.

Backtest authority must be separate from live-trading authority. ML feature engineering needs explicit feature/label roles, split policy, embargo/leakage controls, fit scope, metrics, seed and model lineage. Donor marketing does not establish adequate controls.

## 9. Copilot and agent scope

Taskade’s authoring/editing and app-use surfaces reinforce the QMX context distinction:

- **Authoring copilot:** may draft definitions, schemas, layouts, flows and code; changes should be diffed, validated, previewed and explicitly saved/published.
- **App-use copilot:** may query or operate only capabilities granted to that app/session; it should not silently acquire authoring, credential, external-action, paid-compute, or trading scopes.

Tool declarations need side-effect class, required scope, sensitive inputs, cost/budget, idempotency, approval policy and audit fields. Sending, publishing, external mutation, paid compute, model training and trading should expose action-time confirmation/approval controls appropriate to the risk.

## 10. Loading, empty, error and permission states

Evidence included real loading, empty and 404 states but not many runtime failures. QMX app contracts should make these first class:

- not configured / credential required / permission denied / entitlement required;
- loading / queued / running / paused / awaiting approval;
- empty because no matching data versus empty because source is unavailable;
- validation error with field-level detail;
- provider throttled/quota exhausted;
- partial data or stale cache with provenance warning;
- job failed/cancelled/expired and artifact unavailable;
- stream reconnecting/gap detected/replay phase/live phase;
- template/app version incompatible;
- external side effect rejected or rolled back.

## 11. Owners to map in the QMX repository audit

No QMX files were inspected or modified in this assignment, so these are owner categories, not asserted modules:

- QMF extension registry and capability discovery;
- QML authoring definitions, validation and preview;
- QMB datasets, experiments, backtests, ML runs and artifacts;
- QMA agent/tool registry, knowledge and approvals;
- QMN market-data streams, broker/trading authority and operations;
- workspace/project/file persistence and provenance;
- app shell/layout/state and shared-parameter routing;
- job orchestration, event/log store and budget/quota enforcement;
- auth/secrets/entitlements and audit trail.

The next step is an independent repository audit that maps or rejects these proposed boundaries based on actual QMX ownership.
