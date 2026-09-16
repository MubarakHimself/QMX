# Spine-fidelity review — workbench documentation-factory increment (2026-09-14)

Role: independent spine-fidelity reviewer. Docs not edited.

Authority: `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md` (status: final; local AD-1..AD-16). Compare absorbed `docs/` against that spine, not against earlier memlog lines the parent-consistency gate already amended. Ledger statements DEC-0269..DEC-0287 and ADR-0022 are the docs-local restatement of that spine.

**Verdict: FAIL-with-amendments.** Seven of ten hunt items are clean. Three hunts fail (AD-2 dual-label collapse in the golden scenario; local AD-id collisions in mixed docs; ADR-0022 AD-1 omits the closed inherited-store list including QMA daemon sqlite / Experiment Ledger). Component specs `qmb.md` and `qma-daemon.md` already carry the post-gate AD-2 dual-label rule; SCN-0015 and the index blurb contradict them.

---

## Hunt checklist

| # | Hunt | Result |
|---|---|---|
| 1 | Silent filling of GAP-0085 nouns, GAP-0063 algorithm, GAP-0062 host machine, or PRD rewrite (GAP-0061) | **PASS** |
| 2 | Local AD ids colliding with QMA AD / QMF AD numbering in prose | **FAIL** |
| 3 | Projection allowing size rescale | **PASS** |
| 4 | AD-2 recording lane as evidence class or as CT-32 field; dual labels collapsed | **FAIL** (not recorded as evidence class / CT-32 field; golden scenario collapses the two honest labels) |
| 5 | AD-7 closing the legal B-15 hub-inbox path | **PASS** |
| 6 | AD-1 omitting QMA daemon sqlite / Experiment Ledger as a legal store | **FAIL** |
| 7 | New COMP or sixth application | **PASS** |
| 8 | QMA `import qmb` | **PASS** |
| 9 | Treating `RecordingQmbDoorTransport` as working integration | **PASS** |
| 10 | Generated layouts treated as preference | **PASS** |

---

## Findings

### F1 — HIGH — SCN-0015 records `workbench_lane=governed` only for orchestrator spawns *not* placed by CT-47, and omits the QMB evidence of a coordinated run

**Hunt:** 4 (post-gate AD-2 dual labels).

**File:** `docs/scenarios/SCN-0015-three-experiment-lanes.md` (Then (3); Worked numbers). Same collapse in `docs/index.md` SCN-0015 blurb.

**Spine sentence (AD-2 / DEC-0270):** *"`workbench_lane` is derived from the door and is recorded only as **workbench metadata** on the QMB ledger line (`governed` for every orchestrator spawn, including those QMA placed) and on the Experiment Ledger entry (`coordinated` when QMA placed it). It is not QMF AD-12 evidence class, not B-4 `role`, and not a CT-32 field. A QMA-placed **run** therefore has two honest labels on two objects: the QMB ledger line is `workbench_lane=governed` (it is QMB evidence); the Experiment Ledger entry is `workbench_lane=coordinated` (QMA placed it). They are not the same field and must not be collapsed."* Evidence of the coordinated run is *the spawned run's QMB ledger line and CT-32, reached by `_ref` from the Experiment Ledger; QMA does not copy them.*

**Doc sentence:** Then (3): *"QMA places the run only when a registered ExperimentSpec (CT-47) exists; the Experiment Ledger entry carries `workbench_lane = coordinated`."* Worked numbers: *"`workbench_lane = governed` rides the QMB ledger line metadata for every orchestrator spawn **not placed by CT-47**"* and *"`workbench_lane = coordinated` rides the Experiment Ledger when QMA placed the run."* Index: *"governed (one ledger line + CT-32, `workbench_lane=governed`) vs coordinated (ExperimentSpec + Experiment Ledger)."*

**What:** SCN-0015 is the golden lane scenario. It (1) withholds `workbench_lane=governed` from QMA-placed QMB ledger lines, which is the pre-gate collapse the FINAL spine forbade; (2) never states that a coordinated placement still writes one QMB ledger line + one CT-32 as evidence. CT-32 / B-4 / QMF AD-12 are correctly refused as homes (Given + Branch A) — that half of hunt 4 is clean. `docs/components/qmb.md` (Three door-derived lanes) and `docs/components/qma-daemon.md` (Coordinated lane identity) already state the two-object rule. The golden scenario contradicts those specs.

**Fix:** Rewrite Then (3) and the Worked numbers: a CT-47 placement still produces one QMB ledger line with metadata `workbench_lane=governed` plus one CT-32; the Experiment Ledger entry is `workbench_lane=coordinated` and cites those by `_ref`. Delete "not placed by CT-47" from the governed-metadata bullet. Align the `docs/index.md` SCN-0015 blurb. Optional: ADR-0017 follow-up and `docs/architecture/overview.md` three-lanes paragraph should name the two objects rather than "ledger and/or Experiment Ledger."

---

### F2 — HIGH — Bare `AD-10` / `AD-5` / `AD-4` in mixed docs mean workbench-local ids and collide with QMA AD-10 (hooks) and QMF AD-5 (version ladders)

**Hunt:** 2.

**Files:** `docs/gap-report.md` (GAP-0062 row and the "3 deferred" bullet); `docs/knowledge/traceability.md` (GAP-0062 locator; FEAT-0038 blocker); `docs/changelog.md` (2026-09-14 Gaps row); `docs/components/qmf-data.md` (Workbench data wrap); `_docwork/gaps.yaml` GAP-0062 question (source of the gap-report copy).

**Spine sentence:** *"Local `AD-1`..`AD-16` are this sitting’s ids and do not renumber QMF `AD-*`, QMA `AD-*`, or CONNECT `AD-*`. Cite parents by `QMF AD-n` / `QMA AD-n` / `B-n` / `QL-n` / `TN-n` / `CONNECT AD-n`."* Hunt rule: cite **workbench AD-n** or **DEC-02xx**, not bare AD-8 meaning QMA AD-8.

**Doc sentences:**
- Gap report GAP-0062: *"What is the concrete always-on host for **AD-10** laptop-off continuation"* and *"Keep **AD-10**'s property."* Same file GAP-0087: *"AD-10's hook set is QMA-authored."*
- Traceability GAP-0062: *"Concrete always-on host for **AD-10** continuation."* FEAT-0038: *"Continuation host config (**AD-10** property; machine is GAP-0062)."* Adjacent QMA rows cite AD-10 as hooks (GAP-0087 / DEC-0309).
- Changelog Gaps: *"GAP-0062 (**AD-10** host machine)"* and *"GAP-0085 ownership … (**AD-4** / DEC-0272)."* Same file CONNECT table: *"AD-4 / DEC-0266."*
- `qmf-data.md`: *"Quality surfaces … are not **AD-5** analysis views and not a new COMP (DEC-0281)."* In a QMF component spec, AD-5 is QMF version ladders (DEC-0103).

**What:** Workbench AD-10 is continuation (DEC-0278). QMA AD-10 is hooks (DEC-0309). Workbench AD-5 is named analysis (DEC-0273). QMF AD-5 is two version ladders. Workbench AD-4 is generation-vs-search (DEC-0272). CONNECT AD-4 is FTR-01. Bare AD-n in these mixed documents will be read as the parent. ADR-0022's own `AD-n / DEC-02xx` bullets are scoped (the ADR is the workbench sitting) and are not this finding. QMA component specs citing QMA AD-n for QMA parents are not this finding.

**Fix:** In every mixed doc, write `workbench AD-10` / `DEC-0278`, `workbench AD-5` / `DEC-0273`, `workbench AD-4` / `DEC-0272`. Gap-report GAP-0062 and `gaps.yaml` question text must not share "AD-10" with GAP-0087. `qmf-data.md`: "not workbench AD-5 / DEC-0273 analysis views."

---

### F3 — MEDIUM — ADR-0022 AD-1 restatement drops the closed inherited-store list (QMA daemon sqlite / Experiment Ledger)

**Hunt:** 6.

**File:** `docs/decisions/ADR-0022-workbench-expansion.md` (Decision, AD-1 / DEC-0269 bullet). Ledger DEC-0269 itself is complete; the ADR is the docs-local AD restatement.

**Spine sentence (AD-1 / DEC-0269):** *"Inherited stores stand: `qmf-registry`, `qmf-data` rooms, QMB JSONL run ledger, QMA daemon sqlite (journal, Experiment Ledger). A **new** store beside those is a spine amendment. DEC-0084 stays dead."*

**Doc sentence:** *"Minting a new application package or a permanent experiment daemon besides `qma-daemon` is a spine amendment. Inherited stores stand. DEC-0084 stays dead."*

**What:** Parent-consistency F3 was HIGH because a closed pair of `qmf-registry`/`qmf-data` would make the inherited QMA Experiment Ledger a spine amendment. The FINAL spine named the four owners. ADR-0022 shortened that to "Inherited stores stand" with no list. `qma-daemon.md` correctly persists ExperimentSpec/Experiment Ledger through the sqlite writer (connect, not a new COMP), so runtime prose is fine — the AD-1 restatement that factory preflight will copy is the hole.

**Fix:** Restore the four-owner list on the ADR-0022 AD-1 bullet (and any constitution/overview one-liner that claims to restate AD-1 stores). Keep DEC-0084 dead.

---

## Clean hunts (no finding)

### Hunt 1 — gaps not silently filled; PRD not rewritten

GAP-0085 remains `deferred`, `answer: null`; ownership QML/host (DEC-0272); nouns unruled. GAP-0063 remains the unruled generator algorithm (placeholder-fill vs Python-logic synthesis). GAP-0062 remains the unnamed always-on host. GAP-0061 remains PRD FR addenda; ADR-0022 and cheap-veto A5 say the PRD is not rewritten. `qml.md`, ADR-0018 follow-up, `qma-core.md`, CT-33/CT-34, and AGENTS hard rules all refuse filling those holes in prose.

### Hunt 3 — projection does not allow size rescale

SCN-0016 Branch A, ADR-0022 AD-5, `qmb.md` named-analysis section, `qmf-risk.md`, glossary `analysis.project`, overview, and CT-32 invariant all forbid size / R / Book / ports / `starting_capital` as projection. Path-dependent is `analysis.rerun` (new CT-32).

### Hunt 4 (forbidden recording half) — lane is not evidence class and not a CT-32 field

CT-32 `intended_producers` and invariants: `workbench_lane` and `analysis_method` are **not** fields of the container. Glossary `workbench_lane`, AGENTS hard rules, ADR-0022 AD-2, `qmb.md` labels section, and SCN-0015 Given/Branch A all refuse QMF AD-12 evidence class, B-4 role, and CT-32 as homes. The remaining defect is F1 (dual-label collapse), not a CT-32/AD-12 mint.

### Hunt 5 — B-15 hub-inbox path stays open; sandbox-provenance stays refused

Spine AD-7 / DEC-0275: *"QMB may append WriterId-scoped fragments to the B-15 hub inbox; sandbox-provenance fragments stay refused at publish and pull (TN-20). `hub_publish` is human. QMA never writes the hub; it holds candidate refs only."*

`qmb.md` Paper trinity, `trading-node.md` Hub inbox and provenance, and ADR-0022 AD-7 match. No absorbed sentence revives "QMA/QMB never write the hub-inbox except as sandbox-tainted fragments."

### Hunt 7 — no new COMP, no sixth application

Preflight reuse recorded in ADR-0022, changelog, constitution L7/L31 annotations, overview, AGENTS, `qmb.md`, `qma-daemon.md`, `qmf-registry.md`, `trading-node.md`. No `COMP-EXP`. FEAT-0033..0039 reuse existing COMP-* owners. DEC-0084 stays dead.

### Hunt 8 — QMA never `import qmb`

ADR-0022 AD-2/AD-8/AD-9, `qma-daemon.md` May never, CT-47 invariants, SCN-0015 When (3), overview mermaid, AGENTS hard rules, ADR-0020 follow-up. Notebooks `import qmb` remain AD-11 / DEC-0279 on a controlled-room host (not QMA).

### Hunt 9 — `RecordingQmbDoorTransport` is not a working integration

ADR-0022 Context + AD-8 + Consequences, `qma-daemon.md` Real CLI transport, ADR-0020 follow-up, CT-47 invariant and provenance_note, DEC-0286. Default on `integration@1b451a8` still records and does not spawn `qmb`; connect-wave replaces it.

### Hunt 10 — generated layouts are not preference evidence

ADR-0022 Context + cheap-veto A3, changelog A3, DEC-0287 A3. No absorbed doc treats generated layouts or reactions as preference.

---

## Residual nits (non-blocking; not hunt failures)

1. **ADR-0017 follow-up / overview three-lanes paragraph** state `workbench_lane` as metadata "on the ledger / Experiment Ledger" without the two-object rule. Not wrong; incomplete next to F1.
2. **ADR-0022 AD-5 bullet** omits B-3 `seed_overridden` → fold `unrated` on `starting_capital` override (spine AD-5 / DEC-0273). Glossary `analysis.rerun` and `qmb.md` still carry it.
3. Some **ops/incident lenses** still say risk contracts are `defined-unwired` / "no code." DEC-0286 residual; CT-22..32 YAML already stamps `source-inspected`. Not a workbench AD fork.

---

## Required amendment list (docs, not operator)

1. SCN-0015 Then (3) + Worked numbers: dual labels on two objects; QMB ledger+CT-32 remain the coordinated-run evidence. Index blurb follows.
2. Mixed-doc AD citations: `workbench AD-n` or `DEC-02xx` in gap-report GAP-0062, traceability GAP-0062/FEAT-0038, changelog Gaps row, `qmf-data.md` AD-5, `gaps.yaml` GAP-0062 question.
3. ADR-0022 AD-1: restore the four inherited stores, including QMA daemon sqlite (journal, Experiment Ledger).

Do not fill GAP-0085 / GAP-0063 / GAP-0062 / GAP-0061. Do not put `workbench_lane` on CT-32 or QMF AD-12. Do not close the B-15 WriterId hub-inbox path. Do not mint a COMP. Do not `import qmb` from QMA. Do not treat `RecordingQmbDoorTransport` as e2e. Do not treat generated layouts as preference.
