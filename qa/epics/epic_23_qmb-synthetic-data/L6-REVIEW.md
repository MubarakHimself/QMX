# Epic 23 — QMB synthetic data — L6 requirements-fidelity review

Independent review of the Epic 23 verification pass (`PLAN.md`, `RESULTS.md`,
`findings.csv`, `qa/tests/epic_23/`). One question per test: **does it assert what the
requirement demands, or what the implementation happens to do?** Judged against the
HARDENED AUTHOR CONTRACT (falsifiability, banned shapes, independent observation, fault
realism, scope honesty, findings-ledger completeness) and against Epic 23's own section of
`_bmad-output/planning-artifacts/epics.md` (lines 4471–4693). No test was run or edited;
source was read as evidence only.

**Reviewer scope note:** the epic-binding rule was applied to every row. Requirement ids
owned by Epics 3/4/6/14/15/16/19 are noted, not tested here.

---

## Verdict

**GAPS.**

The three findings are all real, and the four highest-risk requirement families
(world derivation, replay-clock guard, namespace firewall, determinism/anchor) are
genuinely proven. But the pass reports **0 UNPROVEN** requirements, and that number is
wrong. At least two Epic-23-owned acceptance clauses — AC 23.3.4's promotion half and the
whole of AC 23.3.5 — are green only because the test calls a function whose body is an
unconditional `return policy(...)` or a constructor that stamps the asserted literals.
Those are the banned "calling a function against itself / asserting self-declared
constants" shapes, and under rule 6 they belong in `findings.csv` as `observed=UNPROVEN`,
not in the ledger as PASS. Three further clauses were silently narrowed (rule 5) without
an UNPROVEN row.

Nothing needs to be un-filed: **3 genuine violations, 0 wrong-expectation tests.** What is
missing is the honest other half of the ledger.

| | Count |
|---|---|
| `findings.csv` rows that are genuine violations | **3** (E23-F01, E23-F02, E23-F03) |
| Rows that are wrong expectations | **0** |
| Rows correctly recorded as UNPROVEN | **0** |
| Rows that *should* exist as UNPROVEN and do not | **2 firm** (AC 23.3.4 promotion half, AC 23.3.5) **+ 3 narrowed clauses** |
| Green tests resting wholly on a banned shape | **1** (T23-316) |
| Green tests with a genuine core plus tautological padding | **6** (T23-308, 309, 315, 317, 319, 322) |

---

## 1. Per-`findings.csv` row verdict

### E23-F01 — API-door parity gap — **GENUINE VIOLATION** (with an epic-binding caveat)

Confirmed independently against source. `qmb/src/qmb/doors/api/__init__.py` carries no
`generate` export; `qmb/src/qmb/doors/cli/tree.py` adapts the library function and
`DATA_COMMANDS` lists `generate`. The parity catalog masks it:

```
qmb/src/qmb/doors/parity.py:40    "data.generate": ("DATA_COMMANDS", "data_front_identity"),
```

Every sibling row (`data.verify`, `data.gap-check`, `data.list`, `data.catalog`) names its
library function as the third element; `data.generate` omits it, so the parity contract has
nothing to compare and cannot fail. That is a real defect and the description states it
accurately.

**Epic-binding caveat.** Epic 23's own ACs name only the CLI door ("the click==8.4.2 CLI
door (B-11, B-1)", AC 23.1.1). The *reachable-from-every-door* obligation and **FR-046** are
Epic 16's, and Epic 16 filed the same defect as F16-F02. The row is correctly
cross-referenced, so this is not a mis-file — but the finding's home is Epic 16 with an
Epic-23 cross-reference, not the reverse. Recommend downgrading this row to a
cross-reference line once Epic 16's F16-F02 is accepted, to avoid double-counting one
defect as two P0s.

**Test-shape note.** The CLI half of the pin is implementation-shaped:
`getattr(tree, "run_generate", None) is lib_generate` hard-codes an attribute name. If the
CLI door renamed its adapter the pin would fail for a reason unrelated to parity. The API
half (`any(getattr(api, name) is lib_generate for name in dir(api))`) is a genuine derived
enumeration. Also: the pin checks two doors; `qmb/src/qmb/doors/mcp/` exists and is not
enumerated, so "reachable from every door" is narrower than tested.

### E23-F02 — source-scale trust — **GENUINE VIOLATION**

Confirmed by tracing the scale. `_coerce_source_bars` (generate.py:1445-1446) *does* read
the source row's declared scale — `row.get("scale", scale)` — into `SyntheticBar.scale`, so
the declared source scale is present on the bar and available. It is then never consulted:
every draw adapter divides by `float(10**config.scale)` (generate.py:1108, 1166, 1206) and
the only float→integer money boundary, `_FloatToScaledInt` (generate.py:1260-1281), is
constructed with `scale=config.scale`. A source declared at scale 3 is therefore
reinterpreted at scale 5 with no conversion and no refusal — exactly what DEC-0105 forbids
("conversions to Money or Price are derived with lineage, never a silent rescale"), and it
breaks AC 23.1.3's "quantized to the instrument's tick size" for the target instrument.
The finding is in-epic (23.1-AC3), correctly categorised, and the expected-behaviour clause
correctly offers both the conversion arm and the refusal arm.

**Test-shape note.** The failing assertion is a magnitude proxy —
`min(closes) > max_source_magnitude * 10` — not the exact 10^(target−source) factor and not
a lineage check. It is directionally right and it fails, so it produces no hollow green; but
after repair this pin would also pass on a wrong-by-2x conversion. Tighten to the exact
factor before it is used as a regression lock.

### E23-F03 — nested-config replay-clock bypass — **GENUINE VIOLATION** (highest severity, confirmed reachable)

Confirmed, and stronger than the row claims. `resolve_generator_config`
(generate.py:592-602) merges a nested `generator_config` body by carrying forward **only**
`destination`, `output_root`, `calendar`, `source_series` — then runs
`_refuse_replay_clock_on_synthetic(body)` against the *merged* body, from which the outer
`clock` and `world` have already been dropped. The guard itself (generate.py:1851-1876)
correctly refuses both a flat `clock=replay` and a flat non-simulated `world`, so the
nested-vs-flat asymmetry the pin asserts is exactly the defect.

The row understates one thing: this is not a hypothetical composition. The real CLI door
routes nested bodies —

```
qmb/src/qmb/doors/cli/tree.py:511    if has_generator_config(resources):
```

— and `_is_generation_request` (generate.py:567-569) treats a nested `generator_config`
mapping as a generation request. The bypass is reachable from the shipped operator door,
not only from an in-process caller. The "highest severity" characterisation is justified.

---

## 2. Tests that assert the implementation rather than the requirement

None of these produce a false finding — all are green — but each is a place where the
ledger claims proof it does not have.

### 2.1 Hollow green — must be re-recorded as UNPROVEN

**T23-316 (AC 23.3.5, procedure-ephemeral) — the whole test.**
`procedure_ephemeral_taint` (store_taint.py:747-777) is a pure constructor: given a name
and a seed it returns a frozen record with `world=World.REPLAY.value`,
`claim_class=CLAIM_ROBUSTNESS`, `creates_store_partition=False` written in as literals. The
test asserts precisely those literals back. No counter-case exists short of editing the
constructor. The requirement — "when `block-bootstrap` (or a B-14 trade-shuffle) perturbs a
`world=replay` run **without persisting a synthetic series**, world stays `replay`" — is
about a *run*, and no run is perturbed anywhere in the suite; no world is derived; no
store-partition absence is observed through a sink. The remaining assertion,
`refuse_ephemeral_as_admission_evidence(...)` (store_taint.py:780-797), is an unconditional
`return policy(...)`: it refuses whatever it is handed, including `None`.
**Verdict: AC 23.3.5 is UNPROVEN.** It is recorded as PASS.

### 2.2 Half-hollow — one clause of the AC is unproven

**T23-315 (AC 23.3.4, non-promotable).** The load half is real: `refuse_synthetic_load`
(store_taint.py:660-682) genuinely branches on the target world and returns `Ok` for
`SIMULATED`, so the REPLAY/LIVE refusals discriminate. The **promotion** half is not:
`refuse_promote_synthetic` (store_taint.py:685-706) takes an optional artifact id and
unconditionally returns a policy refusal. There is no promotion surface in the package for
it to guard. Asserting it refuses is asserting that `policy(...)` builds a refusal.
**Verdict: the "or to promote a synthetic artifact toward live money" clause of AC 23.3.4 is
UNPROVEN.**

### 2.3 Genuine core, tautological padding (no ledger change needed, but the padding is not evidence)

Each of these has a real, falsifiable primary assertion; the listed line adds nothing and
should not be counted as coverage.

| Test | Tautological line | Why it proves nothing |
|---|---|---|
| T23-308 | `refuse_edge_claim("edge", process="gbm")` | claim_class.py:551-574 — unconditional `return policy(...)`. The real proof is the 4×3 loop through `resolve_claim_label`, which is genuine. |
| T23-308 | `label.claims_edge is False` | reads the module constant `CLAIMS_EDGE`. |
| T23-309 | `refuse_post_hoc_threshold("alpha_level")` | claim_class.py:710-726 — unconditional. The real proof is `preregister_threshold({}, …)` → refusal and `robustness_report_interface(threshold=0.05)` → refusal, both genuine branches. |
| T23-309 | `report.emits_verdict is False` | reads `REPORT_EMITS_VERDICT`. |
| T23-317 | `refuse_synthetic_write_into_governed_namespace("live")` | store_taint.py:483-502 — unconditional. `route_synthetic_persist(prov, requested_namespace=…)` is the genuine branch and is asserted. |
| T23-319 | `store_provenance["rng_is_runtime_stdlib_random"] is False` | a self-declared flag. The genuine proof — reseeding the global `random` between two runs leaves the artifact fingerprint identical — is present and is the right test. |
| T23-322 | `refuse_robustness_band_for_from_scratch("gbm")` | scenarios.py:685-703 — unconditional; it ignores lineage entirely and would refuse for `block-bootstrap` too. A falsifiability pass would have caught that by probing the history-seeded arm. |
| T23-322 | `has_original_anchor is False`, `robustness_band_computable is False`, `permittable_claim_classes` set | flags/tables the fan-out sets on its own report. `original_anchor() is None` plus the history-seeded discriminator are the genuine half. |
| T23-307 | `permittable_claim_classes("gbm")` / `("block-bootstrap")` | asserting the module's own lookup table (claim_class.py:444-473). The `resolve_claim_label` refusal is the genuine half. |

### 2.4 Over-specified — asserts a choice the requirement leaves open

- **T23-302:** asserts that a `gbm` config *citing* a source dataset is refused. AC 23.1.2
  says only that "no source dataset is required and the config records
  `source-dataset id = none`". Refusing a superfluous citation is a defensible
  implementation choice, not a requirement. The assertion mirrors the code.
- **T23-320:** asserts the substream rule is exactly `base_seed + k`. AC 23.4.3 says
  "**e.g.** master seed + scenario index" — the rule is illustrative; the requirement is
  "derived deterministically … so scenario k reproduces in isolation". That half *is*
  genuinely proven (`regenerate_scenario(res, k)` reproduces the in-fan-out fingerprint) and
  is the assertion that should carry the AC.
- **T23-323:** the fan-out is tuned (`count=60, scenario_count=24, seed=1,
  volatility="0.60"`) until the implementation happens to fail some scenarios. The
  invariant asserted (`produced + filtered == scenario_count`) is the right one, but the
  fixture is fitted to observed behaviour and will silently stop discriminating if the
  adapter's overflow threshold moves.
- **T23-303-rounding:** asserts FLOOR and CEILING *differ*. It never asserts the direction
  (floor ≤ ceiling per bar), so a mode-swap defect would pass.

### 2.5 Tests that are exemplary — keep these as the model

- **T23-303-grid** — the only test in the suite with a test-owned injected fake
  (`GappedCalendar`) driving a real code path and observing an effect the fake defines.
  Falsifiable, independent, correct level.
- **T23-321** — asserts scenario 0's OHLC equals the cited source verbatim, bar by bar, and
  that scenario 1 differs. Observes real output against real input.
- **T23-313** — genuine derivation plus a genuine override-refusal branch; the caller
  cannot declare world, proven both ways.
- **T23-318 / T23-320 (isolation half)** — determinism observed across independent runs.

---

## 3. Requirements in Epic 23's `epics.md` section that no test covers

Ordered by how much of the epic's safety promise they carry.

1. **AC 23.3.1 — "at the store level (not merely in a filename)".** The defining clause of
   the epic (it closes the LEAN spec §2A.8 gap) is never observed against anything
   persisted. `_store_taint` writes the provenance sidecar only when an output root is
   resolvable (generate.py:1574-1580), and **no test in `qa/tests/epic_23/` passes
   `output_root` to a call whose provenance it then inspects** — the single `tmp_path` use
   (T23-301) checks the *config* artifact only. `_write_provenance` is never executed.
   T23-312 proves the clause with `isinstance(record, dict)`, which is not a store.
   Additionally the six-field check is presence-only (`field in record`,
   `record[field] is not None`); no field's *value* is checked against the config that
   produced it, so a record carrying six wrong values passes. AC 23.3.1's "tick series or
   derived aggregate" cases are not covered at all.
2. **AC 23.1.1 — invocation through the door.** "When I invoke `qmb data generate`" is
   never invoked. All 30 tests import `qmb.data` directly; no test crosses the click CLI
   door the AC names (B-11/B-1 thin front). The one door-aware test, T23-PIN-01, inspects
   module attributes rather than executing a command.
3. **AC 23.1.4 — "OHLC integrity survives every transform."** T23-304 exercises the
   `SyntheticBar.try_create` constructor only. No test drives an adapter or perturbation
   into producing a bound-violating bar, so "survives every transform" — that every
   completed bar in every process routes through the gate — is unobserved. PLAN §6 named an
   "OHLC-bound-violating transform input" fixture for exactly this; it was not built, and
   the narrowing is not recorded.
4. **AC 23.3.4 (promotion half)** — see §2.2. UNPROVEN, recorded as PASS.
5. **AC 23.3.5 (whole)** — see §2.1. UNPROVEN, recorded as PASS.
6. **AC 23.2.1 — the CT-32 result label.** The AC binds the claim class to "the CT-32
   result label emitted by the run loop (AR-59; Epic 14)". Every test asserts against
   `ClaimClassLabel`, a `qmb.data`-local value object. Whether the claim class actually
   reaches a CT-32 label is untested. §7.3 defers the CT-32 engine to Epic 14 — legitimate —
   but the *seam* (claim class enters the label) is Epic 23's and is unproven.
7. **AC 23.4.6 (first half) — governor mechanics.** "the governor spawns them
   process-per-run bounded by min(cpu, memory) budgets with enqueue-when-full (never silent
   oversubscription)" sits inside an Epic-23 AC and Epic 23's own traceability cites B-5 and
   AR-50. Deferring it to Epic 15 is a defensible seam call and RESULTS records it, so this
   is honest — but it is an uncovered Epic-23 AC clause, not a non-requirement.
8. **AC 23.1.2 — "resolved from a qmf-data room (CT-10)."** Only the presence of a citation
   string is checked. Room resolution is Epics 3/6 (recorded §7.4) — noted, not a defect of
   this pass.
9. **AC 23.2.4 — "the module ships no numeric pass battery."** Proven only by the returned
   interface's `None` fields. No module-level scan establishes the absence claim.
10. **AC 23.1.3 — the NFR-02 scanner's reach.** `tools/money_path_scan.py` is annotation-
    driven over money-path types; `generate.py` computes in binary `float` throughout
    (lines 1108-1227) and the scanner reports clean. The scanner result is true and the
    tool is correctly borrowed, but RESULTS' line "flags 0 findings … over all 15
    `qmb/data` files" reads as proof of "no float on the money path" and is not. The real
    AC content — float re-enters *only* through a named AD-7/AD-22 conversion — rests on
    T23-303-rounding alone.

**Correctly recorded as out-of-scope (no action):** market-hours calendar authority
(Epic 4), GAP-0048-gated content, SC-07 threshold values, the deferred-by-tier L0/L1/L2/L4/L5
suite, the door-parity mechanism (Epic 16), and the missing `test-design-qa.md` /
`QMX-handoff.md` authorities. The plan-integrity caveat in PLAN §7.8 is accurate — this
reviewer independently confirms `_bmad-output/test-artifacts/` is absent from the worktree.

---

## 4. The single most important gap

**No test in the epic observes the synthetic taint surviving persistence.**

Everything Epic 23 promises reduces to one sentence: fabricated data can never masquerade
as real evidence on the money path. The mechanism that delivers it is the store-level
`origin = synthetic` record — the thing that, unlike a filename, a second process reading
the room cannot fail to see. That record's write path (`_store_taint` →
`route_synthetic_persist` → `_write_provenance`, generate.py:1531-1589) is **never executed
by any test in this suite**. Both P0 tests that claim it — T23-312 (`origin=synthetic` at
the store level) and T23-313 (world derived from that provenance) — operate on an in-memory
`SyntheticStoreProvenance` value handed straight back by the same call that made it. The
derivation is proven; the *persistence* is not. A defect that wrote the sidecar to the wrong
partition, dropped it silently on an unwritable root, or serialised it with a missing
`origin` key would pass all 27 green tests.

The fix is small and squarely inside the T3 band: give T23-312 an `output_root`, then read
the sidecar back off disk as an independent observer, assert each of the six fields equals
the value the resolved config actually holds (not merely that it is non-`None`), assert its
path sits under `SYNTHETIC_STORE_PARTITION`, and feed that on-disk mapping — not the live
object — into `derive_world_from_store_provenance` for T23-313. That single change converts
the epic's central promise from a self-report into an observation, and it is the difference
between this pass reading "0 UNPROVEN" honestly and reading it by omission.

---

## 5. Required ledger corrections

1. Add `findings.csv` rows with `observed=UNPROVEN`:
   - AC 23.3.5 (procedure-ephemeral, T23-316) — asserted only against constructor literals
     and an unconditional refusal factory; no run is perturbed, no world derived.
   - AC 23.3.4 promotion clause (T23-315) — no promotion surface exists;
     `refuse_promote_synthetic` is an unconditional `return policy(...)`.
2. Add UNPROVEN or explicitly-narrowed rows for the three silent narrowings: AC 23.3.1
   "store level, not a filename" (never persisted), AC 23.1.4 "survives every transform"
   (constructor only), AC 23.1.1 door invocation (library-only).
3. Correct RESULTS.md's summary line **"UNPROVEN Epic-23-owned requirements: 0"** — it is
   the claim rule 6 exists to prevent, and it is not supportable as written.
4. Keep all three findings. Consider re-homing E23-F01 to Epic 16 as the owner with an
   Epic-23 cross-reference, so one defect is not counted as two P0s.
5. RESULTS.md §"L6 independent review (folded in — no additional findings)" should be
   superseded by this document. That self-review was performed by the same author against
   the same source and reached "no additional findings"; its point 9 (the `raise`
   enumeration) is independently confirmed correct — `rng.py:107` is the only `raise` in
   `qmb/data/*.py` and is a sanctioned internal programmer-error guard — but its points 1-4
   assert the same self-reported structures the tests do, and did not surface the
   persistence gap in §4 above.
