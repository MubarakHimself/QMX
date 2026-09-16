---
id: SCN-0017
title: Stage 0 LAYOUT-DEMO projection preserves entry_hypothesis and unresolved F
type: scenario
status: provisional
component: COMP-QML
depends_on: [COMP-QML, COMP-QMA-CORE, COMP-QMA-DAEMON]
decisions: [DEC-0380, DEC-0386, DEC-0387, DEC-0394, DEC-0396, DEC-0400, DEC-0401, DEC-0406, DEC-0409]
sources: [_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/inputs/worked-mapping.md, _docwork/qml-research-increment-brief.md, docs/decisions/ADR-0023-qml-research-expansion.md]
generated: 2026-09-16
verified: 2026-09-16
stale_after: 90d
---

# SCN-0017: Stage 0 LAYOUT-DEMO projection preserves entry_hypothesis and unresolved F

The first vertical slice (DEC-0394) must project seed package `STRAT-000001` without inventing exits, a short side, a CT-33 mint, or a `research_ref`. This scenario is **provisional** with the architecture package (DEC-0380).

## Given

- Operator-configured seed `root_path` points at the portable Stats tree (DEC-0382).
- research-corpus binds `PlainFileLibrarySource(root_path, source_id="strats")` with AD-4 include/exclude (DEC-0384, DEC-0388).
- A Mission (or session) pins one `snapshot_ref` (DEC-0391).
- Seed package `STRAT-000001` (LAYOUT-DEMO) is class `entry_hypothesis`; every DNA F slot is `unresolved`; it is not extracted research to complete (DEC-0394).
- Dictionary entry `swing-high` exists as a 12-field role-neutral file record; colliding slugs require `(file_path, id)` (DEC-0385, DEC-0396).
- `register_library_kind("strats")` is refused (DEC-0381).
- Stage 0 types may be a read-only projection in this slice; viewing cited seed does not mint `research_ref` (DEC-0401).

## When

An author or agent:

1. `search` / `retrieve` / `cite` of locator for `STRAT-000001` against the pinned snapshot (DEC-0383, DEC-0385).
2. `cite` of dictionary locator `dictionary/market-structure-and-location/locations-and-structure.md#swing-high` (or the equivalent posix path plus fragment).
3. Asks QML vocabulary helpers to resolve `swing-high` from **cited bytes the host passed in** (DEC-0396).
4. Opens the read-only Stage 0 projection of LAYOUT-DEMO (DEC-0394).

## Then

- Cite copies are retained bytes of the pinned snapshot; an uncopied retrieve is `StaleSnapshot`, never live-tree substitution (DEC-0391).
- The vocabulary helper returns the 12 fields and eligible roles from those bytes. It does not register `swing-high` as a kind and does not mint a CT-16 producer (DEC-0396).
- The Stage 0 projection shows class `entry_hypothesis` and F labels `unresolved`. It does not invent stops, take-profits, a short side, or a CT-29 close-reason (DEC-0386, DEC-0400).
- The projection does **not** return a `research_ref`. Identity exists only after an explicit later save (DEC-0394, DEC-0401).
- No CT-33 / CT-34 record is minted. `register_library_kind("strats")` still refuses. Auto-mint from DNA is dead (DEC-0381, DEC-0409).
- Boolean/temporal graph operators on the package (`ALL` / `THEN` / …) stay on the hypothesis plane. Compiling them to `run_slice` is dead (DEC-0386, DEC-0411).
- Ungoverned Python remains legal without opening Stage 0 (DEC-0387).
- Class/test existence of CT-44 helpers is not this scenario's pass; slice 0 proves real seed bytes plus the honesty envelope (DEC-0406, DEC-0286).

## Worked numbers

No registry numeric keys apply. Seed counts that bound the fixture (evidence-summary, 2026-09-16 validate.py OK): 239 dictionary entries parsed; 229 unique ids; 9 colliding keepers; one strategy package besides template (`STRAT-000001`). Those counts are seed-disk facts, not QMX registry values.

GAP(GAP-0064): PRD FR-RES addenda are not written yet; this scenario cites the proposed spine, not the 2026-08-21 PRD.
GAP(GAP-0085): eligible roles including invalidation stay on Stage 0; they are not GAP-0085 nouns.
