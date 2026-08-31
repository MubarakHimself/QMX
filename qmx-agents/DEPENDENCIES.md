# DEPENDENCIES register (AR-Q01 / AR-Q09; DEC-0334, DEC-0104)

Every third-party dependency in this nested QMA workspace is listed here with its
**name**, **licence**, and **why**. This register is the licence gate: adding a
dependency means adding its row here first. Shape matches the parent QMF
`DEPENDENCIES.md`.

## Policy

- **Allowed, freely:** MIT, BSD (2/3-clause), Apache-2.0, PSF.
- **Rejected:** GPL / AGPL; any **strategy-family** dependency; any
  **platform-imposing** dependency (event loop / reactor / daemon the platform
  must adopt).
- **LGPL:** permitted only if used unmodified and installed separately.
- **`qma-core` depends only on `qmf-core`** among workspace/path edges (DEC-0335).
- Runtime third-party pins from AR-Q09 (websockets, OpenTelemetry, OpenCodex,
  duckdb for fold views, …) arrive with the stories that wire them — none are
  declared at this structural seed.

## Version ladders

- The three QMA packages (`qma-core`, `qma-wire`, `qma-daemon`) version in
  **SemVer lockstep with the QMF workspace**, `0.x` until the V1 blueprint ships.
  Package version is **display-only provenance**, never identity content
  (AR-Q11; DEC-0335).
- **`qma-ui-contract`** is a deferred stub only (GAP-0081; AR-Q08) and is not a
  workspace member.
- CPython **3.14** is pinned (`.python-version`, per-package `requires-python`)
  (AR-Q09; DEC-0334).

## Workspace / path dependencies

| Name | Version | Licence | Used by | Why |
|---|---|---|---|---|
| qmf-core | path `../packages/qmf-core` (editable) | (workspace) | `qma-core` (and transitively `qma-wire`, `qma-daemon`) | Parent definitions-only roster package: typed refusals, `fp1`, money, time, ids. Sole declared dependency of `qma-core` (DEC-0335, DEC-0302). |
| qma-core | workspace | (workspace) | `qma-wire`, `qma-daemon` | QMA definitions package (ontology, ports, plugin surface, refusals). |
| qma-wire | workspace | (workspace) | `qma-daemon` | Sole cross-boundary contract package (DEC-0304, DEC-0347). |

## Runtime dependencies

None at the structural seed. AR-Q09 pins (websockets 17.1, duckdb 1.5.5,
OpenTelemetry Python SDK 1.44.0, OpenCodex, …) are recorded in
`docs/architecture/stack.md` §QMA application stack and land when the stories
that consume them declare them here first.

## Toolchain (workspace `dev` dependency-group)

| Name | Version | Licence | Why |
|---|---|---|---|
| ruff | `==0.16.5` | MIT | Formatter + linter (AR-Q09 bump from parent 0.16.3). |
| pyright | `==1.1.411` | MIT | Strict type checker. |
| pytest | `>=9,<10` | MIT | Test runner. |
| pytest-cov | `>=7,<8` | MIT | Coverage measurement. |
| poethepoet | `==0.48.0` | MIT | Task runner (`poe check`). |
