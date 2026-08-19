---
id: PERF-BUDGETS-QMF-V1
title: QMF V1 Performance Budgets
type: lens
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP]
decisions: [DEC-0009, DEC-0030, DEC-0041, DEC-0045, DEC-0048, DEC-0056, DEC-0059, DEC-0065, DEC-0096, DEC-0097, DEC-0098]
sources: [DEC-0009, DEC-0030, DEC-0041, DEC-0045, DEC-0048, DEC-0056, DEC-0059, DEC-0065, DEC-0096, DEC-0097, DEC-0098, _docwork/gaps.yaml, docs/registry/variables.yaml, _docwork/feature_inventory.yaml, docs/contracts/ct-08-gate-evidence.yaml, docs/contracts/ct-09-registry-persistence.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-11-evidence-persistence.yaml, docs/contracts/ct-13-journal.yaml, docs/contracts/ct-14-backup-restore.yaml, docs/contracts/ct-16-indicator.yaml, docs/contracts/ct-17-causal-structure.yaml, docs/contracts/ct-18-venue-capabilities.yaml, docs/contracts/ct-19-venue-command.yaml, docs/contracts/ct-20-venue-event.yaml, docs/contracts/ct-23-risk-evaluation.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# QMF V1 Performance Budgets

QMF V1 has no ratified latency, throughput, memory, startup, storage, recovery, availability, or concurrency budget. `registry:design_bot_concurrency` preserves the source's ~40-Bot real-workload design case, but its value is null: the scenario is not an SLO, percentile, capacity guarantee, or benchmark pass threshold. [DEC-0098]

## Budget status

`GAP(GAP-0013): Ratify the benchmark scenario, environment, workload, measurement method, per-component and end-to-end budgets, and failure response before any performance claim is made.`

| Scope | Budget registry reference | Current status | Additional blockers |
|---|---|---|---|
| End-to-end QMF consumer path | `registry:design_bot_concurrency` | No value or SLO is ratified. | GAP-0013; no application runtime is in QMF V1. [DEC-0009] |
| qmf-core values and fingerprints | `registry:design_bot_concurrency` | No latency, allocation, or throughput budget is ratified. | GAP-0007 through GAP-0013. |
| qmf-registry registration, lineage, and gates | `registry:registry_attempt_scope`, `registry:registry_attempt_budget`, `registry:registry_attempt_reset_policy` | All values are null; no operation budget is ratified. | GAP-0014 through GAP-0017 and GAP-0021/GAP-0022. |
| qmf-data ingestion, access, journal, and persistence | `registry:local_store_engine`, `registry:raw_history_retention_policy` | Store engine and performance budgets are unratified. | GAP-0020 through GAP-0030. |
| qmf-data backup and restore | `registry:backup_recovery_point_objective`, `registry:backup_recovery_time_objective`, `registry:restore_verification_cadence` | All objective values are null. | GAP-0027. [DEC-0045] |
| qmf-indicators light path | `registry:canonical_indicator_reference` | Reference and execution budget are unratified. | GAP-0031, GAP-0032, and the nonblocking classification GAP-0033. [DEC-0056] |
| qmf-structure causal families | `registry:timestamp_precision` | No family, workload, or budget is ratified. | GAP-0034. |
| Reserved venue capability, command, event, and reconciliation shapes | `registry:venue_trendbar_price_basis` | CT-18 through CT-21 are unwired; no active path or performance source exists. | GAP-0035 through GAP-0039. [DEC-0059] |
| Reserved risk evaluation and Book-transition shapes | Risk registry keys in `docs/registry/variables.yaml` | CT-22 through CT-25 are unwired; no implementation or performance budget is authorized. | GAP-0039 through GAP-0046. [DEC-0065] |

## Measurement method

No benchmark runner, fixture corpus, clock source, environment, warm-up, sampling method, percentile set, sustained/burst definition, memory measure, startup definition, or baseline capture process is ratified. GAP-0013 must define them before an agent writes a benchmark.

Every eventual measurement must bind to a contract version, input fingerprint, environment identity, dataset/source identity, and evidence-time range after GAP-0012 and GAP-0013 are resolved. Incompatible semantic changes mint new versions rather than sharing a baseline. [DEC-0030] [DEC-0097]

## Baselines

No current baseline exists because no QMF implementation or ratified benchmark exists. Factory reference usage and executable tests are required evidence of contract behavior, but they are not performance baselines or SLOs. [DEC-0096]

The ~40-Bot source case must remain a design input through `registry:design_bot_concurrency`. It must not be rewritten as a measured percentile, supported maximum, concurrent-load guarantee, or release gate. [DEC-0098]

## Storage and recovery budgets

Retention, partitioning, compaction, and capacity remain GAP-0026. `registry:backup_cadence`, `registry:backup_recovery_point_objective`, `registry:backup_recovery_time_objective`, `registry:backup_retention_period`, and `registry:restore_verification_cadence` are non-authoritative while GAP-0027 remains open; no cadence, completion rule, validation rule, or recovery objective is adopted. [DEC-0045]

## Exceeding a future budget

No automatic response is ratified. A future budget breach may become CT-13 evidence after its event schema and threshold are defined; CT-25 is an unwired placeholder and cannot be assumed as an evidence path. No breach can authorize promotion, order rejection, retry, flattening, exit, Book transition, restore, or external-provider action. [DEC-0041] [DEC-0048]

Venue outage and flattening authority remain GAP-0036. Exit ownership remains GAP-0040. Paper-mode behavior remains GAP-0041. Same-tick priority remains GAP-0046. No performance test may fill those authority gaps. [DEC-0065]

## Acceptance gate

A performance budget is valid only when its numeric value exists in `docs/registry/variables.yaml`, its measurement method is executable, its workload and environment are identified, its emitting contract is versioned, and its breach response is ratified. Until GAP-0013 is answered, every QMF performance statement remains a design constraint without a pass/fail threshold. [DEC-0096] [DEC-0098]
