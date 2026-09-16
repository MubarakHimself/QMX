---
id: ADR-0022
title: QMX strategy-experimentation workbench — composition over existing applications
type: adr
status: ratified
component: COMP-QMB
depends_on: [COMP-QMB, COMP-QML, COMP-QMA-CORE, COMP-QMA-WIRE, COMP-QMA-DAEMON, COMP-QMF-REGISTRY, COMP-QMF-RISK, COMP-QMF-DATA, COMP-QMN]
decisions: [DEC-0269, DEC-0270, DEC-0271, DEC-0272, DEC-0273, DEC-0274, DEC-0275, DEC-0276, DEC-0277, DEC-0278, DEC-0279, DEC-0280, DEC-0281, DEC-0282, DEC-0283, DEC-0284, DEC-0285, DEC-0286, DEC-0287, DEC-0381, DEC-0402, DEC-0403]
sources: [_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-14/CAPABILITY-EXPANSION.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-14/.memlog.md, _docwork/workbench-increment-brief.md, _docwork/ledger.yaml, docs/architecture/dependencies.yaml, docs/decisions/ADR-0017-qmb-experimentation-library.md, docs/decisions/ADR-0018-qml-bot-authoring-library.md, docs/decisions/ADR-0020-qma-agentic-system.md, docs/decisions/ADR-0019-trading-node.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/ARCHITECTURE-SPINE.md]
generated: 2026-09-14
verified: 2026-09-16
stale_after: 1y
---

# ADR-0022: QMX strategy-experimentation workbench — composition over existing applications

Date: 2026-09-14. Status: accepted.

## Context

QMX already has five application-layer products on the QMF toolbox: `COMP-QMB` (experimentation library + `qmb` CLI), `COMP-QML` (bot authoring), `COMP-QMN` (trading node, paper then live), and `COMP-QMA-CORE` / `COMP-QMA-WIRE` / `COMP-QMA-DAEMON` (agentic system). The 2026-09-14 architecture sitting produced a feature-altitude spine (`architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md`, status: final, local AD-1..AD-16) so those products compose as one **strategy-experimentation workbench**: one fingerprint identity, three door-derived experiment lanes, two named analysis methods. Parents QMF AD-1..41, QMB B-1..15, QML QL-1..10, NODE TN-1..25, QMA AD-1..29, and CONNECT AD-1..5 bind read-only. Local `AD-1`..`AD-16` do not renumber those parents (DEC-0285).

Planning checkout is `main` `430fb7d`. Implementation was inspected on `integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` via `git show` / `git ls-tree` without switching branches. Matching source exists for CT-32, CT-33/CT-34, CT-47 and CT-40..CT-51, and `qmf-risk` value types; the default QMA→QMB transport is still `RecordingQmbDoorTransport`; no composed asyncio listener process was found under `qma-daemon`/`qma-wire` `src/`; robustness remains library-only on the CLI. Class/test existence is not end-to-end proof (DEC-0286).

This ADR records the documentation-factory absorption of that spine. It does not authorize implementation, credentials, a live session, order submission, promotion, or go-live — those arrive only through the factory pipeline (DEC-0285). Generated layouts and reactions to them are not preference evidence (DEC-0287). The PRD is not rewritten here; FR addenda are GAP-0061 (DEC-0287).

## Options considered

1. **Mint an experiment-service package / an HTTP experiment service / a Project or Workspace kind** — a sixth application or a QuantConnect-shaped identity store. Rejected because: DEC-0084 stays dead; QMF AD-16 kinds already cover bots, Books, results; QMA AD-17 already owns ExperimentSpec (DEC-0269, DEC-0284).
2. **Adopt a donor engine** (LEAN, StrategyQuant genetic/random, RoboQuant RQ Engine) or revive a central backtest service. Rejected because: DEC-0013, DEC-0084, DEC-0085, DEC-0086, Cut DEC-0376 (DEC-0285).
3. **Put structure generation inside QMB** or let QMA assemble CT-33 JSON. Rejected because: search is QMB parameter variation over the same bot `fp1`; generation authors new bytes via QML (DEC-0272). GAP-0085 nouns and GAP-0063 algorithm stay gaps.
4. **Treat a filtered trade list as a Book/BMS counterfactual** or extend CT-32 with `lane` / `analysis_method`. Rejected because: two named methods already split projection (saved view) from path-dependent rerun; labels stay parent-shaped (DEC-0273, DEC-0283).
5. **Reuse the existing applications and connect what already exists** — chosen. Workbench is projections, doors, and procedures over QMF, QMB, QML, QMA, and QMN (DEC-0285).

## Decision

The workbench spine AD-1..AD-16 is adopted in full as DEC-0269 through DEC-0284. The umbrella is DEC-0285. Wiring-status reconcile is DEC-0286. Cheap-veto assumptions ride DEC-0287.

- **AD-1 / DEC-0269 — not a sixth application.** Every new capability names an existing `COMP-*` owner or an explicit connect/extend of one. Minting a new application package or a permanent experiment daemon besides `qma-daemon` is a spine amendment. Inherited stores stand: `qmf-registry`, `qmf-data` rooms, QMB JSONL run ledger, QMA daemon sqlite (journal, Experiment Ledger). A new store beside those is a spine amendment. DEC-0084 stays dead.
- **AD-2 / DEC-0270 — three door-derived lanes.** Ungoverned (`qmb.run()` / ordinary Python / `import qml`) returns values and writes no ledger, no CT-32, no ExperimentSpec. Governed (orchestrator spawn not placed by CT-47) writes one QMB ledger line and one CT-32. Coordinated (QMA Backtesting Service) places at most one `qmb` CLI/MCP invocation per ExecutionEnvironment, never `import qmb`, and requires a registered ExperimentSpec. `workbench_lane` is derived from the door and recorded only as metadata on the QMB ledger line (`governed` for every orchestrator spawn) and on the Experiment Ledger entry (`coordinated` when QMA placed it). It is not QMF AD-12 evidence class, not B-4 role, not a CT-32 field. L33 graduation is two-artifact registration, not this spawn.
- **AD-3 / DEC-0271 — Library is a projection.** No new COMP. Shared objects are existing `fp1` kinds: CT-33, CT-34, strategy-family, CT-22, CT-27, CT-28, CT-12, CT-10, CT-32, and CT-47 ExperimentSpec (coordinated only). STRATS does not write registry kinds. Staging, JobHandles, Graph Templates, Skills, Routines, saved views, and derived datasets are not Library kinds.
- **AD-4 / DEC-0272 — generation is not search.** Search varies declared CT-33 parameters in QMB. Generation, if built, authors new CT-33/CT-34 and/or logic-source bytes via QML. QMA never assembles that JSON. GAP-0085 nouns and GAP-0063 algorithm stay deferred.
- **AD-5 / DEC-0273 — two named analysis methods.** `analysis.project` is a saved view over one cited CT-32 and its CT-29 stream; the durable body is the canonical JSON `{method: projection, source_ct32, source_ct29, predicate, as_of}`; size/R/Book/ports/`starting_capital` are forbidden as projection; it is not a run and consumes no occupancy. `analysis.rerun` is a new QMB run whose artifact is a new CT-32. `compare_runs` is readout only. F07 synthetic portfolios stay deferred.
- **AD-6 / DEC-0274 — Book/BMS variants are complete candidates plus replay.** A proposed Book/BMS is a complete new fingerprinted CT-22/CT-27 in the registry `dev` zone, not a patch. QMA may emit it only as `money_path_relevant` with a field-level diff; unset money-path fields stay unset.
- **AD-7 / DEC-0275 — paper trinity.** research-paper = QMB governed replay (`world=replay`) outside the node. node-paper = Book-level demo routing + soak (`role=demo`, `world=live`); no per-bot paper lane (DEC-0261). QMA-paper does not exist (DEC-0341). QMB WriterId fragments may enter the B-15 hub inbox; sandbox-provenance stays refused; `hub_publish` is human; QMA never writes the hub.
- **AD-8 / DEC-0276 — the QMA→QMB door is connect.** Replace `RecordingQmbDoorTransport` with a real CLI transport. Compose the asyncio daemon process from existing modules. Persist ExperimentSpec and Experiment Ledger through the daemon writer. Occupancy is one `qmb` **run** invocation per ExecutionEnvironment. Queries (`analysis.project`, `compare_runs`, `sweep.rank`, gap-check/verify/catalog/list) do not consume occupancy.
- **AD-9 / DEC-0277 — procedures live in QMA; steps live in QMB.** Graph Templates / Skills / Routines. QMB does not grow a task graph. No compulsory wizard. Never `import qmb` from the daemon, a plugin, or a worker image.
- **AD-10 / DEC-0278 — continuation is a daemon property.** Work that must survive workstation sleep is owned by `qma-daemon` plus remote ExecutionEnvironments and the durable outbox. Closing a UI tab cancels nothing. The concrete host is GAP-0062.
- **AD-11 / DEC-0279 — notebooks import the library.** Managed interpreter lifecycle, if product-owned, is a QMA ExecutionEnvironment. Not a QMB module and not a new COMP.
- **AD-12 / DEC-0280 — extensibility ladder.** Rungs 1–3 bind now. Rung 4 stays GAP-0081.
- **AD-13 / DEC-0281 — data work wraps qmf-data.** QMB data commands. No clone store. Coordinated `data_ref` cites CT-12 splits.
- **AD-14 / DEC-0282 — a candidate set is a query.** Read-time view over QMB ledger lines, registry as-of (including `dev`-zone), and Experiment Ledger refs. Does not read QMA staging.
- **AD-15 / DEC-0283 — labels stay parent-shaped.** Do not extend CT-32 or B-4. Confirmation evidence remains B-4 `role=confirmation` only. Projection never reads as `confirmed`. L20 stands.
- **AD-16 / DEC-0284 — no Project kind, no Workspace kind.** Coordinated continuity is ExperimentSpec `fp1`. Display names `project` / `workspace` are UX aliases.

## Architecture-preflight verdict

**reuse COMP-QMB** for named analysis functions, CLI/API coverage of existing library rungs, data commands wrapping qmf-data, ungoverned `run()`, governed orchestrator spawn, CT-32 production, and B-15 as-of reads.

**reuse COMP-QML** for CT-33/CT-34 authoring, the ungoverned tunnel, and (later) generation write-ownership.

**reuse COMP-QMA-CORE** for ExperimentSpec, handles, ports, Graph Template / Skill / Routine definitions.

**reuse COMP-QMA-WIRE** for the loopback listener posture, dial-out, and durable outbox types.

**reuse COMP-QMA-DAEMON** for the real CLI door, ExperimentSpec/ledger persistence, composed asyncio process, procedure placement, and continuation.

**reuse COMP-QMF-REGISTRY** as Library kind owner and CT-07 edge log.

**reuse COMP-QMF-RISK** as Book/BMS shape owner.

**reuse COMP-QMF-DATA** as rooms/splits/journal owner wrapped by QMB data commands.

**reuse COMP-QMN** for node-paper, soak, live, and unforked `run_slice`. Research-paper does not belong here (DEC-0261, DEC-0275).

Candidates refused by id:

- **new experiment-service package / HTTP experiment daemon / Project package / Workspace kind** — DEC-0269, DEC-0284; DEC-0084 stays dead.
- **second backtest governor / `import qmb` from QMA** — DEC-0276, QMA AD-17, DEC-0348.
- **donor engines** (LEAN, StrategyQuant genetic, RoboQuant RQ Engine) — DEC-0013; DEC-0085 and DEC-0086 stay dead.
- **QMA-paper / any QMA execution tool** — DEC-0341, DEC-0275.
- **per-bot paper lane on the node** — DEC-0261.
- **UI contribution SDK this sitting** — GAP-0081, DEC-0280.
- **extending CT-32 or B-4 with workbench fields** — DEC-0283.

Dead list honored: DEC-0084 stays dead, DEC-0085 stays dead, DEC-0086 stays dead, DEC-0376 stays cut, QMA-paper does not exist, `.qml` DSL, complexity gate, paper twins, QuantConnect paper-brokerage as a QMX lane (DEC-0285).

No existing component's authority shrinks. No new dependency edge. No new contract id. CT-32/CT-33/CT-34/CT-47 and CT-40..CT-51 take a `source-inspected` wiring stamp (DEC-0286); remaining connect work is named, not invented as a second design.

## Consequences

Easier: factory units can connect the QMA→QMB door, name projection versus path-dependent analysis, and query the Library without minting a sixth package or a second identity store.

Harder: every public experiment must pick a door (not a payload flag); saved views must carry the canonical JSON body; Book/BMS variants must be complete documents; occupancy is counted only on run invocations; laptop-off cannot be promised from QMB process-per-run.

Foreclosed: an experiment-service package; treating `RecordingQmbDoorTransport` as a working integration; TPE as "strategy generation"; a filtered trade list as Book truth; QMA-paper; Project/Workspace records; filling GAP-0085 nouns or GAP-0063's algorithm in prose; rewriting the PRD in this sitting.

Blast radius (change mode): `COMP-QMB`, `COMP-QML`, `COMP-QMA-CORE`, `COMP-QMA-WIRE`, `COMP-QMA-DAEMON`, `COMP-QMF-REGISTRY`, `COMP-QMF-RISK`, `COMP-QMF-DATA`, `COMP-QMN`, and every doc declaring a dependency on them. Primary edits: this ADR; `docs/components/qmb.md`, `qml.md`, `qma-daemon.md`, `qma-core.md`, `qma-wire.md`, `qmf-registry.md`, `qmf-risk.md`, `qmf-data.md`, `trading-node.md`; CT-22..CT-34 and CT-40..CT-51 wiring comments; constitution annotations; architecture overview and stack; glossary; gap report; traceability; index; AGENTS.md; changelog; SCN-0015/SCN-0016; dated follow-ups on ADR-0017/ADR-0018/ADR-0020; and `_docwork/` (ledger DEC-0269..DEC-0287, gaps GAP-0061/GAP-0062/GAP-0063 plus GAP-0085 note, features FEAT-0033..FEAT-0039, SRC-17/SRC-18). Implementation authorization remains factory-pipeline-only.

Cheap-veto (DEC-0287): A1 connect-wave first / generation trails; A2 work-environment roster UI-open; A3 generated layouts are not preference evidence; A4 Optuna pin stays `4.9.0`; A5 no PRD rewrite (GAP-0061).

## Follow-up — 2026-09-16 QML research expansion (ADR-0023)

This ADR's 2026-09-14 Decision stands as written. The 2026-09-16 QML research expansion ([ADR-0023](ADR-0023-qml-research-expansion.md), DEC-0380 ratified paradigm; package **PROPOSED**) does not mint a sixth COMP and does not add hypotheses to the Library roster.

- **Workbench AD-3 roster unchanged (DEC-0381).** Hypotheses are not Library objects and not registry kinds until CT-33 registration. `strats` stays a refused Library kind.
- **Proposed discovery commentary only (DEC-0403).** Product discovery may federate Knowledge hits as a distinct class; the kind roster is unchanged.
- **No sixth COMP confirmed again (DEC-0402).** Preflight remains reuse of existing applications.
