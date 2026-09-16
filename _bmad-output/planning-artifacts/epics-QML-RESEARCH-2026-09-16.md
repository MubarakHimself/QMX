---
stepsCompleted: [1, 2, 3, 4]
validated: true
inputDocuments:
  - _docwork/riders/qml-research-expansion-2026-09-16.md
  - docs/decisions/ADR-0023-qml-research-expansion.md
  - _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/REQUIREMENTS-ADDENDUM.md
  - _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/QML-EXPANSION.md
  - _docwork/qml-research-increment-brief.md
  - _docwork/qml-research-epics-handoff.md
  - docs/scenarios/SCN-0017-stage0-honesty-envelope.md
  - docs/components/qml.md
  - docs/components/qma-core.md
  - docs/components/qma-daemon.md
  - docs/components/qma-wire.md
  - docs/components/qmb.md
  - docs/contracts/ct-06-registration.yaml
  - docs/contracts/ct-07-lineage-edge.yaml
  - docs/contracts/ct-33-bot-definition.yaml
  - docs/contracts/ct-34-confluence.yaml
  - docs/contracts/ct-40-qma-wire-envelope.yaml
  - docs/contracts/ct-44-qma-knowledge-source.yaml
  - docs/gap-report.md
  - docs/glossary.md
  - docs/AGENTS.md
  - _docwork/feature_inventory.yaml (FEAT-0047..FEAT-0050; blockers FEAT-0045, FEAT-0046, FEAT-0030, FEAT-0034, FEAT-0041)
  - _docwork/ledger.yaml (DEC-0380 ratified; DEC-0381..DEC-0407 provisional; DEC-0408..DEC-0413 dead)
  - _docwork/gaps.yaml (GAP-0064; GAP-0073/0085/0061/0063 updated in place)
  - _bmad-output/planning-artifacts/prds/prd-QMX-2026-08-21/prd.md (§7 out of scope; no mill FRs; GAP-0061 — do not rewrite)
  - _bmad-output/planning-artifacts/epics.md (Epics 11–12 only — extend, do not duplicate)
  - _bmad-output/planning-artifacts/epics-QMA-2026-08-29.md (Epics 47.2, 48.4 — KnowledgeSource + research-corpus pack; extend, do not duplicate)
  - _bmad-output/planning-artifacts/epics-WORKBENCH-2026-09-14.md (Epics 34, 38 — Library kinds + generation law; extend, do not duplicate)
  - _bmad-output/planning-artifacts/epics-CONNECT-2026-09-11.md (Epic 31 — numbering reservation only)
  - integration@8510c032496bb870824ecc5c4f807e8a4e4f167e (brownfield defects this increment forbids)
excludedDocuments:
  - _bmad-output/planning-artifacts/epics.md (must not be rewritten)
  - _bmad-output/planning-artifacts/epics-QMA-2026-08-29.md (must not be rewritten)
  - _bmad-output/planning-artifacts/epics-CONNECT-2026-09-11.md (must not be rewritten)
  - _bmad-output/planning-artifacts/epics-WORKBENCH-2026-09-14.md (must not be rewritten)
  - _bmad-output/planning-artifacts/prds/prd-QMX-2026-08-21/prd.md (must not be rewritten; GAP-0061)
  - _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/LIBRARY-ADAPTATION.md (superseded first distill; do not fold as current)
  - _bmad-output/planning-artifacts/ux-designs/ux-QMX-2026-09-01/DESIGN.md (empty scaffold; README forbids using it as a contract)
  - _bmad-output/planning-artifacts/ux-designs/ux-QMX-2026-09-01/EXPERIENCE.md (empty scaffold; README forbids using it as a contract)
delegation: "operator 2026-09-16 — autonomous run; operator away; menus auto-continued; QML research increment only; operator authorized unbounded agents and factory drain after stories"
epicNumbering: "Epic 49–52 — reserved so QML-RESEARCH never collides with Phase-1 (1–23), trading-node (24–30), CONNECT (31), WORKBENCH (32–38), or QMA (40–48). Epic 39 left unused as a buffer."
baseInventory: "integration@8510c032496bb870824ecc5c4f807e8a4e4f167e (git show / .worktrees/integration-inspect, no checkout of integration onto main)"
feature: FEAT-0047..FEAT-0050
adr: ADR-0023
architectureStatus: provisional — operator has not accepted the 2026-09-16 spine; DEC-0380 is ratified; absorbed AD-1..AD-21 are provisional
decisions: [DEC-0380, DEC-0381, DEC-0382, DEC-0383, DEC-0384, DEC-0385, DEC-0386, DEC-0387, DEC-0388, DEC-0389, DEC-0390, DEC-0391, DEC-0392, DEC-0393, DEC-0394, DEC-0395, DEC-0396, DEC-0397, DEC-0398, DEC-0399, DEC-0400, DEC-0401, DEC-0402, DEC-0403, DEC-0404, DEC-0405, DEC-0406, DEC-0407, DEC-0408, DEC-0409, DEC-0410, DEC-0411, DEC-0412, DEC-0413]
---

# QMX - Epic Breakdown

## Overview

This document is the epic and story breakdown for the **QML research expansion** increment (FEAT-0047..FEAT-0050): absorb the portable Stats seed mill as **Stage 0** of the existing QML bot-authoring library — two-stage authoring over hexagonal libraries — without minting a sixth application, a new contract id, or a STRATS product language.

It decomposes the **proposed** 2026-09-16 corpus — architecture-QMX-2026-09-16 local AD-1..AD-21, ADR-0023 (provisional), DEC-0380 (ratified paradigm) plus DEC-0381..DEC-0407 (provisional), SCN-0017, FR-RES-* on GAP-0064, and the brownfield defects at `integration@8510c032496bb870824ecc5c4f807e8a4e4f167e` — into implementable stories for the factory lanes.

The Phase-1 file (`epics.md`, Epics 1–23 and trading-node Epics 24–30) stays untouched and is not superseded. CONNECT (`epics-CONNECT-2026-09-11.md`, Epic 31) stays untouched. WORKBENCH (`epics-WORKBENCH-2026-09-14.md`, Epics 32–38) stays untouched. QMA (`epics-QMA-2026-08-29.md`, Epics 40–48) stays untouched. **Epic numbering starts at Epic 49**, a reserved block so this increment never collides with those files. Epic 39 is left unused as a buffer.

Requirement prefixes carry the RES marker because these requirements derive from the **proposed QML research-expansion docs corpus and child spine, not from a PRD rewrite**. The 2026-08-21 PRD has no mill / seed-corpus / hypothesis FRs. GAP-0061 stays deferred; this sitting does not rewrite the PRD (DEC-0405). FR-RES-* live on GAP-0064. Rules carried forward from `epics.md`: each FR's cited artifact is the epic boundary and the source of its acceptance criteria; FR granularity is deliberately coarser than story granularity — never size a lane by counting FRs.

This increment **extends** QML Epics 11–12, QMA Stories 47.2 and 48.4, and WORKBENCH Epics 34 and 38. It does not duplicate completed stories. Story 11.1 remains the `qml` scaffold (pure, no CLI, no I/O). Story 12.* remains QL-7/QL-8 including `graduate_to_governed`. Story 47.2 remains CT-44 snapshot/search/retrieve/cite **law**. Story 48.4 remains the five desk packs including `research-corpus`. Story 34.1 remains the Library kind roster (`strats` refused). Story 38.1 remains generation write-ownership. These stories **close** the in-memory two-file stub, the missing `qml.research` surface, mill graduation identity, and the federated hit DTO those stories left open, and **forbid** treating the stub as the seed, minting `research_ref` from a LAYOUT-DEMO view, auto-minting CT-33 from DNA, or adding `hit_class: strats`.

Preflight verdict (ADR-0023): **reuse** COMP-QML, COMP-QMA-CORE, COMP-QMA-DAEMON, research-corpus desk pack, COMP-QMA-WIRE, COMP-QMB, COMP-QMF-REGISTRY. No new component, no new contract id, no mill daemon, no sixth application. The architecture package is **proposed, not accepted**. Stories stamp against provisional DECs except the operator-direct paradigm DEC-0380 (ratified). Nothing in this document grants implementation, credential, order, paper-mode, promotion, live-money or destructive authority; that arrives only through the factory pipeline (ADR-0023; DEC-0380). Implementation authorization remains factory-pipeline-only even though this sitting also launches that pipeline.

## Requirements Inventory

### Functional Requirements

**A. Composition and authority (DEC-0380 / DEC-0388 / DEC-0402 / research AD-8)**

- FR-RES-01: QMA binds the operator seed tree as KnowledgeSource `source_id` `strats` via configured `root_path`. The adapter key is technical archaeology, not product brand. Reuse CT-44. (AD-2, AD-8; DEC-0382, DEC-0388)
- FR-RES-17: QMA never writes Stats. QMA never authors hypotheses. (AD-2, AD-19; DEC-0382, DEC-0399)
- FR-RES-19: Population ingest (yt-dlp / n8n / YouTube / Hermes) is out of scope until the operator starts it. The mill is source-agnostic; ingest is not this increment. (AD-2; DEC-0380)
- FR-RES-20: Target markets remain forex and crypto-spot. No futures execution in the seed. Futures/stock sources may contribute only with explicit transfer caveats. Prop-firm is an overlay, not a third library. (AD-2; DEC-0382)

**B. Seed bind, snapshot, cite (DEC-0383 / DEC-0384 / DEC-0385 / DEC-0391 / research AD-3..AD-5, AD-11)**

- FR-RES-02: Snapshot include/exclude is AD-4 and lives on the **research-corpus plugin**, not as hardcoded layout in `qma-core` / `plain_file.py`. A Mission (or session) pins one `snapshot_ref`. (AD-4, QMA AD-19; DEC-0384, DEC-0391)
- FR-RES-03: `search` is literal/locator. Hybrid / semantic / ranked search is `unsupported-capability` (GAP-0073). (AD-9; DEC-0389, DEC-0407)
- FR-RES-04: `retrieve` / `cite` run over the pinned snapshot. Cite copies bytes. Uncopied retrieve is `StaleSnapshot`, never live-tree substitution. (AD-5, AD-11; DEC-0385, DEC-0391)
- FR-RES-05: Colliding dictionary slugs are addressable only with `(file_path, id)`. QMA does not mint a parallel primitive-id scheme. (AD-5, AD-16; DEC-0385, DEC-0396)
- FR-RES-21: Browse/cite pins a `snapshot_ref` first. Unpinned live-tree reads are refused. The six confidence keys emit `unscored` until a locator carries corpus-authored scores. Never a QMA-computed scalar and never Memory `admission_confidence`. (AD-3, AD-11; DEC-0383, DEC-0391)

**C. Two-rail Library; hypotheses are not a third rail (DEC-0381 / DEC-0389 / research AD-1, AD-9)**

- FR-RES-06: Knowledge hits are not Artifact Library kinds. `register_library_kind("strats")` stays refused. Seed corpus writes no registry kinds. (AD-1, Workbench AD-3; DEC-0381)
- FR-RES-07: Product Library discovery concatenates Knowledge + Artifact typed hits via the frozen AD-9 DTO without a fourth store. Hypotheses are not a third hit class. COMP-QMA-WIRE owns the DTO (additive CT-40 family only). (AD-1, AD-9; DEC-0381, DEC-0389)
- FR-RES-18: Additive CT-40 queries for facade get/search (names illustrative). UI chrome is deferred (GAP-0081). (AD-9, AD-12; DEC-0389, DEC-0392)

**D. Stage 0 surface and honesty envelope (DEC-0394 / DEC-0395 / DEC-0396 / DEC-0400 / DEC-0401)**

- FR-RES-08: QML ships Stage 0 types in public `qml.research` on its own `RESEARCH_FORMAT_VERSION` ladder. Never sizes, never CT-23, never a seat, never cited by governed evidence. No new CT-*. No new COMP. Proposed QL-1 four-count is a docs amendment (DEC-0403), not an implementation veto. (AD-15; DEC-0395)
- FR-RES-09: QML vocabulary helpers resolve dictionary entries from **cited bytes the host passed in**. The adapter emits no structured dictionary/DNA fields. No filesystem I/O in `qml`. No registry rows. (AD-16; DEC-0396)
- FR-RES-10: Stage 0 preserves class taxonomy and F/H holes. It refuses invented exits and an invented short side. LAYOUT-DEMO stays `entry_hypothesis`; it is not extracted research to complete. (AD-6, AD-20; DEC-0386, DEC-0400)
- FR-RES-11: Hypothesis identity is `research_ref` = fp1-shaped fingerprint of class `qml-research-hypothesis`. Not a registry kind. Not a Library object. (AD-21; DEC-0401)
- FR-RES-23: A hypothesis may start from an idea, chart, journal, or seed package (source-agnostic mill). Stage 0 is not a Stats-only viewer. (AD-15; DEC-0395)
- FR-RES-25: Viewing cited seed does **not** mint `research_ref`. Explicit save returns canonical bytes. (AD-14, AD-21; DEC-0394, DEC-0401)
- FR-RES-22: Product copy uses research / hypothesis / dictionary entry / seed corpus. Not STRATS as language. Stage 0 field is `graph`, never `Confluence`. CT-34 Confluence remains the fingerprinted leg-set. (AD-18; DEC-0398)

**E. Three legal entries and mill graduation (DEC-0387 / DEC-0397)**

- FR-RES-12: Graduation uses existing `qml.conformance.registration.graduate_to_governed` after both QL-8 layers. For mill graduation `originating_research_ref` is the hypothesis `research_ref` only. Knowledge Citation digest / `artifact_ref` / `source_ref` / `seed_cite` is illegal there. Host stamps CT-07 `promoted-from` with `to_ref = research_ref`. That edge is lineage, not governed evidence. `spawn_governed` is not graduation. Do not call `qmf.structure.research.graduate_to_governed`. (AD-17; DEC-0397)
- FR-RES-13: No auto-mint of CT-33/CT-34 from DNA or graph. (AD-7; DEC-0409)
- FR-RES-14: Live handle `origin` stays the frozen string `"qma"`. Optional `seed_cite` triple `{source_ref, snapshot_ref, locator}` is a distinct non-fp1 field. Host is the single writer. Not inside CT-33 identity. No CT-07 to a Citation. (AD-7; DEC-0387)
- FR-RES-15: Ungoverned Python may skip Stage 0 (don’t-box-in). (AD-7, QL-1; DEC-0387)
- FR-RES-24: Three legal entries, none a toll booth: (1) ungoverned Python; (2) `gate_registration` without Stage 0; (3) Stage 0 save then `graduate_to_governed`. (AD-7; DEC-0387)
- FR-RES-16: Optional librarian is a skill on the same ports. No mandatory wizard. (AD-10; DEC-0390)

### NonFunctional Requirements

This increment inherits NFR-01..NFR-11 from `epics.md` / PRD §8 unchanged (environment, quality gates, determinism, measure-then-budget, secrets-as-references, append-only durability, L38 configurability, auditability, concurrency posture, one-person operability, failure-register). Node-local NFR-12..NFR-22 do not bind except where a story would otherwise touch the trading node (it must not). Increment-local NFRs:

- NFR-RES-01: Seed corpus remains usable without QMX, Hermes, n8n, or Obsidian. (AD-2; DEC-0382)
- NFR-RES-02: Reproducibility is over retained cite copies, not the live filesystem. (AD-11; DEC-0391)
- NFR-RES-03: Seed `source_id` and the six confidence keys are immutable for the life of the source. (AD-3; DEC-0383)
- NFR-RES-04: QML Stage 0 module is pure (no I/O, no threads, no process spawn). Hosts persist. (AD-15, AD-21; DEC-0395, DEC-0401)
- NFR-RES-05: Web UI first; desktop later; no account-management product. Chrome is deferred (GAP-0081). (AD-12; DEC-0392)
- NFR-RES-06: Personal operator. `root_path` is not a venue secret, not an env var, not a git path, not a `qmb` setting. (AD-8; DEC-0388)
- NFR-RES-07: Closing a UI tab cancels nothing. (AD-10; DEC-0390)
- NFR-RES-08: `source-inspected` ≠ e2e (DEC-0286, DEC-0406). Slice 0 proves real seed bytes plus the Stage 0 honesty envelope. Class/test existence of CT-44 helpers is not a pass.
- NFR-RES-09: CPython 3.14. No new runtime framework. json-render and MCP Apps are presentation candidates, not dependencies of the daemon. (architecture-QMX-2026-09-16 Stack)
- NFR-RES-10: Typed refusals (CT-04) at every public boundary: `StaleSnapshot`, `ProvenanceShapeMismatch`, `unsupported-capability` (hybrid), existing Library-kind refusals, QL-8 graduation self-edge refusal. Doors render, never swallow. (AD Consistency Conventions)
- NFR-RES-11: Cheap-veto A1–A5 on DEC-0404 stand: A1 `source_id=strats` freeze; A2 AD-4 include/exclude lists; A3 six dim spellings + `unscored`; A4 QMA AD-19 empty-corpus factual refresh only; A5 FR-RES-* on GAP-0064, GAP-0061 not closed. A factory worker may not overturn them.
- NFR-RES-12: Public formats stay the existing CT-06 / CT-07 / CT-33 / CT-34 / CT-40 / CT-44 shapes. No new contract id. Stage 0 types ride QML’s own ladder. (DEC-0395, DEC-0402)

### Additional Requirements

- AR-RES-01: Code is specified against the read-only brownfield at `integration@8510c032496bb870824ecc5c4f807e8a4e4f167e` via `git show` / `.worktrees/integration-inspect` (no checkout of `integration` onto `main`). Defects this spine forbids, not seed to copy: (1) `research-corpus` still registers in-memory `StratsCorpus` with two stub files (`notes/liquidity.md`, `notes/session.md`); (2) `qml/src/qml/research/` does not exist; (3) `KnowledgeService.cite` currently requires a caller-supplied `evidence_confidence` map and does not emit `unscored`; (4) `PlainFileLibrarySource._read_tree` hashes every non-hidden file (would include `backend/strats.sqlite` if pointed at Stats); (5) `graduate_to_governed` exists and coerces `originating_research_ref` through `fp1:sha256:<hex>` — mill identity must reuse that encoding, not invent `research:sha256:…`. (ADR-0023; DEC-0406)

- AR-RES-02: No starter template. No new distribution. Structural seed is inherited: `qmx-agents/plugins/research-corpus/daemon/plugin.py`, `qmx-agents/packages/qma-daemon/src/qma/daemon/knowledge/{plain_file.py,service.py}`, `qml/src/qml/{declaration,conformance/registration.py,generation/gaps.py,host/}`, `qmb/src/qmb/registryread/library.py`. New module home: `qml/src/qml/research/`. Host blob store: `research_root/` owned by the QML authoring composition root (`qml/src/qml/host/`). (ARCHITECTURE-SPINE Structural Seed)

- AR-RES-03: Factory touch ownership — exclusive writable surfaces, serialize wave-mates that share a component:

  | FEAT | Wave (inventory 2026-09-16) | Weight | Blocked by | Serialize with |
  |---|---|---|---|---|
  | FEAT-0047 seed bind + Stage 0 view | 16 | H | FEAT-0045, FEAT-0046, FEAT-0030 (all have story commits on `integration@8510c03`) | FEAT-0050 (both COMP-QMA-DAEMON) until 0047 merges |
  | FEAT-0048 `qml.research` + `research_ref` + blob store | 17 | H | FEAT-0047, FEAT-0030 | trails 0047 (same `qml/src/qml/research/`) |
  | FEAT-0049 mill graduation + `seed_cite` | 18 | H | FEAT-0048, FEAT-0030 | trails 0048 |
  | FEAT-0050 federated hit DTO | 15 | L | FEAT-0034, FEAT-0045, FEAT-0041 (shipped on integration) | after 0047 because of COMP-QMA-DAEMON; then may parallel 0048 (disjoint: wire/qmb vs qml) |

  Inventory `--next` still prints earlier planned rows. Do not start FEAT-0047 before its substrate (Stories 47.2, 48.4, 11.*, 12.*) is treated as present. On `integration@8510c03` those stories already have commits.

- AR-RES-04: Stories 11.*, 12.*, 34.1, 38.*, 47.2, 48.4 remain the substrate. This increment cites them; it does not re-implement the `qml` scaffold, QL-7 protocol, QL-8 two-layer gate, Library kind roster, CT-44 port, or the five desk-pack loader.

- AR-RES-05: Dead list honored: DEC-0084 (central Library/backtest service), DEC-0085/0086 (donor engines), DEC-0172 (`.qml` not revived), DEC-0408 (STRATS as QMX language), DEC-0409 (auto-mint from DNA), DEC-0410 (git subtree of Stats), DEC-0411 (compile Stage 0 `graph` → `run_slice`), DEC-0412 (`hit_class: strats` / `QmlCandidateHit`), DEC-0413 (fill GAP-0085 this increment). (ADR-0023)

- AR-RES-06: Out of this increment (Deferred table / GAP rows): GAP-0061 PRD rewrite; GAP-0063 generator algorithm; GAP-0064 is the FR-RES hole — note it, do not close it by rewriting the PRD; GAP-0073 hybrid index (layout trigger met; hybrid still deferred); GAP-0081 UI SDK / `qma-ui-contract`; GAP-0085 mechanism nouns; videos / n8n / Hermes; Workflows runtime; rewriting 239 dictionary entries; inventing exits on `STRAT-000001`; federating hypotheses into Library search; second CT-44 `source_id` over the research root; git submodule of Stats. (architecture-QMX-2026-09-16 Deferred; DEC-0380)

- AR-RES-07: SCN-0017 (Stage 0 LAYOUT-DEMO honesty envelope) binds as the golden scenario for Epic 49. A story that cannot demonstrate the Then branches, or that implements a Failure branch as a feature (invented exits, minted `research_ref`, CT-33 from DNA), is incomplete.

- AR-RES-08: Vocabulary law: say **research** / **hypothesis** / **dictionary entry** / **seed corpus**. Say **Knowledge rail** / **Artifact rail** for product Library. Ban STRATS as product language, COMP-LIB, Knowledge Base, “primitive” as a brand, revived `.qml`, DNA/STRAT-ids as UI nouns (they may appear as imported locator text). Stage 0 composition identifier is `graph`, never `Confluence`. `source_id=strats` is the adapter key only. Local `AD-1`..`AD-21` do not renumber QMF/QMB/QML/NODE/QMA/CONNECT/Workbench parents — cite parents as `QMF AD-n` / `QMA AD-n` / `Workbench AD-n` / `QL-n` / `B-n` / `TN-n`. (DEC-0398, DEC-0402)

- AR-RES-09: Each implementing spec must state, in its own prose: what must already exist (blockers with reasons), what this feature delivers that others wait on, what may run alongside (wave-mates). (qml-research-increment-brief)

- AR-RES-10: Acceptance fixtures: operator seed tree at `C:/Users/Mubarak/Desktop/Stats` when present. A test fixture MUST be bytes copied from that tree for `STRAT-000001` and dictionary entry `swing-high`, not invented stubs and not a git subtree of the whole Stats tree (DEC-0410). Do not add Stats to the QMX repo.

- AR-RES-11: File-churn split is intentional. Epics 49 and 50 both touch `qml/src/qml/research/` because AD-14 forbids minting `research_ref` in slice 0 — that risk boundary is the reason they are not one epic. Epic 49 and Epic 52 both touch COMP-QMA-DAEMON — they serialize. After 49 merges, 50 (COMP-QML) and 52 (COMP-QMA-WIRE / COMP-QMB / COMP-QMA-DAEMON) are disjoint and may run in parallel.

### UX Design Requirements

The bmad-ux spine pair `ux-QMX-2026-09-01/DESIGN.md` + `EXPERIENCE.md` exists as a folder but both files are empty scaffolds. The folder README forbids using them as implementation contracts. This increment has no UI, Penpot, or desktop-chrome work (AD-12; GAP-0081). UX-DRs below are **backend-binding objects** so a later UI session can bind without a department roster. Layout, chrome, and generated-layout reactions are deferred.

- UX-DR1: Product copy and agent prompts use research / hypothesis / dictionary entry / seed corpus. They do not brand the product STRATS. Seed-disk ids may appear as imported locator text. (FR-RES-22)
- UX-DR2: Federated search hits a later UI binds to are exactly `KnowledgeHit {hit_class: knowledge, source_ref, snapshot_ref, locator}` and `ArtifactHit {hit_class: artifact, fp1, kind}`. No `qml_candidate`. No `strats` hit_class. Display aliases on KnowledgeHits must not say “hypothesis” or “research candidate.” (FR-RES-07)
- UX-DR3: Stage 0 composition is field/type `graph`. A later UI must not export or label it `Confluence`. CT-34 Confluence remains the registry kind. (FR-RES-22)
- UX-DR4: Tab-close cancels nothing. (NFR-RES-07)
- UX-DR5: Viewing cited seed / LAYOUT-DEMO is a read-only projection and does not mint `research_ref`. Identity exists only after an explicit save. (FR-RES-25)
- UX-DR6: A later QML UI/agent MUST expose `gate_registration` without opening Stage 0. Stage 0 is not a toll booth. (FR-RES-24)
- UX-DR7: Optional librarian is a QMA Skill over `search` / `retrieve` / `cite` plus QML Stage 0 helpers. No compulsory research-to-bot wizard. (FR-RES-16)

Deferred chrome (must not appear as stories): Penpot / generated layouts; Library pages; json-render / MCP Apps as storage; `qma-ui-contract`; screen composition / departments.

### FR Coverage Map

- FR-RES-01: Epic 49 — `root_path` bind + `PlainFileLibrarySource` (Story 49.1)
- FR-RES-02: Epic 49 — AD-4 include/exclude on the plugin; Mission pin (Stories 49.2, 49.3)
- FR-RES-03: Epic 49 — literal search (Story 49.4); Epic 52 repeats GAP-0073 refusal
- FR-RES-04: Epic 49 — retrieve/cite copy + `StaleSnapshot` (Story 49.4)
- FR-RES-05: Epic 49 — colliding slugs carry `file_path` (Stories 49.4, 49.5)
- FR-RES-06: Epic 49 — `strats` kind still refuses (Story 49.6); Epic 52 inherits
- FR-RES-07: Epic 52 — federated DTO (Stories 52.1–52.3)
- FR-RES-08: Epic 50 — `qml.research` public submodule (Story 50.1)
- FR-RES-09: Epic 49 — vocab helper over host-passed bytes (Story 49.5); Epic 50 owns the lasting types
- FR-RES-10: Epic 49 — SCN-0017 LAYOUT-DEMO projection (Story 49.6); Epic 51 collapse refuses invented exits
- FR-RES-11: Epic 50 — `research_ref` identity (Story 50.2)
- FR-RES-12: Epic 51 — mill `graduate_to_governed` (Story 51.1)
- FR-RES-13: Epic 51 — no auto-mint (Story 51.4)
- FR-RES-14: Epic 51 — `origin` stays `"qma"`; optional `seed_cite` (Story 51.3)
- FR-RES-15: Epic 51 — ungoverned Python skip (Story 51.4); Epic 49 restates don’t-box-in
- FR-RES-16: Epic 52 — librarian is a skill, not a wizard (Story 52.3); no new runtime
- FR-RES-17: Epic 49 — QMA never writes Stats (Story 49.1); Epic 50 — QMA never writes `research_root` (Story 50.3)
- FR-RES-18: Epic 52 — additive CT-40 queries (Story 52.1)
- FR-RES-19: Epic 49 — no population ingest (Story 49.6)
- FR-RES-20: Epic 49 — markets/transfer caveats (Story 49.6 documentation AC)
- FR-RES-21: Epic 49 — pin + `unscored` (Stories 49.3, 49.4)
- FR-RES-22: Epic 49 — product nouns + `graph` not Confluence (Story 49.6); Epic 50 repeats the export ban
- FR-RES-23: Epic 50 — mill is source-agnostic (Story 50.1)
- FR-RES-24: Epic 51 — three legal entries (Story 51.4)
- FR-RES-25: Epic 49 — view does not mint (Story 49.6); Epic 50 — explicit save (Story 50.3)
- UX-DR1: Epic 49 — product copy (Story 49.6)
- UX-DR2: Epic 52 — hit shapes
- UX-DR3: Epic 50 — `graph` identifier
- UX-DR4: Epic 52 — tab-close (NFR-RES-07 restated)
- UX-DR5: Epic 49 / 50 — view vs save
- UX-DR6: Epic 51 — expose `gate_registration` without Stage 0
- UX-DR7: Epic 52 — no wizard

## Epic List

Four epics, one per inventory feature. They stay separate because AD-14 forbids minting `research_ref` in slice 0 (a genuine risk boundary between 49 and 50), because mill graduation identity is illegal until `research_ref` exists (50 → 51), and because federation is a different component set that is not required for slice 0 (52). Consolidating 49+50 would let a builder “complete” LAYOUT-DEMO by saving a hypothesis. That is a Failure branch of SCN-0017.

Weight tags route factory lanes: **H** heavy (`args.build_model = grok-4.6`), **L** light (`grok-4.5`). Wave numbers are the 2026-09-16 inventory waves, not a required build order beyond `blocked_by` and file-disjointness.

### Epic 49: Point QMX at the seed and see LAYOUT-DEMO honestly (Wave 16, H)

The operator can configure `root_path` to the Stats tree, pin a snapshot, cite `STRAT-000001` and `swing-high`, resolve the dictionary entry from cited bytes, and open a read-only Stage 0 projection that keeps class `entry_hypothesis` and unresolved F — with no invented exits, no `research_ref`, no CT-33, and no population ingest.

**FRs covered:** FR-RES-01, FR-RES-02, FR-RES-03, FR-RES-04, FR-RES-05, FR-RES-06, FR-RES-09, FR-RES-10, FR-RES-17, FR-RES-19, FR-RES-20, FR-RES-21, FR-RES-22, FR-RES-25
**Feature:** FEAT-0047
**Notes:** Blocked by FEAT-0045, FEAT-0046, FEAT-0030 (substrate present on `integration@8510c03`). Serialize with Epic 52 (COMP-QMA-DAEMON). SCN-0017 is the golden scenario. Delivers for FEAT-0048.

### Epic 50: Hypotheses get a QML identity and a host blob store (Wave 17, H)

The operator can save a Stage 0 hypothesis as canonical `qml.research` bytes under `research_root`, identified by `research_ref` (fp1-shaped, class `qml-research-hypothesis`), without registering it as a Library kind and without QMA writing that store.

**FRs covered:** FR-RES-08, FR-RES-11, FR-RES-17 (research_root half), FR-RES-23, FR-RES-25 (save half)
**Feature:** FEAT-0048
**Notes:** Blocked by FEAT-0047, FEAT-0030. Trails Epic 49 (same `qml/research/`). Proposed QL-1 four-count is docs, not a veto. Delivers for FEAT-0049.

### Epic 51: A hypothesis graduates; skipping Stage 0 stays legal (Wave 18, H)

The operator can graduate a saved hypothesis through existing `graduate_to_governed` with `originating_research_ref = research_ref`, optional `seed_cite`, and `origin` still `"qma"` — or skip Stage 0 entirely via `gate_registration` or ungoverned Python. No auto-mint. No invented exits.

**FRs covered:** FR-RES-12, FR-RES-13, FR-RES-14, FR-RES-15, FR-RES-24
**Feature:** FEAT-0049
**Notes:** Blocked by FEAT-0048, FEAT-0030. L33 remains two-artifact registration, not an orchestrator spawn (DEC-0270).

### Epic 52: One search concatenates Knowledge cites and Artifact fingerprints (Wave 15, L)

The operator (and later an agent) can run a federated discovery query that returns only `KnowledgeHit` and `ArtifactHit`, without a fourth store, without occupancy, and without turning hypotheses into Library hits.

**FRs covered:** FR-RES-07, FR-RES-16, FR-RES-18
**Feature:** FEAT-0050
**Notes:** Blocked by FEAT-0034, FEAT-0045, FEAT-0041 (shipped). Serialize after Epic 49 (COMP-QMA-DAEMON). Then may parallel Epic 50. Not required for slice 0.

### Stories in other increment files that this increment extends (do not duplicate)

| Existing story | What it already delivered | What QML-RESEARCH must not redo | What QML-RESEARCH closes |
|---|---|---|---|
| 11.1 | `qml` scaffold, pure, no CLI, qmf-venue ban | Second COMP; I/O in qml | `qml.research/` module home (49, 50) |
| 12.* | QL-7 protocol; QL-8 two-layer gate; `graduate_to_governed` | Fork `qmf.structure.research.graduate_to_governed`; new CT | Mill identity target of the existing helper (51) |
| 34.1 | Library kinds = existing fp1 list; `strats` refused | Add `strats` / hypothesis kind | Keep the refusal (49.6, 52) |
| 38.1 / 38.3 | Generation write-ownership QML/host; GAP-0085 unfilled | Fill GAP-0085; generator inside QMB | Stage 0 is upstream authoring, not generation (50, 51) |
| 47.2 | CT-44 snapshot / literal search / cite-copy / `StaleSnapshot` | Second knowledge port | Real seed tree + `unscored` + AD-4 filter (49) |
| 48.4 | Five desk packs including `research-corpus` | New plugin model | Replace `StratsCorpus` stub (49.1) |
| 32.2 | Tab-close cancels nothing | New cancel authority | Restate for librarian/UI (52) |

## Epic 49: Point QMX at the seed and see LAYOUT-DEMO honestly

The operator can configure `root_path` to the Stats tree, pin a snapshot, cite `STRAT-000001` and `swing-high`, resolve the dictionary entry from cited bytes the host passed in, and open a read-only Stage 0 projection that preserves class `entry_hypothesis` and unresolved F. This epic does **not** mint `research_ref`, does not persist `research_root`, does not graduate, and does not federate Library search.

**Factory touch ownership:** exclusive writable surfaces are `qmx-agents/plugins/research-corpus/` (bind + AD-4 include/exclude), `qmx-agents/packages/qma-daemon/src/qma/daemon/knowledge/service.py` (pin + `unscored` cite default — do not hardcode Stats layout into `plain_file.py`), and a **minimal** `qml/src/qml/research/` helper plus read-only projection sufficient for SCN-0017. Must not rewrite Story 47.2’s CT-44 port, Story 48.1–48.3 loader law, or QL-8. Must not add `research_ref` minting (Epic 50). Must not git-add Stats.

**Traceability for the epic:** FR-RES-01, FR-RES-02, FR-RES-03, FR-RES-04, FR-RES-05, FR-RES-06, FR-RES-09, FR-RES-10, FR-RES-17, FR-RES-19, FR-RES-20, FR-RES-21, FR-RES-22, FR-RES-25, UX-DR1, UX-DR5, NFR-RES-01, NFR-RES-02, NFR-RES-03, NFR-RES-06, NFR-RES-08, NFR-RES-11, AR-RES-01, AR-RES-07, AR-RES-10.

**What must already exist:** FEAT-0045 / Story 47.2 (KnowledgeSource, CorpusSnapshot, Citation, six `evidence_confidence` keys); FEAT-0046 / Story 48.4 (`research-corpus` pack loads); FEAT-0030 / Epics 11–12 (`qml` distribution, pure, host composition root).

**What this delivers:** real seed bytes through CT-44; AD-4 snapshot set; SCN-0017 honesty envelope. FEAT-0048 waits on it.

### Story 49.1: Replace the two-file stub with PlainFileLibrarySource at root_path

As a QMX operator,
I want the research-corpus pack to snapshot the portable Stats tree at a configured `root_path`,
So that cites are real seed bytes rather than the in-memory two-file stub.

**Traceability:** FR-RES-01, FR-RES-17, NFR-RES-01, NFR-RES-06, AR-RES-01.

**Acceptance Criteria:**

**Given** the research-corpus desk pack on `integration@8510c03`
**When** it activates
**Then** it binds `PlainFileLibrarySource(root_path, source_id="strats")` (kind `plain_file_library`) in place of in-memory `StratsCorpus`
**And** the two stub files `notes/liquidity.md` and `notes/session.md` are no longer the production corpus. (FR-RES-01; DEC-0388; DEC-0406)

**Given** `root_path`
**When** it is configured
**Then** it homes on operator-principal **plugin/daemon load config** as a filesystem path
**And** it is not an environment variable, not a git path, not a venue secret, not a `qmb` setting. (NFR-RES-06; AD-8; DEC-0388)

**Given** the canonical seed
**When** `root_path` points at the operator tree (today `C:/Users/Mubarak/Desktop/Stats`)
**Then** `snapshot()` reads that tree
**And** QMA does not copy, subtree, or write the tree into the QMX repo. (FR-RES-17; DEC-0382; DEC-0410)

**Given** `source_id="strats"`
**When** product copy, glossary, or agent prompts name the mill
**Then** they say seed corpus / dictionary entry / hypothesis / research
**And** they do not brand the product STRATS. The adapter key stays `strats` for the life of the source. (FR-RES-22; NFR-RES-03; DEC-0380; DEC-0383)

**Given** a write to the KnowledgeSource
**When** any caller invokes `write`
**Then** it is refused (`refuse_knowledge_write_back`)
**And** QMA never authors hypotheses. (FR-RES-17; Story 47.2)

### Story 49.2: Snapshot include/exclude is research-corpus plugin config

As a QMX operator,
I want snapshots to hash the seed’s source files and skip derived sqlite, tooling, and editor folders,
So that a Mission pin is stable and two adapters cannot silently disagree on the tree.

**Traceability:** FR-RES-02, NFR-RES-01, NFR-RES-11 A2.

**Acceptance Criteria:**

**Given** AD-4
**When** the production adapter snapshots
**Then** **include** (plugin config): `README.md`, `STRATS-BUILD-STATE.md`, `schema/`, `dictionary/`, `strategies/`, `sources/`, `knowledge/`, `lineage/`, `catalog/`, `IDEA.md`
**And** **exclude** (plugin config): `.hermes/`, `.obsidian/`, `backend/strats.sqlite`, `__pycache__/`, `backend/*.py`. (FR-RES-02; DEC-0384; DEC-0404 A2)

**Given** `qma-core` / `plain_file.py`
**When** layout rules are inspected
**Then** `PlainFileLibrarySource` continues to skip hidden path parts only and imposes no Stats schema
**And** the include/exclude lists are **not** hardcoded in `qma-core`. They live on the research-corpus plugin. (AD-4; QMA AD-19; AR-RES-01)

**Given** `backend/strats.sqlite` or `.obsidian/` under `root_path`
**When** `snapshot()` runs
**Then** those paths do not participate in `snapshot_ref`
**And** a second adapter that hashed them would mint a different `snapshot_ref` — there is one production adapter. (DEC-0384)

**Given** Markdown/YAML in the include set versus derived sqlite
**When** identity is discussed
**Then** the files are source of truth and sqlite is derived and disposable
**And** this story does not make sqlite a QMX store. (AD-2; NFR-RES-01)

### Story 49.3: Browse and cite pin a snapshot_ref first

As a Quant or authoring agent,
I want every retrieve/cite to run against a pinned `snapshot_ref`,
So that conclusions stay reproducible when the live seed tree later moves.

**Traceability:** FR-RES-02, FR-RES-21, NFR-RES-02.

**Acceptance Criteria:**

**Given** a Mission
**When** it uses the seed source
**Then** it pins exactly one `snapshot_ref`
**And** re-pinning is recorded; snapshots of `strats` form a linear supersedes chain. (FR-RES-02; Story 47.2; DEC-0391)

**Given** UI/agent browse **without** a Mission
**When** retrieve or cite is requested
**Then** the session still pins a `snapshot_ref` before the read
**And** an unpinned live-tree read is a typed refusal, not current bytes. (FR-RES-21; AD-11)

**Given** the live tree changes after the pin
**When** retrieve/cite runs
**Then** bytes are those of the pinned snapshot (or `StaleSnapshot` if the copy was not retained)
**And** the adapter does not silently substitute live files. (NFR-RES-02; FR-RES-04)

### Story 49.4: Search, retrieve, and cite STRAT-000001 and swing-high from real seed bytes

As an author or agent,
I want literal search plus cite-copy of `STRAT-000001` and dictionary entry `swing-high` against the pinned snapshot,
So that Stage 0 view and vocab helpers receive retained bytes rather than a stub.

**Traceability:** FR-RES-03, FR-RES-04, FR-RES-05, FR-RES-21, NFR-RES-03, NFR-RES-08, AR-RES-07, AR-RES-10.

**Acceptance Criteria:**

**Given** a pinned snapshot of the operator seed (or a fixture of bytes copied from it — AR-RES-10)
**When** a caller `search`es for `STRAT-000001` or `swing-high`
**Then** search is literal/locator (grep-class) and returns locators present in the snapshot
**And** ranking, embeddings, and hybrid indexing return `unsupported-capability` (GAP-0073). (FR-RES-03; Story 47.2)

**Given** locator for package `STRAT-000001` (LAYOUT-DEMO)
**When** the caller `retrieve`s / `cite`s against the pinned snapshot
**Then** cite copies the cited bytes into the artifact store and the Citation resolves against that copy
**And** an uncopied retrieve is `StaleSnapshot`. (FR-RES-04; DEC-0391; SCN-0017)

**Given** dictionary locator `dictionary/market-structure-and-location/locations-and-structure.md#swing-high` (or the equivalent posix path plus fragment)
**When** retrieve runs
**Then** the fragment is stripped and file bytes are returned
**And** colliding slugs require `(file_path, id)` — `swing-high` must not resolve to the wrong family file. (FR-RES-05; AD-5; DEC-0385)

**Given** first-slice cite of a locator that carries no corpus-authored scores
**When** `cite` builds Provenance
**Then** it emits the six frozen keys `extraction_confidence`, `rule_explicitness`, `source_quality_completeness`, `ambiguity_unresolved_status`, `empirical_status`, `portability_market_transfer_status` each with value `unscored`
**And** it never invents a QMA-computed scalar and never uses Memory `admission_confidence`. A mismatched key set remains `ProvenanceShapeMismatch`. (FR-RES-21; DEC-0383; DEC-0404 A3; AR-RES-01 item 3)

**Given** evidence labels on the seed
**When** they are stored
**Then** they remain opaque corpus strings, stored verbatim, never parsed into registry fields. (AD-3; DEC-0383)

**Given** Tier 1
**When** it claims slice 0 search/cite works
**Then** it proves real seed bytes (operator tree or AR-RES-10 fixture), not the two-file stub
**And** class/test existence of CT-44 helpers is not this story’s pass. (NFR-RES-08; DEC-0286; DEC-0406)

### Story 49.5: Vocabulary helper resolves swing-high from host-passed cited bytes

As an author,
I want QML to parse the 12-field dictionary record for `swing-high` from bytes the host already cited,
So that meaning lives in QML and the adapter stays a byte pipe.

**Traceability:** FR-RES-09, FR-RES-05, NFR-RES-04.

**Acceptance Criteria:**

**Given** cited bytes for `swing-high` (host-passed buffer; no path)
**When** the QML vocabulary helper resolves the entry
**Then** it returns the seed’s 12-field markdown record and eligible roles (including location / trigger / invalidation)
**And** it performs **no filesystem I/O**. (FR-RES-09; AD-16; DEC-0396; NFR-RES-04)

**Given** a colliding slug
**When** lookup runs
**Then** collision resolution uses `(file_path, id)`
**And** QML does not mint a parallel primitive id. (FR-RES-05; DEC-0385)

**Given** the research-corpus adapter
**When** it returns a search/retrieve/cite result
**Then** it returns bytes + locators + AD-4 include/exclude only
**And** it MUST NOT emit structured dictionary/DNA fields, class labels, or F maps. Meaning is computed only by `qml.research`. (AD-16; DEC-0396)

**Given** `swing-high`
**When** the helper returns
**Then** it does not register a registry row and does not mint a CT-16 producer
**And** GAP-0085 stays unfilled — eligible roles including invalidation stay on Stage 0. (FR-RES-09; DEC-0413)

**Given** `qml` purity (Story 11.1)
**When** the ambient-nondeterminism scanner scans the new helper
**Then** it spawns no thread, performs no I/O, and spawns no process. (NFR-RES-04; QL-1)

### Story 49.6: Read-only LAYOUT-DEMO projection preserves entry_hypothesis and unresolved F

As an author,
I want a read-only Stage 0 projection of LAYOUT-DEMO that refuses to invent what the seed left open,
So that slice 0 is an honesty envelope rather than a completed bot.

**Traceability:** FR-RES-06, FR-RES-10, FR-RES-19, FR-RES-20, FR-RES-22, FR-RES-25, UX-DR1, UX-DR5, AR-RES-07, SCN-0017.

**Acceptance Criteria:**

**Given** cited bytes for `STRAT-000001` (LAYOUT-DEMO) after Stories 49.4–49.5
**When** the read-only Stage 0 projection opens
**Then** it shows class `entry_hypothesis` and F labels `unresolved`
**And** it does not invent stops, take-profits, a short side, or a CT-29 close-reason. (FR-RES-10; DEC-0394; DEC-0400; SCN-0017)

**Given** that projection
**When** it returns
**Then** it does **not** return a `research_ref`
**And** viewing cited seed is not a save. Identity waits on Epic 50. (FR-RES-25; DEC-0394; DEC-0401; UX-DR5)

**Given** Boolean/temporal operators on the package (`ALL` / `THEN` / …)
**When** the projection displays them
**Then** they stay on the hypothesis plane as meaning
**And** compiling them to `run_slice`, a Graph Template, or an order adapter is refused (DEC-0411). (FR-RES-10; AD-6)

**Given** `register_library_kind("strats")`
**When** it is called
**Then** it is still refused (Story 34.1)
**And** no CT-33 / CT-34 record is minted. Auto-mint from DNA is dead (DEC-0409). (FR-RES-06; FR-RES-13)

**Given** population ingest (yt-dlp, n8n, YouTube, Hermes, vision)
**When** this epic ships
**Then** it is not started
**And** the mill remains source-agnostic without ingest. (FR-RES-19; DEC-0380)

**Given** product language in this projection and its tests
**When** names are printed
**Then** they say research / hypothesis / dictionary entry / seed corpus
**And** Stage 0 composition, if named, is `graph` not `Confluence`. (FR-RES-22; UX-DR1; DEC-0398)

**Given** ungoverned Python
**When** a caller skips Stage 0
**Then** tunnel entry remains legal
**And** this projection is not a toll booth. (FR-RES-15; DEC-0387)

**Given** SCN-0017
**When** the story is accepted
**Then** every Then branch of that scenario holds
**And** implementing a Failure branch (invented exits, minted identity, CT-33 from DNA) fails the story. (AR-RES-07)

## Epic 50: Hypotheses get a QML identity and a host blob store

The operator can save a Stage 0 hypothesis as canonical `qml.research` bytes under `research_root`, identified by `research_ref`. Viewing cited seed still does not mint identity. QMA does not write this store and does not bind a second CT-44 `source_id` over it in v1.

**Factory touch ownership:** exclusive writable surface is `qml/src/qml/research/` (public submodule + `RESEARCH_FORMAT_VERSION` + Stage 0 types) and `qml/src/qml/host/` (blob store keyed by `research_ref` under `research_root`). Must not register a qmf-registry kind. Must not write daemon sqlite. Must not fill GAP-0085.

**Traceability:** FR-RES-08, FR-RES-11, FR-RES-17, FR-RES-23, FR-RES-25, UX-DR3, UX-DR5, NFR-RES-04, NFR-RES-12, AR-RES-02.

**What must already exist:** FEAT-0047 (Epic 49) — seed bind + read-only projection that does not mint. FEAT-0030 — `qml` distribution.

**What this delivers:** durable `research_ref` and canonical bytes. FEAT-0049 waits on it.

### Story 50.1: Public qml.research on QML’s own format ladder

As a QML consumer,
I want Stage 0 types in a public `qml.research` submodule with its own `RESEARCH_FORMAT_VERSION`,
So that hosts consume one mill contract instead of forking host-private DNA files.

**Traceability:** FR-RES-08, FR-RES-23, UX-DR3, NFR-RES-04, NFR-RES-12.

**Acceptance Criteria:**

**Given** the `qml` distribution (Story 11.1)
**When** `import qml.research` runs
**Then** it is a public submodule of that distribution, not a QMA type, not a CT-*, not a host-private schema
**And** `RESEARCH_FORMAT_VERSION` is an independent integer in that module (not QL-7 protocol / QL-8 conformance versions). (FR-RES-08; DEC-0395)

**Given** Stage 0 types
**When** they are enumerated
**Then** they cover dictionary cites, role bindings, `graph` (Boolean / temporal / lifecycle meaning), evidence, unknowns, F/H labels, and class taxonomy (`entry_hypothesis` | `fragment` | `descriptive_pattern` | `composite` | `complete`)
**And** a hypothesis may start from an idea, chart, journal, or seed package — not only a Stats file. (FR-RES-23; AD-20; DEC-0386)

**Given** Stage 0
**When** it is used
**Then** it never sizes, never emits CT-23 intents, never becomes a Book/node seat, and is never cited by governed evidence (CT-32 / seats cite Bot `fp1` only)
**And** hiding Stage 0 in QMA or host-private DNA to keep QL-1’s three-count is not legal. The four-count amendment is documentation-factory, not this story’s veto. (DEC-0395; DEC-0403)

**Given** the identifier for Stage 0 composition
**When** it is exported
**Then** the field/type is `graph`
**And** `qml.research` does **not** export `Confluence` / `confluence`. CT-34 Confluence remains the registry kind. (FR-RES-22; UX-DR3; DEC-0398)

**Given** AD-15 purity
**When** the scanner runs
**Then** `qml.research` performs no I/O, spawns no thread, and spawns no process. Hosts persist. (NFR-RES-04)

**Given** an unknown `RESEARCH_FORMAT_VERSION`
**When** a host restores
**Then** it is `unavailable dependency`
**And** additive optional fields require a version bump. (AD-21; DEC-0401)

### Story 50.2: research_ref is an fp1-shaped qml-research-hypothesis fingerprint

As an author,
I want a hypothesis identified by `research_ref` that `graduate_to_governed` can already consume,
So that mill identity is content-addressed without becoming a registry kind.

**Traceability:** FR-RES-11, FR-RES-25, NFR-RES-12.

**Acceptance Criteria:**

**Given** canonical Stage 0 content
**When** identity is computed
**Then** `research_ref` is the qmf-core fingerprint of exactly `{ "class": "qml-research-hypothesis", "contract_format_version": RESEARCH_FORMAT_VERSION, "body": <canonical Stage 0 JSON> }`
**And** the value is fp1-shaped (`fp1:sha256:<hex>`). Occurrence / writer / created-at / seed `snapshot_ref` are excluded from the preimage. `body` is the canonical JSON `qml.research` returns (sorted keys; locators and meaning; not host markdown). (FR-RES-11; DEC-0401)

**Given** that `research_ref`
**When** registry/Library surfaces see it
**Then** it is **not** registered as a qmf-registry kind, does not appear on the Artifact rail, and does not reuse a `class` already used by Bot / experiment / Citation envelopes
**And** “not a registry `fp1`” means kind law, not a different string scheme. Do not invent `research:sha256:…`. (DEC-0401; AR-RES-01 item 5)

**Given** viewing cited seed / LAYOUT-DEMO (Story 49.6)
**When** the projection returns
**Then** it still does not mint `research_ref`
**And** a hypothesis exists only after an explicit save (Story 50.3). (FR-RES-25; DEC-0394)

### Story 50.3: Host blob store under research_root; explicit save returns canonical bytes

As the QML authoring host,
I want to persist only canonical Stage 0 bytes keyed by `research_ref` under `research_root`,
So that hypotheses survive without daemon sqlite, Stats write-back, or a sixth COMP store.

**Traceability:** FR-RES-17, FR-RES-25, UX-DR5, NFR-RES-04.

**Acceptance Criteria:**

**Given** an explicit QML authoring save
**When** it succeeds
**Then** it returns the canonical bytes and `research_ref`
**And** the QML authoring composition root persists **only** those bytes under `research_root`, keyed by `research_ref`. (FR-RES-25; AD-21; DEC-0401)

**Given** `research_root`
**When** it is configured
**Then** it is distinct from seed `root_path` and is **not** a QMA daemon / research-corpus setting
**And** COMP-QMA-DAEMON MUST NOT write the research root and MUST NOT bind a second CT-44 `source_id` in v1 even though files exist. (FR-RES-17; AD-8; DEC-0388)

**Given** the blob store
**When** its home is named
**Then** it is the same composition root that stamps CT-06/CT-07 for bots (`qml/src/qml/host/`)
**And** it is not daemon sqlite, not QMA AD-22 staging, not a new COMP store, not Stats, and not a second AD-4 include/exclude. Host-private files, if any, are caches of those bytes, never an identity basis. (AD-8; AD-21)

**Given** viewing cited seed without save
**When** the host is asked for a `research_ref`
**Then** none is minted
**And** UX-DR5 holds. (FR-RES-25; UX-DR5)

## Epic 51: A hypothesis graduates; skipping Stage 0 stays legal

The operator can graduate a saved hypothesis through existing `graduate_to_governed`, or skip Stage 0 via `gate_registration` or ungoverned Python. Live handle `origin` stays `"qma"`. Optional `seed_cite` is a distinct field. Unresolved F does not grow invented exits.

**Factory touch ownership:** exclusive writable surface is `qml/src/qml/conformance/registration.py` (mill-path validation of `originating_research_ref`) plus host mint of CT-07 `promoted-from` and optional `seed_cite` on the candidate. Must not treat `spawn_governed` as graduation. Must not call `qmf.structure.research.graduate_to_governed`. Must not put `seed_cite` inside CT-33/`fp1` preimage. Must not break parent QL-8 ungoverned-experiment graduation that uses a different preimage class.

**Traceability:** FR-RES-12, FR-RES-13, FR-RES-14, FR-RES-15, FR-RES-24, UX-DR6, AR-RES-05.

**What must already exist:** FEAT-0048 (Epic 50) `research_ref`. FEAT-0030 QL-8 `graduate_to_governed`, CT-33/CT-34 authoring, host CT-06/CT-07 mint.

### Story 51.1: Mill graduation passes originating_research_ref = research_ref only

As an author,
I want mill graduation to reuse `graduate_to_governed` with the hypothesis `research_ref` as the originating artifact,
So that lineage is a fingerprint the helper already understands and a Citation digest cannot masquerade as research.

**Traceability:** FR-RES-12, AR-RES-01 item 5.

**Acceptance Criteria:**

**Given** a saved hypothesis (`research_ref` from Epic 50) and two artifacts that pass both QL-8 layers
**When** mill graduation runs
**Then** it calls existing `qml.conformance.registration.graduate_to_governed`
**And** `originating_research_ref` is that hypothesis `research_ref` (class `qml-research-hypothesis`). (FR-RES-12; DEC-0397)

**Given** a Knowledge Citation digest / `artifact_ref` / `source_ref` / `seed_cite`
**When** it is passed as mill `originating_research_ref`
**Then** it is refused
**And** seed cites travel on `seed_cite` only (Story 51.3). (DEC-0397; DEC-0401)

**Given** the host
**When** it stamps the CT-07 edge
**Then** the edge is `promoted-from` with `to_ref = research_ref`
**And** that edge is **lineage, not governed evidence**: CT-32 and seats cite only the Bot `fp1`. Self-edge remains refused. (FR-RES-12; DEC-0387)

**Given** `qmf.structure.research.graduate_to_governed`
**When** mill graduation is implemented
**Then** it is not called
**And** parent QL-8 ungoverned-experiment graduation keeps its own preimage class — do not break existing tests that fingerprint `{"class": "research"}`. (AD-17; AR-RES-04)

**Given** `spawn_governed`
**When** someone calls it “graduation”
**Then** that naming is refused
**And** L33 remains two-artifact registration, not an orchestrator spawn (DEC-0270). (FR-RES-12)

### Story 51.2: Collapse open Stage 0 roles; refuse invented exits

As an author graduating LAYOUT-DEMO-shaped holes,
I want unresolved F to become empty `permitted_exit_intents` and/or Book family policy,
So that graduation cannot “complete” a hypothesis by inventing stops.

**Traceability:** FR-RES-10, FR-RES-12, DEC-0400.

**Acceptance Criteria:**

**Given** open Stage 0 eligible roles (invalidation, target, context, …)
**When** mill graduation collapses into Stage 1
**Then** CT-34 legs use only the closed enum `level | trigger | confirmation | filter`
**And** the remainder (ALL/sequence/within, invalidation, …) lands in Python WHEN, not a new CT-34 role and not GAP-0085 nouns. (DEC-0387; DEC-0413)

**Given** F labels `unresolved` (LAYOUT-DEMO)
**When** graduation produces CT-33
**Then** `permitted_exit_intents` is empty and/or exit is Book family policy
**And** graduation refuses to invent exits, producers, or CT-29 close-reasons to “complete” the hypothesis. (FR-RES-10; DEC-0400; SCN-0017)

**Given** class `entry_hypothesis`
**When** it appears on Stage 0
**Then** it is Stage 0 taxonomy, not a CT-33 field. (AD-20; DEC-0400)

### Story 51.3: origin stays "qma"; optional seed_cite is a distinct field

As a host minting a `dev`-zone candidate from a mill graduation,
I want `origin` to stay the frozen string `"qma"` and seed handoff to ride an optional `seed_cite` triple,
So that who minted the candidate stays distinct from which seed locator was cited.

**Traceability:** FR-RES-14.

**Acceptance Criteria:**

**Given** a live StrategyHandle / candidate from mill graduation
**When** `origin` is read
**Then** it is the frozen string `"qma"` (who minted)
**And** it is not reshaped into a seed locator. (FR-RES-14; DEC-0387)

**Given** optional seed handoff
**When** the host supplies it
**Then** it is `seed_cite: { source_ref, snapshot_ref, locator }` citing an existing Knowledge Citation
**And** the QML authoring composition root is the **single writer**. QMA copies it at register only if the host supplied it; QMA never invents locators. (DEC-0387)

**Given** `seed_cite`
**When** CT-33 / CT-34 / `fp1` preimage is computed
**Then** `seed_cite` is **not** inside that preimage
**And** there is **no** CT-07 edge to a Knowledge Citation. (FR-RES-14; DEC-0387)

**Given** skip-Stage-0 `gate_registration`
**When** the host still has a seed locator
**Then** `seed_cite` may still be set
**And** there is no `originating_research_ref` and no mill CT-07. (AD-7)

### Story 51.4: Three legal entries, none a toll booth; no auto-mint

As a Quant,
I want ungoverned Python, `gate_registration` without Stage 0, and Stage 0-then-graduate to all remain legal,
So that Stage 0 cannot box me in and DNA cannot mint a bot behind my back.

**Traceability:** FR-RES-13, FR-RES-15, FR-RES-24, UX-DR6.

**Acceptance Criteria:**

**Given** the three legal entries
**When** they are enumerated
**Then** (1) QMB ungoverned Python — zero QML; (2) QML `gate_registration` — CT-33 + Python, no Stage 0; (3) Stage 0 save then `graduate_to_governed` — requires a hypothesis `research_ref`
**And** none is a toll booth for the others. (FR-RES-24; DEC-0387)

**Given** QML UI/agents (when they exist) and this library surface now
**When** `gate_registration` is used
**Then** it MUST work without opening Stage 0
**And** UX-DR6 holds. (UX-DR6; AD-7)

**Given** DNA, `graph.yaml`, or a hypothesis package
**When** a caller asks to auto-mint CT-33/CT-34
**Then** it is refused
**And** executable artifacts appear only when a human (or human-approved QML authoring) produces CT-33/34 + logic. (FR-RES-13; DEC-0409)

**Given** ungoverned Python with zero qml imports
**When** it runs in QMB
**Then** it executes unchanged
**And** conformance still never gates tunnel entry (Story 11.1 / 12.*). (FR-RES-15)

## Epic 52: One search concatenates Knowledge cites and Artifact fingerprints

The operator and later an agent can concatenate CT-44 Knowledge search and QMB `library.search` into a frozen federated hit DTO. Hypotheses stay on the QML research surface. No fourth store. No occupancy. No `strats` hit class.

**Factory touch ownership:** exclusive writable surface is COMP-QMA-WIRE (additive CT-40 family for the DTO) plus the concatenate at the daemon/facade that already owns Knowledge search. COMP-QMB Artifact search stays Story 34.2. Must not open daemon sqlite from QMB. Must not persist a unified row cache. Serialize after Epic 49 (shared COMP-QMA-DAEMON).

**Traceability:** FR-RES-07, FR-RES-16, FR-RES-18, UX-DR2, UX-DR4, UX-DR7, NFR-RES-05, NFR-RES-07.

**What must already exist:** FEAT-0034 / Epic 34 Artifact-rail queries; FEAT-0045 / Story 47.2 Knowledge search; FEAT-0041 / Epic 41 wire envelope.

**What this delivers:** UI/agent search can cite the DTO. Not required for slice 0.

### Story 52.1: Frozen DTO is KnowledgeHit or ArtifactHit only

As a UI or agent author,
I want a frozen federated hit DTO owned by COMP-QMA-WIRE,
So that clients cannot invent a third hit class or a STRATS identity.

**Traceability:** FR-RES-07, FR-RES-18, UX-DR2, NFR-RES-12.

**Acceptance Criteria:**

**Given** federated discovery
**When** a hit is returned
**Then** it is exactly one of: `KnowledgeHit { hit_class: "knowledge", source_ref, snapshot_ref, locator }` or `ArtifactHit { hit_class: "artifact", fp1, kind }` where `kind` ∈ Workbench AD-3 roster **or** closed query-hit tags `saved-view` | `analysis.published` (live tokens; not registry kinds)
**And** there is no other `hit_class` — including no `qml_candidate` and no `strats`. (FR-RES-07; DEC-0389; DEC-0412; UX-DR2)

**Given** cite-copy `artifact_ref` on a Citation
**When** it appears in discovery
**Then** it is not an Artifact-rail hit
**And** durable Knowledge detail still requires a Citation after `cite`. (AD-9)

**Given** the DTO owner
**When** the package is named
**Then** it is COMP-QMA-WIRE as an **additive CT-40 family** (names illustrative)
**And** no new CT number is minted. (FR-RES-18; DEC-0389; NFR-RES-12)

**Given** `hit_class: "strats"` or `QmlCandidateHit`
**When** a client sends or a server emits it
**Then** it is refused
**And** DEC-0412 stays dead. (AR-RES-05)

### Story 52.2: Concatenate two existing queries; no fourth store; no occupancy

As an operator,
I want federated search to concatenate CT-44 search and QMB `library.search`,
So that product Library discovery does not grow a copied-row index or a door run.

**Traceability:** FR-RES-07, FR-RES-03.

**Acceptance Criteria:**

**Given** a federated search
**When** it runs
**Then** it concatenates (1) CT-44 / COMP-QMA-DAEMON Knowledge search and (2) COMP-QMB `library.search` / B-15 / ledger merge / Experiment Ledger refs per Workbench AD-3
**And** it is never a fourth store and never a door **run**. Workbench AD-8 occupancy is unchanged: this path consumes none. (FR-RES-07; DEC-0389)

**Given** QMB
**When** federated search runs
**Then** QMB never opens daemon sqlite
**And** locators are not treated as `fp1`. (AD-9)

**Given** a unified row cache / copied-row Library index / QMA staging read
**When** proposed as this path
**Then** it is refused. (DEC-0389; Workbench AD-14)

**Given** ranked/semantic/hybrid search
**When** requested
**Then** it is `unsupported-capability` (GAP-0073)
**And** v1 stays literal+locator. (FR-RES-03; DEC-0407)

### Story 52.3: Hypotheses stay on the QML research surface; librarian is optional

As an author looking for a draft hypothesis,
I want to use the QML research surface rather than Library search,
So that a seed cite cannot be mistaken for a saved hypothesis and no wizard is required.

**Traceability:** FR-RES-16, UX-DR2, UX-DR4, UX-DR7, NFR-RES-07.

**Acceptance Criteria:**

**Given** Stage 0 hypotheses
**When** federated Library search runs
**Then** they are not hits on this DTO
**And** they are found through the QML research surface (Epic 50 listing). (AD-9; DEC-0389)

**Given** display aliases on KnowledgeHits
**When** they are rendered
**Then** they MUST NOT say “hypothesis” or “research candidate”
**And** viewing cited seed still does not mint `research_ref`. (UX-DR2; FR-RES-25)

**Given** an optional librarian
**When** it exists
**Then** it is a QMA Skill / Graph Template over `search` / `retrieve` / `cite` plus QML Stage 0 helpers
**And** no wizard is required to start from a paper, idea, existing package, or ungoverned Python. (FR-RES-16; UX-DR7; DEC-0390)

**Given** a UI tab close
**When** a federated search or librarian skill is in flight
**Then** closing the tab cancels nothing
**And** json-render / MCP Apps, if later used, present DTOs and do not store or execute. (NFR-RES-07; UX-DR4; AD-12; GAP-0081)

## Final validation (Step 4)

- **FR coverage:** FR-RES-01..25 each appear in the coverage map and in at least one story AC.
- **UX-DR coverage:** UX-DR1..7 each appear in at least one story.
- **Starter template:** none. Epic 49 Story 49.1 connects an existing pack; it does not scaffold a new distribution.
- **Entities:** blob store created in Story 50.3 when first needed; no upfront mill database.
- **Forward dependencies:** none inside an epic. 49.6 uses 49.4–49.5 only. 50.3 uses 50.1–50.2. 51.2–51.4 use 51.1. 52.3 uses 52.1–52.2.
- **Epic independence:** Epic 49 is valuable without 50 (honest view, no identity). Epic 50 is valuable without 51 (save without graduate). Epic 51 needs 50’s `research_ref` (declared blocker). Epic 52 is valuable without 50 (federation of existing rails); it serializes after 49 only for COMP-QMA-DAEMON file safety.
- **File churn:** 49+50 share `qml/research/` **intentionally** (AD-14 risk boundary). 49+52 share COMP-QMA-DAEMON — serialized. Consolidation of 49+50 was considered and rejected: minting `research_ref` from LAYOUT-DEMO is SCN-0017 Failure.
- **Architecture:** reuse-only; no new COMP; no new CT; Stats not absorbed; GAP-0085/0063/0073 hybrid/0061 unfilled.
- **Provisional stamp:** stories cite provisional DECs except ratified DEC-0380. ADR-0023 remains `status: provisional`.
