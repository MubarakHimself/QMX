# Epic 9 — qmf-structure — Independent Verification RESULTS

**Package:** `qmf-structure` (import root `qmf.structure`). **Owned requirement:**
FR-020 / CT-17 (causal, append-only, look-ahead-safe chart-object families) — the only
FR and the only CT this epic owns (epics.md Epic 9, FR Coverage Map).

**Run command**

```
uv run --with hypothesis pytest qa/tests/epic_09 -q --tb=short
```

**Outcome:** **74 tests written, 74 passed, 0 failed, 0 errored.** (`hypothesis` is not
in the base dev group, so the L1 file is run under `--with hypothesis`, per the lane
brief.) Every authored assertion is drawn from an oracle — epics.md Epic 9 ACs,
`docs/contracts/ct-17-causal-structure.yaml`, `docs/constitution.md`,
`docs/registry/variables.yaml` — never from the implementation.

| Level | File | Tests | Pass | Fail |
| ----- | ---- | ----- | ---- | ---- |
| L0 structural | `test_l0_structural.py` | 11 | 11 | 0 |
| L1 property (hypothesis) | `test_l1_properties.py` | 10 | 10 | 0 |
| L2 contract | `test_l2_contract.py` | 18 | 18 | 0 |
| L3 acceptance | `test_l3_acceptance.py` | 35 | 35 | 0 |
| **Total** | | **74** | **74** | **0** |

**No source was modified. No failing test was made to pass and no test was weakened.**
No source defect was found: the implementation satisfies every requirement-level
assertion that could be independently constructed under the hardened-author rules. The
`findings.csv` rows are therefore the process/traceability finding (E9-F01) plus the
scope-narrowed / structurally-out-of-lane requirement clauses recorded as **UNPROVEN**
(E9-F02..F06) — not source failures.

## Falsifiability discipline (hardened-author rule 1)

Every green here is falsifiable, and the suite proves it by construction:

- **Independent oracles, not the code's own trace.** L1-001 recomputes the emission
  invariant from first principles and asserts `Ok iff oracle-legal`; L3-005 recomputes
  `still_valid` independently and compares to the fold; L2-003 recomputes the composite
  max-rule independently.
- **Reject arms demonstrably reachable.** `test_l0_001_detector_flags_a_forbidden_import`
  (a synthetic `qmf.data`/`numpy` IS flagged), `test_l0_003_detector_reject_arm_is_reachable`
  (a school-named token IS flagged, and does not misfire on `GovernanceVerdict`),
  `test_l1_001_both_arms_are_reachable` (a legal chain mints, a look-ahead one refuses).
- **Absence-of-effect observed through the sink, not a flag.** L3-010 asserts the confirmed
  read returns a **TypedRefusal, not a shorter tuple** — a silent filter would fail it.
- **Fault realism.** Refusals are observed as returned `TypedRefusal`s (never raised), and
  the R-002 no-raise universal (L1-002) fuzzes 37 public boundaries with arbitrary objects.

## L0 — structural gates (oracle = constitution law / directory fact)

| Test | Requirement | Result | Meaning |
| ---- | ----------- | ------ | ------- |
| test_l0_001_detector_flags_a_forbidden_import | L30 (falsifiability) | PASS | The import-graph checker's reject arm fires on `qmf.data`/`numpy` and passes `qmf.core`/stdlib. |
| test_l0_001_structure_imports_only_qmf_core_and_stdlib | L30, AR-06, CT-17 | PASS | Every `qmf.structure` module imports only `qmf.core` + stdlib (AST-parsed, no third-party, no cross-package qmf). |
| test_l0_001_no_roster_package_imports_qmf_structure | L30 | PASS | No other roster package under `packages/*/src` imports `qmf.structure` (default-deny, V1). |
| test_l0_002_every_public_dataclass_is_frozen | Story 9.1 AC-1 | PASS | Every public value type in `__all__` that is a dataclass is `frozen=True`. |
| test_l0_002_frozen_instance_rejects_mutation | Story 9.1 AC-1 | PASS | A minted object's in-place mutation raises `FrozenInstanceError` (behavioral, not a flag). |
| test_l0_002_seams_are_runtime_checkable_protocols | Story 9.1 AC-1 | PASS | The five seams (StructureFamily/EvidenceRow/IndicatorResultInput/InvalidationPredicate/PriceObservation) are runtime-checkable `typing.Protocol`s. |
| test_l0_003_detector_reject_arm_is_reachable | FM-9, L32 (falsifiability) | PASS | The school-name detector flags `elliott`/`order block` and does not misfire on `verdict`. |
| test_l0_003_no_school_name_across_the_export_surface | FM-9, L32 | PASS | No trading-school name appears in any public symbol, enum value, seed geometry, or concept-walk register term. |
| test_l0_003_seed_family_names_no_school | FM-9, L32 | PASS | The swing-point seed family's id/geometry/descriptor name no trading school. |
| test_l0_004_distribution_artifacts_present | L27, AR-21, NFR-11 | PASS | `FAILURES.md`, `examples/structure_usage.py`, `_bench.py`, `py.typed`, `README.md` all present. |
| test_l0_004_failure_register_names_the_ct17_refusal_categories | L27, NFR-11 | PASS | `FAILURES.md` registers the two CT-17 refusal categories (`invalid input`, `policy rejection`). |

## L1 — property tests, hypothesis (oracle = a CT-17 invariant, quantified)

| Test | Requirement | Result | Meaning |
| ---- | ----------- | ------ | ------- |
| test_l1_001_emission_invariant_holds_iff_oracle | FR-020, CT-17, FM-1 | PASS | For every generated chain + consumed-input set, mint succeeds **iff** `anchor.end ≤ observed ≤ confirmed ≤ invalidated` and `observed ≥ max(consumed)`, else `invalid-input` — matched to an independent oracle. |
| test_l1_001_both_arms_are_reachable | FM-1 | PASS | Both the accept and refuse arms of the emission invariant are demonstrably hit. |
| test_l1_002_no_public_callable_raises_on_arbitrary_input | CT-17 R-002 | PASS | 37 public boundaries, fuzzed with arbitrary objects, always return `Ok` or a `TypedRefusal` — never raise. |
| test_l1_002_swing_family_methods_also_return_results | CT-17 R-002 | PASS | `SwingPointFamily.detect`/`confirmation_for` return refusals on bad input, never raise. |
| test_l1_003_distinct_identity_field_yields_distinct_fingerprint | CT-17, DEC-0108 | PASS | Two objects differing in one identity field (observed-at, a parameter, an anchor bound, version) fingerprint distinctly. |
| test_l1_003_each_evidence_class_is_a_distinct_fact | CT-17, DEC-0110 | PASS | The three evidence classes fingerprint to three distinct facts (class is identity). |
| test_l1_003_no_null_ever_appears_in_identity_content | CT-17 nullability | PASS | No `None` appears anywhere in fp1 identity content; an unbounded delay is the explicit `"unbounded"` token. |
| test_l1_004_a_binary_float_parameter_is_refused | CT-17, DEC-0105 | PASS | Any generated binary-float parameter is refused `invalid-input` (`field: parameters`). |
| test_l1_004_exact_rational_parameters_carry_no_float_in_identity | CT-17, DEC-0105 | PASS | Exact-rational parameters never leak a `float` into fp1 identity content. |
| test_l1_004_a_float_anchor_bound_is_refused | CT-17, DEC-0105 | PASS | A raw float in an anchor price-bound position is refused (a Price is a scaled integer). |

## L2 — contract tests (oracle = the ct-17-causal-structure.yaml clause)

| Test | Requirement | Result | Meaning |
| ---- | ----------- | ------ | ------- |
| test_l2_001_known_geometry_seed_set_is_the_ct17_six | CT-17, DEC-0129 | PASS | The seed geometry set is exactly point\|level\|zone\|span\|distribution\|graph. |
| test_l2_001_geometry_is_open_not_a_closed_enum | CT-17, DEC-0129 | PASS | A geometry outside the seed set is **accepted** (open, family-declared), not refused. |
| test_l2_001_blank_geometry_is_refused | CT-17 | PASS | A blank geometry is the one refusal (`field: geometry`). |
| test_l2_002_sloped_object_identity_has_anchors_and_rule_but_no_stored_slope | CT-17, DEC-0126/0105 | PASS | A sloped object's identity carries anchors + versioned evaluation rule; slope is **not** stored (`"slope"` absent). |
| test_l2_002_versioned_evaluation_rule_is_identity_bearing | CT-17, DEC-0126 | PASS | Two sloped objects differing only in evaluation-rule version fingerprint distinctly. |
| test_l2_002_calendar_level_declares_fingerprinted_policies | CT-17, DEC-0119 | PASS | A calendar level's sampling_policy and schedule_gap_policy are named parts of its fp1 identity. |
| test_l2_002_policy_is_identity_bearing | CT-17 | PASS | Two levels differing only in sampling policy are distinct artifacts. |
| test_l2_002_policy_enums_are_the_ct17_closed_sets | CT-17 | PASS | Sampling/schedule-gap policy enums equal the CT-17-declared closed sets. |
| test_l2_003_instants_are_the_maxima_over_children | CT-17, DEC-0115 | PASS | Composite observed-at/confirmed-at are the maxima over children, never earlier than any child; bound is the children's sum. |
| test_l2_003_unconfirmed_until_every_child_is_confirmed | CT-17, DEC-0115 | PASS | A composite has no confirmed-at while any child is unconfirmed. |
| test_l2_003_unbounded_child_makes_composite_unbounded | CT-17, DEC-0119 | PASS | Any unbounded child makes the composite's confirmation-delay bound unbounded. |
| test_l2_003_children_order_significant_by_default_unordered_when_declared | CT-17, DEC-0115 | PASS | Ordered composites are order-sensitive in fp1; explicitly-unordered ones fingerprint order-independently. |
| test_l2_003_composite_lineage_is_its_children_fingerprints | CT-17, DEC-0114 | PASS | A composite's lineage inputs are exactly its children's fingerprints. |
| test_l2_004_all_ct17_refusals_are_registered_categories | CT-17, DEC-0109 | PASS | Seven provoked CT-17 refusal paths all carry a registry `typed_refusal_codes` category (parsed from the registry), machine-readable context, and retryability. |
| test_l2_005_builder_set_matches_the_register_no_drift | CT-17, DEC-0131/0102 | PASS | The 11 concept-walk builders exactly match `CONCEPT_WALK_REGISTER` (no drift). |
| test_l2_005_every_concept_walk_item_is_constructible | CT-17, DEC-0131/0102 | PASS | Each of the 11 concept-walk items builds a real fingerprintable artifact from the public surface (retro-anchored zone, born-from-invalidation, tolerance cluster, breach-then-reversal, calendar composite, multi-BarSpec nest, cross-instrument divergence, distribution-over-price, a-priori grid, projected level, pattern refit). |
| test_l2_006_emissions_carry_no_writer_or_sequence | CT-17, DEC-0114/0106 | PASS | Objects/records/edges carry no writer/sequence/created-at attribute or fp1 key — fingerprintable content, never a stamped record. |
| test_l2_006_content_fingerprint_is_deterministic | CT-17, DEC-0108 | PASS | Identical content lands on one fp1 (dedup by construction, no writer). |

## L3 — acceptance tests (oracle = epics.md Epic-9 ACs)

| Test | Requirement | Pri | Result | Meaning |
| ---- | ----------- | --- | ------ | ------- |
| test_l3_001_observed_at_behind_a_consumed_input_is_refused | Story 9.1 AC-3, FM-1 | P0 | PASS | An observed-at behind a consumed input's evidence time is refused `invalid-input`. |
| test_l3_001_confirmed_before_observed_is_refused | Story 9.1 AC-3, FM-1 | P0 | PASS | A confirmed-at before observed-at (data not knowable at confirmation) is refused. |
| test_l3_001_causality_refuses_at_equal_but_consumption_admits_at_equal | Story 9.3 AC-2, DEC-0106 | P0 | PASS | The causality test refuses at `T==T` while a consumer at `confirmed-at==T` is admitted — no look-ahead artifact enters governed evidence. |
| test_l3_001_real_family_pivots_are_never_dated_before_their_payload | Story 9.4 AC-1, FM-1 | P0 | PASS | Every real swing pivot's observed-at is ≥ its own anchor — a repainted/look-ahead swing cannot mint. |
| test_l3_002_object_carries_every_identity_field_and_is_frozen | Story 9.1 AC-2 | P0 | PASS | An object carries every identity field, all present in fp1, and is frozen (mutation raises). |
| test_l3_002_a_change_is_a_new_artifact_not_a_mutation | Story 9.1 AC-2 | P0 | PASS | Every "change" mints a new fp (a refit), never an in-place edit. |
| test_l3_003_anchor_may_precede_observed_at | Story 9.1 AC-2 | P0 | PASS | The anchor span is permitted to precede observed-at. |
| test_l3_003_anchor_excluded_from_causal_test_but_observed_at_is_not | Story 9.1 AC-2/9.3 AC-2 | P0 | PASS | A consumed input later than the anchor but ≤ observed-at is fine; later than observed-at is refused — the anchor is excluded from causality. |
| test_l3_003_standing_object_declares_observed_at_as_config_instant | Story 9.1 AC-2 | P0 | PASS | A standing (a-priori) calendar level declares observed-at = its configuration instant. |
| test_l3_004_records_are_separate_kinds_referencing_object_by_fingerprint | Story 9.2 AC-1 | P0 | PASS | Confirmation/invalidation/interaction are three separate record kinds, each referencing the object by fp1. |
| test_l3_004_each_record_instant_is_identity_bearing | Story 9.2 AC-1 | P0 | PASS | Two confirmations of one object at two instants are two distinct facts. |
| test_l3_004_records_are_frozen_no_in_place_edit | Story 9.2 AC-1 | P0 | PASS | A lifecycle record is frozen — no in-place edit exists. |
| test_l3_005_still_valid_is_a_fold_matching_an_independent_oracle | Story 9.2 AC-1 | P1 | PASS | "Still valid at T" is a read-time fold with no stored field, matching an independent oracle across five knowledge times. |
| test_l3_006_refit_mints_new_artifact_keeps_first_observed_at_prior_untouched | Story 9.2 AC-2, FM-3 | P0 | PASS | A refit mints a new artifact with a supersedes edge, keeps the first observed-at, and leaves the prior object untouched. |
| test_l3_007_precise_and_clock_confirmed_admitted_imprecise_refused | Story 9.2 AC-3, FM-2 | P0 | PASS | A precise/clock-confirmed rule is admitted; an imprecise (blank) rule is refused `policy-rejection` into the research lane. |
| test_l3_008_childs_own_fold_does_not_cascade | Story 9.2 AC-4 | P1 | PASS | An invalidated parent does not cascade to the child's own fold. |
| test_l3_008_cascade_is_opt_in_and_read_time_only | Story 9.2 AC-4 | P1 | PASS | Cascade is an opt-in read-time derivation that never mutates the child's own state. |
| test_l3_009_evidence_class_identity_and_confirmed_as_edge | Story 9.3 AC-1 | P1 | PASS | Evidence class is identity-bearing; an unconfirmed output carries a typed `confirmed-as` edge to its successor. |
| test_l3_010_confirmed_read_refuses_rather_than_silently_filtering | Story 9.3 AC-1, FM-4 | P0 | PASS | A confirmed read over a mixed set returns a **refusal, not a shorter tuple** — never a silent filter. |
| test_l3_010_all_confirmed_read_returns_every_row | Story 9.3 AC-1 | P0 | PASS | An all-confirmed read returns every row. |
| test_l3_011_consumption_admits_le_t_causality_refuses_at_equal | Story 9.3 AC-2, DEC-0106 | P0 | PASS | Consumption admits `confirmed-at ≤ T` (equality included); the distinct causality test refuses at equal. |
| test_l3_012_straddle_beyond_embargo_refused_within_embargo_admitted | Story 9.3 AC-3, FM-7 | P0 | PASS | A record straddling a boundary beyond its embargo is refused; within embargo / non-straddle is admitted. |
| test_l3_012_unbounded_family_excluded_from_split_governed_evidence | Story 9.3 AC-3, FM-7 | P0 | PASS | An unbounded confirmation-delay family is refused a finite embargo width (excluded from split-governed evidence). |
| test_l3_012_bound_derived_embargo_governs_the_boundary | Story 9.3 AC-3, FM-7 | P0 | PASS | The bound-derived embargo width admits a within-bound straddle and refuses one that confirmed later than declared. |
| test_l3_013_revised_input_changes_the_label_and_label_carries_every_part | Story 9.3 AC-4, DEC-0110 | P1 | PASS | A revised input yields a different computation identity (no silent change); the label carries producer identity, format version, inputs, evidence range, class, world. |
| test_l3_014_citation_law_and_confirmed_only_promotion | Story 9.3 AC-5 | P1 | PASS | In-memory use persists nothing; a journal/label citation makes the object governed (must-persist); a scanner promotes only confirmed objects. |
| test_l3_015_seed_family_precise_unprivileged_consumes_declared_inputs_no_school | Story 9.4 AC-1, FM-9 | P1 | PASS | The swing seed family is precise, admitted through the identical gate as an operator peer (no privilege), consumes declared bar inputs, and names no trading school. |
| test_l3_016_routing_admits_exactly_one_answer | Story 9.4 AC-3, FM-6 | P1 | PASS | Routing admits exactly one of CT-16/CT-17; both-or-neither is refused. |
| test_l3_016_indicator_consumed_as_declared_input_returns_its_fingerprint | Story 9.4 AC-3, FM-6 | P1 | PASS | An indicator is consumed as a declared input (its fp returned to record), never re-implemented inline. |
| test_l3_017_benchmark_rungs_are_the_three_structure_rungs | Story 9.4 AC-4, FM-8 | P1 | PASS | The benchmark rungs are active-object-set-size / objects-minted-per-bar / interaction-records-per-bar. |
| test_l3_017_light_claim_lacking_baseline_and_over_bound_refused | Story 9.4 AC-4, FM-8 | P1 | PASS | A light claim lacking a baseline or over a declared bound is refused at the gate; a clean claim is light. |
| test_l3_017_peak_memory_regression_fails_exactly_as_a_slowdown | Story 9.4 AC-4, FM-8 | P1 | PASS | A peak-memory regression is refused exactly as a slowdown is. |
| test_l3_018_precise_family_graduates_with_promoted_from_edge | Story 9.4 AC-5, L33 | P1 | PASS | A precise family graduates with a `promoted-from` edge from the graduated artifact to its originating experiment. |
| test_l3_018_imprecise_concept_never_graduates | Story 9.4 AC-5, L33, FM-2 | P1 | PASS | An imprecise concept never graduates — it stays in the ungoverned research lane. |
| test_l3_018_graduation_requires_distinct_artifact_and_experiment | Story 9.4 AC-5, L33 | P1 | PASS | A graduation links a governed artifact to a **distinct** experiment (same-ref is refused). |

## UNPROVEN requirements (scope honesty — hardened-author rule 5)

Every clause below is an owned-AC clause I could not fully prove in this Tier-1 lane. Each
has a `findings.csv` row (observed=UNPROVEN). None is a source defect; each is a
structural / out-of-lane / by-design-deferred limit, recorded rather than silently
narrowed.

| # | Clause | Why UNPROVEN | Finding |
| - | ------ | ------------ | ------- |
| 1 | Story 9.1 AC-1 "undeclared import fails the Tier-2 isolated-environment gate" | The import GRAPH is proven structurally (L0-001), but the isolated-per-package-env ENFORCEMENT is out-of-band CI, not exercisable in-lane. | E9-F02 |
| 2 | Story 9.1 AC-1 "versions in the roster SemVer lockstep" | The package's own `__version__==0.1.0` is confirmed, but roster-wide lockstep is an Epic-1 invariant not re-verified here. | E9-F03 |
| 3 | Story 9.4 AC-4 concrete benchmark budget numbers (FM-8) | Measure-then-budget: no baseline numbers exist. Only the refusal negatives are provable, and they are proven (L3-017). No number invented. | E9-F04 |
| 4 | Story 9.3 AC-5 "…becomes governed evidence and is **persisted**" | The citation verdict is proven (L3-014); actual persistence is composition-root / Epic 3 (CT-11/CT-13), which the library never performs. | E9-F05 |
| 5 | CT-08 full look-ahead/causality **registration gate** | Deferred to the backtesting sitting (GAP-0016); Story 9.3 AC-5 states the emission invariant is the interim guard, not that gate. The interim guard is proven (L1-001/L3-001). | E9-F06 |

## Section 5 — existing-test audit (R-003)

Author suite: `packages/qmf-structure/tests/test_ct17_*.py` (12 modules). The three most
suspect modules were read in full (`test_ct17_objects.py`, `test_ct17_lifecycle.py`,
`test_ct17_provenance.py`) plus `test_ct17_families.py`; the rest were classified by their
assertion shape.

| Module | Requirement | Classification | Note |
| ------ | ----------- | -------------- | ---- |
| test_ct17_objects.py | Story 9.1 (mint, emission invariant) | **keep** | Asserts the FULL ordering chain **and** the adversarial future-leak case (`observed_at` behind a consumed input), observed through the public `check_emission_invariant` / mint — not a single hand-picked violation. |
| test_ct17_lifecycle.py | Story 9.2 (fold, refit, admission) | **keep** | "Still valid at T" is asserted as a fold over the public `resolve_state` (look-ahead-safe, no stored field), overwrite is refused, and a refit mints a new artifact keeping the first observed-at. It asserts the LAW, not the code's own fold. |
| test_ct17_provenance.py | Story 9.3 (evidence class, confirmed read, split) | **keep** | The confirmed read **refuses** (policy-rejection), does not filter; the revised-input relabel and split-embargo boundary refusal are asserted against a gap the embargo does not cover. |
| test_ct17_families.py | Story 9.4 (seed family, FM-2/FM-9) | **keep** | Refuses an imprecise rule admission, asserts no-privilege and no-school over the family's own strings, and pins the pivot's observed-at to the right-window bar (look-ahead safety). |
| test_ct17_composites/geometry/routing/budget/research/conformance.py | CT-17 / Story 9.4 | **keep** (by shape) | Contract-fact assertions over the public surface; no "contradicts" row surfaced. |

**R-003 result: no `contradicts` finding.** The plan's prior suspicion (F-E09-004: that the
author suite pins the code's fold rather than the contract law) is **not confirmed** — the
author tests assert the CT-17 law through public surfaces. F-E09-004 is therefore closed as
info, not elevated to a `findings.csv` row. The net-new independent claims the per-behaviour
author tests structurally cannot make — the emission-invariant universal (L1-001) and the
no-raise universal over 37 boundaries (L1-002) — are written here regardless and pass.

## Findings summary

| finding_id | severity | kind | one-line |
| ---------- | -------- | ---- | -------- |
| E9-F01 | medium | process/traceability | test-design-qa.md and QMX-handoff.md absent from the worktree snapshot; handoff risk rows and the 15-assertion cross-reference could not be consumed. |
| E9-F02 | low | UNPROVEN | Isolated-per-package-env import gate is out-of-band CI (import graph proven structurally). |
| E9-F03 | low | UNPROVEN | Roster-wide SemVer lockstep not re-verified in this lane (package version 0.1.0 confirmed). |
| E9-F04 | low | UNPROVEN | Concrete benchmark budget numbers do not exist (measure-then-budget); only the negatives are proven. |
| E9-F05 | low | UNPROVEN | Governed-evidence PERSISTENCE is composition-root / Epic 3; only the citation verdict is proven. |
| E9-F06 | low | UNPROVEN (deferred) | CT-08 registration gate deferred to GAP-0016 by design; the interim emission-invariant guard is proven. |

**No P0/P1 source defect was found.** The `qmf-structure` implementation satisfied every
independently-constructed requirement-level assertion for FR-020 / CT-17.
