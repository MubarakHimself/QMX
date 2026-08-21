# qmf-data

Room-roles, evidence policy, dataset splits, the holdout seal, journals, source adapters, and backup primitives.

`qmf-data` imports as `qmf.data` under the PEP 420 `qmf.*` implicit namespace
(there is no `qmf/__init__.py` in any distribution). It versions in SemVer lockstep with the other six roster packages (0.x until the V1 blueprint ships).

## Status

Story 3.1 lands the dependency-free persistence seam `COMP-QMF-DATA-STORE`
(`qmf.data.store`): the CT-11 append-store, CT-13 journal, CT-09 registry room,
and CT-26 store-to-backup boundaries, over the four ratified engines — **Parquet**
(columnar time-series, evidence-bearing), **DuckDB** (rebuildable analytics views
only), **SQLite** (transactional metadata), and **JSONL** (append streams) — with
no database server. Every artifact is keyed on its `fp1:sha256:<hex>` fingerprint
(a byte-identical re-write is idempotent, a true collision is refused and alarmed);
the seven room-roles are instantiated per world; a `world = simulated` write and a
cross-world read are policy rejections; and any engine failure is translated to a
`storage failure` refusal at the boundary, never raised across a package seam.

`EvidenceStore(root).for_world(world)` returns the four boundaries for one world.
The engines sit behind their owned `typing.Protocol` contracts, so each is
swappable. The public data-policy contracts (CT-10 observations, CT-12 splits, the
entity-journal projections) arrive in later Epic 3 stories on top of this seam.

`qmf-data` depends only on `qmf-core` and declares its own engine libraries
(`pyarrow`, `duckdb`) — see the workspace `DEPENDENCIES.md`. Build, lint,
type-check, and test it through the workspace `poe` tasks — never in isolation.
