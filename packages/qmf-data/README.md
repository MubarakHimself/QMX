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

Story 5.1 lands `COMP-QMF-DATA-BACKUP` (`qmf.data.backup`): the CT-14 encrypted,
versioned off-machine copy primitive. It consumes CT-26 `RoomExport` input,
encrypts through an injected `PayloadCipher`, and puts each copy as a **new**
versioned artifact through an injected `ObjectStorage` port. Encryption is
required as a pointer; provider selection, object-key layout, credentials, and
numeric RPO/RTO/retention stay node/ops-owned. Cross-world / `simulated` copies
are policy rejections; unreachable or corrupt object storage is a storage-failure
refusal — never raised, never claimed complete.

Story 5.2 lands the matching restore primitive (`OffMachineRestore`): fetch +
decrypt into a **replacement** `EvidenceStore` root — never an in-place rewrite of
the only local copy — with int64 UTC-ns timestamps restored verbatim. Restored
reads still enforce the wired 12-month seal and world isolation as policy
rejections; discarding the only local raw copy is refused under this component's
authority.

Story 5.3 lands the verify primitives (`OffMachineVerify`): automated
`sample_restore` and `full_restore_rehearsal` are the **only** source of a
`RecoverabilityClaim` — never a snapshot alone (SCN-0004). A corrupt restore is a
`storage failure` with no claim. `migrate_evidence` runs preflight → backup-first →
dry-run → migrate → verify against a documented restore path and never mutates the
only copy. Numeric restore-verification cadence, RPO, RTO, and retention stay null
node/ops pointers.

Story 5.4 lands the application-owned nightly cycle helper (`OffMachineCycle`):
`run_once` backs up every room-role (including the registry room) for one world,
puts encrypted versioned copies through CT-14, and runs sample-restore (plus an
optional full-restore rehearsal when the application opts in). There are **no**
threads, cron, or daemons in `qmf-data` — asking the boundary to own the schedule
or a numeric RPO/RTO is a typed policy rejection. Encryption stays a required
pointer; credentials never enter the cycle report.

`EvidenceStore(root).for_world(world)` returns the four boundaries for one world.
The engines sit behind their owned `typing.Protocol` contracts, so each is
swappable. The public data-policy contracts (CT-10 observations, CT-12 splits, the
entity-journal projections) arrive in later Epic 3 stories on top of this seam.

`qmf-data` depends only on `qmf-core` and declares its own engine libraries
(`pyarrow`, `duckdb`) — see the workspace `DEPENDENCIES.md`. Build, lint,
type-check, and test it through the workspace `poe` tasks — never in isolation.
