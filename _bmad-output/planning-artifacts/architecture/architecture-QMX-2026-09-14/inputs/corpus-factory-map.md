# Corpus factory map — strategy-experimentation architecture sitting

Agent-consumable inventory of the ratified `docs/` knowledge base as documentation-factory would surface it. Architecture sitting only; no docs mutation beyond this inputs artifact. Evidence level for all rows below: **documented-design** unless noted. CT-47 and peer QMA contracts are `defined-unwired` in docs while brownfield may exist on `integration@1b451a8` — reconcile at source inspection; do not pick docs or code silently ([`_BRIEF.md`](_BRIEF.md)).

## Compact reuse-or-new table

| Candidate | Class | Own / reuse | Evidence | Why not parallel |
|---|---|---|---|---|
| Strategy template / structure generation | **reuse** (+ optional **extend**) | `COMP-QML` authors; `COMP-QMF-REGISTRY` owns CT-33/CT-34; structure objects via `COMP-QMF-STRUCTURE` (CT-17) | ADR-0018; CT-33/34; DEC-0172–0175 | No second Bot/confluence schema; `.qml` DSL stays dead |
| Candidate databank | **reuse** | `COMP-QMA-DAEMON` staging + artifact store + CT-06 `dev`-zone candidates; `COMP-QMF-REGISTRY` kinds; Experiment Ledger | ADR-0020; CT-47; DEC-0313, DEC-0345 | Candidates are admitted/applied, never promoted by QMA; no parallel databank store |
| Custom research procedure / workflow | **reuse** | `COMP-QMB` validation-ladder + research-surface pure functions; QMA Graph Templates / Routines (CT-49) place work | ADR-0017 B-*; DEC-0169; DEC-0312/0328 | Do not mint a second procedure engine or revive DEC-0084 central service |
| What-if analysis | **reuse** / **connect** | `COMP-QMB` named condition presets + run-config wind tunnel; deferred Simulator UI consumes QMB | ADR-0017; glossary Simulator; DEC-0159, DEC-0088 | Simulator is UI over QMB, never a second backtest path |
| Money-management simulator | **reuse** | `COMP-QMF-RISK` Book/BMS templates (CT-22/27) + dimensional law; `COMP-QMB` wires them in `world=replay` | ADR-0008/0010/0017; DEC-0143–0155 | Book is the money-management container; no twin simulator (DEC-0069 dead) |
| Data quality workbench | **reuse** / **extend** | `COMP-QMF-DATA` rooms/splits/journal; CT-13 `data quality` type; node journals same; CONNECT closed FTR-01 onto it | ADR-0016; ADR-0021 DEC-0266; CT-13 | No eighth journal type; workbench = read models over existing streams |
| Research project / workspace identity | **reuse** | QMA Desk→Quant→ExperimentSpec (CT-47) + Experiment Ledger; QMB workspace defaults layer in run-config | ADR-0020; CT-47; DEC-0160 | Identity is content-addressed ExperimentSpec / Desk, not a new “project” package |
| Notebook kernel lifecycle | **reuse** | QMA **RLM kernel** (Analysis worker persistent interpreter) + `host_request`; QMB research-surface on controlled-room host | ADR-0020 DEC-0334/0313; GAP-0076/0080 | Do not revive bare “kernel”; Jupyter-shaped research is QMB door, not a new runtime |
| Experiment continuation after laptop sleep | **reuse** / **extend** | QMA Routines + continuation budget (CT-49, DEC-0328); remote outbox + `unknown_tail`; JobHandle states | qma-daemon AD-29; DEC-0305/0308 | Unattended continuation already owned; sleep/resume semantics may need one AD if host-suspend is in scope |
| UI extension SDK | **deferred** (not new COMP now) | `COMP-QMA-WIRE` binds now; `qma-ui-contract` stub; GAP-0081 | ADR-0020; DEC-0333; GAP-0081 | Wire first; SDK is its own session — do not invent parallel UI plugin stack |

Classification vocabulary per brief: `reuse | connect | extend | new | undecided`.

---

## Factory state

| Surface | State | Cite |
|---|---|---|
| `_docwork/stage_state.yaml` | `current_stage: 9`; corpus `ratification.status: ratified` 2026-08-21; `final_gate` pass; change-mode through CONNECT 2026-09-11 complete | `_docwork/stage_state.yaml:1-40`, `:263-281` |
| `_docwork/manifest.yaml` | Mode `transcripts`; SRC-01..SRC-16 harvested (foundation→CONNECT); lenses core/data/ops/security/observability/performance/testing/bugs | `_docwork/manifest.yaml:1-140` |
| Docs authority | Operator-ratified design only; implementation = factory pipeline only | `docs/AGENTS.md:15-17`, `docs/constitution.md` L4/L29 |
| Next BMad-exit step | Epics/stories then factory lane — not another docs rebuild | `docs/AGENTS.md:123`, stage_state remaining notes |

---

## Corpus spine (read order)

1. `docs/constitution.md` — L1–L39 (toolbox, default-deny L30, downstream-must-use-QMF L31, human promote L17, money path L36).
2. `docs/AGENTS.md` — ratified vs open, hard rules, architecture preflight (reuse-or-new mandatory).
3. `docs/architecture/dependencies.yaml` — machine graph (roster + QMB/QML/QMN/QMA).
4. `docs/architecture/stack.md` — CPython 3.14, uv, stores, per-application stacks.
5. `docs/gap-report.md` — answered / deferred / open / graveyard.
6. Component specs → contracts → `docs/glossary.md` → ADRs.

---

## Component inventory (one-paragraph roles)

Paths under `docs/components/`.

### QMF roster (public)

| ID | Role |
|---|---|
| **COMP-QMF-CORE** | Definitions-only asset-neutral foundation: money/time/identity/refusals/fp1 (CT-01..05). No broker, loop, backtest, or node runtime (`qmf-core.md`; L13). |
| **COMP-QMF-REGISTRY** | Identity, lineage, registration, promotion skeleton; owns all kinds including CT-33/CT-34 authored via QML (`qmf-registry.md`; DEC-0173). |
| **COMP-QMF-DATA** | Governed bitemporal evidence, rooms, splits, holdout, journal policy (`qmf-data.md`; AD-19..21). |
| **COMP-QMF-INDICATORS** | Two-mode CT-16 indicator protocol; TA-Lib 0.7.1 arithmetic pin (`qmf-indicators.md`; AD-22..24). |
| **COMP-QMF-STRUCTURE** | QMX-owned causal levels/zones/structure under CT-17 lifecycle (`qmf-structure.md`; AD-25). |
| **COMP-QMF-VENUE** | Venue-neutral adapter module: secrets, five-command uncertainty law, CT-18..21; nothing imports it except `qmn.venue` (`qmf-venue.md`; L30). |
| **COMP-QMF-RISK** | Book/BMS binding, admission, exits, paper, controls, SQS, R/dimensional law, CT-22..32 definitions — runs nothing (`qmf-risk.md`; AD-29..41). |

### Internal seams / extensions / externals

| ID | Role |
|---|---|
| **COMP-QMF-DATA-INGEST** | CT-15 source boundary producing CT-10 into qmf-data (`qmf-data-ingest.md`). |
| **COMP-QMF-DATA-STORE** | Physical persistence adapter seam CT-09/11/13/26 (`qmf-data-store.md`). |
| **COMP-QMF-DATA-BACKUP** | CT-14 backup/restore evidence ownership (`qmf-data-backup.md`). |
| **COMP-QMF-CALENDAR-FOREX** | First market-hours calendar extension; own SemVer outside roster (`qmf-calendar-forex.md`). |
| **COMP-CTRADER** | External cTrader Open API authority boundary (`ctrader.md`). |
| **COMP-DUKASCOPY** | External historical source for bounded acquisition (`dukascopy.md`). |
| **COMP-CALENDAR-FEED** | External news-calendar feed (Forex Factory free weekly = sole V1) (`calendar-feed.md`). |
| **COMP-OBJECT-STORAGE** | Off-machine backup bucket destination (`object-storage.md`). |

### Application layer (built ON QMF)

| ID | Role |
|---|---|
| **COMP-QMB** | Experimentation/backtesting library + `qmb` CLI; pure `run()` + impure orchestrator; wires risk contracts in `world=replay`; never imports venue (`qmb.md`; ADR-0017). |
| **COMP-QML** | Bot-authoring library: CT-33/34 helpers, runtime protocol, conformance gate; never venue (`qml.md`; ADR-0018). |
| **COMP-QMN** | Trading node: supervised composition root, `paper\|live`, sole `qmf-venue` wirer at `qmn.venue`, no operator CLI (`trading-node.md`; ADR-0019). CONNECT completes FX paper in place (ADR-0021). |
| **COMP-QMA-CORE** | Definitions-only agentic SDK ports, plugin surface, closed vocabularies; depends only on qmf-core (`qma-core.md`; ADR-0020). |
| **COMP-QMA-WIRE** | Daemon↔UI/worker wire envelope CT-40; `qma-ui-contract` deferred stub (`qma-wire.md`). |
| **COMP-QMA-DAEMON** | Sole writer asyncio runtime: journals, Task Graph, ledgers, RLM kernel supervision, QMB door placement, money-path barrier (`qma-daemon.md`). |

---

## Contracts by owner

Paths under `docs/contracts/`. Wiring status for risk/QMA application contracts is largely `defined-unwired` until factory lanes wire them.

### COMP-QMF-CORE
CT-01 money/quantity · CT-02 time/calendar · CT-03 instrument identity · CT-04 typed refusal · CT-05 version/fingerprint

### COMP-QMF-REGISTRY
CT-06 registration · CT-07 lineage · CT-08 gate evidence · CT-09 registry persistence · **CT-33** Bot definition · **CT-34** confluence

### COMP-QMF-DATA (+ seams)
CT-10 source observation · CT-11 evidence persistence · CT-12 dataset split · CT-13 journal (seven types incl. **data quality**) · CT-14 backup/restore · CT-15 external source adapter · CT-26 store→backup input

### COMP-QMF-INDICATORS / STRUCTURE
CT-16 indicator · CT-17 causal structure

### COMP-QMF-VENUE
CT-18 capabilities · CT-19 command · CT-20 event · CT-21 secret/session

### COMP-QMF-RISK
CT-22 Book template · CT-23 risk-evaluation door · CT-24 Book mode · CT-25 risk journal · CT-27 BMS template · CT-28 Book binding · CT-29 exit record · CT-30 control action · CT-31 control window · CT-32 performance result

### COMP-QMA-CORE (daemon realizes)
CT-40 wire envelope (owned/consumed via WIRE) · CT-41 hook · CT-42 plugin manifest · CT-43 memory · CT-44 knowledge · CT-45 model/broker · CT-46 execution env/job · **CT-47 ExperimentSpec + qmb door** · CT-48 mailbox · CT-49 routine · CT-50 refinement · CT-51 task ledger

CT-35..CT-39 deliberately free (node id block).

---

## ADR anchors (required)

| ADR | Verdict | Owns |
|---|---|---|
| **ADR-0017** QMB | **new COMP-QMB** | Run loop, config compiler, fill/cost ports, sampler, research-surface, orchestrator; refused folding into risk/data/registry |
| **ADR-0018** QML | **new COMP-QML** | Author types, footprint helpers, runtime protocol, conformance; kinds live in registry |
| **ADR-0019** Node | **new COMP-QMN** | Live composition root, doors, soak, `qmn.venue`; reuses QMB `run_slice` unforked |
| **ADR-0020** QMA | **new COMP-QMA-{CORE,WIRE,DAEMON}** | Agentic runtime; money-path = candidates only; UI SDK deferred GAP-0081 |
| **ADR-0021** CONNECT | **reuse COMP-QMN + COMP-QMF-VENUE** | Fail-closed live selection, honest FX paper, encode/`connect_open_api`, FTR-01→CT-13 data quality; no fourth kind |

---

## Glossary pins (experimentation domain)

| Term | Pin | Cite |
|---|---|---|
| **World** | `live \| replay \| simulated`; simulated reserved-unusable until GAP-0048 | `glossary.md` World; DEC-0110/0164 |
| **Experimentation / backtest** | Umbrella vs verification stage; realized by QMB | glossary; DEC-0159 |
| **QMB** | Library + CLI, never engine/kernel | glossary QMB |
| **Bot / Book / BMS** | Authority bot→book→BMS→operator; Book = money-management container | glossary; L36 |
| **Bot journey** | Backtest/paper **outside** node before promote (DEC-0261) | glossary Bot journey |
| **ExperimentSpec** | Content-addressed; QMB door one job/env | glossary; CT-47 |
| **RLM kernel** | QMA-only qualified name for Analysis interpreter | glossary; DEC-0346 |
| **plugin (agentic)** | Desk extension package — QMA scope only | glossary; DEC-0346 |
| **Simulator** | Deferred **UI** consuming QMB; not QMF | glossary Simulator; DEC-0088 |
| **admit / apply / promote** | Memory admit; refinement apply; human promote outside QMA | glossary; DEC-0345 |

---

## Gap surface (architect must not reopen settled, must not ignore deferred)

### Answered (46)
Foundation GAP-0001–0015, 0018–0038; risk 0039–0046; QML 0047; node warm-up **0057** (DEC-0261). No blocking gap open.

### Deferred — backtesting / research
| Gap | Remains | Owner touch |
|---|---|---|
| GAP-0016/0017 | Registration **gate** / attempt **policy** (prevention delivered in QMB) | registry + QMB |
| GAP-0048 | Fidelity taxonomy values + calibration (seams ruled) | QMB |
| GAP-0049 | SR*/search-quality thresholds | QMB + research |

### Deferred — node
GAP-0050 KSA values · 0051 MIS train · 0052 hot-apply · 0053 agent/MCP door · 0054 OS confinement · 0055 second VPS · 0056 fill sim in replay.

### Open non-blocking
**GAP-0058** single-machine placement — design owed by one-shot architecture increment (DEC-0262).

### CONNECT deferred
GAP-0059 FTR-02 · GAP-0060 live source token.

### QMA deferred (22) — high relevance
| Gap | Topic |
|---|---|
| **GAP-0076** | RLM kernel performance envelope |
| **GAP-0080** | RLM beyond Analysis / depth >2 |
| **GAP-0081** | **UI presentation / extension SDK / qma-ui-contract** |
| GAP-0084 | Mission Template vs Graph Template |
| GAP-0085 | Typed strategy-mechanism decomposition (QML/registry own; QMA carries candidates) |

### Graveyard (do not revive)
DEC-0084 central backtesting service · DEC-0085/0086 donor engines · DEC-0069 paper twins · DEC-0088 Simulator as QMF deliverable (product UI later) · QMA Cut DEC-0360–0379 (foreign agent runtimes, capability solver, execution tool “paper only”, git-branch-per-parameter, …).

---

## Dependency / stack snapshot

- **Roster default-deny:** only `qmf-registry → qmf-data`; nothing imports venue/risk inside roster (`dependencies.yaml`; L30).
- **Applications:** QMB/QML/QMA may consume risk (and venue-free) at composition roots; **only** `COMP-QMN.qmn.venue` imports venue.
- **QMA→QMB:** runtime door, **not** package import (`dependencies.yaml` COMP-QMA-DAEMON notes; CT-47).
- **Runtime:** CPython 3.14; stores Parquet/DuckDB/SQLite/JSONL; QMB pins click 8.4.2 + optuna 4.9.0; QMA asyncio daemon + websockets (`stack.md`).

---

## Candidate deep-dives (reuse-or-new proofs)

### 1. Strategy template / structure generation
**reuse COMP-QML + COMP-QMF-REGISTRY (+ COMP-QMF-STRUCTURE for chart objects).**  
Governed strategy shape is already CT-33 Bot definition + CT-34 confluence + strategy-family key (`ADR-0018`; `qml.md`). Structure generation for levels/zones is CT-17 under `COMP-QMF-STRUCTURE`, not a bot schema. Plain-Python authoring remains legal; graduation is L33.  
**Mismatch if “new”:** second declaration language (`.qml` dead DEC-0172) or a template store outside registry kinds.  
**Open:** GAP-0085 typed mechanism decomposition — revisit may **extend** handles, not mint parallel COMP.  
**AD needed?** Only if operator wants a new registry kind beyond CT-33/34; else Deferred under GAP-0085.

### 2. Candidate databank
**reuse COMP-QMA-DAEMON + COMP-QMF-REGISTRY.**  
Candidates are content-addressed `dev`-zone artifacts with lineage (CT-47 / DEC-0313); staging store + admission gate (CT-50/43); Experiment Ledger is the scientist notebook. Verbs: admit/apply — never promote (DEC-0345).  
**Mismatch if “new”:** a second durable candidate DB bypassing journal/artifact store or granting QMA promote.  
**Missing:** wiring (`defined-unwired`), not function shape.  
**AD needed?** No for ownership; maybe Deferred for UX naming of “databank”.

### 3. Custom research procedure / workflow
**reuse COMP-QMB (procedures) + connect COMP-QMA-DAEMON (orchestration).**  
QMB owns validation-ladder versioned procedures, sampler, research-surface pure functions (`qmb.md` B-1/B-8/B-*; DEC-0169). QMA owns Graph Templates, Task Graph, Routines (CT-49) that **place** one `qmb` job per env — never a second backtest engine (DEC-0348).  
**Mismatch if “new”:** procedure runtime inside QMA or revived DEC-0084 service.  
**AD needed?** Only if a procedure kind must become a registry artifact with new CT; else extend QMB library functions.

### 4. What-if analysis
**reuse COMP-QMB; connect deferred Simulator UI.**  
Wind tunnel = one resolved run-config; named condition presets are config fragments (`qmb.md` B-3; DEC-0160). Monte Carlo / significance = ledgered `trial|replicate` roles (DEC-0162). Simulator glossary: separate deferred UI consuming QMB (DEC-0159/0088).  
**Mismatch if “new”:** interactive what-if engine with its own fill model (competes with GAP-0048 ports).  
**AD needed?** Product-UI sitting for Simulator; not this architecture for a new COMP.

### 5. Money-management simulator
**reuse COMP-QMF-RISK definitions + COMP-QMB replay wiring.**  
Book is the money-management container (glossary Book; CT-22 money_rules, admission_bar, exit_policy). QMB mints `world=replay` bindings and consumes sizing/R/exit verbatim. Paper twins dead (DEC-0069).  
**Mismatch if “new”:** standalone MM simulator duplicating Book/BMS.  
**Gap:** GAP-0048 fidelity before trusting replay as money-path evidence.  
**AD needed?** No new COMP; calibration content sitting for GAP-0048.

### 6. Data quality workbench
**reuse COMP-QMF-DATA (+ node/CONNECT producers); extend = UI/read-model only.**  
CT-13 already has `data quality` among seven journal types; folds alarm and journal DQ (`glossary` Journal; risk fold law). CONNECT maps position/balance read-back → CT-13 `data quality` (ADR-0021 DEC-0266) — **no eighth type**.  
**Mismatch if “new”:** parallel DQ catalog or observation-as-journal-type (rejected).  
**AD needed?** Only if workbench needs new query contracts; else UI over existing streams (may ride GAP-0081 later).

### 7. Research project / workspace identity
**reuse QMA ExperimentSpec + Desk/Quant ontology; QMB workspace defaults.**  
CT-47 ExperimentSpec is content-addressed identity (code_ref / resolved_config_ref / data_ref / env / seed / lineage). Desk is organizational workspace unit (DEC-0306). QMB compile precedence includes workspace defaults (DEC-0160).  
**Mismatch if “new”:** git-branch-per-project identity (Cut DEC-0376) or COMP-QMB-owned “project” service.  
**AD needed?** If “research project” must be a first-class registry kind distinct from ExperimentSpec — otherwise **reuse**.

### 8. Notebook kernel lifecycle
**reuse COMP-QMA-DAEMON RLM kernel + COMP-QMB research-surface.**  
RLM kernel = Analysis worker persistent Python interpreter over `host_request` (glossary; DEC-0313/0334). QMB exposes research-surface pure functions on controlled-room host (`qmb.md` authority May). Parent ban: bare “kernel” retired except qualified RLM (DEC-0346).  
**Mismatch if “new”:** second notebook runtime or Jupyter kernel package as QMF roster.  
**Gaps:** GAP-0076 envelope; GAP-0080 scope.  
**AD needed?** Lifecycle specifics (start/stop/snapshot/restore) if not already implied by JobHandle + RLM — prefer **extend** daemon behavior under existing ADs before new COMP.

### 9. Experiment continuation after laptop sleep
**reuse COMP-QMA-DAEMON scheduler/continuation; extend if host-suspend is explicit.**  
Unattended continuation: Routines, continuation budget/escalation (DEC-0328; CT-49). Remote outbox + `unknown_tail` on lost env (DEC-0305/0308). Quiet hours defer wakes, don’t pause in-flight (qma-daemon). Daemon workstation-default (DEC-0336).  
**Missing function?** Explicit “laptop sleep / OS suspend / resume experiment” may be underspecified vs Routine miss-fire (“recorded, not replayed”).  
**Class:** **reuse** core mechanism; **extend** with one AD if sleep-resume durability is in product scope; else Deferred ops note.  
**Do not** invent a QMB daemon for this.

### 10. UI extension SDK
**deferred — reuse COMP-QMA-WIRE now; do not mint COMP.**  
GAP-0081: UI presentation architecture, Rust extension tech, contribution points, packaging, `qma-ui-contract` beyond stub — own session; wire + variables bind now (DEC-0333).  
**Mismatch if “new” now:** parallel plugin SDK fighting CT-42 / wire principal classes.  
**AD needed?** Yes — **later** UI sitting; this sitting should **not** design SDK internals.

---

## Closing synthesis (brief contract)

### (1) What already exists
Full QMF toolbox + risk/venue contracts; QMB experimentation host; QML bot authoring; QMN live/paper node; QMA agentic triad with ExperimentSpec/QMB door, RLM kernel, Routines/continuation; CONNECT reuse path for honest FX paper; CT-13 data-quality journal type; Simulator named as deferred UI over QMB.

### (2) Missing wiring vs missing function
| Area | Mostly |
|---|---|
| Risk CT-22..32, QMA CT-40..51, CT-47 | **Missing wiring** (`defined-unwired`) |
| GAP-0048 taxonomy/calibration, GAP-0049 thresholds, GAP-0016/17 gate policy | **Missing function/content** (seams exist) |
| UI extension SDK (GAP-0081) | **Deferred function** |
| Laptop-sleep resume | **Possible small gap** on host-suspend semantics — mechanism (continuation/outbox) exists |
| Strategy “templates” | **Function exists** as CT-33/34; generation UX may be missing |

### (3) Recommended architectural ownership
Keep experimentation gravity in **COMP-QMB**; authoring in **COMP-QML**; money rules in **COMP-QMF-RISK**; agent orchestration and candidate identity in **COMP-QMA-***; live money in **COMP-QMN**; evidence/DQ in **COMP-QMF-DATA**. Prefer **reuse/connect/extend**. Mint **new COMP** only when preflight shows an authority boundary no existing COMP can own (AGENTS.md architecture preflight).

### (4) Open questions — AD vs Deferred
| Question | Route |
|---|---|
| Fidelity values / fill calibration | **Deferred** GAP-0048 sitting (not silent invent) |
| Search-quality / attempt budget policy | **Deferred** GAP-0049 (+ 0016/0017) |
| UI extension SDK surfaces | **Deferred** GAP-0081 (own AD later) |
| RLM perf / multi-desk RLM | **Deferred** GAP-0076/0080 |
| Strategy-mechanism typed decomposition | **Deferred** GAP-0085 (extend QML/registry) |
| Explicit OS-sleep experiment resume | **AD if in scope**; else ops Deferred |
| “Research project” as kind ≠ ExperimentSpec | **AD only if** ExperimentSpec proven insufficient |
| Single-machine co-location with agentic | **Open** GAP-0058 one-shot increment |
| Simulator what-if UX | Product UI later; **reuse QMB** — no COMP |

---

## Source index (primary)

- `docs/index.md`, `docs/AGENTS.md`, `docs/constitution.md`
- `docs/architecture/dependencies.yaml`, `docs/architecture/stack.md`
- `docs/gap-report.md`, `docs/glossary.md`
- `docs/components/*.md`, `docs/contracts/ct-*.yaml`
- `docs/decisions/ADR-0017` … `ADR-0021`
- `_docwork/manifest.yaml`, `_docwork/stage_state.yaml`
- Brief: `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-14/inputs/_BRIEF.md`
