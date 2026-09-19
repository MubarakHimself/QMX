---
name: opportunities-journeys
sitting: architecture-QMX-2026-09-18
created: 2026-09-18
status: input
kind: CIS opportunity-to-journey map
purpose: cluster, challenge, and classify the opportunity space; not a backlog
sources:
  - workroom/research/2026-09-18_node-editor-architecture/staged-handoff/QMX-GROK-CODEX-STAGED-HANDOFF-2026-09-18/06-OPPORTUNITY-SEEDS.md
  - workroom/research/2026-09-18_node-editor-architecture/staged-handoff/QMX-GROK-CODEX-STAGED-HANDOFF-2026-09-18/05-JOURNEYS-AND-FAILURE-COVERAGE.md
  - workroom/research/2026-09-18_node-editor-architecture/reference-recon/QMX-REFERENCE-RECON-20260918T082954Z/QMX-ADAPTATION-OPPORTUNITIES.md
  - workroom/research/2026-09-18_node-editor-architecture/staged-handoff/QMX-GROK-CODEX-STAGED-HANDOFF-2026-09-18/01-GROK-ARCHITECTURE-PROMPT.md
  - workroom/research/2026-09-18_node-editor-architecture/staged-handoff/QMX-GROK-CODEX-STAGED-HANDOFF-2026-09-18/02-OPERATOR-INTENT-AND-SCOPE.md
  - workroom/research/2026-09-18_node-editor-architecture/staged-handoff/QMX-GROK-CODEX-STAGED-HANDOFF-2026-09-18/04-ARCHITECTURE-WORKSTREAMS.md
  - workroom/research/2026-09-18_node-editor-architecture/staged-handoff/QMX-GROK-CODEX-STAGED-HANDOFF-2026-09-18/07-COPILOT-SKILLS-AND-EVALUATION.md
  - architecture-QMX-2026-09-14 Workbench AD-3
  - architecture-QMX-2026-09-16 AD-1 (two-rail Library)
---

# CIS opportunity → journey map

**Status: architecture input.** The 80 `OP-*` seeds remain optional opportunity space. This sitting adds `OP-NEW-01`…`OP-NEW-18` for gaps the original list missed. Neither set is accepted implementation scope. Architecture acceptance is the enabling contracts plus a small proving slice — not delivery of 80 or 98 ideas.

Use this file to **cluster, challenge, split, and refuse**. Do not mint a subsystem per row. Do not treat donor features (LSE, OpenBB, Taskade, Hermes, n8n) as QMX requirements. Identifiers `OP-*`, `OP-NEW-*`, and `J*` are local to this Workflows sitting.

## How to read the classification

| Tag | Meaning | Architecture may require it? |
|---|---|---|
| **E** | Enabling architecture: public contracts, owners, lifecycle, discovery, authority. | Yes, as a contract — not as a shipped product app. |
| **X** | Thin fixture / reference example that proves an **E** contract. | Only the first-slice handful. |
| **A** | Optional later app or workbench. Consumes **E**; may never ship. | No. |
| **P** | Speculative / donor-shaped product pack. Interesting after **E** exists. | No. Do not design a core path for it. |

A single seed can carry two tags (example: **E** recipe contract + **A** builder UI). The **E** part is the architecture obligation; the **A** part is not.

Parent law that this map must not silently override:

- QMF remains the one framework. No sixth COMP.
- Artifact Library kinds stay the Workbench AD-3 `fp1` roster unless an explicit amendment is proposed. Hypotheses are not Library objects. Federated discovery concatenates Knowledge hits and Artifact hits; it is not a fourth store.
- This sitting **may** add capability/package discovery without minting research hypotheses as Library kinds.
- Book/BMS/SQS/MIS remain the default trading arrangement with regression coverage; they are not the ceiling.
- Authoring vs app-use sessions stay distinct. Manifest text cannot self-grant.
- `mutmut` is an optional test-strength tool, not a trading evaluator and not a mandatory dependency.

---

## 1. Clustered map of the original 80

Original grouping in `06-OPPORTUNITY-SEEDS.md` already tracks these families. Quality/governance seeds (OP-073–080) sit under **ops** as the user-requested nine-family cut; they are not a tenth product line.

### 1.1 Data — OP-001–008

| Seed | Class | Why this class | Primary journeys |
|---|---|---|---|
| OP-001 Dataset recipe builder | **E** recipe + **A** builder | Heterogeneous join/lineage is a platform contract; the studio UI is later. | J06, J13 |
| OP-002 Provider disagreement workbench | **E** no-silent-merge + **A** workbench | Conflicting sources must stay attributed. | J06, J20 |
| OP-003 Historical universe builder | **E** | Point-in-time membership is required for honest evaluation. | J06 |
| OP-004 Data revision explorer | **E** pin-original + **A** explorer | Later corrections must not rewrite an old run. | J06, J18 |
| OP-005 Corporate-action / normalization lab | **A** | Useful; not a first-slice contract. Raw vs adjusted must remain labelled wherever used. | J06, J13 |
| OP-006 Streaming capture and gap replay | **E** | Stream ownership, gaps, replayable capture. Complements OP-NEW-10. | J17, J18 |
| OP-007 API/CLI/file provider wrapper | **E** / **X** | Typed replaceable provider without private core edits. | J09, J20, J24 |
| OP-008 Dataset quality and entitlement preview | **E** | Preflight before a large job; unavailable must be visible. | J06, J20 |

**Cluster verdict:** keep the **recipe, provenance, revision, provider, preflight, stream** contracts. Do not backlog a corporate-action lab or a disagreement workbench as core.

**Maps to:** J06 (primary), J13, J17, J18, J20, J24. Adaptation recon: QMX-OPP-02, QMX-OPP-04, QMX-OPP-06.

### 1.2 ML — OP-009–016

| Seed | Class | Why this class | Primary journeys |
|---|---|---|---|
| OP-009 Model comparison studio | **A**; **E** eval protocol | Comparison needs pinned data/split/metrics; the studio is a later app. | J07, J13 |
| OP-010 Feature engineering workspace | **A**; **E** temporal semantics | Feature code with declared as-of is enabling; the workspace is not. | J06, J13, J24 |
| OP-011 Neural portfolio candidate | **P** | Optional alternative implementation. Must not force a bot. | J03, J07 |
| OP-012 Tree-model intelligence candidate | **P** | Shadow comparison, not a replacement mandate. | J04, J13 |
| OP-013 Clustering / segmentation study | **X** (non-bot proof) / **A** | Proves a research outcome with no Book/QMN. | J13 |
| OP-014 Forecast evaluation bench | **A** | Consumes recipe + eval protocol. | J06, J13 |
| OP-015 Typed model-output adapter | **E** optional interface | Investigate a typed decision envelope; Jev is a seed, not an assumed runtime. | J13, J24 |
| OP-016 Model artifact lineage explorer | **E** lineage + **A** explorer | Training data / weights / eval / inference must be linked. | J04, J07, J18 |

**Cluster verdict:** the enabling slice is **pinned dataset + split + eval + lineage + optional typed model output**. Neural/tree/forecast studios are later consumers (QMX-OPP-09). OP-013 is the cheapest non-trading ML proof.

**Maps to:** J13 (primary), J04, J06, J07, J18, J24.

### 1.3 Trading-system — OP-017–024

| Seed | Class | Why this class | Primary journeys |
|---|---|---|---|
| OP-017 Default-system version comparator | **X** | Proves Book/BMS regression without rescaling old trades. | J03, J09 |
| OP-018 Non-Book scalping system | **E** alternative composition; **A** this specific system | The contract is “a different complete system without fake Book/BMS”. The scalping policy is one example, not the product. | J03, J10 |
| OP-019 Multiple sizing-policy laboratory | **E** policy interface + **A** lab | Explicit risk units; incomparable fields stay incomparable. | J03 |
| OP-020 Optional-intelligence experiment | **E** | MIS/model must be bindable, shadowable, or absent. | J03, J04 |
| OP-021 Strategy hybrid constructor | **A** | Authoring convenience over QML/Python; not a new composition runtime. | J14, J15, J16 |
| OP-022 Cross-account allocation study | **A** analysis-only | Must not invent a shared-account writer. | J03, J05 |
| OP-023 Sequential deployment planner | **A** planner | Useful UI over OP-NEW-08. Not the handover contract itself. | J10, J18 |
| OP-024 Supervised vs unattended profile | **E** | Local supervised vs continuous hosted are placement profiles, not product SKUs. | J07, J10 |

**Cluster verdict:** architecture must allow **two honest complete systems** and a **sequential, stopped/flat handover**. Do not implement a scalping engine, a hybrid constructor, or a PM allocation product in this sitting.

**Maps to:** J03, J10 (decisive proofs 1), J04, J05, J07, J09, J18. Audit row: sequential deployment is only partial on the current Book path.

### 1.4 Research — OP-025–032

| Seed | Class | Why this class | Primary journeys |
|---|---|---|---|
| OP-025 WF1-style cited research pipeline | **A** | QML Stage 0 already owns hypotheses; this is a procedure pack. | J14, J22 |
| OP-026 Research-to-code procedure | **A**; **E** graduation path | Existing mill → CT-33 path; Workflows must not invent a second authoring language. | J14, J03 |
| OP-027 Bounded diagnosis-and-revision loop | **A** | Budgets and stop reasons are good workflow semantics (see OP-045). | J14, J16 |
| OP-028 Dictionary authoring helper | **A** | QML mill / vocabulary already in flight. Not a Workflows subsystem. | J14, J15 |
| OP-029 Experiment notebook-to-operation | **E** / **X** | Wrap a useful script behind tested I/O; proves custom contribution. | J09, J24 |
| OP-030 Study procedure capture | **A** | Template extraction from a successful exploration. | J15 |
| OP-031 Candidate-review table | **A** | Review UI over cited artifacts. | J14, J19 |
| OP-032 Partial hypothesis experimentation | **E** | Test a specified component without fabricating exits or full-system claims. | J14, J15 |

**Cluster verdict:** Workflows consumes the mill; it does not replace it. Enabling pieces are **notebook→operation** and **partial/honest evaluation**. WF1 as a shipped pipeline is later.

**Maps to:** J14, J15, J16, J22, J24.

### 1.5 Intelligence-apps — OP-033–040

| Seed | Class | Why this class | Primary journeys |
|---|---|---|---|
| OP-033 Energy-sector intelligence workspace | **P** / **A** | QMX-OPP-10 class: extension-supplied research pack. | J06, J13, J19 |
| OP-034 Macroeconomic release monitor | **P** / **A** | Same. Timing/revision semantics come from Data **E**. | J06, J17, J23 |
| OP-035 Liquidity-state monitor | **A** | Feature method over supported observations; not a trading signal factory. | J04, J17 |
| OP-036 Sentiment analysis comparison | **A** | Authorized text + methods; no implied trade. | J13, J14 |
| OP-037 Cross-market relationship study | **A** | Study ≠ permission to trade each instrument. | J06, J13 |
| OP-038 Daily analytical briefing | **A** | Aggregates pinned results; must not invent a recommendation. | J23, J19 |
| OP-039 Economic heatmap component | **A**; **E** widget registration | The widget contract is enabling (OP-060); this heatmap is one consumer. | J06, J19, J24 |
| OP-040 Universe screener recipe | **A**; **E**-lite filters | Screener is a recipe over OP-003, not a new engine. | J06, J16 |

**Cluster verdict:** **zero of these are first-slice.** They are the proof that the construction kit is not bot-only. Build them only after resource, recipe, job, widget, and shared-parameter contracts exist.

**Maps to:** J06, J13, J17, J19, J23, J24. Adaptation recon: QMX-OPP-05, QMX-OPP-10.

### 1.6 Workflow-runtime — OP-041–048

| Seed | Class | Why this class | Primary journeys |
|---|---|---|---|
| OP-041 Typed fan-out / join builder | **E** | Broadcast / zip / keyed / Cartesian must be declared. | J16 |
| OP-042 Reusable subworkflow library | **E** | Versioned composition with typed I/O. Distinct from QMA Graph Templates. | J15, J12 |
| OP-043 Selected-subgraph execution | **E** | Draft board ≠ runnable whole. | J15 |
| OP-044 Dependency-aware rerun planner | **E** | Invalidation after semantic change; cache reuse only when valid. | J15, J18 |
| OP-045 Error and recovery branch patterns | **E** | Classified failure, not hidden retry. | J16, J18 |
| OP-046 Human-review checkpoint | **E** | Pause / recorded decision / resume. | J14, J18 |
| OP-047 Schedule and webhook triggers | **E** | Trigger ≠ workflow definition; dedupe required. | J23, J17 |
| OP-048 Run comparison and trace inspector | **E** / **X** | Evidence-centred comparison of attempts/skips/failures. | J09, J16, J18 |

**Cluster verdict:** this family **is** architecture. It is the authored-procedure runtime that QMA’s agentic graphs do not already supply. Do not clone n8n. Do not force every app call through a top-level workflow.

**Maps to:** J15, J16 (primary), J12, J14, J17, J18, J23, J09.

### 1.7 Copilot — OP-049–056

| Seed | Class | Why this class | Primary journeys |
|---|---|---|---|
| OP-049 App-use explanation companion | **X** / **A** | Grounded in exact run records. Proves J01 inspect. | J01, J19 |
| OP-050 App-use change-request builder | **E** / **X** | The handoff artifact between app-use and authoring. | J01 |
| OP-051 Session history retrieval | **E** | Cited retrieval must not retarget commands. | J02 |
| OP-052 Capability-aware authoring assistant | **E** | Discover shipped tools before writing code. Complements OP-NEW-04. | J15, J20, J24 |
| OP-053 Skill activation evaluation | **E** | Desired and undesired activation with neighbors present. | J11 |
| OP-054 Skill ablation comparison | **A** | Incremental-value evidence; Caliper-inspired, not a product studio. | J11 |
| OP-055 Specialist delegation inspector | **A** | Work view without many permanent panes. | J14, J19 |
| OP-056 App integration profile authoring | **E** | Allowed context/actions/docs for an app-use companion. | J01, J19, J24 |

**Cluster verdict:** enabling pieces are **two session profiles, change-request artifact, host-granted tool discovery, skill evaluation, app profile**. Do not rewrite copilot core instructions per installed app (that gap is OP-NEW-04).

**Maps to:** J01, J02, J11, J15, J19, J20, J24. Adaptation recon: QMX-OPP-07.

### 1.8 Packaging — OP-057–064

| Seed | Class | Why this class | Primary journeys |
|---|---|---|---|
| OP-057 Extension scaffold generator | **E** / **X** | Package from public interfaces + tests. | J08, J24 |
| OP-058 Install preflight inspector | **E** | Dependencies, permissions, configuration before activation. | J08, J21 |
| OP-059 Cross-app exported analysis | **E** / **X** | App B invokes app A’s versioned operation. One of four composition modes. | J12 |
| OP-060 Reusable widget catalogue | **E** registration + **A** catalogue | Rich views against explicit results; not cards-only. | J19, J24 |
| OP-061 Mini-app parameter linking | **E** | Shared dates/universes/models as typed edges, not globals. | J19, J02 |
| OP-062 App version diff and lineage | **E** | What changed, which evidence supported it. | J01, J21 |
| OP-063 Private-to-shareable export | **E** | Strip chats/credentials; keep docs and allowed lineage. | J08, J22 |
| OP-064 Dependant-aware uninstall | **E** | Detect affected apps/workflows before disable. | J12, J21 |

**Cluster verdict:** this family **is** architecture. First-slice needs scaffold, install, export, one exported operation, and uninstall-with-dependants. Widget catalogue product and pretty diffs can wait.

**Maps to:** J08, J12, J21, J19, J24, J01, J22. Adaptation recon: QMX-OPP-01, QMX-OPP-05.

### 1.9 Ops — OP-065–080 (compute + quality/governance)

| Seed | Class | Why this class | Primary journeys |
|---|---|---|---|
| OP-065 Execution environment preflight | **E** | Hardware, deps, access, entitlement before placement. | J07, J20 |
| OP-066 CLI-backed operation inspector | **X** | Progress/logs/outputs/cancel for a typed command. | J09 |
| OP-067 Training-to-inference transfer | **A**; **E** split | Placement of training ≠ deployed inference. | J04, J07 |
| OP-068 Long-run recovery console | **E** / **A** console | Authoritative unfinished/interrupted/unknown. Console UI is later. | J18 |
| OP-069 Resource and quota overview | **E** | Limits before fan-out. | J07, J16, J20 |
| OP-070 Deployment readiness dashboard | **A**; **E** checks | Actual checks, not a global green light. | J10, J19 |
| OP-071 Multi-account operations view | **A** | Attributed readouts; does not retarget commands. | J05, J19 |
| OP-072 Backup/restore verification recipe | **E** | Restore consistency, not hope. | J18 |
| OP-073 Contract conformance runner | **E** | Contribution vs declared schemas/fixtures. | J09, J24 |
| OP-074 Default-system regression suite | **E** / **X** | Preserve Book/BMS behavior while boundaries change. | J03, J10 |
| OP-075 Provider compatibility comparison | **A** | Migration assessment over OP-002/007. | J06, J20 |
| OP-076 Context/permission red-team suite | **E** | Scope escalation and target confusion. | J01, J02, J22 |
| OP-077 Result comparability checker | **E** | Invalid comparisons across accounting/policy assumptions. | J03, J13 |
| OP-078 Package migration rehearsal | **E** | Reversible vs forward-only on disposable data. | J08, J21 |
| OP-079 Scenario coverage explorer | **A** | Useful later; not a platform runtime. | J01, J03, J18, J24 |
| OP-080 Extension-maintenance boundary audit | **E** / **X** | New capability without private host edits. | J08, J12, J24 |

**Cluster verdict:** keep **preflight, recovery, quota, conformance, default regression, comparability, migration, red-team, coupling audit**. Dashboards and overview apps are optional. Mutation testing of the test suite is missing here — OP-NEW-06.

**Maps to:** J07, J09, J10, J18, J20, J21, J03, J05, J08, J24.

---

## 2. New seeds the original 80 missed (`OP-NEW-*`)

These are CIS additions, not a second backlog. Each is recorded with the retained-idea fields. Several **E** rows were implied by the September 18 composition addendum, operator Artifact Library reminder, and adaptation recon, but never given an `OP-*` id.

### OP-NEW-01 — Artifact Library as a catalog of more than bots

- **Class:** **E** (catalog/discovery surface). Proposed commentary amendment to Workbench AD-3; **kind roster unchanged**.
- **User / start:** Operator opens Library expecting datasets, model artifacts, experiment results, workflows, packages, and apps — not only CT-33 bots. Today the product noun “Library” is read as the strategy shelf.
- **Operations:** browse/filter/cite across Artifact hits (existing `fp1` kinds), Knowledge hits (CT-44; not Library objects), and **capability/package hits** (new discovery class). Open an item to its owner surface.
- **Data/contracts:** projection over QMF registry, QMB B-15 / ledger merge, QMA Experiment Ledger, plus a generated capability index (OP-NEW-02). No fourth store. No `register_library_kind("strats")`. No Stage 0 hypothesis as a Library object.
- **Observable output:** attributed catalog rows with `hit_class`, owner, version, schema/kind, and “not a Library kind” labels where true.
- **Failure/recovery:** refusing to mint a new kind must be visible, not a silent empty shelf; duplicate display names do not collide `fp1`; missing owner index degrades that class only.
- **Dependencies:** Workbench AD-3, QMA federated discovery (DEC-0389), OP-NEW-02.
- **Unknowns:** which additional **query hits** (derived datasets, workflow definitions, installed apps) are in-scope as catalog rows vs owner-only. That is an AD, not a silent kind expansion.
- **Journeys:** J13, J19, J24; supports J03/J08 as the place users find proving fixtures.
- **Why the 80 missed it:** OP-016 is a model-lineage *explorer*; OP-042 a subworkflow *library*; OP-060 a widget *catalogue*. None is the product Library as a multi-rail catalog.

### OP-NEW-02 — Generated capability discovery index

- **Class:** **E**. Matches QMX-OPP-01.
- **User / start:** After install or enable, the user (and copilot, and another app) can see what data, operations, apps, streams, jobs, and widgets a package contributes — including unavailable ones.
- **Operations:** validate manifest → rebuild index → query by kind/owner/version/health/scope.
- **Data/contracts:** versioned extension manifest; generated index; typed operation schemas; required scopes/credentials/entitlements/cost; explicit unavailable states.
- **Observable output:** registry entries with owner/version/health; diagnostics; no implied access.
- **Failure/recovery:** incompatible version, duplicate id, missing dependency, invalid schema, failed migration → previous index remains consistent.
- **Dependencies:** OP-057, OP-058, OP-NEW-11. Distinct from QMA federated Knowledge+Artifact search.
- **Unknowns:** hot reload, package trust, current QMA plugin contribution points vs mini-app packages.
- **Journeys:** J08, J12, J20, J24.

### OP-NEW-03 — Composite app from independent contributions

- **Class:** **E** contract; **A** any particular composite.
- **User / start:** Assemble one app from supported operations, workflows, and views of several independently useful apps, without merging their source or unioning their authority.
- **Operations:** declare composition, pin component versions, bind shared parameters, open an app-use session on the composite.
- **Data/contracts:** composition manifest; component instance ids; version locks; exported contracts only; optional coordinating workflow (not mandatory).
- **Observable output:** a composite instance that remains intelligible if one component is unavailable; each component still runnable alone.
- **Failure/recovery:** breaking upgrade, removed provider, circular dependency, partial migration, deadlock — see OP-NEW-12, OP-NEW-15, OP-NEW-18.
- **Dependencies:** OP-059, OP-061, OP-NEW-09, OP-NEW-15.
- **Unknowns:** whether a composite is a package kind, an installed instance graph, or both.
- **Journeys:** J12, J19, J21. Extra interaction: composite-app app-use session (hole on J01).

### OP-NEW-04 — Copilot discovers installed contributions

- **Class:** **E**.
- **User / start:** Copilot tools and docs update from the host-granted, versioned interface of installed contributions and of a composite, without rewriting core instructions and without self-grant.
- **Operations:** session start / context revision reads the capability index filtered by host grants; install/upgrade does not widen an existing session.
- **Data/contracts:** session profile + grant set + capability index + app profile (OP-056). Composite profiles reference component capabilities; they do not copy private context or invent a permission union.
- **Observable output:** tool list equals host grants; a newly installed package is invisible to an already-open app-use session until re-grant; authoring session sees the public contribution surface, not another user’s private chats.
- **Failure/recovery:** stale grant after uninstall; neighbor skill stolen (J11); app content asking for extra tools (J01).
- **Dependencies:** OP-NEW-02, OP-056, OP-052 (authoring composition helper is a *skill*; this is the *discovery mechanism*).
- **Unknowns:** QMA tool-tag overlay vs a new host contribution protocol.
- **Journeys:** J01, J11, J12, J19, J24.

### OP-NEW-05 — Output-shape taxonomy (value, file/artifact, job, stream, event)

- **Class:** **E**.
- **User / start:** An operation declares how its result lives: a short typed value, a durable file/artifact, a job handle, an event, or a stream — not “everything is a JSON return”.
- **Operations:** invoke; observe the declared shape; cancel/subscribe/retrieve accordingly.
- **Data/contracts:** logical operation result envelope with shape tag; durable artifacts carry schema/type, content identity, provenance, completeness, authorized resolution. Machine-local paths are not portable IDs (see OP-NEW-14).
- **Observable output:** callers (app, copilot, workflow, CLI, direct) handle the same shape. A preview is not a bulk export. A stream is not a job. A job is not a file.
- **Failure/recovery:** treating a job handle as a completed artifact; preview endpoint carrying bulk; cancelled UI killing a shared stream (J17); expired artifact.
- **Dependencies:** QMX-OPP-03; OP-006; OP-066; OP-NEW-07; OP-NEW-14.
- **Unknowns:** whether one runner or several domain executors sit behind the job handle.
- **Journeys:** J07, J09, J17, J18, J24.

### OP-NEW-06 — Mutation testing evaluates tests, not trading

- **Class:** **E** as a test-strength principle; **A** as a product; `mutmut` optional.
- **User / start:** A maintainer asks whether the conformance/regression suite actually detects small semantic code changes. This is not a way to score a strategy or certify the architecture.
- **Operations:** on an isolated copy, mutate, run the existing tests, classify killed / survived / equivalent / invalid / timeout / error. Never `mutmut apply` on canonical files. Windows needs fork support (WSL) per current mutmut docs — verify, do not assume.
- **Data/contracts:** baseline test command, scope/exclusions, raw survivor report. Missing future code gets a mutation *plan*, not a fake score.
- **Observable output:** a report about **test** adequacy for a bounded module (e.g. OP-073 fixtures, OP-074 default-system tests, refusal mapping).
- **Failure/recovery:** using survivors as a trading quality metric; mutating the shared worktree; claiming architectural completeness from a score.
- **Dependencies:** OP-073, OP-074, OP-080. Complements Caliper-style skill eval (OP-053); does not replace scenarios.
- **Unknowns:** installed mutmut version, platform, which modules are isolated-copy safe.
- **Journeys:** J09, J03, J24 (quality of the tests those journeys rely on). No new product journey.

### OP-NEW-07 — Versioned internal operation interface

- **Class:** **E**.
- **User / start:** The same typed operation is callable from app, copilot, workflow node, CLI, and direct Python with equivalent deep semantics. Transport (in-process, process message, RPC, existing QMA wire) is an implementation choice, not a second API.
- **Operations:** describe, authorize, invoke, observe, cancel. No global untyped dispatch bypass.
- **Data/contracts:** logical contract (id, version, schemas, side-effect class, output shape, scope, errors) separate from transport. Owner-side validation at every door.
- **Observable output:** J09 parity is a *consequence* of one interface, not three reimplementations.
- **Failure/recovery:** schema drift per door; hardcoded selector; extension bypasses validation; adding a network service to every module.
- **Dependencies:** OP-007, OP-029, OP-066, OP-073, OP-NEW-05. W11.
- **Unknowns:** reuse of QMA wire vs a QMF-level operation descriptor vs both.
- **Journeys:** J09, J12, J24.

### OP-NEW-08 — Sequential deployment as command-ownership state machine

- **Class:** **E**. Distinct from OP-023 (planner app) and OP-070 (readiness view).
- **User / start:** A validated successor system takes responsibility after demo/shadow and a deliberate stopped/flat (or explicitly non-flat) handover. Software rollback does not reverse fills.
- **Operations:** readiness checks → shadow/demo → stop/flatten or record residual → switch command ownership → supervise → retire or roll back the *runtime*, never the fills.
- **Data/contracts:** deployment version, account scope, command-ownership record, reconciliation, unknown-order register, approval. Two versions must not both write one role.
- **Observable output:** new responsible runtime; retained old evidence; explicit rollback/retirement path (J10).
- **Failure/recovery:** unknown order; non-flat predecessor treated as flat; lost supervisor; old process resumes; rollback after actual fills; guessed positions.
- **Dependencies:** OP-023 (UI), OP-024, OP-074, J10, W6. Audit: current switch is Book-path partial.
- **Unknowns:** shared-account sequential handover vs distinct-account first (operator: distinct accounts first).
- **Journeys:** J10, J18, J04 (model consumer binding), J05.

### OP-NEW-09 — Four composition modes as distinct contracts

- **Class:** **E** taxonomy. The 80 only named mode 2 (OP-059).
- **User / start:** Reuse another app without wrapping every function in a workflow and without driving another app’s screen.
- **Operations / modes:**
  1. Consume a **saved output / artifact**.
  2. Invoke an **exported operation**.
  3. Coordinate several apps through an **optional workflow**.
  4. Build a **composite app** (OP-NEW-03).
- **Data/contracts:** each mode has its own permission, version pin, and failure story. Presentation is not the integration boundary.
- **Observable output:** a caller names the mode; the architecture does not collapse them into “app-to-app”.
- **Failure/recovery:** forcing mode 3 for a simple artifact read; iframe disposal killing durable work; one app mutating another’s implementation.
- **Dependencies:** OP-059, OP-042, OP-NEW-03, OP-NEW-05.
- **Journeys:** J12, J15, J19.

### OP-NEW-10 — Replay-to-live stream phase boundary

- **Class:** **E**. QMX-OPP-04. Distinct from OP-006 (capture/gap).
- **User / start:** Initialize from recent history, then continue live, without treating replay ticks as live market state or as execution authority.
- **Operations:** authorize → subscribe → replay → explicit handoff → live → unsubscribe. Consumer lifetime independent of a cancelled board.
- **Data/contracts:** phase/cursor, event time vs receive time, replay/live provenance, heartbeat, gap/dedupe, reconnect, backpressure. Stream ≠ trading permission.
- **Observable output:** ordered envelopes with phase; other consumers survive one cancel (J17).
- **Failure/recovery:** disconnect, late data, duplicates, buffer full, canceled UI closing a shared trading feed, clock drift.
- **Dependencies:** OP-006, OP-047, J17, J04.
- **Unknowns:** current event bus, replay store, separation from broker execution.
- **Journeys:** J17, J04, J18.

### OP-NEW-11 — Install vs activate vs grant

- **Class:** **E**. The 80 folds these into OP-058.
- **User / start:** A package can be present on disk, enabled for the installation, and still not granted to a given session/app-use profile.
- **Operations:** install → validate/migrate → activate (catalogue) → grant (session/app) → revoke. Uninstall with dependants (OP-064).
- **Data/contracts:** package state ≠ activation state ≠ session grant. Manifest permissions are requests.
- **Observable output:** J21 coexistence of old pinned runs with a newly installed version; an open app-use session does not silently gain tools.
- **Failure/recovery:** half-activated package; conflicting singleton; forward-only migration; grant leak across instances.
- **Dependencies:** OP-058, OP-062, OP-NEW-02, OP-NEW-04.
- **Journeys:** J08, J21, J01, J20.

### OP-NEW-12 — Shared instance vs independent instance / dependency diamonds

- **Class:** **E**.
- **User / start:** Two apps depend on provider P. Sometimes they must share one configured instance; sometimes each has its own. A diamond (A→P, B→P, C→A+B) must pin compatible versions.
- **Operations:** declare share vs copy; pin versions; upgrade one edge; refuse incompatible diamonds.
- **Data/contracts:** instance identity, configuration identity, version lock, diamond resolution, bounded cycles (OP-NEW-18).
- **Observable output:** attributed results name the instance used; upgrading P for A does not retarget B’s in-flight run.
- **Failure/recovery:** J21 “upgrade during waiting run”; circular dependency; removed provider; partial migration.
- **Dependencies:** OP-059, OP-064, OP-NEW-03.
- **Journeys:** J12, J21.

### OP-NEW-13 — Venue/account command targeting

- **Class:** **E**. Fills the thin J05 coverage in the original 80.
- **User / start:** Aggregate authorized reads across brokers/accounts while every command names venue, account, role, and credential. Same symbol on two venues is two instruments.
- **Operations:** select target; preflight adapter capability (CT-18); send; reconcile; revoke one credential without retargeting others.
- **Data/contracts:** existing QMF identity + venue capability discovery + roster. Dashboard filter is not a command target (INT-10).
- **Observable output:** per-account evidence; attributed aggregates (OP-071 is the **A** view).
- **Failure/recovery:** stale dashboard filter; netting/shared-account conflict; one credential revoked; unsupported adapter.
- **Dependencies:** OP-071, OP-022 (analysis-only), J05, J20. CONNECT / venue ADs.
- **Journeys:** J05, J20, J10.

### OP-NEW-14 — Portable durable-artifact identity

- **Class:** **E**. Pair with OP-NEW-05.
- **User / start:** A file handoff used by another app, a remote worker, or a second installation resolves by content identity and authorized locator — not `C:\Users\…\out.parquet`.
- **Operations:** publish artifact → content hash + schema + provenance + completeness → resolve in another environment.
- **Data/contracts:** artifact ref envelope; no machine-local path as global id; export strips private paths (OP-063).
- **Observable output:** remote GPU job and second installation retrieve the same bytes or refuse.
- **Failure/recovery:** path escape (J22); local file on remote worker; incomplete restored reference (J18); expired blob.
- **Dependencies:** OP-063, OP-067, OP-072, OP-NEW-05, OP-NEW-17.
- **Journeys:** J07, J08, J18, J22.

### OP-NEW-15 — Composite authority is not a union

- **Class:** **E**.
- **User / start:** Combining interfaces of a research app and a live-trading operation must not combine their authority. A composite app-use copilot sees the intersection (or explicit declared set) of host grants, never the union of component wish-lists.
- **Operations:** compose; open app-use; attempt a component’s extra tool; refuse.
- **Data/contracts:** grant set is host-computed from declared exports + session profile. App documentation cannot escalate.
- **Observable output:** live-trading operations remain explicitly scoped; nested app-use cannot become authoring.
- **Failure/recovery:** J01 extra tools; nested app escalation; callback permission propagation.
- **Dependencies:** OP-NEW-03, OP-NEW-04, OP-076.
- **Journeys:** J01, J05, J12, J19.

### OP-NEW-16 — Headless contribution as a reusable step

- **Class:** **E** / **X**.
- **User / start:** An extension with no navigation pane still appears as a typed operation, a workflow node, a CLI command, and an app-callable export.
- **Operations:** install headless package → discover → invoke through all doors (J09) → another app consumes it (J12).
- **Data/contracts:** UI contribution is optional; operation contract is not. A workflow does not automatically specify an app’s UI, permissions, or deployment.
- **Observable output:** first-slice proof 4 without building a widget.
- **Failure/recovery:** hidden because no icon; duplicated logic per door; private import.
- **Dependencies:** OP-057, OP-059, OP-NEW-02, OP-NEW-07.
- **Journeys:** J08, J09, J12, J24.

### OP-NEW-17 — Local file reference on a remote worker

- **Class:** **E**. Named in the September 18 extra interactions; absent from the 80.
- **User / start:** An authoring session or job names a local file. Placement is remote/GPU. The file is either staged as a portable artifact or the job refuses — never a silent path that only existed on the laptop.
- **Operations:** preflight placement (OP-065) → stage or refuse → run → return artifacts (OP-NEW-14).
- **Data/contracts:** data-transfer policy, entitlement, completeness. Laptop coordinator sleep ≠ remote worker (INT-21 / Workbench AD-10).
- **Observable output:** job handle records what was staged; missing local path is a refusal, not a hang.
- **Failure/recovery:** interrupted upload; symlink escape; revoked key; preemption with partial stage.
- **Dependencies:** OP-065, OP-067, OP-NEW-14, J07, J22.
- **Journeys:** J07, J18, J22.

### OP-NEW-18 — Nested invocation and cycle budgets

- **Class:** **E**.
- **User / start:** App/workflow/copilot calls may nest. Recursion, expensive nested jobs, and legitimate bounded cycles need a budget and a deadlock refusal — not unbounded fan-out.
- **Operations:** invoke with remaining budget; detect cycles; skip/fail partitions with attribution (J16).
- **Data/contracts:** recursion budget, cycle allowance, cost/quota (OP-069), join policy for partial failure.
- **Observable output:** nested call either completes with provenance or refuses with a stable code; averages cannot hide a missing branch.
- **Failure/recovery:** explosive Cartesian product; callback permission propagation; deadlocked composite; notification storms from overlapping schedules (J23).
- **Dependencies:** OP-041, OP-069, OP-NEW-03, OP-NEW-12.
- **Journeys:** J12, J16, J23.

---

## 3. Journey map and coverage holes

### 3.1 Cluster → journey (presence, not completeness)

| Family | J01 | J02 | J03 | J04 | J05 | J06 | J07 | J08 | J09 | J10 | J11 | J12 | J13 | J14 | J15 | J16 | J17 | J18 | J19 | J20 | J21 | J22 | J23 | J24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Data | | | | | | ● | | | ○ | | | | ● | | | | ● | ○ | | ● | | | | ○ |
| ML | | | ○ | ● | | ○ | ● | | | | | | ● | | | | | ○ | | | | | | ○ |
| Trading-system | | | ● | ○ | ○ | | ○ | | ○ | ● | | | | | | | | ○ | | | | | | |
| Research | | | ○ | | | | | | ○ | | | | | ● | ● | ○ | | | ○ | | | ○ | | ○ |
| Intelligence-apps | | | | ○ | | ● | | | | | | | ● | ○ | | ○ | ○ | | ● | | | | ● | ○ |
| Workflow-runtime | | | | | | | | | ○ | | | ○ | | ○ | ● | ● | ○ | ● | | | | | ● | |
| Copilot | ● | ○ | | | | | | | | | ● | | | ○ | ○ | | | | ● | ○ | | | | ○ |
| Packaging | ○ | ○ | | | | | | ● | | | | ● | | | | | | | ● | | ● | ○ | | ● |
| Ops | ○ | ○ | ● | ○ | ○ | ○ | ● | ● | ● | ○ | | ○ | ○ | | | ○ | | ● | ○ | ● | ● | ○ | | ● |
| NEW seeds | ● | ● | ○ | ○ | ● | | ● | ● | ● | ● | ● | ● | ○ | | | ○ | ● | ● | ● | ● | ● | ● | ○ | ● |

● = family is a primary probe for that journey. ○ = secondary / supporting. Blank = not a natural home.

### 3.2 Four decisive proofs — seed coverage

| Proof | Journeys | Seeds that actually probe it | Still missing without NEW |
|---|---|---|---|
| 1. Two trading compositions + sequential deploy | J03, J10 | OP-017, 018, 019, 020, 074, 077; OP-023/070 as UI | Command-ownership state machine, non-flat residual, rollback-after-fills → **OP-NEW-08** |
| 2. Non-trading dataset/ML, no fake bot | J06, J13 | OP-001–004, 008–010, 013, 032 | Library catalog so the result is findable as a non-bot artifact → **OP-NEW-01** |
| 3. App-use → change request → authoring v2; isolation | J01, J02 | OP-049, 050, 056, 076; OP-051, 061 | Copilot grant freeze; composite app-use → **OP-NEW-04, 11, 15**. J02 remains a journey hole: no original seed *is* the three-session fixture (use J02 as an **X**, do not mint OP-NEW-19). |
| 4. Custom contribution discovered, tested, reused, including another install | J08, J09, J12, J24 | OP-007, 029, 057–059, 063, 073, 080 | Discovery index, internal interface, output shapes, headless step, four composition modes, install≠activate → **OP-NEW-02, 05, 07, 09, 11, 16** |

### 3.3 Per-journey holes

| Journey | Original-80 density | Hole | NEW seed / disposition |
|---|---|---|---|
| J01 App-use → authoring v2 | Adequate for the pairwise handoff | Composite-app app-use session; nested app becoming authoring; install widening tools | OP-NEW-04, 11, 15. Still no dedicated composite-app-use journey — flag for Stage B, do not invent J25 here. |
| J02 Concurrent session isolation | **Thin** (051, 061, 076) | Three concurrent product sessions (workflow + strategy + ML) as a first-class seed; reconnect replay | Covered as **E** by OP-051 + OP-NEW-04 grants. Remains a journey hole: no seed *is* the three-session fixture. First-slice should use J02 as an **X**, not a new app. |
| J03 Two trading systems | Strong | — | Keep. OP-NEW-06 tests whether OP-074 actually detects policy-boundary mutations. |
| J04 Two intelligence versions | Medium | Two writers claiming one role; shadow used as production; consumer binding | OP-NEW-08 (ownership) + OP-NEW-10 (stream phase) + OP-020. No extra app. |
| J05 Multiple brokers/accounts | **Thin** (022, 071) | Command targeting, same symbol two venues, credential revoke | **OP-NEW-13**. OP-071 stays the optional dashboard. |
| J06 Point-in-time recipe | Strong | — | Keep E; builder UI is A. |
| J07 GPU/remote placement | Adequate | Local file on remote worker; output shape of training jobs | **OP-NEW-17, 05, 14** |
| J08 Install into another QMX | Strong | Install vs activate vs grant; portable artifact ids | **OP-NEW-11, 14** |
| J09 Door parity | Adequate as a test | Shared logical interface; output shapes; mutation of the parity tests | **OP-NEW-07, 05, 06** |
| J10 Sequential rollout | Medium (planner/dashboard/regression) | Ownership state machine; unknown orders; old process resume; rollback after fills | **OP-NEW-08** (E). OP-023 remains A. |
| J11 Skill create/eval | **Thin** (053, 054) | Author ≠ verifier; neighbor-skill theft; install separated from authoring | OP-053 is E. OP-NEW-04/06/11 support. Do not backlog an ablation studio (054). |
| J12 App-to-app reuse | Medium, mode-2 only | Composite, diamonds, cycles, shared vs independent instance, copilot of composite | **OP-NEW-03, 09, 12, 15, 18, 04** |
| J13 Non-trading ML/data | Strong | Result not appearing in Library except as a bot | **OP-NEW-01** |
| J14 Mixed research workflow | Strong | — | Keep as A over mill + workflow E. |
| J15 Messy draft / selected run | Strong | — | Keep E. |
| J16 Parallel joins | Adequate | Nested expensive calls; cycle budget | **OP-NEW-18** |
| J17 Shared live subscriptions | Medium (capture/gap, monitors) | Replay→live phase; shared-feed cancel; stream vs job | **OP-NEW-10, 05** |
| J18 Crash/restore | Strong | Portable artifact refs after restore; remote stage | OP-068/072 + **OP-NEW-14, 17** |
| J19 App profile / rich view | Strong | Composite profile; headless (no view) still valid | **OP-NEW-03, 15, 16** |
| J20 Provider/account reconfig | Adequate | Capability index unavailable states; venue capability | **OP-NEW-02, 13** |
| J21 Extension upgrade in flight | Medium | Install≠activate; side-by-side; composite dep upgrade while a run waits | **OP-NEW-11, 12** |
| J22 External files/browser/computer | Medium-thin | Remote resolution of local files; path/symlink | **OP-NEW-14, 17**. Computer-use remains provisioned capability (INT-13), not a seed explosion. |
| J23 Scheduled department work | Adequate | Overlap/nested schedule budgets | **OP-NEW-18** |
| J24 Public-interface custom contribution | Strong | Copilot discovery of the new contribution; output shapes; headless | **OP-NEW-02, 04, 05, 07, 16** |

### 3.4 Extra interactions still without a journey id

Stage B should derive these rather than this file minting J25–J32:

- Multi-app dependency upgrade during a waiting run (OP-NEW-12 × J21).
- Shared-feed cancellation (OP-NEW-10 × J17).
- App-call cycles and callback permission propagation (OP-NEW-18 × OP-NEW-15).
- Mixed artifact/schema versions.
- Composite-app app-use session (OP-NEW-03 × J01).
- Expensive nested calls (OP-NEW-18).
- Local file references on remote workers (OP-NEW-17).
- Plugin install versus activation (OP-NEW-11).
- Missing provider/GPU entitlement as an unavailable catalog state (OP-NEW-02 × J07/J20).

---

## 4. Enabling architecture vs optional later apps

### 4.1 Enabling architecture (acceptance-relevant)

These must exist as **contracts, owners, and lifecycle**, even if no pretty app ships. They are the construction kit.

| Theme | Seeds | Owner hint (not a package mint) |
|---|---|---|
| Capability manifest + generated index | OP-NEW-02, OP-007, OP-057, OP-080 | QMF extension/registry + packaging |
| Artifact Library catalog (multi-rail projection) | OP-NEW-01 | Existing Library projection + capability hits; no sixth COMP |
| Internal operation interface + door parity | OP-NEW-07, OP-029, OP-066, OP-073, J09 | Logical contract; transport later |
| Output shapes + portable artifacts | OP-NEW-05, OP-NEW-14, OP-063 | Job/artifact/stream/value distinct |
| Data recipe / PIT / revision / provider | OP-001–004, OP-007, OP-008 | QMF Data + adapters |
| Stream phase + shared consumer lifetime | OP-006, OP-NEW-10, OP-047 | QMN/QMF streams; not trading permission |
| Workflow semantics (draft, subgraph, fan-out, rerun, recovery, trigger) | OP-041–048 | General authored workflow; QMA keeps agentic graphs |
| Authoring vs app-use + change request | OP-050, OP-056, OP-NEW-04, OP-076 | QMA session/profile + host grants |
| Four composition modes + composite rules | OP-NEW-09, OP-059, OP-NEW-03, OP-NEW-12, OP-NEW-15, OP-NEW-18 | W11 |
| Install / activate / grant / export / uninstall | OP-058, OP-NEW-11, OP-063, OP-064, OP-078 | Packaging lifecycle |
| Alternative trading composition + comparability | OP-018 (as contract), OP-019, OP-020, OP-074, OP-077 | QMF Risk/QMB/QMN seams; no dummy Book |
| Sequential command-ownership handover | OP-NEW-08 | QMN deploy/reconcile; distinct from planner UI |
| Compute preflight / recovery / quota | OP-065, OP-068, OP-069, OP-NEW-17 | Placement ≠ agentic |
| Venue/account targeting | OP-NEW-13 | Existing identity + capability discovery |
| Test strength (conformance, regression, mutation of tests) | OP-073, OP-074, OP-NEW-06 | Eval of tests, not of PnL |
| Widget/app declaration (not visual design) | OP-060, OP-061, OP-056 | Host contribution contract; layouts later |

Adaptation recon sequencing still holds: **manifest, resource envelope, scope/permission, job/artifact lifecycle first**; one vertical reference; replay/live after provenance; ML/macro packs as consumers.

### 4.2 Optional later apps (not acceptance)

Do not design core paths for these. They consume the table above.

- Intelligence packs: OP-033–040, QMX-OPP-10.
- ML studios: OP-009, 011, 012, 014, QMX-OPP-09.
- Research procedure packs: OP-025–028, 030, 031 (mill already owns hypotheses/dictionary).
- Trading labs as products: OP-021, 022, 023 (planner), 070 (dashboard), 071 (multi-account view).
- Copilot chrome: OP-049 companion, OP-054 ablation studio, OP-055 specialist inspector.
- Ops chrome: OP-066 inspector UI, OP-068 console UI, OP-079 coverage explorer.
- Specific alternative system (scalping, neural portfolio): examples only.

### 4.3 Explicit non-goals for this sitting

- Implementing all 80 or all 18 NEW seeds.
- Cloning LSE / OpenBB / Taskade / n8n / Hermes.
- A marketplace, cloud tenancy, or public publication (INT-15).
- Live trading, paid GPUs, production deployment from architecture.
- Final visual design (INT-29).
- Minting hypotheses or STRATS as Artifact Library kinds.
- Using mutation score as a trading or architecture certificate.
- A second general framework beside QMF.

---

## 5. First-slice recommendation

An early usable slice is **not** the scope ceiling. It is the smallest set that jointly stresses the hardest contracts. Prefer fixtures over product apps.

### Slice 0 — substrate (must precede examples)

1. **Capability manifest + generated index** (OP-NEW-02) with unavailable states.
2. **Versioned internal operation interface** (OP-NEW-07) and **output-shape tags** (OP-NEW-05).
3. **Job/run/artifact lifecycle** with cancel, unknown, and portable artifact refs (QMX-OPP-03, OP-NEW-14).
4. **Authoring vs app-use profiles** and a **change-request artifact** (OP-050, OP-056, OP-NEW-04).
5. **Install / activate / grant / export-without-secrets** (OP-NEW-11, OP-057, OP-063).
6. **Artifact Library catalog projection** that can show a non-bot artifact and a capability hit without minting new kinds (OP-NEW-01).

Stop-condition for Slice 0: a new typed operation can be described, discovered, invoked through two doors, and found in the catalog — still with no domain app.

### Slice 1 — four proofs as thin fixtures

| Proof | Fixture, not product | Seeds | Journeys |
|---|---|---|---|
| Two compositions | Default Book/BMS regression **plus** one honest non-Book complete system (toy policy, not a scalping franchise) | OP-017, OP-018-as-contract, OP-074, OP-077 | J03 |
| Sequential handover | Stopped/flat switch of command ownership on a distinct account; refuse dual writers; rollback does not unfill | OP-NEW-08, OP-024 | J10 |
| Non-trading study | Provider-backed resource → preview → recipe → queued run → dataset/model/report artifact → two bound widgets **or** a headless report. No bot, no Book, no QMN | OP-001, OP-008, OP-013, OP-060/061 | J06, J13 |
| Session handoff | Installed mini-app result → explanation from records → change request → v2 in a separate authoring session; v1 untouched | OP-049, OP-050, OP-056, OP-076 | J01 |
| Isolation | Concurrent workflow + strategy + ML sessions; reconnect; retrieval does not retarget | OP-051, OP-NEW-04 | J02 |
| Custom contribution | Headless package: one implementation as direct/CLI/node/app-export; install into a second fixture installation; App B calls it; uninstall names dependants | OP-NEW-16, OP-057, OP-059, OP-064, OP-080 | J08, J09, J12, J24 |

### Slice 1b — one live-cycle failure (required)

Pick **one** so a static happy path cannot pass:

- Shared stream: two consumers, cancel one, the other survives; replay→live phase explicit (J17, OP-NEW-10), **or**
- Remote placement: missing GPU/entitlement refused; local file on remote worker staged or refused (J07, OP-NEW-17), **or**
- Crash/restore: unfinished job remains unknown, not guessed complete (J18, OP-068).

Do not require all three in the first slice; require the contracts so the other two are not designs-from-scratch later.

### Out of the first slice (refuse politely)

Energy workspace, daily briefing, neural portfolio, sentiment pack, economic heatmap, WF1 pipeline, training-to-inference product, mutation-testing UI, macro/intermarket app pack, cross-account allocation product, skill ablation studio, deployment dashboard chrome.

### Suggested proving vertical (from adaptation recon, QMX-shaped)

`discover provider resource → entitlement/quality preview → versioned recipe → queued job → portable artifact → catalog hit → two bound widgets **or** a second app’s exported-operation call → app-use inspect → change request`.

That one vertical exercises Data, Workflow-runtime, Packaging, Copilot, Library catalog, and Ops without building the intelligence-app family.

---

## 6. CIS challenge notes (splits, merges, refusals)

| Challenge | Disposition |
|---|---|
| Merge OP-023 into OP-NEW-08 | **Split kept.** Planner is A; state machine is E. |
| Merge OP-052 into OP-NEW-04 | **Split kept.** 052 is an authoring skill (“compose from catalogue”). NEW-04 is the session discovery mechanism. |
| Merge OP-059 into OP-NEW-03 | **Split kept.** 059 is mode 2. NEW-03 is mode 4. NEW-09 is the taxonomy. |
| Merge OP-016 into OP-NEW-01 | **Split kept.** 016 is model lineage. NEW-01 is the catalog surface across kinds. |
| Merge OP-006 into OP-NEW-10 | **Split kept.** Capture/gap vs replay→live phase. |
| Merge OP-058 into OP-NEW-11 | **Split kept.** Preflight inspector vs three-state lifecycle. |
| Merge OP-073 into OP-NEW-06 | **Split kept.** Conformance is behavioral fixtures. Mutation asks whether those fixtures detect code edits. |
| Split OP-018 into contract vs scalping app | **Already classified** E vs A. Do not implement scalping. |
| Add a journey J25 for Library browse | **Defer to Stage B.** J13/J19/J24 plus OP-NEW-01 are enough for Stage A. |
| Make all intelligence-apps first-slice to “show breadth” | **Refuse.** Breadth is proved by one non-bot artifact in the catalog plus one headless contribution. |
| Elevate mutmut to a required runtime | **Refuse.** Optional tool; principle is E. |
| Expand Library kinds to datasets/workflows/apps | **Refuse silent expansion.** Catalog *hits* may cite those owners; kind roster stays an explicit AD. |
| Require a network operation service per module | **Refuse.** Transport is a choice behind OP-NEW-07. |

---

## 7. Traceability for later UX (not layouts)

For first-slice journeys only, later UX work needs: entry point, user question, allowed commands, data displayed, component/widget needs, state transitions, progress, error/recovery, copilot context, lineage/handoff links, exit state. That work is a UI-host readiness map, not this file.

This map’s job ends at: **clustered opportunity space, 18 gap seeds, journey holes, enabling vs optional, first-slice.** Downstream architecture spine should bind **E** rows to owners and ADs; it should not copy **A**/**P** rows into the epic backlog by default.
