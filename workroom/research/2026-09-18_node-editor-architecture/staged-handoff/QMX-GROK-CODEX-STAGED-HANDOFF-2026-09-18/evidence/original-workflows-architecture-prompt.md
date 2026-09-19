# Prompt 2 — QMX Workflows and its Workflow Canvas

Use the installed `bmad-architecture` skill for a broad, creative brownfield investigation in `C:/Users/Mubarak/Desktop/QMX`. You are Grok 4.6, acting as my technical lead. Design how reusable, inspectable workflows should fit into QMX and what backend work makes a future visual composer possible.

The user has accepted **QMX Workflows** as the product direction's name. **Workflow Canvas** and connected **steps** are proposed interface terms. The existing **Trading Node** is a separate concept. n8n is inspiration for composition and visibility; adopting its software, runtime, or object model is an architectural option to evaluate, not a settled requirement.

This is an architecture session. Documentation Factory, epics/stories, and production implementation will occur in separate sessions. Codex and I will develop the UI alongside this backend work. Use the architecture skill's fast drafting path, with explicit assumptions and a reviewable recommendation. Produce both the architecture spine and enough supporting explanation for the downstream agents and me to understand the choices.

I will start the sessions manually. End this session with the Documentation Factory handoff prompt, including an instruction for that later session to produce an epics/stories handoff. My existing automation handles work after epics/stories; you do not need to launch those sessions or organize that automation.

## Investigate and expand the idea

**Treat this brief as a seed for your own investigation.** Conduct your own research and studies: inspect the live repository state, trace actual behavior, consult current primary sources, and run relevant diagnostic experiments. Independently verify the supplied reconnaissance. Follow evidence into adjacent capabilities, generate additional use cases, and propose better approaches wherever justified. Assess impacts across QML, QMB, QMA, QMF, the Library and the future UI. The desired outcome and explicit user constraints govern; the examples, suggested investigation topics, and preliminary findings do not cap exploration or prescribe the answer.

Choose your own research plan, agents, and dynamic workflows. Explore beyond my examples and challenge weak premises. You may use installed BMAD CIS brainstorming or problem-solving capabilities where they help. Keep a distinction between the broad opportunity space, your recommended scope, and my accepted requirements. Group meaningful open decisions for review after doing the independent investigation; automated artifact approval does not answer them.

I want to compose the capabilities QMX already has, plus justified additions. Workflows may involve agents, ordinary Python, deterministic tools, human decisions, or combinations. They can be exploratory and temporary, saved as reusable procedures, or executed repeatedly. Some work should continue on a server after the laptop closes. The interface should make the work understandable and inspectable without making visual editing compulsory.

Use these as starting scenarios, then discover and prioritize others:

- Take a Library strategy and compare it against different research Book configurations or parameter sets, retaining exactly what changed and why.
- Run QMB what-if scenarios, sweeps, robustness studies, or custom experiments and inspect comparable evidence.
- Have a Co-Pilot or department team propose a workflow, let me understand/edit it, and reuse the accepted version.
- Collect sources, annotations, hypotheses, and results on a research board; make executable work possible without forcing every note into a runnable step.
- Fan out a study across data slices or instruments, collect results, branch on a meaningful condition, and resume after an interruption.
- Revisit evidence when inputs change, reuse part of a workflow, or schedule bounded research with notifications only when useful.

Consider further opportunities, their product value, and their actual architectural cost. Retain QMX's open laboratory character: fresh research, an agent, and a fixed sequence of stages are all optional.

## Establish the existing foundation first

Load the output of the preceding STRATS-to-QMX Library architecture session, including its accepted/proposed status, requirement identifiers, artifact contracts, and open questions. If that session is still underway, investigate independent areas and state provisional dependencies explicitly; do not invent its decisions.

Read applicable instructions, `docs/AGENTS.md`, the constitution, glossary, component/dependency manifest, related spines/ADRs, contracts, gaps, and current stories. Inspect actual implementation and tests across the relevant branches/worktrees. At brief preparation, the root was the planning checkout on `main`, with implementation also on `integration`; re-resolve current locations and record revisions. Preserve concurrent changes.

Audit QMA graphs, jobs, routines/procedures, continuation, execution environments, wire and event surfaces, ExperimentSpec/ledger, extension packages, and knowledge/artifacts; audit QMB experiment, analysis, search and execution doors; audit QML authoring and the QMF registry/data/risk foundations. Reuse owners and implementations where they fit. Investigate any mismatch before proposing another runtime, scheduler, storage model, or service.

Bounded source reconnaissance on `integration@1b451a8` found substantive starting points: `qmx-agents/packages/qma-daemon/src/qma/daemon/taskgraph/`, `experiments/sqlite.py`, `backtest/service.py`, and `process.py`; QMB includes `qmb/workbench.py`, `analysis/project.py`, `analysis/rerun.py`, `sweep/batch.py`, and `robustness/walkforward.py`. Resolve the exact current paths in that checkout. The `qma-ui-contract` area was still a stub in the inspected UI worktree. No end-to-end run was performed for this reconnaissance. Some documentation still describes missing behavior for which source files now exist: reconcile that discrepancy with real execution evidence instead of repeating either claim uncritically. Explicitly revisit GAP-0061, GAP-0062, GAP-0063 and GAP-0085.

The current docs give QMA candidate-artifact authority and reserve account execution for the Trading Node. Workbench decisions also specify particular QMA/QMB doors and reject a central experiment service. Read the exact current rulings. Show how research automation, deterministic production automation, human promotion/activation, and live operation would relate. If useful capability needs a law or boundary to change, present that amendment and its consequences explicitly; neither the canvas nor a workflow step silently grants new authority.

## Architectural questions to resolve

Develop a coherent recommendation covering these concerns wherever the intended behavior requires them. Add issues the audit reveals; this list is not an implementation blueprint.

1. **Composition and extensibility.** Workflows compose capabilities; extensions add capabilities. Determine the shared registration/discovery and contract surfaces that connect them. Consider backend capabilities, agent tools, typed step inputs/outputs, and UI contributions without conflating their lifecycles or authority. Explain the legitimate role of JSON Render and MCP Apps using current primary documentation.
2. **Definition and execution.** Distinguish editable drafts, immutable runnable versions, executions, step attempts, outputs, and presentation layout. Determine typed connections, validation, loops/branches, subflows, concurrency, human intervention, and how much belongs in the first usable increment. Test whether existing representations can carry these semantics.
3. **Durable work.** Resolve ownership and persistence across submission, scheduling, progress, interruption, cancellation, retry, checkpoint/restart, laptop disconnection, and remote execution. Explain duplicate side-effect handling, partial results, resource budgets, and recovery rather than assuming a graph on screen solves them.
4. **Evidence and reuse.** Preserve source/data/code/configuration versions and result lineage. Distinguish deterministic calculation from stochastic agent work and genuine reruns from projections of existing results. Library references and reusable procedures must retain useful identity and history.
   Distinguish the STRATS strategy-meaning graph, the authored procedure graph, runtime task/attempt state, and the visible canvas arrangement. Their different meanings may warrant different representations even when the interface connects them.
5. **Human and agent participation.** Define who can propose, edit, validate, execute, inspect, and change ongoing work. Agents should use the same supported contracts where appropriate. A main conversation, a compact contextual assistant, and a canvas are different views onto work, not competing sources of truth.
6. **UI connection.** Specify the commands, queries, progress/events, errors, validation messages, discovery metadata, and reconnect behavior needed by the browser UI and later desktop host. Separate backend requirements that can be implemented now from visual choices that our UX session must make. Audit the actual adapter/wire readiness.

Use current primary sources when assessing n8n or alternative graph/composition/editor approaches. Compare adaptation, embedding, and implementing a suitable QMX representation against actual requirements and licensing. Choose based on fit; do not bind a technology because its canvas resembles a reference screenshot.

## Completion and handoff

Produce a reviewed BMAD architecture package with the current-state audit, opportunity/use-case map, alternatives, recommended design, exact owner/contract changes, prerequisite requirements, and unresolved decisions. Trace several complete representative journeys from creation through result inspection and reuse, including interruption or failure. These are architectural examples for review, not final screen designs.

Provide an implementation sequence that makes useful work available incrementally, with a proposed first vertical slice and observable acceptance criteria. Classify what already works, what is merely documented, what needs wiring, and what requires new design. Give the UI session a concrete readiness map and list what it can design now.

End with an exact artifact/revision manifest and a next-session prompt for `documentation-factory`, which will integrate the accepted changes into the existing knowledge base. The downstream epic pass needs traceable requirements and dependencies; identify or produce the appropriate requirements addendum rather than relying on stale scope. Subsequent implementation will verify real user-facing flows with Reticle and backend persistence/execution checks. Generated diagrams, passing isolated unit tests, and mock UI results alone do not prove a runnable workflow.

I want useful implementation work to be able to progress tonight. Recommend the best supported slice and expose its actual blockers; do not promise that the entire platform, visual designer, and desktop delivery will all finish tonight.
