# QMX Intent, Capability, and Layout Audit

**Status:** Working synthesis for the next rough sketch; not a final UX specification or approved architecture.  
**Evidence cut:** 2026-09-13.  
**Decision rule:** A user statement outranks an assistant interpretation; the latest user correction outranks an earlier tentative direction.

## 1. Coverage and chronological corrections

I inspected all 29 `response_item` records whose role is `user` in the named local session JSONL, from the first substantive September 11 message through the September 13 Sol-audit request. Ambient environment and recommended-plugin wrappers were excluded. I also inspected the assigned planning notes, targeted component documentation, harvested QMA records, and original visual references at full detail.

Coverage is complete only for those 29 local records. It does not prove that older context outside the JSONL survived as a verbatim export, nor replace hands-on verification of each donor product. Older inherited summaries were treated as navigation, not primary user evidence. Latest user clarification governs conflicts.

The important chronological corrections are:

1. **Intent preceded layout.** The opening request was to understand how QMX would actually be used day to day, with Lieflat as a chart/data reference and Penpot assets as a parts library. It was not permission to assemble a familiar quant dashboard.
2. **QMX is an active work environment.** The user described experimentation, data mining, coding, analysis, trading, and portfolio work on an ordinary laptop, with agents participating in the same work. This ruled out an oversight-only control centre.
3. **The donor-platform boundary was stated early.** StrategyQuant was called the closest product, but QMX borrows selected capabilities, not its navigation or overall layout. The same rule applies to QuantConnect and GitHub repositories.
4. **The world idea was intentionally open.** The user proposed five practitioner lenses—Researcher, Analyst, Developer, Trader, and Portfolio Manager—but also asked whether all five were needed and whether their interiors should be uniform or different. The latest answer is capability-first: interiors may differ when their work differs.
5. **Hermes was never a universal layout.** The original anchor was explicit: one agent-oriented panel does not mean every QMX area looks like it. Hermes contributes a strong agent-work arrangement; Codex contributes roomy sessions, durable work context, and independent right-side resources.
6. **The accepted sketch is a structural starting point only.** `layout-common-workspace.png` earned approval for its floating global rail, open tabs, roomy local navigation, central work area, and integrated agent/resources. Its labels, footer, chat-dominant centre, taxonomy, and aesthetics were not approved as universal.
7. **The rejected sketch failed by collapsing distinctions.** `layout-shared-working-context.png` became a generic, plain research chat/comparison page. It did not express departments/worlds, capability-specific work, or sufficiently native agent/resource participation.
8. **Another picture alone is insufficient.** A feature-bearing sketch must separate product intentionality, borrowed capabilities, and layout references. Modularity and end-user extensibility are explicit, while their first-release boundary remains open.

Original-user anchors include “VS Code for quants,” “the agents need to participate,” “one panel ... doesn't mean everything else looks like that,” and “we are building QMX, not StrategyQuant.”

## 2. Source-role and capability ledger

### What each source is allowed to contribute

| Source | Legitimate contribution | Must not become |
|---|---|---|
| StrategyQuant family | Generation templates, candidate banks, robustness procedures, What-if analysis, sizing simulation, portfolio construction, data-management ideas | QMX's global navigation, dated application chrome, or a single monolithic “StrategyQuant” screen |
| QuantConnect | Continuity among a project, code, notebooks, backtests, optimisation, deployments, compute resources, and contextual agents | A clone of its IDE, file tree, execution authority, or deployment model |
| Hermes / Codex | Agent sessions, parent/child work, roomy local navigation, durable tabs, independent resources such as browser/notebook/report | A compulsory chat centre or one global interior repeated across all worlds |
| Fincept / Hyprland / Bloomberg references | Dense composability, tiling, multi-pane focus, terminal-like information rhythm, keyboard-friendly work surfaces | Fincept's actual nav bar, Bloomberg imitation, or indiscriminate widget density |
| White dashboard image | Only the floating, narrow far-left launcher/menu | Its KPI cards, chart layout, labels, or visual content |
| Lieflat | Chart/report grammar: one clear question or conclusion per view, readable evidence, annotations, sources, and a “glance” versus “inspect” distinction | Copied code, page layout, or ornamental finance charts |
| OpenResearch / OpenScience / Delphi | Reproducible research harness ideas: bounded fan-out, immutable source capture, citations, protocols, selection, budgets, evidence, and resume | Mandatory dependency, branded UI, or proof that generated research is correct or profitable |
| STRATS | A simple shared Library mental model and inspiration for accumulating reusable strategies/knowledge | A GitHub-first file explorer or an inflated social platform |

The dictation overlay visible near the bottom of screenshots is external capture software and is explicitly not QMX UI.

### F01–F17: present status, without converting interest into approval

| ID | Capability family | Current reading |
|---|---|---|
| F01 | StrategyQuant template generation | **Specifically wanted direction.** The user liked templating, including forex-oriented templates. Adapt as typed strategy primitives, fixed/variable slots, ranges, and budgets; exact QML/QMB ownership still needs design. |
| F02 | Candidate databanks, filters, lineage | **Exploratory.** Useful for large result sets and saved views, but must not duplicate the shared Library or imply a generic KPI dashboard. |
| F03 | Custom Projects / staged procedures | **Strong exploratory mechanism.** Potentially maps to QMA Graph/Loop/task-ledger foundations; no new orchestration system is approved. |
| F04 | Robustness suite | **Specifically relevant.** Walk-forward, Monte Carlo, sensitivity, and cross-market analysis fit QMB's documented evidence model; exact supported methods and thresholds require audit. |
| F05 | QuantAnalyzer What-if | **Explicit enthusiasm.** A high-value Analysis capability. The UI must distinguish a filtered historical trade report from a path-dependent rerun under changed assumptions. |
| F06 | Money Management Simulator | **Explicitly wanted for BMS/Book work.** It should bind to exact sizing and Book/BMS versions. Rescaling a historical trade list must not be presented as a valid replay when path dependence matters. |
| F07 | Portfolio Master | **Explicit strong interest.** Candidate portfolio combinations, constraints, and evidence comparisons are relevant; QMX does not yet document a portfolio-search implementation. |
| F08 | Equity-control/result comparison | **Exploratory adjacent capability.** Useful only if it serves a concrete question and retains evidence provenance. |
| F09 | QuantDataManager ingestion | **Tentative.** The user said QDM may be useful; QMF Data already owns acquisition/provenance boundaries, so this is a UX opportunity pending capability audit. |
| F10 | Data quality/repair | **Exploratory.** Preserve raw evidence and journal repairs; do not imply destructive cleanup or a second data layer. |
| F11 | Derived data clones/transforms | **Exploratory.** Derived datasets should be reproducible and provenance-bound, not silently mutated copies. |
| F12 | QuantConnect project continuity | **Specifically wanted mechanism.** Link code, notebooks, tests, optimisation, results, and deployments around an undertaking. Whether the visible container is called Project, Workspace, or something else is open. |
| F13 | Notebook work | **Specifically requested direction.** Jupyter/open Python experimentation is a first-class tool surface, not the whole shell. Runtime lifecycle and persistence remain architecture work. |
| F14 | Contextual agents | **Core intent.** Agents should know the exact artifact, version, data, run, and local task context. A permanent right dock was only one placement proposal, not a decision. |
| F15 | Resource/compute continuity | **Core intent.** Work may continue remotely or overnight while the laptop is off. The supervisor placement and lifecycle required to make that true are unresolved. |
| F16 | Collaboration limits | **Design warning, not a requested feature.** Shared work needs explicit ownership, visibility, and conflict semantics. |
| F17 | AlgoCloud visible rules/cloud | **Low-priority exploration.** AlgoCloud was deprioritised. Visible rules may still be valuable, but this source is not adopted as a product model. |

Keep the donor families distinct: StrategyQuant covers templates/generation/candidates/robustness/procedures; QuantAnalyzer covers What-if/sizing/portfolio/comparison; QuantDataManager suggests data patterns; AlgoWizard may later inform rule authoring; AlgoCloud is weak, low-priority evidence. QuantConnect contributes continuity/contextual tooling, Lieflat evidence presentation, and OpenResearch/OpenScience/Delphi research procedure and traceability. None supplies QMX's screen architecture.

## 3. Responsibility map: perspectives, shared surfaces, and crossings

The cleanest current model is **candidate work perspectives plus shared product surfaces**, not five cloned applications or a fixed five-item commitment.

| Candidate perspective | Primary human intention | Likely local capabilities | Natural hand-offs |
|---|---|---|---|
| Research | Form questions, collect sources/data, explore hypotheses, design experiments | Source/evidence capture, datasets, notebooks, ordinary Python, bounded research procedures, experiment definition | An experiment package to Analysis; reusable artifact to Library |
| Analysis | Produce and compare deterministic evidence | Candidate/result sets, robustness, What-if, sizing studies, portfolio studies, annotated evidence views | Validated evidence to Development or Portfolio work; decisions back to Research |
| Development | Define and refine executable strategy logic | QML bot declarations plus plain Python logic, parameters/confluences/footprints, versions/diffs, conformance, test evidence | Versioned candidate to Library; exact variant for review/promotion |
| Portfolio work | Construct combinations and propose governed configuration | Portfolio comparisons, constraints, Book/BMS proposals, sizing comparisons, change impact | Exact proposed Book/BMS version to governed review; never silent activation |
| Trading | Operate and understand the integrated Trading Node | Positions, orders/events, risk read models, Books/BMS, paper/live state, approved powers, incident evidence | Operational evidence back to Analysis/Research; human-controlled activation |

QMA's documented `pm` role means **Product Manager**, so a Portfolio Manager perspective must not rename it. QMA's Desk → Role → Quant → Agent → Subagent hierarchy is an authority/execution ontology, not evidence for five UI departments. A display Profile may collapse desks without changing identity or permissions.

These should **not** be departments:

- **Library** is a shared, versioned discovery and provenance surface for strategies, bots, templates, results, datasets, procedures, Books/BMS, and related artifacts. It is not a Git repository browser.
- **Trading Node** is the integrated paper/live operational product area containing Books, BMS, risk, and runtime evidence. Whether it appears beside perspectives in the global launcher or under the Trading perspective is still a topology decision.
- **Experimentation** is a cross-perspective capability, not necessarily a destination.
- **QMA, QMB, QML, and QMF** are component boundaries, not user navigation labels.
- **Agents, resources, browsers, notebooks, charts, tasks, and files** are tools or resources that a local interior can host.
- **Project/workspace/undertaking** is a continuity container whose visible terminology is unresolved.

Cross-area work must preserve object identity rather than copy screens. A Research experiment can open in Analysis with the same dataset and hypothesis references. An Analysis sizing study can produce a proposed BMS version without changing the Trading Node. A Development change branches a QML bot version, with conformance/evidence attached, and a human later approves the exact variant and intended Book. Operational evidence can return to Analysis as a new run, never as a rewritten historical result.

## 4. Modular and end-user-extensible UI boundaries

This section separates documented foundations from design proposals.

### Stable shell — user intent and UX proposal

The stable shell should own cross-world concerns: the floating launcher, open-work tabs, restoration of tabs/local arrangements, context/search/command access, and a host for local tools/resources. “Stable” means consistent orientation and state semantics, not identical interiors.

The shell should not own research metrics, a universal chat layout, a generic widget dashboard, or the business logic of a contributed capability. Each work perspective may assemble a different interior from compatible surfaces.

### Contribution boundaries — proposal, not an existing UI SDK

QMX will probably need these separately evolvable contribution classes:

1. **Tool surfaces:** notebook, editor, candidate table, What-if builder, comparison, chart inspector.
2. **Artifact renderers:** safe kind/version views for bots, results, datasets, evidence, templates, Books, or BMS, with a read-only fallback.
3. **Contextual actions:** commands valid for the selected object and permission boundary.
4. **Agent resources:** task/session/run/ledger views bound to exact inputs/outputs, not an unscoped assistant panel.
5. **Saved compositions:** user-arranged tools or capability workbench templates, not copied departmental shells.

These are design requirements only. QMA explicitly has **no `ui_view` contribution in v1**; the UI SDK and `qma-ui-contract` are deferred under GAP-0081. QMA's current contribution/lifecycle model for tools, skills, graph templates, workers, and related resources is useful backend precedent, not proof that UI extensions already exist. Its marketplace/trust-tier/install-count ideas and capability-solver contracts were explicitly cut and must not be revived under the name of extensibility.

### Exact context and version binding

Every tab, resource, and agent task should identify its undertaking, artifact version/fingerprint, data cut or split, run/configuration, relevant perspective/Desk identity, execution target, and granted capabilities. Starting a task pins that context. Selection changes must not silently retarget running work; attaching or rebinding is explicit. Stale, superseded, missing, or incompatible inputs remain visible.

This matches documented foundations: QMA tasks are transcript-independent and carry exact references, evidence, acceptance, and durable ledgers; QMB resolves fingerprinted configurations and emits canonical evidence; QML bots and Registry artifacts are versioned; Books and BMS are immutable version graphs with structured, UI-editable configuration and change-admission impact.

### Three levels of extensibility

These levels should not be conflated:

- **Configuration:** edit parameters, flags, preferences, and structured Book/BMS/template values. It should be validated, versioned when it changes product truth, and show admission or restart impact.
- **Composition:** arrange compatible tools, bind artifacts, save workbench arrangements, and connect validated procedures. Composition must not grant new execution power.
- **Executable extension:** install or run code, adapters, agent tools, or resource providers. This is a privileged boundary requiring explicit provenance, compatibility, permissions, resource budgets, secrets/network scope, lifecycle control, and failure isolation.

The first-release boundary between these levels is unratified. No concrete manifest, API, marketplace, or capability solver should be invented during sketching.

### Lifecycle and containment questions the architecture must answer

A credible modular surface must cover compatibility, job states, resource budgets, detach versus cancel, restart persistence, version negotiation, migration/unload behaviour, crash containment, and a safe fallback renderer. A broken pane must not take down the shell; removing a contributor must not make durable artifacts unreadable.

Permissions must be least-authority and context-specific. QMA narrows capabilities by role, mission, parent, and money-path reachability, emitting only candidate artifacts toward that path. Trading Node v1 has no agent execution control. Configuration, promotion, and activation are separate human acts; paper and live remain explicit.

Remote work also needs honesty. QMA documents multiple execution environments and persistent/ephemeral jobs, but a workstation-bound supervisor cannot continue after the laptop is off. The UI may promise remote/overnight continuation only after durable supervision is assigned. Docker support does not make Docker mandatory for end users.

## 5. Brief for one next feature-bearing sketch

Create **one Analysis / What-if workbench**, not a universal shell diagram or feature inventory dashboard. It preserves the accepted shell while proving that a non-Research interior can be capability-specific. F06 and F07 appear only as neighbouring Analysis work categories, not competing cards.

### Include

- A narrow floating far-left launcher. Show the active destination as **Analysis**, while treating other icons/labels as illustrative candidates rather than a ratified five-world roster. Shared Library and the integrated Trading Node may be visible, but their final hierarchy must remain visually noncommittal.
- Durable top tabs representing actual open work, for example a Research experiment, an active Analysis What-if study, and a Trading Node view. Tabs should persist context; they are not a StrategyQuant-style product menu.
- A roomy Analysis-local left column organised around studies and saved work: recent comparisons, robustness work, sizing studies, and portfolio studies. The active item is one What-if study with an explicit pinned baseline.
- A centre work surface focused on one question. It should show the baseline artifact/run, scenario definition, changed assumptions, and comparison/evidence output. The methodological mode must be unmistakable: **filtered historical report** versus **rerun required/completed under changed assumptions**. If there is no real run, show an honest empty or pending state instead of invented Sharpe, P&L, or win-rate figures.
- A resizable right resource area with interchangeable evidence/methodology, notebook/report, and agent-task resources. The agent card should name its exact bound baseline, scenario/config version, and task status. It may expand into conversation or task detail, but chat must not consume the primary work surface.
- Lieflat-inspired evidence hierarchy: one question, legible comparison, annotation/provenance, and clear progression from glance to inspect. Use neutral structural placeholders at this sketch stage.
- Visible modular seams: individual tools/resources can be opened, closed, resized, restored, or replaced without making the page look like a free-for-all widget dashboard.

### Omit

Do not include StrategyQuant navigation, KPI cards from the white reference, a generic grid of every borrowed feature, a linear “Explore → Build → Validate” footer, fake financial results, Git/file-explorer chrome, RoboQuant Plan/Act, dictation controls, a global green health claim, direct agent/live trading controls, or all five candidate perspectives as if ratified. Do not render F05, F06, and F07 simultaneously; F05 is the active capability and the others are discoverable local work types.

The sketch should answer: **Can QMX keep a recognisable shell while Analysis becomes a context-bound evidence workbench rather than a reskinned Research chat?** It should not settle final aesthetics or taxonomy.

## 6. Planning path that remains valid

The earlier process still holds, with the current audit as a correction gate:

1. Finish the breadth-first responsibility map and capability ledger, retaining wanted/exploratory/rejected status and ownership.
2. Form coherent BMAD planning/architecture batches covering UX, data, API, backend, execution, evidence, permissions, and lifecycle. Batch by responsibility and risk.
3. Run Documentation Factory separately against the exact transcript/source set, reconciling ratified decisions without treating sketches as authority.
4. Derive epics and stories after the key UX/architecture boundaries are explicit.
5. Give Grok a bounded implementation plan based on those artifacts, not screenshots alone.

This work is not ready to become a final UX specification. There is no Monday deadline and no justification for compressing discovery into premature implementation.

## 7. Actual unresolved decisions worth user attention

1. **Top-level topology:** Are Research/Analysis/Development/Trading/Portfolio the user-facing launcher destinations, with Library and Trading Node nested or shared, or may Library/Trading Node sit beside a smaller set of practitioner worlds?
2. **Tab semantics:** May one top tab open a world, another a concrete study/artifact, and another the Trading Node, or should the shell separate destination tabs from nested local work tabs?
3. **First-release extensibility:** Should end users initially extend configuration and saved compositions only, or must they also install executable tools/adapters in the first release? The latter changes the permission, isolation, migration, and support architecture substantially.

Those are genuine decisions. Floating-left routing, durable work tabs, capability-specific interiors, a shared Library, integrated Trading Node, contextual agents, and deferred aesthetics no longer need to be re-litigated.
