---
id: ARCH-OVERVIEW
title: QMF V1 Architecture Overview
type: architecture
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP, COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, COMP-OBJECT-STORAGE]
decisions: [DEC-0008, DEC-0009, DEC-0019, DEC-0022, DEC-0024, DEC-0031, DEC-0033, DEC-0035, DEC-0042, DEC-0045, DEC-0055, DEC-0058, DEC-0059, DEC-0061, DEC-0065]
sources: [DEC-0008, DEC-0009, DEC-0019, DEC-0022, DEC-0024, DEC-0031, DEC-0033, DEC-0035, DEC-0042, DEC-0045, DEC-0055, DEC-0058, DEC-0059, DEC-0061, DEC-0065, docs/architecture/dependencies.yaml, docs/contracts/]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 90d
---

# QMF V1 Architecture Overview

QMF V1 is a contracts-first Python toolbox consumed by QMX applications. QMF provides five reusable libraries and two modules; it does not provide an application loop, scheduler, product UI, backtester, or trading-node runtime. (DEC-0008, DEC-0009, DEC-0022, DEC-0024)

## C4 Level 1 — system context

The QMF system sits between QMX application code and external venue, market-data, calendar, and backup systems. Every external data exchange uses a Stage 5 contract; operator interaction belongs to QMX rather than a QMF UI.

```mermaid
flowchart LR
    operator([Operator])
    qmx["QMX application<br/>consumer outside QMF V1"]
    subgraph qmf_system["QMF V1 Blueprint"]
        qmf["QMF toolbox<br/>five libraries and two modules"]
    end
    ctrader["COMP-CTRADER<br/>cTrader Open API"]
    dukascopy["COMP-DUKASCOPY<br/>Dukascopy historical data source"]
    calendar["COMP-CALENDAR-FEED<br/>Economic-calendar feed"]
    object_storage["COMP-OBJECT-STORAGE<br/>Off-machine object storage"]

    operator -->|"operates"| qmx
    qmx -->|"composes provisional QMF libraries; no runtime or live authority"| qmf
    qmf -.->|"CT-19 reserved/unwired; CT-21 no-operation"| ctrader
    ctrader -.->|"CT-18, CT-20 reserved/unwired; CT-21 no-operation"| qmf
    dukascopy -->|"CT-15"| qmf
    calendar -->|"CT-15"| qmf
    qmf -->|"CT-14"| object_storage
```

## C4 Level 2 — containers and support seams

The public roster remains the five libraries and two modules in DEC-0024. `roster_role` in `docs/architecture/dependencies.yaml` records that membership independently from component kind and layer. `COMP-QMF-DATA-INGEST`, `COMP-QMF-DATA-STORE`, and `COMP-QMF-DATA-BACKUP` are internal seams required to keep middleware, backend policy, and physical data responsibilities separate; they do not enlarge the public roster.

```mermaid
flowchart TB
    subgraph qmf_system["QMF V1 Blueprint"]
        core["COMP-QMF-CORE<br/>qmf-core"]
        registry["COMP-QMF-REGISTRY<br/>qmf-registry"]
        data_api["COMP-QMF-DATA<br/>qmf-data"]
        indicators["COMP-QMF-INDICATORS<br/>qmf-indicators"]
        structure["COMP-QMF-STRUCTURE<br/>qmf-structure"]
        venue["COMP-QMF-VENUE<br/>QMF venue module"]
        risk["COMP-QMF-RISK<br/>QMF risk module"]
        ingest["COMP-QMF-DATA-INGEST<br/>qmf-data source-ingest seam"]
        store[("COMP-QMF-DATA-STORE<br/>qmf-data persistence seam")]
        backup["COMP-QMF-DATA-BACKUP<br/>qmf-data backup and restore process"]
    end

    ctrader["COMP-CTRADER<br/>cTrader Open API"]
    dukascopy["COMP-DUKASCOPY<br/>Dukascopy historical data source"]
    calendar["COMP-CALENDAR-FEED<br/>Economic-calendar feed"]
    object_storage["COMP-OBJECT-STORAGE<br/>Off-machine object storage"]

    registry -->|"CT-02, CT-03, CT-04, CT-05"| core
    registry -->|"CT-09"| store
    registry -.->|"CT-13 intended/unwired"| data_api
    data_api -->|"CT-01, CT-02, CT-03, CT-04, CT-05"| core
    data_api -->|"CT-06, CT-07, CT-08"| registry
    data_api -->|"CT-11, CT-13"| store
    indicators -->|"CT-01, CT-02, CT-03, CT-04, CT-05"| core
    indicators -->|"CT-10 governed read"| data_api
    structure -->|"CT-02, CT-03, CT-04, CT-05"| core
    structure -->|"CT-06, CT-07, CT-08"| registry
    structure -->|"CT-10 governed read"| data_api
    venue -->|"CT-01, CT-02, CT-03, CT-04, CT-05"| core
    venue -->|"CT-10 producer; CT-13 intended/unwired"| data_api
    risk -->|"CT-01, CT-02, CT-03, CT-04, CT-05"| core
    risk -->|"CT-06, CT-07"| registry
    risk -->|"CT-10 governed read; CT-13 intended/unwired"| data_api
    ingest -->|"CT-03, CT-04"| core
    ingest -->|"CT-10 producer"| data_api
    dukascopy -->|"CT-15"| ingest
    calendar -->|"CT-15"| ingest
    venue -.->|"CT-19 reserved/unwired; CT-21 no-operation"| ctrader
    ctrader -.->|"CT-18, CT-20 reserved/unwired"| venue
    store -->|"CT-26 store-to-backup input"| backup
    backup -->|"CT-14"| object_storage
```

## Layer view

QMF V1 has active middleware, backend, data, and external layers. QMF V1 has no UI layer. Arrows show the relevant contract interaction; `docs/architecture/dependencies.yaml` remains authoritative for `depends_on`. Every data-bearing arrow carries the governing contract IDs.

```mermaid
flowchart TB
    subgraph external_layer["external"]
        ctrader["COMP-CTRADER<br/>cTrader Open API"]
        dukascopy["COMP-DUKASCOPY<br/>Dukascopy historical data source"]
        calendar["COMP-CALENDAR-FEED<br/>Economic-calendar feed"]
        object_storage["COMP-OBJECT-STORAGE<br/>Off-machine object storage"]
    end

    subgraph middleware_layer["middleware"]
        venue["COMP-QMF-VENUE<br/>QMF venue module"]
        ingest["COMP-QMF-DATA-INGEST<br/>qmf-data source-ingest seam"]
    end

    subgraph backend_layer["backend"]
        core["COMP-QMF-CORE<br/>qmf-core"]
        registry["COMP-QMF-REGISTRY<br/>qmf-registry"]
        data_api["COMP-QMF-DATA<br/>qmf-data"]
        indicators["COMP-QMF-INDICATORS<br/>qmf-indicators"]
        structure["COMP-QMF-STRUCTURE<br/>qmf-structure"]
        risk["COMP-QMF-RISK<br/>QMF risk module"]
    end

    subgraph data_layer["data"]
        store[("COMP-QMF-DATA-STORE<br/>qmf-data persistence seam")]
        backup["COMP-QMF-DATA-BACKUP<br/>qmf-data backup and restore process"]
    end

    registry -->|"CT-02, CT-03, CT-04, CT-05"| core
    registry -->|"CT-09"| store
    registry -.->|"CT-13 intended/unwired"| data_api
    data_api -->|"CT-01, CT-02, CT-03, CT-04, CT-05"| core
    data_api -->|"CT-06, CT-07, CT-08"| registry
    data_api -->|"CT-11, CT-13"| store
    indicators -->|"CT-01, CT-02, CT-03, CT-04, CT-05"| core
    indicators -->|"CT-10 governed read"| data_api
    structure -->|"CT-02, CT-03, CT-04, CT-05"| core
    structure -->|"CT-06, CT-07, CT-08"| registry
    structure -->|"CT-10 governed read"| data_api
    venue -->|"CT-01, CT-02, CT-03, CT-04, CT-05"| core
    venue -->|"CT-10 producer; CT-13 intended/unwired"| data_api
    venue -.->|"CT-18 to CT-20 reserved/unwired; CT-21 no-operation"| ctrader
    risk -->|"CT-01, CT-02, CT-03, CT-04, CT-05"| core
    risk -->|"CT-06, CT-07"| registry
    risk -->|"CT-10 governed read; CT-13 intended/unwired"| data_api
    ingest -->|"CT-03, CT-04"| core
    ingest -->|"CT-10 producer"| data_api
    dukascopy -->|"CT-15"| ingest
    calendar -->|"CT-15"| ingest
    store -->|"CT-26 store-to-backup input"| backup
    backup -->|"CT-14"| object_storage
```

## Runtime and data shape

QMF libraries expose provisional definitions and backend policy through CT-01 through CT-17. CT-18 through CT-20 are reserved and unwired Venue shapes, CT-21 is a no-operation credential/session gate, CT-22 through CT-25 are reserved and unwired Risk boundaries, and CT-26 is the provisional internal Store-to-Backup input boundary. QMF has no autonomous startup or orchestration path; a later QMX application composes the libraries. (DEC-0008, DEC-0009, DEC-0022)

External observations enter through `COMP-QMF-DATA-INGEST` or `COMP-QMF-VENUE`, which produce CT-10 into `COMP-QMF-DATA`. Governed readers depend on `COMP-QMF-DATA` rather than bypassing it. CT-15 is only the external-source adapter boundary into `COMP-QMF-DATA-INGEST`; it is not a `COMP-QMF-DATA` interface. Governed observations reach `COMP-QMF-DATA-STORE` only through CT-11 or CT-13. Acquisition scheduling and lifecycle ownership remain `GAP(GAP-0028)`.

`COMP-QMF-DATA-STORE` supplies an input boundary to `COMP-QMF-DATA-BACKUP` through CT-26; CT-14 covers the Backup-to-Object-Storage boundary. Snapshot shape, consistency, completeness, manifest binding, restore procedure, and verification remain `GAP(GAP-0026)` and `GAP(GAP-0027)`. The boundary does not assert recovery completion.

`COMP-QMF-REGISTRY` supplies identities, graph-shaped lineage, and registration gates without requiring a graph database. Registry kinds and persistence details remain `GAP(GAP-0014)`, `GAP(GAP-0015)`, `GAP(GAP-0021)`, and `GAP(GAP-0022)`. (DEC-0033, DEC-0035)

`COMP-QMF-DATA` owns split, holdout, evidence, and journal policy; the data layer owns physical persistence and backup mechanics. Exact layer schemas and store engines remain `GAP(GAP-0020)` through `GAP(GAP-0027)`. (DEC-0042, DEC-0045)

`COMP-QMF-RISK` is present in the public roster but remains a fenced specification boundary. Book, BMS, exit, paper-mode, SQS, and execution-priority semantics remain `GAP(GAP-0039)` through `GAP(GAP-0046)`. (DEC-0065)

## Component index

| Component | Layer | Role | Specification |
|---|---|---|---|
| `COMP-QMF-CORE` — qmf-core | backend | Framework-neutral definitions | `docs/components/qmf-core.md` |
| `COMP-QMF-REGISTRY` — qmf-registry | backend | Identity, lineage, and registration gates | `docs/components/qmf-registry.md` |
| `COMP-QMF-DATA` — qmf-data | backend | Data policy and public API | `docs/components/qmf-data.md` |
| `COMP-QMF-INDICATORS` — qmf-indicators | backend | Light indicator protocol and wrappers | `docs/components/qmf-indicators.md` |
| `COMP-QMF-STRUCTURE` — qmf-structure | backend | Causal QMX-owned market structure | `docs/components/qmf-structure.md` |
| `COMP-QMF-VENUE` — QMF venue module | middleware | Venue translation and session seam | `docs/components/qmf-venue.md` |
| `COMP-QMF-RISK` — QMF risk module | backend | Fenced Book, BMS, and risk boundary | `docs/components/qmf-risk.md` |
| `COMP-QMF-DATA-INGEST` — qmf-data source-ingest seam | middleware | External-source translation | `docs/components/qmf-data-ingest.md` |
| `COMP-QMF-DATA-STORE` — qmf-data persistence seam | data | Physical evidence persistence | `docs/components/qmf-data-store.md` |
| `COMP-QMF-DATA-BACKUP` — qmf-data backup and restore process | data | Backup/restore boundary | `docs/components/qmf-data-backup.md` |
| `COMP-CTRADER` — cTrader Open API | external | First intended external venue peer; no active dependency or live connection is authorized | `docs/components/ctrader.md` |
| `COMP-DUKASCOPY` — Dukascopy historical data source | external | Historical tick source | `docs/components/dukascopy.md` |
| `COMP-CALENDAR-FEED` — Economic-calendar feed | external | Forward calendar observations | `docs/components/calendar-feed.md` |
| `COMP-OBJECT-STORAGE` — Off-machine object storage | external | Backup destination | `docs/components/object-storage.md` |

## Contract authority

`docs/architecture/dependencies.yaml` is the component and dependency registry. `docs/contracts/ct-01-*.yaml` through `docs/contracts/ct-26-*.yaml` are provisional schema boundaries; every unresolved field, enum, unit, and nullability choice remains null and cites an existing GAP.
