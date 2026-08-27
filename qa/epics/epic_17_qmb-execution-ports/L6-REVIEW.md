# L6 REQUIREMENTS-FIDELITY REVIEW — Epic 17 (qmb-execution-ports)

**Reviewer question, per test:** does it assert what the requirement demands, or what the
implementation happens to do?

**Verdict: GAPS.**

The suite is well above the tier-1 hollow-green baseline — the composition-order test uses
test-owned recorders, the worst-case pricing guards assert exact values that flip under
`min`→`max`, every absent-calibration arm asserts a returned CT-04 refusal *with* its category
and pairs it with an Ok counter-case, and the calibration-content deferrals are honestly
recorded rather than faked. Roughly 40 of the 51 tests are substantive and falsifiable.

But three things block an "adequate" verdict:

1. **The headline is false.** RESULTS.md claims "Requirements green under rules 1–5 | 33 (each
   with ≥1 substantive, falsifiable test)" and "All 33 owned requirements are met by the
   source". Two owned requirement clauses are **flatly unimplemented** (R8's
   composition-version change, R23's stochastic-seed draw) and were recorded as UNPROVEN
   rather than as defects. A requirement whose demanded behaviour does not exist is not green.
2. **A real integration gap no test could have caught, because no test looked:** the cost port
   never executes on the run-loop path (see §4). The pinned `fill → slippage → cost` order was
   proven only against `apply_execution_ports`, which nothing in the run loop calls.
3. **Silent narrowing (rule 5) in at least four places** — `stale_price_span`, the path-split
   sequencing mechanism, the sub-phase-2/3 call points, and "a fee queried for admission whose
   fill does not occur charges nothing" — each an AC clause that is neither tested nor carried
   as an UNPROVEN row.

---

## 1. Wrong-expectation tests (assert the implementation, not the requirement)

### 1.1 Substituted mechanism — the one that changes a requirement's verdict

**`test_a_composition.py::test_t171i_changing_bound_set_changes_identity_no_drift` (R8, 17.1/AC4)**
AC4: *"composition-version changes whenever the bound port set or its order changes, so identity
never silently drifts."* The test asserts that **`fp1_identity()` fingerprints differ** across
bound sets. That is the implementation's anti-drift mechanism, not the requirement's. The
requirement names one field; `COMPOSITION_VERSION: Final[int] = 1` (`ports.py:93`) never changes,
and `BoundExecution.composition_version` defaults to it. The falsifiable requirement-level
assertion — `bind(cost=zero).composition_version != bind(cost=percent-of-notional).composition_version`
— was constructible and would have **failed**. It was replaced with a passing surrogate and the
gap was demoted to an UNPROVEN row (E17-F04). R8 is graded PASS* and counted in the 33 green.

### 1.2 Banned shape — a module's self-declared constant as proof of behaviour (rule 2)

- **`test_e_financing.py::test_t175a…` — `assert FINANCING_IS_ORDER_FILL is False`.** The AC
  clause "…as an exact-integer Money debit or credit to each open position — **not an order
  fill**" is proven by reading `ports.py:99 FINANCING_IS_ORDER_FILL: Final[bool] = False`.
  The observable version (the rollover emits `FinancingCashEvent`s and drives no `FillPort` —
  a test-owned `RecordingFill` recorder would show `calls == []`) was available and not used.
- **`test_e_financing.py::test_t175d…` — `event.payload["financing_is_order_fill"] is False`
  and `payload["kind"] == FINANCING_JOURNAL_KIND`.** The implementation's own payload is the
  only observer of its own claim (rule 2: "using the implementation's own trace/report as the
  only observer"). The `event_type.value not in ("fill", "order")` assertion in the same test
  is the honest half and does carry the finding.
- **`test_e_financing.py::test_t175e…` — `assert names == list(COST_DRAG_COMPONENTS)`.** The
  AC names the four lines explicitly (fill P&L, slippage, commission, financing); the test reads
  them off the module constant instead. `len(set(names)) == 4` and the exact `total() == money(90)`
  keep this from being fully hollow, but the four *identities* are unasserted.
- **`test_t171h` / `test_t173d` / `test_t172a` — `taint == TAINT_OPTIMISTIC`,
  `fill_basis == FILL_BASIS_WORST_CASE`, `price_basis == PRICE_BASIS_QUOTE_SYNTHETIC`.** All
  compare against constants imported from the module under test. If `TAINT_OPTIMISTIC` were
  redefined to `"live"`, every one of these still passes while SC-06 is violated. The ratified
  literals (`"optimistic"`, `"worst-case"`, `"optimistic-exact"`, `"quote-real"`,
  `"quote-synthetic"`) are stated in the ACs and in LABEL-1 and should be the expected values.
  Cheap fix, real loss of falsifiability. (`test_t171h` also asserts `composition_version == 1`,
  which is asserting the constant that E17-F04 says is wrong.)

### 1.3 Unfalsifiable / tautological greens (rule 1: name the failing counter-case)

- **`test_t173n` (R23 seed).** `derive_slippage_seed(run_a) == derive_slippage_seed(run_a)` is
  true of any pure function; no counter-case exists. The `run_a != run_b` arm is the only real
  assertion. The clause it stands in for ("replay reproduces the same draw") is unimplemented —
  `slip_fill` does `del seed` (`slippage.py:285`) — correctly captured as E17-F07.
- **`test_t173j` (R22).** `handler.mint_intents(...) == ()` asserts that a stub method returns an
  empty tuple. It establishes nothing about intent eligibility. Counted PASS for R22.
- **`test_t171m` (R12).** `refuse_optimistic_edge_claim(claims_edge=True)` passes the conclusion
  in as the argument (rule 2) against a function whose body is `if claims_edge: refuse`. E17-F05
  correctly says the real enforcement is downstream — but then this is an UNPROVEN row's evidence,
  not a green for R12.
- **`test_t174d` (R27, double-call determinism).** `quote()` and `itemize()` both delegate to the
  same `charge_commission` (`cost.py:356`, `:395`), so FEE-3's equality holds by construction and
  the assertion cannot fail. Acceptable as a regression pin; should not be read as verification.
- **`test_t17f_partial_commission_sums_to_whole` (L6).** Uses the `per-lot` shape, where the sum
  identity is `per_lot·Σqᵢ = Σ(per_lot·qᵢ)` — and `_money_from_fraction` refuses rather than
  rounds, so no drift is representable in any shape. The property has no reachable failing arm.
  The `notional-proportional-with-per-order-minimum` shape (which *pro-rates the minimum* —
  `cost.py:591-594`, an unratified choice) is where a real property would bite.

### 1.4 Vacuously-green static gate

**`test_f_static.py::test_t170_no_binary_float_on_money_path`.** The scan walks
`pathlib.Path("qmb/src/qmb/execution")` — a **relative** path — and asserts `offenders == []`.
Run from any cwd other than the worktree root the glob yields zero files and the test passes
having scanned nothing. The self-check probes the scanner against a synthetic string but never
asserts that any file was parsed. One line (`assert len(scanned) >= 11`) closes it. This is the
epic's P0 no-float gate, so the hollow mode matters.

---

## 2. Requirements from this epic's `epics.md` section that NO test covers

All 33 roster rows (R1–R33) map cleanly onto Stories 17.1–17.5 ACs — the roster itself has no
holes. The uncovered items are **AC clauses inside covered requirements**, none of which carry an
UNPROVEN row (rule 5 violations):

| # | Clause (epics.md) | Owner | Status |
|---|---|---|---|
| 1 | **17.3/AC4** — "…or a market order beyond the configured `stale_price_span`" → typed NoFill | R21 | **Untested and unrecorded.** `_stale_guard` implements the Duration arm (`fill.py:767-795`); no test in `qa/tests/epic_17/` ever passes a `stale_price_span`. Only the resting-order (bar-end-precedes-submission) arm is exercised. |
| 2 | **17.3/AC5** — "…a deterministic order **derived by splitting the declared path at each fill price**" | R22 | **Untested and unrecorded.** `split_path_at` + `remaining_paths` (the actual FILL-6 mechanism, in `handler.execute_resting`) is never driven. `test_t173i` calls `rank_resting_on_path` once on a fresh path; the tie-break (equal cross index → `intent_id`, `fill.py:492`) is also untested. |
| 3 | **17.3/AC1 + 17.5/AC1** — "evaluated in run-loop **sub-phase 3**" / "when the run loop reaches **sub-phase 2**, scheduled position-level events" | R18, R29 | **Untested and unrecorded.** `ExecutionSliceHandler.scheduled_position_event` / `.execute_resting` are Epic-17-owned code implementing exactly these call points, with their own requirement-bearing guards (calendar required, WriterId required). Financing is tested only through the free `apply_financing_rollover`. |
| 4 | **17.4/AC4** — "a fee queried for admission whose fill does not occur **charges nothing**" | R27 | **Not proven.** The test states this in a comment ("it emits no `CostedFill` line") rather than observing a sink (rule 3: absence-of-effect is observed, not asserted from a comment). Either drive a recorder or file it UNPROVEN. |
| 5 | **17.2/AC4** — "the Book's **SQS door (AD-39)** needs its spread input" | R16 | **Seam not observed.** Only Epic-17's own `sqs_spread_input` shim is exercised; the real AD-39 door consuming the series is never involved. E17-F06 records the DEC-0153 freshness slot but not this boundary. |
| 6 | **17.1/AC6** — "`world=simulated` is refused" | R11 | **Conflated, not isolated.** The only binder-level test passes `clock="replay"` **and** `data_provenance="synthetic-tainted"` **and** `world=SIMULATED` at once; `_refuse_world` short-circuits on the clock arm first (`binder.py:308-317`), so the world arm is never the cause of the observed refusal. A config with `world=SIMULATED, provenance="recorded"` **is** refused by the source ("world is provenance-derived, never caller-declared") and was testable. |

---

## 3. Per-`findings.csv` row

| Row | Req | Classification | Note |
|---|---|---|---|
| **E17-F01** | R32 | **UNPROVEN — correctly recorded** | Verified against `docs/contracts/ct-13-journal.yaml`: the enum is exactly `decision \| order \| fill \| risk transition \| promotion \| data quality \| control action` and names no financing kind. Asserting the mapping would assert an unratified value. **Downgrade severity to low:** CT-13 line 19 already rules that treasury cash boundary events (sweep, refund, re_seed, paper_epoch_reset) *map onto the risk transition event type* — the code follows a ratified precedent, not an invention. Still worth the ruling. |
| **E17-F02** | R14;R23;R26;R30 | **UNPROVEN — correctly recorded** | The ACs themselves defer content to GAP-0048 ("stays deferred", "no rate is invented"). Mechanism + absence-refuses are proven green and independently. Correct call. |
| **E17-F03** | R10;R15 | **UNPROVEN — correctly recorded** | 17.2/AC3 and 17.1/AC5 defer the ordinal in their own text. Fair. One caveat: LABEL-1 in `spec-fill-fees.md` does ratify the *relative* order (`quote-real > quote-synthetic > trade-only`), and the source implements no ranking between them at all — so this row also conceals a small unimplemented clause. Keep as UNPROVEN, add the LABEL-1 citation. |
| **E17-F04** | R8 | **GENUINE VIOLATION — mis-filed as UNPROVEN** | 17.1/AC4 is unambiguous: "composition-version changes whenever the bound port set or its order changes." `COMPOSITION_VERSION` is `Final[int] = 1` and is never recomputed; the row's own text says "the literal behaviour is not implemented". That is a defect finding with a constructible failing test, not an ambiguity awaiting a ruling. R8 must not be counted green. |
| **E17-F05** | R12;R33 | **UNPROVEN — correctly recorded** | Split-budget enforcement is genuinely CT-12 / Epic-14-owned, and PLAN §1 declares the boundary in advance. Correct. The port-side "green" it leans on is the tautological gate (§1.3) — so R12's Epic-17 half is thin, not proven. |
| **E17-F06** | R16 | **UNPROVEN — correctly recorded (under-stated)** | The DEC-0153 freshness slot is real and deferred. It under-states: the AD-39 door itself is never observed (§2 row 5). Widen the row. |
| **E17-F07** | R23 | **GENUINE GAP — correctly recorded as UNPROVEN** | Confirmed: `slip_fill(..., seed=None) → del seed` (`slippage.py:285`); all five V1 models are deterministic. 17.3/AC6's stochastic-seed clause has no implementation. Recording it as UNPROVEN is right (nothing to test), but like F04 it means R23 is not fully green. |
| **E17-F08** | R11;R22 | **UNPROVEN — correctly recorded (over-broad)** | The Epic-14 boundary is real (`runloop/loop.py:702-704` owns sub-phase-5 ineligibility) and pre-declared in PLAN §1. Over-broad on both halves: R11's binder-side world refusal *was* isolatable (§2 row 6), and R22's path-splitting mechanism is Epic-17 code that was not driven (§2 row 2). |

**Counts: 8 rows → 2 genuine violations/gaps (F04, F07), 6 UNPROVEN-correctly-recorded, 0 wrong
expectations.** No row is a fabricated or defensive finding. `findings.csv` is honest in
substance; its failure mode is *classification* — F04 is a defect wearing an UNPROVEN label —
and RESULTS.md then reads the whole set as compatible with "33/33 green", which it is not.

---

## 4. The single most important gap

**The composed cost port never runs on the run-loop path, and no test looks at the composition
the run loop actually uses.**

There are two disjoint execution paths in `qmb/src/qmb/execution/`:

- `apply_execution_ports` / `BoundExecution.execute` (`ports.py:1024`) — runs
  fill → slippage → cost correctly, with the never-resize and taint guards. **Nothing in
  `qmb/runloop/` calls it** (`grep -rn "apply_execution_ports\|BoundExecution" qmb/src/qmb/runloop/`
  → no hits; the only non-execution references are re-exports in `doors/api/__init__.py`).
- `ExecutionSliceHandler` (`qmb/src/qmb/execution/handler.py`) — Epic 17's implementation of the
  loop's `SliceHandler` Protocol (`runloop/loop.py:600`), the thing the six sub-phases actually
  drive. Its constructor takes **`fill` and `slippage` only**. `execute_resting` runs
  fill → slippage → `split_path_at` and **returns `Ok(True)`**. There is no `CostPort` field, no
  `itemize` call, no `cost` token anywhere in the file.

So in a real run: no commission is itemized, 17.4/AC2 ("each partial carries its own pro-rated
commission, itemized separately") has no producer, and 17.5/AC4's four-line cost-drag
decomposition can never be assembled from live run output — the financing line exists
(`scheduled_position_event` collects `financing_events`) but the commission line does not.

The audit did not surface this because `test_t171b` proves the pinned `fill → slippage → cost`
order against `apply_execution_ports` — the path the loop does not take — and `test_t173j` is the
only test that touches `ExecutionSliceHandler`, asserting that one stub method returns `()`.
This is precisely the failure mode the hardened contract was written to prevent: a green
composition-order test standing over a composition that does not reach production.

**Required follow-up (in order):**

1. Drive `ExecutionSliceHandler` end-to-end for one slice with test-owned `RecordingFill` /
   `RecordingSlippage` / `RecordingCost`, and assert the cost recorder saw the post-slip fill.
   Expected: it fails / cannot be wired — file it as a defect against 17.1/AC1 + 17.4/AC2.
2. Re-file **E17-F04** as a defect (R8 unimplemented) and drop R8 and R23 from the green count;
   correct the RESULTS.md headline from "33 green / no behavioural defect" to the true tally.
3. Add UNPROVEN rows (or tests) for the six narrowed clauses in §2 — `stale_price_span` and the
   path-split sequencing are both implemented and directly testable, so they should be tests.
4. Replace module-constant expectations with the ratified literals (§1.2) and pin the AST scan
   to an absolute path with a `scanned >= 11` guard (§1.4).
