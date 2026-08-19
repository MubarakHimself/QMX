# T04 — AutoDesign: Meta-Harness Optimization for Long-Horizon Agentic Design

Source: arXiv 2608.13560v1 (13 Aug 2026), Meituan / MBZUAI et al. Read via full-text paper index on 2026-08-18.
Code: https://github.com/Yaxin9Luo/AutoDesign · Project: https://autodesign.designanything.ai/

## 1. What the paper actually does

AutoDesign runs **two nested loops** around a *fixed* model (weights never change — optimization acts only on the scaffold):

- **Inner loop (design harness H):** a designer module generates/revises an editable artifact (HTML poster); a critic (rule-based validator + VLM visual critic) returns localized feedback f_k. Up to K=12 refinement attempts; the inner loop terminates when a candidate passes all deterministic *blocking checks* (missing assets, broken provenance links, overflow/overlap, typography violations); if the budget is exhausted, fallback mechanisms pick a deliverable candidate from attempt history. Everything is recorded as an execution trajectory τ.
- **Outer loop (meta-harness):** improves H itself across tasks. Each iteration = **rollout → evaluation → update proposal → acceptance gate**.

## 2. What is measured

- **R_meta, the optimization-time evaluator.** Before optimization, an evaluator coding agent is given *human-annotated reference artifacts* scored along seven dimensions (Faithfulness, Coverage, Density, Visual Evidence, Layout, Readability, Aesthetics) and implements R_meta as rule-based checks for measurable properties + VLM judgment for perceptual ones. This is how human preference enters the loop — as a one-time grounding artifact, not per-step feedback. **R_meta is then frozen** during autonomous optimization (it can only be revised through explicit human input when a human spots systematic evaluator bias).
- **Objective J(H)** = expected R_meta score of artifacts produced by H over the task distribution, estimated on a training set D_train and an independent dev set D_dev.
- **Trajectories τ**, not just scores: the full sequence of actions, states, critic feedback, and revisions per run. The proposer mines these for *recurrent failure patterns* — process evidence, not only outcome scalars.
- **A frozen external benchmark (PosterBench)** sits entirely outside the loop for final system comparison; it is never optimized against.

## 3. What is mutable

H is decomposed into **five functional components**, and this decomposition *is* the mutability contract:

1. **Context & Memory** — source management, prompts, skills, reusable assets, persistent state
2. **Tools & Specifications** — tools plus editable artifact specs (layout, typography, provenance)
3. **Execution Runtime** — workspace/runtime for authoring, rendering, validating, exporting
4. **Orchestration** — task routing, attempt budgets, loop control, candidate selection, fallback, finalization
5. **Evaluation & Feedback** — rule-based validation, model-based critique, localized revision feedback

**Bounded updates:** each outer-loop iteration may modify *exactly one* component (multiple files inside it are fine, crossing components is not). This keeps credit assignment interpretable — every gain or regression is attributable to one coherent intervention. Immutable: model weights, R_meta (absent human input), the acceptance gate, and the dev set.

## 4. How changes are proposed, applied, rolled back

- **Proposal.** The optimizer P is a coding agent with two sequential roles. *Planner:* dispatches parallel subagents to inspect trajectories τ_t and scores s_t plus the optimization record L; synthesizes structured evidence of recurrent failures; emits an update plan (failure modes, the single component to modify, intended changes). *Code editor:* implements the plan on H_t, yielding candidate H′_{t+1}. Formally H′ = P(H_t, τ_t, s_t, L [, g_t]).
- **Acceptance gate.** The candidate is rolled out on both task sets. Accept iff **J_train strictly improves AND J_dev does not decline**. Dev-set results are used *only* by the gate and are never shown to P — a structural information firewall against overfitting the harness to training tasks.
- **Apply / rollback.** Single active harness, no tree search: on accept, H′ is promoted; on reject, H_t is simply retained (rollback is "don't promote"). Every iteration appends to the **optimization record L**: harness repository checkpoint, trajectories + scores, selected component, update plan, code diffs, and accept/reject decision. L is fed back to P as persistent context, so a rejected direction is remembered and the next proposal tries something different. L explicitly supports "comparison, reproducibility, and rollback across iterations."

## 5. How the loop terminates

- Nominally a **fixed iteration budget T** (Algorithm 1: for t = 0..T−1; return H_T and L).
- In practice the autonomous loop **plateaus** — the coding agent converges to a locally satisfactory harness. Two optional human channels then re-energize it: (a) natural-language *directional guidance* g_t injected into the planner; (b) *evaluator revision* when a human observes systematic artifact bias R_meta missed. Humans supply observations/direction only — they never directly edit harness or evaluator code.
- Reported scale: ~7 days of evolution, 224 subagents, ≥123 recursive iterations, **54 accepted harness updates**; final DesignHarness lifts 7 agent/model configs by +5.0 to +19.6 PosterBench points and beats Claude Design by 7.45.

## 6. DISTILLED: structural hooks the QMX chassis must expose

Requirements on a Cordis-style plugin core (everything reversible) so an AutoDesign-style meta-loop can be *built on top* — the SDK does not need to ship the meta-optimizer, it needs to make one possible:

1. **Harness-as-data with a component manifest.** Every mutable part of the operating harness (prompts, skills, tool specs, orchestration policies, validators) must live as inspectable, diffable files/config — never baked into opaque code — and be *partitioned into named components* with declared boundaries. The manifest is what lets an external optimizer enforce "one component per iteration" mechanically and attribute outcomes to a single intervention.
2. **First-class trajectory recording.** Every run emits a structured, queryable trace (tool calls, intermediate states, critic feedback, revisions, budget consumption) addressable by run-id. No trace, no evidence, no meta-loop. This must be an SDK guarantee, not a plugin's courtesy.
3. **Evaluator seam, outside the mutable surface.** A pluggable scorer interface — (artifact, source, context) → score vector — that the chassis invokes but that lives *outside* the harness's own mutable components, is versioned, and can only be changed through a privileged (human) channel. The inner-loop critic (component 5) and the outer-loop evaluator must be *different objects*; conflating them lets the optimizer grade its own homework.
4. **Atomic checkpoint / promote / reject on harness config.** Snapshot the full harness state per iteration; run a candidate config without it becoming active; promotion is a single reversible pointer flip; rejection costs nothing. Cordis's "everything reversible" maps directly here — but it must cover *harness configuration*, not just artifact/user actions.
5. **Shadow execution of candidate harnesses.** The SDK must be able to instantiate a second harness variant from a checkpoint and run it against a task batch in an isolated workspace, side-by-side with the incumbent, with no shared mutable state.
6. **A gate hook with an information firewall.** A policy point where scores on declared task sets decide promotion, where the SDK — not convention — guarantees the proposer process cannot read held-out (dev) results. This needs enforced data-visibility scoping between agent roles.
7. **Append-only optimization ledger.** A record store keyed by iteration (component touched, plan, diff, score deltas, decision, checkpoint ref) that the SDK exposes as context to future proposal runs. This is the meta-loop's persistent memory and the audit/rollback index.
8. **Declared mutation boundary / immutable kernel.** The SDK must let a deployment declare what the optimizer may touch (the component slots) versus what it may never touch (model choice, safety constraints, the gate, the evaluator, the ledger itself) — enforced at the plugin-loading layer, not by prompt discipline.
9. **Loop-control knobs as tunable config with hard ceilings.** Attempt budgets, fallback chains, candidate-selection policies are data the optimizer may rewrite; the chassis enforces non-negotiable outer ceilings (cost, wall-clock, attempts) so a bad update cannot run away.
10. **Human-guidance injection points.** Two typed channels: NL directional guidance into any proposal step, and a supervised evaluator-revision path — both structured as observations/direction, never direct edits, and both recorded in the ledger.

Litmus test: if the chassis exposes 1–7, a third-party plugin can *be* the meta-harness. 8–10 are what keep that plugin from optimizing its way out of its box.
