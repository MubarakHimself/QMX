# DEPENDENCIES register (AR-07 / AD-6; DEC-0104)

Every third-party dependency in this workspace is listed here with its **name**,
**licence**, and **why**. This register is the licence gate: adding a dependency
means adding its row here first.

## Policy

- **Allowed, freely:** MIT, BSD (2/3-clause), Apache-2.0, PSF.
- **Rejected:** GPL / AGPL; any **strategy-family** dependency (a library that
  encodes trading edge or a specific strategy school); any **platform-imposing**
  dependency (one that dictates an event loop, reactor, daemon, or runtime the
  platform must adopt — e.g. Twisted).
- **LGPL:** permitted **only** if used unmodified **and** installed separately
  (never vendored or statically bound).
- **`qmf-core` takes zero outside dependencies** (stdlib only). numpy / pandas /
  pyarrow are permitted **only** in outer packages, and only when actually
  needed — none are needed at the scaffold stage, so none are declared yet.

## Version ladders

- The **seven roster packages** (`qmf-core`, `qmf-registry`, `qmf-data`,
  `qmf-indicators`, `qmf-structure`, `qmf-venue`, `qmf-risk`) version in
  **SemVer lockstep**, `0.x` until the V1 blueprint ships. (AR-09; DEC-0103)
- **`qmf-calendar-forex`** rides its **own SemVer ladder** outside roster
  lockstep, with **`tzdata` pinned**; a `tzdata` pin change is at minimum a
  minor bump on that ladder. (AR-02/AR-27; DEC-0106)
- **`qml`** is an application-layer product outside the seven-package roster,
  on its **own SemVer ladder as display-only provenance** (never identity). It
  adds **no new runtime dependency** beyond `qmf-core`, `qmf-registry`, and
  `qmf-risk`. (DEC-0180)
- **`qmb`** is an application-layer product outside the seven-package roster,
  on its **own SemVer ladder as display-only provenance** (never identity). It
  is one wheel — the pure library plus the `qmb` CLI — consuming the six
  backend `qmf-*` packages in lockstep and never `qmf-venue`. It pins
  `click==8.4.2` and `optuna==4.9.0`. (DEC-0159, DEC-0167, DEC-0168)
- **`qmn`** is an application-layer product outside the seven-package roster,
  on its **own SemVer ladder as display-only provenance** (never identity). It
  is the trading node (code name only) and the **one sanctioned importer** of
  `qmf-venue` at its `qmn.venue` subpackage (DEC-0186, DEC-0241). Story 24.1
  declared `qmf-core` and `qmf-venue`; Story 25.10 adds
  `prometheus-client==0.26.0` for registry and exposition format only (no
  library HTTP server thread). `protobuf==7.36.0` stays declared only in
  `qmf-venue`. It ships **no console-script** entry point (DEC-0211, DEC-0220).
- CPython **3.14** is pinned across every package (`.python-version`,
  per-package `requires-python`). (AR-04; DEC-0099)

## Runtime dependencies

| Name | Version | Licence | Used by | Why |
|---|---|---|---|---|
| tzdata | `==2025.2` | Apache-2.0 | `qmf-calendar-forex` (extension) | Pinned IANA time-zone database; the extension forces `TZPATH` to this pin and verifies the resolved tzdb equals it, and the pinned version participates in fingerprints. (DEC-0106) |
| pyarrow | `==25.0.1` | Apache-2.0 | `qmf-data` (roster) | The **Parquet** store engine for the CT-11 columnar time-series raw archive; embedded, no database server. Declared only in `packages/qmf-data/pyproject.toml`; never crosses a boundary signature. (Story 3.1; AR-30, DEC-0117) |
| duckdb | `==1.5.5` | MIT | `qmf-data` (roster) | The **DuckDB** store engine for CT-11 rebuildable analytics views only (never evidence-bearing); embedded, no database server. Declared only in `packages/qmf-data/pyproject.toml`; never crosses a boundary signature. (Story 3.1; AR-30, DEC-0117) |
| protobuf | `==7.36.0` | BSD-3-Clause | `qmf-venue` (roster) | The Protobuf **runtime** for the venue transport. qmf-venue owns its own transport: the Spotware `openapi-proto-messages` release (integer tag **91**, `registry:venue_protocol_artifact`) is compiled **in-house** from its proto message definitions (data, not code) via `google.protobuf`, and **zero Spotware code runs** — the OpenApiPy SDK is reference-only (its pinned Twisted reactor is platform-imposing → rejected below). Declared only in `packages/qmf-venue/pyproject.toml`; never crosses a boundary signature and never leaks a compiled message into `qmf-core`. (Story 8.2; AR-43, DEC-0141) |
| click | `==8.4.2` | BSD-3-Clause | `qmb` (off-roster app) | The `qmb` CLI door. Declared only in `qmb/pyproject.toml`; a major bump is a contract-versioning event (`registry:qmb_cli_pin`). (Story 13.1; DEC-0168) |
| optuna | `==4.9.0` | MIT | `qmb` (off-roster app) | The default TPE-class sampler adapter. Declared only in `qmb/pyproject.toml`; adapters run `n_jobs=1` (fan-out is the orchestrator's); a major bump is a contract-versioning event (`registry:qmb_sampler_pin`). (Story 13.1; DEC-0168, DEC-0161) |
| prometheus-client | `==0.26.0` | Apache-2.0 | `qmn` (off-roster app) | Metric registry and Prometheus exposition format for the node's `qmn_` signal families. Declared only in `qmn/pyproject.toml`; used as registry + text exposition only — the evidence door serves `/metrics` and no library-spawned server thread exists. (Story 25.10; TN-15 / DEC-0200) |

`qmf-data` is the first roster package to declare runtime outside-dependencies —
`pyarrow` and `duckdb`, the CT-11/CT-09 store engines (Parquet + DuckDB; SQLite and
JSONL are stdlib). They are declared **only** in `qmf-data`'s own pyproject and are
installed into the gate environment via the root `store-engines` dependency group,
which pulls in the `qmf-data` workspace member. `qmf-registry → qmf-data` is the sole
inter-library edge; every other roster package depends only on `qmf-core` (declared
as workspace dependencies, not third-party). (AR-06; L30)

`qmf-venue` follows the identical pattern for `protobuf`: it is declared **only** in
`qmf-venue`'s own pyproject and installed into the gate environment via the root
`venue-proto` dependency group, which pulls in the `qmf-venue` workspace member. The
protobuf runtime is a **qmf-venue-only** dependency — no other package declares or
imports it — and qmf-venue still imports only `qmf-core` among the roster (protobuf
is third-party, not a workspace edge). (AR-06/AR-43; L30; DEC-0141)

## Toolchain (workspace `dev` dependency-group)

The canonical QMF toolchain, pinned for byte-identical results on every machine
(AR-11; DEC-0101/0102). The committed `uv.lock` pins the full transitive set.

| Name | Version | Licence | Why |
|---|---|---|---|
| ruff | `==0.16.3` | MIT | Formatter + linter (`poe fmt` / `poe lint`). |
| pyright | `==1.1.411` | MIT | Strict, workspace-wide type checker (`poe types`). |
| pytest | `>=9,<10` | MIT | Test runner (`poe test`). |
| pytest-cov | `>=7,<8` | MIT | Coverage measurement + the Tier-1 floor. |
| poethepoet | `==0.48.0` | MIT | Task runner exposing `poe fmt / lint / types / test / check`. |

## SSSF factory-gate group (`dev`, essentials) and `scan`

Preserved from the factory stamp; the merge gate runs `ruff check .`,
`mypy adws`, and `pytest -q adws/tests` against `adws/`.

| Name | Version | Licence | Why |
|---|---|---|---|
| mypy | (lockfile) | MIT | Type-checks `adws` for the SSSF gate (`mypy adws`). |
| types-PyYAML | (lockfile) | Apache-2.0 | Stubs so `mypy adws` resolves PyYAML. |
| pydantic | (lockfile) | MIT | Imported by `adws/adw_modules`; needed for `adws/tests`. |
| python-dotenv | (lockfile) | BSD-3-Clause | Imported by `adws/adw_modules`. |
| pyyaml | (lockfile) | MIT | Imported by `adws/adw_modules`. |
| rich | (lockfile) | MIT | Imported by `adws/adw_modules`. |
| skylos | (lockfile) | MIT | AI-defect / dead-code scan; isolated in the `scan` group because its build does not install everywhere (treated as TOOL UNAVAILABLE on failure, never a pass/fail). |

## Build backend

| Name | Version | Licence | Why |
|---|---|---|---|
| uv_build | `>=0.12,<0.13` | Apache-2.0 OR MIT | Per-package build backend; produces the `qmf.*` PEP 420 namespace wheels with no `qmf/__init__.py`. |

## External tools (not Python dependencies)

Pinned tools and container images the VPS / ops toolkit invoke. They never
enter a `pyproject.toml` dependency list. Observability images run as
**process-isolated containers** under `qmn/deploy/observability/` only — the
sole VPS surface allowed to use containers — and are never linked into `qmn`
(DEC-0200, DEC-0212, AR-83). Grafana/Loki/Promtail are AGPL; that licence
binds those container processes alone. The operator named Prometheus and
Grafana (DEC-0212); floating tags are forbidden.

| Name | Version | Licence | Used by | Why |
|---|---|---|---|---|
| just | `v1.58.0` | CC0-1.0 | ops toolkit | `just node-…` recipe runner (Story 25.12; DEC-0201). |
| docker-ce (engine) | `28.3.3` | Apache-2.0 | observability stack only | Container runtime for `qmx-observability.service`; node stays uncontainerised (Story 25.17; DEC-0201). |
| docker compose plugin | `2.39.2` | Apache-2.0 | observability stack only | Runs the checked-in `compose.yml` under `qmn/deploy/observability/` (Story 25.17). |
| rclone | `v1.75.0` | MIT | backup unit | Off-machine CT-14 transfer (DEC-0198). |
| prom/prometheus | `v3.5.5` | Apache-2.0 | observability compose | Scrapes loopback `/metrics`; LTS pin (Story 25.17; DEC-0200). |
| grafana/grafana | `13.1.4` | AGPL-3.0-only | observability compose | Operator-named dashboard UI; process-isolated container (Story 25.17; DEC-0212). |
| grafana/loki | `3.7.7` | AGPL-3.0-only | observability compose | Operator-log store under `/var/lib/qmx-observability` (Story 25.17; DEC-0200). |
| grafana/promtail | `3.6.11` | AGPL-3.0-only | observability compose | Reads `LogNamespace=qmn` only — never the system journal (Story 25.17; DEC-0200). |

## Permitted but not yet added

Recorded so their licences and homes are pre-cleared; add the row's version and
flip it to a live section when a story first needs it.

| Name | Licence | Intended home | Note |
|---|---|---|---|
| numpy | BSD-3-Clause | outer packages only | 2.5.2 pin (never in `qmf-core`). |
| pandas | BSD-3-Clause | outer packages only | 3.0.5 pin (young major; ecosystem lag watched). |
| TA-Lib (C + Python wrapper) | BSD-3-Clause | `qmf-indicators` | Canonical arithmetic reference, 0.7.1 + 0.7.1. (DEC-0127) |
