# L6 REQUIREMENTS-FIDELITY REVIEW — Epic 15: QMB orchestrator, ledger & concurrency

**Reviewed:** `PLAN.md`, `RESULTS.md`, `findings.csv`, and all 8 modules under `qa/tests/epic_15/`.
**Authorities used:** `_bmad-output/planning-artifacts/epics.md` §"Epic 15: QMB orchestrator, ledger & concurrency" (Stories 15.1–15.5, 21 ACs → the PLAN's R1–R21), FR-045, the `docs/` corpus (B-4, B-5, AD-12/14/15/40, AR-17/31/35/50/51/53/59, CT-04/11/13/32), SCN-0012.
**Authorities confirmed absent:** `_bmad-output/test-artifacts/` does not exist in this worktree — neither `test-design-qa.md` (L0–L6 template) nor `test-design/QMX-handoff.md` (the 15 P0/P1 assertions + this epic's risk-gate rows). The PLAN's §1 Process Gap note is factually correct; the L0–L6 taxonomy and the four risk gates were reconstructed. **No test in this suite can be reconciled against the handoff's P0/P1 list, because that list does not exist here.** This is recorded in PLAN and RESULTS and is not held against the author.
**Question asked of each test:** does it assert what the requirement demands, or what the implementation happens to do?
**Nothing was run and nothing was edited.** Source was read as read-only evidence to adjudicate whether an assertion's oracle is the requirement or the implementation.

---

## VERDICT: **gaps**

The suite is strong where it counts most. The flagship exactly-one-ledger-line law (R13 / R-010) is genuinely proven: `finish_run` is driven across a terminal-cause matrix built from B-4/B-5 *before* observing, effects are read back through the real on-disk fragment directory the test owns, the never-two and the never-zero arms are separately pinned, and the "zero lines is correct here" boundary (admission refusal) is pinned so the law cannot misfire. The governor property test is a real property with a reachable refusal arm. The storage-failure test provokes a **real** `OSError` from the OS rather than a pre-normalized package error — fault realism satisfied. The three `findings.csv` rows are all honest and all evidence-backed.

The verdict is `gaps` for three reasons:

1. **Four assertions read the implementation's own self-declared constants or echoed flags back as proof of behaviour** — the first banned shape, verbatim. One of them (R11) is a **P0** in the PLAN's own traceability matrix.
2. **Eleven contract clauses were silently narrowed or dropped** relative to what epics.md demands and what PLAN §4 planned, with **no UNPROVEN row** in RESULTS.md and no `findings.csv` entry. Rule 5 (scope honesty) requires an explicit row for each. One of these narrowings — `provenance=sandbox` — is deferred in RESULTS.md with a reason that is **factually wrong**.
3. **One green test is structurally unfalsifiable** (no counter-case is constructible through its observation channel), which rule 1 says must be recorded as UNPROVEN rather than shipped green.

None of these overturn a green result into a red one; no test in this suite asserts something the requirement does not demand *in the wrong direction*. The gap is fidelity of the **observation channel**, not fidelity of the **expectation**.

---

## 1. Wrong-expectation / wrong-oracle tests

Nine tests. Severity ordered.

### 1.1 GENUINE CONTRACT VIOLATION — `test_l5_system.py::test_abort_kills_only_its_own_process_siblings_survive` [R11, PLAN P0]

```python
assert refusal.context.get("sibling_processes_touched") == ABORT_KILLS_SIBLINGS is False
assert refusal.context.get("killed_os_process") is True
```

`ABORT_KILLS_SIBLINGS` is imported from `qmb.orchestrator.watch`, where it is `Final[bool] = False` (watch.py:54) and is written verbatim into the refusal context by `abort_run` (watch.py:186). The test therefore compares a value the implementation copied out of a constant against **that same constant**, and then asserts the constant is `False`. Under Python's chained comparison this is `(ctx == const) and (const is False)` — both conjuncts are tautologies over source text. `killed_os_process is True` is likewise a flag the implementation writes, not an observation.

**What R11 demands:** "Aborting one run's process kills only that process — sibling processes are untouched" (epics.md Story 15.3 AC3; B-5). **What the test proves:** that `watch.py` declares it does not kill siblings.

**Counter-case that should fail but does not:** change `abort_run` to `os.kill` every live sibling PID while leaving `ABORT_KILLS_SIBLINGS = False` — the test still passes.

**Mitigation (real, partial):** the second half of the test *is* an independent observation — the survivor is driven through `finish_run`, returns `Ok`, and ledgers a line, which does prove the sibling process was not killed. So the **"only"** half of R11 is genuinely observed; the **"kills"** half (victim PID actually dead) is not observed at all. A `psutil`/`process.poll()` check on the victim handle, and a check that the survivor's PID is still alive *before* collecting it, would close this.

### 1.2 GENUINE CONTRACT VIOLATION — `test_l2_component.py::test_abort_declares_no_partial_governed_result` [R12, PLAN P1]

```python
assert result.context.get("partial_governed_result") is False
```

`partial_governed_result` is the source constant `PARTIAL_GOVERNED_RESULT_ON_ABORT` echoed into the refusal context (watch.py:182). This is rule 3's named anti-pattern verbatim: *"state absence-of-effect by observing the sink, not by trusting a returned flag."*

PLAN §4 T-15.3-f planned the correct channel — *"the run's output directory holds no CT-32 result artifact and no governed evidence — only a partial operational log in its own room."* The delivered test creates `out`, hands it to `fake_live`, and **never lists it**. The on-disk channel was dropped.

**Mitigation (real, partial):** the test's other assertion — the aborted ledger line carries `ct32_fingerprint is None` — *is* a genuine sink observation, and it covers the "no governed evidence in the ledger" half of R12. The "its output stays in its own room" half (no result artifact in the run directory) is unobserved.

### 1.3 PARTIAL BANNED SHAPE — `test_l3_contract.py::test_per_run_log_is_never_evidence_bearing` [R19, PLAN P1]

The first two assertions are behavioural and good: an `OperationalRecord` constructed with `is_evidence=True` is **coerced** to `False`, and its `fp1_identity()` reflects that. Those prove CT-11 enforcement.

The last three are self-declared markers:
```python
assert LOG_IS_EVIDENCE is False
assert LOG_KIND == "ad-14-operational"
assert "journal" in EVIDENCE_BEARING_FORMATS and LOG_KIND not in EVIDENCE_BEARING_FORMATS
```
`EVIDENCE_BEARING_FORMATS` is the implementation's own list of what bears evidence; asserting the implementation's log kind is absent from the implementation's own list is a source-text tautology, not a CT-11 proof. The test is not hollow overall — the coercion carries it — but three of its five assertions carry no weight.

### 1.4 PARTIAL BANNED SHAPE — `test_l0_static.py::test_governor_has_no_invented_budget_literal` [R8]

```python
assert "not-a-validated-budget" in governor_src
```
`SANDBOX_CONCURRENT_MOTIVATING_REFERENCE: Final[str] = "not-a-validated-budget"` (governor.py:57). Asserting that the module declares its own disclaimer is the banned shape.

The primary assertion — no `12`/`13`/`14` integer constant appears inside any `ast.Compare` in `governor.py` — is a genuine structural negative and is the right shape for an R-017 gate. Note it **under-detects**: a baked default such as `cpu_budget = cpu_budget or 12` is an `ast.BoolOp`, not a `Compare`, and would pass. The companion test `test_governor_refuses_to_run_without_declared_budgets` is the real behavioural gate for R8 and is sound.

### 1.5 STRUCTURALLY UNFALSIFIABLE GREEN — `test_l2_component.py::test_direct_library_call_ledgers_nothing` [R17, PLAN P0]

The test creates an empty `led` directory, calls `run(...)` — which is never given `led` and has no way to discover it — then asserts `read_merge_view(led, ...) == ()` for three roles. The named counter-case ("a governed ledger line appearing after a bare `run()`") **cannot be constructed through this channel**: no implementation of `run()`, however broken, could write into a `tmp_path` it was never told about. Rule 1 says a requirement with no constructible failing counter-case goes into RESULTS.md as UNPROVEN, not as a green row.

**Mitigation:** R17 is genuinely covered elsewhere — `test_no_write_escapes_pure_run` (cwd stays empty, and the author verified this channel detects a planted sentinel) and the L0 purity gate. So R17 is not unproven; but *this* row in RESULTS.md is a hollow green and should be marked as corroborating, not proving.

### 1.6 ORACLE IS THE IMPLEMENTATION — `test_l5_system.py::test_real_spawn_separate_process_and_named_output_dir` [R1]

```python
assert run_dir.name == ok(run_directory_name(cfg.fingerprint))
```
R1 demands the directory be "named by the run id". The test checks the directory name equals whatever the implementation's own naming function returns for that run id — a function checked against itself. If `run_directory_name` returned a single constant for every input, this passes. The pid assertion in the same test is genuine and is the load-bearing part.

**Mitigation:** `test_l2::test_isolated_output_directories_keyed_by_run_id` independently asserts distinct ids → distinct names, which rules out the degenerate case. An assertion that the run-id fingerprint's own digest text appears in the directory name would make the L5 test self-standing.

### 1.7 ORACLE IS THE IMPLEMENTATION (partial) — `test_l6_property.py::test_governor_property_never_exceeds_min_bound` [R5, R6, PLAN P0]

```python
bound = ok(governor.parallelism_bound(projected_peak_memory=peak))
...
assert governor.running_count <= bound
```
The bound the property checks against is the implementation's own computed bound, not the test's independent `min(cpu_budget, memory_budget // peak)`. A `parallelism_bound` that over-reports would satisfy this arm.

**Mitigation (substantial):** the other two invariants — `reserved_cpu <= cpu_budget` and `reserved_memory <= memory_budget` — are checked against the **test-supplied** budgets and are fully independent, and the L1 tests assert `bound == 3` / `bound == 2` against independently reasoned values. So the property is not hollow; only its first invariant is self-referential. Computing the expected bound in the test would cost one line.

### 1.8 CONFOUNDED REFUSAL — `test_l4_scenario.py::test_scn0012_branch_b_simulated_store_never_governed` [R13, R16]

```python
minted = mint_completed_line(sim, outcome_identity={...}, ct32_fingerprint="fp1:sha256:" + "0"*64)
assert is_refusal(minted)
assert minted.category.value in REFUSAL_REGISTER
```
`ct32_fingerprint` is passed as a raw `str` here, where the L1 test passes a real `Fingerprint`. The refusal may therefore be an `invalid input` on the argument **type**, not the `world=simulated` policy rejection the test claims to prove; `category.value in REFUSAL_REGISTER` is satisfied by any refusal, so the two causes are indistinguishable. The test should assert the refusal's `field`/`context` names the world, or pass a well-formed fingerprint so `world` is the only variable.

**Mitigation:** the other two arms of the same test are sound — `governed_namespace(World.SIMULATED)` genuinely refuses, and the sink `append` of a simulated line genuinely refuses with the absence confirmed by reading the sink (`line_count == 0` on both worlds) — which is rule 3 done exactly right.

### 1.9 OUT OF EPIC SCOPE — `test_l6_property.py::test_concurrency_fingerprint_invariance` [labelled R33]

RESULTS.md labels this "R33 (shared w/ E14)". **R33 is not a requirement in Epic 15's section of epics.md.** Stories 15.1–15.5 contain 21 ACs and none concerns CT-32 fingerprint invariance; deterministic reproduction is Epic 14 (FR-036/FR-037, "the one never-forked event-slice loop: warm-up in-loop, deterministic reproduction"). Per the epic-binding rule this behaviour should be **noted, not tested** here. The test is harmless and well-formed — it is an identity assertion, not a speed one, correctly honouring R-017 — but it is Epic 14's row to claim and it inflates this epic's green count by one.

---

## 2. Missed requirements

All 21 requirement ids (R1–R21) have at least one test, and the PLAN's R1–R21 is a faithful, complete decomposition of Epic 15's 21 acceptance criteria — no whole AC is unmapped. The misses are **clause-level**: text inside an AC that is demanded, is testable, and is neither tested nor recorded as UNPROVEN. Each of these is a rule-5 scope-honesty violation (silent narrowing).

| # | Requirement clause (epics.md / PLAN) | Status |
|---|---|---|
| M1 | **R14 — `provenance=sandbox` on factory-sandbox runs.** RESULTS.md defers this as *"depends on a factory-sandbox deployment context not reproducible in isolation."* **That reason is factually wrong:** `factory_sandbox` is a plain public keyword argument on both `mint_completed_line` (line.py:268) and `finish_run` (ledger.py:324), and `_label_payload` stamps `payload["provenance"] = PROVENANCE_SANDBOX` when it is `True` (line.py:606-610). A two-line test (`factory_sandbox=True` → label carries `provenance`; `False` → absent) proves the clause with no deployment context whatever. Deferred on a false premise. | **untested, wrongly deferred** |
| M2 | **R14 — the *full* AD-12 result label, "evidence class".** `test_completed_confirmation_line_content` asserts only `assert dict(line.result_label)` — non-emptiness. The `evidence_class` key the AC names is never checked, despite `_e15.ledger_line` showing the author knew the key name. | untested, no UNPROVEN row |
| M3 | **R15 — "append-with-fsync".** No test observes durability or its proxy. The observable proxy exists in source (ledger.py:497 handles a torn tail as "not a committed line") and is exactly CT-13's gap-signals-loss: plant a truncated final line in a fragment and confirm the reader refuses to count it as committed. Not tested, not recorded. | untested, no UNPROVEN row |
| M4 | **R15 — "one *fp1-canonical* object per line".** `test_fragment_is_lf_terminated_jsonl_writer_scoped` checks `json.loads` succeeds and that `obj["class"]`/`obj["role"]` are right. Canonicality (stable key order / canonical encoding — the property that makes byte-identical dedup across sandboxes work at all) is not asserted. | untested, no UNPROVEN row |
| M5 | **R16 — "a world-and-role-scoped merge view *over fragments*"; R15 — "many sandboxes merge without coordination".** No test ever writes through **two** WriterId-scoped sinks and reads a merge view containing lines from both. `test_fragment_is_lf_terminated...` constructs a second sink (`worker_slot=1`) but only compares its **path**, never appending through it. `test_cross_fragment_merge_refuses_differing_lines_for_one_run` calls `merge_ledger_lines([a, b], ...)` — a pure list function over in-memory lines, **not** a read over two on-disk fragments. The multi-writer read path, which is the entire point of WriterId scoping, is unexercised end to end. | untested, no UNPROVEN row |
| M6 | **R13 — the never-two *race*.** PLAN T-15.4-b (P0) planned: *"when the completion path and the death-observer fire for the same run near-simultaneously … the sink still receives exactly one line."* The delivered `test_never_two_idempotent_and_collision` calls `sink.append(same)` twice with a hand-built line — it proves the **sink** is idempotent, not that the **orchestrator's two terminal paths** arbitrate to one line. The author's own falsifiability note says a double-`finish_run` injection was tried and yielded 1 line; that stronger check is not in the committed test. | narrowed, no UNPROVEN row |
| M7 | **R13 — "cancelled while still enqueued (never spawned) produces ZERO lines".** PLAN T-15.4-d planned both arms; only the over-budget admission-refusal arm was delivered. The enqueued-cancel arm is absent. | untested, no UNPROVEN row |
| M8 | **R12 — "its output stays in its own room."** See §1.2: the run directory's contents are never listed after the abort. | untested (flag-trusted instead) |
| M9 | **R21 — "leaves a partial log *in its own room*."** `test_crashed_run_leaves_partial_log_in_its_own_room` proves the *negative* half (sibling untouched, no phantom sibling ledger line) but never asserts room A's own `run.log` still exists and holds the partial record after the crash — which is the clause the test is named for. | half untested |
| M10 | **R3 — "no *required Docker*".** `test_no_ray_no_daemon_runtime_platform` covers Ray and daemons only. The Docker clause of the AC is not tested and not recorded. (Also under-detects daemons: it greps `daemon=True`, missing `daemon = True`, `t.daemon = True`, `setDaemon`.) | untested, no UNPROVEN row |
| M11 | **R2 — the purity scan's scope.** PLAN T-15.0-purity (P0) planned a scan of *"everything below `orchestrator/`"*. The delivered `test_run_loop_surface_writes_nothing` scans only `runloop/`, and against a token list drawn from the implementation's own write primitives — plain `open(p, "w")` or `Path.write_text` anywhere in the pure library would pass. Same class of under-detection in `test_process_spawn_only_at_composition_root` (greps `import subprocess`; `from subprocess import Popen` evades). | narrowed, no UNPROVEN row |

**Also noted, correctly out of scope and correctly recorded by the author** (no action): SCN-0012 Branch A stale-Book refusal → Epic 13; CT-32 measure-math correctness → Epics 14/19; Book-bar read-time verdict fold → Epic 19; `study.py` generation stepping → Epic 21.

---

## 3. Per `findings.csv` row

| Row | Requirement(s) | Adjudication |
|---|---|---|
| **E15-F01** — no batch/teardown path ledgers a reaped or abandoned in-flight run | R13, R-010 | **UNPROVEN-correctly-recorded** — and independently confirmed. `spawn_governed` (spawn.py:197) and `spawn_concurrent` (spawn.py:255) both return `Result[tuple[IsolatedRun, ...]]` and take **no** ledger parameter, so no ledger line can be minted through them; `spawn_concurrent` calls `_reap_live(live)` on a start failure (spawn.py:~283), killing already-started siblings and returning the refusal with **zero ledger accounting for the reaped runs**. The description, expected, and observed columns are all accurate. The one criticism: at `severity=medium` this reads softer than it is — a spawned run that is killed and never ledgered is a live hole in the B-4 "never zero, never silently absent" law on the epic's flagship risk gate (R-010), and the honest recording is the only reason it is not a red test. It is correctly filed as UNPROVEN rather than as a failing test, because Epic 15's public surface offers no door through which the assertion could be driven. |
| **E15-F02** — the "12–14 concurrent" figure is not a validated budget | R8 | **UNPROVEN-correctly-recorded.** This is the right call and the right shape: R8 is a *negative* requirement ("never a validated budget until a fingerprinted baseline is measured"), asserting the count as a number would manufacture the very perf claim R-017 forbids, and the AD-13 fingerprinted baseline genuinely does not exist in Epic-15 isolation. The behavioural residue (min-bound admission; refusal to construct a governor with no declared budgets) is tested and green. Severity `low` is right. Sole blemish: the test backing this row carries the self-declared-marker assertion described in §1.4. |
| **E15-F03** — no OS-enforced hard memory cap (Job Object / rlimit) | R10 | **UNPROVEN-correctly-recorded.** Accurate and appropriately scoped. The AC's actual demand — *"Given a limit breach or a cancel, When the orchestrator detects it, Then it produces a typed `aborted` refusal with context"* — is about **detection → typed abort**, and that is proven green for both the time and the memory arm. The row correctly separates the AC (satisfied) from the stronger hard-cap property (not implemented, not testable on this Windows host) instead of conflating them. Severity `low` is right. |

**Summary:** 3 of 3 rows are honest UNPROVEN records. **Zero rows are wrong expectations, and zero rows are misfiled genuine violations.** The `findings.csv` is well-formed, correctly columned, and every factual claim in it that could be checked against source checked out. The author's honesty about what could not be proven is the strongest part of this submission.

What the file is **missing** is the eleven §2 rows: rule 6 requires `findings.csv` to record *"structurally-unprovable-or-unimplemented requirements (mark observed=UNPROVEN)"*, and rule 5 requires *"any contract clause you exclude or narrow"* to get an explicit UNPROVEN row in RESULTS.md. M1–M11 are narrowings that received neither.

---

## 4. What would close this review

Ordered by value per unit of work.

1. **R11 (P0):** replace the `ABORT_KILLS_SIBLINGS` / `killed_os_process` flag reads with an independent liveness check — victim handle `poll()` returns non-`None` after the abort, survivor PID still alive before it is collected.
2. **M1:** add the two-line `factory_sandbox=True` / `False` test for `provenance=sandbox`, and strike the false deferral reason from RESULTS.md.
3. **R12:** list the aborted run's output directory and assert no CT-32 result artifact is present; keep the flag assertion only as a secondary.
4. **M5:** append through two WriterId sinks and read one merge view spanning both fragments — the WriterId design is otherwise untested where it matters.
5. **M3:** plant a truncated final line in a fragment; assert the reader treats it as uncommitted (the observable proxy for append-with-fsync / CT-13 gap-signals-loss).
6. **M6:** drive the never-two race through `finish_run` twice for one run, not through `sink.append` twice.
7. **Rules 5/6 bookkeeping:** add M2, M4, M7–M11 as UNPROVEN rows in RESULTS.md and `findings.csv`.
8. **Scope:** move `test_concurrency_fingerprint_invariance` to Epic 14's suite, or relabel it in RESULTS.md as a cross-epic corroboration that claims no Epic-15 requirement.
9. **Hollow-green hygiene:** relabel `test_direct_library_call_ledgers_nothing` as corroborating (R17 is proven by the cwd-sentinel purity test and the L0 gate, not by this one).
