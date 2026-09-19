---
name: 'QMX Workflows construction kit'
type: architecture-spine
purpose: build-substrate
altitude: feature
paradigm: 'Capability-oriented composition over hexagonal libraries'
scope: 'How QMX composes, creates, tests, packages and operates capabilities through workflows, extensions, mini-apps and widgets, with session-aware QuantMind/QMX Copilot, Artifact Library discovery, app orchestration, data recipes, alternative-system honesty, and future UI-host contracts. No final visual layout. No production implementation. No sixth COMP unless a named amendment in this spine.'
status: draft
created: '2026-09-18'
updated: '2026-09-19'
binds: [INT-01, INT-02, INT-08, INT-09, INT-18, GAP-0081-contracts-only, Workbench-AD-1, Workbench-AD-3, Workbench-AD-9, QML-AD-13]
sources: [docs/AGENTS.md, docs/constitution.md, architecture-QMX-2026-09-14, architecture-QMX-2026-09-16, architecture-QMA-2026-08-28, architecture-QMB-2026-08-20, architecture-QML-2026-08-21, architecture-NODE-2026-08-28, integration@270e992, QMX-GROK-CODEX-STAGED-HANDOFF-2026-09-18, Explore-Node-Editor-Architecture.md, QMX-REFERENCE-RECON-20260918T082954Z, QMX-CODEX-CHALLENGE-20260919T130812Z]
companions: [RECON-RETURN.md, REQUIREMENTS-ADDENDUM.md, CONTRACTS.md, JOURNEYS.md, STACK-AND-EVALUATION.md, COPILOT-AND-APPS.md, CONFLICT-REGISTER.md, IMPLEMENTATION-SEQUENCE.md, CHALLENGE-RECONCILIATION.md]
review_status: stage-c-reconciled-candidate — not operator-accepted; not Codex-rechecked after material contract repair; not ratified
---

# Architecture Spine — QMX Workflows construction kit

## Design Paradigm

**Capability-oriented composition over hexagonal libraries.** QMF remains the one framework (toolbox, not application). QML, QMB, QMA and QMN remain the application-layer products. This sitting does not mint a sixth COMP, a second orchestrator, a marketplace, or a foreign workflow runtime.

A **capability** is a versioned operation with declared meaning, schemas, effect class and output shape. An **extension** contributes capabilities (and optionally procedures, skills or presentation descriptors). A **workflow** composes operations. A **mini-app** groups capabilities, views and a copilot profile around an installed instance. A **widget** is a view/control inside an interface. These are related, not a compulsory hierarchy.

The Experimentation Board is a **working-surface projection**. It is not a registry kind, not a Mission, and not automatic execution.

```mermaid
graph TD
  COP[QuantMind / QMX Copilot]
  BOARD[Experimentation Board — layout only]
  COI[Capability Operation Interface]
  COP --> COI
  BOARD --> COI
  CLI[qmb CLI / library API]
  CLI --> COI
  APP[Mini-app instance]
  APP --> COI
  COI --> QMA[QMA daemon — procedures, sessions, plugins]
  COI --> QMB[QMB doors — experiment machinery]
  COI --> QML[QML authoring / research]
  COI --> QMN[QMN host — paper then live]
  QMA -->|CT-47 one run per env; never import qmb| QMB
  QML --> QMF[QMF contracts / registry / data / risk]
  QMB --> QMF
  HUM[Human L17 promote]
  QMB --> HUM
  HUM --> QMN
  QMN -->|unforked run_slice| QMB
```

## Inherited Invariants

Parents bind read-only. Local `AD-1`..`AD-22` do not renumber them. A local rule that would mint a sixth COMP, compile a Stage 0 graph, let QMA `import qmb`, invert L36 with dummy Book fields, or treat json-render as identity is a **conflict**, not an override.

| Inherited | From parent | Binds here |
| --- | --- | --- |
| L7, L8, L14, L31 | constitution | Toolbox; loops/UI outside QMF unless named admission; no silent sixth application |
| L17, L33, L34, L35, L36, L39 | constitution | Human promote; ordinary Python legal; secrets as refs; UNKNOWN; bot→book→BMS→operator; exit-preservation |
| L30, DEC-0241, DEC-0347 | constitution / QMA | Default-deny; only `qmn.venue` imports qmf-venue; QMA never venue; QMA never `import qmb` |
| Workbench AD-1, AD-2, AD-3, AD-5, AD-7, AD-8, AD-9, AD-10, AD-12, AD-14, AD-16 | architecture-QMX-2026-09-14 | No sixth COMP; three door-derived lanes; Library = listed fp1 kinds; two analysis methods; paper trinity; CT-47 door; procedures in QMA; continuation is daemon+remote+outbox; rung 4 = GAP-0081; candidate set is a query; no Project/Workspace kind |
| QMA AD-1, AD-2, AD-6, AD-14, AD-16, AD-18, AD-19, AD-21, AD-24, DEC-0341 | architecture-QMA-2026-08-28 | Port cardinality; sole writer sqlite; Session is execution container; no execution tool; plugins first-party; Memory ≠ Knowledge |
| QL-1..QL-10, mill AD-6, AD-7, AD-13, AD-15 | architecture-QML + 2026-09-16 | Two-artifact bot; three legal entries; Stage 0 graph is not a workflow; `qml.research` fourth surface |
| B-1..B-15 | architecture-QMB-2026-08-20 | Thin doors; TPE search ≠ generation; B-15 as-of |
| TN-1..TN-25, CONNECT AD-1..AD-5 | NODE + CONNECT | Unforked `run_slice`; closed VenueClientKind; honest FX paper |
| DEC-0084 / 0085 / 0086, DEC-0361 / 0362 / 0366 | graveyard | No central library/backtest service; no marketplace/solver; no HMR |
| GAP-0061 / 0062 / 0063 / 0085, GAP-0058, GAP-0081 chrome | gap-report | Do not fill in prose; contracts-only revisit of GAP-0081 is this sitting’s limit |

**Proposed parent amendments** (not silent overrides):

1. Workbench AD-16 commentary — “Experimentation Board” is an allowed display alias; still mints no record.
2. Workbench AD-9 / QMA topology — Graph Template topology is a **DAG** (cycles and self-loops refuse), not pairwise reverse-edges only.
3. QMA closed store list — persist the already-named `task_graph_state` projection including the AD-26 outbox; add journal-projected `product_session` (not a QMA Session fold) and GrantRecord rows beside it. Mini-app instances reuse plugin-install records with `instance_id`. Change-request is an addable AD-22 staging kind. CheckpointManifest is journal-projected. No other new sqlite.
4. QMA AD-7 Profile law does not apply to `ProductSessionProfile`; QMA AD-5 `scope_path` does not gain a segment — product-session is a wire/header field beside it.
5. QMA Role display — trading-floor “Product Manager” **label** becomes **Portfolio Manager**; `desk_slug=pm` unchanged (GAP-0083).
6. Mill/wire DEC-0389 two-class freeze — **named amendment**: federated union gains `ContributionHit` as a third discovery class, never fp1, never a registry kind.
7. L36 Book/BMS authority chain — **named amendment, not a silent inversion.** Book/BMS remain the **default** implementation of portfolio accounting and risk/position-sizing. They are not the only implementations the kit may host. A complete alternative PolicyPair may occupy those roles without dummy Book/BMS records. Downstream authoring, evaluation, optional intelligence, node, and live **adopt** the selected composition. Human L17 promote and sequential paper-then-live remain. Sensing/research is not a trading composition. Constitution prose is updated in Documentation Factory from this named amendment.
8. QMA AD-22 staging kinds — add `change_request`.
9. QMA AD-17 JobHandle vocabulary is reused exactly by this sitting’s job contract (AD-26). Sitting payloads must not drift to `succeeded` / `awaiting_approval`.
10. Recipe **definition** identity is additive beside Workbench AD-13 output-release fp1 (AD-31). Output identity stays fp1. CT-06 registry kind remains deferred.

## Invariants & Rules

### AD-1 — Construction kit is composition, not a sixth application [ADOPTED]

- **Binds:** all Workflows units, factory preflight
- **Prevents:** COMP-WF / COMP-LIB / extra experiment daemon / extra identity store
- **Rule:** Every new capability names an existing `COMP-*` owner or an explicit connect/extend of one. Minting a new application package or a permanent process besides `qma-daemon`, `qmn`, and QMB process-per-run children is a spine amendment. QMF stays toolbox (L7/L8). “Under QMF” never means one process or one database.

### AD-2 — Four discovery rails; Artifact Library kinds unchanged [ADOPTED]

- **Binds:** UI/agent search, copilot discovery, packaging
- **Prevents:** hypotheses/skills/graph-templates/mini-apps becoming registry kinds; copied-row Library sqlite; `hit_class: strats`
- **Rule:** Product discovery concatenates typed hits. It is never a fourth store and never a door **run**. Frozen hit classes:
  1. `KnowledgeHit` — `{hit_class: knowledge, source_ref, snapshot_ref, locator}`
  2. `ArtifactHit` — `{hit_class: artifact, fp1, kind}` where `kind` ∈ Workbench AD-3 roster or query-hit tags `saved-view` \| `analysis.published`
  3. `ContributionHit` — `{hit_class: contribution, plugin_id, point, qualified_id, package_id, package_version}` from live `published_contributions()`. Identity is that tuple. **Never fp1, never a registry kind, never `ArtifactHit.kind`.** Pins store `(qualified_id, package_version, availability_revision)`, not a descriptor digest. Invoke revalidates the pin (AD-30). Missing/disabled/uninstalled plugin ⇒ typed `unavailable` or `tombstone`, never a silent resolve to another version, never a stale fp1. A hit is not a grant.
  4. Hypothesis listing stays on `qml.research` / `research_ref` and is **refused** on the facade
- Occupancy none. Daemon never `import qmb`. QMB never opens daemon sqlite. Ranked/semantic search stays GAP-0073. Extra Artifact query-hit tags beyond `saved-view` \| `analysis.published` are refused unless this spine is amended. Discovery listings must distinguish **published** vs **configured** vs **granted** vs **reachable** vs **healthy** (AD-15); a ContributionHit is not a grant. Pack `contributes` entries are `{point, local_id}` and expand to ContributionHit at enable. `view:*` is a wire DTO only (AD-17) — **not** a plugin contribution point and **not** a ContributionHit until a named GAP-0081 `ui_view` increment. **DTO owner is COMP-QMA-WIRE** (additive CT-40 family, no new CT number). Query owner of live contributions remains COMP-QMA-DAEMON `published_contributions()`. This AD is the named amendment of mill/wire DEC-0389’s two-class freeze.

### AD-3 — Capability Operation Interface is the shared contract [ADOPTED]

- **Binds:** apps, copilot, workflows, CLI, direct callers
- **Prevents:** untyped `execute(anything)`; HTTP on every module; local file paths as portable ids
- **Rule:** Every public operation publishes a versioned descriptor: stable id, owner COMP, input schema, output **shape** (`value` \| `artifact_ref` \| `job_handle` \| `event` \| `stream`), native cardinality (`one` \| `many` in/out), empty_policy, configuration/defaults, declared operation dependencies, resource needs, documentation refs, validation class, units, version compatibility, effect class (`none` \| `read` \| `append-evidence` \| `mutate-config` \| `place-run` \| `external-egress`), permission requests, execution placement, error/refusal shape, progress, and lifecycle verbs (`start` \| `query-state` \| `cancel` \| `await`). Collection **mapping** is **not** on the descriptor — it lives on Graph Template edges (AD-5). Finite `event` ≠ persistent `stream`. Every public call carries an **InvocationEnvelope** (AD-24) binding contribution tuple, `instance_id`, config revision, grant snapshot, logical invocation/attempt ids, and effect-specific idempotency. Transport (in-process, CLI, wire, future RPC) is an implementation choice of the owner and is never a bypass of that envelope. Durable **file** handoffs cite schema, content fp1, source/run provenance and completeness — never a machine-local path as global id. Content fp1 applies to artifact bytes, **not** to contribution identity (AD-2 tuple). Manifests **request**; the host **grants** structured GrantRecords (AD-24). The only parameter authority is `input_schema`. Representative payloads in `CONTRACTS.md` are schema-complete or explicitly marked fragments; a fragment must not contradict this Rule.

### AD-4 — Four workflow layers stay distinct [ADOPTED]

- **Binds:** Experimentation Board, QMA procedures, QMB doors, QML mill
- **Prevents:** Board-as-run; Stage 0 graph as executor; Skill as Loop; Graph Template as Task Graph
- **Rule:** (1) **Board layout is client-only.** It MUST NOT be a field of `product_session`, Mission, Task Graph, Graph Template, or any sqlite row. Display alias only (Workbench AD-16). Editing the client layout writes nothing. (2) **Graph Template** — authored, versioned, stateless DAG; plugin-contributed. Compile identity is `(qualified_id, version)` from the plugin manifest at enable. Rebuild-on-load MUST NOT change bytes of an enabled `(id, version)`; a byte change is a new version or a disable. Do not fingerprint templates onto the Artifact rail. (3) **Task Graph** — one Mission’s execution projection; persist `edges: {from, to, mapping}` and walk successors (connect/extend `qma.daemon.taskgraph`; today edges are dropped — that is a hole this AD binds closed). Nodes do not carry successor lists. (4) **Ungoverned library call** — `import qmb` / `import qml` on a controlled-room host; writes no Mission. A Stage 0 `graph` is none of these and is never compiled to a bot, Graph Template, or `run_slice`. A loop is node state, not a Skill; Loop `stopping_condition` is a typed stop (max-iterations / budget / predicate), not an opaque string. A Routine **fires** a compile; a schedule/webhook **trigger** is not the workflow definition. Selected-subgraph execution is `MissionCompiler(template.qualified_id, template.version, node_ids)` where `node_ids` is a non-empty induced DAG of that already-registered template version — not a live board scribble, not a board id. One compile → one Mission → one Task Graph whose `graph_template_ref` is the template `qualified_id`. After a semantic rewire, derived results are invalidated; reuse of prior results is allowed only where the operation’s declared semantics permit it (projection vs rerun stays Workbench AD-5).

### AD-5 — Mapping is explicit; no silent Cartesian [ADOPTED]

- **Binds:** typed dataflow, fan-out/join
- **Prevents:** guessed zip vs broadcast vs keyed join vs Cartesian
- **Rule:** Each port declares kind `reference` \| `data` \| `event` \| `control`. Collection mapping is declared on the edge: `one` \| `zip` \| `broadcast` \| `keyed-join` \| `cartesian`. Cartesian requires an explicit flag. Empty collections skip or refuse per the operation’s declared empty-policy. Join algebra (unique keys, expected cardinality, watermark, late/missing/failed partitions, partial retry) is AD-26 and is not guessed from JSON shape. Conditional skip is a node kind, not dropped edges. Validate endpoints and cycles against DAG law (AD-6). Shared mini-app parameters are typed edges of this kind, not ambient globals.

### AD-6 — Graph Template topology is a DAG [ADOPTED]

- **Binds:** `validate_graph_template_topology`, Mission Compiler
- **Prevents:** `A→B→C→A` and `A→A` registering as templates
- **Rule:** Registration refuses self-loops and any directed cycle (reuse the plugin-loader DFS already used for plugin requires). Pairwise reverse-edge checks are insufficient. Runtime **Loops** remain node state (iteration/budget/stop), not template cycles. This amends the inspected implementation hole; it does not revive graph-as-chat.

### AD-7 — Reuse QMA as the procedure runtime; extend in place [ADOPTED]

- **Binds:** Graph Templates, Routines, CT-47 door steps, occupancy
- **Prevents:** a second scheduler; a QMB task-graph module; ExperimentSpec DAG as control flow
- **Rule:** Author in Graph Templates; instantiate via Mission Compiler (one template → one Mission); schedule via RoutineScheduler; place QMB work via `place_procedure_step` (run vs query occupancy unchanged). ExperimentSpec successors are **lineage**, not control-flow edges — CT-07 MUST NOT be walked as graph successors. Persist `task_graph_state` including `edges: {from, to, mapping}` in daemon sqlite (existing named projection, not a new store). Completing a predecessor and making successors ready is **one** sqlite transaction plus outbox (AD-26). Occupancy is **not** a separate table: it is the existing `environment_lease` + Workbench AD-8 door law, folded into `task_graph_state`. QMB does not write daemon occupancy; the daemon maps `JobHandle` ↔ lease using **QMA AD-17** state vocabulary exactly (AD-26). Implement successor dispatch and daemon-evaluated node kinds (`conditional`, `join`, `approval_gate`) in `qma.daemon.taskgraph`. Skills remain knowledge; they never compile to Missions and never grant tools.

### AD-8 — Product sessions are authority overlays, not QMA Session [ADOPTED]

- **Binds:** copilot, mini-apps, wire
- **Prevents:** tab-switch as context change; app-use editing implementation; one global Agent
- **Rule:** `product_session` is a **new journal-projected record kind**, not a QMA `Session` and not a QMA `Profile`. Ids are `psess:`; QMA `Session` ids remain `sess:` and remain the execution container (execution_model + autonomy only). Cardinality is **1 product_session → many QMA Sessions**. `ProductSessionProfile` is a closed enum `{authoring, app-use}`, **immutable at create**, and is **not** `qma.core.ontology.Profile`. `scope_path` does **not** gain a segment — product-session is a wire/header field beside it, never a permission key inside it. Durable fields: `product_session_id`, `profile`, `principal`, `context_revision`, `app_instance_id` (pointer to plugin-install instance row), `granted_ops` (array of `grant_id` referencing structured GrantRecords — AD-24; never a bare op-id string as the grant), `selected_refs` (typed `{kind, id}` only), optional `private_notes` JSON column (not a new store, not MemoryProvider, not Knowledge). **Not durable:** `qma_session_id`, tab attachment, UI layout. Closed `selected_refs` kinds: artifact fp1, `research_ref`, contribution `(qualified_id, package_version)`, template `(qualified_id, version)`, dataset/run/attempt refs, node-id sets citing a template. **Forbidden in selected_refs:** layout JSON, positions, widgets, json-render trees. Select/grant mutations are named wire commands that bump `context_revision` under compare-and-set on `expected_revision` (AD-29). Duplicate `command_id` returns the prior durable result. Reconnect resumes queries/events; it does not replay unacked intent. Tab change writes nothing. A dashboard/account **filter is not a command target**. Analysis access to an instrument is not execution permission. App-use may inspect, invoke exposed operations, adjust permitted runtime inputs, and mint a **change-request** staging kind (QMA AD-22 addable `change_request`; not fp1, not Library, not `promote`). Path: app-use → change request → authoring → **validation** → v2; v1 stays. It must not edit package source, install code, elevate grants, or retarget accounts. Authoring uses granted files/tools/diagnostics. Specialists remain on-demand worker templates (DEC-0374 stays dead). Installation/upgrade MUST NOT mutate an existing row’s `granted_ops` or retarget `app_instance_id`. Packs ship a versioned **copilot integration profile** as a request, not a grant.

### AD-9 — Copilot discovers granted descriptors; prose is not authorization [ADOPTED]

- **Binds:** QuantMind/QMX Copilot, skills, hooks
- **Prevents:** app-supplied text granting tools; rewriting core instructions per install
- **Rule:** The copilot identity is one familiar product surface over QMA infrastructure. Tool availability = intersection of (published ContributionHits, host grants, `product_session` GrantRecords, health). Skills describe behavior; they do not grant. Skill authoring is separated from verification; the same model must not write the skill and certify it. Installation of a skill is not authoring. Hooks may veto/approve at existing QMA events; a model-authored hook cannot override a failed deterministic check or privilege gate. Cross-session retrieval is explicit, attributed, and cannot retarget actions. Explanations cite saved records/tool evidence, not fabricated recollection. Internal QMX context is structured schema, not screenshots as the default. MemoryProvider stays desk-scoped. Product-session private notes are the AD-8 JSON column (retention/export/deletion with the session row), not MemoryProvider, not Knowledge, not telemetry. RLM remains Analysis execution, not a product IDE.

### AD-10 — Four cross-app composition modes [ADOPTED]

- **Binds:** mini-apps, workflows, copilot
- **Prevents:** every function wrapped as an app; one app driving another’s screen
- **Rule:** Supported modes, none compulsory: (1) consume another app’s **saved artifact** by fp1/content id; (2) **invoke** its exported operation through AD-3; (3) **coordinate** several apps via a Graph Template; (4) **composite app** that cites component contribution ids + artifact refs without merging code. A composite is an **instance graph**, not a new Library kind. Independent apps remain independently useful. Shared instances vs separately configured instances are explicit. Dependency diamonds pin versions per instance. Nested invocation does **not** union permissions or propagate the caller’s tools into the callee. Composite authority is the host-granted intersection, never a union of component requests. Bounded cycles of **invocation** require a recursion budget; template topology remains a DAG (AD-6). Partial failure does not silently substitute a different provider or account. A new venue **protocol** is a new VenueClientKind (refused in V1), not an extra account row.

### AD-11 — Default Book/BMS is not a ceiling; dummy Book is forbidden [ADOPTED]

- **Binds:** QMB compile, QMN seats, alternative systems
- **Prevents:** fake Book/BMS fields; silent L36 inversion; treating sensing/research as a complete second trading system
- **Rule:** **Dummy (mechanical):** a CT-22/CT-27/CT-33, or an ATC PolicyPair, is dummy if minted solely to satisfy a required field, or if its policy is identity / no-op / unlimited / pass-through. Sentinel fps (`NULL_BOOK`, empty-object Book, `mis_ref: null` as a fake MIS) are dummy. Dummy is `INVALID_INPUT` at compile, register, validate, simulate, and seat.
- **Three config types, not optional fields on one.** (1) `ResolvedRunConfig` — unchanged; `book_fp1`/`bms_fp1`/`bot_fp1`/fragments **required**; default path to governed evidence, node-paper, live, L17 seats. (2) `AlternativeRunConfig` — Book/BMS/bot keys **absent, not null**; complete second trading system defined by AD-23 (`PolicyPair`, command, admission, evidence, journey). When this composition is selected, QML authoring, QMB evaluation/optimization, optional MIS binding, QMN unattended host, and live **adopt it** — they do not stay secretly Book-shaped. Sequential paper-then-live and L17 human promote still apply. (3) `UngovernedWorkConfig` — those keys **absent, not null**; ungoverned `qmb.run()`, ordinary Python, data-ML, recipes, QMN sensing-only. Sensing-only **is not a seat** and **is not** class (2).
- Alternative **policy inside the default system** remains a complete CT-22/CT-27 that still implements Book/BMS semantics (L36), evaluated by `analysis.rerun` of that fingerprint — not a wrapper around absent policy and not a projection. ATC is not that path. Compare Book vs ATC only on conserved measures both policies define; do not force ATC into the Book R vocabulary or relabel filtered trades as a rerun. MIS/SQS/KSA stay Book-door consumers unless an ATC PolicyPair names a distinct intelligence binding; optional-intelligence means a system may have no MIS consumer, not a fake MIS record. Do not weaken existing compile/fragment tests to admit type (2) or (3) through type (1).

### AD-12 — Data recipes wrap qmf-data; provider ≠ venue [ADOPTED]

- **Binds:** dataset builder, providers, streams
- **Prevents:** QuantDataManager clone; silent source substitution; encoding every fact as bid/ask
- **Rule:** A recipe has **two identities** (AD-31). Definition identity is `(recipe_def_id, recipe_def_version, recipe_def_hash)` and is reviewable before any run. Output identity is the **release fp1** (Workbench AD-13 derived-dataset law) plus CT-07 lineage to the definition and to CT-10/CT-12 inputs (COMP-QMB wrap of COMP-QMF-DATA). Display `recipe_id` is not computational identity. It is not a Library kind. CT-06 recipe kind is deferred until metadata-sharing is required. Recipes declare calendars, timezone, alignment, point-in-time/known-at policy, missing/late policy, units, adjustment, entitlements/licensing, environment/code pins, and output completeness. A new provider tomorrow must not rewrite yesterday’s pinned release. Provider name ≠ meaning; provider ≠ venue ≠ account ≠ instrument. Providers declare coverage, transport (file/API/SDK/CLI/webhook), historical vs poll vs stream, entitlements by **credential reference**, and quality/freshness. Preview ≠ export job ≠ live stream. Replay-to-live follows the stream protocol (AD-28). A stream subscription is not a trading permission. Source disagreement is preserved; production sensing feed is never silently swapped. Heterogeneous non-market facts do not widen CT-10 into untyped JSON: knowledge stays CT-44; session/product facts stay QMA; market/source facts stay CT-10. A new venue **protocol** is a new VenueClientKind, not an extra account.

### AD-13 — Identities stay separate [ADOPTED]

- **Binds:** versioning, results, deployments
- **Prevents:** display-name change invalidating computation; layout edit changing run meaning
- **Rule:** Semantic identity is fp1 (artifacts), `research_ref` (hypotheses), `(qualified_id, package_version)` (contributions — **not** fp1), ExperimentSpec fp1 (coordinated continuity), `composition_fp` (node), `instance_id` (installed mini-app). Display names and Board layouts are UX. A saved **runnable** pins code, config, data release, model weights, environment and dependencies. Retry of an uncertain external action ≠ new experiment. Projection ≠ path-dependent rerun (Workbench AD-5). Three pack states stay distinct: **installed** (bytes present) ≠ **enabled/activated** (roster on) ≠ **session-granted** (AD-8 `granted_ops`). Published package ≠ activation on a trading account.

### AD-14 — Sequential handover; software rollback cannot undo fills [ADOPTED]

- **Binds:** QMN, deployments, two model versions
- **Prevents:** default hot-swap of live positions; HMR (DEC-0366 stays dead)
- **Rule:** Default replacement: develop → evaluate → non-real-money validate → explicit activation after stopped/flat-or-drained handover. The transition is the AD-25 fencing state machine: command-owner epoch, fencing token, typed positions/orders snapshot, residual disposition, predecessor acknowledgement, timeout/escalation, immutable completion evidence. Outstanding positions, UNKNOWN commands, shared-account concurrency are **separate** refusal/drain cases, not a boolean `residual_positions` string. A stale predecessor restart cannot recover command authority from local state. Two MIS/model versions may shadow or bind distinct consumers; one writer per role. Owner means software/control scope, not user money. Software rollback never reverses fills. GAP-0058 single-machine placement stays its own increment.

### AD-15 — Compute placement is preflight, not a toggle sticker [ADOPTED]

- **Binds:** jobs, GPU, remote workers
- **Prevents:** laptop coordinator promising durability because a remote worker exists; unpaid subscription implying API embed
- **Rule:** States are distinct: available / configured / authorized / reachable / healthy. Training ≠ inference ≠ trading deployment. Expensive experiments must not starve protective trading actions. No cloud/Colab/provider is assumed; bind only through existing QMA ExecutionEnvironment / ComputeProvider ports. Cancellation, unknown outcome and checkpoint/resume are job-handle law. Browser/computer-use remain provisionable rungs (GAP-0070/0078) fail-closed until registered.

### AD-16 — Persistence owners stay split; new product records are not qmf-core [ADOPTED]

- **Binds:** stores, recovery
- **Prevents:** all new records in qmf-core; merging QMB JSONL into daemon sqlite
- **Rule:** Evidence: qmf-data rooms + CT-13 journals + registry sqlite + QMB JSONL ledger (including ATC rows tagged `composition_class: alternative`). Coordinated experiment identity: QMA Experiment sqlite. Hypotheses: QML `research_root` blobs. **v1 daemon additions (complete list):** (1) `product_session` journal projection (AD-8); (2) persist existing `task_graph_state` including edges and the AD-26 outbox; (3) mini-app instance rows in the **existing** plugin-install projection, keyed by `instance_id` ≠ `plugin_id`; (4) GrantRecord rows beside product_session (same sqlite, not a new store class). No other new sqlite. Change-request = staging kind `change_request` (AD-8). Recipe **definition** identity is AD-31; output identity remains release fp1 plus CT-07; CT-06 recipe kind deferred. Graph Templates rebuild from plugins but enabled `(qualified_id, version)` bytes are immutable. MemoryProvider remains optional per desk (GAP-0072). Logs are not evidence. Backup/restore stay application-owned using QMF primitives plus an application checkpoint **manifest** (AD-27) that records per-owner fences and restore order. Orphans, corruption, disk exhaustion and cross-store reconstruction are owner-specific: never invent a second evidence database; never silently merge divergent stores.

### AD-17 — UI host contracts now; chrome is GAP-0081 [ADOPTED]

- **Binds:** later desktop/web host
- **Prevents:** every pane as MCP App; json-render as runtime; tab-close cancelling jobs
- **Rule:** The host is a **client** of qma-wire, QMB API/CLI, QMN three doors. Contribution descriptors (navigation, commands, rich views **including editors**, parameter forms, context providers, events, reconnect) are wire-owned DTOs defined in CONTRACTS §14 — **not** a v1 `ui_view` plugin point until a named GAP-0081 increment. The catalogue is not cards-only. JSON Render and MCP Apps are **presentation adapters**. They are not identity, not persistence, not a runtime, **and not authority**. The only parameter authority is AD-3 `input_schema`. The only invoke authority is AD-9 ∩ GrantRecord. A json-render catalog entry MUST name an existing AD-3 `op_id` and MUST NOT add/remove fields. Absence of a catalog entry is native/CLI using the same schema. MCP App HTML MUST NOT grant tools; the host intercepts every tool call and refuses if outside the session’s GrantRecords. Pack `view:*` is a wire DTO, not a plugin point, not a json-render runtime id, not an fp1. Native QMX panes remain first. UI mount/dispose must not start/kill durable backend work. Stale snapshot/cursor refuses invoke. Headless packs appear as reusable AD-3 steps without navigation. QMB remains the only operator CLI; QMA and QMN ship none. Do not pin `@json-render/*` in this sitting.

### AD-18 — Packages export without private lineage or secrets [ADOPTED]

- **Binds:** install/export/import
- **Prevents:** marketplace (DEC-0361 dead); secrets in packs (L34); author chats as required payload
- **Rule:** A pack is versioned: manifest, contribution list, requested capabilities, compatibility range, migrations. Lifecycle is AD-30 (downloaded / installed / validated / enabled / disabled / uninstalled) with a transition journal, atomic roster publication, and QMA AD-21 `down` or `forward_only` migrations. Install / configure / enable / disable / validate / pin / rollback / dependency-removal / export / import are host operations. First-party trust in v1; custom packs are explicit operator enable. Missing dependency is a hard error at enable, not warning-and-continue (do not copy Hermes advisory-dep behaviour). Partial install rolls back to the last usable roster. Side-by-side versions allowed; running work stays pinned to the instance it started. `exports_secrets: false` is a request; an independent export scanner is the oracle and replaces secret values with typed refs.

### AD-19 — Mutation testing is a test-strength principle [ADOPTED]

- **Binds:** later QA, not this sitting’s runtime
- **Prevents:** mutmut as a product dependency; `mutmut apply` on shared worktrees; mutation score as architecture proof
- **Rule:** Behaviour oracles (BDD/journeys) come first. Then contract/integration, state-machine, fault-injection, and **optional** mutation testing of existing Python tests. mutmut (current docs 2026-09-18) requires `os.fork` — Windows execution is WSL only. Run only on disposable copies. Classify surviving/equivalent/invalid/timeout. Caliper-style skill evaluation is a later QMA adapter question, not a CLI assumption.

### AD-20 — Defaults and templates ship with a custom path [ADOPTED]

- **Binds:** first usable slice
- **Prevents:** empty canvas; everything-must-be-a-node
- **Rule:** Ship enough defaults (data preview, governed backtest door, library search, authoring vs app-use shells) that real work is possible. Custom granularity is operator-chosen: wrap notebooks/scripts as operations, or expose selected stages. Graph editing is not the only programming route (L9).

### AD-21 — Headless parity of operations [ADOPTED]

- **Binds:** CLI, library, node, copilot
- **Prevents:** UI-only semantics; a privileged general terminal
- **Rule:** Deep behaviour of an AD-3 operation is identical across **that operation’s supported doors**. Supported-door sets are per `op_id` and recorded in CONTRACTS §15. QMB remains the **only** operator CLI. QMA and QMN ship no operator CLI; their operations use library and qma-wire adapters, and may be invoked through QMB-owned orchestration when the owner is QMB. Unsupported door → typed `unsupported_door`, never a newly minted `qma`/`qmn` CLI. A useful log/progress panel is not a general shell.

### AD-22 — Portfolio Manager is a label, not an identity rewrite [ADOPTED]

- **Binds:** QMA Role prose, skills, glossary
- **Prevents:** silent `desk_slug` / `ActorId` / plugin-prefix rename; F07 closure
- **Rule:** Trading-floor Role display becomes **Portfolio Manager**. Keep `desk_slug=pm` and `pm-coordination` until a GAP-0083 migration sitting. Preserve BMAD Product Manager. Combining two bots’ equity streams stays deferred (F07 / Workbench AD-5).

### AD-23 — Alternative Trading Composition is a complete second system [ADOPTED]

- **Binds:** replaceable portfolio/risk/sizing compositions; BR-MKT-02; J03b; QML/QMB/MIS/QMN consumers
- **Prevents:** dummy Book/BMS; calling sensing or `UngovernedWorkConfig` a complete trading system; treating Book/BMS as the kit; swapping live mid-position
- **Rule:** Book/BMS is one specific **portfolio accounting + risk + position-sizing** implementation — the default, not the ceiling. An Alternative Trading Composition (ATC) is `AlternativeRunConfig` whose Book/BMS/bot keys are **absent, not null**. It MUST carry a `PolicyPair` of `AccountingPolicy` + `RiskPolicy`, both complete (the dummy test in AD-11 applies). **AccountingPolicy** declares cash identity, position identity, fill application, valuation marks, currency, and residual meaning. **RiskPolicy** declares limits, halt, sizing, UNKNOWN handling, and the override principal. **Command** binds venue, account, role, instrument, adapter capability, credential ref, and AD-25 owner epoch — a dashboard filter is not a target. **Admission** checks PolicyPair completeness, grants, health, sequential paper-then-live readiness, and L17 human promote before any live `VenueClientKind`. That promote is operating discipline already in the transcript (“do not replace a Book and trade tomorrow”), not a later architecture question. **Adopt:** QML authoring, QMB backtest/optimize, optional MIS/intelligence binding, QMN unattended host, and live bind to the **selected** composition version. A Book-shaped consumer must not silently remain when the composition is ATC. **Evidence** is QMB JSONL tagged `composition_class: alternative` plus CT-07 lineage to the PolicyPair hash; it is not a Book journal and not qmf-core. Compare with the default path only on conserved measures both policies define. End-to-end: author PolicyPair (optionally as a mini-app/workflow) → validate → simulate against pinned CT-10/replay → paper on node → fenced sequential handover onto live. QMN remains the only `qmf-venue` importer. No new COMP. No dummy CT-22/CT-27/CT-33. Two versions (e.g. scalping Book v1 vs v2, or Book vs Kelly) are distinct `composition_fp`s; they do not share a command-owner epoch.

### AD-24 — Invocation envelope and structured grants [ADOPTED]

- **Binds:** every public AD-3 call, including headless and nested
- **Prevents:** retry duplicating external effects; invoking the right op against the wrong instance; grant widening on upgrade
- **Rule:** Every public call carries `InvocationEnvelope`: `logical_invocation_id`, monotonic `attempt_id`, `op_id`/`op_version`, contribution `(qualified_id, package_version)`, `instance_id`, `config_revision`, optional caller/callee `psess:` refs, `grant_id` snapshot, `effect_class`, `idempotency_key`, `reconcile_policy`, `input_hash`. Ambiguous instance/config resolution refuses. Idempotency is effect-specific: `none`/`read` may retry; `append-evidence` dedupes on the key; `mutate-config` is CAS on `config_revision`; `place-run` treats `logical_invocation_id` as the run identity; `external-egress` MUST obtain a receipt or become `unknown` and MUST NOT blind-retry. `reconcile_policy` is `query-then-decide` \| `unknown-manual` \| `never-retry`. GrantRecord is immutable after mint: `grant_id`, principal, audience, contribution tuple, `instance_id`, `config_revision`, `op_id`/`op_version`, `effect_class`, parameter ceiling, `account_scope` (null unless granted), `expires_at`, optional `revoked_at`. `product_session.granted_ops` stores `grant_id`s. Upgrade, re-resolution, or a new package version cannot widen or retarget an existing grant; that requires an explicit re-grant that bumps `context_revision`.

### AD-25 — Command-owner fencing for sequential deploy [ADOPTED]

- **Binds:** QMN seats, Book path, ATC venue path
- **Prevents:** dual writers; stale predecessor restart; untyped residuals; software rollback of fills
- **Rule:** One command owner per `(account, venue, role)`. Transition states, in order: `idle` → `drain-requested` → `draining` → (`residuals-attributed` \| `unknown-blocked`) → `predecessor-acked` → `fenced-activate` → `active` → `retired`. Required records: `command_owner_epoch`, `fencing_token` (QMN issues venue tokens; QMB issues internal ATC-simulate tokens), account, venue kind, `composition_fp`, typed `positions_snapshot` and `orders_snapshot`, `residual_disposition` (`flatten` \| `transfer-to-successor` \| `hold-manual`), predecessor ack, timeout/escalation, immutable completion evidence. `unknown-blocked` is terminal for this attempt until operator reconcile; it is never an automatic retry. A process restart presenting a stale epoch or token is refused. Software rollback after a new-owner fill cannot unfill. This machine applies to the default Book path and to ATC (simulate tokens and, after paper-then-live + L17, venue tokens).

### AD-26 — Durable workflow: outbox, JobHandle parent vocab, join algebra [ADOPTED]

- **Binds:** `qma.daemon.taskgraph`, JobHandle, mapping edges
- **Prevents:** lost/duplicate successor dispatch; a second job dialect; guessed join results; a second scheduler
- **Rule:** Completing predecessor A and making successor B ready is one daemon-sqlite transaction: (1) persist A terminal, (2) persist successor eligibility at a revision, (3) write an outbox row per newly ready successor. The dispatcher reads the outbox, invokes B with AD-24 `logical_invocation_id`, and acks the outbox. Crash recovery replays unacked outbox rows; dispatch is idempotent on the envelope. No second scheduler. **JobHandle** reuses QMA AD-17 exactly: `queued` \| `running` \| `done` \| `failed` \| `cancelled` \| `aborted` \| `unknown`. Terminal = `done`/`failed`/`cancelled`/`aborted`. `unknown` is non-terminal and holds `environment_lease`. `cancelled` is explicit cancel; `aborted` is known environmental non-completion; timeout/lost supervisor is `unknown`, never `failed` or `aborted`. `awaiting_approval` is a Mission/Task gate, not a JobHandle state. Each handle records `logical_run_id`, `attempt_id`, artifact inventory with completeness `complete` \| `partial` \| `missing` \| `expired`. First durable terminal wins a cancel/complete race; later commands are no-ops recorded against that terminal. **Join algebra** per AD-5 mapping: stable `partition_id`; expected cardinality; keyed-join unique keys (duplicate policy declared: `refuse` or `first-wins`); watermark `all-expected` \| `timeout` \| `failed-aggregation`; late arrival after watermark is `late`, not silently merged; partial retry re-invokes only failed `partition_id`s and reuses successful artifacts via their `logical_invocation_id`. Output order is sorted by `partition_id` unless the edge declares otherwise.

### AD-27 — Application checkpoint manifest, not a second evidence database [ADOPTED]

- **Binds:** backup/restore across QMA sqlite, QMB JSONL, QMF rooms, QML blobs, artifact bytes
- **Prevents:** central evidence DB; silent merge of divergent stores; treating missing ack as non-execution
- **Rule:** COMP-QMA-DAEMON owns a `CheckpointManifest` (journal-projected, not a new store class) listing per-owner `{owner, store, fence, content_hash}` and a restore order: QMF rooms → QMB JSONL (including ATC) → QML blobs → artifact bytes → QMA sqlite projections. Each owner restores its own store using existing primitives (QMA AD-27 five-step for daemon projections; QMF backup for rooms). After restore, verify cross-store references. Missing/corrupt refs become `orphan` and are quarantined; they are never silently merged. External-effect reconcile hooks run after local restore; absence of acknowledgement is `unknown`, not proof of non-execution. UI disconnect, coordinator loss, and worker loss remain distinct (AD-15).

### AD-28 — Stream protocol: epoch, cutover, leases [ADOPTED]

- **Binds:** replay/live market and data streams
- **Prevents:** silent loss/duplication; provider/venue conflation; one consumer tearing down a shared feed; replay authorizing live commands
- **Rule:** A subscription carries `sub_id`, `channel`, `source_id` (provider), optional `venue_id` (never the same field), `epoch`, monotonic `sequence`, `event_time`, `receive_time`, phase `replay` \| `cutover` \| `live`, `cutover_watermark`, cursor, bounded buffer, `backpressure_policy` (`block` \| `disconnect` \| `spill-with-evidence`), gap/duplicate/late events, heartbeat, `consumer_id`, and a reference count. Cutover is atomic at the watermark: events at-or-before are replay; after are live. Overload cannot silently drop market-driving events; the declared policy and loss evidence must be visible. Cancelling one consumer decrements the refcount; the shared upstream stays until refcount is 0. Replay provenance cannot be interpreted as a live command absent an explicit, granted policy. A stream subscription is not trading permission.

### AD-29 — Product-session CAS, reconnect, and change-request completeness [ADOPTED]

- **Binds:** `psess:` commands, app-use handoff
- **Prevents:** tab-owned context; replayed intent on reconnect; app-use applying implementation edits; stale change requests
- **Rule:** Mutations are `mutate(product_session_id, expected_revision, command_id, payload)` → `ok(new_revision, result)` \| `conflict(current_revision)` \| `duplicate(prior_result)`. Queries do not bump revision. Reconnect is a query from the client cursor; it never re-issues an unacked command without the original `command_id`. Change-request payload MUST include source `psess:`, source `instance_id`/`config_revision`, target refs, **base hashes** of those refs, `context_revision` at mint, `request_hash`, typed patch, validation result, `conflict` \| `rebase-required` \| `valid`, and — after authoring apply — apply evidence. App-use mints; authoring + operator principal applies; `promote` remains L17 and is not this path.

### AD-30 — Package lifecycle, atomic roster, pin/invoke, export oracle [ADOPTED]

- **Binds:** pack install/enable/export; ContributionHit invoke
- **Prevents:** corrupt index; secret leakage by self-assertion; pin resolving to another version
- **Rule:** Pack states: `downloaded` → `installed` → `validated` → `enabled` ⇄ `disabled` → `uninstalled`. Each transition is journaled. Roster publication is atomic (stage, fsync, swap). Failed validation/migration restores the last usable roster. Migrations follow QMA AD-21 (`down` or `forward_only` with operator confirmation). Uninstall names dependants; in-flight pinned runs keep the bytes they started with. Session-granted is AD-8, not a pack state. Pin of a ContributionHit stores `(qualified_id, package_version, availability_revision)`. Invoke revalidates; disabled/uninstalled → `unavailable` or `tombstone`, never another version. Export scanner is independent of the manifest: it must prove absence of secret values, private paths, and transcripts, and must rewrite remaining secrets to typed refs. Manifest `exports_secrets: false` without a passing scan is not evidence.

### AD-31 — Recipe-definition identity and complete recipe schema [ADOPTED]

- **Binds:** data recipes, ML/data work without bot wrap
- **Prevents:** treating a release fp1 as the authored recipe; incomplete temporal/unit/licensing semantics
- **Rule:** `RecipeDefinition` identity is `(recipe_def_id, recipe_def_version, recipe_def_hash)`. It is reviewable and pinnable before execution. A run produces a new output **release fp1** (Workbench AD-13) with CT-07 lineage to the definition and to each input revision. Two runs of one definition are two releases, not two recipes. Display rename does not change `recipe_def_hash`. The definition schema includes inputs (provider, coverage, schema/roles, units, timezone/calendar, freshness, provenance, entitlement, licensing, revision), transforms (alignment, known-at/no-lookahead, missing/late policy, adjustment), split policy, environment/code pins, and output completeness. Preview ≠ export ≠ stream. Non-trading outputs need no CT-33/Book/QMN wrap (AD-11 class 3).

## Consistency Conventions

| Concern | Convention |
| --- | --- |
| Naming | Capability / extension / workflow / mini-app / widget stay distinct. Say research-paper / node-paper; never bare paper. QMA `plugin` stays QMA-scoped. Stage 0 field is `graph`, never Confluence. Experimentation Board is the exploratory surface name. |
| Identity | Artifacts `fp1`; hypotheses `research_ref`; contributions `(qualified_id, package_version)` never fp1; product sessions `psess:` ≠ QMA `sess:`; recipe definition `(recipe_def_id, version, hash)` ≠ release fp1. Display names are UX. |
| QMA store class | `product_session` is a **journal-derived projection** (QMA AD-6 class), not an independent store and not the Session fold. `task_graph_state` remains the existing named projection, now durable, including the AD-26 outbox. Backup/restore follow QMA AD-27 for those projections plus this sitting’s AD-27 checkpoint manifest. |
| JobHandle | QMA AD-17 vocabulary only: `queued`/`running`/`done`/`failed`/`cancelled`/`aborted`/`unknown`. Never `succeeded` or `awaiting_approval` on a handle. |
| Errors | Typed refusals (CT-04) at every public boundary. Doors render, never swallow. ATC without a complete PolicyPair is `INVALID_INPUT`. Live ATC without paper-then-live + L17 is `not_promoted`. Dummy Book remains `INVALID_INPUT`. |
| Claim labels | `existing` / `connect` / `amend` / `new` / `deferred`. Package tests are not cross-component adoption. |
| Occupancy | QMB **run** commands occupy one slot per ExecutionEnvironment; queries do not. Federated search occupancy none. |
| Extensibility | Add adapters, descriptors, library functions, or QMA pack contributions — never a new tunnel or untyped dispatch. |
| Docs vs code | Class/test existence is not e2e (DEC-0286). ADR-0023 remains provisional. |

## Stack

Inherited pins stand. This sitting adds **no** required runtime. Presentation and mutation-testing tools are optional later.

| Name | Version |
| --- | --- |
| CPython | 3.14 (observed 3.14.6 at 270e992; docs 3.14.7 current at last stack verify — not upgraded here) |
| uv workspace + lockfile | inherited (`docs/architecture/stack.md`) |
| QMF stores | Parquet, DuckDB, SQLite, JSONL behind QMF contracts |
| QMA daemon store | SQLite single writer (inherited); product sessions + task_graph_state added per AD-16/AD-7 |
| Optuna | `optuna==4.9.0` in qmb — TPE search only |
| json-render | not pinned — presentation candidate; upstream v0.20.0 as of 2026-08-18 |
| MCP Apps | SEP-1865 stable 2026-01-26 — presentation candidate, not storage |
| mutmut | not a dependency; optional WSL/POSIX later |
| Hermes / n8n / OpenBB / LEAN | mental models only; not imported runtimes |

## Structural Seed

```text
qmx-agents/packages/qma-core/     # operation descriptor types; product-session profile nouns
qmx-agents/packages/qma-wire/     # ContributionHit; session commands/queries; UI contribution DTOs
qmx-agents/packages/qma-daemon/   # Graph Template DAG; Task Graph edges+sqlite; product sessions
qmx-agents/plugins/*/             # first-party packs; published_contributions
qmb/src/qmb/                      # doors + library.search + data wrap; no task graph
qml/src/qml/research/             # Stage 0 (exists @ 270e992)
qml/src/qml/host/research_store.py
qmn/src/qmn/                      # host/supervision; Book-shaped operable path; sensing-only without Book
packages/qmf-data/                # rooms, CT-10/12; recipes wrap here
packages/qmf-registry/            # kinds; Library projection
```

```mermaid
flowchart LR
  subgraph rails [discovery facade]
    K[KnowledgeHit]
    A[ArtifactHit]
    C[ContributionHit]
  end
  subgraph off [not on facade]
    H[hypothesis research_ref]
  end
  K --> CITE[CT-44]
  A --> LIB[qmb library.search]
  C --> PUB[published_contributions]
  H --> QML[qml.research listing]
```

```mermaid
sequenceDiagram
  participant U as User
  participant AU as App-use session
  participant CR as Change request
  participant AR as Authoring session
  U->>AU: inspect run/version
  AU->>AU: invoke granted ops only
  AU->>CR: mint staging artifact
  CR->>AR: new session with scoped refs
  AR->>AR: develop v2
  Note over AU: v1 instance and grants unchanged
```

## Capability → Architecture Map

| Capability / Area | Lives in | Governed by |
| --- | --- | --- |
| Artifact Library | QMB B-15 + registry as-of | AD-2, Workbench AD-3 |
| Capability discovery | QMA published_contributions + wire DTO | AD-2, AD-3, AD-9 |
| Workflows runtime | QMA taskgraph + Routines + CT-47 | AD-4, AD-6, AD-7 |
| Experimentation Board | UX projection | AD-1, AD-4, AD-13 |
| Copilot profiles | qma-wire + daemon sqlite | AD-8, AD-9 |
| Mini-apps / composite apps | packs + AD-3 exports | AD-10, AD-18 |
| Data recipes / providers | QMB wrap qmf-data | AD-12 |
| Default Book/BMS system | QMB compile + QMN seats | AD-11 |
| Alternative Trading Composition | QMB PolicyPair + ATC journal; QMN adopts selected composition | AD-11, AD-23, AD-25 |
| Non-Book research / sensing | ungoverned run; QMN sensing-only — not ATC | AD-11 class 3 |
| Invocation / grants | qma-wire envelope + daemon GrantRecord | AD-24, AD-8, AD-9 |
| Durable workflow | taskgraph outbox + join + JobHandle | AD-7, AD-26 |
| Streams | QMB wrap of qmf-data | AD-12, AD-28 |
| UI host contracts | qma-wire DTOs | AD-17, GAP-0081 chrome |
| Sequential deploy | QMN + human L17 + fencing | AD-14, AD-25 |
| Cross-store restore | owner stores + checkpoint manifest | AD-16, AD-27 |
| Test strength | later QA | AD-19 |

## Deferred

| Item | Why it can wait |
| --- | --- |
| Final visual layout / branding | GAP-0081 chrome; INT-29 |
| Constitution L36 prose rewrite | Named amendment is decided here (Book/BMS = default implementation of accounting/risk roles). Documentation Factory writes the constitution text. |
| F07 synthetic portfolio | Workbench AD-5; not a projection |
| GAP-0058 single-machine node | Own increment; VPS proceeds |
| GAP-0062 always-on host machine | Property decided (daemon+remote+outbox); machine unruled |
| GAP-0063 generator algorithm / GAP-0085 nouns | Do not fill |
| MemoryProvider production backend | GAP-0072 |
| Browser/desktop env provisioning | GAP-0070 / GAP-0078 fail-closed |
| Marketplace / capability solver | DEC-0361 / 0362 dead |
| Hot-apply settings / HMR | GAP-0052 / DEC-0366 |
| mutmut in CI | Optional later; WSL required on Windows |
| json-render / MCP Apps as pinned deps | Presentation candidates until UI sitting chooses a host stack |
| `desk_slug=pm` rename | GAP-0083 identity migration |
| Hypothesis listing API | Mill blob exists; browse listing is a small connect |
| QMA wire listener dispatch | Connect existing vocabulary; not a new runtime |
