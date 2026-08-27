# RESULTS — Epic 14: QMB Run Loop & Replay Backtest (independent audit)

**Audit tier:** T1. **Package under test:** `qmb/src/qmb/runloop/` (loop, frontier
clock, bars, warmup, observe) plus the seams into `qmb/src/qmb/execution/`,
`qmb/src/qmb/config/`, `qmb/src/qmb/results/`.
**Authored from:** `qa/epics/epic_14_qmb-run-loop/PLAN.md` (Sections 4/5/8) and the
ratified spine (B-2/B-4/B-5/B-6/B-7) + Epic 14 ACs (R1–R37). Tests assert what the
REQUIREMENTS demand, never what the source happens to do.

**Command:** `uv run --with hypothesis pytest qa/tests/epic_14 -q --tb=short`
(run from the worktree root). Property tests use `hypothesis` (200 examples each).

## Headline

| Metric | Count |
|---|---|
| Tests **written** (distinct pytest cases) | 51 |
| **Passed** | 47 |
| **Failed** | 0 |
| **Errored** | 0 |
| **Skipped (blocked scaffolds — Story 14.8)** | 4 |
| **Findings recorded** (`findings.csv` rows) | 0 |

Every executable requirement test is GREEN. No source was modified; no assertion
was softened to pass. The four skips are the cross-epic Story 14.8 scaffolds
(recorded below with owning epic — blocked, not omitted). The run loop's
platform-identity guarantees (pinned sub-phase order, forming-bar
non-actionability, no ambient time below the composition root, golden-slice
determinism) all hold under independent, requirement-derived assertions,
including a subprocess `PYTHONHASHSEED` 0-vs-1 determinism check and hypothesis
property breadth over the `bars.py` weak spot.

## Per-test results

Level per PLAN §5. Priority per PLAN §3. "Meaning" states the requirement the
green assertion proves (for a failure it would state what the failure means — no
failures occurred).

### Group A — frontier clock (Story 14.1) · `test_e14_a_frontier.py`
| Test ID | Req | Lvl | Prio | Status | Assertion proved |
|---|---|---|---|---|---|
| T-14.1-a | R2 | L1 | P0 | PASS | `advance()` is monotone non-decreasing over a fixed cursor. |
| T-14.1-b | R2,R9 | L1 | P0 | PASS | Pull is the min next-emit; chosen instant is declaration-order-invariant; exhausted streams ignored. |
| T-14.1-c | R2 | L1 | P0 | PASS | The clock refuses a rewind (`invalid input`). |
| T-14.1-d | R3 | L1 | P1 | PASS | Emitted instant is AD-8 WALL kind; a `MonotonicReading` is refused as a frontier instant. |
| T-14.1-e | R3 | L1 | P1 | PASS | No `world` input/output on the clock seam; `CLOCK_DOES_NOT_CHOOSE_WORLD`. |
| T-14.1-f | R4 | L3 | P1 | PASS | FrontierClock (and the scripted reuse) IS an AD-8 `Clock` (substitutable). |
| T-14.1-h | R6 | L3 | P1 | PASS | Asserting a simulated instant as wall/replay is a `policy rejection` until GAP-0048. |
| T-14.1-i | R5 | L4 | P2 | PASS | One un-forked loop; clock-vs-no-clock give byte-identical outcome identity; no `run_backtest/replay/live`. |

### Group B — six pinned sub-phases (Story 14.2) · `test_e14_b_subphases.py`
| Test ID | Req | Lvl | Prio | Status | Assertion proved |
|---|---|---|---|---|---|
| T-14.2-a | R7 | L1 | **P0** | PASS | Slice sub-phase order == the pinned 6-tuple, no omission/reorder. |
| T-14.2-b | R8 | L2 | **P0** | PASS | A phase-5 minted intent is resting/ineligible and never filled this slice (even with a would-fill handler). |
| T-14.2-c | R9 | L1 | P2 | PASS | Per-phase instrument order == stream-set declaration order; permuting permutes deterministically. |
| T-14.2-d | R10 | L2 | **P0** | PASS | Indicators receive closed data only; a forming observation never reaches `update_closed_data`. |
| T-14.2-e | R11 | L3 | **P0** | PASS | Permuting the sub-phase order changes the fingerprint — order is identity content. |
| T-14.2-f | R11 | L1 | **P0** | PASS | Order is not a runtime parameter; the dispatcher refuses an out-of-order/unknown phase. |

### Group C — completed-boundary & forming-bar (Story 14.3) · `test_e14_c_bars.py`
| Test ID | Req | Lvl | Prio | Status | Assertion proved |
|---|---|---|---|---|---|
| T-14.3-a | R12 | L1 | **P0** | PASS | Higher bar folds from finest base, emitted only on a completed boundary (no mid-interval emission). |
| T-14.3-b | R13 | L2 | **P0** | PASS | A forming bar is not visible/actionable; acting on it (or listing it readable) is a `policy rejection`. |
| T-14.3-c | R13 | L1 | P0 | PASS | Completeness is inspectable first-class state (forming vs completed; `closed`; fp1 flags). |
| T-14.3-d | R14 | L2 | **P0** | PASS | Bars and fills cite one `series_fp1`; a divergent series is refused. |
| T-14.3-f | R15 | L4 | P2 | PASS | Look-ahead prevention holds with GAP-0048 open; no print after the frontier is consumed. |
| (extra) finest-base | R12 | L1 | — | PASS | `finest_base` returns the genuinely finest declared spec. |

### Group D — in-loop warm-up (Story 14.4) · `test_e14_d_warmup.py`
| Test ID | Req | Lvl | Prio | Status | Assertion proved |
|---|---|---|---|---|---|
| T-14.4-a | R16 | L2 | P1 | PASS | Warm-up drives the same loop, same 6-phase order, trading locked. |
| T-14.4-b | R17 | L2 | **P1** | PASS | Any act during warm-up is a `policy rejection`; minting under lock aborts the run. |
| T-14.4-c | R18 | L1 | P1 | PASS | Embargo is an observation COUNT, not a Duration; no second window. |
| T-14.4-d | R19 | L2 | **P1** | PASS | Evidence range = trading interval only; warm-up frontier excluded. |
| T-14.4-e | R20 | L1 | P2 | PASS | Pre-seeding buffers is a `policy rejection` — not warm-up. |

### Group E — CT-23 intake / ports / CT-29 exits (Story 14.5) · `test_e14_e_execution.py`
| Test ID | Req | Lvl | Prio | Status | Assertion proved |
|---|---|---|---|---|---|
| T-14.5-a/-f | R21 | L3/L2 | **P1** | PASS | Inbound is a CT-23 EntryIntent/ExitIntent or a refusal; a bot-sized order is refused; full-loss-before-open is pinned. |
| T-14.5-b | R22 | L2 | P2 | PASS | Fill decides Fill/NoFill/PartialFill; partials are first-class (own type, remaining qty). |
| T-14.5-c | R23 | L3 | **P1** | PASS | A second close of a virtual position is a `policy rejection` (exactly one CT-29 exit per close). |
| T-14.5-d | R24 | L3 | **P1** | PASS | Every fill carries the `optimistic` taint; claiming edge / spending split budget is refused. |
| T-14.5-e | R25 | L3 | **P1** | PASS | Store-persisted synthetic data derives `world=simulated` and is a `policy rejection` for governed evidence. |

### Group F — cancel & observe (Story 14.6) · `test_e14_f_cancel_observe.py`
| Test ID | Req | Lvl | Prio | Status | Assertion proved |
|---|---|---|---|---|---|
| T-14.6-a | R26 | L2 | **P1** | PASS | Cancel stops at the next slice boundary (exactly one slice done), typed terminal. |
| T-14.6-b | R27 | L2 | P2 | PASS | Progress exposes data-points-processed (monotone) and `is_warming_up` during the run. |
| T-14.6-c | R28 | L2 | **P1** | PASS | An in-loop time/memory breach surfaces a typed `aborted`; no hang. |
| T-14.6-d | R29 | L2 | **P1** | PASS | On abort the pure `run()` writes nothing; no partial governed result. |

### Group G — determinism & reproduction (Story 14.7) · `test_e14_g_determinism.py`
| Test ID | Req | Lvl | Prio | Status | Assertion proved |
|---|---|---|---|---|---|
| T-14.7-a | R30 | L4 | **P0** | PASS | Two identical runs share a byte-identical CT-32 fingerprint. |
| T-14.7-b | R31 | L3 | **P0** | PASS | Re-run reproduces the fingerprint; a mismatch is a typed `policy rejection`. |
| T-14.7-c (ambient) | R32 | L4/L6 | **P0** | PASS | Fingerprint invariant under perturbed wall/monotonic clock, env, and dict insertion order. |
| T-14.7-c (hashseed) | R32 | L6 | **P0** | PASS | Fingerprint identical across `PYTHONHASHSEED=0` and `=1` (subprocess). |
| T-14.7-d | R33 | L5 | P2 | PASS | Loop-purity: a run alongside concurrent siblings is byte-identical (thread half; see blocked note). |

### Group I — static gates & properties · `test_e14_i_static.py`, `test_e14_h_properties.py`
| Test ID | Req | Lvl | Prio | Status | Assertion proved |
|---|---|---|---|---|---|
| T-14.0-imports | R1 | L0 | P0 | PASS | No `runloop/` module imports a system-clock source (AST scan of the 5 modules). |
| T-14.0-state | R32 | L0 | P0 | PASS | No module-global mutable state in `runloop/` (AST scan; `__all__` export manifest excluded). |
| T-14.0-protocol | R22 | L0 | P2 | PASS | fill/slippage/cost are three distinct `typing.Protocol` seams. |
| T-14.1-g | R1 | L2 | P0 | PASS | A poisoned system clock (raises on read) is never touched by a full replay slice sequence. |
| T-14.1-P | R2 | L6 | P0 | PASS | Property: over arbitrary cursors the frontier is monotone and equals the min next-emit. |
| T-14.2-P | R8 | L6 | P0 | PASS | Property: over arbitrary phase-5 injections, no injected intent fills its own slice. |
| T-14.3-e | R13 | L6 | **P0** | PASS | Property (200 cases): no actionable event ever references a forming bar; only completed boundaries emit. |
| (support) modules_present | — | L0 | — | PASS | The five `runloop/` modules exist and are scanned. |

## Blocked / partial requirements (recorded, NOT omissions)

These are recorded here per PLAN §8. They are **not** `findings.csv` rows (that
file is per FAILING test; nothing failed) — they are cross-epic dependencies or
out-of-scope content, each with an owning epic.

| Req | Test ID | Status | Owning epic / reason |
|---|---|---|---|
| R34 | T-14.8-a | SKIPPED (scaffold) | Epics 11/12 — QL-7 CT-33 host factory + host-owned conformance runner not in this worktree's testable surface. |
| R35 | T-14.8-b | SKIPPED (scaffold) | Epic 13 — DEC-0183 config-compiler extensions (`assignment_is_canonical`, producer-template resolution) land there. |
| R36 | T-14.8-c | SKIPPED (scaffold) | Epic 12 — host-owned conformance sandbox (isolated-process verdict suite). |
| R37 | T-14.8-d | SKIPPED (scaffold) | QML tunnel territory (QL-1, FR-047/048); not assertable in `runloop/` isolation — execute at QML/Epic-15 integration. |
| R28 (OS half) | — | PARTIAL | Only the in-loop cooperative surfacing of a typed `aborted` is testable here (T-14.6-c, GREEN). Real OS time/memory enforcement is the **Epic 15** orchestrator/governor. |
| R33 (process half) | — | PARTIAL | Loop-purity/determinism is proven here (T-14.7-d thread half, GREEN). Byte-identity across N **OS-process** siblings needs the **Epic 15** orchestrator. |
| R21 (full-loss enforcement) | — | SEAM | CT-23 gating + the pinned `full_loss_before_open` flag are asserted (T-14.5-a). The actual `require_full_loss_before_open`/`admit_open` enforcement lives in `qmb/execution/risk.py` (deeper seam; Epic 17 territory). |
| R23 (risk-monotonic half) | — | SEAM | The one-exit-per-close guard is asserted (T-14.5-c). The risk-reducing-only exit evaluation lives in `qmb/execution/risk.py::evaluate_exit`; its content is out of the `runloop/` scope. |
| Fill/slippage/cost **fidelity content** (B-6/GAP-0048) | — | OUT OF SCOPE | Only the seam, the `optimistic` taint (R24), and refuse-until-GAP-0048 (R6/R25) are testable now. Asserting a "correct" fill model would assert an unratified value — **GAP-0048 / Epic 17**. |
| SQS modeled-spread input (B-2 tail) | — | OUT OF SCOPE | The read-point is in the loop; the modeled-spread content is an execution-adapter concern — **Epic 17 / GAP-0048**. |

## Notes on method & caveats

1. **PROCESS GAP (carried from the PLAN, re-confirmed).** The two named
   authorities `_bmad-output/test-artifacts/test-design-qa.md` (Per-Epic template
   + L0–L6 architecture) and `_bmad-output/test-artifacts/test-design/QMX-handoff.md`
   (the 15 P0/P1 assertions + risk-gate rows) are **absent from this worktree**
   (confirmed by tree search; `_bmad-output/test-artifacts/` does not exist). The
   L0–L6 taxonomy and the P0/P1 priority set used above were reconstructed by the
   PLAN from the ratified spine + Epic 14 ACs. When those files are restored, the
   priority ladder and level mapping should be re-reconciled; the requirement
   assertions themselves derive from ratified sources and stand independently.

2. **Mutation-sensitivity (PLAN §8 exit criterion 1).** Full mutation testing was
   NOT run: the audit lane forbids editing `runloop/` source. Each P0 guard is
   nonetheless tied to a concrete, non-decorative assertion that would break if the
   guard flipped — e.g. permuting the pinned order changes the fingerprint
   (T-14.2-e), a forming bar refuses action across 200 hypothesis cases (T-14.3-e),
   determinism is asserted end-to-end under hash-seed variation (T-14.7-c).

3. **Coverage floors (PLAN §7).** Branch-coverage numbers for `loop.py`/`bars.py`
   were not re-measured in this lane (coverage instrumentation is a separate gate);
   the weak-spot risk was addressed by targeted branch tests (Groups B/C/D/F) and
   the `bars.py` hypothesis property (T-14.3-e) rather than by a coverage number.

## Verdict

Within the Epic-14-isolable scope, the run loop satisfies every independently
derived requirement test (R1–R33 executable set), including all eleven P0
behaviours. Story 14.8 (R34–R37) is correctly deferred to its cross-epic
dependencies. No findings.
