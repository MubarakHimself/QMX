#!/usr/bin/env python3
"""Append QML research-expansion change-mode YAML. Run once from project root. Idempotent by id."""
from pathlib import Path

ROOT = Path(r"C:/Users/Mubarak/Desktop/QMX")


def already(text: str, needle: str) -> bool:
    return needle in text


def append_if_missing(path: Path, marker: str, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if already(text, marker):
        print(f"skip {path.name}: {marker} already present")
        return
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + block, encoding="utf-8")
    print(f"appended {marker} -> {path.name}")


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if label in text and old not in text:
        print(f"skip {path.name}: {label} already patched")
        return
    if old not in text:
        raise SystemExit(f"{path.name}: block not found for {label}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"patched {label} -> {path.name}")


MANIFEST = r"""
- id: SRC-19
  path: _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/
  kind: rider
  role: primary
  status: harvested
  note: "2026-09-16 QMX QML research-expansion architecture sitting (restart-as-update; spine status draft/proposed, not operator-accepted): ARCHITECTURE-SPINE.md (local AD-1..AD-21 plus Inherited Invariants, Consistency Conventions, Stack, Structural Seed, Capability map, Deferred, Open questions), QML-EXPANSION.md (current companion; supersedes LIBRARY-ADAPTATION.md), REQUIREMENTS-ADDENDUM.md (FR-RES-* proposed), DOCUMENTATION-FACTORY-HANDOFF.md, .memlog.md, inputs/evidence-summary.md, inputs/worked-mapping.md, research/qml-expansion-legality.md, research/parent-conflicts-qml-expansion.md, research/naming-qml-expansion.md, research/mill-pipeline.md, reviews/. Citation surface for the QML research increment (EXT-2213..EXT-2245). LIBRARY-ADAPTATION.md is the superseded first distill and is not current. Parents QMF AD-1..41, QMB B-1..15, QML QL-1..10, NODE TN-1..25, QMA AD-1..29, CONNECT AD-1..5, Workbench AD-1..16 bind read-only. Local AD ids do not renumber parents. Implementation inspected on integration@8510c032496bb870824ecc5c4f807e8a4e4f167e."
- id: SRC-20
  path: _docwork/riders/qml-research-expansion-2026-09-16.md
  kind: rider
  role: primary
  status: harvested
  note: "Operator-direct rider for the 2026-09-16 documentation-factory change-mode session: STRATS is not a QMX language; Stats is a staging mill absorbed as QML two-stage authoring; QMF=framework, QML/QMB/QMA=libraries, QMN=node; no new COMP; no new CT; source_id=strats is adapter key not product copy; architecture package proposed not accepted; do not fill GAP-0085; do not start videos/n8n/Hermes; first epic = AD-14 seed bind + Stage 0 view. Citation surface for the operator's own words (DEC-0380)."
"""

EXTR = r"""
  - id: EXT-2213
    type: decision
    summary: "Operator-direct: STRATS is not a QMX language. Stats was a staging mill (noise to structured hypothesis) because QMX was unfinished. Absorb the mill as a QML expansion: two-stage bot authoring. Stage 0 = research hypotheses (dictionary, bindings, graph, holes). Stage 1 = existing CT-33 + Python + QL-8. Graduation is graduate_to_governed. QMF = framework. QML / QMB / QMA = libraries. QMN = node. No new COMP. No new CT. Stats is seed corpus only; source_id=strats is the adapter key, not product copy."
    quote: "STRATS is not a QMX language. Stats was a staging mill (noise → structured hypothesis) because QMX was unfinished. Absorb that mill as a QML expansion: two-stage bot authoring."
    cite: SRC-20
    topics: [qml, research, mill, seed-corpus, no-new-comp]
    authority: rider
  - id: EXT-2214
    type: decision
    summary: "Architecture package review_status is proposed — not operator-accepted. Absorbed AD-1..AD-21 and derived package rulings stamp provisional. LIBRARY-ADAPTATION.md is the superseded first distill and is not current."
    quote: "The package is proposed, not accepted, unless I say otherwise in this session. If not accepted, stamp every absorbed ruling proposed/provisional."
    cite: SRC-20
    topics: [provisional, package-standing]
    authority: rider
  - id: EXT-2215
    type: decision
    summary: "AD-1 — Product Library stays two-rail (Knowledge cites + Artifact fp1). Hypotheses are not a third rail, not a registry kind, and not Library objects until CT-33 registration. qmb.registryread.library continues to refuse strats. No hit_class strats."
    quote: "Workbench AD-3 Library-object set and kind roster are unchanged. Product Library discovery federates two typed hit classes only. A QML hypothesis is not a Library object and not a registry kind until Stage 1 registration mints CT-33/CT-34."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-1
    topics: [ad-1, library, hypothesis]
    authority: rider
  - id: EXT-2216
    type: decision
    summary: "AD-2 — Canonical seed is the portable tree at operator-configured root_path (today C:/Users/Mubarak/Desktop/Stats). Copy/subtree into QMX git is forbidden. Desktop/strats is debris. Population stays paused. Target markets forex and crypto-spot. Product language for the mill is QML."
    quote: "Canonical seed is the portable tree at the operator-configured root_path (today C:/Users/Mubarak/Desktop/Stats). Copy/subtree into QMX git is forbidden."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-2
    topics: [ad-2, seed-corpus, root_path]
    authority: rider
  - id: EXT-2217
    type: decision
    summary: "AD-3 — Exactly one KnowledgeSource binds singleton key source_id strats, kind plain_file_library, as the seed adapter. That key is technical archaeology, not UI/glossary language. Six confidence_dimensions freeze for life. Until corpus-authored scores exist, first-slice cite must emit the six keys with value unscored."
    quote: "Exactly one KnowledgeSource binds singleton key source_id strats, kind plain_file_library, as the seed adapter. That key is technical archaeology, not UI/glossary language."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-3
    topics: [ad-3, source_id, confidence]
    authority: rider
  - id: EXT-2218
    type: decision
    summary: "AD-4 — Snapshot include/exclude is research-corpus plugin adapter config, not a seed schema and not hardcoded in qma-core / plain_file.py. Include README.md, STRATS-BUILD-STATE.md, schema/, dictionary/, strategies/, sources/, knowledge/, lineage/, catalog/, IDEA.md. Exclude .hermes/, .obsidian/, backend/strats.sqlite, __pycache__/, backend/*.py."
    quote: "The adapter's snapshot set is configuration of the research-corpus plugin, not fields written into Stats and not hardcoded layout in qma-core / plain_file.py."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-4
    topics: [ad-4, snapshot, research-corpus]
    authority: rider
  - id: EXT-2219
    type: decision
    summary: "AD-5 — Seed locator is posix relative path plus optional #heading fragment. Colliding slugs carry (file_path, id). QMA does not mint a parallel primitive id scheme."
    quote: "Seed locator = posix relative path, optional #heading fragment. Bindings and graph nodes for a colliding slug must name (file_path, id) as the seed already requires."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-5
    topics: [ad-5, locator, collisions]
    authority: rider
  - id: EXT-2220
    type: decision
    summary: "AD-6 — Four planes: (1) research candidate / hypothesis (2) governed bot CT-33+Python+CT-34 (3) evidence QMB/CT-32 (4) deployment QMN paper|live. Stage 0 graph is never an executor. Trigger is not order. Dictionary entry must not become a CT-16 producer or CT-29 close-reason by import."
    quote: "A Stage 0 graph is never an executor, backtest spec, Graph Template, or order adapter. Trigger ≠ order."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-6
    topics: [ad-6, four-planes, graph]
    authority: rider
  - id: EXT-2221
    type: decision
    summary: "AD-7 — Three legal entries, none a toll booth: ungoverned Python; gate_registration without Stage 0; Stage 0 save then graduate_to_governed requiring research_ref. Never auto-mint CT-33 from DNA. spawn_governed is not graduation. Live handle origin stays qma. Optional seed_cite is a distinct non-fp1 field. No CT-07 edge to a Knowledge Citation."
    quote: "Three legal entries, none a toll booth for the others: (1) QMB ungoverned Python — zero QML; (2) QML gate_registration — CT-33 + Python, no Stage 0; (3) Stage 0 save then graduate_to_governed — requires a hypothesis research_ref."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-7
    topics: [ad-7, graduation, seed_cite, dont-box-in]
    authority: rider
  - id: EXT-2222
    type: decision
    summary: "AD-8 — Reuse existing owners. QML absorbs the mill process. No new COMP, no new CT, no mill daemon. Replace in-memory StratsCorpus with PlainFileLibrarySource(root_path, source_id=strats). Hypothesis persistence owner is the QML authoring composition root. COMP-QMA-DAEMON must not write the research root and must not bind a second CT-44 source_id in v1."
    quote: "Reuse-or-new only. Owners: COMP-QML, COMP-QMA-CORE, COMP-QMA-DAEMON, desk pack research-corpus, COMP-QMB, COMP-QMF-REGISTRY, COMP-QMA-WIRE. No federating COMP, no mill daemon."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-8
    topics: [ad-8, reuse, preflight]
    authority: rider
  - id: EXT-2223
    type: decision
    summary: "AD-9 — Federated discovery concatenates two existing queries. Frozen hits: KnowledgeHit {hit_class knowledge, source_ref, snapshot_ref, locator} and ArtifactHit {hit_class artifact, fp1, kind}. No qml_candidate and no strats hit_class. Stage 0 hypotheses are found through the QML research surface. Owner of the federated hit DTO is COMP-QMA-WIRE."
    quote: "No other hit_class — including no qml_candidate and no strats. Stage 0 hypotheses are found through the QML research surface, not this DTO."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-9
    topics: [ad-9, federated-discovery, dto]
    authority: rider
  - id: EXT-2224
    type: decision
    summary: "AD-10 — Optional librarian is a QMA Skill/Graph Template over search/retrieve/cite plus QML Stage 0 helpers. No mandatory wizard. Closing a UI tab cancels nothing."
    quote: "A contextual librarian is a QMA Skill/Graph Template over search/retrieve/cite plus QML Stage 0 helpers. No wizard is required."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-10
    topics: [ad-10, librarian]
    authority: rider
  - id: EXT-2225
    type: decision
    summary: "AD-11 — Seed edits happen in Stats. QMA learns them by snapshot plus recorded re-pin. Cite copies remain pinned-snapshot bytes. Browse without a Mission still pins a session snapshot_ref. Unpinned live-tree reads are refused. Colliding slugs stay keepers."
    quote: "UI/agent browse without a Mission still pins a session snapshot_ref before retrieve/cite; unpinned live-tree reads are refused."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-11
    topics: [ad-11, snapshot-pin]
    authority: rider
  - id: EXT-2226
    type: decision
    summary: "AD-12 — json-render and MCP Apps present; they do not store or execute. Native web UI is first; qma-ui-contract stays GAP-0081."
    quote: "They are not identity, persistence, or authority. Native web UI is first; desktop later. qma-ui-contract stays GAP-0081."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-12
    topics: [ad-12, presentation]
    authority: rider
  - id: EXT-2227
    type: decision
    summary: "AD-13 — Workflows sitting consumes citations, hypotheses, and doors, not DNA graphs. This sitting does not choose a workflow runtime."
    quote: "A Stage 0 graph is not a workflow definition. This sitting does not choose a workflow runtime or editor."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-13
    topics: [ad-13, workflows]
    authority: rider
  - id: EXT-2228
    type: decision
    summary: "AD-14 — First vertical slice is seed bind plus a Stage 0 view: configure root_path; snapshot per AD-4; search/retrieve/cite STRAT-000001 and one dictionary entry; Mission pin; QML vocabulary helper resolves swing-high from cited bytes the host passed in; read-only Stage 0 projection of LAYOUT-DEMO preserves entry_hypothesis and unresolved F. The projection does not mint research_ref. No CT-33 mint. register_library_kind(strats) still refuses."
    quote: "The projection does not mint research_ref and is not a wizard. LAYOUT-DEMO is not extracted research to complete. register_library_kind(\"strats\") still refuses; no CT-33 mint; no population ingest."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-14
    topics: [ad-14, first-slice]
    authority: rider
  - id: EXT-2229
    type: decision
    summary: "AD-15 — Stage 0 types live in public qml.research on QML's own format-version ladder (RESEARCH_FORMAT_VERSION). Not CT-33 helpers, not QMA types, not host-private schemas. QML still mints no QMF-ladder CT-* shared contract. Proposed QL-1 amendment: four thin things. Hiding Stage 0 in QMA or host-private DNA to keep the three-count is not legal."
    quote: "Stage 0 types live in qml.research, a public submodule of the qml distribution, on QML's own format-version ladder. QML still mints no QMF-ladder (CT-*) shared contract."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-15
    topics: [ad-15, qml.research, ql-1]
    authority: rider
  - id: EXT-2230
    type: decision
    summary: "AD-16 — Dictionary is vocabulary over files, not 239 registry kinds. QML ships parse/validate/lookup helpers over bytes the host passed in. Eligible roles stay on Stage 0. CT-34 enum unchanged. GAP-0085 stays deferred. Adapter must not emit structured dictionary/DNA fields."
    quote: "A dictionary entry is a role-neutral file record. QML ships parse/validate/lookup helpers over bytes the host passed in — QML performs no filesystem I/O. GAP-0085 stays deferred."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-16
    topics: [ad-16, dictionary, gap-0085]
    authority: rider
  - id: EXT-2231
    type: decision
    summary: "AD-17 — Graduation is graduate_to_governed, not a QMB spawn. originating_research_ref for mill graduation MUST be the hypothesis research_ref (class qml-research-hypothesis). Knowledge Citation digest / artifact_ref / source_ref / seed_cite is not a legal originating_research_ref. Host stamps promoted-from CT-07 with to_ref = research_ref. That edge is lineage, not governed evidence."
    quote: "Knowledge Citation digest / artifact_ref / source_ref / seed_cite is not a legal originating_research_ref. Seed cites travel on AD-7 seed_cite only."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-17
    topics: [ad-17, graduate_to_governed]
    authority: rider
  - id: EXT-2232
    type: decision
    summary: "AD-18 — Product nouns are QMX / QML; STRATS is seed-disk only. Mill surface = research. Package = hypothesis. Vocab item = dictionary entry. Stats tree = seed corpus. Never export Confluence / confluence from qml.research. CT-34 Confluence remains the fingerprinted leg-set registry kind."
    quote: "Banned in product language: STRATS as ontology brand, second language, COMP-LIB, Knowledge Base, primitive as a brand. Homonym: Stage 0 composition is field/type graph. Never export Confluence / confluence from qml.research."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-18
    topics: [ad-18, naming]
    authority: rider
  - id: EXT-2233
    type: decision
    summary: "AD-19 — QMA cites; QML owns meaning. QMA Knowledge port remains read-only transport. QMA does not parse dictionary/DNA meaning. QMA AD-19 law holds; empty-corpus sentence is a docs factual refresh only."
    quote: "QMA's Knowledge port remains read-only transport: snapshot, search, retrieve, cite-copy. QML owns Stage 0 types, vocabulary helpers, and Stage 1 authoring."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-19
    topics: [ad-19, qma-cites, qml-owns-meaning]
    authority: rider
  - id: EXT-2234
    type: decision
    summary: "AD-20 — Independence law: dictionary entry ≠ binding ≠ graph ≠ hypothesis ≠ declaration ≠ logic ≠ CT-32 ≠ seat. Stage 0 must preserve F labels and H unknowns. Graduation refuses to invent exits, producers, or CT-29 close-reasons to complete a hypothesis."
    quote: "Graduation refuses to invent exits, producers, or CT-29 close-reasons to complete a hypothesis. Class entry_hypothesis / fragment / descriptive_pattern / composite / complete is Stage 0 taxonomy, not a CT-33 field."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-20
    topics: [ad-20, honesty-envelope]
    authority: rider
  - id: EXT-2235
    type: decision
    summary: "AD-21 — Hypothesis identity is research_ref = qmf-core fingerprint of {class qml-research-hypothesis, contract_format_version RESEARCH_FORMAT_VERSION, body}. fp1-shaped so graduate_to_governed can consume it; must not be registered as a qmf-registry kind. Host blob store keyed by research_ref under research_root. Viewing cited seed is not a save."
    quote: "A hypothesis is identified by research_ref = qmf-core fingerprint of exactly { class: qml-research-hypothesis, contract_format_version: RESEARCH_FORMAT_VERSION, body }. The value is fp1-shaped so graduate_to_governed can consume it, and must not be registered as a qmf-registry kind."
    cite: SRC-19:ARCHITECTURE-SPINE.md#ad-21
    topics: [ad-21, research_ref]
    authority: rider
  - id: EXT-2236
    type: constraint
    summary: "Do not start YouTube/n8n/Hermes population. Do not fill GAP-0085. Do not implement production code. After docs emit an epics-and-stories handoff; first epic = AD-14 seed bind + Stage 0 view. Do not launch epics."
    quote: "Do not start videos/n8n/Hermes. Do not fill GAP-0085. Do not implement code. After docs, emit an epics-and-stories handoff; first epic = AD-14 seed bind + Stage 0 view. Do not launch epics yourself."
    cite: SRC-20
    topics: [out-of-scope, first-epic]
    authority: rider
  - id: EXT-2237
    type: context
    summary: "Integration inspect 8510c03: graduate_to_governed exists in qml/conformance/registration.py. Stage 0 types do not. research-corpus plugin still uses in-memory two-file StratsCorpus stub, not Stats. PlainFileLibrarySource exists and currently hashes all non-hidden files including backend/strats.sqlite. qmb registryread library refuses strats. qma-ui-contract is a stub (GAP-0081)."
    quote: "graduate_to_governed exists; Stage 0 types do not. research-corpus still points at an in-memory two-file stub."
    cite: SRC-19:QML-EXPANSION.md
    topics: [wiring, integration-inspect]
    authority: rider
  - id: EXT-2238
    type: open
    summary: "Open cheap-veto: confirm source_id=strats freeze key and the six confidence dimension spellings; confirm AD-4 include/exclude lists. Defaults are the integration plugin values and the spine lists."
    quote: "Confirm source_id=strats as the seed adapter freeze key (not a product brand) and the six dim spellings. Confirm snapshot include/exclude (AD-4)."
    cite: SRC-19:ARCHITECTURE-SPINE.md#open-questions
    topics: [cheap-veto, source_id, ad-4]
    authority: rider
  - id: EXT-2239
    type: death
    summary: "First distill LIBRARY-ADAPTATION.md (adapt-to-STRATS as a second QMX language behind a two-rail Library facade) is superseded. STRATS-as-QMX-language stays dead."
    quote: "LIBRARY-ADAPTATION.md is the superseded first distill — do not fold it as current."
    cite: SRC-20
    topics: [dead, first-distill, strats-language]
    authority: rider
  - id: EXT-2240
    type: death
    summary: "Auto-mint of CT-33/34 from DNA or graph is refused. Compile Stage 0 graph into run_slice / executor is refused. Git subtree/copy Stats into QMX is forbidden. hit_class strats and QmlCandidateHit as a Library DTO are refused. Filling GAP-0085 to fit DNA roles this increment is refused."
    quote: "No auto-mint of CT-33/34 from DNA or graph. A Stage 0 graph is never an executor. Copy/subtree into QMX git is forbidden. No qml_candidate and no strats. GAP-0085 stays deferred."
    cite: SRC-19:ARCHITECTURE-SPINE.md
    topics: [dead, auto-mint, graph-executor, subtree, hit-class]
    authority: rider
  - id: EXT-2241
    type: constraint
    summary: "FR-RES-01..FR-RES-25 and NFR-RES-01..08 are proposed identifiers in REQUIREMENTS-ADDENDUM.md. They do not rewrite prd-QMX-2026-08-21. They are a sibling hole to GAP-0061. First-distill FR-LIB-* ids are superseded. Do not close GAP-0061."
    quote: "Does not rewrite prd-QMX-2026-08-21. Sibling to GAP-0061 (workbench FRs). First-distill FR-LIB-* ids are superseded by FR-RES-*."
    cite: SRC-19:REQUIREMENTS-ADDENDUM.md
    topics: [fr-res, gap-0061, gap-0064]
    authority: rider
  - id: EXT-2242
    type: correction
    summary: "QMA AD-19 last sentence (empty corpus / layout unratified) is factually stale. Stats now has 239 dictionary entries, LAYOUT-DEMO, schema locks. The read-only adapt-to-library law stands. This is a docs factual refresh, not a law change."
    quote: "QMA AD-19's law holds. The closing sentence empty corpus / layout unratified is factually stale (239 dictionary entries, LAYOUT-DEMO, schema locks). That is a docs refresh, not a law change."
    cite: SRC-19:QML-EXPANSION.md
    topics: [qma-ad-19, empty-corpus, factual-refresh]
    authority: rider
  - id: EXT-2243
    type: context
    summary: "GAP-0073 layout trigger is met in the seed; hybrid retrieval remains deferred. v1 literal+locator search only."
    quote: "GAP-0073 hybrid / semantic index — Layout revisit trigger is met in the seed; hybrid retrieval is a separate irreversible index choice. v1 literal+locator."
    cite: SRC-19:ARCHITECTURE-SPINE.md#deferred
    topics: [gap-0073]
    authority: rider
  - id: EXT-2244
    type: context
    summary: "Proposed parent amendments, not silent overrides: (1) QL-1 surface count three thin things to four, adding Stage 0. (2) Workbench AD-3 commentary — product discovery may federate Knowledge hits as a distinct class; kind roster unchanged. (3) QMA AD-19 last sentence factual refresh."
    quote: "The amendment is a documentation-factory obligation, not an implementation veto. Factory implements qml.research against this child AD."
    cite: SRC-19:ARCHITECTURE-SPINE.md#inherited-invariants
    topics: [parent-amendments, ql-1]
    authority: rider
  - id: EXT-2245
    type: context
    summary: "Worked mapping: swing-high survives as a dictionary entry, not a CT-16 producer. STRAT-000001 survives as hypothesis class entry_hypothesis with all F unresolved. level-invalidation stays a thin dictionary entry, not a CT-29 close-reason. Lineage planes: seed I ≠ CT-07 ≠ ExperimentSpec branches-from."
    quote: "Stage 0 view must not invent exits. Graduation, if anyone later authors a bot, is human/QML: CT-34 legs + Python ALL/THEN, CT-33 with empty exit intents."
    cite: SRC-19:inputs/worked-mapping.md
    topics: [worked-mapping, layout-demo, swing-high]
    authority: rider
"""

LEDGER = r"""
  - id: DEC-0380
    title: "Operator-direct paradigm — mill absorbed as two-stage QML authoring; STRATS is not a language"
    statement: "STRATS is not a QMX language. Stats was a staging mill (noise to structured hypothesis) because QMX was unfinished. Absorb that mill as a QML expansion: two-stage bot authoring. Stage 0 = research hypotheses (dictionary, bindings, graph, holes). Stage 1 = existing CT-33 + Python + QL-8. Graduation is graduate_to_governed. QMF is the framework. QML, QMB, and QMA are libraries. QMN is the node. No new COMP. No new CT. Stats is seed corpus only. source_id=strats is the adapter key, not product copy. The architecture package at architecture-QMX-2026-09-16 is proposed, not accepted; absorbed AD-1..AD-21 stamp provisional. LIBRARY-ADAPTATION.md is superseded and is not current. Do not start videos/n8n/Hermes. Do not fill GAP-0085. Do not implement production code from this documentation-factory pass. First epic after docs is AD-14 seed bind plus Stage 0 view."
    status: ratified
    rationale: "Direct operator ruling in the 2026-09-16 documentation-factory session. Rider wins over architecture-package commentary. The sitting's 21 ADs remain proposed until the operator accepts the package."
    sources: [EXT-2213, EXT-2214, EXT-2236, EXT-2239]
    authority: rider
    component: COMP-QML
    tags: [law, qml, research, mill, operator-direct]
    date: 2026-09-16
    spine_ref: "SRC-20"

  - id: DEC-0381
    title: "QML-research AD-1 — Product Library stays two-rail; hypotheses are not a third rail"
    statement: "Workbench AD-3 Library-object set and kind roster are unchanged. Product Library discovery federates two typed hit classes only (AD-9): Knowledge (seed cites) and Artifact (fp1). A QML hypothesis is not a Library object and not a registry kind until Stage 1 registration mints CT-33/CT-34. qmb.registryread.library continues to refuse strats. Display aliases never mint a third identity. Federation is a discovery DTO, not a fifth persistence surface."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-1. Package is proposed, not operator-accepted (DEC-0380)."
    sources: [EXT-2215]
    authority: rider
    component: COMP-QML
    tags: [qml-research, ad-1, library, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-1"

  - id: DEC-0382
    title: "QML-research AD-2 — Stats is the seed corpus; QMX points, it does not absorb"
    statement: "Canonical seed is the portable tree at the operator-configured root_path (today C:/Users/Mubarak/Desktop/Stats). Markdown/YAML files are source of truth; SQLite is derived and disposable. QMA snapshots that tree. Copy/subtree into QMX git is forbidden. Submodule is deferred until a remote host cannot receive a path. Desktop/strats is debris. Population stays paused until the operator starts it. Target markets remain forex and crypto-spot; no futures execution in the seed; futures/stock sources may contribute only with explicit transfer caveats. Prop-firm is an overlay, not a third library. Stats must not contain QMX adapters, executors, CT-33/34, Book/BMS bindings, run ledgers, genetic machinery, BMS/KSA/MIS, certification, or account/position/agent memory. Product language for the mill is QML. Seed-disk ids (STRAT-NNNNNN, kebab slugs) may remain on disk; they are not product nouns."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-2. Package proposed (DEC-0380)."
    sources: [EXT-2216]
    authority: rider
    component: COMP-QMA-DAEMON
    tags: [qml-research, ad-2, seed-corpus, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-2"

  - id: DEC-0383
    title: "QML-research AD-3 — Seed source_id and six confidence keys freeze for life"
    statement: "Exactly one KnowledgeSource binds singleton key source_id strats, kind plain_file_library, as the seed adapter. That key is technical archaeology, not UI/glossary language. CT-44 Provenance/Citation use source_ref for that source. confidence_dimensions are exactly extraction_confidence, rule_explicitness, source_quality_completeness, ambiguity_unresolved_status, empirical_status, portability_market_transfer_status. Changing them is a new source_id, not an in-place rename. Evidence labels are opaque seed-corpus strings — QMA stores verbatim, never parses. Until a locator carries corpus-authored scores, first-slice cite must emit the six keys with value unscored (corpus-owned default), never a QMA-computed scalar and never Memory admission_confidence. That default is not live adapter behaviour on integration@8510c03 (cite currently requires a caller-supplied map)."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-3. Freeze key remains cheap-veto (DEC-0404). Package proposed (DEC-0380)."
    sources: [EXT-2217, EXT-2238]
    authority: rider
    component: COMP-QMA-CORE
    tags: [qml-research, ad-3, source_id, ct-44, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-3"

  - id: DEC-0384
    title: "QML-research AD-4 — Snapshot include/exclude is adapter config, not a seed schema"
    statement: "The adapter's snapshot set is configuration of the research-corpus plugin, not fields written into Stats and not hardcoded layout in qma-core / plain_file.py. qma-core stays layout-agnostic; PlainFileLibrarySource continues to skip hidden path parts only. Include (plugin config): README.md, STRATS-BUILD-STATE.md, schema/, dictionary/, strategies/, sources/, knowledge/, lineage/, catalog/, IDEA.md. Exclude (plugin config): .hermes/, .obsidian/, backend/strats.sqlite, __pycache__/, backend/*.py. Two adapters that hash different include sets mint different snapshot_refs — there is one production adapter."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-4. Include/exclude lists remain cheap-veto (DEC-0404). Package proposed (DEC-0380)."
    sources: [EXT-2218, EXT-2238]
    authority: rider
    component: COMP-QMA-DAEMON
    tags: [qml-research, ad-4, snapshot, research-corpus, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-4"

  - id: DEC-0385
    title: "QML-research AD-5 — Seed locators are corpus paths; colliding slugs carry file_path"
    statement: "Seed locator equals posix relative path plus optional #heading fragment. Retrieve strips the fragment and returns file bytes. Bindings and graph nodes for a colliding slug must name (file_path, id) as the seed already requires. QMA does not mint a parallel primitive id scheme. qma-core stays layout-agnostic; path/heading conventions live in the research-corpus adapter. Hypothesis identity is a different locus (DEC-0401)."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-5. Package proposed (DEC-0380)."
    sources: [EXT-2219]
    authority: rider
    component: COMP-QMA-CORE
    tags: [qml-research, ad-5, locator, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-5"

  - id: DEC-0386
    title: "QML-research AD-6 — Four planes stay distinct"
    statement: "Four planes: (1) research candidate — Stage 0 hypothesis (dictionary cites, bindings, graph, DNA-shaped holes); seed files feed this plane via cite; a hypothesis may also start with zero seed package. (2) governed bot — CT-33 + Python logic + CT-34. (3) evidence — QMB ledger + CT-32 (and ExperimentSpec on the coordinated lane). (4) deployment — QMN paper | live after human promote. A Stage 0 graph is never an executor, backtest spec, Graph Template, or order adapter. Trigger is not order. Boolean/temporal operators (ALL / sequence / within / ...) stay on the hypothesis or later Python WHEN, not CT-34 declaration. A dictionary entry must not become a CT-16 producer or a CT-29 close-reason by import. Class entry_hypothesis with unresolved F must not be completed by QMX invention. F labels (source_defined / external_policy / deliberately_open / unresolved) stay on the hypothesis. Seed lineage (I) is not CT-07 and is not ExperimentSpec branches-from."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-6. Package proposed (DEC-0380)."
    sources: [EXT-2220, EXT-2245]
    authority: rider
    component: COMP-QML
    tags: [qml-research, ad-6, four-planes, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-6"

  - id: DEC-0387
    title: "QML-research AD-7 — Handoff is cite, author a hypothesis, then graduate; never auto-mint"
    statement: "Three legal entries, none a toll booth for the others: (1) QMB ungoverned Python — zero QML; (2) QML gate_registration — CT-33 + Python, no Stage 0; (3) Stage 0 save then graduate_to_governed — requires a hypothesis research_ref. QML UI/agents MUST expose (2) without opening Stage 0. Executable artifacts appear only when a human (or human-approved QML authoring) produces CT-33/34 + logic. QMB then validates on a legal lane. Only a human promotes onto the node. RefinementProposals are applied, never promoted. Live StrategyHandle origin stays the frozen string qma. Optional seed handoff is a distinct non-fp1 field seed_cite: { source_ref, snapshot_ref, locator } citing an existing Knowledge Citation — never a reshape of origin. Single writer of seed_cite: the QML authoring composition root. QMA copies it at register only if the host supplied it; QMA never invents locators. seed_cite must not enter CT-33/CT-34/fp1 preimage. No CT-07 edge to a Knowledge Citation. Skipping Stage 0 means no originating_research_ref and no mill CT-07; seed_cite may still be set. Informal role translation (location≈level, trigger≈trigger, filter≈filter, confirmation≈confirmation; invalidation stays Book/F) is a handoff aid, not a contract mint."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-7. Package proposed (DEC-0380)."
    sources: [EXT-2221]
    authority: rider
    component: COMP-QML
    tags: [qml-research, ad-7, graduation, seed_cite, dont-box-in, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-7"

  - id: DEC-0388
    title: "QML-research AD-8 — Reuse existing owners; QML absorbs the mill process"
    statement: "Reuse-or-new only. Owners: COMP-QML (Stage 1 authoring + QL-7/QL-8; Stage 0 types per AD-15), COMP-QMA-CORE (CT-44), COMP-QMA-DAEMON (KnowledgeService, PlainFileLibrarySource, cite-copy), desk pack research-corpus (seed bind + AD-4 include/exclude), COMP-QMB (Artifact-rail queries), COMP-QMF-REGISTRY (kinds), COMP-QMA-WIRE (federated hit DTO / additive CT-40 family only). No federating COMP, no mill daemon, no identity port on the facade. Replace in-memory StratsCorpus with PlainFileLibrarySource(root_path, source_id=strats). Seed root_path homes on operator-principal plugin/daemon load config (the research-corpus pack), a filesystem path, not an env var, not a git path, not a venue secret, not a qmb setting. v1 persistence owner of hypotheses is the QML authoring composition root (the same root that stamps CT-06/CT-07 for bots per QL-1). Config key research_root is distinct from seed root_path and is not a QMA daemon / research-corpus setting. COMP-QMA-DAEMON MUST NOT write the research root and MUST NOT bind a second CT-44 source_id in v1."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-8. Package proposed (DEC-0380)."
    sources: [EXT-2222]
    authority: rider
    component: COMP-QML
    tags: [qml-research, ad-8, reuse, preflight, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-8"

  - id: DEC-0389
    title: "QML-research AD-9 — Federated discovery concatenates two existing queries"
    statement: "Federated discovery is a concatenate of two existing queries — never a fourth store and never a door run. Workbench AD-8 occupancy is unchanged: this path consumes none. Owner of the federated hit DTO is COMP-QMA-WIRE (additive CT-40 family). Owner of Knowledge search remains CT-44 / COMP-QMA-DAEMON. Owner of Artifact search remains COMP-QMB (library.search / B-15 / ledger merge / Experiment Ledger refs per Workbench AD-3). Frozen hits — exactly one of: KnowledgeHit { hit_class: knowledge, source_ref, snapshot_ref, locator } (durable detail requires a Citation after cite; cite-copy artifact_ref is not an Artifact-rail hit); ArtifactHit { hit_class: artifact, fp1, kind } where kind is in Workbench AD-3 roster or closed query-hit tags saved-view | analysis.published (live tokens; not registry kinds). No other hit_class — including no qml_candidate and no strats. Stage 0 hypotheses are found through the QML research surface, not this DTO. Display aliases on KnowledgeHits MUST NOT say hypothesis or research candidate. Viewing cited seed bytes is a read-only projection and does not mint research_ref. Must not persist a unified row cache, read QMA staging, or treat locators as fp1. Ranked/semantic search stays GAP-0073 (unsupported-capability)."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-9. Package proposed (DEC-0380)."
    sources: [EXT-2223]
    authority: rider
    component: COMP-QMA-WIRE
    tags: [qml-research, ad-9, federated-discovery, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-9"

  - id: DEC-0390
    title: "QML-research AD-10 — Optional librarian is a skill on the same ports"
    statement: "A contextual librarian is a QMA Skill/Graph Template over search/retrieve/cite plus QML Stage 0 helpers. The main agent workspace is a separate view onto the same contracts. No wizard is required to start from a paper, idea, existing package, or ungoverned Python. Closing a UI tab cancels nothing."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-10. Package proposed (DEC-0380)."
    sources: [EXT-2224]
    authority: rider
    component: COMP-QMA-CORE
    tags: [qml-research, ad-10, librarian, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-10"

  - id: DEC-0391
    title: "QML-research AD-11 — Updates are new snapshots; QMX does not merge the dictionary"
    statement: "Edits to the seed happen in Stats (or a future population agent writing Stats files). QMA learns them by snapshot() plus recorded re-pin; snapshots of strats form a linear supersedes chain. Cite copies remain the bytes of the pinned snapshot (StaleSnapshot otherwise). UI/agent browse without a Mission still pins a session snapshot_ref before retrieve/cite; unpinned live-tree reads are refused. Colliding slugs stay keepers. Duplicate/conflict handling is the seed's (file_path, id) rule plus DNA H, not a QMX merge."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-11. Package proposed (DEC-0380)."
    sources: [EXT-2225]
    authority: rider
    component: COMP-QMA-DAEMON
    tags: [qml-research, ad-11, snapshot, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-11"

  - id: DEC-0392
    title: "QML-research AD-12 — JSON Render and MCP Apps present; they do not store or execute"
    statement: "json-render (catalog-constrained generative UI) and MCP Apps (ui:// resources, SEP-1865 stable 2026-01-26) may render DTOs in chat or a tool pane. They are not identity, persistence, or authority. Native web UI is first; desktop later. qma-ui-contract stays GAP-0081. Additive CT-40 query families for the facade are backend work now; chrome is the UI session."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-12. Package proposed (DEC-0380)."
    sources: [EXT-2226]
    authority: rider
    component: COMP-QMA-WIRE
    tags: [qml-research, ad-12, presentation, gap-0081, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-12"

  - id: DEC-0393
    title: "QML-research AD-13 — Workflows sitting consumes citations, hypotheses, and doors, not DNA graphs"
    statement: "Workflows may take Knowledge Citations, QML research_refs, and Artifact fp1s as inputs and may place QMB door steps per Workbench AD-8/AD-9. A Stage 0 graph is not a workflow definition. This sitting does not choose a workflow runtime or editor."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-13. Package proposed (DEC-0380)."
    sources: [EXT-2227]
    authority: rider
    component: COMP-QML
    tags: [qml-research, ad-13, workflows, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-13"

  - id: DEC-0394
    title: "QML-research AD-14 — First vertical slice is seed bind plus a Stage 0 view"
    statement: "The first implementable slice: configure root_path; snapshot per AD-4; search/retrieve/cite against STRAT-000001 and one dictionary entry; Mission pin; QML vocabulary helper resolves swing-high from cited bytes the host passed in; read-only Stage 0 projection of LAYOUT-DEMO preserves entry_hypothesis and unresolved F (no invented exits, no invented short side). The projection does not mint research_ref and is not a wizard. LAYOUT-DEMO is not extracted research to complete. register_library_kind(strats) still refuses; no CT-33 mint; no population ingest. Class/test existence is not e2e (DEC-0286, DEC-0406)."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-14. First epic after docs (DEC-0380). Package proposed (DEC-0380)."
    sources: [EXT-2228, EXT-2245]
    authority: rider
    component: COMP-QML
    tags: [qml-research, ad-14, first-slice, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-14"

  - id: DEC-0395
    title: "QML-research AD-15 — Stage 0 is QML's fourth surface, on QML's own ladder"
    statement: "Stage 0 types live in qml.research, a public submodule of the qml distribution, on QML's own format-version ladder. RESEARCH_FORMAT_VERSION is an independent integer in that module (not QL-7 protocol / QL-8 conformance versions). They are not CT-33 helpers, not QMA/qma-core types, not host-private schemas. Hosts consume the module; they do not fork it. QML still mints no QMF-ladder (CT-*) shared contract. Stage 0 never sizes, never emits CT-23 intents, never becomes a Book/node seat, and is never cited by governed evidence (CT-32 / seats cite Bot fp1 only). Graduation (DEC-0397) is the only mill bridge into CT-33 + Python; gate_registration without a hypothesis remains legal (DEC-0387). The library stays pure per QMF AD-15 (no threads, no I/O, no process spawning). QMA hosts own seed snapshot / search / retrieve / cite. The QML authoring composition root owns hypothesis serialization and listing. A hypothesis may start from an idea, chart, journal, or seed package — Stage 0 is the mill, not a Stats viewer. Proposed parent QL-1: QML's surface is four thin things — (1) CT-33/CT-34 author types, (2) Stage 0 research-candidate types, (3) QL-7 protocol, (4) QL-8 gate. The amendment is a documentation-factory obligation, not an implementation veto. It is not legal to preserve the three-count by hiding Stage 0 in QMA or in host-private DNA files."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-15. QL-1 four-count is a proposed parent amendment (DEC-0403). Package proposed (DEC-0380)."
    sources: [EXT-2229, EXT-2244]
    authority: rider
    component: COMP-QML
    tags: [qml-research, ad-15, qml.research, ql-1, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-15"

  - id: DEC-0396
    title: "QML-research AD-16 — Dictionary is vocabulary over files, not registry kinds"
    statement: "A dictionary entry is a role-neutral file record (12-field markdown in the seed). QML ships parse/validate/lookup helpers over bytes the host passed in (cited copies or caller-supplied buffers) — QML performs no filesystem I/O. Collision resolution uses (file_path, id). Meaning (12 fields, eligible roles, class taxonomy, F/H labels) is computed only by qml.research. The research-corpus adapter returns bytes + locators + AD-4 include/exclude; it MUST NOT emit structured dictionary/DNA fields. QMA cites locators; it does not register slugs as kinds. Binding an entry into a bot still requires a human (or human-approved) choice of CT-16/CT-17 producer or plain Python, then a CT-34 leg role from the closed enum level | trigger | confirmation | filter. Eligible roles on the dictionary (invalidation, target, context, ...) stay on Stage 0. GAP-0085 stays deferred. Dictionary growth happens in the seed tree and appears via new snapshot; QML does not fork a second vocabulary store in v1. Pillars (location, context, trigger, confirmation) are human lenses, not a closed Stage 0 schema."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-16. GAP-0085 stays deferred per operator rider (DEC-0380). Package proposed (DEC-0380)."
    sources: [EXT-2230]
    authority: rider
    component: COMP-QML
    tags: [qml-research, ad-16, dictionary, gap-0085, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-16"

  - id: DEC-0397
    title: "QML-research AD-17 — Graduation is graduate_to_governed, not a QMB spawn"
    statement: "Graduation mints the two artifacts only after both QL-8 layers pass. originating_research_ref is a qmf-core Fingerprint (fp1:sha256:<hex>) so existing graduate_to_governed can consume it. For mill graduation it MUST be the hypothesis research_ref (preimage class = qml-research-hypothesis, DEC-0401). Parent QL-8 ungoverned-experiment graduation keeps its own preimage class; do not call qmf.structure.research.graduate_to_governed. Knowledge Citation digest / artifact_ref / source_ref / seed_cite is not a legal originating_research_ref. Seed cites travel on AD-7 seed_cite only. Host stamps promoted-from CT-07 with to_ref = research_ref. That edge is lineage, not governed evidence: CT-32 and seats cite only the Bot fp1. Self-edge remains refused. Informal collapse: open Stage 0 roles to closed CT-34 enum + Python WHEN; unresolved F to empty permitted_exit_intents and/or Book family policy, never invented exits. Skipping Stage 0 uses gate_registration with no mill CT-07."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-17. Package proposed (DEC-0380)."
    sources: [EXT-2231]
    authority: rider
    component: COMP-QML
    tags: [qml-research, ad-17, graduate_to_governed, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-17"

  - id: DEC-0398
    title: "QML-research AD-18 — Product nouns are QMX / QML; STRATS is seed-disk only"
    statement: "Mill module/surface = research. One DNA-shaped package = hypothesis (also research candidate until graduated). Vocab item = dictionary entry. Stats tree = seed corpus. Lifecycle copy: seed corpus to cite to hypothesis to graduation to declaration + logic. Banned in product language: STRATS as ontology brand, second language, COMP-LIB, Knowledge Base, primitive as a brand, DNA/STRAT-ids as UI nouns (they may appear as imported locator text). Homonym: Stage 0 composition is field/type graph (Boolean / temporal / lifecycle). Never export Confluence / confluence from qml.research. CT-34 Confluence remains the fingerprinted leg-set registry kind."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-18. Aligns with operator-direct DEC-0380. Package proposed (DEC-0380)."
    sources: [EXT-2232]
    authority: rider
    component: COMP-QML
    tags: [qml-research, ad-18, naming, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-18"

  - id: DEC-0399
    title: "QML-research AD-19 — QMA cites; QML owns meaning"
    statement: "QMA's Knowledge port remains read-only transport: snapshot, search, retrieve, cite-copy. QML owns Stage 0 types, vocabulary helpers, and Stage 1 authoring. QMB owns experiments after something runnable exists. The Trading Node owns paper|live after L17. A later CT-44 source_id over a QML-owned research root is a new source, not a rename of strats, and stays deferred in v1 even if host files exist (DEC-0401). QMA does not parse dictionary/DNA meaning (DEC-0396). QMA AD-19 read-only law holds; the empty-corpus sentence is a docs factual refresh only (DEC-0403)."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-19. Package proposed (DEC-0380)."
    sources: [EXT-2233, EXT-2242]
    authority: rider
    component: COMP-QML
    tags: [qml-research, ad-19, meaning-ownership, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-19"

  - id: DEC-0400
    title: "QML-research AD-20 — Independence law and honesty envelope"
    statement: "These are distinct objects: dictionary entry (what exists, role-neutral) is not binding (what job it does in this hypothesis) is not graph (how bound parts interact: Boolean / temporal / lifecycle) is not hypothesis (candidate spec + evidence + unknowns + research lineage) is not declaration (CT-33) is not logic (Python WHEN) is not CT-32 (measured) is not seat (QMN after promote). Stage 0 must preserve F labels and H unknowns. Graduation refuses to invent exits, producers, or CT-29 close-reasons to complete a hypothesis. Class entry_hypothesis / fragment / descriptive_pattern / composite / complete is Stage 0 taxonomy, not a CT-33 field."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-20. Package proposed (DEC-0380)."
    sources: [EXT-2234, EXT-2245]
    authority: rider
    component: COMP-QML
    tags: [qml-research, ad-20, honesty-envelope, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-20"

  - id: DEC-0401
    title: "QML-research AD-21 — Hypothesis identity is QML-local; host persists; not registry fp1"
    statement: "A hypothesis is identified by research_ref = qmf-core fingerprint of exactly { class: qml-research-hypothesis, contract_format_version: RESEARCH_FORMAT_VERSION, body: <canonical Stage 0 content> }. The value is fp1-shaped (fp1:sha256:<hex>) so graduate_to_governed can consume it, and must not be registered as a qmf-registry kind, must not appear on the Artifact rail, and must not reuse a class already used by Bot / experiment / Citation envelopes. Occurrence / writer / created-at / seed snapshot_ref are excluded from the preimage. body is the canonical JSON qml.research returns (sorted keys; locators and meaning; not host markdown). Additive optional fields require a version bump; unknown version is unavailable dependency. A hypothesis exists only after an explicit QML authoring save that returns those bytes; viewing cited seed is not a save (DEC-0394). QML returns fingerprintable content only. The QML authoring composition root is a blob store keyed by research_ref: it persists only those canonical bytes under research_root. It is not daemon sqlite, not QMA AD-22 staging, not a new COMP store, not Stats, and not a second AD-4 include/exclude. Host-private files, if any, are caches of those bytes, never an identity basis. A second KnowledgeSource over this root stays deferred in v1 even though files exist. Restoring across qml format versions is an unavailable dependency refusal."
    status: provisional
    rationale: "Absorbed from architecture-QMX-2026-09-16 AD-21. Package proposed (DEC-0380)."
    sources: [EXT-2235]
    authority: rider
    component: COMP-QML
    tags: [qml-research, ad-21, research_ref, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#ad-21"

  - id: DEC-0402
    title: "QML-research spine adopted as proposed (reuse existing applications; no new COMP; no new CT)"
    statement: "The 2026-09-16 QMX QML research-expansion spine (architecture-QMX-2026-09-16, status draft/proposed) is absorbed into docs/ as DEC-0381 through DEC-0401, under operator-direct paradigm DEC-0380. Preflight verdict is reuse COMP-QML (Stage 0 types + Stage 1 authoring + graduation), COMP-QMA-CORE (CT-44), COMP-QMA-DAEMON (KnowledgeService / PlainFileLibrarySource / cite-copy), research-corpus pack (seed bind + AD-4 include/exclude), COMP-QMB (Artifact-rail queries), COMP-QMF-REGISTRY (kinds), COMP-QMA-WIRE (federated hit DTO / additive CT-40 family). No new component. No new contract id. No new depends_on edge. Parents QMF AD-1..41, QMB B-1..15, QML QL-1..10, NODE TN-1..25, QMA AD-1..29, CONNECT AD-1..5, Workbench AD-1..16 bind read-only. Local AD-1..AD-21 do not renumber those parents. Implementation authorization remains factory-pipeline-only. This umbrella is provisional until the operator accepts the package."
    status: provisional
    rationale: "Operator-directed documentation-factory change-mode absorption of a proposed architecture spine (2026-09-16). Operator rider forbids treating the package as accepted (DEC-0380)."
    sources: [EXT-2213, EXT-2214, EXT-2222]
    authority: rider
    component: COMP-QML
    tags: [qml-research, spine-adoption, preflight, reuse, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md"

  - id: DEC-0403
    title: "Proposed parent amendments — QL-1 four-count, Workbench AD-3 commentary, QMA AD-19 empty-corpus factual refresh"
    statement: "Three proposed parent amendments, not silent overrides. (1) QL-1 surface enumeration: three thin things becomes four — add Stage 0 research-candidate types on QML's own ladder (DEC-0395). Mechanism already legal via QL-7/QL-8 local-ladder path; the count is what needs amendment. (2) Workbench AD-3 commentary only: product discovery may federate Knowledge hits as a distinct class; kind roster unchanged; hypotheses still write no registry kinds (DEC-0381). (3) QMA AD-19 last sentence is a docs factual refresh: seed corpus is no longer empty (239 dictionary entries, LAYOUT-DEMO, schema locks); the read-only adapt-to-library law stands (EXT-2242). None of these silently override parent spine text."
    status: provisional
    rationale: "Spine Inherited Invariants proposed parent amendments. Operator package not accepted (DEC-0380)."
    sources: [EXT-2244, EXT-2242, EXT-2229]
    authority: rider
    component: COMP-QML
    tags: [qml-research, parent-amendments, ql-1, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#inherited-invariants"

  - id: DEC-0404
    title: "QML-research cheap-veto register"
    statement: "Cheap-veto assumptions, each individually overturnable without unwinding another call: (A1) source_id=strats remains the seed adapter freeze key because the research-corpus plugin already uses it; branding does not follow the key (DEC-0383). (A2) AD-4 include/exclude lists are the spine defaults (DEC-0384). (A3) six confidence dimension spellings freeze as listed in DEC-0383; first-slice unscored is corpus-owned default, not current adapter behaviour on integration@8510c03. (A4) QMA AD-19 empty-corpus sentence is docs factual refresh only (DEC-0403). (A5) FR-RES-* numbering is proposed; GAP-0064 records the PRD hole; GAP-0061 is not closed (DEC-0405)."
    status: provisional
    rationale: "Spine Open questions plus memlog assumptions. Package proposed (DEC-0380)."
    sources: [EXT-2238, EXT-2241, EXT-2242]
    authority: rider
    component: COMP-QML
    tags: [qml-research, cheap-veto, assumptions, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#open-questions"

  - id: DEC-0405
    title: "FR-RES addendum recorded as proposed; GAP-0061 not closed"
    statement: "REQUIREMENTS-ADDENDUM.md FR-RES-01 through FR-RES-25 and NFR-RES-01 through NFR-RES-08 are proposed identifiers for documentation-factory and epics. They do not rewrite prd-QMX-2026-08-21. They are a sibling hole to GAP-0061 (workbench FRs). First-distill FR-LIB-* ids are superseded; do not implement both sets. GAP-0064 records this PRD hole. Do not silently close GAP-0061."
    status: provisional
    rationale: "Spine open question on PRD addendum vs GAP-0061 sibling numbering. Operator: do not pretend PRD 2026-08-21 already had mill FRs."
    sources: [EXT-2241]
    authority: rider
    component: COMP-QML
    tags: [qml-research, fr-res, gap-0064, gap-0061, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:REQUIREMENTS-ADDENDUM.md"

  - id: DEC-0406
    title: "Wiring inspect 8510c03 — graduate_to_governed exists; Stage 0 types do not; research-corpus is a stub"
    statement: "On integration@8510c032496bb870824ecc5c4f807e8a4e4f167e: graduate_to_governed exists in qml/src/qml/conformance/registration.py; Stage 0 types (qml.research) do not exist; research-corpus plugin still registers source_id=strats against an in-memory two-file StratsCorpus stub, not the Stats tree; PlainFileLibrarySource exists (filesystem, skips hidden parts, currently hashes all other files including backend/strats.sqlite); qmb registryread library refuses strats and COMP_LIB_MINTED is False; qma-ui-contract is a stub (GAP-0081). Class/test existence is not end-to-end demonstration (DEC-0286 stands). Remaining connect work includes replacing the stub with PlainFileLibrarySource(root_path=Stats), AD-4 include/exclude in the plugin, qml.research types, and host research_root. Implementation authorization still arrives only through the factory pipeline. This inspect SHA is later than the workbench sitting's 1b451a8; do not overwrite that stamp — add this dated note."
    status: provisional
    rationale: "Architecture sitting consistency convention and evidence-summary inspect. Package proposed (DEC-0380)."
    sources: [EXT-2237]
    authority: rider
    component: COMP-QML
    tags: [qml-research, wiring, source-inspected, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:QML-EXPANSION.md"

  - id: DEC-0407
    title: "GAP-0073 layout trigger met upstream; hybrid indexing still deferred"
    statement: "The GAP-0073 layout revisit trigger is met in the seed (239 dictionary entries, LAYOUT-DEMO, schema locks). Hybrid / semantic retrieval remains a separate irreversible index choice and stays deferred. v1 search is literal and locator-based. Ranked or semantic retrieval remains unsupported-capability."
    status: provisional
    rationale: "Spine Deferred table. Do not silently close GAP-0073."
    sources: [EXT-2243]
    authority: rider
    component: COMP-QMA-CORE
    tags: [qml-research, gap-0073, provisional]
    date: 2026-09-16
    spine_ref: "SRC-19:ARCHITECTURE-SPINE.md#deferred"

  - id: DEC-0408
    title: "Dead: STRATS as a QMX language / second ontology"
    statement: "Treating STRATS as QMX's language or as a lasting second ontology behind a two-rail Library facade is dead. The first distill LIBRARY-ADAPTATION.md carried that notion; the operator rejected it. Stats is seed corpus / import. Product language is QML research / hypothesis / dictionary entry / seed corpus. source_id=strats may remain the technical adapter key."
    status: dead
    rationale: "Operator-direct 2026-09-16 (DEC-0380) plus superseded first distill (EXT-2239)."
    sources: [EXT-2239, EXT-2213]
    component: COMP-QML
    tags: [dead, strats-language, first-distill]
    reason: "Operator ruled STRATS is not a QMX language; the mill is absorbed as QML Stage 0, not adapted-to as a second ontology."
    date: 2026-09-16

  - id: DEC-0409
    title: "Dead: auto-mint CT-33/34 from DNA or graph"
    statement: "Automatically assembling CT-33/CT-34 JSON from seed DNA, graph.yaml, or a hypothesis package is dead. Executable artifacts appear only when a human (or human-approved QML authoring) produces the two artifacts."
    status: dead
    rationale: "Operator rider plus spine AD-7. Aligns with Workbench AD-4 (QMA never assembles CT-33 JSON)."
    sources: [EXT-2240, EXT-2221]
    component: COMP-QML
    tags: [dead, auto-mint]
    reason: "Auto-mint from DNA/graph would skip human/QML authorship and collapse research into governed identity."
    date: 2026-09-16

  - id: DEC-0410
    title: "Dead: git subtree or copy of Stats into the QMX repo"
    statement: "Copying or subtree-ing the Stats seed corpus into QMX git is forbidden. QMX points root_path; QMA snapshots. Submodule is deferred until a remote host cannot receive a path."
    status: dead
    rationale: "Spine AD-2 plus QMA AD-19 no-write-back / no QMX fields in the corpus."
    sources: [EXT-2240, EXT-2216]
    component: COMP-QMA-DAEMON
    tags: [dead, subtree, seed-absorb]
    reason: "Absorbing the seed into QMX git would invert adapt-to-library and mix seed files with product source."
    date: 2026-09-16

  - id: DEC-0411
    title: "Dead: Stage 0 graph as executor / run_slice / Graph Template"
    statement: "Compiling a Stage 0 graph (Boolean / temporal / lifecycle operators, seed graph.yaml) into a QMB run_slice, a QMA Graph Template, a task graph, or an order adapter is dead. Graph is meaning on the hypothesis, not a runtime."
    status: dead
    rationale: "Spine AD-6 plus QL-2 (no third governed half) plus QMA AD-16 (no execution tool)."
    sources: [EXT-2240, EXT-2220]
    component: COMP-QML
    tags: [dead, graph-executor]
    reason: "A Stage 0 graph is research meaning; executing it would mint a third governed bot half and a QMA execution tool."
    date: 2026-09-16

  - id: DEC-0412
    title: "Dead: hit_class strats or QmlCandidateHit as a product-Library DTO class"
    statement: "Federated product-Library discovery does not grow hit_class strats or QmlCandidateHit. Frozen hits are KnowledgeHit and ArtifactHit only. Stage 0 hypotheses are found through the QML research surface, not the Library DTO."
    status: dead
    rationale: "Spine AD-1/AD-9 after the restart rejected the first-distill QmlCandidateHit additive."
    sources: [EXT-2240, EXT-2215, EXT-2223]
    component: COMP-QMA-WIRE
    tags: [dead, hit-class, qml-candidate]
    reason: "A third Library hit class would make hypotheses Library objects before CT-33 registration and brand STRATS as identity."
    date: 2026-09-16

  - id: DEC-0413
    title: "Dead: fill GAP-0085 this increment to fit seed DNA roles"
    statement: "Minting typed EntryMechanism / ExitMechanism / Filter / SessionRule / PositionRule / InvalidationRule nouns in this increment to fit seed eligible roles is dead. GAP-0085 stays deferred. Stage 0 already carries open roles and F/H holes. CT-34 enum stays level | trigger | confirmation | filter."
    status: dead
    rationale: "Operator rider: do not fill GAP-0085. Spine AD-16. Workbench DEC-0272 ownership stands; nouns still unruled."
    sources: [EXT-2236, EXT-2230]
    component: COMP-QML
    tags: [dead, gap-0085]
    reason: "Filling GAP-0085 now would mint governed mechanism nouns to fit a seed mill; Stage 0 already carries open roles without that mint."
    date: 2026-09-16
"""

GAPS_NEW = r"""
  - id: GAP-0064
    question: "When are the PRD functional-requirement addenda written for QML Stage 0 / seed corpus / hypothesis FRs (FR-RES-01..FR-RES-25 and NFR-RES-01..08)?"
    needed_by: [COMP-QML, COMP-QMA-CORE, COMP-QMA-DAEMON]
    blocking: false
    recommendation: "Note the hole in this sitting; do not rewrite the PRD here. REQUIREMENTS-ADDENDUM.md holds proposed FR-RES-* identifiers. Sibling to GAP-0061 (workbench FRs); do not close GAP-0061. Epics may be written from the proposed spine and FEAT-0047..FEAT-0050 without waiting, with first epic = AD-14 seed bind + Stage 0 view."
    status: deferred
    answer: null
    note: "QML research expansion Open questions 2026-09-16 (DEC-0405, DEC-0380). PRD 2026-08-21 has QMB/QML FRs and a QMA phase boundary; it has no mill / seed-corpus / hypothesis FRs. First-distill FR-LIB-* ids are superseded. Operator instruction: stamp the package proposed; do not pretend the old PRD specified this expansion."
    date: 2026-09-16
"""

FEATS = r"""
  - id: FEAT-0047
    name: "Seed bind plus Stage 0 view (AD-14 first slice)"
    scope: >-
      In: configure research-corpus root_path to the operator seed tree; snapshot
      per AD-4 include/exclude (DEC-0384); Mission pin of snapshot_ref; literal
      search / retrieve / cite of STRAT-000001 and one dictionary entry
      (swing-high) through CT-44 (DEC-0383, DEC-0385, DEC-0391); replace
      in-memory StratsCorpus stub with PlainFileLibrarySource(root_path,
      source_id=strats) (DEC-0388, DEC-0406); QML vocabulary helper resolves
      swing-high 12 fields from cited bytes the host passed in (DEC-0396);
      read-only Stage 0 projection of LAYOUT-DEMO preserves class
      entry_hypothesis and unresolved F with no invented exits and no invented
      short side (DEC-0394, DEC-0400); register_library_kind(strats) still
      refuses; no CT-33 mint; no population ingest; viewing cited seed does not
      mint research_ref (DEC-0387, DEC-0401). Out: durable research_root blob
      store (FEAT-0048); mill graduation (FEAT-0049); federated Library DTO
      (FEAT-0050); videos/n8n/Hermes; GAP-0085 nouns; GAP-0063 generator; a new
      COMP or CT. Done means implementing stories can cite the slice-0
      acceptance checks; implementation authorization still arrives only
      through the factory pipeline. This feature is proposed (DEC-0380).
    decisions: [DEC-0380, DEC-0382, DEC-0383, DEC-0384, DEC-0385, DEC-0388, DEC-0391, DEC-0394, DEC-0396, DEC-0398, DEC-0400, DEC-0402, DEC-0406]
    components: [COMP-QML, COMP-QMA-DAEMON, COMP-QMA-CORE]
    blocked_by:
      - id: FEAT-0045
        reason: "seed snapshot/search/retrieve/cite rides the KnowledgeSource port, CorpusSnapshot, Citation, and evidence_confidence surface FEAT-0045 lands (DEC-0318, DEC-0383)"
      - id: FEAT-0046
        reason: "the research-corpus desk pack is the plugin that binds PlainFileLibrarySource(root_path) and AD-4 include/exclude; the five desk packs FEAT-0046 lands must exist for that adapter to load (DEC-0384, DEC-0388)"
      - id: FEAT-0030
        reason: "the Stage 0 projection and vocabulary helpers are a QML authoring-surface expansion of the bot-authoring library FEAT-0030 lands; they must not fork a second COMP (DEC-0394, DEC-0396, DEC-0171)"
    size: multi-pass
    status: planned
    notes: "First epic after this documentation-factory pass (DEC-0380, DEC-0394). Package proposed not accepted — absorbed AD rulings are provisional (DEC-0402). Implementation authorization factory-pipeline-only."

  - id: FEAT-0048
    name: "qml.research types, research_ref identity, and host blob store"
    scope: >-
      In: public qml.research submodule on QML's own RESEARCH_FORMAT_VERSION
      ladder (DEC-0395); Stage 0 types for dictionary cites, bindings, graph,
      evidence, unknowns, F/H labels, class taxonomy (DEC-0386, DEC-0400);
      research_ref = fp1-shaped fingerprint of class qml-research-hypothesis
      (DEC-0401); QML authoring composition root blob store keyed by
      research_ref under research_root, distinct from seed root_path and from
      daemon sqlite (DEC-0388, DEC-0401); explicit save returns canonical bytes;
      viewing cited seed still does not mint identity (DEC-0394). Out: a new
      COMP or CT; registering hypotheses as qmf-registry kinds; a second CT-44
      source_id over the research root in v1; QMA writing the research root;
      filling GAP-0085. Done means hosts consume qml.research and persist
      canonical bytes; implementation authorization still arrives only through
      the factory pipeline. This feature is proposed (DEC-0380).
    decisions: [DEC-0386, DEC-0388, DEC-0395, DEC-0400, DEC-0401, DEC-0402]
    components: [COMP-QML]
    blocked_by:
      - id: FEAT-0047
        reason: "durable hypothesis identity and the research_root blob store trail the seed-bind plus read-only Stage 0 view FEAT-0047 lands; AD-14 forbids minting research_ref from the LAYOUT-DEMO projection (DEC-0394, DEC-0401)"
      - id: FEAT-0030
        reason: "qml.research is a fourth surface of the existing qml distribution FEAT-0030 lands, on QML's own ladder, never a new COMP (DEC-0395, DEC-0171)"
    size: multi-pass
    status: planned
    notes: "Trails FEAT-0047. Proposed QL-1 four-count is a docs amendment (DEC-0403), not an implementation veto. Implementation authorization factory-pipeline-only."

  - id: FEAT-0049
    name: "Mill graduation via graduate_to_governed plus optional seed_cite"
    scope: >-
      In: mill path through existing graduate_to_governed after both QL-8
      layers (DEC-0397); originating_research_ref for mill graduation is the
      hypothesis research_ref only; Knowledge Citation digest / artifact_ref /
      source_ref / seed_cite is illegal as originating_research_ref (DEC-0397);
      host-stamped CT-07 promoted-from edge with to_ref = research_ref, lineage
      not governed evidence (DEC-0387, DEC-0397); optional seed_cite triple on
      the candidate, host is the single writer, origin stays the frozen string
      qma, seed_cite not inside CT-33 identity (DEC-0387); collapse of open
      Stage 0 roles into closed CT-34 enum plus Python WHEN; unresolved F to
      empty permitted_exit_intents and/or Book family policy, never invented
      exits (DEC-0400); gate_registration without Stage 0 remains legal;
      ungoverned Python remains legal (DEC-0387). Out: auto-mint from DNA
      (DEC-0409); treating spawn_governed as graduation; a third governed bot
      half; CT-07 to a Knowledge Citation. Done means mill graduation and
      skip-Stage-0 registration are both specified; implementation
      authorization still arrives only through the factory pipeline. This
      feature is proposed (DEC-0380).
    decisions: [DEC-0387, DEC-0397, DEC-0398, DEC-0400, DEC-0402]
    components: [COMP-QML, COMP-QMF-REGISTRY]
    blocked_by:
      - id: FEAT-0048
        reason: "mill originating_research_ref is the hypothesis research_ref FEAT-0048 lands; Citation digest is illegal here (DEC-0397, DEC-0401)"
      - id: FEAT-0030
        reason: "graduation reuses QL-8 graduate_to_governed, CT-33/CT-34 authoring, and the host CT-06/CT-07 mint FEAT-0030 already lands (DEC-0397, DEC-0178)"
    size: multi-pass
    status: planned
    notes: "Trails FEAT-0048. L33 graduation remains two-artifact registration, not an orchestrator spawn (DEC-0270). Implementation authorization factory-pipeline-only."

  - id: FEAT-0050
    name: "Federated Knowledge plus Artifact discovery DTO"
    scope: >-
      In: concatenate existing CT-44 Knowledge search and QMB library.search
      Artifact queries into a frozen federated hit DTO owned by COMP-QMA-WIRE
      (additive CT-40 family) (DEC-0389); KnowledgeHit {hit_class knowledge,
      source_ref, snapshot_ref, locator} and ArtifactHit {hit_class artifact,
      fp1, kind} only; no qml_candidate and no strats hit_class (DEC-0381,
      DEC-0412); hypotheses stay on the QML research surface; no fourth store;
      no occupancy on this path (DEC-0389). Out: a copied-row Library index;
      QMB opening daemon sqlite; persisting a unified row cache; treating
      locators as fp1; ranked/semantic search (GAP-0073). Done means UI/agent
      search can cite the DTO without minting a new COMP; implementation
      authorization still arrives only through the factory pipeline. This
      feature is proposed (DEC-0380).
    decisions: [DEC-0381, DEC-0389, DEC-0392, DEC-0402]
    components: [COMP-QMA-WIRE, COMP-QMB, COMP-QMA-DAEMON]
    blocked_by:
      - id: FEAT-0034
        reason: "Artifact-rail hits are the Workbench AD-3 fp1 projection and candidate-set queries FEAT-0034 lands; federation concatenates that query, it does not fork it (DEC-0389, DEC-0271)"
      - id: FEAT-0045
        reason: "Knowledge-rail hits are CT-44 search/retrieve/cite FEAT-0045 lands; federation concatenates that query (DEC-0389, DEC-0318)"
      - id: FEAT-0041
        reason: "the federated hit DTO is an additive CT-40 family owned by COMP-QMA-WIRE; the wire contract FEAT-0041 lands is the envelope those queries ride (DEC-0389, DEC-0304)"
    size: multi-pass
    status: planned
    notes: "May trail FEAT-0047; not required for slice 0. Implementation authorization factory-pipeline-only."
"""


def patch_gap_0073(path: Path) -> None:
    old = """  - id: GAP-0073
    question: "What hybrid retrieval / indexing does the Knowledge corpus need beyond literal and locator-based search?"
    needed_by: [COMP-QMA-CORE, COMP-QMA-DAEMON]
    blocking: false
    recommendation: "the corpus root holds at least one ingestible content file and STRATS §6 Q1-Q12 (folder layout, serialization, stable-id scheme) are ratified upstream"
    status: deferred
    answer: null
    note: "AD-19 KnowledgeSource port. v1 ships the adapter over the STRATS plain-file library with CorpusSnapshot / Citation / Provenance and literal + locator search only; evidence_confidence on knowledge is never conflated with admission_confidence on memory (DEC-0343)."
    date: 2026-08-29"""
    new = """  - id: GAP-0073
    question: "What hybrid retrieval / indexing does the Knowledge corpus need beyond literal and locator-based search?"
    needed_by: [COMP-QMA-CORE, COMP-QMA-DAEMON]
    blocking: false
    recommendation: "Layout trigger is met in the seed (239 dictionary entries, LAYOUT-DEMO, schema locks). Hybrid retrieval is a separate irreversible index choice and stays deferred. v1 remains literal + locator only (DEC-0407)."
    status: deferred
    answer: null
    note: "AD-19 KnowledgeSource port. v1 ships the adapter over the seed corpus (source_id=strats, product language is seed corpus not STRATS brand) with CorpusSnapshot / Citation / Provenance and literal + locator search only; evidence_confidence on knowledge is never conflated with admission_confidence on memory (DEC-0343). 2026-09-16 QML research expansion (DEC-0407): layout revisit trigger is met upstream; do not silently close this row; ranked/semantic search remains unsupported-capability."
    date: 2026-09-16"""
    replace_once(path, old, new, "GAP-0073 2026-09-16")


def patch_gap_0085(path: Path) -> None:
    old = """    note: "Ownership ruled 2026-09-14 by workbench AD-4 (DEC-0272): search varies declared CT-33 parameters in QMB; generation, if built, authors new CT-33/CT-34 and/or logic-source bytes via QML; QMA StrategyHandle may only reference already-fingerprinted records and register dev-zone candidates. Typed Entry/Exit/Filter/Session vocabulary remains unruled. QMA AD-14 parent still holds. Integration source (qma/core/ports/experiments.py) refuses the mechanism keys. Do not silently fill nouns in prose."
    date: 2026-09-14"""
    new = """    note: "Ownership ruled 2026-09-14 by workbench AD-4 (DEC-0272): search varies declared CT-33 parameters in QMB; generation, if built, authors new CT-33/CT-34 and/or logic-source bytes via QML; QMA StrategyHandle may only reference already-fingerprinted records and register dev-zone candidates. Typed Entry/Exit/Filter/Session vocabulary remains unruled. QMA AD-14 parent still holds. Integration source (qma/core/ports/experiments.py) refuses the mechanism keys. Do not silently fill nouns in prose. 2026-09-16 QML research expansion (DEC-0396, DEC-0413): Stage 0 already carries open eligible roles and F/H holes; filling GAP-0085 this increment to fit seed DNA roles is dead; CT-34 enum stays level | trigger | confirmation | filter."
    date: 2026-09-16"""
    replace_once(path, old, new, "GAP-0085 2026-09-16")


def patch_gap_0061(path: Path) -> None:
    old = """    note: "Workbench Open questions 2026-09-14 (DEC-0287). PRD today covers QMB FRs (FR-036..046) and QML FRs; it does not yet state ExperimentSpec, analysis methods, generation-vs-search, or procedures. Operator instruction: note the hole; do not rewrite the PRD in this sitting."
    date: 2026-09-14"""
    new = """    note: "Workbench Open questions 2026-09-14 (DEC-0287). PRD today covers QMB FRs (FR-036..046) and QML FRs; it does not yet state ExperimentSpec, analysis methods, generation-vs-search, or procedures. Operator instruction: note the hole; do not rewrite the PRD in this sitting. 2026-09-16: mill/seed/hypothesis FRs are a sibling hole GAP-0064 (FR-RES-*); do not close this row to absorb them (DEC-0405)."
    date: 2026-09-16"""
    replace_once(path, old, new, "GAP-0061 2026-09-16")


def main() -> None:
    append_if_missing(ROOT / "_docwork/manifest.yaml", "id: SRC-19", MANIFEST)
    append_if_missing(ROOT / "_docwork/extractions.yaml", "id: EXT-2213", EXTR)
    append_if_missing(ROOT / "_docwork/ledger.yaml", "id: DEC-0380", LEDGER)
    patch_gap_0073(ROOT / "_docwork/gaps.yaml")
    patch_gap_0085(ROOT / "_docwork/gaps.yaml")
    patch_gap_0061(ROOT / "_docwork/gaps.yaml")
    append_if_missing(ROOT / "_docwork/gaps.yaml", "id: GAP-0064", GAPS_NEW)
    append_if_missing(ROOT / "_docwork/feature_inventory.yaml", "id: FEAT-0047", FEATS)
    print("done")


if __name__ == "__main__":
    main()
