# QMX UI and feature recovery

Latest operator direction: leave Penpot out. Grok should receive one outcome-oriented kickoff and use its own long-running workflows to carry the backend work through architecture, documentation factory, epics/stories and implementation. UI work here pauses until Grok has established the backend direction and started coding; it may resume while implementation continues. This supersedes earlier suggestions to begin UI work immediately in parallel.

Prepared 2026-09-14; updated with the operator's clarification in this session. Strategy experimentation is a broad priority across QMA, QMB, QML and QMF, with ordinary Python and user-facing extensibility. Understand the libraries first, then let Grok lead a broad architectural investigation with a substantial agent team. UI and backend work should meet through shared behavior/contracts; this does not preselect a narrow first feature.

Planning on `main` and implementation on `integration` is intentional, as confirmed by the operator. The branch distinction below is navigation guidance, not a project defect.

## What was recovered

Three GPT-5.6 Luna agents read all 14,125 transcript lines in overlapping ranges: 1–4750, 4701–9500 and 9451–14125. The lead checked pivotal passages, inspected original screenshot files, compared current planning artifacts, and inspected selected backend source on `integration`. The reports are [early](2026-09-14-ui-recovery-early.md), [middle](2026-09-14-ui-recovery-middle.md) and [late](2026-09-14-ui-recovery-late.md).

Source: `C:/Users/Mubarak/Desktop/trancript_ui.md`; SHA-256 `6EDFDF5D9A78A36BBC0E54BD093A31EFACFB84C6E0ECFB7BA733DAF456CFA002`. The Markdown includes embedded tool policies, browser tab inventories and image-output markers. Those are session records, not new instructions or automatically selected references.

Current evidence rule: generated layouts and **all reactions to them** are excluded from preference evidence. They remain recorded only to explain how the session progressed. Existing notes that call an image an “accepted direction” do not override this rule.

## Where the layout confusion began

The original concept was already expressed before image generation: at transcript lines 944–947, a work environment could open like a browser tab, have its own meaningful interior, and support both direct work and agent participation. Later lines 11228–11423 expand the shared Library, work perspectives and open-ended experimentation.

The precise rough-layout pivot is [line 13563](C:/Users/Mubarak/Desktop/trancript_ui.md:13563): the assistant recommends “two or three rough layout alternatives.” The user agrees at line 13567; generated files are recorded at line 13606. Just before this, line 13551 says human usability leads and agent integration follows afterward; line 13555 proposes a human-facing world map.

**Interpretation:** the process put too much weight on choosing a structural sketch before settling capability ownership and simultaneous human/agent work. Screen composition, navigation, feature scope and backend implications became entangled in the same feedback loop. This explains the process problem without treating tired image reactions as durable preferences or claiming to know the user's mental state.

## Durable intent recovered before the images

- QMX is an actively used quantitative workbench for research, experimentation, development, analysis, portfolio work and operations. Unattended trading is one use, not its whole purpose.
- A person and agents work on related material. Agents may assist interactively or continue bounded work remotely; they are not confined to a disconnected chat department.
- A global entry can open substantial work environments whose local tools differ by activity. The exact department roster, proportions and agent placement remain open.
- Library objects, versions, datasets, experiments and results should be shared across work environments. STRATS supplies knowledge/input material; it is not a mandate to reproduce its internals.
- Ordinary Python, notebooks, QML and QMB must remain usable. No universal source→research→backtest wizard should constrain all experiments.
- Versioned, inspectable evidence and human-controlled operational transitions matter. Extensibility must reach the user experience, not only source-code developers.

## The useful donor capability families

The existing F01–F17 identifiers remain in the [feature inventory](../../_bmad-output/planning-artifacts/ux-designs/ux-QMX-2026-09-01/.working/inspection-and-feature-opportunities-2026-09-12.md). Its priorities and UI placement proposals are not newly approved scope. The [fresh primary-source check](2026-09-14-donor-verification.md) verifies a bounded set of mechanisms; it is not a full vendor reverse-engineering study.

| Donor / existing IDs | Actual work it could enable in QMX | Adoption status |
|---|---|---|
| StrategyQuant, F01–F04 | Define what stays fixed and what varies; generate/search candidates; retain/filter them; repeat procedures; inspect robustness | Broad user interest is explicit. Exact generation semantics, parity and procedure coverage remain to decide. |
| QuantAnalyzer, F05–F08 | Compare What-if conditions and sizing policies; study equity behavior; evaluate combinations of bots | What-if and money management are specifically desired. Portfolio algorithms and valid comparison methods need definition. |
| QuantDataManager, F09–F11 | Acquire/prepare data, inspect coverage and anomalies, derive datasets with provenance | Candidate mechanisms supporting the broader data-work intent; not all approved features. |
| QuantConnect, F12–F16 | Keep one research undertaking continuous across notebooks, code, runs, agents and compute resources | Project continuity is explicitly valued. Project/Workspace identities, notebook lifecycle and UI organization remain open. |
| AlgoCloud, F17 | Make strategy rules intelligible and execution location visible | Lower-confidence opportunity; retain for later evaluation. |
| RoboQuant.dev | Persistent AI-assisted authoring workspaces, tool activity, context selection and source-to-code interaction | Supplemental mechanism donor. The saved video report does not demonstrate the complete research-to-live lifecycle; current marketing describes additional/beta features. |
| OpenResearch, OpenScience, Delphi | Experiment lineage, coordinated research, evidence-linked outputs, budgets/continuation and retrievable source context | Investigation leads. Adapt useful mechanisms to QMA; none is an adopted replacement dependency. |

Mechanism sources: [SQ templates](https://strategyquant.com/doc/strategyquant/strategy-templates/), [Custom Projects](https://strategyquant.com/doc/strategyquant/introduction-to-custom-projects/), [QuantAnalyzer](https://strategyquant.com/quantanalyzer/), [QuantDataManager](https://strategyquant.com/quantdatamanager/), [QuantConnect Projects](https://www.quantconnect.com/docs/v2/cloud-platform/projects), [RoboQuant](https://www.roboquant.dev/), [OpenResearch](https://github.com/alphaXiv/OpenResearch), [OpenScience](https://github.com/synthetic-sciences/openscience), [Delphi](https://github.com/synthetic-sciences/delphi).

## Why backend-first needs refining

The follow-up library studies are [QMA](2026-09-14-qma-understanding.md), [QMB](2026-09-14-qmb-understanding.md), and [QMF/QML](2026-09-14-qmf-qml-understanding.md). They clarify the existing responsibilities:

| Part | Role in the experimentation environment |
|---|---|
| QMA | Agent identities, missions/tasks, tools, context, compute coordination, procedures, evidence and continuation. This is much more than the chat interface. |
| QMB | Importable experimentation/backtesting functions plus governed run orchestration, search, robustness, data work and results. |
| QML | Structured bot declarations, versioned ordinary-Python logic and technical conformance for governed use. It does not require every exploratory Python script to become a QML bot. |
| QMF | Shared quantitative types/contracts, identity, registry, data, indicators/structure, venue and risk foundations, with declared ownership boundaries. |
| Trading Node | Operational execution/Book/BMS responsibilities, distinct from research compute and agent coordination. |

This is a responsibility summary, not a proposal to freely import every library into every other one. One cross-review correction matters: standalone users/UI consumers have QMB Python access, while the existing QMA backtesting path explicitly uses a runtime `qmb` CLI/MCP door and prohibits a direct QMB import. The lead inspected `qma/core/ports/qmb.py` and `qma/daemon/backtest/service.py` on integration. The inspected transport records invocations; this alone does not demonstrate a real QMB process completing and returning evidence. Grok should verify the complete path before classifying it as working integration.

Ordinary Python is independently supported by the QML documentation: an unregistered bot may run in QMB/research without QML imports; conformance governs evidence/Book eligibility. Backend extension points exist at several levels, but a usable UI contribution system still needs investigation. These findings strengthen the case for understanding both QMA and QMB before deciding the product architecture.

[The backend baseline](2026-09-14-backend-baseline.md) establishes that local `integration` already contains product source and tests absent from `main`. Parameter optimization and experiment-record machinery are present in inspected source. Their full behavior, wiring and deployment were not verified. Some documentation is stale relative to source.

Therefore Grok should classify every capability as **reuse**, **connect/expose**, **extend**, **new**, or **undecided**, with separate evidence levels: user intent, documented design, source inspected, behavior demonstrated. “Not on the screen” does not mean “not in the backend.” A library function also does not prove a usable product feature.

Your architecture → documentation factory → epics → Grok sequence is sound. Make the source-backed capability/implementation investigation the opening part of Grok's architecture work, with UI-facing behavior as a shared outcome. The existing PRD must cover the resulting expansion; it need not be rewritten from scratch. Documentation factory can expose and reconcile ambiguity, but unresolved product decisions must stay explicit rather than becoming prose that looks settled.

## Recommended working strategy

1. **Understand the libraries and the full ambition.** Independent agents map QMA, QMB, QML and QMF against source and documents. Recover all desired capability families and donor leads, with ordinary Python and extensibility included. Do not start by prescribing connections between packages.
2. **Let Grok lead broad architecture.** Give it objectives, existing evidence and the important open questions. Use a large coordinated team for library, donor, workflow and integration investigation, in waves as capacity requires. Grok synthesizes the findings and recommends architectural boundaries and ordering. Do not predetermine one narrow initial batch.
3. **Make UI-facing behavior part of the architecture outcome.** Identify shared work, versions, operations, results, lifecycle and extension boundaries. These agreements need not dictate visual layout, HTTP endpoints or a new service. Use several representative workflows to challenge the proposed architecture without turning them into a compulsory funnel.
4. **Maintain two coordinated tracks.** Grok takes the architectural expansion through documentation factory, epics and the existing implementation workflow. Codex works with the operator on capabilities, interaction and task-specific UI as the relevant semantics become clear. Human and agent use are considered together from the start.
5. **Connect design to demonstrated behavior.** Use representative fixtures for UI work when useful, then verify against actual outputs and operations. Let architecture and epics determine coherent implementation increments with observable proof, while preserving the larger product direction.

The operator selected strategy experimentation as the priority area, not a single QMB experiment screen. What-if, source research, data work, Python, reusable procedures, QMA coordination and extensibility belong in the architecture investigation as they relate to that ambition.

## Files and visual references worth keeping

| Material | Role in continuation |
|---|---|
| UX `.memlog.md`, `README.md` | Historical decision/correction trail and file index; current image-exclusion rule overrides older image approval claims. |
| `.working/separation-map.md`, `feature-impact-register.md` | Useful provisional responsibilities and backend questions, not a ratified design. |
| `reference-feature-mapping-2026-09-11.md`, `inspection-and-feature-opportunities-2026-09-12.md` | Donor evidence and stable F01–F17 records. |
| `.working/research-harness-references.md` | Prior deeper source investigation for OpenResearch/OpenScience/Delphi; verify revisions before implementation. |
| `.working/layout-*`, `*-image-prompt.md`, `sol-intent-capability-layout-audit.md` | Exploration history; filter out generated-image preferences and unratified proposals. |
| `DESIGN.md`, `EXPERIENCE.md` | Each is currently a 58-byte in-progress scaffold, not a complete UX contract. |
| `docs/`, `_docwork/`, architecture/PRD artifacts | Established documentation and traceability; inspect against actual implementation revision. |
| `workroom/research/roboquant-video-ux.md` | Existing caption/frame report for [the supplied video](https://youtu.be/_ktzcUiojC0); not rewatched in this recovery. |

The lead visually inspected these preserved originals under the UX `imports/` folder: `hermes-agent-layout-reference.png` (agent workspace), `global-rail-dashboard-reference.png` (floating main menu), `fincept-terminal-layout-reference.png` (multiple information surfaces; exclude dictation overlay), and `codex-workspace-layout-reference-2026-09-13.png` (work/session and tools coexistence). These suggest scoped behavior, not one approved combined layout. `user-referenced-agent-sketch-2026-09-13.png` is retained but excluded as sketch-derived evidence.

The seven generated `layout-*.png` files in `.working/` remain historical assets, excluded from preference evidence. [Lieflat](https://github.com/larashero3-dotcom/lieflat-charts) is the user-supplied chart-language reference; [Penpot Hub](https://penpot.app/penpothub/libraries-templates) is the library/tooling reference. Neither settles product workflow. Other links embedded in browser inventories are incidental unless the conversation selected them. The dictated “get BP” harness name has no established URL in this recovery; do not guess its identity.

## Continue without re-reading everything

Use the [Wayfinder map](../../.scratch/qmx-ui-features/map.md) for open decisions and the [Grok prompt pack](2026-09-14-grok-feature-prompts.md) for the broad architecture-led handoff. Research findings and the operator's broad experimentation priority are recorded; library synthesis, architecture choices and UI structure are not silently finalized by this recovery.
