# RESULTS — Epic 7: qmf-indicators (independent QA audit, tier T3)

**Command:** `uv run --with hypothesis pytest qa/tests/epic_07 -q --tb=short` (worktree root)
**Outcome:** **95 passed, 0 failed, 0 errored.** 2 requirements UNPROVEN (recorded below + in `findings.csv`).
**Tests live under** `qa/tests/epic_07/`; `packages/qmf-indicators/` is read-only evidence.
**Reference ground truth:** TA-Lib C 0.7.1 + wrapper 0.7.1 is installed and the import-time
reference-configuration record verifies (`reference_status()` returns `Ok`); the equality law,
restore-equivalence, and the wrapper set are exercised end-to-end against the real reference.

The 38 planned executable test IDs (T7-S1..S5, U1..U4, C1..C4, A1..A24, SCN) are implemented as
95 pytest items (families split / parametrized). Every planned ID is green. T7-REV was run as a
manual requirements-fidelity read (below); T7-PIN = 0 (no confirmed regression to pin).

## Counts

| Bucket | Written | Passed | Failed | Errored | UNPROVEN |
|---|---|---|---|---|---|
| L0 static (T7-S1..S5) | 9 | 9 | 0 | 0 | — |
| L1 units (T7-U1..U4, hypothesis) | 10 | 10 | 0 | 0 | — |
| L2 contract (T7-C1..C4) | 10 | 10 | 0 | 0 | — |
| L3 acceptance (T7-A1..A24) | 62 | 62 | 0 | 0 | — |
| L4 composition (T7-SCN) | 2 | 2 | 0 | 0 | — |
| L6 review (T7-REV) | manual | — | — | — | — |
| **Requirements UNPROVEN** | | | | | **R28; R24/R25 numeric half** |
| **Total pytest items** | **95** | **95** | **0** | **0** | |

## Falsifiability (rule 1) — built-in negative controls + injected counter-cases

Each gate carries a counter-case that makes it fail; several are shipped as assertions:
- **A13 equality** — `test_a13_negative_control_different_series_are_not_equal` reports `False`; an
  injected one-value perturbation of the streamed series was verified to flip the law to `False`.
- **A2 identity** — pruning a *non-existent* key leaves fp1 unchanged while pruning any real element
  changes it (verified), proving the load-bearing test only bites hashed elements.
- **A5 gate-1** — the accept arm (`test_a5_matching_reference_is_accepted`) returns `Ok`; the pin-drift
  and config-drift arms return `unavailable dependency`.
- **A6 wrap-not-reimplement** — injected re-implementation owners (`vwap→SMA`, package-owned `sma`) are
  caught as defects; the clean registry has none.
- **A24 upgrade gate** — the unchanged arm mints nothing; the changed arm mints `previous+1` with evidence.
- **A19 conformance** — the fail-closed control (a config not expressing its concept) is non-expressible.
- **S1/S4 scanners** — verified non-vacuous (26 import roots incl. `qmf.core`; 661 public annotations),
  and confirmed they would flag an injected `qmf.data` import / a `talib` annotation.
- **C4 ULP comparator** — a one-ULP difference is unequal at `ulps=0`, equal at `ulps=1`.

## Per-test result (requirement ids · verdict · meaning)

### L0 — static / structural (T7-S1..S5)
- `test_s1_static_imports_reach_only_qmf_core_and_own_package` — R5, AR-06 — **PASS** — default-deny: no `qmf.*` sibling import in the source graph.
- `test_s1_no_static_vendor_import_crosses_module_top_level` — R5 — **PASS** — `talib` is resolved lazily by name, never statically imported.
- `test_s2_no_bare_timeframe_token_in_public_source` — R13 (vocab half) — **PASS** — the token `timeframe` never appears as an aggregation discriminant.
- `test_s3_no_trading_school_name_in_public_source` — R29 (school half) — **PASS** — no name from the school-name lexicon appears in rule/vocabulary.
- `test_s3_lexicon_is_discriminating_not_vacuous` — R29 — **PASS** — the school-name scan can fire (falsifiability guard).
- `test_s4_no_vendor_type_on_public_signatures` — R11 (structural half) — **PASS** — no `talib`/TA-Lib type on any public signature or dataclass field.
- `test_s5_no_async_or_thread_surface` — component Foundation — **PASS** — no async construct, no `asyncio`/`threading` import.
- `test_s5_health_is_only_on_the_streaming_stateful_class` — R18 boundary — **PASS** — only `StreamingIndicator` exposes `health()`; pure batch types do not.
- `test_s5_no_module_global_indicator_instance_registry` — component Foundation — **PASS** — no global instance registry / ambient-scan surface.

### L1 — minimal unit laws (T7-U1..U4)
- `test_u1_any_binary_float_parameter_is_refused` (hypothesis) — R4 — **PASS** — every binary float on the parameter path is refused `invalid input`.
- `test_u1_exact_rational_parameter_is_accepted_and_leaves_no_float_in_identity` — R4 — **PASS** — a rational is admitted and the whole identity serialises fp1-clean.
- `test_u1_num_den_rational_is_accepted` — R4 — **PASS** — a num/den rational parameter fingerprints.
- `test_u2_mutating_any_required_identity_element_changes_fp1` — R1, R2 — **PASS** — ten of the eleven required elements, mutated at config level, each move fp1.
- `test_u2_alignment_policy_is_present_and_load_bearing_in_identity` — R1 — **PASS** — the single-valued alignment policy is present and hashed.
- `test_u2_byte_identical_config_yields_identical_fp1_and_display_field_is_absent` — R1, R2 — **PASS** — equal config ⇒ equal fp1; no display verdict in identity.
- `test_u3_batch_output_is_full_length_presence_mapped_no_sentinel` (hypothesis) — R12 — **PASS** — for any generated series: full-length, every position presence-mapped, integer values (no NaN).
- `test_u4_warm_up_below_reference_lookback_is_refused` (hypothesis) — R16 — **PASS** — warm-up below the kernel lookback is refused.
- `test_u4_warm_up_window_is_marked_not_ready_never_a_number` (hypothesis) — R16 — **PASS** — every warm-up position is `not_ready`, then `present`.
- `test_u4_warm_up_is_an_integer_count_not_a_duration` — R16 — **PASS** — a float/str warm-up is refused; an integer is accepted.

### L2 — contract adoption + refusal shape (T7-C1..C4)
- `test_c1_valid_record_carries_every_required_identity_element` — R1, R3 — **PASS** — a valid record's fp1 content carries all eleven contract-required elements.
- `test_c1_omitting_a_required_field_at_construction_is_refused` — R3 — **PASS** — a declaration missing inputs/output/modes is refused (contract defect).
- `test_c2_every_boundary_returns_value_or_refusal_never_raises` — CT-04 — **PASS** — malformed inputs across five boundaries RETURN refusals, never raise.
- `test_c2_correlation_id_does_not_cross_the_pure_value_signatures` — CT-16 inv.18 — **PASS** — no pure signature declares `correlation_id`.
- `test_c3_forward_fill_across_the_instant_is_policy_rejection` — R14 — **PASS** — forward-fill/interpolate → `policy rejection`.
- `test_c3_heavy_synchronous_entry_is_unsupported_capability` — R25 — **PASS** — a heavy synchronous entry → `unsupported capability`.
- `test_c3_reference_config_mismatch_is_unavailable_dependency` — R7 — **PASS** — a process-global config drift → `unavailable dependency` (at the assertion seam).
- `test_c3_binary_float_param_is_invalid_input` — R4 — **PASS** — a binary-float parameter → `invalid input`.
- `test_c4_integer_ulp_comparator_default_zero_is_exact` — R19 — **PASS** — a one-ULP difference is unequal at 0, equal at 1.
- `test_c4_equality_law_binds_only_when_both_modes_declared` — R19 — **PASS** — a non-both-modes config refuses the equality law.

### L3 — Story 7.1 identity (T7-A1..A3)
- `test_a1_fp1_is_computed_by_the_single_qmf_core_function` — R1 — **PASS** — fp1 == `fingerprint(config)` == `fingerprint(config.fp1_identity())`; no local hashing.
- `test_a1_equal_declarations_reproduce_the_same_fp1` — R2 — **PASS** — equal declarations share one fp1.
- `test_a1_differing_in_exactly_one_element_yields_a_distinct_fp1` — R2 — **PASS** — a one-element difference mints a distinct fp1.
- `test_a1_fp1_is_the_only_dedup_key` — R1, R2 — **PASS** — fp1 is the identity; ordered-element reorder is a genuine identity change.
- `test_a2_each_required_identity_element_is_load_bearing_in_the_fingerprint` — R3 — **PASS** — dropping ANY of the eleven required elements changes the fingerprint (none stored-but-unhashed).
- `test_a2_identity_element_names_reports_the_declared_element_set` — R3 — **PASS** — `identity_element_names()` is the conformance surface (required + declared optional).
- `test_a3_public_value_types_are_frozen_dataclasses` — R5 — **PASS** — `ConfiguredIndicator` is frozen; assignment raises `FrozenInstanceError`.
- `test_a3_public_seams_are_runtime_checkable_protocols` — R5 — **PASS** — `BatchKernel`/`SupportsFp1Identity` are runtime-checkable Protocols.
- `test_a3_pyproject_declares_every_dependency` — R5 — **PASS** — pyproject declares `qmf-core` and `ta-lib==0.7.1`.
- `test_a3_versions_in_semver_lockstep` — R5 — **PASS** — version is SemVer and never enters fp1 identity.

### L3 — Story 7.2 canonical arithmetic (T7-A4..A7) — GATE 1
- `test_a4_reference_resolves_to_talib_0_7_1_with_lockfile_hashes` — R6 — **PASS** — reference is TA-Lib 0.7.1+0.7.1; uv.lock pins `ta-lib==0.7.1` with sha256 wheel hashes (read, not fabricated).
- `test_a5_pin_drift_returns_unavailable_dependency` — R7 — **PASS** — a resolved-artifact drift → `unavailable dependency` at the assertion seam.
- `test_a5_process_global_config_drift_returns_unavailable_dependency` — R7 — **PASS** — a process-global config drift → `unavailable dependency`.
- `test_a5_matching_reference_is_accepted` — R7 — **PASS** — the accept arm verifies to a package-neutral `ArithmeticReference` (proves the refusal arms non-vacuous).
- `test_a5_package_never_mutates_the_reference_process_global_configuration` — R8 — **PASS** — after resolve, the reference's process-global compatibility (a sink) is unchanged.
- `test_a6_ownership_registry_is_conformant` — R9, R10 — **PASS** — every reference-owned formula names a real reference function; grounded check clean against live TA-Lib.
- `test_a6_a_reimplementation_is_caught_as_a_contract_defect` — R9 — **PASS** — a package-owned formula naming a reference function is caught (FM-5).
- `test_a6_a_package_owned_formula_colliding_with_the_reference_is_caught` — R10 — **PASS** — a package-owned formula the reference implements is caught (must be wrapped).
- `test_a6_reference_owned_formula_requires_the_verified_reference` — R9 — **PASS** — mandatory wrapping: a reference-owned formula refuses under a refused reference; package-owned needs none.
- `test_a7_no_vendor_object_crosses_on_the_success_path` — R11 — **PASS** — every returned object's type module is `qmf`, never `talib`.
- `test_a7_no_vendor_object_crosses_on_the_refusal_path` — R11 — **PASS** — a refusal path returns a CT-04 `TypedRefusal` (qmf), never a vendor object.

### L3 — Story 7.3 batch mode (T7-A8..A12) — GATE 3
- `test_a8_output_is_full_length_index_aligned_no_sentinel` — R12 — **PASS** — real-reference batch is full-length, presence-mapped, integer-valued.
- `test_a8_absent_and_gap_positions_carry_presence_states_not_holes` — R12 — **PASS** — non-present positions are presence states at the same index, never omitted slots.
- `test_a9_different_barspec_is_a_different_configured_identity` — R13 — **PASS** — same values under a different BarSpec are a distinct fp1.
- `test_a9_indicator_never_derives_bar_boundaries_passes_knowable_at_through` — R13 — **PASS** — output knowable-at equals input knowable-at (no derived instants).
- `test_a10_forward_fill_or_interpolation_across_the_instant_is_policy_rejection` — R14 — **PASS** — forward-fill/interpolate → `policy rejection`.
- `test_a10_as_of_returns_last_value_known_at_or_before_the_instant` — R14 — **PASS** — as-of returns the last knowable value; nothing-yet is `not_ready`, not a fill.
- `test_a11_calendar_closed_is_absent_by_schedule_never_a_gap` — R15 — **PASS** — a closed position is `absent_by_schedule`.
- `test_a11_calendar_open_gap_follows_declared_policy_never_silent_fill` — R15 — **PASS** — mark-gap → `gap`; refuse → `policy rejection`; never a silent fill.
- `test_a12_warm_up_below_reference_lookback_is_refused` — R16 — **PASS** — warm-up below the reference lookback is refused.
- `test_a12_warm_up_window_is_marked_not_ready_never_a_number` — R16 — **PASS** — warm-up positions are `not_ready`, then `present`.
- `test_a12_every_sample_carries_a_knowable_at_and_provisional_never_enters_governed` — R16, R17 — **PASS** — samples carry knowable-at; provisional evidence is refused at the governed gate.

### L3 — Story 7.4 streaming + equality + restore (T7-A13..A16) — GATE 2
- `test_a13_streaming_equals_batch_under_the_default_ulp_comparator` — R19 — **PASS** — real-reference streaming ≡ batch over cold-state canonical inputs at ULP 0.
- `test_a13_negative_control_different_series_are_not_equal` — R19 — **PASS** — different series are reported unequal (equality law not vacuous).
- `test_a14_restore_then_n_equals_cold_warm_then_n` — R21 — **PASS** — restore-then-N equals cold-warm-then-N, channel for channel.
- `test_a14_result_from_restored_state_carries_the_snapshot_fingerprint` — R21 — **PASS** — a restored result carries the snapshot fingerprint as an input fingerprint.
- `test_a15_restore_on_a_different_tuple_is_unavailable_dependency` — R22 — **PASS** — cross-OS and cross-build restore both → `unavailable dependency`.
- `test_a16_exactly_one_feeder_a_second_feeder_is_refused` — R18 — **PASS** — a foreign WriterId feeder → `unsupported capability`.
- `test_a16_every_output_carries_its_producing_input_sequence_number` — R18 — **PASS** — outputs carry the per-feeder sequence number (0,1,2…).
- `test_a16_instance_count_scales_with_distinct_configurations_not_consumers` — R18 — **PASS** — two same-config instances share the configuration fingerprint; `health()` exposed.

### L3 — Story 7.5 conformance / benchmark / catalog (T7-A17..A21)
- `test_a17_no_declared_budget_is_heavy_by_default` — R25 — **PASS** — no budget ⇒ heavy by default.
- `test_a17_light_claim_without_a_baseline_is_refused` — R25 — **PASS** — a light claim without a recorded baseline is refused at the gate.
- `test_a17_heavy_synchronous_entry_returns_unsupported_capability` — R25 — **PASS** — a heavy synchronous entry → `unsupported capability`.
- `test_a17_a_fully_proven_light_claim_is_admitted` — R25 — **PASS** — a declared+baselined+benchmark-proven claim yields a light verdict (accept arm).
- `test_a18_two_rungs_and_separate_noop_path_are_distinct` — R24 — **PASS** — two rungs; the no-op path is a distinct value type.
- `test_a18_peak_memory_regression_fails_the_gate_exactly_as_a_slowdown` — R24 — **PASS** — a peak-memory regression fails the gate exactly as a latency slowdown.
- `test_a19_every_register_concept_is_expressible` — R23 — **PASS** — all ten CT-16 concept-walk concepts are expressible as governed configs.
- `test_a19_full_conformance_suite_passes_and_fails_closed` — R23 — **PASS** — the suite passes closed; a non-expressing config fails the check.
- `test_a20_catalog_has_no_ambient_scan_surface` — R26 — **PASS** — no scan/discover/autoload entry point on the catalog.
- `test_a20_extension_identity_is_mandatory_in_every_artifact` — R26 — **PASS** — an artifact missing extension identity is refused; stamping adds both fields.
- `test_a21_graduation_requires_a_research_lineage_edge` — R27 — **PASS** — graduation without a research artifact is refused.
- `test_a21_graduation_cannot_reown_a_core_formula` — R27 — **PASS** — graduating a core-owned formula id is refused (one canonical owner).

### L3 — Story 7.6 first wrapper set + upgrade gate (T7-A22..A24)
- `test_a22_wrapper_set_is_conformant_wrapping_not_reimplementing` — R29 — **PASS** — every wrapper wraps its assigned reference formula (no re-implementation).
- `test_a22_each_wrapper_declares_both_modes_and_passes_the_equality_law` [sma,ema,wma,rsi,mom,roc] — R29, R30 — **PASS (6/6)** — each wrapper is both-modes, warm-up ≥ reference lookback, streaming ≡ batch on the real reference.
- `test_a22_sma_wrapper_passes_restore_equivalence` — R30 — **PASS** — the sma wrapper's restore-then-N equals cold-warm-then-N.
- `test_a22_warm_up_below_reference_lookback_is_refused` — R29 — **PASS** — a wrapper warm-up below the reference lookback is refused.
- `test_a23_wrapper_ships_tests_and_reference_usage_examples` — R31 — **PASS** — `examples/configured_wrapper_set_usage.py` and `tests/test_wrappers.py` ship as tier-1 artifacts.
- `test_a24_output_changing_upgrade_mints_a_format_version_with_evidence` — R32 — **PASS** — an output change mints `previous+1` with before/after evidence; protocol version unchanged.
- `test_a24_identical_output_is_not_a_change_and_mints_nothing` — R32 — **PASS** — identical output mints nothing (the CHANGED arm is not vacuous).

### L4 — composition law (T7-SCN)
- `test_scn_upstream_fingerprint_enters_downstream_identity` — R2 (derived-series), composition — **PASS** — a derived input carries the upstream fingerprint (source-id token, never an Instrument) and it moves the downstream fp1.
- `test_scn_two_hop_batch_equals_two_hop_streaming` — R19, composition — **PASS** — a CT-16→CT-16 two-hop chain's batch result equals its streaming result under the equality law.

### L6 — adversarial requirements-fidelity review (T7-REV)
Run as a full manual read of every module under `packages/qmf-indicators/src/qmf/indicators/` against
the Epic 7 ACs, CT-16 invariants, and the three load-bearing gates. **One substantive gap** surfaced
(R28, below); the rest of the implementation is faithful to CT-16 — canonical arithmetic is provably the
arithmetic used, identity spans the whole configuration and is computed only by qmf-core, presence is
honest, BarSpec is data, and the equality/restore/upgrade laws hold on the real reference. **T7-PIN = 0**
(the one gap is a *missing* clause, recorded UNPROVEN, not a regressing behaviour to pin).

## UNPROVEN requirements (recorded, not worked around)

- **R28 (P1) — stale-evidence refusal for a fanned-out heavy value past its declared maximum age.**
  CT-16 invariant 12 / `enums.refusal_categories` name this refusal, but **no code path in
  `qmf-indicators` produces it and no CT-16 value type carries a maximum-age field** (`stale`/`max age`
  absent from the entire package). It is **also absent from Story 7.5's epics.md acceptance criteria**
  (the AC covers only heavy-by-default and the `unsupported capability` synchronous gate, both tested by
  A17). No falsifiable counter-case is constructible against the package surface. Most likely the max-age
  enforcement lives at the application composition root (out of this epic's package). **observed=UNPROVEN.**
- **R24/R25 (numeric half, P1) — the numeric benchmark rung values / the numeric light-vs-heavy budget.**
  CT-16 records the numeric AD-13 rungs "await first measured baselines" — a **ratified deferred
  measurement**. The light-claim *interface* (A17) and the regression gate incl. peak-memory (A18) are
  tested; a numeric ceiling is **not** asserted because doing so would test an unratified value.
  **observed=UNPROVEN (deferred by ratified reason).**

## §5.2 existing-test reconciliation (R-003) — classification

Read of the shipped suites against the P0/P1 behaviours: `test_ct16_configured_indicator.py` iterates the
**full** identity-element set with both mutation-distinct and content-prune load-bearing checks (not a
hand-picked subset) → **keep**; `test_canonical_reference.py`/`test_batch_mode.py`/`test_streaming_mode.py`
exercise the import-refusal, presence/as-of, and equality/restore laws through the real reference →
**keep**. **No `contradicts` row found**, so no R-003 finding is filed; every P0/P1 behaviour is
additionally re-asserted net-new by the independent suite above (the audit does not rely on the shipped
tests). The high author-written coverage was treated as suspect and independently re-proven, per T3.

## §7 boundaries (out of scope / deferred — logged, not counted as pass or fail)

- **R20** cross-OS/cross-build float bit-identity — **not a gate** (CT-05 inv.6 / CT-16 inv.9). The
  equality law (A13) is same-process/same-build; the tuple-scoping it disclaims is enforced by the
  snapshot scope tuple (A15 cross-tuple restore refusal). The numeric cross-build comparison *artifact*
  is out of scope here.
- **CT-16 → CT-17 consumption** (structure families) — Epic 9 (qmf-structure), defined-unwired. Only the
  CT-16 → CT-16 composition law is tested (T7-SCN).
- **Money-path conversion arithmetic** (exact↔analytic descale/return) — qmf-core (Epic 1). R23's
  price-valued re-entry is tested only as concept-walk *expressibility* (A19).
- **Per-formula numeric correctness against an external oracle** — inherited from the pinned reference by
  construction (wrap-not-reimplement, A6); no fabricated golden number (DEC-0007).
- **L2 depth / footprint-class nested series** — outside the V1 series vocabulary, ungoverned research
  lane by ratified reason.

## Plan-integrity caveat (carried from PLAN §7.7)

`_bmad-output/test-artifacts/test-design-qa.md` and `.../QMX-handoff.md` (the L0–L6 taxonomy and the 15
P0/P1 assertions) are **absent from this worktree** (confirmed; only `planning-artifacts/` exists). The
level scheme, the P0/P1 split, and the risk-gate framing are reconstructed from the ratified corpus and
the task brief. Recorded as an audit-integrity note (`findings.csv` E7-F03), not worked around; reconcile
if those files are restored.
