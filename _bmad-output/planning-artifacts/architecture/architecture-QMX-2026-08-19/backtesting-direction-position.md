# Backtesting Direction — Position Paper (v2, post-challenge)

status: challenged and revised — pending operator ratification
date: 2026-08-20
inputs: operator dictation 2026-08-20 (memlog 118); eight grounding dossiers + three adversarial challenge reports in `research-backtesting/`
v1 → v2: three adversarial lenses (mechanics, economics, override-steelman) produced 3 broken + 12 wounded findings; all folded in below. v1's AD-42..45 are demoted to direction candidates; v1's "stateless AND live" claim, "mechanically drift-free doors" claim, "the Jesse lesson" MCP attribution, and unqualified "Jupyter anywhere" are all retracted.

---

## 1. The verdict, reframed

**This is a new organizing architecture at the interface layer, assembled from mostly-ratified parts. The override is real where you felt it — how agents and you touch the system — and contained where it matters: not one invariant of AD-1..41 needs to change.** The parts-tally (most dictation lines map to standing law) cannot refute the gestalt: no prior ruling covers a state-synced agent interface, and that is the load-bearing centre of what you dictated.

**Cost honesty (challenge finding):** "already ratified" means ratified *contracts*, not built software — every mapped row is 0% built. The expensive, risky, reference-less core is the **retail-forex fill engine** (variable spread by hour/event, weekend gaps, swap, partial-lot rounding). No reference implementation exists anywhere — Jesse has *no slippage model at all* and a flat fee; the old QMX fill simulator died unbuilt. That build cost sits entirely ahead, inside the deferred GAP-0048, whatever we decide about interfaces today.

Line-by-line mapping (unchanged from v1, abbreviated): own-Lean-CLI-shaped = ratified (D1, DEC-0085/0086 dead); backtest-against-Book/BMS = ratified (Simulator shape, "Book sets the bar", AD-32); CLI-in-sandbox = ratified (DEC-0084 dead, decentralized); QML revival = planned (GAP-0047); prop-firm room = socketed (DEC-0082). Genuinely new: the state-synced interface (§3), portability requirement (§5), and the feature commitments (§4).

## 2. Lean vs Jesse — the choice dissolves (survived challenge intact)

Neither is adoptable as code, on engineering grounds independent of D1 — and the fork was costed this time (challenge-economics §1):

- **Fork-and-gut Jesse fails the surgery.** Floats are the substrate (Candle FloatFields, float metrics, float fees, and the hot path is a pinned external Rust binary *whose source is not in the repo*); the singletons ARE the engine (removing store/router/config means rewriting backtest_mode 1523 lines + Strategy 1874 lines + every service); the data layer is Postgres/Redis + bespoke crypto REST drivers. The surgery deletes the load-bearing ~90% and keeps the ~5–10% (textbook MC/bootstrap algorithms, declaration schemas) that must be re-expressed on QMF types anyway — while leaving dead float/singleton/crypto idioms in the tree for factory agents to re-copy. **And the one thing QMX most needs — the forex fill model — is the one thing Jesse doesn't have.**
- **Lean CLI wholesale buys an empty shell** — a logic-free Python orchestrator whose every compute command runs a C# engine in Docker that we will never run.

**Donor table, narrowed (challenge-economics §2 applied):**

| Donor | What actually transfers |
|---|---|
| **Lean CLI** (Apache-2.0, 1.0.228) | Proof that a zero-domain-logic CLI works; the **resolved run-config written out as an inspectable artifact** (feeds AD-10/12 fingerprints — the single best Lean idea); command shapes: `init` workspace, `report` over a results file, `data download`/`data generate`; their `:latest` image default is the **determinism trap we fix** by stamping versions into the result label. |
| **LEAN engine** | **Confirmation, not donation.** Its config-composed handler skeleton validates QMX's own prior art (contract-hub, AD-8 injected clock, AD-12 worlds, verdict-doc "one kernel three wirings"). Its *mechanism* — reflection over class names — is banned (AD-2: explicit registration, never ambient scanning). Nothing to copy; one thing to avoid. |
| **Jesse** (MIT, 3.0.7) | Declaration schemas: `hyperparameters()` (name/type/min/max/default/step) and routes (exchange, symbol, timeframe, strategy) for multi-TF/multi-symbol permutations; the *existence* of MC (trade-shuffle + candle pipelines), bootstrap rule-significance, and an MCP surface as product decisions. **Explicitly rejected:** its optimize sampler (home-grown np.random; Optuna used only as a ledger — if we optimize, we use real Optuna samplers), its "pure-function" API (a facade over global-singleton reset; only the bare signature ports), its MCP architecture (see §3), its fill model (absent), floats, singletons, Postgres/Redis, crypto drivers, paid closed-source live plugin. |

## 3. The interface architecture — owned as ours, with the contradictions ruled

v1 claimed "three logic-free doors; nothing can drift, mechanically" and cited Jesse. **Both claims were broken.** Jesse is the *counter-example*: it has three heterogeneous stacks (web controllers over singletons, research functions over process-reset, MCP wrapped over the HTTP API) that can and do drift. And "mechanically" would demand an unbudgeted codegen subsystem. The honest design, presented as QMX's own:

- **One library** (application-side, built on QMF contracts — never a QMF roster package; DEC-0022/L21). All compute, all policy (seal checks, world rules, refusals) lives here.
- **Thin hand-written wrappers as doors**: Python API (in-process), CLI (one-shot process — the natural agent tool in factory sandboxes), MCP (long-running server). Doors carry **no domain logic** but necessarily carry *adaptation* logic: parsing, transport, refusal rendering per door (raise / exit code / error object), and registry enumeration for the autocomplete you asked for. Door parity is enforced the boring way: an AD-4 **tier-2 contract test** asserting every door exposes the same functions with the same semantics — not codegen.
- **UI backend**: a consumer of the Python API in-process — not a fourth door, and MCP is a sibling door, never stacked over an HTTP layer (rejecting Jesse's topology explicitly).
- **MCP security**: localhost-bound by default (Jesse binds 0.0.0.0:9002 — rejected); exposure beyond localhost is a node/ops decision.

**The state-sync mechanism — the either/or v1 illegally straddled (both mechanics and steelman lenses broke this):** a fingerprinted snapshot cannot be "live", and re-resolving against a live central registry would re-enter the always-on dependency DEC-0084 killed. The fork you must rule (§8 Q2):

- **(a) Snapshot + sync hub (recommended).** The registry stays JSONL-append, no server (AD-16). Sandboxes and laptops carry an **immutable, fingerprinted registry snapshot**; a dumb file-sync hub (your own "middle sync server / Dropbox-like" idea from the data sitting, filed at memlog 55) re-syncs at session start and on demand when reachable. "The CLI updates automatically" becomes: *auto-resync when the hub is reachable; honest staleness when not.* Every result label carries the snapshot fingerprint AND a `registry_as_of` instant; running against a ref that a fresher snapshot shows superseded raises an AD-11 **stale-evidence** refusal (severity configurable). Works offline; DEC-0084 stays dead (the hub stores files, it computes nothing).
- **(b) Live central registry read-service.** True liveness, but amends DEC-0084's scope, dies offline, and adds an always-on dependency to every sandbox.

**Write-back (v1 said nothing; mechanics lens broke it):** N parallel sandboxes minting campaign/occurrence records is the dictated workflow. Under (a): each sandbox writes to its **own WriterId-scoped append stream** (AD-15 one-writer preserved); the hub import is the single merge point; identical-fingerprint arrivals are idempotent accepts; **label-identified float-differing artifacts are R-7 lineage siblings, never AD-10 collisions**; true collisions (same identity, different content, same environment claim) refuse + alarm as ratified.

**Per-door staleness:** the MCP server is the door that holds state longest and serves the agents ticket 008 names as the executors — so MCP re-resolves the snapshot **per call** (or stamps `registry_as_of` in every tool result so an agent can detect staleness). The CLI is naturally fresh per invocation; the Python API documents snapshot lifetime as caller-owned.

**Result label completeness (mechanics wound):** the label is AD-12's mandated label, never a shorter restatement — producer contract version, **CLI version AND QMF roster version** (two separate ladders), snapshot fingerprint + as-of, input/split fingerprints, world, occurrence id, plus **R-8 seed/generator/reduction-order** on every stochastic door (optimize, MC, bootstrap), plus fidelity/fill identity once GAP-0048 mints it.

## 4. What ships when — replay mechanism ≠ backtests (mechanics wound applied)

- **Ships under standing law:** the replay *mechanism* (injected data-driven clock, data cursor, split-governed reads under AD-21), data download, report rendering over CT-32 containers, research/analysis functions, the doors themselves.
- **Does NOT ship yet:** verdict-bearing **backtests**. A clocked replay becomes a backtest only through a fill model and fidelity taxonomy — that is GAP-0048, deferred, and fidelity + result-key tuple are flagged **irreversible** (map.md locks list). Any interim fill run carries a `fidelity=optimistic` taint: it cannot spend split budget and cannot claim edge.
- **Synthetic data (broken in v1, fixed):** `data generate` may ship as **infrastructure-stress tooling only**. **World is derived from input provenance, never caller-declared**: synthetic-origin data is tainted at the store level (per-world rooms, AD-19, mirroring AD-7's money-path taint); any run consuming it is forced to world=simulated → policy rejection for governed evidence in V1 (L20: synthetic never validates edge). Without this taint, `data generate` is an edge-validation backdoor — an agent could generate favourable candles and book a world=replay Sharpe. Your "synthetic sorts our data problem" hope conflicts with L20 if the problem was edge-evidence scarcity — that is ruling ask Q3, not something I'll paper over.
- **The data-licensing hole (steelman find):** the only recovered tick corpus **failed the licensing gate**. Replay-first needs a canonically-licensed historical corpus (Dukascopy terms) as a named dependency of the backtesting sitting — currently unresolved.

## 5. Portability, honestly scoped (steelman wound applied)

"Jupyter anywhere" = the **tooling** runs anywhere (pip/uv-installable pure library, no server, no workstation coupling). It does **not** mean governed data goes anywhere: on an uncontrolled laptop, pandas reads sealed Parquet without asking AD-21's permission — enforcement is honor-system off-sandbox, exactly five-hats R-4's finding. So: **sealed and governed evidence never leaves controlled rooms; external/portable contexts receive only unsealed, split-governed exports** (purge/embargo per R-5). The seal's one final look stays a write-gated registered occurrence (R-4), which lives with the hub/controlled side.

## 6. Experimentation freedom vs pre-registration (steelman wound → surfaced as a ruling)

v1 quietly landed optimization on "campaign budgets minted before the run" while claiming GAP-0017 stays deferred — pre-deciding the exact friction your "for any X strategy, Y optimizations at time t" wants removed. Retracted. The live choice (§8 Q4), with the five-hats X-1 asymmetry as the likely synthesis: **experimentation free** (registration permissive — run whatever, whenever; occurrences log as raw material), **promotion strict** (evidence offered toward a Book seat / live money must belong to a pre-registered campaign with charter + split + budget). The full ruling belongs to GAP-0017 at the sitting; today you only pick the direction.

## 7. QML — answered, plus ordering (your mid-session lead, memlog 122)

Old QML = the "QML Shared Contract Library" (Bot = Archetype + Features + Filters + Risk + Execution + ExitLogic); revival planned as GAP-0047 — the QMF-era update you described (things removed, superseded by AD-29..41) is exactly that sitting's job. **New find:** the corpus held a second QML-named artifact the dig missed — the **`.qml` bot-source file format** (Monaco-edited, codegen-produced, one per variant). Recorded as mandatory GAP-0047 input; plain-Python-vs-`.qml`-DSL authoring gets ruled there. **Ordering:** sitting order and build order are separable; QML needs only admission-bar *interfaces* (thresholds may stay "not yet ruled" — blocks live money only), so the QML sitting may run before the backtesting sitting, and QML-first *build* is natural (the experimentation library wants a uniform bot to exercise; plain-Python bots bridge meanwhile).

## 8. Direction candidates + ruling asks

**Procedural fix (economics + steelman, both flagged):** v1 proposed minting AD-42..45 onto the QMF spine. Wrong twice — the library is application-side (L21 puts it outside the spine's scope), and the doors' surface is coupled to irreversible deferred cargo (fidelity, result-key tuple, GAP-0048/0049) while ticket 008's required input (your GPT brainstorm markdown) is still missing. So: **the spine stays AD-1..41.** What you ratify today are binding **direction candidates**, recorded in the memlog, minted as ADs at the backtesting sitting:

- **DC-1 — One library, thin doors.** One application-side experimentation library on QMF contracts; Python API / CLI / MCP as thin no-domain-logic wrappers; door parity by tier-2 contract test; UI backend consumes the Python API; MCP sibling not stacked, localhost-default.
- **DC-2 — Snapshot + hub state model.** Immutable fingerprinted registry snapshots, dumb sync hub, `registry_as_of` + snapshot fingerprint in every label, stale-evidence refusal on superseded refs, WriterId-scoped write-back streams merged at the hub, R-7 sibling semantics.
- **DC-3 — Donors as narrowed in §2.** Shape-only, code ban reaffirmed; LEAN skeleton = confirmation; Jesse sampler and MCP topology explicitly rejected.
- **DC-4 — Provenance-derived world.** World comes from input provenance via store-level taint; synthetic = infra-stress only until GAP-0048; interim fills carry fidelity=optimistic taint.
- **DC-5 — Names.** CLI command `qmx`; the library named under your vocabulary: **experimentation** the umbrella, **backtesting** the verification stage (it is a *library*, never a framework or engine — QMF stays the only framework).

**Asks:** Q1 adopt DC-1..5 as binding direction (spine untouched)? Q2 state model (a) snapshot+hub vs (b) live registry? Q3 synthetic data: confirm L20 or override it? Q4 experimentation friction: X-1 asymmetry vs strict-everywhere vs defer untouched?
