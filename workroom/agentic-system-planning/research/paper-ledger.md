# QMA Paper Ledger — component → research to borrow from

Organized 2026-08-18 from the AlphaXiv conversation (C:\Users\Mubarak\Desktop\chat-harnes.txt, updated version) plus papers Mubarak supplied directly. Links come from the AlphaXiv assistant — treat each as unverified until its step actually reads it (at least one link below is malformed). This ledger is an index, not a reading commitment: each component's papers get read when that component becomes the active step.

## The stack (reading/build order the transcript converged on)

harness → tools/runtime → context & memory → skills → loops & orchestration → evaluation & traces → safe self-improvement.
Build order: one observable, permission-bounded, tool-using agent with an evaluation loop → structured memory → skills → profiles/multi-agent → only then self-improvement.

## 1. Harness core & architecture (feeds Step 1–2: kernel contract)

- The Hitchhiker's Guide to Agentic AI: From Foundations to Systems — https://www.alphaxiv.org/abs/2606.24937 (vocabulary + design-space map; transcript's #1 read)
- From Question Answering to Task Completion: A Survey on Agent System and Harness Design — https://www.alphaxiv.org/abs/2606.20683
- Architectural Design Decisions in AI Agent Harnesses — https://www.alphaxiv.org/abs/2604.18071
- Code as Agent Harness — https://www.alphaxiv.org/abs/2605.18747 (harness = real inspectable software, not a giant prompt — aligns with our kernel-first stance)
- From Model Scaling to System Scaling: Scaling the Harness in Agentic AI — https://www.alphaxiv.org/abs/2605.26112
- Cordiverse paper: A Programming Paradigm for Spatiotemporal Composability — https://github.com/cordiverse/paper (PRIMARY — under study now by the running workflow)

## 2. Reversibility & orchestration control (feeds minds-in-sandboxes design)

- Shepherd: Enabling Programmable Meta-Agents via Reversible Agentic Execution Traces — https://www.alphaxiv.org/abs/2605.10913 + https://github.com/shepherd-agents/shepherd (the control plane: fork, inspect, replay, select, apply, discard)
- Agentic Transaction: Towards ACID-Compliant Agent Systems — (link not captured; from search results — locate when needed)

## 3. Memory

- Agentic Memory: Learning Unified Long-Term and Short-Term Memory Management — https://www.alphaxiv.org/abs/2601.01885
- Agent Memory: Characterization and System Implications of Stateful Long-Horizon Workloads — https://www.alphaxiv.org/abs/2606.06448
- ACM: Agentic Context Management for Long Horizon Tasks — https://www.alphaxiv.org/abs/2607.23809
- AdMem: Advanced Memory for Task-solving Agents — https://www.alphaxiv.org/abs/2606.06787
- From Memory to Skills: Evidence-Grounded Co-Evolution Governance for Long-Horizon LLM Agents — https://www.alphaxiv.org/abs/2607.16621 (bridge paper: verified experience becomes governed capability — pairs with the promotion-gate law)
- Also parked from Mubarak by recall: "Gray box", "Tencent Memory". **DISPOSITION (2026-08-18 repair pass): remains parked by design** — the real project names cannot be verified without Mubarak; the memory cluster (c3) was researched from its five assigned papers without them; cost of deferral is low. Ask Mubarak for the actual names when memory becomes the active step.

## 4. Skills

- A Comprehensive Survey on Agent Skills: Taxonomy, Techniques, and Applications — https://www.alphaxiv.org/abs/2605.07358 (read before defining what "skill" means in QMA)
- CoEvoSkills: Self-Evolving Agent Skills via Co-Evolutionary Verification — https://www.alphaxiv.org/abs/2604.01687
- SkillOpt: Executive Strategy for Self-Evolving Agent Skills — https://www.alphaxiv.org/abs/2605.23904
- SkillClaw: Let Skills Evolve Collectively with Agentic Evolver — https://www.alphaxiv.org/abs/2604.08377
- Demystifying Agent Skills: Why They Work—Until They Don't — https://www.alphaxiv.org/abs/2608.14036 (counterweight — brittleness under distribution shift)
- CODESKILL: Learning Self-Evolving Skills for Coding Agents — https://www.alphaxiv.org/abs/2605.25430
- Memento-Skills: Let Agents Design Agents — https://www.alphaxiv.org/abs/2603.18743 (Mubarak-supplied earlier)

## 5. Tools

- Tool-R0: Self-Evolving LLM Agents for Tool-Learning from Zero Data — https://www.alphaxiv.org/abs/2602.21320
- Tool-Making and Self-Evolving LLM Agents in Low-Latency Systems — https://www.alphaxiv.org/abs/2607.08010
- AgentFactory: A Self-Evolving Framework Through Executable Subagent Accumulation and Reuse — https://www.alphaxiv.org/abs/2603.18000 (successful trajectories → executable subagents)
- The Bitter Lesson of Tool Calling — (from search results; locate when needed)

## 6. Loops, graphs, multi-agent orchestration

- Stop Hand-Holding Your Coding Agent: Engineering the Loops that Replace Step-by-Step Prompting — https://www.alphaxiv.org/abs/2607.00038
- When Agents Do Not Stop: Uncovering Infinite Agentic Loops in LLM Agents — https://www.alphaxiv.org/abs/2607.01641 (budgets, stop rules, escalation — read before autonomy)
- Beyond Individual Intelligence: Surveying Collaboration, Failure Attribution, and Self-Evolution in Multi-Agent Systems — https://www.alphaxiv.org/abs/2605.14892
- MANTA: Multi-Agent Network Topology Adaptation for Self-Evolving Multi-Agent Systems — https://www.alphaxiv.org/abs/2607.28527

## 7. Context at scale (Mubarak addition — not in the transcript)

- RLM / Recursive Language Models — recursive inference over near-unbounded context (root model queries sub-models over context slices instead of stuffing one window). Candidate mechanism for: book-scale knowledge bases (e.g. parse whole books via Firecrawl → domain corpus like "scalping across all timeframes"), long-running sandboxed research bots, high-cost high-context tasks. Locate the paper + any successors when this becomes the active step.

## 8. Evaluation, provenance, safety

- HarnessOpt-Bench: Evaluating LLMs at Harness Optimization — https://www.alphaxiv.org/abs/2608.06301
- From Agent Traces to Trust: A Survey of Evidence Tracing and Execution Provenance — https://www.alphaxiv.org/abs/2606.04990
- JANUS: Foreseeing Latent Risk for Long-Horizon Agent Safety — https://www.alphaxiv.org/abs/2607.19913
- Engineering Trustworthy Agentic AI for Critical Systems — https://www.alphaxiv.org/abs/2607.18548
- AppLooper: An Agentic Application Engineering Loop for Accountable Release — https://www.alphaxiv.org/abs/2608.14093

## 9. Self-improvement (deferred to its own later study, per Mubarak)

- AutoDesign: Meta-Harness Optimization for Long-Horizon Agentic Design — https://www.alphaxiv.org/abs/2608.13560 (Mubarak-supplied)
- Continual Harness: Online Adaptation for Self-Improving Foundation Agents — https://www.alphaxiv.org/abs/2605.09998 (Mubarak-supplied)
- Agentic Harness Engineering: Observability-Driven Automatic Evolution — https://www.alphaxiv.org/abs/2604.25850
- Self-Improvements in Modern Agentic Systems: A Survey — https://www.alphaxiv.org/abs/2607.13104
- Harness Engineering for Self-Improvement — transcript link is MALFORMED (alphaxiv.org/abs/2607.harness-3); re-locate by title.

## 10. Providers & model adaptation (Mubarak addition)

**DISPOSITION (2026-08-18 repair pass):** deliberately deferred — no cluster file exists and none is owed yet. This section is design-input for the model-adapter plugin family, which has no papers assigned; the gathering starts when providers/model-adaptation becomes the active step. Not a silent omission.

- Model adapters: per-model prompting/capability profiles assembled from lab model cards + academic prompt-engineering research + self-improvement; applied automatically on provider/model swap. Gather the prompt-engineering paper set when this becomes the active step.
- Research-agent architectures: "so many it's not even funny" — survey when the research-profile step arrives; we build our own regardless.
- RLM appears attached to many recent papers — sweep the citation neighborhood when the context step arrives.

## Design laws the transcript proposed that look kernel-worthy (candidate CONSTANTS)

- Memory, skills, and tools are three distinct registries with different promotion rules.
- A successful run never auto-promotes into memory/skill/tool — it passes a promotion gate: reproducibility, measured benefit, scope, tests, rollback path.
- Retrieval must surface negative evidence as aggressively as positive.
- Agent-created tools go proposal → contract/permissions → sandbox → tests/replay → benchmark → versioned registry, never silently into trust.
- Certain privileges (secrets, money paths, order routing, unrestricted network) live behind a human-controlled boundary, outside anything self-improving.
