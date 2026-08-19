# Cluster C2: Reversibility & Transactional Control

Papers: (1) Shepherd: Enabling Programmable Meta-Agents via Reversible Agentic
Execution Traces (arXiv:2605.10913, Yu/Chong/Nandi/Soylu/Sun/Manning/Shi —
Stanford/Berkeley) + github.com/shepherd-agents/shepherd. (2) Agentic
Transaction: Towards ACID-Compliant Agent Systems (arXiv:2608.13900, Sun/Wang/Li
— Tsinghua DB Group). Both located and fully read (paper text + repo).
Transcript (chat-harnes.txt) consulted only for why these were flagged: user's
prior session pointed at Shepherd as "the control mechanism... retain, inspect,
fork, replay, select, apply, or discard agent-produced artifacts" for a
quant-trading harness — that's a pointer, not a verdict; judged independently
below.

---

## Paper 1 — Shepherd (2605.10913)

**Core mechanism (faithful).** Four FP-grounded primitives: **Task** (a typed
Python function = an agent, substitutable/composable, so meta-agents can hold
and pass agents as values); **Effect** (a typed record of one action; every
action emits a separate *intent* effect then an *outcome* effect, so a
meta-agent can read the intent and veto before the outcome materializes);
**Scope** (region-scoped effect handler — `emit/fork/merge/discard`; `fork()`
does an atomic copy-on-write snapshot of *both* the worker's filesystem/process
state *and* its effect stream); **Trace** (a persistent Git-like commit graph —
every past commit is reachable/replayable byte-exactly, and sibling branches
share storage by content hash). Effects carry a **reversibility tier**:
reversible (fs writes, sandbox state — rolled back natively by the scope),
compensable (DB writes — rolled back via user-supplied compensation handlers),
irreversible (model calls, emails — materialize on emission, only audit-logged,
never undone). This tiering, not a blanket "everything is reversible" claim, is
the actual mechanism.

**Evidence quality.** Real systems benchmark: fork/revert costs 134–143ms (2–3%
of one agent turn), ~5× faster than `docker commit`, ~95% KV-cache hit rate on
replay from K=2 onward — measured, not claimed. Three case studies are
explicitly framed by the authors as **"proof of existence," not benchmarked
optimality**: runtime supervisor raises CooperBench joint pass rate 28.8%→54.7%;
counterfactual replay optimizer (CRO) beats MetaHarness on 4/5 datasets at up to
58% lower wall-clock; meta-agent-guided Tree-GRPO lifts Terminal-Bench 2.0 by
5.2 pts over flat GRPO. The paper is unusually honest about scope: it ships a
Lean-mechanized "core," but the **non-claims list is long and load-bearing** —
the proof envelope does *not* verify arbitrary Python control flow, provider SDK
behavior, model outputs, prompt-cache state, shell commands, filesystem
mutation correctness, Docker/sandbox implementations, scheduling, cancellation,
retries, recovery, or multi-branch replay. Only a narrow effect-trace fragment
(direct abort, no resume, deterministic two-phase handlers) is actually
theorem-backed. **Treat "reversibility" as an architectural/empirical property,
not a proven one** — the formal-verification framing is much thinner than the
paper's presentation suggests.

**Implementation reality (github.com/shepherd-agents/shepherd, checked
directly).** Early alpha (self-labeled), MIT license, PyPI package
`shepherd-ai`, Python 3.11+, ~2.3k stars, weekly commit activity, API still
churning (0.1→0.3.0 in ~6 weeks with breaking changes each time).
**macOS/Linux only — Windows unsupported** (enforcement would be
advisory-only), must use WSL. Grants are enforced at the **native syscall jail
layer** (macOS Seatbelt; Linux Landlock, in a privileged container) — this is
real OS-level sandboxing, not a policy-file fiction. Settlement verbs are
`select / apply / release / discard` on a `run`; a task's body can literally
*be* a sandboxed Claude Code agent whose output comes back as a reviewable,
un-applied proposal. Commit messages show heavy internal jargon churn ("Beat-0
safety bar," "fabrication fence," "the fence/refusal/W0 sentinels") — a signal
of real complexity and an actively-renegotiated internal design, consistent
with genuinely hard systems software, not just marketing gloss.

**What QMA should borrow.** (1) The **proposal lifecycle**
(sandbox → retained/reviewable output → select/apply/release/discard) maps
directly onto "minds run in sandboxes under supervision" — don't reinvent this
vocabulary, adopt it. (2) **Intent/outcome effect splitting** — letting a
supervisor read an about-to-happen action and veto before it lands — is the
cleanest mechanism seen in this cluster for a human/meta-agent kill-switch on
irreversible mind actions. (3) The **three-tier reversibility model**
(reversible / compensable / irreversible) is a clean, adoptable taxonomy for
classifying what a mind's sandboxed/computer actions can do and what recovery
contract each tier gets — this belongs in the sandbox abstraction design
directly. (4) Copy-on-write scope forking as the mechanism for cheap parallel
exploration (useful for any "try N approaches, keep the best" mind pattern).

**What to reject and why.** (1) Do not import the Lean-proof narrative as a
selling point for QMA's own docs — it covers a sliver of the real system and
the paper itself says so; overselling it would misrepresent our own evidence
quality later. (2) Don't treat Shepherd (the library) as a dependency to build
on directly — alpha, breaking API, no Windows, heavy Claude-CLI coupling in the
quickstart path. Borrow the *pattern*, not the package. (3) The paper's headline
numbers are single-policy, single-benchmark "existence proofs," explicitly not
compared against simpler alternatives by the authors — don't cite the CooperBench
28.8%→54.7% jump as if it generalizes.

**Kernel implications.** This one **does demand a kernel-level hook**, not a
convenience wrapper. Atomic fork of agent+environment state requires
overlay-filesystem virtualization and native sandbox checkpoint facilities —
that's inherently privileged, platform-specific plumbing (Seatbelt/Landlock),
exactly the kind of thing a provider-unbiased sandbox/computer abstraction in a
Cordis-style kernel plugin should own, because no amount of application-level
scaffolding can fake copy-on-write process+fs forking. This is a point of
support for the plugin-kernel direction, specifically for the sandbox/computer
plugin surface — but note it also argues for scoping that plugin narrowly (fork/
merge/discard/emit + tiered reversibility) rather than trying to mechanize the
whole effect-trace semantics, since even Shepherd's own authors only formally
cover a fragment of it.

---

## Paper 2 — Agentic Transaction / ACID-Agent (2608.13900)

**Core mechanism (faithful).** Reinterprets the four classical ACID properties
as **semantic**, not literal, guarantees for LLM agent execution (explicitly:
"the proposed semantics constrain committed effects rather than requiring
deterministic execution traces" — they are *not* claiming database-grade ACID).
An "agentic transaction" τ = ⟨r₁,...,rₙ⟩ is a bounded sequence of steps
rᵢ=(cᵢ,aᵢ,fᵢ) (context, action, feedback). Four techniques instantiate the four
letters for a concrete **data agent**: **Atomicity** — model each
exploration→execution→validation cycle as a transaction unit with
commit-or-retry semantics; failed units are discarded from the workspace and
from context before they can contaminate later steps. **Consistency** — a
**confidence-divergence validator**: a small local model (Qwen3-0.6B, chosen
because API models don't expose token logprobs) scores whether a generated
decision/code span is actually grounded in the exploration evidence; low
divergence between "with evidence" and "without evidence" confidence signals an
ungrounded, likely-hallucinated step and triggers a retry. **Isolation** —
agent-level (independent / collaborative-git-like / competitive-sibling
sub-agent strategies) plus operation-level (versioned workspaces, snapshot
execution) so failed retries never pollute shared memory. **Durability** — an
append-only workspace plus an LLM-managed evolving knowledge-graph memory for
recovery/audit, replacing naive step-wise summarization.

**Evidence quality.** Concrete, moderately convincing: evaluated on
KramaBench (104 tasks, 1,700 files, 24 sources, 6 domains). ACID-Agent beats
Claude Code by **10.6%** on the same (smaller) backbone, and even beats Claude
Code running the *larger* GLM-5.2 backbone — a real result, not just
self-comparison. Variance across 3 runs drops sharply (±18.6 vs Claude Code's
±30.9), i.e., the transactional scaffolding measurably improves consistency,
not just mean score. The ablation is the most useful number in the paper:
removing **failed-step isolation alone** drops the score by **11.7%** —
concrete evidence that letting failed intermediate state leak into context is
a real, quantifiable failure mode, and that walling it off is worth the
overhead. Caveats: authors call these "preliminary"; the system is scoped to
one domain (data-science agents over files/DBs); the Section 4 "Open Problems"
admits most of general-purpose ACID-agent design (skill ecosystems, isolation
for shared context/tools across arbitrary multi-agent systems, durable memory
as real infrastructure) is unsolved future work, not delivered here. This is a
narrower, more honest paper than its title suggests — it demonstrates the value
of the *pattern* in one domain, not a general-purpose ACID substrate.

**What QMA should borrow.** (1) **Confidence-divergence validation as a cheap
consistency gate** — using a small, fast local model to check "is this
decision actually grounded in evidence" before committing a step is a concrete
recipe QMA could specify at the harness-loop level, independent of any kernel
work. (2) The **ablation finding itself** — isolating failed attempts from
context/memory is worth ~12% by itself — is strong independent justification
for a "failed work never touches persistent context" invariant regardless of
which reversibility substrate underlies it. (3) The three sub-agent isolation
modes (independent/collaborative/competitive) are a useful, minimal vocabulary
for multi-mind coordination policies.

**What to reject and why.** Don't adopt the "ACID" branding literally in QMA
docs — the paper itself concedes it's a semantic reinterpretation with weaker
guarantees than the database term implies, and using it verbatim risks
over-promising the same way the paper's title slightly over-promises relative
to its single-domain data-agent scope. Don't treat this as validated for
general (non-data-science) mind workloads — it wasn't tested there.

**Kernel implications — this is the important contrast with Shepherd.**
ACID-Agent's guarantees are achieved **entirely at the orchestration/harness
level**: retry loops, an append-only *logical* workspace, and a confidence
classifier — **no OS-level sandboxing, no copy-on-write filesystem forking, no
kernel hooks at all**. It "rolls back" by simply not propagating a failed
step's context/memory forward, not by undoing real-world side effects. This is
a genuine, concrete counter-data-point to a heavy Cordis-plugin-kernel
architecture: it shows that a large share of what people mean by "transactional
agent reliability" (consistency, isolation-of-failure, durability of good
state) is obtainable as a **lightweight scaffolding pattern bolted onto an
ordinary agent loop**, with real measured benefit (10.6% task score, 11.7%
isolation ablation), and does not by itself demand a kernel plugin. It suggests
QMA should **separate two different problems that Shepherd's framing tends to
conflate**: (a) undoing real-world/sandbox side effects (genuinely needs kernel-
level fork/rollback — Shepherd's territory), vs. (b) keeping bad reasoning and
failed attempts out of a mind's context/memory (a pure harness-level
discipline, no kernel needed — ACID-Agent's territory). Building the kernel
plugin to solve (a) does not automatically get you (b), and (b) alone captures
much of the measured benefit here.

---

## Related work worth flagging (from Shepherd's §2, not separately read)

Both papers sit inside a **crowded, unsettled field** of transactional/
reversible agent designs at different stack layers: AgentGit (VCS as
cooperative LangGraph tools), BranchFS (kernel `branch()` syscall for fs
isolation), AgentSPEX (checkpointing embedded in a DSL), Atomix/ATCC/SagaLLM/
Mnemosyne (transaction-processing framings closer to paper 2). This is not a
solved-problem area with one obviously correct design point — worth naming
explicitly rather than presenting either paper's approach as the consensus
answer.

---

## Cluster verdict

**Top borrowings:** (1) Shepherd's proposal lifecycle vocabulary
(sandbox→proposal→select/apply/release/discard) and its intent/outcome effect
split for pre-materialization vetoes — both fit "minds run in sandboxes under
Shepherd-style supervision" almost directly. (2) Shepherd's three-tier
reversibility taxonomy (reversible/compensable/irreversible) as the
organizing model for the sandbox/computer plugin's action contract. (3)
ACID-Agent's confidence-divergence retry gate and its proven "isolate failed
attempts from context" discipline as harness-level (non-kernel) additions.

**Direct challenge to our Cordis-leaning kernel direction:** Paper 2 is real
evidence that a meaningful fraction of "transactional agent reliability" is
achievable with **no kernel plugin at all** — pure harness/orchestration
scaffolding, measured at +10.6% task score and +11.7% from isolation alone in
one domain. This means the "minds run in sandboxes under Shepherd-style
supervision" premise should be split in the architecture doc: genuine
side-effect reversibility (undoing real filesystem/tool actions) is a hard
systems problem that legitimately warrants kernel-level hooks (Shepherd
confirms this needs OS-level sandbox primitives, not app-level tricks) — but
context/memory isolation of failed attempts, which is where a chunk of the
measured reliability gain actually comes from, does not need the kernel at
all and could ship as a lightweight harness pattern well before any
Cordis-plugin sandbox substrate is built. Don't let the kernel-hook case for
(a) justify routing (b) through the kernel too. Also worth registering:
Shepherd's own formal-verification claims are much narrower than its
presentation implies (explicit non-claims list covers scheduling, retries,
recovery, provider behavior, arbitrary Python) — if QMA cites "proof-backed
reversibility" anywhere down the line, cite it at Shepherd's actual coverage
level, not its headline framing.
