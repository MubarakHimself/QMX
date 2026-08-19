# Cordis framework — code study for QMA kernel (Python reimplementation)

Sources (all read directly from cloned source, not docs):
- `https://github.com/cordiverse/cordis` @ `main` (packages/core, packages/loader) — cloned to scratchpad, files at `packages/core/src/{context,events,fiber,reflect,registry,service,utils,logger,index}.ts`.
- Vendored copy inside `deepseek-ai/deepseek-harness` at `vendor/` (cloned to scratchpad):
  - `vendor/README.md` — sync process, manifest, 18-entry "local modifications" log.
  - `vendor/cordis/src/*.ts` — pinned at upstream `cordis@4.0.0-rc.7`, commit `56b3d4f725681cf4556c1a8695a709cc3b6eed74` (packages/core), rescoped to `@deepseek-ai/cordis`.
  - `vendor/loader/src/{index,config/entry,config/tree,config/group,config/isolate}.ts` — `@cordisjs/plugin-loader@1.0.0-rc.5`.
  - `vendor/hmr/src/index.ts` — `@cordisjs/plugin-hmr@1.0.15` (deepseek-harness fork, commit `abb0a307...`).
  - `vendor/include`, `vendor/group`, `vendor/timer`, `vendor/logger-console`, `vendor/schemastery`, `vendor/cosmokit` — sibling vendored packages.
  - Two real plugin implementations that consume the framework: `packages/api/gateway/src/index.ts` (`TypertGatewayService extends Service`) and `packages/attachment/attachment/src/index.ts` / `packages/code-runtime/code-runtime/src/index.ts` (abstract `Service` subclasses defining a capability seam via `declare module`).

Every code excerpt below is copied verbatim from the files named; line numbers refer to those files as read.

---

## 1. Plugin protocol (apply/inject signatures, `Service` base class)

### 1.1 Plugin shapes (`registry.ts` lines 92–146)

```ts
export type Plugin<T = any> =
  | Plugin.Function<T>
  | Plugin.Constructor<T>
  | Plugin.Object<T>

export namespace Plugin {
  export interface Base<T = any> {
    name?: string
    Config?: StandardSchemaV1<any, T>
    inject?: Inject
    provide?: string | string[]
    intercept?: Dict<boolean>
  }
  export interface Function<T = any> extends Base<T> { (ctx: Context, config: T): any }
  export interface Constructor<T = any> extends Base<T> { new (ctx: Context, config: T): any }
  export interface Object<T = any> extends Base<T> { apply(ctx: Context, config: T): any }
  export interface Runtime {
    name?: string
    fibers: DisposableList<Fiber>
    callback: globalThis.Function   // registry identity key
    Config?: StandardSchemaV1
  }
}
```

Three interchangeable entrypoint shapes: a plain function `(ctx, config) => effect`, a class constructed as `new Plugin(ctx, config)`, or an object with an `apply(ctx, config)` method. `RegistryService.resolve()` (registry.ts:222-228) picks the callback:
```ts
resolve(plugin: Plugin): Function | undefined {
  try {
    if (typeof plugin === 'function') return plugin
    if (isApplicable(plugin)) return plugin.apply   // plugin.apply may throw
  } catch {}
}
```
`isApplicable` = `object && typeof object === 'object' && typeof object.apply === 'function'`. The **callback function identity** (the class itself, or the object's `.apply` method) is the map key in `RegistryService._internal: Map<Function, Plugin.Runtime>` — this is how re-`ctx.plugin()`'ing the same function reuses one `Runtime` and spawns another `Fiber` (one Runtime can have many fibers, e.g. HMR reload keeps the Runtime and swaps fibers).

`ctx.plugin(plugin, config)` (registry.ts:316-336): validates the current fiber is active, gets-or-creates the `Runtime` keyed by resolved callback, constructs a new `Fiber(ctx, config, Inject.resolve(plugin.inject), runtime, outerStack)`, and returns a thenable wrapper (`Object.create(fiber)` with a custom `.then`) so `await ctx.plugin(X)` waits for the fiber to settle (`fiber.await()`) without changing what synchronous callers get back (a `Fiber` instance they can inspect immediately).

`ctx.inject(deps, callback)` (registry.ts:300-302) is sugar: `this.plugin({ inject: deps, apply: callback, name: callback.name })` — an anonymous plugin whose whole body is gated on dependencies.

**Fiber execution dispatch** (fiber.ts:250-261, inside the `EffectRunner.execute`):
```ts
execute: function () {
  if (isConstructor(runtime.callback)) {
    const instance = new runtime.callback(this.ctx, this.config)
    for (const hook of instance?.[symbols.initHooks] ?? []) hook()
    return instance?.[symbols.init]?.()
  } else {
    return runtime.callback(this.ctx, this.config)
  }
}
```
`isConstructor` (utils.ts:79-89) distinguishes class plugins from function plugins by checking `func.prototype` exists and it isn't a generator/async-generator function (arrow functions have no `.prototype` and so are never misclassified as constructors). For class plugins, after `new`, any `[Service.init]` async generator hook (see §5) runs, and any `[symbols.initHooks]` queued by decorators (`@Inject` on a method, see §1.3) fire.

### 1.2 `Service` base class (`service.ts`, full file read)

```ts
export abstract class Service<out T = never> {
  static readonly init: unique symbol = symbols.init
  static readonly check: unique symbol = symbols.check
  static readonly config: unique symbol = symbols.config
  static readonly invoke: unique symbol = symbols.invoke
  static readonly extend: unique symbol = symbols.extend
  static readonly tracker: unique symbol = symbols.tracker
  static readonly resolveConfig: unique symbol = symbols.resolveConfig

  declare [symbols.config]: T
  public name!: string

  constructor(protected ctx: Context, name: string) {
    name ??= this.constructor['provide'] as string
    let self = this
    const tracker: Tracker = { associate: name, property: 'ctx' }
    if (self[symbols.invoke]) {
      self = createCallable(name, joinPrototype(Object.getPrototypeOf(this), Function.prototype), tracker)
    }
    self.ctx = ctx
    self.name = name
    defineProperty(self, symbols.tracker, tracker)
    self.ctx.reflect.provide(name, self, this[symbols.check])
    return self
  }
  ...
}
```

Key points:
- A `Service` subclass calls `super(ctx, name)` and is **self-registering**: the constructor calls `ctx.reflect.provide(name, self, check)` itself — there is no separate "install" step. `provide()` is wrapped in `ctx.fiber.effect(...)` (see §4), so the registration is disposed automatically when the fiber that constructed the service unloads.
- `[Service.check]` — an optional instance method (`this[symbols.check]`) is passed through as the `check` predicate to `reflect.provide`; dependents only see the service "available" while `check()` returns true (re-evaluated via `_checkImpl`, see §3).
- `[Service.invoke]` — if the subclass defines this symbol method, the constructor swaps `self` for a **callable object** built by `createCallable` (utils.ts:226-233), making `ctx.logger('name')`-style call syntax work: calling the service itself dispatches to `value[symbols.invoke].apply(proxy, args)` (utils.ts:220-223, `applyTraceable`).
- `constructor` returning `self` (a different object than the one JS is constructing, because `class` constructors may return an object override) is what lets `new SomeService(ctx, ...)` produce a callable function when `[Service.invoke]` is present — a JS-specific trick (explicit constructor return override) with no Python equivalent (Python `__new__` can return a different type but the result won't be callable-as-a-function unless it implements `__call__`, which is straightforward — but subclassing `object` to conditionally return a *function-shaped* instance has no analogue; Python's `__call__` protocol is the natural substitute).
- `[symbols.filter]` (service.ts:61-63) — the default context filter used by isolation: `ctx[symbols.isolate][this.name] === this.ctx[symbols.isolate][this.name]`, i.e. an event/listener registered under this service is only visible to contexts sharing the same isolation label for that service name.
- `[symbols.resolveConfig]` (service.ts:86-102) — merges "intercept" config from every ancestor `ctx.intercept(name, cfg)` call by walking the intercept prototype chain (`Object.getPrototypeOf`), unshifting each own-property level (so **root-closest intercepts apply first**, closer overrides later), then `base` prepended / `head` appended, using `Config.merge` if the service declares a standard-schema `Config` with a `.merge`, else `Object.assign`.
- `static [Symbol.hasInstance]` (service.ts:104-114) — a **custom `instanceof`** implementation that walks `instance.constructor.prototype.constructor` chains rather than trusting the object's actual prototype chain, explicitly because "constructor may be a proxy" (services are wrapped in tracing proxies — see §7 — so `instanceof` needs to unwrap them manually).

### 1.3 `@Inject` decorator (`registry.ts` lines 37-60)

```ts
export function Inject<K extends InjectKey>(name: K, config?: ...) {
  return function (value: any, decorator: ClassDecoratorContext | ClassMethodDecoratorContext) {
    if (decorator.kind === 'class') {
      // contributes to the class's static `inject` map (with proto inheritance via checkProto symbol)
      value.inject[name] = config
    } else if (decorator.kind === 'method') {
      // records metadata + registers an initializer that, once the instance
      // exists, calls ctx.inject(deps, () => method.call(this)) to defer the
      // method until services are available
      const inject = (value[symbols.metadata] ??= {}).inject ??= Object.create(null)
      inject[name] = config
      decorator.addInitializer(function () {
        (this[symbols.initHooks] ??= []).push(() => {
          (this.ctx as Context).inject(inject, (ctx) => value.call(...))
        })
      })
    }
  }
}
```
This uses the **TC39 Stage-3 decorators** (native `ClassDecoratorContext`/`ClassMethodDecoratorContext`, `decorator.addInitializer`), not legacy experimental decorators. On a class, it just builds a static `inject` dict (walking the prototype chain for inherited requirements via a `checkProto` marker symbol, `Inject.resolve` in registry.ts:71-88). On a *method*, it delays that single method's invocation until its own service dependencies resolve, independent of the class's own `inject`.

---

## 2. Context / container internals — how `ctx.<key>` lookup works

### 2.1 The Context object is a `Proxy`

`Context` constructor (context.ts:71-84):
```ts
constructor() {
  this[symbols.isolate] = Object.create(null)
  this[symbols.intercept] = Object.create(null)
  const self = new Proxy<this>(this, ReflectService.handler)
  this.root = self
  ...
  return self   // constructor returns the proxy, not `this`
}
```
So **every `Context` instance ever visible to user code is a `Proxy`**, never the bare class instance — another JS-specific trick (constructor return-override) baking the proxy invisibly into `new Context()`.

`ReflectService.handler` (reflect.ts:135-206) implements `get`, `set`, `has`:

**get trap** (reflect.ts:136-171):
1. `isSpecialProperty(prop)` — symbol, reserved word (`prototype`/`then`), numeric-string, or leading `_` — falls straight through to `Reflect.get` (i.e. bypasses service resolution; these are treated as plain object properties).
2. If the prop is an **own/inherited property already present on the target** (e.g. `fiber`, `reflect`, `registry`, `events`, `logger`, `root`, or something set via plain assignment/`extend()`), return `getTraceable(ctx, Reflect.get(...))` — wrapped so nested method calls see the calling context (§7).
3. Otherwise, treat it as a **service lookup**. Build an `Error` (used for diagnostics/stack enrichment). Check `ctx.reflect.props[prop]` for a declared **accessor** (`type: 'accessor'`) — computed property — and call its `get` hook.
4. Otherwise, if `ctx.fiber.runtime` is falsy (this is the root fiber / not inside a plugin), fall back to a non-strict `ctx.reflect.get(prop, false)` (looked up ignoring active-state).
5. Otherwise, run the **`internal/get` waterfall event** (an extension point letting other services intercept/veto property reads) whose inner "next" callback does the actual isolation-scope walk:
   ```ts
   return ctx.events.waterfall('internal/get', ctx, prop, error, () => {
     const key = target[symbols.isolate][prop]
     let fiber = (ctx[symbols.shadow] as Context ?? ctx).fiber
     while (true) {
       const impl = fiber.store?.[prop]
       if (impl) return getTraceable(ctx, impl.value)
       if (prop in fiber.inject) { error.message = `cannot get required service "${prop}" in inactive context`; throw error }
       if (!fiber.runtime) throw error
       if (fiber.parent[symbols.isolate][prop] !== key) throw error
       fiber = fiber.parent.fiber
     }
   })
   ```
   This walks **up the fiber chain** (not the raw prototype chain) looking for a cached impl in `fiber.store` (a per-fiber snapshot of currently-injected services taken at activation, see §3), stopping either when found, when the property is a declared-but-unavailable injection (hard error), when the root is reached, or when the isolation label changes between parent/child (an `isolate()` boundary — see below — walls off lookup).

**set trap** (reflect.ts:173-197): symbol/reserved props go to `Reflect.set` directly; otherwise requires a declared `Property` (service or accessor) or throws `cannot set property "X" without provide`; accessor setters get called; service writes go through an `internal/set` waterfall to `ctx.reflect.set(prop, value, error)` which **only permits the providing fiber to write** (reflect.ts:254-265 — `if (impl.fiber !== this.ctx.fiber) throw`).

**has trap** (reflect.ts:199-205): special props delegate to `Reflect.has`; otherwise true if either the raw target has it or `ctx.reflect.props[prop]` is declared.

### 2.2 Prototypal child contexts — `extend()`, `isolate()`, `intercept()`

`Context.extend(meta)` (context.ts:99-107):
```ts
extend(meta = {}): this {
  const shadow = Reflect.getOwnPropertyDescriptor(this, symbols.shadow)?.value
  const self = Object.create(getTraceable(this, this))
  for (const prop of Reflect.ownKeys(meta)) {
    Object.defineProperty(self, prop, Reflect.getOwnPropertyDescriptor(meta, prop)!)
  }
  if (!shadow) return self
  return Object.assign(Object.create(self), { [symbols.shadow]: shadow })
}
```
A child context is `Object.create(parentProxy)` with `meta`'s own keys defined directly on the child — **plain JS prototypal inheritance** is the mechanism for "context extends parent, own overrides shadow it." Because the parent passed to `Object.create` is itself the Proxy (`getTraceable(this, this)`), *every* property read on the child that isn't shadowed re-triggers the parent's proxy traps, so isolate/intercept maps, `fiber`, `reflect`, etc. are inherited by delegation, not copying. This is the crux of Cordis's "child scope" model: a child context is a **new proxy-linked object**, not a deep-cloned config.

`isolate(name, label?)` (context.ts:121-125): creates `shadow = Object.create(this[symbols.isolate])` (a new isolate map prototype-chained off the parent's), sets `shadow[name] = label ?? Symbol(name)`, and extends with that new isolate map. Below this context, service `name` resolves against a **different symbol key** in `ReflectService.store`, so `ctx.provide(name, ...)` there registers under a distinct slot without affecting the parent's binding for `name`. Passing the *same* `label` symbol to two `isolate()` calls elsewhere joins their scopes (shared isolated namespace).

`intercept(name, config)` (context.ts:139-145): identical shape but for `[symbols.intercept]`, consumed by `Service[symbols.resolveConfig]` (§1.2) to merge ancestor-declared config into a service's own resolved config.

### 2.3 `ReflectService` — the "container" proper (reflect.ts, full file read)

- `store: Dict<Impl, symbol>` — flat map keyed by **isolation-label symbol** (not by context) → `Impl { name, fiber, value, check }`. This is the single source of truth for "what implementation currently answers for service X in isolation scope S."
- `props: Dict<Property>` — flat map of declared context properties, name → `{ type: 'service' }` or `{ type: 'accessor', get, set? }`.
- `provide(name, value, check?)` (reflect.ts:277-305) is itself an **effect** (`ctx.fiber.effect(...)`, see §4): on setup it registers `props[name]`, allocates `ctx.root[symbols.isolate][name]` if unset, writes into `store[key]`, writes into `ctx.fiber.store![name]` (own-fiber snapshot), and if the fiber is already `ACTIVE`, calls `notify([name])` immediately. Its teardown deletes `store[key]`, calls `notify([name])` again (waking dependents so they see the service disappear), `await`s every affected fiber's settle, *then* deletes the entry from the providing fiber's own `store` (comment: "ensure self access before dependencies cleanup" — the provider can still read its own service value while its dependents are unwinding).
- `notify(names, filter?)` (reflect.ts:314-336) is the **dependency-change propagation engine**: iterates every registered `Plugin.Runtime` and every one of its live `fibers`; for each fiber, for each changed service `name` that's in that fiber's `inject` map and passes the isolation `filter`, calls `fiber._checkImpl(name)` (refresh the per-fiber snapshot for that one name) and marks the fiber dirty; dirty fibers get `fiber._refresh()` called (recomputes the fiber's activation "epoch" string, §3) and are collected into the returned list. It also fires an `internal/service` event scoped via a synthetic filtering context (`self[symbols.filter] = (target) => filter(target, name)`).
- `mixin(source, mixins)` (reflect.ts:364-390) — implements `ctx.on`/`ctx.emit`/etc forwarding onto `ctx` directly. For each `[ctxKey, serviceKey]` pair it calls `self.accessor(ctxKey, { get(receiver, error) { ... bind to service method ... }, set(...) })`. This is how `context.ts`'s constructor wiring (`this.mixin('reflect', [...]); this.mixin('fiber', [...]); this.mixin('registry', [...]); this.mixin('events', [...])`) exposes e.g. `ctx.on(...)` as sugar for `ctx.events.on(...)` — implemented entirely via the accessor mechanism, not static class methods.
- `accessor(name, {get, set?})` (reflect.ts:345-353) — also itself an effect; disposal simply `delete`s the prop declaration.
- `trace()` / `bind()` (reflect.ts:398-417) expose the tracing-proxy machinery (§7) for ad-hoc use.

**No metaclasses, no decorators drive DI here** — the container is a hand-rolled `Proxy` + two flat dictionaries (`store` keyed by isolation symbol, `props` keyed by name) + a fiber-chain walk on miss. This is directly portable to Python: a `Context.__getattr__`/`__setattr__` override plus the same two dicts and the same walk-up-fiber-parents loop. The **hard-to-port piece** is exclusively the `Proxy` mechanics — see §7.

---

## 3. Event dispatch implementation — all four (five) modes

`EventsService` (events.ts, full file read). Storage: `_hooks: Record<keyof any, Hook[]>` — one array per event name, each `Hook = { ctx, callback, prepend?, global? }`.

`dispatch(type, args)` (events.ts:165-175) — shared resolution step every mode calls first:
```ts
dispatch(type: string, args: any[]) {
  const thisArg = typeof args[0] === 'object' || typeof args[0] === 'function' ? args.shift() : null
  const name: string = args.shift()
  if (!name.startsWith('internal/')) this.emit('internal/dispatch', type, name, args, thisArg)
  const filter = thisArg?.[Context.filter]
  return (this._hooks[name] || [])
    .filter(hook => hook.global || !filter || filter.call(thisArg, hook.ctx))
    .map(hook => hook.callback.bind(thisArg))
}
```
- Optional leading `thisArg` (object/function) is shifted off — this is both the "explicit this" for listeners *and* the context-filter source. `Context.filter` (symbol) on `thisArg` is a predicate `(hookCtx) => boolean` checked per hook unless the hook is `{ global: true }`.
- Every *public* (non-`internal/`) dispatch self-reports via `emit('internal/dispatch', mode, name, args, thisArg)` — a synchronous, unfiltered meta-event for diagnostics/telemetry, itself dispatched through the same machinery (feedback loop guarded only by the `internal/` name-prefix check).
- Returns bound callback closures, already filtered by isolation-context match.

**The four public modes + one internal mode:**

| Mode | Method | Semantics |
|---|---|---|
| `emit` | events.ts:194-196 | `dispatch('emit', args).map(cb => cb(...args))` — fire-and-forget, synchronous call to every listener, return values and promises ignored (async listener errors are NOT awaited here — they'd need `.catch` themselves or bubble as unhandled rejections). |
| `parallel` | events.ts:183-187 | `await Promise.allSettled(dispatch('emit', args).map(async cb => cb(...args)))`; rejections collected and re-thrown as one `AggregateError`. Reuses `dispatch('emit', ...)` — parallel and emit resolve the *same* listener set, differing only in await/error semantics. |
| `serial` | events.ts:204-209 | `for (const cb of dispatch('serial', args)) { const r = await cb(...args); if (isBailed(r)) return r }` — sequential, awaited, stops at first bail. |
| `bail` | events.ts:217-222 | Same as serial but synchronous (`cb(...args)`, no `await`) — stops at first bail. |
| `waterfall` | events.ts:234-243 | ```const cbs = dispatch('waterfall', args); const inner = args.pop(); const next = () => { const cb = cbs.shift() ?? inner; return cb(...args) }; args.push(next); return next()``` — the *last* dispatch argument is treated as the terminal continuation; each listener is called with all prior args plus a synthesized `next` closure that dequeues the next listener (or falls through to the original terminal `inner` once the queue is empty) — classic middleware/onion composition. A listener that never calls `next()` vetoes everything downstream including the built-in behavior. |

`isBailed(value)` (events.ts:13-15): `value !== null && value !== false && value !== undefined` — the "did a serial/bail listener produce a real answer" predicate (JS's specific falsy-but-not-a-bail set: `0`, `''`, `NaN` **do** count as bails; only exactly `null`/`false`/`undefined` don't — a detail to replicate precisely in Python, where the natural translation would be `is not None` unless `False` must also pass through).

**Special bootstrapping listeners registered in the constructor** (events.ts:140-155) implement `internal/update`'s own waterfall chain as *fiber-scoped* sub-hooks:
```ts
this.on('internal/listener', function (name, listener, options) {
  if (name === 'internal/update' && !options.global) {
    const hooks = this.fiber._hooks['internal/update'] ??= new DisposableList()
    return hooks[options.prepend ? 'unshift' : 'push'](listener)
  }
})
this.on('internal/update', function (config, noSave, next) {
  const cbs = [...this._hooks['internal/update'] || []]
  const _next = () => { const cb = cbs.shift() ?? next; return cb.call(this, config, noSave, _next) }
  return _next()
}, { global: true, prepend: true })
```
This means `ctx.on('internal/update', fn)` calls are intercepted at *registration time* (via the `internal/listener` bail hook, see below) and redirected into a **per-fiber** list (`fiber._hooks['internal/update']`) rather than the global `_hooks` table — so each plugin's own update-hooks form their own private waterfall chain, nested inside the single global `internal/update` waterfall that Loader triggers on `fiber.update()`.

**`register`/`unregister`/`on`/`once`** (events.ts:246-318):
```ts
register(label, hooks, callback, options) {
  const method = options.prepend ? 'unshift' : 'push'
  return this.ctx.fiber.effect(() => {
    hooks[method]({ ctx: this.ctx, callback, ...options })
    return () => this.unregister(hooks, callback)
  }, label)
}
on(name, listener, options?) {
  if (typeof options !== 'object') options = { prepend: options }
  this.ctx.fiber.assertActive()
  listener = this.ctx.reflect.bind(listener)          // wrap so `this`/args trace back to registering ctx
  const result = this.bail(this.ctx, 'internal/listener', name, listener, options)  // interception point
  if (result) return result
  const hooks = this._hooks[name] ||= []
  return this.register(`ctx.on(${...})`, hooks, listener, options)
}
once(name, listener, options?) {
  const dispose = this.on(name, function (...args) { dispose(); return listener.apply(this, args) }, options)
  return dispose
}
```
Every listener registration is wrapped as a **fiber effect** (§4) — the listener is unregistered automatically when the owning fiber tears down; `on()` returns the effect's disposer directly. `once()` composes on top of `on()` by wrapping the listener to self-dispose on first invocation, still registered as one effect. Listener callbacks are wrapped via `ctx.reflect.bind()` (a `Proxy` with `apply`/`construct` traps that re-traces `this`/args to the registering context — see §7) so a listener's internal `ctx.foo` calls resolve against the context that *registered* the listener, not whatever `thisArg` a particular dispatch happened to pass.

`internal/listener` itself is a **bail-mode extension point** run before actual registration — any listener on `internal/listener` that returns a truthy (bailed) value *replaces* the normal registration outcome (used above to redirect `internal/update` registrations into per-fiber storage instead of the global table).

---

## 4. Effect/disposer lifecycle and teardown ordering

`Fiber.effect(execute, label)` (fiber.ts:415-561) is the single primitive underlying **every** disposable resource in Cordis (service registration, event listeners, accessors, mixins, `ctx.plugin()` itself, arbitrary user cleanup). Accepted `execute` return shapes (`Effect<T>`, fiber.ts:83-93):
- a single `Disposable` (`() => T`)
- a `Promise<Disposable>`
- a sync `Iterable<Disposable>` (generator) — each yielded disposer is collected as it's produced
- an `AsyncIterable<Disposable>` (async generator) — same, awaited

`_execute()` (fiber.ts:356-400) dispatches on the shape returned by `runner.execute.call(this)`: function → collect directly; nullish → no-op; has `.then` → `effect.then(safeCollect)`; has `Symbol.iterator` → drain the sync iterator eagerly, collecting each yielded disposer, recording `info.error = new Error()` for stack composition; has `Symbol.asyncIterator` → an async IIFE that awaits `Promise.resolve()` first ("force async stack trace"), then loops `await iter.next()`, bailing early if `runner.epoch !== oldEpoch` (the effect's fiber already moved on — stale generator, stop draining); anything else → `TypeError('Invalid effect')`.

**Registration order matters for reentrancy** (fiber.ts:520, comment at 517-519): the wrapper disposer is pushed onto `this._disposables` **before** `execute()` runs, specifically so a reentrant owner-unload triggered *from inside* `execute()` (e.g. a plugin's setup body disposes its own parent) can already see and await this effect's wrapper.

**Disposal ordering — LIFO within one effect's own nested disposables, LIFO across a fiber's top-level effects:**
```ts
const dispose = () => {
  if (disposing) return disposalTask
  disposing = true
  let task
  for (const disposable of disposables.splice(0).reverse()) {   // reverse = LIFO
    if (task) task = task.then(() => runDisposable(disposable))
    else { const result = runDisposable(disposable); if (thenable) task = result }
  }
  return disposalTask = task
}
```
and the fiber-level `_unload()` (fiber.ts:675-696):
```ts
private async _unload() {
  await Promise.all(this._disposables.clear().map(async (dispose) => {
    try { await composeError(async (info) => { await Promise.resolve(); info.error = new Error(); await runDisposable(dispose) }, this._runner.getOuterStack) }
    catch (reason) { this.ctx.logger.error(reason) }
  }))
  this.store = undefined
  this._updateState(() => { ... re-check epoch, possibly immediately _reload() again ... })
}
```
Fiber-level teardown runs **all top-level disposables concurrently** (`Promise.all`, not sequential!) with **per-disposable error containment** (`try/catch` inside the `.map`, logged via `ctx.logger.error`, never rethrown to a sibling) — one broken teardown does not stop or corrupt the others. *Within* a single `effect()` call's own nested disposers (collected via `runner.collect`), teardown is strictly LIFO and sequential (chained `.then`).

**Single-shot disposer guarantee + reentrant-join** (fiber.ts:427-442, 504-560): a local `disposing` flag makes the returned disposer idempotent (`if (disposing) return disposalTask`). The public `wrapper` (what `ctx.on()`/`ctx.provide()`/etc actually return to plugin code) additionally tracks `executing`/`setupFailed`/`inFlight`/`setupBarrier` so that:
- calling the disposer **while setup is still running** (`executing === true`) doesn't tear down half-constructed state; it waits for setup via `waitForSetup()` then disposes.
- a **synchronous setup failure** rejects `setupBarrier`, runs `dispose()` to roll back whatever partial disposables were already collected, and rethrows to the caller — `effect()` never returns a wrapper for a failed setup.
- `effectInertia` (a `WeakMap<Disposable, () => Promise<void>|void>`, fiber.ts:112) lets an **already-running async cleanup remain discoverable**: `runDisposable(dispose)` (fiber.ts:114-117) checks this map after calling the disposer, so a second/reentrant caller that finds the wrapper already disposing joins the same in-flight promise (`inFlight`) instead of double-disposing.
- `wrapper.then` is defined (fiber.ts:555-559) so the disposer itself is **awaitable as a promise of "did the effect finish loading"** — `await ctx.on(...)` resolves to the disposal function once the effect's own setup task settles.

**`getEffects()`** (fiber.ts:568-572) — walks live `_disposables`, reading each wrapper's `[symbols.effect]` metadata (an `EffectMeta { label, children }` tree, attached to disposers via `defineProperty(wrapper, symbols.effect, meta)` and populated by nested `effect()` calls registering themselves as `meta.children` — see `collect:` in the outer runner, fiber.ts:448-454) — this is what backs runtime introspection/debugging of "what does this plugin currently hold."

**Effect creation is rejected while `UNLOADING`** (fiber.ts:419-422): `if (this.state === FiberState.UNLOADING) throw new CordisError('INACTIVE_EFFECT')` — prevents new registrations from escaping an unload snapshot mid-teardown (called out explicitly as a local hardening in `vendor/README.md` modification #6, along with several other reentrancy fixes the harness applied on top of upstream — see §9).

**`ctx.plugin()` disposal itself is implemented as an effect** (fiber.ts:265-297) — a child fiber's very existence is one effect on its parent: setup pushes the child into `runtime.fibers`, teardown clears `uid`, fires `internal/plugin` (§below), removes the fiber from `runtime.fibers`, deletes the `Runtime` record if it was the last fiber, resets the fiber's own epoch to `INACTIVE`, and — if not already unloading — kicks off the fiber's *own* `_unload()` and awaits it. This is how disposing a parent context cascades: parent unload → parent's `_disposables` include each child's `dispose` wrapper (LIFO) → each child's disposal chain recurses the same way.

`emitPluginDisposed` (fiber.ts:120-137) dispatches `internal/plugin` **with per-callback error containment**, deliberately not using the normal `events.emit()` path (which has no such containment) — "notify plugin teardown without allowing one observer to break ownership cleanup."

---

## 5. `Service[Service.init]` — async-generator startup hook

Seen concretely in `vendor/hmr/src/index.ts:199` — `async* [Service.init]() { yield async () => { ...teardown... }; ...setup work...; }`. This is the class-plugin equivalent of a function-plugin's `effect`-shaped return: since `execute()` (fiber.ts:250-257) calls `instance?.[symbols.init]?.()` after constructing a class plugin, and an async-generator method invoked this way returns an `AsyncIterable`, it flows through the exact same `_execute()` iterable-draining branch as any other effect (§4) — the *first* `yield` is conventionally the teardown disposer (registered before any setup work that could throw, so a failure mid-setup still tears down whatever the first yield established), and subsequent code before further yields is the async setup body.

---

## 6. Fiber lifecycle states and the epoch/dependency-driven reload machine

`FiberState` enum (fiber.ts:147-154): `PENDING, LOADING, ACTIVE, FAILED, DISPOSED, UNLOADING`.

Each fiber tracks its own **epoch** — a string built from every injected service's providing-fiber uid (`_refresh()`, fiber.ts:611-623):
```ts
_refresh() {
  let epoch = ''
  for (const name of Object.keys(this.inject)) {
    const impl = this._store[name]
    if (!impl) { epoch = INACTIVE; break }
    epoch += ':' + impl.fiber.uid
  }
  this._setEpoch(epoch)
}
```
`INACTIVE = '__INACTIVE__'` is the sentinel meaning "at least one required dependency is currently missing." `_setEpoch` (fiber.ts:625-639) only reacts on an actual epoch *change*: transitioning **into** `INACTIVE` from a real epoch triggers `_unload()`; transitioning **out of** `INACTIVE` triggers `_reload()`; changing between two *different* real epochs (a dependency's providing fiber was swapped) also triggers `_unload()` — the ensuing `_unload()` re-checks the epoch at its end and calls `_reload()` again if it's no longer `INACTIVE` (fiber.ts:688-695), so a same-fiber dependency swap manifests as unload-then-reload, never a live in-place patch.

`_reload()` (fiber.ts:646-673): snapshots `this.store = {...this._store}`, `await Promise.resolve()` (a microtask checkpoint — allows a disposer queued in the interim to invalidate the load before plugin code runs), re-checks the epoch hasn't changed since (stale-epoch guard), resolves config via the `internal/config` waterfall + standard-schema validation (`_resolveConfig`, fiber.ts:641-644), executes the plugin body, catches and stores any thrown error into `this._error` + logs it + forces epoch back to `INACTIVE` (so a failed load doesn't masquerade as loaded), then `_updateState` decides whether to settle or (if epoch changed again during execution) immediately unload.

`_updateState` (fiber.ts:581-595) computes/sets `this.state`, emits `internal/status(fiber, oldState)` on change, and — only on transitions crossing the `ACTIVE` boundary in either direction — re-notifies every service *this* fiber itself provides (so the fiber's own dependents re-check availability when it goes active/inactive).

`await()` (fiber.ts:704-710): spins on `while (this.inertia) await this.inertia`, then rethrows `this._error` if set. `restart()` (fiber.ts:718-723): force `_setEpoch(INACTIVE)` then `_refresh()` (unload+immediately-reload) then await. `update(config, noSave)` (fiber.ts:736-753): assigns new raw config; if not currently `ACTIVE`, defers resolution (services may not be available yet); if `ACTIVE`, resolves config and runs it through the `internal/update` waterfall (§3) whose terminal action assigns `this.config` and calls `restart()`.

---

## 7. TypeScript/JS language features the design leans on (Python-porting difficulty)

| # | Feature | Where used | What it buys Cordis | Python translation & difficulty |
|---|---|---|---|---|
| 1 | **`Proxy` with `get`/`set`/`has`/`apply`/`construct` traps** | `ReflectService.handler` (reflect.ts:135-206) — the entire `ctx.<key>` resolution; `withProps`/`createTraceable`/`createCallable`/`createShadowMethod` (utils.ts:117-233) — context-tracing on every service method call; `ctx.reflect.bind()` re-tracing listener callbacks | Transparent computed-property + dynamic-dispatch container; lets `ctx.foo` look identical whether `foo` is a plain field, a declared accessor, or a resolved service, and lets a returned method silently rebind to the calling context. | **Hard.** Python's closest analogue is `__getattr__`/`__getattribute__`/`__setattr__` on a class — this covers the `get`/`set`/`has` traps reasonably (a custom `Context.__getattr__` doing the isolation-scope walk) but Python has **no `apply`/`construct` trap equivalent** — there is no way to intercept "this object was called as a function" or "this object was used with a different `this`" the way JS `Proxy.apply` does. The "traceable" re-binding of method calls to a different `ctx` (so `service.method()` sees the *caller's* context even though the service instance is shared) has no direct Python equivalent; likely needs an explicit wrapper/descriptor-based re-binding (e.g. custom descriptors returning bound partials) rather than a transparent proxy — expect real design divergence, not a 1:1 port. |
| 2 | **Constructor return-value override** (`return self` from a `class`'s `constructor`, where `self` may be a *different* object) | `Context` constructor returns the Proxy instead of `this` (context.ts:83); `Service` constructor conditionally returns a *callable* object instead of `this` (service.ts:58) | Lets `new Context()` silently produce a proxy, and `new SomeService(ctx)` silently produce a function-shaped object when the service defines `[Service.invoke]`. | **Hard / needs a different pattern.** Python constructors (`__init__`) cannot change what `type()` returns; only `__new__` can, and even then the result must already be an instance of the class (or subclass) being constructed — you cannot make `__new__` return a plain function. The callable-service pattern (`ctx.logger('name')`) is portable via `__call__` on the service class itself (Python's native callable-object protocol) — likely a **cleaner** fit than JS's trick, but requires abandoning the "class returns a different runtime shape" mechanism entirely and redesigning around `__call__`. |
| 3 | **Declaration merging on `interface Context`** (`declare module './context.ts' { interface Context { ... } }`) | Used pervasively: `events.ts`, `reflect.ts`, `fiber.ts`, `registry.ts` each *reopen* the `Context` interface to add typed members (`ctx.on`, `ctx.get`, `ctx.fiber`, `ctx.plugin`, etc.); every downstream plugin (e.g. `hmr/src/index.ts:15-31`, `attachment/src/index.ts:24-28`, `code-runtime/src/index.ts:89-93`) does the same to register `ctx.<serviceName>: MyService` and `Events['my/event']` as compile-time-checked additions | Gives every plugin **fully typed** `ctx.foo` access and typed event payloads across separately-compiled packages, purely through TS's structural interface-merging — with **zero runtime code**. This is the mechanism the task explicitly flags as "typed events." | **Not portable at all — must be replaced with a different mechanism.** Python has no structural interface-merging; there is no way to "reopen" a `Protocol`/class across modules and have a type checker merge the fields. Nearest analogues: (a) a single hand-maintained `TypedDict`/`Protocol` registry updated by every plugin (defeats decentralization), (b) `typing.Protocol` + `runtime_checkable` plus **untyped** `getattr`-based access with a companion `.pyi` stub per plugin that mypy/pyright can merge via `# type: ignore` + `cast`, or (c) give up compile-time typed `ctx.<key>` entirely and rely on runtime checks / a service-registry with `TypeVar`-parameterized `get(name: str) -> T` calls where `T` is supplied at each call site. This is the single biggest architectural gap between the TS design and a Python port — plan for it explicitly rather than trying to "translate" it. |
| 4 | **Structural typing** (interfaces satisfied by shape, not declared inheritance) — e.g. `Plugin.Object<T> { apply(ctx, config): any }`, any object with an `.apply` method qualifies | `isApplicable()` (registry.ts:8-10) checks `typeof object.apply === 'function'`, not `instanceof` | Lets ordinary objects/modules act as plugins without extending a base class. | **Moderate.** Python's duck typing already permits this at runtime (`hasattr(plugin, 'apply')`); the loss is purely at the *type-checking* layer — `typing.Protocol` recovers static structural typing reasonably well for this specific case (single-method protocols are Protocol's best use case), so this is one of the more portable features. |
| 5 | **`unique symbol` static members as private/collision-proof API surface** (`Context.effect`, `Context.filter`, `Service.init`, `Service.check`, `Service.invoke`, etc., all backed by `Symbol.for(...)` — i.e. **global, cross-realm registry symbols**, not module-local `Symbol()`) | `symbols` object in `utils.ts:50-73`; used as dict keys throughout (`ctx[symbols.isolate]`, `instance[symbols.init]`, `dispose[symbols.effect]`) | Namespaced, un-enumerable-by-default, collision-free keys that also work "across multiple copies of cordis" (comment in `Context.is`, context.ts:53-56) — important because the harness vendors + rescopes the package, so two different `cordis` npm packages could coexist, and `Symbol.for()` (global registry) keys still interoperate. | **Easy-moderate.** Python has no exact `Symbol` equivalent, but a small `sentinel` object (or `object()` instances stored in a shared module, or string keys with a private-name convention like `__cordis_effect__`) covers the "collision-proof internal key" need. The **cross-package-identity** property (`Symbol.for` global registry matching across independently-installed copies) is the subtler part to replicate — Python's `id()`-based object identity doesn't give you that "same logical symbol, different import" property for free; would need to standardize on plain string keys (which *do* naturally match across packages) instead, trading collision-safety for portability — a deliberate design decision, not a mechanical translation. |
| 6 | **TC39 Stage-3 (native) decorators with `ClassDecoratorContext`/`ClassMethodDecoratorContext` and `decorator.addInitializer`** | `@Inject()` (registry.ts:32-60) | Declarative dependency declaration on classes and deferred-until-ready method wrapping. | **Easy.** Python decorators are a mature, first-class language feature (`@Inject(...)` on a class or method is idiomatic Python) — this is one of the *most* directly portable features; the main nuance is that Python method decorators wrap the function before class-body execution, so the "class inherits static inject dict with prototype-chain walking" trick (`symbols.checkProto`, registry.ts:40-43) needs a different inheritance mechanism (e.g. `__init_subclass__` merging a class attribute dict), but no fundamentally new capability is required. |
| 7 | **Generators / async generators as effect bodies** (`function* () { yield disposer }`, `async function* () { yield disposer; ...await setup... }`) | `ReflectService.mixin()` (reflect.ts:366), `Hmr[Service.init]` (hmr/src/index.ts:199), the `_execute()` iterable-draining logic (fiber.ts:375-395) | Lets an effect register several nested sub-effects incrementally, and lets class-plugin setup interleave teardown-registration before/between awaited setup steps. | **Easy.** Python generators (`yield`) and async generators (`async def ... yield`) are directly equivalent; `_execute()`'s manual `iter.next()` draining loop translates near-verbatim to Python's iterator protocol (`__next__`/`__anext__`). |
| 8 | **`WeakMap`/`WeakSet`-keyed side tables** (`effectInertia = new WeakMap<Disposable, ...>()`, fiber.ts:112; `DisposableList`'s internal `weak = new WeakMap<T, number>()`, utils.ts:7) | Reentrant-cleanup tracking without leaking references; O(1) delete-by-value for disposer lists | Lets the framework attach metadata to a disposer function / track it for removal without preventing GC and without the disposer needing to know its own list membership. | **Easy.** Python's `weakref.WeakKeyDictionary` is a direct equivalent, with the caveat that Python functions/closures are weak-referenceable like JS ones, so no additional wrapping is needed. |
| 9 | **Explicit prototype-chain manipulation** (`Object.create`, `Object.getPrototypeOf`, `Object.setPrototypeOf`, `Reflect.getOwnPropertyDescriptor`/`defineProperty` used as the *mechanism* for context extension, isolate/intercept-map inheritance, and `joinPrototype` merging a Service instance's prototype with `Function.prototype`) | `Context.extend/isolate/intercept` (context.ts:99-145); `Service[symbols.resolveConfig]`'s intercept-chain walk (service.ts:87-94) walking `Object.getPrototypeOf` levels to reconstruct "which ancestor added this key" via `Object.hasOwn`; `joinPrototype` (utils.ts:92-99) | Cordis deliberately uses **live prototype chains as its "immutable persistent map" data structure** — an ancestor's isolate/intercept map is never copied, only extended, and "does this level own the key" (`Object.hasOwn`) distinguishes an override from an inherited default. | **Moderate.** Python has no first-class mutable prototype-chain primitive equivalent to `Object.create`/`Object.getPrototypeOf` chains used *as a runtime map data structure* (Python classes have MRO, but instances don't chain like this). The nearest port is `collections.ChainMap` (which supports exactly "layered dict lookup with own-vs-inherited distinction" via `.maps[0]` vs the rest) or a hand-rolled linked-parent dict wrapper — functionally equivalent, just not "free" the way JS prototypes make it. `joinPrototype`'s merging of two unrelated prototype chains (a Service instance's chain + `Function.prototype`) has no Python analogue at all because Python doesn't separate "callable" as a prototype trait — again pushes toward using `__call__` instead (see #2). |
| 10 | **Module-level side-effecting `declare module` type augmentation combined with real runtime `Symbol.for()` global registration** (`Context.is` static method doubles as a brand check via `Symbol.toPrimitive`, context.ts:65-68: `Context.is[Symbol.toPrimitive] = () => Symbol.for('cordis.is')`) | Cross-realm/cross-copy "is this a Context" checks that don't rely on `instanceof` | Version- and copy-independent identity checks. | **Easy-moderate** as a runtime mechanism (any sentinel-attribute check works: `getattr(obj, '_is_cordis_context', False)`), but the *type-level* half (branding a TS type via a callable's coercion) has no meaning in Python's runtime type system — purely a runtime-check port, dropping the compile-time narrowing benefit (again see #3, mypy/pyright narrowing would need `TypeGuard`/`TypeIs` functions instead, which Python does support natively via `typing.TypeGuard`). |

**Overall assessment for the QMA port:** the *state-machine* half of Cordis (fiber epochs, effect/disposer trees, LIFO-per-effect + concurrent-per-fiber teardown, waterfall/bail/serial/parallel dispatch, isolation-as-symbol-keyed-dict) is straightforward, well-specified imperative logic with no TypeScript-specific dependency — it ports to Python essentially as designed, using `asyncio` for the async paths and plain dict/list structures for `_hooks`/`store`/`props`. The *ergonomics* half — the transparent `ctx.<key>` proxy (#1), the constructor-return trick for context/callable-service identity (#2), and especially **declaration merging for typed `ctx`/`Events` augmentation across independently-authored plugins (#3)** — has no faithful Python equivalent and needs a deliberately different design (most likely: an explicit typed service-registry object plus `Protocol`/`TypedDict` stubs maintained per-plugin, sacrificing the "any plugin can silently widen `ctx`'s type" property that TS gives Cordis for free). Recommend treating #1 and #3 as the two design decisions to make explicitly and early, rather than as implementation details to fill in later.

---

## 8. Loader entry format

`EntryOptions` (`vendor/loader/src/config/entry.ts:9-22`):
```ts
export interface EntryOptions {
  id: string                 // stable id inside the containing entry tree
  name: string                // module specifier imported by the entry tree
  config?: any                 // config passed to the plugin
  group?: boolean | null      // marks this entry as a nested group
  disabled?: boolean | null   // prevents this entry (and descendants) from running
  inject?: Inject | null      // required services / intercept config for this entry
}
```
This is the literal shape of one row in a Cordis YAML config (e.g. `cordis.yml`), one `Entry` object per row. `Entry.id` (entry.ts:75-81) is **hierarchical**, joined by `EntryTree.sep = ':'` when nested inside a parent entry's own fiber (`this.parent.tree.ctx.fiber.entry.id + ':' + id`). `disabled` uniquely supports a `!!js` YAML-tagged expression (`isJsExpr`/`evaluate`, entry.ts:104-112) evaluated against the loader context at every mount decision — every other option field is a static value written straight from config.

An `Entry`'s lifecycle (`init`/`_init`/`_start`, entry.ts:259-303): resolve `options.name` to a module via `this.parent.tree.import(...)`, unwrap its default export (`loader.unwrapExports`), patch the entry's `ctx` prototype onto its parent (`_patchContext`, entry.ts:114-122 — `Object.setPrototypeOf(this.ctx, this.parent.ctx)`, i.e. **live reparenting** of the JS prototype chain, not a copy, so a moved/edited entry's context immediately sees its new ancestor chain), then `this.ctx.registry.plugin(plugin, options.config, outerStack)` to actually start the fiber, tracked as `this.fiber`.

`Entry.update()` (entry.ts:142-246) is the transactional apply path invoked on config edits — diffs old vs. candidate options (`deepEqual` field-by-field), and picks one of four strategies depending on what changed: (a) no previous fiber → straight `init()`; (b) newly disabled → dispose and persist; (c) only `config` (or `group`) changed and not `name`/`inject`/`group` → **in-place patch via `fiber.update()`** without reimporting/restarting the plugin module; (d) `name`/`inject`/`group` changed → full replace: import the new plugin, dispose the old fiber, start a new one, with an explicit **rollback path** (`try { start(plugin) } catch { options = previousOptions; start(previousPlugin) ... throw updateError('apply', ...) }`) that restores the previous plugin if the new one fails to start — this transactional reconciliation is called out as harness-local hardening in `vendor/README.md` modification #8.

---

## 9. HMR mechanics (`vendor/hmr/src/index.ts`, `@cordisjs/plugin-hmr@1.0.15`, deepseek-harness fork)

`Hmr extends Service` (`static inject = ['loader', 'timer']`), requires `ctx.loader.internal` (a Node `ModuleLoader` hook only present when the process was started with `--expose-internals`).

**Two independent watch mechanisms:**
1. **Main file watcher** (`[Service.init]`, lines 199-295) — a `chokidar` watcher over `config.root` globs, `ignoreInitial: true` (deliberately, to avoid re-announcing files boot already consumed — vendor/README.md mod #12). On `add`/`change`/`unlink`:
   - First checks whether the changed path matches a live `Include` subtree's config file (`entry.subtree as Include`) → routes to `refreshConfig` (config-reload path, not module-reload).
   - Else, if the changed file's URL is in `this.externals` (the CLI worker entry point's own static dependency tree, precomputed via `loadDependencies` walking `ModuleJob.linked`) → **full process reload** via `loader.exit()`.
   - Else, if the URL is in Node's ESM `loadCache` → **partial reload**: added to a `stashed` set and a **debounced** (`ctx.debounce(..., config.debounce)`) `partialReload()` is scheduled.
   - Else → just emits `hmr/change` (informational, e.g. for non-module static assets).
2. **Per-config exact-path watcher** (`registerConfig(filename, refresh)`, lines 134-187) — for watching one exact config file (outside the module roots, `ignoreInitial: false` since a user patch layer present at registration must apply once), with realpath-based canonicalization (`findWatchRoot`, lines 64-84) to survive Windows short-name-vs-long-form path aliasing, serialized via `refreshConfig`'s dirty-flag/single-in-flight-task loop (lines 297-324) so overlapping fs events coalesce into one re-run of `refresh()` per settle.

**Partial-reload dependency analysis (`analyzeChanges`, lines 345-398)** is a classic **accept/decline propagation** over the ESM module graph, similar in spirit to Vite/webpack HMR:
- `accepted = stashed` (directly changed files) ∪ any file whose *any* dependent is accepted.
- `declined = externals` ∪ any file whose *every* dependent is declined.
- Iteratively processes a `pending` worklist (files reachable from stashed but not yet classified) until no file can be reclassified, then declines whatever's left ambiguous.

**`partialReload()` (lines 400-549)** — the actual swap:
1. Maps every configured loader entry's plugin `name` to its resolved file URL per config-tree `baseUrl`, checks each against `declined`/`loadCache`/`unwrapExports` to build a `pending: Map<ModuleJob, Plugin>`.
2. For each pending module, walks its own dependency set (`loadDependencies`, excluding already-declined) — if **none** of its dependencies are `accepted`, skip it; otherwise mark its whole dependency set accepted and record it as a `reloads` candidate (capturing `{ filename, runtime: ctx.registry.get(plugin) }`).
3. **Cache eviction with rollback capability**: for every accepted file, backs up and deletes both the ESM `loadCache` entry (`Map.prototype.delete.call(...)`, used explicitly rather than the loadCache's own `.delete()` because Node 24's `LoadCache` subclass only nulls a type-slot rather than removing the Map entry) and the CJS `require.cache` entry, keeping `esmBackup`/`cjsBackup` dicts so a failed reload can `rollback()` by restoring both caches verbatim.
4. Attempts to re-`import()` every reload candidate's file; **any import failure aborts and rolls back caches immediately**, no plugin state touched yet.
5. On successful reimport, for each `[plugin, {filename, runtime}]`: `ctx.registry.delete(plugin)` (disposes every fiber of the *old* callback), then `reload(newPlugin, runtime)` which **creates a fresh fiber per old fiber** (`oldFiber.parent.registry.plugin(newPlugin, oldFiber._config, ...)`), explicitly carrying over `fiber.entry = oldFiber.entry` and re-pointing `entry.fiber = fiber` so the Loader's `Entry` bookkeeping (§8) stays consistent across the swap. Any failure during this step triggers a **second-order rollback**: restore caches *and* re-register the *old* plugin/runtime pairs so the running system ends up exactly where it started.
6. On full success: `ctx.emit('hmr/reload', reloads)` and clears `this.stashed`.

This is the concrete mechanism behind "hot module replacement": module-graph reachability analysis + Node internal cache surgery + Cordis fiber replace-in-place (dispose old fiber(s), construct new fiber(s) under the same `Runtime`/`Entry`, all-or-nothing via manual two-tier rollback). None of this depends on TypeScript language features — it is pure Node.js module-system introspection (`internal.loadCache`, `internal.resolve`/`resolveSync` version-branching for Node 22 vs 24 API differences) plus the Cordis `Fiber`/`Runtime`/`Entry` primitives already covered above. A Python port has **no equivalent to hot-swap live in-process module code** the way Node's ESM loader internals allow — CPython's `importlib.reload()` exists but doesn't give the same fine-grained per-object cache-and-rollback control (`sys.modules` entries can be swapped/restored similarly, but reloading a module reruns *all* its top-level code and does not automatically re-target existing object references the way Node's `loadCache` swap keeps object identity stable elsewhere in the graph) — this subsystem is the one most likely to need a fundamentally different design in Python rather than a port (e.g. process-supervisor-level restart instead of true in-process HMR, or restricting "hot" reload to explicitly reloadable plugin modules with their own supervised namespace).

---

## 10. Vendoring/sync process (`vendor/README.md`, harness-side)

- Packages copied by `src/` (not npm-installed), renamed to the `@deepseek-ai` npm scope, directory names/version numbers left as upstream snapshot markers; `pnpm-workspace.yaml#linkWorkspacePackages` resolves the preserved semver ranges to the pinned local workspaces; a `verify-vendored-links` hygiene gate asserts no registry copy sneaks in alongside.
- Manifest table records `Directory | npm name | Upstream name | Version | Upstream repo | Commit` per package — `cordis` pinned to `4.0.0-rc.7` @ `56b3d4f7...` from `cordiverse/cordis` (`packages/core`); `loader` from the same commit/repo (`packages/loader`); `include`/`group`/`timer`/`hmr`/`logger-console` from a **different** repo (`deepseek-harness/cordis`, a fork, commit `abb0a307...`) — i.e. the harness forked Cordis's plugin packages but kept core itself unforked upstream.
- An 18-item **exhaustive local-modification log** (§ excerpted throughout this doc) is the harness's own patch set on top of vendored upstream: notably #6 (fiber.ts reentrant-disposal hardening — effect-ordering, UNLOADING-state effect rejection, per-observer teardown error containment), #8 (transactional Loader/Include reconciliation with rollback), #9 (exact-config-path HMR watching with Windows short-name-safe realpath), #12 (serialized per-Include mutation queue to avoid a specific deadlock between Include rollback and HMR teardown drain), #15 (lazy raw-config resolution ported from upstream PR `cordiverse/cordis#41`, deferring `!!js` expression evaluation until a fiber's injections are active).
- Sync procedure (README lines 148-156): note upstream commit hash in an upstream workspace checkout, copy `src/` (+`bin.js`/README/LICENSE) over the vendored dir, **re-apply every local modification from the log by hand** (or drop an entry if upstream now makes it moot — log updated either way), bump the manifest table, then `pnpm install && pnpm run test && pnpm run build`. This is a manual, log-driven, non-automated rebase process — there is no tool re-diffing upstream automatically.

---

## Digest (10 lines)

1. Cordis's `Context` is literally a `Proxy(this, ReflectService.handler)` returned from its own constructor; every `ctx.<key>` read either hits an own property, a declared accessor, or triggers a fiber-parent-chain walk through `reflect.store` keyed by isolation-label symbols — Python needs `__getattr__`/`__setattr__` for this, no `apply`/`construct`-trap equivalent exists.
2. Plugins are functions, classes, or `{apply}` objects, keyed by callback identity in `RegistryService._internal: Map<Function, Runtime>`; `Fiber.execute()` picks `new Ctor(ctx,cfg)` vs `fn(ctx,cfg)` via `isConstructor()`; `Service` self-registers via `ctx.reflect.provide()` inside its own constructor, wrapped as a fiber effect.
3. `ctx.effect()` is the one disposal primitive underlying services/listeners/plugins alike: nested disposers run LIFO-sequential within one effect, but a fiber's top-level effects tear down **concurrently** (`Promise.all`) with per-disposable error containment — a subtlety worth replicating exactly, not approximating.
4. Event dispatch has 4 public modes (`emit`/`parallel`/`serial`/`bail`) built on shared `dispatch()` resolution plus a 5th (`waterfall`, onion-composed around a terminal `next`); `isBailed()` treats only `null`/`false`/`undefined` as non-bail, an exact-semantics detail.
5. Fiber lifecycle is epoch-string-driven: `PENDING→LOADING→ACTIVE↔FAILED`, `UNLOADING→DISPOSED`; a dependency-availability string built from providing-fiber uids drives automatic unload/reload, entirely dict/loop logic with no TS dependency — this half ports cleanly to Python/asyncio.
6. The loader entry format is `{id, name, config?, group?, disabled?, inject?}` with hierarchical `:`-joined ids and a transactional `Entry.update()` that rolls back to the previous plugin on apply failure — read from `vendor/loader/src/config/entry.ts`.
7. HMR (`vendor/hmr/src/index.ts`) does accept/decline dependency-graph propagation over Node's ESM `loadCache`, evicts+backs-up both ESM and CJS module caches, re-imports, and swaps fibers in place with two-tier rollback on failure — this has no faithful Python equivalent (no live in-process hot module swap primitive); expect a different design (process restart or a supervised reload namespace).
8. The single biggest Python-porting gap is TypeScript **declaration merging** (`declare module './context.ts' { interface Context {...} }`), used by every plugin to typed-augment `ctx` and `Events` with zero runtime code — Python has no structural interface-merging; plan an explicit typed-registry/Protocol-stub replacement rather than attempting a mechanical translation.
9. Two other JS-only tricks worth flagging early: constructor return-value override (`Context`/`Service` constructors return a different object than `this`, e.g. a callable) — Python should use `__call__` instead; and prototype-chain-as-persistent-map (`Context.extend/isolate/intercept` via `Object.create`) — Python should use `ChainMap` or a hand-rolled linked-dict wrapper.
10. Every vendored file inside `deepseek-harness/vendor/` carries an 18-entry exhaustive local-modification log on top of pinned upstream commits (cordis core unforked from `cordiverse/cordis`; loader plugins forked at `deepseek-harness/cordis`), manually re-applied on each sync — QMA's own kernel work should expect the same "own the framework layer" posture rather than depending on an external Cordis-equivalent package.
