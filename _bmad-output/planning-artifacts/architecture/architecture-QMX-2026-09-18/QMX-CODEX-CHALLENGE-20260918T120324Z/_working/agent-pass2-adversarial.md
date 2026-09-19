# Pass-II adversarial and edge-case review

Scope: `pass2-candidate`, including `ARCHITECTURE-SPINE.md`, `CONTRACTS.md`, `JOURNEYS.md`, `UI-HOST.md`, `COPILOT-AND-APPS.md`, and `IMPLEMENTATION-SEQUENCE.md`.

The internal adversarial review already resolved the five named identity/authority traps: product-session versus QMA Session, ContributionHit versus fp1, dummy Book, Board versus Mission, and json-render/MCP Apps as authority. Those are recorded below only as overlap, not as new findings. QMF remains one framework; Book/BMS is a default rather than a universal ceiling; data/ML is not a bot; session context is explicit; app-use cannot edit implementation; specialists remain; and PM means Portfolio Manager.

## Adversarial lens

### A-1 — Operation retries have no idempotency contract

- location: `CONTRACTS.md:11-30`, operation descriptor
- trigger_condition: A caller times out after a `mutate-config`, `append-evidence`, `place-run`, or `external-egress` operation may have committed, then retries the same `op_id` and inputs.
- guard_snippet: Add `request_id`/idempotency scope, deduplication retention, and a rule that uncertain completion returns the original `job_handle`/outcome rather than executing a second effect. Require idempotency or explicit non-retryability per effect class.
- potential_consequence: Duplicate runs, evidence, configuration mutations, or external orders can be created while both attempts look valid.

### A-2 — Job cancellation races completion without a winner rule

- location: `CONTRACTS.md:98-112`, job handle
- trigger_condition: `cancel` arrives concurrently with worker completion, or a client retries cancel after the job has crossed `running` to `succeeded`/`unknown`.
- guard_snippet: Define an atomic state-transition matrix (`queued/running -> cancelling -> cancelled` versus completion), a single terminal-state winner, and the returned result when cancel loses the race. Cancellation must never imply rollback of a committed effect.
- potential_consequence: Two readers can observe contradictory terminal states, or a caller can report cancelled while a run/order/evidence write completed.

### A-3 — Task Graph successor dispatch is not idempotent or atomic with state persistence

- location: `ARCHITECTURE-SPINE.md:125-126`; `IMPLEMENTATION-SEQUENCE.md:17`
- trigger_condition: The daemon persists a node as succeeded, crashes before dispatching successors, or dispatches and crashes before recording the dispatch; restart replays the boundary.
- guard_snippet: Persist node transition, dispatch intent, and per-edge dispatch key in one owner-controlled transaction/outbox; use `(mission_id, node_id, attempt, edge_id)` as an idempotency key and reconcile pending intents on restart.
- potential_consequence: Successors are skipped or run twice, producing non-deterministic graph results and duplicate side effects.

### A-4 — Edge mapping does not define cardinality validation or partial-output behavior

- location: `ARCHITECTURE-SPINE.md:113-114`; `CONTRACTS.md:144-146`
- trigger_condition: A `zip`, `keyed-join`, `broadcast`, or `cartesian` edge receives mismatched/empty collections, duplicate keys, or a producer returning `many` where the consumer expects `one`.
- guard_snippet: Require compile-time compatibility plus runtime checks for lengths, key uniqueness, null/empty policy, and overflow; persist a typed refusal with the edge id and mapping inputs before dispatch.
- potential_consequence: Silent truncation, accidental Cartesian explosion, or a consumer receiving an arbitrary element can corrupt downstream artifacts.

### A-5 — Product-session context revision lacks compare-and-swap semantics

- location: `ARCHITECTURE-SPINE.md:128-132`; `CONTRACTS.md:49-64`
- trigger_condition: Two tabs or reconnecting clients issue `select`/grant mutations against the same `context_revision` concurrently.
- guard_snippet: Every mutation must carry `expected_context_revision`; reject stale writes with a typed conflict and return the current snapshot. Define whether grants and selected refs share one revision and make the journal append atomic.
- potential_consequence: Last-writer-wins can silently retarget a copilot or revoke/restore authority based on stale UI state.

### A-6 — Change-request target and validation provenance can drift

- location: `CONTRACTS.md:66-79`; `ARCHITECTURE-SPINE.md:132`
- trigger_condition: A request is opened against an app instance/version and target artifact, then the instance is upgraded, disabled, or the artifact is superseded before authoring applies it.
- guard_snippet: Pin source instance `(package_id, version, instance_id)`, target identities and base revisions in the change request; apply only with an explicit rebase/conflict result and record validation evidence before v2 activation.
- potential_consequence: Authoring silently applies a request to different code/data, invalidating the claim that v1 remained untouched and making review evidence non-reproducible.

### A-7 — Stream replay/live boundary has no gap, duplicate, or ordering rule

- location: `CONTRACTS.md:114-128`; `UI-HOST.md:18-20`
- trigger_condition: A reconnect uses `since_seq` during a producer restart, retention truncation, late event, or phase transition from replay to live.
- guard_snippet: Define monotonic producer epoch plus sequence, retention expiry response (`resync_required`), event-time versus receive-time ordering, duplicate suppression, and the atomic cursor at the replay-to-live cutover.
- potential_consequence: Consumers miss ticks or process duplicates/out-of-order events while believing the stream is continuous.

### A-8 — Pack enable rollback does not specify external/plugin side effects

- location: `ARCHITECTURE-SPINE.md:193-194`; `CONTRACTS.md:130-142`
- trigger_condition: Enable validates some dependencies and publishes contributions, then a later migration/health check fails; partial install is said to roll back but publication and external setup are unspecified.
- guard_snippet: Separate staged bytes from activation; publish roster/contributions only at a commit point, make migrations compensating/idempotent, and define cleanup for processes, files, leases, and credentials on failed enable.
- potential_consequence: A failed install leaves ghost ContributionHits, half-migrated state, or enabled capabilities whose package is not atomically present.

### A-9 — Deployment drain has no bounded timeout/escalation transition

- location: `CONTRACTS.md:148-159`; `ARCHITECTURE-SPINE.md:166-170`
- trigger_condition: Replacement is requested while positions remain, a job never acknowledges drain, or an UNKNOWN command prevents proving flatness.
- guard_snippet: Specify `requested -> draining -> drained|blocked|unknown`, timeout and operator escalation, and the only safe actions while blocked; activation must require a fresh observed state, not a stale `residual_positions` label.
- potential_consequence: Replacement can hang indefinitely or an operator can force activation while old control still owns positions/commands.

### A-10 — Contribution availability can change between discovery, pin, and invoke

- location: `ARCHITECTURE-SPINE.md:90-96, 137-138`; `COPILOT-AND-APPS.md:34`
- trigger_condition: A contribution is discovered and granted, then its package is disabled, revoked, or health changes before invocation; the text says typed unavailability but does not define pin revalidation.
- guard_snippet: Resolve `(qualified_id, package_version, instance_id)` at invocation, re-check enabled/granted/authorized/reachable/healthy states, and return a stable `unavailable` result containing the pin and reason. Never fall back to another version or instance.
- potential_consequence: The same saved workflow invokes a different implementation or fails ambiguously after a package transition.

### A-11 — Job-handle ownership and lease expiry are underspecified

- location: `ARCHITECTURE-SPINE.md:125-126, 175-176`; `CONTRACTS.md:98-112`
- trigger_condition: The client/session that created a job disappears, an environment lease expires, or a remote worker reports success after the daemon lost reachability.
- guard_snippet: Name the durable job owner, lease/heartbeat policy, orphan adoption and expiry behavior, and reconciliation authority for late results; client disposal must detach, not cancel.
- potential_consequence: Jobs become unobservable or are duplicated on resume, and late results can be attached to the wrong mission/session.

## Edge-case lens: unhandled branch/transition conditions

1. `CONTRACTS.md:112`: `timeout` is said not to be silent, but there is no explicit transition/result for timeout versus `unknown`; a timed-out caller cannot know whether retry is safe.
2. `CONTRACTS.md:114-128`: no branch for cursor older than stream retention or for producer epoch changing; `attach/since_seq` can acknowledge a discontinuity as normal replay.
3. `CONTRACTS.md:66-79`: no branch for a change request whose source session is deleted/revoked or whose target fp1 is unavailable; “lands in staging” has no refusal state.
4. `ARCHITECTURE-SPINE.md:128-132`: no stale-revision branch for concurrent context mutation; “bump context_revision” does not say whether stale commands are rejected or merged.
5. `ARCHITECTURE-SPINE.md:125-126`: no restart branch for “state persisted, successor not dispatched” versus “successor dispatched, state not persisted”; both are possible at the stated boundary.
6. `ARCHITECTURE-SPINE.md:113-114`: no unhandled branch for duplicate keyed-join keys, unequal `zip` lengths, or a required input being empty; empty policy is attached to operations but not proven for edge mapping.
7. `ARCHITECTURE-SPINE.md:166-170`: no explicit operator branch for drain timeout, stale position snapshot, or an UNKNOWN command that later resolves after activation was requested.
8. `ARCHITECTURE-SPINE.md:193-194`: no branch for disable/uninstall while a pinned running job still references the package; “running work stays pinned” lacks retention/garbage-collection and health semantics.
9. `UI-HOST.md:18-20`: no branch for a snapshot older than the producer’s event log or for event sequence gaps; snapshots are called authoritative without a resync protocol.
10. `CONTRACTS.md:41-47`: no branch for a ContributionHit whose package version is installed but not enabled, or enabled but unauthorized/unreachable; discovery and invocation states are conflated in the representative payload.
11. `CONTRACTS.md:98-112`: no branch for cancel after terminal success/failure or repeated cancel; idempotent terminal responses are not defined.
12. `CONTRACTS.md:148-159`: no branch for `from_composition_fp == to_composition_fp`, duplicate activation requests, or a second writer attempting activation during handover.

## Overlap accounting

The findings in the prior internal `reviews/review-adversarial.md` were checked rather than repeated. Its C-1 through C-5 are considered resolved in the candidate: the spine now explicitly separates product sessions from QMA Sessions, gives ContributionHit a versioned tuple identity, rejects dummy Books, makes Board layout client-only, and declares JSON Render/MCP Apps presentation-only. A-5, A-10, and edge items 2/4/10 are adjacent residual timing/state-machine gaps, not restatements of those identity corrections.
