# Study notes — "A Programming Paradigm for Spatiotemporal Composability" (the Cordis / Cordiverse paper)

**Source of record**
- Repo: https://github.com/cordiverse/paper (2 commits, `main`, ~2.3k stars, 95 forks)
- Paper file: `paper.pdf` → raw: `https://raw.githubusercontent.com/cordiverse/paper/main/paper.pdf`
- 88 pages, PDF 1.7. README states: **Draft of August 13, 2026**, "preprint under active revision… cite the latest version."
- Authors: **Yifan Shi**¹˒², **Wei Zhang**¹, **Tianyi Cui**² — ¹Peking University, ²DeepSeek-AI. (`shigma` is the committer / Cordis+Koishi author.)
- Local working copies made during extraction (scratchpad, ephemeral): `cordis-paper.pdf`, `cordis-paper.txt` (pdftotext -layout, math glyphs dropped), `paper-fc.md` (Firecrawl PDF parse, math preserved — the faithful copy used for these notes).

**Extraction fidelity note.** `pdftotext` loses every math glyph (no ToUnicode map on the math fonts). The Firecrawl PDF parser recovers inline Unicode math plus per-equation LaTeX blocks; these notes are transcribed from that. Equation numbers `(n)`, Definition/Theorem/Lemma numbers, and section numbers below are the paper's own.

---

## 0. Abstract (verbatim)

> Modern software—from plugin systems to self-evolving agent harnesses—increasingly requires *dynamic composition*, yet its formal foundations remain underdeveloped. We identify two orthogonal dimensions of the problem: *temporal composability*, the ability to completely revert a component's side effects upon removal, and *spatial composability*, the ability to declare and reactively manage inter-component dependencies. We address the two dimensions by lifting classical effect and coeffect concepts to runtime mechanisms. In particular, we formalize *revertible effects*, in which every context transformation carries an inverse that the runtime tracks. We formalize *reactive coeffects*, in which each change of the context notifies a component against its coeffect specification. We unify the effect context and the coeffect context into a single *context type*, which constitutes a programming paradigm. After that, we combine these mechanisms into the notion of a *component* and give a calculus of dynamic composition, whose metatheory carries spatiotemporal composability from a single component to a whole system of interleaved components. We implement these ideas in *Cordis*, a meta-framework of spatiotemporal composability that provides a core library with effect tracking and coeffect resolution, as well as a declarative component loader with configuration reconciliation and hot module replacement.

**Table of contents (page anchors).** 1 Introduction (4) · 2 Preliminaries (7) · 3 Revertible Effects and Reactive Coeffects (9) — 3.1 Revertible Effects (9), 3.2 Reactive Coeffects (17), 3.3 The Context Paradigm (22) · 4 A Calculus of Dynamic Composition (28) — 4.1 Components and Fibers (28), 4.2 Base Calculus (30), 4.3 Transitions in Progress (33), 4.4 Metatheory (38) · 5 Implementation and Case Study (54) · 6 Discussion (67) · 7 Related Work (74) · 8 Conclusion (79) · References (80).

---

## 1. Introduction (§1)

### 1.1 Two dimensions of composability
Composition is traditionally **static** (function calls, module imports, class inheritance resolved at compile time). Modern software demands **dynamic composition** — components loaded, unloaded, reconfigured at runtime. Two orthogonal dimensions *beyond the well-studied algebraic aspects*:

- **Temporal composability** (time axis): upon removal of a component, its modifications to the shared environment must be **completely and safely reversed** — tracking every resource allocation, event registration, state mutation, and guaranteeing orderly reclamation.
- **Spatial composability** (space axis): components must **declare, discover, and resolve** dependencies on one another in a structured, verifiable manner — managing dependency topology and coordinating lifecycles in response to dependency changes.

In the **static** setting: temporal composability reduces to lexical scoping (RAII, bracket patterns); spatial composability reduces to module import resolution. In the **dynamic** setting both get much harder: temporal must handle long-lived stateful effects whose scope is *not lexically bounded*; spatial must handle dependencies that **appear, disappear, or change identity** during execution.

### 1.2 Motivating examples

**1.2.1 Plugin systems (VSCode as representative).**
- *Temporal limitation.* All extensions share the extension host process; no mechanism to unload an individual extension's code at runtime. Once `activate` has run, disabling/uninstalling requires restarting the whole host. **Empirical: among the top 100 extensions by install count, 87 contain executable code** (data retrieved from VS Code Marketplace, June 9, 2026) and therefore require a restart on removal. `deactivate` is only a graceful-shutdown callback during host termination — it does not enable live removal, and it **separates effect disposal from effect creation**, violating locality of concern.
- *Spatial limitation.* `extensionDependencies` exists but **only 7 of the top 100 declare it on non-built-in extensions**. The API exposes fixed surface-level extension points (commands, views, language features) so extensions contribute to the *host* rather than depending on each other. `vscode.extensions.getExtension(...).exports` is untyped (`any`) — no checked interface contract.
- These limitations "recur across plugin systems generally, differing only in degree."

**1.2.2 Self-evolving agent harnesses.** *(Directly load-bearing for QMA.)* Modern AI agents rely on runtime **agent harnesses**. Such systems "may compose diverse tool suites and execution environments, govern permissions and sandboxing, maintain session state and persistence, provide context management and memory systems, orchestrate subagents and multi-agent workflows, and expose interfaces to users and automation." A future harness "may generate and deploy modifications to its own components while continuously serving requests." Model-synthesized reusable tools are a narrower precursor. **Each such modification is itself an instance of dynamic composition.**

Because modifications occur continuously with limited/no human oversight:
- Without **temporal** composability: each self-modification forces a full restart discarding all process-local accumulated state; at frequency, cumulative unavailability is substantial and in-flight tasks are repeatedly disrupted; **"even worse, a faulty self-modification can disable the very process needed to recover."**
- Without **spatial** composability: each module must itself detect and adapt to changes in its dependencies by ad hoc means; **"a naive code-replacement strategy may silently break dependents or introduce circular dependencies that surface only at reload time."**

**1.2.3 The coarse-grained workaround.** OSes give temporal composability at *process* granularity; container orchestrators give spatial composability at *service* granularity. Costs: each restart discards caches, connections, partial computations (rebuild takes seconds→minutes); maintaining availability needs redundant replicas; container orchestration cannot express dependencies between components **sharing an address space** and adds network overhead for what could be local calls. "This granularity mismatch demands a compositional abstraction that manages effects and dependencies at the same level as the components themselves."

### 1.3 Contributions (five, verbatim structure)
1. Formalize **revertible effects** (§3.1): every context transformation carries an explicit inverse the runtime tracks; **both tracking and recovery preserve composition**, so the context is recovered upon component removal. → *local temporal composability*.
2. Formalize **reactive coeffects** (§3.2): a component declares required coeffects as a **specification**; each change of context notifies the component against that specification as **activating / deactivating / neutral**. → *local spatial composability*.
3. **Unify** effect context and coeffect context into a single **context type** (§3.3), in which an **observational equivalence on the coeffects supplies the effects with independence** — constituting a programming paradigm.
4. **Calculus of dynamic composition** (§4): combines both into the notion of a **component**, equips its lifecycle with an operational semantics; metatheory carries spatiotemporal composability from one component to a whole interleaved system.
5. **Cordis** (§5): meta-framework — core library (effect tracking + coeffect resolution) + declarative component loader (configuration reconciliation + hot module replacement).

Framing: effects = vocabulary for environmental **modification**; coeffects = vocabulary for environmental **requirements**. Existing formulations restrict to compile-time analysis over lexically fixed scopes. "By lifting effects to a revertible runtime model and coeffects to a reactive dependency resolution mechanism, we obtain a unified formal foundation for dynamic composability, one that is **language-agnostic**."

---

## 2. Preliminaries (§2)

### 2.1 Effects
STLC judgment `Γ ⊢ t : T`. Effect system refines the **type**:

> **(1)** `Γ ⊢ t : T_effect`

- **Monadic effects** (Moggi; Wadler): monad `(T, η, μ)` on category 𝒞; `T(A)`; `η : A → T(A)`; `μ : T(T(A)) → T(A)`. Instances: Maybe, State, IO.
- **Algebraic effects** (Plotkin & Power): algebraic operations determine monads; effect signature Σ declares operations (`get : () → S`, `put : S → ()`). Handlers (Plotkin & Pretnar):

> **(2)** `handle e with { op(v, κ) ↦ … }`

  where κ is the delimited continuation, invocable 0/1/many times. Koka, Eff, OCaml 5.

### 2.2 Coeffects
Dually, coeffect systems enrich the **context**:

> **(3)** `Γ_coeffect ⊢ t : T`

- **Comonadic coeffects** (Uustalu & Vene; Petricek et al.): comonad `(D, ε, δ)`; `ε : D(A) → A` extracts; `δ : D(A) → D(D(A))` duplicates. Environment comonad `D(X) = E × X`; Stream comonad `D(X) = ℕ → X`.
- **Graded coeffects**: pre-ordered semiring 𝒮 = (S, ≤, +, ×, 0, 1) annotates each variable binding: `0` unused, `1` linear, `n` bounded, `∞` unrestricted; `×` sequential, `+` parallel composition. Unified with graded effects by Gaboardi et al.

### 2.3 Relationship to dynamic composability
- Temporal composability ⇒ the relevant effects are the **stateful** ones; undoing a transformation requires it to **admit an inverse**.
- Spatial composability ⇒ dependencies are exactly what coeffects capture; managing them = resolving each against what the environment supplies.
- But classical systems are **static instruments**: effects tracked in lexically fixed scopes, discharged by compile-time handlers; coeffect annotations verified against pre-execution contexts. "No fixed lexical scope can delimit a plugin loaded after deployment; no compile-time context can anticipate dependencies that emerge from runtime configuration."
- ⇒ **Shift in perspective: reify the conceptual structures of effects and coeffects so that a runtime can operate on them directly**, establishing dynamically what these systems provide statically.

---

## 3. Revertible Effects and Reactive Coeffects (§3)

Central idea: turn *typing contexts* carrying effects/coeffects into **context types** — runtime-operable types that reify the context as a **first-class entity**.

### 3.1 Revertible effects (§3.1)

Model of an effect: a function of type **`Γ → Γ × (Γ → Γ)`** — applied to the current context it yields the modified context **together with an explicit inverse**. Supplying the inverse is what lets the effect be reverted; **returning it to the runtime is what makes the effect trackable**.

#### 3.1.1 Effect context (§3.1.1)

Purification: any impure `f_impure : X → Y` becomes `f : Γ × X → Γ × Y`. For fixed `x : X`, the induced map `γ ↦ pr₁(f(γ, x))` captures the side effect independently of the return value. Effects live in the **monoid of transformations `Γ → Γ` under ∘**, whose axioms read directly:
- *Closure* — sequential composition of two effects is an effect;
- *Associativity* — a composite effect is independent of bracketing;
- *Identity* — `id_Γ` is the unit.

Inverses are **one-sided (left inverses)**: "what an inverse is held to is `g ∘ f` and never `f ∘ g`."

> **Definition 1 (twisted composition).**
> **(4)** `(f₁, g₁) ∘ (f₂, g₂) := (f₁ ∘ f₂, g₂ ∘ g₁)`
>
> Left operand acts after the right; **inverses accumulate in the opposite order**. Makes `(Γ→Γ) × (Γ→Γ)` a monoid with unit `(id_Γ, id_Γ)` — the product of the transformation monoid with its **opposite**. Call it the **twisted composition monoid 𝔗_Γ**.

> **Definition 2 (effect context).**
> **(5)** `∂Γ := Γ × (Γ → Γ)`
>
> A pair `(γ, φ)` where `γ : Γ` is the current state and **`φ : Γ → Γ` is the *accumulator*** — the composite of the inverses of the effects performed so far, i.e. the function that recovers the context to its initial state. Initial effect context = `(γ₀, id_Γ)`. Also `∂²Γ = ∂Γ × (∂Γ → ∂Γ)`, and so on **up the tower**.

> **Definition 3 (track).**
> **(6)** `track_Γ : (Γ→Γ) × (Γ→Γ) → ∂Γ → ∂Γ`
> `track_Γ = (f, g) ↦ (γ, φ) ↦ (f(γ), φ ∘ g)`

> **Theorem 4 (projection commutes).** For every `(f,g) ∈ (Γ→Γ)×(Γ→Γ)`:
> **(7)** `pr₁ ∘ track_Γ(f, g) = f ∘ pr₁`
> (Commuting square: Γ —f→ Γ over ∂Γ —f′→ ∂Γ via pr₁ / track.)

> **Theorem 5 (track is a monoid homomorphism)** from 𝔗_Γ into `∂Γ → ∂Γ`:
> 1. `track_Γ(id_Γ, id_Γ) = id_∂Γ`
> 2. **(8)** `track_Γ((f₁,g₁) ∘ (f₂,g₂)) = track_Γ(f₁,g₁) ∘ track_Γ(f₂,g₂)`
>
> Proof key line: `(track(f₁,g₁) ∘ track(f₂,g₂))(γ,φ) = (f₁(f₂(γ)), φ ∘ g₂ ∘ g₁) = track(f₁∘f₂, g₂∘g₁)(γ,φ)`.

> **Definition 6 (recover).**
> **(9)** `recover_Γ : ∂Γ → ∂Γ`, `recover_Γ = (γ, φ) ↦ (φ(γ), id_Γ)`

> **Theorem 7 (recovery is preserved by tracking).** For every `(γ,φ) ∈ ∂Γ` and every pair `(f,g)` with `g(f(γ)) = γ`:
> **(10)** `recover_Γ(track_Γ(f,g)(γ,φ)) = recover_Γ(γ,φ)`

Sequences need no separate argument: with `δ₀ = γ`, `δᵢ = fᵢ(δᵢ₋₁)`, Theorem 5 collapses the composite to `track_Γ(fₙ∘⋯∘f₁, g₁∘⋯∘gₙ)`, and if `gᵢ(δᵢ) = δᵢ₋₁` for every i then `(g₁∘⋯∘gₙ)(δₙ) = δ₀ = γ`, giving

> **(11)** `recover_Γ((track_Γ(fₙ,gₙ) ∘ ⋯ ∘ track_Γ(f₁,g₁))(γ,φ)) = recover_Γ(γ,φ)`

Taking `(γ,φ) = (γ₀, id_Γ)`, recovery carries every reachable state back to `(γ₀, id_Γ)`. A pair with `g ∘ f = id_Γ` meets the hypothesis at **every** state.

**Soundness invariant** of a state in ∂Γ: **`φ(γ) = γ₀`**.

#### 3.1.2 Revertible effect functions (§3.1.2)

Two defects of track/recover: (a) `track_Γ(f,g)` fixes `g` a priori, before any state is seen — one `g` must serve every state; (b) `recover` is all-or-nothing, cannot selectively undo one effect. Fix both by enhancing input and output sides:
1. Input side: `Γ → Γ × (Γ→Γ)`, i.e. **`Γ → ∂Γ`** — the inverse is supplied where the effect is applied.
2. Output side: `∂Γ → ∂Γ × (∂Γ→∂Γ)`, i.e. **`∂Γ → ∂²Γ`** — one effect can be undone while others are retained.

> **Definition 8 (effect function 𝔈_Γ and witnessed effect function 𝔈*_Γ).**
> **(12)**
> `𝔈_Γ := Γ → Γ × (Γ → Γ)`
> `𝔈*_Γ := (e : Γ → Γ × (Γ→Γ)) × ((γ : Γ) → ((δ : Γ) × (g : Γ→Γ) × ((δ, g) = e(γ) → g(δ) = γ)))`
>
> `e(γ)` yields `(δ, g)`: δ is the new context; g is the inverse of the current effect. An element of 𝔈*_Γ **chooses its inverse per state**, and the constraint `g(δ) = γ` holds that choice only to reverting the effect *where it was applied*, leaving g unconstrained elsewhere. A single g with `g ∘ f = id_Γ` meets the constraint everywhere and induces an element of 𝔈*_Γ by `(f,g) ↦ γ ↦ (f(γ), g)`.

> **Definition 9 (effect composition ⋄).**
> **(13)** `f ⋄ g : Γ → ∂Γ`
> `f ⋄ g = γ ↦ let (δ, s) = g(γ) in let (ε, t) = f(δ) in (ε, s ∘ t)`

> **Theorem 10.** ⋄ carries the monoid structure of 𝔗_Γ over to 𝔈_Γ:
> 1. `(𝔈_Γ, ⋄)` is a monoid with unit **`η_Γ := γ ↦ (γ, id_Γ)`**;
> 2. `(f,g) ↦ γ ↦ (f(γ), g)` is a monoid homomorphism 𝔗_Γ → 𝔈_Γ.

> **Theorem 11.** 1. `𝔈*_Γ` is a **submonoid** of `𝔈_Γ` (witnessing survives ⋄); 2. the homomorphism of Thm 10 carries every pair with `g ∘ f = id_Γ` into 𝔈*_Γ.
> Closure proof: `(δ,s)=g(γ)`, `(ε,t)=f(δ)`, `(f⋄g)(γ)=(ε, s∘t)`; `s(δ)=γ`, `t(ε)=δ` ⇒ `(s∘t)(ε)=γ`.

> **Definition 12 (effect lift).**
> **(14)** `effect_Γ : 𝔈_Γ → ∂Γ → ∂²Γ`
> `effect_Γ = e ↦ (γ, φ) ↦ let (δ, g) = e(γ) in ((δ, φ ∘ g), track_Γ(g, pr₁ ∘ e))`
>
> Reading: undoing the effect **is itself an effect**, transforming the state by g; the way to undo *that* is to perform the effect again, which is `pr₁ ∘ e`. So the returned inverse is `track_Γ(g, pr₁ ∘ e)` — a track of the pair with the two directions swapped.

> **Theorem 13.** `effect` preserves ⋄: **(15)** `effect_Γ(f) ⋄ effect_Γ(g) = effect_Γ(f ⋄ g)`.

> **Theorem 14.** With `e ∈ 𝔈_Γ`, `f := pr₁ ∘ e`, `e′ := effect_Γ(e)`, `f′ := pr₁ ∘ e′`:
> 1. `pr₁ ∘ f′ = f ∘ pr₁`;
> 2. for each `(γ,φ)`, the lifted inverse `g′ := pr₂(e′(γ,φ))` and the witnessed inverse `g := pr₂(e(γ))` satisfy `pr₁ ∘ g′ = g ∘ pr₁`.

> **Theorem 15 (the level-lifting boundary).** Let `e ∈ 𝔈*_Γ`, `f := pr₁ ∘ e`, `(δ,g) = e(γ)`, and `(Δ, g′)` the value of `effect_Γ(e)` at `(γ,φ)`. Then
> **(16)** `g′(Δ) = (γ, φ ∘ g ∘ f)`
>
> **The state is recovered exactly.** The accumulator is restored as well — equivalently `effect_Γ(e) ∈ 𝔈*_∂Γ` — **iff `g ∘ f = id_Γ`**; and *in every case* `(φ ∘ g ∘ f)(γ) = φ(γ)`, so **the soundness invariant is preserved**.
>
> Consequence: `effect_Γ` does **not** carry 𝔈*_Γ into 𝔈*_∂Γ in general. What always holds is agreement at γ: `recover_Γ(g′(Δ)) = recover_Γ(γ, φ)` — "reverting leaves the recovery target untouched."

> **Theorem 16 (LIFO reversion needs no extra hypothesis).** Let `e₁,…,eₙ ∈ 𝔈*_Γ` be applied in order from `(γ₀, id_Γ)` and reverted in **reverse order**. Then (1) each revert recovers the context state its application ran against; (2) every intermediate state satisfies the soundness invariant.

#### 3.1.3 Independence of effects (§3.1.3)

Two situations require reverting an inverse at a state *other* than the one its application produced: (a) running an inverse while later effects are still in place — i.e. **withdrawing one component from a running system**; (b) one sequence **interleaving the effects of several components**. Both are questions of **commutation** — of every transformation one effect can perform with every transformation the other can, forward map and yielded inverse alike. "A single accumulator settles neither situation, φ being a composite that runs every inverse it holds in one order and all at once."

> **Definition 17 (transformation monoid).** For `e ∈ 𝔈_Γ`:
> **(17)** `𝔐(e) := ⟨{pr₁ ∘ e} ∪ {pr₂(e(γ)) | γ ∈ Γ}⟩`
> — the submonoid of `Γ→Γ` generated by e's forward map together with every inverse e yields. Its **generators** are the elements of that generating set.

> **Lemma 18.** 1. Commutation is settled on the generators: if every generator of 𝔐(e₁) commutes with every generator of 𝔐(e₂), then every element of 𝔐(e₁) commutes with every element of 𝔐(e₂). 2. `𝔐(e₁ ⋄ e₂) ⊆ ⟨𝔐(e₁) ∪ 𝔐(e₂)⟩` (⋄ enlarges no transformation monoid).

> **Definition 19 (independence).** `e₁, e₂ ∈ 𝔈_Γ` are **independent** when
> **(18)** `∀ f ∈ 𝔐(e₁), g ∈ 𝔐(e₂). f ∘ g = g ∘ f`
> **(19)** `∀ g ∈ 𝔐(e₂), γ ∈ Γ. pr₂(e₁(g(γ))) = pr₂(e₁(γ))`
> — and the same with e₁, e₂ exchanged. Clause (2) says **neither one's transformations disturb the inverse the other yields.** A family `(e_l)_{l∈L}` is **pairwise independent** when `e_l` and `e_{l′}` are independent for every `l ≠ l′`; a family may repeat, and holding an effect independent of itself = holding 𝔐(e) **commutative**.
>
> For effects induced by pairs, clause (1) reduces (via Lemma 18(1)) to commutation of the four pairs `f₁,f₂ ; g₁,g₂ ; f₁,g₂ ; g₁,f₂`, and clause (2) holds outright. **Independence ≠ commutation under ⋄**: `e₁ ⋄ e₂ = e₂ ⋄ e₁` equates composites; independence relates each transformation of one to each of the other, foreign-inverse pairings included.

> **Theorem 20.** Let `e₁,…,eₙ ∈ 𝔈*_Γ` be pairwise independent, applied in order from γ₀. `fᵢ := pr₁ ∘ eᵢ`, `δᵢ := fᵢ(δᵢ₋₁)`, `δ₀ := γ₀`, `gᵢ := pr₂(eᵢ(δᵢ₋₁))`. Fix j and write `δ′ᵢ := (fᵢ ∘ ⋯ ∘ f_{j+1})(δ_{j−1})` for the states of the sequence **with e_j omitted**, so `δ′_j = δ_{j−1}`. Then for every u with `j ≤ u ≤ n`:
> 1. `δ_u = f_j(δ′_u)` and **`g_j(δ_u) = δ′_u`**;
> 2. each `eᵢ` with `i > j` yields at `δ′_{i−1}` **the same inverse `gᵢ`** it yields at `δ_{i−1}`.
>
> Reading: clause (1) locates the state an inverse reaches — **it is the state the same sequence would have reached had the effect never been applied**, whatever ran after it. Clause (2) locates the inverses the others hold there.

> **Corollary 21 (arbitrary revert order).** Under pairwise independence, applying the n inverses at δₙ **in the order of any permutation of {1,…,n} reaches γ₀.**

**Local temporal composability (the criterion, stated in §3.1.3).** "For every sequence of effect functions a component applies, the accumulator recovers the context it began at (Theorem 7), and reverting the sequence hands each inverse the state its own application ran against (Theorem 16). **Loading a component is applying such a sequence and accumulating its inverses in φ; unloading it is applying φ.**"

Two things the local criterion leaves out, both arriving with multiple components: reverting **out of accumulator order**, and a sequence that **interleaves the effects of others**. Independence delivers them (Cor 21) and is a condition on the *effects*, not the construction: §3.3.2 identifies the discipline that meets it; §4.4.2 reads the guarantee off a whole system trace. **Where independence fails, the order has to be carried elsewhere:** within one component by the accumulator (LIFO — §4.3.2); **across components by a declared coeffect**, which orders one activation against another (§4.3.1).

### 3.2 Reactive coeffects (§3.2)

Model: dependencies of a component = a **specification**; each change to the context is **classified against it** as activating / deactivating / neutral. Classification detects a change in satisfaction; responding to it drives activation/deactivation.

#### 3.2.1 Coeffect context (§3.2.1)

Formalizes inversion-of-control (IoC) containers as a coeffect context that synergizes with revertible effects.

> **Definition 22 (coeffect context).** Given a type family `𝒱 : K → Type`,
> **(20)** `Σ := (k : K) ⇀ 𝒱_k`
> — a **dependent partial function type**; `σ : Σ` is a finite partial function assigning to each `k ∈ dom(σ) ⊆ K` a value of type `𝒱_k`. Notation: `σ(k)` application; `σ[k ↦ v]` extension; `σ ∖ k` restriction; `k ∈ dom(σ)` membership.
>
> Preconditions: cannot provide twice (`k ∉ dom(σ)` for extension) nor revoke if absent (`k ∈ dom(σ)` for restriction). A violated precondition is signalled as an error and **produces no transition**, so the effect algebra (which describes the transitions that *do* occur) applies unchanged. Alternative reading: every `Σ ⇀ Σ` as `Σ → Maybe(Σ)` composed in the Maybe monad.

> **Definition 23 (get / set).**
> **(21)**
> `get : (k : K) → Σ ⇀ 𝒱_k`,  `get = k ↦ σ ↦ σ(k)`
> `set : (k : K) × 𝒱_k → Σ ⇀ Σ × (Σ ⇀ Σ)`,  `set = (k, v) ↦ σ ↦ (σ[k ↦ v], λσ′. σ′ ∖ k)`
> — `get(k)` requires `k ∈ dom(σ)`; `set(k,v)` requires `k ∉ dom(σ)`.

**The synergy, stated explicitly:** "`set(k,v)` has type **𝔈*_Σ**, precisely an effect function on the coeffect context. We can therefore directly apply the effect machinery from §3.1: `effect_Σ` provides automatic tracking and recovery of dependency registrations. **This is the synergy between reactive coeffects and revertible effects: coeffect operations are effects, and effects are revertible.**"

> **Definition 24 (a coeffect).** A coeffect at key k is a triple **`(𝒱_k, ≃_k, 𝒜_k)`**: `𝒱_k` the value type; `≃_k` an **equivalence relation on 𝒱_k** up to which values at k are compared (see §3.3.2); `𝒜_k` a set of **coeffect operations** — the operations the value bound at k provides to a component holding it. An operation `a ∈ 𝒜_k` carries argument type `X_a` and outcome type `B_a`:
> **(22)** `a : X_a → 𝒱_k → 𝒱_k × (𝒱_k → 𝒱_k) × B_a`
> — its first two constituents forming a **witnessed effect function on 𝒱_k**, its third an **outcome**. Each operation must **respect ≃_k**: at ≃-related values it is defined at both or neither; where defined it yields ≃-related successors, inverses that again carry ≃-related values to ≃-related values, and **equal outcomes**.
> An operation acts on the coeffect context through its **lift**:
> **(23)** `a^Σ(x)(σ) := let (v, g, b) = a(x)(σ(k)) in (σ[k ↦ v], λσ′. σ′[k ↦ g(σ′(k))], b)`
> defined when `k ∈ dom(σ)`; its first two constituents are an effect function on Σ.
>
> Typing an operation of k on 𝒱_k **confines it to the binding at k** — the lift reads and writes that binding and leaves every other key alone, so no side condition is needed. Under isolation the binding it reaches is the one the realm resolves to (Def 28). An operation whose behaviour turns on another key **reads that key's value into its argument X_a**, and the reactive discipline holds that value fixed for as long as the reading component runs (Theorem 63).

#### 3.2.2 Specification and notification (§3.2.2)

Accessing an absent dependency is a runtime failure ⇒ a component should activate **only once all declared dependencies are present**, not access optimistically.

> **Satisfaction predicate.** For any coeffect specification `d ⊆ K`:
> **(24)** `σ ⊧ d := ∀ k ∈ d. k ∈ dom(σ)`
> Decidable (dom(σ) finite). Since all mutations to σ pass through effect functions (whose inverses recover the previous domain), **changes to satisfaction are detectable at each effect boundary**. "This is the algebraic basis of reactivity: the effect system guarantees that every coeffect change is observed."

> **Definition 25 (coeffect specification).** **(25)** `𝔇_Σ := Set(K)`

> **Definition 26 (notification).** For `d ⊆ K` and states `σ, σ′ ∈ Σ`:
> **(26)**
> ```
> notify_d(σ, σ′) := | activating    if σ ⊭ d ∧ σ′ ⊨ d
>                    | deactivating  if σ ⊨ d ∧ σ′ ⊭ d
>                    | neutral       otherwise
> ```
> **The reactive invariant:** an *activating* transition triggers execution of the component's effects (with full effect tracking); a *deactivating* transition triggers **recovery by applying the accumulator**.

**Local spatial composability (the criterion).** "A component activates only at a state satisfying its specification, so it never reads a binding that is absent, and every change to the context is classified against that specification, so a loss of satisfaction is detected where it happens and drives a deactivation."

**The half the criterion does not cover.** If A provides k and B declares `k ∈ d_B`, then B can activate only after A activated and provided k (since `σ ⊨ d_B` requires `k ∈ dom(σ)`). The converse **fails**: unloading A removes k and breaks B's satisfaction, but a notification cannot by itself (a) keep k readable for as long as B's own teardown needs it, nor (b) hold A's recovery back until B has finished. That is a condition on *other* components ⇒ belongs to the **global** form ⇒ machinery in **§4.3.1**.

#### 3.2.3 Isolation and interception (§3.2.3)

> **Definition 27 (two realizations of an effect function).**
> - **In-place** realization: mutates the context and returns a **nontrivial inverse**; successor aliases the input; recovery runs the inverse to undo the mutation.
> - **Derived** realization: leaves the input intact, returns a **fresh context deriving from it, with the identity as its inverse**; recovery **discards** the derived context.
>
> In a purely functional setting the two coincide; an imperative host may choose either per operation (§5.1.2 implements both). **Isolation and interception are given derived realization outright** — each produces a fresh context whose own table differs from the inherited one, so each is typed as a map context→context rather than as an effect function. Nothing in the shared table changes ⇒ no inverse to track, nothing for Def 12 to lift. Assignment on a derived table **overrides** the inherited value, which is why neither operation carries a precondition.

**Coeffect isolation** — same dependency binds to different values in different contexts (multitenancy, testing, sandboxes).

> **Definition 28.** **(27)** `Σ^iso := (K ⇀ R) × ((r : R) ⇀ 𝒱_r)`, a pair `(ρ, σ)`:
> - `ρ : K ⇀ R` the **isolation realm table**; a key outside `dom(ρ)` resolves to its own realm, so `ρ(k) = k` there (with `R ⊇ K`);
> - `σ : (r : R) ⇀ 𝒱_r` the **dependency table**, from realm identifiers to typed values.
>
> Two-layer resolution decouples logical from storage layer: access k → resolve `ρ(k) = r` → access `σ(r)`.

> **Definition 29 (get / set / isolate on Σ^iso).**
> **(28)**
> `get = k ↦ (ρ,σ) ↦ σ(ρ(k))`
> `set = (k,v) ↦ (ρ,σ) ↦ ((ρ, σ[ρ(k) ↦ v]), λ(ρ′,σ′). (ρ′, σ′ ∖ ρ′(k)))`
> `isolate = (k,r) ↦ (ρ,σ) ↦ (ρ[k ↦ r], σ)`
> Preconditions transported along ρ: `ρ(k) ∈ dom(σ)` / `ρ(k) ∉ dom(σ)`. A key already isolated is **reassigned rather than refused**.
>
> "Coeffect isolation essentially implements a **runtime ad-hoc polymorphism** system." `set` remains an effect function (`𝔈*_{Σ^iso}`) and inherits revertibility; `isolate` needs none, deriving a context instead of writing the shared table.

**Coeffect interception** — cross-cutting metadata on dependency access, adding behavior without modifying the dependency value.

> **Definition 30.** **(29)**
> `Σ^inter := ((k : K) → ℳ_k) × ((k : K) ⇀ (ℳ_k → 𝒱_k))`
> `𝔇^inter := (k : K) ⇀ ℳ_k`
> `Σ^inter` is a pair `(ι, σ)`: ι is **context-carried** metadata installed on the context itself, empty (`ε_k`) by default; σ maps each key to a **provider function** from metadata to value. A specification `d ∈ 𝔇^inter` carries **component-declared** metadata `d(k)`, with `dom(d)` serving as the dependency set. Each key equips its metadata with a monoid `(ℳ_k, ⊕_k, ε_k)`.

> **Definition 31 (get / set / intercept on Σ^inter).**
> **(30)**
> `get = (k, μ) ↦ (ι,σ) ↦ σ(k)(μ ⊕_k ι(k))`
> `set = (k, ψ) ↦ (ι,σ) ↦ ((ι, σ[k ↦ ψ]), λ(ι′,σ′). (ι′, σ′ ∖ k))`
> `intercept = (k, ν) ↦ (ι,σ) ↦ (ι[k ↦ ι(k) ⊕_k ν], σ)`
>
> When a component with specification d accesses k, the system evaluates **`σ(k)(d(k) ⊕_k ι(k))`**. The merge follows each key's own semantics (scalars overwritten, sets unioned) and is **right-biased**, so `ι(k)` takes priority and can **override the component's declaration** — letting an enclosing context constrain how a component uses a coeffect **without modifying that component** (cf. §6.3 access control).

### 3.3 The context paradigm (§3.3)

#### 3.3.1 Unified context (§3.3.1)

> **Definition 32 (the context type).**
> **(31)** `Γ_∞ := μΓ. Γ × (Γ → Γ) × Σ`
> Projections: **Γ** the current context state (recursive); **Γ → Γ** the accumulator recovering this level's effects; **Σ** the coeffect context carrying dependency information.
>
> Under this definition `effect` maps `𝔈_{Γ_∞}` to itself, **unifying the ∂-tower into a single self-similar type**. Σ is structurally integrated: `set`/`get` act on Σ and the accumulator tracks their reversal. **Since 𝒱 is unconstrained, any state the system needs to share across components can be encoded as a dependency with an appropriate value type — Σ subsumes all shared mutable state, not just inter-component dependencies. Every interaction between a component and its environment passes through this single entity.**

**Hierarchical composition.** The recursion supports a **tree-shaped control structure**: a parent context aggregates multiple child-level effects. The effect transformation realizes a literal "plug-in" metaphor:
- Loading a component = executing its effects (plugging in);
- Unloading = recovering its effects (unplugging, **without affecting other running components**);
- Components at different levels are independently loadable/unloadable; a parent aggregates and manages all its children's effects, enabling **arbitrarily nested composition**.

#### 3.3.2 Observational equivalence (§3.3.2)

Motivation: exact state equality is an idealization — `free` releases a block without restoring the heap layout `malloc` found; a **generative name** is not restored by the inverse that discards it (the next creation draws a fresh one). So all §3 equalities are read **up to an equivalence ≃**, taken to be an **observational equivalence**: two states are related when no observer can distinguish them. What an observer of a context is given is **the coeffects it carries**, each of which arrives with its own equivalence (Def 24), so the relation on a context is assembled from theirs.

> **Definition 33.** **(32)**
> `σ ≃ σ′ := dom(σ) = dom(σ′) ∧ ∀ k ∈ dom(σ). σ(k) ≃_k σ′(k)`
> `γ ≃ γ′ := σ_γ ≃ σ_{γ′}`
> (writing σ_γ for the coeffect projection of γ).
>
> "**The part of a state that no key binds is thereby forgotten**" — heap layout, generative names lie outside the relation unless some key binds them. Related states have the same domain ⇒ agree on `σ ⊨ d` and on `notify_d` ⇒ **reactivity is a property of Σ/≃**.

> **Definition 34 (tests and indistinguishability).** Let V carry a set 𝒜 of operations (Def 24), and 𝔐(a) the transformation monoid of the effect functions `a(x)` over every argument `x : X_a`. A **test** over 𝒜 is a **finite word over the generators of the monoids 𝔐(a), a ∈ 𝒜**, each letter applied to the value the letters before it left; its **outcomes** are those the forward-map letters yield along the way; it is undefined where a precondition fails. `v ≈_𝒜 v′` (**indistinguishable**) when every test is defined at both or neither and yields the same outcomes.

> **Lemma 35.** Indistinguishability is the **coarsest** relation the operations respect: (1) every operation respects `≈_𝒜`; (2) every equivalence that every operation respects is contained in `≈_𝒜`. Hence every admissible ≃_k ⊆ ≈_{𝒜_k}, and ≈_{𝒜_k} is itself admissible.

> **Definition 36.** `f : Γ → Γ` **respects ≃** when **(33)** `∀γ,γ′. γ ≃ γ′ ⇒ f(γ) ≃ f(γ′)`. And **(34)** `f ≃ g := ∀γ. f(γ) ≃ g(γ)`; `(δ,g) ≃ (δ′,g′) := δ ≃ δ′ ∧ g ≃ g′`.
> A map respecting ≃ descends to Γ/≃; two ≃-related maps descend to the same map. **An effect function needs both**: the first so the state it computes is determined on the quotient, the second so the **inverse it returns** is.

> **Definition 37 (Def 8 read up to ≃).** `e ∈ 𝔈_Γ` lies in `𝔈*_Γ` when e respects ≃ as a map Γ → ∂Γ and, writing `(δ,g) = e(γ)`, for every γ: (1) `g(δ) ≃ γ`; (2) g respects ≃. Taking ≃ = equality recovers Def 8.

> **Lemma 38.** With 𝔈*_Γ read as in Def 37, **every equality of states asserted in §3.1 holds with `=` replaced by `≃`**, and the accumulator of every state reachable from `(γ₀, id_Γ)` respects ≃. (Soundness invariant becomes `φ(γ) ≃ γ₀`.)

> **Definition 39 (independent operations; commutative key).** Operations a, a′ are **independent** when their lifts are independent as effect functions (Def 19) at every pair of arguments, **and neither one's transformations disturb the outcome the other yields**:
> **(35)** `∀ x : X_a, g ∈ 𝔐(a′^Σ), σ ∈ Σ. pr₃(a^Σ(x)(g(σ))) = pr₃(a^Σ(x)(σ))`
> (and symmetrically). A key k is **commutative** when any two operations of 𝒜_k are independent, **an operation being held independent of itself as well**.

> **Theorem 40.** **Operations at distinct keys are independent.** (Each generator is `σ ↦ σ[k ↦ u(σ(k))]`; two such at distinct keys commute; Lemma 18(1) extends to the monoids; and what a^Σ yields at σ is determined by σ(k), which the other's generators leave alone.)

**Which keys are commutative — the design rule.** "A key whose value is a **table of entries added and removed independently** is commutative — registration of a route or of an event listener being the representative case: two registrations in either order leave a table that answers every test alike, and either registration can be withdrawn while the other stands. **A key whose value is an ordered chain is not**, since a middleware inserted before another sees a different request, and neither order can be withdrawn without disturbing the other." The allocator divides by what its interface publishes: where handles are compared by no operation, ≃_k may relate two heaps **up to a renaming of handles** (as CompCert relates memory states of a program and its translation) and allocation is commutative; where addresses are outcomes compared by equality, **no admissible ≃_k makes the two orders agree** and the key is not commutative.

> **Definition 41 (coeffect-mediated effect functions).** `𝔈^𝒜_Σ ⊆ 𝔈_Σ` is the **least set** containing the unit `η_Σ` and closed under: for a key k, an operation `a ∈ 𝒜_k`, an argument `x : X_a`, and a family `(e_b)_{b ∈ B_a}` of members,
> **(36)** `γ ↦ let (δ, s, b) = a^Σ(x)(σ) in let (ε, t) = e_b(δ) in (ε, s ∘ t)`
> is again a member. **Each stage performs one operation and chooses what follows it by the outcome**, so an argument may depend on outcomes already obtained. The operations *occurring in* a member are the ones its stages perform, over every choice of outcome.

> **Theorem 42 (the bridge — commutative keys ⇒ independence).** Let `e₁, e₂ ∈ 𝔈^𝒜_Σ` and let **every key at which operations of both occur be commutative** (Def 39). Then e₁ and e₂ are independent (Def 19).

**The payoff, stated in §3.3.2.** Since 𝒱 is unconstrained, a system may bind **every location it shares across components at a key of its own**. A component's effect function is then the lift of a coeffect-mediated one along the coeffect projection, and independence transfers to that lift. "**The assumption §3.1.3 leaves open is met that way, and with it the temporal composability of a whole system of components.**"

**The decomposition principle (quotable).** "What the decomposition divides is a computation's **commuting part** from its **order-sensitive part**. The commuting part is carried by the **effects**: a component performs them in whatever order its task calls for, and Corollary 21 reverts them in whatever order the system finds convenient, **no two components constraining each other**. The order-sensitive part is carried by the **coeffects**, since a key whose operations do not commute is one whose order has to be imposed from outside the effects, and two places are available for imposing it. **Within one component the accumulator imposes it (LIFO, Thm 16). Across components a declared coeffect imposes it**, one component providing what another declares and the provision preceding the declaration's satisfaction (§3.2.2). **Composability is thereby had at the grain of components rather than of single effects.**"

Two named limits: (a) binding every shared location at a key is the paradigm's **discipline**, not a property of the construction — a location the system cannot reify as a coeffect lies outside the boundary of §6.1 and outside the theorem; (b) **commutativity of a key is a property of the interface that key publishes**, so meeting it is an obligation on the **provider** of the key, not on consumers.

#### 3.3.3 Situating the context paradigm (§3.3.3)

Two poles:
- **Explicit state threading (functional).** State monad `S → (A, S)` threads environment through every computation. Strong compositional guarantees (effects visible in types, equational reasoning) but heavy ergonomic cost: every function in the chain must accept/return the state even when passing it through; monadic stacking / effect-handler boilerplate proliferates as effect dimensions grow.
- **Implicit mutation (imperative/OOP).** React's `useEffect` registers a persistent side effect on the component's internal **fiber**, yet neither the effect target nor the registration mechanism appears as a parameter — **identification relies on call-order position within hidden runtime state**. Java's service-locator (`ApplicationContext.getBean(...)`) retrieves dependencies from a process-wide registry with null checks and casts; dependency relationships implicit and scattered. Understanding how `f()` modifies or depends on the system requires reading its implementation **transitively**; refactoring is fragile.

**The context paradigm combines the traceability of the functional approach with the ergonomics of the imperative approach.** Effects and coeffects are both mediated through an **explicit context parameter**, so **each operation is attributable to the specific context on which it was invoked, and hence to the component that context belongs to.**

Beyond combining the poles: the developer handles each effect/dependency **individually** and the system composes them automatically. For revertible effects: the developer supplies the inverse of **each atomic operation**, and the inverse of any composite follows by composition — "**a component's teardown is derived from its loading rather than written alongside it.**" For reactive coeffects: a component declares only what it needs, and the runtime resolves and **re-wires** them automatically as providers are added, removed, or replaced. "In both directions, correctness that would otherwise rest on developer discipline becomes a **structural property of the paradigm**."

---

## 4. A Calculus of Dynamic Composition (§4)

Structure: §4.1–4.2 give the **smallest** calculus, taking each transition to be **atomic, immediate, and infallible**; §4.3 drops all three (plus adds withdrawal ordering), arriving at the calculus a real runtime implements; §4.4 gives the metatheory — **preservation, global temporal and spatial composability, progress, confluence**.

### 4.1 Components and fibers (§4.1)

> **Definition 43 (component).**
> **(37)** `ℭ_Γ := 𝔇_Γ × 𝔓_Γ × 𝔈*_Γ` — a triple `(d, p, e)`:
> - `d : 𝔇_Γ` the **coeffect specification** (Def 25) — dependencies required from the environment;
> - `p : 𝔓_Γ := Set(K)` the **provision** — the coeffect keys the component may provide; **no key outside p is one its effect function writes**;
> - `e : 𝔈*_Γ` the **witnessed effect function** (Def 8) — the effects contributed when active, together with the inverse that withdraws them.
>
> "The two declarations are the two directions of one interface." §4.2 admits **no two fibers of one registry whose provisions meet** (disjointness). This calculus reads every key at **one shared realm** (no realms here), which makes disjointness the right condition and each key's provider unique. Consequence: **a component with a non-empty provision has one fiber at a time**; the many-instantiation cases below are of components providing nothing (the common case of a component that only consumes, or that registers others).

Lifecycle: an **activation** executes e, accumulating side effects; a **deactivation** applies the accumulator to recover the context. Simplest form = two-state model of **Figure 1** (Inactive ⇄ Active).

> **Definition 44 (fiber).** Fix a set 𝔑 of fiber names. A fiber instantiating `(d,p,e) ∈ ℭ_Γ` is `⟨d, p, e, π, σ, τ, θ⟩`:
> - `d, p, e` as in Def 43;
> - `π : 𝔑 ∪ {root}` the **parent** — the fiber this one was instantiated under, or the root marker;
> - `σ : Σ` the fiber's **own coeffect table**, empty until it activates and written by its effects as they run;
> - `τ : {⊥, ⊤}` the **retirement flag**, ⊥ in a fresh fiber, ⊤ once the orchestrator has retired it;
> - `θ : Θ_Γ` the **lifecycle state**; in the two-state model
>   **(38)** `Θ := Inactive | Active(g, ω)` where `g : Γ → Γ` is the **accumulator** and `ω : d → 𝔑` the **committed view**.
>
> The **committed view ω** sends each declared key to **the name of the fiber that provided it when the transition committed**.

> **Definition 45 (registry).** `𝔉_Γ` = set of fibers over Γ. A state `γ ∈ Γ` carries a registry
> **(39)** `F_γ : 𝔑 ⇀ 𝔉_Γ`
> a finite partial function whose **parent pointers form a tree rooted at `root`**, together with whatever else in Γ no fiber's σ names. Write `γ(n)` for `F_γ(n)`, and subscript fields by name: `d_n, p_n, e_n, π_n, σ_n, τ_n, θ_n`, with `g_n, ω_n` the accumulator and committed view θ_n carries. `γ[θ_n ↦ θ′]`, `γ[n ↦ ⟨⋯⟩]`, `γ ∖ n` edit one field / one fiber / presence.

**Names are atoms.** "No rule computes one, inspects its structure, or relates two of them by anything but equality, and introducing a fiber simply draws one not already in use. This is the discipline of **dynamically created local names**, used here for fiber identity."

**The coeffect context is derived, not stored:**
> **(40)** `σ_γ := ⋃ { σ_m | m ∈ dom(F_γ), θ_m = Active(−,−) }`
>
> Well defined because `dom(σ_n) ⊆ p_n` and provisions of distinct fibers are disjoint ⇒ each `k ∈ dom(σ_γ)` lies in the table of exactly one **Active** fiber, whose name is `provider_k(γ)`. **Each key has one possible provider, fixed by the provisions and not by the state.** No rule writes σ_n directly: a fiber's provisions are the `set` operations its own effect function performs. **Only the coeffect part of an effect is recorded this way** — effects mutating state elsewhere in γ are tracked by g like any other, but no fiber can name them in a specification, so **they contribute no ordering constraint**.

`γ ⊨ d` abbreviates `σ_γ ⊨ d`. Taking the union over **Active** fibers alone "is what lets a fiber **cease to provide before it has withdrawn anything**", which §4.3.1 turns into the ordering discipline.

### 4.2 The base calculus (§4.2)

> **Definition 46 (target view / quiescence).**
> **(41)** `target_n(γ) := ⊥` if `τ_n ∨ ¬(γ ⊨ d_n)`; otherwise `(k ∈ d_n) ↦ provider_k(γ)`
> **(42)** `quiet(γ) := ∀ n ∈ dom(F_γ).` [ `target_n(γ) = ⊥` if `θ_n = Inactive`; `target_n(γ) = ω_n` if `θ_n = Active(−, ω_n)` ]
>
> "The target answers to two things and to nothing else: **retirement**, through τ_n, and **coeffect resolution**, through `γ ⊨ d_n` and `provider_k`."
>
> The **committed view has the same type as the target view, and the lifecycle is driven by comparing them**: ω_n is the resolution n activated against; `target_n(γ)` is the one it should be running against; every rule fires on their agreeing or differing. **Recording a provider rather than a value is what makes the comparison usable** — a different fiber providing an equal value would otherwise compare equal.

**Rules.** Two relations: **orchestration** rules (prefix `O-`, written `γ ⇒ δ`) are actions the orchestrator *may* perform (premises say when legal, not when it occurs); **lifecycle** rules (prefix `L-`, written `γ ⟶ δ`) are steps the system takes **unprompted** whenever premises hold. `⟶*` means lifecycle steps alone.

```
n ∉ dom(F_γ)   π ∈ dom(F_γ) ∪ {root}   (d,p,e) ∈ ℭ_Γ   ∀m ∈ dom(F_γ). p ∩ p_m = ∅
──────────────────────────────────────────────────────────────────────────────────── O-Insert
              γ ⇒ γ[n ↦ ⟨d, p, e, π, ∅, ⊥, Inactive⟩]

  n ∈ dom(F_γ)                                τ_n = ⊤   θ_n = Inactive   ∀m. π_m ≠ n
──────────────────── O-Retire               ───────────────────────────────────────── O-Remove
γ ⇒ γ[τ_n ↦ ⊤]                                            γ ⇒ γ ∖ n

θ_n = Inactive   ω = target_n(γ) ≠ ⊥   e_n(γ) = (δ, g)
────────────────────────────────────────────────────── L-Reload
       γ ⟶ δ[θ_n ↦ Active(g, ω)]

θ_n = Active(g, ω)   target_n(γ) ≠ ω   g(γ) = δ
─────────────────────────────────────────────── L-Unload
        γ ⟶ δ[θ_n ↦ Inactive]
```

Commentary: **insertion and retirement are the only external inputs**; the orchestrator never sets a lifecycle state directly. O-Retire is unconditional (retiring is a *request*; lifecycle rules carry it out). Retirement is separated from removal because a retired-but-Active fiber must first be deactivated — **removing it earlier would discard the accumulator and leak**. `∀m. π_m ≠ n` keeps the tree well-formed (children removed before parent). **The last premise of O-Insert is where the single-source discipline is imposed.**

> **Definition 47 (registration primitive).** An application of `e_n` (or one of its iterations, §4.3.2) may **register** a component `(d,p,e) ∈ ℭ_Γ`. In place of a state map it takes the **O-Insert** of that component with `π = n`, and it yields **as its inverse the O-Retire** of the fiber so registered. The rule draws the name (subject to O-Insert's freshness premise) and hands it to the effect function.
>
> Why retire rather than remove: **an inverse has to apply wherever it is reached.** O-Remove carries premises so an inverse built from it can fail; O-Retire has only `n ∈ dom(F_γ)`. The entry it leaves behind is retired, `Inactive(⊥)`, holding an empty table — the **vestigial entry** of Lemma 57, differing from absence in control fields alone, which no rule tells apart. A grandchild is reached one level at a time (the child's own accumulator retires what the child registered).

> **Definition 48 (confinement).** `f : Γ → Γ` is **confined to n** when for every γ with `n ∈ dom(F_γ)`, writing `δ = f(γ)`:
> 1. *(Writes.)* `dom(F_δ) = dom(F_γ)`, `δ(m) = γ(m)` for every `m ≠ n`, and `δ(n)`, `γ(n)` **differ in σ alone**;
> 2. *(Reads.)* two states agreeing on `σ_n`, on the restrictions `σ_m|_{d_n}` for every m, and on the part of the state no fiber's table names, are carried by f to states agreeing on the same three.
>
> An effect function e is confined to n when **every** application (and each iteration) either **registers** a component (Def 47) or has both its state map `pr₁ ∘ e` and the inverse it yields confined to n. **Every fiber's effect function is required to be confined to that fiber.**
>
> Clause (2) is why a component may read the values it declared (those lie in providers' tables). What it may **not** read is a table outside `d_n`, or **any control field** — which is what keeps a component from branching on the lifecycle state of a fiber it did not declare.

**The rules are nondeterministic and reactive-only** — no rule mentions a scheduler, so a theorem proved over all step sequences **holds for every scheduling policy a runtime might adopt.**

### 4.3 Transitions in progress (§4.3)

> **Definition 49 (extended lifecycle states).**
> **(43)** `Θ_Γ := Inactive(ζ) | Reloading(i, g, ω) | Active(g, ω) | Unloading(g, ω, ζ)`
> where `i : 𝔈^{iter*}_Γ` is the **remaining effect iterator** (Def 51), `g` the accumulator built so far, `ω` the committed view, and `ζ : {⊥} ∪ Ξ` the **outcome** — carried by Unloading as the one its deactivation is headed for and by Inactive as the one it reached (⊥ or an error from Ξ, §4.3.4).
>
> **(44)** `installed_n(γ) := θ_n ≠ Inactive(−)`;  `failed_n(γ) := ∃ξ ∈ Ξ. θ_n = Inactive(ξ)`
> An installed fiber n **resolves k to m** when `ω_n(k) = m`.
> **(45)** `quiet(γ) := ∀n.` [ `ζ ≠ ⊥ ∨ target_n(γ) = ⊥` if `θ_n = Inactive(ζ)`; `target_n(γ) = ω_n` if `θ_n = Active(−, ω_n)`; `⊥` otherwise ]
>
> **Crucially:** `σ_γ` still unions the tables of **Active** fibers alone, so **a fiber whose transition is under way in either direction reads its coeffects through the ω it holds and provides none of its own**; a key its transition has already written is **not yet** one a dependent may activate against.

**Figure 2** — lifecycle with transitions in progress (two transition states outlined):
```
                 L-Iter (self-loop)
        L-Begin ──────► Reloading ──── L-Finish ────►
   Inactive                │  │                        Active
        ▲                  │  └── L-Divert ──┐          │
        │                  └──── L-Raise ────┤          │ L-Leave
        └──── L-Unload ───── Unloading ◄─────┴──────────┘
```

#### 4.3.1 Withdrawal (§4.3.1)

The substantive half: **a component being torn down because its provider is going away is running its own teardown code, which may need the very coeffect that is being withdrawn** (closing a connection pool means handing connections back). What must be delivered: **a consumer can still read k throughout its own deactivation, and the provider's withdrawal of k takes effect only afterwards.** The base calculus cannot: its L-Unload removes provisions and runs the inverse **together**, leaving no interval.

> **Definition 50 (relied upon).**
> **(46)** `relied_n(γ) := ∃ m ∈ dom(F_γ), k ∈ d_m. m ≠ n ∧ installed_m(γ) ∧ ω_m(k) = n`

```
θ_n = Active(g, ω)   target_n(γ) ≠ ω              θ_n = Unloading(g, ω, ζ)   ¬relied_n(γ)   g(γ) = δ
──────────────────────────────────── L-Leave     ─────────────────────────────────────────────────── L-Unload
γ ⟶ γ[θ_n ↦ Unloading(g, ω, ⊥)]                          γ ⟶ δ[θ_n ↦ Inactive(ζ)]
```

- **L-Leave records the decision to deactivate without acting on it** — it stops the fiber providing its coeffects while leaving its own committed view and everyone else's intact.
- **L-Unload is the only rule in the calculus that applies an accumulator.**
- The two halves of the ordering are carried by different parts of the form: the **visibility** half by the committed view (which L-Unload discards as its last act), and the **ordering** half by the premise `¬relied_n(γ)` — **the guard**. Theorem 63 establishes both.
- The guard is **per binding, not per fiber**: a fiber declaring none of n's keys is no obstacle, nor is one that resolved a key of n's in another realm.
- **Why it does not deadlock:** once L-Leave has marked n, its table leaves σ_γ, so **no target view can name n any longer**, and every consumer that committed to n is itself on its way out. Theorem 66 turns that into "the guard always releases."
- The guard **orders deactivations along coeffects and not along the fiber tree**: a parent may run its inverse while a child is still Unloading (relied speaks only of committed views). Parent/child are ordered more weakly than provider/consumer; parent-and-child effects meeting in ambient state are governed by the **independence hypothesis** of Def 60 instead.

#### 4.3.2 Iteration (§4.3.2)

> **Definition 51 (effect iterator).**
> **(47)**
> `𝔈^iter_Γ := μℐ. Γ → Γ × (Γ→Γ) × Maybe(ℐ)`
> `𝔈^{iter*}_Γ := μℐ. (e : Γ → Γ × (Γ→Γ) × Maybe(ℐ)) × ((γ : Γ) → (let (δ, g, o) = e(γ) in g(δ) ≃ γ))`
> `e(γ)` yields `(δ, g, o)`: δ the new context, g the inverse of the current effect, o the continuation — **Nothing** signals termination, **Just(i)** provides the next iteration.
> Witness read at the ≃ of Def 33; triples compared componentwise; ≃ on iterators is the **greatest** relation meeting those clauses (coinductive).

> **Definition 52 (effect iterator transformation).**
> **(48)** `effect^iter_Γ : 𝔈^iter_Γ → ∂Γ → ∂²Γ`
> ```
> effect^iter_Γ = i ↦ (γ, φ) ↦
>   let (δ, g, o) = i(γ) in
>   let t = track_Γ(g, pr₁ ∘ i) in
>   match o
>   | Nothing  ⇒ ((δ, φ ∘ g), t)
>   | Just(i′) ⇒ let (s, r) = effect^iter_Γ(i′)(δ, φ ∘ g) in (s, t ∘ r)
> ```
> At each iteration the inverse g is composed onto φ **in application order**, so the accumulator `φ ∘ g₁ ∘ ⋯ ∘ g_k` **recovers effects in LIFO order when applied**. Because `effect^iter_Γ` lands in the same `∂Γ → ∂²Γ` as `effect_Γ`, **an iterator is an effect in its own right and can be used wherever an effect can.**
>
> "The `Maybe(𝔈^iter)` continuation makes a **boundary** available between any two consecutive iterations, at which the context is whatever the iterations so far have made it and the accumulator recovers those and nothing more. **In this sense the effect iterator is a reified delimited continuation, the structure that mainstream languages expose through the `yield` operator**, so the model maps directly onto the generators they already provide."

From here on `e_n` is read at `𝔈^{iter*}_Γ`. Rules:
```
θ_n = Inactive(⊥)   ω = target_n(γ) ≠ ⊥
─────────────────────────────────────────────────────── L-Begin
γ ⟶ γ[θ_n ↦ Reloading(e_n, id_Γ, ω)]

θ_n = Reloading(i,g,ω)   target_n(γ) ≠ ω   (δ,h) = (γ, id_Γ) ∨ i(γ) = (δ,h,−)
──────────────────────────────────────────────────────────────────────────── L-Divert
γ ⟶ δ[θ_n ↦ Unloading(g ∘ h, ω, ⊥)]

θ_n = Reloading(i,g,ω)   target_n(γ) = ω   i(γ) = (δ,h,Just(i′))
──────────────────────────────────────────────────────────────── L-Iter
γ ⟶ δ[θ_n ↦ Reloading(i′, g ∘ h, ω)]

θ_n = Reloading(i,g,ω)   target_n(γ) = ω   i(γ) = (δ,h,Nothing)
─────────────────────────────────────────────────────────────── L-Finish
γ ⟶ δ[θ_n ↦ Active(g ∘ h, ω)]
```
Between any two consecutive iterations the system may **divert** if the target view changed. **L-Divert routes through Unloading** like every other deactivation rather than applying the accumulator in place; the guard it meets there is **vacuous** (a fiber that has never been Active provides nothing and appears in no committed view). L-Divert's **first alternative aborts** the iteration the fiber is holding — only an iteration boundary makes that possible, so **the granularity at which a divert may fall is that of the iterator**; the **second lets that iteration land** (needed by §4.3.3).

A plain effect function `𝔈_Γ` is the degenerate iterator that yields Nothing first: the transition still passes through Reloading, L-Divert still applies, but the accumulator is `id_Γ` — **the transition installs either all of its effects or none of them.**

#### 4.3.3 Asynchrony (§4.3.3)

An iteration yields a value of type **`Future(A)`** — an opaque type constructor "whose defining property is that between submission and resolution, external state may change." The fiber is **Reloading** while an iteration is in flight.

**Inertia:** "**once launched, an iteration lands, and its landing cannot be declined.**" A target view that turns during flight therefore cannot be answered by aborting; only the **landing** alternative of L-Divert remains: the iteration lands, and the fiber deactivates afterwards. **This layer adds no rule and no type** — at the granularity of Γ, inertia is its whole content, taking the form of a restriction on which alternative of L-Divert a host may take.

Why routing through Unloading is the only sound place: routing through **Active** instead "would let the fiber provide its coeffects for the length of one step and oblige its dependents to activate against a component that is already leaving." **This is the mutual chaining of reload and unload in the implementation.**

A deactivation may also chain straight back into an activation, **by a composite rather than a rule**: L-Unload carries **no premise on the target view**, so the accumulator runs, the fiber becomes Inactive, and L-Begin may immediately start a new transition.

#### 4.3.4 Failure (§4.3.4)

"The effects a component installs reach outside the context that tracks them, and what they reach may refuse: a port already bound, a file that is not there, a peer that does not answer."

> **(49)**
> `𝔈^fail_Γ := μℐ. Γ → Either(Ξ, Γ × (Γ→Γ) × Maybe(ℐ))`
> `𝔈^{fail*}_Γ := μℐ. (e : Γ → Either(Ξ, Γ × (Γ→Γ) × Maybe(ℐ))) × ((γ : Γ) → (let Right(δ,g,o) = e(γ) in g(δ) ≃ γ))`
> The witness constrains the **Right** case alone — **a raise has nothing to undo**. Premises of L-Iter, L-Finish, L-Divert are read with `Right` around the triple.

```
θ_n = Reloading(i, g, ω)   i(γ) = Left(ξ)
───────────────────────────────────────── L-Raise
γ ⟶ γ[θ_n ↦ Unloading(g, ω, ξ)]
```

**L-Raise recovers before it records.** The fiber routes into Unloading carrying the error, the accumulator built up to the failing iteration is applied there, and the fiber arrives at `Inactive(ξ)` **having installed nothing** — differing from an aborting L-Divert only in the outcome carried. "Routing a failure like every other deactivation is what makes **every outcome reachable only through L-Unload**, which is the single fact Theorem 59 turns on." L-Begin has `Inactive(⊥)` as a premise, so **the lifecycle is not re-entered from an error outcome** — this "withholds a fiber whose effect function has shown itself to be unsound in the state it ran against rather than retrying it against an unchanged environment." A failed fiber **obstructs nothing** (Inactive ⇒ no committed view ⇒ cannot make `relied` hold).

**A failure is recorded on the fiber rather than propagated to its parent**, so a component whose transition fails **leaves its siblings running** — "the behavior a plugin host wants."

### 4.4 Metatheory (§4.4)

Ten rules total: O-Insert, O-Retire, O-Remove; L-Begin, L-Iter, L-Finish (activation); L-Divert, L-Raise (early ends); L-Leave, L-Unload (deactivation).

> **Definition 53 (step indexing, state map, edit).** Index steps by t; `γ^t` is the state the first t reach; **(50)** `step^t := r(n)` — the rule r and the name n it applies at. The sequence starts at `γ⁰` with `dom(F⁰) = ∅`, so **every fiber comes into existence by an O-Insert** (orchestrator's or an iteration's, Def 47). Fields carry the index as superscript: `θ^t_n, ω^t_n, σ^t_n, g^t_n, i^t_n`; `F^t`, `σ^t`; predicates `installed^t_n, target^t_n, relied^t_n, quiet^t`.
> An **episode** of n is a maximal interval `[b, u]` of indices throughout which `installed_n` holds. It **opens** at b (`b > 0`, `¬installed^{b−1}_n`) and **closes** at u (`installed^u_n` and not `installed^{u+1}_n`); a final episode need not close.
>
> Every rule concludes in the shape `γ ⟶ δ[⋯]`. The **state map**:
> **(51)** `Ψ^t := pr₁ ∘ i` at L-Iter, L-Finish, and a **landing** L-Divert; `g` at L-Unload; `id_Γ` at every other rule.
> The **edit** `edit^t : Γ → Γ` is the bracket read as a function. Each step factors as
> **(52)** `γ^{t+1} = edit^t(Ψ^t(γ^t))`
>
> Field seam: **tables** `σ_m` (which no edit writes once O-Insert set it empty) vs **control fields** `θ_m, τ_m, π_m, d_m, p_m, e_m` together with `dom(F_γ)` (which no Ψ writes save through Def 47).
> Write **`γ ≈ δ`** when two states **agree on everything but the control fields**.
> And **(53)** `γ ≃ δ := σ_γ ≃ σ_δ ∧ dom(F_γ) = dom(F_δ) ∧ ∀n, c ∈ {θ,τ,π,d,p,e}. c(γ(n)) ≃ c(δ(n))`
> — i.e. §4.4 reads ≃ as Def 33 **conjoined with** agreement on the registry domain and every control field. "≈ and ≃ neither refines the other, because each forgets what the other has to keep."

**Table 1 — the ten rules as writes on the fiber n they act on** (verbatim structure):

| rule | θ^t_n | θ^{t+1}_n | Ψ^t | control fields edited |
|---|---|---|---|---|
| O-Insert | undefined | `Inactive(⊥)` | `id_Γ` | `dom(F_γ)` |
| O-Retire | unconstrained | unchanged | `id_Γ` | `τ_n` |
| O-Remove | `Inactive(−)` | undefined | `id_Γ` | `dom(F_γ)` |
| L-Begin | `Inactive(⊥)` | `Reloading(e_n, id_Γ, ω)` | `id_Γ` | `θ_n` |
| L-Iter | `Reloading(i,g,ω)` | `Reloading(i′, g∘h, ω)` | `pr₁ ∘ i` | `θ_n` |
| L-Finish | `Reloading(i,g,ω)` | `Active(g∘h, ω)` | `pr₁ ∘ i` | `θ_n` |
| L-Divert | `Reloading(i,g,ω)` | `Unloading(g∘h, ω, ⊥)` | `id_Γ` **or** `pr₁ ∘ i` | `θ_n` |
| L-Raise | `Reloading(i,g,ω)` | `Unloading(g, ω, ξ)` | `id_Γ` | `θ_n` |
| L-Leave | `Active(g, ω)` | `Unloading(g, ω, ⊥)` | `id_Γ` | `θ_n` |
| L-Unload | `Unloading(g, ω, ζ)` | `Inactive(ζ)` | `g` | `θ_n` |

(h names the inverse the iteration of the Ψ column yields; `id_Γ` where L-Divert aborts. A Ψ that registers a fiber carries the O-Insert row's writes at the drawn name; an L-Unload whose accumulator retires one carries the O-Retire row's.)

> **Lemma 54 (five lookups).** For every step t and all fibers m, n present at γ^t:
> 1. `σ^{t+1}_m ≠ σ^t_m` only where step t acts on m, the write lying inside Ψ^t;
> 2. `ω_n` comes into existence **only at L-Begin(n)** and ceases **only at L-Unload(n)**, so **ω^t_n is constant for t in an episode of n**;
> 3. `Ψ^t = g^t_n` only where `step^t = L-Unload(n)`, and **no other step applies g_n to the state**;
> 4. `¬installed^t_n ∧ installed^{t+1}_n ⇒ step^t = L-Begin(n)`, and `installed^t_n ∧ ¬installed^{t+1}_n ⇒ step^t = L-Unload(n)`;
> 5. `π_n, d_n, p_n, e_n` come into existence with the entry of n and are **never written again**; `τ_n` is **monotone**, written only at ⊤ and only by an O-Retire.

> **Lemma 55 (≃-invariance).** If `γ ≃ γ′`, a rule applies at γ acting on n iff it applies at γ′ acting on n, and the resulting states are again ≃-related. **⇒ the whole calculus descends to Γ/≃.**

> **Lemma 56 (equivariance).** For a bijection `χ : 𝔑 → 𝔑`, `χ·γ` (registry `F_γ ∘ χ⁻¹`, names in π/ω replaced by images) is a well-formed state, and `step^t = r(n)` carries `γ^t` to `γ^{t+1}` iff `r(χ(n))` carries `χ·γ^t` to `χ·γ^{t+1}`. ⇒ results below are read **up to renaming**.

> **Lemma 57 (vestigial entries).** Call n **vestigial** at γ when `τ_n = ⊤`, `θ_n = Inactive(⊥)`, `σ_n = ∅`, and no m has `π_m = n`; then `γ ≈ γ ∖ n`. (1) A rule applying at γ on `m ≠ n` applies at `γ ∖ n` on m, reaching states differing in the entry at n alone, which stays vestigial; (2) conversely, **unless** it is an O-Insert **drawing the name n or claiming a key of p_n**.

**Subcalculus caveat.** Dropping §4.3.1 is the one simplification that costs results: its guard establishes clauses (3) and (4) of Def 58, and Theorem 63 rests on the interval the guard creates — **those three fail without it.** §4.3.2–4.3.4 can be simplified away without disturbing the results.

#### 4.4.1 Preservation (§4.4.1)

> **Definition 58 (well-formed registry).** For all `m, n ∈ dom(F_γ)` and all `k ∈ K`:
> 1. `π_n ∈ dom(F_γ) ∪ {root}`;
> 2. `m ≠ n ⇒ p_m ∩ p_n = ∅`;
> 3. `installed_n(γ) ⇒ ω_n` is **total on d_n and valued in dom(F_γ)**;
> 4. `installed_n(γ) ∧ k ∈ d_n ∧ ω_n(k) = m ⇒ installed_m(γ)`.
>
> (Acyclicity of the tree needs no clause, since the fiber a pointer names is registered before the fiber naming it.)

> **Theorem 59 (Preservation).** If `F^t` is well formed then so is `F^{t+1}`, whichever rule step t applies. Each clause established at `γ^{t+1}` from all four at `γ^t`.

**"The guard on L-Unload is what carries clauses (3) and (4)."** O-Remove's `∀m. π_m ≠ n` speaks only of *parent pointers*; what keeps a **committed view** from naming a removed fiber is the guard, imposed several steps earlier for a different reason. Two consequences the base calculus lacks: **a name freed by O-Remove may be reissued** (no stale committed view can name it), and **a fiber may be removed as soon as it is Inactive**, without a separate dependency check.

#### 4.4.2 Temporal composability, global form (§4.4.2)

> **Definition 60 (independence for iterators).** For `i ∈ 𝔈^{iter*}_Γ`, `reach(i)` = least set of iterators containing i, closed under continuation:
> **(54)**
> `reach(i) := ⋂ { S | i ∈ S ∧ ∀ i′ ∈ S, γ ∈ Γ, i′(γ) = (−,−,Just(i″)) ⇒ i″ ∈ S }`
> `𝔐(i) := ⟨{pr₁ ∘ i′ | i′ ∈ reach(i)} ∪ {pr₂(i′(γ)) | i′ ∈ reach(i), γ ∈ Γ}⟩`
> `len(i)` = supremum of |C| over chains `C ⊆ reach(i)` ordered by continuation.
> Two iterators i, j are **independent** when
> **(55)**
> `∀ f ∈ 𝔐(i), g ∈ 𝔐(j). f ∘ g ≃ g ∘ f`
> `∀ i′ ∈ reach(i), g ∈ 𝔐(j), γ ∈ Γ. pr_{2,3}(i′(g(γ))) ≃ pr_{2,3}(i′(γ))`
> — i.e. **the yield of an iteration is its inverse *together with its continuation***, and a **registering** iteration is compared by **agreement of the component it names**. A **sequence of steps is pairwise independent** when `(e_n)_{n ∈ N}` is, N being the set of names the sequence ever holds.
>
> "Independence in this sense is what **trace theory** takes as primitive: commuting actions generate an equivalence on sequences under which reordering two adjacent independent actions preserves the endpoint, and **Lemma 71 is that reordering for these rules**."

> **Theorem 61 (Recovery exactness).** Let the sequence be pairwise independent, an episode of n open at b, `u ≥ b` lie in it, and `t₁ < ⋯ < t_l` be the indices in `[b, u)` at which the acting fiber is **not** n. Then
> **(56)** `g^u_n(γ^u) ≈ (Ψ^{t_l} ∘ ⋯ ∘ Ψ^{t₁})(γ^b)`
>
> "Applying n's accumulator at γ^u yields, **up to the control fields**, the state those same steps would have produced from γ^b." Reading the right side as *the state reached had n never begun* additionally assumes no fiber n registers takes a step in `[b, u)`.

> **Corollary 62 (Terminal recovery).** Under the same hypotheses, for an episode of n opening at b and **closing** at u, whatever outcome n arrives at:
> **(57)** `γ^{u+1} ≈ (Ψ^{t_l} ∘ ⋯ ∘ Ψ^{t₁})(γ^b)`
> A fiber removed by O-Remove leaves nothing behind either. **(A failed fiber's contribution to the state is nothing.)**

**Discharging pairwise independence:** §3.3.2 supplies it — where every effect a component performs is an operation of a key and **every key is commutative**, any two effect functions built from those operations are independent (Thm 42). Carrying it from effect functions to **iterators needs nothing new**, a coeffect-mediated effect function already choosing what follows each stage by the outcome. **The coeffect operations of §3.2 need no hypothesis at all**: the maps are composites of `set` and the corresponding restrictions, two such commute whenever they touch disjoint keys, and Def 58(2) makes provisions of distinct fibers disjoint.

#### 4.4.3 Spatial composability, global form (§4.4.3)

Both theorems rest on **the fixity of ω_n over an episode** (Lemma 54(2)).

> **Theorem 63 (Ordering).** A fiber begins a transition only where its dependencies are provided:
> **(58)** `step^t = L-Begin(m) ⇒ γ^t ⊨ d_m`
> Let further `[b,u]` be an episode of m with `ω^{b′}_m(k) = n` for some `m ≠ n`, `k ∈ d_m`; let `[b′,u′]` be the episode of n containing b′; let t range over `[b′, u′]`. Then
> 1. `ω^t_m(k) = n`;
> 2. **`b < b′`, and `u′ < u` if `[b,u]` closes** — i.e. **the provider's episode strictly encloses the consumer's**;
> 3. `k ∈ dom(σ^t_n)` and **`σ^t_n(k) = σ^{b′}_n(k)`** — the binding is present and *unchanged* throughout.

> **Theorem 64 (Resolution coherence).** Let an episode `[b,u]` of n open at b with `ω^b_n = ω`. Then θ_n is `Reloading(−,−,−)` on an initial interval `[b, r]`, and **every iteration of the transition runs against the one resolution ω**:
> **(59)** `∀ t ∈ [b, r]. step^t ∈ {L-Iter(n), L-Finish(n)} ⇒ target^t_n = ω`
> Where the fiber leaves that interval (`r < u`), **exactly one** of:
> 1. `step^r = L-Finish(n)` and `θ^{r+1}_n = Active(−, ω)`;
> 2. `step^r ∈ {L-Divert(n), L-Raise(n)}`, and the episode closes at some `u > r` with `γ^{u+1} ≈ (Ψ^{t_l} ∘ ⋯ ∘ Ψ^{t₁})(γ^b)` as in Cor 62.
>
> "**Inertia is what stops this from being a guarantee about every step.** An iteration already in flight when the target view turns lands regardless, and that landing installs an effect computed against a resolution that no longer holds. **What the rules deliver is therefore a disjunction, and the second branch is what makes the first safe.**"
>
> Also: L-Iter/L-Finish carry `target_n(γ) = ω`; L-Divert carries the negation; **L-Raise is not conditioned on the target view at all** (a raise is something the iteration does). The two directions of change are not distinguished — a dependency **gone** and one **replaced** leave by the same route, both being unequal to ω.

#### 4.4.4 Progress (§4.4.4)

> **Definition 65 (precedence).** **(60)** `n ≺ m := p_n ∩ d_m ≠ ∅` — n *may* provide a key m declares. Reads d and p alone (never written again after entry, Lemma 54(5)).
>
> ≺-acyclicity is an **assumption**, not delivered by the definition (`n ≺ n` holds of a component declaring a key it provides itself). **≺ orders activations, not lifetimes**: `n ≺ m` says n must become Active before m can, whereas "a provider outlives its consumer" is Thm 63(2).

> **Theorem 66 (Progress).** Assume ≺ acyclic, `len(e_n) ≤ K` for every n, and the name set N finite; let every step apply a **lifecycle** rule. With `S(n)` = number of steps acting on n and
> **(61)** `V(n) := |{ t : target^t_n ≠ target^{t+1}_n }|`
> Then:
> 1. **(No deadlock.)** `¬quiet^t` implies some lifecycle rule applies at `γ^t`;
> 2. **(Termination.)** **`S(n) ≤ (K + 4)(V(n) + 1)`**, and both `V(n)` and `Σ_n S(n)` are finite.
> Consequently **every maximal sequence of lifecycle steps ends in a quiescent state.**
>
> *No-deadlock proof shape:* four kinds where a rule directly applies (Inactive(⊥) with target ≠ ⊥ → L-Begin; Reloading with target = ω → L-Iter/L-Finish/L-Raise; Reloading with target ≠ ω → L-Raise or a **landing** L-Divert; Active with target ≠ ω → L-Leave). Otherwise build a chain `m₀, m₁, …` of Unloading fibers with `k_j ∈ d_{m_{j+1}} ∩ dom(σ^t_{m_j}) ⊆ d_{m_{j+1}} ∩ p_{m_j}` so `m_j ≺ m_{j+1}`; ≺-increasing ⇒ distinct by acyclicity ⇒ finite registry ⇒ construction stops at a fiber where L-Unload applies.
> *Termination:* (A) over a maximal interval with constant target, at most `K + 4` steps act on n; (B) each turn of `target_n` either consumes a step of a fiber strictly ≺-below n or is the one turn τ_n affords ⇒ `V(n) ≤ 1 + Σ_{m ≺ n} S(m)` ⇒ well-founded recursion `B(n) := (K+4)(2 + Σ_{m≺n} B(m))` bounds S(n).
>
> **Progress appeals to the aborting alternative of L-Divert nowhere**, so a host bound by inertia (§4.3.3) is covered.

Finiteness of N is assumed; one condition on components delivers it: **if no component can register, however indirectly, a fiber of a component that registers one of its own**, the registrations form a tree of bounded depth (branching bounded by `len(e_n) ≤ K`). What it rules out: **a component that registers instances of itself without bound.**

#### 4.4.5 Confluence (§4.4.5)

**The headline claim:** "whatever sequence of activations and deactivations a running system has been through, **the state it quiesces at is the one the same insertions and retirements would have produced had each component that ends up active been loaded once, in dependency order, and none ever unloaded.** The lifecycle relation is confluent, and the normal form it converges on is the **statically assembled** one." — the analogue, for dynamic composition, of **consistency with from-scratch evaluation** in incremental computation.

The claim is about ⟶ alone (orchestration steps are inputs).

> **Definition 67 (support).** A fiber is **supported** at γ when it is not retired, the fiber registering it is supported, and every key it declares is provided by a supported fiber. Support relation:
> **(62)** `m ⊲ n := m ≺ n ∨ π_n = m`
> **(63)** `n ∈ A := ¬τ_n ∧ (π_n = root ∨ π_n ∈ A) ∧ ∀ k ∈ d_n. ∃ m ∈ A. k ∈ p_m`
> The clauses read **no field but τ, π, d, p**.

> **Lemma 68 (support is well founded).** Let ≺ be acyclic and γ be reached by a sequence of steps. Then ⊲ is well founded and A is the **one** solution of Def 67, a function of τ, π, d, p alone.

> **Definition 69 (total on its provision).** A component `(d,p,e)` is **total on its provision** when an activation of it that finishes has installed **every** key of p, so `dom(σ_n) = p_n` at every Active fiber instantiating it.
> Note: independence already bounds how far this can fail — "were a component to install a key only at context states another component's effects reach, its forward map would not commute with that component's, so **the keys a fiber installs are fixed by its component rather than by the schedule**." Totality adds that the fixed set is **all** of p.

> **Lemma 70 (support at quiescence).** ≺ acyclic, `quiet(γ)`, no fiber failed, every component total on its provision ⇒
> **(64)** `A = { n : θ_n = Active(−,−) }`

> **Lemma 71 (Transposition).** Steps t and t+1 acting on distinct fibers m and n: (1) if both apply an **activation** rule (L-Begin, L-Iter, L-Finish) and t+1 is applicable at γ^t, then t is applicable at the state t+1 produces, and **both orders reach the same γ^{t+2}**; (2) same when t applies an activation rule at m, t+1 an **orchestration** rule at n, and t does not register n.

> **Lemma 72 (Deletion).** Under pairwise independence, totality, a quiescent γ^T with no failed fiber, a **closing** episode `[b,u]` of n, no episode of any m with `n ≺ m` closing, and no fiber n registers during `[b,u]` having an episode (names drawn: R) — **deleting the steps acting on n in `[b,u]` together with every step acting on a name of R leaves a valid step sequence reaching a state ≈-equal to γ^T and ≃-equal outside R.**

> **Theorem 73 (Confluence).** Let a sequence reach a quiescent γ^T with no failed fiber, the steps pairwise independent, every component total on its provision, and A as in Def 67. Then:
> 1. **(Canonical form.)** γ^T is reached, up to the names whose entries the reduction withdraws, from γ⁰ by a sequence that takes the same orchestration steps in their original order — those at orchestrator-inserted fibers preceding every lifecycle step, each of the rest following the step that registered its fiber — and that takes, **for an enumeration `n₁, …, n_k` of A linearizing ⊲, one episode of each `nᵢ` in that order.**
> 2. **(Confluence.)** Any two such sequences from γ⁰ taking the same orchestration steps reach states related, after a renaming (Lemma 56), by **≃ and by ≈**.
> With the termination of Thm 66, **the lifecycle relation has unique normal forms.**

**Failure is deliberately excluded from the statement** — it is "a genuine source of divergence": whether a step raises depends on the state it ran against, so one schedule may fail a fiber where another completes it, and the two quiescent states differ in **that fiber's lifecycle state**. "**They do not differ in anything else, by Corollary 62, which puts a failed fiber's contribution to the state at nothing.**"

The base calculus (§4.2) satisfies the same theorem (drop the guard paragraph of Lemma 72).

**What confluence licenses.** "Reasoning about a Cordis application **as though it were statically assembled**. An orchestrator that adds a component, removes it, replaces a provider, and reverts the replacement is guaranteed to arrive at the state it would have obtained by writing the final composition down at the outset, and a **component author reasoning about which coeffects are in scope may reason about the quiescent state alone.**" **It also delimits the guarantee:** it speaks of the **state**, not of the **emissions** the system produced along the way — the §6.1 distinction between an *acquisition* (tracked inside the boundary) and an *emission* (which crosses it).

---

## 5. Implementation and Case Study (§5)

**Cordis** = a **meta-framework** of spatiotemporal composability: unlike application frameworks targeting a domain (web routing, ORM, UI rendering) it prescribes no scenario; its sole responsibility is to supply **universal dynamic composition semantics**. Three tiers: (1) **core library** (§5.1) implements effect + coeffect systems; (2) **component loader** (§5.2) adds configuration reconciliation + HMR; (3) **application frameworks** such as **Koishi** (§5.3) build domain functionality atop.

### Table 2 — theory-to-implementation correspondence (verbatim)

| Theory (§3, §4) | Implementation |
|---|---|
| `Γ_∞` | `ctx`, the first-class context |
| `γ ∈ Γ` | the context tree together with everything the running system has touched |
| `𝔈_Γ`, `𝔈^iter_Γ` | Effect callback returning / yielding inverses |
| `effect_Γ(e)` | `ctx.effect(callback)` |
| `Σ`, `Σ^iso`, `Σ^inter` | `ctx[@@store]`, `ctx[@@isolate]`, `ctx[@@intercept]` |
| `get(k)`, `set(k,v)` | `ctx.get(key)`, `ctx.set(key, value)` |
| `isolate(k, r)` | `ctx.isolate(key, realm)` |
| `intercept(k, ν)` | `ctx.intercept(key, metadata)` |
| `⟨d,p,e,π,σ,τ,θ⟩` | `fiber`, the instantiation of a component in `ℭ_Γ` |
| `dom(F_γ)` | enumerated through `ctx.registry` |
| `n : 𝔑` | `fiber.uid` |
| `d : 𝔇_Γ` | `fiber.inject` |
| `p : 𝔓_Γ` | the component's `provide` |
| `e : 𝔈*_Γ` | `fiber.apply` |
| `π : 𝔑` | `fiber.parent.fiber.uid` — the fiber owning the context it was instantiated on |
| derived realization (Def 27) | `fiber.ctx`, the child context the fiber runs in |
| `θ` (Def 44) | `fiber.state`; **LOADING = Reloading**, **FAILED = Inactive(ξ)** |
| `recover`, accumulator g | `fiber.dispose` |
| `ω` (Def 44) | **`fiber.committed`**, the committed view |
| `provider_k(γ)` | an `Impl` whose provider fiber is ACTIVE |
| `target(γ, n)` | `fiber.target`, recomputed by `refresh` (Alg 5); ⊥ is INACTIVE |
| `Future`, inertia (§4.3.3) | **`fiber.inertia`**, the handle of the transition in flight |
| O-Insert, O-Retire (Def 47) | `ctx.use` and the inverse of its callback (Alg 4) |
| O-Remove | the fiber dropped from its runtime, with `uid` cleared |
| L-Begin, L-Iter, L-Finish | `execute`'s iteration loop (Alg 1) |
| L-Divert | the guard failing at an iteration boundary (Alg 1), or `reload` chaining into `unload` |
| L-Leave | `refresh` marking the fiber UNLOADING (Alg 5 line 10) |
| L-Unload | `unload` and its inertial chaining (Alg 5) |
| guard on L-Unload | `unload` awaiting the notified dependents (Alg 5 line 25) |
| L-Raise | the error recorded on the fiber, with its target set to ⊥ |

Notation: `@@name` = framework-internal **symbol** key; `ctx[@@store]` is symbol-keyed access to an opaque slot, not string-map indexing.

### 5.1.1 Effect tracking (§5.1.1)

**Every context mutation in Cordis flows through a single primitive, `ctx.effect`** — coeffect provision, component instantiation, and every other context-mutating operation reduces to a `ctx.effect` call, so any operation performed through the context is **automatically tracked and recovered on unload**. `ctx.effect` is the realization of `effect^iter_Γ` (Def 52): takes a callback of type `𝔈^iter_Γ`, lifts it to `𝔈^iter_∂Γ`, yielding a **dispose** closure. Cordis accepts both `𝔈_Γ` and `𝔈^iter_Γ` (ad-hoc polymorphism).

> **What the runtime does NOT check: the witness that `𝔈*_Γ` carries.** "The callback supplies an inverse, and **that the inverse recovers the effect it accompanies is an obligation on the component author rather than a property the runtime verifies.** Theorem 61 is where the calculus appeals to it, and §6.1 is where the obligation is delimited."

```
Algorithm 1  Effect tracking
 1 async function execute(callback, guard)
 2   iter ← callback()
 3   inverse ← id
 4   while guard()
 5     (value, done) ← await iter.next()
 6     if value then inverse ← value ∘ inverse         # prepend ⇒ LIFO
 7     if done then break
 8   return inverse
 9 function effect(ctx, callback)
10   armed ← true
11   task ← execute(callback, () ↦ armed)
12   async function dispose()
13     if not armed then return
14     armed ← false
15     recover ← await task
16     recover()
17   ctx.dispose ← dispose ∘ ctx.dispose
18   return dispose
```
- `execute` drives the callback as an effect iterator and folds each yielded inverse into a composite; before each step it consults a caller-supplied **guard**; once tripped, iteration stops and only inverses accumulated so far remain. **This is the step-boundary interruption of §4.3.2** — `Maybe(𝔈^iter)` realized by the iterator's `done` flag together with `guard`.
- `ctx.effect` adds two things: **self-disposal** (guard reports `armed`; the returned `dispose` flips it false, which simultaneously halts any in-flight iteration and makes recovery fire **at most once** — "firing twice would apply an inverse at a state no application of the effect produced, where nothing holds it to reverting anything"); and **parent composition** (`dispose` prepended to `ctx.dispose`, so a child effect's inverse is itself an effect on the parent — **the recursive structure of ∂²Γ**).
- The component level (§5.1.3) **reuses the same `execute`** with a guard testing the stability of `fiber.target` instead of `armed`.

### 5.1.2 Coeffect operations (§5.1.2)

Three symbol-keyed slots on every context: **`@@store`** (`σ : (r : R) ⇀ 𝒱_r`), **`@@isolate`** (`ρ : Map(K, R)`), **`@@intercept`** (`ι : (k : K) → ℳ_k`). Two-layer resolution `k → ρ(k) → σ(ρ(k))`. `@@intercept` is consulted only when a binding is **accessed** — adjusting *how it is used* rather than *what it resolves to*.

```
Algorithm 2  Coeffect operations
 1 function get(ctx, key)
 2   realm ← ctx[@@isolate][key]                    ▷ ρ(k)
 3   return ctx[@@store][realm]                     ▷ σ(ρ(k))
 4 function set(ctx, key, value)
 5   function callback()
 6     realm ← ctx[@@isolate][key]                  ▷ ρ(k)
 7     ctx[@@store][realm] ← value                  ▷ σ[ρ(k) ↦ v]
 8     notify(ctx, [key])
 9     return function()
10       delete ctx[@@store][realm]                 ▷ σ ∖ ρ(k)
11       notify(ctx, [key])
12   return ctx.effect(callback)
```

```
Algorithm 3  Reactive notification
 1 function notify(ctx, keys)
 2   affected ← ∅
 3   for fiber in all_fibers do
 4     for key in keys do
 5       if key ∈ fiber.inject and fiber.ctx[@@isolate][key] = ctx[@@isolate][key] then
 6         refresh(fiber)
 7         affected ← affected ∪ {fiber}
 8         break
 9   return affected
```
"This is the reactive classification of Def 26: a change that flips satisfaction activates or deactivates the fiber, and **refresh's idempotence renders a neutral change harmless**."

**Availability rule.** "A binding counts as available to a dependent **only while the fiber that installed it is ACTIVE**, so `refresh` resolves each declared key against an **active provider** rather than against the store alone. … **it is what makes a withdrawal visible to dependents one step before it happens**: a provider that has entered UNLOADING has stopped providing, so its dependents recompute an unsatisfied target view and begin their own teardown **while its bindings are all still in place**."

**Isolation/interception**: each derives a child context adjusting one inherited table for `key`, leaving the parent untouched, **so recovery is implicit — discarding the child context suffices, with no explicit inverse to run**. `ctx.isolate(key, realm)` overrides ρ (fresh symbol by default). `ctx.intercept(key, metadata)` merges into ι, new metadata **taking priority**.

### 5.1.3 Component lifecycle (§5.1.3)

Two driving fields: `fiber.parent` (parent context of `fiber.ctx`, forming the component hierarchy — the recursive structure of Γ_∞), and **`fiber.inertia`** (handle to the in-flight async transition, or null if idle).

```
Algorithm 4  Component instantiation
 1 function use(ctx, component, config)
 2   function callback()
 3     refresh(fiber)
 4     return function()
 5       fiber.target ← ⊥
 6       unload(fiber)
 7   fiber ← Fiber(parent: ctx, inject: component.inject)
 8   fiber.ctx ← ctx[fiber ↦ fiber]
 9   fiber.apply ← () ↦ component.apply(fiber.ctx, config)
10   ctx.effect(callback)
11   return fiber
```
"This is the registration primitive of Def 47, with `callback` as its **O-Insert** and the closure `callback` returns as its **O-Retire**: **an instantiation is an ordinary tracked effect of the parent, so unloading a parent cascades to its children.**"

```
Algorithm 5  Component lifecycle
 1 function refresh(fiber)
 2   target ← target(γ, n)
 3   if target = fiber.target then return
 4   fiber.target ← target
 5   if fiber.inertia then return                       # inertia: do not preempt
 6   if target ≠ ⊥ then
 7     fiber.state ← LOADING
 8     fiber.inertia ← create_task(reload(fiber))
 9   else
10     fiber.state ← UNLOADING   ▷ out of service before any inverse is scheduled   [= L-Leave]
11     fiber.inertia ← create_task(unload(fiber))
12 async function reload(fiber)
13   target₀ ← fiber.target
14   fiber.committed ← resolve(fiber.inject)            ▷ commit the view
15   recover ← await execute(fiber.apply, () ↦ fiber.target = target₀)
16   fiber.dispose ← recover ∘ fiber.dispose
17   if fiber.target = target₀ then
18     fiber.state ← ACTIVE
19     notify(fiber.ctx, provided(fiber))
20     fiber.inertia ← null
21   else
22     fiber.state ← UNLOADING
23     fiber.inertia ← create_task(unload(fiber))
24 async function unload(fiber)
25   await all(notify(fiber.ctx, provided(fiber)).map(f ↦ f.await()))   ▷ drain dependents [= guard]
26   await fiber.dispose()
27   fiber.dispose ← id
28   fiber.committed ← ⊥
29   if fiber.target = ⊥ then
30     fiber.state ← INACTIVE
31     fiber.inertia ← null
32   else
33     fiber.state ← LOADING
34     fiber.inertia ← create_task(reload(fiber))
```
Auxiliaries: `resolve(inject)` returns the bindings the declared keys currently resolve to; `provided(fiber)` returns the keys whose binding this fiber installed. Footnote: `create_task` schedules an async function concurrently and returns a handle — written explicitly **for language independence** (eager scheduling e.g. TS promises makes the call implicit; lazy scheduling e.g. Python coroutines, Rust futures requires the host to spawn).

**`fiber.target` is a digest of `target(γ,n)`**: each declared key resolved against the current coeffect store, **tupled with the `uid` of the providing fiber**. "**A uid is drawn fresh and never reused**, so a provider that is replaced cannot be mistaken for the one it replaced, even when the two provide equal values." Since `notify` recomputes the target on every coeffect change, a fiber reloads **precisely when one of its declared keys comes to be provided by a different fiber**. Corollary: **a provider that overwrites its own binding in place is not observed** — "a component that wants its replacement to propagate **withdraws the binding and installs it afresh**."

**Two complementary levels.** *Transition* level: `reload`/`unload` check the target at completion ⇒ inertial chaining across transitions (§4.3.3). *Iteration* level: `execute` (Alg 1) checks the target at each iteration boundary ⇒ **partial rollback within a single transition** (the intra-transition staleness check Thm 64 rests on).

**Three lines carry the coeffect ordering of Thm 63** — "and where each of them sits is what makes the ordering hold": (a) `reload` **commits the resolved view at line 14** and `unload` **discards it only after every inverse has run** (line 28), so a fiber reads the same bindings for as long as it is loaded, **its own teardown included**; (b) `refresh` marks the fiber UNLOADING at **line 10, before the transition task is created** — the L-Leave step: the fiber stops providing and dependents recompute against that **before any of its inverses is scheduled**; (c) `unload` **waits at line 25** for each notified dependent to reach INACTIVE — the guard on L-Unload; `notify` admits a dependent only when its declared key **resolves to the same realm symbol** as the provider's ("the runtime form of the guard's demand that the dependent see the key *from this fiber* rather than merely declare it"). **The wait sits ahead of the whole recovery** rather than inside one of the inverses, "since `fiber.dispose` initiates a fiber's effects concurrently and a wait placed within one of them would leave the rest unordered." Termination follows Thm 66 — **"the provider graph is traversed on demand rather than analyzed in advance."**

### 5.1.4 Context access (§5.1.4)

§5.1.2 gives a **reflective** API (`ctx.set` / `ctx.get`, keyed by name). Cordis layers a **native** way on top: **property access** `ctx[key]`, realized in TypeScript with a **`Proxy`** whose `get` trap mediates every property access.

```
Algorithm 6  Proxy-mediated context access
 1 function resolve(ctx, key)
 2   fiber ← ctx.fiber
 3   repeat
 4     if key ∈ fiber.committed then return fiber.committed[key]
 5     if key ∈ fiber.inject   then throw INACTIVE_ACCESS
 6     if fiber = root         then throw UNDECLARED_ACCESS
 7     fiber ← fiber.parent.fiber
```
Walks the fiber chain **upward**: first fiber whose **committed view** binds key ⇒ authorized, return binding; a fiber declaring key without having committed it ⇒ not loaded ⇒ fail; reaching root without any declaration ⇒ **undeclared access rejected**.

"This is where the proxy differs from bare `ctx.get`: `ctx.get(key)` is a **lookup against the store** that returns the bound value or nothing and never fails, whereas the proxy **resolves against the accessing fiber's own view and enforces the coeffect specification d at the point of use**. **Reading the view rather than the store is also what Theorem 63 rests on**, since it is what keeps a dependency readable to a component whose teardown was triggered by that dependency going away."

The rejection is a **runtime** check; since d is declared statically the same violation is in principle detectable at compile time (§6.4).

### 5.2 Component loader (§5.2)

Core library serves **component developers** (imperative primitives `ctx.effect`, `ctx.use`, `ctx.set`). The loader serves **application orchestrators**: a **declarative configuration layer** — the orchestrator specifies desired composition as a **persistent data structure**, and the loader translates changes into imperative fiber operations.

#### 5.2.1 Declarative configuration (§5.2.1)

> **Definition 74 (entry).** An entry declares a single fiber, recording:
> - **`id`** — stable identifier, used as the **reconciliation key** when its group's child list changes;
> - **`url`** — URL of the component module to instantiate;
> - **`isolate`** — isolation annotation applied to the entry's context;
> - **`intercept`** — interception annotation applied to the entry's context;
> - **`config`** — configuration bound into the component to form its effect function `apply`;
> - **`disabled`** — whether the entry is administratively turned off.
>
> **Why an entry is a faithful specification:** the support set (Def 67) reads **τ, π, d, p and nothing else**, and an entry gives all four — `disabled` gives τ, the entry's parent in the tree gives π, and `url` selects the component which declares d and p. Lemma 70 identifies the support set with the Active fibers of a quiescent state, as far as each component installs every key it declares (Def 69).

Entries form a **configuration tree**. `@cordisjs/group` takes a list of child entries and loads them as a subgroup; `@cordisjs/include` loads an external YAML/JSON configuration file and grafts its entries as a nested subtree. Both are **ordinary components** resting on the registration primitive of Def 47 ⇒ **a nested tree stays within the calculus**.

**Reconciliation is incremental**, and the metatheory supplies the soundness:
- **Thm 73** makes the quiescent state a function of the **final configuration alone** — whatever instantiations/retirements the loader performs, and in whatever order, the system quiesces where a from-scratch load would have left it. (Caveat: only as far as each component installs every key it declares, Def 69.)
- **Thm 66** proves the system **does** quiesce ⇒ a reconciliation is complete once its instantiations/retirements have been issued.
- **Cor 62** puts a departing fiber's contribution to the state at nothing ⇒ rebuilding one entry withdraws what its fiber installed and leaves neighbours as they were.
- **Thm 63** lets entries be instantiated **together, with no load order for the orchestrator to arrange**: a fiber whose keys are not yet provided waits at its L-Begin; one whose provider leaves is deactivated ahead of it. "**A dependency therefore constrains when a fiber activates rather than when its module is fetched and evaluated, so the loader loads modules concurrently**, where bringing up a large configuration spends its time."

**Per-field dispatch (least disruptive operation):**
- `id`, `url` → **rebuild** the entry (identity or component changed);
- `isolate` → **reassign realms** (Alg 7);
- `intercept` → **updated in place** — interception metadata is consulted at read time, needs no reload;
- `config` → **handed to the component**, which decides (typically diff against previous, reload only on material change). An `@cordisjs/group` entry's config **is its list of child entries**, so it applies the update as a **keyed diff over child ids**; updating a surviving child re-enters this same per-field dispatch ⇒ group reconciliation and entry update **recurse together down the tree**;
- `disabled` → unload when set, reload when cleared.

**Managed realms.** `isolate: true` asks for a **local** realm, private to the entry and tagged by its `id`, carried with it wherever it moves; a **string** asks for a **global** realm shared by every entry naming that string (moving such an entry changes which entries it shares a binding with). A realm is discarded once no entry names it. The hard question — whether the entry is itself the provider at a changed key when a realm symbol is shared by several fibers — is answered with **delimiters**: one symbol `δ_k` per key, under which each context stores a tag of its own, **written on a context and inherited by its descendants, drawn afresh at each reassignment**, so
> **(65)** `γ′[δ_k] = d₁ ⟺ γ′ is derived from the entry's context`
Write `own(γ′)` for that condition; `d₂ = d₁` is the instance at the provider.

```
Algorithm 7  Isolation realm reassignment
 1 function patch_isolation(entry, ρ′)
 2   ρ ← entry.ctx[@@isolate]
 3   store ← entry.ctx[@@store]
 4   Δ ← { k | ρ(k) ≠ ρ′(k) }                            ▷ keys whose realm changes
 5   for k in Δ do
 6     entry.ctx[δ_k] ← fresh tag
 7     diff[k] ← (ρ(k), ρ′(k), entry.ctx[δ_k], store[ρ(k)].fiber.ctx[δ_k])
 8   entry.ctx[@@isolate] ← ρ′
 9   reload(entry.fiber)
10   for k in Δ do
11     (s₁, s₂, d₁, d₂) ← diff[k]
12     if d₁ = d₂ and store[s₁] and not store[s₂] then   ▷ the binding is the entry's own
13       store[s₂] ← store[s₁]
14       delete store[s₁]
15   function affected(fiber, k)
16     (s₁, s₂, d₁, d₂) ← diff[k]
17     return fiber.ctx[@@isolate][k] ∈ {s₁, s₂} and (fiber.ctx[δ_k] = d₁) ≠ (d₂ = d₁)
18   notify(entry.ctx, Δ, affected)                      ▷ in place of Alg 3's realm test
```
Reasoning: the reassignment moves contexts satisfying `own` from s₁ to s₂ and leaves others; the loop moves the binding to s₂ exactly when the provider satisfies `own`. Where `own` agrees on dependent and provider, both move or neither ⇒ the dependent sees the binding afterwards exactly when it saw it before. **Where `own` separates them, one side moves and the other stays ⇒ the dependent gains or loses the binding.** The inequality in line 17 is that separation; the membership test drops dependents resolving k in neither realm.

#### 5.2.2 Hot module replacement (§5.2.2)

HMR applies the revertible-effect pattern at **module** level. "Because a fiber already bounds all of its component's effects and coeffects, a module that is itself a component can be replaced through fiber operations alone: **disposing the old fiber recovers everything the component installed, and a new fiber instantiated from the reloaded module reinstalls it. HMR therefore needs no developer-annotated acceptance boundaries**, as opposed to Webpack or Vite HMR." Engine = `@cordisjs/hmr`, three phases.

**Phase 1 — module classification.** Inputs: **stashed** (file URLs whose contents changed since last reload) and **externals** (modules that cannot be hot-replaced ⇒ trigger a full restart).
```
Algorithm 8  Module classification
 1 function classify(stashed, externals)
 2   accepted ← stashed
 3   declined ← externals
 4   pending  ← ∅
 5   for url in stashed do
 6     pending ← pending ∪ (get_imports(url) ∖ (accepted ∪ declined))
 7   repeat
 8     progress ← false
 9     for url in pending do
10       if get_imports(url) ∩ accepted ≠ ∅ then
11         accepted ← accepted ∪ {url};  pending ← pending ∖ {url};  progress ← true
14       else if get_imports(url) ⊆ declined then
15         declined ← declined ∪ {url};  pending ← pending ∖ {url};  progress ← true
18       else
19         pending ← pending ∪ (get_imports(url) ∖ (accepted ∪ declined))
20   until not progress
21   declined ← declined ∪ pending
22   return (accepted, declined)
```
Fixed point: **accept a module once one of its imports is accepted; decline one once all of its imports are declined; anything left undecided (caught in an import cycle) defaults to declined.**

**Phase 2 — stale-entry detection.**
```
Algorithm 9  Stale-entry detection
 1 function get_dependencies(root, declined)
 2   deps ← ∅
 3   function traverse(url)
 4     if url ∈ deps or url ∈ declined then return
 5     deps ← deps ∪ {url}
 6     for child in get_imports(url) do traverse(child)
 7   traverse(root)
 8   return deps
 9 function detect(entries, accepted, declined)
10   stale_entries ← ∅
11   for entry in entries do
12     tree ← get_dependencies(entry.url, declined)
13     if tree ∩ accepted ≠ ∅ then
14       accepted ← accepted ∪ tree
15       stale_entries ← stale_entries ∪ {entry}
16   return stale_entries
```
"An entry is stale exactly when its tree intersects `accepted`; that tree is then folded into `accepted`, so every stale module along it is invalidated in the next phase." `declined` acts as a **traversal boundary**.

**Phase 3 — transactional reload.**
```
Algorithm 10  Transactional module reload
 1 function reload(ctx, accepted, stale_entries)
 2   backup ← invalidate_caches(accepted)
 3   try
 4     for entry in stale_entries do
 5       entry.fiber.dispose()
 6       entry.fiber ← ctx.use(import(entry.url), entry.config)
 7   catch error
 8     restore_caches(backup)
 9     for entry in stale_entries do
10       entry.fiber.dispose()
11       entry.fiber ← ctx.use(backup[entry.url], entry.config)
12     throw error
```
**Transactional guarantee: the system never enters a half-reloaded state** — if any module fails to import (e.g. syntax error), caches are restored and every stale entry is rebuilt from `backup[entry.url]`, undoing the swaps already made. (Footnote: on Node.js this means clearing **both** the ES module and CommonJS caches, since a module imported through the ES loader can appear in both.)

### 5.3 Case study: Koishi (§5.3)

Koishi = open-source **chatbot application framework** built on Cordis. **Over four years of development, 4000+ community-contributed plugins** — IM adapters, database drivers, admin consoles, end-user features. (Footnotes: Koishi currently uses **Cordis v3**; the paper presents **Cordis v4**, which refines effect/coeffect semantics and **redesigns the loader** — "the core compositional model is shared across both versions." Koishi says *plugin* for what the paper calls *component*.)

- **Expressiveness and generality.** Every Koishi feature is a plugin over the §5.1 context primitives; Koishi contributes only chatbot-domain vocabulary. **The same model reappears in a wholly different runtime: Koishi's web console is a second, independent Cordis application** whose plugins compose browser/UI primitives rather than server ones. ⇒ (1) **expressive** — primitives suffice to carry a complete production system; (2) **general** — fixes how effects and coeffects compose while leaving their meaning to each application, presupposing neither a domain nor a runtime.
- **Temporal composability without cognitive overhead.** Orchestrators disable a plugin from the console and its effects are withdrawn in place; during development the HMR engine re-applies edited plugins on save **while preserving cache state and live connections elsewhere**. "Even an inexperienced author obtains ordered cleanup for a plugin's context-mediated effects **without writing an uninstall path**." This achieves the locality of concern §1.2.1 found missing.
- **Spatial composability across an open ecosystem.** Genuine dependency topology: IM adapters provide platform access, database drivers provide persistent storage, functional plugins declare these as coeffects. Reconfiguring a provider at runtime (switching storage backend, reconnecting an adapter) **reactivates only the dependents whose resolved dependency changed**; a plugin whose dependency is unavailable **stays inactive until it appears, without erroring**. "A plugin and its dependencies are typically written by different authors who **coordinate on nothing beyond the coeffect that connects them**."
- **Threats to validity (stated by the authors).** Single ecosystem, single host language ⇒ cannot separate paradigm merits from the TypeScript realization or Koishi's domain; **observational rather than a controlled comparison**. "**An existence-and-adoption result rather than a quantitative one**"; measuring overhead and developer-productivity effect against a baseline remains future work.

---

## 6. Discussion (§6)

### 6.1 System boundary (§6.1) — *the limit of the whole guarantee*
The **system boundary** divides the environment into two parts:
1. A location is **inside** when the system can modify it **exclusively** and **restore the state before that modification** ⇒ an operation on it is tracked in Γ and recoverable.
2. A location is **outside** when either ability fails ⇒ an operation acts as `id_Γ` and is **neither tracked nor recovered**.

**Boundaries from coeffects.** "A coeffect **moves** the boundary by **reifying** an external location: it confines every access to that location to a set of operations it provides, each of which it can supply an inverse for, so operations that acted as `id_Γ` come to be tracked in Γ and recovered." The boundary is drawn **per location, not per medium** — a memory region is inside when only the system writes it, outside when other processes do; a file is inside when only the system can reach it (a scratch file under a private path), outside when other programs read/write the path. Moving the boundary trades off "whether the environment provides revertible semantics for a location" against "what supplying those semantics costs on every access."

**Acquisition vs emission (the two stages of any outward operation).**
1. **Acquisition** — obtains access and installs a record **inside** the boundary: `open` installs a descriptor that `close` removes; `malloc` reserves a block that `free` releases; `fork` starts a child that `kill` terminates. The record is part of the coeffect that reifies the location, and installing it is a **revertible effect**. That record is at the same time the **channel** along which data can leave.
2. **Emission** — pushes data through that channel (bytes a `write` hands to a file, the datagram a `send` puts on the wire). **The push acts as `id_Γ`**, leaving data where other parties may read/write it.
⇒ "The acquisition stays inside the boundary, whereas the emission crosses to the outside."

**Recovering from an emission — two approaches.** (a) **Withhold** the emission until the producing state is certain to persist — the **output commit problem** of rollback-recovery. (b) **Compensation** — an action restoring state up to an **application-supplied equivalence coarser than ≃** (delete a created file, refund a charge). "Such actions compose in the same LIFO order as inverses do, so the composition of §3.1 transfers to them. **The metatheory does not**: the commutation of Def 60 is proved against ≃ and has to be re-established against the coarser one."

### 6.2 Service multiplexing (§6.2)
Cordis coeffects echo OSGi **services**: a service = the interface behind a key; components that `provide` are **providers**, components that `inject` are **consumers**. Two realizations of multiplicity:
1. **Exclusive binding** — several implementations share one interface, at most one bound; switching requires unloading one and loading another, **momentarily perturbing every consumer's dependency**.
2. **Service broker** — a central service acting as the entrypoint for the interface, injected by both backing providers and consumers; **multiple providers coexist and the broker dispatches**. The broker **absorbs the perturbation**: updating a backing provider leaves the broker in place ⇒ **consumers see no change and no reload is triggered.**

Broker underlies three capabilities:
- **Load balancing** — configurable policy (round-robin, least-loaded, latency-weighted) or explicit target; providers are ordinary components, added/removed to scale; **each provider registers with the broker through a revertible effect, so unloading it drops it from the routing set automatically.**
- **Rolling updates** — new provider loaded as an additional fiber, registers with the broker; once ACTIVE, traffic gradually shifted (e.g. selection weights); old providers unloaded once no in-flight requests. "**Turns what is traditionally an infrastructure-level operation (container orchestration, blue-green deployment) into an application-level composition pattern.**"
- **Cross-process invocation** — each process hosts its own Cordis context with local providers; a coordinating component links them, treating each as a remote provider; RPC preserves the interface, making distribution transparent. **Caveat: a cross-process call incurs latency and may fail mid-flight, so an interface intended to cross processes must be designed against an asynchronous contract.**

### 6.3 Access control and sandboxing (§6.3)
- **Capability-based access control.** The dependency-access mechanism (§5.1.4) is already access control over proxy-mediated properties: a component can only access dependencies it declared; undeclared access raises. Structurally similar to **capability-based security** — "the `inject` declaration acts as a **capability request**, and the context proxy acts as a **capability mediator**." Since requests are declared statically, **the complete set of proxy-mediated capabilities a component requires is known before it runs**, letting the orchestrator **review and approve them at load time**.
- **Fine-grained policy through interception.** Access-control metadata carried by contexts or declared by components (Def 30); **the provider consults it when the dependency is invoked** to decide whether a request is permitted (e.g. a filesystem dependency carrying which paths a component may read/write). "Because this interception lives on **the context** rather than in either party's code, an orchestrator can adjust it to constrain any component's access **without modifying the provider**" — e.g. read-only DB access for a community component while a core component retains full access. **Since interception affects only how a dependency is invoked, not whether it is satisfied, it can be installed, reconfigured, or removed at runtime without triggering any reload or perturbing the dependency graph.**
- **Sandboxing untrusted components.** Language-level control is insufficient when code cannot be trusted — a malicious component with host-runtime access can reach underlying objects directly. Requires an execution boundary beyond language means: software fault isolation, a separate language runtime, a sandboxed process, a virtualized container. The untrusted component runs in its **own sandboxed context** and reaches host dependencies through a **bridge**, generalizing cross-process invocation; **on the host side the bridge is an ordinary fiber whose capabilities can be attenuated by the access control above.**

### 6.4 Language independence and selection (§6.4)
The paradigm is language-agnostic. Requirements per dimension:
- **Temporal.** At minimum **closures** — "a revertible effect pairs an action with an inverse, and that inverse must be **captured as a value, along with the state it restores**." Beyond that, a component's code and the side effects of loading it must be **introducible and retractable at runtime**: managed runtimes need a **programmatic module registry** (Node.js exposes one; footnote: CommonJS via `require.cache`, ES modules have no public eviction API though engine-internal interfaces exist). Native code has no module registry ⇒ explicit dynamic linking/unlinking (`dlopen`/`dlclose`, `LoadLibrary`/`FreeLibrary`). WebAssembly goes either way depending on embedder. "Across these mechanisms, the revertible effects model **treats loading as an effect on the context**, with inverses that undo the registration of symbols, types, or handlers the module introduced."
- **Spatial.** Reduces to a **dependency injection** problem manifesting at two levels:
  - *Typing.* The context type must **record each key's coeffect**. Haskell **typeclasses**, Rust **traits** (provider extends the context type from its own module via `instance`/`impl`), TypeScript **module augmentation**.
  - *Runtime mediation.* Access must be dynamically interposed transparently — JavaScript `Proxy`, Python descriptor protocol (`__get__`). Absent such a primitive, **runtime reflection** can mediate, at the cost of type safety and DX.
  - **Metaprogramming supplies both together**: annotations/decorators attach metadata a processor expands into the mediating accessor; compile-time metaprogramming (Rust procedural macros, Scala macros, Zig `comptime`) emits, per dependency, a typed declaration **together with** an accessor — **dispensing with a general-purpose interception primitive**.

### 6.5 Mutual dependencies and component granularity (§6.5)
A dependency cycle "simply leaves the involved components **permanently inactive**" — neither satisfaction predicate can become true. **Unlike deadlock**, this is **predictable from the dependency declarations alone**, so a runtime can report it when components are loaded.

**Decomposition recipe.** Server (network interface) + access controller (authorization) interact bidirectionally. Monolithic ⇒ mutual dependency. Decompose the two logically independent interaction directions into **four** components: `server-core`, `access-control-core`, `request-mediation` (depends on both cores, applies access control to incoming requests), `policy-management` (depends on both cores, exposes policy modification via the server). **Neither core depends on the other; only the integration components depend on both.**

Cost: "in the general case, given n mutually interacting components, the number of integration components can grow **quadratically** with n." Does not affect correctness or runtime performance (components are lightweight), and finer granularity is beneficial (users load only the integration bindings they need). But it affects DX. Mitigations named: **package bundling**, **convention-based wiring**, **scaffold tooling**.

### 6.6 Dependency typing and versioning (§6.6)
In the formal model a dependency link is established **purely by key identity**. `𝒱_k` ensures type-level agreement within a single compilation unit, but this breaks when components are built independently. Two problems:
- **Interface drift** — provider modifies the interface at k between versions while a consumer compiled against an earlier interface still declares k. Satisfied at the coeffect level (`k ∈ dom(σ)`), yet the runtime value no longer conforms ⇒ type errors, method-not-found, or **silent behavioral divergence**.
- **Key collision** — two independently developed providers use the same key name for **entirely unrelated interfaces**; no compatibility check ⇒ "failures unpredictable and difficult to diagnose."

Both point to the same gap: **nominal linking but no versioned or structural linking.** Three approaches, most-coupled to most-agnostic:
1. **Key namespacing** — extend key space `K` to `K × P` where P identifies the interface-defining package. Eliminates collision by construction; most coupled (embeds package namespace into the formal model, depends on an external registry for key identity).
2. **Peer dependencies** — *the approach Cordis currently adopts.* Component dependencies are semantically **peer dependencies**; package managers with peer-dep support (npm) enforce version compatibility at install time. Limits: (a) depends on providers faithfully following semver, **an unenforceable convention**; (b) package managers typically resolve each dependency to a **single version**, preventing multiple versions of the same package in one application.
3. **Structural compatibility** — replace `k ∈ dom(σ)` with a compatibility predicate verifying the provider's interface **structurally subsumes** the consumer's expectation (structural subtyping). Challenge: straightforward for record types (width subtyping), complex for behavioral contracts (pre/postconditions, effect specifications), **undecidable once parametric polymorphism introduces bounded quantification**.

"Designing a unified dependency model that combines these approaches while preserving the dynamic composition guarantees of the coeffect model **remains an open problem**."

### 6.7 Co-design with languages and operating systems (§6.7)
**With languages** — two improvements over a library:
1. *Make the context implicit again while preserving context semantics.* An imperative language already runs every statement against an implicit context, but that single context neither tracks effects nor resolves coeffects. The paradigm distinguishes **multiple** contexts, where an operation either modifies the one it runs against (in-place realization) or **derives another from it** (derived realization) — for which the language must provide a construct. Two benefits: (a) ergonomic — functions no longer need to take the context; (b) **safety** — "a library realization passes a context as an ordinary variable, so **a component may reach another component's context by mistake, through a closure or a global variable. An effect it installs there then leaks out of its own lifecycle, and a coeffect it reads there escapes its dependency specification.** Making the context implicit closes both."
2. *Make effects and coeffects known to the compiler.* (a) For effects: an effect iterator allocates a closure at every step to hold the inverse plus the state it restores; with syntax for performing an effect, a compiler can **emit a single state machine for the whole iteration and hold those inverses in its frame**. (b) For coeffects: admit the coeffect specification into the type system ⇒ **dependency cycles reported at compile time** (§6.5), and **dependencies compared by the structure of their type rather than by key identity alone, as row types do** — type-level support for the structural compatibility of §6.6.

**With operating systems.** An OS co-designed with the paradigm would support fine-grained composition by **making the coeffect specification a component declares the whole of what it can reach**, and by **providing its own resources as coeffects**:
- Supplies the sandbox §6.3 defers to an external mechanism — bounding a component to its declared dependencies, supplying them at load and **leaving nothing else reachable**, "as a WebAssembly module receives its imports from its embedder at instantiation." Can also provide coeffect isolation and interception as **abilities of its own**.
- Provides its own resources as coeffects: "a resource lying outside the boundary is made revertible where the runtime records each acquisition **against the component that made it** (§6.1), and every runtime keeps a record of its own. **An operating system that provides the resource as a coeffect keeps that record once**, since it is the party that hands the resource out and can attribute it to the asking component." Immediate candidates: **memory and file descriptors** (tracking for recovery has been done at the kernel interface — Nooks, shadow drivers). Further: an OS can make **revertible** some operations §6.1 can only withhold or compensate for — transactional persistent-storage writes can be rolled back; copy-on-write / immutable storage reaches an earlier state by moving a pointer.

---

## 7. Related Work (§7) — condensed with the paper's own contrasts

### 7.1 Effect and coeffect systems
- **Monadic effect systems** (ZIO `ZIO[R,E,A]`, Effect-TS `Effect<A,E,R>`, fp-ts Reader transformers). Two differences: (i) tracking is bought with a **monadic embedding** — a program obtains it only by being *written inside the effect type*, whereas **Cordis tracks effects as an overlay over ordinary host code**; (ii) a requirement is discharged by **interpretation** — an installed service supplying operations — and **when that service is withdrawn what its operations performed remains in place**; Cordis pairs each effect with an inverse and **re-resolves requirements as providers come and go**.
- **Algebraic effects as capabilities** (Brachthäuser et al., **Effekt**): effect types as capabilities — what a computation *requires from its context*. Differences: (i) *purpose* — algebraic effects enable **modular interpretation** (one operation, many handler semantics); Cordis enables **tracking and reversion**; (ii) *setting* — Effekt disciplines effects **statically**, capabilities second-class and lexically confined, first-class use recovered through boxing; **Cordis disciplines effects at runtime, aiming at complete resource recovery on component removal.**
- **Reversible effect semantics** (Heunen et al., **dagger arrows / inverse arrows**) — the closest formal account. Differences: Heunen et al. are **denotational/categorical**, reversibility is a **global property guaranteed by construction** (every computation invertible), the inverse **two-sided** and recovered from the categorical structure. **Cordis tracks inverses at runtime and requires less: not that the whole computation be reversible, but that each atomic effect admit a one-sided inverse, supplied by the caller at the point of application rather than derived, from which the inverse of any composite follows by composition.**
- **Graded types unifying effects and coeffects** (Orchard et al., **Granule**; extensions to Java-like languages and call-by-push-value). All operate at the **type level**, over lexically fixed scopes. "Our contribution is **orthogonal**: we lift the same two notions to runtime mechanisms."

### 7.2 Programming paradigms
- **Context-oriented programming (COP)** — layers activated/deactivated at runtime. Resemblance is **nominal**: in COP "context" is the ambient execution situation (location, user, mode) and activation changes **method dispatch** within a dynamically scoped extent; a layer **neither tracks nor reverts** the side effects it induces, and activation is not governed by dependency satisfaction. Trade-off: COP folds activation into the host language's method dispatch (gains dynamically-scoped extents, costs language specificity); **Cordis, as a language-agnostic overlay, resolves activation reactively over a shared context** and can express only COP's global, value-driven fragment.
- **Aspect-oriented programming (AOP)** — pointcut/join-point/advice. **Cordis's analogue of an aspect is a coeffect**: a shared point of mediation many components declare a dependence on. Two axes of difference: (i) **declaration vs obliviousness** — an AOP pointcut is oblivious and quantified; **Cordis confines crosscutting to the coeffects each component declares, so its reach is exactly that declared surface**, yielding determinacy and traceability ("an application orchestrator can inspect and govern what cross-cuts a component **at the configuration layer, without reading or analyzing its source**"); (ii) **lifecycle integration** — a crosscutting change in Cordis is carried by a component's effects, **reverted when the component unloads and propagated reactively to its dependents**; dynamic-AOP can weave/unweave at runtime but as a standalone operation, neither bound to a lifecycle nor triggering re-resolution.

### 7.3 Temporal composability (four families)
1. **Stateful forward migration** — quiescence (Kramer & Magee) relaxed to tranquility (Vandewoude et al.) — the paper's rolling-update pattern enforces it by **draining in-flight requests**. DSU for C (Hicks et al.), type-safe update points via con-freeness (Stoyle et al.), Kitsune (Hayden et al.); event-store schema migration (Overeem et al.); **Erlang/OTP** (`code_change/3`, supervisor restarts rather than effect reversion); JS HMR (webpack, Vite) via `module.hot` / `import.meta.hot`. **Contrast:** these migrate in-memory state more gracefully; **Cordis reverts the old component's tracked effects and reapplies the new component's from a clean slate, so a component's own in-memory state does not survive a reload unless placed in a longer-lived dependency** — and *layering DSU-style forward migration atop revertible effects is future work.* Cordis is more general in two respects: **needs no hand-written migration functions**, and **supports unloading a component entirely and recovering its resources**, not merely updating in place.
2. **Developer-authored recovery** — OSGi / Eclipse extension points / IntelliJ / VSCode unload callbacks; **Command pattern** undo; **saga** compensating actions; algebraic effect handler finalizers; **event sourcing** (retracts by appending compensating events, never executing an inverse). "In all of them the inverse is an **unenforced duty, decoupled from the operation**, so that a forgotten one leaks resources silently." **React's `useEffect` comes closest** to structural pairing (returns a cleanup the runtime invokes before each re-execution and on unmount) — **its shortfall is composability**: a hook may be called only at the top level, never inside a conditional, loop, or nested function; its effect body accepts **neither an async function nor an iterator**. "Effects thus cannot be assembled from other effects or interleaved with control flow, leaving nothing from which a composite inverse could be derived." Cordis effects are ordinary operations that **compose freely and may run asynchronously**, requiring a hand-written inverse **only for each atomic effect** — "assembling existing effects requires writing no inverses at all."
3. **Statically scoped reversal** — STM (read/write log, commit or abort); reversible computing (Landauer, Bennett; Janus); reversible process calculi (**RCCS** carries a memory alongside each process, admitting a step to be taken back when the past it leads to is **causally equivalent**; Phillips & Ulidowski derive reversible operators for CCS/ACP/CSP). "Their **causal-consistency criterion is the concurrent counterpart** of the order Cordis's recovery follows — an accumulator applying a component's own inverses LIFO and the guard of §4.3.1 deferring a provider's withdrawal until its consumers have deactivated (Thm 63)." But their reach is fixed by the semantics. Linear types, RAII, Rust ownership tie release to a lexical region. **Cordis fixes no such scope in advance**, and treats lexical resource management as **complementary** (appropriate for local resources within a single component).
4. **Interposed reclamation** — **Nooks** (wraps every call crossing the kernel/extension boundary; object tracker tells the recovery manager what to release), **shadow drivers** (taps the same calls from the other side), **Akeso** (compiler instrumentation; nestable **recovery domains** logging state changes and cross-thread dependencies, rolling a faulting request back with every dependent domain). "**The closest systems-level precedent for revertible effects.**" Differences: **the platform fixes what can be recorded** (release code per kernel object type, one shadow per driver class, an inverse per instrumented allocator), so a component may hold only resources the platform already knows how to release; **a Cordis component instead introduces effects of its own and supplies an inverse for each atomic one.** Reclamation there is bounded by a request that commits or a restart of the same extension; **Cordis reverts over a component's whole lifetime and propagates removal to its dependents**, which release their own effects in turn.

### 7.4 Spatial composability (three families)
1. **Initialization-time dependency wiring** — DI frameworks (Spring, Guice, Angular, Inversify) and UI framework context (Vue `provide`/`inject`, React Context). Some support dynamic scoping, but **none re-resolves reactively**: when a provider is replaced or removed at runtime, existing dependents are neither deactivated nor re-initialized, and none offers lifecycle management of the kind the component state machine provides.
2. **Availability-reactive component models** — *the closest precedent.* OSGi **Declarative Services** and **iPOJO** let components declare provided/required services with the runtime automatically activating/deactivating as services appear/disappear; iPOJO's **Gravity** project targets autonomous runtime adaptation and its provide/require model **directly prefigures Cordis's `ctx.provide`/`ctx.get` pattern**; **R-OSGi** extends this transparently to distributed settings via RPC, mapping network failures to service-withdrawal events. **Two limits:** (a) the deactivation callback is **hand-written**, so resource safety rests on developer discipline; (b) the callback is **synchronous** — "should teardown require an asynchronous exchange with the departing dependency, the frameworks offer no protocol to await it, forcing a blocking wait against a reference that may already be stale." **Cordis closes both: deactivation reverts the dependents' accumulated effects, and its inertial UNLOADING state runs asynchronous teardown to completion before acting on further change.**
3. **Value-level reactivity** — FRP and signals (SolidJS, Vue reactivity, Angular Signals) propagate change at **value-level** granularity. Cordis's reactive coeffects act at **component-level** granularity, adding **asynchronous lifecycle semantics** that value-level propagation does not model. The granularity difference **runs the other way for consistency**: propagating in a *turn*, in dependency-graph order, lets FRP require **glitch freedom** (no derived computation reads a mixture of updated and stale inputs), whereas **Cordis has no counterpart of a turn** — orchestration actions arrive one at a time — and guarantees only that **no single transition straddles two resolutions of its coeffects (Thm 64)**. The two are **complementary**: a Cordis coeffect can itself carry reactive values, refining component-level reactivity into finer-grained reactive coeffects spanning both levels.

---

## 8. Conclusion (§8) — including the explicit agent-harness call-out

Summary restates: **revertible effects** ⇒ local temporal composability; **reactive coeffects** ⇒ local spatial composability, with **coeffect isolation varying what a declared key resolves to and coeffect interception varying how the binding is used**; unification into a single **context type** where an observational equivalence on coeffects supplies the effects with independence; the **component** calculus whose metatheory carries both from one component to a whole interleaved system; **Cordis** as realization; **Koishi** (4000+ plugins) as validation.

> "Beyond human-curated plugin ecosystems, a compelling direction for future validation is **self-evolving agent harnesses (§1.2.2)**, where an AI agent generates and replaces its own harness components continuously and with little human oversight. Applying Cordis in such a setting would validate the **temporal guarantees of complete recovery under rapid component replacement**, as well as the **spatial guarantees of dependency coordination under frequent topological change**. Such validation would demonstrate the paradigm's applicability as a foundation for **recoverable, coordinated, and continuous self-evolution in agent harnesses and other autonomous systems**."

---

## Appendix A — Master index of the formal apparatus

| # | Name | Statement in one line |
|---|---|---|
| Def 1 | Twisted composition | `(f₁,g₁) ∘ (f₂,g₂) := (f₁∘f₂, g₂∘g₁)`; monoid 𝔗_Γ, unit `(id,id)` |
| Def 2 | Effect context | `∂Γ := Γ × (Γ→Γ)`; pair `(γ, φ)`, φ the accumulator; init `(γ₀, id)` |
| Def 3 | track | `(f,g) ↦ (γ,φ) ↦ (f(γ), φ∘g)` |
| Thm 4 | Projection | `pr₁ ∘ track(f,g) = f ∘ pr₁` |
| Thm 5 | track is a monoid hom | `track((f₁,g₁)∘(f₂,g₂)) = track(f₁,g₁) ∘ track(f₂,g₂)` |
| Def 6 | recover | `(γ,φ) ↦ (φ(γ), id)` |
| Thm 7 | Recovery preserved | `g(f(γ))=γ ⇒ recover(track(f,g)(γ,φ)) = recover(γ,φ)`; soundness invariant `φ(γ)=γ₀` |
| Def 8 | 𝔈_Γ / 𝔈*_Γ | effect function `Γ → Γ×(Γ→Γ)`; witnessed adds per-state `g(δ)=γ` |
| Def 9 | ⋄ | `f⋄g = γ ↦ let (δ,s)=g(γ); (ε,t)=f(δ) in (ε, s∘t)` |
| Thm 10 | Monoid | `(𝔈_Γ, ⋄)` monoid, unit `η_Γ = γ ↦ (γ, id)`; hom from 𝔗_Γ |
| Thm 11 | Witness survives ⋄ | 𝔈*_Γ is a submonoid |
| Def 12 | effect lift | `e ↦ (γ,φ) ↦ ((δ, φ∘g), track(g, pr₁∘e))` |
| Thm 13 | effect preserves ⋄ | `effect(f) ⋄ effect(g) = effect(f⋄g)` |
| Thm 14 | Level projection | `pr₁∘f′ = f∘pr₁`; `pr₁∘g′ = g∘pr₁` |
| Thm 15 | Lifted revert | `g′(Δ) = (γ, φ∘g∘f)`; accumulator restored iff `g∘f=id`; invariant always preserved |
| Thm 16 | LIFO revert | reverse-order reverts recover each application's own state |
| Def 17 | 𝔐(e) | monoid generated by forward map + every yielded inverse |
| Lem 18 | Generators suffice | commutation on generators ⇒ on monoids; `𝔐(e₁⋄e₂) ⊆ ⟨𝔐(e₁)∪𝔐(e₂)⟩` |
| Def 19 | Independence | mutual commutation + neither disturbs the other's yielded inverse |
| Thm 20 | Foreign-state revert | `g_j(δ_u) = δ′_u` — the state as if e_j never ran |
| Cor 21 | Any order | inverses in **any permutation** reach γ₀ |
| Def 22 | Σ | `(k : K) ⇀ 𝒱_k`, finite dependent partial function |
| Def 23 | get/set | `set(k,v) : 𝔈*_Σ` — **coeffect ops are effects** |
| Def 24 | Coeffect | `(𝒱_k, ≃_k, 𝒜_k)`; op type `X_a → 𝒱_k → 𝒱_k × (𝒱_k→𝒱_k) × B_a`; lift `a^Σ` |
| (24) | Satisfaction | `σ ⊨ d := ∀k∈d. k ∈ dom(σ)` |
| Def 25 | Specification | `𝔇_Σ := Set(K)` |
| Def 26 | notify | activating / deactivating / neutral |
| Def 27 | Realizations | in-place (nontrivial inverse) vs derived (identity inverse, discard) |
| Def 28/29 | Σ^iso, isolate | `(ρ, σ)`, `ρ : K ⇀ R`; two-layer resolution |
| Def 30/31 | Σ^inter, intercept | `(ι, σ)`; `get = σ(k)(μ ⊕_k ι(k))`, right-biased merge |
| Def 32 | **Γ_∞** | `μΓ. Γ × (Γ→Γ) × Σ` |
| Def 33 | ≃ | same domain, ≃_k-related values; γ compared by coeffect projection |
| Def 34/Lem 35 | Tests / ≈_𝒜 | indistinguishability = **coarsest** relation the operations respect |
| Def 36/37/Lem 38 | ≃-respect | §3.1 holds verbatim with `=` → `≃` |
| Def 39/Thm 40 | Commutative key | ops at **distinct keys are always independent** |
| Def 41/Thm 42 | Coeffect-mediated | **commutative keys ⇒ independent effect functions** |
| Def 43 | Component | `ℭ_Γ := 𝔇_Γ × 𝔓_Γ × 𝔈*_Γ` = `(d, p, e)` |
| Def 44 | Fiber | `⟨d,p,e,π,σ,τ,θ⟩`; `Θ = Inactive \| Active(g, ω)` |
| Def 45 | Registry / σ_γ | `F_γ : 𝔑 ⇀ 𝔉_Γ`; `σ_γ` = union over **Active** fibers; unique `provider_k` |
| Def 46 | Target view / quiet | `target_n(γ)` = ⊥ or `k ↦ provider_k(γ)` |
| Def 47 | Registration | O-Insert as effect; **inverse is O-Retire** |
| Def 48 | Confinement | bounds writes to `σ_n` (+ registration) and reads to `σ_n`, `σ_m\|_{d_n}`, unnamed ambient |
| Def 49 | 4-state Θ_Γ | `Inactive(ζ) \| Reloading(i,g,ω) \| Active(g,ω) \| Unloading(g,ω,ζ)` |
| Def 50 | relied | some other installed fiber's ω names n |
| Def 51/52 | Effect iterator | `μℐ. Γ → Γ×(Γ→Γ)×Maybe(ℐ)`; lift into `∂Γ → ∂²Γ`; **reified delimited continuation** |
| (49) | Failing iterator | `Either(Ξ, …)`; witness on **Right** only |
| Def 53 | step / Ψ / edit / ≈ | `γ^{t+1} = edit^t(Ψ^t(γ^t))`; ≈ forgets control fields |
| Lem 54–57 | Lookups | writes/ω-fixity/accumulator-uniqueness/episode-boundaries; ≃-invariance; equivariance; vestigial entries |
| Def 58/Thm 59 | Well-formedness / Preservation | tree, disjoint provisions, ω total & installed-valued |
| Def 60 | Iterator independence | 𝔐 over `reach(i)`; yield = inverse **+ continuation**; `len(i)` |
| **Thm 61** | **Recovery exactness** | `g^u_n(γ^u) ≈ (Ψ^{t_l}∘⋯∘Ψ^{t₁})(γ^b)` |
| **Cor 62** | **Terminal recovery** | closing an episode leaves the state as if n never ran |
| **Thm 63** | **Ordering** | activation needs `γ ⊨ d`; provider's episode strictly encloses consumer's; binding constant throughout |
| **Thm 64** | **Resolution coherence** | one resolution per transition; L-Finish **or** (L-Divert/L-Raise + full recovery) |
| Def 65 | Precedence ≺ | `p_n ∩ d_m ≠ ∅`; acyclicity assumed |
| **Thm 66** | **Progress** | no deadlock + `S(n) ≤ (K+4)(V(n)+1)`; every maximal lifecycle sequence quiesces |
| Def 67/Lem 68 | Support A, ⊲ | function of τ, π, d, p alone; well founded |
| Def 69/Lem 70 | Total on provision | at quiescence `A` = the Active fibers |
| Lem 71/72 | Transposition / Deletion | adjacent independent steps commute; closing episodes are deletable |
| **Thm 73** | **Confluence** | canonical form = one episode per supported fiber in ⊲ order; unique normal forms |
| Def 74 | Entry | id, url, isolate, intercept, config, disabled |

## Appendix B — Load-bearing hooks for a QMA-style kernel *(my annotation, not the paper's)*

1. **One mutation primitive.** Everything (coeffect provision, component instantiation, any context mutation) must funnel through a single `ctx.effect`-equivalent, or the tracking guarantee is void (§5.1.1). A Python backend would express `𝔈^iter_Γ` as an (async) generator yielding inverses — the paper explicitly names `yield`/generators as the natural encoding (§4.3.2) and calls out lazy scheduling (Python coroutines) needing explicit `create_task` (§5.1.3 fn. 2).
2. **The witness is unchecked.** The runtime does **not** verify `g(δ) ≃ γ`; it is an authorial obligation (§5.1.1). A kernel wanting stronger assurance must add its own verification layer — the paper offers none.
3. **Commutative keys are the whole independence discipline.** Registry/table-shaped services (tool registries, event listeners, route tables) are commutative; **ordered chains (middleware stacks) are not** (§3.3.2). Anything order-sensitive must be pushed into a declared coeffect, not into raw effects.
4. **Provider identity, not value, drives reload.** `fiber.target` tuples the provider's fresh-never-reused `uid`; **in-place overwrite of a binding is invisible** — replacement must be withdraw-then-install (§5.1.3).
5. **Three lines carry the ordering guarantee** (§5.1.3): commit the view at reload start; mark UNLOADING *before* scheduling any inverse; await notified dependents *ahead of* the whole recovery, not inside an individual inverse.
6. **Proxy-mediated access enforces the specification at the point of use** and is the mechanism §6.3 turns into capability-based access control + interception-based policy — the paper's own answer to permissioning an agent harness.
7. **The boundary (§6.1) is where the guarantee stops.** LLM calls, tool emissions to the outside world, network sends are **emissions** — `id_Γ`, unrecoverable. Only the **acquisition** (handle/registration) is revertible. A QMA kernel must decide, per resource, whether to reify it as a coeffect (moving it inside), withhold (output-commit), or compensate.
8. **Confluence licenses static reasoning** about a dynamically reconfigured harness (§4.4.5), but **only** under: ≺ acyclic, pairwise independence, totality on provisions, and **no failed fiber**. Failure is explicitly a divergence source — though a failed fiber contributes nothing to state (Cor 62).
9. **Self-registration must be bounded** — the finiteness assumption behind Progress rules out a component that registers instances of itself without bound (§4.4.4). Directly relevant to a self-evolving harness.
10. **HMR needs no acceptance boundaries** because the fiber already bounds the component's effects (§5.2.2) — and the reload is transactional with cache backup/restore.
