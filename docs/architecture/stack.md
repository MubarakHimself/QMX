---
id: ARCH-STACK
title: QMF V1 Stack and Pipeline
type: architecture
status: ratified
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP, COMP-QMB, COMP-QML, COMP-QMN, COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, COMP-OBJECT-STORAGE, COMP-QMA-CORE, COMP-QMA-WIRE, COMP-QMA-DAEMON]
decisions: [DEC-0008, DEC-0009, DEC-0011, DEC-0013, DEC-0022, DEC-0024, DEC-0030, DEC-0033, DEC-0035, DEC-0042, DEC-0045, DEC-0055, DEC-0058, DEC-0059, DEC-0060, DEC-0065, DEC-0089, DEC-0091, DEC-0096, DEC-0099, DEC-0100, DEC-0101, DEC-0102, DEC-0103, DEC-0104, DEC-0106, DEC-0111, DEC-0117, DEC-0118, DEC-0126, DEC-0127, DEC-0128, DEC-0129, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0139, DEC-0141, DEC-0143, DEC-0159, DEC-0167, DEC-0168, DEC-0171, DEC-0178, DEC-0180, DEC-0184, DEC-0186, DEC-0189, DEC-0196, DEC-0197, DEC-0198, DEC-0199, DEC-0200, DEC-0201, DEC-0202, DEC-0208, DEC-0211, DEC-0212, DEC-0259, DEC-0334, DEC-0335, DEC-0336, DEC-0337, DEC-0342, DEC-0344, DEC-0347]
sources: [DEC-0008, DEC-0009, DEC-0011, DEC-0013, DEC-0022, DEC-0024, DEC-0030, DEC-0033, DEC-0035, DEC-0042, DEC-0045, DEC-0055, DEC-0058, DEC-0059, DEC-0060, DEC-0065, DEC-0089, DEC-0091, DEC-0096, DEC-0099, DEC-0100, DEC-0101, DEC-0102, DEC-0103, DEC-0104, DEC-0106, DEC-0111, DEC-0117, DEC-0126, DEC-0127, DEC-0128, DEC-0129, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0139, DEC-0141, DEC-0143, DEC-0159, DEC-0167, DEC-0168, DEC-0171, DEC-0178, DEC-0180, DEC-0184, DEC-0186, DEC-0196, DEC-0197, DEC-0198, DEC-0199, DEC-0200, DEC-0201, DEC-0202, DEC-0208, DEC-0211, DEC-0212, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-NODE-2026-08-28/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ctrader-venue-facts.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/spotware-org-inventory.md, docs/decisions/ADR-0019-trading-node.md, docs/architecture/dependencies.yaml, docs/registry/variables.yaml, docs/contracts/]
generated: 2026-08-18
verified: '2026-08-29'
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

QMF V1 has no UI layer. Product UI remains outside the reusable foundation, and the future backtesting library is now specified — it is QMB, a separate application-layer product (one pure library plus the `qmb` CLI) that composes the QMF backend libraries as a consumer, living outside the seven-package roster and outside QMF V1. Its application stack is captured below under [QMB application stack](#qmb-application-stack). (DEC-0009, DEC-0159) The QMX bot-authoring library QML is a second such application-layer product — one uv-installable pure library (`import qml`) that composes `qmf-core`, `qmf-registry`, and `qmf-risk` — its stack captured under [QML application stack](#qml-application-stack). (DEC-0180) The QMX agentic system QMA is a third such application-layer product — the daemon plus the QMA SDK and the wire contract, built ON QMF outside the seven-package roster — its stack captured under [QMA application stack](#qma-application-stack). (DEC-0335) The trading node is a third application-layer product — the Phase-2 QMX composition-root runtime (`qmn`) that composes the QMF roster plus QMB and QML on the Trading VPS, ONE product with modes `paper | live` — living outside the seven-package roster and outside QMF V1; its stack is captured under [Trading node application stack](#trading-node-application-stack). (DEC-0186, DEC-0259)

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

The dependency registry records four independent axes: `kind` (architectural form), `layer` (middleware, backend, data, or external), `roster_role` (public library, public module, internal seam, external system, or application), and `distribution` (the installable package). The seven-package roster below is the distribution unit; `COMP-QMF-DATA-INGEST`, `COMP-QMF-DATA-STORE`, and `COMP-QMF-DATA-BACKUP` are internal seams of `qmf-data` and add no packages. The three application-layer products — QMB, QML, and the trading node (`COMP-QMN`, `roster_role: application`) — sit outside this roster: each is a uv-workspace member built ON QMF, never a roster package, and the trading node is the composition-root runtime that wires the roster plus QMB and QML while nothing imports it. (DEC-0100, DEC-0024, DEC-0186, DEC-0259)

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

The trading node adds a **Linux CI lane pinned to `ubuntu-24.04`**, never `latest`, so `systemd-creds`, the `AF_UNIX` sockets, and the unit-file infrastructure-as-code scan run on the same systemd 255.4 image the Trading VPS uses. The node ships under the permanent battery — Skylos (including its scan of the committed unit files), vulture, the four tier-1 scanners, the coverage floor, and this Linux lane — with nightly mutmut extended to the node's money-path modules (door-path wiring, command mint, equity derivation, drift decomposition, sizing-ladder evaluation, virtual-ledger folds) at the ratified kill floor, run against the branch that carries code. (DEC-0201, DEC-0208)

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

## Trading node application stack

The trading node is the Phase-2 QMX application — the supervised composition-root runtime (`qmn`) that composes the QMF roster plus QMB and QML on the Trading VPS — outside the seven-package roster and outside QMF V1. It is a top-level uv-workspace member with its own SemVer (display-only provenance, never identity), consuming the `qmf-*` packages, `qmb`, and `qml` in lockstep and published to no index (DEC-0186, DEC-0259). It inherits QMF's runtime and quality toolchain unchanged — CPython 3.14 on the tier-1 OSes, uv, `uv_build`, ruff, pyright, pytest, and poethepoet — and **ships no command line**: the operator ruled the node has no command line, so no CLI framework is a node dependency, `qmb` stays the platform's single command-line surface, and a tier-1 `check` asserts `qmn` declares no console-script entry point (DEC-0186, DEC-0211).

Every pin below was verified 2026-08-28 as authoring evidence and is registered at the implementation gate per AD-6 — in `DEPENDENCIES.md` for a Python dependency, or the external-tool register for a tool. Recorded numbers are evidence, never ratified constants; the code owns these pins once it exists (DEC-0201, DEC-0259).

| Name | Version / status | Role | Cites |
|---|---|---|---|
| `just` (external tool) | v1.58.0 (released 2026-08-03) | The operations-toolkit runner: `just node-…` recipes in the root justfile whose bodies live under `qmn/deploy/justfile-recipes/` — DevOps tooling, never a product command line; installed by the day-one bootstrap before any recipe runs | DEC-0186, DEC-0201 |
| Container runtime (external tool) | docker-ce `28.3.3` + compose plugin `2.39.2` | Provisioning installs it for the SEPARATE observability stack alone, with the image registry added to the egress allow-list; the trading node keeps its no-container-requirement and runs and passes with the stack absent | DEC-0201, DEC-0212 |
| Observability stack — Prometheus + Grafana + Loki/Promtail-class (external tools) | `prom/prometheus:v3.5.5`, `grafana/grafana:13.1.4`, `grafana/loki:3.7.7`, `grafana/promtail:3.6.11` (never floating tags) | A separate zero-authority system under `qmn/deploy/observability/` (its own checked-in compose file, its own non-`qmx` account, its own storage budget), the one place containers are permitted; the node itself is a plain systemd service, and this stack is a zero-authority consumer of the node's exported signals | DEC-0200, DEC-0201, DEC-0212 |
| prometheus_client | ==0.26.0 (Apache-2.0) | Metric registry and exposition format for the node's `qmn_` signal families; exposition only | DEC-0200 |
| cryptography | ==50.0.1 (Apache-2.0 OR BSD-3-Clause; released 2026-08-25) | AEAD (`ChaCha20Poly1305` / `AESGCM`) for the KEK store and the CT-14 payload cipher; resolves to the cp311-abi3 wheels on Linux x86-64 and Windows | DEC-0197 |
| rclone (external tool) | v1.75.0 (MIT; released 2026-07-31) | Off-machine backup transfer only (native Backblaze B2 and S3 backends covering R2/Wasabi/MinIO); pinned in the AD-6 register as a tool, never a Python dependency | DEC-0198 |
| Ubuntu LTS x86-64 | 24.04 | The node OS; 26.04 LTS is the planned upgrade at the first maintenance window, and 24.04 is chosen because it matches the pinned CI runner while `ubuntu-26.04` is runner-preview only; on the upgrade chrony becomes the default time daemon, so provisioning verifies rather than installs | DEC-0201, DEC-0199 |
| systemd | 255.4 | `systemd-creds` and `LoadCredentialEncrypted` available (the secret path); `TimeoutStopSec` and `WatchdogSec` are rendered from `drain_window` and `watchdog_interval`, never hand-authored | DEC-0201, DEC-0189 |
| chrony | minimum as packaged by Ubuntu 24.04 (4.5); 4.7 (2025-06-12) and 4.8 current upstream | The sole stamper of QMX-owned event times — four or more sources, RTC and system zone UTC — provisioned by install | DEC-0199 |
| keyring (workstation wizard only) | ==25.7.0 (`WinVaultKeyring`) | Reads the `qmx/*` provisioning secrets and the escrowed CT-14 backup payload key from Windows Credential Manager during provisioning; not a VPS dependency | DEC-0197 |
| Python stdlib sd_notify | 3.14 — the raw `sd_notify` wire protocol over an `AF_UNIX` datagram socket | Owned by the supervisor and door layer; there is NO stdlib `sd_notify` helper and NO `python-systemd` dependency | DEC-0189 |
| click | **NOT TAKEN by the node** | The node ships no command line, so no CLI framework is a node dependency; QMB keeps its own `==8.4.2` pin, unaffected | DEC-0186, DEC-0211 |
| protobuf | stays `qmf-venue`'s `==7.36.0` | The cTrader transport increment keeps protobuf inside `qmf-venue`; the node adds no protobuf dependency of its own and reaches the venue only through the `qmn.venue` import boundary | DEC-0196, DEC-0186 |

No Twisted, no Spotware SDK, no database server, and no OpenTelemetry in V1 — the exportable signals suffice — and **no container for the node**: it runs as a plain systemd service and no Docker requirement stands over it (NFR-10); containers appear only in the separate observability stack the node neither needs nor waits for. (DEC-0200, DEC-0201)

## Model training

None — QMF V1 trains or fine-tunes no model. MIS model work and the agentic ML harness remain outside current QMF V1 scope. (DEC-0089, DEC-0091)

## QMA application stack

The QMX agentic system (QMA) is a third application-layer product — the daemon plus the QMA SDK (QuantMind Agents, the SDK only) plus the wire contract — built ON QMF, outside the seven-package roster and outside QMF V1. It is its own uv workspace on the QMF workspace in lockstep, in the `qma.*` namespace (`qma.core`, `qma.wire`, `qma.daemon`) with no blanket `qmx.` prefix, SemVer display-only provenance never identity (DEC-0334, DEC-0335, DEC-0337). The daemon runs on the operator's workstation by default with workers in Docker on that host, and ships no command line — deployment is driven from the operator's UI and wire commands, and `qmb` stays the platform's single command-line surface (DEC-0336). It consumes `qmf-core` and reads-and-calculates over `qmf-registry`, `qmf-data`, and `qmf-risk` on an enumerated default-deny surface, and imports `qmf-venue` in no package, worker, or plugin (DEC-0347). It inherits QMF's runtime and quality toolchain — CPython 3.14 on the tier-1 OSes, `uv_build`, pyright, pytest, and poethepoet unchanged from the QMF workspace — with `uv` and `ruff` bumped for this workspace. Every pin was verified 2026-08-28 as authoring evidence; recorded numbers are evidence, never ratified constants, and the code owns these pins once it exists (DEC-0334).

| Name | Version / status | Role | Cites |
|---|---|---|---|
| CPython (daemon runtime) | 3.14 (3.14.7 re-verified 2026-08-28) | The single asyncio daemon runtime, inherited from the parent spine | DEC-0334 |
| SQLite (stdlib `sqlite3`, WAL mode) | 3.50.4 — a WAL floor by design, below the 3.51.3 multi-writer WAL-reset fix because AD-6's one-connection sole-writer rule forbids the conditions that bug needs; the floor becomes 3.51.3, or the 3.50.7 backport, the moment sole-writer is relaxed | The daemon store engine behind AD-6's sole-writer, one-connection journal | DEC-0334 |
| JSON-RPC (wire transport spec) | 2.0 | Commands and events over WebSocket on the wire envelope | DEC-0334 |
| websockets (wire transport implementation) | 17.1 | The WebSocket transport for qma-wire | DEC-0334 |
| JSON-Schema validator (message-family validation) | `[UNPINNED — implementation choice at the build gate, stated rather than invented]` | Validates the wire message families | DEC-0334 |
| Model Context Protocol (adapter surface only) | revision 2026-07-28 | The MCP adapter surface behind a ToolAdapter, never a second runtime | DEC-0334 |
| uv (workspace + lockfile) | 0.12.7 (bumped from the parent's 0.12.5, re-verified 2026-08-28) | The QMA uv workspace and lockfile | DEC-0334 |
| ruff | 0.16.5 (bumped from the parent's 0.16.3, re-verified 2026-08-28) | Format and lint | DEC-0334 |
| pyright (strict) | 1.1.411 (inherited, re-verified 2026-08-28) | Strict type checking | DEC-0334 |
| pytest | 9.1.1 (inherited, re-verified 2026-08-28) | Test runner | DEC-0334 |
| poethepoet | 0.48.0 (inherited, re-verified 2026-08-28) | Task runner | DEC-0334 |
| duckdb (rebuildable fold views only) | 1.5.5 (inherited, re-verified 2026-08-28) | Rebuildable analytic fold views only; engine major pinned per release | DEC-0334 |
| Docker Engine (default worker isolation) | 29.7.2 | The default worker isolation on the daemon host | DEC-0334 |
| OpenTelemetry Python SDK (behind the export port) | 1.44.0 | Telemetry export behind the OTel port; telemetry is neither the ledger nor the journal | DEC-0334 |
| OpenCodex (first ModelDeployment implementation) | 2.34.0 published; 2.31.0 installed locally | The first `ModelDeployment` behind the Deployment contract, not behind the Credential Broker | DEC-0334, DEC-0344 |
| Hindsight (deferred first memory backend) | v0.9.2 — deferred | The deferred first `MemoryProvider` backend, arriving behind a testable eval | DEC-0334, DEC-0342 |
| pgvector (arrives only with the deferred memory provider) | 0.8.6 — deferred | Arrives only with the deferred memory backend | DEC-0334, DEC-0342 |

The JSON-Schema validator is deliberately `[UNPINNED]` — the implementation choice is made at the build gate rather than invented here. Hindsight and pgvector are deferred and arrive only with the deferred external memory provider behind its eval (GAP-0072). OpenCodex sits behind the `ModelDeployment` contract with `auth_mode: none` and a mandatory loopback bind, and its own provider credentials stay outside QMA's namespace (DEC-0344). QMA pins no database server: the daemon's stores are SQLite, DuckDB fold views, and append-only journals behind daemon-owned contracts, and the no-database-server rule binds QMA's own stores while never reaching inside a provider's storage behind a QMA-owned port (DEC-0342).

## Related

Layers, containers, and external systems: `docs/architecture/overview.md`. Component graph: `docs/architecture/dependencies.yaml`. Values: `docs/registry/variables.yaml`. Interface schemas: `docs/contracts/`. Ratified spine: `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md`. Trading node component spec: `docs/components/trading-node.md`. Trading node decision: `docs/decisions/ADR-0019-trading-node.md`. Trading node spine: `_bmad-output/planning-artifacts/architecture/architecture-NODE-2026-08-28/ARCHITECTURE-SPINE.md`.
