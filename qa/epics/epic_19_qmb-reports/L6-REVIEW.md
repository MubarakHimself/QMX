# L6 REQUIREMENTS-FIDELITY REVIEW — Epic 19 (qmb-reports)

**Reviewer question, one per test:** does the assertion state what the requirement
demands (FR/AR/CT/SCN/AC id cited), or what the implementation happens to do?

**Scope check (EPIC-BINDING RULE):** every requirement judged below is confirmed
present in Epic 19's section of `_bmad-output/planning-artifacts/epics.md`
(lines 3730–3968, Stories 19.1–19.5) and in the PLAN's R1–R29 table. Clauses
owned by other epics are named as boundaries, not tested and not filed.

---

## VERDICT: **gaps**

The suite is unusually strong on Stories 19.1, 19.2, 19.3 and 19.5's refusal
discipline — real fakes, returned CT-04 refusals asserted by category **and**
context field, several genuine falsifiability probes (planted `hashlib.sha256(`,
planted `threading.Thread(`, planted float, planted composite key, a misleading
`keys["world"]="live"` flag, a role-varying headline counter-case), a real
`run()` return at L4, and a real 14-thread L5. The one FAIL is a correctly
reasoned, correctly scoped, genuine finding.

It is nevertheless **gaps**, on two independent grounds:

1. **One P0 requirement (R18) is scored green while the shipped code violates
   it.** Chart series are never emitted *in the artifact*. R-RPT-11 — which R18
   cites — reads: *"Every chart MUST be emitted as a machine-readable series **in
   the artifact**, not as an image."* CT-32's QMB-adoption invariant makes chart
   series a **declared extension of the container**. The code does the opposite,
   by design and in writing (`mint_run_performance_result` docstring: *"Chart
   series and HTML are not emitted."*). Three assertions in the suite actively
   bless the omission, and one of them would **fail if the code were fixed**.
2. **Several greens are structurally hollow under the HARDENED AUTHOR CONTRACT**
   — the module's own constants, rosters, enums, marker flags and identity
   functions are used as the oracle (banned shape 2 and "calling a function
   against its own lookup table"), and R29 (P0) states absence-of-effect by
   trusting a guard function's return rather than observing a test-owned sink
   (rule 3).
3. **Rule 5 (scope honesty) is breached in five places**: narrowings that are
   neither tested nor recorded as UNPROVEN in RESULTS.md. RESULTS.md's seven
   recorded boundaries are all *cross-epic delegations*; not one of the
   within-Epic-19 narrowings below is disclosed. findings.csv is therefore not
   legitimately one row (rule 6).

P0 scoreboard after this review: **11 of 13 P0 requirements survive as green**
(R1, R5, R6, R8, R9, R13-artifact-half, R24, R25, R27 hold up; R2 and R4 hold in
substance but on partly tautological evidence). **R18 fails.** **R29 is
UNPROVEN.**

---

## 1. THE ONE THAT MATTERS — R18 (P0): chart series are not in the artifact

**Requirement.** Epic 19 intro: *"the artifact holds the QMX-native measure set …
chart data is emitted as series, never images; and every human-facing rendering,
interpretation, and reproduction is a pure downstream function of the artifact —
agents read the artifact, never renderings."* AC19.4 + R-RPT-11 + R-RPT-12;
CT-32 invariant (DEC-0163): *"chart series and trade-event references are
DECLARED QMB EXTENSIONS of this container."* PLAN R18 = **P0**.

**Evidence (source, read-only).**

- `qmb/src/qmb/results/ct32.py:174` — `mint_run_performance_result` docstring:
  *"Chart series and HTML are not emitted."* No chart parameter exists.
- `packages/qmf-risk/src/qmf/risk/performance.py:510-549` — the CT-32
  `PerformanceResult` container has fields `result_label, account_binding_role,
  population, period, measure_set, suppression_accounting, veto_accounting,
  baseline_pointer`. **No chart-series field, no trade-event-reference field** —
  the two declared QMB extensions are absent from the container.
- `assemble_v1_chart_set` has **no caller anywhere in the run/assembly path** —
  only re-exports (`qmb/results/__init__.py`, `qmb/doors/api/__init__.py`,
  `qmb/__init__.py`). `charts.py` is 1,406 lines reachable only by an external
  caller who already knows to ask.
- `assemble_run_performance_result` writes `results/ct-32.json` and nothing else;
  `render.py` and `interpret.py` contain **zero** references to `chart` or
  `series`. An agent obeying R26 ("read the artifact, never a rendering") can
  never obtain chart data for a run.

**How the suite scored this green.** R18's tests (`test_u4_*`, `test_a15_*`) call
`assemble_v1_chart_set` **directly as a standalone library**, prove the series
shape is right, and stop. The shape assertions are good; the requirement is
"in the artifact", and nothing asserts a stored artifact carries a series.

**Three assertions lock the omission in:**

| Test | Assertion | Why it is wrong-expectation |
|---|---|---|
| `test_c1_stored_artifact_is_a_valid_ct32_container` | `all_files == ["ct-32.json"]` | Reads as "no second report JSON" (R1) but also certifies that **no chart payload is emitted anywhere in the run output**. |
| `test_a19_artifact_identity_is_invariant_to_charts_and_downsample` | `"chart" not in flat` | Vacuously true: charts never touch the artifact. Asserts an omission as if it were AD-10 exclusion. |
| `test_a19_downsample_declares_its_sampler_and_is_excluded_from_identity` | `assert not hasattr(ChartSet, "fp1_identity")` | **Would FAIL once the code is fixed.** A CT-32 declared-extension chart set needs a canonical identity representation; this test forbids one. |

**Filing.** This belongs in findings.csv as a **high** row against R18 (P0), test
path `qa/tests/epic_19/test_l3_story_19_4_charts.py` (no covering test exists —
the row is `observed=UNPROVEN`/violation, per rule 6). It is Epic-19-owned:
Story 19.4 is Epic 19's, R18 is in the PLAN's Epic-19 table.

---

## 2. WRONG-EXPECTATION TESTS

Ordered by severity. "Wrong expectation" = the assertion's oracle is the
implementation (its constants, its enums, its own identity functions, its own
structural omissions) rather than the requirement.

### 2.1 `test_a24_refuse_downstream_act_refuses_every_act_with_no_allow_arm` and `test_a24_publish_act_enum_covers_size_promote_bench_and_mode` — R29 (**P0**)

```python
acts = set(DOWNSTREAM_FORBIDDEN_ACTS) | {m.value for m in PublishAct}
for act in acts: assert is_refusal(refuse_downstream_act(act))
...
covered = {m.value for m in PublishAct}
assert {"size","promote","bench","change_mode"}.issubset(covered)
```

The first calls a refusal function **against its own lookup table**; the second
asserts an **enum's membership** as if it were behaviour. Both are named banned
shapes. R29 demands: *"Given rendering, interpretation, and reproduction all run
… none has sized, promoted, benched, bound, or changed a mode."* The requirement
is about what `render_report` / `explain_run` / `compare_runs` /
`require_reproduced_fingerprint` **do while running** — observed through a
test-owned sizing/promotion/bench/mode-change sink that records nothing (rule 3:
*state absence-of-effect by observing the sink, not by trusting a returned
flag*). No such sink exists in the suite. The only other R29 evidence is
`test_s3_results_declares_no_ledger_or_log_writer`, a grep for five
author-invented token strings (`append_ledger`, `ledger_line`, `write_log`,
`operational_log`, `emit_log`) with **no falsifiability probe** and no check that
those are the real sink names — it would pass vacuously against any differently
named sink. **R29 (P0) is UNPROVEN, not green.**

### 2.2 `test_a14_unresolvable_door_is_refused_not_dropped` — R17

Tests `qmf.data.journal.JournalEvent.try_create` — **another epic's surface** —
and concludes *"a door veto is never silently dropped."* Epic 19's actual door
folder says otherwise (`qmb/src/qmb/results/accounting.py:127-139`):

```python
door = _payload_token(event.payload, _DOOR_KEYS)
if door is None:  return invalid("refusing_door", "... unresolvable doors are a typed refusal, never dropped or silently bucketed ...")
counts[door] = counts.get(door, 0) + 1      # <-- ANY door token becomes a new key
```

Only an **absent** token refuses. An unrostered door string (`"mystery-door"`)
is silently bucketed into a brand-new tally key, outside the ratified
`VETO_DOOR_IDENTITIES` spine roster (AD-36/DEC-0150) — precisely the "silently
bucketing" the module's own refusal message disclaims. The sibling authority
path (`_resolve_authority`) does close its vocabulary and refuse, which is why
`test_a14_unresolvable_authority_is_refused_not_bucketed` is a good test. Had
this test driven the Epic-19 surface with an unrostered door, it would have found
the asymmetry. Same hole one level over: `_suppression_key` accepts **any**
non-empty reason string as a new key; only a missing key refuses. AC19.3 names
"authority **or reason**".

### 2.3 `test_a16_v1_core_series_and_worst_periods_derive_from_the_curve` — R20

```python
assert set(V1_CHART_SERIES_NAMES).issubset(names)
```

The oracle is the module's own constant — and that constant is exactly four
names (`equity`, `cumulative_returns`, `drawdown`, `underwater`,
`charts.py:59-64`). AC19.4 enumerates the V1 chart set as *"equity curve,
cumulative returns, drawdown/underwater with a top-5 worst-periods table,
**monthly-returns grid**, and **monthly-return + trade-P&L distributions as raw
histogram-ready arrays**."* The implementation **does** build all of them
(`ChartSet.monthly_returns`, `AnnualReturnCell`, `monthly_return_distribution`,
`trade_pnl_distribution`, `HistogramReadyArray`) — the test simply adopted the
narrower constant and so **no test touches the three the constant omits**. The
worst-periods and drawdown-exactness half of this test is genuinely good.

### 2.4 `test_a19_*` — R23 (both tests)

```python
assert data["sampler_identity"] == "stride-nth"
assert data["in_identity"] is False
assert data["ad10_excluded"] is True
```

`in_identity` and `ad10_excluded` are **self-declared markers** — banned shape 2
verbatim. A module can set `ad10_excluded = True` and still fold the payload into
identity. The structural `not hasattr(...)` checks are better but, as §1 shows,
they are true only because charts never reach the artifact at all — so R23
("AD-10-excluded from **the artifact's** identity, never the canonical payload")
is proven against a world where there is no canonical payload to exclude.

### 2.5 `test_c1_stored_artifact_is_a_valid_ct32_container` — R1 (**P0**)

`MANDATORY_CT32_FIELDS` in the test is the **same eight names, same content** as
the implementation's private `_REQUIRED_CT32_FIELDS` (`ct32.py:130-139`). The
test validates the artifact against the code's own required-field list. It
happens to agree with CT-32's ratified nullability clauses for
label/population/period/accounting/role — but it drops two fields the CT-32
schema declares (`population_edge`, `baseline_pointer`) with no recorded
narrowing. The rest of this test (on-disk file count, `class`, world verbatim,
`fp1:sha256:` prefix, plus the `test_c1_a_bespoke_report_body_is_not_a_ct32`
counter-case) is sound.

### 2.6 `test_a2_label_carries_full_ad12_and_evidence_range_verbatim` — R2 (**P0**)

```python
assert label.producer_contract_identity == ok(fingerprint(result_identity()))
assert label.computation_identity     == ok(fingerprint(label.fp1_identity()))
```

Both expected values are computed by **calling the implementation's own identity
functions** — the code checked against itself. Any `result_identity()` content
whatsoever satisfies the first; any label content satisfies the second. Also
`evidence_class is PROVISIONAL` and `account_binding_role is DEMO` assert the
implementation's private defaults (`_REPLAY_EVIDENCE_CLASS`,
`_REPLAY_ACCOUNT_ROLE`), not values the AC names. What *is* genuine here and
carries R2: `input_fingerprints[0] == config().fingerprint` (test-owned config)
and `evidence_time_range == ev` (test-owned interval, verbatim copy).

### 2.7 `test_a4_identity_is_label_derived_and_reproduces` — R4 (**P0**)

```python
once = fingerprint(identity); twice = fingerprint(identity)
assert once == twice == artifact.fingerprint()
```

A tautology: the same input through the same pure function. It proves
determinism, not *"identity is label-derived per AD-10"*. The falsifiable form —
mutate one **label** field and require fp1 to move; mutate a declared
non-identity field and require fp1 to hold — is never written. R4 survives on
the genuinely good `test_a4_no_float_byte_enters_identity` (walker with a planted
float) and `test_s1` (scanner with a planted `hashlib.sha256(`), plus
`test_a23`'s stream-order counter-case. Keep R4 green, on that evidence, not on
this test.

### 2.8 Self-declared-constant oracles (a family)

| Test | Self-declared oracle | Note |
|---|---|---|
| `test_s2_measure_roster_has_no_composite_token` | `MEASURE_IDENTITIES` | Scans the code's own roster. Redeemed by `test_a10`'s deep artifact scan. |
| `test_a8_measure_set_is_ordered_and_covers_the_v1_core` | `order == list(MEASURE_IDENTITIES)` | Redeemed by the test-owned `EXPECTED_CORE` subset check on the next line. "Ordered" is never proven as *stable across two mints*. |
| `test_a10_the_set_is_not_collapsed_into_one_number` | `len(...) == len(MEASURE_IDENTITIES)` | Redeemed by `len > 1` and the sibling deep scan. |
| `test_a12_quiet_run_emits_full_roster_at_zero` | set-equality against `AuthorityKind × SUPPRESSION_REASON_CLASSES` and `VETO_DOOR_IDENTITIES` | Would pass against an **empty** roster. Redeemed by `test_a11`'s literal `by_veto["bench"] == 0` (test-owned door name) and `test_c2`'s `assert suppressions and vetoes`. |
| `test_a13_counts_are_count_kind_and_a_distinct_field_group` | `TALLY_UNIT_KIND is UnitKind.COUNT`; `TALLY_FIELD_GROUP == "control-accounting"` | Two pure self-declarations. Redeemed by the per-row `fp1_identity()["unit_kind"]` loop and `test_a13_artifact_keeps_tallies_separate_from_measure_set`. |

None of these is fatal on its own — each has a behavioural sibling — but they
inflate the green count and should not be cited as independent evidence.

### 2.9 Minor

- `test_a3_rng_provenance_present_only_when_supplied` — asserts
  `len(stochastic) == len(base) + 1`. A **count**, not the content: any extra
  input fingerprint satisfies it. Contrast the sibling `test_a3_ar59_stamps…`,
  which correctly recomputes the expected data/split/registry fingerprints
  test-side. Fix by recomputing the RNG-provenance fingerprint the same way.
- `test_a15_an_image_payload_is_never_the_canonical_series` — asserts only
  `is_refusal`, with no category/field. Passing `bytes`/`str` where an
  `EquityPoint` tuple belongs would be refused as a plain type error; the test
  cannot distinguish "images are rejected as a payload" from "wrong type".
  (`test_u4_a_banned_renderer_key_in_source_data_is_refused` is the good one —
  the refusal is key-driven, `field == "renderer"`, `BANNED_RENDERER_KEYS`
  confirmed at `charts.py:76-88`.)
- `test_l5_concurrency.py` docstring claims "assembly/**render** … no shared
  mutable render state"; only mint+assemble run concurrently. `render_report` is
  never called on a thread. The test is otherwise excellent (distinct dirs,
  single-threaded baseline comparison, N distinct fingerprints).
- `test_s1` — `assert "fingerprint" in ct32` is implied by the preceding
  `"from qmf.core.fingerprint import" in ct32`; it adds nothing.

### Tests that are exemplary (cited so the rework does not damage them)

`test_a6_world_comes_from_provenance_field_not_a_keys_flag` (a genuinely
misleading `keys["world"]="live"`), `test_a11_a_parallel_bespoke_log_cannot_move_
the_tally`, `test_a11_a_cross_world_event_is_refused`,
`test_a14_unresolvable_authority_is_refused_not_bucketed` (verified against the
closed `AuthorityKind` = operator | book_policy | protection_authority |
venue-delegated | adapter_self — `"kill-switch"` is genuinely unrostered),
`test_u2_*` (undefined ≠ zero, all three arms), `test_u3_*`,
`test_a21_a_different_role_changes_the_headline_verbatim`,
`test_a22_interpretation_reads_the_artifact_not_a_rendering`,
`test_a23_a_mismatch_is_a_typed_refusal_never_silently_tolerated`,
`test_a16`'s exact `Fraction(1,5)` drawdown, and both L4 golden-scenario tests
(a real `run()` return, not a fixture).

---

## 3. MISSED REQUIREMENTS — Epic 19 clauses with NO covering test

All confirmed present in this epic's `epics.md` section. Ranked.

| # | Epic 19 clause (AC · req) | Status |
|---|---|---|
| M1 | **AC19.4 / R18 / R-RPT-11 — every chart emitted as a series *in the artifact*.** | **VIOLATED** (§1). No test asserts a stored artifact carries any series; three assertions bless the absence. |
| M2 | **AC19.5 / R29 (P0) — render + interpret + reproduce size/promote/bench/bind/change-mode nothing, observed while they run.** | **UNPROVEN** (§2.1). No test-owned sink; only a guard-vs-own-table test and a token grep. |
| M3 | **AC19.4 / R20 — monthly-returns grid (+ annual column), monthly-return distribution, trade-P&L distribution as raw histogram-ready arrays.** | Implemented (`ChartSet.monthly_returns`, `monthly_return_distribution`, `trade_pnl_distribution`, `AnnualReturnCell`, `HistogramReadyArray`), **zero tests**. Narrowed silently via `V1_CHART_SERIES_NAMES` (§2.3). |
| M4 | **AC19.2 / R10 — "time measures (durations, underwater period, drawdown recovery) are int64 UTC-ns or a typed `duration`".** | **Untested half of a requirement scored PASS.** U1×3 are all money. No test asserts `max_drawdown_recovery` / underwater carries the `duration` unit-kind or an int64-ns representation. Not recorded as UNPROVEN — rule 5. |
| M5 | **AC19.3 / R17 — an *unresolvable* (present-but-unrostered) door, and an unrostered reason class.** | **Untested, and the code buckets both into new tally keys** (§2.2). The door test proves an upstream constructor law instead. |
| M6 | **AC19.1 / R3 — fidelity identity (adapter-id + composition-version + taint) stamped into the label.** | `_fidelity_input` (`ct32.py:864-903`) folds it into `input_fingerprints`; `test_a3` asserts data/split/registry only, never the fidelity fingerprint. `composition_version` appears in no test. |
| M7 | **AC19.4 / R21 — leverage series on a leveraged run.** | Both A17 cases pass `leveraged=False`. The `leverage` series is never produced by any test; only its *omission* is asserted. |
| M8 | **AC19.5 / R24 — the on-disk render path.** | `render.write_run_renders` (writes `results/report.md`) has **no test**. Also R24's "adding no computation and deriving no new number" is never observed (no check that every numeral in the render appears in the artifact); A20 proves byte-stability + an unknown-token refusal only. |
| M9 | **AC19.3 final clause / R-RPT-22 — an interpretation skill can attribute action count to control authority vs strategy decision without re-deriving anything.** | No test. `flag_refusal_heavy` is exercised only for `refusal_bearing is False` on a quiet run. |
| M10 | **R1 "CT-32 adopted, not reinvented" — container clauses never asserted:** population as a *fingerprinted declaration* (AD-29 binding epoch cited by fingerprint, never interval); period's calendar identity + version and knowledge-time bound; `population_edge` (continues-performance only, never carries-ledger); `baseline_pointer` and its UNAVAILABLE_DEPENDENCY refusal. | Untested. The container type is qmf-risk's (Epic 10) so the *implementation* is a boundary — but Epic 19's `MANDATORY_CT32_FIELDS` silently drops two CT-32 schema fields, and `RefusalCategory.UNAVAILABLE_DEPENDENCY` is admitted to the allowed set in `_assert_ct04` while never being exercised. Record as a narrowing with owner. |

**Boundaries correctly excluded** (verified against the epic text; RESULTS.md
already records all seven and names an owner for each): warm-up-exclusion
computation → E14; split-budget/edge-claim refusal function → E17/GAP-0048; the
read-time verdict fold → E15; the ledger line and the R-RPT-17-vs-DEC-0162
conflict → E15 (correctly flagged, correctly not resolved here); per-metric
numeric correctness → the metric's own producer contract; GAP-0048 fidelity
content → E17; alpha/beta/info-ratio math → extended tier. These are honest and
well argued.

---

## 4. findings.csv — per-row verdict

| Row | Verdict |
|---|---|
| **E19-F01** — `emit_measure` accepts `grade` / `overall_grade` / `letter_grade` / `weighted_aggregate` as measure identities (R13, AC19.2, R-RPT-10, DEC-0162) | **GENUINE VIOLATION.** Independently confirmed: `FORBIDDEN_COMPOSITE_EXPRESSIONS` has no `grade` token and its `weighted-*` members are hyphenated, so they substring-match only hyphenated identities; `weighted_composite` is caught incidentally via `composite`. The AC names "grade" and "weighted rating" explicitly. Reached through the exported Epic-19 surface `emit_measure`, so a composite is mintable and storable. Epic-binding respected (R13 is Epic-19-owned; cross-epic root cause named without being tested there). Severity `medium` is defensible — the shipped 27-name roster is clean and `test_a10` confirms no artifact carries one. Description, expected and observed are all accurate. The FAIL doubles correctly as a regression pin. |

**Rows that should exist and do not** (rule 6: an all-but-empty findings.csv is
legitimate only if RESULTS.md shows every owned requirement green under rules
1–5):

| Missing row | Kind | Requirement |
|---|---|---|
| Chart series are never emitted in the artifact; `assemble_v1_chart_set` has no caller in the run path; the CT-32 container has no chart field; no chart payload is written to the run output dir | **genuine violation, high** | R18 (P0) · AC19.4 · R-RPT-11 · CT-32 QMB-extension invariant |
| R29's publish-only property is never observed through a test-owned sink while render/interpret/reproduce run | **UNPROVEN** | R29 (P0) · AC19.5 · R-RPT-9 |
| An unrostered `refusing_door` (and an unrostered `reason_class`) is silently bucketed into a new tally key rather than refused | **genuine violation, medium** | R17 · AC19.3 · R-RPT-8 · AR-13 |
| Time-measure exactness (int64 UTC-ns / typed `duration`) has no test | **UNPROVEN** | R10 · AC19.2 · R-RPT-4 |
| Monthly-returns grid + the two histogram-ready distributions have no test | **UNPROVEN** | R20 · AC19.4 · R-RPT-13 |
| Fidelity identity's entry into the label is not asserted | **UNPROVEN** | R3 · AC19.1 · AR-59 |
| `write_run_renders` (on-disk render) untested; "renderer computes nothing" not observed | **UNPROVEN** | R24 (P0) · AC19.5 · R-RPT-21 |

**RESULTS.md corrections required:** R18 PASS → FAIL; R29 PASS → UNPROVEN; R20,
R23, R10, R3, R17, R24 PASS → PARTIAL with the narrowing stated; the exit-gate
line "All 13 P0 requirements green" is not supportable.

---

## 5. What a rework must not do

The chart fix (`M1`) is a **source** change and belongs to the factory lane, not
to this audit — the audit's job is the finding. When it lands, three assertions
must change with it: `test_a19`'s `not hasattr(ChartSet, "fp1_identity")` and
`"chart" not in flat`, and `test_c1`'s `all_files == ["ct-32.json"]`. Until then
they must stay in place **with the finding filed against them**, so the green
does not read as coverage. No test in this suite may be relaxed to accommodate
the current behaviour.
