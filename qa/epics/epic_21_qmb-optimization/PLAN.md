# Verification PLAN — Epic 21: QMB optimization studies

**Audit tier:** **T3** (contract-surface audit of a Wave-7, weight-M, *publish-never-act* epic — no live money at trade time; the damage class is a corrupted trial identity, a dishonest overfit/edge claim, a money-path float leak, or an **invented figure**, never a bad live order).
**Package under test:** `qmb/src/qmb/optimize/` (module homes observed by directory listing only: `space.py`, `objective.py`, `splits.py`, `sampler.py`, `resume.py`, `sensitivity.py`). Seams into `qmb/src/qmb/ledger/` (role=trial views), `qmb/src/qmb/orchestrator/` (spawn/barrier/governor — Epic 15), `qmb/src/qmb/results/` (CT-32 — Epics 14/19), `qmb/src/qmb/config/` (resolved run-config — Epic 13), `qmb/src/qmb/registryread/` (as-of set — Epic 13).
**Delivers:** all of **FR-039** — typed search spaces, objective + hard constraints, train/test split discipline over fingerprinted split manifests, the optuna 4.9.0 TPE-class pure sampler in deterministic generations, resume + cost estimation, and the anti-overfit sensitivity report.
**Governing invariant:** QMB spine **B-8** (declared typed space; pure generation-stepped sampler reading trial history from the *ledger view* only; propose→run→barrier→condition determinism; anti-overfit analysis). Supporting: **B-4** (pure run, reader-derived verdicts, role=trial), **B-5** (process-per-run governor — Epic 15 seam), **B-6/SC-06** (optimistic taint until GAP-0048), **B-7** (world derived from provenance), **B-10** (one CT-32 artifact, charts as data), **B-14** (return-space float carve-out), **B-15/SC-11** (one frozen as-of set per batch). Contracts: **CT-01** (money/unit-kind, float ban), **CT-04** (typed refusal), **CT-13** (journal/ledger line), **CT-32** (performance result), **CT-11/CT-12** (evidence/split — qmf-data seam).

> **PROCESS GAP (read first).** Two authorities named in the audit brief **do not exist in this worktree**:
> `_bmad-output/test-artifacts/test-design-qa.md` (the Per-Epic Test Plan Template + the L0–L6 test-level architecture) and
> `_bmad-output/test-artifacts/test-design/QMX-handoff.md` (the 15 P0/P1 assertions + this epic's risk-gate rows).
> Confirmed absent by full-tree search — the entire `_bmad-output/test-artifacts/` directory is missing; only `_bmad-output/planning-artifacts/` is present.
> **Consequence:** the 8-section structure below, the L0–L6 taxonomy in §5, and the P0/P1 split in §3 are **reconstructed** from the ratified QMB spine (`docs/components/qmb.md` B-1..B-15; DEC-0169/0163/0164/0161), the CT-* contracts, and this project's own vocabulary, following the shape and rules the task prompt states verbatim (8 sections order-load-bearing; Section 4 = an independent requirements-derived list authored before any `src/` read; one behaviour → one level, lower level wins). The risk-gate rows **R-001** (cross-currency `target_value`), **R-010** (one ledger line per run), and **R-013/R-017** (invented peak-memory estimate) are taken from the task brief. When the two files are restored, re-reconcile §1 template order, §3 assertion set, and §5 level definitions against them (recorded in §8 as a blocked input, not worked around).

---

## Section 1 — Epic Context, Scope & Authorities

**What this epic is.** A parameter-optimization **Study** over a Book/BMS. An agent declares a *typed, bounded* parameter space that validates at Study creation; names one objective (measure + direction) plus any number of hard constraint filters; scores each trial on a training split and re-runs the identical parameter set on a testing split, both named by split-manifest fingerprint; drives the optuna 4.9.0 TPE-class **pure** sampler in **deterministic generations** (propose → run → barrier → condition) so a seeded Study proposes identical trials regardless of completion order; can estimate cost before committing compute and resume an interrupted Study from the **ledger view** without re-running completed trials; and emits an **anti-overfit parameter-sensitivity** report. Every trial is a first-class `role = trial` run under B-3/B-4; every fill is `optimistic`-tainted until GAP-0048; the Study **publishes, it does not bench, promote, or bind** — a winner is a read-time ranking that carries no edge claim and no bar verdict. Locked-validation third split and grid/Euler samplers are **deferred out of V1**.

**In scope (Stories 21.1–21.6):** typed space schema + validation (21.1); objective + hard constraints + winner-set + optional `target_value` early-stop (21.2); train/test split discipline over fingerprinted manifests + optimistic taint + `world = replay`-only (21.3); pure TPE sampler in deterministic generations + one frozen as-of set + trial-label identity + reproduce-or-refuse (21.4); resume-from-ledger + cost estimation + clean stop with one ledger line per spawned run (21.5); anti-overfit sensitivity report with isolated-spike flagging + return-space float carve-out (21.6).

**Out of scope (owned elsewhere, seams only here — enforced by the epic-binding rule):**
- **The event-slice run loop + CT-32 *result* artifact byte-reproduction** (Story 14.7 golden-slice determinism) → **Epic 14**. Epic 21 asserts the Study-side trial *label* content and the *reproduce-or-refuse contract*; it does not re-run Epic 14's determinism proof.
- **The canonical CT-32 artifact shape / chart-series extension / HTML render** → **Epic 19** (FR-043). Epic 21 asserts only that the sensitivity report is *carried in* the artifact and that charts cite exact `Bar`/`Price` data.
- **Process-per-run spawn, the `min(cpu,memory)` governor, WriterId ledger append, aborted-line minting** → **Epic 15** (FR-045, B-4/B-5). Epic 21 asserts the *Study-scoped orchestration* (barrier/condition sequencing, one line per already-spawned run on terminate); the primitive append + concurrency cap are Epic 15's.
- **Split seal / embargo / knowledge-time / calendar-in-band boundary enforcement + sealed-holdout exclusion** → **qmf-data / Epic 3** (FR-012, CT-11/CT-12). Epic 21 asserts only that the Study consumes splits *by fingerprint* and cannot reach the holdout via default access.
- **World derivation from data provenance** → **Epic 13/14** (B-7). Epic 21 asserts the Study *admission* refuses a would-be `world = simulated` config.
- **Fill/slippage/cost *fidelity content*, `world = simulated` unlock, taint semantics** → **GAP-0048 / Epic 17**. Only the *presence* of the `optimistic` taint and the refuse-until-GAP-0048 behaviour are testable now.

**Two senses of "tier" (do not conflate).** *Audit tier* **T3** = this plan's scrutiny band: contract-level (L3) assertions over the P0/P1 acceptance criteria, plus targeted regression pins for the two confirmed advisory findings, plus an **L6 review** pass — calibrated to a publish-never-act Wave-7 epic, not the full L0–L6 pyramid a T1 loop epic gets. *Test tier* = the project's `poe check` / `poe check-integration` execution bands (§5 maps our levels onto them).

**Authorities, in precedence order:**
1. Epic 21 section of `_bmad-output/planning-artifacts/epics.md` (lines 4084–4273; Stories 21.1–21.6, ACs; wave row line 415; FR-039 line 296).
2. `docs/` knowledge base: `docs/components/qmb.md` (B-8 line 93–97; B-4 line 77–81; B-10 line 103–105; B-14 line 119–121; provenance/world line 91; sampler pin line 196; FM-5 line 211); `docs/contracts/ct-01` (money/unit-kind/float-ban), `ct-04` (typed refusal), `ct-13` (journal/ledger), `ct-32` (performance result), `ct-11`/`ct-12` (evidence/split — seam). No `docs/scenarios/SCN-*` exercises a Study (SCN-0012 is Epic 14's replay run) — **no golden L4/L5 fixture is planned here** (consistent with T3).
3. `_bmad-output/planning-artifacts/architecture/` QMB spine (B-1…B-15; inherited AD-*).
4. *(Missing — see Process Gap)* test-design-qa.md; QMX-handoff.md. Risk gates **R-001 / R-010 / R-013 / R-017** taken from the task brief.

---

## Section 2 — Requirements → Behaviours Traceability

Every row is a testable behaviour extracted from a ratified source. IDs feed the independent test list (§4) and the matrix (§8). "Ref" cites the governing AC / spine / contract. Priority (§3) in the P column. Behaviours owned by another epic are marked **seam** and are asserted only at Epic 21's boundary.

| # | Behaviour (requirement, stated as an assertion) | Ref | Story | P |
|---|---|---|---|---|
| R1 | A declared space (`name`, `type ∈ {exact int, exact rational, categorical, boolean}`, numeric `min/max/step?/default` or categorical `options+default`) validates at creation and is materialized as **identity-bearing content** of the resolved run-config — never a code edit. | B-8, OPT-1/2, AC21.1 | 21.1 | P1 |
| R2 | A numeric space with `min>max`, `step<=0`, or `step>(max−min)` → a typed **`invalid input`** naming the offending parameter and the violated rule — **never a silent clamp**. | B-8, OPT-3, AD-11, AC21.1 | 21.1 | P1 |
| R3 | A categorical space with empty `options`, or a `default ∉ options` → a typed `invalid input`. | B-8, AC21.1 | 21.1 | P1 |
| R4 | A money parameter's `min/max/step/default` are exact-integer minor-unit values at the declared scale; **a binary float anywhere in the space is an `invalid input`** (money-path float ban). | FR-001, AD-7/AD-22, OPT-4, CT-01, AC21.1 | 21.1 | **P0** |
| R5 | The parameter space is fingerprint **identity content** (AD-10): two Studies declaring the same space share the space fingerprint, and the money path never sees a float in identity. | B-8, AR-14, AC21.1 | 21.1 | P1 |
| R6 | Objective `{measure_identity, direction}` with `direction ∈ {min,max}` and a measure resolving in the AD-23/AD-41 roster is accepted; a `direction` outside `{min,max}` is a typed `invalid input`. | B-8, B-10, OPT-5, AC21.2 | 21.2 | P1 |
| R7 | An objective or constraint naming a metric **absent from the roster** → a typed refusal **at creation time, never deferred to trial time**. | OPT-8, AD-11, AC21.2 | 21.2 | P1 |
| R8 | A trial violating a hard constraint `{measure_identity, op∈{<,<=,>,>=,=,!=}, value}` is **excluded from the winner set yet still appears in the ledger** with the violated constraint named. | B-8, OPT-6, AC21.2 | 21.2 | P1 |
| R9 | The minimum-trades gate is **on by default**; with no explicit floor its floor is a UI-editable configurable with **no spine constant** — a blank floor is permitted and **no number is invented**. | OPT-7, NFR-07, L38, SC-07, AC21.2 | 21.2 | P1 |
| R10 | An optional `target_value` on the objective must share the objective **measure's unit-kind (currency included for money-kind)**; a `target_value` in a **different currency / mismatched unit-kind is a typed refusal**, never a silent numeric "meets it" comparison. **[R-001 — advisory finding]** | CT-01 (unit-kind law), B-8, AC21.2 | 21.2 | **P0** |
| R11 | When a completed generation contains a trial meeting a *valid* `target_value`, the Study **may stop early**, transitioning to a clean terminal state with **partial results preserved**. | OPT-5, OPT-18, AC21.2 | 21.2 | P1 |
| R12 | A named winner is a **read-time ranking** over ledger `role = trial` lines carrying **no edge claim and no bar verdict**; the `optimistic` taint and no-verdict rule stand until GAP-0048. | B-4, B-6, SC-06, AC21.2 | 21.2 | P1 |
| R13 | Per trial, the **training** run computes the objective; the **testing** run executes the **identical parameter set** and records its measures **without contributing to the objective**. | B-8, OPT-9, AC21.3 | 21.3 | P1 |
| R14 | Both split-manifest **fingerprints** appear on the trial label; **"train"/"test" are display aliases only**, never substituted for the fingerprints. | B-8, AC21.3 | 21.3 | P1 |
| R15 | Every trial fill carries the **`optimistic` taint**; the run **cannot spend split budget** and emits **no edge/verdict-bearing claim**. | SC-06, B-6, GAP-0048, AC21.3 | 21.3 | P1 |
| R16 | A Study config resolving to **`world = simulated`** (any run reading store-tainted synthetic data) → a **`policy rejection`**; Studies run **`world = replay` only** in V1. | B-7, SC-06, AC21.3 | 21.3 | **P0** |
| R17 | Warm-up length = the split manifest's declared **embargo observation count** (AD-22 count, never a Duration); the result label's evidence range is the **trading interval only**. | B-2, SC-10, AC21.3 | 21.3 | P1 |
| R18 | The pure sampler port returns the next parameter batch as a **deterministic function of exactly** `(declared space, seed, prior trial results from the ledger view, generation index)` — **no in-process optuna study, daemon, or optuna store** is consulted for trial history. | B-8, B-4, AR-50, AC21.4 | 21.4 | **P0** |
| R19 | Search steps in **deterministic generations** (propose→run→barrier→condition): two runs of the same seeded Study propose **identical trials regardless of completion order**. | B-5, B-8, SC-11, AR-50, AC21.4 | 21.4 | **P0** |
| R20 | A second `ask` before the outstanding generation's `tell` (TPE-class adapter) → an **`unsupported capability`** refusal. | B-8, FM-5, AC21.4 | 21.4 | P1 |
| R21 | A sampler internal float for an exact-integer/exact-rational parameter passes a **named AD-7/AD-22 conversion** (declared rounding mode + target scale); **only the converted value is identity-bearing** — the internal float never enters identity. | B-8, AD-7/AD-22, AC21.4 | 21.4 | P1 |
| R22 | Batch admission freezes **exactly one registry as-of set** through the single B-15 read port for every trial, stamped into the Study label; after admission, fragments resolve **by explicit fingerprint, never name@latest**. | B-15, SC-11, AC21.4 | 21.4 | **P0** |
| R23 | A trial ledgers as `role = trial` with a label carrying **sampler identity + seed + generator provenance + `study_fp`**; re-running the trial under its resolved config **reproduces its CT-32 fingerprint or refuses**; an optuna major bump is a **contract-versioning event**, never a transparent update. | B-8, B-10, AR-29, AC21.4 | 21.4 | **P0** |
| R24 | On resume, completed trials are **read from the ledger view and not re-run**; the deterministic **generation index resumes from the last completed generation**. | B-8, OPT-23, AC21.5 | 21.5 | P1 |
| R25 | Resume relies **only on the ledger view** — **no in-process optuna study or daemon state** is required; the ledger is the **sole source of trial history**. | B-4, AC21.5 | 21.5 | P1 |
| R26 | With an explicit trial-budget policy, a cost estimate reports **projected total trials × measured typical per-trial runtime ÷ governor concurrency cap**, spawning **no trial**. | OPT-17/24, AD-13, FR-046, AC21.5 | 21.5 | P1 |
| R27 | With **no measured per-trial baseline**, an estimate is returned as **`not-yet-measured`, never an invented figure** — including a **peak-memory** estimate, which must be `not-yet-measured` with no measured memory baseline, never a synthesized number. **[R-013/R-017 — advisory finding]** | AD-13 (measure-then-budget), NFR-04, AC21.5 | 21.5 | **P0** |
| R28 | On operator terminate of a running Study → a clean **`stopped`** state; the orchestrator appends **exactly one ledger line per already-spawned run** (completed or `aborted`, **never zero, never two**); partial results are preserved and resumable. **[R-010]** | B-4, AR-51, OPT-18, AC21.5 | 21.5 | **P0** |
| R29 | The result artifact includes **per-parameter objective slices** and a distribution summary (**mean, std, min, max, median**) over all completed `role = trial` ledger lines. | B-8, OPT-22, AC21.6 | 21.6 | P1 |
| R30 | A winner in an unstable neighborhood is **flagged isolated-spike**, distinct from a winner inside a stable cluster. | B-8, OPT-22, AC21.6 | 21.6 | P1 |
| R31 | The report emits **no SR*/search-quality pass/fail verdict and no invented threshold** (thresholds deferred); it describes parameter structure and neighborhood stability only. | SC-07, GAP-0049, AC21.6 | 21.6 | P1 |
| R32 | Chart series **cite exact `Bar`/`Price` inputs**; **no image is ever the canonical payload** (a downsample is a display-only, identity-excluded derivative). | B-10, AC21.6 | 21.6 | P1 |
| R33 | Return-space float carve-out: **P&L/equity stay exact-integer**; floats exist only **inside the statistic under a fixed rounding contract**; any float-valued measure takes **label-derived identity**, never a raw float in identity. | B-14, AD-41, AD-7, AC21.6 | 21.6 | P1 |
| R34 | Every refusal on an Epic-21 path is a valid **CT-04** value (category ∈ the seven; machine-readable context present, non-null; retryability present) — **RETURNED across the public boundary, never raised**. | CT-04 | cross | P1 |

FR/NFR roots: **FR-039** (Studies), **NFR-02** (determinism / no ambient nondeterminism), **NFR-03** (reproducibility of identity), **NFR-04** (measure-then-budget honesty), **NFR-07** (configurable thresholds), **SC-06** (optimistic taint), **SC-07** (thresholds deferred), **SC-11** (one frozen as-of set).

---

## Section 3 — Risk Assessment, Weak Spots & Priority

**Highest-value risk theme.** An optimization Study is the single most powerful **overfit and dishonesty amplifier** in the platform: it searches thousands of parameter sets *precisely to find the one that looks best*, so every honesty seam — the optimistic taint, the no-verdict rule, the sealed holdout, the "no invented figure" law — is under maximum pressure here. The three failure classes that carry platform harm:

1. **Reproducibility / identity collapse (R18/R19/R22/R23).** If the sampler is not a pure function of `(space, seed, prior results, generation index)` — if it consults optuna's own in-process store, a daemon, or wall-order — then a seeded Study is **not reproducible**, two runs diverge, and `study_fp`/trial identity is a lie. Every downstream claim built on a Study inherits the defect and cannot be back-filled. **P0.**
2. **Money-path & unit-kind integrity (R4/R10).** A binary float anywhere in the parameter space, or a **cross-currency `target_value`** compared numerically without a unit-kind guard, silently corrupts identity or fabricates an early-stop decision from an apples-to-oranges comparison. **R10 is the confirmed advisory finding (R-001).** **P0.**
3. **Invented-figure dishonesty (R27).** A cost estimate — especially **peak memory**, which the governor's `min(cpu,memory)` cap depends on — that **synthesizes a number** where none was measured violates AD-13 measure-then-budget and NFR-04. **R27 is the confirmed advisory finding (R-013/R-017).** **P0.**

Plus the evidence-firewall P0s: **R16** (`world = simulated` → policy rejection — the synthetic backdoor LEAN ships must stay closed) and **R28** (exactly one ledger line per spawned run — **R-010**; zero lines loses a run, two lines double-counts it, both corrupt the ledger the winner is ranked from).

**Named weak spots (module inventory known by directory listing; contents NOT read — to be confirmed at execution against the two loci the advisory findings touch):**

| Locus | Why it is the risk centre | Mitigation in this plan |
|---|---|---|
| `sampler.py` | Owns purity (R18), deterministic generations (R19), the ask-before-tell guard (R20), and the AD-7/AD-22 float→identity conversion (R21). Any optuna-global-state read or wall-order dependency here breaks reproducibility silently. | L3 determinism/purity tests T21-317/318/319/320; L6-review determinism scan (no ambient nondeterminism, no optuna store read below the composition root). |
| `objective.py` | Owns the `target_value` comparison (R10) and constraint arithmetic (R8). The **cross-currency `target_value`** finding lives here: a naive numeric compare with no unit-kind/currency guard. | **Regression PIN-1 (T21-309)** — mixed-currency `target_value` must return CT-04; expected to **FAIL** if the finding is real. |
| `resume.py` | Owns cost estimation (R26/R27) and resume-from-ledger (R24/R25). The **invented peak-memory** finding lives here: a synthesized memory figure where AD-13 demands `not-yet-measured`. | **Regression PIN-2 (T21-326)** — peak-memory with no measured baseline must be `not-yet-measured`; expected to **FAIL** if the finding is real. |
| `sensitivity.py` | Owns the anti-overfit report (R29–R33): the return-space float carve-out and the "no invented threshold / no image-as-payload" honesty laws. | L3 tests T21-328..332; L6-review invented-figure scan. |

**Priority ladder (derived — see Process Gap re: the missing 15-assertion handoff):**
- **P0 (must-pass gate; block the epic on any failure):** R4, R10, R16, R18, R19, R22, R23, R27, R28.
- **P1 (high — evidence honesty & correctness):** R1, R2, R3, R5, R6, R7, R8, R9, R11, R12, R13, R14, R15, R17, R20, R21, R24, R25, R26, R29, R30, R31, R32, R33, R34.

The two **regression pins** (R10 → PIN-1, R27 → PIN-2) are the audit's centre of gravity: each **should FAIL against current source if the finding is real**, and the outcome is recorded honestly either way (a PASS means the finding is already fixed / not real — recorded as such, not suppressed).

---

## Section 4 — Independent Test List (authored from requirements, BEFORE any src read)

> **Discipline statement.** This section was written having read **zero files** under `qmb/src/qmb/optimize/`. Directory *names* (`space.py`, `objective.py`, …) were listed for weak-spot targeting, but **no source file's contents were opened**. Every test below asserts what a *requirement* demands — from epics.md ACs, the QMB spine (B-4/B-6/B-7/B-8/B-10/B-14/B-15), and the CT-* contracts — never what the code happens to do. **A failing test is a FINDING, not a licence to edit source or weaken the assertion.** Tier T3 concentrates the executable layer at **L3 (contract conformance)** over the P0/P1 ACs, plus **two regression pins**, plus an **L6 review** (§5). Property/metamorphic breadth that a T1 epic would run as L6 hypothesis tests is, at T3, routed into the L6 *review* lane as reasoning (noted per test). Runner: `uv run pytest qa/tests/epic_21 -q`; refusal/identity contract tests in the `poe check-integration` band; `uv run --with hypothesis ...` only if a concrete metamorphic case is promoted to a property.

### Group A — Typed parameter space (Story 21.1) → R1–R5

- **T21-301** *(L3)* A well-formed space (each declared `type`, numeric bounds or categorical `options+default`) validates at creation **and** is emitted as identity-bearing content of the resolved run-config (present in the fingerprinted config, not a mutated tunnel). **[R1]**
- **T21-302** *(L3)* Each of `min>max`, `step<=0`, `step>(max−min)` returns a CT-04 **`invalid input`** naming the offending parameter **and** the violated rule; assert **no clamped value** is produced. **[R2]**
- **T21-303** *(L3)* Categorical: empty `options`, and separately `default ∉ options`, each return a CT-04 `invalid input`. **[R3]**
- **T21-304** *(L3)* **[money-path P0]** A money parameter whose `min`/`max`/`step`/`default` contains a **binary float** (at any of the four) returns a CT-04 `invalid input`; a well-formed money parameter carries exact-integer minor-unit bounds at the declared scale. **[R4]** **P0**
- **T21-305** *(L3)* **[identity]** Two Studies declaring the **same** space produce the **same** space fingerprint (via the single qmf-core fp1 path); a float never appears in that identity content. **[R5]**

### Group B — Objective & hard constraints (Story 21.2) → R6–R12

- **T21-306** *(L3)* A valid `{measure_identity, direction∈{min,max}}` is accepted; `direction` outside `{min,max}` returns a CT-04 `invalid input`. **[R6]**
- **T21-307** *(L3)* An objective **or** a constraint naming a metric **absent from the AD-23/AD-41 roster** returns a typed refusal **at Study creation** — assert the refusal fires before any trial is scheduled (creation-time, not trial-time). **[R7]**
- **T21-308** *(L3)* A trial whose result violates a hard constraint is **excluded from the winner set** yet **present in the ledger** with the violated constraint named (assert both: absent from winners, present + annotated in `role=trial` view). **[R8]**
- **T21-309** *(L3)* **[REGRESSION PIN-1 — R-001, cross-currency `target_value`]** An objective measure of money-kind currency C1 with an optional **`target_value` declared in a different currency C2** (or a mismatched unit-kind) returns a CT-04 **typed refusal** at the point the "trial meets `target_value`" test would be evaluated — **never** a silent numeric comparison that treats C2's count as C1's. Companion positive: a **same-currency** `target_value` compares cleanly. **[R10]** **P0** — *expected to FAIL against current source if the finding is real; record the actual outcome honestly.*
- **T21-310** *(L3)* When a completed generation holds a trial meeting a **valid** (same-unit-kind) `target_value`, the Study stops early into a clean terminal state with **partial results preserved** and readable. **[R11]**
- **T21-311** *(L3)* A named winner is a **read-time ranking** over `role=trial` ledger lines and carries **no edge claim and no bar verdict**; the winner label shows the `optimistic` taint intact and no `role=confirmation` verdict field. **[R12]**

### Group C — Split discipline (Story 21.3) → R13–R17

- **T21-312** *(L3)* For one trial, the **training** run computes the objective; the **testing** run executes the **identical parameter set** and records measures that **do not enter** the objective (assert the objective value derives from the training split only). **[R13]**
- **T21-313** *(L3)* The trial label carries **both split-manifest fingerprints**; "train"/"test" appear only as display aliases and are **never substituted for** the fingerprints in identity content. **[R14]**
- **T21-314** *(L3)* Every trial fill carries the **`optimistic` taint**; the trial spends **no split budget** and its label bears **no edge/verdict claim**. **[R15]**
- **T21-315** *(L3)* **[evidence firewall P0]** A Study config that would resolve to **`world = simulated`** (stream set reads store-tainted synthetic data) is a **`policy rejection`** at admission — Studies are `world = replay` only in V1. **[R16]** **P0**
- **T21-316** *(L3)* Warm-up length equals the split manifest's **embargo observation count** (an AD-22 count, not a Duration), and the result label's evidence range is the **trading interval only**, excluding warm-up. **[R17]** *(seal/embargo boundary enforcement itself = qmf-data/Epic 3 — §7.)*

### Group D — Pure sampler in deterministic generations (Story 21.4) → R18–R23

- **T21-317** *(L3)* **[reproducibility P0]** The pure sampler port, given `(declared space, seed, prior trial results injected from the ledger view, generation index)`, returns a batch that is a **deterministic function of exactly those inputs** — identical inputs → identical batch across repeated calls; **no in-process optuna study/daemon/store** is consulted (assert history comes only from the injected ledger-view argument). **[R18]** **P0**
- **T21-318** *(L3, concrete metamorphic)* **[reproducibility P0]** Two runs of the **same seeded Study** whose trials **complete in different orders** propose **identical trials** per generation (propose→barrier→condition): feed the same generation's results in order π and order π′ → identical next batch. **[R19]** **P0** *(full permutation breadth → L6 review.)*
- **T21-319** *(L3)* A **second `ask` before the outstanding generation's `tell`** (TPE-class adapter) returns an **`unsupported capability`** CT-04 refusal. **[R20]**
- **T21-320** *(L3)* A sampler **internal float** for an exact-integer/exact-rational parameter passes a **named AD-7/AD-22 conversion** (declared rounding mode + target scale); **only the converted (scaled-integer / exact-rational) value is identity-bearing**; the raw float is absent from identity content. **[R21]**
- **T21-321** *(L3)* **[consistency P0]** Batch admission resolves **exactly one** registry as-of set through the **single B-15 read port**, freezes it for every trial, and stamps it into the Study label; a post-admission fragment resolution by `name@latest` is refused — resolution is **by explicit fingerprint** only. **[R22]** **P0**
- **T21-322** *(L3)* **[identity P0]** A trial ledgers as `role = trial` with a label carrying **sampler identity + seed + generator provenance + `study_fp`**; re-resolving/re-running the trial under its resolved config **reproduces the CT-32 fingerprint or returns a typed refusal on mismatch**; assert an optuna-version change is surfaced as a contract-version delta, not a transparent identity. **[R23]** **P0** *(CT-32 byte-reproduction machinery = Epic 14 — §7; here: label content + reproduce-or-refuse contract.)*

### Group E — Resume & cost estimation (Story 21.5) → R24–R28

- **T21-323** *(L3)* On resume of a Study with completed trials in the ledger, the completed trials are **not re-run** (assert no spawn for them) and the deterministic **generation index resumes from the last completed generation**. **[R24]**
- **T21-324** *(L3)* Resume succeeds with the ledger view as the **only** trial-history input — **no in-process optuna study/daemon state** is present or required. **[R25]**
- **T21-325** *(L3)* With an explicit trial-budget policy **and a seeded measured per-trial runtime baseline** (fixture), a cost estimate returns **projected total trials × measured typical per-trial runtime ÷ governor concurrency cap** and spawns **no trial**. **[R26]** *(governor cap value = Epic 15 seam, referenced not computed.)*
- **T21-326** *(L3)* **[REGRESSION PIN-2 — R-013/R-017, invented peak-memory]** With **no measured baseline**, a cost estimate returns **`not-yet-measured`** for every projected figure — in particular a **peak-memory** projection with no measured memory baseline is **`not-yet-measured`**, **never a synthesized number**. **[R27]** **P0** — *expected to FAIL against current source if the finding is real; record the actual outcome honestly.*
- **T21-327** *(L3)* **[ledger integrity P0 — R-010]** Terminating a running Study yields a clean **`stopped`** state and **exactly one ledger line per already-spawned run** (completed **or** `aborted`; **never zero, never two**); partial results are preserved and the Study is resumable. **[R28]** **P0** *(the general per-run append primitive = Epic 15 — §7; here: the Study-terminate count law.)*

### Group F — Anti-overfit sensitivity report (Story 21.6) → R29–R33

- **T21-328** *(L3)* The emitted result artifact carries **per-parameter objective slices** and a distribution summary (**mean, std, min, max, median**) computed over **all completed `role=trial`** ledger lines. **[R29]**
- **T21-329** *(L3)* A winner in an **unstable neighborhood** is **flagged isolated-spike**, distinct from a winner in a stable cluster (assert the flag differentiates the two constructed cases). **[R30]**
- **T21-330** *(L3)* The report emits **no SR*/search-quality pass/fail verdict and no invented threshold** — assert the artifact contains no numeric threshold constant and no pass/fail field for search quality. **[R31]**
- **T21-331** *(L3)* Chart series **cite exact `Bar`/`Price` inputs**; assert **no image/binary is the canonical payload** (any downsample is display-only and AD-10-excluded from identity). **[R32]**
- **T21-332** *(L3)* Return-space float carve-out: **P&L/equity inputs are exact-integer**; floats appear **only inside** a sensitivity statistic under a fixed rounding contract; a **float-valued measure takes label-derived identity**, never a raw-float-byte hash. **[R33]**

### Group G — Cross-cutting refusal register

- **T21-333** *(L3)* Every refusal produced on an Epic-21 path (T21-302/303/304/306/307/309/315/319/321/326) is a valid **CT-04** value: `category ∈` the seven, machine-readable `context` present (non-null), `retryability` present, **RETURNED** across the public boundary — **never raised** as an exception. **[R34]**

**Independent test count: 33 L3 tests** (2 of which are the regression pins, T21-309 and T21-326).

### L6 review lane (planned deliverable → `qa/epics/epic_21_qmb-optimization/L6-REVIEW.md`)

Not executable pytest — a source-reasoning pass over `optimize/` performed **after** §4 is authored and the L3 suite is written. Checklist:
- **LR-1 — Determinism / no ambient nondeterminism.** Scan `sampler.py` (and the whole package below the composition root) for any read of a system clock, unseeded RNG, dict/set-iteration-order dependence, or **optuna global/study/store state** consulted for trial history. The purity claim (R18) must hold structurally, not only in the two concrete cases (T21-317/318).
- **LR-2 — Money-path float scan.** No binary float on any path transitively contributing to a parameter bound or to identity content (R4/R5/R21) — beyond the declared B-14 return-space carve-out (R33).
- **LR-3 — Invented-figure scan.** No hardcoded numeric threshold or estimate anywhere: peak-memory, per-trial runtime, min-trades floor, SR*/search thresholds — every such figure must be **measured**, **`not-yet-measured`**, or a **registry key** (`qmb_sampler_pin` and configurables), never a literal. Directly supports PIN-2 (R27) and R9/R31.
- **LR-4 — Weak-spot review** of `objective.py` (`target_value`/constraint arithmetic — the unit-kind guard behind PIN-1) and `resume.py` (cost estimator — the baseline gate behind PIN-2).
- **LR-5 — CT-04 register conformance** reasoning across the package (returned-not-raised, correct category), backing T21-333.
- **LR-6 — Ledger-line count reasoning** (R28/R-010): confirm the terminate path cannot append zero or two lines per spawned run at the Study-orchestration seam into Epic 15.

---

## Section 5 — Test-Level Architecture Mapping (L0–L6)

> Reconstructed taxonomy (test-design-qa.md absent). Rule enforced: **one behaviour, one level; the lowest level that can meaningfully assert it wins** — no behaviour re-asserted higher. **T3 deliberately concentrates at L3** (the contract surface) plus two regression pins plus an **L6 review**; it does **not** populate a full L0–L5 pyramid — that scrutiny band belongs to the T1 loop/identity epics (13/14). The justification: Epic 21 is a Wave-7, weight-M, publish-never-act epic whose harm class is contract-level (identity, refusal, taint, invented-figure), which L3 assertions + a reasoning review cover with the right budget.

| Level | Meaning here | Execution band | Epic-21 population |
|---|---|---|---|
| **L0** | Static/structural gates (imports, module-global state, Protocol seams). | lint/type gate | **folded into the L6 review (LR-1)** — no separate L0 suite authored at T3; the determinism/import scan is done as reasoning. |
| **L1** | Pure unit — one pure function, no wiring. | tier-1 | *none at T3* — space-validation and constraint logic are asserted at their **contract** boundary (L3), lower-level-wins deferred to the L3 refusal shape, not duplicated as isolated units. |
| **L2** | Component/integration in-process. | tier-1/2 | *none at T3* — the compose-and-run behaviours (resume, admission) are asserted at their L3 contract outcome. |
| **L3** | **Contract conformance** — CT-01/04/13/32 shape + refusal + identity; sampler purity/determinism; taint/world derivation; ledger-line count; report honesty. | **tier-2** (`poe check-integration`) | **31 contract tests + 2 regression pins = 33** (Groups A–G). |
| **L4** | Scenario / golden-path. | tier-2 | *none* — **no `SCN-*` exercises a Study** (§1); no golden fixture planned at T3. |
| **L5** | System / orchestrated (process-per-run concurrency). | tier-2/system | *none* — process-per-run + governor concurrency = **Epic 15**; Study-side barrier/condition determinism is asserted concretely at **L3** (T21-318). |
| **L6** | Non-functional / property / **review**. | review + tier-2 | **1 review deliverable, 6 checklist items (LR-1..LR-6)**; property breadth (full permutation of R19, arbitrary-space money-float of R4) noted as review reasoning, promotable to a hypothesis property only if a concrete L3 case proves insufficient. |

**Lower-level-wins applications at T3:**
- Space/constraint validation is asserted **once at L3** (as the returned CT-04 refusal — T21-302/303/306), not re-run as L1 units *and* L3 contracts.
- Determinism is asserted **concretely at L3** (T21-317 purity, T21-318 order-invariance) and its *universal* form is carried by the **L6 review** (LR-1) — not duplicated as an L6 hypothesis test unless the concrete cases miss.
- Identity (R5/R23) rides the single qmf-core fp1 path at **L3**; it is not re-derived at a lower level.

---

## Section 6 — Fixtures, Data & Determinism Strategy

**Runner & boundary.** All tests live under `qa/tests/epic_21/` per the audit write-boundary; **source is read-only evidence**. Run from the worktree root: `uv run pytest qa/tests/epic_21 -q` (contract tests in the `poe check-integration` band). A failing test is a **finding recorded in this epic's findings artifact** — never a reason to edit `optimize/` source or soften an assertion.

**Fixtures (controlled test fixtures permitted; no product mock data, no default strategies shipped):**
- **Study corpus:** a small, fully-declared Study config with a typed space spanning all four parameter types (exact int, exact rational, categorical, boolean) + a money parameter; one objective + one hard constraint; two named split-manifest fingerprints (train/test). Substrate for Groups A/B/C.
- **Ledger-view stub:** an in-memory `role=trial` ledger view seeded with prior completed trials (per generation), the **sole** trial-history input to the sampler and to resume — no optuna store, no daemon. Substrate for T21-317/318/323/324/328.
- **Two-order replay fixture:** the same generation's results presented in two completion orders (π, π′) for the metamorphic determinism case (T21-318).
- **Cross-currency `target_value` fixture (PIN-1):** an objective measure of money-kind currency C1 with a `target_value` in C2, plus a same-currency C1 companion (T21-309).
- **Baseline fixtures (PIN-2 / R26):** (a) a ledger with **no** measured per-trial runtime/memory baseline → `not-yet-measured` expected (T21-326); (b) a ledger seeded with a measured baseline → the estimate formula expected (T21-325).
- **CT-01/CT-04/CT-13/CT-32 fakes are shape-faithful** to the ratified contracts (fields, unit-kinds, refusal categories, label shape) — a test that passes against a shape-unfaithful fake is itself a finding.

**Determinism strategy (the spine of the audit):**
1. **Sampler purity is proven by injection, not observation.** Trial history enters the sampler **only** as an argument sourced from the ledger-view stub; the test asserts identical output for identical arguments and is blind to any optuna internal store (T21-317). LR-1 backs this structurally.
2. **Order-invariance is a metamorphic assertion** (T21-318): same seed, permuted completion order → identical proposals. Run under `PYTHONHASHSEED` variation to catch set/dict-ordering leaks in the batch construction.
3. **Identity is content, not float.** fp1 identity tests (T21-305/322) go through the single qmf-core implementation; money-path float tests (T21-304) and the AD-7/AD-22 conversion test (T21-320) prove the float never enters identity.
4. **Values are referenced, never restated.** Governor cap, sampler pin, stale-evidence severity, min-trades floor come from **registry keys** (`qmb_sampler_pin`, configurables) — the tests name keys, never invented literals (SCN-0012 discipline). This is itself the anchor for PIN-2 and R9/R31.

**Refusal discipline.** Every "is refused" assertion (T21-302/303/304/306/307/309/315/319/321/326) checks a **RETURNED** CT-04 typed value with the correct category — never a raised exception across a public boundary (CT-04 invariant; exceptions reserved for programmer error). Folded once into T21-333.

---

## Section 7 — Coverage Targets, Weak-Spot Plan & Deferred/Untestable Requirements

**Coverage posture (T3).** Coverage is a *floor and a map*, never the goal — a green line with no assertion is a finding. T3 gates on **P0/P1-AC contract coverage + the two regression pins + the L6 review**, not a line/branch pyramid. The concrete gates:
- **Every P0/P1 AC in §2 maps to ≥1 L3 test in §4** (traceability matrix, §8) — a shortfall is recorded, not waived.
- **Both regression pins are executed and their real outcome recorded** — a FAIL confirms the advisory finding; a PASS is recorded as "finding not reproduced / already fixed", never suppressed.
- **The L6 review (LR-1..LR-6) is delivered** as `L6-REVIEW.md`, with the determinism, money-path-float, and invented-figure scans explicitly resolved.

**Weak-spot execution order (do the risky work first):**
1. **`objective.py` PIN-1** (cross-currency `target_value`, T21-309) + **`resume.py` PIN-2** (invented peak-memory, T21-326) — the two confirmed findings; run these before the breadth suite so the audit's centre of gravity is pinned first.
2. **`sampler.py` determinism/purity** (T21-317/318/319/320) + LR-1 — the reproducibility P0s.
3. **Evidence-firewall & ledger P0s** (T21-304 money float, T21-315 world=simulated, T21-321 one as-of set, T21-322 reproduce-or-refuse, T21-327 one ledger line).
4. **`sensitivity.py` honesty suite** (T21-328..332) + LR-3.

**Deferred / untestable in Epic 21 isolation (findings, not omissions):**
- **CT-32 *result*-fingerprint byte-reproduction (R23 result-side)** — the event-slice loop + CT-32 artifact are **Epic 14** (Story 14.7); the canonical shape is **Epic 19**. Epic 21 asserts only the trial *label* content + the reproduce-or-refuse *contract* (T21-322). The byte-identical reproduction proof is Epic 14's.
- **Process-per-run spawn, the `min(cpu,memory)` governor, the concurrency-cap number, the general one-line-per-run append primitive** — **Epic 15** (FR-045, B-4/B-5). Epic 21 asserts the Study-scoped terminate-count law (T21-327) and references the governor cap as a value (T21-325), never computes it.
- **Split seal / embargo / knowledge-time / calendar-in-band enforcement + sealed-holdout exclusion** — **qmf-data / Epic 3** (FR-012, CT-11/CT-12). Epic 21 asserts fingerprint-only split consumption and warm-up-as-count (T21-316); the boundary enforcement itself is Epic 3's.
- **Optimistic-taint *content* / fidelity taxonomy / `world = simulated` unlock** — **GAP-0048 / Epic 17**. Only the taint *presence* (T21-314) and the refuse-until-GAP-0048 behaviour (T21-315) are testable now; whether a fill is *correctly modeled* is untestable (would assert an unratified value).
- **SR*/search-quality thresholds + pass/fail verdicts** — **GAP-0049**, deferred. Only the **absence** of any invented threshold/verdict is testable (T21-330), never a threshold value.
- **The measured-baseline cost formula (R26 positive path)** — testable only with a fixture supplying a *measured* per-trial baseline (T21-325 fixture (b)); with no run history in the audited worktree the baseline is synthetic-in-fixture. The *`not-yet-measured`* path (PIN-2) is the primary, source-truthful assertion.
- **Locked-validation third split; grid/Euler samplers** — **explicitly deferred out of V1** by the epic overview; not tested (testing them would assert un-shipped behaviour).
- **Process authorities absent** — test-design-qa.md (template + L0–L6) and QMX-handoff.md (15 P0/P1 assertions + risk-gate rows) are missing (§Process Gap); §1 order, §3 P0/P1 split, and §5 level definitions are reconstructed and must be reconciled when restored. The single largest caveat on the plan's fidelity to the intended template.

---

## Section 8 — Execution, Traceability Matrix & Exit Criteria

**Execution.** `uv run pytest qa/tests/epic_21 -q` from the worktree root; contract tests in the `poe check-integration` band; `PYTHONHASHSEED` varied for the determinism cases (T21-317/318). Every §4 test records a **PASS**, a **FINDING** (a requirement the source does not satisfy — never resolved by editing source or weakening the test), or a **DEFERRED** with its owning epic. The two pins additionally record **FAIL-confirms-finding** vs **PASS-not-reproduced** explicitly.

**Traceability (requirement → test → priority → level → status):** every R1–R34 maps to ≥1 test.

| Req | Test ID(s) | Prio | Level | Status |
|---|---|---|---|---|
| R1 | T21-301 | P1 | L3 | planned |
| R2 | T21-302 | P1 | L3 | planned |
| R3 | T21-303 | P1 | L3 | planned |
| R4 | T21-304 | **P0** | L3 | planned |
| R5 | T21-305 | P1 | L3 | planned |
| R6 | T21-306 | P1 | L3 | planned |
| R7 | T21-307 | P1 | L3 | planned |
| R8 | T21-308 | P1 | L3 | planned |
| R9 | T21-330 (+ LR-3) | P1 | L3/L6 | planned |
| R10 | **T21-309 [PIN-1]** | **P0** | L3 | planned — *FAIL if finding real* |
| R11 | T21-310 | P1 | L3 | planned |
| R12 | T21-311 | P1 | L3 | planned |
| R13 | T21-312 | P1 | L3 | planned |
| R14 | T21-313 | P1 | L3 | planned |
| R15 | T21-314 | P1 | L3 | planned |
| R16 | T21-315 | **P0** | L3 | planned |
| R17 | T21-316 | P1 | L3 | planned (seal enforcement = Epic 3) |
| R18 | T21-317 (+ LR-1) | **P0** | L3/L6 | planned |
| R19 | T21-318 (+ LR-1) | **P0** | L3/L6 | planned |
| R20 | T21-319 | P1 | L3 | planned |
| R21 | T21-320 | P1 | L3 | planned |
| R22 | T21-321 | **P0** | L3 | planned |
| R23 | T21-322 | **P0** | L3 | planned (CT-32 byte-repro = Epic 14) |
| R24 | T21-323 | P1 | L3 | planned |
| R25 | T21-324 | P1 | L3 | planned |
| R26 | T21-325 | P1 | L3 | planned (governor cap = Epic 15) |
| R27 | **T21-326 [PIN-2]** | **P0** | L3 | planned — *FAIL if finding real* |
| R28 | T21-327 | **P0** | L3 | planned (append primitive = Epic 15) |
| R29 | T21-328 | P1 | L3 | planned |
| R30 | T21-329 | P1 | L3 | planned |
| R31 | T21-330 | P1 | L3 | planned |
| R32 | T21-331 | P1 | L3 | planned |
| R33 | T21-332 | P1 | L3 | planned |
| R34 | T21-333 (folds all refusals) | P1 | L3 | planned |

**Exit criteria (epic passes audit when):**
1. **Every P0 test is green** (R4, R16, R18, R19, R22, R23, R27, R28) — *except* that the two pins are judged on truth, not green: **PIN-1 (R10/T21-309)** and **PIN-2 (R27/T21-326)** each record their real outcome; a FAIL is the expected, correct result **if the finding is real**, filed as a confirmed finding, and does **not** block on being "fixed" (source is read-only).
2. **Every P1 AC in §2 maps to a recorded PASS or FINDING** in §4/§8.
3. **The two regression pins are executed and honestly recorded** — FAIL-confirms-finding or PASS-not-reproduced, with evidence, for both R10 and R27.
4. **Every "is refused" test asserts a RETURNED CT-04 refusal** of the correct category (T21-333).
5. **The L6 review is delivered** (`L6-REVIEW.md`, LR-1..LR-6) with the determinism, money-path-float, and invented-figure scans resolved.
6. **Every deferred/blocked requirement (§7) is explicitly recorded** with its owning epic — none silently counted as passed or failed.

**Coverage ledger to maintain alongside execution** (`qa/epics/epic_21_qmb-optimization/`): one row per §4 test id → {level, status PASS/FINDING/DEFERRED, evidence path}, plus the two pin outcomes and the L6-review disposition. Findings land in `findings.csv`; results in `RESULTS.md`.
