# L6-REVIEW — Epic 21: QMB optimization studies (requirements-fidelity review)

**Reviewer lane:** L6 requirements-fidelity. One question per test: *does it assert what
the requirement demands, or what the implementation happens to do?*
**Inputs reviewed:** `PLAN.md`, `RESULTS.md`, `findings.csv`, `qa/tests/epic_21/` (7 files
+ `conftest.py`, 34 tests). Source read as read-only evidence only; nothing run, nothing edited.
**Authorities:** epics.md Epic 21 §Stories 21.1–21.6 (lines 4084–4273); `docs/contracts/`
(ct-01 money/unit-kind, ct-04 typed refusal, ct-12 dataset split, ct-32 performance result);
`packages/qmf-core/src/qmf/core/exact.py` module law (cross-kind operand → typed refusal).
The two system authorities named in the brief (`test-design-qa.md`, `QMX-handoff.md`) are
**absent from this worktree** — confirmed; the author's Process Gap note stands and this
review inherits it.

---

## Verdict: **gaps**

The suite is unusually disciplined for its class — refusals are asserted as *returned*
CT-04 values, identity is scanned recursively for floats and byte blobs, the determinism
tests carry a real content-sensitivity witness, and PIN-1 is a correctly-expectation-bound
red that confirms a genuine defect. But three things keep it short of adequate:

1. **One whole epics.md acceptance criterion (Story 21.3 AC3 — the seal law and the sealed
   holdout) is untested, has live Epic-21 surfaces, and is recorded nowhere in
   `findings.csv`** — it was moved into a RESULTS section explicitly labelled "not counted
   here". That is the silent narrowing rule 5 forbids, over the epic's highest-stakes
   evidence law.
2. **Eight green tests assert structure the module declares about itself rather than
   behaviour it performs** — including one assertion (T21-301) that is arithmetically
   incapable of failing, and three that pass the conclusion in as an argument (T21-312/314/315).
   Two of those three carry a **P0** label.
3. **Four further in-epic clauses have live surfaces and no test and no UNPROVEN row** —
   the whole-generation barrier (`StudyStepper.tell`), good-region clustering
   (`report.clusters`), the `qmb` CLI estimate door, and space-from-bot-definition.

`findings.csv` is not empty, but rule 6 is still unmet: the structurally-unproven
requirements above are absent from it, and one row that *is* present (E21-F04) claims more
proof than its test delivers.

---

## Part 1 — Wrong-expectation / hollow tests

Ordered by how much a green here misleads a reader.

### 1. T21-301 [R1] — an assertion that cannot fail

```python
layer = space.run_config_layer()
assert layer[STUDY_SPACE_KEY] == space.fp1_identity()
```

`StudyParameterSpace.run_config_layer()` is, verbatim (space.py L116-123),
`return {STUDY_SPACE_KEY: self.fp1_identity()}`. The assertion compares the method's
return value against the expression the method is defined as. No counter-case exists —
**rule 1 (falsifiability) is unsatisfiable for this line**, and it is the only line
standing behind the requirement's load-bearing half.

R1 / OPT-2 demands the declared space be **identity-bearing content of the *resolved
run-config*** ("never a code edit to swap the tunnel"). The resolved run-config is never
built: `qmb.config`'s compiler is never imported, and the space is never observed inside a
resolved config's fingerprint or keys. The real test — resolve a run-config with this layer
overlaid and observe the space content inside the resolved config's fp1 — was constructible
and was not written.

### 2. T21-312 [R13] — self-declared flags plus a guard handed its own answer

```python
assert plan.train_run.contributes_to_objective is True
assert plan.test_run.contributes_to_objective is False
refused = admit_objective_run(plan.test_run)   # refuses because the flag says so
```

R13 demands the **training run computes the objective** while the **testing run records
measures without contributing to it**. Nothing here computes an objective. The test reads
two booleans the plan declares about itself, then hands one of those flagged runs to a
guard that reads the same flag. An implementation that set the flags correctly and then
folded both splits into the objective would pass every line. The available real
observation — feed a train-split line and a test-split line to `compute_winner_set` and
show the objective value derives from the train line alone — was not used.

### 3. T21-314 [R15] — the conclusion passed in as an argument (P1, but the taint law)

```python
assert_ct04_refusal(refuse_split_edge_or_budget(claims_edge=True), POLICY_REJECTION)
assert_ct04_refusal(refuse_split_edge_or_budget(spends_split_budget=True), POLICY_REJECTION)
```

The requirement is that a trial run **cannot** spend split budget or claim edge. The test
tells a guard "this run claims edge" and observes the guard say no. That proves the guard
exists; it says nothing about whether any Epic-21 trial path calls it. Banned shape:
*passing the conclusion in as an argument*. The taint clause is then asserted as
`plan.train_run.taint == "optimistic"` — a declared attribute of the value under test, not
an observed fill.

### 4. T21-315 [R16] — same shape, carrying a **P0** label

```python
assert_ct04_refusal(admit_study_world(World.SIMULATED), POLICY_REJECTION)
assert_ct04_refusal(admit_study_world("synthetic-tainted"), POLICY_REJECTION)
```

R16 / B-7: a Study config **that would resolve to** `world = simulated` (any run reading
store-tainted synthetic data) is refused. The test hands `World.SIMULATED` and a token
literally spelled `"synthetic-tainted"` straight to the admitter — the derivation *from
data provenance* that makes the firewall real is never exercised. The plan itself assigns
world-derivation to Epic 13/14, which is a legitimate scope call — but then the P0 claim in
RESULTS ("the synthetic backdoor stays closed") is stronger than the evidence, and no
UNPROVEN row records the narrowing. The `coerce_study_splits({... "world": "simulated"})`
case is the one genuine assertion in this test.

### 5. T21-327 [R28] — proves another epic's read primitive, then over-claims

The duplicate-collapse and collision-refusal assertions land in
`qmb/ledger/line.py::merge_ledger_lines` (L447-500) — the **ledger merge primitive**, an
Epic-13/15-owned surface reached incidentally through `compute_winner_set`. Under the
epic-binding rule that is another epic's requirement.

The "never zero" arm is worse: the test **constructs its own `aborted_line("c")`**, feeds
it to the fold, and asserts the fold kept it. It observes that a reader does not discard a
line the test itself supplied. R28's actual demand — *on operator terminate, the
orchestrator appends exactly one ledger line per already-spawned run* — is about the append
path and is not touched. RESULTS records R28 as "PASS (narrowed)" with only the
`stopped`-state clause UNPROVEN; the honest disposition is **R28 UNPROVEN in Epic-21
isolation, in full**.

### 6. T21-330 [R31] — half the requirement dropped without a row

PLAN §4 committed to: *"assert the artifact contains **no numeric threshold constant** and
no pass/fail field for search quality."* The written test asserts only a string-value
denylist `{"pass", "fail", "sr_star", "search_quality"}` — an arbitrary token list — and
never checks for a numeric threshold. SC-07's "no invented threshold" half of R31 is
**silently narrowed** (rule 5). Separately, `refuse_search_quality_verdict("SR*")` is a
guard that refuses every non-blank name it is given; asserting it refuses is near-tautological
and is not evidence about the report.

### 7. T21-331 [R32] — a self-declared marker, and "Bar/Price" quietly became "x"

`assert report.canonical_payload == "series-data"` reads
`SensitivityReport.canonical_payload`, whose value is the module constant
`SENSITIVITY_CANONICAL_PAYLOAD` supplied as a dataclass default (sensitivity.py L501) — a
**self-declared marker asserted as proof of behaviour** (banned shape 2). The
`find_bytes(report.fp1_identity()) == []` scan beside it is the real observation and is
good. Separately, the AC says chart series cite exact **`Bar`/`Price`** inputs; the test
asserts slice bins cite the exact **parameter** values — a defensible proxy, but a
narrowing with no UNPROVEN row.

### 8. T21-313 [R14] — one unfalsifiable line inside a good test

`assert "aliases" not in collect_string_values(identity)` — `collect_string_values` returns
string **values**, and `"aliases"` is a **key**. The check can essentially never fire; the
comment above it ("the display alias map is not part of identity content") describes an
assertion that was not written (`"display" not in identity` / `"aliases" not in
identity["splits"]`). The fingerprint assertions carrying the requirement are sound.

### 9. T21-322 [R23] — positive arm calls the guard against its own module state

`refuse_sampler_contract_bump(generator_provenance())` feeds the module's own provenance
back into the module's own guard (banned shape: *calling a function against itself*). The
bumped-major arm **is** a real discriminator, so this test is only half self-referential —
noted, not counted as a failure of the requirement. `label["sampler_identity"]` is asserted
present-and-non-empty only, which is what the AC asks (presence), so that is fine.

### 10. Minor (recorded, not counted)

- **T21-325/326** compare `estimate.status` against the module's own exported
  `ESTIMATE_STATUS_*` constants. Tautological in isolation; carried by the real
  assertions beside them (`projected_wall_ns` formula; `None`-ness and key absence).
- **T21-r9 [R9]** asserts `blank.enabled is True` / `blank.is_active is False` — declared
  flags — but `as_constraint() is None` is the behavioural anchor and it is present. The
  AC's other half ("a UI-editable configurable with **no spine constant**") is untested:
  the observable form is the configurable key in the refusal context
  (`configurable=MIN_TRADES_FLOOR_KEY`, objective.py L407/414), which the test never reads.
- **T21-307 [R7]** proves a creation-time refusal but the "never deferred to trial time"
  clause rests on a docstring comment ("`coerce_study_criteria` schedules no trial"), not
  on an observation through a spawn sink.
- **T21-308 [R8]** exercises exactly one operator (`<=`) of the six the AC enumerates
  (`<, <=, >, >=, =, !=`). Narrowing, no row.
- **T21-328 [R29]** recomputes mean/min/max/median independently (good) but never checks
  **std** against an independent recomputation — T21-332 only checks its *shape*. `std` is
  named explicitly in the AC.

**Tests that assert the requirement cleanly** (no reservations): T21-302, T21-303, T21-304,
T21-305, T21-306, T21-309, T21-310, T21-311, T21-316, T21-317, T21-318, T21-319, T21-320,
T21-321, T21-323, T21-324, T21-329, T21-332, T21-333. That is a solid majority, and the
fixture discipline in `conftest.py` (exact-integer money, fp1-canonical measures, recursive
float/bytes scanners, returned-refusal harness) is genuinely good work.

---

## Part 2 — Requirements in this epic's epics.md section that NO test covers

Every item below was confirmed to have a **live, shipped Epic-21 surface** — none is
untestable, and none belongs to another epic.

| # | epics.md clause | Story | Live surface | Status in QA artifacts |
|---|---|---|---|---|
| **M1** | "the 12-month seal, embargo, knowledge-time, and calendar-in-band rules are enforced at the boundary and **the sealed holdout is excluded from default access**" | 21.3 AC3 | `optimize/splits.py::admit_default_split_access` (L462 — `sealed-test` → policy rejection, CT-12/AR-16/DEC-0119) and `::serve_split_read` (L485) | **No test imports either function.** Not in findings.csv. Filed in RESULTS under "Deferred seams (owned elsewhere — **not counted here**)" |
| **M2** | "the orchestrator … **barriers on the whole generation**, conditions the sampler on the completed generation, then proposes the next (propose → run → barrier → condition)"; adapter "pinned `n_jobs=1`" | 21.4 AC2 | `sampler.py::StudyStepper.tell` (L872 — refuses unless every ask in the generation reported); `SAMPLER_JOBS` pin | **`tell` is never called by any test.** Order-invariance is asserted only against the pure port with hand-permuted priors — never across the barrier the AC names. No row. |
| **M3** | "**good regions are clustered and each cluster is described as data**" | 21.6 AC2 | `sensitivity.py::GoodRegionCluster` (L355) + `SensitivityReport.clusters` (L498) — `member_run_ids`, `parameter_ranges`, per-cluster `distribution`, `contains_winner` | **No R-row in PLAN §2, no test, no row.** Only the second half of this AC (charts-as-data) was extracted as R32. |
| **M4** | "When an estimate is requested **through the `qmb` CLI door (click 8.4.2)**" | 21.5 AC3 | `qmb/doors/cli/tree.py` L361-378 (calls `estimate_study_cost`) | Tests call the library function directly. Door never driven. No row. |
| **M5** | "materialized as identity-bearing content of the resolved run-config — **never a code edit to swap the tunnel**" | 21.1 AC1 | `optimize::parameter_space_from_bot`, `::study_space_from_bot` (space-from-CT-33-bot-definition); `qmb.config` resolved-run-config compiler | Never driven — see wrong-expectation #1; the only assertion is self-referential. |
| **M6** | "**its result artifact is emitted** … includes per-parameter objective slices and an objective distribution summary" | 21.6 AC1 | `optimize::StudyArtifact` | Never built. Slices/summary asserted on the bare report — a fair proxy, but the named surface is untouched and unrecorded. |
| **M7** | "N hard constraints … `op ∈ {<, <=, >, >=, =, !=}`" | 21.2 AC3 | `STUDY_CONSTRAINT_OPERATORS` / `StudyConstraint.try_create` | One of six operators exercised. No row. |
| **M8** | "the Study may stop early, **transitioning to a clean terminal state with partial results preserved**" | 21.2 AC5 | terminal-state seam (same seam as R28's `stopped`) | `target_reached` and winner preservation are asserted; the clean-terminal-state clause is neither asserted nor given an UNPROVEN row (only R28's got one). |
| **M9** | "its floor is a **UI-editable configurable with no spine constant**" | 21.2 AC4 | `MIN_TRADES_FLOOR_KEY` surfaced in the refusal context | Untested half; see minor notes. |

**M1 is the single most important gap** (expanded in Part 4).

---

## Part 3 — Per `findings.csv` row

| Row | Req | Verdict | Basis |
|---|---|---|---|
| **E21-F01** | R10 / CT-01 | **Genuine violation** | Confirmed independently against source. `StudyObjective` *stores* `target_currency` and `target_unit_kind` (objective.py L200-217) and then `meets_target` (L224-234) compares bare `Fraction` magnitudes — `magnitude >= self.target_value` — with no currency or unit-kind guard, on the path called from `_place_trial`. The refusal is requirement-derived, not test-invented: CT-01 fixes a closed unit-kind vocabulary with "a null unit-kind is a typed refusal, never a default", and qmf-core's own money law (`packages/qmf-core/src/qmf/core/exact.py` L33-35) states that "a cross-kind operand (a different currency, unit, instrument, or value class) returns a typed refusal". The test is correctly expectation-bound: it accepts a refusal at *either* boundary (`INVALID_INPUT` or `POLICY_REJECTION`) and its same-currency companion passes first, so the red is isolated, not vacuous. Severity `high` is right — a silent apples-to-oranges early-stop is an invented decision on the money path. |
| **E21-F02** | R27 (peak-memory) | **UNPROVEN, correctly recorded** — with one correction | The disposition is honest and names the owning epic (Epic 15 governor, FR-045). One correction for the record: **the peak-memory clause is not in Epic 21's epics.md at all.** Story 21.5 AC4 reads only "the estimate is returned as `not-yet-measured` rather than an invented figure"; the memory dimension entered via the brief's risk gates R-013/R-017 and the plan's own R27 wording. So this is not an Epic-21 defect and never could have been — the row is the right *outcome* reached through slightly over-scoped requirement drafting. PIN-2's real result (the estimator honestly returns `not-yet-measured` with no synthesized runtime, discriminated by T21-325's measured path) is sound. |
| **E21-F03** | R23 (CT-32 byte reproduction) | **UNPROVEN, correctly recorded** | Matches PLAN §7 and the epic-binding rule: the event-slice loop and the CT-32 artifact are Epic 14 (Story 14.7) / Epic 19. What Epic 21 owns — trial-label content and the reproduce-or-refuse contract-versioning event — is asserted, and the bumped-major arm is a real discriminator. Correct scope call, correctly filed. |
| **E21-F04** | R28 (clean `stopped` state) | **UNPROVEN recorded, but the row under-states the gap** | The narrowing it declares (the `stopped`-state transition → Epic 15) is correct. Its companion claim — *"the one-line-per-run count law **IS** proven via the read fold"* — is not supported by T21-327 (wrong-expectation #5): the duplicate/collision arms exercise `qmb/ledger/line.py::merge_ledger_lines`, an out-of-epic read primitive, and the "never zero" arm asserts that the fold kept an aborted line the **test itself supplied**. Nothing observes an append. The row should be widened to **R28 UNPROVEN in Epic-21 isolation, in full**, and RESULTS' "PASS (narrowed)" for T21-327 downgraded accordingly. |

**Rows that rule 6 requires and that are missing:** M1 (Story 21.3 AC3 seal/holdout — the
serious one), M2 (barrier + `n_jobs=1`), M3 (good-region clustering), M4 (CLI estimate
door), M5 (space-from-bot / resolved-run-config), M7 (constraint operator coverage), M8
(R11 clean terminal state), plus the R31 numeric-threshold half and the R32 `Bar`/`Price`
narrowing.

---

## Part 4 — The single most important gap

**Story 21.3 AC3 — the seal law and the sealed holdout — is an in-epic acceptance criterion
with two shipped Epic-21 functions, zero tests, and no findings row.**

`optimize/splits.py::admit_default_split_access` (L462) is Epic-21 code that decides whether
a research read may touch a segment role, and refuses `sealed-test` under default access
with a policy rejection citing CT-12, AR-16 seal law, DEC-0119.
`::serve_split_read` (L485) composes the CT-12 `HoldoutSeal` guard, the manifest's
embargo/knowledge-time partitioning, and that admission into the one split-read door.
Neither function is imported by any file under `qa/tests/epic_21/`.

The falsifiable test was trivially available and is a two-liner:
`admit_default_split_access("sealed-test")` must be a `POLICY_REJECTION`, while `train`
and `validation` are admitted. That single case would prove the holdout door is shut. It
was not written.

Instead the clause was filed in RESULTS.md under *"Deferred seams (owned elsewhere —
asserted only at Epic-21's boundary, **not counted here**)"*, attributed to qmf-data /
Epic 3. The attribution is half right — the *enforcement primitives* (`HoldoutSeal`,
`SplitManifest.partition_record`) are indeed qmf-data's — but the **admission decision is
Epic 21's own code**, in this epic's own package, implementing this epic's own AC. Routing
a live in-epic surface into an uncounted "deferred" bucket, with no `findings.csv` row, is
exactly the silent narrowing rule 5 bans, and it lands on the one requirement in Epic 21
whose failure mode is an unsealed holdout — the platform's most expensive kind of dishonesty,
and the failure class this Study epic exists to guard against.

Why this outranks the rest: PIN-1 (E21-F01) is a real defect but it is *found, filed, and
visible*. M1 is a hole that a reader of RESULTS.md would not know is there — the artifact
reads as though the clause belongs to someone else. Everything else in Part 1 weakens
evidence for requirements that at least have a row; M1 removes a requirement from the
ledger entirely.

---

## Required repairs (for the author lane, in order)

1. **Test M1.** `admit_default_split_access`: `sealed-test` → policy rejection;
   `train`/`validation` admitted. Then either a `serve_split_read` case or an explicit
   `findings.csv` UNPROVEN row naming exactly which sub-clause is qmf-data's.
2. **Rewrite T21-301's identity assertion** against a resolved run-config, or file R1's
   run-config clause as UNPROVEN. As written it cannot fail.
3. **Re-file R28** as UNPROVEN in full (widen E21-F04); downgrade T21-327's RESULTS row.
4. **Re-shape T21-312 / T21-314 / T21-315** to observe effects instead of flags and handed
   conclusions — or record each narrowing as an UNPROVEN row. Two of the three are P0.
5. **Add rows or tests for M2–M9** (barrier/`tell`, clustering, CLI door, space-from-bot,
   artifact, operator set, R11 terminal state, R9 configurable key) and for the R31
   numeric-threshold half.
6. **Reconcile against `test-design-qa.md` / `QMX-handoff.md` when restored** — the P0/P1
   split, the L0–L6 definitions, and the 15-assertion set used here are all reconstructed.
