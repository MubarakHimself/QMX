---
id: LENS-BUG-TRIAGE
title: QMF Bug Triage
type: lens
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP, COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, COMP-OBJECT-STORAGE]
decisions: [DEC-0004, DEC-0007, DEC-0029, DEC-0030, DEC-0038, DEC-0044, DEC-0045, DEC-0046, DEC-0096]
sources: [_docwork/ledger.yaml, _docwork/gaps.yaml, docs/constitution.md, docs/architecture/dependencies.yaml, docs/registry/variables.yaml, docs/components/, docs/contracts/, docs/lenses/testing/test-strategy.md, docs/lenses/testing/fixtures-and-scenarios.md]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# QMF Bug Triage

No global severity tier, response-time target, numeric impact threshold, disposition taxonomy, proof-key format, or closure gate is ratified. DEC-0096 requires executable tests and reference usage at a high level; the detailed triage, reproduction, regression, and closure scheme below is proposed under `GAP(GAP-0003)` and `GAP(GAP-0004)`. It records gaps instead of inventing priority or release rules.

## Proposed triage classes

One possible scheme assigns a report one disposition after an authority check. The classes and cardinality are not mandatory until `GAP(GAP-0003)` and `GAP(GAP-0004)` are resolved.

| Class | Condition | Proposed action |
|---|---|---|
| Documented-behavior regression | Implementation or generated artifact contradicts a live DEC, CT, component behavior, FM row, or registry value | Reproduce, add the failing regression test, fix without changing documented meaning, and retain evidence (DEC-0004, DEC-0096). |
| Authority-boundary violation | A component performs an action prohibited by its `May never` boundary or a CT invariant | Contain the prohibited action, prove the boundary with a property/structural test, and fix through the owning component (DEC-0004, DEC-0096). |
| Unresolved-contract case | Expected behavior depends on an open GAP, null registry value, conflict, or fenced risk contract | Do not guess in code; attach the GAP/contract and route the decision through documentation before implementation (DEC-0004). |
| External-dependency incident | QMF receives an outage, malformed payload, rate limit, credential/session failure, or contradictory result from an external component | Preserve the external evidence, reproduce through the QMF adapter boundary, and change only QMF-owned behavior unless the provider facts change. |
| Documentation or traceability defect | A DEC/GAP/CT/COMP/FEAT reference is missing, contradictory, stale, or cannot lead an agent to an executable test | Correct documentation first, run citation/lint/registry/inventory gates, and add a regression check when the defect is machine-detectable (DEC-0004, DEC-0096). |

## Impact evidence without invented severity

Triage records the affected domain and the evidence in this table. It does not map the row to an ordinal severity or response target until the named design inputs are ratified.

| Impact domain | Evidence to capture | Authority | Missing target or behavior |
|---|---|---|---|
| Live command, execution, or reconciliation | CT-19 command identity, CT-20 observations, CT-13 journal chain, venue/session evidence | CT-19, CT-20, CT-21 | `GAP(GAP-0035)`, `GAP(GAP-0036)`, `GAP(GAP-0037)`, `GAP(GAP-0038)` |
| Risk, Book, mode, or same-tick action | CT-22 through CT-25 inputs/evidence without implementing the fenced policy | CT-22, CT-23, CT-24, CT-25 | `GAP(GAP-0039)` through `GAP(GAP-0046)`; FEAT-0027 remains specification/reconciliation only |
| Secret or session exposure | Affected boundary, redacted occurrence, session lifecycle facts; never the secret value | CT-21 | `GAP(GAP-0035)`, `GAP(GAP-0036)` |
| Raw evidence, lineage, journal, or schema integrity | CT-09, CT-11, or CT-13 identity; prior and observed record; event and knowledge time; store outcome | CT-09, CT-11, CT-13 | `GAP(GAP-0015)`, `GAP(GAP-0021)`, `GAP(GAP-0022)`, `GAP(GAP-0023)`, `GAP(GAP-0025)`, `GAP(GAP-0026)`; CT-13 mutation semantics are unresolved |
| Backup, verification, or recovery | CT-26 input identity when defined, CT-14 external result when defined, and the exact unfulfilled claim; never assume snapshot completeness or restored identity | CT-14, CT-26 | `registry:backup_cadence`, `registry:backup_recovery_point_objective`, `registry:backup_recovery_time_objective`, `GAP(GAP-0020)`, `GAP(GAP-0022)`, `GAP(GAP-0026)`, `GAP(GAP-0027)`; recovery/cutover is non-operational |
| Causality or final-holdout leakage | CT-08 gate evidence, CT-10 event/knowledge time, CT-12 release/split identity, access evidence | CT-08, CT-10, CT-12 | `GAP(GAP-0016)`, `GAP(GAP-0024)` |
| Contract identity or compatibility | CT-05 canonical input, fingerprint, producer/consumer version, observed compatibility result | CT-05 | `GAP(GAP-0005)`, `GAP(GAP-0010)`, `GAP(GAP-0012)` |
| Performance or capacity | Component, contract path, workload fixture, measured result, environment fingerprint | `registry:design_bot_concurrency` | `GAP(GAP-0013)`; no latency, throughput, memory, startup, or persistence threshold is ratified |

An incident response or fix must not infer flatten authority, retry limits, recovery priority, alert timing, or service target from urgency. Those behaviors remain in their named GAPs.

## Proposed reproduction record

The proposed record is sufficient when another agent can execute one bounded case without private context. Its fields and gate remain subject to `GAP(GAP-0003)` and `GAP(GAP-0004)`.

| Proposed evidence | Proposed rule |
|---|---|
| Affected component | One or more `COMP-*` IDs from `docs/architecture/dependencies.yaml`. |
| Public boundary | The affected `CT-*` ID and direction; use the component FM ID when a documented failure mode applies. |
| Authority | Live `DEC-*`, `GAP-*`, registry keys, and FEAT ID; recommendations are not expected behavior. |
| Runtime context | Operating system, runtime, package/build identity, and dependency versions once `GAP(GAP-0001)`, `GAP(GAP-0002)`, and `GAP(GAP-0005)` are answered. |
| Input | Fixture proof key and canonical fingerprint when CT-05 is available; attach source identity for external evidence. |
| Time | CT-02 clock/session context plus event and knowledge time when causality matters. |
| Observed result | Exact returned value/refusal, persisted evidence identity, journal/lineage references, and prohibited side effect if present. |
| Expected result | Exact CT, component FM Behavior, law, or registry reference; never a recommendation. |
| Determinism | Frozen clock, declared random seed, controlled replay, and number of reproductions without a percentage target. |
| Secrets | Redacted location and lifecycle facts only; no credential or token value. |

Fixture and replay construction could follow the proposal in [QMF Fixtures and Golden Scenarios](../testing/fixtures-and-scenarios.md). A bug that cannot yet be reproduced retains the evidence collected and the exact missing input or GAP; this proposal does not invent a closure result.

## Proposed triage workflow

This is a candidate sequence, not an adopted operational or release gate. Steps that require a runner, proof suite, or closure command remain blocked by `GAP(GAP-0003)` and `GAP(GAP-0004)`.

1. Preserve the original observation, journal/lineage references, source payload identity, event time, and knowledge time before attempting a fix (DEC-0038, DEC-0044, DEC-0045).
2. Resolve the affected COMP, CT, FM, DEC, GAP, registry, and FEAT IDs. If no documented authority exists, classify the report as an unresolved-contract case (DEC-0004).
3. Build the smallest deterministic reproduction through a public CT boundary. Unit reproductions use no network; external cases use a controlled replay or approved integration boundary (DEC-0007, DEC-0096).
4. Run the component FM test, CT round-trip/boundary suite, relevant law properties, and nearest cross-component integration test from [QMF Test Strategy](../testing/test-strategy.md).
5. Decide whether the correction preserves documented behavior or changes it. A behavior change enters documentation/change mode and receives the required new or superseding decision and ADR before implementation (DEC-0004, DEC-0030).
6. Implement the smallest owning-component fix. A store, adapter, or external component must not absorb a backend rule to shorten the fix.
7. Add the regression test, reference usage when the public contract changed, and evidence that all affected CT/FM/law tests pass (DEC-0096).
8. Re-run the adopted gates applicable to the change once they exist, and record the fixed revision plus regression evidence; the exact closure decision remains GAP-bound.

## Proposed regression-test rule

DEC-0096 requires executable tests and reference usage, but it does not ratify this key format or closure test. Proposed practice is a deterministic regression keyed by the bug record and CT, COMP/FM, and DEC/GAP authority, demonstrating the defective behavior before the correction and the documented result afterward. The exact runner, command, proof requirements, and release gate remain `GAP(GAP-0003)` and `GAP(GAP-0004)`.

A fix that changes a public schema, enum, unit, nullability, version, compatibility result, authority boundary, state, or invariant is a documentation change before it is a code change (DEC-0004, DEC-0030). The change updates the ledger/ADR, CT contract, component spec, registry, feature inventory, test matrix, fixtures, and scenarios through change mode; triage never edits around those artifacts.

## Provisional closure guidance

Proposed closure evidence includes a reproducible or explicitly evidence-limited record, authority IDs, owning component, fix or documented ruling, executable regression evidence, and updated reference usage when a public contract changes (DEC-0004, DEC-0096). The exact closure and release gate remains `GAP(GAP-0003)` and `GAP(GAP-0004)`. A report blocked on unresolved contract behavior is not test-complete or releasable; no severity number, coverage percentage, verbal assurance, or GAP marker substitutes for a passing adopted gate.
