# C9 — Self-Improvement: what a kernel must expose, and whether a kernel is even the right shape

Cluster focus: the *structural* hooks self-improvement demands — what is measured, what is
mutable, how changes are validated / applied / rolled back — and whether any of these sources
propose a **simpler substrate than a Cordis-style plugin kernel**.

Coverage (no silent caps — every assigned item accounted for):

| # | Assigned | Status | Access route |
|---|---|---|---|
| 1 | 2608.13560 AutoDesign: Meta-Harness Optimization | READ (full text) | paper index full-text |
| 2 | 2605.09998 Continual Harness | READ (full text) | paper index full-text |
| 3 | 2604.25850 Agentic Harness Engineering (AHE) | READ (full text, v4) | paper index full-text |
| 4 | 2607.13104 Self-Improvements in Modern Agentic Systems (survey) | READ (full text) | paper index full-text |
| 5 | "Harness Engineering for Self-Improvement" (locate by title) | READ (full text) | **not a paper** — see below |

**Item 5 resolution.** The transcript link `alphaxiv.org/abs/2607.harness-3` is a malformed /
non-existent identifier. The exact title does not exist on arXiv. It resolves to a **blog post**:
Lilian Weng, "Harness Engineering for Self-Improvement", Lil'Log, 4 July 2026,
<https://lilianweng.github.io/posts/2026-07-04-harness/>. Confirmed by citation trails in four
independent arXiv papers (2608.08466, 2608.06301, 2608.09096, 2608.09885) all citing
"Weng (2026), Harness engineering for self-improvement, lilianweng.github.io". Read in full.
Treat its evidence weight accordingly: it is a well-sourced literature review by a credible
author, **not peer-reviewed and containing zero original experiments**.

---

## 1. AutoDesign — Meta-Harness Optimization for Long-Horizon Agentic Design (arXiv 2608.13560v1, 13 Aug 2026)

Meituan / MBZUAI / HUST / PKU / THU / CUHK / SJTU. Code: github.com/Yaxin9Luo/AutoDesign.

### 1a. Verification of the aborted agent's draft notes

The prior draft at `research/T04-autodesign-paper.md` was checked line-by-line against the paper
full text. **Sound and reusable**, with four corrections:

- **VERIFIED.** Two nested loops around a frozen model; five-component decomposition; exactly one
  component per outer iteration; acceptance gate `J_train(H') > J_train(H) ∧ J_dev(H') ≥ J_dev(H)`;
  dev results used *only* by the gate and never exposed to the proposer P; optimization record L
  contents; single active harness, no tree search; rollback = "retain H_t"; K=12 inner attempts;
  deterministic blocking checks + fallback chain; R_meta constructed once from human-annotated
  reference artifacts then frozen; evaluator revision requires explicit human input; optional NL
  directional guidance g_t; humans supply observations/direction only; PosterBench frozen and
  outside the loop; 78.32 main-track score; +7.45 over Claude Design; 54.99 → 67.39 average across
  seven configurations; ~7 days, 224 subagents, ≥123 recursive iterations, 54 harness updates.
- **ADD (draft missed it).** Dev-set trajectories and scores are **excluded from L**, not just
  hidden from the proposer at proposal time. The firewall is on the *record*, not merely on one
  prompt. That is a stronger and more implementable requirement.
- **ADD (draft missed it).** There are **three distinct evaluators at three levels**, not two: the
  in-harness image-native critic (component 5, mutable), R_meta (outer-loop, frozen per run,
  human-revisable only), and PosterBench (frozen external, never optimized against). The draft's
  point 3 is right but understated.
- **CORRECT — draft point 5 ("shadow execution … side-by-side with the incumbent") overstates the
  paper.** AutoDesign runs the candidate sequentially on D_train and D_dev and compares the
  resulting scalars to the incumbent's *stored* scores. There is no concurrent side-by-side
  execution and no isolated parallel workspace. Do not cite AutoDesign as evidence for a shadow
  -execution kernel requirement.
- **FLAG — unverified in draft.** The claim "+5.0 to +19.6 PosterBench points" per configuration
  was not located in the retrieved text; only the aggregate +12.40 average was confirmed. Treat the
  per-config range as unverified.

### 1b. Core mechanism (faithful)

A *design harness* `H` wraps a fixed model π_θ: `y ~ H(π_θ, x, c)`. H is decomposed into five
functional components — **Context & Memory; Tools & Specifications; Execution Runtime;
Orchestration; Evaluation & Feedback**. Critically, the paper states this "specifies only the
high-level abstraction … the concrete implementation of each component is instantiated and
iteratively improved by the meta-harness." The components are a *credit-assignment partition*, not
a runtime plugin API.

Objective `J(H) = E[R_meta(y,x,c)]`. Outer loop per iteration: rollout → evaluation → update
proposal → acceptance. P is a coding agent playing planner (dispatches parallel subagents over
trajectories, synthesizes recurrent failure evidence, emits a plan naming failure modes + the one
component + intended changes) then code-editor. Gate promotes or retains. L accumulates
{harness checkpoint, trajectories, scores, component, plan, diffs, decision} and is fed back to P.

### 1c. Evidence quality

Moderate-to-good, single-domain. Real external benchmark (PosterBench, 100 papers, 5 disciplines)
frozen before comparison; a system-blind human study with 933 pairwise judgments and bootstrap CIs
over both papers and reviewers; agreement between benchmark and human preference rises 51.9% →
74.4% as score gap widens. Weaknesses: **one task family** (paper→poster), **one optimization run**
(no seeds, no variance on the meta-loop itself), PosterBench is authored by the same group that
built the system, and R_meta shares its seven-dimension vocabulary with PosterBench — the
"frozen external evaluator" is less independent than the framing implies. Slides / webpage / video
outputs are explicitly labelled pilots with no evaluation.

### 1d. Borrow / reject

**Borrow.** (i) The information firewall as a *data-scope* rule: held-out results never enter the
record the proposer reads. This is cheap to implement and is the single most transferable idea in
the cluster. (ii) One-intervention-per-iteration as an *attribution discipline*. (iii) Three-tier
evaluator separation. (iv) Append-only iteration ledger that carries rejected directions forward so
the proposer does not re-propose them.

**Reject.** (i) The five-component taxonomy as an SDK-level API — it is domain-shaped (typography,
provenance, rendering) and the paper itself treats it as an abstraction the optimizer fills in.
Freezing it into QMA's kernel would import poster-generation ontology into a general agent SDK.
(ii) The human-annotated-reference bootstrap for R_meta as a general pattern — it presumes a
domain with gradeable reference artifacts. (iii) "Frozen R_meta per run" as a *safety* claim: it is
an anti-overfit device, and the paper is candid that the loop stagnates without human re-energizing.

### 1e. Kernel implications

**Demands very little kernel.** Everything AutoDesign needs is: a harness that lives as an
inspectable repository, per-iteration repository checkpoints, an append-only record file, and a
process boundary that keeps dev-set artifacts out of the proposer's readable scope. Checkpointing +
"don't promote" is *weaker* than a reversible-action kernel — rollback here costs nothing because
nothing was applied. **This is evidence against, not for, a Cordis-style everything-reversible
kernel**: AutoDesign gets reversibility from version control over configuration, not from a
transactional runtime.

The one genuine kernel-ish requirement is **scoped visibility between agent roles** — the SDK, not
convention, must be able to say "this subprocess may not read that directory."

---

## 2. Continual Harness — Online Adaptation for Self-Improving Foundation Agents (arXiv 2605.09998v1, 11 May 2026)

Princeton / ARISE / Google DeepMind (Karten, Zhang, …, Jin, Vodrahalli).

### 2a. Core mechanism (faithful)

Harness `H = (p, G, K, M)` — system prompt, sub-agents, skills, memory — following the PokeAgent
decomposition. The harness also exposes a fixed set of **meta-tools** (`define_agent`, `run_code`,
`process_memory`, notepad edits, custom tool creation) through which components are edited in place.

Two loops. Inner = ordinary agent step. Outer = **every F steps after a warm-up of W steps**, a
Refiner reads the recent trajectory window `τ_{t−F:t}`, identifies failure signatures (navigation
loops, tool-call failures, stalled objectives, missed exploration), and emits per-component edits
`Δ = (Δp, ΔG, ΔK, ΔM)`; `H_{t+1} = H_t ⊕ Δ`. Four passes: rewrite prompt; create/edit/delete
sub-agent entries (deleting ones never invoked productively); codify skills from successful
sequences and repair code that raised exceptions; add/update memory entries and demote stale ones.
p is *replaced*; G, K, M receive **CRUD** operations. Agent and Refiner share the same base model
and the same meta-tool API — "they differ only in when each is invoked and on what trajectory
context."

**The agent never resets.** This is the whole point: refinement information accumulates
monotonically within one episode, so late-episode failure modes (gym puzzles, dialogue chains) are
reachable, which reset-based prompt optimizers (GEPA, MIPRO) cannot reach by construction.

A third loop co-learns weights: 256-step DAgger rollouts inside the live-refining harness, a
pairwise process reward model over a sliding window, frontier-teacher relabelling of low-reward
windows, soft SFT. Emulator state at the end of iteration k is the start of k+1.

### 2b. THE CRITICAL POINT FOR US: there is no gate, no validation, no rollback

Continual Harness applies edits **immediately and unconditionally**. There is no acceptance test, no
held-out split, no promotion step, no revert. The paper is explicit that the loop *triages* rather
than validates: "it repairs the skills the agent depends on, tolerates regressions on unused ones,
and accepts a long create-and-forget tail." Most authored skills are never invoked; a small working
set absorbs the calls and gets repaired in-episode.

And it works: on Pokémon Red and Emerald, starting from `H_min` (frames, ASCII map, buttons, generic
prompt — no sub-agents, memory or skills), it substantially cuts button-press cost and recovers a
majority of the gap to a hand-engineered expert harness with no game decompilation, no milestone
schedule and no hand-built sub-agents. On Gemini 3.1 Pro / Emerald it is **strictly Pareto-dominant**
over the minimal baseline: 100% of milestones at $130 median vs 98% at $215 (~40% cost cut, no
completion loss). Navigation skills measurably converge toward a Dijkstra oracle — path-cost deficit
falls from a near-half-cost penalty to single digits and stays there, in-loop, reset-free.

### 2c. Evidence quality

Good by the standards of this cluster and unusually honest. ≥3 seeds everywhere, seed medians with
per-seed traces shown, two games, three model tiers, a cost–completion Pareto plane rather than a
single headline number, a negative control (Qwen3.5 without SFT warm-up emits parseable tool calls
but cannot leave the starting area), and per-store inheritance tables. The GPP completion record
(Blue, Yellow Legacy hard mode, Crystal) is real but is a *demonstration*, not a controlled result —
the authors say so.

Honest negatives the authors report themselves:
- **Capability floor.** On Gemini 3.1 Flash-Lite *every* Continual Harness variant is **worse** than
  the minimal baseline (3–13% vs 20% of milestones, at equal or higher cost). Below a capability
  threshold, self-refinement is net-harmful.
- **High variance mid-tier.** On Flash the benefit is marginal and noisy.
- **A documented regression from unvalidated edits.** In Red bootstrap-updating runs, newly authored
  sub-agents overtake inherited ones around step 213; they never went through the repair cycle, their
  per-invocation success is worse, and the milestone staircase regresses *below the minimal
  baseline*. Inherited sub-agent invocation share collapses to 6.4% ± 5.7 (vs 100% on Emerald).
  The authors' proposed fix is a **reuse prior or a deletion policy that deprecates newly authored
  components whose task signature is covered by inherited ones** — i.e. exactly the governance that
  the no-gate design omits.
- Memory reference rate "remains low in absolute terms, which we report honestly; most authored
  entries sit unused."

### 2d. Borrow / reject

**Borrow.** (i) **The meta-tool API as the mutation surface.** Editing the harness is done through
*the same tool-call channel the agent already uses* — not a separate privileged kernel path. That is
a genuinely simpler design than a plugin-mutation API. (ii) **CRUD semantics per store** rather than
whole-blob rewrite (prompt is the only replace-in-full component). (iii) **The harness, not the
episode, is the transferable unit** — bootstrap-updating inherits skills/sub-agents/memory across
runs and matches or beats bootstrap-frozen, so a mind's accumulated scaffold should be a portable,
loadable artifact independent of any single session. (iv) A **reuse prior / deprecation policy** on
newly authored components — the paper's own remedy for its worst failure.

**Reject.** (i) The unvalidated apply-immediately design as-is. Their own Red regression is the
argument. QMA deployments do work with consequences; "tolerate regressions on unused components"
is acceptable when the cost of a bad button press is one button press, not when a mind is acting on
a user's systems. (ii) Any claim that self-refinement is monotonically good — the Flash-Lite result
directly refutes that, and QMA is explicitly provider-unbiased, meaning it will be run on
weaker/cheaper models where refinement is *net-negative*. **A QMA self-improvement feature must ship
with an off switch and a stated capability floor, not as a default-on.**

### 2e. Kernel implications — this is the cluster's strongest "simpler substrate" datapoint

Continual Harness demands **no kernel hook whatsoever**. Its mutation surface is a fixed set of
ordinary tools (`define_agent`, `run_code`, `process_memory`); its four stores are ordinary
persistent state; its "outer loop" is a scheduled invocation every F steps. A plugin kernel with
lifecycle hooks, capability negotiation and a mutation API is strictly more machinery than this
paper needed to beat hand-engineered scaffolds from a bare interface.

What it *does* imply the substrate must have: **stores with CRUD and stable identity** (skills,
sub-agents, memories addressable by ID, with lifetime events — add / update / run / delete —
observable), and **a trajectory window readable by a same-model process**. Both are data-layer
concerns, not kernel concerns.

---

## 3. Agentic Harness Engineering (AHE) — Observability-Driven Automatic Evolution (arXiv 2604.25850v4, 18 May 2026)

Fudan / PKU / Shanghai Qiji Zhifeng. Code: github.com/china-qijizhifeng/agentic-harness-engineering.

### 3a. Core mechanism (faithful)

Thesis: harness evolution "is bottlenecked by *observability*, not by agent capability." Three
matched pillars.

**① Component observability.** The harness is instantiated on NexAU, which "exposes seven orthogonal
component types as explicit files at fixed mount points in a single workspace: system prompt, tool
description, tool implementation, middleware, skill, sub-agent configuration, and long-term memory."
Component types are *loosely coupled* — adding middleware does not require editing the prompt,
adding a skill does not touch a tool. Each failure pattern maps to one component class.
**"Each logical edit becomes one commit on the workspace's git history, which yields file-level
diffs and rollback granularity for free."** The seed H₀ is deliberately minimal (one shell tool, no
middleware, no skills, no sub-agents) so a pre-fitted seed cannot contaminate attribution.

**② Experience observability.** k traces per task. An "Agent Debugger" treats the trajectory set as a
navigable **file-based environment — each trajectory message in its own file, reached with generic
shell and scripting tools**. It produces a per-task root-cause analysis (including pass/fail),
aggregated into a benchmark-level overview that is the entry point each iteration. Raw and lightly
-processed traces remain available for verification. Layered for progressive disclosure.

**③ Decision observability.** The Evolve Agent adds/modifies/removes components and records, per
edit, a manifest entry naming: the failure evidence, the inferred root cause, the targeted fix, and
a **predicted impact comprising both expected fixes and at-risk regressions**. Next round, predicted
sets are intersected with observed task-level deltas to produce a per-edit verdict.

Algorithm 1 outer loop: rollout → clean → **attribute prior manifest, then Rollback rejected edits**
→ layered distillation → evolve (workspace edits + new manifest) → **Commit (git tag the
iteration)** → track best. Attribution runs *before* distillation so the verdict lands inside the
evidence corpus.

**Controllability constraints.** "The Evolve Agent writes only inside the harness workspace, while
the runs directory, tracer, verifier, and LLM configuration are read-only, and the seed system
prompt is marked non-deletable. These restrictions block the shortcuts an unconstrained
self-modifier would take, such as disabling the verifier, swapping the model, or raising the
reasoning budget."

### 3b. Evidence quality

**The strongest in this cluster.** Terminal-Bench 2, all 89 tasks, **k = 2 rollouts/task** (Table 4,
reference-run hyperparameters: "Rollouts per task k 2"; the paper notes generally that "the rollout
count k varies across experiments; each table states it explicitly"), ~32 hours,
official difficulty split, official pass@1 convention (timeouts count as failures). Ten iterations:
69.7% → 77.0%, beating three human-designed harnesses (OpenCode 47.2, Terminus-2 62.9, Codex 71.9)
and two self-evolving baselines from the same seed (ACE 68.9, TF-GRPO 72.3). All three role agents
share one base model, isolating the gain to harness edits rather than analyzer/editor capability.
Transfer is tested, not assumed: the *frozen* harness tops aggregate success on SWE-bench-verified at
12% fewer tokens, and gains +2.3 to +10.1 pp across five alternate bases including three other model
families. A component ablation and a self-attribution precision/recall study against random baselines
are both reported.

### 3c. THE THREE FINDINGS THAT CUT AGAINST OUR DIRECTION

These are the most important results in the cluster for QMA and must not be smoothed over.

**(i) Regression blindness — self-attribution is one-sided.** Fix-prediction precision 33.7% /
recall 51.4%, roughly 5× above random. **Regression-prediction precision 11.8% / recall 11.1%, only
~2× above the random baselines of 5.6% / 5.4%.** In the authors' words: "The agent can justify why
an edit should help, but it cannot reliably name the tasks the same edit is about to break." They
name regression foresight as "the clearest direction for future self-evolution loops."
→ **Any QMA design that lets a self-improvement loop reason about its own blast radius is building
on a capability that does not exist.** Blast radius must be bounded structurally (read-only scopes,
declared write surfaces), never predicted.

**(ii) Components interact non-additively — clean composition is a fiction.** Ablation on
Terminal-Bench 2: memory-only 75.3%, tool-only 73.0%, middleware-only 71.9%, prompt-only **67.4%
(a −2.3 pp regression)**, seed 69.7%, full AHE 77.0%. The three positive single-component gains sum
to +11.1 pp against full AHE's +7.3 pp; on Hard, memory-only (63.3%) *exceeds* full AHE (53.3%).
Reason: memory, middleware and prompt all push toward the same closure-style verification, so
stacking them spends turns on redundant re-checks.
→ **This is a direct challenge to the plugin-kernel mental model.** A plugin architecture's implicit
promise is that independently-good components compose to something better. Here, orthogonal file
-level components with clean boundaries *still* interfere behaviourally, and the aggregate is
capped below the sum. Component orthogonality at the *file* level does not buy orthogonality at the
*behaviour* level, and no kernel can make it do so.

**(iii) The system prompt is the wrong place to put strategy.** "Ablations further localize the gain
to tools, middleware, and long-term memory rather than the system prompt … factual harness structure
transfers across tasks and models whereas prose-level strategy does not." The prompt encodes 79
lines of "universal discipline whose executability depends on the other three"; inserted alone it
*loses* 2.3 pp. Prompt-only self-evolution (ACE, TF-GRPO) underperforms precisely because "neither
method opens the surrounding scaffolding to edits."

Authors' own limitations, stated: the step budget and per-task timeout were fitted to one base model
during evolution, so cross-model transfer conflates portability with operating-point coupling
(within one family the gain is non-monotone across reasoning tiers); "AHE bounds edits to a
workspace, attributes every change in a versioned manifest, and rolls back ineffective edits at file
granularity, **but it does not provide a complete guardrail stack** … AHE should be viewed as a
controlled research prototype rather than a fully mature autonomous self-improvement system."

### 3d. Borrow / reject

**Borrow — this paper is the cluster's design template.**
1. **Files at fixed mount points as the component contract.** Named component *types*, loosely
   coupled, each a file or directory. This is the mutability manifest, and it costs nothing.
2. **Git as the entire checkpoint/rollback mechanism.** One logical edit = one commit; file-level
   diffs and rollback granularity "for free"; iterations are git tags. There is no reason to invent
   a transactional kernel for something `git revert <path>` already does.
3. **The read-only boundary as the actual safety mechanism.** Runs directory, tracer, verifier and
   model configuration are read-only; the seed prompt is non-deletable. This is a *filesystem
   permission*, not a kernel policy engine, and it is what blocks the reward-hacking shortcuts.
4. **Traces as a navigable file environment** with layered distillation (per-task report →
   benchmark overview → raw trace on demand). Progressive disclosure is a token-budget mechanism
   and an agent-ergonomics mechanism at once.
5. **The falsifiable-prediction manifest.** Every edit ships expected fixes *and* at-risk
   regressions; next round intersects predictions with observed deltas; failed edits are reverted at
   file granularity. This converts self-justification into a measurable contract — and,
   conveniently, it is also how you measure that your loop has regression blindness.
6. **Minimal seed.** A pre-fitted starting harness contaminates every subsequent attribution.

**Reject.** (i) Trusting predicted regressions for gating — finding (i) says they are near-random;
use them as a *measurement of the loop's calibration*, not as a safety input. (ii) Assuming
component gains stack (finding ii). (iii) Investing evolution effort in system-prompt prose
(finding iii). (iv) The "seven component types" as a literal QMA taxonomy — they are coding-agent
shaped (middleware, tool description vs tool implementation). Take the *pattern* (named, loosely
coupled, file-backed, one failure class per component), not the list.

### 3e. Kernel implications — **AHE is evidence for a SIMPLER substrate, but not as simple as first written**

**Correction of record (fidelity defect, found on re-read of 2604.25850v4).** The earlier version of
this section stated that AHE's entire substrate is "a filesystem with fixed mount points, a loader
that reads those mounts, git, and OS-level read-only permissions — no plugin registry, no lifecycle
hooks, no capability negotiation." **The first half is right; the "no registry, no hooks" half is
wrong**, and the error ran in the anti-kernel direction. The paper's own evolve prompt (Appendix B)
is explicit:

> "**Creating a file is NOT enough — register in `code_agent.yaml`:**
> - New tool: create `.tool.yaml` + Python implementation + add entry to `tools:` list
> - New middleware: create Python class + add entry to `middlewares:` list with `import:` path and `params:`
> - New skill: create `skills/{name}/SKILL.md` folder + add to `skills:` list
> - New sub-agent: create `sub_agents/{name}/agent.yaml` + add to `sub_agents:` list. Framework
>   **auto-injects** `RecallSubAgent` tool — do NOT add it manually."

And on resolution: "The config directory is added to `sys.path` at runtime: `binding:
tools.file_tools:read_file` resolves to `workspace/tools/file_tools/read_file.py`; `import:
middleware.long_tool_output:LongToolOutputMiddleware` resolves to
`workspace/middleware/long_tool_output.py`." Middleware "has access to the agent's LLM client via
`ModelCallParams` in the **`wrap_model_call` hook**," and can make side-calls through an `LLMCaller`.

So what NexAU actually provides is: **a single declarative manifest with typed component lists, a
dotted-path binding resolver over a runtime-injected import root, framework-side auto-injection of
dependent tools, per-component `params:` blocks, and at least one named lifecycle hook that wraps
the model call.** That is a declarative typed plugin registry plus a lifecycle hook — **a thin
kernel**, not "folder + git + chmod." The correct statement of the challenge is therefore narrower
and, being accurate, more useful:

> AHE got component-level mutability, attribution, checkpointing, rollback and self-modification
> governance from a **declarative YAML component registry with import-path bindings and a model-call
> hook, plus git, plus OS read-only permissions** — and from *no* dynamic registration API, *no*
> capability negotiation, *no* dependency/substitution graph, *no* reversible-action runtime, *no*
> undo ledger, and *no* live reconfiguration (every iteration is a fresh process).

What is genuinely absent from AHE — and therefore what a QMA kernel still has to justify on its own
— is the **dynamic** half of a plugin kernel: runtime load/unload, identity-keyed provider
substitution, inverse/undo, capability negotiation, isolation realms, and anything that survives a
restart being unacceptable. What is *present* in AHE, and so cannot be counted as a QMA innovation,
is the **static** half: typed component types, a declarative manifest, binding resolution, and a
hook the framework calls.

Mapping, restated correctly:
- *mutability manifest* → **`code_agent.yaml`, a real declarative registry** (not merely a directory convention),
- *component discovery/binding* → **`sys.path` injection + `module:symbol` bindings** (a loader with a resolution rule),
- *lifecycle interception* → **`wrap_model_call` middleware hook** with LLM-client access,
- *checkpoint / promote / reject* → git commit / tag / revert,
- *declared mutation boundary* → filesystem write permissions,
- *audit ledger* → an append-only JSON manifest + git history,
- *trace store* → a directory of files.

The irreducibly kernel-shaped requirements are then (a) **the loader plus its binding/registration
contract** — which AHE has and needed; (b) **enforced read-only scoping** of the tracer, verifier,
model config and evaluator, at load time not by prompt discipline; and (c) **auto-injection of
framework-owned dependencies** (`RecallSubAgent`) — a small but real kernel service, since the
component author is explicitly told *not* to declare it.

**Net effect on the anti-kernel case:** it survives, but the baseline it sets is higher than the
old wording implied. The gate to beat is not `folder + git + chmod + a loader`; it is
`folder + git + chmod + a loader + a declarative typed component manifest with binding resolution
and one model-call hook`. Any acceptance test written against the weaker baseline is measuring the
wrong thing.

---

## 4. Self-Improvements in Modern Agentic Systems: A Survey (arXiv 2607.13104v1, 14 Jul 2026)

Jilin University / KAUST / Alberta / IDSIA — Ren, Chen, Guo, …, Zhuge, **Schmidhuber**.
Tracker: github.com/selfimproving-agent/awesome-Self-Improving-Agents.

### 4a. Core mechanism (faithful)

A formal frame, not a system. Agent configuration `A_t = (θ_t, Σ_t)` where θ is FM parameters and
Σ is the **operational scaffold**, decomposed as `Σ_t := (p_t, m_t, T_t, g_t)` — structured prompts,
memory (with its retrieval and update policies), external tools with invocation interfaces, and
**control logic g_t such as routing, scheduling, or safety constraints**. Induced policy
`π_{θ,Σ}(A_t | X_t)`, where `X_t` is an **ephemeral execution state** (KV caches, intermediate
plans, working memory) that is discarded at task boundaries and explicitly *not* part of the agent's
intrinsic architecture.

Self-improvement is a **self-induced update operator**:
`A_{t+1} = U(A_{1:t}, E(π_{θ_t,Σ_t}; Σ_t, C_t))`,
factorized into an execution phase E (the agent runs, producing trajectories, reflections, critiques,
or *proposed edits*) and an update phase U (which **commits durable changes**). Σ_t is passed as an
explicit argument to E "to permit direct self-inspection (e.g. critiquing prompt templates or
auditing tool configurations)."

Two modes: **foundation-model improvement** (θ updates, Σ fixed — indirect, distributional,
slow, expensive, global) and **scaffolding improvement** (Σ updates, θ fixed — direct, action-level
self-modification; "typically faster, more reversible, and more context-dependent"). Scaffolding
improvement further splits by target: prompt optimization, memory evolution, tool governance, and
**full scaffolding update** (holistic reconfiguration, treating the codebase and operational logic
as mutable substrate — ADAS, Darwin Gödel Machine, AlphaEvolve, Live-SWE-agent).

### 4b. The three definitional moves QMA should adopt

**(i) The intrinsic/ephemeral split.** `(θ, Σ)` is the mind; `X_t` is the run. A mind's identity is
its scaffold, not its session. This is a clean architectural boundary and it maps directly onto
"deployable semi-profile" — a QMA mind *is* a Σ.

**(ii) Version history as the validation-and-rollback primitive.** The survey writes the update as
`Σ_{t+1} = IMPROVE_Σ(Σ_{1:t}; S_t)` — over the **history**, not the current state — and states:
"By maintaining a version history (Σ_{1:t}), the system inherently supports validation and rollback
against harmful modifications across all components." Same for parameters: "θ_{1:t} denotes the
parameter history, enabling validation and rollback (e.g. reverting to a prior checkpoint)."
→ The survey's answer to "how are changes rolled back" is **keep versions**. Not transactions, not
reversible actions. Versioned config.

**(iii) Skill = a reusable, serialized instance of the update operator.** "A skill is a named update
to the agent's own configuration that it retains and reuses. Acquiring a skill serializes this
update into one of A_t's substrates: a tool and its calling convention, an instruction or workflow,
a memory entry, consolidated weights, or control logic. The skill's identity is the update it
encodes; the substrate only names where it is stored." Two scopes: **object-level** (acts on world
/ task state — the agentic analog of an HRL option) and **meta-level** (acts on the agent's own
configuration: writing a tool, refactoring a prompt, consolidating memory, patching its own
scaffold). "For self-improvement, the meta-level scope is the central one." Reusability comes in two
forms: repeatedly-invoked routine, or **installer** — applied once, valued for the persistent change
it leaves behind, but still a portable artifact reusable across agents and sessions.

This is a materially better definition of "skill" than the SDK-typical one and it is *substrate
-agnostic by construction* — which is precisely QMA's provider-unbiased posture.

### 4c. Evidence quality

It is a survey: zero original experiments, and its taxonomy is a *classification*, not a validated
claim. Authority is high (Schmidhuber's group; the framing is explicitly rooted in his 1987–1997
self-referential meta-learning line) and the coverage is broad (~700 references). But QMA must not
treat any of its statements as empirically established. Notably, its assertion that version history
"inherently supports validation and rollback" is asserted, not demonstrated — and AHE's regression
blindness and Continual Harness's Red collapse are the empirical texture the survey lacks.

### 4d. The safety statement, and the applications observation

The survey's one concrete governance requirement: "**Before any structural update is committed to
Σ_{t+1} or θ_{t+1}, the proposed patch must pass verifier-gated checks, covering functional
correctness, tool permission boundaries, and robustness to random state perturbations. Improvement
is only permitted within an explicitly defined and continuously audited safety boundary.**"

Note what that names: *permission boundaries* and *a verifier*, not a kernel. And it names a check
none of the systems in this cluster implement — **robustness to random state perturbations**. AHE
gates on aggregate pass@1; AutoDesign on two task-set means; Continual Harness on nothing. Nobody
perturbs. That is a real gap and a cheap thing for QMA to be first at.

On applications, the survey's cross-domain pattern is worth quoting for QMA's sandbox abstraction:
"a common pattern is the use of **sandboxed or otherwise controlled environments that provide
feedback while limiting the cost of failure** … The fidelity, scalability, and cost of these
environments shape each domain's dominant bottlenecks, improvement targets, and iteration modes."
Software engineering is singled out as the easy case precisely because compilers, tests, linters and
CI "turn many agent actions into checkable outcomes."

Open problems relevant to us: test-time continual adaptation, where "implementing such on-the-fly
patching introduces a critical trade-off: we should manage these localized updates carefully to
prevent them from subtly eroding the system's long-term global performance"; and joint θ/Σ
optimization, which "requires solving a formidable credit assignment problem: when the agent fails,
the improvement operator should autonomously decide whether the better fix is to refine a prompt,
rewrite a tool wrapper, or compute a gradient update."

### 4e. Borrow / reject / kernel implications

**Borrow.** The `(θ, Σ)` vs `X_t` split; `Σ = (p, m, T, g)` as QMA's mind-shape with **control logic
including safety constraints as a first-class scaffold component**; version history as the rollback
primitive; the skill-as-serialized-update definition with object/meta scopes and the installer form;
the verifier-gated-commit + audited-boundary requirement; **robustness-to-perturbation as a
validation check nobody else runs**.

**Reject.** Its taxonomy as evidence of anything; the implicit optimism that scaffolding improvement
is "more reversible" therefore safer (Continual Harness's regression happened *in* the reversible
layer, and nothing reverted it because nothing was watching); and any read that full-scaffolding
self-modification is a settled practice — the survey's own takeaway concedes "achieving truly
open-ended recursive self-improvement remains a grand challenge" and that current systems
operationalize it only as "bounded, verifiable loops."

**Kernel implications: neutral-to-negative for a plugin kernel.** The survey's Σ is a *configuration
record*, and its update operator is a function over the *history* of that record. Nothing in the
formalism requires a runtime plugin system. The one thing it demands that a config file cannot
provide is the **verifier-gated commit path with an audited permission boundary** — a gate, an
audit log, and a scope enforcer. That is three components, not a kernel.

---

## 5. Lilian Weng — "Harness Engineering for Self-Improvement" (Lil'Log, 4 Jul 2026) — NOT A PAPER

Blog post. No original experiments. Value is as a well-sourced map plus one credible practitioner
warning. Weigh accordingly.

### 5a. Core content

Defines a **harness** as "the system surrounding a base model that orchestrates execution and decides
how the model thinks and plans, calls tools and acts, perceives and manages context, stores
artifacts, and evaluates results" — extending "agent = LLM + memory + tools + planning + action" with
**workflow design, evaluation, permission controls, and persistent state management**. Explicitly:
"It is no longer only prompt templates, but closer to **runtime and software system design**." Draws
an OS analogy: "similar to an OS, a harness should encapsulate complicated logic while keeping the
interface simple," and predicts configs, tool interfaces and protocols will standardize.

The organizing claim: **the object being optimized progresses "instruction prompts → structured
context → workflow → harness code → optimizer code."** As models get stronger, targets get more
complex and methods get *more generic and less heuristic*: "The harness system itself becomes an
optimization target, with fewer heuristic rules and more general mechanisms."

Three design patterns: (1) workflow automation as a goal-oriented plan/execute/observe/improve loop;
(2) **file system as persistent memory** — "A harness should not carry the entire workflow and all
logs in context; instead, it should keep durable state in files," and reading/writing/editing files
via bash "is a foundation skill for LLMs, and thus managing persistent memory in the simple form of
files naturally benefits from improvements in core model capability"; (3) sub-agents and backend
jobs, where "the key design choice is to make parallelism explicit and inspectable. If subagent
outputs only live in a transient chat context, they quickly become obsolete and hidden. If they are
stored as files, logs, and status records, the model can recover after interruptions and reason over
its own execution history."

Reviews ACE (context as an itemized playbook of `(identifier, description)` bullets merged by
**deterministic** logic — the curator never rewrites a full prompt blob, specifically to prevent
context collapse and brevity bias), MCE (bi-level: meta-level skill evolution over context
*mechanisms*, base-level context optimization; a context function is "a collection of files in a
dedicated directory" including `skill.md` plus dynamic rollouts, optimized with a standard
`{Read, Write, Edit, Bash, Glob, Grep, TodoWrite}` toolset), Meta-Harness (optimizes the *code*;
"the entire execution history is accessible via a file system, and thus the coding agent uses
commands like `grep` or `cat` to read through it instead of shoveling everything into a single
prompt context"; each candidate harness is "a dictionary in the file system containing its own
source code, scores, rollout trajectories, and state updates"; output is a Pareto frontier of
candidates), ADAS, AFlow (MCTS over workflow graphs), STOP, Self-Harness, AHE, and the evolutionary
line (Promptbreeder, GEPA, AlphaEvolve with its explicit `# EVOLVE-BLOCK-START/END` markers,
ShinkaEvolve, Darwin Gödel Machine).

### 5b. The two findings that matter most to us

**(i) The abstraction-boundary warning — stated directly against self-modifying harnesses.**
"Self-harness type of work does raise my concerns that **if a program is allowed to edit the OS
system, abstraction boundaries are broken. The editable surface needs to be properly designed and
the permission control and security layers need to live outside this loop.** All the challenges
around reward hacking still remain."

Restated in the challenges section: "**The evaluator and permission control should likely sit
outside the loop that evolves harness**, with held-out tests, trace audits, and human review at
decision points that matter."

This is the single most kernel-relevant sentence in the cluster, and it is a *constraint on* the
design, not a feature request: the mutation loop and the permission/evaluation layer must be
different systems, with the latter not reachable from the former. AHE implements exactly this
(read-only tracer/verifier/model-config); AutoDesign implements the evaluator half; **Continual
Harness implements neither.**

**(ii) Capability dependence, twice.** STOP improved downstream performance with GPT-4 but *degraded*
with GPT-3.5 and Mixtral — "Recursive structure alone is not enough. The base model must be capable
enough to improve the mechanism." And Lin et al. 2026 (arXiv 2605.30621, *Harness Updating Is Not
Harness Benefit*) disentangle two axes: **harness-updating capability was flat from ~9B up to Claude
Opus 4.6** — "the 9B harness proposer/evolver is able to write a skill procedurally isomorphic to
Opus" — while **harness-benefit capability is non-monotonic, with middle-tier models benefiting
most.** To use a harness a model must "invoke skills/tools correctly and timely and be good at
long-horizon instruction following."

→ For a provider-unbiased SDK this is directly actionable and slightly counter-intuitive: **you can
run the improver on a cheap model; what you cannot do is assume the improved scaffold helps every
executor.** The scaffold-benefit axis, not the scaffold-authoring axis, is where model choice bites.

### 5c. Other challenges Weng names that QMA should not paper over

Weak/fuzzy evaluators (self-improvement loops "work best for tasks when evaluation metrics are
measurable and objective"); context/memory lifecycle; **negative results** ("a research harness
should make failed attempts easy to preserve, as learning from failure is the best way to trim down
the task search space" — and LLMs are biased against reporting failure because the literature is);
**diversity collapse** ("evolutionary and RL loops tend to exploit known high-reward patterns … this
is especially critical for open-ended research, where the best path may initially look worse under
the current evaluator"); reward hacking against whichever signal is supplied (tests → overfit tests;
judge model → judge-specific tricks; benchmark → benchmark artifacts); long-term vs short-term
objectives ("standard sandbox-based RLVR-style training rarely captures maintainability, ownership
boundaries, migration cost, backwards compatibility, or future debugging burden"); and the role of
humans — "**humans should move up the stack, not be removed from the loop** … our system design
should consider when and how to set up such touch points."

She also cites the Trehan & Chopra failure taxonomy for autonomous research agents: bias toward
training-data defaults; **implementation drift under execution pressure** (when the task gets hard,
the model quietly reverts to a simpler standard solution instead of the proposed method);
memory/context degradation unless logs are written as persistent artifacts; **over-optimism** —
declaring success on noisy or failed experiments, the "numerical duct tape" pattern; insufficient
domain intelligence; weak scientific taste. Every one of these is a failure mode a QMA
self-improvement loop would inherit.

### 5d. Borrow / reject / kernel implications

**Borrow.** The permission-and-evaluation-outside-the-loop rule as a hard architectural invariant;
files-as-durable-state and traces-as-a-navigable-filesystem; ACE's deterministic itemized merge
(never let an agent rewrite a whole context blob free-form); explicit inspectable parallelism (sub
-agent output must land in files/logs/status records, not transient context); the
harness-updating vs harness-benefit distinction as a model-selection rule; preserving negative
results as first-class artifacts; the `# EVOLVE-BLOCK` idea of *explicitly marked* editable regions.

**Reject.** Everything here as *evidence*. It is a literature map, not a result. Also reject the
implicit trajectory "→ optimizer code" as something QMA should chase — it is Weng's forecast, and
her own listed bottlenecks (fuzzy evaluators, reward hacking, diversity collapse) all get worse at
that level.

**Kernel implications.** Two, pulling in opposite directions. *Pro-kernel:* the OS analogy and
"permission control and security layers must live outside this loop" argue for a real,
non-agent-reachable enforcement layer — the strongest argument in the cluster for something
kernel-shaped. *Anti-kernel:* every concrete mechanism she praises is filesystem-based, and she
explicitly frames the direction of travel as "fewer heuristic rules and more general mechanisms."
The synthesis is a **thin, non-negotiable enforcement boundary around a filesystem-shaped mutable
region** — not a rich plugin kernel.

---

## CLUSTER VERDICT

### Answering the assignment's three questions directly

**What is measured?** Not scalars alone — every system that worked measured **trajectories**.
AHE: k traces/task distilled into per-task root-cause reports + a benchmark overview, with raw
traces retained for verification. AutoDesign: full execution trajectories τ mined by parallel
subagents for *recurrent* failure patterns. Continual Harness: a sliding trajectory window scanned
for named failure signatures. Outcome scores decide promotion; **process evidence drives proposal**.
A QMA that emits only success/failure metrics cannot host any of these loops.

**What is mutable?** Convergent answer across all four systems: **prompt, tools (description and
implementation separately), skills, sub-agents, memory, and control/orchestration logic** — declared
as *named, loosely-coupled, file-backed component types*, one failure class per type. Immutable in
every system that took safety seriously: the tracer, the verifier/evaluator, model selection and
reasoning budget, the gate, and the audit record.

**How are changes validated / applied / rolled back?** Three distinct answers, and the spread is the
finding:
- **AHE**: git commit per logical edit; falsifiable prediction manifest; next-round attribution;
  `Rollback` reverts rejected edits at file granularity; iterations are git tags.
- **AutoDesign**: candidate run on train+dev; promote iff train improves and dev does not decline;
  rejection = retain incumbent (rollback is free because nothing was applied); append-only record L.
- **Continual Harness**: applied immediately, never validated, never rolled back — and it produced
  the cluster's one documented catastrophic regression.

### Top borrowings for QMA (ranked)

1. **AHE's substrate**: named component types as files at fixed mount points + git for
   checkpoint/diff/rollback + OS read-only permissions on tracer, verifier, evaluator and model
   config. This is the whole self-improvement substrate, and it is not a kernel.
2. **AutoDesign's information firewall**, at record scope: held-out results never enter the
   artifact the proposer reads. Plus one-intervention-per-iteration for attribution.
3. **AHE's falsifiable-prediction manifest** — expected fixes *and* at-risk regressions per edit,
   verified next round. Use it to measure the loop's calibration, not to gate on.
4. **The survey's `(θ, Σ)` vs `X_t` split** and `Σ = (p, m, T, g)` with safety constraints inside
   control logic — a QMA mind *is* a Σ, portable and versioned.
5. **The survey's skill definition**: a serialized, named, reusable instance of the update operator,
   with object-level vs meta-level scope and an "installer" form. Substrate-agnostic by
   construction, which fits QMA's provider-unbiased posture.
6. **Continual Harness's meta-tool API** — mutation happens through ordinary tool calls, not a
   privileged kernel path — plus CRUD-with-stable-identity stores and observable component
   lifetimes, plus a **reuse prior / deprecation policy** for newly authored components.
7. **Weng's invariant**: evaluator and permission control live *outside* the loop that evolves the
   harness. Non-negotiable.
8. **The survey's unimplemented check**: robustness to random state perturbations before commit.
   Nobody in this cluster does it; cheap differentiator.

### DIRECT CHALLENGES TO OUR CURRENT CORDIS-LEANING KERNEL DIRECTION

**Challenge 1 — The winning substrate is a filesystem, git, and a permission bit. Not a plugin
kernel.** AHE is the best-evidenced system here (Terminal-Bench 2 full panel, transfer to
SWE-bench-verified and to three other model families, ablations, calibration study) and it needs
zero kernel machinery: seven component types as files at fixed mount points, one commit per edit
giving "file-level diffs and rollback granularity **for free**", and read-only permissions on the
things the optimizer must not touch. Meta-Harness stores each candidate harness as a directory of
source + scores + trajectories. MCE stores a context function as a directory with `skill.md`.
AutoDesign checkpoints a repository. Continual Harness edits four stores through ordinary tools.
**Four independent groups converged on version-controlled files, and none of them built a plugin
kernel.** Before QMA commits to one, the design must state what it buys that
`directory layout + git + chmod + a loader` does not.

**Challenge 2 — "Everything reversible" is the wrong primitive; "nothing applied until promoted" is
cheaper and stronger.** AutoDesign's rollback is *don't promote* — zero cost, zero machinery,
because the candidate never became active. AHE's rollback is `git revert` on a path. The survey's
rollback is "keep the version history." A Cordis-style reversible-execution kernel solves a harder
problem than any of these systems needed solved, and reversibility of *actions* is a different
problem from versioning of *configuration* — the self-improvement literature only ever needed the
latter.

**Challenge 3 — Clean plugin composition is empirically false.** AHE's ablation: three
single-component gains summing to +11.1 pp deliver +7.3 pp together; memory-only *beats* full AHE on
Hard tasks; system-prompt-only *regresses* the seed. Components were file-level orthogonal by
construction and still interfered behaviourally, because several independently push the same
strategy. A plugin kernel's core promise — good parts compose — does not survive contact with this
result, and no kernel feature can rescue it. QMA should plan for **interaction-aware evaluation of
component sets**, not per-plugin validation.

**Challenge 4 — The system cannot see its own blast radius.** AHE's regression-prediction precision
is 11.8% against a 5.6% random baseline. Any QMA hook that asks a self-improving mind to declare
what its change might break will get near-noise. **Containment must be structural — declared write
scopes, read-only evaluators, hard ceilings — and never predictive.**

**Challenge 5 — Self-improvement is net-harmful below a capability floor, and QMA is
provider-unbiased.** Continual Harness on Gemini 3.1 Flash-Lite: *every* variant underperforms the
minimal baseline at equal or higher cost. STOP degraded on GPT-3.5 and Mixtral. Lin et al. find
harness-*benefit* is non-monotonic (middle tiers gain most) even though harness-*authoring* is flat
from 9B upward. An SDK that is deliberately model-agnostic must therefore treat self-improvement as
an **opt-in capability with a declared floor and a measured off-switch**, never as a default kernel
service — otherwise it degrades exactly the cheap-model deployments that provider-unbiasedness is
meant to serve.

**Challenge 6 — Prose is the worst place to put the improvement.** Gains localize to tools,
middleware and long-term memory; "factual harness structure transfers across tasks and models
whereas prose-level strategy does not," and prompt-only evolution regressed. If QMA's mutable
surface is mostly prompt/persona text, the self-improvement story has no engine.

### The residual, honest case for something kernel-shaped

Stripped of everything the filesystem already does, exactly three requirements survive across all
five sources:

1. **A loader** that mounts declared component types into a running mind (AHE's "fixed mount
   points"; AutoDesign's component partition; Continual Harness's four stores).
2. **An enforced read-only boundary** around tracer, evaluator/verifier, model configuration,
   gate and audit ledger — enforced at load time, not by prompt discipline (AHE's controllability
   constraint; Weng's "permission control and security layers must live outside this loop"; the
   survey's "continuously audited safety boundary").
3. **Scoped visibility between agent roles**, so held-out evidence is unreachable from the proposer
   (AutoDesign's firewall, extended to the record itself).

That is a *thin* kernel — a loader, a permission model, and a scope enforcer — sitting under a
version-controlled directory. It is materially smaller than a Cordis-style plugin kernel, and this
cluster provides no evidence for the difference.
