# Verification PLAN — Epic 7: qmf-indicators (two-mode indicators, TA-Lib canonical)

**Audit tier:** **T3** (lighter than T2 — the deliverable is **L3 acceptance tests for the P0/P1 ACs**, one **L6** adversarial requirements-fidelity review, one **L4** composition-law participation, and one regression pin per *confirmed* advisory finding. A **lean** L0 static / L1 property / L2 contract band is built only where it carries a law L3 cannot reach — no exhaustive property or branch suites.)
**Package under test:** `packages/qmf-indicators/` (import root `qmf.indicators`, src/ layout `src/qmf/indicators/`). Module **names** observed by directory listing only — `arithmetic.py`, `batch.py`, `benchmark.py`, `budget.py`, `catalog.py`, `comparison.py`, `configured_indicator.py`, `conformance.py`, `series.py`, `streaming.py`, `wrappers.py`, `_reference.py`, `_bench.py`, `__init__.py` — **no source file was read before §4 was authored.**
**Delivers:** **FR-019** — batch and streaming indicators with guaranteed equivalence over TA-Lib canonical arithmetic, as-of-only alignment, a conformance harness, and a first wrapper set. (**CT-16**; **AR-49**; ADR-0006.)
**Governing invariants:** **CT-16** (two-mode indicator contract), **CT-05** (fp1 / result-label identity — *consumed*, qmf-core-owned), **CT-04** (typed refusal — *consumed*, qmf-core-owned), **AR-49** (TA-Lib pin + wrap-not-reimplement), **AR-06** (default-deny: qmf-indicators imports only qmf-core), **DEC-0126/0127/0128/0130/0133/0134**, and the `COMP-QMF-INDICATORS` component spec.

> **PROCESS GAP (read first).** Two authorities named in the audit brief **do not exist in this worktree**: `_bmad-output/test-artifacts/test-design-qa.md` (the Per-Epic Test Plan Template + the L0–L6 test-level architecture) and `_bmad-output/test-artifacts/test-design/QMX-handoff.md` (the 15 P0/P1 assertions + this epic's risk-gate rows). Confirmed absent by full-tree search; `_bmad-output/test-artifacts/` does not exist — only `planning-artifacts/`. Sibling plans (`epic_06`, `epic_19`, `epic_22`) record the same gap.
> **Consequence:** the 8-section structure, the L0–L6 taxonomy in §5, the "one behaviour, one level; lower level wins" rule, the T3 tier scope (**L3 for P0/P1 ACs; L6 review**), and this epic's risk-gate framing are **reconstructed** from the ratified corpus (epics.md §Epic 7; `docs/contracts/ct-16-indicator.yaml`; `docs/components/qmf-indicators.md`; CT-04/CT-05; `docs/registry/variables.yaml`; the constitution) and the **level scheme + epic-specific priorities the task brief supplies**. When the two files are restored, treat them as authoritative and reconcile §1 template order, §4 assertion set, and §5 level definitions against them before executing.

---

## Section 1 — Epic Context, Scope & Authorities

**What this epic is.** `qmf-indicators` is a **pure-computation** library that defines and owns **one CT-16 contract with two conformant modes** — **batch** over a whole series and **streaming** over incremental updates — engineered so *research and the live path compute the same numbers by construction*. A configured indicator's identity **is the entire declared configuration** (an `fp1` fingerprint computed by qmf-core's single fingerprint function); its arithmetic is **TA-Lib 0.7.1 wrapped, never re-implemented**, pinned as lockfile-resolved artifact hashes with an **identity-bearing reference-configuration record asserted at import**; its outputs are **full-length, index-aligned, presence-mapped** under **as-of-only** alignment; and every governed input is a series **defined by its BarSpec** (the discriminated aggregation rule that **bans the bare word "timeframe"**). The package imports **only qmf-core** (default-deny), holds no external resource, spawns no threads, and returns immutable values or **CT-04 typed refusals**.

**The centre of gravity (epic-specific).** Three laws are the reason this epic exists and are this audit's spine — they are the task brief's epic-specific priorities:
1. **Canonical arithmetic is *provably* the arithmetic used.** TA-Lib is pinned by artifact hash + a reference-configuration record; the package **refuses at import** if the resolved artifacts or the reference's process-global configuration drift from the record — "the fingerprint must never attest arithmetic that was not used" (FM-2). Wrapping is mandatory where TA-Lib implements a formula; re-implementing is a contract defect (FM-5).
2. **Derived-series / configuration identity.** `fp1` spans the **entire** declared configuration — *same input + same config ⇒ the same fingerprinted series*; any element differing ⇒ a distinct `fp1`; an element **missing** from the fingerprint is a **contract defect**; a config **outside** the reference record **refuses (import)** or is **identity-distinct (mints a format version)**. A computed series is identified by its result label and **its upstream fingerprint enters downstream identity** (composition law).
3. **BarSpec discipline + honest presence.** No bare "timeframe"; the indicator **receives its BarSpec as data and never derives bar boundaries**; outputs are full-length/index-aligned/presence-mapped with **NaN and sentinels prohibited**; **as-of-only** alignment (forward-fill or interpolation across the evaluation instant is a **policy rejection**); warm-up is an **integer count** with **not-ready** (never a number).

**In scope (Stories 7.1–7.6):**
- **7.1** — package scaffold + the CT-16 configured-indicator identity (`fp1` = the whole configuration; binary-float params refused).
- **7.2** — TA-Lib canonical-arithmetic wrapping; reference-configuration record asserted at import; wrap-not-reimplement; vendor-neutral CT-16 surface.
- **7.3** — batch mode: full-length, index-aligned, presence-mapped outputs; as-of-only alignment; BarSpec-as-data; warm-up not-ready.
- **7.4** — streaming mode; the tier-2 **equality law** (streaming ≡ batch, integer-ULP); versioned snapshot / **restore-equivalence**; cross-tuple restore refusal.
- **7.5** — conformance harness (concept-walk register); light/heavy benchmark budgets; the one named **catalog** surface for explicit extension registration.
- **7.6** — the first wrapper set of TA-Lib-backed configured indicators, each proving equality + warm-up + the canonical-upgrade gate.

**Out of scope (owned elsewhere; boundary only here) — per the EPIC-BINDING RULE:**
- **CT-05 fp1 recipe correctness** (the canonical serializer, the SHA-256 recipe, float-refusal-in-identity) → **Epic 1 (qmf-core)**. Epic 7 asserts only that indicators **use** the single qmf-core function and that identity **spans the whole config** — not the recipe's internal correctness.
- **CT-04 refusal machinery** (the seven-category taxonomy, the try_create factory pattern) → **Epic 1**. Epic 7 asserts only that its CT-16 paths **return** the correctly-categorised refusal.
- **Bar aggregation itself** (source → BarSpec bars, its lineage) → **qmf-data (Epic 3/6)**, a "fingerprinted qmf-data derivation". Epic 7 asserts only that the indicator **receives** its BarSpec as data and never aggregates.
- **CT-16 → CT-17 consumption** (structure families) → **Epic 9 (qmf-structure)**, `intended_consumers`, defined-unwired. Epic 7 tests only the **CT-16 → CT-16 composition law** it owns (§4 T7-SCN).
- **The two named money-path conversion boundaries' arithmetic** (exact↔analytic descale/return) → **qmf-core (Epic 1)**. Epic 7 asserts only that a price-valued output **re-enters the money path via the named boundary** (concept-walk expressibility, T7-A19), never re-implements it.

**Authorities, in precedence order:**
1. **Epic 7 section of `_bmad-output/planning-artifacts/epics.md`** (Stories 7.1–7.6 and their ACs; lines 1438–1605) — the requirement oracle.
2. **`docs/` knowledge base:** `docs/contracts/ct-16-indicator.yaml` (invariants, schema, enums, units, nullability, conformance_register); `docs/components/qmf-indicators.md` (authority boundary; Behavior; Foundation invariants; FM-1..FM-8); `docs/contracts/ct-05-version-fingerprint.yaml` and `docs/contracts/ct-04-typed-refusal.yaml` (consumed); `docs/registry/variables.yaml` keys `canonical_indicator_reference`, `barspec_kinds`, `presence_map_states`, `evidence_classes`, `typed_refusal_codes`; `docs/constitution.md` (L30 default-deny, L33 escape-hatch-graduation, L20 nothing-synthetic-validates-edge, DEC-0007 no product mock data).
3. **`DEPENDENCIES.md`** (TA-Lib C + Python wrapper, BSD-3-Clause, `qmf-indicators`, **0.7.1 + 0.7.1**, DEC-0127) and the committed **`uv.lock`** (the actual artifact hashes — read at execution, never fabricated).
4. *(Missing — see Process Gap)* test-design-qa.md; QMX-handoff.md.

**Two senses of "tier" (do not conflate).** *Audit tier* **T3** = this plan's scrutiny band. *Test tiers* tier-1 / tier-2 = the project's `poe check` / `poe check-integration` execution bands; the CT-16 equality law, restore-equivalence, conformance, and benchmark budgets are all **tier-2** gates by ratified design. §5 maps the L-levels onto these bands.

**Evidence baseline** (from `coverage.json`, a data artifact — **no source logic read**):

| Module | Line cov | Missing branches | Signal |
|---|---|---|---|
| `configured_indicator.py` | 98.8% (393/397) | 3/176 | identity assembly — where a missing-from-fp defect would live |
| `streaming.py` | 99.0% (430/433) | 3/170 | equality-law / feeder-reader / seq-number state machine |
| `batch.py` | 93.9% (318/332) | **15**/142 | presence-map / as-of / warm-up arms |
| `series.py` | 90.9% (186/199) | **12**/76 | presence-map integrity; bulk-form handling |
| `conformance.py` | 93.0% (105/110) | 4/18 | concept-walk register expressibility |
| `_reference.py` | 96.3% (81/84) | 1/24 | import-time reference-config assertion (FM-2) |
| `arithmetic.py` | 98.1% (73/74) | 1/34 | wrap-not-reimplement boundary |
| `catalog.py` | 98.0% (165/169) | 1/78 | explicit-registration / extension-identity |
| `comparison.py` | 100% (79/79) | 0/22 | integer-ULP comparator; upgrade before/after |
| `benchmark.py` | 99.1% (167/168) | 1/52 | two-rung harness |
| `budget.py` | 100% (62/62) | 0/28 | light/heavy verdict |
| `wrappers.py` | 100% (97/97) | 0/40 | first wrapper set |
| `_bench.py` | 81.0% (73/84) | 11/32 | benchmark internals (non-behavioural) |

Line coverage is **high and author-written** — precisely the R-003 hazard (a test can pin the code's fold rather than the contract's law). The equality law, restore-equivalence, presence-map honesty, and the **import-time reference-config refusal** are exactly what line coverage cannot see; §5.2 reconciles the existing suites keep/suspect/contradicts.

**Distribution-unit check** (directory listing only): the package ships **`FAILURES.md`** *and* an **`examples/`** directory (`batch_mode_usage.py`, `streaming_mode_usage.py`, `canonical_reference_usage.py`, `configured_indicator_usage.py`, `configured_wrapper_set_usage.py`, `conformance_and_catalog_usage.py`). **No NFR-11 / L27 distribution-unit gap — no invented finding.**

**Build/advisory-review report:** Epic 7 < 20, so no epic build/advisory-review report exists (stated explicitly per template).

---

## Section 2 — Requirements → Behaviours Traceability

Every row is a testable behaviour extracted from a ratified source and confirmed to belong to **Epic 7's** section of epics.md. "Ref" cites the governing AC / CT-16 invariant / component FM / registry key.

| # | Behaviour (stated as an assertion) | Ref | Story | Prio |
|---|---|---|---|---|
| R1 | A configured-indicator declaration's `fp1` is computed by qmf-core's **single** fingerprint function and identity **spans the entire declared configuration** (formula_id, contract_format_version, exact-rational parameters, ordered named input set, calendar_requirements incl. tzdata version, alignment_policy, missing_value_policy, warm_up, output_schema, supported_modes, arithmetic_reference_configuration). | AC7.1; CT-16 inv.2; CT-05 inv.3 | 7.1 | **P0** |
| R2 | Two configurations differing in **any one** identity element receive **distinct** `fp1`; an equal configuration reproduces the **same** `fp1`; that `fp1` is the **only** dedup key. | AC7.1; CT-16 inv.2 | 7.1 | **P0** |
| R3 | A configuration that **omits a required identity element from the fingerprint** is a **contract defect** and the conformance test **fails**. | AC7.1; CT-16 inv.2 | 7.1 | **P0** |
| R4 | A parameter expressed as a **binary float** is **refused** (`invalid input`) — parameters are exact rationals only (scaled integers or num/den pairs); **no binary float ever appears in parameters or identity**. | AC7.1; CT-16 schema.parameters; CT-05 recipe | 7.1 | **P0** |
| R5 | The package **builds** from `packages/qmf-indicators/` in src/ layout, versions in **roster SemVer lockstep**, its `pyproject.toml` declares **every** dependency, at the Tier-2 isolated-environment gate it **imports only qmf-core** (default-deny, AR-06), and public value types are **frozen dataclasses** / public seams **`typing.Protocol`**. | AC7.1; AR-06; DEC-0096 | 7.1 | P1 |
| R6 | `registry:canonical_indicator_reference` resolves to **TA-Lib C 0.7.1 + Python wrapper 0.7.1** pinned as **lockfile-resolved artifact hashes** (distribution filename + hash) with an **identity-bearing reference-configuration record**. | AC7.2; AR-49; registry | 7.2 | **P0** |
| R7 | At import the package **asserts the reference-configuration record**: if resolved artifacts differ from the lockfile pin, **or** the reference's process-global configuration differs from the record → an **`unavailable dependency` refusal at import** (FM-2). | AC7.2; CT-16 inv.11; FM-2 | 7.2 | **P0** |
| R8 | The package **never mutates** the reference's process-global configuration at runtime. | AC7.2; component "May never" | 7.2 | **P0** |
| R9 | Where TA-Lib **implements** a formula, **wrapping is mandatory and canonical**; a wrapper that **re-implements** it is a **contract defect** and fails conformance (FM-5). | AC7.2; CT-16 inv.11; FM-5 | 7.2 | **P0** |
| R10 | Where the reference **does not** implement a formula (volume-weighted, session-anchored, QMX-original), **this package's implementation is canonical** under the identical upgrade gate. | AC7.2; CT-16 inv.11 | 7.2 | P1 |
| R11 | **No TA-Lib / vendor object** appears in any CT-16 signature or output — the public surface stays **package-neutral**, returning CT-04 refusals without exposing dependency-specific objects (FM-5). | AC7.2; component "May never"; FM-5 | 7.2 | **P0** |
| R12 | Batch outputs are **full-length** and **index-aligned** to the input, **begin-index trimming prohibited**; every position carries a `registry:presence_map_states` value; **NaN and sentinel markers prohibited**. | AC7.3; CT-16 inv.5 | 7.3 | **P0** |
| R13 | The indicator **receives its BarSpec as data** and **never derives bar boundaries itself**; a bar series is well-defined only via its BarSpec; **bare "timeframe" is banned vocabulary**. | AC7.3; CT-16 inv.3/4; registry:barspec_kinds | 7.3 | **P0** |
| R14 | For governed evidence, **only as-of alignment** is permitted; forward-fill or interpolation **across the evaluation instant** → a **`policy rejection` refusal** (FM-1). | AC7.3; CT-16 inv.8; FM-1 | 7.3 | **P0** |
| R15 | A **calendar-closed** position is **`absent_by_schedule`**, never a gap; a **calendar-open** position with no data follows the **declared missing-value policy**, never silent filling. | AC7.3; CT-16 inv.8 | 7.3 | P1 |
| R16 | **Warm-up** is an **integer count** of completed input observations in the input's own sample unit (**never ticks, never a Duration**), **at least the reference's lookback**; during warm-up the output is a **marked not-ready value, never a number**. | AC7.3; CT-16 inv.7 | 7.3 | **P0** |
| R17 | Every output sample carries a **knowable-at instant**; **provisional samples never enter governed evidence**. | AC7.3; CT-16 inv.6 | 7.3 | P1 |
| R18 | A streaming instance is the **one named stateful class** — exactly **one feeder** (one WriterId holder), **unlimited readers** — exposes **`health()`**, and every streaming output carries the **input sequence number** that produced it; instance count scales with **distinct configurations, not consumers**. | AC7.4; CT-16 inv.13; component foundation | 7.4 | P1 |
| R19 | The **equality law** (tier-2): for a both-modes config, **streaming ≡ batch** same-process/same-build under a **per-configuration integer-ULP comparator (default 0)** over canonical inputs = (series, exact parameters, cold initial state), with the seeding rule + leading-undefined-prefix→not_ready mapping declared. | AC7.4; CT-16 inv.9 | 7.4 | **P0** |
| R20 | **Cross-OS or cross-build agreement is never the equality gate** — it is a **separate registered comparison artifact**. | AC7.4; CT-16 inv.9; CT-05 inv.6 | 7.4 | P1 |
| R21 | **Restore-equivalence**: restore-then-N-updates **equals** cold-warm-then-the-same-N-updates; the snapshot is a **versioned serialized contract** scoped to a declared **(OS, arithmetic-reference build)** tuple; a result from restored state carries the **snapshot fingerprint as an input fingerprint**. | AC7.4; CT-16 inv.10 | 7.4 | **P0** |
| R22 | A snapshot restored on a **different (OS, arithmetic-reference build) tuple** → an **`unavailable dependency` refusal** (FM-7). | AC7.4; CT-16 inv.10; FM-7 | 7.4 | **P0** |
| R23 | The **CT-16 conformance suite** at Tier 2 keeps the register's **concept-walk list expressible** (multi-instrument/multi-BarSpec input sets, derived-series chaining, non-time bar kinds, calendar-scoped windows & calendar-anchored sampling, projected outputs under knowable-at, batch-only statistical methods, price-valued outputs re-entering the money path via the named boundary, delta-typed price differences). | AC7.5; CT-16 conformance_register | 7.5 | P1 |
| R24 | The **benchmark harness** records **two rungs** — burst throughput and per-tick latency per accepted input observation at the configured BarSpec, no-op tick path measured **separately** — and a **peak-memory regression fails the Tier-2 gate exactly as a slowdown does**. | AC7.5; CT-16 inv (benchmark); DEC-0111 | 7.5 | P1 |
| R25 | A configuration claiming **light** without a recorded **live-path rung baseline**, or whose benchmark **misses a declared bound**, is **refused at the Tier-2 gate**; every configuration is **heavy by default**; a heavy configuration's **synchronous entry point returns `unsupported capability`** (FM-3, FM-6). | AC7.5; CT-16 inv.12; FM-3/6 | 7.5 | **P0** |
| R26 | Extension discovery is **explicit registration** at the composition root through the **one named catalog surface** — **never ambient scanning** — and the extension's **distribution identity and version are mandatory fields in every artifact** it produces (FM-8). | AC7.5; CT-16 inv.16; FM-8 | 7.5 | P1 |
| R27 | A concept the framework cannot yet articulate is **authorable as plain Python outside governed evidence**, entering governed evidence only by **graduating through the CT-16 extension shape with a lineage edge** to its originating research artifact (L33). | AC7.5; CT-16 inv.16; L33 | 7.5 | P1 |
| R28 | A **fanned-out heavy value consumed past its declared maximum age** is a **`stale evidence` refusal**. | CT-16 inv.12; enums.refusal | 7.5 | P1 |
| R29 | Each wrapper in the first set **wraps a TA-Lib formula where the reference implements it**, is declared in both modes where applicable, with **warm-up at least the reference's lookback**; **no trading-school name** appears in any rule or vocabulary. | AC7.6; CT-16 inv.11/17 | 7.6 | P1 |
| R30 | Each both-modes wrapper **passes the equality law** at the declared integer-ULP tolerance and its **restore-equivalence** test. | AC7.6 | 7.6 | **P0** |
| R31 | Each wrapper ships **executable tests and reference-usage examples as Tier-1 artifacts**. | AC7.6; DEC-0096 | 7.6 | P1 |
| R32 | An **upgrade to the canonical reference that changes output** for identical canonical inputs is **caught by the comparison suite before the upgrade lands**, minting the **per-configured-indicator contract format version** with recorded **before/after evidence** — **never a silent accept and never a protocol-wide bump** (FM-4). | AC7.6; CT-16 inv.11; FM-4 | 7.6 | **P0** |

**P0 set (16):** R1, R2, R3, R4, R6, R7, R8, R9, R11, R12, R13, R14, R16, R19, R21, R22, R25, R30, R32.
*(19 rows — the three gate clusters. Counted as the P0 acceptance target.)*
**P1 set:** R5, R10, R15, R17, R18, R20, R23, R24, R26, R27, R28, R29, R31.

---

## Section 3 — Risk Assessment, Weak Spots & Priority

**Highest-value risk theme.** This library's entire promise is **"the same numbers by construction"** across research and the live path, with an identity that dedups and merges. A defect here is silent and downstream-uncorrectable: it either (a) **attests arithmetic that was not used** (a reference-config/pin drift that import failed to catch), (b) **lets identity drift** (an element missing from `fp1`, a float in identity, streaming≠batch), (c) **fabricates presence** (a NaN, a begin-index trim, a forward-fill across the evaluation instant, a silently-filled gap), or (d) **derives a bar boundary the indicator was never handed** (bare-timeframe leakage). Each corrupts governed evidence while every line-coverage number stays green.

**Three epic-specific gates (the audit's centre of gravity):**

1. **Canonical arithmetic is provably the arithmetic used (R6, R7, R8, R9, R11, R32).** TA-Lib 0.7.1+0.7.1 pinned by artifact hash + a reference-configuration record; **import refuses** on any pin or process-global-config drift; **wrap-not-reimplement**; **no vendor object crosses CT-16**; an output-changing upgrade **mints a format version with before/after**, never silently. *"The fingerprint must never attest arithmetic that was not used."* **P0.**
2. **Configuration / derived-series identity (R1, R2, R3, R4, R19, R21).** `fp1` spans the **entire** declared configuration; **same input + same config ⇒ the same fingerprinted series**; any element differing ⇒ distinct `fp1`; an element **missing from the fingerprint is a contract defect**; **binary-float params refused**; a config **outside** the reference record **refuses or is identity-distinct**; a derived series carries **its upstream fingerprint in downstream identity** and never mints an Instrument. **P0.**
3. **BarSpec discipline + honest presence (R12, R13, R14, R15, R16).** **No bare "timeframe"**; BarSpec **received as data, never derived**; **full-length / index-aligned / presence-mapped** (no NaN, no sentinel, no trim); **as-of-only** (forward-fill / interpolation across the evaluation instant → `policy rejection`); **warm-up integer-count / not-ready**. **P0.**

**Named weak spots** (to confirm against the module inventory at execution — module *names* only known now):

| Locus | Risk implication | Mitigation in this plan |
|---|---|---|
| `_reference.py` / `arithmetic.py` (import-time reference assertion, wrap boundary) | A missing/weak import-time check attests arithmetic that was not used; a re-implementation silently diverges from canonical. | §4 gate-1: T7-A4/A5/A6/A7, S4; C3. |
| `configured_indicator.py` (identity assembly) | An identity element left out of `fp1`; a display-only field folded into identity; a binary float on the parameter path. | §4 gate-2: T7-A1/A2, U1/U2; C1. |
| `batch.py` / `series.py` (presence map, as-of, warm-up) | A begin-index trim, a NaN/sentinel, a forward-fill across the evaluation instant, a silent gap-fill, a float warm-up. | §4 gate-3: T7-A8/A9/A10/A11/A12, U3/U4; C3. |
| `streaming.py` / `comparison.py` (equality law, snapshot/restore) | Streaming ≠ batch beyond the declared ULP; restore-then-N ≠ cold-warm-then-N; a cross-tuple restore silently accepted. | §4: T7-A13/A14/A15/A16; C4; T7-SCN. |
| `budget.py` / `benchmark.py` / `catalog.py` (light/heavy, benchmark, extension) | A light claim accepted without a baseline; a heavy synchronous entry that does not refuse; an extension discovered by scanning or missing identity. | §4: T7-A17/A18/A19/A20/A21. |
| `wrappers.py` (first set) | A wrapper that re-implements; a school name in vocabulary; an upgrade that changes output silently. | §4: T7-A22/A23/A24; S3. |

**Priority ladder:** P0 blocks the epic on any failure; P1 is high (evidence honesty); the L6 review is advisory (its confirmed findings become regression pins).

---

## Section 4 — Independent Test List (authored from requirements, BEFORE any src read)

> **Discipline statement.** This section was written having read **zero source files** under `packages/qmf-indicators/src/` — only the directory's file *names* (a listing, not a read) and `coverage.json` (a data artifact) are known. Every test below asserts what a **requirement** demands, derived from epics.md §Epic 7, CT-16, CT-05, CT-04, the component spec, and the registry — **never** what the code happens to do. A failing test here is a **finding recorded in `qa/epics/epic_07_qmf-indicators/findings.csv`**, **never** a licence to edit source or weaken the assertion. Test files are planned targets under `qa/tests/epic_07/`. Level assignment follows "one behaviour, one level; the lowest level that meaningfully asserts it wins" (§5). Every refusal assertion checks a **returned** CT-04 value's `category` + machine-readable context — never a parsed exception string.
>
> **Epic-binding applied.** CT-05 recipe correctness, CT-04 machinery, bar aggregation, and CT-16→CT-17 consumption are owned elsewhere (§1); rows touching them assert only **Epic 7's producer/consumer obligation** and are tagged accordingly. **T3 scope:** L3 acceptance carries the epic; L0/L1/L2 are deliberately lean; one L4 composition participation; one L6 review; regression pins reserved.

### Group S — Static / structural gates (L0)
- **T7-S1** *(L0)* **Default-deny import.** The import graph of `qmf.indicators` reaches only `qmf.core` plus the package's own declared third-party pins (TA-Lib / numpy); **no sibling `qmf.*` package** is imported. **[R5, AR-06]**
- **T7-S2** *(L0)* **No bare "timeframe".** A static scan of the public surface/vocabulary finds **no `timeframe` token used as a series/aggregation discriminant** — `BarSpec` (registry:barspec_kinds) is the only aggregation vocabulary. **[R13 — vocabulary half]**
- **T7-S3** *(L0)* **No trading-school name** appears in any public rule, vocabulary, or exported identifier (scan against a fixed school-name lexicon). **[R29 — school-name half]**
- **T7-S4** *(L0)* **Vendor-neutral surface.** A static scan of exported CT-16 signatures and public dataclass fields finds **no `talib` / TA-Lib / vendor type** in any signature or output field. **[R11 — structural half]**
- **T7-S5** *(L0)* **Pure-computation foundation.** No `asyncio` / `threading` / background-work surface and **no module-global mutable instance registry** (dedup is per-process, application-owned); pure batch functions expose no `health()` (only the streaming stateful class does). **[component Foundation invariants; R18 boundary]**

### Group U — Minimal unit laws (L1) — only where L3 cannot reach the law
- **T7-U1** *(L1)* A parameter expressed as a **binary float** is **refused** (`invalid input`); a scaled-integer / numerator-denominator rational is accepted; **no float appears in parameters or identity content** for any generated parameter. **[R4]**
- **T7-U2** *(L1)* **`fp1` spans the whole configuration.** For a generated configuration, mutating **any one** identity element (formula_id, format version, a parameter, an input-set member incl. its BarSpec/quote-side/upstream fp, a calendar/tzdata version, alignment/missing policy, warm-up, output schema, supported modes, arithmetic-reference config) **changes `fp1`**; mutating a display-only field does **not**; a byte-identical configuration yields the **identical** `fp1`. **[R1, R2]** *(uses qmf-core's fp1 as an oracle; CT-05 recipe is Epic-1-owned.)*
- **T7-U3** *(L1)* **Presence-map integrity.** For a generated batch output: `len(output) == len(input)` (no begin-index trim), **every** position carries a `presence_map_states` value ∈ {present, provisional, not_ready, gap, absent_by_schedule}, and **no NaN / sentinel** appears in the value channel. **[R12]**
- **T7-U4** *(L1)* **Warm-up discipline.** `warm_up` is an **integer count** (never a Duration/tick), **≥ the reference lookback**, and every position inside the warm-up window is a **marked not_ready value, never a number**. **[R16]**

### Group C — Contract adoption & refusal shape (L2)
- **T7-C1** *(L2)* The configured-indicator declaration is a **valid CT-16 record** with **all identity-bearing fields present** (formula_id, contract_format_version, parameters, inputs, calendar_requirements, alignment_policy, missing_value_policy, warm_up, output_schema, supported_modes, arithmetic_reference_configuration); a declaration **omitting any required identity element from the fingerprint** is a **contract defect** the conformance test rejects. **[R1, R3]**
- **T7-C2** *(L2)* **Refusals are returned, never raised.** Every CT-16 public boundary returns **value-or-CT-04-refusal**; a refusal is a valid CT-04 (category ∈ the seven; machine-readable context present; retryability answered) **RETURNED**; and **`correlation_id` does not cross** the pure value signature. **[cross-cutting; CT-04; CT-16 inv.18]**
- **T7-C3** *(L2)* **Refusal-category mapping** at the CT-16-declared paths is exhaustive and correct: forward-fill/interp across the evaluation instant → **policy rejection**; heavy synchronous entry → **unsupported capability**; reference-config/tzdata mismatch at import **and** cross-tuple restore → **unavailable dependency**; fanned-out heavy value past max age → **stale evidence**; malformed config / binary-float param → **invalid input**. **[R14, R25, R7, R22, R28, R4]**
- **T7-C4** *(L2)* **The equality law is a declared contract test.** For a both-modes config, **streaming ≡ batch** under the per-configuration **integer-ULP comparator (default 0)** over canonical inputs (series, exact params, cold state), with the seeding rule + leading-undefined-prefix→not_ready mapping **declared contract surface**. **[R19]** *(contract-level; the shipped-wrapper acceptance instance is T7-A13/A22.)*

### Group A — Acceptance (the T3 core; L3) — one per P0/P1 AC

*Story 7.1 — identity*
- **T7-A1** *(L3)* Given a configured-indicator declaration, its `fp1` is computed by **qmf-core's single fingerprint function**, identity **spans the entire declared configuration**, two declarations differing in exactly one element receive **distinct** `fp1`, an equal declaration reproduces the **same** `fp1`, and `fp1` is the **only** dedup key. **[R1, R2] P0**
- **T7-A2** *(L3)* A declaration that **omits a required identity element from the fingerprint** is caught by the conformance test as a **contract defect** (the test fails, not silently passes). **[R3] P0**
- **T7-A3** *(L3)* The package builds in src/ layout under the `qmf.*` namespace, versions in **SemVer lockstep**, `pyproject.toml` declares **every** dependency, at the Tier-2 isolated-environment gate **imports only qmf-core**, and public value types are **frozen dataclasses** / seams **`typing.Protocol`**. **[R5] P1**

*Story 7.2 — canonical reference*
- **T7-A4** *(L3)* `registry:canonical_indicator_reference` resolves to **TA-Lib C 0.7.1 + wrapper 0.7.1** pinned as **lockfile-resolved artifact hashes** (distribution filename + hash) with an **identity-bearing reference-configuration record**. **[R6] P0** *(the concrete hash is read from `uv.lock` at execution, never fabricated.)*
- **T7-A5** *(L3)* At import the package **asserts the reference-configuration record**: a resolved artifact differing from the lockfile pin, **or** a process-global reference configuration differing from the record, returns an **`unavailable dependency` refusal at import**; and the package **never mutates** the reference's process-global configuration at runtime. **[R7, R8] P0** — *gate-1 anchor.*
- **T7-A6** *(L3)* Where TA-Lib **implements** a formula the wrapper **wraps the reference** (canonical) and a wrapper that **re-implements** it **fails conformance**; where the reference **lacks** the formula, the **QMX implementation is canonical** under the identical upgrade gate. **[R9, R10] P0**
- **T7-A7** *(L3)* **No TA-Lib / vendor object crosses any CT-16 boundary**: over a computed result **and** every refusal path, the public surface is package-neutral (a returned CT-04, never a vendor exception or object). **[R11] P0**

*Story 7.3 — batch*
- **T7-A8** *(L3)* A batch configuration over an input series produces **full-length, index-aligned** output with **begin-index trimming prohibited**; every position carries a `presence_map_states` value; **no NaN / sentinel**. **[R12] P0**
- **T7-A9** *(L3)* The indicator **receives its BarSpec as data** and **never derives bar boundaries itself**; the same values under a different BarSpec are a **different configured identity**; no bar-boundary computation exists in the indicator path. **[R13] P0**
- **T7-A10** *(L3)* For governed evidence, **only as-of alignment** is permitted; a forward-fill or interpolation **across the evaluation instant** returns a **`policy rejection` refusal**. **[R14] P0**
- **T7-A11** *(L3)* A **market-hours-closed** position is **`absent_by_schedule`** (never a gap); a **calendar-open** position with no data follows the **declared missing-value policy**, never silent filling. **[R15] P1**
- **T7-A12** *(L3)* **Warm-up** is an **integer count** of completed input observations **≥ the reference lookback**; during warm-up the output is a **marked not_ready value, never a number**; every sample carries a **knowable-at instant**; **provisional samples never enter governed evidence**. **[R16, R17] P0**

*Story 7.4 — streaming + equality*
- **T7-A13** *(L3)* A both-modes configuration satisfies the **equality law**: streaming ≡ batch same-process/same-build under the declared **per-configuration integer-ULP comparator (default 0)** over canonical cold-state inputs. **[R19] P0** — *gate-2 anchor.*
- **T7-A14** *(L3)* **Restore-equivalence**: restore-then-N-updates **==** cold-warm-then-the-same-N-updates; the snapshot is a **versioned serialized contract** scoped to a declared **(OS, arithmetic-reference build)** tuple; a result from restored state carries the **snapshot fingerprint as an input fingerprint**. **[R21] P0**
- **T7-A15** *(L3)* A snapshot restored on a **different (OS, arithmetic-reference build) tuple** returns an **`unavailable dependency` refusal**. **[R22] P0**
- **T7-A16** *(L3)* A streaming instance is the **one named stateful class** — **one feeder** (one WriterId holder), **unlimited readers** — exposes **`health()`**, stamps each output with its **producing input sequence number**, and instance count scales with **distinct configurations, not consumers**. **[R18] P1**

*Story 7.5 — conformance / benchmark / catalog*
- **T7-A17** *(L3)* A configuration claiming **light** without a recorded **live-path rung baseline**, or whose benchmark **misses a declared bound**, is **refused at the Tier-2 gate**; every configuration is **heavy by default**; a heavy configuration's **synchronous entry point returns `unsupported capability`**. **[R25] P0**
- **T7-A18** *(L3)* The **benchmark harness** records the **two rungs** (burst throughput; per-tick latency per accepted input observation at the configured BarSpec; no-op path measured separately) and a **peak-memory regression fails the Tier-2 gate exactly as a slowdown does**. **[R24] P1**
- **T7-A19** *(L3)* The **CT-16 conformance suite** keeps the register's **concept-walk list expressible** (the eight named concepts, incl. **price-valued outputs re-entering the money path via the named boundary** and **delta-typed price differences**). **[R23] P1** *(the money-path boundary arithmetic itself is Epic-1-owned; asserted as expressibility only.)*
- **T7-A20** *(L3)* Extension discovery is **explicit registration** through the **one named catalog surface** (never ambient scanning); an extension's **distribution identity and version are mandatory fields** in every artifact it produces; a scanned or identity-less extension is **non-conformant**. **[R26] P1**
- **T7-A21** *(L3)* A concept not yet articulable is **authorable as plain Python outside governed evidence** and enters governed evidence **only** by graduating through the **CT-16 extension shape with a lineage edge** to its originating research artifact. **[R27] P1**

*Story 7.6 — first wrapper set*
- **T7-A22** *(L3)* Each wrapper in the first set **wraps a TA-Lib formula where the reference implements it**, declares both modes where applicable with **warm-up ≥ the reference lookback**, and **passes both the equality law** (declared integer-ULP tolerance) **and its restore-equivalence** test. **[R29, R30] P0** *(concrete instance of A13/A14 on the shipped set.)*
- **T7-A23** *(L3)* Each wrapper ships **executable tests and reference-usage examples as Tier-1 artifacts**. **[R31] P1**
- **T7-A24** *(L3)* An **upgrade to the canonical reference that changes output** for identical canonical inputs is **caught by the comparison suite before the upgrade lands**, minting the **per-configured-indicator contract format version** with recorded **before/after evidence** — **never a silent accept, never a protocol-wide bump**. **[R32] P0**

### Group SCN — Composition-law participation (L4) — light, T3
- **T7-SCN** *(L4)* **CT-16 → CT-16 derived-series chain.** A CT-16 output series fed as a CT-16 **input** to a second configuration produces a derived series whose identity **carries the upstream artifact's fingerprint** (derived-series identity) and **never mints an Instrument**; driven end-to-end over **both** the batch and streaming paths (injected qmf-core value types; the arithmetic reference asserted at the seam), the **two-hop batch result equals the two-hop streaming result** under the equality law. **[composition law; R2 derived-series identity; R19]** *The CT-16 → CT-17 hop (structure families) is Epic 9's and out of scope (epic-binding).*

### Group R — Adversarial review (L6) + regression pins
- **T7-REV** *(L6)* Run **`bmad-code-review`** over `packages/qmf-indicators/src/qmf/indicators/` against Epic 7 ACs + CT-16 invariants + the **three load-bearing gates** — (1) canonical pin / import-refusal / wrap-not-reimplement / vendor-neutral; (2) full-config & derived-series identity; (3) BarSpec-as-data / as-of-only / presence honesty. One question per behaviour: *does the code assert what the requirement demands, or what the implementation happens to do?* Advisory findings recorded in `findings.csv`.
- **T7-PIN-\*** *(reserved)* **One regression pin per *confirmed* advisory finding** (from T7-REV) or per failing acceptance test — a minimal test locking the corrected behaviour. **Zero at authoring; populated at execution.**

**Planned counts — L0: 5 · L1: 4 · L2: 4 · L3: 24 · L4: 1 · L6: 1 review (+ N pins).** Executable total **38 tests + 1 review + N regression pins** (N = confirmed advisory findings, 0 at authoring). Each L2/L3 family expands to several parametrized cases at implementation (per identity-element, per refusal-category, per shipped wrapper).

---

## Section 5 — Test-Level Architecture Mapping (L0–L6)

> Reconstructed taxonomy (test-design-qa.md absent), using the **level scheme the T3 brief supplies**: L3 acceptance carries the epic; L4 is the composition participation; L6 is the adversarial review. Rule enforced: **one behaviour, one level; the lowest level that meaningfully asserts it wins.**

### 5.1 Level table

| Level | Meaning here | Execution band | Epic-7 population | Count |
|---|---|---|---|---|
| **L0** | Static / structural gates (default-deny import, no-bare-timeframe, no-school-name, vendor-neutral surface, pure-computation). | tier-1 lint/type | T7-S1..S5 | **5** |
| **L1** | Minimal pure-unit laws not reachable at L3 (binary-float refusal, full-config `fp1`, presence-map integrity, warm-up). | tier-1 (`poe check`) | T7-U1..U4 | **4** |
| **L2** | Contract adoption + refusal shape (valid CT-16 record + missing-element defect; returned-not-raised; refusal-category map; equality-law contract). | tier-2 (`poe check-integration`) | T7-C1..C4 | **4** |
| **L3** | **Acceptance — the T3 core**: one test per P0/P1 AC across Stories 7.1–7.6. | tier-2 | T7-A1..A24 | **24** |
| **L4** | Composition-law participation — CT-16 → CT-16 derived-series chain over both modes. | tier-2 | T7-SCN | **1** |
| **L6** | Adversarial review (`bmad-code-review`) + reserved regression pins. | review | T7-REV (+ T7-PIN-\*) | **1** (+N) |

**Planned counts — L0: 5 · L1: 4 · L2: 4 · L3: 24 · L4: 1 · L6: 1 review.** Executable total **38 tests + 1 review + N pins**.

**Lower-level-wins applications:**
- The **full-config identity** law is quantified once at **L1 (U2)** and asserted behaviourally once at **L3 (A1)** — two facets (property over all elements vs. the acceptance narrative), not a duplication.
- **No bare timeframe** is caught **statically (S2)**; the BarSpec-as-data *behaviour* (never derives boundaries; different BarSpec = different identity) is a distinct **L3 (A9)** assertion.
- **Vendor-neutral surface** is a **static (S4)** scan of signatures plus one **behavioural (A7)** assertion that a refusal path returns a CT-04, not a vendor object — the negative is proven both structurally and behaviourally because it is a gate.
- The **equality law** sits at **L2 (C4, the declared contract)** and is instanced at **L3 (A13, A22)** on real/shipped configs; it also **participates** in **L4 (T7-SCN)** over a two-hop chain — asserted once per level, not re-run.
- **Refusal-category** correctness is one **L2 (C3)** mapping test; each acceptance test that expects a refusal (A5, A10, A15, A17) checks its *own* category inline rather than re-deriving the map.

### 5.2 Existing-test reconciliation (R-003 — audit, do not trust)

The author-written suites produced the §1 high coverage. **No source body was read to author §4; this reconciliation is the read that happens at execution.** For every P0/P1 behaviour, name the covering suite and classify **keep / suspect / contradicts**; every "contradicts" goes to `findings.csv` with the requirement id.

| Existing suite (by name) | Behaviours it claims | Audit focus (classify per behaviour) |
|---|---|---|
| `test_ct16_configured_indicator.py` | R1–R4 (identity) | Confirm it asserts **`fp1` = the whole config** (every element mutation ⇒ new fp1) and the **missing-element-is-a-defect** law, not just a happy round-trip. **Suspect** if the element set is hand-picked. |
| `test_canonical_reference.py` | R6, R7, R8 (pin + import assert) | **Highest suspicion (gate-1).** Confirm the **import-time refusal** fires on **both** a pin drift **and** a process-global-config drift, and that runtime never mutates the reference config — not merely that a happy import succeeds. |
| `test_arithmetic_wrapping.py` | R9, R10, R11 (wrap-not-reimplement, neutral) | Confirm **re-implementation fails conformance** and **no vendor object** crosses CT-16 on a **refusal** path (not only on success). |
| `test_batch_mode.py` | R12–R17 (presence, as-of, warm-up) | Confirm **begin-index-trim / NaN / sentinel** are rejected, **forward-fill across the eval instant** returns `policy rejection`, and warm-up yields **not_ready**, not a number. `batch.py`/`series.py` carry the most missing branches — the refusal/presence arms are the branch-coverage blind spot. |
| `test_streaming_mode.py` | R18, R19, R21, R22 (equality, restore) | **High suspicion (gate-2).** Confirm the equality law is asserted with the **declared ULP comparator over cold state** and restore-equivalence + **cross-tuple refusal**, not a single hand-run stream. |
| `test_comparison.py` | R19, R20, R32 (comparator, upgrade gate) | Confirm the **integer-ULP** comparator and the **upgrade-mints-a-format-version-with-before/after** law (never silent, never protocol-wide). |
| `test_budget.py` / `test_benchmark.py` | R24, R25, R28 (light/heavy) | Confirm **light-without-baseline is refused** and **heavy synchronous entry → unsupported capability**, not only that a light claim can succeed. |
| `test_catalog.py` | R26, R27 (explicit registration) | Confirm **scanning is rejected** and extension **identity fields are mandatory**. |
| `test_wrappers.py` / `test_conformance.py` | R23, R29–R32 (first set, conformance) | Confirm each wrapper **passes equality + restore** and **no school name**; confirm the **concept-walk register stays expressible**. |
| `test_indicators.py` + `test_*_examples.py` | cross-cutting / examples | Classify per assertion; confirm the example suites assert the **public contract**, not internal shape. |

R-003 conclusion is data-driven: any behaviour whose only cover is an existing test classified **suspect/contradicts** is (re)asserted net-new at the level above.

---

## Section 6 — Fixtures, Data & Determinism Strategy

**Runner.** `uv run pytest qa/tests/epic_07 -q` from the worktree root (dev group synced); tier-2 gates (equality law, restore, conformance, benchmark) via `poe check-integration`. If `hypothesis` is used for U1/U2/U3, `uv run --with hypothesis ...`. **All tests live under `qa/`; source is read-only evidence.** A failing test is a **finding in `qa/epics/epic_07_qmf-indicators/findings.csv`**, never a reason to edit `src/` or soften an assertion.

**Fixtures (controlled test fixtures under L6/DEC-0007; no product mock data, no default strategies):**
- **A minimal input-series fixture** — a small, deterministic input series (values + presence map + BarSpec + calendar identity + tzdata version) supplied *as data* to the indicator (the application aggregates bars; the indicator never does). Checked into `qa/`, never sourced from a provider (L20/B-11).
- **A canonical both-modes configuration** — exact-rational parameters, an ordered named input set, warm-up ≥ the reference lookback, both `supported_modes`, the arithmetic-reference-configuration record — sufficient to drive identity (A1/A2), batch (A8–A12), streaming + equality (A13), restore (A14/A15), and the composition chain (T7-SCN).
- **Variants:** a binary-float-parameter config (U1/A-neg); a config with one identity element mutated (U2/A1); a config that omits a required element from the fingerprint (A2); a forward-fill/interp-across-instant request (A10); a calendar-closed vs. calendar-open-no-data window (A11); a heavy config + a light-claim-without-baseline config (A17); a cross-(OS, reference-build)-tuple snapshot (A15); a two-hop derived-series config (T7-SCN); a simulated reference-config/pin drift (A5, injected at the seam).
- **The arithmetic reference is asserted, not mocked away.** The pin (0.7.1 + 0.7.1) and its lockfile hash are read from `DEPENDENCIES.md` + `uv.lock` at execution; A5's drift case is produced by injecting a divergent reference-configuration record **at the seam**, never by fabricating a hash string in the plan.
- **CT-04 / CT-05 / CT-16 fakes are shape-faithful** to the ratified contracts (fields, enums, refusal categories); a test that passes against a shape-unfaithful fake is itself a finding.

**Determinism & discipline strategy:**
1. **Identity is computed once, by qmf-core.** U2 + A1 prove `fp1` comes only from qmf-core's canonical function and spans the whole config; T7-SCN proves the **upstream fingerprint enters downstream identity**; no float byte enters identity (U1).
2. **Same numbers by construction — proven at the ULP gate.** C4 + A13 + A22 assert streaming ≡ batch under the declared integer-ULP comparator over **cold state**; A14 asserts restore-then-N == cold-warm-then-N. **Cross-OS/cross-build agreement is explicitly *not* this gate** (§7) — asserting it would test a value CT-05/CT-16 do not promise.
3. **Numeric correctness is inherited, not invented.** Canonical arithmetic **is** TA-Lib by construction (wrap-not-reimplement, A6); the plan asserts **identity, equality, restore, presence, and refusal structure**, **not** a fabricated golden number for any formula (DEC-0007 forbids product mock data; CT-16 gives no fixture oracle to freeze).
4. **Refusals are RETURNED, not raised.** Every "is refused" assertion (A5, A10, A15, A17, U1, C2, C3) checks a **returned** CT-04 typed value with the correct category — never a raised exception across the pure boundary; `correlation_id` never rides the pure signature (C2).

---

## Section 7 — Coverage, T3 Scoping & Untestable / Deferred / Boundary

**T3 posture.** Coverage is a floor and a map, not the goal. Because this is **T3**, the plan does **not** build exhaustive property/branch suites; it targets **acceptance of every P0/P1 AC (L3)**, a lean L0/L1/L2 band only where a law L3 cannot reach it, one **L4** composition participation, and one **L6** review, with **regression pins** added only for *confirmed* advisory findings. The gate is **assertion completeness over the P0/P1 ACs**, not a line-percentage. The high author-written coverage (§1) is treated as **R-003 suspect**, not as evidence of correctness.

**Untestable / deferred / out-of-Epic-7 (findings and boundaries, not omissions):**

- **7.1 — Numeric benchmark rungs / the numeric light-vs-heavy budget.** CT-16 records that the **numeric AD-13 rungs "await first measured baselines" — a deferred measurement, not a gap**. The **light-claim *interface*** is tested (A17: refuse-without-baseline; heavy → unsupported capability); the **numeric ceiling** is **not invented** — asserting one would test an unratified value. **DEFERRED (measure-then-budget).**
- **7.2 — Cross-OS / cross-build bit-identity of float content.** CT-05 inv.6 + CT-16 inv.9: float-bearing artifacts take identity from the **result label, not from hashing float bytes**; **cross-OS bit-identity is not promised**; cross-build agreement is a **separate registered comparison artifact**. The equality law is **same-process/same-build only** (A13); A24 tests the **upgrade mint**, not a cross-build number. **OUT OF SCOPE as a gate.**
- **7.3 — CT-16 → CT-17 consumption (structure families).** `intended_consumers: [COMP-QMF-STRUCTURE]`, wired only through the application composition root — **Epic 9 territory, defined-unwired**. Epic 7 tests the **CT-16 → CT-16 composition law** it owns (T7-SCN); the CT-16 → CT-17 hop is not this epic's and not runtime-provable here. **OUT OF SCOPE (epic-binding).**
- **7.4 — The two money-path conversion boundaries' arithmetic** (exact↔analytic descale/return). **qmf-core-owned (Epic 1).** Epic 7 asserts only that a price-valued output **re-enters the money path via the named boundary** as a **concept-walk expressibility** (A19), never re-implements or re-verifies the descale. **BOUNDARY.**
- **7.5 — L2 depth / footprint-class nested series data.** CT-16 last invariant: **outside the V1 series vocabulary — an ungoverned research lane** until a later pass widens the bulk form. Not tested. **DEFERRED by ratified reason.**
- **7.6 — Per-formula numeric correctness against an external oracle.** Not asserted against an invented golden — canonical arithmetic is TA-Lib by construction (A6); the metric's *arithmetic* correctness is inherited from the pinned reference, and the audit's job is the **identity / equality / restore / presence / refusal** structure around it (mirrors the DEC-0007 no-product-mock-data rule). **BOUNDARY.**
- **7.7 — PLAN-INTEGRITY CAVEAT.** `test-design-qa.md` and `QMX-handoff.md` are absent (§Process Gap). The 8-section template, the L0–L6 mapping, the P0/P1 split, and the risk-gate framing are reconstructed from the ratified corpus and the T3 brief; the "15 P0/P1 assertions" and this epic's risk-gate rows are taken from the brief's **epic-specific priorities** (canonical pin + reference-config record; derived-series identity; BarSpec discipline). Reconcile when restored. **Recorded as a finding, not worked around.**

**Findings authored while writing this plan (no fixes; from data artifacts + directory listing only):** see `findings.csv`. Seed rows:

| Finding ID | Requirement | Severity | Reproducer | Description |
|---|---|---|---|---|
| F-E07-001 | FR-019, CT-16 wiring | Info (testability) | CT-16 `consumers: []`, `wiring_status: ratified-shape-application-mediated` | CT-16 has **no in-tree consumer** (intended COMP-QMF-STRUCTURE via the composition root); every L3/L4 test must **inject qmf-core value types and drive the seam directly**, and the CT-16 → CT-17 journey is not runtime-provable in this epic. Not a defect — a testability note shaping the suite. |
| F-E07-002 | R-003, FR-019 | Info (to confirm in §5.2) | `coverage.json` — line 90.9%–100% author-written; `batch.py` 15 / `series.py` 12 missing branches | High author-written coverage is exactly where R-003 bites: the **import-time reference-config refusal**, the **equality law over cold state**, **restore-equivalence**, and **presence-map honesty** are behaviours line coverage cannot see; the missing-branch hot-spots (`batch.py`, `series.py`) are the refusal/presence arms. Elevated to a confirmed finding only if §5.2 yields a suspect/contradicts row. |
| F-E07-003 | AC7.5, CT-16 benchmark | Info (scope) | CT-16 `gaps` note: "numeric AD-13 rungs await first measured baselines" | The **numeric** benchmark rungs / light-vs-heavy budgets are **deferred-measurement**; the light-claim *interface* is testable (A17), the numeric verdict is not — asserting a number would test an unratified value. |

*(Distribution-unit check: the package ships `FAILURES.md` **and** `examples/` — no NFR-11 / L27 gap; no invented finding.)*

---

## Section 8 — Execution, Traceability Matrix & Exit Criteria

**Execution order.** L0 structural gates → L1 unit laws (binary-float, full-config fp1, presence-map, warm-up) → L2 contract + refusal shape → **L3 acceptance (every P0/P1 AC)** → L4 composition chain → L6 `bmad-code-review` + regression pins. Run from the worktree root: `uv run pytest qa/tests/epic_07 -q` (L0/L1 tier-1); `poe check-integration` band for L2/L3/L4; `bmad-code-review` for L6. **All tests under `qa/`; source read-only. A failing test → a row in `findings.csv`, never a source edit.**

**Traceability (requirement → test → priority → level → status). Every R1–R32 maps to ≥1 test.**

| Req | Test IDs | Prio | Level(s) | Status |
|---|---|---|---|---|
| R1 | T7-U2, T7-C1, T7-A1 | P0 | L1,L2,L3 | planned |
| R2 | T7-U2, T7-A1, T7-SCN | P0 | L1,L3,L4 | planned |
| R3 | T7-C1, T7-A2 | P0 | L2,L3 | planned |
| R4 | T7-U1, T7-C3 | P0 | L1,L2 | planned |
| R5 | T7-S1, T7-A3 | P1 | L0,L3 | planned |
| R6 | T7-A4 | P0 | L3 | planned |
| R7 | T7-C3, T7-A5 | P0 | L2,L3 | planned |
| R8 | T7-A5 | P0 | L3 | planned |
| R9 | T7-A6 | P0 | L3 | planned |
| R10 | T7-A6 | P1 | L3 | planned |
| R11 | T7-S4, T7-A7 | P0 | L0,L3 | planned |
| R12 | T7-U3, T7-A8 | P0 | L1,L3 | planned |
| R13 | T7-S2, T7-A9 | P0 | L0,L3 | planned |
| R14 | T7-C3, T7-A10 | P0 | L2,L3 | planned |
| R15 | T7-A11 | P1 | L3 | planned |
| R16 | T7-U4, T7-A12 | P0 | L1,L3 | planned |
| R17 | T7-A12 | P1 | L3 | planned |
| R18 | T7-S5, T7-A16 | P1 | L0,L3 | planned |
| R19 | T7-C4, T7-A13, T7-SCN | P0 | L2,L3,L4 | planned |
| R20 | T7-A18 (note) / §7.2 | P1 | L3/boundary | planned |
| R21 | T7-A14 | P0 | L3 | planned |
| R22 | T7-C3, T7-A15 | P0 | L2,L3 | planned |
| R23 | T7-A19 | P1 | L3 | planned |
| R24 | T7-A18 | P1 | L3 | planned |
| R25 | T7-C3, T7-A17 | P0 | L2,L3 | planned |
| R26 | T7-A20 | P1 | L3 | planned |
| R27 | T7-A21 | P1 | L3 | planned |
| R28 | T7-C3 | P1 | L2 | planned |
| R29 | T7-S3, T7-A22 | P1 | L0,L3 | planned |
| R30 | T7-A22 | P0 | L3 | planned |
| R31 | T7-A23 | P1 | L3 | planned |
| R32 | T7-A24, T7-C4 | P0 | L2,L3 | planned |
| composition | T7-SCN | — | L4 | planned |
| review | T7-REV (+ T7-PIN-\*) | — | L6 | planned |

**Exit criteria (Epic 7 passes audit when):**
1. Every **P0** test is green (R1, R2, R3, R4, R6, R7, R8, R9, R11, R12, R13, R14, R16, R19, R21, R22, R25, R30, R32 — via their L3 anchors plus supporting L1/L2).
2. Every **P1** test is green **or** has a recorded finding with an owner.
3. The **three §3 gates** hold: **(a)** canonical arithmetic provably used — import-refusal on pin/config drift (A5), wrap-not-reimplement (A6), vendor-neutral surface (S4/A7), upgrade-mints-with-before/after (A24); **(b)** full-config & derived-series identity (U2/A1/A2, T7-SCN, U1 no-float); **(c)** BarSpec-as-data + as-of-only + presence honesty (S2/A9, A10, U3/A8, U4/A12).
4. **T7-SCN** (L4) passes: a two-hop derived series carries the upstream fingerprint in identity and the two-hop batch result equals the two-hop streaming result under the equality law.
5. **T7-REV** (L6) has run; **each confirmed advisory finding has a regression pin** (T7-PIN-\*); unconfirmed findings are recorded, not pinned.
6. **§5.2 existing-test reconciliation** is complete: every P0/P1 behaviour is classified keep/suspect/contradicts, and every **contradicts** row is in `findings.csv` with its requirement id (R-003 evidence).
7. Every **§7 boundary/deferred item** is explicitly recorded with its owning epic/reason — none silently counted as passed or failed. In particular the **numeric benchmark budget** (§7.1), **cross-OS/cross-build float identity** (§7.2), **CT-16 → CT-17 consumption** (§7.3), and **per-formula numeric correctness** (§7.6) are logged as out-of-scope/deferred, not as coverage gaps.

Coverage ledger maintained alongside execution in `qa/epics/epic_07_qmf-indicators/` — one row per §4 test id → {level, status PASS/FINDING/DEFERRED, evidence path}.

**Plan caveat carried forward:** `test-design-qa.md` and `QMX-handoff.md` were absent from the worktree; if restored, reconcile this plan's section shape, level names, the P0/P1 split, and the risk-gate framing against them (they are authoritative over this reconstruction).
