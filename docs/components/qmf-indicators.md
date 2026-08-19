---
id: COMP-QMF-INDICATORS
title: qmf-indicators
type: component-spec
status: provisional
component: COMP-QMF-INDICATORS
depends_on: [COMP-QMF-CORE, COMP-QMF-DATA]
decisions: [DEC-0009, DEC-0013, DEC-0029, DEC-0030, DEC-0055, DEC-0056, DEC-0096]
sources: [DEC-0009, DEC-0013, DEC-0029, DEC-0030, DEC-0055, DEC-0056, DEC-0096, docs/architecture/dependencies.yaml, docs/contracts/ct-01-money-quantity.yaml, docs/contracts/ct-02-time-calendar.yaml, docs/contracts/ct-03-instrument-identity.yaml, docs/contracts/ct-04-typed-refusal.yaml, docs/contracts/ct-05-version-fingerprint.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-16-indicator.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# qmf-indicators

`COMP-QMF-INDICATORS` is the package-neutral protocol and light-wrapper library for deterministic indicator arithmetic. It consumes QMF values and causal observations, isolates suitable TA-Lib-class implementations, and exposes no research runtime. [DEC-0055] [DEC-0056]

## Authority boundary

May: define the light indicator boundary; validate component inputs and parameters; wrap a ratified reference implementation; expose batch or incremental behavior after CT-16 is completed; and return CT-04 refusals without exposing dependency-specific objects. [DEC-0029] [DEC-0055]

May never: reimplement established indicator formulas merely to own the arithmetic; expose vendor objects as QMF contracts; run heavy MIS or research analysis; define strategy, market-structure, backtesting, scheduling, or trading-loop behavior; or select a reference implementation, version, tolerance, warm-up rule, or state model while the governing gaps remain open. [DEC-0009] [DEC-0055] [DEC-0056] [DEC-0083] [DEC-0089]

## Interfaces

| Interface | Direction | Contract | Peer |
|---|---|---|---|
| Exact money, price, and quantity values | in | [CT-01](../contracts/ct-01-money-quantity.yaml) | COMP-QMF-CORE |
| Exact time and trading-calendar values | in | [CT-02](../contracts/ct-02-time-calendar.yaml) | COMP-QMF-CORE |
| Instrument and venue identity | in | [CT-03](../contracts/ct-03-instrument-identity.yaml) | COMP-QMF-CORE |
| Typed refusals | out | [CT-04](../contracts/ct-04-typed-refusal.yaml) | COMP-QMF-CORE |
| Version, fingerprint, and compatibility values | in/out | [CT-05](../contracts/ct-05-version-fingerprint.yaml) | COMP-QMF-CORE |
| Source observations | in | [CT-10](../contracts/ct-10-source-observation.yaml) | COMP-QMF-DATA |
| Indicator component boundary | out (reserved) | [CT-16](../contracts/ct-16-indicator.yaml) | Intended: COMP-QMF-STRUCTURE; not wired |

## Behavior

Indicator implementations consume source-identified observations through CT-10 and use CT-01 through CT-05 for QMF values, failures, and identity. Public behavior remains package-neutral; a wrapped library is an implementation detail. [DEC-0013] [DEC-0055]

Light deterministic work belongs in `COMP-QMF-INDICATORS`. Heavy analytical work belongs to later MIS or research consumers and cannot be added to this component. [DEC-0056] [DEC-0089]

Incompatible arithmetic or public-contract changes mint a new version instead of mutating existing meaning. [DEC-0030]

`GAP(GAP-0031): Define CT-16 fields, input/output alignment, warm-up, readiness, missing values, state, reset, streaming behavior, and replay equivalence before implementation.`

`GAP(GAP-0032): Select the canonical indicator implementation and version, comparison tolerance, and dual-reference evidence before any wrapper is called canonical.`

`GAP(GAP-0033): Define the nonblocking light-versus-heavy classification rule without enlarging CT-16.`

<!-- no-diagram: the component is one package-neutral protocol plus adapters; CT-16 internal structure is unresolved under GAP-0031 -->

## Configuration

| Variable | Registry key | Notes |
|---|---|---|
| Canonical arithmetic reference | `registry:canonical_indicator_reference` | Null until GAP-0032 selects an implementation, version, and oracle tolerance. |
| Contract version syntax | `registry:contract_version_syntax` | Null until GAP-0005 defines version and compatibility syntax. |
| Typed refusal codes | `registry:typed_refusal_codes` | Null until GAP-0011 defines the shared taxonomy. |

## Failure modes

| # | Condition | Behavior | Cites |
|---|---|---|---|
| FM-1 | A CT-10 observation is malformed, lacks required causal fields, or cannot align to the selected input series. | The component must not emit a valid indicator result. `GAP(GAP-0031): Define the exact CT-04 refusal and alignment evidence.` | DEC-0029, DEC-0055 |
| FM-2 | No ratified reference implementation, version, or tolerance exists. | The wrapper must not claim canonical arithmetic or ship as a completed wrapper. | DEC-0032, DEC-0055 |
| FM-3 | A caller requests heavy MIS or research analysis through CT-16. | The component performs no heavy analysis; the request is outside its authority boundary. `GAP(GAP-0011): Define the refusal code.` | DEC-0056, DEC-0089 |
| FM-4 | A dependency upgrade changes arithmetic for identical canonical inputs. | The implementation must not silently accept the change; incompatible meaning requires a new contract version and new evidence. | DEC-0030 |
| FM-5 | A wrapper exposes a dependency-specific object across CT-16. | The conformance test fails because the public interface must remain package-neutral. | DEC-0013, DEC-0055, DEC-0096 |

## Related

Decisions: DEC-0013, DEC-0030, DEC-0055, DEC-0056, DEC-0096. Scenarios: [SCN-0001 core freeze gate](../scenarios/SCN-0001-core-freeze-gate.md), [SCN-0009 synthetic stress boundary](../scenarios/SCN-0009-synthetic-stress.md). Knowledge: none drafted.
