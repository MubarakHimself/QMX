# Epic 9 (qmf-structure) — L6 requirements-fidelity review

**Verdict: GAPS.**

The suite is well above the tier-1 baseline that provoked the hardened author contract:
the flagship P0 behaviours (emission invariant, refuse-at-equal vs consumption, the
confirmed-read refusal, refit-not-overwrite, the read-time fold, the split-embargo
straddle) are asserted against independently recomputed oracles, through public surfaces,
with test-owned fakes, and with reachable reject arms. Those greens are real.

It nevertheless fails on two of the six hardened rules:

- **Rule 1 (falsifiability)** — the epic's dedicated conformance requirement
  (Story 9.4 AC-2 / CT-17 `conformance_register`) is certified by an assertion that **any**
  minted object satisfies, and one L0 assertion is provably vacuous.
- **Rules 5 and 6 (scope honesty / findings completeness)** — at least **13 owned clauses**
  have neither a test nor an `UNPROVEN` row, four of them promised by the author's own
  PLAN.md rows and then dropped silently. Two of those clauses look **unimplemented in
  source**, which rule 6 required as `observed=UNPROVEN` findings rows.

Consequently RESULTS.md's headline — *"No source defect was found … the implementation
satisfies every requirement-level assertion"* — is not warranted as written. It is true of
what was asserted; it is not true of what the epic owns.

Scope confirmed against epics.md §Epic 9 (lines 1843-1957): FR-020 is the only FR
(epics.md line 357), CT-17 the only contract. Every id below is owned by this epic.
`_bmad-output/test-artifacts/` is indeed absent from this worktree — E9-F01 independently
confirmed.

---

## 1. Wrong-expectation / hollow tests

### Material (4)

**W-1 — `test_l2_005_every_concept_walk_item_is_constructible` (test_l2_contract.py:399).
The headline defect.**
Requirement: Story 9.4 AC-2 / CT-17 `conformance_register` — the harness must keep the
11-item concept-walk list *expressible*. The assertion for all 11 items is identical:

```python
assert isinstance(artifact, Fingerprint)
assert artifact.value.startswith("fp1:sha256:")
```

Any minted object passes that. It asserts *"a fingerprint was produced"*, not *"this
concept is expressible"*. Worse, 6 of the 11 builders do not encode the distinguishing
feature of the concept they are named for:

| Builder | Concept demanded | What it actually builds |
| --- | --- | --- |
| `_build_distribution_over_price` | distribution-over-price object | a generic mint with the string `"distribution"` — already proven trivially by `test_l2_001_geometry_is_open` |
| `_build_tolerance_cluster` | cluster over **tolerance-grouped extremes** | an unordered composite of two arbitrary point children; no tolerance, no extremes |
| `_build_calendar_composite` | **ordered multi-phase calendar** composite | an ordered composite of three arbitrary children; nothing calendar-bearing (`CalendarAnchoredLevel` exists and is not used) |
| `_build_multi_barspec_nest` | **multi-BarSpec** nest | two children with different `confirmation_delay_bound` values (3, 15) as a BarSpec proxy; no BarSpec anywhere |
| `_build_born_from_invalidation` | object **born from another object's invalidation** | builds a parent `InvalidationRecord`, **discards it**, then mints an unrelated child; no edge, no lineage, no linkage of any kind |
| `_build_threshold_breach_reversal` | breach **then reversal** | a level plus one `"breach"` interaction; the reversal half is absent |

`_build_retro_anchored_zone` likewise builds its consumption-state `InteractionRecord` and
throws the result away. Only `PATTERN_REFITS`, `CROSS_INSTRUMENT_DIVERGENCE`,
`A_PRIORI_PRICE_GRIDS` and (partly) `PROJECTED_LEVELS` genuinely encode their concept.
This is the banned "duplicate another test and relabel it" shape applied 11 times: the
counter-case (a concept the library can no longer express) cannot make this test fail.
The construction calls do exercise real refusal paths through `H.ok`, so it is not
completely inert — but the requirement it is credited with is effectively unverified.

**W-2 — `test_l0_002_seams_are_runtime_checkable_protocols` (test_l0_structural.py:132).
Vacuous assertion.**

```python
assert hasattr(seam, "__instancecheck__") or getattr(seam, "_is_runtime_protocol", False)
```

`hasattr(cls, "__instancecheck__")` is `True` for **every** Python class (`type` defines
it) — verified in this worktree against a plain class and against `int`. The `or`
short-circuits, `_is_runtime_protocol` is never read, and no counter-case can fail this
line. The preceding line asserts `_is_protocol`, a self-declared marker attribute — banned
shape 1. The claim happens to be true (all five seams *are* runtime-checkable, verified
independently), so nothing is masked; the assertion simply proves nothing. The behavioural
form already exists elsewhere in the suite —
`test_l3_016_indicator_consumed_as_declared_input` does
`isinstance(fake, IndicatorResultInput)` on a test-owned fake — and should have been used
for all five seams.

**W-3 — `test_l3_017_peak_memory_regression_fails_exactly_as_a_slowdown`
(test_l3_acceptance.py:542). Over-claims; half the comparison is missing.**
The requirement (Story 9.4 AC-4 / FM-8) is *comparative*: a peak-memory regression fails
**exactly as** a slowdown does. The test exercises only the memory arm (seconds held at
1.0 in every case) and never asserts that a seconds-regression with steady memory is
refused, so the equivalence is not observed — only one of the two limbs is. It then reads
`result.context["memory_regressed"]`, the implementation's own report field, as the
observer of the effect (rule 3: state the effect through a test-owned observation, not the
implementation's trace). The honest form asserts both directions refuse with the same
category, and both pass under tolerance.

**W-4 — `test_l0_004_failure_register_names_the_ct17_refusal_categories`
(test_l0_structural.py:240). Self-declared doc as proof.**
Asserts only that the lowercase substrings `"invalid input"` and `"policy rejection"`
appear anywhere in the package's own `FAILURES.md`. The governing requirement (NFR-11,
epics.md line 118, standing on every story per line 475) demands each entry carry **class,
detection, recovery semantics, degraded state, notification tier, product-user
affordance**. PLAN.md row QA-E09-L0-004 promised *"every typed-refusal path named in CT-17
has a `FAILURES.md` register entry"*; CT-17 line 58 names five categories, not two. The
delivered test is a narrowing with no `UNPROVEN` row.

### Minor (3) — noted, not counted as violations

- **W-5** — `test_l2_002_calendar_level_declares_fingerprinted_policies` /
  `..._policy_enums_are_the_ct17_closed_sets` are *correct* against CT-17 line 26's literal
  wording (declared + fingerprinted) and the enum literals come from the ratified contract,
  not the module, so they are not banned shape 1. But the package has **no sampling or
  schedule-gap resolution entry point at all** (`geometry.py` exposes only `try_create` /
  `fp1_identity` / `content_fingerprint`), so the green certifies a declared, fingerprinted
  field and nothing about how a gap or a sample is actually governed. Worth an explicit
  scope note.
- **W-6** — several tests pin implementation-chosen refusal context values no ratified
  oracle fixes: `context["field"] == "low"` (L1-004), `context["index"] == 1` and
  `context["evidence_class"] == "unconfirmed"` (L3-010), `context["field"] == "geometry"`
  (L2-001). The load-bearing half of each assertion is requirement-grounded; the context
  pin is brittle over-specification, close to "asserting exact prose of unratified
  messages".
- **W-7** — `test_l2_005_builder_set_matches_the_register_no_drift` pins the module's
  `CONCEPT_WALK_REGISTER` to a test-side literal set of 11 names (legitimate), but never
  binds those names to CT-17's `conformance_register` prose (line 69). Combined with W-1,
  the register→contract binding rests on naming alone.
- **W-8** — `test_l3_012_bound_derived_embargo_governs_the_boundary` asserts
  `embargo == bound × observation_width` and reads the straddle gap as
  `confirmed_at − observed_at`. CT-17 line 23 says only that the bound *"feeds"* the
  required widths and line 24 says only *"unless the declared embargo covers the gap"* —
  neither formula is ratified. The reading is the sane one, but it is the implementation's
  arithmetic, not the contract's.

### Everything else holds up

L1-001 (independent oracle, both arms demonstrably reachable), L1-002 (37 boundaries, real
no-raise universal), L1-003/004 (identity and exactness quantified), L3-001, L3-003,
L3-005 (independent fold oracle plus `not hasattr` absence checks), L3-006, L3-007,
L3-008 (two test-owned predicate fakes, opt-in cascade observed not to mutate the child's
own read), L3-010 (`assert not isinstance(result, tuple)` — a silent filter genuinely
fails this), L3-011, L3-012, L3-013, L3-014, L3-016, L3-018, L2-003, L2-004 (registry
parsed as the oracle), L2-006. These are requirement-shaped and falsifiable.

---

## 2. Missed requirements — owned, no test, no `UNPROVEN` row

Rule 5 requires an explicit `UNPROVEN` row for any clause excluded or narrowed; rule 6
requires a `findings.csv` row for anything structurally unprovable **or unimplemented**.
None of the following got either.

| # | Clause | Authority | Status |
| - | ------ | --------- | ------ |
| M-1 | Anchor span, observed-at and every lifecycle instant "may **never be occurrence-classified**" | Story 9.1 AC-2 (epics.md 1866); CT-17 inv. line 17 | **Promised in PLAN.md row QA-E09-L3-002, silently dropped.** L3-002 asserts identity-bearing only. |
| M-2 | The `anchor.start ≤ anchor.end` link of the emission chain | Story 9.1 AC-3 (epics.md 1870); CT-17 line 18 | **Reject arm unreachable by construction** — L1-001 builds `a_end = a_start + a_len, a_len ≥ 0`, so an inverted anchor is never generated, and no other test refuses one. Rule 1: a generator whose refusal arm is unreachable. |
| M-3 | "Interaction records are the **only** permitted way an object's state evolves" | Story 9.2 AC-1 (epics.md 1883); CT-17 line 19 | **Promised in PLAN.md row QA-E09-L3-004, dropped.** L3-004 proves three separate kinds and frozenness, not exclusivity. |
| M-4 | The **purge** half of "required purge/embargo widths" | Story 9.3 AC-3 (epics.md 1917); CT-17 line 23 | **Promised in PLAN.md row QA-E09-L3-012, dropped.** Only embargo is exercised. |
| M-5 | Sloped-object **evaluation at an instant crosses the named analytic-to-exact boundary** with its declared rounding | CT-17 line 25; PLAN.md row QA-E09-L1-004 | **Looks unimplemented.** `SlopedObject` stores `target_scale` and `rounding` but exposes no evaluation entry point (`geometry.py` — `try_create`, `fp1_identity`, `content_fingerprint` only). Rule 6 required an `observed=UNPROVEN` row. |
| M-6 | "CT-16's state bound and **snapshot/restore obligations apply to families verbatim**" | CT-17 line 31 | **Looks unimplemented.** Zero occurrences of `snapshot` or `restore` anywhere in `packages/qmf-structure/src/qmf/structure/`. No test, no row. |
| M-7 | The fourth light/heavy bound — **synchronous availability** | CT-17 line 31; Story 9.4 AC-4 | Refusal path exists (`budget.py:253`) and is never exercised: every test builds `synchronous_available=True`. Three of four bounds covered, the fourth silently dropped. |
| M-8 | Family ids "opaque, stable, **never reused**"; families "versioned, **addable never redefined**" | CT-17 line 33 + schema line 39; quoted in PLAN.md line 252 | No test. |
| M-9 | A family is "never a **strategy, bot, or Book category**" | CT-17 line 13 | **Promised in PLAN.md row QA-E09-L2-001, dropped.** Only the no-school half (FM-9) is tested. |
| M-10 | "A **mechanically stated variant of any school's concept is admissible** under the same bar" | CT-17 line 20 (DEC-0133) | The positive arm of FM-9/L32 is untested — only the negative (no school name in vocabulary) is. A suite that only forbids school names cannot distinguish correct behaviour from over-refusal. |
| M-11 | "still-**unmitigated**" as a read-time fold | CT-17 nullability line 68; PLAN.md row QA-E09-L3-005 | Only `still_valid` is folded. |
| M-12 | Composite children "may be of **any governed kind** — indicator results, structure objects, calendar windows" | CT-17 line 27 | Every child in every test is a structure object. |
| M-13 | "The benchmark harness with the **same standing as unit tests**" | Story 9.4 AC-4 (epics.md 1950) | `_bench.py` presence is checked; nothing binds it to the tier-2 gate. Process-shaped — legitimately hard in-lane, which is exactly what an `UNPROVEN` row is for. |
| M-14 | NFR-11 six-part register entries | epics.md 118 / 475 | See W-4. |

M-5, M-6 and M-7 are the ones that matter: two are candidate **unimplemented-requirement
defects** in source and the third is an unexercised refusal path, and all three are
consistent with RESULTS.md's "no source defect" only because they were never looked at.

---

## 3. Per `findings.csv` row

| Row | Requirement | Verdict |
| --- | ----------- | ------- |
| **E9-F01** — test-artifacts absent | process/traceability | **Genuine violation, correctly recorded.** Independently confirmed: `_bmad-output/` contains `planning-artifacts/` only; `test-artifacts/` does not exist. Medium severity is right — the 15 P0/P1 handoff assertions and this epic's risk-gate rows could not be consumed, so the suite's priority ranking is self-assigned. |
| **E9-F02** — isolated-per-package-env import gate | FR-020; CT-17; Story 9.1 AC-1 | **UNPROVEN, correctly recorded.** The enforcement is out-of-band CI; the in-lane substitute (AST import graph, both directions, with a reachable reject arm at test_l0_structural.py:65) is the strongest thing constructible here. Reason given meets the bar. |
| **E9-F03** — roster SemVer lockstep | FR-020; CT-17; Story 9.1 AC-1 | **UNPROVEN recorded, but the justification does not hold — reclassify as a coverage gap.** This clause was provable in-lane in five lines: all seven `packages/*/pyproject.toml` files are in this worktree and are readable; I checked them — qmf-core, qmf-data, qmf-indicators, qmf-registry, qmf-risk, qmf-structure, qmf-venue are all `version = "0.1.0"`, i.e. in lockstep. "An Epic-1 invariant not re-verified here" is a scope preference, not structural unprovability. The `UNPROVEN` bar is *cannot be constructed*, not *belongs to another epic's story* — and Story 9.1 AC-1 puts the clause in this epic's own section. |
| **E9-F04** — benchmark budget numbers | FR-020; CT-17; Story 9.4 AC-4; FM-8 | **UNPROVEN, correctly recorded.** Measure-then-budget: no baseline numbers exist, and refusing to invent one is the right call. The negatives that *are* provable are proven — with the exception of M-7 (synchronous availability) and the missing slowdown limb in W-3, neither of which this row covers. |
| **E9-F05** — governed-evidence persistence | FR-020; CT-17; Story 9.3 AC-5 | **UNPROVEN, correctly recorded.** CT-17 line 30 makes persistence the composition root's act (CT-11/CT-13, Epic 3); the library holds only the verdict, which L3-014 proves. Correctly scoped and correctly not tested here. |
| **E9-F06** — CT-08 registration gate | CT-08; GAP-0016; Story 9.3 AC-5 | **UNPROVEN, correctly recorded — and correctly out of scope.** CT-17 line 10 and epics.md line 1927 defer the gate to GAP-0016 by design; CT-08 is another epic's contract. Recording it as deferred-not-defective, and testing the interim emission-invariant guard instead, is exactly right under the epic-binding rule. |

**Row tally: 5 sound (1 genuine violation + 4 correctly-recorded UNPROVEN), 1 mis-justified
(E9-F03). No row is a wrong expectation about behaviour.** The `findings.csv` defect is
what is *absent* from it — M-5, M-6, M-7 and the W-1/W-3/W-4 narrowings each owed a row
under rules 5 and 6.

---

## 4. What would close this out

1. Rewrite `test_l2_005_every_concept_walk_item_is_constructible` so each builder asserts
   the concept's **distinguishing** structure (the born-from-invalidation edge actually
   linking parent invalidation to child birth; a real tolerance parameter on the cluster; a
   `CalendarAnchoredLevel` child in the calendar composite; distinct BarSpecs in the nest;
   the reversal interaction after the breach) — then verify each can fail by breaking one
   builder's linkage.
2. Replace the vacuous W-2 assertion with `isinstance()` against a test-owned duck for each
   of the five seams.
3. Add the missing limb to W-3 (seconds-regression refused identically) and observe the
   category rather than `context["memory_regressed"]`.
4. Add tests for M-2 (inverted anchor refused), M-7 (`synchronous_available=False` refuses a
   light claim), M-3 and M-1 — all cheap and in-lane.
5. Convert E9-F03 into a five-line L0 lockstep test (it passes today).
6. File `observed=UNPROVEN` rows for M-5 (no sloped evaluation entry point), M-6 (no
   snapshot/restore), M-13 and M-14, and soften RESULTS.md's "no source defect" headline to
   "no source defect **among the clauses asserted**" until M-5 and M-6 are adjudicated.
