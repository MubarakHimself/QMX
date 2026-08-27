# RESULTS — Epic 19: QMB Reports & Result Artifacts (qmb-reports)

**Audit tier:** T3 (L3 acceptance carries the epic; one L4 scenario, one L5 concurrency test, one L6 adversarial pass).
**Package under test:** `qmb/src/qmb/results/` (`ct32.py`, `measures.py`, `accounting.py`, `charts.py`, `render.py`, `interpret.py`) — source read-only.
**Run command:** `uv run --with hypothesis pytest qa/tests/epic_19 -q --tb=short` (from the worktree root).
**Result totals:** **71 executable tests — 70 PASS, 1 FAIL** (the fail is the genuine R13 finding E19-F01, doubling as its regression pin) + 1 L6 adversarial pass. hypothesis is not in the synced dev group; the one property test (U1) runs under `--with hypothesis`.

Delivers FR-043. Governing invariants exercised: B-10/B-13, AR-59, AR-14, AR-15, AD-10, AD-12, AD-40, DEC-0162, CT-32.

---

## Headline

The `qmb/results/` implementation is strong and, for the pinned V1 measure roster, faithfully honours every P0/P1 acceptance criterion: exactly one CT-32 container per run (adopted, not reinvented), label-derived `fp1` via qmf-core only with no float byte in identity, provenance-derived world (a keys `world` flag is ignored), simulated/multi-role refused before any write, an ordered unit-kinded measure set with undefined ≠ zero, suppression/veto tallies folded only from CT-13 journals with explicit zero keys, charts as data (never images), pure byte-stable rendering with a verbatim world/role headline, interpretation that refuses a rendering, reproduce-or-refuse, and per-run concurrency isolation.

**One confirmed finding (E19-F01, R13, medium):** the composite-expression *guard* is incomplete versus the ratified AC wording — it never rejects a `grade`-named composite, and lets an underscore/space-spelled weighted composite (`weighted_aggregate`) through. No shipped artifact carries one (the 27-name roster is clean and `assemble_v1_measure_set` emits only that roster), but `emit_measure` is a public Epic-19 surface, so a composite CAN be minted and stored — the epic's centre-of-gravity negative is under-enforced.

---

## Per-test results

Legend: PASS = requirement demonstrated behaviourally with a named failing counter-case; FAIL = requirement violated (finding).

### L0 — static / structural gates
| Test | Req | Result | Meaning |
|---|---|---|---|
| test_s1_no_local_hashing_only_qmf_core_fingerprint | R4 | PASS | no results module invokes hashlib/sha256()/hexdigest; the sole `fp1` path is a call into qmf-core's `fingerprint` (scanner proven to flag a planted `hashlib.sha256(...)`). |
| test_s2_measure_roster_has_no_composite_token | R13 | PASS | the pinned MEASURE_IDENTITIES roster contains no score/grade/tier/weighted/rating/composite token. |
| test_s2_emit_measure_refuses_the_enforced_composite_tokens | R13 | PASS | the guard DOES refuse composite_score/tier_band/weighted_rating/perf_score/overall_rating/quality_tier (accept arm reachable via `net_profit`). |
| **test_s2_emit_measure_refuses_every_composite_the_ac_names** | **R13** | **FAIL → E19-F01** | the guard does NOT refuse `overall_grade`/`letter_grade`/`weighted_aggregate` — composites the AC names may never express a result. |
| test_s3_no_concurrency_or_mutable_global_in_results | R28,R29 | PASS | no results module imports threading/multiprocessing/spawns a Thread or rebinds a module `global` (scanner proven to flag a planted `threading.Thread(`). |
| test_s3_results_declares_no_ledger_or_log_writer | R29 | PASS | no results module references a ledger-append/operational-log sink — publish-only. |

### L1 — minimal pure-unit laws
| Test | Req | Result | Meaning |
|---|---|---|---|
| test_u1_money_is_exact_scaled_integer (hypothesis, 200 ex.) | R10 | PASS | Money magnitude and its `fp1` num/den equal `value/10**scale` exactly across random int×scale — no float drift, integer num/den. |
| test_u1_binary_float_money_is_refused_not_coerced | R10 | PASS | a float on the money path is an INVALID_INPUT refusal (refuse arm reachable). |
| test_u1_money_measure_reflects_exact_integer_sum | R10 | PASS | net_profit over exact trades is exact Money, not a float aggregate. |
| test_u2_profit_factor_with_no_losing_trades_is_undefined_not_ten | R12 | PASS | no losing trades ⇒ UndefinedMeasure(code=undefined), never PerformanceMeasure(10) or 0. |
| test_u2_sharpe_with_under_two_samples_is_insufficient_sample | R12 | PASS | <2 daily samples ⇒ UndefinedMeasure(insufficient-sample/undefined). |
| test_u2_a_genuine_zero_is_a_measure_not_undefined | R12 | PASS | net_profit==0 is a real PerformanceMeasure(0), distinguishable from undefined. |
| test_u3_null_unit_kind_is_refused_never_defaulted | R9 | PASS | emit_measure(unit_kind=None) and ExactRational(unit_kind=None) both INVALID_INPUT on field unit_kind (accept arm reachable). |
| test_u3_declared_unit_kind_must_match_quantity | R9 | PASS | a declared unit-kind mismatching the quantity is refused, not silently overwritten. |
| test_u4_series_point_shape_is_t_and_v_only | R18,R19 | PASS | each series point is exactly {t:int64-ns, v:unit-kinded}; no color/style/bin in the payload. |
| test_u4_a_banned_renderer_key_in_source_data_is_refused | R18,R19 | PASS | a color/bin in the run's own record is refused (gate proven able to fail). |

### L2 — CT-32 adoption + refusal shape
| Test | Req | Result | Meaning |
|---|---|---|---|
| test_c1_stored_artifact_is_a_valid_ct32_container | R1 | PASS | exactly one `results/ct-32.json`, all mandatory CT-32 fields, class=performance-result, no other file, no report.json; qmf-core `fp1`. |
| test_c1_a_bespoke_report_body_is_not_a_ct32 | R1 | PASS | a hand-rolled report body missing CT-32 fields is refused as a CT-32 (acceptance gate can fail). |
| test_c2_every_measure_quantity_carries_ad40_unit_kind | R8 | PASS | every computed measure carries an AD-40 unit-kind; the only alternative slot is a typed UndefinedMeasure. |
| test_c2_suppression_and_veto_counts_are_count_kind_and_default_zero | R15,R16 | PASS | tally rows carry the `count` unit-kind and default to explicit zero, never omitted. |
| test_c3_epic19_refusals_are_returned_ct04_values | cross | PASS | multi-role/non-replay/unresolvable-authority/missing-dir all RETURN a CT-04 typed value (field+reason present), never raise. |

### L3 — acceptance (Stories 19.1–19.5)
| Test | Req | Result | Meaning |
|---|---|---|---|
| test_a1_assembly_writes_one_ct32_and_returns_qmfcore_fp1 | R1 | PASS | one container written; on-disk bytes == canonical_bytes(identity); returned fp == artifact.fingerprint() == fingerprint(identity) == re-read fp. |
| test_a1_second_assembly_is_refused_exactly_one_per_run | R1 | PASS | a second assemble is a STORAGE_FAILURE; still exactly one artifact. |
| test_a2_label_carries_full_ad12_and_evidence_range_verbatim | R2 | PASS | producer identity+format-version, evidence_class, world, input[0]==run-id, occurrence identity, single account role; evidence range copied verbatim (warm-up EXCLUSION is E14 — see boundaries). |
| test_a3_ar59_stamps_enter_input_fingerprints | R3 | PASS | data/split fingerprints verbatim and registry-as-of (pinned wrapper) enter input_fingerprints. |
| test_a3_rng_provenance_present_only_when_supplied | R3 | PASS | a non-stochastic run carries no RNG input; supplying rng adds exactly one. |
| test_a4_identity_is_label_derived_and_reproduces | R4 | PASS | fingerprint(identity) is deterministic and equals artifact.fingerprint(). |
| test_a4_no_float_byte_enters_identity | R4 | PASS | the stored CT-32 JSON contains no float anywhere (walker proven to flag a planted float). |
| test_a5_multi_role_is_policy_rejection_and_writes_nothing | R5 | PASS | a >1-role result is POLICY_REJECTION; nothing written. |
| test_a6_world_comes_from_provenance_field_not_a_keys_flag | R6 | PASS | a misleading keys `world="live"` is ignored; the label records the typed provenance world (replay). |
| test_a6_simulated_world_is_refused_no_artifact_in_v1 | R6 | PASS | world=simulated ⇒ POLICY_REJECTION on field world. |
| test_a7_non_optimistic_taint_fidelity_is_refused | R7 | PASS | a calibrated (edge-claiming) taint is refused at mint (field taint); optimistic passes. |
| test_a7_artifact_carries_no_verdict_bearing_edge_claim | R7 | PASS | the artifact identity smuggles no claims_edge/verdict/split_budget token. |
| test_a8_measure_set_is_ordered_and_covers_the_v1_core | R8 | PASS | measure order == pinned roster; the enumerated V1 core set is present. |
| test_a8_every_computed_measure_carries_a_non_null_unit_kind | R8 | PASS | every PerformanceMeasure carries an AD-40 unit-kind; else a typed UndefinedMeasure. |
| test_a9_a_metric_format_version_change_moves_that_metric_identity | R11 | PASS | same identity+quantity, different metric format version ⇒ different measure identity content. |
| test_a9_every_stored_measure_pins_its_format_version | R11 | PASS | every stored measure carries a positive metric_contract_format_version in its identity. |
| test_a10_no_composite_or_verdict_token_anywhere_in_artifact | R13 | PASS | a deep key+value scan of the assembled artifact finds no score/grade/tier/weighted/rating/composite/verdict (scanner proven to flag a planted composite). |
| test_a10_the_set_is_not_collapsed_into_one_number | R13 | PASS | the artifact presents all 27 measures, never one collapsed rating; no top-level scalar verdict field. |
| test_a11_tallies_count_journal_events_by_authority_reason_and_door | R14 | PASS | suppression keyed by (authority,reason), veto by door, counted from CT-13 events; non-firing doors still explicit-zero. |
| test_a11_a_parallel_bespoke_log_cannot_move_the_tally | R14 | PASS | a plain-dict bespoke log is refused (field journal_events) — a tally can't be sourced from a non-CT-13 log. |
| test_a11_a_cross_world_event_is_refused | R14 | PASS | a live-world event in a replay tally is POLICY_REJECTION on field world. |
| test_a12_quiet_run_emits_full_roster_at_zero | R15 | PASS | a quiet run emits the full AuthorityKind×reason and door roster at count 0, never omitted. |
| test_a13_counts_are_count_kind_and_a_distinct_field_group | R16 | PASS | tallies carry `count`; TALLY_FIELD_GROUP is control-accounting; no measure identity mentions suppression/veto. |
| test_a13_artifact_keeps_tallies_separate_from_measure_set | R16 | PASS | suppression_accounting / veto_accounting are separate artifact fields from measure_set. |
| test_a14_unresolvable_authority_is_refused_not_bucketed | R17 | PASS | an unknown suppressing authority ⇒ INVALID_INPUT (field suppressing_authority), not bucketed. |
| test_a14_missing_reason_class_is_refused_not_bucketed | R17 | PASS | a missing reason_class ⇒ INVALID_INPUT (field reason_class). |
| test_a14_unresolvable_door_is_refused_not_dropped | R17 | PASS | a refused-by-door decision without a resolvable door cannot even build as a CT-13 event — a door veto is never silently dropped. |
| test_a15_each_chart_is_a_unit_kinded_series_of_t_v_points | R18 | PASS | series are {name,unit_kind,points[{t,v}]}, t int64-ns, v exact Money/ExactRational; ratio series carry the ratio unit-kind. |
| test_a15_an_image_payload_is_never_the_canonical_series | R18 | PASS | PNG bytes and a data:image/base64 string are both refused as an equity source. |
| test_a16_v1_core_series_and_worst_periods_derive_from_the_curve | R20 | PASS | equity/cum/drawdown/underwater present; ≤5 worst-periods with {start,bottom,recovery,max_drawdown}; drawdown 20% exact; equity values == the run's own curve. |
| test_a17_single_instrument_unleveraged_omits_holdings_family | R21 | PASS | holdings/exposure/allocation/leverage omitted-with-reason, never faked, on a single unleveraged run. |
| test_a17_multi_instrument_reconstructs_holdings_from_the_stream | R21 | PASS | a two-instrument run reconstructs holdings.*/exposure.* series from the position stream. |
| test_a18_no_benchmark_is_omitted_with_note_never_faked | R22 | PASS | no benchmark ⇒ benchmark_identity None and an explicit "no benchmark declared" omission; no faked benchmark series. |
| test_a18_declared_benchmark_identity_is_recorded | R22 | PASS | a declared benchmark identity is recorded in the artifact. |
| test_a19_downsample_declares_its_sampler_and_is_excluded_from_identity | R23 | PASS | a display downsample declares its sampler identity, is marked in_identity=False, and carries no fp1_identity (AD-10-excluded structurally). |
| test_a19_artifact_identity_is_invariant_to_charts_and_downsample | R23 | PASS | the CT-32 identity contains no chart/downsample/html token — the artifact fp is invariant to chart presence. |
| test_a20_render_is_byte_stable_and_reads_the_same_from_object_or_bytes | R24 | PASS | rendering is byte-stable and identical from the object or its stored bytes — pure function of the artifact. |
| test_a20_renderer_cannot_invent_a_value | R24 | PASS | a template token with no stored field is refused — the renderer fabricates nothing. |
| test_a21_headline_shows_world_and_role_verbatim | R25 | PASS | HTML header and markdown H1 carry world=replay and account-binding-role=demo verbatim. |
| test_a21_a_different_role_changes_the_headline_verbatim | R25 | PASS | a paper-validation role changes the headline verbatim (tracks the stored role, not a constant). |
| test_a22_interpretation_reads_the_artifact_not_a_rendering | R26 | PASS | explain_run reads the artifact; given the rendered HTML it refuses (field artifact) — agents never parse HTML. |
| test_a22_compare_and_flag_also_consume_the_artifact | R26 | PASS | compare_runs / flag_refusal_heavy consume the artifact and refuse a rendering. |
| test_a23_identical_inputs_reproduce_the_fingerprint | R27 | PASS | identical inputs mint an identical fp; require_reproduced_fingerprint returns it. |
| test_a23_a_mismatch_is_a_typed_refusal_never_silently_tolerated | R27 | PASS | a differing run mints a different fp; a mismatch is POLICY_REJECTION (field ct32_fingerprint), never silently tolerated. |
| test_a24_refuse_downstream_act_refuses_every_act_with_no_allow_arm | R29 | PASS | every forbidden act + every PublishAct is POLICY_REJECTION; an unknown act is INVALID_INPUT — no input returns Ok (no allow arm). |
| test_a24_publish_act_enum_covers_size_promote_bench_and_mode | R29 | PASS | the forbidden-act vocabulary covers size/promote/bench/change_mode/bind. |

### L4 — golden scenario (SCN-0012 tail, co-owned with Epic 14, R-016)
| Test | Req | Result | Meaning |
|---|---|---|---|
| test_scn0012_run_return_assembles_one_ct32_replay_artifact | R-016 | PASS | a real E14 `run()` return assembles into exactly one world=replay CT-32 with the full label and the pinned unit-kinded measure order; label.evidence_time_range == the loop's trading interval. |
| test_scn0012_step8_verdict_is_absent_from_the_artifact | R-016 | PASS | the step-8 verdict is reader-derived and absent from the stored artifact (no score/grade/tier/verdict/pass_fail token). |

### L5 — concurrency isolation
| Test | Req | Result | Meaning |
|---|---|---|---|
| test_concurrent_assembly_is_isolated_and_deterministic | R28 | PASS | 14 concurrent mint+assemble into 14 distinct dirs each write their own artifact; every fp matches its single-threaded value; 14 distinct artifacts (no cross-run aliasing). |
| test_same_config_across_threads_yields_one_fingerprint | R28 | PASS | the same config across 24 concurrent computations yields one stable fp — no shared mutable render state. |

### L6 — adversarial review
One adversarial pass over the six modules against the four load-bearing laws (no stored verdict/no composite; float-identity ban; provenance-derived world; publish-only). One confirmed finding (E19-F01, pinned by the failing L0 test). Advisory-only observations recorded below (no requirement violated).

---

## Finding

**E19-F01 (R13, medium) — composite-expression guard is incomplete vs the ratified AC.**
`qmf.risk.performance.FORBIDDEN_COMPOSITE_EXPRESSIONS` (reached from the public Epic-19 `emit_measure` → `PerformanceMeasure.try_create`) rejects `score`/`rating`/`tier`/`composite` (and their substrings) but **omits `grade` entirely** and only substring-matches its **hyphenated** members, so `overall_grade`, `letter_grade`, `grade`, and `weighted_aggregate` are accepted and storable, while `weighted_composite` is caught only incidentally via `composite`. AC19.2 / R-RPT-10 / DEC-0162 name "grade" and "weighted rating/aggregate" as composites that may never express a result. No shipped artifact carries one (the 27-name roster is clean; `assemble_v1_measure_set` emits only the roster), so the artifact-level negative (test_a10, PASS) holds — but the **guard** under-enforces the epic's centre-of-gravity negative on a public surface. Root cause is the qmf-risk vocabulary (Epic 10, Story 10.10 — cross-epic); recorded here because R13 is Epic-19-owned. Regression pin: `test_s2_emit_measure_refuses_every_composite_the_ac_names` (goes green when `grade` and an underscore/space-normalized weighted composite are rejected).

---

## Scope narrowings & boundaries (UNPROVEN-at-Epic-19 — recorded, not counted as pass/fail)

- **R2 warm-up exclusion → Epic 14.** Epic 19 copies `evidence_range` into the label verbatim (proven: test_a2, and SCN shows the real post-warmup interval flowing through). The "trading interval only, **never warm-up**" *computation* is the E14 `run()` loop's; Epic 19 cannot and does not enforce it. Owning epic: E14.
- **R7 "cannot spend split budget" → Epic 17 ports.** Epic 19 stamps the optimistic taint and refuses a non-optimistic (edge-claiming) taint at mint (proven: test_a7). The split-budget/edge-claim *refusal function* (`refuse_optimistic_edge_claim`) lives in `qmb.execution.ports`; its own enforcement is E17/GAP-0048.
- **The read-time verdict fold (§7.1) → qmb.md B-4 / Epic 15 reader.** Per-requirement outcomes, `not-yet-ruled`, re-verdict-on-ruling, the canonical-assignment qualifier, and replay-never-gates-live *enforcement* are downstream of the Epic-15 ledger. Epic 19 proves only the artifact's *inputs* (A2/A3/A8/A9/A11/A7) and the *absence* of a stored verdict (A10, SCN). Not built here.
- **Ledger line + R-RPT-17 tension (§7.2) → Epic 15.** "Exactly one ledger line per run" is Epic 15's. **Documented conflict:** spec-reports R-RPT-17 says the ledger stores one structural pass/fail line, but ratified DEC-0162 / CT-32 (L33) / qmb.md B-4 say a verdict is **never stored** — the ratified corpus governs. Epic 19 tests the never-stored discipline (A10); the conflict is flagged for the Epic-15 auditor, not resolved here.
- **Metric numeric correctness (§7.3) → per-metric contract.** Epic 19 pins each measure's unit-kind, exactness, format-version, and undefined/refusal discipline — **not** the numeric value of any Sharpe/Sortino/Calmar against an invented oracle (SCN-0012: "no fixture number to freeze"; L6/DEC-0007 forbids product mock data). Untestable here without fabricating a golden number.
- **GAP-0048 fidelity content (§7.4) → Epic 17.** Whether a fill is correctly modeled (fidelity taxonomy, forex calibration, `world=simulated` unlock) is decided-deferred. Epic 19 stamps the taint and the non-edge-claiming property only.
- **Benchmark-relative math (§7.5).** Testable now and proven: omitted-with-note when no benchmark, identity-recorded when present (A18). The alpha/beta/info-ratio math when a benchmark IS present is extended-tier — not gated in this T3 pass.

## Advisory observations (no requirement violated; not findings.csv rows)

- **A1 — `assemble_run_performance_result` edge-claim guard is a constant.** It calls `refuse_optimistic_edge_claim()` with the module default taint, so at assembly time it can never fail on real data; the data-driven taint refusal is the mint path (`_refuse_edge_claim`/`_fidelity_input`, proven by test_a7). Harmless (mint already enforced), but a hollow guard.
- **A2 — the assembly's `if "chart" in identity or "html" in identity` guard is a top-level key check** on the CT-32 identity dict; since charts/HTML are never CT-32 keys it is dead-defensive and would not catch a nested key. Structurally the CT-32 identity excludes charts, so no artifact is at risk.
- **A3 — float-derived transcendental metrics (CAGR/Sharpe/Sortino via `**`/`math.sqrt`) are snapped to an exact rational at scale 12 before entering identity** (so no float byte enters identity — A4 holds, reproduction A23/SCN holds on one platform). Cross-platform libm differences could in principle change the rounded rational; that degrades to a reproduction **refusal** (R27 permits "reproduce exactly OR typed refusal"), never a silent wrong value. Low reproducibility-fragility note only.

---

## Traceability (requirement → tests → result)

| Req | Prio | Tests | Result |
|---|---|---|---|
| R1 | P0 | C1, A1 (×2) | PASS |
| R2 | P0 | A2 | PASS (warm-up exclusion = E14 boundary) |
| R3 | P1 | A3 (×2) | PASS |
| R4 | P0 | S1, A4 (×2) | PASS |
| R5 | P0 | A5 | PASS |
| R6 | P0 | A6 (×2) | PASS |
| R7 | P1 | A7 (×2) | PASS (split-budget refusal = E17 boundary) |
| R8 | P0 | C2, A8 (×2) | PASS |
| R9 | P0 | U3 (×2) | PASS |
| R10 | P1 | U1 (×3) | PASS |
| R11 | P1 | A9 (×2) | PASS |
| R12 | P1 | U2 (×3) | PASS |
| R13 | P0 | S2 (×3), A10 (×2) | **PARTIAL — E19-F01** (artifact clean; guard under-enforces `grade`/`weighted_aggregate`) |
| R14 | P1 | A11 (×3) | PASS |
| R15 | P1 | C2, A12 | PASS |
| R16 | P1 | A13 (×2) | PASS |
| R17 | P1 | A14 (×3) | PASS |
| R18 | P0 | U4 (×2), A15 (×2) | PASS |
| R19 | P1 | U4 (×2) | PASS |
| R20 | P1 | A16 | PASS |
| R21 | P1 | A17 (×2) | PASS |
| R22 | P1 | A18 (×2) | PASS |
| R23 | P1 | A19 (×2) | PASS |
| R24 | P0 | A20 (×2) | PASS |
| R25 | P0 | A21 (×2) | PASS |
| R26 | P1 | A22 (×2) | PASS |
| R27 | P0 | A23 (×2) | PASS |
| R28 | P1 | S3, SYS (×2) | PASS |
| R29 | P0 | S3 (×2), A24 (×2) | PASS |
| R-016 | — | SCN (×2) | PASS |
| cross | — | C3 | PASS |

**Exit-gate assessment:** All 13 P0 requirements green. All P1 green except R13, which is PARTIAL with a recorded finding (E19-F01) and an owner (root cause qmf-risk vocabulary / Epic 10; requirement Epic 19). The three §3 gates hold behaviourally — CT-32 adopted-not-reinvented (C1/A1), verdict-never-stored + publish-only (A10/S2/S3/A24, artifact-clean), identity integrity + replay-never-gates-live (S1/A4/A6/A21/A7/A23) — with the single caveat that the composite *guard* (not the shipped artifact) is incomplete. The L4 golden scenario confirms the verdict is absent from the artifact. The L6 pass is recorded; its one confirmed finding is pinned by a failing test.
