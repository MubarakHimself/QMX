---
id: ARCH-OVERVIEW
title: QMF V1 Architecture Overview
type: architecture
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP, COMP-QMF-CALENDAR-FOREX, COMP-QMB, COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, COMP-OBJECT-STORAGE]
decisions: [DEC-0008, DEC-0009, DEC-0019, DEC-0022, DEC-0024, DEC-0031, DEC-0033, DEC-0035, DEC-0042, DEC-0045, DEC-0055, DEC-0058, DEC-0059, DEC-0061, DEC-0065, DEC-0099, DEC-0100, DEC-0104, DEC-0106, DEC-0110, DEC-0113, DEC-0114, DEC-0116, DEC-0117, DEC-0118, DEC-0119, DEC-0120, DEC-0121, DEC-0122, DEC-0126, DEC-0127, DEC-0128, DEC-0131, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0139, DEC-0141, DEC-0143, DEC-0144, DEC-0145, DEC-0147, DEC-0149, DEC-0150, DEC-0151, DEC-0158, DEC-0159, DEC-0161, DEC-0163, DEC-0164, DEC-0165, DEC-0169]
sources: [DEC-0008, DEC-0009, DEC-0019, DEC-0022, DEC-0024, DEC-0031, DEC-0033, DEC-0035, DEC-0042, DEC-0045, DEC-0055, DEC-0058, DEC-0059, DEC-0061, DEC-0065, DEC-0099, DEC-0100, DEC-0104, DEC-0106, DEC-0110, DEC-0113, DEC-0114, DEC-0116, DEC-0117, DEC-0118, DEC-0119, DEC-0120, DEC-0121, DEC-0122, DEC-0126, DEC-0127, DEC-0128, DEC-0131, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0139, DEC-0141, DEC-0143, DEC-0144, DEC-0145, DEC-0147, DEC-0149, DEC-0150, DEC-0151, DEC-0158, DEC-0159, DEC-0161, DEC-0163, DEC-0164, DEC-0165, DEC-0169, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ctrader-venue-facts.md, docs/architecture/dependencies.yaml, docs/contracts/]
generated: 2026-08-18
verified: 2026-08-21
stale_after: 90d
---

# QMF V1 Architecture Overview

QMF V1 is a contracts-first Python toolbox consumed by QMX applications. QMF provides five reusable libraries and two modules; it does not provide an application loop, scheduler, product UI, backtesting library, or trading-node runtime. Everything downstream of QMF — the trading node, backtesting, the agentic system, and the product UI — is built with QMF libraries rather than re-implementing or bypassing its contracts. The backtesting library named there is now specified: it is QMB, the QMX experimentation/backtesting product (one pure library plus the `qmb` CLI) that composes the QMF backend libraries as an application-layer consumer outside QMF V1 — detailed under [Application-layer consumer — QMB](#application-layer-consumer--qmb) below and in `docs/decisions/ADR-0017`. (DEC-0008, DEC-0009, DEC-0022, DEC-0024, DEC-0122, DEC-0159)

## Design paradigm

QMF is a **contract-hub library workspace, hexagonal at workspace scale.** `qmf-core` is the dependency-free hub carrying only definitions — exact value types, domain nouns, typed refusals, fingerprints, and protocol seams. Every other package depends inward on `qmf-core`; runtime concerns (clocks, market-hours calendars, venues) enter through protocols the core defines and outer packages or calendar extensions implement. Nothing in QMF is an application; applications are built *with* it, outside this repository's scope. (DEC-0022, DEC-0100, DEC-0104, DEC-0120)

## Package shape — one repo, seven packages

QMF V1 is a single repository organized as a uv workspace with seven installable packages — `qmf-core`, `qmf-registry`, `qmf-data`, `qmf-indicators`, `qmf-structure`, `qmf-venue`, `qmf-risk` — importing under the `qmf.*` PEP 420 implicit namespace. No distribution ever contains `qmf/__init__.py`; every package uses `src/` layout (`src/qmf/<name>/`); every dependency, including sibling packages, is declared explicitly; the build backend is `uv_build`; one `uv.lock` is committed; and the seven roster packages release in lockstep SemVer. Shared nouns (Venue, Account, Instrument, WriterId) are defined in `qmf-core` and their records owned by `qmf-registry`. Calendar extensions (for example `qmf-calendar-forex`) are separate versioned packages outside the roster, in the same workspace, on their own SemVer ladder. (DEC-0100)

## Dependency direction (ratified)

The dependency graph is a governed artifact under a **default-deny** rule: `qmf-core` depends on nothing; every package may depend on `qmf-core`; and until an inter-library edge is ratified as a spine amendment, no package may depend on any package other than `qmf-core`. One inter-library edge is ratified — `qmf-registry → qmf-data` (2026-08-20) — through which the registry persists records and lineage via qmf-data's CT-11 append-store contract, with stdlib-typed signatures at that boundary. Nothing imports `qmf-venue` or `qmf-risk`: they are edge modules. Calendar extensions implement core protocols from outside the roster. (DEC-0120)

```mermaid
graph TD
  REG[qmf-registry] --> CORE[qmf-core<br/>zero-dep hub]
  REG -- ratified edge 2026-08-20<br/>stores via CT-11 --> DATA[qmf-data]
  DATA --> CORE
  IND[qmf-indicators] --> CORE
  STR[qmf-structure] --> CORE
  VEN[qmf-venue<br/>module] --> CORE
  RISK[qmf-risk<br/>module] --> CORE
  CAL[calendar extensions<br/>outside roster] -. implement core protocols .-> CORE
  subgraph edge [edge modules — nothing imports them]
    VEN
    RISK
  end
```

This ratified direction governs package import dependencies. Adding any further edge is a spine amendment. The venue write path adds **no** edge: `qmf-venue` emits through `qmf-core`-defined sink protocols (`ObservationSink`, `JournalSink`, `RecordSink`, `SecretStore`) injected at the composition root, with the adapter's connection manager holding the `WriterId` and seeing every sink refusal. (DEC-0120, DEC-0138, DEC-0141)

## Clock injection seam

No component below the composition root reads the system clock. Clock access is a core-defined protocol; the application's composition root injects the real system clock for `world = live`, or a data-driven replay clock (a pure function of the data cursor) for `world = replay`. Every QMF component below the root receives the injected clock and never touches the system clock directly. (DEC-0106)

```mermaid
graph LR
  subgraph app [composition root — application side]
    RC[real system clock]
    RP[replay clock<br/>pure function of data cursor]
  end
  RC -- injected --> PORT[Clock protocol<br/>defined in qmf-core]
  RP -- injected --> PORT
  PORT --> USERS[every QMF component<br/>below the root]
  USERS x--x SYS[(system clock<br/>direct access forbidden)]
```

## C4 Level 1 — system context

The QMF system sits between QMX application code and external venue, market-data, news-calendar, and backup systems. Every external data exchange crosses a declared `CT-*` contract; operator interaction belongs to QMX rather than a QMF UI. QMB is the first named application-layer consumer: it composes the QMF backend libraries in `world = replay`, produces CT-32 results and CT-13 journal streams, and takes no venue edge — live wiring is trading-node territory. (DEC-0159, DEC-0163)

```mermaid
flowchart LR
    operator([Operator])
    qmx["QMX application<br/>consumer outside QMF V1"]
    qmb["COMP-QMB<br/>experimentation library + qmb CLI<br/>application-layer consumer outside QMF V1"]
    subgraph qmf_system["QMF V1 Blueprint"]
        qmf["QMF toolbox<br/>five libraries and two modules"]
    end
    ctrader["COMP-CTRADER<br/>cTrader Open API"]
    dukascopy["COMP-DUKASCOPY<br/>Dukascopy historical data source"]
    calendar["COMP-CALENDAR-FEED<br/>news-calendar feed"]
    object_storage["COMP-OBJECT-STORAGE<br/>Off-machine object storage"]

    operator -->|"operates"| qmx
    operator -->|"runs experiments via the qmb CLI"| qmb
    qmx -->|"composes provisional QMF libraries; no runtime or live authority"| qmf
    qmb -->|"composes QMF backend libraries; world=replay, no live authority"| qmf
    qmf -.->|"CT-19 command, CT-21 session (ratified design; no adapter)"| ctrader
    ctrader -.->|"CT-18 capability, CT-20 event; market data via CT-15"| qmf
    dukascopy -->|"CT-15"| qmf
    calendar -->|"CT-15"| qmf
    qmf -->|"CT-14"| object_storage
```

## C4 Level 2 — containers and support seams

The public roster is the five libraries and two modules in DEC-0024. `roster_role` in `docs/architecture/dependencies.yaml` records that membership independently from component kind and layer. `COMP-QMF-DATA-INGEST`, `COMP-QMF-DATA-STORE`, and `COMP-QMF-DATA-BACKUP` are internal seams of `qmf-data` that separate middleware, backend policy, and physical data responsibilities; they do not enlarge the public roster.

Package import dependencies follow the ratified default-deny direction above (DEC-0120): `qmf-core` depends on nothing, every package may depend on `qmf-core`, and `qmf-registry → qmf-data` is the only ratified inter-library edge. The CT-labeled arrows below depict contract interactions and governed data flows — which the application mediates through core-defined protocols and dependency injection — not additional package import edges.

```mermaid
flowchart TB
    subgraph qmf_system["QMF V1 Blueprint"]
        core["COMP-QMF-CORE<br/>qmf-core"]
        registry["COMP-QMF-REGISTRY<br/>qmf-registry"]
        data_api["COMP-QMF-DATA<br/>qmf-data"]
        indicators["COMP-QMF-INDICATORS<br/>qmf-indicators"]
        structure["COMP-QMF-STRUCTURE<br/>qmf-structure"]
        venue["COMP-QMF-VENUE<br/>qmf-venue module"]
        risk["COMP-QMF-RISK<br/>qmf-risk module"]
        ingest["COMP-QMF-DATA-INGEST<br/>qmf-data source-ingest seam"]
        store[("COMP-QMF-DATA-STORE<br/>qmf-data persistence seam")]
        backup["COMP-QMF-DATA-BACKUP<br/>qmf-data backup and restore process"]
    end

    ctrader["COMP-CTRADER<br/>cTrader Open API"]
    dukascopy["COMP-DUKASCOPY<br/>Dukascopy historical data source"]
    calendar["COMP-CALENDAR-FEED<br/>news-calendar feed"]
    object_storage["COMP-OBJECT-STORAGE<br/>Off-machine object storage"]

    registry -->|"CT-02, CT-03, CT-04, CT-05"| core
    registry -->|"CT-11 ratified edge 2026-08-20"| data_api
    data_api -->|"CT-01, CT-02, CT-03, CT-04, CT-05"| core
    indicators -->|"CT-01, CT-02, CT-03, CT-04, CT-05"| core
    indicators -->|"CT-10 governed read"| data_api
    structure -->|"CT-02, CT-03, CT-04, CT-05"| core
    structure -->|"CT-10 governed read"| data_api
    venue -->|"CT-01, CT-02, CT-03, CT-04, CT-05"| core
    venue -->|"CT-10 producer; CT-13 intended/unwired"| data_api
    risk -->|"CT-01, CT-02, CT-03, CT-04, CT-05"| core
    risk -->|"CT-10 governed read; CT-13 intended/unwired"| data_api
    data_api -->|"CT-11, CT-13"| store
    ingest -->|"CT-03, CT-04"| core
    ingest -->|"CT-10 producer"| data_api
    dukascopy -->|"CT-15"| ingest
    calendar -->|"CT-15"| ingest
    venue -.->|"CT-19 command, CT-21 session (ratified design; no adapter)"| ctrader
    ctrader -.->|"CT-18 capability, CT-20 event (ratified design)"| venue
    store -->|"CT-26 store-to-backup input"| backup
    backup -->|"CT-14"| object_storage
```

## Layer view

QMF V1 has active middleware, backend, data, and external layers. QMF V1 has no UI layer. Arrows show the relevant contract interaction; `docs/architecture/dependencies.yaml` remains authoritative for `depends_on`, and package import dependencies follow the ratified default-deny direction (DEC-0120).

```mermaid
flowchart TB
    subgraph external_layer["external"]
        ctrader["COMP-CTRADER<br/>cTrader Open API"]
        dukascopy["COMP-DUKASCOPY<br/>Dukascopy historical data source"]
        calendar["COMP-CALENDAR-FEED<br/>news-calendar feed"]
        object_storage["COMP-OBJECT-STORAGE<br/>Off-machine object storage"]
    end

    subgraph middleware_layer["middleware"]
        venue["COMP-QMF-VENUE<br/>qmf-venue module"]
        ingest["COMP-QMF-DATA-INGEST<br/>qmf-data source-ingest seam"]
    end

    subgraph backend_layer["backend"]
        core["COMP-QMF-CORE<br/>qmf-core"]
        registry["COMP-QMF-REGISTRY<br/>qmf-registry"]
        data_api["COMP-QMF-DATA<br/>qmf-data"]
        indicators["COMP-QMF-INDICATORS<br/>qmf-indicators"]
        structure["COMP-QMF-STRUCTURE<br/>qmf-structure"]
        risk["COMP-QMF-RISK<br/>qmf-risk module"]
        calendarforex["COMP-QMF-CALENDAR-FOREX<br/>qmf-calendar-forex extension<br/>outside roster, own SemVer ladder"]
    end

    subgraph data_layer["data"]
        store[("COMP-QMF-DATA-STORE<br/>qmf-data persistence seam")]
        backup["COMP-QMF-DATA-BACKUP<br/>qmf-data backup and restore process"]
    end

    registry -->|"CT-02, CT-03, CT-04, CT-05"| core
    registry -->|"CT-11 ratified edge 2026-08-20"| data_api
    data_api -->|"CT-01, CT-02, CT-03, CT-04, CT-05"| core
    indicators -->|"CT-01, CT-02, CT-03, CT-04, CT-05"| core
    indicators -->|"CT-10 governed read"| data_api
    structure -->|"CT-02, CT-03, CT-04, CT-05"| core
    structure -->|"CT-10 governed read"| data_api
    venue -->|"CT-01, CT-02, CT-03, CT-04, CT-05"| core
    venue -->|"CT-10 producer; CT-13 intended/unwired"| data_api
    venue -.->|"CT-18 to CT-21 ratified design; no adapter implemented"| ctrader
    calendarforex -.->|"CT-02 calendar-provider protocol"| core
    risk -->|"CT-01, CT-02, CT-03, CT-04, CT-05"| core
    risk -->|"CT-10 governed read; CT-13 intended/unwired"| data_api
    data_api -->|"CT-11, CT-13"| store
    ingest -->|"CT-03, CT-04"| core
    ingest -->|"CT-10 producer"| data_api
    dukascopy -->|"CT-15"| ingest
    calendar -->|"CT-15"| ingest
    store -->|"CT-26 store-to-backup input"| backup
    backup -->|"CT-14"| object_storage
```

## Worlds and namespace isolation

Every computed result entering evidence carries a **world**, one of the identity parts of a result label (which also carries producer contract identity and evidence class per DEC-0131). Three worlds exist: `live` (real venue clocks and quotes — the account role, not the world, carries money-reality, so paper and demo runs are `world = live` and stay comparable to live for alpha-decay sensing); `replay` (a data-driven injected clock over recorded history, implementable today); and `simulated` (synthetic data, reserved but unusable in V1 — writing `world = simulated` into governed evidence is a `policy rejection` typed refusal until the backtesting sitting defines simulated-time typing). A non-live world may never write into the live evidence namespace, and factory sandboxes never produce timestamps that enter an evidence store. Identity distinctness alone does not deliver world separation — storage separation does. (DEC-0110, DEC-0131)

## Data rooms per world

`qmf-data` defines seven room-roles — ingest door, immutable raw archive, processed, journal, split-governed research door, backup, and the registry room (holding `qmf-registry`'s records and lineage under the same retention, backup, and migration law). The room-roles are **instantiated per world**, and a read that crosses worlds is a `policy rejection` refusal. Stores are Parquet (columnar time-series), DuckDB (local analytics), SQLite (transactional metadata), and JSONL (append streams), each behind a QMF-owned contract with stdlib-typed boundary signatures and no database server. Only raw-archive and journal formats are evidence-bearing; analytics engines hold rebuildable views. (DEC-0117)

## Concurrency stance

QMF values are immutable and safe to share by construction; purity binds the pure-computation libraries (core, indicators, structure). Components that own an external resource — stores, recorders, adapters — are the stateful class and follow **one-writer-per-stream with unlimited readers**, where the writer is the holder of an AD-8 WriterId. QMF never spawns threads or background work: the application owns all concurrency. Async APIs exist only at the venue network edge, never in `qmf-core` or the libraries. (DEC-0113)

## Runtime and data shape

QMF has no autonomous startup or orchestration path; a later QMX application composes the libraries and injects the clock at the composition root. CT-18 through CT-21 carry the **ratified venue design** (AD-26 through AD-28) — one neutral port and four contracts that per-venue adapters implement and the composition root wires, with no adapter yet implemented; CT-22 through CT-25 and CT-27 through CT-32 are the **ratified Risk boundaries** (AD-29 through AD-41), filled and minted at format version 1 as `defined-unwired` surface that the composition root wires with no new package edge; and CT-26 is the internal Store-to-Backup input boundary. (DEC-0008, DEC-0009, DEC-0022, DEC-0136, DEC-0137, DEC-0138, DEC-0143, DEC-0158)

External observations enter through `COMP-QMF-DATA-INGEST` or `COMP-QMF-VENUE`, which produce CT-10 into `COMP-QMF-DATA`. Governed readers reach data through `COMP-QMF-DATA` rather than bypassing it. CT-15 is only the external-source adapter boundary into `COMP-QMF-DATA-INGEST`; it is not a `COMP-QMF-DATA` interface. Every external fact carries event-time, known-at, source, and revision, where source is a core provenance noun orthogonal to VenueId, and corrections are appended, never overwritten. `qmf-data` defines source contracts, normalization, validation, and idempotent intake keyed on (source, source-native id, revision); applications own scheduling, retries, supervision, and UI. (DEC-0117, DEC-0119)

`COMP-QMF-VENUE`'s design is ratified (AD-26 through AD-28). One neutral port carries four contracts on `qmf-core` nouns: capability (CT-18), command (CT-19), event and reconciliation (CT-20), and secret/session (CT-21, shaped by the AD-26 secret lifecycle). The command stream — the unit of `UNKNOWN` blocking, `WriterId` ownership, and the gapless per-writer sequence — is the (VenueId, account) pair; the five command kinds are `place_order`, `cancel_order`, `close_position`, `close_all`, and `amend_protection` — the fifth minted by the risk sitting (DEC-0148) — and every well-formed submission resolves to one of four outcomes with `UNKNOWN` a recorded state, never an error. The adapter's connection manager owns venue sessions and emits through the `qmf-core`-defined sink protocols injected at the composition root, so the venue write path adds no dependency edge and the writer sees every sink refusal. Market data has a named home: ticks, bars, depth, gap-replay backfill, and historical paging enter as CT-10 source observations through `qmf-data`'s CT-15 intake — application-mediated, no fifth contract, no new edge. cTrader is the first adapter target; its ratified venue facts and the platform-versus-broker split live in `docs/components/ctrader.md`. (DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0139, DEC-0141)

`COMP-QMF-REGISTRY` uses per-kind record schemas — each its own versioned contract — sharing a tiny common header of kind, contract format version, at-birth parent references, writer, and sequence; a record's stable id is derived from its `fp1` fingerprint, never minted, so identical work from two sandboxes deduplicates. Lineage accruing after birth lives exclusively in append-only typed edge records (supersedes, promoted-from, occurrence-of, corroborates, disagrees-with) stored as pinned JSONL; indexes are local and rebuildable; no database server exists. The registry reserves a promotion-occurrence card kind whose mandatory plain-words summary is an identity field, and V1 signing is the operator's recorded approval attesting the record's `fp1`. (DEC-0114, DEC-0116)

`COMP-QMF-DATA` owns split, holdout seal, evidence, and journal policy; the data layer owns physical persistence and backup mechanics. Dataset splits are fingerprinted, time-ordered, non-overlapping manifests, each pinning exactly one calendar identity and version in-band; the 12-month seal is a no-peek lock enforced now as a `policy rejection` refusal at every `qmf-data` read boundary, independent of the deferred causality gates. The journal is N append-only streams — one per producing component under its WriterId — recording seven event types (decision, order, fill, risk transition, promotion, data quality, control action). Migrations run preflight checks, backup first, dry-run, migrate, verify; the ratified backup design is nightly, encrypted, versioned, off-machine, with QMF providing the backup/restore/verify primitives (CT-14, CT-26) and applications owning the schedule; numeric recovery objectives await the node/ops sitting. (DEC-0117, DEC-0118, DEC-0119)

The look-ahead causality registration gate (`GAP-0016`) and the attempt counter (`GAP-0017`) stay operator-deferred, with the consequence knowingly accepted that artifacts registered before then carry no causality evidence; the bitemporal ingredients (event-time versus knowledge-time) remain ratified. Look-ahead *prevention* is now delivered structurally inside a QMB run (forming-bar rules, split-manifest enforcement, declared stream sets); only the CT-08 registration gate and the counting policy remain deferred. (DEC-0121, DEC-0169)

`COMP-QMF-RISK` is present in the public roster and its design is **ratified** (AD-29 through AD-41). It owns the Book/BMS binding chain — the BMS is the account-facing supervising layer, one BMS instance per account serving many Books, a Book binds exactly one BMS, and a Bot binds exactly one Book (DEC-0143) — plus template-and-versioning discipline (DEC-0144), journals-as-projections (DEC-0145), three-layer admission (DEC-0146), Book-owned exit policy with Bot proposals through the CT-23 door (DEC-0147, resolving DEC-0067), paper as a Book-level standing evidence state (DEC-0149), control actions with the kill switch versus kill line split (DEC-0150), same-tick priority per command stream (DEC-0151), protection windows (DEC-0152), SQS V1 (DEC-0153), the R/dimensional law (DEC-0154), and the exit-record and bench evidence base (DEC-0155). The risk sitting adds **no** package import edge: `qmf-risk` depends only on `qmf-core`, its record kinds are `qmf-core` value types wrapped into registry records by the composition root, and control-action dispatch reaches the venue through the same `qmf-core`-defined sink protocols the venue write path uses (DEC-0158). CT-22 through CT-25 are filled and CT-27 through CT-32 are minted at format version 1 as `defined-unwired` surface; every recovered number is a configurable UI-editable variable with no ratified spine value (DEC-0157), and implementation authorization arrives only through the factory pipeline. Trading-node runtime matter stays out of these docs, referenced through `tracker/trading-node-notes.md` as a pointer only (DEC-0142). (DEC-0143, DEC-0147, DEC-0150, DEC-0158)

## Application-layer consumer — QMB

QMB is the QMX experimentation/backtesting product and the first named application-layer consumer built on the QMF foundation: one pure library plus the `qmb` CLI shipped in one wheel, an application-layer product built ON QMF, never a QMF roster package (DEC-0159). It composes the six backend QMF libraries — `qmf-core`, `qmf-registry`, `qmf-data`, `qmf-indicators`, `qmf-structure`, and `qmf-risk` — as a composition root, and is the first sanctioned place the defined-unwired risk contracts are legally wired, in `world = replay` only (DEC-0169). It realizes the reserved "future backtesting library" slot; the Simulator stays a separate deferred UI product that will consume QMB, not QMF directly (DEC-0159).

QMB takes **no** edge to `COMP-QMF-VENUE`: live venue wiring is trading-node territory, and replay execution binds QMB's own fill, cost, and financing ports instead (DEC-0164). The library's `run()` is pure and returns a CT-32 performance-result; one impure orchestrator owns all writes — per-run operational logs during the run and exactly one WriterId-scoped ledger line at completion (DEC-0161). Run outputs adopt existing contracts: the result artifact is a CT-32 with declared chart-series and trade-event-reference extensions, and run trading events ride CT-13 journal events on writer-scoped streams in the run's world (DEC-0163). Registry state reaches QMB as immutable fingerprinted **as-of sets** over a passive file-sync hub — dumb storage, never a central service (DEC-0165).

```mermaid
flowchart TB
    operator([Operator / agent])
    subgraph consumers["Application-layer consumers — outside QMF V1"]
        qmb["COMP-QMB<br/>experimentation library + qmb CLI"]
        simulator["Simulator<br/>deferred UI product"]
    end
    subgraph qmf_backend["QMF V1 backend libraries — composed as a root"]
        core["COMP-QMF-CORE"]
        registry["COMP-QMF-REGISTRY"]
        data_api["COMP-QMF-DATA"]
        indicators["COMP-QMF-INDICATORS"]
        structure["COMP-QMF-STRUCTURE"]
        risk["COMP-QMF-RISK"]
    end
    hub[("passive file-sync hub<br/>immutable as-of sets — dumb storage")]
    results["CT-32 result artifact<br/>+ CT-13 replay-world journal streams"]
    venue["COMP-QMF-VENUE venue module<br/>no QMB edge — live wiring is trading-node territory"]

    operator -->|"runs experiments via qmb CLI / Python API"| qmb
    qmb -->|"composes six backend libraries; world=replay only"| qmf_backend
    qmb -->|"pure run() emits"| results
    registry -.->|"records published as as-of sets"| hub
    hub -.->|"library-owned registry-read port"| qmb
    simulator -.->|"deferred; will consume QMB"| qmb
    qmb x--x venue
```

## Component index

| Component | Layer | Role | Specification |
|---|---|---|---|
| `COMP-QMF-CORE` — qmf-core | backend | Framework-neutral definitions and the single `fp1` implementation | `docs/components/qmf-core.md` |
| `COMP-QMF-REGISTRY` — qmf-registry | backend | Per-kind records, fingerprint-derived ids, and typed lineage edges | `docs/components/qmf-registry.md` |
| `COMP-QMF-DATA` — qmf-data | backend | Seven room-roles, data policy, and public API | `docs/components/qmf-data.md` |
| `COMP-QMF-INDICATORS` — qmf-indicators | backend | Package-neutral two-mode indicator protocol and TA-Lib wrappers | `docs/components/qmf-indicators.md` |
| `COMP-QMF-STRUCTURE` — qmf-structure | backend | Causal QMX-owned market structure | `docs/components/qmf-structure.md` |
| `COMP-QMF-VENUE` — qmf-venue module | middleware | Venue translation and session seam (edge module) | `docs/components/qmf-venue.md` |
| `COMP-QMF-RISK` — qmf-risk module | backend | Ratified Book, BMS, exit, paper-mode, control, and risk-arithmetic boundary (edge module) | `docs/components/qmf-risk.md` |
| `COMP-QMF-DATA-INGEST` — qmf-data source-ingest seam | middleware | External-source translation | `docs/components/qmf-data-ingest.md` |
| `COMP-QMF-DATA-STORE` — qmf-data persistence seam | data | Physical evidence persistence | `docs/components/qmf-data-store.md` |
| `COMP-QMF-DATA-BACKUP` — qmf-data backup and restore process | data | Backup/restore boundary | `docs/components/qmf-data-backup.md` |
| `COMP-QMF-CALENDAR-FOREX` — qmf-calendar-forex | backend | First market-hours calendar extension — outside the roster, own SemVer ladder | `docs/components/qmf-calendar-forex.md` |
| `COMP-QMB` — experimentation library + qmb CLI | middleware | Application-layer experimentation/backtesting consumer built ON QMF; composes the six backend libraries in `world = replay`, produces CT-32 results and CT-13 journal streams, no venue edge — outside the roster and outside QMF V1 | `docs/components/qmb.md` |
| `COMP-CTRADER` — cTrader Open API | external | First intended external venue peer; no active dependency or live connection is authorized | `docs/components/ctrader.md` |
| `COMP-DUKASCOPY` — Dukascopy historical data source | external | Historical tick source | `docs/components/dukascopy.md` |
| `COMP-CALENDAR-FEED` — news-calendar feed | external | Forward news-calendar observations | `docs/components/calendar-feed.md` |
| `COMP-OBJECT-STORAGE` — Off-machine object storage | external | Backup destination | `docs/components/object-storage.md` |

## Contract authority

`docs/architecture/dependencies.yaml` is the component and dependency registry. `docs/contracts/ct-01-*.yaml` through `docs/contracts/ct-32-*.yaml` are provisional schema boundaries; the venue (CT-18 through CT-21), indicator/structure (CT-16, CT-17), and risk (CT-22 through CT-25, CT-27 through CT-32) contracts are filled at format version 1 as ratified `defined-unwired` surface, while any still-unresolved field, enum, unit, or nullability choice remains null and cites an existing GAP or a declared pending slot. The ratified spine at `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md` is the authoritative source for the paradigm, dependency direction, and invariants absorbed here.
