# Reconcile — load-bearing inputs vs distilled spine

Date: 2026-09-14. Architecture sitting only. Not a layout, epic, or implementation plan.

**Spine:** `ARCHITECTURE-SPINE.md` (AD-1..AD-15) + companion `CAPABILITY-EXPANSION.md`.  
**Inputs read:** `_BRIEF.md`, `intent-durable.md`, `orchestrator-verified.md`, `code-qma.md`, `code-qmb.md`, `code-qml.md`, `code-qmn.md`, `code-qmf.md`, `corpus-factory-map.md`, `corpus-docs.md`, plus donor notes (SQ, QC, QDM, OpenResearch, RoboQuant.dev).

Evidence rule inherited from the brief: class/test existence is not end-to-end proof; stale `defined-unwired` is not proof of absence.

## Verdict

**Partial land.** The six intent AD-cands that needed a named decision (generation≠search, paper trinity, laptop-off owner, Book/BMS candidates, What-if methods, and “no sixth application”) are in the spine. The quiet miss is **F12 research-undertaking continuity**: the header binds F12, the companion says Project vs Workspace is “answered as ExperimentSpec + projections,” and no AD states the join that would stop a later sitting from minting a Project package or leaving Bot / ExperimentSpec / run-config / notebook as four unjoined nouns.

Connect-wave A+B+D in the companion is otherwise coherent. Two source-inspected connect contracts the inventories flagged as **needing an AD this sitting** did not become rules: composed `qma-daemon` process, and QMA/QMB → node hub-inbox fragments.

---

## Compact scorecard

| Input load-bearing item | Where it asked | Spine landing | Class |
|---|---|---|---|
| No sixth application / DEC-0084 stays dead | brief; factory-map | **AD-1** | landed |
| Three lanes (ungoverned / governed / coordinated) | brief QMB purity; QMA door | **AD-2** | landed |
| Shared Library = fp1 kinds; not STRATS store; not three records | intent §6; F02; code-qmf | **AD-3**, **AD-14** | landed (Library). **F12 continuity join not landed** (below) |
| Search ≠ structure generation; GAP-0085 ownership | intent AD-cand-1; code-qml; SQ donor | **AD-4** (ownership ruled; nouns deferred) | landed |
| What-if projection vs path-dependent rerun | intent AD-cand-5; F05/F08 | **AD-5**, **AD-15** | landed |
| Book/BMS = candidates + replay; QMA never fills money-path | intent AD-cand-4; F06 | **AD-6** | landed |
| Paper trinity (research / node / no QMA-paper) | intent AD-cand-2; code-qmn | **AD-7** | landed (nouns). **hub-inbox connect not landed** |
| Real QMA→QMB CLI door + persist ExperimentSpec | orchestrator; code-qma; CT-47 | **AD-8** | landed as law. **Daemon process composition omitted** |
| Procedures = QMA graphs; steps = QMB; no wizard | intent §2; F03; AD-9 | **AD-9** | landed |
| Laptop-off = daemon + remote env + outbox | intent AD-cand-3; F15 | **AD-10** | landed as property. Host still open (honest). Process composition still missing |
| Notebooks import library; lifecycle = ExecutionEnvironment | F13; B-9 | **AD-11** | landed |
| Extensibility ladder; GAP-0081 deferred | intent §5; F17 lower | **AD-12** | landed |
| Data wraps qmf-data; no silent clone auto-update | F09–F11; QDM donor | **AD-13** | partial — existing `DATA_COMMANDS` only |
| GAP-0048/0049/0016/0017 this sitting vs child sitting | corpus-docs §2 | Deferred table (explicit re-defer) | landed as deferral, not drop |
| F12 / AD-cand-6 Project vs Workspace continuity | intent §9; QC donor; F12 First | companion sentence only; **no AD** | **dropped (quiet)** |
| Composed asyncio daemon (listener + one writer) | code-qma §2/§5; synthesis (2) | not in Structural Seed connect list | **mismatch** |
| QMA/QMB → hub-inbox WriterId / sandbox-provenance | code-qmn §5 + open Q | AD-7 stops at “human act onto the node” | **dropped connect AD** |
| ExperimentSpec `data_ref` cites CT-12 / HoldoutSeal | corpus-docs PRD hole; code-qmf | AD-13 never binds splits to experiments | **dropped (quiet)** |
| F09 file/CSV import (new CT-15 adapter) | F09 bound; QDM donor `new` | AD-13 restates download/verify/gap-check/catalog/generate | **bound, truncated** |
| Ungoverned→governed graduation as named operation | brief L33; code-qml; QC handoff | Inherited L33 only; no workbench op | noted, not top |
| Dirty/unfingerprinted launch refusal | OpenResearch #3 | not named | noted, not top |
| Heterogeneous intake (idea/video/paper/article) | intent job #1 | no owner row | noted, not top |

---

## Top dropped requirements / mismatches

### 1. Quiet drop — F12 continuity join (AD-cand-6)

**Load-bearing.** Intent listed AD-cand-6 as an Architecture Decision: *“Shared work identity: Project vs Workspace (or another container) for continuity across notebooks/code/runs/agents.”* F12 is First-order and **bound in the spine YAML**. QuantConnect donor: transfer the *job* of one named undertaking (declaration + logic + notes + result lineage across local/remote), do not transfer a Project folder; wire CT-33 → ExperimentSpec → QMB run-config so a UI workspace can present them as one unit without a fourth service (`inputs/donor-quantconnect.md` §1). Factory-map: reuse ExperimentSpec unless proven insufficient; **AD only if** “research project” must be a kind ≠ ExperimentSpec.

**What the AD structure did.** Companion §2: *“Project vs Workspace (answered as ExperimentSpec + projections, not a new package).”* AD-3 is a **Library** identity rule (one bot/result is one fp1; work-environment tabs are UX). AD-8 persists ExperimentSpec. AD-11 places notebook lifecycle. None of those states the join, the display alias, or the refusal of a COMP-PROJECT / QC-`config.json` identity.

**Why it is quiet.** The header claims F12; the companion claims the open question is closed; a later epic can still mint a Project package or leave four unjoined nouns. That is exactly the failure AD-cand-6 was invented to prevent.

**Repair if this sitting still owns ADs.** One short AD (or an AD-3 clause): *a research undertaking is the join of CT-33 + logic-manifest + ExperimentSpec + Experiment Ledger + resolved run-config (+ optional notebook env). UI may name a workspace. Identity stays those fingerprints. A new Project/Workspace kind is a spine amendment.*

### 2. Mismatch — composed `qma-daemon` process is the missing wiring AD-8/AD-10 assume

**Load-bearing.** `code-qma.md`: no `asyncio.run` / websockets server under `qma-daemon`/`qma-wire` `src/`; wire is contract library + validators; default QMB transport is `RecordingQmbDoorTransport`. Remaining product-unwired: (a) composed long-running process, (b) remotes dialing a live listener, (c) real QMB transport, (d) UI stub, (e) deferred backends. Laptop-off implication: the missing piece is the **always-on process** that binds the listener and keeps the journal writer alive — not a new ontology.

**What the AD structure did.** AD-8: replace recording transport; persist through daemon journal/sqlite. AD-10: work that survives sleep is owned by `qma-daemon` + remote envs + outbox. Companion connect-wave: (1) real CLI transport, (2) persist ExperimentSpec, (3) CLI parity, (4) Library projections, (5) stamp `lane`. Structural Seed `connect:` lists transport and persistence only.

**Gap.** Persistence and laptop-off are laws over a process that source says is **not composed**. Factory epics following connect-wave A can ship a CLI adapter into an in-memory example `main()` and call AD-8 done.

**Repair.** Add to Structural Seed `connect:` *composed qma-daemon entry (listener + single sqlite writer + pack roster)*. AD-8/AD-10 already name the owner; they do not name the missing composition.

### 3. Dropped connect AD — experiment artifacts → node hub-inbox

**Load-bearing.** Intent job “Governed handoff”: versioned evidence; variant assigned to intended Book; paper then human promote. `code-qmn.md` path is coded: hub-inbox (WriterId-scoped fragments) → `hub_publish` → `promotion_sign` + silent battery → ADMITTED → next-day `activation`; sandbox provenance refused at publish and pull. Open question **this sitting**: *“Exact artifact schema / WriterId conventions for QMA→hub-inbox fragments — Needs AD if not already pinned.”* Missing wiring: research/QMA producers emitting those fragments.

**What the AD structure did.** AD-7 names the three paper nouns and “Promotion remains a human act outside QMA onto the node.” Capability map: live = QMN; agent money-path = candidates only. No WriterId, no hub-inbox, no sandbox-provenance, no Book-assignment-before-promote as a connect contract.

**Gap.** A connect-wave can finish CT-47 and still have no lawful producer path from a governed CT-32 / dev-zone candidate onto the hub the node already implements. That is the last mile of the settled handoff job.

### 4. Quiet drop — ExperimentSpec `data_ref` does not bind CT-12 / HoldoutSeal

**Load-bearing.** Brief + constitution: splits and L20 (synthetic/robustness never validate edge). `code-qmf.md`: `HoldoutSeal` is policy rejection at every read boundary; CT-12 `split_id` is fp1. `corpus-docs.md` PRD hole: *“no FR tying ExperimentSpec `data_ref` to CT-12 manifests.”* Orchestrator classification: Shared Library includes splits; data work is QMB fronts over qmf-data.

**What the AD structure did.** AD-3 lists CT-12 among Library kinds. AD-13: acquire/verify/gap-check/catalog/generate; derived dataset = new fingerprinted artifact; refuse vendor-style timezone clones that auto-update under an experiment’s feet. AD-8 persists ExperimentSpec. None requires a governed/coordinated experiment to **cite** a CT-12 manifest, nor that holdout peek is a typed refusal at the workbench door.

**Gap.** Factory can wire ExperimentSpec persistence with a free-form `data_ref` and never touch splits. That silently weakens L18–L20 for the new experiment surface.

### 5. Bound-but-truncated — F09–F11 reduced to existing `DATA_COMMANDS`

**Load-bearing.** Spine YAML binds F09, F10, F11. F09: ingest **and normalize** (import mapping, timezone, resolution, derived relationship). QDM donor: file/CSV import is **`new`** — no CT-15 file-source adapter, no `qmb data import`; spike/incorrect-candle review is **`extend`** (`verify` is integrity, not spike/OHLC). Intent data-prep job: acquire/scrape/ingest, inspect coverage/quality/anomalies, derive with provenance.

**What the AD structure did.** AD-13 reuses the six existing QMB commands and names quality as projections over CT-13 + `gap_check`. Auto-update clones correctly refused. Import mapping, CSV/file source, and spike/OHLC detectors are unnamed — not even Deferred.

**Gap.** Binding F09–F11 then restating `DATA_COMMANDS` looks like coverage. The new/extend half of those IDs did not land. Either mint “file import + spike detectors stay Deferred (not all QDM approved)” or add them as QMB/QMF extend under AD-13.

---

## What did land (so this is not a general complaint)

AD-1..AD-15 correctly refuse a sixth app, a fourth experiment lane, a STRATS candidate store, TPE-as-generation, filtered-trades-as-Book-truth, QMA paper execution, a QMB workflow engine, a Jupyter product inside QMB, a UI plugin SDK this sitting, and a QuantDataManager clone store. CT-47 `defined-unwired` vs integration source is treated as docs drift, not a silent pick — matches the brief. GAP-0048/0049/0016/0017 are **explicitly re-deferred** (corpus-docs asked for that decision). Genetic/Random **engine** is companion-refused; GAP-0085 nouns wait on a QML increment (AD-4).

## Noted, not in the top five

| Item | Why not top |
|---|---|
| Ungoverned→governed graduation as a named op (`graduate_to_governed` + lineage) | L33 is inherited; missing is a workbench verb, not the law |
| OpenResearch dirty/unfingerprinted launch gate | Small extend of existing `code_ref` law; not a settled operator job |
| Heterogeneous intake (video/paper/article/idea) | Settled job #1; research-corpus plugin exists; no AD owner. UI/authoring sitting can take it if named |
| F14 exact agent object/version context (no silent retarget) | Operator rejected a universal dock; backend bind is still real; F14 was **not** in the spine `binds` list |
| SQ WF-as-reopt-per-window / WF Matrix | Donor extend; QMB B-14 already owns the ladder; thresholds stay GAP-0049 |
| Optuna 5.0.0 prose vs factory-map lockfile 4.9.0 | Stack note; lockfile-owns-pin is already the rule |

## Repair order if the spine is still open

1. Write the F12 continuity-join AD (or fold it into AD-3). This is the quiet one.  
2. Add composed daemon process to Structural Seed `connect:` (makes AD-8/AD-10 executable).  
3. Name hub-inbox/WriterId as connect (AD-7 clause or AD-16).  
4. Bind ExperimentSpec `data_ref` → CT-12 + HoldoutSeal.  
5. Either defer or extend F09 import / F10 spike under AD-13 so the binds list is honest.
