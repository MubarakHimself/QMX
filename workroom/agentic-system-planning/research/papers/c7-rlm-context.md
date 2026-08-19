# C7 — Recursive Language Models & Context-as-Environment

**Cluster brief:** Locate and read the RLM paper; sweep its citation neighbourhood for successors and
critiques; answer whether RLM is an inference-loop plugin on a Cordis-style kernel or demands
kernel-level support.

**Stance:** Every paper judged on its own merits. The AlphaXiv transcript
(`C:/Users/Mubarak/Desktop/chat-harnes.txt`) was consulted and contains **no mention of RLM at all** —
it is a harness-engineering/quant-trading reading list. RLM came from Mubarak's own flag, not from the
transcript. So there is no transcript framing to correct for here; but there *is* a strong pro-RLM
narrative in the field ("the paradigm of 2026" — Prime Intellect), and that narrative is what this
document pushes back on. **The contradicting evidence is substantial and is placed first in the
verdict, not smoothed over.**

---

## Coverage ledger (no silent caps)

**Read in depth (full text or targeted full-text passages):**

| # | ID | Title |
|---|---|---|
| 1 | `arXiv:2512.24601v3` | Recursive Language Models — Zhang, Kraska, Khattab (MIT CSAIL) |
| 2 | `arXiv:2603.20432` | Coding Agents are Effective Long-Context Processors — Cao, Yin, Dhingra, Zhou (Duke) |
| 3 | `arXiv:2606.13643` | Recursive Agent Harnesses — Lumer, Sen, Paul, Subbiah (PwC US) |
| 4 | `arXiv:2605.04050` | LCM: Lossless Context Management — Ehrlich, Blackman (Voltropy PBC) |
| 5 | `arXiv:2603.02615` | Think, But Don't Overthink: Reproducing RLMs — Wang (CUHK) |
| 6 | `arXiv:2603.20105` | The Y-Combinator for LLMs: λ-RLM — Roy, Tutunov, Ji, Zimmer, Bou-Ammar (IIT Delhi / Huawei Noah's Ark / UCL) |
| 7 | `arXiv:2603.02112` | Recursive Models for Long-Horizon Reasoning — Yang, Srebro, Li (ICML) |
| 8 | `arXiv:2603.15653` | RLMs Meet Uncertainty: Self-Reflective Program Search (SRLM) — Alizadeh, Shojaee, Cho, Farajtabar (Apple) |
| 9 | `arXiv:2608.05124` | Chained Recursive Language Models for Multi-Iteration Reasoning |
| 10 | `arXiv:2602.16520` | RLMs for Jailbreak Detection (RLM-JB) — Shavit (Silverfort) |
| 11 | `arXiv:2602.01848` | ROMA: Recursive Open Meta-Agent Framework |
| 12 | `github.com/alexzhang13/rlm` | Reference implementation (MIT OASYS lab) — README/API read in full |

**Located, abstract-level only — deliberately not read in depth, reason given:**

- `arXiv:2607.02509` **ReContext** — recursive evidence replay; training-free relevance-signal harness.
  *Reason: same family as SRLM (program/evidence selection), no distinct kernel implication.*
- `arXiv:2608.03391` **TimeRLM** — RLM for time-series anomaly localisation. *Domain transfer, not architecture.*
- `arXiv:2603.17948` **VideoAtlas** — recursive zoom over a hierarchical video grid. *Domain transfer.*
- `doi:10.64898/2026.01.24.26344761` **C-RLM** — schema-enforced recursive clinical synthesis.
  *Same "constrain the free-form REPL" thesis as λ-RLM/LCM, weaker venue; no new kernel claim.*
- `arXiv:2602.22603` **SideQuest** (KV-cache management) and `arXiv:2601.23211`
  (multi-agent principal–agent) — adjacent, sub-kernel / incentive layer respectively.

**Nothing in the assigned cluster was unreachable.** All PDFs and HTML resolved.

---

## 1. Recursive Language Models — `arXiv:2512.24601v3` (MIT CSAIL)

### Core mechanism (faithful)

Given a base model `M` with max context `K` and an arbitrary-length prompt string `P` (where `|P| >> K`):

1. The scaffold initialises a **persistent REPL environment** with `P` bound to a variable named
   `context`, plus a function `llm_query` (and at depth>1, `rlm_query`) available as a module.
2. The **root** model is invoked with *only constant-size metadata* about `P` — its length, a short
   prefix, chunk lengths, and instructions for how to access it. `P` itself never enters the root's
   context window.
3. The root emits Python code. The REPL executes it, mutates persistent state, and returns `stdout`.
   **Only constant-size metadata about `stdout`** (short prefix + length) is appended to the root's
   history. This truncation is deliberate: it forces the model to use variables and sub-calls rather
   than pouring text into its own window.
4. Loop terminates when the root sets a `Final` variable in the REPL — surfaced to the model as
   `FINAL(answer)` / `FINAL_VAR(variable_name)` tags.

The paper names three design choices as the load-bearing ones, contrasted against a strawman
"Algorithm 2":

- **Flaw #1 avoided:** the prompt is a *symbolic handle*, not context-window content.
- **Flaw #2 avoided:** the answer can be assembled in a REPL variable, so **output length is not
  bounded by `M`'s output window**.
- **Flaw #3 avoided — the one they call most important:** *symbolic recursion*. Code inside the
  environment can invoke `M` on programmatically constructed transformations of `P`, inside arbitrary
  loops. Prior sub-agent delegation (Anthropic subagents, THREAD, Context Folding) can only
  *verbalise* a handful of sub-calls autoregressively; RLM can launch Ω(|P|) or Ω(|P|²) of them from a
  three-line loop.

`RLM(model, depth=N)`: depth 0 = REPL with no sub-calls; depth 1 = sub-calls are plain LLM calls;
depth >1 = sub-calls are themselves RLMs. GPT-5 root / GPT-5-mini sub-calls in the headline runs.

### Evidence quality — **good, with three real soft spots**

Strengths: four tasks of deliberately different complexity classes (S-NIAH ≈ constant, OOLONG ≈ linear,
OOLONG-Pairs ≈ quadratic, plus BrowseComp-Plus and LongBench-v2 CodeQA); two model families (GPT-5,
Qwen3-Coder-480B); API cost reported alongside every score; depth ablated 0→3; an ablation on
in-context decomposition examples; a syntax-error analysis correlating errors with failures; and both
SFT distillation (RLM-Qwen3-8B, 1,000 filtered trajectories, 48 H100-hours) and RLVR
(RLM-Qwen3-4B on MRCRv2, showing 64K→1M length generalisation).

Soft spots:

1. **OOLONG is evaluated on the `trec_coarse` split only.** Cao et al. (`2603.20432`) flag this
   explicitly and further note GPT-5's Oolong numbers in the RLM paper come from datapoints under
   200K tokens. On the full Oolong-Synthetic set, RLM scores **64.38%** — below an off-the-shelf
   coding agent (see §2).
2. **No error bars on scores.** Cost is reported ±σ and the σ is often larger than the mean
   (`$1.10 ± $3.25` on OOLONG at depth 2) — i.e. the cost distribution is heavy-tailed with runaway
   trajectories. Score variance is not reported at all.
3. **All sub-LM calls are blocking/sequential in their implementation**, so the reported runtimes
   characterise the implementation, not the paradigm. The authors say so.

### Numbers that matter (Table 1, GPT-5 root)

| Method | CodeQA | BrowseComp+ (1K, 6–11M tok) | OOLONG | OOLONG-Pairs |
|---|---|---|---|---|
| Base GPT-5 | 24.0* | 0.0* | 44.0 | **0.1** |
| Compaction agent | 58.0 | 70.5 | 46.0 | 0.1 |
| **OpenCode + context offloading** | 64.0 | **94.0** | 52.0 | 4.8 |
| RLM depth=0 (REPL, no sub-calls) | 58.0 | 88.0 | 36.0 | 43.9 |
| RLM depth=1 | 62.0 | 91.3 | 56.0 | 58.0 |
| RLM depth=2 | **66.0** | 92.0 | 56.5 | 65.5 |
| RLM depth=3 | 58.0 | 92.0 | **58.0** | **76.0** |

Read this honestly:

- On **BrowseComp-Plus, a plain coding agent with context offloading (94.0) beats every RLM
  configuration (max 92.0)**. This is in the RLM paper's own table.
- On **CodeQA the trend is non-monotonic** — depth 3 (58.0) is worse than depth 0 (58.0) and much
  worse than depth 2 (66.0).
- On **Qwen3-Coder, depth=0 beats every sub-calling variant on CodeQA (66.0 vs 56.0/54.0)** and
  depth=2 *collapses* OOLONG from 48.0 → 26.0. The authors attribute this to syntax errors
  propagating into sub-calls.
- **OOLONG-Pairs is the one place RLM is uniquely, dramatically better** (0.1 → 76.0). That task
  requires Ω(n²) pairwise semantic work with an answer longer than the output window. That is the
  *actual* shape of problem RLM solves.

### The result the RLM paper buries — general reasoning regressions

A second table (GPT-5.2 backbone, general reasoning, not long context):

| Model | Overall | MATH | CHEM | CS | LOGIC | CHESS |
|---|---|---|---|---|---|---|
| GPT-5.2 base | 38.7 | **26.0** | 37.0 | **40.4** | 53.6 | 36.6 |
| RLM(GPT-5.2, depth=1) | 50.6 | **5.6** | 50.0 | **11.0** | 86.7 | 93.0 |
| + decomposition hints | 65.6 | 32.0 | 52.0 | 46.0 | 99.0 | 99.0 |

**Wrapping a model in RLM cut MATH from 26.0 to 5.6 and CS from 40.4 to 11.0** — a 4.6× and 3.7×
degradation — and only recovered with hand-written decomposition hints. This is the strongest
argument in the paper against RLM as a default loop, and it is not discussed in the abstract.

### Authors' own negative results (Appendix B) — read these as engineering requirements

- **Prompts don't transfer across models.** The GPT-5 RLM system prompt applied to Qwen3-Coder caused
  it to "perform a subcall on everything, leading to thousands of LM subcalls for basic tasks."
  A single added sentence fixed it. *The scaffold is prompt-fragile per backbone.*
- **Models without strong coding ability fail as RLMs.** Qwen3-8B could not operate the REPL.
- **Thinking models with small output budgets fail** — reasoning tokens exhaust the per-call output cap.
- **Termination signalling is brittle.** In the distillation corpus, **16% of root turns misused
  `FINAL()` and 13% misused `FINAL_VAR()`**; they had to add a programmatic patcher. The authors say
  this "should be avoided altogether in the future."
- **Blocking sub-calls make it slow.**
- Limitations section names **"exploding sub-call costs"** as an unsolved side-effect, and says
  "the best mechanisms for implementing **guardrails** for RLMs remain highly underexplored."

### What QMA should borrow

- **B1 — Context as a symbolic handle, not prompt content.** This is the durable idea and it survives
  every critique in this cluster. A mind's inputs should be addressed by reference (`ContextRef`:
  id + type + length + chunk boundaries + accessor) and materialised only by explicit slicing.
- **B2 — Truncate observations aggressively and deliberately.** Feeding back only a prefix+length of
  stdout is what *forces* good behaviour. It's a constraint that produces capability, not a limitation.
- **B3 — Answers assembled in environment variables, not in the output stream.** Decouples deliverable
  size from model output caps. Directly relevant to a research mind producing a long report.
- **B4 — Sub-calls as *functions in code*, not as verbalised delegations.** The Ω(n) vs O(few)
  expressivity gap between "write a loop that calls the model" and "emit a tool-call per delegation"
  is real and is confirmed independently by RAH (§3).
- **B5 — In-context decomposition exemplars are worth a lot,** even when unrelated to the task. Cheap
  win: ship a small library of decomposition patterns as a scoped constant per mind kind.

### What QMA should reject

- **R1 — RLM as the default inference loop.** The MATH 26→5.6 and CS 40→11 regressions, LCM's
  "short-context penalty" argument, and SRLM's finding that RLM degrades below base model inside the
  native window, all say the same thing: this is a *task-scoped strategy*, not a substrate.
- **R2 — Unbounded model-authored recursion.** Depth must be a kernel-enforced scoped constant with
  default 1, and fan-out/concurrency/spend must be enforced by the kernel, not by a sentence in a
  system prompt. "Add a sentence so Qwen doesn't spawn thousands of sub-calls" is not a control plane.
- **R3 — `FINAL()` / `FINAL_VAR()` string-tag termination.** 16%+13% malformed rate. The kernel must
  own the completion contract.
- **R4 — Per-backbone prompt coupling inside a plugin.** If the RLM plugin needs a different system
  prompt per provider, that belongs in a provider-scoped constant table, not baked into the loop.

### Kernel implications

Read against the reference implementation (`github.com/alexzhang13/rlm`, MIT OASYS lab, 5.5k stars,
adopted by DSPy as `dspy.RLM`, Prime Agent, Ax, Google ADK), the paper's own architecture answers the
plugin-vs-kernel question:

> "RLMs replace the canonical `llm.completion(prompt, model)` call with an `rlm.completion(prompt,
> model)` call, acting as a 'language model'."

**RLM is interface-compatible with a plain model call.** It is a *drop-in at the model-provider
seam*. That is a plugin, and a shallow one. The library already ships pluggable sandboxes
(`local`, `ipython`, `docker`, `modal`, `prime`, `daytona`, `e2b`) and pluggable providers
(OpenAI, Anthropic, OpenRouter, Portkey, vLLM) — exactly the provider-unbiased abstraction QMA wants,
validated at scale by someone else.

But three things it needs are **not** available at that seam, and those are the genuine kernel asks —
see §12.

**One direct challenge to a Cordis-style plugin kernel**, stated by the authors in the README:

> "We want to move away from the JSON tool-calling standard for both sub-agents and generic tool calls."

If QMA's plugin model is *"a plugin registers a JSON tool schema"*, this whole research line says the
higher-ceiling action space is *"a plugin is a Python module mounted into the sandbox namespace."*
RAH confirms this empirically (§3). This is a real architectural fork, not a style preference.

---

## 2. Coding Agents are Effective Long-Context Processors — `arXiv:2603.20432` (Duke)

### **This is the strongest direct challenge in the cluster. Read it before committing to RLM.**

### Core mechanism

Do not build a recursive scaffold at all. Write the corpus to a **directory tree of `.txt` files**,
hand an off-the-shelf frontier coding agent (Codex, Claude Code) the *path plus the query*, and impose
**no constraints whatsoever** on how it proceeds. It uses `grep`/`ripgrep`, `sed`, `head`, writes and
iteratively refines Python scripts, saves intermediate files, and decides for itself whether to scan,
search, or script.

### Evidence quality — **strong**

Five benchmarks spanning 188K to **three trillion** tokens (BrowseComp-Plus, Natural Questions,
LongBench, Oolong-Synthetic, Oolong-Real). Head-to-head against RLM, RAG, ReAct, and full-context.
Cost table per benchmark. Structural ablation. A clean negative result. Contamination in the
full-context baseline is acknowledged and correctly argued to be symmetric.

### Findings that hit our direction

- **SOTA on 4 of 5 benchmarks; +17.3% average over published SOTA.** No task-specific prompting, no
  training, no architecture change.
- **RLM's own reported OOLONG advantage doesn't hold on the full set.** RLM scores 64.38% on
  Oolong-Synthetic; Codex scores 71.75%. And they name the reason the published numbers diverge:
  the RLM paper used the `trec_coarse` subset and sub-200K contexts.
- **File-system *layout* is worth ~6 points.** BrowseComp-Plus, 100-example subset:
  folder structure **89.0** vs single JSON file **83.0**. Same content, same agent.
- **Adding a retriever can HURT.** With no retriever: 89.0. With BM25: 82.0. Their words: "naively
  providing retrieval tools may degrade performance … without suppressing agents' native exploration."
- **Emergent per-task strategies.** Code volume is near-zero on LongBench (the agent correctly just
  reads), code-dominated on Oolong, search-dominated on NQ. Their critique lands hard:
  *"RLMs impose a uniform recursive decomposition strategy regardless of task structure."*
- **Cost:** Codex on Oolong-Syn `$0.194` vs RLM `$0.920` — ~4.7× cheaper *and* more accurate.

### Borrow / reject

- **Borrow:** the KB layout question is a first-class design decision, not plumbing. Ship book-scale
  knowledge as a **navigable directory hierarchy**, not one blob and not (only) a vector index.
- **Borrow:** default a research mind to *no retriever*, and let it earn one. Retrieval-by-default is
  a measured regression here.
- **Reject:** the idea that a bespoke recursive kernel is *required* for book-scale corpora. It is not.
  A competent coding mind with `grep` + `python` + a filesystem is the baseline QMA must beat before
  paying for anything more.

### Kernel implication — **suggests a SIMPLER approach**

This paper is an argument that the kernel's most valuable long-context primitive is a **sandbox with a
real filesystem and real shell tools**, not a recursion engine. Everything else can be a strategy the
mind chooses at runtime. If QMA ships good sandbox + fs + shell + code-exec, it gets 4/5-SOTA
long-context behaviour for free and can add RLM later as an opt-in strategy.

---

## 3. Recursive Agent Harnesses (RAH) — `arXiv:2606.13643` (PwC)

### Core mechanism

Keep recursion, but **upgrade the recursive unit from a bare model call to a full agent harness.**
A parent mind writes an executable script in which each subtask is a `Task()` object; all tasks are
gathered into one `asyncio.gather` and run in parallel through its shell tool. Each spawned child is a
complete harness — `read_file`, `write_file`, `ls`, `glob`, `grep`, `execute`, web search, plus a
planning step — running in an **isolated workspace with no access to the parent context or to
siblings**. Children carry the same spawn capability, so decomposition is genuinely recursive rather
than one level of fan-out. **Depth bounded by a configurable limit, default 3.** Parent sees only
aggregated stdout; children write structured JSON records to a shared output path, which the parent
reads. No IPC.

Two spawn paths, chosen automatically by entry count:
- **JSON tool-call spawning** for 1–5 entries — *capped by the provider's per-turn parallel tool-call limit.*
- **Code-execution spawning** for everything else — *no such cap; scale set by the workload.*

Their framing: "It is a harness primitive, not a system-prompt convention."

### Evidence quality — **moderate; treat the number as directional**

Backbone held fixed at GPT-5 to isolate the harness effect — that part is well designed. But: a single
benchmark (Oolong-Synthetic, 199 samples), **no ablation of recursion depth, entries-per-subagent, or
spawn path** (they say so), token and latency profiles "remain uninstrumented", industry lab, code
"will be released shortly."

### The ladder it establishes (Oolong-Synthetic, GPT-5 fixed)

| Recursive unit | Score |
|---|---|
| RLM — model call, no tools | 64.38% |
| Codex coding agent — no recursion | 71.75% |
| **RAH — full agent harness** | **81.36%** |
| RAH + Claude Sonnet 4.5 | 89.77% |

**Bare-model recursion is the weakest rung on this ladder.** That ordering is the single most
consequential fact in this cluster for QMA.

### Borrow / reject / kernel

- **Borrow — the central design lesson:** *make the recursive unit a mind, not a model call.* A child
  gets its own context, its own tool grant, its own workspace, and its own spawn right. This is
  exactly a semi-profile "mind" spawning a child mind. It maps onto QMA's vocabulary with zero friction.
- **Borrow — isolation by default, aggregation by file.** No shared memory, no sibling channel, results
  land as structured records at a designated path. Deterministic aggregation, and the parent's context
  never inflates.
- **Borrow — the JSON-cap finding.** Provider per-turn parallel-tool-call limits are a hard ceiling on
  fan-out. If QMA wants thousands of parallel children, spawning must be expressible **in code inside
  the sandbox**, not only as a tool schema. This is the concrete, measurable form of the RLM authors'
  anti-JSON-tool-calling argument.
- **Reject:** the headline gain as settled. One benchmark, no ablations, no cost data. The *design* is
  the contribution; the number is a hint.
- **Kernel implication — this DEMANDS a kernel hook.** A spawn primitive that (a) is callable from
  inside sandbox code, (b) instantiates a full mind with its own scoped tool grant and workspace,
  (c) carries a depth counter, and (d) is bounded by an inherited budget, cannot live in a plugin.
  It is the kernel.

---

## 4. LCM: Lossless Context Management — `arXiv:2605.04050` (Voltropy PBC)

### Core mechanism

Accept RLM's premise (context management should be *active*) and reject its method (the model writes
the loops). Instead the **engine** owns memory, via two deterministic mechanisms:

1. **Recursive context compression** — a dual-state store. An **Immutable Store** persists every user
   message, assistant response, and tool result verbatim, forever, unmodified. An **Active Context**
   holds pointers. A high-fanout **DAG of summaries** compacts older blocks; every summary retains
   **lossless pointers** back to the originals, reachable via `lcm_grep` / `lcm_expand`. Soft threshold
   triggers async compaction; hard threshold blocks and compacts.
2. **Recursive task partitioning** — engine-managed parallel primitives, `LLM-Map` and `Agentic-Map`,
   replace model-written loops:

```
# RLM: model writes the control flow          # LCM: model delegates control flow to the engine
for chunk in large_file:                      tool_call("llm_map",
    response = llm.query(chunk)                   input_path="large_file.jsonl",
                                                  prompt="Extract entities...",
                                                  output_schema={...},
                                                  concurrency=16)
```

### The argument — **the best-articulated challenge in the cluster**

> RLM gives the model **GOTO**-like power. LCM offers **structured control flow**: a small set of
> well-defined operators covering the common cases deterministically.

Their stated trade: sacrifice maximal flexibility for **termination guarantees**, **zero-cost
continuity on short tasks**, and **lossless retrievability of all prior state**. And the diagnosis of
RLM's core production problem: *"the system inherits the stochasticity of the model: an efficient
chunking script in one rollout may become a suboptimal one in the next."* Plus a **short-context
penalty** — wrapping every interaction in a recursive scaffold taxes the majority of queries that
would have fit comfortably in the window.

### Evidence quality — **weak. This is a vendor paper.**

Voltropy benchmarking its own product (Volt) against Claude Code, on one split (`trec_coarse`), no cost
data, no variance, contamination acknowledged. Result: Volt 74.8 avg vs Claude Code 70.3; Volt ahead at
every length ≥32K, behind at 8K and 16K. Their own data shows the short-context penalty applies to
them too.

**Take the argument, not the numbers.** The GOTO/structured-programming framing is the sharpest lens in
this cluster and it is independently corroborated by λ-RLM (§6), which *does* have real evidence.

### Borrow / reject / kernel

- **Borrow — B6: an append-only immutable store with lossless pointers, and summaries as a DAG over it.**
  For a long-running research mind and for book-scale KBs this is strictly better than RLM's per-query
  "load the prompt into a variable." Nothing is ever destroyed; compaction is a *view*, not a deletion.
  It is also the only design in this cluster that makes an agent's history auditable after the fact.
- **Borrow — B7: engine-managed `llm_map` / `agentic_map` as first-class kernel primitives** with
  `input_path`, `prompt`, `output_schema`, `concurrency`. This covers the overwhelmingly common
  "fan out over N items" case deterministically, with a knowable cost and a guaranteed termination.
- **Borrow — B8: zero-cost continuity.** Short tasks must pay *nothing* for the long-context machinery.
  Structural property, not a model bet. Make it a kernel invariant.
- **Reject — LCM as a replacement for the escape hatch.** Their own conclusion is the right one:
  *"Just as GOTO remains available in modern languages … a future system could default to LCM's
  structured operators for most usage while retaining full RLM-style symbolic recursion for
  exceptional tasks."* That is the design QMA should adopt verbatim.
- **Kernel implication:** deterministic map/reduce operators over an immutable store are **kernel
  primitives**. RLM-style free-form recursion is the **plugin escape hatch** behind them.

---

## 5. Think, But Don't Overthink — `arXiv:2603.02615` (CUHK, single author)

### Core finding

Independent reproduction with DeepSeek v3.2 and Kimi K2, scaling depth 1→2.

### Evidence quality — **weak by the numbers, high by the effect size**

20 samples per condition, single run, no significance testing. The author states this and argues the
effect sizes carry it. Fair — a 3.6s → 344.5s latency change does not need error bars. Treat as a
qualitative failure taxonomy backed by suggestive numbers, and it is the *only* independent
reproduction available.

### What it shows

- **Depth 1 helps only where the task is genuinely hard.** DeepSeek v3.2 on OOLONG: 0.0% → 42.1%. Real.
- **RLM *hurts* on simple retrieval.** S-NIAH degraded under the scaffold.
- **RLM *hurts* models that are already good at long context.** Base Kimi K2 scored **86.6%**; forced
  into the RLM scaffold it collapsed to **60.0%** (depth 1) and **55.0%** (depth 2).
- **Latency explodes superlinearly with depth.** DeepSeek S-NIAH: base **3.6s** → depth 1 **89.3s** →
  depth 2 **344.5s**. Kimi K2 peaks at **545.5s/query** at depth 2; one OOLONG trace ran **1223.6s**.
- **Token counts sometimes *fall* while latency explodes** — the signature of trajectories crashing
  early on format errors or stalling in serial sub-call loops.

### Three named failure modes — treat as a kernel test suite

1. **Parametric hallucination / context-anchoring loss.** At depth 2, asked for a fictional magic number
   hidden in the text, DeepSeek returned the real nuclear magic numbers (2, 8, 20, 28, 50, 82, 126)
   from parametric memory. **Deep recursion severed the model from its own input.**
2. **Formatting collapse in the REPL.** Models return raw `print(f"Answer: {x}")` instead of the answer —
   role confusion between scratchpad and user-facing output. Corroborates the RLM paper's own 16%/13%
   `FINAL` misuse rate.
3. **Performative reasoning and endless verification.** 741.5s spent generating 11,715 tokens,
   re-verifying already-extracted answers. Their diagnosis is the important line:
   > *"The REPL architecture inherently lacks a stopping mechanism for an over-anxious agent."*

### Borrow / reject / kernel

- **Borrow — B9: a gate that decides whether to engage RLM at all.** Cheap pre-check: does the input
  exceed the effective window, *and* is the task aggregation-shaped? If not, call the model directly.
  Without this gate, RLM is a net negative on the majority of traffic.
- **Reject — R5: depth > 1 as a default, on any current model.** Ship depth 1. Make depth 2+ an
  explicitly-enabled, budget-gated experiment.
- **Kernel implication — DEMANDS a kernel hook.** "The REPL lacks a stopping mechanism" is precisely
  the thing a plugin cannot fix for itself. Wall-clock ceilings, sub-call count ceilings, spend
  ceilings, and a no-progress detector must be enforced by the kernel around *any* loop plugin. This
  is the single clearest kernel-level requirement produced by the entire cluster.

---

## 6. The Y-Combinator for LLMs: λ-RLM — `arXiv:2603.20105` (IIT Delhi / Huawei Noah's Ark / UCL)

### Core mechanism

Keep prompt-as-environment; **delete the open-endedness of what may execute inside it.** The REPL still
stores the prompt externally, still exposes peek/slice, still supports sub-calls. What changes is the
control interface: instead of synthesising arbitrary programs token by token, the model composes a
**fixed typed library of pre-verified combinators**:

`SPLIT` and `PEEK` (decompose/inspect) · `MAP` (lift processing over collections) · `FILTER`
(symbolic pruning) · `REDUCE` / `CONCAT` / `CROSS` (structured aggregation) · **`M`, the only neural
primitive, used exclusively on bounded leaf subproblems.**

Recursion is a fixed-point over these combinators (a Y-combinator), which "ties the knot without
requiring the LLM to manage function names or global state, eliminating the reference errors and
non-termination failures common in open-ended REPL loops."

The stated separation: **semantic reasoning stays neural; structural control becomes symbolic,
deterministic, and auditable.**

### Evidence quality — **the best in the cluster after the source paper**

Four task families, **nine base models, 36 model-task comparisons**, formal operational semantics with
termination and cost-bound proofs under size-decreasing decomposition, open-sourced. Ceiling: contexts
tested only to 128K — it does not probe the >1M regime where RLM's headline claim lives.

### Results

- **Wins 29/36 comparisons (81%) against standard RLM.**
- **+21.9 points on weak models, +18.6 on medium** — the gain is largest exactly where free-form code
  generation fails, which is the RLM paper's own admitted weakness.
- **3.3×–4.1× latency reduction**; **6.2× speedup with +28.6 points on OOLONG-Pairs** — the task RLM
  was best at.
- Formal guarantees RLM lacks: **termination by construction**, closed-form cost bounds, controlled
  accuracy scaling with depth, and an optimal partition rule under a simple cost model.

### The argument that matters

> "In standard RLMs, uncertainty enters twice: first through the model's semantic judgments about the
> task, and second through the model's generated control flow, which may be malformed, inefficient, or
> non-terminating."

λ-RLM removes the second source. That is the whole thesis, and the 36-comparison sweep supports it.

### Borrow / reject / kernel

- **Borrow — B10: the combinator set as the kernel's decomposition vocabulary.**
  `SPLIT / PEEK / MAP / FILTER / REDUCE / CONCAT / CROSS + M`. Small, typed, verifiable, and
  independently arrived at by LCM (`llm_map`) from a production angle. Two papers converging on the
  same seven-ish operators from opposite directions is a strong signal.
- **Borrow — B11: "the model is a bounded oracle at the leaves."** This is a clean architectural rule
  and it makes cost predictable in advance rather than discovered after the bill.
- **Reject — R6: replacing free-form code entirely.** RAH's evidence cuts the other way for tasks
  needing per-entry tool use, and RAH explicitly notes λ-RLM "decomposes through a deterministic
  pipeline with fixed structure and **no tool access**" and "cannot spawn subagents that carry its own
  tools." Typed combinators buy reliability at the cost of the open action space.
- **Kernel implication — suggests a SIMPLER approach than a full recursion engine.** If QMA ships the
  combinator library as kernel primitives, most of RLM's practical value is available with termination
  proofs and no plugin at all. **This, plus LCM, is the strongest case that a Cordis-style
  free-form-loop plugin kernel is the wrong default.**

---

## 7. Recursive Models for Long-Horizon Reasoning — `arXiv:2603.02112` (Yang, Srebro, Li — ICML)

### Core mechanism — the theoretical foundation, and the strongest case *for* a kernel primitive

Strip recursion to its minimum: one base LLM plus **two tools, `call` and `return`.** `call` creates an
**isolated fresh context** in which the model solves a subtask independently; `return` **discards all
intermediate reasoning** and passes back only the result. Each invoked model may itself call. This
yields a **deep context stack with every individual context bounded by the window.**

### Results

- **Any computable problem admits a recursive decomposition** in which each subtask needs only
  **exponentially smaller active context** than a standard autoregressive model.
- With local space `S(n)`, recursive models solve anything requiring `exp(O(S(n)))` time; a standard
  autoregressive model would need context `exp(O(S(n)))`. **Exponential gap.**
- **Summarisation is provably optimal among all "single-context" models — and still strictly weaker
  than recursion.** No context-management strategy confined to one sequence can beat summarisation, and
  **even depth-1 recursion already matches that ceiling; deeper recursion breaks through it.**
  *This is a formal proof that compaction has a hard ceiling that recursion does not.*
- Empirical: a **3B** model fine-tuned to reason recursively scores **98 / 95 / 64** (easy/medium/hard)
  on SAT vs GPT-4o's 69.9 / 55.2 / 48.8 and Qwen3-235B's 88.0 / 64.8 / 51.4 — trained only on
  easy+medium, generalising to hard.
- **Trajectory length grows rapidly while active context length stays bounded**, and the gap widens
  with difficulty.

### The line with the sharpest kernel consequence

> "The recursive model naturally induces a separation between local and global space: the generator
> only needs to attend to the active context, while **inactive contexts in the context stack can be
> offloaded to external storage and restored upon return**."

They note that with KV caches of suspended contexts stored externally and restored on return, inference
cost drops by a factor of global-space / local-space.

### Evidence quality

Theory: strong (proofs, ICML, grounded in Savitch's recursive Turing machines, stack automata, iterated
pushdown storage). Empirical: narrow (SAT only, one 3B model) but the effect size is unambiguous.

### Borrow / reject / kernel

- **Borrow — B12: `call` / `return` with context isolation as the minimal recursion primitive.** Not
  "sub-LLM call," not "sub-agent" — a *stack frame*. Fresh context on call, discard-and-return-result on
  return. Everything else in this cluster (RLM, RAH, ROMA, Chained RLM) is a specialisation of this.
- **Borrow — B13: an explicit, suspendable, persistable context stack.** Suspended frames go to storage;
  restore on return. For a long-running research mind this is also *checkpointing and resumability* for
  free — the mind can be stopped and rehydrated mid-recursion.
- **Kernel implication — DEMANDS a kernel hook, and this is the one worth paying for.** A context stack
  with isolation, suspension, external offload, and restore is not expressible as a plugin over a
  provider API. **This is the load-bearing theorem for the whole cluster: if QMA ever wants a mind to
  exceed what compaction can do, it needs `call`/`return` in the kernel.** Note it also states depth-1
  already matches the best possible single-context system — which reconciles the theory with the
  empirical finding that depth>1 breaks current models. *Build the stack; default the depth to 1.*

---

## 8. RLMs Meet Uncertainty (SRLM) — `arXiv:2603.15653` (Apple)

### **Second-strongest direct challenge. It attacks the causal claim.**

### Core mechanism

Keep prompt-as-external-variable and programmatic context interaction. **Drop the requirement that
programs instantiate recursive self-queries at all.** Sample `K` candidate context-interaction programs
from the policy, then select among them using three intrinsic uncertainty signals — **self-consistency**
(sampling), **verbalized confidence** (semantic), and **reasoning trace length** (behavioural). No
verifier, no reward model, no labels.

Their framing question: *"Is recursion itself the key ingredient for long-context reasoning, or is the
real bottleneck how we select among candidate interaction programs under uncertainty?"*

### Evidence quality — **strong methodology**

Multiple benchmarks, multiple backbones, varied context lengths, and critically **compared under the
same wall-clock time budget** — the fairest comparison protocol in this cluster.

### Findings

- **+22% over RLM under an equal time budget.**
- **"Recursion is not the primary driver of RLM's performance."** A simple self-reflective program
  search matches or surpasses RLM **without any explicit recursion or self-query mechanism.**
- **RLM's recursive procedure is more sensitive to context length than self-reflection; inside the
  model's native window, recursive RLM reasoning degrades performance relative to the base model.**
  (Independently corroborates Kimi K2's 86.6→60.0 collapse in §5 and the MATH/CS regressions in §1.)
- **RLM is systematically weak on semantically intensive tasks** where heuristic program search is
  insufficient.
- Their repositioning: *"recursion is one component of long-context reasoning rather than its defining
  feature."*

### Borrow / reject / kernel

- **Borrow — B14: sample-K-programs-and-select is a cheaper, more robust lever than deepening recursion.**
  Under a fixed budget, spend it on *breadth of strategy* rather than *depth of recursion*.
- **Borrow — B15: three free confidence signals** (self-consistency, verbalized confidence, trace
  length) requiring no verifier. Useful far beyond long context — a general kernel-level quality signal
  for any mind output.
- **Kernel implication — suggests a SIMPLER approach.** If the decomposition *program* is what matters
  and recursion is incidental, then the kernel needs (a) a way to run K candidate strategies and
  (b) a selection hook — which is ordinary parallelism plus a scoring interface, not a recursion
  engine. **Cheaper than a recursion kernel and better-evidenced under matched budgets.**

---

## 9. Chained Recursive Language Models — `arXiv:2608.05124`

### Core mechanism

Instead of one root trajectory, call the same RLM **multiple times in a linear chain**. Each call is a
**fresh root** — a new instance of the model and environment. It receives the original problem and
context but **only a compact continuity state** from its predecessors: a plain-text **summary**, a
plain-text **blackboard**, and a set of plain-text **artifacts on disk**. Raw predecessor trajectories
are saved but *not* auto-injected; a later root may inspect them only if the summary or artifact is
insufficient. Explicitly **no JSON, no host-parsed state** in the handoff.

Worked shape: Root 0 builds a candidate event ledger → Root 1 inspects and corrects the ledger →
Root 2 audits the counts and answers.

### The diagnosis of RLM it is built on — worth quoting

> "The global working state still largely lives inside one orchestration trajectory. Early extraction
> or aggregation mistakes can therefore become **stale assumptions** that later steps continue to use."

And the mechanism of the fix: a fresh root *re-reads its predecessor's conclusion as an external object*
rather than as its own prior commitment.

### Evidence quality — **weak.** Not trained, no RL, no verifier, "initial evaluation protocol," no
headline numbers surfaced. Treat as a design pattern with a good rationale, not a result.

### Borrow / reject / kernel

- **Borrow — B16: fresh-root checkpoint boundaries with artifact-mediated handoff.** For a long-running
  research mind this is the antidote to trajectory staleness, and it is close to what a human research
  process actually looks like: durable notes that the next session audits.
- **Borrow — B17: plain-text, human-readable continuity state.** Summary + blackboard + artifacts, no
  host-parsed schema. Directly inspectable by an operator mid-run.
- **Reject — R7: unenforced artifact discipline.** Their own limitations section: the host does not
  require a root to read artifacts before finalising, so premature answers slip through; a bad Root-0
  event definition propagates; and chains drift when a later root ignores a good artifact. If QMA
  adopts this, **the kernel must enforce the read-before-finalise contract** — that is precisely the
  gap they left open.
- **Kernel implication:** modest. An artifact workspace with a run-scoped lifetime plus a "fresh mind,
  inherited artifacts" spawn mode. Both are plugin-shaped if the kernel already has B2/B13.

---

## 10. RLM-JB: RLMs for Jailbreak Detection — `arXiv:2602.16520` (Silverfort)

### Core mechanism

Use the RLM shape as a **security engineering pattern**: root model canonicalises input, attempts
de-obfuscation (e.g. Base64 spans, carrying forward both original and decoded forms), **chunks the text
into overlapping segments to guarantee coverage**, screens each segment in parallel with worker calls
returning structured verdict+confidence+signals, then aggregates cross-segment evidence to recover
**split-payload** attacks (an "ignore instructions" preamble in one segment, the payload in another).

### Evidence quality — **moderate.** One attack family (AutoDAN), one author, industry. F1 up to 98.49%,
precision 98.99–100%, FPR 0–2%. Explicitly not evaluated against adaptive adversaries optimising
against the detector. **~3× processing time vs baseline.** They correctly propose a cheap triage filter
in front, reserving full analysis for high-risk inputs.

### Why this is in the cluster, and the risk it implies

This paper is *useful* but it also names the threat model that the rest of the cluster ignores.
**Every RLM-shaped system feeds untrusted content into a model that writes and executes code.** The
reference implementation's default sandbox (`local`) runs `exec` **in the host process** — the README
says plainly it "should not be used for production settings." For a research mind reading the open web
into a REPL, that is a live prompt-injection-to-code-execution path.

### Borrow / reject / kernel

- **Borrow — B18: overlapping-chunk coverage with parallel screening and compositional aggregation** as
  a reusable pattern for *any* whole-corpus guarantee, not just security. It is the honest way to say
  "every part of the input was examined."
- **Borrow — B19: cheap triage in front of expensive recursion.** Same shape as B9's engage-RLM gate.
- **Kernel implication — DEMANDS a kernel hook:** untrusted context must be a **typed, tainted**
  `ContextRef`, and the kernel must refuse to bind tainted content into a sandbox that has host
  process access or unrestricted egress. Isolation level should be a scoped constant derived from the
  taint of the inputs, not a developer's choice at call time. *Non-negotiable before any web-reading
  research mind ships.*

---

## 11. ROMA: Recursive Open Meta-Agent Framework — `arXiv:2602.01848`

### Core mechanism

One recursive control loop applied uniformly at **every** node of a task tree:

```
Solve(task):
  if is_atomic(task):  return execute(task)      # Atomizer -> Executor
  subtasks = plan(task)                           # Planner -> dependency-aware MECE DAG
  results  = [Solve(s) for s in subtasks]         # recursive, parallel where deps allow
  return aggregate(results)                       # Aggregator
```

**Atomizer** decides atomic vs not. **Planner** emits a mutually-exclusive/collectively-exhaustive
dependency DAG maximising parallelism. **Executors** are *type-specialised* by a small `task_type` set
— `search`, `think`, `write`, `code` — each routed to a different strategy (ReAct, CodeAct, CoT) and a
different model, so cost/latency/quality can be traded per node type. **Aggregator** distils and
normalises child outputs into the parent's target form rather than concatenating them.

Engineering that matters to QMA:

- Components are **DSPy modules with typed input/output signatures**, so they can be **swapped while
  preserving type compatibility**, with optimisation hooks for prompts and weights.
- **Intermediate artifacts persist to an object store and are passed to downstream nodes through typed
  signatures rather than embedded in prompts** — reuse across the tree without inflating context.
- `code` nodes run in a **sandboxed runtime**, reaching external tools through **MCP**.
- Because one protocol runs at every node, the run produces a **structured hierarchical trace mirroring
  the execution tree** — failures are localisable to the planning, retrieval, or aggregation decision
  that caused them.
- Their named pathology, which is our pathology: *"agentic systems suffer from uncontrolled context
  growth, where accumulating intermediate reasoning, tool outputs, and artifacts degrade performance."*

### Evidence quality — **moderate-strong as a framework paper**; the contribution is the abstraction and
the trace model rather than a benchmark number.

### Borrow / reject / kernel

- **Borrow — B20: the four-role node contract** (Atomizer / Planner / Executor / Aggregator) as the
  kernel's recursion protocol. It is more opinionated than RLM's free-form loop and far more debuggable,
  and it composes cleanly with `call`/`return` (§7): each node is a stack frame.
- **Borrow — B21: typed signatures as the plugin seam.** This is the concrete answer to "what is a
  plugin in QMA?" — a module with a typed input/output signature, swappable while type-compatible.
  Strictly better than either a JSON tool schema or an untyped Python module.
- **Borrow — B22: artifacts by reference through typed signatures, never inline in prompts.** Same
  principle as B1 and B6, arrived at from the multi-agent side. **Three independent papers converge
  on it.**
- **Borrow — B23: type-specialised executors with per-type model selection.** `search`/`think`/`write`/
  `code` is a good default taxonomy and makes cost control a routing decision.
- **Kernel implication:** ROMA is the closest published thing to what a QMA kernel should look like.
  It DEMANDS kernel support (uniform node protocol, artifact store, trace tree, sandbox) but everything
  above the protocol is plugin-shaped.

---

## 12. Direct answer to the assigned question

### Is RLM an inference-loop plugin, or does it demand kernel support?

**RLM as published is a plugin, and a shallow one — but the *capability class* it belongs to demands
four kernel primitives that a provider-seam plugin cannot provide.**

The plugin claim is not an interpretation; it is the authors' own design. `rlm.completion(prompt,
model)` is a drop-in replacement for `llm.completion(prompt, model)`. The reference library is a pip
package with swappable sandboxes and swappable providers, adopted as `dspy.RLM` inside another
framework. If QMA's kernel has a model-provider seam, RLM slots into it today with zero core changes.

**What it needs that the provider seam does not give:**

| # | Kernel primitive | Why a plugin cannot own it | Evidence |
|---|---|---|---|
| **K1** | **Reentrancy** — sandbox code must be able to call *back into* the kernel to start a new model call or a new mind, accounted to the same run | The sandbox is by construction isolated from the host; the reference impl needs "a host-side proxy [to] bridge LM access back into the container" | RLM impl (Docker/Modal/E2B backends); RAH §3.2 |
| **K2** | **Budget ledger** — depth, fan-out, concurrency, tokens, spend, wall-clock — inherited down the tree and decremented, enforced by the kernel | A plugin cannot bound its own runaway; the loop *is* the runaway | 3.6s→344.5s; "thousands of LM subcalls for basic tasks"; authors' own "exploding sub-call costs"; "the REPL inherently lacks a stopping mechanism" |
| **K3** | **Context stack** — `call`/`return` with isolated frames, suspendable, offloadable to storage, restorable | Proven to exceed what *any* single-context strategy can do; requires owning frame lifecycle and storage | `2603.02112` (theorem + external KV offload) |
| **K4** | **Taint-scoped isolation** — untrusted context must not be bindable into a host-process sandbox | Security invariant; a plugin choosing its own isolation level is not a control | `2602.16520`; RLM impl default `local` runs `exec` in-process |

### What the kernel needs so an RLM loop is swappable-in without core surgery

Seven concrete requirements. Note that **five of the seven are things QMA wants anyway** for reasons
unrelated to RLM — which is the good news: build these and RLM becomes a config choice.

1. **`ContextRef` — inputs by reference, never by value.** A handle carrying `{id, type, total_length,
   chunk_boundaries, accessor, taint}`. Minds receive handles; materialisation is an explicit,
   budgeted operation. *(Every winning system in this cluster does this. Non-negotiable.)*
2. **A reentrant `spawn()` primitive exposed inside the sandbox namespace**, with a single signature
   covering both recursive units:
   - `spawn(prompt, model=..., tools=[], workspace=None)` → a bare sub-model call (RLM's unit)
   - `spawn(prompt, model=..., tools=[fs, shell, web], workspace=fresh)` → a full child mind (RAH's unit)

   Same primitive, different **capability grant**. The grant, not the call site, is what differs.
   *This is the single most important design decision in the cluster, because RAH's ladder shows the
   full-harness unit beats the bare-model unit by 17 points on a fixed backbone.*
3. **Scoped constants for the recursion envelope**, inherited and decremented: `max_depth` (default
   **1**), `max_fanout`, `max_concurrent_subcalls`, `token_budget`, `spend_budget`, `wall_clock_budget`,
   plus a no-progress detector. QMA's scoped-constants design maps onto this exactly — this is the
   cluster's best argument that scoped constants were the right call.
4. **Sandbox provider abstraction with an isolation *level* derived from input taint**, not chosen by
   the caller. RLM's library validates the provider-unbiased shape empirically (local / ipython /
   docker / modal / prime / daytona / e2b) — QMA should mirror that set and add the taint rule.
5. **A kernel-owned completion contract.** Not `FINAL()` string tags — a typed return with a schema.
   The 16% + 13% malformed-turn rate is the cost of leaving this to the plugin.
6. **A trajectory tree recorder.** Run config plus every iteration and every sub-call, reconstructable,
   hierarchical, matching the execution tree. RLM ships `RLMLogger` + a visualiser; ROMA makes the trace
   the point. Required for both debugging and audit.
7. **An engine-managed operator library alongside the free-form loop.** `SPLIT / PEEK / MAP / FILTER /
   REDUCE / CONCAT / CROSS` (λ-RLM) ≡ `llm_map` / `agentic_map` (LCM). Deterministic, terminating,
   cost-predictable, and the **default path**. Free-form RLM recursion is the *escape hatch behind it*.

### Where this contradicts a Cordis-leaning free-form-plugin-kernel direction

Stated plainly, because the brief asks for it prominently:

- **A Cordis-style kernel whose plugin unit is a JSON tool schema has a measured ceiling.** RAH shows
  JSON tool-call spawning is capped by the provider's per-turn parallel-tool-call budget, and that
  routing spawns through *code* is what unlocks thousands of parallel children. The RLM authors state
  the position directly: *"We want to move away from the JSON tool-calling standard for both sub-agents
  and generic tool calls."* If QMA's plugin seam is a schema registry, this cluster says that seam is
  the bottleneck.
- **The better plugin seam is ROMA's: a module with a typed input/output signature, swappable while
  type-compatible.** It keeps the verifiability that JSON schemas give and the expressivity that code
  gives.
- **A free-form model-authored loop should not be the kernel's default.** LCM's GOTO argument plus
  λ-RLM's 29/36 win rate, 3.3–4.1× latency reduction, and termination proofs say the default control
  flow should be *structured*, with the free-form loop reserved for the exceptional case. A kernel that
  makes free-form the default is a kernel that inherits the model's stochasticity as a system property.
- **The simplest thing may beat the kernel entirely for our stated use case.** Cao et al. put the corpus
  on a filesystem, hand a coding agent `grep` + `python`, impose nothing, and take SOTA on 4/5
  benchmarks at ~4.7× lower cost than RLM. **QMA must beat that baseline before spending kernel
  complexity on recursion.** Concretely: build sandbox + filesystem + shell + code-exec first, measure,
  and only then decide whether the recursion engine earns its keep.

---

## Cluster verdict

### Top borrowings (ranked by confidence × value)

1. **Context as a handle, not as prompt content** (B1/B6/B22). Converged on independently by RLM
   (REPL variable), Cao et al. (filesystem), LCM (immutable store + lossless pointers), Chained RLM
   (artifact workspace), and ROMA (typed artifact signatures). **Five independent derivations. This is
   the finding of the cluster, and it is bigger than RLM.**
2. **`call` / `return` with isolated, suspendable, offloadable context frames** (B12/B13, §7). Formally
   proven to exceed what any compaction strategy can achieve, and it delivers checkpointing and
   resumability for a long-running research mind as a side effect. **The one thing worth putting in the
   kernel.**
3. **Make the recursive unit a *mind*, not a model call** (RAH, §3). 64.38 → 81.36 on a fixed backbone.
   One primitive, two capability grants.
4. **Deterministic map/reduce operators as the default, free-form recursion as the escape hatch**
   (λ-RLM + LCM, §4/§6). Termination proofs, cost bounds, 29/36 win rate, 3.3–4.1× faster.
5. **Kernel-enforced recursion envelope as scoped constants** (§5). Depth default 1. Everything in this
   cluster that broke, broke here.
6. **The engage-gate** (B9/B19): decide *whether* to recurse before recursing. Without it RLM is a net
   negative on the majority of traffic.
7. **Corpus layout is a design decision** (§2): folder hierarchy 89.0 vs single file 83.0; adding a
   retriever *dropped* 89.0 → 82.0.

### Direct challenges to our current direction — stated without softening

- **RLM is not the strongest known long-context method, and the field's "paradigm of 2026" framing is
  ahead of the evidence.** On the full Oolong-Synthetic set with the backbone held fixed:
  **RLM 64.38 < plain coding agent 71.75 < recursive agent harness 81.36.** Bare-model recursion is the
  *weakest* rung.
- **Recursion may not even be the causal ingredient.** Apple's SRLM matches or beats RLM **with no
  recursion and no self-query**, under a matched wall-clock budget, and concludes recursion is "one
  component rather than the defining feature." This is the best-controlled comparison in the cluster and
  it undercuts the core claim.
- **RLM actively harms performance in the common case.** Inside the native context window it degrades
  below base (SRLM). On an already-strong long-context model it collapsed 86.6 → 60.0 (§5). On general
  reasoning it cut MATH 26.0 → 5.6 and CS 40.4 → 11.0 — **in the RLM paper's own table**.
- **A free-form model-authored loop is a stochastic control plane.** LCM's GOTO framing is correct and
  λ-RLM proves the structured alternative wins on 29/36 comparisons with termination guarantees.
  A kernel built around free-form loops inherits model variance as an architectural property.
- **If QMA's plugin unit is a JSON tool schema, that seam is measurably capped** (RAH), and the RLM
  authors are explicitly designing away from it. ROMA's typed-signature modules are the better answer.
- **For Mubarak's stated use cases specifically:**
  - **Book-scale knowledge bases** — RLM is a *poor* structural fit. It assumes the corpus arrives as a
    per-query prompt. A persistent KB wants LCM's immutable store with lossless pointers, laid out as
    Cao's navigable directory hierarchy. **RLM is at best the query strategy over that store, never the
    store.** And a plain coding mind over that filesystem is the baseline to beat.
  - **Long-running sandboxed research minds** — this is where the cluster genuinely supports us, but via
    the *theory* paper (§7) rather than RLM itself: a persistable context stack, plus Chained RLM's
    fresh-root artifact handoff to defeat trajectory staleness, plus taint-scoped sandbox isolation
    because a web-reading mind that writes and executes code is a live injection-to-execution path.

### Recommended posture

**Do not make RLM the kernel loop. Do build the four primitives it needs (K1–K4), because three of
them (reentrant spawn, budget ledger, context stack) are what *every* system in this cluster needs and
the fourth (taint-scoped isolation) is a safety precondition for shipping at all.** Then make RLM one
selectable strategy among several — behind an engage-gate, at depth 1, inside a budget — and make the
deterministic operator library the default path. Measure against the embarrassingly simple baseline
(filesystem + grep + python) before paying for anything more.
