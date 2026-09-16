---
id: ADR-0023
title: QML research expansion — two-stage authoring over the seed mill
type: adr
status: provisional
component: COMP-QML
depends_on: [COMP-QML, COMP-QMA-CORE, COMP-QMA-WIRE, COMP-QMA-DAEMON, COMP-QMB, COMP-QMF-REGISTRY]
decisions: [DEC-0380, DEC-0381, DEC-0382, DEC-0383, DEC-0384, DEC-0385, DEC-0386, DEC-0387, DEC-0388, DEC-0389, DEC-0390, DEC-0391, DEC-0392, DEC-0393, DEC-0394, DEC-0395, DEC-0396, DEC-0397, DEC-0398, DEC-0399, DEC-0400, DEC-0401, DEC-0402, DEC-0403, DEC-0404, DEC-0405, DEC-0406, DEC-0407, DEC-0408, DEC-0409, DEC-0410, DEC-0411, DEC-0412, DEC-0413]
sources: [_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/QML-EXPANSION.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/REQUIREMENTS-ADDENDUM.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/.memlog.md, _docwork/riders/qml-research-expansion-2026-09-16.md, _docwork/qml-research-increment-brief.md, _docwork/ledger.yaml, docs/architecture/dependencies.yaml, docs/decisions/ADR-0018-qml-bot-authoring-library.md, docs/decisions/ADR-0020-qma-agentic-system.md, docs/decisions/ADR-0022-workbench-expansion.md]
generated: 2026-09-16
verified: 2026-09-16
stale_after: 90d
---

# ADR-0023: QML research expansion — two-stage authoring over the seed mill

Date: 2026-09-16. Status: **provisional** — the architecture package is proposed, not operator-accepted. Operator-direct paradigm DEC-0380 is ratified. Absorbed local AD-1..AD-21 (DEC-0381..DEC-0401) and package umbrellas (DEC-0402..DEC-0407) are provisional. This ADR does not authorize implementation.

## Context

QMX already has bot authoring (`COMP-QML`, two artifacts, QL-1..QL-10), experimentation (`COMP-QMB`), a read-only KnowledgeSource port (`CT-44` / QMA AD-19), and a product Library that is a projection over existing `fp1` kinds (Workbench AD-3). Beside the repo sits a portable tree at `C:/Users/Mubarak/Desktop/Stats`: 239 dictionary entries, one LAYOUT-DEMO package `STRAT-000001` of class `entry_hypothesis` with all F slots `unresolved`, schema locks, population paused.

A first distill of the 2026-09-16 sitting treated that tree as a language QMX would adapt to, behind a two-rail Library facade (`LIBRARY-ADAPTATION.md`). The operator rejected that notion (DEC-0380, DEC-0408). Restated: Stats was a **staging mill** (noise → structured hypothesis) built because QMX authoring was unfinished. Absorb the mill as a **QML expansion**: two-stage bot authoring. QMF stays the framework. QML, QMB, and QMA stay libraries. QMN stays the node. No new COMP. No new CT. `source_id=strats` is the adapter key, not product copy (DEC-0380).

The child spine is `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/ARCHITECTURE-SPINE.md` (local AD-1..AD-21, status draft/proposed). Parents bind read-only. Local AD ids do not renumber QMF / QMB / QML / NODE / QMA / CONNECT / Workbench parents (DEC-0402). Implementation was inspected on `integration@8510c032496bb870824ecc5c4f807e8a4e4f167e`: `graduate_to_governed` exists; Stage 0 types do not; research-corpus still points at an in-memory two-file stub (DEC-0406). Class/test existence is not end-to-end demonstration (DEC-0286).

This ADR records the documentation-factory absorption. FR-RES-* identifiers live on GAP-0064; they do not rewrite the 2026-08-21 PRD and they do not close GAP-0061 (DEC-0405).

## Options considered

1. **Keep STRATS as QMX's language** (first distill: adapt-to-STRATS behind a two-rail Library facade). Rejected because: operator ruled STRATS is not a QMX language (DEC-0380, DEC-0408). Two vocabularies for one bot-creation job.
2. **Mint COMP-LIB / a Knowledge Base product / a mill daemon.** Rejected because: Workbench AD-1, DEC-0084 stays dead, L7 toolbox (DEC-0388, DEC-0402).
3. **Park the mill in QMA.** Rejected because: QMA is coordination plus knowledge transport (CT-44). It must not author bots (Workbench AD-4) and must not execute (QMA AD-16) (DEC-0399).
4. **Park the mill in QMB.** Rejected because: QMB is experimentation after something runnable exists. A hypothesis is not a run. `spawn_governed` is not graduation (DEC-0387, DEC-0270).
5. **Mint seed packages as registry kinds / auto CT-33 from DNA.** Rejected because: Workbench AD-3; AD-7 never auto-mint (DEC-0381, DEC-0409).
6. **Fill GAP-0085 now to fit seed DNA roles.** Rejected because: operator rider plus DEC-0413; Stage 0 already carries open roles (DEC-0396).
7. **Absorb mill as QML Stage 0** — chosen. Fourth QML surface on QML's own ladder; Stats as seed; graduate via existing `graduate_to_governed` (DEC-0380, DEC-0395, DEC-0397).

## Decision

Operator-direct paradigm is DEC-0380 (ratified). The child spine AD-1..AD-21 is absorbed as DEC-0381 through DEC-0401 (**provisional**). Umbrella and preflight are DEC-0402 (**provisional**). Parent amendments are DEC-0403 (**provisional**). Cheap-veto is DEC-0404. FR-RES hole is DEC-0405 / GAP-0064. Wiring inspect is DEC-0406. GAP-0073 layout trigger is DEC-0407.

- **AD-1 / DEC-0381 — two-rail Library; hypotheses are not a third rail.** Knowledge hits and Artifact `fp1` hits only. A hypothesis is not a Library object until CT-33 registration. `strats` stays a refused Library kind.
- **AD-2 / DEC-0382 — Stats is seed corpus.** `root_path` bind. No git subtree (DEC-0410). Product language is QML.
- **AD-3 / DEC-0383 — `source_id=strats` and six confidence keys freeze.** Adapter key, not brand. First-slice `unscored` until corpus-authored scores exist.
- **AD-4 / DEC-0384 — snapshot include/exclude is research-corpus plugin config.** Not hardcoded in `qma-core`.
- **AD-5 / DEC-0385 — locators are corpus paths.** Colliding slugs carry `(file_path, id)`.
- **AD-6 / DEC-0386 — four planes.** Research candidate / governed bot / evidence / deployment. Stage 0 `graph` is never an executor (DEC-0411).
- **AD-7 / DEC-0387 — three legal entries, none a toll booth.** Ungoverned Python; `gate_registration` without Stage 0; Stage 0 then `graduate_to_governed`. Live handle `origin` stays `"qma"`. Optional `seed_cite` is a distinct field. No auto-mint (DEC-0409).
- **AD-8 / DEC-0388 — reuse owners.** QML absorbs the mill process. No mill daemon. QMA daemon must not write `research_root` and must not bind a second CT-44 `source_id` in v1.
- **AD-9 / DEC-0389 — federated discovery concatenates two queries.** Frozen DTO: `KnowledgeHit` | `ArtifactHit`. No `qml_candidate`, no `strats` (DEC-0412). Owner: COMP-QMA-WIRE.
- **AD-10 / DEC-0390 — optional librarian.** Skill on the same ports. No mandatory wizard.
- **AD-11 / DEC-0391 — new snapshots, no dictionary merge.** Unpinned live-tree reads refused.
- **AD-12 / DEC-0392 — json-render / MCP Apps present only.** GAP-0081 stays.
- **AD-13 / DEC-0393 — Workflows sitting is a sibling.** Stage 0 `graph` is not a workflow definition.
- **AD-14 / DEC-0394 — first slice.** Seed bind + cite `STRAT-000001` and `swing-high` + read-only LAYOUT-DEMO projection that preserves `entry_hypothesis` and unresolved F. Does not mint `research_ref`. No CT-33 mint.
- **AD-15 / DEC-0395 — Stage 0 lives in `qml.research`.** Proposed QL-1 four-count (DEC-0403). No new CT-*. Hiding Stage 0 in QMA or host-private DNA to keep the three-count is not legal.
- **AD-16 / DEC-0396 — dictionary is vocabulary over files.** Helpers over host-passed bytes. GAP-0085 stays deferred (DEC-0413).
- **AD-17 / DEC-0397 — graduation is `graduate_to_governed`.** `originating_research_ref` for mill graduation is hypothesis `research_ref` only. Citation digest is illegal there. CT-07 `promoted-from` is lineage, not governed evidence.
- **AD-18 / DEC-0398 — product nouns.** research / hypothesis / dictionary entry / seed corpus. Stage 0 field is `graph`, never `Confluence`.
- **AD-19 / DEC-0399 — QMA cites; QML owns meaning.** QMA AD-19 law holds; empty-corpus sentence is a factual refresh (DEC-0403).
- **AD-20 / DEC-0400 — independence + honesty envelope.** Distinct objects. Refuse invented exits.
- **AD-21 / DEC-0401 — `research_ref` identity.** fp1-shaped `qml-research-hypothesis` fingerprint, not a registry kind. Host blob store under `research_root`.

## Architecture-preflight verdict

**reuse COMP-QML** for Stage 0 types (`qml.research`), vocabulary helpers, Stage 1 authoring, QL-8 `graduate_to_governed`, and the host composition root that stamps CT-06/CT-07 and persists `research_root`.

**reuse COMP-QMA-CORE** for the CT-44 KnowledgeSource port (definitions only).

**reuse COMP-QMA-DAEMON** for `KnowledgeService`, `PlainFileLibrarySource`, cite-copy, Mission `snapshot_ref` pin. Must not write hypotheses. Must not bind a second `source_id` in v1.

**reuse research-corpus desk pack** for seed `root_path` bind and AD-4 include/exclude. Replace in-memory `StratsCorpus` stub.

**reuse COMP-QMA-WIRE** for the federated hit DTO (additive CT-40 family only).

**reuse COMP-QMB** for Artifact-rail `library.search` / B-15. Continues to refuse `strats` as a Library kind.

**reuse COMP-QMF-REGISTRY** as kind owner. No hypothesis kind.

Candidates refused by id:

- **new COMP-LIB / Knowledge Base / mill daemon / identity store** — DEC-0388, DEC-0402; DEC-0084 stays dead.
- **`strats` Library kind / auto CT-33 from DNA** — DEC-0381, DEC-0409.
- **new CT-\* for hypotheses** — DEC-0395; QL-1 no-CT-* rule stands.
- **QMA authoring hypotheses or assembling CT-33** — DEC-0399, Workbench AD-4 / DEC-0272.
- **QMB owning the mill / treating `spawn_governed` as graduation** — DEC-0387, DEC-0270.
- **compile Stage 0 `graph` → `run_slice` / Graph Template / executor** — DEC-0411.
- **git subtree absorb of Stats** — DEC-0410.
- **`hit_class: strats` or `QmlCandidateHit` as a Library DTO class** — DEC-0412.
- **fill GAP-0085 this increment** — DEC-0413.

Dead list honored: DEC-0084, DEC-0085, DEC-0086, DEC-0172 (`.qml` not revived), DEC-0408..DEC-0413.

No existing component's authority shrinks. No new `depends_on` edge. No new contract id.

## Consequences

Easier: bot creation has an upstream honesty envelope (F/H holes, role-neutral dictionary, source-faithful evidence) inside the same library that already graduates into CT-33 + Python. Seed bytes are cited, not transplanted.

Harder: QL-1's "three thin things" sentence is a proposed amendment (DEC-0403), not a silent override. Product copy must not say STRATS. Federation must not grow a third hit class. Graduation must not treat a Citation digest as `originating_research_ref`.

Foreclosed: STRATS-as-language; COMP-LIB; auto-mint; graph-as-executor; subtree absorb; filling GAP-0085 or GAP-0063 in this sitting; starting videos/n8n/Hermes; treating this ADR as accepted architecture.

Blast radius (change mode): `COMP-QML`, `COMP-QMA-CORE`, `COMP-QMA-DAEMON`, `COMP-QMA-WIRE`, `COMP-QMB`, `COMP-QMF-REGISTRY`, and docs declaring a dependency on them. Primary edits: this ADR; `qml.md`, `qma-core.md`, `qma-daemon.md`, `qma-wire.md`, `qmb.md`, `qmf-registry.md`; CT-33/CT-34/CT-44/CT-07/CT-40/CT-32/CT-06 annotations; constitution L11/L33; AGENTS.md; glossary; gap-report GAP-0064 plus GAP-0073/0085/0061 notes; traceability; index; changelog; overview; stack; dependencies.yaml notes; SCN-0017; dated follow-ups on ADR-0018/0020/0022.

Cheap-veto (DEC-0404): A1 `source_id=strats` freeze; A2 AD-4 include/exclude lists; A3 six dim spellings + `unscored`; A4 QMA AD-19 empty-corpus factual refresh only; A5 FR-RES-* on GAP-0064, GAP-0061 not closed.

Implementation authorization remains factory-pipeline-only. First epic after docs is FEAT-0047 (AD-14 seed bind + Stage 0 view).
