# Stage 7 pass-1 consistency review — QML research expansion

Date: 2026-09-16. Reviewer: grok-4.6. Scope: increment docs listed in `_docwork/qml-research-increment-brief.md` against ADR-0023, architecture spine AD-1..AD-21 + inherited invariants, and the 15 hunt items. No file edits.

## Verdict: FAIL-with-amendments

QL-1 four-count, no-new-COMP/CT, gap standing, graduation vs spawn, `origin`/`originating_research_ref`, Stage 0 `graph`, LAYOUT-DEMO, and CT-33/CT-44 wiring stamps are consistent with the proposed package. Amendments are required before pass: STRATS still used as a corpus product noun in a touched spec, proposed parent-authority clauses spliced into ratified May-never / AD-19 prose without `[PROPOSED]`, and the glossary Seed-corpus entry contradicts its own product-noun law.

## Findings

### 1. major — `docs/components/qmf-registry.md`

**What's wrong.** The ratified Workbench AD-3 paragraph still says “STRATS remains a KnowledgeSource corpus and **does not write registry kinds**.” That is STRATS as product language on a file this increment touched. The new `[PROPOSED]` subsection on the same page correctly says “the seed corpus still writes no registry kinds.”

**Contradicts.** DEC-0380 (ratified: STRATS is not a QMX language; `source_id=strats` is adapter key only), DEC-0398 / AD-18 (product nouns: seed corpus), DEC-0408 (dead: STRATS-as-language).

**Fix.** In the 2026-09-14 Workbench paragraph, replace “STRATS remains a KnowledgeSource corpus” with “the seed corpus behind CT-44 still writes no registry kinds (`source_id=strats` is the adapter key, not a Library kind) (DEC-0380) (DEC-0271).”

### 2. major — `docs/glossary.md` (Seed corpus)

**What's wrong.** The new Seed corpus entry reads: “the portable Stats tree QMX binds by `root_path`. Not product language. … Product language is research / hypothesis / dictionary entry / seed corpus.” “Not product language” lands on the term being defined, then the next sentence names seed corpus as product language.

**Contradicts.** DEC-0398 / AD-18 (Stats tree = seed corpus, a product noun; STRATS/Stats-as-brand is what is banned).

**Fix.** Rewrite the second sentence to “Stats / STRATS is not product language” and keep “Product language is research / hypothesis / dictionary entry / seed corpus.”

### 3. major — `docs/components/qma-core.md`, `docs/components/qma-daemon.md`, `docs/glossary.md` (Knowledge)

**What's wrong.** New mill-authority sentences are written as current ratified law instead of `[PROPOSED]` parent amendments:

- `qma-core.md` Authority **May never** now forbids parsing dictionary/DNA meaning and authoring Stage 0 hypotheses (DEC-0399, DEC-0396) with no `[PROPOSED]` tag. `qml.md` tags the equivalent May/May-never clauses `[PROPOSED]`.
- `qma-daemon.md` Authority **May never** now forbids writing `research_root` / a second `source_id` and authoring hypotheses (DEC-0388, DEC-0399) with no `[PROPOSED]` tag. FM-21 / FM-22 are likewise untagged; `qml.md` FM-13..16 are tagged.
- `qma-daemon.md` ratified AD-19 Knowledge paragraph now states “the adapter over the operator-configured seed plain-file library” as current AD-19 prose (DEC-0380 cited; DEC-0403 not tagged).
- Glossary **Knowledge** opening states a bound Seed corpus and “QMA cites; QML owns meaning (DEC-0399)” as the canonical definition; only the later empty-corpus sentence is tagged `[PROPOSED, DEC-0399, DEC-0403]`.

**Contradicts.** Increment standing rule and DEC-0403 (parent amendments stay `[PROPOSED]`, never silent overrides); DEC-0388 / DEC-0399 / DEC-0396 / DEC-0402 are provisional (AD-8, AD-19, AD-16, umbrella), not accepted parent law. Same standing as the QL-1 four-count, which `qml.md` / L11 correctly keep `[PROPOSED]`.

**Fix.** Tag every new mill clause in ratified May-never, FM rows, the AD-19 Knowledge sentence, and the Knowledge glossary opening `[PROPOSED]` and cite the provisional DEC; leave the ratified empty-corpus / three-count sentences in place beside them.

### 4. minor — `docs/AGENTS.md` (QML research mill hard rules)

**What's wrong.** The mill hard-rules bullet is one uncited paragraph after a range heading (`DEC-0380..DEC-0403`). Workbench hard rules on the same page cite a DEC on each normative sentence. “Do not fill GAP-0085” also wants DEC-0413 (dead fill-now), which is outside the heading range.

**Contradicts.** Drafting rule “every new normative sentence cites a DEC”; DEC-0413 (GAP-0085 fill-now is dead).

**Fix.** Cite per sentence: DEC-0380 (STRATS), DEC-0402 (no COMP/CT), DEC-0381 (hypotheses not Library), DEC-0387 (three entries; not `spawn_governed`), DEC-0398 (`graph`), DEC-0413 (do not fill GAP-0085).

### 5. minor — `docs/components/qma-wire.md` FM-10; `docs/components/qma-core.md` FM-12

**What's wrong.** New federated-hit / hypothesis-authorship failure modes sit in the ratified FM tables without `[PROPOSED]`, unlike `qml.md` FM-13..16.

**Contradicts.** DEC-0389 / DEC-0412 / DEC-0399 standing (provisional package claims).

**Fix.** Mark FM-10 and FM-12 `[PROPOSED]` and keep the DEC cites already on those rows.

## Hunts with no defect

| # | Hunt | Result |
|---|---|---|
| 1 | Silent QL-1 four-count as accepted | Clear. `qml.md`, L11, glossary QML, overview, `dependencies.yaml` keep the ratified three-count and tag four-count `[PROPOSED]` (DEC-0403). |
| 3 | New COMP or new CT | Clear. Preflight reuse; no `COMP-LIB`; no CT-35+; CT-40 family additive only. |
| 4 | GAP-0085 filled; GAP-0061 closed; GAP-0073 hybrid closed | Clear. GAP-0064 sibling; GAP-0061 not closed; GAP-0073 layout trigger met, hybrid deferred; GAP-0085 deferred (DEC-0413). |
| 5 | Hypotheses as Library objects / registry kinds | Clear. Refused until CT-33 (DEC-0381, DEC-0401). |
| 6 | `spawn_governed` equated with graduation | Clear. Distinct (DEC-0387, DEC-0397, DEC-0270). |
| 7 | `originating_research_ref` = Citation digest | Clear. Illegal; `research_ref` only (DEC-0397). |
| 8 | `origin` reshaped off `"qma"` | Clear. Frozen `"qma"`; `seed_cite` distinct (DEC-0387). |
| 9 | Stage 0 field named Confluence | Clear. Field is `graph` (DEC-0398); CT-34 Confluence unchanged. |
| 10 | LAYOUT-DEMO mints `research_ref` or invented exits | Clear. SCN-0017 + qml FM-13/15 refuse both (DEC-0394, DEC-0400, DEC-0401). |
| 11 | QMA writes `research_root` or authors hypotheses | Clear in proposed sections and FMs (DEC-0388, DEC-0399). Defect is tagging (finding 3), not the rule. |
| 12 | git subtree absorb; graph as executor | Clear. Dead DEC-0410 / DEC-0411. |
| 13 | “no code exists” / `defined-unwired` as current CT-44/CT-33 fact | Clear. Both `source-inspected`; `8510c03` note does not overwrite `1b451a8` (DEC-0286, DEC-0406). |

DEC-0380 paradigm (STRATS not a language; no sixth COMP; no new CT; mill absorbed as QML Stage 0) is treated as ratified throughout, which matches ADR-0023. The fail is standing-of-claims and leftover STRATS product copy, not a paradigm reversal.

## Desk amendments 2026-09-16

Findings 1–5 applied at desk: `qmf-registry.md` Workbench paragraph now says seed corpus / adapter key; glossary Seed corpus says Stats/STRATS is not product language; mill May-never / FM / Knowledge clauses tagged `[PROPOSED]`; AGENTS mill rules cite per sentence including DEC-0413; `qma-wire` FM-10 and `qma-core` FM-12 tagged `[PROPOSED]`. `lint_docs` re-clean after those edits.
