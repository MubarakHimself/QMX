# C1 — Harness Core

**Cluster:** architectural decision frameworks for the harness/kernel layer; evidence about what a harness core should and should not own.
**Read for:** QMA (Quantum Mind Agents) — Python backend, kernel + plugin architecture, scoped constants, provider-unbiased sandbox/computer abstractions. Deployable semi-profile = a **mind**.
**Stance:** every paper judged on its own merits. The AlphaXiv chat that pointed at these papers is casual context, not authority. Findings that contradict a Cordis-style plugin-kernel direction are surfaced first, not smoothed over.

## Coverage ledger

| Paper | Status | Source used |
|---|---|---|
| 2606.24937 — The Hitchhiker's Guide to Agentic AI (v2, 27 Jul 2026) | READ (targeted: Ch. 15 stack overview, Ch. 18 Harness, Ch. 19 Loop Engineering, Ch. 20.4 pattern selection) | `pdfs.assets.alphaxiv.org/2606.24937v1.pdf` — 1.57M chars, ~700pp textbook; full linear read not warranted, sections selected by index + full-text grep on "harness", "loop", "simplest" |
| 2606.20683 — From QA to Task Completion (v1, 14 Jun 2026) | READ (full structure; §5 anatomy, §6 task→config, §7 empirical, §8 outlook read in full) | same host |
| 2604.18071 — Architectural Design Decisions in AI Agent Harnesses (v1, 20 Apr 2026) | READ IN FULL (incl. appendices A–C) | same host |
| 2605.18747 — Code as Agent Harness (v1, 18 May 2026) | READ (full structure; §3.3–3.5, §4.3–4.4, §5.2 read in full) | same host |
| 2605.26112 — From Model Scaling to System Scaling (v1, 25 May 2026) | READ IN FULL | same host |
| *(optional)* HarnessX: A Composable, Adaptive, and Evolvable Agent Harness Foundry | LOCATED + READ (arXiv 2606.14249v1, 12 Jun 2026) | found by title search; same host |

No paper in this cluster was unreachable. No silent caps.

---

## 1. 2604.18071 — Architectural Design Decisions in AI Agent Harnesses

*Hu Wei (single author, 1990huwei@sina.com). Cross-sectional study of 70 public agent-system projects, corpus frozen 23 Mar 2026.*

### Core mechanism (faithful)

Not a system — a **design-space study**. Protocol-guided, source-grounded coding of 70 projects across a fixed 14-module inspection SOP (overview, architecture, runtime loop, orchestration, tool system, sandbox execution, workspace filesystem, memory system, subagent relations, model abstraction, observability/debug, safety governance, technical environment). Five focal dimensions retained: **subagent architecture, context management, tool systems, safety mechanisms, orchestration**. The author is explicit that "Agent harness" is used "only as a loose working label… not intended as a strict definition."

Marginal distributions (N=70):

- **Subagent:** None 30.0% · Tool-based delegation 17.1% · Orchestrator-worker 18.6% · Multi-level recursive 12.9% · Event-driven 7.1% · Basic spawn 7.1% · Swarm 5.7% · Pipeline 1.4%
- **Context:** Hybrid 27.1% · File persistence 22.9% · Hierarchical 17.1% · Enterprise 12.9% · Vector/RAG 10.0% · LLM summarization 5.7% · Context window only 4.3%
- **Tool system:** **Registry 34.3%** · MCP-first 14.3% · Minimalist 11.4% · **Plugin ecosystem 10.0%** · Decorator 10.0% · Declarative/DSL 8.6% · Enterprise 8.6% · Delegation/proxy 2.9%
- **Isolation:** Process separation 45% · Container 31% · **No isolation 17%** · WASM 7%
- **Audit:** **No audit 40%** · Basic logging 35% · Structured 20% · Tamper-evident 5%
- **Orchestration:** Imperative 45% / Declarative 25% / Event-driven 30%; ReAct 50% / Plan-and-execute 35% / Hierarchical 15%

Co-occurrences (descriptive, support/lift):
- Subagent complexity → context sophistication (0.73 / 1.8). File persistence in 85% of orchestrator-worker vs **20%** of single-agent projects.
- Container isolation → policy-structured security (0.89 / **3.4**); **100%** of container-isolated projects implement policy engines vs 23% without.
- MCP-first tooling → stronger tool discovery (0.62 / 2.8), and formalized registration correlates with **platform/ecosystem positioning**.

Non-co-occurrences (the analytically load-bearing part):
1. **Programming language does not determine architecture.** Advanced subagent patterns: Rust 57%, Go 43%, **Python 42%**, TypeScript 40%.
2. **Use case does not fix design complexity.** "General purpose" spans minimalist to enterprise; "coding assistant" spans lightweight local tool to governed platform.
3. **Capability growth does not produce safety maturity.** Uneven landscape, not a maturity ladder.

Five patterns: Multi-Agent Orchestrator 31.4% · Balanced CLI Framework 25.7% · Lightweight Tool 21.4% · Scenario-Verticalized/Research 11.4% · **Enterprise Full-Featured 10.0%** (the only bundle that lists "plugin architecture with versioning and dependency management").

### Evidence quality — moderate, with real weaknesses

Strong: transparent SOP, published corpus (Appendix A lists all 70), operational codebook (Appendix B), screening protocol (Appendix C), explicit non-PRISMA disclosure, 21% human audit sample with 94% initial field-level agreement, confidence notes on ambiguous coding.

Weak, and it matters:
- **Single author**, non-institutional email, no co-rater beyond an unspecified "research team"; no chance-corrected agreement (κ) for the full matrix — the author says so.
- The quantitative co-occurrence claims lean on **undefined composite scores**: "memory score 4.1 vs 2.8", "discovery 4.62 vs 3.86", "security-score gradient 4.5/3.2/2.1". No rubric for these scores is published anywhere in the paper or appendices. Treat the *rank orderings* as informative and the *numbers* as unverifiable.
- Support/lift are drawn from "internal cross-project summaries" whose raw matrix is not released.
- Corpus provenance is uneven: `claude-code-src` is coded from a **"source-visible leaked snapshot."** That is a provenance and ethics problem for anyone citing the claude-code rows; the corpus also skews heavily to small community "…claw" forks, which inflates the tail of lightweight patterns.
- Cross-sectional snapshot; the author explicitly disclaims causal direction.

Net: **the best empirical base-rate data in this cluster**, but use the distributions and the non-co-occurrences, not the composite scores.

### QMA should borrow

- **The five-dimension decision frame verbatim** as the QMA kernel spec's table of contents: subagent architecture / context management / tool system / safety mechanisms / orchestration. It is the only frame in this cluster derived bottom-up from implementations rather than top-down from a definition.
- **Separating "subagent architecture" from "orchestration."** The paper's justification is sound: a project can have sophisticated orchestration with no subagents, or subagents with no formalized workflow. QMA should not fuse "mind spawns mind" with "control-flow style" into one kernel concern.
- **Bundle coherence over feature maximization.** "Choose coherent bundles rather than isolated features"; "architectural coherence matters more than maximizing the number of advanced features."
- **The isolation/audit taxonomies as scoped-constant enums**: isolation ∈ {none, process, container, wasm}; audit ∈ {none, basic, structured, tamper-evident}; approval ∈ {absent, confirmation, policy-structured}. These are observed, not invented, and give QMA a defensible default ladder.
- **Design the complexity envelope up front.** "Architectural complexity is usually easier to manage when it is chosen as part of an overall operating model rather than accumulated opportunistically feature by feature."

### QMA should reject

- **The implicit "capability ⇒ governance" story.** The paper's own non-co-occurrence 3 kills it. QMA cannot assume a maturing kernel will grow safety; safety has to be a designed dimension from day one or it will not appear.
- Any use of the composite scores (4.62, 4.1, 2.1, …) as evidence for a QMA decision.
- The corpus's implicit normative pull toward the Enterprise Full-Featured pattern. It is 10% of projects and the paper explicitly says patterns "are not maturity levels or quality tiers."

### Kernel implications — **contradicts a Cordis-leaning plugin kernel**

Three findings cut directly against a plugin kernel as the default:

1. **Plugin ecosystem is a 10% minority pattern.** The modal tool system is an **explicit registry (34.3%)** — tools added via explicit API calls, dynamic management, no versioning/dependency/dynamic-loading machinery. Registry + MCP-first + decorator = 58.6%. The paper reads this as projects "first formalize tools internally before committing to broader interoperability or ecosystem-facing extension boundaries."
2. **Formalized extension boundaries track *ecosystem ambition*, not agent quality.** Co-occurrence 3 (support 0.62, lift 2.8): MCP/plugin registration is "rarely adopted in isolation. They usually appear in projects that present themselves as reusable platforms, developer-facing CLIs, or broader orchestration substrates." The honest reading: **a plugin kernel is a bet on third-party contribution, not a performance decision.** If QMA does not intend a third-party mind/plugin marketplace, the plugin kernel is unpaid complexity. If it does, the plugin kernel is justified — but for market reasons, and it comes bundled with the governance cost of the Enterprise pattern.
3. **"Python backend" constrains nothing.** Non-co-occurrence 1 removes any language-derived argument for or against a kernel shape.

Simpler alternative this paper puts on the table: **typed registry + explicit process/container isolation + structured audit**, with the plugin loader deferred until QMA actually has an external contributor. That configuration is the empirical center of gravity and sits in the "Balanced CLI Framework" bundle (25.7%).

---

## 2. 2606.20683 — From Question Answering to Task Completion: A Survey on Agent System and Harness Design

*Guo, Hao, Wang, … Xu, Wang (CityU HK / Univ. Sydney / PKU / TokenRhythm), 14 Jun 2026. IEEE-style survey with an original empirical section.*

### Core mechanism (faithful)

Model–harness lens. An LLM agent is `A_LLM = ⟨M, H⟩` where the harness decomposes into **six coupled runtime responsibilities**:

`H = ⟨I_obs, C, L, I_act, S, V⟩` — observation interface, context manager, control loop, action interface, state & artifact store, verification & governance.

The authors are careful: "The decomposition is not intended as a software package diagram. Rather, it identifies the runtime *responsibilities*." §5.7 argues the six are **not independently optimizable** — "improving one layer can shift risk elsewhere: stronger compression can reduce cost while weakening downstream verification; richer actions can improve task coverage while increasing governance pressure; more persistent state can improve continuity while also introducing stale or conflicting evidence."

Four-paradigm evolution: prompt engineering → workflows/context engineering → **harness engineering** → agent-native training & co-evolution. Notably, context engineering is characterized as "fundamentally feedforward: it optimizes the input to each reasoning step but provides no structural mechanism to detect drift, verify intermediate outcomes, or recover from errors." Harness engineering is what closes the loop.

Task-pressure taxonomy (horizon × environment × autonomy) mapping tasks to which component becomes the bottleneck:

| Level | Description | Bottleneck |
|---|---|---|
| L1 single-step | search, translate, calculate | Context Mgr; Verif & Gov |
| L2 multi-step | form filling, code generation | Action Interface; State Store; Verif & Gov |
| L3 long-horizon | repo-scale coding, research | Context Mgr; State Store; Control Loop |
| L4 open-ended | monitoring, auto exploration | Verif & Gov; Control Loop |

The most consequential transition is L2→L3.

### Evidence quality — the strongest in this cluster

This is the only paper here with a real quantitative harness-effect analysis, and it is careful about its own limits.

- **Terminal-Bench 2.0**: sourced from the official leaderboard plus the HuggingFace public-submission repo. 75 submissions with metadata/logs covering **32,604 trial records**; **48 strictly matched** to visible leaderboard entries; coverage stated field-by-field (reward 97.2%, agent-runtime 98.1%, full-runtime 100%, token fields 45.0%, dollar cost **15.2%**) — and monetary cost is therefore explicitly *excluded* from cross-harness claims. Official submissions use `-k 5` with fixed environments and no timeout/CPU/memory overrides. This is unusually disciplined evidence hygiene.
- **Headline result:** among the 20 models with ≥3 observed harness results, the **median within-model range is 13.6%**, and **14 of 20 models vary by ≥10% across harnesses**. Named spreads: GPT-5.3-Codex 64.7% (Terminus 2) → 78.4% (SageAgent); Claude Opus 4.6 58.0% (Claude Code) → 76.4% (Meta-Harness), an 18.4pt spread; Gemini 3.1 Pro 59.4% (Gemini CLI) → 80.2% (TongAgents), 20.8pt. "These gaps are substantially larger than the standard errors reported for most relevant leaderboard entries."
- **WebArena**: model-only vs harnessed spans — GPT-4o 13.1% → 54.6% (WebOperator), a 41.5pt span; Llama-3.1-8B 5.6% → 48.5% (AgentSymbiotic). Same-harness slice (BrowserGym) shows model capability also matters monotonically within Qwen3.5 27B→9B→4B→2B.
- **SWE-bench Verified** table is honestly labelled "a compact synthesis of public evidence rather than a fully controlled factorial experiment," with per-row reasoning-setting caveats spelled out (e.g. Opus 4.5 mini-SWE-agent 76.8% is extended-thinking; the same source reports 74.4% at medium reasoning).

Weaknesses: observational, not randomized; leaderboard entries differ in prompts, budgets, versions; WebArena rows are sparse and mix complete systems with baselines. The authors say all of this.

### QMA should borrow

- **`H = ⟨I_obs, C, L, I_act, S, V⟩` as the kernel's responsibility contract** — six named seams the kernel must own or explicitly delegate. This is a better kernel spine than an ad-hoc module list because each element is defined by *what fails if it is missing*.
- **Task-pressure profiling as the configuration mechanism.** Rather than one global kernel config, QMA should derive a mind's harness configuration from its (horizon, environment, autonomy) profile. §6.3's domain-independent rules are directly implementable as scoped-constant policies: long horizon ⇒ externalized state; partial observability ⇒ structured observation; strong oracle ⇒ verifier loops; weak/delayed oracle ⇒ provenance + intermediate review + conservative stopping; irreversible actions ⇒ governance; high autonomy ⇒ logging + budgets + recovery.
- **The layered design recommendation in §8.3 — this is the single most directly applicable sentence in the cluster:**
  > "A general substrate plus domain-specific adapters. The substrate provides logging, isolation, permission control, persistence, cost accounting, standardized tool access, and auditability. Adapters define observations, actions, verifiers, memory policies, and retry, rollback, stopping, or escalation rules."

  That is a precise kernel/plugin boundary, and it is *not* the boundary most plugin kernels draw. Under it, the QMA kernel owns **seven** things (log, isolate, permission, persist, cost-account, tool access, audit) and **nothing else**. Orchestration topology, memory policy, verifier choice, and stopping rules live in adapters.
- **Reporting contract.** "A benchmark score is interpretable only together with the runtime configuration that produced it. Reports should include at least model version, harness identity, tool privileges, retry and timeout policy, execution environment, token or API usage when available, and trace or verifier metadata." QMA should make this the mandatory shape of any mind's run record.
- **Value-density objective** as the shape of QMA's optimization target: success jointly with normalized cost, latency, risk, and process quality — not success alone.

### QMA should reject

- The formalism `PH = Φ(...)`-style equations as anything but bookkeeping. The authors' `VD_{α,β,γ}` is "a family of deployment-specific utilities rather than a fixed metric." Do not hard-code weights.
- **"Protocol standardization is not the same as harness generalization."** Explicit warning against treating MCP/A2A adoption as harness maturity. QMA must not let "we speak MCP" substitute for deciding what to expose, what to allow, how to verify, how to recover.
- Reading the vendor-scaffold rows as evidence that closed scaffolds are architecturally superior — the margin is only **2–4%** across same-generation Claude and Gemini models, attributed to "prompt design, candidate selection, and compute scaling."

### Kernel implications — **partly supports, sharply bounds**

Supports a kernel: harness choice moves a *fixed* model by a median 13.6pt on Terminal-Bench and up to 41.5pt on WebArena. The kernel layer is where a large fraction of realizable capability lives. That justifies investing in it at all.

But it contradicts a *heavy* kernel, with a section heading stated flatly:

> **"Scaffold complexity does not predict effectiveness."**

Evidence inside the paper: on Claude Opus 4/4.5, **mini-SWE-agent — a ~100-line scaffold that "leaves most orchestration to the model" — scores 76.8%, beating SWE-agent+tools at 73.2%**, and trails the full OpenHands+CodeAct 2.1 runtime by only 0.8pt (77.6%). Agentless, a fixed non-agentic localize→repair→validate pipeline, beat interactive SWE-agent on GPT-4o (38.8% vs 23.2%) and on Claude 3.5 Sonnet was within 3pt of the best. And: "a lightweight scaffold can be effective when it matches the model's preferred interaction pattern and the benchmark's feedback structure… compatibility [is] an empirical property of the model–harness pair rather than an implementation detail."

The Terminal-Bench resource table adds a cost dimension a kernel design must respect: Meta-Harness on Opus 4.6 buys 76.4% with a **755.0K** median input context per trial; Terminus 2 gets 62.9% on **79.4K**. Nearly 10× the context for 13.5pt. A kernel that assembles maximal context is not free.

**Simpler approach this paper suggests:** a thin substrate (the seven listed services) + swappable adapters, with the *plugin surface deliberately narrow* and the orchestration left to the model unless a measured pressure profile demands otherwise.

---

## 3. 2605.18747 — Code as Agent Harness

*Ning, Tieu, Fu, Wei, Li, Bei, … Zhang, Tong, He (UIUC / Meta / Stanford), 18 May 2026. ~66pp survey with an original position section.*

### Core mechanism (faithful)

Thesis: **code is the right medium between model and environment** because it is simultaneously *executable* (outputs become operations with formally verifiable outcomes), *inspectable* (intermediate computation exposed as structured traces the harness can read, store, act on), and *stateful* (the evolving program persists task progress across steps).

Important scope boundary the paper draws itself: "We use *code* broadly, but not metaphorically… raw perception, physical state, human intent, and model-internal latent reasoning are not themselves code." Code does not replace perception or embodiment; it makes selected aspects of them executable/inspectable/stateful.

Three-element distinction that matters for QMA vocabulary:
- **model-internal capabilities** (reasoning, planning, simulation, evaluation)
- **system-provided harness infrastructure** (predefined tools, APIs, sandboxes, memory, validators, permission boundaries, telemetry, workflows) — "the main focus of harness engineering"
- **agent-initiated code artifacts** (regression tests, temporary tools, DSL programs, executable workflows, reusable skills, intermediate program states) — the underexplored category

Layers: harness interface (code for reasoning / acting / environment modeling) → harness mechanisms (planning, memory, tool use, control, optimization) → scaling the harness (multi-agent over shared code).

**Plan–Execute–Verify (PEV)** as the unifying control frame: the harness "acts as a *cybernetic governor*", observing the environment through **deterministic sensors** (linters, parsers, compilers, type checkers, unit/integration tests, static analyzers, fuzzers, runtime monitors, CI) rather than forwarding error strings to the model. It then decides: continue, revise, request more context, route to another module, **reduce permissions**, or escalate. Explicit rule: "Termination should likewise be governed by verification rather than by model confidence."

Three-tier permission model (§3.4.3): **read-only** (browsing, retrieval, static inspection, log analysis) / **sandbox-edit** (local patching, test execution, temporary dependency install inside an isolated workspace) / **full-access** (network, credentials, deployment, package publishing, destructive fs ops, git history mutation) — with mandatory HITL gates on the last tier.

Execution substrates read as **three functional clusters**, not one catalog: coding sandboxes (filesystems, git, shells, package managers, code-exec backends); computer-use substrates (browser, desktop, LSP, IDE state); durable runtimes (microVM/WASM isolation, snapshots, warm pools, resumable sessions, always-on operating contexts).

**Agentic Harness Engineering (§3.5):** deep telemetry → Evolution Agent (observe → diagnose → propose → evaluate → promote) → **governed harness mutation**. Explicit: "AHE should not be confused with unconstrained self-modification… the Evolution Agent is itself subject to the PEV loop."

### Evidence quality — survey-grade, with one strong original analysis

Large author list from strong institutions; ~480 references; companion GitHub list. Most of the paper is synthesis, so its claims inherit the evidence quality of the works cited — no new experiments.

The exception is **§4.3–4.4**, an original comparative analysis of multi-agent code systems by shared-state representation and convergence criterion. That section produces the most useful non-obvious findings in the cluster, and it names systems and mechanisms concretely enough to check (L2MAC's persistent file store D with a Control Unit; SyncMind's formal ground-truth state S_k vs agent belief B_k; AutoSafeCoder's security convergence; MAGE's clock-edge waveform checkpoints; QualityFlow's 75–84% first-call early exit).

Caveats: taxonomy-driven, so category boundaries are the authors'; "the majority of the literature resides in the implicit/file-only category" is a distributional claim without a published count; the code-centric thesis is a position, and the paper argues for it rather than testing it against non-code harnesses.

### QMA should borrow

- **PEV as the kernel's control contract**, with the cybernetic-governor framing: the kernel's job is to *regulate state transitions*, not to think. Deterministic sensors first; model critique interprets sensor output rather than replacing it.
- **The three-tier permission model as QMA's scoped-constant backbone**, plus the crucial refinement from §5.2.5: "permissions should depend not only on tool identity, but also on **arguments, environment state, data sensitivity, and expected side effects**. The same command may be safe in a disposable sandbox but unsafe in a production repository." That means QMA's permission constants must be scoped over *(tool, args, environment, data class)*, not just tool name — which is exactly the "scoped constants" idea, validated.
- **The three-cluster sandbox decomposition** as the shape of QMA's provider-unbiased computer abstraction: coding sandbox / computer-use substrate / durable runtime. These have genuinely different interfaces and should be three abstractions, not one leaky `Sandbox`.
- **Evidence bundles.** "Every accepted action carry an evidence bundle containing the checks run, the assumptions preserved, the untested regions, and the remaining risks." And: "Each artifact should declare what it verifies, what it cannot verify, and what confidence it provides." A verifier that does not declare its own scope is a liability.
- **Change contracts for any kernel/config mutation:** "which component is modified, which failure mode it targets, what improvement it predicts, which invariants it must preserve, which evaluation can falsify it, and how it can be rolled back."
- **Transactional shared state** (§5.2.4): "each action should declare its read set, write set, assumptions, version dependencies, verifier obligations, and conflict policy." If minds ever share workspace, this is the contract.
- **Human-in-the-loop as durable harness state**, not a prompt interruption: "Each approval, rejection, policy exception, or reviewer correction should update the harness's permission rules, escalation policy, verification criteria, and future memory retrieval."
- The tool-mechanism checklist from §3.3: "typed tool schemas, permission-aware invocation, sandboxed execution, lifecycle hooks, result sanitization, context compaction, state offloading, and reproducible traces."

### QMA should reject

- The **code-maximalism** reading. The paper itself warns: "a harness can become overconfident precisely because it has executable feedback: the agent sees a green test, but the green test is not the full specification." Oracle adequacy is the bottleneck, not oracle presence.
- Reflexive sandboxing of everything. §4.4 reports a genuinely awkward finding: Self-Collaboration and QualityFlow show **LLM-simulated execution achieving 98%+ precision and recall in predicting actual outcomes without running code**. The paper's own conclusion: "a mature harness would integrate both: using linguistic reasoning as the fast path and delegating to execution as the verification oracle only for the failure modes that require it" (runtime crashes, resource exhaustion, boundary conditions, performance regressions). Sandbox-by-default is a cost QMA should pay selectively.
- Test-gated convergence on self-generated tests. FlowGen "can converge on code that passes its own biased tests but fails on external evaluation."
- Implicit convergence (fixed round counts) — the paper calls it "the most prevalent convergence pattern in the literature and… the most significant gap in the field."

### Kernel implications — **contradicts a Cordis-leaning plugin kernel, from an unexpected direction**

Four findings in §4.4 form the sharpest architectural argument against orchestration-heavy kernels anywhere in this cluster:

1. **"Topology complexity inversely correlates with harness-state formality."** L2MAC, which has "the clearest formal harness substrate (a persistent file store with explicit context scheduling), uses a simple sequential chain with sophisticated state management. By contrast, implicit-state systems like EvoMAC and SEW develop elaborate adaptive topologies (dynamic DAGs, workflow mutation, agent pool scaling)… **topology complexity is partially a symptom**: when the substrate is formally represented and queryable, agents can coordinate through simple, transparent protocols."

2. **"Context management is the tax of implicit shared state."** L2MAC's Control Unit, MetaGPT's publish-subscribe pool, SoA's agent-pool scaling, Cogito's three-tier memory — "all responses to the same underlying problem: how to give agents a coherent view of a code harness that is too large to fit in any one context window. A mature harness substrate could unify these disparate solutions by providing a principled, queryable representation of task state."

3. **"The reliance on implicit state representations is the technical root of system brittleness rather than a scalability convenience."**

4. **Implicit convergence is "a direct consequence of the lack of formal shared substrates."**

**Read against a Cordis-style plugin kernel:** if QMA's kernel investment goes into plugin composition, hook ordering, and orchestration topology, this paper says that is *the symptom, not the cure*. The high-leverage kernel investment is a **formal, queryable, versioned state substrate** — read/write sets, belief-vs-ground-truth divergence, assumptions, provenance. Get that right and the orchestration can stay a simple loop. Get it wrong and no amount of plugin machinery will compensate; the system will grow elaborate topologies as scar tissue.

**Simpler approach it suggests:** kernel = state substrate + PEV governor + permission tiers + deterministic-sensor registry. Orchestration topology is *not* a kernel concern and probably not even a plugin concern until measured need.

---

## 4. 2605.26112 — From Model Scaling to System Scaling: Scaling the Harness in Agentic AI

*Shangding Gu (UC Berkeley), 25 May 2026. Position paper, single author, self-described "under active development."*

### Core mechanism (faithful)

Six-component conceptual decomposition: `P_H = Φ(R, M, C, S, O, G)` — reasoning substrate, memory store, context constructor, skill-routing layer (tools + subagents), orchestration loop, verification & governance. Model scaling improves R; system scaling improves M, C, S, O, G.

Factorizations: `M = (precision, durability, retrievability, verifiability)`; `C = (relevance, compactness, traceability, refresh policy)`; and for S: (specificity, selectivity, composability, verifiability).

Three bottlenecks, each stated as a named threat + a named system move:

| Component | Threat | System move |
|---|---|---|
| Context governance | **"exposure without access"** — model sees more tokens, attends to the wrong ones | context as the output of a *selection policy*, not a fixed buffer; persistent priors + just-in-time refresh |
| Memory trust | **"stale-but-confident"** | trust as a **runtime decision, not a property of the stored item**; staleness penalty against time-of-last-verification; retrieved content treated as *hypothesis until re-checked* |
| Skill routing | **"confident-but-unchecked"** | adaptive routing + explicit post-condition checks; routing as a learned policy, analogous to OS scheduling |

Prompt / skill / memory as three *temporal* layers: prompt = local ("what to do now"), skill = task-level ("how to do this class of things"), memory = longitudinal ("what should survive over time").

Safe-evolution standard as four questions: **What persists? What updates? What is measured? What is auditable?**

### Evidence quality — weakest in the cluster. Position paper, no original experiments.

Stated plainly by the author: "Equation 1 is a conceptual organization rather than a quantitative model: Φ has no closed form, the factors are not strictly orthogonal, and we do not claim they jointly determine P_H as a measurable equation."

- **No experiments of its own.** Every number is borrowed: Anthropic's 90.2% multi-agent result, the 80%/95% variance decomposition, SWE-agent's ACI gains, τ-bench pass^k collapse, lost-in-the-middle.
- The comparison table (Claude Code v2.1.88 / OpenClaw v2026.4.6 / CheetahClaws v3.05.79) is explicitly **"illustrative… The point is not to rank systems."** CheetahClaws is the author's own release and is **not evaluated** anywhere in the paper.
- Single author, preprint, "under active development," soliciting comments.
- Several cited works are the author's own (privacy/long-context, uncertainty, AgenticPay, agent-scaling-via-diversity, memory safety risks) — the framing is somewhat self-referential.

Treat this as **useful vocabulary with essentially zero independent evidentiary weight**. Its factual claims about harness effects are all better sourced in 2606.20683.

### QMA should borrow

- **"Trust is a runtime decision, not a property of the stored item."** This is the paper's one genuinely sharp idea and it is directly implementable: QMA memory entries carry per-entry confidence + time-of-last-verification as **first-class fields**, and retrieval ranking applies a staleness penalty and a confidence-gated risk term. Retrieved content is a hypothesis until re-checked against the live environment.
- **The hybrid pattern**: persistent distilled priors *plus* just-in-time environment access. "Durable memory without periodic verification accumulates undetected drift; environment-only search without distilled priors discards every prior verification."
- **The symmetry insight**: stale-but-confident (memory) and confident-but-unchecked (skills) are the same failure — "both let the agent act on a claim whose truth condition was never re-established." One kernel mechanism (re-establish truth conditions at use time) covers both.
- **The four safe-evolution questions** as the required header of any QMA self-modification design: what persists / what updates / what is measured / what is auditable. And: "Memory, skills, preferences, and guardrails should be distinguished rather than merged into one undifferentiated state, so that updates to one component do not silently rewrite another." That is a real constraint on how a "mind" is serialized.
- **Process metrics alongside outcome metrics**: trajectory quality, memory hygiene, context efficiency, communication fidelity, verification cost, safe evolution.

### QMA should reject

- `P_H = Φ(R,M,C,S,O,G)` as anything more than a naming scheme. Six-tuples are cheap: this cluster contains **four incompatible ones** (Gu's RMCSOG; Guo et al.'s I_obs/C/L/I_act/S/V; Hu Wei's five dimensions; HarnessX's nine). Their non-convergence is itself the finding — do not adopt any as canonical.
- Any implied endorsement of CheetahClaws as a reference design. It is unevaluated.
- The "skill routing as OS scheduling" analogy as a design instruction. It is a metaphor with no mechanism behind it in this paper.

### Kernel implications — **weakly supports modularity, on governance grounds only**

The paper's Objection-2 rebuttal is its strongest argument for a kernel and it is worth quoting because it is the correct reason to be modular:

> "Deployed agents still require modular boundaries. They operate over private files, credentials, tools, repositories, browsers, and external services. In these settings, auditability, permission control, rollback, and provenance are not optional. **Modularity is therefore not only an engineering convenience; it is a requirement for safe and governable deployment**, and an end-to-end policy still has to act through the same permission, verification, and audit surfaces we describe."

That justifies a kernel that owns **permission, verification, audit, provenance, rollback**. It does *not* justify a kernel that owns orchestration, and it says nothing about plugins. The paper offers **no evidence** that a plugin architecture beats a registry.

Note also the Objection-1 rebuttal, which QMA should hold: stronger models reduce the frequency of system failures but "does not remove the need for explicit mechanisms that govern what information is exposed, which actions are authorized, and how failures are traced." The governance surfaces are the durable part of the kernel; the cleverness is the perishable part.

---

## 5. 2606.24937 — The Hitchhiker's Guide to Agentic AI: From Foundations to Systems

*Haggai Roitman, v2 27 Jul 2026. Single-author textbook, ~700pp, 27 chapters, LLM internals through agentic UI.*

### Core mechanism (faithful)

Ch. 18 defines the agent harness as "the runtime infrastructure that wraps an LLM to transform it from a stateless text-completion engine into a stateful, goal-directed agent," enforcing a **separation of concerns**:

- **Reasoning** — delegated entirely to the LLM; *"the harness does not second-guess model outputs"*
- **Execution** — harness dispatches tool calls, manages I/O, enforces sandboxing
- **Memory** — short-term (context window), working (scratchpad), long-term (vector store / DB)
- **Communication** — message routing between agents, users, external services
- **Observability** — instrument every step for logging, tracing, debugging

OS analogy, stated as the design rationale: "Just as an OS abstracts hardware from applications, the harness abstracts infrastructure from the model."

**Context budget as an explicit constraint** (Eq. 18.1): `C ≥ S(system) + M(memory/RAG) + T(tool defs) + H(history) + R(reserved output)`, with a fixed-allocation default of α≈0.10 / β≈0.20 / γ≈0.10 / δ≈0.50 / ε≈0.10. Named hazard: **the Silent Truncation Trap** — "Many LLM APIs silently truncate input that exceeds the context limit, dropping tokens from the *middle* or *beginning*… all without any error signal. Always count tokens *before* sending."

Compression: summarization of old turns; selective retention scored by `sim(e(m_i), e(q)) + λ·recency(i)`; importance-weighted truncation framed as 0/1 knapsack, solved greedily on `w_i/|m_i|`. Recursive Language Models as the escape hatch from "everything must fit in one window" — Zhang et al. report a recursive GPT-5-mini *outperforming* non-recursive GPT-5 on hard long-context benchmarks, cheaper per query.

Ch. 19 **Loop Engineering** reframes the agent loop as inference-time RL with **frozen policy weights**: "'Learning' happens purely through state accumulation." Five primitives: **Automations** (episode initiation), **Worktrees** (isolation / independent rollout workers), **Skills** (persistent conditioning), **Connectors** (action space, typically MCP), **Sub-agents** (maker–checker separation / actor–critic). Plus **external state**, which is non-negotiable: "A loop without external state is a loop with amnesia… The state mechanism need not be complex — a markdown file committed to git after each iteration is often sufficient — but it must exist."

Loop guards: max-iteration hard cap; action deduplication by `hash(tool, args)` within sliding window W; progress detection. Escalation predicate: `escalate ⟺ p_success < τ_conf ∨ action ∈ A_irreversible ∨ cost > B_auto`.

### Evidence quality — pedagogical, not empirical. Use it as a design catalogue.

- **Single author, self-published book on arXiv**, no peer review, no experiments. Numbers cited (recursive RLM results, context-rot) come from third parties.
- Framework comparison (Table 18.1) is High/Medium/Low qualitative judgment with no methodology.
- Breadth is enormous (tokenization → Flash Attention 4 → MCP → agentic UI), which necessarily means depth is uneven; the harness chapter is competent practitioner synthesis, not research.
- Its value is **completeness of the design surface and named anti-patterns**, both of which are genuinely useful for a spec.

### QMA should borrow

- **The five-way separation of concerns as the kernel's contract**, especially the first clause: *the kernel does not second-guess model outputs*. That single rule prevents a large class of kernel bloat.
- **The context budget equation as literal scoped constants.** `C ≥ S + M + T + H + R` with per-mind α/β/γ/δ/ε shares is exactly the kind of thing QMA's scoped-constants system should carry, and the defaults (0.10 / 0.20 / 0.10 / 0.50 / 0.10) are a defensible starting point.
- **Pre-flight token counting as a kernel invariant.** The Silent Truncation Trap is a real failure mode with no error signal; the kernel is the only layer that can prevent it.
- **Loop guards as kernel-owned constants**: max_steps (e.g. 50), action-hash dedup with window W, progress-stall detection, and the three-clause escalation predicate. These are cheap, universal, and belong in the core.
- **Maker–checker separation as a structural rule**: "A model grading its own output is analogous to a student marking their own exam — the incentives are misaligned." A verification sub-agent, potentially a different model or higher reasoning effort.
- **External state is mandatory, complexity is optional.** Three functions: progress tracking, failure memory ("preventing the loop from oscillating between identical dead ends"), handoff context/audit trail.
- **Context degradation countermeasures**: aggressive compaction every k steps, external scratchpad read on demand, **sub-agent isolation returning only conclusions not full reasoning traces**, sliding window over history.
- **Named anti-patterns for QMA's own docs**: *Loopmaxxing* ("without a gradient signal pointing toward improvement, iteration alone is not optimization"), *Comprehension debt* ("when a loop modifies code faster than the engineering team can review it"), *Reward hacking* (test deletion, metric gaming, specification narrowing, output masking).

### QMA should reject

- Table 18.1's framework rankings as decision input — no methodology.
- The "harness as OS" analogy taken literally. It is a good teaching device and a bad architecture brief: an OS owns scheduling and resource arbitration, which is precisely the region this cluster's evidence says to keep thin.
- Treating the book as a primary source for any empirical claim.

### Kernel implications — **supports a thin kernel, explicitly warns against layering**

The book's own decision rules cut against a heavy kernel:

- **§20.4 Pattern Selection Guide:** "start from the top (simplest) and move down only when the simpler pattern demonstrably fails… Patterns are composable… **The art is knowing when to stop adding layers.**" Complexity ladder: prompt chaining / routing / parallelization (Low) → orchestrator-workers / evaluator-optimizer / ReAct (Medium) → planning agent / reflection / multi-agent (High).
- **§19.11 When Not to Use Loops** + **The Simplicity Principle:** "start with the simplest approach that works, and add loop complexity only when you have evidence that iteration materially improves outcomes. A prompt chain that solves the problem is always preferable to a loop that might."
- **§18.9 build-vs-buy:** build custom "when the framework's abstractions leak in ways that cause bugs, you need fine-grained control over context management, or you are building a product where the agent harness is a core differentiator." Note the inverse reading for QMA: a plugin kernel *is* a framework, and QMA would be imposing on itself exactly the leaky-abstraction risk this section warns third parties about.

The **cheapest high-value kernel** implied by this book is small: context budgeting + pre-flight token counting + loop guards + external state file + escalation predicate + observability. Every one of those is a few hundred lines and none requires a plugin system.

---

## 6. 2606.14249 — HarnessX: A Composable, Adaptive, and Evolvable Agent Harness Foundry *(optional, located by title)*

*"Darwin Agent Team", 12 Jun 2026. The most directly relevant paper in the cluster to a Cordis-style plugin kernel — it essentially builds one.*

### Core mechanism (faithful)

`H = (M, C)` — model configuration and harness configuration, **disjoint concerns**. M records *which* model serves which role (main, judge, evaluator) plus fallback policy; C records *how* the agent behaves independently of model identity. Combined via `agent = model_config.agentic(harness_config)`. "An agent in HarnessX is a processor pipeline bound to a model, both independently substitutable."

`C = (P, S)`:
- **P: Hook → List[Processor]** — hook-indexed processor lists over **eight lifecycle hooks** with declared permitted modifications:

| Hook | Event | Permitted modifications |
|---|---|---|
| task_start | TaskStartEvent | system prompt |
| step_start | StepStartEvent | structural history edits |
| before_model | BeforeModelEvent | last user content; one user-message append |
| after_model | ModelResponseEvent | response content, tool calls |
| before_tool | ToolCallEvent | tool input, approval flag |
| after_tool | ToolResultEvent | tool result |
| step_end | StepEndEvent | read-only |
| task_end | TaskEndEvent | read-only |

- **S** — a fixed set of orthogonal **slot resources**: tool registry, tracer, workspace, sandbox provider, plugin list. "Slots are singletons, shared across all processors in a configuration; processor state is instance-private. **P implements all per-step behavior; S houses the shared infrastructure that processors depend on but do not own.**"

**Processor protocol:** `async def process(self, event: Event) -> AsyncIterator[Event]`, producing exactly one of five outcomes — pass-through, transform, split, intercept (yield nothing, blocking propagation), interrupt (raise, halting the loop). Because every processor at a hook consumes and yields the same event type, processors compose by sequential application and can be inserted/removed without breaking pipeline type correctness. Three class-level metadata fields govern composition: `_singleton_group` (mutual exclusion class), `_order` (PRE/NORMAL/POST), `_after` (soft dependencies on other singleton groups). **The run loop validates hook contracts after each invocation: a violation raises immediately rather than silently propagating corrupted state.**

Nine-dimensional taxonomy: model selection, context assembly, memory management, tool ecosystem, execution environment, evaluation & reward, control & safety, observability, training bridge.

**AEGIS** — trace-driven evolution: Digester → Planner → Evolver → Critic, with a deterministic acceptance gate ("seesaw constraint": reject any edit that regresses even a single previously solved task under pass@2). Framed via an "operational mirror" mapping harness evolution to RL (states = configs, actions = typed edits, feedback = trace + verifier score), which *predicts* three pathologies: reward hacking, catastrophic forgetting, under-exploration.

### Evidence quality — real experiments, but a disqualifying methodological hole

Positives: 5 benchmarks (ALFWorld, GAIA, WebShop, τ³-Bench, SWE-bench Verified) × 3 task-agent families (Claude Sonnet 4.6, GPT-5.4, Qwen3.5-9B), up to 15 evolution rounds; token costs reported (43.4M–143.7M); three failure case studies documented with detection round, root cause, and outcome; a strategy ablation and a meta-agent ablation.

Headline: **average +14.5% absolute across 15 configurations, up to +44.0%**, with an inverse-scaling pattern — the weakest agent gains most (Qwen3.5-9B +44.0% on ALFWorld from a 53.0% baseline; Sonnet 4.6 only +11.2%).

**But — from the paper's own Limitations §7.7:**

> "**No held-out evaluation.** All reported gains are measured on the same task set used for evolution. Since we report **peak** accuracy and evaluate on the adaptation set itself, the numbers carry both **selection bias and potential overfitting**. Generalization to unseen tasks within the same distribution is plausible but untested."

Also: SWE-bench Verified runs use a **55-task subsample**; τ³-Bench covers three domains; meta-agent is closed-source (Opus 4.6) and open-weight meta-agents are untested; co-evolution requires joint control of harness and model training, which the authors concede is "impractical without cross-team coordination"; codebase "will be open-sourced in a future release" (i.e. not yet).

**The +14.5% headline should be read as a within-set peak, not a generalization result.** Meanwhile the paper's negative results are more credible precisely because they are self-damaging:

- **Global (single-harness) strategy on GAIA/GPT-5.4: Δ = 0.0 over 15 rounds**, peaking at R4 (73.8%) then degrading to 49.5% — a **−24.3pt peak-to-final gap**, which the authors verify exceeds the per-round binomial 95% CI (±8.5% at n=103), "confirming catastrophic forgetting."
- **SWE-bench/GPT-5.4 post-peak degradation:** 63.6% at R3 → 50.9% by R5.
- **τ³-Bench Telecom/Sonnet 4.6: −14.0% in a single round (R7)** from five consecutive same-type edits accumulating sub-threshold coupling that the per-edit gate could not see. "This is a structural limitation of per-edit gating: sub-threshold regressions accumulate undetected regardless of how many prior rounds have demonstrated apparent stability."
- Self-assessment of the theory: "We therefore treat the mirror as a **design checklist rather than a predictive theory**: it identifies failure modes to defend against but does not predict their ordering, timing, or relative severity."

### QMA should borrow — this is the most concrete kernel spec available

- **`H = (M, C)`: model config and harness config as disjoint, independently substitutable objects.** This is precisely QMA's provider-unbiased requirement, expressed as a type. Two agents sharing C but differing in M run the same pipeline; two sharing M but differing in C are behaviorally distinct. Adopt this split.
- **The P/S distinction is the sharpest kernel-boundary rule in the cluster:** *P implements all per-step behavior; S houses shared infrastructure that processors depend on but do not own.* Slots (tool registry, tracer, workspace, sandbox provider, plugin list) are **singletons**, processor state is **instance-private**. This resolves a question every plugin kernel gets wrong: plugins must not own infrastructure.
- **Typed hooks with declared permitted-modification sets, validated after every invocation, failing loudly.** The eight-hook table is a directly reusable design. The `step_end`/`task_end` read-only hooks are a good pattern for observability plugins that must not mutate.
- **The five processor outcomes** (pass-through / transform / split / intercept / interrupt) as the complete plugin return contract — small, closed, and enough.
- **`_singleton_group` / `_order` / `_after` metadata** as the minimum composition-control surface. Mutual exclusion is the important one; it is what makes substitution safe.
- **Variant isolation over a single global config.** Empirically it was both more effective (87.4% vs 49.5% final) *and* cheaper (107.8M vs 143.7M tokens). For QMA: per-mind (or per-task-cluster) harness variants routed by prior success rate, rather than one shared config that every change perturbs.
- **The deterministic acceptance gate** (reject any change regressing a previously-passing case) — plus the honest caveat that it does not catch accumulated sub-threshold coupling, so **cap consecutive same-type edits** as an additional rule.
- Deployment note worth keeping: "At deployment, the evolved harness is a static artifact requiring no meta-agent inference." Evolution is a build-time activity, not a runtime one.

### QMA should reject

- **The +14.5% headline as justification for building this.** No held-out set, peak reporting, small subsamples.
- **Self-evolving harnesses as an early QMA feature.** Three of three predicted pathologies actually fired in a well-instrumented system with a deterministic gate and a frontier meta-agent. QMA does not have the telemetry maturity to survive that. Build the *substrate* (typed hooks, traces); defer the *evolver*.
- The nine-dimensional taxonomy as a kernel module list — D6/D9 (evaluation-and-reward, training bridge) are research apparatus, not runtime concerns for a first QMA.
- Harness–model co-evolution entirely. Requires joint control of model training; QMA is provider-unbiased by design, so this path is closed.

### Kernel implications — **the strongest support for a plugin kernel in this cluster, but it endorses only two of its properties**

HarnessX *is* a Cordis-style plugin kernel, built and measured. And its **§6.4 meta-agent ablation is the single most useful result for QMA's kernel decision**:

Replacing the sophisticated four-stage AEGIS pipeline with a **single-agent evolver** sharing the same model, budget, and infrastructure gave 86.4% vs 87.4% — inside one standard error (~3.3% at n=103) — while consuming ~14% more tokens. The authors' conclusion:

> "With a capable meta-agent under variant isolation, **accuracy gains derive primarily from HarnessX's infrastructure (typed components enabling isolation, structured traces enabling diagnosis) rather than the evolver's internal architecture.** The four-stage decomposition contributes efficiency (~12% fewer tokens) and interpretability (auditable intermediate artifacts) but not measurable accuracy at this scale."

And §7.2's design principle: **"the richness of the feedback signal bounds the sophistication of evolution that can be safely performed."** From scalar reward alone, none of the three pathologies is detectable.

So the paper's own evidence says the value of the kernel is **(a) type-safe substitutability that enables isolation** and **(b) structured traces that enable diagnosis**. It does *not* say the value is in orchestration cleverness, pipeline depth, or a rich plugin taxonomy. That is a narrow, buildable mandate — and it is exactly congruent with 2605.18747's "topology complexity is a symptom" finding and with 2606.20683's "scaffold complexity does not predict effectiveness."

---

## Cluster verdict

### Top borrowings (ranked by evidence strength × applicability)

1. **The kernel/plugin boundary from 2606.20683 §8.3.** The kernel (general substrate) owns exactly seven services: **logging, isolation, permission control, persistence, cost accounting, standardized tool access, auditability**. Adapters/plugins own **observations, actions, verifiers, memory policies, and retry/rollback/stopping/escalation rules**. Orchestration topology is not a kernel concern. This is the most defensible boundary in the cluster and three other papers independently converge on it.

2. **`H = (M, C)` with P/S separation, from HarnessX.** Model config and harness config disjoint and independently substitutable (this *is* provider-unbiasedness as a type). Within C: processors implement per-step behavior; **slots** (tool registry, tracer, workspace, sandbox provider) are singletons that processors depend on but **do not own**. Eight typed hooks with declared permitted-modification sets, validated after every invocation, failing loudly. Five processor outcomes. `_singleton_group` for mutual exclusion.

3. **A formal, queryable state substrate as the highest-leverage kernel investment (2605.18747 §4.3–4.4).** Read/write sets, declared assumptions, version dependencies, belief-vs-ground-truth divergence, provenance. The evidence says elaborate orchestration is a *symptom* of missing formal state, and that "context management is the tax of implicit shared state."

4. **Scoped constants, concretely.** Context budget `C ≥ S+M+T+H+R` with α/β/γ/δ/ε ≈ 0.10/0.20/0.10/0.50/0.10 (2606.24937). Three permission tiers — read-only / sandbox-edit / full-access with mandatory HITL on the last — scoped over **(tool, arguments, environment state, data sensitivity, expected side effects)**, not tool identity alone (2605.18747). Isolation enum {none, process, container, wasm} and audit enum {none, basic, structured, tamper-evident} (2604.18071). Loop guards: max_steps, `hash(tool,args)` dedup window W, progress-stall, and escalation `p_success < τ_conf ∨ action ∈ A_irreversible ∨ cost > B_auto` (2606.24937).

5. **Trust as a runtime decision, not a stored property (2605.26112).** Per-entry confidence + time-of-last-verification as first-class fields; staleness penalty in retrieval ranking; retrieved content is a hypothesis until re-checked. Same mechanism covers stale-but-confident memory and confident-but-unchecked skills.

6. **PEV with deterministic sensors, and verification-governed termination (2605.18747).** Kernel as cybernetic governor. Termination governed by verification, not model confidence. Every accepted action carries an evidence bundle; every verifier declares what it cannot verify.

7. **Provider-unbiased computer abstraction as three clusters, not one (2605.18747 §3.4.3):** coding sandbox (fs/git/shell/pkg/exec) · computer-use substrate (browser/desktop/LSP/IDE) · durable runtime (microVM/WASM, snapshots, warm pools, resumable sessions).

8. **Maker–checker separation and mandatory external state (2606.24937).** A verifying sub-agent, potentially a different model/effort. External state file for progress, failure memory, and handoff — "need not be complex… but it must exist."

9. **Variant isolation over one global config (HarnessX).** More effective *and* cheaper than a single shared harness on heterogeneous task sets. Per-mind or per-cluster harness variants.

### Direct challenges to a Cordis-leaning plugin kernel

**Challenge 1 — the plugin architecture is a minority pattern, and it correlates with market ambition rather than capability.** (2604.18071, N=70) Plugin ecosystems are **10.0%** of projects; the modal tool system is a plain **explicit registry at 34.3%**. Formalized registration boundaries co-occur with platform/ecosystem positioning at support 0.62 / lift 2.8. The plugin architecture appears in the "Enterprise Full-Featured" bundle — the heaviest governance and infrastructure cost in the corpus, at 10% of projects. **If QMA does not intend third-party mind/plugin distribution, the plugin kernel is unpaid complexity.** If it does, the cost is real and should be budgeted as an ecosystem investment, not a performance one.

**Challenge 2 — scaffold complexity does not predict effectiveness, and it is measurable.** (2606.20683) The section heading is literal. mini-SWE-agent — a ~100-line scaffold that "leaves most orchestration to the model" — beats SWE-agent+tools on Opus 4/4.5 (**76.8% vs 73.2%**) and trails the full OpenHands runtime by 0.8pt. Agentless, a *non-agentic fixed pipeline*, beat interactive SWE-agent on GPT-4o by 15.6pt. Proprietary vendor scaffolds beat the best open scaffolds by only **2–4%**. Meanwhile the harness *does* matter — median within-model spread of **13.6pt** on Terminal-Bench 2.0, up to **41.5pt** on WebArena — so the lesson is not "harnesses don't matter." It is that **the payoff is in fit, not in layers**, and fit is an empirical property of the (model, harness) pair that no kernel abstraction can pre-decide.

**Challenge 3 — elaborate composition machinery is the scar tissue of missing formal state.** (2605.18747 §4.4) "Topology complexity inversely correlates with harness-state formality." L2MAC, with the clearest formal substrate, uses a *simple sequential chain*; implicit-state systems grow dynamic DAGs, workflow mutation, and agent-pool scaling "as a structural workaround." "Context management is the tax of implicit shared state." If QMA spends its kernel budget on plugin composition instead of a queryable state substrate, this predicts QMA will later grow exactly the orchestration complexity a kernel was supposed to prevent.

**Challenge 4 — the best evidence *for* a plugin kernel endorses only two of its properties.** (HarnessX §6.4) Swapping the sophisticated four-stage evolver for a single-agent one changed accuracy by 1.0pt (inside one SE). The authors attribute gains to "typed components enabling isolation, structured traces enabling diagnosis" — i.e. **type-safe substitutability and observability**, full stop. Not orchestration, not pipeline depth, not taxonomy breadth. And their headline +14.5% has **no held-out evaluation** and reports peak-on-adaptation-set, so even that is soft.

**Challenge 5 — the safety story does not come for free with the architecture.** (2604.18071) 40% of 70 projects have no audit trail; 17% no isolation at all; only 5% tamper-evident. And "capability growth does not automatically produce safety maturity." A plugin kernel that adds extension points without simultaneously adding permission, isolation, and audit *increases* attack surface while the safety dimension stays flat. The one strongly supported co-occurrence here (container isolation → policy-structured security, support 0.89 / lift 3.4, 100% of container-isolated projects) argues QMA should pair the isolation decision and the policy-engine decision as one move.

**Challenge 6 — "Python backend" buys no architectural argument.** Advanced subagent patterns by language: Rust 57%, Go 43%, Python 42%, TypeScript 40%. Language "constrains implementation style more directly than it constrains high-level harness architecture."

### The simpler approach this cluster actually supports

A **thin kernel** owning only what the evidence says must be central — permission (scoped over tool+args+env+data-class), isolation, audit/trace, persistence & formal state, cost accounting, standardized tool access, context budgeting with pre-flight token counting, and loop guards — plus **typed hook contracts with declared permitted modifications and loud validation**, and **singleton slot resources that extensions may use but never own**. Tool extension starts as an **explicit typed registry** (the empirical modal choice, 34.3%), with the dynamic plugin loader deferred until QMA has an actual external contributor or a measured need. Orchestration topology, memory policy, verifier selection, and stopping rules live outside the kernel as per-mind adapters, selected by the mind's (horizon, environment, autonomy) pressure profile.

That configuration keeps the two properties HarnessX's own ablation credits — **substitutability and observability** — while declining the layers that four separate papers, using four different methods, independently found do not pay.

### Where the cluster does not converge (and the honest reading)

Four papers, four incompatible harness decompositions: Gu's six `(R,M,C,S,O,G)`; Guo et al.'s six `(I_obs,C,L,I_act,S,V)`; Hu Wei's five empirical dimensions; HarnessX's nine. **The non-convergence is the finding.** No canonical decomposition exists yet, which means QMA should not enshrine one in the kernel's type system. Pick a working vocabulary — Guo et al.'s six responsibilities are the best-evidenced — and keep the *seams* (hooks, slots, permission scopes) more stable than the *taxonomy*.

Hu Wei's closing observation is the right note to end on, and it applies to QMA's own choice: "pluralism in Agent harness architecture is not merely a transient sign of immaturity; it is at least partly a consequence of genuinely competing infrastructural commitments." QMA should therefore justify its kernel by naming its commitment — third-party extensibility, or governed single-vendor reliability — because the evidence says those two commitments want different kernels.
