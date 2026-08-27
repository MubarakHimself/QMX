# L6 REVIEW — Epic 7: qmf-indicators (requirements-fidelity, adversarial)

**Verdict: gaps.**

The suite is broad, honestly documented, and several gates are genuinely strong (A5 non-mutation
against the real `talib` global; A6 injected re-implementation arms; A24 mint/no-mint arms; the
independently-stated `_CONTRACT_IDENTITY_ELEMENTS` oracle in `test_contract_l2.py`). But the epic's
**headline gate is not proven by a number**, one **P0 clause of R25 is silently narrowed**, one
requirement (R20) is excluded with no `findings.csv` row, and the R5 dependency tests are written to
what the implementation ships rather than to what the AC demands — which masks a **probable real
source defect** (undeclared `numpy`). `findings.csv` therefore reports zero defects while at least
one is visible from the read.

Scope note: judged against Epic 7's own section of `_bmad-output/planning-artifacts/epics.md`
(Stories 7.1–7.6), `docs/contracts/ct-16-indicator.yaml`, and the PLAN's R1–R32 register. No test was
run or edited; source was read as evidence only.

---

## 1. Wrong-expectation / hollow tests

Ordered by severity. Each names the requirement clause the test was supposed to bind and what it
binds instead.

### 1.1 No numeric oracle anywhere — R9, R29, R30 (P0, Gate 1) — **highest**

`ReferenceKernel._run_reference` (`packages/qmf-indicators/src/qmf/indicators/batch.py:376`) calls
`reference_fn(array, timeperiod=period)`, i.e. the live TA-Lib function, then rescales to integers.
**No test in `qa/tests/epic_07/` ever compares a produced value to the reference function's own
output.** The only use of `talib` in the whole suite is `get_compatibility`/`set_compatibility` in
`test_a5_package_never_mutates_the_reference_process_global_configuration`.

Story 7.2 demands "canonical arithmetic is *provably* the arithmetic used" and "wrapping the
reference is mandatory and it is canonical". What is actually asserted is:
- a self-declared ownership registry is internally consistent (`ownership_conformance_defects()`),
- the named reference function *exists* (`reference_grounded_defects()`),
- resolution *refuses* when the reference status is refused (`test_a6_reference_owned_formula_requires_the_verified_reference` — the one genuinely behavioural arm),
- batch == streaming (`test_a13`, `test_a22`).

The equality law cannot substitute: `StreamingIndicator._recompute()` calls `compute_batch`
(`streaming.py:1074`), so **both sides of every equality assertion run the same kernel through the
same code path**. A rescaling, rounding, descaling, or lookback-counting error in
`_run_reference` — or a wholesale re-implementation that still declared the right delegate — leaves
all 95 tests green.

A falsifiable counter-case is trivially constructible and costs nothing: compute
`talib.SMA(numpy.asarray([...]), timeperiod=3)`, rescale by the test's own rule, and compare to
`compute_batch(...).outputs["sma"]`; inject a `bias=1` kernel to confirm it can fail. RESULTS §7
excludes this as "inherited from the pinned reference by construction … no fabricated golden number
(DEC-0007)". **The reason is mis-stated** — a live call to the pinned reference is an oracle, not a
fabricated golden number. Under rule 5 this is a silent narrowing of a P0 clause; under rule 1 the
requirement should have been UNPROVEN rather than green.

### 1.2 `test_a3_pyproject_declares_every_dependency` — R5 — **masks a probable defect**

```python
assert "qmf-core" in text
assert "ta-lib==0.7.1" in text
```

Two hardcoded substrings that happen to be present. The AC says *"its pyproject.toml declares **every**
dependency"* and *"at the Tier-2 isolated-environment gate it imports only qmf-core — any undeclared
or sibling import fails (default-deny, AR-06)"*.

Written to the requirement, the test would enumerate every non-stdlib module the package reaches
(static **and** `importlib.import_module`) and require each in `pyproject.toml`. That test fails
today:

- `packages/qmf-indicators/src/qmf/indicators/batch.py:374` — `importlib.import_module("numpy")`, on the main compute path, unguarded (a `ModuleNotFoundError` here would *raise*, not return a CT-04 refusal).
- `packages/qmf-indicators/pyproject.toml` — `dependencies = ["qmf-core", "ta-lib==0.7.1"]`. **`numpy` is not declared**; it arrives only transitively (`uv.lock`: `ta-lib` → `{ name = "numpy" }`).

Compounding it, `test_s1_static_imports_reach_only_qmf_core_and_own_package` filters
`root.split(".")[0] == "qmf"`, so the scanner is **structurally incapable** of seeing a non-`qmf`
undeclared import, and an AST-root scan sees neither dynamic import (`talib`, `numpy`) at all.
`test_s1_no_static_vendor_import_crosses_module_top_level` then reads that same blind spot as a
*virtue* ("talib is resolved lazily"). Net: R5's default-deny half is unproven and the one candidate
violation of it is invisible to the suite.

Recommended: file a finding (undeclared direct dependency, severity medium — it is transitively
satisfied today, so it is a governance/gate defect rather than a runtime break) plus an UNPROVEN row
for the isolated-environment clause.

### 1.3 `test_a18_two_rungs_and_separate_noop_path_are_distinct` — R24 — **hollow green**

```python
assert {r.value for r in BenchmarkRung} == {"burst-throughput", "per-tick-latency"}
assert NoOpTickMeasurement is not RungMeasurement
```

Banned shape 2(a): a module's self-declared enum members asserted as proof of behaviour. The second
line compares two distinct class objects with `is not` — it cannot fail under any source change short
of aliasing the names. The AC says the harness *"records two rungs … per accepted input observation
at the configured BarSpec, with the no-op tick path **measured** separately"*.

A real harness exists and is never invoked anywhere in the suite: `_bench.measure_burst`,
`measure_latency`, `measure_noop_tick`, `measure_configuration`. Grep of `qa/tests/epic_07/` returns
zero hits for all four. The measurement half of R24 — and the AC clause "the benchmark harness with
the same standing as unit tests" — is unproven while recorded PASS. (`_bench` is a private module and
is not re-exported from `__init__.py`; if that is the reason it was skipped, that is precisely the
narrowing rule 5 requires be written down as UNPROVEN, not passed off as green.)

### 1.4 R25's "misses a declared bound" arm — P0 — **untested, unrecorded**

The AC: *"A configuration claiming light without a recorded live-path rung baseline, **or whose
benchmark misses a declared bound**, is refused at the Tier-2 gate."* `test_acceptance_story75.py`
covers heavy-by-default, light-without-baseline, the synchronous guard, and a fully-proven accept.
The second disjunct is never exercised, although the code path exists and returns a refusal
(`budget.py:148-161`): `evaluate_light_claim(cfg, baseline=b, measurement=<regressing>)`, or a
`DeclaredBudget(..., bounded_state=False, ...)`. Two lines of test. Silently narrowed P0 clause.

### 1.5 R7's "at import" clause tested through a private helper — P0

`test_c3_reference_config_mismatch_is_unavailable_dependency`, `test_a5_pin_drift_returns_unavailable_dependency`,
`test_a5_process_global_config_drift_returns_unavailable_dependency`, `test_a5_matching_reference_is_accepted`
all construct `_reference.ResolvedReference(...)` by hand and call
`qmf.indicators._reference.assert_reference` — a private module, against rule 3 ("drive public
surfaces only, never private `_helpers`"). Two further problems:

- `test_a5_matching_reference_is_accepted` passes `MappingProxyType(_reference.REFERENCE_CONFIGURATION)` — the module's own expected value handed back in as the argument (banned shape 2(c), passing the conclusion in).
- The clause under test is *"returns an `unavailable dependency` refusal **at import**"*. Nothing in the suite observes the import. It is constructible through the public surface: a subprocess that calls `talib.set_compatibility(1)` **before** `import qmf.indicators`, then reads `reference_status()` — `resolve_reference()` reads compatibility at import (`_reference.py:166-183`) and `reference_status()` is public. That would falsifiably prove the import gate; the current tests prove only that a pure comparison function compares.

### 1.6 `test_a22_wrapper_set_is_conformant_wrapping_not_reimplementing` — R29

`assert wrapper_set_conformance_defects() == ()` — the package's own checker over the package's own
registry, with no injected counter-case *in this test*. (A6 does inject, which proves the checker can
bite, so this is not fully vacuous — but a wrapper that re-implements while declaring the correct
delegate passes both.) It is the registry that is asserted, not the arithmetic; see §1.1.

### 1.7 `test_a19_*` uses the package's own register as the checklist — R23

`for concept in CONCEPT_WALK_REGISTER:` — an omitted concept is invisible (only an *addition* trips
the `raise AssertionError(f"unhandled concept")`). The ten concepts are enumerated verbatim in
epics.md Story 7.5 and CT-16 `conformance_register`; the same technique already used well in
`test_contract_l2.py::_CONTRACT_IDENTITY_ELEMENTS` — an independent oracle tuple stated from the
contract — should have been used here. Inconsistent rigor rather than an outright hollow green.

### 1.8 `test_a23_wrapper_ships_tests_and_reference_usage_examples` — R31

Asserts two hardcoded filenames exist. The AC says *"**each** ships executable tests and
reference-usage examples"*. No per-wrapper check (`WRAPPER_FORMULAS` has six), no check that the
shipped tests are executable. File existence is what the implementation happens to have.

### 1.9 Fingerprint-prune arms are tautologies — R1, R3 (informational)

`test_a2_each_required_identity_element_is_load_bearing_in_the_fingerprint` and
`test_u2_alignment_policy_is_present_and_load_bearing_in_identity` prune a key from the dict
`fp1_identity()` just returned and re-hash it. *That removing a key from a dict changes its hash* is
a property of `qmf.core.fingerprint`, not of the configuration; that arm cannot fail. The load-bearing
assertion is the `element in content` membership plus `test_a1`'s `fp1 == fingerprint(fp1_identity())`
— that chain does hold, so R1/R3 are genuinely proven. RESULTS overstates the prune arm
("proving none is stored-but-unhashed"); the wording should be corrected, no re-test needed.

### 1.10 Equality/restore laws are near-tautological against this design — R19, R21, R30 (informational)

Because `_recompute()` delegates to `compute_batch`, streaming *is* batch, and snapshot/restore
carries an accumulated buffer. The tests do assert what the requirements demand (the AC itself says
"by construction"), so these are **not** wrong expectations — but their evidential force is close to
zero, and the RESULTS falsifiability note ("an injected one-value perturbation … flips the law to
False") proves the *comparator* discriminates, not the *law*. Worth stating plainly in RESULTS.

---

## 2. Requirements with no test coverage

From Epic 7's epics.md section (clause-level; the R-register is the PLAN's numbering):

| # | Clause (epics.md story) | R | Status now | Provable? |
|---|---|---|---|---|
| M1 | "cross-OS or cross-build agreement is never this gate — it is a **separate registered comparison artifact**" (7.4) | R20 | RESULTS §7 boundary only; **no findings.csv row** | Partly — `comparison.py` / `compare_reference_outputs` is that artifact and is assertable as a separate surface; the equality law's same-process scoping is assertable. Rule 5/6 requires at minimum an UNPROVEN row. |
| M2 | the snapshot "is a serialized contract with **its own format version**" (7.4) | R21 | untested | Yes — assert a snapshot format version distinct from `contract_format_version`. |
| M3 | "exactly one feeder … and **unlimited readers**" (7.4) | R18 | feeder half only | Yes — multiple readers over one instance. |
| M4 | equality law "with the **seeding rule** and leading-undefined-prefix-to-not-ready mapping **declared**" (7.4) | R19 | not asserted as declared | Yes — the declaration is a surface. |
| M5 | "it **builds** from … in **src/ layout**" and the "**Tier-2 isolated-environment gate**" (7.1) | R5 | pyproject substring only | Yes — see §1.2. |
| M6 | "the benchmark harness **with the same standing as unit tests**" (7.5) | R24 | harness never run | Yes — `_bench.measure_configuration`. |
| M7 | "fanned-out heavy value past its declared maximum age → **stale evidence**" (CT-16 inv.12; **not** an Epic 7 AC) | R28 | UNPROVEN, recorded | No — correctly judged. |
| M8 | numeric AD-13 rung values / numeric light-vs-heavy ceiling | R24/R25 | UNPROVEN, recorded | No — ratified deferral, confirmed at `ct-16-indicator.yaml:13`. |

M7 and M8 are correct exclusions. **M1–M6 are gaps**, and M1 additionally breaches rule 6 (an excluded
requirement with no `findings.csv` row).

---

## 3. `findings.csv` row-by-row

| Row | Req | Classification | Notes |
|---|---|---|---|
| **E7-F01** | R28 | **UNPROVEN-correctly-recorded** | Independently verified: `stale` / max-age appear nowhere under `packages/qmf-indicators/src/`; `STALE_EVIDENCE` lives in `qmf-core` (`refusal.py:60`); CT-16 invariant 12 (`ct-16-indicator.yaml:27`) does state the clause and Story 7.5's epics.md ACs do not. Correct call, correct severity, honest wording. |
| **E7-F02** | R24, R25 | **UNPROVEN-correctly-recorded, but understated** | The numeric-ceiling half is a genuine ratified deferral (`ct-16-indicator.yaml:13` — "numeric AD-13 rungs await first measured baselines"). However the row claims "the regression gate incl. the peak-memory axis are tested (T7-A17/A18)" and thereby covers over **two provable halves that were left unproven**: the harness never being exercised (§1.3) and R25's "misses a declared bound" arm (§1.4). Those need their own rows; as written the row makes a testable gap look deferred. |
| **E7-F03** | FR-019 | **UNPROVEN-correctly-recorded** | Independently verified: `_bmad-output/` contains only `planning-artifacts/`; `_bmad-output/test-artifacts/` does not exist. Audit-integrity note is accurate and correctly does not affect any test outcome. |

**Genuine violations recorded: 0. Wrong-expectation rows: 0. UNPROVEN-correctly-recorded: 3 (one
understated).**

`findings.csv` is legitimate under rule 6 only if RESULTS shows every owned requirement green under
rules 1–5. It does not: §1.1–§1.5 and M1–M6 above are green-or-silent where they should be UNPROVEN
or failing.

---

## 4. Required repairs, in priority order

1. **Add a reference-oracle test** (R9/R29/R30): compare `compute_batch` output against the live
   `talib` function for each of the six wrapper formulas, with an injected-bias falsification arm.
   Until it exists, R9's "provably the arithmetic used" is UNPROVEN, not green.
2. **File the `numpy` finding** and rewrite `test_a3_pyproject_declares_every_dependency` to
   enumerate reached third-party roots (static + `importlib`) against declared dependencies;
   widen the S1 scanner past its `qmf`-only filter.
3. **Drive `_bench.measure_configuration`** for R24, or record the harness half UNPROVEN with the
   private-module reason.
4. **Add R25's "misses a declared bound" refusal arm** (two lines).
5. **Re-test R7 through the public import seam** (subprocess with drifted compatibility → `reference_status()`), and stop passing `_reference.REFERENCE_CONFIGURATION` in as the expected answer.
6. **Add an UNPROVEN row for R20**, plus tests or UNPROVEN rows for M2–M6.
7. Correct the RESULTS wording on the fingerprint-prune arms (§1.9) and on the equality law's
   evidential force (§1.10).
