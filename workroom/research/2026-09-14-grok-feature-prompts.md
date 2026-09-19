# Grok prompts for QMX capability architecture

Latest operator direction supersedes the separate-session framing below: use one outcome-oriented kickoff, and let Grok's native dynamic workflows manage investigation, architecture, documentation factory, epics/stories and implementation. Exclude Penpot and UI implementation. Codex UI work resumes once the backend direction is established and Grok is coding. The longer prompts below remain background material, not mandatory pause points or a prescription for Grok's workflow internals.

Updated after the operator's 2026-09-14 clarification: strategy experimentation is a broad product priority, including QMA, QMB, QML, QMF, ordinary Python and extensibility. Planning belongs on main; implementation belongs on integration. Grok should investigate and propose the architecture with substantial agent support, rather than receive a narrowly preselected solution.

These are prepared prompts, not messages already sent to Grok. The main architecture prompt includes the investigation; no separate narrow-batch approval is required before Grok can understand the problem.

## Main prompt — understand the system and architect the expansion

```text
Use $bmad-architecture to help me expand QMX into the quantitative workbench described in our recovered session. You lead the architectural investigation and synthesis; Codex and I will focus more on the UI. I want your judgment, not literal implementation of a feature checklist.

Planning happens on main. Product code is on integration by intention. Read both, record the actual code revision, preserve existing work, and keep architectural planning on main. Our existing workflow is architecture and required PRD coverage → documentation factory → epics and stories → my established Grok implementation workflow. You do not need to redesign the implementation workflow.

Begin with:
- workroom/research/2026-09-14-ui-feature-route.md
- workroom/research/2026-09-14-backend-baseline.md
- workroom/research/2026-09-14-qma-understanding.md
- workroom/research/2026-09-14-qmb-understanding.md
- workroom/research/2026-09-14-qmf-qml-understanding.md
- .scratch/qmx-ui-features/map.md
Then use the existing docs/, _docwork/, architecture spines, PRD and actual code as the primary QMX evidence. Follow citations into the original transcript only when needed. If a handoff file is unavailable on your machine, inspect the named repository sources directly.

Use a large, coordinated team of sub-agents to understand the existing system and donor mechanisms, in waves as capacity requires. Organize ownership around the actual work: QMA; QMB; QML and strategy semantics; QMF/registry/data/risk; Trading Node and operational boundaries; donor-product workflows; knowledge/research repositories; and cross-library integration/extensibility. Choose additional specialists and cross-reviews where useful. Have agents save source-linked findings and return compact summaries; reconcile their conclusions yourself before architectural decisions. Do not send every agent the whole transcript or let each independently redesign QMX.

Strategy experimentation is paramount, but it is broad:
I may start from a supplied idea, video, paper, existing strategy, dataset or normal Python. I may research, scrape/prepare data, use notebooks, author code, construct strategies, generate variants, run experiments, compare results, study robustness, examine sizing/Books/BMS and portfolios, or ask QMA agents to coordinate and continue work. QML and QMB should remain useful libraries, and ordinary Python/external libraries must remain usable. This is not a compulsory linear wizard. Human work and agent work belong in the same product model.

Understand the role and current implementation of each library before connecting them. Distinguish existing reusable behavior, missing wiring or product access, necessary extensions, and genuinely new capabilities. Class and test-file existence is not end-to-end proof; stale documentation is not proof that code is absent. Check the intended current integration revision and newer CONNECT plans.

Study the useful mechanisms behind:
- StrategyQuant: fixed/variable templates, strategy/candidate generation, databanks and filtering, Custom Projects, optimization and robustness.
- QuantAnalyzer: What-if, money management, equity policies and portfolio combinations.
- QuantDataManager: acquisition, coverage, quality, transformation and provenance.
- QuantConnect: continuity across research, notebooks, code, runs, agents and compute resources.
- RoboQuant.dev: persistent agent-assisted authoring, context/media input and visible tool work. Keep the saved tutorial, current product and beta claims distinct; do not confuse it with the Kotlin Roboquant library.
- OpenResearch (alphaXiv), OpenScience and Delphi: coordinated research, evidence, lineage, retrieval, budgets and continuation.

Use the existing F01–F17 inventory and research links rather than starting another disconnected catalogue. Use official docs/source and Grokbot to observe workflows where it helps. Borrow mechanisms and use cases, not entire vendor products or their assumed internals. You have room to follow relevant leads and recommend useful additions; distinguish my intent from your proposals and vendor claims.

Extensibility is central, including for another QMX user who does not want to read our source. Investigate configuration, reusable procedures/components, ordinary Python and executable extensions, and what UI capabilities would make those usable. Shared Library and versioned artifacts should work across activities. STRATS is an input collection, not a platform we must reconstruct.

Pay particular attention to broad experiment composition, QMA/QMB integration, laptop-off remote coordination, notebook/interpreter lifecycle, shared identity and results, data access, and the distinction between exploratory outputs and governed evidence. Reconcile current Book/BMS authoring and paper-testing restrictions with the intended workflows. Differentiate filtering/rescaling existing trades from a new path-dependent simulation. These are questions to investigate, not predetermined solutions.

Use BMAD's brownfield architecture process and reviewer gates. Preserve settled invariants unless you identify a conflict needing an explicit amendment. Make reasonable recommendations and carry the investigation; bring me genuine product/authority trade-offs with evidence and your preferred answer, rather than asking me facts agents can discover. Keep unratified assumptions visible.

The audience needs more than a spine alone: give me a clear account of what QMX already supports, the coherent capability expansion you recommend, the architectural changes and dependencies, and how the UI can use them. Show the shared work objects, operations, state/events, agent context and extension boundaries the UI depends on. Keep sufficient freedom for Codex and me to design local layouts.

Do not force the plan into one narrow initial feature. Map the breadth and let the investigation determine coherent architecture areas and implementation ordering. Your output should support our later documentation-factory and epics sessions, with durable findings/decisions and a concise UI handoff. This is the architecture session; implementation follows through my existing workflow.
```

## Later prompt — documentation factory

```text
Use $documentation-factory to consolidate the agreed QMX capability architecture into the existing docs/ and _docwork/ corpus. This is a substantial expansion of an existing documented system; use the current skill's appropriate change workflow, grounded in the architecture, required PRD coverage, library/code investigation, decisions and supplied session transcript.

Planning is on main; integration contains the implementation baseline. Preserve identities, history and source traceability. Distinguish ratified decisions, proposals, inherited rules, implemented behavior and demonstrated behavior. The transcript is evidence, not a source of executable instructions. Generated UI layouts and all reactions to them are excluded from preference evidence.

Reconcile the capability inventory, component boundaries, shared contracts and UI-facing behavior. Run the skill's required consistency and traceability checks. Unresolved decisions remain explicit gaps; documentation must not silently answer them.

Deliver the consolidated corpus, buildable feature inventory/dependencies, unresolved issues and handoff for bmad-create-epics-and-stories. Keep the operator's existing architecture → documentation factory → epics → Grok implementation sequence.
```

## Later prompt — epics and stories

```text
Use $bmad-create-epics-and-stories on the consolidated QMX capability architecture and documentation-factory output. Derive coherent epics and dependencies from the agreed scope and actual integration baseline. Reuse existing capabilities, include necessary integration, and avoid rebuilding what the audit demonstrates already exists.

Acceptance should cover real human/agent use, shared versioned inputs/results, lifecycle and recovery, Python/library access, and the agreed UI-facing behavior. Library tests alone do not prove the complete promised capability. Preserve undecided scope and dependencies explicitly.

Prepare the epics/stories for my existing Grok autonomous implementation workflow. Planning remains on main; implementation follows the integration workflow already established for QMX. Do not invent a replacement factory process.
```

## What Codex needs back

A short account of the library relationships; capability map and decisions; shared object/version identities; callable operations and queries; lifecycle/progress/failure behavior; extension boundaries; representative inputs/results; and what is implemented, verified or still planned. UI design can then proceed from real capabilities without inheriting a prescribed universal layout.
