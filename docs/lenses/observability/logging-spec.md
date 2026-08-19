---
id: OBS-LOGGING-QMF-V1
title: QMF V1 Logging and Journal Specification
type: lens
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP]
decisions: [DEC-0022, DEC-0029, DEC-0030, DEC-0033, DEC-0035, DEC-0038, DEC-0042, DEC-0045, DEC-0048, DEC-0051, DEC-0052, DEC-0053, DEC-0055, DEC-0058, DEC-0059, DEC-0065, DEC-0096]
sources: [DEC-0022, DEC-0029, DEC-0030, DEC-0033, DEC-0035, DEC-0038, DEC-0042, DEC-0045, DEC-0048, DEC-0051, DEC-0052, DEC-0053, DEC-0055, DEC-0058, DEC-0059, DEC-0065, DEC-0096, _docwork/gaps.yaml, docs/architecture/dependencies.yaml, docs/contracts/ct-04-typed-refusal.yaml, docs/contracts/ct-05-version-fingerprint.yaml, docs/contracts/ct-06-registration.yaml, docs/contracts/ct-07-lineage-edge.yaml, docs/contracts/ct-08-gate-evidence.yaml, docs/contracts/ct-09-registry-persistence.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-11-evidence-persistence.yaml, docs/contracts/ct-12-dataset-split.yaml, docs/contracts/ct-13-journal.yaml, docs/contracts/ct-14-backup-restore.yaml, docs/contracts/ct-15-external-source-adapter.yaml, docs/contracts/ct-16-indicator.yaml, docs/contracts/ct-17-causal-structure.yaml, docs/contracts/ct-18-venue-capabilities.yaml, docs/contracts/ct-19-venue-command.yaml, docs/contracts/ct-20-venue-event.yaml, docs/contracts/ct-21-venue-secret-session.yaml, docs/contracts/ct-22-book-charter.yaml, docs/contracts/ct-23-risk-evaluation.yaml, docs/contracts/ct-24-book-mode.yaml, docs/contracts/ct-25-risk-journal.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# QMF V1 Logging and Journal Specification

QMF V1 reserves CT-13 as the journal boundary and CT-25 as an unwired future risk-evidence placeholder; neither is a runtime event bus or arbitrary application-log store. No log levels, logger names, structured-field schema, file path, service, retention period, sampling rule, or query system is ratified. [DEC-0042] [DEC-0048]

## Evidence classes

| Class | Contract boundary | Normative distinction |
|---|---|---|
| Typed refusal | CT-04 | A machine-readable public failure outcome; exact codes, fields, retryability, redaction, and exception mapping remain GAP-0011. [DEC-0029] |
| Identity and lineage evidence | CT-05 through CT-08 | Versioned identity, immutable provenance, registration, causality, and attempt evidence; exact schemas remain GAP-0010 and GAP-0014 through GAP-0017. [DEC-0030] [DEC-0035] [DEC-0038] |
| Source and dataset evidence | CT-10 through CT-12 | Source identity, event time, knowledge time, persistence identity, release, split, and holdout evidence; exact fields remain GAP-0020 through GAP-0024. [DEC-0038] [DEC-0042] |
| Operational/research journal | CT-13 | Reserved component and adapter evidence boundary; mutation, notification, workflow, recovery, and persistence semantics remain GAP-0025/GAP-0026. [DEC-0048] |
| Backup/restore evidence | CT-14 | COMP-QMF-DATA-BACKUP owns the reserved provider-neutral transfer/restore evidence boundary; completion and validation semantics remain GAP-0027. [DEC-0045] |
| Venue evidence | CT-18 through CT-21 | Reserved and unwired shapes: CT-18/CT-20 have no active consumers, CT-19 has no caller or authorization evidence, and CT-21 is a no-operation gate. [DEC-0059] |
| Risk and Book evidence | CT-22 through CT-25 | Reserved and unwired placeholders: CT-23 has no caller, CT-24 is evidence-only pending confirmation/GAP-0041, and CT-25 is not wired to Data. [DEC-0065] |

## Component emission matrix

| Component | Evidence it may produce after contracts are ratified | Unresolved logging definition |
|---|---|---|
| COMP-QMF-CORE | CT-04 refusal and CT-05 version/fingerprint values returned to callers. | Core does not own a runtime logger. Exact refusal fields remain GAP-0011. [DEC-0022] |
| COMP-QMF-REGISTRY | CT-06 registration, CT-07 lineage, CT-08 gate/attempt, and CT-09 persistence evidence. | Kinds, fields, correlation, atomicity, and storage remain GAP-0014 through GAP-0017 and GAP-0021/GAP-0022. [DEC-0033] |
| COMP-QMF-DATA | Owns/provides CT-10 to downstream consumers and owns CT-11 through CT-13 data/journal boundaries. Data-Ingest and Venue may produce CT-10 into Data; downstream components never depend on Data-Ingest for CT-10. Data is the only wired CT-13 producer into Store; Registry, Venue, and Risk remain intended/unwired CT-13 producers. | Event kinds, fields, producer/consumer handoffs, cadence, retention, failure behavior, and storage remain GAP-0020 through GAP-0026. [DEC-0042] [DEC-0048] |
| COMP-QMF-INDICATORS | CT-16 output/refusal evidence linked to CT-10 inputs and CT-05 identity. | Warm-up, readiness, state, output, reference version, and tolerance remain GAP-0031 and GAP-0032. [DEC-0055] |
| COMP-QMF-STRUCTURE | CT-17 output plus CT-07 lineage and CT-08 causality evidence. | First family, fields, confirmation, and invalidation remain GAP-0034. [DEC-0058] |
| COMP-QMF-VENUE | May eventually produce CT-10 observations into Data; CT-18 through CT-21 create no active logging handoff. | Caller, authorization evidence, complete order states, retries, reconciliation, price basis, fields, and consumers remain GAP-0035 through GAP-0039. [DEC-0059] |
| COMP-QMF-RISK | CT-22 through CT-25 are reserved placeholders only and create no active logging handoff. | Book/BMS, exits, modes, SQS, news, formulas, stop-out, priority, callers, and consumers remain GAP-0039 through GAP-0046. [DEC-0065] |
| COMP-QMF-DATA-INGEST | May normalize CT-15 source results into CT-10 for COMP-QMF-DATA; it is a producer, not the downstream CT-10 dependency. | Provider fields, legal posture, corrections, retries, and reconciliation remain GAP-0028 through GAP-0030. [DEC-0051] [DEC-0052] [DEC-0053] |
| COMP-QMF-DATA-STORE | Persistence outcomes for CT-09, CT-11, and CT-13. | Engines, paths, schema, migrations, compaction, capacity, and recovery remain GAP-0021, GAP-0022, and GAP-0026. |
| COMP-QMF-DATA-BACKUP | Owns the reserved CT-14 transfer/restore evidence boundary. | Provider, manifest, encryption, RPO, RTO, retention, cadence, completion, and validation details remain GAP-0027. [DEC-0045] |
| External components | CT-15 may carry ratified source responses; CT-14 and CT-18 through CT-21 are reserved boundaries and create no active evidence handoff. | QMF cannot specify or depend on provider-internal logs. |

## Structured fields and levels

`GAP(GAP-0025): Define the exhaustive CT-13/CT-25 event kinds, required fields, occurrence and causation identifiers, level/severity representation, ordering, cadence, redaction, and query guarantees.`

`GAP(GAP-0011): Define CT-04 codes, safe detail fields, retryability, redaction, and exception mapping.`

No log-level enum is documented because no level taxonomy is ratified. No field beyond a ratified contract may be treated as stable. Every incompatible event or field meaning must mint a new version rather than silently change. [DEC-0030]

## Locations, stores, and retention

No log path, journal engine, table, file format, index, dashboard, or query service is ratified. The study-proposed persistence stack is not an adopted engine contract. `GAP(GAP-0021): Select the store and formats.` `GAP(GAP-0022): Define schemas and migrations.` [DEC-0047]

Journal retention, redaction, partitioning, compaction, and capacity remain `GAP(GAP-0025)` and `GAP(GAP-0026)`. Raw evidence and lineage must not be silently overwritten or discarded. [DEC-0035] [DEC-0045]

## Secret and sensitive-data handling

No credential-bearing integration may proceed while GAP-0035 is open. Secret location, storage, injection, redaction, and lifecycle remain unresolved; this lens adopts no recommendation as a settled invariant. [DEC-0059]

`GAP(GAP-0025): Define journal redaction for account, provider, and other sensitive fields without inventing a schema.`

## Failure behavior

When evidence cannot be persisted, a component must not write an uncontracted fallback store or claim durability. The caller-visible refusal, buffering, backpressure, retry, and safe-continuation behavior remain GAP-0025, GAP-0026, GAP-0036, and GAP-0046. [DEC-0048]

An external provider's internal log is not QMF evidence. Only a source-identified response that crosses a ratified contract can enter the QMF evidence chain. [DEC-0038]

## Traceability requirement

An eventual trace must follow ratified identities from source evidence into COMP-QMF-DATA's CT-10 boundary, then through derived output, CT-05 fingerprint, CT-07 lineage, and CT-13 evidence. CT-25 cannot be part of an active trace until its Data consumer is wired. Exact correlation fields and queries remain GAP-0015, GAP-0023, and GAP-0025. [DEC-0035] [DEC-0038] [DEC-0048]
