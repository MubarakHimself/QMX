---
id: SCN-0013
title: A Quant Reachable Through Models Over the Wire
type: scenario
status: ratified
component: COMP-QMA-DAEMON
depends_on: [COMP-QMA-CORE, COMP-QMA-WIRE, COMP-QMA-DAEMON, COMP-QMF-CORE]
decisions: [DEC-0304, DEC-0306, DEC-0311, DEC-0313, DEC-0314, DEC-0344, DEC-0309, DEC-0308, DEC-0305, DEC-0323, DEC-0333, DEC-0341, DEC-0345, DEC-0300]
sources: [DEC-0304, DEC-0314, DEC-0344, DEC-0309, DEC-0308, DEC-0323, DEC-0333, _bmad-output/planning-artifacts/architecture/architecture-QMA-2026-08-28/ARCHITECTURE-SPINE.md]
generated: '2026-08-29'
verified: '2026-08-29'
stale_after: 30d
---

# SCN-0013: A Quant Reachable Through Models Over the Wire

This scenario pins the QMA first milestone end to end: an operator-principal client completes the `initialize` handshake over loopback, mints a Desk and a Quant by wire command, opens a Mission carrying one Task, and the daemon runs that Task — the deterministic scheduler grants the `dispatch_lease` and an `environment_lease`, a Session opens on a Docker worker, the harness picks a `ModelClass` and the model proxy routes it to the OpenCodex Deployment over the daemon-host loopback bind, every daemon-owned primitive passes its `before_*` hook, the Agent writes a structured Task Ledger append the daemon persists, and the durable event stream carries `noun.verb` events the client replays by `wire.attach`. Three failure branches — `NoEligibleReviewer` at the completion gate, a `before_tool` hook timeout resolving to `deny`, and an evidence append arriving with no `correlation_id` — are pinned alongside. A Quant reachable through models over the wire is the first milestone; the UI is Deferred and its extension SDK is Deferred, while the wire contract and the variables registry bind now (DEC-0333, GAP-0081). No trading act occurs anywhere in this walk. [DEC-0304] [DEC-0314]

## Given

The daemon runs on the operator's workstation and binds loopback by default; a `qma-wire` client connects over that loopback bind (AD-5). The client completes the MCP-style `initialize` handshake, negotiating a semver `protocolVersion` (additive-only within a major, deprecations living `registry:wire.deprecation_minors`) and receiving its `producer_id` — the stable minting identity, unchanged across reconnects and the first half of the idempotency pair. Every client authenticates with a credential the Credential Broker resolved before protocol bytes, and this connection carries the `operator` principal class; a `machine` principal could open the same wire but could answer no human gate (DEC-0304, DEC-0323).

The definition store holds a Deployment registered under `ModelClass` `WORKHORSE_GENERAL` whose implementation is a local **OpenCodex** proxy sitting behind the Deployment contract, not behind the Credential Broker. It carries `auth_mode: none`, so no QMA-resolved secret value crosses into the proxy's process, and it binds loopback (`127.0.0.1`) on the daemon's host, verified at registration; an unauthenticated loopback proxy is permitted only by `registry:proxy.allow_unauthenticated_loopback` (default `true`, `ui-editable`, a surfaced assumption overturnable in one line). A second Deployment under `REASONING_HIGH` carries a distinct operator-assigned `model_family` so the completion gate's ReviewPolicy has a comparison to make (DEC-0344, DEC-0314).

The five desks are bootstrapped with the fixed `desk_slug` values `research`, `trading`, `dev`, `analysis` and `pm`; this walk uses the Research desk. The interim lead-flag rule holds: a second lead flag on a desk is a hard startup error and an undeliverable `Envelope` resolves to `dead_letter` until the operator rules the catch-all (DEC-0306, GAP-0071). The daemon is the sole writer of the journal, the SQLite store and the artifact store, and `journal_seq` is the single total order in the system (DEC-0305).

## When

The operator-principal client issues two operator-gated commands (DEC-0323):

```
desk.create   research
quant.create  research/<quant_slug>
```

`desk.create` and `quant.create` mint the `ActorId` `quant:research/<quant_slug>`, each slug lower-case and 2 to 32 characters; the daemon refuses with `SlugUnavailable` any `quant_slug` that case-folds onto a current or retired slug, a Role name or a reserved desk prefix token (DEC-0306). The client then opens a **Mission** owned by that Quant carrying one Task. The deterministic Mission Compiler — daemon code, never an LLM — turns the Goal into a Mission record and its initial Task Graph; the desk is derived from the Quant record and never separately stored (DEC-0311).

## Then

**(1) The scheduler grants the leases and a Session opens.** The deterministic scheduler and dispatcher grant the Task its single `dispatch_lease` (append rights to its Task Ledger, AD-9) and an `environment_lease` on a Docker-per-worker `ExecutionEnvironment` whose required `network` field is `none` or `allowlist` and whose venue-reaching hosts are deny-listed by code (AD-17, AD-28). A Session opens as the run container; its durable record carries the execution-model axis (`dialogue` here) and the autonomy axis only, while attachment stays client state and is never persisted, which is what makes closing the client harmless (DEC-0313). The `scope_path` is built in the fixed order desk, quant, mission, task, session, agent, subagent — Session between Task and Agent because a Task outlives the Session that runs it; every existing ancestor is present, and this walk spawns no Subagent (DEC-0304).

**(2) The harness picks a `ModelClass` and the proxy routes it to OpenCodex over loopback.** The Agent needs a model; the harness picks the class and an agent never names a vendor. The deterministic chain ModelClass to Deployment to Credential Broker resolves in two stages that never cross a class boundary: `WORKHORSE_GENERAL` selects the candidate pool, then the request's `needs` flags and `min_context_tokens` are the sole eligibility filter; an empty filtered pool would return `NoEligibleDeployment` naming the class and the unmet constraint. The eligible pool resolves to the OpenCodex Deployment and the router load-balances under its routing policy. Because the Deployment is a local proxy with `auth_mode: none`, QMA passes it no credential and the call reaches the loopback bind; the proxy's own provider credentials stay its own custody outside QMA's namespace, and QMA registers each proxy target as one logical Deployment and records the true deployment honestly on the routing-decision telemetry (DEC-0314, DEC-0344).

**(3) Every daemon-owned primitive passes its `before_*` hook.** Hooks are the single enforcement and control surface. A tool call passes `before_tool`; a subagent spawn passes `before_subagent_spawn`; each write into a daemon-owned store passes its gate without exception. A `HookResult` is one tagged union, decisions resolve most-restrictive-wins under the total precedence `block_stop` over `deny` over `defer` over `ask` over `allow` over `observe`, and `injected_context` from a hook reaches the Context Compiler and never the ledger. On a `before_tool` event a hook that returns nothing resolves to `allow` (DEC-0309).

**(4) The Agent writes a structured Task Ledger append the daemon persists.** A task-completion transition requires a structured ledger append — what was done, what changed, evidence and artifact refs, unresolved issues and the next recommendation — through `before_task_complete`, which runs a deterministic verifier script rather than an LLM judging itself, and ReviewPolicy enforces `author_family` not equal to `reviewer_family` against the optional `model_family` field (satisfied here by the two distinct families). The entry is written through `before_ledger_append` by the Agent holding the Task's `dispatch_lease`, carries `attempt_no`, `authored_by` (an agent ref plus the owning Quant's `ActorId`) and the model deployment used, and is persisted by the daemon so it survives the worker; the append emits a `ledger.appended` journal announcement carrying the record's `fp1`, keeping ordering and replay journal-authoritative (DEC-0308, DEC-0305).

**(5) The durable event stream carries the run and the client replays it.** Commands are acked immediately with side effects settling asynchronously, queries read durable state, and a durable event stream carries `noun.verb` events, each carrying its full `scope_path` and a per-scope `seq` — the projection index of the scope named last, never `journal_seq`, which is opaque to clients. The client calls `wire.attach(scope, since_seq)` to follow the run and `wire.attach(since_seq=0)` for a read-only replay from the start; a cursor is valid only for its own scope and a cross-scope cursor is refused with `CursorScopeMismatch`. Closing the client stops no agent and an overnight agent need not know a client exists (DEC-0304). The three closed verbs stay distinct throughout: this walk admits no memory candidate and applies no RefinementProposal, and it promotes nothing — promotion is a human act outside QMA (DEC-0345).

## Failure branches

**Branch A — no reviewer qualifies (`NoEligibleReviewer`).** The completion gate `before_task_complete` runs ReviewPolicy, which compares `author_family` against `reviewer_family`. If every registered Deployment's `model_family` is unassigned, or none differs from the author's family, ReviewPolicy qualifies no deployment and the daemon returns the typed refusal `NoEligibleReviewer`; the completion transition is refused and the Task does not reach a terminal state. The structured ledger entry the transition required is still written and never discarded, because `before_ledger_append` is a validating gate and not a blocking control (L39). A plugin-contributed `model_deployment` registers through the AD-1 contribution surface with no `model_family` and stays routable but ineligible for the comparison until an operator command assigns one (DEC-0300, DEC-0309, DEC-0314).

**Branch B — a `before_tool` hook times out (`deny`).** A `before_tool` hook that exceeds `registry:hook.timeout_before` resolves to `deny` with reason `hook_timeout` plus a telemetry record — the fail-closed default for a `before_*` gate — and the tool call is refused. This carve-out does not reach evidence: a `before_ledger_append` timeout resolves instead to `allow` with the entry recorded and annotated `hook_timeout`, an `agent_stop` timeout resolves to `observe`, and any `after_*` timeout resolves to `observe`, so no timeout ever discards a well-formed evidence append (DEC-0309).

**Branch C — an evidence append arrives with no `correlation_id` (`correlation_missing`).** `correlation_id` has exactly three minting origins (an originating operator command, a scheduled trigger, a daemon-internal lifecycle act) and is copied verbatim onto every downstream command, event, `JobHandle`, ledger append, memory candidate and telemetry span; a record without one is refused at the gate — except an evidence append, which the daemon records under a daemon-minted lifecycle id annotated `correlation_missing`, because L39 forbids a control blocking the recording of evidence. Idempotency holds throughout: every wire command is idempotent on the pair `producer_id` plus `id`, and the daemon keeps a dedup cursor whose window is `registry:wire.dedup_window` (DEC-0304, DEC-0305).

## Worked numbers

This scenario pins a control-and-identity flow, not an arithmetic computation, so there is no fixture number to freeze — and none may be invented. The load-bearing chain is an identity-and-authority chain:

- **`producer_id` plus `id` = the idempotency pair**, assigned at `initialize` and minted per message, so a replayed command dedups against the daemon's cursor rather than acting twice (DEC-0304);
- **one `correlation_id`, copied verbatim** from its origin onto every downstream record, never regenerated or truncated, with the single `correlation_missing` carve-out for an evidence append (DEC-0304, DEC-0305);
- **one `dispatch_lease` per Task** fixes who may append to its Task Ledger, and the append is persisted by the daemon and announced by `journal_seq`, the single total order (DEC-0308, DEC-0305);
- the **operator principal class** is the sole authority that can answer a human gate; a `machine` principal — worker, routine, scheduler or deployed Quant — can answer none (DEC-0323).

The only registry-referenced values in the walk are the wire and proxy configurables — `registry:wire.deprecation_minors`, `registry:wire.dedup_window`, `registry:proxy.allow_unauthenticated_loopback` and the per-phase hook timeouts `registry:hook.timeout_before`, `registry:hook.timeout_after` and the phase-less-control `registry:hook.timeout_control` — and the `ModelClass` tokens `WORKHORSE_GENERAL` and `REASONING_HIGH`, which are closed vocabulary, not numbers. All values are referenced, never restated, so a change to any of them leaves this walk intact. The honest defaults this run reports are that it opens no writable trading surface, mints no money-path value and promotes nothing — the barrier SCN-0014 pins is never exercised here because no tool or environment in this walk reaches toward the market (DEC-0333, DEC-0341).
