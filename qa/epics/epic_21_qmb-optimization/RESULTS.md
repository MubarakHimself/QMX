# RESULTS — Epic 21: QMB optimization studies (independent verification)

**Runner:** `uv run pytest qa/tests/epic_21 -q --tb=short` (from the worktree root).
**Outcome:** **34 tests — 33 passed, 1 failed, 0 errored.** The single failure is
**REGRESSION PIN-1 (T21-309)**, a *confirmed advisory finding*, expected to fail
against current source and recorded as a finding rather than fixed (source is
read-only). Determinism tests (T21-317/T21-318) additionally re-run green under
`PYTHONHASHSEED=0,1,12345`.

**Audit tier T3** — contract-surface (L3) over the P0/P1 acceptance criteria + the
two regression pins. All effects are observed through returned public values (winner
sets, batches, reports, typed refusals); no test asserts a module's self-declared
constant/flag as proof of behaviour, and no source was edited or assertion weakened.

**Pins:**
- **PIN-1 (R10 / T21-309): FAIL — finding CONFIRMED (E21-F01).** Cross-currency
  `target_value` is compared by bare numeric magnitude; no unit-kind/currency guard.
- **PIN-2 (R27 / T21-326): PASS — finding NOT reproduced** for the per-trial-runtime
  baseline path (the estimator honestly returns `not-yet-measured`). The
  *peak-memory* sub-clause the plan added is **UNPROVEN** in Epic-21 isolation — no
  memory dimension exists in the Study cost estimator (Epic-15 governor territory).
  Recorded as E21-F02.

---

## Per-test results

| Test | Req | Level | Status | One-line meaning |
|---|---|---|---|---|
| T21-301 | R1 | L3 | PASS | A four-type + money space validates and is emitted as run-config fp1 identity content (not a mutated tunnel). |
| T21-302 | R2 | L3 | PASS | `min>max`, `step<=0`, `step>(max-min)` each return an `invalid input` naming the parameter — no silent clamp. |
| T21-303 | R3 | L3 | PASS | Empty categorical options and a default outside options each return `invalid input`. |
| T21-304 | R4 | **L3 P0** | PASS | A binary float at any money bound refuses; money-as-rational refuses; a clean money param validates (money-path float ban). |
| T21-305 | R5 | L3 | PASS | Identical spaces share the fp1 fingerprint; a different space does not collide; identity is float-free. |
| T21-306 | R6 | L3 | PASS | `min`/`max` accepted; a direction outside `{min,max}` returns `invalid input`. |
| T21-307 | R7 | L3 | PASS | An off-roster objective or constraint metric is refused at Study creation (no trial scheduled). |
| T21-308 | R8 | L3 | PASS | A constraint-violating trial is held out of the winner set yet present (excluded) and names the violated constraint. |
| **T21-309** | **R10** | **L3 P0 PIN-1** | **FAIL (finding confirmed)** | A cross-currency `target_value` is silently numerically compared (`meets_target`/`target_reached` True) instead of a CT-04 refusal. **E21-F01.** |
| T21-310 | R11 | L3 | PASS | A valid same-unit target that a trial meets flags `target_reached`, winners preserved; unmet target -> no early stop. |
| T21-311 | R12 | L3 | PASS | The winner is a correct read-time ranking (max objective first), optimistic-tainted, with no edge/bar-verdict token in identity. |
| T21-r9 | R9 | L3 | PASS | The min-trades gate is on by default; a blank floor invents no number (excludes nothing); a configured floor yields a `total_trades >= floor` constraint. |
| T21-312 | R13 | L3 | PASS | Training feeds the objective; the testing run (identical param-set fp1) is a policy rejection if admitted to the objective. |
| T21-313 | R14 | L3 | PASS | Both split fingerprints ride the trial label; `train`/`test` aliases are display-only, never substituted for the fingerprints. |
| T21-314 | R15 | L3 | PASS | The compliant split fill passes; claiming edge or spending split budget is a policy rejection; a non-optimistic taint is `invalid input`; runs carry the optimistic taint. |
| T21-315 | R16 | **L3 P0** | PASS | `world=simulated` (declared or synthetic-provenance-derived) is a policy rejection; `world=replay` is admitted. |
| T21-316 | R17 | L3 | PASS | Warm-up is an AD-22 observation count (a Duration is refused); the evidence range starts at the first trading instant (warm-up excluded). |
| T21-317 | R18 | **L3 P0** | PASS | The batch is a deterministic function of exactly `(space, seed, priors, generation)`; empty-prior calls agree (no cross-call store); different priors give a different batch (history read from the argument). |
| T21-318 | R19 | **L3 P0** | PASS | The same seeded Study proposes an identical batch when the generation's results are fed in reversed/interleaved completion order (canonical-order metamorphic). |
| T21-319 | R20 | L3 | PASS | A second `ask` before the outstanding generation's `tell` returns `unsupported capability`. |
| T21-320 | R21 | L3 | PASS | A sampler internal float converts through the named AD-7/AD-22 boundary; only the exact int/`ExactRational` value enters identity — no raw float. |
| T21-321 | R22 | **L3 P0** | PASS | `admit_study` resolves + freezes exactly one registry as-of set into the Study label; a post-admission alias resolve refuses, an explicit fingerprint resolves (SC-11). |
| T21-322 | R23 | **L3 P0** | PASS (narrowed) | The trial label carries sampler identity + seed + generator provenance + `study_fp`; a differing optuna major is `unsupported capability`, a matching major re-samples. *(CT-32 byte-repro = Epic 14 — UNPROVEN sub-clause E21-F03.)* |
| T21-323 | R24 | L3 | PASS | Resume reads completed trials from the ledger, resumes the generation index past the last full generation, and never schedules a completed ask to re-run. |
| T21-324 | R25 | L3 | PASS | Resume uses only the ledger view: the repositioned stepper's next `ask` is reproduced byte-for-byte by the pure port over the same conditioned history (no hidden optuna store). |
| T21-325 | R26 | L3 | PASS | With a measured baseline the estimate is `total x runtime // concurrency_cap`, spawning no trial (the governor cap is passed in, not computed). |
| **T21-326** | **R27** | **L3 P0 PIN-2** | **PASS (finding not reproduced)** | With no baseline the estimate is `not-yet-measured` with no synthesized runtime/wall; identity omits the unmeasured figures. *(Peak-memory sub-clause UNPROVEN — E21-F02.)* |
| T21-327 | R28 | **L3 P0** | PASS (narrowed) | Exactly one ledger line per spawned run: an aborted run is kept (never zero); a byte-identical duplicate collapses; a second differing line for one run id is a collision refusal (never two). *(Clean `stopped`-state transition = Epic 15 — UNPROVEN sub-clause E21-F04.)* |
| T21-328 | R29 | L3 | PASS | The report carries per-parameter slices and a mean/std/min/max/median summary matching an independent recomputation over the fed objectives. |
| T21-329 | R30 | L3 | PASS | A winner amid adjacent favourable trials is flagged `stable-cluster`; a lone high winner far from any favourable trial is flagged `isolated-spike` (two constructed cases differentiated). |
| T21-330 | R31 | L3 | PASS | Reading a search-quality verdict out of the report is refused (`policy rejection`); a blank name is `invalid input`; no bare pass/fail verdict value appears in identity. |
| T21-331 | R32 | L3 | PASS | Slice bins cite the exact parameter inputs (data), `canonical_payload = series-data`, and no bytes/image blob is the canonical payload. |
| T21-332 | R33 | L3 | PASS | P&L inputs stay exact-integer; the std is stored as a label-derived scaled rational under a fixed `{rounding,scale}` contract; the whole report identity is float-free. |
| T21-333 | R34 | L3 | PASS | Nine Epic-21 refusal surfaces each RETURN a valid CT-04 value (category in the seven, retryability present, context present/non-null); invalid-input, policy, and unsupported categories all exercised. |

**Traceability:** every requirement R1–R34 maps to at least one test above (R9 covered
by T21-r9; R31 by T21-330). All P0 tests (R4, R16, R18, R19, R22, R23, R27, R28) are
green except the two pins, which are judged on truth: PIN-1 FAIL = confirmed finding,
PIN-2 PASS = finding not reproduced.

---

## Falsifiability notes (HARDENED AUTHOR CONTRACT rule 1)

- **PIN-1 (T21-309)** carries its own discriminator: the *same-currency* companion runs
  first and PASSES (`target_reached` True for a valid USD target), so the failure is
  isolated to the cross-currency case — a real, not vacuous, red.
- **T21-317/318 (purity/order-invariance)** are made meaningful by an in-test
  content-sensitivity witness: *different* prior objectives produce a *different* batch,
  so equality under permutation/repeat is a genuine signal (a hidden store or an
  order-dependent model would break it). Re-verified under `PYTHONHASHSEED` variation.
- **PIN-2 (T21-326)** is discriminated by **T21-325**: the estimator DOES produce a
  concrete wall when a baseline exists, so `not-yet-measured` in the no-baseline case is
  a real distinction, not an "always None."
- **Float-ban scans (T21-305/320/332)** and **byte-payload scan (T21-331)** would fail
  if a single raw float / image blob reached identity; the exact-integer fixtures make
  the absence load-bearing.
- **Refusal assertions** everywhere check a RETURNED `TypedRefusal` of a specific
  category — reaching the assertion proves it was not raised across the boundary.

---

## UNPROVEN / narrowed requirements (scope honesty — rules 5 & 6)

| Req | Clause | Status | Reason / owning epic |
|---|---|---|---|
| R27 | peak-memory estimate = not-yet-measured | **UNPROVEN** (E21-F02) | No memory dimension exists in the Study cost estimator; `min(cpu,memory)` budgeting is the Epic-15 governor (FR-045). The runtime `not-yet-measured` path IS proven (PIN-2 not reproduced). |
| R23 | CT-32 result-fingerprint BYTE reproduction | **UNPROVEN** (E21-F03) | The event-slice loop + CT-32 artifact are Epic 14 (Story 14.7) / Epic 19. Epic-21 proves the trial-label content + the reproduce-or-refuse + optuna-major-bump contract. |
| R28 | clean `stopped`-state terminate transition | **UNPROVEN** (E21-F04) | The one-line-per-run count law IS proven via the read fold; the literal terminate-state transition + the general per-run append primitive are the Epic-15 orchestrator (FR-045). |

## Deferred seams (owned elsewhere — asserted only at Epic-21's boundary, not counted here)

- **Split seal / embargo / knowledge-time / calendar-in-band enforcement + sealed-holdout
  exclusion** (Story 21.3 AC3) -> **qmf-data / Epic 3** (FR-012, CT-11/CT-12). Epic 21
  asserts fingerprint-only split consumption (T21-312/313) and warm-up-as-count (T21-316).
- **Process-per-run spawn, the `min(cpu,memory)` governor + concurrency-cap number** ->
  **Epic 15** (FR-045). The cap is a value passed into T21-325, never computed.
- **Fill/slippage/cost fidelity content, `world=simulated` unlock, taint semantics** ->
  **GAP-0048 / Epic 17**. Only taint *presence* (T21-314) and the refuse-until-GAP-0048
  behaviour (T21-315) are testable now.
- **SR*/search-quality thresholds + pass/fail battery** -> **GAP-0049** (deferred). Only the
  *absence* of any invented threshold/verdict is testable (T21-330), never a value.

## L6 review lane

Not delivered as `L6-REVIEW.md` in this run (this task authored and ran the executable L3
suite). The three structural scans the L6 lane calls for were exercised as concrete L3
assertions instead: determinism/no-ambient-nondeterminism (T21-317/318 under hash-seed
variation), money-path/return-space float ban (T21-305/320/332 recursive identity scans),
and the invented-figure scan (PIN-2 T21-326, R9 T21-r9, no-threshold T21-330). Their
universal (structural) form remains the open L6 deliverable.

---

## Process gap (carried from PLAN §Process Gap)

`_bmad-output/test-artifacts/test-design-qa.md` and `.../test-design/QMX-handoff.md`
are absent from the worktree; the L0–L6 taxonomy, the 8-section template, and the P0/P1
split were reconstructed from the ratified QMB spine and the CT-* contracts. Risk gates
R-001 (PIN-1), R-010 (R28), R-013/R-017 (PIN-2) were taken from the task brief and are
each recorded above. Re-reconcile if those authorities are restored.
