---
id: SCN-0004
title: Backup Does Not Claim Recoverability Before Its Boundaries Exist
type: scenario
status: provisional
component: COMP-QMF-DATA-BACKUP
depends_on: [COMP-QMF-CORE, COMP-QMF-DATA-STORE, COMP-OBJECT-STORAGE]
decisions: [DEC-0044, DEC-0045]
sources: [docs/components/qmf-data-store.md, docs/components/qmf-data-backup.md, docs/components/object-storage.md, docs/registry/variables.yaml, docs/contracts/ct-14-backup-restore.yaml, docs/contracts/ct-26-store-backup-input.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# SCN-0004: Backup Does Not Claim Recoverability Before Its Boundaries Exist

This scenario distinguishes the source-backed off-machine direction from an unearned claim that a snapshot is complete, consistent, or operationally recoverable. Execution status: **blocked specification**. [DEC-0045]

## Given

The Store contains an original observation, its later correction, and their lineage. CT-26 reserves the Store-to-Backup handoff; CT-14 reserves the Backup-to-Object-Storage handoff. Both schemas are null, and all backup timing and recovery registry keys are null. [DEC-0044] [DEC-0045]

`GAP(GAP-0022): Ratify schema compatibility, migration, rollback, and verification.`

`GAP(GAP-0026): Ratify completeness, partition, and consistency boundaries.`

`GAP(GAP-0027): Ratify cadence, encryption, retention, restore, RPO, RTO, verification, recovery, rollback, and cutover authority.`

## When

An agent is asked to create a snapshot, transmit it off-machine, restore it into a replacement Store, or declare disaster recovery complete.

## Then

No operation may be labelled complete or recoverable until CT-26 proves a coherent input and CT-14 proves the off-machine handoff. A recovery attempt must not overwrite the only good local evidence, perform cutover, or claim cross-link integrity. The only current rule is the off-machine direction. [DEC-0045]

## Worked numbers

`registry:backup_cadence`, `registry:backup_recovery_point_objective`, `registry:backup_recovery_time_objective`, `registry:backup_retention_period`, and `registry:restore_verification_cadence` are null. No schedule or recovery target may be copied from the recommendation in GAP-0027.
