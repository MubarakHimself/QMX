# Durable operator intent — QMX strategy experimentation

Date: 2026-09-14. Architecture input only. Not a layout, UI contract, or implementation plan.

Evidence rule: generated layouts and **all reactions to them** are excluded. Penpot is out of scope. Screen composition is not prescribed here. F01–F17 are a **mechanism inventory**, not approved UI scope.

Sources (priority order): `workroom/research/2026-09-14-ui-feature-route.md`; recovery early/middle/late; `2026-09-14-grok-feature-prompts.md`; `.scratch/qmx-ui-features/map.md` + issues/01, 02, 07; F01–F17 inventory; `2026-09-14-backend-baseline.md`. Standing laws from `_BRIEF.md` are inherited, not reopened.

## Compact status

| Topic | Status | Evidence |
|---|---|---|
| Broad strategy-experimentation priority (not one narrow screen) | **Settled intent** | user-intent |
| Non-linear entry; no compulsory wizard | **Settled intent** | user-intent |
| Human + agent in the same product model | **Settled intent** | user-intent |
| Ordinary Python / notebooks / QML / QMB coexistence | **Settled intent** | user-intent |
| Shared Library + versioned artifacts across activities | **Settled intent** | user-intent |
| STRATS = input/knowledge collection, not a platform to rebuild | **Settled intent** | user-intent |
| User-facing extensibility (including non-source readers) | **Settled intent** (depth open) | user-intent |
| Exact world roster / Project vs Workspace / agent placement | **Open** | undecided |
| Strategy generation: params vs logic/structure | **Open** (needs AD) | user-intent + source-inspected |
| Paper-before-promotion path vs node/QMA boundaries | **Open** (needs AD) | user-intent + documented-design |
| Laptop-off remote continuation ownership | **Open** (needs AD) | user-intent + documented-design |
| What-if: trade-list filter vs path-dependent rerun | **Open** (needs AD) | user-intent + documented-design |
| Book/BMS candidate-authoring vs QMA money-path prohibitions | **Open** (needs AD) | user-intent + documented-design |
| First-release extensibility contract depth | **Deferred** until architecture maps owners | undecided |
| Exact donor mechanism parity (F01–F17) | **Deferred** feature-by-feature | mechanism inventory only |
| Local screen composition / chrome | **Out of scope here** | excluded |

---

## 1. Jobs the operator actually wants to do

These are durable **jobs**, not screens. Entry points and sequencing are free (see §2).

| Job | Operator meaning (durable) | Source |
|---|---|---|
| Start from heterogeneous inputs | Idea, video, paper/article, existing Library/strategy item, dataset, or ordinary Python — not only a blank strategy form | `2026-09-14-grok-feature-prompts.md:27-28`; late recovery `11423` |
| Research / hypothesis sourcing | Actively used workbench for research and data mining; agents may participate; unattended trading is one mode, not the whole product | early `L813–L814`, `L944–L947`; route `26-28` |
| Data prep | Acquire/scrape/ingest, inspect coverage/quality/anomalies, derive datasets with provenance; data work supports experiments | early `L945`; F09–F11 inventory; route donor table |
| Author | Write and iterate ordinary Python, notebooks, and/or QML-structured bots; QML does **not** require every exploratory script to become a QML bot | route `58-59`, `64`; late `11290` |
| Generate variants | Freeze what stays fixed, vary selected parts; retain/filter candidates; genetic/batched generation of interest — exact generation semantics still open | F01–F02; middle SQ templates; route `40` |
| Run experiments | Custom, repeated, batched, agent-assisted runs: backtests, optimization, procedures with stages/loops — not one fixed pipeline | late `11423`, `13375`; F03; QMB role in route `57` |
| Compare | What-if conditions, result comparison, equity/policy deltas against a named baseline | middle QA What-if; F05/F08; route `41` |
| Robustness | Walk-forward, sensitivity, Monte Carlo, cross-market / changed-assumption survival | F04; backend baseline walk-forward source |
| Sizing / Book / BMS / portfolio | Money-management and sizing policies; propose Book/BMS variants; combination/portfolio study — research proposes, human promotes | middle F06–F07; late `11423`; brief standing laws |
| Agent continuation | Interactive assistance **and** bounded remote continuation after laptop shutdown; agents share selected artifact versions and produce derived versions | early `L945–L947`; late `11423`, `13375–13379` |
| Governed handoff | Versioned evidence; human approval; strategy variant assigned to intended Book before live; paper testing precedes promotion; only human promotes into live zone | late `11423`; `_BRIEF.md` standing laws |

**Product shape (settled):** QMX is an actively used quantitative workbench spanning research, experimentation, development, analysis, portfolio work and operations — StrategyQuant-like breadth extended with QMX agents and other capabilities, not a chat app with a trading add-on (`2026-09-14-ui-feature-route.md:26-32`; early `L944`).

---

## 2. What must remain non-linear

**Settled:** there is **no** compulsory universal wizard and **no** forced research → development → analysis funnel.

- Inputs may arrive in any order and form (video, paper, library item, raw idea, fresh research, Python, dataset) — late `11423`; grok prompts `27-28`.
- Experiments may be custom, repeated, batched, genetic, or agent-composed — late `11423`, `13375`.
- Architecture should support **several representative workflows** that challenge boundaries without turning them into a compulsory product funnel — route `76`.
- Premature abstract journey maps were rejected as inaccurate; donor mechanisms become building blocks, not a single mandated journey — early `L813–L841`, `L944`.

**Implication for architecture:** composition and orchestration are first-class; a single “happy path” screen sequence is not.

---

## 3. Human + agent same product model

**Settled:**

- A person and agents work on **related material** in the same product; agents are not confined to a disconnected chat department — route `28-29`.
- Agents are cross-cutting: research, QMB, QML, charts, risk/BMS, node areas; they use selected **versions** of artifacts and may help create derived versions — early `L945–L947`.
- Local execution while the machine is on **and** remote execution that survives shutdown are both desired — early `L945–L947`; late `11423`.
- Agents interpret and assist with explicit instructions, tools and schemas; deterministic tool output must not be fabricated — late `11423`.
- QMA’s fan-out / loop / harness direction is central to coordination — late `11423`; route `55-56`.

**Open (not settled by intent recovery):** exact agent chrome/placement; whether a “human-first then agents later” process pass overrides simultaneous-use product intent (process evidence at transcript `13551` vs earlier simultaneous-use intent — issue `01`); laptop-off ownership and durability of orchestration state — backend baseline Q3.

**Standing law (do not reopen):** QMA’s only money-path output is a **candidate a human promotes**; no QMA execution tool, paper included — `_BRIEF.md`.

---

## 4. Ordinary Python / notebooks / QML / QMB coexistence

**Settled:**

| Surface | Intent |
|---|---|
| Ordinary Python | Always legal for exploration; external libraries remain usable; governed evidence requires graduation | 
| Notebooks | First-class exploratory work tools (not the application shell); continuity with code/runs/agents valued (QuantConnect-style) |
| QML | Structured bot declarations and versioned ordinary-Python logic for governed use — optional for exploratory scripts |
| QMB | Remains independently usable as library + CLI (+ pure `run()`); inspired by LEAN/Jesse-style research use; orchestrator writes evidence |
| QMF | Shared foundation/toolbox applications are built on — not an application itself |

Sources: route `31-32`, `52-64`; late `11290`, `11327`; grok prompts `28`; `_BRIEF.md` QMF/QMB laws.

**Boundary already clarified in recovery (not a new design):** standalone users/UI consumers may use QMB Python access; QMA’s backtesting path uses a runtime `qmb` CLI/MCP door and must not directly import QMB — issue `07`; route `62`. End-to-end transport completeness remains unverified.

---

## 5. Extensibility for a user who will not read source

**Settled direction:**

- Extensibility must reach the **user experience**, not only source-code developers — route `32`.
- Non-coding users should be able to extend the system — late `11292`, `13950`, `14010`.
- Investigate configuration, reusable procedures/components, ordinary Python, and executable extensions, plus UI capabilities that make those usable — grok prompts `42`.

**Open / Deferred:**

- Exact depth of no-code vs configuration vs composition vs executable-extension for **first release** — late unresolved; map.md “Not yet specified”.
- A usable **UI contribution system** is not established by backend executable extensions alone — backend baseline Q7; route `64`.

Treat “extensibility is central” as settled intent; treat the first-release contract as an architecture decision after owners and seams are mapped.

---

## 6. Shared Library / versioned artifacts

**Settled:**

- Library objects, versions, datasets, experiments and results are **shared across work environments** — route `30`.
- Library is a shared product surface (not a file explorer / GitHub clone), informed by Desktop STRATS as knowledge shape — late `11290–11292`, `11327–11328`.
- Git-like history/variants **without requiring GitHub**, covering strategies and Book/BMS variants — late `11423`.
- A shared bot/version/result can appear from Library, experiments or Trading Node **without creating three records** — F01–F17 design consequence 3.
- Human approval of a strategy variant and assignment to an intended Book before live use — late `11423`.
- Perspectives (researcher, analyst, developer, trader, portfolio manager) are intentionality lenses; work and agents cross perspectives; worlds may present the same work differently — late `11290–11328`.

**Open:** Project versus Workspace as the durable semantic container — late unresolved; F12; route leaves department roster open.

---

## 7. STRATS as input collection — not a platform to reconstruct

**Settled:**

- STRATS supplies **knowledge / input material** to be populated ahead of QMX — route `30`; late `11363–11371`.
- It is a relatively simple database-like collection, **not** a major subsystem or prerequisite platform — late `11363–11371`.
- Do **not** create a second STRATS store for candidates/databanks — F02 backend question.
- Build-our-own rule: borrow donor **mechanisms**, never donor engines or foreign platform contracts — `_BRIEF.md`; map.md out of scope.

---

## 8. Mechanism inventory vs approved scope (F01–F17)

F01–F17 record **useful donor mechanisms** and backend questions. Priorities and UI placement in the inventory are **not** newly approved scope — route `36`; inventory header; issue `02`.

| Family | Operator interest level | What remains undecided |
|---|---|---|
| F01–F04 StrategyQuant-like | Broad explicit interest (templates, candidates, procedures, robustness) | Generation semantics, parity, procedure coverage |
| F05–F08 QuantAnalyzer-like | What-if and money management specifically desired; portfolio combinations of interest | Valid comparison methods; filter vs rerun; Book/BMS simulation fidelity |
| F09–F11 QuantDataManager-like | Supports broader data-work intent | Not all approved as features |
| F12–F16 QuantConnect-like | Project continuity explicitly valued | Project/Workspace; notebook lifecycle; resource UX |
| F17 AlgoCloud-like | Lower-confidence opportunity | Retain for later evaluation |
| RoboQuant.dev | Useful for AI authoring ideas; **too basic** as overall QMX model | Supplemental mechanism donor only |
| OpenResearch / OpenScience / Delphi | Investigation leads for lineage, budgets, continuation, retrieval | Adapt mechanisms to QMA; not replacement dependencies |

---

## 9. Settled intent vs genuine open product questions

### Settled (architecture must honor)

1. Strategy experimentation is the **broad** priority across QMA, QMB, QML, QMF — not a single experiment screen.
2. Non-linear, multi-entry laboratory; no compulsory wizard.
3. Human and agent work share one product model and versioned artifacts.
4. Ordinary Python, notebooks, QML, and QMB remain coexisting legal surfaces.
5. Shared Library with versioned, inspectable artifacts across activities.
6. STRATS is input/knowledge only.
7. Extensibility for non-source-reading users is in-scope directionally.
8. Versioned evidence and human-controlled promotion into live; paper before promotion as a **workflow requirement** (execution locus open).
9. Planning on `main` / implementation on `integration` is intentional.
10. Standing laws in `_BRIEF.md` (QMF toolbox, default-deny imports, worlds, Books/BMS, QMB purity, QMA candidate-only money path, ordinary Python legal, build-our-own, configurable = UI-editable at platform level).

### Open questions that need an Architecture Decision (AD)

| ID | Question | Why an AD |
|---|---|---|
| AD-cand-1 | Strategy generation: vary declared parameters only vs generate condition/logic structure (F01 / GAP-0085) | Changes QML/QMB semantics and evidence identity |
| AD-cand-2 | Paper-before-promotion: where it runs given “outside the node” (DEC-0261) and QMA’s no-paper-execution rule | Workflow vs standing laws must be reconciled explicitly |
| AD-cand-3 | Laptop-off continuation: what survives workstation sleep (orchestration, state, follow-on scheduling) | Affects QMA daemon/worker topology |
| AD-cand-4 | Book/BMS: exact candidate-authoring boundary vs documented QMA prohibitions on mutating Book/BMS | Money-path and authority surface |
| AD-cand-5 | What-if / sizing: trade-list filter/rescale vs path-dependent Book/BMS-aware rerun — named methods and limits | Prevents false counterfactuals in product contracts |
| AD-cand-6 | Shared work identity: Project vs Workspace (or another container) for continuity across notebooks/code/runs/agents | UI-facing contracts and QMA ExperimentSpec linkage |

### May stay Deferred (no AD required to proceed with architecture framing)

- Exact world/department roster and count.
- Agent chrome placement and transitions.
- First-release depth of no-code extensibility / UI contribution system (after seams exist).
- Feature-by-feature donor parity and ordering (derive from capability audit).
- Notebook kernel lifecycle details beyond “notebooks are first-class tools.”
- AlgoCloud / F17 evaluation.
- Visual density metaphors (Hyprland/Bloomberg as mental tone only — early `L111`, `L813–L814`); not layout prescriptions.

---

## 10. Brief-required closing (intent lens)

### (1) What already exists (as durable intent baseline)

Recovered, cross-checked operator intent for a non-linear strategy-experimentation workbench with shared Library/versioning, coexisting Python/QML/QMB, human+agent continuity, and human-gated promotion. Backend baseline on `integration` @ `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` shows **source** for QMB optimize/walk-forward/data helpers, QMA experiment records, and related packages — presence ≠ demonstrated end-to-end product features (`2026-09-14-backend-baseline.md`).

### (2) Missing wiring vs missing function (intent-relevant)

| Area | Likely class (pending Grok classify) | Intent note |
|---|---|---|
| Parameter optimization, walk-forward, data helpers, experiment records | Often **reuse** or **connect/expose** once verified | Do not rebuild because UI was absent |
| Strategy **logic** generation, SQ-parity procedures | Possibly **extend** or **new** | Distinguish from param search (AD-cand-1) |
| Paper-before-promotion path | Likely **connect** + policy AD, not “add paper lane inside node” | Honor DEC-0261 / QMA candidate-only rule |
| Laptop-off continuation | **Extend** / topology AD | Desired job; not proven by daemon-on-workstation docs |
| What-if / MM vs Book-aware simulation | **Extend** with named semantics | Analysis ≠ automatic counterfactual backtest |
| UI contribution / no-code extensibility | **New** or **undecided** product surface | Backend plugins ≠ user-facing extensibility |
| CT-47 ExperimentSpec “defined-unwired” vs inspected source | **Reconcile** docs vs code | Do not silently pick one |

### (3) Recommended architectural ownership (from settled intent + standing laws)

| Concern | Owner (intent-aligned) |
|---|---|
| Agent identity, missions, tools, context, compute coordination, procedures, evidence, continuation | **QMA** |
| Experimentation/backtesting functions, governed run orchestration, search, robustness, data work, results | **QMB** (library+CLI; orchestrator writes evidence) |
| Structured bot declarations, versioned logic, conformance for governed use | **QML** |
| Shared types/contracts, identity, registry, data, indicators, venue, risk foundations | **QMF** (toolbox; default-deny imports) |
| Operational execution, Books, BMS, live zone | **Trading Node** — distinct from research compute |
| Shared Library / versioned artifacts as product surface | Cross-cutting **identity & provenance** contracts used by QMA/QMB/QML/UI — not a second STRATS engine |
| STRATS | External/input collection only |
| Human promotion into live | Human-only authority; QMA emits candidates |

Do not predetermine package import graphs beyond standing laws; understand each library before connecting them — issue `07`; route `74`.

### (4) Open questions — AD vs Deferred

See §9 tables. Bring AD-cand-1…6 to the operator with evidence and a preferred answer; keep Deferred items visible without blocking the capability map.

---

## Citations (primary)

- `workroom/research/2026-09-14-ui-feature-route.md:15-32`, `:36-46`, `:52-80`
- `workroom/research/2026-09-14-ui-recovery-early.md` (esp. L813–L814, L944–L947)
- `workroom/research/2026-09-14-ui-recovery-middle.md` (donor mechanism evidence; user asks at 5768/5798)
- `workroom/research/2026-09-14-ui-recovery-late.md:7-15`, `:38-40`
- `workroom/research/2026-09-14-grok-feature-prompts.md:27-44`
- `.scratch/qmx-ui-features/map.md:13-38`
- `.scratch/qmx-ui-features/issues/01-recover-original-intent.md`, `02-…`, `07-…`
- `.../inspection-and-feature-opportunities-2026-09-12.md` F01–F17 (mechanism inventory only)
- `workroom/research/2026-09-14-backend-baseline.md:17-38`
- `_bmad-output/.../inputs/_BRIEF.md` standing laws
