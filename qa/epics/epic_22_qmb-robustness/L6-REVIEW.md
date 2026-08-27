# Epic 22 — QMB robustness ladder — L6 requirements-fidelity review

**Verdict: GAPS.**

One question was asked of every test: does it assert what the requirement demands, or
what the implementation happens to do? The suite's arithmetic core is genuinely strong —
the carve-out denominator discriminator, the exact OHLC cumulative-sum round-trip, the
independently-recomputed p-values, the order-invariance/path-dependence discriminator, the
only-last-bar-fired look-ahead refusal. But the epic's **firewall** requirements (L20 /
SC-06 / B-4 / B-7) are, in the main, asserted against the module's own self-declared flags,
constants, and single-purpose `refuse_*` constructors. Those are the assertions RESULTS.md
marks **P0 green**, and they are the ones that cannot fail. Two requirements with
constructible independent falsifiers are unasserted entirely, and one confirmed-defect class
(F-22-01) has an uncovered sibling on a second public boundary — which PLAN §8 exit
criterion 6 explicitly charged this review with finding.

Scope confirmed against `_bmad-output/planning-artifacts/epics.md` §"Epic 22": all 33
requirement rows tested belong to Stories 22.1–22.5. No out-of-epic requirement was tested.

---

## 1. Wrong-expectation tests

Fifteen test functions carry at least one banned-shape assertion; six rest on one entirely.
Ranked by how much requirement weight the hollow assertion is carrying.

### 1.1 Wholly hollow — the test cannot fail for any behavioural reason

| Test | Requirement it claims | Why it proves nothing |
|---|---|---|
| `test_t22_327_oos_bar_outcome_is_a_read_time_not_yet_ruled_fold` | 22.5-AC2 (**P0**), SC-06 | `fold_oos_bar_outcome` is `del window; return OOS_BAR_OUTCOME_NOT_YET_RULED` (walkforward.py:869-879). The test asserts `fold_oos_bar_outcome() == OOS_BAR_OUTCOME_NOT_YET_RULED == "not-yet-ruled"` — a function compared against the very constant it returns. Banned shape 2 (self-declared constant; function against itself). Nothing about a *read-time fold over ledger window runs* is observed. |
| `test_t22_309_edge_claim_and_live_money_gate_are_refused` | 22.1-AC6 (**P0**), L20/SC-06 | `refuse_edge_claim` / `refuse_live_money_gate` (contract.py:183, 209) are pure refusal constructors — their entire body is `return policy(...)`. Asserting they return a policy rejection proves the module contains a function that returns a refusal. No edge-claim consumer and no money-gate surface is driven, so no laundering path is closed by this test. |
| `test_t22_325_auto_merge_and_live_world_are_refused` | 22.4-AC6 (**P0**) | Same shape: `refuse_gate_auto_merge`, `refuse_live_result_world` (significance.py:728, 755) are constructors. |
| `test_t22_317_named_refusal_builders_return_the_right_categories` | 22.3-AC3 (**P0**) | Same shape. (Its sibling `test_t22_317_ephemeral_ok_persist_simulated_policy_persist_replay_invalid` **is** genuine — it drives `perturbation_persistence` across three input combinations and discriminates two categories. That test carries the AC; this one is a relabelled duplicate of its refusal arms — banned shape 2, "duplicating another test and relabeling it".) |
| `test_t22_327_in_sample_role_is_trial_and_no_run_carries_a_bar_verdict` | 22.5-AC2 (**P0**), B-4 | Reads `.role` off a `WalkForwardWindow` the test itself constructed — a self-declared attribute, not a ledger sink. The second assertion, `out_of_sample_run.role in (ROLE_TRIAL, ROLE_REPLICATE)`, is near-vacuous: the roster has two members and both satisfy it. No injected ledger recorder observes "exactly one line, role=trial, never a bar verdict". |
| `test_t22_301_module_scope_has_no_bare_mutable_containers` | 22.1-AC1, "no module-global mutable state anywhere" | The scan `continue`s on any name starting with `_` **or** any all-caps name. The two shapes a hidden accumulator actually takes — `_cache = {}` and `CACHE = {}` — are both skipped, so the refusal arm is unreachable for the realistic violation (banned shape: an accept/refuse arm that cannot be reached). Its sibling determinism test does the real work. |

### 1.2 Partly hollow — a genuine assertion carries the test, a self-declaration carries the AC's core clause

| Test | Clause asserted by self-declaration | The falsifier that was available |
|---|---|---|
| `test_t22_312_seed_is_base_plus_index_and_run_reproduces_bit_for_bit` (**P0**) | `scenario_seed(10,3)==13` tests a helper **the shuffle never calls** — shuffle.py:701 inlines `random.Random(base_seed + index)`. The procedure's own derivation is unobserved. | Offset-shift: run at `base_seed=B` and `base_seed=B+1`; scenario *i* of the first must equal scenario *i−1* of the second. Falsifies any non-additive derivation, through the public procedure. |
| `test_t22_312_provenance_records_rng_seed_rule_count_and_window_bounds` | `prov.seed_derivation_rule == SEED_DERIVATION_RULE == "base_seed + scenario_index"` — the result compared to the module's own constant. (The window-bound assertions **are** genuine.) | As above. |
| `test_t22_318_perturbation_reproduces_and_records_full_provenance` | `prov.resampling_scheme == RESAMPLING_SCHEME == "moving-block-bootstrap"`, `prov.block_length == 3` (an echo of the input). **Nothing asserts the resampling is moving-block, or that `block_length` changes any output.** | With block length *k*, each scenario's delta sequence must decompose into contiguous length-*k* runs drawn from the original delta series (perturbation.py:1073-1091 does exactly this); *k*=1 and *k*=*n* must produce structurally different scenarios. This is the mechanic 22.3-AC1 names, and it is untested. |
| `test_t22_320_signal_only_pass_stays_flat_and_mint_attempts_are_refused` (**P0**) | The mint half calls `refuse_signal_pass_act` / `guard_signal_pass` — and `guard_signal_pass` is literally `return refuse_signal_pass_act(action)` (significance.py:277). | The flat half is **genuine** (it drives the real `qmb.runloop.loop.run` with an injected handler). The same seam was available for the mint half: inject a handler that *does* return an intent and observe the loop's outcome. 22.4-AC1's "any attempt to mint … is a typed policy rejection" is unproven. |
| `test_t22_311_shuffle_stays_world_replay_and_stamps_procedure_and_seed` (**P0**), `test_t22_316_perturbation_stays_world_replay_with_robustness_claim` (**P0**) | Absence of persistence is asserted as `label["provenance_kind"] == "procedure-ephemeral"` — a returned flag, not a sink (rule 3 names this explicitly: "state absence-of-effect by observing the sink, not by trusting a returned flag"). | No recording data-room/writer fake owned by the test; no filesystem observation. B-7's "never mints or persists a synthetic market series" is taken on the module's word. |
| `test_t22_307_summary_emits_no_verdict_and_invents_no_alpha` (**P0**) | `summary.emits_verdict is False` is `SUMMARY_EMITS_VERDICT`, a module constant (summary.py:~300). `refuse_pass_fail_verdict("pass")` is a constructor. | The genuine parts survive: the identity-key vocabulary scan, and "no bands invented when none declared". Those should carry the AC; the flag and the constructor should not be counted toward it. |
| `test_t22_330_aggregation_is_a_read_time_view_never_a_merged_run` | `canonical_payload == "series-data"`, `governance_battery_has_ratified_thresholds is False`, `governance_battery_candidates == ("pbo","cscv")`, `is_merged_run is False` — four self-declared markers. | The genuine parts are the sibling's missing-metric refusal and the in/out fold content. "Never a merged run" is a flag, not an observation. |
| `test_t22_319_...`, `test_t22_329_...` | Their `refuse_perturbation_bar_verdict` / `refuse_walk_forward_battery_threshold` halves. | Their other halves (objective-as-data; plan-configurable refusals, window-count mismatch) are genuine and carry the ACs. |

### 1.3 Tests that hold up under the hardened contract

`T22-303` (the `10**scale % denominator` discriminator against `Fraction(0.1)`'s 2⁵⁵ denominator — a real, verified-biting falsifier), `T22-304` (scanner proven able to fail via injected `Money(3.5, …)` before being trusted on the module), `T22-305`, `T22-306` (at-or-beyond recomputed independently, direction flip 11/100 → 90/100), `T22-308`, `T22-310` (order-invariant net_profit vs path-dependent drawdown — a genuine discriminator against resample-with-replacement), `T22-313` (series/no-image), `T22-314`, `T22-315` (exact cumsum reconstruction), `T22-317`-a, `T22-321` (the only-last-bar-fired refusal is the real anti-look-ahead discriminator), `T22-322` (independent p recompute + a re-centring discriminator with a stated margin), `T22-323`, `T22-324`, `T22-326`, `T22-328`, `T22-329`-a, `T22-330`-b, `T22-331`, `PIN-01`, `PIN-02`.

---

## 2. Missed requirements — Epic 22 ACs that no test covers

| # | Requirement (epics.md §Epic 22) | Status |
|---|---|---|
| **M1** | **22.2-AC3** — "the **direction-aware empirical percentile rank of the original result** (lower-is-better for drawdown)". | **Implemented and wholly unasserted.** `ShuffleMetric.observed_favorable_rank` and `_favorable_rank(summary.percentile_rank, direction)` exist (shuffle.py:396-425, 745-759); no test reads them, and no test checks that `max_drawdown` is scored lower-is-better. `T22-313` asserts only chart-series shape. A direction inversion on drawdown — the exact error this clause exists to prevent — passes the suite untouched. Independently recomputable from the scenario distribution the test already holds. |
| **M2** | **22.3-AC1** — "moving-block-bootstraps … (block length is a UI-editable configurable)". | Covered only by the declared string constant and an echoed integer (see §1.2). The block structure and the effect of `block_length` are untested. |
| **M3** | **22.1-AC1** — "RETURNS its result, and **writes no log and no ledger line**". | PLAN §2 maps this to T22-301; **no test observes a log or ledger sink**. Silent narrowing — rule 5 requires an explicit UNPROVEN row; RESULTS.md's T22-301 line drops the clause without one. (A `caplog`/handler observation was trivially constructible; the module imports no `logging`, so it would have passed honestly.) |
| **M4** | **22.2-AC5, 22.3-AC5** — governor fan-out bounded by min(cpu, memory), enqueue-when-full, cancel token, and "exactly one ledger line per run with `role = replicate`, never a bar verdict". | Deferred to Epic 15 in PLAN §7.2 / RESULTS "noted-not-tested" — but **no findings.csv UNPROVEN row** (rule 6). The robustness-side half is in-module and testable: `ROLE_REPLICATE` is imported by shuffle.py:60 and perturbation.py:77 and `refuse_scenario_bar_verdict` exists (shuffle.py:318); no test asserts either. |
| **M5** | **22.5-AC1** — "every read goes through qmf-data split-governed at every boundary (AD-21; FR-012)". | Narrowed to Epic 3 in PLAN §7.5; no UNPROVEN row in RESULTS.md's list or findings.csv. |
| **M6** | **22.4-AC3** — "returns are detrended by their in-sample mean **AND** the rule-return series is re-centred to zero". | Only the composite outcome is tested (T22-322). RESULTS.md notes "detrend-by-mean arithmetic is L1-deferred-by-tier" inside the results table — not as an UNPROVEN row with a reason, as rule 5 requires. |
| **M7** | **Cross-cutting, P0-assertion-3 (CT-04/DEC-0109)** — see §4: an uncovered F-22-01 **sibling** on a second public boundary. | Not pinned. PLAN §8 exit criterion 6 required this review to enumerate them. |
| **M8** | **22.1-AC4** — the primitive's degenerate-input refusals (empty distribution, band probability outside (0,1), off-vocabulary direction). | Implemented (summary.py:211-243) and untested. Minor. |

---

## 3. findings.csv — row-by-row verdict

| Row | Verdict | Basis |
|---|---|---|
| **E22-F01** (P0, OverflowError at the carve-out boundaries) | **GENUINE VIOLATION** | Confirmed in source. `carveout.py:137` and `carveout.py:192` both do `number = float(value)` *before* the `math.isfinite` guard, on a value validated only as `isinstance(value, (int, float))`. `int` is unbounded, so `float(10**400)` raises `OverflowError` across two public boundaries. CT-04/DEC-0109 require a returned typed refusal. The pin asserts the correct behaviour and is correctly left failing. **Under-scoped** — see §4. |
| **E22-F02** (P1, no NFR-11 register entry for Epic-22 designed failures) | **GENUINE VIOLATION**, weak instrument | The gap is real: `qmb/FAILURES.md` carries no Epic-22 entry. But the gate is a keyword-substring proxy, and PLAN §3 promised a check for "an NFR-11 entry (**all six required fields**)". The finding's `expected` column still claims the six-field form the test never checks. The row's own text is honest that a single keyword would satisfy it; the *test* should be re-stated to match what it asserts, or strengthened to the six-field check. |
| **E22-F03** (P1, SC-11 single-frozen-registry-as-of UNPROVEN) | **UNPROVEN, CORRECTLY RECORDED** | The admission invariant genuinely runs through the Epic-13-owned B-15 `RegistryReadPort` and Epic-13/15 fragment materialization. Out of the epic's independent surface under the EPIC-BINDING RULE; the robustness-side fingerprint-not-alias half is separately proven (T22-326/328). Correctly not counted green. |
| **E22-F04** (P2, forward-compat reader sub-clause UNPROVEN) | **UNPROVEN, CORRECTLY RECORDED** | Only `ROBUSTNESS_CONTRACT_FORMAT_VERSION = 1` exists; no format-(N+1) counter-case is constructible without inventing a second format. Correct call, correctly severity-rated. |

**Counts:** 2 genuine violations · 0 wrong expectations · 2 UNPROVEN correctly recorded.

**Rows that should exist and do not** (rule 6: findings.csv records structurally-unprovable-or-unimplemented requirements, `observed=UNPROVEN`): M3 (no-log/no-ledger), M4 (governor + role=replicate ledger line), M5 (split-governed reads), M6 (detrend-by-mean). Each is narrowed in PLAN §7 or in a RESULTS table cell but never reaches findings.csv, so a reader of findings.csv alone sees an epic with two defects and full coverage otherwise.

---

## 4. The uncovered F-22-01 sibling (PLAN §8 exit criterion 6)

Every `float()` / `math.*` call on a caller-supplied magnitude across a public boundary of
`qmb/robustness/` was enumerated. Beyond the two boundaries E22-F01 already pins, one more
carries the identical defect:

**`significance.py:414` — `carved = carve_return_statistic(_RETURN_LABEL, math.log(float(ratio)))`**
inside `next_bar_log_returns`, a public export reachable from `run_significance_gate`.

`ratio` is `Fraction(next_close) / Fraction(prev_close)` built from two `Price` values.
`Price.try_create` (packages/qmf-core/src/qmf/core/exact.py:516-536) accepts **any** int with
no magnitude bound, and `SignalBar.try_create` (significance.py:223-251) guards only
positivity. Two legally-constructed positive bars — closes `1` and `10**400` at the same
scale — make `float(ratio)` raise `OverflowError` out of a public boundary, exactly the
F-22-01 defect class, on a P0 path (the anti-look-ahead return series). No test in the suite
constructs it. This should be added to E22-F01's `test_path`/`requirement_ids` or filed as
E22-F05 at P0.

(`math.log` domain errors are *not* reachable here — `SignalBar` refuses non-positive closes —
and `summarize_distribution` guards the empty distribution. Those two are clean.)

---

## 5. Contract-rule compliance summary

| Rule | Verdict |
|---|---|
| 1 — Falsifiability | **Partial.** Every test names a counter-case in its docstring; several (T22-303, T22-304, T22-306, T22-310) are verified to bite. But six tests' counter-cases are not constructible as written (§1.1), and T22-315's "high/low bounds enforced" arm is unreachable with the tame fixture used (prices 100-107, small deltas — no resampling of that series can push a price non-positive), so the enforcement it claims to prove is untested. |
| 2 — Banned shapes | **Violated.** Self-declared flags/constants as proof of behaviour (`emits_verdict`, `is_merged_run`, `provenance_kind`, `canonical_payload`, `governance_battery_has_ratified_thresholds`, `SEED_DERIVATION_RULE`, `RESAMPLING_SCHEME`); function-against-itself (`fold_oos_bar_outcome`, every `refuse_*` constructor, `guard_signal_pass` → `refuse_signal_pass_act`); one relabelled duplicate (T22-317-b). |
| 3 — Independent observation | **Violated for absence-of-effect.** No test owns an injected sink. Non-persistence, no-ledger-line, and no-log are all asserted through returned flags or not at all. Public surfaces only — that half is respected; no `_helper` is driven. |
| 4 — Fault realism | **N/A** — no third-party failure translation in this epic's owned surface. |
| 5 — Scope honesty | **Violated.** M3, M5, M6 are narrowed or dropped without an UNPROVEN row; the PLAN's own §2 row for "writes no log and no ledger line" is mapped to a test that does not check it. |
| 6 — findings.csv completeness | **Violated.** Four unprovable/narrowed requirements (M3-M6) plus the §4 sibling are absent from findings.csv. |

---

## 6. Required to reach *adequate*

1. Assert **M1** (`observed_favorable_rank`, direction-aware, lower-is-better for drawdown) by independent recompute — the highest-value missing assertion in the epic.
2. Replace the six wholly-hollow tests (§1.1) with observations through injected sinks or the real loop: a minting handler through `qmb.runloop.loop.run`; a recording ledger/writer fake for role and non-persistence; a real read-time fold over window runs rather than the constant.
3. Prove the **moving-block** mechanic and `block_length`'s effect (M2), and the seed derivation via the base-seed offset-shift (§1.2).
4. File the §4 sibling, and add findings.csv UNPROVEN rows for M3-M6.
5. Re-fixture T22-315 with a delta series adverse enough that the positivity/high-low guard must actually fire.

None of this requires touching source. The two recorded findings stand as filed; the gap is
in what the greens are worth, not in what the reds say.
