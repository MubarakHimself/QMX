#!/usr/bin/env python3
"""Append Workflows construction-kit change-mode YAML. Run once from project root. Idempotent by id."""
from pathlib import Path

ROOT = Path(r"C:/Users/Mubarak/Desktop/QMX")


def already(text: str, needle: str) -> bool:
    return needle in text


def append_if_missing(path: Path, marker: str, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if already(text, marker):
        print(f"skip {path.name}: {marker} already present")
        return
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + block, encoding="utf-8")
    print(f"appended {marker} -> {path.name}")


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if label in text and old not in text:
        print(f"skip {path.name}: {label} already patched")
        return
    if old not in text:
        raise SystemExit(f"{path.name}: block not found for {label}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"patched {label} -> {path.name}")


def patch_gap_0081(path: Path) -> None:
    old = """    note: "AD-5 wire. The qma-ui-contract package ships as a stub only in v1. The wire contract (AD-5) and the variables registry (AD-26) are NOT deferred and bind now. Carried forward: the UI reads as a trading/research terminal, not a generic agent dashboard (operator, T-5071, T-5082-5084)."
    date: 2026-08-29"""
    new = """    note: "AD-5 wire. The qma-ui-contract package ships as a stub only in v1. The wire contract (AD-5) and the variables registry (AD-26) are NOT deferred and bind now. Carried forward: the UI reads as a trading/research terminal, not a generic agent dashboard (operator, T-5071, T-5082-5084). 2026-09-19 Workflows: UI-host contracts (AD-17 / DEC-0430 DTOs) fold now; chrome stays deferred on this row (DEC-0446)."
    date: 2026-09-19"""
    if "UI-host contracts (AD-17 / DEC-0430 DTOs) fold now" in path.read_text(encoding="utf-8"):
        print("skip gaps.yaml: GAP-0081 already patched")
        return
    replace_once(path, old, new, "GAP-0081 2026-09-19")


MANIFEST = r"""
- id: SRC-21
  path: _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/
  kind: rider
  role: primary
  status: harvested
  note: "2026-09-18/19 QMX Workflows construction-kit architecture sitting (candidate qmx-workflows-arch-2026-09-19-c; OD-01 CLOSED): ARCHITECTURE-SPINE.md (local AD-1..AD-31 plus Inherited Invariants, Consistency Conventions, Stack), CHALLENGE-RECONCILIATION.md (prefer §1/§6/§8 over residual AF-01 OD-01 deferred cells), OPERATOR-QUESTIONS.md (OD-01 CLOSED), CONTRACTS.md, JOURNEYS.md, REQUIREMENTS-ADDENDUM.md, CONFLICT-REGISTER.md C-05 row only (footer stale). Citation surface for the Workflows increment (EXT-2246..EXT-2285). Do not fold as current law: ARCHITECTURE-CANDIDATE-MANIFEST.json (still 2026-09-18-a), IMPLEMENTATION-SEQUENCE.md Blockers now, CODEX-RECHECK-HANDOFF.md wait text, empty companions/ and contracts/ dirs, Stage A reviews/review-adversarial.md as judgment of 2026-09-19-c. Parents QMF/QMB/QML/NODE/QMA/CONNECT/Workbench/mill bind read-only. Local AD ids do not renumber parents. Planning on main; implementation inspected on integration@270e992995c2378ca63cf6343254ef8140a8c97e."
- id: SRC-22
  path: _docwork/riders/workflows-construction-kit-2026-09-19.md
  kind: rider
  role: primary
  status: harvested
  note: "Operator-direct rider for the 2026-09-19 documentation-factory change-mode session: standing corrections (no sixth COMP; Book/BMS default not ceiling; sessions≠tabs; app-use cannot edit; sequential paper-then-live; BDD=spec; mutmut optional; n8n/OpenBB/Hermes mental models); L36 named amendment; DEC-0389 named amendment without whole-supersession; wiring honesty @ 270e992; dead-list honors; out-of-pass (no GAP-0085/0063/0061/0062/0058 fill; no new COMP/CT; no production code). Citation surface for operator rulings (DEC-0445..DEC-0451 and standing corrections EXT-2246)."
- id: SRC-23
  path: _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/transcript-refresh-20260919/Explore-Node-Editor-Architecture.md
  kind: transcript
  role: primary
  status: harvested
  no_chunks: "Original Explore-Node-Editor-Architecture transcript harvested for operator words only (OD-01 close ~L1061 Book/BMS replace; Kelly; adopt-the-chain; sequential not tomorrow; sessions not tabs; app-use cannot edit). House treatment: no chunk index; spine/rider remain citation surface for sitting law."
  note: "Operator-words citation surface for OD-01 close and related dictation (EXT-2247). Not a second spine."
"""

EXTR = r"""
  - id: EXT-2246
    type: decision
    summary: "Operator-direct standing corrections for Workflows construction-kit fold: QMF is one framework (no sixth COMP); Book/BMS is the default portfolio/risk/sizing stack not the ceiling and never dummy; when that stack is replaced QML/QMB/MIS/QMN/paper/live adopt the selected composition; research/sensing is not a trading system; sessions own context and grants (tabs do not); app-use cannot edit implementation or apply its own changes; specialists remain; trading-floor PM means Portfolio Manager (preserve BMAD Product Manager; do not rewrite desk_slug=pm / GAP-0083); sequential cutover not hot-swap, paper then live, human L17 promote remains; BDD/Gherkin is specification not executed proof; mutmut optional (WSL/POSIX, disposable copy, never mutmut apply on shared worktree); n8n/Hermes/OpenBB/JSON Render/MCP Apps/LEAN/QuantConnect are mental models only."
    quote: "QMF is one framework. No sixth COMP. Book/BMS is the default, not the ceiling. Never dummy Book/BMS. Sessions own context and grants; tabs do not. App-use cannot edit."
    cite: SRC-22
    topics: [workflows, rider, standing-corrections, no-sixth-comp]
    authority: rider
  - id: EXT-2247
    type: decision
    summary: "OD-01 is CLOSED from Explore-Node-Editor-Architecture.md (~L1061): Book/BMS may be replaced or improved (Kelly example); adopt-the-chain across QML/QMB/MIS/QMN/paper/live; sequential paper-then-live not tomorrow; never dummy Book. ATC class (AD-11/AD-23) is operator-direct. Architecture companions still saying AWAITING_OPERATOR_OD01 or OD-01 unanswered are stale; OPERATOR-QUESTIONS.md and RESUME-STATE.md win."
    quote: "OD-01 CLOSED from the original transcript. Replace/improve Book/BMS; Kelly; adopt-the-chain; sequential not tomorrow; never fake a Book."
    cite: SRC-23
    topics: [workflows, od-01, atc, book-bms]
    authority: rider
  - id: EXT-2248
    type: decision
    summary: "Workflows AD-1 — Construction kit is composition, not a sixth application. Every new capability names an existing COMP-* owner or an explicit connect/extend of one. Minting a new application package or a permanent process besides qma-daemon, qmn, and QMB process-per-run children is a spine amendment. QMF stays toolbox (L7/L8). “Under QMF” never means one process or one database."
    quote: "Every new capability names an existing COMP-* owner or an explicit connect/extend of one. Minting a new application package or a permanent process besides qma-daemon, qmn, and QMB process-per-run children is a spine amendment. QMF stays toolbox (L7/L8). “Under QMF” never means one process or one database."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-1
    topics: [workflows, ad-1]
    authority: rider
  - id: EXT-2249
    type: decision
    summary: "Workflows AD-2 — Four discovery rails; Artifact Library kinds unchanged. Product discovery concatenates typed hits. It is never a fourth store and never a door run. Frozen hit classes: 1. KnowledgeHit — {hit_class: knowledge, source_ref, snapshot_ref, locator} 2. ArtifactHit — {hit_class: artifact, fp1, kind} where kind ∈ Workbench AD-3 roster or query-hit tags saved-view \\| analysis.published 3. ContributionHit — {hit_class: contribution, plugin_id, point, qualified_id, package_id, package_version} from live published_contributions(). Identity is that tuple. Never fp1, never a registry kind, never ArtifactHit.kind. Pins store (qualified_id, package_version, availability_revision), not a descriptor digest. Invoke revalidates the pin (AD-30). Missing/disabled/uninstalled plugin ⇒ typed unavailable or tombstone, never a silent resolve to another version, never a stale fp1. A hit is not a grant. 4. Hypothesis listing stays on qml.research / research_ref and is refused on the facade - Occupancy none. Daemon never import qmb. QMB never opens daemon sqlite. Ranked/semantic search stays GAP-0073. Extra Artifact query-hit tags beyond saved-view \\| analysis.published are refused unless t..."
    quote: "Product discovery concatenates typed hits. It is never a fourth store and never a door run. Frozen hit classes: 1. KnowledgeHit — {hit_class: knowledge, source_ref, snapshot_ref, locator} 2. ArtifactHit — {hit_class: artifact, fp1, kind} where kind ∈ Workbench AD-3 roster or query-hit tags saved-view \\| analysis.pub..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-2
    topics: [workflows, ad-2]
    authority: rider
  - id: EXT-2250
    type: decision
    summary: "Workflows AD-3 — Capability Operation Interface is the shared contract. Every public operation publishes a versioned descriptor: stable id, owner COMP, input schema, output shape (value \\| artifact_ref \\| job_handle \\| event \\| stream), native cardinality (one \\| many in/out), empty_policy, configuration/defaults, declared operation dependencies, resource needs, documentation refs, validation class, units, version compatibility, effect class (none \\| read \\| append-evidence \\| mutate-config \\| place-run \\| external-egress), permission requests, execution placement, error/refusal shape, progress, and lifecycle verbs (start \\| query-state \\| cancel \\| await). Collection mapping is not on the descriptor — it lives on Graph Template edges (AD-5). Finite event ≠ persistent stream. Every public call carries an InvocationEnvelope (AD-24) binding contribution tuple, instance_id, config revision, grant snapshot, logical invocation/attempt ids, and effect-specific idempotency. Transport (in-process, CLI, wire, future RPC) is an implementation choice of the owner and is never a bypass of that envelope. Durable file handoffs cite schema, content fp1, source/run provenance and completeness —..."
    quote: "Every public operation publishes a versioned descriptor: stable id, owner COMP, input schema, output shape (value \\| artifact_ref \\| job_handle \\| event \\| stream), native cardinality (one \\| many in/out), empty_policy, configuration/defaults, declared operation dependencies, resource needs, documentation refs, vali..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-3
    topics: [workflows, ad-3]
    authority: rider
  - id: EXT-2251
    type: decision
    summary: "Workflows AD-4 — Four workflow layers stay distinct. (1) Board layout is client-only. It MUST NOT be a field of product_session, Mission, Task Graph, Graph Template, or any sqlite row. Display alias only (Workbench AD-16). Editing the client layout writes nothing. (2) Graph Template — authored, versioned, stateless DAG; plugin-contributed. Compile identity is (qualified_id, version) from the plugin manifest at enable. Rebuild-on-load MUST NOT change bytes of an enabled (id, version); a byte change is a new version or a disable. Do not fingerprint templates onto the Artifact rail. (3) Task Graph — one Mission’s execution projection; persist edges: {from, to, mapping} and walk successors (connect/extend qma.daemon.taskgraph; today edges are dropped — that is a hole this AD binds closed). Nodes do not carry successor lists. (4) Ungoverned library call — import qmb / import qml on a controlled-room host; writes no Mission. A Stage 0 graph is none of these and is never compiled to a bot, Graph Template, or run_slice. A loop is node state, not a Skill; Loop stopping_condition is a typed stop (max-iterations / budget / predicate), not an opaque string. A Routine fires a compile; a sche..."
    quote: "(1) Board layout is client-only. It MUST NOT be a field of product_session, Mission, Task Graph, Graph Template, or any sqlite row. Display alias only (Workbench AD-16). Editing the client layout writes nothing. (2) Graph Template — authored, versioned, stateless DAG; plugin-contributed. Compile identity is (qualifi..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-4
    topics: [workflows, ad-4]
    authority: rider
  - id: EXT-2252
    type: decision
    summary: "Workflows AD-5 — Mapping is explicit; no silent Cartesian. Each port declares kind reference \\| data \\| event \\| control. Collection mapping is declared on the edge: one \\| zip \\| broadcast \\| keyed-join \\| cartesian. Cartesian requires an explicit flag. Empty collections skip or refuse per the operation’s declared empty-policy. Join algebra (unique keys, expected cardinality, watermark, late/missing/failed partitions, partial retry) is AD-26 and is not guessed from JSON shape. Conditional skip is a node kind, not dropped edges. Validate endpoints and cycles against DAG law (AD-6). Shared mini-app parameters are typed edges of this kind, not ambient globals."
    quote: "Each port declares kind reference \\| data \\| event \\| control. Collection mapping is declared on the edge: one \\| zip \\| broadcast \\| keyed-join \\| cartesian. Cartesian requires an explicit flag. Empty collections skip or refuse per the operation’s declared empty-policy. Join algebra (unique keys, expected cardinali..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-5
    topics: [workflows, ad-5]
    authority: rider
  - id: EXT-2253
    type: decision
    summary: "Workflows AD-6 — Graph Template topology is a DAG. Registration refuses self-loops and any directed cycle (reuse the plugin-loader DFS already used for plugin requires). Pairwise reverse-edge checks are insufficient. Runtime Loops remain node state (iteration/budget/stop), not template cycles. This amends the inspected implementation hole; it does not revive graph-as-chat."
    quote: "Registration refuses self-loops and any directed cycle (reuse the plugin-loader DFS already used for plugin requires). Pairwise reverse-edge checks are insufficient. Runtime Loops remain node state (iteration/budget/stop), not template cycles. This amends the inspected implementation hole; it does not revive graph-a..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-6
    topics: [workflows, ad-6]
    authority: rider
  - id: EXT-2254
    type: decision
    summary: "Workflows AD-7 — Reuse QMA as the procedure runtime; extend in place. Author in Graph Templates; instantiate via Mission Compiler (one template → one Mission); schedule via RoutineScheduler; place QMB work via place_procedure_step (run vs query occupancy unchanged). ExperimentSpec successors are lineage, not control-flow edges — CT-07 MUST NOT be walked as graph successors. Persist task_graph_state including edges: {from, to, mapping} in daemon sqlite (existing named projection, not a new store). Completing a predecessor and making successors ready is one sqlite transaction plus outbox (AD-26). Occupancy is not a separate table: it is the existing environment_lease + Workbench AD-8 door law, folded into task_graph_state. QMB does not write daemon occupancy; the daemon maps JobHandle ↔ lease using QMA AD-17 state vocabulary exactly (AD-26). Implement successor dispatch and daemon-evaluated node kinds (conditional, join, approval_gate) in qma.daemon.taskgraph. Skills remain knowledge; they never compile to Missions and never grant tools."
    quote: "Author in Graph Templates; instantiate via Mission Compiler (one template → one Mission); schedule via RoutineScheduler; place QMB work via place_procedure_step (run vs query occupancy unchanged). ExperimentSpec successors are lineage, not control-flow edges — CT-07 MUST NOT be walked as graph successors. Persist ta..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-7
    topics: [workflows, ad-7]
    authority: rider
  - id: EXT-2255
    type: decision
    summary: "Workflows AD-8 — Product sessions are authority overlays, not QMA Session. product_session is a new journal-projected record kind, not a QMA Session and not a QMA Profile. Ids are psess:; QMA Session ids remain sess: and remain the execution container (execution_model + autonomy only). Cardinality is 1 product_session → many QMA Sessions. ProductSessionProfile is a closed enum {authoring, app-use}, immutable at create, and is not qma.core.ontology.Profile. scope_path does not gain a segment — product-session is a wire/header field beside it, never a permission key inside it. Durable fields: product_session_id, profile, principal, context_revision, app_instance_id (pointer to plugin-install instance row), granted_ops (array of grant_id referencing structured GrantRecords — AD-24; never a bare op-id string as the grant), selected_refs (typed {kind, id} only), optional private_notes JSON column (not a new store, not MemoryProvider, not Knowledge). Not durable: qma_session_id, tab attachment, UI layout. Closed selected_refs kinds: artifact fp1, research_ref, contribution (qualified_id, package_version), template (qualified_id, version), dataset/run/attempt refs, node-id sets citing ..."
    quote: "product_session is a new journal-projected record kind, not a QMA Session and not a QMA Profile. Ids are psess:; QMA Session ids remain sess: and remain the execution container (execution_model + autonomy only). Cardinality is 1 product_session → many QMA Sessions. ProductSessionProfile is a closed enum {authoring, ..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-8
    topics: [workflows, ad-8]
    authority: rider
  - id: EXT-2256
    type: decision
    summary: "Workflows AD-9 — Copilot discovers granted descriptors; prose is not authorization. The copilot identity is one familiar product surface over QMA infrastructure. Tool availability = intersection of (published ContributionHits, host grants, product_session GrantRecords, health). Skills describe behavior; they do not grant. Skill authoring is separated from verification; the same model must not write the skill and certify it. Installation of a skill is not authoring. Hooks may veto/approve at existing QMA events; a model-authored hook cannot override a failed deterministic check or privilege gate. Cross-session retrieval is explicit, attributed, and cannot retarget actions. Explanations cite saved records/tool evidence, not fabricated recollection. Internal QMX context is structured schema, not screenshots as the default. MemoryProvider stays desk-scoped. Product-session private notes are the AD-8 JSON column (retention/export/deletion with the session row), not MemoryProvider, not Knowledge, not telemetry. RLM remains Analysis execution, not a product IDE."
    quote: "The copilot identity is one familiar product surface over QMA infrastructure. Tool availability = intersection of (published ContributionHits, host grants, product_session GrantRecords, health). Skills describe behavior; they do not grant. Skill authoring is separated from verification; the same model must not write..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-9
    topics: [workflows, ad-9]
    authority: rider
  - id: EXT-2257
    type: decision
    summary: "Workflows AD-10 — Four cross-app composition modes. Supported modes, none compulsory: (1) consume another app’s saved artifact by fp1/content id; (2) invoke its exported operation through AD-3; (3) coordinate several apps via a Graph Template; (4) composite app that cites component contribution ids + artifact refs without merging code. A composite is an instance graph, not a new Library kind. Independent apps remain independently useful. Shared instances vs separately configured instances are explicit. Dependency diamonds pin versions per instance. Nested invocation does not union permissions or propagate the caller’s tools into the callee. Composite authority is the host-granted intersection, never a union of component requests. Bounded cycles of invocation require a recursion budget; template topology remains a DAG (AD-6). Partial failure does not silently substitute a different provider or account. A new venue protocol is a new VenueClientKind (refused in V1), not an extra account row."
    quote: "Supported modes, none compulsory: (1) consume another app’s saved artifact by fp1/content id; (2) invoke its exported operation through AD-3; (3) coordinate several apps via a Graph Template; (4) composite app that cites component contribution ids + artifact refs without merging code. A composite is an instance grap..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-10
    topics: [workflows, ad-10]
    authority: rider
  - id: EXT-2258
    type: decision
    summary: "Workflows AD-11 — Default Book/BMS is not a ceiling; dummy Book is forbidden. Dummy (mechanical): a CT-22/CT-27/CT-33, or an ATC PolicyPair, is dummy if minted solely to satisfy a required field, or if its policy is identity / no-op / unlimited / pass-through. Sentinel fps (NULL_BOOK, empty-object Book, mis_ref: null as a fake MIS) are dummy. Dummy is INVALID_INPUT at compile, register, validate, simulate, and seat. - Three config types, not optional fields on one. (1) ResolvedRunConfig — unchanged; book_fp1/bms_fp1/bot_fp1/fragments required; default path to governed evidence, node-paper, live, L17 seats. (2) AlternativeRunConfig — Book/BMS/bot keys absent, not null; complete second trading system defined by AD-23 (PolicyPair, command, admission, evidence, journey). When this composition is selected, QML authoring, QMB evaluation/optimization, optional MIS binding, QMN unattended host, and live adopt it — they do not stay secretly Book-shaped. Sequential paper-then-live and L17 human promote still apply. (3) UngovernedWorkConfig — those keys absent, not null; ungoverned qmb.run(), ordinary Python, data-ML, recipes, QMN sensing-only. Sensing-only is not a seat and is not class (..."
    quote: "Dummy (mechanical): a CT-22/CT-27/CT-33, or an ATC PolicyPair, is dummy if minted solely to satisfy a required field, or if its policy is identity / no-op / unlimited / pass-through. Sentinel fps (NULL_BOOK, empty-object Book, mis_ref: null as a fake MIS) are dummy. Dummy is INVALID_INPUT at compile, register, valid..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-11
    topics: [workflows, ad-11]
    authority: rider
  - id: EXT-2259
    type: decision
    summary: "Workflows AD-12 — Data recipes wrap qmf-data; provider ≠ venue. A recipe has two identities (AD-31). Definition identity is (recipe_def_id, recipe_def_version, recipe_def_hash) and is reviewable before any run. Output identity is the release fp1 (Workbench AD-13 derived-dataset law) plus CT-07 lineage to the definition and to CT-10/CT-12 inputs (COMP-QMB wrap of COMP-QMF-DATA). Display recipe_id is not computational identity. It is not a Library kind. CT-06 recipe kind is deferred until metadata-sharing is required. Recipes declare calendars, timezone, alignment, point-in-time/known-at policy, missing/late policy, units, adjustment, entitlements/licensing, environment/code pins, and output completeness. A new provider tomorrow must not rewrite yesterday’s pinned release. Provider name ≠ meaning; provider ≠ venue ≠ account ≠ instrument. Providers declare coverage, transport (file/API/SDK/CLI/webhook), historical vs poll vs stream, entitlements by credential reference, and quality/freshness. Preview ≠ export job ≠ live stream. Replay-to-live follows the stream protocol (AD-28). A stream subscription is not a trading permission. Source disagreement is preserved; production sensing ..."
    quote: "A recipe has two identities (AD-31). Definition identity is (recipe_def_id, recipe_def_version, recipe_def_hash) and is reviewable before any run. Output identity is the release fp1 (Workbench AD-13 derived-dataset law) plus CT-07 lineage to the definition and to CT-10/CT-12 inputs (COMP-QMB wrap of COMP-QMF-DATA). ..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-12
    topics: [workflows, ad-12]
    authority: rider
  - id: EXT-2260
    type: decision
    summary: "Workflows AD-13 — Identities stay separate. Semantic identity is fp1 (artifacts), research_ref (hypotheses), (qualified_id, package_version) (contributions — not fp1), ExperimentSpec fp1 (coordinated continuity), composition_fp (node), instance_id (installed mini-app). Display names and Board layouts are UX. A saved runnable pins code, config, data release, model weights, environment and dependencies. Retry of an uncertain external action ≠ new experiment. Projection ≠ path-dependent rerun (Workbench AD-5). Three pack states stay distinct: installed (bytes present) ≠ enabled/activated (roster on) ≠ session-granted (AD-8 granted_ops). Published package ≠ activation on a trading account."
    quote: "Semantic identity is fp1 (artifacts), research_ref (hypotheses), (qualified_id, package_version) (contributions — not fp1), ExperimentSpec fp1 (coordinated continuity), composition_fp (node), instance_id (installed mini-app). Display names and Board layouts are UX. A saved runnable pins code, config, data release, m..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-13
    topics: [workflows, ad-13]
    authority: rider
  - id: EXT-2261
    type: decision
    summary: "Workflows AD-14 — Sequential handover; software rollback cannot undo fills. Default replacement: develop → evaluate → non-real-money validate → explicit activation after stopped/flat-or-drained handover. The transition is the AD-25 fencing state machine: command-owner epoch, fencing token, typed positions/orders snapshot, residual disposition, predecessor acknowledgement, timeout/escalation, immutable completion evidence. Outstanding positions, UNKNOWN commands, shared-account concurrency are separate refusal/drain cases, not a boolean residual_positions string. A stale predecessor restart cannot recover command authority from local state. Two MIS/model versions may shadow or bind distinct consumers; one writer per role. Owner means software/control scope, not user money. Software rollback never reverses fills. GAP-0058 single-machine placement stays its own increment."
    quote: "Default replacement: develop → evaluate → non-real-money validate → explicit activation after stopped/flat-or-drained handover. The transition is the AD-25 fencing state machine: command-owner epoch, fencing token, typed positions/orders snapshot, residual disposition, predecessor acknowledgement, timeout/escalation..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-14
    topics: [workflows, ad-14]
    authority: rider
  - id: EXT-2262
    type: decision
    summary: "Workflows AD-15 — Compute placement is preflight, not a toggle sticker. States are distinct: available / configured / authorized / reachable / healthy. Training ≠ inference ≠ trading deployment. Expensive experiments must not starve protective trading actions. No cloud/Colab/provider is assumed; bind only through existing QMA ExecutionEnvironment / ComputeProvider ports. Cancellation, unknown outcome and checkpoint/resume are job-handle law. Browser/computer-use remain provisionable rungs (GAP-0070/0078) fail-closed until registered."
    quote: "States are distinct: available / configured / authorized / reachable / healthy. Training ≠ inference ≠ trading deployment. Expensive experiments must not starve protective trading actions. No cloud/Colab/provider is assumed; bind only through existing QMA ExecutionEnvironment / ComputeProvider ports. Cancellation, u..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-15
    topics: [workflows, ad-15]
    authority: rider
  - id: EXT-2263
    type: decision
    summary: "Workflows AD-16 — Persistence owners stay split; new product records are not qmf-core. Evidence: qmf-data rooms + CT-13 journals + registry sqlite + QMB JSONL ledger (including ATC rows tagged composition_class: alternative). Coordinated experiment identity: QMA Experiment sqlite. Hypotheses: QML research_root blobs. v1 daemon additions (complete list): (1) product_session journal projection (AD-8); (2) persist existing task_graph_state including edges and the AD-26 outbox; (3) mini-app instance rows in the existing plugin-install projection, keyed by instance_id ≠ plugin_id; (4) GrantRecord rows beside product_session (same sqlite, not a new store class). No other new sqlite. Change-request = staging kind change_request (AD-8). Recipe definition identity is AD-31; output identity remains release fp1 plus CT-07; CT-06 recipe kind deferred. Graph Templates rebuild from plugins but enabled (qualified_id, version) bytes are immutable. MemoryProvider remains optional per desk (GAP-0072). Logs are not evidence. Backup/restore stay application-owned using QMF primitives plus an application checkpoint manifest (AD-27) that records per-owner fences and restore order. Orphans, corruption..."
    quote: "Evidence: qmf-data rooms + CT-13 journals + registry sqlite + QMB JSONL ledger (including ATC rows tagged composition_class: alternative). Coordinated experiment identity: QMA Experiment sqlite. Hypotheses: QML research_root blobs. v1 daemon additions (complete list): (1) product_session journal projection (AD-8); (..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-16
    topics: [workflows, ad-16]
    authority: rider
  - id: EXT-2264
    type: decision
    summary: "Workflows AD-17 — UI host contracts now; chrome is GAP-0081. The host is a client of qma-wire, QMB API/CLI, QMN three doors. Contribution descriptors (navigation, commands, rich views including editors, parameter forms, context providers, events, reconnect) are wire-owned DTOs defined in CONTRACTS §14 — not a v1 ui_view plugin point until a named GAP-0081 increment. The catalogue is not cards-only. JSON Render and MCP Apps are presentation adapters. They are not identity, not persistence, not a runtime, and not authority. The only parameter authority is AD-3 input_schema. The only invoke authority is AD-9 ∩ GrantRecord. A json-render catalog entry MUST name an existing AD-3 op_id and MUST NOT add/remove fields. Absence of a catalog entry is native/CLI using the same schema. MCP App HTML MUST NOT grant tools; the host intercepts every tool call and refuses if outside the session’s GrantRecords. Pack view:* is a wire DTO, not a plugin point, not a json-render runtime id, not an fp1. Native QMX panes remain first. UI mount/dispose must not start/kill durable backend work. Stale snapshot/cursor refuses invoke. Headless packs appear as reusable AD-3 steps without navigation. QMB rema..."
    quote: "The host is a client of qma-wire, QMB API/CLI, QMN three doors. Contribution descriptors (navigation, commands, rich views including editors, parameter forms, context providers, events, reconnect) are wire-owned DTOs defined in CONTRACTS §14 — not a v1 ui_view plugin point until a named GAP-0081 increment. The catal..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-17
    topics: [workflows, ad-17]
    authority: rider
  - id: EXT-2265
    type: decision
    summary: "Workflows AD-18 — Packages export without private lineage or secrets. A pack is versioned: manifest, contribution list, requested capabilities, compatibility range, migrations. Lifecycle is AD-30 (downloaded / installed / validated / enabled / disabled / uninstalled) with a transition journal, atomic roster publication, and QMA AD-21 down or forward_only migrations. Install / configure / enable / disable / validate / pin / rollback / dependency-removal / export / import are host operations. First-party trust in v1; custom packs are explicit operator enable. Missing dependency is a hard error at enable, not warning-and-continue (do not copy Hermes advisory-dep behaviour). Partial install rolls back to the last usable roster. Side-by-side versions allowed; running work stays pinned to the instance it started. exports_secrets: false is a request; an independent export scanner is the oracle and replaces secret values with typed refs."
    quote: "A pack is versioned: manifest, contribution list, requested capabilities, compatibility range, migrations. Lifecycle is AD-30 (downloaded / installed / validated / enabled / disabled / uninstalled) with a transition journal, atomic roster publication, and QMA AD-21 down or forward_only migrations. Install / configur..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-18
    topics: [workflows, ad-18]
    authority: rider
  - id: EXT-2266
    type: decision
    summary: "Workflows AD-19 — Mutation testing is a test-strength principle. Behaviour oracles (BDD/journeys) come first. Then contract/integration, state-machine, fault-injection, and optional mutation testing of existing Python tests. mutmut (current docs 2026-09-18) requires os.fork — Windows execution is WSL only. Run only on disposable copies. Classify surviving/equivalent/invalid/timeout. Caliper-style skill evaluation is a later QMA adapter question, not a CLI assumption."
    quote: "Behaviour oracles (BDD/journeys) come first. Then contract/integration, state-machine, fault-injection, and optional mutation testing of existing Python tests. mutmut (current docs 2026-09-18) requires os.fork — Windows execution is WSL only. Run only on disposable copies. Classify surviving/equivalent/invalid/timeo..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-19
    topics: [workflows, ad-19]
    authority: rider
  - id: EXT-2267
    type: decision
    summary: "Workflows AD-20 — Defaults and templates ship with a custom path. Ship enough defaults (data preview, governed backtest door, library search, authoring vs app-use shells) that real work is possible. Custom granularity is operator-chosen: wrap notebooks/scripts as operations, or expose selected stages. Graph editing is not the only programming route (L9)."
    quote: "Ship enough defaults (data preview, governed backtest door, library search, authoring vs app-use shells) that real work is possible. Custom granularity is operator-chosen: wrap notebooks/scripts as operations, or expose selected stages. Graph editing is not the only programming route (L9)."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-20
    topics: [workflows, ad-20]
    authority: rider
  - id: EXT-2268
    type: decision
    summary: "Workflows AD-21 — Headless parity of operations. Deep behaviour of an AD-3 operation is identical across that operation’s supported doors. Supported-door sets are per op_id and recorded in CONTRACTS §15. QMB remains the only operator CLI. QMA and QMN ship no operator CLI; their operations use library and qma-wire adapters, and may be invoked through QMB-owned orchestration when the owner is QMB. Unsupported door → typed unsupported_door, never a newly minted qma/qmn CLI. A useful log/progress panel is not a general shell."
    quote: "Deep behaviour of an AD-3 operation is identical across that operation’s supported doors. Supported-door sets are per op_id and recorded in CONTRACTS §15. QMB remains the only operator CLI. QMA and QMN ship no operator CLI; their operations use library and qma-wire adapters, and may be invoked through QMB-owned orch..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-21
    topics: [workflows, ad-21]
    authority: rider
  - id: EXT-2269
    type: decision
    summary: "Workflows AD-22 — Portfolio Manager is a label, not an identity rewrite. Trading-floor Role display becomes Portfolio Manager. Keep desk_slug=pm and pm-coordination until a GAP-0083 migration sitting. Preserve BMAD Product Manager. Combining two bots’ equity streams stays deferred (F07 / Workbench AD-5)."
    quote: "Trading-floor Role display becomes Portfolio Manager. Keep desk_slug=pm and pm-coordination until a GAP-0083 migration sitting. Preserve BMAD Product Manager. Combining two bots’ equity streams stays deferred (F07 / Workbench AD-5)."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-22
    topics: [workflows, ad-22]
    authority: rider
  - id: EXT-2270
    type: decision
    summary: "Workflows AD-23 — Alternative Trading Composition is a complete second system. Book/BMS is one specific portfolio accounting + risk + position-sizing implementation — the default, not the ceiling. An Alternative Trading Composition (ATC) is AlternativeRunConfig whose Book/BMS/bot keys are absent, not null. It MUST carry a PolicyPair of AccountingPolicy + RiskPolicy, both complete (the dummy test in AD-11 applies). AccountingPolicy declares cash identity, position identity, fill application, valuation marks, currency, and residual meaning. RiskPolicy declares limits, halt, sizing, UNKNOWN handling, and the override principal. Command binds venue, account, role, instrument, adapter capability, credential ref, and AD-25 owner epoch — a dashboard filter is not a target. Admission checks PolicyPair completeness, grants, health, sequential paper-then-live readiness, and L17 human promote before any live VenueClientKind. That promote is operating discipline already in the transcript (“do not replace a Book and trade tomorrow”), not a later architecture question. Adopt: QML authoring, QMB backtest/optimize, optional MIS/intelligence binding, QMN unattended host, and live bind to the sel..."
    quote: "Book/BMS is one specific portfolio accounting + risk + position-sizing implementation — the default, not the ceiling. An Alternative Trading Composition (ATC) is AlternativeRunConfig whose Book/BMS/bot keys are absent, not null. It MUST carry a PolicyPair of AccountingPolicy + RiskPolicy, both complete (the dummy te..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-23
    topics: [workflows, ad-23]
    authority: rider
  - id: EXT-2271
    type: decision
    summary: "Workflows AD-24 — Invocation envelope and structured grants. Every public call carries InvocationEnvelope: logical_invocation_id, monotonic attempt_id, op_id/op_version, contribution (qualified_id, package_version), instance_id, config_revision, optional caller/callee psess: refs, grant_id snapshot, effect_class, idempotency_key, reconcile_policy, input_hash. Ambiguous instance/config resolution refuses. Idempotency is effect-specific: none/read may retry; append-evidence dedupes on the key; mutate-config is CAS on config_revision; place-run treats logical_invocation_id as the run identity; external-egress MUST obtain a receipt or become unknown and MUST NOT blind-retry. reconcile_policy is query-then-decide \\| unknown-manual \\| never-retry. GrantRecord is immutable after mint: grant_id, principal, audience, contribution tuple, instance_id, config_revision, op_id/op_version, effect_class, parameter ceiling, account_scope (null unless granted), expires_at, optional revoked_at. product_session.granted_ops stores grant_ids. Upgrade, re-resolution, or a new package version cannot widen or retarget an existing grant; that requires an explicit re-grant that bumps context_revision."
    quote: "Every public call carries InvocationEnvelope: logical_invocation_id, monotonic attempt_id, op_id/op_version, contribution (qualified_id, package_version), instance_id, config_revision, optional caller/callee psess: refs, grant_id snapshot, effect_class, idempotency_key, reconcile_policy, input_hash. Ambiguous instan..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-24
    topics: [workflows, ad-24]
    authority: rider
  - id: EXT-2272
    type: decision
    summary: "Workflows AD-25 — Command-owner fencing for sequential deploy. One command owner per (account, venue, role). Transition states, in order: idle → drain-requested → draining → (residuals-attributed \\| unknown-blocked) → predecessor-acked → fenced-activate → active → retired. Required records: command_owner_epoch, fencing_token (QMN issues venue tokens; QMB issues internal ATC-simulate tokens), account, venue kind, composition_fp, typed positions_snapshot and orders_snapshot, residual_disposition (flatten \\| transfer-to-successor \\| hold-manual), predecessor ack, timeout/escalation, immutable completion evidence. unknown-blocked is terminal for this attempt until operator reconcile; it is never an automatic retry. A process restart presenting a stale epoch or token is refused. Software rollback after a new-owner fill cannot unfill. This machine applies to the default Book path and to ATC (simulate tokens and, after paper-then-live + L17, venue tokens)."
    quote: "One command owner per (account, venue, role). Transition states, in order: idle → drain-requested → draining → (residuals-attributed \\| unknown-blocked) → predecessor-acked → fenced-activate → active → retired. Required records: command_owner_epoch, fencing_token (QMN issues venue tokens; QMB issues internal ATC-sim..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-25
    topics: [workflows, ad-25]
    authority: rider
  - id: EXT-2273
    type: decision
    summary: "Workflows AD-26 — Durable workflow: outbox, JobHandle parent vocab, join algebra. Completing predecessor A and making successor B ready is one daemon-sqlite transaction: (1) persist A terminal, (2) persist successor eligibility at a revision, (3) write an outbox row per newly ready successor. The dispatcher reads the outbox, invokes B with AD-24 logical_invocation_id, and acks the outbox. Crash recovery replays unacked outbox rows; dispatch is idempotent on the envelope. No second scheduler. JobHandle reuses QMA AD-17 exactly: queued \\| running \\| done \\| failed \\| cancelled \\| aborted \\| unknown. Terminal = done/failed/cancelled/aborted. unknown is non-terminal and holds environment_lease. cancelled is explicit cancel; aborted is known environmental non-completion; timeout/lost supervisor is unknown, never failed or aborted. awaiting_approval is a Mission/Task gate, not a JobHandle state. Each handle records logical_run_id, attempt_id, artifact inventory with completeness complete \\| partial \\| missing \\| expired. First durable terminal wins a cancel/complete race; later commands are no-ops recorded against that terminal. Join algebra per AD-5 mapping: stable partition_id; expe..."
    quote: "Completing predecessor A and making successor B ready is one daemon-sqlite transaction: (1) persist A terminal, (2) persist successor eligibility at a revision, (3) write an outbox row per newly ready successor. The dispatcher reads the outbox, invokes B with AD-24 logical_invocation_id, and acks the outbox. Crash r..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-26
    topics: [workflows, ad-26]
    authority: rider
  - id: EXT-2274
    type: decision
    summary: "Workflows AD-27 — Application checkpoint manifest, not a second evidence database. COMP-QMA-DAEMON owns a CheckpointManifest (journal-projected, not a new store class) listing per-owner {owner, store, fence, content_hash} and a restore order: QMF rooms → QMB JSONL (including ATC) → QML blobs → artifact bytes → QMA sqlite projections. Each owner restores its own store using existing primitives (QMA AD-27 five-step for daemon projections; QMF backup for rooms). After restore, verify cross-store references. Missing/corrupt refs become orphan and are quarantined; they are never silently merged. External-effect reconcile hooks run after local restore; absence of acknowledgement is unknown, not proof of non-execution. UI disconnect, coordinator loss, and worker loss remain distinct (AD-15)."
    quote: "COMP-QMA-DAEMON owns a CheckpointManifest (journal-projected, not a new store class) listing per-owner {owner, store, fence, content_hash} and a restore order: QMF rooms → QMB JSONL (including ATC) → QML blobs → artifact bytes → QMA sqlite projections. Each owner restores its own store using existing primitives (QMA..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-27
    topics: [workflows, ad-27]
    authority: rider
  - id: EXT-2275
    type: decision
    summary: "Workflows AD-28 — Stream protocol: epoch, cutover, leases. A subscription carries sub_id, channel, source_id (provider), optional venue_id (never the same field), epoch, monotonic sequence, event_time, receive_time, phase replay \\| cutover \\| live, cutover_watermark, cursor, bounded buffer, backpressure_policy (block \\| disconnect \\| spill-with-evidence), gap/duplicate/late events, heartbeat, consumer_id, and a reference count. Cutover is atomic at the watermark: events at-or-before are replay; after are live. Overload cannot silently drop market-driving events; the declared policy and loss evidence must be visible. Cancelling one consumer decrements the refcount; the shared upstream stays until refcount is 0. Replay provenance cannot be interpreted as a live command absent an explicit, granted policy. A stream subscription is not trading permission."
    quote: "A subscription carries sub_id, channel, source_id (provider), optional venue_id (never the same field), epoch, monotonic sequence, event_time, receive_time, phase replay \\| cutover \\| live, cutover_watermark, cursor, bounded buffer, backpressure_policy (block \\| disconnect \\| spill-with-evidence), gap/duplicate/late..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-28
    topics: [workflows, ad-28]
    authority: rider
  - id: EXT-2276
    type: decision
    summary: "Workflows AD-29 — Product-session CAS, reconnect, and change-request completeness. Mutations are mutate(product_session_id, expected_revision, command_id, payload) → ok(new_revision, result) \\| conflict(current_revision) \\| duplicate(prior_result). Queries do not bump revision. Reconnect is a query from the client cursor; it never re-issues an unacked command without the original command_id. Change-request payload MUST include source psess:, source instance_id/config_revision, target refs, base hashes of those refs, context_revision at mint, request_hash, typed patch, validation result, conflict \\| rebase-required \\| valid, and — after authoring apply — apply evidence. App-use mints; authoring + operator principal applies; promote remains L17 and is not this path."
    quote: "Mutations are mutate(product_session_id, expected_revision, command_id, payload) → ok(new_revision, result) \\| conflict(current_revision) \\| duplicate(prior_result). Queries do not bump revision. Reconnect is a query from the client cursor; it never re-issues an unacked command without the original command_id. Chang..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-29
    topics: [workflows, ad-29]
    authority: rider
  - id: EXT-2277
    type: decision
    summary: "Workflows AD-30 — Package lifecycle, atomic roster, pin/invoke, export oracle. Pack states: downloaded → installed → validated → enabled ⇄ disabled → uninstalled. Each transition is journaled. Roster publication is atomic (stage, fsync, swap). Failed validation/migration restores the last usable roster. Migrations follow QMA AD-21 (down or forward_only with operator confirmation). Uninstall names dependants; in-flight pinned runs keep the bytes they started with. Session-granted is AD-8, not a pack state. Pin of a ContributionHit stores (qualified_id, package_version, availability_revision). Invoke revalidates; disabled/uninstalled → unavailable or tombstone, never another version. Export scanner is independent of the manifest: it must prove absence of secret values, private paths, and transcripts, and must rewrite remaining secrets to typed refs. Manifest exports_secrets: false without a passing scan is not evidence."
    quote: "Pack states: downloaded → installed → validated → enabled ⇄ disabled → uninstalled. Each transition is journaled. Roster publication is atomic (stage, fsync, swap). Failed validation/migration restores the last usable roster. Migrations follow QMA AD-21 (down or forward_only with operator confirmation). Uninstall na..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-30
    topics: [workflows, ad-30]
    authority: rider
  - id: EXT-2278
    type: decision
    summary: "Workflows AD-31 — Recipe-definition identity and complete recipe schema. RecipeDefinition identity is (recipe_def_id, recipe_def_version, recipe_def_hash). It is reviewable and pinnable before execution. A run produces a new output release fp1 (Workbench AD-13) with CT-07 lineage to the definition and to each input revision. Two runs of one definition are two releases, not two recipes. Display rename does not change recipe_def_hash. The definition schema includes inputs (provider, coverage, schema/roles, units, timezone/calendar, freshness, provenance, entitlement, licensing, revision), transforms (alignment, known-at/no-lookahead, missing/late policy, adjustment), split policy, environment/code pins, and output completeness. Preview ≠ export ≠ stream. Non-trading outputs need no CT-33/Book/QMN wrap (AD-11 class 3)."
    quote: "RecipeDefinition identity is (recipe_def_id, recipe_def_version, recipe_def_hash). It is reviewable and pinnable before execution. A run produces a new output release fp1 (Workbench AD-13) with CT-07 lineage to the definition and to each input revision. Two runs of one definition are two releases, not two recipes. D..."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-31
    topics: [workflows, ad-31]
    authority: rider
  - id: EXT-2279
    type: decision
    summary: "Workflows construction-kit umbrella: local AD-1..AD-31 adopted in full as DEC-0414..DEC-0444. Paradigm is composition over existing applications (capability / extension / workflow / mini-app / widget). ADR-0024 + SCN-0018..0022 are docs authority only. Implementation authorization remains factory-pipeline-only."
    quote: "Fold AD-1..AD-31. Do not self-ratify missing design. Implementation authorization remains factory-pipeline-only."
    cite: SRC-21:ARCHITECTURE-SPINE.md
    topics: [workflows, umbrella, spine-adoption]
    authority: rider
  - id: EXT-2280
    type: decision
    summary: "Preflight verdict: reuse existing applications. new COMP: none. new CT: none. No new depends_on edge. Owners: COMP-QMA-WIRE + COMP-QMA-DAEMON (ContributionHit/published_contributions); COMP-QMA-CORE + COMP-QMA-WIRE (Operation descriptor/InvocationEnvelope/GrantRecord); COMP-QMA-DAEMON + COMP-QMA-WIRE (product_session CAS); COMP-QMA-DAEMON/CORE (DAG validator); COMP-QMA-DAEMON (Task Graph edges/outbox/JobHandle); COMP-QMB + COMP-QML + COMP-QMN + COMP-QMF-RISK (ATC PolicyPair); COMP-QMB wrap of COMP-QMF-DATA (recipes); COMP-QMN (fencing). Candidates refused: COMP-WF/COMP-LIB/sixth COMP; new CT-*; marketplace; solver; HMR; QMA import qmb; dummy Book; sensing-as-ATC; hit_class strats; Stage 0 graph as executor."
    quote: "reuse existing applications. new COMP: none. new CT: none."
    cite: SRC-21:ARCHITECTURE-SPINE.md#design-paradigm
    topics: [workflows, preflight, reuse, no-new-comp]
    authority: rider
  - id: EXT-2281
    type: open
    summary: "Cheap-veto A1-A6 (operator may overturn in one line): A1 PolicyPair field catalogue; A2 AD-25 fencing state enum; A3 InvocationEnvelope full field set + effect-specific idempotency matrix; A4 ContributionHit pin tuple (qualified_id, package_version, availability_revision); A5 Recipe definition identity (recipe_def_id, version, hash); A6 CheckpointManifest restore order. Defaults proceed. Not vetoable: no sixth COMP; dummy Book INVALID_INPUT; sessions≠tabs; app-use cannot edit; QMN sole venue importer; L17; sequential paper-then-live; BDD=spec; mutmut optional."
    quote: "AD-24..AD-31 machines ratified with cheap-veto A1-A6. Focused Codex recheck of AD-23..AD-31 was skipped."
    cite: SRC-22
    topics: [workflows, cheap-veto, a1-a6]
    authority: rider
  - id: EXT-2282
    type: decision
    summary: "L36 named amendment: keep bot → Book → BMS → operator as the default authority chain. Book and BMS are the default implementations of accounting and risk/sizing roles, not the only implementations the framework may host. A complete alternative PolicyPair may occupy those roles without dummy records. Human L17 promote and sequential paper-then-live remain. QMN remains the only venue importer."
    quote: "Book/BMS are default implementations of accounting and risk/sizing roles, not the ceiling. Complete PolicyPair may occupy those roles without dummy records."
    cite: SRC-22
    topics: [workflows, l36, law, book-bms, atc]
    authority: rider
  - id: EXT-2283
    type: decision
    summary: "Named amendment of DEC-0389 two-class freeze: product discovery adds ContributionHit as a third frozen hit class (AD-2 / DEC-0415). The rest of DEC-0389 stands — occupancy none, no hit_class strats, no qml_candidate, hypotheses remain off the Library facade and are found through qml.research. Do not whole-supersede DEC-0389; leave the mill package provisional."
    quote: "This AD is the named amendment of mill/wire DEC-0389's two-class freeze. Hypotheses stay refused on the facade."
    cite: SRC-21:ARCHITECTURE-SPINE.md#ad-2
    topics: [workflows, dec-0389, contribution-hit, amendment]
    authority: rider
  - id: EXT-2284
    type: context
    summary: "Wiring honesty at integration@270e992995c2378ca63cf6343254ef8140a8c97e: federated discovery is still KnowledgeHit|ArtifactHit only; ContributionHit proposed not on wire; product_session absent; TaskGraph store in-memory (edges dropped / outbox absent); QML→QMB→QMN cross-component integration unsupported (P2-INT-001). Class/test existence is not e2e (DEC-0286 stands). Do not use 8510c03 for absence claims."
    quote: "At 270e992: TaskGraph store is in-memory; ContributionHit is proposed; product sessions are absent; QML→QMB→QMN is unsupported integration."
    cite: SRC-22
    topics: [workflows, wiring, source-inspected, 270e992]
    authority: rider
  - id: EXT-2285
    type: death
    summary: "Dead list honored: DEC-0084/0085/0086 stay dead; DEC-0361 marketplace, DEC-0362 solver, DEC-0366 HMR stay dead; DEC-0408..0413 mill deaths stay dead. No hit_class strats. No qml_candidate hit class. Hypotheses stay off the Library facade. No COMP-WF / COMP-LIB / sixth COMP. No Stage 0 graph as workflow executor."
    quote: "DEC-0084 / 0085 / 0086 stay dead. DEC-0361 marketplace, DEC-0362 solver, DEC-0366 HMR stay dead. DEC-0408..0413 mill deaths stay dead."
    cite: SRC-22
    topics: [workflows, dead-list]
    authority: rider
"""

LEDGER = r"""
  - id: DEC-0414
    title: "Workflows AD-1 — Construction kit is composition, not a sixth application"
    statement: "Every new capability names an existing COMP-* owner or an explicit connect/extend of one. Minting a new application package or a permanent process besides qma-daemon, qmn, and QMB process-per-run children is a spine amendment. QMF stays toolbox (L7/L8). “Under QMF” never means one process or one database."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-1. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2248]
    authority: rider
    component: COMP-QMA-CORE
    tags: [workflows, ad-1]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-1"

  - id: DEC-0415
    title: "Workflows AD-2 — Four discovery rails; Artifact Library kinds unchanged"
    statement: "Product discovery concatenates typed hits. It is never a fourth store and never a door run. Frozen hit classes: 1. KnowledgeHit — {hit_class: knowledge, source_ref, snapshot_ref, locator} 2. ArtifactHit — {hit_class: artifact, fp1, kind} where kind ∈ Workbench AD-3 roster or query-hit tags saved-view \\| analysis.published 3. ContributionHit — {hit_class: contribution, plugin_id, point, qualified_id, package_id, package_version} from live published_contributions(). Identity is that tuple. Never fp1, never a registry kind, never ArtifactHit.kind. Pins store (qualified_id, package_version, availability_revision), not a descriptor digest. Invoke revalidates the pin (AD-30). Missing/disabled/uninstalled plugin ⇒ typed unavailable or tombstone, never a silent resolve to another version, never a stale fp1. A hit is not a grant. 4. Hypothesis listing stays on qml.research / research_ref and is refused on the facade - Occupancy none. Daemon never import qmb. QMB never opens daemon sqlite. Ranked/semantic search stays GAP-0073. Extra Artifact query-hit tags beyond saved-view \\| analysis.published are refused unless this spine is amended. Discovery listings must distinguish published vs configured vs granted vs reachable vs healthy (AD-15); a ContributionHit is not a grant. Pack contributes entries are {point, local_id} and expand to ContributionHit at enable. view:* is a wire DTO only (AD-17) — not a plugin contribution point and not a ContributionHit until a named GAP-0081 ui_view increment. DTO owner is COMP-QMA-WIRE (additive CT-40 family, no new CT number). Query owner of live..."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-2. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2249]
    authority: rider
    component: COMP-QMA-WIRE
    tags: [workflows, ad-2]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-2"

  - id: DEC-0416
    title: "Workflows AD-3 — Capability Operation Interface is the shared contract"
    statement: "Every public operation publishes a versioned descriptor: stable id, owner COMP, input schema, output shape (value \\| artifact_ref \\| job_handle \\| event \\| stream), native cardinality (one \\| many in/out), empty_policy, configuration/defaults, declared operation dependencies, resource needs, documentation refs, validation class, units, version compatibility, effect class (none \\| read \\| append-evidence \\| mutate-config \\| place-run \\| external-egress), permission requests, execution placement, error/refusal shape, progress, and lifecycle verbs (start \\| query-state \\| cancel \\| await). Collection mapping is not on the descriptor — it lives on Graph Template edges (AD-5). Finite event ≠ persistent stream. Every public call carries an InvocationEnvelope (AD-24) binding contribution tuple, instance_id, config revision, grant snapshot, logical invocation/attempt ids, and effect-specific idempotency. Transport (in-process, CLI, wire, future RPC) is an implementation choice of the owner and is never a bypass of that envelope. Durable file handoffs cite schema, content fp1, source/run provenance and completeness — never a machine-local path as global id. Content fp1 applies to artifact bytes, not to contribution identity (AD-2 tuple). Manifests request; the host grants structured GrantRecords (AD-24). The only parameter authority is input_schema. Representative payloads in CONTRACTS.md are schema-complete or explicitly marked fragments; a fragment must not contradict this Rule."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-3. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2250]
    authority: rider
    component: COMP-QMA-CORE
    tags: [workflows, ad-3]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-3"

  - id: DEC-0417
    title: "Workflows AD-4 — Four workflow layers stay distinct"
    statement: "(1) Board layout is client-only. It MUST NOT be a field of product_session, Mission, Task Graph, Graph Template, or any sqlite row. Display alias only (Workbench AD-16). Editing the client layout writes nothing. (2) Graph Template — authored, versioned, stateless DAG; plugin-contributed. Compile identity is (qualified_id, version) from the plugin manifest at enable. Rebuild-on-load MUST NOT change bytes of an enabled (id, version); a byte change is a new version or a disable. Do not fingerprint templates onto the Artifact rail. (3) Task Graph — one Mission’s execution projection; persist edges: {from, to, mapping} and walk successors (connect/extend qma.daemon.taskgraph; today edges are dropped — that is a hole this AD binds closed). Nodes do not carry successor lists. (4) Ungoverned library call — import qmb / import qml on a controlled-room host; writes no Mission. A Stage 0 graph is none of these and is never compiled to a bot, Graph Template, or run_slice. A loop is node state, not a Skill; Loop stopping_condition is a typed stop (max-iterations / budget / predicate), not an opaque string. A Routine fires a compile; a schedule/webhook trigger is not the workflow definition. Selected-subgraph execution is MissionCompiler(template.qualified_id, template.version, node_ids) where node_ids is a non-empty induced DAG of that already-registered template version — not a live board scribble, not a board id. One compile → one Mission → one Task Graph whose graph_template_ref is the template qualified_id. After a semantic rewire, derived results are invalidated; reuse of prior ..."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-4. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2251]
    authority: rider
    component: COMP-QMA-DAEMON
    tags: [workflows, ad-4]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-4"

  - id: DEC-0418
    title: "Workflows AD-5 — Mapping is explicit; no silent Cartesian"
    statement: "Each port declares kind reference \\| data \\| event \\| control. Collection mapping is declared on the edge: one \\| zip \\| broadcast \\| keyed-join \\| cartesian. Cartesian requires an explicit flag. Empty collections skip or refuse per the operation’s declared empty-policy. Join algebra (unique keys, expected cardinality, watermark, late/missing/failed partitions, partial retry) is AD-26 and is not guessed from JSON shape. Conditional skip is a node kind, not dropped edges. Validate endpoints and cycles against DAG law (AD-6). Shared mini-app parameters are typed edges of this kind, not ambient globals."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-5. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2252]
    authority: rider
    component: COMP-QMA-CORE
    tags: [workflows, ad-5]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-5"

  - id: DEC-0419
    title: "Workflows AD-6 — Graph Template topology is a DAG"
    statement: "Registration refuses self-loops and any directed cycle (reuse the plugin-loader DFS already used for plugin requires). Pairwise reverse-edge checks are insufficient. Runtime Loops remain node state (iteration/budget/stop), not template cycles. This amends the inspected implementation hole; it does not revive graph-as-chat."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-6. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2253]
    authority: rider
    component: COMP-QMA-DAEMON
    tags: [workflows, ad-6]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-6"

  - id: DEC-0420
    title: "Workflows AD-7 — Reuse QMA as the procedure runtime; extend in place"
    statement: "Author in Graph Templates; instantiate via Mission Compiler (one template → one Mission); schedule via RoutineScheduler; place QMB work via place_procedure_step (run vs query occupancy unchanged). ExperimentSpec successors are lineage, not control-flow edges — CT-07 MUST NOT be walked as graph successors. Persist task_graph_state including edges: {from, to, mapping} in daemon sqlite (existing named projection, not a new store). Completing a predecessor and making successors ready is one sqlite transaction plus outbox (AD-26). Occupancy is not a separate table: it is the existing environment_lease + Workbench AD-8 door law, folded into task_graph_state. QMB does not write daemon occupancy; the daemon maps JobHandle ↔ lease using QMA AD-17 state vocabulary exactly (AD-26). Implement successor dispatch and daemon-evaluated node kinds (conditional, join, approval_gate) in qma.daemon.taskgraph. Skills remain knowledge; they never compile to Missions and never grant tools."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-7. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2254]
    authority: rider
    component: COMP-QMA-DAEMON
    tags: [workflows, ad-7]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-7"

  - id: DEC-0421
    title: "Workflows AD-8 — Product sessions are authority overlays, not QMA Session"
    statement: "product_session is a new journal-projected record kind, not a QMA Session and not a QMA Profile. Ids are psess:; QMA Session ids remain sess: and remain the execution container (execution_model + autonomy only). Cardinality is 1 product_session → many QMA Sessions. ProductSessionProfile is a closed enum {authoring, app-use}, immutable at create, and is not qma.core.ontology.Profile. scope_path does not gain a segment — product-session is a wire/header field beside it, never a permission key inside it. Durable fields: product_session_id, profile, principal, context_revision, app_instance_id (pointer to plugin-install instance row), granted_ops (array of grant_id referencing structured GrantRecords — AD-24; never a bare op-id string as the grant), selected_refs (typed {kind, id} only), optional private_notes JSON column (not a new store, not MemoryProvider, not Knowledge). Not durable: qma_session_id, tab attachment, UI layout. Closed selected_refs kinds: artifact fp1, research_ref, contribution (qualified_id, package_version), template (qualified_id, version), dataset/run/attempt refs, node-id sets citing a template. Forbidden in selected_refs: layout JSON, positions, widgets, json-render trees. Select/grant mutations are named wire commands that bump context_revision under compare-and-set on expected_revision (AD-29). Duplicate command_id returns the prior durable result. Reconnect resumes queries/events; it does not replay unacked intent. Tab change writes nothing. A dashboard/account filter is not a command target. Analysis access to an instrument is not execution perm..."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-8. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2255]
    authority: rider
    component: COMP-QMA-DAEMON
    tags: [workflows, ad-8]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-8"

  - id: DEC-0422
    title: "Workflows AD-9 — Copilot discovers granted descriptors; prose is not authorization"
    statement: "The copilot identity is one familiar product surface over QMA infrastructure. Tool availability = intersection of (published ContributionHits, host grants, product_session GrantRecords, health). Skills describe behavior; they do not grant. Skill authoring is separated from verification; the same model must not write the skill and certify it. Installation of a skill is not authoring. Hooks may veto/approve at existing QMA events; a model-authored hook cannot override a failed deterministic check or privilege gate. Cross-session retrieval is explicit, attributed, and cannot retarget actions. Explanations cite saved records/tool evidence, not fabricated recollection. Internal QMX context is structured schema, not screenshots as the default. MemoryProvider stays desk-scoped. Product-session private notes are the AD-8 JSON column (retention/export/deletion with the session row), not MemoryProvider, not Knowledge, not telemetry. RLM remains Analysis execution, not a product IDE."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-9. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2256]
    authority: rider
    component: COMP-QMA-CORE
    tags: [workflows, ad-9]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-9"

  - id: DEC-0423
    title: "Workflows AD-10 — Four cross-app composition modes"
    statement: "Supported modes, none compulsory: (1) consume another app’s saved artifact by fp1/content id; (2) invoke its exported operation through AD-3; (3) coordinate several apps via a Graph Template; (4) composite app that cites component contribution ids + artifact refs without merging code. A composite is an instance graph, not a new Library kind. Independent apps remain independently useful. Shared instances vs separately configured instances are explicit. Dependency diamonds pin versions per instance. Nested invocation does not union permissions or propagate the caller’s tools into the callee. Composite authority is the host-granted intersection, never a union of component requests. Bounded cycles of invocation require a recursion budget; template topology remains a DAG (AD-6). Partial failure does not silently substitute a different provider or account. A new venue protocol is a new VenueClientKind (refused in V1), not an extra account row."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-10. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2257]
    authority: rider
    component: COMP-QMA-CORE
    tags: [workflows, ad-10]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-10"

  - id: DEC-0424
    title: "Workflows AD-11 — Default Book/BMS is not a ceiling; dummy Book is forbidden"
    statement: "Dummy (mechanical): a CT-22/CT-27/CT-33, or an ATC PolicyPair, is dummy if minted solely to satisfy a required field, or if its policy is identity / no-op / unlimited / pass-through. Sentinel fps (NULL_BOOK, empty-object Book, mis_ref: null as a fake MIS) are dummy. Dummy is INVALID_INPUT at compile, register, validate, simulate, and seat. - Three config types, not optional fields on one. (1) ResolvedRunConfig — unchanged; book_fp1/bms_fp1/bot_fp1/fragments required; default path to governed evidence, node-paper, live, L17 seats. (2) AlternativeRunConfig — Book/BMS/bot keys absent, not null; complete second trading system defined by AD-23 (PolicyPair, command, admission, evidence, journey). When this composition is selected, QML authoring, QMB evaluation/optimization, optional MIS binding, QMN unattended host, and live adopt it — they do not stay secretly Book-shaped. Sequential paper-then-live and L17 human promote still apply. (3) UngovernedWorkConfig — those keys absent, not null; ungoverned qmb.run(), ordinary Python, data-ML, recipes, QMN sensing-only. Sensing-only is not a seat and is not class (2). - Alternative policy inside the default system remains a complete CT-22/CT-27 that still implements Book/BMS semantics (L36), evaluated by analysis.rerun of that fingerprint — not a wrapper around absent policy and not a projection. ATC is not that path. Compare Book vs ATC only on conserved measures both policies define; do not force ATC into the Book R vocabulary or relabel filtered trades as a rerun. MIS/SQS/KSA stay Book-door consumers unless an ATC PolicyPair names..."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-11. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2258]
    authority: rider
    component: COMP-QMF-RISK
    tags: [workflows, ad-11]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-11"

  - id: DEC-0425
    title: "Workflows AD-12 — Data recipes wrap qmf-data; provider ≠ venue"
    statement: "A recipe has two identities (AD-31). Definition identity is (recipe_def_id, recipe_def_version, recipe_def_hash) and is reviewable before any run. Output identity is the release fp1 (Workbench AD-13 derived-dataset law) plus CT-07 lineage to the definition and to CT-10/CT-12 inputs (COMP-QMB wrap of COMP-QMF-DATA). Display recipe_id is not computational identity. It is not a Library kind. CT-06 recipe kind is deferred until metadata-sharing is required. Recipes declare calendars, timezone, alignment, point-in-time/known-at policy, missing/late policy, units, adjustment, entitlements/licensing, environment/code pins, and output completeness. A new provider tomorrow must not rewrite yesterday’s pinned release. Provider name ≠ meaning; provider ≠ venue ≠ account ≠ instrument. Providers declare coverage, transport (file/API/SDK/CLI/webhook), historical vs poll vs stream, entitlements by credential reference, and quality/freshness. Preview ≠ export job ≠ live stream. Replay-to-live follows the stream protocol (AD-28). A stream subscription is not a trading permission. Source disagreement is preserved; production sensing feed is never silently swapped. Heterogeneous non-market facts do not widen CT-10 into untyped JSON: knowledge stays CT-44; session/product facts stay QMA; market/source facts stay CT-10. A new venue protocol is a new VenueClientKind, not an extra account."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-12. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2259]
    authority: rider
    component: COMP-QMB
    tags: [workflows, ad-12]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-12"

  - id: DEC-0426
    title: "Workflows AD-13 — Identities stay separate"
    statement: "Semantic identity is fp1 (artifacts), research_ref (hypotheses), (qualified_id, package_version) (contributions — not fp1), ExperimentSpec fp1 (coordinated continuity), composition_fp (node), instance_id (installed mini-app). Display names and Board layouts are UX. A saved runnable pins code, config, data release, model weights, environment and dependencies. Retry of an uncertain external action ≠ new experiment. Projection ≠ path-dependent rerun (Workbench AD-5). Three pack states stay distinct: installed (bytes present) ≠ enabled/activated (roster on) ≠ session-granted (AD-8 granted_ops). Published package ≠ activation on a trading account."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-13. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2260]
    authority: rider
    component: COMP-QMA-CORE
    tags: [workflows, ad-13]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-13"

  - id: DEC-0427
    title: "Workflows AD-14 — Sequential handover; software rollback cannot undo fills"
    statement: "Default replacement: develop → evaluate → non-real-money validate → explicit activation after stopped/flat-or-drained handover. The transition is the AD-25 fencing state machine: command-owner epoch, fencing token, typed positions/orders snapshot, residual disposition, predecessor acknowledgement, timeout/escalation, immutable completion evidence. Outstanding positions, UNKNOWN commands, shared-account concurrency are separate refusal/drain cases, not a boolean residual_positions string. A stale predecessor restart cannot recover command authority from local state. Two MIS/model versions may shadow or bind distinct consumers; one writer per role. Owner means software/control scope, not user money. Software rollback never reverses fills. GAP-0058 single-machine placement stays its own increment."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-14. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2261]
    authority: rider
    component: COMP-QMN
    tags: [workflows, ad-14]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-14"

  - id: DEC-0428
    title: "Workflows AD-15 — Compute placement is preflight, not a toggle sticker"
    statement: "States are distinct: available / configured / authorized / reachable / healthy. Training ≠ inference ≠ trading deployment. Expensive experiments must not starve protective trading actions. No cloud/Colab/provider is assumed; bind only through existing QMA ExecutionEnvironment / ComputeProvider ports. Cancellation, unknown outcome and checkpoint/resume are job-handle law. Browser/computer-use remain provisionable rungs (GAP-0070/0078) fail-closed until registered."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-15. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2262]
    authority: rider
    component: COMP-QMA-DAEMON
    tags: [workflows, ad-15]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-15"

  - id: DEC-0429
    title: "Workflows AD-16 — Persistence owners stay split; new product records are not qmf-core"
    statement: "Evidence: qmf-data rooms + CT-13 journals + registry sqlite + QMB JSONL ledger (including ATC rows tagged composition_class: alternative). Coordinated experiment identity: QMA Experiment sqlite. Hypotheses: QML research_root blobs. v1 daemon additions (complete list): (1) product_session journal projection (AD-8); (2) persist existing task_graph_state including edges and the AD-26 outbox; (3) mini-app instance rows in the existing plugin-install projection, keyed by instance_id ≠ plugin_id; (4) GrantRecord rows beside product_session (same sqlite, not a new store class). No other new sqlite. Change-request = staging kind change_request (AD-8). Recipe definition identity is AD-31; output identity remains release fp1 plus CT-07; CT-06 recipe kind deferred. Graph Templates rebuild from plugins but enabled (qualified_id, version) bytes are immutable. MemoryProvider remains optional per desk (GAP-0072). Logs are not evidence. Backup/restore stay application-owned using QMF primitives plus an application checkpoint manifest (AD-27) that records per-owner fences and restore order. Orphans, corruption, disk exhaustion and cross-store reconstruction are owner-specific: never invent a second evidence database; never silently merge divergent stores."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-16. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2263]
    authority: rider
    component: COMP-QMA-DAEMON
    tags: [workflows, ad-16]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-16"

  - id: DEC-0430
    title: "Workflows AD-17 — UI host contracts now; chrome is GAP-0081"
    statement: "The host is a client of qma-wire, QMB API/CLI, QMN three doors. Contribution descriptors (navigation, commands, rich views including editors, parameter forms, context providers, events, reconnect) are wire-owned DTOs defined in CONTRACTS §14 — not a v1 ui_view plugin point until a named GAP-0081 increment. The catalogue is not cards-only. JSON Render and MCP Apps are presentation adapters. They are not identity, not persistence, not a runtime, and not authority. The only parameter authority is AD-3 input_schema. The only invoke authority is AD-9 ∩ GrantRecord. A json-render catalog entry MUST name an existing AD-3 op_id and MUST NOT add/remove fields. Absence of a catalog entry is native/CLI using the same schema. MCP App HTML MUST NOT grant tools; the host intercepts every tool call and refuses if outside the session’s GrantRecords. Pack view:* is a wire DTO, not a plugin point, not a json-render runtime id, not an fp1. Native QMX panes remain first. UI mount/dispose must not start/kill durable backend work. Stale snapshot/cursor refuses invoke. Headless packs appear as reusable AD-3 steps without navigation. QMB remains the only operator CLI; QMA and QMN ship none. Do not pin @json-render/* in this sitting."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-17. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2264]
    authority: rider
    component: COMP-QMA-WIRE
    tags: [workflows, ad-17]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-17"

  - id: DEC-0431
    title: "Workflows AD-18 — Packages export without private lineage or secrets"
    statement: "A pack is versioned: manifest, contribution list, requested capabilities, compatibility range, migrations. Lifecycle is AD-30 (downloaded / installed / validated / enabled / disabled / uninstalled) with a transition journal, atomic roster publication, and QMA AD-21 down or forward_only migrations. Install / configure / enable / disable / validate / pin / rollback / dependency-removal / export / import are host operations. First-party trust in v1; custom packs are explicit operator enable. Missing dependency is a hard error at enable, not warning-and-continue (do not copy Hermes advisory-dep behaviour). Partial install rolls back to the last usable roster. Side-by-side versions allowed; running work stays pinned to the instance it started. exports_secrets: false is a request; an independent export scanner is the oracle and replaces secret values with typed refs."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-18. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2265]
    authority: rider
    component: COMP-QMA-DAEMON
    tags: [workflows, ad-18]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-18"

  - id: DEC-0432
    title: "Workflows AD-19 — Mutation testing is a test-strength principle"
    statement: "Behaviour oracles (BDD/journeys) come first. Then contract/integration, state-machine, fault-injection, and optional mutation testing of existing Python tests. mutmut (current docs 2026-09-18) requires os.fork — Windows execution is WSL only. Run only on disposable copies. Classify surviving/equivalent/invalid/timeout. Caliper-style skill evaluation is a later QMA adapter question, not a CLI assumption."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-19. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2266]
    authority: rider
    component: COMP-QMA-CORE
    tags: [workflows, ad-19]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-19"

  - id: DEC-0433
    title: "Workflows AD-20 — Defaults and templates ship with a custom path"
    statement: "Ship enough defaults (data preview, governed backtest door, library search, authoring vs app-use shells) that real work is possible. Custom granularity is operator-chosen: wrap notebooks/scripts as operations, or expose selected stages. Graph editing is not the only programming route (L9)."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-20. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2267]
    authority: rider
    component: COMP-QMA-CORE
    tags: [workflows, ad-20]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-20"

  - id: DEC-0434
    title: "Workflows AD-21 — Headless parity of operations"
    statement: "Deep behaviour of an AD-3 operation is identical across that operation’s supported doors. Supported-door sets are per op_id and recorded in CONTRACTS §15. QMB remains the only operator CLI. QMA and QMN ship no operator CLI; their operations use library and qma-wire adapters, and may be invoked through QMB-owned orchestration when the owner is QMB. Unsupported door → typed unsupported_door, never a newly minted qma/qmn CLI. A useful log/progress panel is not a general shell."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-21. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2268]
    authority: rider
    component: COMP-QMA-WIRE
    tags: [workflows, ad-21]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-21"

  - id: DEC-0435
    title: "Workflows AD-22 — Portfolio Manager is a label, not an identity rewrite"
    statement: "Trading-floor Role display becomes Portfolio Manager. Keep desk_slug=pm and pm-coordination until a GAP-0083 migration sitting. Preserve BMAD Product Manager. Combining two bots’ equity streams stays deferred (F07 / Workbench AD-5)."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-22. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2269]
    authority: rider
    component: COMP-QMA-CORE
    tags: [workflows, ad-22]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-22"

  - id: DEC-0436
    title: "Workflows AD-23 — Alternative Trading Composition is a complete second system"
    statement: "Book/BMS is one specific portfolio accounting + risk + position-sizing implementation — the default, not the ceiling. An Alternative Trading Composition (ATC) is AlternativeRunConfig whose Book/BMS/bot keys are absent, not null. It MUST carry a PolicyPair of AccountingPolicy + RiskPolicy, both complete (the dummy test in AD-11 applies). AccountingPolicy declares cash identity, position identity, fill application, valuation marks, currency, and residual meaning. RiskPolicy declares limits, halt, sizing, UNKNOWN handling, and the override principal. Command binds venue, account, role, instrument, adapter capability, credential ref, and AD-25 owner epoch — a dashboard filter is not a target. Admission checks PolicyPair completeness, grants, health, sequential paper-then-live readiness, and L17 human promote before any live VenueClientKind. That promote is operating discipline already in the transcript (“do not replace a Book and trade tomorrow”), not a later architecture question. Adopt: QML authoring, QMB backtest/optimize, optional MIS/intelligence binding, QMN unattended host, and live bind to the selected composition version. A Book-shaped consumer must not silently remain when the composition is ATC. Evidence is QMB JSONL tagged composition_class: alternative plus CT-07 lineage to the PolicyPair hash; it is not a Book journal and not qmf-core. Compare with the default path only on conserved measures both policies define. End-to-end: author PolicyPair (optionally as a mini-app/workflow) → validate → simulate against pinned CT-10/replay → paper on node → fenced sequentia..."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-23. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2270]
    authority: rider
    component: COMP-QMF-RISK
    tags: [workflows, ad-23]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-23"

  - id: DEC-0437
    title: "Workflows AD-24 — Invocation envelope and structured grants"
    statement: "Every public call carries InvocationEnvelope: logical_invocation_id, monotonic attempt_id, op_id/op_version, contribution (qualified_id, package_version), instance_id, config_revision, optional caller/callee psess: refs, grant_id snapshot, effect_class, idempotency_key, reconcile_policy, input_hash. Ambiguous instance/config resolution refuses. Idempotency is effect-specific: none/read may retry; append-evidence dedupes on the key; mutate-config is CAS on config_revision; place-run treats logical_invocation_id as the run identity; external-egress MUST obtain a receipt or become unknown and MUST NOT blind-retry. reconcile_policy is query-then-decide \\| unknown-manual \\| never-retry. GrantRecord is immutable after mint: grant_id, principal, audience, contribution tuple, instance_id, config_revision, op_id/op_version, effect_class, parameter ceiling, account_scope (null unless granted), expires_at, optional revoked_at. product_session.granted_ops stores grant_ids. Upgrade, re-resolution, or a new package version cannot widen or retarget an existing grant; that requires an explicit re-grant that bumps context_revision."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-24. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2271]
    authority: rider
    component: COMP-QMA-WIRE
    tags: [workflows, ad-24]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-24"

  - id: DEC-0438
    title: "Workflows AD-25 — Command-owner fencing for sequential deploy"
    statement: "One command owner per (account, venue, role). Transition states, in order: idle → drain-requested → draining → (residuals-attributed \\| unknown-blocked) → predecessor-acked → fenced-activate → active → retired. Required records: command_owner_epoch, fencing_token (QMN issues venue tokens; QMB issues internal ATC-simulate tokens), account, venue kind, composition_fp, typed positions_snapshot and orders_snapshot, residual_disposition (flatten \\| transfer-to-successor \\| hold-manual), predecessor ack, timeout/escalation, immutable completion evidence. unknown-blocked is terminal for this attempt until operator reconcile; it is never an automatic retry. A process restart presenting a stale epoch or token is refused. Software rollback after a new-owner fill cannot unfill. This machine applies to the default Book path and to ATC (simulate tokens and, after paper-then-live + L17, venue tokens)."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-25. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2272]
    authority: rider
    component: COMP-QMN
    tags: [workflows, ad-25]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-25"

  - id: DEC-0439
    title: "Workflows AD-26 — Durable workflow: outbox, JobHandle parent vocab, join algebra"
    statement: "Completing predecessor A and making successor B ready is one daemon-sqlite transaction: (1) persist A terminal, (2) persist successor eligibility at a revision, (3) write an outbox row per newly ready successor. The dispatcher reads the outbox, invokes B with AD-24 logical_invocation_id, and acks the outbox. Crash recovery replays unacked outbox rows; dispatch is idempotent on the envelope. No second scheduler. JobHandle reuses QMA AD-17 exactly: queued \\| running \\| done \\| failed \\| cancelled \\| aborted \\| unknown. Terminal = done/failed/cancelled/aborted. unknown is non-terminal and holds environment_lease. cancelled is explicit cancel; aborted is known environmental non-completion; timeout/lost supervisor is unknown, never failed or aborted. awaiting_approval is a Mission/Task gate, not a JobHandle state. Each handle records logical_run_id, attempt_id, artifact inventory with completeness complete \\| partial \\| missing \\| expired. First durable terminal wins a cancel/complete race; later commands are no-ops recorded against that terminal. Join algebra per AD-5 mapping: stable partition_id; expected cardinality; keyed-join unique keys (duplicate policy declared: refuse or first-wins); watermark all-expected \\| timeout \\| failed-aggregation; late arrival after watermark is late, not silently merged; partial retry re-invokes only failed partition_ids and reuses successful artifacts via their logical_invocation_id. Output order is sorted by partition_id unless the edge declares otherwise."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-26. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2273]
    authority: rider
    component: COMP-QMA-DAEMON
    tags: [workflows, ad-26]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-26"

  - id: DEC-0440
    title: "Workflows AD-27 — Application checkpoint manifest, not a second evidence database"
    statement: "COMP-QMA-DAEMON owns a CheckpointManifest (journal-projected, not a new store class) listing per-owner {owner, store, fence, content_hash} and a restore order: QMF rooms → QMB JSONL (including ATC) → QML blobs → artifact bytes → QMA sqlite projections. Each owner restores its own store using existing primitives (QMA AD-27 five-step for daemon projections; QMF backup for rooms). After restore, verify cross-store references. Missing/corrupt refs become orphan and are quarantined; they are never silently merged. External-effect reconcile hooks run after local restore; absence of acknowledgement is unknown, not proof of non-execution. UI disconnect, coordinator loss, and worker loss remain distinct (AD-15)."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-27. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2274]
    authority: rider
    component: COMP-QMA-DAEMON
    tags: [workflows, ad-27]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-27"

  - id: DEC-0441
    title: "Workflows AD-28 — Stream protocol: epoch, cutover, leases"
    statement: "A subscription carries sub_id, channel, source_id (provider), optional venue_id (never the same field), epoch, monotonic sequence, event_time, receive_time, phase replay \\| cutover \\| live, cutover_watermark, cursor, bounded buffer, backpressure_policy (block \\| disconnect \\| spill-with-evidence), gap/duplicate/late events, heartbeat, consumer_id, and a reference count. Cutover is atomic at the watermark: events at-or-before are replay; after are live. Overload cannot silently drop market-driving events; the declared policy and loss evidence must be visible. Cancelling one consumer decrements the refcount; the shared upstream stays until refcount is 0. Replay provenance cannot be interpreted as a live command absent an explicit, granted policy. A stream subscription is not trading permission."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-28. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2275]
    authority: rider
    component: COMP-QMB
    tags: [workflows, ad-28]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-28"

  - id: DEC-0442
    title: "Workflows AD-29 — Product-session CAS, reconnect, and change-request completeness"
    statement: "Mutations are mutate(product_session_id, expected_revision, command_id, payload) → ok(new_revision, result) \\| conflict(current_revision) \\| duplicate(prior_result). Queries do not bump revision. Reconnect is a query from the client cursor; it never re-issues an unacked command without the original command_id. Change-request payload MUST include source psess:, source instance_id/config_revision, target refs, base hashes of those refs, context_revision at mint, request_hash, typed patch, validation result, conflict \\| rebase-required \\| valid, and — after authoring apply — apply evidence. App-use mints; authoring + operator principal applies; promote remains L17 and is not this path."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-29. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2276]
    authority: rider
    component: COMP-QMA-DAEMON
    tags: [workflows, ad-29]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-29"

  - id: DEC-0443
    title: "Workflows AD-30 — Package lifecycle, atomic roster, pin/invoke, export oracle"
    statement: "Pack states: downloaded → installed → validated → enabled ⇄ disabled → uninstalled. Each transition is journaled. Roster publication is atomic (stage, fsync, swap). Failed validation/migration restores the last usable roster. Migrations follow QMA AD-21 (down or forward_only with operator confirmation). Uninstall names dependants; in-flight pinned runs keep the bytes they started with. Session-granted is AD-8, not a pack state. Pin of a ContributionHit stores (qualified_id, package_version, availability_revision). Invoke revalidates; disabled/uninstalled → unavailable or tombstone, never another version. Export scanner is independent of the manifest: it must prove absence of secret values, private paths, and transcripts, and must rewrite remaining secrets to typed refs. Manifest exports_secrets: false without a passing scan is not evidence."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-30. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2277]
    authority: rider
    component: COMP-QMA-DAEMON
    tags: [workflows, ad-30]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-30"

  - id: DEC-0444
    title: "Workflows AD-31 — Recipe-definition identity and complete recipe schema"
    statement: "RecipeDefinition identity is (recipe_def_id, recipe_def_version, recipe_def_hash). It is reviewable and pinnable before execution. A run produces a new output release fp1 (Workbench AD-13) with CT-07 lineage to the definition and to each input revision. Two runs of one definition are two releases, not two recipes. Display rename does not change recipe_def_hash. The definition schema includes inputs (provider, coverage, schema/roles, units, timezone/calendar, freshness, provenance, entitlement, licensing, revision), transforms (alignment, known-at/no-lookahead, missing/late policy, adjustment), split policy, environment/code pins, and output completeness. Preview ≠ export ≠ stream. Non-trading outputs need no CT-33/Book/QMN wrap (AD-11 class 3)."
    status: ratified
    rationale: "Absorbed from architecture-QMX-2026-09-18 AD-31. Operator rider 2026-09-19; OD-01 closed; package folded as ratified (AD-24..AD-31 with cheap-veto A1-A6)."
    sources: [EXT-2278]
    authority: rider
    component: COMP-QMB
    tags: [workflows, ad-31]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-31"


  - id: DEC-0445
    title: "Workflows construction-kit spine adopted in full (reuse existing applications; no sixth package)"
    statement: "The 2026-09-18/19 QMX Workflows construction-kit spine (architecture-QMX-2026-09-18, candidate qmx-workflows-arch-2026-09-19-c) is adopted in full as DEC-0414 through DEC-0444. Paradigm is composition over hexagonal libraries and existing application-layer products: capability / extension / workflow / mini-app / widget; product_session psess: distinct from QMA Session sess:; ContributionHit never fp1; Alternative Trading Composition / PolicyPair; RecipeDefinition distinct from release fp1. Preflight reuse with no new COMP and no new CT (DEC-0446). Cheap-veto A1-A6 ride DEC-0447. L36 named amendment is DEC-0448. DEC-0389 two-class freeze is named-amended by DEC-0449 without superseding the rest of the mill package. Wiring honesty at 270e992 is DEC-0450. Dead list honors are DEC-0451. Parents QMF / QMB / QML / NODE / QMA / CONNECT / Workbench / mill bind read-only. Local AD-1..AD-31 do not renumber parents. ADR-0024 and SCN-0018..0022 are docs authority only. Implementation authorization remains factory-pipeline-only."
    status: ratified
    rationale: "Operator launched Documentation Factory after OD-01 closed; rider 2026-09-19 is authoritative. Package is ratified (not provisional); AD-24..AD-31 carry cheap-veto."
    sources: [EXT-2279, EXT-2246, EXT-2247, EXT-2280]
    authority: rider
    component: COMP-QMA-CORE
    tags: [workflows, spine-adoption, umbrella, reuse]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md"

  - id: DEC-0446
    title: "Workflows preflight — reuse existing applications; no new COMP; no new CT"
    statement: "Preflight verdict: reuse existing applications. new COMP: none. new CT: none. No new depends_on edge and no existing component's authority shrinks. Work owners: ContributionHit DTO + pin/tombstone = COMP-QMA-WIRE + COMP-QMA-DAEMON published_contributions() (amend DEC-0389 / extend CT-40); Operation descriptor + InvocationEnvelope + GrantRecord = COMP-QMA-CORE + COMP-QMA-WIRE; product_session CAS + authoring/app-use = COMP-QMA-DAEMON + COMP-QMA-WIRE (journal projection, not a new store class); DAG validator = COMP-QMA-DAEMON / COMP-QMA-CORE (closes hole under DEC-0312); Task Graph edges + outbox + JobHandle parent vocab = COMP-QMA-DAEMON (connect named task_graph_state); ATC PolicyPair / AlternativeRunConfig = COMP-QMB (eval/journal) + COMP-QML (author) + COMP-QMN (seat after paper+L17) + COMP-QMF-RISK (default shapes only); Data recipes = COMP-QMB wrap of COMP-QMF-DATA; Fencing sequential deploy = COMP-QMN (+ QMB simulate tokens); UI contribution DTOs = COMP-QMA-WIRE (chrome GAP-0081); Pack lifecycle / export scanner = COMP-QMA-DAEMON (connect QMA AD-21). Candidates refused: COMP-WF / COMP-LIB / sixth COMP; new CT-*; marketplace (DEC-0361); solver (DEC-0362); HMR (DEC-0366); QMA import qmb; dummy Book; sensing-as-ATC; hit_class strats; Stage 0 graph as executor (DEC-0411)."
    status: ratified
    rationale: "Architecture preflight recorded for ADR-0024. Matches workbench/QMA reuse pattern."
    sources: [EXT-2280, EXT-2279]
    authority: rider
    component: COMP-QMA-CORE
    tags: [workflows, preflight, reuse, no-new-comp, no-new-ct]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md"

  - id: DEC-0447
    title: "Workflows cheap-veto register A1-A6"
    statement: "Cheap-veto assumptions for AD-24..AD-31 machinery, each individually overturnable without unwinding another call: (A1) PolicyPair field catalogue (AccountingPolicy / RiskPolicy closed fields in CONTRACTS §11) — proceed; ATC class is operator-direct; field list is sitting machinery. (A2) AD-25 fencing state enum (idle…retired) — proceed. (A3) InvocationEnvelope full field set + effect-specific idempotency matrix — proceed. (A4) ContributionHit pin tuple (qualified_id, package_version, availability_revision) — proceed. (A5) Recipe definition identity (recipe_def_id, version, hash) — proceed; CT-06 kind still deferred. (A6) CheckpointManifest restore order — proceed. Not vetoable here: no sixth COMP; dummy Book INVALID_INPUT; sessions≠tabs; app-use cannot edit; QMN sole venue importer; L17; sequential paper-then-live; BDD=spec; mutmut optional. Focused Codex recheck of AD-23..AD-31 was skipped by operator process preference (GAP-0092); do not claim Codex approved those ADs."
    status: ratified
    rationale: "Workbench cheap-veto pattern for sitting machinery after operator-direct ATC class. Rider records the Codex skip."
    sources: [EXT-2281, EXT-2246]
    authority: rider
    component: COMP-QMA-CORE
    tags: [workflows, cheap-veto, assumptions]
    date: 2026-09-19
    spine_ref: "SRC-22"

  - id: DEC-0448
    title: "L36 named amendment — Book/BMS are default implementations, not the ceiling"
    statement: "L36 stays bot → Book → BMS → operator as the default authority chain. Book and BMS are the default implementations of accounting and risk/sizing roles, not the only implementations the framework may host. A complete alternative PolicyPair may occupy those roles without dummy records. Human L17 promote and sequential paper-then-live remain. QMN remains the only venue importer. Dummy Book/BMS (identity / no-op / unlimited / pass-through / sentinel fps) remains INVALID_INPUT."
    status: ratified
    rationale: "Operator-direct constitution work for this pass. Named amendment; do not rewrite parent Decision sections silently."
    sources: [EXT-2282, EXT-2246, EXT-2247]
    authority: rider
    component: COMP-QMF-RISK
    tags: [law, workflows, l36, book-bms, atc]
    date: 2026-09-19
    spine_ref: "SRC-22"

  - id: DEC-0449
    title: "Named amendment of DEC-0389 two-class freeze — ContributionHit added; rest of DEC-0389 stands"
    statement: "DEC-0389's two-class Library discovery freeze is named-amended by Workflows AD-2 (DEC-0415): product discovery concatenates KnowledgeHit, ArtifactHit, and ContributionHit. ContributionHit identity is the live published_contributions() tuple and is never fp1 and never a registry kind. Pins store (qualified_id, package_version, availability_revision). The rest of DEC-0389 stands unchanged: occupancy none on the discovery path; no hit_class strats; no qml_candidate; hypotheses remain off the Library facade and are found through the QML research surface; daemon never import qmb; QMB never opens daemon sqlite; ranked/semantic search stays GAP-0073. Do not set DEC-0389 superseded_by. Leave DEC-0389 as provisional mill-package text; this amendment is the workflows-side correction of its two-class freeze only."
    status: ratified
    rationale: "Spine AD-2 explicitly names this as the amendment of mill/wire DEC-0389's two-class freeze. Whole-supersession would erase standing mill constraints the operator kept."
    sources: [EXT-2283, EXT-2249]
    authority: rider
    component: COMP-QMA-WIRE
    tags: [workflows, dec-0389, contribution-hit, amendment]
    date: 2026-09-19
    spine_ref: "SRC-21:ARCHITECTURE-SPINE.md#ad-2"

  - id: DEC-0450
    title: "Wiring honesty @ 270e992 — inherit DEC-0286; ContributionHit and product_session not on wire"
    statement: "Inherit DEC-0286: class/test existence is not end-to-end demonstration. On integration@270e992995c2378ca63cf6343254ef8140a8c97e this session reconfirmed federated discovery is still KnowledgeHit|ArtifactHit only; ContributionHit is proposed and not on the wire; product_session is absent; TaskGraph classes exist but the store is in-memory with edges dropped and outbox absent; Operation descriptor / InvocationEnvelope / GrantRecord are absent; AlternativeRunConfig / PolicyPair are not in code; QML→QMB→QMN cross-component integration is unsupported (P2-INT-001). Do not describe proposed connects as implemented. Do not use 8510c03 for absence claims. Implementation authorization still arrives only through the factory pipeline."
    status: ratified
    rationale: "Operator rider evidence-honesty pin plus inspect SHA for this fold."
    sources: [EXT-2284]
    authority: rider
    component: COMP-QMA-WIRE
    tags: [workflows, wiring, source-inspected, 270e992]
    date: 2026-09-19
    spine_ref: "SRC-22"

  - id: DEC-0451
    title: "Dead-list honors — marketplace, solver, HMR, sixth COMP, mill deaths stay dead"
    statement: "This increment honors existing deaths and does not revive them: DEC-0084 / DEC-0085 / DEC-0086 stay dead; DEC-0361 marketplace, DEC-0362 solver, and DEC-0366 HMR stay dead; DEC-0408..DEC-0413 mill deaths stay dead. No hit_class strats. No qml_candidate hit class. Hypotheses stay off the Library facade. No COMP-WF / COMP-LIB / sixth application. No Stage 0 graph as workflow executor. No dummy Book. Sensing is not an Alternative Trading Composition."
    status: ratified
    rationale: "Rider dead-list section. This entry is ratified (honors deaths); it is not itself a dead entry."
    sources: [EXT-2285, EXT-2246]
    authority: rider
    component: COMP-QMA-CORE
    tags: [workflows, dead-list, honors]
    date: 2026-09-19
    spine_ref: "SRC-22"
"""

GAPS = r"""
  - id: GAP-0092
    question: "Focused Codex recheck of AD-23..AD-31 was skipped. When, if ever, is independent recheck required?"
    needed_by: [COMP-QMA-CORE, COMP-QMF-RISK, COMP-QMN]
    blocking: false
    recommendation: "Documentation-factory fold proceeds now. Do not claim Codex approved AD-23..AD-31. Revisit only if the operator asks for an independent recheck before implementation of those machines."
    status: deferred
    answer: null
    note: "Workflows increment 2026-09-19 (DEC-0447). Operator process preference skipped focused Codex recheck. 85 Codex scenario IDs remain specification oracles, not executed proof."
    date: 2026-09-19
  - id: GAP-0093
    question: "When is product_session runtime (psess: journal projection, CAS mutations, authoring/app-use profiles) delivered on the daemon/wire?"
    needed_by: [COMP-QMA-DAEMON, COMP-QMA-WIRE]
    blocking: false
    recommendation: "Feeds FEAT-0053. Absent at 270e992 (DEC-0450). Implement after Operation/GrantRecord surface (FEAT-0052)."
    status: deferred
    answer: null
    note: "Workflows AD-8/AD-29. product_session is a journal-projected record kind, not a new store class."
    date: 2026-09-19
  - id: GAP-0094
    question: "When do ContributionHit and pin/tombstone land on the federated discovery wire (still KnowledgeHit|ArtifactHit at 270e992)?"
    needed_by: [COMP-QMA-WIRE, COMP-QMA-DAEMON]
    blocking: false
    recommendation: "Feeds FEAT-0051. First epic after docs. Amend DEC-0389 two-class freeze via DEC-0449 without superseding the mill package."
    status: deferred
    answer: null
    note: "Workflows AD-2 / DEC-0415 / DEC-0449. Identity is the published_contributions() tuple; never fp1."
    date: 2026-09-19
  - id: GAP-0095
    question: "When are Task Graph edges persisted and the durable outbox added (in-memory store today drops edges)?"
    needed_by: [COMP-QMA-DAEMON]
    blocking: false
    recommendation: "Feeds FEAT-0055 after DAG validator FEAT-0054. Connect named task_graph_state; JobHandle stays QMA AD-17 parent vocab."
    status: deferred
    answer: null
    note: "Workflows AD-7/AD-26. Completing predecessor and making successors ready is one sqlite transaction plus outbox."
    date: 2026-09-19
  - id: GAP-0096
    question: "When do Operation descriptor, InvocationEnvelope, and GrantRecord land on COMP-QMA-CORE / COMP-QMA-WIRE?"
    needed_by: [COMP-QMA-CORE, COMP-QMA-WIRE]
    blocking: false
    recommendation: "Feeds FEAT-0052. Absent at 270e992 (DEC-0450). Field catalogue is cheap-veto A3."
    status: deferred
    answer: null
    note: "Workflows AD-3/AD-24. Manifests request; host grants structured GrantRecords."
    date: 2026-09-19
  - id: GAP-0097
    question: "When do AlternativeRunConfig and PolicyPair appear in code (ATC path)?"
    needed_by: [COMP-QMF-RISK, COMP-QMB, COMP-QML, COMP-QMN]
    blocking: false
    recommendation: "Feeds FEAT-0056 thin fixtures. ATC class is operator-direct (OD-01); PolicyPair field catalogue is cheap-veto A1. Dummy Book remains INVALID_INPUT."
    status: deferred
    answer: null
    note: "Workflows AD-11/AD-23. Book/BMS keys absent-not-null on AlternativeRunConfig."
    date: 2026-09-19
  - id: GAP-0098
    question: "When is QML→QMB→QMN cross-component integration supported end-to-end (P2-INT-001)?"
    needed_by: [COMP-QML, COMP-QMB, COMP-QMN]
    blocking: false
    recommendation: "Package tests are not e2e (DEC-0286 / DEC-0450). Keep as deferred integration hole; do not claim adoption from unit presence."
    status: deferred
    answer: null
    note: "Workflows wiring honesty. Unsupported at 270e992."
    date: 2026-09-19
  - id: GAP-0099
    question: "What is the QMN supervision-mode taxonomy (unattended VPS vs local-attended vs agent-watched)?"
    needed_by: [COMP-QMN]
    blocking: false
    recommendation: "Operator-seeded; sitting did not decide. Do not invent a taxonomy in docs. Revisit when the operator rules supervision modes."
    status: deferred
    answer: null
    note: "Workflows deferred. Distinct from GAP-0058 single-machine placement design."
    date: 2026-09-19
  - id: GAP-0100
    question: "Is a cutover readiness dashboard (latency/deployed) required beside the AD-25 fencing machine?"
    needed_by: [COMP-QMN, COMP-QMA-WIRE]
    blocking: false
    recommendation: "Operator-seeded; sitting answered with fencing only. Do not invent chrome. GAP-0081 chrome stays deferred."
    status: deferred
    answer: null
    note: "Workflows deferred. AD-25 fencing is the transition machine; readiness chrome is not designed here."
    date: 2026-09-19
"""

FEATS = r"""
  - id: FEAT-0051
    name: "ContributionHit concatenate + pin/tombstone"
    scope: >-
      In: extend federated discovery with ContributionHit from live
      published_contributions() (DEC-0415, DEC-0449); pin tuple
      (qualified_id, package_version, availability_revision); invoke
      revalidates pin; missing/disabled/uninstalled yields typed
      unavailable or tombstone, never silent resolve to another version
      (DEC-0415, DEC-0443); DTO owner COMP-QMA-WIRE additive CT-40
      family; no new CT number; no new COMP (DEC-0414, DEC-0446);
      hypotheses stay off the facade; occupancy none. Out: fp1 for
      contributions; registry kind for contributions; hit_class strats;
      qml_candidate; chrome (GAP-0081). Done means UI/agent search can
      cite ContributionHit with honest pin/tombstone behaviour;
      implementation authorization still arrives only through the
      factory pipeline.
    decisions: [DEC-0415, DEC-0449, DEC-0414, DEC-0446]
    components: [COMP-QMA-WIRE, COMP-QMA-DAEMON]
    blocked_by:
      - id: FEAT-0050
        reason: "ContributionHit extends the federated Knowledge+Artifact discovery DTO FEAT-0050 lands; do not fork a second facade (DEC-0415, DEC-0449)"
      - id: FEAT-0041
        reason: "the hit DTO rides the additive CT-40 wire family FEAT-0041 lands (DEC-0415, DEC-0446)"
      - id: FEAT-0046
        reason: "pack contributes expand to ContributionHit at enable; desk packs FEAT-0046 lands are the contribution publishers (DEC-0415, DEC-0443)"
    size: multi-pass
    status: planned
    notes: "First epic after this documentation-factory pass. Do not launch from the YAML mint alone. Implementation authorization factory-pipeline-only."

  - id: FEAT-0052
    name: "Operation descriptor + InvocationEnvelope + GrantRecord"
    scope: >-
      In: every public operation publishes a versioned descriptor
      (DEC-0416); every public call carries InvocationEnvelope with
      effect-specific idempotency (DEC-0437); host grants structured
      GrantRecords (immutable after mint); manifests request, host
      grants; transport never bypasses the envelope; no new COMP or CT
      (DEC-0446). Out: untyped execute(anything); widening grants on
      upgrade; new CT number. Done means descriptors and envelopes are
      specified on wire/core; implementation authorization still arrives
      only through the factory pipeline.
    decisions: [DEC-0416, DEC-0437, DEC-0446]
    components: [COMP-QMA-CORE, COMP-QMA-WIRE]
    blocked_by:
      - id: FEAT-0041
        reason: "InvocationEnvelope and GrantRecord ride COMP-QMA-WIRE / CT-40 family FEAT-0041 lands (DEC-0416, DEC-0437)"
      - id: FEAT-0040
        reason: "operation descriptors and permission requests extend COMP-QMA-CORE ontology/ports FEAT-0040 lands (DEC-0416)"
    size: multi-pass
    status: planned
    notes: "Cheap-veto A3 covers full field catalogue. Implementation authorization factory-pipeline-only."

  - id: FEAT-0053
    name: "product_session + CAS + grant intersection"
    scope: >-
      In: product_session journal projection with psess: ids distinct
      from QMA Session sess: (DEC-0421); ProductSessionProfile
      authoring|app-use immutable at create; granted_ops store grant_ids
      not bare op strings; select/grant mutations bump context_revision
      under CAS (DEC-0442); copilot tool availability is intersection of
      published ContributionHits, host grants, product_session
      GrantRecords, and health (DEC-0422); app-use may mint change-request
      only — cannot edit package source or elevate grants; tab change
      writes nothing. Out: tab-owned context; app-use applying
      implementation edits; new store class. Done means psess: CAS and
      grant intersection are specified; implementation authorization
      still arrives only through the factory pipeline.
    decisions: [DEC-0421, DEC-0442, DEC-0422, DEC-0446]
    components: [COMP-QMA-DAEMON, COMP-QMA-WIRE, COMP-QMA-CORE]
    blocked_by:
      - id: FEAT-0052
        reason: "product_session.granted_ops references GrantRecords FEAT-0052 lands; CAS commands assume InvocationEnvelope identity (DEC-0421, DEC-0437, DEC-0442)"
      - id: FEAT-0042
        reason: "product_session is a journal-projected daemon record beside existing QMA projections FEAT-0042 lands; not a new store class (DEC-0421, DEC-0429)"
    size: multi-pass
    status: planned
    notes: "Feeds from GAP-0093. Implementation authorization factory-pipeline-only."

  - id: FEAT-0054
    name: "Graph Template DAG validator"
    scope: >-
      In: validate_graph_template_topology refuses self-loops and any
      directed cycle (DEC-0419); Graph Template is authored versioned
      stateless DAG with compile identity (qualified_id, version)
      (DEC-0417); Task Graph is one Mission execution projection with
      edges from,to,mapping (DEC-0420); Stage 0 graph is none of these
      (DEC-0411 honored). Out: template cycles; fingerprinting templates
      onto the Artifact rail; Board layout as a durable row. Done means
      registration refuses illegal topologies; implementation
      authorization still arrives only through the factory pipeline.
    decisions: [DEC-0419, DEC-0417, DEC-0420, DEC-0446]
    components: [COMP-QMA-DAEMON, COMP-QMA-CORE]
    blocked_by:
      - id: FEAT-0042
        reason: "Graph Template registration and Mission Compiler live on the daemon/core procedure runtime FEAT-0042 lands (DEC-0420)"
      - id: FEAT-0037
        reason: "reusable procedures / Graph Templates surface FEAT-0037 lands is the topology this validator gates (DEC-0417, DEC-0419)"
    size: multi-pass
    status: planned
    notes: "Closes hole under DEC-0312. Implementation authorization factory-pipeline-only."

  - id: FEAT-0055
    name: "Task Graph edges + outbox + JobHandle parent vocab"
    scope: >-
      In: persist task_graph_state including edges and AD-26 outbox in
      daemon sqlite (DEC-0420, DEC-0429, DEC-0439); completing
      predecessor and making successors ready is one transaction plus
      outbox; JobHandle reuses QMA AD-17 vocab exactly — never succeeded
      or awaiting_approval on a handle (DEC-0439); join algebra per
      mapping edges; no second scheduler. Out: guessed join results; a
      second job dialect; dropping edges. Done means durable edges and
      outbox recovery are specified; implementation authorization still
      arrives only through the factory pipeline.
    decisions: [DEC-0420, DEC-0439, DEC-0429, DEC-0446]
    components: [COMP-QMA-DAEMON]
    blocked_by:
      - id: FEAT-0054
        reason: "durable Task Graph edges assume Graph Template DAG validity FEAT-0054 lands (DEC-0419, DEC-0420)"
      - id: FEAT-0042
        reason: "task_graph_state and outbox extend the existing daemon sqlite projections FEAT-0042 lands (DEC-0429, DEC-0439)"
      - id: FEAT-0044
        reason: "JobHandle parent vocabulary and environment_lease occupancy law FEAT-0044 lands must stay exact (DEC-0439)"
      - id: FEAT-0033
        reason: "coordinated QMB door occupancy and ExperimentSpec lineage FEAT-0033 lands remain distinct from Task Graph control-flow edges (DEC-0420)"
    size: multi-pass
    status: planned
    notes: "Feeds from GAP-0095. Implementation authorization factory-pipeline-only."

  - id: FEAT-0056
    name: "Four proofs as thin fixtures (Book regression; ATC simulate; recipe-def; app-use change-request; pack export)"
    scope: >-
      In: thin fixtures proving (1) Book/BMS default path regression and
      dummy Book INVALID_INPUT (DEC-0424, DEC-0448); (2) ATC simulate with
      zero Book keys and complete PolicyPair (DEC-0436); (3)
      RecipeDefinition identity distinct from release fp1 (DEC-0444);
      (4) app-use change-request staging without self-apply (DEC-0421,
      DEC-0442); (5) pack export scanner oracle and pin/invoke honesty
      (DEC-0443). Out: inventing harness-engineering product surface;
      filling GAP-0081 chrome; claiming e2e adoption. Done means the
      fixtures are specified for factory stories; implementation
      authorization still arrives only through the factory pipeline.
    decisions: [DEC-0424, DEC-0436, DEC-0444, DEC-0421, DEC-0442, DEC-0443, DEC-0448]
    components: [COMP-QMF-RISK, COMP-QMB, COMP-QML, COMP-QMN, COMP-QMA-DAEMON, COMP-QMA-WIRE]
    blocked_by:
      - id: FEAT-0051
        reason: "pack pin/invoke and ContributionHit tombstone behaviour FEAT-0051 lands are required for honest export/invoke fixtures (DEC-0443)"
      - id: FEAT-0052
        reason: "ATC/app-use fixtures invoke through Operation descriptors and GrantRecords FEAT-0052 lands (DEC-0416, DEC-0437)"
      - id: FEAT-0053
        reason: "app-use change-request completeness rides product_session CAS FEAT-0053 lands (DEC-0421, DEC-0442)"
      - id: FEAT-0054
        reason: "workflow-shaped ATC authoring fixtures assume DAG-valid Graph Templates FEAT-0054 lands (DEC-0419)"
      - id: FEAT-0055
        reason: "durable procedure steps and outbox FEAT-0055 lands back multi-step proof journeys (DEC-0439)"
      - id: FEAT-0029
        reason: "Book/BMS and risk contract surfaces FEAT-0029 lands are the default composition under regression (DEC-0424, DEC-0448)"
      - id: FEAT-0031
        reason: "QMN seat/fencing after paper+L17 FEAT-0031 lands is required for ATC live-path honesty even when this feature stays at simulate (DEC-0436, DEC-0438)"
    size: multi-pass
    status: planned
    notes: "Feeds from GAP-0097. Implementation authorization factory-pipeline-only."

  - id: FEAT-0057
    name: "Safety fixtures (stream cancel+cutover; outbox restart; UNKNOWN blocks handover; stale predecessor refused; grant refuses other instance)"
    scope: >-
      In: at least two of: stream cancel+cutover with refcount (DEC-0441);
      outbox crash recovery idempotent replay (DEC-0439); UNKNOWN blocks
      handover / unknown-blocked terminal for attempt (DEC-0438);
      stale predecessor restart refused (DEC-0438); grant refuses wrong
      instance_id / config_revision (DEC-0437, DEC-0443). Out: inventing
      readiness-dashboard chrome (GAP-0100); mutmut as architecture proof.
      Done means safety fixtures are specified; implementation
      authorization still arrives only through the factory pipeline.
    decisions: [DEC-0438, DEC-0439, DEC-0441, DEC-0437, DEC-0443]
    components: [COMP-QMN, COMP-QMA-DAEMON, COMP-QMB, COMP-QMA-WIRE]
    blocked_by:
      - id: FEAT-0055
        reason: "outbox restart and JobHandle unknown/lease behaviour FEAT-0055 lands are prerequisites for durable safety fixtures (DEC-0439)"
      - id: FEAT-0056
        reason: "safety fixtures trail the four thin proof fixtures FEAT-0056 lands so failure modes are checked against the same envelopes (DEC-0437, DEC-0438)"
    size: multi-pass
    status: planned
    notes: "Implementation authorization factory-pipeline-only."
"""

STAGE = r"""
- date: '2026-09-19'
  change: "Mint Workflows construction-kit change-mode YAML into _docwork/ (SRC-21..23, EXT-2246..2285, DEC-0414..0451, GAP-0092..0100, FEAT-0051..0057) — docs/ fold and ADR-0024 still owed"
  sources: [SRC-21, SRC-22, SRC-23]
  provenance: "SRC-21 = architecture-QMX-2026-09-18/ citation surface; SRC-22 = workflows-construction-kit-2026-09-19.md rider; SRC-23 = transcript-refresh Explore-Node-Editor-Architecture.md (operator words; no_chunks). Inspect integration@270e992. Route e change-mode Stage 9."
  ledger: "DEC-0414..DEC-0444 = AD-1..AD-31 ratified; DEC-0445 umbrella; DEC-0446 preflight; DEC-0447 cheap-veto; DEC-0448 L36 law amendment; DEC-0449 DEC-0389 named amendment (DEC-0389 not superseded); DEC-0450 wiring @270e992; DEC-0451 dead-list honors. EXT-2246..EXT-2285. No live DEC superseded."
  gaps: "GAP-0092..GAP-0100 minted deferred non-blocking. GAP-0081 note patched (UI-host contracts fold; chrome stays deferred). Do not fill 0085/0063/0061/0062/0058."
  features: "FEAT-0051..FEAT-0057 minted (multi-pass, planned). First epic = FEAT-0051."
  status: in-progress
  remaining: "docs/ fold (ADR-0024, SCN-0018..0022, constitution L36, component specs, gap-report, etc.) still owed by Documentation Factory; do not start epics from this YAML mint alone."
"""


def main() -> None:
    append_if_missing(ROOT / "_docwork/manifest.yaml", "id: SRC-21", MANIFEST)
    append_if_missing(ROOT / "_docwork/extractions.yaml", "id: EXT-2246", EXTR)
    append_if_missing(ROOT / "_docwork/ledger.yaml", "id: DEC-0414", LEDGER)
    patch_gap_0081(ROOT / "_docwork/gaps.yaml")
    append_if_missing(ROOT / "_docwork/gaps.yaml", "id: GAP-0092", GAPS)
    append_if_missing(ROOT / "_docwork/feature_inventory.yaml", "id: FEAT-0051", FEATS)
    append_if_missing(ROOT / "_docwork/stage_state.yaml", "date: '2026-09-19'", STAGE)
    print("done")


if __name__ == "__main__":
    main()
