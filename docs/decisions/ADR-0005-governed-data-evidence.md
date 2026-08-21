---
id: ADR-0005
title: Governed data evidence, holdout, and durability
type: adr
status: ratified
component: COMP-QMF-DATA
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA-STORE]
decisions: [DEC-0042, DEC-0044, DEC-0045, DEC-0046, DEC-0048, DEC-0051, DEC-0052, DEC-0053, DEC-0054]
sources: [DEC-0042, DEC-0043, DEC-0044, DEC-0045, DEC-0046, DEC-0047, DEC-0048, DEC-0049, DEC-0051, DEC-0052, DEC-0053, DEC-0054]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 1y
---

# ADR-0005: Governed data evidence, holdout, and durability

Date: 2026-08-18. status: ratified — corpus signed off by the operator 2026-08-21 (conditional go-ahead in the PRD session; the independent contradiction sweep passed).

## Context

Research integrity and later live diagnosis require immutable source evidence, reproducible partitions, durable journals, and recovery beyond one workstation. The delivered six-layer design and local engine stack are studies, not adopted contracts.

## Options considered

1. **Reduced or local-only evidence** — rejected because it loses provenance and recovery.
2. **Adopt the study stack wholesale** — rejected because completed studies do not auto-adopt.
3. **Ratify behavior first and keep engines behind contracts** — selected.

## Decision

qmf-data separates ingestion evidence, processed data, governed research access, journaling, and backup. It applies `registry:raw_history_retention_policy`, protects a final holdout through `registry:historical_holdout_months`, uses explicit research splits, and maintains off-machine backup. Scheduled lifecycle remains application-owned. (DEC-0042, DEC-0044, DEC-0045, DEC-0046, DEC-0048, DEC-0051, DEC-0052, DEC-0053)

Synthetic data may test infrastructure and failure handling but may not validate trading edge. (DEC-0054)

## Consequences

Store engines, schemas, migrations, retention mechanics, and detector authority remain explicit gaps. The recorder and acquisition adapters must preserve source identity and cannot silently operate as a QMF runtime.
