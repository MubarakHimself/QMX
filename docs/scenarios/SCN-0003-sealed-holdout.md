---
id: SCN-0003
title: Default Research Access Excludes the Sealed Holdout
type: scenario
status: provisional
component: COMP-QMF-DATA
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY]
decisions: [DEC-0044, DEC-0046]
sources: [docs/components/qmf-data.md, docs/registry/variables.yaml, docs/contracts/ct-12-dataset-split.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# SCN-0003: Default Research Access Excludes the Sealed Holdout

This scenario proves the research-door direction without inventing the exact holdout boundary or reopening policy. Execution status: **blocked specification**. [DEC-0044] [DEC-0046]

## Given

History is preserved according to `registry:raw_history_retention_policy`. A CT-12 release is intended to divide governed research data from the newest sealed period. The duration key `registry:historical_holdout_months` is null because the source gives only an approximate period. [DEC-0044]

`GAP(GAP-0024): Ratify split fields, boundary arithmetic, reopening, one-look authorization, and audit evidence.`

## When

A normal research consumer requests the default dataset release.

## Then

The sealed identities must be absent from the research release, while the underlying source evidence remains retained. The consumer must not infer the approximate period as an exact duration and must not reopen or recycle the sealed set without the future audited authorization. [DEC-0044] [DEC-0046]

## Worked numbers

No exact month count or boundary date is available. The executable fixture must compute the boundary only after `registry:historical_holdout_months` and CT-12 date arithmetic are ratified.
