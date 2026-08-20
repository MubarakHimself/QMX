---
id: OBS-METRICS-QMF-V1
title: QMF V1 Metrics and Alerts
type: lens
status: provisional
depends_on: [COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP]
decisions: [DEC-0038, DEC-0041, DEC-0045, DEC-0048, DEC-0055, DEC-0058, DEC-0059, DEC-0065, DEC-0072, DEC-0074, DEC-0096, DEC-0098, DEC-0106, DEC-0111, DEC-0112, DEC-0117, DEC-0118, DEC-0119, DEC-0121, DEC-0126, DEC-0127, DEC-0128, DEC-0129, DEC-0131, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0142]
sources: [DEC-0038, DEC-0041, DEC-0045, DEC-0048, DEC-0055, DEC-0058, DEC-0059, DEC-0065, DEC-0072, DEC-0074, DEC-0096, DEC-0098, DEC-0106, DEC-0111, DEC-0112, DEC-0126, DEC-0127, DEC-0128, DEC-0129, DEC-0131, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/time-audit-devops.md, _docwork/gaps.yaml, docs/registry/variables.yaml, docs/contracts/ct-08-gate-evidence.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-13-journal.yaml, docs/contracts/ct-14-backup-restore.yaml, docs/contracts/ct-16-indicator.yaml, docs/contracts/ct-17-causal-structure.yaml, docs/contracts/ct-18-venue-capabilities.yaml, docs/contracts/ct-19-venue-command.yaml, docs/contracts/ct-20-venue-event.yaml, docs/contracts/ct-21-venue-secret-session.yaml, docs/contracts/ct-23-risk-evaluation.yaml, docs/contracts/ct-24-book-mode.yaml, docs/contracts/ct-25-risk-journal.yaml]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# QMF V1 Metrics and Alerts

QMF V1 has no ratified metrics schema, aggregation window, dashboard, alert threshold, severity tier, notification destination, paging route, or automatic remediation. Two obligations bind now: emitted signals must be **exportable to Prometheus-class monitoring stacks with push alerting**, the stack choice itself being node/ops territory (DEC-0112); and performance is governed by **measure-then-budget** — every component ships a benchmark harness measuring speed **and peak memory** at a load ladder, with first measurements recorded as fingerprinted (OS, CPU-class)-scoped baselines and variance-scaled regression thresholds gating tier-2 merges (DEC-0111). This document identifies source-backed measurement subjects and the registry/GAP that must define each numeric value before an alert can exist. [DEC-0048] [DEC-0098] [DEC-0111] [DEC-0112]

## Exportability obligation

Emitted signals must be exportable to standard monitoring stacks (Prometheus-class metrics, push alerts); the stack selection, dashboard, storage backend, and full monitoring/evaluation design land at the node/ops sitting, but the exportability obligation binds now (DEC-0112). The DevOps time-audit names concrete signals to export once a node exists — chrony offset, stratum, and sync-age; per-venue clock skew; the clock step counter — over a push alert path with no on-call rotation (DEC-0112, DEC-0106; companion `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/time-audit-devops.md`). These are stated node/ops obligations binding later sittings, not implemented panels here.

## Performance measurement subjects

Performance follows measure-then-budget (DEC-0111): every component ships a benchmark harness with the same status as unit tests, measuring **speed and peak memory** at a load ladder in framework-native units per package (calls/s, series length, artifact count), sized around the ~40-bot reference with 10/100/200 marks. Peak memory is a first-class budget — a regression in peak memory fails the tier-2 merge gate the same as a slowdown. First real measurements become fingerprinted baselines scoped to a declared (OS, CPU-class) tuple, and each benchmark's regression threshold is stated when its baseline is recorded, as a multiple of measured run-to-run variance. The one stated design constraint (not a measurement) is that `qmf-core` imports in well under one second. Numeric budgets intentionally await first baselines; the measure-then-budget method is ratified (DEC-0111), and no numeric value may be invented before its baseline is recorded.

Classification and visibility follow one chain per configuration: the per-configuration **declared budget is the promise** (contract surface), the **AD-13 measurement is the proof**, **AD-14 metrics are runtime visibility**, and **UI display is platform territory**. The light/heavy verdict is a machine-scoped AD-13 benchmark artifact, declared display-only and never identity (DEC-0128, DEC-0131).

The venue live-path adds a **six-stage latency decomposition** (tick received → evidence write → indicator update → decision → risk evaluation → order submitted) recorded as **named AD-13 rungs with NO numeric budgets until measured** (DEC-0138). Each rung is a **monotonic delta within one boot epoch on one machine** — receive wall time and the boot-scoped monotonic stamp are mandatory on every inbound venue event, and a wall-computed rung is refused as a baseline. The adapter owns the arrival and submit stamps for its stages. The rungs stay numberless; no threshold or budget may be invented before its first fingerprinted baseline exists (DEC-0138, DEC-0111).

## Measurement subjects

| Subject | Evidence source | Registry reference | Unresolved definition |
|---|---|---|---|
| Real-workload speed and peak memory | Per-component benchmark harness (speed + peak memory) at the load ladder | `registry:design_bot_concurrency` | Measure-then-budget method is ratified (DEC-0111); numeric budgets await first (OS, CPU-class)-scoped baselines. The ~40-bot value stays a design input, not a percentile or supported maximum. [DEC-0098] [DEC-0111] |
| Registry gate and attempt outcomes | CT-08 | `registry:registry_attempt_scope`, `registry:registry_attempt_budget`, `registry:registry_attempt_reset_policy` | All values are null; the attempt counter GAP-0017 and the look-ahead gate GAP-0016 are deferred to the backtesting sitting (DEC-0121). Registry occurrence records still log every run. |
| Source ingestion quality | CT-10 owned/provided by COMP-QMF-DATA; CT-15 source edge | — | Bitemporal fact shape (event-time, known-at, source, revision), idempotent intake, and separately-identified tick sources are ratified (DEC-0117, DEC-0119); numeric duplicate/gap-rate metrics await measured volume, and the news-calendar legal posture stays an open operator item. |
| Data-store capacity and durability | CT-09, CT-11, CT-13 | `registry:local_store_engine`, `registry:raw_history_retention_policy` | The store stack is ratified (Parquet/DuckDB/SQLite/JSONL behind contracts, DEC-0117); numeric capacity, partition, and retention measurements are set after measured volume (DEC-0118). |
| Backup freshness and recoverability | CT-14 owned by COMP-QMF-DATA-BACKUP | `registry:backup_cadence`, `registry:backup_recovery_point_objective`, `registry:backup_recovery_time_objective`, `registry:backup_retention_period`, `registry:restore_verification_cadence` | The design (nightly, encrypted, versioned, off-machine, with sample- and full-restore tests) is ratified (DEC-0118); numeric objectives and alert thresholds are named at the node/ops sitting. [DEC-0045] |
| Indicator readiness and conformance | CT-16 | `registry:canonical_indicator_reference` | Reference, warm-up, readiness, and tolerances (integer ULP counts) are ratified (DEC-0126, DEC-0127); two AD-13 rungs per configuration — burst throughput and per-tick latency, per accepted input observation at the configured BarSpec. Streaming indicator instances are components exposing `health()` (DEC-0131); numeric budgets await first baselines. |
| Structure causality and invalidation | CT-17 and CT-08 | — | The causal lifecycle (observed-at/confirmed-at, confirmation and invalidation edges) is ratified (DEC-0129); three AD-13 rungs — active object-set size, objects minted per bar, interaction records per bar. Structure family instances are components exposing `health()` (DEC-0131); numeric budgets await first baselines. |
| Venue session and reconciliation | CT-18 through CT-21 ratified (DEC-0136, DEC-0137, DEC-0138) | `registry:venue_trendbar_price_basis` | The measurement subjects are named: outstanding-`UNKNOWN` state per command stream, the continuous daily-boundary monitor, and reconciliation read-back verdicts (`reconciled` \| `drift` \| `unknown`); `registry:venue_trendbar_price_basis` is measured per broker at first connection under the verify-or-refuse suite, not a fixed value (DEC-0135). No numeric threshold is invented; the Book/BMS caller and reconciliation-verdict consequences are node/risk territory `GAP(GAP-0039)` (DEC-0142). [DEC-0059] |
| SQS | CT-23/CT-25 reserved/unwired placeholders | `registry:spread_quality_sensor_formula` | No active measurement source exists; formula, units, inputs, thresholds, cadence, hysteresis, stale behavior, and alert meaning remain GAP-0043. [DEC-0074] [DEC-0075] |
| News control | CT-25 reserved and not wired to Data | `registry:news_blackout_before`, `registry:news_blackout_after` | Values are null; severity, mapping, windows, overrides, consumer, and alert behavior remain GAP-0042. [DEC-0072] |
| Stop-out and bench state | CT-23/CT-25 reserved/unwired placeholders | `registry:bench_stopout_threshold`, `registry:bench_reset_boundary` | Values are null and no active source exists; stop-out, names, benchmark, reset, and alert meaning remain GAP-0045. [DEC-0094] |

## Dashboard status

No dashboard is specified. No metric name, unit, label set, aggregation, sampling interval, storage backend, panel, query, or baseline may be invented from the measurement-subject table.

The performance measurement method is ratified (measure-then-budget, DEC-0111); numeric budgets await first fingerprinted baselines before performance panels can carry thresholds. No metric name, unit, or panel may be invented before its baseline exists.

The journal event vocabulary is ratified (seven event types across N per-component streams, DEC-0119); a panel derived from journal events binds to that vocabulary, and per-event field lists plus numeric cadence are set after measured volume before a panel carries them.

Numeric retention windows and metrics-store capacity are set after measured volume (DEC-0118); the metrics store and query horizon are node/ops monitoring-stack choices (DEC-0112).

## Alert status

No numeric-threshold alert may be implemented because no threshold or severity model is ratified. A registry key with a null value is not an implicit default. The venue ADs name several **state- and event-triggered alarms** (DEC-0136, DEC-0137, DEC-0138) — these carry no numeric threshold and invent none; their severity, notification destination, and paging route remain node/ops territory.

| Alert domain | Trigger or threshold source | Severity/notification | Automatic action |
|---|---|---|---|
| Performance | Fingerprinted (OS, CPU-class) baselines with variance-scaled thresholds (DEC-0111) | Unratified until baselines exist; a threshold breach (speed or peak memory) fails the tier-2 merge gate, not a live alert. | None authorized. |
| Backup/restore | RPO, RTO, retention, and verification registry keys | Unratified under GAP-0027. | No automatic restore or deletion. |
| Rotation store-failure | State/event: a failed store after credential rotation (DEC-0136) | Named alarm; no numeric threshold. Severity/notification node/ops. | Also blocks the command pipe (after-condition = successful store or operator re-provision) while sensing continues; no secret value ever surfaced. |
| Unmapped venue error code | State/event: a venue code with no CT-18 error-table row (DEC-0138) | Named alarm; no numeric threshold. Severity/notification node/ops. | Unmapped default is `(transient venue failure, retryable = no, outcome = UNKNOWN)`; no retry, no assumed outcome. |
| Reused command identity | State/event: differing content under a reused command `fp1` (DEC-0137) | Named alarm; no numeric threshold. Severity/notification node/ops. | The submission is refused and alarmed; an idempotent re-present is accepted silently, never overwritten. |
| Outstanding `UNKNOWN` | State: an `UNKNOWN` outstanding on a `(VenueId, account)` command stream (DEC-0137) | State signal; no numeric threshold. Severity/notification node/ops. | New commands on that stream are refused (`transient venue failure`) until an explicit `resolve_unknown`; the adapter never self-clears, retries, flattens, or invents a terminal state. |
| Daily-boundary monitor | Continuous per-broker measurement of the venue daily-bar boundary (DEC-0135, DEC-0138) | State signal; no numeric threshold. A drift from the stored per-broker boundary is a `data quality` journal event. | Venue daily bars stay ungoverned until measured and verified; no bar evidence is admitted on a failed reconciliation. |
| News/SQS/risk | News, SQS, stop-out, and bench registry keys | Unratified under GAP-0042 through GAP-0045. | No order, exit, promotion, or mode change. |
| Journal/data quality | CT-13 seven event types across N per-component streams (DEC-0119); numeric cadence after measured volume | Unratified until per-event fields and cadence are recorded. | No store bypass or evidence mutation. |

## Alert authority

An alert is evidence, not permission. It cannot promote an artifact, authorize an order, flatten exposure, invoke an exit, change Book mode, rotate a secret, restore over data, or command an external provider. Human-only promotion remains absolute. [DEC-0041]

Flatten is mechanical `close_position`/`close_all` commands the adapter never initiates; flatten-authority assignment (VPS-death included) is node/risk sitting territory, tracked in `tracker/trading-node-notes.md` (DEC-0137, DEC-0142). Exit ownership remains `GAP(GAP-0040)`. Paper-mode transitions remain `GAP(GAP-0041)`. Same-tick priority remains `GAP(GAP-0046)`. [DEC-0065]

## External authority boundary

QMF metrics may eventually describe responses observed through CT-14 and CT-15, and venue market data enters as CT-10/CT-15 source observations (DEC-0138). CT-18 through CT-21 are the ratified venue-adapter contracts, but no live venue caller is assigned in QMF, so the named venue signals above are measurement subjects, not live panels. No metric may claim provider-internal health, cause, queue depth, capacity, or recovery state without a ratified external contract. [DEC-0059]

## Traceability

Every future metric or alert must name its emitting component, contract field, registry threshold, measurement window, evidence identity, and the ratified `correlation_id` path propagated across every package boundary (DEC-0112). CT-13 event types are ratified (DEC-0119); per-event fields are set after measured volume, and CT-25 cannot be used until its Data consumer is wired. [DEC-0038] [DEC-0048] [DEC-0112]
