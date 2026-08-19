# Study: DeepSeek Harness (DSH) Docs — Plugins, Services, Events, Effects, Loader

Source: https://deepseek-harness.github.io/deepseek-harness/ (bilingual site; English `/en/` mirror used directly — no translation needed). Scope: extensibility mechanics for the Cordis-based plugin kernel underlying DSH, as a comparison point for the QMA/Cordis-class harness kernel.

---

## 1. Core mental model (from `reference/cordis-primer`)

Cordis is the **vendored plugin framework** underneath DSH (not written by the DSH team; pinned + synced from an upstream `vendor/cordis`). Five ideas:

1. **A plugin is an object implementing `Service`** — either a function with optional `inject`/`apply(ctx)`, or a `Service` subclass whose lifecycle Cordis mounts into the current context.
2. **A context is a repository of services.** A service claims a stable `ctx.<key>` (e.g. `ctx.tools`, `ctx.llm`, `ctx.sessions`). Other plugins find services by key, never by importing a concrete implementation.
3. **Declare service dependency via `inject`.** A plugin naming required services waits until those services exist — load order is expressed as dependency requirements, not manual boot sequencing.
4. **Typed events for communication.** Services declare event names via TypeScript declaration merging, dispatched as `emit` / `waterfall` / `parallel` / `serial` depending on whether listeners observe, wrap, fan out, or run in order.
5. **Registrations are reversible effects.** Prompt sections, tool schemas, adapters, providers, listeners are installed through `ctx.effect()` or `ctx.on()` so reload/teardown unwind them predictably.

### Dispatch modes (canonical table)

| Mode | Awaited? | Dispatch Order | Has Return Value? |
|---|---|---|---|
| `emit` | No | registration order | No |
| `waterfall` | No | registration order (around-middleware) | Yes |
| `parallel` | Yes | all listeners concurrently | No |
| `serial` | Yes | registration order | Yes |

- Dispatch mode is part of an event's **public contract**. New harness events document it with an `@mode` JSDoc tag so the generated catalog can check declarations against dispatch sites.
- **Waterfall semantics**: around-middleware. Listener signature `(...args, next)`. Call `next()` to delegate the (possibly wrapped) result downstream; return without calling `next()` to short-circuit. Cooperative listeners mutate a shared request/decision object then delegate; a listener may also replace the result outright. `prepend: true` runs a listener before ordinary registrations. For single-decision events, short-circuiting IS the design — a policy listener returns without `next()` when it owns the decision.
- Cordis core additionally exposes `bail` (first non-null/false/undefined result wins, listeners run in order, sync) — distinct from `waterfall`; DSH's own event catalog uses mostly emit/waterfall/parallel/serial, `bail` is documented in the generic Cordis tutorial page (`develop/framework/events`) as a 5th primitive alongside the four above.

### Loader configuration

- `@deepseek-ai/cordis-plugin-include` parses `!!js` into expression nodes.
- The Loader interpolates an entry's `config` (after declared injections activate, evaluated against that plugin's own context — `ctx.serviceName` reachable) and its `disabled` field (evaluated at *every* mount decision, against the loader's context).
- `Include` preserves nested row expressions until the target activates.
- All other entry metadata (id, name, etc.) stays literal — not interpolated.
- **Overlays** are the recommended mechanism when the deployment environment should select which plugins load.

### Practical rules (canonical, stated verbatim in the primer)

- Encapsulate behavior into plugins: a tool-pipeline event belongs to `ctx.tools`, model streaming belongs to `ctx.llm`, live agent coordination belongs to `ctx.agents`.
- Prefer **events** for interception/policy; prefer **service methods** for direct capability calls.
- Every registration should have a disposer — either returned from `ctx.effect()`, or via a Cordis helper that provides one automatically.
- If teardown order matters, keep the related registrations inside **one** `ctx.effect()` so disposal unwinds in the intended sequence (Cordis does not guarantee serial disposer completion across separate effects — see §2).

---

## 2. Plugin lifecycle (`develop/framework`)

**Fiber state machine** (every loaded plugin owns a Fiber scope):

```
PENDING → LOADING → ACTIVE
                 ↘ FAILED
ACTIVE → UNLOADING → DISPOSED
```

| State | Meaning |
|---|---|
| PENDING | declared, required deps not ready |
| LOADING | deps ready, `apply` running |
| ACTIVE | plugin running |
| FAILED | `apply` threw |
| UNLOADING | unloading, disposing resources |
| DISPOSED | fully unloaded |

- `inject` makes a plugin wait for every required service before loading. If a required service later disappears (e.g. provider swap), the plugin **auto-unloads** (ACTIVE→DISPOSED) and reloads when the service returns.
- **Automatic cleanup**: everything registered through `ctx` is undone on unload — `ctx.on(event, handler)`, `ctx.tools.register(tool)`, `ctx.llm.registerAdapter(names, adapter)`, `ctx.effect(() => cleanup)`.
- Disposer invocation *starts* in reverse registration order on unload, but **multiple async disposers run concurrently with no serial completion guarantee**. Order-dependent cleanup must live inside one disposer from a single `ctx.effect()`, awaited serially there.
- `ctx.plugin()` creates a **child Fiber** — inherits parent context, independent lifecycle, unloads with parent.
- Manual disposal: `const fiber = ctx.plugin(myPlugin); await fiber.dispose()` — guarantees (1) all owned registrations removed, (2) child plugins recursively unloaded, (3) promise resolves after all async cleanup finishes.
- **HMR** (`@deepseek-ai/cordis-plugin-hmr`): editing a plugin source file → unload old (cleanup) → load new code → run new `apply`. Because registrations self-clean, HMR never retains stale registrations.

---

## 3. Services (`develop/framework/service`)

- A service = a capability one plugin exposes to others. `tools`, `llm`, `agents` are services, each a named capability mounted on `ctx` (`ctx.tools`, `ctx.llm`, `ctx.agents`).
- **Consume**: `export const inject = ['tools']` — service guaranteed ready when `apply` runs; otherwise plugin waits.
- **Provide** by extending `Service`:
  ```ts
  export default class MetricsService extends Service {
    static inject = ['llm']  // services can depend on other services
    constructor(ctx: Context) { super(ctx, 'metrics') }
    record(event: string, value: number) { /* ... */ }
  }
  ```
  Then `declare module '@deepseek-ai/cordis' { interface Context { metrics: MetricsService } }` for typing.
- **Required vs optional deps**: `inject` = required (plugin never loads without it); optional = omit `inject`, use `ctx.get('metrics')` at the call site (returns `undefined` if absent).
- **Disappearing service** → dependents auto-dispose, reload when it returns.
- **Service isolation**: `cordis.yml` groups (`group: true`) with an `isolate:` map (e.g. `isolate: { shell: true }`) give separate plugin groups their own instance of an otherwise-shared service (e.g. two Bash configs with different timeouts coexisting).
- Built-in service names/methods/source locations are **generated** into each service's subsystem page from source — not maintained as a second static list.

---

## 4. Events (`develop/framework/events`)

- `ctx.on('event-name', handler)` to listen; `ctx.emit('event-name', payload)` to dispatch (emit mode).
- **emit**: every listener runs sync, return values ignored.
- **bail**: listeners run in order; first result other than `null`/`false`/`undefined` becomes final result and stops the chain — `ctx.bail(...)`.
- **serial**: listeners run in registration order, async awaited; first non-null/false/undefined result stops execution — `await ctx.serial(...)`.
- **waterfall**: each listener may wrap the downstream result; **must call `next()`** or the pipeline short-circuits by design (documented as intentional, enabling interception/gateway behavior) — `await ctx.waterfall('name', input, async () => input)`.
- **Typed events** via declaration merging:
  ```ts
  declare module '@deepseek-ai/cordis' {
    interface Events {
      'my-plugin/ready': (payload: { id: string }) => void
      'my-plugin/check': (input: string) => boolean | undefined
      'my-plugin/transform': (input: string, next: () => Promise<string>) => Promise<string>
    }
  }
  ```
- **Naming convention**: `namespace/action`, e.g. `agent/step`, `agent/request`, `agent/request-error`, `tools/result`, `session/event`.
- **Important distinction**: `turn/*`, `step/*`, `tool/call`, `tool/result`, `compaction/*` are **durable session-event types** (payload rows in the append-only session log), NOT same-named Cordis events. To observe them live you listen to the single Cordis event `session/event` and inspect `event.type` — the session log and the Cordis event bus are two different buses that happen to share vocabulary.
- Listeners registered via `ctx.on()` are effects — auto-removed on plugin unload.

---

## 5. Three-role capability design (`develop/practice`) — the seam pattern

When a capability needs replaceable providers, DSH splits it into three roles, each optionally its own package:

- **Service Definition** — declares the Cordis service + request/result types (e.g. `dsh-shell`).
- **Service Provider** — implements it (e.g. `dsh-bash-local`, executes locally).
- **Consumer** — exposes the capability to the model/user (e.g. `dsh-tool-bash`, a model-callable tool).

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│  dsh-shell   │────▶│  dsh-bash-local  │     │ dsh-tool-bash│
│(definition) │     │    (provider)     │     │(consumer/tool)│
└─────────────┘     └──────────────────┘     └──────────────┘
       ▲                                            │
       └────────────────────────────────────────────┘
                    inject: ['shell']
```

- The **complete capability is the seam** — no individual role is a seam by itself.
- Benefits: swap providers via `cordis.yml` row edit only; Definition/Provider/Consumer evolve independently; Provider and Consumer **never depend on each other**, only on the Definition.
- Design points: don't split preemptively (a simple tool doesn't need 3 packages); the Service Definition owns Request/Result types; prefer an explicit `resolve(request): Spec` step over buried `?? default` fallbacks.

---

## 6. Service inventory — `ctx.<key>` capability seams and core services

From `reference/capability-seams` (generated table: role = `core` | `seam` | `bundle`; owner package; known implementations; direct consumers). Abbreviated — role and one-line purpose per key:

| ctx key | role | owner pkg | purpose |
|---|---|---|---|
| `ctx.attachments` | seam | attachment | image identity/metadata; host commits before session events, adapters resolve refs into provider-native content |
| `ctx.llm` | seam | llm | provider-neutral model streaming; adapters register (`llm-deepseek`, `llm-pi-ai`, `llm-replay`); consumed by `agent-loop`, `compaction-basic` |
| `ctx.tokenMeter` | core | token-meter | isolated per-session replay folds; immutable revisioned measurements |
| `ctx.toolResultPruner` | core | compaction-tool-result-pruner | rewrites oversized tool results via replayable surface replacement pre-summary |
| `ctx.sessions` | core | session | owns append-only `Session` instances, emits durable session event feed |
| `ctx.invariants` | core | invariants | runtime-invariant registry: selection, uniqueness, child fibers, package-attributed failures |
| `ctx.typert` | core | typert-registry | live zod RPC contribution registry; consumed by api-gateway |
| `ctx.typertGateway` | core | api-gateway | associates Remote descriptors with Cordis services over RPC |
| `ctx.sessionPersistence` | seam | session-persistence | durability backends (`-jsonl`, `-sqlite`) |
| `ctx.settings` | seam | settings | namespace schemas, layered resolution (defaults→base→user) |
| `ctx.credentials` | seam | credentials | `CredentialRef` resolution, never carries raw secret values in config |
| `ctx.sessionTelemetry` | seam | session-telemetry | outbound redacted session reporting (e.g. `-otel` backend) |
| `ctx.storage` | seam | storage | KV backend (`-json`, `-sqlite`); `ctx.storageDomain` (core) layers typed domains on top |
| `ctx.messageFeedback` | core | message-feedback | per-message feedback, compare-and-set, Host RPC |
| `ctx.workspaceRegistry` | core | workspace | `WorkspaceId`-branded records |
| `ctx.sessionQuery` | seam | session-query | exact reads/filters/traces; `-sqlite` adds full-text search |
| `ctx.sessionReferenceResolver` | core | session-reference | cross-session mention resolution into durable message context |
| `ctx.sessionTitle` | seam | session-title | async title-generation providers (`-first-prompt-llm`, `-all-prompts-llm`) |
| `ctx.systemPrompt` | core | system-prompt | collects prompt sections + tool schemas per assembly |
| `ctx.tools` | core | tools | tool registry, Code Mode transport, full execution pipeline (see §7) |
| `ctx.userQuestions` | seam | user-questions | UI-backed human Q&A provider registration |
| `ctx.planMode` | core | plan-mode | logged `plan/mode` state, `/plan` command, exit-review arc |
| `ctx.agentPresets` | core | agent-presets | discovers/mounts preset `cordis.yml` under an agent scope at creation |
| `ctx.commands` | core | commands | direct human slash-commands (never sent to model) |
| `ctx.sessionProjections` | core | session-projection | domain fold units, eager per-session watermark drive |
| `ctx.sessionProjectionCache` | core | session-projection-cache | durable checkpoints of projection state, cold-read ladder |
| `ctx.skills` | seam | skill | merges provider skill catalogs (`-badge`, `-filesystem`) |
| `ctx.agents` | core | agent | live `Agent` handles, create/resume factory, initiator propagation |
| `ctx.agentDefaultModel` | core | agent-default-model | layers default `ModelSelection` via settings |
| `ctx.agentLoop` | bundle | agent-loop | the one concrete loop plugin |
| `ctx.goals` | core | goal | revisioned objective state folded from session log |
| `ctx.e2b` | core | e2b | shared E2B SDK handle, remote cwd, sandbox disposition |
| `ctx.subprocess` | seam | subprocess | process spawn/coordination (`-local`, `-e2b`); consumed by bash/terminal/lsp/subagent backends |
| `ctx.shell` | seam | shell | shell command execution (`bash-local`, `bash-sandbox`, `pwsh-local`) |
| `ctx.shellEnv` | core | shell-env | effect-scoped `DSH_*` env fact registration |
| `ctx.terminals` | seam | terminal | persistent PTY session registry (`terminal-bash`) |
| `ctx.sandbox` | seam | sandbox | per-call process confinement (`sandbox-local`) |
| `ctx.sandboxPolicy` | core | sandbox-policy | one home for default sandbox mode + workspace root |
| `ctx.approval` | seam | approval | one-shot permission decisions over `approval/request` waterfall |
| `ctx.permissionPresets` | core | permission-presets | bundles sandbox-mode + approval-policy knobs (`workspace-write`, `danger-full-access`) |
| `ctx.codeRuntime` | seam | code-runtime | runs model-written programs (Code Mode) against host async bindings |
| `ctx.fs` | seam | fs | filesystem ops (`-local`, `-sandbox`, `-e2b`) |
| `ctx.compaction` | seam | compaction | context compaction (`compaction-basic`) |
| `ctx.subagents` | seam | subagent | named-provider registry for child-agent delegation (`-spawn-in-process`, `-fork`, `-acp`, `-codex`, `-claude-code`, `-dsh-sdk`) |
| `ctx.jobs` | seam | jobs | background-task runtime (`jobs-local`) |
| `ctx.web` | seam | web | search/fetch providers (`-exa`, `-perplexity`, `-deepseek`, `-fetch-http`) |
| `ctx.spillStore` | seam | spill | oversized tool text offload (`spill-local`) + `spill-policy` consumer |
| `ctx.webServer` | core | webserver | plain `node:http` carrier, named-route registry |
| `ctx.clientModules` | core | modules | composes `DSH_BOOT` entry graph, serves plugin bundles for the Web UI |
| `ctx.workflowEngine` | seam | workflow | one engine per context (`workflow-worker-thread`), no named-provider registry |
| `ctx.lsp` | seam | lsp | normalized 4-operation LSP query seam |
| `ctx.apiProxy` | core | apiproxy | transport-agnostic host gateway for browser API calls |
| `ctx.dynamicCordisRunner` | core | cordis-host-runner | in-memory dynamic plugin definition registry + vm sandbox (user-defined runtime plugins) |
| `ctx.cordisInspect` | core | cordis-host-runner | host inspect providers + client provider manifest mirroring |

**Pattern to note**: `seam` = swappable capability with 1+ named/registered providers; `core` = single fixed spine implementation; `bundle` = the one concrete assembly plugin (e.g. the agent loop itself). This 3-way typing is itself documented and maintained by `scripts/gen-doc-graphs.ts` with a "completeness guard" — i.e. every declared Cordis service must be classified.

---

## 7. Event catalog conventions

- Every generated event doc block carries a `@mode` JSDoc tag (`@mode emit`, `@mode waterfall`, `@mode serial`, `@mode parallel`) as the single source of truth for dispatch semantics; a script (`gen-cordis-catalog.ts`) generates the docs from source and `verify-cordis-catalog` checks the catalog is fresh — declarations are checked against actual dispatch call sites.
- Two **separate vocabularies** exist and must not be confused:
  1. **Cordis (live) events** — `ctx.on/emit/waterfall/serial/parallel`, ephemeral, in-process coordination (`agent/*`, `tools/*`, `session/event` itself).
  2. **Session log events** (`SessionEventMap`) — durable, replayable, JSON-serialized rows appended to the append-only session log (`turn/start`, `step/start`, `tool/call`, `tool/result`, `assistant/message`, `compaction/*`, etc.), reached live only via the single `session/event` Cordis emit. Each row is tagged **surface** (contributes to derived LLM message history: only `user/message`, `assistant/message`, `tool/result`) or **log-only** (audit/state, e.g. `hook/invoked`, `approval/asked`, `plan/mode`, `sandbox/mode`, `todo/write`). Merge-extensible via TS declaration merging into `SessionEventMap`.
  3. Session events use `type`, monotonic `seq`, epoch `time`, `data`; surface events additionally carry `sourceEventSeqs` and `surfaceOp` (`'append'` or `{op:'replace', start, end}` — the latter used by compaction to replace/shadow a surface range).
- **Naming**: `namespace/action`, namespace = owning subsystem (`agent`, `agent-loop`, `agent-preset`, `tools`, `tool`, `session`, `approval`, `compaction`, `hook`, `permission`, `plan`, `sandbox`, `schedule`, `turn`, `step`, `user`, `web`, `subagent`, `tool-workflow`, `command`, `llm`, `feedback`, `goal`, `request`).
- **Tool pipeline event chain** (from `subsystems/tools`, representative of the waterfall-chain idiom used throughout): `tools/pre-execute` (waterfall, allow/deny/ask decision) → registered monotonic `ToolGuard`s (final-only, can deny but never re-allow) → `tools/execute` (waterfall, around-dispatch: timeout/retry/metrics, may replace only `exec.signal`) → `tools/post-execute` (waterfall, accept/replace/block) → tool-owned `finalizeContent` (sync, content-only) → `tools/result` (emit, frozen final observation). `tools/change` and `tools/code-dispatch-log` (waterfall, durable-log-copy-only content replacement) round out the family.
- Agent-loop events (`agent/*`) mirror the same idiom: `agent/pre-step` (waterfall, authoritative reject-or-enter), `agent/request` (waterfall) → `llm/stream` (waterfall) for the model call, `agent/request-error` (waterfall, retry-or-preserve), `agent/turn-stopping` (serial terminal checkpoint, may steer another step), plus plain `emit` status/lifecycle events (`agent/created`, `agent/disposed`, `agent/error`, `agent/status`, `agent/inbox/*`, `agent/session-start`).
- Scope-filtered dispatch: many events (esp. `tools/*`) are declared with `this: Scoped<ToolRuntime>` via `@deepseek-ai/dsh-scope` — listeners registered through `agent.ctx` (a scoped context) receive only that agent's events; listeners on the plain root context receive everything.

---

## 8. Loader / config practices

- `cordis.yml` is a **plugin tree**: each row = `{ id?, name, config?, disabled? }`; `!!js` expressions inside `config`/`disabled` are evaluated live against the plugin's own context (config) or the loader's context (disabled) at mount decisions — see §1 Loader Configuration.
- `insert:` blocks add local plugin rows (used pervasively in tutorial examples).
- **Groups + isolation**: `group: true` rows with an `isolate:` map scope a named service to just that group, letting two groups run differently-configured instances of the same service concurrently side by side (worked example: two Bash timeout configs, §3).
- **Plugin config contract**: export a `Config` TS interface *and* a same-named `Schema<Config>` (Schemastery) with `.default()`s inline on fields; Cordis validates + fills defaults using the schema at load time; an invalid config **fails the load loudly** with an actionable error (fail-fast is a stated design principle — "anything two deployments may want to set differently must be a configuration field," tested by "can `cordis.yml` change this without a code edit?").
- A config edit hot-replaces the plugin under HMR the same way source edits do (unload old, load new); because registrations are effects, no stale registration survives.
- `reference/config-catalog` is a **generated, per-package inventory** of every shipped plugin's config schema (one `##` heading per `@deepseek-ai/dsh-*` package name) — dozens of packages enumerated (acp, agent-default-model, agent-instructions, agent-loop, agent-presets, bash-local, bash-sandbox, client-connection/hmr, code-runtime-worker-thread, compaction-basic, compaction-tool-result-pruner, cordis-host-runner, credentials-local, e2b, fs-local/-sandbox, goal, headless, hooks-claude-code/-codex, host-apiproxy, host-directory-picker-browse, host-frontend-static, host-webserver, invariants, and many more) — confirms the "every tunable is a plugin config field, discoverable from one generated catalog" convention.

---

## 9. Plugin-authoring guidance (cookbook + basic/tool + practice)

### Minimal tool plugin shape (`reference/cookbook/adding-a-tool`)
```ts
export const name = 'my-tool'
export const inject = ['tools']
export function apply(ctx: Context) {
  ctx.tools.register(defineTool({
    name: 'read_file',
    description: 'Read a file from disk.',
    parameters: { path: { type: 'string', required: true }, limit: { type: 'number' } },
    output: { schema: { type: 'string' }, render: (_args, value) => [{ type: 'text', text: value }] },
    async execute(args, exec) { return readFile(args.path, { encoding: 'utf8', signal: exec.signal }) },
  }))
}
```
Rules: args are pre-validated against the `ParameterSchemaSpec`; the registered definition is a **readonly borrowed** same-process contract (never mutate after registration — dispose + re-register to hot-swap); execution identity (`callId`, `token`, `signal`) is protected/frozen; return exactly one canonical JSON value matching `output.schema` (never return content blocks from the body); throwing or an invalid value becomes a materialized `isError`; honor `exec.signal` for cancellation; use `output.presentationMeta` for replayable durable card data; use `agent.inject()` (not a "wake up") for async plugin-sourced context.

### Extension-point selection rule (repeated across pages — the canonical guidance)
- `tools/pre-execute` — reorderable allow/deny/ask policy.
- `ctx.tools.guard()` — final **monotonic** deny (a later listener can never re-allow what a guard denied).
- `tools/execute` — around-dispatch wrapping (timeout/retry/metrics); may replace only `exec.signal`.
- `tools/post-execute` — explicit result transform/block/context-attach.
- `tools/result` — contained, read-only observation of the frozen final outcome.

### Hook / permission-gate example (native, no external protocol needed)
```ts
ctx.on('tools/pre-execute', async (exec, next): Promise<PreToolDecision> => {
  if (!(await isAllowed(exec))) return { kind: 'deny', reason: 'Denied by policy.' }
  return next()
})
```
Framed explicitly as: "A 'native hook' is an ordinary Cordis plugin on an interception point; it needs no external protocol."

### Feature → mechanism map (`cookbook/extension-cookbook`, stated as making the "microkernel" claim checkable — every product feature maps to a listener on a documented extension point, no row modifies the loop itself). Selected rows:
- Hook system (Claude-Code/Codex style) → listeners on `agent/session-start`, `agent/pre-step`, `agent/request`, `tools/pre-execute`, `tools/post-execute`, `agent/turn-stopping`; vendor-specific bridge packages (`dsh-hooks-claude-code`, `dsh-hooks-codex`) map external hook-config files onto these same extension points.
- `/goal` → `ctx.goals` + a round-driver plugin scheduling same-session rounds through the public `Agent` API.
- `/loop` → `followup()` on `turn/end`.
- Dynamic workflow → `ctx.workflowEngine` + worker-thread engine + `workflow` tool; scoped tool/prompt registration + monotonic guard + `concludeTurn()`.
- Context compaction → `ctx.compaction` seam + `dsh-compaction-basic`, triggered on `agent/pre-step` (pressure) and `agent/request-error` (canonical overflow recovery).
- System prompt sections → `ctx.systemPrompt.section()` with ordering + scope-local shadowing.
- MCP-sourced tools → "one plugin per server: discover tools → `ctx.tools.register()`" (raw JSON-Schema `ToolDefinition`s accepted directly, bypassing `defineTool`).
- Sub-agent delegation → `ctx.subagents` named-provider registry + `dsh-tool-subagent` consumer exposing one configured provider to the model.
- Plugin hot-reload → "every registration is a `ctx.effect` → vendored HMR just works" (stated as a direct consequence of the effect discipline, not a separate mechanism).

### Three-role capability worked example (`develop/practice`) — see §5; the pattern is the canonical answer to "how do I add a new swappable capability."

### Inherited Cordis core API (`reference/cordis-api/inherited`) — members every plugin gets beyond the DSH-specific tier:
`ctx.on/once`, `ctx.emit/parallel/serial/bail/waterfall`, `ctx.plugin/inject`, `ctx.effect`, `ctx.get/set/provide/accessor/mixin` (low-level service-store access), `ctx.extend/isolate/intercept` (derive child context), `ctx.root/scope/fiber/registry/reflect/events/logger` (ambient handles), `ctx.timer` (+interval/timeout/throttle/debounce, disposable), `ctx.loader` (the booting config Loader), `ctx.hmr` (the HMR watcher). Plus inherited internal events: `internal/plugin`, `internal/status`, `internal/service`, `internal/update` (waterfall), `internal/get`/`internal/set` (waterfall), `internal/listener`, `internal/dispatch`, `hmr/change`, `hmr/reload`, `exit`, `loader/config-update`, `loader/entry-init`, `loader/partial-dispose`, `loader/patch-context`.

---

## 10. Tool/config catalogs (generated, not hand-read in full — noted for follow-up)

Two very large generated catalogs were located but not fully ingested (site truncation on scrape; local raw copies retained at the paths below for follow-up grep/read if needed):
- `reference/config-catalog` — per-package `Config` schema for every shipped `@deepseek-ai/dsh-*` plugin (~80+ packages headed alphabetically acp → …). Confirms every tunable is schema-declared and centrally cataloged.
- `reference/tool-catalog` — every shipped model-facing tool grouped by owning package (e.g. `dsh-tool-ask-user`→`ask_user_question`, `dsh-tools`→`run_code`, `dsh-plan-mode`→`exit_plan_mode`, `dsh-tool-bash`→`bash`, `dsh-tool-pwsh`→`pwsh`, `dsh-tool-cordis`→`cordis_define`/`cordis_inspect_list`/`cordis_inspect_query`/`cordis_inspect_self`/`cordis_run`/`cordis_stop`/`cordis_undefine` — i.e. Cordis itself is reflectively tool-exposed, letting a model define/run/inspect dynamic plugins — `dsh-tool-str-replace-editor`→`str_replace_editor`, `dsh-tool-fs`→`edit`/`read`/`read_image`/`write`, `dsh-tool-fs-search`→`glob`/`grep`, `dsh-tool-terminal`→`terminal_open`/`_close`/`_list`/`_read`/`_send`/`_signal`, `dsh-tool-goal`→`create_goal`, and more).
- Local raw scrape dumps (untranslated markdown, English source already): `core.md` full text at the tool-results cache path referenced by scrapeId `01a01574-1c88...` region — not re-saved here to keep this file bounded; re-scrape `en/reference/subsystems/core` if deeper detail is needed (agent-loop package spine, `AgentHandle` delivery/cancellation/interception contracts, `…Map → derived-union` and branded-id type patterns were confirmed present but not transcribed).

---

## 11. Notable structural takeaways for QMA/Cordis-class kernel comparison

- DSH treats the **whole harness as Cordis plugins**, including its own dynamic-extension runtime (`ctx.dynamicCordisRunner`/`tool-cordis` lets a *model* define, run, inspect, and undefine Cordis plugins at runtime inside a vm sandbox — recursive self-extension).
- The **seam vs core vs bundle** service classification is enforced by a generator+guard script, not just convention — every `ctx.<key>` must be classified, giving a machine-checkable extensibility inventory (`reference/capability-seams`).
- The **durable session log** (event-sourced, merge-extensible `SessionEventMap`, surface vs log-only) is architecturally separate from the **live Cordis event bus**, bridged only through one `session/event` emit — this two-bus split (replayable truth vs live coordination) is a repeated, load-bearing distinction across nearly every subsystem page.
- Tool/agent-loop interception is built from a **small closed set of waterfall + guard + emit stages** reused identically across subsystems (pre → guard → around-dispatch → post → finalize → observe), documented as the one pattern to imitate for any new capability rather than inventing new event shapes per feature.
- Everything-is-an-effect discipline (`ctx.effect`, `ctx.on`, `.register()`) is what makes HMR "just work" without bespoke unload code — repeatedly called out as a design payoff, not incidental plumbing.
