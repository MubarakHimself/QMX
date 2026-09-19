# QMX sessions/workflows research audit

Date: 2026-09-17 (Africa/Nairobi). Read-only audit of planning `b8b4d21` and implementation worktree `integration-inspect` at `8510c03`; no fetches or repository edits. Local citations use the ratified docs in the main checkout unless a worktree path is explicit.

## Executive finding

QMA has a deliberately narrow authoring/runtime split. `qma-core` defines ontology, ports, contribution schemas and refusal vocabularies; `qma-daemon` is the single Python 3.14 asyncio runtime and sole writer; `qma-wire` is the only cross-boundary contract. The strongest safety property is that authoring output is candidate/definition material and cannot directly become runtime or money-path state. The principal residual risks are integration maturity (CT-40..51 are documented as source-inspected, not end-to-end demonstrated), deferred UI contribution architecture, and the concrete always-on continuation host.

## Model and workflow graph

- Ontology is Desk → Role → Quant → Agent → Subagent; Session is a run container and Worker is an addressable execution slot, not an ontology object. Goal is informal intent; Mission is a Quant-owned executable organizational contract; Task is the work unit. `docs/components/qma-core.md:51-55`.
- The daemon owns deterministic Mission compilation, Task Graph state, graph-template compilation, `loop` node iteration, task/agent nodes, scheduler, leases and transitions. LLMs may propose decomposition, but only daemon validation reaches persisted state; parallel workers synchronize through the Task Graph, never chat. `docs/components/qma-daemon.md:23`, `:108-114`.
- There is no separate Mission Template registry in v1 (GAP-0084). Graph Template is authored/versioned/stateless; Task Graph is runtime state. Loop is a node kind with runtime-owned stopping condition, budget and escalation, not an eleven-entry loop registry. `docs/components/qma-daemon.md:112`; `docs/decisions/ADR-0020-qma-agentic-system.md:33,47`.
- Fan-out/join semantics are not exposed as an independent QMA contract in the inspected docs; the safe inference is that parallelism and dependency synchronization belong to daemon-owned Task Graph scheduling. Any richer subflow/port/fanout/join grammar would be a new spine decision, not an implied implementation feature.

## Persistence, provenance and recovery

- JSONL append journal plus SQLite WAL are durable evidence; DuckDB is rebuildable fold-view storage only. One daemon writer and global monotonic `journal_seq` provide total ordering. `docs/components/qma-daemon.md:53-57,78-82`.
- Closed projections include Session/Agent records and Task Graph; independent stores include three ledgers, artifacts, telemetry, staging and admitted provider storage. Context is compiled per invocation, written by nobody and never persisted. `docs/components/qma-daemon.md:57,88-106`.
- Every durable record carries UTC occurred/recorded timestamps; workers do not timestamp evidence. Remote workers use a durable ordered, fsynced outbox; daemon deduplicates producer+id; exhaustion blocks new dispatch rather than discarding evidence. A lost environment yields `unknown_tail`, never a fabricated tail. `docs/components/qma-daemon.md:82-84`.
- Task Ledger is Task-owned for its whole life across Agents, with one `dispatch_lease`; reassignment increments `attempt_no`, defer-resume does not. Completion requires a structured five-field TaskCompleted append, while a refused completion preserves the append. `docs/contracts/ct-51-qma-task-ledger-entry.yaml:14-39,41-67`.

## Capability, provider and authority boundaries

- Seven runtime ports are defined in core: MemoryProvider, ModelDeployment, ExecutionEnvironment, KnowledgeSource, ToolAdapter, ComputeProvider and ContextCompiler. Cardinality and singleton scope keys are explicit; duplicate bindings are startup errors, not last-write-wins. `docs/components/qma-core.md:57-61`.
- Secrets cross as `credential_ref`, never values; the daemon Credential Broker keeps resolved values inside the egress call frame. Model routing is ModelClass → Deployment → Credential Broker. `docs/components/qma-core.md:63-65`; `docs/components/qma-daemon.md:23`.
- Memory candidates are daemon-gated and admitted; Knowledge is read-only, provenance-carrying, with cited bytes copied into artifacts. Context is ephemeral. The verbs are intentionally distinct: memory is admitted, refinement is applied, and only a human promotes a registered artifact outside QMA. `docs/components/qma-daemon.md:23,98,103-106`; `docs/decisions/ADR-0020-qma-agentic-system.md:49`.
- Effective capabilities are computed once at Agent spawn; Subagents cannot widen parent capabilities. The act-level deny-list rejects money-path tools at registration, and placement rejects environments/edges that could reach venue, broker, exchange, trading node or platform-registry controls. `docs/components/qma-core.md:23-25`; `docs/components/qma-daemon.md:23-25`.

## Authoring vs application use / packaging

QMA is three application-layer packages, not a QMF roster package: definitions-only `qma-core`, runtime/sole-writer `qma-daemon`, and contract-only `qma-wire`; all use `qma.*`. UI and an extension SDK are explicitly deferred (GAP-0081), and there is no v1 `ui_view` contribution point. `docs/components/qma-core.md:15-19,27-44,57-65`; `docs/decisions/ADR-0020-qma-agentic-system.md:41-46`.

The plugin contribution surface is scoped/reversible and imports definitions from core, never daemon. No mini-app/desktop UI packaging contract is ratified in the inspected corpus. This is a material isolation boundary: adding UI contributions or a mini-app host would need a new contract/spine decision, not reuse by naming similarity.

QMA reaches QMB only through the CT-47 door and must never `import qmb`; the inspected integration SHA still has `RecordingQmbDoorTransport`, which records rather than spawns and is explicitly not working end-to-end integration. `docs/components/qma-daemon.md:38`; `docs/components/qma-daemon.md:25`; `docs/decisions/ADR-0020-qma-agentic-system.md:87-89`.

## Compute execution

ExecutionEnvironment and ComputeProvider are typed by kind; JobHandle includes `unknown`. The daemon's Compute Router places ComputeRequirements and maps JobHandle state to Task state. Workstation-default deployment uses Docker workers locally; remote workspace/research-node/sandbox workers dial out, never daemon dial-in. No explicit GPU contract was found; GPU use must therefore remain an ExecutionEnvironment/ComputeRequirement extension, not an ambient capability. `docs/components/qma-daemon.md:19,23,37`.

Continuation is architecturally daemon + remote environments + durable outbox, but the always-on host is GAP-0062. QMA has no command line; mutation comes over wire from UI/scripts, while `qmb` remains the platform CLI. `docs/components/qma-daemon.md:19,25`; `docs/decisions/ADR-0020-qma-agentic-system.md:46,50,92`.

## Narrow official current references

- JSON Render’s official repository documents a component catalog with state expressions, built-in `setState`, action parameters and state watchers; this supports treating a render catalog as presentation/action vocabulary only, not as authority. [vercel-labs/json-render README](https://github.com/vercel-labs/json-render/blob/main/README.md) (retrieved 2026-09-17; repository licence/version not asserted here because the visible source did not establish a stable release pin).
- MCP Apps is an official MCP extension. The official docs specify tool-linked `ui://` resources, sandboxed iframe rendering, `ui/initialize`, host context/capability negotiation, `postMessage` JSON-RPC, tool calls, model-context updates, and teardown. [MCP Apps overview](https://apps.extensions.modelcontextprotocol.io/api/documents/overview.html), [official API](https://apps.extensions.modelcontextprotocol.io/api/), [App class](https://apps.extensions.modelcontextprotocol.io/api/classes/app.App.html) (retrieved 2026-09-17). The docs show `@modelcontextprotocol/ext-apps` v1.1.2 in the versioned API path and state the wire is unchanged across ext-apps 1.x/2.x; this is external reference material, not a QMA adoption decision.
- Security inference: MCP Apps’ host-proxied tool calls and sandboxed iframe are compatible with a UI contribution boundary, but do not grant QMA authority. Any QMA UI must still route through qma-wire and daemon principal/capability checks; app-only tools must not be treated as privileged operations.

## Verification and limitations

Commands run (read-only): `Get-Content docs/AGENTS.md`; `git show --stat b8b4d21`; `git show --stat 8510c03`; `rg` over QMA docs/contracts and the `integration-inspect` worktree; official web search/open for JSON Render and MCP Apps. No tests were run and no running app was available, so no Reticle verdict is claimed. The implementation worktree contains QMB/QML and QMA documentation/staged artifacts but no demonstrated QMA daemon end-to-end runtime; contract metadata explicitly says `source-inspected`, not e2e (`docs/contracts/ct-51-qma-task-ledger-entry.yaml:6-10,68`).

