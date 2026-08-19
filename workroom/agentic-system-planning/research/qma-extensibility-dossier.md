# QMA Extensibility Dossier — Cordis-class kernel, read for a Python reimplementation

**Purpose.** Everything QMA needs to know about how Cordis (the kernel under DeepSeek Harness, formalised in *A Programming Paradigm for Spatiotemporal Composability*) makes a system extensible, and what it costs to build the same thing in Python with a React/TypeScript UI.

**Inputs.** `research/raw/` holds six files; **four are load-bearing here**: `study-cordiverse-paper.md` (the 88-page paper, Draft of Aug 13 2026, Shi/Zhang/Cui — PKU + DeepSeek-AI), `study-cordis-code.md` (cordis `main` + the vendored `cordis@4.0.0-rc.7` inside `deepseek-ai/deepseek-harness`), `study-dsh-docs.md` (the DSH developer docs), `study-ui-extensibility.md` (Koishi console + DSH web client). The other two (`lean-cli-readme-extraction.md`, `x-timelines-2026-08-18.md`) are parked and unrelated to this dossier. Three conflicts between notes or between paper and code were re-checked against original source; see §7.

---

## Plain summary — for the operator, no jargon

Read this part and you will understand the whole decision. The rest is detail.

**The problem.** Normal software is assembled once, at startup. If you want to add or remove a piece, you restart. That is fine for a text editor. It is not fine for an agent that writes its own tools: every time it improves itself, it would have to kill and restart itself, losing everything it was holding — and a bad edit would kill the very process needed to fix the bad edit.

**What Cordis does.** It makes parts addable and removable *while the system is running*, and it makes that safe with two rules.

1. **Nothing is done without an undo.** Every time a part changes the system — registers a tool, opens a connection, listens for an event — it must hand back the exact undo for that one change. The kernel collects those undos. Removing the part means running them. The part never writes a "cleanup" function; its cleanup is *assembled automatically from the things it did*. This is why removing a plugin leaves no residue: not discipline, structure.

2. **Parts declare what they need, and the kernel does the wiring.** A part says "I need `tools` and `llm`". It does not start until both exist. If one disappears — because you swapped the model provider — the part is stopped automatically, and restarted automatically when the replacement is up. Nobody writes boot order. Nobody writes reconnection logic.

**Why this matters for QMA specifically.** These two rules are exactly what a self-modifying agent harness needs, and the paper's own conclusion says so in as many words: it names self-evolving agent harnesses as the intended future validation of the work. An agent can rewrite one of its own capabilities, the kernel swaps that one piece, everything else keeps running, and if the new version fails to start, the old one is put back and the failure is recorded on that one part instead of taking down the process.

**What it costs.** Three honest limits.

- **The undo is a promise, not a check.** The kernel never verifies that your undo actually undoes. If an author writes a sloppy inverse, the guarantee quietly stops holding, and nothing tells you.
- **Anything that leaves the process cannot be taken back.** A file written where other programs can read it, a message sent, an API call made — those are gone. What is reversible is the *handle* (the open file, the registration, the subscription), not the *output*. For an agent harness this is the important sentence in the whole document: you can undo "the tool is registered", you cannot undo "the tool emailed someone".
- **Python does not have two of the tricks the TypeScript version leans on.** One is cosmetic (the `ctx.tools` dot-syntax); one is not (the way every plugin silently adds its own types to a shared type, which is how the whole ecosystem stays type-safe without a central registry). Section 5 has the replacement, and it is arguably better than the original — but it is a design decision to make now, not later.

**The bottom line.** The load-bearing part of Cordis is about 20% of it, it is well specified, and it ports to Python cleanly because it is ordinary state-machine logic. The parts that do *not* port are the ergonomics and the type system. Budget the design effort there, not in the state machine.

---

## 1. The paradigm

### 1.1 In plain language

Cordis is a **meta-framework**: it has no opinion about what your software does. Its only job is to define what "adding a part" and "removing a part" mean, precisely enough that the meaning still holds when parts are added and removed continuously, concurrently, and by a machine rather than a person.

It identifies two independent dimensions that every plugin system gets wrong:

- **Temporal composability** — *time*: when a part is removed, everything it did must be undone. The paper's evidence that this is unsolved: of the top 100 VS Code extensions, 87 contain executable code and therefore require a host restart to remove; `deactivate` is a shutdown callback, not an unload mechanism, and it separates disposal from creation (you write the undo somewhere far away from the do, so it drifts).
- **Spatial composability** — *space*: parts must declare and discover each other in a checkable way, and must react when a dependency appears, disappears, or is replaced by a different implementation. VS Code's evidence: only 7 of the top 100 declare `extensionDependencies`, and the cross-extension API is typed `any`.

Statically these are solved problems — temporal is lexical scoping (RAII), spatial is import resolution. Dynamically both break, because no lexical scope can bracket a plugin loaded after deployment and no compile-time context can anticipate a dependency created by runtime configuration.

The move is to **reify** the two classical academic notions — effects (what a computation *does to* its environment) and coeffects (what it *needs from* its environment) — as runtime objects the kernel can manipulate, rather than as compile-time annotations. Effects become **revertible**: each one carries its inverse. Coeffects become **reactive**: each change of environment is classified against a declaration as *activating*, *deactivating*, or *neutral*.

Then both are folded into **one object**: the context, `ctx`. Everything a part does, and everything a part needs, passes through that single object. That is the paradigm's whole ergonomic claim — the traceability of pure-functional state threading with the ergonomics of ordinary imperative code, because every operation is attributable to the specific `ctx` it was invoked on, and therefore to the part that owns it.

### 1.2 The formal core that must not be lost in translation

These are the pieces where a "reasonable simplification" silently destroys the guarantee. Each is stated with its source.

**F1 — An effect is a function that returns its own inverse.**
`𝔈_Γ := Γ → Γ × (Γ → Γ)` (Def 8). Applied to the current context, it yields the new context *and* the function that undoes it. Inverses are **one-sided (left) inverses**: what an inverse is held to is `g ∘ f = id`, never `f ∘ g`. The inverse is chosen **per state, at the point of application** (`𝔈*_Γ`, the "witnessed" version, constrains `g(δ) = γ` only where the effect was applied). *Do not* let an inverse be a method on a class registered separately from the operation — that is exactly the VS Code `deactivate` defect the paper diagnoses.

**F2 — Inverses accumulate in reverse (twisted composition).**
`(f₁,g₁) ∘ (f₂,g₂) := (f₁∘f₂, g₂∘g₁)` (Def 1). The accumulator `φ` is the composite of all inverses so far; the state carries the invariant **`φ(γ) ≃ γ₀`** — applying the accumulator returns you to where you started. LIFO reversion needs no extra hypothesis (Thm 16).

**F3 — An effect may be a generator.**
`𝔈^iter_Γ := μℐ. Γ → Γ × (Γ→Γ) × Maybe(ℐ)` (Def 51). Each iteration yields one inverse and optionally a continuation. The paper is explicit that this is a *reified delimited continuation* and that it maps directly onto the `yield` operator mainstream languages already provide. The reason it matters is not elegance: **the boundary between two iterations is the only place a load can be interrupted and partially rolled back.** Without generator-shaped effects, a transition is all-or-nothing.

**F4 — Providing a dependency is itself an effect.**
`set(k,v) : 𝔈*_Σ` (Def 23). This one line is the entire synergy: because registering a service is an effect, service registration is automatically tracked and automatically undone. The paper states it directly — "coeffect operations are effects, and effects are revertible." A kernel that has a separate `registerService` path outside the effect primitive has already lost the guarantee.

**F5 — One primitive, no exceptions.**
"Every context mutation in Cordis flows through a single primitive, `ctx.effect`" (§5.1.1). Component instantiation (`ctx.plugin`) is itself an effect on the parent — which is *why* unloading a parent cascades to children, with no cascade code anywhere.

**F6 — Satisfaction and notification.**
`σ ⊨ d := ∀k ∈ d. k ∈ dom(σ)` (24); `notify_d(σ,σ′)` returns activating / deactivating / neutral (Def 26). Activating runs the effects; deactivating applies the accumulator. Because *all* mutation passes through effects (F5), every change of satisfaction is detectable at an effect boundary. That is the algebraic basis of reactivity.

**F7 — The lifecycle compares two views, and identity beats value.**
A fiber holds a **committed view** `ω` (which fiber provided each declared key when this fiber last activated) and computes a **target view** (who provides them now). Every rule fires on their agreeing or differing (Def 46). The view records **the provider's identity, not the value** — a uid drawn fresh and never reused. Two consequences that must be preserved: a different provider supplying an equal value *is* a change; and **a provider overwriting its own binding in place is invisible**, so replacement must be withdraw-then-install (§5.1.3).

**F8 — A fiber in transition provides nothing.**
`σ_γ` unions the tables of **Active** fibers alone (40). A fiber that is loading or unloading is not a provider. This is what "makes a withdrawal visible to dependents one step before it happens": the provider stops providing, dependents recompute an unsatisfied target and begin their own teardown, **while the provider's bindings are all still physically in place**.

**F9 — Leaving and unloading are two separate steps, and the second is guarded.**
`L-Leave` records the decision to deactivate without acting on it; `L-Unload` is *the only rule in the calculus that applies an accumulator*, and it carries the premise `¬relied_n(γ)` — no other installed fiber's committed view still names me (Def 50). This is what lets a consumer keep reading a dependency **throughout its own teardown** (closing a connection pool means handing connections back to the pool that is going away). The guard is per-binding, not per-fiber, and it provably cannot deadlock (Thm 66).

**F10 — Order-sensitive things go in coeffects, not effects — and commutativity is an obligation on the PROVIDER of a key.**
Effects are only safely reorderable when they are **independent** (Def 19), and Thm 42 delivers independence from a simpler condition: every key touched is **commutative**. The design rule (§3.3.2, quotable): *a key whose value is a table of independently added and removed entries is commutative — a route table, an event-listener list. A key whose value is an ordered chain is not — a middleware inserted before another sees a different request.* Where order matters it must be imposed from outside: **within one component by the accumulator (LIFO); across components by a declared dependency.** Composability is thereby had at the grain of components, not of single effects.

**The half this dossier previously stated as a rule and never converted into a law.** §3.3.2 closes with: *"commutativity of a key is a property of the interface that key publishes, so meeting it is an obligation on the **provider** of the key, not on consumers."* That has teeth, and it bites the flagship surface of any Cordis-class harness: **an interception pipeline is an ordered chain**, listener order is registration order, and the loader deliberately arranges no load order at all. Mount two policy plugins on the same `pre-execute` point — one that denies, one that rewrites — and their relative order is undetermined, so the assembled system's behaviour is **not a function of the configuration**, which is exactly what confluence (F13) is claiming. Two things restore it and both must be written into the authoring contract, not left implicit:

1. **Monotonic (deny-only) stages are commutative by construction** — a set of contributions that can only subtract yields the same intersection in any order. This is what DSH's separate *guard* stage buys, and why it sits beside the waterfall stage rather than inside it. Anything that must be order-independent belongs there.
2. **Every non-commutative key must publish how order is determined** — an explicit priority on registration, or a declared dependency between the contributing plugins so activation order fixes registration order. A key that cannot state this is not a shippable extension point.

**F11 — Inertia.**
Once an iteration is launched it lands, and its landing cannot be declined (§4.3.3). A target that changes mid-flight cannot abort the in-flight step; the fiber lands, then deactivates. This is why Resolution Coherence (Thm 64) is a *disjunction* — either the transition finishes against one resolution, or it diverts/raises and is fully recovered — rather than a promise about every step.

**F12 — Failure is recorded on the fiber, not propagated.**
`L-Raise` routes a failure through Unloading, so the accumulator built up to the failing step is applied and the fiber arrives at `Inactive(ξ)` **having installed nothing** (Cor 62: a failed fiber's contribution to the state is nothing). `L-Begin` requires `Inactive(⊥)`, so a failed fiber does not auto-retry against an unchanged environment. A failed fiber blocks nothing and leaves its siblings running — "the behavior a plugin host wants."

**F13 — Confluence: the payoff sentence.**
Whatever sequence of loads, unloads, swaps and reverts a running system went through, **the state it settles at is the state you would have got by writing the final composition down at the outset and loading it once, in dependency order** (Thm 73). This is what licenses reasoning about a live, agent-mutated harness as if it were statically assembled. It holds under four conditions — dependency graph acyclic, effects pairwise independent, every component installs everything it declares it provides, and **no failed fiber**. Failure is explicitly excluded as a genuine source of divergence.

**The four conditions must travel with the claim, every time it is invoked.** The last one is awkward for an agent harness specifically, because failure containment (F12) is a *headline feature* — "a plugin that fails to start damages only itself, the profile keeps running" — and it is precisely the condition that voids the confluence relied on for safe incremental reconciliation. Cor 62 bounds the damage: a failed fiber's contribution to the state is nothing, so the divergence is confined to **which fibers are Active**. But for a configuration-driven UI, which fibers are Active *is* the observable. The honest downstream statement is therefore: with a failed fiber present, the running system is not guaranteed to equal a from-scratch load of the same configuration, the difference is confined to activity, and **"reload from the recipe" is a real operation rather than a no-op**. Quoting the payoff sentence without the hypotheses — as the first pass of the kernel contract did — is the single easiest way to build a reconciliation loop on a theorem that is not in force.

**F14 — The system boundary is where the guarantee stops.**
A location is *inside* the boundary when the system can modify it exclusively and restore it; otherwise the operation is `id_Γ` — untracked, unrecoverable (§6.1). Every outward operation has two stages: the **acquisition** (open a descriptor, spawn a child, register a handle) is inside and revertible; the **emission** (bytes written, datagram sent, tokens streamed to a user) crosses to the outside and is not. Recovery from an emission is only ever *withholding* it until the state is certain, or *compensating* for it — and the paper is explicit that compensation composes LIFO like an inverse **but the metatheory does not transfer**, because commutation was proved against `≃` and must be re-established against the coarser equivalence.

**F15 — Provisions are disjoint, and a second provider is refused at mount.**
Def 58(2): `m ≠ n ⇒ p_m ∩ p_n = ∅` is a **well-formedness clause**, and it is imposed at **O-Insert's last premise** — "the last premise of O-Insert is where the single-source discipline is imposed." Preservation (Thm 59) establishes it at every step. So this is not a policy choice a runtime may relax into last-writer-wins: a mount whose provision set collides with an installed fiber's must be **refused**, or the registry is not well-formed and every theorem built on preservation stops applying. This was missing from the first pass of §4.1 and from the kernel contract's law table.

**F16 — Confinement: an effect function may not read another fiber's control fields.**
Def 48. A fiber's effect function is *confined to that fiber*: it writes only its own entry, and it reads only its own table, the restrictions of other tables to the keys **it declared**, and the part of the state no fiber's table names. Explicitly forbidden: "a table outside `d_n`, or **any control field** — which is what keeps a component from branching on the lifecycle state of a fiber it did not declare." Every fiber's effect function is *required* to be confined. This has a direct consequence for any plugin-tree introspection surface (a UI, telemetry, a supervisor): it cannot be ambient. It has to be a declared capability published by the runtime, not something a component reaches by walking the tree.

**F17 — The inverse of a registration is retirement, not removal.**
Def 47. A registration's inverse is **O-Retire**, and the paper says why in one line: *"an inverse has to apply wherever it is reached."* O-Retire has a single premise (the name exists) and therefore always applies; **O-Remove carries premises that can fail** (`∀m. π_m ≠ n` — children removed before parent), so an inverse built from it can fail, which the accumulator has no way to handle. What retirement leaves behind is a **vestigial entry** (Lemma 57): retired, `Inactive(⊥)`, empty table, no children — differing from absence in control fields alone, which no rule can tell apart. Removal is then a separate, guarded step. And this is what earns safe **name reuse**: a freed name is reissuable only because the L-Unload guard already prevents any surviving committed view from naming it (Thm 59, "the guard on L-Unload is what carries clauses (3) and (4)"). Fresh-never-reused uids alone are not the mechanism.

---

## 2. Backend extensibility, end to end — the full life of a capability

Traced against the actual code (`packages/core/src/{registry,fiber,service,reflect,events}.ts`) with the paper's algorithms as the normative statement, and DSH's docs as the applied convention. Divergences between the three are flagged **[DIVERGENCE]**.

### Stage 0 — The capability is declared as a package

DSH's canonical shape is the **three-role split** (`develop/practice`): a **Service Definition** package declares the `ctx.<key>` and its request/result types (`dsh-shell`); one or more **Service Provider** packages implement it (`dsh-bash-local`, `dsh-bash-sandbox`, `dsh-pwsh-local`); a **Consumer** package exposes it to the model as a tool (`dsh-tool-bash`). Provider and consumer never depend on each other, only on the definition. **The complete capability is the seam — no individual role is one.** Swapping the implementation is a one-row edit in `cordis.yml`.

DSH classifies every `ctx.<key>` as `seam` (swappable, 1+ named providers), `core` (single fixed spine implementation), or `bundle` (the one concrete assembly, e.g. the agent loop), and enforces that every declared service is classified by a generator + completeness guard script. That is a machine-checkable extensibility inventory — worth copying wholesale.

### Stage 1 — An entry in the config tree

`cordis.yml` is a **plugin tree**, one row per fiber (Def 74 / `vendor/loader/src/config/entry.ts`):

```
{ id, name, config?, group?, disabled?, inject?, isolate?, intercept? }
```

`id` is hierarchical (`:`-joined when nested) and is the **reconciliation key**. `name` is the module specifier. `disabled` supports a `!!js` expression evaluated against the loader context at every mount decision; `config` supports expressions evaluated against the plugin's *own* context after its injections activate. Everything else is literal.

Why an entry is a *faithful* specification of the calculus: the support set (Def 67) reads only τ, π, d, p — and an entry supplies all four (`disabled`→τ, tree position→π, `name`→the component, which declares d and p).

Reconciliation is **incremental with per-field dispatch**: `id`/`name` → rebuild; `isolate` → **realm reassignment**; `intercept` → patched in place, no reload (metadata is read at access time); `config` → handed to the component, which decides; `disabled` → unload/reload. A group's config *is* its child list, so group reconciliation and entry update recurse together down the tree. Entry update is **transactional with rollback** — if the new plugin fails to start, the previous options and previous plugin are restored and an apply error is raised.

**Realm reassignment is not a table cell — it is Algorithm 7 plus equation (65), and reducing it to "→ realm reassignment (Alg 7)" (as the first pass of this dossier did) leaves any `isolate` edit through a UI undefined.** Since `isolate` is in the entry shape and per-mind/per-session isolation is the reason it exists, this has to be carried in full:

- **Two kinds of realm, behaving differently under every edit.** `isolate: true` asks for a **local** realm, private to the entry, **tagged by its `id`, and carried with the entry wherever it moves**. A **string** asks for a **global** realm, **shared by every entry naming that string** — so moving such an entry changes which entries it shares a binding with. A realm is **discarded once no entry names it**.
- **The hard question** is whether the entry is *itself the provider* at a key whose realm changed — undecidable from the realm symbol alone once a realm is shared by several fibers. The answer is **delimiters**: one symbol `δ_k` per key, under which each context stores a tag of its own, **written on a context, inherited by descendants, drawn fresh at each reassignment**. Equation (65): `γ′[δ_k] = d₁ ⟺ γ′ derives from the entry's context`. Write `own(γ′)` for that test.
- **The rebind loop.** For each key `k` whose realm changes, capture `(s₁, s₂, d₁, d₂)` = (old realm, new realm, the entry's fresh tag, the provider's tag); reload the entry's fiber; then move `store[s₁] → store[s₂]` **exactly when `d₁ = d₂`**, i.e. exactly when the entry is itself the provider at `k`.
- **`affected` replaces Alg 3's realm test.** A dependent is affected at `k` when its realm for `k` is `s₁` or `s₂` **and** `own` separates it from the provider: `(fiber.ctx[δ_k] = d₁) ≠ (d₂ = d₁)`. Where `own` agrees on dependent and provider, both move or neither, and the dependent sees the binding afterwards exactly as before; where `own` separates them, the dependent **gains or loses** the binding — the only case that must trigger a reload. Notify with this predicate, not with realm equality.

**Entry movement between groups** is worth stating alongside: Cordis handles it by **live prototype re-parenting** (`Object.setPrototypeOf(this.ctx, this.parent.ctx)` in the loader's `_patchContext`), so a moved entry immediately sees its new ancestor chain with no rebuild. `collections.ChainMap` cannot do that cheaply — re-parenting means rebuilding `.maps` for the entry and every context derived from it. And since ids are hierarchical and `:`-joined, a move **changes the id**, which is a rebuild by the first dispatch row anyway. A Python port should simply state that a moved entry is rebuilt.

The metatheory is what licenses this being incremental: Thm 73 makes the settled state a function of the final config alone, Thm 66 guarantees it settles, Cor 62 makes a departing fiber's contribution nothing. And Thm 63 means **the orchestrator arranges no load order at all** — a fiber whose dependencies are not up simply waits at its L-Begin. So the loader imports modules concurrently, which is where bringing up a large configuration actually spends its time.

### Stage 2 — `ctx.plugin(plugin, config)` → Runtime + Fiber

A plugin is one of three interchangeable shapes (`registry.ts`): a function `(ctx, config)`, a class constructed as `new P(ctx, config)`, or an object with `apply(ctx, config)`. The **resolved callback's function identity** is the registry key (`Map<Function, Runtime>`), so re-plugging the same function reuses one `Runtime` and adds another `Fiber`. One Runtime, many fibers — which is precisely what lets HMR swap fibers while the Runtime record survives.

`ctx.plugin()` returns a thenable wrapper over the Fiber, so `await ctx.plugin(X)` waits for it to settle while synchronous callers still get an inspectable Fiber immediately. `ctx.inject(deps, cb)` is sugar for an anonymous plugin whose whole body is gated on dependencies.

**A fiber's very existence is one effect on its parent** (`fiber.ts:265-297`). Setup pushes the child into `runtime.fibers`; teardown clears the uid, fires `internal/plugin`, removes it from the runtime, drops the Runtime if it was the last, and kicks the child's own `_unload()`. Parent disposal cascades because the parent's disposables list contains each child's disposer.

### Stage 3 — Dependency resolution and the epoch

`inject` is the coeffect specification `d`. The fiber computes an **epoch string** from its dependencies (`fiber.ts:611`):

```
epoch = "" ; for name in inject: impl = store[name] ;
  if not impl: epoch = INACTIVE, break ; else epoch += ":" + impl.fiber.uid
```

`INACTIVE = '__INACTIVE__'` means at least one dependency is missing. This string **is** the target view of F7, flattened. State changes only react to an actual epoch change: into INACTIVE → unload; out of INACTIVE → reload; **between two different real epochs → unload, then reload** (a dependency's provider was swapped; never a live in-place patch). Fiber states: `PENDING, LOADING, ACTIVE, FAILED, DISPOSED, UNLOADING`, mapping onto the calculus as LOADING=Reloading, FAILED=Inactive(ξ).

### Stage 4 — The plugin body runs; a Service self-registers

For a class plugin: `new Ctor(ctx, config)`, then any `[symbols.initHooks]` queued by `@Inject`-decorated methods, then `instance[Service.init]?.()`. `[Service.init]` is conventionally an **async generator** — the first `yield` is the teardown disposer, registered *before* any setup that could throw; subsequent code is the async setup body. That is F3 realised as an ordinary language feature.

`Service`'s constructor **self-registers**: it calls `ctx.reflect.provide(name, self, check)` on itself. There is no install step. `provide()` is itself wrapped in `ctx.fiber.effect(...)`, so the registration is undone when the constructing fiber unloads (F4 concretely). Optional `[Service.check]` gates availability dynamically — **and its re-evaluation trigger matters**: it is re-checked on `notify`, so a provider signals "I have become unavailable" by causing a notify, not by returning `false` at some arbitrary later moment. A port that ships `available()` without specifying when it is re-read gives a provider no way to withdraw itself. `[Service.invoke]` makes the service callable (`ctx.logger('name')`); `[Service.resolveConfig]` merges `intercept` config from every ancestor context, root-closest first.

Note also that `ctx.logger` is **not sacred core**: in DSH the console logger is a **vendored plugin** (`logger-console`), and `ctx.timer`, `ctx.loader`, `ctx.hmr` are all plugin-provided services in the "inherited Cordis core API" list. Any Python port using `__getattr__` for service sugar should count carefully: `__getattr__` fires **only on a miss**, so every name declared on the `Context` class is permanently unavailable as a service name. Fixing something like `logger` as a class attribute quietly removes the ability to swap it per realm — e.g. routing each mind's logs into that mind's own session log — and turns a one-row recipe edit into a kernel commit.

`reflect.provide()`'s setup: declare `props[name]`, allocate the isolation key, write `store[key]`, write the fiber's own snapshot, and if already ACTIVE, `notify([name])`. Its teardown: delete `store[key]`, `notify([name])` again, **await every affected fiber settling**, *then* delete from the provider's own store — comment: "ensure self access before dependencies cleanup." That last line is F9's guard, in code.

### Stage 5 — Lookup: `ctx.tools`

`Context` is a `Proxy` returned from its own constructor, so every context user code ever sees is a proxy (`context.ts:83`). The `get` trap: special props (symbols, `then`, `_`-prefixed, numeric) fall through; own/inherited properties return traced; a declared accessor calls its getter; otherwise the **`internal/get` waterfall** runs, whose terminal step walks **up the fiber chain**:

```
key = target[isolate][prop]
fiber = ctx.fiber
loop: impl = fiber.store?.[prop]         → found: return traced value
      prop in fiber.inject               → throw "inactive context"
      !fiber.runtime                     → throw (root reached, undeclared)
      fiber.parent[isolate][prop] != key → throw (isolation boundary)
      fiber = fiber.parent.fiber
```

This is Alg 6 of the paper. Note what it enforces: **the fiber's committed view, not the store.** `ctx.get(key)` is a lookup against the store that never fails; `ctx.tools` resolves against the accessing fiber's own view and **enforces the declaration at the point of use** — undeclared access is rejected.

**Two things about this that a reimplementation loses if it "simplifies":**

- **`internal/get` is a genuine extension point, and it is the only one that spans every capability.** The walk above is the *terminal step* of a waterfall, so a plugin can wrap **every service read in the system**. That is where per-component attribution, per-mind quotas, read auditing and record/replay live — none of which any individual capability's own pre-execute pipeline can provide, since a waterfall only exists where that capability's author chose to publish one. The sibling points are `internal/set` (waterfall, and it enforces that only the providing fiber may write), `internal/listener` (**bail** mode, runs *before* registration and can replace the registration outcome entirely — Cordis uses it to redirect `internal/update` listeners into per-fiber chains), and `internal/dispatch` (every public dispatch self-reports mode/name/args/scope). Inline the terminal and delete the waterfall, and cross-cutting policy becomes a kernel edit.
- **The unchecked path is narrower than it looks.** The paper's own capability claim (§6.3) is scoped — "the complete set of **proxy-mediated** capabilities a component requires is known before it runs" — and `ctx.get` sits outside that mediated surface. In the code the unchecked read is not even *transparently* reachable from a plugin: `reflect.ts`'s get trap falls back to the non-strict `reflect.get(prop, false)` **only when `ctx.fiber.runtime` is falsy**, i.e. only at the root fiber. Any reimplementation that keeps a universal unchecked read **and** advertises a complete, load-time-reviewable capability set is claiming something neither source claims. Reading the view rather than the store is also exactly what keeps a dependency readable to a component whose teardown was triggered by that dependency going away (F9). The paper turns this into its answer for agent permissioning: `inject` is a capability request, the proxy is the capability mediator, and because requests are declared statically the complete capability set is knowable before a component runs — reviewable and approvable at load time (§6.3).

Child contexts are `Object.create(parentProxy)` with own keys defined on the child. `isolate(name, label?)` creates a new isolate map prototype-chained off the parent's and points `name` at a fresh (or shared) symbol — below that context, the service resolves to a different slot. This is the two-layer `ρ`/`σ` resolution of Def 28, and DSH uses it via `group: true` + `isolate:` maps to run two differently-configured instances of the same service side by side.

### Stage 6 — Events

Five dispatch modes over one shared resolution step. `dispatch()` shifts an optional leading `thisArg` (which doubles as the isolation filter source via `Context.filter`), then returns the matching hooks' callbacks bound and filtered.

| Mode | Semantics |
|---|---|
| `emit` | fire-and-forget, synchronous, return values and promises ignored |
| `parallel` | `Promise.allSettled` over the same listener set as emit; rejections re-thrown as one `AggregateError` |
| `serial` | sequential, awaited, stops at the first non-`null`/`false`/`undefined` result |
| `bail` | same as serial but synchronous |
| `waterfall` | onion/around-middleware: the last argument is the terminal continuation; each listener gets `next`; not calling `next()` vetoes everything downstream including the built-in behavior |

**⚠ The two synchronous modes do not port to Python, and reproducing this table verbatim (as the first pass did) hides it.** In JS, `emit` calling an async listener at least **executes the body** and orphans the returned promise — sloppy, but the work happens. In Python, calling an `async def` listener from a synchronous method returns a coroutine object that is never awaited: **the body never runs at all**, and the only signal is a `RuntimeWarning` at garbage-collection time that nobody sees in production. A synchronous `emit`/`bail` in a Python kernel therefore **silently drops every async listener** — and "make the handler async because it awaits something" is the first thing a plugin author, or a model writing a plugin, will do. Any Python port has to either reject async listeners on these keys at *registration* (loud, load-time, with the `parallel` alternative named in the error) or drop the two synchronous modes. It cannot simply translate the semantics.

**A shape the five modes do not cover, and that the "closed set of five" claim can obscure: the collector** — run every contributor and *merge* their results. `parallel` returns nothing; `serial` stops at the first answer. DSH does catalog-merging through **services**, not events: `ctx.skills` "merges provider skill catalogs", `ctx.llm.registerAdapter`, `ctx.subagents` as a named-provider registry, `ctx.systemPrompt.section()`. The rule to carry forward is *collectors are registries*, and each contribution is a caller-attributed effect (§7 row 1) so it withdraws on unload. Without saying so, an author will try to build a collector out of `parallel` and find it cannot return anything.

`isBailed(v) = v !== null && v !== false && v !== undefined` — so `0`, `''`, `NaN` **do** stop the chain. **[DIVERGENCE — minor]** DSH's canonical table marks `waterfall` as "Awaited? No" while its own examples write `await ctx.waterfall(...)`; the code resolves it: the dispatcher does not await, it returns whatever the chain returns, which is usually a promise the caller awaits. DSH counts the four modes as emit/waterfall/parallel/serial with `bail` as a fifth; the core counts emit/parallel/serial/bail as four with `waterfall` separate. Same five primitives, two framings.

Every `ctx.on()` is **an effect**, so listeners unregister on unload and `on()` returns the disposer directly. Listeners are wrapped so their internal `ctx.foo` resolves against the *registering* context. `internal/listener` is a bail-mode extension point that runs before registration and can replace the registration outcome entirely — used internally to redirect `internal/update` listeners into per-fiber chains.

**Scope filtering, and the default that is easy to get backwards.** `dispatch()` reads `Context.filter` off the optional leading `thisArg` and applies it per hook unless the hook was registered `{ global: true }`. The default filter a Service supplies is **isolation-label equality** (`service.ts`: `ctx[isolate][name] === this.ctx[isolate][name]`), so a listener registered at **root does *not* see events from an isolated child realm** — `{ global: true }` is the explicit opt-out. DSH's `dsh-scope` package layers the *opposite* convention on its scoped tool events ("listeners on the plain root context receive everything"), so the two sources genuinely differ and a port must choose rather than inherit an accident. Whichever default is chosen, **the `global` escape hatch is load-bearing**: telemetry, cost accounting, the durable session-log bridge and the UI bridge all must observe every realm, and under an equality default with no opt-out none of them can be written.

**The applied convention is what makes this into an extensibility surface.** DSH's tool pipeline is one closed pattern, reused identically everywhere: `tools/pre-execute` (waterfall — reorderable allow/deny/ask) → registered **monotonic guards** (final-only, can deny but never re-allow) → `tools/execute` (waterfall — around-dispatch: timeout/retry/metrics, may replace only the abort signal) → `tools/post-execute` (waterfall — accept/replace/block) → tool-owned `finalizeContent` (sync, content only) → `tools/result` (emit — frozen final observation). The agent loop mirrors it exactly. Every dispatch mode is documented on the event with an `@mode` tag, a generator builds the catalog from source, and a verifier checks declarations against actual dispatch sites. A "native hook" is then just an ordinary plugin listening on an interception point — no external hook protocol needed, and Claude-Code/Codex-style hook config files are bridged by mapping them onto these same points.

DSH additionally keeps **two separate buses** and insists they not be confused: the live Cordis event bus (ephemeral, in-process coordination) and the **durable append-only session log** (`SessionEventMap` — replayable JSON rows, each tagged *surface* or *log-only*, merge-extensible), reachable live only through the single Cordis emit `session/event`. Same vocabulary, different buses. For an agent SDK this two-bus split is arguably as load-bearing as Cordis itself, and it is orthogonal to it.

### Stage 7 — Reconfiguration

`fiber.update(config, noSave)`: if not ACTIVE, defer resolution (services may not be available); if ACTIVE, resolve and run through the `internal/update` waterfall whose terminal action assigns the config and calls `restart()` (force epoch INACTIVE → refresh → unload + reload). Each plugin's own `internal/update` hooks form a private nested waterfall, so a plugin can intercept its own config changes and handle them in place rather than restarting.

### Stage 8 — Teardown

The normative version (Alg 5): mark UNLOADING **before** any transition task is created; `unload` **awaits every notified dependent reaching INACTIVE**; then apply the whole accumulator; then discard the committed view; then either settle Inactive or chain straight back into a reload if the target changed again.

The code (`fiber.ts:_unload`): `await Promise.all(this._disposables.clear().map(...))` — **all top-level effects torn down concurrently**, each wrapped in its own `try/catch` that logs and never rethrows to a sibling. Within one `effect()` call's own nested disposers, teardown is strictly **LIFO and sequential**. Effect creation is rejected outright while UNLOADING. Disposers are idempotent and re-entrant-safe: a `disposing` flag returns the in-flight task; a `WeakMap` side table lets a second caller join an async cleanup already running; calling a disposer while setup is still executing waits for setup first; a synchronous setup failure rolls back partial disposables and rethrows, so `effect()` never returns a wrapper for a failed setup.

**[DIVERGENCE — load-bearing, verified against source]** The paper places the dependent-drain wait *ahead of the whole recovery*, and argues explicitly why: "`fiber.dispose` initiates a fiber's effects concurrently and a wait placed within one of them would leave the rest unordered." The shipped code places it *inside one inverse* — the `provide()` effect's own disposer — which is precisely the arrangement the paper rules out. Confirmed at `cordiverse/cordis@main`: `fiber._unload` has no dependent wait and fans its disposables out with `Promise.all`; `reflect.provide`'s disposer does `delete store[key]; const fibers = this.notify([name]); await Promise.allSettled(fibers.map(f => f.await())); delete ctx.fiber.store[name]`. Net effect: the *store deletion* is ordered after dependents drain, but the provider's **other** disposers (its connections, its subprocesses, its listeners) race the drain. QMA must pick one; see §6 Q1.

**[DIVERGENCE — documented, but worth deciding deliberately]** Theory says reversion is LIFO (Thm 16). Implementation gives LIFO *initiation* and concurrent *completion* across a fiber's top-level effects. DSH's docs handle this by turning it into a written rule for plugin authors: *"if teardown order matters, keep the related registrations inside one `ctx.effect()`."* That is a real contract, not a footnote — it is the difference between "the kernel orders your cleanup" and "the kernel orders your cleanup only where you nested it."

### Stage 9 — Hot reload

Config edit → in-place `fiber.update` if only `config` changed. Source edit → HMR: classify the module graph by **accept/decline propagation** (accept a module once any of its imports is accepted; decline once *all* its imports are declined; anything left ambiguous — i.e. caught in an import cycle — defaults to declined), detect stale entries whose dependency tree intersects `accepted`, then **transactionally** back up and evict both the ESM and CJS caches, re-import, dispose old fibers, create fresh fibers under the same Runtime/Entry, and on any failure restore the caches *and* re-register the old plugins so the system ends up exactly where it started.

The paper's framing is the important one: **HMR needs no developer-annotated acceptance boundaries** (unlike Webpack/Vite), because the fiber already bounds all of the component's effects and coeffects. Disposing the old fiber recovers everything; a new fiber reinstalls it. DSH states the same as a consequence rather than a feature: "every registration is a `ctx.effect` → vendored HMR just works."

The honest cost, stated by the paper: **a component's own in-memory state does not survive a reload unless it is placed in a longer-lived dependency.** Cordis reverts and reapplies from a clean slate; it does not migrate state forward the way Erlang's `code_change/3` or DSU systems do. Layering forward migration on top of revertible effects is named as future work.

---

## 3. UI extensibility

### 3.1 What Koishi actually does — corrected

The `study-ui-extensibility.md` note asserts (marked `[INFERENCE]`) that Koishi's browser client "is not itself a Cordis context" and that running Cordis on both sides is DSH's generational leap. **That is wrong.** Re-checked against source:

- `koishijs/webui`, `packages/client/client/context.ts`: **`export class Context extends cordis.Context`**, using `this.effect()` for registrations and mounting its UI capabilities (`ActionService`, `I18nService`, `LoaderService`, `RouterService`, `SettingService`, `ThemeService`) as ordinary `this.plugin()` calls.
- `packages/client/client/index.ts`: **`export const root = new Context()`** — the browser boots a real Cordis root.
- The paper says the same in §5.3: *"Koishi's web console is a second, independent Cordis application whose plugins compose browser/UI primitives rather than server ones"* — cited there as evidence of the paradigm's **runtime-generality**, that the same primitives carry a production system in a wholly different runtime.

So the server-side surface (`ctx.console.addEntry({dev, prod})`, `addListener`, `broadcast`, `DataService` with `get()`/`refresh()`, WebSocket transport) is the *bridge*, not the whole story: the browser side has been a Cordis tree since Koishi.

The genuine DSH deltas are narrower and more interesting than "two trees vs one":

1. **The browser boots the same vendored `@cordisjs/plugin-loader` the host uses**, with a client module table filling its `internal` contract — so UI plugins are loaded by a real declarative loader with dependency ordering, not just registered.
2. **Per-plugin bundles with a boot manifest**, rather than dev/prod entry paths declared per plugin.
3. **Slots as the sole composition mechanism**, in React, with `SlotMap` declaration merging as the type authority.

### 3.2 How a plugin ships UI in DSH

- Declare a `dsh.client` field in `package.json` (`platform: 'web'`, optional `inject` edges, optional `immediately` flag) and export the built bundle at `exports["./client"]`. One package emits both halves — `lib/index.js` (node) and `lib/client.js` (browser) — from a shared `tsdown` preset. No separate `dist/`.
- The host's `ctx.clientModules` (`ClientModuleRegistry`) scans **incrementally, driven off Cordis fiber construction/disposal**: `internal/plugin` emissions mark an entry name dirty and a microtask flush reconciles dirty names against live loader entries. The UI asset graph is therefore a *derived view of the plugin tree*, not a parallel registry.
- The host composes a `WebBootGraph` of `{ id, url, rev, inject?, immediately? }` rows and injects it as the first `<head>` script, `window.__DSH_BOOT__`, with `<` escaped so plugin-controlled strings cannot break out. **A page without a valid manifest cannot boot** — the parser throws loudly on a missing or malformed graph.
- Bundles are served at `GET /plugins/<id>/client.js`, content-hash `rev` as cache-buster, response `no-cache`; unknown ids 404 loudly rather than falling back to SPA HTML served as JS. `immediately: true` rows execute during stage-one boot (registration only); the rest are lazy.
- Bundles execute against a shell-held lazy CJS module table (`window.__ModuleLoader__.load({id, factory})`), so **cross-plugin value imports are a build error** — plugins cooperate only through Cordis services, mirroring the backend's no-privileged-core rule exactly.
- The plugin's browser-half `apply()` mounts services/stores and registers slots. Composition is **only** through slots — "there is no component registration model besides slots; the former view and tool rings both dissolved into it." A `register` call occupies a slot, declares and authorizes its child slots, declares its store, and injects its business face; props arrive in four auto-derived shares. Every rendered entry sits in a **per-entry error boundary**. Never export components globally.
- A pure-UI plugin is possible with zero backend footprint — `ui-trajectory` is cited as the exemplar: no ctx service, only view-slot registrations. Even the settings screen is plugin-composed: `ui-settings-plugins` owns the Plugins section and its tab extension point; `ui-settings-plugin-inventory` contributes a tab into it.
- CSS is inlined into the bundle and injected as `<style data-plugin="<id>">` at materialization — CSS Modules hashing plus an ownership tag give isolation *and* clean removal on unload.
- Type safety across the boundary is kept by splitting TS project references (`tsconfig.host.json` / `tsconfig.client.json`), with client packages consuming host wire types only through pure type subpaths so no host-only augmentation leaks into the browser type program.

### 3.3 Transport

DSH: `IApiClient` is the object-layer face; Web carriage is **HTTP POST for the two client→server quadrants** and **one WebSocket per logical stream for the two server→client quadrants**. A `ConnectionController` opens the streams, pumps them with `for await`, and reconnects with jittered exponential backoff (500ms → 10s, unlimited retries) behind a generation fence; reconnect triggers a full list refresh plus a per-open-session resync. Sinks are injected one-way so the transport never knows about `Session` objects, and `ctx.apiProxy` is explicitly transport-independent. Koishi is plain WebSocket end to end.

### 3.4 Is UI registration reversible?

**Yes, structurally — with one caveat that matters for QMA.**

Structurally yes because the browser tree is a real Cordis tree: slot registrations, store declarations and service mounts made in a UI plugin's `apply()` are ordinary fiber effects, subject to the same construction/disposal lifecycle as any backend registration. It is exercised continuously rather than theoretically: dev-mode HMR stat-polls each bundle, calls `rebuilt(id)`, broadcasts over SSE, and the client **swaps one Cordis fiber per frame** — routine proof that slot/store/service registrations tear down cleanly and re-register without residue. Failure is contained the same way as on the backend: "one crashing slot entry blacks out one card, one failed bundle fails loud before the UI flips in." CSS removal is explicit via the ownership tag.

The caveat: **reversal of the registry is not reversal of the rendered world.** Cordis guarantees the *slot table* returns to its prior state. It does not, and cannot, guarantee that the user's screen, scroll position, in-flight animation, or focus returns — and by the paper's own §6.1 framing, pixels already painted are an **emission**, not an acquisition. For a UI this is usually fine (React re-renders from the restored registry). It stops being fine wherever a UI plugin's effect reached outside the browser tab — a downloaded file, a posted form, a clipboard write. The rule for QMA is the same as on the backend: reify the handle, treat the output as emitted.

---

## 4. Essential vs incidental

The test applied: **does removing this break a guarantee, or only comfort?**

### 4.1 The load-bearing 20% — remove any of these and it is not Cordis any more

1. **One mutation primitive that returns inverses at the point of application, and accepts a generator.** (F1, F3, F5.) The generator form is not optional sugar: it is the only thing that provides interruption boundaries and partial rollback within a transition.
2. **Service provision implemented as an effect.** (F4.) The single line that makes the whole thing self-cleaning.
3. **A declared dependency set that gates activation, plus reactive notification.** (F6.) Without it you have RAII, not composability.
4. **The fiber state machine with committed view vs target view, keyed on provider identity.** (F7.) Value-keyed comparison silently misses provider swaps; in-place binding overwrite becomes invisible.
5. **Active-only provision.** (F8.) The one-step-early visibility of a withdrawal is what makes ordered teardown possible at all.
6. **The L-Leave / L-Unload split with the `¬relied` guard.** (F9.) Without it, a consumer's teardown can dereference a dependency that has already been torn down. This is the single most-often-omitted mechanism in comparable systems (OSGi Declarative Services and iPOJO both have hand-written, *synchronous* deactivation callbacks with no protocol to await an asynchronous teardown exchange — the paper names this as their limit and as what Cordis closes).
7. **Per-iteration staleness check, plus inertia as an explicit concept.** (F11.) You need both the check and the honesty that an in-flight step cannot be aborted.
8. **Failure contained on the fiber, no auto-retry from a failed state, siblings unaffected.** (F12.)
9. **Access resolved against the accessing fiber's committed view, and undeclared access rejected.** This is simultaneously the correctness mechanism (a dependency stays readable through its consumer's teardown) and the security mechanism (capability request + capability mediator).
10. **Isolation realms — the two-layer `ρ`/`σ` resolution.** Genuinely essential for an agent harness, because per-session and per-agent service instances are exactly what it buys; and it is very expensive to retrofit, since it touches every lookup.
11. **Config as a declarative tree with per-field dispatch and transactional entry update.** The imperative primitives alone do not give an orchestrator (or a model) a safe surface to reconfigure the system.
12. **A closed, documented set of dispatch modes with `waterfall` as the interception primitive.** The value is the closedness — every extension point in DSH is one of five shapes, so a plugin author never invents an event protocol.
13. **Disjoint provisions, refused at mount.** (F15.) Def 58(2) is a well-formedness clause imposed at O-Insert; without the refusal the registry is not well-formed and preservation — and everything built on it — stops applying.
14. **Confinement.** (F16.) Def 48 forbids a fiber's effect function from reading another fiber's control fields. Drop it and a component can branch on a sibling's lifecycle state, which is outside the calculus and defeats the traceability the whole paradigm is selling.

**Two honesty notes about this list, because it mixes criteria without saying so.** The stated test is *"does removing this break a guarantee"*, and items 11 and 12 do not meet it: the paper's calculus contains **neither a loader nor an event bus**, and Cordis is still Cordis without either. They belong on the list, but under a different heading — *"genuinely essential for an agent harness"* — which is the criterion item 10 (isolation realms) is explicitly justified by too. Meanwhile items 13 and 14, which **are** preservation hypotheses of the metatheory, were absent from the first pass. Two headings, honestly labelled, is better than one list carrying two tests silently:

- **Breaks a guarantee if removed:** 1–9, 13, 14.
- **Does not break the calculus, but a Cordis-class agent harness is not buildable without it:** 10, 11, 12.

### 4.2 Ecosystem convenience — valuable, replaceable, not load-bearing

- **The `Proxy`-based `ctx.foo` property syntax — the `get` trap only.** Split it carefully, in **three** parts, not two: the *capability check on access* is essential (item 9 above); the *transparent dot-syntax* is ergonomics and can be replaced by an explicit typed-key call; but the **`apply` trap is neither**, and it does not belong in this section at all — see §5.1 row 7, which the first pass of this dossier also mis-filed as ergonomics. It is a correctness mechanism.
- **Constructor return-override** (`Context` returning its own Proxy; `Service` returning a callable object when `[Service.invoke]` is defined). Pure JS trickery for identity ergonomics.
- **Callable services** (`ctx.logger('name')`).
- **`Symbol.for()` cross-realm symbol keys** and the custom `Symbol.hasInstance` that unwraps proxies for `instanceof`. Solves a problem created by proxies and by vendoring the package under two npm scopes.
- **TypeScript declaration merging.** Nuance: *incidental to the model, essential to the ecosystem.* The runtime does not depend on it at all — zero runtime code. But it is the entire reason 4000+ independently-authored Koishi plugins can type `ctx.<key>` and event payloads without a central registry. It must be **replaced**, not dropped (§5).
- **The `@Inject` decorator**, class-level and method-level.
- **`mixin`/`accessor` sugar** — `ctx.on` forwarding to `ctx.events.on` is implemented as accessors, not as class methods.
- **`!!js` YAML expressions** in `disabled`/`config`.
- **HMR itself.** The paper is right that it is a *consequence* of the effect discipline rather than a mechanism. For QMA it is a developer-experience investment, not a correctness one — and the most expensive single item to port.
- **Interception (`ι` metadata with right-biased merge).** Powerful — it is the paper's answer to per-component access policy, adjustable at runtime with no reload and no graph perturbation because it changes only *how* a binding is used, not *whether* it is satisfied. But composability holds without it.
- **The three-role capability pattern and the seam/core/bundle classification.** Conventions and tooling discipline, not kernel mechanisms — and both are cheap, high-yield things to copy.
- **The service broker pattern** (§6.2) — one broker injected by both providers and consumers, absorbing the perturbation so that swapping a backing provider triggers no consumer reload. Not kernel; a pattern the kernel enables, and the one that turns rolling updates from an infrastructure operation into an application-level composition. **"Incidental" is right about the kernel and wrong about the product, and this dossier should not have left it at one line.** The alternative — *exclusive binding*, where at most one implementation is bound and switching unloads one and loads another — is what every "swap the provider, it is a one-row edit" demo actually shows, and its blast radius is **every consumer fiber in every realm naming that key**. For one profile that is cheap and correct; for `llm` with hundreds of minds running it is a reload of the world. The broker absorbs it and reloads nobody, and it is also the natural shape for cross-process and remote providers (§6.2's third capability), with the caveat the paper attaches: an interface intended to cross processes must be designed against an asynchronous, mid-flight-failable contract from the start. **Which shape each seam uses is a per-key decision that belongs in the seam classification on day one**, because retrofitting a broker changes consumers' `inject` sets and is therefore a breaking change to every consumer package.

### 4.3 Explicitly outside the guarantee

Worth stating so it is never assumed: emissions (§6.1); in-memory state across reload; anything a component reaches through a global or a captured closure rather than through its context — the paper flags this as the specific safety cost of realising the paradigm as a library rather than a language feature: *"a component may reach another component's context by mistake, through a closure or a global variable. An effect it installs there then leaks out of its own lifecycle, and a coeffect it reads there escapes its dependency specification."*

---

## 5. Python reimplementation analysis

Overall verdict, stated up front: **the state machine ports; the type system and the transparent-access ergonomics do not.** The fiber/effect/coeffect machinery is ordinary imperative logic with no TypeScript dependency — dicts, lists, a loop, and `asyncio`. The two design decisions to make *now*, not later, are (a) how typed identity works without declaration merging, and (b) how much of the transparent proxy to emulate versus replace with something explicit.

### 5.1 Mechanism-by-mechanism

| # | Mechanism | TS feature used | Python equivalent | Difficulty | Recommended approach |
|---|---|---|---|---|---|
| 1 | Effect primitive returning a disposer | closures | closures | **Easy** | Direct port. Accept the same four return shapes: callable, awaitable-of-callable, generator, async generator. |
| 2 | Generator-shaped effects (`𝔈^iter`) | `function*` / `async function*` | `yield` / `async def … yield` | **Easy *except at abandonment*** | Direct port; the manual `iter.next()` drain loop becomes `__next__`/`__anext__`. Keep the stale-epoch check at each boundary — **and when that check fires, `await iter.aclose()` (or `iter.close()`) before returning.** Simply breaking out of the loop, which is what a literal port of the JS does, leaves a half-drained async generator to be finalised by GC or `loop.shutdown_asyncgens()`, so any `finally` in the plugin's setup body runs at an arbitrary later time — **possibly after the fiber is DISPOSED**. That is a second, untracked teardown path outside the accumulator, and it is the state the calculus has no name for. This row is not "Easy"; it is easy plus one mandatory line. |
| 3 | Fiber state machine + epoch string | plain logic | plain logic | **Easy** | Port near-verbatim. `asyncio.Task` for `fiber.inertia`; implement `Fiber.__await__` to reproduce the thenable-plugin trick natively. |
| 4 | Concurrent teardown, per-disposable error containment | `Promise.all` + per-item try/catch | `asyncio.gather(*, return_exceptions=True)` | **Easy for the fan-out, hard for cancellation** | Use `gather(return_exceptions=True)`, **not** `TaskGroup` — TaskGroup's cancel-siblings-on-error semantics directly contradict "one broken teardown must not stop the others"; surface the aggregate as an `ExceptionGroup` (the `AggregateError` analogue). **The cancellation half is a separate, harder problem and `asyncio.shield` is not the answer** — see §5.3. Also: every task created here needs a **strong reference held somewhere named**, or CPython may collect it mid-flight; a fan-out into an unreferenced `gather` is a real bug, not a style point. |
| 5 | Reentrancy hardening (idempotent disposers, join-in-flight, setup barrier) | flags + `WeakMap` | flags + `weakref.WeakKeyDictionary` | **Easy** | Direct port; single-threaded event loop makes the reasoning identical. Caveat: bound methods are re-created per attribute access, so never use one as a weak key — key on the wrapper object. |
| 6 | `ctx.<key>` resolution | `Proxy` get/set/has traps | `__getattr__`, `__setattr__` | **Moderate** | Implement the fiber-chain walk in `__getattr__`. Keep undeclared-access rejection — it is a guarantee, not a nicety. **Correction to the first pass: `__getattr__` is *not* "cleaner than the JS trap's special-property dance" — it needs the same dance and more.** Python probes `__deepcopy__`, `__getstate__`, `__setstate__`, `__iter__`, `__len__`, `__await__`, `__fspath__` and friends by explicit `getattr`, and `copy`, `pickle`, `inspect` and Pydantic all do this routinely — so `__getattr__` must refuse dunders before touching resolution. Worse, there is a genuine dilemma: if the undeclared-access error does **not** subclass `AttributeError`, `hasattr`/`copy`/`pickle`/`inspect` break; if it **does**, a real undeclared access inside a `hasattr` probe is silently swallowed. Pick and document. Note also that **every name on the class shadows a service name forever**, since `__getattr__` fires only on a miss. Paper §6.4 names the **Python descriptor protocol (`__get__`)** as the intended runtime-mediation primitive for exactly this problem — an on-point passage the first pass of this dossier never cited. |
| 7 | Method-call re-tracing (a service method sees the *caller's* ctx) | `Proxy` apply/construct traps | — none — | **Hard — and this is a CORRECTNESS mechanism, not ergonomics** | **Re-filed.** The first pass called this "explicit beats invisible… removes a class of debugging", which reads as a comfort item. It is not. The trap is why `ctx.tools.register(...)` **unwinds with the consumer**: `EventsService.register` does `return this.ctx.fiber.effect(...)` where `this.ctx` has been re-traced to the *caller*, so the registration belongs to the calling fiber. Drop the trap without replacing it with a **stated law**, and the natural Python spelling — `self.ctx.effect(...)` inside a service method — binds the effect to the **provider's** fiber, so the registration **survives the consumer's unload** with nothing raised anywhere. That is a silent, systemic leak class voiding F1/F4/F5 for every registry-style service (`tools`, `llm` adapters, `skills`, `subagents`, `commands`, prompt sections — i.e. most of a harness). The replacement is still an explicit per-caller bound facade, but it must come with: two clearly named handles (`self.ctx` = provider's own resources, `self.caller` = the calling context), and a checked decorator on registration methods that asserts the effect it produced is owned by the caller's fiber. Without the check the mistake is undetectable. |
| 8 | Constructor return-override (Context→Proxy; Service→callable) | `class` may return another object | `__new__` (restricted) | **N/A — redesign** | Use a `create_root()` factory instead of a self-proxying constructor; use `__call__` for callable services. Python's `__call__` is a *better* fit than the JS trick. |
| 9 | Prototypal child contexts; isolate/intercept maps | `Object.create` chains as a persistent map | `collections.ChainMap` | **Easy-Moderate** | `ChainMap` gives layered lookup with own-vs-inherited distinction (`.maps[0]`) — exactly what `Object.hasOwn` is used for in `resolveConfig`'s intercept walk. Contexts themselves: a small object with a parent pointer, not a class hierarchy. |
| 10 | Collision-proof internal keys | `Symbol.for()` global registry | module-level sentinel objects **or** namespaced strings | **Easy** | Prefer namespaced strings (`"qma.effect"`). Sentinels do not survive two independent installs of the kernel; strings do — the same cross-copy property `Symbol.for` was chosen for. |
| 11 | Three plugin shapes (fn / class / `{apply}`) | structural typing | duck typing + `typing.Protocol` | **Easy** | `Protocol` is at its best on single-method contracts. Accept: a callable, a class, or an object/module with `apply`. Key the registry on the resolved callable's identity as Cordis does. |
| 12 | `@Inject` decorator | TC39 stage-3 decorators | native decorators | **Easy** | Direct. Replace the prototype-chain walk for inherited `inject` dicts with `__init_subclass__` merging a class attribute. |
| 13 | Config schema + defaults + fail-loud | Schemastery / StandardSchemaV1 | **Pydantic v2** | **Easy for validation, not for merge** | Export a `Config` model per plugin; kernel validates and fills defaults at load; invalid config fails the load loudly with an actionable message. **Correction: the intercept-chain merge is *not* `model_copy(update=…)`.** Two reasons. (a) The paper requires each key to define its **own** metadata monoid `(ℳ_k, ⊕_k, ε_k)` with a right-biased merge (Def 30/31); a single hardcoded shallow update over the ancestor chain is not that, and silently imposes last-wins on keys whose merge should be additive. (b) `model_copy(update=…)` is shallow **and, by Pydantic v2's documented behaviour, does not validate the updated fields** — so an intercept-merged config bypasses the very load-time validation this row is selling. Correct shape: fold the ancestor chain root-closest-first with the key's declared `merge`, then `Config.model_validate(merged)`. A key that declares no merge rule is simply not interceptable. |
| 14 | Typed `ctx.<key>` and typed events | **declaration merging** | — none — | **Hard — biggest gap** | Typed key objects. See §5.2. |
| 15 | Eager promises | promises start on creation | coroutines are lazy | **Moderate — pervasive** | Every implicit concurrency point in Alg 5 needs an explicit `create_task`; the paper's own footnote calls this out for Python. See §5.3. |
| 16 | Bail sentinel | `null`/`false`/`undefined` | — decide — | **Easy but one-way** | See §5.3. |
| 17 | HMR | Node ESM `loadCache` surgery | `sys.modules` + `importlib` | **Hard — different design** | See §5.4. |
| 18 | Plugin packaging & discovery | npm workspaces, `package.json` fields, `exports` | `pyproject.toml` + entry points | **Moderate** | See §5.5. |
| 19 | Browser-side plugin tree | a second Cordis instance in TS | — n/a — | **Strategic** | See §5.6. |

### 5.2 Typed events and typed services without declaration merging — the recommended design

**The gap.** In Cordis, any plugin anywhere writes `declare module '@deepseek-ai/cordis' { interface Context { metrics: MetricsService }; interface Events { 'my/event': (x: X) => void } }` and every downstream consumer, in a separately compiled package, gets full static typing on `ctx.metrics` and on `ctx.on('my/event', …)`. Zero runtime code. Python has nothing like this: type checkers do not merge classes or protocols across modules, and `.pyi` stubs do not compose that way either. Faithful translation is impossible.

**Options considered.** (1) A central registry module every plugin edits — **rejected**: defeats decentralisation, which is the point. (2) Untyped `getattr` plus casts at every call site — **rejected**: loses the property that made the TS ecosystem work. (3) **Compile-time metaprogramming — not evaluated in the first pass, and it deserves a row**, because paper §6.4 names it explicitly as a third family: metaprogramming "supplies both together", and compile-time metaprogramming (Rust proc macros, Scala macros, Zig `comptime`) "emits, per dependency, a typed declaration **together with** an accessor — dispensing with a general-purpose interception primitive". The Python-shaped member of that family is **generating a `.pyi` stub for `Context` at install time** from the installed plugins' `qma.keys` entry points. That is the closest structural analogue of TS declaration merging that Python actually admits: decentralised (each package declares its own keys), fully typed (`ctx.tools` type-checks), and with no central file any author edits. Costs: a step in the install path, staleness whenever a plugin is added without re-running it, and editor tooling that must find the generated stub. It should be weighed against option (4) below rather than skipped.

**Recommended — option (4): make the key a typed value, not a typed property.**

The declaring package exports objects; consumers import them (a type-only import at zero runtime cost if desired). The kernel's `on`/`get` are generic over those objects.

```python
# in the definition package qma_shell/keys.py
shell: ServiceKey["ShellService"] = service_key("shell")
pre_execute: Waterfall[[ToolExec], PreToolDecision] = event_key("tools/pre-execute")
```

```python
# in a consumer plugin
from qma_shell.keys import shell, pre_execute

inject = [shell]

def apply(ctx: Context, config: Config) -> None:
    svc = ctx.get(shell)                    # inferred: ShellService
    ctx.on(pre_execute, my_handler)         # handler signature checked
```

Why this is the right trade, not a consolation prize:

- **It type-checks fully**, with ordinary generics — no plugin, no merging, no central file.
- **It fixes a problem the paper leaves open.** §6.6 names *key collision* (two unrelated providers claiming the same string) and *interface drift* (a consumer compiled against an older interface still satisfies `k ∈ dom(σ)` and then breaks at runtime) as unsolved, with Cordis's current answer being npm **peer dependencies** — a mechanism Python does not have at all. A key object carries its declaring package's identity by construction: importing it *is* the version pin, and collision is impossible because identity is the object.
- **It matches the paper's own preferred direction.** §6.4 says the typing half of spatial composability is discharged by Haskell typeclasses, Rust traits, or TS module augmentation — all of which are "the provider extends the shared type from its own module." Typed key objects are the Python-shaped member of that family.
- **The string name survives** for config, telemetry, the generated catalog, and the `@mode` verifier — it is just no longer the type authority.

Keep `ctx.tools` attribute access as **untyped runtime sugar** via `__getattr__` (nice in a REPL, nice in a model-authored plugin), and make the key-object path the one that type-checks. Two doors, one of them checked.

For the durable session-log analogue of `SessionEventMap` merge-extension, the same technique applies: each package exports its own row model plus a registration call; the "union" is a runtime registry with a discriminated `type` field, and static typing comes from the row model the caller imported.

### 5.3 Async model

- **Laziness is the whole difference.** JS promises begin executing on creation; Python coroutines do nothing until awaited or scheduled. Every place Alg 5 writes `fiber.inertia ← create_task(reload(fiber))` must be a literal `asyncio.create_task`. The paper wrote `create_task` explicitly *for language independence* and footnotes exactly this. Audit every implicit-concurrency site: the fiber's inertia handle, the effect setup task, the dependent-drain fan-out, the child-fiber cascade.
- **Own the loop.** The kernel should be async-only, single-loop, with no synchronous public API that can be called from another thread. Cordis's reentrancy hardening assumes a single-threaded event loop; break that assumption and the `disposing`/`inFlight`/`setupBarrier` reasoning becomes wrong rather than merely incomplete. Thread and process work goes behind a service boundary (`ctx.subprocess`-shaped), never through the kernel.
- **Cancellation is a Python-specific hazard with no JS analogue.** `asyncio.CancelledError` can interrupt a disposer *mid-inverse*, leaving the accumulator partially applied — a state the calculus has no name for (there is no "recovery failed" outcome; L-Unload is total). Recommendation: run teardown under `asyncio.shield` or on a dedicated non-cancellable path, give it a configurable timeout, and define explicitly what a timed-out teardown leaves behind (see §6 Q6). This is the single highest-risk difference between a JS and a Python kernel and it is invisible until production.
- **`await ctx.plugin(X)`.** Cordis fakes it with a thenable wrapper over the fiber. Python has a first-class equivalent: implement `Fiber.__await__` to delegate to the settle-await. Cleaner than the original.
- **Bail semantics.** Cordis's `isBailed` treats only `null`/`false`/`undefined` as "no answer", so `0` and `''` stop a chain. Naively translated to `is not None`, `False` changes meaning. Recommendation: **do not translate the JS falsy set** — introduce an explicit sentinel (`NO_RESULT`) that a listener returns to pass, with every other value (including `None` and `False`) counting as an answer. It is unambiguous and it makes "a policy listener that legitimately decides *no*" expressible, which the JS semantics cannot do. It is also a one-way door: decide it before the first extension point ships.
- **Structured concurrency.** `anyio` buys trio compatibility and better cancellation scoping; plain `asyncio` buys fewer dependencies. Either is fine — but the teardown fan-out must be `gather(return_exceptions=True)` under both, for the reason in row 4 above.

### 5.4 HMR in Python

**What does not exist.** There is no Python equivalent of Node's ESM `loadCache` with per-module eviction that keeps object identity stable elsewhere in the graph. `importlib.reload()` re-runs a module's top-level code in the *same* module object and does not re-target existing references. Class identity changes across a reload, so `isinstance` across the plugin boundary breaks (Cordis papers over the equivalent with a custom `Symbol.hasInstance`; Python's analogue would be a metaclass `__instancecheck__`, or simply never using `isinstance` across the seam and relying on Protocols).

**What makes it tractable anyway.** Cordis's own discipline already forbids the two things that make Python reload dangerous: **cross-plugin value imports** (the browser side makes them a build error; the backside convention is "plugins cooperate only through services") and **module-level state** (everything lives in services, which the fiber owns). If QMA enforces both at packaging time, the remaining problem is just cache surgery, and `sys.modules` is a plain dict that can be snapshotted and restored — which is exactly the two-tier rollback Alg 10 needs.

**Recommended three-tier reload strategy:**

1. **Config-only change → no import at all.** `fiber.update(config)`, which lets the plugin's own `internal/update` hook patch in place. This is already the majority of edits in practice.
2. **Plugin module change → in-process fiber swap.** Record each plugin package's file set at load (via `importlib.metadata` + the module's `__file__`, plus a recorded import set if a custom loader/finder is installed). Watch with `watchfiles` (Rust-backed, the `chokidar` analogue). Run the same accept/decline fixpoint (Alg 8) over the recorded import graph, detect stale entries (Alg 9), snapshot the `sys.modules` entries for the accepted set, evict, re-import, dispose old fibers and construct new ones under the same Runtime/Entry — and on any failure restore `sys.modules` verbatim *and* re-register the previous plugin objects (Alg 10's second-order rollback). Everything in this tier is a straight port.
3. **Kernel or "externals" change → supervised process restart**, with session state having been persisted in a longer-lived dependency. This is not a defeat: it is exactly what the paper says happens anyway ("a component's own in-memory state does not survive a reload unless placed in a longer-lived dependency"), just at a coarser grain.

**Platform note, since this operator is on Windows:** the DSH fork had to add realpath-based canonicalisation to survive Windows short-name-vs-long-form path aliasing in its watcher, and a serialized per-config mutation queue to avoid a deadlock between rollback and teardown drain. Budget for both; do not assume the POSIX path story.

### 5.5 Plugin packaging

- **Entry shape** stays as Cordis defines it, since it is a faithful encoding of the calculus: `{id, name, config?, group?, disabled?, inject?, isolate?, intercept?}`, `id` hierarchical and used as the reconciliation key, `name` a module specifier — in Python, a dotted path (`qma_bash_local`) or `module:attr`.
- **Discovery** via `importlib.metadata.entry_points(group="qma.plugins")` for the installed-plugin catalog and the settings UI; direct import by specifier for the config tree. Both, not one: the config tree needs specifiers, the UI needs enumeration.
- **Metadata** in `pyproject.toml` under `[tool.qma]` — the analogue of the `dsh.client` field, carrying the client bundle path, `inject` topology, and the `immediately` flag for UI plugins.
- **Plugin surface**: a module exporting `name`, `inject`, `Config` (Pydantic model), and either `apply(ctx, config)` or a `Service` subclass. Drop the class-constructor-return shape entirely.
- **Vendoring posture.** DSH does not depend on an upstream Cordis package: it vendors `src/`, rescopes it, and maintains an 18-item exhaustive local-modification log re-applied by hand at each sync — including reentrancy hardening in `fiber.ts`, transactional loader reconciliation, and the Windows path fix. QMA should expect the same posture toward its own kernel: **own the framework layer**, do not treat it as a dependency to be upgraded.

### 5.6 The strategic one: two kernels or one?

QMA is Python backend + React/TypeScript UI. Cordis's UI extensibility works because the *same* kernel runs in the browser. Three options:

- **(a) Port the kernel to TypeScript as well** and run it in the browser. Two implementations of one contract; genuine client-side plugin composability; ongoing cost of keeping them in step. This is effectively what Cordis has — one implementation running in two places, which is cheaper than two implementations.
- **(b) Backend-declared UI only** — the backend registers slot descriptors, the browser is a thin renderer. Cheapest; loses the property that a UI feature can be a plugin with its own lifecycle, dependency ordering, and failure containment. DSH's "one crashing slot entry blacks out one card" behaviour is not reproducible this way.
- **(c) Run the browser tree on actual Cordis (TS, upstream or vendored) and the backend on the QMA Python kernel**, with an explicitly versioned wire contract between them.

**Recommendation: (c) for v1, with (a) as the considered end-state.** (c) gets a real, proven, plugin-composable UI immediately without blocking on a second kernel implementation, at the cost of owning two kernels whose semantics must not drift. Make the seam explicit and small — the boot manifest, the slot contract, and the transport — and write the contract down before either side ships. Do not drift into (b) by accident; it is a one-way loss of the property that makes the UI extensible at all.

---

## 6. Open questions the kernel contract must answer

Ordered by how expensive they are to change later.

**Q1 — Where does the dependent-drain wait live?** *(Verified divergence, §2 Stage 8.)* The paper puts it ahead of the entire recovery and argues that placing it inside one inverse leaves the rest unordered. The shipped code puts it inside the `provide` effect's disposer, so only the store deletion is ordered after the drain while the provider's other disposers race it. Which does QMA promise? The paper's version is stronger and matches the theorem; the code's version is what has actually been exercised in production. **Decide and write it into the contract, because plugin authors will build on whichever they observe.**

**Q2 — Is teardown LIFO, or LIFO-initiated and concurrent?** Theory says LIFO (Thm 16); the implementation gives LIFO initiation with concurrent completion across a fiber's top-level effects, and DSH covers the gap with an authoring rule ("keep order-dependent registrations inside one `ctx.effect`"). Is that rule QMA's contract too, or does QMA make fiber-level teardown sequential and pay the latency?

**Q3 — Is the inverse ever checked?** The runtime verifies nothing; `g(δ) ≃ γ` is an authorial obligation, and Thm 61 is where the calculus appeals to it. Does QMA ship a debug mode that at least snapshots `dom(σ)` around each effect and flags an inverse that did not restore the coeffect domain? That is cheap and catches the most common real failure (a registration that was not withdrawn). Value-level restoration is not checkable.

**Q4 — Typed identity: strings or key objects?** (§5.2.) This decides the entire public plugin API surface and cannot be changed after the first third-party plugin ships. Recommendation: key objects for the typed path, string names retained for config/catalog/telemetry, `__getattr__` sugar untyped.

**Q5 — Bail sentinel semantics.** Replicate JS's `null`/`false`/`undefined`, or an explicit `NO_RESULT`? One-way door; recommendation in §5.3.

**Q6 — What is the cancellation and teardown-failure contract?** If a teardown is cancelled or times out, what state is the fiber in? The calculus has no "recovery failed" outcome — L-Unload is total. QMA must invent one: a `POISONED` state that blocks reactivation and is reported, or a best-effort continue-and-log. Also: is teardown shielded from cancellation, and is there a timeout? This is the highest-risk Python-specific divergence.

**Q7 — Where is the system boundary drawn for an agent harness?** Per resource, is it reified as a coeffect (inside, revertible), withheld until commit, or compensated? Specific cases that must be answered by name: an **in-flight LLM stream** whose provider plugin is unloading — abort, drain, or orphan? A **subprocess or sandbox** the tool spawned. A **file written to the user's workspace**. A **message already sent to the user**. The paper's answer is that only the acquisition is revertible; QMA must publish the list.

**Q8 — Is self-registration bounded?** Progress (Thm 66) assumes a finite name set, delivered by the condition that no component can register, however indirectly, an instance of a component that registers one of its own. A harness where the model authors and mounts plugins at runtime can violate this trivially. What is the quota, the depth limit, and what happens when it is hit? DSH already ships the loaded-gun version of this: `ctx.dynamicCordisRunner` plus `cordis_define`/`cordis_run`/`cordis_inspect_*` tools let the *model* define, run, inspect and undefine plugins at runtime inside a vm sandbox. QMA will want that; it needs the bound first.

**Q9 — One kernel or two?** (§5.6.) Decide before the UI ships.

**Q10 — Do isolation realms ship in v1?** Very expensive to retrofit (two-layer resolution touches every lookup), and they are what makes per-session and per-agent service instances possible — which an agent SDK will want almost immediately. Recommendation: yes, in v1, even if the config surface for them lands later.

**Q11 — Does interception ship, and with what merge semantics per key?** It is the paper's answer to per-component access policy (§6.3), costs no reload, and perturbs no dependency graph. But each key must define its own metadata monoid `(ℳ_k, ⊕_k, ε_k)`, and the merge is right-biased so an enclosing context can override a component's own declaration. Defer or ship, but do not half-ship.

**Q12 — Does QMA adopt the two-bus split?** Live event bus for coordination, durable append-only session log for replayable truth, bridged by exactly one live emit. This is orthogonal to Cordis, is arguably the most consequential single borrowing from DSH for an agent SDK, and dictates the shape of persistence, replay, compaction and telemetry. It also needs the *surface* vs *log-only* row tagging and the `surfaceOp: append | replace(start,end)` mechanism that lets compaction shadow a range without rewriting history.

**Q13 — Versioning and key collision.** The paper leaves this open (§6.6) and names Cordis's current answer as npm peer dependencies — a mechanism Python does not have. Key namespacing, structural compatibility checks, or the key-object identity of Q4? Q4 answers it if chosen; if not chosen, this becomes an unbounded liability in an ecosystem of model-authored plugins.

**Q14 — Does the kernel expose an atomic `replace`?** In-place overwrite of a binding is invisible to dependents by design; replacement must be withdraw-then-install. Does QMA expose that pair as one guaranteed-atomic operation, or leave every author to discover the rule?

**Q15 — Who allocates entry ids when a model writes config?** Ids are hierarchical, `:`-joined, and are the reconciliation key — a changed id means a rebuild, not an update. A model editing config needs a stable id discipline, or every edit becomes a full rebuild of the subtree.

**Q16 — Does the harness enforce no-cross-plugin-value-imports on the Python side?** The browser side makes it a build error; the Python side has no equivalent enforcement point. Everything in §5.4 tier 2 depends on it. A load-time import audit is probably the answer.

---

## 7. Conflicts re-checked against original sources

Two conflicts existed between the four raw studies. Both were resolved against primary source.

**C1 — Is Koishi's web console a Cordis application in the browser?**
`study-ui-extensibility.md` §2 asserts (`[INFERENCE]`) that Koishi's client "is *not* itself a Cordis context" and is "a fairly conventional Vue/Vuex-ish SPA", making dsh's dual-tree design a generational leap. `study-cordiverse-paper.md` §5.3 states the opposite from the framework author's own paper.
**Resolved: the paper is correct; the note's inference is wrong.** Verified at `koishijs/webui`: `packages/client/client/context.ts` declares `export class Context extends cordis.Context`, uses `this.effect()` for registrations, and mounts `ActionService`/`I18nService`/`LoaderService`/`RouterService`/`SettingService`/`ThemeService` via `this.plugin()`; `packages/client/client/index.ts` has `export const root = new Context()`. The real DSH deltas are the shared vendored *loader* in the browser, per-plugin content-hashed bundles with a boot manifest, and React slots with `SlotMap` as the type authority — not the existence of a client-side Cordis tree. §3.1 above is written to the corrected version.

**C2 — Where does the dependent-drain wait sit during unload?**
`study-cordiverse-paper.md` §5.1.3 (Alg 5 line 25) places it ahead of the whole recovery and argues explicitly against placing it inside an individual inverse. `study-cordis-code.md` §2.3/§4 describes it inside `reflect.provide()`'s disposer, with `fiber._unload` fanning disposables out concurrently and no dependent wait.
**Resolved: both notes report their own source accurately; the paper and the shipped code genuinely differ.** Verified at `cordiverse/cordis@main`: `packages/core/src/fiber.ts` `_unload` does `await Promise.all(this._disposables.clear().map(...))` with per-disposable try/catch and no dependent wait; `packages/core/src/reflect.ts` `provide`'s disposer does `delete this.store[key]; const fibers = this.notify([name]); await Promise.allSettled(fibers.map(f => f.await())); delete this.ctx.fiber.store![name]`. Carried forward as **Q1**, the most consequential open question in this dossier.

**Minor, noted not escalated:** DSH's canonical dispatch table marks `waterfall` "Awaited? No" while its own examples `await` it — the dispatcher does not await, callers do. DSH counts four modes plus `bail`; the core counts four plus `waterfall`. Same five primitives.

---

## Appendix — source map

| Claim class | Read from |
|---|---|
| Formal core (§1.2) | `study-cordiverse-paper.md` — the paper's own Definitions/Theorems, numbered as in the paper |
| Runtime behaviour, exact semantics (§2) | `study-cordis-code.md` — `cordiverse/cordis@main` and vendored `cordis@4.0.0-rc.7` @ `56b3d4f7…` inside `deepseek-ai/deepseek-harness` |
| Applied conventions: seams, event catalog, extension-point selection, two-bus split (§2 Stages 0, 6) | `study-dsh-docs.md` — deepseek-harness.github.io `/en/` |
| UI mechanism (§3) | `study-ui-extensibility.md` + direct re-check of `koishijs/webui` client sources |
| Divergences (§2 Stage 8, §7) | direct fetch of `cordiverse/cordis@main` `fiber.ts` and `reflect.ts` |
