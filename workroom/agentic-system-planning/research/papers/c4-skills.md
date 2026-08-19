# Cluster 4: Agent Skills — what a skill IS, verification-gated evolution, brittleness

Transcript (`chat-harnes.txt`) consulted only for why the cluster was assembled — treated as
casual pointer, not authority. Findings below are graded on each paper's own claims/evidence,
not fitted to our Cordis-leaning kernel framing.

## Coverage ledger (no silent caps — every assigned item accounted for)

| # | Assigned (ledger §4) | Status | Access route |
|---|---|---|---|
| 1 | 2605.07358 — A Comprehensive Survey on Agent Skills | READ (full text) | AlphaXiv PDF asset |
| 2 | 2604.01687 — CoEvoSkills | READ (full text) | AlphaXiv PDF asset |
| 3 | 2605.23904 — SkillOpt | READ (full text) | AlphaXiv PDF asset |
| 4 | 2604.08377 — SkillClaw | READ (full text) | AlphaXiv PDF asset |
| 5 | 2608.14036 — Demystifying Agent Skills | READ (full text) | AlphaXiv PDF asset |
| 6 | 2605.25430 — CODESKILL | READ (full text) | AlphaXiv PDF asset |
| 7 | 2603.18743 — Memento-Skills: Let Agents Design Agents | READ (full text) | `pdfs.assets.alphaxiv.org/2603.18743v1.pdf` |

**Correction of record.** The first version of this file covered only items 1–6 while asserting
"all 7 reached; no unreachable papers, no coverage gaps," and its verdict claimed a "converged
definition across all 7 papers." Item 7 (Memento-Skills) was silently absent. It is fully
reachable and it is load-bearing: it is the only paper in the cluster that proposes a concrete
**routing mechanism** for the retrieval-precision problem Demystifying measures. It is written up
in full below (last paper section), and the verdict is rewritten accordingly. Recorded rather than quietly
patched, because the failure mode — a coverage claim not backed by a per-item table — is exactly
what this table exists to prevent.

**Cross-cluster note.** A seventh-plus source bearing directly on this cluster sits in `c10`:
SkVM (2604.03088) analyses 118,000 published skills and finds that *enabling* a skill degrades
performance on **15% of tasks** (7% for Opus 4.6, 25% for Qwen3-30B) and changes nothing on a
further 17% — an independent, larger-N corroboration of Demystifying's brittleness finding, plus
the model-dependence dimension none of the six original papers measures.

---

## 2605.07358 — A Comprehensive Survey on Agent Skills (Zhou et al.)

**Core mechanism (faithful).** Formalizes a skill as a tuple `S = (M, R, C)`: `M` = root
instruction document (the human-readable "what/when/how"), `R` = optional auxiliary resources
(text references, executable scripts, or hybrid), `C` = applicability/trigger conditions
governing retrieval. Organizes the field into a 4-stage lifecycle: **representation** →
**acquisition** (human-derived / experience-derived / task-derived / corpus-derived) →
**retrieval** (context-aware, compositional, cost-aware, feedback-reranked selection) →
**evolution**, which itself decomposes into revision (content edit) → validation (held-out
survival check) → policy coupling → repository evolution (shared/collective growth, e.g.
SkillClaw, SkillNet) → runtime governance (routing + trust, e.g. SkillRouter, PoisonedSkills).
Explicitly distinguishes skills from raw tools/MCP: a tool exposes *what* can be done, a skill
encodes *when/how/pitfalls* — MCP solves interoperability, not the procedural gap.

**Evidence quality.** Survey (~170 papers systematized), not original experiments — but
grounded in cited empirical benchmarks (SkillsBench, SRA-Bench) and names five live production
skill platforms (SkillNet 300k+, SkillsMP 700k+, ClawHub 40k+, etc.), so the taxonomy reflects
deployed practice, not just papers.

**Borrow.** The `(M, R, C)` tuple as QMA's minimal skill schema. The named open challenge of
**"asymmetric revision"** — systems are far better at *adding* skills than at safely rewriting
or retiring them — is a direct hit on our promotion-gate design law; the survey explicitly
flags this as unsolved across the field, not just a hypothetical risk. Also flags
**"weakly specified repository-scale governance"**: once skills are shareable, the live question
becomes who can publish/trust/deprecate, and **PoisonedSkills** shows third-party skill docs can
hide malicious logic an agent later executes as trusted guidance — a supply-chain risk directly
relevant to any QMA skill-hub/import feature.

**Reject.** None of the taxonomy itself is wrong to adopt; the risk is treating "no unified skill
schema exists yet" as license to under-specify QMA's own — the survey names this as the #1 future
direction precisely because ad hoc schemas are already causing interoperability pain industry-wide.

**Kernel implications.** Confirms our design law that skills need their own registry with
distinct promotion rules from tools/memory. Does **not** by itself argue for a Cordis-style
plugin kernel over something simpler — it argues for a schema + lifecycle contract (fields:
scope, trigger, dependencies, versioning, safety constraints), which a kernel hook can enforce
but which doesn't *require* one.

---

## 2604.01687 — CoEvoSkills: Self-Evolving Agent Skills via Co-Evolutionary Verification

**Core mechanism (faithful).** Two independent LLM roles co-evolve: a **Skill Generator**
produces/executes a candidate multi-file skill package, and an informationally-isolated
**Surrogate Verifier** (separate session, no shared context or bias) independently writes test
assertions against the output and returns structured failure diagnostics. When the surrogate
passes, a **Ground-Truth Oracle** re-executes the skill in a fresh environment and returns only
an **opaque pass/fail bit** — no test content, no failure detail — specifically to prevent the
generator from overfitting to the surrogate's tests. On oracle failure, the surrogate must
independently escalate (harder/more diverse tests) without being told why it was wrong. Modeled
formally as a POMDP over filesystem state.

**Evidence quality.** Strong for the claims made: SkillsBench (87 tasks/~20 domains, deterministic
verifiers). CoEvoSkills reaches 71.1% pass rate (+40.5pp vs no-skill), overtakes human-curated
skills (53.5%) by round 3 and converges ~round 5 (avg. 4.1 verification cycles, 2.4 oracle
escalations/task). Ablation: removing the surrogate verifier drops pass rate by 30pp — the
co-evolutionary loop, not the generation prompt, is shown to be the primary driver.

**Notable finding.** Self-evolved skills beat human-curated skills in 9/11 domains (Finance
+56.9pp, Cybersecurity +23.2pp) and the paper frames this as **"human–machine cognitive
misalignment"**: human-written skills can *actively degrade* agent performance in some domains
because they encode reasoning patterns humans use, not patterns the LLM agent actually needs.
Skills also transfer across model families with only modest loss vs. model-matched evolution.

**Borrow.** The information-isolated verifier + opaque-bit oracle escalation is a concrete,
game-resistant mechanism for verification-gated evolution — stronger than "ask a judge model" or
even CODESKILL's rubric-based reward, because the generator literally cannot see what it's being
graded on past the surrogate stage. This is the strongest gaming-resistance mechanism in the
cluster and directly operationalizes our "promotion gate" design law.

**Reject.** Requires a deterministic, automatically-checkable ground-truth oracle per task
(SkillsBench-style). Doesn't transfer cleanly to QMA's open-ended trading-research or
UI-refinement domains where "correct" isn't a binary test suite — the mechanism needs an
adaptation (e.g., a held-out human-approved outcome standing in for the oracle bit).

**Kernel implications.** DEMANDS a kernel hook: sandboxed dual-session execution (generator +
isolated verifier), an opaque-result channel between verification tiers, and fresh-environment
re-execution for the final gate. This is more infrastructure than a single plugin call — it's a
verification *protocol* the kernel should support as a first-class primitive if QMA wants
self-authored skill evolution at all.

---

## 2605.23904 — SkillOpt: Executive Strategy for Self-Evolving Agent Skills

**Core mechanism (faithful).** Treats a **single skill document** as the trainable external
state of a frozen agent, explicitly modeled on deep-learning optimizer discipline. A separate
(optionally stronger) optimizer model runs minibatch reflection over rollout batches, proposing
bounded **add/delete/replace** edits; a **textual learning-rate budget** caps edits per step with
a cosine decay schedule; each candidate skill is evaluated on a **held-out selection split** and
accepted only if it *strictly improves* the score; rejected edits are kept in a **rejected-edit
buffer** as negative feedback for later reflection calls; an **epoch-wise slow/meta update**
consolidates durable lessons into a protected field that fast edits cannot overwrite. The
optimizer runs only offline — deployment is a static `best_skill.md` (300–2,000 tokens), zero
extra inference cost. Harness-agnostic via a thin adapter (direct chat, Codex CLI, Claude Code
CLI all consume the same file format).

**Evidence quality.** The strongest empirical matrix in the cluster: 6 benchmarks × 7 target
models × 3 harnesses = 52 cells, SkillOpt best-or-tied on all 52. GPT-5.5 gains +23.5pp (direct
chat), +24.8pp (Codex), +19.1pp (Claude Code) over no-skill; beats EvoSkill, GEPA, TextGrad,
Trace2Skill, human/one-shot-LLM skills on every cell. Transfers across model scale, across
harness (Codex-trained skill → Claude Code: +59.7pp), and to a nearby benchmark
(OlympiadBench→Omni-MATH, positive on all 3 tested model scales). Full hyperparameter ablation
(batch size, learning rate, scheduler, slow-update sample count) included.

**Borrow.** The bounded-edit + held-out-gate + rejected-edit-buffer triad is literally our
design law ("reproducibility, measured benefit, rollback path") already implemented and
validated at scale — this is the cleanest reference implementation of a promotion gate in the
cluster. Also: separating a *stronger offline optimizer* from a *cheap deployed artifact* (target-
matched optimizer still recovers 56–74% of strong-optimizer gains) is a reusable cost lever.

**Reject.** Explicitly optimizes ONE skill per domain — authors state multi-skill libraries are
future work; needs an automatic/exact-match verifier or reliable scored feedback, so it's weak
for open-ended, subjective, or hard-to-verify QMA domains without adaptation.

**Kernel implications — the sharpest challenge to a heavyweight approach in this cluster.**
SkillOpt gets state-of-the-art results with **no runtime registry, no retrieval, no routing
machinery at all** — for a bounded domain, a single trained text file swapped in via adapter
outperforms every registry/evolution-engine competitor tested (including harness-side EvoSkill).
For QMA, this suggests: before building a general skill-plugin kernel, a **"trainable skill slot"
per mind/profile** (one document, offline-trained, swapped in whole) may be the higher-leverage
first increment for any narrow, well-verified sub-task (e.g., a specific backtest-formatting or
report-writing skill) — reserve the heavier plugin-kernel machinery for genuinely multi-skill,
multi-domain minds.

---

## 2604.08377 — SkillClaw: Let Skills Evolve Collectively with Agentic Evolver

**Core mechanism (faithful).** Multi-user (OpenClaw-style) collective evolution. Each user
session is recorded as a structured causal chain (`prompt → action → feedback → ... → response`)
with lightweight metadata (skills referenced, tool errors, quality estimate). Sessions are
grouped by referenced skill `G(s)`, which the paper calls a **"natural ablation"**: comparing
outcomes across different users/contexts that invoked the *same* skill isolates whether it
actually helps, using the skill as the controlled factor. A single **agentic evolver** (an LLM
with a structured harness, not hand-coded rules) reasons jointly over successful sessions
(define invariants — must not be broken) and failed sessions (define correction targets) and
picks one of **{refine, create, skip}** per skill group, plus scans the "no-skill-used" group for
missing-but-recurring procedures. Deployment follows a strict **day/night loop**: day = collect
sessions; night = generate candidate updates, execute both old and new skill version on the same
tasks in idle user environments, and only **Accept** if the new version measurably outperforms —
producing a monotonic (never-regressing) deployed pool.

**Evidence quality.** Moderate. WildClawBench (60 tasks/6 domains), 6-day simulated deployment,
8 concurrent users, Qwen3-Max — authors explicitly self-flag this as "a small-scale test." The
shown validation log (Table 4) is itself a useful data point on conservatism: of ~4 candidate
updates proposed across 6 nights in one category, only 1 was ever Accepted — most rounds produced
either a Reject or no candidate at all.

**Borrow.** The published maintenance-prompt discipline is the most immediately reusable artifact
here: explicitly separate "is this a skill problem, an agent-runtime problem, or an environment
problem" *before* editing (never bloat a skill with agent-level or generic-robustness advice);
never delete correct environment facts (API endpoints, ports, schemas) just because the agent
failed to use them — that's an agent failure, not a skill failure; keep a per-edit versioned
evidence file (which sessions drove the change, what was preserved vs revised, open questions).
This governance pattern is usable even without any multi-user population to ablate against.

**Reject.** The core "natural ablation" mechanism assumes a multi-tenant population — it doesn't
map to QMA's single-operator context, where there's no cross-user signal to exploit. The
centralized evolution engine also assumes a trusted operator aggregating all session data, which
is a real privacy/trust cost that would need explicit design if ever adopted.

**Kernel implications.** Suggests skill promotion should require **live re-execution of old vs.
new version on matched tasks**, not just a static held-out score, before sync/deploy — a stronger
bar than a single-pass eval. Does not itself argue for or against a plugin kernel; it argues for
a day/night (batch) validate-then-sync cadence as the deployment discipline, independent of the
kernel's shape.

---

## 2608.14036 — Demystifying Agent Skills: Why They Work — Until They Don't

**Core mechanism (faithful).** Not a skill-building system — a controlled empirical study of
*why* skills help or fail. Method: run the same task under three matched arms (Raw / Workflow
Memory / Skill, built from identical source trajectories), have an LLM judge label each trajectory
against a 12-mode taxonomy (grouped into 3 categories: SC1 successful procedural anchoring, SC2
execution-layer/verification failure, SC3 invocation/applicability/boundary failure), and
validate the taxonomy against human coding (95.8% exact agreement, Cohen's κ=0.952 on 714
trajectory-label checks). Scale: 8,135 normalized trial records, 528 matched triples across
SkillsBench, Terminal-Bench 2.0, Terminal-Bench-Pro; separate retrieval-scaling experiments
varying pool size (5→100) and distractor type (random/similar/dissimilar).

**Key findings (the counterweight the cluster was assigned for).**
1. **Skills work as procedural anchors, not knowledge sources.** Mechanism-label breakdown:
   `procedural_anchor` = 65.7% of skill-success cases vs. `explicit_knowledge_injection` = 4.5%.
   Skills beat Workflow Memory by +6.06pp (bootstrap CI [+0.76, +11.36]) even though both are
   built from **identical** source trajectories — representation format, not underlying evidence
   volume, drives the gain.
2. **Skills create a new failure mode that doesn't exist without them.**
   `skill_guidance_misapplied_or_ignored` appears in 10.0% of skill-arm trajectories vs. 0.8%
   raw / 0.4% workflow-memory — roughly a 12–25× increase. Skills are sometimes followed
   mechanically, applied outside their valid context, or trusted past the point their guidance
   still holds.
3. **Skills do not fix reasoning or verification failures.** `algorithmic_logic_error` persists
   at 7.4–11.0% and `static_verification_without_runtime` at 11.7–12.5% across *all three arms* —
   skills only help with execution-layer robustness (environment setup, output format, service
   lifecycle), not with getting the underlying logic or verification right.
4. **Retrieval precision collapses with library size, but downstream success does not track it
   linearly.** As pool size grows 5→100, actual-use precision (Arm 3) falls from 29.6%→3.3%
   (random distractors) and to 3.7% under semantically similar distractors — yet downstream task
   success stays roughly flat (~32–42%) across the same range. Exact skill-ID matching is shown
   to be **neither necessary nor sufficient** for task success.

**Evidence quality.** The most methodologically rigorous paper in the cluster — largest N,
human-validated taxonomy, matched-arm controlled design, and an honest limitations section
(narrow to terminal/tool-use benchmarks; taxonomy drawn from ~3% open-coded sample). This is a
measurement paper with no system to over-claim for.

**Borrow.** The 12-mode taxonomy itself is directly reusable as an observability/diagnostic
schema for any QMA skill-registry telemetry — classify failures as anchor-miss vs.
misapplication vs. retrieval-miss rather than tracking aggregate pass rate alone. The
"identical-evidence, different-representation" experimental design is worth reusing internally
whenever we A/B a memory format change.

**Direct challenge to the Cordis-leaning kernel direction (surfaced prominently, not smoothed
over).** This paper is hard evidence against treating automated skill-evolution machinery as a
free win. Three of the other six papers in this cluster (CoEvoSkills, SkillClaw, CODESKILL) all
push toward larger, continuously-growing skill libraries built and maintained by autonomous
agentic evolvers. Demystifying shows that growth itself has a cost that doesn't show up in those
papers' own benchmarks (small, curated pools): retrieval precision falls off a cliff as the pool
scales, and skills introduce a misapplication failure mode at a rate 12–25× baseline. **A skill
registry that grows without matching investment in routing/retrieval quality and misapplication
monitoring can make an agent *worse*, not better, past some library size** — this is a real risk
to any plugin-kernel design that treats "more skills, auto-evolved" as inherently good. The
practical implication: any skill-registry kernel hook QMA builds must budget for retrieval-
precision decay as a first-class design constraint (active-pool capping per context, routing
investment proportional to library size, explicit SC3-style failure monitoring), not treat it as
an implementation detail to optimize later.

**Kernel implications.** Doesn't demand a new hook; it demands a *constraint* on any hook we do
build: skill retrieval/routing quality must be monitored and capped, and skill libraries should
not be allowed to grow unboundedly without a governance mechanism that actually validates net
benefit at the current pool size, not just at creation time.

---

## 2605.25430 — CODESKILL: Learning Self-Evolving Skills for Coding Agents

**Core mechanism (faithful).** Learns an RL policy `M_θ` that manages a skill bank
`B = {s_1,...,s_N}`: given trajectory evidence and relevant bank context, it outputs one
operation `u = (a, z)` where `a` is an operation type (generation / evolution / one of
add-merge-drop maintenance ops) and `z` is the content (a generated skill or a maintenance
decision). Skills are markdown instruction files with a title, granularity label, an explicit
`when_to_apply` trigger, and actionable rules — organized at **two granularities**: task-level
(high-level strategy for a task family, distilled from related trajectories) and event-driven
(local guidance for recurring execution signals like specific error patterns). Trained via SFT
warm-start then GRPO with a **hybrid reward**: sparse verifiable downstream task success (from a
frozen coding agent actually using the skill) + dense rubric-based LLM-judge skill-quality score.

**Evidence quality.** Solid: EnvBench, SWE-Bench Verified, Terminal-Bench 2. +9.69pp avg over
no-skill, +4.01pp over the strongest prompt-based/memory baseline (~33%/~11% relative gains).
Baselines are fair — the prompt-based comparison uses the *same* action space, prompts,
retrieval, downstream policy, and decoding settings as CODESKILL, isolating the value of the
learned (vs. fixed-heuristic) management policy specifically.

**Notable finding — directly answers Demystifying's growth-risk concern.** Tracking cumulative
maintenance decisions over time: early in a run, `add` dominates (bank is sparse, most candidates
are genuinely new); as the bank matures, `merge`/`drop` decisions become dominant and bank size
**stabilizes** rather than growing unboundedly — this happens per-benchmark, with `add` spiking
again on entering a new benchmark's task distribution. The paper demonstrates this stabilization
is a *learned, reward-optimized* behavior, not a fixed cap.

**Explicit stated limitation.** The action space is restricted to **one operation over one
candidate skill at a time** — cannot express joint multi-skill maintenance (e.g., splitting an
overly broad skill into two, or coordinating several add/merge/drop decisions together in one
step). Authors flag this as future work.

**Borrow.** Treating add/merge/drop as a first-class, auditable, *learned* policy against a
hybrid (sparse-verifiable + dense-rubric) reward is a genuine answer to "how do we keep a
growing skill library from becoming retrieval noise" — it's the mechanism Demystifying's findings
imply is necessary. The task-level vs. event-driven granularity split is also a clean, minimal
skill-type taxonomy worth adopting directly.

**Reject.** The single-operation-at-a-time constraint is real and would block bulk restructuring
QMA might eventually need. The full RL training pipeline (GRPO + rubric-judge reward) is
meaningful infrastructure investment that isn't justified until QMA has both a sizeable skill
corpus and a reliable usage-derived reward signal — their own "prompt-based" fixed-policy ablation
(same pipeline, heuristic decisions instead of learned ones) is a legitimate, much cheaper
starting point that still beats no-skill and beats raw memory baselines.

**Kernel implications.** Supports making skill-bank maintenance (add/merge/drop) an atomic,
auditable kernel-level operation on the registry from day one — but the *learned-policy* part is
an optional later upgrade, not a prerequisite. A rule-based maintenance policy is sufficient to
start and is explicitly validated as functional (if weaker) in the paper's own ablation.

---

## 2603.18743 — Memento-Skills: Let Agents Design Agents (Memento-Team; UCL / HKUST-GZ / Jilin / AI Lab Yangtze River Delta)

**Core mechanism (faithful).** A frozen-LLM continual-learning system in which the *skill library
is the only thing that changes* — no parameter updates anywhere. Formal frame: a Stateful
Reflective Decision Process, `D_SRDP = ⟨S,A,P,R,γ,M,p_LLM⟩`, an MDP augmented with a growing skill
memory `M_t = {c_i}` and an LLM decision kernel; augmenting the state to `x_t := (s_t, M_t)`
restores the Markov property even while the library mutates. A skill `c_i` is a **skill folder**:
a declarative spec (`SKILL.md`) plus prompts plus executable code — not a trajectory log. The
runtime loop is **Observe → Read → Act → Feedback → Write**:

- **Read** = a *behaviour-aligned skill router* picks one skill conditioned on the query plus an
  accumulated "tip memory"; if nothing matches and `CREATE_ON_MISS` is enabled, a new skill is
  synthesised on the spot.
- **Write** = (a) a utility update on the invoked skill (running empirical success rate);
  (b) a generic tip appended to tip memory; (c) **skill-level failure attribution** — an LLM
  *target selector* reads the full trace and the judge's rationale and names the **single skill
  most responsible** for the failure; (d) a *skill rewriter* proposes targeted edits that add
  guardrails or alternative strategies for the observed failure mode "while preserving the skill's
  generality"; (e) **utility-threshold escalation** — when a skill's running utility drops below δ
  (with `n ≥ n_min` samples), in-place patching is declared insufficient and the system escalates
  from *patch* to **discover**: restructure the folder with a fundamentally different approach, or
  synthesise an entirely new skill; (f) **a unit-test gate**: every mutation generates a synthetic
  test case, executes it through the updated skill, scores it with the judge, and **rolls back on
  failure**; (g) up to `K` feedback-retry rounds.

**The router — the mechanism this cluster was missing.** The paper states the problem in the
terms Demystifying measures it in: purely semantic routers (BM25, or a Qwen3 embedding model)
"primarily capture semantic similarity between the user goal and skill text rather than
*behavioural* similarity — i.e. whether executing a skill would produce the desired trajectory and
outcome," and in the authors' own framing, "in a library of 8,000 skills, semantic overlap is just
noise." (Note that line is spoken by a character in the paper's dialogue framing, not a measured
result — see evidence quality.) Their fix is **single-step offline RL on top of an embedding
model**, deliberately *not* end-to-end RL, because "we have 8,000 skills but only a few hundred
real-world tasks — the exploration space is a desert." Concretely: crawl ~5k public skills
(GitHub, stars > 500, SHA-256 description dedup), sample ~3k as seeds, use an LLM that sees only
the skill *name and description* to synthesise realistic routing goals, then a second LLM judge
that *does* read the full skill file filters them — yielding **positives** and **hard negatives**
("same domain and terminology, but the target skill is not the right tool," with an explicit
instruction to avoid giveaway cues). Train with multi-positive InfoNCE. The learned score is then
read as a soft Q-function over a one-step MDP (state = goal, action = skill, horizon 1), giving a
Boltzmann routing policy `π_θ(d|q) ∝ exp(Q_θ(q,d)/τ)` which is the maximiser of a KL-regularised
objective against a uniform prior — so τ is literally an exploration dial, and InfoNCE is
single-step offline policy improvement for routing.

**Evidence quality — moderate, and thinner than the cluster's best.** Numbers that exist:
Recall@1 over **140 synthetic routing queries** rises 0.32 (BM25) → 0.54 (Qwen3-Embedding-0.6B) →
**0.60** (their Memento-Qwen), and Recall@10 to 0.90. End-to-end on real trajectories: route hit
rate 0.29 → 0.53 → **0.58**; judge success rate 0.50 → 0.79 → **0.80**. System-level: GAIA (165
validation questions split 100 train / 65 test) 52.3% → **66.0%** over the Read-Write ablation
(+13.7pp); HLE (788 train / 342 test) 17.9% → **38.7%** (+20.8pp, the "116.2% relative" headline);
training-time GAIA success climbs 65.1% → 91.6% across three retries; HLE training 30.8% (R0) →
54.5% (R3). Library growth from 5 atomic seed skills: **41 skills after GAIA, 235 after HLE**.
Caveats that matter: a **single backbone** (Gemini-3.1-Flash) throughout; a **single ablation
baseline** (Read-Write with all skill optimisation disabled) — no comparison against SkillOpt,
CODESKILL, GEPA or any other evolver in this cluster; the router eval is 140 *synthetic* queries,
not held-out real user traffic; the paper is written as a three-character stage dialogue with a
"Memento-Team" author block, and several of its most quotable lines (including the 8,000-skill
one) are dialogue, not results; and the authors explicitly defer the third evaluation axis —
**"sandbox safety — whether it solves the task without breaking anything else — requires a proper
isolation harness. Future work."**

**Notable finding, honestly stated.** The **transfer result cuts against unbounded library
growth**: on GAIA, "most skills optimised during training were never triggered during testing,
because no sufficiently similar test question existed." Skill transfer worked on HLE only because
HLE has a structured subject taxonomy. Their own conclusion — "domain-aligned skill libraries are
the key enabler of cross-task generalisation" — is an argument for **scoping libraries by domain**,
not for growing one big pool. That is convergent with Demystifying's pool-size warning arrived at
from the opposite direction.

**Borrow.**
1. **Behaviour-aligned routing trained by one-step offline RL** — the concrete answer to
   "retrieval precision collapses with library size." Crucially, the expensive part is *data
   synthesis, not RL*: an LLM generates positives and hard negatives from skill metadata, a second
   LLM with full-file access filters them, and a contrastive fine-tune of a **0.6B** embedding
   model does the rest. That is cheap enough for QMA to actually run, and it is offline —
   no inference-time cost, no training the mind itself.
2. **Utility-threshold escalation `patch → discover`.** A running Beta-style success rate per
   skill with a threshold δ and a minimum-sample floor `n_min`, where crossing the floor stops
   patching and forces a rebuild. This is the missing *decision rule* between MSCE's reliability
   lifecycle and CODESKILL's add/merge/drop: it says *when* to stop editing and start over.
3. **Skill-level failure attribution before any edit** — name the single responsible skill from
   the trace + judge rationale first. Same discipline as SkillClaw's maintenance prompt, but
   mechanised as a selector step rather than left to prose guidance.
4. **Unit-test gate with rollback on every mutation**, including LLM-generated skills. Weaker
   than CoEvoSkills' opaque-bit oracle but far cheaper, and it is the minimum bar.
5. **Hard negatives are the product.** "Relevant but useless for THIS skill" is precisely the
   distractor class Demystifying shows destroys precision at scale, and it is the class semantic
   similarity cannot separate. Any QMA skill-retrieval eval set must contain them by construction.

**Reject.**
- The **`CREATE_ON_MISS` default**. Creating a skill whenever the router misses is exactly the
  unbounded-growth policy Demystifying warns about and Memento's own GAIA transfer failure
  demonstrates the cost of. Adopt the router; make creation-on-miss opt-in and rate-limited.
- The **convergence claim as reassurance**. "The memory coverage radius `r_M` shrinks, so the
  value gap converges" is a bound inherited from Memento 2, not something measured here;
  the observed diminishing-returns curve is consistent with it but does not test it.
- **The router's evidence base as a proxy for QMA's.** The router is trained on a ~5k public-skill
  catalogue but the deployed libraries were 41 and 235 skills. The paper never measures precision
  as a function of pool size, so it does **not** refute Demystifying's 29.6% → 3.3% collapse — it
  proposes a mechanism that plausibly attacks it and does not test it at that scale. Treat it as a
  design candidate, not as a settled answer.
- The **single-backbone, single-baseline evaluation** means none of the system-level percentages
  should be compared against SkillOpt's or CODESKILL's numbers.

**Kernel implications.** Mostly **does not demand a kernel hook** — the router is an offline-trained
embedding artifact and a top-k call, the escalation rule is a threshold on a counter, the test gate
is a subprocess. Three things do touch the kernel: (i) the **per-skill utility counter must be a
first-class registry field** (`n_success`, `n_trials`, running utility) rather than telemetry, since
the escalation rule reads it synchronously at write time — this is the same field MSCE's η needs,
so one field serves both; (ii) **rollback of a skill mutation must be atomic with the test gate**,
which is the registry's `add/merge/drop` transaction from CODESKILL, not a new mechanism; (iii) the
router is a **swappable component with a stable contract** (`route(goal, library) → skill | ∅`),
which argues for the kernel standardising the *interface* and owning none of the ranking. Net: this
paper adds a mechanism, not kernel surface — mildly **anti**-kernel in the same direction as
SkillOpt.

---

## Cluster verdict

**What a skill IS (converged across all 7 papers):** a bounded, reusable, inspectable
procedural artifact — `(instruction document, optional auxiliary resources, trigger condition)`
— distinct from a raw tool (which exposes capability, not procedure) and distinct from raw
episodic/workflow memory (which preserves noisy trace detail the skill deliberately discards).
Every paper that measured it found skills win by **compressing into stable procedure**, not by
injecting facts. Memento-Skills is the one dissent on packaging: its unit is a *skill folder* of
spec + prompts + **executable code**, so the `R` slot is load-bearing rather than optional, and
CODESKILL/SkillClaw ship multi-file packages too. Read the survey's `(M, R, C)` as the schema and
"resources may include code" as the majority position, not a footnote.

**Top borrowings for QMA's kernel:**
1. **Verification-gated promotion, concretely implemented twice** — SkillOpt's
   bounded-edit + held-out-gate + rejected-edit-buffer (simplest, best-validated) and
   CoEvoSkills' isolated-verifier + opaque-bit-oracle (strongest anti-gaming, needs deterministic
   verifiers). Adopt SkillOpt's pattern as the default promotion gate; reserve CoEvoSkills'
   heavier dual-session protocol for domains with automatic ground-truth checks.
2. **Skill-bank maintenance (add/merge/drop) as an atomic, auditable kernel operation**
   (CODESKILL), starting rule-based, upgradeable to learned later.
3. **A diagnostic taxonomy for skill telemetry** (Demystifying's 12 modes / 3 categories) —
   instrument the registry to detect misapplication and retrieval-precision decay specifically,
   not just track aggregate success.
4. **Skill-vs-agent-vs-environment failure attribution discipline before any edit**
   (SkillClaw's maintenance prompt) — cheap, immediately adoptable governance text.
5. **A single trained skill-document as a lighter-weight alternative to a full registry**
   (SkillOpt) for any narrow, well-verified, single-domain task inside a mind — don't reach for
   the plugin kernel until the task genuinely needs multiple, composable, retrieved skills.
6. **A behaviour-aligned router, not a semantic one** (Memento-Skills) — the cluster's only
   *mechanism* for the retrieval-precision problem, and cheap: LLM-synthesised positives and hard
   negatives from skill metadata, judge-filtered, multi-positive InfoNCE fine-tune of a 0.6B
   embedding model, read as a one-step Q-function. Offline, so zero inference-time cost. Measured
   lift over a stock embedding router is modest (Recall@1 0.54 → 0.60, route hit 0.53 → 0.58,
   judge success 0.79 → 0.80) and over BM25 large — so the honest claim is "lexical matching is a
   bad proxy for behavioural utility," not "this solves routing."
7. **Utility-threshold escalation `patch → discover` with a minimum-sample floor**
   (Memento-Skills) — the decision rule for when to stop patching a skill and rebuild it, which
   MSCE's reliability lifecycle and CODESKILL's add/merge/drop both leave implicit.

**Direct challenge to our Cordis-leaning kernel direction:** Demystifying Agent Skills is real
evidence that automated, ever-growing skill-evolution machinery (the shared assumption behind
CoEvoSkills, SkillClaw, and to a lesser extent CODESKILL) has a cost curve the other three papers'
own benchmarks are too small to expose: retrieval precision collapses with library size
independent of downstream success, and skills add a misapplication failure mode absent from raw
execution. This does **not** invalidate a skill-registry kernel hook — every paper, including
the survey, still treats skills as a distinct governed artifact type worth a registry — but it
does mean the kernel's skill-registry contract must treat **retrieval-precision decay and
misapplication rate as first-class, monitored constraints**, not an afterthought to optimize once
the library is already large. The kernel-worthy design law to add: *skill promotion must validate
net benefit at the agent's current active pool size, not just at creation time against a small
benchmark.*

**Where the cluster now stands on that challenge (revised after adding Memento-Skills).** The
first version of this file left Demystifying's finding standing with only a telemetry
recommendation and a pool cap against it — a diagnosis with no treatment. Memento-Skills supplies
the treatment: routing trained on **execution outcome** rather than text similarity, plus a
`patch → discover` escalation rule that prevents the library from accumulating skills that are
individually dying. Two honest limits on that relief. First, Memento never measures precision as a
function of pool size, so it **does not refute** the 29.6% → 3.3% collapse — it proposes a
plausible attack on it. Second, and pointing the same way as Demystifying: Memento's own GAIA
result shows most trained skills were *never triggered* at test time because no similar question
existed, and its HLE result works only because HLE has a subject taxonomy. Read together, the two
papers say the same thing from opposite ends — **libraries should be scoped per domain and routed
on behaviour, not grown globally and retrieved on similarity.** That is a design law for QMA's
registry, and it is still a constraint on a kernel hook rather than a demand for one.
