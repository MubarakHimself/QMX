---
id: COMP-QMF-DATA-BACKUP
title: qmf-data Off-Machine Backup Boundary
type: component-spec
status: ratified
component: COMP-QMF-DATA-BACKUP
depends_on: [COMP-QMF-DATA-STORE, COMP-OBJECT-STORAGE]
decisions: [DEC-0103, DEC-0106, DEC-0109, DEC-0110, DEC-0113, DEC-0117, DEC-0118, DEC-0119, DEC-0045]
sources: [_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _docwork/ledger.yaml, _docwork/gaps.yaml, docs/architecture/dependencies.yaml, docs/registry/variables.yaml, docs/contracts/ct-14-backup-restore.yaml, docs/contracts/ct-26-store-backup-input.yaml]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# qmf-data Off-Machine Backup Boundary

`COMP-QMF-DATA-BACKUP` provides QMF's backup, restore, and verify **primitives**, carrying encrypted, versioned copies off-machine from `COMP-QMF-DATA-STORE` to `COMP-OBJECT-STORAGE`. The backup design is ratified — nightly, encrypted, versioned, off-machine, with automated sample-restore tests and a periodic full-restore rehearsal — while the schedule (`registry:backup_cadence` = nightly) and its execution are application/ops-owned, the same split as all scheduling (DEC-0118, AD-20). QMF ships the primitives; the cadence that runs them nightly is application/ops territory.

## Authority boundary

May: receive the CT-26 Store-to-Backup input per room-role and per world (DEC-0117); produce an encrypted, versioned off-machine copy through CT-14 as a backup, restore, and verify primitive (DEC-0118); back up every room-role including the registry room under one retention, backup, and migration law (DEC-0117); preserve stored int64 UTC nanosecond timestamps verbatim across the round-trip, never re-derived under a later calendar identity or tzdata version (DEC-0106); run automated sample-restore tests and a periodic full-restore rehearsal as first-class verification, never optional add-ons (DEC-0118); and enforce the 12-month seal on any read against restored data exactly as a live read does (DEC-0119).

May never: mutate the only copy — every off-machine copy is a new versioned artifact, and every migration backs up first (preflight → backup-first → dry-run → migrate → verify) (DEC-0118); read across worlds (a cross-world restore read is a policy-rejection refusal) or restore `world = simulated` into governed evidence (DEC-0117, DEC-0110); embed credentials in evidence; delete the only local raw evidence copy; select the object-storage provider, object-key layout, encryption key custody, or numeric RPO/RTO/retention targets — those are named at the node/ops sitting (DEC-0118); own the schedule or operate a QMF application runtime; or define data-retention policy (DEC-0118, DEC-0045).

## Interfaces

| Interface | Direction | Contract | Peer |
|---|---|---|---|
| Store-to-Backup input | in | [CT-26](../contracts/ct-26-store-backup-input.yaml) | COMP-QMF-DATA-STORE |
| Off-machine backup boundary | out | [CT-14](../contracts/ct-14-backup-restore.yaml) | COMP-OBJECT-STORAGE |

CT-26 presents one room-role's records per world as a consistent, restorable input, read verbatim under one-writer-per-stream and never mutated (DEC-0113). CT-14 carries the encrypted, versioned copy across to object storage; boundary failures return typed refusals rather than raising (DEC-0109).

## Behavior

### Ratified backup design

The backup primitive produces an encrypted, versioned copy and the application/ops cadence runs it nightly off-machine to the object-storage bucket (DEC-0118). The CT-26 input covers every room-role — ingest door, immutable raw archive, processed, journal, split-governed research door, backup, and the registry room — all instantiated per world; a cross-world backup read is a policy-rejection refusal (DEC-0117, DEC-0110). Timestamps pass through verbatim as int64 UTC nanosecond data, never re-derived (DEC-0106). Topology: the trading-node VPS records and syncs down, the workstation holds the working archive, and the bucket catches nightly copies (DEC-0118).

### Verification and restore

Verification is a first-class primitive: automated sample-restore tests plus a periodic full-restore rehearsal are part of the ratified design (DEC-0118). A restore never rewrites the only copy; each off-machine copy is a distinct version. Restored backups still enforce the 12-month seal — a read against restored data refuses sealed rows as a policy rejection exactly as a live read does (DEC-0119). Encryption is required; encryption key custody and the crypto dependency are named at the node/ops sitting — a pointer carried here, not resolved by this boundary (DEC-0118).

### Node/ops-owned numbers

The design is ratified; the numbers are node/ops territory. Object-key layout, retention depth, the numeric recovery-point objective (`registry:backup_recovery_point_objective`), recovery-time objective (`registry:backup_recovery_time_objective`), retention period (`registry:backup_retention_period`), and verification cadence (`registry:restore_verification_cadence`) are named at the node/ops sitting (DEC-0118). No provider selection is baked into QMF: the object-storage target stays external and replaceable (DEC-0045).

```mermaid
sequenceDiagram
    participant Store as COMP-QMF-DATA-STORE
    participant Backup as COMP-QMF-DATA-BACKUP
    participant Object as COMP-OBJECT-STORAGE
    Store->>Backup: CT-26 room-role records, per world (verbatim, unlimited reader)
    Backup->>Backup: encrypt + version (primitive)
    Backup->>Object: CT-14 off-machine copy (nightly cadence = app/ops-owned)
    Backup->>Backup: automated sample-restore + periodic full-restore rehearsal
    Note over Store,Object: 12-month seal enforced on restored reads; timestamps verbatim; key custody + numeric RPO/RTO at node/ops sitting
```

## Configuration

| Variable | Registry key | Notes |
|---|---|---|
| Backup cadence | `registry:backup_cadence` | Nightly (ratified design); QMF provides the primitives while schedule and execution are application/ops-owned (DEC-0118). |
| Recovery-point objective | `registry:backup_recovery_point_objective` | Design ratified; the numeric RPO is named at the node/ops sitting (DEC-0118). |
| Recovery-time objective | `registry:backup_recovery_time_objective` | Design ratified; the numeric RTO is named at the node/ops sitting (DEC-0118). |
| Backup retention | `registry:backup_retention_period` | Design ratified; the numeric retention depth is named at the node/ops sitting (DEC-0118). |
| Restore-verification cadence | `registry:restore_verification_cadence` | Automated sample-restore plus periodic full-restore rehearsal are ratified; the numeric cadence is named at the node/ops sitting (DEC-0118). |

The object-storage provider, object-key layout, credential location, encryption method and key custody, and manifest schema are named at the node/ops sitting; no credential-bearing operation is baked into this boundary (DEC-0118).

## Failure modes

| # | Condition | Behavior | Cites |
|---|---|---|---|
| FM-1 | A CT-26 read would cross worlds or read `world = simulated`. | The read is a `policy rejection` refusal; storage separation delivers world isolation. | DEC-0117, DEC-0110 |
| FM-2 | `COMP-OBJECT-STORAGE` is unreachable, rejects the upload, or the copy is corrupt. | No CT-14 completion is claimed; the boundary returns a `storage failure` typed refusal, never raised across the boundary. | DEC-0109, DEC-0118 |
| FM-3 | A migration would mutate the only copy. | The migration backs up first (preflight → backup-first → dry-run → migrate → verify) and never mutates the only copy. | DEC-0118 |
| FM-4 | A read against restored data touches the sealed holdout. | The restored read refuses sealed rows as a `policy rejection`, exactly as a live read does. | DEC-0119 |
| FM-5 | A retention action would delete the only local raw evidence copy. | The deletion does not proceed under this component's authority; raw originals are kept forever. | DEC-0118 |
| FM-6 | A caller asks the boundary to own the nightly schedule or a numeric RPO/RTO. | The boundary provides the primitive only; the cadence and numeric targets are application/ops- and node/ops-owned. | DEC-0118 |
| FM-7 | A copy is transferred while encryption key custody is unresolved. | The boundary carries the encryption-required pointer; key custody is named at the node/ops sitting and no credential is embedded in evidence. | DEC-0118 |

## Related

Decisions: DEC-0118, DEC-0119, DEC-0117, DEC-0113, DEC-0110, DEC-0109, DEC-0106, DEC-0045. Spine: [ARCHITECTURE-SPINE.md](../../_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md) AD-20, AD-19, AD-21. Scenarios: [SCN-0004 backup boundary](../scenarios/SCN-0004-off-machine-backup.md). Knowledge: none in the current provisional set.
