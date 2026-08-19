---
id: COMP-QMF-STRUCTURE
title: qmf-structure
type: component-spec
status: provisional
component: COMP-QMF-STRUCTURE
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA]
decisions: [DEC-0009, DEC-0013, DEC-0030, DEC-0033, DEC-0035, DEC-0038, DEC-0039, DEC-0058, DEC-0096]
sources: [DEC-0009, DEC-0013, DEC-0030, DEC-0033, DEC-0035, DEC-0038, DEC-0039, DEC-0058, DEC-0096, docs/architecture/dependencies.yaml, docs/contracts/ct-02-time-calendar.yaml, docs/contracts/ct-03-instrument-identity.yaml, docs/contracts/ct-04-typed-refusal.yaml, docs/contracts/ct-05-version-fingerprint.yaml, docs/contracts/ct-06-registration.yaml, docs/contracts/ct-07-lineage-edge.yaml, docs/contracts/ct-08-gate-evidence.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-17-causal-structure.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# qmf-structure

`COMP-QMF-STRUCTURE` is the QMX-owned library for causal level, zone, and market-structure components. It turns ordered source evidence into versioned structure evidence whose knowledge time and lineage can be checked by `COMP-QMF-REGISTRY`. [DEC-0033] [DEC-0038] [DEC-0058]

## Authority boundary

May: implement an operator-ratified structure family; consume CT-10 observations; identify definitions and outputs through CT-05; emit CT-06 registration, CT-07 lineage, and CT-08 causality evidence; and expose the family-neutral CT-17 boundary. [DEC-0033] [DEC-0035] [DEC-0058]

May never: revive the dead third-party strategy-family contract design; invent the first family, parameters, confirmation, invalidation, or composition rules; emit trading-entry, Bot, Book, exit, or risk policy; bypass the causality gate; overwrite earlier lineage; or add a runtime, scheduler, or backtester. [DEC-0009] [DEC-0013] [DEC-0014] [DEC-0035] [DEC-0058] [DEC-0083]

## Interfaces

| Interface | Direction | Contract | Peer |
|---|---|---|---|
| Exact time and trading-calendar values | in | [CT-02](../contracts/ct-02-time-calendar.yaml) | COMP-QMF-CORE |
| Instrument and venue identity | in | [CT-03](../contracts/ct-03-instrument-identity.yaml) | COMP-QMF-CORE |
| Typed refusals | out | [CT-04](../contracts/ct-04-typed-refusal.yaml) | COMP-QMF-CORE |
| Version, fingerprint, and compatibility values | in/out | [CT-05](../contracts/ct-05-version-fingerprint.yaml) | COMP-QMF-CORE |
| Registry registration | out | [CT-06](../contracts/ct-06-registration.yaml) | COMP-QMF-REGISTRY |
| Lineage edges | out | [CT-07](../contracts/ct-07-lineage-edge.yaml) | COMP-QMF-REGISTRY |
| Causality and attempt-gate evidence | out | [CT-08](../contracts/ct-08-gate-evidence.yaml) | COMP-QMF-REGISTRY |
| Source observations | in | [CT-10](../contracts/ct-10-source-observation.yaml) | COMP-QMF-DATA |
| Causal structure evidence | out | [CT-17](../contracts/ct-17-causal-structure.yaml) | No V1 consumer assigned |

## Behavior

Every supported family is QMX-owned and versioned. A family consumes source observations with distinct event and knowledge time, and its output remains compatible with the registry causality gate. [DEC-0013] [DEC-0030] [DEC-0038] [DEC-0058]

Earlier results and their provenance remain preserved through CT-07. A corrected, invalidated, or superseded result cannot erase the earlier evidence. [DEC-0035] [DEC-0039]

`GAP(GAP-0034): Ratify the first structure family, its fields, parameters, confirmation time, invalidation behavior, composition, output shape, and causal fixtures before CT-17 is implemented.`

`GAP(GAP-0015): Define the exact CT-07 edge kinds and amendment rules before structure-result lineage is persisted.`

`GAP(GAP-0016): Define the exact CT-08 claim and pass/refusal evidence before a structure output can be registered.`

<!-- no-diagram: CT-17 is a single unresolved family-neutral boundary; drawing internal families before GAP-0034 is ratified would invent architecture -->

## Configuration

| Variable | Registry key | Notes |
|---|---|---|
| First supported structure family | — | `GAP(GAP-0034): No family or parameter catalog is ratified.` |
| Timestamp precision | `registry:timestamp_precision` | Null until GAP-0008 resolves exact temporal representation. |
| Instrument identity shape | `registry:instrument_identity_shape` | Null until GAP-0009 resolves identity and alias semantics. |
| Contract version syntax | `registry:contract_version_syntax` | Null until GAP-0005 defines compatibility syntax. |

## Failure modes

| # | Condition | Behavior | Cites |
|---|---|---|---|
| FM-1 | Required evidence became knowable after the claimed confirmation cutoff. | The output cannot pass CT-08 registration and must remain unregistered with causality-refusal evidence. `GAP(GAP-0016): Define the exact evidence shape.` | DEC-0033, DEC-0038 |
| FM-2 | A caller selects a family, confirmation rule, or parameter set that has not been ratified. | The component must not execute or emit a structure result. `GAP(GAP-0034): Define the CT-04 refusal.` | DEC-0058 |
| FM-3 | A correction would overwrite an earlier output or lineage edge. | The mutation is prohibited; earlier evidence remains and a future amendment uses the ratified lineage-amendment rule. | DEC-0035, DEC-0039 |
| FM-4 | An implementation imports the dead third-party strategy-family contract design. | The conformance test fails; the family must be expressed through a QMX-owned CT-17 contract. | DEC-0013, DEC-0014, DEC-0058 |
| FM-5 | CT-10 input lacks the event-time or knowledge-time evidence required for causality. | The component must not claim a causal output. `GAP(GAP-0023): Define the input refusal and correction path.` | DEC-0038 |

## Related

Decisions: DEC-0013, DEC-0030, DEC-0033, DEC-0035, DEC-0038, DEC-0058, DEC-0096. Scenarios: [SCN-0002 source correction](../scenarios/SCN-0002-source-correction.md), [SCN-0009 synthetic stress boundary](../scenarios/SCN-0009-synthetic-stress.md). Knowledge: none drafted.
