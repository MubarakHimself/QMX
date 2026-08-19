---
id: OBS-METRICS-QMF-V1
title: QMF V1 Metrics and Alerts
type: lens
status: provisional
depends_on: [COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP]
decisions: [DEC-0038, DEC-0041, DEC-0045, DEC-0048, DEC-0055, DEC-0058, DEC-0059, DEC-0065, DEC-0072, DEC-0074, DEC-0096, DEC-0098]
sources: [DEC-0038, DEC-0041, DEC-0045, DEC-0048, DEC-0055, DEC-0058, DEC-0059, DEC-0065, DEC-0072, DEC-0074, DEC-0096, DEC-0098, _docwork/gaps.yaml, docs/registry/variables.yaml, docs/contracts/ct-08-gate-evidence.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-13-journal.yaml, docs/contracts/ct-14-backup-restore.yaml, docs/contracts/ct-16-indicator.yaml, docs/contracts/ct-17-causal-structure.yaml, docs/contracts/ct-18-venue-capabilities.yaml, docs/contracts/ct-19-venue-command.yaml, docs/contracts/ct-20-venue-event.yaml, docs/contracts/ct-21-venue-secret-session.yaml, docs/contracts/ct-23-risk-evaluation.yaml, docs/contracts/ct-24-book-mode.yaml, docs/contracts/ct-25-risk-journal.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# QMF V1 Metrics and Alerts

QMF V1 has no ratified metrics schema, aggregation window, dashboard, alert threshold, severity tier, notification destination, paging route, or automatic remediation. This document identifies source-backed measurement subjects and the registry/GAP that must define each one before an alert can exist. [DEC-0048] [DEC-0098]

## Measurement subjects

| Subject | Evidence source | Registry reference | Unresolved definition |
|---|---|---|---|
| Real-workload concurrency | Component benchmark evidence | `registry:design_bot_concurrency` | Value is null. `GAP(GAP-0013): Define benchmark scenario, latency, throughput, memory, startup, persistence, and recovery budgets.` [DEC-0098] |
| Registry gate and attempt outcomes | CT-08 | `registry:registry_attempt_scope`, `registry:registry_attempt_budget`, `registry:registry_attempt_reset_policy` | All values are null. Claim, outcome, scope, budget, reset, and metric aggregation remain GAP-0016 and GAP-0017. |
| Source ingestion quality | CT-10 owned/provided by COMP-QMF-DATA; CT-15 source edge | — | Data-Ingest and Venue may produce CT-10 into Data, but downstream components consume it from Data. Fields, duplicate/gap rules, quality flags, legal posture, and cadence remain GAP-0023 and GAP-0028 through GAP-0030. |
| Data-store capacity and durability | CT-09, CT-11, CT-13 | `registry:local_store_engine`, `registry:raw_history_retention_policy` | Engine is null; schema, partition, compaction, capacity, and retention measurements remain GAP-0021, GAP-0022, GAP-0025, and GAP-0026. |
| Backup freshness and recoverability | CT-14 owned by COMP-QMF-DATA-BACKUP | `registry:backup_cadence`, `registry:backup_recovery_point_objective`, `registry:backup_recovery_time_objective`, `registry:backup_retention_period`, `registry:restore_verification_cadence` | Every reference is non-authoritative while GAP-0027 remains open; cadence, completion, validation, objectives, retention, and alert thresholds are not adopted. [DEC-0045] |
| Indicator readiness and conformance | CT-16 | `registry:canonical_indicator_reference` | Reference, warm-up, readiness, state, tolerances, and measurement rules remain GAP-0031 and GAP-0032. [DEC-0055] |
| Structure causality and invalidation | CT-17 and CT-08 | — | Family, confirmation, invalidation, output, and measurement rules remain GAP-0034. [DEC-0058] |
| Venue session and reconciliation | CT-18 through CT-21 reserved/unwired | `registry:venue_trendbar_price_basis` | No active measurement source exists. Caller, authorization evidence, command states, retries, reconciliation, price basis, consumers, and thresholds remain GAP-0035 through GAP-0039. [DEC-0059] |
| SQS | CT-23/CT-25 reserved/unwired placeholders | `registry:spread_quality_sensor_formula` | No active measurement source exists; formula, units, inputs, thresholds, cadence, hysteresis, stale behavior, and alert meaning remain GAP-0043. [DEC-0074] [DEC-0075] |
| News control | CT-25 reserved and not wired to Data | `registry:news_blackout_before`, `registry:news_blackout_after` | Values are null; severity, mapping, windows, overrides, consumer, and alert behavior remain GAP-0042. [DEC-0072] |
| Stop-out and bench state | CT-23/CT-25 reserved/unwired placeholders | `registry:bench_stopout_threshold`, `registry:bench_reset_boundary` | Values are null and no active source exists; stop-out, names, benchmark, reset, and alert meaning remain GAP-0045. [DEC-0094] |

## Dashboard status

No dashboard is specified. No metric name, unit, label set, aggregation, sampling interval, storage backend, panel, query, or baseline may be invented from the measurement-subject table.

`GAP(GAP-0013): Define the performance measurement method and numeric budgets before performance panels exist.`

`GAP(GAP-0025): Define event fields and cadence before evidence-derived panels exist.`

`GAP(GAP-0026): Define retention and capacity before a metrics store or query horizon exists.`

## Alert status

No alert may be implemented because no threshold or severity model is ratified. A registry key with a null value is not an implicit default.

| Alert domain | Threshold source | Severity/notification | Automatic action |
|---|---|---|---|
| Performance | `registry:design_bot_concurrency` plus future GAP-0013 budgets | Unratified. | None authorized. |
| Backup/restore | RPO, RTO, retention, and verification registry keys | Unratified under GAP-0027. | No automatic restore or deletion. |
| Venue/session | Reserved CT-20 shape; no active consumer | Unratified under GAP-0036/GAP-0038. | No command, retry, flattening, or Book transition. |
| News/SQS/risk | News, SQS, stop-out, and bench registry keys | Unratified under GAP-0042 through GAP-0045. | No order, exit, promotion, or mode change. |
| Journal/data quality | Future CT-13 event fields and cadence | Unratified under GAP-0025/GAP-0026. | No store bypass or evidence mutation. |

## Alert authority

An alert is evidence, not permission. It cannot promote an artifact, authorize an order, flatten exposure, invoke an exit, change Book mode, rotate a secret, restore over data, or command an external provider. Human-only promotion remains absolute. [DEC-0041]

Venue flattening remains `GAP(GAP-0036)`. Exit ownership remains `GAP(GAP-0040)`. Paper-mode transitions remain `GAP(GAP-0041)`. Same-tick priority remains `GAP(GAP-0046)`. [DEC-0065]

## External authority boundary

QMF metrics may eventually describe responses observed through CT-14 and CT-15. CT-18 through CT-21 are currently reserved and unwired, so they provide no active metric source. No metric may claim provider-internal health, cause, queue depth, capacity, or recovery state without a ratified external contract. [DEC-0059]

## Traceability

Every future metric or alert must name its emitting component, contract field, registry threshold, measurement window, evidence identity, and ratified correlation path. CT-13 fields remain GAP-0025, and CT-25 cannot be used until its Data consumer is wired. [DEC-0038] [DEC-0048]
