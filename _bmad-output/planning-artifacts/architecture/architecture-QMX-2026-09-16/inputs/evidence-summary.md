---
name: evidence-summary
sitting: architecture-QMX-2026-09-16
created: 2026-09-16
status: input
---

# Evidence summary — STRATS → QMX Library sitting

Planning checkout: `main@f722694e3c2bd190ce01ea933d7f68f6f9dd66b7` (dirty docs preserved, not mutated).
Implementation inspect: `.worktrees/integration-inspect` @ `integration@8510c032496bb870824ecc5c4f807e8a4e4f167e` (recon `1b451a8` is behind).
UI worktree: `.worktrees/ui` @ `af66288` — docs/planning only; no frontend app.
STRATS: `C:/Users/Mubarak/Desktop/Stats`. Debris: `C:/Users/Mubarak/Desktop/strats` (tar-flag dirs + empty git remnant).

## STRATS (canonical)

- Authority: Mubarak > `STRATS-BUILD-STATE.md` > `STRATS-GROUND-STATE.md`. GROUND-STATE “empty root” is stale.
- Files canonical; `backend/strats.sqlite` derived. `python backend/validate.py` **executed 2026-09-16: OK**. 239 primitives parsed; sqlite 239 rows / 229 unique ids; 9 colliding keepers; package `STRAT-000001` present.
- DNA A–I locked. Graph operators Boolean/temporal/lifecycle. `graph.yaml` is knowledge, not an executor.
- Dictionary: 12 fields (historical ~25 discussed; do not rewrite 239). 86 ontology-seed entries.
- Only strategy besides template: LAYOUT-DEMO `STRAT-000001` class `entry_hypothesis`; all F slots `unresolved`. Not extracted research.
- Zero real `SRC-*`, zero `kb-*` notes. Population paused.
- `.hermes` is historical evidence, not canonical. Rejected: specialist fleet, staging/curator, n8n-as-required, tests-as-product, promotion ceremony, software-first.

## QMX parents

- Workbench AD-3: Library = fp1 projection; STRATS = KnowledgeSource; no new COMP; `strats` is not a Library kind.
- QMA AD-19 / CT-44: read-only adapt-to-library; six evidence_confidence dims; cite-copy; literal search; GAP-0073 hybrid deferred. AD-19 last sentence (“empty corpus”) is **factually stale**.
- CT-34 roles: `level | trigger | confirmation | filter`. WHEN lives in Python. GAP-0085 nouns deferred.
- QMB `registryread/library.py` on integration: `STRATS_CORPUS = "KnowledgeSource"`; `register_library_kind("strats")` refused; `COMP_LIB_MINTED = False`.
- `PlainFileLibrarySource` exists (filesystem, skips `.*` parts, currently hashes all other files including `backend/strats.sqlite`).
- `research-corpus` plugin registers `source_id="strats"` but `StratsCorpus` is an **in-memory two-file stub**, not Stats.
- `qma-ui-contract` is a stub (GAP-0081). ui@af66288 has no Library routes.
- PRD 2026-08-21 has no STRATS/knowledge-product FRs. GAP-0061 covers workbench addenda, not this rail.

## Reuse-or-new

Reuse COMP-QMA-CORE, COMP-QMA-DAEMON, research-corpus pack, COMP-QMB projection, COMP-QML authoring, COMP-QMF-REGISTRY kinds. No new COMP, no new CT. First slice: bind `PlainFileLibrarySource(root_path)` from the pack.
