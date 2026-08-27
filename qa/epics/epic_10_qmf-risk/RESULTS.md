# RESULTS — Epic 10: qmf-risk (Books, BMS & governance)

- Tier: **T1** (highest-scrutiny / highest-damage epic)
- Package under audit: `packages/qmf-risk` (`src/qmf/risk/`) — READ-ONLY evidence
- Test location: `qa/tests/epic_10/` (11 files, one per cluster A–J plus X)
- Run command: `uv run --with hypothesis pytest qa/tests/epic_10 -q --tb=short`
- Authorities: Epic 10 Stories 10.1–10.10 ACs; `docs/contracts/CT-22..CT-32`;
  `constitution.md` L38/L39; `docs/contracts/ct-04-typed-refusal.yaml` +
  `docs/registry/variables.yaml` (`typed_refusal_codes`); scenarios SCN-0006/0008/0010/0011.
  The two authority files named in the task prompt (`test-design-qa.md`,
  `QMX-handoff.md`) are **absent** from the worktree (confirmed by full-tree search);
  the L0–L6 shape and the P0-8/P0-9/R-001/R-009 gates were taken from the task prompt
  and the PLAN, exactly as the PLAN records in its Section 7 blocked-input note.

## Headline

| Metric | Value |
|--------|-------|
| Test functions written | 107 |
| **Passed** | **107** |
| **Failed** | **0** |
| **Errored** | **0** |
| L0 static gates | 5 / 5 pass |
| **FINDINGS filed** | **0** |

`findings.csv` contains its header only — no failing test produced a finding.

Every planned assertion A1–X4 was implemented as an executable, independent test and
**passed against the real, wired source** (no contract in scope turned out to be
genuinely unwired — the "defined-unwired" caveat in the PLAN did not bite; all
Epic-10 modules `admission..versioning` exist and behave). The audit is therefore a
clean, positive verdict: the `qmf-risk` package satisfies the requirement-derived
assertions for Epic 10, including the two P0 invariants and both risk-gate rows.

Author discipline: the assertion for every test was written from the requirement
authorities (the demanded outcome), and construction idioms only were adapted from
the package's own tests. No test was weakened to pass; no source file outside `qa/`
was modified.

## L0 static gates (reported separately, not counted in the 107)

| Gate | Result | Evidence |
|------|--------|----------|
| Money-path float scanner (NFR-02 / R-001) | **PASS** | `test_X3_L0_money_path_float_scanner` — 0 binary-float literals in `qmf-risk` src |
| Ambient-nondeterminism scanner (NFR-02) | **PASS** | `test_L0_no_ambient_nondeterminism_in_qmf_risk` — no `random`/`secrets`/`uuid` imports |
| AR-06 dependency direction | **PASS** | `test_L0_ar06_dependency_direction` + `test_A12_*` — imports only `qmf-core`; imported by nothing |
| ruff | **PASS** | `uv run ruff check packages/qmf-risk/src` → "All checks passed!" |
| pyright-strict | **PASS** | `uv run pyright packages/qmf-risk/src` → 0 errors, 0 warnings |

## Risk-gate rows (must-pass, T1)

| Gate | Statement | Result | Discharged by |
|------|-----------|--------|---------------|
| **R-001** | Mixed unit-kind / currency refuses on the money path — never a silent conversion | **GREEN** | A4, A6, A9, A10, B12, B13, B15, C8, D8, I3, X3 |
| **R-009** | Every door-reachable typed refusal is on the seven-category register | **GREEN** | X1, X2 |

## P0 assertions

| # | Assertion | Result | Discharged by |
|---|-----------|--------|---------------|
| **P0-8** | Every trade intent passes the Book charter doors with R **frozen at admission** and a **declared full-loss price required** | **GREEN** | B2, B3, B4, B6, F1, F3, X4 |
| **P0-9** | **No control ever blocks a risk-reducing act** (exit-preservation, L39) | **GREEN** | H1 (Hypothesis property over kind×authority×scope×act), H2, H8 |

## Per-test results

Legend: every row **PASS**. "Meaning of failure" is populated only for a FAIL — there
are none, so the column reads `—`. Requirement anchors cite Story.AC / CT / L / gate.

### Cluster A — Story 10.1 (template grammar, dimensional law, USD numeraire)

| ID | Test | Requirement anchors | Result | Meaning of failure |
|----|------|---------------------|--------|--------------------|
| A1 | `test_A1_variable_missing_any_of_four_parts_is_invalid_input` | 10.1 AC1, CT-22, CT-27, L38 | PASS | — |
| A2 | `test_A2_unit_kind_is_the_closed_ad40_vocabulary` | 10.1 AC1, AD-40 | PASS | — |
| A3 | `test_A3_binary_float_value_is_refused_on_the_money_path` | 10.1 AC1, CT-01 | PASS | — |
| A4 | `test_A4_dimensional_checker_refuses_a_unit_kind_mismatch` | 10.1 AC2, R-001 | PASS | — |
| A5 | `test_A5_every_ladder_formula_has_a_recomputing_worked_example` | 10.1 AC2 | PASS | — |
| A6 | `test_A6_dead_form_0006_is_rejected_by_the_checker` | 10.1 AC2, R-001 | PASS | — |
| A7 | `test_A7_ui_edit_mints_new_version_never_mutates` | 10.1 AC3, CT-22, L38 | PASS | — |
| A8 | `test_A8_recorded_number_is_non_spine_evidence_with_layer_and_grade` | 10.1 AC3, L38 | PASS | — |
| A9 | `test_A9_usd_is_the_sole_v1_numeraire` | 10.1 AC4, R-001 | PASS | — |
| A10 | `test_A10_book_limit_in_lots_is_policy_rejection` | 10.1 AC4, CT-22, R-001 | PASS | — |
| A11 | `test_A11_version_graph_branches_from_multiple_heads_and_current_pointer` | 10.1 AC5 | PASS | — |
| A12 | `test_A12_qmf_risk_imports_only_qmf_core` / `..._is_imported_by_no_other_package` | 10.1 AC6, AR-06 | PASS | — |

### Cluster B — Story 10.2 (R faces, sizing ladder, full-loss-price law)

| ID | Test | Requirement anchors | Result | Meaning of failure |
|----|------|---------------------|--------|--------------------|
| B1 | `test_B1_r_is_three_typed_faces_with_correct_unit_kinds` | 10.2 AC1, CT-23 | PASS | — |
| B2 | `test_B2_stop_move_never_re_bases_frozen_faces` | 10.2 AC1, P0-8 | PASS | — |
| B3 | `test_B3_protection_amendment_never_re_bases_frozen_faces` | 10.2 AC1, P0-8 | PASS | — |
| B4 | `test_B4_budget_re_derivation_never_re_bases_frozen_faces` | 10.2 AC1, P0-8 | PASS | — |
| B5 | `test_B5_r_multiple_anchors_minus_one_and_zero` | 10.2 AC1 | PASS | — |
| B6 | `test_B6_no_full_loss_price_is_invalid_input_no_admission` | 10.2 AC2, CT-23, P0-8 | PASS | — |
| B7 | `test_B7_scale_in_is_a_policy_rejection` | 10.2 AC2 | PASS | — |
| B8 | `test_B8_money_rules_units_only_and_loss_runway_formula` | 10.2 AC3 | PASS | — |
| B9 | `test_B9_seat_r_ceiling_bound_is_enforced` | 10.2 AC3 | PASS | — |
| B10 | `test_B10_position_risk_amount_is_requested_r_times_r_unit_price` | 10.2 AC3 | PASS | — |
| B11 | `test_B11_loss_floor_is_one_value_read_by_both` | 10.2 AC3, CT-22 | PASS | — |
| B12 | `test_B12_b_split_refuses_a_count_where_an_r_multiple_is_declared` | 10.2 AC4, R-001 | PASS | — |
| B13 | `test_B13_absent_value_factor_is_unavailable_dependency_never_silent` | 10.2 AC5, R-001 | PASS | — |
| B14 | `test_B14_sizing_uses_a_value_factor_not_margin` | 10.2 AC5 | PASS | — |
| B15 | `test_B15_money_r_crossing_names_a_rate` | 10.2 AC6, R-001 | PASS | — |
| B16 | `test_B16_only_r_multiple_averages` | 10.2 AC6 | PASS | — |

### Cluster C — Story 10.3 (three-layer admission, admission bar, blank-blocks-live)

| ID | Test | Requirement anchors | Result | Meaning of failure |
|----|------|---------------------|--------|--------------------|
| C1 | `test_C1_admission_is_three_ordered_layers_ending_in_a_signature` | 10.3 AC1 | PASS | — |
| C2 | `test_C2_no_trial_probation_or_paper_performance_gate` | 10.3 AC1 | PASS | — |
| C3 | `test_C3_admission_requirement_carries_the_four_declared_parts` | 10.3 AC2 | PASS | — |
| C4 | `test_C4_no_composite_may_express_a_bar` | 10.3 AC2 | PASS | — |
| C5 | `test_C5_blank_bar_blocks_live_binds_non_live_freely` | 10.3 AC3, CT-22 | PASS | — |
| C6 | `test_C6_paper_role_bar_gating_live_is_refused_at_layer1` | 10.3 AC4 | PASS | — |
| C7 | `test_C7_worked_examples_recompute_via_cited_producer_only` | 10.3 AC5 | PASS | — |
| C8 | `test_C8_layer1_enforces_unit_kind_coverage` | 10.3 AC5, R-001 | PASS | — |
| C9 | `test_C9_two_kinds_sharing_a_rank_is_invalid_input` | 10.3 AC5, CT-30 | PASS | — |
| C10 | `test_C10_float_measure_needs_a_declared_comparison_rule` | 10.3 AC6, CT-22 | PASS | — |

### Cluster D — Story 10.4 (binding chain, identity trinity, bind-time capability)

| ID | Test | Requirement anchors | Result | Meaning of failure |
|----|------|---------------------|--------|--------------------|
| D1 | `test_D1_binding_tuple_is_five_components_without_role` | 10.4 AC1, CT-28 | PASS | — |
| D2 | `test_D2_identity_trinity_version_instance_and_epoch` | 10.4 AC2 | PASS | — |
| D3 | `test_D3_equal_fingerprint_rebinding_is_invalid_input` | 10.4 AC2, CT-28 | PASS | — |
| D4 | `test_D4_state_carry_is_mandatory_and_complete` | 10.4 AC3 | PASS | — |
| D5 | `test_D5_carry_requires_a_signed_carries_ledger_edge` | 10.4 AC3 | PASS | — |
| D6 | `test_D6_lineage_edges_are_independent` | 10.4 AC3 | PASS | — |
| D7 | `test_D7_missing_required_capability_refuses_at_bind_time` | 10.4 AC4, CT-28 | PASS | — |
| D8 | `test_D8_non_usd_settlement_currency_is_policy_rejection` | 10.4 AC5, CT-28, R-001 | PASS | — |
| D9 | `test_D9_second_book_netted_overlap_needs_shared_flatten_signature` | 10.4 AC6, CT-28 | PASS | — |
| D10 | `test_D10_missing_baselines_are_unavailable_dependency` | 10.4 AC4, CT-28 | PASS | — |
| D11 | `test_D11_contradicting_rank_table_refuses_at_bind` | 10.4 AC4, CT-28, CT-30 | PASS | — |

### Cluster E — Story 10.5 (paper as a dated binding-epoch change; SCN-0006)

| ID | Test | Requirement anchors | Result | Meaning of failure |
|----|------|---------------------|--------|--------------------|
| E1 | `test_E1_book_modes_are_exactly_live_and_paper` | 10.5 AC1, CT-24 | PASS | — |
| E2 | `test_E2_flip_is_dated_epoch_change_and_mode_is_a_fold` | 10.5 AC1, SCN-0006 | PASS | — |
| E3 | `test_E3_paper_mode_selects_the_single_paired_target` | 10.5 AC2, CT-24 | PASS | — |
| E4 | `test_E4_one_active_paper_target_per_binding` | 10.5 AC3, CT-24 | PASS | — |
| E5 | `test_E5_trigger_disposition_routes_or_blocks_recording_not_trading` | 10.5 AC4 | PASS | — |
| E6 | `test_E6_paper_balance_frozen_reset_signed_no_money_boundary` | 10.5 AC5, FR-035 | PASS | — |
| E7 | `test_E7_return_to_live_asymmetry` | 10.5 AC6, CT-24 | PASS | — |
| E8 | `test_E8_scn0006_book_paper_transition_end_to_end` | SCN-0006 (L4 golden) | PASS | — |

### Cluster F — Story 10.6 (risk-evaluation door)

| ID | Test | Requirement anchors | Result | Meaning of failure |
|----|------|---------------------|--------|--------------------|
| F1 | `test_F1_door_two_families_and_no_inbound_requested_r` | 10.6 AC1, CT-23, P0-8 | PASS | — |
| F2 | `test_F2_entry_intent_carries_format1_declaration` | 10.6 AC2 | PASS | — |
| F3 | `test_F3_full_loss_price_derived_at_door_requested_r_book_resolved` | 10.6 AC2, CT-23, P0-8 | PASS | — |
| F4 | `test_F4_v1_exit_kinds_and_tighten_names_no_price` | 10.6 AC3, CT-23 | PASS | — |
| F5 | `test_F5_risk_monotonic_violations_are_policy_rejections` | 10.6 AC4 | PASS | — |
| F6 | `test_F6_adopt_mode_gated_by_format_and_r_stays_frozen` | 10.6 AC5, SC-05 | PASS | — |
| F7 | `test_F7_format1_readable_forever_unknown_field_ignored` | 10.6 AC6, AD-5 | PASS | — |

### Cluster G — Story 10.7 (exit records, close reasons, bench fold; SCN-0011)

| ID | Test | Requirement anchors | Result | Meaning of failure |
|----|------|---------------------|--------|--------------------|
| G1 | `test_G1_one_immutable_exit_record_with_mandated_fields` | 10.7 AC1, CT-29 | PASS | — |
| G2 | `test_G2_realized_r_is_derived_never_a_second_implementation` | 10.7 AC1, CT-29 | PASS | — |
| G3 | `test_G3_close_reason_taxonomy_mechanism_outcome_and_kills_apart` | 10.7 AC2 | PASS | — |
| G4 | `test_G4_whole_trade_attribution_credits_opening_bot` | 10.7 AC3, CT-29 | PASS | — |
| G5 | `test_G5_bench_counts_qualifying_losses_only` | 10.7 AC4, SCN-0011 | PASS | — |
| G6 | `test_G6_recording_precedes_interpretation_stale_evidence` | 10.7 AC5 (L3) | PASS | — |
| G7 | `test_G7_breakeven_ratchet_risk_non_increasing_r_frozen` | 10.7 AC6, CT-29, CT-23 | PASS | — |
| G8 | `test_G8_scn0011_qualifying_loss_bench_end_to_end` | SCN-0011 (L4 golden) | PASS | — |

### Cluster H — Story 10.8 (control actions, exit-preservation, arbitration; SCN-0010)

| ID | Test | Requirement anchors | Result | Meaning of failure |
|----|------|---------------------|--------|--------------------|
| H1 | `test_H1_exit_preservation_never_blocks_a_risk_reducing_act` (Hypothesis) + `..._entries_are_the_only_blockable_half` | 10.8 AC1, CT-30, L39, P0-9 | PASS | — |
| H2 | `test_H2_no_blanket_command_pipe_block_kind` | 10.8 AC1, P0-9 | PASS | — |
| H3 | `test_H3_vocabulary_and_never_auto` | 10.8 AC2, CT-30 | PASS | — |
| H4 | `test_H4_scope_resolution_refuses_never_widens` | 10.8 AC2 | PASS | — |
| H5 | `test_H5_standing_intent_journaled_before_dispatch_and_redecided` | 10.8 AC3, CT-30, SCN-0005 (L3) | PASS | — |
| H6 | `test_H6_kill_switch_vs_kill_line_and_resume_operator_only` | 10.8 AC4 | PASS | — |
| H7 | `test_H7_same_tick_collapse_to_one_command` | 10.8 AC5, SCN-0010 | PASS | — |
| H8 | `test_H8_compose_suspend_new_and_flatten_both_execute` + `..._higher_rank_never_reduces_protection...` (Hypothesis) | 10.8 AC5, SCN-0010, P0-9 | PASS | — |
| H9 | `test_H9_flatten_authority_is_closed` | 10.8 AC6 | PASS | — |
| H10 | `test_H10_scn0010_risk_boundary_conflicts_end_to_end` | SCN-0010 (L4 golden) | PASS | — |

### Cluster I — Story 10.9 (protection windows; SCN-0008)

| ID | Test | Requirement anchors | Result | Meaning of failure |
|----|------|---------------------|--------|--------------------|
| I1 | `test_I1_window_record_shape` | 10.9 AC1, CT-31 | PASS | — |
| I2 | `test_I2_window_blocks_entries_only_live_and_paper` | 10.9 AC2, CT-31 | PASS | — |
| I3 | `test_I3_scope_via_currency_exposure_missing_treated_as_affected` | 10.9 AC3, R-001 | PASS | — |
| I4 | `test_I4_effective_window_is_the_widening_union` (Hypothesis) + `..._narrowing_revision...` | 10.9 AC4, CT-31 | PASS | — |
| I5 | `test_I5_fail_closed_no_skip_no_click_exemption` | 10.9 AC5 | PASS | — |
| I6 | `test_I6_window_forced_flat_rank_two_v1_declares_none` | 10.9 AC6, FR-035 | PASS | — |
| I7 | `test_I7_scn0008_pair_scoped_news_end_to_end` | SCN-0008 (L4 golden) | PASS | — |

### Cluster J — Story 10.10 (risk journals, publish-never-act performance)

| ID | Test | Requirement anchors | Result | Meaning of failure |
|----|------|---------------------|--------|--------------------|
| J1 | `test_J1_entity_journals_are_projections_no_entity_writer` | 10.10 AC1, CT-25 | PASS | — |
| J2 | `test_J2_risk_and_venue_events_join_via_command_fingerprint` | 10.10 AC2, CT-25 | PASS | — |
| J3 | `test_J3_control_action_journaled_before_dispatch_blocks_on_failure` | 10.10 AC3, CT-25 (L3) | PASS | — |
| J4 | `test_J4_role_scoped_projections_no_silent_cross_role_union` | 10.10 AC3 | PASS | — |
| J5 | `test_J5_performance_result_container_shape` | 10.10 AC4, CT-32 | PASS | — |
| J6 | `test_J6_no_composite_single_role_publish_never_act` | 10.10 AC5, CT-32 | PASS | — |
| J7 | `test_J7_bench_fold_governed_producer_replay_never_gates_live` | 10.10 AC6, CT-32 | PASS | — |

### Cluster X — cross-cutting gates and P0 aggregates

| ID | Test | Requirement anchors | Result | Meaning of failure |
|----|------|---------------------|--------|--------------------|
| X1 | `test_X1_every_door_reachable_refusal_is_on_the_register` | R-009, CT-04, CT-22..CT-32 | PASS | — |
| X2 | `test_X2_register_is_exactly_the_seven_categories` | R-009, CT-04 | PASS | — |
| X3 | `test_X3_money_path_value_types_refuse_floats` + `test_X3_L0_money_path_float_scanner` | R-001, CT-01 (L0/L2) | PASS | — |
| X4 | `test_X4_p0_8_admitted_entry_lifecycle_r_frozen_full_loss_required` | P0-8, CT-22/23 (L3) | PASS | — |
| L0 | `test_L0_no_ambient_nondeterminism_in_qmf_risk` | NFR-02 | PASS | — |
| L0 | `test_L0_ar06_dependency_direction` | AR-06 | PASS | — |

## Planned tests not implemented as executable, and why

Every planned ID **A1–X4 was implemented and executed**. The items the PLAN's
Section 7 recorded as untestable were NOT part of the A1–X4 independent list and are
restated here for completeness — each is untestable in this package by ratified
boundary, not by any gap in coverage:

1. **Cryptographic authenticity of operator signatures.** V1 signing is a recorded
   approval with no crypto dependency (CT-22/ADR-0015). Presence and gating semantics
   are covered (C1, D5, E6, E7); authenticity / non-repudiation has no crypto to verify.
2. **Node severity policy** (KSA `trigger→level→effect` matrix, `severity→window`).
   Ruled explicitly OUT of the QMF surface (CT-27/30/31) — it lives in the trading node.
   The QMF-side contract, scopes, refusals and evidence ARE covered (H6, H9, I6).
3. **Alpha-decay mathematics.** Decided-deferred (AD-41); only the evidence primitives
   ship. The primitives are covered (G1/G5, J5, J7 baseline gate); no decay score exists
   to assert.
4. **The not-yet-ruled admission-bar thresholds behind the CT-22/23 format-2 evidence
   fields** (GAP-0048/0049). Blank-blocks-live is covered (C5); the threshold comparison
   has no ruled value to assert against.
5. **A true cross-epic worked-example recompute** invoking the real upstream producers
   (Epic 1/5/6). In-package this is covered with the reference producers (C7); an
   end-to-end recompute across packages is a system-level test outside the Epic-10
   package boundary.
6. **CT-32 reproducibility under an actual QMB replay run** (DEC-0163). Container
   determinism and `world=replay`-never-gates-live are covered in-package (J5, J7);
   reproducing a real QMB run id is COMP-QMB (Epic 13) territory.

## Reconcile note (PLAN Sections 5/8)

The reconcile-against-source pass found **no `blocked-unwired` and no `absent`
requirement**: every Epic-10 contract in scope is implemented and wired through real
`src/qmf/risk/*` modules with a runnable path, so every planned assertion ran against
live code rather than degrading to a coverage FINDING. The `control_action.py`
complexity hot-spot (the arbitration collapse/compose/conflict rules, the
exit-preservation property, scope resolution, flatten-authority closure, and the
standing-intent fold) is exercised by H1, H2, H4, H5, H7, H8, H9, H10 with each branch
tied to a CT-30 / SCN-0010 requirement anchor — no untethered high-complexity branch
was observed.
