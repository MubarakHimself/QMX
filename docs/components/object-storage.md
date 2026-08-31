---
id: COMP-OBJECT-STORAGE
title: Off-Machine Object Storage
type: component-spec
status: ratified
component: COMP-OBJECT-STORAGE
depends_on: []
decisions: [DEC-0013, DEC-0045, DEC-0103, DEC-0106, DEC-0109, DEC-0117, DEC-0118, DEC-0119, DEC-0188, DEC-0197, DEC-0198, DEC-0217, DEC-0252, DEC-0259]
sources: [_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-NODE-2026-08-28/ARCHITECTURE-SPINE.md, _docwork/ledger.yaml, _docwork/gaps.yaml, docs/architecture/dependencies.yaml, docs/registry/variables.yaml, docs/components/trading-node.md, docs/contracts/ct-14-backup-restore.yaml]
generated: 2026-08-18
verified: 2026-08-29
stale_after: 30d
---

# Off-Machine Object Storage

`COMP-OBJECT-STORAGE` is the external, replaceable destination for QMF's encrypted, versioned backup copies produced by `COMP-QMF-DATA-BACKUP` through CT-14. The nightly, encrypted, versioned, off-machine backup design is ratified (DEC-0118, AD-20); the bucket catches the nightly copies while remaining outside QMF ownership. Provider selection, object-key layout, credential and encryption key custody, and the numeric recovery objectives are named at the node/ops sitting, not by this boundary (DEC-0118).

## Authority boundary

May, from QMF's perspective: accept, retain, and return encrypted, versioned backup objects and provider acknowledgements through CT-14; hold copies of every room-role including the registry room, per world, as opaque encrypted payloads (DEC-0117, DEC-0118).

May never, from QMF's perspective: be described as QMF-owned or QMF-deployed; be assumed durable merely because an upload returned — durability is established by QMF-side verification primitives in `COMP-QMF-DATA-BACKUP`, not by a byte-transfer acknowledgement (DEC-0118); decide that a backup or restore is valid; receive secrets in QMF evidence; silently delete evidence; leak provider-specific object, acknowledgement, encryption, or credential details into QMF core or data-policy contracts (DEC-0013); or replace the complete local raw evidence copy (DEC-0118, DEC-0045).

## Interfaces

| Interface | Direction | Contract | Peer |
|---|---|---|---|
| Off-machine backup copy transfer and restore | in/out | [CT-14](../contracts/ct-14-backup-restore.yaml) | COMP-QMF-DATA-BACKUP |

CT-14 carries encrypted, versioned copies; boundary failures (an unreachable bucket, a failed upload, a corrupt copy) surface as `storage failure` typed refusals returned by `COMP-QMF-DATA-BACKUP`, never raised across the boundary (DEC-0109).

## Behavior

`registry:backup_cadence` is nightly (ratified design); the schedule and execution are application/ops-owned, so the provider receives copies on the application's cadence, not one this component defines (DEC-0118). Every copy is a distinct version; the provider never mutates an existing copy, and QMF never treats a provider deletion or retention behavior as authority to drop the only local raw evidence copy (DEC-0118). Stored int64 UTC nanosecond timestamps in a payload round-trip verbatim, never re-derived under a later calendar identity or tzdata version (DEC-0106).

The provider remains external and replaceable; provider-specific object, acknowledgement, encryption, and credential details cannot enter QMF core or data-policy contracts (DEC-0013). Encryption is required; encryption key custody and the crypto dependency are named at the node/ops sitting (DEC-0118). A read against restored data still enforces the 12-month seal exactly as a live read does — the enforcement is QMF-side, not the provider's (DEC-0119).

The numeric recovery-point objective, recovery-time objective, retention depth, verification cadence, object-key layout, and provider selection are named at the node/ops sitting (DEC-0118); this boundary asserts none of them.

<!-- no-diagram: the component is an external CT-14 object boundary; provider internals are outside QMF authority and the backup sequence is shown in COMP-QMF-DATA-BACKUP -->

## Trading-node increment (2026-08-29)

The trading node (`COMP-QMN`) is the runtime that pushes backups to this bucket, and the 2026-08-28 trading-node sitting fixed the backup transport, the payload-key custody and the restore drills that read the bucket; the bucket stays external and replaceable and the increment was ratified by operator delegation plus four direct rulings (DEC-0259). See [COMP-QMN](trading-node.md) for the node's own spec.

### The bucket is the off-host backup target, pushed by the VPS via rclone

The bucket is the off-host backup target: `qmn-backup.timer` runs nightly on the VPS and the V1 `ObjectStorage` implementation is local staging under `/var/lib/qmx/staging` plus **`rclone` to this S3-compatible bucket**, ciphertext only, **pushed by the VPS and never by the workstation** — a 24 h recovery-point objective cannot depend on a laptop being awake, and the bucket credential belongs where the timer runs (DEC-0198, DEC-0188). The provider is deployment configuration, never architecture: **Backblaze B2 is the recommendation**, with R2 and Wasabi as alternatives, and credentials are held by reference (DEC-0198). The copy is always a prefix of a real stream — the backup unit copies only journal segments sealed at a committed sequence boundary — so a restored room can never hold a torn record (DEC-0198).

### Payload-key custody is on the workstation; the restore drills read the bucket

The CT-14 backup **payload key that decrypts every off-host copy is generated at provisioning on the workstation**, escrowed in Windows Credential Manager under `qmx/backup-payload-key` plus one operator-held offline copy, and delivered to the VPS as a bootstrap credential — it is never VPS-minted, and the VPS-minted key-encryption key protects rotated session material only, so the backup does not die with the host it exists to survive (DEC-0252, DEC-0197, DEC-0217). `registry:backup_payload_key_custody` carries the escrow rule itself rather than a blank (DEC-0252).

Three restore drills read this bucket, each measuring against the copies it holds (DEC-0252, DEC-0198): a **nightly sample restore** (`qmn-restore-sample.timer`) that pulls one file back and verifies its fingerprint; a **monthly full restore** (`qmn-restore-full.timer`) into a scratch directory, an integrity test and only that; and a **host-loss restore rehearsal**, the operator's `restore_drill_run` power, that restores from this bucket onto a clean host holding nothing but the escrowed payload key — the only drill that exercises key availability and therefore the only one that can prove disaster recovery. The integrity-restore recovery-time objective is measured at the monthly rehearsal and the full-DR objective at the host-loss rehearsal; RTO is measured, never declared (DEC-0198, DEC-0252).

## Configuration

| Variable | Registry key | Notes |
|---|---|---|
| Backup cadence | `registry:backup_cadence` | Nightly (ratified); application/ops-owned schedule; no cadence is decided here (DEC-0118). |
| Recovery-point objective | `registry:backup_recovery_point_objective` | Design ratified; the numeric RPO is named at the node/ops sitting (DEC-0118). |
| Recovery-time objective | `registry:backup_recovery_time_objective` | Design ratified; the numeric RTO is named at the node/ops sitting (DEC-0118). |
| Backup retention period | `registry:backup_retention_period` | Design ratified; the numeric retention depth is named at the node/ops sitting (DEC-0118). |
| Restore-verification cadence | `registry:restore_verification_cadence` | Automated sample-restore plus periodic full-restore rehearsal are ratified; the numeric cadence is named at the node/ops sitting (DEC-0118). |
| Provider, credentials, and encryption | — | Provider selection, credential representation and custody, and encryption key custody are named at the node/ops sitting; no credential-bearing operation is defined here (DEC-0118). |

## Failure modes

| # | Condition | Behavior | Cites |
|---|---|---|---|
| FM-1 | An upload is rejected, interrupted, or only partially acknowledged. | Completion is not claimed on the acknowledgement alone; `COMP-QMF-DATA-BACKUP` returns a `storage failure` refusal, and durability is established by QMF-side verification. | DEC-0109, DEC-0118 |
| FM-2 | A restore observes a missing or corrupt object. | No recoverability claim or destructive restore action is authorized; the automated sample-restore and full-restore rehearsal primitives are the recovery evidence (DEC-0118). | DEC-0118 |
| FM-3 | A credential-bearing transfer is requested. | No secret enters QMF evidence; credential representation, storage, and rotation are named at the node/ops sitting. | DEC-0118 |
| FM-4 | The provider is unavailable longer than the recovery objective. | No numeric objective is asserted by this boundary; the RPO/RTO are named at the node/ops sitting. | DEC-0118 |
| FM-5 | Provider retention or deletion behavior conflicts with QMF evidence retention. | QMF does not treat the provider as compliant and never deletes the only local raw evidence copy. | DEC-0118, DEC-0045 |
| FM-6 | Restore evidence does not match the source. | No success claim is made; restore validity is decided by QMF-side verification, not a provider acknowledgement. | DEC-0118 |

## Related

Decisions: DEC-0118, DEC-0117, DEC-0119, DEC-0109, DEC-0106, DEC-0045, DEC-0013. Spine: [ARCHITECTURE-SPINE.md](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md) AD-20, AD-19. Scenarios: [SCN-0004 backup boundary](../scenarios/SCN-0004-off-machine-backup.md). Knowledge: none drafted.
