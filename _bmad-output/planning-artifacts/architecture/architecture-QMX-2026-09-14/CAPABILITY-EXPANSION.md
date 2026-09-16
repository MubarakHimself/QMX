---
name: QMX Strategy Experimentation — capability expansion
type: architecture-companion
status: draft
created: '2026-09-14'
updated: '2026-09-14'
spine: ARCHITECTURE-SPINE.md
audience: operator, later documentation-factory, later UI (Codex), later epics
---

# Capability expansion — what QMX already is, and what to grow

This is the human-facing companion to `ARCHITECTURE-SPINE.md`. The spine is the build contract. This file is the account: existing support, recommended expansion, dependencies, and the UI-facing objects — without prescribing layout.

Planning checkout: `main` `430fb7d`. Implementation inspected: `integration` `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2`. Class/test existence is not runtime proof. Generated layouts and reactions to them are not preference evidence.

## 1. What QMX already supports

QMX is already a quantitative workbench in **libraries**, not a missing engine. The expansion is mostly **connect and name**, not rebuild.

| Layer | Already there (source-inspected on integration) | Not there / not proven |
| --- | --- | --- |
| **QMF** | Exact money/time/fp1/refusals; registry kinds including bot/Book/BMS/result; data rooms, splits, journals, CT-15 ingest | Risk contracts still stamped `defined-unwired` in YAML while value types exist — composition-root wiring, not missing shapes |
| **QMB** | Event-slice loop; config compiler; pure `run()` vs orchestrator evidence; Python API + CLI; data download/verify/gap-check/catalog/generate; TPE optimize; sweeps; walk-forward / MC / significance as library; CT-32 + chart series; QML host adapter; plain-Python `SliceHandler` | MCP door unshipped; CLI does not yet expose robustness or full sweep batch/rank; no What-if projection function; no structure generator |
| **QML** | Two-artifact bot (CT-33 + logic); ungoverned tunnel (`admit_ungoverned_tunnel`, `plain_research_bot`); conformance ≠ performance; parameter spaces; producer templates | No structure/template generation; host CT-06 mint is composition-root; GAP-0085 mechanism nouns absent |
| **QMA** | Ontology, mission/task graph, plugins/skills/routines, ExperimentSpec + Experiment Ledger, QMB door **law**, money-path deny (paper included), continuation/outbox libraries, sqlite writer | Default QMB transport **records** invocations and does not spawn `qmb`; no composed asyncio listener process found; `qma-ui-contract` is a stub; knowledge search is literal |
| **QMN** | Unforked `run_slice`; Book-level demo paper; promotion/activation; evidence HTTP vs powers socket; refuses ungoverned seats and per-bot paper | Research-paper does not belong here (DEC-0261) |

**Stale docs to reconcile later (not a design fork):** CT-32/33/34/47 (and CT-40..51) still say `defined-unwired` / “no code exists” while matching packages exist on integration.

## 2. Durable intent (settled vs open)

Settled: QMX is a strategy-experimentation workbench (research through operations). Unattended trading is one mode. Humans and agents share versioned artifacts. No compulsory wizard. Ordinary Python, notebooks, QML, and QMB coexist. Shared Library is one identity. STRATS is an input collection. Extensibility must reach people who will not read this source. Paper before promotion. Only a human promotes live.

Open (this spine answers with ADs, not screens): parameter search vs structure generation (AD-4 write path); What-if filter vs path-dependent rerun (AD-5 saved views, no size rescale); three “paper” nouns (AD-7); laptop-off host (AD-10); Book/BMS candidate boundary (AD-6 complete documents); Project vs Workspace (AD-16: ExperimentSpec, no Project kind).

## 3. Donor mechanisms kept vs refused

Borrowed as **shapes**:

| Donor | Keep | Refuse |
| --- | --- | --- |
| StrategyQuant | Fixed vs variable slots; databank-as-query; Custom Projects as staged procedures; robustness ladder (already QMB) | Random/genetic **engine**; building-block DSL; MT export pipeline |
| QuantAnalyzer | Named What-if conditions; snippet-like extension of **projection** filters; MM as Book-policy comparison | Treating filtered trades as path-dependent truth; “optimal portfolio” vendor claim |
| QuantDataManager | Coverage/gap/quality review; derived datasets with lineage | Silent clone auto-update; CDN/verified-download as QMX product claims; a second store |
| QuantConnect / Lean CLI | Project continuity as ExperimentSpec; notebooks beside code; CLI as agent-facing door (already QMB’s Lean-CLI inspiration); compute placement as ExecutionEnvironment | Research Pipeline kanban as required lifecycle; paper brokerage as QMX paper; Lean engine |
| OpenResearch | Lineage + parallel bounded work + local/remote compute | Git worktree per parameter (Cut DEC-0376); adopting the product |
| Delphi | Indexed retrieval as a future KnowledgeSource adapter | PostgreSQL+pgvector as a required store now |
| RoboQuant.dev | Visible tool work; idea-to-code assistance (QMA already) | RQ Engine, L2-as-product, “survives tab close” live runtime (node already owns live) |

## 4. Recommended expansion (coherent, not a single screen)

Four architecture areas, not a funnel. Epics may start in any area once dependencies below are respected.

### A. Connect what already exists (highest leverage)

1. Real QMA→QMB CLI transport (AD-8).
2. Persist ExperimentSpec/ledger through the daemon writer (AD-8).
3. CLI/API parity for robustness and sweep batch/rank (missing wiring).
4. Library query projections over fp1 kinds (AD-3, AD-14).
5. Derive `workbench_lane` from the door (AD-2); do not add a payload flag or extend CT-32.

### B. Name the analysis methods (AD-5, AD-6, AD-15)

1. Projection What-if over CT-29/CT-32 (hours/days/max-trades class).
2. Path-dependent re-run for Book/BMS/sizing variants.
3. Claim-class on every published analysis.

### C. Authoring and generation (AD-4)

1. Keep parameter search as QMB.
2. If/when generation ships: QML authors candidates; QMB runs; QMA lineages. Do not start a generator inside QMB.

### D. Coordination and continuation (AD-9, AD-10, AD-11)

1. Graph Templates / Skills / Routines as the Custom-Project equivalent.
2. Daemon (or remote env) off the sleeping laptop if laptop-off is promised.
3. Notebooks import QMB; managed interpreter = ExecutionEnvironment.

Do **not** implement UI, Penpot, or a new COMP in this expansion.

## 5. UI-facing shared objects (no layout)

Codex/UI can bind to these without inheriting a department roster.

**Identities (fp1):** Bot definition, Book, BMS, binding, split, observation window, CT-32 result, ExperimentSpec (coordinated only). Logic source-manifests ride CT-33. Graph Templates, Skills, Routines, saved views, and JobHandles are not Library kinds.

**Operations:** `run` ungoverned; `spawn_governed`; `optimize.ask/tell`; `sweep`; robustness rungs; `data.download|verify|gap-check|catalog`; `analysis.project`; `analysis.rerun`; `procedure.start`; `experiment.register`; `candidate.admit`; `promotion` (human, outside QMA).

**Queries:** Library search by kind+fp1; candidate-set view; ledger merge; gap/quality projection; as-of registry.

**Lifecycle:** job states from QMB orchestrator and QMA JobHandle (`unknown` included); tab-close ≠ cancel; laptop-sleep ≠ abort if AD-10 host is up.

**Events:** CT-13 journal types; QMA wire events; progress/failure on JobHandle.

**Extension points visible to a non-source user:** ui-editable variables; drop-in Python logic package; install a QMA desk pack. Not: UI widgets (GAP-0081).

## 6. Dependencies and suggested epic clustering

Not a required sequence — a constraint graph.

| Cluster | Depends on | Notes |
| --- | --- | --- |
| Door + ExperimentSpec persistence | existing QMA/QMB | Unlocks coordinated experiments |
| Library projections + candidate queries | registry + ledger | Unlocks shared Library UI later |
| Named analysis methods | CT-32/CT-29 streams | Unlocks What-if/MM without a new engine |
| CLI coverage of robustness/sweeps | existing library | Wiring |
| Procedure Graph Templates | door + QMB rungs | Custom-Project shape |
| Continuation host config | QMA daemon composition | Laptop-off |
| Structure generation | QML + AD-4 | Can trail connect-wave |
| UI contribution SDK | GAP-0081 | After daemon API is live |
| GAP-0048 taxonomy | own sitting | Blocks live-gating of replay |

PRD today covers QMB FRs (FR-036..046) and QML FRs; it does **not** yet state ExperimentSpec, analysis methods, generation-vs-search, or procedures. Update the existing PRD; do not rewrite it.

## 7. Assumptions and leftover questions

`[ASSUMPTION]` Connect-wave (A+B+D door/projections/analysis naming) is the coherent first implementation area; generation can trail without blocking Library or What-if.

`[ASSUMPTION]` Work-environment roster stays UI-open (AD-16 aliases only).

Open: generator algorithm; concrete always-on host; PRD FR addenda. None of these blocks writing epics for connect-wave.

Conflicts with parents: none. CT `defined-unwired` vs source is documentation drift, recorded for documentation-factory, not an AD override.
