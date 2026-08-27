# RESULTS — Epic 15: QMB Orchestrator, Ledger & Concurrency

**Run:** `uv run --with hypothesis pytest qa/tests/epic_15 -q --tb=short`
**Outcome:** **48 written · 48 passed · 0 failed · 0 errored · 3 UNPROVEN facets recorded** (hypothesis not in the synced dev group; run with `--with hypothesis`).
**Source touched:** none. Source is read-only evidence; every assertion states what the ratified requirement demands (epics.md Stories 15.1–15.5 / FR-045 + QMB spine B-4/B-5 + CT-* contracts + SCN-0012), not what the code happens to do.

**Falsifiability (hardened contract rule 1):** the P0 guards were confirmed load-bearing by injecting the violation into the test's own fakes/inputs (never source): driving `finish_run` twice for one run still yields **1** line (never-two is real); an un-driven sink dir holds **0** lines and the aborted line appears **only** because the observer appended it (never-zero append is load-bearing); `cpu_budget=1` queues the 2nd run (min-bound enforced); the "directory-empty" purity channel detects a planted sentinel (not vacuous).

Legend: **PASS** = requirement proven by a falsifiable, independently-observed test. **UNPROVEN** = a requirement facet that is structurally unprovable / out of Epic-15's public surface / OS-conditional, recorded (never counted as green). Effects are observed through the REAL ledger fragment directory the test owns (`read_merge_view`/`read_book_bar`) or through returned `Result` values — never by trusting a returned flag.

---

## Group A — Process-per-run & isolation (Story 15.1 → R1–R4)

| Test | Req | Lvl | Result | Meaning |
|---|---|---|---|---|
| `test_l2::test_no_write_escapes_pure_run` | R2 | L2 | PASS | Pure `run()` returns a value and writes **no** file into the working directory the test owns — no write escapes `run()`. |
| `test_l0::test_run_loop_surface_writes_nothing` | R2,R17 | L0 | PASS | The run-loop compute surface (`runloop/`) contains **no** file-write / fsync / write-primitive — the static face of purity. |
| `test_l0::test_per_run_log_write_primitive_only_at_composition_root` | R2,R18 | L0 | PASS | `open_write_handle` (per-run log write) is referenced **only** under `orchestrator/`. |
| `test_l0::test_ledger_fragment_written_only_by_orchestrator_ledger` | R2,R15 | L0 | PASS | The `ledger.jsonl` fragment sink (`LedgerSink`) lives **only** in `orchestrator/ledger.py` — one ledger writer. |
| `test_l0::test_process_spawn_only_at_composition_root` | R2 | L0 | PASS | No module below the composition root imports `subprocess`/`multiprocessing`/`threading`; only `orchestrator/spawn.py` spawns. |
| `test_l0::test_no_ray_no_daemon_runtime_platform` | R3 | L0 | PASS | No `import ray`, no daemonised thread anywhere in `qmb` — bare uv install runs the same package. |
| `test_l0::test_no_module_global_mutable_state_in_impure_package` | x-cut | L0 | PASS | `orchestrator/` + `ledger/` hold **no** module-global mutable container state (only `__all__` export lists and `Final` constants); impurity lives in context objects. |
| `test_l2::test_isolated_output_directories_keyed_by_run_id` | R1 | L2 | PASS | Distinct run ids key distinct output-dir names; spawning the **same** run id twice is refused (never share a writer). |
| `test_l5::test_real_spawn_separate_process_and_named_output_dir` | R1 | L5 | PASS | A **real** spawn runs in a separate OS process (`worker_pid != orchestrator pid`); the isolated dir exists, named by the run id. |
| `test_l5::test_concurrent_real_processes_never_share_a_writer` | R4 | L5 | PASS | Two **real** concurrent processes get distinct output dirs, distinct pids, and distinct per-run `run.log` files — one-writer-per-stream. |

## Group B — Governor: min(cpu,mem) & enqueue-on-full (Story 15.2 → R5–R8)

| Test | Req | Lvl | Result | Meaning |
|---|---|---|---|---|
| `test_l1::test_admission_bound_is_min_cpu_memory` | R5 | L1 | PASS | Admitted concurrency = `min(cpu slots, memory slots)`; the (bound+1)-th run enqueues, never oversubscribes. |
| `test_l1::test_admission_bound_memory_is_the_constraint` | R5 | L1 | PASS | When memory is the tighter budget, admission follows memory even with spare cpu slots. |
| `test_l1::test_over_total_budget_run_is_refused_not_crashed` | R6 | L1 | PASS | A run whose peak exceeds the **total** budget is a returned typed refusal (register-legal), never admitted, never crashed. |
| `test_l1::test_over_remaining_budget_enqueues_or_refuses_never_admits` | R6 | L1 | PASS | Over-**remaining**-budget enqueues (default) or refuses (`on_full=refuse`) — never a silent third state. |
| `test_l2::test_finish_then_admit_next_queued_run` | R7 | L2 | PASS | A finish admits **exactly one** queued run in FIFO order; running count never exceeds the bound. |
| `test_l3::test_governor_over_budget_refusal_is_register_value_returned` | R6 | L3 | PASS | The over-budget refusal is a **returned** CT-04 value of a register-legal category carrying the run id + budget keys. |
| `test_l6::test_governor_property_never_exceeds_min_bound` | R5,R6 | L6 | PASS | **Property (hypothesis):** over arbitrary submit/release interleavings, running count and reserved cpu/memory never exceed the declared budgets. No throughput number asserted. |
| `test_l0::test_governor_has_no_invented_budget_literal` | R8 | L0 | PASS | **R-017 negative:** no 12/13/14 literal is a governor admission comparison; the figure surfaces only as a documented not-a-budget marker. |
| `test_l0::test_governor_refuses_to_run_without_declared_budgets` | R8 | L0 | PASS | Budgets come from registry keys — constructing a governor with none is **refused** (no baked spine default). |
| R8 — the "12–14 concurrent" figure **as a validated number** | R8 | — | **UNPROVEN** (E15-F02) | Structurally deferred: a validated budget needs an AD-13 fingerprinted baseline; asserting a count would invent a perf claim (R-017). Only the min-bound behaviour is testable, and it is green above. |

## Group C — Cancel tokens & per-run limits (Story 15.3 → R9–R12)

| Test | Req | Lvl | Result | Meaning |
|---|---|---|---|---|
| `test_l2::test_submitted_run_carries_cancel_token_and_declared_limits` | R9 | L2 | PASS | Every submitted run carries a `CancelToken` and the declared `qmb_run_time_limit`/`qmb_run_memory_limit` (values from the config keys). |
| `test_l2::test_signalled_cancel_yields_typed_aborted` | R10 | L2 | PASS | A signalled cancel produces a **returned** typed `aborted` outcome (terminal context = aborted, cause = cancel). |
| `test_l2::test_per_run_limit_breach_yields_typed_aborted[time-limit]` | R10 | L2 | PASS | A per-run time-limit breach yields a typed `aborted` outcome with context. |
| `test_l2::test_per_run_limit_breach_yields_typed_aborted[memory-limit]` | R10 | L2 | PASS | A per-run (observed) memory-limit breach yields a typed `aborted` outcome with context. |
| `test_l3::test_aborted_refusal_category_is_register_legal_not_the_word_aborted` | R10 | L3 | PASS | The aborted refusal's **category** is register-legal and is **not** the literal `"aborted"` (which is a run role/kind), returned not raised. |
| `test_l5::test_abort_kills_only_its_own_process_siblings_survive` | R11 | L5 | PASS | Aborting one **real** process kills only that pid (`sibling_processes_touched=False`); the sibling completes and ledgers one line. |
| `test_l2::test_abort_declares_no_partial_governed_result` | R12 | L2 | PASS | After an abort the ledger's aborted line carries **no** CT-32 fingerprint and the refusal declares `partial_governed_result=False`. |
| R10 — **real OS-enforced hard memory cap** (Windows Job Object / POSIX rlimit) | R10 | — | **UNPROVEN / OS-conditional** (E15-F03) | The gate is the cooperative **observed** breach → typed `aborted` (green above). No OS-level hard cap is set; the watchdog observes peak working set and kills. Real hard enforcement is OS-conditional and not implemented. |

## Group D — The one-ledger-line law (Story 15.4 → R13–R17) — FLAGSHIP R-010

| Test | Req | Lvl | Result | Meaning |
|---|---|---|---|---|
| `test_l2::test_exactly_one_ledger_line_across_terminal_cause_matrix[cancel\|time\|memory\|hard-crash]` | R13 | L2 | PASS | **Flagship:** every terminal cause funnels through `finish_run` to **exactly ONE** aborted-role line carrying refusal context — never zero, never two — observed through the injected ledger directory. |
| `test_l4::test_scn0012_one_governed_run_one_confirmation_line` | R1,R13,R14 | L4 | PASS | The **completion** arm (real spawn): one governed process → **exactly ONE** `confirmation` line. |
| `test_l6::test_exactly_one_line_per_finished_run_property` | R13 | L6 | PASS | **Property (hypothesis):** over arbitrary sequences of terminal causes across N runs, line count == N (each run exactly once). |
| `test_l2::test_never_two_idempotent_and_collision` | R13 | L2 | PASS | A single-owner sink collapses a repeated append to one line and **refuses a differing** second line for one run id (never two). |
| `test_l3::test_cross_fragment_merge_refuses_differing_lines_for_one_run` | R13,R15 | L3 | PASS | Merging two **differing** fragments for one run id is a collision (never an overwrite); identical duplicates collapse to one. |
| `test_l2::test_admission_refusal_produces_zero_lines` | R13,R6 | L2 | PASS | A run refused at admission (over-budget) produces **ZERO** lines — the boundary is pinned so "every submit ⇒ a line" cannot misfire. |
| `test_l3::test_ledger_append_storage_failure_is_surfaced_not_silent` | R13,R15 | L3 | PASS | A real OSError on append surfaces a `storage failure` CT-04 refusal — never a silent never-zero. |
| `test_l3::test_completed_confirmation_line_content` | R14 | L3 | PASS | A completed line carries the AD-12 label, CT-32 fp, raw AD-40 unit-kinded measures, Book-bar fp, and a discriminated role — and stores **no** verdict. |
| `test_l1::test_aborted_line_builder_is_aborted_role_with_refusal_and_no_ct32` | R14 | L1 | PASS | `mint_aborted_line` yields an aborted-role line with refusal context, no ct32, no verdict. |
| `test_l1::test_completed_line_builder_refuses_aborted_role` | R14 | L1 | PASS | The completed-line builder refuses `role=aborted` (aborted is minted only from a typed refusal). |
| `test_l3::test_fragment_is_lf_terminated_jsonl_writer_scoped` | R15 | L3 | PASS | Fragments are LF-terminated JSONL (one fp1-canonical object per line) at a world-and-role-scoped WriterId path; distinct slots never share a file. |
| `test_l2::test_merge_view_book_bar_selects_confirmation_only` | R16 | L2 | PASS | A Book-bar read is a world-and-role-scoped merge selecting `role=confirmation` only; aborted/trial excluded. |
| `test_l2::test_direct_library_call_ledgers_nothing` | R17 | L2 | PASS | A direct library `run()` produces **no** governed ledger line (the read-twin of the purity law). |
| R13 — **orchestrator-teardown-while-in-flight / governed-batch partial failure** | R13,R-010 | — | **UNPROVEN** (E15-F01) | The exactly-one-line law is delivered **only** by the single-run `finish_run` door. `spawn_governed`/`spawn_concurrent` have **no ledger parameter**, return un-ledgerable `IsolatedRun` values (no `LiveSpawn`), and **reap** (kill) in-flight siblings on a hard failure — so a run abandoned at teardown / reaped in a batch gets **zero** ledger lines. This terminal cause (enumerated in PLAN §4 T-15.4-a) is not provable in Epic-15's public surface. |

## Group E — Per-run operational logs (Story 15.5 → R18–R21)

| Test | Req | Lvl | Result | Meaning |
|---|---|---|---|---|
| `test_l2::test_orchestrator_streams_per_run_log_into_run_directory` | R18 | L2 | PASS | The orchestrator streams each run's operational log into `run.log` **inside** the run's own output directory. |
| `test_l3::test_per_run_log_is_never_evidence_bearing` | R19 | L3 | PASS | Per-run logs are AD-14 operational only; a record claiming evidence is **coerced** to non-evidence (CT-11); the log kind is not among evidence-bearing formats. |
| `test_l3::test_correlation_id_excluded_from_fp1_identity` | R20 | L3 | PASS | Structured logs carry a `correlation_id` across boundaries that is **excluded** from fp1 identity (present on the row, absent from identity). |
| `test_l2::test_crashed_run_leaves_partial_log_in_its_own_room` | R21 | L2 | PASS | A crash in room A leaves a partial log in A, does **not** mutate a sibling's log, and writes no phantom sibling ledger line. |

## Group F — Golden scenario (SCN-0012)

| Test | Req | Lvl | Result | Meaning |
|---|---|---|---|---|
| `test_l4::test_scn0012_one_governed_run_one_confirmation_line` | R1,R13,R14 | L4 | PASS | (also in Group D) The golden replay run: one governed process → one confirmation line with genuine CT-32, no verdict. |
| `test_l4::test_scn0012_branch_b_simulated_store_never_governed` | R13,R16 | L4 | PASS | A `world=simulated` (synthetic-store) run is a **policy rejection** for governed evidence: `governed_namespace` refuses, no CT-32 is minted, and a simulated line never enters the governed ledger. |

## Group G / non-functional

| Test | Req | Lvl | Result | Meaning |
|---|---|---|---|---|
| `test_l6::test_concurrency_fingerprint_invariance` | R33 (shared w/ E14) | L6 | PASS | A run alongside a **real** concurrent sibling yields a byte-identical CT-32 fingerprint to the isolated run — concurrency is scheduling only. Identity assertion, no speed. |

---

## Risk-gate verdicts (PLAN §8)

- **R-010 (exactly one ledger line per run):** GREEN for every terminal cause reachable through `finish_run` (cancel, time-breach, memory-breach, hard-crash) + completion (L4) + never-two (idempotent/collision, cross-fragment merge) + admission-refusal ⇒ zero + storage-failure-surfaced. **One caveat:** the teardown/governed-batch partial-failure facet is **UNPROVEN** (E15-F01) — the law lives only in the single-run door.
- **R-009 (refusals are register rows):** GREEN. Every refusal asserted is a **returned** CT-04 value of one of the seven register categories; `aborted` is asserted as a role/kind, never a category (`test_l3::test_aborted_refusal_category_is_register_legal_not_the_word_aborted`); simulated-store → policy rejection; append failure → storage failure.
- **R-011 (branch behaviour by requirement):** the `watch.py` death-observer branches (cancel/time/memory/crash) and `governor.py` admission branches (admit/queue/refuse-total/refuse-remaining/release) and `spawn.py` isolation branches are each tied to a named requirement assertion, not a line-coverage incidental.
- **R-017 (perf claims not invented):** GREEN. No test asserts any throughput/latency/run-count number as a pass criterion; the "12–14" figure is absent from every gate; budgets/limits resolve from registry keys and the governor refuses to run without declared budgets.

## Deferred / out-of-Epic-15-scope (recorded, never counted as pass or fail)

- **CT-32 result *content* correctness (measure math)** → Epic 14 (run loop) / Epic 19 (reports). Here the line **faithfully carries** the fp + raw measures (`test_l3::test_completed_confirmation_line_content`); their computation is out of scope.
- **Book-bar read-time verdict fold** → Epic 19 / Book door. Only the orchestrator's **write** of `role=confirmation` and the role-scoped read selection are tested; the per-requirement verdict is not.
- **SCN-0012 Branch A (stale Book ref → stale-evidence refusal)** → Epic 13 (registry read). Noted, not tested.
- **`provenance=sandbox` correctness beyond field-presence** → depends on a factory-sandbox deployment context not reproducible in isolation.
- **Optimize/sweep generation-stepping (`study.py`)** → Epic 21 (B-8). Only the spawn/governor/ledger primitives are tested here.
- **Missing process authorities** — `_bmad-output/test-artifacts/test-design-qa.md` (L0–L6 template) and `QMX-handoff.md` (15 P0/P1 assertions + risk-gate rows) are **absent from this worktree** (PLAN §1 Process Gap). The L0–L6 taxonomy and the four risk gates were reconstructed from the ratified sibling plans + the task brief and must be reconciled when the files are restored.
