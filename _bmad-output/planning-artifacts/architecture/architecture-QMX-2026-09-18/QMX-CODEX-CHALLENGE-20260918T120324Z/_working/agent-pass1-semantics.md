# Pass I — public/domain semantics (bounded source synthesis)

Scope: `RECON-RETURN.md` and `reference-recon/*` only. This is evidence synthesis, not architecture ratification.

## Semantics QMX must preserve

| Concept | Evidence-backed meaning / non-distortion rule |
|---|---|
| **Capability** | A discoverable, typed ability with inputs, outputs, owner/extension, entitlement/credential requirements, side-effect class, cost/budget, and availability/health. Do not equate a visible declaration or marketing claim with executable access. Unavailable capabilities should be explicit rather than hidden. |
| **Workflow** | A composition of definitions, scoped assets, operations/jobs, events, approvals, and artifacts. Submission, status, retrieval, expiry, cancellation, failure, and partial output are distinct states; a workflow is not merely a UI sequence. |
| **App / node / session / context** | An app is a declared composition of operations/views/layout over workspace-scoped assets. A node/widget is a typed operation/view binding, not necessarily an executor. A session is a bounded execution/interaction context; QMA's execution `Session` is not automatically the product/app session. Authoring copilot context must remain distinct from app-use context and cannot silently gain credentials, trading, paid-compute, or external-action scope. |
| **Model / dataset** | A dataset is a resource or immutable derived artifact with schema, coverage, freshness, provenance, entitlement, live/snapshot status, version/hash, and recipe lineage. A model/strategy definition, exact data binding, run, and resulting artifacts are separate concepts. Preserve feature/label roles, split/embargo/leakage controls, seed, executor/version, and lineage. |
| **Job / stream / event** | A job is an asynchronous operation with stable run ID, state, progress, logs/events, cancellation/retryability, budgets, artifacts, and failure code. A stream has subscription state, channels/symbols, quotas, heartbeats, ordering, deduplication, backpressure, gap/reconnect policy. Events must distinguish event time from receive time and carry provider/source plus replay/live provenance. Replay-to-live requires an explicit transition marker/cursor; stream access is not trading permission. |
| **Provider / broker / account / venue** | A provider supplies/normalizes data or capability under declared coverage, credentials, symbol rules, warnings, and provenance. Broker/exchange action authority is separate from market-data access and strategy evaluation. An account/credential scope and venue/protocol kind must not be conflated; new protocol is not automatically a new account. |
| **Instance / version** | Runtime identity, definition version, extension version, resource content hash, template source/version, and generated registry revision are distinct. Clones receive new identity while retaining source/version provenance. Generated/static indexes need invalidation/rebuild discipline. |

## Invariants and edge cases

- Preview is bounded and distinct from queued bulk export; export artifacts can expire. Do not make preview synchronous bulk work.
- Resource recipes and run outputs must retain exact transforms, time alignment, timezone/calendar, licensing/provenance, and stale/incompatible dependency signals.
- Shared parameters are typed dataflow edges (source/target field, mapping, update mode, validation), not implicit UI coupling. Cycles, missing targets, conflicting writers, stale options, and unauthorized downstream actions need deterministic errors.
- Required failure states include invalid input, missing entitlement/credential, empty data, provider timeout, quota/compute exhaustion, cancellation, partial/truncated output, expiry, stale dependency, and schema/version incompatibility.
- Replay/live reconnect semantics must state whether gaps replay, duplicate, or surface; preserve ordering and dedupe identity.
- Workspace references distinguish live versus snapshot; templates/clones need atomicity or explicit partial/rollback recovery, ownership, permissions, retention, and audit.
- Backtest authority is separate from live-trading authority. Authoring changes require diff/validate/preview/save or publish boundaries; app-use must be capability-scoped.
- Observed UI state proves only visibility, not accuracy, entitlement, computation, reliability, or backend architecture.

## Freshness, uncertainty, and provenance

- `RECON-RETURN` freshness reconciliation is a 2026-09-18 checkpoint. Current inspected implementation was revision `270e992`; audit revision `8510c03` is 32 commits behind and must not support absence claims. Current retained gaps include QMA venv-blocked tests, no whole-system QML→QMB→QMN proof, closed venue kinds, in-memory template catalog, and TaskGraphStore lacking edges/successor walking.
- Reference research ran approximately 2026-09-18 08:30–08:40 UTC, read-only. Evidence classes are `OBSERVED_INTERACTION`, `DOCUMENTED_CAPABILITY`, `VENDOR_CLAIM`, `REPOSITORY_SOURCE`, `QMX_ADAPTATION_PROPOSAL`, and `UNVERIFIED`.
- Strongest provenance: LSE catalogue/API/WebSocket documentation and observed UI; OpenBB official docs/repositories for provider normalization and widget/app declarations; Taskade official docs/repository for workspace assets, agents, automations, and app composition. No OpenBB/Taskade backend, LSE runtime API/WebSocket call, export, backtest, ML run, or trade was executed.
- LSE heatmap/COT 404s are failed navigation, not absence. Conflicting vendor scale counts are unreconciled measures. Marketing claims and screenshots are not production guarantees. Treat all proposed QMX envelopes/contracts as proposals requiring repository audit.
