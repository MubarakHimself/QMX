# Epic 9 — qmf-structure — Independent Verification PLAN

> Per-epic template compliance: the eight sections below run in the template's
> fixed order. **Section 4 (the independent test list) was authored before any
> `packages/qmf-structure/src/**` implementation body was opened.** Only the
> public module/file *names* and the directory layout were listed prior to
> Section 4 (permitted); no implementation body was read. Oracles are
> `epics.md` (Epic 9 section), `docs/contracts/ct-17-causal-structure.yaml`,
> `docs/constitution.md`, and `docs/registry/variables.yaml` — never the code.
>
> **Authority-absence note (load-bearing):** the two test-artifact authorities
> named in the lane brief —
> `_bmad-output/test-artifacts/test-design-qa.md` and
> `_bmad-output/test-artifacts/test-design/QMX-handoff.md` — **do not exist in
> this worktree snapshot** (`_bmad-output/test-artifacts/` is absent). This
> plan is therefore grounded on the surviving primary oracles above. The
> handoff's Epic-9-specific risk-gate rows and its "15 P0/P1 assertions"
> cross-reference cannot be cited verbatim; the universal risk rows that every
> sibling lane applies (R-002 no-raise, R-003 existing-test audit) are carried
> forward by pattern, and the absence is filed in Section 8 (F-E09-001). No
> requirement was invented to fill the gap.

---

## Section 1 — Header and baseline

- **Epic:** 9 — qmf-structure (Wave 3, **M**). "Market structure as causal,
  append-only, look-ahead-safe chart-object families." (epics.md L1845-1849.)
- **Tier:** **T3** (per lane brief). Tier scope: **L3 acceptance for every
  P0/P1 AC** as the primary deliverable, plus a **targeted L1 property** layer
  for the highest-value quantified universals (the emission-invariant / future-
  leak refusal and the no-raise refusal universal), a **lean L2 contract** set
  for load-bearing CT-17 invariants that are contract facts rather than epic
  behaviour, **L0** structural gates, and the **L6 requirements-fidelity
  review** seat. **No L4 scenario is owned** (see below); **L5 mutation** is a
  named roster, execution deferred (Section 6/7). One-behaviour-one-level with
  lower-level-wins is applied across L0-L3.
- **Package in scope:** `qmf-structure` (`packages/qmf-structure/`, import root
  `qmf.structure`, src/ layout `src/qmf/structure/`).
- **Modules in scope** (names only, no body read before Section 4):
  `objects.py` (object mint + emission invariant, Story 9.1),
  `lifecycle.py` (confirmation/invalidation/interaction records, read-time
  fold, Story 9.2), `provenance.py` (evidence class, knowledge-time result
  label, Story 9.3), `splits.py` (confirmed-at split partitioning / embargo,
  Story 9.3), `families.py` (family declaration, seed candidate + first
  governed family, Story 9.4), `geometry.py` (point|level|zone|span|
  distribution|graph geometry, sloped/anchored evaluation), `composites.py`
  (composite children max-rule, CT-17), `routing.py` (CT-16-vs-CT-17 routing,
  FM-6), `conformance.py` (CT-17 conformance harness / concept-walk register,
  Story 9.4), `budget.py` (light/heavy benchmark bounds, Story 9.4),
  `research.py` (ungoverned research lane, L33 graduation), `_bench.py`
  (benchmark harness — **present**).
- **Requirement ids this epic owns** (copied from the epics.md FR Coverage Map,
  L59-62 / L277, and the Epic 9 header L1849 — not re-derived):
  - **FR:** **FR-020** only — "Market structure is expressed as causal,
    append-only, look-ahead-safe chart-object families. (CT-17)".
  - **CT:** **CT-17** only (Causal structure lifecycle contract).
  - **Constitution laws:** **L14** (qmf-structure is a V1 library), **L15/L28**
    (versioned-from-first-release; extension over replacement), **L27** (ships
    executable tests + reference usage), **L30** (default-deny: qmf-structure
    imports only qmf-core, nothing imports qmf-structure in V1), **L32**
    (no trading-school name or privilege — FM-9), **L33** (plain-Python
    graduation via the extension shape with a lineage edge).
  - **Registry:** `typed_refusal_codes`, `evidence_classes`,
    `structure_seed_family_candidates`, `result_identity_key` (consumed as
    oracles; the first three are COMP-QMF-CORE / COMP-QMF-STRUCTURE lists).
  - **NFR:** NFR-11 (failure-register discipline; FAILURES.md present — see
    below), AR-21/L27 (tests + examples as tier-1 artifacts — examples present).
- **Epic-local failure modes** (FM labels are scoped to this epic's ACs / CT-17,
  not a global legend): **FM-1** emission-invariant violation → `invalid-input`;
  **FM-2** imprecise confirmation rule → not admitted to the governed library;
  **FM-3** overwrite/refit → prohibited, refit mints a new artifact with a
  `supersedes` edge; **FM-4** confirmed-read over unconfirmed rows →
  `policy-rejection`; **FM-6** routing (CT-16 vs CT-17), indicator consumed as a
  declared input never inline; **FM-7** split-manifest embargo/purge boundary
  refusal; **FM-8** benchmark light-claim / peak-memory regression refused at
  the Tier-2 gate; **FM-9** no trading-school name in any rule or vocabulary.
  (No FM-5 is referenced by Epic 9.)
- **Owned risk-gate rows** (handoff §Risk-to-Story Mapping): **not citable** —
  QMX-handoff.md is absent (F-E09-001). Applied by pattern from every sibling
  lane: **R-002** (no public callable raises; realised as L1-002), **R-003**
  (existing-test audit; realised as Section 5). No live-money row applies —
  qmf-structure emits evidence only and touches no venue/order path.
- **Evidence baseline:** the ranked coverage/Skylos/complexity baseline lives in
  the absent test-design-qa.md, so **no numeric baseline is cited** here (not
  invented). The repo-level `.coverage` / `coverage.json` at the worktree root
  are available to the RESULTS pass; author-written suite coverage is treated as
  R-003 evidence, not as proof of requirement fidelity.
- **Build report:** **None.** Epic 9 is < 20, so no epic build/advisory-review
  report exists (stated explicitly per the template rather than left blank).
- **Distribution-unit artifacts** (confirmed by directory listing only — a
  *positive* confirmation, unlike Epic 8): `FAILURES.md` **present**,
  `examples/structure_usage.py` **present**, `_bench.py` **present**,
  `py.typed` **present**, `README.md` **present**. No NFR-11 / AR-21 / L27
  distribution gap is filed for this package.

---

## Section 2 — Requirement extract

The oracle. Acceptance criteria are quoted / tightly condensed from `epics.md`
(Epic 9); contract clauses are quoted from `ct-17-causal-structure.yaml`.
Nothing paraphrased into a stronger claim. Ambiguities are logged in Section 8,
never resolved by reading code. There is **no golden scenario** for CT-17 in
`docs/scenarios/` (SCN-0001..0012 carry none for structure), so §2.3 is empty by
design and no L4 journey is owned.

### 2.1 Story acceptance criteria (verbatim / condensed, `epics.md`)

**Story 9.1 — scaffold, object mint, emission invariant.**
- "it builds from `packages/qmf/structure/` in src/ layout, versions in the
  roster SemVer lockstep, imports only qmf-core in V1 (any undeclared import
  fails the Tier-2 isolated-environment gate), and its public value types are
  frozen dataclasses with `typing.Protocol` seams."
- "it is minted once carrying family identity plus version, exact-rational
  parameters, its declared confirmation rule, its anchor span (frozen at
  observation, permitted to precede observed-at, excluded from every causality
  test), and observed-at (the earliest instant the object was derivable from
  causally-available data — known-at, never event time) **And** the object is
  never mutated afterward, and anchor span, observed-at, and every lifecycle
  instant are identity fields, never occurrence-classified."
- "it requires `anchor.start ≤ anchor.end ≤ observed-at ≤ confirmed-at ≤
  invalidated-at` and `observed-at ≥` the maximum evidence time of every input
  actually consumed; a violation returns an `invalid input` refusal (FM-1)
  **And** the library returns fingerprintable content and never stamps records
  — the composition root holds the WriterId and the gapless per-(writer, kind)
  sequence."

**Story 9.2 — append-only lifecycle, read-time state.**
- "confirmation, invalidation, and interaction records are separate append-only
  typed records/edges referencing the object's fingerprint, each instant an
  identity field of its own record; interaction records are the only permitted
  way an object's state evolves **And** 'still valid at T' is a read-time fold
  over the object's edge stream per CT-17's read-resolution rule, never a
  stored field."
- "a correction, refit, or state change that would overwrite an object or an
  edge … is prohibited: interaction records append, and a refit mints a new
  artifact with a `supersedes` edge, anchors frozen at each fit, the lineage
  head keeping the first observed-at, and earlier evidence remains (FM-3)."
- "a family whose confirmation rule cannot state 'confirmed the moment X
  happens' with X knowable at that instant … is not admitted; the concept stays
  freely usable in the ungoverned research lane (FM-2); clock-confirmed
  (degenerate) confirmation is legal."
- "invalidation never cascades automatically; the reader may compute cascade at
  read time from lineage."

**Story 9.3 — evidence class, knowledge-time, split governance.**
- "evidence class (`confirmed | unconfirmed | provisional`) is a declared
  identity field and a named part of the result label; an unconfirmed output
  links to its confirmed successor via a typed `confirmed-as` edge **And** a
  read requesting confirmed evidence refuses unconfirmed rows with a `policy
  rejection`, never a silent filter (FM-4)."
- "a decision at instant T … may consume evidence with `confirmed-at ≤ T` —
  equality is consumption, not look-ahead; refuse-at-equal governs causality
  tests between derived artifacts, not consumption."
- "the bound [confirmation-delay, integer observations at the family's BarSpec]
  feeds the split manifests' required purge/embargo widths; a manifest refuses
  any record whose observed-at precedes a boundary while its confirmed-at
  follows it, unless the declared embargo covers the gap (FM-7) **And** an
  unbounded confirmation-delay declaration is legal only for families excluded
  from split-governed evidence."
- "it receives a different result label through its input fingerprints rather
  than silently changing; the label carries producer contract identity, format
  version, input fingerprints, evidence time range, evidence class, and world."
- "live in-memory use persists nothing, but any object cited by a journal event
  or result label becomes governed evidence by that act and is persisted;
  scanners run ungoverned and promote only confirmed objects **And** the full
  look-ahead/causality registration gate (CT-08) remains deferred to the
  backtesting sitting (GAP-0016); the in-component emission invariant is the
  interim guard, not that gate."

**Story 9.4 — first family, conformance harness, benchmarks.**
- "it is one seed candidate (a swing-point family) whose confirmation rule is
  precise — 'confirmed the moment X happens' with X knowable at that instant —
  consuming source/bar observations as declared inputs **And** it holds no
  privilege over operator-authored families … and no trading-school name
  appears in any rule or vocabulary (FM-9)."
- "it keeps the register's concept-walk list expressible — retro-anchored zones
  with consumption state, objects born from another object's invalidation,
  cluster objects over tolerance-grouped extremes, threshold-breach-then-
  reversal objects, ordered multi-phase calendar composites, multi-BarSpec
  nests, cross-instrument divergence objects, distribution-over-price objects,
  a-priori price grids, projected levels, and pattern refits."
- "a value per evaluation instant is CT-16 and a discrete object with a birth
  and a lifetime is CT-17; a family needing an indicator consumes it as a
  declared input through the composition law, never re-implemented inline
  (FM-6)."
- "its rungs are active object-set size, objects minted per bar, and
  interaction records per bar; a light claim exceeding a declared bound (or
  lacking a baseline) is refused at the Tier-2 gate, and a peak-memory
  regression fails exactly as a slowdown does (FM-8)."
- "it stays freely usable in plain Python outside governed evidence, entering
  governed evidence only by graduating through the extension shape with a
  lineage edge to the originating experiment (L33)."

### 2.2 Contract clauses (verbatim, load-bearing CT-17 invariants)

- **Mint-once / immutable:** "An object is minted once, at observation, carrying
  family identity + version, exact parameters, its declared confirmation rule,
  its anchor span, and observed-at; the object is never mutated afterward."
- **Two-dates / knowable-at:** "observed-at is the earliest instant the object
  was derivable from causally-available data — known-at, never event time;
  invalidated-at is the detection instant; a standing (a-priori) object declares
  observed-at = its configuration instant."
- **Anchor excluded from causality:** "The anchor span … is payload geometry
  frozen at observation, explicitly permitted to precede observed-at, and
  excluded from every causality test."
- **Identity, never occurrence:** "Anchor span, observed-at, and every lifecycle
  instant are identity fields and may never be occurrence-classified: a
  structure object is a fact about the market at a time, not a computation."
- **Emission invariant (FM-1):** "anchor.start ≤ anchor.end ≤ observed-at ≤
  confirmed-at ≤ invalidated-at, and observed-at ≥ the maximum evidence time of
  every input actually consumed; violation is an invalid-input refusal."
- **Append-only lifecycle / read-time fold:** "Confirmation, invalidation, and
  interaction records … are separate append-only typed records/edges
  referencing the object's fingerprint … interaction records are the only
  permitted way an object's state evolves; current state is a read-time fold
  over the object's edge stream."
- **Admissibility bar (FM-2):** "A family ships into the governed library only
  when its confirmation rule states 'confirmed the moment X happens' with X
  knowable at that instant; clock-confirmed (degenerate) confirmation is legal;
  imprecise concepts stay free in ungoverned research lanes."
- **Evidence class + confirmed-read refusal (FM-4):** "Evidence class … is a
  named part of the result label and a declared identity field; an unconfirmed
  output links to its confirmed successor via a typed confirmed-as edge; a read
  requesting confirmed evidence refuses unconfirmed rows (policy rejection)
  rather than filtering silently."
- **Refuse-at-equal vs consumption:** "A decision at instant T may consume
  evidence with confirmed-at ≤ T — equality is consumption, not look-ahead;
  refuse-at-equal governs causality tests between derived artifacts, not
  consumption."
- **Confirmation delay + split (FM-7):** "Confirmation delay is a declared
  maximum bound … an unbounded declaration is legal only for families excluded
  from split-governed evidence … a manifest refuses any record whose observed-at
  precedes a boundary while its confirmed-at follows it, unless the declared
  embargo covers the gap."
- **Composites max-rule:** "confirmed-at is the maximum of the children's
  confirmed-at and observed-at the maximum of theirs, never earlier than any
  child; children are order-significant by default … a composite is its own
  artifact with lineage to its children."
- **No auto-cascade / refit:** "Invalidation never cascades automatically … a
  refit is a new artifact with a supersedes edge, anchors frozen at each fit,
  the lineage head keeping the first observed-at."
- **Routing (FM-6):** "a value per evaluation instant is CT-16; a discrete
  object with a birth and a lifetime is CT-17 … a family needing an indicator
  consumes it as a declared input, never inline."
- **Governed-evidence trigger:** "live in-memory use persists nothing, but any
  object cited by a journal event or result label becomes governed evidence by
  that act and is persisted … scanners run ungoverned and promote only
  confirmed objects."
- **No privilege / no school (FM-9):** "No privileged families … families are
  QMX-owned, versioned, addable never redefined" and (L32) "No QMF rule,
  contract, or vocabulary may name or privilege any trading school."
- **Revised-input relabel:** "An object computed on a revised input receives a
  different result label through its input fingerprints rather than silently
  changing; no second revision mechanism exists."
- **Typed refusals / default-deny:** "All failures are typed refusals per
  registry:typed_refusal_codes; qmf-structure depends on qmf-core only in V1,
  all evidence flowing through the composition root under default-deny."
- **Nullability:** "per fp1, null is prohibited; an absent value is an omitted
  key; invalidated-at is absent until an invalidation record exists — never a
  placeholder instant … current state … is never a stored field."
- **Emissions minted by composition root:** "structure objects, lifecycle
  records, and comparison artifacts are minted by the composition root, which
  holds the WriterId and the gapless per-(writer, kind) sequence; the library
  returns fingerprintable content, never stamped records."

### 2.3 Scenario clauses

**None owned.** `docs/scenarios/` holds no CT-17 golden scenario. The
constructed future-leak journey (Section 4, L3-001) is authored *in this plan*
from the emission-invariant and refuse-at-equal clauses above — it is a test
construction, not a quoted scenario, and is recorded as such.

---

## Section 3 — Fault-family checklist

The eight recurring families the Epic 20-23 advisory reviews surfaced (carried
as the standing fault taxonomy). "None" is a result.

| # | Family | Member in Epic 9? | Where / how it manifests |
| - | ------ | ----------------- | ------------------------ |
| a | Unit-kind / exactness treated as optional on a numeric path | **YES** | CT-17 requires exact-rational parameters and exact Price/PriceDelta anchors; pip/point is instrument-scoped from metadata, "never hardcoded". A binary float entering parameters or anchor identity is the defect. Sites: `objects.py`, `geometry.py`. **L1-004, L2-002.** |
| b | An exception where a typed refusal was contracted | **YES** | CT-17: "All failures are typed refusals per registry:typed_refusal_codes." Every emission-invariant violation, confirmed-read, split-boundary breach, and unsupported family must *return* a typed refusal, never raise. R-002 universal. **L1-002, and the refusal assertions in L1-001/L3-001/L3-010/L3-012.** |
| c | A fingerprint that omits a distinguishing input | **YES** | Anchor span, observed-at, and every lifecycle instant are *identity* fields (must enter fp1); confirmation rule and parameters are identity; a revised input must yield a *different* result label. A survivor drops observed-at or an anchor from identity → two causally-distinct facts collide. **L1-003, L3-013.** |
| d | A governance gate implemented at one input shape | **YES** | Three gates must hold over *all* shapes, not one: the emission invariant (over every input set actually consumed), the confirmed-read refusal (over every unconfirmed row, not a sampled subset), and the split-manifest embargo (over every observed-before/confirmed-after record). **L1-001, L3-010, L3-012.** |
| e | An external / caller input trusted without validation | **YES** | The family author's declared observed-at, confirmation rule, and consumed-input set are the untrusted edge: a stamped observed-at earlier than an input's evidence time, or an imprecise confirmation rule, must be *refused*, not accepted. This is the future-leak surface. **L3-001, L3-007.** |
| f | A capability reachable from one door only | **None.** | qmf-structure sits below any door surface (no CLI/MCP door; door parity is E16). Recorded as "none" for the door-parity sense; the analogous discipline (typed-refusal register completeness) is L27/NFR-11, confirmed present (FAILURES.md). |
| g | A ledger / journal line missing on a failure path | **PARTIAL / boundary.** | CT-17's journal-citation trigger is owned here ("any object cited by a journal event … becomes governed evidence … and is persisted"), but journal-event *cardinality* is CT-13/Epic 3. Epic 9 owns only the *becomes-governed-and-persisted* obligation. **L3-014** (scoped to the CT-17 side; CT-13 cardinality noted out of scope §7). |
| h | An existing test that pins the implementation rather than the requirement | **SUSPECT — to be confirmed in Section 5.** | The author suite is `packages/qmf-structure/tests/test_ct17_*.py` (12 modules). The read-time fold, the emission-invariant ordering, and the confirmed-read refusal are exactly what a line-coverage-driven test can satisfy by re-asserting the code's own fold. High prior that `test_ct17_lifecycle.py` / `test_ct17_objects.py` pin the fold rather than the contract's ordering law. |

---

## Section 4 — Independent test list

> **Authored before any `src/` implementation body was read.** Reading a public
> signature to *call* it is permitted afterwards; reading a body before this
> table existed was not. Test ID = `QA-E09-L<level>-<seq>`. Oracle = the exact
> document + clause (never the code). Duplicate-coverage guard: a contract fact
> lives at L2 and is not restated at L3; an epic-specific AC behaviour lives at
> L3; a quantified universal lives at L1; a structural fact lives at L0.

### L0 — Structural gates; oracle = a constitution law / AR / directory fact

| Test ID | Requirement | Level | Oracle | Pri | Assertion (one sentence) |
| ------- | ----------- | ----- | ------ | --- | ------------------------ |
| QA-E09-L0-001 | L30, AR-06, CT-17 | L0 | L30 default-deny | P1 | The `qmf.structure` import graph imports only `qmf.core` (plus stdlib / declared third-party) and nothing in the roster imports `qmf.structure`; any undeclared cross-package import is a finding. |
| QA-E09-L0-002 | Story 9.1 AC-1 | L0 | epics.md ("frozen dataclasses with `typing.Protocol` seams") | P1 | Every public value type exported by `qmf.structure` is a frozen dataclass (mutation raises `FrozenInstanceError`) and every seam is a `typing.Protocol`. |
| QA-E09-L0-003 | FM-9, L32 | L0 | L32 / CT-17 no-privilege invariant | P1 | No trading-school name appears in any family id, rule, vocabulary term, or public symbol (enumerated grep over the export surface and the seed-family declaration); a school name may appear only as prose illustration, never as vocabulary. |
| QA-E09-L0-004 | L27, AR-21, NFR-11 | L0 | L27 tier-1 artifacts | P2 | The distribution unit ships `FAILURES.md`, an `examples/` reference-usage module, `_bench.py`, and `py.typed` (confirmed present); every typed-refusal path named in CT-17 has a `FAILURES.md` register entry. |

### L1 — Property tests (`hypothesis`); oracle = a CT-17 invariant, quantified

| Test ID | Requirement | Level | Oracle | Pri | Assertion (one sentence) |
| ------- | ----------- | ----- | ------ | --- | ------------------------ |
| QA-E09-L1-001 | FR-020, CT-17, FM-1, DEC-0129 | L1 | CT-17 emission-invariant clause | **P0** | For every generated object + consumed-input set, mint succeeds iff `anchor.start ≤ anchor.end ≤ observed-at ≤ confirmed-at ≤ invalidated-at` **and** `observed-at ≥ max(evidence-time of every input actually consumed)`; any violation returns an `invalid-input` typed refusal and never a mutated or partially-minted object. |
| QA-E09-L1-002 | FR-020, CT-17, R-002 | L1 | CT-17 "All failures are typed refusals" | **P0** | Every public callable enumerated from the `qmf.structure` export surface returns a value or a typed refusal (one of the seven `typed_refusal_codes`) and never raises for any generated well-typed input. |
| QA-E09-L1-003 | FR-020, CT-17, DEC-0108 | L1 | CT-17 identity-field / nullability invariant | P1 | Two objects differing in any identity field (family id, version, a parameter, an anchor-span endpoint or price bound, observed-at, or the confirmation rule) produce distinct fp1, and `null` never appears in a fingerprinted field (an absent value is an omitted key; invalidated-at is absent, never a placeholder instant). |
| QA-E09-L1-004 | FR-020, CT-17, DEC-0105 | L1 | CT-17 "exact parameters … exact Price/PriceDelta … slope derived never stored" | P1 | For every generated parameter and anchor, no binary float ever appears in a parameter or in object identity; a float re-enters only through the named analytic-to-exact conversion boundary that states its rounding mode, and slope is derived, never stored, never identity. |

### L2 — Contract tests; oracle = the `ct-17-causal-structure.yaml` clause

| Test ID | Requirement | Level | Oracle | Pri | Assertion (one sentence) |
| ------- | ----------- | ----- | ------ | --- | ------------------------ |
| QA-E09-L2-001 | FR-020, CT-17, DEC-0129/0132 | L2 | CT-17 family-definition invariant | P1 | A family is a *type of chart object* (geometry ∈ open set point\|level\|zone\|span\|distribution\|graph, family-declared) and is never a strategy, bot, or Book category; geometry declared outside the enumerated set is refused. |
| QA-E09-L2-002 | FR-020, CT-17, DEC-0126/0105 | L2 | CT-17 sloped/anchored + calendar clauses | P1 | A sloped/continuous object is identified by integer `(instant, exact Price)` anchors plus a declared versioned evaluation-rule id (slope derived, never identity), and a calendar-anchored level declares a fingerprinted `sampling_policy` (last-known-at-or-before\|refuse) and `schedule_gap_policy` (refuse\|nearest-open-instant\|carry-previous-session). |
| QA-E09-L2-003 | FR-020, CT-17, DEC-0115/0131 | L2 | CT-17 composites invariant | P1 | A composite's confirmed-at is the maximum of its children's confirmed-at and its observed-at the maximum of theirs (never earlier than any child), children are referenced by fingerprint and order-significant unless the family declares the collection unordered, and the composite is its own artifact with lineage to its children. |
| QA-E09-L2-004 | FR-020, CT-17, DEC-0109 | L2 | CT-17 typed-refusal path enumeration | P1 | Every failure path in CT-17 returns one of the declared categories — `invalid-input` (emission-invariant violation), `policy-rejection` (confirmed read over unconfirmed rows; cross-world read), `stale-evidence`, `unsupported-capability`, `unavailable-dependency` — with machine-readable context and retryability, and categories are addable never redefined. |
| QA-E09-L2-005 | FR-020, CT-17, DEC-0131/0102 | L2 | CT-17 `conformance_register` | P1 | The conformance harness keeps the full concept-walk register expressible (retro-anchored zones with consumption state, born-from-invalidation objects, tolerance-cluster objects, breach-then-reversal objects, ordered multi-phase calendar composites, multi-BarSpec nests, cross-instrument divergence, distribution-over-price, a-priori grids, projected levels, pattern refits) without redefining the lifecycle law for any of them. |
| QA-E09-L2-006 | FR-020, CT-17, DEC-0114/0106 | L2 | CT-17 emission-minting clause | P1 | The library returns fingerprintable content and never stamps a record; structure objects, lifecycle records, and comparison artifacts carry no WriterId or per-(writer,kind) sequence of their own (those belong to the composition root). |

### L3 — Acceptance tests; oracle = the `epics.md` Epic-9 AC (epic-specific behaviour)

| Test ID | Requirement | Level | Oracle | Pri | Assertion (one sentence) |
| ------- | ----------- | ----- | ------ | --- | ------------------------ |
| QA-E09-L3-001 | FR-020, CT-17, FM-1, DEC-0129/0121 | L3 | Story 9.1 AC-3; emission-invariant + refuse-at-equal | **P0** | **FLAGSHIP future-leak.** A constructed object whose stamped observed-at *precedes* the evidence time of an input actually consumed is refused `invalid-input`; a confirmation rule referencing data not knowable at the stamped confirmed-at is refused; and a causality test between two derived artifacts refuses at `confirmed-at = T` on the *test* path while a *consumer* at T with `confirmed-at ≤ T` is admitted — no look-ahead object ever enters governed evidence. |
| QA-E09-L3-002 | FR-020, CT-17, DEC-0129 | L3 | Story 9.1 AC-2 | **P0** | An object is minted once carrying family identity+version, exact-rational parameters, confirmation rule, anchor span, and observed-at, is never mutated afterward (every "change" is a new record/artifact), and anchor span / observed-at / every lifecycle instant are identity fields, never occurrence-classified. |
| QA-E09-L3-003 | FR-020, CT-17, DEC-0129 | L3 | Story 9.1 AC-2 (two-dates) | **P0** | observed-at is the earliest *knowable-at* instant (never event time); the anchor span is permitted to *precede* observed-at and is excluded from every causality test, while a standing (a-priori) object declares observed-at = its configuration instant. |
| QA-E09-L3-004 | FR-020, CT-17, DEC-0114 | L3 | Story 9.2 AC-1 | **P0** | Confirmation, invalidation, and interaction records are separate append-only typed records/edges referencing the object's fingerprint, each instant an identity field of its own record, and an interaction record is the *only* permitted way an object's state evolves. |
| QA-E09-L3-005 | FR-020, CT-17, DEC-0129 | L3 | Story 9.2 AC-1 (read-time fold) | P1 | "Still valid at T" (and still-unmitigated) is computed as a read-time fold over the object's append-only edge stream per CT-17's read-resolution rule and is never a stored field. |
| QA-E09-L3-006 | FR-020, CT-17, FM-3, DEC-0114 | L3 | Story 9.2 AC-2 | **P0** | An attempt to overwrite an object or an edge (correction, refit, or state change) is prohibited; a refit instead mints a *new* artifact with a `supersedes` edge, anchors frozen at each fit, the lineage head keeping the *first* observed-at, and all earlier evidence remains. |
| QA-E09-L3-007 | FR-020, CT-17, FM-2, DEC-0132/0133 | L3 | Story 9.2 AC-3 | **P0** | A family whose confirmation rule cannot state "confirmed the moment X happens" with X knowable at that instant is *not admitted* to the governed library (the concept stays freely usable in the ungoverned research lane), while a clock-confirmed (degenerate) rule is admitted. |
| QA-E09-L3-008 | FR-020, CT-17, DEC-0114 | L3 | Story 9.2 AC-4 | P1 | Invalidation never cascades automatically: invalidating a parent leaves children's stored state untouched, and a reader computes cascade at read time from lineage only when it asks for it. |
| QA-E09-L3-009 | FR-020, CT-17, DEC-0110/0131 | L3 | Story 9.3 AC-1 | P1 | Evidence class (`confirmed\|unconfirmed\|provisional`) is a declared identity field and a named part of the result label, and an unconfirmed output links to its confirmed successor via a typed `confirmed-as` edge. |
| QA-E09-L3-010 | FR-020, CT-17, FM-4, DEC-0109/0110 | L3 | Story 9.3 AC-1 | **P0** | A read requesting confirmed evidence *refuses* unconfirmed rows with a `policy-rejection` typed refusal — never a silent filter that drops them and returns a shorter set. |
| QA-E09-L3-011 | FR-020, CT-17, DEC-0106 | L3 | Story 9.3 AC-2 | **P0** | A decision at instant T may consume evidence with `confirmed-at ≤ T` (equality is consumption, not look-ahead), and this consumption path is distinct from the refuse-at-equal that governs causality tests *between derived artifacts*. |
| QA-E09-L3-012 | FR-020, CT-17, FM-7, DEC-0119/0131 | L3 | Story 9.3 AC-3 | **P0** | A family's declared confirmation-delay bound (integer observations at its BarSpec) feeds the split manifests' required purge/embargo widths; a manifest refuses any record whose observed-at precedes a split boundary while its confirmed-at follows it unless the declared embargo covers the gap; and an unbounded declaration is legal only for a family excluded from split-governed evidence. |
| QA-E09-L3-013 | FR-020, CT-17, DEC-0110 | L3 | Story 9.3 AC-4 | P1 | An object computed on a revised input receives a *different* result label through its input fingerprints (never silently changing under the same label), and the label carries producer contract identity, format version, input fingerprints, evidence time range, evidence class, and world. |
| QA-E09-L3-014 | FR-020, CT-17, DEC-0119 | L3 | Story 9.3 AC-5 | P1 | Live in-memory use persists nothing, but any object cited by a journal event or result label becomes governed evidence by that act and is persisted (or its fingerprint-bearing content inlined into the citing record), and scanners run ungoverned, promoting only confirmed objects. |
| QA-E09-L3-015 | FR-020, CT-17, FM-9, DEC-0129/0058 | L3 | Story 9.4 AC-1 | P1 | The first governed family is exactly one seed candidate — a swing-point family — whose confirmation rule is precise and which consumes source/bar observations as declared inputs, holds no privilege over an operator-authored peer family under identical law, and names no trading school. |
| QA-E09-L3-016 | FR-020, CT-17, FM-6, DEC-0126/0127 | L3 | Story 9.4 AC-3 | P1 | The routing test holds: a value per evaluation instant is CT-16 and a discrete object with a birth and a lifetime is CT-17; a CT-17 family needing an indicator consumes it as a declared input through the composition law and never re-implements it inline. |
| QA-E09-L3-017 | FR-020, CT-17, FM-8, DEC-0128 | L3 | Story 9.4 AC-4 | P1 | The benchmark harness carries the same standing as unit tests, its rungs are active object-set size / objects-minted-per-bar / interaction-records-per-bar, a light claim exceeding a declared bound (or lacking a baseline) is refused at the Tier-2 gate, and a peak-memory regression fails exactly as a slowdown does. |
| QA-E09-L3-018 | FR-020, CT-17, L33, DEC-0133 | L3 | Story 9.4 AC-5 | P1 | A concept a family cannot yet state precisely stays freely usable in plain Python outside governed evidence and enters governed evidence only by graduating through the extension shape with a lineage edge back to its originating research artifact. |

### L4 — Scenario test

**None owned.** No CT-17 golden scenario exists in `docs/scenarios/`. The
cross-clause future-leak journey is carried at L3-001 as a constructed
acceptance test, not a scenario walkthrough.

**Planned counts — L0: 4 · L1: 4 · L2: 6 · L3: 18 · L4: 0 (32 planned rows;
each L1/L2/L3 family expands to several concrete cases at implementation).**

---

## Section 5 — Existing-test audit

Author-written suite: `packages/qmf-structure/tests/test_ct17_*.py` (12 modules,
listed by name only — no body read before Section 4). For every requirement in
Section 2, the lane names the covering module and classifies it **keep** /
**suspect** / **contradicts**; every "contradicts" row goes to `findings.csv`
with the requirement id (this is where R-003 gets its evidence).

| Existing test module | Requirements it claims | Audit focus (classify per requirement) |
| -------------------- | ---------------------- | -------------------------------------- |
| `test_ct17_objects.py` | Story 9.1 (mint, emission invariant) | **High suspicion (family h).** Confirm the emission invariant is asserted as the *full* ordering chain **and** `observed-at ≥ max input evidence time` over an *adversarial* future-leak input, not only a happy in-order mint. Suspect if the illegal case is a single hand-picked violation. |
| `test_ct17_lifecycle.py` | Story 9.2 (append-only, fold, refit) | **Highest suspicion.** Confirm "still valid at T" is asserted as a fold over the edge stream (not a stored flag the test reads back), that overwrite is *refused*, and that a refit mints a new artifact keeping the first observed-at. |
| `test_ct17_provenance.py` | Story 9.3 (evidence class, result label, confirmed-read) | Confirm the confirmed-read *refuses* (policy-rejection) rather than filtering; confirm the revised-input relabel and the label field-set. |
| `test_ct17_splits.py` *(module inferred from `splits.py`; confirm presence)* | Story 9.3 (split embargo, FM-7) | Confirm the observed-before/confirmed-after boundary refusal is asserted against an embargo that does *not* cover the gap; confirm the unbounded-declaration exclusion. If no split test module exists, that is a coverage finding. |
| `test_ct17_families.py` | Story 9.2/9.4 (admissibility, seed family, no privilege) | Confirm an *imprecise* confirmation rule is refused admission (FM-2) and that the seed family holds no privilege; grep for any school name (FM-9). |
| `test_ct17_composites.py` | CT-17 composites | Confirm the max-rule for confirmed-at/observed-at and order-significance default. |
| `test_ct17_routing.py` | Story 9.4 (FM-6) | Confirm CT-16-vs-CT-17 routing and indicator-as-declared-input (never inline). |
| `test_ct17_geometry.py` | CT-17 geometry / sloped anchors | Confirm exact-Price anchors and slope-derived-never-stored. |
| `test_ct17_budget.py` | Story 9.4 (FM-8) | Confirm a light claim over bound / missing baseline / peak-memory regression is refused at the gate. |
| `test_ct17_research.py` | Story 9.4 (L33) | Confirm the ungoverned-lane / extension-graduation path. |
| `test_ct17_conformance.py` | Story 9.4 conformance register | Confirm the concept-walk list stays expressible; suspect if it asserts only a subset. |
| `test_ct17_objects_examples.py`, `test_structure.py` | reference usage / cross-cutting | Classify per assertion; `examples` doubles as the L27 artifact. |

R-002/no-raise (L1-002) and the future-leak universal (L1-001) are **net-new
independent** claims the per-behaviour author tests structurally cannot make;
they are written regardless of the audit outcome.

---

## Section 6 — Mutation targets (`mutmut` roster; execution deferred at T3)

Inclusion rule: a surviving mutant here would leave a causality or governance
claim unasserted. **T3 note:** the roster is *named* here; mutation *execution*
is deferred (Section 7) — the RESULTS pass runs it only if time permits after
L0-L3 and L6 are green.

| Module | Justification |
| ------ | ------------- |
| `objects.py` | The emission invariant (ordering + `observed-at ≥ max input evidence time`) is the causality core; a survivor means a future-leak object mints unrefused. |
| `lifecycle.py` | The append-only fold, the overwrite prohibition, and the refit-mints-new-artifact logic; a survivor means state is overwritten or a fold silently reads a stored flag. |
| `provenance.py` | The confirmed-read policy-rejection and the revised-input relabel; a survivor means an unconfirmed row leaks into a confirmed read or a revision changes silently. |
| `splits.py` | The observed-before/confirmed-after embargo refusal; a survivor means a record leaks across a split boundary. |
| `families.py` | The admissibility bar (imprecise rule refused) and no-privilege law; a survivor means an imprecise family enters governed evidence. |
| `routing.py` | The CT-16-vs-CT-17 decision and indicator-as-declared-input; a survivor means an indicator is re-implemented inline. |

**Excluded** (the rule excludes reports/formatting/scaffolding): `_bench.py`,
`conformance.py` harness scaffolding, and pure geometry/rendering helpers.

---

## Section 7 — Deferred and out of scope

| Item | Disposition | Reference |
| ---- | ----------- | --------- |
| Full look-ahead / causality **registration gate** (CT-08) | **DEFERRED** to the backtesting sitting (GAP-0016); the in-component emission invariant is the interim guard, *not* that gate. Epic 9 verifies the interim guard only. | CT-17 `gaps: [GAP-0016]`; Story 9.3 AC-5 |
| CT-16 **indicator internals** (value-per-instant computation) | **OUT OF SCOPE — Epic 7.** Epic 9 tests only the CT-17 *routing decision* and that an indicator is consumed as a declared input via the composition law, never CT-16 behaviour itself. | epics.md Epic 7; CT-16; EPIC-BINDING RULE |
| CT-12 **split-manifest mechanism** (train/val/test partitioning, seal) | **OUT OF SCOPE — Epic 3.** Epic 9 owns only the confirmation-delay-bound → purge/embargo *contribution* and the observed-before/confirmed-after *refusal predicate*; the manifest/seal machinery is CT-12. | epics.md Epic 3; SCN-0003; CT-12 |
| CT-07 **lineage-edge persistence** (`supersedes`, `confirmed-as`, `corroborates`) | **OUT OF SCOPE — Epic 2.** Epic 9 tests that a refit *mints* a new artifact *with* a supersedes edge and that an unconfirmed output *declares* a confirmed-as edge; the edge-store persistence is CT-07. | epics.md Epic 2; CT-07 |
| Composition-root **WriterId / gapless per-(writer,kind) sequence**, journal-event **cardinality** | **OUT OF SCOPE — Epic 1/2 (writer/sequence) and Epic 3 (CT-13 journal).** Epic 9 tests only that the library returns fingerprintable content and *never stamps*, and that a cited object *becomes governed and is persisted*. | CT-05/CT-09/CT-13; Story 9.1 AC-3 / 9.3 AC-5 |
| `result_identity_key` **mechanism** (the AD-12 label as an identity) | **OUT OF SCOPE — Epic 1.** Epic 9 tests only the CT-17-declared *contents* (evidence class present, revised-input relabel), not the label's identity machinery. | `registry:result_identity_key`; DEC-0110 |
| **Measured benchmark budgets** (concrete rung numbers) | **DEFERRED (measure-then-budget).** Only the *negative* is asserted — a light claim over a declared bound / lacking a baseline / a peak-memory regression is refused; **no number is invented.** | CT-17 benchmark clause; FM-8 |
| **L4 cross-package scenario** | **NOT OWNED / DEFERRED.** No CT-17 golden scenario exists; the constructed future-leak journey is carried at L3-001. If a structure scenario is later authored it becomes an L4 target. | `docs/scenarios/` (none for CT-17) |
| **L5 mutation execution** | **DEFERRED at T3.** Roster named (Section 6); executed only if L0-L3 + L6 land green with budget to spare. | Lane brief (T3 = L3 for P0/P1 ACs; L6 review) |
| **The absent test-artifact authorities** | **RECORDED, not remediated.** test-design-qa.md and QMX-handoff.md are absent; their risk-gate rows and the 15-assertion cross-reference cannot be consumed. See F-E09-001. | Section 1; Section 8 |

---

## Section 8 — Findings (authored while writing this plan; **no fixes**)

Appended to `qa/epics/epic_09_qmf-structure/findings.csv`. Reproducers are
directory / documentary — no `src/` body was read.

| Finding ID | Requirement | Severity | Reproducer | Description |
| ---------- | ----------- | -------- | ---------- | ----------- |
| F-E09-001 | Process / traceability | Medium | `ls _bmad-output/test-artifacts/` → **No such directory** | The two test-artifact authorities named in the lane brief (`test-design-qa.md`, `test-design/QMX-handoff.md`) are **absent from this worktree snapshot**. Consequence: the epic's handoff risk-gate rows, ranked evidence baseline, and the 15 P0/P1 assertion cross-reference could not be cited; this plan is grounded on the surviving primary oracles (epics.md, CT-17, constitution, registry). Recorded, not remediated. |
| F-E09-002 | FR-020, CT-17 | Info (testability) | CT-17 `consumers: []`; "evidence flowing through the composition root" | CT-17 is deliberately consumer-blind (no in-tree caller drives structure evidence into governed storage; wiring is composition-root-mediated). Consequence for verification: every L2/L3 test must inject a fake composition root / writer and fake input observations to drive the lifecycle — a testability note that shapes the suite, not a defect. |
| F-E09-003 | Story 9.3 AC-3 vs CT-12 | Info (boundary) | Story 9.3 AC-3 references split manifests, owned by CT-12/Epic 3 | The FM-7 split-embargo AC straddles the Epic 9 / Epic 3 boundary. Epic 9 owns only the confirmation-delay-bound contribution and the observed-before/confirmed-after refusal *predicate*; if the predicate is implemented inside `splits.py` here (rather than consumed from qmf-data), that is a placement question to confirm in RESULTS, not a defect prejudged now. |
| F-E09-004 | R-003, Story 9.2 | Info (to confirm in §5) | `test_ct17_lifecycle.py` / `test_ct17_objects.py` present; fold + emission invariant are line-coverage-satisfiable | High prior that the author suite pins the code's fold and a single hand-picked emission-invariant violation rather than the contract's full ordering law over an adversarial future-leak input. Elevated to a confirmed finding only if the Section 5 audit yields a "contradicts" or "suspect" row. |

**Lane completion criterion (template):** all eight sections present; every
Section 4 test (L0-L3) exists and has run (pass or fail); Section 5 covers every
Section 2 requirement; the L6 requirements-fidelity seat has reviewed the lane;
every finding is in `findings.csv`.
