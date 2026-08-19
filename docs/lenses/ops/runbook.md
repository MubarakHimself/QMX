---
id: OPS-RUNBOOK-QMF-V1
title: QMF V1 Operations Runbook
type: runbook
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP, COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, COMP-OBJECT-STORAGE]
decisions: [DEC-0001, DEC-0003, DEC-0004, DEC-0005, DEC-0008, DEC-0009, DEC-0030, DEC-0041, DEC-0045, DEC-0051, DEC-0052, DEC-0053, DEC-0059, DEC-0065, DEC-0096]
sources: [DEC-0001, DEC-0003, DEC-0004, DEC-0005, DEC-0008, DEC-0009, DEC-0030, DEC-0041, DEC-0045, DEC-0051, DEC-0052, DEC-0053, DEC-0059, DEC-0065, DEC-0096, _docwork/gaps.yaml, docs/architecture/dependencies.yaml, docs/registry/variables.yaml, docs/contracts/ct-09-registry-persistence.yaml, docs/contracts/ct-11-evidence-persistence.yaml, docs/contracts/ct-13-journal.yaml, docs/contracts/ct-14-backup-restore.yaml, docs/contracts/ct-15-external-source-adapter.yaml, docs/contracts/ct-19-venue-command.yaml, docs/contracts/ct-20-venue-event.yaml, docs/contracts/ct-21-venue-secret-session.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# QMF V1 Operations Runbook

QMF V1 is design-only and has no ratified start, stop, restart, deploy, migration, rollback, or live-connection command. QMF is a reusable toolbox rather than an application runtime; this document records operational boundaries and the decisions still required before executable procedures can exist. [DEC-0008] [DEC-0009]

## Permission boundary

This runbook grants no permission to initialize the project, deploy code, access credentials, connect to a broker, submit an order, promote an artifact, change a Book mode, flatten exposure, or operate live money. Project initialization remains with operator tooling, and promotion into the live zone remains human-only. [DEC-0005] [DEC-0041]

Agents may inspect documented contracts, run already-approved read-only validation, and preserve evidence. Agents may not infer an operational command from a recommendation, a GAP, a study, or an external provider's examples. [DEC-0003] [DEC-0004]

## Environments and commands

| Operational need | Current procedure | Blocking definition |
|---|---|---|
| Supported runtime and host | No executable procedure is ratified. | `GAP(GAP-0001): Select the CPython minor, OS versions, and architectures.` |
| Workspace installation | No package/install command is ratified. | `GAP(GAP-0002): Select repository layout, build backend, dependency manager, and lockfile policy.` |
| Local validation | No canonical command suite is ratified. Factory-built components must eventually ship executable tests and reference usage. [DEC-0096] | `GAP(GAP-0003): Select formatter, linter, type checker, test runner, coverage rule, and commands.` |
| CI validation and release | No pipeline or release command is ratified. | `GAP(GAP-0004): Define PR, merge, and release tiers.` `GAP(GAP-0005): Define release, compatibility, and deprecation policy.` |
| Start, stop, and restart | No QMF-wide operation exists because libraries do not form a runtime. Any future process-specific command belongs to its owning application or process. [DEC-0008] [DEC-0009] | `GAP(GAP-0002): Define package and executable boundaries before commands are documented.` |
| Deploy or rollback | No deploy target, artifact, command, rollback rule, or environment is ratified. | `GAP(GAP-0004): Define release gates.` `GAP(GAP-0022): Define schema migration and rollback.` |

## Operational units

| Unit | What can be operated | What remains prohibited or unresolved |
|---|---|---|
| QMF libraries | Installed and invoked only after their package and contract gaps are ratified. | No application loop, scheduler, deployment service, or QMF-wide daemon exists. [DEC-0008] [DEC-0009] |
| `COMP-QMF-DATA-INGEST` | A bounded adapter invocation after source contracts are ratified. | Scheduling, process supervision, retries, and bulk acquisition remain application-owned and unresolved under GAP-0028 through GAP-0030. [DEC-0051] [DEC-0053] |
| Standalone calendar recorder | A separate future application invokes a bounded Data-Ingest operation; Data-Ingest owns and calls CT-15 against the Calendar provider, then produces governed CT-10 input to Data. The application does not consume CT-15 directly. | The application-facing call, provider, schedule, retry, legal-retention, and command procedure are unratified. `GAP(GAP-0028)` `GAP(GAP-0029)` [DEC-0052] |
| `COMP-QMF-DATA-STORE` | Physical persistence only after engines, schemas, and migrations are ratified. | No store engine, path, schema, migration, compaction, or recovery procedure may be invented. `GAP(GAP-0021)` `GAP(GAP-0022)` `GAP(GAP-0026)` |
| `COMP-QMF-DATA-BACKUP` | Contract and provider-boundary design only. | `registry:backup_cadence` is non-authoritative while GAP-0027 is open; provider, credentials, encryption, retention, RPO, RTO, completion evidence, and restore validation remain unresolved. [DEC-0045] |
| `COMP-QMF-VENUE` | Reserved CT-18 through CT-21 shapes only. | CT-18/CT-20 have no active consumers, CT-19 has no caller or authorization evidence, and CT-21 is a credential no-operation gate. No connection, command, retry, reconciliation, flatten action, or deployment is authorized. `GAP(GAP-0035)` through `GAP(GAP-0039)` [DEC-0059] |
| `COMP-QMF-RISK` | Fenced reconciliation and reserved CT-22 through CT-25 shapes only. | The contracts have no active caller or consumer; CT-24 is evidence-only pending operator confirmation and CT-25 is not wired to Data. No risk evaluation, order authorization, exit action, Book transition, or live operation is implementation-ready. `GAP(GAP-0039)` through `GAP(GAP-0046)` [DEC-0065] |

## Scheduled work

| Work | Schedule source | Operator boundary |
|---|---|---|
| Off-machine evidence backup | `registry:backup_cadence` is a non-authoritative registry reference | GAP-0027 must ratify cadence, invocation, scheduler, completion evidence, and restore validation before any schedule exists. [DEC-0045] |
| Historical backfill | No recurring schedule is ratified. | Bulk acquisition is a first-install/operator action after GAP-0028 and GAP-0030 are resolved. [DEC-0051] [DEC-0053] |
| Economic-calendar recording | No registry schedule is ratified. | The standalone recorder's provider, schedule, and retries remain `GAP(GAP-0029)`. [DEC-0052] |
| Forward broker capture | No schedule or supervisor is ratified. | Broker access and the safe account boundary remain `GAP(GAP-0035)` through `GAP(GAP-0038)`. [DEC-0053] [DEC-0059] |

## Secrets handling

No secret location, injection command, storage rule, redaction rule, rotation procedure, or incident authority is ratified. The interim rule is a no-operation gate: no broker credential-bearing integration proceeds until GAP-0035 is ratified. This runbook does not adopt the gap recommendation as settled design. [DEC-0059]

Object-storage credentials and encryption remain `GAP(GAP-0027)`. Calendar and historical-provider access or legal conditions remain `GAP(GAP-0029)` and `GAP(GAP-0030)`. No credential-bearing operation is authorized at any of these boundaries.

## Data migration, backup, and restore

Schema changes must not run until explicit versions, preflight behavior, backup requirements, migration direction, verification, rollback, and restore are ratified. `GAP(GAP-0022)` [DEC-0030]

CT-14 reserves transfer and restore evidence, but no completion rule, validation procedure, restore command, RPO, RTO, or verification cadence is ratified. The registry references `registry:backup_recovery_point_objective`, `registry:backup_recovery_time_objective`, and `registry:restore_verification_cadence` remain governed by GAP-0027 and authorize no destructive restore action. [DEC-0045]

## Pre-operation checklist

An operator must stop before mutation when any required item is unresolved:

- Runtime, package, dependency, and release definitions: GAP-0001 through GAP-0006.
- Exact core value, time, identity, refusal, and fingerprint contracts: GAP-0007 through GAP-0012.
- Store, schema, migration, retention, and restore contracts: GAP-0021, GAP-0022, GAP-0026, and GAP-0027.
- External-source provider, mapping, legal, and reconciliation contracts: GAP-0028 through GAP-0030.
- Venue credentials, order-state, account, and capability contracts: GAP-0035 through GAP-0038.
- Book, BMS, exit, paper-mode, news, SQS, formula, stop-out, and priority contracts: GAP-0039 through GAP-0046.
- Human authorization for promotion or any live-money boundary. [DEC-0041]

## Incident handoff

Operational failures route to [OPS-INCIDENT-QMF-V1](incident-playbook.md). No failure grants an agent implicit authority to promote, trade, flatten, rotate credentials, restore data, or override a Book. [DEC-0001] [DEC-0041]
