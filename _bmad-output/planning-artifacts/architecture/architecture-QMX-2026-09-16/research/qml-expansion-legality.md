# QML expansion legality — STRATS absorbed as COMP-QML Stage 0

Date: 2026-09-16  
Status: research note for spine amendment (not operator-accepted)  
Operator seed: STRATS was a staging mill (noise → structured hypothesis) because QMX was unfinished; it is **not** a second QMX language. Absorb as an **expansion of COMP-QML**. QMF stays the framework. No new COMP. No Hermes/QMA agentics. No videos.

Primary parents:
- [`architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md`](../../architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md) — QL-1, QL-2, QL-5, QL-7, QL-8
- Integration inspect: `qml/src/qml/generation/{__init__.py,gaps.py}`, `qml/src/qml/conformance/registration.py`
- Companion ontology dig: [`compare-strats-vocab-vs-qml.md`](compare-strats-vocab-vs-qml.md)

---

## Answers

### 1. Can QML grow a fourth surface (research-candidate authoring types on QML's own format-version ladder) without minting a CT-* and without a new COMP?

**Yes — by the same mechanism QL-7 / QL-8 already use.**

QL-1's deep rule is: **QML mints no new QMF-ladder (CT-\*) shared contract**; CT-33/CT-34 remain qmf-registry kinds; QML-local contracts ride **AD-5's second ladder** (not CT-numbered), exactly as QMB owns run-config/ledger contracts. QL-7 (runtime protocol) and QL-8 (conformance) are already those local-ladder surfaces.

A **research-candidate** package — dictionary cites, role bindings, logic-graph/DNA holes, exit-completeness labels, unknowns — can be typed and versioned as another QML-local contract on that same ladder:

- No new `CT-*`
- No new COMP (stays inside `qml` / COMP-QML)
- No qmf-registry kind for the candidate itself
- Host composition root still stamps any later CT-06/CT-07 envelopes; QML returns fingerprintable content only (QL-1 registration write path)

Generation code already points the same way: QML authors; host mints; QMB runs; `.qml` DSL refused; GAP-0085 nouns refused (`generation/__init__.py`, `generation/gaps.py`).

### 2. Does that contradict QL-1 "three thin things"? Is the honest move a proposed QL-1 amendment?

**Yes, it contradicts the enumeration. Honest move = [PROPOSAL] QL-1 amendment.**

QL-1 literally: *"Its whole surface is three thin things: (1) author-side types… CT-33/CT-34; (2) the bot runtime protocol (QL-7); (3) the conformance gate (QL-8)."*

A Stage-0 candidate surface is a fourth enumerated thing. Pretending it is "just helpers under (1)" would be dishonest: Stage 0 does **not** produce CT-33/CT-34 content until graduation; it is a distinct contract with its own format version, identity basis, and refuse set.

**[PROPOSAL] QL-1 amendment** (shape, not final wording):

> QML's surface is four thin things: (1) author-side types/helpers for Bot-domain registry artifacts (CT-33/CT-34); (2) research-candidate authoring types on QML's own format-version ladder (Stage 0 — structured hypothesis; non-executable; cites files, never registry kinds); (3) the bot runtime protocol (QL-7); (4) the conformance gate (QL-8). QML still mints no new QMF-ladder (CT-\*) contract and remains one uv distribution / one COMP.

Thin-by-law constraints that must stay in the amendment:

- Stage 0 is **not** a second shared-contract stratum beside QMF
- Stage 0 is **not** cited by governed evidence or seats
- Stage 0 never sizes, never emits CT-23 intents, never becomes a Book/node seat
- Graduation (QL-8) is the only bridge into CT-33+Python

Tag: **[PROPOSAL]** vs parent QL-1 text. Mechanism already parent-legal; the count is what needs amendment.

### 3. Does a candidate package that GRADUATES to the same two artifacts (CT-33 + Python) violate QL-2 "no second language"?

**No — graduation into the two artifacts is QL-2 / QL-8's intended path.**

QL-2: a governed bot is exactly declaration (CT-33) + plain-Python logic; `.qml` is not revived; *"a future declarative condition grammar, editor surface, or agent codegen lane … **compiles to these same two artifacts** — nothing forecloses it."*

QL-8: *"a working ungoverned experiment graduates by minting the two artifacts with a lineage edge back to its originating research artifact."*

Code already implements that edge: `graduate_to_governed` in `conformance/registration.py` requires both conformance layers, links a distinct `originating_research_ref`, and returns declaration + logic + `promoted-from` edge content (host stamps CT-07).

What **would** violate QL-2:

- Executing Stage 0 / `graph.yaml` / DNA operators as a host runtime
- Keeping a durable third governed artifact beside CT-33 + Python
- Reviving `.qml` as editable bot source
- Auto-minting CT-33 from DNA without human/QML authorship (Workbench / AD-7 posture)

Stage 0 as **pre-governed staging that compiles/authors into the two artifacts** is QL-2-compatible. STRATS folder = seed/import into Stage 0, not a product language.

### 4. Where do dictionary primitives live?

| Locus | Verdict |
| --- | --- |
| **Files until cite** (Stats/seed tree; path + optional fragment; durable only after cite/copy) | **Required home of meaning bytes** |
| **QML-local Stage-0 types that cite those files** (locator / digest / citation ref; eligible-role prose; not `fp1` of a registry kind) | **Legal handoff surface inside COMP-QML** |
| **qmf-registry kinds for primitives** | **Forbidden** — would mint CT-\* / Artifact-rail kinds; collapses knowledge into Bot-domain identity; violates "no new CT" and Workbench AD-3 "STRATS writes no registry kinds" |

Do **not** auto-map a dictionary slug into a CT-16 producer (QL-5 / compare note). A human (or Stage-1 authoring) chooses a producer binding when graduating a leg. Dictionary **eligible roles** (invalidation, target, context, …) stay on the cite/Stage-0 side; CT-34 keeps its closed-and-addable enum (`level | trigger | confirmation | filter`) until a separate CT-34 format mint — not smuggled via dictionary import.

QMA CT-44 snapshot/cite machinery may remain a **transport** for file cites if already present; this note does not reopen Hermes agentics or a Knowledge-product language. Under the operator ruling, the **authoring expansion** owns Stage 0 inside QML, not a parallel STRATS product ontology.

### 5. GAP-0085 — fill now as this expansion, or keep deferred?

**Keep deferred. Richer roles stay on the candidate layer only.**

Evidence:

- `gaps.py`: `GAP_0085_STATUS = "deferred"`; `MECHANISM_VOCABULARY_MINTED = False`; `refuse_gap_0085_nouns` / `mint_mechanism_vocabulary` always refuse; write-owner `qml-host`, increment `later`
- Generation refuses nested mechanism keys; CT-34 `role: filter` is explicitly **not** a GAP-0085 hit
- Parent Deferred table and this sitting's inherited rows already list GAP-0085 as catalog-deferred
- Filling GAP-0085 now to "fit" STRATS would mint typed `EntryMechanism` / `ExitMechanism` / `InvalidationRule` / … onto the governed authoring path — a different, heavier mint than Stage 0 cites, and unnecessary for graduation (QL-5: WHEN in Python; exits via Book/`permitted_exit_intents`)

Stage 0 may carry **open, source-faithful role labels and DNA F/H holes** without promoting them into CT-34 or GAP-0085 nouns. At graduation, roles collapse by human authorship into the closed CT-34 enum + Python WHEN + Book exit policy. Informal bridge tables remain handoff aids, not contract mints.

---

## Recommended shape (one)

**COMP-QML two-stage authoring; STRATS is seed, not language.**

```text
Stage 0  research-candidate (QML-local format ladder)
         dictionary file cites · bindings · graph/DNA holes · F/H labels
         non-executable · not seat-citable · no CT-* · no new COMP
            │
            │  graduate_to_governed (QL-8)
            │  lineage → originating research ref
            ▼
Stage 1  CT-33 + CT-34 + plain-Python logic (unchanged)
         QL-7 hosts · QL-8 ticket · Book/QMB/QMN as today
```

| Decision | Tag |
| --- | --- |
| Fourth QML surface = Stage-0 research-candidate types on QML's own ladder | **[PROPOSAL]** QL-1 amendment (three → four thin things) |
| No new COMP; no new CT-\*; QMF remains framework | Parent-consistent |
| Graduation → same two artifacts + research lineage edge | Parent-consistent (QL-2, QL-8, `graduate_to_governed`) |
| Dictionary = files until cite; QML-local cites only; registry kinds forbidden | Parent-consistent on "no CT"; **supersedes** earlier "adapt-to-STRATS as product Knowledge language" framing where that framed STRATS as a lasting second ontology |
| GAP-0085 stays deferred; richer roles on Stage 0 only | Parent-consistent (Deferred / `gaps.py`) |
| No Hermes agentics; no video population; no `.qml` revival; `graph.yaml` never executor | Parent-consistent (QL-2, QL-5) |
| Prior sitting AD-1..AD-14 "two-rail Library / adapt-to-STRATS" paradigm | **Parent-conflict** with operator restart — keep AD IDs if amending that spine, but paradigm shifts to QML expansion; do not silently keep "STRATS is the product language QMX adapts to" |

### What not to do

- Do not mint `COMP-LIB` or a STRATS registry kind
- Do not fill GAP-0085 to absorb DNA roles
- Do not treat Stage 0 as a third governed bot half
- Do not compile Stage-0 graphs into QMB `run_slice` / node execution
- Do not claim QL-1 already allows a fourth surface without amending the "three thin things" sentence

### Minimal parent touch list if accepted

1. **[PROPOSAL]** Amend QL-1 surface enumeration (+ Stage 0 thin-by-law bullets).
2. Add a short QL-# or QL-8 subsection: research-candidate contract + graduation identity (originating ref already coded).
3. Amend this sitting's spine paradigm from "adapt-to-STRATS Knowledge Library" to "QML Stage-0 expansion; Stats as seed/import" (AD-15+ as memlog directed) — mark superseded rows explicitly.
4. Leave GAP-0085 / GAP-0063 catalog rows deferred.

---

## Source anchors

```44:50:C:/Users/Mubarak/Desktop/QMX/_bmad-output/planning-artifacts/architecture/architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md
### QL-1 — QML identity: the authoring library, thin by law
...
- **Rule:** QML is the bot-authoring **library** ... Its whole surface is three thin things: (1) author-side types and helpers producing the Bot-domain registry artifacts (CT-33/CT-34) on `qmf-core` nouns; (2) the bot runtime protocol hosts invoke (QL-7); (3) the conformance gate (QL-8). **QML mints no new QMF-ladder (CT-*) shared contract of its own** — ... the runtime protocol (QL-7) and conformance contract (QL-8) are QML-local contracts on QML's own format-version ladder ...
```

```56:60:C:/Users/Mubarak/Desktop/QMX/_bmad-output/planning-artifacts/architecture/architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md
### QL-2 — Two halves of a bot; the `.qml` DSL is not revived
...
**The `.qml` bot-source file format and its Monaco surface are not revived in V1** — no second language: ... A future declarative condition grammar, editor surface, or agent codegen lane ... **compiles to these same two artifacts** ...
```

```113:113:C:/Users/Mubarak/Desktop/QMX/_bmad-output/planning-artifacts/architecture/architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md
  - **Graduation path:** a working ungoverned experiment graduates by minting the two artifacts with a lineage edge back to its originating research artifact (AD-22's graduation mechanics generalized to bots).
```

```63:70:C:/Users/Mubarak/Desktop/QMX/.worktrees/integration-inspect/qml/src/qml/generation/gaps.py
GAP_0085_ID: Final[str] = "GAP-0085"
...
GAP_0085_STATUS: Final[str] = "deferred"
...
MECHANISM_VOCABULARY_MINTED: Final[bool] = False
```

```326:360:C:/Users/Mubarak/Desktop/QMX/.worktrees/integration-inspect/qml/src/qml/conformance/registration.py
def graduate_to_governed(
    ...
) -> Result[Graduation]:
    """Mint the two artifacts with a ``promoted-from`` edge to originating research.
    ...
    """
```
