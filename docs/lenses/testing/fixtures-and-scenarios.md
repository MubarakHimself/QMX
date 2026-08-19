---
id: LENS-TEST-FIXTURES
title: QMF Fixtures and Golden Scenarios
type: lens
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP, COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, COMP-OBJECT-STORAGE]
decisions: [DEC-0004, DEC-0007, DEC-0026, DEC-0029, DEC-0030, DEC-0033, DEC-0038, DEC-0044, DEC-0045, DEC-0046, DEC-0054, DEC-0096]
sources: [_docwork/ledger.yaml, _docwork/gaps.yaml, docs/constitution.md, docs/architecture/dependencies.yaml, docs/registry/variables.yaml, docs/components/, docs/contracts/, docs/lenses/testing/test-strategy.md]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# QMF Fixtures and Golden Scenarios

DEC-0096 supplies the live high-level requirement for executable tests and reference usage. The fixture classes, proof-key formats, metadata mapping, and golden-scenario binding below are a proposed implementation scheme under `GAP(GAP-0003)` and `GAP(GAP-0004)`, not an adopted test or release gate. Controlled fixtures are test evidence only; they are not product market data, Bots, or strategies (DEC-0007, DEC-0096).

## Proposed fixture classes

The proposed scheme assigns each fixture one source class and allows several proof references to point to the same case. The taxonomy and key shapes are not mandatory until `GAP(GAP-0003)` and `GAP(GAP-0004)` are resolved.

| Class | Stable proof key | Purpose |
|---|---|---|
| Contract valid round-trip | `<contract-id>/round-trip/<case>` | Prove canonical encode/decode and semantic equality for a valid contract value. |
| Contract boundary | `<contract-id>/boundary/<case>` | Prove every ratified enum, unit, nullability, range, version, and compatibility edge. |
| Contract invalid/refusal | `<contract-id>/invalid/<case>` | Prove malformed or prohibited input does not cross the public boundary and produces the ratified refusal/evidence. |
| Component failure mode | `<component-id>/<failure-mode-id>` | Execute one component-spec Condition and assert its Behavior plus absence of prohibited side effects. |
| Law or invariant property | `<decision-id>/property/<case>` or `<contract-id>/invariant/<case>` | Generate or replay inputs that would falsify a constitution law, contract invariant, or component `May never` boundary. |
| External controlled replay | `<component-id>/replay/<case>` | Replay a recorded external response through a QMF adapter without testing provider internals. |
| Synthetic infrastructure | `<component-id>/synthetic/<case>` | Stress parsing, capacity, corruption, outage, retry, or failure handling without making an edge claim. |

The exact test and fixture directory is `GAP(GAP-0002): Which repository layout and package namespaces contain tests, fixtures, recordings, and generated cases?` The selected path must keep fixtures outside shipped QMF product artifacts (DEC-0007).

## Proposed fixture identity and provenance

The proposed binding records existing IDs needed to reproduce its claim. These are candidate test metadata, not application-domain fields.

| Mapping item | Proposed value | Proposed rule |
|---|---|---|
| Proof key | CT, COMP/FM, or DEC key from the fixture classes | Never invent an untraceable test-only requirement. |
| Scenario | `SCN-*` when the fixture implements a golden scenario; otherwise null | One scenario may map to several proof keys. |
| Components | One or more `COMP-*` IDs | Must resolve in `docs/architecture/dependencies.yaml`. |
| Contracts | One or more `CT-*` IDs | Must resolve in `docs/contracts/`. |
| Authority | Applicable `DEC-*` and `GAP-*` IDs | A GAP recommendation is never expected output. |
| Given | Canonical fixture identity plus setup references | Values use CT schemas and registry keys, not duplicated literals. |
| When | One public CT operation or bounded scenario action | Unit cases have no network. |
| Then | Exact output/refusal/evidence and prohibited side effects | Expected fields must exist in a ratified CT schema. |
| Clock | Frozen CT-02 value or null when time is irrelevant | Encoding and session semantics remain `GAP(GAP-0008)`. |
| Random seed | Declared seed or null when deterministic without randomness | Replaying the binding with the same seed must reproduce the same inputs. |
| Source class | `source-evidence`, `controlled-replay`, or `synthetic` | Synthetic cannot validate trading edge (DEC-0054). |
| Fingerprint | CT-05 identity when the schema is ratified | Canonical bytes and algorithm remain `GAP(GAP-0010)`. |

## Proposed determinism rules

Under the proposed scheme, unit fixtures would make no network calls. External outcomes would enter unit tests as controlled replays at CT-15, CT-18, CT-20, CT-21, or CT-14 boundaries. Integration tests could use an approved sandbox or selected store/target only after `GAP(GAP-0021)`, `GAP(GAP-0027)`, `GAP(GAP-0035)`, and `GAP(GAP-0037)` are resolved.

Time-dependent fixtures freeze a CT-02 instant and declare the trading-date/session context. Randomized and property fixtures declare their seed. Equal semantic inputs must replay to equal CT-05 identities after `GAP(GAP-0010)` and `GAP(GAP-0012)` are resolved (DEC-0029, DEC-0030).

Source fixtures preserve provider identity, event time, knowledge time, and raw source material. Corrections append a new fixture record and relationship rather than rewriting the earlier evidence (DEC-0038, DEC-0044, DEC-0045).

Credential-bearing fixtures, snapshots, expected outputs, journal assertions, and golden scenarios are not created while GAP-0035 is open. Whether placeholders, redacted forms, or any credential-related fields may enter evidence remains part of the unratified CT-21 storage, injection, and redaction boundary.

## Proposed golden scenario binding

The proposed format is a `SCN-*` document under `docs/scenarios/` with concrete Given, When, and Then statements. It would map inputs to fixture identities, actions to CT boundaries, and assertions to outputs/refusals, component behavior, laws, or evidence. DEC-0096 requires executable tests and reference usage but does not ratify this exact structure.

If a scenario needs an unresolved field, enum, value, target, or state, it carries the applicable `GAP(GAP-*)` marker and remains blocked. It must not fill CT-01 through CT-26 from a recommendation. A blocked scenario is not test-complete or releasable.

| Scenario domain | Contract fixtures | Proposed assertions | Blocking design areas |
|---|---|---|---|
| Exact values and identity | CT-01 through CT-05 | Exact money, unambiguous time, asset-neutral identity, typed refusal, deterministic versioned identity | `GAP(GAP-0005)`, `GAP(GAP-0007)` through `GAP(GAP-0012)` |
| Registration and lineage | CT-06 through CT-09 | Type-specific admission, append-only lineage, causality and attempt evidence, persistence without graph-database assumptions | `GAP(GAP-0014)` through `GAP(GAP-0017)`, `GAP(GAP-0019)`, `GAP(GAP-0021)`, `GAP(GAP-0022)` |
| Data acquisition and research access | CT-10 through CT-15, CT-26 | Data-owned CT-10 topology, bitemporal source evidence, no destructive overwrite, split/holdout isolation, durable journal evidence with mutation semantics blocked, CT-15 provider↔Data-Ingest roles, provisional Store→Backup boundary, no recovery/cutover claim | `GAP(GAP-0020)` through `GAP(GAP-0030)` |
| Indicators | CT-16 | Warm-up/readiness, batch/incremental equivalence, package-neutral result, approved oracle comparison | `GAP(GAP-0031)`, `GAP(GAP-0032)`, `GAP(GAP-0033)` |
| Causal structure | CT-17 | Ordered inputs, confirmation time, invalidation, replay, parameter identity, no look-ahead | `GAP(GAP-0034)` |
| Venue transport | CT-18 through CT-21 | Reserved/unwired command boundary with no assigned caller or authorization evidence; capability gating, canonical event/reconciliation shapes, secret exclusion, and no manufactured risk approval | `GAP(GAP-0035)` through `GAP(GAP-0039)` |
| Risk boundary | CT-22 through CT-25 | Specification-only Book/BMS, risk, mode, and journal cases until FEAT-0027 produces ratified one-pass features | `GAP(GAP-0018)`, `GAP(GAP-0019)`, `GAP(GAP-0039)` through `GAP(GAP-0046)` |

## Proposed component failure fixtures

The proposed FM binding references the component file and FM ID without copying prose into a new source of truth, supplies only concrete input allowed by ratified CT fields, and compares the result with documented behavior. When an FM row names a GAP, the binding remains a blocked specification; it is not test-complete or releasable until the GAP is answered and the eventual test gate passes.

External component FM rows become adapter fixtures: the Given is a recorded or generated external outcome, the When invokes the QMF-owned adapter, and the Then asserts QMF behavior. Tests never claim to verify `COMP-CTRADER`, `COMP-DUKASCOPY`, `COMP-CALENDAR-FEED`, or `COMP-OBJECT-STORAGE` internals.

## Proposed causality and final-holdout fixtures

The proposed causality family includes evidence that is knowable at the ratified cutoff, evidence unavailable at that cutoff, a late correction, and deterministic replay. Each candidate record would carry distinct event and knowledge times and a source identity; exact fields and comparisons remain `GAP(GAP-0016)` and `GAP(GAP-0023)` (DEC-0033, DEC-0038).

The proposed final-holdout family references `registry:raw_history_retention_policy`, constructs CT-12 release manifests, exercises default research reads, and checks that no sealed identity appears. Duration is referenced through `registry:historical_holdout_months`; boundary arithmetic, reopening, one-look authorization, and audit remain `GAP(GAP-0024)` (DEC-0044, DEC-0046).

Synthetic fixtures carry `source class: synthetic` and may test only infrastructure or failure handling. No synthetic fixture, derived result, or golden scenario may satisfy a trading-edge validation assertion (DEC-0054).

## Provisional acceptance guidance

The proposed acceptance check would require ratified CT schemas and registry values, reproducible provenance, named authority, and replayable evidence. The exact command and release gate remain `GAP(GAP-0003)` and `GAP(GAP-0004)`. A blocked scenario remains visible with its GAP IDs, is never converted into a pass by inventing fields or values, and is not test-complete or releasable (DEC-0004, DEC-0096).
