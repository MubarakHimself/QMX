---
id: SCN-0004
title: Backup Does Not Claim Recoverability Before Its Boundaries Exist
type: scenario
status: ratified
component: COMP-QMF-DATA-BACKUP
depends_on: [COMP-QMF-CORE, COMP-QMF-DATA-STORE, COMP-OBJECT-STORAGE]
decisions: [DEC-0044, DEC-0045, DEC-0117, DEC-0118]
sources: [docs/components/qmf-data-store.md, docs/components/qmf-data-backup.md, docs/components/object-storage.md, docs/registry/variables.yaml, docs/contracts/ct-14-backup-restore.yaml, docs/contracts/ct-26-store-backup-input.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# SCN-0004: Backup Does Not Claim Recoverability Before Its Boundaries Exist

This scenario exercises the ratified off-machine backup design and its primitives-versus-schedule split. The architecture sitting ratified the backup design — nightly, encrypted, versioned, off-machine to an object-storage bucket, with automated sample-restore tests and a periodic full-restore rehearsal — where QMF provides the backup, restore, and verify primitives (CT-14, CT-26) and applications own schedule, execution, and cutover; migrations run preflight checks, backup first, dry-run, migrate, verify, never mutating the only copy in place. Numeric recovery targets, encryption key custody, and the crypto dependency remain node/ops-sitting items. Execution status: **backup design and migration ratified; numeric RPO/RTO await the node/ops sitting**. [DEC-0118]

## Given

The Store contains an original observation, its later correction, and their lineage. CT-26 carries the Store-to-Backup handoff and CT-14 the Backup-to-Object-Storage handoff; QMF owns the backup, restore, and verify primitives behind these contracts, while the schedule and its execution are application/ops-owned. The topology is ratified: the trading-node VPS records and syncs down, the workstation holds the working archive, and the bucket catches nightly copies. [DEC-0117] [DEC-0118]

## When

An agent is asked to create a snapshot, transmit it off-machine, restore it into a replacement Store, run a migration, or declare disaster recovery complete.

## Then

Recoverability is claimed only through the ratified verify primitives — automated sample-restore tests plus a periodic full-restore rehearsal (DEC-0118) — never asserted from a snapshot alone. A recovery or migration never mutates the only copy in place: it runs preflight, backs up first, dry-runs, then verifies against a documented restore path, and must not overwrite the only good local evidence or perform operational cutover, which stays application/ops-owned. [DEC-0045] [DEC-0118]

## Worked numbers

The backup cadence is ratified as nightly and copies are encrypted, versioned, and off-machine (DEC-0118). Numeric recovery-point and recovery-time objectives, the restore-verification cadence's exact period, encryption key custody, and the crypto dependency remain node/ops-sitting items under DEC-0118 — so `registry:backup_recovery_point_objective`, `registry:backup_recovery_time_objective`, and `registry:restore_verification_cadence` are not filled from a recommendation; they are measured and set at that sitting.
