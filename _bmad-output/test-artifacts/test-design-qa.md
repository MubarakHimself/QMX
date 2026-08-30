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
  - docs/contracts/ (CT-01..CT-34)
  - docs/scenarios/ (SCN-0001..SCN-0012)
  - docs/constitution.md, docs/decisions/, conventions/failure-register.md
  - QMX-worktrees/epic-{020,021,022,023}-*-report.md
  - battery/{skylos,coverage,vulture}/
---

# Test Design for QA: QMX V1 — Independent Verification Programme

**Purpose:** The execution recipe. What gets tested, at which level, judged by which oracle, in what order, and what "done" means for this phase.

**Date:** 2026-08-27
**Author:** Master Test Architect (TEA), for Mubarak
**Status:** Draft
**Project:** QMX

**Related:** `test-design-architecture.md` — testability concerns, the full risk register, and the three blockers Architecture must resolve. Risk ids (R-001…R-021) are shared between the two documents and defined there.

---

## Executive Summary

**Scope:** Independent verification of all 23 epics / 131 stories as merged on `integration@2c8d495`, authored from requirements rather than from code.

**The premise this plan is built on.** The machines have already done their part and done it well: Skylos reports security, secrets, AI-defects and dependencies all at 100/A+, dead code at 0.4 findings per 1K LOC, and Vulture finds four trivial things. The suite is large and green — 3899 passed, 0 failed, 86.97% line / 75.01% branch. None of that is evidence of correctness against requirements, because every one of those tests was written by the agent that wrote the code it tests. Epic 23's advisory review states the consequence plainly: two claim-class gates disagree with each other and *"both behaviors are test-pinned, so the suite ratifies the contradiction."*

So this plan does not re-find what machines already found. It builds the one thing no machine and no author-written test can supply: an **independent oracle** — tests written from `epics.md`, the CT-* contracts, the SCN-* scenarios and the constitution, by an author who has not read the implementation.

**Risk Summary:**

- Total risks: 21 (3 critical score 9, 9 high score 6, 6 medium, 3 low)
- Critical categories: DATA (money-path dimension confusion, identity collision, silent corruption) and TECH (typed-refusal breach, oracle dependence)

**Coverage Summary:**

- P0 tests: ~55–75 (money path, governance gates, identity, seals)
- P1 tests: ~160–210 (contract conformance, run-loop correctness, doors, ledger)
- P2 tests: ~130–180 (edge cases, regression pins for the 8 evidenced HIGH findings)
- P3 tests: ~35–55 (exploratory, benchmarks, register reconciliation)
- **Total**: ~380–520 tests (~7–12 weeks for one engineer; ~4–7 weeks across parallel factory lanes)

P0 at roughly 14% of the total exceeds the usual <10% guidance. This is deliberate and stated so it can be challenged: in a system whose stated purpose is to gate money, the money path and the governance gates are an unusually large fraction of the total surface, and no workaround exists for either.

---

## Not in Scope

| Item                                                              | Reasoning                                                                                                                              | Mitigation                                                                                             |
| ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| **Security scanning, secret detection, CVE checks, AI-defect scan** | Skylos already reports 100/A+ on all four categories with 0 dependency vulnerabilities. Re-running by hand adds cost and no information. | Skylos CI gate output is consumed as L0 evidence; one `SecretValue` rendering property test covers AR-37's rendering claim only. |
| **Dead-code hunting**                                             | Skylos: 79 findings, of which 75 are unused parameters and 4 unused variables. Vulture at 100% confidence: 4 trivial findings.          | Folded into the fix-card backlog as a single low-priority cleanup cluster.                                |
| **Style and complexity remediation** (4084 quality findings)       | These are machine-found and machine-fixable; they are not behavioural defects. Testing them again proves nothing.                        | Complexity findings are used as *likelihood evidence* for risk scoring, not as test targets.               |
| **Any code change, fix, merge or deletion**                       | Operator ruling: zero fixes until a consolidated findings inventory reaches the operator.                                                | Every finding becomes a lane-agnostic fix card. The phase produces a backlog, not a diff.                 |
| **GAP-0048 / GAP-0049 threshold validation**                       | Deferred by ruling (SC-06/SC-07). Fidelity taxonomy, robustness pass batteries, CT-08 registration-gate and SR*/search thresholds are unruled. | Interfaces are tested; thresholds are marked DEFERRED in the proof map. No number is invented.        |
| **Ubuntu tier-1 platform verification**                            | AR-23: Ubuntu stays untested until a GitHub remote exists.                                                                              | Windows 11 x86-64 is the verification platform; the gap is recorded in the proof map as DEFERRED.          |
| **Live venue interaction with cTrader**                            | No credentials or live account are in scope for a verification phase, and a real order is a real order.                                  | The venue port is verified against the CT-18..CT-21 contracts and recorded venue facts (DEC-0135/0139/0141) at the port seam. |
| **UI / browser / contract-broker testing**                         | V1 has no UI surface (PRD: terminal is Phase 3, Simulator UI deferred by ADR-0011) and no HTTP microservice boundary.                    | See the tooling deviation note below.                                                                      |

**Tooling deviation, recorded deliberately.** `_bmad/tea/config.yaml` sets `tea_use_playwright_utils: true`, `tea_use_pactjs_utils: true` and `tea_pact_mcp: mcp`. None applies here: the detected stack is `backend` (Python, uv workspace, `pyproject.toml`), there is no browser surface anywhere in V1, and there are no Pact artifacts, no HTTP provider/consumer split and no broker. Per the pactjs mandate's own relevance gate — the flag defaults to true and never means "add contract tests to this project" — Playwright and Pact are out of scope and no example in this document uses them. The Python equivalents are `pytest`, `hypothesis` and `mutmut`. Where this document's parent template says "Playwright", read "pytest".

---

## Dependencies & Test Blockers

**QA cannot produce trustworthy evidence without these.**

### Architecture / Operator Dependencies (Phase Entry)

**Source:** `test-design-architecture.md` Quick Guide, blockers B-1..B-3.

1. **B-1 — Reconcile the declared gate with the executed gate** — Operator + factory — phase entry
   - What QA needs: a ruling on whether `money-path-scan`, `ambient-scan`, `mock-data-scan`, `secret-scan`, `cov-report` and `test-tools` are part of the gate.
   - Why it blocks: FR-001 and FR-002 are designed to be *mechanically* enforced. If the enforcement never ran, QA is testing a law nobody applied, and a live `ambient-scan` failure at `qmb/src/qmb/data/download.py:127` is already on record.

2. **B-2 — Rule that `qa/` is structurally isolated** — Operator + Architecture — phase entry
   - What QA needs: `qa/` on its own branch, with its own pytest configuration, forbidden from importing any package's `tests/`, conftest or fixtures.
   - Why it blocks: without the ruling, the fan-out will reuse existing factories and inherit the exact blind spot this phase exists to break (R-003).

3. **B-3 — Decide how door parity is derived** — QMB / Architecture — before the Epic 16 lane
   - What QA needs: parity enumerated from the door surfaces, or a completeness check over `doors/parity.py`.
   - Why it blocks: a parity test written against a hand-maintained map tests the map, not the platform (R-006, evidenced by E23-H1).

### QA Infrastructure Setup (Phase Entry)

1. **Isolated qa worktrees** — QA
   - Branch `qa/independent-tests` cut from `integration@2c8d495`. One worktree per concurrent epic lane. Nothing runs in the main worktree; nothing touches the existing `QMX-worktrees/` build trees.

2. **Dependency group** — QA
   - A qa-only group adding `hypothesis` (not currently a workspace dependency) and extending the `mutmut` configuration. Nothing is added to `dev`, `scan`, or any package's own `pyproject.toml` — the shipped dependency surface (AR-07, DEPENDENCIES.md) does not change for a test phase.

3. **The `qa/` tree** — QA

```text
qa/
  pyproject.toml            # qa-only deps + its own [tool.pytest.ini_options]; never inherits the shipped conftest
  conftest.py               # the req() marker, the trace collector, the no-implementation-import guard
  _oracles/
    requirements.py         # parses FR/NFR/AR ids + AC text out of epics.md
    contracts.py            # loads docs/contracts/ct-NN-*.yaml
    scenarios.py            # loads docs/scenarios/SCN-*.md
    laws.py                 # loads docs/constitution.md L1..L39
  properties/               # L1 - hypothesis
    test_money_algebra.py
    test_no_boundary_raises.py
    test_fp1_identity.py
    test_causality.py
  contracts/                # L2 - one module per CT-*, parameterized over every implementer and consumer
    test_ct01_money_quantity.py ... test_ct34_confluence.py
  epics/                    # L3 - mirrors the epic structure
    epic_01_qmf_core/
      PLAN.md               # the per-epic test plan (template below)
      test_fr001_exact_values.py
      ...
    epic_10_qmf_risk/ ... epic_23_qmb_synthetic_data/
  scenarios/                # L4 - one module per golden scenario
    test_scn_0001_core_freeze_gate.py ... test_scn_0012_qmb_replay_run.py
  mutation/
    roster.toml             # the justified module list; see "Mutation targets"
  _trace/
    trace.yaml              # generated from markers
    proof_map.md            # generated; the phase's headline artifact
    findings.csv            # the findings inventory
```

**Independence rules, enforced not just stated:**

- `qa/conftest.py` fails collection for any module that imports from a package's `tests/`.
- Every test carries `@pytest.mark.req(...)`; a test with no requirement id fails collection.
- The authoring order in the per-epic template puts the test list before any `src/` read. Reading a public signature in order to call it is allowed; reading the implementation body before the list is written is not.

**Test authoring pattern** (the shape every independent test takes — oracle first, call second):

```python
import pytest
from hypothesis import given, strategies as st

from qa._oracles.contracts import load_contract
from qmf.core import exact


@pytest.mark.req("FR-001", "CT-01", "AR-15")
@given(
    scale=st.integers(min_value=0, max_value=9),
    raw=st.integers(min_value=-(10**18), max_value=10**18),
)
def test_ct01_money_round_trips_exactly_at_every_declared_scale(scale: int, raw: int) -> None:
    """CT-01: a Money value is a scaled integer at a declared scale.

    Oracle: docs/contracts/ct-01-money-quantity.yaml, not the implementation.
    """
    contract = load_contract("ct-01")
    assert scale in contract["declared_scales"], "test's own premise must come from the contract"

    result = exact.Money.try_create(raw, scale=scale, currency="USD")

    assert result.is_ok(), f"CT-01 requires construction to succeed at declared scale {scale}"
    assert result.value.raw == raw, "no float ever touches the money path"
    assert result.value.scale == scale
```

---

## Risk Assessment

**Full detail in `test-design-architecture.md`.** This section maps risks to the QA work that validates them.

### Critical Risks (Score 9)

| Risk ID   | Category | Description                                         | Score | QA Test Coverage                                                                                                     |
| --------- | -------- | --------------------------------------------------- | ----- | -------------------------------------------------------------------------------------------------------------------- |
| **R-001** | DATA     | Unit-kind / currency confusion on the money path    | **9** | L1 property over the unit-kind × currency cross-product; L5 mutation on `qmf-risk` sizing and `qmf-core` exact modules |
| **R-002** | TECH     | Typed-refusal envelope breached (boundaries raise)  | **9** | L1 universal property: no public callable raises, enumerated from the export surface                                  |
| **R-003** | TECH     | Author-authored tests ratify contradictions         | **9** | The whole programme; per-epic existing-test audit; one requirements-fidelity seat per epic; L5 mutation               |

### High-Priority Risks (Score 6)

| Risk ID | Category | Description                                          | Score | QA Test Coverage                                                                       |
| ------- | -------- | ---------------------------------------------------- | ----- | ---------------------------------------------------------------------------------------- |
| R-004   | DATA     | fp1 identity collisions drop/conflate artifacts      | 6     | L1 identity-completeness property per artifact kind; L3 fan-out collision tests (E20, E23) |
| R-005   | OPS      | Tier-1 static scanners never in the executed gate    | 6     | L0 baseline sweep — first action of the phase                                             |
| R-006   | BUS      | Door parity blind to single-door capabilities        | 6     | L3 surface-derived parity test (E16), enumerating every door's exports                     |
| R-007   | DATA     | Corrupt input silently accepted (scale, clamp)       | 6     | L3 adversarial-input tests per intake seam (E3, E6, E18, E23)                              |
| R-008   | TECH     | Governance gate bypassed by an alternate input shape | 6     | L3 gate tests over every accepted shape, generated from the config schema (E13, E23)       |
| R-009   | OPS      | Failure registers absent or incomplete               | 6     | L3 register-vs-refusal reconciliation per package (P3 effort, high information)            |
| R-010   | DATA     | Ledger cardinality breaks on failure paths           | 6     | L3 fault-injection matrix over abort/teardown/cancel (E15, E20, E21)                       |
| R-011   | TECH     | Coverage-weak band conceals behaviour (qml, qmb)     | 6     | Tiering of the epic fan-out; branch-targeted acceptance tests                              |
| R-012   | DATA     | Seal/split/world governance proven at one boundary   | 6     | L3 boundary census: every read path into `qmf-data` asserts the refusal (E3)                |

### Medium / Low Risks

| Risk ID | Category | Description                                       | Score | QA Test Coverage                                                          |
| ------- | -------- | ------------------------------------------------- | ----- | --------------------------------------------------------------------------- |
| R-013   | PERF     | Invented figures substitute for measurement       | 4     | L3: an unmeasurable estimate must refuse, not default (E21)                  |
| R-014   | OPS      | No fingerprinted benchmark baselines; no qml bench | 4     | L0 nightly benchmark run; finding, not a test failure                       |
| R-015   | TECH     | AR-19 contract-test completeness unproven         | 4     | L2 — one independent module per CT-*, which settles the question directly    |
| R-016   | TECH     | No golden corpus for determinism                  | 4     | L4 weekly replay once the corpus exists; until then a recorded UNPROVEN row  |
| R-017   | PERF     | Concurrency/backpressure on the worst-covered code | 4     | L3 orchestrator fault-injection matrix (E15)                                 |
| R-018   | BUS      | Look-ahead safety rests on author tests           | 4     | L1 causality property; capped by SC-06                                       |
| R-019   | SEC      | Secret rendering paths                            | 2     | One L1 property; no re-scanning                                             |
| R-020   | OPS      | Packaging integrity at Tier 2                     | 2     | L0 `poe check-integration`                                                  |
| R-021   | OPS      | Known concurrent-I/O flake class                  | 2     | Quarantine list + burn-in on the qa branch; no fixes                        |

---

## Test Levels and Their Oracles

**The rule that makes this plan different: every level names the thing that decides whether the test passed, and none of them is the implementation.**

| Level  | Name                          | Oracle (what judges it)                                                         | What it proves                                                                | What it must not be used for                          |
| ------ | ----------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------ |
| **L0** | Machine sweeps                | The tool's own verdict (Skylos, ruff, pyright, the four `poe` scanners, Vulture) | Absence of known defect classes; enforcement of FR-001/FR-002                    | Behavioural correctness. A green scan says nothing about meaning. |
| **L1** | Property tests (`hypothesis`) | An invariant stated in a contract or law, quantified over generated inputs        | Universal claims: exactness, no-raise, identity completeness, causality           | Anything the contract does not state as universal        |
| **L2** | Contract tests                | The CT-* YAML in `docs/contracts/`                                              | That every implementer and every consumer honours the same contract              | Epic-specific behaviour; that belongs at L3               |
| **L3** | Acceptance tests              | The acceptance-criterion sentence in `epics.md`, verbatim                       | That the built behaviour is the behaviour the epic promised                       | Contract facts already fixed at L2                        |
| **L4** | Scenario tests                | The prose walkthrough in `docs/scenarios/SCN-*.md`                              | That cross-package journeys work end to end as designed                           | Unit-level edge cases                                     |
| **L5** | Mutation testing (`mutmut`)   | A surviving mutant — an assertion that does not assert                          | That the tests at L1–L4 actually constrain the code                              | Coverage percentage; a survivor is a finding, not a metric |
| **L6** | Requirements-fidelity review  | One agentic seat per epic reading ACs against assertions                        | That the tests test the requirement rather than the implementation                | Adversarial panels — explicitly not used                  |

**Duplicate-coverage guard.** A behaviour is asserted at exactly one level. Contract facts live at L2 and are never restated at L3. Epic ACs live at L3 and are never restated at L4. L4 asserts only what no single epic owns — the cross-package journey. When two levels want the same assertion, the lower one keeps it.

**Where independent tests still matter in the well-covered packages.** `qmf-core` (99.65% / 98.38%), `qmf-venue` (99.13% / 96.99%), `qmf-registry` (98.46% / 94.86%), `qmf-structure` (98.03% / 95.21%) and `qmf-indicators` (97.44% / 94.17%) have strong nets. Line coverage there is saturated and adding tests to raise it would be waste. What coverage cannot see, and what the independent suite is for:

- **qmf-core** — whether the CT-01 rounding-mode table in the contract matches the one in the code; whether fp1 canonicalization is stable across NFC normalization, key ordering and integer-only identity content for inputs no author happened to construct; whether *every* public callable returns rather than raises. All three are L1 properties plus L5 mutation, and none is a line.
- **qmf-registry** — "no path reaches the live zone without a recorded operator signature attesting the record's fp1" (L17, AR-39, SCN-0007) is a negative claim over the whole export surface. An enumeration test, not a line.
- **qmf-venue** — the four-outcome law (CT-19, L35, SCN-0005) is a state-machine claim: timeout is not rejection, UNKNOWN is a state, an UNKNOWN blocks its `(venue, account)` command stream until explicit reconciliation, and market data keeps flowing throughout. That is a stateful property over command/event sequences. Note also that `qmf-venue` ships no `FAILURES.md` and no `examples/` directory, against NFR-11 and AR-21.
- **qmf-structure** — look-ahead safety (CT-17, FR-020) is the property "no chart object's value at time `t` depends on any input with timestamp greater than `t`", quantified over all input orderings. Invisible to coverage; decisive for every backtest.
- **qmf-indicators** — batch/stream equivalence (CT-16, FR-019) is the property "for every input series and every split point, the streaming fold equals the batch result". And the arithmetic itself has a genuinely external oracle: TA-Lib is the canonical reference by ratification (AR-49, DEC-0127), so re-implementation is a contract defect and TA-Lib's own output is the judge.

---

## Ranked Epic List — Likelihood × Damage

**Damage model** (operator-ratified): money-math and governance-gate errors poison everything downstream; evidence-integrity errors are unrecoverable after the fact; reports and CLI cosmetics are recoverable. **Likelihood evidence**: coverage gaps, complexity hot-spots, and advisory-finding density. **Who coded what is barred as a factor.**

Tiers set the depth of the independent suite, not the order of discovery:

- **T1** — full independent suite: L1 properties + L2 contracts + L3 acceptance for every AC + L4 participation + L5 mutation targets + L6 review.
- **T2** — L2 contracts + L3 acceptance for every AC + targeted L1 properties + L6 review.
- **T3** — L3 acceptance for P0/P1 ACs + regression pins for every confirmed finding + L6 review.
- **T4** — L2 contract conformance spot-check + L4 scenario participation only.

### T1 — Foundational spine (7 epics)

| Rank | Epic                                       | Tier | Likelihood × Damage — one line                                                                                                                                                                                    |
| ---- | ------------------------------------------ | ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | **E10 qmf-risk — Books, BMS & governance** | T1   | Maximum damage (sizing and every money gate) × high likelihood: 455 quality findings, four CRITICAL complexity hits (`control_action.py` cyclomatic 38 and 31, cognitive 62; `exit_record.py` 28; `journal.py` 26), and the package's own weakest files at 71–74% (`journal` 71.7%, `exit_record` 72.2%, `performance` 73.1%, `control_window` 73.7%) — nine FRs concentrated in one epic. |
| 2    | **E1 qmf-core — exact domain foundation**  | T1   | Maximum damage (every package builds on CT-01..CT-05) × low measured likelihood (99.65% / 98.38%, mutation already running) — but both critical risks R-001 and R-002 are failures to *use* core's guards, so core is where the universal properties must be authored.                                                     |
| 3    | **E8 qmf-venue port + cTrader adapter**    | T1   | Maximum damage (the literal live-money boundary: five command kinds, four-outcome law, UNKNOWN blocking) × low-moderate likelihood (99.13% / 96.99% coverage, 132 findings) — but no `FAILURES.md`, no `examples/`, and a state-machine law that line coverage cannot reach.                                              |
| 4    | **E3 qmf-data — evidence store & journals** | T1   | Maximum damage (seals, splits, world isolation, journals — errors are unrecoverable after the fact) × moderate likelihood: `verify.py` CRITICAL cyclomatic 27, `cycle.py` 63.3% line / 44.3% branch (worst file outside qmb/qml), 406 findings; R-012's "at every boundary" claim is untested as a claim.               |
| 5    | **E2 qmf-registry — identity & promotion** | T1   | Maximum damage (the only path to live money is a human-signed promotion; lineage never rewritten) × moderate likelihood: `persistence.py` CRITICAL cyclomatic 26 against 98.46% / 94.86% coverage — a negative-space claim needing an enumeration test.                                                                  |
| 6    | **E13 QMB substrate**                      | T1   | Maximum damage (the resolved run-config fingerprint *is* the run id and the ledger key; carries world derivation) × high likelihood: `config/compiler.py` two CRITICAL complexity hits (36 and 30); epic 23's replay-clock bypass was caught only because this compiler independently re-gated it.                        |
| 7    | **E14 QMB run loop & replay backtest**     | T1   | Maximum damage (one never-forked loop; forming bars never actionable; warm-up boundary; every result derives from it) × high likelihood: `runloop/loop.py` CRITICAL cyclomatic 26, `bars.py` 67.9% line / 55.6% branch.                                                                                                 |

### T2 — High damage, narrower blast radius or stronger nets (8 epics)

| Rank | Epic                                        | Tier | Likelihood × Damage — one line                                                                                                                                                                                                     |
| ---- | ------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 8    | **E15 QMB orchestrator, ledger, concurrency** | T2 | High damage (experiment accounting: exactly one ledger line per run) × the highest measured likelihood in the repository: `spawn.py` 59.8% line / 50.8% branch with 55 findings, `watch.py` 64.3% / 37.0%, plus two evidenced ledger-loss findings (E20-#3, E21-#4). |
| 9    | **E12 QML protocol & conformance**          | T2   | High damage (the two-layer gate is the ticket into governed Book seats; V1 sandbox is static scanning only per AR-68) × high likelihood: `layer1.py` 70.9% / 63.6%, `layer2.py` 70.0% / 58.0%, `qml` the weakest package band, no `FAILURES.md`. |
| 10   | **E11 QML authoring**                       | T2   | High damage (bot identity mint = governance; carries the CT-22/CT-23 format-2 mints) × high likelihood: `footprint/_coerce.py` 58.3% line / 48.8% branch — the worst-covered file in the repository — plus `template.py` 67.1%, `confluence.py` 73.5%, `parameters.py` 74.2%. |
| 11   | **E18 QMB data management**                 | T2   | High damage (gappy or mis-catalogued market data silently invalidates every downstream run) × the worst likelihood cluster in the repository: `qmb data/verify.py` 59.9% with CRITICAL cyclomatic 28 / cognitive 59, `gap_check.py` 62.8% / 50.0%, `download.py` 69.0% with CRITICAL cyclomatic 35 / cognitive 64 *and* the live `ambient-scan` failure, `catalog.py` CRITICAL cyclomatic 32. |
| 12   | **E16 qmb CLI & doors**                     | T2   | High damage (the human's only surface; a refusal rendered wrong is a wrong decision) × high likelihood with direct evidence: E23-H1 proved the parity gate blind, E20-#10 found inconsistent door precedence between sibling axes.        |
| 13   | **E17 QMB fill/slippage/fee/financing**     | T2   | High damage (the money model under every backtest) capped by SC-06's `optimistic` taint × high likelihood: `execution/ports.py` 70.2% with 46 findings, `fill.py` 68.6%, `spread.py` 68.9%, `financing.py` 71.6%, `cost.py` 71.7%, three CRITICAL complexity hits. |
| 14   | **E6 qmf-data — source intake**             | T2   | High damage (CT-15 idempotency governs everything that lands; the news-calendar feed powers a fail-closed *money* gate per FR-033/SCN-0008) × moderate likelihood within a 92.2% / 82.5% package.                                       |
| 15   | **E5 qmf-data — backup, restore & verify**  | T2   | High damage on the day it matters (recoverability claims come only from `verify`; a false green is discovered exactly once) × moderate likelihood: `qmf-data verify.py` 69.3% line / 55.4% branch.                                       |

### T3 — Moderate damage or damage capped by ruling (7 epics)

| Rank | Epic                              | Tier | Likelihood × Damage — one line                                                                                                                                                                              |
| ---- | --------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 16   | **E19 QMB reports & CT-32**       | T3   | Moderate-high damage (the artifact *is* CT-32 and every render is a pure function of it, so a wrong number becomes a wrong decision — but never a money act) × high likelihood: `measures.py` two CRITICAL hits (32, 28), `charts.py` 69.8% with CRITICAL cyclomatic 29 / cognitive 53, `render.py` 71.6%. |
| 17   | **E22 QMB robustness ladder**     | T3   | Moderate damage (publishes only; thresholds deferred to GAP-0049) × the densest confirmed evidence: 2 HIGH + 4 MEDIUM live, including the money-path back door via `carve_return_statistic`'s `unit_kind` default and the unguarded `summarize_distribution`. |
| 18   | **E21 QMB optimization studies**  | T3   | Moderate damage (search results, not money acts — but a Study stopping early on a meaningless cross-currency comparison spends a governed split budget for nothing) × high likelihood: 2 HIGH confirmed, `sampler.py` 72.6%.  |
| 19   | **E23 QMB synthetic data**        | T3   | Damage bounded by law (L20: synthetic never validates edge) except for the taint/world-derivation gate, which is governance × the highest confirmed-finding count: 3 HIGH live (door parity gap, nested-shape replay-clock bypass, source-scale trust producing a silent 100× price error). |
| 20   | **E20 QMB multi-route sweeps**    | T3   | Moderate damage (a dropped combination means the sweep silently did not test what its pre-flight count promised) × high likelihood: 1 HIGH confirmed and reproduced by the reviewer (4-combo sweep → 2 combos with zero ledger lines).  |
| 21   | **E9 qmf-structure**              | T3   | Moderate-high damage (a look-ahead leak invalidates every backtest, though SC-06 caps it today) × low likelihood: 98.03% / 95.21%, eleven CT-17 test modules, 103 findings. One causality property carries most of the value here.       |
| 22   | **E7 qmf-indicators**             | T3   | Moderate damage (a wrong indicator misleads a bot, but the Book still gates the money) × low likelihood: 97.44% / 94.17%, 177 findings — and TA-Lib is an external oracle by ratification, which makes the two properties here cheap and strong. |

### T4 — Low damage, small surface (1 epic)

| Rank | Epic                              | Tier | Likelihood × Damage — one line                                                                                                                                                        |
| ---- | --------------------------------- | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 23   | **E4 qmf-calendar-forex**         | T4   | Low-moderate damage (a wrong session boundary shifts bars, but the calendar is versioned and fingerprinted, and tzdata is pinned with the resolved version inside the fingerprint) × low likelihood: 270 statements, 94.81% / 75.81%, 18 findings. Contract spot-check plus scenario participation is proportionate. |

**Deviation from operator instinct, flagged.** The instinct was foundational-first, and the evidence largely confirms it — E1/E2/E3/E8/E10 all land in T1. Two evidence-driven departures: **E13/E14 (QMB substrate and run loop) were promoted into T1** because the resolved-config fingerprint is the identity root of every run and the loop is the single source of every result, which makes them foundational in the damage sense even though they sit at wave 5–6; and **E18 (data management) was promoted to T2** despite being tagged a light epic, because it carries the single worst likelihood cluster in the repository and corrupt market data invalidates everything built on it.

---

## Test Coverage Plan

**P0/P1/P2/P3 = priority and risk level — what to focus on if time runs short. It is not execution timing.** See "Execution Strategy" for when things run.

### P0 (Critical)

**Criteria:** Money-path, governance-gate, identity or evidence-integrity impact, and no safe workaround.

| Test ID    | Requirement                                                                          | Test Level | Risk Link     | Notes                                                                        |
| ---------- | ------------------------------------------------------------------------------------ | ---------- | ------------- | ----------------------------------------------------------------------------- |
| **P0-001** | FR-001 / CT-01 / AR-15 — money, price, quantity are exact scaled integers            | L1         | R-001         | Round-trip and arithmetic properties at every declared scale                   |
| **P0-002** | FR-001 / CT-01 — dimension algebra: mixed unit-kind or currency must refuse          | L1         | R-001         | Full unit-kind × currency cross-product; reproduces E21-H1, E22-M4, E22-M5     |
| **P0-003** | FR-004 / CT-04 / AR-13 — no public boundary raises; value or typed refusal always    | L1         | R-002         | Enumerated from the export surface of all ten units; the universal law         |
| **P0-004** | FR-005 / CT-05 / AR-14 — fp1 canonical, deterministic, integer-only identity content | L1         | R-004         | NFC, key ordering, integer-only content, `fp1:sha256:<hex>` shape              |
| **P0-005** | FR-005 / AR-52 — distinct semantic inputs produce distinct fingerprints              | L1         | R-004         | Identity completeness; reproduces E20-H1 and E23-M4 without naming them        |
| **P0-006** | FR-002 / CT-02 / AR-16 — int64 UTC-ns everywhere; no clock read below the root       | L1 + L0    | R-005         | Property plus the `ambient-scan` verdict                                       |
| **P0-007** | FR-009 / L17 / AR-39 / SCN-0007 — only a human-signed promotion reaches live         | L3         | —             | Negative enumeration over the registry export surface                          |
| **P0-008** | FR-012 / CT-12 / L19 / SCN-0003 — the sealed holdout is excluded at *every* boundary  | L3         | R-012         | Boundary census, not a single-path test                                        |
| **P0-009** | FR-011 / CT-11 / L18 / AR-33 — cross-world reads refuse; `world=simulated` refuses    | L3         | R-012         | Every room-role × world pair                                                   |
| **P0-010** | FR-027 / FR-028 / CT-22 / CT-23 — every trade intent passes the Book's charter doors  | L3         | R-001         | Three admission layers; R frozen at admission; full-loss price required        |
| **P0-011** | FR-032 / FR-033 / CT-29 / CT-30 / L39 — exit preservation; no control blocks a risk-reducing act | L3 | —      | Kill-switch vs kill-line distinction; same-tick BMS rank arbitration            |
| **P0-012** | FR-023 / CT-19 / L35 / SCN-0005 — four-outcome law; UNKNOWN blocks the command stream | L3         | —             | Stateful sequence test at the port seam                                        |
| **P0-013** | FR-025 / CT-21 / AR-37 / L34 — secrets never leave the connection manager, never render | L1        | R-019         | Rendering property; no re-scanning                                             |
| **P0-014** | FR-036 / AR-52 — the resolved run-config fingerprint is the run id and the ledger key | L3         | R-008         | Over every accepted config shape, generated from the schema                    |
| **P0-015** | FR-045 / AR-51 — exactly one ledger line per run, never zero, never two              | L3         | R-010         | Fault-injection matrix over abort, teardown, cancel and storage refusal        |
| **P0-016** | FR-048 / AR-64 — the Bot kind mints only after both conformance layers pass          | L3         | —             | Negative enumeration: no other path mints                                      |
| **P0-017** | NFR-02 — the tier-1 static scanners actually run and pass on `integration`           | L0         | R-005         | The L0 baseline sweep; first action of the phase                               |
| **P0-018** | FR-010 / CT-10 / CT-15 — intake is idempotent; corrections append, never overwrite    | L2 + L3    | R-007         | Includes the adversarial scale-mismatch case (E23-H3)                          |

**Total P0:** ~55–75 tests (the rows above are families; each expands to several cases)

---

### P1 (High)

**Criteria:** Core or frequent behaviour, material reach, limited workaround.

| Test ID    | Requirement                                                                       | Test Level | Risk Link | Notes                                                     |
| ---------- | --------------------------------------------------------------------------------- | ---------- | --------- | ---------------------------------------------------------- |
| **P1-001** | CT-01..CT-34 — one independent contract module per contract                       | L2         | R-015     | Parameterized over every implementer and consumer; settles AR-19 |
| **P1-002** | SCN-0001..SCN-0012 — one module per golden scenario                               | L4         | R-003     | The prose walkthrough is the oracle                        |
| **P1-003** | FR-046 / AR-58 — door parity: every capability on every door, refusals per transport | L3       | R-006     | Surface-derived; depends on blocker B-3                    |
| **P1-004** | FR-037 / B-2 / SC-10 — warm-up in-loop with trading locked; forming bars never visible | L3      | R-018     | The evidence range is the trading interval only            |
| **P1-005** | FR-020 / CT-17 — causality: no value at `t` depends on an input after `t`          | L1         | R-018     | Quantified over input orderings                            |
| **P1-006** | FR-019 / CT-16 / AR-49 — batch/stream equivalence; TA-Lib is canonical             | L1         | —         | TA-Lib is the external oracle                              |
| **P1-007** | FR-013 / CT-13 — gapless per-writer journals; read-time projections                | L1 + L3    | —         | Gaplessness as a property; logbook projection at L3        |
| **P1-008** | FR-014 / CT-14 / CT-26 / SCN-0004 — recoverability claims come only from `verify`  | L3         | —         | A false-green `verify` is the test that matters            |
| **P1-009** | FR-038 / FR-039 / SC-11 — one registry as-of frozen at batch admission             | L3         | R-004     | Sweeps and Studies share the rule                          |
| **P1-010** | FR-044 / SC-06 — every fill carries the `optimistic` taint; fidelity labels present | L3        | —         | Interface only; no threshold                               |
| **P1-011** | FR-043 / CT-32 / AR-59 — the result artifact carries the full label set            | L3         | —         | Charts are data, never images                              |
| **P1-012** | FR-047 / AR-62 / AR-63 — bot identity content; what mints and what does not        | L3         | R-004     | Re-binding, seat assignment and paper flips never mint     |
| **P1-013** | FR-029 / FR-031 / CT-24 / CT-28 / SCN-0006 — paper and bindings as dated epochs    | L3         | —         | One Book per bot                                           |
| **P1-014** | FR-042 — data management: download, verify, gap-check, catalog, calendar-aware     | L3         | R-007     | The worst likelihood cluster in the repository             |
| **P1-015** | FR-018 / FR-033 / SCN-0008 — a failed calendar refresh degrades to a fail-closed block | L3      | —         | Pair-scoped news windows blocking entries                  |
| **P1-016** | FR-034 / CT-32 / SCN-0011 — performance publishes and never acts; no composite gates money | L3   | —         | Negative claim over the performance surface                |
| **P1-017** | NFR-03 — replay reproduces the CT-32 fingerprint or refuses                        | L4         | R-016     | UNPROVEN until the golden corpus exists                    |
| **P1-018** | NFR-11 — every typed refusal reachable from a door has a register entry            | L3         | R-009     | Reconciliation, cheap to run, high information             |

**Total P1:** ~160–210 tests

---

### P2 (Medium)

**Criteria:** Secondary behaviour, narrower reach, an acceptable workaround exists.

| Test ID    | Requirement                                                              | Test Level | Risk Link      | Notes                                                                 |
| ---------- | ------------------------------------------------------------------------ | ---------- | -------------- | ---------------------------------------------------------------------- |
| **P2-001** | Regression pins for the 8 confirmed HIGH advisory findings (E20–E23)     | L3         | R-001/004/006/007/008 | One requirement-shaped test per finding — never a site-shaped one |
| **P2-002** | FR-040 — robustness ladder interfaces (MC, significance gate, walk-forward) | L3       | —              | Interfaces only; GAP-0049 thresholds stay DEFERRED                      |
| **P2-003** | FR-041 / L20 / SCN-0009 — claim-class labels; synthetic never validates edge | L3      | —              | Includes the taint and world-derivation gate                            |
| **P2-004** | FR-021 / AR-27 — forex calendar; tzdata pin participates in the fingerprint | L2        | —              | E4's whole allocation                                                   |
| **P2-005** | AR-35 — `correlation_id` propagates across every package boundary; `health()` census | L3 | —              | Currently unsurveyed by any gate                                        |
| **P2-006** | AR-25 / NFR-06 — every format version stays readable forever             | L3         | —              | Includes the CT-22/CT-23 format-1 → format-2 path                       |
| **P2-007** | FR-030 / CT-25 — read-time risk journal projections                       | L3         | —              | Projection equivalence under replay                                     |
| **P2-008** | FR-035 / L38 / NFR-07 — a blank configurable blocks live money but allows registration | L3 | —          | The whole variables registry surface                                    |
| **P2-009** | FR-022 / CT-18 / AR-45 — verify-or-refuse before any command is accepted  | L3         | —              | Per-(VenueId, account) observation profile must exist first             |
| **P2-010** | FR-024 / CT-20 / AR-47 — recording precedes interpretation                | L3         | —              | Market data keeps flowing while the command pipe is gated               |

**Total P2:** ~130–180 tests

---

### P3 (Low)

**Criteria:** Rare, cosmetic or experimental; easy workaround.

| Test ID    | Requirement                                                        | Test Level | Notes                                                        |
| ---------- | ------------------------------------------------------------------ | ---------- | ------------------------------------------------------------- |
| **P3-001** | AR-22 — benchmark harnesses run and emit comparable numbers        | L0         | Baselines and threshold are UNKNOWN; the finding is the gap    |
| **P3-002** | AR-21 — every package ships examples as tier-1 artifacts           | L3         | `qmf-venue` has no `examples/`; `qml` has no `_bench.py`       |
| **P3-003** | Dead-code and unused-parameter cleanup verification                | L0         | Consumes Skylos and Vulture output; authors nothing            |
| **P3-004** | Exploratory charter: the money path, hand-driven, one session      | L6         | Time-boxed; findings only                                     |
| **P3-005** | AR-07 — DEPENDENCIES.md matches the resolved lockfile and licences | L3         | Licence-policy conformance                                    |

**Total P3:** ~35–55 tests

---

## NFR Test Coverage Plan

| NFR Category                | Requirement / Threshold                                                              | Planned Validation                                                              | Tool / Level             | Evidence Artifact                        | Priority |
| --------------------------- | ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------- | ------------------------ | ----------------------------------------- | -------- |
| Security (NFR-05)           | Zero secrets in any artifact; `SecretValue` never renders                            | Consume the Skylos gate; one rendering property                                   | Skylos (L0) + hypothesis (L1) | Skylos report + `test_secret_rendering`   | P0       |
| Determinism (NFR-03)        | Same inputs ⇒ same fingerprints and same results; replay reproduces or refuses       | Replay golden run ids and compare CT-32 fingerprints                              | pytest (L4)              | Replay diff report                        | P0       |
| Data integrity (NFR-06/08)  | Format versions readable forever; every state change reconstructable                 | Multi-version artifact corpus replay; journal gaplessness property                 | pytest (L2/L3) + hypothesis (L1) | Format corpus results                | P1       |
| Maintainability (NFR-02)    | 80% coverage floor per package; 100% branch on CT-01/CT-02 modules; tier-1 scanners   | Full `poe check` + `cov-report`; the four static scanners                          | poe / CI (L0)            | `poe check` transcript, `coverage.json`   | P0       |
| Failure discipline (NFR-11) | Every designed failure mode has a register entry                                     | Reconcile every door-reachable typed refusal against the registers                 | pytest (L3)              | Register delta list                       | P1       |
| Performance (NFR-04/AR-22)  | Measure-then-budget at 10/100/200; qmf-core import under ~1s                          | Run every `_bench.py`; record numbers as the first baseline                        | pytest-benchmark-class (L0) | Benchmark output per (OS, CPU-class)   | P3       |
| Operability (NFR-10/AR-35)  | `correlation_id` across every boundary; `health()` on every resource owner            | Export-surface census; propagation test across a full journey                      | pytest (L3)              | Census table                              | P2       |
| Concurrency (NFR-09/AR-17)  | No QMF-spawned concurrency; async only at the venue edge; one writer per stream       | `ambient-scan` plus writer-ownership acceptance tests                              | poe (L0) + pytest (L3)   | Scanner output + ownership tests          | P1       |
| Compliance / licensing (AR-07) | MIT/BSD/Apache/PSF only; no GPL/AGPL; ship-no-corpus gate honoured                 | DEPENDENCIES.md vs lockfile reconciliation; licence-tag assertion on data windows   | pytest (L3)              | Licence reconciliation report             | P3       |

**Missing thresholds or evidence sources — flagged, not guessed:**

- NFR-04's latency, throughput and memory numbers at the 10/100/200 marks do not exist. Ratified as measure-then-budget. This phase produces the first measurements; it asserts nothing against them.
- AR-22's "regression beyond recorded threshold" — the threshold is not recorded anywhere in the tree. Blocks the Tier-2 performance gate. Needs an Architecture decision (HIGH-4).
- NFR-03 has no golden corpus. Determinism stays UNPROVEN in the proof map until one is committed (HIGH-5).
- GAP-0048 (fidelity taxonomy) and GAP-0049 (robustness pass batteries), CT-08 registration-gate thresholds, and SR*/search-quality thresholds are deferred by ruling. Every requirement depending on them is marked DEFERRED, with its SC-0N reference.

---

## Per-Epic Test Plan Template

**Every epic in the fan-out produces exactly one `qa/epics/epic_NN_<slug>/PLAN.md` following this outline. Sections run in order, and the order is the point: the test list is written before any implementation is read.**

**Section 1 — Header and baseline.**
Epic number and title; tier (T1–T4); packages and modules in scope; the FR / AR / NFR / CT / SCN / L ids this epic owns (copied from the epics.md FR Coverage Map, never re-derived); the evidence baseline for those modules — line and branch coverage, Skylos finding count and any CRITICAL complexity hits, and the advisory-review findings if a build report exists for the epic. Where no build report exists (epics 1–19), say so explicitly rather than leaving the row blank.

**Section 2 — Requirement extract.**
Every acceptance criterion this epic owns, quoted verbatim from `epics.md` with its story number, plus the relevant clauses of each CT-* YAML and each SCN-* walkthrough. Nothing paraphrased. This section is the oracle; if a requirement is ambiguous, that ambiguity is a finding, recorded here and not resolved by reading the code.

**Section 3 — Fault-family checklist.**
The eight families the epic 20–23 reviews actually found. For each, answer "does this epic have a member, and where": (a) unit-kind or currency treated as optional on a numeric path; (b) an exception where a typed refusal was contracted; (c) a fingerprint that omits a distinguishing input; (d) a governance gate implemented at one input shape; (e) an external input trusted without validation; (f) a capability reachable from one door only; (g) a ledger or journal line missing on a failure path; (h) an existing test that pins the implementation rather than the requirement. An epic with no member of a family says so; the answer "none" is a result.

**Section 4 — Independent test list.**
The table the lane will implement. Columns: Test ID (`QA-E<NN>-L<level>-<seq>`) | Requirement id(s) | Level (L1–L4) | Oracle (the exact document and clause) | Priority (P0–P3) | The assertion, in one sentence. **This section is written before any `src/` file is opened.** Reading a public signature in order to call it is permitted afterwards; reading the implementation body before this table exists is not.

**Section 5 — Existing-test audit.**
For every requirement in section 2, name the existing test in the package's own `tests/` that claims to cover it, and classify it in one line: **keep** (asserts the requirement), **suspect** (asserts something narrower or derived from the implementation), or **contradicts** (asserts behaviour the requirement forbids). Every "contradicts" row goes straight into the findings inventory with the requirement id it contradicts. This is where R-003 gets its evidence.

**Section 6 — Mutation targets.**
Modules from this epic proposed for the `mutmut` roster, one justification each. The rule for inclusion: a surviving mutant in this module would mean a money or governance claim is unasserted. Reports, charts, CLI rendering and formatting helpers are excluded by that rule.

**Section 7 — Deferred and out of scope.**
Requirements gated by GAP-0048 / GAP-0049, with the SC-0N reference; platform gaps (Ubuntu per AR-23); anything the tier does not fund. Each becomes a DEFERRED or UNPROVEN row in the proof map — never a blank.

**Section 8 — Findings.**
Everything the author found while writing the plan and the tests: failing assertions, ambiguous requirements, contradictions, missing register entries, undocumented behaviour. Id, requirement, severity, reproducer, one-line description. **No fixes.** These rows are appended to `qa/_trace/findings.csv`.

**Lane completion criterion:** the epic's PLAN.md has all eight sections, every test in section 4 exists and has run (pass or fail), section 5 covers every requirement in section 2, the L6 requirements-fidelity seat has reviewed the lane, and every finding is in the inventory.

---

## Requirement Traceability

**Every test declares what it proves. A test that declares nothing does not run.**

- **Marker:** `@pytest.mark.req("FR-023", "CT-19", "SCN-0005", "AR-44", "L35")` — any mix of `FR-0NN`, `NFR-0N`, `AR-NN`, `CT-NN`, `SCN-0NNN`, `L<n>`, `DEC-0NNN`.
- **Test id:** `QA-E<epic>-L<level>-<seq>`, e.g. `QA-E10-L3-004`. Stable across runs; it is the key in the findings inventory and the fix cards.
- **Collection guard:** `qa/conftest.py` fails collection for any test lacking a `req` marker and for any marker id that does not resolve against `qa/_oracles/`. Requirement ids cannot drift silently.
- **Forward map:** `qa/_trace/trace.yaml`, generated from markers — requirement id → list of test ids, levels, oracles and last outcome.
- **Reverse map:** requirement ids with no test — the UNPROVEN list. This is the map's most valuable output and the reason it is generated rather than hand-kept.
- **Proof map** (`qa/_trace/proof_map.md`) — one row per requirement across the full inventory: **FR-001..FR-050**, **NFR-01..NFR-11**, **AR-01..AR-69**, **CT-01..CT-34**, **SCN-0001..SCN-0012**, plus every constitution law a test cites. Each row carries a verdict:
  - **PROVEN** — at least one passing independent test at the right level, with its test ids named.
  - **PARTIAL** — some clauses proven, others not; the unproven clauses are quoted.
  - **UNPROVEN** — no independent test; the reason is stated (out of tier, no oracle, needs a blocker resolved).
  - **DEFERRED** — gated by ruling (GAP-0048 / GAP-0049 / SC-06 / SC-07 / AR-23), with the reference.
  - **FAILING** — an independent test exists and fails; links to the finding id.

The proof map is the phase's headline artifact. A red suite with a complete proof map is a successful phase; a green suite with an incomplete one is not.

---

## Execution Strategy

**Philosophy:** run everything on every push to the qa branch unless it needs infrastructure or real time. The suite is pure Python with injected clocks, no database server, no network and no browser, so it parallelizes cleanly with `pytest -n auto`.

### Every push to the qa branch: pytest (~10–15 min)

The full `qa/` suite — L1 properties, L2 contract modules, L3 acceptance tests, L4 scenarios — across all priorities. Parallelized across worker processes. `hypothesis` runs at its default example budget here.

**Why in-push:** fast feedback, no infrastructure, and the whole point of the phase is finding things early.

### Nightly (~1–3 hours)

- **Mutation testing** (`mutmut`) over the justified roster — the mechanical adversary. Slow by nature; survivors are findings, not metrics.
- **Deep property runs** — `hypothesis` at a raised example budget with a persistent example database, so rare counterexamples accumulate across nights.
- **Full `poe check` and `poe check-integration`** — the four static scanners, `cov-report`, `test-tools`, `build-all`, and the isolated-install smoke that proves an undeclared import fails.
- **Benchmark harnesses** — every `_bench.py`, recorded as the first baseline (there is nothing to compare against yet; see R-014).

**Why nightly:** minutes-to-hours each, and none of them needs to gate an authoring push.

### Weekly (~hours)

- **Determinism replay** — re-run the golden run corpus and compare CT-32 fingerprints (once the corpus exists; UNPROVEN until then).
- **Full restore rehearsal** — CT-14 / SCN-0004 end-to-end restore-and-verify against a real off-machine target.
- **Flake burn-in** — the quarantine list, including the known concurrent-I/O class (R-021), run repeatedly to characterize rather than fix.

**Why weekly:** real infrastructure, real time, and infrequent validation is sufficient.

### Manual, excluded from automation

- The exploratory money-path charter (P3-004), time-boxed, one session.
- Requirements-fidelity review seats (L6) — one per epic, agentic but not a suite.
- Ubuntu tier-1 verification — blocked on a remote (AR-23).

---

## QA Effort Estimate

| Priority  | Count    | Effort Range       | Notes                                                                              |
| --------- | -------- | ------------------ | ----------------------------------------------------------------------------------- |
| P0        | ~55–75   | ~2.5–4.5 weeks     | Property-test design over the money path and governance gates; the enumeration tests are design-heavy |
| P1        | ~160–210 | ~2.5–4.5 weeks     | 34 contract modules, 12 scenario modules, per-epic acceptance coverage               |
| P2        | ~130–180 | ~1.5–2.5 weeks     | Regression pins for confirmed findings, secondary flows, censuses                    |
| P3        | ~35–55   | ~0.5–1 week        | Benchmarks, register reconciliation, licence check, one exploratory session          |
| **Total** | ~380–520 | **~7–12 weeks**    | **1 engineer, full-time** — or **~4–7 weeks** across parallel factory lanes          |

**Assumptions:**

- Includes plan authoring, test implementation, debugging, and the traceability plumbing.
- Excludes all remediation — fixes are a separate lane after the operator triages the inventory.
- Excludes ongoing maintenance (~10%).
- Assumes the three blockers are resolved at phase entry. B-1 unresolved costs the L0 baseline; B-2 unresolved invalidates the whole premise; B-3 unresolved defers the E16 parity work.

---

## Entry Criteria

**Independent verification cannot begin until all of the following are met:**

- [ ] Blockers B-1 (gate reconciliation), B-2 (`qa/` isolation ruling) and B-3 (parity derivation) answered by the operator or Architecture.
- [ ] `qa/independent-tests` branch cut from `integration@2c8d495`; isolated qa worktrees provisioned.
- [ ] `hypothesis` available in a qa-only dependency group; `mutmut` roster extensible.
- [ ] The L0 baseline captured: full `poe check` and `poe check-integration` output stored as an artifact, including whatever the four static scanners say.
- [ ] Requirement-id extraction working: FR / NFR / AR from `epics.md`, CT from `docs/contracts/`, SCN from `docs/scenarios/`, L* from `docs/constitution.md`.
- [ ] The collection guard live — a test without a resolvable `req` marker fails collection.

## Exit Criteria — the stopping point of this phase

**This phase is complete when these three artifacts exist and the operator has them. It is not complete when the suite is green, and it does not require the suite to be green.**

- [ ] **Findings inventory** (`qa/_trace/findings.csv`) — every failing independent test and every audit finding as one row: finding id, epic, requirement id(s), level, oracle, severity, evidence (failing test id or `file:line`), reproducer, and the risk id it belongs to. Zero fixes applied. Zero merges. Zero deletions.
- [ ] **Fix-card backlog** — one lane-agnostic card per finding *cluster* (clustered by fault family, not filed one per symptom), each naming the requirement it restores and the independent test that will prove the restoration. Cards are lane-agnostic: any factory lane can pick one up.
- [ ] **Proof map** (`qa/_trace/proof_map.md`) — every FR-001..050, NFR-01..11, AR-01..69, CT-01..34 and SCN-0001..0012 carrying PROVEN / PARTIAL / UNPROVEN / DEFERRED / FAILING, with test ids on every PROVEN row and a stated reason on every UNPROVEN one.

Supporting completion conditions:

- [ ] Every epic has a `PLAN.md` with all eight sections and an L6 review seat completed.
- [ ] Every T1 and T2 epic has its full independent suite implemented and run.
- [ ] The mutation roster has run at least once and survivors are in the inventory.
- [ ] No code outside `qa/` has been modified.

**Quality gate criteria for the independent suite itself** (not for the product — the product's verdict is the proof map):

- P0 independent tests: 100% authored and executed; failures are findings, not blockers.
- P1 independent tests: ≥95% authored and executed.
- Every P0 and P1 requirement has a proof-map row that is not blank.
- Every independent test has at least one resolvable requirement id.
- Mutation survivors in money-path and governance modules are each triaged into the inventory.

---

## Implementation Planning Handoff

| Work Item                                                   | Owner              | Target Milestone | Dependencies / Notes                                     |
| ----------------------------------------------------------- | ------------------ | ---------------- | --------------------------------------------------------- |
| Resolve blockers B-1, B-2, B-3                              | Operator / Architecture | Phase entry  | Everything else waits on B-2 in particular                 |
| L0 baseline sweep (`poe check`, `check-integration`)        | QA                 | Phase entry      | Cheapest high-information action in the plan               |
| `qa/` tree, conftest guards, `_oracles/` loaders            | QA                 | Phase entry      | Requirement extraction from `epics.md` and `docs/`         |
| L1 universal properties (no-raise, money algebra, fp1, causality) | QA           | Week 1–2         | These four cover three of the four highest risks           |
| L2 contract modules, CT-01..CT-34                           | QA                 | Week 2–4         | Settles AR-19 (R-015) as a by-product                      |
| T1 epic fan-out (E10, E1, E8, E3, E2, E13, E14)             | QA lanes           | Week 2–6         | Parallel worktrees; disjoint by package                    |
| T2 epic fan-out (E15, E12, E11, E18, E16, E17, E6, E5)      | QA lanes           | Week 4–8         | E16 needs B-3 resolved                                     |
| T3/T4 fan-out (E19, E22, E21, E23, E20, E9, E7, E4)         | QA lanes           | Week 6–10        | Regression pins for confirmed findings dominate here       |
| Mutation roster extension and first full run                | QA                 | Week 4 onward    | Nightly thereafter                                         |
| Proof map generation and findings consolidation             | QA                 | Continuous       | The operator handoff artifact                              |
| Failure-register backfill                                   | Package owners     | Fix lane         | Out of this phase; card written by it                      |
| Golden-run corpus, benchmark baselines, parity derivation   | QMB / Architecture | Fix lane         | Each unblocks a currently-UNPROVEN NFR row                 |

---

## Tooling & Access

| Tool or Service            | Purpose                                                              | Access Required                    | Status  |
| -------------------------- | -------------------------------------------------------------------- | ---------------------------------- | ------- |
| `hypothesis`               | L1 property tests — the workhorse of this plan                        | New qa-only dependency group        | Pending |
| `mutmut`                   | L5 mechanical adversary; roster extended beyond `qmf-core`             | Already present; roster edit needed | Pending |
| `pytest-xdist`             | Parallel execution to keep the push suite under 15 minutes            | qa-only dependency                  | Pending |
| Skylos CI                  | L0 security / secrets / AI-defects / CVE evidence                     | Already running; consume output     | Ready   |
| `poe check` / `check-integration` | L0 scanners, coverage floors, isolated-install smoke           | In-repo; needs blocker B-1          | Pending |
| Isolated qa worktrees      | Execution isolation; nothing runs in the main worktree                 | Local                               | Ready   |
| Off-machine backup target  | Weekly CT-14 / SCN-0004 full restore rehearsal                        | Object-storage credentials          | Pending |

**Access requests needed:**

- [ ] Object-storage credentials for the restore rehearsal (weekly lane only).
- [ ] Confirmation that no live venue credentials are in scope (they are not, by this plan's own exclusion).

---

## Interworking & Regression

| Service / Component                | Impact                                                                       | Regression Scope                                          | Validation Steps                                                    |
| ---------------------------------- | ---------------------------------------------------------------------------- | --------------------------------------------------------- | -------------------------------------------------------------------- |
| **The shipped test suite**         | Untouched. Independent tests live only in `qa/`.                              | All 3899 existing tests must still pass unchanged          | Run `poe test` on the qa branch; any delta means `qa/` leaked         |
| **`integration` branch**           | Untouched. No merges, no fixes, no deletions during this phase.               | `integration@2c8d495` remains the tree under verification  | Confirm the tip before each lane starts; re-baseline if it moves      |
| **Skylos CI gate**                 | The `qa/` tree adds files that Skylos will scan                               | Gate must stay clean; qa test code is not shipped code     | Confirm `qa/` is scoped out of the shipped-code scanners, as `tools/tests/fixtures/` already is |
| **`qmf-registry` → `qmf-data`**    | The single ratified inter-library edge (L30, AR-06); contract tests cross it  | The isolated-install smoke must still pass                 | `poe isolated-build` in the nightly lane                              |
| **QMB → qmf-\* consumption**       | QMB consumes seven roster packages in SemVer lockstep                         | Contract tests run producer-side and consumer-side (AR-19) | L2 modules parameterized over every consumer                          |
| **QML → qmf-core / registry / risk** | QML imports three packages and never `qmf-venue` (AR-60)                     | Dependency-direction violations must still fail            | `poe isolated-build`; dependency-direction assertion at L3            |
| **Factory lanes (epic-factory, queue-publish)** | Fix cards produced here feed the lanes later                    | Cards must be lane-agnostic                                | Card format carries no lane-specific field                            |

**Regression strategy:** this phase adds tests and changes nothing else, so the regression surface is the shipped suite itself. The single regression assertion that matters: after every qa-branch push, `poe test` on the shipped suite produces the same 3899 passed, and `poe check`'s coverage floors report the same numbers. Any movement means the `qa/` tree has leaked into the shipped one, which is a phase-integrity failure and is fixed immediately.

---

## Appendix A: Test Tagging and Selective Execution

Priority and level are pytest markers, so lanes can slice the suite without a naming convention:

```python
# qa/conftest.py — the markers and the two guards that make traceability enforceable
import pytest

from qa._oracles.requirements import resolve_requirement_id

REQ_MARKER = "req"


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "req(*ids): requirement ids this test proves")
    for level in ("L1", "L2", "L3", "L4"):
        config.addinivalue_line("markers", f"{level}: test level {level}")
    for priority in ("P0", "P1", "P2", "P3"):
        config.addinivalue_line("markers", f"{priority}: priority {priority}")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Guard 1: no test without a resolvable requirement id. Guard 2: no import from a shipped suite."""
    for item in items:
        marker = item.get_closest_marker(REQ_MARKER)
        if marker is None or not marker.args:
            raise pytest.UsageError(f"{item.nodeid}: independent tests must declare @pytest.mark.req(...)")
        for req_id in marker.args:
            if resolve_requirement_id(req_id) is None:
                raise pytest.UsageError(f"{item.nodeid}: unknown requirement id {req_id!r}")
        module = item.module.__name__ if item.module else ""
        if ".tests." in module or module.startswith("tests."):
            raise pytest.UsageError(f"{item.nodeid}: qa/ must not import a package's own tests")
```

```bash
# Everything (the push lane)
uv run pytest qa -n auto

# P0 only, when time is short
uv run pytest qa -m P0

# One level: the universal properties
uv run pytest qa/properties -m L1

# One epic's lane
uv run pytest qa/epics/epic_10_qmf_risk

# Everything proving one requirement, across levels
uv run pytest qa -m "req" -k "FR-028"

# Nightly: deep property budget
uv run pytest qa/properties --hypothesis-profile=nightly
```

---

## Appendix B: Mutation Targets Beyond qmf-core

**Inclusion rule:** a surviving mutant in this module would mean a money or governance claim is unasserted. Reports, charts, CLI rendering and formatting helpers fail that rule and are excluded regardless of their complexity scores.

| Module                                                    | Justification                                                                                                       |
| --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `packages/qmf-core/src/qmf/core/exact.py`, `chrono.py`    | Already on the roster; the arithmetic and time spine                                                                  |
| `packages/qmf-core/src/qmf/core/` fingerprint + refusal modules | fp1 identity and the CT-04 envelope are the two spine invariants everything else assumes                        |
| `packages/qmf-risk/src/qmf/risk/sizing.py`                | Book-owned sizing is where a mutant becomes a wrong position size                                                     |
| `packages/qmf-risk/src/qmf/risk/control_action.py`        | Cyclomatic 38 and 31, cognitive 62 — the kill-switch, kill-line and exit-preservation arbitration                     |
| `packages/qmf-risk/src/qmf/risk/exit_record.py`           | Cyclomatic 28; every virtual close must mint exactly one exit record (CT-29, L39)                                     |
| `packages/qmf-registry/src/qmf/registry/persistence.py`   | Cyclomatic 26; the storage path under the human-promotion gate                                                        |
| `qmb/src/qmb/config/compiler.py`                          | Cyclomatic 36 and 30; the run-id root and the world-derivation gate                                                   |
| `qmb/src/qmb/runloop/loop.py`, `bars.py`                  | Cyclomatic 26; forming-bar and warm-up boundaries — `bars.py` at 55.6% branch coverage                                |
| `qml/src/qml/conformance/layer1.py`, `layer2.py`          | The gate into governed Book seats; 63.6% and 58.0% branch coverage                                                    |

---

## Appendix C: Knowledge Base References

- **Risk Governance**: `risk-governance.md` — P × I scoring, category taxonomy, mitigation ownership
- **Probability–Impact**: `probability-impact.md` — likelihood and damage calibration
- **Test Levels Framework**: `test-levels-framework.md` — level selection and the duplicate-coverage guard
- **Test Priorities Matrix**: `test-priorities-matrix.md` — P0–P3 criteria
- **NFR Criteria**: `nfr-criteria.md` — NFR category taxonomy and evidence planning
- **Test Quality**: `test-quality.md` — definition of done for a test

**Project sources of truth (the oracles):** `_bmad-output/planning-artifacts/epics.md`; `docs/contracts/ct-01..ct-34`; `docs/scenarios/SCN-0001..SCN-0012`; `docs/constitution.md`; `docs/decisions/ADR-0001..0018`; `conventions/failure-register.md`.

---

**Generated by:** BMad TEA Agent (Master Test Architect)
**Workflow:** `bmad-testarch-test-design` — system-level, create mode, headless
**Version:** 5.0 (BMad v6)
