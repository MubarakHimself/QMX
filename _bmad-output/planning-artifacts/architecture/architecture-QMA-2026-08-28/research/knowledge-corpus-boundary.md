# Reference: knowledge-corpus-boundary (STRATS library → QMX Knowledge contract)

**Study (primary source):** `C:/Users/Mubarak/Desktop/Stats/STRATS-GROUND-STATE.md` (596 lines, produced 2026-08-26 by glm-5.2 audit session; authoritative-until-superseded), read in full 2026-08-28. Section refs below = `§` into that file. No web fetched: the only URL inside is the QMX GitBook, which the file itself forbids inspecting (§8). Root dir holds only `IDEA.md` + this ground-state + `.hermes/` (another agent's live workspace, not read).
**Constitution filter:** `.../packet/QMX_AGENTIC_ARCHITECTURE_PACKET_v0.1/01_QMX_CONSTITUTION.md`. **Transcript register:** `.../inputs/transcript-decision-register.md` (rows R40/R46/R47/R48, §5 Delphi row, §6 L2314–2326).

---

## Q1 — Target mental model

Knowledge is an **external, versioned, provenance-carrying evidence corpus that agents interrogate** (Delphi-shaped: an agent context engine over papers/repos/datasets with reproducible source snapshots and provenance-aware retrieval) — **not** one giant summarized document, **not** memory, **not** mutated in place (register R47; §5 Delphi row; Constitution §6/§8). The STRATS library is the archetypal such corpus and the concrete forcing function for the contract: a **portable plain-file / Obsidian trading-strategy knowledge library** that is "a folder structure, not software, not a database, not a runtime" and must stay readable "without Hermes, QMX, n8n, Gemini, NotebookLM, Firecrawl or any other tool" (`STRATS-GROUND-STATE.md §1`, checked 2026-08-28). The binding law is directional: **"QMX will adapt to the library — the library is NOT built around QMX"** (`§1`, checked 2026-08-28). So QMX Knowledge is a *read-only consumer that conforms to an external corpus it does not own*, the inverse of a KB the platform authors for itself.

## Q2 — Concrete structures that implement it

**A. STRATS ontology shape** (the corpus internal model QMX must index but never redefine). Semantic core is a one-way pipeline: `heterogeneous sources → source-faithful evidence + atomic claims → role-neutral primitive dictionary → strategy-specific role bindings → Boolean/temporal/stateful logic graph → human+agent-readable strategy package → lineage/catalog/mini-KBs → downstream QMX consumption` (`§4.1`, checked 2026-08-28). Three deliberately separate layers (`§4.2`, checked 2026-08-28):
- **Primitive dictionary** — reusable, *role-neutral* concepts (bullish-engulfing, liquidity sweep, RSI, order block). A primitive is NOT permanently a "trigger" or "confirmation."
- **Contextual role binding** — the job one primitive does in ONE strategy (role, params/profile, pair, timeframe, session, direction, timing, dependencies, evidence, ambiguity).
- **Strategy logic graph** — how bound components combine: Boolean `AND/OR/NOT/K_OF_N`, temporal `SEQUENCE/WITHIN/UNTIL`, stateful + execution edges; unbounded cardinality.

**B. Dictionary entry** — ~25 fields discussed, exact serialization NOT ratified (`§4.4`, checked 2026-08-28); the 239 built candidates use **12 required fields** (family, aliases, definition, boundaries, observable inputs, recognition semantics, parameters/profiles, eligible roles, market/data constraints, transfer notes, evidence/status, uncertainty/variants), 229 unique IDs, 9 cross-file dup IDs intentionally unresolved (`§3`, checked 2026-08-28). Relation vocabulary between entries: `alias-of, equivalent-to, broader/narrower-than, specialization/profile-of, derived-from, constructed-from, depends-on, compatible-with, incompatible-with, often-composed-with, contradicts, replaces/supersedes` (`§4.4`, checked 2026-08-28).

**C. Strategy package** — 14 sections (identity, source+evidence map, scope/context, primitive refs, role bindings, setup/eligibility, trigger/confirmation/entry, invalidation/stop/target/exit, operational logic graph, parameters+defaults, dependencies/assumptions, unknowns/conflicts, lineage/composition, research status) (`§4.5`, checked 2026-08-28). Missing exits are **labelled, never invented** (`source_defined | external_policy | deliberately_open | unresolved`).

**D. Evidence layers (never flatten)** — 9 layers: raw source/immutable locator → source manifest → normalized transcript → frames/OCR/cursor context → transcript↔visual temporal alignment → atomic claims w/ exact locators → model/analyst interpretation → dictionary mappings/bindings/graph → later empirical findings kept separately linked (`§4.6`, checked 2026-08-28).

**E. Provenance labels + confidence** — every operational statement carries an **evidence label** from `{source-stated/explicit, visually-demonstrated, repeated-example-inference, analyst/model-inference, STRATS-standardized, unresolved}`; "Model output is interpretation, NOT ground truth." A **single aggregate confidence score is REJECTED**; instead 6 orthogonal dimensions: extraction confidence, rule explicitness, source quality/completeness, ambiguity/unresolved status, empirical status, portability/market-transfer status. "High extraction confidence ≠ edge" (`§4.6`, checked 2026-08-28).

**F. Lineage + catalog** — lineage is a **DAG, not a linear tree**; source-faithful baselines are never silently overwritten; composites name multiple parents; **no single "magical best" variant** (empirical selection is downstream). Catalog aspiration ~7,000 strategies with stable IDs + global index + tags + pair/timeframe/session indexes (`§4.8`, checked 2026-08-28).

**G. Formats/naming** — Markdown-primary, Obsidian-portable (wikilinks/backlinks/indexes readable *outside* Obsidian is an open goal, `§6` Q12). Stable canonical IDs per entry. Draft layouts used `manifest.yaml/graph.yaml/lineage.yaml` but exact **names and extensions "remain open"** (`§4.5`, checked 2026-08-28). Dictionary candidates are `.md` (e.g. `locations-and-structure.md`) currently stranded in `.hermes/orchestration/dictionary-wave-1/candidates/`, NOT yet in the library root (`§3`, checked 2026-08-28).

**H. QMX-owned Knowledge contract (proposed — QMX owns this, STRATS untouched behind it):**
- `KnowledgeSource{ kind, source_id, adapter }` where `kind ∈ {plain_file_library, paper, video_transcript, web_research, broker_doc, code_repo, book, market_microstructure_lit, qmx_report}` (register §6 L2314–2326 corpus-for-scalping list, checked 2026-08-28).
- `PlainFileLibrarySource{ root_path, read_only=true, impose_schema=false }.snapshot() -> CorpusSnapshot` — points at the STRATS folder, imposes no schema, reads Markdown/frontmatter/wikilinks as-is, never writes back.
- `CorpusSnapshot{ snapshot_id, root_path, created_at, file_digests[] }` — `snapshot_id` = **content-addressed tree digest** (Merkle over file contents, git-tree style), immutable; every query and every citation pins one (Constitution §11 reproducibility; register §6 experiment freeze-list "data snapshot/reference," checked 2026-08-28).
- `Provenance{ source_id, source_kind, snapshot_id, locator, evidence_label(6 vals), confidence[6 dims], transfer_caveat, retrieved_at }` — `locator` is kind-specific (file+char-range | video timestamp+frame_id | paper page/section). Evidence label + 6 confidence dims copied verbatim from §4.6, stored as **opaque metadata QMX does not reinterpret**.
- Query surface (agent-facing, RLM-friendly): `search(query, filters, snapshot_id?) -> KnowledgeHit[]`; `retrieve(ref | doc_id, snapshot_id) -> KnowledgeChunk`; `cite(hit) -> Citation{ source_id, locator, snapshot_id }`. Returns handles/locators so RLM operates over the corpus programmatically instead of dumping it into context (register R48, checked 2026-08-28).
- `Citation` is embeddable into a Ledger entry / Artifact / Finding as a `knowledge_ref` (reference, not shared semantics — mirrors register R37 `trace_ref` pattern).

## Q3 — Failure modes it solved

1. **Context compaction destroying settled decisions** — the entire ground-state doc exists because compaction repeatedly ate the design and agents regressed into rejected overengineering (`§2`, checked 2026-08-28). Directly validates Constitution §6/§7 (state outlives context; context is compiled not accumulated) and the durable-external-corpus premise.
2. **Silent merges of disagreeing sources** — preserved as profiles/variants, not merged (`§4.4`).
3. **One-number confidence hiding that clarity ≠ edge** — 6 orthogonal confidence dims (`§4.6`).
4. **Model interpretation masquerading as truth** — mandatory evidence labels; model output flagged as interpretation (`§4.6`).
5. **Cross-market contamination** — CEX volume/DOM/futures sessions/funding/order-book "must NEVER be silently treated as spot-Forex/spot-crypto facts"; transfer caveats + venue provenance mandatory (`§1`, `§4.2`, checked 2026-08-28).
6. **Tool lock-in destroying portability** — plain-file, tool-independent; tools may build it but the artifact never depends on them (`§1`).
7. **Overengineering "just a folder" into a software release system** — tests/validators/promotion gates/curators explicitly rejected as poison (`§9`, `§10`, checked 2026-08-28).
8. **Losing lineage on promotion** — DAG, no silent overwrite, no single best variant (`§4.8`).

## Q4 — What QMX should reuse conceptually

- The **whole "external evidence corpus the agent interrogates"** model as the definition of Knowledge (aligns register R47).
- **The 6 evidence labels + 6 confidence dimensions** as QMX's Knowledge `Provenance` schema — carry them through, never collapse (`§4.6`).
- **Never-flattened evidence layers** as a provenance principle (raw → normalized → claim → interpretation → empirical stay distinguishable) (`§4.6`).
- **Content-addressed snapshot identity for a folder tree** as the reproducibility/citation primitive (Constitution §11).
- **Read-only, tool-independent consumption**; QMX adapts its query surface to the library's shape, not vice versa (`§1`).
- **Mandatory transfer caveats / venue provenance** on any borrowed cross-market fact (`§1`).
- **DAG lineage, no single "best"** — QMX must let multiple valid variants coexist and keep parent links when re-ingesting (`§4.8`).
- **Knowledge ≠ Memory reinforced from the source side**: mini-KBs are "NOT QMX agent memory, NOT current market state, NOT daily runtime intelligence" (`§4.7`, checked 2026-08-28) — the corpus itself refuses to be memory.

## Q5 — What QMX should reject

- **Writing back into the library** or adding any QMX-facing field/folder — `§8` bars QMX adapters, executable test manifests, run results, experiment ledgers, executors, genetic machinery, package locks, account/position/agent state, certification state (`§8`, checked 2026-08-28). QMX Knowledge is strictly read-only over STRATS.
- **Hardcoding STRATS's layout or serialization** — folder layout is *unresolved* (`§6` 12 open questions) and field serialization/extensions are explicitly open (`§4.5`). Any adapter that assumes `dictionary/` vs `primitives/`, or `.yaml` vs `.md`, will break.
- **Collapsing evidence layers or the 6 confidence dims** into one score — the source rejects it.
- **Treating model/analyst interpretation as ground truth, or source performance claims as verified edge** — STRATS keeps perf claims as *cited claims only* (`§8`).
- **Expecting the 239 dictionary entries to be final/promoted** — they are unpromoted candidates, frozen until layout approval (`§3`, `§7`).
- **[INHERITED FASHION]** Importing generic/multi-tenant KB machinery into QMX Knowledge — per-tenant ACLs, corpus sharing/publishing, a marketplace of corpora, certification/promotion state on the corpus. QMX is single-operator (Constitution §1); STRATS is single-operator and *already* purged this ("no promotion gates, no curator bureaucracies," `§10`). None of it is load-bearing.
- **[INHERITED FASHION]** A single **summarized/indexed "one giant document" KB** — register R47 explicitly rejects it; that is a general-public RAG convenience, not what an evidence corpus interrogated for provenance needs.

## Q6 — Contract QMX should own instead

QMX owns the **`KnowledgeSource` contract + `CorpusSnapshot` + `Provenance` + query surface** (Q2·H); STRATS stays byte-identical behind a `PlainFileLibrarySource` adapter. Governing invariants:
1. **Adapt, don't impose.** The adapter conforms to the corpus's (open, drifting) shape; it extracts stable IDs where entries provide them and falls back to `path#heading` anchors otherwise, and it tolerates schema/layout drift snapshot-to-snapshot.
2. **Content-addressed, immutable snapshots.** Every retrieval and citation pins a `snapshot_id`; a changed vault yields a new snapshot, never an in-place edit of an old one (Constitution §11).
3. **Provenance is first-class and opaque.** The 6 evidence labels + 6 confidence dims + transfer caveat ride with every `KnowledgeChunk`; QMX stores and surfaces them, never overwrites or averages them.
4. **Knowledge ≠ Memory (separation rule).** Knowledge is external, versioned, read-mostly evidence *not derived from the agent's experience*; Memory is "selective durable adaptive state derived from experience" (register R44). Flow is **Knowledge → Context** (retrieved per invocation) and **Knowledge → cited in Memory/Ledger/Artifact** — but agent experience **never silently becomes Knowledge**. When an agent's own output must enter the corpus, it re-enters *only* as a distinct `KnowledgeSource{kind: qmx_report}` with its own provenance + snapshot — an ingestion, not a mutation (Constitution §8; register R40 `MEMORY ≠ LEDGER ≠ KNOWLEDGE ≠ ARTIFACTS ≠ CONTEXT`; STRATS `§4.7` mini-KB boundaries).
5. **Trading-bots vs research-workers boundary carries over** (`§4.9`, checked 2026-08-28): STRATS stores candidate strategy *definitions*, never running bots; QMX's trading agents *consume* those candidate specs and implement/test/deploy downstream — Knowledge is the source of candidate logic, not an executor.

---

## Forbidden assumptions QMX must NOT make (explicit from the study)

- Do NOT assume the library is a DB/runtime/software — "it's just a folder" (`§10`, checked 2026-08-28).
- Do NOT require the library to depend on QMX/Hermes/n8n/etc. — portability is non-negotiable (`§1`).
- Do NOT expect a ratified schema, serialization, or finalized layout — both are open (`§4.5`, `§6`).
- Do NOT flatten evidence layers or collapse confidence to one score (`§4.6`).
- Do NOT treat interpretation as truth or source perf claims as edge (`§4.6`, `§8`).
- Do NOT silently treat futures/CEX/DOM/order-book data as spot facts (`§1`).
- Do NOT write into the library or add QMX fields/folders (`§8`).
- Do NOT expect running bots or executable manifests — candidate definitions only (`§4.9`, `§8`).
- Do NOT inspect the QMX GitBook from the STRATS side (`§8`).

## Open questions this reference cannot settle

- STRATS layout + serialization are unratified (`dictionary/` vs `primitives/`; `.yaml` vs `.md`; catalog/lineage as folders vs Markdown indexes) — the stable-anchor scheme QMX's adapter should key on is undecided (`§6` Q1–Q12).
- Whether a Knowledge base is even needed vs RLM was never operator-ratified (register open-Q #10) — QMX may possess-not-embed the corpus, but "need it at all" stays open.
- Snapshot granularity for a live, moving Obsidian vault (whole-tree digest vs per-file; how to cite an evolving vault) is unspecified.
- Stable-ID fallback (`path#heading`) is fragile across edits; the source has 9 unresolved duplicate IDs (`§3`).
- **STRATS root is still empty** (only `IDEA.md` + ground-state); no library content exists yet to ingest — the contract is designed against a spec, not a populated corpus (`§3`, checked 2026-08-28).
- How QMX-generated reports re-enter as `qmx_report` Knowledge without contaminating provenance or crossing into Memory.
