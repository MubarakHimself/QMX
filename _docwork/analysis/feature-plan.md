# QMF V1 Feature-Inventory Plan

Status: internal Stage 4 planning input; not a substitute for `feature_inventory.yaml`.

This plan translates the reconciled transcript evidence into inventory-sized delivery slices before final `DEC-*` identifiers exist. Every buildable candidate is scoped for one specification pass, has one owning component, and names the contracts that must exist before a consumer can be specified. Candidate identifiers (`FP-*`) are temporary and must not be copied into the final inventory as decision identifiers.

The governing boundary is strict: QMF V1 is a reusable Python toolbox of five libraries and two modules. It is not a trading application, node runtime, backtesting platform, agent authoring surface, or deployment kernel. QMX2 is the primary authority where the sources differ; QMF1 is retained only for corroboration, genuinely unresolved options, and explicit superseded/dead history.

## Final component IDs

| Component ID | Final name | Kind | V1 delivery status | Direct dependency direction |
|---|---|---|---|---|
| `COMP-QMF-CORE` | `qmf-core` | library | Buildable after Gate 0 ratifications | None |
| `COMP-QMF-REGISTRY` | `qmf-registry` | library | Buildable after core contracts | Core |
| `COMP-QMF-DATA` | `qmf-data` | library | Buildable after core and registry identity contracts | Core, Registry |
| `COMP-QMF-INDICATORS` | `qmf-indicators` | library | Buildable after fact, identity, and core contracts | Core, Registry, Data |
| `COMP-QMF-STRUCTURE` | `qmf-structure` | library | Buildable after fact, identity, and causality-gate contracts | Core, Registry, Data |
| `COMP-QMF-VENUE` | Venue module | module | Buildable as a small platform-neutral port plus cTrader adapter | Core, Registry, Data |
| `COMP-QMF-RISK` | Risk module | module | In the final roster, but blocked from specification and implementation pending Book/BMS reconciliation | Core, Registry, Data, operator reconciliation |

These are the only final QMF V1 component IDs. Cross-cutting conformance tests, schemas, and adapters belong to their owning component; they do not create an eighth component.

## Gate 0: ratifications before feature specification

These are decision gates, not implementation features. The final ledger must resolve them or mark the dependent feature blocked.

| Gate | Required ratification | Features held by the gate | Reason |
|---|---|---|---|
| `G0-AUTHORITY` | Ratify QMX2 as primary authority, the exact 5-library/2-module roster, and the no-code-before-docs law | All | Prevents earlier trading-node/runtime proposals from silently returning as QMF scope. |
| `G0-DEPENDENCY` | Ratify the standard-library-first rule, criteria for wrapping a third-party package, and acceptable dependency direction | `FP-0019`, `FP-0020`, all adapter slices | Indicator and venue work otherwise hard-code an unreviewed dependency policy. |
| `G0-MONEY` | Choose amount/price/quantity precision, rounding, currency/unit representation, and overflow/error policy | `FP-0001`, then all market-data and venue consumers | Money semantics are foundational and must not be guessed independently by consumers. |
| `G0-TIME` | Choose timestamp precision, UTC rules, trading-day/session/calendar semantics, and ambiguity policy | `FP-0002`, then data, structure, and venue consumers | Causality, holdouts, and session handling require one clock vocabulary. |
| `G0-INSTRUMENT` | Choose canonical instrument identity fields, venue qualification, symbol aliasing, and asset-neutral order-flow nouns | `FP-0003`, `FP-0006`, and all downstream consumers | Registry, facts, and venue commands must refer to the same market object. |
| `G0-CANONICAL` | Choose canonical serialization, fingerprint inputs, schema/version compatibility, and deprecation rules | `FP-0005`, then registry and data consumers | Stable identity and lineage cannot be built over mutable or ambiguous encodings. |
| `G0-REGISTRY-SHAPE` | Ratify the first identity families and minimum relationship vocabulary; explicitly reject a universal card | `FP-0006`, `FP-0007`, `FP-0009` | The source supports a registry but leaves its exact catalog and fields provisional. |
| `G0-CAUSALITY` | Ratify the causality-gate claim fields, cutoff comparison, output/refusal evidence, and treatment of unavailable observations | `FP-0008` | The gate is settled in principle, but its input/output contract remains an explicit gap. |
| `G0-ATTEMPT` | Ratify what constitutes an attempt, its target/scope, reset behavior, and budget semantics | `FP-0009` | The immutable attempt counter survives in Registry, but its exact scope and reset/budget laws are not settled. |
| `G0-DATA-SHAPE` | Ratify the minimum fact envelope and select the first storage backend without treating the proposed six-layer stack as settled | `FP-0010`, `FP-0014` onward | The data laws are settled, but the complete schema and storage stack are not. |
| `G0-ACQUISITION` | Decide whether historical acquisition is a QMF adapter seam or install/runbook plumbing and ratify the first source | `FP-0018` | Bulk downloading is explicitly not a documentation-time action and ownership remains open. |
| `G0-OFFSITE` | Select the first offsite backup target, credential boundary, encryption expectation, and scheduler-neutral invocation method | `FP-0017` | Offsite backup is required, but the provider and operational boundary must not be invented by an adapter. |
| `G0-INDICATOR-SET` | Ratify the first small wrapper set and its reference/oracle math | `FP-0020` | The transcript authorizes light wrappers, not an arbitrary indicator catalog. |
| `G0-STRUCTURE-FAMILY` | Ratify the first causal levels/zones/market-structure family and its invalidation semantics | `FP-0022` | Every structure family requires its own depth pass; none may be inferred wholesale. |
| `G0-CTRADER` | Confirm Spotware API facts, test credentials/environment, and acceptable external test boundary | `FP-0024` through `FP-0026` | The adapter cannot be declared done against invented platform behavior. |
| `G0-RISK-BOOK` | Complete the dedicated trading-node, Book, BMS, exits, sizing, and correlation reconciliation | Any `COMP-QMF-RISK` feature | QMF1 and QMX2 do not provide a safe, final module contract; node policy must not leak into QMF. |

## Recommended delivery waves

Within a component, listed features are serialized even when the wider wave permits parallel work. Across components, a feature may run in parallel only after every named blocker is complete.

| Wave | Candidate slices | Delivery intent |
|---|---|---|
| Gate 0 | Decision gates above | Ratify foundation laws and preserve unresolved choices as explicit blockers. |
| Wave 1 | `FP-0001` through `FP-0005`, in order | Establish the complete `qmf-core` contract surface before any consumer freezes its own substitutes. |
| Wave 2 | `FP-0006` through `FP-0009`, in order | Establish registry identities, lineage, the provider-neutral causality gate, and attempt accounting before consumers register artifacts. |
| Wave 3 | `FP-0010` through `FP-0013`, in order | Establish facts, dataset partitions, journals, and recovery contracts before persistence code. |
| Wave 4 | `FP-0019`, `FP-0021`, and `FP-0023` may run in parallel | Specify the first consumer protocols against stable core, registry, and data contracts. |
| Wave 5A | Data: `FP-0014` through `FP-0018` in order; parallel with `FP-0020`, `FP-0022`, and `FP-0024` | Implement storage and first usable domain families without coupling the components. |
| Wave 5B | `FP-0025`, then `FP-0026` | Add cTrader market-data and execution behavior only after its session adapter and venue port conform. |
| Blocked wave R | Risk reconciliation slice described below | Do not schedule risk implementation until `G0-RISK-BOOK` is closed and the result is decomposed into one-pass features. |

## Buildable QMF V1 candidate slices

### `FP-0001` — Money, price, and quantity value contracts

Component: `COMP-QMF-CORE`  
Recommended wave: 1.1  
Size: one-pass  
Evidence: QMX2 foundation-law reconciliation; corroborated by QMF1 value-object and deterministic-boundary proposals.

Blocked by: `G0-AUTHORITY`, because the toolbox boundary must be ratified before its primitive API is frozen; `G0-MONEY`, because precision, rounding, units, and error behavior are operator choices rather than implementation guesses.

In: Specify and implement immutable amount, price, and quantity value types; validated construction; explicit arithmetic and comparison rules; currency/unit compatibility checks; deterministic rounding; and unit/property tests for boundary behavior.

Out: Foreign exchange, position sizing, P&L, portfolio aggregation, risk limits, broker balances, order submission, persistence backends, and UI formatting.

Done: The chosen precision and rounding laws are encoded once in `qmf-core`; invalid cross-unit operations return the ratified typed failure; serialization-neutral value semantics are tested; and downstream components need no private money primitive.

### `FP-0002` — UTC, trading-day, calendar, and session value contracts

Component: `COMP-QMF-CORE`  
Recommended wave: 1.2  
Size: one-pass  
Evidence: QMX2 time/causality foundation laws; QMF1 UTC and temporal-invariant corroboration.

Blocked by: `FP-0001`, to serialize changes to the same component; `G0-TIME`, because timestamp precision and trading-day/session rules remain technical choices.

In: Specify and implement canonical UTC instants, closed/open interval rules, trading-day and session identifiers, calendar/session boundary interfaces, conversion validation, and tests for daylight-saving and ambiguous-time cases.

Out: A global market-calendar database, exchange-holiday maintenance service, live clock scheduler, trading-node loop, sealed-holdout policy, and structure algorithms.

Done: Every time-bearing QMF contract can use one unambiguous temporal vocabulary; local or naive times are refused at the boundary; interval semantics are tested; and no runtime scheduler is introduced.

### `FP-0003` — Asset-neutral instrument and order-flow nouns

Component: `COMP-QMF-CORE`  
Recommended wave: 1.3  
Size: one-pass  
Evidence: QMX2 asset-neutral core direction and first-brick discussion; QMF1 cross-asset corroboration.

Blocked by: `FP-0002`, to serialize the core pass; `G0-INSTRUMENT`, because canonical instrument qualification and aliasing are unresolved.

In: Specify and implement the smallest asset-neutral vocabulary required by facts and venue ports: instrument identity value, venue-qualified symbol reference, side, order intent/type/time-in-force nouns where ratified, and validated market-event direction fields.

Out: Broker commands, fills, strategy signals, positions, portfolios, node state, crypto/equities specializations, and a universal entity/card abstraction.

Done: Data, registry, and venue specifications can cite the same stable nouns; asset-specific assumptions are absent from the primitives; invalid combinations are explicitly refused; and the API does not imply an execution runtime.

### `FP-0004` — Typed refusal and invariant-violation envelope

Component: `COMP-QMF-CORE`  
Recommended wave: 1.4  
Size: one-pass  
Evidence: QMX2 typed-refusal foundation law; QMF1 strong-invariant and explicit-boundary corroboration.

Blocked by: `FP-0003`, to serialize the core pass; `G0-AUTHORITY`, because refusals must describe library boundary failures rather than resurrect node workflow states.

In: Specify and implement a small typed refusal taxonomy, stable machine code, human-safe detail fields, causal chaining rules, and helpers for converting validation failures at public boundaries.

Out: Retry orchestration, incident management, notification routing, trading-node recovery, DPR/PRS recovery protocols, and exception swallowing.

Done: Every public QMF boundary can return or raise the same documented refusal shape; codes are stable and tested; internal secrets are not exposed; and no runtime recovery policy is embedded.

### `FP-0005` — Canonical serialization, fingerprints, and compatibility rules

Component: `COMP-QMF-CORE`  
Recommended wave: 1.5  
Size: one-pass  
Evidence: QMX2 canonical/fingerprint/compatibility foundation laws; QMF1 deterministic identity and lineage corroboration.

Blocked by: `FP-0001` through `FP-0004`, because canonical encodings must cover the ratified core values and refusals; `G0-CANONICAL`, because fingerprint inputs and version/deprecation behavior are not safely inferable.

In: Specify and implement deterministic canonical encoding for ratified core values, content fingerprinting, schema/version identifiers, compatibility checks, and deprecation metadata rules.

Out: A general object mapper, database schema migrations, network protocol negotiation, executable artifact packaging, registry graph storage, and proprietary cryptographic signing.

Done: Equal semantic values produce equal canonical bytes and fingerprints; incompatible versions fail explicitly; golden vectors cover ordering and edge cases; and downstream identity contracts can depend on the result.

### `FP-0006` — Registry identity families and canonical addresses

Component: `COMP-QMF-REGISTRY`  
Recommended wave: 2.1  
Size: one-pass  
Evidence: QMX2 registry inclusion and address/identity direction; QMF1 lineage and identity proposals retained without the universal-card shape.

Blocked by: `FP-0003` and `FP-0005`, because registry identity must use canonical instruments and fingerprints; `G0-REGISTRY-SHAPE`, because the initial identity catalog and required fields remain provisional.

In: Specify and implement the ratified first identity families, typed addresses, immutable identity records, namespace/version rules, lookup-by-address, and collision/refusal tests.

Out: A universal card, one-page agent metadata, generic extension plumbing, graph-database selection, UI browsing, agent lifecycle, and trading-node entities.

Done: Each ratified QMF entity family has a narrow typed identity and stable address; collisions and malformed references are refused; identities round-trip canonically; and adding an identity family does not require a universal mega-record.

### `FP-0007` — Registry lineage edges and graph invariants

Component: `COMP-QMF-REGISTRY`  
Recommended wave: 2.2  
Size: one-pass  
Evidence: QMX2 registry/lineage direction; QMF1 provenance graph corroboration with storage technology left open.

Blocked by: `FP-0006`, because edges require stable endpoints; `FP-0005`, because edge identity and payloads require canonical fingerprints.

In: Specify and implement the first ratified lineage edge types, append-only relationship records, endpoint validation, cycle/duplicate policy, ancestry queries required by V1, and invariant tests using an in-memory reference implementation.

Out: Graph-database adoption, arbitrary knowledge-graph traversal, visualization, runtime event buses, organization/project/mission ownership graphs, and agent communication.

Done: V1 entities can record and query their provenance using typed endpoints; illegal or duplicate relationships follow the ratified refusal policy; the reference implementation proves the contract without committing QMF to a graph database.

### `FP-0008` — Causality/look-ahead registration gate

Component: `COMP-QMF-REGISTRY`  
Recommended wave: 2.3  
Size: one-pass  
Evidence: QMX2 mandatory look-ahead/causality gate; QMF1 causal-integrity corroboration.

Blocked by: `FP-0002`, `FP-0004`, `FP-0006`, and `FP-0007`, because the gate needs canonical time, refusals, typed identities, and provenance; `G0-CAUSALITY`, because the exact claim and evidence shapes remain unresolved. It deliberately does not depend on `COMP-QMF-DATA`, which prevents a Registry↔Data dependency cycle.

In: Specify and implement a provider-neutral registration-time causality claim using canonical observation time, availability time, cutoff, and registry addresses; validate the ratified relationships; return refusal evidence tied to the attempted identity; and add deterministic tests for permitted, unavailable, and leaking examples.

Out: A full backtester, model evaluation, walk-forward optimization, alpha research, live data monitoring, and automatic strategy approval.

Done: A registrable artifact whose submitted claims include future or unavailable evidence is rejected deterministically; the refusal identifies the violated causal rule; accepted artifacts retain validation evidence in lineage; and later Data facts can implement the claim contract without Registry importing Data.

### `FP-0009` — Immutable registration-attempt accounting

Component: `COMP-QMF-REGISTRY`  
Recommended wave: 2.4  
Size: one-pass  
Evidence: QMX2 immutable attempt-counter decision; QMF1 lineage evidence corroboration.

Blocked by: `FP-0006`, because attempts must be attached to typed identity/address families; `FP-0004`, because failed attempts need stable refusal codes; `G0-ATTEMPT`, because target, scope, reset, and budget semantics remain unresolved.

In: Specify and implement append-only records for the ratified attempt scope, its target address, sequence/count behavior, reset or no-reset rule, budget state, success/failure outcome references, idempotency behavior, and the ratified minimum queries.

Out: Retry scheduling, quotas, billing, agent-run accounting, workflow orchestration, and mutable counters that can erase failed attempts.

Done: Every in-scope attempt is durably representable whether accepted or refused; historical attempt evidence cannot be overwritten through the public API; the ratified reset/budget behavior and idempotency are tested; and the causality gate can attach its outcome without redefining accounting.

### `FP-0010` — Bitemporal market-fact envelope

Component: `COMP-QMF-DATA`  
Recommended wave: 3.1  
Size: one-pass  
Evidence: QMX2 causal data/fact laws and raw-evidence retention; QMF1 bitemporal data corroboration.

Blocked by: `FP-0001` through `FP-0005` and `FP-0006`, because facts carry core values, time, instruments, refusals, canonical fingerprints, and identities; `G0-DATA-SHAPE`, because the minimum envelope fields require ratification.

In: Specify and implement the minimum immutable fact envelope, observation/event time, availability/knowledge time, source identity, instrument identity, payload fingerprint, correction/supersession link, validation, and golden examples.

Out: The previously proposed complete six-layer data architecture, a particular database, ingestion scheduling, feature engineering, resampling catalogs, and deletion/compaction policy.

Done: Facts preserve what was observed, when it occurred, when it became available, and where it came from; corrections do not erase prior evidence; canonical round trips and causal comparisons are tested; and storage remains replaceable.

### `FP-0011` — Dataset partition, sealed-holdout, and release contract

Component: `COMP-QMF-DATA`  
Recommended wave: 3.2  
Size: one-pass  
Evidence: QMX2 decision to retain all obtainable history and seal the newest approximately 12 months as final holdout; QMF1 research-discipline corroboration.

Blocked by: `FP-0010`, because partitions reference fact availability and time; `FP-0007`, because releases and derivations require lineage.

In: Specify and implement immutable dataset-release identity, train/validation/test/final-holdout partition metadata, the default newest-approximately-12-month sealed rule, explicit operator override metadata, leakage checks, and access-policy hooks.

Out: A backtesting engine, model training, walk-forward optimization, researcher UI, performance metrics, automated promotion, and claims that one split fits every market regime.

Done: A dataset release records exactly which facts belong to each partition; final-holdout access is denied through the default research path; override evidence is explicit and immutable; and leakage-oriented golden scenarios pass.

### `FP-0012` — Append-only operational/research journal contract

Component: `COMP-QMF-DATA`  
Recommended wave: 3.3  
Size: one-pass  
Evidence: QMX2 durable data/lineage and journal needs; QMF1 journal/event evidence retained as a reusable data concern rather than a runtime kernel.

Blocked by: `FP-0010` and `FP-0007`, because journal entries use fact/identity provenance; `FP-0004`, because refused operations need typed outcomes.

In: Specify and implement a narrow append-only journal-entry schema for library and adapter evidence, causal/reference fields, outcome/refusal attachment, canonical encoding, and an in-memory contract test harness.

Out: A global event bus, context-disposer lifecycle, trading-node execution loop, notification system, audit UI, operational recovery coordinator, and arbitrary application logging.

Done: QMF components can emit durable, typed evidence without depending on a runtime; entries are immutable and canonically addressable; causal links validate; and consumers can replace the in-memory implementation behind the contract.

### `FP-0013` — Backup, restore, and evidence-integrity contract

Component: `COMP-QMF-DATA`  
Recommended wave: 3.4  
Size: one-pass  
Evidence: QMX2 offsite-backup and raw-retention decisions; QMF1 restore-integrity corroboration.

Blocked by: `FP-0010` through `FP-0012`, because backup units and restoration assertions must reference settled fact, release, and journal contracts.

In: Specify backup manifest, content hashes, snapshot boundaries, offsite-target interface, restore verification, partial/corrupt backup refusals, and golden restore scenarios using a local test double.

Out: Choosing a cloud vendor without a decision, disaster-recovery orchestration, live high availability, retention deletion, secrets management, and trading-node state recovery.

Done: A complete QMF evidence snapshot can be described, verified, and restored through a provider-neutral contract; corruption and missing objects are detected; the original fingerprints survive restoration; and the tests require no cloud account.

### `FP-0014` — Raw-evidence persistence adapter

Component: `COMP-QMF-DATA`  
Recommended wave: 5A.1  
Size: one-pass  
Evidence: QMX2 retain-all-history/raw-evidence law and storage-study requirement.

Blocked by: `FP-0010` and `FP-0013`, because persistence must honor fact identity and recovery contracts; `G0-DATA-SHAPE`, because the first backend must be explicitly chosen.

In: Implement one ratified local persistence adapter for immutable raw facts and manifests, content-addressed write/read, duplicate handling, corruption detection, and adapter conformance tests.

Out: The whole proposed six-layer stack, warehouse optimization, cloud replication, derived indicators, dataset split enforcement, acquisition downloading, and deletion/compaction.

Done: The selected adapter passes the provider-neutral fact and integrity suites; repeated writes are deterministic; earlier evidence cannot be silently overwritten; and no consumer imports backend-specific types.

### `FP-0015` — Dataset-release access and sealed-holdout enforcement

Component: `COMP-QMF-DATA`  
Recommended wave: 5A.2  
Size: one-pass  
Evidence: QMX2 holdout/split-discipline decision.

Blocked by: `FP-0011` and `FP-0014`, because policy enforcement needs a settled release contract and persisted facts; `FP-0012`, because denied and exceptional access must produce the shared evidence shape rather than misuse Registry's separately scoped attempt counter.

In: Implement release materialization, partition-filtered reads, default final-holdout denial, explicit authorized override recording, and tests proving unavailable/future facts cannot enter a permitted partition read.

Out: Research notebooks, model fitting, backtesting, performance analytics, a permissions service, and automatic holdout consumption.

Done: Consumers can read declared non-final partitions without seeing sealed facts; every denied or overridden final-holdout access produces deterministic journal-ready evidence; partition membership is reproducible from a release identity; and leakage scenarios fail closed.

### `FP-0016` — Journal persistence adapter

Component: `COMP-QMF-DATA`  
Recommended wave: 5A.3  
Size: one-pass  
Evidence: Reconciled reusable journal/evidence requirement.

Blocked by: `FP-0012` and `FP-0014`, because journal persistence must implement the settled contract over the selected storage primitives.

In: Implement append, read-by-identity, read-by-causal-chain, and integrity verification for journal entries using the chosen local backend, plus crash/interrupted-write conformance tests.

Out: Event dispatch, pub/sub, workflow state, notification delivery, live node recovery, log search UI, and storage of arbitrary application logs.

Done: Journal writes are append-only and recoverable; interrupted writes cannot create apparently valid entries; causal queries return deterministic order; and the adapter passes the contract suite without runtime dependencies.

### `FP-0017` — Offsite backup and verified-restore adapter

Component: `COMP-QMF-DATA`  
Recommended wave: 5A.4  
Size: one-pass  
Evidence: QMX2 explicit offsite-backup requirement.

Blocked by: `FP-0013`, `FP-0014`, and `FP-0016`, because the offsite adapter must cover the ratified manifests, facts, and journals; `G0-OFFSITE`, because provider, credential, encryption, and invocation behavior cannot be invented.

In: Implement one selected offsite-target adapter, the ratified credential/encryption boundary, manifest upload/download, resumable or idempotent behavior required by the provider, a scheduler-neutral command/runbook for the required nightly cadence, and a verified restore drill against disposable test data.

Out: Enterprise disaster-recovery automation, high availability, credential provisioning by the library, vendor lock-in in core contracts, and deletion of local/raw evidence.

Done: A disposable complete snapshot is copied offsite and restored into an empty local target with matching fingerprints; missing/corrupt objects fail verification; secrets are external to persisted evidence; provider specifics remain inside the adapter; and an external scheduler can invoke the documented nightly backup without adding a QMF runtime.

### `FP-0018` — First historical-source acquisition adapter

Component: `COMP-QMF-DATA`  
Recommended wave: 5A.5  
Size: one-pass  
Evidence: QMX2 recognizes historical acquisition and Dukascopy as a likely first source while leaving ownership/plumbing open.

Blocked by: `G0-ACQUISITION`, because ownership and the first source are not final; `FP-0010`, `FP-0014`, and `FP-0016`, because acquired observations require fact, raw-store, and journal contracts.

In: Specify the source boundary and implement one ratified historical-source adapter that maps source records into immutable raw facts, records source/checksum/progress evidence, supports bounded resumable batches, and passes fixture-based mapping tests.

Out: Downloading the historical corpus during factory build, scheduled harvesting, every data vendor, transformation into indicators, backfilling live systems, and embedding credentials.

Done: A bounded fixture or operator-invoked batch is reproducibly acquired and persisted with provenance; retries do not duplicate semantic facts; malformed source records are journaled/refused; and bulk acquisition remains an installation/runbook action.

### `FP-0019` — Incremental indicator protocol and conformance harness

Component: `COMP-QMF-INDICATORS`  
Recommended wave: 4  
Size: one-pass  
Evidence: QMX2 final indicator-library inclusion and light/incremental-wrapper direction; QMF1 indicator-primitive corroboration.

Blocked by: `FP-0001` through `FP-0005`, `FP-0006`, and `FP-0010`, because the protocol consumes canonical values, identities, time, and facts; `G0-DEPENDENCY`, because wrapper boundaries require a dependency law.

In: Specify a small incremental indicator interface, warm-up/readiness semantics, missing/invalid input behavior, output fact/identity linkage, deterministic reset/snapshot rules where ratified, and a conformance harness with oracle hooks.

Out: A full indicator catalog, batch research framework, GPU/vector engine, signals, strategies, market structure, backtesting, and runtime scheduling.

Done: An implementation can be tested without knowledge of its vendor library; identical input fact streams produce identical outputs; readiness and refusals are explicit; and outputs preserve causal source references.

### `FP-0020` — First light-indicator wrapper set

Component: `COMP-QMF-INDICATORS`  
Recommended wave: 5A  
Size: one-pass  
Evidence: QMX2 direction to wrap suitable TA-Lib-class implementations rather than own all arithmetic.

Blocked by: `FP-0019`, because wrappers must conform to the component protocol; `G0-INDICATOR-SET`, because the first set and reference math must be ratified; `G0-DEPENDENCY`, because the wrapped package must pass the dependency criteria.

In: Implement the ratified small first wrapper set, parameter validation, incremental/batch-equivalence tests where applicable, reference-oracle comparisons, causal output facts, and dependency-isolation adapters.

Out: Every technical indicator, vendor API leakage, structure/zone logic, signals, hyperparameter search, visualization, and claims of canonical math for unratified families.

Done: Every selected wrapper passes the shared conformance harness and approved oracle tolerances; edge cases and warm-up behavior are documented; package-specific types do not cross the public boundary; and the scope remains a small light-indicator set.

### `FP-0021` — Causal structure-component protocol

Component: `COMP-QMF-STRUCTURE`  
Recommended wave: 4  
Size: one-pass  
Evidence: QMX2 final structure-library inclusion for QMX-owned causal levels/zones/market structure; QMF1 causal market-structure corroboration.

Blocked by: `FP-0002` through `FP-0005`, `FP-0006`, `FP-0007`, `FP-0008`, and `FP-0010`, because structure outputs require time, instruments, canonical identity, lineage, causality validation, and facts.

In: Specify the common causal component boundary for consuming ordered facts and emitting versioned structure facts, including confirmation time, invalidation/supersession, readiness, provenance, parameter identity, and causality conformance scenarios.

Out: An all-purpose algorithm framework, trading signals, strategies, plotting, a backtester, runtime scheduling, and any specific unratified level/zone family.

Done: A structure family can declare exactly what it knew and when; outputs cannot precede required confirmation facts; invalidation preserves earlier evidence; and the registry causality gate accepts valid examples and rejects leaking examples.

### `FP-0022` — First causal structure family

Component: `COMP-QMF-STRUCTURE`  
Recommended wave: 5A  
Size: one-pass  
Evidence: QMX2 requirement to own levels/zones/market-structure algorithms and give each family a depth pass.

Blocked by: `FP-0021`, because the family must conform to the shared protocol; `G0-STRUCTURE-FAMILY`, because no exact first algorithm and invalidation law is final; `FP-0015`, because realistic causal fixtures require partition-safe fact access.

In: Specify and implement one ratified structure family, its parameters and identity, confirmation and invalidation laws, incremental computation, fixture corpus, reference/golden outputs, and look-ahead failure cases.

Out: Additional structure families, discretionary chart interpretation, plotting/UI, strategies, signal scoring, backtesting, and claims that the first family defines the whole structure library.

Done: The selected family passes protocol, causality, replay-determinism, and invalidation tests; every output links to sufficient source facts; parameter changes create distinct identities; and the next family can be added as a separate one-pass feature.

### `FP-0023` — Platform-neutral venue port contract

Component: `COMP-QMF-VENUE`  
Recommended wave: 4  
Size: one-pass  
Evidence: QMX2 final small venue-module decision, cTrader-first direction, and later crypto/equities portability; QMF1 adapter-boundary corroboration.

Blocked by: `FP-0001` through `FP-0005`, `FP-0006`, `FP-0010`, and `FP-0012`, because venue capabilities, commands, events, refusals, and reconciliation evidence use these contracts.

In: Specify venue capability discovery, connection/session boundary, historical/live market-data requests, asset-neutral order commands, acknowledgements/execution events, idempotency keys, refusal mapping, and state-reconciliation evidence as a small Python port.

Out: A standalone broker library, autonomous trading loop, order/risk policy, portfolio state, deployment service, universal exchange abstraction, and cTrader-specific types in public contracts.

Done: A test double demonstrates the full port contract; unsupported capabilities fail explicitly; duplicate commands are handled by the ratified idempotency rule; events journal canonically; and no runtime loop or risk decision is embedded.

### `FP-0024` — cTrader authentication and session adapter

Component: `COMP-QMF-VENUE`  
Recommended wave: 5A  
Size: one-pass  
Evidence: QMX2 choice of Python cTrader Open API as the first venue seam.

Blocked by: `FP-0023`, because the adapter must implement the venue port; `G0-CTRADER`, because API behavior and a safe test environment must be verified from primary platform facts.

In: Implement cTrader credential/token injection boundary, connection and session lifecycle, account/capability discovery, reconnect/idempotency behavior required by the API, refusal translation, and fixture/sandbox conformance tests.

Out: Credential creation or storage, market-data mapping, order placement, trading-node liveness, long-running service deployment, and other venues.

Done: The adapter establishes and tears down a sandbox/test session through the venue port; secrets never enter QMF evidence; capabilities and platform failures map to typed results; and reconnect behavior is deterministic under tested cases.

### `FP-0025` — cTrader market-data adapter

Component: `COMP-QMF-VENUE`  
Recommended wave: 5B.1  
Size: one-pass  
Evidence: QMX2 cTrader-first venue seam and reusable data requirement.

Blocked by: `FP-0024`, because a valid cTrader session is required; `FP-0010`, `FP-0014`, and `FP-0016`, because received observations must map into facts, persistence, and journal evidence.

In: Implement ratified historical/live market-data requests, subscription lifecycle, instrument/time mapping, pagination/gap/duplicate handling, fact-envelope conversion, and sandbox/fixture conformance tests.

Out: Trading decisions, indicator computation, order commands, global resampling, automatic long-running collection, and non-cTrader venues.

Done: Representative cTrader data maps losslessly into canonical facts with source and availability times; pagination/reconnect duplicates are idempotent; gaps and malformed messages are explicit evidence; and no vendor type escapes the adapter.

### `FP-0026` — cTrader order, execution-event, and reconciliation adapter

Component: `COMP-QMF-VENUE`  
Recommended wave: 5B.2  
Size: one-pass  
Evidence: QMX2 small venue seam, typed failure, and reconciliation direction; QMF1 execution-adapter boundary corroboration.

Blocked by: `FP-0024` and `FP-0025`, to serialize the venue component and reuse settled mappings; `FP-0012` and `FP-0016`, because commands and execution events require durable evidence. It is deliberately not blocked by the Registry attempt counter or the risk module: the venue journal records command attempts, while the adapter transports already-authorized commands and owns no risk policy.

In: Implement the ratified command subset, platform-id/idempotency mapping, acknowledgement/fill/cancel/reject event conversion, refusal mapping, read-back reconciliation, and sandbox tests that do not place uncontrolled live trades.

Out: Deciding whether to trade, risk checks, sizing, strategy logic, autonomous retries, portfolio accounting, trading-node lifecycle, and crypto/equities adapters.

Done: An already-authorized canonical command can be submitted in the safe test environment; every response becomes canonical journal evidence; replay/duplicate submission follows the port rule; read-back detects divergence; and the module never manufactures approval or risk decisions.

## Blocked risk-module slice

### `FP-R-0001` — Book/BMS/risk boundary reconciliation

Component: `COMP-QMF-RISK`  
Recommended wave: blocked wave R  
Size: multi-pass discovery; must be decomposed into one-pass build features after completion  
Evidence: QMX2 retains a risk module at high level but defers the node/Book/BMS detail; QMF1 contains materially different node-first, prop-firm, Book, risk, exit, and recovery proposals that cannot be silently promoted.

Blocked by: `G0-RISK-BOOK`, because only a dedicated operator reconciliation can decide the reusable QMF boundary; `FP-0001` through `FP-0005`, `FP-0006`, `FP-0007`, `FP-0010`, and `FP-0012`, because any eventual contract must reuse settled values, identity, lineage, facts, and evidence rather than redefine them.

In: Reconcile Book versus account versus venue-account terminology; BMS ownership and state; versioned money/risk rules; sizing inputs/outputs; exit-policy representation; correlation/exposure concepts; reusable calculations versus node policy; and the exact boundary between `COMP-QMF-RISK` and a future trading node. Produce operator-ratified decisions and a one-pass feature decomposition.

Out: Implementing risk code, a prop-firm program/campaign model, a trading-node runtime, autonomous order authorization, broker supervision, recovery orchestration, MIS, backtesting, and importing QMF1's node-first architecture by default.

Done: The operator has ratified a vocabulary and ownership matrix; every reusable risk responsibility is separated from runtime/node policy; conflicting earlier proposals are explicitly accepted, superseded, dead, or deferred; and the result yields independently specifiable one-pass risk features with named upstream blockers.

No `COMP-QMF-RISK` implementation feature is inventory-ready before `FP-R-0001` is complete. The module's presence in the final roster is not permission to invent its contract.

## Explicit non-features and deferred consumers

The following items must not appear as active QMF V1 features. Keeping them visible here prevents zombie scope while preserving future dependency knowledge.

| Item | Disposition | Earliest legitimate dependency boundary |
|---|---|---|
| Trading node, runtime kernel, orchestration loop, or Nautilus-based application | Outside QMF V1; earlier node-first/runtime direction is superseded | A separate product/application pass after reusable QMF contracts exist |
| `qmf-mis` or MIS framework | Dead as a QMF V1 component; potentially node-owned later | Data and indicator contracts, then a separate node/product decision |
| QML/bot library | Deferred, not in the seven-component roster | Registry, structure, and the reconciled risk/Book binding |
| Backtesting/research framework, full overfit controls, or strategy evaluation | Deferred and intentionally absent from QMF V1 | Data releases, venue semantics, and risk contracts; dedicated future reconciliation |
| Universal card or one-card abstraction | Rejected | Narrow typed identities in `COMP-QMF-REGISTRY` replace it |
| One-page agent surface | Rejected as current QMF scope | Separate agent/product authoring decision if ever revived |
| Context, disposer, event-bus, and generalized extension plumbing | Rejected/deferred | No dependency; require a fresh use-case-led decision |
| UI, simulator, dashboards, plotting, or product shell | Outside reusable library/module scope | Separate application/product documentation |
| Prop-firm Program/Campaign model | Dead in QMF V1 | Future node/risk reconciliation only if operator revives it |
| Graph database | Technology choice rejected as a default | Registry contracts may later justify a storage adapter through a separate decision |
| DPR/PRS recovery and full operational recovery architecture | Superseded/deferred node concern | Future runtime/node design |
| Bulk historical download during documentation/build | Deferred to installation/runbook execution | `FP-0018` supplies the bounded adapter seam only |
| Calendar/news recorder rewrite | Outside this plan; existing standalone asset is not absorbed automatically | Separate integration decision after inventory completion |

## Contract-before-consumer summary

```text
COMP-QMF-CORE
  -> COMP-QMF-REGISTRY identities/lineage
       -> COMP-QMF-DATA facts/releases/journal
            -> COMP-QMF-INDICATORS protocol and wrappers
            -> COMP-QMF-STRUCTURE protocol and causal families
            -> COMP-QMF-VENUE port and cTrader adapter
            -> COMP-QMF-RISK only after Book/BMS reconciliation

REGISTRY causality/look-ahead gate
  + DATA facts that implement its claim contract
       -> STRUCTURE family registration
```

The arrows are contract dependencies, not a request for an application runtime. No consumer may copy an upstream concept locally to bypass a blocker.

## Conversion rules for the final feature inventory

1. Replace each buildable `FP-*` candidate with the inventory's required feature identifier only after its governing `DEC-*` records exist.
2. Attach the final component ID exactly as listed above; do not create components for conformance, adapters, schemas, or tests.
3. Preserve each In, Out, and Done paragraph as the starting scope boundary. Tightening is allowed; broadening requires a new decision or a separate feature.
4. Convert every named completed-feature blocker into `blocked_by` and keep the stated reason in the inventory. Convert each unresolved Gate 0 item into a gap/decision blocker rather than deleting it.
5. Schedule at most one active specification pass per feature. Same-component features remain serialized even if their wider wave is parallel.
6. Do not add a risk implementation placeholder. After `FP-R-0001`, decompose the ratified module into genuine one-pass features and only then add them to the inventory.
7. Do not add any explicit non-feature unless a later operator decision revives it and supersedes the current disposition.
