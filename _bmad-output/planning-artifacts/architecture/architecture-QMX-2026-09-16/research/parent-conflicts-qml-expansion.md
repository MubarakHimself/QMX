# Parent conflicts — QML expansion absorbs STRATS mill

**Date:** 2026-09-16  
**Question:** If QML expansion absorbs the STRATS “mill” (research → candidate → author → experiment), which parent ADs hold, need a proposed amendment, or conflict?  
**Against:** Workbench AD-1..AD-16 (`architecture-QMX-2026-09-14`); QMA AD-19 (+ AD-16/AD-25); child spine AD-1..AD-14 (`architecture-QMX-2026-09-16`); L7/L10/L17/L33; DEC-0084; `qmb` workbench / library lanes on `integration@8510c03`.  
**Verdict classes:** `holds` | `proposed amendment` | `conflict`.

---

## Executive verdict

No parent **conflict** is required to absorb the mill under QML, provided three non-negotiables stay intact:

1. Research candidates owned by QML are **not** Workbench AD-3 Library objects until CT-33 (+ CT-34 + logic) registration.  
2. Stats remains a **seed KnowledgeSource import** (CT-44); product language for discovery hits is **not** “STRATS language” as an identity class.  
3. No sixth COMP / no revival of DEC-0084; ungoverned Python stays legal (L33 / QL-1 don’t-box-in).

Operator correction “don’t keep STRATS as the language; Stats is seed import” is a **factual / product-vocabulary correction**, not a QMA AD-19 law change.

---

## Especially checked

### Workbench AD-3 — STRATS = KnowledgeSource, not Library kind

| Field | Content |
| --- | --- |
| Parent rule | Shared Library objects are exactly listed `fp1` kinds. STRATS is a KnowledgeSource corpus (QMA AD-19); it does not write registry kinds. Staging, saved views, publications, Project/Workspace are not Library kinds. |
| Code | `qmb/registryread/library.py`: `STRATS_CORPUS = "KnowledgeSource"`; `strats` ∈ `NOT_LIBRARY_KIND_NAMES` / refused aliases; `COMP_LIB_MINTED = False`. |
| QML-owns-candidates question | If QML owns **research candidates** (drafts, DNA-shaped scratch, origin-pending handles) before two-artifact mint, are they Library objects? |
| **Recommendation** | **They are NOT Library objects until CT-33 registration** (composition-root mint of CT-33/CT-34 + logic identity into `qmf-registry`, typically `dev` zone). Until then they are QML-local / QMA StrategyHandle staging-adjacent **research candidates** — discovery class only, never `LIBRARY_KINDS`. |
| Status | **holds** |

Rationale: AD-3’s Prevents clause exists to stop “one bot/result as three records” and a STRATS-shaped second store. Promoting pre-registration mill output into Library kinds would be the conflict. Child AD-1 already separates Knowledge hits from Artifact (`fp1`) hits; extending that separation to a **QML-candidate** discovery class (still non-`fp1`) does not amend AD-3’s object roster.

Optional **proposed amendment** (commentary only, roster unchanged): Workbench AD-3 / product Library discovery **may federate** typed non-Library hit classes (Knowledge cite hits; QML research-candidate hits) without adding kinds. Same shape already proposed in `LIBRARY-ADAPTATION.md` §2 for Knowledge federation.

### QMA AD-19 — adapt-to-library; operator: Stats is seed, not product language

| Field | Content |
| --- | --- |
| Parent rule | Read-only plain-file KnowledgeSource; QMX adapts to the library (no write-back, no QMX fields/folders in the corpus, no hardcoded layout in `qma-core`); six `evidence_confidence` dims frozen per `source_id`; cite-copy into artifact store; literal/locator search; Knowledge ≠ Memory. Closing sentence: corpus empty / layout unratified (2026-08-28). |
| Operator now | Don’t keep STRATS as **the** language; Stats is **seed import**. |
| Law vs fact? | **Factual / product correction**, not a law change. |
| Status | **holds** (law); **proposed amendment** only for the stale empty-corpus sentence |

Why not a law change:

- **Adapt direction stands.** QMX still consumes Stats via CT-44; it does not transplant STRATS DNA into CT-33/34 or write QMX adapters into Stats (L10 / AD-19).  
- **Seed import** = bind `PlainFileLibrarySource(root_path=Stats)`, snapshot/cite; dictionary + packages remain portable evidence, not the product ontology brand.  
- **“Don’t keep STRATS as the language”** means product surfaces (Library discovery, QML mill, glossary) must not mint a durable identity class called “STRATS language.” Hits are Knowledge (`source_ref`/`snapshot_ref`/`locator`) or **QML-candidate** / Artifact — never a third `strats` kind. That aligns with Workbench AD-3 and child AD-1 Prevents (`strats` refused on Artifact rail).  
- AD-19’s last sentence (“empty today… unratified”) is **docs factual refresh** only (Stats now has layout locks + `STRAT-000001`); GAP-0073 **layout** trigger may be met; **hybrid indexing** remains deferred. Child open question already routes this to documentation-factory.

### DEC-0084 / no sixth COMP

| Field | Content |
| --- | --- |
| Dead law | DEC-0084 — centralized always-on backtest / Library service. Graveyard; AGENTS.md: never revive. |
| Workbench AD-1 | No sixth application; every capability names existing `COMP-*` or connect/extend. |
| Child AD-8 | Owners: COMP-QMA-*, COMP-QMB, COMP-QML, COMP-QMF-REGISTRY; ban COMP-LIB / `qmx-library`. |
| Code | `COMP_LIB_MINTED = False`; `QMX_LIBRARY_PACKAGE = False`. |
| Status | **holds** |

Absorbing the mill into **QML (+ existing QMA knowledge + QMB doors)** is reuse, not a COMP-LIB / central research service. A new mill daemon or identity store would be **conflict** with AD-1 / DEC-0084.

### Product Library two-rail (child AD-1) — keep discovery; rename research hit class

| Field | Content |
| --- | --- |
| Child AD-1 | Two-rail facade: Knowledge (CT-44) + Artifact (Workbench AD-3 `fp1`). Knowledge hits never Library objects / never registry kinds. |
| Parent-consistency review | Already **PASS** — federation is not a weakening of AD-3. |
| Expansion tweak | Keep two-rail for discovery. Research / mill hits that are not yet CT-33 are a **QML-candidate** discovery class (or remain Knowledge hits when they are Stats cites), **not** “STRATS language.” |
| Status | **holds** for two-rail; **proposed amendment** to child AD-1/AD-9 hit vocabulary only |

Frozen hit classes today: `KnowledgeHit` | `ArtifactHit`. Proposed additive (still non-persisted, still not a kind):

- `QmlCandidateHit` `{ hit_class: "qml_candidate", … }` — local draft / StrategyHandle-shaped research candidate **without** `fp1` Library identity; may carry optional `origin` cite to a Knowledge Citation.  
- Or fold under Knowledge until mint: only Stats-backed locators stay `knowledge`; QML-authored drafts stay host-private until registration.

Do **not** add `hit_class: "strats"` or `kind: strats`.

---

## Parent AD roll-call (Workbench + QMA + child + laws)

### Workbench (`architecture-QMX-2026-09-14`)

| AD | Status | Note |
| --- | --- | --- |
| AD-1 no sixth application | **holds** | Mill lives in QML/QMA/QMB; no COMP-EXP / COMP-LIB. |
| AD-2 three lanes | **holds** | Ungoverned / governed / coordinated door-derived; mill does not invent a fourth lane. |
| AD-3 Library projection | **holds** (+ optional discovery commentary amendment) | Candidates ≠ Library until CT-33 registration. |
| AD-4 generation ≠ search | **holds** | Mill authoring is QML write-ownership; QMA never assembles CT-33 JSON. |
| AD-5 analysis methods | **holds** | Out of mill scope; unchanged. |
| AD-6 Book/BMS candidates | **holds** | Complete `dev`-zone docs after mint; not research scratch. |
| AD-7 paper trinity | **holds** | Research-paper = QMB governed replay after graduation path. |
| AD-8 QMA→QMB door | **holds** | Coordinated experiments still CT-47 door; never `import qmb` from QMA. |
| AD-9 procedures in QMA | **holds** | Optional librarian/procedures; not STRATS `graph.yaml` as task graph. |
| AD-10..AD-13 | **holds** | Continuation / notebooks / extensibility / data — orthogonal. |
| AD-14 candidate set is a query | **holds** | Registry as-of + ledger + Experiment Ledger; does **not** read QMA staging; mill scratch stays out of this query until registered. |
| AD-15 labels | **holds** | No CT-32/B-4 extension for mill nouns. |
| AD-16 research-undertaking | **holds** | Continuity = ExperimentSpec after coordinated work; no Project kind. |

### QMA (`architecture-QMA-2026-08-28`)

| AD | Status | Note |
| --- | --- | --- |
| AD-19 Knowledge | **holds**; empty-corpus sentence = **proposed amendment** (factual) | Seed Stats import; product language ≠ STRATS brand. |
| AD-16 no execution tool | **holds** | Mill does not give QMA paper/live execution. |
| AD-18 Memory ≠ Knowledge | **holds** | Six dims vs admission scalar unchanged. |
| AD-22 staging | **holds** | RefinementProposals ≠ bots; CT-33 path is not staging. |
| AD-25 candidate-only money path | **holds** | Promote remains human outside QMA (L17). |

### Child spine (`architecture-QMX-2026-09-16`)

| AD | Status | Note |
| --- | --- | --- |
| AD-1 two-rail | **holds**; **proposed amendment** hit-class naming | Drop “STRATS language” as product identity; add QML-candidate class or keep drafts host-private. |
| AD-2 Stats canonical | **holds** | Seed path bind; no git absorb. |
| AD-3..AD-5 freeze / snapshot / locator | **holds** | `source_id=strats` may remain adapter singleton key (technical), without branding UI as STRATS-language. |
| AD-6 four planes | **holds** | Knowledge / Authoring / Evidence / Deployment — mill sits on Authoring with Knowledge cites. |
| AD-7 cite then author | **holds** | Aligns with graduation below; origin non-`fp1`. |
| AD-8 reuse owners | **holds** | QML absorbs mill **process**, not a new COMP. |
| AD-9 federated discovery | **holds** / amend hit DTO | Concatenate queries; no fourth store. |
| AD-10..AD-14 | **holds** | Librarian optional; first slice still real Stats bind for seed. |

### Constitution / graveyard / QML

| Law | Status | Note |
| --- | --- | --- |
| L7 toolbox / no sixth app | **holds** | |
| L10 wrap not transplant | **holds** | Stats seed; no STRATS→QMX contract transplant. |
| L17 human promote | **holds** | |
| L33 graduation | **holds** | Two-artifact registration + lineage — **not** orchestrator spawn (Workbench annotation / DEC-0270). |
| QL-1 don’t-box-in | **holds** | Ungoverned plain Python forever legal. |
| DEC-0084 / 0085 / 0086 | **holds** (dead) | |

---

## QMB lanes (code) — ungoverned vs governed

From `.worktrees/integration-inspect/qmb/src/qmb/workbench.py` (`integration@8510c03`):

| Door | Writes ledger / CT-32 | Library object? | L33 graduation? |
| --- | --- | --- | --- |
| Ungoverned (`qmb.run` / ordinary Python) | No | **No** (`is_library_object=False`) | **No** — `graduate_ungoverned_via_spawn` refuses; `L33_GRADUATION_IS_THIS_SPAWN=False` |
| Governed (`spawn_governed` / orchestrator) | Yes; `workbench_lane=governed` | Yes (registered kinds / CT-32) | No — lane ≠ graduation |
| Coordinated (CT-47 door) | QMB line `governed` + Experiment Ledger `coordinated` | Yes | No |

Implication for mill absorption: QML-local research and ungoverned Python exploration remain **outside** Library and outside L33 until an explicit registration act. Do not teach “run governed = graduated.”

---

## Proposed graduation path (mill → governed)

```text
research candidate (QML-local)
    → optional Knowledge cite (CT-44 snapshot_ref + locator) as origin metadata
    → two-artifact mint (CT-33 + Python logic [+ CT-34 as needed])
         composition root registers; optional CT-07 / origin cite
         (origin: non-fp1 field on StrategyHandle / dev-zone candidate only)
    → QMB governed (or coordinated via CT-47) for evidence
    → human L17 promote → QMN
```

Constraints:

- **Ungoverned Python still legal** (QL-1 / L33 / Workbench AD-2) — don’t-box-in; mill must not require CT-33 to explore.  
- L33 = extension-package + composition-root registration + lineage edge — **not** `spawn_governed`.  
- Auto-mint from DNA / `graph.yaml` remains **conflict** with child AD-7 and Workbench AD-4.  
- Research candidates are **not** Library objects and **not** AD-14 candidate-set rows until registered `fp1` kinds exist.

---

## What would be a real conflict (do not do)

| Move | Conflicts |
| --- | --- |
| Register `strats` / DNA packages as `LIBRARY_KINDS` | Workbench AD-3, child AD-1, `library.py` refuse path |
| Treat QML research drafts as Shared Library objects pre-CT-33 | Workbench AD-3, AD-14 |
| Mint COMP-LIB / central mill service | Workbench AD-1, DEC-0084, L7 |
| Keep product identity “STRATS language” as a hit/kind class | Product correction + AD-3 Prevents; adapter `source_id=strats` may stay technical only |
| Rewrite AD-19 to allow write-back / QMX fields in Stats | QMA AD-19, L10 — **law** conflict |
| Equate governed spawn with L33 graduation | L33 annotation, `workbench.py` |
| Compile `graph.yaml` → executor / `run_slice` | Child AD-6/AD-7, QMA AD-16 |

---

## Summary table (load-bearing)

| Parent | Verdict |
| --- | --- |
| Workbench AD-3 (STRATS ≠ Library; candidates need CT-33) | **holds** — recommend NOT Library until CT-33 registration |
| QMA AD-19 adapt-to-library + Stats-as-seed / not product language | **holds** (law); empty-corpus + branding = **factual/product correction** |
| DEC-0084 / no sixth COMP | **holds** |
| Child AD-1 two-rail discovery | **holds**; research hits = QML-candidate / Knowledge — **not** “STRATS language” |
| L33 + ungoverned tunnel | **holds** — graduation path as proposed; don’t-box-in |

**No conflict** blocks QML expansion absorbing the STRATS mill under the constraints above.
)