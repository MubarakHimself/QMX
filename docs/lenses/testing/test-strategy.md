---
id: LENS-TEST-STRATEGY
title: QMF Test Strategy
type: lens
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP, COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, COMP-OBJECT-STORAGE]
decisions: [DEC-0004, DEC-0007, DEC-0008, DEC-0009, DEC-0013, DEC-0022, DEC-0026, DEC-0029, DEC-0030, DEC-0031, DEC-0033, DEC-0038, DEC-0041, DEC-0044, DEC-0045, DEC-0046, DEC-0054, DEC-0060, DEC-0061, DEC-0074, DEC-0076, DEC-0080, DEC-0092, DEC-0096]
sources: [_docwork/ledger.yaml, _docwork/gaps.yaml, _docwork/feature_inventory.yaml, docs/constitution.md, docs/architecture/dependencies.yaml, docs/registry/variables.yaml, docs/components/, docs/contracts/]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# QMF Test Strategy

DEC-0096 provides the live high-level mandate: factory-built components need executable tests and reference usage for their public contracts. The test levels, proof keys, matrices, fixture taxonomy, and release evidence below are a proposed scheme, not an adopted gate, until `GAP(GAP-0003)` and `GAP(GAP-0004)` are resolved. A specification blocked by any GAP is not test-complete or releasable; naming the GAP preserves uncertainty but does not satisfy a test or release gate (DEC-0004, DEC-0096).

## Proposed test levels

| Level | Scope | Proposed proof | Exclusions |
|---|---|---|---|
| Static and documentation gates | Ledger, gaps, inventory, component graph, contracts, registry, docs | IDs resolve; dead decisions are not revived; dependency and layer rules hold; docs and code-facing contracts exist before implementation | No product behavior claim from prose alone (DEC-0004) |
| Unit | Pure values, validation, policy, transformations, indicator and structure behavior | Named behavior and failure-mode assertions through public interfaces; no network; frozen time; declared random seed | No external service, physical store, trading runtime, or broad mock estate (DEC-0007, DEC-0022) |
| Property / invariant | CT invariants, constitution laws, component `May never` boundaries | Generated valid and invalid inputs prove the invariant and prohibited side effects remain absent | No generated result may validate trading edge (DEC-0054) |
| Contract | CT-01 through CT-26 | Schema round-trip, declared boundaries, version compatibility, invalid payload behavior, and owner/consumer agreement | A schema blocked by a GAP is not filled from a recommendation and is not test-complete |
| Integration | Real selected store adapter, source adapter replay, backup/restore target, venue sandbox | Cross-component contract handoff, persistence, restart/replay, reconciliation, and failure propagation | No uncontrolled live trade; credential-bearing fixtures/evidence remain blocked until GAP-0035 ratifies storage and redaction behavior |
| QMF acceptance scenario | A bounded chain of QMF components and contracts | Golden input, expected contract outputs/refusals, evidence lineage, deterministic replay | No trading-node application loop, backtesting engine, MIS, QML, or product UI (DEC-0008, DEC-0009, DEC-0022) |

`GAP(GAP-0001): Which runtime and operating-system matrix runs these tests?` `GAP(GAP-0002): Which repository paths and package layout contain tests and fixtures?` `GAP(GAP-0003): Which test runner, type checker, lint tools, coverage policy, and commands are mandatory?` `GAP(GAP-0004): Which checks gate pull requests, integration, and releases?`

## Proposed component failure-mode matrix

Proposed convention under `GAP(GAP-0003)` and `GAP(GAP-0004)`: map a component-spec `Failure modes` row to `<component-id>/<failure-mode-id>`, use Condition as Given, invoke a listed CT interface as When, and compare the result with the documented Behavior and prohibited side effects. This key format and proof structure are not yet mandatory. A failure mode containing a GAP remains a blocked specification and is not test-complete or releasable.

| Component spec | Proposed failure-mode proofs | Proposed level |
|---|---|---|
| [COMP-QMF-CORE](../../components/qmf-core.md) | FM-1 through FM-5 | unit, property, contract |
| [COMP-QMF-REGISTRY](../../components/qmf-registry.md) | FM-1 through FM-6 | unit, property, store integration |
| [COMP-QMF-DATA](../../components/qmf-data.md) | FM-1 through FM-8 | unit, property, store integration |
| [COMP-QMF-DATA-INGEST](../../components/qmf-data-ingest.md) | FM-1 through FM-6 | adapter contract, replay integration |
| [COMP-QMF-DATA-STORE](../../components/qmf-data-store.md) | FM-1 through FM-7 | selected-backend integration |
| [COMP-QMF-DATA-BACKUP](../../components/qmf-data-backup.md) | FM-1 through FM-7 | backup/restore integration |
| [COMP-QMF-INDICATORS](../../components/qmf-indicators.md) | FM-1 through FM-5 | unit, property, oracle contract |
| [COMP-QMF-STRUCTURE](../../components/qmf-structure.md) | FM-1 through FM-5 | unit, causality property |
| [COMP-QMF-VENUE](../../components/qmf-venue.md) | FM-1 through FM-6 | adapter contract, approved sandbox integration |
| [COMP-QMF-RISK](../../components/qmf-risk.md) | FM-1 through FM-8 | blocked contract specifications until risk reconciliation |
| [COMP-CTRADER](../../components/ctrader.md) | FM-1 through FM-6 | project adapter response simulation and approved sandbox; never provider internals |
| [COMP-DUKASCOPY](../../components/dukascopy.md) | FM-1 through FM-5 | recorded-response adapter tests; never provider internals |
| [COMP-CALENDAR-FEED](../../components/calendar-feed.md) | FM-1 through FM-5 | recorded-response adapter tests; never provider internals |
| [COMP-OBJECT-STORAGE](../../components/object-storage.md) | FM-1 through FM-6 | target-adapter failure simulation and restore integration; never provider internals |

External-component tests prove QMF adapter behavior under documented external outcomes. They do not claim control over or internal knowledge of an external system.

## Proposed contract test matrix

Proposed convention under `GAP(GAP-0003)` and `GAP(GAP-0004)`: give each ratified CT a `<contract-id>/round-trip` case and a `<contract-id>/boundary` suite. The proposed meanings are canonical encode/decode semantic equality for round-trip and ratified enum, unit, nullability, range, version, malformed-input, and refusal edges for boundary. These names and required gates are unresolved. All public versions remain blocked by `GAP(GAP-0005)` until the compatibility policy is ratified (DEC-0030).

| Contract | Owner | Proposed contract proof | Contract-specific blockers |
|---|---|---|---|
| [CT-01](../../contracts/ct-01-money-quantity.yaml) | `COMP-QMF-CORE` | Exact-value round-trip; binary floating point is inadmissible; quantization, unit, overflow, and rounding boundaries | `GAP(GAP-0007)` |
| [CT-02](../../contracts/ct-02-time-calendar.yaml) | `COMP-QMF-CORE` | Instant, civil-date, trading-date, interval, timezone, DST, session, and rollover boundaries | `GAP(GAP-0008)` |
| [CT-03](../../contracts/ct-03-instrument-identity.yaml) | `COMP-QMF-CORE` | Identity round-trip; alias, rename, asset, venue qualification, and metadata boundaries; no venue-specific core type | `GAP(GAP-0009)` |
| [CT-04](../../contracts/ct-04-typed-refusal.yaml) | `COMP-QMF-CORE` | Refusal round-trip; every code and retryability value; redaction; invalid/unknown payload behavior | `GAP(GAP-0011)` |
| [CT-05](../../contracts/ct-05-version-fingerprint.yaml) | `COMP-QMF-CORE` | Canonical-byte determinism, stable fingerprint, collision behavior, result identity, version incompatibility, and deprecation | `GAP(GAP-0005)`, `GAP(GAP-0010)`, `GAP(GAP-0012)` |
| [CT-06](../../contracts/ct-06-registration.yaml) | `COMP-QMF-REGISTRY` | Type-specific registration round-trip; unknown kind; missing preconditions; transaction result; human promotion evidence | `GAP(GAP-0014)`, `GAP(GAP-0016)`, `GAP(GAP-0017)`, `GAP(GAP-0019)` |
| [CT-07](../../contracts/ct-07-lineage-edge.yaml) | `COMP-QMF-REGISTRY` | Edge round-trip; endpoint, duplicate, cardinality, cycle, amendment, and query boundaries | `GAP(GAP-0015)` |
| [CT-08](../../contracts/ct-08-gate-evidence.yaml) | `COMP-QMF-REGISTRY` | Gate-evidence round-trip; knowable versus unavailable evidence; cutoff; attempt scope, budget, reset, and override | `GAP(GAP-0016)`, `GAP(GAP-0017)` |
| [CT-09](../../contracts/ct-09-registry-persistence.yaml) | `COMP-QMF-REGISTRY` | Persistence round-trip; append/transaction, index, migration, compaction, and recovery boundaries | `GAP(GAP-0015)`, `GAP(GAP-0021)`, `GAP(GAP-0022)` |
| [CT-10](../../contracts/ct-10-source-observation.yaml) | `COMP-QMF-DATA` | Data-owned observation round-trip; Data-Ingest/Venue producer input; Data-only direct ingest consumption; governed-reader access; event/knowledge time and evidence boundaries | `GAP(GAP-0020)`, `GAP(GAP-0023)`, `GAP(GAP-0028)`, `GAP(GAP-0030)` |
| [CT-11](../../contracts/ct-11-evidence-persistence.yaml) | `COMP-QMF-DATA` | Evidence round-trip; no destructive overwrite; raw/processed separation; partition, migration, retention, and recovery | `GAP(GAP-0020)`, `GAP(GAP-0021)`, `GAP(GAP-0022)`, `GAP(GAP-0023)`, `GAP(GAP-0026)` |
| [CT-12](../../contracts/ct-12-dataset-split.yaml) | `COMP-QMF-DATA` | Release round-trip; split membership; default final-holdout denial; boundary arithmetic, reopening, authorization, audit, and leakage | `GAP(GAP-0024)` |
| [CT-13](../../contracts/ct-13-journal.yaml) | `COMP-QMF-DATA` | Durable journal-evidence round-trip; non-event-bus boundary; mutation, amendment, immutability, ordering, redaction, retention, and query cases remain blocked | `GAP(GAP-0022)`, `GAP(GAP-0025)`, `GAP(GAP-0026)` |
| [CT-14](../../contracts/ct-14-backup-restore.yaml) | `COMP-QMF-DATA-BACKUP` | Off-machine boundary cases only after shape exists; no completeness, routine-verification, recovery, or cutover assertion while unresolved | `GAP(GAP-0026)`, `GAP(GAP-0027)` |
| [CT-15](../../contracts/ct-15-external-source-adapter.yaml) | `COMP-QMF-DATA-INGEST` | Data-Ingest caller/owner requests and active-provider responses; source identity, correction, capability, rate-limit, retry, legal-retention, and lifecycle boundaries; Data is not a participant | `GAP(GAP-0028)`, `GAP(GAP-0029)`, `GAP(GAP-0030)` |
| [CT-16](../../contracts/ct-16-indicator.yaml) | `COMP-QMF-INDICATORS` | Batch/incremental round-trip; input/output alignment, warm-up, readiness, missing values, replay equivalence, reference/oracle tolerance | `GAP(GAP-0031)`, `GAP(GAP-0032)`, `GAP(GAP-0033)` |
| [CT-17](../../contracts/ct-17-causal-structure.yaml) | `COMP-QMF-STRUCTURE` | Structure round-trip; ordered facts, confirmation, invalidation, replay, parameter identity, and look-ahead rejection | `GAP(GAP-0034)` |
| [CT-18](../../contracts/ct-18-venue-capabilities.yaml) | `COMP-QMF-VENUE` | Capability round-trip; unsupported capability; symbol, price basis, order type, account mode, limit, and negotiation boundaries | `GAP(GAP-0037)`, `GAP(GAP-0038)` |
| [CT-19](../../contracts/ct-19-venue-command.yaml) | `COMP-QMF-VENUE` | Reserved/unwired placeholder only; caller, authorization producer/evidence, command kind, quantity/price, idempotency, deadline, and refusal boundaries must be ratified before any round-trip test exists | `GAP(GAP-0036)`, `GAP(GAP-0038)`, `GAP(GAP-0039)` |
| [CT-20](../../contracts/ct-20-venue-event.yaml) | `COMP-QMF-VENUE` | Event round-trip; acknowledgement/fill/reject/reconciliation, sequence, duplicate, cursor, outage, and price-basis boundaries; no manufactured approval | `GAP(GAP-0030)`, `GAP(GAP-0036)`, `GAP(GAP-0037)`, `GAP(GAP-0038)` |
| [CT-21](../../contracts/ct-21-venue-secret-session.yaml) | `COMP-QMF-VENUE` | No round-trip exists: secret fields, persistence/exclusion, injection, redaction, expiry, refresh, rotation, revocation, target, test environment, and failure behavior are all unratified | `GAP(GAP-0035)`, `GAP(GAP-0036)`, `GAP(GAP-0037)` |
| [CT-22](../../contracts/ct-22-book-charter.yaml) | `COMP-QMF-RISK` | Fenced charter round-trip; Book/BMS ownership, cardinality, versioning, exit boundary, and non-universal Scalping Book property | `GAP(GAP-0018)`, `GAP(GAP-0039)`, `GAP(GAP-0040)` |
| [CT-23](../../contracts/ct-23-risk-evaluation.yaml) | `COMP-QMF-RISK` | Fenced risk round-trip; dimensional units, R meaning, legacy-input rejection, SQS, sizing, correlation, stop-out, priority, and refusal boundaries | `GAP(GAP-0007)`, `GAP(GAP-0011)`, `GAP(GAP-0039)`, `GAP(GAP-0040)`, `GAP(GAP-0043)`, `GAP(GAP-0044)`, `GAP(GAP-0045)`, `GAP(GAP-0046)` |
| [CT-24](../../contracts/ct-24-book-mode.yaml) | `COMP-QMF-RISK` | Fenced mode round-trip; human promotion; no parallel paper twin; state, trigger, account, rollback, duplicate, continuity, and audit boundaries | `GAP(GAP-0018)`, `GAP(GAP-0019)`, `GAP(GAP-0041)` |
| [CT-25](../../contracts/ct-25-risk-journal.yaml) | `COMP-QMF-RISK` | Fenced journal round-trip; pair-scoped news distinct from SQS; no direct store; event, cadence, correlation, redaction, priority, and retention boundaries | `GAP(GAP-0025)`, `GAP(GAP-0042)`, `GAP(GAP-0043)`, `GAP(GAP-0045)`, `GAP(GAP-0046)` |
| [CT-26](../../contracts/ct-26-store-backup-input.yaml) | `COMP-QMF-DATA-STORE` | Store-to-Backup boundary only after shape exists; explicitly no completeness or consistency assertion; recovery and cutover remain non-operational | `GAP(GAP-0020)`, `GAP(GAP-0022)`, `GAP(GAP-0026)`, `GAP(GAP-0027)` |

CT-22 through CT-25 are specification tests only until FEAT-0027 resolves the risk boundary. A test must not turn a conflict or GAP recommendation into a passing fixture.

## Proposed law and authority property tests

DEC-0096 requires executable tests and reference usage, but it does not ratify the following property taxonomy. Proposed convention under `GAP(GAP-0003)` and `GAP(GAP-0004)`: map ratified invariants and `May never` clauses to `<contract-id>/invariant/<slug>` or `<component-id>/never/<slug>`. Exact keys, runner behavior, and release gating are unresolved.

| Law family | Executable proof | Authority |
|---|---|---|
| Documentation before implementation | A feature build gate fails when its required DEC, CT, component spec, or blocking GAP record is absent. | DEC-0004 |
| No shipped fake trading estate | Packaging and reference-usage tests keep controlled fixtures outside shipped market data, Bots, and strategies. | DEC-0007 |
| Toolbox, not application runtime | Dependency and import tests reject event loops, schedulers, product UI, backtest runtime, and trading-node orchestration inside foundation components. | DEC-0008, DEC-0009, DEC-0022 |
| Owned domain boundary | Dependency tests keep QMX strategy semantics local and third-party platform objects behind adapters. | DEC-0013 |
| Exact money | Generated CT-01 values never use binary floating-point monetary representation. | DEC-0026 |
| Typed, versioned identity | Equal semantic inputs produce the same ratified canonical identity; incompatible semantics never retain the old version. | DEC-0029, DEC-0030 |
| Asset-neutral core | Core tests contain no Forex-, cTrader-, scalping-, or deployment-specific public type dependency. | DEC-0031 |
| Human promotion | Promotion cannot succeed without the human evidence contract once `GAP(GAP-0019)` is resolved. | DEC-0041 |
| Raw evidence and correction integrity | Processing and correction sequences preserve earlier raw evidence according to `registry:raw_history_retention_policy`; recovery proof remains GAP-bound. | DEC-0044, DEC-0045 |
| Split and final-holdout isolation | Default CT-12 access never includes the final holdout, independent of access order. | DEC-0044, DEC-0046 |
| Synthetic-data limit | Synthetic fixtures may prove infrastructure behavior but never satisfy an edge-validation assertion. | DEC-0054 |
| Venue boundary | The first adapter uses Python cTrader, exposes no MQL implementation, and keeps cTrader objects behind the venue-neutral seam. | DEC-0060, DEC-0061 |
| Risk vocabulary | SQS remains Spread Quality Sensor and distinct from news; R retains pre-trade-risk units; one Scalping Book pattern never becomes the universal charter; future alpha-decay math uses current definitions. | DEC-0074, DEC-0076, DEC-0080, DEC-0092 |
| Executable public contract | Every factory-built component has tests and reference usage that traverse its declared public CT interfaces. | DEC-0096 |

## Proposed causality, holdout, and synthetic evidence

The proposed causality fixture family would include a knowable case, an unavailable-at-cutoff case, a late correction, and deterministic replay with event time, knowledge time, source identity, and a decision cutoff. Exact fields, comparisons, runner, and gate remain `GAP(GAP-0016)`, `GAP(GAP-0003)`, and `GAP(GAP-0004)` (DEC-0033, DEC-0038).

The proposed final-holdout family would build a CT-12 release, exercise default research splits, and check that no final-holdout identity appears. It references `registry:raw_history_retention_policy` and `registry:historical_holdout_months`; exact boundary arithmetic, one-look authorization, reopening, and audit remain `GAP(GAP-0024)` (DEC-0044, DEC-0046).

The proposed fixture metadata distinguishes source evidence, controlled replay, and synthetic inputs. Regardless of the eventual taxonomy, synthetic inputs may exercise infrastructure and failure handling but may not be cited as proof of trading edge (DEC-0007, DEC-0054).

## Provisional completion guidance

DEC-0096 does not by itself select a release checklist. Proposed traceability would cite FEAT, COMP, FM, CT, DEC, and GAP IDs and would not substitute a coverage percentage for behavior evidence. Until `GAP(GAP-0003)` and `GAP(GAP-0004)` ratify the commands and gates, this remains guidance. A blocked specification is not test-complete or releasable; an explicit GAP records why the test cannot exist but does not count as a passing test (DEC-0004, DEC-0096).
