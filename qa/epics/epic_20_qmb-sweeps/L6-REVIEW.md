# Epic 20 (qmb-sweeps) — L6 requirements-fidelity review

Reviewer: independent L6 pass. Inputs read: `PLAN.md`, `RESULTS.md`, `findings.csv`,
all five files under `qa/tests/epic_20/`, this epic's section of
`_bmad-output/planning-artifacts/epics.md` (lines 3964–4090), and — as read-only
evidence only — `qmb/src/qmb/sweep/rank.py`, `.../batch.py`,
`qmb/src/qmb/registryread/port.py`, `qmb/src/qmb/execution/ports.py`.

No test was run and no test or source file was edited. Only this file was written.

> **Note on the file this replaces.** The path `L6-REVIEW.md` previously held a
> review authored by the same agent that wrote the tests (it is referenced from
> `RESULTS.md` §"L6 independent review"). A self-authored L6 is not an independent
> level; its conclusions are folded in below where they survive scrutiny and
> corrected where they do not.

---

## Verdict: **gaps**

The suite is substantially better than a hollow-green suite. Its spine is real:
`T20-301`, `T20-305`, `T20-306/306b`, `T20-310`, `T20-314`, `T20-315/315b`,
`T20-317`, `T20-318`, `T20-320`, `T20-321`, `T20-322`, `T20-302c` and `T20-PIN-01`
all name a requirement, construct a counter-case that would fail, and observe the
effect through a test-owned artifact (the on-disk ledger, a returned `TypedRefusal`,
test-built `LedgerLine`s). `conftest.py` builds inputs from the ratified value types
rather than from the code under test, and the Story-20.3 fixtures drive the real
process-per-run batch instead of a mock. The F-20-01 disposition is credible: the
swept parameter is genuinely identity-bearing, and `T20-PIN-01`'s 1×1×2 probe is the
right sharpest instrument for it.

The verdict is nonetheless **gaps**, on three counts:

1. **One test asserts the implementation's self-description as proof of the
   requirement** — `T20-319`, which carries the epic's most important firewall
   (B-10 / FR-034, "ranking publishes and never acts"). Four of its assertions read
   back hard-coded module constants. This is banned shape #2 verbatim.
2. **Eight requirement clauses are silently narrowed** — excluded from the suite
   with no UNPROVEN row in `RESULTS.md` or `findings.csv`. Author-rule 5 makes
   silent narrowing a violation regardless of whether the underlying code is
   correct. The most consequential is R16's *"every fill carries the `optimistic`
   taint"*: no test in the epic ever produces or inspects a fill.
3. **`T20-323` pins the very default it declares unratified.** It asserts
   `len(bar) == 4` on the confirmation-only Book-bar fold — an assertion that fails
   the moment the operator rules a sweep combo is `trial`. The test cannot both
   record the role as UNPROVEN and assert a count that depends on it.

None of the three is a hollow green in the tier-1 sense (nothing here passes because
it asserts nothing). They are fidelity defects: assertions aimed at the code's shape
rather than the requirement's demand, and clauses quietly dropped.

---

## Wrong-expectation tests

Ranked by how much of a P0 requirement they leave unguarded.

### 1. `T20-319` — `test_t20_319_ranking_publishes_and_never_acts` (R19, P0) — **wrong expectation**

`test_l3_story_20_4_rank.py`. Four assertions read back constants the module
declares about itself. Verified in source:

```
rank.py:132  RANK_PUBLISHES_NEVER_ACTS: Final[bool] = True
rank.py:133  RANK_MAKES_EDGE_CLAIM: Final[bool] = False
rank.py:134  RANK_MAKES_PASS_FAIL_VERDICT: Final[bool] = False
rank.py:222  makes_edge_claim: bool = RANK_MAKES_EDGE_CLAIM      # RankedCombo default
rank.py:223  taint: str = TAINT_OPTIMISTIC                        # RankedCombo default
rank.py:304  publishes_never_acts: bool = RANK_PUBLISHES_NEVER_ACTS
```

so `assert ranking.publishes_never_acts is True`,
`assert ranking.makes_edge_claim is False`,
`assert ranking.makes_pass_fail_verdict is False` and
`assert combo.taint == "optimistic"` are each `assert <literal> == <same literal>`.
There is no constructible counter-case: an implementation that promoted a Book on
every rank would still set the flag to `True` and pass. The requirement demands a
*behaviour* (nothing bound, no promotion minted, no money gated), and the behaviour
is not observed.

The same test's `for act in RANK_FORBIDDEN_ACTS: refuse_rank_act(act)` loop is
banned shape "calling a function against its own lookup table": it proves every
member of the module's list is in the module's list. A requirement-derived version
enumerates the acts from the spine (`size`, `promote`, `bench`, `bind`, `allocate`,
`demote`, `change_mode`) as a **test-owned** literal — then a source-side deletion
from `RANK_FORBIDDEN_ACTS` fails the test instead of silently shrinking it.

What survives in this test and is genuine: the `composite_score` objective refusal,
and `{"verdict","pass","fail","score","rating","tier"}.isdisjoint(identity)`.

### 2. `T20-316` (d)+(e) — `test_t20_316_world_derives_from_provenance_and_no_edge_is_claimed` (R16, P0) — **wrong expectation (partial)**

Parts (a)–(c) and (f) are sound: `PROVENANCE_RECORDED` → `world is World.REPLAY`, a
caller-declared `world` refused, `PROVENANCE_SYNTHETIC_TAINTED` under a replay clock
refused — all observed on a real compiled config.

Parts (d) and (e) pass the conclusion in as an argument:

```python
sim_refusal = refuse_store_synthetic_governed_evidence(World.SIMULATED)
edge = refuse_optimistic_edge_claim(claims_edge=True)
```

Handing `World.SIMULATED` / `claims_edge=True` to a function whose job is to refuse
those exact inputs proves the helper works. It does not prove that any sweep combo
reading store-tainted data *routes through* that helper, which is what the AC
demands ("a store-tainted read **is** world=simulated **and refuses**").

Worse, `refuse_optimistic_edge_claim` takes a `taint` parameter
(`execution/ports.py:247`) that refuses any non-`optimistic` token — a ready-made,
falsifiable counter-case (`taint="pessimistic"` → expect refusal) that the test does
not use. And **the AC clause "every fill carries the `optimistic` taint" is not
asserted anywhere in the epic**: `good_slices` produces no fills, the only
`mint_run_performance_result` call in the suite (`T20-311`) passes
`filled_count=0`, and the sole `taint` assertion in the epic is the `RankedCombo`
dataclass default in `T20-319`. This clause is untested and unrecorded.

### 3. `T20-307` — `test_t20_307_admission_resolves_one_frozen_as_of_through_one_port` (R7, P0) — **wrong expectation (partial)**

`assert admitted.port.frozen is True` is a self-declared flag standing in for the
freeze behaviour. And the AC's "**no door-side or second cache**" is asserted only
as `admitted.registry_as_of == live_as_of.registry_as_of` — an implementation that
kept a second cache and happened to seed it from the live port passes unchanged. The
positive half (exactly one as-of; the stamp is an instant + set-fingerprint pair) is
genuine.

### 4. `T20-308b` — `test_t20_308_a_fresher_as_of_mid_batch_changes_no_combination` (R8, P0) — **wrong expectation**

This test never exercises `admitted.port`. It grows the hub, then **constructs its
own** port and asserts against that:

```python
frozen = ok(RegistryReadPort.try_create(grown, ..., bound=admitted.port.bound, frozen=True))
still  = ok(frozen.resolve(book_id))
```

So it proves "a `RegistryReadPort` I built with `frozen=True` ignores a newer set",
not "the admitted sweep's port does". The link between the two is the self-declared
flag from `T20-307`. Worth stating plainly: because `PassiveHub.with_set` returns a
**new** hub, the admitted sweep's port physically cannot see a fresher set through
any public surface — meaning "a fresher registry state arriving mid-batch" has **no
constructible counter-case** at this level. Under author-rule 1 that makes it an
UNPROVEN row with the structural reason, not a green test.

### 5. `T20-323` — `test_t20_323_role_discriminant_and_confirmation_only_fold` (R23) — **internally inconsistent**

The docstring says it "does NOT assert WHICH role a plain sweep combo SHOULD take".
It then asserts:

```python
bar = ok(qmb.read_book_bar(happy_batch.ledger_root, world=World.REPLAY))
assert all(line.role == "confirmation" for line in bar)
assert len(bar) == 4
```

`len(bar) == 4` is only true because the source defaults sweep combos to
`role=confirmation`. If the operator rules `trial`, the Book-bar is empty and this
test fails. The test pins the unratified default while `findings.csv` declares that
default unproven. Drop the `len(bar) == 4` assertion (or assert
`len(bar) == len([o for o in report.outcomes if o.role == "confirmation"])`, which
holds under either ruling) and the test matches its own stated scope.

The same coupling touches `T20-314`, `T20-316(f)` and `T20-PIN-01`, which read the
merge view with a hard-coded `role="confirmation"`. Those are more defensible —
they must name some role to read a view — but they will all break together on the
operator's ruling, and `RESULTS.md` does not say so.

### Not wrong, for the record

- `T20-304`'s `assert api.preflight_run_count is preflight_run_count` looks like a
  marker assertion but is a legitimate structural proof of B-1's "the computation
  lives once, never duplicated in a door" — a door-local copy is a different
  function object. Keep it.
- `T20-303`'s billion-combo purity probe is a genuinely clever falsifiable design:
  an impure count that expanded or spawned could not return. (Its "writes no ledger
  line" half is argued, not observed — see narrowings.)
- `T20-311`'s `REGISTRY_AS_OF_KEY == CT32_REGISTRY_AS_OF_KEY == "registry_as_of"` is
  a constants assertion, but the test then does the real work: it rebuilds the
  `registry-as-of` fingerprint input **test-side** and asserts it is present in the
  minted CT-32 label's `input_fingerprints`. That observation stands on its own.
- `T20-322`'s bogus-port injection (`admit_sweep(decl, object(), writer())`) is
  proper fault injection at a public boundary.
- Rule 4 (fault realism / third-party exception types) is largely **N/A** for this
  epic: no Epic-20 AC covers third-party failure translation — the `OSError` /
  spawn-failure surfaces belong to Epic 15's orchestrator seam. No violation.

---

## Missed requirements (clauses in this epic's `epics.md` section with no test and no UNPROVEN row)

All eight are Epic-20 AC text, confirmed against lines 3964–4090. Each is a **silent
narrowing** under author-rule 5.

| # | Requirement clause (verbatim from epics.md) | Story / plan row | Status |
|---|---|---|---|
| M1 | "every fill carries the `optimistic` taint" | 20.3 AC4 / R16 (**P0**) | No test. No fill is produced or inspected anywhere in the epic; the only `taint` assertion is a dataclass default. **Highest-value miss.** |
| M2 | "parallelism is bounded by the governor's min(cpu budget, memory budget) with enqueue-when-full" | 20.3 AC1 / R13 | No test observes the concurrency bound or the queueing. `T20-313` varies `cpu_budget` 1→4 and compares identity — it never checks that ≤ min(cpu,mem) ran at once, so a governor that ignored the budget entirely would pass. Partially mitigated: `RESULTS.md` lists "the governor … (Epic 15)" under seam-owned, but the *sweep's use* of the bound is Epic-20 AC text and is not in `findings.csv`. |
| M3 | "compiles to exactly one resolved, **schema-validated** run-config artifact" | 20.3 AC1 / R12 (**P0**) | `T20-312` asserts one config per combo and `fp1 == run_id`; the schema-validation clause is never exercised (no malformed-config counter-case). |
| M4 | "executes as **one isolated OS process**" | 20.3 AC1 / R12 (**P0**) | Proven only by four distinct `output_dir` values. No test-owned observation of process separation (distinct PIDs, out-of-process execution). The source does use `orchestrator.spawn.start_run`/`LiveSpawn`, so the behaviour is likely real — but the test does not observe it. |
| M5 | "a stream-set violation **such as `DuplicatePositionStream` or `MixedSettlementAsset`**" and "an `aborted` **time**-limit breach" | 20.3 AC3 / R15 (**P0**) | `T20-315` injects one invalid stream id (`"NOT-A-STREAM"`); `T20-315b` covers the memory breach. Both named stream-set exemplars and the time-limit breach are untested. |
| M6 | "severity configurable, **no invented default**" | 20.2 AC3 / R10 (**P0**) | `T20-310` proves the *configured* severity is used; `conftest.make_port` always supplies one. The counter-case — a port built with no severity, which must refuse rather than invent — is never constructed. (Source `port.py:127,144` does take it as a required arg with a `clean_token` guard, so the code appears correct; the *test* does not prove it.) |
| M7 | "that one as-of … is stamped into **the sweep label** and into every combo's run label" | 20.2 AC1 / R8 (**P0**) | `T20-308` checks the **run** label only; no assertion that `admitted.label` carries the as-of stamp. |
| M8 | "the door is a thin wrapper (**click==8.4.2**)" · "the same object at unit scale, **created the same way a Book config is created**" | 20.1 AC3 / R4 · 20.1 AC1 / R1 | Neither the click pin nor the creation-path equivalence is asserted. Low value individually; listed for completeness. |

Two further clauses are proven but weakly, and belong in the same ledger:

- **R14 payload breadth.** `T20-314` accepts a measure as AD-40-conforming if
  `"unit_kind" in m or m.get("class") == "undefined-measure"` — a line whose
  measures were *all* undefined satisfies it. And
  `coords["instrument"] == outcome.sweep_coordinates["instrument"]` compares the
  ledger against the implementation's own report object (its own trace as observer);
  `sweep_id`, checked against `admitted.label`, is the assertion doing real work.
- **R14 "never zero".** The count is taken from `read_merge_view(..., role="confirmation")`.
  A combo written under a different role would be invisible to that view and would
  read as a drop the test cannot distinguish from a mis-role. Reading the
  unfiltered ledger and *then* partitioning by role closes this.

No requirement from another epic was tested here — the epic-binding rule holds. R23
(ledger role) is the one boundary case: **`epics.md` assigns no role to a sweep
combo anywhere in Epic 20's four stories.** Filing it as an escalation rather than
inventing a ruling is the correct call; see the row-by-row below.

---

## Per `findings.csv` row

`findings.csv` parses (7 columns, 3 data rows, quoting well-formed).

| Row | Requirement | Judgment |
|---|---|---|
| **E20-F01** — sweep-combo ledger role unratified, source defaults to `role=confirmation` | R23 | **UNPROVEN-correctly-recorded.** Verified: `run_sweep_batch(..., role=ROLE_CONFIRMATION)` does default every combo to a bar-eligible `confirmation`, and Epic 20's ACs are silent on a plain sweep combo's role (Story 20.4 AC1 says only "world-and-role-scoped"). Escalating to the operator instead of inventing a ruling is exactly right, and `medium` is the right severity for a bar-eligibility question. **Two corrections:** (a) R23 is a *derived spine question*, not an Epic-20 AC requirement — the row would be cleaner as `requirement_ids=SPEC-GAP` or `B-4/B-12` than as an invented `R23`; (b) the cited test contradicts the row's own scope via `assert len(bar) == 4` (see wrong-expectation #5). |
| **E20-F02** — batch-driver write-side keying has no explicit CT-05 true-collision guard | R2 | **UNPROVEN-correctly-recorded.** The unprovability claim is accurate: `_by_run_id[config.fingerprint.value]` and `_outcomes[combo_fp1.value]` are keyed on full `fp1` strings, and no real SHA-256 collision can be injected through a public surface without editing source. The mitigations cited are real and independently confirmed — `merge_ledger_lines` does refuse-and-alarm on a true collision (tested green by `T20-302c`), and `batch._report` returns `invalid(...)` when an admitted combo has no outcome, so a config-key collision surfaces as a loud refusal rather than a drop. `low` severity is right. Minor: the write-side CT-05 guard is arguably CT-05 / Epic-15-owned rather than Epic-20 — recording it here is harmless and honest. |
| **E20-F03** — the two named test-design authorities are absent from the worktree | PLAN-INTEGRITY | **Genuine — independently verified.** `_bmad-output/` in this worktree contains only `planning-artifacts`; there is no `test-artifacts/` directory, so neither `test-design-qa.md` nor `test-design/QMX-handoff.md` exists. `info` is the right severity and the row correctly states that the L0–L6 mapping and the R-004/R-010 gate ids were reconstructed. **Consequence the row understates:** the 15 P0/P1 assertions and this epic's risk-gate rows could not be honoured, so the P0/P1 labels throughout `PLAN.md` are the author's own reconstruction, not the handoff's. Every coverage claim in `RESULTS.md` is therefore provisional against that authority. |

**Summary of the three rows: 0 genuine product violations, 0 wrong expectations, 3
correctly-recorded UNPROVEN/informational.** The author found no defect in the sweep
package, and on the evidence I read that conclusion is defensible — including the
F-20-01 non-reproduction, which I confirm: the swept parameter reaches
`ResolvedRunConfig.keys`, `keys` is in `IDENTITY_FIELDS`, and `batch._report`
refuses on a missing outcome rather than dropping. No T1 escalation is warranted on
the F-20-01 basis.

**What `findings.csv` is missing.** Under author-rule 6, the eight narrowings M1–M8
each warrant an `observed=UNPROVEN` row. Their absence — not any filed row — is why
this review returns **gaps**. The file's three rows are honest; the file is
incomplete.

---

## Required remediation, ranked

1. **`T20-319`:** replace the four constant read-backs and the `RANK_FORBIDDEN_ACTS`
   self-table loop with behavioural observation — a test-owned sink/recorder that
   registers whether ranking bound, promoted, or sized anything, and a test-owned
   literal list of forbidden acts drawn from the spine.
2. **M1 (R16 fill taint):** produce at least one filled combo and read the taint off
   the resulting artifact/ledger line; add the falsifiable
   `refuse_optimistic_edge_claim(taint="pessimistic")` counter-case. If a fill
   cannot be produced through the public sweep surface at L3, record R16's fill
   clause as UNPROVEN with that reason.
3. **`T20-323`:** drop `len(bar) == 4`, or restate it so it holds under either
   operator ruling.
4. **M2 (governor bound + enqueue-when-full):** observe max concurrent live spawns
   ≤ min(cpu, mem) and that the surplus queued — or file it UNPROVEN as an
   Epic-15-seam exclusion in `findings.csv`, not only in `RESULTS.md` prose.
5. **`T20-307` / `T20-308b`:** replace `admitted.port.frozen is True` with an
   observation, and re-run the fresher-hub probe against `admitted.port` itself. If
   the immutable-hub structure makes the mid-batch counter-case unconstructible,
   record R8's fresher-mid-batch clause as UNPROVEN with that structural reason.
6. **M3–M8:** add the missing counter-cases or file the UNPROVEN rows. Silence is
   the violation; either resolution closes it.
