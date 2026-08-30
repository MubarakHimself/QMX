---
title: 'TEA Test Design → BMAD Handoff Document'
version: '1.0'
workflowType: 'testarch-test-design-handoff'
inputDocuments:
  - _bmad-output/test-artifacts/test-design-architecture.md
  - _bmad-output/test-artifacts/test-design-qa.md
  - _bmad-output/planning-artifacts/epics.md
sourceWorkflow: 'testarch-test-design'
generatedBy: 'TEA Master Test Architect'
generatedAt: '2026-08-27'
projectName: 'QMX'
---

# TEA → BMAD Integration Handoff

## Purpose

This document bridges TEA's system-level test design with the downstream lanes that will act on it. **QMX inverts the usual direction:** the epics and stories already exist and are built and merged (`integration@2c8d495`), so this handoff does not feed `create-epics-and-stories` with quality requirements for work not yet done. It feeds the **independent verification phase** and, after it, the **fix-card backlog** that the factory lanes (attended epic-factory, or `/queue-publish` + to-kanban cards) will consume.

Read that inversion into every section below: "Story-Level Guidance" means "what the per-epic verification lane must assert", and "Risk-to-Story Mapping" means "which epic lane owns which risk".

## TEA Artifacts Inventory

| Artifact                   | Path                                                       | Downstream Integration Point                                                       |
| -------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Architecture test design    | `_bmad-output/test-artifacts/test-design-architecture.md`   | Architecture/operator decisions; the three blockers; the 21-risk register; NFR gaps    |
| QA test design              | `_bmad-output/test-artifacts/test-design-qa.md`             | The execution recipe: test levels, ranked epics, per-epic template, traceability, exit criteria |
| Risk assessment             | (in the architecture doc)                                   | Epic tiering; fix-card priority                                                        |
| Coverage strategy           | (in the QA doc)                                             | Per-epic verification lane scope                                                       |
| Per-epic plan template      | (QA doc, "Per-Epic Test Plan Template")                     | Each lane writes `qa/epics/epic_NN_<slug>/PLAN.md` from it                              |
| Proof map (to be generated) | `qa/_trace/proof_map.md`                                    | The operator handoff artifact; the phase's verdict                                     |
| Findings inventory (to be generated) | `qa/_trace/findings.csv`                          | Source for every fix card                                                              |
| Progress checkpoint         | `_bmad-output/test-artifacts/test-design-progress-system.md` | Workflow resume state (runKey `system`)                                                |

## Epic-Level Integration Guidance

### Risk References — risks that must appear as quality gates on their owning lane

| Risk  | Score | Owning epic lane(s)          | Gate the lane must satisfy                                                       |
| ----- | ----- | ---------------------------- | ---------------------------------------------------------------------------------- |
| R-001 | 9     | E1, E10, E21, E22            | Mixed unit-kind or currency refuses everywhere on the money path                    |
| R-002 | 9     | all ten distribution units   | No public callable raises; value or typed refusal always                             |
| R-003 | 9     | every lane                   | Section 5 existing-test audit complete; every "contradicts" row in the inventory     |
| R-004 | 6     | E1, E13, E20, E23            | Distinct semantic inputs ⇒ distinct fp1; no silent overwrite                          |
| R-005 | 6     | phase entry (all)            | The L0 baseline sweep ran and its output is an artifact                              |
| R-006 | 6     | E16, E23                     | Every capability reachable from every door; parity derived, not declared             |
| R-007 | 6     | E3, E6, E18, E23             | Adversarial input refuses rather than returning `Ok`                                 |
| R-008 | 6     | E13, E23                     | Every accepted input shape yields the same gate verdict                              |
| R-009 | 6     | E8, E10, E11, E12, E15, E4   | Every door-reachable typed refusal has a register entry                              |
| R-010 | 6     | E15, E20, E21                | Exactly one ledger line per run across the whole abort/cancel/teardown matrix        |
| R-011 | 6     | E11, E12, E15, E17, E18      | Branch behaviour asserted by requirement, not by line-chasing                        |
| R-012 | 6     | E3                           | Seal, split and world refusals hold at every enumerated read path                    |

### Quality Gates per epic tier

| Tier   | Epics                                            | Gate to enter the fix lane                                                                                     |
| ------ | ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| **T1** | E10, E1, E8, E3, E2, E13, E14                    | Full L1+L2+L3+L4 suite authored and run; mutation targets on the roster; L6 review complete; every owned requirement has a non-blank proof-map row |
| **T2** | E15, E12, E11, E18, E16, E17, E6, E5             | L2 + L3 for every AC, targeted L1 properties, L6 review; every P0/P1 requirement has a proof-map row              |
| **T3** | E19, E22, E21, E23, E20, E9, E7                  | L3 for P0/P1 ACs + a regression pin per confirmed advisory finding; L6 review                                     |
| **T4** | E4                                               | L2 contract spot-check + L4 scenario participation                                                               |

## Story-Level Integration Guidance

### P0/P1 scenarios that every verification lane must assert

These are the assertions no lane may skip, expressed as they would read in an acceptance criterion:

1. **No float ever reaches the money path**, and every money, price and quantity value is an exact scaled integer at a declared scale (FR-001, CT-01, AR-15).
2. **Mixing unit kinds or currencies refuses.** A comparison, aggregation or conversion across dimensions never returns `Ok` (FR-001, CT-01) — the single highest-value assertion in the whole plan.
3. **No public boundary raises.** Every public callable returns a value or a typed refusal; exceptions are reserved for programmer error (FR-004, CT-04, AR-13).
4. **Distinct semantic inputs produce distinct fingerprints**, and no artifact silently overwrites another (FR-005, CT-05, AR-52).
5. **No path reaches live money without a recorded human promotion** attesting the record's fp1 (FR-009, L17, AR-39, SCN-0007).
6. **The sealed holdout is excluded at every boundary**, not at the boundary the author had in mind (FR-012, CT-12, L19, SCN-0003).
7. **Cross-world reads refuse, and `world=simulated` refuses** (FR-011, CT-11, L18, AR-33).
8. **Every trade intent passes the Book's charter doors**, with R frozen at admission and a declared full-loss price required (FR-027, FR-028, CT-22, CT-23).
9. **No control ever blocks a risk-reducing act** (FR-033, CT-30, L39).
10. **A venue UNKNOWN is a state, not an error**, and it blocks its `(venue, account)` command stream until explicit reconciliation while market data keeps flowing (FR-023, CT-19, L35, SCN-0005).
11. **Exactly one ledger line per run — never zero, never two** — including on every failure path (FR-045, AR-51).
12. **Every capability is reachable from every door**, with refusals rendered per transport (FR-046, AR-58).
13. **Re-running a run id under its resolved config reproduces the CT-32 fingerprint or refuses** (NFR-03, AR-58).
14. **The Bot kind mints only after both conformance layers pass** (FR-048, AR-64).
15. **Every designed failure mode has a register entry** written for someone who was not in the design room (NFR-11).

### Testability Requirements for the fix lane

When a fix card is picked up, the lane must also deliver the testability change that made the defect invisible, not only the defect fix:

- Dimension parameters (`unit_kind`, `currency`) required and refusal-bearing on shared numeric primitives.
- Bound-and-check before conversion at every named conversion boundary.
- Duplicate-fingerprint detection at fan-out admission.
- Governance gates evaluated after normalization, through a single entry point.
- Ledger writes as a `finally`-class obligation, not a happy-path step.
- Door parity derived from the door surfaces.
- A `FAILURES.md` in every distribution unit.
- Committed golden-run corpus and fingerprinted benchmark baselines.

## Risk-to-Story Mapping

| Risk ID | Category | P×I | Owning epic lane(s)                          | Test Level    |
| ------- | -------- | --- | -------------------------------------------- | ------------- |
| R-001   | DATA     | 9   | E1 (property), E10, E21, E22                 | L1 + L5       |
| R-002   | TECH     | 9   | E1 (property), all units (enumeration)       | L1            |
| R-003   | TECH     | 9   | every lane (section 5 audit) + L6 seats      | L5 + L6       |
| R-004   | DATA     | 6   | E1, E13, E20, E23                            | L1 + L3       |
| R-005   | OPS      | 6   | phase entry                                  | L0            |
| R-006   | BUS      | 6   | E16, E23                                     | L3            |
| R-007   | DATA     | 6   | E3, E6, E18, E23                             | L3            |
| R-008   | TECH     | 6   | E13, E23                                     | L3            |
| R-009   | OPS      | 6   | E8, E10, E11, E12, E15, E4                   | L3            |
| R-010   | DATA     | 6   | E15, E20, E21                                | L3            |
| R-011   | TECH     | 6   | E11, E12, E15, E17, E18                      | L3            |
| R-012   | DATA     | 6   | E3                                           | L3            |
| R-013   | PERF     | 4   | E21                                          | L3            |
| R-014   | OPS      | 4   | all (nightly benchmarks)                     | L0            |
| R-015   | TECH     | 4   | contract lane (CT-01..CT-34)                 | L2            |
| R-016   | TECH     | 4   | E14, E19                                     | L4            |
| R-017   | PERF     | 4   | E15                                          | L3            |
| R-018   | BUS      | 4   | E9, E14                                      | L1            |
| R-019   | SEC      | 2   | E1, E8                                       | L1            |
| R-020   | OPS      | 2   | phase entry                                  | L0            |
| R-021   | OPS      | 2   | E15 (quarantine list)                        | burn-in       |

## Recommended Workflow Sequence for QMX

BMad is planning-only in this project and implementation ships through the factory. The sequence this handoff feeds:

1. **TEA Test Design** (this document) → the plan, the tiering, the template, the traceability scheme.
2. **Operator decisions** → the three blockers (B-1 gate reconciliation, B-2 `qa/` isolation, B-3 parity derivation).
3. **L0 baseline sweep** → full `poe check` / `check-integration` captured as evidence.
4. **Per-epic verification fan-out** → one lane per epic, each producing `qa/epics/epic_NN_<slug>/PLAN.md` plus its tests, following the per-epic template.
5. **Consolidation** → findings inventory, fix-card backlog, proof map delivered to the operator.
6. **Operator triage** → which fix cards ship, in what order.
7. **Factory lanes** → attended epic-factory or `/queue-publish` + to-kanban cards execute the fix cards. `main` moves only by the operator's own squash-merge click.

`bmad-testarch-trace` may be run afterwards over the completed `qa/_trace/trace.yaml` if a second, independent coverage verdict is wanted; it is not required by this plan, which generates its own proof map.

## Phase Transition Quality Gates

| From Phase                | To Phase                     | Gate Criteria                                                                                                    |
| ------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Test Design               | Verification fan-out         | Blockers B-1/B-2/B-3 answered; `qa/` tree and collection guards live; L0 baseline captured                          |
| Verification fan-out      | Consolidation                | Every T1/T2 epic suite authored and run; every epic has an eight-section `PLAN.md` and a completed L6 review seat    |
| Consolidation             | Operator triage              | Findings inventory, fix-card backlog and proof map all exist; no code outside `qa/` modified                        |
| Operator triage           | Factory fix lanes            | Cards selected by the operator; each names its requirement id and the independent test that proves the restoration  |
| Factory fix lanes         | Re-verification              | The named independent test moves from FAILING to PROVEN in the proof map without being edited to suit the fix       |
| Re-verification           | Ship consideration           | Every score-9 risk mitigated; every P0 requirement PROVEN or explicitly accepted by the operator with a reason      |
