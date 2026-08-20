---
id: LENS-BUG-TRIAGE
title: QMF Bug Triage
type: lens
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP, COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, COMP-OBJECT-STORAGE]
decisions: [DEC-0004, DEC-0007, DEC-0029, DEC-0030, DEC-0038, DEC-0044, DEC-0045, DEC-0046, DEC-0096, DEC-0099, DEC-0100, DEC-0101, DEC-0102, DEC-0103, DEC-0108, DEC-0109, DEC-0111, DEC-0112, DEC-0114, DEC-0117, DEC-0118, DEC-0119, DEC-0121, DEC-0136, DEC-0137, DEC-0138, DEC-0142]
sources: [_docwork/ledger.yaml, _docwork/gaps.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, docs/constitution.md, docs/architecture/dependencies.yaml, docs/registry/variables.yaml, docs/components/, docs/contracts/, docs/lenses/testing/test-strategy.md, docs/lenses/testing/fixtures-and-scenarios.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# QMF Bug Triage

No global severity tier, response-time target, or numeric impact threshold is ratified. The quality toolchain and gates that a fix runs against are ratified: ruff, pyright strict, and pytest, with `poe check` at tier 1, `poe check-integration` at tier 2 (contract tests, isolated per-package environments), and `poe check-release` at tier 3 (DEC-0101, DEC-0102). Two loud-failure invariants govern every bug: every public operation **returns** a typed refusal rather than raising across a package boundary (category, machine-readable context, retryability), and errors and refusals always carry context and are never swallowed (DEC-0109, DEC-0112). The triage, reproduction, regression, and closure scheme below records gaps instead of inventing priority or release rules.

## Loud-failure and typed-refusal invariants

A bug that surfaces a failure surfaces it through the ratified mechanisms, and triage checks them first (DEC-0109, DEC-0112):

- A public boundary returns a typed refusal as a result union; an exception crossing a package boundary is itself a defect (exceptions are reserved for programmer error). A store-library exception must be translated to a `storage failure` refusal at the qmf-data boundary, never propagated.
- The seven refusal categories are invalid input, unsupported capability, unavailable dependency, stale evidence, policy rejection, transient venue failure, and storage failure; a report that a wrong category was returned is a documented-behavior regression.
- A refusal or error that was swallowed, or that lost its context, is an authority-boundary/loud-failure defect regardless of any other symptom.
- A missing or non-propagated `correlation_id` across a package boundary, or a component with no working `health()`, is a defect against the observability convention.

## Proposed triage classes

A report takes one disposition after an authority check. The disposition runs against the ratified tiers and toolchain (DEC-0101, DEC-0102).

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
| Live command, execution, or reconciliation | CT-19 command identity, CT-20 observations, CT-13 journal chain, venue/session evidence | CT-19, CT-20, CT-21 | Venue command and uncertainty law ratified (DEC-0137, DEC-0138): an UNKNOWN outcome is a state, never a bug; a storage failure blocks the command pipe as a `storage failure` refusal; an unmapped venue code alarms and stays UNKNOWN. The command caller and flatten authority are node/risk territory, `GAP(GAP-0039)` (tracker/trading-node-notes.md, DEC-0142) |
| Risk, Book, mode, or same-tick action | CT-22 through CT-25 inputs/evidence without implementing the fenced policy | CT-22, CT-23, CT-24, CT-25 | `GAP(GAP-0039)` through `GAP(GAP-0046)`; FEAT-0027 remains specification/reconciliation only |
| Secret or session exposure | Affected boundary, redacted occurrence, session lifecycle facts; never the secret value | CT-21 | Secret lifecycle ratified (DEC-0136): components handle secret references never values, a `SecretValue` never renders its value, and expiry/refusal secret paths ship as tested behavior; store mechanics and key custody are node/ops-owned |
| Raw evidence, lineage, journal, or schema integrity | CT-09, CT-11, or CT-13 identity; prior and observed record; event-time and known-at; store outcome; a per-(writer, boot-epoch) journal sequence gap | CT-09, CT-11, CT-13 | Store stack, append-only lineage, N-stream journals, and migrations are ratified (DEC-0114, DEC-0117, DEC-0118, DEC-0119); a store-library exception must surface as a `storage failure` refusal (DEC-0109) |
| Backup, verification, or recovery | CT-26 input identity, CT-14 external result, and the exact unfulfilled claim; never assume snapshot completeness or restored identity | CT-14, CT-26 | Backup design ratified nightly/encrypted/off-machine (DEC-0118); `registry:backup_recovery_point_objective`, `registry:backup_recovery_time_objective`, and restore/cutover authority are node/ops-owned |
| Causality or final-holdout leakage | CT-08 event-time/known-at ingredients, CT-10 fact identity, CT-12 split identity, sealed-read refusal evidence | CT-08, CT-10, CT-12 | Seal enforced now as `policy rejection` (DEC-0119); the look-ahead gate `GAP(GAP-0016)` is deferred to the backtesting sitting (DEC-0121) |
| Contract identity or compatibility | CT-05 canonical `fp1` input, fingerprint, producer/consumer contract format version, observed compatibility result | CT-05 | Ratified: `fp1` recipe and format-version rules (DEC-0103, DEC-0108); floats are refused in identity content |
| Performance or capacity | Component, contract path, workload fixture, measured speed and peak memory, environment (OS, CPU-class) fingerprint | `registry:design_bot_concurrency` | Measure-then-budget ratified (DEC-0111); a numeric threshold exists only once its (OS, CPU-class) baseline is recorded |

An incident response or fix must not infer flatten authority, recovery priority, alert timing, or service target from urgency; those remain in their named GAPs or node/risk territory. Command retry is not among them — it is prohibited outright, retryability rides typed refusals, and retry/pool/health constants are node values under do-not-default (DEC-0137).

## Proposed reproduction record

The record is sufficient when another agent can execute one bounded case without private context, run under the ratified `poe check` gates (DEC-0101, DEC-0102).

| Proposed evidence | Proposed rule |
|---|---|
| Affected component | One or more `COMP-*` IDs from `docs/architecture/dependencies.yaml`. |
| Public boundary | The affected `CT-*` ID and direction; use the component FM ID when a documented failure mode applies. |
| Authority | Live `DEC-*`, `GAP-*`, registry keys, and FEAT ID; recommendations are not expected behavior. |
| Runtime context | Operating system (Windows 11 x86-64 or Ubuntu LTS x86-64), CPython 3.14, uv-workspace package/build identity, and dependency versions from `uv.lock` (DEC-0099, DEC-0100, DEC-0103). |
| Input | Fixture proof key and canonical fingerprint when CT-05 is available; attach source identity for external evidence. |
| Time | CT-02 clock/session context plus event and knowledge time when causality matters. |
| Observed result | Exact returned value/refusal, persisted evidence identity, journal/lineage references, and prohibited side effect if present. |
| Expected result | Exact CT, component FM Behavior, law, or registry reference; never a recommendation. |
| Determinism | Frozen clock, declared random seed, controlled replay, and number of reproductions without a percentage target. |
| Secrets | Redacted location and lifecycle facts only; no credential or token value. |

Fixture and replay construction could follow the proposal in [QMF Fixtures and Golden Scenarios](../testing/fixtures-and-scenarios.md). A bug that cannot yet be reproduced retains the evidence collected and the exact missing input or GAP; this proposal does not invent a closure result.

## Proposed triage workflow

The sequence runs against the ratified toolchain and tiers: pytest under `poe check` (tier 1), `poe check-integration` (tier 2, contract tests in isolated per-package environments), and `poe check-release` (tier 3) (DEC-0101, DEC-0102).

1. Preserve the original observation, journal/lineage references, source payload identity, event time, and knowledge time before attempting a fix (DEC-0038, DEC-0044, DEC-0045).
2. Resolve the affected COMP, CT, FM, DEC, GAP, registry, and FEAT IDs. If no documented authority exists, classify the report as an unresolved-contract case (DEC-0004).
3. Build the smallest deterministic reproduction through a public CT boundary. Unit reproductions use no network; external cases use a controlled replay or approved integration boundary (DEC-0007, DEC-0096).
4. Run the component FM test, CT round-trip/boundary suite, relevant law properties, and nearest cross-component integration test from [QMF Test Strategy](../testing/test-strategy.md).
5. Decide whether the correction preserves documented behavior or changes it. A behavior change enters documentation/change mode and receives the required new or superseding decision and ADR before implementation (DEC-0004, DEC-0030).
6. Implement the smallest owning-component fix. A store, adapter, or external component must not absorb a backend rule to shorten the fix.
7. Add the regression test, reference usage when the public contract changed, and evidence that all affected CT/FM/law tests pass (DEC-0096).
8. Re-run the ratified gates applicable to the change (`poe check`, and `poe check-integration` when a contract or cross-package path is touched), keep coverage at or above the 80% floor with 100% branch on any CT-01/CT-02 primitive module, and record the fixed revision plus regression evidence (DEC-0101, DEC-0102).

## Proposed regression-test rule

DEC-0096 and DEC-0101 make executable tests and reference usage tier-1 artifacts. The regression is a deterministic pytest case keyed by the bug record and CT, COMP/FM, and DEC/GAP authority, demonstrating the defective behavior before the correction and the documented result afterward, run under `poe check` (DEC-0101, DEC-0102). The exact proof-key format is documentation-time convention.

A fix that changes a public schema, enum, unit, nullability, version, compatibility result, authority boundary, state, or invariant is a documentation change before it is a code change (DEC-0004, DEC-0030). The change updates the ledger/ADR, CT contract, component spec, registry, feature inventory, test matrix, fixtures, and scenarios through change mode; triage never edits around those artifacts.

## Provisional closure guidance

Closure evidence includes a reproducible or explicitly evidence-limited record, authority IDs, owning component, fix or documented ruling, executable regression evidence passing the ratified gates, and updated reference usage when a public contract changes (DEC-0004, DEC-0096, DEC-0101, DEC-0102). A report blocked on an unresolved contract (risk gaps, or the deferred look-ahead gate) is not test-complete or releasable; no severity number, coverage percentage, verbal assurance, or GAP marker substitutes for a passing gate.
