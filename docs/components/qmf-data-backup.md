---
id: COMP-QMF-DATA-BACKUP
title: qmf-data Off-Machine Backup Boundary
type: component-spec
status: provisional
component: COMP-QMF-DATA-BACKUP
depends_on: [COMP-QMF-DATA-STORE, COMP-OBJECT-STORAGE]
decisions: [DEC-0045]
sources: [_docwork/ledger.yaml, _docwork/gaps.yaml, docs/architecture/dependencies.yaml, docs/registry/variables.yaml, docs/contracts/ct-14-backup-restore.yaml, docs/contracts/ct-26-store-backup-input.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# qmf-data Off-Machine Backup Boundary

`COMP-QMF-DATA-BACKUP` is the data-layer seam for the decided off-machine backup direction from `COMP-QMF-DATA-STORE` to `COMP-OBJECT-STORAGE` (DEC-0045). CT-26 and CT-14 do not yet define a complete snapshot, routine verification, disaster recovery, or cutover procedure.

## Authority boundary

May: receive only the provisional CT-26 Store-to-Backup input, and, after the missing schemas and operating policy are ratified, transfer material through CT-14 in the off-machine direction (DEC-0045).

May never: claim CT-26 input is complete or consistent; select the object-storage provider, snapshot or manifest schema, encryption, credential store, cadence, RPO, RTO, retention, deletion, restore procedure, or verification cadence without ratification; embed credentials in evidence; delete local raw evidence; define data retention policy; operate a QMF application runtime; or perform operational recovery or cutover while `GAP(GAP-0027)` is open (DEC-0045).

## Interfaces

| Interface | Direction | Contract | Peer |
|---|---|---|---|
| Store-to-Backup input | in | [CT-26](../contracts/ct-26-store-backup-input.yaml) | COMP-QMF-DATA-STORE |
| Off-machine backup boundary | out | [CT-14](../contracts/ct-14-backup-restore.yaml) | COMP-OBJECT-STORAGE |

CT-26 is provisional: shape, completeness, consistency, concurrency, and manifest binding remain null. CT-14 is likewise provisional and does not certify recovery.

## Behavior

The decided behavior is directional: retained evidence must have an off-machine backup path (DEC-0045). `registry:backup_cadence` is null under `GAP(GAP-0027)`, so no scheduled run is specified. CT-26 reserves the store input seam and CT-14 reserves the external target seam; neither authorizes an operational transfer implementation while their shapes and results remain null.

Routine verification and disaster recovery are separate operating concerns, not synonyms for off-machine direction. `GAP(GAP-0027): Which provider, manifest fields, encryption, credential boundary, cadence, retention, RPO, RTO, restore procedure, verification cadence, retry behavior, recovery authority, cutover gate, and result shape define CT-14?` `GAP(GAP-0020)`, `GAP(GAP-0022)`, and `GAP(GAP-0026)` also block CT-26 shape, consistency, partitions, and completeness. Non-destructive implementation gate: no operational recovery or cutover may be implemented until GAP-0027 is resolved.

```mermaid
sequenceDiagram
    participant Store as COMP-QMF-DATA-STORE
    participant Backup as COMP-QMF-DATA-BACKUP
    participant Object as COMP-OBJECT-STORAGE
    Store-->>Backup: provisional input (CT-26)
    Backup-->>Object: off-machine boundary (CT-14; non-operational)
    Note over Store,Object: Shape, completeness, consistency, verification, recovery, and cutover are GAP-bound
```

## Configuration

| Variable | Registry key | Notes |
|---|---|---|
| Backup cadence | `registry:backup_cadence` | `GAP(GAP-0027)`; no cadence, invocation time, or scheduler is ratified. |
| Recovery-point objective | `registry:backup_recovery_point_objective` | `GAP(GAP-0027)`; no RPO is ratified. |
| Recovery-time objective | `registry:backup_recovery_time_objective` | `GAP(GAP-0027)`; no RTO is ratified. |
| Backup retention | `registry:backup_retention_period` | `GAP(GAP-0027)`; no off-machine retention period is ratified. |
| Restore-verification cadence | `registry:restore_verification_cadence` | `GAP(GAP-0027)`; no verification cadence is ratified. |

The provider, credential location, encryption method, manifest schema, and deletion policy have no ratified registry variables and remain `GAP(GAP-0027)`.

## Failure modes

| # | Condition | Behavior | Cites |
|---|---|---|---|
| FM-1 | A caller asks CT-26 for a complete or consistent snapshot. | The process does not start or make the claim; shape, completeness, and consistency remain `GAP(GAP-0020)`, `GAP(GAP-0022)`, `GAP(GAP-0026)`, and `GAP(GAP-0027)`. | DEC-0045 |
| FM-2 | Material is transferred off-machine while verification behavior is unresolved. | The transfer may not be represented as verified recovery; routine verification and result semantics remain `GAP(GAP-0027)`. | DEC-0045 |
| FM-3 | A caller requests restore, disaster recovery, or cutover. | The request is non-operational and cannot proceed until `GAP(GAP-0027)` defines the authority, non-destructive procedure, verification, and cutover gate. | DEC-0045 |
| FM-4 | `COMP-OBJECT-STORAGE` is unavailable or rejects a transfer. | No CT-14 completion is reported; retry limits, resumability, and error result remain `GAP(GAP-0027)`. | DEC-0045 |
| FM-5 | Required credentials or encryption behavior are absent or unratified. | The process cannot assert that CT-14 has been satisfied; credential and encryption behavior remain `GAP(GAP-0027)`. | DEC-0045 |
| FM-6 | A caller asks whether the unresolved `registry:backup_cadence` was met. | The process makes no cadence claim; schedule, detection, notification, and catch-up behavior remain `GAP(GAP-0027)`. | DEC-0045 |
| FM-7 | A retention action would delete the only raw evidence copy or apply an unratified deletion rule. | The deletion does not proceed under this component's authority. | DEC-0045 |

## Related

Decisions: DEC-0045. Scenarios: [SCN-0004 backup boundary](../scenarios/SCN-0004-off-machine-backup.md). Knowledge: none in the current provisional set.
