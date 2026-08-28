---
runScope: 'system-level'
runKey: 'system'
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
---

# Test Design Progress — QMX system-level run (runKey: `system`)

Workflow: `bmad-testarch-test-design` v5.0, create mode, headless.
Operator: Mubarak. Language: English. All in-workflow decisions delegated to the orchestrator and resolved from the run prompt; no interactive prompts were raised.

---

## Step 1 — Detect Mode & Prerequisites

**Mode:** System-Level. Chosen by explicit user intent (the run prompt names a SYSTEM-level run) and confirmed by file-based detection: no `sprint-status.yaml` exists, and PRD + architecture spines + a ratified `docs/` corpus are all present.

**Run identity:** `run_scope = system-level`, `run_key = system`. Checkpoint path `_bmad-output/test-artifacts/test-design-progress-system.md`.

**Existing checkpoint:** none — `_bmad-output/test-artifacts/` was empty. Fresh run; nothing merged from a prior run.

**Prerequisites:**

| Requirement                     | Status  | Source                                                                              |
| ------------------------------- | ------- | ------------------------------------------------------------------------------------- |
| PRD with FRs + NFRs             | Present | `_bmad-output/planning-artifacts/prds/prd-QMX-2026-08-21/prd.md` (final)              |
| ADRs                            | Present | `docs/decisions/ADR-0001..ADR-0018`                                                   |
| Architecture / tech-spec        | Present | Three ratified spines (QMX 2026-08-19, QMB 2026-08-20, QML 2026-08-21)                |
| Epics for scope                 | Present | `_bmad-output/planning-artifacts/epics.md` — 23 epics, 131 stories, validated         |
| Requirements testable           | Yes     | 50 FRs, 11 NFRs, 69 ARs, 34 CT contracts, 12 golden scenarios, 39 constitution laws   |

**Customization:** `uv run _bmad/scripts/resolve_customization.py --skill .claude/skills/bmad-testarch-test-design --key workflow` succeeded and returned empty `activation_steps_prepend`, `activation_steps_append`, `persistent_facts` and `on_complete`. No overrides to apply; no on-complete hook to run.

---

## Step 2 — Load Context & Knowledge Base

**Config resolved** from `_bmad/tea/config.yaml`: `test_artifacts = {project-root}/_bmad-output/test-artifacts`, `user_name = Mubarak`, `communication_language = English`, `document_output_language = English`, `project_name = QMX`, `risk_threshold = p1`, `tea_execution_mode = auto`, `tea_capability_probe = true`.

**Stack detection:** `test_stack_type = auto` → **backend**. Evidence: `pyproject.toml` at the workspace root and in every member; no `playwright.config.*`, no `cypress.config.*`, no `package.json`, no mobile indicators anywhere in the tree.

**Tooling flags — deviation recorded.** `tea_use_playwright_utils: true`, `tea_use_pactjs_utils: true` and `tea_pact_mcp: mcp` are all set, and none applies:

- **Playwright** — no browser surface exists. V1 has no UI (PRD: terminal is Phase 3; Simulator UI deferred by ADR-0011; QMB chart output is data per FR-043). No Playwright fragments loaded; no Playwright example appears in any output document.
- **Pact / contract broker** — the relevance gate in `pactjs-utils-mandate.md` is not met: no `pact/` or `tests/contract/` directory, no `.pacttest.ts`, no `@pact-foundation/pact`, no `PACT_BROKER_*`, and no HTTP provider/consumer split. QMX is a single-process uv workspace of importable libraries. `contract-testing.md` conventions inform the L2 level design; no Pact artifact is planned.
- **Pact MCP probe** — not performed. `pact_mcp_reachable = not-applicable` (no consumer/provider relationship exists to probe). Reported once here; the run continued without blocking.
- **Browser exploration** — skipped (system-level mode does not call for it, and there is no target URL). No CLI sessions opened, so none to clean up.

The Python equivalents carry these roles: `pytest` (all authored levels), `hypothesis` (properties), `mutmut` (mutation), `poe check` scanners and Skylos (static/L0).

**Project artifacts loaded:**

- `_bmad-output/planning-artifacts/epics.md` — requirements inventory (FR-001..050, NFR-01..11, AR-01..69, SC-01..12, FR coverage map, 23-epic list with waves and weight tags).
- `docs/contracts/` — CT-01..CT-34 YAML.
- `docs/scenarios/` — SCN-0001..SCN-0012.
- `docs/decisions/` — ADR-0001..0018; `docs/constitution.md`; `docs/components/`; `conventions/failure-register.md`.
- Per-epic build reports: `QMX-worktrees/epic-{020,021,022,023}-*-report.md`. **Evidence gap recorded:** no build reports exist for epics 1–19, so likelihood scoring for those epics rests on coverage, complexity and package finding-density alone.

**Existing coverage analysed** (integration@2c8d495; battery summaries):

- Suite: 3899 passed, 0 failed, 86.97% line / 75.01% branch.
- Package band: `qml` 80.8/66.0, `qmb` 83.2/66.5, `qmf-risk` 91.4/82.2, `qmf-data` 92.2/82.5, `qmf-calendar-forex` 94.8/75.8, `qmf-indicators` 97.4/94.2, `qmf-structure` 98.0/95.2, `qmf-registry` 98.5/94.9, `qmf-venue` 99.1/97.0, `qmf-core` 99.7/98.4.
- Worst files: `qml footprint/_coerce.py` 58.3/48.8, `qmb orchestrator/spawn.py` 59.8/50.8, `qmb data/verify.py` 59.9/47.1, `qml host/runner.py` 61.4/50.0, `qmb data/gap_check.py` 62.8/50.0, `qmf-data cycle.py` 63.3/44.3, `qmb orchestrator/watch.py` 64.3/37.0.
- Skylos: 650 files, 200,886 LOC; security/secrets/AI-defects/dependencies all 100 A+; dead code 79 (75 unused params, 4 vars) = A+; quality 4084 (25 CRITICAL, 361 HIGH) = F, all complexity/style families; overall 77 C+.
- Skylos package concentration: `qmb` 1926, `qml` 564, `qmf-risk` 455, `qmf-data` 406, `qmf-indicators` 177.
- Vulture at 100% confidence: 4 trivial findings.
- Mutation: `mutmut` running on `qmf-core` `exact.py` / `chrono.py` only.

**Tree structure observed** (integration): 7 roster packages + 1 extension + `qml` + `qmb`; per-package `tests/`, `examples/` and `_bench.py`; `poe` surface with `check` / `check-integration` / `check-release` and four tier-1 static scanners.

**Knowledge fragments loaded** (system-level required set): `risk-governance.md`, `probability-impact.md`, `test-levels-framework.md`, `test-priorities-matrix.md`, `nfr-criteria.md`, `test-quality.md`, `adr-quality-readiness-checklist.md`. Extended/specialized tiers not loaded — no browser, mobile, webhook, email, Pact or visual-debugging surface in scope.

---

## Step 3 — Testability & Risk Assessment

**Testability review produced** (full text in `test-design-architecture.md`):

- Six actionable concerns, three of which are BLOCKERS: the declared gate differs from the executed gate (the four tier-1 static scanners never ran in the factory's per-story gate, and a live `ambient-scan` failure is on record at `qmb/src/qmb/data/download.py:127`); door parity rests on a hand-maintained map that shipped stale; the `qa/` tree needs a structural isolation ruling.
- Four architectural improvements: convert-after-check ordering at conversion boundaries; identity completeness for fan-out artifacts; governance gates applied after normalization; ledger writes as a `finally`-class obligation.
- Strengths recorded: injected clocks, no ambient concurrency, pure `qml`, value-or-refusal returns, deterministic fingerprints, and an unusually strong external oracle set (34 contract YAMLs, 12 prose scenarios, 39 laws).

**ASRs:** six ACTIONABLE (NFR-02, AR-58, AR-13/CT-04, AR-19, AR-22, NFR-11); three FYI (AR-05/AR-06, AR-01..04, SC-06/SC-07).

**Risk register: 21 risks** — 3 critical (score 9), 9 high (6), 6 medium (3–4), 3 low (1–2). Categories: DATA 7, TECH 7, OPS 5, PERF 2, BUS 2, SEC 1. Every risk is evidence-backed by an advisory finding, a coverage number, a complexity finding or an observed tree fact; none is speculative.

Critical: R-001 unit-kind/currency confusion on the money path (three confirmed live instances); R-002 typed-refusal envelope breached (four confirmed entry points raise); R-003 author-authored tests ratify contradictions (confirmed verbatim in the epic-23 review).

**NFR planning:** nine categories in scope. Thresholds extracted where ratified; four marked **UNKNOWN and not guessed** — NFR-04's 10/100/200-mark numbers, AR-22's regression threshold, GAP-0048/GAP-0049 batteries, CT-08 and SR*/search thresholds. Each became a risk or a DEFERRED proof-map row rather than an invented value.

---

## Step 4 — Coverage Plan & Execution Strategy

**Test-level architecture:** six levels, each with a named oracle that is never the implementation — L0 machine sweeps (the tool), L1 properties (a contract-stated invariant, via `hypothesis`), L2 contract tests (the CT-* YAML), L3 acceptance tests (the `epics.md` AC sentence), L4 scenario tests (the SCN-* walkthrough), L5 mutation (`mutmut`, surviving mutants), L6 one requirements-fidelity review seat per epic. Duplicate-coverage guard: a behaviour is asserted at exactly one level, and when two levels want it the lower one keeps it.

**Coverage matrix:** ~380–520 scenarios — P0 ~55–75, P1 ~160–210, P2 ~130–180, P3 ~35–55, each row linked to a requirement id and a risk id. P0 at ~14% exceeds the usual <10% guidance; the deviation is stated and justified in the QA document rather than hidden.

**Epic tiering:** 23 epics ranked by likelihood × damage into T1 (7), T2 (8), T3 (7), T4 (1), each with a one-line evidence-backed justification. Two evidence-driven departures from the foundational-first instinct are flagged: E13/E14 promoted into T1, E18 promoted to T2.

**Execution strategy:** push / nightly / weekly. Push = the full `qa/` suite under `pytest -n auto` (<15 min). Nightly = mutation, deep property budgets, full `poe check` + `check-integration`, benchmarks. Weekly = determinism replay, full restore rehearsal, flake burn-in.

**Estimates** given as ranges only: P0 ~2.5–4.5 weeks, P1 ~2.5–4.5 weeks, P2 ~1.5–2.5 weeks, P3 ~0.5–1 week; total ~7–12 weeks for one engineer or ~4–7 weeks across parallel lanes.

**Quality gates** defined for the suite itself (P0 100% authored and executed, P1 ≥95%, every P0/P1 requirement carrying a non-blank proof-map row, every test carrying a resolvable requirement id). The product's verdict is the proof map, not a pass rate.

---

## Step 5 — Generate Outputs & Validate

**Execution mode resolved:** `sequential`. `tea_execution_mode` is `auto` and `tea_capability_probe` is true, but the run prompt forbids spawning subagents, so agent-team and subagent capability both resolve false. Single-context synthesis throughout.

**Outputs written:**

| Document                | Path                                                          | Template                                |
| ----------------------- | ------------------------------------------------------------- | ----------------------------------------- |
| Architecture test design | `_bmad-output/test-artifacts/test-design-architecture.md`      | `test-design-architecture-template.md`    |
| QA test design           | `_bmad-output/test-artifacts/test-design-qa.md`                | `test-design-qa-template.md`              |
| BMAD handoff             | `_bmad-output/test-artifacts/test-design/QMX-handoff.md`       | `test-design-handoff-template.md`         |
| Progress checkpoint      | `_bmad-output/test-artifacts/test-design-progress-system.md`   | (this file)                               |

**Validation against `checklist.md`:** all prerequisites, process steps, output validations, quality checks and integration points reviewed. Notable results:

- Risk matrix: unique ids R-001..R-021, categories assigned, probability and impact each 1–3, scores arithmetically correct, ≥6 marked, mitigations specific with owners and timelines.
- Estimates: intervals only, no exact totals, no `N tests × M hours` arithmetic anywhere.
- Execution strategy: simple push/nightly/weekly, no smoke/P0/P1 tier structure, no re-listing of tests.
- Priority sections carry criteria only, with the "priority ≠ execution timing" note at the top of the coverage plan.
- Architecture doc: no test code, no quality-gate criteria, no tool-selection section, no test-levels-strategy section, no environment section — all correctly in the QA doc. Actionable-first ordering honoured (Quick Guide → risks → concerns → mitigations, then FYI sections).
- Cross-document consistency: shared risk ids, shared priority levels, shared blockers, same date and author, PRD and ADR references identical.
- Handoff: artifacts inventory populated with real paths; epic guidance built from the register; risk-to-story map complete for all 21 risks.
- Temp artifacts: none written outside `{test_artifacts}`. No browser sessions opened, so none orphaned.

**Deviations from the checklist, recorded deliberately:**

1. **Playwright and Pact items marked N/A.** The checklist assumes a JS/browser stack (`playwright-utils` fixtures in code examples, `k6` for performance, Pact provider verification). QMX is a pure-Python library workspace with no browser and no service boundary. Python equivalents are used and the substitution is stated in both documents.
2. **P0 share is ~14%, above the <10% guidance.** Stated with its reason rather than trimmed to fit: money-path and governance-gate requirements are an unusually large fraction of this system's surface, and neither has a workaround.
3. **Two risks scored 9 alongside a third.** The checklist warns against uniformly high scores; these three are each backed by multiple independently-confirmed live instances, and the register below them differentiates properly (9 at score 6, 6 at 3–4, 3 at 1–2).
4. **The handoff document's downstream consumer is inverted.** Epics and stories already exist and are built, so the handoff feeds the verification phase and the fix-card backlog rather than `create-epics-and-stories`. The inversion is stated at the top of that document.

**Open assumptions carried forward:**

- `integration@2c8d495` is the tree under verification and does not move; if it moves, the L0 baseline is re-run.
- Advisory findings from epics 20–23 are representative of the fault families in epics 1–19. No build reports exist for epics 1–19 to confirm this.
- GAP-0048 and GAP-0049 remain unruled for the phase; every dependent requirement stays DEFERRED.
- Money is not live during the phase.

**Workflow status: completed.** No `on_complete` hook configured; the run exits normally.
