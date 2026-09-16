---
name: REQUIREMENTS-ADDENDUM
type: requirements-addendum
status: proposed
created: '2026-09-16'
updated: '2026-09-16'
covers: QML Stage 0 research mill + seed import via CT-44 + product Library facade
note: Does not rewrite prd-QMX-2026-08-21. Sibling to GAP-0061 (workbench FRs). First-distill FR-LIB-* ids are superseded by FR-RES-*. Proposed identifiers for documentation-factory / epics.
---

# Requirements addendum — QML research expansion (proposed)

The 2026-08-21 PRD has QMB/QML FRs and a QMA phase boundary. It has **no** mill / seed-corpus / hypothesis FRs. GAP-0061 covers ExperimentSpec / analysis methods / generation / procedures — not this expansion. Epics must not pretend the old PRD specified the following.

All IDs below are **proposed**. Documentation-factory assigns ledger DECs after operator acceptance. First-distill `FR-LIB-*` rows are superseded; do not implement both sets.

## Functional

| ID | Requirement | Spine | Notes |
|---|---|---|---|
| FR-RES-01 | QMA binds the operator seed tree as KnowledgeSource `strats` via configured `root_path` | AD-2, AD-8 | reuse CT-44; adapter key is not product brand |
| FR-RES-02 | Snapshot include/exclude as AD-4; Mission pins one `snapshot_ref` | AD-4, QMA AD-19 | |
| FR-RES-03 | `search` is literal/locator; hybrid refused GAP-0073 | AD-9 | |
| FR-RES-04 | `retrieve`/`cite` over pinned snapshot; cite copies bytes; uncopied → `StaleSnapshot` | AD-5, AD-11 | |
| FR-RES-05 | Colliding dictionary slugs addressable only with `file_path` | AD-5, AD-16 | |
| FR-RES-06 | Knowledge hits are not Artifact Library kinds; `strats` refused as registry kind | AD-1, Workbench AD-3 | |
| FR-RES-07 | Product Library discovery concatenates Knowledge + Artifact typed hits via the frozen AD-9 DTO without a fourth store; hypotheses are not a third hit class | AD-1, AD-9 | COMP-QMA-WIRE owns DTO |
| FR-RES-08 | QML ships Stage 0 types in public `qml.research` on its own ladder; never sizes, never CT-23, never seat, never cited by governed evidence; no new CT-*; no new COMP | AD-15 | proposed QL-1 amendment is docs-factory, not a veto |
| FR-RES-09 | QML vocabulary helpers resolve dictionary entries from host-passed cited bytes; adapter emits no DNA fields; no registry rows | AD-16 | |
| FR-RES-10 | Stage 0 preserves class taxonomy and F/H holes; refuses invented exits and invented short side | AD-6, AD-20 | LAYOUT-DEMO stays `entry_hypothesis`; not extracted research to complete |
| FR-RES-11 | Hypothesis identity is `research_ref` = fp1-shaped fingerprint with class `qml-research-hypothesis`; not a registry kind; not a Library object | AD-21 | |
| FR-RES-12 | Graduation uses `graduate_to_governed`: both QL-8 layers, `originating_research_ref` = hypothesis `research_ref` only, host-stamped CT-07 edge; Citation digest illegal here | AD-17 | spawn_governed is not graduation |
| FR-RES-13 | No auto-mint of CT-33/34 from DNA or graph | AD-7 | |
| FR-RES-14 | Live handle `origin` stays `"qma"`; optional `seed_cite` triple is a distinct field; host is the single writer; not inside CT-33 identity; no CT-07 to a Citation | AD-7 | |
| FR-RES-15 | Ungoverned Python may skip Stage 0 (don’t-box-in) | AD-7, QL-1 | |
| FR-RES-16 | Optional librarian is a skill on the same ports; no mandatory wizard | AD-10 | |
| FR-RES-17 | QMA never writes Stats; QMA never authors hypotheses | AD-2, AD-19 | |
| FR-RES-18 | Additive CT-40 queries for facade get/search (names illustrative) | AD-9, AD-12 | UI chrome deferred |
| FR-RES-19 | Population ingest (yt-dlp/n8n/YouTube) is out of scope until operator starts it | AD-2 | mill is source-agnostic |
| FR-RES-20 | Markets: forex + crypto-spot; no futures execution; transfer caveats required; prop-firm overlay only | AD-2 | |
| FR-RES-21 | Browse/cite pins a `snapshot_ref`; six confidence keys use `unscored` until corpus-authored | AD-3, AD-11 | |
| FR-RES-22 | Product copy uses research / hypothesis / dictionary entry / seed corpus; not STRATS as language; Stage 0 field is `graph` not Confluence | AD-18 | |
| FR-RES-23 | A hypothesis may start from an idea, chart, journal, or seed package (source-agnostic mill) | AD-15 | not a Stats-only viewer |
| FR-RES-24 | Three legal entries: ungoverned Python; `gate_registration` without Stage 0; Stage 0 then graduate | AD-7 | none is a toll booth |
| FR-RES-25 | Viewing cited seed does not mint `research_ref`; explicit save returns canonical bytes | AD-14, AD-21 | |

## Non-functional

| ID | Requirement | Spine |
|---|---|---|
| NFR-RES-01 | Seed corpus remains usable without QMX, Hermes, n8n, or Obsidian | AD-2 |
| NFR-RES-02 | Reproducibility over retained cite copies, not the live filesystem | AD-11 |
| NFR-RES-03 | Seed `source_id` and six confidence keys immutable for the life of the source | AD-3 |
| NFR-RES-04 | QML Stage 0 module is pure (no I/O); hosts persist | AD-15, AD-21 |
| NFR-RES-05 | Web UI first; desktop later; no account-management product | AD-12 |
| NFR-RES-06 | Personal operator; `root_path` is not a venue secret | AD-8 |
| NFR-RES-07 | Closing a UI tab cancels nothing | AD-10 |
| NFR-RES-08 | source-inspected ≠ e2e; slice 0 proves real seed bytes + Stage 0 view | AD-14, DEC-0286 |

## Explicitly not required now

GAP-0073 hybrid index; GAP-0085 nouns; GAP-0063 generator; GAP-0081 UI SDK; Workflows runtime; rewriting 239 dictionary entries; inventing exits on `STRAT-000001`; federating hypotheses into Library search; second CT-44 source over the research root; video population.
