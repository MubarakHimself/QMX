---
id: COMP-OBJECT-STORAGE
title: Off-Machine Object Storage
type: component-spec
status: provisional
component: COMP-OBJECT-STORAGE
depends_on: []
decisions: [DEC-0013, DEC-0045]
sources: [DEC-0013, DEC-0045, docs/architecture/dependencies.yaml, docs/registry/variables.yaml, docs/contracts/ct-14-backup-restore.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# Off-Machine Object Storage

`COMP-OBJECT-STORAGE` is the provisional external destination for QMF evidence snapshots produced by `COMP-QMF-DATA-BACKUP`. CT-14 reserves the provider-neutral transfer boundary; provider selection, scheduling, manifest completeness, and restore validation remain unresolved. [DEC-0045]

## Authority boundary

May, from QMF's perspective and only after GAP-0027 is ratified: accept, retain, and return backup objects and provider acknowledgements through CT-14. [DEC-0045]

May never, from QMF's perspective: be described as QMF-owned or QMF-deployed; be assumed durable merely because an upload returned; decide that a backup or restore is valid; receive secrets in QMF evidence; silently delete evidence; define QMF retention, RPO, RTO, or verification cadence; or replace complete local raw evidence. [DEC-0045]

## Interfaces

| Interface | Direction | Contract | Peer |
|---|---|---|---|
| Reserved snapshot transfer and restore evidence | in/out | [CT-14](../contracts/ct-14-backup-restore.yaml) | COMP-QMF-DATA-BACKUP |

## Behavior

`registry:backup_cadence` is a registry reference, not an adopted schedule: GAP-0027 still governs cadence, completion evidence, and restore validation. A byte-transfer acknowledgement alone establishes none of those unresolved semantics. [DEC-0045]

The provider remains external and replaceable. Provider-specific object, acknowledgement, encryption, and credential details cannot enter QMF core or data-policy contracts. [DEC-0013] [DEC-0045]

`GAP(GAP-0027): Select the provider and ratify manifest fields, credentials, encryption, retention, deletion, transfer behavior, RPO, RTO, and restore-verification cadence.`

`GAP(GAP-0026): Define which evidence partitions and compaction state form a complete snapshot.`

<!-- no-diagram: the component is an external CT-14 object boundary; provider internals are outside QMF authority -->

## Configuration

| Variable | Registry key | Notes |
|---|---|---|
| Backup cadence | `registry:backup_cadence` | Non-authoritative while GAP-0027 remains open; no schedule is adopted here. |
| Recovery point objective | `registry:backup_recovery_point_objective` | Null until GAP-0027. |
| Recovery time objective | `registry:backup_recovery_time_objective` | Null until GAP-0027. |
| Backup retention period | `registry:backup_retention_period` | Null until GAP-0027. |
| Restore-verification cadence | `registry:restore_verification_cadence` | Null until GAP-0027. |
| Provider, credentials, and encryption | — | `GAP(GAP-0027): Provider selection, credential representation, storage/injection, registry exclusion, redaction, encryption, and lifecycle behavior are all unratified; no credential-bearing operation may proceed.` |

## Failure modes

| # | Condition | Behavior | Cites |
|---|---|---|---|
| FM-1 | A future upload is rejected, interrupted, or only partially acknowledged. | Completion cannot be claimed because GAP-0027 has not defined completion evidence, resumability, or cleanup. | DEC-0045 |
| FM-2 | A future restore observes a missing or corrupt object. | No recoverability claim or destructive restore action is authorized. `GAP(GAP-0027): Define validation evidence, failure handling, and recovery authority.` | DEC-0045 |
| FM-3 | A credential-bearing transfer is requested. | No transfer proceeds while provider credential handling remains unresolved; this spec defines neither secret storage nor rotation. `GAP(GAP-0027): Define the gate.` | DEC-0045 |
| FM-4 | The provider is unavailable longer than an assumed objective. | No objective may be claimed while the RPO and RTO registry values are null. `GAP(GAP-0027): Ratify the objectives and escalation path.` | DEC-0045 |
| FM-5 | Provider retention or deletion behavior conflicts with QMF evidence retention. | QMF must not treat the provider as compliant or delete local raw evidence. `GAP(GAP-0027): Define retention and deletion controls.` | DEC-0045 |
| FM-6 | Future restore evidence does not match the source manifest. | No success claim is available until GAP-0027 defines manifest identity, validation, and completion semantics. | DEC-0045 |

## Related

Decisions: DEC-0013, DEC-0045. Scenarios: [SCN-0004 backup boundary](../scenarios/SCN-0004-off-machine-backup.md). Knowledge: none drafted.
