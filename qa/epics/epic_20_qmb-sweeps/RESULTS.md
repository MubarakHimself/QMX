# Epic 20 — QMB multi-route sweeps — RESULTS (audit tier T3, author-and-run pass)

Runner: `uv run pytest qa/tests/epic_20 -q --tb=short` from the worktree root.
Outcome: **28 tests, 28 passed, 0 failed, 0 errored.** ~17 s (the Story-20.3 tests
run the REAL never-forked run loop under the REAL orchestrator/governor/ledger —
process-per-run fan-out — via two module-scoped batch fixtures).

Discipline: every assertion is requirement-derived (authored from the Epic-20 ACs,
the B-12/B-15/B-4/B-3 spine, the CT-* contracts, and the constitution — Section 4 of
`PLAN.md` was written before any `qmb/src/qmb/sweep/` file was read). Effects are
observed through returned artifacts, on-disk ledger lines, and RETURNED CT-04
refusals — never a module's self-declared flag. No source was edited; no assertion
was weakened. A failing test would have been recorded as a FINDING.

## Headline: the R-004 / F-20-01 disposition

**F-20-01 ("the sweep drops combinations on an fp1 collision") is NOT reproduced
against the current source.** `PLAN.md` expected `T20-PIN-01` to FAIL; run
independently, **it PASSES**, and so does the full R-004 pair `T20-302` /
`T20-302c`. The no-silent-drop / distinct-identity property is GREEN, proven from
three independent angles:

1. **Write side (`T20-302`, `T20-PIN-01`):** distinct combos → distinct combo
   `fp1` AND distinct *resolved-run-config* `fp1` (the run-id root + ledger key +
   output-dir name). The swept parameter is identity-bearing — it rides into
   `ResolvedRunConfig.keys`, which is in the config's `IDENTITY_FIELDS` — so two
   combos differing *only* in a swept parameter resolve to two distinct run ids
   (`T20-PIN-01`, the sharpest probe: 1 instrument × 1 timeframe × 2 params).
2. **End to end (`T20-PIN-01`, `T20-314`):** a real batch writes exactly one
   ledger line per admitted combo — `admitted-combo count == distinct-run-id count
   == ledger-line count` — never zero (a drop), never two (a double). A dropped
   combo would surface here as a missing line; none is.
3. **Read side (`T20-302c`):** the read-time fold's substrate `merge_ledger_lines`
   REFUSES-and-ALARMS on a *true* collision (same `run_id`, differing identity
   bytes) per CT-05/AR-51 (`policy rejection`, `context["alarm"] is True`) and
   collapses a byte-identical idempotent duplicate — never a silent overwrite.

A residual is recorded honestly (see **E20-F02**): the batch driver's own write-side
keying dictionaries (`_by_run_id`, `_outcomes` in `batch.py`) carry no *explicit*
CT-05 true-collision guard; a genuine `fp1` hash collision on those keys would
overwrite silently. That path is **UNPROVABLE through public inputs** (a real
SHA-256 collision cannot be constructed without editing source), so per author-rule
5 it is filed UNPROVEN rather than green — even though the observable collision
paths (merge + the report's missing-outcome refusal) both refuse loudly.

## Coverage ledger — one row per planned check

| Test id | Test function | Req | Level | Status | Meaning (one line) |
|---|---|---|---|---|---|
| T20-301 | test_t20_301_expansion_is_full_cartesian_product_and_unit_scale | R1 | L3 | PASS | Expansion is the full Cartesian product in deterministic declaration order; 1×1×1 → one run spec. |
| T20-302 | test_t20_302_distinct_combos_have_distinct_run_and_config_fingerprints | R2/R-004 | L3 | PASS | Distinct combos → distinct combo `fp1` AND distinct resolved-config `fp1`; none collapses. |
| T20-302c | test_t20_302c_true_collision_refuses_and_alarms_never_overwrites | R2/R-004 | L3 | PASS | A true `run_id` collision refuses-and-alarms (CT-05/AR-51); a byte-identical dup collapses. |
| T20-303 | test_t20_303_preflight_count_is_the_product_and_a_pure_inspection | R3 | L3 | PASS | Pre-flight count = product of axis lengths; a 1e9-combo count returns instantly (pure inspection, no spawn/expand). |
| T20-304 | test_t20_304_door_count_equals_library_and_the_logic_lives_once | R4 | L3 | PASS | The CLI/API door returns the library count; `api.preflight_run_count IS` the library fn (logic lives once). |
| T20-305 | test_t20_305_empty_axis_is_a_typed_invalid_input_naming_the_axis | R5 | L3 | PASS | An empty instrument/BarSpec/param-value axis → RETURNED `invalid input` naming the axis. |
| T20-306 | test_t20_306_exact_values_verbatim_money_converts_float_refused | R6 | L3 | PASS | int/categorical/bool verbatim; money/rational cross a named AD-7/AD-22 conversion; a bare float is refused. |
| T20-306b | test_t20_306_conversion_without_rounding_and_scale_is_refused | R6 | L3 | PASS | A money conversion without a declared rounding mode + target scale is refused. |
| T20-307 | test_t20_307_admission_resolves_one_frozen_as_of_through_one_port | R7 | L3 | PASS | Admission binds exactly one as-of (instant + set fingerprint) — the live port's — and freezes it; no second cache. |
| T20-308 | test_t20_308_one_as_of_is_frozen_for_every_combination | R8 | L3 | PASS | Every combo resolves the identical Book/BMS/bot `fp1`; every run label carries the identical frozen as-of stamp. |
| T20-308b | test_t20_308_a_fresher_as_of_mid_batch_changes_no_combination | R8 | L3 | PASS | Recompile is byte-identical; a fresher superseding as-of grown on the hub never reaches the frozen port. |
| T20-309 | test_t20_309_after_admission_resolution_is_by_fp1_never_name_at_latest | R9 | L3 | PASS | The frozen port refuses aliases / `name@latest`; the compiled config cites the bot by the admission `fp1`. |
| T20-310 | test_t20_310_superseded_context_reference_is_a_stale_evidence_refusal | R10 | L3 | PASS | Citing a superseded Book → RETURNED `stale evidence`; severity is the configured key (no invented default); neither version bound. |
| T20-311 | test_t20_311_registry_as_of_is_verbatim_in_every_combo_ct32_label | R11 | L3 | PASS | The frozen `registry_as_of` is verbatim in every combo's resolved config and lands in its CT-32 label set. |
| T20-312 | test_t20_312_each_combo_is_one_isolated_run_with_its_own_output_dir | R12 | L3 | PASS | Each combo = one resolved config (`fp1` = run id) run as one isolated process with its own output dir (4 distinct). |
| T20-313 | test_t20_313_concurrency_never_changes_result_or_ct32 | R13 | L3 | PASS | Serial (cpu=1) vs concurrent (cpu=4) dispatch yields identical report identity and identical CT-32 fingerprints. |
| T20-314 | test_t20_314_exactly_one_ledger_line_per_combo_with_full_payload | R14/R-010 | L3 | PASS | admitted-combo count == ledger-line count (never 0/2); each line carries label + CT-32 fp + AD-40 measures + `{sweep_id,instrument,bar_spec,param_hash}`. |
| T20-315 | test_t20_315_a_combo_refusal_is_its_line_and_the_batch_continues | R15 | L3 | PASS | One combo's stream-set violation is its own aborted line with refusal context; the batch completes the survivors. |
| T20-315b | test_t20_315_run_over_budget_is_each_combos_refused_line | R15 | L3 | PASS | A never-admissible peak makes every combo a refused line and STILL returns a complete report — none dropped. |
| T20-316 | test_t20_316_world_derives_from_provenance_and_no_edge_is_claimed | R16 | L3 | PASS | recorded→replay; caller-declared world refused; replay+synthetic-tainted refused; simulated governed-evidence refused; optimistic-taint edge claim refused; ledger lines carry no verdict. |
| T20-317 | test_t20_317_ranks_by_objective_and_reads_only_this_sweep_world_role | R17 | L3 | PASS | Read-time ordering by `measure_identity`; reads only this `sweep_id`; never mixes worlds/roles; objective = the exact input measure (no recomputation). |
| T20-318 | test_t20_318_constraint_value_is_caller_supplied_no_threshold_invented | R18 | L3 | PASS | No-constraint ranks all (no baked default); a caller `max_drawdown≤0.20` holds out the violator; a binary-float threshold is refused. |
| T20-319 | test_t20_319_ranking_publishes_and_never_acts | R19 | L3 | PASS | Every forbidden act (size/promote/…) refused (policy); composite objective refused; ranked combos carry taint+world; no edge/verdict/score in identity. |
| T20-320 | test_t20_320_refused_and_incomplete_combos_excluded_but_reported_never_zeroed | R20 | L3 | PASS | An aborted (no-measures) and an undefined-objective combo go to the incomplete list with reasons — excluded from ranking, never zeroed. |
| T20-321 | test_t20_321_recomputation_is_deterministic_and_reproducible | R21 | L3 | PASS | Ranking is order-invariant and byte-identical on recompute; direction flips best/worst but stays a pure fold. |
| T20-322 | test_t20_322_every_epic20_refusal_is_a_returned_ct04_value | R22 | L3 | PASS | Six Epic-20 refusal surfaces each RETURN a `TypedRefusal` (not an exception), category ∈ the seven, context non-empty. |
| T20-323 | test_t20_323_role_discriminant_and_confirmation_only_fold | R23 | L3 | **UNPROVEN (structural PASS)** | The role is one of `{confirmation,trial,replicate,aborted}` and the Book-bar fold selects confirmation only — but WHICH role a plain sweep combo takes is an OPEN operator-ruling item (see E20-F01); not asserted/invented. |
| T20-PIN-01 | test_t20_pin_01_two_combos_differing_only_in_a_param_are_not_dropped | R-004 | L3 | **PASS** | F-20-01 probe: two combos differing only in a swept param → two distinct run ids + two distinct ledger lines end to end. **F-20-01 not reproduced.** |

**Totals — 28 tests: 26 unqualified PASS · 1 PASS-but-records-UNPROVEN-requirement
(T20-323 / R23) · 1 PASS that closes the named finding F-20-01 as NOT reproduced
(T20-PIN-01).** Failing tests: 0. Errored: 0.

Requirement → status roll-up (the 23 owned requirements):
- **Green (21):** R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13, R14, R15,
  R16, R17, R18, R19, R20, R21, R22 — (that is 22; R2's write+read observable core
  is green, its batch-driver-keying sub-clause is the E20-F02 residual).
- **UNPROVEN (1):** R23 (open operator-ruling item — E20-F01).
- **Partial-narrowing residual (1):** R2/R-004 batch-driver write-side collision
  guard (E20-F02).

## Findings (see `findings.csv`)

- **E20-F01 — R23 sweep-combo ledger role is UNRATIFIED, and the source silently
  defaults it to `confirmation` (bar-eligible).** B-12 gives each sweep combination
  a ledger line but assigns NO role; B-4 names `trial`/`replicate` for optimize/MC/
  walk-forward and `confirmation` for Book-declared-adapter runs, and is silent on a
  plain sweep combo. `run_sweep_batch(..., role=ROLE_CONFIRMATION)` defaults every
  combo to `confirmation`, i.e. **bar-eligible under the confirmation-only fold** —
  which is exactly the unratified choice. Whether a sweep combo should be `trial`
  (exploration, never bar-eligible) or `confirmation` is **not settled by Epic-20's
  ACs or the ratified spine**. Recorded UNPROVEN and **escalated to the operator**;
  not invented. `T20-323` asserts only the structural discriminant + confirmation-
  only-fold property.
- **E20-F02 — R2/R-004: the batch driver's write-side keying carries no explicit
  CT-05 true-collision guard.** `_BatchDriver._by_run_id[config.fingerprint.value]`
  and `_outcomes[combo_fp1.value]` (`batch.py`) assign into dicts with no
  "`if key in map: refuse-and-alarm`" — a genuine `fp1` collision would silently
  overwrite. The clause is UNPROVABLE through public inputs (a real SHA-256
  collision can't be built without editing source), so it is filed UNPROVEN per
  author-rule 5. Mitigating (and tested green): the *read-side* `merge_ledger_lines`
  DOES refuse-and-alarm on a true collision (`T20-302c`), and the batch `_report`
  loudly refuses if any admitted combo lacks an outcome (so a config-fp collision
  would surface as a refusal, not a silent drop). Residual severity: low.
- **E20-F03 — PLAN-INTEGRITY: two named authorities are absent from the worktree.**
  `_bmad-output/test-artifacts/test-design-qa.md` and
  `_bmad-output/test-artifacts/test-design/QMX-handoff.md` — named as the sources of
  the L0–L6 architecture, the Per-Epic template, the 15 P0/P1 assertions, and this
  epic's risk-gate rows — do not exist (`_bmad-output/test-artifacts/` is absent).
  The L-level scheme and the R-004/R-010 gates were reconstructed from
  `LENS-TEST-STRATEGY`, the sibling epic plans, and the task brief. Informational;
  reconcile if those files are supplied.

## UNPROVEN / deferred / out-of-scope (recorded, not silently passed or failed)

- **R23 sweep-combo ledger role — UNPROVEN, open operator-ruling item (E20-F01).**
  Escalated; not invented. Only the structural discriminant is asserted.
- **CT-05 batch-driver write-side collision guard — UNPROVEN (E20-F02).** No public
  injection point for a real hash collision; the observable collision paths are
  green.
- **T3 tier scope — L0/L1/L2/L4/L5 independent suite DEFERRED-BY-TIER** (PLAN §7.8),
  not a coverage gap: the hypothesis breadth over expansion/ranking (L4), the
  pure-unit Cartesian/`param-hash` enumeration (L1), the real-port/real-ledger
  integration (L2), the end-to-end governed sweep (L5), the no-second-cache /
  no-composite-score static scans (L0), and mutation sensitivity are the T1
  treatment. Each P0/P1 *behaviour* they would prove is pinned once at L3 above.
- **Seam-owned, tested only at the sweep boundary (PLAN §7.1–7.6):** the governor /
  process-per-run / WriterId ledger physics (Epic 15); the B-2 loop + CT-32 artifact
  + fingerprint engine (Epic 14/19); as-of-set construction + hub write-back
  (Epic 2); qmf-data provenance derivation (Epic 3); the measure-roster arithmetic
  (Epic 19/qmf-risk). Epic 20 consumes these through real seams; it does not
  re-verify their internals.
- **GAP-0048/0049-gated content — DEFERRED by seam (PLAN §7.5):** the per-combo
  unbiased pass/fail verdict, the multiple-comparisons statistic, and the
  `world=simulated` unlock ship no ratified value. Only the *discipline* is testable
  now and is green: optimistic taint carried forward, no verdict emitted
  (`T20-319`), no threshold invented (`T20-318`), `world=simulated` refuses
  (`T20-316`).

## L6 independent review

Delivered as `L6-REVIEW.md` (PLAN §4.5 / exit criterion 7). It reads
`axes.py` / `admit.py` / `batch.py` / `rank.py` against the B-12/B-15/B-4/B-3 spine
and the firewalls, confirms the exact (non-)mechanism of F-20-01, enumerates every
public-boundary `raise`, and confirms the sweep-combo role is genuinely unspecified.
Its findings are folded into `findings.csv` above (E20-F01, E20-F02).
