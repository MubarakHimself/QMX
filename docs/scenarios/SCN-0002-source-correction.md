---
id: SCN-0002
title: Late Source Correction Preserves Earlier Evidence
type: scenario
status: provisional
component: COMP-QMF-DATA
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE]
decisions: [DEC-0035, DEC-0038, DEC-0042, DEC-0044, DEC-0045, DEC-0051, DEC-0053]
sources: [docs/components/qmf-data.md, docs/components/qmf-data-ingest.md, docs/components/qmf-data-store.md, docs/contracts/ct-07-lineage-edge.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-11-evidence-persistence.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# SCN-0002: Late Source Correction Preserves Earlier Evidence

This scenario pins down the no-overwrite direction for corrected external facts while leaving the exact bitemporal schema for operator ratification. Execution status: **blocked specification**. [DEC-0038] [DEC-0044] [DEC-0045]

## Given

A controlled source replay contains an original observation and a later correction referring to the same provider-native occurrence. The original is already preserved by the qmf-data boundary. CT-10 has separate event-time and knowledge-time semantics, but the exact fields, identity, revision key, and ordering rules are null. [DEC-0038] [DEC-0042] [DEC-0051]

`GAP(GAP-0010): Ratify deterministic fingerprinting before assigning observation identities.`

`GAP(GAP-0015): Ratify lineage edge types and revision rules.`

`GAP(GAP-0023): Ratify the bitemporal fact and correction shape.`

`GAP(GAP-0030): Ratify source fields and reconciliation rules.`

## When

`COMP-QMF-DATA-INGEST` submits the correction through the Data-owned CT-10 boundary.

## Then

The original evidence must remain preserved; the correction must not overwrite or masquerade as the original. The future executable fixture must prove distinct evidence identities plus a traceable relationship, and CT-11 persistence must either preserve the complete pair or make no completion claim. Exact fields remain blocked by the listed gaps. [DEC-0035] [DEC-0038] [DEC-0045]

## Worked numbers

The fixture has two logical evidence versions—original and correction—but this is event cardinality, not a configurable QMF threshold. Hashes, timestamps, revision numbers, and source keys must come from ratified CT-05, CT-07, CT-10, and CT-11 schemas rather than this scenario.
