---
id: SCN-0002
title: Late Source Correction Preserves Earlier Evidence
type: scenario
status: provisional
component: COMP-QMF-DATA
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE]
decisions: [DEC-0035, DEC-0038, DEC-0042, DEC-0044, DEC-0045, DEC-0051, DEC-0053, DEC-0108, DEC-0114, DEC-0117, DEC-0119]
sources: [docs/components/qmf-data.md, docs/components/qmf-data-ingest.md, docs/components/qmf-data-store.md, docs/contracts/ct-07-lineage-edge.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-11-evidence-persistence.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# SCN-0002: Late Source Correction Preserves Earlier Evidence

This scenario exercises the append-only correction rule for external facts, now ratified. The architecture sitting ratified that every external fact carries event-time, known-at, source, and revision, that corrections are appended and never overwrite, and that intake is idempotent keyed on (source, source-native id, revision) so a provider revision is a new artifact rather than a fingerprint collision. Execution status: **corrections append-only, revision-keyed intake ratified**. [DEC-0117] [DEC-0119]

## Given

A controlled source replay contains an original observation and a later correction referring to the same provider-native occurrence. The original is already preserved by the qmf-data boundary. CT-10 carries the ratified bitemporal fact shape: event-time, known-at, source, and revision, where source is a core provenance noun orthogonal to VenueId (a provider you only read from is a source, a provider you trade at is a venue). [DEC-0038] [DEC-0042] [DEC-0117]

The observation's identity is its `fp1` fingerprint, computed only by the single qmf-core implementation (DEC-0108); the correction's relationship to the original lives in an append-only typed lineage edge referencing fingerprints, not in a rewrite of the header (DEC-0114). [DEC-0108] [DEC-0114]

## When

`COMP-QMF-DATA-INGEST` submits the correction through the Data-owned CT-10 boundary, keyed on (source, source-native id, revision).

## Then

The original evidence remains preserved and the correction does not overwrite or masquerade as the original: the revision is a distinct artifact with its own `fp1` fingerprint, admitted through idempotent intake, and linked to the original by a typed lineage edge (DEC-0119). CT-11 persistence either preserves the complete pair or makes no completion claim. Foreign timestamps and foreign money in the observation are stored verbatim as evidence, with any conversions derived under lineage rather than rewritten. [DEC-0035] [DEC-0117] [DEC-0119]

## Worked numbers

The fixture has two logical evidence versions — original and correction — but this is event cardinality, not a configurable QMF threshold. The two carry distinct `fp1` fingerprints and are joined by an append-only typed lineage edge (the ratified edge vocabulary is `supersedes`, `promoted-from`, `occurrence-of`, `corroborates`, `disagrees-with`); intake idempotency is keyed on (source, source-native id, revision) per DEC-0119. Exact CT-10 and CT-11 field lists are detailed per contract at documentation time under DEC-0117.
