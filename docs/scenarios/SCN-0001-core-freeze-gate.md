---
id: SCN-0001
title: Core Freeze Choices Block Implementation
type: scenario
status: provisional
component: COMP-QMF-CORE
depends_on: []
decisions: [DEC-0004, DEC-0022, DEC-0025, DEC-0026, DEC-0027, DEC-0028, DEC-0029, DEC-0030, DEC-0031, DEC-0032]
sources: [docs/constitution.md, docs/components/qmf-core.md, docs/registry/variables.yaml, docs/contracts/ct-01-money-quantity.yaml, docs/contracts/ct-02-time-calendar.yaml, docs/contracts/ct-03-instrument-identity.yaml, docs/contracts/ct-04-typed-refusal.yaml, docs/contracts/ct-05-version-fingerprint.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# SCN-0001: Core Freeze Choices Block Implementation

This scenario proves that a plausible implementation choice is not authority to build the first QMF brick. Execution status: **blocked specification**. [DEC-0004] [DEC-0025] [DEC-0032]

## Given

An agent is asked to implement exact money, exact time, Instrument identity, typed refusals, result identity, and version fingerprints in `COMP-QMF-CORE`. CT-01 through CT-05 reserve those boundaries, but their schemas remain null. The governing registry keys are also null where the operator has not ruled. [DEC-0026] [DEC-0027] [DEC-0028] [DEC-0029] [DEC-0030]

`GAP(GAP-0005): Ratify versioning and compatibility policy.`

`GAP(GAP-0007): Ratify precision, units, rounding, and quantization.`

`GAP(GAP-0008): Ratify instant, timezone, trading-date, calendar, and rollover semantics.`

`GAP(GAP-0009): Ratify Instrument identity and alias behavior.`

`GAP(GAP-0010): Ratify canonical bytes, hashing, and collision policy.`

`GAP(GAP-0011): Ratify the typed-refusal taxonomy and payload.`

`GAP(GAP-0012): Ratify the result-label identity tuple.`

## When

The agent proposes concrete Python types, timestamp precision, symbol keys, hash algorithm, or error codes and attempts to treat the proposal as the public contract.

## Then

The implementation must stop before code or serialized data is created. The proposal may be recorded for operator review, but it cannot replace a null contract field or null registry value. qmf-core remains definitions-only and asset-neutral. [DEC-0004] [DEC-0022] [DEC-0031] [DEC-0032]

## Worked numbers

No arithmetic is authorized. `registry:money_decimal_scale`, `registry:price_decimal_scale`, `registry:quantity_decimal_scale`, and `registry:timestamp_precision` are deliberately null; any numeric example would manufacture a contract.
