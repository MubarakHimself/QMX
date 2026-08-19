# QMA Kernel Contract — DRAFT v0

**Status: DRAFT. Nothing here is ratified.** This is the Step-1 output of the map: the extensibility dossier turned into a contract you can argue with. It gets bent against the Step-2 paper findings and then ratified with you in Step 3.

**How to read it.** Part A is written for you — no jargon, no code. Part B is the precise contract, in Python, for the documentation agent and the factory. Part C is the register of open decisions.

**How open decisions are marked.** Every choice that could genuinely go the other way carries a tag like **OPEN-07**, inline where it bites, and again in the register at the end with a draft position. If something is *not* tagged OPEN, I am claiming it is forced — either by the Cordiverse metatheory or by the acceptance test — and you should push back if you disagree, because that is where I could be wrong quietly.

**Source.** `research/qma-extensibility-dossier.md` and the four load-bearing raw studies under `research/raw/` (the folder holds six; two are parked and unrelated). Where this draft departs from Cordis, it says so.

**Revision note.** This draft has been through one adversarial review against the raw notes and the primary sources. Positions that **changed** as a result — read these first if you read the previous version: the bail sentinel (**OPEN-05**, reversed), the scope-filter default (**OPEN-19**, flipped), OPEN-17 (re-filed from ergonomics to a correctness law, K18), the typed-event-mode claim in B.1 (was false; the catalog verifier cannot be dropped), the optional-dependency path (B.2.1, now declared), the cancellation mechanism (B.3, `shield` was wrong), the interception-merge rule (B.4, monoid not `model_copy`), and the CI gate (B.8, structural not lexical). Five laws were added (K15–K19) and four decisions opened (OPEN-25 … OPEN-28).

---

# PART A — The plain version

## A.1 What the kernel is

The kernel is the smallest possible piece of QMA that everything else stands on. It is not the agent. It is not memory, tools, models, or the UI. It is the thing that knows how to **add a part and take a part away while the system is running**, and how to make sure taking a part away leaves nothing behind.

That is the whole job. If it does that job perfectly, everything else in QMA — every profile, every mind, every tool, the entire UI — is a part you plug in. If it does that job badly, every new agent is surgery on the core, and we have built another framework that fights us.

## A.2 The six things the kernel owns

Think of a workshop with a shared workbench.

**1. The workbench (the Context).** Every part gets handed the same workbench, and asks it for what it needs by name: "give me the shell", "give me the model". The workbench refuses to hand over anything the part did not declare it needed in advance. That refusal is not bureaucracy — it is how we can look at any part and know, before running it, exactly what it can touch. That is also our permission system for agent-written code, for free. **This holds only if there is no back door**: a part that merely *might* want the shell still has to say so ("optional: shell"), because one unchecked lookup anywhere makes the whole declared-capability list advisory rather than complete. The draft originally had exactly that back door and it has been closed — see §B.2.

**2. A capability on the workbench (a Service).** A part can put something on the workbench under a name, for everyone else to use. Putting it there is itself an undoable action, so it comes off the bench automatically when that part leaves. Nobody writes cleanup code for it.

**3. The parts themselves (Plugins).** A part is a folder or a file that says three things: my name, what I need, and what to do when you start me. It never says what order to load it in. It does not get to know.

**4. The announcement board (the event bus).** Parts talk to each other by announcing things, in exactly five ways, and no sixth way is ever invented: *shout it and move on*, *ask everyone at once*, *ask each in turn until someone answers*, *the same but answered on the spot without waiting*, and *wrap around it* — the last being how a part inserts itself into the middle of something it did not write (a permission check in front of every tool call, for instance). The five modes are closed. Nobody invents a private protocol. This is what makes hooks and policies ordinary plugins rather than a special subsystem. (One thing the five modes are *not* is a collector — "run everyone and merge what they all say". That shape exists in the original too, and it is built from a service registry, not from an event; see §B.6.)

**5. The undo ledger (effects and disposers).** Every single thing a part does to the system — register a tool, open a connection, listen to the board, start a child part — hands back the exact undo for that one thing, at the moment it does it. The kernel keeps them. Removing the part means running them backwards. **The part never writes a "cleanup" function.** Its cleanup is assembled from what it actually did. This is the one rule that makes hot-swapping safe rather than aspirational, and it is why a self-improving harness can rewrite one of its own capabilities without dying.

**6. The recipe reader (the loader).** A profile — a research scientist, a quant mind, a Delphi-like — is a folder with a recipe file listing which parts to mount and how to configure them. The loader reads it, mounts them, and when you edit the recipe it changes only what actually changed. No load order in the file. No boot sequence anywhere in QMA. A part whose dependency is not up simply waits; when the dependency arrives, it starts.

## A.3 The five things the kernel refuses to own

This list matters more than the previous one, because this is where frameworks rot.

- **Profiles and minds.** Not in the kernel. A profile is a folder plus a recipe; the thing that understands "profile" is a plugin.
- **Agent loops, models, tools, skills, memory.** Not in the kernel. All of them are parts on the workbench. The kernel has never heard of an LLM.
- **The UI.** Not in the kernel. The kernel exposes what is running and lets a bridge plugin publish it; the screen is composed of plugins on the other side of the wire.
- **Constants, policies, permissions.** Not in the kernel as concepts. The kernel gives the *mechanism* (declared needs, scoped overrides, interception) that a constants plugin and a permissions plugin are built from. Your scoped-constants idea lands as a plugin family, not a kernel feature — see **OPEN-18**.
- **Persistence and session history.** Not in the kernel. The kernel's event board is live and forgetful by design; a durable, replayable session log is a separate thing on a separate bus — **OPEN-12**, and I think it is the single most consequential borrowing after the kernel itself.

If you ever hear "we need to add X to the kernel so that Y works", that is the alarm. The correct answer is almost always a new plugin and possibly a new event.

## A.4 The one test this whole document exists to pass

> **ACCEPTANCE PROPERTY — creating a new harness, profile, or agent is plugin assembly on the kernel, never surgery on the core.**

Stated so it can be failed, not admired: **from the day the kernel is frozen, building an open-science researcher, a Delphi-like, and a quant mind must require zero commits to the kernel package** — only new plugin packages, new recipe rows, and new configuration. If any one of those three requires a kernel change, the kernel is wrong and we fix the kernel, not the profile.

Two corollaries you should hold me to:
- Swapping any capability's implementation (local shell → sandboxed shell, one model provider → another) is **a one-row edit in a recipe file**, not a code change anywhere.
- A part that fails to start **damages only itself**. Its siblings keep running, the failure is recorded against that part by name, and it does not silently retry.

## A.5 The UI, in one paragraph

Your requirement is "everything via the UI". That forces a specific shape. The Python backend runs the kernel and the plugin tree. The browser runs a **second** plugin tree — the same idea, different language — so that a UI feature is itself a plugin with its own lifecycle, its own dependencies, and its own failure containment (one broken card blacks out one card, not the app). Between them sits one explicitly versioned wire contract, and nothing else. The alternative — the backend describing screens and the browser dumbly rendering them — is cheaper this month and permanently gives up the property that makes the UI extensible. I recommend against it, and I have marked the choice **OPEN-09** because it is yours to make and it is expensive to reverse.

## A.6 The three honest limits

1. **The undo is a promise, not a check.** The kernel never verifies that a part's undo actually undoes. A sloppy inverse silently voids the guarantee for that part. We can add a cheap debug mode that catches the most common case — **OPEN-03**.
2. **Anything that left the process cannot be taken back.** We can undo "the tool is registered". We cannot undo "the tool emailed someone", "the file was written to your workspace", "the tokens were streamed to the user". What is reversible is the *handle*, never the *output*. For an agent harness that is the important sentence in this whole document — **OPEN-07** lists, resource by resource, what we promise.
3. **A part's own in-memory state does not survive a reload.** The kernel reverts and reapplies from clean. If state must survive, it has to live in something longer-lived. This is a real cost and there is no clever way around it at this layer.

   **Say this one out loud, because it collides with a standing idea of yours.** `map.md` records "reversible execution … so a mind that breaks mid-run is recoverable" as a Shepherd-level goal. The kernel as drafted **cannot deliver that**, and no amount of getting the kernel right will make it. What the kernel reverses is *what a part installed* — its registrations, its handles, its listeners. It does not reverse *where a run had got to*: the paper is explicit (§7.3) that layering DSU-style forward state migration onto revertible effects is future work, and by limit 2 above everything the run already emitted is gone regardless. Mid-run recoverability is therefore a **session-log / replay** property, not a kernel property, which is another reason **OPEN-12** (the durable replayable log) is load-bearing rather than a nice-to-have. **OPEN-24** compounds it: a mind in a remote sandbox is drafted as an opaque leaf, so even its registrations are outside the guarantee.

## A.7 What I actually need from you

Everything else in the register I can carry a draft position on. These four are yours:

- **OPEN-09** — one kernel or two (does the browser run a real plugin tree, or is the UI backend-declared)?
- **OPEN-07** — the emission list: for an in-flight model stream, a running sandbox, a written file, a sent message — abort, drain, orphan, or compensate?
- **OPEN-12** — do we adopt the two-bus split (live bus + durable replayable session log) now, which shapes persistence, replay, compaction and telemetry forever?
- **OPEN-08** — when a mind writes and mounts its own plugins, what is the quota and depth limit before we say no?

---

# PART B — The contract

Notation: Python 3.12+, `asyncio`, Pydantic v2 for config. `qma.kernel` is the kernel package. Laws are numbered **K1..K19** and are the things that may not be traded away without the guarantee collapsing; each cites its origin in the dossier (F-numbers) so the provenance survives. **K15–K19 were added after review**: they are preservation hypotheses or registration laws that the metatheory the rest of this contract invokes actually *requires*, and that the first draft silently omitted. A kernel generated from a K1–K14 table alone is unsound in five specific ways, each named below.

## B.0 Kernel laws (the non-negotiable core)

| # | Law | Origin |
|---|---|---|
| **K1** | Every context mutation flows through **one** primitive, `ctx.effect`. No registration path exists outside it. | F5 |
| **K2** | An effect returns its inverse **at the point of application**, chosen against the state it just produced. Inverses are never declared elsewhere. | F1 |
| **K3** | An effect body may be a generator; each yielded inverse is collected as produced, and the boundary between yields is the only place a load may be interrupted and partially rolled back. | F3 |
| **K4** | Providing a service **is an effect**. There is no `register_service` outside `effect`. | F4 |
| **K5** | A plugin declares the services it requires; it does not run until all are present, is torn down when any leaves, and is restarted when they return. It never expresses load order. | F6 |
| **K6** | The lifecycle compares a **committed view** against a **target view**, keyed on **provider identity** (a fresh, never-reused uid), not on value. In-place overwrite of a binding is therefore invisible; replacement is withdraw-then-install. | F7 |
| **K7** | A fiber that is loading or unloading **provides nothing**. Withdrawal becomes visible to dependents one step before any inverse runs. | F8 |
| **K8** | Deciding to deactivate and actually unloading are two steps; the second is guarded until no other installed fiber's committed view still names this fiber. A consumer can therefore read its dependency throughout its own teardown. | F9 |
| **K9** | Attribute/key access resolves against the **accessing fiber's committed view**, and undeclared access is rejected. This is simultaneously the correctness mechanism and the capability mechanism. | F7/§5.1.4 |
| **K10** | Once an iteration is launched it lands; a target that changes mid-flight cannot abort the in-flight step. The fiber lands, then deactivates. | F11 |
| **K11** | Failure is recorded on the fiber, never propagated. A failed fiber has installed nothing, blocks nothing, does not auto-retry against an unchanged environment, and leaves siblings running. | F12 |
| **K12** | Order-sensitive things live in **declared dependencies**, not in effects. Within one component, order comes from the accumulator (LIFO); across components, from a declared dependency. **A key whose value is an ordered chain is not commutative, and the obligation to state its ordering law falls on the key's provider** — see K17. | F10 |
| **K13** | The system boundary is where the guarantee stops. Acquisition is revertible; emission is not. | F14 |
| **K14** | The kernel owns no domain concept. It has never heard of an agent, a model, a tool, a profile, a session, or a screen. | acceptance property |
| **K15** | **Provisions are disjoint.** No two installed fibers may provide the same key in the same realm. A mount whose declared `provide` set intersects an installed fiber's is **refused at mount**, loudly, by name — it is not a last-writer-wins overwrite and not a warning. | paper Def 58(2), imposed at O-Insert's last premise |
| **K16** | **Confinement.** A fiber's effect function may read its own table and the tables of exactly the keys it declared — nothing else, and in particular **no other fiber's control fields** (state, epoch, committed view, error). Introspection of the fiber tree is therefore not something a plugin does directly; it is a kernel-provided capability that a plugin must declare like any other (see §B.9). | paper Def 48 |
| **K17** | **Commutativity is an obligation on the provider of a key**, not on its consumers. A key whose value is a table of independently added and removed entries is commutative; a key whose value is an **ordered chain** (a middleware list, a pre-execute pipeline) is not, and its provider must publish how order is determined and what is order-independent. An extension point that cannot state this is not shippable. | paper Def 39 / Thm 42 / §3.3.2 |
| **K18** | **Registration is attributed to the caller.** When a service method registers something on a caller's behalf (`ctx.require(tools).register(...)`), the resulting effect binds to the **calling fiber**, not the providing fiber, and unwinds with the caller. A service author who writes `self.ctx.effect(...)` inside such a method has written a leak. | Cordis Proxy `apply` trap (study-cordis-code §7 row 1, §3 `register`) |
| **K19** | **The inverse of a registration is retirement, not removal.** Retiring is unconditional and therefore always applicable wherever the accumulator reaches it; removal carries premises (children first, nothing still relying) and can fail. A retired entry stays in the registry as a vestigial record until removal is separately safe, and a fiber uid is only reissuable because the L-Unload guard already prevents any stale committed view from naming it. | paper Def 47, Lemma 57, Thm 59 |

Everything in B.1–B.7 is an expression of K1–K19. Everything in B.8 is explicitly outside them.

## B.1 Typed identity — keys, not attributes

Cordis gets typed `ctx.<key>` and typed events from TypeScript declaration merging, with zero runtime code. **Python has no equivalent and no near-equivalent.** The replacement, and it is a better fit than the original:

```python
# qma/kernel/keys.py
@dataclass(frozen=True, slots=True)
class ServiceKey(Generic[T]):
    name: str            # "shell" — used by config, telemetry, catalogs, the UI
    package: str         # "qma_shell" — declaring package identity
    def __repr__(self) -> str: return f"<service {self.package}:{self.name}>"

def service_key(name: str, package: str) -> ServiceKey[Any]: ...
```

The **object is the identity**; the string is a label. A definition package exports its keys; consumers import them. Consequences, all of them wanted:

- Full static typing with ordinary generics — no plugin, no central registry file, no merging.
- **Name collision becomes impossible by construction** (two packages cannot own the same object), which closes the specific problem the Cordiverse paper leaves open (§6.6 *key collision*: two unrelated packages both naming their key `shell`) and answers with npm peer dependencies — a mechanism Python does not have. **This is not the same as provision collision.** Two plugins both providing *the same key object* is still possible and is a different failure; it is refused at mount by **K15**. Do not let the two get conflated in the docs: the key-object design solves naming, K15 solves provision.
- **Importing the key is the version pin.** Interface drift becomes an import error rather than a runtime surprise.
- **The string layer does not disappear, and it is where the collision problem comes back.** Config, telemetry, the UI, and `Entry.inject` / `Entry.isolate` are all strings (§B.7). The loader therefore needs a **string → key-object resolver**, and that resolver is a global namespace with exactly the collision surface B.1 claims to have eliminated. Specified, not hand-waved: strings in config are **package-qualified** (`qma_notes:notes`), resolved through a `qma.keys` entry-point group that maps qualified name → key object; the resolver imports **only the declaring package**, lazily, on first reference, never the whole installed set; an unqualified string is accepted only when exactly one installed package declares it and is an **error, not a guess**, when two do. Unqualified-name ambiguity is thus a load-time failure with both candidates named.

`ctx.<name>` attribute access still exists as **untyped runtime sugar** (`__getattr__`), enforcing exactly the same declaration check — pleasant in a REPL and for model-authored plugins. Two doors, one of which type-checks. **OPEN-04.**

Event keys carry their **dispatch mode in the type**. The first draft wrote this as five aliases, which does not work and must not be shipped that way:

```python
# WRONG — this is what the first draft specified, and it type-checks nothing.
Emit      = EventKey[P, None]
Parallel  = EventKey[P, None]           # ... identical to Emit
Serial    = EventKey[P, R]
Bail      = EventKey[P, R]              # ... identical to Serial
Waterfall = EventKey[P, R]              # ... identical again
```

A Python type alias is **not a distinct type**. `Emit` and `Parallel` are the same type to every checker; `Serial`, `Bail` and `Waterfall` are the same type as each other. Dispatching an emit key through `ctx.serial` would type-check cleanly. The claim "a wrong-mode dispatch is a type error" was false as written, and since it was the stated reason DSH's `@mode` tag plus `verify-cordis-catalog` script could be dropped, **that script cannot be dropped on this basis**. The correction, in two parts:

```python
# qma/kernel/keys.py — five DISTINCT generic classes, not aliases.
class EmitKey(Generic[P]):      __slots__ = ("name", "package")   # fire and forget
class ParallelKey(Generic[P]):  ...                               # all at once, awaited, errors aggregated
class SerialKey(Generic[P, R]): ...                               # in order, awaited, stops at first answer
class BailKey(Generic[P, R]):   ...                               # same, synchronous
class WaterfallKey(Generic[P, R]): ...                            # around-middleware

pre_execute: WaterfallKey[[ToolExec], PreToolDecision] = waterfall_key("tools/pre-execute", __package__)
```

1. **Distinct classes, one per mode.** `ctx.emit` accepts only `EmitKey`, `ctx.waterfall` only `WaterfallKey`, and so on. *Now* a wrong-mode dispatch is a type error. Five constructor functions (`emit_key`, `parallel_key`, `serial_key`, `bail_key`, `waterfall_key`) replace the single `event_key`, so the mode is chosen once, at declaration.
2. **`WaterfallKey` must encode `next`.** A waterfall listener's signature is not `P` — it is `(*P, next: Callable[[], Awaitable[R]]) -> Awaitable[R]`. `ctx.on(waterfall_key, handler)` is typed against *that* shape, not against `P`. The first draft's `Waterfall[[ToolExec], PreToolDecision]` would have accepted a plain `(ToolExec) -> PreToolDecision` listener that silently vetoes everything downstream by never calling `next`. This is the same class of bug as the bail sentinel below.

**Keep the catalog verifier anyway.** Even with distinct classes, the type system cannot check what the mode *means* (that an `emit` listener is not doing work whose result matters, that a `waterfall` listener actually calls `next` on its pass path). Port DSH's generator + `verify-catalog` script: it is cheap, it is the only machine check on the applied convention in §B.6, and it is the thing that keeps the event catalog honest for a documentation agent. **This is a reversal of the first draft's position, which offered typed keys as the replacement for it.**

## B.2 Context — the container

```python
class Context:
    fiber: Fiber
    root: Context

    # --- service access -------------------------------------------------
    def require(self, key: ServiceKey[T]) -> T      # required-declared: enforced, raises
    def find(self, key: ServiceKey[T]) -> T | None  # optional-DECLARED: None if provider down
    def get(self, key: ServiceKey[T]) -> T | None   # unchecked store read — ROOT FIBER ONLY
    def __getattr__(self, name: str) -> Any         # untyped sugar, same enforcement as require

    # --- registration (all are effects) ---------------------------------
    def effect(self, body: EffectBody, label: str | None = None) -> Disposer
    def provide(self, key: ServiceKey[T], value: T,
                check: Callable[[], bool] | None = None) -> Disposer
    def on(self, key: AnyEventKey, handler: Callable, *, prepend: bool = False,
           scope_global: bool = False) -> Disposer
    def once(self, key: AnyEventKey, handler: Callable) -> Disposer
    def plugin(self, plugin: Plugin, config: Any = None) -> Fiber
    def inject(self, deps: Sequence[ServiceKey], fn: Callable[[Context], Any]) -> Fiber

    # --- dispatch --------------------------------------------------------
    def emit(self, key: EmitKey[P], *args) -> None
    async def parallel(self, key: ParallelKey[P], *args) -> None
    async def serial(self, key: SerialKey[P, R], *args) -> R | NoResult
    def bail(self, key: BailKey[P, R], *args) -> R | NoResult
    async def waterfall(self, key: WaterfallKey[P, R], *args,
                        terminal: Callable[..., Awaitable[R]]) -> R

    # --- derivation -------------------------------------------------------
    def extend(self, **meta) -> Context
    def isolate(self, key: ServiceKey, label: str | object | None = None) -> Context
    def intercept(self, key: ServiceKey, config: Any) -> Context
```

### B.2.1 The three access paths, and why there is no fourth

The first draft had `get` (enforcing) and `find` ("optional: never raises"). Both halves were wrong.

**The names were inverted against both primary sources.** Paper §5.1.4 is explicit: "`ctx.get(key)` is a **lookup against the store** that returns the bound value or nothing and **never fails**, whereas the proxy resolves against the accessing fiber's own view and enforces the coeffect specification `d` at the point of use." DSH's service page says the same in applied form: optional dependency = omit `inject`, call `ctx.get(...)`, get `undefined` if absent. The enforcing path is the *attribute* path; `get` is the unchecked one. The draft had it exactly backwards, which would have made every QMA plugin author who has read either source write the wrong call.

**More seriously, the draft kept a universal undeclared-read path and simultaneously sold the capability set as complete.** Those cannot both hold. Note precisely what the paper claims in §6.3 — "the complete set of **proxy-mediated** capabilities a component requires is known before it runs". The qualifier is doing all the work: the paper is claiming completeness *of the mediated surface*, not of the component's total reach, and the unchecked `ctx.get` sits outside it. The draft dropped the qualifier and inherited an unsound claim. And in Cordis the unchecked read is not even transparently reachable from a plugin: `reflect.ts`'s get trap falls back to the non-strict `reflect.get(prop, false)` **only when `ctx.fiber.runtime` is falsy** — i.e. only at the root fiber. Plugin contexts always go down the strict waterfall.

QMA closes the hole rather than inheriting the qualifier, because "the capability list of an agent-written plugin is complete and reviewable before it runs" is the property A.2 is selling and **OPEN-08** is bounding. Three paths, and the set is closed:

| call | requires | when the provider is down | when undeclared |
|---|---|---|---|
| `ctx.require(key)` | `key ∈ inject` | cannot happen (fiber is not ACTIVE without it) | `UndeclaredAccess` |
| `ctx.find(key)` | `key ∈ optional` | returns `None` | `UndeclaredAccess` |
| `ctx.get(key)` | caller is the **root** fiber | returns `None` | `RootOnlyAccess` from any plugin fiber |

So **optional dependencies are declared** — in a second list, `optional`, which does *not* gate activation and does *not* enter the epoch, but does enter the reviewable capability set. This is the one substantive divergence from Cordis in B.2 and it is deliberate: an undeclared optional read is exactly the hole through which an agent-written plugin reaches a capability nobody approved. `ctx.get` survives for the kernel, the loader, the introspection bridge and the REPL, all of which run at root.

**OPEN-25** covers the naming only (`require`/`find`/`get` versus keeping `get` enforcing and accepting the divergence from both sources). The substance — no undeclared read from a plugin fiber — is not open; it is what makes A.2 item 1 true.

### B.2.2 Resolution (K9), as the algorithm the kernel must implement

First, the three structures the loop touches, because the first draft named all three and defined none, and their relationship is where a code-generating factory will get K8 wrong.

```python
@dataclass(frozen=True, slots=True)
class Binding:
    uid: str            # the PROVIDER FIBER's uid — fresh, never reused. This is the identity K6 compares.
    value: Any          # the provided object. This is what a lookup returns.
    provider: Fiber

# 1. The kernel-wide store: one entry per (realm, key). Written by provide(), read by _refresh.
Store = dict[tuple[Realm, ServiceKey], Binding]

# 2. Each fiber's COMMITTED VIEW: the snapshot taken when this fiber last activated.
#    Maps key -> Binding. `uid` is the identity K6/F7 compares (the paper's ω : d -> 𝔑 is
#    the uid projection of this map); `value` is what a read returns. They are the same map
#    read two ways, which is what the first draft's "returns fiber.committed[key] as the VALUE
#    while K6 says it maps to identity" contradiction was.
Fiber.committed: dict[ServiceKey, Binding]

# 3. Realms: per-context, per-key. ChainMap-layered, inherited by derivation.
Context._realms: ChainMap[ServiceKey, Realm]
```

Three rules bind them, and none of them were stated before:

- **`provide()` writes to BOTH.** It writes `store[(realm, key)]` *and* `provider_fiber.committed[key]`. Writing the provider's own committed view is what lets **a provider read the service it provides** — without it a provider's own key is in no view it can reach and `self.require(self.key)` raises, which is absurd and which the first draft's algorithm did produce.
- **`_refresh()` reads the store** (to compute the epoch from provider uids). **`_resolve()` reads committed views** (to answer a lookup). A fiber's committed view is refreshed from the store only at activation and on an explicit per-key notify — never continuously. That gap *is* K8: a departing provider is already gone from the store while its consumers' committed views still name it.
- **K8's "delete from the provider's own view last"** now refers to something real: `provide()`'s disposer deletes `store[(realm, key)]`, notifies, awaits every affected fiber settling, and **only then** deletes `provider_fiber.committed[key]` — so the provider can still read its own service throughout its dependents' teardown.

```python
async def _resolve(ctx: Context, key: ServiceKey) -> Any:
    # Every public read is mediated. The waterfall is the interception point (B.6.1);
    # `_walk` is its terminal step. Do not inline the terminal and delete the waterfall —
    # per-mind attribution, quota and record/replay are built here and nowhere else.
    return await ctx.waterfall(internal_get, ctx, key, terminal=lambda: _walk(ctx, key))

def _walk(ctx: Context, key: ServiceKey) -> Any:
    realm = ctx._realms[key]                       # this context's realm for key
    fiber = ctx.fiber
    while True:
        binding = fiber.committed.get(key)         # committed view, NOT the store
        if binding is not None:
            return _bind_to_caller(binding.value, ctx)   # K18 — see B.2.3
        if key in fiber.inject or key in fiber.optional:
            raise InactiveAccess(key, fiber)       # declared but provider not up
        if fiber.parent is None:
            raise UndeclaredAccess(key, fiber)     # reached root without declaration
        if fiber.parent.ctx._realms[key] is not realm:
            raise IsolationBoundary(key, fiber)    # crossed an isolate() wall
        fiber = fiber.parent.ctx.fiber
```

Four properties of this loop are load-bearing and must not be "simplified":
1. It reads the **committed view**, not the store — which is what keeps a dependency readable to a consumer whose teardown that very dependency triggered (K8).
2. Undeclared access **raises, on every path** (B.2.1). `inject`/`optional` is a capability request; this loop is the capability mediator; and because declarations are static, **the complete capability set of any plugin — including one an agent just wrote — is knowable before it runs, and therefore reviewable and approvable at load time.** That sentence is only true because B.2.1 closed the unchecked path; if `find` is ever reverted to "never raises", strike the sentence at the same time.
3. The isolation check is per-key, at each hop, and is what makes per-profile and per-session service instances possible.
4. **The waterfall wrapper is not optional decoration.** It is the only place a policy plugin can observe or intercept *every* service access made by an untrusted mind. See B.2.4.

### B.2.3 Caller-attributed registration (K18) — a correctness mechanism, not ergonomics

**This was the single worst misfiling in the first draft.** OPEN-17 read "Cordis re-traces every method call through a `Proxy.apply` trap; Python has no such trap; use an explicit bound facade — explicit beats invisible, and it removes a class of debugging." That framing treats the trap as ergonomics. It is not. It is load-bearing for K1/K2 on **every registry-style service in the system**.

What the trap actually does (study-cordis-code §7 row 1; `events.ts` `register`):

```ts
register(label, hooks, callback, options) {
  return this.ctx.fiber.effect(() => { hooks.push(...); return () => this.unregister(...) }, label)
}
```

`this.ctx` there is **not the events service's own context** — the `apply` trap re-traced the method to the caller, so `this.ctx.fiber` is the *consumer's* fiber and the registration unwinds with the consumer. That is why `ctx.tools.register(tool)` in B.10 Step 3 makes the tool disappear when the *tool plugin* unloads, and not when the *tools service* unloads. B.10 Step 3's comment ("`register` is itself an effect → the tool disappears when this plugin unloads") was silently depending on behaviour this contract never stated.

Drop the trap without replacing it with a law and the natural Python spelling of the same method —

```python
class ToolsService(Service):
    def register(self, tool: ToolDef) -> Disposer:
        return self.ctx.effect(...)      # ← WRONG: binds to the PROVIDER's fiber
```

— binds the effect to the tools service's fiber. The tool then **survives the consumer's unload**, and keeps executing against a torn-down plugin's closures. Nothing raises. This is a silent, systemic leak class that voids K1 and K2 for every registry-style service (`tools`, `llm` adapters, `skills`, `subagents`, `commands`, `systemPrompt` sections — i.e. most of the harness), and no amount of care about `ctx.effect` elsewhere catches it.

**The law is K18**, and it is discharged mechanically rather than by author discipline:

- `_bind_to_caller(value, ctx)` in `_walk` returns a **per-caller bound facade** — a small wrapper holding `(service, caller_ctx)`, generated once per (service, fiber) pair and cached on the fiber, whose methods receive the caller's context.
- Inside a service method, `self.ctx` is **the provider's own context** (correct for the service's own resources: its connection pool, its background task) and **`self.caller`** is the calling fiber's context (correct for anything registered on the caller's behalf). Two names, one obvious rule: *if the thing you are registering should die when the caller dies, use `self.caller.effect`; if it should die when you die, use `self.ctx.effect`.*
- The kernel makes the wrong choice **detectable, not just documented**: a registry-style service declares its registration methods with `@registers_for_caller`, which asserts at call time that the effect it created is owned by `self.caller.fiber` and raises `ProviderBoundRegistration` naming the method if it is not. This is the same shape as OPEN-03's debug mode and is worth having on by default, since the failure is otherwise invisible.

**OPEN-17** is therefore re-scoped: not "do we emulate the trap" (we do not) but "explicit two-name facade with a checked decorator, versus a descriptor that rewrites `self.ctx` per call". The first is honest and greppable; the second is closer to Cordis and closer to invisible. Either way **the law is not optional**, and this is no longer an ergonomics item.

### B.2.4 There is an interception point, and it is `internal/*`

The first draft presented `_resolve` as "verbatim as the algorithm the kernel must implement" with no hook anywhere, and §B.6 defined no internal event surface at all. That is a hole big enough to fail the acceptance property on its own. The original has four:

| internal event | mode | what it wraps |
|---|---|---|
| `internal/get` | waterfall | **every property/service read** — the resolution waterfall above, whose terminal step is `_walk` |
| `internal/set` | waterfall | every write to a provided binding (and enforces that only the providing fiber may write) |
| `internal/listener` | bail | runs **before** a listener is registered and may replace the registration outcome entirely |
| `internal/dispatch` | emit | every public dispatch self-reports `(mode, name, args, scope)` |

Plus the lifecycle emissions `internal/plugin`, `internal/status`, `internal/service`, and the `internal/update` waterfall (§B.7 fiber API).

**Why this is not a nice-to-have.** The counterexample capability is the paper's own §6.3 story and DSH's `llm-replay` generalised: *per-mind attribution, quota, and record/replay over every service call an untrusted mind makes.* Under the first draft that requires editing `_resolve` inside `qma.kernel` — core surgery, which is precisely what A.4 says must never be needed. With `internal/get` it is an ordinary plugin. Same for a read-audit log, a per-mind rate limiter, and a "which capability did this mind actually touch" report — none of which any capability's own pre-execute waterfall can provide, because a waterfall only exists where the capability's author chose to publish one, and `ctx.llm` publishing one does not help you observe `ctx.fs`.

Two consequences the contract must carry:

- **`internal/*` ships in v1** and is *not* gated on **OPEN-11**. Interception in the OPEN-11 sense is the ι-metadata chain (per-key merge monoids); the internal event surface is a different mechanism with a different cost. B.8's claim that permissions live on "pre-execute waterfalls + monotonic guards + interception metadata" was unsound while the first two are per-capability opt-ins and the third was deferred; with `internal/get` the claim holds.
- `internal/*` dispatches **do not recurse**: an `internal/`-prefixed name never self-reports through `internal/dispatch`, and `_walk` never re-enters `_resolve`. Listener registration on `internal/get` is restricted to fibers holding the `intercept_reads` capability, which is itself a declared key — otherwise the interception point is a capability-bypass by construction.

### B.2.5 Reserved names, and why `logger` is not one of them

`__getattr__` fires **only on a miss**. Every name that exists on `Context` is therefore permanently unavailable as a service name. The first draft declared `logger: Logger` on the class body, which quietly made `logger` a kernel concept and a domain leak in one line — and **B.8's grep gate does not catch it**, because `logger` is not on the grep list.

Concretely what that costs: routing each mind's logs into that mind's own session log or sandbox is a **provider swap on a `logging` seam** — a one-row recipe edit under A.4 corollary 1. With `logger` fixed on `Context`, it is a kernel commit. In Cordis and DSH the ambient handles are not sacred in this way: `ctx.timer`, `ctx.loader`, `ctx.hmr` are plugin-provided services (study-dsh-docs §9), and even the logger console is a **vendored plugin** (`logger-console`), not core.

The contract:

- **`Context` declares exactly two data attributes — `fiber` and `root` — plus the kernel methods listed above.** Nothing else, ever. `logger` is deleted from the class body and becomes an ordinary `ServiceKey` (`qma_logging:logger`) provided by a logging plugin, injected like anything else. The kernel's own diagnostics use the stdlib `logging` module directly, which is not a context attribute at all.
- The **reserved-name set is finite, published, frozen at v1, and CI-checked**: `fiber`, `root`, `require`, `find`, `get`, `effect`, `provide`, `on`, `once`, `plugin`, `inject`, `emit`, `parallel`, `serial`, `bail`, `waterfall`, `extend`, `isolate`, `intercept`. A `service_key()` call naming any of them fails at import. Adding a name to this set after v1 is a breaking change to every plugin in the ecosystem and is treated as one.
- **`__getattr__` is not the free lunch the dossier's §5.1 row 6 claims** ("cleaner than the JS trap's special-property dance"). It needs the same dance and more: Python probes `__deepcopy__`, `__getstate__`, `__setstate__`, `__iter__`, `__len__`, `__await__`, `__fspath__` and friends by explicit `getattr`, and Pydantic, `copy`, `pickle` and `inspect` all do this routinely. The rule: **`__getattr__` refuses any dunder immediately** (raise `AttributeError` before touching resolution), and `UndeclaredAccess` **subclasses `AttributeError`** so `hasattr`/`copy`/`inspect` behave — with the accepted cost, stated here so it is not discovered later, that a genuine undeclared access inside a `hasattr` probe is swallowed. That is why the typed `require(key)` path is the one the SDK docs lead with and the attribute path is sugar.

**Derived contexts** are a small object with a parent pointer and `collections.ChainMap`-layered realm/intercept maps — never a class hierarchy, never a deep copy.

## B.3 Effects and disposers — the one primitive (K1–K3)

```python
# What a plugin AUTHOR may return as an inverse — sync or async, both accepted:
RawDisposer = Callable[[], None] | Callable[[], Awaitable[None]]

# What ctx.effect() HANDS BACK. Always awaitable. This distinction is not cosmetic:
class Disposer(Protocol):
    def __call__(self) -> Awaitable[None]: ...
    def __await__(self): ...          # `await disposer` == "did this effect finish loading?"

EffectBody = (
      Callable[[], RawDisposer | None]                  # sync setup
    | Callable[[], Awaitable[RawDisposer | None]]        # async setup
    | Callable[[], Iterator[RawDisposer]]                # generator: yields inverses as it goes
    | Callable[[], AsyncIterator[RawDisposer]]           # async generator: same, awaited
)

disposer = ctx.effect(body, label="my-thing")
await disposer()          # idempotent, re-entrant-safe, joins an in-flight disposal
```

**Why two types.** The first draft wrote `Disposer = Callable[[], None | Awaitable[None]]` and then documented `await disposer()`. In Python that is a `TypeError` the moment the author's inverse is a plain sync function, because `await None` raises. It works in Cordis only because `await undefined` is legal JS. The kernel therefore **wraps every raw disposer** so the public handle is uniformly awaitable — which is also what Cordis does for a different reason (`wrapper.then`, fiber.ts:555-559, which the first draft dropped along with it). One call form, `await disposer()`, everywhere; the sync/async choice is the author's private business.

Required behaviours, each of which exists because omitting it broke something in the original:

- The wrapper disposer is pushed onto the fiber's list **before** the body runs, so a re-entrant unload triggered from inside setup can already see and await it.
- Generator bodies are drained one step at a time, and **the fiber's epoch is re-checked at every yield boundary**; a stale generator stops draining mid-flight (K3, K10). **When it stops, the kernel must `await iter.aclose()` on the abandoned async generator** (and `iter.close()` on a sync one) before returning. Simply dropping the reference — which is what a literal port of the JS "break out of the loop" does — defers `GeneratorExit` to garbage collection or to `loop.shutdown_asyncgens()`, so any `try/finally` in the plugin's setup body runs at an arbitrary later time, **possibly after the fiber is DISPOSED**. That is a second, untracked teardown path outside the accumulator, and it is exactly the state the calculus has no name for. The dossier grades generator effects "Easy — direct port"; this is the part that is not.
- A **synchronous setup failure** rolls back whatever partial disposers were collected and re-raises. `effect()` never returns a wrapper for a failed setup.
- Calling a disposer **while setup is still running** waits for setup, then disposes.
- Disposers are idempotent; a second caller joins the in-flight cleanup via a `weakref.WeakKeyDictionary` side table rather than double-disposing. (Never key that table on a bound method — Python re-creates those per attribute access. Key on the wrapper object.)
- Effect creation is **rejected** while the fiber is UNLOADING.
- `ctx.effect` bodies register nested effects, forming an inspectable tree (`fiber.effects()`) — this is what the UI renders as "what does this plugin currently hold".

**Teardown ordering.** Within one `effect()` call, nested disposers run strictly **LIFO and sequentially**. Across a fiber's top-level effects, Cordis runs them **concurrently** with per-disposer error containment (`asyncio.gather(..., return_exceptions=True)` — explicitly *not* `TaskGroup`, whose cancel-siblings-on-error semantics directly contradict "one broken teardown must not stop the others"). Whether QMA keeps that, or pays latency for fiber-level sequential teardown, is **OPEN-02**; whichever we choose becomes a written authoring rule, because plugin authors will build on whichever they observe.

**Where the dependent-drain wait lives** is the single most consequential mechanical decision in the kernel and the paper and the shipped code genuinely disagree — **OPEN-01**.

**Cancellation** has no JS analogue and is the highest-risk Python-specific divergence: `asyncio.CancelledError` can interrupt a disposer mid-inverse, leaving the accumulator partially applied — a state the calculus has no name for, because unloading is total there.

**`asyncio.shield` does not do what this needs, and the first draft specified it anyway.** `shield` protects the *inner* task from cancellation, but the **awaiter still receives `CancelledError`** and unblocks. So the caller waiting on the K8 dependent-drain gets cancelled, abandons the wait, and proceeds — while the shielded inverse is still running, detached, on a fiber the caller now believes is torn down. That is precisely the partially-applied accumulator the register says it is preventing, reached by a different road. The correct shape:

```python
# Teardown runs as its own task on the fiber, never inline on a cancellable caller.
fiber._teardown_task = asyncio.create_task(_run_accumulator(fiber))   # strong ref: see B.5
# Callers join it UNCANCELLABLY:
await asyncio.wait({fiber._teardown_task}, timeout=cfg.teardown_timeout)
# `wait` returns rather than raising on cancellation of the awaiter, and never
# propagates cancellation INTO the task it is waiting on. `shield` does neither.
```

A cancelled *awaiter* therefore stops waiting without touching the inverse; a timed-out *teardown* puts the fiber into a terminal `POISONED` state that blocks reactivation and is reported by name in the UI. **OPEN-06** now decides the timeout and what a timed-out teardown is *presumed* to have left behind — not the shielding mechanism, which is settled above.

## B.4 Service — a capability on the workbench (K4)

```python
class Service(Generic[T]):
    key: ClassVar[ServiceKey]                       # what this service provides
    inject: ClassVar[Sequence[ServiceKey]] = ()     # what it requires
    Config: ClassVar[type[BaseModel] | None] = None

    def __init__(self, ctx: Context, config: Any = None) -> None:
        self.ctx = ctx
        self.config = config
        ctx.provide(self.key, self, check=self.available)   # ← self-registration IS an effect

    def available(self) -> bool:                    # optional dynamic gate
        return True

    async def start(self) -> AsyncIterator[Disposer]:
        """Async-generator startup. The FIRST yield hands back teardown, before any
        setup that could throw. Code after it is the async setup body."""
        yield self._teardown
        await self._connect()

    def __call__(self, *a, **kw):                   # optional: callable services
        ...
```

Notes:

- **Self-registration is the whole trick.** `provide()` is itself wrapped in `ctx.effect`, so a service is withdrawn when its constructing fiber unloads, with no install/uninstall code anywhere (K4). A kernel with a separate service-registration path has already lost the guarantee.
- **`provide()` refuses a second provider (K15).** If `(realm, key)` is already bound by an installed fiber, `provide()` raises `DuplicateProvision` naming both fibers, and the mounting fiber goes to FAILED. This is paper Def 58(2) — `m ≠ n ⇒ p_m ∩ p_n = ∅` — a well-formedness clause imposed at O-Insert's last premise, not an implementation detail. Last-writer-wins would break the preservation theorem the rest of §B.7 leans on, and would do it silently. Note the interaction with **OPEN-14**: `ctx.replace` is the *sanctioned* way to change a binding, and it works precisely because it withdraws before it installs.
- **`provide()` writes both the store and the provider's own committed view**, per B.2.2. Its disposer must then: delete the store binding, notify dependents, **await every affected fiber settling**, and only then delete from the provider's own committed view — "self access before dependencies cleanup" (K8). Without the write in the first place, K8's "delete from the provider's own view last" refers to nothing and a provider cannot read its own service.
- **`start()` is called by the kernel, immediately after construction, and nowhere else.** Say this explicitly or a factory will generate a kernel that never runs it: `execute()` constructs the plugin (`instance = P(ctx, config)`), runs any `@inject_method` init hooks, then calls `instance.start()` and feeds the resulting (async) iterator into the same `_execute` drain loop as any other effect body. `start()` as an async generator is K3 realised as an ordinary language feature, and it is the reason a service that fails halfway through setup still tears down what it already built.
- **`available()` needs a re-evaluation trigger, and the first draft gave it none** — so a provider could never signal that it had *become* unavailable. Cordis re-checks `[Service.check]` on every `notify`. The contract: `available()` is evaluated on provision, on every notify touching this key, and on demand via `ctx.replace`-style `service.invalidate()`; a transition from `True` to `False` notifies dependents exactly as a withdrawal does. An `available()` that reads something the kernel never notifies on is an authoring error.
- Cordis's callable-service trick (a constructor returning a function-shaped object) does not port and should not be emulated; Python's `__call__` is a cleaner fit.
- **A registered definition is a readonly borrowed same-process contract.** DSH's authoring law for tool definitions generalises to every registry-style service: *never mutate a definition after registration; dispose and re-register to hot-swap.* This is the registry-level analogue of K6's withdraw-then-install (an in-place mutation is invisible to everyone holding the old object, exactly as an in-place binding overwrite is invisible to dependents), and **OPEN-14**'s `ctx.replace` should cover both levels — the binding and the registry entry — or authors will get one right and the other wrong.
- **Per-context config merging (the `intercept` chain) — the first draft specified this two incompatible ways.** §B.4 said `model_copy(update=...)` over the ancestor chain; **OPEN-11** said each key defines its own metadata monoid `(ℳ_k, ⊕_k, ε_k)` with a right-biased merge (paper Def 30/31). They cannot both hold, and the first is wrong twice over: it hardcodes one merge rule for every key, and `model_copy(update=...)` is **shallow and does not validate the updated fields** (documented Pydantic v2 behaviour), so an intercept-merged config would bypass the very load-time validation §B.5 makes a guarantee. Resolution: **the monoid is the contract.** A key that participates in interception declares `merge: Callable[[M, M], M]` and `identity: M` alongside its type; the kernel folds the ancestor chain root-closest-first with that merge, then **re-validates the result through the model** (`Config.model_validate(merged)`), never `model_copy`. A key that declares no merge rule is not interceptable, and asking to intercept it is a load-time error. **OPEN-11** now decides only *whether interception ships in v1*, not how it merges.

**The three-role convention** (not a kernel mechanism — a convention worth copying wholesale, cheaply, on day one):

- **Definition** package: owns the `ServiceKey` and the request/result types. Depends on nothing.
- **Provider** package(s): implement it.
- **Consumer** package: exposes it to the model/user as a tool or a UI surface.

Provider and consumer **never depend on each other**, only on the definition. The complete capability is the seam; no single role is one. Every `ServiceKey` in QMA is classified `seam` (swappable, 1+ providers) / `core` (single fixed implementation) / `bundle` (one concrete assembly, e.g. the agent loop), and a generator + completeness guard asserts every declared key is classified. That is a machine-checkable extensibility inventory and it is what makes the acceptance property auditable rather than aspirational.

**The three-role split is the special case of a general recipe, and the general case has a cost worth knowing.** Paper §6.5: two components that interact bidirectionally (a server and an access controller, say) create a dependency cycle if written as two, and a cycle "simply leaves the involved components **permanently inactive**". The decomposition is into **four**: two cores that depend on nothing of each other, plus one integration component per interaction direction, each depending on both cores. Definition/provider/consumer is that recipe with one direction. Two things follow that neither document said:

- **Cycle detection is cheap and must ship.** Unlike deadlock, a dependency cycle is "predictable from the dependency declarations alone, so a runtime can report it when components are loaded". The kernel therefore runs a cycle check over declared `inject` edges at mount and **reports the cycle by entry id** instead of leaving a set of fibers silently PENDING forever. Without it, the most common composition mistake presents as "my plugin never starts, no error anywhere" — which for a model-authored plugin is close to undiagnosable.
- **Integration components grow quadratically** in the number of mutually interacting components. This does not hurt correctness or runtime (fibers are cheap) but it hurts authoring, and it is the honest cost of the no-cycles rule. Mitigations the paper names and QMA should adopt: package bundling, convention-based wiring, and scaffolding — i.e. the factory generates the integration component rather than asking an author to hand-write it.

**Exclusive binding versus the service broker — this is a choice, and it sets the blast radius of every provider swap.** §B.10 advertises the exclusive shape as the acceptance demo: *"every consumer is torn down, the new provider comes up, consumers restart against it."* That is correct, and at the scale this SDK is aimed at it is also alarming: with hundreds of minds running, swapping the LLM provider under exclusive binding **reloads every consumer fiber in every mind**. The paper's §6.2 broker is the alternative — one broker service injected by both providers and consumers, providers registering with it through a revertible effect, the broker absorbing the perturbation so a backing-provider swap triggers **no consumer reload at all**. It is also what makes rolling updates an application-level composition (load new provider as an extra fiber, shift weights, unload old once drained) rather than an infrastructure operation, and it is the natural shape for cross-process/remote providers (**OPEN-24**). The dossier files the broker under "incidental", which is right about the *kernel* and wrong about the *product*: the kernel needs no broker, but QMA's high-traffic seams (`llm`, `tools`, `subagents`) should each declare which shape they use, in the seam classification, on day one. **OPEN-26.**

## B.5 Plugin protocol (K5)

Three accepted shapes; the resolved callable's identity is the registry key, so re-plugging the same object reuses one runtime record and adds another fiber (which is what lets hot reload swap fibers while the record survives).

```python
# --- module-as-plugin (the common shape; a folder with __init__.py qualifies) ---
name     = "qma-tool-read-note"
inject   = [notes_key]                      # ServiceKeys — required, gate activation, enter the epoch
optional = [metrics_key]                    # ServiceKeys — declared but NOT gating; readable via ctx.find
provide  = [ ]                              # ServiceKeys this plugin installs (declared, checked)

class Config(BaseModel):
    max_bytes: int = 64_000

def apply(ctx: Context, config: Config) -> Disposer | None:
    ...

# --- or a Service subclass, or any object with .apply(ctx, config) ---
```

- `inject` is the coeffect specification. A plugin naming a key **waits** until it is provided, is torn down when it goes, and reloads when it returns. **There is no boot order anywhere in QMA** — the loader may import and mount everything concurrently, and a fiber whose dependencies are not up simply waits.
- `provide` is a declaration the kernel **checks**: a plugin that declares a key and does not install it breaks the confluence condition, so this is worth enforcing at load rather than discovering later.
- `Config` is a Pydantic model. The kernel validates and fills defaults at load; invalid config **fails the load loudly** with an actionable message. The design rule: *anything two deployments might want to set differently must be a config field*, tested by "can the recipe change this without a code edit?"
- **Optional dependencies ARE declared** — in `optional`, read at the call site with `ctx.find(key)`, which returns `None` when the provider is not up and **raises `UndeclaredAccess` when the key is in neither list**. This is the B.2.1 divergence from Cordis, and it exists so that "the declared capability set is complete" survives contact with optional dependencies. `optional` does not enter the epoch: appearance or disappearance of an optional provider does **not** reload the fiber, which is the whole point of the distinction. (Consequence to document for authors: a plugin holding a value fetched through `find` across an optional provider's swap holds a stale object; `find` at the call site, never cache the result.)
- `@inject_method(key)` defers one method until its own dependencies resolve, independent of the class's `inject`.

**Fiber states** (`PENDING → LOADING → ACTIVE`, `→ FAILED`, `ACTIVE → UNLOADING → DISPOSED`, `→ POISONED`) are driven by an **epoch**: a string built from the uid of the fiber providing each injected key.

```python
def _refresh(self) -> None:
    epoch = ""
    for key in self.inject:                        # `optional` is deliberately NOT in this loop
        binding = self._store.get((self._realm(key), key))   # the kernel STORE (B.2.2), not a view
        if binding is None:
            epoch = INACTIVE; break
        epoch += f":{binding.uid}"                 # provider IDENTITY, never value (K6)
    self._set_epoch(epoch)
```

State reacts only to an actual **change** of epoch: into `INACTIVE` → unload; out of `INACTIVE` → reload; **between two different real epochs → unload then reload** (a provider was swapped; never a live in-place patch). This is K6 flattened into one string, and it is why identity-not-value matters: a different provider handing over an equal value *is* a change. `_refresh` reads the **store**; `_resolve` reads **committed views** (B.2.2); the gap between them is K8.

**Retirement versus removal (K19).** The state list above is not the whole registry story, and the first draft's omission would produce a kernel that runs a removal-shaped inverse and fails it. Paper Def 47 is explicit that the inverse of a registration must be **O-Retire, not O-Remove**, "because an inverse has to apply wherever it is reached": retiring has one premise (the fiber exists) and therefore always succeeds, whereas removal carries premises that can fail — `∀m. π_m ≠ n`, i.e. **children are removed before their parent**. So:

- Each fiber carries a **retirement flag `τ`**, monotone, written only once and only to ⊤. An accumulator's inverse sets `τ`; it does not delete the record.
- A retired fiber that is INACTIVE with an empty table and no children is **vestigial** (Lemma 57): indistinguishable from absence by any rule, and only *then* removable. Removal is a separate, guarded step the loader performs — never something an inverse does.
- **This is what makes K6's "fresh, never-reused uid" affordable.** A freed uid is reissuable only because the L-Unload guard already guarantees no surviving committed view can name it (Thm 59). State the guard alongside the freshness claim, or an implementer will conclude that fresh uids alone are the mechanism and will reuse them under memory pressure.

**FAILED has no exit edge, and there is a third paper-versus-code divergence here that the dossier's §7 did not catch.** The paper's L-Begin premise is `Inactive(⊥)`, so a fiber that failed is **never re-entered**, even when its environment changes — deliberately, to withhold a component "whose effect function has shown itself to be unsound in the state it ran against". The shipped code does the opposite: `_reload` catches the error, stores it, and **forces the epoch back to `INACTIVE`**; `_setEpoch` then triggers `_reload()` on any later transition *out of* INACTIVE. So in Cordis a failed fiber **does** come back when a dependency changes. K11 copies the paper's prose ("does not auto-retry against an unchanged environment") while the state machine has no `FAILED → LOADING` edge at all and the contract never says what happens on a *changed* one.

This is product-visible and the operator should decide it, not the kernel author: **does a mind whose model provider was briefly down come back by itself?** Draft position — **follow the shipped code, not the paper**: FAILED is not terminal, and an epoch change (a genuinely different environment) re-enters LOADING, while an unchanged environment never does. That is what an agent harness wants and it is what has actually been exercised in production. The paper's stricter rule is available as a per-entry `retry: never` option. Add the edge to the state diagram either way. **OPEN-27.** (`POISONED`, from **OPEN-06**, *is* terminal — a teardown that timed out has left unknown residue, and that is a different thing from a load that failed cleanly.)

**Task lifetime.** Every `asyncio.create_task` in the lifecycle must be **literal and explicit**. JS promises begin executing on creation; Python coroutines do nothing until scheduled. The paper wrote `create_task` explicitly for exactly this reason. Audit sites and **where each task's strong reference lives** — CPython may garbage-collect a task nothing references, mid-flight, and the first draft named the sites without naming the homes:

| task | strong ref held at |
|---|---|
| fiber's in-flight transition | `fiber.inertia` |
| effect setup | `effect_runner.setup_task`, cleared on settle |
| dependent-drain fan-out | `fiber._drain_tasks: set[Task]`, discarded via `task.add_done_callback(set.discard)` |
| child-fiber cascade | the child's own `fiber.inertia`, plus the parent's disposer holding the child fiber |
| teardown (B.3) | `fiber._teardown_task` |

Missing a `create_task` produces a system that appears to work and deadlocks under load; missing a *reference* produces one that works until it does not, non-deterministically.

**`parallel` aggregates failures as an `ExceptionGroup`** — the Python analogue of Cordis's `AggregateError`. Implemented as `gather(*, return_exceptions=True)` followed by an explicit `raise ExceptionGroup(...)`, **not** `TaskGroup` (whose cancel-siblings-on-error semantics contradict the containment rule, as in B.3).

The kernel is **async-only, single-loop, with no synchronous public API callable from another thread** — the re-entrancy reasoning above assumes a single-threaded event loop, and breaking that assumption makes it wrong rather than merely incomplete. Thread and process work goes behind a service boundary (`ctx.subprocess`-shaped). **OPEN-16.**

## B.6 The event bus (K12)

Five primitives, closed set, mode carried in the key's type:

| Mode | Semantics | Listener may be `async def`? | Use it for |
|---|---|---|---|
| `emit` | fire-and-forget, synchronous, returns ignored | **NO — rejected at registration** | status, lifecycle, "this happened" |
| `parallel` | all listeners concurrently, awaited, failures aggregated as an `ExceptionGroup` | yes | fan-out side work |
| `serial` | in registration order, awaited, stops at first answer | yes | ordered first-answer-wins |
| `bail` | same, synchronous | **NO — rejected at registration** | cheap synchronous decisions |
| `waterfall` | around-middleware; each listener gets `next`; not calling `next()` vetoes everything downstream **including the built-in behaviour** | yes | interception, policy, wrapping |

`waterfall` is the interception primitive and the reason no plugin ever needs to invent an event protocol. The **closedness** is the value: every extension point in the system is one of five shapes.

**A synchronous `emit`/`bail` does not port from JS, and the first draft specified it as though it did.** In JavaScript, calling an async listener from a synchronous `emit` at least *executes the body* and orphans the returned promise — sloppy, but the work happens. In Python, calling an `async def` listener from a synchronous method returns a coroutine object that is never awaited: **the listener body never runs at all**, and the only signal is a `RuntimeWarning` on garbage collection that nobody reads in production. Every `emit`-mode extension point would silently drop every async listener — and "make the handler `async` because it awaits something" is the single most likely thing a plugin author, and a model writing a plugin, will do.

The contract closes this at **registration** rather than at dispatch, so the failure is loud and load-time rather than silent and runtime:

```python
def on(self, key, handler, *, prepend=False, scope_global=False) -> Disposer:
    if isinstance(key, (EmitKey, BailKey)) and inspect.iscoroutinefunction(handler):
        raise SyncListenerRequired(key, handler)   # names the event, the handler, and the fix
```

The fix offered in the message is always the same and always available: *use the `parallel` key that pairs with this `emit` key, or do the async work in a task you own.* (A rejected alternative, recorded so it is not re-litigated: have `emit` schedule async listeners as tasks. It restores the JS behaviour but silently converts a synchronous status broadcast into unordered concurrent work with no error containment and no place to hold the task reference — worse than the disease.) **OPEN-28** covers only whether `bail` survives at all in Python given this constraint, since a synchronous decision point in an async kernel is a narrow niche.

**Bail sentinel — `NO_RESULT` inverts the failure mode in the most dangerous direction, and both documents presented it as strictly better with no counter-argument.** The draft was: every value including `None` counts as an answer, and a listener returns the explicit sentinel `NO_RESULT` to pass. Now consider the single most common Python authoring slip, and one that is near-certain in model-authored plugins:

```python
def gate(exec):
    if exec.tool == "read_note" and is_private(exec.args):
        return Deny("private")
    # ← falls off the end: returns None
```

Under `NO_RESULT`, `None` means **"I answered"**. That listener silently truncates the chain and **skips every downstream policy listener** — including the deny-only guards. The most likely typo in the system produces a silent permission bypass. Cordis's falsy set exists precisely so that "fell off the end" means "pass"; that is not an accident of JS, it is the safe default for a chain of policy listeners.

Revised position, and this is a reversal of the first draft: **an answer must be explicit, and passing is what happens by default.**

```python
class Answer(Generic[R]):          # explicit wrapper — the ONLY way to stop a chain
    __slots__ = ("value",)

# serial / bail listener returns: Answer(v) to answer, or anything else (incl. None) to pass.
result = await ctx.serial(key, arg)      # -> Answer(v) | NO_RESULT
```

This keeps everything `NO_RESULT` was introduced for — `Answer(None)` and `Answer(False)` are expressible, so "a policy listener that legitimately decides *no*" works, which the JS falsy set cannot do — while making the dangerous direction the one that requires typing something. If the operator prefers to keep bare `NO_RESULT`, then the kernel **must** reject a listener that returns `None` without an explicit `return None` statement (an AST check at registration; unpleasant but mechanical). What is not acceptable is shipping "bare `None` means answered" with no guard. Still a one-way door; decide before the first extension point ships. **OPEN-05, position changed.**

**The five modes do not include a collector.** B.6 claims "every extension point in the system is one of five shapes", and that is true of *events* — but a very common extension shape is *run every contributor and merge their results*: a skills catalog, a system-prompt assembly, a tool inventory, a settings namespace. None of the five does this (`parallel` returns nothing, `serial` stops at the first answer). The original does not do it with events either: DSH builds catalog-merging through **services** — `ctx.skills` "merges provider skill catalogs", `ctx.llm.registerAdapter`, `ctx.subagents` as a named-provider registry, `ctx.systemPrompt.section()`. So the rule to write down is: **collectors are registries, not events.** A collector-shaped capability is a service whose registry is populated by `register`-style calls, each of which is a caller-attributed effect (K18) so contributions withdraw automatically. Say this explicitly, or an author — reasonably — will try to build a collector out of `parallel` and discover it cannot return anything.

`ctx.on()` is an effect: listeners unregister on unload and `on()` returns the disposer directly. Listeners resolve `ctx` against the **registering** context, not the dispatching one.

**Internal event surface.** The four `internal/*` extension points (`internal/get`, `internal/set`, `internal/listener`, `internal/dispatch`) plus the lifecycle emissions are specified in **B.2.4** and are part of this closed set. They are what makes cross-cutting policy over *all* service access a plugin rather than kernel surgery.

**Scope filtering — the draft's default is the opposite of Cordis's, and it leaves telemetry with no sanctioned path.** Many events must reach only the listeners registered under one agent/session context. The first draft said "a listener on root hears everything". Cordis's actual default is **isolation-label equality**: `Service[symbols.filter]` is `ctx[isolate][name] === this.ctx[isolate][name]`, so a listener registered at root does **not** see events from an isolated child realm, and `{ global: true }` on the registration is the explicit opt-out. (DSH's `dsh-scope` package layers the *other* convention on top for its scoped tool events — root listeners there do see everything — so the two primary sources genuinely differ, and the contract must pick rather than inherit an accident.)

Whichever default is chosen, **the `global` escape hatch is not optional**: telemetry, cost accounting, the session log bridge and the UI bridge all must observe every realm, and under an equality default with no opt-out they simply cannot be written. Hence `scope_global: bool = False` on `ctx.on` in B.2. Draft position: **isolation-realm equality as the default** (matching Cordis, and matching the reason isolation exists — a per-mind realm that leaks its events to root is not isolating much), with `scope_global=True` available and **gated on a declared `observe_all` capability** so it is visible in the load-time capability review of B.2.2 rather than being a quiet way around isolation. **OPEN-19, default flipped.**

**Cross-realm communication is undefined at exactly the point the acceptance test names.** Two consequences nobody connected: (1) with the realm as the event filter, events **do not cross realms** — but `map.md` names a Delphi-like (many minds talking to each other, DSH's `agent/inbox/*` shape) as one of the three acceptance profiles, so inter-mind messaging needs an explicitly realm-crossing mechanism: a `messaging` service provided **above** the per-mind realms and injected by each mind, i.e. the broker shape of B.4, not an event. (2) Under **K15** only one fiber may provide `agent_loop` per realm, so heterogeneous per-participant loops require **per-participant realms** — which means the Delphi-like acceptance case is gated on **OPEN-10** (isolation realms) landing early, not late. That is a schedule fact, not a design detail.

**The applied convention** (worth copying identically, because it is what makes this into an extensibility *surface* rather than an event soup) — one closed pipeline shape, reused everywhere:

```
<x>/pre-execute   (waterfall)  reorderable allow / deny / ask
registered guards (monotonic)  final-only; may deny, may never re-allow
<x>/execute       (waterfall)  around-dispatch: timeout, retry, metrics
<x>/post-execute  (waterfall)  accept / replace / block
finalize          (sync)       owner-only, content shaping
<x>/result        (emit)       frozen final observation
```

A "hook" is then an ordinary plugin listening on an interception point — no external hook protocol, and Claude-Code/Codex-style hook config files are bridged by mapping them onto these same points.

**This pipeline is a non-commutative key, and that obligation must be discharged here (K17).** Paper §3.3.2 is explicit: *"a key whose value is an ordered chain is not [commutative], since a middleware inserted before another sees a different request"*, and commutativity is *"an obligation on the **provider** of the key, not on consumers."* The pipeline above is an ordered chain, listener order is registration order, and §B.7 says **"the orchestrator arranges no load order at all"**. Put those three together and there is a concrete break: mount two policy plugins on `tools/pre-execute`, one that denies and one that rewrites the arguments. Their relative order is undetermined, so **the assembled profile's behaviour is not a function of the recipe** — which is the property the whole confluence argument in §B.7 is claiming.

K12 says where order should live; it never stated the provider's obligation. The provider of every ordered-chain key in QMA must therefore publish, in the key's own definition package:

1. **What is order-independent.** The mechanism that buys this back is the one DSH already uses and the first draft mentioned without explaining: **monotonic guards**. A guard may only deny, never re-allow. A set of deny-only contributions is commutative — the result is the intersection regardless of order — so *policy that only subtracts* is order-free by construction, and that is why the pipeline's guard stage is separate from its waterfall stage. **Anything that must be order-independent belongs in the guard stage, not the waterfall stage.**
2. **How order is determined for the rest.** Registration order is not a specification when nothing arranges load order. The options, and one must be chosen per key: an explicit `priority: int` on the listener registration (simple, and what most systems end up with), or a declared dependency between the two policy *plugins* so K5 orders their activation and therefore their registration (purer, matches K12, more work for the author).

Draft position: **`priority` on `ctx.on` for waterfall keys, plus the authoring law that order-sensitive policy is a design smell** and belongs in the monotonic stage wherever it can be expressed there. A waterfall key whose definition package does not state its ordering rule fails the catalog verifier.

## B.7 The loader — recipes and folder-as-agent (K5, K14)

One row per fiber. This shape is a faithful encoding of the calculus and should not be redesigned:

```python
@dataclass
class Entry:
    id: str                                  # hierarchical, ":"-joined; THE reconciliation key
    name: str                                # module specifier: "qma_notes_local" or "pkg.mod:attr"
    config: dict | None = None
    group: bool = False                      # this entry's config IS its child list
    disabled: bool = False
    inject: list[str] | None = None          # package-qualified key names — see B.1
    isolate: dict[str, bool | str] | None = None
    intercept: dict[str, Any] | None = None
```

**Strings here, key objects in B.1 — and the seam between them is specified in B.1, not left implicit.** `Entry.inject` and `Entry.isolate` are strings because config is text; §B.1's key objects are the type authority. The `qma.keys` entry-point resolver bridges them, package-qualified, imported lazily, ambiguity is a load error. This is the one place the collision problem B.1 eliminates at the type layer reappears at the config layer, and pretending otherwise would leave a factory to invent a global registry of its own.

**Reconciliation is incremental with per-field dispatch** — this is what makes "everything via the UI" and "an agent edits its own configuration" safe rather than terrifying:

| field changed | action |
|---|---|
| `id` or `name` | rebuild the entry |
| **entry moves between groups** | **rebuild** — see below |
| `isolate` | realm reassignment (Algorithm 7 — see below; **not** a plain reload) |
| `intercept` | patched in place, **no reload** (metadata is read at access time) |
| `config` | handed to the plugin, which may patch in place or restart |
| `disabled` | unload / reload |

**Entry movement.** Cordis handles an entry moving to a new parent by **live prototype re-parenting** (`Object.setPrototypeOf(this.ctx, this.parent.ctx)` in the loader's `_patchContext`) — the moved entry's context immediately sees its new ancestor chain with no rebuild. `collections.ChainMap` cannot do that cheaply: re-parenting means rebuilding `.maps` for the entry and every descendant context derived from it. And because ids are hierarchical and `:`-joined, **a move changes the id**, which by row 1 of this table is a rebuild anyway. So the contract states it plainly: *an entry that moves is rebuilt.* Worth writing down next to **OPEN-15**, because it means a config-writing model that reorganises a subtree pays a full rebuild of it, and an id discipline that survives reorganisation is worth more than one that only survives renames.

**Isolation realm reassignment — the first draft reduced an algorithm to a table cell.** `isolate` is mandated in the Entry shape and **OPEN-10** says ship it in v1, so "any `isolate` edit through the UI is undefined behaviour" is not an acceptable state for a document whose purpose is no-ambiguity. The paper spends Algorithm 7 plus equation (65) on it. The four pieces the contract must carry:

1. **Two kinds of realm.** `isolate: true` asks for a **local** realm, private to the entry, tagged by its `id`, and **carried with the entry wherever it moves**. A **string** asks for a **global** realm, shared by every entry naming that string — so moving such an entry changes which entries it shares a binding with. A realm is **discarded once no entry names it**. These behave differently under every edit and must not be collapsed into one "isolate" concept in the UI.
2. **Delimiter tags.** The hard case is deciding, when a realm changes at key `k`, whether *this entry is itself the provider* at `k` — undecidable from the realm symbol alone once a realm is shared by several fibers. The mechanism is one delimiter symbol `δ_k` per key, under which each context stores a tag of its own, **written on a context, inherited by its descendants, and drawn fresh at each reassignment**, giving equation (65): `γ′[δ_k] = d₁` iff `γ′` derives from the entry's context. Write `own(γ′)` for that test.
3. **The rebind loop.** For each key whose realm changed, capture `(s₁, s₂, d₁, d₂)` = (old realm, new realm, the entry's fresh tag, the provider's tag); reload the entry's fiber; then **move the binding from `s₁` to `s₂` exactly when `d₁ = d₂`** — i.e. exactly when the entry is itself the provider at that key.
4. **`affected` replaces Alg 3's realm test.** A dependent is affected at `k` when its realm for `k` is `s₁` or `s₂` **and** `own` separates it from the provider: `(fiber.ctx[δ_k] = d₁) ≠ (d₂ = d₁)`. Where `own` agrees on dependent and provider, both move or neither and the dependent sees the binding afterwards exactly as before; where `own` separates them, the dependent **gains or loses** the binding — which is the whole point and the only case that triggers a reload. Notify with this predicate, not with a realm-equality test.

Entry update is **transactional with rollback**: if the new plugin fails to start, the previous options and previous plugin are restored and an apply error is raised.

### B.7.1 The Fiber API

The contract had no Fiber section at all, while §B.7 and §B.9 both depend on one and §B.9 references `fiber.effects()` by name. For a document whose stated purpose is "no ambiguity" for a code-generating factory, that is a hole. The surface, complete:

```python
class Fiber:
    uid: str                        # fresh, never reused (K6/K19)
    entry_id: str | None            # the loader's reconciliation key, when loader-mounted
    state: FiberState               # PENDING | LOADING | ACTIVE | FAILED | UNLOADING | DISPOSED | POISONED
    error: BaseException | None     # set iff FAILED; reported by name in the UI (K11)
    inertia: asyncio.Task | None    # the in-flight transition, or None when settled
    committed: dict[ServiceKey, Binding]

    async def dispose(self) -> None
    async def await_settled(self) -> None
    async def restart(self) -> None
    async def update(self, config: Any, *, no_save: bool = False) -> None
    def effects(self) -> EffectTree
    def __await__(self)             # `await ctx.plugin(P)` — settles, then re-raises `error`
```

- **`dispose()`** carries three guarantees, and they are the ones to state in the SDK docs verbatim: (1) every registration this fiber owns is removed, (2) child fibers are recursively unloaded, (3) the returned awaitable resolves **after all async cleanup has finished** — not after cleanup was initiated.
- **`await_settled()`** waits out `inertia` (looping, since a transition may chain straight into another) and then **re-raises `error`** if the fiber failed. `Fiber.__await__` delegates to it, which is Python's native replacement for Cordis's thenable-wrapper trick and is cleaner than the original.
- **`restart()`** = force epoch to `INACTIVE`, refresh, await. Unload-then-reload, never an in-place patch (K6).
- **`update(config, no_save=False)`** — **when the fiber is not ACTIVE, resolution is DEFERRED**, because the services a config expression or validator may need are not available yet. This rule is load-bearing and easy to omit: eagerly resolving config against a half-built environment is how a config edit turns into a spurious failure. When ACTIVE, the new config runs through the `internal/update` waterfall (B.2.4), whose **terminal** action assigns the config and calls `restart()` — so a plugin can intercept its own config change and patch in place rather than restarting, by not calling `next`.
- **`effects()`** returns the labelled tree of what this fiber currently holds, built from the `EffectMeta{label, children}` attached to each disposer as nested `effect()` calls register themselves as children. This is what §B.9 item 2 renders as "what does this plugin currently hold".
- **Confinement (K16) applies to all of it.** These are the *kernel's* handles on a fiber, and the loader's. A plugin does not reach another fiber's `state`, `error` or `committed` by walking the tree; it declares the introspection capability and reads it through a service, exactly as §B.9 requires.

**The metatheory licenses the incremental approach — under four hypotheses that must travel with the claim.** The settled state is a function of the final configuration alone (Thm 73), it provably settles (Thm 66), a departing fiber's contribution is nothing (Cor 62), and **the orchestrator arranges no load order at all** (Thm 63). But confluence holds only when: (i) the dependency graph is **acyclic**, (ii) effects are **pairwise independent** — which by K17 means every shared key is commutative, (iii) **every component installs everything it declares it provides** (Def 69 — which is why `provide` is checked in §B.5, not merely documented), and (iv) **there is no failed fiber.**

Hypothesis (iv) is the uncomfortable one, and the first draft asserted the theorem while advertising the exact condition that voids it. **A.4 corollary 2, K11, and §B.10's failure bullet all sell failure containment as a headline property** — a plugin that fails to start damages only itself, and the profile keeps running. Cor 62 does bound the damage: a failed fiber's *contribution to the state* is nothing, so the divergence is confined to **which fibers are Active**. But for a config-driven UI, which fibers are Active **is precisely the observable**. So the honest statement, which belongs in the ratified contract and in the UI:

> With a failed fiber present, the running system is *not* guaranteed to be the one a from-scratch load of the same recipe would produce. What is guaranteed is that the difference is confined to which fibers are active — nothing a failed fiber installed survives, and no sibling's state is perturbed. **"Reload the profile from the recipe" is therefore a real, distinguishable operation, not a no-op**, and the UI must offer it whenever any fiber is FAILED.

That is a better product than pretending the theorem holds unconditionally, and it is the same reason **OPEN-27** (does FAILED ever exit?) is product-visible rather than internal.

**Folder-as-agent.** A profile is a folder; the kernel's loader is the thing that makes this work without the kernel knowing what a profile is.

```
profiles/toy-scholar/
  profile.yaml        # an entry subtree — the only file the loader itself understands
  constants.yaml      # profile-level constants        (a plugin reads this — OPEN-18)
  prompts/  skills/  tools/  memory/                   (plugins read these — not the kernel)
```

The mechanism, all of it already required by the above:

1. A `group` entry whose config is a child list, so a folder mounts as one subtree.
2. A `folder` plugin (an ordinary plugin, like Cordis's `include`) that reads `profile.yaml` and grafts its rows as children — a nested tree stays inside the calculus because grafting is itself an effect.
3. Hierarchical `:`-joined ids (`profiles:toy-scholar:notes`), so every row in every profile has a stable reconciliation key and an edit updates rather than rebuilds. **Who allocates ids when a model writes config is OPEN-15** — get it wrong and every agent edit becomes a full subtree rebuild.
4. `isolate:` on the group, so each profile/mind gets **its own instances** of the services it names, side by side with other profiles running different configurations of the same service. This is the mechanism per-session and per-agent isolation is built from, it touches every lookup, and it is very expensive to retrofit. Draft: ship it in v1 even if its config surface lands later. **OPEN-10.**

What the kernel does **not** define: what `prompts/` means, what a skill is, what memory is, what a mind is. Those are conventions owned by plugins, and that separation is exactly what the acceptance property is protecting.

## B.8 What the kernel explicitly does NOT own

Stated as a list so it can be enforced by review. None of these may appear as an import, a concept, or a string constant inside `qma.kernel`:

| Not in the kernel | Where it lives instead |
|---|---|
| Profiles, minds, agents | a `profile` plugin family reading a folder + `profile.yaml`; the kernel sees only entries |
| The agent loop | one `bundle`-classified plugin providing `ctx.agent_loop` |
| Models / providers / prompt adaptation | `ctx.llm` seam + per-provider adapter plugins |
| Tools | `ctx.tools` core plugin + one plugin per tool or per MCP server |
| Skills, memory, knowledge bases | seams with named providers; promotion gates are plugin policy, not kernel law |
| Sandboxes, computers, subprocesses | `ctx.sandbox` / `ctx.subprocess` seams, provider-neutral by construction |
| Sessions, persistence, replay, compaction | a session plugin owning a durable append-only log on a **separate bus** — **OPEN-12** |
| Permissions, approvals, policy | two layers: per-capability `pre-execute` waterfalls + monotonic guards for *that capability's* decisions, and **`internal/get` (B.2.4) for cross-cutting policy over every service access**. The second is what makes per-mind attribution, quota and record/replay a plugin. Interception metadata (**OPEN-11**) is a third, optional layer — not the load-bearing one |
| Logging and log routing | a `logging` seam with per-realm providers. **Not a `Context` attribute** — see B.2.5 |
| Scoped constants (kernel/platform/profile levels) | a constants plugin using `isolate`/`intercept` for scoping — **OPEN-18**, which depends on **OPEN-11** shipping |
| The UI, slots, screens | the bridge plugin + a second plugin tree in the browser — B.9 |
| Telemetry, metrics, cost accounting | listeners on the frozen-result `emit` events, plus `internal/dispatch`, both requiring the `observe_all` scope capability (B.6) |
| Runtime invariants | a `ctx.invariants` plugin — see below |
| Layered settings, credentials | `ctx.settings` / `ctx.credentials` plugins — see below |

**Four DSH borrowings that neither document costed, each worth at least a row:**

- **`ctx.invariants`** — a runtime-invariant registry with selection, uniqueness and child-fiber checks, and **package-attributed failures**. This is the machine-checkable complement to the seam/core/bundle guard (**OPEN-23**): the guard checks the *inventory* statically, `invariants` checks the *running assembly* dynamically, and "exactly one provider for this key in this realm" (K15) is exactly an invariant. For a system that lets a model mount plugins, having a place to say "this must remain true and here is who broke it" is worth more than it costs.
- **`ctx.settings`** — layered resolution `defaults → base → user`, **distinct from plugin config**. Plugin config answers "how is this plugin configured in this recipe"; settings answer "what does this operator prefer, across recipes". They are different lifetimes and different UIs, and collapsing them is why settings screens end up hand-written. This is also the natural home for **OPEN-18**'s scoped constants, and a cheaper one than the interception chain.
- **`ctx.credentials`** — `CredentialRef` resolution that **never carries raw secret values in config**. Directly relevant, because §B.5 makes *every tunable a config field* and §B.9 makes every config schema serialisable to the browser. Without a credential indirection, that design decision ships API keys to the UI. This is not a v1.1 item.
- **Overlays and `!!js` expression config.** DSH names overlays as the recommended mechanism for environment-driven plugin selection, and evaluates `disabled` expressions against the loader context at **every mount decision** and `config` expressions against the plugin's **own** context after its injections activate. The contract's Entry is literal-only, which drops both. Note the cost honestly: literal-only config means every environment difference becomes a separate recipe file. Draft: ship overlays (a recipe that patches a recipe — pure loader mechanics, no expression evaluation), **defer expressions** (a `!!py` evaluator inside config is an arbitrary-code surface pointed straight at model-authored files, and **OPEN-08**'s bound would have to cover it).

**The CI gate must be structural, not lexical.** `grep -ri "agent\|model\|tool\|prompt\|session" qma/kernel/` fails on day one against this contract's own design: §B.5 mandates "Config is a Pydantic model" and §B.4 uses `model_copy`/`model_validate` — every one of those is a `model` hit. And it does **not** catch `logger`, which was the actual boundary leak (B.2.5). Replace it with checks that mean something:

1. **Import-graph gate.** `qma.kernel`'s transitive imports must be a subset of `{stdlib, pydantic, typing_extensions}`. No `qma.*` package outside the kernel, ever. This is a real fence and it is checkable exactly.
2. **Reserved-name gate.** The published reserved-name set (B.2.5) is frozen, and no name in it may be a domain concept. Any addition to `Context`'s class body is a diff a human must approve.
3. If a word list is kept at all it is a *review prompt*, not a gate, and it must at minimum include `logger`, `log`, `llm`, `mind`, `profile`, `skill`, `memory`, `sandbox` — the words that actually name QMA domain concepts — while excluding the ones Pydantic forces into the file.

## B.9 The UI-plugin bridge (Python backend → React/TS UI)

**Shape.** Backend runs the QMA Python kernel. Browser runs a **second plugin tree**. Between them, one explicitly versioned wire contract and nothing else. Draft position: for v1 the browser tree runs a real (TS) kernel — vendored, proven — while the backend runs ours, with the seam kept small and written down **before either side ships**; a single TS+Python kernel pair is the considered end-state. The thing to refuse is drifting into "backend declares screens, browser renders them" by accident: it is cheaper this quarter and permanently costs the property that a UI feature is a plugin with its own lifecycle and failure containment. **OPEN-09.**

Draft position (c) also has a cost the first draft did not name: **it is a semantics seam, not just a data seam.** The TS side has *already resolved three of this register's open questions the opposite way* — **OPEN-01** (the drain lives inside the provide disposer), **OPEN-02** (LIFO-initiated, concurrent completion) and **OPEN-05** (the JS falsy bail set). So a plugin author writing both halves of one package under (c) faces two different bail semantics and two different teardown-ordering contracts in one repository, and every SDK doc has to say "on the backend… on the browser…". That is not a versioned wire contract's problem; it is a fork in the authoring model. It does not sink (c) — the alternatives are worse — but it is a real recurring tax, it argues for resolving OPEN-01/02/05 *toward* the shipped TS behaviour where the choice is otherwise close, and it strengthens (a) as the end state.

**What the kernel must expose for any bridge to be possible** (this is the only UI-shaped obligation the kernel carries, and it is domain-free):

1. **Plugin-tree introspection** — fiber construction/disposal/status events, entry ids, current state, and the failure record of any FAILED fiber, by name. **This is a declared capability, not ambient access**, because K16 (confinement) forbids a fiber from reading another fiber's control fields — a component that can branch on a sibling's lifecycle state is outside the calculus, and this item as first drafted mandated exactly the forbidden surface. The resolution: the **kernel** (which is not a fiber) publishes an `introspection` service key; the bridge plugin, the UI and any telemetry plugin **declare** it like any other dependency; it appears in their load-time capability review; and nothing else can read the tree. Same mechanism, one line of declaration, and confinement survives.
2. **Effect inventory** — `fiber.effects()`, the labelled tree of what a plugin currently holds. This is what makes an honest "what is running" screen possible.
3. **Stable identity + revision** for entries, so the UI can reconcile incrementally rather than re-render the world.
4. **Config schemas** — every plugin's Pydantic model, serialisable, so the settings UI is generated rather than hand-written. This is what makes "everything via the UI" achievable instead of a per-feature chore.

Everything else is a bridge plugin: `ctx.ui_bridge` (host side) plus a browser-side tree.

**Bridge contract v0 (draft, five clauses):**

- **Registration.** A plugin ships both halves in one package: the Python half and a built browser bundle, declared in `pyproject.toml` under `[tool.qma.client]` (path, `inject` topology, an `immediately` flag). The host scans **incrementally, driven off fiber construction/disposal** — the UI asset graph is a *derived view of the plugin tree*, never a parallel registry that can drift.
- **Boot.** The host composes a manifest of `{id, url, rev, inject?, immediately?}` rows, injected as the first script in `<head>`, with plugin-controlled strings escaped. **A page without a valid manifest must not boot** — fail loud, never fall back.
- **Serving.** Bundles at `GET /plugins/<id>/client.js`, content-hash `rev` as cache-buster, `no-cache`; unknown ids **404 loudly** rather than serving SPA HTML as JavaScript. Bundles execute against a shell-held lazy module table, making **cross-plugin value imports a build error** — plugins cooperate only through services, mirroring the backend rule exactly.
- **Composition.** **Slots are the sole composition mechanism.** A `register` call occupies a slot, declares and authorises its child slots, declares its store, and injects its business face. No global component exports, no second registration model. Every rendered entry sits in a **per-entry error boundary** — one crashing card blacks out one card. A pure-UI plugin with zero backend footprint must be possible; if it is not, the bridge is wrong.
- **Transport.** Object layer faces one client interface; carriage is HTTP POST for client→server and one stream per logical server→client channel, behind a reconnect controller with jittered backoff and a generation fence. Reconnect triggers a full refresh plus per-session resync. The transport must not know what a session is. Wire types generated from the Pydantic models, versioned, checked in CI on both sides. **OPEN-20.**

**The caveat that must be written down.** Reversal of the registry is not reversal of the rendered world. The kernel guarantees the slot table returns to its prior state; it cannot return the user's scroll position, focus, in-flight animation — and by K13, pixels already painted are an **emission**. Usually fine, because React re-renders from the restored registry. Not fine wherever a UI plugin's effect reached outside the tab: a downloaded file, a posted form, a clipboard write. Same rule as the backend: reify the handle, treat the output as emitted.

## B.10 Worked walkthrough — building a toy profile under this contract

The goal: a **Toy Scholar** mind that can read notes from somewhere and summarise one. It exists to demonstrate that nothing below touches the kernel, and that swapping *where notes live* is a one-row edit.

**Step 1 — the definition package** (`qma_notes`). Owns the key and the types. Depends on nothing.

```python
# qma_notes/keys.py
from qma.kernel import service_key, waterfall_key, ServiceKey, WaterfallKey

class Note(BaseModel):
    id: str
    title: str
    body: str

class NotesService(Protocol):
    async def list(self) -> list[str]: ...
    async def read(self, note_id: str) -> Note: ...

notes: ServiceKey[NotesService] = service_key("notes", __package__)
note_read: WaterfallKey[[str], Note] = waterfall_key("notes/read", __package__)  # interception point
# ordered-chain key → this package must also publish its ordering rule (K17)
```

**Step 2 — a provider package** (`qma_notes_local`). Implements it against the filesystem.

```python
# qma_notes_local/__init__.py
name = "qma-notes-local"

class Config(BaseModel):
    root: Path

class LocalNotes(Service):
    key = notes
    Config = Config

    def __init__(self, ctx, config):
        super().__init__(ctx, config)          # ← self-registers; provision is an effect (K4).
                                               #    Note it provides BEFORE self.root is set —
                                               #    safe only because a LOADING fiber provides
                                               #    nothing (K7), so no consumer can observe the
                                               #    half-built instance. Do not "fix" the order.
        self.root = config.root

    async def start(self):
        watcher = FileWatcher(self.root)
        yield watcher.close                    # ← teardown FIRST, before anything can throw (K3)
        await watcher.open()

    async def read(self, note_id: str) -> Note:
        return await self.ctx.waterfall(note_read, note_id,
                                        terminal=lambda nid: self._read_from_disk(nid))

apply = LocalNotes
```

Note what is absent: no registration call, no unregister, no cleanup function, no "am I loaded" check. A sibling package `qma_notes_sandbox` implements the same key against a sandbox and shares not one line with this one.

**Step 3 — a consumer package** (`qma_tool_read_note`). Exposes the capability to the model. Depends on the *definition*, never on the provider.

```python
name   = "qma-tool-read-note"
inject = [notes, tools]                        # ← waits for both; no boot order anywhere

def apply(ctx: Context, config: Config) -> None:
    ctx.require(tools).register(ToolDef(
        name="read_note",
        parameters={"note_id": {"type": "string", "required": True}},
        execute=lambda args, exec: ctx.require(notes).read(args["note_id"]),
    ))
    # `register` is an effect owned by THIS fiber, not by the tools service's fiber (K18)
    # → the tool disappears when this plugin unloads. That is not automatic in Python:
    # it is true because ToolsService.register is decorated @registers_for_caller and
    # registers against `self.caller`. See B.2.3 — get this wrong and the tool outlives
    # the plugin, silently, with no error anywhere.
```

**Step 4 — a policy plugin** (`qma_scholar_policy`). This is the shape every hook, permission, guard, budget cap and audit rule takes. Nothing in the tool or the loop is modified.

```python
name   = "qma-scholar-policy"
inject = [tools]

def apply(ctx: Context, config: Config) -> None:
    async def gate(exec: ToolExec, next):
        if exec.tool == "read_note" and not config.allow_private and is_private(exec.args):
            return Deny("private notes are out of scope for this profile")
        return await next()
    ctx.on(tools_pre_execute, gate)             # ← an effect; vanishes on unload
```

**Step 5 — the profile folder.** This is the mind.

```
profiles/toy-scholar/
  profile.yaml
```

```yaml
# profiles/toy-scholar/profile.yaml
- id: notes
  name: qma_notes_local              # ← swap to qma_notes_sandbox: ONE ROW. no code change.
  config: { root: ./corpus }
- id: tools
  name: qma_tools
- id: read-note
  name: qma_tool_read_note
- id: policy
  name: qma_scholar_policy
  config: { allow_private: false }
- id: loop
  name: qma_agent_loop
  config: { model: "<provider>/<model>" }
```

Mounted by one row in the platform recipe:

```yaml
- id: profiles
  group: true
  isolate: { notes: true, tools: true }   # ← this profile gets its OWN notes and tools instances
  config:
    - id: toy-scholar
      name: qma.profile:folder
      config: { path: ./profiles/toy-scholar }
```

**What just happened, checked against the acceptance property:**

- Kernel commits: **zero**. Agent-loop commits: **zero**. Tools-plugin commits: **zero**.
- New code: three small packages, one of which (the policy) is nine lines.
- Load order: **never expressed**. `read-note` waits for `notes` and `tools`; the loader mounts everything concurrently.
- Swap the note store: edit `name:` on one row. Every consumer is torn down, the new provider comes up, consumers restart against it — because provider **identity** changed (K6), not because anyone wrote reconnection logic. **Note what this costs at scale**, because it is the demo and it will be read as the recommendation: this is *exclusive binding*, and the blast radius is every consumer fiber in every realm that names the key. For one profile that is correct and cheap. For `ctx.llm` with hundreds of minds running it is a full reload of the world. The broker shape (B.4, paper §6.2) absorbs the perturbation instead and triggers no consumer reload — **the seam classification must say which shape each key uses**, and the high-traffic ones should not be exclusive. **OPEN-26.**
- Delete the policy row: the gate unregisters itself; nothing else notices.
- The policy plugin raises on startup: it lands in FAILED with the failure recorded against `profiles:toy-scholar:policy` by name, having installed nothing, and **the profile keeps running without it** (K11). That is a product decision the operator can see in the UI, not a crash.
- A second profile mounted beside it with `root: ./other-corpus` gets its **own** notes instance, concurrently, because of `isolate` (K9).
- The model itself writes a fourth plugin at runtime and mounts it: same path, same guarantees, bounded by **OPEN-08**.

If any step above required editing something that already existed, the contract failed. That is the test.

---

# PART C — Open decisions register

Every item is genuinely open. "Draft" is my position, not a decision. Ordered by cost-to-change-later, worst first. Items marked ⚑ are the ones only the operator can settle.

| # | Decision | Draft position |
|---|---|---|
| **OPEN-01** | **Where does the dependent-drain wait live?** The paper puts it ahead of the entire recovery, arguing a wait inside one inverse leaves the rest unordered. The shipped code puts it inside the service-withdrawal disposer, so only the binding deletion is ordered after the drain while the provider's other disposers race it. | ~~Follow the paper.~~ **Position weakened — this is now genuinely undecided.** The paper's arrangement is the stronger promise, but it is unpriced against a *known* failure: DSH local-modification **#12** is a serialized per-Include mutation queue added specifically to fix a **deadlock between loader rollback and HMR teardown drain**. Moving the drain ahead of the entire recovery *enlarges* that deadlock surface rather than shrinking it, because more of the recovery is inside the wait. Whoever ratifies this must reproduce #12's deadlock scenario against the paper's arrangement first. (Note also: the dossier's §5.4 platform note mis-attributes #12 to the watcher — **#9** is the Windows realpath watcher fix, **#12** is the mutation queue. Both are real; they are different modifications.) Whichever we choose, plugin authors will build on what they observe, so it must be written into the contract, not discovered. |
| **OPEN-02** | **Teardown ordering: LIFO, or LIFO-initiated and concurrent?** Theory says LIFO; the implementation gives LIFO initiation and concurrent completion across a fiber's top-level effects, and covers the gap with an authoring rule. | Keep concurrent completion + the authoring rule ("if teardown order matters, keep the registrations inside one `ctx.effect`"), and state the rule loudly in the SDK docs. Revisit if it bites. |
| **OPEN-03** | **Is the inverse ever checked?** The runtime verifies nothing; a correct inverse is an authorial obligation. | Ship a debug mode that snapshots the provided-key set around each effect and flags an inverse that did not restore it. Cheap, catches the most common real failure (a registration that was not withdrawn). Value-level restoration is not checkable and we should not pretend otherwise. |
| **OPEN-04** ⚑ | **Typed identity: key objects or strings?** Decides the entire public plugin API and cannot change after the first third-party plugin ships. | Key objects for the typed path; **package-qualified** string names retained for config, telemetry, catalogs and the UI, resolved through a `qma.keys` entry-point registry (B.1); `ctx.<name>` attribute sugar untyped. This closes OPEN-13's *naming* half; provision collision is K15's job. **A third option neither document evaluated** and which deserves a row before this is ratified: paper §6.4 names **compile-time metaprogramming** as a family that "emits, per dependency, a typed declaration together with an accessor" — in Python, **generating a `.pyi` stub for `Context` at install time from installed plugins' entry points**. That is the closest structural analogue of TS declaration merging that exists here: it would restore typed `ctx.<key>` attribute access, decentralised, with no central file an author edits. Cost: a build step in the install path, and staleness when a plugin is added without re-running it. Rejected-options list previously considered only "a central registry" and "untyped getattr" — this is neither. |
| **OPEN-05** | **Bail sentinel semantics.** Replicate the JS falsy set, or an explicit `NO_RESULT`? One-way door. | **Position reversed — see B.6.** `NO_RESULT` as drafted inverts the failure mode in the most dangerous direction: a listener that falls off the end returns `None`, which under `NO_RESULT` means *"I answered"*, silently truncating the chain and skipping every downstream policy listener. That is the most common Python authoring slip and it is near-certain in model-authored plugins. Draft now: **explicit `Answer(v)` to answer, anything else passes** — which keeps `Answer(None)`/`Answer(False)` expressible (the thing the JS falsy set cannot do) while making the dangerous direction the one you must type. If bare `NO_RESULT` is kept instead, the kernel must reject a listener that returns `None` without an explicit `return`. Shipping "bare `None` = answered" unguarded is not an option. |
| **OPEN-06** | **Cancellation and teardown-failure contract.** If teardown is cancelled or times out, what state is the fiber in? The calculus has no "recovery failed" outcome; we must invent one. Highest-risk Python-specific divergence, invisible until production. | **The mechanism is settled and it is not `asyncio.shield`** — shield protects the inner task but the *awaiter* still receives `CancelledError`, so the K8 drain wait can be abandoned while the inverse runs detached, which is the exact partially-applied accumulator this item exists to prevent. Teardown runs as its own task, joined with an uncancellable `asyncio.wait` (B.3). What remains open: the timeout value, and **what a timed-out teardown is presumed to have left behind**. Terminal `POISONED` state blocks reactivation and is reported by name in the UI. |
| **OPEN-07** ⚑ | **Where is the system boundary drawn, resource by resource?** Must be answered by name for: an in-flight model stream whose provider is unloading (abort / drain / orphan); a spawned subprocess or sandbox; a file written into the user's workspace; a message already shown to the user; a tool call already dispatched to a third party. | Publish the list as a table in the ratified contract. Only the acquisition is revertible; for each emission choose reify / withhold-until-commit / compensate, and say so out loud. Compensation composes LIFO like an inverse but the metatheory does not transfer — do not claim otherwise. |
| **OPEN-08** ⚑ | **Is self-registration bounded?** Progress assumes a finite name set. A harness where a mind authors and mounts its own plugins violates that trivially. What is the quota, the depth limit, and what happens at the ceiling? | Bound before shipping the self-modification tools: per-agent quota on live dynamic plugins, a depth limit on plugin-defining-plugins, and a loud, recorded refusal at the ceiling. This is load-bearing for the whole self-improvement direction. |
| **OPEN-09** ⚑ | **One kernel or two?** (a) port the kernel to TS too; (b) backend-declared UI with a thin renderer; (c) real TS kernel in the browser + Python kernel on the backend, explicitly versioned wire between them. | (c) for v1, (a) as the considered end-state. Refuse (b) — it is a one-way loss of the property that makes the UI extensible. Decide before the UI ships. |
| **OPEN-10** | **Do isolation realms ship in v1?** Two-layer resolution touches every lookup; retrofitting is very expensive. They are what makes per-profile, per-session and per-mind service instances possible. | Yes, in v1, even if the config surface for them lands later. An agent SDK needs them almost immediately. |
| **OPEN-11** | **Does interception ship?** (The ι-metadata chain — per-component access policy, no reload, no graph perturbation.) **Merge semantics are no longer part of this question**: B.4 settles them as a per-key monoid `(ℳ_k, ⊕_k, ε_k)`, right-biased, folded root-closest-first and then **re-validated through the model** — never `model_copy(update=...)`, which is shallow and does not validate. | Defer to v1.1 **or** ship complete — do not half-ship. If deferred, leave the metadata slot in the context so it can be added without touching lookup. **Two dependencies to weigh before deferring:** **OPEN-18** (scoped constants) has *no mechanism at all* without it, and B.8's permissions row would be down to per-capability waterfalls if `internal/get` (B.2.4) were not shipping independently. Note that `internal/*` is **not** gated on this item — that was a conflation in the first draft. |
| **OPEN-12** ⚑ | **Do we adopt the two-bus split?** Live event bus for coordination + a durable, replayable, append-only session log, bridged by exactly one live emit. Needs surface-vs-log-only row tagging and a replace-range operation so compaction can shadow history without rewriting it. | Yes. It is orthogonal to the kernel, arguably the most consequential single borrowing for an agent SDK, and it dictates the shape of persistence, replay, compaction and telemetry. Design it in the same session as memory. |
| **OPEN-13** | **Versioning and key collision.** The paper leaves this open and answers it with npm peer dependencies — a mechanism Python does not have. | Answered by OPEN-04 if key objects win. If strings win, this becomes an unbounded liability in an ecosystem of model-authored plugins and needs its own mechanism. |
| **OPEN-14** | **Does the kernel expose an atomic `replace`?** In-place overwrite of a binding is invisible to dependents by design (K6); replacement must be withdraw-then-install. | Expose `ctx.replace(key, value)` as one guaranteed pair rather than leaving every author to rediscover the rule. Cheap; prevents a whole failure class. **Cover both levels**: the binding *and* the registry entry — DSH's authoring law is that a registered tool definition is "a readonly borrowed same-process contract; never mutate after registration, dispose + re-register to hot-swap", which is the same rule one layer down. An author who learns it at the binding level and not at the registry level has half the protection. |
| **OPEN-15** | **Who allocates entry ids when a model writes configuration?** Ids are the reconciliation key: a changed id is a rebuild, not an update. | A stable id discipline owned by the config-writing plugin (slug from role + monotonic suffix, never renumbered). Without it, every agent edit is a full subtree rebuild. |
| **OPEN-16** | **Is the kernel strictly async-only and single-loop, with no sync public API?** | Yes. The re-entrancy reasoning depends on it. Thread/process work goes behind a service seam. Also decide `asyncio` vs `anyio` — either is fine, but the teardown fan-out must use gather-with-exceptions under both. |
| **OPEN-17** | **How does a resolved service bind to the calling context?** ~~Ergonomics.~~ **Re-filed as a correctness item — see K18 and B.2.3.** Cordis's `Proxy.apply` trap re-traces a service method to the *caller's* context, which is why `ctx.tools.register(...)` unwinds with the consumer. Drop it without a stated law and the natural Python spelling (`self.ctx.effect(...)` inside a service method) binds the effect to the **provider's** fiber, so the registration survives the consumer's unload — a silent, systemic leak class voiding K1/K2 for every registry-style service, and the unstated behaviour B.10 Step 3 was already depending on. | The **law** (K18) is not optional. What is open is only its spelling: (a) explicit two-name facade — `self.ctx` = provider, `self.caller` = caller — with a `@registers_for_caller` decorator asserting ownership at call time; or (b) a descriptor that rewrites `self.ctx` per call, closer to Cordis and closer to invisible. Draft: (a). Either way ship the assertion, because the failure is otherwise undetectable. |
| **OPEN-18** ⚑ | **Scoped constants** (kernel laws → operator platform constants → profile constants, with promote/demote). Does the kernel provide the mechanism, or is it entirely a plugin over `isolate`/`intercept`? | Plugin, using kernel-owned scoping. **But be explicit that this answer is currently empty if OPEN-11 defers.** `isolate` gives different *instances* per realm; it does not give inherited-with-override *values*. Only the `intercept` ι-chain gives the promote/demote semantics `map.md` describes, and B.2 exposes no parent/ancestry accessor a constants plugin could use instead — walking other fibers to find one would violate confinement (K16). So: either OPEN-11 ships, or this lands on the `ctx.settings` layered-resolution borrowing (B.8) instead, which is cheaper and independent. Pick one before promising the operator the dial. The promote/demote dial is an operator-facing product surface and needs its own design pass — flag it for the memory/self-improvement step. |
| **OPEN-19** | **Scope-filtered dispatch.** How does an event reach only the listeners under one agent/session context? | Scope object on dispatch, filtered against each listener's registering context, isolation realm as the default filter — **but the draft's stated default was backwards.** Cordis's default is isolate-label *equality* (`Service[symbols.filter]`), so a root listener does **not** see an isolated child realm's events; `{global: true}` is the explicit opt-out. (DSH's `dsh-scope` layers the opposite convention for its tool events, so the sources genuinely differ.) The draft said "a listener on root hears everything" and offered no escape hatch, which leaves telemetry and the UI bridge — both of which must observe everything — with no sanctioned path. Draft now: **equality default, `scope_global=True` opt-out gated on a declared `observe_all` capability** so the bypass is visible in the load-time review. Settle before the first scoped event ships. Related and unresolved: **events do not cross realms**, so the Delphi-like acceptance profile (inter-mind messaging) needs a realm-crossing *service* provided above the realms, and per-participant loops need per-participant realms — i.e. that acceptance case is gated on **OPEN-10** landing early. |
| **OPEN-20** | **Wire contract versioning between Python and the browser.** | Generate TS types from the Pydantic models, version the whole surface, and gate both sides in CI. Write it down before either side ships. |
| **OPEN-21** | **Hot reload: which tier, and when?** Tier 1 config-only (no import) is free. Tier 2 in-process module swap needs recorded import graphs, accept/decline propagation, `sys.modules` snapshot/restore and two-tier rollback. Tier 3 is a supervised process restart. | Tier 1 in v1; tier 3 always available as the floor. **Tier 2 is gated on two Python problems OPEN-22 does not address, and the dossier's §5.4 hid the first in a parenthetical.** (1) **`get_imports(url)` does not exist in Python.** Algorithms 8 and 9 are pure functions of a runtime import graph; Node supplies one via `ModuleJob.linked`. Python records nothing — `sys.modules` is flat, and a module does not retain what it imported. The dossier's "plus a recorded import set if a custom loader/finder is installed" **is the entire load-bearing piece**, and it is harder than it reads: a `MetaPathFinder` sees *requests*, not *requester attribution*, so recording "who imported what" needs either an import-hook that tracks the executing module frame or a static `ast` pass over the plugin's file set. Cost this before committing to tier 2. (2) **`from x import y` binds a value, ESM binds live.** Evicting and re-importing a module does **not** re-target references held by importers that were not themselves re-imported — so the accept/decline fixpoint has to be conservative in a way Node's does not. Budget Windows path canonicalisation (mod #9) and the serialised mutation queue (mod #12) on top. |
| **OPEN-22** | **Do we enforce no-cross-plugin-value-imports on the Python side?** The browser side makes it a build error; Python has no equivalent enforcement point, and tier-2 reload depends entirely on it. | A load-time import audit that fails loudly. Without it, tier-2 reload is unsafe and the "plugins cooperate only through services" rule is folklore. |
| **OPEN-23** | **Do we ship the seam/core/bundle classification and its completeness guard on day one?** | Yes. It is cheap, it is generated, and it is the only thing that makes the acceptance property auditable rather than a slogan. |
| **OPEN-24** | **What does a mind launched into a remote sandbox need from the kernel?** Cross-process service brokering, or is the remote workload an opaque leaf? | Draft: opaque leaf in v1, reached through a `subprocess`/`sandbox` seam. **State the consequence where the operator will see it** (A.6 limit 3): under this draft a remote mind's registrations are outside the guarantee entirely, so `map.md`'s "reversible execution — a mind that breaks mid-run is recoverable" is not deliverable by the kernel at all, and is a session-log/replay property (**OPEN-12**). The broker of §6.2 is the eventual answer — it makes rolling provider updates an application-level composition rather than an infrastructure operation, and cross-process invocation is one of its three named capabilities — but it must be designed against an asynchronous, mid-flight-failable interface contract from the start. See **OPEN-26**. |
| **OPEN-25** | **Naming of the three access paths.** The draft had `get` enforcing and `find` unchecked; both primary sources have `ctx.get` as the *unchecked store lookup* and the mediated attribute path as the enforcing one (paper §5.1.4, DSH docs §3). | Rename per B.2.1: `require` (enforcing), `find` (declared-optional), `get` (unchecked, **root fiber only**). Only the naming is open — the substance (no undeclared read from any plugin fiber; optional dependencies are declared) is forced by A.2 item 1 and B.2.2 note 2. Alternative: keep `get` enforcing and accept that every author who read either source writes the wrong call. |
| **OPEN-26** | **Exclusive binding or service broker, per seam?** Exclusive binding (the B.10 demo) tears down every consumer on a provider swap; the broker (paper §6.2) absorbs the perturbation and reloads nobody. The choice sets the blast radius of every swap and is invisible until scale. | Classify it **per key, in the seam inventory, on day one** — not per deployment. Draft: exclusive for low-fanout seams (`notes`, `shell`), broker for `llm`, `tools`, `subagents` and anything a remote/cross-process provider will ever back. Not a kernel feature either way; the kernel needs no broker. But retrofitting a broker under live consumers changes their `inject` sets, which is a breaking change to every consumer package. |
| **OPEN-27** ⚑ | **Does a FAILED fiber ever come back?** Paper L-Begin premises `Inactive(⊥)`, so a failed fiber is never re-entered even when its environment changes. The shipped code re-enters it (`_reload` forces epoch to INACTIVE; `_setEpoch` reloads on any later transition out). K11 copied the paper's prose while the state machine had no FAILED→LOADING edge and the contract never said what happens on a *changed* environment. A **third** paper-vs-code divergence, which the dossier's §7 did not catch. | Product-visible: *does a mind whose model provider was briefly down come back by itself?* Draft: **follow the shipped code** — an epoch change re-enters LOADING, an unchanged environment never does — with `retry: never` available per entry for the paper's stricter rule. Add the edge to the state diagram either way. |
| **OPEN-28** | **Does `bail` survive in Python?** A synchronous dispatch mode in an async kernel cannot accept `async def` listeners at all (B.6): calling one from a sync method returns an un-awaited coroutine and the body never runs. The contract rejects such registrations loudly, but that leaves `bail` usable only by fully synchronous policy. | Keep it for now — Cordis uses it for registration-time interception (`internal/listener`), which genuinely must be synchronous. But if no QMA extension point needs it, dropping to four modes is simpler than documenting a trap. Decide when the first internal-event surface is written. |

---

## Provenance

Derived from `research/qma-extensibility-dossier.md` (§1.2 F1–F14, §2 Stages 0–9, §3 UI, §4 essential-vs-incidental, §5 Python analysis, §6 Q1–Q16, §7 conflicts) and the raw studies under `research/raw/` — **six files, four of them load-bearing** (`study-cordiverse-paper.md`, `study-cordis-code.md`, `study-dsh-docs.md`, `study-ui-extensibility.md`; `lean-cli-readme-extraction.md` and `x-timelines-2026-08-18.md` are parked and unrelated).

**Q → OPEN mapping, corrected.** The dossier's Q1–Q15 map onto OPEN-01 … OPEN-15 in the same order. **Q16 is not OPEN-16**: Q16 (no cross-plugin value imports) is **OPEN-22**, and OPEN-16 (async-only, single-loop) comes from dossier §5.3, not the Q-list. The first draft asserted a clean 1:1 through Q16 and was wrong at the last item. OPEN-17 … OPEN-28 are decisions this draft forces, of which OPEN-25 … OPEN-28 were added in the review pass.

**Conflicts.** Two were resolved against primary source in the dossier and are carried here as settled: the browser side of the original is a real second kernel tree (not a conventional SPA), and the paper and shipped code genuinely differ on the drain-wait placement (**OPEN-01**). A **third** divergence was found in this review and is carried as **OPEN-27**: the paper never re-enters a failed fiber (L-Begin premises `Inactive(⊥)`), the shipped code does. The dossier's §7 should carry it as C3.

**One provenance caveat to fix before this reaches the documentation agent.** The dossier's C1 resolution and its Appendix source map cite a *direct re-check of `koishijs/webui` client sources* (`packages/client/client/context.ts`, `index.ts`) that exists in **no file under `research/raw/`** — so as written it is unreproducible. The conclusion is not in doubt: the paper states it directly (§5.3) and the paper study captures that. But the code-level verification must either be captured as a raw note or the claim downgraded to "per the paper".

**Laws added in the review pass.** K15 (disjoint provisions), K16 (confinement), K17 (commutativity as a provider obligation), K18 (caller-attributed registration), K19 (retire-not-remove). The first three are preservation hypotheses the paper imposes and the first draft omitted while invoking the theorems that depend on them; the last two are registration laws whose absence produces silent leaks.
