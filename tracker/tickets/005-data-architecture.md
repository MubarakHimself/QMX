---
id: 005
title: Data architecture
label: wayfinder:grilling
status: open
assignee:
blocked-by: [001]
---

## Question

Choose QMX's data stack from the research findings (`workroom/research/02-data-foundation.md`): storage engines and layout for multi-pair forex tick/bar history plus continuously collected live data, the relational store, cross-pair analysis access, and the Dukascopy ingestion path ("engulf" candidate). Sized for one operator, deployable on workstation + Linux VPS.

## Progress (2026-08-18)

Deep-dive blueprint delivered to `workroom/reference/09-data-layer-blueprint.md` (workflow over workroom/research/02+10, node primer, operator dictation): six layers L0–L5 (ingest / raw evidence / processed / journal / research door with splits-by-default / backup), stores-per-purpose matrix (Parquet+DuckDB+SQLite-inbox; PostgreSQL rejected), **ArcticDB verdict: NO for v1 — technical, not licence** (transaction-time only, no valid-time axis); **lineage: graph model in append-only JSONL files, graph database deferred until proven needed**; full journal stream table (12 streams, cadence + retention); paper-twin permanently on for alpha-decay continuity; auto-detection = operator-owned rules.yaml over a fixed metric catalog, flags notify but NEVER act. Eight yes/no questions queued for the operator (holdout months, backup cadence, Dukascopy risk posture, etc.). Nothing adopted yet — this ticket's session ratifies.

**Operator rulings landed early (2026-08-18 evening):** keep ALL history as far back as each source goes (12-month seal ≠ 12-month dataset — the seal only excludes the newest year from research until a strategy's one logged final look; RATIFIED); split/chunking discipline is QMF's job by default (he wants help there — splits registry covers it); MIS snapshots and everything else kept RAW in full (storage is his to buy; "better to have every copy"); backup to a cloud bucket, nightly; news blackout is systematic ±15 minutes around scheduled news and is NOT the SQS (separate gates, never conflate); the record-through-blackout paper-simulation idea was dropped — ordinary market recording continues anyway because recorders never stop.
