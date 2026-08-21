---
id: ARCH-STACK
title: QMF V1 Stack and Pipeline
type: architecture
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP, COMP-QMB, COMP-QML, COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, COMP-OBJECT-STORAGE]
decisions: [DEC-0008, DEC-0009, DEC-0011, DEC-0013, DEC-0022, DEC-0024, DEC-0030, DEC-0033, DEC-0035, DEC-0042, DEC-0045, DEC-0055, DEC-0058, DEC-0059, DEC-0060, DEC-0065, DEC-0089, DEC-0091, DEC-0096, DEC-0099, DEC-0100, DEC-0101, DEC-0102, DEC-0103, DEC-0104, DEC-0106, DEC-0111, DEC-0117, DEC-0118, DEC-0126, DEC-0127, DEC-0128, DEC-0129, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0139, DEC-0141, DEC-0143, DEC-0159, DEC-0167, DEC-0168, DEC-0171, DEC-0178, DEC-0180, DEC-0184]
sources: [DEC-0008, DEC-0009, DEC-0011, DEC-0013, DEC-0022, DEC-0024, DEC-0030, DEC-0033, DEC-0035, DEC-0042, DEC-0045, DEC-0055, DEC-0058, DEC-0059, DEC-0060, DEC-0065, DEC-0089, DEC-0091, DEC-0096, DEC-0099, DEC-0100, DEC-0101, DEC-0102, DEC-0103, DEC-0104, DEC-0106, DEC-0111, DEC-0117, DEC-0126, DEC-0127, DEC-0128, DEC-0129, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0139, DEC-0141, DEC-0143, DEC-0159, DEC-0167, DEC-0168, DEC-0171, DEC-0178, DEC-0180, DEC-0184, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ctrader-venue-facts.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/spotware-org-inventory.md, docs/architecture/dependencies.yaml, docs/registry/variables.yaml, docs/contracts/]
generated: 2026-08-18
verified: 2026-08-21
stale_after: 90d
---

# QMF V1 Stack and Pipeline

QMF V1 is a reusable Python toolbox built as one uv workspace of seven installable packages. The runtime matrix, packaging, quality toolchain, and gate tiers were ratified at the architecture sitting (2026-08-19/20); the library version pins below were verified on the web 2026-08-19 and re-verified at that sitting's reviewer gate. Physical store engines are chosen (Parquet, DuckDB, SQLite, JSONL) behind QMF-owned contracts. A small set of vendor facts remain explicit GAPs and are not implied by any selection here. (DEC-0099, DEC-0100, DEC-0101, DEC-0102, DEC-0117)

## Ratified stack

Every version was verified on the web 2026-08-19 and re-verified at the sitting's reviewer gate. (DEC-0099, DEC-0100, DEC-0101, DEC-0103, DEC-0104)

| Name | Version | Cites |
|---|---|---|
| CPython | 3.14 (3.14.7 current) | DEC-0099 |
| uv (workspace + lockfile) | 0.12.5 | DEC-0100 |
| uv_build | stable, per uv 0.12.x | DEC-0100 |
| ruff (format + lint) | 0.16.3 | DEC-0101 |
| pyright (strict) | 1.1.411 (PyPI) | DEC-0101 |
| pytest | 9.x (9.1.1) | DEC-0101 |
| poethepoet | 0.48.0 | DEC-0101 |
| numpy / pandas / pyarrow | 2.5.2 / 3.0.5 / 25.0.1 — outer packages only; pandas 3.0 is a young major, so ecosystem lag is watched | DEC-0104 |
| duckdb | 1.5.5 (AD-19 analytics store, rebuildable views only; engine major pinned per release) | DEC-0117 |
| TA-Lib (C library + Python wrapper) | 0.7.1 + 0.7.1 — AD-23 canonical arithmetic reference, pinned per QMF release as lockfile-resolved artifacts (distribution filename + hash) plus the declared reference-configuration record asserted at import; verified current 2026-08-20 | DEC-0127 |
| tzdata (PyPI) | pinned in calendar extensions only; `TZPATH` is forced to the pin and the resolved version participates in fingerprints | DEC-0106 |
| Spotware openapi-proto-messages | integer release tag 91 (MIT) — the cTrader venue protocol artifact, pinned in the AD-6 register; the GitHub Releases feed is the change record; a tag change mints a new capability declaration plus gated re-verification. Message definitions only (data, not code) | DEC-0141 |
| protobuf (runtime) | pinned per QMF release; decodes the Spotware proto message definitions at the venue network edge; permitted in `qmf-venue` only, never in `qmf-core` | DEC-0141 |

numpy, pandas, and pyarrow are permitted only in outer packages — never in `qmf-core`, which takes zero outside dependencies. The store stack — Parquet, DuckDB, SQLite, JSONL — is ratified behind QMF-owned contracts, and DuckDB's engine major is pinned per release (DEC-0117). TA-Lib is the ratified AD-23 canonical arithmetic reference — C library 0.7.1 + Python wrapper 0.7.1, pinned per QMF release as lockfile-resolved artifacts (distribution filename + hash) plus a declared reference-configuration record asserted at import — and the reference pair is recorded in the AD-6 `DEPENDENCIES.md` register. (DEC-0104, DEC-0117, DEC-0127) The Spotware `openapi-proto-messages` package supplies the cTrader wire schema, pinned at integer release tag 91; only its proto message definitions are consumed, and the official OpenApiPy SDK is **reference-only** because its pinned Twisted reactor violates AD-6's platform-imposing prohibition, so zero Spotware code runs in QMX. (DEC-0141)

## Runtime matrix

CPython 3.14 is pinned across all packages, CI, and factory sandboxes. Tier-1 tested targets are Windows 11 x86-64 and Ubuntu LTS x86-64 — the operator's workstation and the trading-node VPS. QMF code stays pure-Python and OS-neutral; other platforms work by construction but are untested and not CI-gated in V1. CI gates run locally in the factory until a remote exists, then bind to GitHub Actions. (DEC-0099)

## Stack by layer

| Layer | Language | Runtime | Components | Cites |
|---|---|---|---|---|
| middleware | Python (first Venue adapter is the cTrader Open API in Python) | CPython 3.14; async only at the venue network edge | `COMP-QMF-VENUE`, `COMP-QMF-DATA-INGEST` | DEC-0060, DEC-0099 |
| backend | Pure-Python toolbox | CPython 3.14 | `COMP-QMF-CORE`, `COMP-QMF-REGISTRY`, `COMP-QMF-DATA`, `COMP-QMF-INDICATORS`, `COMP-QMF-STRUCTURE`, `COMP-QMF-RISK` | DEC-0024, DEC-0099 |
| data | Store engines behind QMF-owned contracts | Parquet, DuckDB, SQLite, JSONL; no database server | `COMP-QMF-DATA-STORE`, `COMP-QMF-DATA-BACKUP` | DEC-0117 |
| external | Vendor-owned | cTrader Open API; Dukascopy historical source; news-calendar feed; off-machine object-storage bucket for the nightly, encrypted, versioned backups, its specific provider named at the node/ops sitting | `COMP-CTRADER`, `COMP-DUKASCOPY`, `COMP-CALENDAR-FEED`, `COMP-OBJECT-STORAGE` | DEC-0059, DEC-0117, DEC-0118 |

QMF V1 has no UI layer. Product UI remains outside the reusable foundation, and the future backtesting library is now specified — it is QMB, a separate application-layer product (one pure library plus the `qmb` CLI) that composes the QMF backend libraries as a consumer, living outside the seven-package roster and outside QMF V1. Its application stack is captured below under [QMB application stack](#qmb-application-stack). (DEC-0009, DEC-0159) The QMX bot-authoring library QML is a second such application-layer product — one uv-installable pure library (`import qml`) that composes `qmf-core`, `qmf-registry`, and `qmf-risk` — its stack captured under [QML application stack](#qml-application-stack). (DEC-0180)

## Runtime and version capture points

| Concern | Declared value | Authority |
|---|---|---|
| Python runtime | CPython 3.14 pinned; tier-1 OSes Windows 11 x86-64 and Ubuntu LTS x86-64 | DEC-0099 |
| Package versioning | SemVer in lockstep across the seven roster packages, 0.x until the V1 blueprint ships, one-release deprecation window | DEC-0103 |
| Serialized-contract versioning | per-contract integer format version stamped into every artifact; meaning never mutates — incompatible change mints the next version plus a migration note | DEC-0103 |
| cTrader venue facts (ratified) | Per-field Unix ms UTC with named epoch exceptions; no server clock (receive-time recording mandatory); historical ticks BID/ASK-selectable; 50/5 req/s per connection; 10s heartbeat bound; ~30-day access token with a never-expiring refresh token; 1/100000 wire price scale; one-week tick-history span cap; Spotware proto integer release tag 91. The 17:00-New-York daily boundary and BID-derived trendbars are demoted to measure-per-broker adapter obligations, never hardcoded. Which broker fronts the platform is deployment configuration. | DEC-0135, DEC-0139, DEC-0141 |
| Indicator reference | TA-Lib is the ratified AD-23 canonical arithmetic reference — C library 0.7.1 + Python wrapper 0.7.1, pinned per QMF release as lockfile-resolved artifacts (distribution filename + hash) plus a declared reference-configuration record asserted at import; verified current 2026-08-20 | DEC-0127 |
| Local persistence engines | Parquet (columnar time-series), DuckDB (local analytics), SQLite (transactional metadata), JSONL (append streams), each behind a QMF-owned contract | DEC-0117 |
| Off-machine backup | Nightly, encrypted, versioned, off-machine to an object-storage bucket, with automated sample-restore tests and a periodic full-restore rehearsal; QMF provides the backup, restore, and verify primitives while applications own schedule and execution; the specific provider, encryption key custody, and numeric retention, recovery objectives, and verification cadence are named at the node/ops sitting | DEC-0118, DEC-0045 |

## Build and package tooling

| Concern | Tool | Notes | Cites |
|---|---|---|---|
| Repository, distribution, and package layout | uv workspace | One repository; seven installable packages importing as the `qmf.*` PEP 420 namespace with no `qmf/__init__.py` anywhere; `src/` layout (`src/qmf/<name>/`); every dependency, including sibling packages, declared explicitly | DEC-0100 |
| Build backend | `uv_build` | Stable per uv 0.12.x; one committed `uv.lock`; tier-2 runs each package's tests in an isolated per-package environment so an undeclared import fails | DEC-0100 |
| Test runner | pytest 9.x | Coverage measured per package on every change, floor 80%; the modules implementing CT-01 and CT-02 primitives require 100% branch coverage; every package ships executable tests and reference usage as tier-1 artifacts | DEC-0101 |
| Formatter and linter | ruff 0.16.3 | Format and lint; strictness governs QMF's own source, never consumers | DEC-0101 |
| Type checker | pyright 1.1.411 | Strict, workspace-wide | DEC-0101 |
| Task runner | poethepoet 0.48.0 | Canonical commands `poe fmt \| lint \| types \| test \| check`, identical on every machine | DEC-0101 |
| Dependency and licence gate | `DEPENDENCIES.md` register | Permissive (MIT/BSD/Apache/PSF) freely allowed; LGPL only unmodified and separately installed; GPL/AGPL, strategy-family, and platform-imposing dependencies prohibited; `qmf-core` takes zero outside dependencies; every dependency gets one line: name, licence, why | DEC-0104 |
| Release and deprecation | Two version ladders | Code packages SemVer lockstep (deprecations keep working with a warning for one release before removal); serialized contracts carry per-artifact integer format versions whose meaning never mutates; history is append-only and QMF never loses the ability to read old evidence | DEC-0103 |

Calendar extensions are separate versioned packages outside the seven-package roster, in the same workspace, on their own SemVer ladder — a tzdata pin change is at minimum a minor bump. (DEC-0100, DEC-0106)

## Component classification and public roster

The dependency registry records four independent axes: `kind` (architectural form), `layer` (middleware, backend, data, or external), `roster_role` (public library, public module, internal seam, or external system), and `distribution` (the installable package). The seven-package roster below is the distribution unit; `COMP-QMF-DATA-INGEST`, `COMP-QMF-DATA-STORE`, and `COMP-QMF-DATA-BACKUP` are internal seams of `qmf-data` and add no packages. (DEC-0100, DEC-0024)

| Roster member | `roster_role` | Layer | `distribution` (package / import) | What it carries | Component | Cites |
|---|---|---|---|---|---|---|
| qmf-core | public-library | backend | `qmf-core` / `qmf.core` | Exact money and time primitives, asset-neutral nouns, typed refusals, the single `fp1` serializer, protocol seams; zero outside dependencies | `COMP-QMF-CORE` | DEC-0022, DEC-0100 |
| qmf-registry | public-library | backend | `qmf-registry` / `qmf.registry` | Per-kind records, fingerprint-derived ids, append-only typed lineage edges, promotion skeleton | `COMP-QMF-REGISTRY` | DEC-0033, DEC-0100 |
| qmf-data | public-library | backend | `qmf-data` / `qmf.data` | Seven room-roles, evidence policy, splits, holdout seal, journal, source adapters, backup primitives | `COMP-QMF-DATA` | DEC-0042, DEC-0117 |
| qmf-indicators | public-library | backend | `qmf-indicators` / `qmf.indicators` | Two-mode CT-16 indicator protocol and wrappers around the pinned canonical reference; light and heavy are placements, not species | `COMP-QMF-INDICATORS` | DEC-0055, DEC-0126, DEC-0128 |
| qmf-structure | public-library | backend | `qmf-structure` / `qmf.structure` | QMX-owned causal chart-object families under the CT-17 lifecycle law | `COMP-QMF-STRUCTURE` | DEC-0058, DEC-0129 |
| qmf-venue | public-module | middleware | `qmf-venue` / `qmf.venue` | Venue seam and cTrader translation; an edge module nothing imports | `COMP-QMF-VENUE` | DEC-0059, DEC-0060 |
| qmf-risk | public-module | backend | `qmf-risk` / `qmf.risk` | Ratified Book, BMS, exit, paper-mode, control, and risk-arithmetic boundary (AD-29..41); an edge module nothing imports | `COMP-QMF-RISK` | DEC-0065, DEC-0143 |

The public roster is exactly the five libraries and two modules of DEC-0024. Shared nouns (Venue, Account, Instrument, WriterId) are defined in `qmf-core` and their records owned by `qmf-registry`; edge modules never define shared nouns. Calendar extensions (for example `qmf-calendar-forex`) live in `extensions/` outside the roster on their own SemVer ladder. (DEC-0100)

## Data stores

Every store sits behind a QMF-owned contract with stdlib-typed boundary signatures, so engines are swappable and no database server is required. Only raw-archive and journal formats are evidence-bearing; analytics engines hold rebuildable views, so an engine's format break (for example DuckDB v2.0's new storage format, previewed 2026-08-17) costs a rebuild, never evidence. Engine majors are pinned per release. (DEC-0117)

| Store | Engine | Role | Cites |
|---|---|---|---|
| Columnar time-series | Parquet | Evidence-bearing raw archive and processed partitions, partitioned by source, instrument, and time window | DEC-0117 |
| Local analytics | DuckDB 1.5.5 | Rebuildable analytic views only; engine major pinned per release | DEC-0117 |
| Transactional metadata | SQLite | Metadata behind the owned contract | DEC-0117 |
| Append streams | JSONL | Evidence-bearing journals and lineage edges: one `fp1`-canonical object per line, LF-terminated, append-with-fsync, size-rotated with a monotonic ordinal | DEC-0117 |

Migrations run preflight checks, backup first, dry-run, migrate, verify, with a documented restore path and never in-place mutation of the only copy. Raw originals and lineage are kept forever; journal trimming rules are set only after measured volume. (DEC-0117)

## Pipeline — three tiers bound to factory events

The three tiers bind to factory events, not Git-host mechanics. Commands are host-neutral and run locally in the factory until a remote exists, then bind to GitHub Actions. Factory-internal review layers stack on top, never replaced. (DEC-0102)

| Tier | When it runs | Command | Checks | Cites |
|---|---|---|---|---|
| Tier 1 | Every factory work unit (worktree or temp branch) | `poe check` | format, lint, types, unit tests, coverage | DEC-0102 |
| Tier 2 | Landing into the integration branch | `poe check-integration` | tier 1 plus integration tests and contract tests, each package in an isolated environment | DEC-0102 |
| Tier 3 | Ship / release from integration | `poe check-release` | tier 2 plus build all packages and clean-install smoke on both tier-1 OSes | DEC-0102 |

| Check | Command | Tier |
|---|---|---|
| Format | `poe fmt` | tier 1 |
| Lint | `poe lint` | tier 1 |
| Type check | `poe types` | tier 1 |
| Unit tests + coverage | `poe test` | tier 1 |
| Integration + contract tests | `poe check-integration` | tier 2 |
| Build + clean-install smoke (Windows 11 + Ubuntu LTS) | `poe check-release` | tier 3 |

A contract test is an executable conformance suite for a `CT-*` contract's public shape, owned by the contract's owning package and run by the producer and all consumer packages at tier 2. (DEC-0102)

## Performance budgets

No performance number is invented. Every component ships a benchmark harness (same status as unit tests) measuring speed and peak memory at a load ladder in framework-native units, sized around the roughly-forty-bot reference scenario with 10/100/200 marks. First real measurements become fingerprinted baselines scoped to a declared (OS, CPU-class) tuple, with per-benchmark regression thresholds stated as multiples of measured run-to-run variance; regressions beyond threshold — memory equally with speed — fail the tier-2 merge gate. The one design constraint stated now is that `qmf-core` imports in well under one second. Numeric budgets intentionally await first baselines. (DEC-0111)

## Remaining open selections

- GAP-0032 answered: TA-Lib is the ratified AD-23 canonical arithmetic reference (C library 0.7.1 + Python wrapper 0.7.1), pinned per QMF release as lockfile-resolved artifacts plus a reference-configuration record asserted at import. (DEC-0127)
- GAP-0035 answered: the venue secret lifecycle (AD-26) — secret references not values, a single in-memory holder, one refresher per credential, and the cTID compromise drill. (DEC-0136)
- GAP-0036 and GAP-0038 answered: the four-command vocabulary and uncertainty law (AD-27) and the one-port four-contract adapter with capability discovery (AD-28). (DEC-0137, DEC-0138)
- GAP-0037 answered: the cTrader venue facts are ratified with corrected evidence grades (DEC-0135); broker identity is deployment configuration (DEC-0139); trend-bar price basis and the venue daily-bar boundary are measured per broker, never hardcoded.
- Off-machine backup design is ratified — nightly, encrypted, versioned, object-storage bucket, with automated sample restores plus a periodic full rehearsal (DEC-0118); only the specific provider, encryption key custody, and numeric recovery objectives remain node/ops-sitting items.

## QMB application stack

QMB is the experimentation/backtesting application product — one pure library plus the `qmb` CLI in one wheel — outside the seven-package roster and outside QMF V1, consuming the QMF backend libraries in lockstep. It inherits QMF's runtime and quality toolchain unchanged: CPython 3.14 on the tier-1 OSes, uv, `uv_build`, ruff, pyright, pytest, and poethepoet exactly as fixed above. Its distribution is `uv add qmb` — a lockfile-tracked pinned dependency; `uv tool` is a CLI-only convenience for reaching the command, never a sandbox-provisioning path. SemVer is display-only provenance, never identity, and the `qmf-*` packages are consumed in lockstep. (DEC-0167)

| Name | Version | Role | Cites |
|---|---|---|---|
| click | 8.4.2 (exact) | The `qmb` CLI door | DEC-0168 |
| optuna | 4.9.0 (exact) | Default sampler adapter behind the typed parameter-space port; runs `n_jobs=1` | DEC-0168 |

Both pins were verified on the web 2026-08-20. `click` and `optuna` are pinned exactly; an optuna **major** bump is a contract-versioning event — the sampler sits behind a versioned adapter port — not a silent upgrade, and optuna always runs single-process (`n_jobs=1`), leaving process management to the QMB orchestrator. The pins are held authoritatively by the `qmb_cli_pin` and `qmb_sampler_pin` registry rows — non-configurable version pins, never UI-editable — and are referenced here, not restated as authority. (DEC-0168)

## QML application stack

QML is the QMX bot-authoring library — one uv-installable pure library (`import qml`) — outside the seven-package roster and outside QMF V1, consuming the QMF backend libraries (`qmf-core`, `qmf-registry`, `qmf-risk`) in lockstep. It inherits QMF's runtime and quality toolchain unchanged: CPython 3.14 on the tier-1 OSes, uv, `uv_build`, ruff, pyright, pytest, and poethepoet exactly as fixed above. Its distribution is `uv add qml` — a lockfile-tracked pinned dependency — and SemVer is display-only provenance, never identity (CT-33 `fp1` and the logic-artifact source-manifest identity carry Bot identity); the `qmf-*` packages are consumed in lockstep. **QML pins no new runtime dependency**: it adds nothing beyond the `qmf-*` packages it consumes, so there is no QML pins table below. (DEC-0180)

One mechanism is deliberately scoped rather than pinned: the conformance gate's Layer-2 runner isolation in V1 is **static AST/import scanning + capability starvation (hosts inject read surfaces only) + host process isolation** (stdlib process management, the host owning process spawning). Hardened OS-level runtime confinement (restricted tokens/job objects on Windows, seccomp-class on Linux) is a **named deferred dependency** of the node/platform sitting, **not a hidden pin**; a dynamically-evasive malicious bot is out of V1's threat model (bots are operator- or operator's-agent-authored). Any future authoring-surface dependency (an editor, a grammar) arrives with its own sitting. (DEC-0178)

## Model training

None — QMF V1 trains or fine-tunes no model. MIS model work and the agentic ML harness remain outside current QMF V1 scope. (DEC-0089, DEC-0091)

## Related

Layers, containers, and external systems: `docs/architecture/overview.md`. Component graph: `docs/architecture/dependencies.yaml`. Values: `docs/registry/variables.yaml`. Interface schemas: `docs/contracts/`. Ratified spine: `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md`.
