---
name: reconcile-inputs
sitting: architecture-QMX-2026-09-16
created: 2026-09-16
updated: 2026-09-16
status: review
scope: load-bearing inputs vs re-distilled spine (AD-1..AD-21 two-stage QML authoring)
supersedes: first-distill reconcile (Library facade / FR-LIB-*)
---

# Reconcile — inputs vs re-distilled spine

Compares each load-bearing input against `ARCHITECTURE-SPINE.md` (AD-1..AD-21), `QML-EXPANSION.md`, and `REQUIREMENTS-ADDENDUM.md` (`FR-RES-*`). Focus: what the AD structure dropped — especially a quiet tone or constraint.

Spine package now = two-stage QML authoring (Stage 0 mill → Stage 1 declaration) + seed import via CT-44 + two-rail product Library discovery. `LIBRARY-ADAPTATION.md` is superseded first distill; not treated as current architecture.

**Verdict: LANDED WITH QUIET MISSES.** Restart paradigm, naming, legality, parent non-negotiables, worked mapping negatives (CT-16/CT-29/no invented F), and FR-RES→AD map all hold. The AD set still thins three load-bearing quiet requirements: (1) Stage 0 is a **source-agnostic mill**, not a Stats-import viewer; (2) operator taxonomy **QMF=framework, QML/QMB/QMA=libraries**; (3) compare-note file still preaches the **superseded “meaning stays in QMA knowledge”** posture that spine/QML-EXPANSION already overturn.

---

## Per-input

### 1. Operator restart seed (`.memlog.md` paradigm-shift entries)

Seed (memlog 2026-09-16 restart-as-update + restated decision): STRATS is not a QMX language; Stats was a staging mill (noise → structured hypothesis) because QMX was unfinished; absorb as QML expansion (bot-creation library); QMF=framework; QML/QMB/QMA=libraries; no new COMP; keep AD IDs, amend rules, add AD-15+; Hermes agentics out; videos paused. User brief also names **expand beyond dictation** (mill is the filter on any noise, not a transcript/dictionary dump).

| Class | Items |
|---|---|
| **Landed** | Not-a-language / seed-not-ontology (paradigm, AD-2, AD-18). Staging mill as Stage 0 (paradigm, AD-6, AD-15). QML expansion not adapt-to-STRATS (paradigm, AD-8, AD-15..AD-21). No new COMP (AD-8, Inherited Workbench AD-1). No new CT (AD-15). Keep AD IDs + AD-15+ (local AD-1..AD-21). Graduation via existing QL-8 `graduate_to_governed` (AD-17). No Hermes fleet (Deferred Cut; AD-4 excludes `.hermes/`). Videos paused (scope, Deferred, FR-RES-19). Hypotheses not a third Library rail (AD-1, AD-9). `source_id=strats` adapter-only, never UI brand (AD-2, AD-3, AD-18). |
| **Dropped / thinned (quiet)** | **QMF=framework; QML/QMB/QMA=libraries** — companion repeats the operator sentence; spine paraphrases “QMF stays the contract hub” and “four application-layer products” (adds QMN). That muffles the standing taxonomy correction and collides with the already-overloaded noun “Library.” **Expand beyond dictation / source-agnostic mill** — QML-EXPANSION §3 states it in full (“any noisy claim — transcript, idea, chart, discretionary journal, seed package”); spine only says “the mill is source-agnostic” inside the **ingest** Deferred row, and AD-10 frames paper/idea as “no wizard,” not as Stage 0’s job. Factory can ship a LAYOUT-DEMO viewer and miss original-research authoring. |
| **Conflicts** | None with the restart. Spine includes QMN as a fourth application-layer product; operator seed listed three libraries. Compatible (QMN is the node after L17), but the “libraries” word is the one the operator used to reject a sixth COMP / STRATS language. |

### 2. `QML-EXPANSION.md` (discussion companion — should match spine)

| Class | Items |
|---|---|
| **Landed (match)** | Wrong-first-distill narrative; independence law; honesty envelope as authoring invariant (AD-20); why-not QMA/QMB/COMP-LIB/`.qml`; honest QL-1 four-surface **[PROPOSAL]** (AD-15); graduation as **collapse not translation** (AD-17 table in companion, Rule in spine); DNA B ≠ CT-32; seed vs product; worked-mapping headlines; complementary richness sequential not competing; compare-note adoption posture **superseded** (companion §7 + AD-19); refusals list (companion §8 = Deferred Cut); slice 0 (AD-14); UI/agent table (AD-9/AD-12/AD-16/AD-17/AD-21); audit SHAs. |
| **Dropped / thinned into ADs** | Filter-stack layers 0–7 live in companion, not as an AD Rule. “Pillars were human lenses, not a closed schema” — companion only. “A developer who is not a trader can cite `bullish-engulfing` instead of reinventing prose” — qualitative dictionary usefulness, no AD/FR. “Conformance gates **citation and seats**, never tunnel entry” — AD-7 has don’t-box-in skip; the gate-scope sentence is companion-only. “Specking a bot meant a candidate specification” — substance in AD-6/AD-15 (non-executable), tone not restated. |
| **Companion↔spine drift** | Companion keeps operator “QMF is the framework / three libraries” wording; spine uses parent “application-layer products.” Companion §3 mill-is-the-filter is stronger than any AD Prevents. Both correctly supersede the compare note. No AD contradicts the companion. |

### 3. `REQUIREMENTS-ADDENDUM.md` FR-RES-* → ADs

All `FR-RES-01`..`FR-RES-22` and `NFR-RES-01`..`NFR-RES-08` cite a spine AD. Mapping holds. Inverse: several AD constraints have **no FR**, so epics sliced from the addendum will miss them.

| ID | Spine | Map |
|---|---|---|
| FR-RES-01 bind `root_path` / `source_id=strats` | AD-2, AD-8 | ok |
| FR-RES-02 snapshot include/exclude + Mission pin | AD-4, QMA AD-19 | ok |
| FR-RES-03 literal search; hybrid GAP-0073 | AD-9 (+ Inherited QMA AD-19) | ok (AD-9 is federation; literal law is also parent) |
| FR-RES-04 retrieve/cite; `StaleSnapshot` | AD-5, AD-11 | ok |
| FR-RES-05 colliding slugs need `file_path` | AD-5, AD-16 | ok |
| FR-RES-06 Knowledge ≠ Artifact kinds; `strats` refused | AD-1, Workbench AD-3 | ok |
| FR-RES-07 federated DTO; hypotheses not a third hit class | AD-1, AD-9 | ok |
| FR-RES-08 Stage 0 QML-local ladder; no new CT/COMP | AD-15 | **thin** — misses AD-15 thin-by-law: never sizes, never CT-23, never seat, never cited by governed evidence |
| FR-RES-09 vocab helpers; no registry rows | AD-16 | ok |
| FR-RES-10 class taxonomy + F/H; no invented exits | AD-6, AD-20 | ok (LAYOUT-DEMO note present) |
| FR-RES-11 `research_ref` not `fp1` | AD-21 | **thin** — misses occurrence/writer/created-at excluded; cross-version restore = `unavailable dependency` |
| FR-RES-12 `graduate_to_governed` + distinct ref + CT-07 | AD-17 | ok (collapse details stay in AD/companion) |
| FR-RES-13 no auto-mint from DNA/graph | AD-7 | ok |
| FR-RES-14 origin non-`fp1`; host single writer | AD-7 | ok |
| FR-RES-15 don’t-box-in skip Stage 0 | AD-7, QL-1 | ok |
| FR-RES-16 optional librarian; no mandatory wizard | AD-10 | ok |
| FR-RES-17 QMA never writes Stats; never authors hypotheses | AD-2, AD-19 | ok |
| FR-RES-18 additive CT-40 facade queries | AD-9, AD-12 | ok |
| FR-RES-19 population out of scope | AD-2 | ok |
| FR-RES-20 forex + crypto-spot; no futures exec; caveats; prop overlay | AD-2 | ok |
| FR-RES-21 session pin; six keys `unscored` until corpus-authored | AD-3, AD-11 | ok |
| FR-RES-22 product copy = research / hypothesis / dictionary entry / seed corpus | AD-18 | ok |
| NFR-RES-01 seed usable without QMX/Hermes/n8n/Obsidian | AD-2 | ok |
| NFR-RES-02 reproducibility = cite copies | AD-11 | ok |
| NFR-RES-03 `source_id` + six keys immutable | AD-3 | ok |
| NFR-RES-04 QML Stage 0 pure; hosts persist | AD-15, AD-21 | ok |
| NFR-RES-05 web first; desktop later; no account-management | AD-12 | ok |
| NFR-RES-06 personal operator; `root_path` not a venue secret | AD-8 | ok |
| NFR-RES-07 UI tab close ≠ cancel | AD-10 | ok |
| NFR-RES-08 source-inspected ≠ e2e; slice 0 real bytes | AD-14, DEC-0286 | ok |

**ADs with no FR:** AD-13 (Workflows fence — listed under “Explicitly not required now”; acceptable). AD-14 covered via NFR-RES-08 not a functional FR (slice 0 is still the first epic in the docs-factory handoff).

**FR gaps (quiet):** AD-15 thin-by-law bullets; AD-21 restore-refusal; source-agnostic original-research origin (no FR says a hypothesis may start from an idea/chart/journal with zero seed package).

### 4. `research/naming-qml-expansion.md`

| Class | Items |
|---|---|
| **Landed** | Banned STRATS-as-language, second language, COMP-LIB, Knowledge Base, primitive-as-brand (AD-18 + conventions). Recommended set research / hypothesis / dictionary entry / seed corpus (AD-18). Lifecycle seed→cite→hypothesis→graduation→declaration (AD-7, AD-17, AD-18). Seed-disk ids may remain on disk (AD-2, AD-18). Homonym confluence called in AD-18. `.qml` revival banned (AD-18, Inherited QL-2). |
| **Dropped / thinned** | Synonym “research artifact” until graduated — spine uses `research_ref` / “research candidate”; fine. Naming one-liner not copied into conventions table (table is equivalent). |
| **Conflicts** | None. |

### 5. `research/mill-pipeline.md`

| Class | Items |
|---|---|
| **Landed** | Two-stage owner table (AD-15/AD-17). Stats as portable seed (AD-2). No new COMP/CT; no `strats` kind; no auto CT-33; `graph.yaml` never executor (paradigm, AD-6, AD-7). Independence law (AD-20). Dictionary = helpers over files (AD-16). Slice 0 acceptance 1–6 ≈ AD-14 + AD-8 stub replace. Open points 1–3 **closed by spine:** host-private research root (AD-21), QML-local ladder (AD-15), dictionary growth in seed not a QML overlay (AD-16). Open point 4 (`source_id` freeze) remains an Open question. CT-34 enum unchanged; GAP-0085 deferred; L17; confluence homonym. |
| **Dropped / thinned** | mill-pipeline mermaid `EDIT → CT-44 → CT-34` can be read as QMA assembling confluence; prose says human/QML authoring. Spine AD-19 is the correct owner (QMA transport only). Slice check “stub replaced or unused” is AD-8, not restated as an AD-14 acceptance bullet. |
| **Conflicts (research stale vs spine)** | (a) Open-design-points section still lists store shape / Stage-0 typing / dictionary write policy as open; spine decided them. (b) “Explicitly later: Federated Library hit DTO” — spine AD-9/AD-12 freeze the DTO **this sitting** (chrome later). QML-EXPANSION §10 matches spine; mill-pipeline does not. |

### 6. `research/qml-expansion-legality.md`

| Class | Items |
|---|---|
| **Landed** | Fourth surface via QL-7/QL-8 mechanism, no CT-*, no new COMP (AD-15). Honest **[PROPOSAL] QL-1** three→four (AD-15 + Inherited proposed amendments). Graduation into two artifacts does not violate QL-2 (AD-17). Dictionary files-until-cite; no registry; no auto CT-16 (AD-16, AD-6). GAP-0085 stays deferred. Thin-by-law: not a second shared-contract stratum; not seat-citable; never sizes; never CT-23; never Book/node seat (AD-15 Rule). No Hermes/videos/`.qml`/graph-as-executor. Prior AD-1..AD-14 adapt-to-STRATS paradigm marked superseded (companion header + memlog). |
| **Dropped / thinned** | Parent-touch #2 “add a short QL-# or QL-8 subsection: research-candidate contract + graduation identity” is **not** in the spine’s proposed parent-amendment list (only QL-1 count, Workbench AD-3 commentary, QMA AD-19 empty-corpus sentence). Local AD-17 covers the identity; docs-factory may amend QL-1 and leave parent QL-8 still talking only about “ungoverned experiment.” |
| **Conflicts** | None. Mechanism already parent-legal; count amendment is flagged, not silent. |

### 7. `research/parent-conflicts-qml-expansion.md`

| Class | Items |
|---|---|
| **Landed** | Three non-negotiables: candidates ≠ Library until CT-33; Stats = seed import not identity class; no sixth COMP / don’t-box-in (AD-1, AD-2, AD-8, AD-21, AD-7). Workbench AD-3 holds; QMA AD-19 law holds + empty-corpus factual refresh; DEC-0084 holds; L33 ≠ `spawn_governed` (AD-17); QMA never `import qmb` (Inherited). Real-conflict table matches spine Prevents. |
| **Dropped / thinned** | Optional **proposed amendment** to federate a `QmlCandidateHit` `{ hit_class: "qml_candidate" }` — **explicitly rejected** by AD-9 (“No other `hit_class`”; Stage 0 found on QML research surface). This is a deliberate resolution, not an accidental drop. Record it so a later epic does not “helpfully” add the research note’s DTO. |
| **Conflicts** | Research offered additive hit class; spine forbade it. Spine wins. Parent-conflicts also allowed “fold under Knowledge until mint”; AD-9 forbids using Knowledge hits as a disguise for hypotheses. |

### 8. `inputs/worked-mapping.md`

| Class | Items |
|---|---|
| **Landed** | Case 1 `swing-high` = dictionary entry, not CT-16/CT-33 (AD-16, AD-6, AD-14). Informal CT-34 translation is handoff aid (AD-7). Case 2 `STRAT-000001` = `entry_hypothesis`, all F `unresolved`, no invented exits (AD-14, AD-20, FR-RES-10). Colliding `liquidity-sweep` must carry `file_path` (AD-5). Graph not `run_slice`; WHEN in Python (AD-6). Lineage triad Plane I ≠ CT-07 ≠ ExperimentSpec `branches-from` (AD-6). Case 3 `level-invalidation` must not become CT-29 (AD-6). Trigger ≠ order (AD-6). Boolean/temporal operators not CT-34 declaration (AD-6). F labels named `source_defined` / `external_policy` / `deliberately_open` / `unresolved` (AD-6). |
| **Dropped / thinned (quiet)** | **Asymmetric short** — still only in worked-mapping “cannot yet express.” Graduation must not invent a short side for LAYOUT-DEMO. **Unresolved pair/TF/session params** — covered generically by H unknowns (AD-20), not named. **CT-23 remainder** for invalidation/stop/management — AD-7 says Book/F; mapping’s CT-23 cite dropped. **Must not become CT-10** from empty SRC / DNA B (mapping case 2) — AD-20 says DNA B ≠ CT-32; CT-10 never named. **LAYOUT-DEMO is not extracted research** (evidence-summary) — slice 0 preserves holes but never says “do not treat this package as a real strategy to complete.” |
| **Conflicts** | None. Risk remains factory stories reading only ADs. |

### 9. `inputs/evidence-summary.md`

| Class | Items |
|---|---|
| **Landed** | Authority BUILD-STATE over GROUND-STATE (companion audit). validate.py OK / 239 / 229 unique / 9 collisions / LAYOUT-DEMO (AD-14, companion). DNA lock; `graph.yaml` knowledge (AD-6). 12 fields; do not rewrite 239 (Deferred). Population paused (Deferred, FR-RES-19). `Desktop/strats` debris (AD-2). Workbench AD-3 refuse `strats` (AD-1). CT-44 read-only; empty-corpus sentence stale (Inherited proposed amendment). Stub vs `PlainFileLibrarySource` (AD-8). Reuse list (AD-8). Rejected ceremony list → Deferred Cut. Adapter hashing sqlite → AD-4 exclude. GAP-0081 stub (AD-12). PRD gap → addendum. |
| **Dropped / thinned** | **86 ontology-seed entries** as a distinct corpus fact (only case 3 touches thin seeds). **Zero real `SRC-*` / zero `kb-*` notes** — not in spine. **`.hermes` is historical evidence, not instructions** — exclude list + Cut, tone quieter. **LAYOUT-DEMO is a layout demo, not extracted research** — see worked-mapping. **`PlainFileLibrarySource` currently hashes sqlite` as today’s bug** — AD-4 fixes the rule; factory acceptance delta is implicit in the exclude list. |
| **Conflicts** | None. |

### 10. `research/compare-strats-vocab-vs-qml.md`

| Class | Items |
|---|---|
| **Landed (as ontology table)** | Complementary richness (identity/footprint/conformance vs meaning/F/H/graph/class). Confluence homonym (AD-18). Informal role bridge (AD-7). Do not auto-mint, do not fill GAP-0085, do not import primitives as CT-16 (AD-6, AD-16, Deferred). `graph.yaml` never executor (AD-6). |
| **Supersession check (required)** | Note’s **Adoption posture** still says: meaning, evidence, unknowns, F labels, graph operators, dictionary → **QMA knowledge**. **Spine AD-19 and QML-EXPANSION §7 explicitly supersede that:** meaning **types** move into QML Stage 0; QMA remains cite **transport**; seed **bytes** stay files. Confirmation: **companions say so; the compare file itself is unstamped and still teaches the old ownership column on ~15 rows.** |
| **Dropped / thinned** | Sample depth (`swing-high` boundaries, `liquidity-sweep` “smart money intent” non-transferable) lives only in the note. AD-2 microstructure sentence covers CEX/DOM/funding, not that dictionary-level non-transfer example. |
| **Conflicts** | **Stale ownership column vs AD-19.** Any agent that opens the compare note without QML-EXPANSION §7 will park Stage 0 types in QMA. Docs-factory handoff does **not** list this file as an exact input (safer) but QML-EXPANSION still points at it as “full table.” |

---

## First-distill drops — recovered vs still open

Previous reconcile (Library facade / `FR-LIB-*`) listed quiet misses. Re-distill recovery:

| First-distill drop | Re-distill |
|---|---|
| Markets / futures discipline | **Recovered** AD-2, FR-RES-20 |
| Microstructure non-transfer (CEX/DOM/funding) | **Recovered** AD-2 |
| Prop-firm overlay ≠ third library | **Recovered** AD-2 |
| STRATS §8 exclusion list | **Recovered** AD-2 |
| CT-16 / CT-29 negative mints | **Recovered** AD-6 |
| Trigger ≠ order; ALL/sequence not declaration | **Recovered** AD-6 |
| F slot labels named | **Recovered** AD-6 |
| RefinementProposal applied-not-promote | **Recovered** AD-7 |
| Rejected-ceremony Cut rows | **Recovered** Deferred |
| Graph operator classes named | **Recovered** AD-6 |
| Evidence-label vocabulary freeze (enumerated set) | **Still thinned** — AD-3 “opaque, never parse,” set not listed |
| Asymmetric short | **Still dropped** |
| CT-23 remainder | **Still dropped** |
| 86 ontology-seed count | **Still dropped** |
| LAYOUT-DEMO skill/prompt “not-QML-ready” labelling | **Still dropped** |
| DEC-0333 do-not-reorder QMA build | **Still dropped** |
| Qualitative exploration depth as Library UX | **Superseded by restart** (mill, not Library-as-product) — do not revive as a miss |
| C1 “everything under QMF as libraries” park | **Operator resolved** (QMF=framework; three libraries) but spine did not stamp the resolution in those words |

---

## Landed (summary)

- Restart paradigm: two-stage QML authoring; Stats = seed mill import; STRATS ≠ QMX language; no new COMP/CT; no Hermes/videos.
- Product Library stays two-rail discovery; hypotheses are not Library objects / not a third `hit_class`.
- Seed freeze: `source_id=strats` technical, six dims, snapshot include/exclude, locators, cite-copy, no git absorb, markets/overlay/§8 bans.
- Stage 0 on QML’s own ladder; honest QL-1 amendment; QMA cites; QML owns meaning types (superseding compare-note posture **in spine + QML-EXPANSION**).
- Independence + honesty envelope (AD-20); graduation collapse (AD-17); don’t-box-in; L33 ≠ spawn.
- Worked mapping outcomes: `swing-high` stays a dictionary entry; `STRAT-000001` stays `entry_hypothesis` with unresolved F; no invented exits.
- Every `FR-RES-*` / `NFR-RES-*` maps to at least one AD.
- Naming set + confluence homonym + Deferred Cut of rejected mill ceremony.

## Dropped (summary — quiet requirements AD structure lost)

1. **Source-agnostic mill / expand beyond dictation** — Stage 0 is the filter on *any* noise (idea, chart, journal, transcript, seed), not a Stats-package viewer. Strong in QML-EXPANSION §3; in the spine only as an ingest Deferred clause + AD-10 “no wizard.” Highest quiet miss: factory slice-0 success can look like “we bound Stats” and never author a hypothesis that did not come from disk.
2. **QMF=framework; QML/QMB/QMA=libraries** — operator taxonomy. Spine says contract-hub / application-layer products. Tone/constraint that blocks a mill-COMP and a QMF-ladder Stage 0, already partly enforced by AD-8/AD-15, but the words the operator used did not land as an AD/conventions row.
3. **Compare-note file still assigns meaning ownership to QMA knowledge.** Spine/companion supersede; the note is unstamped. Quiet because an ontology table looks more “complete” than AD-19’s three sentences.
4. **Pillars = human lenses, not CT-34’s four roles.** Companion only. Informal bridge in AD-7 can be misread as schema merge.
5. **Asymmetric short + unresolved pair/TF/session** as named do-not-invent (worked-mapping).
6. **Evidence-label vocabulary** still opaque-not-enumerated; **CT-23** remainder; **CT-10** negative from empty SRC.
7. **AD-15 thin-by-law and AD-21 restore-refusal** have no FR (epics-from-addendum hole).
8. **LAYOUT-DEMO is a layout demo, not extracted research** — no prompt/skill labelling AD; 86 ontology-seed entries unstated.
9. **Parent QL-8 subsection** (legality parent-touch #2) omitted from proposed parent amendments.
10. mill-pipeline mermaid / “DTO later” / still-open store-shape — research stale vs spine (not a spine miss; a companion-hygiene miss).

## Conflicts

| Id | Conflict | Resolution in package |
|---|---|---|
| K1 | Briefing-era short confidence keys vs integration long keys | Unchanged: AD-3 uses plugin spellings; Open question asks operator confirm |
| K2 | `IDEA.md` optional-include vs AD-4 include | AD-4 includes; Open question on snapshot set |
| K3 | compare-note “meaning → QMA knowledge” vs AD-19 / QML-EXPANSION §7 | **Spine + companion supersede.** Compare file not rewritten. |
| K4 | parent-conflicts optional `QmlCandidateHit` vs AD-9 closed DTO | **Spine rejects** additive hit class; v1 QML research surface only |
| K5 | mill-pipeline “federated DTO later” + still-open AD-15+ points vs spine decisions | Spine is current; mill-pipeline is a pre-distill research note |
| K6 | mill-pipeline mermaid CT-44 → CT-34 vs AD-19 QMA-never-authors | Spine AD-19 wins; mermaid is misleading |

No local AD silently overrides a parent. Proposed parent touches remain tagged **[PROPOSAL]**.

## Top gaps (priority)

1. **Source-agnostic mill (expand beyond dictation)** — the quiet requirement most likely to vanish in epics. Needs an AD-15/AD-10 Prevents clause or a FR: a hypothesis may originate from a paper/idea/chart/journal with no seed package; Stage 0 is not an import viewer.
2. **Compare-note stale ownership** — stamp the file superseded, or factory agents will re-park meaning in QMA.
3. **QMF=framework / three-libraries wording** — one conventions row would lock the operator’s taxonomy against “application-layer product” drift.
4. **FR holes on AD-15 thin-by-law + AD-21 restore-refusal + named worked-mapping non-claims (asymmetric short).**
5. **K1 confidence-key spelling** — still blocks life-of-source freeze until operator review (carried Open question; correct).

## Path

`C:/Users/Mubarak/Desktop/QMX/_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/reviews/reconcile-inputs.md`
