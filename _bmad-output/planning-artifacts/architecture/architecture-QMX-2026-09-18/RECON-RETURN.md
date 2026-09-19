---
name: Stage A freshness reconciliation
sitting: architecture-QMX-2026-09-18
status: checkpoint — not architecture ratification
---

# RECON-RETURN — freshness vs the stale audit

## Working set (this sitting)

| Track | Path | Revision | Notes |
|---|---|---|---|
| Docs / planning workspace | `C:/Users/Mubarak/Desktop/QMX` | `main` = `b8b4d21a3d6ec33158254f1827912c8fc0c4dcc3` = `origin/main` | Dirty only untracked planning/research; no production code edits |
| Implementation inspected | `C:/Users/Mubarak/Desktop/QMX-worktrees/epic-051-skylos-mill-split` | `270e992995c2378ca63cf6343254ef8140a8c97e` = `origin/integration` | Current implementation HEAD. Matches the 2026-09-17 review-delta checkpoint |
| Audit-era implementation | `C:/Users/Mubarak/Desktop/QMX/.worktrees/integration-inspect` | `8510c032496bb870824ecc5c4f807e8a4e4f167e` | **32 commits behind** `origin/integration`. Do not use for absence claims |
| Runtime observed | same 270e992 worktree | CPython **3.14.6** | Docs pin 3.14 (3.14.7 current at last stack verify). No fetch performed |

No `git fetch`, checkout, reset, or stash. Concurrent factory worktrees (epics 049–052, Skylos chunks) were listed and left untouched.

Delta `8510c03..270e992` is **32 commits**, entirely QML research mill + QMA knowledge/discovery/graduation quality. No QMB/QMN/QMF package changes in that delta (matches review-delta §3).

## Tests executed now (not the audit’s 54)

| Command | CWD | Revision | Result |
|---|---|---|---|
| `uv run --project qml python -m pytest -q --tb=line` on mill/store/stage0/legal/projection | mill-split worktree | 270e992 | **32 passed in 5.96s** |
| `uv run --project qmn python -m pytest -q --tb=line qmn/tests/test_qmn_conformance.py` | mill-split | 270e992 | **5 passed, 1 skipped in 2.21s** |
| QMA daemon selected tests | mill-split | 270e992 | **blocked**: `qmx-agents/.venv` has no Python executable; `uv sync --frozen` refused the same invalid env. Findings remain **source-inspected** |

The audit’s 54-test / 12.95s claim is **historical at 8510c03**. It is not current and not comprehensive.

## Finding refresh

Format: `id | original claim | current evidence | status | consequence`

| id | original claim / source | inspected now | status | consequence |
|---|---|---|---|---|
| F-01 | QML Stage 0 types not implemented (`8510c03` audit) | `qml/src/qml/research/stage0.py` + vocab/projection/collapse @ 270e992; 32 mill tests green | **superseded** | Do not rebuild Stage 0 |
| F-02 | Research persistence prospective | `qml/src/qml/host/research_store.py` blob store under `research_root`; tests green | **superseded** (listing API still **partial**) | Reuse host blob; add listing if browse is in scope |
| F-03 | Graduation unproven | `graduate_mill_to_governed` + `qml/host/graduation.py`; tests green | **partial** | Lineage attach exists; does not compile DNA→bot; e2e QML→QMB→QMN still unverified |
| F-04 | Federated discovery absent | `qma/daemon/discovery/federated.py` + wire DTO; two hit classes only | **superseded** as source; QMA tests not executed here | Reuse concatenate; do not add `strats` / hypothesis hit class |
| F-05 | Book/BMS required on full-run config | `ResolvedRunConfig` still requires `book_fp1`/`bms_fp1` @ 270e992 | **retained** | Alternative live system is not a dummy wrapper |
| F-06 | Venue kinds closed CTRADER/REPLAY/CONFORMANCE | `VenueClientKind` unchanged | **retained** | New protocol ≠ extra account |
| F-07 | Graph Template catalog in-memory stand-in | Confirmed; daemon ships zero templates | **retained** | Templates rebuild from plugins; OK |
| F-08 | TaskGraphStore in-memory | Confirmed; **no edges stored**; dispatcher does not walk successors | **retained + worsened** | Must extend in place, not mint a second engine |
| F-09 | Topology only refuses direct back-edges | `validate_graph_template_topology` admits `A→B→C→A` and `A→A` | **retained** | Close as DAG law |
| F-10 | Daemon listener drains bytes, no dispatch | `DaemonProcess._handle_client` confirmed | **retained** | Wire vocabulary exists; UI command bus not live |
| F-11 | MemoryProvider protocol; no default engine | Registry empty by default; research desk binds in-process dict | **retained** | GAP-0072 still open |
| F-12 | QMA Session ≠ product session | `Session` is execution container only | **retained** | Authoring/app-use are new overlays |
| F-13 | Product Manager Role | `desks.py` Role `Product Manager`; pack `pm-coordination` | **retained** | Label → Portfolio Manager; slug stays |
| F-14 | Audit “missing app/session/package/data-recipe contracts” | Still no those product records as QMF kinds | **retained** as design work | Place in existing COMPs, not qmf-core |
| F-15 | 54 tests prove the system | Historical, narrow, old revision | **unverified as current** | Do not cite |

## Codex reference recon

Package `QMX-REFERENCE-RECON-20260918T082954Z` included. Highest transferable contracts: discoverable data resources; preview vs export job; replay-to-live stream phase; widget/app declarations + shared parameters; authoring vs app-use. LSE heatmap 404 is a failed navigation, not proof of absence.

## What this sitting will not claim

- Whole-system e2e QML→QMB→QMN
- Live/demo broker, GPU, backup/restore
- QMA pytest green at 270e992 (venv blocked)
- Ratification of ADR-0023 (still provisional)
