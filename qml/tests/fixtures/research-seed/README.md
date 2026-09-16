# STRATS

STRATS is a portable **files + SQLite** strategy-graph backend. Markdown (and a few YAML) files are the source of truth. SQLite is a derived index you can throw away and rebuild.

**Obsidian** is the current UI — plain folders and notes, readable without any app. This library will plug into **QMX** later. QMX implements; it does not own STRATS.

This is **one library**. It is **not Hermes**. Hermes may have helped construct files; nothing here depends on `.hermes`, agents, or orchestration scratch.

## Pause before populate

**Do not start ingestion.** Do not download videos, run yt-dlp, stand up n8n, or extract strategies from YouTube. Scaffolding is copy-ready so a later agent can populate by copying templates and filling files. Mechanism of population is out of scope here.

## What lives here

| Path | Role |
|---|---|
| `dictionary/` | Reusable, role-neutral primitive language (239 seed entries in four family files) |
| `schema/` | DNA lock, ids/vocab, `graph.yaml` contract, `strats.sql` |
| `backend/` | import / export_catalog / validate / rebuild; derived `strats.sqlite` |
| `strategies/` | Candidate packages. Copy `_template/`. LAYOUT-DEMO: `STRAT-000001` |
| `sources/` | One source, one home under `items/`. Copy `items/_template/` |
| `knowledge/` | Mini-KBs. Copy `_note-template.md`. Prop-firm is an overlay |
| `lineage/` | Cross-strategy pointers (per-package `lineage/` is DNA I) |
| `catalog/` | Indexes, not copies |
| `.obsidian/` | Minimal vault so this folder opens in Obsidian. No community plugins |

Markets: **forex** and **crypto spot**. Horizons: **scalp**, **intraday**, **swing**. Prop-firm rules are an overlay (`knowledge/prop-firms` plus identity tags), not a third library.

IDs and class tokens: [`schema/ids.md`](schema/ids.md). DNA A–I: [`schema/strategy-dna.md`](schema/strategy-dna.md). Graph shape: [`schema/graph.yaml.md`](schema/graph.yaml.md).

## Copy `_template` to add a strategy

1. Next id: scan `strategies/` for `STRAT-(\d{6})-`, increment (`schema/ids.md`).
2. Copy `strategies/_template/` → `strategies/STRAT-NNNNNN-short-slug/`.
3. Fill every `TODO`. **Do not invent exits** (F). If F is unresolved, class is `entry_hypothesis`.
4. Append a one-liner to `catalog/strategies.md`.
5. `python backend/validate.py`

## Copy `_template` to add a source

1. Next id: scan `sources/items/` for `SRC-(\d{6})-`, increment.
2. Copy `sources/items/_template/` → `sources/items/SRC-NNNNNN-short-slug/`.
3. Fill `manifest.md` (kind, locator, creator, rights, hash placeholder).
4. Append a one-liner to `catalog/sources.md`.
5. Do not ingest media until population is started.

Knowledge notes: copy `knowledge/_note-template.md` → `knowledge/<area>/kb-<area>-<slug>.md`.

## Append a dictionary entry

1. Open the matching **family** file under `dictionary/` (do not fork per market).
2. Append a new `## slug — Title` heading — same format as existing entries.
3. Fill the **12 fields** as `- **Field:**` bullets (see `dictionary/README.md`).
4. If that slug already exists **in that file**, pick a more specific slug. Cross-file same slug is allowed (`catalog/dictionary-collisions.md`).
5. Rebuild.

Do not rewrite the 239 seed entries.

## Rebuild / validate

```bash
python backend/rebuild.py
```

Or:

```bash
python backend/import_dictionary.py
python backend/export_catalog.py
python backend/validate.py
```

Files remain canonical. The DB is derived. `catalog/dictionary.md` is generated. `validate.py` fails on missing required strategy files, not on colliding slugs.

## Authority

Mubarak's latest messages > [`STRATS-BUILD-STATE.md`](STRATS-BUILD-STATE.md) > [`STRATS-GROUND-STATE.md`](STRATS-GROUND-STATE.md). Do not delete GROUND-STATE.
