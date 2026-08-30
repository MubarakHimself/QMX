# Cordis — Plugin-Lifecycle Reference (for the QMX daemon plugin manager)

Reference: **Cordis** (cordiverse) as vendored by the **DeepSeek Harness**. Studied ONLY as a
plugin-lifecycle model for the QMX agentic harness. Operator ruling stands: this paradigm applies
to the agentic daemon, **never** to the trading platform. QMX is single-operator with a handful of
first-party plugins — that filter (Constitution §1, §3) governs every line below.

Primary sources (all checked 2026-08-28): primer
`deepseek-harness.github.io/deepseek-harness/reference/cordis-primer` (zh); tutorial ch2/3/4/6
`.../develop/cordis-tutorial/{02-lifecycle-and-effects,03-services,04-events,06-composition-and-hmr}`;
Context API `.../reference/cordis-api/context`; repo `github.com/cordiverse/cordis`; paper
`github.com/cordiverse/paper`.

---

## Q1 — Target mental model
A running system is a **tree of plugins mounted onto a shared Context**. Every capability — tools,
LLM adapter, file access, even the agent loop — is a plugin occupying a stable `ctx.<key>`. The
paper names the discipline the **context paradigm** with two orthogonal axes: **temporal
composability** = a component's side effects can be *completely reverted* on removal (formalized as
*revertible effects*: every context transformation carries an inverse the runtime holds); **spatial
composability** = inter-component dependencies are *declared and reactively managed* (formalized as
*reactive coeffects*: every context change is classified against a component's coeffect spec to drive
its activation/deactivation) (github.com/cordiverse/paper, checked 2026-08-28). Practical slogan:
*load = install effects; unload = the runtime plays every inverse back*.

## Q2 — Concrete runtime / API structures
**Plugin form.** A plugin is a function `(ctx) => {}`, an object `{ name, inject?, apply(ctx) }`, or a
`Service` subclass. `ctx.plugin(child)` mounts it and returns a **fiber** (runtime handle); function
plugins need no `apply`, objects/classes do (ch2).
**apply / dispose contract.** `apply(ctx)` runs on load. There is no `dispose` method authors write —
teardown is the sum of the plugin's recorded effects. `fiber.dispose()` awaits all cleanup (incl.
async disposers) and **recursively unloads every child plugin** (ch2).
**Effects (reversible registration).** `ctx.effect(() => { ...acquire...; return () => {...release...} })` —
body runs at load, returned **disposer** runs at unload. Disposers fire in **reverse registration
order**; multiple *async* disposers run **concurrently** — put ordered teardown inside one disposer
(ch2). Built-in registrations are already effects and auto-revert: `ctx.on(event,fn)`,
`ctx.plugin(child)`, service registration, and registry calls like `ctx.tools.register(...)` (which
attach their disposer to the calling plugin) (ch2). `Context.effect` symbol exposes an `EffectMeta`
diagnostics tree per disposer (cordis-api/context).
**Fiber state machine.** `PENDING → LOADING → ACTIVE → UNLOADING → DISPOSED`, with a `FAILED` branch
when `apply` or config validation throws. PENDING = declared but injected services not yet present
(ch2).
**Services.** `class GreeterService extends Service { constructor(ctx){ super(ctx,'greeter') } }`; the
`super(ctx,name)` call registers the instance at `ctx.<name>` (itself an effect — removed on unload).
Consumers declare `export const inject = ['greeter']`; the fiber stays PENDING until every listed
service exists, so `ctx.greeter` is guaranteed inside `apply`. **`inject` is live, not one-shot**: if
a required service is unloaded/hot-swapped, each dependent unloads too and reloads when it returns
(ch3). Optional dep = omit `inject`, probe `ctx.get('greeter')` (undefined if absent). Flat service
namespace (ch3). Reflect layer: `ctx.get(name,strict=true)` (strict returns only active-provider
impls), `ctx.set(name,value)` (only providing fiber may set), `ctx.provide(name,value)→disposer`,
`ctx.accessor`, `ctx.mixin` (cordis-api/context).
**Event bus — 5 dispatch modes** (mode is part of each event's contract) (ch4):
`emit(name,…)` sync broadcast, no await/return; `await parallel(name,…)` all listeners concurrent;
`await serial(name,…)` sequential+awaited, **first non-null/false/undefined return wins and stops the
rest**; `bail(name,…)` synchronous serial; `waterfall(name,…,next)` surround middleware — each
listener gets `(…args, next)`, transforms `next()`'s result or **short-circuits (a "veto") by not
calling `next()`**. Discipline: observe-only waterfall listeners MUST call `next()` or they silently
swallow downstream defaults. Harness uses waterfall for `agent/request` (replace model-call config)
and `approval/request` (policy answers for the user) (ch4, primer).
**Scoping / isolation.** Context is a proxy; `ctx.extend(meta)`, `ctx.isolate(name,label?)`,
`ctx.intercept(name,config)` return scoped child contexts **without mutating the parent**. `isolate`
gives a name an independent service scope; passing the same `label` joins two scopes so two plugin
groups can each see a differently-configured `shell` provider (cordis-api/context, ch6).
**HMR / loader.** `cordis.yml` is the plugin tree; entries carry `id` (stable identity), `name`,
`config`, `disabled`, and nestable groups. `@deepseek-ai/cordis-plugin-hmr` watches files and on save
**unloads the old instance (all effects roll back) then loads the new code and re-runs apply**;
editing `cordis.yml` diffs entries **by `id`**, mounting/unmounting/reconfiguring only what changed
(entries without an explicit `id` get a fresh id each read, so any edit re-mounts them). `disabled:
true` unloads without deleting the entry (ch6). HMR is possible *because* unload releases effects and
load follows dependencies — nothing HMR-specific in a plugin (ch6, paper: "configuration
reconciliation and hot module replacement").

## Q3 — Failure modes it solved
- **Leaked side effects on unload** (dangling timers, orphan listeners, half-removed tools/prompt
  fragments) → every registration carries its inverse; unload is total and ordered (ch2).
- **Manual startup sequencing / import-order coupling** → `inject` + PENDING express order through
  dependencies; file order is irrelevant (ch3).
- **Stale references to a swapped/removed capability** → reactive coeffect deactivates dependents
  when their service vanishes; no consumer holds a dead handle (ch3).
- **Unsafe hot reload** → clean unload+reload makes HMR fall out of the effect/dependency machinery
  for free (ch6).
- **Silent "why is nothing happening"** → the fiber state machine makes PENDING (missing dep)
  inspectable via `ctx.registry` + `FiberState` (ch6).

## Q4 — What QMX should reuse (conceptually only — QMX owns the contract, §3)
1. **Reversible registration as the load-bearing invariant.** activate installs, deactivate replays
   inverses; the *runtime* holds the disposers, not the plugin author. This is the whole answer to
   "unload a first-party plugin cleanly." Python analogue: a per-plugin `contextlib.ExitStack` /
   `AsyncExitStack` — every `register_*` pushes its undo onto the stack; unload closes it LIFO.
2. **Register-through-a-scoped-handle, look up by name.** Plugins get a `PluginContext`, register into
   named QMX registries (tools, hooks, skills, loops, graphs, memory-provider, model-deployment,
   commands, ui-view-over-wire), and resolve peers by name — never import a concrete peer. Gives
   decoupling + an automatic disposal scope.
3. **Dependency-declared load order** (`depends`/`requires`), not a hand-written boot sequence.
4. **Inspectable lifecycle state** (an explicit small state enum) so a missing dependency is a
   diagnosable condition, not a silent hang.
5. **The waterfall/veto shape** — but folded into QMX's already-committed **Hook** primitive
   (observe / block / modify input / inject context), not re-created as a second event bus.

## Q5 — What QMX should reject (INHERITED FASHION for a general framework / many authors)
- **HMR file-watching of production plugins & live re-composition.** Dev nicety; the operator wants
  determinism (Constitution §2). A handful of first-party plugins load at boot; use an explicit
  `reload(plugin_id)` command or a daemon restart. Reject the file-watcher.
- **Full reactive coeffect re-mount** (services vanishing/returning at runtime, dependents auto-
  suspending to PENDING and silently resuming). First-party plugins are present or a hard startup
  error — not a fabric of appearing/disappearing tenants.
- **`isolate()` / `intercept()` / label-joined scopes.** Multi-config, multi-tenant overlay fashion.
  One operator = one config; no need for two differently-configured `shell` providers side by side.
- **The open `ctx.<key>` service container + declaration-merged typed event bus with 5 dispatch
  modes.** Architecture-by-enumeration (transcript §8 items 6, 20). QMX exposes a *small fixed* set of
  registries, not a space where any plugin invents a global `ctx.foo` and its own emit/serial/bail
  channels. Hooks are the one interception surface.
- **Loader `!!js` expression config, overlays, include-plugin templating** — general-purpose config
  metaprogramming with no single-operator payoff.
- **Marketplace / plugin store / trust levels** (transcript §8 items 2, 19) — no third-party
  publishers, so no untrusted-extension problem to solve.
- TS-native leverage that does not port: **declaration merging** (compile-time typing of `ctx.x` and
  event names) and the **proxy Context**. In Python these become explicit registry method signatures +
  `typing.Protocol`; do not try to reproduce the proxy magic.

## Q6 — The smallest QMX-owned plugin lifecycle contract (Python daemon)
Note: the daemon language is still open (TS vs Python, transcript §3 Q1). Cordis's ergonomics are TS-
native; the Python design below keeps the *invariant* (reversible activate/deactivate) and drops the
proxy/declaration-merging machinery.

```python
# Manifest — plugin.toml (or a pyproject entry-point); validated before activate
class PluginManifest:
    id: str                     # stable identity (HMR-style diffing, disable/enable)
    version: str                # semver of the plugin
    qmx_api: str                # daemon contract range it targets, e.g. ">=1.2,<2"  (COMPAT GATE)
    desk: str                   # naming rule: research|trading|dev|analysis|pm (no blanket "qmx")
    depends: list[str]          # required service/registry names — topo-ordered load
    provides: list[str]         # service names this plugin registers
    permissions: list[str]      # capability grants requested (checked at load)
    entrypoint: str             # "module:PluginClass"

class Plugin(Protocol):
    def activate(self, ctx: "PluginContext") -> None: ...   # register everything through ctx
    # no deactivate() required — teardown = ctx.scope closed LIFO; optional hook for exotic cleanup
    def deactivate(self) -> None: ...                        # optional

class PluginContext:                 # the scoped handle; wraps an AsyncExitStack per plugin
    def register_tool(self, spec) -> Disposer: ...
    def register_hook(self, event, fn) -> Disposer: ...      # observe|block|modify|inject (waterfall shape)
    def register_skill(self, spec) -> Disposer: ...
    def register_loop(self, spec) -> Disposer: ...
    def register_graph(self, spec) -> Disposer: ...
    def register_memory_provider(self, provider) -> Disposer: ...
    def register_model_deployment(self, dep) -> Disposer: ...
    def register_command(self, name, fn) -> Disposer: ...
    def contribute_ui_view(self, point, view_ref) -> Disposer: ...   # over the daemon wire contract
    def on_dispose(self, fn: Callable[[], None]) -> None: ...  # raw effect escape hatch (ctx.effect)
    def get_service(self, name: str): ...                     # resolve peer by name (None if absent)

class PluginManager:
    def load(self, m: PluginManifest) -> None:  # validate qmx_api compat -> permissions -> depends
        ...                                      # present -> topo activate; missing dep = startup error
    def unload(self, id: str) -> None: ...        # close the plugin's scope: disposers run LIFO
    def reload(self, id: str) -> None: ...        # explicit unload+load (NO file watcher)

Disposer = Callable[[], None]                     # every register_* returns one; auto-pushed to scope
LifecycleState = Enum("LOADED","ACTIVE","FAILED","UNLOADED")   # small, inspectable
```

**Load flow (answers the operator's upgrade fear, packet §L5015–5035):** manifest validation →
`qmx_api` compatibility check → permission check → dependency check → migrations if any → topo-sorted
`activate(ctx)` → on success publish the plugin's contributions to the registries; UI learns the new
contribution points over the versioned wire contract. **Unload** closes the scope so every recorded
`Disposer` runs LIFO — tools, hooks, skills, loops, graphs, model deployments, commands and UI
contributions all disappear together, cleanly. That single guarantee is the entire reason to study
Cordis; everything else Cordis carries is general-public machinery QMX does not need.
