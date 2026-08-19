---
id: ARCH-STACK
title: QMF V1 Stack and Pipeline
type: architecture
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP, COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, COMP-OBJECT-STORAGE]
decisions: [DEC-0008, DEC-0009, DEC-0011, DEC-0013, DEC-0022, DEC-0024, DEC-0030, DEC-0033, DEC-0035, DEC-0042, DEC-0045, DEC-0047, DEC-0055, DEC-0058, DEC-0059, DEC-0060, DEC-0065, DEC-0089, DEC-0091, DEC-0096]
sources: [DEC-0008, DEC-0009, DEC-0011, DEC-0013, DEC-0022, DEC-0024, DEC-0030, DEC-0033, DEC-0035, DEC-0042, DEC-0045, DEC-0047, DEC-0055, DEC-0058, DEC-0059, DEC-0060, DEC-0065, DEC-0089, DEC-0091, DEC-0096, docs/architecture/dependencies.yaml, docs/registry/variables.yaml, docs/contracts/]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 90d
---

# QMF V1 Stack and Pipeline

QMF V1 is a reusable Python-oriented toolbox with a middleware, backend, data, and external stack. The public roster is fixed independently from architectural kind, layer placement, and eventual package distribution. Runtime versions, build tools, package identities, physical stores, migration mechanics, and CI/CD commands remain explicit GAPs rather than implied technology selections. (DEC-0008, DEC-0011, DEC-0024)

## Stack by layer

| Layer | Language | Framework or runtime | Components | Cites |
|---|---|---|---|---|
| middleware | Python for the first Venue adapter; other execution details are `GAP(GAP-0001)` | `GAP(GAP-0001)`: CPython version and platform matrix; no application framework selected | `COMP-QMF-VENUE`, `COMP-QMF-DATA-INGEST` | DEC-0011, DEC-0060 |
| backend | Python-compatible public toolbox | `GAP(GAP-0001)`: CPython version and supported operating systems | `COMP-QMF-CORE`, `COMP-QMF-REGISTRY`, `COMP-QMF-DATA`, `COMP-QMF-INDICATORS`, `COMP-QMF-STRUCTURE`, `COMP-QMF-RISK` | DEC-0011, DEC-0024 |
| data | `GAP(GAP-0001)`: data-process runtime is unresolved | `registry:local_store_engine` is null under `GAP(GAP-0021)`; migrations remain `GAP(GAP-0022)` | `COMP-QMF-DATA-STORE`, `COMP-QMF-DATA-BACKUP` | DEC-0042, DEC-0045 |
| external | Vendor-owned | cTrader Open API; Dukascopy historical source; Economic-calendar feed; off-machine object storage provider remains `GAP(GAP-0027)` | `COMP-CTRADER`, `COMP-DUKASCOPY`, `COMP-CALENDAR-FEED`, `COMP-OBJECT-STORAGE` | DEC-0045, DEC-0059, DEC-0060 |

QMF V1 has no UI layer. Product UI and Simulator work remain outside the current reusable foundation. (DEC-0009)

## Runtime and version capture points

| Concern | Declared value | Authority |
|---|---|---|
| Python runtime | `GAP(GAP-0001)`: exact CPython minor, operating systems, and architecture matrix | DEC-0011 |
| Package and contract versions | `registry:contract_version_syntax` is null under `GAP(GAP-0005)` | DEC-0030 |
| cTrader target and API facts | `GAP(GAP-0037)`: broker, account type, API version, and price basis | DEC-0059, DEC-0060 |
| Indicator reference | `registry:canonical_indicator_reference` is null under `GAP(GAP-0032)` | DEC-0055 |
| Local persistence engine | `registry:local_store_engine` is null under `GAP(GAP-0021)` | DEC-0042 |
| Off-machine provider | `GAP(GAP-0027)`: provider, encryption, retention, recovery objectives, and verification cadence | DEC-0045 |

## Build and package tooling

| Concern | Tool | Notes | Cites |
|---|---|---|---|
| Repository, distribution, and package layout | `GAP(GAP-0002)` | Distribution identities, package namespaces, build backend, dependency manager, and lockfile policy are unresolved. | DEC-0096 |
| Build and package command | `GAP(GAP-0002)` | No build backend or exact command is selected. | DEC-0096 |
| Test runner | `GAP(GAP-0003)` | Tests and reference usage are mandatory; runner, coverage policy, and command are unresolved. | DEC-0096 |
| Formatter and linter | `GAP(GAP-0003)` | Formatter, linter, and exact commands are unresolved. | DEC-0096 |
| Type checker | `GAP(GAP-0003)` | Type-checking tool and strictness are unresolved. | DEC-0096 |
| Dependency and licence gate | `GAP(GAP-0006)` | QMF may wrap suitable dependencies but must not transplant foreign strategy-family contracts. | DEC-0013 |
| Release and deprecation tooling | `GAP(GAP-0005)` | Release workflow, package versioning, schema versioning, and deprecation window are unresolved. | DEC-0030 |

## Component classification and public roster

The dependency registry records four independent axes:

- `kind` describes architectural form using the closed dependency-registry vocabulary.
- `layer` records placement in middleware, backend, data, or external.
- `roster_role` distinguishes the five public libraries, two public modules, internal seams, and external systems.
- `distribution` records eventual package or deployable identity. It is null for every component under `GAP(GAP-0002)`; no component has a package identity yet.

| Public roster member | `roster_role` | `kind` | Layer | `distribution` | What it carries | Component | Cites |
|---|---|---|---|---|---|---|---|
| qmf-core | public-library | library | backend | null — `GAP(GAP-0002)` | Exact primitive direction, asset-neutral nouns, typed refusals, canonical identity, and compatibility | `COMP-QMF-CORE` | DEC-0022, DEC-0030 |
| qmf-registry | public-library | library | backend | null — `GAP(GAP-0002)` | Identity, graph-shaped lineage, registration gates, and attempt accounting | `COMP-QMF-REGISTRY` | DEC-0033, DEC-0035 |
| qmf-data | public-library | library | backend | null — `GAP(GAP-0002)` | Evidence policy, data contracts, splits, holdout, journal, and backup requirements | `COMP-QMF-DATA` | DEC-0042, DEC-0045 |
| qmf-indicators | public-library | library | backend | null — `GAP(GAP-0002)` | Light indicator protocol and wrappers around a ratified reference | `COMP-QMF-INDICATORS` | DEC-0055 |
| qmf-structure | public-library | library | backend | null — `GAP(GAP-0002)` | QMX-owned causal levels, zones, and market-structure components | `COMP-QMF-STRUCTURE` | DEC-0058 |
| QMF venue module | public-module | middleware | middleware | null — `GAP(GAP-0002)` | Platform-neutral venue capabilities, commands, events, sessions, and cTrader translation | `COMP-QMF-VENUE` | DEC-0059, DEC-0060 |
| QMF risk module | public-module | library | backend | null — `GAP(GAP-0002)` | Fenced Book, BMS, money, exit, correlation, and risk boundary | `COMP-QMF-RISK` | DEC-0065 |

The public roster is exactly the five libraries and two modules in DEC-0024. Venue is a public module whose architectural `kind` is middleware; Risk is a public module whose architectural `kind` is library. `COMP-QMF-DATA-INGEST`, `COMP-QMF-DATA-STORE`, and `COMP-QMF-DATA-BACKUP` have `roster_role: internal-seam`; they are not extra public libraries or modules. External components have `roster_role: external`. None of those classifications selects a distribution or package while `GAP(GAP-0002)` remains open.

## Data stores

| Store | Engine | Schema lives in | Migration policy | Cites |
|---|---|---|---|---|
| QMF evidence persistence | `registry:local_store_engine` is null under `GAP(GAP-0021)` | CT-09, CT-11, and CT-13; physical fields remain `GAP(GAP-0020)` and `GAP(GAP-0023)` | `GAP(GAP-0022)`: versioning, migration, rollback, and verification are unresolved | DEC-0042 |
| Store-to-Backup input boundary | `registry:local_store_engine` is null under `GAP(GAP-0021)` | CT-26; snapshot shape, consistency, completeness, identity, and manifest binding remain `GAP(GAP-0026)` and `GAP(GAP-0027)` | `GAP(GAP-0027)`: restore and recovery procedure remains unresolved | DEC-0045 |
| Off-machine backup target | `GAP(GAP-0027)`: provider is unresolved | CT-14; manifest and restore fields remain `GAP(GAP-0027)` | `GAP(GAP-0027)`: retention, restore, and recovery policy are unresolved | DEC-0045 |

Study candidates do not select an engine. Parquet, DuckDB, SQLite, and JSONL remain unadopted until `GAP(GAP-0021)` is answered. (DEC-0047)

## Pipeline — what runs, and when

The pipeline has the required three declaration tiers, but the tools, commands, branch events, and failure policy remain `GAP(GAP-0003)` and `GAP(GAP-0004)`. No undocumented check is presumed to run.

| Tier | When it runs | Checks | Failure means | Cites |
|---|---|---|---|---|
| Per run | `GAP(GAP-0004)`: exact trigger is unresolved | `GAP(GAP-0003)`: format, lint, type, unit, and reference-usage commands are unresolved | `GAP(GAP-0004)`: handoff policy is unresolved | DEC-0096 |
| Integration line | `GAP(GAP-0004)`: branch and merge trigger are unresolved | `GAP(GAP-0004)`: build, integration, and contract-test commands are unresolved | `GAP(GAP-0004)`: merge policy is unresolved | DEC-0096 |
| Pre-release | `GAP(GAP-0004)`: release trigger is unresolved | `GAP(GAP-0004)`: package, install, migration, restore, security, and smoke gates are unresolved | `GAP(GAP-0004)`: release policy is unresolved | DEC-0096 |

| Check | Command | Tier |
|---|---|---|
| Format | `GAP(GAP-0003)` | per run |
| Lint | `GAP(GAP-0003)` | per run |
| Type check | `GAP(GAP-0003)` | per run |
| Unit tests | `GAP(GAP-0003)` | per run |
| Integration and contract tests | `GAP(GAP-0004)` | integration line |
| Package and install verification | `GAP(GAP-0004)` | pre-release |
| Migration dry run | `GAP(GAP-0022)` | pre-release |
| Backup/restore procedure | `GAP(GAP-0027)` | pre-release |

## Model training

None — QMF V1 trains or fine-tunes no model. MIS model work and the agentic ML harness remain outside current QMF V1 scope. (DEC-0089, DEC-0091)

## Related

Layers, containers, and external systems: `docs/architecture/overview.md`. Component graph: `docs/architecture/dependencies.yaml`. Values: `docs/registry/variables.yaml`. Interface schemas: `docs/contracts/`.
