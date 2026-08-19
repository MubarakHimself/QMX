# QMA (Quantum Mind Agents) — SDK Map

Reconciled 2026-08-18 with Mubarak. Single planning document for this effort; the earlier ticket set was removed as premature. Work only inside `agentic-system-planning/` — sibling QMX folders are other agents' active work and off limits.

**Session output contract:** this session produces research + design ARTIFACTS only — no code. Mubarak exports the transcript; a separate agent documents; his software factory generates the code. UI is a separate session. Deliverable here = the framework/library (kernel + SDK) designed with no ambiguity.

**Vocabulary:** the deployable semi-profile concept is called a **mind** (renamed from "bot" — on an algorithmic-trading platform "bot" collides with trading bots). "Bot Mode" appears below only as the name of Hermes's product feature.

## Status — end of 2026-08-18

Steps 1 and 2 research are COMPLETE. The papers-side audit fixes (Memento-Skills integration, AHE/NexAU retraction with softened anti-kernel headline, corrected C13 baseline, ledger dispositions) were applied 2026-08-18 late evening. The contract draft was revised against its critic's 20 findings (v0 → revision note at top, laws K15–K19, OPEN-25–28 added); a report-only verification of that coverage could NOT run on 2026-08-18 (repeated API 529 overloads) — **tomorrow's first action: run the verification agent** (prompt preserved below in this Status section's companion note at `research/raw/contract-verification-TODO.md`), which writes `research/raw/contract-verification.md`; any leftovers it names are settled before ratification. Artifacts: `research/qma-extensibility-dossier.md` (Cordis paradigm, faithful per critic), `kernel-contract-draft.md` (v0.1 once repair lands; Part C = OPEN-decision register), `research/papers/` (9 cluster files + `kernel-implications.md`), `research/paper-ledger.md`, raw studies in `research/raw/`.

**Next session = Step 3, kernel ratification with Mubarak.** Agenda: (1) the four operator-only decisions from the paper synthesis — platform vs private system; kernel-enforced budgets + pre-action checkpoint; tool-calling convention (JSON-per-call vs compile-to-stubs) — irreversible; the emission table (reversible/compensable/irreversible per resource); (2) the ⚑-flagged OPEN items in the contract's Part C; (3) the reframe: the kernel is justified by LIVE operation + isolation + everything-via-UI, NOT by self-improvement (batch self-improvement is served by files+git+loader — both stories are in `research/papers/kernel-implications.md`).

## Destination

**QMA — Quantum Mind Agents**: the agent SDK under QMF, whose kernel makes building extensible harnesses trivial — the ability to do "what DeepSeek did with Cordis," ours. Acceptance test: creating a new harness, profile, or agent (an open-science researcher, a Delphi-like, a quant mind) is plugin assembly on the kernel — never surgery on the core. Once the SDK can do that, "the rest is simple."

## The ordered path — one step at a time, Mubarak gates each transition

**Step 1 — Study what DeepSeek/Cordis did, in depth — extensibility ONLY.** The subject is the extensibility mechanism specifically and how they pulled it off, both backend and UI; "the harness is just the extensible logic." Primary text: the Cordiverse paper, "A Programming Paradigm for Spatiotemporal Composability" (https://github.com/cordiverse/paper, draft 2026-08-13 — revertible effects, reactive coeffects, unified context, hot module replacement). Plus the DeepSeek harness docs (https://deepseek-harness.github.io/deepseek-harness/, Chinese) and the vendored Cordis framework. Since QMA's backend is Python, the study extracts the paradigm to reimplement, not code to vendor. Explicitly deferred to a later paper study: self-evolving harness, self-evolving memory, self-evolving skills. Standing operator ruling: the Cordiverse ideology applies to the agentic harness ONLY — never QML, trading node, or platform. Output: extensibility dossier + first draft of the kernel contract (Python terms).

**Step 2 — Deep academic research across the paper ledger (unbiased).** Before any kernel thinking is ratified: read the papers deeply, cluster by cluster (`research/paper-ledger.md`), with the transcript's reasoning as context. Cordis is the idea, not the end goal — papers may suggest better or simpler ways for the kernel itself, for RLM-style context, for research agents. Findings reported unbiased: contradictions with our current direction surfaced prominently. Output: per-cluster findings + a kernel-implications synthesis.

**Step 3 — Kernel contract ratification (conversation with Mubarak).** The extensibility draft (Step 1) is bent against the paper findings (Step 2) and the standing ideas below (scoped constants, RLM swap test, provider-unbiased abstractions, everything-via-UI). Reference SDKs for surface comparison: Mastra, LangChain/LangGraph/LangMem, Vercel AI SDK; folder-as-agent profile structure. Output: ratified kernel contract.

**Step 4 — Factory-ready artifacts.** Kernel + SDK design specs written with no ambiguity, for handoff: transcript export → documentation agent → software factory generates the code. We do not build here.

**Later steps (separate sessions/efforts):** UI; memory architecture; minds-in-sandboxes + Shepherd supervision; self-improvement loop; browser/HUD; harness assembly (rebuild-our-own-Hermes on the SDK); absorption of parked projects.

## Standing ideas so far (Mubarak — not yet ratified decisions)

- **Stack (Mubarak, 2026-08-18):** a mixture — Python backend (like Hermes), React/TypeScript UI, possibly Rust in hot spots (e.g. the browser, for speed).
- Kernel is the core of the SDK; extensibility is the whole point: "if I want my own version of open science, or a new agent, or a knowledge base, I shouldn't have to suffer because of how the SDK is built."
- **Profiles:** folder-as-agent, as popularized in Vercel/Mastra ecosystems (pattern credited to a creator Mubarak recalls as "Lucky Something" — identify later).
- **Minds, QMX twist:** minds are workloads launched into cloud workspaces/sandboxes (deep research, deep analysis, deep knowledge work) to offload compute and run for days; **Shepherd**-style reversible execution manages them, so a mind that breaks mid-run is recoverable. (Nous's "Bot Mode", shipped ~2026-08-17, is a chat-surface concept — per-profile named personas with own role/model/memory/skills/tools and inter-persona messaging; our mind reinterprets that as an execution concept.)
- **Self-improvement:** the harness must improve itself. Sources: AutoDesign (alphaxiv 2608.13560), Continual Harness (2605.09998), Memento-Skills (2603.18743), plus papers cited in the AlphaXiv chat transcript (C:\Users\Mubarak\Desktop\chat-harnes.txt). Academic papers are the preferred source for this design.
- **Scoped constants (Mubarak, 2026-08-18):** constants exist at levels — kernel laws (forever) → operator-declared platform constants → profile-level constants (e.g. core memory for the research profile, core tools every agent under the development profile inherits). The kernel provides the promote/demote mechanism; the operator owns the dial; a promoted constant binds every agent beneath it. Constants can be evolved manually, by self-evolution, or both.
- **"Mind" (RESOLVED rename, 2026-08-18):** the semi-profile/deployable-specialist concept is a **mind** — "bot" is banned for our concept (trading-platform collision). Applied across all session artifacts; Mubarak can swap the word anytime.
- **Provider-unbiased abstractions:** sandboxes (Modal, Daytona, e2b, possibly Google Colab-as-compute — paid, has a CLI) and computers (OpenCUA / Open Computer Use, Windows VPS) are sibling-but-distinct abstractions; the SDK is a neutral framework/library — never hardwired to a provider. Actual provider picks stay deferred.
- **Model adapters (Mubarak idea):** when a session/agent swaps provider or model, prompting adapts automatically by combining the lab's model card + prompt-engineering tactics from academic research + self-improvement. A plugin family.
- **Everything via the UI:** all creation/configuration (profiles, constants, deployments, providers) must be drivable from the UI — the reason for the Hermes-UI preference. Consequence: the SDK exposes a control-plane API as a first-class surface, not an afterthought.
- **Video-watch method (parked, for the X/UI step):** scrape the account → keep ORIGINAL videos only (skip reposts) → agents watch them via vision (most have no audio) → cross-reference with the Hermes NLM corpus. SDK first.
- **Component research per socket:** every harness component (memory, skills, tools, orchestration, self-improvement, context-at-scale) gets its own paper-grounded design when its step arrives — index: `research/paper-ledger.md` (built from the updated AlphaXiv transcript, 2026-08-18).
- **Promotion gates as law:** nothing an agent produces auto-becomes memory/skill/tool — it passes a gate (reproducibility, measured benefit, tests, rollback). Candidate kernel constant.
- **RLM (Recursive Language Models):** candidate mechanism for high-context/long-running work — book-scale knowledge bases (Firecrawl-parsed books → domain corpora, e.g. scalping across timeframes), sandboxed research minds. Paper hunt now part of Step 2.
- **Computer use:** possibly OpenCUA/CUA-family for giving agents their own Windows VPS/computer — undecided, later.
- **Browser vision:** a shared-instance browser — user and agent see the same live session; agent can take over or answer questions about anything on screen (e.g. the YouTube video you're watching). HUD follows the same logic. Likely custom build. Later.
- Scale expectation: hundreds of agents working at a go, heavy data — structure over improvisation.

## Parked (stored, deliberately not researched yet)

- https://github.com/synthetic-sciences/scientist#the-research-loop and https://github.com/synthetic-sciences — open-research loop projects; prefer their documentation over repo-diving when the time comes. Creator reportedly has better projects, e.g. "Delphi".
- X accounts @Teknium1 / @imbabybrooklyn — later down the road. First-page captures from 2026-08-18 archived: `research/raw/x-timelines-2026-08-18.md` (Bot Mode details, Hermes ports/gateways, in-app browser, gen-UI skills).
- Lean CLI — raw README extraction archived: `research/raw/lean-cli-readme-extraction.md`. For SDK ergonomics + future absorption pipeline.
- Memory projects Mubarak named from recall as "Gray box" and "Tencent Memory" — dispositioned during the 2026-08-18 repair pass as parked-by-design: names unverifiable without Mubarak, ask him when memory becomes the active step.
- Hermes deep inventory beyond what's in conversation: NotebookLM notebook `5cffee86-ad17-4913-bce4-77a90fc55ad0` (`nlm notebook query <id> "..."`).

## Out of scope

- QMF UI library build (direction only, here; library elsewhere). Backtesting library / quant frameworks. Sandbox provider selection. Live trading and strategy content. Anything in sibling QMX folders.
