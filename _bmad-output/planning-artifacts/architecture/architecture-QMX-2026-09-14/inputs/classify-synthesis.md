# Classify synthesis — QMX strategy-experimentation feature spine

**Sitting:** architecture only (2026-09-14).  
**Checkout:** `main` (planning). **Product inspected:** `integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2`.  
**Altitude:** feature. **Stack:** inherited pins only — no new framework.  
**Parents (read-only):** QMF AD-1..41, QMB B-1..B-15, QML QL-1..QL-10, NODE TN-1..TN-25, QMA AD-1..AD-29, CONNECT AD-1..AD-5.

Evidence: `user-intent` | `documented-design` | `source-inspected`. Class/test existence is not end-to-end proof. Contract YAML `defined-unwired` / “no code exists” is stale where matching integration source exists.

This file is the classifier. It names the paradigm and the **at-most-16 invariants two factory epics could otherwise ship incompatibly**. It does not prescribe UI layout, mint a sixth application, or weaken a parent AD.

## Compact table

| Item | Verdict |
| --- | --- |
| Paradigm | **Workbench composition over hexagonal libraries** — one fingerprint identity, three door-derived experiment lanes, two named analysis methods |
| New framework / sixth COMP | **Forbidden** (DEC-0084 stays dead) |
| Invariants this sitting | **16** (joints two epics would otherwise fork) |
| Dominant class | **reuse** library function; **connect** doors/persistence/projections; **extend** named analysis + QML generation later; **new** only for structure generation (function absent) |
| Parent AD conflicts that require weakening | **None** |
| Docs vs source | CT-32/33/34/47 and CT-40..51 `defined-unwired` while packages exist — documentation-factory, not a design fork |

| Capability | Class | Owner |
| --- | --- | --- |
| Event-slice backtest, optimize, sweep, robustness, CT-32 | reuse | COMP-QMB |
| Data download/verify/gap-check/catalog/generate | reuse | COMP-QMB fronts qmf-data |
| Ungoverned ordinary Python in the tunnel | reuse | QML `admit_ungoverned_tunnel` + QMB `run()` |
| QMA mission/task/plugin/skill/routine | reuse | COMP-QMA-* |
| QMA→QMB real CLI door + composed daemon + persist ExperimentSpec | connect | COMP-QMA-DAEMON |
| Shared Library / candidate databank / research undertaking | connect | projections over existing fp1 kinds |
| Custom-project procedures | connect | QMA Graph Templates placing QMB via the door |
| Notebook as research host | connect | `import qmb` + Analysis RLM kernel |
| What-if trade-list filter | extend | COMP-QMB `analysis.project` (saved view, not CT-32) |
| Path-dependent What-if / MM / Book policy | reuse via re-run | COMP-QMB tunnel + qmf-risk shapes |
| Structure generation (SQ templates, GAP-0085) | new (function) | COMP-QML authors; QMB runs; QMA references |
| Research-paper before promotion | connect | QMB governed replay; hub-inbox last mile |
| Laptop-off continuation | connect | always-on `qma-daemon` (not QMB, not worker+outbox) |
| UI contribution SDK | deferred | GAP-0081 |
| GAP-0048/0049/0016/0017 content | deferred | parent revisit conditions stand |

---

## Paradigm

**Workbench composition over hexagonal libraries.**

QMF remains the contract-hub toolbox. QMB, QML, QMA, and QMN remain the four application-layer products. This sitting does not mint a fifth runtime, a sixth package, a donor engine, or a QuantConnect Project service.

The workbench is **projections, doors, and procedures** over those products:

- **One identity** — existing `fp1` kinds. Library tabs, databanks, and “projects” are queries/joins, not stores.
- **Three experiment lanes** — selected by **which door is called** (ungoverned values / governed orchestrator / coordinated CT-47), never by a payload flag.
- **Two named analysis methods** — projection (saved view over a cited stream) vs path-dependent (new resolved run-config through the QMB tunnel).

Changing test conditions still means changing config. Coordinating work still means QMA missions. Authoring still means QML or ordinary Python. Live money still means the node and a human.

Donor mechanisms (StrategyQuant Custom Projects, QuantAnalyzer What-if, QuantDataManager quality, QuantConnect project continuity, OpenResearch lineage/compute) transfer as **shapes**. Donor engines, paper brokerages, genetic structure runtimes, and `config.json` Project identity are refused.

---

## Invariants

Each row is a joint two independently-built epics would otherwise choose incompatibly. Parent ADs remain in force; these do not reopen them.

### I-1 — Workbench is not a sixth application

- **Binds:** all expansion units, factory preflight
- **Prevents:** a COMP-EXP / HTTP experiment service / second identity store; three owners of one query because “connect” was treated as a home
- **Rule:** Every new capability names **exactly one** existing `COMP-*` owner. `reuse | connect | extend | new` classify the work; they are not homes. This sitting’s owners: QMA→QMB CLI transport and ExperimentSpec persistence → `COMP-QMA-DAEMON`; named analysis functions, CLI coverage of robustness/sweep, data commands → `COMP-QMB`; generation authoring → `COMP-QML`; registry kinds and CT-07 → `COMP-QMF-REGISTRY`; risk shapes → `COMP-QMF-RISK`; data rooms → `COMP-QMF-DATA`. Minting a new application package, a permanent experiment daemon besides `qma-daemon`, or a durable store other than the already-declared QMF roster stores, QMB ledger fragments, and QMA daemon stores, is a spine amendment. DEC-0084 stays dead.

### I-2 — Three door-derived experiment lanes

- **Binds:** QMB, QMA, notebooks, UI backends, agents
- **Prevents:** `lane` as a caller-declared payload flag; ExperimentSpec / CT-32 / returned values as three identities for one experiment; ungoverned values becoming Library objects
- **Rule:** Exactly three lanes, selected by **which door is called**, never by a flag on a payload. **ungoverned** — `qmb.run()` / ordinary Python / `import qml` on a controlled-room host; returns values; writes no QMB ledger line, no CT-32 registry record, no ExperimentSpec; it is not a Library object; graduation is an explicit later orchestrator spawn (L33). **governed** — QMB orchestrator spawn **not** placed by the CT-47 door (CLI/API `spawn_governed`, including path-dependent `analysis.rerun`); one QMB ledger line, one CT-32; no ExperimentSpec. **coordinated** — QMA Backtesting Service places at most one `qmb` CLI/MCP invocation per ExecutionEnvironment and never `import qmb`; requires a registered ExperimentSpec; the QMB ledger line and CT-32 are the evidence (`_ref` from the Experiment Ledger); QMA does not copy them. `lane` is derived from the door. CT-32 is not extended with `lane`. ExperimentSpec exists only in the coordinated lane. A fourth call path is a spine amendment.

### I-3 — Library identity is existing fp1 kinds; a research undertaking is a join

- **Binds:** Shared Library, work environments, UI, QMA handles, F12
- **Prevents:** one bot/result as three records; a STRATS-shaped second store; a COMP-PROJECT / QuantConnect `config.json` identity; work-environment as a CT-06 kind; Graph Templates listed as Library `fp1`
- **Rule:** Shared Library objects are **exactly** these existing kinds, cited by `fp1`: CT-33 bot, CT-34 confluence, strategy-family (CT-06 metadata), CT-22 Book, CT-27 BMS, CT-28 binding, CT-12 split, CT-10 observation, CT-32 result, CT-47 ExperimentSpec (**coordinated only**). Logic source-manifests are cited from CT-33, not a sibling kind. A **research undertaking** is the join of CT-33 + logic-manifest + ExperimentSpec + Experiment Ledger + resolved run-config; UI may name a workspace; identity stays those fingerprints. Work-environment tabs and display aliases are UX over those fingerprints — not CT-46 and not a kind. `study_fp` is cited from ledger labels, never re-kinded. STRATS is a KnowledgeSource corpus (QMA AD-19); it does not write registry kinds. Graph Templates, Skills, Routines, JobHandles, saved views, and QMA staging are **not** Library kinds. A new Project / Workspace / Library kind is a spine amendment.

### I-4 — Generation is not search; QML writes, QMA only references

- **Binds:** F01, GAP-0085, QML, QMB optimize, QMA ExperimentSpec
- **Prevents:** TPE / `propose_generation` sold as strategy generation; a generator inside QMB’s tunnel; QMA assembling CT-33 JSON or filling RandomCondition slots; two mint paths for one bot
- **Rule:** **Search** varies declared CT-33 parameters (same bot `fp1`; assignment is a run-spec override; QMB optimize/sweep, B-8). **Generation**, if built, authors **new** CT-33/CT-34 content and/or logic-source **bytes via QML**; the QML/host composition root mints the CT-06 envelope. QMA `StrategyHandle` may only (1) reference an already-fingerprinted registry record and (2) register those bytes as a `dev`-zone candidate with a QMA `origin` field and a CT-07 predecessor edge. QMA never assembles CT-33/CT-34 JSON, never mints GAP-0085 mechanism nouns, never fills structure slots. TPE `propose_generation` is a batch index. `qmb data generate` is synthetic series (`world=simulated`, L20). CT-17 market structure is a different noun. Placeholder-fill vs Python-logic synthesis stays a later QML increment; neither ships as a QMA step. SQ RandomCondition is a donor shape, not a schema to copy.

### I-5 — Two named analysis methods with pinned artifact identity

- **Binds:** F05 What-if, F08 equity-control, result comparison, UI, agents, COMP-QMB
- **Prevents:** a filtered trade list treated as a Book/BMS counterfactual; `starting_capital` rescale as projection in one epic and re-run in another; analysis artifact as a new CT-32 vs a QMA sqlite view vs a new registry kind; F07 synthetic portfolios sneaking in as projection
- **Rule:** Exactly two methods, owned once by **COMP-QMB**. **Projection** is `analysis.project` over **one** cited CT-32 and its CT-29/CT-13 stream. Output is a **saved view**, not a CT-32: identity is `fp1` of the canonical JSON `{method: projection, source_ct32, source_ct29, predicate, as_of}`. The view stores the predicate and cites, never a copied trade list or rescaled measure set. Claim-class is always `projection`; never admission evidence. **Path-dependent** is a new QMB run through the tunnel (new resolved run-config: Book/BMS fragments, fill/cost/financing ports, `starting_capital`). Its canonical artifact **is** the new CT-32. `analysis_method` and `lane` are **not** CT-32 fields (CT-32 stays parent-shaped). Changes to `starting_capital`, Book/BMS fragments, or execution ports are always path-dependent. Hours/days/max-trades filters and display-only equity rescale that does **not** change the binding seed are projection. `compare_runs` is a readout of cited CT-32 fields, not an analysis method, and stamps nothing. Combining two bots’ equity/trade streams into a synthetic portfolio is **refused** here; F07 stays deferred. `analysis.project` / `analysis.rerun` exist once in the QMB library; doors wrap them (B-1). QMA may **call** those functions and persist refs; it may not reimplement the filter.

### I-6 — Book/BMS variants are complete candidates plus replay

- **Binds:** F06 money-management, Book/BMS assistance, CT-47 `money_path_relevant`
- **Prevents:** trade-list rescaling posing as Book simulation; QMA filling unset risk fields; patch records that replay cannot cite
- **Rule:** A proposed Book/BMS version is a **complete** new fingerprinted CT-22/CT-27 document in the registry `dev` zone (not a patch record). Path-dependent evaluation is a QMB governed or coordinated replay citing that fingerprint (I-2, I-5). QMA may emit it only as a `money_path_relevant` candidate whose `approval_request` carries the field-level diff against the predecessor; QMA never fills an unset money-path field. Shape owner remains QMF Risk; mint remains the composition-root pattern (same as CT-33). Named condition presets (stress-spread, etc.) are B-3 config fragments and are path-dependent by construction — they are not QuantAnalyzer What-if.

### I-7 — Paper trinity; research-paper is a display alias

- **Binds:** pre-promotion paper, QMA, QMB, QMN, DEC-0261, CONNECT AD-2
- **Prevents:** QuantConnect paper-brokerage, node soak, and QMB replay sharing one “paper” noun; Book paper-mode fragments compiled into QMB; a paper-performance gate on live
- **Rule:** **research-paper** is a **display alias** for QMB governed (or coordinated) replay evidence produced **outside** the node before promotion. It is `world=replay`, never Book paper-mode, never `world=live`, never a CT-32 / lane / claim-class extension. **node-paper** remains TN-9 / CONNECT AD-2: Book-level demo routing + soak/demotion (`role=demo`, `world=live`); no per-bot paper lane. **QMA-paper** does not exist — no execution tool at any account role. Paper-testing-before-promotion is **workflow**, not an AD-32 paper-performance gate (replay cannot gate live; paper roles cannot gate live). Promotion remains a human act outside QMA onto the node.

### I-8 — The QMA→QMB door is connect; two ledgers stay two

- **Binds:** CT-47, `analysis-backtest` plugin, Experiment Ledger, JobHandle
- **Prevents:** a second backtest governor; `import qmb` from QMA; treating `RecordingQmbDoorTransport` as a working integration; merging the QMB run ledger into daemon sqlite; two CT-07 writers for one successor
- **Rule:** Keep the route Agent → QMA backtest tool → Backtesting Service → `qmb` CLI (MCP later) → QMB. Replace `RecordingQmbDoorTransport` with a real CLI transport. **Compose one long-running `qma-daemon` process** (listener + single sqlite writer + pack roster + scheduler). Persist **ExperimentSpec, the QMA Experiment Ledger, and ExperimentSpec CT-07 successor edges** through the daemon journal / sqlite writer. The QMB run ledger remains QMB JSONL, reached by `_ref`, never copied, never merged (QMA AD-6). QMB does not write ExperimentSpec edges. Occupancy: one `qmb` **invocation** per ExecutionEnvironment; QMB’s process-per-run children inside that invocation are not additional QMA jobs; data / analysis / robustness CLI invocations **are** `qmb` jobs and do consume occupancy.

### I-9 — Procedures live in QMA; steps are door placements

- **Binds:** F03 Custom Projects, reusable workflows, agents
- **Prevents:** a workflow engine inside QMB; a compulsory research→backtest→paper wizard; in-process `import qmb` from QMA workers vs CLI door (two occupancy/cancel stories); a Graph Template treated as an ExperimentSpec
- **Rule:** Reusable procedures are QMA Graph Templates, Skills, and operator Routines. QMB does not grow a task graph. A step that names a QMB capability (backtest, optimize, sweep, robustness, data, `analysis.project`, `analysis.rerun`) is **placed through the CT-47 `qmb` door as one CLI/MCP invocation**. The daemon, every plugin, and every QMA worker image never `import qmb`. Composition is non-linear: any step in the intent set may be the first door placement. One Graph Template instantiation is one Mission. Each door step that changes resolved-config is an ExperimentSpec successor (`create_successor` + CT-07 `branches-from`); the procedure is not itself an ExperimentSpec. SQ Custom Projects remain a donor shape, not a product to clone.

### I-10 — Continuation is a reachable always-on daemon

- **Binds:** laptop-off, remote workers, QMA scheduler, cancel
- **Prevents:** QMB process-per-run sold as unattended continuation; remote worker + outbox substituting for the daemon; parking `qma-daemon` on the trading-node VPS; competing cancel writers
- **Rule:** Laptop-off unattended work requires a **reachable always-on `qma-daemon`** (journal writer, scheduler, dispatcher) that does **not** live only on the sleeping laptop and is **not** placed on the trading-node VPS (QMA AD-28). Remote ExecutionEnvironments plus the durable outbox preserve **in-flight job evidence** across partition; they do not dispatch the next Task, fire Routines, or replace the daemon. QMB orchestrator lifetime remains the **job**. Coordinated cancel authority is `JobHandle.cancel` only; the door maps it to QMB abort and the QMB ledger writes `aborted`. Governed-without-QMA cancel is QMB abort only. Ungoverned cancel is process death and writes nothing. UI tab-close remains a no-op. Missed Routine fires are recorded, not auto-replayed (`AUTOMATIC_BACKFILL=False`). Lost supervisor / unreachable env / daemon restart → JobHandle `unknown`, never inferred `failed`. Host SKU is operator-recorded QMA AD-25/AD-26 config, not a new COMP.

### I-11 — Notebooks import the library; product-owned interpreter is the RLM kernel

- **Binds:** F13, B-9, QMA ExecutionEnvironment / RLM kernel
- **Prevents:** a Jupyter product inside QMB; a `kind=notebook` env forking the Analysis RLM kernel; reviving the banned bare “kernel” name outside QMA
- **Rule:** Exploratory notebooks `import qmb` / `import qml` on a controlled-room host (B-9). Product-owned managed interpreter **is** the existing Analysis RLM kernel ExecutionEnvironment (QMA AD-14). External Jupyter remains legal as ungoverned `import qmb` with **no** product-owned lifecycle. It is not a QMB module and not a new COMP.

### I-12 — Extensibility ladder; QMB adapters are closed catalogs

- **Binds:** user-facing extension, plugins, config, UI later
- **Prevents:** promising a UI plugin SDK that is GAP-0081; treating source-only catalog amendment as the product; user `FillPort` drop-ins / ambient discovery
- **Rule:** Four rungs, in order: (1) ui-editable config variables on templates (L38); (2) ordinary Python logic **and** QMB ports/adapters **selected by adapter-id from closed catalogs** (`AMBIENT_DISCOVERY=false`; bind from resolved run-config; new ids = platform catalog extend at the composition root, not a user pack); (3) QMA plugins, skills, graph templates, desk packs (first-party only; marketplace/trust-tiers stay Cut); (4) UI contribution SDK. Rungs 1–3 bind now. Rung 4 stays GAP-0081 deferred. No-code authoring is not promised. QMA “plugin” vocabulary stays QMA-scoped (DEC-0346). QMB/QMF still say **extensions**, never plugins.

### I-13 — Data work wraps qmf-data; experiments cite CT-12

- **Binds:** F09–F11, QMB data commands, qmf-data rooms, ExperimentSpec `data_ref`
- **Prevents:** a QuantDataManager clone store; silent auto-update of experiment inputs; derived dataset as CT-10 vs QMB sidecar vs new room; free-form `data_ref` weakening L18–L20
- **Rule:** Acquire / verify / gap-check / catalog / generate are QMB data commands wrapping qmf-data (B-11). Quality surfaces are QMB data-command outputs and CT-13 `data quality` reads — **not** I-5 analysis artifacts, and never called “projection.” A derived dataset is a new fingerprinted **qmf-data room** (existing room machinery, new as-of) with a CT-07 lineage edge to its source room(s). It is not a CT-10, not a CT-32, not a QMB sidecar. Vendor-style timezone clones that auto-update the source under an experiment’s feet are refused. **Governed and coordinated experiments cite a CT-12 `split_id`**; `HoldoutSeal` remains policy rejection at every read boundary. File/CSV import and spike/OHLC detectors are **not** in the current command set and stay deferred (not all QDM mechanisms are approved).

### I-14 — A candidate set is a query

- **Binds:** F02 databanks, sweep ranks, QMA staging
- **Prevents:** a copied-row candidate database beside the ledger; `rank_sweep` as a published identity artifact; unioning QMA staging (RefinementProposals) with Library databank
- **Rule:** Retain / filter / rank is a read-time view over (1) QMB ledger lines, (2) registry as-of sets including `dev`-zone candidates of Library kinds, (3) coordinated Experiment Ledger refs. It does **not** read QMA staging (QMA AD-22: staging is RefinementProposals, never bots/Books). `sweep.rank` is this view; it publishes no copied-row artifact. Saved views cite fingerprints and query predicates, not duplicated payloads. Home of a saved view: QMB-returned value (ungoverned); QMB run-dir sidecar citing `fp1` (governed, no new store); Experiment Ledger entry citing the same `fp1` (coordinated). Not `qmf-registry`, not a new sqlite table.

### I-15 — Claim-class mapping; do not extend CT-32 or B-4

- **Binds:** reports, UI, agents, admission
- **Prevents:** projection, synthetic, or trial results masquerading as confirmation; extending B-4’s closed role enum; four stamps for the English word “confirmation”
- **Rule:** Do not extend CT-32 or B-4. Mapping is total: governed/coordinated confirmation run → B-4 `role=confirmation`, no AD-15 field; optimize trial / sweep combo → `role=trial`; MC / WF replicate → `role=replicate` with B-7 procedure label `robustness` or `infra-stress`; aborted → `role=aborted`; projection saved view → no B-4 role, claim-class `projection`, inherit source world, never `confirmed`; path-dependent re-run → B-4 role of **that** run, AD-15 stamp only if published as analysis, still not admission evidence unless `role=confirmation`. Confirmation evidence remains B-4 `role=confirmation` only. L20 stands: synthetic and robustness procedures never validate edge. Replay-world verdicts still cannot gate live money (B-4, GAP-0048). “Published analysis” = a saved view or an Experiment Ledger `analysis.published` entry, not every CT-32.

### I-16 — Governed handoff uses the node hub

- **Binds:** promotion, QMA candidates, QMB CT-32, QMN hub-inbox
- **Prevents:** a QMA promotion command; silent merge of sandbox provenance; a connect-wave that finishes CT-47 with no lawful producer path onto the hub; per-bot paper as the last mile
- **Rule:** QMB governed CT-32 and QMA `dev`-zone candidates reach the node only as **WriterId-scoped hub-inbox fragments**. QMA never mints a promotion command (`QMA_MINTED_PROMOTION_COMMAND = None`). Sandbox provenance is refused at `hub_publish` and pull (TN-20). Human ops: `hub_publish` → `promotion_sign` + silent battery → ADMITTED → next-day `activation`. Assignment of a strategy variant to an intended Book happens before live, as a human act citing fingerprints. This sitting does not reopen DEC-0261 or L30.

---

## Deferred

These can wait because the 16 invariants already pin the shape two epics would otherwise fork. Content, SKU, and UI chrome are not identity.

| Deferred | Why it can wait |
| --- | --- |
| GAP-0048 fidelity taxonomy / `world=simulated` unlock | Irreversible content; QMB B-6/B-7 hold the seams; neither analysis method nor the door needs calibration values to pick a shape |
| GAP-0049 search-quality thresholds / pass batteries | Procedures exist; values would gate compute/live; staged funnel stays manual |
| GAP-0016/0017 look-ahead **registration** gate | Prevention already delivered in QMB; gate stays operator-deferred (DEC-0121) |
| GAP-0085 typed mechanism vocabulary (Entry/Exit/Filter/Session/…) | Ownership ruled in I-4; nouns wait on a QML increment with a non-obsolete trigger (the “revisit at the QML sitting” trigger is consumed) |
| First generator algorithm (placeholder-fill vs logic synthesis vs agent-codegen) | I-4 pins write path; algorithm is not required for connect-wave |
| GAP-0081 UI SDK / `qma-ui-contract` | Wire + AD-26 variables bind now; presentation is its own sitting |
| GAP-0072/0073 memory backend / knowledge index (Delphi-class) | Ports exist; literal search is enough to compose the workbench |
| GAP-0070/0075/0076/0079/0086 | Desktop env, sandbox vendors, RLM envelope, external A2A, graph engine — parent revisit conditions stand |
| QMB MCP door ship | B-1 already: after CLI v1; CT-47 CLI transport is the first door |
| Jupyter as a pinned product / notebook vendor | I-11 does not need a vendor pin; B-9 import is enough |
| Portfolio-combination search (F07) | I-5 refuses the projection reading now; needs correlation/capital evidence later |
| Equity-control sequential walk (QuantAnalyzer Class B) | Sibling of I-5; live on/off stays leash/kill/BMS demotion |
| File/CSV import (F09 new) and spike/OHLC detectors (F10 extend) | Not all QDM mechanisms are approved; I-13 names the omission so F09–F11 are not silently covered by existing `DATA_COMMANDS` |
| AlgoCloud / F17 | Lower-confidence donor; inspectability is already QML+CT-33 |
| RoboQuant.dev RQ Engine, L2-as-product, broker list | Closed beta; shapes only; live-survive-tab-close is node territory |
| Exact always-on daemon host SKU/vendor | I-10 states the property; host is QMA AD-25/AD-26 config |
| `paper-validation` vs `paper-benched` role split | Node V1 collapses to `demo` (TN-9); later role addition, not a rewrite |
| ExperimentSpec re-homed as a CT-06 kind | Unnecessary for Library; default do-not |
| Predicate grammar / `.qml` / Monaco (DEC-0172/0175) | V1 WHEN lives in Python; future grammar compiles to the same two artifacts |
| Screen composition / department roster / agent chrome | UI track; this spine exposes objects and operations only |
| Documentation-factory reconcile of `defined-unwired` stamps | Docs debt, not an architectural fork |
| Automatic missed-fire backfill | Explicitly refused |
| Venue paper of unpromoted bots | Would reopen DEC-0261 and L30 |

---

## Conflicts with parent spines

**No local invariant weakens a parent AD.** Recorded tensions are documentation drift, consumed revisit triggers, or input-row errors — resolve without forking parents.

| Tension | Resolution (do not weaken the parent) |
| --- | --- |
| CT-32/33/34/47 and CT-40..51 YAML still `defined-unwired` / “no code exists” while matching packages exist on `integration@1b451a8` | Documentation-factory reconcile. Treat as **library-present, process/product-unwired**. Do not invent a second design from the stamp. |
| QMA Deferred GAP-0085 said “revisit at the QML sitting”; that sitting closed GAP-0047 and did not mint the nouns | I-4 pins **ownership** (QML + `qmf-registry`; QMA carries candidates only) and **re-defers the nouns** with a non-obsolete trigger. Does not move mechanisms onto QMA (would weaken QMA AD-14). |
| PRD §6 still says QMA “ideation has not begun” vs ADR-0020 | PRD is stale. Architecture authority is ADR-0020 + QMA AD-1..29. Update the existing PRD later; do not rewrite it as a sixth app. |
| `corpus-factory-map.md` “What-if = reuse named condition presets” | That row names **path-dependent config fragments** (B-3), not QuantAnalyzer Class A. I-5 keeps the two nouns apart. Factory-map row is wrong, not a parent AD. |
| Draft companion listing Graph Template / Skill / Routine as Library `fp1` identities | Conflicts with I-3 and with QMA definition-store vs `qmf-registry`. Companion must cite them as QMA records, not Library kinds. |
| QMA AD-6 (QMB run ledger reached by `_ref`, never merged) vs a reading of “persist the ledger” through sqlite | I-8 names **Experiment Ledger only**. Copying QMB JSONL into sqlite would weaken QMA AD-6. |
| QMA AD-22 staging (RefinementProposals, never bots/Books, never registry) vs unioning staging into a databank query | I-14 excludes staging. Union would type-error against QMA AD-22. |
| CONNECT AD-2 / TN-9 (honest FX paper is node+venue, `world=live`) vs calling QMB replay “paper-mode” | I-7 makes research-paper a **display alias** for `world=replay`. Compiling Book paper-mode into QMB would silently override CONNECT. |
| QMA AD-28 (no QMA workload on the trading VPS) vs “put the daemon where live already continues” | I-10 forbids that host. Live continuation through laptop-off is already QMN’s job. |
| B-4 closed role enum `{confirmation, trial, replicate, aborted}` vs adding `projection` as a ledger role | I-15 forbids extending B-4 or CT-32. |
| CT-32 owned by COMP-QMF-RISK (publish-never-act) vs stamping `lane`/`analysis_method` onto CT-32 | I-2 / I-5 / I-15 keep those fields off CT-32 (ledger / Experiment Ledger / saved-view metadata). |
| DEC-0376 (no git-branch-per-parameter) vs OpenResearch worktree-per-experiment | Borrow lineage + compute placement only. Identity stays `fp1`. |
| Optuna “current 5.0.0” prose vs QMB lockfile pin (factory-map 4.9.0) | Lockfile owns the pin. Optuna remains an internal QMB sampler adapter; floats never enter identity. |
| Donor-strategyquant header “no `qma/` package on integration” | Stale vs `qmx-agents/` at the cited SHA. Prefer `code-qma.md`. |

Graveyard that this sitting must not revive: DEC-0084 central backtest service; DEC-0085/0086 donor engines; DEC-0069 paper twins; DEC-0375 QMA execution/paper tool; DEC-0376 git-branch-per-parameter; DEC-0361/0362 plugin marketplace.

---

## UI-facing shared objects (no layout)

Codex/UI may bind to these. Chrome, department roster, and widget packs are out of scope (GAP-0081).

### Identities (Library — `fp1` kinds)

- CT-33 bot-definition
- CT-33 logic source-manifest (cited, not a sibling kind)
- CT-34 confluence
- strategy-family (CT-06 metadata)
- CT-22 Book definition
- CT-27 BMS definition
- CT-28 binding epoch
- CT-12 split
- CT-10 observation / window
- CT-32 performance result
- CT-47 ExperimentSpec (`spec_fp1`, coordinated only)
- `qma-dev-zone-candidate` (dev-zone, Library-kind payload)
- promotion-occurrence-card (human-signed; journal holds pointer)

### Identities (cite, do not re-kind)

- QMB `study_fp` (optimize campaign; derived)
- QMB resolved run-config fragment (DEC-0160; derived)
- QMB ledger line / run id
- saved analysis view (`fp1` of `{method, source, predicate, as_of}`)

### QMA records (not Library kinds)

- Graph Template, Skill, Routine (`content_address`)
- JobHandle (states include `unknown`)
- ExecutionEnvironment (CT-46 compute placement — not a research tab)
- Mission / Task Graph

### Operations

- `run` (ungoverned; values; no ledger)
- `spawn_governed` (QMB orchestrator)
- QMA backtest tool / CT-47 door (coordinated; one invocation per env)
- `optimize.ask` / `optimize.tell`
- `sweep` (expand / batch; `rank` is a view)
- robustness rungs (walk-forward, trade-shuffle, candle MC, significance)
- `data.download` / `verify` / `gap-check` / `catalog` / `generate`
- `analysis.project` (projection saved view)
- `analysis.rerun` (path-dependent new run)
- `compare_runs` (readout; no stamp)
- `procedure.start` (Graph Template → Mission)
- `experiment.register` / `create_successor` (coordinated only)
- `candidate.admit` (dev-zone; never promote)
- `variable.set` (registry-homed AD-26)
- `plugin.install` / `enable` / `reload` (first-party packs)
- `graduate_to_governed` (explicit orchestrator spawn; L33)
- `hub_publish` / `promotion_sign` / `activation` (human, outside QMA, on the node)

### Queries

- Library search by kind + `fp1`
- candidate-set view (ledger + as-of `dev` + Experiment Ledger refs; not staging)
- ledger merge / as-of registry
- gap / quality surface (CT-13 + `gap_check`; not I-5)
- Experiment Ledger inspect

### Lifecycle / events

- QMB orchestrator job states; QMA JobHandle including `unknown`
- tab-close ≠ cancel; laptop-sleep ≠ abort if I-10 host is up
- CT-13 journal types (including `data quality` and `promotion`)
- QMA wire events (attach/detach, mailbox, routine fire, `unknown_tail`)
- JobHandle progress / failure / `unknown`
- CT-07 edges: `branches-from`, `supersedes`, `promoted-from`

### Extension points a non-source user can see

- ui-editable template variables
- drop-in ordinary-Python logic package (ungoverned until graduation)
- install a first-party QMA desk pack; write a Routine citing a graph template
- **Not:** UI widgets (GAP-0081); ambient FillPort drop-ins; plugin marketplace

---

## (1) What already exists

**QMF** — exact money/time/`fp1`/refusals; registry kinds (bot/Book/BMS/result/lineage/promotion card); data rooms, splits, journals, CT-15 ingest; risk value types CT-22..32. Risk YAML still `defined-unwired` while source exists.

**QMB** — event-slice loop; config compiler; pure `run()` vs orchestrator evidence; Python API + CLI; data download/verify/gap-check/catalog/generate; TPE optimize; sweeps; walk-forward / MC / significance as library; CT-32 + chart series; QML host adapter; plain-Python `SliceHandler`. MCP unshipped. CLI does not yet expose robustness or full sweep batch/rank. No named What-if projection function. No structure generator.

**QML** — two-artifact bot (CT-33 + logic); ungoverned tunnel; conformance ≠ performance; parameter spaces; producer templates (number holes, not structure holes). No GAP-0085 mechanism nouns. Host CT-06 mint is composition-root.

**QMA** — ontology, mission/task graph, plugins/skills/routines, ExperimentSpec + Experiment Ledger, QMB door **law**, money-path deny (paper included), continuation/outbox libraries, sqlite writer. Default QMB transport **records** invocations. ExperimentSpec maps are in-process. No composed asyncio listener process found. `qma-ui-contract` is a stub.

**QMN** — unforked `run_slice`; Book-level demo paper; promotion hub + silent battery + next-day activation; evidence HTTP vs powers socket; refuses ungoverned seats and per-bot paper. Research-paper does not belong here.

---

## (2) Missing wiring vs missing function

| Missing wiring (function present) | Missing function |
| --- | --- |
| Real QMA→QMB CLI transport; composed `qma-daemon` process; persist ExperimentSpec/JobHandle/continuation through sqlite | Named **projection** analysis (`analysis.project`) |
| CLI coverage of robustness and sweep batch/rank | Structure/template **generator** (QML; I-4) |
| Durable `dev`-zone `Registrar` vs in-memory | GAP-0085 typed mechanism kinds (deferred) |
| Library query / saved-view predicates | File/CSV CT-15 import; spike/OHLC detectors (deferred) |
| Research/QMA producers emitting hub-inbox fragments | Venue paper of unpromoted bots (**must remain absent**) |
| CT YAML `wiring_status` refresh | UI SDK (GAP-0081); GAP-0048/0049 content |

---

## (3) Recommended architectural ownership

| Concern | Owner | Class |
| --- | --- | --- |
| Wind tunnel, evidence, search, robustness, data fronts, named analysis | COMP-QMB | reuse / extend |
| Bot/confluence/logic authoring; generation **if** built | COMP-QML | reuse now; new later |
| ExperimentSpec, Experiment Ledger, door, procedures, continuation | COMP-QMA-DAEMON (+ CORE defs, WIRE envelope) | reuse law; connect process |
| Kinds, lineage, promotion card | COMP-QMF-REGISTRY | reuse |
| Book/BMS/CT-29/CT-32 shapes | COMP-QMF-RISK | reuse |
| Rooms, splits, journals | COMP-QMF-DATA | reuse |
| Live/paper soak, hub, unforked `run_slice` | COMP-QMN | reuse; not a research lab |
| Shared Library UI | query over fp1 kinds | connect |
| Human live promote | operator outside QMA, node powers | reuse |

Connect-wave (door + persistence + composed daemon + Library queries + named analysis + CLI coverage + hub-inbox producers) is the coherent first implementation area. Generation can trail without blocking Library or What-if.

---

## (4) Open questions — AD vs Deferred

The 16 invariants **are** the ADs this sitting owes (intent AD-cand-1..6 plus the joints inventories and the adversary pass showed two epics would fork). Remaining opens are not identity:

- First generator algorithm → Deferred (I-4 owns the write path).
- Concrete always-on host → ops over I-10 / QMA AD-25/AD-26.
- PRD FR addenda for ExperimentSpec, analysis methods, generation-vs-search, procedures → next PRD update; do not rewrite the PRD.
- Work-environment roster → UI-open.

No further AD is required to keep builders compatible once these 16 are adopted verbatim.

---

## Citations (primary)

- Inputs this sitting: `_BRIEF.md`, `intent-durable.md`, `orchestrator-verified.md`, `code-qma.md`, `code-qmb.md`, `code-qml.md`, `code-qmf.md`, `code-qmn.md`, `corpus-docs.md`, `corpus-factory-map.md`, `cut-identity.md`, `cut-generation.md`, `cut-what-if.md`, `cut-paper.md`, `cut-continuation.md`, `cut-extensibility.md`, donor notes (SQ, QA, QDM, QC, OpenResearch, RoboQuant.dev)
- Parents: `architecture-QMX-2026-08-19`, `architecture-QMB-2026-08-20`, `architecture-QML-2026-08-21`, `architecture-NODE-2026-08-28`, `architecture-QMA-2026-08-28`, `architecture-CONNECT-2026-09-11` Deferred tables
- Product: `git show integration:<path>` at `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2`

*Architecture only. No implementation. No branch switch. No donor engine copy.*
