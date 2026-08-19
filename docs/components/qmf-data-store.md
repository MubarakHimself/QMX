---
id: COMP-QMF-DATA-STORE
title: qmf-data Persistence Seam
type: component-spec
status: provisional
component: COMP-QMF-DATA-STORE
depends_on: []
decisions: [DEC-0030, DEC-0035, DEC-0038, DEC-0042, DEC-0044, DEC-0045, DEC-0046, DEC-0047, DEC-0048]
sources: [_docwork/ledger.yaml, _docwork/gaps.yaml, docs/architecture/dependencies.yaml, docs/registry/variables.yaml, docs/contracts/ct-09-registry-persistence.yaml, docs/contracts/ct-11-evidence-persistence.yaml, docs/contracts/ct-13-journal.yaml, docs/contracts/ct-26-store-backup-input.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# qmf-data Persistence Seam

`COMP-QMF-DATA-STORE` is the dependency-free data-layer seam that persists registry records, evidence, and journals without owning their business meaning, and exposes the provisional CT-26 input seam to Backup. Physical engines and schemas remain replaceable behind CT-09, CT-11, CT-13, and CT-26 (DEC-0035, DEC-0042, DEC-0047).

## Authority boundary

May: persist registry identities, lineage, versions, and occurrences presented through CT-09; persist immutable raw and processed evidence presented through CT-11; persist durable journal evidence presented through CT-13; expose provisional backup input through CT-26 without a completeness or consistency claim; implement only ratified transactions, indexes, partitions, migrations, compaction, and integrity checks; and expose only storage-layer outcomes defined by those contracts (DEC-0035, DEC-0038, DEC-0042, DEC-0045, DEC-0048).

May never: define registration, lineage, causality, attempt, split, final-holdout, journal-event, notification, recovery-orchestration, or trading rules; require a graph database; adopt a study engine or file format without ratification; overwrite raw evidence or immutable lineage; treat processed data as a replacement for source evidence; or schedule acquisition and backup processes (DEC-0035, DEC-0042, DEC-0044, DEC-0045, DEC-0047, DEC-0048).

## Interfaces

| Interface | Direction | Contract | Peer |
|---|---|---|---|
| Registry persistence | in | [CT-09](../contracts/ct-09-registry-persistence.yaml) | COMP-QMF-REGISTRY |
| Evidence persistence | in | [CT-11](../contracts/ct-11-evidence-persistence.yaml) | COMP-QMF-DATA |
| Durable journal evidence | in | [CT-13](../contracts/ct-13-journal.yaml) | COMP-QMF-DATA |
| Store-to-Backup input | out | [CT-26](../contracts/ct-26-store-backup-input.yaml) | COMP-QMF-DATA-BACKUP |

## Behavior

### Storage neutrality

The component has no component dependencies and owns no backend rule. `registry:local_store_engine` is unresolved; Parquet, DuckDB, SQLite, and JSONL remain study candidates rather than adopted contracts (DEC-0047). `GAP(GAP-0021): Which engines and formats back registry records, raw evidence, processed data, journals, indexes, and metadata?`

CT-09 persists graph-shaped registry history without requiring a graph database (DEC-0035). `GAP(GAP-0015): Which record and edge fields, transaction boundaries, indexes, cycle representation, and compaction rules apply?`

CT-11 persists source evidence and processed records while retaining the complete raw record and appending corrections instead of overwriting evidence (DEC-0038, DEC-0044, DEC-0045). The retention law is `registry:raw_history_retention_policy`. `GAP(GAP-0020): Which data responsibilities and schemas are admitted?` `GAP(GAP-0023): Which fact and revision fields are stored?` `GAP(GAP-0026): Which partitions, capacity limits, retention mechanics, and compaction rules apply?`

CT-13 persists durable operational and research journal evidence without becoming a runtime event bus or arbitrary application-log database (DEC-0042, DEC-0048). Mutation, amendment, immutability, ordering, query, redaction, and retention semantics remain `GAP(GAP-0025)` and `GAP(GAP-0026)`.

CT-26 is the only Store-to-Backup input boundary. Its record shape, completeness, consistency, concurrency, and manifest binding are null under `GAP(GAP-0020)`, `GAP(GAP-0022)`, `GAP(GAP-0026)`, and `GAP(GAP-0027)`; the store must not describe its output as a complete snapshot.

All stored public contracts are versioned from birth. `GAP(GAP-0022): How are schemas migrated, rolled back, and verified across upgrades?` (DEC-0030).

<!-- no-diagram: COMP-QMF-DATA-STORE is one storage-neutral seam; CT-26 exposes only a provisional Store-to-Backup boundary while internal engines, schemas, indexes, snapshots, and migration structures remain GAP-bound. -->

## Configuration

| Variable | Registry key | Notes |
|---|---|---|
| Local store engine | `registry:local_store_engine` | `GAP(GAP-0021)`; no engine or file format is ratified. |
| Raw-history retention | `registry:raw_history_retention_policy` | Follows the registered policy; mechanics remain `GAP(GAP-0026)`. |

No migration, partition, index, compression, transaction, journal-retention, or compaction variable is registered. These remain `GAP(GAP-0015)`, `GAP(GAP-0022)`, `GAP(GAP-0025)`, and `GAP(GAP-0026)`.

## Failure modes

| # | Condition | Behavior | Cites |
|---|---|---|---|
| FM-1 | A CT-11 write would replace an existing raw observation or correction in place. | The store must preserve the existing evidence and may accept only the ratified append/revision form. | DEC-0038, DEC-0044, DEC-0045 |
| FM-2 | A CT-09 write would mutate immutable lineage or an existing semantic version. | The store must not perform the mutation; amendment, transaction, and new-version behavior remain `GAP(GAP-0015)` and `GAP(GAP-0022)`. | DEC-0030, DEC-0035 |
| FM-3 | The selected engine is unavailable, corrupt, or cannot durably commit a write. | The store does not report persistence success; transaction, integrity, rollback, and recovery behavior remain `GAP(GAP-0021)` and `GAP(GAP-0022)`. | DEC-0038, DEC-0045 |
| FM-4 | A CT-13 record lacks a ratified event kind, correlation identity, or required field. | The record is not valid persisted journal evidence; validation, mutation, and rejection behavior remain `GAP(GAP-0025)` and `GAP(GAP-0026)`. | DEC-0048 |
| FM-5 | Capacity, partition, retention, or compaction behavior is needed before it is ratified. | The store does not infer a deletion or compaction policy; the required mechanics remain `GAP(GAP-0026)`. | DEC-0044, DEC-0045 |
| FM-6 | A caller asks the store to decide a split, holdout, gate, promotion, notification, or retry rule. | The request is outside the data-layer authority boundary and must return to the owning backend or middleware contract. | DEC-0035, DEC-0042, DEC-0046, DEC-0048 |
| FM-7 | A CT-26 read is requested as a complete or consistent recovery snapshot. | The store does not make that claim; CT-26 shape, completeness, consistency, and recovery semantics remain blocked by `GAP(GAP-0020)`, `GAP(GAP-0022)`, `GAP(GAP-0026)`, and `GAP(GAP-0027)`. | DEC-0045 |

## Related

Decisions: DEC-0030, DEC-0035, DEC-0038, DEC-0042, DEC-0044, DEC-0045, DEC-0046, DEC-0047, DEC-0048. Scenarios: [SCN-0002 source correction](../scenarios/SCN-0002-source-correction.md), [SCN-0003 sealed holdout](../scenarios/SCN-0003-sealed-holdout.md), [SCN-0004 backup boundary](../scenarios/SCN-0004-off-machine-backup.md). Knowledge: none in the current provisional set.
