#!/usr/bin/env python3
"""Append workbench change-mode YAML. Run once from project root. Idempotent by id."""
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


def patch_gap_0085(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    old = """  - id: GAP-0085
    question: "What is the typed strategy-mechanism decomposition and recombination (EntryMechanism, ExitMechanism, Filter, SessionRule, PositionRule, InvalidationRule with paper-level provenance)?"
    needed_by: [COMP-QMA-CORE]
    blocking: false
    recommendation: "QML and qmf-registry own strategy semantics (AD-14); QMA carries the candidates and the lineage edges. Revisit at the QML sitting - StrategyHandle and ExperimentSpec are already shaped to carry the result"
    status: deferred
    answer: null
    note: "AD-14. Operator source T-1896 / T-2832. QML and qmf-registry own strategy semantics; QMA holds references and content-addressed candidates with lineage edges only, and no QMA contract redefines Strategy or Bot. Revisit at the QML sitting."
    date: 2026-08-29"""
    new = """  - id: GAP-0085
    question: "What is the typed strategy-mechanism decomposition and recombination (EntryMechanism, ExitMechanism, Filter, SessionRule, PositionRule, InvalidationRule with paper-level provenance)?"
    needed_by: [COMP-QML, COMP-QMF-REGISTRY, COMP-QMA-CORE]
    blocking: false
    recommendation: "Write-ownership is QML/host (DEC-0272 / workbench AD-4). QMA never assembles CT-33/CT-34 JSON and already refuses GAP_0085_STRATEGY_MECHANISMS on integration. Nouns wait on a later QML increment. Generator algorithm is GAP-0063, not this row."
    status: deferred
    answer: null
    note: "Ownership ruled 2026-09-14 by workbench AD-4 (DEC-0272): search varies declared CT-33 parameters in QMB; generation, if built, authors new CT-33/CT-34 and/or logic-source bytes via QML; QMA StrategyHandle may only reference already-fingerprinted records and register dev-zone candidates. Typed Entry/Exit/Filter/Session vocabulary remains unruled. QMA AD-14 parent still holds. Integration source (qma/core/ports/experiments.py) refuses the mechanism keys. Do not silently fill nouns in prose."
    date: 2026-09-14"""
    if "Write-ownership is QML/host (DEC-0272" in text:
        print("skip gaps.yaml: GAP-0085 already patched")
        return
    if old not in text:
        raise SystemExit("GAP-0085 block not found for in-place patch")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("patched GAP-0085 -> gaps.yaml")


MANIFEST = r"""
- id: SRC-17
  path: _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-14/
  kind: rider
  role: primary
  status: harvested
  note: "2026-09-14 QMX strategy-experimentation workbench architecture sitting (operator-absent one-shot; spine status final): ARCHITECTURE-SPINE.md (local AD-1..AD-16 plus Inherited Invariants, Consistency Conventions, Stack, Structural Seed, Capability map, Deferred, Open questions), CAPABILITY-EXPANSION.md (companion), .memlog.md (Fast-path through spine finalized after reviewer-gate amendments), inputs/ (code-qma/qmb/qml/qmf/qmn, classify-synthesis, donor cuts, intent-durable, orchestrator-verified), reviews/ (adversarial, parent-consistency, currency, rubric, reconcile-inputs). Citation surface for the workbench increment (EXT-2183..EXT-2212). Parents QMF AD-1..41, QMB B-1..15, QML QL-1..10, NODE TN-1..25, QMA AD-1..29, CONNECT AD-1..5 bind read-only. Local AD ids do not renumber parents. Planning on main 430fb7d; implementation inspected on integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2. Generated layouts are not preference evidence."
- id: SRC-18
  path: epansion_session
  kind: transcript
  role: primary
  status: harvested
  no_chunks: "Sitting transcript harvested into the SRC-17 memlog/spine, which is its citation surface (house treatment for architecture-sitting transcripts; no chunk index)."
  note: "Architecture-sitting session export for the 2026-09-14 workbench expansion. Citation surface for the operator's own words only; the SRC-17 memlog/spine is the citation surface for everything else (mirrors SRC-08/SRC-10/SRC-12/SRC-14)."
"""

EXTR = r"""
  - id: EXT-2183
    type: decision
    summary: "Workbench AD-1 — Workbench is not a sixth application. Every new capability names an existing COMP-* owner or an explicit connect/extend of one. Minting a new application package or a permanent experiment daemon besides qma-daemon is a spine amendment. Inherited stores stand: qmf-registry, qmf-data rooms, QMB JSONL run ledger, QMA daemon sqlite. A new store beside those is a spine amendment. DEC-0084 stays dead."
    quote: "every new capability names an existing COMP-* owner, or an explicit connect/extend of one. Minting a new application package or a permanent experiment daemon besides qma-daemon is a spine amendment."
    cite: SRC-17:ARCHITECTURE-SPINE.md#ad-1
    topics: [workbench, ad-1, reuse, no-sixth-app, DEC-0084]
    authority: rider
  - id: EXT-2184
    type: decision
    summary: "Workbench AD-2 — Exactly three experiment lanes selected by which door is called, never by a flag on a payload. (1) ungoverned — qmb.run() / ordinary Python / import qml on a controlled-room host; returns values; writes no QMB ledger line, no CT-32 registry record, no ExperimentSpec; not a Library object. L33 graduation is a separate extension-package + registration act, not this spawn. (2) governed — QMB orchestrator spawn not placed by the CT-47 door; one QMB ledger line, one CT-32; no ExperimentSpec. (3) coordinated — QMA Backtesting Service places at most one qmb CLI/MCP invocation per ExecutionEnvironment and never import qmb; requires a registered ExperimentSpec; evidence reached by _ref. workbench_lane is derived from the door and recorded only as workbench metadata on the QMB ledger line (governed for every orchestrator spawn) and on the Experiment Ledger entry (coordinated when QMA placed it). Not QMF AD-12 evidence class, not B-4 role, not a CT-32 field."
    quote: "exactly three lanes, selected by which door is called, never by a flag on a payload."
    cite: SRC-17:ARCHITECTURE-SPINE.md#ad-2
    topics: [workbench, ad-2, lanes, workbench_lane, L33]
    authority: rider
  - id: EXT-2185
    type: decision
    summary: "Workbench AD-3 — Library identity is a projection. No new COMP. Kind owner is COMP-QMF-REGISTRY. Shared Library objects are existing kinds cited by fp1: CT-33 bot, CT-34 confluence, strategy-family, CT-22 Book, CT-27 BMS, CT-28 binding, CT-12 split, CT-10 observation, CT-32 result, CT-47 ExperimentSpec (coordinated lane only). Not Library objects: QMA staging/RefinementProposals, JobHandles, Graph Templates, Skills, Routines, saved views, analysis publications, derived datasets. STRATS is a KnowledgeSource corpus; it does not write registry kinds."
    quote: "Library has no new COMP. Kind owner is COMP-QMF-REGISTRY"
    cite: SRC-17:ARCHITECTURE-SPINE.md#ad-3
    topics: [workbench, ad-3, library, fp1]
    authority: rider
  - id: EXT-2186
    type: decision
    summary: "Workbench AD-4 — Generation is not search. Search varies declared CT-33 parameters (QMB optimize/sweep, B-8) and writes trial ledger lines citing the same bot fp1. Generation, if built, authors new CT-33/CT-34 content and/or logic-source bytes via QML. The QML/host composition root mints the CT-06 envelope. QMA StrategyHandle may only reference an already-fingerprinted registry record and register those bytes as a dev-zone candidate with a QMA origin field and a CT-07 predecessor edge. QMA never assembles CT-33/CT-34 JSON, never mints mechanism nouns, never fills RandomCondition slots. Typed Entry/Exit/Filter/Session vocabulary remains a later QML increment (GAP-0085). Write-ownership is QML/host, not QMA."
    quote: "Search varies declared CT-33 parameters. Generation, if built, authors new CT-33/CT-34 content and/or logic-source bytes via QML."
    cite: SRC-17:ARCHITECTURE-SPINE.md#ad-4
    topics: [workbench, ad-4, generation, search, GAP-0085, qml]
    authority: rider
  - id: EXT-2187
    type: decision
    summary: "Workbench AD-5 — Two named analysis methods, both COMP-QMB library functions with thin doors. Projection (analysis.project) reads one cited CT-32 and its CT-29 stream; output is a saved view, not a CT-32. Durable body is the canonical JSON {method: projection, source_ct32, source_ct29, predicate, as_of}. Permitted predicates: hours/days/session windows, max-trades caps, include/exclude filters. Forbidden as projection: any change to size, R, Book/BMS fragments, execution ports, or starting_capital. Claim-class is always projection; never admission evidence. Path-dependent (analysis.rerun) is a new QMB run through the tunnel; canonical artifact is the new CT-32. analysis_method and lane are not CT-32 fields. Combining two bots' equity/trade streams into a synthetic portfolio is refused; F07 stays deferred. compare_runs is a readout, not an analysis method."
    quote: "exactly two methods, both COMP-QMB library functions with thin doors (B-1)."
    cite: SRC-17:ARCHITECTURE-SPINE.md#ad-5
    topics: [workbench, ad-5, projection, path-dependent, saved-view]
    authority: rider
  - id: EXT-2188
    type: decision
    summary: "Workbench AD-6 — A proposed Book/BMS version is a complete new fingerprinted CT-22/CT-27 document in the registry dev zone (not a patch record). Path-dependent evaluation is a QMB governed or coordinated replay citing that fingerprint. QMA may emit it only as a money_path_relevant candidate whose approval_request carries the field-level diff against the predecessor; QMA never fills an unset money-path field. Shape owner remains QMF Risk; mint remains the composition-root pattern."
    quote: "a proposed Book/BMS version is a complete new fingerprinted CT-22/CT-27 document in the registry dev zone (not a patch record)."
    cite: SRC-17:ARCHITECTURE-SPINE.md#ad-6
    topics: [workbench, ad-6, book, bms, money_path_relevant]
    authority: rider
  - id: EXT-2189
    type: decision
    summary: "Workbench AD-7 — Paper trinity. research-paper = QMB governed replay (world=replay, Book/BMS fragments in the run-config) outside the node, before promotion. node-paper = Book-level demo routing + soak/demotion (role=demo, world=live); no per-bot paper lane. QMA-paper does not exist — no execution tool at any account role. QuantConnect paper-brokerage is not a QMX lane. Promotion remains a human act outside QMA onto the node. QMB may append WriterId-scoped fragments to the B-15 hub inbox; sandbox-provenance fragments stay refused at publish and pull. hub_publish is human. QMA never writes the hub."
    quote: "QMA-paper does not exist — no execution tool at any account role."
    cite: SRC-17:ARCHITECTURE-SPINE.md#ad-7
    topics: [workbench, ad-7, paper-trinity, QMA-paper, hub-inbox]
    authority: rider
  - id: EXT-2190
    type: decision
    summary: "Workbench AD-8 — The QMA to QMB door is connect, not new. Keep Agent to QMA backtest tool to Backtesting Service to qmb CLI (MCP later) to QMB. Replace RecordingQmbDoorTransport with a real CLI transport. Compose the long-running asyncio daemon process (loopback listener + sole sqlite writer + pack roster) from existing modules — that process is connect, not a new COMP. Persist ExperimentSpec, the QMA Experiment Ledger, and ExperimentSpec CT-07 successor edges through the daemon journal / sqlite writer. QMB run ledger remains QMB JSONL, reached by _ref, never copied, never merged. Occupancy: one qmb CLI/MCP run invocation per ExecutionEnvironment. analysis.project, compare_runs, sweep.rank, ledger reads, and data.gap-check|verify|catalog|list are queries: they do not consume occupancy."
    quote: "Replace RecordingQmbDoorTransport with a real CLI transport."
    cite: SRC-17:ARCHITECTURE-SPINE.md#ad-8
    topics: [workbench, ad-8, ct-47, RecordingQmbDoorTransport, occupancy]
    authority: rider
  - id: EXT-2191
    type: decision
    summary: "Workbench AD-9 — Reusable procedures are QMA Graph Templates, Skills, and operator Routines. QMB does not grow a task graph. A step that names a QMB run is placed through the CT-47 qmb door as one CLI/MCP run invocation (occupancy). A step that names a QMB query is a door query: no occupancy, no CT-32, no spec successor. The daemon, every plugin, and every QMA worker image never import qmb. One Graph Template instantiation is one Mission. Each door step that changes resolved-config is an ExperimentSpec successor. Composition stays non-linear. No compulsory wizard. SQ Custom Projects remain a donor shape, not a clone."
    quote: "reusable procedures are QMA Graph Templates, Skills, and operator Routines. QMB does not grow a task graph."
    cite: SRC-17:ARCHITECTURE-SPINE.md#ad-9
    topics: [workbench, ad-9, procedures, graph-templates]
    authority: rider
  - id: EXT-2192
    type: decision
    summary: "Workbench AD-10 — Continuation is a daemon property. Work that must survive workstation sleep is owned by qma-daemon plus registered remote ExecutionEnvironments and the durable outbox. If laptop-off is promised, the daemon or a reachable remote env must not live only on the sleeping laptop. QMB orchestrator lifetime is the job. Coordinated cancel authority is JobHandle.cancel only. Closing a UI tab cancels nothing. Concrete always-on host is GAP-0062 (property decided; machine is not)."
    quote: "work that must survive workstation sleep is owned by qma-daemon plus registered remote ExecutionEnvironments and the durable outbox."
    cite: SRC-17:ARCHITECTURE-SPINE.md#ad-10
    topics: [workbench, ad-10, continuation, laptop-off, GAP-0062]
    authority: rider
  - id: EXT-2193
    type: decision
    summary: "Workbench AD-11 — Exploratory notebooks import qmb / import qml on a controlled-room host (B-9). A managed interpreter lifecycle, if product-owned, is a QMA ExecutionEnvironment (Analysis RLM kernel or a declared env kind). It is not a QMB module and not a new COMP."
    quote: "exploratory notebooks import qmb / import qml on a controlled-room host (B-9)."
    cite: SRC-17:ARCHITECTURE-SPINE.md#ad-11
    topics: [workbench, ad-11, notebooks, rlm-kernel]
    authority: rider
  - id: EXT-2194
    type: decision
    summary: "Workbench AD-12 — Extensibility ladder, four rungs in order: (1) ui-editable config variables on templates; (2) ordinary Python logic + QMB ports/adapters; (3) QMA plugins, skills, graph templates, desk packs; (4) UI contribution SDK. Rungs 1-3 bind now. Rung 4 stays GAP-0081 deferred. No-code authoring is not promised. QMA plugin vocabulary stays QMA-scoped (DEC-0346)."
    quote: "Rungs 1–3 bind now. Rung 4 stays GAP-0081 deferred."
    cite: SRC-17:ARCHITECTURE-SPINE.md#ad-12
    topics: [workbench, ad-12, extensibility, GAP-0081]
    authority: rider
  - id: EXT-2195
    type: decision
    summary: "Workbench AD-13 — Acquire / verify / gap-check / catalog / generate are QMB data commands wrapping qmf-data (B-11). CSV/file import is a CT-15 adapter (extend ingest), not a new store. Quality surfaces are read models over CT-13 data quality events and gap_check reports. A derived dataset is a new fingerprinted artifact with a lineage edge; it is not a Library kind. Vendor-style timezone clones that auto-update the source under an experiment's feet are refused. Coordinated ExperimentSpec data_ref must cite CT-12 split fingerprints. Governed runs cite splits on the resolved run-config, not via ExperimentSpec."
    quote: "acquire / verify / gap-check / catalog / generate are QMB data commands wrapping qmf-data (B-11)."
    cite: SRC-17:ARCHITECTURE-SPINE.md#ad-13
    topics: [workbench, ad-13, qmf-data, ct-12, ct-15]
    authority: rider
  - id: EXT-2196
    type: decision
    summary: "Workbench AD-14 — A candidate set is a query. Retain / filter / rank is a read-time view over (1) QMB ledger lines, (2) registry as-of sets including dev-zone candidates of Library kinds, (3) coordinated Experiment Ledger refs. It does not read QMA staging. sweep.rank is this view; it publishes no copied-row artifact. A saved view's home follows AD-5. Not qmf-registry, not a new sqlite table, not a citation without a body."
    quote: "retain / filter / rank is a read-time view over (1) QMB ledger lines, (2) registry as-of sets including dev-zone candidates of Library kinds, (3) coordinated Experiment Ledger refs."
    cite: SRC-17:ARCHITECTURE-SPINE.md#ad-14
    topics: [workbench, ad-14, candidate-set, sweep.rank]
    authority: rider
  - id: EXT-2197
    type: decision
    summary: "Workbench AD-15 — Do not extend CT-32 or B-4. Mapping is total. Governed/coordinated confirmation run: B-4 role=confirmation; no AD-15 claim-class. Optimize trial / sweep combo: role=trial. MC / WF replicate: role=replicate plus B-7 procedure label robustness or infra-stress. Aborted: role=aborted. Projection saved view: no B-4 role (not a run); claim-class projection; inherit source world; never confirmed. Path-dependent re-run: B-4 role of that run. Confirmation evidence remains B-4 role=confirmation only. L20 stands. Replay-world verdicts still cannot gate live money."
    quote: "do not extend CT-32 or B-4. Mapping is total."
    cite: SRC-17:ARCHITECTURE-SPINE.md#ad-15
    topics: [workbench, ad-15, labels, b-4, ct-32]
    authority: rider
  - id: EXT-2198
    type: decision
    summary: "Workbench AD-16 — There is no Project kind and no Workspace kind. Coordinated research continuity is the ExperimentSpec fp1 (code_ref when code changes, resolved_config_ref for parameter/config, data_ref = CT-12 split, environment_ref). QMB workspace defaults are a config-compiler layer (B-3), never an identity. A notebook file is an ungoverned working surface until an orchestrator spawn or a CT-47 placement; it joins the undertaking only as code_ref or as an ExecutionEnvironment session, not as a fourth identity. Display names project / workspace are UX aliases."
    quote: "there is no Project kind and no Workspace kind. Coordinated research continuity is the ExperimentSpec fp1"
    cite: SRC-17:ARCHITECTURE-SPINE.md#ad-16
    topics: [workbench, ad-16, ExperimentSpec, project, workspace]
    authority: rider
  - id: EXT-2199
    type: context
    summary: "Workbench brownfield verified on integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2 via git show (no checkout). Present: qmb results/ct32, qml declaration, qmf-risk types, qma-core/daemon/wire packages, RecordingQmbDoorTransport default, GAP_0085_STRATEGY_MECHANISMS refused in ports/experiments.py. Missing/unproven: composed asyncio daemon process (no asyncio.run/websockets/uvicorn under qma-daemon/qma-wire src), real qmb CLI door (recording transport does not spawn qmb), robustness CLI group, analysis.project, structure generator, qma-ui-contract beyond stub. Class/test existence is not end-to-end proof."
    quote: "Class/test existence is not end-to-end proof. Contract YAML defined-unwired on integration is stale where matching source exists"
    cite: SRC-17:ARCHITECTURE-SPINE.md#consistency-conventions
    topics: [workbench, brownfield, integration, source-inspected]
    authority: rider
  - id: EXT-2200
    type: decision
    summary: "Workbench preflight: reuse COMP-QMB, COMP-QML, COMP-QMA-CORE, COMP-QMA-WIRE, COMP-QMA-DAEMON, COMP-QMF-REGISTRY, COMP-QMF-RISK, COMP-QMF-DATA, COMP-QMN. No new component. No sixth application. Candidates refused: COMP-EXP, HTTP experiment service, Project/Workspace kinds, second backtest governor, donor engines, QMA-paper, per-bot paper lane, UI SDK this sitting."
    quote: "This sitting does not mint a fifth runtime or a sixth package."
    cite: SRC-17:ARCHITECTURE-SPINE.md#design-paradigm
    topics: [workbench, preflight, reuse]
    authority: rider
  - id: EXT-2201
    type: death
    summary: "Donor engines stay shapes-only and dead as products: StrategyQuant random/genetic engine and building-block DSL; QuantConnect Lean engine and paper brokerage as a QMX lane; RoboQuant.dev RQ Engine; OpenResearch git-worktree-per-parameter (Cut DEC-0376); QuantAnalyzer treating filtered trades as path-dependent truth. DEC-0084 central backtest service stays dead. QMA-paper does not exist."
    quote: "DEC-0084 / DEC-0085 / DEC-0086 stay dead. No central backtest service; no donor engine adoption."
    cite: SRC-17:ARCHITECTURE-SPINE.md#inherited-invariants
    topics: [workbench, dead-list, donor-engines, DEC-0084, QMA-paper]
    authority: rider
  - id: EXT-2202
    type: correction
    summary: "Docs vs code: CT-32/33/34/47 and CT-40..51 (and risk CT-22..31 where value types exist) still say defined-unwired / no code exists while matching packages exist on integration@1b451a8. Reconcile to source-inspected. Source-inspected is not end-to-end demonstrated. This is documentation drift, not an architectural fork."
    quote: "Contract YAML defined-unwired on integration is stale where matching source exists; reconcile in documentation-factory, do not invent a second design."
    cite: SRC-17:ARCHITECTURE-SPINE.md#consistency-conventions
    topics: [workbench, wiring_status, source-inspected, defined-unwired]
    authority: rider
  - id: EXT-2203
    type: open
    summary: "Workbench cheap-veto assumptions: (A1) Connect-wave (door + projections + named analysis + procedures/continuation config) is the coherent first implementation area; generation can trail. (A2) Work-environment roster stays UI-open (AD-16 aliases only). (A3) Generated layouts and reactions to them are not preference evidence. (A4) Optuna pin stays 4.9.0 on integration despite upstream 5.0.0. (A5) No PRD rewrite this sitting — FR addenda are GAP-0061."
    quote: "Generated layouts and reactions to them are not preference evidence."
    cite: SRC-17:.memlog.md
    topics: [workbench, assumptions, cheap-veto]
    authority: rider
  - id: EXT-2204
    type: open
    summary: "Workbench open questions left as gaps, never silent prose: GAP-0085 mechanism vocabulary (ownership ruled, nouns open); GAP-0063 first generator algorithm; GAP-0062 concrete always-on host for AD-10; GAP-0061 PRD FR addenda for ExperimentSpec, analysis methods, generation-vs-search, procedures."
    quote: "Open: generator algorithm; concrete always-on host; PRD FR coverage for ExperimentSpec, procedures, generation, analysis methods."
    cite: SRC-17:ARCHITECTURE-SPINE.md#open-questions
    topics: [workbench, gaps, GAP-0085, GAP-0061, GAP-0062, GAP-0063]
    authority: rider
  - id: EXT-2205
    type: decision
    summary: "Workbench spine finalized status:final 2026-09-14 after reviewer-gate amendments (saved-view body/homes/query occupancy; workbench_lane dual-label; hub-inbox legal B-15 path; ExperimentSpec data_ref coordinated-only; local AD ids disclaimed). Paradigm: workbench composition over hexagonal libraries. Child of QMF/QMB/QML/NODE/QMA/CONNECT parents. Captain next skill is documentation-factory then bmad-create-epics-and-stories."
    quote: "spine finalized after reviewer-gate amendments"
    cite: SRC-17:.memlog.md
    topics: [workbench, spine-final, reviewer-gate]
    authority: rider
  - id: EXT-2206
    type: constraint
    summary: "Do not implement UI, Penpot, or a new COMP in this expansion. Planning on main; implementation baseline local integration 1b451a8. Do not switch branches. Implementation authorization remains factory-pipeline-only."
    quote: "Do not implement UI, Penpot, or a new COMP in this expansion."
    cite: SRC-17:CAPABILITY-EXPANSION.md
    topics: [workbench, no-ui, no-penpot, factory-only]
    authority: rider
  - id: EXT-2207
    type: context
    summary: "Capability expansion clusters (constraint graph, not a required sequence): Door + ExperimentSpec persistence; Library projections + candidate queries; Named analysis methods; CLI coverage of robustness/sweeps; Procedure Graph Templates; Continuation host config; Structure generation (trails); UI contribution SDK (GAP-0081); GAP-0048 taxonomy (own sitting)."
    quote: "Four architecture areas, not a funnel. Epics may start in any area once dependencies below are respected."
    cite: SRC-17:CAPABILITY-EXPANSION.md
    topics: [workbench, clusters, epics]
    authority: rider
  - id: EXT-2208
    type: constraint
    summary: "Parent-consistency reviewer gate amendments that the FINAL spine already carries and this increment must not regress: L33 is two-artifact registration not orchestrator spawn; workbench_lane is not AD-12 evidence class and is not a CT-32/B-4 field; QMB WriterId fragments may enter hub-inbox under B-15 while sandbox-provenance stays refused; AD-1 legal stores include the inherited QMA daemon sqlite / Experiment Ledger; AD-14 does not read QMA staging; AD-5 projection forbids size rescale."
    quote: "FAIL-with-amendments. Five local sentences still contradict or weaken a parent; none require re-opening a ruling; all are amendments at this desk."
    cite: SRC-17:reviews/review-parent-consistency.md
    topics: [workbench, parent-consistency, L33, hub-inbox]
    authority: rider
  - id: EXT-2209
    type: value
    summary: "Workbench stack seed: inherited pins stand; no new framework. CPython 3.14 (3.14.7 current stable 2026-08-05; 3.15 not adopted). Optuna remains an internal QMB sampler adapter pinned optuna==4.9.0 on integration (qmb/pyproject.toml, DEC-0168); upstream 5.0.0 exists 2026-09-07 and is not adopted — TPE default change is a contract-versioning event."
    quote: "Optuna (QMB sampler adapter only) optuna==4.9.0 on integration. Upstream 5.0.0 exists 2026-09-07; not adopted."
    cite: SRC-17:ARCHITECTURE-SPINE.md#stack
    topics: [workbench, stack, optuna, cpython]
    authority: rider
  - id: EXT-2210
    type: constraint
    summary: "Consistency conventions: QMB is a library+CLI, never an engine/kernel. Bare paper, calendar, kernel, plugin (outside QMA), and snapshot (for registry state) stay banned. Say research-paper / node-paper; market-hours / day-boundary / news calendar; RLM kernel; as-of set. Cite Book, BMS, bot, split, result, ExperimentSpec by fp1. Errors are typed refusals (CT-04). Configurable means ui-editable at platform level (L38)."
    quote: "QMB is a library+CLI, never an engine/kernel. Bare paper, calendar, kernel, plugin (outside QMA), and snapshot (for registry state) stay banned."
    cite: SRC-17:ARCHITECTURE-SPINE.md#consistency-conventions
    topics: [workbench, vocabulary, bans]
    authority: rider
  - id: EXT-2211
    type: context
    summary: "epansion_session is the architecture-sitting transcript. Operator dictation: take ownership of backend capability expansion as one long-running architecture assignment; no documentation factory in that sitting; operator away; do not pause on ambiguity. This documentation-factory sitting is the follow-on the spine named."
    quote: "you're going to only handle architecture, no documentation factory"
    cite: SRC-18
    topics: [workbench, transcript, operator-away]
    authority: rider
  - id: EXT-2212
    type: decision
    summary: "Workbench umbrella: local AD-1..AD-16 adopted in full as DEC-0269 through DEC-0284. Preflight reuse, no new COMP, no new contract id, no new dependency edge. Wiring-status reconcile is DEC-0286. Cheap-veto assumptions ride DEC-0287. Implementation authorization arrives only through the factory pipeline."
    quote: "Workbench composition over hexagonal libraries. QMF remains the contract-hub toolbox. QMB, QML, QMA, and QMN remain the four application-layer products."
    cite: SRC-17:ARCHITECTURE-SPINE.md#design-paradigm
    topics: [workbench, spine-adoption, umbrella]
    authority: rider
"""

LEDGER = r"""
  - id: DEC-0269
    title: "Workbench AD-1 — Workbench is not a sixth application"
    statement: "Every new capability names an existing COMP-* owner, or an explicit connect/extend of one. Minting a new application package or a permanent experiment daemon besides qma-daemon is a spine amendment. Inherited stores stand: qmf-registry, qmf-data rooms, QMB JSONL run ledger, QMA daemon sqlite (journal, Experiment Ledger). A new store beside those is a spine amendment. DEC-0084 stays dead."
    status: ratified
    rationale: "Prevents a COMP-EXP / HTTP experiment service / second identity store drifting from QMB+QMA. Workbench sitting 2026-09-14, spine status final."
    sources: [EXT-2183, EXT-2200, EXT-2212]
    authority: rider
    component: COMP-QMB
    tags: [workbench, ad-1, no-sixth-app, DEC-0084]
    date: 2026-09-14
    spine_ref: "SRC-17:ARCHITECTURE-SPINE.md#ad-1"

  - id: DEC-0270
    title: "Workbench AD-2 — Three experiment lanes, door-derived"
    statement: "Exactly three lanes, selected by which door is called, never by a flag on a payload. (1) ungoverned — qmb.run() / ordinary Python / import qml on a controlled-room host. Returns values. Writes no QMB ledger line, no CT-32 registry record, no ExperimentSpec. It is not a Library object. L33 graduation (ungoverned Python to governed evidence) is a separate extension-package + registration act, not this spawn. (2) governed — QMB orchestrator spawn not placed by the CT-47 door (CLI/API spawn_governed, including path-dependent analysis.rerun). One QMB ledger line, one CT-32. No ExperimentSpec. (3) coordinated — QMA Backtesting Service places at most one qmb CLI/MCP invocation per ExecutionEnvironment and never import qmb. Requires a registered ExperimentSpec. The spawned run's QMB ledger line and CT-32 are the evidence, reached by _ref from the Experiment Ledger; QMA does not copy them. workbench_lane is derived from the door and is recorded only as workbench metadata on the QMB ledger line (governed for every orchestrator spawn, including those QMA placed) and on the Experiment Ledger entry (coordinated when QMA placed it). It is not QMF AD-12 evidence class, not B-4 role, and not a CT-32 field. A QMA-placed run therefore has two honest labels on two objects. UI/agents select a lane by calling run / spawn_governed / the QMA backtest tool; a fourth call path is a spine amendment."
    status: ratified
    rationale: "Prevents exploratory values, governed evidence, and agent jobs collapsing into one run noun; prevents caller-declared lane flags; prevents treating spawn as L33. Workbench sitting 2026-09-14, spine status final after parent-consistency amendments."
    sources: [EXT-2184, EXT-2208, EXT-2212]
    authority: rider
    component: COMP-QMB
    tags: [workbench, ad-2, lanes, workbench_lane, L33]
    date: 2026-09-14
    spine_ref: "SRC-17:ARCHITECTURE-SPINE.md#ad-2"

  - id: DEC-0271
    title: "Workbench AD-3 — Library identity is a projection"
    statement: "Library has no new COMP. Kind owner is COMP-QMF-REGISTRY; query surfaces are the QMB B-15 registry-read as-of port, the QMB ledger merge view, and the QMA Experiment Ledger. Shared Library objects are exactly these existing kinds, cited by fp1: CT-33 bot, CT-34 confluence, strategy-family, CT-22 Book, CT-27 BMS, CT-28 binding, CT-12 split, CT-10 observation, CT-32 result, CT-47 ExperimentSpec (coordinated lane only). Logic source-manifests are cited from CT-33, not a separate Library kind. Not Library objects: QMA staging/RefinementProposals, JobHandles, Graph Templates, Skills, Routines, saved views, analysis publications, derived datasets. Work-environment tabs and display aliases are UX over those fingerprints. STRATS is a KnowledgeSource corpus (QMA AD-19); it does not write registry kinds. Saved views and analysis publications are not registry kinds; Library search returns them only as query hits citing the source kind's fp1."
    status: ratified
    rationale: "Prevents one bot/result existing as three records; a STRATS-shaped second store; QMA staging mixed into Library kinds. Workbench sitting 2026-09-14, spine status final."
    sources: [EXT-2185, EXT-2212]
    authority: rider
    component: COMP-QMF-REGISTRY
    tags: [workbench, ad-3, library, fp1]
    date: 2026-09-14
    spine_ref: "SRC-17:ARCHITECTURE-SPINE.md#ad-3"

  - id: DEC-0272
    title: "Workbench AD-4 — Generation is not search"
    statement: "Search varies declared CT-33 parameters (QMB optimize/sweep, B-8) and writes trial ledger lines citing the same bot fp1. Generation, if built, authors new CT-33/CT-34 content and/or logic-source bytes via QML. The QML/host composition root mints the CT-06 envelope. QMA StrategyHandle may only (1) reference an already-fingerprinted registry record and (2) register those bytes as a dev-zone candidate with a QMA origin field and a CT-07 predecessor edge. QMA never assembles CT-33/CT-34 JSON, never mints mechanism nouns, never fills RandomCondition slots. The typed Entry/Exit/Filter/Session vocabulary remains a later QML increment (GAP-0085); write-ownership is QML/host, not QMA. SQ RandomCondition templates are a donor shape, not a schema to copy. The first generator algorithm is GAP-0063."
    status: ratified
    rationale: "Prevents TPE parameter search being sold as strategy generation; a generator living inside QMB's tunnel; QMA assembling CT-33 JSON. Ownership of GAP-0085 is now ruled; nouns stay deferred. Workbench sitting 2026-09-14, spine status final."
    sources: [EXT-2186, EXT-2204, EXT-2212]
    authority: rider
    component: COMP-QML
    tags: [workbench, ad-4, generation, search, GAP-0085]
    date: 2026-09-14
    spine_ref: "SRC-17:ARCHITECTURE-SPINE.md#ad-4"

  - id: DEC-0273
    title: "Workbench AD-5 — Two named analysis methods"
    statement: "Exactly two methods, both COMP-QMB library functions with thin doors (B-1). Projection (analysis.project) reads one cited CT-32 and its CT-29 stream. Output is a saved view, not a CT-32. The durable body is the canonical JSON {method: projection, source_ct32, source_ct29, predicate, as_of} — a citation without that body is not a saved view. as_of is the source CT-32's registry_as_of / occurrence, never query time. Identity fp1 is of that JSON. Never a copied trade list or rescaled measure set. Permitted predicates: hours/days/session windows, max-trades caps, include/exclude filters. Forbidden as projection: any change to size, R, Book/BMS fragments, execution ports, or starting_capital. Claim-class is always projection; never admission evidence. Homes: ungoverned — return value only, not durable, not a Library object; governed-without-QMA — JSON sidecar in the source run-dir (not a new orchestrator spawn, not a QMB ledger line, not a CT-32); coordinated — the QMA daemon (Agent holding dispatch_lease) persists the JSON and an analysis.published Experiment Ledger entry citing that fp1. QMB never opens daemon sqlite. analysis.project is not a run: no CT-32, no QMB ledger line, no ExperimentSpec successor, no occupancy. Coordinated call = daemon shells the CLI as a query, waits, persists refs. analysis.rerun remains a run. Path-dependent (analysis.rerun) is a new QMB run through the tunnel (new resolved run-config: Book/BMS fragments, fill/cost/financing ports, starting_capital). A starting_capital override stamps seed_overridden on the binding and forces the B-4 fold unrated (B-3). Its canonical artifact is the new CT-32. analysis_method and lane are not CT-32 fields; they live on the QMB ledger line (governed) and/or the Experiment Ledger entry (coordinated) as metadata citing the CT-32 by _ref. Combining two bots' equity/trade streams into a synthetic portfolio is neither method — refused here; F07 stays deferred. compare_runs is a readout of cited CT-32 fields, not an analysis method and not a new artifact; it stamps nothing. F08 that only overlays two existing series uses compare_runs; F08 that changes sizing/Book/seed is path-dependent (AD-6). QMA queries may call analysis.project / analysis.rerun and persist refs; they may not reimplement the filter."
    status: ratified
    rationale: "Prevents a filtered trade list being treated as a Book/BMS counterfactual; a new CT-32 sibling for a projection; size/seed rewrites as rescale. Workbench sitting 2026-09-14, spine status final."
    sources: [EXT-2187, EXT-2208, EXT-2212]
    authority: rider
    component: COMP-QMB
    tags: [workbench, ad-5, analysis, projection, path-dependent]
    date: 2026-09-14
    spine_ref: "SRC-17:ARCHITECTURE-SPINE.md#ad-5"

  - id: DEC-0274
    title: "Workbench AD-6 — Book and BMS variants are candidates plus replay"
    statement: "A proposed Book/BMS version is a complete new fingerprinted CT-22/CT-27 document in the registry dev zone (not a patch record). Path-dependent evaluation is a QMB governed or coordinated replay citing that fingerprint (DEC-0270, DEC-0273). QMA may emit it only as a money_path_relevant candidate whose approval_request carries the field-level diff against the predecessor; QMA never fills an unset money-path field. Shape owner remains QMF Risk; mint remains the composition-root pattern (same as CT-33)."
    status: ratified
    rationale: "Prevents trade-list rescaling posing as Book simulation; QMA filling unset risk fields; patch records posing as definitions. Workbench sitting 2026-09-14, spine status final."
    sources: [EXT-2188, EXT-2212]
    authority: rider
    component: COMP-QMF-RISK
    tags: [workbench, ad-6, book, bms, candidates]
    date: 2026-09-14
    spine_ref: "SRC-17:ARCHITECTURE-SPINE.md#ad-6"

  - id: DEC-0275
    title: "Workbench AD-7 — Paper trinity"
    statement: "research-paper = QMB governed replay (world=replay, Book/BMS fragments in the run-config) outside the node, before promotion. node-paper = Book-level demo routing + soak/demotion (role=demo, world=live); no per-bot paper lane (DEC-0261). QMA-paper does not exist — no execution tool at any account role (DEC-0341). QuantConnect paper-brokerage is not a QMX lane. Promotion remains a human act outside QMA onto the node. QMB may append WriterId-scoped fragments to the B-15 hub inbox; sandbox-provenance fragments stay refused at publish and pull (TN-20). hub_publish is human. QMA never writes the hub; it holds candidate refs only."
    status: ratified
    rationale: "Prevents QuantConnect paper-brokerage, node soak, and QMB replay sharing one paper noun; keeps the only legal hub write path (B-15 WriterId fragments) open while sandbox-provenance stays refused. Workbench sitting 2026-09-14, spine status final after parent-consistency amendments."
    sources: [EXT-2189, EXT-2201, EXT-2208, EXT-2212]
    authority: rider
    component: COMP-QMB
    tags: [workbench, ad-7, paper-trinity, QMA-paper, hub-inbox]
    date: 2026-09-14
    spine_ref: "SRC-17:ARCHITECTURE-SPINE.md#ad-7"

  - id: DEC-0276
    title: "Workbench AD-8 — The QMA to QMB door is connect, not new"
    statement: "Keep the route Agent to QMA backtest tool to Backtesting Service to qmb CLI (MCP later) to QMB. Replace RecordingQmbDoorTransport with a real CLI transport. Compose the long-running asyncio daemon process (loopback listener + sole sqlite writer + pack roster) from the existing modules — that process is connect, not a new COMP. Persist ExperimentSpec, the QMA Experiment Ledger, and ExperimentSpec CT-07 successor edges through the daemon journal / sqlite writer. The QMB run ledger remains QMB JSONL, reached by _ref, never copied, never merged (QMA AD-6). QMB does not write ExperimentSpec edges. Occupancy: one qmb CLI/MCP run invocation per ExecutionEnvironment (backtest, optimize, sweep, robustness, analysis.rerun, data download that mutates rooms). QMB's process-per-run children inside that invocation are not additional QMA jobs. analysis.project, compare_runs, sweep.rank, ledger reads, and data.gap-check|verify|catalog|list are queries: they do not consume occupancy, mint no CT-32, and mint no ExperimentSpec successor. Docs that still say CT-47 no code exists are stale relative to integration@1b451a8 (DEC-0286)."
    status: ratified
    rationale: "Prevents a second backtest governor; import qmb from QMA; treating the recording transport as a working integration. Workbench sitting 2026-09-14, spine status final."
    sources: [EXT-2190, EXT-2199, EXT-2212]
    authority: rider
    component: COMP-QMA-DAEMON
    tags: [workbench, ad-8, ct-47, connect, occupancy]
    date: 2026-09-14
    spine_ref: "SRC-17:ARCHITECTURE-SPINE.md#ad-8"

  - id: DEC-0277
    title: "Workbench AD-9 — Procedures live in QMA; steps live in QMB"
    statement: "Reusable procedures are QMA Graph Templates, Skills, and operator Routines. QMB does not grow a task graph. A step that names a QMB run (backtest, optimize, sweep, robustness, analysis.rerun, mutating data download) is placed through the CT-47 qmb door as one CLI/MCP run invocation (occupancy, DEC-0276). A step that names a QMB query (analysis.project, compare_runs, sweep.rank, gap-check/verify/catalog/list) is a door query: no occupancy, no CT-32, no spec successor. The daemon, every plugin, and every QMA worker image never import qmb. The CLI process is QMB; in-process library calls from QMA are a spine amendment. One Graph Template instantiation is one Mission. Each door step that changes resolved-config is an ExperimentSpec successor (create_successor + the QMA ExperimentSpec CT-07 branches-from edge already minted for specs — not bot supersedes, not a new edge kind); the procedure is not itself an ExperimentSpec. Composition stays non-linear: any step may be the first door placement. SQ Custom Projects remain a donor shape, not a clone. No compulsory research-to-backtest-to-paper wizard."
    status: ratified
    rationale: "Prevents a workflow engine inside QMB and a compulsory linear wizard. Workbench sitting 2026-09-14, spine status final."
    sources: [EXT-2191, EXT-2212]
    authority: rider
    component: COMP-QMA-DAEMON
    tags: [workbench, ad-9, procedures, graph-templates]
    date: 2026-09-14
    spine_ref: "SRC-17:ARCHITECTURE-SPINE.md#ad-9"

  - id: DEC-0278
    title: "Workbench AD-10 — Continuation is a daemon property"
    statement: "Work that must survive workstation sleep is owned by qma-daemon plus registered remote ExecutionEnvironments and the durable outbox. If laptop-off is promised, the daemon or a reachable remote env must not live only on the sleeping laptop. QMB orchestrator lifetime is the job. Coordinated cancel authority is JobHandle.cancel only; the door maps it to QMB abort and the QMB ledger writes aborted. Governed-without-QMA cancel is QMB abort only. Ungoverned cancel is process death and writes nothing. Closing a UI tab cancels nothing. No other writer may set a terminal JobHandle or ledger state. The concrete always-on host is GAP-0062 — the property is decided; the machine is not."
    status: ratified
    rationale: "Prevents QMB process-per-run being treated as unattended continuation. Host machine left as an explicit gap, not silent prose. Workbench sitting 2026-09-14, spine status final."
    sources: [EXT-2192, EXT-2204, EXT-2212]
    authority: rider
    component: COMP-QMA-DAEMON
    tags: [workbench, ad-10, continuation, GAP-0062]
    date: 2026-09-14
    spine_ref: "SRC-17:ARCHITECTURE-SPINE.md#ad-10"

  - id: DEC-0279
    title: "Workbench AD-11 — Notebooks import the library; lifecycle is an environment"
    statement: "Exploratory notebooks import qmb / import qml on a controlled-room host (B-9). A managed interpreter lifecycle, if product-owned, is a QMA ExecutionEnvironment (Analysis RLM kernel or a declared env kind). It is not a QMB module and not a new COMP."
    status: ratified
    rationale: "Prevents a Jupyter product inside QMB; reviving the banned bare kernel name outside QMA. Workbench sitting 2026-09-14, spine status final."
    sources: [EXT-2193, EXT-2212]
    authority: rider
    component: COMP-QMB
    tags: [workbench, ad-11, notebooks]
    date: 2026-09-14
    spine_ref: "SRC-17:ARCHITECTURE-SPINE.md#ad-11"

  - id: DEC-0280
    title: "Workbench AD-12 — Extensibility ladder"
    statement: "Four rungs, in order: (1) ui-editable config variables on templates; (2) ordinary Python logic + QMB ports/adapters; (3) QMA plugins, skills, graph templates, desk packs; (4) UI contribution SDK. Rungs 1-3 bind now. Rung 4 stays GAP-0081 deferred. No-code authoring is not promised. QMA plugin vocabulary stays QMA-scoped (DEC-0346)."
    status: ratified
    rationale: "Prevents promising a UI plugin SDK that is GAP-0081; treating source-only extension as the product. Workbench sitting 2026-09-14, spine status final."
    sources: [EXT-2194, EXT-2212]
    authority: rider
    component: COMP-QMA-CORE
    tags: [workbench, ad-12, extensibility, GAP-0081]
    date: 2026-09-14
    spine_ref: "SRC-17:ARCHITECTURE-SPINE.md#ad-12"

  - id: DEC-0281
    title: "Workbench AD-13 — Data work wraps qmf-data"
    statement: "Acquire / verify / gap-check / catalog / generate are QMB data commands wrapping qmf-data (B-11). CSV/file import is a CT-15 adapter (extend ingest), not a new store. Spike/OHLC quality detectors, if added, extend QMB data over existing observations — they are not AD-5 analysis views and not a new COMP. Quality surfaces are read models over CT-13 data quality events and gap_check reports. A derived dataset is a new fingerprinted artifact with a lineage edge; it is not a Library kind (DEC-0271). Vendor-style timezone clones that auto-update the source under an experiment's feet are refused. Only a coordinated ExperimentSpec exists (DEC-0270); its data_ref must cite CT-12 split fingerprints (B-8). Governed runs cite splits on the resolved run-config, not via ExperimentSpec. Ungoverned calls mint neither."
    status: ratified
    rationale: "Prevents a QuantDataManager clone store; silent auto-update of experiment inputs. Workbench sitting 2026-09-14, spine status final."
    sources: [EXT-2195, EXT-2212]
    authority: rider
    component: COMP-QMB
    tags: [workbench, ad-13, qmf-data, ct-12]
    date: 2026-09-14
    spine_ref: "SRC-17:ARCHITECTURE-SPINE.md#ad-13"

  - id: DEC-0282
    title: "Workbench AD-14 — A candidate set is a query"
    statement: "Retain / filter / rank is a read-time view over (1) QMB ledger lines, (2) registry as-of sets including dev-zone candidates of Library kinds, (3) coordinated Experiment Ledger refs. It does not read QMA staging. sweep.rank is this view; it publishes no copied-row artifact. A saved view's home follows DEC-0273: return value (ungoverned); JSON sidecar in the source run-dir (governed-without-QMA); daemon-persisted JSON plus analysis.published (coordinated). Not qmf-registry, not a new sqlite table, not a citation without a body."
    status: ratified
    rationale: "Prevents a copied-row candidate database beside the ledger. Workbench sitting 2026-09-14, spine status final after parent-consistency amendment dropping staging from this view."
    sources: [EXT-2196, EXT-2208, EXT-2212]
    authority: rider
    component: COMP-QMB
    tags: [workbench, ad-14, candidate-set]
    date: 2026-09-14
    spine_ref: "SRC-17:ARCHITECTURE-SPINE.md#ad-14"

  - id: DEC-0283
    title: "Workbench AD-15 — Labels stay parent-shaped"
    statement: "Do not extend CT-32 or B-4. Mapping is total. Governed/coordinated confirmation run: B-4 role=confirmation; no AD-15 claim-class (it is not an analysis); AD-12 evidence class as parent. Optimize trial / sweep combo: role=trial. MC / WF replicate: role=replicate plus B-7 procedure label robustness or infra-stress. Aborted: role=aborted. Projection saved view: no B-4 role (not a run); claim-class projection; inherit source world; never confirmed. Path-dependent re-run: B-4 role of that run; may be published as analysis only as an Experiment Ledger analysis.published entry citing the new CT-32; still not admission evidence unless role=confirmation. Confirmation evidence remains B-4 role=confirmation only. L20 stands. Replay-world verdicts still cannot gate live money. Published analysis = a saved view or an Experiment Ledger analysis.published entry, not every CT-32."
    status: ratified
    rationale: "Prevents projection, synthetic, or trial results masquerading as confirmation; extending CT-32 or B-4 with workbench fields. Workbench sitting 2026-09-14, spine status final."
    sources: [EXT-2197, EXT-2212]
    authority: rider
    component: COMP-QMB
    tags: [workbench, ad-15, labels, b-4]
    date: 2026-09-14
    spine_ref: "SRC-17:ARCHITECTURE-SPINE.md#ad-15"

  - id: DEC-0284
    title: "Workbench AD-16 — Research-undertaking identity"
    statement: "There is no Project kind and no Workspace kind. Coordinated research continuity is the ExperimentSpec fp1 (code_ref when code changes, resolved_config_ref for parameter/config, data_ref = CT-12 split, environment_ref). QMB workspace defaults are a config-compiler layer (B-3), never an identity. A notebook file is an ungoverned working surface until an orchestrator spawn or a CT-47 placement; it joins the undertaking only as code_ref or as an ExecutionEnvironment session, not as a fourth identity. Display names project / workspace are UX aliases over ExperimentSpec (coordinated) or over a bot fp1 (governed). UI tabs may group those aliases; they must not mint a record."
    status: ratified
    rationale: "Prevents a QuantConnect Project package; Workspace-as-identity; Bot + ExperimentSpec + run-config + notebook as four unjoined records. Workbench sitting 2026-09-14, spine status final (F12 join landed as this AD after reconcile-inputs flagged the quiet miss)."
    sources: [EXT-2198, EXT-2212]
    authority: rider
    component: COMP-QMA-CORE
    tags: [workbench, ad-16, ExperimentSpec, project, workspace]
    date: 2026-09-14
    spine_ref: "SRC-17:ARCHITECTURE-SPINE.md#ad-16"

  - id: DEC-0285
    title: "Workbench spine adopted in full (reuse existing applications; no sixth package)"
    statement: "The 2026-09-14 QMX strategy-experimentation workbench spine (architecture-QMX-2026-09-14, status final) is adopted in full as DEC-0269 through DEC-0284. Paradigm is workbench composition over hexagonal libraries: one fingerprint identity, three door-derived experiment lanes, two named analysis methods. Preflight verdict is reuse COMP-QMB (analysis functions, CLI coverage, data commands, governed/ungoverned doors), COMP-QML (generation authoring, ungoverned tunnel), COMP-QMA-CORE (ExperimentSpec, handles, ports), COMP-QMA-WIRE (CT-40 listener posture), COMP-QMA-DAEMON (real CLI door, ExperimentSpec persistence, composed asyncio process, Graph Templates, continuation), COMP-QMF-REGISTRY (Library kinds), COMP-QMF-RISK (Book/BMS complete candidates), COMP-QMF-DATA (rooms wrapped by QMB data commands), COMP-QMN (node-paper, unforked run_slice, never research-paper). No new component. No new contract id. No new dependency edge. Parents QMF AD-1..41, QMB B-1..15, QML QL-1..10, NODE TN-1..25, QMA AD-1..29, CONNECT AD-1..5 bind read-only. Local AD-1..AD-16 do not renumber parents. Dead list honored: DEC-0084/0085/0086 stay dead; DEC-0376 stays cut; QMA-paper does not exist; donor engines stay shapes-only. Implementation authorization arrives only through the factory pipeline."
    status: ratified
    rationale: "Operator-directed documentation-factory change-mode absorption of a status:final architecture spine (2026-09-14). The sitting itself was operator-absent with tagged assumptions; those assumptions are the cheap-veto surface (DEC-0287), not silent invention."
    sources: [EXT-2212, EXT-2200, EXT-2201, EXT-2205, EXT-2206]
    authority: rider
    component: COMP-QMB
    tags: [workbench, spine-adoption, preflight, reuse]
    date: 2026-09-14
    spine_ref: "SRC-17:ARCHITECTURE-SPINE.md"

  - id: DEC-0286
    title: "Contract wiring_status reconcile — source-inspected is not end-to-end demonstrated"
    statement: "On integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2, matching source exists for CT-32 (qmb/src/qmb/results), CT-33/CT-34 (qml/src/qml/declaration and confluence), CT-47 and CT-40..CT-51 (qma-core/qma-wire/qma-daemon packages), and qmf-risk value types for CT-22..CT-31. Contract YAML wiring_status defined-unwired plus the prose no code exists is stale documentation drift, not an architectural fork and not a second design. The reconciled stamp is source-inspected: matching packages exist at that SHA; class/test existence is not end-to-end demonstration. Remaining connect work includes replacing RecordingQmbDoorTransport with a real CLI transport, composing the asyncio daemon process (no asyncio.run/websockets/uvicorn under qma-daemon/qma-wire src), CLI coverage of robustness and sweep batch/rank, and analysis.project. Implementation authorization still arrives only through the factory pipeline."
    status: ratified
    rationale: "Operator instruction for this documentation-factory sitting: reconcile stale defined-unwired / no code exists stamps with integration source; source-inspected is not end-to-end demonstrated. Independently re-verified via git grep/ls-tree on the SHA without checkout."
    sources: [EXT-2202, EXT-2199, EXT-2212]
    authority: rider
    component: COMP-QMB
    tags: [workbench, wiring_status, source-inspected, ct-32, ct-33, ct-47]
    date: 2026-09-14
    spine_ref: "SRC-17:ARCHITECTURE-SPINE.md#consistency-conventions"

  - id: DEC-0287
    title: "Workbench cheap-veto register and unresolved holes"
    statement: "Cheap-veto assumptions, each individually overturnable without unwinding another call: (A1) Connect-wave (door + projections + named analysis + procedures/continuation config) is the coherent first implementation area; generation can trail without blocking Library or What-if. (A2) Work-environment roster stays UI-open (AD-16 aliases only). (A3) Generated layouts and reactions to them are not preference evidence. (A4) Optuna pin stays optuna==4.9.0 on integration despite upstream 5.0.0 (DEC-0168 stands; TPE default change is a contract-versioning event). (A5) No PRD rewrite this sitting — FR addenda for ExperimentSpec, analysis methods, generation-vs-search, and procedures are GAP-0061. Unresolved holes kept as gaps, never silent prose: GAP-0085 mechanism vocabulary (ownership ruled by DEC-0272; nouns open); GAP-0063 first generator algorithm; GAP-0062 concrete always-on host for DEC-0278; GAP-0061 PRD FR addenda."
    status: ratified
    rationale: "The architecture sitting was operator-absent Fast-path; tagged assumptions are the cheap-veto surface. Operator instruction for this documentation-factory sitting: keep those holes as gaps, never silent prose; do not rewrite the PRD; generated layouts are not preference evidence."
    sources: [EXT-2203, EXT-2204, EXT-2206, EXT-2209, EXT-2211]
    authority: rider
    component: COMP-QMB
    tags: [workbench, cheap-veto, assumptions, gaps]
    date: 2026-09-14
    spine_ref: "SRC-17:.memlog.md"
"""

GAPS = r"""
  - id: GAP-0061
    question: "When are the existing PRD functional-requirement addenda written for ExperimentSpec, named analysis methods, generation-vs-search, and reusable procedures?"
    needed_by: [COMP-QMB, COMP-QMA-CORE, COMP-QML]
    blocking: false
    recommendation: "Note the hole in this sitting; do not rewrite the PRD here. The workbench spine is the expansion contract until a later PRD update pass. Connect-wave epics may be written from the spine and FEAT-0033..0038 without waiting."
    status: deferred
    answer: null
    note: "Workbench Open questions 2026-09-14 (DEC-0287). PRD today covers QMB FRs (FR-036..046) and QML FRs; it does not yet state ExperimentSpec, analysis methods, generation-vs-search, or procedures. Operator instruction: note the hole; do not rewrite the PRD in this sitting."
    date: 2026-09-14
  - id: GAP-0062
    question: "What is the concrete always-on host for AD-10 laptop-off continuation — operator-named reachable ExecutionEnvironment, workstation-adjacent machine, or moving qma-daemon off the sleeping laptop?"
    needed_by: [COMP-QMA-DAEMON]
    blocking: false
    recommendation: "Keep AD-10's property (daemon or a reachable remote env must not live only on the sleeping laptop). Leave the machine as operator config under QMA AD-25/AD-26. Do not invent a host name in docs."
    status: deferred
    answer: null
    note: "Workbench Open questions 2026-09-14 (DEC-0278, DEC-0287). Property is decided; the machine is not. Revisit when the operator names a reachable ExecutionEnvironment or moves the daemon off the laptop."
    date: 2026-09-14
  - id: GAP-0063
    question: "What is the first structure-generator algorithm — placeholder-fill of CT-34 legs versus Python-logic synthesis?"
    needed_by: [COMP-QML]
    blocking: false
    recommendation: "Ownership is DEC-0272 (QML authors; QMB runs; QMA references). Do not start a generator inside QMB. Do not fill GAP-0085 mechanism nouns to dodge this choice. Revisit at a QML increment after connect-wave."
    status: deferred
    answer: null
    note: "Workbench Open questions 2026-09-14 (DEC-0272, DEC-0287). Distinct from GAP-0085 (typed mechanism vocabulary). Neither blocks connect-wave epics."
    date: 2026-09-14
"""

FEAT = r'''
  - id: FEAT-0033
    name: "Connect the QMA to QMB door, persist ExperimentSpec, compose the daemon; three lanes and paper trinity"
    scope: >-
      In: replace RecordingQmbDoorTransport with a real qmb CLI transport (MCP later);
      compose the long-running asyncio daemon process (loopback listener + sole sqlite
      writer + pack roster) from existing modules — connect, not a new COMP (DEC-0276);
      persist ExperimentSpec, the QMA Experiment Ledger, and ExperimentSpec CT-07
      successor edges through the daemon journal / sqlite writer (DEC-0276); stamp
      workbench_lane as door-derived metadata on the QMB ledger line (governed for
      every orchestrator spawn) and on the Experiment Ledger entry (coordinated when
      QMA placed it), never as a CT-32 field, never as QMF AD-12 evidence class, never
      as B-4 role (DEC-0270); keep ungoverned as values-only with L33 graduation a
      separate two-artifact registration act (DEC-0270); research-paper as QMB
      governed replay outside the node, node-paper unchanged, QMA-paper nonexistent
      (DEC-0275); notebooks import qmb/qml on a controlled-room host and a managed
      interpreter lifecycle is a QMA ExecutionEnvironment (DEC-0279); coordinated
      research continuity is ExperimentSpec fp1 with no Project or Workspace kind
      (DEC-0284). Out: a sixth application, a second backtest governor, import qmb
      from QMA, extending CT-32 or B-4, QMA-paper, UI/Penpot, PRD rewrite, naming
      the AD-10 host machine (GAP-0062). Done means the knowledge base forbids the
      recording transport being treated as a working integration, names the three
      doors, and gives implementing stories a cited contract and DEC; implementation
      authorization still arrives only through the factory pipeline.
    decisions: [DEC-0269, DEC-0270, DEC-0275, DEC-0276, DEC-0279, DEC-0284, DEC-0285, DEC-0286]
    components: [COMP-QMA-DAEMON, COMP-QMA-CORE, COMP-QMB]
    blocked_by:
      - id: FEAT-0044
        reason: "the QMB door, ExperimentSpec, JobHandle occupancy, and analysis-backtest plugin placement FEAT-0044 lands are the surface this connect increment completes rather than forks (DEC-0276, DEC-0316)"
      - id: FEAT-0042
        reason: "composing the asyncio daemon process and persisting ExperimentSpec through the sole sqlite writer requires the daemon substrate, journal, and store lifecycle FEAT-0042 lands (DEC-0276, DEC-0305)"
      - id: FEAT-0029
        reason: "the real CLI transport places one qmb run invocation per ExecutionEnvironment onto the QMB orchestrator, CT-32, and JSONL ledger FEAT-0029 lands (DEC-0276, DEC-0161)"
    size: multi-pass
    status: planned
    notes: "Absorbed from architecture-QMX-2026-09-14 (status final) by the 2026-09-14 documentation-factory change-mode pass (ADR-0022, DEC-0285). Preflight verdict: reuse COMP-QMA-DAEMON / COMP-QMA-CORE / COMP-QMB — no new component. Cheap-veto A1-A5 on DEC-0287. Implementation authorization factory-pipeline-only."
  - id: FEAT-0034
    name: "Library projections and candidate-set queries over existing fp1 kinds"
    scope: >-
      In: Shared Library as a projection over existing fp1 kinds owned by
      COMP-QMF-REGISTRY — CT-33 bot, CT-34 confluence, strategy-family, CT-22 Book,
      CT-27 BMS, CT-28 binding, CT-12 split, CT-10 observation, CT-32 result, CT-47
      ExperimentSpec (coordinated lane only) — queried via the QMB B-15 registry-read
      as-of port, the QMB ledger merge view, and the QMA Experiment Ledger (DEC-0271);
      candidate retain/filter/rank as a read-time view over QMB ledger lines, registry
      as-of sets including dev-zone candidates, and coordinated Experiment Ledger refs,
      never QMA staging, never a copied-row database (DEC-0282); sweep.rank is this
      view. Out: a new Library COMP, a STRATS-shaped second store, Graph Templates /
      Skills / Routines / JobHandles / saved views as registry kinds, a Project or
      Workspace kind (DEC-0284). Done means implementing stories can cite the kind
      list and the three query surfaces; implementation authorization still arrives
      only through the factory pipeline.
    decisions: [DEC-0271, DEC-0282, DEC-0284, DEC-0285]
    components: [COMP-QMF-REGISTRY, COMP-QMB, COMP-QMA-DAEMON]
    blocked_by:
      - id: FEAT-0007
        reason: "Library kinds are qmf-registry per-kind records FEAT-0007 lands; the projection does not mint a second store (DEC-0271)"
      - id: FEAT-0029
        reason: "the QMB ledger merge view and B-15 registry-read as-of port FEAT-0029 lands are two of the three query surfaces (DEC-0271, DEC-0165)"
      - id: FEAT-0045
        reason: "coordinated Experiment Ledger refs FEAT-0045 lands are the third query surface and must not be mixed with QMA staging (DEC-0282, DEC-0308)"
    size: multi-pass
    status: planned
    notes: "Connect-wave cluster. STRATS remains a KnowledgeSource corpus (QMA AD-19). Implementation authorization factory-pipeline-only."
  - id: FEAT-0035
    name: "Named analysis methods — projection saved view versus path-dependent rerun"
    scope: >-
      In: COMP-QMB library functions analysis.project and analysis.rerun with thin
      doors (DEC-0273); projection reads one cited CT-32 and its CT-29 stream and
      emits a saved view whose durable body is the canonical JSON {method:
      projection, source_ct32, source_ct29, predicate, as_of} with homes per lane
      (ungoverned return value; governed-without-QMA JSON sidecar in the source
      run-dir; coordinated daemon-persisted plus analysis.published); permitted
      predicates hours/days/session/max-trades/include-exclude; forbidden as
      projection any change to size, R, Book/BMS fragments, execution ports, or
      starting_capital; path-dependent analysis.rerun is a new QMB run whose
      canonical artifact is a new CT-32; compare_runs is readout only; Book/BMS
      variants are complete new fingerprinted CT-22/CT-27 documents in the registry
      dev zone plus a replay citing that fingerprint (DEC-0274); labels stay
      parent-shaped — do not extend CT-32 or B-4 (DEC-0283). Out: a new analysis
      COMP, a CT-32 sibling for a projection, synthetic portfolio combination (F07
      deferred), QMA reimplementing the filter, treating a filtered trade list as
      Book/BMS truth. Done means implementing stories can distinguish the two
      methods, the saved-view body, and the occupancy split (project is a query;
      rerun is a run); implementation authorization still arrives only through the
      factory pipeline.
    decisions: [DEC-0273, DEC-0274, DEC-0283, DEC-0285]
    components: [COMP-QMB, COMP-QMF-RISK]
    blocked_by:
      - id: FEAT-0029
        reason: "both methods are QMB library functions over the CT-32 producer, CT-29 stream, orchestrator spawn, and ledger metadata FEAT-0029 lands (DEC-0273, DEC-0163)"
      - id: FEAT-0027
        reason: "path-dependent Book/BMS variants are complete CT-22/CT-27 documents and CT-29 streams FEAT-0027 lands; QMA never fills unset money-path fields (DEC-0274, DEC-0143)"
    size: multi-pass
    status: planned
    notes: "Connect-wave cluster. F07 portfolio-combination search stays deferred. Implementation authorization factory-pipeline-only."
  - id: FEAT-0036
    name: "CLI and API coverage of robustness and sweep batch/rank; data commands wrap qmf-data"
    scope: >-
      In: wire existing QMB library rungs that integration already implements but
      the CLI does not yet expose — robustness ladder (walk-forward, trade-shuffle
      MC, candle MC, significance) and sweep batch/rank — through the same thin-door
      parity surface as backtest/optimize/data (DEC-0276, DEC-0281); keep those
      rungs as queries or runs per DEC-0276 occupancy (sweep.rank is a query;
      robustness scenario batches that spawn runs consume occupancy when placed
      through the CT-47 door); data download/verify/gap-check/catalog/generate stay
      QMB fronts over qmf-data; CSV/file import is a CT-15 adapter extend, not a
      new store; quality surfaces are read models over CT-13 data quality events
      and gap_check reports; derived datasets are new fingerprinted artifacts with
      a lineage edge, not Library kinds; vendor-style timezone clones that
      auto-update experiment inputs are refused; coordinated ExperimentSpec
      data_ref cites CT-12 split fingerprints (DEC-0281). Out: a QuantDataManager
      clone store, a new COMP, MCP door ship (stays post-CLI-v1), GAP-0048/0049
      threshold content. Done means CLI/API parity names the missing wiring as
      wiring, not missing function; implementation authorization still arrives
      only through the factory pipeline.
    decisions: [DEC-0281, DEC-0276, DEC-0285]
    components: [COMP-QMB, COMP-QMF-DATA]
    blocked_by:
      - id: FEAT-0029
        reason: "CLI/API parity extends the qmb door tree, orchestrator, robustness library, sweep library, and data fronts FEAT-0029 already lands; this feature is missing wiring, not a second library (DEC-0276, DEC-0166)"
    size: multi-pass
    status: planned
    notes: "Connect-wave cluster. Integration already has robustness/ as library-only and sweep.rank unpublished on CLI. Implementation authorization factory-pipeline-only."
  - id: FEAT-0037
    name: "Procedures as QMA Graph Templates placing QMB runs and queries through the door"
    scope: >-
      In: reusable procedures as QMA Graph Templates, Skills, and operator Routines
      whose run-steps place one qmb CLI/MCP invocation per ExecutionEnvironment
      through the CT-47 door and whose query-steps call analysis.project /
      compare_runs / sweep.rank / gap-check/verify/catalog/list without occupancy
      (DEC-0277); one Graph Template instantiation is one Mission; each door step
      that changes resolved-config is an ExperimentSpec successor via the existing
      CT-07 branches-from edge; composition stays non-linear; no compulsory wizard;
      daemon/plugins/workers never import qmb (DEC-0277). Out: a workflow engine
      inside QMB, SQ Custom Projects clone, a new edge kind, treating the procedure
      itself as an ExperimentSpec. Done means implementing stories can name the
      occupancy split per step; implementation authorization still arrives only
      through the factory pipeline.
    decisions: [DEC-0277, DEC-0276, DEC-0285]
    components: [COMP-QMA-DAEMON, COMP-QMA-CORE]
    blocked_by:
      - id: FEAT-0033
        reason: "procedure run-steps consume the real CLI door, occupancy, and ExperimentSpec successor persistence FEAT-0033 lands (DEC-0277, DEC-0276)"
      - id: FEAT-0046
        reason: "Graph Templates, Skills, and desk packs are contributed through the plugin loader and five desk packs FEAT-0046 lands (DEC-0277, DEC-0320)"
    size: multi-pass
    status: planned
    notes: "Connect-wave cluster. Implementation authorization factory-pipeline-only."
  - id: FEAT-0038
    name: "Continuation host configuration and extensibility rungs 1-3"
    scope: >-
      In: configure qma-daemon plus registered remote ExecutionEnvironments and the
      durable outbox so work that must survive workstation sleep is not owned by
      QMB process-per-run (DEC-0278); coordinated cancel is JobHandle.cancel only;
      closing a UI tab cancels nothing; bind extensibility rungs 1-3 — ui-editable
      config variables, ordinary Python logic + QMB ports/adapters, QMA plugins /
      skills / graph templates / desk packs (DEC-0280). Out: naming the concrete
      always-on host machine (GAP-0062 stays deferred); UI contribution SDK
      (GAP-0081); a Jupyter product inside QMB; a new COMP. Done means the
      knowledge base states the property and the three rungs with the host machine
      left as GAP-0062; implementation authorization still arrives only through
      the factory pipeline.
    decisions: [DEC-0278, DEC-0280, DEC-0285, DEC-0287]
    components: [COMP-QMA-DAEMON, COMP-QMA-WIRE]
    blocked_by:
      - id: FEAT-0042
        reason: "continuation is a daemon property over the substrate, scheduler, and outbox FEAT-0042 lands (DEC-0278, DEC-0328)"
      - id: FEAT-0041
        reason: "loopback listener posture, dial-out, and durable remote outbox ride the wire contract FEAT-0041 lands; composing the live listener process is connect on that contract (DEC-0278, DEC-0304)"
    size: multi-pass
    status: planned
    notes: "Connect-wave cluster. GAP-0062 (host machine) and GAP-0081 (rung 4) stay deferred. Implementation authorization factory-pipeline-only."
  - id: FEAT-0039
    name: "QML structure-generation authoring of new CT-33/CT-34 candidates"
    scope: >-
      In: if and when generation ships, QML authors new CT-33/CT-34 content and/or
      logic-source bytes; the QML/host composition root mints the CT-06 envelope;
      QMB runs the candidates; QMA StrategyHandle may only reference already-
      fingerprinted records and register dev-zone candidates with origin plus a
      CT-07 predecessor edge; QMA never assembles CT-33/CT-34 JSON and never mints
      mechanism nouns (DEC-0272). Out: a generator inside QMB; copying SQ
      RandomCondition as a schema; filling GAP-0085 mechanism nouns in this
      feature; choosing the generator algorithm (GAP-0063); no-code authoring.
      Done means ownership is documented and implementing stories cannot put
      generation in QMB or QMA; the algorithm and nouns stay gaps. Implementation
      authorization still arrives only through the factory pipeline.
    decisions: [DEC-0272, DEC-0285, DEC-0287]
    components: [COMP-QML, COMP-QMF-REGISTRY]
    blocked_by:
      - id: FEAT-0030
        reason: "generation authors CT-33/CT-34 and logic-source bytes through the QML authoring surface, runtime protocol, and host mint FEAT-0030 lands (DEC-0272, DEC-0173)"
      - id: FEAT-0007
        reason: "new candidates are qmf-registry records in the dev zone with CT-07 predecessor edges FEAT-0007 lands; QMA does not assemble the JSON (DEC-0272)"
    size: multi-pass
    status: planned
    notes: "Trails connect-wave (DEC-0287 A1). GAP-0085 nouns and GAP-0063 algorithm remain deferred and must not be filled in prose. Implementation authorization factory-pipeline-only."
'''


def main() -> None:
    append_if_missing(ROOT / "_docwork" / "manifest.yaml", "id: SRC-17", MANIFEST)
    append_if_missing(ROOT / "_docwork" / "extractions.yaml", "id: EXT-2183", EXTR)
    append_if_missing(ROOT / "_docwork" / "ledger.yaml", "id: DEC-0269", LEDGER)
    append_if_missing(ROOT / "_docwork" / "gaps.yaml", "id: GAP-0061", GAPS)
    append_if_missing(ROOT / "_docwork" / "feature_inventory.yaml", "id: FEAT-0033", FEAT)
    patch_gap_0085(ROOT / "_docwork" / "gaps.yaml")


if __name__ == "__main__":
    main()
