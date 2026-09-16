---
stepsCompleted: [1, 2, 3, 4]
validated: true
inputDocuments:
  - _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-14/CAPABILITY-EXPANSION.md
  - docs/decisions/ADR-0022-workbench-expansion.md
  - workroom/research/2026-09-14-workbench-docs-factory-handoff.md
  - _docwork/workbench-increment-brief.md
  - docs/scenarios/SCN-0015-three-experiment-lanes.md
  - docs/scenarios/SCN-0016-projection-vs-path-dependent.md
  - docs/components/qmb.md
  - docs/components/qml.md
  - docs/components/qma-daemon.md
  - docs/components/qma-core.md
  - docs/components/qma-wire.md
  - docs/components/qmf-registry.md
  - docs/components/qmf-risk.md
  - docs/components/qmf-data.md
  - docs/components/trading-node.md
  - docs/contracts/ct-32-performance-result.yaml
  - docs/contracts/ct-33-bot-definition.yaml
  - docs/contracts/ct-34-confluence.yaml
  - docs/contracts/ct-47-qma-experiment-spec.yaml
  - docs/gap-report.md
  - docs/glossary.md
  - docs/AGENTS.md
  - _docwork/feature_inventory.yaml (FEAT-0033..FEAT-0039; blockers FEAT-0007, FEAT-0027, FEAT-0029, FEAT-0030, FEAT-0041, FEAT-0042, FEAT-0044, FEAT-0045, FEAT-0046)
  - _docwork/ledger.yaml (DEC-0269..DEC-0287)
  - _docwork/gaps.yaml (GAP-0061, GAP-0062, GAP-0063; GAP-0085 updated in place)
  - _bmad-output/planning-artifacts/prds/prd-QMX-2026-08-21/prd.md (§5 G–H FR-036..FR-050; §7 out of scope; §8 NFRs; GAP-0061 — do not rewrite)
  - _bmad-output/planning-artifacts/epics.md (Epics 13–16, 18–23 only — extend, do not duplicate; Phase-1 1–12, node 24–30, and CONNECT 31 out of this increment)
  - _bmad-output/planning-artifacts/epics-QMA-2026-08-29.md (Epics 41.4, 42, 43.1/43.3, 45.1–45.8, 46.3/46.6/46.7, 48 — door/spec/ledger/procedure/continuation law; extend, do not duplicate)
  - _bmad-output/planning-artifacts/epics-CONNECT-2026-09-11.md (Epic 31 — no overlap; numbering reservation only)
  - integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2 (brownfield defects this increment forbids)
excludedDocuments:
  - _bmad-output/planning-artifacts/epics.md (must not be rewritten)
  - _bmad-output/planning-artifacts/epics-QMA-2026-08-29.md (must not be rewritten)
  - _bmad-output/planning-artifacts/epics-CONNECT-2026-09-11.md (must not be rewritten)
  - _bmad-output/planning-artifacts/prds/prd-QMX-2026-08-21/prd.md (must not be rewritten; GAP-0061)
  - _bmad-output/planning-artifacts/ux-designs/ux-QMX-2026-09-01/DESIGN.md (empty scaffold; README forbids using it as a contract)
  - _bmad-output/planning-artifacts/ux-designs/ux-QMX-2026-09-01/EXPERIENCE.md (empty scaffold; README forbids using it as a contract)
  - generated UI layouts / Penpot (DEC-0287 A3 — not preference evidence)
delegation: "operator 2026-09-14 — autonomous run; menus auto-continued; workbench increment only; operator authorized unbounded agents"
epicNumbering: "Epic 32–38 — reserved so WORKBENCH never collides with Phase-1 (1–23), trading-node (24–30), CONNECT (31), or QMA (40–48)"
baseInventory: "integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2 (git show, no checkout)"
feature: FEAT-0033..FEAT-0039
adr: ADR-0022
decisions: [DEC-0269, DEC-0270, DEC-0271, DEC-0272, DEC-0273, DEC-0274, DEC-0275, DEC-0276, DEC-0277, DEC-0278, DEC-0279, DEC-0280, DEC-0281, DEC-0282, DEC-0283, DEC-0284, DEC-0285, DEC-0286, DEC-0287]
---

# QMX - Epic Breakdown

## Overview

This document is the epic and story breakdown for the **QMX strategy-experimentation workbench** increment (FEAT-0033..FEAT-0039): connect and name what already exists so QMB, QML, QMA, QMF, and the trading node compose as one workbench — one fingerprint identity, three door-derived experiment lanes, two named analysis methods — without minting a sixth application.

It decomposes the ratified workbench corpus — architecture-QMX-2026-09-14 AD-1..AD-16, ADR-0022, DEC-0269..DEC-0287, SCN-0015/SCN-0016, and the brownfield connect defects at `integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` — into implementable stories for the factory lanes.

The Phase-1 file (`epics.md`, Epics 1–23 and trading-node Epics 24–30) stays untouched and is not superseded. CONNECT (`epics-CONNECT-2026-09-11.md`, Epic 31) stays untouched. QMA (`epics-QMA-2026-08-29.md`, Epics 40–48) stays untouched. **Epic numbering starts at Epic 32**, a reserved block so WORKBENCH never collides with those files.

Requirement prefixes carry the W marker because these requirements derive from the **ratified workbench docs corpus and child spine, not from a PRD rewrite**. PRD §5 G–H (FR-036..FR-050) and QMA FR-Q54/FR-Q55 bind read-only as the substrate this increment extends. GAP-0061 (PRD FR addenda) stays deferred; this sitting does not rewrite the PRD (DEC-0287 A5). Rules carried forward from `epics.md`: each FR's cited artifact is the epic boundary and the source of its acceptance criteria; FR granularity is deliberately coarser than story granularity — never size a lane by counting FRs.

This increment **extends** QMB Epics 13–16 and 18–23 and QMA Epics 42, 43, 45, 46, and 48. It does not duplicate completed stories. Story 16.1 remains the thin `qmb` CLI; Story 45.8 remains the QMB-door **law** (one job per environment, no import edge); Story 45.7 remains ExperimentSpec identity; Story 46.3 remains the Experiment Ledger; Story 22.* remains the robustness **library**. WORKBENCH stories **close** the recording-transport, missing-daemon-process, missing-CLI-wiring, and unnamed-analysis gaps those stories left open and **forbid** treating `RecordingQmbDoorTransport` as a working integration, treating `source-inspected` as e2e, or extending CT-32 / B-4 with `lane` / `analysis_method`.

Preflight verdict (ADR-0022): **reuse** COMP-QMB, COMP-QML, COMP-QMA-CORE, COMP-QMA-WIRE, COMP-QMA-DAEMON, COMP-QMF-REGISTRY, COMP-QMF-RISK, COMP-QMF-DATA, COMP-QMN. No new component, no new contract id, no new store, no sixth application. Ratification fixes the architecture only. Nothing in this document grants implementation, credential, order, paper-mode, promotion, live-money or destructive authority; that arrives only through the factory pipeline (ADR-0022; DEC-0285).

## Requirements Inventory

### Functional Requirements

**A. Composition and authority (DEC-0269 / DEC-0285 / workbench AD-1)**

- FR-W01: Every new capability in this increment names an existing `COMP-*` owner or an explicit connect/extend of one. No sixth application package, no `COMP-EXP`, no HTTP experiment service, and no permanent experiment daemon besides `qma-daemon` is minted. Inherited stores stand: `qmf-registry`, `qmf-data` rooms, QMB JSONL run ledger, QMA daemon sqlite (journal, Experiment Ledger). A new store beside those is a spine amendment. DEC-0084 stays dead. (ADR-0022; AD-1; DEC-0269; DEC-0285)

- FR-W02: Implementation, credentials, a live session, order submission, paper-mode transition, promotion, and go-live remain factory-pipeline-only. `source-inspected` on `integration@1b451a8` means matching source exists; class/test existence is not end-to-end demonstration. Contract YAML `defined-unwired` plus “no code exists” is stale documentation drift where matching packages exist — reconcile, do not invent a second design. (DEC-0285; DEC-0286)

**B. Three door-derived lanes (DEC-0270 / SCN-0015 / FEAT-0033)**

- FR-W03: Exactly three experiment lanes exist, selected by **which door is called**, never by a flag on a payload. (1) **ungoverned** — `qmb.run()` / ordinary Python / `import qml` on a controlled-room host. (2) **governed** — QMB orchestrator spawn not placed by the CT-47 door (`spawn_governed`, including path-dependent `analysis.rerun`). (3) **coordinated** — QMA Backtesting Service places at most one `qmb` CLI/MCP **run** invocation per ExecutionEnvironment and never `import qmb`. A fourth call path is a spine amendment. A caller-declared `lane` / `workbench_lane` / `analysis_method` on the payload, on CT-32, or on a B-4 role is refused. (SCN-0015; AD-2; DEC-0270)

- FR-W04: Ungoverned returns library values only. It writes no QMB ledger line, no CT-32 **registry record**, and no ExperimentSpec / Experiment Ledger entry. A returned CT-32-shaped value, if any, is not a Library object and is not governed evidence. L33 graduation (ungoverned Python → governed evidence) is a separate two-artifact registration act, not this spawn. (SCN-0015; DEC-0270)

- FR-W05: Governed writes exactly one WriterId-scoped QMB ledger line carrying metadata `workbench_lane = governed` and one CT-32. It is **research-paper**: QMB governed replay (`world = replay`) outside the trading node. It is not an ExperimentSpec and creates no Experiment Ledger entry unless a later act places the same work through CT-47. (SCN-0015; DEC-0270; DEC-0275)

- FR-W06: Coordinated requires a registered ExperimentSpec (CT-47). The spawned run still writes one QMB ledger line with metadata `workbench_lane = governed` and one CT-32 — that is the evidence, reached by `_ref`; QMA does not copy or merge it. The Experiment Ledger entry carries `workbench_lane = coordinated`. The two labels live on two objects and must not be collapsed. (SCN-0015; DEC-0270; DEC-0276)

- FR-W07: `workbench_lane` is derived from the door and recorded only as workbench metadata on the QMB ledger line and/or the Experiment Ledger entry. It is not QMF AD-12 evidence class, not B-4 `role`, and not a CT-32 field. Extending CT-32 or B-4 with such a field is a spine amendment, not a connect fix. (SCN-0015; DEC-0270; DEC-0283)

**C. The QMA→QMB door is connect (DEC-0276 / FEAT-0033)**

- FR-W08: Keep the route Agent → QMA backtest tool → Backtesting Service (`analysis-backtest` plugin daemon half: one Tool Registry entry plus the single `qmb` door, holding no scheduling authority, no parallelism and no state of its own) → `qmb` CLI (MCP later) → QMB. Replace `RecordingQmbDoorTransport` with a real CLI transport that places the coordinated-lane `qmb` process. Treating the recording transport as a working integration is forbidden. Story 45.8 remains the door **law**; this increment closes the transport. (qma-daemon.md; AD-8; DEC-0276; DEC-0286; FR-Q55)

- FR-W09: Compose the long-running asyncio daemon process — loopback listener + sole sqlite writer + pack roster — from the existing `qma-daemon` / `qma-wire` modules. That composition is connect, not a new COMP. No composed listener process was found under those packages' `src/` at `integration@1b451a8`. (qma-daemon.md; qma-wire.md; DEC-0276; DEC-0269)

- FR-W10: Persist ExperimentSpec records, the QMA Experiment Ledger, and ExperimentSpec CT-07 successor (`branches-from`) edges through the daemon journal / sole sqlite writer. The QMB run ledger remains QMB JSONL, reached by `_ref`, never copied, never merged. QMB does not write ExperimentSpec edges. Story 45.7 remains ExperimentSpec identity; this increment makes persistence durable rather than in-memory maps. (qma-daemon.md; DEC-0276; DEC-0308; FR-Q54)

- FR-W11: Occupancy is one `qmb` CLI/MCP **run** invocation per ExecutionEnvironment — backtest, optimize, sweep, robustness, `analysis.rerun`, and data download that mutates rooms. QMB's process-per-run children inside that invocation are not additional QMA jobs. Queries do not consume occupancy, mint no CT-32, and mint no ExperimentSpec successor: `analysis.project`, `compare_runs`, `sweep.rank`, ledger reads, and `data.gap-check|verify|catalog|list`. (qmb.md; qma-daemon.md; DEC-0276)

- FR-W12: The daemon, every plugin, and every QMA worker image never `import qmb`. In-process library calls from QMA are a spine amendment. QMB and QML keep the `qmf-venue` ban. (DEC-0276; DEC-0277; DEC-0348)

**D. Paper trinity, notebooks, research identity (DEC-0275 / DEC-0279 / DEC-0284 / FEAT-0033)**

- FR-W13: Exactly three paper nouns, never collapsed. **research-paper** = QMB governed replay (`world=replay`, Book/BMS fragments in the run-config) outside the node, before promotion. **node-paper** = Book-level demo routing + soak (`role=demo`, `world=live`); no per-bot paper lane (DEC-0261). **QMA-paper** does not exist — no execution tool at any account role. QuantConnect paper-brokerage is not a QMX lane. Bare “paper” is forbidden for these meanings. (AD-7; DEC-0275; DEC-0341)

- FR-W14: QMB may append WriterId-scoped fragments to the B-15 hub inbox; sandbox-provenance fragments stay refused at publish and pull; `hub_publish` is human; QMA never writes the hub (candidate refs only). Promotion remains a human act outside QMA onto the node. (DEC-0275; TN-20)

- FR-W15: Exploratory notebooks `import qmb` / `import qml` on a controlled-room host (B-9). A managed interpreter lifecycle, if product-owned, is a QMA ExecutionEnvironment (Analysis RLM kernel or a declared env kind). It is not a QMB module and not a new COMP. Jupyter is not a pinned product this sitting. (AD-11; DEC-0279)

- FR-W16: There is no Project kind and no Workspace kind. Coordinated research continuity is the ExperimentSpec `fp1` (`code_ref` when code changes, `resolved_config_ref` for parameter/config, `data_ref` = CT-12 split, `environment_ref`). QMB “workspace defaults” are a config-compiler layer (B-3), never an identity. A notebook file is an ungoverned working surface until an orchestrator spawn or a CT-47 placement; it joins the undertaking only as `code_ref` or as an ExecutionEnvironment session. Display names “project” / “workspace” are UX aliases over ExperimentSpec (coordinated) or over a bot `fp1` (governed). UI tabs may group those aliases; they must not mint a record. (AD-16; DEC-0284)

**E. Library projections and candidate-set queries (DEC-0271 / DEC-0282 / FEAT-0034)**

- FR-W17: Library has no new COMP. Kind owner is COMP-QMF-REGISTRY. Shared Library objects are exactly these existing kinds, cited by `fp1`: CT-33 bot, CT-34 confluence, strategy-family, CT-22 Book, CT-27 BMS, CT-28 binding, CT-12 split, CT-10 observation, CT-32 result, CT-47 ExperimentSpec (coordinated lane only). Logic source-manifests are cited from CT-33, not a separate Library kind. (AD-3; DEC-0271)

- FR-W18: Not Library objects: QMA staging / RefinementProposals, JobHandles, Graph Templates, Skills, Routines, saved views, analysis publications, derived datasets. STRATS is a KnowledgeSource corpus (QMA AD-19) and does not write registry kinds. Work-environment tabs and display aliases are UX over fingerprints. (DEC-0271; DEC-0284)

- FR-W19: Query surfaces are exactly three: the QMB B-15 registry-read as-of port, the QMB ledger merge view, and the QMA Experiment Ledger. Library search returns saved views and analysis publications only as query hits citing the source kind’s `fp1`, never as registry kinds. (DEC-0271)

- FR-W20: A candidate set is a read-time view over (1) QMB ledger lines, (2) registry as-of sets including `dev`-zone candidates of Library kinds, (3) coordinated Experiment Ledger refs. It does **not** read QMA staging. `sweep.rank` is this view and publishes no copied-row artifact. A saved view’s home follows FR-W24. Not `qmf-registry`, not a new sqlite table, not a citation without a body. (AD-14; DEC-0282)

**F. Named analysis methods (DEC-0273 / DEC-0274 / DEC-0283 / SCN-0016 / FEAT-0035)**

- FR-W21: Exactly two named analysis methods exist as COMP-QMB library functions with thin doors (B-1). `analysis.project` reads one cited CT-32 and its CT-29 stream and returns a **saved view**, not a CT-32. `analysis.rerun` is a new QMB run through the tunnel whose canonical artifact is a new CT-32. Combining two bots’ equity/trade streams into a synthetic portfolio is neither method — refused here; F07 stays deferred. (SCN-0016; AD-5; DEC-0273)

- FR-W22: The durable body of a projection **is** the canonical JSON `{method: projection, source_ct32, source_ct29, predicate, as_of}`. A citation without that body is not a saved view. `as_of` is the source CT-32’s `registry_as_of` / occurrence, never query time. Identity `fp1` is of that JSON. Never a copied trade list or rescaled measure set. Claim-class is always `projection`; never admission evidence. (SCN-0016; DEC-0273)

- FR-W23: Permitted projection predicates: hours/days/session windows, max-trades caps, include/exclude filters. Forbidden as projection: any change to size, R, Book/BMS fragments, execution ports, or `starting_capital`. Those changes are path-dependent and require `analysis.rerun`. (SCN-0016 Branch A; DEC-0273)

- FR-W24: Projection homes: **ungoverned** — return value only, not durable, not a Library object; **governed-without-QMA** — JSON sidecar in the **source** run-dir (not a new orchestrator spawn, not a QMB ledger line, not a CT-32); **coordinated** — the QMA daemon (Agent holding `dispatch_lease`) persists the JSON and an `analysis.published` Experiment Ledger entry citing that `fp1`. QMB never opens daemon sqlite. Coordinated call = daemon shells the CLI as a query, waits, persists refs. `analysis.project` is not a run: no CT-32, no QMB ledger line, no ExperimentSpec successor, no occupancy. (DEC-0273; DEC-0276)

- FR-W25: `analysis.rerun` is a new QMB run with a new resolved run-config (Book/BMS fragments, fill/cost/financing ports, `starting_capital`). A `starting_capital` override stamps `seed_overridden` on the binding and forces the B-4 fold `unrated` (B-3). Occupancy applies as a governed or coordinated run. `analysis_method` and `lane` are not CT-32 fields; they live on the QMB ledger line (governed) and/or the Experiment Ledger entry (coordinated) as metadata citing the CT-32 by `_ref`. (DEC-0273; DEC-0160)

- FR-W26: `compare_runs` is a readout of cited CT-32 fields, not an analysis method and not a new artifact; it stamps nothing. F08 that only overlays two existing series uses `compare_runs`; F08 that changes sizing/Book/seed is path-dependent. QMA queries may call `analysis.project` / `analysis.rerun` and persist refs; they may not reimplement the filter. (DEC-0273)

- FR-W27: A proposed Book/BMS version is a **complete** new fingerprinted CT-22/CT-27 document in the registry `dev` zone (not a patch record). Path-dependent evaluation is a QMB governed or coordinated replay citing that fingerprint. QMA may emit it only as a `money_path_relevant` candidate whose `approval_request` carries the field-level diff against the predecessor; QMA never fills an unset money-path field. Shape owner remains QMF Risk; mint remains the composition-root pattern. Trade-list rescaling is never Book simulation. (SCN-0016; AD-6; DEC-0274)

- FR-W28: Do not extend CT-32 or B-4. Mapping is total. Governed/coordinated confirmation run: B-4 `role=confirmation`; no AD-15 claim-class (it is not an analysis). Optimize trial / sweep combo: `role=trial`. MC / WF replicate: `role=replicate` plus B-7 procedure label `robustness` or `infra-stress`. Aborted: `role=aborted`. Projection saved view: no B-4 role (not a run); claim-class `projection`; inherit source world; never `confirmed`. Path-dependent re-run: B-4 role of **that** run; may be published as analysis only as an Experiment Ledger `analysis.published` entry citing the new CT-32; still not admission evidence unless `role=confirmation`. Confirmation evidence remains B-4 `role=confirmation` only. L20 stands. Replay-world verdicts still cannot gate live money. (AD-15; DEC-0283)

**G. CLI/API coverage and data wrap (DEC-0281 / DEC-0276 / FEAT-0036)**

- FR-W29: Wire existing QMB library rungs that `integration@1b451a8` already implements but the CLI does not yet expose — robustness ladder (walk-forward, trade-shuffle MC, candle MC, significance) and sweep `batch`/`rank` — through the same thin-door parity surface as backtest/optimize/data. This is missing wiring, not a second library. MCP door ship stays post-CLI-v1 (Story 16.6). GAP-0048/0049 threshold content stays deferred. (qmb.md; AD-13; DEC-0281; DEC-0286)

- FR-W30: Acquire / verify / gap-check / catalog / generate remain QMB data commands wrapping qmf-data (B-11). CSV/file import is a CT-15 adapter (extend ingest), not a new store. Spike/OHLC quality detectors, if added, extend QMB `data` over existing observations — they are not AD-5 analysis views and not a new COMP. Quality surfaces are read models over CT-13 `data quality` events and `gap_check` reports. (DEC-0281)

- FR-W31: A derived dataset is a new fingerprinted artifact with a lineage edge; it is not a Library kind. Vendor-style timezone clones that auto-update the source under an experiment’s feet are refused. Only a coordinated ExperimentSpec exists (FR-W03); its `data_ref` must cite CT-12 split fingerprints (B-8). Governed runs cite splits on the resolved run-config, not via ExperimentSpec. Ungoverned calls mint neither. (DEC-0281; DEC-0271)

**H. Procedures as Graph Templates (DEC-0277 / FEAT-0037)**

- FR-W32: Reusable procedures are QMA Graph Templates, Skills, and operator Routines. QMB does not grow a task graph. There is no compulsory research→backtest→paper wizard. SQ Custom Projects remain a donor shape, not a clone. Stories 43.3 and 46.6 remain Graph Template / Routine **law**; this increment uses them as the Custom-Project equivalent. (AD-9; DEC-0277)

- FR-W33: A step that names a QMB **run** (backtest, optimize, sweep, robustness, `analysis.rerun`, mutating data download) is placed through the CT-47 `qmb` door as one CLI/MCP run invocation (occupancy, FR-W11). A step that names a QMB **query** (`analysis.project`, `compare_runs`, `sweep.rank`, gap-check/verify/catalog/list) is a door query: no occupancy, no CT-32, no spec successor. One Graph Template instantiation is one Mission. (DEC-0277)

- FR-W34: Each door step that changes resolved-config is an ExperimentSpec successor (`create_successor` + the existing ExperimentSpec CT-07 `branches-from` edge — not bot `supersedes`, not a new edge kind). The procedure itself is not an ExperimentSpec. Composition stays non-linear: any step may be the first door placement. (DEC-0277)

**I. Continuation and extensibility (DEC-0278 / DEC-0280 / FEAT-0038)**

- FR-W35: Work that must survive workstation sleep is owned by `qma-daemon` plus registered remote ExecutionEnvironments and the durable outbox. If laptop-off is promised, the daemon or a reachable remote env must not live only on the sleeping laptop. QMB orchestrator lifetime is the job. The concrete always-on host machine remains GAP-0062 — stories configure the property and must not invent a host name. (AD-10; DEC-0278; DEC-0287)

- FR-W36: Coordinated cancel authority is `JobHandle.cancel` only; the door maps it to QMB abort and the QMB ledger writes `aborted`. Governed-without-QMA cancel is QMB abort only. Ungoverned cancel is process death and writes nothing. Closing a UI tab cancels nothing. No other writer may set a terminal JobHandle or ledger state. (DEC-0278; DEC-0304; Story 14.6 / 15.3 / 45.4)

- FR-W37: Extensibility is four rungs, in order: (1) ui-editable config variables on templates; (2) ordinary Python logic + QMB ports/adapters; (3) QMA plugins, skills, graph templates, desk packs; (4) UI contribution SDK. Rungs 1–3 bind now. Rung 4 stays GAP-0081 deferred. No-code authoring is not promised. QMA “plugin” vocabulary stays QMA-scoped (DEC-0346). (AD-12; DEC-0280)

**J. Generation is not search (DEC-0272 / FEAT-0039)**

- FR-W38: **Search** varies declared CT-33 parameters (QMB optimize/sweep, B-8) and writes trial ledger lines citing the **same** bot `fp1`. **Generation**, if built, authors new CT-33/CT-34 content and/or logic-source **bytes via QML**. The QML/host composition root mints the CT-06 envelope. A generator living inside QMB is refused. TPE parameter search must not be sold as strategy generation. (AD-4; DEC-0272)

- FR-W39: QMA `StrategyHandle` may only (1) reference an already-fingerprinted registry record and (2) register those bytes as a `dev`-zone candidate with a QMA `origin` field and a CT-07 predecessor edge. QMA never assembles CT-33/CT-34 JSON, never mints mechanism nouns, never fills RandomCondition slots. On `integration@1b451a8`, `GAP_0085_STRATEGY_MECHANISMS` is already refused in `qma/core/ports/experiments.py`. (DEC-0272; DEC-0313; FR-Q53)

- FR-W40: GAP-0085 typed Entry/Exit/Filter/Session vocabulary remains deferred; write-ownership is QML/host, not QMA. GAP-0063 first generator algorithm (placeholder-fill of CT-34 legs vs Python-logic synthesis) remains unruled. Neither may be filled in prose. SQ RandomCondition templates are a donor shape, not a schema to copy. No-code authoring is not promised. Generation trails connect-wave (DEC-0287 A1). (DEC-0272; DEC-0287)

### NonFunctional Requirements

Workbench inherits NFR-01..NFR-11 from `epics.md` / PRD §8 unchanged (environment, quality gates, determinism, measure-then-budget, secrets-as-references, append-only durability, L38 configurability, auditability, concurrency posture, one-person operability, failure-register). Node-local NFR-12..NFR-22 do not bind this increment except where a workbench story would otherwise touch the trading node (it must not). Increment-local NFRs:

- NFR-W01: CPython 3.14; Optuna pin stays `optuna==4.9.0` on the QMB sampler adapter (DEC-0168; DEC-0287 A4). Upstream 5.0.0 is not adopted — a TPE default change is a contract-versioning event. No new framework is added. (architecture-QMX-2026-09-14 Stack)

- NFR-W02: Typed refusals (CT-04) at every public workbench boundary; doors render, never swallow. A caller-declared lane flag, a forbidden projection axis, an `import qmb` from QMA, a Project/Workspace mint, and a QMA execution tool each refuse with a named variant rather than failing open. (AD Consistency Conventions; NFR-11)

- NFR-W03: Static import gate — `qma-daemon`, every QMA plugin, and every QMA worker image never import `qmb`; `qmb`/`qml` never import `qmf-venue`. This is a tier-1 check, same posture as the L30/`qmn.venue`-only venue gate. (DEC-0276; DEC-0348; AR-73 inherited)

- NFR-W04: QMA sqlite remains a single-writer-thread store. QMB JSONL remains WriterId-scoped. The two stores are never merged. Experiment Ledger cites QMB evidence by `_ref` only. (DEC-0276; DEC-0305; NFR-06)

- NFR-W05: Acceptance tests that claim the QMA→QMB door works must actually spawn `qmb` (or a documented test double that is not `RecordingQmbDoorTransport` presented as production). `source-inspected` is not a substitute for an e2e walk. (DEC-0286; NFR-03)

- NFR-W06: Cheap-veto A1–A5 on DEC-0287 stand: A1 connect-wave first / generation trails; A2 work-environment roster UI-open; A3 generated layouts are not preference evidence; A4 Optuna pin stays `4.9.0`; A5 no PRD rewrite (GAP-0061). A factory worker may not overturn them.

- NFR-W07: Public formats stay the existing CT-32 / CT-33 / CT-34 / CT-47 / CT-40..CT-51 shapes. No new contract id. No `lane` / `analysis_method` field on CT-32 or B-4. Wiring stamp may move to `source-inspected`; remaining connect work is named, not a second schema. (DEC-0283; DEC-0286; NFR-19 posture)

### Additional Requirements

- AR-W01: Code is specified against the read-only brownfield at `integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` via `git show` (no checkout of `integration`). Defects this spine forbids, not seed to copy: (1) `RecordingQmbDoorTransport` is the default and records without spawning `qmb`; (2) no composed asyncio listener process under `qma-daemon`/`qma-wire` `src/`; (3) robustness remains library-only on the CLI; (4) full sweep `batch`/`rank` CLI coverage is missing; (5) `analysis.project` is not a library function yet. (ADR-0022; DEC-0286)

- AR-W02: No starter template. No new distribution. Structural seed is inherited: `qmb/` (runloop, config, orchestrator, doors/{cli,api,mcp}, data, optimize, robustness, results, ledger), `qml/` (declaration, protocol, conformance), `qma-core|daemon|wire`, `qmf-*`, `qmn`. Connect work composes existing modules; it does not mint a package. (ARCHITECTURE-SPINE Structural Seed)

- AR-W03: Factory touch ownership — exclusive writable surfaces, serialize wave-mates that share a component:

  | FEAT | Wave (inventory 2026-09-14) | Blocked by | Serialize with |
  |---|---|---|---|
  | FEAT-0038 continuation + rungs 1–3 | 11 | FEAT-0042, FEAT-0041, FEAT-0027 | FEAT-0043 (both COMP-QMA-DAEMON) |
  | FEAT-0039 QML generation authoring | 12 | FEAT-0030, FEAT-0007 | trails connect-wave by DEC-0287 A1 |
  | FEAT-0034 Library projections | 14 | FEAT-0007, FEAT-0029, FEAT-0045 | FEAT-0035/0036 (COMP-QMB) |
  | FEAT-0035 named analysis methods | 14 | FEAT-0029, FEAT-0027 | FEAT-0034/0036 |
  | FEAT-0036 CLI robustness/sweep + data wrap | 14 | FEAT-0029 | FEAT-0034/0035 |
  | FEAT-0033 QMA→QMB door + daemon compose + three lanes | 15 | FEAT-0044, FEAT-0042, FEAT-0029 | FEAT-0046 (COMP-QMA-CORE/DAEMON); delivers for FEAT-0037 |
  | FEAT-0037 procedures as Graph Templates | 16 | FEAT-0033, FEAT-0046 | after the door |

  `--next` still prints FEAT-0001: the workbench slices sit on top of the existing planned inventory. Do not start FEAT-0033 before its blockers ship.

- AR-W04: Stories 13.*–16.*, 18.*–23.* in `epics.md` and Stories 41.4, 42.*, 43.1, 43.3, 45.1–45.8, 46.3, 46.6, 46.7, 48.* in `epics-QMA-2026-08-29.md` remain the substrate. WORKBENCH stories cite them; they do not re-implement the run loop, config compiler, orchestrator, CT-32 producer, robustness library, sweep Cartesian, Optuna TPE, data download/verify/gap-check, ExperimentSpec identity, JobHandle state machine, Graph Template compiler, plugin loader, or money-path deny-list.

- AR-W05: Dead list honored: DEC-0084 (central backtest service), DEC-0085/0086 (donor engines), DEC-0376 (git-branch-per-parameter), QMA-paper, `.qml` DSL, complexity gate, paper twins, QuantConnect paper-brokerage as a QMX lane, a generator inside QMB, `import qmb` from QMA, Project/Workspace kinds, extending CT-32 or B-4. (ADR-0022; DEC-0285)

- AR-W06: Out of this increment (Deferred table / GAP rows): GAP-0061 PRD FR addenda rewrite; GAP-0062 concrete always-on host machine; GAP-0063 generator algorithm; GAP-0085 mechanism nouns; GAP-0081 UI contribution SDK / `qma-ui-contract`; GAP-0048/0049 taxonomy and thresholds; F07 synthetic portfolios; MCP door ship; Jupyter as a pinned product; screen composition / departments / chrome; UI/Penpot; filling any of those in prose. (architecture-QMX-2026-09-14 Deferred; DEC-0287)

- AR-W07: SCN-0015 (three door-derived lanes) and SCN-0016 (projection vs path-dependent) bind as golden scenarios. A story that cannot demonstrate the Then branches, or that implements a Failure branch as a feature, is incomplete. (SCN-0015; SCN-0016)

- AR-W08: Vocabulary law: QMB is a library+CLI, never an engine/kernel. Bare “paper”, “calendar”, “kernel”, “plugin” (outside QMA), and “snapshot” (for registry state) stay banned. Say research-paper / node-paper; market-hours / day-boundary / news calendar; RLM kernel; as-of set. Cite Book, BMS, bot, split, result, ExperimentSpec by `fp1`. Display names and `name@version` are UX only. (ARCHITECTURE-SPINE Consistency Conventions)

- AR-W09: Local `AD-1`..`AD-16` are this sitting’s ids and do not renumber QMF `AD-*`, QMA `AD-*`, or CONNECT `AD-*`. Cite parents by `QMF AD-n` / `QMA AD-n` / `B-n` / `QL-n` / `TN-n` / `CONNECT AD-n`. (DEC-0285)

- AR-W10: Each implementing spec must state, in its own prose: what must already exist (blockers with reasons), what this feature delivers that others wait on, what may run alongside (wave-mates). (workbench-docs-factory-handoff)

### UX Design Requirements

The bmad-ux spine pair `ux-QMX-2026-09-01/DESIGN.md` + `EXPERIENCE.md` exists as a folder but both files are empty scaffolds (`status: in-progress`, `updated: 2026-09-01`). The folder README forbids using them as implementation contracts. This increment has no UI, Penpot, or desktop-chrome work (DEC-0287 A3; CAPABILITY-EXPANSION §4). UX-DRs below are the **backend-binding objects** from CAPABILITY-EXPANSION §5 so later UI can bind without a department roster. Layout, chrome, and generated-layout reactions are deferred and are not preference evidence.

- UX-DR1: Library/`fp1` identities exposed to any later UI are exactly: Bot definition, Book, BMS, binding, split, observation window, CT-32 result, ExperimentSpec (coordinated only). Logic source-manifests ride CT-33. (CAPABILITY-EXPANSION §5; FR-W17)

- UX-DR2: Graph Templates, Skills, Routines, saved views, and JobHandles are not Library kinds and must not be presented as registry records. (CAPABILITY-EXPANSION §5; FR-W18)

- UX-DR3: Operations a later UI/agent binds to: `run` (ungoverned); `spawn_governed`; `optimize.ask/tell`; `sweep`; robustness rungs; `data.download|verify|gap-check|catalog`; `analysis.project`; `analysis.rerun`; `procedure.start`; `experiment.register`; `candidate.admit`; `promotion` (human, outside QMA). Lane is selected by which of `run` / `spawn_governed` / the QMA backtest tool is called, never by a payload flag. (CAPABILITY-EXPANSION §5; FR-W03)

- UX-DR4: Queries a later UI/agent binds to: Library search by kind+`fp1`; candidate-set view; ledger merge; gap/quality projection; as-of registry. (CAPABILITY-EXPANSION §5; FR-W19; FR-W20)

- UX-DR5: Job states come from the QMB orchestrator and QMA JobHandle (`unknown` included). Tab-close ≠ cancel. Laptop-sleep ≠ abort if the AD-10 host is up. (CAPABILITY-EXPANSION §5; FR-W36)

- UX-DR6: Events a later UI binds to: CT-13 journal types; QMA wire events; progress/failure on JobHandle. (CAPABILITY-EXPANSION §5)

- UX-DR7: Extension points visible to a non-source user: ui-editable variables; drop-in Python logic package; install a QMA desk pack. Not: UI widgets (GAP-0081). (CAPABILITY-EXPANSION §5; FR-W37)

- UX-DR8: Display names “project” / “workspace” are aliases over ExperimentSpec (coordinated) or bot `fp1` (governed). Tabs may group aliases; they must not mint a Project or Workspace record. (AD-16; DEC-0284; FR-W16)

Deferred chrome (must not appear as stories): Penpot / generated layouts; department roster as UI; floating far-left world menu; durable top-tab layout; Hermes/Codex/Fincept interior composition; universal chat-centre; UI contribution SDK; compulsory research→backtest wizard.

### FR Coverage Map

- FR-W01: Epic 36 — no sixth application; reuse existing COMP-* (all epics inherit)
- FR-W02: Epic 36 — factory-pipeline-only; source-inspected ≠ e2e (all epics inherit)
- FR-W03: Epic 36 — three door-derived lanes; no payload flag
- FR-W04: Epic 36 — ungoverned returns values only; L33 ≠ this spawn
- FR-W05: Epic 36 — governed = one ledger line + one CT-32 = research-paper
- FR-W06: Epic 36 — coordinated dual labels; evidence by `_ref`
- FR-W07: Epic 36 — `workbench_lane` is metadata, not CT-32 / B-4 / AD-12
- FR-W08: Epic 36 — replace RecordingQmbDoorTransport; keep Story 45.8 law
- FR-W09: Epic 36 — compose asyncio daemon from existing modules
- FR-W10: Epic 36 — persist ExperimentSpec / Experiment Ledger / CT-07 successors
- FR-W11: Epic 36 — occupancy = one run invocation; queries exempt (Epics 33/35/37 consume the split)
- FR-W12: Epic 36 — never `import qmb` from QMA (Epic 37 repeats the gate)
- FR-W13: Epic 36 — paper trinity; QMA-paper does not exist
- FR-W14: Epic 36 — hub inbox / human hub_publish; QMA never writes the hub
- FR-W15: Epic 36 — notebooks import the library; managed interpreter = ExecutionEnvironment
- FR-W16: Epic 36 — no Project/Workspace kind; ExperimentSpec `fp1` is continuity
- FR-W17: Epic 34 — Library kinds are the existing fp1 list
- FR-W18: Epic 34 — not-Library kinds (staging, JobHandles, saved views, …)
- FR-W19: Epic 34 — three query surfaces
- FR-W20: Epic 34 — candidate set is a query; `sweep.rank` publishes no copied rows
- FR-W21: Epic 35 — two named methods; F07 refused
- FR-W22: Epic 35 — projection body is the canonical saved-view JSON
- FR-W23: Epic 35 — permitted vs forbidden projection predicates
- FR-W24: Epic 35 — projection homes and no occupancy
- FR-W25: Epic 35 — `analysis.rerun` is a new CT-32
- FR-W26: Epic 35 — `compare_runs` readout only
- FR-W27: Epic 35 — Book/BMS variants are complete `dev` candidates
- FR-W28: Epic 35 — labels stay parent-shaped
- FR-W29: Epic 33 — CLI/API parity for robustness and sweep batch/rank
- FR-W30: Epic 33 — data commands wrap qmf-data; no clone store
- FR-W31: Epic 33 — derived datasets + CT-12 `data_ref`; no auto-update clones
- FR-W32: Epic 37 — procedures are Graph Templates / Skills / Routines
- FR-W33: Epic 37 — run-steps occupy; query-steps do not
- FR-W34: Epic 37 — config-changing door steps mint ExperimentSpec successors
- FR-W35: Epic 32 — continuation is a daemon property; host is GAP-0062
- FR-W36: Epic 32 — cancel authority; tab-close cancels nothing
- FR-W37: Epic 32 — extensibility rungs 1–3; rung 4 = GAP-0081
- FR-W38: Epic 38 — generation ≠ search; QML authors; QMB runs
- FR-W39: Epic 38 — StrategyHandle references and registers; never assembles JSON
- FR-W40: Epic 38 — GAP-0085 nouns and GAP-0063 algorithm stay unfilled
- UX-DR1: Epic 34 — Library identities a later UI binds to
- UX-DR2: Epic 34 — non-kinds a later UI must not present as registry records
- UX-DR3: Epic 36 — operations / door-selected lanes (Epic 33/35/37 own named ops)
- UX-DR4: Epic 34 — query surfaces
- UX-DR5: Epic 32 — job lifecycle; tab-close ≠ cancel
- UX-DR6: Epic 36 — events (CT-13, wire, JobHandle)
- UX-DR7: Epic 32 — extension points visible to a non-source user
- UX-DR8: Epic 36 — project/workspace are display aliases

## Epic List

Seven epics, one per inventory feature. They stay separate because their
blockers differ (FEAT-0036 can start on FEAT-0029 alone; FEAT-0034 waits on
FEAT-0045; FEAT-0033 waits on FEAT-0044/0042; FEAT-0037 waits on the door).
QMB wave-mates (33/34/35) serialize if they share a worktree; they are not
merged into one epic.

Weight tags route factory lanes: **H** heavy, **L** light. Wave numbers are
the 2026-09-14 inventory waves, not a required build order beyond
`blocked_by`.

### Epic 32: Work that survives the laptop — continuation and three extension rungs (Wave 11, H)

The operator can leave a coordinated job running through `qma-daemon` plus a
reachable remote ExecutionEnvironment and the durable outbox, cancel it only
through `JobHandle.cancel`, and extend the workbench at rungs 1–3 (editable
config, ordinary Python, QMA packs) without a UI plugin SDK.

**FRs covered:** FR-W35, FR-W36, FR-W37
**Feature:** FEAT-0038
**Notes:** Blocked by FEAT-0042, FEAT-0041, FEAT-0027. Serialize with
FEAT-0043 (both COMP-QMA-DAEMON). GAP-0062 host machine stays unnamed.
GAP-0081 rung 4 stays deferred.

### Epic 33: The same CLI an agent uses reaches robustness, sweeps, and data (Wave 14, L)

The operator (and later an agent) can invoke the robustness ladder and sweep
`batch`/`rank` through the existing thin `qmb` CLI/API, and can acquire /
verify / gap-check / catalog / generate data as QMB fronts over qmf-data
without a second store.

**FRs covered:** FR-W29, FR-W30, FR-W31
**Feature:** FEAT-0036
**Notes:** Blocked by FEAT-0029. Serialize with Epics 34/35 (COMP-QMB).
Missing wiring, not a second library. MCP stays post-CLI-v1 (Story 16.6).

### Epic 34: One Library over fingerprints the operator already has (Wave 14, H)

The operator can query bots, Books, results, and coordinated ExperimentSpecs
as one Library of existing `fp1` kinds, and can retain / filter / rank
candidates as a read-time view — never a copied-row database, never QMA
staging, never a new COMP.

**FRs covered:** FR-W17, FR-W18, FR-W19, FR-W20
**Feature:** FEAT-0034
**Notes:** Blocked by FEAT-0007, FEAT-0029, FEAT-0045. Serialize with
Epics 33/35. Saved views are query hits, not registry kinds.

### Epic 35: Honest What-if — projection saved views versus path-dependent reruns (Wave 14, H)

The operator can filter an existing CT-32/CT-29 stream into a saved-view
JSON without pretending the Book changed, and can evaluate a complete
Book/BMS candidate only by spawning a new run that produces a new CT-32.
Size/R/seed rescales cannot hide as projections.

**FRs covered:** FR-W21, FR-W22, FR-W23, FR-W24, FR-W25, FR-W26, FR-W27, FR-W28
**Feature:** FEAT-0035
**Notes:** Blocked by FEAT-0029, FEAT-0027. Serialize with Epics 33/34.
SCN-0016 is the golden scenario. F07 stays deferred.

### Epic 36: A real QMA→QMB door — three lanes, research-paper, no sixth app (Wave 15, H)

The operator and a Quant can pick a lane by which door they call. Ungoverned
returns values. Governed writes research-paper evidence. Coordinated actually
spawns `qmb` under a persisted ExperimentSpec, with two honest labels on two
objects. There is no sixth application, no QMA-paper, and no Project kind.

**FRs covered:** FR-W01, FR-W02, FR-W03, FR-W04, FR-W05, FR-W06, FR-W07, FR-W08, FR-W09, FR-W10, FR-W11, FR-W12, FR-W13, FR-W14, FR-W15, FR-W16
**Feature:** FEAT-0033
**Notes:** Blocked by FEAT-0044, FEAT-0042, FEAT-0029. Serialize with
FEAT-0046 (COMP-QMA-CORE/DAEMON). Delivers the door FEAT-0037 waits on.
SCN-0015 is the golden scenario. Extends Stories 45.7/45.8/42.*/46.3; does
not rewrite them.

### Epic 37: Reusable procedures as Graph Templates, not a QMB wizard (Wave 16, H)

The operator can instantiate a Graph Template / Skill / Routine whose run
steps place one `qmb` invocation through the real door and whose query steps
do not consume occupancy. There is no workflow engine inside QMB and no
compulsory wizard.

**FRs covered:** FR-W32, FR-W33, FR-W34
**Feature:** FEAT-0037
**Notes:** Blocked by FEAT-0033 (Epic 36) and FEAT-0046. After the door.
Extends Stories 43.3 and 46.6.

### Epic 38: New strategy structures authored in QML, never generated inside QMB (Wave 12, H)

When generation ships, QML authors new CT-33/CT-34 bytes, QMB runs them, and
QMA only references and registers `dev`-zone candidates. Search stays QMB
parameter variation over the same bot `fp1`. Mechanism nouns and the
generator algorithm stay gaps.

**FRs covered:** FR-W38, FR-W39, FR-W40
**Feature:** FEAT-0039
**Notes:** Blocked by FEAT-0030, FEAT-0007. Trails connect-wave (DEC-0287
A1). Wave 12 in the inventory; sequenced last because generation must not
block Library, What-if, or the door.

### Stories in other increment files that this increment extends (do not duplicate)

| Existing story | What it already delivered | What WORKBENCH must not redo | What WORKBENCH closes |
|---|---|---|---|
| 13.2 / 15.4 | B-15 as-of port; one JSONL ledger line | Second registry; merge QMB ledger into sqlite | Library query + `workbench_lane` metadata (34, 36) |
| 16.1–16.5 | Thin `qmb` CLI/API + door-parity | Domain logic in doors; required MCP | Robustness/sweep/analysis/data CLI wiring (33, 35) |
| 16.6 | MCP scaffold, post-CLI-v1 | Make MCP required | — |
| 18.* / 20.* / 22.* | Data cmds; sweep Cartesian; robustness library | Second data store; second sweep/robustness engine | CLI exposure + occupancy split (33) |
| 19.* | CT-32 is the result; charts as data | Extend CT-32 with lane/analysis_method | Projection saved view beside it (35) |
| 21.* | TPE search over same bot `fp1` | Call TPE “generation” | Generation write-path is QML (38) |
| 41.4 / 46.7 | Durable outbox; unattended continuation budgets | Treat QMB process-per-run as laptop-off | Daemon/remote host property (32) |
| 42.* | Sole-writer sqlite / journal law | Second writer; new COMP | Compose the live process; persist specs (36) |
| 43.1 / 43.3 | Task Graph compiler; Graph Template law | Workflow engine inside QMB | Procedures place door steps (37) |
| 45.1–45.4 | ExecutionEnvironment, occupancy, JobHandle | New env kind; invent terminal state | Cancel map; continuation env (32, 36) |
| 45.7 | ExperimentSpec identity + lineage DAG | Git-branch-per-parameter; in-memory as product | Durable sqlite persistence (36) |
| 45.8 | Door **law**: one job/env, no import | Second governor; `import qmb` | Real CLI transport (36) |
| 46.3 | Experiment Ledger | Copy CT-32 into the ledger | `_ref` + `workbench_lane=coordinated` (36) |
| 46.6 | Routines fire Graph Templates | Agent-authored schedules | Procedure equivalent (37) |
| 48.* | Plugin packs incl. `analysis-backtest` | New plugin model | Load packs in composed daemon (36, 37) |
| 31.* | Honest FX paper on cTrader | Venue/node paths | **None** |

## Epic 32: Work that survives the laptop — continuation and three extension rungs

The operator can leave a coordinated job running through `qma-daemon` plus a
reachable remote ExecutionEnvironment and the durable outbox, cancel it only
through `JobHandle.cancel`, and extend the workbench at rungs 1–3 without a
UI plugin SDK. This epic binds the continuation **property** and the public
extension ladder. It does not name the GAP-0062 host machine, does not
replace `RecordingQmbDoorTransport` (Epic 36), and does not map cancel onto
a real `qmb` spawn until that door exists.

**Factory touch ownership:** exclusive writable surface is continuation /
ExecutionEnvironment reachability configuration under `qma-daemon` and the
durable outbox posture already owned by Story 41.4, plus any registry
variable that records “laptop-off promised”. Must not rewrite Epic 42
journal/sqlite law, Epic 43 hooks, Epic 45 door law, or QMB process-per-run.

**Traceability for the epic:** FR-W35, FR-W36, FR-W37, UX-DR5, UX-DR7,
NFR-W02, NFR-W06 A2, AR-W06 (GAP-0062, GAP-0081).

### Story 32.1: Continuation is a daemon property, not QMB process-per-run

As a QMX operator,
I want laptop-off continuation to require `qma-daemon` plus a reachable remote ExecutionEnvironment and the durable outbox,
So that QMB process-per-run cannot be sold as unattended work that survives sleep.

**Traceability:** FR-W35, NFR-W02, AR-W06.

**Acceptance Criteria:**

**Given** work that must survive workstation sleep
**When** the operator promises laptop-off continuation
**Then** the configuration names `qma-daemon` plus at least one registered remote ExecutionEnvironment and the durable ordered/fsynced outbox (Story 41.4)
**And** a configuration whose daemon and every reachable env live only on the sleeping laptop is a typed refusal, not a silent promise. (FR-W35; DEC-0278)

**Given** GAP-0062
**When** docs, settings, or tests describe the always-on host
**Then** they state the property and leave the machine as operator config
**And** no story invents a host name, a second VPS product, or a new COMP. (GAP-0062; DEC-0287)

**Given** a governed QMB orchestrator spawn (not CT-47)
**When** the operator workstation sleeps
**Then** that job's lifetime remains the QMB orchestrator process (process-per-run)
**And** this story does not treat that spawn as laptop-off continuation. (FR-W35; B-5)

**Given** Story 46.7 continuation budgets
**When** this story lands
**Then** those budgets still cap unattended Task Graph work
**And** this story does not rewrite the verifier, `block_stop`, or escalation mailbox. (AR-W04)

**Given** Tier 1
**When** it runs
**Then** it passes without a live remote host
**And** a fixture env marked unreachable is enough to prove the refusal. (NFR-W05 posture)

### Story 32.2: Tab-close cancels nothing; JobHandle.cancel is the only coordinated cancel authority

As a QMX operator,
I want closing a UI tab to detach client state only,
So that a running job does not die because a window closed.

**Traceability:** FR-W36, UX-DR5, DEC-0304.

**Acceptance Criteria:**

**Given** a coordinated JobHandle in `queued` or `running`
**When** a UI client detaches or a tab closes
**Then** the JobHandle state is unchanged
**And** no writer sets `cancelled`, `aborted`, `failed`, or `done`. (FR-W36; UX-DR5; DEC-0278)

**Given** coordinated cancel
**When** an authorized caller invokes `JobHandle.cancel`
**Then** that is the only coordinated cancel authority
**And** a plugin, Routine, worker, or UI widget other than that call cannot set a terminal JobHandle or QMB ledger state. (FR-W36; Story 45.4)

**Given** the QMA→QMB door is still `RecordingQmbDoorTransport`
**When** `JobHandle.cancel` is invoked
**Then** JobHandle still enters `cancelled` per Story 45.4
**And** mapping that cancel onto a live `qmb` abort is Epic 36's work, not this story's. (AR-W04; FR-W08)

**Given** ungoverned `qmb.run()`
**When** the calling process dies
**Then** nothing is written to the QMB ledger or Experiment Ledger
**And** this story does not invent an ungoverned cancel record. (FR-W04; FR-W36)

### Story 32.3: Extensibility rungs 1–3 bind; rung 4 stays GAP-0081

As a QMX operator who will not read this source,
I want three documented extension rungs — editable config, ordinary Python, QMA packs —
So that I can extend the workbench without a UI plugin SDK or a no-code generator.

**Traceability:** FR-W37, UX-DR7, NFR-W07.

**Acceptance Criteria:**

**Given** the public extension surface
**When** it is enumerated
**Then** rung 1 is ui-editable config variables on templates (`configurable: true`, L38)
**And** rung 2 is ordinary Python logic plus QMB ports/adapters
**And** rung 3 is QMA plugins, skills, graph templates, and desk packs. (FR-W37; DEC-0280; UX-DR7)

**Given** rung 4 (UI contribution SDK / `qma-ui-contract`)
**When** a caller asks to register a UI widget contribution
**Then** it is refused as GAP-0081 deferred
**And** no `ui_view` contribution point is minted. (FR-W37; DEC-0280; QMA AD-1)

**Given** a no-code authoring request (SQ-style building-block DSL, RandomCondition editor, `.qml` revival)
**When** it is presented as an extension rung
**Then** it is refused
**And** ordinary Python (rung 2) remains the logic path. (FR-W37; FR-W40; DEC-0172)

**Given** QMA “plugin” vocabulary
**When** rung 3 is described
**Then** “plugin” stays QMA-scoped (DEC-0346)
**And** no QMB module is called a plugin. (AR-W08)

**Given** A2 (work-environment roster UI-open)
**When** this epic ships
**Then** the work-environment roster remains a later UI alias over fingerprints
**And** this story does not mint a roster kind. (NFR-W06 A2; FR-W16)

## Epic 33: The same CLI an agent uses reaches robustness, sweeps, and data

The operator and later an agent can invoke the robustness ladder and sweep
`batch`/`rank` through the existing thin `qmb` CLI/API, and can acquire /
verify / gap-check / catalog / generate data as QMB fronts over qmf-data
without a second store. This is missing wiring, not a second library.

**Factory touch ownership:** exclusive writable surface is
`qmb/src/qmb/doors/cli` (and the Python API re-export in `doors/api`) for
new `robustness` / `sweep batch|rank` command groups, plus occupancy
classification on existing `qmb data` commands. Must not rewrite Epic 22
robustness library, Epic 20 Cartesian expansion, Epic 18 download/verify
internals, or Story 16.6 MCP.

**Traceability:** FR-W29, FR-W30, FR-W31, FR-W11, NFR-W01, AR-W01.

### Story 33.1: Expose the robustness ladder on the qmb CLI

As a QMX operator,
I want walk-forward, Monte Carlo, and significance on the `qmb` CLI,
So that robustness is a door, not a hidden library module.

**Traceability:** FR-W29, FR-W11, AR-W01.

**Acceptance Criteria:**

**Given** `integration@1b451a8` (robustness remains library-only; no `robustness` group under `qmb` CLI)
**When** this story lands
**Then** a thin `qmb robustness` command group (or equivalent subcommands) exposes walk-forward, trade-shuffle MC, candle-perturbation MC, and the pre-build rule-significance gate
**And** each command is adaptation-only over the Epic 22 library — no second robustness engine. (FR-W29; DEC-0281; DEC-0286)

**Given** a robustness command that spawns runs
**When** it is placed through the CT-47 door (once Epic 36 exists) or invoked as governed CLI
**Then** it counts as one `qmb` **run** invocation for occupancy when invoked as governed CLI (CT-47 placement uses the same classification once that door exists)
**And** QMB process-per-run children inside that invocation are not additional QMA jobs. (FR-W11; DEC-0276)

**Given** GAP-0048/0049 threshold values and pass batteries
**When** CLI help or output is inspected
**Then** no invented pass/fail battery is shipped
**And** the commands remain the interfaces Epic 22 already bound. (AR-W06; Story 22.1)

**Given** Story 16.5 door-parity
**When** the Python API is called
**Then** the same robustness rungs are reachable without domain logic in the door
**And** MCP remains post-CLI-v1 (Story 16.6). (FR-046; FR-W29)

**Given** Optuna
**When** lockfiles are inspected
**Then** `optuna==4.9.0` is unchanged
**And** 5.0.0 is not adopted. (NFR-W01; DEC-0287 A4)

### Story 33.2: Sweep batch and rank on the CLI; rank is a query

As a QMX operator,
I want `sweep batch` and `sweep rank` on the same CLI as backtest,
So that permutation work and ranking do not require importing library internals.

**Traceability:** FR-W29, FR-W20, FR-W11.

**Acceptance Criteria:**

**Given** `integration@1b451a8` (full sweep `batch`/`rank` CLI coverage missing)
**When** this story lands
**Then** thin CLI/API doors expose sweep batch (run invocation) and sweep rank (query)
**And** they wrap Epic 20 — no second Cartesian engine. (FR-W29; DEC-0281)

**Given** `sweep.rank`
**When** it is invoked
**Then** it is a read-time fold over the sweep's ledger lines (Story 20.4)
**And** it publishes no copied-row artifact, consumes no occupancy, mints no CT-32, and mints no ExperimentSpec successor. (FR-W20; FR-W11; DEC-0282)

**Given** sweep batch
**When** it is invoked
**Then** occupancy is one `qmb` run invocation wrapping the combo children
**And** each combo still writes exactly one ledger line (Story 20.3). (FR-W11; DEC-0276)

**Given** a caller asks `sweep.rank` to persist a candidate database
**When** the command runs
**Then** it is refused
**And** the operator is left with the fold, not a second store. (FR-W20; DEC-0269)

### Story 33.3: Data commands wrap qmf-data; derived datasets are not Library kinds

As a QMX operator,
I want acquire / verify / gap-check / catalog / generate to stay QMB fronts over qmf-data,
So that I never get a QuantDataManager clone or a silent auto-update under an experiment's feet.

**Traceability:** FR-W30, FR-W31, FR-W11.

**Acceptance Criteria:**

**Given** existing `qmb data download|verify|gap-check|catalog|generate` (Stories 18.*, 23.1)
**When** this story lands
**Then** those commands remain thin fronts over qmf-data rooms
**And** no clone store, CDN product, or second catalog is minted. (FR-W30; DEC-0281)

**Given** CSV/file import
**When** it is added or extended
**Then** it is a CT-15 adapter extend
**And** it is not a new store. (FR-W30)

**Given** a vendor-style timezone clone that would auto-update the source under a running experiment
**When** it is requested
**Then** it is refused
**And** ExperimentSpec `data_ref` (coordinated) and governed run-config continue to cite frozen CT-12 split fingerprints. (FR-W31; DEC-0281)

**Given** `data.download` that mutates rooms
**When** occupancy is classified
**Then** it is a **run** invocation
**And** `data.gap-check|verify|catalog|list` are queries (no occupancy, no CT-32, no spec successor). (FR-W11)

**Given** a derived dataset
**When** it is materialized
**Then** it is a new fingerprinted artifact with a CT-07 lineage edge
**And** it is not a Library kind. (FR-W31; FR-W18)

**Given** quality surfaces
**When** they are read
**Then** they are read models over CT-13 `data quality` events and `gap_check` reports
**And** they are not `analysis.project` views and not a new COMP. (FR-W30; DEC-0281)

## Epic 34: One Library over fingerprints the operator already has

The operator can query bots, Books, results, and coordinated ExperimentSpecs
as one Library of existing `fp1` kinds, and can retain / filter / rank
candidates as a read-time view — never a copied-row database, never QMA
staging, never a new COMP.

**Factory touch ownership:** exclusive writable surface is QMB B-15
registry-read / ledger merge query helpers and any thin CLI/API query door
that projects those reads. Must not mint a Library package, a sqlite table
for candidates, or registry kinds. Must not read the QMA staging store.

**Traceability:** FR-W17, FR-W18, FR-W19, FR-W20, UX-DR1, UX-DR2, UX-DR4.

### Story 34.1: Library kinds are the existing fp1 list; nothing else

As a QMX operator,
I want the shared Library to be a projection over fingerprints I already have,
So that one bot or result cannot exist as three records.

**Traceability:** FR-W17, FR-W18, UX-DR1, UX-DR2.

**Acceptance Criteria:**

**Given** a Library query
**When** kinds are enumerated
**Then** the kind list is exactly: CT-33 bot, CT-34 confluence, strategy-family, CT-22 Book, CT-27 BMS, CT-28 binding, CT-12 split, CT-10 observation, CT-32 result, and CT-47 ExperimentSpec (coordinated lane only)
**And** logic source-manifests are cited from CT-33, not a separate Library kind. (FR-W17; DEC-0271; UX-DR1)

**Given** QMA staging, RefinementProposals, JobHandles, Graph Templates, Skills, Routines, saved views, analysis publications, or derived datasets
**When** they are asked to register as Library kinds
**Then** they are refused
**And** a later UI must not present them as registry records. (FR-W18; UX-DR2; DEC-0271)

**Given** STRATS
**When** Library ingest is attempted
**Then** STRATS remains a KnowledgeSource corpus (QMA AD-19)
**And** it writes no registry kinds. (FR-W18)

**Given** a Project or Workspace kind
**When** it is requested
**Then** it is refused
**And** display names remain aliases (Epic 36 / FR-W16). (FR-W18; DEC-0284)

**Given** package layout
**When** it is inspected
**Then** there is no `COMP-LIB` / `qmx-library` package
**And** kind owner remains COMP-QMF-REGISTRY. (FR-W01; DEC-0271)

### Story 34.2: Three query surfaces — as-of, ledger merge, Experiment Ledger refs

As a QMX operator,
I want Library search to read the three surfaces that already exist,
So that I do not get a fourth identity store.

**Traceability:** FR-W19, UX-DR4.

**Acceptance Criteria:**

**Given** a Library search by kind + `fp1`
**When** it runs
**Then** it reads (1) the QMB B-15 registry-read as-of port (Story 13.2), (2) the QMB ledger merge view (Story 15.4), and (3) coordinated Experiment Ledger refs (Story 46.3)
**And** it does not open a fourth store. (FR-W19; DEC-0271; UX-DR4)

**Given** saved views or analysis publications
**When** Library search hits them
**Then** the hit cites the source kind's `fp1` (the CT-32, or a saved-view JSON `fp1` if one already exists)
**And** the hit is not a new registry kind. (FR-W19; FR-W18)

**Given** QMA staging
**When** Library search runs
**Then** staging is not read
**And** a test that folds staging into Library fails this story. (FR-W20; DEC-0282)

**Given** an as-of set
**When** search resolves names
**Then** Story 13.2 frozen as-of / fingerprint resolution still holds
**And** this story does not add a door-side registry cache. (AR-W04)

### Story 34.3: Candidate retain / filter / rank is a query, not a copied-row database

As a QMX operator,
I want to retain, filter, and rank candidates over ledger lines and `dev`-zone records,
So that a databank is a view rather than a second table.

**Traceability:** FR-W20, FR-W18.

**Acceptance Criteria:**

**Given** a candidate-set query
**When** it runs
**Then** it is a read-time view over QMB ledger lines, registry as-of sets including `dev`-zone candidates of Library kinds, and coordinated Experiment Ledger refs
**And** it does not read QMA staging and does not persist copied rows. (FR-W20; DEC-0282)

**Given** `sweep.rank` (Story 33.2)
**When** it is used as the candidate-set rank
**Then** it is this same view
**And** it still publishes no copied-row artifact. (FR-W20)

**Given** a saved-view home
**When** a candidate-set result is saved
**Then** ungoverned is a return value; governed-without-QMA is JSON in the source run-dir; coordinated persistence is Epic 36
**And** the body is required — a citation without a body is not a saved view. (FR-W20; FR-W24)

**Given** a request to write candidates into `qmf-registry` as a new kind or into a new sqlite table
**When** it is made
**Then** it is refused
**And** DEC-0084 stays dead. (FR-W20; DEC-0269)

## Epic 35: Honest What-if — projection saved views versus path-dependent reruns

The operator can filter an existing CT-32/CT-29 stream into a saved-view JSON
without pretending the Book changed, and can evaluate a complete Book/BMS
candidate only by spawning a new run that produces a new CT-32. Size/R/seed
rescales cannot hide as projections. Coordinated daemon persistence of
`analysis.published` waits on Epic 36; this epic ships the QMB library
functions and the ungoverned / governed-without-QMA homes.

**Factory touch ownership:** exclusive writable surface is a new QMB
`analysis` library module with thin CLI/API doors (`analysis.project`,
`analysis.rerun`, `compare_runs`) plus governed sidecar writes in the source
run-dir. Must not extend CT-32 or B-4 schemas. Must not reimplement Book/BMS
shapes (COMP-QMF-RISK). Must not open daemon sqlite.

**Traceability:** FR-W21..FR-W28, SCN-0016, NFR-W02, NFR-W07.

### Story 35.1: analysis.project returns the canonical saved-view JSON

As a QMX operator,
I want `analysis.project` to filter one cited CT-32 and its CT-29 stream into a saved view,
So that a What-if on hours or max-trades is not a new backtest and not a fake Book.

**Traceability:** FR-W21, FR-W22, FR-W23, FR-W11, SCN-0016.

**Acceptance Criteria:**

**Given** a completed governed (or coordinated) run with one CT-32 and a paired CT-29 stream
**When** `analysis.project` is called with a permitted predicate (hours/days/session window, max-trades cap, include/exclude filter)
**Then** the durable body is the canonical JSON `{method: projection, source_ct32, source_ct29, predicate, as_of}`
**And** `as_of` is the source CT-32's `registry_as_of` / occurrence, never query time
**And** identity `fp1` is of that JSON. (FR-W22; SCN-0016; DEC-0273)

**Given** that call
**When** artifacts are inspected
**Then** no new CT-32 is minted, no QMB ledger line is appended, no ExperimentSpec successor is minted, and no ExecutionEnvironment occupancy is consumed
**And** claim-class is `projection` — never admission evidence, never B-4 `role=confirmation`. (FR-W21; FR-W11; FR-W28; SCN-0016)

**Given** a citation of a projection without that JSON body
**When** it is treated as a saved view
**Then** it is refused
**And** a copied trade list is not a saved view. (FR-W22)

**Given** the Python API and `qmb` CLI
**When** `analysis.project` is exposed
**Then** the door is thin (B-1)
**And** QMA must not reimplement the filter (call the door, or wait for Epic 36 to shell it). (FR-W26; DEC-0273)

### Story 35.2: Forbidden projection axes refuse; ungoverned and governed homes

As a QMX operator,
I want a size or Book change to be impossible as a projection,
So that a filtered trade list cannot pose as a money-path counterfactual.

**Traceability:** FR-W23, FR-W24, SCN-0016 Branch A.

**Acceptance Criteria:**

**Given** `analysis.project`
**When** the predicate (or any extra field) would change size, R, Book/BMS fragments, execution ports, or `starting_capital`
**Then** the call is a typed refusal naming the forbidden axis
**And** the refusal names the change as path-dependent (a new run, a new CT-32) rather than implementing that run in this story. (FR-W23; SCN-0016 Branch A; NFR-W02)

**Given** an ungoverned caller (`qmb` library in-process, no orchestrator)
**When** `analysis.project` succeeds
**Then** the saved view is a return value only
**And** it is not durable and not a Library object. (FR-W24; DEC-0273)

**Given** a governed-without-QMA caller
**When** `analysis.project` succeeds
**Then** the JSON sidecar is written in the **source** run-dir
**And** there is no new orchestrator spawn, no QMB ledger line, and no CT-32. (FR-W24)

**Given** QMB
**When** it persists a governed sidecar
**Then** it does not open daemon sqlite
**And** coordinated `analysis.published` persistence is Epic 36. (FR-W24; DEC-0273)

### Story 35.3: analysis.rerun is a new QMB run and a new CT-32

As a QMX operator,
I want a path-dependent What-if to spawn a real run,
So that a Book or seed change has its own evidence instead of a rescaled list.

**Traceability:** FR-W25, FR-W11, SCN-0016 Then (2).

**Acceptance Criteria:**

**Given** a completed run and a new resolved run-config (Book/BMS fragments, fill/cost/financing ports, and/or `starting_capital`)
**When** `analysis.rerun` is called
**Then** QMB spawns a new governed (or, once Epic 36 exists, coordinated) run through the tunnel
**And** the canonical artifact is a new CT-32. (FR-W25; SCN-0016; DEC-0273)

**Given** occupancy
**When** `analysis.rerun` is placed
**Then** it consumes one `qmb` **run** invocation per ExecutionEnvironment
**And** it is not classified as a query. (FR-W11; FR-W25)

**Given** a `starting_capital` override
**When** the rerun compiles
**Then** the binding is stamped `seed_overridden` and the B-4 fold is forced `unrated`
**And** Story 13.5 / FM-12 still hold. (FR-W25; DEC-0160)

**Given** `analysis_method` or `lane`
**When** the new CT-32 is inspected
**Then** those fields do not exist on CT-32 or B-4
**And** metadata lives on the QMB ledger line (`workbench_lane=governed`) citing the CT-32 by `_ref` — the coordinated Experiment Ledger stamp is Epic 36. (FR-W07; FR-W28)

### Story 35.4: Book and BMS variants are complete dev-zone candidates plus replay

As a QMX operator,
I want a proposed Book or BMS to be a complete fingerprinted document,
So that a field patch cannot pose as a definition and a trade-list rescale cannot pose as Book simulation.

**Traceability:** FR-W27, SCN-0016.

**Acceptance Criteria:**

**Given** a proposed Book or BMS variant
**When** it is registered
**Then** it is a complete new fingerprinted CT-22/CT-27 in the registry `dev` zone
**And** a patch record or partial overlay is refused as a definition. (FR-W27; DEC-0274)

**Given** that candidate `fp1`
**When** it is evaluated
**Then** evaluation is `analysis.rerun` (Story 35.3) citing that fingerprint
**And** trade-list rescaling is not accepted as Book/BMS truth. (FR-W27; FR-W23)

**Given** QMA
**When** it emits a Book/BMS candidate
**Then** it remains `money_path_relevant` with a field-level diff in `approval_request` (Story 45.6 / FR-Q53)
**And** QMA still never fills an unset money-path field. (FR-W27; DEC-0274)

**Given** shape ownership
**When** the candidate is minted
**Then** COMP-QMF-RISK remains the shape owner and the composition root remains the mint
**And** this story does not move mint into QMB or QMA. (FR-W27; AR-W04)

### Story 35.5: compare_runs is readout; labels stay parent-shaped

As a QMX operator,
I want overlaying two CT-32s to stamp nothing,
So that a comparison cannot mint a third analysis method or a confirmation label.

**Traceability:** FR-W26, FR-W28, SCN-0016 Then (3).

**Acceptance Criteria:**

**Given** two cited CT-32s (original and rerun, or any pair)
**When** `compare_runs` is called
**Then** it reads cited CT-32 fields and returns a readout
**And** it mints no artifact, no ledger line, no confirmation label, and no occupancy. (FR-W26; SCN-0016; DEC-0273)

**Given** CT-32 and B-4 public shapes
**When** this epic's diffs are inspected
**Then** no `lane`, `analysis_method`, or other workbench field is added
**And** NFR-W07 holds. (FR-W28; DEC-0283)

**Given** a projection saved view
**When** it is read as evidence
**Then** it has no B-4 role, claim-class `projection`, inherited source world, and never `confirmed`
**And** L20 still forbids gating live money on replay-world verdicts. (FR-W28)

**Given** a path-dependent rerun CT-32
**When** its B-4 role is read
**Then** it is the role of **that** run
**And** it is not admission evidence unless `role=confirmation`. (FR-W28)

**Given** F07 synthetic portfolio combination
**When** it is requested
**Then** it is refused as deferred
**And** neither `analysis.project` nor `analysis.rerun` implements it. (FR-W21; AR-W06)

## Epic 36: A real QMA→QMB door — three lanes, research-paper, no sixth app

The operator and a Quant can pick a lane by which door they call. Ungoverned
returns values. Governed writes research-paper evidence. Coordinated actually
spawns `qmb` under a persisted ExperimentSpec, with two honest labels on two
objects. There is no sixth application, no QMA-paper, and no Project kind.
This epic closes the brownfield recording transport and missing daemon
process. It extends Stories 45.7, 45.8, 42.*, and 46.3; it does not rewrite
their law.

**Factory touch ownership:** exclusive writable surface is
`qma-daemon` backtest transport (replace `RecordingQmbDoorTransport`), the
composed asyncio process entry (loopback listener + sole sqlite writer +
pack roster), ExperimentSpec / Experiment Ledger persistence through that
writer, and QMB ledger-line metadata for `workbench_lane`. Must not add an
`import qmb` edge, must not extend CT-32/B-4, must not mint a package, must
not rewrite Epic 42 store law or Epic 45 JobHandle state machine.

**Traceability:** FR-W01..FR-W16, SCN-0015, UX-DR3, UX-DR6, UX-DR8,
NFR-W03, NFR-W04, NFR-W05, AR-W01.

### Story 36.1: Compose the asyncio daemon process from existing modules

As a daemon operator,
I want one long-running process that is the loopback listener, the sole sqlite writer, and the pack roster,
So that connect-wave is composition, not a sixth application.

**Traceability:** FR-W09, FR-W01, NFR-W04, AR-W02.

**Acceptance Criteria:**

**Given** `integration@1b451a8` (no composed asyncio listener process found under `qma-daemon`/`qma-wire` `src/`)
**When** this story lands
**Then** a long-running process is composed from existing modules: loopback listener + sole sqlite writer + pack roster
**And** no new COMP, no HTTP experiment service, and no second daemon runtime is minted. (FR-W09; FR-W01; DEC-0276; DEC-0269)

**Given** sqlite
**When** the process runs
**Then** the store still opens on exactly one connection in one writer thread (Story 42.1)
**And** QMB JSONL is not merged into that store. (NFR-W04; DEC-0305)

**Given** pack roster
**When** the process starts
**Then** the five desk packs load under Epic 48 law
**And** `analysis-backtest` remains the Backtesting Service's daemon half. (AR-W04; DEC-0316)

**Given** CT-40..CT-51 wiring stamps
**When** docs are checked
**Then** matching source may be `source-inspected`
**And** this story does not invent a second wire schema. (DEC-0286; NFR-W07)

### Story 36.2: Replace RecordingQmbDoorTransport with a real qmb CLI transport

As an Analysis Agent,
I want the Backtesting Service to spawn a real `qmb` CLI process,
So that a coordinated experiment is a run rather than a recorded pretend.

**Traceability:** FR-W08, FR-W12, NFR-W03, NFR-W05, AR-W01.

**Acceptance Criteria:**

**Given** the Story 36.1 composed process and `RecordingQmbDoorTransport` as the default at `integration@1b451a8` (records, does not spawn `qmb`)
**When** this story lands
**Then** the production transport places a real `qmb` CLI process (MCP later) along the existing route Agent → QMA backtest tool → Backtesting Service → `qmb` door → QMB
**And** treating the recording transport as a working integration is a test failure. (FR-W08; DEC-0276; DEC-0286; Story 45.8)

**Given** the Backtesting Service
**When** package boundaries and import graphs are checked
**Then** the daemon, every plugin, and every QMA worker image still have no `import qmb` edge
**And** in-process library calls from QMA are a typed refusal / static-gate failure. (FR-W12; NFR-W03; DEC-0348)

**Given** Story 45.8 occupancy law
**When** a second `qmb` **run** job is placed in an environment that already holds one
**Then** it is refused
**And** QMB still owns intra-node parallelism, its JSONL ledger, and CT-32. (FR-W08; FR-Q55)

**Given** an acceptance test that claims the door works
**When** it runs
**Then** it actually spawns `qmb` or a documented test double that is not `RecordingQmbDoorTransport` presented as production
**And** `source-inspected` is not accepted as e2e. (NFR-W05; DEC-0286)

**Given** the request
**When** it runs
**Then** it runs only against recorded evidence and QMB replay
**And** it never targets a venue account (SCN-0014; FR-Q55). (FR-W13)

### Story 36.3: Persist ExperimentSpec, Experiment Ledger, and successor edges through sqlite

As an Analysis Agent,
I want ExperimentSpec identity to survive a daemon restart,
So that coordinated continuity is a fingerprint rather than an in-memory map.

**Traceability:** FR-W10, FR-W16, NFR-W04.

**Acceptance Criteria:**

**Given** Story 45.7 ExperimentSpec identity (content-addressed `fp1`, lineage DAG, ledger link)
**When** an experiment is registered
**Then** the ExperimentSpec, its Experiment Ledger, and CT-07 `branches-from` successor edges persist through the daemon journal / sole sqlite writer
**And** a daemon restart restores them; in-memory maps are not product truth. (FR-W10; DEC-0276; DEC-0308)

**Given** the QMB run ledger
**When** coordinated evidence is recorded
**Then** QMA stores `_ref`s only — it does not copy or merge JSONL or CT-32
**And** QMB does not write ExperimentSpec edges. (FR-W10; NFR-W04)

**Given** DEC-0376
**When** a parameter change is recorded
**Then** it is a resolved-config ref on a successor ExperimentSpec
**And** git-branch-per-parameter remains cut. (FR-W10; FR-W16; DEC-0284)

**Given** a Project or Workspace record
**When** it is requested as the continuity object
**Then** it is refused
**And** coordinated continuity is the ExperimentSpec `fp1` (`code_ref` / `resolved_config_ref` / `data_ref` = CT-12 / `environment_ref`). (FR-W16; DEC-0284; UX-DR8)

### Story 36.4: Three door-derived lanes and two honest workbench_lane labels

As a QMX operator,
I want the lane to come from which door I called,
So that exploratory values, governed evidence, and agent jobs cannot collapse into one “run” noun.

**Traceability:** FR-W03, FR-W04, FR-W05, FR-W06, FR-W07, SCN-0015.

**Acceptance Criteria:**

**Given** a registered bot `fp1`
**When** it is invoked via `qmb.run()` / ordinary Python / `import qml` with no orchestrator and no CT-47
**Then** the call is **ungoverned**: library values only; no QMB ledger line; no CT-32 registry record; no ExperimentSpec / Experiment Ledger
**And** a returned CT-32-shaped value is not a Library object. (FR-W04; SCN-0015 Then (1))

**Given** the same bot
**When** the QMB orchestrator spawns a CLI/API run **not** placed by CT-47 (`spawn_governed`)
**Then** the call is **governed**: exactly one WriterId-scoped ledger line with metadata `workbench_lane=governed` and one CT-32
**And** there is no ExperimentSpec unless a later act places the same work through CT-47. (FR-W05; SCN-0015 Then (2))

**Given** the same bot and a registered ExperimentSpec
**When** the QMA Backtesting Service places one `qmb` CLI run
**Then** the spawned run still writes one QMB ledger line with `workbench_lane=governed` and one CT-32 (evidence by `_ref`)
**And** the Experiment Ledger entry carries `workbench_lane=coordinated`
**And** the two labels are not collapsed into one field. (FR-W06; SCN-0015 Then (3))

**Given** a caller-declared `lane` / `workbench_lane` / `analysis_method` on the payload, on CT-32, or on B-4
**When** the call is made
**Then** it is refused
**And** extending CT-32 or B-4 with that field is a spine amendment, not a connect fix. (FR-W03; FR-W07; SCN-0015 Branch A)

**Given** L33 graduation
**When** ungoverned Python is turned into governed evidence
**Then** it is a separate two-artifact registration act
**And** it is not this spawn and not a `workbench_lane`. (FR-W04; DEC-0270)

### Story 36.5: Occupancy versus queries; JobHandle.cancel maps to QMB abort

As a daemon operator,
I want only run invocations to occupy an ExecutionEnvironment,
So that a What-if projection or a sweep rank cannot block the next backtest.

**Traceability:** FR-W11, FR-W36, UX-DR5.

**Acceptance Criteria:**

**Given** an ExecutionEnvironment
**When** occupancy is counted
**Then** one `qmb` CLI/MCP **run** invocation is consumed by backtest, optimize, sweep, robustness, `analysis.rerun`, and data download that mutates rooms
**And** QMB process-per-run children inside that invocation are not additional QMA jobs. (FR-W11; DEC-0276)

**Given** `analysis.project`, `compare_runs`, `sweep.rank`, ledger reads, `data.gap-check|verify|catalog|list`
**When** they are placed through the door
**Then** they consume no occupancy, mint no CT-32, and mint no ExperimentSpec successor
**And** coordinated `analysis.project` is the daemon shelling the CLI as a query, waiting, and persisting refs (Story 36.3 / 35.1). (FR-W11; FR-W24)

**Given** a coordinated JobHandle
**When** `JobHandle.cancel` is invoked
**Then** the door maps it to QMB abort and the QMB ledger writes `aborted`
**And** no other writer may set that terminal ledger state. (FR-W36; Story 32.2; Story 15.3)

**Given** a projection saved view produced through the coordinated query path
**When** the daemon persists it
**Then** it writes the JSON plus an `analysis.published` Experiment Ledger entry citing that `fp1`
**And** QMB still never opens daemon sqlite. (FR-W24; DEC-0273)

**Given** a placed run or query
**When** progress or failure is observed
**Then** clients see JobHandle progress/failure plus existing CT-13 / qma-wire events
**And** no new event bus is minted. (UX-DR6; CT-13; CT-40)

### Story 36.6: Paper trinity, hub, notebooks, and alias identity

As a QMX operator,
I want research-paper, node-paper, and “QMA-paper” to stay three different nouns,
So that a coordinated QMB replay cannot be sold as node soak or as an agent execution tool.

**Traceability:** FR-W13, FR-W14, FR-W15, FR-W16, UX-DR3, UX-DR8.

**Acceptance Criteria:**

**Given** a governed QMB replay (`world=replay`) outside the node
**When** it is named
**Then** it is **research-paper**
**And** it is not node-paper and not QMA-paper. (FR-W13; DEC-0275)

**Given** node-paper
**When** this epic is inspected
**Then** Book-level demo routing + soak (`role=demo`, `world=live`) remains COMP-QMN / CONNECT
**And** no per-bot paper lane is introduced. (FR-W13; DEC-0261)

**Given** any QMA execution tool at any account role, “paper only” included
**When** registration is attempted
**Then** it is refused (DEC-0341)
**And** QMA-paper does not exist. (FR-W13; DEC-0275)

**Given** QMB WriterId-scoped fragments
**When** they enter the B-15 hub inbox
**Then** sandbox-provenance stays refused at publish and pull; `hub_publish` is human
**And** QMA never writes the hub (candidate refs only). (FR-W14; DEC-0275)

**Given** an exploratory notebook
**When** it runs on a controlled-room host
**Then** it `import qmb` / `import qml`
**And** a managed interpreter lifecycle, if product-owned, is a QMA ExecutionEnvironment — not a QMB module, not a new COMP, not a pinned Jupyter product. (FR-W15; DEC-0279)

**Given** display names “project” / “workspace”
**When** they appear
**Then** they are UX aliases over ExperimentSpec (coordinated) or bot `fp1` (governed)
**And** UI tabs must not mint a record. (FR-W16; UX-DR8; DEC-0284)

**Given** promotion
**When** a candidate should go live
**Then** it remains a human act outside QMA onto the node
**And** this epic grants no promotion authority. (FR-W02; UX-DR3; DEC-0285)

## Epic 37: Reusable procedures as Graph Templates, not a QMB wizard

The operator can instantiate a Graph Template / Skill / Routine whose run
steps place one `qmb` invocation through the real door and whose query steps
do not consume occupancy. There is no workflow engine inside QMB and no
compulsory wizard. Requires Epic 36 (the door) and FEAT-0046 (packs).

**Factory touch ownership:** exclusive writable surface is Graph Template /
Skill / Routine **content** and the `analysis-backtest` (and sibling) pack
step types that place QMB run vs query through the Story 36.2 door. Must not
grow a task graph inside QMB. Must not mint a new CT-07 edge kind.

**Traceability:** FR-W32, FR-W33, FR-W34, FR-W12.

### Story 37.1: Procedures live in QMA; QMB does not grow a task graph

As a QMX operator,
I want a reusable procedure to be a Graph Template, Skill, or Routine,
So that I can repeat research work without a QMB workflow engine or a compulsory wizard.

**Traceability:** FR-W32, AR-W04.

**Acceptance Criteria:**

**Given** a reusable procedure
**When** it is authored
**Then** it is a QMA Graph Template, Skill, or operator Routine (Stories 43.3, 46.6)
**And** QMB gains no task-graph module. (FR-W32; DEC-0277)

**Given** a compulsory research→backtest→paper wizard or SQ Custom Projects clone
**When** it is requested as the procedure product
**Then** it is refused
**And** composition stays non-linear: any step may be the first door placement. (FR-W32; FR-W34; DEC-0277)

**Given** one Graph Template instantiation
**When** it is compiled
**Then** it is one Mission
**And** the procedure itself is not an ExperimentSpec. (FR-W32; FR-W34)

**Given** daemon / plugins / worker images
**When** import graphs are checked
**Then** they still never `import qmb`
**And** NFR-W03 still holds. (FR-W12)

### Story 37.2: Run-steps occupy the door; query-steps do not

As an Analysis Agent,
I want procedure steps to honor the same occupancy split as the door,
So that a projection or rank inside a procedure cannot block the next backtest.

**Traceability:** FR-W33, FR-W11.

**Acceptance Criteria:**

**Given** a procedure step that names a QMB **run** (backtest, optimize, sweep, robustness, `analysis.rerun`, mutating data download)
**When** it executes
**Then** it is placed through the CT-47 `qmb` door as one CLI/MCP run invocation
**And** occupancy is consumed per FR-W11 / Story 36.5. (FR-W33; DEC-0277)

**Given** a procedure step that names a QMB **query** (`analysis.project`, `compare_runs`, `sweep.rank`, gap-check/verify/catalog/list)
**When** it executes
**Then** it is a door query: no occupancy, no CT-32, no spec successor
**And** it calls Epic 35/33 functions rather than reimplementing them. (FR-W33; FR-W26)

**Given** an environment that already holds a run invocation
**When** a second run-step is placed
**Then** it is refused until the slot is free
**And** query-steps still proceed. (FR-W33; FR-W11)

### Story 37.3: Config-changing door steps mint ExperimentSpec successors

As an Analysis Agent,
I want each procedure step that changes resolved-config to be a successor spec,
So that lineage stays on ExperimentSpec rather than mutating a procedure-as-experiment.

**Traceability:** FR-W34, FR-W10.

**Acceptance Criteria:**

**Given** a door step that changes resolved-config
**When** it is placed
**Then** it mints an ExperimentSpec successor via `create_successor` plus the existing CT-07 `branches-from` edge
**And** it does not use bot `supersedes` and does not mint a new edge kind. (FR-W34; DEC-0277)

**Given** a query-step that does not change resolved-config
**When** it is placed
**Then** it mints no ExperimentSpec successor
**And** occupancy remains zero. (FR-W34; FR-W11)

**Given** the procedure record
**When** identity is inspected
**Then** the procedure is not itself an ExperimentSpec
**And** coordinated continuity remains the spec `fp1` (Story 36.3). (FR-W34; FR-W16)

## Epic 38: New strategy structures authored in QML, never generated inside QMB

When generation ships, QML authors new CT-33/CT-34 bytes, QMB runs them, and
QMA only references and registers `dev`-zone candidates. Search stays QMB
parameter variation over the same bot `fp1`. Mechanism nouns and the
generator algorithm stay gaps. Trails connect-wave (DEC-0287 A1).

**Factory touch ownership:** exclusive writable surface is COMP-QML
authoring / host mint (CT-06 envelope) plus tests that QMA `StrategyHandle`
and QMB search stay on their existing sides of the line. Must not put a
generator inside QMB. Must not fill GAP-0085 nouns or GAP-0063 algorithm in
prose or code.

**Traceability:** FR-W38, FR-W39, FR-W40, NFR-W06 A1.

### Story 38.1: Search stays QMB; generation write-ownership is QML/host

As a QMX operator,
I want parameter search and structure generation to be different acts,
So that TPE cannot be sold as “strategy generation”.

**Traceability:** FR-W38, AR-W05.

**Acceptance Criteria:**

**Given** QMB optimize/sweep (Epic 21 / 20)
**When** it varies declared CT-33 parameters
**Then** trial ledger lines cite the **same** bot `fp1`
**And** that act is **search**, not generation. (FR-W38; DEC-0272)

**Given** generation, if this story ships a first authoring path
**When** new structure is produced
**Then** QML authors new CT-33/CT-34 content and/or logic-source bytes
**And** the QML/host composition root mints the CT-06 envelope
**And** QMB runs the candidates — it does not author them. (FR-W38; DEC-0272)

**Given** a generator module inside `qmb/`
**When** layout is inspected
**Then** it does not exist
**And** a PR that adds one fails this story. (FR-W38; AR-W05)

**Given** `.qml` DSL revival or SQ RandomCondition as a schema
**When** either is proposed
**Then** it is refused
**And** RandomCondition remains a donor shape, not a copy. (FR-W40; DEC-0172)

### Story 38.2: StrategyHandle references and registers; it never assembles CT-33 JSON

As an Analysis Agent,
I want `StrategyHandle` to point at fingerprints QML already minted,
So that QMA cannot become the author of bot definitions.

**Traceability:** FR-W39, FR-Q53.

**Acceptance Criteria:**

**Given** QMA `StrategyHandle`
**When** it is used
**Then** it may only (1) reference an already-fingerprinted registry record and (2) register those bytes as a `dev`-zone candidate with a QMA `origin` field and a CT-07 predecessor edge
**And** it never assembles CT-33/CT-34 JSON, never mints mechanism nouns, never fills RandomCondition slots. (FR-W39; DEC-0272; DEC-0313)

**Given** `GAP_0085_STRATEGY_MECHANISMS` on `integration@1b451a8`
**When** a caller asks QMA to mint Entry/Exit/Filter/Session nouns
**Then** the existing refusal still holds
**And** this story does not weaken it. (FR-W39; FR-W40)

**Given** Story 45.6 `money_path_relevant`
**When** a candidate touches risk/sizing/exit fields
**Then** the field-level diff requirement still holds
**And** QMA still never fills an unset money-path field. (FR-W27; FR-W39)

### Story 38.3: GAP-0085 nouns and GAP-0063 algorithm stay unfilled

As a QMX operator,
I want the generator algorithm and mechanism nouns to remain named gaps,
So that connect-wave cannot quietly invent a DSL to dodge those choices.

**Traceability:** FR-W40, NFR-W06 A1, AR-W06.

**Acceptance Criteria:**

**Given** GAP-0085
**When** this epic's diffs and docs are inspected
**Then** typed Entry/Exit/Filter/Session vocabulary is not minted
**And** write-ownership remains QML/host for a later increment. (FR-W40; DEC-0272)

**Given** GAP-0063
**When** a first algorithm (placeholder-fill of CT-34 legs vs Python-logic synthesis) is requested as a decided default
**Then** the request is refused as unruled
**And** no prose in this epic fills the choice. (FR-W40; DEC-0287)

**Given** DEC-0287 A1
**When** factory scheduling is read
**Then** this epic trails connect-wave (Epics 32–37)
**And** it does not block Library, What-if, or the door. (NFR-W06 A1)

**Given** no-code authoring
**When** it is promised as a V1 generation surface
**Then** it is refused
**And** rung 2 ordinary Python (Story 32.3) remains the logic path. (FR-W40; FR-W37)



