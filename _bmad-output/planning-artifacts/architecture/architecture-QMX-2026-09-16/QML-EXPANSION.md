---
name: QML-EXPANSION
type: architecture-discussion
purpose: reviewable explanation for operators and downstream agents
sitting: architecture-QMX-2026-09-16
status: draft
created: '2026-09-16'
updated: '2026-09-16'
spine: ARCHITECTURE-SPINE.md
review_status: proposed — not operator-accepted
supersedes: LIBRARY-ADAPTATION.md (first distill: adapt-to-STRATS as a second language)
---

# QML research expansion — the mill absorbed as bot-creation

This is the discussion companion to `ARCHITECTURE-SPINE.md`. The spine is the build contract. This file is what a human (and documentation-factory) need in order to judge the restart. **Nothing here is operator-accepted until review.** Implementation is not done because the design is written.

The first distill of this sitting treated Stats as a language QMX would adapt to, behind a two-rail Library facade. That was the wrong notion. The operator’s restart: STRATS is not QMX’s language. The folder was a **staging mill** built under the assumption that QMX was still unfinished. Absorb the mill as an **expansion of QML**, because QML is the library for creation of bots globally in QMX. QMF is the framework. QML, QMB, and QMA are libraries. No new COMP.

## 1. What the mill actually was

Stats was never meant to stay a parallel product. It was built so that, by the time QMX came up, the operator would not start from raw YouTube and transcripts. Processed material would already be **hypotheses** — structured enough to code, stress-test, and eventually seat.

That is research, not live-bot authoring. QML as it stands today is the opposite end of the same pipe: CT-33/CT-34, Python WHEN, conformance, Book seats. The mill is the huge filter on noise. QML Stage 1 puts the survivors into executable structure. They are not two languages. They are two stages of **one authoring library**.

Recovered independence law (Friendly Greeting + Gold Mine, ontology only — no Hermes crews, no n8n, no Gemini, no video pipeline):

```text
dictionary entry     → what reusable thing exists?          (role-neutral)
role binding         → what job does it do in this candidate?
logic graph          → how do bound parts interact?         (Boolean / temporal / stateful)
hypothesis package   → candidate spec + evidence + holes + lineage
```

“Specking a bot” in that folder meant producing a **candidate specification**, not writing a trading bot, not backtesting, not seating. QMX was later. Pillars were human lenses, not a closed schema.

The mill’s real gift is not the 239 terms. It is the **refusal to invent**: `entry_hypothesis`, unresolved F, H unknowns, transfer caveats, evidence class, colliding slugs kept rather than merged. A developer who is not a trader can cite `bullish-engulfing` instead of reinventing prose. A source that never stated an exit does not grow a fake stop because a schema demanded one.

That honesty envelope is load-bearing. If QMX “adapts to STRATS” as a second language, the envelope stays outside QML and graduation has to translate across a dialect boundary forever. If QML **owns** the mill, the envelope is an authoring invariant (AD-20) and graduation is a collapse, not a translation.

## 2. Why QML, not a new language, not QMA, not QMB

| Wrong home | Why it fails |
| --- | --- |
| Keep STRATS as QMX’s language | Operator rejected. Two vocabularies for one bot-creation job. UI and agents would speak a dialect QML does not graduate. |
| New COMP-LIB / “Knowledge Base” | Workbench AD-1, DEC-0084, L7. The mill is a process, not a sixth application. |
| Park the mill in QMA | QMA is coordination + knowledge **transport** (CT-44). It must not author bots (Workbench AD-4) and must not execute (QMA AD-16). Meaning types in QMA would make knowledge own bot-creation vocabulary. |
| Park the mill in QMB | QMB is experimentation after something runnable exists. A hypothesis is not a run. Governed spawn is not graduation (`workbench.py` already refuses that). |
| Call Stage 0 a second language / revive `.qml` | QL-2. Stage 0 compiles/authors into the same two artifacts. It does not add a third governed half. |

QML is the only library whose charter is **creation of bots**. Creation starts when noise is tagged, not when `fp1` is minted. Stage 0 is upstream authoring. Stage 1 is the ticket. QL-8 already has the hook: `graduate_to_governed` requires a distinct `originating_research_ref` and returns declaration + logic + `promoted-from` edge content. The mill is what that ref is supposed to point at.

Honest parent touch: QL-1 currently says QML’s whole surface is **three** thin things (CT-33/34 types, QL-7 protocol, QL-8 gate). A Stage 0 contract with its own format version is a **fourth**. Pretending it is “helpers under (1)” is false — Stage 0 does not produce CT-33 content until graduation. The no-CT-* rule already allows QML-local contracts (QL-7/QL-8). The enumeration is what needs a **[PROPOSAL] QL-1 amendment**. Factory still implements `qml.research` now; hiding Stage 0 in QMA or host-private DNA to keep the three-count is not legal.

Gate tightenings applied 2026-09-16: `research_ref` is an fp1-shaped `qml-research-hypothesis` fingerprint (not a registry kind); live handle `origin` stays `"qma"`; seed handoff is distinct `seed_cite`; single hypothesis writer is the QML authoring composition root; viewing LAYOUT-DEMO does not mint identity; Stage 0 composition field is `graph`.

## 3. Two-stage authoring as a filter stack

The mill is source-agnostic. Video ingest is paused; the filter is not. Any noisy claim — transcript, idea, chart, discretionary journal, seed package — can enter the same stack.

| Layer | What it does | Owner |
| --- | --- | --- |
| 0 Source bytes | Portable files. Seed today; population later | Stats tree; QMA snapshots |
| 1 Vocabulary | Tag noise with stable dictionary ids | QML helpers over files |
| 2 Binding | Give those ids a job in **this** candidate | QML Stage 0 |
| 3 Graph | Boolean / temporal / lifecycle composition as **meaning** | QML Stage 0 |
| 4 Honesty | Evidence map, F labels, H unknowns, class taxonomy, transfer caveats | QML Stage 0 |
| 5 Graduation | Collapse into CT-33 + Python (+ CT-34) with lineage | QML QL-8 + host |
| 6 Experiment | Governed / coordinated / ungoverned tunnel | QMB |
| 7 Seat | Paper then live | Human L17 → QMN |

Don’t-box-in: a Quant may skip layers 1–5 and write ordinary Python into the QMB tunnel. Stage 0 is not a toll booth. Conformance gates **citation and seats**, never tunnel entry.

Graduation is a **collapse**, not an import:

| Stage 0 | Stage 1 |
| --- | --- |
| Open eligible roles (invalidation, target, context, …) | Closed CT-34 `level \| trigger \| confirmation \| filter` + Python remainder |
| Graph operators (`ALL` / `sequence` / `within` / arming) | Python WHEN |
| F labels including `unresolved` | Empty `permitted_exit_intents` and/or Book family policy — never invented stops |
| Dictionary slug | Human-chosen CT-16/CT-17 producer or plain Python |
| Hypothesis `research_ref` | Distinct `originating_research_ref` on the Bot; Bot `fp1` is new |
| DNA I research lineage | CT-07 `promoted-from` (host-stamped); not a copy of DNA I |
| DNA B claims | Origin citations; **not** CT-32 |

CT-32 is measured edge after a run. DNA B is source-faithful claim mapping. Collapsing them is how a YouTube sentence becomes a performance number.

## 4. Seed versus product

Stats remains the canonical **seed corpus** at `C:/Users/Mubarak/Desktop/Stats`. QMX points `root_path`; it does not git-absorb. `Desktop/strats` is tar-flag debris.

`source_id=strats` on the research-corpus plugin is a **life-of-source adapter key**. Cites forever depend on it. That does not make STRATS the product language. UI, glossary, and agent prompts say seed corpus / dictionary entry / hypothesis / research. Seed-disk ids may appear as imported locator text.

QMA AD-19’s law (read-only, no QMX fields in the corpus, six confidence dimensions, cite-copy) **holds**. The closing sentence “empty corpus / layout unratified” is factually stale (239 dictionary entries, LAYOUT-DEMO, schema locks). That is a docs refresh, not a law change.

Workbench AD-3 **holds**: hypotheses are not Library objects until CT-33 registration. Product Library discovery stays two rails (Knowledge cites + Artifact `fp1`). Stage 0 drafts are found on the QML research surface, not as a third Library hit class. `register_library_kind("strats")` stays refused.

## 5. Alternatives (restart)

| Option | What | Verdict |
| --- | --- | --- |
| **H. Absorb mill as QML Stage 0** | Fourth QML surface; Stats as seed; graduate via existing QL-8 | **Recommend** |
| A. Two-rail Library, QMX adapts to STRATS as language | First distill of this sitting | **Superseded** — operator rejected the language |
| B. Knowledge tools only | Agents cite; no Stage 0 types | Legal, fails “creation of bots starts here” |
| C. Mint seed packages as registry kinds | `strats` Library kind or auto CT-33 | Conflicts Workbench AD-3, AD-7. **Reject** |
| D. New COMP-LIB | Sixth application | Conflicts Workbench AD-1, DEC-0084. **Reject** |
| E. Git subtree Stats into QMX | Absorb corpus | Conflicts QMA AD-19. **Forbid** |
| F. Compile graph → executor | DNA as runtime | Conflicts AD-6, QL-2. **Reject** |
| G. Fill GAP-0085 to fit DNA roles | Mechanism nouns now | Parent deferred; Stage 0 already carries open roles. **Defer** |

Reuse-or-new: **reuse** COMP-QML (expand), COMP-QMA-CORE, COMP-QMA-DAEMON, `research-corpus`, COMP-QMB, COMP-QMF-REGISTRY. Connect the stub. No new COMP, no new CT.

## 6. Worked mapping (same cases, new plane)

See `inputs/worked-mapping.md`. Headline unchanged in outcome, changed in owner:

- `swing-high` survives as a **dictionary entry** (files until cite). QML helpers resolve fields. Eligible roles including invalidation stay on Stage 0. It does not become a CT-16 producer.
- `STRAT-000001` survives as a **hypothesis** of class `entry_hypothesis` with all F `unresolved`. Stage 0 view must not invent exits. Graduation, if anyone later authors a bot, is human/QML: CT-34 legs + Python ALL/THEN, CT-33 with empty exit intents, QMB run, human promote.
- `level-invalidation` stays a thin dictionary entry with unscored/low empirical confidence. Not a CT-29 close-reason.
- Lineage planes stay split: seed I ≠ CT-07 ≠ ExperimentSpec `branches-from`.

## 7. Complementary richness (do not flatten)

QML/QMF is richer at identity (`fp1`), footprint completeness, parameter space + units, two-layer conformance, logic-reference, producer bindings.

The mill is richer at meaning (role-neutral entries, eligible roles, source-faithful evidence, F/H holes, Boolean-temporal-lifecycle graph, candidate class taxonomy).

They are sequential planes of one authoring library, not competing ontologies. Full table: `research/compare-strats-vocab-vs-qml.md`. That note’s “adoption posture” (meaning stays in QMA knowledge) is **superseded** by this restart: meaning types move into QML Stage 0; QMA remains the cite transport.

## 8. What this sitting still refuses

Hermes specialist fleet, staging/curator, n8n-as-required, Gemini routing, video population, tests-as-product, promotion ceremony, software-first, mandatory wizard, `.qml` revival, auto CT-33, graph as executor, GAP-0085 fill, COMP-LIB, `strats` as a Library kind, treating `spawn_governed` as L33 graduation, requiring Stage 0 to write Python.

## 9. First slice and later

**Slice 0 (AD-14):** bind `root_path` to Stats; snapshot; cite `STRAT-000001` and `swing-high`; Stage 0 hypothesis view preserves `entry_hypothesis` + unresolved F; vocab helper resolves the 12 fields; `strats` kind still refuses; no mint; no videos.

Later increments (not this slice): host research root; origin field on graduation of a real mint; QMB governed run of a graduated bot; UI chrome; optional second CT-44 `source_id` over the research root.

## 10. UI / agent readiness

ui@af66288 has **no Library pages** and no research surface. GAP-0081 stub. Backend can implement seed bind + Stage 0 types now. Chrome is the UI session.

| Action | Owner | Input | Output | Identity |
| --- | --- | --- | --- | --- |
| Search seed | QMA CT-44 | query + snapshot | locators | durable after cite |
| Resolve dictionary entry | QML research helpers | cited bytes | 12 fields + collisions | not `fp1` |
| Draft hypothesis | QML Stage 0 | cites + author edits | `research_ref` | QML ladder |
| Search artifacts | QMB library.search | kind + as-of | hits | `fp1` |
| Federated Library search | facade | query | KnowledgeHit \| ArtifactHit | per class |
| Graduate | QML + host | hypothesis + two artifacts | CT-33/34 + CT-07 edge | Bot `fp1` ≠ `research_ref` |

## 11. Audit (carried)

| Tree | Rev | Role |
| --- | --- | --- |
| QMX planning | `main@f722694` | Docs/planning; dirty uncommitted docs preserved |
| Implementation | `integration@8510c03` | Inspect worktree `.worktrees/integration-inspect` |
| UI | `ui@af66288` | Docs-only; no app routes |
| Seed | on-disk 2026-09-16 | `C:/Users/Mubarak/Desktop/Stats` — validate.py OK: 239 / 229 unique / 9 collisions / LAYOUT-DEMO |

`graduate_to_governed` exists on integration. Stage 0 types do not. research-corpus still points at an in-memory two-file stub.
