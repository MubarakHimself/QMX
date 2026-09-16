---
name: worked-mapping
sitting: architecture-QMX-2026-09-16
created: 2026-09-16
status: input
---

# Worked seed → QML Stage 0 mapping

First-distill “knowledge rail” wording is historical. Owner of meaning types is now QML Stage 0; QMA CT-44 remains cite transport. Outcomes (no auto CT-33, no invented F) unchanged.

## Case 1 — well-specified primitive: `swing-high`

| STRATS | Survives as | QMX home | Notes |
|---|---|---|---|
| 12-field dictionary entry | Knowledge bytes | CT-44 locator `dictionary/market-structure-and-location/locations-and-structure.md#swing-high` | Role-neutral; eligible roles include location/trigger/invalidation |
| Evidence URLs | Opaque evidence_label + retained cite copy | Citation after `cite` | QMA does not parse URLs into registry |
| Eligible roles | Informal translation guide | Not CT-34 until a bot is authored | `location` ≈ `level`; `trigger` ≈ `trigger`; invalidation is Book/F, not a CT-34 role |

Does **not** become a CT-16 producer or CT-33 bot.

## Case 2 — LAYOUT-DEMO strategy: `STRAT-000001`

| DNA | Content | QMX mapping |
|---|---|---|
| A identity | `STRAT-000001`, `entry_hypothesis`, forex, intraday | Knowledge object id = STRATS id inside snapshot; **not** `fp1` |
| B evidence | empty SRC; claims unresolved | Cite package files; no CT-10 |
| C+D bindings | 4 primitives; `liquidity-sweep` file_path unresolved | Keep as knowledge; colliding slug **must** carry `file_path` |
| E graph | ALL(4) THEN enter(long) | Knowledge only. Do not compile to `run_slice`. Python logic later may encode WHEN |
| F exits | all `unresolved` | Stay `entry_hypothesis`. Do not invent Book exits. CT-33 `permitted_exit_intents` may be empty |
| G/H/I | unresolved / no parents | Searchable knowledge; not registry lineage |

**What QMX cannot yet express as executable:** Boolean/temporal graph operators as declaration (CT-34 has no ALL/sequence/within); unresolved pair/TF/session params; trigger≠order; asymmetric short.

**Handoff if someone later authors a bot:** human/QML writes CT-34 legs (`level` from session-high, `trigger` from sweep+engulfing, `filter` from London window) + Python for ALL/THEN; CT-33 with empty exit intents; QMB governed replay; human promote. Graph.yaml remains the source-faithful record.

## Case 3 — ambiguous / weak: `level-invalidation`

Ontology-seed, thin citations. Survives as knowledge with six confidence dims (empirical_status low). Must not become a CT-29 close-reason or Book exit policy.

## Case 4 — variant / lineage

No real parents in corpus. Plane I (STRATS lineage DAG) ≠ CT-07 registry edges ≠ ExperimentSpec `branches-from`. When a variant appears, record it in STRATS first; a later bot may cite the package locator in origin metadata without copying DNA into CT-07.

## Informal role translation (not a schema merge)

| STRATS binding role (demo + dictionary eligible) | Closest CT-34 | Remainder |
|---|---|---|
| location | `level` | |
| trigger | `trigger` | compound ALL lives in Python |
| filter | `filter` | |
| confirmation | `confirmation` | |
| invalidation / stop / management | none | Book / CT-23 / DNA F |
| context / regime | `filter` or Python | GAP-0085 SessionRule stays deferred |

GAP-0085 nouns stay unfilled. This table is a handoff aid, not a mint.
