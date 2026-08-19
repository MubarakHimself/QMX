---
id: GLOSSARY-QMF-V1
title: QMF V1 Glossary
type: glossary
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK]
decisions: [DEC-0001, DEC-0017, DEC-0019, DEC-0024, DEC-0028, DEC-0033, DEC-0035, DEC-0042, DEC-0045, DEC-0048, DEC-0055, DEC-0058, DEC-0059, DEC-0065, DEC-0066, DEC-0074, DEC-0076]
sources: [_docwork/ledger.yaml, _docwork/gaps.yaml, docs/registry/variables.yaml, docs/architecture/dependencies.yaml, docs/contracts/]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# QMF V1 Glossary

This glossary fixes names for the provisional QMF V1 documentation. A definition containing `GAP(...)` is a boundary marker, not permission to choose the missing design.

## Canonical terms

### Account

A qmf-core market noun for an execution or custody context. The exact account fields and the distinction among Book, broker account, venue account, live account, and demo account remain `GAP(GAP-0039)` and `GAP(GAP-0041)`.

### Attempt accounting

Immutable registry evidence that a governed registration or research attempt occurred. Target, scope, budget, and reset semantics remain `GAP(GAP-0017)`.

### Bar

An asset-neutral qmf-core market noun for aggregated observations. Its exact field and price-basis contract remains `GAP(GAP-0009)` and `GAP(GAP-0037)`.

### BMS

Versioned risk and money-management machinery owned within the Book domain. The documentation does not expand the initials because the authoritative sources do not fix an expansion. Schema, ownership, and multiplicity remain `GAP(GAP-0039)`.

### Book

A versioned risk and money-management container to which a Bot is bound. The recovered Scalping Book is one pattern, not the universal Book schema. Book fields, BMS cardinality, exit ownership, and account transitions remain `GAP(GAP-0039)`, `GAP(GAP-0040)`, and `GAP(GAP-0041)`.

### Bot

A future QML-domain trading artifact that contains confluence logic and binds to a Book. Bot-to-confluence cardinality and the binding schema remain `GAP(GAP-0018)`.

### Causality gate

A qmf-registry registration precondition that checks whether submitted evidence was knowable by the applicable cutoff. Claim fields, comparison rules, and pass evidence remain `GAP(GAP-0016)`. See also **look-ahead**.

### Confirmation

A confluence element that confirms a candidate trading condition. Its exact schema and composition rules remain part of `GAP(GAP-0034)` and `GAP(GAP-0018)`.

### Confluence

Bot-side trading logic composed from Levels, Triggers, and Confirmations. Whether a Bot contains one or several confluences remains `GAP(GAP-0018)`. Exit ownership remains separate and unresolved under `GAP(GAP-0040)`.

### Dataset release

A reproducible identity and manifest for a fixed dataset partitioning. Release fields, split rules, reopening, and audit semantics remain `GAP(GAP-0024)`.

### Event time

The time at which an observed market or external event occurred. Event time is distinct from knowledge time under CT-10.

### External source adapter (CT-15)

The external-to-middleware provider boundary terminating at `COMP-QMF-DATA-INGEST`. CT-15 does not terminate at `COMP-QMF-DATA`; Data-Ingest translates provider evidence and produces CT-10 into the Data-owned governed boundary. Provider operations, source schemas, rate limits, retries, and correction behavior remain `GAP(GAP-0028)`, `GAP(GAP-0029)`, and `GAP(GAP-0030)`.

### Exit

The policy or action that closes or reduces a trading position. Whether ordinary exits are Bot organs or all exit policy belongs to the Book remains `GAP(GAP-0040)`.

### Fill

An asset-neutral qmf-core market noun for an observed execution result. Its field and venue-reconciliation schema remains `GAP(GAP-0009)` and `GAP(GAP-0036)`.

### Future backtesting library

A deferred modular, on-demand QMF consumer for testing Bot-by-Book behavior. It is outside QMF V1 and is not a permanent central service, runtime engine, or Simulator UI.

### Final holdout

The sealed recent portion of retained history excluded from the default research path and reserved for a logged final evaluation. Exact boundary arithmetic and access evidence remain `GAP(GAP-0024)`.

### Fingerprint

A deterministic, versioned identity derived from canonical serialization. Canonical bytes, hash algorithm, collision policy, and result-key fields remain `GAP(GAP-0010)` and `GAP(GAP-0012)`.

### Instrument

An asset-neutral qmf-core market noun for a tradable market object. Identity shape, aliases, venue qualification, and metadata remain `GAP(GAP-0009)`.

### Journal

Durable operational and research evidence emitted through qmf-data. The Journal is not a runtime event bus or arbitrary application-log store. Append-only behavior is not adopted; event types, fields, mutation rules, cadence, retention, and redaction remain `GAP(GAP-0025)` and `GAP(GAP-0026)`.

### Knowledge time

The time at which an observation became knowable or entered the governed evidence system. Knowledge time is distinct from event time and is required for causality checks under CT-10.

### Level

A confluence or market-structure element representing a causally derived price or market area. Supported families and exact fields remain `GAP(GAP-0034)`.

### Lineage

Graph-shaped, append-only provenance among versioned identities, variants, and occurrences. Edge kinds, cardinalities, cycle rules, and persistence remain `GAP(GAP-0015)`.

### Look-ahead

Use **causality gate** for the registration control. Look-ahead is the prohibited use of evidence that was unavailable at the applicable decision cutoff.

### MIS

A future trading-node analytical or machine-learning ensemble consumer. MIS is not a QMF V1 library and is not `qmf-indicators`.

### Occurrence

A candidate qmf-registry term for a concrete instance associated with a reproducible definition or charter. The exact kind catalog and occurrence schema are not adopted and remain `GAP(GAP-0014)`.

### Order

An asset-neutral qmf-core market noun. Order-command fields, state, idempotency, and venue mapping remain `GAP(GAP-0036)` and `GAP(GAP-0038)`.

### Paper mode

A Book-level execution mode in the recorded ruling: the Book and its attached Bots use a paper account rather than running parallel Bot twins. The direct operator wording is missing from the export; transition and account semantics remain `GAP(GAP-0041)`.

### Position

An asset-neutral qmf-core market noun representing market exposure. Its exact field, accounting, and risk contract remains `GAP(GAP-0009)` and `GAP(GAP-0039)`.

### Processed data

Data derived from raw evidence through an identified transformation. Processed data does not replace or overwrite raw evidence.

### Promotion

The human-controlled act that moves a registered artifact into the live zone. Required evidence and signatures remain `GAP(GAP-0019)`.

### qmf-core

The definitions-only foundational library `COMP-QMF-CORE`. It owns exact primitive direction, asset-neutral nouns, typed refusals, canonical serialization, fingerprints, and compatibility contracts; it owns no broker, event loop, backtest, download, or trading-node runtime.

### qmf-data

The public data-policy and API library `COMP-QMF-DATA`. Middleware ingest, physical persistence, and backup execution are separate internal seams so business rules do not collapse into adapters or stores.

### qmf-indicators

The light indicator protocol and wrapper library `COMP-QMF-INDICATORS`. Heavy MIS and research analysis are consumers outside this component.

### qmf-registry

The identity, lineage, and registration-gate library `COMP-QMF-REGISTRY`. Its V1 design does not require a universal card or graph database.

### qmf-structure

The QMX-owned causal level, zone, and market-structure library `COMP-QMF-STRUCTURE`. Family selection and confirmation rules remain `GAP(GAP-0034)`.

### QMF

The reusable Quant Mind Framework toolbox from which QMX applications are built. QMF is not an application or runtime.

### QMF V1 Blueprint

The current documentation scope: qmf-core, qmf-registry, qmf-data, qmf-indicators, qmf-structure, the Venue module, and the Risk module.

### QML

The deferred Bot-oriented library under the QMF umbrella. QML is not part of the immediate QMF V1 roster.

### QMX

The operator's broader algorithmic and quantitative trading platform. QMX applications consume QMF libraries and modules.

### R

The canonical original pre-trade risk unit referenced by `registry:original_risk_unit`. R does not mean realized profit, account equity, or post-trade return.

### Raw evidence

Source-preserving observations retained without destructive replacement by processed forms and kept available for verification. Retention is controlled by `registry:raw_history_retention_policy`; this glossary does not duplicate its configured value.

### Registration

The qmf-registry act that admits a type-specific identity after applicable lineage and gate preconditions are represented. Object kinds, fields, transaction behavior, and evidence remain `GAP(GAP-0014)`, `GAP(GAP-0016)`, and `GAP(GAP-0017)`.

### Risk module

The provisional reusable Book and BMS boundary `COMP-QMF-RISK`. The module owns risk-domain direction but no implementation schema until the fenced risk reconciliation resolves `GAP(GAP-0039)` through `GAP(GAP-0046)`.

### Risk contracts (CT-22 through CT-25)

Reserved, provisional schema boundaries owned by `COMP-QMF-RISK`, not completed integration paths. The Registry and Data handoffs named by CT-22, CT-24, and CT-25, and the caller for CT-23, remain unwired; these contracts grant no implementation authority while `GAP(GAP-0039)` through `GAP(GAP-0046)` remain unresolved.

### SQS

Spread Quality Sensor. SQS is distinct from news control. Formula, inputs, thresholds, cadence, and stale-data behavior remain `GAP(GAP-0043)`.

### Source observation (CT-10)

The Data-owned governed observation boundary. `COMP-QMF-DATA-INGEST` and `COMP-QMF-VENUE` produce CT-10 into `COMP-QMF-DATA`; Indicators, Structure, Venue, and Risk read the governed boundary through their dependency on Data rather than consuming directly from Data-Ingest. Fields, ordering, duplicate handling, source keys, units, and raw-payload behavior remain `GAP(GAP-0023)`, `GAP(GAP-0028)`, and `GAP(GAP-0030)`.

### Store-to-Backup input (CT-26)

The internal boundary from `COMP-QMF-DATA-STORE` to `COMP-QMF-DATA-BACKUP`. Snapshot shape, consistency, completeness, identity, concurrent-write behavior, manifest binding, restore procedure, and verification remain unresolved under `GAP(GAP-0026)` and `GAP(GAP-0027)`; CT-26 does not itself assert successful recovery.

### Stop-out

An unresolved risk event term. Whether breakeven or other closes count and how stop-out drives BENCHED state remain `GAP(GAP-0045)`.

### Tick

An asset-neutral qmf-core market noun for a market observation. Exact source fields, bid and ask handling, depth, and reconciliation remain `GAP(GAP-0030)`.

### Trading Node

A later QMX application that owns live-trading runtime and orchestration. The Trading Node is not qmf-core and is outside QMF V1 documentation scope.

### Trigger

The confluence element that represents the trade-entry event. Its exact schema and supported structure families remain `GAP(GAP-0034)`.

### Typed refusal

A versioned machine-readable failure outcome shared across QMF boundaries. Codes, payload, retryability, redaction, and exception mapping remain `GAP(GAP-0011)`.

### Venue

An external execution or market-data destination. Venue identity and capability shape remain `GAP(GAP-0009)` and `GAP(GAP-0038)`.

### Venue module

The middleware seam `COMP-QMF-VENUE` for cTrader Open API in Python and later venue adapters. The module translates capabilities, commands, events, sessions, and refusals; it does not own trading permission or risk policy.

## Retired or prohibited names

### Backtesting engine

Use **future backtesting library**. Backtesting is outside QMF V1, and a permanent central engine is rejected.

### BENCHED

Do not assign BENCHED a canonical schema yet. The name is overloaded between Book mode and Bot seat state under `GAP(GAP-0045)`.

### Broker Exam

Retired name. Use **Venue module** for connection and **future backtesting library** for parity work.

### DPR

Dead legacy mechanism. DPR must not appear as a live QMF risk variable or contract.

### FORM-0006

Dead legacy formula. FORM-0006 is dimensionally broken and must not be implemented.

### Kernel

Retired name. Use **qmf-core** for the definitions library and **Trading Node** for application runtime.

### Minimal core

Retired name for the whole agreement. Use **QMF V1 Blueprint**; qmf-core remains intentionally small.

### Program and Campaign

Rejected prop-firm abstractions. Future prop-firm behavior, if revived, is modeled through a new Book after a fresh ruling.

### PRS

Dead legacy mechanism. PRS must not appear as a live QMF performance or risk contract.

### Snapshot Quality Sensor

Incorrect expansion of SQS. Use **SQS**.

### Simulator

A deferred product UI for exploring Bot-by-Book conditions. Simulator does not mean the QMF data or venue layer and is outside QMF V1.
