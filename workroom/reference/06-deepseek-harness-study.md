# 06 — DeepSeek Harness Study: how a system lets agents extend it themselves

**For:** Mubarak, and every future Claude session that touches QMF extensibility · **Written:** 2026-08-18 · **Status:** study — mechanics and mental models only, no design ratified
**Operator ruling this document serves:** *"QMX must be FULLY EXTENSIBLE — agents extend the system themselves. Want to experiment with ML → extend and do it. Anything else → same. The way quants experiment with Python."*
**Why this source:** the DeepSeek Harness is the operator's chosen reference for **HOW extension works** — not for what to build. We are building something different (QMF, a Python quant framework, plus applications on it).

**Source:** `https://deepseek-harness.github.io/deepseek-harness/` — the docs are bilingual; the Chinese side is the default path and the English mirror lives under `/en/`. Every citation below uses the English URL.
**Rule this document obeys:** extract **mechanics and mental models**. Never the code — it is TypeScript and we write 100% our own Python. Never the chat-agent machinery — turns, prompts, transcripts and compaction are not a quant framework.
**What is authority:** nothing here. This is evidence for a future design session, exactly like `reference/00–05`.

---

## In plain words

1. The DeepSeek Harness is a coding-assistant program, but it is really a **chassis**. Almost nothing is built into it; what it can do is **assembled at start-up from parts**.
2. Every capability is a part of the same kind: the thing that talks to the AI model, the thing that runs shell commands, the file reader — and even the main loop that drives the whole conversation. *"Every part of the product is a plugin, including the model adapter, the tool registry, the session log, and the agent loop itself."*
3. There is therefore **no privileged centre to patch**. In their words: *"There is no privileged core to patch: you extend dsh by mounting a plugin beside the others."*
4. A part is, at its smallest, **one function**. The system hands it a single object, and the part hangs its offerings on that object.
5. Parts find each other **by name, never by importing each other**. One part says "I provide the toolbox"; another says "I need the toolbox"; the system does the matchmaking and starts them in the right order.
6. Because they only know names, **any part can be swapped for another answering the same name**. Change where files come from, and every feature that touches files moves with it — without editing any of those features.
7. Everything a part registers is **undoable by construction**. Registering hands back an "undo". Remove the part and every trace of it disappears on its own — no cleanup code to remember, none to forget.
8. That single property is what makes **live editing** possible: save a file, the old part is unloaded (undoing everything it did), the new code loads, and the system keeps running. Hot reload is not a feature they built; it is a **consequence** of the undo rule.
9. Parts talk to each other through **named messages**, and there are exactly four ways to send one: shout it and move on; run every listener at once; run them in order until one answers; or **wrap them around each other like nested envelopes**.
10. That last shape — the wrapper chain — is how a permission check works. Each wrapper may pass the request further in, change it on the way, or **refuse and stop it dead**. Refusal is simply "don't pass it on".
11. What the program *is* on a given machine is an **ordered list in a config file**. Install a part and a line is added to the list. Delete the line and the feature is gone. You can print the exact list the machine will boot before booting it.
12. So **"agents extend it themselves" means, mechanically:** an agent writes one file containing one function, adds one line to a list, and that capability is now part of the running system — reachable by every other part, and removable without residue, because everything it did was reversible from the first line.

---

## The extension mechanics

> Everything in this section is diagrammable. Sub-sections are ordered so they can be drawn in sequence: shape → container → lifecycle → messages → undo → composition.

### 2.1 The five concepts (the whole model on one page)

From the [Cordis primer](https://deepseek-harness.github.io/deepseek-harness/en/reference/cordis-primer), the framework underneath the harness is exactly five ideas:

| # | Concept | What it means |
|---|---|---|
| 1 | **A plugin is an object implementing a Service** | a function with optional `inject` and `apply(ctx)`, or a `Service` subclass |
| 2 | **A context is a container of services** | one service occupies one stable `ctx.<key>`; others look it up **by key, not by import** |
| 3 | **`inject` declares service dependencies** | a plugin waits until its services exist; **load order is expressed as dependency, never hand-sequenced** |
| 4 | **Typed events are the communication** | registered event names, dispatched in one of four modes |
| 5 | **Registration is a reversible side effect** | prompts, schemas, adapters, providers, listeners all install via `ctx.effect()` / `ctx.on()` and **unwind on reload and teardown** |

Keep #5 in view: it is the load-bearing one. Points 1–4 are ordinary dependency injection; point 5 is what makes the whole thing safe to take apart.

### 2.2 The plugin shape — three forms, one contract

*Source: [Your first plugin](https://deepseek-harness.github.io/deepseek-harness/en/develop/basic/), [Registry](https://deepseek-harness.github.io/deepseek-harness/en/reference/cordis-api/registry).*

```
            ┌──────────────────────────────────────────┐
  FUNCTION  │  name?      "greet-tool"                 │
  OBJECT    │  inject?    ['tools', 'llm']   ← needs   │
  CLASS     │  provide?   'metrics'          ← offers  │
            │  Config?    a schema           ← settings│
            │  apply(ctx, config)            ← the body│
            └──────────────────────────────────────────┘
```

Three accepted entrypoint shapes, all carrying the same metadata (`name`, `Config`, `inject`, `provide`, `intercept`):

- **Function** — `export function apply(ctx) {}`. Sufficient in most cases.
- **Object** — `{ name, inject, apply(ctx) {} }`.
- **Class** — extends `Service`, `super(ctx, 'metrics')` registers itself as `ctx.metrics`. *"Use class form when the plugin provides a service to other plugins."*

The contract is one sentence: **the framework calls `apply` and passes a context; the plugin registers capabilities on it.** Their own words: *"That is the complete configuration."*

### 2.3 The context is the service container

*Source: [Context](https://deepseek-harness.github.io/deepseek-harness/en/reference/cordis-api/context), [Services and dependencies](https://deepseek-harness.github.io/deepseek-harness/en/develop/framework/service).*

`ctx` is the only object a plugin needs. Services live at stable keys — `ctx.tools`, `ctx.llm`, `ctx.sessions`, `ctx.fs`, `ctx.shell`. The operations that matter:

| Operation | What it does | Why it matters |
|---|---|---|
| `ctx.provide(name, value)` | register a service owned by this plugin | **returns a disposer**; unregisters on unload, waking dependents |
| `ctx.get(name)` | read a service *without* declaring a dependency | the "optional dependency" escape hatch |
| `ctx.extend(meta)` | child context with extra metadata | parent is never mutated |
| `ctx.isolate(name, label?)` | child context with **its own instance** of one named service | *"a different implementation can be provided without affecting the parent scope"* |
| `ctx.intercept(name, config)` | child context supplying per-service config to everything below it | scoped settings without globals |
| `ctx.plugin(child)` | mount a child plugin | child has its own lifecycle and unloads with its parent |

The contexts form a **tree**, and `isolate` is the mechanism that lets two groups in one process each see a differently configured provider of the same name — their example gives group A a 5-second shell and group B a 60-second shell, *"with no cross-group effect."*

### 2.4 The lifecycle — one state machine, memorised once

*Source: [Plugins and lifecycle](https://deepseek-harness.github.io/deepseek-harness/en/develop/framework/), [Fiber](https://deepseek-harness.github.io/deepseek-harness/en/reference/cordis-api/fiber).*

Every loaded plugin instance is a **fiber** — "one loaded plugin instance: its lifecycle state, validated config, and registered effects".

```
   PENDING ──▶ LOADING ──▶ ACTIVE ──▶ UNLOADING ──▶ DISPOSED
                   │
                   └──▶ FAILED
```

| State | Meaning |
|---|---|
| PENDING | declared, but a required service is not ready |
| LOADING | dependencies ready, `apply` is running |
| ACTIVE | running |
| FAILED | `apply` or config validation threw |
| UNLOADING / DISPOSED | disposers running / fully torn down |

Two behaviours hang off this:

- **A missing dependency is not an error — it is PENDING.** The provider may be mounted later.
- **A disappearing dependency unloads you.** *"If a required service disappears, for example during provider replacement, the plugin unloads automatically (ACTIVE → DISPOSED) and loads again when the service returns."*

`fiber.dispose()` guarantees three things: every registration the plugin owns is removed, child plugins are recursively unloaded, and the returned promise resolves **after all asynchronous cleanup finishes**.

### 2.5 Typed events and the four dispatch modes

*Source: [Cordis primer § dispatch modes](https://deepseek-harness.github.io/deepseek-harness/en/reference/cordis-primer), [Events](https://deepseek-harness.github.io/deepseek-harness/en/reference/cordis-api/events), [Event system](https://deepseek-harness.github.io/deepseek-harness/en/develop/framework/events).*

Events are named `namespace/action` (`tools/pre-execute`, `agent/request`, `session/event`). **Each event has exactly one dispatch mode, and can only be dispatched by that mode** — the mode is *"part of the event's public contract"*, recorded with an `@mode` tag so the generated catalogs can cross-check declarations against dispatch call sites.

| Mode | Awaited? | Order | Returns a value? | Shape in plain words |
|---|---|---|---|---|
| `emit` | no | registration order | no | **shout it** — observers, return values ignored |
| `waterfall` | no | registration order | **yes** | **nested envelopes** — each listener wraps the rest |
| `parallel` | yes | all at once | no | **fan out** — awaits every listener together |
| `serial` | yes | registration order | **yes** | **queue** — awaits in order until one answers |

(A fifth, `bail`, appears in the API: synchronous ordered dispatch stopping at the first non-`null`/`false`/`undefined` return.)

**Waterfall is the interesting one** and deserves its own picture. It is *around*-middleware: listeners receive `(...args, next)`.

```
   dispatch ──▶ [ listener A ]──next()──▶[ listener B ]──next()──▶[ built-in default ]
                     │                        │                          │
                     │◀───── return ──────────│◀────── return ───────────│
                     ▼
                  result

   listener B does NOT call next()  ──▶  short circuit; A still wraps B's answer
```

Their rules, verbatim where it matters:

- *"Calling `next()` will execute downstream listeners; the downstream return value comes back through `next()` to the current wrapping layer, which may wrap it and continue returning outward. Not calling `next()` and returning directly short-circuits."*
- *"For single-decision events, short-circuiting is the design intent. A policy listener may return without calling `next()` when it holds the decision, while a listener that only annotates or observes must delegate."*
- `prepend: true` exists but is discouraged: *"only when a listener must run before ordinary registrations."*

### 2.6 The asymmetry that makes policy safe: waterfalls vs monotonic guards

*Source: [Tools subsystem](https://deepseek-harness.github.io/deepseek-harness/en/reference/subsystems/tools), [Tool execution pipeline](https://deepseek-harness.github.io/deepseek-harness/en/reference/tool-execution-pipeline).*

This is the single most transferable idea on the whole site, and it is worth a diagram of its own.

A reorderable waterfall (`tools/pre-execute`) returns a **decision**: `allow` | `deny` | `ask`. Ordering matters, and a listener that runs first can decide.

A **guard** (`ctx.tools.guard()`) is different by design:

> *"Its return type deliberately has no allow result: `undefined` preserves the waterfall decision, while a returned reason can only reduce permission, so a later listener cannot undo it."*
> *"Any matching guard may deny by returning a reason, while no guard can force-allow a call another guard denied."*

```
   extensible, reorderable          monotonic, order-independent
   ┌───────────────────────┐        ┌───────────────────────┐
   │  tools/pre-execute    │        │   registered guards   │
   │  allow │ deny │ ask   │  ───▶  │   deny │ (abstain)    │  ───▶  body
   │  ORDER MATTERS        │        │   ORDER CANNOT MATTER │
   └───────────────────────┘        └───────────────────────┘
```

The pipeline as a whole is a five-stage sandwich every capability passes through, and **no stage requires touching the loop**:

```
 pre-execute (waterfall: allow/deny/ask)
   → monotonic guards (deny-only)
     → approval ask, fail-closed
       → execute (waterfall: around-dispatch — timeout, retry, metrics)
         → the tool body
       → post-execute (waterfall: accept / replace / block / add context)
     → finalizeContent (definition-owned, synchronous, must not throw)
   → tools/result (emit: frozen, immutable, observation only)
```

Paired with it, the **fail-closed approval vocabulary**: outcomes are the closed set `'allowed-once' | 'rejected' | 'cancelled' | 'unavailable'`, and *"a missing, non-owning, throwing, or non-conforming answerer becomes `unavailable` rather than opening the gate."* There is also a session policy `'ask' | 'never'`, where `never` is *"the strict headless stance (CI, unattended runs) and the policy whose outcome is knowable without asking"* — enforced **inside the service before waterfall dispatch, so even an answerer registered later with `prepend` cannot bypass it.**

### 2.7 Reversible effects and teardown

*Source: [Fiber](https://deepseek-harness.github.io/deepseek-harness/en/reference/cordis-api/fiber), [Lifecycle and effects](https://deepseek-harness.github.io/deepseek-harness/en/develop/cordis-tutorial/02-lifecycle-and-effects).*

The rule: **every registration should have a matching disposer** — either returned from `ctx.effect()` or produced automatically by a Cordis helper.

Already effects, no work required:

- `ctx.on(event, handler)` — listener removed on unload
- `ctx.plugin(child)` — child disposed with parent
- `ctx.provide(name, value)` — service unregistered on unload
- `ctx.tools.register(tool)`, `ctx.llm.registerAdapter(...)` — harness registries *"attach their returned disposers to the calling plugin, so they unwind automatically"*

For anything the framework does not manage — a timer, a connection, a watcher — you wrap it:

```
ctx.effect(() => {
   acquire the resource
   return () => release the resource      ← runs on unload, on reload, on dispose
})
```

Two caveats they state explicitly and we should inherit:

- *"Disposers run in reverse registration order when the owning fiber unloads."*
- **But**: *"multiple async disposers run concurrently and have no serial completion guarantee. Put order-dependent cleanup in one disposer returned from a single `ctx.effect()` and await its steps serially there."*

Effects are also **diagnosable**: `fiber.getEffects()` returns a labelled tree, with labels like `ctx.on("event")` and `ctx.provide("name")`.

### 2.8 Hot reload is a consequence, not a feature

*Source: [Composition and HMR](https://deepseek-harness.github.io/deepseek-harness/en/develop/cordis-tutorial/06-composition-and-hmr), [Plugins and lifecycle](https://deepseek-harness.github.io/deepseek-harness/en/develop/framework/).*

Hot module replacement is three steps: unload the old plugin (cleaning up its registrations), load the new code, run the new `apply`.

> *"Because plugin registrations clean themselves up, hot replacement does not retain registrations from the old instance."*

And in the feature→mechanism table, the entry for hot reload reads, in full: **"every registration is a `ctx.effect` → vendored HMR just works."** That is the entire causal chain. The discipline is the asset; the reload is the dividend.

A config edit does the same thing: *"A configuration edit hot-replaces the plugin: the framework unloads the old instance and loads a new one."*

### 2.9 Dependency-driven load order — and its one trap

*Source: [Services and dependencies](https://deepseek-harness.github.io/deepseek-harness/en/develop/framework/service), [Composition and HMR](https://deepseek-harness.github.io/deepseek-harness/en/develop/cordis-tutorial/06-composition-and-hmr).*

Nobody writes a start-up sequence. A plugin declares `inject = ['tools', 'llm']` and *"when `apply` runs, every service declared by `inject` is ready."* Order emerges from the dependency graph.

The trap is stated bluntly and we should copy the warning as much as the mechanism:

> *"A plugin whose `inject` names a service nobody provides waits forever, printing nothing. No error — PENDING is a legitimate state, since the provider may be mounted later."*
> *"When a plugin does nothing and reports nothing, inspect its fiber state."*

Their answer is a diagnostic that walks the registry and prints every PENDING fiber. **Dependency-driven loading without a fiber-state inspector is a silent-failure machine.** The inspector is not optional.

### 2.10 Composition — profiles, bundles, layers, patches

*Source: [Architecture](https://deepseek-harness.github.io/deepseek-harness/en/reference/), [Package and install a plugin](https://deepseek-harness.github.io/deepseek-harness/en/develop/basic/publish).*

> *"A running `dsh` is a plugin tree composed at boot from ordered layers."*

Two nouns, two manifests, and they are never the same thing:

- A **bundle** is a distributable package that ships a **configuration layer** — a patch file that inserts or overrides plugin rows. It declares `dsh.bundle` in its manifest and answers *"what does this package contribute?"*
- A **profile** is a directory describing **one runnable composition** — an ordered list of bundles plus the user's own patch file. It declares `dsh.profile` and answers *"which bundles compose this setup, in what order?"*
- *"A bundle is what you author and distribute; a profile is what a user boots. Nothing is both."*

The layer stack, applied over an empty list:

```
  ┌─ 4. each --patch overlay, in argv order          ┐
  ├─ 3. machine-level patch file                     │  later layers
  ├─ 2. the profile's own patch file                 │  win, per row
  ├─ 1b. each installed bundle, in the order added   │
  └─ 1a. the base bundle (always first)              ┘
```

Three rules from this that matter more than the file formats:

1. **Every row has a stable `id`.** *"`id` gives the entry a stable identity so the loader can tell an edit to an existing entry apart from a removal plus an addition."* Without one, every config edit remounts everything.
2. **`disabled: true` keeps the row and skips mounting it** — a feature switch that leaves the evidence in place.
3. **Later layers replace a row's *entire* config, not a deep merge.** *"a patch replaces a row's entire `config` value rather than deep-merging keys... must restate every key the row needs, not just the changed one."*

And the single most operationally important affordance on the whole site:

```
dsh --profile web --dump-config     # print the exact tree this machine boots
```

*"Any row it prints can be replaced by a patch of your own."*

### 2.11 Configuration is a validated schema, and the rule about what belongs in it

*Source: [Plugin configuration](https://deepseek-harness.github.io/deepseek-harness/en/develop/basic/config).*

A plugin exports a `Config` schema; the loader validates raw config against it and fills defaults **before the plugin starts**, and *"invalid configuration fails the load with an actionable error."* Defaults live on the schema field, not in the code body.

Their design rule, worth quoting because it is the whole philosophy of a configurable system in one line:

> *"Harness requires anything that two deployments may want to set differently to be a configuration field."*
> *"The test is whether `cordis.yml` can change the value without a code edit."*

### 2.12 The three-role capability seam

*Source: [Three-role capability design](https://deepseek-harness.github.io/deepseek-harness/en/develop/practice/), [Capability seams](https://deepseek-harness.github.io/deepseek-harness/en/reference/capability-seams).*

When a capability needs replaceable implementations, it is split into three roles, and **the complete capability is the seam — no individual role is a seam.**

```
   ┌──────────────┐        ┌──────────────────┐        ┌────────────────┐
   │  DEFINITION  │◀───────│    PROVIDER      │        │    CONSUMER    │
   │  the service │        │  one implementa- │        │  uses it (often│
   │  + its Request│       │  tion            │        │  a model-facing│
   │  /Result types│       │                  │        │  tool)         │
   └──────────────┘        └──────────────────┘        └────────────────┘
          ▲                                                     │
          └─────────────────────────────────────────────────────┘
                          both depend only on the DEFINITION
                       provider and consumer never see each other
```

Their shipped example is shell execution: a definition package, a local-execution provider, and a model-facing tool. Swap the provider row in the config and *"the Service Definition and tool remain unchanged."*

The payoff sentence from the architecture page: *"Seams are why one provider swap changes the whole product. Filesystem and subprocess providers share one execution world, so pointing them at a remote sandbox moves Bash, PTY, and LSP with them, with no provider forks."*

Their restraint rule matters as much: **"Do not split preemptively — use separate packages only when the roles need to evolve independently. A simple tool plugin does not."**

### 2.13 Extension points are catalogued, and the catalogue is generated *and verified*

*Source: [Config catalog](https://deepseek-harness.github.io/deepseek-harness/en/reference/config-catalog), [Tool schema catalog](https://deepseek-harness.github.io/deepseek-harness/en/reference/tool-catalog), [Persistence catalog](https://deepseek-harness.github.io/deepseek-harness/en/reference/persistence-catalog), [Subsystems index](https://deepseek-harness.github.io/deepseek-harness/en/reference/subsystems), [Capability seams](https://deepseek-harness.github.io/deepseek-harness/en/reference/capability-seams), [Extension cookbook](https://deepseek-harness.github.io/deepseek-harness/en/reference/cookbook/extension-cookbook).*

A system this decomposed becomes unnavigable unless the surface is enumerated. Their answer is four generated catalogues, each answering one question an extension author actually asks:

| Catalogue | Answers | Generated from |
|---|---|---|
| **Config catalog** | *"what can I put under `config:` for this package, and which services must my tree also load?"* | the `Config` declarations in each package's source — 219 packages exhaustively accounted for, split into loadable-with-config, loadable-without-config, seam and library packages |
| **Tool catalog** | *"what exactly does the model see for every shipped capability?"* | **by booting each plugin on a real context and reading the live registry** — 52 tools across 24 packages |
| **Persistence catalog** | *"which events can appear in the durable log, and which of them actually reach the model?"* | the durable-event declarations, each badged `surface` or `log-only` — 44 events, of which **only 3 are `surface`** |
| **Per-subsystem Cordis API** | *"what can I inject and listen to on this subsystem, and in which dispatch mode?"* | the service and event declarations, with events headed by their mode (`tools/result — emit`, `tools/pre-execute — waterfall`) |

Three properties of these catalogues are worth more than their content:

1. **They are generated and hand-editing is forbidden.** Every one carries a variant of *"This file is GENERATED from source ... and verified fresh by `pnpm run verify-<name>-catalog` (part of `doc-sync`) — do not edit it by hand."* Documentation drift is a build failure, not a chore.
2. **They verify the declaration against the runtime, not just against the source.** The config generator *"cross-checks the runtime schemastery schema against the pasted declaration — every schema-validated key, nested keys included, must be locatable on the declared config type — **so the paste cannot hide a loader-accepted field**."* The tool generator goes further and **boots** the plugins, *"because a tool schema is not statically knowable."*
3. **Completeness is guarded.** *"A completeness guard globs `packages/*/tool-*` and fails if any package is missing from the generator's boot manifest, so **a new tool cannot be silently undocumented**."* The seam graph has one too: roles *"are classified in `scripts/gen-doc-graphs.ts` with a completeness guard."*

The dispatch mode is part of this machinery, not just prose: modes are declared with `@mode` JSDoc tags *"so the generated catalog can check declarations against dispatch sites."* The event's contract and the event's documentation cannot disagree.

And the extension cookbook makes the whole architecture **checkable** rather than merely claimed:

> *"Every product feature maps to a listener on a documented extension point — the microkernel claim made checkable. **No row modifies the loop.**"*

That table is the proof-of-work: hooks, goals, loops, workflows, compaction, memory, skills, MCP, scheduled tasks, UIs, telemetry, model adapters, sub-agents — each is one line naming the extension point it attaches to. If a feature cannot be expressed as a row in that table, the architecture has failed, and it is visible.

There is one more discipline worth naming: **runtime invariants**. Every package publishes a companion that registers checks under its own package name; a violation throws an error carrying a stable code and *the owning package name*, so *"a violation is attributable without the registry importing any product package."* A verifier mechanically rejects packages that ship an unexplained empty check. ([Runtime invariants](https://deepseek-harness.github.io/deepseek-harness/en/reference/subsystems/invariants).)

---

## What an agent-authored extension looks like

Two walkthroughs: the smallest useful extension end-to-end, then the same idea grown into a replaceable capability. Both are drawn from the docs; the *shape* is what transfers, not the syntax.

### 3.1 The smallest one: a tool, from empty directory to running system

*Source: [Build a tool](https://deepseek-harness.github.io/deepseek-harness/en/develop/basic/tool), [Into the harness](https://deepseek-harness.github.io/deepseek-harness/en/develop/cordis-tutorial/07-into-the-harness), [Tool authoring reference](https://deepseek-harness.github.io/deepseek-harness/en/reference/cookbook/adding-a-tool).*

```
  STEP 1        STEP 2         STEP 3        STEP 4         STEP 5
  make a  ───▶  declare  ───▶  register ───▶ add ONE  ───▶  run — it is
  file          what you       the           line to        in the system
                need           capability    the list
                (inject)                     (composition)
```

**Step 1 — one file, one function.** The plugin declares `name` and `inject = ['tools']`. Nothing else.

**Step 2 — the dependency is the whole ordering story.** *"`inject` makes Cordis wait for the tool registry."* The author never thinks about start-up order.

**Step 3 — register the capability.** A single call describing four things: a **name**, a **description** (this is literally what the model reads), a **parameters** schema, and an **output** declaration split into a machine-readable `schema` plus a `render` that turns the canonical value into what the consumer sees. Then an `execute` body.

Everything about that registration is engineered so the author cannot get it wrong:

- **Arguments are validated for you** against the declared schema before `execute` runs, and the argument type is *inferred from the schema* — one declaration, no drift between the doc, the validation, and the code.
- **Registration is an effect.** *"Registration is effect-based: disposing the plugin fiber unregisters the tool."*
- **The schema propagates by itself.** *"Schemas flow into the system-prompt assembly automatically."* The author never registers the capability in a second place — a catalogue, a docs page, a menu. There is one declaration.
- **The declaration is borrowed, not copied.** *"Registration borrows your readonly definition... To hot-swap a tool, dispose its owning effect and register the replacement."* Mutation after registration is forbidden; replacement is the supported move.
- **Identity is frozen before policy runs.** The arguments are snapshotted as lossless JSON, deep-frozen, and stamped with an opaque token *before* any gate sees them, so *"history, audit, UI, and execution must agree."* Notably, the pre-execute gate **cannot rewrite arguments** — only allow, deny, or ask — for exactly that reason.
- **A separate presentation projection.** How the thing renders is a *pure function of the arguments and result*, with a hard rule: *"These run on live streaming AND on session-log REPLAY, so they must be pure functions... NO I/O, NO reading session state, NO clock/random."* Presentation must be reproducible from the log alone.

**Step 4 — one line in the composition file.** The row names the module and optionally its config. That is the entire installation.

**Step 5 — it is live, and other plugins can already see it.** In the tutorial, a *second, independent* plugin listens to the `tools/result` event and logs every call. The closing observation is the point of the whole architecture:

> *"Neither of your plugins knows the other exists — the registry service and the event connect them."*

And the capability arrived with abilities nobody wrote for it: it passes through the full policy pipeline (permission, sandbox, timeout, metrics, audit) because the pipeline is generic; it is reachable from the programmatic "code mode" path *"without extra integration"*; and it is removable without residue.

### 3.2 The grown-up one: a replaceable capability in three packages

*Source: [Three-role capability design](https://deepseek-harness.github.io/deepseek-harness/en/develop/practice/), [LLM adapters](https://deepseek-harness.github.io/deepseek-harness/en/develop/practice/llm-adapter).*

When the capability needs more than one implementation, the same author splits it into three:

1. **The definition** declares an abstract service and the `Request`/`Result` types it speaks. It names the *capability*, never the first implementation.
2. **A provider** subclasses that abstract service and implements the one method. It names the mechanism, vendor or environment that distinguishes it.
3. **A consumer** injects the definition by name and exposes it — typically as a model-facing tool — and *never* imports the provider.

The dependency rule, stated as three lines:

> *"The Service Provider depends on the Service Definition. The Consumer depends on the Service Definition. The Service Provider and Consumer **do not depend on each other**."*

The model-adapter case is the clearest instance of the payoff. Adding an entirely new AI provider is: subclass one adapter base, implement one streaming method that translates the neutral request into the vendor's API and the vendor's response back into a neutral chunk sequence, declare a config schema for the key and the routes it handles, and call `registerAdapter(routes, adapter)`. Then a config row selects it. Two shipped adapters *"see the same harness contract implemented over different provider SDKs."*

Three rules from that guide worth carrying into any adapter QMF ever grows:

- **A capability gap is a typed error, never a silent drop.** *"If the provider cannot honor a field, throw... with a stable code instead of silently dropping it."*
- **The neutral vocabulary is a protocol with invariants**, not a loose dict — every block-start has a matching block-end, indices increase from zero, usage precedes finish, finish is last.
- **Capability discovery belongs to the adapter, not to a core enum.** *"preserve the adapter's authoritative selectable list... instead of promoting those values into a core enum."*

---

## The Python translation for QMX

Honest analysis. Some of this transfers almost unchanged, some transfers only as a shape, and one piece should be refused outright.

### 4.1 Verdict table: what translates, and how

| Harness mechanic | Translates? | The Python form |
|---|---|---|
| Plugin = function + `inject` + `apply(ctx)` | **Yes, cleanly** | a module-level `register(ctx, config)` plus a declared `requires` tuple. No metaclasses, no decorators-as-magic. |
| Context as service container | **Yes** | an explicit `Context` object with typed accessors over a name→instance mapping. **Not** `__getattr__` magic — see 5.1. |
| `inject` → dependency-driven order | **Yes** | topological sort over declared `requires`. Two policies (see 4.4). |
| `isolate()` child scopes | **Yes, and valuable** | a child `Context` overriding selected service names. This is exactly how a backtest workspace gets its own clock, data window and simulated venue while sharing everything else. |
| Reversible effects / disposers | **Yes, and it is free** | `contextlib.AsyncExitStack` / `ExitStack` per component. Every `register()` returns a disposer that is pushed onto the component's stack. Python's ExitStack unwinds **sequentially in reverse**, which is stricter than Cordis and therefore safer. |
| Four dispatch modes | **Yes, with a caveat** | `emit` = fan-out; `parallel` = `asyncio.gather`; `serial` = ordered await, stop on first answer; `waterfall` = a middleware chain, `listener(payload, next_)`. The caveat is *typing* — see 4.3. |
| Monotonic guards (deny-only) | **Yes — import this first** | a registry of callables returning `Refusal | None`. Order-independent by construction. Maps 1:1 onto the Book's doors and the veto ledger. |
| Fail-closed approval with a closed outcome set | **Yes** | an enum, plus the rule that absence of an answerer means refuse. |
| Composition file + ordered layers + `--dump-config` | **Yes — import this** | a YAML/TOML composition with stable row `id`s, a resolve step, and a `qmf show-composition` command that prints the exact tree before boot. |
| Bundle/profile split (distributable layer vs runnable composition) | **Yes** | a package may *contribute* rows via entry points; a **composition file decides what actually boots**. Installation must never equal activation. |
| Config schema with defaults + fail-loud validation | **Yes** | pydantic model per component, validated at load, error names the row `id` and the field. |
| Three-role capability seam | **Yes — the highest-value structural import** | `typing.Protocol` (definition) + implementation packages + consumers depending only on the Protocol. |
| Generated catalogue verified in CI | **Yes, later** | generate the component/event/seam catalogue from declarations; a freshness check in CI. Defer past qmf-core. |
| Runtime invariants attributed to the owning package | **Yes** | a check registry where failures carry the component id. Feeds directly into typed refusals. |
| Hot module replacement | **No — refuse** | see 4.5. |
| Declaration merging for typed events/services | **No** | no compile-time equivalent exists in Python; see 5.1. |

### 4.2 Where QMF's already-planned machinery IS the equivalent

Read against the qmf-v1 draft spec, three planned items already occupy the same slot — and two of them are **stronger** than the harness's version.

| Harness | QMF's planned equivalent | Verdict |
|---|---|---|
| Cordis service registry + `dsh.profile.bundles` list | **versioned component registry** | Same slot. QMF's is *versioned*; Cordis's is not. QMF wins. |
| `package.json` `dsh.bundle` / `dsh.profile` manifests | **manifests** | Same slot, near-identical role: a manifest declares what a package contributes and a separate manifest declares what a deployment composes. Keep the two-manifest split — it is what stops "installed" from meaning "running". |
| `dsh --dump-config` (print the resolved tree) | **fingerprints / the stamp machine** (`qmf-core` item 5: canonical serialization + fingerprinting of any definition) | **This is the marriage.** DSH can *print* its resolved composition; QMF can *fingerprint* it. Fingerprinting the resolved composition — every component id, version, and validated config — turns "which exact set of extensions produced this result?" from a question into a hash. Nothing in the harness does this. |
| `CordisError` / `LlmError` / `ToolFailure` / `InvariantError` with stable codes and an owning package name | **typed refusals** (`qmf-core` item 4) | Same idea, already ratified. The importable *delta* is **attribution**: every refusal should name the component that raised it, the way `InvariantError` carries `packageName`. |
| Config patch layers replacing a row wholesale | **versioning discipline** (`qmf-core` item 6: changing one mints a new version, never rewrites) | QMF is stricter and should stay stricter. See 5.3. |

**Conclusion:** QMF does not need to invent the *registry* idea or the *manifest* idea — it already planned both, in stronger form. What it has not yet planned is everything in 4.3.

### 4.3 What would genuinely need building

Ordered by value-per-unit-effort. Items 1–3 belong in `qmf-core` because retrofitting them is expensive; items 4–7 can follow.

1. **The Context and its child scopes.** Small. A container with `provide` / `get` / `require` / `child(overrides)`. The `isolate` capability is what makes per-workspace and per-backtest configuration possible without globals.
2. **The effect/disposer discipline, made pervasive.** Small individually, expensive to retrofit. Every `register()` in every QMF registry returns a disposer; every component owns an `ExitStack`. Nothing is registered that cannot be unregistered. **This is the one that must land in qmf-core or never.**
3. **A typed event bus with declared dispatch modes.** Medium. Python has no declaration merging, so the discipline has to be moved to **runtime**: an event is *declared* (name, payload dataclass, mode) in a registry; `on()` checks the listener signature and the mode at registration time and refuses a mismatch loudly; dispatch is only possible through the declared mode's method. This buys back most of what TypeScript gives them, at import time rather than compile time.
4. **Monotonic guards.** Small, high value. A separate registry from the waterfall, whose callables can only return a refusal or abstain. For money paths this is not a convenience — it is the correctness property.
5. **Composition: manifest + entry-point discovery + composition file + layer ordering + resolve.** Medium. Python's `importlib.metadata.entry_points` is the direct analogue of scanning `package.json` for a `dsh` key. The layering rules (stable `id`, `disabled`, later-wins-per-row, print-before-boot) transfer verbatim.
6. **The loader doctor.** Small, disproportionate value. `qmf doctor` lists every component and its state, every unmet requirement, every shadowed service, and every registered guard. Their own docs prove why: a plugin waiting on a missing service *"waits forever, printing nothing."* We should go one better and make **an unmet requirement at live start-up a hard failure** rather than a silent PENDING (see 4.4).
7. **Composition fingerprinting + generated catalogue.** Small (fingerprinting, given the stamp machine already exists) and medium (catalogue). Defer the catalogue; **do not defer the fingerprint.** When the catalogue does come, copy the three properties from 2.13 rather than the format: generated not hand-written, **verified against the runtime rather than only the source**, and guarded for completeness so a new component cannot be silently undocumented. Their tool catalogue is generated by *booting* the plugins precisely because *"a tool schema is not statically knowable"* — the same will be true of any QMF component whose declared surface depends on its config.

### 4.4 One mechanic that must be split in two: PENDING vs fail-loud

The harness's reactive model — wait quietly, activate when the provider appears, unload when it disappears, reload when it returns — is *right for an interactive session* and *wrong for a live money path*.

| | Research / agent workspace | Live money path |
|---|---|---|
| Missing requirement at load | PENDING, diagnosable, may resolve later | **Hard failure at start-up.** Refuse to boot. |
| Requirement disappears at runtime | unload the dependent, reload when it returns | **Halt.** A provider vanishing mid-session is an incident, not a graceful reload. |
| Optional dependency via `get()` returning nothing | fine | **banned on money paths** — a missing service must fail at start-up, never as a `None` check at order time |

Same mechanism, two configured policies. This is exactly the kind of thing their own config rule covers: *"anything that two deployments may want to set differently"* is a configuration field.

### 4.5 Hot reload: take the cause, refuse the effect

The harness gets HMR for free — *"every registration is a `ctx.effect` → vendored HMR just works."* The temptation is to want the same in Python.

**Recommendation: build the effect discipline, do not build HMR.** Reasons, honestly stated:

- Python module reloading is genuinely unreliable: stale references to old classes and functions survive in closures, registries, and instances; `isinstance` checks silently fail across reloaded module identities; and native extension modules — which QMF will lean on heavily via Polars and DuckDB — often cannot be re-initialised at all.
- Ninety percent of the benefit comes from something Python does well anyway: **fast, clean process restart**, which reversible teardown makes trustworthy.
- The narrow case where in-process reload genuinely helps — an agent iterating on one indicator inside a long research session — has a safe form that is not HMR: **dispose the component's effects, build a fresh child context, import a fresh module object, re-run `register`.** That is the harness's own supported move (*"To hot-swap a tool, dispose its owning effect and register the replacement"*), and it does not require reloading anything.

### 4.6 Where extensibility should live in QMX's architecture

Three places are in play: the **QMF libraries**, the **QMX app** (with the trading node), and the **agent sandboxes/workspaces**. The standing rules constrain the answer: live money paths are fixed at start-up, and agents never deploy to live unattended.

**Option A — mechanism in QMF only; both deployables consume it.**
One protocol, one registry, one mental model everywhere. An agent's work is directly promotable because it is the same kind of artefact all the way up.
*Cost:* nothing about it is safe by construction. An agent that can write a component can write a component that a live process would load.

**Option B — extension only inside agent workspaces; the app is a fixed build.**
Maximum live safety, trivially auditable.
*Cost:* an agent's proven work can never graduate without a rewrite. That directly contradicts *"the way quants experiment with Python"* — the whole point of that phrase is that a quant's exploratory code **becomes** library code.

**Option C — RECOMMENDED — one mechanism, three composition tiers, one hard line.**

```
  ┌─────────────────────────────────────────────────────────────┐
  │  QMF LIBRARIES — the MECHANISM lives here, and only here    │
  │  context · registry · events · effects · guards · manifests │
  │  · composition resolve · fingerprint                        │
  └─────────────────────────────────────────────────────────────┘
        │                    │                        │
        ▼                    ▼                        ▼
  ┌───────────────┐   ┌────────────────┐   ┌────────────────────┐
  │ TIER 1        │   │ TIER 2         │   │ TIER 3             │
  │ AGENT         │   │ RESEARCH /     │   │ LIVE MONEY         │
  │ WORKSPACE     │   │ PAPER (app)    │   │ (node)             │
  ├───────────────┤   ├────────────────┤   ├────────────────────┤
  │ OPEN          │   │ REVIEWED       │   │ SEALED             │
  │ compose at    │   │ composition is │   │ composed at boot,  │
  │ session start │   │ a checked-in   │   │ printed,           │
  │ mount freely  │   │ artefact;      │   │ FINGERPRINTED,     │
  │ no approval   │   │ change = a     │   │ then CLOSED        │
  │               │   │ reviewed change│   │                    │
  │ NO live venue │   │ paper venue    │   │ no mount, no       │
  │ provider is   │   │ provider       │   │ reload, no         │
  │ INSTALLED     │   │                │   │ discovery — ever   │
  └───────────────┘   └────────────────┘   └────────────────────┘

                 promotion is a HUMAN EDIT to a composition file,
                 never a runtime action  ──────────────────────▶
```

The reasoning, tier by tier:

- **The mechanism belongs in QMF**, because a framework whose extension model differs between deployables has two extension models, and agents will learn the wrong one. One shape everywhere satisfies the ruling.
- **Tier 1 is safe by absence, not by permission.** The strongest control is not "the agent is denied the live venue" but "**the live venue provider package is not installed in the sandbox image at all**". The harness's own seam design supports this exactly: swap the provider row and every consumer follows, with no consumer forks. In a workspace the execution seam binds to a simulator; there is no other provider present to bind to. Their own Python SDK guide is blunt about the alternative: their example composition uses full access and *"Run it only inside a disposable checkout or container."*
- **Tier 3 seals the composition.** The harness already composes at boot from ordered layers and can print the exact tree. QMX's live node does the same, then adds two steps the harness does not have: **fingerprint the resolved tree**, and **close the loader** — after which any attempt to mount, reload, discover or provide is a typed refusal, not an error to handle. The fingerprint is what makes "the live node was running exactly this" a checkable fact rather than a claim.
- **Promotion is a human act on a file.** Not a runtime API, not an agent-callable tool. Copying a component from Tier 1 to Tier 2 means adding a row to a checked-in composition; Tier 2 to Tier 3 means the same again. This satisfies "agents never deploy to live unattended" *structurally* — there is no unattended path, because there is no runtime path at all.
- **The unattended default is refuse.** Import the approval policy verbatim: the unattended stance is *"never prompt anyone: every ask resolves rejected deterministically"*, and it is enforced **before** any answerer chain runs, so no later-registered listener can bypass it. That is the correct default for every agent process by construction, not by configuration hygiene.

Two supporting imports that make Option C hold:

- **Money gates are monotonic guards, never a reorderable waterfall.** Use the waterfall for enrichment and observation; use deny-only guards for anything that can stop a trade. Then no listener ordering can ever make the system less safe.
- **Attribution on every refusal.** Every "no" names the component that raised it, following the invariants pattern. This is the mechanical basis of a veto ledger.

---

## What NOT to import

### 5.1 TypeScript-specific — no Python equivalent, do not fake one

- **Declaration merging** (`declare module { interface Events { ... } }`) is how they get typed events and typed `ctx.<service>` with zero runtime cost. Python has nothing equivalent. **Do not simulate it** with dynamic attribute injection: a `__getattr__`-based context defeats pyright, defeats autocomplete, and hides typos until runtime — in a codebase whose stated value is *"written for humans AND agents"*, that is a direct cost. Use `Protocol` classes and an explicit typed container, and move the mode/signature checking to registration time.
- **The proxy-based `Context`** (*"A context is a proxy: normal property reads go through the service resolver"*) with prototypal inheritance for child scopes. Python's version of this is an explicit dict lookup in a small class. Plainer, and inspectable.
- **Schemastery / Standard Schema.** Python has pydantic. Port the *rule* (defaults on the schema, validate at load, fail loud) and none of the machinery.
- **The monorepo package protocol** — `tsconfig` project references, `files` allowlists, workspace constraint scripts, `publint`. All of it is TypeScript build plumbing. The one idea underneath that *does* transfer is worth keeping: **a mechanical verifier that rejects a package with a missing or unexplained contract section.**
- **Bundler and client-module machinery** — client bundles, lazy-CJS factory artefacts, bundle-purity gates. Not applicable.

### 5.2 Chat-agent-specific — the wrong domain entirely

Wholesale discard: turn and step lifecycle, the inbox / steering / follow-up model, `agent/pre-step` and prompt interception, system-prompt assembly, the session log as *model context*, context compaction and token metering, sub-agents, skills, plan mode, Code Mode, conversation nodes, browser settings cards, permission prompts as UI, transcript replay for a chat UI. A quant framework has none of these problems.

**But three of these have a *shape* worth stealing while discarding all the content:**

| Chat-agent thing | The transferable shape | QMX reading |
|---|---|---|
| Append-only session log + `deriveMessages()` projections + the invariant *"Model-visible means logged"* | one append-only journal is the source of truth; every view is a **projection** of it; anything that reaches the decision surface must be **reconstructable from the log**, asserted by a runtime invariant | *"money-affecting means journaled"* — and the projection idea is how a UI, a report and a telemetry export stay consistent without three writers |
| Every durable event badged `surface` (reaches the model) or `log-only` — 44 events, only **3** are `surface` | the set of events that can *influence the decision* is declared, enumerated, and vastly smaller than the set that is merely recorded | the analogue is worth building: badge which journal events can influence a money decision versus which are recorded for evidence only, and let the catalogue prove the influencing set is small |
| The tool execution pipeline (pre → guard → around → post → observe) | a generic five-stage gate sandwich that policy attaches to **without touching the loop** | this is the seven-doors shape, already |
| Fail-closed approval with a closed outcome set and a deterministic unattended policy | absence of an answerer is a refusal; unattended = refuse before anyone is asked | the human-in-the-loop rule for live, expressed as a type rather than a convention |

### 5.3 Unsafe for money — refuse specifically

1. **Hot reload, or any runtime mounting, on the live path.** Discussed in 4.5 and 4.6. On the live tier the loader is closed after boot.
2. **Auto-unload-and-reload when a required service disappears.** *"Dependent plugins dispose automatically. They load again when the service returns."* Correct for a chat app. On a live money path a provider vanishing mid-session is a halt condition, not a graceful reload — and a component silently coming back to life mid-session is worse than one that stays down.
3. **Waterfall short-circuit used as a *grant*.** Not calling `next()` skips everything downstream. That is exactly right for a refusal and dangerous for an approval: a listener that short-circuits to "allow" also skips every gate behind it. Money gates must be deny-only guards where a short circuit can only *subtract* permission.
4. **`prepend: true`, and listener ordering as policy.** Their own docs restrict `prepend` to *"only when a listener must run before ordinary registrations."* For QMX the rule should be absolute: **ordering must never be what makes the system safe.** If reordering two listeners can change whether a trade is allowed, the design is wrong.
5. **Whole-row config replacement in patch layers.** *"a patch replaces a row's entire config value rather than deep-merging keys... must restate every key the row needs."* An author who forgets a key silently loses it to the schema default. On money paths: require the resolved config to be complete and explicit, reject unknown keys loudly, and fingerprint the result — QMF's versioning discipline (*"changing one mints a new version, never rewrites"*) is the stricter and correct rule.
6. **Optional dependencies resolved at use time.** `ctx.get('metrics')` returning nothing, then `metrics?.record(...)`, is a fine pattern in a chat app and a latent incident in a trading system. On money paths a required service must fail at **start-up**, never as a None-check at order time.
7. **Install-time code execution.** Their own warning is exemplary and applies with more force to us: allowing a build script is *"permission to execute the package's code on your machine at install time, outside any sandbox the agent runs under. Only allow packages whose source you trust, and pin a commit so a later push cannot silently change what runs."* In Python this is worse, not better — installing an sdist runs arbitrary code. **No unpinned installs on any host that shares a machine with live money; agent sandboxes get a pre-built image.**
8. **Full-access default compositions.** Their Python SDK example ships `danger-full-access` with the caveat *"Bash and the editor can modify any path allowed to the runtime process."* An agent sandbox must never share a filesystem or credential namespace with anything live — the sandbox's ability to reach live must be **absent**, not merely denied.

---

## Open questions for Mubarak

1. Should one extension mechanism serve all three tiers with the live node simply sealing it at start-up, or should the live node ship with no extension loader compiled into it at all?
2. When an agent's workspace extension proves itself, what exactly is the promotion act — you editing the composition file yourself, or a reviewed change that a human merges?
3. Do you want the resolved composition — every component, version and validated setting — fingerprinted and stamped onto every backtest result, so no result can ever be read without knowing what produced it?
4. If a required component is missing at start-up, should the live node refuse to boot at all, or boot and refuse only the trades that needed it?
5. Are agents allowed to install third-party Python packages inside their sandboxes, given that installing a package runs its code?

---

## Pages read for this study

**Concepts:** [Cordis primer](https://deepseek-harness.github.io/deepseek-harness/en/reference/cordis-primer) · [Architecture](https://deepseek-harness.github.io/deepseek-harness/en/reference/) · [Capability seams](https://deepseek-harness.github.io/deepseek-harness/en/reference/capability-seams)
**Cordis API:** [Context](https://deepseek-harness.github.io/deepseek-harness/en/reference/cordis-api/context) · [Events](https://deepseek-harness.github.io/deepseek-harness/en/reference/cordis-api/events) · [Fiber](https://deepseek-harness.github.io/deepseek-harness/en/reference/cordis-api/fiber) · [Registry](https://deepseek-harness.github.io/deepseek-harness/en/reference/cordis-api/registry) · [Service](https://deepseek-harness.github.io/deepseek-harness/en/reference/cordis-api/service)
**Developing:** [Plugins and lifecycle](https://deepseek-harness.github.io/deepseek-harness/en/develop/framework/) · [Services and dependencies](https://deepseek-harness.github.io/deepseek-harness/en/develop/framework/service) · [Event system](https://deepseek-harness.github.io/deepseek-harness/en/develop/framework/events) · [Your first plugin](https://deepseek-harness.github.io/deepseek-harness/en/develop/basic/) · [Plugin configuration](https://deepseek-harness.github.io/deepseek-harness/en/develop/basic/config) · [Build a tool](https://deepseek-harness.github.io/deepseek-harness/en/develop/basic/tool) · [Package and install a plugin](https://deepseek-harness.github.io/deepseek-harness/en/develop/basic/publish) · [Three-role capability design](https://deepseek-harness.github.io/deepseek-harness/en/develop/practice/) · [LLM adapters](https://deepseek-harness.github.io/deepseek-harness/en/develop/practice/llm-adapter)
**Tutorial:** [index](https://deepseek-harness.github.io/deepseek-harness/en/develop/cordis-tutorial/) · [2 — Lifecycle and effects](https://deepseek-harness.github.io/deepseek-harness/en/develop/cordis-tutorial/02-lifecycle-and-effects) · [6 — Composition and HMR](https://deepseek-harness.github.io/deepseek-harness/en/develop/cordis-tutorial/06-composition-and-hmr) · [7 — Into the harness](https://deepseek-harness.github.io/deepseek-harness/en/develop/cordis-tutorial/07-into-the-harness)
**Pipelines:** [Agent turn and step lifecycle](https://deepseek-harness.github.io/deepseek-harness/en/reference/agent-lifecycle) · [Tool execution pipeline](https://deepseek-harness.github.io/deepseek-harness/en/reference/tool-execution-pipeline)
**Cookbooks:** [Extension cookbook](https://deepseek-harness.github.io/deepseek-harness/en/reference/cookbook/extension-cookbook) · [Adding a package](https://deepseek-harness.github.io/deepseek-harness/en/reference/cookbook/adding-a-package) · [Tool authoring reference](https://deepseek-harness.github.io/deepseek-harness/en/reference/cookbook/adding-a-tool) · [Adding a settings card](https://deepseek-harness.github.io/deepseek-harness/en/reference/cookbook/adding-a-settings-card)
**Subsystems and catalogs:** [Tools](https://deepseek-harness.github.io/deepseek-harness/en/reference/subsystems/tools) · [Scoped registration](https://deepseek-harness.github.io/deepseek-harness/en/reference/subsystems/scope) · [Runtime invariants](https://deepseek-harness.github.io/deepseek-harness/en/reference/subsystems/invariants) · [User approval](https://deepseek-harness.github.io/deepseek-harness/en/reference/subsystems/approval) · [Config catalog](https://deepseek-harness.github.io/deepseek-harness/en/reference/config-catalog) · [Tool schema catalog](https://deepseek-harness.github.io/deepseek-harness/en/reference/tool-catalog)
**Other:** [Python SDK guide](https://deepseek-harness.github.io/deepseek-harness/en/guide/python-sdk)
