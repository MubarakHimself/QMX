# QML research expansion — documentation-factory Stage 9 brief (2026-09-16)

Route e, change mode, Stage 9. Do not restart Stages 1–8. Do not implement code, UI, videos, n8n, or Hermes. Do not fill GAP-0085 or GAP-0063. Do not launch epics.

Planning checkout: `main` (dirty docs preserved). Implementation inspect SHA if cited: `integration@8510c032496bb870824ecc5c4f807e8a4e4f167e`. Do not switch branches.

## Authority

1. **Operator rider (ratified this session):** `_docwork/riders/qml-research-expansion-2026-09-16.md` plus the operator prompt. STRATS is not a QMX language. Stats is a seed mill absorbed as QML Stage 0. QMF = framework; QML/QMB/QMA = libraries; QMN = node. No new COMP. No new CT. `source_id=strats` is adapter key, not product copy. Package is **proposed, not accepted**.
2. **Architecture package (proposed):** `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/ARCHITECTURE-SPINE.md` (local AD-1..AD-21). Companions: `QML-EXPANSION.md` (current), `REQUIREMENTS-ADDENDUM.md` (FR-RES-* proposed). `LIBRARY-ADAPTATION.md` is **superseded** — do not fold as current.
3. **Parents bind read-only:** QML QL-1..QL-10, Workbench AD-1..AD-16, QMA AD-19, constitution L7/L10/L17/L30–L33/L39. Proposed parent amendments are documentation-factory obligations tagged **[PROPOSED]**, never silent overrides.

Local `AD-1`..`AD-21` do **not** renumber QMF/QMB/QML/NODE/QMA/CONNECT/Workbench parents. Cite parents as `QMF AD-n` / `QMA AD-n` / `Workbench AD-n` / `QL-n` / `B-n` / `TN-n`.

## ID block

| Kind | Range | Use |
|---|---|---|
| SRC | SRC-19, SRC-20 | architecture folder; this rider |
| EXT | EXT-2213..EXT-2245 | extractions |
| DEC | DEC-0380 ratified operator paradigm; DEC-0381..DEC-0401 = AD-1..AD-21 **provisional**; DEC-0402..DEC-0407 package umbrellas **provisional**; DEC-0408..DEC-0413 **dead** |
| GAP | GAP-0064 new (FR-RES PRD hole, sibling to GAP-0061); GAP-0073/0085/0061/0063 updated in place |
| FEAT | FEAT-0047..FEAT-0050 |
| ADR | ADR-0023 | this increment (`status: provisional`) |
| SCN | SCN-0017 | Stage 0 honesty envelope (`status: provisional`) |
| CT | no new id | annotations only |
| COMP | none | **no sixth application** |

## Standing of claims

- Existing ratified docs keep `status: ratified`. New sections on them are tagged **[PROPOSED]** and cite provisional DECs.
- New ADR-0023 and SCN-0017 are `status: provisional`. `lint_docs --strict` is expected to fail on those two; that is the operator's proposed stamp, not a gate to weaken.
- Every new normative sentence cites a DEC. Do not treat AD-1..AD-21 as accepted law.
- `verified: 2026-09-16` on every doc you touch.

## Preflight verdict (record in ADR-0023)

**reuse** existing applications. **new COMP: none. new CT: none.**

| Work | Owner |
|---|---|
| Stage 0 types + vocab helpers (`qml.research`) | COMP-QML |
| Hypothesis blob store (host composition root, `research_root`) | COMP-QML host (same root that stamps CT-06/CT-07) |
| Seed snapshot/search/retrieve/cite | COMP-QMA-CORE (CT-44) + COMP-QMA-DAEMON + research-corpus pack |
| Federated hit DTO | COMP-QMA-WIRE (additive CT-40 family) |
| Artifact-rail queries | COMP-QMB |
| Registry kinds | COMP-QMF-REGISTRY |
| Graduation | existing `graduate_to_governed` in COMP-QML |

Candidates refused: COMP-LIB / Knowledge Base / sixth COMP (Workbench AD-1, DEC-0084); `strats` Library kind (Workbench AD-3); new CT-* for hypotheses (QL-1 no-CT-* rule); QMA authoring hypotheses (Workbench AD-4); QMB owning the mill (QMB is experimentation after something runnable exists); compiling Stage 0 `graph` into `run_slice`.

No existing component's authority shrinks. No new `depends_on` edge. No new contract id.

## Feature slices (implementation still factory-pipeline-only)

| FEAT | Name | Primary DECs | Blocked by |
|---|---|---|---|
| FEAT-0047 | Seed bind + Stage 0 view (AD-14 first slice) | DEC-0380, 0382, 0383, 0384, 0385, 0394, 0396, 0398 | FEAT-0045, FEAT-0046, FEAT-0030 |
| FEAT-0048 | `qml.research` types + `research_ref` identity + host blob store | DEC-0395, 0400, 0401, 0386 | FEAT-0047, FEAT-0030 |
| FEAT-0049 | Mill graduation + `seed_cite` | DEC-0387, 0397 | FEAT-0048, FEAT-0030 |
| FEAT-0050 | Federated Knowledge+Artifact discovery DTO | DEC-0381, 0389 | FEAT-0034, FEAT-0045, FEAT-0041 |

First epic = FEAT-0047. Do not launch it from this sitting.

## Drafting rules

- Cite new DECs on every new normative sentence. Self-contained sections. No "as discussed above". No hedges. No TODO without a GAP id.
- Product nouns: **research** / **hypothesis** / **dictionary entry** / **seed corpus**. Banned as product language: STRATS, second language, COMP-LIB, Knowledge Base, primitive-as-brand, revived `.qml`.
- Stage 0 composition field is **`graph`**, never `Confluence`. CT-34 Confluence remains the fingerprinted leg-set.
- `source_id=strats` is a technical adapter key. UI/glossary/agent prompts do not brand the product STRATS.
- Hypotheses are not Library objects and not registry kinds until CT-33 registration.
- Three legal entries, none a toll booth: ungoverned Python; `gate_registration` without Stage 0; Stage 0 then `graduate_to_governed`.
- `originating_research_ref` for mill graduation = hypothesis `research_ref` only. Citation digest is illegal there. Live handle `origin` stays `"qma"`. Optional `seed_cite` is a distinct non-fp1 field.
- Viewing cited seed / LAYOUT-DEMO does **not** mint `research_ref`.
- Preserve F labels and H unknowns. Refuse invented exits. Class `entry_hypothesis` is Stage 0 taxonomy, not a CT-33 field.
- GAP-0085 stays deferred. GAP-0063 stays deferred. GAP-0061 is not closed. FR-RES-* live on GAP-0064.
- GAP-0073: layout trigger met upstream; hybrid indexing still deferred.
- `source-inspected` ≠ e2e (DEC-0286, DEC-0406). `graduate_to_governed` exists on integration; Stage 0 types do not; research-corpus still points at an in-memory two-file stub.
- Inspect SHA for this sitting: `integration@8510c03` (full `8510c032496bb870824ecc5c4f807e8a4e4f167e`). Do not overwrite workbench's `1b451a8` stamps; add a dated note.
- Dated follow-ups on ADR-0018/0020/0022; do not rewrite those ADRs' original Decision sections.
- QML stays pure (no I/O). Hosts persist.

## Docs to touch

New: `docs/decisions/ADR-0023-qml-research-expansion.md`; `docs/scenarios/SCN-0017-stage0-honesty-envelope.md`.

Update: qml.md (QL-1 **[PROPOSED]** four-count; Stage 0 section; structural seed `qml/research/`); qma-core.md (AD-19 empty-corpus factual refresh; seed adapter); qma-daemon.md (research-corpus include/exclude; must not write research_root); qma-wire.md (federated hit DTO); qmb.md (Workbench AD-3 commentary — hypotheses not Library; `strats` still refused); qmf-registry.md (no hypothesis kind); constitution L11/L33 annotations; AGENTS.md; glossary; gap-report; traceability; index; changelog; overview; stack; dependencies.yaml COMP-QML notes; CT-33/CT-34/CT-44/CT-07/CT-40/CT-32/CT-06 annotations; ADR-0018/0020/0022 follow-ups; SCN-0015 note if needed.

Lenses: only if they still say QML surface is exactly three things, or treat STRATS as a product language, or say CT-44 corpus is empty as current fact.

## What not to do

- Do not fold LIBRARY-ADAPTATION.md as current.
- Do not mint COMP-LIB, CT-35.., or a `strats` registry kind.
- Do not fill GAP-0085 / GAP-0063 / GAP-0073 hybrid.
- Do not close GAP-0061.
- Do not start population ingest.
- Do not implement code.
- Do not launch `bmad-create-epics-and-stories`.
