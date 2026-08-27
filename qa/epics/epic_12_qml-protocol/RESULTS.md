# RESULTS — Epic 12: qml-protocol (bot runtime protocol & two-layer conformance gate)

- **Audit tier:** T2 (L0 + targeted L1 + core L2 + core L3 + one L6 review pass). L4/L5 out-of-tier by ratified reason (§8-A/B of PLAN.md).
- **Run command (primary):** `uv run --with hypothesis pytest qa/tests/epic_12 -q --tb=short`
- **Run command (plain, task-stated):** `uv run pytest qa/tests/epic_12 -q --tb=short` — the single L1-property test (E12-L2-01 hypothesis generalization) `importorskip`s hypothesis and SKIPS; every other test runs unchanged.
- **Result:** **73 written · 73 passed · 0 failed · 0 errored** (with hypothesis). Plain: **72 passed · 1 skipped**. Real subprocess sandbox test executed (not skipped) and agreed with the in-process pure verdict.
- **Tests live under:** `qa/tests/epic_12/` (`conftest.py`, `_world.py` fixture builder, 9 test modules).
- **Findings:** 0 failing tests. 5 owned-requirement rows recorded **UNPROVEN by ratified out-of-tier reason** + 1 process-provenance info row in `findings.csv` (none is a code defect).

The fixture builder `_world.py` constructs a valid conformant declaration + a **test-authored** drivable factory (NOT the shipped example) through the public `qml` mint_* API, so the behavioural tests do not lean on the example's recipe. E12-L3-12 loads and drives the **shipped** `qml/examples/conformant_bot` independently.

---

## Ship-blocking triad (this epic) — verdict

| Triad clause | Assertions | Verdict |
|---|---|---|
| (i) Bot passes BOTH layers or is `policy rejection`, no partial state | E12-L1-03, E12-L3-02 | **GREEN** |
| (ii) Conformance gates citation + seats only, never tunnel entry, never performance | E12-L2-13 | **GREEN** |
| (iii) Bot never sizes / sets its own full-loss (Book-side, inbound `requested_r` refused), deterministic | E12-L1-01, E12-L3-04, E12-L2-01 | **GREEN** |

No FINDING on any triad clause. The epic's five P0 ship-blockers (P0-Q1..Q5) are each GREEN.

---

## Per-test results (73 tests; all PASS)

| Planned id | Test(s) | Req ids | Level | Result | Meaning (one line) |
|---|---|---|---|---|---|
| E12-L0-01 | `test_e12_l0_01_qml_never_imports_qmf_venue`, `..._no_qmf_roster_package_imports_qml` | L30, DEC-0171/0180 | L0 | PASS | qml imports no `qmf.venue`; no qmf roster package imports qml (AST scan, detector self-checked). |
| E12-L0-02 | `test_e12_l0_02_pure_library_has_no_impure_imports_outside_host`, `..._host_is_the_only_impure_site` | AD-15, COMP-QML | L0 | PASS | No thread/process/I-O import in the pure library; impurity is confined to `qml.host.runner`. |
| E12-L0-03 | `test_e12_l0_03_qml_contracts_are_local_not_ct_numbered` | DEC-0171/0177 | L0 | PASS | Protocol/conformance contract identities ride the `qml-ad5` ladder; no CT-number in the payload. |
| E12-L1-01 | `test_e12_l1_01_inbound_requested_r_is_invalid_input`, `..._sizing_dict_refused_in_live_drive_path` | QL-7, CT-23, P0-Q3 | L1 | PASS | An inbound `requested_r` is `invalid input`, at the door AND on the live drive path. |
| E12-L1-02 | `test_e12_l1_02_venue_command_is_unsupported`, `..._close_partial_is_unsupported` | QL-7, CT-23 | L1 | PASS | A venue command and a `close_partial` are `unsupported capability`. |
| E12-L1-03 | 4 tests in `test_l1_gate.py` | FR-048, QL-8, AR-64, DEC-0178, FM-4, P0-Q1 | L1 | PASS | Only (pass,pass) mints; any fail combo is `policy rejection`; probation/partial refused. |
| E12-L1-04 | `test_e12_l1_04_exit_kind_outside_ct23_vocab_is_invalid` | CT-33, CT-23, FM-3 | L1 | PASS | A permitted-exit kind outside `close_full|tighten_protective_stop` (and `entry`) is `invalid input`. |
| E12-L1-05 | `test_e12_l1_05_unknown_declaration_format_version_is_unsupported` | CT-33, FM-12 | L1 | PASS | The declaration parser AND the Layer-1 linter refuse an unknown format version `unsupported capability`. |
| E12-L1-06 | `test_e12_l1_06_family_cardinality_must_be_exactly_one` | CT-33, DEC-0176, FM-10 | L1 | PASS | `strategy_family_id` cardinality 0 or >1 is `invalid input`. |
| E12-L1-07 | `test_e12_l1_07_restore_across_differing_tuple_is_unavailable` | AR-67, FM-6 | L1 | PASS | Restore across a differing OS / arithmetic-reference / logic-identity is `unavailable dependency`; identical tuple restores. |
| E12-L1-08 | `test_e12_l1_08_layer1_failures_are_returned_not_raised_and_journaled` | CT-04, DEC-0109 | L1 | PASS | An unresolvable reference is a RETURNED (never raised) journaled AD-11 refusal, `layer=1`. |
| E12-L2-01 | `..._replay_yields_identical_intents`, `..._nondeterministic_bot_is_discriminated`, `..._determinism_generalizes_over_assignment` | B-2, DEC-0177, P0-Q4 | L2 | PASS | Two independent replays yield byte-identical intents; a nondeterministic bot is discriminated (canary); property holds ∀ lookback (hypothesis). |
| E12-L2-02 | `..._verdict_is_host_independent`, `..._verdict_carries_no_host_identity_field` | QL-8, DEC-0178, P0-Q4 | L2 | PASS | Two independent host runs mint one verdict fingerprint; the verdict identity carries no pid/host field. |
| E12-L2-03 | `test_e12_l2_03_nondeterminism_and_bad_kind_fail_layer2` | FM-5, DEC-0177/0178 | L2 | PASS | Differing runs, a non-permitted kind, and a scan finding each fail the pure verdict. |
| E12-L2-04 | `..._footprint_must_equal_transitive_union`, `..._completeness_report_is_set_equality` | QL-4, FM-1, P0-Q5 | L2 | PASS | A missing leg producer is a Layer-1 refusal; completeness is exact set-equality (missing AND extra caught). |
| E12-L2-05 | `..._callback_sees_only_declared_footprint_evidence`, `..._construct_refuses_undeclared_read_surface` | QL-7, CT-33 | L2 | PASS | Undeclared and forbidden (book/clock) evidence keys are refused; construct refuses an undeclared read surface. |
| E12-L2-06 | `..._denial_set_scan_flags_each_capability_before_spawn`, `..._declared_seed_permits_random_but_not_secrets` | AR-68, FM-5 | L2 | PASS | Clock/fs/network/undeclared-random each become a scan finding (pure, pre-spawn); a declared seed permits `random`, not `secrets`. |
| E12-L2-07 | `..._omitted_ad22_field_is_layer1_refusal`, `..._template_resolution_is_single_valued` | QL-4, FM-2 | L2 | PASS | Removing any AD-22 identity field is a Layer-1 refusal naming it; resolution is single-valued. |
| E12-L2-08 | `..._logic_identity_is_source_manifest_not_build_bytes`, `..._ad16_header_fields_are_excluded_from_identity` | DEC-0172/0173, AD-16, FM-10 | L2 | PASS | Identity is the source-manifest fp (build artifacts stripped); a writer/created-at/stable-id/sequence on the declaration is refused. |
| E12-L2-09 | `..._identity_is_semantic_content_only`, `..._occurrence_facts_never_mint_a_new_bot` | DEC-0173, AD-30 | L2 | PASS | Identical content -> identical fp1; a tuned default mints a new fp1; seat/binding/paper are refused. |
| E12-L2-10 | `..._snapshot_restore_roundtrip_is_equivalent`, `..._state_bound_is_enforced` | AR-67 | L2 | PASS | Snapshot/restore on an identical tuple is equivalent; state exceeding the bound is a `policy rejection`. |
| E12-L2-11 | `test_e12_l2_11_nested_confluence_producer_must_reach_footprint` | CT-34, QL-5, FM-1, P0-Q5 | L2 | PASS | A producer cited only through a NESTED confluence must reach the footprint (transitive union); omission refuses. |
| E12-L2-12 | `..._every_parameter_is_unit_kinded_no_float`, `..._defaults_form_the_canonical_assignment` | AD-40, DEC-0154 | L2 | PASS | A missing unit-kind and a binary-float default are `invalid input`; defaults form the canonical assignment. |
| E12-L2-13 | `..._complexity_score_is_not_a_registration_gate`, `..._conformance_gates_citation_and_seats_not_tunnel` | FR-048, DEC-0178, P0-Q2 | L2 | PASS | `max_acceptable_complexity_score` is discarded not gated; a registered bot may be cited; an ungoverned bot keeps the tunnel but cannot be cited. |
| E12-L3-01 | 3 tests | QL-7, DEC-0177 | L3 | PASS | The factory contract: (declaration, assignment, surfaces) -> callback -> CT-23 intents; shape violations & non-CT-23 emissions refused. |
| E12-L3-02 | `..._gate_returns_content_and_verdict_never_a_record`, `..._graduation_edge_...`, `..._all_fail_combinations_...` | FR-048, AD-25, DEC-0178, FM-4, P0-Q1 | L3 | PASS | The gate returns content + verdict, NEVER a stamped record (no WriterId); graduation edge is authored content; all fail combos are policy rejection. |
| E12-L3-03 | `test_e12_l3_03_unresolvable_references_are_unavailable` | CT-33, QL-8 | L3 | PASS | A missing family/confluence/logic reference is `unavailable dependency`; the clean declaration passes the pinned check list. |
| E12-L3-04 | 5 tests in `test_l3_door.py` | CT-23 v2, DEC-0177/0182/0185, P0-Q3 | L3 | PASS | No bot-side full-loss field exists; inbound `requested_r`/full-loss-price refused; advisory stop admitted; format-2 reader accepts format-1 unchanged. |
| E12-L3-05 | `..._ct33_shape_six_groups_no_exit_logic`, `..._ct33_semantic_content_roundtrip` | CT-33, DEC-0173 | L3 | PASS | Six content groups; header & `exit_logic` excluded; canonical payload re-mints the same fp1 (shape-only). |
| E12-L3-06 | `..._ct34_shape_and_leg_rules`, `..._order_significance_enters_fingerprint_only_when_declared` | CT-34, DEC-0175 | L3 | PASS | >=1 leg; bad role & producerless+childless leg refused; declaring order-significance changes the fingerprint. |
| E12-L3-07 | 3 tests | CT-28, AR-66, Story 12.6 | L3 | PASS | The four pinned checks pass on a compatible binding; (a) footprint and (b) exit-subset failures refuse. |
| E12-L3-08 | 3 tests | DEC-0176/0178, FM-7/8/9 | L3 | PASS | A zero-exit-kind Book admits an entry-only bot; (c) family-resolves and (d) stream-set failures refuse at bind time. |
| E12-L3-09 | `test_e12_l3_09_restored_state_fingerprint_enters_labels` | AR-67, FM-6 | L3 | PASS | The restored-state fingerprint enters downstream labels; a cold bot exposes none. |
| E12-L3-10 | `..._verdict_is_the_pure_function_fed_by_observations`, `..._spawned_runner_yields_the_same_pure_verdict` | AR-68, DEC-0178 | L3 | PASS | The verdict is the pure function's output; the REAL spawned sandbox process yields the identical verdict (host-independent by construction). |
| E12-L3-11 | `..._blank_requirement_passes_registration_blocks_live`, `..._requirement_set_shape_is_format_2_only` | CT-22 v2, DEC-0181, FM-11/12 | L3 | PASS | A blank `footprint_requirement` binds non-live but LIVE binding is a policy rejection; the requirement-set shape is format-2 only. |
| E12-L3-12 | 3 tests in `test_l3_example_bot.py` | Story 12.8, L27, FR-047/050, CT-33 | L3 | PASS | The SHIPPED example passes both layers and mints; no exit_logic/sizing; deterministic advisory-stop entry over the golden slice. |

## L6 — requirements-fidelity review (self-review during authoring)

The six PLAN §4 focus checks were held to during authoring:
- **(a)** No test manufactures an admission-bar / `footprint_requirement` threshold VALUE into a passing fixture — E12-L3-11 uses the ratified *blank* pending slot and a ruled `>=5` that the footprint deliberately fails; no threshold value is invented.
- **(b)** CT-33/CT-34 are asserted **shape-only** (E12-L3-05/06); no test wires the defined-unwired registry record mint.
- **(c)** E12-L3-04 is framed **structurally** (no bot-side full-loss field + inbound `requested_r` refusal), not as a non-existent inbound-refusal on the advisory stop (DEC-0185).
- **(d)** E12-L2-13 asserts conformance gates citation + seats only, never tunnel entry, never performance.
- **(e)** Determinism/host-independence assert the **pure** verdict function / independently-driven traces, never the impure runner as sole witness (and the runner cross-check confirms agreement).
- **(f)** The two Tier-1 registry findings E2-F01/E2-F02 are re-bound to Epic 12 and resolved (see §8-A verdict below and `findings.csv` E12-F01).

---

## UNPROVEN / out-of-tier requirements (scope honesty — rule 5)

None of the following is a code defect; each is recorded so nothing is silently narrowed. All are in `findings.csv` (observed=UNPROVEN, severity=info/low).

- **E12-F01 — §8-A CT-33 registry record MINT (re-adjudication of E2-F01/E2-F02).** `epics.md` assigns FR-048 to Epic 12, not Epic 2. **Verdict:** the two-layer conformance verdict and the "policy rejection on either fail, no partial" decision are **QML's and are realized + GREEN now** (E12-L1-03, E12-L3-02). The **actual registry record mint is defined-unwired at the AD-25 composition root** — QML returns fingerprintable content + the pass/fail verdict, never a stamped record (verified: `gate_registration` yields a `RegistrationCandidate` with no WriterId/occurrence header, `hasattr(candidate,"record")` is False). The registry package correctly has no bot-mint path; the mint is root-territory (QMB Story 14.8 / trading node), **UNPROVEN here by ratified out-of-tier reason, not a defect.** If a future reconcile shows `qml.conformance.registration` itself stamping/persisting a record, that inverts AD-25 and becomes a P0 finding — it does not today.
- **E12-F02 — §8-C OS-level sandbox confinement (AR-68/DEC-0178).** V1 promises only static AST/import scan + capability starvation + host process isolation (all GREEN: E12-L2-06, E12-L3-10). Hardened OS confinement (restricted tokens/job objects, seccomp) is a named deferred dependency and a dynamically-evasive malicious bot is out of V1's threat model. "The sandbox actually prevents a determined malicious bot at the OS level" is **untestable-positive in V1** — documented-deferral, must stay unenforced.
- **E12-F03 — §8-D admission-bar / `footprint_requirement` threshold VALUES (GAP-0048/0049).** The blank-blocks-live behaviour and the format-2 requirement-set shape are GREEN (E12-L3-11). No threshold VALUE is ratified; the threshold itself is **untestable** — a test that manufactured one would be a finding (DEC-0004). Documented-deferral (interface-only).
- **E12-F04 — §8-E graduation lineage-edge PERSISTENCE (Story 12.7 AC4).** The authored `promoted-from` edge SHAPE is GREEN (E12-L3-02 graduation test: `from_ref`=bot fp, `to_ref`=research, no WriterId). The edge's **persistence** rides the same defined-unwired composition-root mint as E12-F01 — **UNPROVEN here**, host-territory.
- **E12-F05 — Story 12.7 tunnel non-gating for ungoverned bots.** The qml-side is GREEN (E12-L2-13: `admit_ungoverned_tunnel` Ok, ungoverned cite refused, no complexity gate). The claim that an ungoverned plain-Python bot "needs zero qml imports and retains full tunnel access" in the actual tunnel is **node/QMB territory** — UNPROVEN in the qml package.
- **E12-F06 — GAP-QA-01 provenance (process, info).** The named authority files `test-design-qa.md` and `QMX-handoff.md` (and the whole `_bmad-output/test-artifacts/` tree) are absent from the worktree; the L0–L6 architecture and the R-009/R-011 risk-gate rows were reconstructed from `LENS-TEST-STRATEGY` + `COMP-QML` + the lane brief. If those files are restored, re-reconcile before trusting section numbering. Not a code defect.

## L4 / L5 (wired integration / acceptance)

**0 executed, out of this T2 tier by ratified reason** (§8-B). A real registry-persisted mint and an end-to-end seat/citation chain need the wired composition root + a live Book/registry (QMB 14.8 / node; SCN-0012 replay is Epic 14). The shipped-example end-to-end (E12-L3-12) is the strongest in-package proxy and is GREEN. Deferred to the host epic — recorded, not silently skipped.

## FM-1..FM-12 disposition

FM-1 (E12-L2-04/11) · FM-2 (E12-L2-07) · FM-3 (E12-L1-04) · FM-4 (E12-L1-03, E12-L3-02) · FM-5 (E12-L2-03/06) · FM-6 (E12-L1-07, E12-L3-09) · FM-7/8/9 (E12-L3-08) · FM-10 (E12-L1-06, E12-L2-08) · FM-11 (E12-L3-11) · FM-12 (E12-L1-05, E12-L3-04/11) — all **GREEN**. OS-confinement (§8-C) and threshold VALUES (§8-D) exit as documented-deferral.
