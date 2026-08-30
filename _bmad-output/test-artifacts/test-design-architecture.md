---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted:
  [
    'step-01-detect-mode',
    'step-02-load-context',
    'step-03-risk-and-testability',
    'step-04-coverage-plan',
    'step-05-generate-output',
  ]
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-08-27'
workflowType: 'testarch-test-design'
runScope: 'system-level'
runKey: 'system'
inputDocuments:
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/planning-artifacts/prds/prd-QMX-2026-08-21/prd.md
  - _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/architecture/architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md
  - docs/contracts/ (CT-01..CT-34)
  - docs/decisions/ (ADR-0001..ADR-0018)
  - docs/scenarios/ (SCN-0001..SCN-0012)
  - docs/constitution.md
  - conventions/failure-register.md
  - QMX-worktrees/epic-020-qmb-sweeps-report.md
  - QMX-worktrees/epic-021-qmb-optimization-report.md
  - QMX-worktrees/epic-022-qmb-robustness-report.md
  - QMX-worktrees/epic-023-qmb-synthetic-data-report.md
  - battery/skylos/SUMMARY.txt, quality-buckets.csv, critical-findings.csv
  - battery/coverage/package-coverage.csv, uncovered-lines.csv
  - battery/vulture/vulture-100.txt
  - .claude/skills/bmad-testarch-test-design/resources/knowledge/{risk-governance,probability-impact,test-levels-framework,test-priorities-matrix,nfr-criteria,test-quality,adr-quality-readiness-checklist}.md
---

# Test Design for Architecture: QMX V1 — Independent Verification of the Built Platform

**Purpose:** Architectural concerns, testability gaps, and NFR requirements that Architecture and the factory lanes must address before independent verification can produce trustworthy evidence. This is the contract between QA and Engineering on what must change in the system so that quality can be proven rather than asserted.

**Date:** 2026-08-27
**Author:** Master Test Architect (TEA), for Mubarak
**Status:** Architecture Review Pending
**Project:** QMX
**PRD Reference:** `_bmad-output/planning-artifacts/prds/prd-QMX-2026-08-21/prd.md` (final, 2026-08-21)
**ADR Reference:** `docs/decisions/ADR-0001..ADR-0018` + three ratified architecture spines (QMX / QMB / QML)

---

## Executive Summary

**Scope:** All 23 epics / 131 stories of QMX V1 (QMF roster + QMB + QML) as merged on `integration@2c8d495`. This is a post-build verification design, not a pre-build one: the code exists, the machines have already scanned it, and the question is no longer "will it be built right" but "does what was built mean what the requirements say".

**Business Context** (from PRD):

- **Impact:** Live money will eventually run on this code. A sizing error, a governance-gate bypass, or a corrupted evidence seal is not a defect — it is a loss.
- **Problem:** Every line of code and every test in the repository was authored by the same agents. The suite is large (3899 passing, 86.97% line / 75.01% branch) but it is not an independent oracle. Epic 23's own advisory review recorded the failure mode verbatim: two claim-class gates disagree, and *"both behaviors are test-pinned, so the suite ratifies the contradiction."*
- **Milestone:** No GA date. The stopping point of this phase is a findings inventory, a fix-card backlog, and a proof map — not a green suite.

**Architecture** (from the ratified spines):

- **Key Decision 1:** Exact scaled integers on the money path, int64 UTC-ns time, injected clocks — floats and ambient clock reads are a taint (CT-01/CT-02; ADR-0013).
- **Key Decision 2:** Value-or-typed-refusal at every public boundary; exceptions are reserved for programmer error (CT-04; AR-13).
- **Key Decision 3:** Deterministic `fp1:sha256` identity on every governed artifact; the resolved run-config fingerprint *is* the run id and the ledger key (CT-05; AR-52).
- **Key Decision 4:** Books are the only gate to money; the BMS accounts and constrains but never trades; only a human-signed promotion reaches the live zone (CT-22/23/27; L17; AR-39).
- **Key Decision 5:** Stack — CPython 3.14, uv workspace, seven roster packages + two application wheels, no database server, no Docker, no threads below the venue edge.

**Expected Scale** (from ADR-0014): the ~40-bot reference workload, benchmarked at the 10/100/200 marks. No throughput or latency numbers are ratified — measure-then-budget is the ruling, and this plan does not invent any.

**Risk Summary:**

- **Total risks**: 21
- **Critical (score 9)**: 3
- **High (score 6)**: 9 — 12 risks require immediate mitigation
- **Test effort**: ~380–520 independent tests (~285–490 hours; ~4–7 weeks of parallel factory-lane time)

---

## Quick Guide

### BLOCKERS — Team Must Decide (Can't Proceed Without)

1. **B-1 / R-005: The tier-1 static scanners were never in the executed gate.** `poe check` declares `money-path-scan`, `ambient-scan`, `mock-data-scan`, `secret-scan`, `cov-report` and `test-tools`; the factory's per-story gate ran `ruff check .`, `poe types`, `poe test` only. Epic 21's report records a live `poe ambient-scan` failure at `qmb/src/qmb/data/download.py:127` and notes "ambient-scan is not part of the ratified quality gate". The two mechanisms that make FR-001 (no floats on the money path) and FR-002 (no ambient clock reads) *mechanically* enforceable have therefore never run against the shipped tree. Decide: reconcile the ratified gate with `poe check`, or rule the scanners advisory and accept FR-001/FR-002 as human-verified only. (recommended owner: Operator + factory lane)

2. **B-2 / R-003: Oracle independence needs a repo-level rule, not a convention.** The independent suite must be structurally unable to inherit the shipped suite's blind spots. Decide and record: `qa/` lives on its own branch, carries its own pytest configuration, and may never import from any package's `tests/` package, conftest, or fixtures. Without this ruling the fan-out will "reuse the existing factories" and reproduce the defect. (recommended owner: Operator + Architecture)

3. **B-3 / R-006: Door parity is enforced by a hand-maintained map that can go stale.** `qmb/src/qmb/doors/parity.py` maps door surfaces literally; epic 23 shipped four capabilities on the CLI only, the map still pointed `data.generate` at a pre-existing stub, and the parity test passed while proving nothing (AR-58 / B-1 one-door law). Architecture must decide whether parity is derived from the door surfaces themselves (enumerate exported callables per door and diff) or stays a literal map with an accompanying completeness check. QA cannot write a meaningful parity test against a self-declaring map. (recommended owner: QMB / Architecture)

**What we need from team:** three decisions before the fan-out starts. Everything else in this document is a recommendation QA can act on alone.

---

### HIGH PRIORITY — Team Should Validate (Recommendation Provided, You Approve)

1. **R-001: Make unit-kind and currency required, refusal-bearing parameters on every shared numeric primitive.** Three independently-found instances (`objective.meets_target` ignoring `target_currency`; `carve_return_statistic`'s `unit_kind` default acting as a money-path back door; `summarize_distribution` accepting mixed USD/EUR/dimensionless and returning `Ok`) are one design fault, not three bugs: a shared primitive that treats dimension as optional. Approve as a qmf-core/qmf-risk convention. (implementation phase)
2. **R-002: Order-of-operations rule for conversion boundaries — bound and check *before* converting.** All four evidenced typed-refusal breaches (`carveout.py:137,192`, `significance.py:414`, and the `sampler.py`/`sensitivity.py` overflow class) convert first and validate after. Approve as an AR-13 addendum so the property test "no public boundary raises" can be made a universal law rather than a per-site fix. (implementation phase)
3. **R-009: Four packages ship no failure register at all** — `qmf-venue`, `qmf-risk`, `qml`, `qmf-calendar-forex` have no `FAILURES.md`; `qmb/FAILURES.md` stops at FR-37 with ~12 known unregistered modes from epic 22 alone. `conventions/failure-register.md` calls a designed failure with no entry an incomplete story. Approve the register backfill as fix-card work, and approve QA treating register completeness as a testable requirement (NFR-11). (implementation phase)
4. **R-014: AR-22 has harnesses but no baselines.** Every roster package ships `_bench.py`; `qml` ships none; nowhere in the tree is there a fingerprinted per-(OS, CPU-class) baseline file or a recorded regression threshold, so AR-22's Tier-2 regression gate cannot fire. Approve committing baselines + the threshold, or record that AR-22 is deferred. QA will not invent the number. (implementation phase)
5. **R-016: Determinism (NFR-03) has no golden corpus.** "Same inputs produce the same fingerprints and the same results" is a platform property with nothing stored to replay against. Approve a committed golden-run corpus (run ids + resolved-config fp1 + CT-32 fp1) so reproduce-or-refuse becomes checkable rather than self-referential. (implementation phase)

**What we need from team:** review and approve, or propose an alternative.

---

### INFO ONLY — Solutions Provided (Review, No Decisions Needed)

1. **Oracle strategy**: six levels, each with a named judge — machine sweeps (the tool), property tests (a contract-stated invariant), contract tests (the CT-* YAML), acceptance tests (the epic AC sentence), scenario tests (the SCN-* walkthrough), mutation (surviving mutants). One agentic seat per epic for requirements fidelity; no adversarial review panels.
2. **Independence rule**: independent tests are authored from requirement text. The author may read a public signature in order to call it; the author does not read the implementation body before the test list is written.
3. **Location**: a `qa/` tree on a dedicated branch cut from `integration`, mirroring the epic structure, with its own dependency group (adds `hypothesis`, extends `mutmut`).
4. **Traceability**: every test carries `@pytest.mark.req(...)` ids; a test with no requirement id fails collection; the markers generate the proof map over FR/NFR/AR/CT/SCN.
5. **Coverage**: ~380–520 scenarios prioritized P0–P3 against the risk register.
6. **Stopping point**: findings inventory + fix-card backlog + proof map. Zero fixes, merges or deletions before the operator has all three.

See the companion QA document (`test-design-qa.md`) for the execution recipe, the ranked 23-epic list, and the per-epic template.

---

## For Architects and Devs — Open Topics

### Risk Assessment

**Total risks identified**: 21 (3 critical score 9, 9 high score 6, 6 medium score 3–4, 3 low score 1–2)

#### Critical Risks (Score 9) — GATE-BLOCKING

| Risk ID   | Category | Description                                                                                                                                                                                                                                                                                                          | Probability | Impact | Score | Mitigation                                                                                                                                                       | Owner            | Timeline           |
| --------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ------ | ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------------ |
| **R-001** | **DATA** | Unit-kind / currency confusion at shared numeric primitives silently produces a meaningful-looking wrong number on the money path. Three confirmed live instances across three epics (E21-H1, E22-M4, E22-M5); one of them verified returning `Ok` for a mixed USD/EUR/dimensionless distribution.                       | 3           | 3      | **9** | Required dimension parameters on shared primitives (see HIGH-1); hypothesis properties over the full unit-kind × currency cross-product; mutation on the money path. | qmf-core / qmf-risk | Before any fix lane |
| **R-002** | **TECH** | The CT-04 / AR-13 typed-refusal envelope is breached — public boundaries raise instead of returning. Four evidenced entry points raise `OverflowError`/`ValueError` live (`carveout.py:137,192`, `significance.py:414` + propagation through `run_significance_gate`), plus the `sampler.py`/`sensitivity.py` class. | 3           | 3      | **9** | Universal property test: for every public callable on every package's export surface, no input produces an exception. Convert-after-check rule (HIGH-2).            | Every package owner | Before any fix lane |
| **R-003** | **TECH** | Tests share authorship with the code, so the suite ratifies the implementation rather than the requirement. Confirmed verbatim in E23-M5 (contradictory gates both test-pinned); E20-#5/#6 and E21-#5 record contract seams pinned only by hand-built fixtures on both sides.                                          | 3           | 3      | **9** | The entire independent-suite programme; structural isolation of `qa/` (BLOCKER B-2); requirements-fidelity review seat per epic.                                   | QA               | This phase          |

#### High-Priority Risks (Score 6) — IMMEDIATE ATTENTION

| Risk ID | Category | Description                                                                                                                                                                                                                       | Probability | Impact | Score | Mitigation                                                                                                          | Owner              | Timeline    |
| ------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ------ | ----- | -------------------------------------------------------------------------------------------------------------------- | ------------------ | ----------- |
| R-004   | DATA     | fp1 identity collisions silently drop or conflate governed artifacts. E20-H1: colliding resolved-config fp1s dropped sweep combinations and produced zero ledger lines. E23-M4: scenario run ids omit index and anchor flag, so an anchor and a perturbed scenario are indistinguishable on disk. | 2           | 3      | 6     | Identity-completeness property per artifact kind: distinct semantic inputs ⇒ distinct fp1, over generated inputs.      | qmf-core / QMB     | Fix lane    |
| R-005   | OPS      | The tier-1 static scanners (FR-001 float ban, FR-002 clock ban, mock-data, secret) never ran in the executed build gate; a live `ambient-scan` failure is already recorded.                                                          | 3           | 2      | 6     | Run the full `poe check` sequence once on `integration` as the L0 baseline, before any authored test (BLOCKER B-1).    | Operator / factory | Phase entry |
| R-006   | BUS      | Door parity proves nothing for single-door capabilities; the human's only surface can silently diverge from the API. E23-H1: four epic-23 capabilities exported from the CLI only, parity map pointing at a stub, test green.        | 2           | 3      | 6     | Surface-derived parity test (BLOCKER B-3): enumerate every door's exported callables and diff, per AR-58.              | QMB / QA           | Fix lane    |
| R-007   | DATA     | Silent corruption from trusted-but-unvalidated inputs. E23-H3: source-series `scale` trusted verbatim — scale-3 data into a scale-5 config returns `Ok` with a 100× price error. E22-M3: 25% of perturbation scenarios bottoming at an unrecorded zero-clamp. | 2           | 3      | 6     | Adversarial-input acceptance tests per intake seam; provenance fields for any transformation that alters values.       | qmf-data / QMB     | Fix lane    |
| R-008   | TECH     | A governance refusal implemented at one shape of a polymorphic input is bypassed by another shape. E23-H2: `{"generator_config": {...}, "clock": "replay"}` generates where the flat shape correctly refuses.                        | 3           | 2      | 6     | Every governance gate tested over the full set of accepted input shapes, generated from the config schema not by hand. | QMB / QA           | Fix lane    |
| R-009   | OPS      | NFR-11 failure registers absent (`qmf-venue`, `qmf-risk`, `qml`, `qmf-calendar-forex`) or incomplete (`qmb` stops at FR-37; ~12 modes unregistered from epic 22 alone; E20-#4, E21-#6). A product user meets a refusal nobody documented. | 3           | 2      | 6     | Register completeness as a checkable requirement: every typed refusal reachable from a door has a register entry.      | Package owners     | Fix lane    |
| R-010   | DATA     | AR-51's "exactly one ledger line per run, never zero, never two" breaks on failure paths. E20-#3: hard-failure teardown kills in-flight combos without minting aborted lines. E21-#4: a storage refusal in `stop_study` leaves later runs un-cancelled and un-ledgered. | 2           | 3      | 6     | Fault-injection acceptance tests over the abort/teardown/cancel matrix, asserting ledger cardinality.                  | QMB                | Fix lane    |
| R-011   | TECH     | The coverage-weak band conceals behaviour in the two largest packages: `qml` 80.8% line / 66.0% branch, `qmb` 83.2% / 66.5%. Worst files `_coerce.py` 58.3%, `spawn.py` 59.8%, `qmb data/verify.py` 59.9%, `runner.py` 61.4%, `gap_check.py` 62.8% — the same files carrying the CRITICAL complexity findings. One decision in three has never executed. | 3           | 2      | 6     | Tier the epic fan-out by this band; branch-targeted acceptance tests, not line-chasing.                                | QA                 | This phase  |
| R-012   | DATA     | Seal, split and world governance (CT-11/CT-12, L18/L19, AR-33) is asserted at one boundary where the requirement says "at every boundary". A holdout leak or a cross-world read is undetectable after the fact.                      | 2           | 3      | 6     | Exhaustive boundary census: enumerate every read path into `qmf-data` and assert the seal/split/world refusal on each. | qmf-data / QA      | Fix lane    |

#### Medium-Priority Risks (Score 3–5)

| Risk ID | Category | Description                                                                                                                                                                          | Probability | Impact | Score | Mitigation                                                                                    | Owner            |
| ------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ------ | ----- | ---------------------------------------------------------------------------------------------- | ---------------- |
| R-013   | PERF     | Invented figures substitute for measurement, contradicting NFR-04. E21-H2: `projected_peak_memory = 1` deletes the memory half of `min(cpu, memory)`; reviewer measured 16× wall-time understatement. | 2           | 2      | 4     | Refuse-rather-than-default rule at estimate sites; acceptance test that an unmeasurable estimate refuses. | QMB              |
| R-014   | OPS      | AR-22 benchmark baselines are not fingerprinted or committed and no regression threshold is recorded; `qml` ships no `_bench.py` at all, so its Tier-2 gate cannot fire.                 | 2           | 2      | 4     | Commit baselines + threshold (HIGH-4); add a `qml` harness.                                    | Architecture     |
| R-015   | TECH     | AR-19 contract-test completeness is unproven. Named CT test modules exist for roughly 20 of 34 contracts; the remainder may be covered under other names or not at all, and no consumer-side execution is visible. | 2           | 2      | 4     | One independent contract module per CT-*, parameterized over every implementer and consumer.    | QA               |
| R-016   | TECH     | NFR-03 determinism has no golden corpus to replay against, so reproduce-or-refuse is self-referential.                                                                                  | 2           | 2      | 4     | Commit a golden-run corpus (HIGH-5); weekly replay comparing CT-32 fingerprints.                | QMB              |
| R-017   | PERF     | Concurrency and backpressure under the governed cap (AR-50/51) rest on the worst-covered code in the repository: `spawn.py` 59.8% line / 50.8% branch (55 quality findings), `watch.py` 64.3% / 37.0%. | 2           | 2      | 4     | Orchestrator fault-injection matrix at L3; process-isolation acceptance tests.                  | QMB              |
| R-018   | BUS      | Look-ahead safety (B-2 forming-bar rules, warm-up boundary SC-10, declared stream sets) rests on author-written tests. Blast radius is capped for now by SC-06: all fills are `optimistic`-tainted and no verdict-bearing backtest ships until GAP-0048. | 2           | 2      | 4     | Causality property test: no object's value at `t` depends on any input with timestamp `> t`.    | qmf-structure / QMB |

#### Low-Priority Risks (Score 1–2)

| Risk ID | Category | Description                                                                                                                                                    | Probability | Impact | Score | Action                                                            |
| ------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ------ | ----- | ------------------------------------------------------------------ |
| R-019   | SEC      | Secret leakage through repr / serialization / logging paths (AR-37, L34). Skylos reports secrets 100 A+, AI-defects 100 A+, 0 dependency vulnerabilities.        | 1           | 2      | 2     | Monitor — one `SecretValue` rendering property test; do not re-scan. |
| R-020   | OPS      | Packaging integrity (AR-06/AR-18): `poe isolated-build` exists and proves undeclared imports fail, but Tier 2 was not part of the executed per-story gate.       | 1           | 2      | 2     | Monitor — folded into the L0 baseline sweep.                        |
| R-021   | OPS      | A known concurrent-I/O flake class: `test_orchestrator_log.py::test_crashed_run_leaves_partial_log_...` failed once in a full suite and passed in isolation.     | 2           | 1      | 2     | Monitor — quarantine list, burn-in on the qa branch, no fixes.       |

#### Risk Category Legend

- **TECH**: Technical/Architecture (contract breaches, integration, fragility)
- **SEC**: Security (secrets, access control, data exposure)
- **PERF**: Performance (SLA, degradation, resource limits)
- **DATA**: Data Integrity (loss, corruption, inconsistency, identity)
- **BUS**: Business Impact (logic errors, wrong decisions, user harm)
- **OPS**: Operations (gates, deployment, monitoring, recoverability)

---

### NFR Testability Requirements

**Purpose:** what architecture must provide so NFR validation can be automated. Planning guidance only — final PASS/CONCERNS/FAIL belongs to `nfr-assess` once evidence exists.

| NFR Category                    | Threshold / Requirement                                                                                                       | Current Design Support                                                                     | Gap / Decision Needed                                                                                     | Planned Evidence                                            |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Security (NFR-05, AR-37)        | Zero secrets in repos, config, `.env`, CLI args, journals, evidence, fingerprints, logs; `SecretValue` never renders           | Supported — Skylos secrets 100 A+; typed `SecretRef`/`SecretValue` in core                  | None blocking                                                                                              | Skylos gate report + rendering property test                 |
| Performance (NFR-04, AR-22)     | Measure-then-budget at the 10/100/200 marks against the ~40-bot reference workload; qmf-core import under ~1s                 | Partial — `_bench.py` in every roster package; none in `qml`                                | **UNKNOWN thresholds**; no fingerprinted baselines; no recorded regression threshold (HIGH-4)              | Benchmark harness output per (OS, CPU-class)                 |
| Reliability / Determinism (NFR-03) | Same inputs ⇒ same fingerprints and same results; re-running a run id under its resolved config reproduces the CT-32 fp1 or refuses | Partial — `reproduce_generation` and door parity tests exist                                | No committed golden-run corpus; the CLI-only door gap (R-006) means one door is unverified (HIGH-5, B-3)   | Replay run comparing stored vs produced CT-32 fingerprints   |
| Data integrity (NFR-06, NFR-08) | Per-contract integer format versions; all history readable forever; every state change reconstructable                        | Partial — CT-22/CT-23 format-2 mints shipped with pre-mint format-1 readability tested       | No multi-version regression corpus of stored artifacts; journal gaplessness proven per-writer, not globally | Format-version corpus replay; journal gapless property test  |
| Maintainability (NFR-02)        | Coverage floor 80% per package; 100% branch on CT-01/CT-02 modules; three event-bound gate tiers; two tier-1 static scanners  | Partial — `cov-report` and the four scanners exist in `poe check`                            | **The executed gate ran ruff/pyright/pytest only** (BLOCKER B-1). `qml` clears the line floor by 0.8pp      | Full `poe check` + `poe check-integration` output            |
| Operability (NFR-10, AR-35)     | One-person deploy/monitor/repair; `correlation_id` across every package boundary; no-argument `health()` on resource owners   | Unknown — not surveyed by any existing gate                                                 | No census of which components actually expose `health()`; correlation propagation untested across seams     | Export-surface census test + correlation propagation test    |
| Failure discipline (NFR-11)     | Every designed failure mode ships a register entry written for someone who was not in the design room                         | Partial — registers in 6 of 10 units                                                        | Absent in `qmf-venue`, `qmf-risk`, `qml`, `qmf-calendar-forex`; `qmb` stops at FR-37 (HIGH-3)               | Register-vs-refusal reconciliation report                    |
| Concurrency (NFR-09, AR-17)     | QMF spawns no concurrency; async only at the venue edge; one-writer-per-stream with a held WriterId                           | Supported by design; `ambient-scan` would catch violations                                   | Scanner not in the executed gate (BLOCKER B-1)                                                             | `ambient-scan` output + writer-ownership acceptance tests    |

**Unknown thresholds — do not guess:**

- NFR-04 latency/throughput/memory at the 10/100/200 marks. Ratified as measure-then-budget; no numbers exist yet.
- AR-22's "regression beyond recorded threshold" — the threshold itself is not recorded anywhere in the tree.
- GAP-0048 (fidelity taxonomy) and GAP-0049 (robustness pass batteries) — deferred by ruling; SC-06/SC-07 bind the interfaces, not the numbers.
- CT-08 registration-gate thresholds and SR*/search-quality thresholds — deferred (SC-07).

**Assessment boundary:** this document plans NFR validation. It assigns no verdicts.

---

### Architecturally Significant Requirements (ASRs)

**ACTIONABLE** — QA cannot produce trustworthy evidence until these are resolved:

- **NFR-02** (tier-1 scanners in the gate) — BLOCKER B-1.
- **AR-58** (door parity, reproduce-or-refuse) — BLOCKER B-3.
- **AR-13 / CT-04** (value-or-typed-refusal at every boundary) — R-002; needs the convert-after-check rule to be testable as a law.
- **AR-19** (an executable contract test per CT-*, run by producer and every consumer at Tier 2) — R-015; consumer-side execution is not visible in the tree.
- **AR-22** (benchmark baselines and threshold) — R-014.
- **NFR-11** (failure registers) — R-009.

**FYI** — already well supported, no action:

- **AR-05/AR-06** (qmf-core stdlib-only; default-deny dependency direction) — `poe isolated-build` proves this mechanically.
- **AR-01..AR-04** (workspace shape, namespace packaging, 3.14 pin) — proven by the build.
- **SC-06 / SC-07** (GAP-0048/0049 deferrals) — these cap blast radius rather than create it, and the plan honours them by testing interfaces without inventing thresholds.

---

### Testability Concerns and Architectural Gaps

#### 1. Blockers to Trustworthy Evidence

| Concern                                   | Impact                                                                                             | What Architecture Must Provide                                                                   | Owner              | Timeline    |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ------------------ | ----------- |
| **Declared gate ≠ executed gate**         | FR-001/FR-002 are unenforced in practice; a live `ambient-scan` failure already exists              | One ratified gate command, or an explicit ruling that the scanners are advisory                    | Operator / factory | Phase entry |
| **Self-declaring door parity map**        | The one-door law (AR-58) is unverifiable; a whole epic shipped on one door with a green parity test | Parity derived from the door surfaces, or a completeness check over the map                        | QMB / Architecture | Fix lane    |
| **No golden-run corpus**                  | NFR-03 determinism cannot be checked against anything external                                      | A committed corpus of run ids + resolved-config fp1 + CT-32 fp1                                    | QMB                | Fix lane    |
| **No fingerprinted benchmark baselines**  | AR-22's Tier-2 regression gate is inert; performance regressions are invisible                      | Baseline files per (OS, CPU-class) and the recorded regression threshold                           | Architecture       | Fix lane    |
| **Optional dimension on shared primitives** | The money path can be entered without declaring currency or unit kind; three live instances       | Required, refusal-bearing `unit_kind`/`currency` on every shared numeric primitive                 | qmf-core / qmf-risk | Fix lane   |
| **Four packages with no failure register** | Designed refusals reach product users undocumented; QA has no list to test against                 | `FAILURES.md` for `qmf-venue`, `qmf-risk`, `qml`, `qmf-calendar-forex`; `qmb` completed past FR-37 | Package owners     | Fix lane    |

#### 2. Architectural Improvements Needed

1. **Convert-after-check at every conversion boundary**
   - **Current problem**: `float()` / ratio conversions execute before bounds validation, so `OverflowError` and `ValueError` escape as exceptions where CT-04 promises a refusal.
   - **Required change**: bound-and-`isfinite`-check first, convert second, at every named conversion boundary (AR-15).
   - **Impact if not fixed**: R-002 stays a per-site whack-a-mole; the "no public boundary raises" property test can never go green as a law.
   - **Owner**: every package owner. **Timeline**: fix lane.

2. **Identity completeness for fan-out artifacts**
   - **Current problem**: fingerprints omit distinguishing inputs (sweep combination shadowing, scenario index and anchor flag), so semantically distinct artifacts collide and one silently overwrites the other.
   - **Required change**: every fan-out artifact's identity content must include every input that distinguishes it; a duplicate-fp1 detection refusal at admission.
   - **Impact if not fixed**: sweeps and scenario fan-outs silently under-run while reporting a full pre-flight count.
   - **Owner**: qmf-core (fp1 discipline) + QMB. **Timeline**: fix lane.

3. **Governance gates applied at the schema, not at one input shape**
   - **Current problem**: refusals are implemented against the shape the author had in mind; a nested or aliased shape of the same config reaches the guarded path.
   - **Required change**: gates evaluate after normalization, and the normalizer is the single entry point.
   - **Impact if not fixed**: every governance gate in the system has an unknown number of bypass shapes.
   - **Owner**: QMB config compiler + Architecture. **Timeline**: fix lane.

4. **Failure-path ledger and journal cardinality**
   - **Current problem**: teardown and cancellation paths exit without minting the ledger line AR-51 requires.
   - **Required change**: the ledger write is a `finally`-class obligation of the orchestrator, not a happy-path step.
   - **Impact if not fixed**: experiment accounting is unreliable exactly when something went wrong — the case that matters most.
   - **Owner**: QMB orchestrator. **Timeline**: fix lane.

---

### Testability Assessment Summary

#### What Works Well

- **Machine oracles are already clean and should not be re-run by hand.** Skylos: security 100 A+, secrets 100 A+, AI-defects 100 A+, 0 dependency vulnerabilities, dead code 79 findings (75 unused parameters, 4 variables) at 0.4 per 1K LOC. Vulture: 4 high-confidence trivial findings. This plan spends no effort re-finding any of it.
- **The exact-value spine has strong existing nets.** `qmf-core` 99.65% line / 98.38% branch, with mutation testing already running on `exact.py` and `chrono.py`; `qmf-venue` 99.13% / 96.99%; `qmf-registry` 98.46% / 94.86%; `qmf-structure` 98.03% / 95.21%; `qmf-indicators` 97.44% / 94.17%.
- **The architecture is unusually testable by design**: injected clocks, no ambient concurrency below the venue edge, pure functions in `qml`, value-or-refusal returns, and deterministic fingerprints. Test isolation and parallel safety are nearly free, and fault injection needs no mocking framework — the seams are `typing.Protocol` ports.
- **Requirements are written as testable sentences.** 34 contract YAMLs, 12 prose golden scenarios, 39 constitution laws, and a decision ledger give this plan real, external oracles. Very few post-hoc verification efforts have this.
- **The advisory reviews already did honest work.** Epics 20–23 produced 8 HIGH findings that this plan treats as the empirical fault taxonomy rather than as isolated bugs.

#### Accepted Trade-offs (No Action Required)

- **Ubuntu tier-1 stays untested** until a GitHub remote exists (AR-23). Accepted; Windows 11 x86-64 is the verification platform for this phase.
- **GAP-0048/0049 thresholds stay deferred.** All fills are `optimistic`-tainted, `world=simulated` refuses, and no verdict-bearing backtest ships (SC-06). This caps the damage of R-018 and of every fidelity-related finding in epics 17 and 20–23 — which is why those epics sit in the lower tiers despite dense findings.
- **V1 sandbox enforcement is static AST/import scanning plus capability starvation and process isolation only** (AR-68). Hardened OS-level confinement is deferred and V1 must not wait on it; QA tests the static layer as shipped and does not treat the absence of confinement as a defect.
- **Coverage cannot rise much further by line-chasing.** The weak band is branch coverage in `qml` and `qmb`, and the answer is behaviour-driven tests against requirements, not more lines.

---

### Risk Mitigation Plans (Critical and High Risks)

#### R-001: Unit-kind / currency confusion on the money path (Score 9) — CRITICAL

**Mitigation Strategy:**

1. Census every shared numeric primitive that accepts or produces a money, price, quantity or return value, and record for each whether `unit_kind` and `currency` are required, defaulted, or absent.
2. Make both required and refusal-bearing wherever the value can reach the money path (HIGH-1).
3. Author hypothesis properties over the full unit-kind × currency cross-product: mixing dimensions must refuse; matching dimensions must round-trip exactly.
4. Add `qmf-risk` sizing and `qmf-core` exact modules to the mutation roster so an unasserted dimension check surfaces as a surviving mutant.

**Owner:** qmf-core / qmf-risk owners **Timeline:** before any fix lane opens
**Status:** Planned **Verification:** the property suite is red on today's tree at the three known sites and green after the fix, with no site-specific test.

#### R-002: Typed-refusal envelope breached (Score 9) — CRITICAL

**Mitigation Strategy:**

1. Enumerate every public callable across all ten distribution units from the export surface, not from a hand list.
2. Author one universal property: for all generated inputs within the declared type, the callable returns a value or a typed refusal and never raises. Exceptions are permitted only where the contract names programmer error.
3. Adopt the convert-after-check ordering rule as an AR-13 addendum (HIGH-2).
4. Record every failing callable in the findings inventory. Do not fix.

**Owner:** all package owners **Timeline:** before any fix lane opens
**Status:** Planned **Verification:** the universal property enumerates ≥95% of the public surface and the four known sites appear in its first run.

#### R-003: Author-authored tests ratify contradictions (Score 9) — CRITICAL

**Mitigation Strategy:**

1. Isolate `qa/` structurally: own branch, own pytest configuration, no import from any package `tests/` (BLOCKER B-2).
2. Author every test from requirement text before reading any implementation body.
3. For each epic, audit the existing tests that claim its requirements and classify each: keep / suspect / contradicts-the-requirement.
4. Run one requirements-fidelity review seat per epic — one seat, not a panel — checking that each AC has a test asserting the AC rather than the code.
5. Extend mutation testing beyond `qmf-core` to the money and governance modules; surviving mutants are the mechanical adversary.

**Owner:** QA **Timeline:** this phase
**Status:** Planned **Verification:** every epic produces an existing-test audit table, and every "contradicts" row lands in the findings inventory with the requirement id it contradicts.

#### R-004 / R-008 / R-010: Identity collision, gate bypass, ledger loss (Score 6) — HIGH

**Mitigation Strategy:**

1. Treat all three as one family: obligations that hold on the happy path and lapse on the alternate path.
2. Author generated-input tests rather than example tests — input shapes generated from the config schema, fan-out inputs generated to force collisions, failure paths driven by fault injection at the port seams.
3. Assert cardinality and identity explicitly: distinct inputs ⇒ distinct fingerprints; every run ⇒ exactly one ledger line; every accepted input shape ⇒ the same gate verdict.

**Owner:** QMB + qmf-core **Timeline:** fix lane
**Status:** Planned **Verification:** each of the four evidenced instances is reproduced by a test that names no site-specific detail.

#### R-005 / R-009 / R-014 / R-016: Gate, register, baseline and corpus gaps (Score 6/4) — HIGH

**Mitigation Strategy:**

1. Run the full `poe check` and `poe check-integration` sequences once on `integration@2c8d495` in a qa worktree and capture the output as the L0 baseline. This is the first action of the phase and costs nothing to author.
2. Reconcile every typed refusal reachable from a door against the failure registers; the delta is a fix-card cluster, not a test failure.
3. Record the AR-22 threshold and commit baselines, or record AR-22 as deferred.
4. Commit the golden-run corpus so determinism has an external referent.

**Owner:** Operator / factory / package owners **Timeline:** phase entry (1) then fix lane (2–4)
**Status:** Planned **Verification:** the L0 baseline output is an artifact in the findings inventory; the register delta is a numbered list.

#### R-006 / R-012: Parity blindness and boundary-incomplete governance (Score 6) — HIGH

**Mitigation Strategy:**

1. Enumerate surfaces rather than sampling them: every door's exported callables, every read path into `qmf-data`.
2. Assert the requirement across the whole enumeration — the same capability on every door, the same seal/split/world refusal on every read path.
3. Where an enumeration cannot be derived mechanically, the finding is the missing derivation, not the missing test.

**Owner:** QMB / qmf-data **Timeline:** fix lane
**Status:** Planned **Verification:** the parity and boundary tests fail on today's tree at the known sites and are written without naming them.

#### R-007 / R-011: Corrupt input accepted, weak-band behaviour unseen (Score 6) — HIGH

**Mitigation Strategy:**

1. Per intake seam, author adversarial-input acceptance tests from the CT-10/CT-15 contract text: mismatched scale, out-of-range revision keys, non-monotonic timestamps, mixed instruments.
2. Tier the epic fan-out by the coverage-weak band (see the QA document's ranked list) so `qml` and `qmb` receive the deepest independent suites.
3. Target uncovered branches by behaviour — pick the requirement the branch serves and test that — never by chasing the line number.

**Owner:** qmf-data / QMB / QA **Timeline:** this phase
**Status:** Planned **Verification:** branch coverage in `qml` and `qmb` rises as a by-product; the primary evidence is the proof map, not the percentage.

---

### Assumptions and Dependencies

#### Assumptions

1. `integration@2c8d495` is the tree under verification and does not move during the phase; if it moves, the L0 baseline is re-run.
2. `epics.md` and the ratified `docs/` corpus are the requirements of record. Where code and requirement disagree, the requirement is right and the code is the finding.
3. The four advisory-review reports available (epics 20–23) are representative of the fault families present in epics 1–19. This is an assumption, not a fact — no build reports exist for epics 1–19, so likelihood scoring for those epics rests on coverage, complexity and finding density alone.
4. GAP-0048 and GAP-0049 remain unruled for the duration of this phase, so no fidelity or robustness threshold is testable and none will be invented.
5. Money is not live on this code during the phase; every finding is a backlog item, not an incident.
6. `world=simulated` continues to refuse and all fills remain `optimistic`-tainted (SC-06), capping the damage of every fidelity-related finding.

#### Dependencies

1. Three BLOCKER decisions (B-1 gate reconciliation, B-2 `qa/` isolation ruling, B-3 parity derivation) — required before the epic fan-out starts.
2. `hypothesis` added to a qa-only dependency group, and the `mutmut` roster extended beyond `qmf-core` — required before T1 authoring.
3. Isolated qa worktrees cut from `integration` — required at phase entry; nothing runs in the main worktree and nothing touches `QMX-worktrees` build trees.
4. The requirement-id extraction (FR/NFR/AR from `epics.md`; CT from `docs/contracts/`; SCN from `docs/scenarios/`; L* from `docs/constitution.md`) — required before the traceability markers can be validated.

#### Risks to the Plan Itself

- **Risk**: The fan-out authors read implementation code before writing test lists and reproduce the original blind spot.
  - **Impact**: The independent suite becomes a second copy of the existing suite and the phase produces false confidence — worse than doing nothing.
  - **Contingency**: The per-epic template orders the steps so the test list is written before any `src/` read, and the requirements-fidelity seat checks for implementation-shaped assertions.
- **Risk**: The findings inventory grows large enough that the operator cannot triage it.
  - **Impact**: The phase ends without a decision.
  - **Contingency**: Findings are clustered into fix cards by fault family, not filed individually; the inventory is ordered by risk id, and the proof map — not the finding count — is the headline artifact.
- **Risk**: A T1 epic turns out to need more work than its tier budgeted, starving the lower tiers.
  - **Impact**: Uneven proof coverage that looks complete.
  - **Contingency**: The proof map marks unreached requirements UNPROVEN rather than leaving them blank; an unproven requirement is a reported outcome, not a gap in the report.

---

**End of Architecture Document**

**Next Steps for Architecture Team:**

1. Resolve the three BLOCKERS (B-1 gate reconciliation, B-2 `qa/` isolation, B-3 parity derivation).
2. Review and approve the five HIGH-priority recommendations.
3. Assign owners for the twelve risks scoring ≥6.
4. Confirm or correct assumption 3 — whether epics 1–19 carry build reports this design has not seen.

**Next Steps for QA:**

1. Run the L0 baseline sweep (`poe check`, `poe check-integration`) in an isolated qa worktree.
2. Stand up the `qa/` tree and the traceability plumbing per the companion QA document.
3. Begin the T1 epic fan-out.
