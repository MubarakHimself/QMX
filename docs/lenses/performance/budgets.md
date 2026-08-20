---
id: PERF-BUDGETS-QMF-V1
title: QMF V1 Performance Budgets
type: lens
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP]
decisions: [DEC-0009, DEC-0030, DEC-0041, DEC-0045, DEC-0048, DEC-0059, DEC-0065, DEC-0096, DEC-0097, DEC-0098, DEC-0111, DEC-0114, DEC-0117, DEC-0118, DEC-0119, DEC-0121, DEC-0126, DEC-0127, DEC-0128, DEC-0129, DEC-0136, DEC-0137, DEC-0138, DEC-0142]
sources: [DEC-0009, DEC-0030, DEC-0041, DEC-0045, DEC-0048, DEC-0059, DEC-0065, DEC-0096, DEC-0097, DEC-0098, DEC-0111, DEC-0126, DEC-0127, DEC-0128, DEC-0129, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _docwork/gaps.yaml, docs/registry/variables.yaml, _docwork/feature_inventory.yaml, docs/contracts/ct-08-gate-evidence.yaml, docs/contracts/ct-09-registry-persistence.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-11-evidence-persistence.yaml, docs/contracts/ct-13-journal.yaml, docs/contracts/ct-14-backup-restore.yaml, docs/contracts/ct-16-indicator.yaml, docs/contracts/ct-17-causal-structure.yaml, docs/contracts/ct-18-venue-capabilities.yaml, docs/contracts/ct-19-venue-command.yaml, docs/contracts/ct-20-venue-event.yaml, docs/contracts/ct-23-risk-evaluation.yaml]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# QMF V1 Performance Budgets

QMF V1 governs performance by **measure-then-budget** (DEC-0111): no numbers are invented; every component ships a benchmark harness measuring speed **and peak memory** at a load ladder, first measurements become fingerprinted (OS, CPU-class)-scoped baselines with variance-scaled regression thresholds, and regressions beyond threshold fail the tier-2 merge gate. `registry:design_bot_concurrency` preserves the source's ~40-bot real-workload design case as the reference sizing the ladder (with 10/100/200 marks), never an SLO, percentile, capacity guarantee, or pass threshold. The one stated design constraint (not a measurement) is that `qmf-core` imports in well under one second (DEC-0111, DEC-0098).

## Budget status

The measurement method is ratified (measure-then-budget, DEC-0111); numeric per-component and end-to-end budgets intentionally await first recorded baselines and may not be invented before a baseline exists.

| Scope | Budget registry reference | Current status | Additional blockers |
|---|---|---|---|
| End-to-end QMF consumer path | `registry:design_bot_concurrency` | Method ratified; no numeric baseline yet. | No application runtime is in QMF V1 (DEC-0009); end-to-end sizing is a node/compute decision. |
| qmf-core values and fingerprints | `registry:design_bot_concurrency` | Method ratified (DEC-0111); no numeric baseline yet. Stated constraint: import in well under one second. | Core value, time, identity, refusal, fingerprint, and result-label contracts are ratified (DEC-0105 through DEC-0110). |
| qmf-registry registration, lineage, and gates | `registry:registry_attempt_scope`, `registry:registry_attempt_budget`, `registry:registry_attempt_reset_policy` | Method ratified; no numeric baseline yet. Attempt-counter keys stay null. | Registry records and lineage are ratified (DEC-0114); the attempt counter GAP-0017 is deferred to the backtesting sitting (DEC-0121). |
| qmf-data ingestion, access, journal, and persistence | `registry:local_store_engine`, `registry:raw_history_retention_policy` | Method ratified; no numeric baseline yet. | Store stack, rooms, bitemporal law, splits, seal, and journal streams are ratified (DEC-0117, DEC-0118, DEC-0119). |
| qmf-data backup and restore | `registry:backup_recovery_point_objective`, `registry:backup_recovery_time_objective`, `registry:restore_verification_cadence` | All objective values are null. | GAP-0027. [DEC-0045] |
| qmf-indicators light path | `registry:canonical_indicator_reference` | Two AD-13 rungs per configuration ratified (burst throughput, per-tick latency at the configured BarSpec, no-op tick path measured separately); pinned reference and the light/heavy gate ratified. No numeric baseline yet. | Rungs, reference, and light/heavy classification ratified (DEC-0126, DEC-0127, DEC-0128); numeric budgets await first baselines. |
| qmf-structure causal families | `registry:timestamp_precision` | Three AD-13 rungs ratified (active object-set size, objects minted per bar, interaction records per bar); the light/heavy four bounds bind families. No numeric baseline yet. | Lifecycle and rungs ratified (DEC-0129, DEC-0128); numeric budgets await first baselines. |
| Reserved venue capability, command, event, and reconciliation shapes | `registry:venue_trendbar_price_basis` | CT-18 through CT-21 shapes are ratified and the six-stage live-path latency decomposition is defined as named AD-13 rungs; no adapter is wired and no numeric baseline exists. | GAP-0035 through GAP-0038 answered (DEC-0136, DEC-0137, DEC-0138); the venue runtime path is node/risk territory (tracker/trading-node-notes.md). [DEC-0138] |
| Reserved risk evaluation and Book-transition shapes | Risk registry keys in `docs/registry/variables.yaml` | CT-22 through CT-25 are unwired; no implementation or performance budget is authorized. | GAP-0039 through GAP-0046. [DEC-0065] |

## Measurement method

The method is ratified (DEC-0111): every component ships a benchmark harness with the same status as unit tests, measuring **speed and peak memory** at a load ladder expressed in **framework-native units per package** (calls/s, series length, artifact count), with the ~40-bot node scenario (and 10/100/200 marks) as the motivating reference for sizing the ladder. Memory is a first-class budget: a regression in peak memory fails the gate the same as a slowdown.

First real measurements are recorded as fingerprinted baselines **scoped to a declared (OS, CPU-class) tuple**; each benchmark's regression threshold is stated when its baseline is recorded, as a multiple of measured run-to-run variance. Benchmark and test data are generated at runtime or held as controlled fixtures, never shipped as product artifacts. Every measurement binds to a contract format version, input fingerprint, environment identity, dataset/source identity, and evidence-time range; incompatible semantic changes mint new versions rather than sharing a baseline (DEC-0111, DEC-0030, DEC-0097). The specific runner, warm-up count, and sampling method are documentation-time detail of the harness, constrained by DEC-0111 rather than an open foundation gap.

## Ratified AD-13 rungs and the light/heavy gate

The increment sitting ratified the per-package AD-13 rungs and the light/heavy classification. These are rung **definitions**, not numeric budgets: the no-invented-numbers stance holds unchanged, and numeric budgets still await first measured baselines.

Each **CT-16 configuration** declares two AD-13 rungs — **burst throughput** and **per-tick latency** — denominated per accepted input observation at the configured BarSpec, with the no-op tick path measured separately. Both are factory-gate machinery; production visibility stays AD-14's job (DEC-0126).

Each **CT-17 family** declares three AD-13 rungs — **active object-set size**, **objects minted per bar**, and **interaction records per bar** (DEC-0129).

A configuration is **light** only if it declares AND benchmark-proves four bounds: (1) per-update cost within the live-path latency rung; (2) bounded declared state size within the owning contract's ceiling; (3) either a bounded declared evidence window or a declared anchor-reset rule with O(1) per-update cost; and (4) synchronous availability on the trading path, which a marked not-ready value satisfies. The light/heavy verdict is a machine-scoped AD-13 benchmark artifact, **declared display-only and never identity**. Until the live-path latency rung has a recorded baseline, **every configuration is heavy by default and a light claim is refused at the gate**. The same four bounds bind structure families — per-update cost, bounded live-object-set size, bounded scan/lookback window, and synchronous availability (DEC-0128).

The venue increment adds the **six-stage live-path latency decomposition** — tick received → evidence write → indicator update → decision → risk evaluation → order submitted — recorded as named AD-13 rungs with **no numeric budgets until measured**; the no-invented-numbers stance is unchanged. Each rung is a **monotonic delta within one boot epoch on one machine**, and a wall-computed rung is refused as a baseline. The venue adapter owns the arrival and submit stamps for its stages (DEC-0138).

## Baselines

No current baseline exists because no QMF implementation has been measured yet; baselines are recorded from first real measurement (DEC-0111). Factory reference usage and executable tests are required evidence of contract behavior, but they are not performance baselines or SLOs (DEC-0096).

The ~40-bot source case remains a design input through `registry:design_bot_concurrency`. It must not be rewritten as a measured percentile, supported maximum, concurrent-load guarantee, or release gate (DEC-0098). Server sizing and scaling are node/compute decisions, made later with these numbers.

## Storage and recovery budgets

Retention, partitioning, compaction, and capacity remain GAP-0026. GAP-0027 is answered: the backup design (nightly, encrypted, versioned, off-machine, with automated sample-restore tests and periodic full-restore rehearsal) is ratified under DEC-0118, so `registry:backup_cadence` is nightly; only the numerics `registry:backup_recovery_point_objective`, `registry:backup_recovery_time_objective`, `registry:backup_retention_period`, and `registry:restore_verification_cadence` stay null pending the node/ops sitting. [DEC-0118]

## Exceeding a future budget

A regression beyond a benchmark's stated threshold — in speed or in peak memory equally — fails the tier-2 merge gate (DEC-0111). Beyond the merge gate, no automatic runtime response is ratified: a breach may become CT-13 journal evidence after its threshold is recorded, but no breach can authorize promotion, order rejection, retry, flattening, exit, Book transition, restore, or external-provider action. CT-25 is an unwired placeholder and cannot be assumed as an evidence path. [DEC-0041] [DEC-0048] [DEC-0111]

Venue outage handling is now ratified fail-closed — in-flight commands become UNKNOWN and command retry is prohibited (DEC-0137) — while flatten authority assignment stays node/risk territory (DEC-0142, tracker/trading-node-notes.md). Exit ownership remains GAP-0040. Paper-mode behavior remains GAP-0041. Same-tick priority remains GAP-0046. No performance test may fill those authority gaps. [DEC-0065]

## Acceptance gate

A performance budget becomes a pass/fail threshold only when its baseline is recorded from real measurement, fingerprinted and scoped to a declared (OS, CPU-class) tuple, with its regression threshold stated as a multiple of measured variance and its load ladder in framework-native units (DEC-0111). Until a baseline is recorded, a component's performance statement is a design constraint without a numeric threshold; the ~40-bot reference and the `qmf-core` sub-one-second import constraint are the only stated targets. [DEC-0096] [DEC-0098] [DEC-0111]
