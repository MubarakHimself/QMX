# RESULTS — Epic 11: QML authoring

- Tier: **T2** (contract-surface-heavy authoring epic; no live money at trade time)
- Package under audit: `qml` (`qml/src/qml/`) — READ-ONLY evidence. (Story 11.7's
  CT-22/CT-23 format-2 delta is qmf-risk-owned; only that delta was reached, never the
  base CT-22/CT-23 door behaviour, which is Epic 10.)
- Test location: `qa/tests/epic_11/` (8 files: A scaffold, B family, C logic, D footprint,
  E confluence, F bot, G format-2, X cross-cutting; plus `helpers.py`, `conftest.py`)
- Run command: `uv run --with hypothesis pytest qa/tests/epic_11 -q --tb=short`
  (hypothesis is not in the base dev group; `--with hypothesis` is required)
- Authorities: Epic 11 Stories 11.1–11.7 ACs; `docs/contracts/ct-33-bot-definition.yaml`,
  `ct-34-confluence.yaml`, `ct-04-typed-refusal.yaml`, `ct-22-book-charter.yaml`,
  `ct-23-risk-evaluation.yaml`; `constitution.md` L11; the R-009 / R-011 gate rows from the
  task prompt. The two authority files named in the prompt (`test-design-qa.md`,
  `QMX-handoff.md`) are **absent** from the worktree (full-tree search confirms
  `_bmad-output/test-artifacts/` does not exist) — the PLAN records this as a blocked input;
  the L0–L6 shape and R-009/R-011 were taken from the prompt as the PLAN states.

## Headline

| Metric | Value |
|--------|-------|
| Test functions written | 70 |
| **Passed** | **67** |
| **Failed** | **3** |
| Errored | 0 |
| UNPROVEN requirements recorded | 3 |
| **FINDINGS filed (failing tests + UNPROVEN)** | **6** (E11-F01…E11-F06) |

All 3 failures are **genuine spec-vs-code findings**, not test-code errors (the initial
run surfaced 5 reds; 2 were test-code bugs — a wrong module-home location and an
idempotent-registrar false assumption — fixed without weakening any assertion; the
remaining 3 reproduce against the real, wired source). No source file outside `qa/` was
modified; no test was weakened to pass.

## Falsifiability posture (HARDENED AUTHOR CONTRACT)

- Every assertion names its concrete counter-case (in the test docstring). Property tests
  ship a companion **non-vacuity** check (e.g. `test_c2_c3_discrimination_is_real_not_vacuous`,
  the D6/E4 "changed value forks identity" arms) so a green is never hollow.
- Effects are observed through **test-owned sinks**: the real `Registrar` (F1 header
  carve-out is read off the derived `stable_id`, not a returned flag), a `_RecordingRegistrar`
  subclass (F7 observes the host's writer/sequence reaching the sink), and the real qmf-risk
  `ExitPolicy` surface (B3 is resolved through the ratified law, not qml's self-declared map).
- Fingerprint expectations are **recomputed through qmf-core fp1**, never a literal hash;
  refusal expectations assert a **CT-04 category value**, never error prose.
- The two static scanners (A4 import-legality, A5 AD-15 purity) are **self-verified to fail**
  on a synthetic violating snippet before being trusted over the real tree.

## Per-test results

### A — Scaffold, purity, dependency stance, tunnel (Story 11.1)

| Test | Req | Result | Meaning |
|------|-----|--------|---------|
| a1_dependencies_are_qmf_only | 11.1 AC1 | PASS | qml depends only on qmf-core/registry/risk; no qmf-venue, no extra runtime dep |
| a2_no_console_scripts | 11.1 AC2 | PASS | qml ships no CLI entry point |
| a2_seven_named_module_homes_present | 11.1 AC2 | PASS | the seven named homes are present (5 in src, examples/+tests/ at root) |
| a2_no_source_home_beyond_the_seven | 11.1 AC2 | **FAIL → E11-F01** | src/qml also ships `host/` and `logic/` — the "exactly seven" clause is not met |
| a4_scanner_can_detect_qmf_venue | 11.1 AC3 | PASS | the import scanner provably flags a synthetic qmf-venue import |
| a4_no_qml_module_imports_qmf_venue | 11.1 AC3, AR-60 | PASS | no qml module imports qmf-venue |
| a5_scanner_can_detect_impurity | 11.1 AC4 | PASS | the AD-15 scanner provably flags synthetic threading/open() |
| a5_no_qml_module_spawns_process_or_io | 11.1 AC4, AD-15 | **FAIL → E11-F02** | `qml/host/runner.py` imports subprocess + calls open() |
| a5_epic11_authoring_homes_are_pure | 11.1 AC4, AD-15 | PASS | the Epic-11 authoring homes (declaration/families/footprint/logic/protocol) are pure |
| a3_conformance_package_is_pure | 11.1 AC2, AD-15 | PASS | conformance/ spawns no process and does no I/O |
| a6_ungoverned_tunnel_open_without_ticket | 11.1 AC5 | PASS | tunnel access is granted with no conformance ticket; citation is gated, tunnel stays open |
| a7_semver_never_enters_fp1 | 11.1 AC1 | PASS | qml.__version__ appears in no authored artifact's identity payload |
| a7_declared_package_version_field_refused | 11.1 AC1 | PASS | a package_version identity field is invalid input |

### B — Strategy-family metadata (Story 11.2)

| Test | Req | Result | Meaning |
|------|-----|--------|---------|
| b1_family_id_resolves_to_dated_ct06_record | 11.2 AC1, CT-06 | PASS | a minted family is a dated CT-06 record whose body is only `family_id` |
| b2_family_has_no_constraint_powers | 11.2 AC2 | PASS | constraint_powers() is empty; permitted-timeframes/feature-families/mutations are policy-rejected |
| b3_family_id_keys_ratified_qmf_risk_exit_policy | 11.2 AC3 | PASS | the id resolves the per-family ExitLogicRef through the REAL qmf-risk ExitPolicy; a wrong id refuses |
| b4_unresolvable_family_is_unavailable_dependency | 11.2 AC4, R-009 | PASS | a missing family is `unavailable dependency`, journaled, never a silent pass |

### C — Reproducible source-manifest logic identity (Story 11.3)

| Test | Req | Result | Meaning |
|------|-----|--------|---------|
| c1_source_manifest_fp1_form | 11.3 AC1, AR-63 | PASS | the source-manifest fingerprint is `fp1:sha256:<64 hex>` |
| c2s_hashes_only_through_qmf_core | 11.3 AC1 | PASS | qml computes the manifest fp only by calling qmf-core fp1 (seam) |
| c2_build_bytes_never_enter_identity (property) | 11.3 AC2 | PASS | wheel/dist-info/__pycache__ bytes vary by stamp; the Bot fp1 is invariant |
| c3_one_char_source_change_mints_new_bot (property) | 11.3 AC3 | PASS | a one-character source change forks the Bot fp1 |
| c2_c3_discrimination_is_real | 11.3 AC2/AC3 | PASS | non-vacuity: build bytes do NOT move identity, a real source byte DOES |
| c4_unresolvable_logic_is_unavailable_dependency | 11.3 AC4, R-009 | PASS | a missing logic distribution is `unavailable dependency` |

### D — Footprint, templates, horizon (Story 11.4) — R-011

| Test | Req | Result | Meaning |
|------|-----|--------|---------|
| d1_resolution_deterministic_order_independent | 11.4 AC1, R-011 | PASS | one assignment → one fp regardless of extra/ordered keys |
| d1_resolution_total_missing_value_refuses | 11.4 AC1, R-011 | PASS | a space-bound value with no assignment is invalid input (totality) |
| d1_resolution_single_valued_injective (property) | 11.4 AC1, R-011 | PASS | distinct values → distinct fps, equal → equal (injective) |
| d2_omitted_ad22_field_is_layer1_refusal | 11.4 AC2, R-011/R-009 | PASS | dropping ANY AD-22 identity field → invalid input, layer=1 |
| d3_completeness_reports_set_equality | 11.4 AC3 | PASS | the module REPORTS complete/missing/extra; it never refuses (Epic-12 linter's job) |
| d4_horizon_derived_from_chain | 11.4 AC4 | PASS | warm-up/embargo is derived from the resolved chain (changes with the chain) |
| d4_hand_declared_window_refused | 11.4 AC4 | PASS | a hand-declared warm_up_horizon/embargo/horizon window is invalid input |
| d5_stream_set_nested_missing_refuses | 11.4 AC5 | PASS | the stream set is nested; a missing stream_set is invalid input |
| d5_try_create_refuses_second_top_level_field | 11.4 AC5 | PASS | the positional factory refuses a second top-level field |
| d5_try_from_mapping_refuses_second_field | 11.4 AC5 | **FAIL → E11-F03** | the mapping factory silently IGNORES a second top-level field instead of refusing |
| d6_coercion_order_stable | 11.4 AC1, R-011 | PASS | equal inputs coerce to one fp any input order; a changed value forks it |

### E — CT-34 confluence (Story 11.5) — FR-049

| Test | Req | Result | Meaning |
|------|-----|--------|---------|
| e1_each_role_validates_zero_legs_refuses | 11.5 AC1 | PASS | level/trigger/confirmation/filter validate; a zero-leg confluence is invalid input |
| e1_leg_role_is_mandatory | 11.5 AC1 | PASS | a role-less leg is invalid input |
| e2_binding_child_or_both | 11.5 AC2, DEC-0185 | PASS | binding-only, child-only, and BOTH validate; neither is invalid input |
| e3_default_ordering_fingerprint_ascending | 11.5 AC3 | PASS | reorder+ordinals give one fp; display ordinal excluded; order-sig opt-in forks fp |
| e4_reuse_is_content_identity | 11.5 AC4 | PASS | reuse mints no new fp; a changed role/binding/param/order-sig always forks it |
| e5_off_vocab_role_and_missing_cite_invalid | 11.5 AC5, R-009 | PASS | an off-vocab role and a condition ("when") key are invalid input |
| e5_unresolvable_producer_or_child_unavailable | 11.5 AC5, R-009 | PASS | an unresolvable producer fp / cited child is `unavailable dependency` |
| e6_leg_counts_never_bounded (property) | 11.5 AC1, DEC-0185 | PASS | N level + M trigger legs (to 40+40) all validate; no ceiling |
| e6_nesting_depth_never_bounded (property) | 11.5 AC1, DEC-0185 | PASS | confluence composition nests to any depth; no ceiling |

### F — CT-33 Bot definition identity + versioning (Story 11.6) — FR-047

| Test | Req | Result | Meaning |
|------|-----|--------|---------|
| f1_ad16_header_excluded_from_identity | 11.6 AC1, CT-33 | PASS | two sandboxes (differing writer/sequence/created_at) derive one stable_id |
| f1_each_semantic_group_enters_identity | 11.6 AC1, CT-33 | PASS | varying any of the six groups forks fp1 (sensitivity) |
| f2_variable_missing_unit_kind_invalid | 11.6 AC2 | PASS | a unit-kind-less variable is invalid input |
| f2_variable_missing_default_invalid | 11.6 AC2 | PASS | a default-less variable is invalid input |
| f2_all_four_parameter_types_validate | 11.6 AC2 | PASS | exact integer/rational/categorical/boolean all admissible |
| f3_family_cardinality_exactly_one | 11.6 AC3, AD-17 | PASS | zero or two family ids is invalid input |
| f3_confluence_set_one_or_more_ordered | 11.6 AC3 | PASS | zero is invalid; canonical order is child-fp ascending |
| f4_permitted_intents_subset_entry_never_listed | 11.6 AC4 | PASS | subset of close_full|tighten; empty legal; "entry"/"close_partial" refused |
| f4_no_sizing_venue_or_exit_logic | 11.6 AC4 | PASS | exit_logic/requested_r/venue_command/sizing fields are invalid input |
| f5_canonical_assignment_is_derived_locus | 11.6 AC2 | PASS | defaults projection == canonical assignment; a declared field is refused |
| f6_versioning_multiple_heads_dated_current | 11.6 AC5, AD-30 | PASS | branches-from multi-head; dated current pointer history; re-add refused |
| f6_occurrence_facts_never_mint_new_bot | 11.6 AC5 | PASS | seat/paper/rebinding fields are invalid input (not identity) |
| f7_qml_returns_content_only_root_stamps | 11.6 AC6, AD-25 | PASS | mint returns a BotDefinition; the host writer/sequence reach the recording sink |
| f7_register_refusal_seen_through_sink | 11.6 AC6 | PASS | a bad writer comes back as a typed refusal, not an exception |

### G — CT-22/CT-23 format-2 delta (Story 11.7)

| Test | Req | Result | Meaning |
|------|-----|--------|---------|
| g4_format1_reader_refuses_format2_ct23 | 11.7 AC4, R-009 | PASS | a format-1 reader confronting a format-2 artifact refuses `unsupported capability` |
| g4_unknown_ct23_version_unsupported | 11.7 AC4, R-009 | PASS | an unknown CT-23 version is `unsupported capability`, never best-effort |
| g1a_exit_policy_catch_all_format2_only | 11.7 AC1 | PASS | the exit_policy catch-all lands only through the format-2 mint; a format-1 exit_policy refuses it |
| g4_unknown_exit_policy_version_unsupported | 11.7 AC4, R-009 | PASS | an unknown exit_policy version is `unsupported capability` |
| g3a_format1_exit_policy_stays_readable | 11.7 AC3, AD-5 | PASS | a pre-mint format-1 exit_policy stays readable and resolves |
| g5_not_yet_ruled_passes_registration | 11.7 AC5 | PASS | a not-yet-ruled footprint requirement constructs and binds non-live freely |
| g5_not_yet_ruled_blocks_live_binding | 11.7 AC5 | PASS | a blank requirement binding to a live account is `policy rejection` |
| **G1 "exactly three and nothing more"** | 11.7 AC1 | **UNPROVEN → E11-F04** | negative/whole-surface claim; not runtime-falsifiable; constant-assertion is banned |
| **G2 advisory_stop_proposal field-carrying** | 11.7 AC2 | **UNPROVEN → E11-F05** | needs Epic-10 EntryIntent door fixtures (narrowed) |
| **G3 CT-23 intent back-compat (intent half)** | 11.7 AC3 | **UNPROVEN → E11-F06** | needs Epic-10 EntryIntent door fixtures (narrowed); CT-22 half proven via G3a |

### X — Cross-cutting gates

| Test | Req | Result | Meaning |
|------|-----|--------|---------|
| x1_every_refusal_on_seven_register | R-009 | PASS | every qml authoring refusal is a member of the seven-category CT-04 register |
| x2_only_four_declared_categories | R-009 | PASS | qml emits exactly {invalid input, unsupported capability, unavailable dependency, policy rejection}; never the other three |
| x3_coerce_refusals_requirement_anchored | R-011 | PASS | _coerce refusals (AD-22 completeness, exact-rational, calendar, bar-spec) are requirement-anchored invalid input |
| x4_no_float_in_parameter_field | AD-7 | PASS | a binary-float default is invalid input |
| x4_no_float_in_leg_declared_parameter | AD-7 | PASS | a binary-float leg parameter is invalid input |
| x4_no_float_in_template_fixed_parameter | AD-7 | PASS | a binary-float template fixed parameter is invalid input |

## Gate status

- **R-009 (refusal-register conformance): GREEN.** X1/X2 plus every per-door refusal
  (B4, C4, D2, E5, G4) show qml's authoring doors emit only the four declared CT-04
  categories, all members of the seven-category register; no path emits an off-register
  category. The Story-11.7 version-mismatch path (G4) refuses `unsupported capability`.
- **R-011 (`footprint/_coerce.py` pinned by requirement): GREEN on behaviour.** D1
  (total, single-valued, deterministic, injective), D2 (every omitted AD-22 field →
  Layer-1 refusal), D6 (order-stable coercion), and X3 (requirement-anchored _coerce
  refusals) all pass, driven **only through public surfaces** (`mint_producer_template`,
  `resolve_template`, `mint_confluence`) — never a `_helper`, never a line-chasing test.
  **Branch-coverage number: not machine-measured in this environment** — enabling
  coverage instrumentation breaks duckdb's native `_duckdb` module import, which the
  `qml.declaration` test-import chain pulls in transitively via `qmf.data` (reproduced
  with both the C tracer and the sysmon backend). The base venv is undamaged (plain runs
  and `import duckdb` succeed). The requirement-anchored branches are exercised by
  D1/D2/D6/X3; no untethered-complexity branch was identified from the requirement mapping.

## Findings summary

| id | sev | requirement | one line |
|----|-----|-------------|----------|
| E11-F01 | low | 11.1 AC2 | src/qml ships `host/` + `logic/` beyond the seven named module homes ("exactly" not met) |
| E11-F02 | medium | 11.1 AC4 (AD-15) | `qml/host/runner.py` imports subprocess + calls open(); the impure Epic-12 host runner ships inside the pure qml library, contradicting AC4's package-wide purity claim |
| E11-F03 | medium | 11.4 AC5 | `Footprint.try_from_mapping` silently ignores a second top-level field instead of refusing it (unlike `try_create`); the "one stream-set locus, never a second top-level field" guarantee is not uniformly enforced |
| E11-F04 | low | 11.7 AC1 | UNPROVEN: "CT-22 format-2 adds exactly three things and nothing more" is a non-falsifiable negative claim |
| E11-F05 | low | 11.7 AC2 | UNPROVEN (narrowed): CT-23 advisory_stop_proposal field-carrying needs Epic-10 EntryIntent door fixtures |
| E11-F06 | low | 11.7 AC3 | UNPROVEN (narrowed): the CT-23-intent half of format back-compat needs Epic-10 door fixtures (CT-22 exit_policy half proven) |

## Scope honesty (excluded / narrowed / out-of-epic, rule 5)

- **B3** was tested through the **real qmf-risk `ExitPolicy`** (stronger than the planned
  fake) — fully proven, not narrowed.
- **D3** proves the completeness **report**; the Layer-1 **linter** that turns the report
  into a registration refusal is **Epic 12** (FR-048) and is correctly out of scope.
- **A6** proves the qml-side tunnel/citation split (`admit_ungoverned_tunnel`,
  `cite_ungoverned_bot`); the host-side "a plain-Python bot runs unchanged in QMB" is
  **Epic 13/14** and is out of scope.
- **G-cluster**: only the Story-11.7 **format-2 delta + migration/back-compat** was
  reached; the base CT-22/CT-23 door behaviour is **Epic 10** and was not re-asserted.
  G1 "nothing more" / G2 field-carrying / G3 CT-23-intent back-compat are recorded UNPROVEN
  above with reasons.
- **Layer-2 sandbox conformance, the prediction linter, the runtime protocol** (FR-048 /
  FR-050) are **Epic 12** and were not tested here.

## Notes

- 2 of the initial 5 reds were **test-code** errors, fixed without weakening any assertion:
  (a) the module-home enumeration looked under `src/qml` for `examples/`+`tests/`, which
  live at the distribution root; (b) F1 asserted two records' writers differ, but a
  same-content re-write on one registrar is *idempotent* and returns the first record — the
  fix uses **two independent composition roots** so both writes store their own header
  facts while deriving one `stable_id`.
- Full run: `uv run --with hypothesis pytest qa/tests/epic_11 -q --tb=short` →
  **67 passed, 3 failed** in ~3.3s.
