# Reference Extract — Pi (earendil-works/pi)

Reference, not a dependency (register §5; supersession L31–72→L3029). Primary sources, all checked 2026-08-28.
Packages @ v0.84.3, published 2026-08-24 (monorepo lockstep). MIT. 5,820 commits, active hourly.

## Q1 — Target mental model
"Aggressively extensible so it doesn't have to dictate your workflow. Features other tools bake in can be built
with extensions/skills/packages. This keeps the core minimal while letting you shape pi to fit how you work"
(coding-agent README §Philosophy). A tiny stateful agent loop + a unified LLM API; everything opinionated is
pushed to userland TypeScript. Recent evolution (Jul 2026) added a **daemon-grade wire trio** (protocol/server/
client) so a remote client can drive sessions the CLI process holds — the exact daemon↔UI split QMX decided (reg #6).

## Q2 — Concrete runtime/API structures

### Package split (github /packages, checked 2026-08-28)
- **pi-ai** (`@earendil-works/pi-ai` 0.84.3) — unified multi-provider LLM API (OpenAI/Anthropic/Google/Bedrock…):
  model discovery, auth resolution, token+cost tracking, context persistence across models. Owns the model layer.
- **pi-agent-core** (`@earendil-works/pi-agent-core` 0.84.3, 6 deps, 296 dependents) — stateful `Agent` + tool
  execution + event streaming, built on pi-ai. Owns the loop + state.
- **pi-coding-agent** (`@earendil-works/pi-coding-agent` 0.84.3) — interactive CLI + the whole extension host,
  sessions, settings, skills. Owns the app + extension API.
- **pi-tui** — terminal UI lib (differential rendering). **pi-telemetry** — vendor-neutral telemetry contracts +
  reference adapter + conformance tests. **pi-evals**.
- **pi-protocol / pi-server / pi-client** — NEW daemon wire trio (added Jul 2026; server was "orchestrator",
  renamed Jul 2026). **pi-session-backend-sqlite-node** — pluggable SQLite session store.

### Agent loop core (pi-agent-core README, checked 2026-08-28)
- `new Agent({ initialState:{systemPrompt, model, thinkingLevel, tools, messages}, streamFn, convertToLlm,
  transformContext, sessionId, getApiKey, toolExecution, beforeToolCall, afterToolCall, shouldStopAfterTurn,
  steeringMode, followUpMode, thinkingBudgets })`.
- **State is held in `agent.state`** (`AgentState`: systemPrompt, model, thinkingLevel, tools[], messages[],
  readonly isStreaming/streamingMessage/pendingToolCalls/errorMessage) — mutable, assignment copies top array.
- **UI attaches by subscribing to the event stream only** — `agent.subscribe((event, signal)=>…)`; no other
  coupling. Events: `agent_start, turn_start, message_start/update/end, tool_execution_start/update/end,
  turn_end, agent_end`. Drive with `agent.prompt(text|msg, images?)`, `agent.continue()`.
- **Tools executed by the loop**: `AgentTool {name,label,description,parameters(TypeBox),executionMode:
  "parallel"|"sequential", execute(toolCallId,params,signal,onUpdate)→{content,details,terminate?}}`. Throw →
  reported to LLM as `isError:true`. `toolExecution:"parallel"` default (preflight sequential, run concurrent).
- **In-loop hooks** (block/mutate, deterministic): `beforeToolCall→{block,reason,terminate?}`;
  `afterToolCall→patch result`; `shouldStopAfterTurn(ctx,signal)→bool` (runtime-owned stop, e.g. compact);
  `transformContext(messages,signal)` (prune/compact/inject); `convertToLlm` (drop UI-only msgs). Steering
  (interrupt while tools run) vs follow-up (queue after stop) queues.
- **Router is injected, not owned**: `streamFn: models.streamSimple.bind(models)`; `streamProxy` for browser→backend.
- Low-level: `agentLoop(prompts, context, config, undefined, streamFn)` / `agentLoopContinue` — async generators;
  `AgentContext{systemPrompt,messages,tools}`, `AgentLoopConfig{model,convertToLlm,toolExecution,before/afterToolCall,shouldStopAfterTurn}`.

### Extension API surface (coding-agent docs/extensions.md, checked 2026-08-28)
- Shape: `export default function(pi: ExtensionAPI){…}` (sync or async factory, awaited before startup). TS modules.
- **register\***: registerTool, registerCommand, registerProvider/unregisterProvider, registerShortcut,
  registerFlag, registerMessageRenderer, registerEntryRenderer, registerMarkdownTransformer.
- **imperative**: on(event,handler), appendEntry(customType,data) [persist non-LLM record], setLabel,
  set/getSessionName, sendMessage/sendUserMessage, get/setActiveTools+getAllTools, setModel, get/setThinkingLevel, exec.
- **~40 events** (lifecycle overview): project_trust → session_start → resources_discover; input;
  **before_agent_start** (inject message / modify systemPrompt); agent_start/end/settled; turn_start/end;
  **context** (modify messages); before_provider_headers / **before_provider_request** (replace payload) /
  after_provider_response; tool_execution_start; **tool_call** (block:{block,reason,terminate}; mutate event.input
  in place); **tool_result** (patch, middleware chain); tool_execution_end; message_start/update/end (replace
  finalized msg); session_before_switch/fork/compact/tree (cancelable); session_shutdown; model_select;
  thinking_level_select; user_bash.
- **ExtensionContext (ctx)**: ctx.ui (dialogs/widgets/status/footer/autocomplete/custom components/editor),
  ctx.sessionManager, ctx.modelRegistry/model/thinkingLevel/scopedModels, ctx.signal, ctx.cwd, ctx.mode, ctx.hasUI,
  ctx.newSession/fork/switchSession/navigateTree/reload/compact/shutdown/waitForIdle, ctx.getContextUsage, ctx.getSystemPrompt.
- "What's possible": custom tools (or replace built-ins), sub-agents & plan mode, custom compaction, permission
  gates & path protection, custom editors/UI, git checkpointing, SSH/sandbox exec, **MCP integration** — all as extensions.

### Daemon/RPC protocol — TWO distinct surfaces (checked 2026-08-28)
1. **coding-agent process modes** (single-process): `-p/--print` one-shot; `--mode json` (event JSON lines);
   `--mode rpc` over stdin/stdout, **strict LF-delimited JSONL** (split on `\n` only). SDK: `createAgentSession
   ({sessionManager, modelRuntime})`, `ModelRuntime.create()`, `SessionManager.inMemory()`.
2. **Remote wire trio** (real daemon contract):
   - **pi-protocol** v1: binary. Frame = **[uint32-BE length][one definite-length CBOR item]**. First client msg =
     `hello {version: PROTOCOL_VERSION}`. Then **correlated request/response envelopes + server event envelopes**.
     Rule: "**Session and server snapshots are authoritative. Progress events are transient UI hints and must not be
     reduced into authoritative state.**" `SessionMetadata` (id+createdAt required; updatedAt/parentSessionId/
     sessionName/cwd optional — cheap, no runtime) vs acquired `SessionSnapshot` (phase, model, thinkingLevel,
     attachment, locking). `encodeClientMessage/encodeServerMessage`, `createServerMessageDecoder`,
     `ProtocolValidationError`. Limits 16MiB/1M elems/64 nest. "**experimental… no compatibility guarantees**";
     "**All transports are untrusted**"; auth completes before protocol bytes.
   - **pi-server**: `PiServer` composes `PiServerListener` transports (Unix=fs perms, WS=validate on HTTP upgrade);
     app supplies `PiServerService {listSessions, listModels, createSession, openSession}` — "**does not provide a
     standalone CLI or coding-agent service. Applications supply the implementation.**" pi-ai↔protocol `toProtocol*` bridge.
   - **pi-client**: `PiClient({transportFactory: ByteTransportFactory})`. `createSession` (exclusive lease),
     `acquireSession({mode:"exclusive"|"shared"})→SessionLease`, `attachSession` (shared). One connection → many
     sessions, correlated by id. `subscribe()`=authoritative snapshots, `onEvent()`=protocol events. No auto-reconnect.
     `PiSessionOwnershipError` (exclusive vs any lease); leases are AsyncDisposable; `PiDisconnected/DetachedError`.

### Session persistence (checked 2026-08-28)
JSONL, **tree structure**: each entry `{id, parentId}` → in-place branching, no new files. Auto-save
`~/.pi/agent/sessions/` by cwd. `/tree /fork /clone --fork`. Compaction lossy but full history stays in JSONL.
Extension records via `appendEntry` (type:"custom", customType, data) — **excluded from LLM context**, restored by
scanning `ctx.sessionManager.getEntries()`.

## Q3 — Failure modes it solved
- Harness lock-in / feature bloat → radical extensibility keeps a small core testable and lets each user reshape it.
- UI/agent coupling → loop emits an event stream; any UI is a subscriber; remote trio lets a detached client attach.
- Attachment vs identity → sessions are server-held; leases (exclusive/shared) mediate; attach ≠ ownership.
- Optimistic-state corruption over a wire → snapshots authoritative, progress events explicitly non-authoritative.
- Lost history under compaction → tree JSONL keeps every branch; compaction is a view, not a delete.
- Provider sprawl → pi-ai unifies auth/models/cost; router injected as `streamFn`.

## Q4 — What QMX should reuse (conceptually)
- **Event-stream-as-only-UI-attachment** + injected router (`streamFn`) — matches reg #6/#51 (router balances, loop owns nothing about routing).
- **Typed block/mutate hooks in the loop** (beforeToolCall→block, afterToolCall→patch, before_agent_start inject,
  context transform, shouldStopAfterTurn) — the deterministic-gate + ReviewPolicy home (reg #29/#30/#31, Constitution 2/9).
- **Deterministic session tree** ({id,parentId} JSONL) — work-state independent of chat (Constitution 6; reg session-replay #39).
- **appendEntry**: durable, non-LLM, renderer-paired session records — a clean seed for the **agent-authored desk ledger** (reg #35), kept out of context.
- **Wire-contract shape**: length-prefixed frames, hello+version, correlated req/resp + server events, authoritative
  snapshots vs transient progress, SessionMetadata(cheap) vs SessionSnapshot(runtime), leases — near-exact fit for reg #6/#7.
- **PiServerService pluggability** — the daemon core is an interface the app fills; runtime impl swappable (RLM vs Dialogue).
- **Philosophy of refusal** as a design discipline: name what the core will NOT decide.

## Q5 — What QMX should reject
- **"No X — build it yourself" minimalism** (No sub-agents / No plan mode / No to-dos / No MCP / No permission system).
  INHERITED FASHION: Pi ships thin *because it serves the general public and cannot presume a workflow*. QMX is
  single-operator with ONE known workflow → it should **bake in** subagents, missions, ReviewPolicy, ledger, the
  quant loops as first-class daemon primitives, not punt them to userland (reg #3, Constitution 1).
- **pi-package marketplace** (npm/git install, "full system access — review before installing", third-party publishers)
  — INHERITED FASHION: no untrusted-publisher problem exists for one operator; drop the store/trust-review machinery.
- **project_trust prompts / trust.json** — multi-tenant safety theatre for a single operator (worker *sandboxing*
  via Docker is still wanted — that's isolation, not publisher trust).
- **Terminal-centric UX**: pi-tui, keyboard shortcuts, differential rendering, `!`/`!!` bash, editor widgets — QMX UI
  is a separate Rust trading terminal over the wire, not Pi's TUI (reg #71).
- **CBOR + "experimental, no compatibility guarantees"** — borrow the *shape*, reject the instability: QMX needs a
  **versioned, migration-disciplined** contract (reg #6). JSON-vs-CBOR is QMX's call, not inherited.
- **Coding built-ins** (read/bash/edit/write/grep/find/ls as the tool set) — that's the Dev desk only, not the general Tool Registry (reg #57).
- **In-process full-trust extensions** as the universal model — fine for daemon-side trusted plugins; QMX workers still need Docker isolation (reg #62).

## Q6 — Contract QMX should own instead
QMX **Agent Runtime** owns (deterministic core): the turn loop + tool dispatch + event emission + steering/follow-up +
runtime-owned stop conditions/budgets (reg #25/#28); `AgentState`; the injected model-stream fn (router external);
the hook dispatch points; session-tree persistence; the durable event stream. It **pushes to extensions**: tools,
provider/router impls, memory providers, MCP adapters, compaction strategy, permission/ReviewPolicy gates, UI
renderers, skills/graphs/loops. Two runtime impls (Dialogue, RLM) behind one loop/state contract (reg #41).

**Smallest daemon-side extension contract** (Pi's philosophy, minus terminal UX): an in-daemon `DaemonExtension(api)`
that may (1) `registerTool`, (2) `on(lifecycleEvent)` — session/agent/turn/tool/provider, (3) block/mutate at typed
points (before_tool→{block,reason}, after_tool→patch, before_agent_start→inject+systemPrompt, context→transform,
shouldStop), (4) `registerProvider` (model/deployment for the router), (5) `appendEntry(deskLedger, customType, data)`,
(6) contribute commands/missions/graphs — **and MUST NOT contribute UI**: UI crosses the versioned wire to the
separate UI extension SDK (reg #8/#68), never in-daemon.

**Daemon wire contract** (own it, versioned): frame=[len][payload]; `Hello{protocolVersion}`; correlated
command/query `Request{id}`/`Response{id}` + `ServerEvent` stream; authoritative `SessionSnapshot` vs
non-authoritative progress; cheap `SessionMetadata{id,createdAt,desk?,mission?,cwd?}` vs acquired runtime snapshot;
exclusive/shared `SessionLease` with **attach ≠ identity**; transport-neutral (Unix local, WS/TLS to the VPS) with
auth before protocol bytes; a `DaemonService{listSessions,listModels,createSession,openSession,…}` pluggable core.

## Open questions Pi cannot settle
- No multi-bot **mailbox / Agent Bus**, no **Mission/Task Graph**, no cross-model **ReviewPolicy** — Pi gives zero precedent; QMX designs these alone (reg #32/#34, open #6).
- No **RLM / programmatic-context** runtime — Pi's loop is dialogue-only; QMX's RLM runtime (reg #41/#48) has no Pi analog.
- No **MemoryProvider** contract — memory in Pi is just JSONL + appendEntry; out of scope for QMX's provider model (reg #43/#46).
- **Daemon language** stays open (reg open #1): Pi is TS-only — evidence TS carries loop+protocol+hooks, but not a ruling.
- Pi's protocol is **single-operator/local** (one Unix socket); "message delivery when the machine is off for days" (open #5) is unaddressed.
- Pi assumes **full-trust in-process** extensions; whether QMX daemon plugins are ever sandboxed is undecided (worker Docker isolation is separate).

## Sources (all checked 2026-08-28)
- https://github.com/earendil-works/pi (README)
- https://github.com/earendil-works/pi/tree/main/packages (package tree)
- https://www.npmjs.com/package/@earendil-works/pi-agent-core (0.84.3)
- https://www.npmjs.com/package/@earendil-works/pi-ai (0.84.3)
- https://www.npmjs.com/package/@earendil-works/pi-coding-agent (0.84.3)
- https://github.com/earendil-works/pi/tree/main/packages/coding-agent (README: sessions, philosophy, RPC, CLI)
- https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/extensions.md (full ExtensionAPI)
- https://github.com/earendil-works/pi/tree/main/packages/protocol (wire protocol)
- https://github.com/earendil-works/pi/tree/main/packages/server (PiServer/PiServerService)
- https://github.com/earendil-works/pi/tree/main/packages/client (PiClient/leases)
