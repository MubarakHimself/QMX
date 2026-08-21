---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-QMX-2026-08-21/prd.md
  - _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/architecture/architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md
  - docs/ (ratified corpus — contracts CT-01..34, components, ADRs, constitution L1..L39, glossary, golden scenarios, registry)
  - _docwork/feature_inventory.yaml (FEAT-0001..0030)
  - docs/architecture/dependencies.yaml
  - _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/research-backtesting/specs/ (13 QMB intake dossiers)
---

# QMX - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for QMX V1
(Phase 1: QMF + QMB + QML), decomposing the requirements from the QMX
Platform PRD (final, 2026-08-21) and the three ratified architecture spines
into implementable stories for the factory lanes.

PRD rule carried forward: each FR's cited artifact is the epic boundary and
the source of its acceptance criteria; where an FR cites a `spec-*` intake
dossier, that dossier is one epic. FR granularity is deliberately coarser
than epic granularity — never size a lane by counting FRs.

## Requirements Inventory

### Functional Requirements

**A. Domain foundation (qmf-core)**

- FR-001: All money, price, and quantity values are exact scaled integers; binary floats are banned on the money path and treated as a taint. (CT-01; ADR-0013)
- FR-002: All timestamps are int64 UTC nanoseconds with versioned trading calendars; nothing below the composition root reads the system clock — time is injected. (CT-02; ADR-0013)
- FR-003: Instrument identity is an opaque, never-parsed `(venue, symbol)` pair. (CT-03)
- FR-004: Every public operation returns value-or-refusal using the seven typed refusal categories; refusals are returned, never raised. (CT-04; ADR-0013)
- FR-005: Every governed artifact carries a deterministic `fp1:sha256` fingerprint; identity rides two version ladders; results are labeled with their `world`, and `world=simulated` is reserved-unusable in V1. (CT-05; AD-spine)

**B. Identity, lineage, and promotion (qmf-registry)**

- FR-006: Per-kind registration records are keyed on fingerprint, giving deduplication by construction. (CT-06)
- FR-007: Provenance is captured as append-only typed lineage edges that are never rewritten. (CT-07)
- FR-008: The registry persists through qmf-data only — no database server; registry→data is the single ratified inter-library dependency edge. (CT-09; L30)
- FR-009: The only path to live money is a human-signed promotion occurrence attesting the record's fingerprint, with a mandatory plain-words summary as an identity field. (ADR-0015; SCN-0007; L17)

**C. Evidence and data (qmf-data and its internal seams; sources)**

- FR-010: Market and reference data lands as bitemporal source observations; corrections append under revision keys and never overwrite. (CT-10; SCN-0002)
- FR-011: The append-only evidence store partitions into seven room-roles per world; cross-world reads are refused; raw evidence is retained forever. (CT-11; L18)
- FR-012: Research access enforces the 12-month no-peek seal and fingerprinted train/validation/holdout splits; the sealed holdout is excluded from default access at every boundary. (CT-11, CT-12; SCN-0003; L19)
- FR-013: Durable journals carry the seven event types in per-writer gapless streams, with entity projections (logbooks) derived at read time. (CT-13)
- FR-014: Nightly encrypted off-machine backup with first-class restore and verify primitives; recoverability claims come only from verify. (CT-14, CT-26; SCN-0004; L18)
- FR-015: External-source intake is idempotent through the CT-15 adapter seam. (CT-15)
- FR-016: Persistence rides a dependency-free store seam over swappable local engines; no DB server anywhere in V1. (qmf-data-store)
- FR-017: Dukascopy is the first historical tick source (download-once; personal-use licensing honored — no redistributed corpus). (dukascopy; QMB data-mgmt spec)
- FR-018: A news-calendar feed is ingested as a governed source powering pair-scoped news windows; every import is journaled, and a failed refresh degrades visibly to the ratified fail-closed block. (calendar-feed; SCN-0008)

**D. Analytics (qmf-indicators, qmf-structure; qmf-calendar-forex off-roster)**

- FR-019: Indicators run in two modes — batch and streaming — with guaranteed equivalence, as-of-only alignment, and TA-Lib as canonical arithmetic. (CT-16; ADR-0006)
- FR-020: Market structure is expressed as causal, append-only, look-ahead-safe chart-object families. (CT-17)
- FR-021: A forex market-hours calendar ships as the first CT-02 calendar provider. (qmf-calendar-forex)

**E. Venue boundary (qmf-venue; cTrader adapter)**

- FR-022: Venue capabilities are discovered through the two-artifact verify-or-refuse mechanism before any command is accepted. (CT-18)
- FR-023: Venue commands come in exactly five kinds under the four-outcome law: timeout is not rejection, UNKNOWN is a state not an error, and an UNKNOWN blocks its `(venue, account)` command stream until explicit reconciliation. (CT-19; SCN-0005; L35)
- FR-024: Venue events are recorded before they are interpreted; reconciliation gates the command pipe only — market data keeps flowing. (CT-20)
- FR-025: Credentials are handled as secret references, never values, and never leave the connection manager. (CT-21; L34)
- FR-026: cTrader Open API is the first venue adapter behind the venue-neutral port; the platform stays venue-blind above the port. (ctrader; ADR-0007)

**F. Risk and governance (qmf-risk)**

- FR-027: Books are chartered gatekeepers: every bot trade intent passes a Book's charter doors; the BMS (one per account, serving many Books) accounts and constrains but never trades, sizes, or reaches inside a Book. (CT-22, CT-27; ADR-0008)
- FR-028: The Book owns sizing: `requested_r` is Book-resolved; an admitted entry requires a declared full-loss price or admission refuses; admission is three technical layers; R is one relationship with three typed faces, frozen at admission. (CT-23; ADR-0010)
- FR-029: Paper is a Book-level standing evidence state entered by a dated binding-epoch change. (CT-24; ADR-0009; SCN-0006)
- FR-030: Risk journals project Book/BMS state at read time. (CT-25)
- FR-031: A bot binds exactly one Book; bindings are dated epochs. (CT-28)
- FR-032: Exits are Book-owned and risk-monotonic; bots may only propose risk-reducing exits; every virtual close mints exactly one exit record. (CT-29; L39)
- FR-033: Controls obey the exit-preservation invariant — no control ever blocks a risk-reducing act; kill-switch (global) and kill-line (per-Book floor) are distinct; same-tick actions arbitrate by BMS rank on one stream; news windows block entries fail-closed by instrument scope. (CT-30, CT-31; SCN-0008, SCN-0010; L39)
- FR-034: Performance measurement publishes and never acts; no composite score gates money; benching is a read-time fold. (CT-32; SCN-0011)
- FR-035: The numeraire is USD-only in V1; every risk/sizing/window/SQS value is a UI-editable configurable with no spine constant, and a blank value blocks live money while allowing registration and non-live binding. (variables registry; L38)

**G. Experimentation and backtesting (QMB)**

- FR-036: One event-slice run loop serves backtest, replay, and live — never forked; each run consumes exactly one resolved, fingerprinted run config; the config fingerprint is the run id and the ledger key; `world` derives from data provenance, never from a flag. (QMB spine B-1..15; SCN-0012)
- FR-037: Replay backtests support warm-up, deterministic reproduction, intra-bar fill fidelity, and cancel/observe while running. (spec-backtest-loop)
- FR-038: Multi-symbol / multi-timeframe permutation sweeps run the Cartesian space with a pre-flight run count, one labeled run per combo, and cross-run ranking. (spec-multi-routes)
- FR-039: Parameter-optimization Studies offer a typed search space, objective plus constraints, train/test split discipline with fingerprinted split manifests, a TPE-class default sampler, resume, cost estimation, and an anti-overfit sensitivity report. Locked-validation third split and grid/Euler samplers deferred out of V1. (spec-optimization intake; QMB spine)
- FR-040: A robustness toolkit ships the ratified B-14 ladder: backtest, optimize, Monte Carlo (trade-shuffle and candle-perturbation), the pre-build rule-significance gate, and walk-forward. Threshold values and pass batteries stay deferred to the GAP-0048/0049 sittings. (QMB spine; spec-mc-significance intake)
- FR-041: Synthetic data generation is claim-class labeled (infra-stress / robustness / logic-smoke) and never validates edge. (spec-synthetic-data; SCN-0009; L20)
- FR-042: Data management covers download, verify, gap-check, and catalog by `(venue, symbol, window, side)`, calendar-aware, behind a ship-no-corpus licensing gate. (spec-data-mgmt)
- FR-043: Every run emits one canonical machine-readable result artifact (it IS CT-32) plus chart series as data, never images; the metric set includes QMX-native suppression/veto accounting; no composite score. (spec-reports; CT-32)
- FR-044: Fill/slippage/fee modeling carries fidelity labels; all fills are `optimistic`-tainted and no verdict-bearing backtest ships until GAP-0048 closes. (spec-fill-fees)
- FR-045: Runs execute process-per-run under a governed concurrency cap with backpressure and per-run isolation. (spec-concurrency)
- FR-046: QMB is reachable through thin doors: the `qmb` CLI (the platform's single command-line surface), the Python API and notebooks, and an optional MCP door that is never required; plain Python remains first-class. (spec-cli-config; DEC-0159, DEC-0185)

**H. Bot authoring (QML)**

- FR-047: A governed bot is exactly two artifacts: a CT-33 declaration plus plain-Python logic; plain-Python bots stay first-class forever — the `.qml` DSL is not revived in V1. (CT-33; QL-spine; ADR-0018)
- FR-048: Conformance is technical-never-performance and is the ticket into governed evidence citation and Book seats — never into tunnel entry. (ADR-0018)
- FR-049: Confluence definitions are authored as CT-34 artifacts. (CT-34)
- FR-050: QML defines the bot runtime protocol that QMB (and later the trading node) hosts. (QL-spine)

### NonFunctional Requirements

- NFR-01 Environment: CPython 3.14; tier-1 OSes Windows 11 x86-64 and Ubuntu LTS x86-64. (ADR-0012)
- NFR-02 Quality gates: ruff + pyright-strict + pytest; coverage floor 80%, 100% branch coverage on CT-01/CT-02 modules; three event-bound gate tiers; two tier-1 static scanners (money-path float scanner, ambient-nondeterminism scanner) make FR-001/FR-002 mechanically enforceable. (ADR-0012)
- NFR-03 Determinism: same inputs produce the same fingerprints and the same results — replay reproducibility is a platform property. (CT-05; B-spine)
- NFR-04 Performance: measure-then-budget, no invented numbers; benchmark at the 10/100/200 marks against the ~40-bot reference workload; qmf-core import under ~1s. (ADR-0014)
- NFR-05 Security: secrets as references only, tier-1 scan gate, encrypted off-machine backup; credentials never leave the connection manager. (CT-21, CT-14; L34)
- NFR-06 Durability & compatibility: evidence append-only, retained forever; per-contract integer format versions keep old evidence readable forever. (CT-11; ADR-0012)
- NFR-07 Configurability: `configurable: true` means UI-editable, always; recorded numbers are evidence, not authority; blank risk values block live money. (variables registry; L38)
- NFR-08 Auditability: journals, lineage edges, and memlogged decisions make every state change reconstructable; corrections append. (CT-07, CT-13)
- NFR-09 Concurrency posture: QMF spawns no concurrency; applications own it (QMB's governor is the V1 instance); async only at the venue edge. (ADR-0014)
- NFR-10 Operability & deployability: `uv add` install, no database server, no Docker for QMB; one-person deploy/monitor/repair from one canonical checkout; monitoring and evaluation built in; external monitoring planes are zero-authority. (operator ruling; DEC-0112, DEC-0041)
- NFR-11 Failure-register discipline: every designed failure mode ships a register entry (class, detection, recovery semantics, degraded state, notification tier, product-user affordance) written for someone who was not in the design room. (PRD §8)

### Additional Requirements

Extracted from the three ratified architecture spines and the docs
implementation surface; deduplicated. Each is binding on story authoring.

**Workspace and packaging (the greenfield scaffold)**

- AR-01: The repo is one uv workspace of seven installable packages (qmf-core, qmf-registry, qmf-data, qmf-indicators, qmf-structure, qmf-venue, qmf-risk) importing under the `qmf.*` PEP 420 implicit namespace; no distribution ever contains a `qmf/__init__.py`. (AD-2; DEC-0100)
- AR-02: Top-level split is `packages/` (roster) and `extensions/` (off-roster); the first extension is `qmf-calendar-forex` with tzdata pinned, on its own SemVer ladder. (Structural Seed; AD-2)
- AR-03: Every package uses src/ layout (`src/qmf/<name>/`), declares every dependency (siblings included) in its own pyproject.toml, builds with uv_build, and shares one committed uv.lock. (AD-2; DEC-0100)
- AR-04: CPython 3.14 pinned across every package, CI job, and factory sandbox; source pure-Python and OS-neutral. (AD-1; DEC-0099)
- AR-05: qmf-core takes zero outside dependencies (stdlib only); numpy/pandas/pyarrow (2.5.2/3.0.5/25.0.1) permitted only in outer packages. (AD-6; DEC-0104)
- AR-06: Default-deny dependency direction: qmf-core depends on nothing; every other package may depend only on qmf-core; the sole ratified inter-library edge is qmf-registry→qmf-data; nothing imports qmf-venue or qmf-risk; any further edge is a spine amendment. (AD-6; L30; DEC-0120)
- AR-07: A workspace-root DEPENDENCIES.md register lists every dependency (name, licence, why); MIT/BSD/Apache/PSF allowed; GPL/AGPL, strategy-family, and platform-imposing dependencies prohibited; LGPL only unmodified and separately installed. (AD-6; DEC-0104)
- AR-08: Shared nouns (Venue, Account, Instrument, WriterId, Bar, Tick/Quote, BarSpec, Position, Order) are defined only in qmf-core with records owned by qmf-registry; never defined in an edge module. (AD-2)
- AR-09: The seven roster packages version in SemVer lockstep (0.x until the V1 blueprint ships); deprecated symbols keep working under a warning for one release. (AD-5; DEC-0103)
- AR-10: QMB ships as one wheel (pure library + `qmb` CLI; click 8.4.2, optuna 4.9.0) and QML as one wheel (import `qml`, no new runtime dependency) — both outside the roster, consuming qmf-* in lockstep, installed via `uv add`. (B-13; QL-1; DEC-0167/0180)

**Toolchain and code conventions**

- AR-11: One canonical toolchain: ruff 0.16.3, pyright 1.1.411 strict workspace-wide, pytest 9.x, poethepoet 0.48.0, via `poe fmt | lint | types | test | check` (+ `check-integration`, `check-release`), byte-identical on every machine. (AD-3/AD-4; DEC-0101/0102)
- AR-12: Public value types are frozen dataclasses; public seams are typing.Protocol. (AD-3)
- AR-13: Every public boundary returns value-or-typed-refusal (category, machine-readable context, retryability); exceptions are reserved for programmer error; value construction pairs an unchecked constructor with a validating try_create factory. (AD-11)
- AR-14: The canonical serializer and fp1 fingerprint function live only in qmf-core; no other package computes a fingerprint except by calling it; format `fp1:sha256:<hex>` over sorted-key NFC UTF-8 JSON with integer-only identity content. (AD-10)
- AR-15: Every stored timestamp is int64 UTC-ns; every Money/Price/Quantity is a scaled integer at a declared scale; float crossings pass named conversion boundaries with declared rounding modes. (AD-7/8/22)
- AR-16: All clock access is injected through the core Clock protocol at the composition root; monotonic readings are type-separated from wall Instants. (AD-8)
- AR-17: QMF never spawns threads or background work; async APIs exist only at the venue network edge; stateful components follow one-writer-per-stream with a held WriterId. (AD-15; DEC-0113)

**Quality gates and testing**

- AR-18: Three factory-event-bound tiers: Tier 1 `poe check` on every work unit; Tier 2 `poe check-integration` (adds integration + contract tests, each package in an isolated environment so an undeclared import fails) on landing to integration; Tier 3 `poe check-release` (adds build-all + clean-install smoke on both tier-1 OSes) on ship. (AD-4; DEC-0102)
- AR-19: Each CT-* contract ships an executable contract test owned by the contract's owning package, run by producer and every consumer at Tier 2. (AD-4)
- AR-20: Coverage per package, 80% floor at Tier 1; 100% branch coverage on CT-01/CT-02 modules. (AD-3)
- AR-21: Every package ships executable tests AND reference-usage examples as tier-1 artifacts. (AD-3; L27)
- AR-22: Every component ships a benchmark harness (speed + peak memory at a package-native load ladder) with the same status as unit tests; baselines are fingerprinted per (OS, CPU-class); a regression beyond recorded threshold fails the Tier-2 gate. (AD-13; DEC-0111)
- AR-23: Quality commands are host-neutral; the factory runs the gates locally until a GitHub remote exists (Ubuntu tier-1 stays untested until then). (AD-1/AD-4)
- AR-24: A secret-scan gate runs inside `poe check` at Tier 1. (AD-26)

**Versioning and compatibility**

- AR-25: Every serialized contract stamps its own integer format version; meanings never mutate; an incompatible change mints the next version plus a migration note; all history stays readable forever. (AD-5; L15)
- AR-26: Package SemVer is display-only provenance and never enters identity. (AD-10; B-13; QL-1)
- AR-27: tzdata is pinned only in calendar extensions; TZPATH is forced to the pin; the resolved tzdata version participates in fingerprints; a pin change is at minimum a minor bump. (DEC-0106)
- AR-28: The QML increment carries CT-22 and CT-23 to format-version 2 (owned by qmf-risk) with migration notes; pre-mint format-1 artifacts stay readable. (QML parent-contract mints; DEC-0181/0182)
- AR-29: A future optuna major bump changes the default sampler and is a contract-versioning event, never a transparent update. (QMB Stack)

**Data and persistence setup**

- AR-30: Four engines behind QMF-owned contracts with stdlib-typed boundary signatures, no database server: Parquet (evidence-bearing), DuckDB 1.5.5 (rebuildable views only), SQLite (transactional metadata), JSONL (append streams). (AD-19; DEC-0117)
- AR-31: JSONL journals and lineage edges: one fp1-canonical object per line, LF-terminated, append-with-fsync, size rotation with monotonic ordinal, local rebuildable indexes. (AD-16/21)
- AR-32: Every migration runs preflight → backup → dry-run → migrate → verify with a documented restore path; never in-place mutation of the only copy. (AD-20)
- AR-33: Room-roles instantiate per world; cross-world reads are policy rejections; non-live worlds never write the live namespace; `world=simulated` writes refuse until GAP-0048. (AD-12; DEC-0110)
- AR-34: Nightly encrypted off-machine backup to object storage with automated sample-restore tests and periodic full-restore rehearsal; QMF owns the primitives, applications own schedule/execution. (DEC-0118)

**Monitoring and operability**

- AR-35: Structured logs carry a `correlation_id` propagated across every package boundary (excluded from fp1 identity); every resource-owning component exposes a no-argument health() returning a typed report; refusals always carry context and are never swallowed. (AD-14; DEC-0112)
- AR-36: Operator-facing log text renders UTC ISO-8601 with explicit Z (display-only); evidence stores int64 ns + writer + sequence; emitted signals are exportable to Prometheus-class stacks, which stay zero-authority. (AD-14; DEC-0112/0041)

**Security**

- AR-37: qmf-core ships typed SecretRef and SecretValue; SecretValue never renders its value in repr/str/serialization/logging; secret values live only in the connection manager, fed by a core-defined SecretStore port (read + atomic replace) injected at the composition root; secrets never appear in repos, config artifacts, .env files, CLI args, journals, evidence, fingerprints, or logs. (AD-26; L34)
- AR-38: On credential rotation the new secret is stored via atomic replace before the old is discarded. (AD-26)
- AR-39: Only a human promotes an artifact into the live zone; V1 signing is the operator's recorded approval attesting the record's fp1. (L17)
- AR-40: Factory-sandbox artifacts carry `provenance=sandbox`, which blocks merge into the operator store. (AD-10)
- AR-41: Sealed and governed evidence never leaves controlled rooms; portable contexts receive only unsealed, split-governed exports. (B-9)

**Venue integration**

- AR-42: The venue boundary is one neutral port with four contracts (CT-18..CT-21) on qmf-core nouns, implemented by per-venue adapters wired at the composition root; cTrader is adapter #1; the platform stays venue-blind above the port; never MQL. (AD-28; L21/22)
- AR-43: The Spotware venue proto is compiled in-house and pinned at integer release tag 91; the protobuf runtime is a dependency of qmf-venue only; the OpenApiPy SDK is reference-only (its Twisted reactor violates the platform-imposing ban). (AD-28; DEC-0141)
- AR-44: Exactly five typed venue command kinds — place_order, cancel_order, close_position, close_all, amend_protection — on core nouns with no free-form payload; kinds are addable-never-redefined. (AD-27/34)
- AR-45: First-connection verification is verify-or-refuse throughout; any measured-at-connection capability is an unavailable dependency until its per-(VenueId, account) venue-observation profile exists. (AD-28)
- AR-46: The cTrader adapter honors the ratified venue facts (per-field Unix-ms UTC, receive-time recording, 50/5 req/s per connection, 10s heartbeat bound, ~30-day access token with never-expiring refresh token, 1/100000 wire price scale, one-week tick-history span cap); the 17:00-New-York daily boundary, BID-derived trendbars, and broker identity are per-broker/deployment configuration, never hardcoded. (DEC-0135/0139/0141)
- AR-47: Recording precedes interpretation: every inbound venue event is stored verbatim and journaled before any state evaluation; a journal or multi-room write completes as one ordered/atomic unit or blocks the command stream. (AD-27/28)
- AR-48: Where the venue client-id field cannot carry the command fingerprint, a durable command-id-binding record persists through the sink before venue submission. (AD-27)
- AR-49: TA-Lib (C 0.7.1 + Python wrapper 0.7.1) is the canonical arithmetic reference, pinned as lockfile-resolved artifacts (distribution filename + hash) with a reference-configuration record asserted at import; where TA-Lib implements a formula, wrapping it is mandatory and re-implementing it is a contract defect. (AD-23; DEC-0127)

**QMB-specific**

- AR-50: The orchestrator owns all impurity: process-per-run via stdlib process management, isolated per-run output directories, a governor bounding parallelism by min(cpu, memory) budgets with enqueue-when-full; no Ray, no required Docker, no daemon; the Optuna adapter runs n_jobs=1. (B-5)
- AR-51: Every run is cancellable via a cancel token with declared per-run time/memory limits (breach = typed `aborted` refusal); the orchestrator appends exactly one ledger line per run — completed or aborted, never zero, never two. (B-4/5)
- AR-52: The resolved run-config is a single JSON artifact, JSON-Schema-validated, stamped with its own format version, written into the run's output directory; its fingerprint is the run id root and the ledger key; the run directory is named by the run id. (B-3)
- AR-53: The ledger is JSONL append-only fragment files written only by the orchestrator, WriterId-scoped per (machine, role, worker-slot); reads are a world-and-role-scoped merge view. (B-4)
- AR-54: Market data is downloaded once (Dukascopy primary) into the QMF immutable raw archive under the user's own provider relationship; runs never fetch from providers; QMB data commands are thin fronts over CT-10/CT-15; every window records provenance plus a licence tag; QMB ships no market data. (B-11)
- AR-55: Registry state reaches machines as immutable fingerprinted as-of sets via a passive file-sync hub; ONE library-owned registry-read port serves the config compiler and door autocomplete — no door-side cache. (B-15)
- AR-56: Execution binds separate pinned ports per run-config — fill, slippage, cost — and financing is a scheduled position-level cash event at the accounting rollover; fill ports execute CT-23 authorized intents, never bot-sized orders; an AD-40 full-loss price is required before any open. (B-6; B-3)
- AR-57: The event-slice run loop is one loop with a six-sub-phase order that is identity-bearing and pinned; higher-BarSpec bars derive from the finest declared base stream, emitted only on completed boundaries; a forming bar is never visible or actionable. (B-2)
- AR-58: Doors render refusals per transport (CLI: nonzero exit + machine-readable stderr JSON; Python: refusal union verbatim; MCP: error.data verbatim); door parity and golden-slice determinism are enforced by Tier-2 contract tests; re-running a run id under its resolved config must reproduce the CT-32 fingerprint or refuse. (B-1/2/10; AD-11)
- AR-59: The CT-32 result artifact carries the full AD-12 label set plus resolved-config fingerprint, registry_as_of, data/split fingerprints, world, evidence class, fidelity identity, and RNG provenance; all human-facing rendering is a pure downstream function of it. (B-10/13)

**QML-specific**

- AR-60: qml is pure per AD-15 (no threads, I/O, or process spawning); it imports only qmf-core, qmf-registry, and qmf-risk types — never qmf-venue; permitted-intent identifiers ride as opaque core-typed values. (QL-1/3)
- AR-61: The host composition root owns the WriterId and gapless per-(writer, kind) sequences, mints the registry records, and handles every RecordSink refusal; qml returns fingerprintable content, never stamped records; the writer unit is (machine, authoring role, kind). (QL-1)
- AR-62: Bot identity is semantic declaration content + contract format version + at-birth refs (AD-16 header excluded from fp1); versioning is the AD-30 branches-from graph with a dated current pointer; a changed default, confluence leg, footprint entry, or logic artifact mints a new Bot; re-binding, seat assignment, and paper flips never mint. (QL-3)
- AR-63: The logic artifact's identity basis is distribution identity + version + a normalized reproducible source-manifest fingerprint; built-artifact bytes are never identity; identical source built in two sandboxes yields one Bot fp1. (QL-2)
- AR-64: Conformance Layer 1 is a machine declaration linter at registration (schema completeness, unit-kinded parameters, resolvable references, footprint transitive-union completeness, producer-template completeness, permitted exit kinds within CT-23); Layer 2 splits a QML-owned pure surface (denial set, AST/import scan, determinism harness, golden-slice generator, verdict function) from a host-owned sandbox runner; the Bot kind mints only after BOTH layers pass, else `policy rejection`. (QL-8)
- AR-65: A conformant bot never sizes, never touches venue commands, never reads a clock, performs no I/O/network/undeclared randomness (stochastic bots declare a seed parameter); hosts inject only declared-footprint evidence; no Book module is ever injected into bot logic; entry proposals carry an advisory stop, and the declared full-loss price is derived Book-side at the door. (QL-7/4)
- AR-66: The prediction linter runs statically on demand and at seat time against the CT-28 binding context: footprint vs Book requirements, exit-kind subset, family resolves an exit_policy entry, stream set within the binding's CT-18 capabilities. (QL-8)
- AR-67: Bot state snapshot/restore is a versioned contract scoped to (OS, logic identity + source-manifest fingerprint, protocol format version, arithmetic-reference build); restoring across any differing component is an `unavailable dependency` refusal; a restored-state fingerprint enters downstream labels. (QL-7)
- AR-68: V1 sandbox enforcement is static AST/import scanning + capability starvation + host process isolation only; hardened OS-level confinement is deferred and V1 must not wait on it. (QL-8)
- AR-69: Governed seats execute the canonical assignment only; non-default assignments exist solely as B-3 run-spec overrides in experimentation runs; promoting a tuned assignment mints a new Bot version. (QL-3)

**Starter template note (Epic 1 Story 1).** There is no external starter
template; the spine prescribes the exact greenfield scaffold (AR-01..AR-11):
uv workspace, `packages/` + `extensions/`, seven roster packages in src/
layout under the `qmf.*` namespace, uv_build + one uv.lock, DEPENDENCIES.md,
the poe task surface, and `qmf-calendar-forex` as the first extension. QMB
(`qmb/` with runloop/, config/, registryread/, execution/, data/, optimize/,
robustness/, results/, ledger/, orchestrator/, doors/{cli,api,mcp}) and QML
(`qml/` with declaration/, families/, footprint/, protocol/, conformance/,
examples/, tests/ — conformance/ pure, one complete example bot) carry their
own prescribed scaffolds inside their own epics.

**Sequencing constraints (bind epic ordering)**

- SC-01: qmf-core builds first — every package depends inward on it; the sole further inter-library edge is registry→data. (Dependency direction; L30)
- SC-02: The cTrader capability probe (CT-18 verify-or-refuse) belongs among the earliest factory work units — venue feasibility cannot be designed on paper and can invalidate upstream assumptions. (PRD §2, operator-ratified sequencing note)
- SC-03: FEAT-0029 (QMB) is blocked by FEAT-0027 (risk contracts), FEAT-0015 (split-governed release), FEAT-0016 (journal adapter), FEAT-0020 (indicators), FEAT-0022 (structure); FEAT-0030 (QML) is blocked by FEAT-0005, FEAT-0007, FEAT-0027 only. Both are size multi-pass. (feature_inventory)
- SC-04: QML builds before the trading node and may build alongside QMB; QMB exercises plain-Python bots from day one and conformant bots only once QML lands; the plain-Python path must exist before conformance. (QL-10; QL-1/8)
- SC-05: The CT-22/CT-23 format-version-2 mints precede the QML admission-bar, exit_policy catch-all, footprint_requirements, and advisory-stop features that depend on them. (QML parent-contract mints)
- SC-06: GAP-0048 gates: `world=simulated` refuses; all fills carry `optimistic` taint; no verdict-bearing backtest and no split-budget spend until the fidelity taxonomy is ruled; look-ahead prevention (forming-bar rules, split-manifest enforcement, declared stream sets) ships regardless. (B-2/6/7; Deferred)
- SC-07: Thresholds are deferred, interfaces are not: the registration gate (CT-08), SR*/search-quality thresholds, and robustness pass batteries wait for GAP-0048/0049; the interface build must not block on them. (QMB/QML Deferred)
- SC-08: The `qmb` CLI is the V1 product face and ships first; the MCP door is post-CLI-v1. (B-1)
- SC-09: Venue wiring order is fixed: capability declaration at construction; the per-(VenueId, account) venue-observation profile must exist before the first command and any evidence-bearing decode. (AD-28)
- SC-10: Warm-up runs in-loop before the trading interval with trading locked; the result label's evidence range is the trading interval only. (B-2)
- SC-11: A sweep resolves exactly one registry as-of at batch admission, frozen for every trial; TPE-class search proceeds in deterministic generations (propose → run → barrier → condition). (B-15/8)
- SC-12: Book/BMS admission is strictly three ordered layers: machine linters at registration → technical shakedown on demo/paper binding → single operator signature. (AD-32)

### UX Design Requirements

None. V1 has no UI surface: the terminal is Phase 3, the Simulator UI is
deferred (ADR-0011), and QMB's chart output is data, never rendering
(FR-043). No UX design contract exists, correctly.

### FR Coverage Map

- FR-001: Epic 1 — exact scaled-integer money/price/quantity (CT-01)
- FR-002: Epic 1 — UTC-ns time, versioned calendars, injected Clock (CT-02)
- FR-003: Epic 1 — opaque (venue, symbol) instrument identity (CT-03)
- FR-004: Epic 1 — typed refusal envelope (CT-04)
- FR-005: Epic 1 — fp1 fingerprints, version ladders, worlds (CT-05)
- FR-006: Epic 2 — fingerprint-keyed registration records (CT-06)
- FR-007: Epic 2 — append-only lineage edges (CT-07)
- FR-008: Epic 2 — registry persists through qmf-data only (CT-09)
- FR-009: Epic 2 — human-signed promotion occurrence (ADR-0015)
- FR-010: Epic 3 — bitemporal source observations (CT-10)
- FR-011: Epic 3 — room-roles per world, cross-world refusal (CT-11)
- FR-012: Epic 3 — 12-month seal, fingerprinted splits (CT-12)
- FR-013: Epic 3 — gapless per-writer journals, read-time projections (CT-13)
- FR-014: Epic 5 — encrypted off-machine backup + verify (CT-14/26)
- FR-015: Epic 6 — idempotent CT-15 intake seam
- FR-016: Epic 3 — dependency-free store seam, no DB server
- FR-017: Epic 6 — Dukascopy first historical source
- FR-018: Epic 6 — news-calendar feed, fail-closed windows
- FR-019: Epic 7 — batch/streaming indicators, TA-Lib canonical (CT-16)
- FR-020: Epic 9 — causal look-ahead-safe structure (CT-17)
- FR-021: Epic 4 — forex market-hours calendar extension
- FR-022: Epic 8 — verify-or-refuse capability discovery (CT-18)
- FR-023: Epic 8 — five commands, four-outcome law (CT-19)
- FR-024: Epic 8 — record-before-interpret, reconciliation (CT-20)
- FR-025: Epic 8 — secret references, connection manager (CT-21)
- FR-026: Epic 8 — cTrader adapter behind neutral port
- FR-027: Epic 10 — Books as gatekeepers, BMS accounts/constrains (CT-22/27)
- FR-028: Epic 10 — Book-owned sizing, full-loss price, R faces (CT-23)
- FR-029: Epic 10 — paper as dated binding-epoch state (CT-24)
- FR-030: Epic 10 — read-time risk journal projections (CT-25)
- FR-031: Epic 10 — one-Book bindings as dated epochs (CT-28)
- FR-032: Epic 10 — Book-owned risk-monotonic exits (CT-29)
- FR-033: Epic 10 — exit-preservation controls, kill-switch/kill-line (CT-30/31)
- FR-034: Epic 10 — publish-never-act performance, benching fold (CT-32)
- FR-035: Epic 10 — USD numeraire, UI-editable configurables (L38)
- FR-036: Epics 13 & 14 — resolved run-config + the one event-slice loop
- FR-037: Epic 14 — replay backtests: warm-up, determinism, cancel/observe
- FR-038: Epic 20 — multi-route permutation sweeps
- FR-039: Epic 21 — optimization Studies
- FR-040: Epic 22 — robustness ladder (interfaces; thresholds deferred)
- FR-041: Epic 23 — claim-class-labeled synthetic data
- FR-042: Epic 18 — data management commands, licensing gate
- FR-043: Epic 19 — canonical CT-32 result artifact, charts as data
- FR-044: Epic 17 — fidelity-labeled fill/slippage/fee/financing
- FR-045: Epic 15 — process-per-run governor and ledger
- FR-046: Epic 16 — qmb CLI, Python API, optional MCP door
- FR-047: Epic 11 — CT-33 declaration + plain-Python logic
- FR-048: Epic 12 — technical-never-performance conformance
- FR-049: Epic 11 — CT-34 confluence artifacts
- FR-050: Epic 12 — bot runtime protocol QMB hosts

## Epic List

Weight tags route factory lanes: **H** heavy (Claude), **M** medium (Codex
band), **L** light (Grok). Waves state the earliest start; epics in the same
wave run in parallel worktrees (disjoint file sets by design).

### Epic 1: qmf-core — exact domain foundation (Wave 1, H)
Everything later builds on exact money/time/instrument values, typed refusals, and deterministic fp1 identity, installable from the scaffolded workspace.
**FRs covered:** FR-001, FR-002, FR-003, FR-004, FR-005
**Notes:** Story 1 is the greenfield workspace scaffold (AR-01..AR-11), including reconciling the workspace-root pyproject.toml with the existing SSSF factory-gate stamp. Runs alone — nothing starts before it.

### Epic 2: qmf-registry — identity, lineage & promotion (Wave 2, H)
Every governed artifact registers once, carries lineage forever, and nothing reaches live money without a human-signed promotion.
**FRs covered:** FR-006, FR-007, FR-008, FR-009
**Notes:** After Epic 1; parallel with Epics 3/4. Its persistence story (CT-09) consumes Epic 3's store-seam story — Epic 3 lands that story first.

### Epic 3: qmf-data — evidence store & journals (Wave 2, H)
Market facts land bitemporally in per-world rooms, journals are gapless, research access is seal-and-split governed.
**FRs covered:** FR-010, FR-011, FR-012, FR-013, FR-016
**Notes:** After Epic 1; parallel with Epic 2. Store-seam story first (unblocks Epic 2's tail).

### Epic 4: qmf-calendar-forex extension (Wave 2, L)
The first CT-02 calendar provider ships as its own extension package.
**FRs covered:** FR-021
**Notes:** After Epic 1; blocks nothing, parallel with everything.

### Epic 5: qmf-data — backup, restore & verify (Wave 3, L)
Nightly encrypted off-machine backup with verify-backed recoverability claims.
**FRs covered:** FR-014
**Notes:** After Epic 3.

### Epic 6: qmf-data — source intake (Wave 3, M)
External data arrives idempotently: CT-15 seam, Dukascopy tick history, news-calendar feed.
**FRs covered:** FR-015, FR-017, FR-018
**Notes:** After Epic 3; parallel with Epics 5/7/8/9.

### Epic 7: qmf-indicators (Wave 3, M)
Batch and streaming indicators with guaranteed equivalence over TA-Lib canonical arithmetic.
**FRs covered:** FR-019
**Notes:** After Epics 1 and 3; parallel within Wave 3.

### Epic 8: qmf-venue port + cTrader adapter (Wave 3, H; Story 1 hoisted to Wave 2)
Commands and events cross one venue-neutral port under the four-outcome law; cTrader is adapter #1.
**FRs covered:** FR-022, FR-023, FR-024, FR-025, FR-026
**Notes:** Story 1 is the cTrader capability probe (SC-02) — runs as early as Epic 1's nouns plus credentials allow; its findings can amend upstream assumptions. Bulk of the epic follows Epic 3 (record-before-interpret needs CT-13 journals).

### Epic 9: qmf-structure (Wave 3, M)
Market structure as causal, append-only, look-ahead-safe chart-object families.
**FRs covered:** FR-020
**Notes:** After Epics 1 and 3; parallel within Wave 3.

### Epic 10: qmf-risk — Books, BMS & governance (Wave 4, H)
Every trade intent passes a Book's charter doors; BMS accounts and constrains; exits are preserved; performance publishes and never acts.
**FRs covered:** FR-027, FR-028, FR-029, FR-030, FR-031, FR-032, FR-033, FR-034, FR-035
**Notes:** After Epic 8's port-contract stories (CT-18/19 shapes), Epic 2, Epic 3.

### Epic 11: QML authoring (Wave 5, H)
Governed bots and confluences are authorable as two-artifact declarations with exact identity and versioning.
**FRs covered:** FR-047, FR-049
**Notes:** After Epics 1, 2, 10. Includes the CT-22/CT-23 format-version-2 mints (SC-05). Parallel with Epic 13.

### Epic 12: QML protocol & conformance (Wave 5, H)
The bot runtime protocol plus the two-layer conformance gate that is the ticket into governed seats.
**FRs covered:** FR-048, FR-050
**Notes:** After Epic 11.

### Epic 13: QMB substrate (Wave 5, H)
One resolved, fingerprinted run-config per run; registry as-of sets through one read port; the QMB package skeleton.
**FRs covered:** FR-036 (config-compiler half)
**Notes:** After Epics 2, 3, 10; parallel with Epic 11.

### Epic 14: QMB run loop & replay backtest (Wave 6, H)
The one never-forked event-slice loop: warm-up in-loop, deterministic reproduction, forming bars never actionable.
**FRs covered:** FR-036 (loop half), FR-037
**Notes:** After Epics 13, 7, 9; consumes CT-23 intents from Epic 10.

### Epic 15: QMB orchestrator, ledger & concurrency (Wave 6, M)
Process-per-run under a governed cap; exactly one ledger line per run.
**FRs covered:** FR-045
**Notes:** After Epic 13; parallel with Epic 14.

### Epic 16: qmb CLI & doors (Wave 6, M)
The platform's single command-line surface plus the Python API door, with enforced parity.
**FRs covered:** FR-046
**Notes:** After Epic 13; parity tests complete after Epic 14. MCP door is post-CLI-v1 (SC-08).

### Epic 17: QMB fill/slippage/fee/financing ports (Wave 7, M)
Fidelity-labeled execution modeling behind separate pinned ports.
**FRs covered:** FR-044
**Notes:** Port interfaces are pinned in Epic 14; implementations run parallel in Wave 7. All fills optimistic-tainted until GAP-0048 (SC-06).

### Epic 18: QMB data management (Wave 7, L)
Download, verify, gap-check, catalog — calendar-aware, behind the licensing gate.
**FRs covered:** FR-042
**Notes:** After Epics 6 and 16.

### Epic 19: QMB reports & result artifacts (Wave 7, M)
Every run emits the canonical CT-32 artifact; charts are data, never images.
**FRs covered:** FR-043
**Notes:** After Epic 14.

### Epic 20: QMB multi-route sweeps (Wave 7, L)
Cartesian permutation sweeps with pre-flight counts and cross-run ranking.
**FRs covered:** FR-038
**Notes:** After Epics 14 and 15.

### Epic 21: QMB optimization studies (Wave 7, M)
Typed search spaces, TPE-class sampling in deterministic generations, anti-overfit reporting.
**FRs covered:** FR-039
**Notes:** After Epics 14 and 15; sweeps (Epic 20) and Studies share the batch-admission rule (SC-11).

### Epic 22: QMB robustness ladder (Wave 7 — serial after Epic 21, M)
Monte Carlo, the pre-build significance gate, and walk-forward — interfaces now, thresholds deferred to GAP-0048/0049 (SC-07).
**FRs covered:** FR-040
**Notes:** After Epic 21.

### Epic 23: QMB synthetic data (Wave 7, L)
Claim-class-labeled synthetic generation that never validates edge.
**FRs covered:** FR-041
**Notes:** After Epic 14.

## Epic 1: qmf-core — exact domain foundation

Everything later builds on exact money/time/instrument values, typed refusals, and deterministic fp1 identity, installable from the scaffolded workspace. This epic delivers the zero-dependency `qmf-core` library — CT-01 through CT-05 — and the two tier-1 static scanners that make FR-001 and FR-002 mechanically enforceable. It runs alone; nothing starts before it.

### Story 1.1: Greenfield uv-workspace scaffold (AR-01..AR-11)

As the factory developer,
I want the greenfield uv workspace laid out with the seven roster packages, the first extension, the pinned toolchain, and the SSSF factory-gate stamp reconciled,
So that every later story installs and gates against one canonical, dependency-directed workspace.

**Acceptance Criteria:**

**Given** a repo with no packages yet,
**When** the workspace scaffold is created,
**Then** the repo root holds a uv workspace whose members are `packages/*` (seven roster packages: qmf-core, qmf-registry, qmf-data, qmf-indicators, qmf-structure, qmf-venue, qmf-risk) and `extensions/*` (first extension qmf-calendar-forex), each in src/ layout `src/qmf/<name>/`, importing under the `qmf.*` PEP 420 implicit namespace,
**And** no distribution anywhere contains a `qmf/__init__.py`. (AR-01, AR-02, AR-03)

**Given** the scaffolded packages,
**When** each package's pyproject.toml is inspected,
**Then** every package declares every dependency (siblings included) in its own pyproject.toml, builds with the uv_build backend, pins CPython 3.14, and shares one committed workspace-root uv.lock,
**And** qmf-core declares zero outside dependencies (stdlib only) while numpy/pandas/pyarrow (2.5.2/3.0.5/25.0.1) appear only in outer packages. (AR-03, AR-04, AR-05)

**Given** the dependency graph,
**When** it is checked at Tier 2 with each package built in an isolated environment,
**Then** qmf-core depends on nothing, every other roster package depends only on qmf-core, the sole inter-library edge present is qmf-registry→qmf-data, and nothing imports qmf-venue or qmf-risk,
**And** an undeclared import fails the isolated build. (AR-06, AR-18)

**Given** the pinned canonical toolchain,
**When** `poe fmt | lint | types | test | check` (and `check-integration`, `check-release`) run,
**Then** they invoke ruff 0.16.3, pyright 1.1.411 strict workspace-wide, pytest 9.x, and poethepoet 0.48.0 and produce byte-identical results on every machine,
**And** a secret-scan gate runs inside `poe check` at Tier 1. (AR-11, AR-23, AR-24)

**Given** the existing SSSF factory-gate stamp at the repo-root pyproject.toml (name `sssf-project`, the `dev` dependency group and `adws/tests` that are the merge gate's fail-closed contract),
**When** the workspace-root pyproject.toml is authored to declare the uv workspace members,
**Then** it preserves that gate contract intact — the `[dependency-groups] dev` list and `[tool.pytest.ini_options] testpaths = ["adws/tests"]` survive — so `uv run --project <tree> --group dev ruff check .`, `... mypy adws`, and `... pytest -q adws/tests` still pass,
**And** the engine's fail-closed integration gate stays green (never reading RED because a command could not run). (epic notes; root pyproject comments)

**Given** a workspace-root DEPENDENCIES.md register,
**When** any dependency is added,
**Then** it is listed with name, licence, and why; MIT/BSD/Apache/PSF are allowed and GPL/AGPL, strategy-family, and platform-imposing dependencies are rejected (LGPL only unmodified and separately installed),
**And** the seven roster packages version in SemVer lockstep (0.x until the V1 blueprint ships) while qmf-calendar-forex rides its own SemVer ladder with tzdata pinned. (AR-07, AR-09, AR-02)

**Given** the workspace quality conventions,
**When** any package story in any epic delivers a designed failure mode,
**Then** the package ships a failure-register entry alongside its tests — failure class, detection, auto-recovery/retry semantics, the visible degraded state, its notification tier, and the product-user affordance (what failed, why, can I retry, what a retry does) — written for someone who was not in the design room,
**And** this register convention is a tier-1 artifact obligation on every subsequent story in this document. (NFR-11)

**Given** the AD-13 benchmark convention,
**When** each roster package's scaffold lands,
**Then** it carries a benchmark-harness slot (speed and peak memory at a package-native load ladder) with unit-test status, first measurements becoming fingerprinted (OS, CPU-class)-scoped baselines,
**And** qmf-core's harness includes the import-time budget benchmark asserting import completes well under one second, with the ~40-bot reference workload at the 10/100/200 marks measured once the QMB run loop and orchestrator exist (Epics 14-15). (NFR-04; AR-22)

### Story 1.2: Typed refusal envelope (FR-004, CT-04)

As a framework consumer,
I want every public operation to return a typed refusal instead of raising,
So that I and any agent branch on structure, never on error prose.

**Acceptance Criteria:**

**Given** any public qmf-core operation,
**When** it fails,
**Then** it RETURNS a `TypedRefusal` frozen-dataclass value across the public boundary (never raised) carrying a `category`, a machine-readable `context`, and a `retryability` answer,
**And** exceptions are reserved for programmer error and never carry a refusal across a package boundary. (CT-04; AR-13)

**Given** a TypedRefusal,
**When** its fields are read,
**Then** `category` is exactly one of the seven values — invalid input, unsupported capability, unavailable dependency, stale evidence, policy rejection, transient venue failure, storage failure — and `retryability` is exactly one of yes | no | after-condition,
**And** the after-condition descriptor is present only when retryability = after-condition and absent otherwise. (CT-04 enums)

**Given** value-type construction,
**When** `try_create` is called with invalid input,
**Then** it returns the refusal arm (a CT-04 value) while the unchecked constructor stays available for trusted internal use,
**And** `context` is always present (it may be an empty structured object) but is never null, and a refusal is never swallowed. (CT-04; DEC-0109, DEC-0112)

**Given** the CT-04 module,
**When** Tier 1 and Tier 2 run,
**Then** an executable CT-04 contract test owned by qmf-core plus reference-usage examples ship as tier-1 artifacts,
**And** the module meets the 80% package coverage floor. (AR-19, AR-21, AR-20)

### Story 1.3: Instrument, venue, and account identity (FR-003, CT-03)

As a framework consumer,
I want instrument identity to be an opaque, never-parsed `(venue, symbol)` pair with venue and account as first-class nouns,
So that multiple brokers never mix and renames never rewrite history.

**Acceptance Criteria:**

**Given** an Instrument identity,
**When** it is constructed,
**Then** it is the opaque pair `(venue, venue's own symbol)` with the symbol stored opaque and never parsed,
**And** VenueId is an operator-minted, opaque, stable token, never derived from a mutable broker attribute and never reused — a prop firm white-labeling cTrader is its own venue. (CT-03)

**Given** the Venue and Account nouns,
**When** they are used,
**Then** they are defined only in qmf-core (records and lifecycle owned by qmf-registry, never by an edge module), an Account carries exactly one role from the fixed set live | demo | paper-validation | paper-benched | prop-firm, and Books bind to accounts never to venues. (CT-03; AR-08)

**Given** a rename, alias, asset-class, or metadata change,
**When** it is recorded,
**Then** it is a separate dated record pointing at the identity and stored history never rewrites — a correction is a new dated record. (CT-03)

**Given** `try_create` for an identity value,
**When** a required part (venue or symbol) is missing or invalid,
**Then** a typed refusal is returned via CT-04, never a default,
**And** null is prohibited in fp1 identity content — absent metadata is an omitted key or simply no dated record, never a null field. (CT-03; CT-04; DEC-0108)

**Given** the CT-03 module,
**When** Tier 1 and Tier 2 run,
**Then** it ships an executable CT-03 contract test plus reference examples as tier-1 artifacts and meets the 80% coverage floor. (AR-19, AR-21, AR-20)

### Story 1.4: Exact money, price, and quantity values (FR-001, CT-01)

As a framework consumer,
I want Money, Price, and Quantity as exact scaled integers with binary float banned on the money path,
So that no arithmetic on the money path can silently lose or invent value.

**Acceptance Criteria:**

**Given** Money, Price, and Quantity,
**When** each is constructed,
**Then** each is a whole-number scaled integer — Money(currency, scale), Price(instrument, scale) as an instrument-tagged ratio never tagged with a single currency, Quantity(unit, scale) with an opaque unit — carrying a unit-kind from the closed vocabulary money(currency) | price-delta(instrument) | quantity(unit) | value-factor(instrument, currency) | r-multiple | rate(money-per-r) | count | dimensionless-ratio | duration | instant,
**And** a null unit-kind is a typed refusal, never a default. (CT-01; DEC-0154)

**Given** a binary float that reaches a value on the money path (any value transitively contributing to an order quantity, price, P&L, or balance),
**When** value construction is attempted,
**Then** `try_create` returns an `invalid input` typed refusal (FM-1),
**And** a float re-enters Money, Price, or Quantity only through a named conversion boundary that states its rounding mode explicitly. (CT-01 FM-1; DEC-0105)

**Given** mixed-scale arithmetic on the same currency or unit,
**When** the scales cannot auto-promote losslessly,
**Then** a typed refusal is returned — never an implicit rescale or silent rounding — and when they can, the result auto-promotes to the finer scale. (CT-01 FM-4)

**Given** price subtraction,
**When** two Prices are subtracted,
**Then** the result is a first-class `PriceDelta(instrument, scale)` distinct from Price and the instrument-scoped pip/point comes from CT-03 instrument-metadata records, never hardcoded,
**And** an absent value-factor is an `unavailable dependency` refusal, never a silent conversion. (CT-01; DEC-0131, DEC-0154)

**Given** a Money/Price/Quantity/PriceDelta value entering fp1 identity content,
**When** it is serialized,
**Then** it takes the pinned canonical form — exact rationals reduced to lowest terms, denominator strictly positive, sign on the numerator, two-key serialization, and the declared canonical storage scale per value class — so equal value implies equal fingerprint by construction,
**And** every serialized CT-01 artifact stamps contract format version 1. (CT-01; DEC-0158, DEC-0103)

**Given** the CT-01 primitive module,
**When** Tier 1 and Tier 2 run,
**Then** it meets 100% branch coverage,
**And** it ships an executable CT-01 contract test plus reference examples as tier-1 artifacts. (AR-20, AR-19, AR-21)

### Story 1.5: Exact time, calendars, and injected Clock (FR-002, CT-02)

As a framework consumer,
I want int64 UTC-nanosecond time with versioned calendars and a Clock injected at the composition root,
So that results stay identical across server moves, DST shifts, tzdata updates, and clock corrections.

**Acceptance Criteria:**

**Given** any stored timestamp,
**When** it is represented,
**Then** it is an int64 count of UTC nanoseconds since the Unix epoch (POSIX no-leap-second) with representable range 1677 through 2262, nanosecond-arithmetic overflow is an `invalid input` typed refusal never a wrap (FM-2), and instant 0 is a valid instant,
**And** an absent time is an absent field, never a zero sentinel. (CT-02; FM-2)

**Given** CivilDate and TradingDate,
**When** they are compared,
**Then** they are distinct types, a TradingDate carries its calendar identity and version in-band, equality holds only within one calendar identity, and cross-calendar comparison returns a typed refusal (FM-3),
**And** a TradingDate is never derived by formatting an instant and is never used as a causality proxy — causality is compared on instants only. (CT-02; FM-3)

**Given** clock access,
**When** any component below the composition root needs the time,
**Then** it reads only through the core-defined `Clock` protocol seam injected at the composition root (real clock in production, data-driven clock in replay) and nothing below the root reads the system clock,
**And** wall and monotonic kinds are type-separated so a monotonic reading is never an Instant and is persistable only as a boot-scoped opaque diagnostic. (CT-02; AR-16)

**Given** calendars,
**When** qmf-core is inspected,
**Then** it embeds no market-hours calendar rule set — calendars ship as separate versioned extensions that force TZPATH to their pinned tzdata and verify at import that the resolved tzdb equals the pin, refusing `unavailable dependency` on a mismatch (FM-5) — and only the rule set plus tzdata version enter fingerprints,
**And** local/ISO-8601 time is display-only, always labelled, and excluded from identity. (CT-02; FM-5)

**Given** WriterId,
**When** it is minted,
**Then** it is a first-class core noun minted per (machine, role, stream) with a boot/epoch id, and every record stream carries a per-writer strictly-increasing sequence where (instant, writer, sequence) is an ordering key with no causal meaning. (CT-02; DEC-0106)

**Given** the CT-02 primitive module,
**When** Tier 1 and Tier 2 run,
**Then** it meets 100% branch coverage,
**And** it ships an executable CT-02 contract test plus reference examples as tier-1 artifacts. (AR-20, AR-19, AR-21)

### Story 1.6: Canonical serializer, fp1 fingerprint, result label, and worlds (FR-005, CT-05)

As a framework consumer,
I want one canonical serializer and fp1 fingerprint, the result label, and the world enum,
So that two conformant producers and merging sandboxes always agree on identity and replay reproducibility is a platform property.

**Acceptance Criteria:**

**Given** the fp1 fingerprint function and canonical serializer,
**When** any artifact is fingerprinted,
**Then** both live only in qmf-core and no other package computes a fingerprint except by calling this single implementation,
**And** the emitted form is `fp1:sha256:<hex>`. (CT-05; AR-14)

**Given** the pinned fp1 recipe,
**When** identity bytes are produced,
**Then** they are UTF-8 JSON with object keys sorted lexicographically at every depth, no insignificant whitespace, NFC-normalized strings, integer-only identity numerics (floats refused in identity content), CT-01 canonical form for exact rationals and money-class values, null prohibited (an absent value is an omitted key), order-significant arrays, and hashed SHA-256,
**And** every contract field is identity by default while a display-only exclusion requires an explicit, versioned declaration. (CT-05; DEC-0108, DEC-0158)

**Given** a computed result entering evidence,
**When** it is labeled,
**Then** the ResultLabel carries producer contract identity, producer contract format version, input fingerprints, evidence time range (a half-open Interval over int64 UTC ns), computation identity, evidence class (confirmed | unconfirmed | provisional), and world — and those parts together ARE its identity,
**And** the occurrence record (when, where, by whom it ran) sits outside identity. (CT-05; DEC-0110)

**Given** a result label with world = simulated,
**When** it is written into governed evidence,
**Then** a `policy rejection` typed refusal is returned (simulated is reserved-unusable in V1, GAP-0048),
**And** world is one of live | replay | simulated and a non-live world never writes the live evidence namespace. (CT-05; FM-7)

**Given** a write presenting an existing fp1 hash,
**When** the bytes are byte-identical,
**Then** the re-write is accepted silently (idempotent), and when the bytes differ (a true collision) it is refused and alarmed, never overwritten. (CT-05; FM-6)

**Given** the two version ladders,
**When** an artifact is versioned,
**Then** package SemVer stays display-only provenance that never enters identity while every serialized artifact stamps its own integer contract format version whose meaning never mutates,
**And** the CT-05 module ships its contract test plus examples and meets the 80% coverage floor. (CT-05; AR-25, AR-26, AR-19, AR-21, AR-20)

### Story 1.7: Money-path float static scanner (NFR-02 enforcing FR-001)

As the factory developer,
I want a tier-1 static scanner that flags binary float on the money path,
So that FR-001 is mechanically enforced by the gate rather than left to code review.

**Acceptance Criteria:**

**Given** the tier-1 static scanners required by NFR-02,
**When** the money-path float scanner runs over the workspace,
**Then** it statically flags any binary float that reaches a value on the money path (any value transitively contributing to an order quantity, price, P&L, or balance),
**And** its purpose is to make FR-001 mechanically enforceable rather than review-dependent. (NFR-02; FR-001)

**Given** a float that crosses a named conversion boundary declaring its rounding mode,
**When** the scanner runs,
**Then** that sanctioned crossing is NOT flagged,
**And** an undeclared float on the money path IS flagged. (CT-01; DEC-0105)

**Given** the scanner,
**When** `poe check` runs at Tier 1,
**Then** the scanner is wired into `poe check` and a flagged violation fails the gate with a nonzero exit,
**And** this is consistent with the fail-closed gate discipline. (AR-11, AR-18)

**Given** the scanner itself,
**When** Tier 1 runs,
**Then** it ships its own executable tests with must-flag and must-not-flag fixtures,
**And** it meets the package coverage floor. (AR-21, AR-20)

### Story 1.8: Ambient-nondeterminism static scanner (NFR-02 enforcing FR-002)

As the factory developer,
I want a tier-1 static scanner that flags system-clock reads and ambient nondeterminism below the composition root,
So that FR-002's "time is injected, nothing below the root reads the system clock" is mechanically enforced.

**Acceptance Criteria:**

**Given** the second tier-1 scanner required by NFR-02,
**When** the ambient-nondeterminism scanner runs over the workspace,
**Then** it statically flags any read of the system clock or other ambient nondeterminism (for example `datetime.now`, `time.time`/`time.monotonic`, or unseeded `random`) below the composition root,
**And** its purpose is to make FR-002 mechanically enforceable. (NFR-02; FR-002; AR-16)

**Given** clock access through the injected `Clock` protocol seam,
**When** the scanner runs,
**Then** injected-Clock usage is NOT flagged,
**And** a direct system-clock read below the composition root IS flagged. (CT-02; AR-16)

**Given** the scanner,
**When** `poe check` runs at Tier 1,
**Then** it is wired into `poe check` and a flagged violation fails the gate with a nonzero exit. (AR-11, AR-18)

**Given** the scanner itself,
**When** Tier 1 runs,
**Then** it ships must-flag / must-not-flag fixtures as executable tests,
**And** it meets the package coverage floor. (AR-21, AR-20)

### Story 1.9: Core protocol seams — secrets and injected sinks

As a framework consumer,
I want qmf-core to define the SecretRef/SecretValue types and the ObservationSink, JournalSink, RecordSink, and SecretStore protocols,
So that every outer package emits through core-defined seams injected at the composition root and no package ever holds secret values or writes stores directly.

**Acceptance Criteria:**

**Given** the qmf-core public API,
**When** a consumer imports qmf.core,
**Then** SecretRef and SecretValue are available as typed values
**And** SecretValue never renders its secret in repr, str, serialization, or logging (AR-37; DEC-0136).

**Given** the four sink protocols (ObservationSink, JournalSink, RecordSink, SecretStore),
**When** an outer package emits an observation, journal event, or record, or reads a secret,
**Then** it does so only through the corresponding typing.Protocol seam injected at the composition root
**And** qmf-core itself performs no I/O and spawns no work (AD-15; DEC-0138).

**Given** a sink refusal for an unpersistable write,
**When** a sink returns that refusal,
**Then** it is a CT-04 typed refusal returned to the caller with category, context, and retryability
**And** callers can implement block-on-unpersistable semantics against it (CT-04; AR-47).

**Given** the SecretStore protocol,
**When** a secret is replaced,
**Then** the protocol exposes read and atomic replace only
**And** no getter path returns a plaintext value outside SecretValue's controlled access (AR-37, AR-38).

**Given** the tier-1 gate,
**When** `poe check` runs on qmf-core,
**Then** the seam modules carry executable tests and reference-usage examples at the 80% coverage floor (AR-20, AR-21).

## Epic 2: qmf-registry — identity, lineage & promotion

Every governed artifact registers once, carries lineage forever, and nothing reaches live money without a human-signed promotion. This epic builds the registry logic inside the already-scaffolded `qmf-registry` package (Epic 1 Story 1.1): fingerprint-keyed per-kind records (CT-06), append-only typed lineage edges (CT-07), the human-signed promotion occurrence (ADR-0015, CT-13), and — last — persistence through qmf-data's store-seam (CT-09 over CT-11). It runs after Epic 1, parallel with Epics 3 and 4; the persistence story consumes Epic 3's store-seam story, which lands first.

### Story 2.1: Per-kind fingerprint-keyed registration records (FR-006, CT-06)

As a framework consumer,
I want each artifact registered as a per-kind versioned record whose stable id is its fp1 fingerprint,
So that identical work from two sandboxes deduplicates by construction and no universal all-fields card is required.

**Acceptance Criteria:**

**Given** an artifact to register,
**When** registration writes a record,
**Then** it is a per-kind versioned record (each kind its own contract, never one universal all-fields recipe card) carrying the tiny common header — kind, contract format version, at-birth parent references (identity-bearing), writer (WriterId), and per-writer sequence — plus a kind-specific body. (CT-06)

**Given** a record,
**When** its stable id is derived,
**Then** the id is derived from its fp1 fingerprint and is never minted,
**And** created-at and every other occurrence fact are display-only and excluded from fp1 identity, so identical work from two sandboxes deduplicates by computation identity. (CT-06; DEC-0114, DEC-0110)

**Given** two writes to the same fp1 stable id,
**When** the bytes are byte-identical,
**Then** the re-write is accepted silently (idempotent),
**And** when the bytes differ (a true collision) it is refused and alarmed, never overwritten. (CT-06; FM-6)

**Given** kinds,
**When** a registration names a kind or field set CT-06 does not define,
**Then** a typed refusal is returned (FM-1) — kinds are addable and never redefined,
**And** the reserved kind names promotion-occurrence-card and treasury-boundary-event are honored. (CT-06; FM-1)

**Given** lineage that accrues after a record's birth,
**When** it is recorded,
**Then** it is written ONLY as CT-07 typed edges and never back into the record,
**And** at-birth parent references stay in the header and readers never union header references with edges. (CT-06)

**Given** roster-scoped default-deny direction,
**When** packages are built in isolation at Tier 2,
**Then** qmf-registry imports only qmf-core, no roster library imports qmf-registry, and registration is invoked by the application at the composition root,
**And** the module ships its CT-06 contract test plus reference examples and meets the 80% coverage floor. (AR-06, AR-18, AR-19, AR-21, AR-20; DEC-0120)

### Story 2.2: Append-only typed lineage edges (FR-007, CT-07)

As a framework consumer,
I want lineage recorded as append-only typed edges referencing fingerprints,
So that provenance is graph-shaped and never rewritten, with no database server.

**Acceptance Criteria:**

**Given** lineage,
**When** an edge is written,
**Then** it is an append-only typed edge record referencing both endpoints by their fp1 fingerprint (never a mutable or minted id), with `edge_type` drawn from the ratified V1 set — supersedes, promoted-from, occurrence-of, corroborates, disagrees-with, confirmed-as, confirmation, invalidation, interaction, out-of-sequence, continues-performance, carries-ledger, enacts, branches-from — addable in later versions and never redefined. (CT-07)

**Given** the edge file format,
**When** edges are serialized,
**Then** they are pinned JSONL: one fp1-canonical JSON object per line, LF-terminated, appended with fsync, never rewritten, and size-rotated with a monotonic file ordinal,
**And** indexes over edges are local and rebuildable, so losing an index costs a rebuild, never evidence. (CT-07)

**Given** `supersedes`,
**When** more than one supersedes edge is presented for a subject,
**Then** supersedes is pinned linear — at most one outgoing edge per subject and one resolvable head, so "current" is never ambiguous,
**And** a branching Book/BMS version graph instead uses `branches-from`, where several heads are legal and "current" is a separate dated pointer record, never inferred from the graph. (CT-07; DEC-0158, DEC-0144)

**Given** a correction,
**When** a record must change,
**Then** it is a new edge (and a superseding relationship is a `supersedes` edge) — never an in-place edit,
**And** `corroborates` and `disagrees-with` edges keep source disagreements visible and are never merged away. (CT-07; DEC-0119)

**Given** an edge that uses a kind outside the ratified CT-07 set or references an endpoint by anything other than an fp1 fingerprint,
**When** it is appended,
**Then** it is not admitted and a typed refusal is returned (FM-2),
**And** a byte-identical idempotent re-append is accepted while a true collision on differing bytes is refused and alarmed. (CT-07; FM-2)

**Given** an edge stream,
**When** it is written,
**Then** it has exactly one writer holding a WriterId and unlimited readers,
**And** the CT-07 module ships its contract test plus reference examples and meets the 80% coverage floor. (CT-07; AR-19, AR-21, AR-20)

### Story 2.3: Human-signed promotion occurrence (FR-009, CT-06 promotion card + CT-13 promotion event, ADR-0015)

As the operator,
I want the only path to live money to be a human-signed promotion occurrence attesting a record's fingerprint with a mandatory plain-words summary,
So that a human's decision to move an artifact toward live money is recorded in a form that human can be held to.

**Acceptance Criteria:**

**Given** the only path to live money,
**When** an artifact is promoted,
**Then** a promotion-occurrence card is minted with a human-only signer, a signed immutable record, and a mandatory plain-words summary declared an identity field, plus the attested record's fp1 string, reviewer identity, and instant,
**And** V1 signing is the operator's recorded approval, taking no cryptographic dependency. (ADR-0015; CT-06; DEC-0116)

**Given** a live-promotion request,
**When** no human-signed promotion-occurrence card is present,
**Then** promotion does not occur and a refusal is returned (FM-4),
**And** only a human promotes an artifact into the live zone. (CT-06 FM-4; AR-39)

**Given** a card whose plain-words summary is corrected after signing,
**When** the correction is made,
**Then** a NEW promotion card is minted and linked to the prior card with a CT-07 `supersedes` edge,
**And** the signed record is never edited in place, because the signature attests the exact words read. (CT-06 FM-5; CT-07)

**Given** the promotion journal event,
**When** it is emitted,
**Then** it is the CT-13 `promotion` event carrying ONLY the promotion card's fp1 fingerprint plus correlation_id — never a second schema,
**And** the registry card is canonical. (CT-13; CT-06)

**Given** a card attesting an AD-32 risk admission,
**When** it is assembled,
**Then** it carries the Book-definition (or BMS-definition) fingerprint as an identity field,
**And** a signature can therefore never attest a superseded template. (DEC-0158)

**Given** the promotion feature,
**When** Tier 1 and Tier 2 run,
**Then** it ships CT-06 promotion-card and CT-13 promotion-event contract tests plus reference examples,
**And** it meets the 80% coverage floor (the promotion gate's own workflow, UI, and timing remain platform territory outside QMF). (AR-19, AR-21, AR-20; ADR-0015)

### Story 2.4: Registry persistence through the qmf-data store-seam (FR-008, CT-09 over CT-11)

As the factory developer,
I want registry records and lineage edges persisted through qmf-data's append-store into the per-world registry room,
So that the registry needs no database server and rides the single ratified inter-library edge.

**Acceptance Criteria:**

**Given** registry records and CT-07 lineage edges,
**When** they persist,
**Then** they are written through qmf-data's CT-11 append-store contract — the single ratified inter-library edge qmf-registry→qmf-data — into the per-world registry room (one of qmf-data's seven room-roles), with stdlib-typed signatures at the boundary and no database server. (CT-09; CT-11; L30)

**Given** the store-seam delivered by Epic 3's store-seam story,
**When** the registry persists a record,
**Then** storage keys on the record's fp1 stable id, never on a timestamp or minted id,
**And** a byte-identical idempotent re-write is accepted silently while a true collision on differing bytes is refused and alarmed. (CT-09; CT-11; DEC-0108)

**Given** rooms instantiated per world,
**When** a read crosses worlds,
**Then** it is a `policy rejection` refusal and a non-live world never writes the live evidence namespace (FM-7),
**And** writing world = simulated into governed evidence is a policy-rejection refusal until GAP-0048. (CT-09; FM-7)

**Given** the underlying store fails — disk-full, corrupt, locked, or truncated,
**When** persistence is attempted,
**Then** a `storage failure` typed refusal is returned — store-library exceptions are translated at the qmf-data boundary and never propagated across the package seam (FM-8),
**And** no partial registration is claimed successful. (CT-09; FM-8)

**Given** a schema or format change,
**When** a migration runs,
**Then** it runs preflight → backup-first → dry-run → migrate → verify with a documented restore path and never in-place mutation of the only copy,
**And** every serialized registry artifact stamps its contract format version so history stays readable forever. (CT-09; AR-32, AR-25)

**Given** the persistence seam,
**When** Tier 2 runs,
**Then** the CT-09 contract test runs against the CT-11 store-seam by both producer and consumer, reference examples ship,
**And** the 80% coverage floor holds. (AR-18, AR-19, AR-21, AR-20)

## Epic 3: qmf-data — evidence store & journals

Market facts land bitemporally in per-world rooms, journals are gapless, research access is seal-and-split governed. This epic delivers the dependency-free store seam first (it unblocks Epic 2's registry-persistence tail), then the bitemporal source-observation boundary, the seven room-roles per world, the dataset splits and the 12-month seal, and the durable journal streams with their read-time entity projections. Covers FR-010, FR-011, FR-012, FR-013, FR-016.

### Story 3.1: Dependency-free store seam over swappable engines

As the factory developer,
I want a dependency-free persistence seam that physically stores artifacts behind QMF-owned contracts over four swappable local engines with no database server,
So that every later data-policy and registry-persistence feature has one append-only, fp1-keyed store to write through, and an engine change costs a rebuild rather than evidence.

**Acceptance Criteria:**

**AC1**
**Given** COMP-QMF-DATA-STORE declares zero component dependencies and exposes the CT-11 append-store, CT-13 journal, CT-09 registry-persistence, and CT-26 store-to-backup boundaries with stdlib-typed signatures
**When** an artifact is persisted through any of these contracts
**Then** it is physically written by exactly one of the ratified engines — Parquet for columnar time-series, DuckDB for rebuildable analytics views, SQLite for transactional metadata, JSONL for append streams (AR-30, DEC-0117)
**And** no database server, graph database, or engine outside that ratified set is introduced, and each engine stays behind its owned contract so it is swappable.

**AC2**
**Given** the store keys every artifact on its `fp1:sha256:<hex>` fingerprint, never on a timestamp or minted id
**When** a write presents a fingerprint that already exists
**Then** a byte-identical re-write (the sandbox-merge normal case) is accepted silently, and a true collision — the same hash with differing bytes — is refused and alarmed, never overwritten (DEC-0108).

**AC3**
**Given** JSONL is the engine for journal and lineage-edge append streams
**When** a record is appended to such a stream
**Then** it is written as one fp1-canonical object per line, LF-terminated, append-with-fsync, with size rotation under a monotonic ordinal and locally rebuildable indexes (AR-31, DEC-0114)
**And** each stream has exactly one holding `WriterId` with unlimited readers, and a second writer attempting the same stream does not proceed (DEC-0113).

**AC4**
**Given** the underlying engine is unavailable, disk-full, or a file is locked, truncated, or corrupt
**When** a write or read is attempted
**Then** the store-library exception is translated to a `storage failure` typed refusal at the boundary and is never propagated as an exception across a package seam, and no persistence-success is reported.

**AC5**
**Given** COMP-QMF-REGISTRY reaches the store through the single ratified `qmf-registry → qmf-data` edge to persist its per-kind records and CT-07 lineage edges into the per-world registry room
**When** Epic 2's CT-09 registry-persistence story writes through this seam
**Then** the registry room accepts records as fp1-keyed per-kind versioned records and lineage as pinned JSONL edges, append-only and never rewritten in place, under the same retention, backup, and migration law as every other room (DEC-0117, DEC-0120)
**And** a cross-world read is a `policy rejection` refusal and a `world = simulated` write is a `policy rejection` refusal (DEC-0110).

### Story 3.2: Bitemporal source observations with append-only corrections

As a framework consumer,
I want external facts to land as bitemporal source observations on the CT-10 boundary, with corrections appended and never overwriting,
So that the framework never loses when a fact occurred, when it became knowable, or from whom it came, and a late correction can never erase the earlier evidence.

**Acceptance Criteria:**

**AC1**
**Given** the CT-10 boundary, owned by COMP-QMF-DATA as its only ratified reader, accepts producer observation values routed by the application
**When** an observation is admitted
**Then** it carries event-time and known-at (both int64 UTC nanoseconds), a `source` id orthogonal to VenueId, a `revision`, an AD-8 WriterId with its boot/epoch id and a per-writer strictly-increasing sequence, its `world`, and its `fp1:sha256:<hex>` identity computed only by qmf-core (DEC-0117, DEC-0108).

**AC2**
**Given** an observation carries a foreign timestamp and, if money- or price-bearing, a foreign amount
**When** it is stored
**Then** the foreign timestamp is stored verbatim with its declared zone, offset, and resolution alongside a local receive wall time in int64 UTC ns, and foreign money is stored verbatim as scaled integers at the source's declared scale — conversions to framework Time and Money are derived values carrying lineage, never silent rewrites or rescales (DEC-0106, DEC-0105).

**AC3**
**Given** a later correction refers to the same provider-native occurrence as an existing observation (SCN-0002)
**When** the correction is submitted through the CT-10 boundary keyed on `(source, source-native id, revision)`
**Then** the original evidence remains preserved, the correction is admitted as a distinct artifact with its own fp1 fingerprint carrying `correction_of` = the corrected observation's fp1, and it is never folded inline or allowed to masquerade as the original (DEC-0117).

**AC4**
**Given** an incoming record lacks event-time, known-at, source, revision, writer, or fp1 identity
**When** admission is attempted
**Then** the observation does not enter governed CT-10 evidence and the boundary returns an `invalid input` typed refusal (FM-1, DEC-0109).

**AC5**
**Given** the observation is world-scoped evidence
**When** a read requests observations from a different world than the caller's, or a write targets `world = simulated`
**Then** each is a `policy rejection` refusal (DEC-0117, DEC-0110).

### Story 3.3: Seven room-roles per world with cross-world refusal

As a framework consumer,
I want evidence partitioned into the seven room-roles, each instantiated per world with only raw archive and journal evidence-bearing and raw retained forever,
So that world isolation is delivered by storage separation, an analytics-engine format break never costs evidence, and no result's cited input is ever deleted.

**Acceptance Criteria:**

**AC1**
**Given** COMP-QMF-DATA owns the seven room-roles — ingest door, immutable raw archive, processed, journal, split-governed research door, backup, and registry room
**When** a world is instantiated (`live` or `replay`)
**Then** all seven roles are instantiated independently for that world, and `world = simulated` is reserved-unusable so any write into its governed evidence is a `policy rejection` refusal (DEC-0117, DEC-0110, AR-33).

**AC2**
**Given** only the immutable raw archive and journal formats are evidence-bearing
**When** processed data or a DuckDB analytics view is written
**Then** it is marked a rebuildable view, its pinned analytics-engine major is recorded, and a rebuild pins the original calendar identity and tzdata version — so an engine format break costs a rebuild, never evidence (DEC-0117, DEC-0103).

**AC3**
**Given** the retention law keeps raw originals and lineage forever
**When** processed data or a correction arrives
**Then** the raw original is never erased, and any rebuildable artifact that a result label cites is retained forever — deletion is licensed only for a rebuildable artifact no result label cites (DEC-0117, DEC-0118).

**AC4**
**Given** each room-role is instantiated per world and storage separation delivers world isolation
**When** a read requests evidence from a world other than the caller's
**Then** the cross-world read is a `policy rejection` refusal (FM-4, DEC-0117, DEC-0110).

**AC5**
**Given** time-series evidence is partitioned by source, instrument, and time window
**When** an artifact is stored or located
**Then** it resolves within its `(source, instrument, time-window)` partition inside its world's room, and a rebuildable view is never treated as evidence-bearing (DEC-0118, DEC-0117).

### Story 3.4: Dataset splits and the 12-month no-peek seal

As a framework consumer,
I want research data exposed as fingerprinted train/validation/sealed-test split manifests with the newest ~12-month window sealed at every read boundary,
So that research can never consume its own held-out evaluation period and the seal cannot be silently recycled.

**Acceptance Criteria:**

**AC1**
**Given** a CT-12 dataset split
**When** the manifest is produced
**Then** it is a fingerprinted, time-ordered, non-overlapping manifest whose `split_id` is derived from its fp1 (never minted), pinning exactly one calendar identity and version in-band, split by default into `train`, `validation`, and `sealed-test`, with boundaries as explicit stored TradingDates or Instants — never civil dates (DEC-0119, DEC-0046, DEC-0106).

**AC2**
**Given** `purge_width` and `embargo_width` are required manifest fields that enter the split fingerprint
**When** a manifest omits either
**Then** it is an `invalid input` refusal; and when present they default to the maximum declared warm-up-plus-confirmation-delay bound across every producer the split cites, so a split reused with a longer-horizon artifact refuses rather than leaks (DEC-0131, DEC-0109).

**AC3**
**Given** records partition into splits by knowledge time — confirmed-at for structure objects, the knowable-at of the last contributing input for indicator results
**When** a record's observed-at precedes a boundary while its confirmed-at follows it
**Then** the manifest refuses that record unless the declared embargo covers the gap (DEC-0131).

**AC4**
**Given** the newest sealed window (`registry:historical_holdout_months`, approximately twelve months) is a no-peek lock and not retention — all history is kept regardless
**When** a default research request or any read crosses the raw-archive, processed, research-door, or restored-backup boundary into the sealed period (SCN-0003)
**Then** the sealed rows are refused with a `policy rejection` at every read boundary, enforced now independent of the deferred GAP-0016/0017 gates, and never returned as a silent empty result (DEC-0119, DEC-0121).

**AC5**
**Given** a row carrying a calendar identity different from the manifest's pinned one
**When** it is offered to the split
**Then** it is refused as a `policy rejection`, never silently rescaled; and the seal boundary is a frozen TradingDate never re-derived under a later tzdata version (DEC-0119, DEC-0106).

**AC6**
**Given** the sealed period is entitled to exactly one authorized final look
**When** that final look is taken
**Then** it is journaled as a named `control action` subtype in CT-13 and the sealed set is never silently recycled into research (DEC-0119).

### Story 3.5: Durable journals — seven event types in gapless per-writer streams

As a framework consumer,
I want durable journal evidence recorded as N append-only per-writer streams over the seven ratified event types,
So that every state change is reconstructable from gapless streams, distinct from operator logging and free of any runtime event bus.

**Acceptance Criteria:**

**AC1**
**Given** CT-13 persists the journal as N append-only streams, one per producing component, each under a single WriterId with unlimited readers
**When** an event is appended
**Then** it is one of exactly seven event types — decision, order, fill, risk transition, promotion, data quality, control action — an enum addable in later versions but never redefined, and QMF's own wired producers are COMP-QMF-DATA (data quality, control action) (DEC-0119, DEC-0116).

**AC2**
**Given** each stream's sequence is strictly increasing and gapless per `(writer, boot-epoch)`
**When** a gap is detected in a stream
**Then** the gap signals loss and is surfaced, and a second writer attempting to write a stream already owned by a WriterId does not proceed (DEC-0119, DEC-0113).

**AC3**
**Given** a `decision` event carries a mandatory closed `outcome` field — `authorized | refused-by-door | suppressed` — with the refusing-door or suppressing-authority reference
**When** a projection later selects decisions (the legacy `veto_ledger` included)
**Then** it selects on that declared field, never on key presence (DEC-0158, DEC-0150).

**AC4**
**Given** journals are evidence encoding (int64 UTC ns + writer + sequence) while operator/diagnostic logs are ISO-8601-with-Z display
**When** an event is recorded
**Then** its identity content is fp1-canonical with `correlation_id` excluded from fp1 identity by explicit versioned declaration, its optional `display_time` excluded from identity, and cross-stream causal linkage carried only by AD-16 typed edge records — never by timestamps or the `(instant, writer, sequence)` ordering key (DEC-0112, DEC-0108, DEC-0114).

**AC5**
**Given** a journal event cannot be durably persisted, or a multi-room write is partial
**When** the write is attempted
**Then** it is a `storage failure` refusal that blocks the command stream in the component holding the WriterId, is journaled on recovery, and never silently loses the event (DEC-0137, DEC-0109).

### Story 3.6: Read-time entity-journal projections (logbooks)

As the operator,
I want the Book, BMS, and per-bot journals delivered as declared read-time projections over the writer-scoped streams,
So that I get one logbook per entity from the single recorded set of streams without any entity minting a stream of its own, and paper and live are separated by construction.

**Acceptance Criteria:**

**AC1**
**Given** entity journals — Book journal, BMS journal, and per-bot journal (the operator's logbook) — are declared read-time projections selected by entity identity, never additional writers
**When** a per-entity, per-binding, or combined view is requested
**Then** it is extracted on demand from the one recorded set of writer-scoped streams, and no entity mints a stream of its own (DEC-0145).

**AC2**
**Given** risk-authored events carry the Book-definition fingerprint and the binding identity `(BookInstanceId, BmsInstanceId, VenueId, AccountId, world)` — and, where one bot is concerned, the CT-33 Bot definition fp1 plus its AD-41 seat binding — as identity fields, while venue-authored events (order, fill, data quality) carry only the command record's content fingerprint
**When** a Book projection must include orders and fills
**Then** it joins venue-authored events through that command-fingerprint join, the pinned versioned CT-25 surface, so Book identity never has to be threaded into the neutral venue payload (DEC-0145, DEC-0143, DEC-0173).

**AC3**
**Given** a projection resolves inside one role-scoped namespace — the live evidence namespace admits only `role = live` rows, and demo, paper-validation, and paper-benched rows write their own role-scoped namespaces
**When** a projection would aggregate rows across account roles without an explicitly-declared cross-role read
**Then** the aggregation is a `policy rejection` refusal; only the two declared exceptions (the decay-cohort read and a multi-role entity projection) may span roles, each carrying `role` on every row, and no write ever crosses roles (FM-11, DEC-0145, DEC-0158).

**AC4**
**Given** the legacy five Records streams — `veto_ledger`, `trade_journal`, `book_journal`, `ksa_audit_log`, `correlation_ledger` — survive as projection names only
**When** one is resolved
**Then** it maps onto the seven journal event types through the one versioned CT-25 mapping table with no second event catalog minted, and `veto_ledger` selects on the `decision` event's `outcome = refused-by-door`, never on key presence (DEC-0145, DEC-0158).

## Epic 4: qmf-calendar-forex extension

The first CT-02 calendar provider ships as its own extension package — a
forex market-hours calendar (`forex-17NY`) that lives in the workspace but
outside the seven-package roster, on its own SemVer ladder, with `tzdata`
pinned and verified at import, so results stay identical across server moves,
DST shifts, and tzdata updates. (FR-021; CT-02; AR-02, AR-27)

### Story 4.1: Extension package scaffold with pinned tzdata and import-time tzdb verification

As the factory developer,
I want the `qmf-calendar-forex` extension scaffolded under `extensions/` on its own SemVer ladder with exactly one pinned `tzdata` version that is forced and verified at import,
So that the calendar can never attest a fingerprint against a tzdb version it did not actually resolve.

**Acceptance Criteria:**

**Given** the greenfield uv workspace from Epic 1 with its `packages/` roster and `extensions/` tree
**When** the extension is built with uv_build
**Then** `qmf-calendar-forex` builds from `extensions/qmf-calendar-forex/` in src/ layout with its own pyproject.toml, carrying a SemVer version independent of the roster's lockstep ladder
**And** it ships no `qmf/__init__.py` and is not published inside the `qmf.*` roster namespace (FM-5 boundary)
**And** it declares exactly one pinned `tzdata` package version as a dependency (AR-27)

**Given** the extension is imported into a process
**When** the package initializes
**Then** it forces the timezone path (TZPATH) to its pinned `tzdata` and reads the resolved tzdb version
**And** when the resolved tzdb version equals the pin, the CT-02 calendar provider becomes ready and exposes both its rule-set identity and the resolved tzdata version for downstream fingerprints

**Given** the resolved tzdb version does not equal the pinned `tzdata` version at import
**When** the package initializes
**Then** it returns an `unavailable dependency` typed refusal and does not become a usable provider, and no fingerprint is attested against the unverified tzdb (FM-1)

**Given** the maintainer changes the pinned `tzdata` version
**When** the extension is re-released
**Then** the change is at minimum a minor version bump on this extension's own SemVer ladder (AR-27)

### Story 4.2: Forex-17NY market-hours calendar provider implementing CT-02

As a framework consumer,
I want a CT-02 calendar-provider implementation that answers only forex market-hours questions — a 17:00 America/New_York accounting rollover plus a session schedule with weekend gaps and holidays,
So that trading dates and open-session windows derive from a versioned rule set rather than from formatting an instant.

**Acceptance Criteria:**

**Given** the verified provider from Story 4.1
**When** it is asked which trading date an instant belongs to
**Then** it applies the accounting rollover at 17:00 America/New_York and returns a `TradingDate` carrying this calendar's identity (`forex-17NY`) and rule-set version in-band (CT-02)
**And** it never derives the trading date by formatting an instant to a local date (FM-3 refuses that path as unsupported)

**Given** the provider is asked when the market is open
**When** it evaluates the session schedule
**Then** it models weekend gaps and the extension's pinned holiday set, and treats session length and trading-day length as data, never assuming them constant
**And** Swap-Wednesday is not modeled (V1 accounts are swap-free; the extension models neither swap nor dated financing)

**Given** two `TradingDate` values produced under different calendar identities
**When** a caller compares them for equality
**Then** the cross-calendar comparison returns a typed refusal; equality is defined only within one calendar identity (FM-2)

**Given** the extension is asked an accounting-boundary (day-boundary) or news-event question
**When** the request reaches the provider
**Then** it refuses as out of authority — this is a market-hours calendar only, and the day-boundary and news calendars are separate named kinds (FM-4)

**Given** any fingerprint is required for a calendar-derived artifact
**When** the fingerprint is computed
**Then** only the rule set plus the pinned `tzdata` version participate in it, computed by the single canonical `fp1` implementation in qmf-core; the extension computes no fingerprint of its own

### Story 4.3: Explicit composition-root registration, identity participation, and authority-boundary conformance

As the factory developer,
I want the forex calendar registered explicitly at the application composition root through the named surface — never by ambient package scanning — with its distribution identity carried into every derived artifact,
So that which calendar is in force is an explicit, auditable wiring decision and a tzdata change surfaces as a new fingerprint rather than a silent rewrite.

**Acceptance Criteria:**

**Given** an application wiring its calendar providers
**When** the forex calendar is made available
**Then** it is injected via explicit registration at the composition root through the named surface, never discovered by ambient scanning of installed packages
**And** the extension's distribution identity and version are recorded so both, alongside the rule set and pinned tzdata version, ride into downstream fingerprints

**Given** a trading date previously derived under one pinned `tzdata` version
**When** the same instant is re-derived after the extension's `tzdata` pin changes
**Then** the exposed calendar identity differs, so the derived artifact carries a new, distinct fingerprint rather than a silent equality — the earlier artifact is never rewritten (the composition root records the lineage edge between them)

**Given** a change that alters only the calendar's binding (which venues or accounts use it) without changing the rule set
**When** derived-artifact identities are compared
**Then** they are unchanged — binding is separate from the rule-set identity that participates in fingerprints

**Given** the extension's conformance test suite
**When** it runs at the Tier-2 gate
**Then** any attempt by the extension to define a shared noun (Venue, Account, Instrument, WriterId, TradingDate) fails conformance — those are defined only in qmf-core and consumed here (FM-5)

## Epic 5: qmf-data — backup, restore & verify

Nightly encrypted off-machine backup with verify-backed recoverability claims. This epic delivers the CT-26 store-to-backup input and the CT-14 encrypted versioned off-machine copy, a restore primitive that still enforces the seal and world isolation, the verify primitives that are the only source of a recoverability claim, and the application-owned nightly off-machine cycle per AR-34 — with QMF owning the primitives only. Covers FR-014. Builds on Epic 3 (the store seam and its seven per-world room-roles).

### Story 5.1: Store-to-backup input and encrypted versioned off-machine copy

As the factory developer,
I want the store to present each room-role's records as a consistent restorable input and the backup primitive to produce an encrypted, versioned off-machine copy,
So that every room-role including the registry room can be carried off-machine without ever mutating the only copy.

**Acceptance Criteria:**

**AC1**
**Given** COMP-QMF-DATA-STORE presents one room-role's records per world through the CT-26 input seam, read as an unlimited reader under one-writer-per-stream
**When** the backup primitive consumes that input
**Then** the read never mutates evidence, the input covers every room-role including the registry room under one retention/backup/migration law, and int64 UTC nanosecond timestamps pass through verbatim, never re-derived under a later calendar identity or tzdata version (DEC-0118, DEC-0113, DEC-0106).

**AC2**
**Given** COMP-QMF-DATA-BACKUP owns the CT-14 off-machine boundary
**When** it produces a backup copy
**Then** the copy is encrypted and versioned, each off-machine copy is a new versioned artifact, and a backup never mutates the only copy (DEC-0118).

**AC3**
**Given** a CT-26 read would cross worlds or read `world = simulated`
**When** the backup input is requested
**Then** it is a `policy rejection` refusal, since storage separation delivers world isolation (FM-1, DEC-0117, DEC-0110).

**AC4**
**Given** object storage is unreachable, rejects the upload, or the copy is corrupt
**When** the CT-14 transfer is attempted
**Then** no completion is claimed and the boundary returns a `storage failure` typed refusal, never raised across the boundary (FM-2, DEC-0109, DEC-0118).

**AC5**
**Given** encryption is required but the object-storage provider, object-key layout, numeric RPO/RTO/retention targets, and encryption key custody are node/ops-sitting items
**When** the primitive is built
**Then** it carries the encryption-required pointer without baking in a provider selection or credential, and embeds no credential in evidence (DEC-0118, DEC-0045, AR-37).

### Story 5.2: Restore primitive with seal and world-isolation enforcement

As the operator,
I want to restore a backup into a replacement store without ever rewriting the only good copy, and with the seal and world isolation still enforced on the restored data,
So that a restore recovers evidence honestly and can never become a back door around the 12-month seal or cross-world isolation.

**Acceptance Criteria:**

**AC1**
**Given** a versioned off-machine copy exists
**When** it is restored into a replacement store
**Then** the restore never rewrites the only copy in place — each off-machine copy stays a distinct version — and restored int64 UTC ns timestamps are preserved verbatim, never re-derived under a later calendar identity or tzdata version (DEC-0118, DEC-0106).

**AC2**
**Given** restored backups still enforce the 12-month seal exactly as a live read does
**When** a read against restored data touches the sealed holdout
**Then** the sealed rows are refused as a `policy rejection`, identical to a live read (FM-4, DEC-0119).

**AC3**
**Given** rooms are instantiated per world
**When** a restore read crosses worlds, or a restore would write `world = simulated` into governed evidence
**Then** each is a `policy rejection` refusal (DEC-0117, DEC-0110).

**AC4**
**Given** a retention action during restore would delete the only local raw evidence copy
**When** it is attempted
**Then** the deletion does not proceed under this component's authority; raw originals and lineage are kept forever (FM-5, DEC-0118).

### Story 5.3: Verify primitives — sample-restore and full-restore rehearsal

As the operator,
I want recoverability proven only through automated sample-restore tests and a periodic full-restore rehearsal,
So that a recoverability claim never rests on a snapshot alone and a migration never mutates the only copy.

**Acceptance Criteria:**

**AC1**
**Given** verification is a first-class primitive, not an optional add-on
**When** recoverability is assessed
**Then** it is claimed only through the ratified verify primitives — automated sample-restore tests plus a periodic full-restore rehearsal — and is never asserted from a snapshot alone (SCN-0004, DEC-0118).

**AC2**
**Given** a sample-restore or full-restore rehearsal runs
**When** the restored copy is read back
**Then** verification confirms the restored evidence against a documented restore path, and a corrupt or failed restore yields no recoverability claim — the boundary returns a `storage failure` refusal rather than reporting success (DEC-0109, DEC-0118).

**AC3**
**Given** a migration must never mutate the only copy
**When** a migration runs
**Then** it proceeds as preflight checks → backup-first → dry-run → migrate → verify against a documented restore path, never an in-place mutation of the only copy (AR-32, DEC-0118).

**AC4**
**Given** numeric restore-verification cadence, RPO, RTO, and retention depth are node/ops-sitting items
**When** the primitive is built
**Then** it exposes the sample-restore and full-restore rehearsal as first-class operations without filling `registry:restore_verification_cadence`, `registry:backup_recovery_point_objective`, `registry:backup_recovery_time_objective`, or `registry:backup_retention_period` from a recommendation (SCN-0004, DEC-0118).

### Story 5.4: Application-owned nightly off-machine cycle

As the operator,
I want the backup, restore, and verify primitives wired into a nightly encrypted off-machine cycle to object storage that the application drives,
So that copies land off-machine every night per AR-34 while QMF stays primitives-only and refuses to own the schedule.

**Acceptance Criteria:**

**AC1**
**Given** the ratified topology — the trading-node VPS records and syncs down, the workstation holds the working archive, and the bucket catches nightly copies
**When** the application drives the cycle
**Then** it runs the CT-14 encrypted versioned copy off-machine to object storage on the `registry:backup_cadence` = nightly cadence, and runs automated sample-restore plus periodic full-restore rehearsal as part of the cycle (AR-34, DEC-0118).

**AC2**
**Given** QMF provides the primitives while the schedule and execution are application/ops-owned
**When** a caller asks COMP-QMF-DATA or COMP-QMF-DATA-BACKUP to own the nightly schedule or a numeric RPO/RTO
**Then** the request is refused as outside the component boundary — the boundary provides the primitive only (FM-6, FM-9, DEC-0118, DEC-0051).

**AC3**
**Given** the cycle backs up every room-role including the registry room, all per world
**When** the nightly cycle runs
**Then** a cross-world backup read is a `policy rejection` refusal and no `world = simulated` room is carried into governed evidence (DEC-0117, DEC-0110).

**AC4**
**Given** a copy would be transferred while encryption key custody is unresolved
**When** the transfer is attempted
**Then** the boundary carries the encryption-required pointer, no credential is embedded in evidence, and key custody remains a node/ops-sitting item (FM-7, DEC-0118, AR-37).

## Epic 6: qmf-data — source intake

External data arrives idempotently: the CT-15 adapter seam, Dukascopy tick history, and the news-calendar feed. This epic delivers the CT-15 external-source seam owned by COMP-QMF-DATA-INGEST with idempotent `(source, source-native id, revision)` intake translated into CT-10 producer values, the bid/ask preservation and source-disagreement edges that keep conflicting sources visible, the Dukascopy download-once historical tick adapter under its personal-use licensing posture, and the news-calendar feed ingested as a governed source with fail-closed degradation. Covers FR-015, FR-017, FR-018. Builds on Epic 3 (the CT-10 boundary, seven rooms, and journal streams).

### Story 6.1: CT-15 adapter seam and idempotent intake

As the factory developer,
I want the Data-Ingest middleware seam to own and call the CT-15 external-source port and translate provider responses into CT-10 producer values under idempotent intake,
So that every external provider enters through one seam, a provider revision is a new artifact rather than a collision, and no downstream library ever calls a provider directly.

**Acceptance Criteria:**

**AC1**
**Given** COMP-QMF-DATA-INGEST is the QMF owner and caller of CT-15, and COMP-QMF-DATA does not accept CT-15
**When** a bounded request is sent to an active provider and a response returns
**Then** the seam validates and normalizes it and submits CT-10 producer observation values to the Data-owned CT-10 boundary — application-routed, creating no package dependency on qmf-data (DEC-0117, DEC-0119, DEC-0120).

**AC2**
**Given** intake is idempotent keyed on `(source, source-native id, revision)`
**When** a duplicate, out-of-order, or corrected record arrives
**Then** a provider revision is admitted as a new artifact with its own fp1 fingerprint — never an fp1 collision — and earlier evidence is never erased or silently merged (FM-3, DEC-0119, DEC-0108).

**AC3**
**Given** foreign timestamps and foreign money must survive as evidence
**When** a provider payload is normalized
**Then** the foreign timestamp is stored verbatim with its declared zone, offset, and resolution, and foreign money verbatim as scaled integers at the source's declared scale, with conversions to framework Time and Money derived under lineage and corrections appended, never overwritten (DEC-0106, DEC-0105).

**AC4**
**Given** a source record lacks event-time, known-at, source key, revision, or a CT-03 instrument mapping
**When** admission is attempted
**Then** no valid CT-10 observation is emitted and the seam returns an `invalid input` typed refusal (FM-2, FM-6, DEC-0109, DEC-0117).

**AC5**
**Given** an external source is unavailable or rate-limits a request
**When** the call fails
**Then** the seam emits no fabricated observation and returns a `transient venue failure` or `unavailable dependency` typed refusal, and a read-only `source` is never conflated with a tradeable `VenueId` (FM-1, FM-7, DEC-0109, DEC-0107).

**AC6**
**Given** scheduling, retries, supervision, and UI are application-owned
**When** a caller asks the seam to operate a scheduler, daemon, process supervisor, or retry loop
**Then** the request is refused as outside the component; the seam is a called port, not a running downloader (FM-5, DEC-0051, DEC-0119).

### Story 6.2: Bid/ask preservation and source-disagreement edges

As a framework consumer,
I want tick sources separately identified with bid and ask preserved and disagreements kept visible via typed lineage edges,
So that two sources are never silently merged into one number and a disagreement stays inspectable rather than being averaged away.

**Acceptance Criteria:**

**AC1**
**Given** tick sources are separately identified (for example Dukascopy history versus a future broker feed)
**When** tick observations are recorded through the CT-15 seam into CT-10
**Then** bid and ask are preserved separately with their source timestamps kept, and are never merged into a single mid value (DEC-0119, DEC-0105).

**AC2**
**Given** two sources report the same fact
**When** their observations are recorded
**Then** agreement is captured with a `corroborates` typed lineage edge and disagreement with a `disagrees-with` edge — the disagreement stays visible and is never merged away (FM-3, DEC-0119).

**AC3**
**Given** each source keeps its own identity and revisions
**When** a later revision of a source fact arrives
**Then** it is keyed under the idempotent `(source, source-native id, revision)` intake as a new artifact and linked to the earlier one, never overwriting it (DEC-0119, DEC-0108).

### Story 6.3: Dukascopy download-once historical tick adapter

As the operator,
I want Dukascopy wired as the first historical tick source under a download-once, personal-use licensing posture with every window license-tagged,
So that I load history once under my own provider relationship into the immutable raw archive, and an unlicensed window can never silently become governed evidence.

**Acceptance Criteria:**

**AC1**
**Given** Dukascopy is an active external CT-15 provider and the acquisition posture is download-once
**When** the historical corpus is acquired
**Then** it is pulled a single time under the user's own provider relationship into the QMF immutable raw archive, runs never fetch from providers, and every accepted record retains its external source identity and is converted into CT-10 by the ingest seam (AR-54, DEC-0166, DEC-0053).

**AC2**
**Given** every ingested window records provenance plus a license tag, with the Dukascopy personal-use posture ruled closed for personal backtesting (DEC-0170)
**When** a source window without a recorded usage right is offered for governed-evidence use
**Then** it is a typed refusal — an unlicensed window can never silently become governed evidence — and the per-window license-tag mechanism stays in force unchanged (AR-54, DEC-0166, DEC-0170).

**AC3**
**Given** a record is malformed, missing required timestamps, or cannot map to a source-qualified CT-03 instrument
**When** intake is attempted
**Then** the seam does not admit it as valid evidence and returns an `invalid input` refusal from the seven-category taxonomy (FM-2, DEC-0038, DEC-0109).

**AC4**
**Given** the D1 build-our-own law and `dukascopy-node` as a reference-only shape, never adopted code
**When** the downloader is built
**Then** no donor code enters the tree, and a request to bulk-download the complete corpus during documentation or a factory feature pass is refused as outside the component — only bounded adapter evidence is permitted until installation/runbook execution (FM-5, DEC-0166, DEC-0013, DEC-0051).

**AC5**
**Given** raw originals and lineage are kept forever, partitioned by source, instrument, and time window
**When** a bounded transfer stops or the source is unavailable
**Then** QMF cannot require external recovery; checkpoint, retry, and operator-visible refusal live in the standalone application that owns scheduling and supervision (FM-1, DEC-0051, DEC-0118, DEC-0119).

### Story 6.4: News-calendar feed as a governed source with fail-closed degradation

As the operator,
I want the news-calendar feed ingested as a governed CT-15 source that keeps provider-native identity and revisions, journals every import, and degrades visibly when a refresh fails,
So that economic-event evidence stays honest and append-only, and a failed refresh surfaces as a fail-closed signal rather than being mistaken for permission to trade.

**Acceptance Criteria:**

**AC1**
**Given** COMP-CALENDAR-FEED is an active external CT-15 provider consumed by the standalone news-calendar recorder (a distinct concept from the market-hours calendar and the day-boundary calendar)
**When** event records and revisions are ingested
**Then** the recorder keeps the provider's native event identity and revisions through the idempotent `(source, source-native id, revision)` intake, each revision a new artifact and corrections appended, never overwriting prior evidence (FM-2, DEC-0052, DEC-0119, DEC-0117).

**AC2**
**Given** provider impact labels are stored verbatim and QMX mints no severity scale of its own in V1
**When** an event is recorded under the recorder's own WriterId
**Then** it carries event-time, known-at, source, and revision as source evidence, and the feed defines no window and holds no permission — the risk-side blackout is CT-31's, derived from this evidence (DEC-0152, DEC-0117).

**AC3**
**Given** every import is journaled
**When** the recorder runs an import
**Then** the import is journaled as a `data quality` event in the ratified CT-13 journal, not an invented format (FR-018, DEC-0119).

**AC4**
**Given** a failed calendar refresh, unknown coverage, or a missing per-instrument currency-exposure record must fail closed (SCN-0008)
**When** a refresh fails
**Then** the outage degrades visibly — journaled as a `data quality` event and alarmed — and is treated-as-affected downstream (blocks new entries at the CT-31 boundary), with no live skip button; the feed itself supplies no permission (FM-4, DEC-0065, DEC-0152).

**AC5**
**Given** licensing and long-term retention rights for the news feed are unresolved
**When** the recorder ingests
**Then** it does not claim operational retention is authorized; the legal archiving posture stays an open operator item, recorded not resolved (FM-3, FM-4, DEC-0119, DEC-0052).

## Epic 7: qmf-indicators

Batch and streaming indicators with guaranteed equivalence over TA-Lib
canonical arithmetic — one CT-16 contract whose two modes compute the same
numbers by construction, with as-of-only alignment for governed evidence, a
conformance harness, and a first wrapper set. (FR-019; CT-16; AR-49)

### Story 7.1: qmf-indicators package scaffold and the CT-16 configured-indicator identity

As the factory developer,
I want the roster package scaffolded and the CT-16 configured-indicator declaration record whose `fp1` fingerprint is the entire declared configuration,
So that every indicator has one deterministic dedup identity and no configuration element can silently drift out of it.

**Acceptance Criteria:**

**Given** the Epic 1 workspace with qmf-core available
**When** `qmf-indicators` is built
**Then** it builds from `packages/qmf/indicators/` in src/ layout, versions in the roster SemVer lockstep, and its pyproject.toml declares every dependency
**And** at the Tier-2 isolated-environment gate it imports only qmf-core — any undeclared or sibling import fails (default-deny, AR-06)
**And** public value types are frozen dataclasses and public seams are `typing.Protocol`

**Given** a configured indicator declaration
**When** its `fp1` is computed by the single qmf-core fingerprint function
**Then** identity spans the entire declared configuration — formula id, contract format version, exact-rational parameters, the ordered named input set, calendar requirements including tzdata version, alignment and missing-value policies, warm-up, output schema, supported modes, and the arithmetic-reference configuration
**And** two configurations differing in any one identity element receive distinct `fp1` values, and that `fp1` is the only dedup key

**Given** a configuration that omits a required identity element from the fingerprint
**When** the conformance test runs
**Then** it is a contract defect and the test fails (an element missing from the fingerprint is a contract defect)

**Given** a parameter expressed as a binary float
**When** the configuration is validated
**Then** it is refused — parameters are exact rationals only (scaled integers or numerator/denominator pairs); binary floats never appear in parameters or identity

### Story 7.2: TA-Lib canonical arithmetic wrapping with the reference-configuration record asserted at import

As the factory developer,
I want TA-Lib pinned as lockfile-resolved artifacts with an identity-bearing reference-configuration record asserted at import, and mandatory wrapping wherever TA-Lib implements a formula,
So that canonical arithmetic is provably the arithmetic used and no governed producer re-implements a formula the reference already owns.

**Acceptance Criteria:**

**Given** the canonical reference `registry:canonical_indicator_reference`
**When** the package resolves it
**Then** it is TA-Lib (C 0.7.1 + Python wrapper 0.7.1) pinned as lockfile-resolved artifact hashes (distribution filename plus hash) with an identity-bearing reference-configuration record (AR-49)

**Given** the package is imported
**When** it asserts the reference-configuration record
**Then** if the resolved artifacts differ from the lockfile pin, or the reference's process-global configuration differs from the reference-configuration record, it returns an `unavailable dependency` refusal at import — the fingerprint must never attest arithmetic that was not used (FM-2)
**And** the package never mutates the reference's process-global configuration at runtime

**Given** a formula that TA-Lib implements
**When** a governed producer supplies that formula
**Then** wrapping the reference is mandatory and it is canonical; a wrapper that re-implements the formula is a contract defect and fails conformance (FM-5)

**Given** a formula the reference does not implement (volume-weighted, session-anchored, QMX-original)
**When** it is supplied
**Then** this package's implementation is the canonical arithmetic under the identical upgrade gate

**Given** any CT-16 boundary
**When** a value crosses it
**Then** no TA-Lib or other vendor object appears in any signature or output — the public surface stays package-neutral, returning CT-04 refusals without exposing dependency-specific objects (FM-5)

### Story 7.3: Batch mode with as-of-only alignment and presence-mapped outputs

As a framework consumer,
I want a batch mode over whole series producing full-length, index-aligned, presence-mapped outputs under as-of-only alignment,
So that research computes governed numbers with no silent filling, no NaN, and no look-ahead across the evaluation instant.

**Acceptance Criteria:**

**Given** an input series supplied by the application (CT-10 source observations aggregated to a declared BarSpec by qmf-data)
**When** a batch configuration computes over it
**Then** outputs are full-length and index-aligned to the input with begin-index trimming prohibited; every position carries a `registry:presence_map_states` value; NaN and sentinel markers are prohibited
**And** the indicator receives its BarSpec as data and never derives bar boundaries itself

**Given** governed evidence is being produced
**When** a value must be aligned to an evaluation instant
**Then** only as-of alignment (last value known at or before the instant) is permitted; forward-fill or interpolation across the evaluation instant returns a `policy rejection` refusal (FM-1)

**Given** a position where the market-hours calendar says closed
**When** the output is presence-mapped
**Then** the position is `absent_by_schedule`, never a gap; a calendar-open position with no data follows the declared missing-value policy, never silent filling

**Given** the warm-up window for a configuration
**When** output samples are produced during warm-up
**Then** warm-up is an integer count of completed input observations in the input's own sample unit (never ticks, never a Duration), at least the reference's lookback, and during warm-up the output is a marked not-ready value, never a number
**And** every output sample carries a knowable-at instant, and provisional samples never enter governed evidence

### Story 7.4: Streaming mode, the tier-2 equality law, and restore-equivalence

As a framework consumer,
I want a streaming mode over incremental updates whose numbers are provably equal to batch, with versioned snapshot/restore,
So that the live path and research compute the same values by construction and streaming state can be resumed without drift.

**Acceptance Criteria:**

**Given** a configuration declaring streaming mode
**When** a streaming instance is created
**Then** it is the one named stateful class — exactly one feeder (one WriterId holder) and unlimited readers — exposes `health()`, and every streaming output carries the input sequence number that produced it
**And** instance count scales with distinct configurations, not consumers

**Given** a configuration declaring both batch and streaming modes
**When** the equality law runs as a Tier-2 contract test
**Then** streaming and batch results are equal same-process, same-build, under a per-configuration integer-ULP comparator (default 0), over canonical inputs = (series, exact parameters, cold initial state), with the seeding rule and leading-undefined-prefix-to-not-ready mapping declared
**And** cross-OS or cross-build agreement is never this gate — it is a separate registered comparison artifact

**Given** a streaming state snapshot
**When** it is restored and advanced by N updates
**Then** the result equals cold-warm-then-the-same-N-updates (restore-equivalence); the snapshot is a serialized contract with its own format version scoped to a declared (OS, arithmetic-reference build) tuple, and a result from restored state carries the snapshot fingerprint as an input fingerprint

**Given** a snapshot restored on a different (OS, arithmetic-reference build) tuple
**When** restore is attempted
**Then** it returns an `unavailable dependency` refusal (FM-7)

### Story 7.5: Conformance harness, light/heavy benchmark budgets, and the explicit catalog surface

As the factory developer,
I want the CT-16 conformance harness bound to the concept-walk register, the light/heavy benchmark harness, and the one named catalog surface for extension registration,
So that conformance is enforced at Tier 2, light claims are benchmark-proven, and extensions register explicitly rather than by scanning.

**Acceptance Criteria:**

**Given** the CT-16 conformance register
**When** the conformance suite runs at Tier 2
**Then** it keeps the register's concept-walk list expressible — multi-instrument and multi-BarSpec input sets, derived-series chaining, non-time bar kinds, calendar-scoped windows and calendar-anchored sampling, projected outputs under knowable-at, batch-only statistical methods, price-valued outputs re-entering the money path via the named boundary, and delta-typed price differences

**Given** the benchmark harness with the same standing as unit tests
**When** it measures a configuration
**Then** it records two rungs — burst throughput and per-tick latency per accepted input observation at the configured BarSpec, with the no-op tick path measured separately — and a peak-memory regression fails the Tier-2 gate exactly as a slowdown does

**Given** a configuration claiming light without a recorded live-path rung baseline, or whose benchmark misses a declared bound
**When** the light claim is evaluated
**Then** it is refused at the Tier-2 gate; every configuration is heavy by default, and a heavy configuration's synchronous entry point returns `unsupported capability` (FM-3, FM-6)

**Given** an indicator extension registering into an application
**When** it is made available
**Then** discovery is explicit registration at the composition root through the one named catalog surface — never ambient scanning — and the extension's distribution identity and version are mandatory fields in every artifact it produces (FM-8)

**Given** a concept the framework cannot yet articulate as a governed configuration
**When** a researcher needs it
**Then** it is authorable as plain Python outside governed evidence, and it enters governed evidence only by graduating through the CT-16 extension shape with a lineage edge back to its originating research artifact (L33)

### Story 7.6: First wrapper set of TA-Lib-backed configured indicators

As a framework consumer,
I want a first set of concrete CT-16 configured indicators wrapping canonical TA-Lib formulas, each proving equality and warm-up discipline,
So that the platform ships working, governed, school-neutral indicators with executable tests and reference usage.

**Acceptance Criteria:**

**Given** the CT-16 protocol, canonical wrapping, and both modes from Stories 7.1–7.4
**When** the first wrapper set is delivered
**Then** each is a configured indicator wrapping a TA-Lib formula where the reference implements it, declared in both modes where applicable, with warm-up at least the reference's lookback
**And** no trading-school name appears in any rule or vocabulary (school concepts enter only as mechanically stated capability terms)

**Given** each configuration declaring both modes
**When** its Tier-2 tests run
**Then** it passes the equality law at the declared integer-ULP tolerance and its restore-equivalence test

**Given** each wrapper as a public contract
**When** the package is assembled
**Then** each ships executable tests and reference-usage examples as Tier-1 artifacts

**Given** an upgrade to the canonical reference that changes output for identical canonical inputs
**When** the comparison suite runs before the upgrade lands
**Then** it catches the change, which mints the per-configured-indicator contract format version with recorded before/after evidence — never a silent accept and never a protocol-wide bump (FM-4)

## Epic 8: qmf-venue port + cTrader adapter

Commands and events cross one venue-neutral port under the four-outcome law, defined on qmf-core nouns and implemented by per-venue adapters wired at the composition root; cTrader is adapter #1, and the platform stays venue-blind above the port.

### Story 8.1: cTrader capability probe against the live demo venue

As the factory developer,
I want to connect to the live cTrader demo venue with only qmf-core nouns and operator-approved demo credentials, run the first-connection verification suite, and record a venue-observation profile,
So that venue feasibility is proven against the real API before any port contract is built on paper, and the measured findings can amend upstream assumptions.

**Acceptance Criteria:**

**Given** only qmf-core nouns (identity, exact values, injected time, typed refusals) and operator-approved demo credentials are available, and no other Epic 8 story has landed,
**When** the probe runs,
**Then** it connects to the cTrader demo host (a throwaway transport over the pinned Spotware proto release tag 91) and executes the named verify-or-refuse checks — spot-timestamp-unit assertion, daily-boundary measurement, bar-basis reconciliation, pip-formula validation, money-exponent presence — recording each measured fact and verdict into a per-(VenueId, account) venue-observation profile.
**And** the probe stands alone: it depends on no port contract, connection manager, or Epic 3 journal, so it can run as the earliest factory work unit (FR-022, FR-026, SC-02, AR-45).

**Given** the probe measures the D1 daily-bar boundary and the trendbar price basis,
**When** it records them,
**Then** both are stored as per-broker configuration in the venue-observation profile, and neither the 17:00-New-York boundary nor the BID basis is hardcoded anywhere in the probe (AR-46, DEC-0135).

**Given** a verify-or-refuse check cannot pass (the spot-timestamp unit is unasserted, or a money exponent is absent),
**When** the probe reaches that check,
**Then** it records the check as unverified/refused rather than defaulting any value, and the dependent evidence class stays unavailable — an unmeasured daily boundary leaves venue daily bars ungoverned (AR-45, edge).

**Given** the probe holds demo credentials,
**When** it uses or logs them,
**Then** the credential value is never rendered (only its reference id appears), and no live host is contacted and no order is submitted (FR-025, AR-37, SC-02).

**Given** the probe completes,
**When** it reports,
**Then** its output is the recorded venue-observation profile plus a findings note whose contradictions with upstream assumptions are surfaced for amendment (SC-02).

### Story 8.2: In-house proto compilation pinned at Spotware release tag 91

As the factory developer,
I want the Spotware openapi-proto-messages compiled in-house and pinned at integer release tag 91, with the protobuf runtime scoped as a qmf-venue-only dependency,
So that the adapter owns its own transport, zero Spotware SDK code runs, and a proto tag change becomes a governed re-verification event rather than a silent update.

**Acceptance Criteria:**

**Given** the AD-6 dependency register,
**When** the venue protocol artifact is pinned,
**Then** it names the Spotware openapi-proto-messages integer release tag 91, and only the proto message definitions (data, not code) are consumed (AR-43, FR-026, DEC-0141).

**Given** the official OpenApiPy SDK carries a pinned Twisted reactor that violates the platform-imposing ban,
**When** the adapter transport is built,
**Then** the SDK is reference-only, no Spotware code executes in QMX, and the protobuf runtime is declared a dependency of qmf-venue alone (AR-43, AR-06).

**Given** the pinned tag is 91,
**When** the tag is changed,
**Then** the change mints a new CT-18 capability declaration and forces re-verification, and bumps a CT-* format version only where the wire change alters that contract's public shape (AR-43, DEC-0141, edge).

**Given** a compiled proto message,
**When** it is used,
**Then** it never leaks into qmf-core: default-deny holds, qmf-venue imports only qmf-core, and nothing imports qmf-venue (AR-06, AR-42).

### Story 8.3: Secret lifecycle, connection manager, and injected-sink wiring

As a framework consumer,
I want a connection manager that is the sole holder of venue sessions and secret values, fed by a composition-root-injected SecretStore port and calling injected core sink protocols synchronously,
So that credentials never leave the connection manager, never render, and every persistence failure is seen by the writer that holds the WriterId.

**Acceptance Criteria:**

**Given** qmf-core's typed SecretRef and SecretValue,
**When** a SecretValue is repr'd, str'd, serialized, or logged,
**Then** it yields only its opaque reference id and never the value, and the tier-1 secret-scan gate rides poe check (FR-025, CT-21, AR-37, NFR-05).

**Given** the connection manager holds the WriterId (machine, adapter role, VenueId, account) and receives an injected SecretStore port (read + atomic replace),
**When** any component other than the connection manager attempts to hold a secret value or construct a venue client,
**Then** it cannot — the connection manager is the single value-holder, and no secret crosses back out through a getter, log line, refusal context, health field, or metric label (FR-025, CT-21, AR-37).

**Given** a rotation where the venue rotates refresh material on use,
**When** the new secret arrives,
**Then** it is stored via atomic replace before the old is discarded; a failed store after rotation is an unavailable-dependency alarm plus a command-pipe block (after-condition = successful store or operator re-provision), the sensing pipe unaffected (FR-025, AR-38, CT-21, edge).

**Given** a missing, expired, or rejected credential,
**When** it is encountered,
**Then** an unavailable-dependency refusal carries the reference id, never the value; an account-binding record's secret reference is occurrence/display-only and excluded from fp1, and a non-opaque reference construction is an invalid-input refusal (CT-21, edge).

**Given** the composition root injects the qmf-core sink protocols (ObservationSink, JournalSink, RecordSink, SecretStore),
**When** the connection manager calls a sink and it returns a storage-failure refusal,
**Then** the writer-holding component blocks the command stream, the sensing pipe is unaffected, and no store is ever written directly rather than through an injected sink (AR-47, CT-21).

### Story 8.4: Two-artifact capability discovery and the first-connection verification suite

As a framework consumer,
I want venue capabilities carried as two artifacts — a static credential-free declaration plus a per-(VenueId, account) venue-observation profile produced post-connect — wired in a fixed order,
So that a caller learns exactly what a venue supports before invoking it, and no measured-but-unverified capability ever enters evidence-bearing work.

**Acceptance Criteria:**

**Given** the capability declaration,
**When** it is imported,
**Then** it is static, adapter-version-scoped, and credential-free, carries the venue protocol artifact identity (tag 91), marks every field static or measured-at-connection, and its fingerprint is identity-bearing for any decode that depends on it (FR-022, CT-18).

**Given** the fixed wiring order,
**When** the adapter is constructed,
**Then** the declaration is present at construction and the venue-observation profile must exist before the first command and before any evidence-bearing decode; a measured-at-connection capability consumed before its profile exists is an unavailable-dependency refusal (FR-022, CT-18, AR-45, SC-09).

**Given** a measured-but-unverified capability,
**When** it is consumed in evidence-bearing work,
**Then** the result is a policy-rejection refusal; the venue-observation profile is append-only with supersedes edges and is occurrence/provenance-only, never identity-bearing downstream (CT-18, edge).

**Given** a caller invokes an undeclared capability or an unsupported close scope (account | account-binding | instrument-within-binding),
**When** the adapter receives it,
**Then** it returns an unsupported-capability refusal and never emulates the capability or widens the scope (CT-18, edge).

**Given** an unmapped venue error code,
**When** the error map is consulted,
**Then** the fail-closed default applies — (transient venue failure, retryable = no, outcome = UNKNOWN) plus an alarm — and a code reads as rejected-by-venue only where the pinned error-map row declares that class (CT-18, edge).

**Given** a measured daily boundary is verified,
**When** it is minted,
**Then** it becomes a venue-scoped market-hours calendar identity anchoring venue-native BarSpec, while a failed bar-basis reconciliation refuses bar evidence and an absent money exponent refuses that message's money decode (CT-18, AR-46).

### Story 8.5: Five typed command kinds under the four-outcome law

As a framework consumer,
I want exactly five typed command kinds on qmf-core nouns, each submission resolving to exactly one of four outcomes with uncertainty recorded as a state,
So that the platform stays venue-blind above the port and no outcome is ever assumed, retried, or invented.

**Acceptance Criteria:**

**Given** the command vocabulary,
**When** a command is constructed,
**Then** it is exactly one of place_order, cancel_order, close_position, close_all, amend_protection — typed per kind on qmf-core nouns with no free-form payload; kinds are addable, never redefined, and a fractional or partial close is an unsupported-capability refusal (FR-023, CT-19, AR-44).

**Given** a well-formed submission,
**When** it resolves,
**Then** it resolves to exactly one of accepted-by-venue, rejected-by-venue, denied-locally, or UNKNOWN; denied-locally is an outcome and never a refusal, and every outcome mints an observation record and a journal event (FR-023, CT-19).

**Given** a transport error, timeout, or disconnect intervenes before a final outcome,
**When** the outcome is decided,
**Then** it is UNKNOWN — a state, not an error — and a venue-returned error resolves rejected-by-venue only where the CT-18 error table declares that class; a timeout is never read as a rejection (FR-023, CT-19, edge).

**Given** command identity is the command record's fp1 (stream qualification, session epoch, ordering ordinal),
**When** the CT-18 mapping into the venue client-id field is not injective-and-total,
**Then** a durable command-id-binding record persists through the injected sink before submission; re-presenting the same command is an idempotent accept, and differing content under a reused identity is refused and alarmed (CT-19, AR-48, edge).

**Given** amend_protection,
**When** a change is submitted,
**Then** it is constrained at contract level to risk-non-increasing changes per protection side (the stop side checked against the frozen original_risk_distance), and it is never emulated by cancel-then-place nor widened into a general amend_order (CT-19, edge).

**Given** a compound command fanning out to N venue submissions,
**When** its children resolve,
**Then** the parent outcome is the meet of its children — any child UNKNOWN makes the parent UNKNOWN, and any child rejected makes the parent partially-executed, a named outcome that is never a success (CT-19, edge).

### Story 8.6: Record-before-interpret events and on-demand reconciliation

As a framework consumer,
I want every inbound venue event stored verbatim and journaled before any interpretation, order state derived as a read-time fold, and reconciliation as an on-demand read-back whose verdict gates only the command pipe,
So that no state machine ever gates the immutable store and market data keeps flowing while commands reconcile.

**Acceptance Criteria:**

**Given** an inbound venue event,
**When** it arrives,
**Then** it is stored verbatim (with mandatory receive wall time and boot-scoped monotonic stamp) and journaled before any state evaluation, and a fill observation's price, quantity, venue instant, and receive instant are mandatory identity fields (FR-024, CT-20, AR-47).

**Given** the order-state machine,
**When** state is needed,
**Then** it is a read-time fold over the observation stream and never a stored field; command outcome and order state are separate streams, and a terminal state is decided only by fills and venue lifecycle events, never inferred from a command outcome or from absence alone (CT-20).

**Given** an observation with no legal transition,
**When** it is recorded,
**Then** it is annotated with a typed out-of-sequence edge and forces its owning command to UNKNOWN; adapters never synthesize a venue observation to paper over the gap (CT-20, edge).

**Given** a multi-room write (raw archive, journal, registry room),
**When** it executes,
**Then** it completes as one ordered unit with a named transaction boundary (atomic or ordered-with-recovery); a partial write is a storage-failure refusal that blocks the command stream and is journaled on recovery (CT-20, AR-47, edge).

**Given** an on-demand reconciliation read-back over a mandatory declared lookback,
**When** it produces a verdict,
**Then** the verdict is one of reconciled, drift, unknown, or out-of-lookback — the fourth so "I cannot see that far back" is never read as "the position closed" — and it gates the command pipe only, never the sensing pipe (FR-024, CT-20, SCN-0005).

**Given** a close_position, close_all, or amend_protection whose subject is observed terminal at or after the submit stamp,
**When** it resolves,
**Then** it resolves rejected-by-venue (superseded-by-terminal-subject) — a named outcome, never UNKNOWN, never a stream block — and a subject absent or already terminal at submission resolves without submission (CT-20, edge).

### Story 8.7: UNKNOWN blocks the command stream until explicit reconciliation

As the operator,
I want an UNKNOWN submission to block new commands on its (venue, account) stream until an explicit resolve_unknown call, with any refused risk-reducing act preserved as a standing intent,
So that the system never assumes, retries, flattens, or invents a terminal state on uncertainty, and protection never evaporates.

**Acceptance Criteria:**

**Given** a submission resolves to UNKNOWN,
**When** it is minted,
**Then** it is an explicit observation carrying its trigger (timeout | transport-error | disconnect), the monotonic elapsed measurement, the wall receive instant, and the injected submission deadline in force — whose existence is mandatory but whose value is never QMF's (FR-023, SCN-0005, CT-19).

**Given** an outstanding UNKNOWN on a (venue, account) stream,
**When** a new command arrives on that stream,
**Then** the adapter refuses it (transient-venue-failure, after-condition = resolution); the adapter never clears its own block, and no component retries, assumes an outcome, flattens, or invents a terminal state (FR-023, SCN-0005, L35).

**Given** a protection command is refused by the block,
**When** the block later clears,
**Then** the protection act never evaporates — it stands as a standing protection intent, journaled before dispatch, re-decided (explicitly not retried) against a reconciled verdict only, while drift, unknown, and out-of-lookback verdicts alarm and hold it open without dispatching (SCN-0005, edge).

**Given** cancel_order, close_position, close_all, and amend_protection share a throttle with place_order,
**When** they are pending,
**Then** the risk-reducing kinds dispatch ahead of place_order on every shared throttle, and suspend-new takes local effect instantly with no venue round-trip (SCN-0005, CT-19).

**Given** the application resolves an UNKNOWN,
**When** it calls resolve_unknown(command identity, resolution),
**Then** the resolution is one of observed-accepted, observed-absent, or operator-attested, the call is itself recorded as an observation, and the block clears on that resolution — never on a reconciliation verdict alone (SCN-0005, CT-19, edge).

### Story 8.8: cTrader adapter honoring the ratified venue facts as per-broker configuration

As the factory developer,
I want the cTrader adapter to honor the ratified venue facts as standing obligations while treating the daily boundary, trendbar basis, and broker identity as per-broker/deployment configuration,
So that cTrader is adapter #1 behind the venue-neutral port with no broker-specific behavior baked into code.

**Acceptance Criteria:**

**Given** the ratified venue facts,
**When** the adapter decodes inbound values,
**Then** it honors per-field Unix-ms UTC timestamps with mandatory receive-time recording (no server clock exists), the 1/100000 market-data wire scale, execution prices as raw doubles crossing the named money-path boundary, and a moneyDigits exponent on the nine money-bearing messages — an absent exponent refusing that message's money decode (FR-026, AR-46, DEC-0135).

**Given** the connection limits,
**When** the adapter paces itself,
**Then** it respects 50 requests/second non-historical plus 5/second historical per connection, adopts the 10-second heartbeat bound, and enforces the one-week historical tick-span cap; demo and live are separate hosts requiring two simultaneous connections (AR-46, DEC-0135).

**Given** the ~30-day access token and never-expiring refresh token (the crown-jewel secret, cTID re-authorization the invalidation anchor),
**When** the adapter runs session duties,
**Then** heartbeat, token refresh, reconnect, gap replay, and verification monitors are declared schedulable duties the application's scheduler drives, and session recovery never resubmits a command (AR-46, FR-025).

**Given** the 17:00-New-York daily boundary and BID-derived trendbars are 2013-forum-grade claims,
**When** the adapter needs them,
**Then** it measures each per broker at first connection, re-verifies with a continuous monitor, and stores the result as per-broker configuration in the venue-observation profile — never hardcoded (FR-026, AR-46, edge).

**Given** which broker fronts the platform is deployment configuration,
**When** the adapter is deployed,
**Then** opaque VenueId/AccountId identity and account bindings suffice, no broker is named in code, and the platform stays venue-blind above the port (FR-026, AR-46, AR-42).

## Epic 9: qmf-structure

Market structure as causal, append-only, look-ahead-safe chart-object
families — objects minted once at observation, evolved only through
append-only lifecycle and interaction records, carrying knowledge time and
evidence class as identity, so repainted or look-ahead structure can never
enter governed evidence. (FR-020; CT-17)

### Story 9.1: qmf-structure package scaffold, object mint, and the emission invariant

As a framework consumer,
I want the roster package scaffolded and CT-17 structure objects minted once at observation under an in-component emission invariant,
So that every object is an immutable, causally-justified fact whose ordering is checked before it can enter evidence.

**Acceptance Criteria:**

**Given** the Epic 1 workspace with qmf-core available
**When** `qmf-structure` is built
**Then** it builds from `packages/qmf/structure/` in src/ layout, versions in the roster SemVer lockstep, imports only qmf-core in V1 (any undeclared import fails the Tier-2 isolated-environment gate), and its public value types are frozen dataclasses with `typing.Protocol` seams

**Given** an object is minted
**When** it is created at observation
**Then** it is minted once carrying family identity plus version, exact-rational parameters, its declared confirmation rule, its anchor span (frozen at observation, permitted to precede observed-at, excluded from every causality test), and observed-at (the earliest instant the object was derivable from causally-available data — known-at, never event time)
**And** the object is never mutated afterward, and anchor span, observed-at, and every lifecycle instant are identity fields, never occurrence-classified

**Given** an emission
**When** the in-component emission invariant is checked
**Then** it requires `anchor.start ≤ anchor.end ≤ observed-at ≤ confirmed-at ≤ invalidated-at` and `observed-at ≥` the maximum evidence time of every input actually consumed; a violation returns an `invalid input` refusal (FM-1)
**And** the library returns fingerprintable content and never stamps records — the composition root holds the WriterId and the gapless per-(writer, kind) sequence

### Story 9.2: Append-only lifecycle — confirmation, invalidation, interaction, and read-time state

As a framework consumer,
I want confirmation, invalidation, and interaction expressed only as append-only records with current state resolved as a read-time fold,
So that structure state evolves without any object or edge ever being overwritten and refits never rewrite history.

**Acceptance Criteria:**

**Given** a minted object
**When** its state evolves
**Then** confirmation, invalidation, and interaction records are separate append-only typed records/edges referencing the object's fingerprint, each instant an identity field of its own record; interaction records are the only permitted way an object's state evolves
**And** "still valid at T" is a read-time fold over the object's edge stream per CT-17's read-resolution rule, never a stored field

**Given** a correction, refit, or state change that would overwrite an object or an edge
**When** it is attempted
**Then** it is prohibited: interaction records append, and a refit mints a new artifact with a `supersedes` edge, anchors frozen at each fit, the lineage head keeping the first observed-at, and earlier evidence remains (FM-3)

**Given** a family whose confirmation rule cannot state "confirmed the moment X happens" with X knowable at that instant
**When** it is offered to the governed library
**Then** it is not admitted; the concept stays freely usable in the ungoverned research lane (FM-2); clock-confirmed (degenerate) confirmation is legal

**Given** a family with an invalidation predicate referencing a parent's lifecycle facts
**When** a parent is invalidated
**Then** invalidation never cascades automatically; the reader may compute cascade at read time from lineage

### Story 9.3: Evidence class, knowledge-time provenance, and split-manifest governance

As the operator,
I want evidence class and knowledge time to be first-class identity, with split partitioning by confirmed-at and a confirmed-read refusal,
So that unconfirmed or look-ahead structure can never leak into confirmed governed evidence or across a split boundary.

**Acceptance Criteria:**

**Given** a structure result
**When** its evidence class is recorded
**Then** evidence class (`confirmed | unconfirmed | provisional`) is a declared identity field and a named part of the result label; an unconfirmed output links to its confirmed successor via a typed `confirmed-as` edge
**And** a read requesting confirmed evidence refuses unconfirmed rows with a `policy rejection`, never a silent filter (FM-4)

**Given** a decision at instant T
**When** it consumes structure evidence
**Then** it may consume evidence with `confirmed-at ≤ T` — equality is consumption, not look-ahead; refuse-at-equal governs causality tests between derived artifacts, not consumption

**Given** a family's declared confirmation-delay bound (an integer count of observations at the family's BarSpec)
**When** records partition into splits by knowledge time (confirmed-at)
**Then** the bound feeds the split manifests' required purge/embargo widths; a manifest refuses any record whose observed-at precedes a boundary while its confirmed-at follows it, unless the declared embargo covers the gap (FM-7)
**And** an unbounded confirmation-delay declaration is legal only for families excluded from split-governed evidence

**Given** an object computed on a revised input
**When** its result label is produced
**Then** it receives a different result label through its input fingerprints rather than silently changing; the label carries producer contract identity, format version, input fingerprints, evidence time range, evidence class, and world

**Given** a structure object used only in memory versus one cited by a journal event or result label
**When** governance is evaluated
**Then** live in-memory use persists nothing, but any object cited by a journal event or result label becomes governed evidence by that act and is persisted; scanners run ungoverned and promote only confirmed objects
**And** the full look-ahead/causality registration gate (CT-08) remains deferred to the backtesting sitting (GAP-0016); the in-component emission invariant is the interim guard, not that gate

### Story 9.4: First causal family, the CT-17 conformance harness, and light/heavy benchmarks

As the factory developer,
I want a first governed family from the seed candidates, the CT-17 conformance harness bound to the concept-walk register, and the light/heavy benchmark harness,
So that the library ships a working, unprivileged family proving the lifecycle while conformance and budgets are enforced at Tier 2.

**Acceptance Criteria:**

**Given** the seed family candidates (`registry:structure_seed_family_candidates`)
**When** the first governed family is delivered
**Then** it is one seed candidate (a swing-point family) whose confirmation rule is precise — "confirmed the moment X happens" with X knowable at that instant — consuming source/bar observations as declared inputs
**And** it holds no privilege over operator-authored families, which are first-class peers under identical law, and no trading-school name appears in any rule or vocabulary (FM-9)

**Given** the CT-17 conformance register
**When** the conformance suite runs at Tier 2
**Then** it keeps the register's concept-walk list expressible — retro-anchored zones with consumption state, objects born from another object's invalidation, cluster objects over tolerance-grouped extremes, threshold-breach-then-reversal objects, ordered multi-phase calendar composites, multi-BarSpec nests, cross-instrument divergence objects, distribution-over-price objects, a-priori price grids, projected levels, and pattern refits

**Given** the routing test
**When** a family needs a per-evaluation-instant value
**Then** a value per evaluation instant is CT-16 and a discrete object with a birth and a lifetime is CT-17; a family needing an indicator consumes it as a declared input through the composition law, never re-implemented inline (FM-6)

**Given** the benchmark harness with the same standing as unit tests
**When** a family's budget is evaluated
**Then** its rungs are active object-set size, objects minted per bar, and interaction records per bar; a light claim exceeding a declared bound (or lacking a baseline) is refused at the Tier-2 gate, and a peak-memory regression fails exactly as a slowdown does (FM-8)

**Given** a concept a family cannot yet state precisely
**When** a researcher needs it
**Then** it stays freely usable in plain Python outside governed evidence, entering governed evidence only by graduating through the extension shape with a lineage edge to the originating experiment (L33)

## Epic 10: qmf-risk — Books, BMS & governance

Every bot trade intent passes a Book's charter doors; the BMS accounts for and constrains its Books but never trades, sizes, or reaches inside a Book; exits are Book-owned and preserved; and performance measurement publishes and never acts. Every contract here is defined on qmf-core nouns, imports only qmf-core, is imported by nothing, and stays defined-unwired — records reach the registry and qmf-data only through the composition root, and no live binding, order, mode transition, or flatten is authorized outside the factory pipeline.

### Story 10.1: Template grammar, the dimensional law, and the USD numeraire

As a framework consumer,
I want Book and BMS definitions expressed as structured configuration artifacts under one grammar, every variable carrying a unit-kind, an exact-rational value, a UI-editable flag, and an admission-impact, with USD as the sole V1 numeraire,
So that a governed artifact's meaning lives inside its identity, a UI can tell what it may change, and no risk number is ever a hardcoded spine constant.

**Acceptance Criteria:**

**Given** a Book or BMS template,
**When** a variable is declared,
**Then** it carries a unit-kind from the closed vocabulary (money(currency) | price-delta(instrument) | quantity(unit) | value-factor(instrument, currency) | r-multiple | rate(money-per-r) | count | dimensionless-ratio | duration | instant), an exact-rational or scaled-integer value with no binary float, a ui-editable | uneditable flag, and an admission_impact of resign | relint | none; a variable missing any of the four is an invalid-input refusal (FR-035, CT-22, CT-27, L38).

**Given** the dimensional law,
**When** a formula is declared,
**Then** it declares the unit-kind of every input and its output, a symbolic checker refuses on mismatch, and every formula ships an executable worked example recomputed at Tier 2; the dead FORM-0006 is retained as the suite's permanent negative test (CT-22, L38).

**Given** configurable means UI-editable at platform level,
**When** a variable is edited in the settings UI,
**Then** the edit mints a new version and never mutates one, and any recorded corpus or recollection number attached to a variable is evidence with a stated source layer and authority grade, never a ratified constant or spine value (FR-035, CT-22, L38).

**Given** the numeraire,
**When** any risk, sizing, or window value is expressed,
**Then** it is USD system-wide in V1, accounting_currency is declared so a later currency is a version change, and a Book-level limit stated in an instrument-native quantity (lots) is a policy rejection at template validation (FR-035, CT-22).

**Given** versioning is git-logic-without-git,
**When** a template changes,
**Then** it appends to a branches-from version graph (multiple heads legal; current is a separate dated pointer), supersedes stays linear elsewhere, every old version stays readable forever, and a changed number changes fp1 hence a new identity (CT-22, CT-27).

**Given** the module is qmf-risk,
**When** it is packaged,
**Then** it defines CT-22 and CT-27 on qmf-core nouns, imports only qmf-core, is imported by nothing, and records reach the registry through the composition root — a ratified defined-unwired contract from which no wiring is authorized (AR-06, CT-22, CT-27).

### Story 10.2: R faces, the sizing ladder, and the full-loss-price law

As a framework consumer,
I want R expressed as one relationship with three typed faces frozen at admission, the units-only sizing ladder, and a mandatory declared full-loss price before any open,
So that sizing is R-denominated and exact, R never re-bases, and a strategy with no planned loss point cannot trade in QMX.

**Acceptance Criteria:**

**Given** R,
**When** a position is admitted,
**Then** R is three typed faces — original_risk_distance (PriceDelta(instrument)), original_risk_amount (Money(numeraire)), and r_multiple (dimensionless exact rational, −1 a full original loss, 0 breakeven) — and both money-bearing faces are frozen at admission and never re-based by a stop move, a protection amendment, or a budget re-derivation (FR-028, CT-23).

**Given** an entry,
**When** it is admitted,
**Then** it must resolve to a declared full-loss price — no price, no original_risk_distance, no admission, an invalid-input refusal — and V1 admits no scale-in, so adding to an open position is a policy rejection (FR-028, CT-23, edge).

**Given** the sizing shape,
**When** money_rules is declared,
**Then** it carries units only with no ratified values — book_capital, loss_floor (the same number the kill line names, read by both), loss_runway = book_capital − loss_floor, period_loss_budget, r_unit_price, seat_loss_run_allowance, seat_r_ceiling ≤ seat_loss_run_allowance, and position_risk_amount = requested_r × r_unit_price frozen at admission (FR-028, CT-22).

**Given** the legacy symbol B did two unrelated jobs,
**When** bench and sizing variables are declared,
**Then** the B-split holds — bench_consecutive_loss_threshold [count] in leash_grammar and seat_loss_run_allowance [r_multiple] in money_rules — and the unit-kind checker refuses a count standing where an r_multiple is declared (CT-22, edge).

**Given** a value-factor (money per price-delta per quantity) is needed,
**When** it is sourced,
**Then** it comes only from venue instrument-metadata snapshots as an exact rational; an absent value factor is an unavailable-dependency refusal and never a silent conversion, and V1 never sizes by margin (CT-23, edge).

**Given** a Money↔R crossing,
**When** it occurs,
**Then** it names a rate (r_unit_price = Money per r_multiple); an implicit crossing refuses, and only r_multiple averages across instruments and accounts (CT-23).

### Story 10.3: Three-layer admission, the admission bar, and blank-blocks-live

As the operator,
I want a Book or BMS to prove itself in exactly three ordered layers ending in my signature, with the admission bar a set of pass/fail requirements whose blank thresholds block live money,
So that nothing reaches live money without a human signature and no composite score or paper-role evidence can gate a live binding.

**Acceptance Criteria:**

**Given** admission,
**When** a Book or BMS is admitted,
**Then** it passes strictly three ordered layers — Layer 1 machine linters at registration, Layer 2 technical shakedown on a demo/paper binding, Layer 3 one operator signature on one assembled page carrying both proofs, the binding identity, and the resolved BMS fingerprint — with no trial period, probation window, or paper-performance gate (FR-027, SC-12, CT-22).

**Given** the admission bar,
**When** a requirement is declared,
**Then** it carries an opaque measure_identity, a mandatory unit, a comparison (at-least | at-most | within-band), and a threshold as a discriminated union ruled(exact-rational) | not-yet-ruled(gap-ref) with the key always present; no composite score, rating, tier band, or weighted aggregate may express a bar (CT-22, FR-035).

**Given** a bar holds any not-yet-ruled threshold or pending slot,
**When** the Book binds,
**Then** it registers and binds to non-live roles freely, and binding to a role = live account is a policy rejection — blank blocks live money while allowing registration and non-live binding (FR-035, CT-22, L38).

**Given** an evidence_requirements.account_role naming a paper role,
**When** it appears in a bar that gates a live binding,
**Then** it is a policy rejection at Layer 1, so this field can never rebuild the paper-performance gate admission exists to forbid (CT-22, edge).

**Given** Layer 1 worked-example arithmetic and control-rank checks,
**When** they run,
**Then** worked examples are recomputed by invoking the cited producer contracts themselves (never linter-local arithmetic), unit-kind coverage is enforced on every declared variable, and two control-action kinds sharing a rank is an invalid-input refusal (CT-22, CT-27, edge).

**Given** a float-valued measure compared to an exact-rational threshold,
**When** the comparison runs,
**Then** it crosses the named analytic→exact boundary under a comparison rule declared in the requirement itself (target scale, rounding mode, tie disposition); an undeclared comparison is an invalid-input refusal (CT-22, edge).

### Story 10.4: The binding chain, identity trinity, and bind-time capability check

As the operator,
I want a Book bound to exactly one BMS on one account at one venue as a dated append-only binding record carrying the identity trinity and a per-counter state_carry, admissible only when the venue's declared and measured capabilities satisfy it,
So that the risk domain aligns with the command stream, a rule change never moves money by accident, and a capability shortfall refuses at bind time rather than at trade time.

**Acceptance Criteria:**

**Given** the risk domain,
**When** a binding is minted,
**Then** it is the tuple (BookInstanceId, BmsInstanceId, VenueId, AccountId, world), aligned with the (VenueId, account) command stream and never coarser; role is deliberately not in the tuple (it rides the per-intent execution-target record), a Bot binds exactly one Book, a Book binds exactly one BMS at a time, and one BMS per account serves many Books (FR-031, FR-027, CT-28, CT-27).

**Given** the identity trinity,
**When** identities are minted,
**Then** a Book version is template fp1, a Book instance is an operator-minted deployment record, and a binding epoch is the binding record's own fingerprint (populations cite fingerprints, never intervals); a binding record fingerprinting equal to an existing one is an invalid-input refusal, never a silent idempotent accept (CT-28, edge).

**Given** every binding record,
**When** it is minted,
**Then** it carries a mandatory complete per-counter state_carry declaration (ledger, cycle, budget, bench_counter, exposure — each carry | reset); carry is legal only under an accompanying human-signed carries-ledger edge, while a continues-performance edge asserts a track record but moves no money, and neither edge is inferred from the other (CT-28, FR-031).

**Given** the bind-time capability check,
**When** a binding is attempted,
**Then** it resolves against CT-18's declaration and the venue-observation profile — required venue capabilities, settlement currency matching the Book's accounting_currency, shared-flatten signature where netted, a present SQS baseline for every sensor the Book's doors read, a live-path rung baseline, and a non-contradicting control-rank table — and any shortfall refuses at bind time, never at trade time (FR-027, CT-28).

**Given** a settlement currency that does not match the Book's accounting_currency (non-USD in V1),
**When** a binding is attempted,
**Then** it is a policy rejection at bind time — no rate source is ratified and a silent conversion is the one error no report shows (CT-28, edge).

**Given** a second Book bound onto a netting account whose live bindings may trade an overlapping instrument set,
**When** the binding is attempted,
**Then** it is an unsupported-capability refusal unless the operator signs the shared-flatten limitation (an identity field of the binding); one Book per netted account is the confirmed default (CT-28, edge).

### Story 10.5: Paper as a dated binding-epoch change

As the operator,
I want a Book's flip to paper expressed as a dated change of its execution binding that mints a new binding epoch, routing intents to one paired demo target while identity, track record, and the money boundary stay intact,
So that paper is a standing evidence state, never a new object and never a way around a control.

**Acceptance Criteria:**

**Given** Book modes are exactly LIVE | PAPER,
**When** a flip occurs,
**Then** it is a dated change of the Book's execution binding minting a new binding epoch — never a new Book, never a Bot twin — appended to the CT-24 stream, and current mode is a read-time fold over that stream and never a stored field; a mode-field write naming a seat or binding-state word is an invalid-input refusal (FR-029, CT-24, SCN-0006).

**Given** routing is separated from binding,
**When** an intent is minted,
**Then** its per-intent execution_target is resolved once from (Book mode, seat state, active-control set) and enters the command record's identity; PAPER selects the paired target without changing the binding identity, so one intent never produces two submissions and a mode flip never replays a command (CT-24, SCN-0006).

**Given** one active paper-routing target per live binding at an instant,
**When** the target is resolved,
**Then** exactly one is resolved (re-pointable by a superseding dated record); no resolvable target makes the paper transition an unavailable-dependency refusal, and live trading is unaffected (CT-24, edge).

**Given** every trigger kind declares a mandatory disposition,
**When** a control fires,
**Then** routes-to-paper covers capital or authority reasons (a kill-line stand-down, a benched seat) and blocks-paper covers market-risk reasons (a protection window, the kill switch); what continues under any control is the recording, and recording is not trading (CT-24, FR-033).

**Given** paper money is frozen evidence,
**When** a paper epoch is set,
**Then** the starting balance is a configurable UI-editable default frozen at flip and never hand-adjusted; a reset mints a new operator-signed paper_epoch_reset record with a fresh balance and a lineage edge, the running balance never mutated, and paper P&L never crosses the money boundary (CT-24, FR-035).

**Given** return to live,
**When** a Book returns,
**Then** it is automatic only where the clearing cause is clocked and mechanical (minting a CT-24 transition, never a CT-30 resume); anything touching real money requires an operator signature, and paper performance never authorizes a return (CT-24, edge).

### Story 10.6: The risk-evaluation door — Book-resolved sizing and risk-monotonic intents

As an agent,
I want one inbound door carrying two typed intent families through which I propose while the Book resolves, sizes, admits, or refuses with a recorded reason,
So that a bot never sizes, never widens risk, and its own exit methodology can be honored without ever inverting the authority order.

**Acceptance Criteria:**

**Given** the door,
**When** an intent is submitted,
**Then** it is exactly one of two families — entry or exit — plus declared evidence slots and nothing else; requested_r is Book-resolved, and an inbound requested_r is an invalid-input refusal because the bot may not size (FR-028, CT-23).

**Given** an entry intent,
**When** it is admitted,
**Then** it carries instrument, direction, an advisory proposed_r, a typed reason code, the execution target, and its cited evidence slots (CT-23 format 1); the declared full-loss price is derived at the Book door by the Book's per-family ExitLogicRef consuming the intent's cited evidence, stamped exactly as requested_r is resolved — no Book module is ever injected into bot logic (FR-028, CT-23).

**Given** exit intents,
**When** they are proposed,
**Then** the only V1 kinds are close_full and tighten_protective_stop, each with a typed reason_code; close_partial is an unsupported-capability refusal, and a tighten_protective_stop names a direction and a bound, never a price (FR-032, CT-23).

**Given** a risk-monotonic violation,
**When** an intent widens a stop, extends a target beyond the Book's declared envelope, re-opens a closed position, or increases size,
**Then** it is a policy rejection (CT-23, edge).

**Given** a bot that carries its own exit or stop methodology,
**When** the Book declares the adopt-the-bot's-advisory-stop ExitLogicRef module mode,
**Then** the mode exists in the ExitLogicRef mode registry with its input contract declared as the CT-23 format-2 `entry.advisory_stop_proposal` field (minted by the QML increment, Story 11.7, per SC-05),
**And** invoking the mode while CT-23 sits at format 1 returns an `unavailable dependency` refusal — requested_r stays Book-resolved and R stays frozen in every mode (CT-23; SC-05).

**Given** CT-22 and CT-23 at contract format version 1,
**When** a future format-2 mint adds optional fields (carried by the QML increment, Story 11.7),
**Then** format-1 artifacts stay readable forever and an unknown optional field never breaks a format-1 consumer (AD-5; CT-22, CT-23, edge).

### Story 10.7: Exit records, close reasons, whole-trade attribution, and the bench fold

As the operator,
I want exactly one immutable exit record per virtual-position close carrying frozen R faces and a typed close reason, with the qualifying-loss bench computed as a read-time fold,
So that whole-trade attribution and the leash read the same recorded dataset and the system's own protection never benches the bot it just protected.

**Acceptance Criteria:**

**Given** a virtual (Book) position close,
**When** it completes,
**Then** it mints exactly one CT-29 exit record — the Book-side noun, never the venue position — carrying the frozen original_risk_distance and original_risk_amount, fill references, realized_pnl, an identity-bearing cost_components set, a single-sourced realized_r (a derived display of the record's frozen fields, never a second implementation of the division), the close reason, the closing_authority plus arbitration reference, and the account-binding role (FR-032, CT-29, SCN-0011).

**Given** the close reason,
**When** it is stamped,
**Then** it is exactly one member of the taxonomy (protective_stop_fill | target_fill | protection_amendment_fill | bot_intent | hold_time_force_flat | boundary_flat | window_forced_flat | protection_forced_flat | kill_line_flat | venue_liquidation | venue_initiated_close | operator_close) with mechanism and outcome as separate fields, and kill_line_flat is minted apart from protection_forced_flat (CT-29).

**Given** whole-trade attribution,
**When** a virtual position closes,
**Then** its full realized R credits the Bot that opened it regardless of who closed it — no counterfactual, no apportionment — and reports partition by close reason so the bot's edge and what the gates cost read as one dataset two ways (FR-032, CT-29).

**Given** the bench,
**When** exits accumulate,
**Then** it counts qualifying-loss exits (realized_r ≤ −q) as a read-time fold over the exit-record stream bounded by the binding epoch; scratches and partial losses do not count by default, and a breakeven never counts under any q (recorded as its own metric) (CT-29, SCN-0011).

**Given** recording precedes interpretation,
**When** a later intent is minted on the same (Book, Bot) seat,
**Then** the closing exit record must be persisted and journaled first, else that intent refuses (stale evidence), so the (N+1)th entry never races the Nth exit record (CT-29, edge).

**Given** the protective stop and the breakeven ratchet,
**When** a stop is moved,
**Then** it moves only in the risk-non-increasing direction measured against the frozen original_risk_distance (V1 dynamic SL/TP is the move-to-breakeven ratchet only), and R stays frozen so −1R keeps meaning a full original loss (CT-29, CT-23).

### Story 10.8: Control actions — exit-preservation, kill switch vs kill line, and same-tick rank arbitration

As the operator,
I want a bounded set of typed control actions arbitrated at exactly one point per command stream by a BMS-declared rank, with the exit-preservation invariant guaranteeing no control ever blocks a risk-reducing act,
So that the kill switch and kill line stay distinct, a 3am kill-line breach never waits for me, and de-escalation is always my call.

**Acceptance Criteria:**

**Given** the exit-preservation invariant,
**When** any control action of any authority at any scope is applied,
**Then** it may never block a risk-reducing act — cancel_order, close_position, close_all, a risk-non-increasing amend_protection, a protection action, or the recording of evidence — the blocking half of any control is entries only in paper and live alike, and no kind whose effect is a blanket command-pipe block may ever be minted (FR-033, CT-30, L39, SCN-0010).

**Given** the action vocabulary,
**When** an action is issued,
**Then** it is exactly one of suspend_new, drain, flatten, resume (each defined once), carrying an issuing authority kind (operator | book_policy | protection_authority | venue-delegated | adapter_self), a subject scope resolved through a pinned versioned table (an unresolvable or netting-indistinguishable scope refuses, never widened), and a satisfaction predicate with suspend_new and drain never-auto by rule (CT-30, FR-033).

**Given** a protection action,
**When** it is issued,
**Then** it is journaled before dispatch as a standing intent (a read-time fold, restart-proof), re-decided rather than retried on reconnect, never time-expiring, and satisfied by flatten only on a reconciled verdict showing the scope flat — drift, unknown, and out-of-lookback alarm and hold the intent open without dispatching (CT-30, SCN-0005).

**Given** the kill switch and the kill line are two different things,
**When** each fires,
**Then** the kill switch is the global black-swan authority stopping all new trading everywhere (live and paper), escalating automatically and de-escalating only by a human, while the kill line is a per-Book capital floor whose breach automatically flattens that binding's scope and stands the Book down; resume is operator-only (CT-30, FR-033).

**Given** same-tick actions on one (VenueId, account) stream,
**When** they collide,
**Then** they arbitrate at exactly one point by the BMS-declared rank table (one per stream, a total order unique at Layer 1): colliding actions collapse to one command with the rank winner supplying authority and reason and each loser journaling as suppressed; mutually exclusive commands let the higher rank win outright; composing effects (suspend_new + flatten) both execute; and a higher rank never reduces the protection a lower rank would deliver (CT-30, SCN-0010).

**Given** flatten authority,
**When** a flatten is initiated,
**Then** only the operator (unconditional, any scope), Book policy (through pre-declared trigger classes only), and the protection authority (where node severity policy declares close_all) may flatten — never the venue adapter, a sensor, or a Bot — and every other money boundary (rollover, sweep, re-seed, paper flip) leaves positions alone (CT-30, edge).

### Story 10.9: Protection windows — entries-only, instrument-scoped, fail-closed

As the operator,
I want one control-window contract covering news, daily dead zones, and session handover buffers, each blocking new entries only on the instruments in scope, live and paper alike, resolved by declared currency exposure and failing closed,
So that a window reduces risk without trapping it, never blocks an exit, and never lets an uncertain window silently pass.

**Acceptance Criteria:**

**Given** one control-window contract,
**When** a window record is minted,
**Then** it carries the window as two instants (never an offset), a resolved instrument scope, a window kind (news | daily_dead_zone | session_handover_buffer, with session_handover_buffer declaring its anchor side pre-close | post-open | both), a reason class, a format version, and the external-fact quadruple (source, source-native event id, revision, known-at) where feed-derived (FR-033, CT-31, SCN-0008).

**Given** a window in force,
**When** a bot proposes an entry on an in-scope instrument,
**Then** the window blocks the new entry — live and paper alike — and blocks nothing else (never an exit, a protection amendment, a protection action, or observation); the blocked decision is journaled on the veto path carrying the refusing door, the would-have-been action, and the window fingerprint (FR-033, CT-31, SCN-0008).

**Given** instrument scope is declared, never parsed,
**When** scope resolves,
**Then** it resolves through dated per-instrument currency-exposure records; a missing record means the instrument is treated as affected and blocked (the absence journaled as data quality and alarmed), and a multi-instrument bot is blocked only on the instruments in scope (CT-31, SCN-0008, edge).

**Given** a later revision,
**When** it arrives,
**Then** enforcement is widen-never-shrink and forward-only — a revision may pull a start earlier for instants not yet passed or push an end later, never narrow, cancel, or retro-invalidate a window that has had effect — and the effective window at a decision instant is a read-time union fold with passed bounds frozen (CT-31, edge).

**Given** a failed calendar refresh, unknown coverage, or an uncertain window,
**When** a decision is made,
**Then** it fails closed and blocks; there is no live skip button, and a standing per-instrument exemption is a dated fingerprinted record consumed at compile time, never a click (CT-31, edge).

**Given** whether a window ever closes open positions,
**When** a Book declares it,
**Then** window_forced_flat enters arbitration at rank 2 (declaring none is the V1 posture), and widths, anchors, and buffers are configurable UI-editable variables with no spine value (CT-31, FR-035).

### Story 10.10: Risk journals as read-time projections and publish-never-act performance

As the operator,
I want entity journals delivered as read-time projections over writer-scoped streams and every performance result carried in one publish-never-act container with suppression and veto accounting,
So that my logbook reconstructs any Book, BMS, or bot without any entity owning a stream, and no composite score ever gates money.

**Acceptance Criteria:**

**Given** entity journals,
**When** the operator's logbook is read,
**Then** the Book journal, BMS journal, and per-bot journal are read-time projections over writer-scoped streams selected by entity identity — an entity holds no WriterId and mints no stream — and the legacy five Records names (veto_ledger, trade_journal, book_journal, ksa_audit_log, correlation_ledger) survive as projection names mapped onto the seven event types by one versioned table (FR-030, CT-25).

**Given** two event classes,
**When** events are minted,
**Then** risk-authored events (decision, risk transition, control action, promotion) carry the Book-definition fingerprint and binding identity, venue-authored events (order, fill, data quality) carry the command record's content fingerprint, and the projection joins them through the pinned versioned command-fingerprint join — never by threading Book identity into a venue payload (CT-25, edge).

**Given** the risk dispatcher,
**When** a control action is journaled before dispatch,
**Then** a storage failure blocks the dispatch rather than losing the intent, and paper and live projections resolve inside one role-scoped namespace with role carried on every row — a cross-role read is explicitly declared, never a silent union (CT-25, edge).

**Given** the performance-result container,
**When** a result is published,
**Then** it carries the full result label plus account-binding role, a fingerprinted population (binding-record fingerprints, never intervals), a declared period with a knowledge-time bound, an ordered measure set with a unit-kind on every emitted quantity, and both suppression accounting (by authority and reason) and veto accounting (by door) (FR-034, CT-32).

**Given** measurement publishes and never acts,
**When** a measure is produced,
**Then** no score, rating, tier band, or weighted composite may express a result, a single result may never span account roles (a multi-role result is a policy rejection), and the authority to act on a published measure belongs to the Book door (bench) or the operator (promotion) (FR-034, CT-32).

**Given** benching is a read-time fold,
**When** the bench fold publishes a crossing,
**Then** it is one governed producer published once and consumed by the Book door, and a replay-world result (world = replay) can never gate live money (FR-034, CT-32, edge).

## Epic 11: QML authoring

Governed bots and confluences are authorable as two-artifact declarations with exact identity and versioning: a CT-33 Bot definition plus plain-Python logic (FR-047), with confluence definitions authored as CT-34 artifacts (FR-049). This epic scaffolds the `qml` library, mints the strategy-family, footprint, confluence, and Bot-definition author surfaces on QMF nouns, and carries the CT-22/CT-23 format-version-2 parent mints the QML increment depends on (SC-05).

### Story 11.1: Scaffold the qml bot-authoring library

As the factory developer,
I want the `qml` distribution scaffolded per the Structural Seed — one uv-installable, pure, library-only package with no CLI that imports only qmf-core, qmf-registry, and qmf-risk —
So that every later QML story lands in a fixed module home that is import-legal, never touches qmf-venue, and never gates a plain-Python bot's tunnel entry (FR-047, QL-1, AR-60, AR-10).

**Acceptance Criteria:**

**Given** the uv workspace from Epic 1
**When** `uv add qml` resolves and `import qml` runs
**Then** qml installs as one wheel outside the seven-package roster, adding no new runtime dependency beyond the `qmf-*` packages it consumes
**And** the distribution carries its own SemVer as display-only provenance that never enters any `fp1`

**Given** the Structural Seed
**When** the package is scaffolded
**Then** it contains exactly the module homes `declaration/`, `families/`, `footprint/`, `protocol/`, `conformance/`, `examples/`, `tests/`, and ships no CLI entry point (no `console_scripts` — QMB's `qmb` CLI is the single command-line surface)
**And** `conformance/` is pure — it spawns no process and performs no I/O

**Given** the dependency stance (AR-60)
**When** pyright-strict and the Tier-2 isolated-environment import check run
**Then** qml imports qmf-core, qmf-registry, and qmf-risk only
**And** any import of qmf-venue fails the gate

**Given** AD-15 purity
**When** the ambient-nondeterminism scanner scans any qml module
**Then** qml spawns no thread, performs no I/O, and spawns no process
**And** every impure step (registration writes, sandbox execution) is left to a host composition root

**Given** a plain-Python bot with zero qml imports
**When** it runs in QMB or a research lane
**Then** it executes unchanged, because conformance is never required for tunnel entry
**And** the `.qml` DSL and its Monaco surface are not revived in V1

### Story 11.2: Mint strategy-family metadata records

As the operator,
I want to mint a strategy family as an opaque id plus a dated registry metadata record through the `families/` helpers,
So that per-family variables and exit-policy resolution have a keying token to hang on, without the family ever gaining authority over a bot (FR-047, QL-6, CT-06).

**Acceptance Criteria:**

**Given** CT-06's addable-kinds law
**When** a strategy-family id is minted
**Then** it is an opaque operator-minted id (AD-9) resolving to a dated metadata record under CT-06 — the same machinery as `instrument_class` — with no new CT number
**And** qml adds no `qml_*` configurable row and no version pin to the registry

**Given** a minted family record
**When** any code inspects it for constraint powers (permitted timeframes, permitted feature families, mutation allowances)
**Then** none exist — a family is a keying token with no authority, and constraining is the Book's job (admission bar, footprint_requirements, prediction linter)

**Given** a family id in use
**When** the ratified law keys on it
**Then** it resolves the per-family variables that law already reaches for — the Book's `exit_policy` `ExitLogicRef` per family, the family-scoped paper starting balance, the per-family bench threshold — while the family itself decides nothing

**Given** a declaration citing a family id
**When** that id resolves to no family record at Layer 1
**Then** the result is an `unavailable dependency` typed refusal, journaled — never a silent pass

### Story 11.3: Fingerprint the logic artifact by reproducible source manifest

As a bot author,
I want my plain-Python logic distribution identified by distribution identity + version + a normalized reproducible source-manifest fingerprint,
So that a code change mints a new Bot exactly as a changed number does, and identical source built in two sandboxes yields one Bot `fp1` (FR-047, QL-2, AR-63).

**Acceptance Criteria:**

**Given** a logic source tree
**When** its source-manifest fingerprint is computed
**Then** it is a normalized, reproducible hash over the source tree in `fp1:sha256:<hex>` form, computed only by calling qmf-core's canonical fp1 function — never re-implemented in qml

**Given** the same logic source built in two different sandboxes
**When** each build's Bot definition is fingerprinted
**Then** both yield one identical Bot `fp1`
**And** non-reproducible built-artifact bytes (wheel timestamps, build metadata) never enter identity

**Given** a one-character change to the logic source
**When** the source-manifest fingerprint is recomputed
**Then** it differs, so the containing Bot definition mints a new `fp1` — a code change mints a new Bot exactly as a changed default mints a new Book

**Given** a declaration whose referenced logic distribution cannot be resolved
**When** Layer 1 evaluates it
**Then** the result is an `unavailable dependency` refusal — the logic reference is mandatory, because a governed bot is exactly two artifacts

### Story 11.4: Author the footprint, producer templates, and horizon derivation

As a bot author,
I want the `footprint/` module to express my bot's single canonical consumption manifest — the stream set, required calendars, and producer bindings as pinned fingerprints or complete templates — with template resolution a total single-valued function and the warm-up horizon derived, not hand-declared,
So that identical canonical runs fingerprint identically on every machine and my footprint is the one locus a host feeds evidence from (FR-047, QL-4, CT-33, AR-64).

**Acceptance Criteria:**

**Given** a producer template (a complete CT-16/CT-17 configuration minus only its space-bound parameter values)
**When** it is resolved by substituting the space-bound values
**Then** resolution is a total, single-valued function producing one deterministic CT-16/CT-17 configured-producer fingerprint, so dedup lands on ordinary producer fingerprints

**Given** a producer template missing any AD-22 identity field (formula id, contract format version, ordered named input set, calendar requirements, alignment policy, missing-value policy, warm-up, output schema, supported modes, arithmetic-reference configuration)
**When** it is validated
**Then** it is a Layer-1 registration refusal — a template is a complete configuration minus only the space-bound values, and an omitted identity field is a contract defect

**Given** a footprint plus every cited confluence's leg producer bindings and any bot-direct producers
**When** the transitive-union completeness is computed
**Then** the module reports whether the footprint's producer-binding set equals that transitive union — the raw material the Epic 12 Layer-1 linter consumes to refuse an incomplete footprint

**Given** a resolved producer chain
**When** the warm-up/embargo horizon is derived
**Then** it comes from the chain (AD-21/AD-22 law) and there is no second, hand-declared window field on the declaration

**Given** the stream set is nested inside the footprint
**When** the footprint is authored
**Then** the stream set (instrument-role + `BarSpec` list in B-12's shape, trading vs data-only roles) is the one stream-set locus, never a second top-level field
**And** hosts provide only the declared footprint to the logic

### Story 11.5: Author the CT-34 confluence kind

As a bot author,
I want to author a confluence as its own reusable registry artifact — one-or-more legs of any role mix, each carrying a producer binding and/or a child-confluence cite —
So that a set of governed producers and the role each plays is declared once, deduplicated by fingerprint, and reused across bots (FR-049, CT-34, QL-5).

**Acceptance Criteria:**

**Given** a confluence
**When** its legs are authored
**Then** each leg carries a mandatory role from the closed-and-addable vocabulary `level | trigger | confirmation | filter`, and at least one leg is present (a zero-leg confluence is `invalid input`, and leg and component counts are never bounded)

**Given** a single leg
**When** it is validated
**Then** it carries a producer binding (a pinned CT-16/CT-17 fingerprint or a QL-4 template), a `leg.confluence_ref` to a child confluence, or both — at least one of the two is required, the role always mandatory

**Given** a confluence with no declared order-significance
**When** it is fingerprinted
**Then** its legs order fingerprint-ascending (order-insignificant) with display-only ordinals that never enter identity; order-significance is opt-in per confluence and enters the fingerprint only when declared (a confluence is a declaration artifact, not a CT-17 causal composite, so AD-25's order-significant-by-default does not reach it)

**Given** two bots citing the same confluence content
**When** each is fingerprinted
**Then** reuse mints no new confluence, while a changed leg, role, producer binding, leg parameter, child cite, or a newly-declared order-significance always mints a new confluence fingerprint

**Given** a leg whose role is outside the vocabulary, or that carries neither a producer binding nor a child-confluence cite
**When** it is validated
**Then** it is an `invalid input` refusal, and an unresolvable producer fingerprint or cited child confluence is an `unavailable dependency` refusal
**And** condition semantics (when a leg is satisfied) live in the Python logic in V1 — the declaration carries only what is consumed and which role each plays

### Story 11.6: Author the CT-33 Bot definition with identity carve-out and versioning

As a bot author,
I want to author my Bot definition as the declaration half of a governed bot — exactly one strategy family, the confluence set, the declared parameter space with unit-kinds, the footprint, the permitted exit-intent declaration, and the logic reference — with identity carved out of the AD-16 header and versioning on AD-30's branches-from graph,
So that my bot's meaning lives inside its `fp1`, two bots compare and deduplicate by construction, and a tuned assignment can never silently wear the original's track record (FR-047, CT-33, QL-3, AR-62).

**Acceptance Criteria:**

**Given** a Bot definition
**When** its `fp1` is computed
**Then** the AD-16 header's `writer`, `sequence`, `stable id`, and `created-at` are excluded (the stable id is derived from the fingerprint, never hashed into it), and identity is the six semantic-content groups plus the contract format version and at-birth refs — nothing more

**Given** the declared parameter space
**When** each variable is validated
**Then** each carries a type in `{exact integer, exact rational, categorical, boolean}`, bounds, step, a mandatory default, an optional hard-constraint filter, and an AD-40 unit-kind; a variable missing its unit-kind is `invalid input`
**And** the mandatory defaults taken together are the canonical assignment — one identity locus, not a separate declared field

**Given** the cardinality rules
**When** a declaration carries zero or more than one strategy-family id
**Then** it is `invalid input` (a deliberate AD-17 cardinality-one ruling)
**And** the confluence set is one-or-more CT-34 fingerprints, canonically ordered by child fingerprint ascending with display-only ordinals

**Given** the permitted-intent declaration
**When** it is authored
**Then** it names only permitted exit-intent kinds as a subset of the ratified CT-23 exit vocabulary (`close_full | tighten_protective_stop`), which may be empty (an entry-only bot is legal); `entry` is always permitted and is never declared here
**And** the declaration carries no sizing, no venue command, and no exit-logic field — exit behaviour is the Book's, keyed by the bot's one family

**Given** AD-30 git-logic versioning
**When** a bot is versioned
**Then** versions ride an append-only `branches-from` graph (multiple heads legal) with a separate dated `current` pointer, every version readable forever; re-binding, seat assignment, and paper flips never mint a new Bot, while a changed default, confluence leg, footprint entry, or logic artifact always does

**Given** the registration write path (AD-25 root-mints pattern)
**When** a declaration is authored
**Then** qml returns fingerprintable content only, never a stamped record — the host composition root holds the `WriterId` and the gapless per-`(writer, kind)` sequence, mints the record, and sees every `RecordSink` refusal; the writer unit is `(machine, authoring role, kind)`

### Story 11.7: Mint CT-22 and CT-23 format-version 2 with migration notes

As the factory developer,
I want CT-22 and CT-23 carried to format-version 2 — qmf-risk-owned shapes with QML-authored semantics and mandatory migration notes —
So that the admission-bar evidence fields, the exit_policy catch-all, the footprint_requirements shape, and the advisory stop proposal have contract surface, while every pre-mint format-1 Book definition and intent stays readable forever (FR-047, FR-049, CT-22 v2, CT-23 v2, AR-28, SC-05).

**Acceptance Criteria:**

**Given** CT-22 format 1
**When** it is minted to format 2
**Then** it adds exactly three things and nothing more: two `admission_bar.evidence_requirements` fields (`registered_conformant_bot_cite`; `canonical_assignment_evidence`), one explicit optional `exit_policy` catch-all default entry, and the `footprint_requirements` requirement-set shape filling its reserved pending slot (per QL-8/QL-6/QL-4)

**Given** CT-23 format 1
**When** it is minted to format 2
**Then** it adds exactly one OPTIONAL entry-intent field, `entry.advisory_stop_proposal` (a Price or PriceDelta bound, advisory exactly as `proposed_r`), and documents the declared full-loss price as Book-resolved at the door — and nothing more (per QL-7)

**Given** a pre-mint format-1 Book definition or intent
**When** it is read after the mint
**Then** it stays readable forever at format 1; because `advisory_stop_proposal` is optional, format-2 readers accept format-1 intents unchanged

**Given** a format-1 reader confronting a format-2 CT-22 or CT-23 artifact
**When** it reads
**Then** it refuses `unsupported capability` on the version mismatch — never a best-effort read
**And** the two new admission-bar fields land only through this mint, never as a silent AD-30 field addition an old parser would ignore and thereby admit the very evidence they exist to refuse

**Given** the admission-bar interfaces
**When** they are minted
**Then** the thresholds behind them stay GAP-0048/0049 (interfaces only, SC-07)
**And** any not-yet-ruled requirement still passes registration while blocking live binding

## Epic 12: QML protocol & conformance

The bot runtime protocol QMB (and later the trading node) hosts (FR-050), plus the two-layer conformance gate that is technical-never-performance and is the ticket into governed evidence citation and Book seats — never into tunnel entry (FR-048). Builds on Epic 11's authored artifacts; every conformance verdict is host-independent by construction, and plain-Python bots keep full tunnel access throughout.

### Story 12.1: Define the bot runtime protocol

As a bot author,
I want to write my logic as a factory the host constructs with (declaration, resolved assignment, injected read surfaces), returning a callback the host drives per evaluation instant that receives only my declared footprint's evidence and returns zero-or-more CT-23 intents,
So that my bot is deterministic, sandbox-testable with no Book present, and identical live and backtest — one protocol, both hosts (FR-050, QL-7, AR-65, CT-23 v2).

**Acceptance Criteria:**

**Given** the runtime protocol
**When** a host constructs a bot
**Then** the bot is a factory taking `(declaration, resolved assignment, injected read surfaces)` and returning a callback object the host drives per evaluation instant
**And** the protocol is a QML-owned format-versioned contract on QML's own AD-5 ladder (not CT-numbered, mirroring QMB's own contracts)

**Given** a callback invocation
**When** evidence is delivered
**Then** the callback receives only the declared footprint's evidence (presence-mapped series per AD-22, structure lifecycle folds per AD-25, each sample carrying its knowable-at instant) and returns zero-or-more CT-23 intents through the door

**Given** the bot's denial set
**When** logic runs
**Then** the bot never sizes (`requested_r` is Book-resolved), never touches venue commands, never reads a clock (the evaluation instant rides the callback), and performs no I/O, network access, or undeclared randomness — a stochastic bot declares a seed parameter in its space

**Given** an entry proposal
**When** it carries an advisory stop proposal
**Then** that proposal is advisory exactly as `proposed_r` is; the declared full-loss price is derived Book-side at the door by the Book executing its per-family `ExitLogicRef`, and no Book module is ever injected into bot logic

**Given** identical `(declaration, assignment, evidence sequence, state)`
**When** the bot is replayed
**Then** it yields identical intents — the deterministic golden-slice property B-2 already demands of everything in the tunnel

**Given** a bot that attempts to size or emit a venue command through the door
**When** the intent is evaluated
**Then** it is rejected — the door carries only the entry and exit intent families, and an inbound `requested_r` is `invalid input`

### Story 12.2: Contract bot state snapshot and restore

As the factory developer hosting bots,
I want bot state snapshot/restore as a versioned contract scoped to the tuple (OS, logic identity + source-manifest fingerprint, protocol format version, arithmetic-reference build),
So that a restored bot is provably the same bot on the same substrate, and a restored-state fingerprint can enter downstream evidence labels (FR-050, QL-7, AR-67).

**Acceptance Criteria:**

**Given** a bot with bounded declared state
**When** it is snapshotted and restored on an identical tuple
**Then** the round-trip is equivalent (identical continued intents)
**And** the restored-state fingerprint enters downstream labels

**Given** a restore attempt across a differing OS
**When** the tuple component differs
**Then** it is an `unavailable dependency` refusal

**Given** a restore attempt across a differing logic identity + source-manifest fingerprint, protocol format version, or arithmetic-reference build
**When** any one of those components differs
**Then** it is an `unavailable dependency` refusal — snapshot/restore is scoped to that exact tuple, never best-effort across it

**Given** a bot whose declared state bound is exceeded
**When** state is captured
**Then** the bound is enforced (asserted as a Layer-2 conformance concern) — bot state is bounded and declared, never unbounded

### Story 12.3: Build the Layer 1 declaration linter

As a bot author,
I want a machine declaration linter that runs at registration and returns typed refusals for any incompleteness,
So that only a fully-formed, resolvable, unit-kinded declaration ever reaches the registration gate (FR-048, QL-8, AR-64, CT-33, CT-34).

**Acceptance Criteria:**

**Given** a declaration at registration
**When** Layer 1 runs
**Then** it checks schema completeness against the declared format version, every parameter unit-kinded with a valid canonical assignment, and every reference resolvable (family record, confluence fingerprints, producer formulas at their declared format versions, logic distribution)

**Given** a footprint
**When** Layer 1 runs
**Then** it enforces footprint transitive-union completeness (consuming Epic 11's `footprint/` machinery) and producer-template completeness; a confluence-leg producer absent from the footprint, or a template missing an identity field, is a typed refusal

**Given** the permitted-intent declaration
**When** Layer 1 runs
**Then** permitted exit-intent kinds must lie within the ratified CT-23 exit vocabulary (`close_full | tighten_protective_stop`); a kind outside it is `invalid input`

**Given** any Layer 1 failure
**When** it occurs
**Then** it is an AD-11 typed refusal (`invalid input | unsupported capability | unavailable dependency`), journaled — never swallowed, never a best-effort pass

**Given** an unknown contract format version on the declaration
**When** Layer 1 reads it
**Then** it is an `unsupported capability` refusal, never a best-effort read

### Story 12.4: Build the Layer 2 pure conformance surface and golden-slice generator

As the factory developer,
I want the QML-owned Layer 2 pure surface — the denial set, static AST/import-scan rules, determinism harness, a deterministic golden-slice generator keyed off the declared footprint, and the verdict function — split cleanly from a host-owned process runner,
So that a bot's conformance verdict is host-independent by construction and no Book is present or needed (FR-048, QL-8, AR-64).

**Acceptance Criteria:**

**Given** the Layer 2 contract
**When** it is built
**Then** QML owns, as format-versioned pure surface, the denial set (clock/I-O/network/randomness), the static AST/import-scan rules, the determinism harness, the golden-slice generator, and the verdict function; the host owns only process spawning and isolation and feeds results back to the pure verdict function

**Given** a bot's declared footprint
**When** the golden-slice generator runs
**Then** it produces a deterministic, identity-bearing conformance fixture keyed off that footprint

**Given** a conformance run
**When** the suite executes
**Then** it asserts: the logic artifact loads in isolation; a golden slice run twice yields identical intents; only permitted intent kinds are emitted; and the declared state bound holds with a snapshot/restore round-trip equivalent

**Given** the same bot run through two different hosts
**When** each verdict is computed
**Then** the verdict is identical — host-independent by construction, with no Book present

**Given** a golden slice that yields differing intents on two runs, or a non-permitted intent kind emitted
**When** the verdict function evaluates
**Then** it is a Layer-2 conformance failure

### Story 12.5: Implement the host sandbox runner within the V1 enforcement scope

As the factory developer,
I want the host-owned sandbox runner that spawns and isolates the bot process and feeds results to QML's pure verdict function, enforcing the denial set through static AST/import scanning, capability starvation, and process isolation only,
So that V1 conformance runs honestly within its stated scope without waiting on hardened OS-level confinement (FR-048, QL-8, AR-68).

**Acceptance Criteria:**

**Given** the V1 enforcement scope
**When** the runner enforces no-clock / no-I-O / no-network
**Then** it does so by static AST/import scanning, capability starvation (hosts inject read surfaces only), and host process isolation — and nothing else is promised

**Given** hardened OS-level runtime confinement (restricted tokens/job objects on Windows, seccomp-class on Linux)
**When** V1 ships
**Then** it is a named deferred dependency of the node/platform sitting, and V1 does not wait on it

**Given** the threat model
**When** conformance is evaluated
**Then** a dynamically-evasive malicious bot is explicitly out of V1's scope — bots are operator- or operator's-agent-authored

**Given** the runner
**When** it executes a bot
**Then** it uses stdlib process management (B-5's posture), spawns and isolates the process, and feeds results back to QML's pure verdict function — the runner owns only spawning and isolation, never the verdict

**Given** a bot whose static AST/import scan detects a clock read, filesystem access, or network import
**When** the scan runs
**Then** it is a Layer-2 conformance failure before any process is spawned

### Story 12.6: Build the prediction linter

As the operator,
I want a prediction linter that runs statically on demand and at seat time against the CT-28 binding context, checking a bot against the Book it would bind,
So that a bot is proven compatible with a Book's requirements before it takes a seat (FR-048, QL-8, AR-66, CT-28, CT-22 v2, CT-18).

**Acceptance Criteria:**

**Given** the CT-28 binding context
**When** the prediction linter runs
**Then** it runs the pinned check list (addable never redefined): (a) the CT-33 footprint satisfies the Book's `footprint_requirements`; (b) the bot's declared permitted exit-intent kinds are a subset of the Book's `exit_policy` permitted exit kinds; (c) the bot's family resolves an `exit_policy` entry (explicit or the declared catch-all); (d) the bot's stream set lies within the binding's declared CT-18 venue capabilities

**Given** check (b) and a Book that declares zero permitted exit kinds (the honest V1 default)
**When** an entry-only bot is checked
**Then** it passes — `entry` is never gated here

**Given** check (c)
**When** a bot's family resolves neither an explicit `exit_policy` entry nor the declared catch-all
**Then** it is a prediction-linter failure

**Given** check (d)
**When** the bot's stream set exceeds the binding's declared venue capabilities
**Then** it is a prediction-linter failure at bind time (AD-29's bind-time check)

**Given** a not-yet-ruled `footprint_requirement` or admission-bar threshold
**When** the linter runs
**Then** the interface is present but the threshold stays GAP-0048/0049 (interfaces only, SC-07) — a blank requirement still passes registration and blocks live binding

### Story 12.7: Gate registration on both conformance layers

As the operator,
I want the Bot registry kind to mint only for a declaration passing both conformance layers, else a policy rejection,
So that registration is the ticket into governed evidence citation and Book seats — and nothing else — while ungoverned plain-Python bots keep full tunnel access (FR-048, FR-050, QL-8, CT-33, ADR-0018).

**Acceptance Criteria:**

**Given** a declaration
**When** registration is attempted
**Then** the Bot kind mints only if both Layer 1 and Layer 2 pass; a declaration failing either layer is refused `policy rejection` — there is no partial or probationary registration

**Given** a registered Bot definition
**When** governed evidence (CT-32) or a seat cites it by `fp1`
**Then** the citation is valid; conformance gates evidence citation and seats, never tunnel entry

**Given** an ungoverned plain-Python bot
**When** it runs in the tunnel
**Then** it keeps full tunnel access (B-4 ledger lines, the research door) and simply cannot be cited by governed evidence — conformance is technical, never performance

**Given** a working ungoverned experiment
**When** it graduates
**Then** it mints the two artifacts (declaration + logic) with a lineage edge back to its originating research artifact

**Given** the old `max_acceptable_complexity_score` anti-sprawl gate
**When** registration runs
**Then** it is not revived — any complexity/quality signal is a later measure, never a registration gate (a stated drop, not an omission)

**Given** the mint decision
**When** the record is written
**Then** the host composition root holds the `WriterId` and mints the record (AD-25 root-mints pattern); qml returns only the fingerprintable content and the pass/fail verdict, never a stamped record

### Story 12.8: Ship the complete example conformant bot

As a bot author,
I want one complete conformant bot in `examples/` — a full declaration plus plain-Python logic — that passes both conformance layers,
So that I have a ratified reference to copy when authoring my own governed bot (FR-047, FR-050, AR-21, L27, QL-8).

**Acceptance Criteria:**

**Given** `examples/`
**When** the reference bot ships
**Then** it is one complete conformant bot — a CT-33 declaration (one strategy family, one-or-more CT-34 confluences, a unit-kinded parameter space with a canonical assignment, a complete footprint, a permitted exit-intent declaration) plus a plain-Python logic distribution conforming to the runtime protocol

**Given** the example
**When** Layer 1 and Layer 2 run against it
**Then** both pass and the Bot kind mints — it is a tier-1 reference-usage artifact (L27) with the same status as unit tests

**Given** the example logic
**When** it is driven per evaluation instant
**Then** it consumes only its declared footprint's evidence, emits only permitted CT-23 intent kinds with an advisory stop proposal on entry, and is deterministic under the golden slice

**Given** the example
**When** it is inspected
**Then** it neither sizes, reads a clock, performs I/O, nor carries an exit-logic field — demonstrating the bot-side boundary honestly

## Epic 13: QMB substrate

One resolved, fingerprinted run-config per run; registry as-of sets through one read port; the QMB package skeleton. This epic stands up the qmb distribution and the config-compiler half of FR-036: the structural-seed scaffold, the single registry-read port over immutable as-of sets, Book/BMS config-fragment materialization, the layered run-config compiler whose fingerprint is the run id, and the `starting_capital` seed with its `world=replay` binding.

### Story 13.1: Scaffold the qmb distribution and structural-seed modules

As the factory developer,
I want the qmb package scaffolded as one wheel — pure library plus the `qmb` CLI — with the spine's structural-seed module tree and pinned dependencies,
So that every later QMB story lands in a fixed, import-clean home that consumes qmf-* in workspace lockstep.

**Acceptance Criteria:**

**Given** the uv workspace,
**When** qmb is built and installed,
**Then** it builds as ONE wheel (pure library + `qmb` CLI), installs via `uv add qmb`, imports as `qmb`, and declares `click==8.4.2` and `optuna==4.9.0` as pinned dependencies (AR-10, B-13, DEC-0167, DEC-0168).
**And** qmb sits outside the qmf roster, depends only on the six backend qmf packages, and adds no dependency edge to qmf-venue (AR-06, B-13).

**Given** the spine's Structural Seed,
**When** the module tree is created,
**Then** it contains `runloop/`, `config/`, `registryread/`, `execution/`, `data/`, `optimize/`, `robustness/`, `results/`, `ledger/`, `orchestrator/`, and `doors/{cli,api,mcp}` — with `doors/mcp` scaffolded but not shipped in V1 (B-1, SC-08).

**Given** the inherited vocabulary law,
**When** any module, symbol, or docstring is named,
**Then** none uses "engine", "kernel", "exam", "plugin", or "snapshot" for registry state — registry state is an "as-of set" (Consistency Conventions).

**Given** QMB SemVer,
**When** it appears on any artifact,
**Then** it rides as display-only provenance and never enters identity (AR-26, B-13).

**Given** the Tier-1 gate,
**When** `poe check` runs over qmb source,
**Then** ruff + pyright-strict + pytest pass, no module-global mutable state exists in the library, and the package is pure-Python and OS-neutral (AR-11, AR-04, NFR-02).

### Story 13.2: The single registry-read port over immutable as-of sets

As a framework consumer,
I want one library-owned registry-read port that resolves records and fragments from an immutable, fingerprinted as-of set,
So that the config compiler and every door read the same registry state and can never disagree.

**Acceptance Criteria:**

**Given** the machine holds a registry as-of set (a `registry_as_of` instant plus a set fingerprint) delivered by the passive file-sync hub,
**When** any consumer needs registry state,
**Then** it resolves through the ONE library-owned registry-read port, and no door-side or second cache exists (AR-55, B-15).

**Given** a record resolvable under a human alias,
**When** the port resolves it,
**Then** it returns the record by `fp1` and the caller cites it by fingerprint, never `name@version` (B-13, B-15).

**Given** a ref that a fresher as-of set shows superseded,
**When** the port resolves that ref,
**Then** it returns an AD-11 stale-evidence refusal at severity `qmb_stale_evidence_severity` — returned, not raised (AR-55, B-15, FM-7).

**Given** a batch/sweep admission,
**When** one as-of is resolved,
**Then** it is frozen for every trial, and thereafter fragments resolve by explicit fingerprint, never `name@latest` (SC-11, B-15).

**Given** the hub,
**When** it is described,
**Then** it is dumb passive storage — never the dead DEC-0084 central service — and registry state is never called a "snapshot" (B-15).

### Story 13.3: Materialize Book and BMS config fragments as derived fp1 artifacts

As an agent,
I want a Book or BMS definition to materialize a schema-validated, fingerprinted config fragment with lineage back to its source,
So that a run's conditions compile from versioned, content-addressed fragments rather than hand-edited files.

**Acceptance Criteria:**

**Given** a Book definition (CT-22) resolved through the registry-read port,
**When** its config fragment is materialized,
**Then** the fragment is a schema-validated, fingerprinted DERIVED artifact carrying an AD-16/CT-07 lineage edge back to the CT-22 source — never a newly minted registry kind and never free-hand-edited (AR-52, B-3).

**Given** a BMS definition (CT-27),
**When** its config fragment is materialized,
**Then** it is likewise a derived, fingerprinted artifact carrying a CT-07 lineage edge back to the CT-27 source (AR-52, B-3).

**Given** the Book and BMS fragments,
**When** their key namespaces are compared,
**Then** they are DISJOINT — Book owns admission, sizing, and exit-door policy; BMS owns accounting, constraints, kill-line, and reporting (B-3, DEC-0143).

**Given** a fragment stamps its own AD-5 integer format version,
**When** it is re-read after a later format version ships,
**Then** old fragments stay readable forever (AR-25, B-3).

**Given** a named condition preset (for example, stress-spread),
**When** it is authored,
**Then** it is a config fragment like any other (B-3).

### Story 13.4: Compile the one resolved run-config with fixed-precedence layers

As an agent,
I want the compiler to resolve exactly one read-only run-config from the fixed-precedence layers, whose fingerprint is the run id and ledger key,
So that every door computes the same run id from the same conditions and the tunnel is never swapped — only its variables change.

**Acceptance Criteria:**

**Given** the layers invocation flags > run spec (the bot layer) > BMS fragment > Book fragment > workspace defaults,
**When** the compiler runs,
**Then** it produces exactly ONE fully-resolved, read-only, schema-validated run-config, and layering is deterministic and pure — same inputs yield a byte-identical resolved artifact (AR-52, B-3).

**Given** a key that collides across the Book and BMS fragments,
**When** compilation runs,
**Then** it returns a compile-time typed refusal; in any sanctioned overlap BMS outranks Book (B-3, FM-1).

**Given** the resolved artifact,
**When** it cites Book, BMS, and any binding,
**Then** it cites them by `fp1`, never `name@version`, even when the invocation used a human alias (B-3, B-13).

**Given** the resolved artifact stamps its own AD-5 format version and declares its AD-10 identity-vs-display field classification,
**When** any door fingerprints it,
**Then** all doors compute the SAME fingerprint; that fingerprint is the run-id root and the ledger key, and the artifact is written into the run's output directory named by the run id (AR-52, B-3).

**Given** a config that binds a replay clock to synthetic-tainted data,
**When** it is compiled,
**Then** it is an `invalid input` refusal, because world is provenance-derived and B-7 wins (FM-3, SC-06).

### Story 13.5: Seed the virtual ledger with starting_capital and mint the world=replay binding

As the operator,
I want `starting_capital` to be a mandatory run-spec seed and every run to mint exactly one `world=replay` binding,
So that a replay run has an honest virtual ledger and an identity that can never be confused with live money.

**Acceptance Criteria:**

**Given** the run spec,
**When** the config compiles,
**Then** `starting_capital` is taken from a mandatory run-spec field (the Book fragment may default it) and seeds the binding's virtual ledger (AR-52, B-3).

**Given** an invocation flag that overrides the seed,
**When** it is applied,
**Then** the binding is stamped `seed_overridden` and the run's fold is forced to `unrated` (B-3, FM-12).

**Given** each run,
**When** it compiles,
**Then** it mints exactly ONE AD-29/CT-28 binding with `world=replay` — a different identity from any live binding of the same Book instance, and incomparable to it (B-3, FR-036).

**Given** sizing, R-freeze, and exits,
**When** they resolve,
**Then** they consume qmf-risk contracts (CT-23 inbound intent, CT-29 exits), and an AD-40 full-loss price is required before any open (B-3, B-6, AR-56).

## Epic 14: QMB run loop & replay backtest

The one never-forked event-slice loop: warm-up in-loop, deterministic reproduction, forming bars never actionable. This epic delivers the loop half of FR-036 and all of FR-037: the injected frontier clock, the six pinned identity-bearing sub-phases, completed-boundary bar derivation, in-loop warm-up, resting-order execution eligibility with CT-23 intents and CT-29 exits, cancel-and-observe, and the tier-2 golden-slice determinism test. It consumes the resolved run-config and `world=replay` binding minted in Epic 13, indicators/structure from Epics 7 and 9, and CT-23 intents from Epic 10.

### Story 14.1: The injected frontier clock

As a framework consumer,
I want time to advance only through an injected frontier clock that IS qmf-core's AD-8 Clock protocol,
So that replay, backtest, and live differ only by the injected clock and adapters — the loop is never forked.

**Acceptance Criteria:**

**Given** the run loop,
**When** it needs the current instant,
**Then** it reads only the injected frontier clock, and nothing below the composition root reads the system clock (AR-16, B-2).

**Given** replay,
**When** the clock advances,
**Then** it is a pure function of the data cursor — monotonically non-decreasing, pulled to the minimum next-emit instant across all declared streams, never rewinding (B-2, FR-037).

**Given** the clock,
**When** it emits an instant,
**Then** it emits AD-8 wall/replay Instants, never the AD-8 monotonic diagnostic kind, and it does NOT choose `world` — B-7 does (B-2).

**Given** the same loop,
**When** only the injected clock and adapters change,
**Then** backtest, replay, and (deferred) live share identical loop code — the loop is never forked (B-2, FR-036).

**Given** simulated-clock typing,
**When** the loop attempts to assert a simulated instant as a wall/replay Instant,
**Then** it is refused until GAP-0048 — the loop seam may exist, but the assertion may not (B-2, SC-06).

### Story 14.2: The event-slice loop with six pinned identity-bearing sub-phases

As a framework consumer,
I want one event-slice loop whose six sub-phases run in a pinned, identity-bearing order,
So that identical inputs produce identical slices and fills, and no new intent can fill against the slice that produced it.

**Acceptance Criteria:**

**Given** one event slice,
**When** it is processed,
**Then** the sub-phases run in this pinned order: (1) frontier advance + stream update, (2) scheduled position-level events (financing), (3) execute resting orders through the execution ports, (4) update indicators/structure on closed data only, (5) strategy callbacks mint intents, (6) new intents are NOT eligible to fill against this slice's path (AR-57, B-2).

**Given** a new intent minted in sub-phase 5,
**When** the current slice completes,
**Then** it never fills against this slice's path and rests for a later slice (B-2, FR-037).

**Given** multiple instruments in a phase,
**When** they are processed,
**Then** they process in the stream-set declaration order, which is identity content of the resolved run-config (B-2, B-12).

**Given** indicators and structure,
**When** they update,
**Then** they update on closed data only, never on a forming bar (B-2, CT-16, CT-17).

**Given** the sub-phase order,
**When** it is altered,
**Then** the change is identity-bearing (a different fingerprint), because the order is pinned spine law (AR-57, B-2).

### Story 14.3: Completed-boundary bar derivation; a forming bar is never actionable

As an agent authoring a bot,
I want higher-BarSpec bars derived only on completed boundaries from the finest declared base stream,
So that my strategy can never see or act on a forming bar and look-ahead via bar timing is impossible.

**Acceptance Criteria:**

**Given** a higher-BarSpec bar,
**When** it is derived,
**Then** it is built from the finest declared base stream and emitted ONLY on its completed boundary (AR-57, B-2).

**Given** a forming (incomplete) bar,
**When** strategy code runs,
**Then** the forming bar is never visible or actionable and carries an inspectable completeness state (B-2).

**Given** a derived bar and the fills of the same slice,
**When** both consume the underlying series,
**Then** the bar is built from the same (possibly gap-fixed) series the fills run on — never a future or a divergent series (B-2, FR-037).

**Given** GAP-0048 is still open,
**When** the run executes,
**Then** completed-boundary and forming-bar look-ahead prevention ships regardless of the deferred fidelity taxonomy (SC-06).

### Story 14.4: In-loop warm-up with trading locked

As an agent,
I want warm-up to run in the same loop with trading locked for the embargo length,
So that indicator state is built by real replay and the result's evidence range is the trading interval only.

**Acceptance Criteria:**

**Given** warm-up,
**When** it runs,
**Then** it uses the same event-slice loop, the same sub-phase order, and the same adapters, with trading locked (SC-10, B-2).

**Given** warm-up is active,
**When** a bot attempts to act — mint an entry, an exit, or any command,
**Then** it is a typed `policy rejection` (B-2, SC-10).

**Given** the warm-up length,
**When** it is determined,
**Then** it is the split-manifest embargo already declared under AD-21 for the producers the stream set cites (an observation count, never a Duration), and the loop adds no second window (B-2, CT-12).

**Given** the result label,
**When** its evidence range is set,
**Then** it is the trading interval only, never the warm-up interval (B-2, SC-10).

**Given** pre-seeding indicator buffers without replaying slices,
**When** it is attempted,
**Then** it is NOT warm-up (B-2).

### Story 14.5: CT-23 intent consumption, the execution port seam, and CT-29 exits

As an agent,
I want the loop to execute only Book-resolved authorized intents through pinned fill/slippage/cost ports and mint one exit record per virtual close,
So that no bot-sized order ever reaches a fill and every close is recorded against the run's replay binding.

**Acceptance Criteria:**

**Given** inbound execution,
**When** an intent reaches the ports,
**Then** it is a CT-23 Book-resolved (authorized) intent or a typed refusal — never a bot-sized order — and an AD-40 full-loss price is required before any open (B-6, AR-56, CT-23).

**Given** execution,
**When** the ports are bound per run-config,
**Then** fill, slippage, and cost are SEPARATE pinned ports (the `typing.Protocol` seams pinned here for Epic 17 to implement); fill decides `Fill | NoFill | PartialFill` with partial quantities first-class (B-6, AR-56).

**Given** every virtual-position close,
**When** it occurs,
**Then** exactly one CT-29 exit record is minted against the run's `world=replay` binding, and bot-proposed exits are risk-monotonic — risk-reducing only (CT-29, FR-032).

**Given** GAP-0048 is open,
**When** any fill is produced,
**Then** all fills carry an `optimistic` taint, so the run spends no split budget and claims no edge (B-6, SC-06, FM-9).

**Given** a run whose stream set reads store-persisted synthetic data,
**When** world is derived from provenance,
**Then** the run is `world=simulated` and a `policy rejection` for governed evidence until GAP-0048 (B-7, FM-2, SC-06).

### Story 14.6: Cancel and observe a run while it is running

As an agent,
I want the loop to be cooperatively cancellable and observable while it runs,
So that a long or wrong run can be stopped and its progress watched without corrupting results.

**Acceptance Criteria:**

**Given** a cancel token,
**When** it is signalled,
**Then** the loop stops cooperatively at a slice boundary and returns a typed terminal state that the orchestrator (Epic 15) renders as the `aborted` ledger line (FR-037, B-4).

**Given** a running loop,
**When** it is observed,
**Then** it exposes progress — data-points-processed throughput — and an `is_warming_up` flag while running (FR-037).

**Given** a per-run time or memory limit breach detected in-loop,
**When** it occurs,
**Then** the loop surfaces a typed `aborted` terminal state rather than hanging (FR-037, B-5).

**Given** cancellation mid-run,
**When** the run stops,
**Then** the pure `run()` returns a terminal refusal and writes nothing — no partial governed result is emitted (B-4).

### Story 14.7: The tier-2 golden-slice determinism test and run-id reproduction

As the factory developer,
I want a tier-2 golden-slice determinism test asserting identical CT-32 fingerprints across two runs of identical inputs,
So that replay reproducibility is a mechanically enforced platform property.

**Acceptance Criteria:**

**Given** identical inputs and resolved config,
**When** the run executes twice,
**Then** both produce an identical CT-32 fingerprint, enforced by a tier-2 golden-slice determinism test (AR-58, B-2, NFR-03).

**Given** a run id,
**When** it is re-run under its resolved config,
**Then** it must reproduce the CT-32 fingerprint or return a typed refusal (AR-58, FM-11).

**Given** determinism,
**When** it is analyzed,
**Then** it derives from the pinned sub-phase order, the stream-set declaration order, and pure aggregation/gap-fix/fill functions — no ambient nondeterminism (B-2, NFR-02).

**Given** the run alongside N concurrent siblings,
**When** compared to the run in isolation,
**Then** results and fingerprint are byte-identical, because concurrency is a scheduling decision only (B-5, NFR-03).

### Story 14.8: Host conformant bots — the QL-7 adapter and QML-aware config compilation

As a bot author,
I want QMB to host my conformant CT-33-declared bot through the QL-7 runtime protocol, with the config compiler resolving my declaration,
So that governed bots run in the same tunnel as plain-Python bots the day QML lands.

**Acceptance Criteria:**

**Given** a registered CT-33 Bot definition and the QL-7 protocol from Epic 12,
**When** a run spec cites the Bot by fp1,
**Then** QMB's composition root constructs the bot via the QL-7 factory (declaration, resolved assignment, injected read surfaces)
**And** drives it per evaluation instant with declared-footprint evidence only (QL-7; AR-65).

**Given** the B-3 config compiler,
**When** it resolves a run citing a CT-33 Bot,
**Then** it applies the DEC-0183 extensions — assignment_is_canonical stamping and producer-template resolution —
**And** a non-canonical assignment is labeled as a run-spec override, never a governed-seat execution (DEC-0183; AR-69).

**Given** the host-owned conformance sandbox runner from Epic 12,
**When** Layer 2 conformance executes under QMB hosting,
**Then** the runner executes the pure verdict suite in an isolated process
**And** feeds results back to the QML-owned pure verdict function unchanged (QL-8; AR-64).

**Given** a plain-Python ungoverned bot,
**When** it runs in the tunnel,
**Then** nothing in the QL-7 adapter path is required for it
**And** tunnel entry remains ungated by conformance (QL-1; FR-047, FR-048).

Note: this story closes the QML-QMB seam and waits for Epics 12 and 13; it is Epic 14's final story.

## Epic 15: QMB orchestrator, ledger & concurrency

Process-per-run under a governed cap; exactly one ledger line per run. This epic delivers FR-045: the impure orchestrator that spawns each run as an isolated OS process, the governor that bounds parallelism by min(cpu, memory) with enqueue-on-full, cancel tokens and per-run limits with typed aborted refusals, the one-ledger-line law over WriterId-scoped JSONL fragments with merge-view reads, and the per-run operational logs the orchestrator streams. It runs against the library's pure `run()` contract established in Epic 13's scaffold, parallel with Epic 14.

### Story 15.1: Process-per-run via stdlib with isolated output directories

As a framework consumer,
I want the orchestrator to run each run as its own OS process with an isolated output directory,
So that concurrent runs share no mutable state and never fight for a file.

**Acceptance Criteria:**

**Given** a run,
**When** the orchestrator spawns it,
**Then** it is a separate OS process via stdlib process management, with its own isolated output directory named by the run id (AR-50, B-5).

**Given** the library's `run()`,
**When** a run executes,
**Then** `run()` is pure and spawns no threads, processes, or background work — the orchestrator owns all process management (AD-15, B-4).

**Given** the runtime,
**When** runs execute,
**Then** there is no Ray, no required Docker, and no daemon — sandbox and laptop run the same uv-installed package (AR-50, B-5).

**Given** two runs executing concurrently,
**When** they write output,
**Then** no two live runs share a writer for any file or stream — one-writer-per-stream (AR-17, B-4).

### Story 15.2: The resource governor with min(cpu, memory) budgets and enqueue-on-full

As the operator,
I want a governor that bounds parallelism by min(cpu budget, memory budget) and enqueues when full,
So that the sandbox never silently oversubscribes and a too-large run is refused, not crashed.

**Acceptance Criteria:**

**Given** the governor,
**When** it admits runs,
**Then** it bounds parallelism by `min(qmb_governor_cpu_budget, qmb_governor_memory_budget)` (AR-50, B-5).

**Given** a run whose projected peak memory exceeds the remaining budget,
**When** admission is attempted,
**Then** it gets a typed refusal or enqueues (enqueue-on-full) — never silent oversubscription (B-5, FM-6).

**Given** a full governor,
**When** a run finishes,
**Then** the next queued run is admitted — finish, then admit next (B-5).

**Given** 12-14 concurrent runs on sandbox hardware,
**When** the number is cited,
**Then** it is a motivating reference under AD-13, never a validated budget until a fingerprinted baseline is measured (B-5).

### Story 15.3: Cancel tokens and per-run limits with typed aborted refusals

As the operator,
I want every run cancellable with declared per-run time and memory limits whose breach is a typed abort,
So that one run can be killed without touching siblings and no run hangs.

**Acceptance Criteria:**

**Given** a run,
**When** it is submitted,
**Then** it carries a cancel token and declared per-run limits `qmb_run_time_limit` and `qmb_run_memory_limit` (AR-51, B-5).

**Given** a limit breach or a cancel,
**When** the orchestrator detects it,
**Then** it produces a typed `aborted` refusal with context (AR-51, B-5, FM-6).

**Given** one run's process,
**When** it is aborted,
**Then** it is killed without touching sibling processes (B-5).

**Given** an aborted run dying mid-flight,
**When** it stops,
**Then** it never writes a partial governed result — its output stays in its own room (B-4).

### Story 15.4: The one-ledger-line law over WriterId-scoped JSONL fragments

As a framework consumer,
I want the orchestrator to append exactly one WriterId-scoped ledger line per run and reads to be a world-and-role-scoped merge view,
So that the scoreboard and the evidence never diverge and many sandboxes merge without coordination.

**Acceptance Criteria:**

**Given** a finished run,
**When** the orchestrator completes it,
**Then** it appends exactly ONE ledger line — completed or aborted, never zero, never two — the aborted line carrying refusal context, never silently absent (AR-51, B-4).

**Given** the ledger line,
**When** it is written,
**Then** it carries the full AD-12 result label (evidence class; `provenance=sandbox` on factory-sandbox runs), the CT-32 fingerprint, the run's raw AD-40 unit-kinded measures, the fingerprint of the Book bar as resolved at run time, and a discriminated run role (`confirmation | trial | replicate | aborted`) — and stores NO pass/fail verdict (B-4, AR-59).

**Given** the physical ledger,
**When** it is written,
**Then** it is JSONL append-only fragment files written ONLY by the orchestrator, one fp1-canonical object per line, LF-terminated, append-with-fsync, WriterId-scoped per `(machine, role, worker-slot)`; concurrent processes never share a file (AR-53, AR-31, B-4).

**Given** a ledger read,
**When** it is served,
**Then** it is a world-and-role-scoped merge view over fragments, and the Book-bar read selects `role=confirmation` lines only (B-4, FM-8).

**Given** a direct library `run()` call in research,
**When** it returns,
**Then** it produces no governed evidence — runs enter the governed ledger only through the orchestrator (B-4).

### Story 15.5: Per-run AD-14 operational logs streamed by the orchestrator

As the operator,
I want the orchestrator to stream each run's operational log into its own run directory,
So that I can tail a live run while knowing the log is never mistaken for evidence.

**Acceptance Criteria:**

**Given** a live run,
**When** it executes,
**Then** the orchestrator owns the injected log sink and streams the run's operational log into a per-run log file in the run's output directory (B-4, Consistency Conventions).

**Given** per-run logs,
**When** their evidence status is asked,
**Then** they are AD-14 operational logs only and are NEVER evidence — under CT-11 only the raw archive and the journal bear evidence (B-4, CT-11).

**Given** structured logs,
**When** they cross package boundaries,
**Then** they carry a `correlation_id` excluded from fp1 identity (AR-35).

**Given** a crashed run,
**When** it dies,
**Then** it leaves a partial log in its own room and never corrupts any sibling or the ledger (B-4).

## Epic 16: qmb CLI & doors

The platform's single command-line surface plus the Python API door, with enforced parity. This epic delivers FR-046: the thin click-based `qmb` command tree, per-transport refusal rendering, the Python API pure re-export surface, registry-enumeration autocomplete through the B-15 port, the tier-2 door-parity contract test, and the MCP door scaffolded but shipped post-CLI-v1. It builds on Epic 13's compiler and registry-read port; parity tests complete against the capabilities landed by Epic 14.

### Story 16.1: The click-based qmb CLI command tree (thin, no domain logic)

As an agent,
I want a thin click-based `qmb` command tree where every capability is a library pure function,
So that the agent and the operator share one command-line surface with no domain logic in the door.

**Acceptance Criteria:**

**Given** the qmb CLI,
**When** it is built,
**Then** it uses `click==8.4.2` (the `qmb_cli_pin`) and every capability it exposes exists once, in the library, as a pure function — the door carries only adaptation logic: parsing, transport, refusal rendering, and autocomplete (B-1, DEC-0168).

**Given** the command tree,
**When** it is enumerated,
**Then** it exposes the platform's single command-line surface (for example, `backtest`, `data`, `optimize`, `ledger`, and `config` groups), and no domain logic accretes in the door (B-1, AR-10).

**Given** a command that runs the tunnel,
**When** it is invoked,
**Then** it declares its config/resource prerequisites and returns a typed refusal if they are absent (B-1, CT-04).

**Given** a `backtest` invocation,
**When** it resolves,
**Then** the door compiles the run-config via the Epic 13 compiler and submits it to the orchestrator entry point — computing no run-id of its own (B-1, B-3).

### Story 16.2: CLI refusal rendering — nonzero exit and machine-readable stderr JSON

As an agent,
I want CLI refusals rendered as a nonzero exit code plus machine-readable stderr JSON,
So that an agent can act on a refusal without parsing prose or HTML.

**Acceptance Criteria:**

**Given** a typed refusal returned by the library,
**When** the CLI renders it,
**Then** it exits nonzero and writes machine-readable stderr JSON carrying category, context, and retryability (AR-58, Consistency Conventions).

**Given** any refusal,
**When** it crosses the door,
**Then** it is RETURNED by the library and rendered by the door — never raised, never swallowed (AR-58, CT-04).

**Given** a successful run,
**When** it completes,
**Then** the CLI exits zero (CT-04).

**Given** a programmer error rather than a typed refusal,
**When** it occurs,
**Then** it surfaces as an exception, distinct from the refusal channel (AR-13).

### Story 16.3: The Python API door as a pure re-export surface

As a framework consumer,
I want a Python API door that re-exports the library's pure functions and returns refusal unions verbatim,
So that notebooks and the UI backend consume the same surface in-process.

**Acceptance Criteria:**

**Given** the Python API door,
**When** it is imported,
**Then** it is a thin pure re-export of the library's pure-function surface, importable from the uv-added qmb package (B-1, B-13).

**Given** a refusal,
**When** the Python door returns it,
**Then** it returns the library's refusal union verbatim — return-not-raise, exceptions only for programmer error (AR-58, AR-13).

**Given** the UI backend,
**When** it consumes QMB,
**Then** it consumes the Python API in-process, never stacked over HTTP (B-1).

**Given** a direct library call through the door in research,
**When** it runs,
**Then** it returns values and produces no governed evidence (B-4, B-9).

### Story 16.4: Registry-enumeration autocomplete through the B-15 port

As the operator,
I want shell autocomplete to enumerate registry state through the one registry-read port,
So that autocomplete and the config compiler can never offer different answers, and a new Book appears without a door cache.

**Acceptance Criteria:**

**Given** autocomplete,
**When** it enumerates registry state,
**Then** it enumerates through the single library-owned registry-read port — never a door-side or second cache (B-1, B-15, AR-55).

**Given** resolution and autocomplete,
**When** both read registry state,
**Then** they can never answer differently — one port over one as-of set (B-15).

**Given** a newly created Book,
**When** it reaches the CLI,
**Then** it arrives as a fresher as-of set — never as a door cache refresh or a live service query (B-15).

**Given** autocomplete,
**When** it is wired,
**Then** it uses the CLI framework's native (click) shell-completion mechanism and adds no bespoke completion machinery (B-1).

### Story 16.5: The tier-2 door-parity contract test

As the factory developer,
I want a tier-2 contract test asserting identical function surface and semantics across doors,
So that no capability drifts between the agent-facing and human-facing surfaces.

**Acceptance Criteria:**

**Given** the CLI and Python API doors,
**When** the parity test runs,
**Then** it asserts an identical function surface and identical semantics across doors (AR-58, B-1).

**Given** a capability added to one door,
**When** it is not present with identical semantics in the other,
**Then** the tier-2 parity test fails (B-1).

**Given** the parity test,
**When** it is scheduled,
**Then** it runs at Tier 2 (`poe check-integration`) and completes against the real capabilities landed by Epic 14 (AR-18, AR-19).

**Given** a door,
**When** it renders a refusal,
**Then** the test confirms per-transport rendering — CLI: nonzero exit plus stderr JSON; Python: refusal union verbatim (AR-58).

### Story 16.6: Scaffold the MCP door, shipped post-CLI-v1

As the factory developer,
I want the MCP door scaffolded but explicitly not shipped until after CLI v1,
So that the seam exists without pulling MCP work into the V1 product face.

**Acceptance Criteria:**

**Given** `doors/mcp`,
**When** it is scaffolded,
**Then** it is present as a sibling wrapper over the same library and is explicitly marked post-CLI-v1, not shipped in V1 (SC-08, B-1).

**Given** the MCP door design,
**When** it is described,
**Then** it is a sibling door over the same library — never stacked over HTTP — and localhost-bound by default (B-1).

**Given** the MCP door renders a refusal later,
**When** it does,
**Then** `error.data` carries the refusal union verbatim (AR-58).

**Given** CLI v1,
**When** it ships,
**Then** it ships first and the MCP door does not gate it (SC-08, B-1).

## Epic 17: QMB fill/slippage/fee/financing ports

Fidelity-labeled execution modeling behind separate pinned ports: the fill,
slippage, and cost ports execute CT-23 Book-resolved authorized intents against
each slice's declared path, financing applies as a scheduled position-level cash
event at the accounting rollover, and every fill carries the `optimistic` taint
until GAP-0048 closes. The port interfaces were pinned in Epic 14's run loop;
this epic implements the adapters, the composition, and the QMX-originated
forex-CFD content that neither donor backtester ships — as calibration seams, never
invented numbers.

### Story 17.1: Execution port-set composition and fidelity identity

As the factory developer,
I want a binder that composes the three separate pinned execution ports plus the financing scheduler from one resolved run-config and stamps each run's fidelity identity,
So that every non-live run's execution modeling is honestly assembled and labeled, and no optimistic result can masquerade as verdict-bearing edge before GAP-0048.

**Acceptance Criteria:**

**AC1 — three separate ports bound only from the resolved config**
**Given** a resolved, read-only run-config (B-3) naming fill, slippage, and cost adapter ids plus a financing-schedule reference
**When** the port-set binder composes execution for the run
**Then** it binds three SEPARATE ports (fill, slippage, cost) plus the financing scheduler, each by adapter-id, in the pinned composition order fill → slippage → cost (AR-56, B-6)
**And** binding happens only from the resolved config — never by ambient discovery or code change (B-3, B-1).

**AC2 — CT-23 authorized-intent inbound guard**
**Given** an inbound execution request
**When** it is not a CT-23 Book-resolved authorized intent (for example a raw bot-sized order)
**Then** the binder returns a typed refusal (CT-04) and no port executes
**And** a well-formed CT-23 authorized intent is admitted unchanged — the ports execute it and never re-size it (AR-56, B-6).

**AC3 — AD-40 full-loss precondition before any open**
**Given** an authorized intent that opens or increases a position
**When** no AD-40 full-loss price is present on the intent
**Then** the fill port is not invoked and a typed refusal is returned before any open (AR-56, B-3)
**And** a risk-reducing CT-29 exit intent is admitted without requiring a new full-loss price (FR-032).

**AC4 — fidelity identity and the optimistic taint**
**Given** any bound adapter
**When** the port-set stamps a fill's fidelity identity
**Then** the identity is `(adapter-id + composition-version + taint)` and the taint field is `optimistic` for every non-live fill until GAP-0048 (B-6, SC-06)
**And** composition-version changes whenever the bound port set or its order changes, so identity never silently drifts (B-6, AR-59).

**AC5 — lowest-fidelity aggregation and mixed-fidelity comparison refusal**
**Given** a run binding adapters of differing fidelity
**When** the run's fidelity is computed
**Then** it is the LOWEST fidelity of any bound adapter (B-6)
**And** when two Book-bar results of differing fidelity are compared without an explicit override, the comparison returns a typed refusal (LABEL-3, B-6)
**And** the fuller fidelity taxonomy that orders these labels is consumed as a deferred artifact — no ordinal values are invented here (SC-07).

**AC6 — world derivation and GAP-0048 gating**
**Given** a run whose provenance resolves `world=simulated`, or a config binding a replay clock to synthetic-tainted data
**When** the port-set is composed
**Then** `world=simulated` is refused and the replay-on-synthetic config is `invalid input` (B-7)
**And** every optimistic-tainted run is barred from spending split budget and from any edge or verdict claim until GAP-0048 (SC-06, B-6).

### Story 17.2: Synthetic-spread model and SQS spread input

As the factory developer,
I want a spread model that supplies calibrated bid/ask when the feed lacks quotes and exposes this run's modeled-spread series,
So that trade-only backtests never silently fill buy = sell and the Book's SQS door has an honest spread input in non-live runs.

**Acceptance Criteria:**

**AC1 — synthetic bid/ask keyed by instrument × hour × session**
**Given** a trading stream carrying trade-only bars (no quote data)
**When** fill pricing needs bid/ask
**Then** the spread model supplies bid/ask keyed by instrument × hour-of-day (UTC) × session from its bound calibration artifact (SPREAD-1)
**And** it never returns an equal buy/sell price silently — absence of a spread source is surfaced, not zeroed (SPREAD-1, FILL-3).

**AC2 — calibration artifact fingerprinted, content deferred, absence refuses**
**Given** the spread model being bound
**When** it resolves its source
**Then** it consumes a versioned, fingerprinted per-broker calibration artifact (DEC-0135) whose spread content is measured from QMX's own recorded bid/ask ticks (B-6) and stays deferred to GAP-0048
**And** when no calibration artifact is bound for the instrument, the model returns a typed refusal (CT-04), never a silent zero spread
**And** the model embeds no invented spread numbers (SC-07).

**AC3 — real quotes take precedence and rank higher fidelity**
**Given** a feed that does carry real quotes
**When** spread is resolved
**Then** the real quote spread takes precedence over the synthetic model (SPREAD-2)
**And** a run using real quotes is recorded at a higher price-basis fidelity than a synthetic-spread run, with the ordinal taxonomy deferred to GAP-0048 (B-6, SC-07).

**AC4 — SQS door consumes the modeled-spread series**
**Given** a non-live run
**When** the Book's SQS door (AD-39) needs its spread input
**Then** the spread model exposes this run's modeled-spread series as that input (B-2)
**And** the series cites exact `Price` values, never binary floats (CT-01, FR-001).

**AC5 — calibration fingerprint in the result label**
**Given** a run that bound the synthetic-spread model
**When** the CT-32 result artifact is labeled
**Then** the spread calibration artifact fingerprint is declared in the label (B-10, B-13, AR-59).

### Story 17.3: Fill and slippage price-forming pipeline

As an agent,
I want the fill port to decide Fill/NoFill/PartialFill and a pre-slip price by honest crossing of each slice's declared path, and the slippage port to map that to a post-slip price or veto it,
So that my backtest fills reflect worst-case OHLC reality and deterministic in-slice ordering rather than the optimistic exact-wick fills a naive loop would grant.

**Acceptance Criteria:**

**AC1 — fill decision and pre-slip price by declared-path crossing, dispatched per order type**
**Given** a CT-23 authorized intent resting against a slice's declared intra-slice path
**When** the fill port evaluates it in run-loop sub-phase 3 (B-2)
**Then** it returns `Fill | NoFill | PartialFill` and, on a fill, a pre-slip price computed by crossing the declared path, dispatched per order type — market, limit, stop, stop-limit, trailing-stop, market-on-open, market-on-close, and an all-or-none group (FILL-2, B-6)
**And** an all-or-none group in which any leg fails returns NoFill for the whole group (FILL-2).

**AC2 — worst-case default with a labeled optimistic-exact mode**
**Given** a limit or stop order that the declared path crosses
**When** the default fill port prices it
**Then** the price is bar-worst-case (buy limit = `min(high, limit)`; sell limit = `max(low, limit)`; stop = worst of stop vs current ± slip) (FILL-4)
**And** when the run-config selects optimistic-exact mode the fill price is the exact order price but the fill stamps a distinct fill-basis in its fidelity label (FILL-4)
**And** both modes remain `optimistic`-tainted until GAP-0048 (SC-06, B-6).

**AC3 — partial fills capped by position size and lot step**
**Given** an intent whose fillable quantity is less than the order quantity
**When** the fill port fills
**Then** it emits a PartialFill with `filled_qty < order_qty`, caps a `reduce_only` fill to the open position size, and rounds to the instrument lot step (FILL-8)
**And** each partial emits its own `Fill` carrying its own pro-rated fee reference (B-6, FILL-8).

**AC4 — stale-data guard, gap fills, and typed NoFill reasons**
**Given** a resting order whose bar end precedes order submission, or a market order beyond the configured `stale_price_span`
**When** the fill port evaluates it
**Then** it returns a typed NoFill carrying a reason code from `market_closed | stale_data | not_triggered | insufficient_liquidity | all_or_none_leg_failed` (FILL-1, FILL-5)
**And** an order whose price sits in a between-bar gap fills at the gapped price with a `gap_fill` marker rather than being skipped (FILL-7).

**AC5 — deterministic intra-slice sequencing; new intents rest**
**Given** several resting orders that fall inside one slice
**When** they fill
**Then** they fill in a deterministic order derived by splitting the declared path at each fill price, reproducible without tick data (FILL-6, B-2)
**And** intents newly minted by strategy callbacks in this slice (sub-phase 5) are not eligible to fill against this slice's path — they rest for a later slice (B-2 sub-phase 6).

**AC6 — slippage maps pre-slip to post-slip and may veto**
**Given** a fill's pre-slip price
**When** the slippage port runs (composition order after fill)
**Then** it maps pre-slip → post-slip price (buy `+`, sell `−`) using the config-selected FX slippage model — `zero | constant-percent | spread-crossing | gap-volatility | size-tiered` — each parameterized by its calibration artifact with no invented numbers (SLIP-2, SC-07)
**And** the slippage port may veto the fill (return NoFill) when the slipped price is not a legal print on the slice (B-6, SLIP-1)
**And** it is not applied to passive limit fills unless explicitly configured, and any stochastic term draws from a per-run seed derived from run identity so replay reproduces the same draw (SLIP-1, SLIP-3, B-13).

### Story 17.4: Cost port — exact-integer itemized commissions

As an agent,
I want the cost port to itemize commission as exact-integer money in its own currency, queryable both for margin admission and at fill time,
So that commission cost drag is separately attributable and reconciles deterministically without a single float rate ever touching the money path.

**Acceptance Criteria:**

**AC1 — typed fee in its own currency, exact-integer money**
**Given** a post-slip fill
**When** the cost port itemizes commission
**Then** it returns a typed fee amount in its own currency mapped to exact-integer `Money` (CT-01, FEE-1)
**And** no float commission rate ever touches the money path (CT-01, FR-001).

**AC2 — per-fill itemization and per-partial pro-rate**
**Given** an intent filled across several partials
**When** commission is charged
**Then** each partial carries its own pro-rated commission, itemized separately (B-6, FILL-8)
**And** commission is a distinct line item, never folded into fill P&L (FEE-5).

**AC3 — commission shapes, calibration-parameterized, no invented rate**
**Given** the cost port
**When** a commission model is selected by run-config
**Then** the shape is one of `zero | percent-of-notional | per-lot/per-1k-units | notional-proportional-with-per-order-minimum` (FEE-2)
**And** each shape is parameterized by a versioned per-broker calibration artifact (DEC-0135) whose rate content is deferred to GAP-0048 — no rate is invented (SC-07).

**AC4 — double-call determinism for admission and charge**
**Given** the same fill inputs
**When** the fee contract is queried before the fill for margin/buying-power admission and again at fill time for the actual charge
**Then** both calls return the identical amount (FEE-3)
**And** a fee queried for admission whose fill does not occur charges nothing.

**AC5 — absent calibration refuses, never zero**
**Given** a commission model whose calibration artifact is missing
**When** the cost port is invoked
**Then** it returns a typed refusal (CT-04), never a silent zero commission (FEE-1, B-6).

### Story 17.5: Daily-swap financing as a scheduled rollover cash event

As the operator,
I want overnight swap financing applied to open positions as a scheduled cash event at the per-broker accounting rollover, logged as its own journal event,
So that multi-day results are never silently free of carry and total cost drag decomposes cleanly into fill P&L, slippage, commission, and financing.

**Acceptance Criteria:**

**AC1 — scheduled position-level cash event at the accounting rollover (sub-phase 2)**
**Given** open positions at the per-broker AD-8 accounting-rollover instant (never hardcoded)
**When** the run loop reaches sub-phase 2, scheduled position-level events (B-2)
**Then** the financing scheduler applies a swap as an exact-integer `Money` debit or credit to each open position — not an order fill — per instrument and per direction (long/short) (AR-56, B-6, FEE-4)
**And** it is applied at the rollover, not per slice (B-6).

**AC2 — triple-swap day and weekend/holiday, calendar-scheduled, no invented content**
**Given** a bound broker swap-schedule calibration artifact
**When** the scheduler computes the swap for a rollover
**Then** it honors a configurable triple-swap day and weekend/holiday handling from that calendar-scheduled per-broker artifact (FEE-4, DEC-0135)
**And** swap points, the sign convention (carry may be a credit), and the triple-swap weekday are read from the artifact — never invented (SC-07).

**AC3 — absent swap table refuses, never zero**
**Given** an open multi-day position whose instrument has no bound swap table
**When** a rollover occurs
**Then** financing returns a typed refusal (CT-04), never a silent zero swap (FEE-4).

**AC4 — distinct journal event and cost-drag decomposition**
**Given** a swap applied to a position
**When** it is recorded
**Then** it is emitted as a distinct CT-13 journal event, separate from fill P&L, slippage cost, and commission (FEE-5, B-4)
**And** the result artifact can decompose total cost drag into fill P&L, slippage, commission, and financing as separately attributable line items (FEE-5, B-10).

**AC5 — fidelity label and GAP-0048 gating**
**Given** a run that applied financing
**When** the CT-32 result artifact is labeled
**Then** the financing calibration fingerprint is declared in the label (B-10, B-13, AR-59)
**And** the run remains `optimistic`-tainted, barred from edge claims and split-budget spend until GAP-0048 (SC-06, B-6).

## Epic 18: QMB data management

Download, verify, gap-check, and catalog market-data windows — calendar-aware, behind the ship-no-corpus licensing gate — as thin `qmb data` fronts over the ratified QMF data contracts, so data is acquired once under the operator's own provider relationship into the immutable raw archive and every run reads that archive rather than fetching from a provider. (FR-042; B-11; AR-54)

### Story 18.1: The `qmb data` command group and download-once acquisition

As the operator,
I want a `qmb data download` command that fetches a market-data window once, under my own provider relationship, into the QMF immutable raw archive,
So that QMX owns its stored source and every experimentation run reads that archive instead of ever fetching from a provider.

**Acceptance Criteria:**

**Given** the `qmb` CLI and Python API doors from Epic 16 (click==8.4.2) and qmf-data's CT-15 idempotent intake seam plus CT-10 bitemporal store from Epic 6,
**When** the `data/` module registers the `data` command group,
**Then** `data download` is a thin front over CT-10/CT-15 that adds no second data layer (B-11) and carries only parsing, transport, and adapter-selection logic (B-1) — the `qmf.data` contracts own all persistence.

**Given** a `(venue, symbol[list], start, end, resolution, side ∈ {bid, ask, both})` request drawn from a Book/BMS config fragment or invocation flags, with `end` defaulting to today but accepting an explicit end for a reproducible window,
**When** download runs,
**Then** it fetches through a QMX-authored provider-adapter port (`fetch`, `earliest_available`, `list_symbols`, batch `count`, rate-limit) with Dukascopy as adapter #1 (dukascopy-node-class downloader is reference-only; no third-party downloader code is vendored, per AR-54/dossier R6),
**And** a provider error — maintenance, geo-block (HTTP-451-class), bad window, or missing entitlement — returns a typed refusal (CT-04 category + machine-readable context + retryability) rendered per transport (AR-58), never a silent partial ingest.

**Given** fetched ticks or bars,
**When** they land in the raw archive,
**Then** bid and ask are preserved as distinct streams (never collapsed to one OHLCV; AR-46 bid+ask preserved), timestamps are int64 UTC-ns and prices are exact scaled integers crossing a named AD-22 conversion boundary (never provider-native floats/decimals unconverted; CT-01/AR-15), written as CT-10 bitemporal source observations into the world-scoped raw room (CT-11) and retained forever.

**Given** a window that overlaps one already ingested,
**When** download re-runs with the same inputs,
**Then** it is idempotent via the bitemporal key (already-present observations skipped, not duplicated),
**And** `--overwrite` appends a new revision under CT-10 revision keys rather than mutating the only copy.

**Given** a long import,
**When** it runs,
**Then** it emits machine-observable progress (percent, date-reached, ETA) on a supervising agent's channel — not only a human progress bar,
**And** each ingested window records its provenance plus a licence tag as CT-10 source-observation metadata (the tag recorded here is the input the Story 18.2 gate enforces).

**Given** any run loop, backtest, sweep, or optimize trial,
**When** it needs data,
**Then** it reads only qmf-data rooms and has no path to a provider (AR-54): `data download` is the sole provider-fetch surface, and a run that attempts a provider fetch is a `policy rejection`.

### Story 18.2: The ship-no-corpus licensing gate

As the operator,
I want a licensing gate that turns each window's recorded licence tag into a typed refusal whenever the window lacks a usage right for governed-evidence use,
So that QMX never treats unlicensed data as governed evidence and never ships or redistributes a market-data corpus.

**Acceptance Criteria:**

**Given** each window carries a recorded licence tag from Story 18.1,
**When** the gate evaluates a window for governed-evidence use,
**Then** it returns value-or-typed-refusal (CT-04/AR-13): a tag that grants the requested use passes, while a tag of `denied`, `unknown`, or absent is a typed refusal for governed-evidence use (B-11), carrying the `(venue, symbol, window)` and the tag state as machine-readable context.

**Given** the licence-tag taxonomy is a policy input,
**When** tags are asserted,
**Then** the recognized states are an explicit interface (redistribution-ok / internal-only / denied / unknown) resolved from a per-venue policy record or operator ruling — never inferred silently by the provider adapter,
**And** any state the operator has not ruled is left blank (SC-07 interfaces-not-numbers), a blank being treated as `unknown` and thus blocking governed-evidence use.

**Given** the old Dukascopy corpus failed the licensing gate (B-11 open ops item),
**When** a Dukascopy window with no recorded usage right is used,
**Then** it still ingests and is catalogable, and non-evidence use (infrastructure stress, strategy-logic smoke) is allowed, but governed-evidence citation is refused until a usage right is recorded.

**Given** QMB packaging,
**When** the wheel is built and shipped,
**Then** it contains and redistributes no market data (AR-54): a Tier-2/release check asserts the distribution bundles zero corpus bytes.

**Given** a window that passes the gate,
**When** it is cited as governed evidence,
**Then** the licence tag and its granting authority ride into the citing artifact's lineage (CT-07) so the entitlement basis is auditable,
**And** the gate is a pure read-time check that writes nothing.

### Story 18.3: `qmb data list` — catalog by (venue, symbol, window, side)

As an agent,
I want `qmb data list` to report exactly what windows are present in the rooms, keyed by (venue, symbol, resolution, side),
So that before requesting a download I can answer "do I already have this window?" and cite the right coverage.

**Acceptance Criteria:**

**Given** windows ingested through Story 18.1,
**When** `data list` runs,
**Then** it reports, per `(venue, symbol, resolution, side ∈ {bid, ask})`, the covered `[start, end]`, observation/bar count, provenance, licence tag, and current bitemporal revision (FR-042 catalog by `(venue, symbol, window, side)`).

**Given** the catalog is a read over the rooms,
**When** it computes coverage,
**Then** it is served through qmf-data contracts as a thin front (B-11) via a rebuildable DuckDB view over the Parquet rooms (AR-30) — a rebuildable view, never an authoritative second store.

**Given** an agent asks about a specific `(venue, symbol, window, side)`,
**When** that window is absent,
**Then** the catalog returns an explicit "not present" result as a value (not a refusal) so the agent can decide to download — an absent window is a normal answer, not an error.

**Given** both bid and ask were requested but only one side is present,
**When** `data list` reports,
**Then** the missing side is shown as absent for that `(venue, symbol, resolution)` so a run needing both sides detects the shortfall before it starts.

**Given** door parity (B-1),
**When** the same catalog query runs through the CLI and the Python API door,
**Then** both return the identical machine-readable coverage payload (enforced by a Tier-2 door-parity contract test), the CLI rendering it as machine-readable output and the Python door returning the value verbatim (AR-58).

### Story 18.4: `qmb data verify` — window integrity

As an agent,
I want `qmb data verify` to check an acquired window's integrity and return a typed pass/fail result,
So that I never build on a window the provider silently truncated or corrupted.

**Acceptance Criteria:**

**Given** a window in the rooms,
**When** `data verify` runs,
**Then** it checks that bid and ask streams are both present where `both` was requested, that timestamps are monotonic int64 UTC-ns, and that prices are exact scaled integers with no float taint (CT-01/AR-15), returning a typed result carrying the counts and any defects.

**Given** a provider can return a range whose edges are off (Jesse's `MAX_MISSING_EDGE_MINUTES`-analog range-integrity guard),
**When** verify applies the guard,
**Then** the edge tolerance is a configurable interface with no invented number (SC-07); a blank tolerance leaves the guard un-armed and verify reports the raw edge offsets rather than passing or failing against a fabricated threshold.

**Given** a defect (edge offset beyond an armed tolerance, a requested side missing, a non-integer price taint, or an empty provider return),
**When** verify completes,
**Then** it returns a typed refusal (CT-04) with machine-readable context, never a silent pass.

**Given** verify must never fabricate data,
**When** it finds interior gaps,
**Then** it reports them and does not fill them — any synthetic fill is out of scope for verify and would be a `world=simulated` derived layer (B-7/L20), never written as observed.

**Given** the integrity outcome,
**When** verify finishes,
**Then** the pass/fail verdict is a factual data-quality result (never an edge- or verdict-bearing claim) recorded through qmf-data journaling (CT-13) with a propagated `correlation_id` (AR-35),
**And** a re-run over the same immutable window reproduces the same verdict (NFR-03 determinism).

### Story 18.5: `qmb data gap-check` — calendar-aware gap detection

As an agent,
I want `qmb data gap-check` to distinguish a venue being closed from data actually missing, using the versioned trading calendar,
So that a weekend or holiday is never mistaken for a data gap and a real hole is never hidden.

**Acceptance Criteria:**

**Given** a window and its `(venue, symbol)`,
**When** `data gap-check` runs,
**Then** it resolves expected sessions from the CT-02 versioned trading calendar (the qmf-calendar-forex provider from Epic 4 for FX venues), computes expected-bars-minus-present-bars per session, and reports gaps as `(start, end, expected, present)`.

**Given** the calendar marks the venue closed (weekend / holiday / half-day / late-open),
**When** bars are absent there,
**Then** gap-check classifies that absence as real closure and not a gap; where the venue is open but bars are absent, it classifies a genuine data gap — the calendar is the authority that makes the two decidable (dossier R2/R5).

**Given** a 24/7 venue reading an always-open CT-02 calendar,
**When** gap-check runs,
**Then** every non-present interior interval within an open window is a genuine gap (no closure exemption applies).

**Given** the resolved calendar version participates in the answer,
**When** gap-check reports,
**Then** it records which CT-02 calendar version it used, and re-running with the same window and same calendar version yields the identical gap set (NFR-03 determinism).

**Given** gap-check must not fabricate,
**When** it finds gaps,
**Then** it only reports them and never writes interior fill — producing a filled series is Epic 23 synthetic territory, `world=simulated`, and a `policy rejection` for governed evidence until GAP-0048 (SC-06/B-7).

**Given** a missing or unresolvable calendar for a `(venue, symbol)`,
**When** gap-check cannot decide open-vs-closed,
**Then** it returns a typed refusal (`unavailable dependency`, CT-04) rather than guessing — an unknown calendar is never silently treated as always-open.

## Epic 19: QMB reports & result artifacts

Every QMB run emits exactly one canonical, machine-readable CT-32 result artifact
carrying the full AR-59 label set; the artifact holds the QMX-native measure set —
unit-kinded, exact, governed, with suppression/veto accounting and no composite
score; chart data is emitted as series, never images; and every human-facing
rendering, interpretation, and reproduction is a pure downstream function of the
artifact — agents read the artifact, never renderings. (FR-043; B-10/B-13; AR-59;
spec-reports R-RPT-*)

### Story 19.1: The canonical CT-32 result artifact and its full label set

As the factory developer,
I want a completed run's pure return assembled into exactly one CT-32
performance-result container stamped with the full AR-59 label and written into the
run's output directory,
So that one canonical artifact serves both the admission-bar evidence reader and the
agent/operator report, with no second "report JSON" that could drift from the
evidence.

**Acceptance Criteria:**

**Given** a completed replay run's pure return (B-4)
**When** the `results/` assembly runs
**Then** it writes exactly one CT-32 container into the run's output directory and
returns its `fp1`
**And** the container carries the full AD-12 label: producer contract identity +
integer format version, input fingerprints, evidence time range (the trading
interval only, never the warm-up interval per B-2/SC-10), occurrence identity,
evidence class, world, and account-binding role. (AR-59, B-10, B-4, R-RPT-1, R-RPT-2)

**Given** the same artifact
**When** the label is stamped
**Then** it additionally carries the resolved-config fingerprint (the run id root),
`registry_as_of` (B-15), data/split fingerprints, fidelity identity, and RNG
provenance where the run is stochastic. (AR-59, B-13)

**Given** the artifact's identity is computed
**When** `fp1` is derived
**Then** identity is label-derived per AD-10 and computed only by calling qmf-core's
canonical `fp1:sha256` function (AR-14) — no other module recomputes it, and no float
bytes ever enter identity. (R-RPT-6, AR-14)

**Given** a run whose result would span more than one account-binding role
**When** the assembly runs
**Then** it returns a typed policy-rejection refusal and writes no artifact. (R-RPT-7)

**Given** `world` is copied verbatim from the run's data-derived provenance, never
from a flag (B-7)
**When** the run resolves to `world=replay`
**Then** the label records `world=replay`; **And** a store-tainted `world=simulated`
run has already refused upstream (B-7/SC-06), so no such artifact is produced in V1.

**Given** every V1 fill carries the `optimistic` taint (SC-06/B-6)
**When** the fidelity identity is stamped (adapter-id + composition-version + taint)
**Then** the artifact is non-edge-claiming by construction — it carries no verdict-
bearing claim, cannot claim edge, and its evidence cannot spend split budget until
GAP-0048 closes. (SC-06, B-6)

### Story 19.2: The QMX-native measure set — ordered, unit-kinded, exact, governed, no composite score

As an agent,
I want the artifact's `measure_set` to hold ordered, unit-kinded, exact measures
whose arithmetic is pinned by each metric's own producer-contract format version,
So that I can reason over one run and compare two runs without ever re-deriving a
number or trusting a formatted string.

**Acceptance Criteria:**

**Given** the assembly computes the V1 core measure set (net profit, CAGR, start/end
equity, Sharpe, Sortino, Calmar, max drawdown + recovery, total/winning/losing trade
counts, win rate with long/short split, profit factor, expectancy, average/largest
win and loss, gross profit/loss, fees, streaks)
**When** each measure is emitted
**Then** it is a member of an ordered `measure_set` and carries a non-null unit-kind
from the closed AD-40 vocabulary. (R-RPT-3, B-10)

**Given** a measure whose unit-kind would be null
**When** it is assembled
**Then** the assembly returns an invalid-input typed refusal — a null unit-kind is
never silently defaulted. (R-RPT-3)

**Given** money measures (net profit, fees, gross profit/loss, largest win/loss,
start/end equity)
**When** they are emitted
**Then** they are exact scaled integers at the declared currency scale, never binary
float; **And** time measures (durations, underwater period, drawdown recovery) are
int64 UTC-ns or a typed `duration`. (R-RPT-4, AR-15)

**Given** each metric's arithmetic (e.g. Sharpe's annualization basis, rf model, ddof)
**When** the metric is emitted
**Then** its arithmetic is pinned by its own `metric_contract_format_version`, so
changing how a metric is computed is a format-version mint with before/after evidence,
never a silent code change. (R-RPT-5)

**Given** a metric that cannot be computed (fewer than 2 daily samples; no losing
trades, so profit factor is undefined)
**When** it is assembled
**Then** it emits a typed "undefined / insufficient-sample" refusal that a reader can
tell apart from zero — never a magic cap of 10 and never NaN coerced to 0. (R-RPT-3)

**Given** the full measure set
**When** the artifact is produced
**Then** no single composite score, grade, tier band, or weighted rating appears
anywhere in it — the artifact presents the set and never collapses it into one number;
**And** producing the artifact sizes nothing, promotes nothing, benches nothing, and
changes no mode. (R-RPT-10, R-RPT-9, B-10)

### Story 19.3: Suppression and veto accounting

As the operator,
I want the artifact to carry explicit suppression accounting (keyed by authority +
reason) and veto accounting (keyed by door),
So that the run's own control-windows and admission-door refusals are never misread as
strategy or alpha decay.

**Acceptance Criteria:**

**Given** a completed run whose CT-13 journal streams record control-window
suppressions and admission-door vetoes (B-4)
**When** the artifact is assembled
**Then** it carries a suppression tally keyed by `(authority, reason)` and a veto
tally keyed by `door`, both derived only from the run's own CT-13 journal streams —
never a parallel bespoke log. (R-RPT-8, B-10, B-4)

**Given** a run in which no action was suppressed and no door vetoed
**When** the artifact is assembled
**Then** the suppression and veto sections carry explicit zero counts — keys are never
omitted. (R-RPT-8)

**Given** the suppression and veto tallies
**When** they are emitted
**Then** each count carries the `count` unit-kind from the AD-40 vocabulary, and the
two tallies form a distinct field group from the returns/trade measures so a control-
heavy window is never folded into an alpha figure. (R-RPT-3, R-RPT-8)

**Given** this accounting has no analogue in either source platform
**When** an interpretation skill reads the artifact
**Then** it can attribute action count directly to control authority versus strategy
decision without re-deriving anything. (R-RPT-8, R-RPT-22)

**Given** a journal event whose suppression authority or reason is unresolvable
**When** the tally is built
**Then** the assembly returns a typed refusal rather than dropping or silently
bucketing the event. (R-RPT-8, AR-13)

### Story 19.4: Chart series as data, never images

As an agent,
I want every chart emitted as a machine-readable series derived from the run's own
position/order/journal record, never as an image,
So that I read chart data directly instead of parsing pixels, and no renderer can
produce a series the evidence disagrees with.

**Acceptance Criteria:**

**Given** the run's ordered position/fill records and CT-13 journal streams
**When** chart data is assembled
**Then** each chart is emitted as a series `{ name, unit_kind, points: [{ t, v }] }`
where `t` is int64 UTC-ns and `v` is the unit-kinded value (exact-integer money or
exact-rational ratio); no image, base64, or PNG is ever the canonical payload.
(R-RPT-11, R-RPT-12, B-10)

**Given** series values
**When** points are emitted
**Then** no color, style, or histogram bin is embedded in the data — those are renderer
concerns. (R-RPT-12)

**Given** the V1 chart set (equity curve, cumulative returns, drawdown/underwater with
a top-5 worst-periods table `{start, bottom, recovery, max_drawdown}`, monthly-returns
grid, and monthly-return + trade-P&L distributions as raw histogram-ready arrays)
**When** it is assembled
**Then** each series derives solely from the run's own ordered position/order/journal
record — not a parallel log that could disagree with the ledger. (R-RPT-13, R-RPT-14)

**Given** time-varying holdings, exposure, allocation, and leverage series
**When** the run is multi-instrument or leveraged
**Then** those series are reconstructed from the same ordered position/order stream; a
single-instrument, unleveraged run omits them rather than emitting empty or faked
series. (R-RPT-13, R-RPT-14)

**Given** benchmark-relative series (cumulative-vs-benchmark, and later alpha/beta)
**When** no benchmark is declared in the Book/BMS config
**Then** those series are omitted with an explicit "no benchmark declared" note and are
never faked; when a benchmark is present its identity is recorded in the artifact.
(R-RPT-15)

**Given** a dense series
**When** a display downsample is produced
**Then** it is a display-only derivative carrying its own declared sampler identity and
is AD-10-excluded from the artifact's identity — never the canonical payload. (B-10)

### Story 19.5: Pure downstream reads — rendering, interpretation, and reproduction

As the operator,
I want every downstream use of the artifact — HTML and markdown rendering, skill
interpretation, and run reproduction — to read the CT-32 artifact and compute nothing
new,
So that the report I read, the findings agents produce, and the reproduction check all
agree by construction, and none of them can act on the result.

**Acceptance Criteria:**

**Given** a stored CT-32 artifact
**When** the HTML (operator, shareable) or markdown (agent-consumable, diffable)
renderer runs
**Then** it is a pure function of the artifact — field/token substitution only, adding
no computation and deriving no new number. (R-RPT-21, B-10)

**Given** the rendered report
**When** its headline is produced
**Then** it shows the `world` label and account-binding role verbatim and unmissably,
so a replay (or paper) result is never mistaken for a live one. (R-RPT-2, R-RPT-19)

**Given** in-house interpretation skills
**When** they explain a run, compare two runs, or flag a refusal-heavy period
**Then** they read the CT-32 artifact and never a rendering — agents never parse HTML.
(R-RPT-22, B-10)

**Given** a stored run id and its resolved run-config
**When** the run is re-executed and its CT-32 fingerprint recomputed
**Then** it must reproduce the stored fingerprint exactly, or the verify returns a
typed refusal — a mismatch is never silently tolerated. (B-10, NFR-03)

**Given** artifact production is per-run isolated in its own output directory
**When** 12–14 concurrent runs each save their own artifact
**Then** there is no shared mutable render state and no cross-run contention. (R-RPT-24,
B-5)

**Given** rendering, interpretation, and reproduction all run
**When** any of them completes
**Then** none has sized, promoted, benched, bound, or changed a mode — every downstream
read is publish-only. (R-RPT-9, B-10)

## Epic 20: QMB multi-route sweeps

Multi-symbol / multi-timeframe permutation sweeps run the full Cartesian space as a
batch of isolated, fully-labeled runs: a pre-flight run count the operator sees before
committing, exactly one registry as-of resolved at batch admission and frozen for every
combination, one ledger line per combo, and cross-run ranking as a read-time fold that
publishes and never acts. Each combination is one isolated run of the same never-forked
run loop with different variables — the batch merges nothing. (FR-038; B-12; B-15; SC-11)

### Story 20.1: Sweep axis declaration and Cartesian expansion with pre-flight run count

As the operator,
I want to declare a sweep as axes (instruments, BarSpecs, parameters) over a Book/BMS and see the exact total run count before anything executes,
So that I know the size of the batch and commit to it deliberately, never discovering a combinatorial blow-up only after compute is already spent.

**Acceptance Criteria:**

**Given** a sweep declaration naming a bot/Book/BMS context plus axes `instruments[]`, `timeframes[]` (a BarSpec list), and `parameters{name: values[]}`
**When** the library expands the sweep
**Then** it produces the full Cartesian product of the axes — one run spec per combination — in a deterministic declaration-order enumeration (B-12; spec R9)
**And** a single run is representable as a 1×1×1 sweep: the same object at unit scale, created the same way a Book config is created (spec R13)

**Given** a valid sweep declaration
**When** the pre-flight run count is computed
**Then** the count equals the product of the axis lengths and is reported before any process is spawned (FR-038; spec R9)
**And** the pre-flight count spawns no process, writes no ledger line, and admits no batch — it is a pure inspection (B-4)

**Given** the pre-flight count is requested through the `qmb` CLI
**When** the door renders it
**Then** the door is a thin wrapper (click==8.4.2) over the one pure library expansion function — the axes-to-count computation lives once in the library, never duplicated in a door (B-1)

**Given** a sweep declaration with an empty axis (a zero-length instrument, BarSpec, or parameter-value list)
**When** expansion is attempted
**Then** the library returns a typed `invalid input` refusal naming the empty axis — never a silent zero-combo batch (AD-11)

**Given** a parameter value in an axis
**When** it enters a combination's run spec
**Then** exact-integer, categorical, and boolean values are carried verbatim, and any money/rational value crosses a named AD-7/AD-22 conversion (declared rounding mode + target scale) before entering the resolved config — binary floats never appear in a run spec's identity content (B-8; AR-15; FR-001)

### Story 20.2: One registry as-of resolved at batch admission, frozen for every combination

As an agent,
I want the whole sweep to resolve exactly one registry as-of at batch admission and freeze it for every combination,
So that no two combos silently resolve different Book/BMS/bot versions mid-flight, and the sweep is reproducible against one stamped registry state.

**Acceptance Criteria:**

**Given** a sweep is admitted as a batch
**When** admission runs
**Then** it resolves exactly ONE registry as-of — a (`registry_as_of` instant + set fingerprint) — through the single library-owned registry-read port, with no door-side or second cache (B-15; AR-55; SC-11)
**And** that one as-of is frozen for the whole batch and stamped into the sweep label and into every combo's run label (B-15; spec R10)

**Given** the batch has been admitted and the as-of is frozen
**When** any combination compiles its resolved run-config
**Then** every Book/BMS/bot fragment resolves by explicit fingerprint (fp1) against the frozen as-of set — never by name@latest (B-15; B-3; B-13)
**And** two combos citing the same Book resolve the identical Book fp1: a fresher registry state arriving mid-batch never changes an in-flight or not-yet-started combination (SC-11; B-15)

**Given** an axis references a record that a fresher as-of shows superseded at admission time
**When** admission evaluates that reference
**Then** it returns an AD-11 stale-evidence refusal (severity configurable, no invented default) rather than silently binding either the stale or the fresher version (B-15; AR-55)

**Given** the frozen registry as-of
**When** it is recorded on results
**Then** it appears verbatim as the `registry_as_of` field in every combo's CT-32 label set (B-13; AR-59)

### Story 20.3: One isolated, fully-labeled run per combo with exactly one ledger line

As the operator,
I want each combination to execute as one isolated, fully-labeled run under the governor, writing exactly one ledger line, where a single combo's refusal is recorded as that combo's outcome and never aborts the batch,
So that a large overnight sweep completes with a complete per-combo evidence trail even when some combinations fail.

**Acceptance Criteria:**

**Given** an admitted sweep of N combinations
**When** the batch executes
**Then** each combination compiles to exactly one resolved, schema-validated run-config artifact whose fp1 is its run id, and executes as one isolated OS process with its own output directory under the Epic 15 orchestrator (B-3; B-5; B-12; spec R10)
**And** parallelism is bounded by the governor's min(cpu budget, memory budget) with enqueue-when-full, and concurrency never changes any single combo's result or CT-32 fingerprint (B-5; NFR-03; spec R12)

**Given** a combination completes or is aborted
**When** the orchestrator records it
**Then** it appends exactly ONE ledger line for that combo — never zero, never two — carrying the full AD-12 label, the CT-32 fingerprint, the run's raw AD-40 unit-kinded measures, and the sweep coordinates `{sweep_id, instrument, BarSpec, param-hash}` (B-4; B-13; spec R10, R11)

**Given** one combination returns a typed refusal (a stream-set violation such as `DuplicatePositionStream` or `MixedSettlementAsset`, an `invalid input` config, or an `aborted` time/memory-limit breach)
**When** that combo finishes
**Then** its refusal is recorded as that combo's labeled `aborted`/refused ledger line with refusal context, and the batch continues — one combo's refusal never aborts the sweep (spec R12; B-4; B-12)

**Given** every combo is a non-live run reading qmf-data rooms
**When** each combo's result is labeled
**Then** `world` derives from data provenance — world=replay for archived reads; a store-tainted read is world=simulated and refuses per GAP-0048 — and every fill carries the `optimistic` taint, so no combo emits a verdict-bearing edge claim (B-7; B-6; SC-06)

### Story 20.4: Cross-run ranking as a read-time fold over the sweep's ledger

As an agent,
I want to rank and filter a sweep's combinations by a declared objective measure with optional constraints, computed as a read-time fold over the sweep's ledger lines and their CT-32 measures,
So that I can find the best- and worst-scoring combinations without re-running anything and without any ranking ever acting on money.

**Acceptance Criteria:**

**Given** a completed sweep's ledger lines (one per combo, each citing a CT-32 fingerprint and carrying the run's raw AD-40 measures)
**When** cross-run ranking is requested
**Then** ranking is a pure read-time view over the world-and-role-scoped ledger merge — never a merged or re-run computation — ordered by a declared objective `measure_identity` from the AD-23/AD-41 roster (B-12; B-4; B-10; FR-038)
**And** the fold reads only combos belonging to this `sweep_id` and never mixes worlds or roles (B-4)

**Given** an optional constraint filter expressed as metric-operator-value (for example a max-drawdown bound)
**When** ranking applies it
**Then** only combos satisfying the constraint are ranked, and the operator or agent supplies the comparison value as a configurable — no threshold number is invented (spec R11; SC-07; NFR-07)

**Given** ranking produces best/worst orderings
**When** results are returned
**Then** ranking publishes and never acts: it produces no composite score that gates money, mints no promotion, and binds nothing (B-10; FR-034)
**And** every ranked combo carries its `optimistic` taint and world label forward; the ranking makes no edge claim and no unbiased pass/fail verdict — the per-combo verdict rule and the multiple-comparisons statistic stay deferred to GAP-0048/0049 (SC-06; SC-07; B-14)

**Given** a combo whose ledger line is a refusal/`aborted` outcome with no CT-32 measures
**When** ranking runs
**Then** that combo is excluded from the objective ordering and reported in a separate refused/incomplete list — never silently dropped and never coerced to a zero score (AD-11; spec R12)

**Given** the same completed sweep and the same objective plus constraints
**When** ranking is recomputed
**Then** it is deterministic and reproducible — a pure downstream function of the CT-32 artifacts and the ledger, adding no computation of its own (B-10; NFR-03)

## Epic 21: QMB optimization studies

Parameter-optimization Studies over a Book/BMS deliver a typed search space,
an objective plus hard constraints, train/test split discipline with
fingerprinted split manifests, the optuna 4.9.0 TPE-class default sampler
driven in deterministic generations, resume, cost estimation, and an
anti-overfit sensitivity report — every trial a first-class `role = trial` run
under B-3/B-4, every fill `optimistic`-tainted until GAP-0048, no invented
thresholds. Locked-validation third split and grid/Euler samplers are deferred
out of V1. (FR-039; spec-optimization intake; QMB spine B-8; SC-11)

### Story 21.1: Typed parameter search space schema

As an agent,
I want to declare a Study's parameter space as a typed, bounded schema that validates at Study creation,
So that an invalid space is refused up front instead of corrupting trials or the money path.

**Acceptance Criteria:**

**Given** a Study config declaring parameters, each with `name`, `type` ∈ {exact integer, exact rational, categorical, boolean}, and (for numeric) `min`/`max`/optional `step`/`default`, or (for categorical) non-empty `options` + `default`
**When** the space is validated at Study creation
**Then** it is accepted and materialized as identity-bearing content of the resolved run-config — never a code edit to swap the tunnel. (B-8; OPT-1/OPT-2)

**Given** a numeric parameter where `min > max`, or `step <= 0`, or `step > (max − min)`
**When** the space is validated
**Then** a typed `invalid input` refusal is returned naming the offending parameter and the violated rule — never a silent clamp. (B-8; OPT-3; AD-11)

**Given** a categorical parameter with empty `options`, or a `default` not present in `options`
**When** the space is validated
**Then** a typed `invalid input` refusal is returned.

**Given** a parameter declared as money
**When** its `min`/`max`/`step`/`default` are read
**Then** every bound is an exact-integer minor-unit value at the declared scale; a binary float appearing anywhere in the space is an `invalid input` refusal (money-path float ban). (FR-001; AD-7/AD-22; OPT-4)

**Given** a valid space
**When** the resolved config is fingerprinted
**Then** the parameter space is identity content (AD-10), so two Studies declaring the same space share the space fingerprint and the money path never sees a float in identity. (B-8; AR-14)

### Story 21.2: Study objective and hard constraints

As an agent,
I want to name one objective metric with a direction plus any number of hard constraint filters,
So that trials rank by a real, resolvable measure and degenerate fits are excluded rather than winning.

**Acceptance Criteria:**

**Given** a Study config with objective `{ measure_identity, direction }` where the measure resolves in the AD-23/AD-41 governed-producer roster and `direction` ∈ {min, max}
**When** the Study is created
**Then** it is accepted; a `direction` outside {min, max} is a typed `invalid input` refusal. (B-8; B-10; OPT-5)

**Given** an objective or a constraint naming a metric absent from the roster
**When** the Study is created
**Then** a typed refusal is returned at creation time, never deferred to trial time. (OPT-8; AD-11)

**Given** N hard constraints `{ measure_identity, op, value }` with `op` ∈ {`<`, `<=`, `>`, `>=`, `=`, `!=`} and a trial whose result violates one
**When** the winner set is computed
**Then** that trial is excluded from the winner set yet still appears in the ledger with the violated constraint named. (B-8; OPT-6)

**Given** a minimum-trades gate expressed as a constraint
**When** no explicit floor is configured
**Then** the gate is on by default and its floor is a UI-editable configurable with no spine constant — a blank floor is permitted and no number is invented (thresholds deferred). (OPT-7; NFR-07; L38; SC-07)

**Given** an optional `target_value` on the objective
**When** a completed generation contains a trial meeting it
**Then** the Study may stop early, transitioning to a clean terminal state with partial results preserved. (OPT-5; OPT-18)

**Given** the Study completes
**When** a winner is named
**Then** it is a read-time ranking over ledger `role = trial` lines and carries no edge claim and no bar verdict — the `optimistic` taint and the no-verdict rule stand until GAP-0048. (B-4; B-6; SC-06)

### Story 21.3: Train/test split discipline with fingerprinted split manifests

As an agent,
I want each trial scored on a training split and also run and recorded on a testing split, both named by split-manifest fingerprint,
So that I can judge overfit from out-of-sample results while the sealed holdout stays untouched.

**Acceptance Criteria:**

**Given** a Study naming a training split manifest and a testing split manifest by fingerprint
**When** a trial runs
**Then** the training run computes the objective and the testing run executes the identical parameter set and records its measures without contributing to the objective. (B-8; OPT-9)

**Given** a trial's two runs
**When** the trial ledgers
**Then** both split-manifest fingerprints appear on the trial label; "train"/"test" are display aliases only and are never substituted for the fingerprints. (B-8)

**Given** any split read
**When** qmf-data serves it
**Then** the 12-month seal, embargo, knowledge-time, and calendar-in-band rules are enforced at the boundary and the sealed holdout is excluded from default access. (FR-012; CT-11; CT-12; AR-16 seal law)

**Given** a trial's fills
**When** the result label is written
**Then** every fill carries the `optimistic` taint, the run cannot spend split budget, and no edge- or verdict-bearing claim is emitted. (SC-06; B-6; GAP-0048)

**Given** a Study config that would resolve to `world = simulated` (any run reading store-tainted synthetic data)
**When** admission is attempted
**Then** it is a `policy rejection` — Studies run `world = replay` only in V1. (B-7; SC-06)

**Given** warm-up
**When** a trial's window is resolved
**Then** warm-up length is the split manifest's declared embargo observation count (AD-22 count, never a Duration) and the evidence range on the result label is the trading interval only. (B-2; SC-10)

### Story 21.4: Optuna 4.9.0 TPE-class default sampler in deterministic generations

As an agent,
I want the default sampler to be a genuinely adaptive TPE-class optuna 4.9.0 sampler driven in deterministic generations,
So that a seeded Study proposes identical trials regardless of completion order and every trial is reproducible.

**Acceptance Criteria:**

**Given** a declared space, a seed, prior trial results read from the ledger view, and a generation index
**When** the pure sampler port is called
**Then** it returns the next parameter batch as a deterministic function of exactly those inputs — no in-process optuna study, daemon, or optuna store is consulted for trial history. (B-8; B-4; AR-50)

**Given** a running Study
**When** a generation is proposed
**Then** the orchestrator spawns the batch process-per-run under the Epic 15 governor with the optuna adapter pinned `n_jobs=1`, barriers on the whole generation, conditions the sampler on the completed generation, then proposes the next — so two runs of the same seeded Study propose identical trials regardless of completion order (propose → run → barrier → condition). (B-5; B-8; SC-11; AR-50)

**Given** a TPE-class adapter
**When** a second `ask` is issued before the outstanding generation's `tell`
**Then** it is refused with `unsupported capability`. (B-8)

**Given** the sampler proposes an internal float for an exact-integer or exact-rational parameter
**When** the value enters the resolved run-config
**Then** it passes a named AD-7/AD-22 conversion (declared rounding mode + target scale) and only the converted value is identity-bearing — the internal float never enters identity. (B-8; AD-7/AD-22)

**Given** batch admission
**When** the Study is admitted
**Then** exactly one registry as-of set is resolved through the single B-15 registry-read port and frozen for every trial and stamped into the Study label; after admission, fragments resolve by explicit fingerprint, never by name@latest. (B-15; SC-11)

**Given** any trial
**When** it ledgers as `role = trial`
**Then** its label carries sampler identity, seed, generator provenance, and `study_fp` (the study artifact before this ask), so re-running the trial under its resolved config reproduces its CT-32 fingerprint or refuses; a future optuna major bump is a contract-versioning event, never a transparent update. (B-8; B-10; AR-29)

### Story 21.5: Study resume and cost estimation

As the operator,
I want to estimate a Study's cost before committing compute and resume an interrupted Study without re-running completed trials,
So that long unattended sandbox runs are cheap to plan and safe to restart.

**Acceptance Criteria:**

**Given** an interrupted Study with completed trials in the ledger
**When** it is resumed
**Then** completed trials are read from the ledger view and are not re-run, and the deterministic generation index resumes from the last completed generation. (B-8; OPT-23)

**Given** resume relies only on the ledger view
**When** resuming
**Then** no in-process optuna study or daemon state is required — the ledger is the sole source of trial history. (B-4)

**Given** a Study config with an explicit trial-budget policy (fixed N | scale-with-#params | run-until-target/timeout)
**When** an estimate is requested through the `qmb` CLI door (click 8.4.2)
**Then** the system reports projected total trials × measured typical per-trial runtime ÷ the governor concurrency cap without spawning any trial. (OPT-17; OPT-24; AD-13; FR-046)

**Given** no per-trial runtime baseline has yet been measured
**When** an estimate is requested
**Then** the estimate is returned as `not-yet-measured` rather than an invented figure. (AD-13 measure-then-budget; NFR-04)

**Given** a running Study
**When** the operator terminates it
**Then** it transitions to a clean `stopped` state, the orchestrator appends exactly one ledger line per already-spawned run (completed or `aborted`, never zero, never two), and partial results are preserved and resumable. (B-4; AR-51; OPT-18)

### Story 21.6: Anti-overfit parameter-sensitivity report

As an agent,
I want the completed Study to emit a parameter-sensitivity analysis over all trials with isolated-spike winners flagged,
So that I can tell a robust parameter region from a fragile lucky point before trusting a winner.

**Acceptance Criteria:**

**Given** a completed Study
**When** its result artifact is emitted
**Then** it includes per-parameter objective slices and an objective distribution summary (mean, std, min, max, median) computed over all completed `role = trial` ledger lines. (B-8; OPT-22)

**Given** the trials cluster in the space
**When** the sensitivity report is built
**Then** good regions are clustered and each cluster is described as data — chart series cite exact `Bar`/`Price` inputs and no image is ever the canonical payload. (B-10)

**Given** a winner sitting in an unstable neighborhood (an isolated spike)
**When** the report is produced
**Then** that winner is flagged as isolated-spike, distinct from a winner inside a stable cluster. (B-8; OPT-22)

**Given** thresholds are deferred (SC-07)
**When** the report renders
**Then** it describes parameter structure and neighborhood stability only and emits no SR*/search-quality pass/fail verdict and no invented threshold. (SC-07; GAP-0049)

**Given** the sensitivity statistics are analytic floats
**When** they are computed
**Then** P&L and equity inputs stay exact-integer, floats exist only inside the statistic under a fixed rounding contract, and any float-valued measure takes label-derived identity — never a raw float in identity. (B-14 return-space carve-out; AD-41; AD-7)

## Epic 22: QMB robustness ladder

The ratified B-14 validation ladder ships as pure QMB library functions with
configurable inputs and versioned statistical-procedure contracts: Monte Carlo
trade-shuffle, Monte Carlo candle-perturbation, the pre-build rule-significance
gate, and walk-forward. The ladder builds on the replay backtest (Epic 14) and
optimization Studies (Epic 21) and adds only the robustness rungs. Interfaces
ship now; every threshold value and pass battery (the MC-1000 / PBO / CSCV
candidates) stays deferred to the GAP-0048/0049 sittings (SC-07) and appears
only as a UI-editable configurable with no ratified value. Every procedure runs
on optimistic-tainted evidence under the GAP-0048 seam (SC-06): the outputs
claim robustness or infra-stress and never edge (L20), and none can gate live
money. (FR-040; QMB spine B-14; spec-mc-significance intake.) Wave 7, weight M;
after Epic 21.

### Story 22.1: Robustness module foundation — procedure contract, return-space float carve-out, and the shared distribution-summary primitive

As the factory developer,
I want the `qmb/robustness/` module scaffolded with a versioned statistical-procedure contract, the bounded return-space float carve-out, and one pure distribution-summary primitive,
So that every ladder procedure (22.2-22.5) is built on one identity-bearing, exact-integer-safe, reproducible foundation instead of re-deriving statistics per procedure.

**Acceptance Criteria:**

**Given** the QMB package skeleton from Epic 13 (the `qmb/robustness/` directory of the Structural Seed)
**When** the robustness module is scaffolded
**Then** each ladder procedure is exposed as a pure library function under B-4 — it consumes a resolved run-config plus data reads, RETURNS its result, and writes no log and no ledger line
**And** the module declares a versioned statistical-procedure contract stamping its own AD-5 integer format version (format version 1) so each procedure's exact mechanics are pinned and every old ledger entry stays readable forever
**And** no module-global mutable state exists anywhere in the module (all impurity stays in the Epic 15 orchestrator).

**Given** the B-14 return-space float carve-out
**When** a procedure computes a return-space statistic (mean log-return, Sharpe, Calmar, and kin)
**Then** all P&L and equity paths remain exact scaled integers (AD-7), floats exist only inside the statistic under a fixed declared rounding contract, and any re-entry to the money path passes a named AD-22 conversion with a declared rounding mode
**And** a binary float appearing on the money path is treated as a taint (FR-001), catchable by the tier-1 money-path float scanner (NFR-02).

**Given** a float-valued measure produced by the carve-out
**When** it is labeled for identity
**Then** it takes label-derived identity per AD-41, never the bit-identity of the float, so identical inputs yield identical measure identity (NFR-03).

**Given** the shared distribution-summary primitive
**When** it is called with a simulated distribution, an observed value, and a declared direction (higher-is-better or lower-is-better)
**Then** it returns percentile ranks, confidence bands, and an empirical one-tailed p-value (the fraction of the distribution at or beyond the observed value in the declared direction) as pure data
**And** it emits NO pass/fail verdict, because α levels, pass batteries, and battery composition (the MC-1000 / PBO / CSCV candidates) are deferred to GAP-0048/0049 (SC-07).

**Given** every robustness threshold and every iteration / scenario / block-length / minimum-observation input
**When** it is declared
**Then** it is a UI-editable configurable (NFR-07) carrying no ratified platform value, the module ships no invented default, and an unset required input returns a typed `invalid input` refusal rather than a silently-applied number (AR-13).

**Given** these procedures produce robustness or infra-stress evidence only
**When** any result is labeled
**Then** its claim class is robustness/infra-stress and never edge (L20/B-7), and no procedure output can gate live money or spend split budget while GAP-0048 is open (SC-06).

### Story 22.2: Monte Carlo trade-shuffle (sequence-risk mode)

As an agent,
I want to re-order a replay run's realised trades N times and re-derive the equity path and metrics,
So that I can quantify how much the ordering of trades drove the outcome (sequence risk) rather than the entry logic itself.

**Acceptance Criteria:**

**Given** a completed `world=replay` backtest whose trade record is the CT-29 stream of the run's replay binding (B-10)
**When** trade-shuffle Monte Carlo runs
**Then** it re-orders the realised trades and re-accumulates the equity path with money math kept exact-integer (AD-7)
**And** it is procedure-ephemeral — it never mints or persists a synthetic market series — so the run stays `world=replay` and the procedure identity plus seed enter the result label (B-7).

**Given** per-scenario reproducibility (AR-59; NFR-03)
**When** scenarios are generated
**Then** each scenario's seed is derived deterministically as base_seed + scenario_index, and the result records the RNG family, base seed, seed-derivation rule, scenario count, and data-window UTC-ns bounds
**And** re-running the same run id under its resolved run-config reproduces the CT-32 fingerprint bit-for-bit or returns a typed refusal (B-10).

**Given** the distribution-summary primitive from Story 22.1
**When** metrics are summarised across scenarios
**Then** per selected metric it writes percentile ranks, confidence bands, and the direction-aware empirical percentile rank of the original result (lower-is-better for drawdown) into the CT-32 result artifact as chart series data, never images (B-10; FR-043)
**And** it emits no pass/fail verdict (thresholds deferred, SC-07).

**Given** the scenario count is a UI-editable configurable with no ratified value (SC-07)
**When** a run is configured
**Then** the operator-supplied count is taken from the resolved run-config, and the MC-1000 baseline remains a deferred battery candidate that is NOT baked as a default.

**Given** B-5 concurrency
**When** scenarios fan out
**Then** fan-out is performed by the orchestrator's process-per-run governor bounded by min(cpu budget, memory budget) with enqueue-when-full — no Ray, no daemon, no required Docker (AR-50)
**And** each governed run is cancellable via its cancel token, and the orchestrator appends exactly one ledger line per run with `role = replicate` and never a bar verdict (B-4; AR-51).

### Story 22.3: Monte Carlo candle-perturbation (alternate-history mode)

As an agent,
I want to re-run the backtest across resampled market paths generated by a real-seeded moving-block bootstrap of OHLC deltas,
So that I can see how the strategy holds up under alternate but short-horizon-consistent market histories.

**Acceptance Criteria:**

**Given** a `world=replay` run's real historical candles
**When** candle-perturbation generates a scenario
**Then** it moving-block-bootstraps exact-integer OHLC delta tuples (block length is a UI-editable configurable with no ratified value, SC-07), cumulative-sums them onto the seed price with exact-integer money math (AD-7), and always rebuilds a valid, strictly-positive OHLC series with high/low bounds enforced
**And** scenario 0 is the true history.

**Given** B-7's persistence rule (the GAP-0048 gate for this story)
**When** the perturbation is procedure-ephemeral (the synthetic series is never persisted into a data room)
**Then** the run stays `world=replay`, the procedure identity plus seed enter the label, and the claim class is robustness-only.

**Given** a config that instead requests persisting the synthetic series,
**When** that config is compiled,
**Then** the run is `world=simulated`, is a typed `policy rejection` for governed evidence, and cannot ledger into the bar's store until GAP-0048 closes (SC-06)
**And** a config binding a replay clock to synthetic-tainted persisted data is a typed `invalid input` (B-2/B-7 wins).

**Given** per-scenario reproducibility
**When** scenarios are generated
**Then** each scenario uses an independent RNG seeded deterministically (base_seed + scenario_index), and the label records the RNG family, seed derivation, block length, scenario count, resampling scheme, and data-window UTC-ns bounds
**And** re-running the run id under its resolved config reproduces the CT-32 fingerprint or refuses (AR-59; B-10).

**Given** each scenario re-runs the full event-slice loop (B-2)
**When** scenarios execute
**Then** they run as governed process-per-run under the B-5 governor (min(cpu, memory), enqueue-when-full, cancel token)
**And** the orchestrator appends exactly one ledger line per scenario run with `role = replicate` plus the objective measure, never a bar verdict (B-4).

**Given** the distribution-summary primitive
**When** metrics are summarised
**Then** percentiles, confidence bands, and direction-aware empirical percentile ranks are written into the CT-32 artifact as data, and no pass/fail verdict is emitted
**And** the claim class is robustness (alternate-history), never edge (L20), and the result cannot gate live money.

### Story 22.4: Pre-build rule-significance gate (signal-only edge test)

As an agent,
I want to test whether a bare entry rule has an edge before committing to a full strategy build,
So that I can reject noise-indistinguishable rules before burning compute — an advisory, evidence-based pre-filter, never an auto-merge.

**Acceptance Criteria:**

**Given** a bot's entry rule and a data window
**When** the significance gate runs
**Then** it performs a signal-only pass over the B-2 event-slice loop with orders disabled — the same loop, same pinned sub-phase order, trading locked as in warm-up — so the strategy stays permanently flat and the raw entry signal is isolated from exit and position-management logic
**And** any attempt to mint an entry, an exit, or a command during the pass is a typed `policy rejection` (B-2).

**Given** look-ahead safety (B-2; SC-06)
**When** each signal is scored
**Then** the signal at bar t is aligned to the NEXT bar's return on log returns (the first return not knowable at signal time), so no forming-bar or future information enters the statistic
**And** close prices are exact Price integers that cross into the bounded return-space float carve-out only via the named AD-22 conversion from Story 22.1.

**Given** the zero-edge null hypothesis
**When** the null is built
**Then** returns are detrended by their in-sample mean AND the rule-return series is re-centred to zero before resampling (H0: E[return]=0)
**And** the reported statistic is the empirical one-tailed p-value = the fraction of null resamples whose mean is at or above the observed mean.

**Given** the resampling scheme and gate parameters are configurable (SC-07)
**When** a run is configured
**Then** the scheme is a UI-editable configurable — `iid`, `block`, or `stationary` — with a configurable block length, and the iteration count and minimum-observation floor are UI-editable configurables carrying no ratified value
**And** the module ships no invented default for any of them.

**Given** insufficient data
**When** the observation count falls below the configured minimum-observation floor
**Then** the procedure returns a typed refusal rather than a fabricated p-value, and where a floor is unset it emits a low-confidence warning label instead of a hard number
**And** the result records seed provenance (base seed plus per-batch derivation), scheme and parameters, iteration count, and data-window UTC-ns bounds, and re-running reproduces the null distribution bit-for-bit (AR-59; NFR-03).

**Given** the gate is advisory (SC-06; B-14)
**When** the gate produces a verdict
**Then** the result world is `replay` or `simulated`, never `live`, and the claim class is robustness, never edge (L20)
**And** the verdict is advisory to the operator — a build pipeline may consult it but it never auto-merges and never gates live money, and the pass/fail α thresholds stay deferred to GAP-0049.

### Story 22.5: Walk-forward as a sequence of split-manifest runs

As an agent,
I want walk-forward to run as an ordered sequence of first-class split-manifest runs with a read-time aggregation view,
So that I can inspect rolling in-sample / out-of-sample behaviour without any single merged run and without inventing deferred window or OOS-count thresholds.

**Acceptance Criteria:**

**Given** B-8's split discipline
**When** a walk-forward is defined
**Then** it is a sequence of split manifests (each a knowledge-time / embargo-purge / calendar-in-band manifest), and each window is a first-class run under B-3/B-4 with its own resolved run-config and its own ledger line
**And** "train/test" is a display alias for two such manifests, never a substitute, and every read goes through qmf-data split-governed at every boundary (AD-21; FR-012).

**Given** B-4 ledger roles under the GAP-0048 seam
**When** a train window runs
**Then** its ledger line carries `role = trial` (or `replicate`) plus the objective measure and never a bar verdict
**And** because no verdict-bearing backtest ships while GAP-0048 is open (SC-06), an out-of-sample window's bar outcome is a read-time fold that returns `not-yet-ruled` until GAP-0048/0049 close.

**Given** SC-11 batch admission
**When** a walk-forward batch is admitted
**Then** it resolves exactly one registry as-of at admission through the single B-15 registry-read port, frozen for every window and stamped into the batch label
**And** after admission fragments resolve by explicit fingerprint, never by name@latest.

**Given** window counts, spans, and OOS counts are deferred pass-battery values (SC-07)
**When** a walk-forward is configured
**Then** the window count, the in-sample and out-of-sample spans, and the step are UI-editable configurables carrying no ratified value
**And** the module ships no invented default and no baked WF/OOS battery.

**Given** B-12
**When** window results are aggregated
**Then** the walk-forward view is a read-time aggregation over the ledger's window runs (never a merged run), written into the CT-32 artifact as data
**And** the aggregated in-sample / out-of-sample metric distributions are the declared feeders for the deferred governance battery (the PBO / CSCV candidates), which itself ships no ratified thresholds (SC-07).

**Given** reproducibility (AR-59; B-10)
**When** a walk-forward run id is re-run under its resolved config
**Then** it reproduces the CT-32 fingerprint or returns a typed refusal
**And** each window's label carries its split-manifest fingerprints, registry_as_of, world, and evidence class.

## Epic 23: QMB synthetic data

Synthetic data generation ships as config-selected generator adapters that are
claim-class labeled (infra-stress / robustness / logic-smoke), carry a
store-level synthetic-origin taint that derives `world=simulated` on any run
reading them, and never validate edge (L20). The library is never swapped — only
config variables change — and no config may bind a replay clock to
synthetic-tainted data. Builds on Epic 14's run loop and CT-32 emission, Epic 15's
orchestrator/governor, and the qmf-data contracts (CT-10/CT-15) from Epics 3/6.

### Story 23.1: `qmb data generate` and config-selected generator adapters

As an agent,
I want to generate synthetic forex CFD series by selecting a generator process
and its variables through one resolved generator config that the
`qmb data generate` command consumes,
So that I can produce infrastructure-stress and smoke-test data by changing
config variables — never by editing or swapping the library.

**Acceptance Criteria:**

**Given** the `qmb data` command group is a thin front over the ratified QMF data
contracts (CT-10/CT-15) on the click==8.4.2 CLI door (B-11, B-1)
**When** I invoke `qmb data generate` with a resolved generator config
**Then** the config selects exactly one process from the v1 menu {`block-bootstrap`
(default), `gaussian-resample`, `gaussian-noise`, `gbm`}
**And** the resolved generator config is materialized as a first-class,
schema-validated, fingerprinted artifact recorded alongside the run it produces
(R1; B-3 config discipline; AR-14 fp1).

**Given** the process menu distinguishes history-seeded from from-scratch processes
**When** I select a history-seeded process (`block-bootstrap` / `gaussian-resample`
/ `gaussian-noise`)
**Then** the config MUST cite a `source-dataset id` resolved from a qmf-data room
(CT-10)
**And** when I select from-scratch `gbm`, no source dataset is required and the
config records `source-dataset id = none` (R2).

**Given** the QMF money and time contracts (AR-15)
**When** any process emits prices/quotes
**Then** every price/quote is exact scaled-integer money quantized to the
instrument's tick size and every timestamp is int64 UTC-ns on a market-hours-aware
grid (Sunday-open / Friday-close weekend gap, session boundaries) (R6)
**And** any float statistic internal to a process re-enters the integer money path
only through a named AD-7/AD-22 conversion with a declared rounding mode.

**Given** OHLC integrity must survive every transform
**When** a process or perturbation completes a bar
**Then** `low <= open,close <= high` and positivity hold on integers, else a typed
`invalid input` refusal is returned (R6, R8) — never a silently corrected bar.

**Given** the v1 menu is exactly four processes and generators are config-selected
adapters (the library/tunnel is never swapped, B-1 extensibility law)
**When** a config names a process×instrument combination the generator cannot
honor (e.g. corporate-action events requested on a forex instrument) or names a
process outside the four-process menu (regime-switching and heavy-tailed processes
are open questions, deferred — spec §5 Q1/Q2)
**Then** a typed refusal is returned (`unsupported capability` for an unknown
process; category-appropriate refusal for a mismatch), never a silent drop (R2, R8).

**Traceability:** FR-041; B-1, B-2, B-3, B-11; CT-10/CT-15; AR-14, AR-15; spec R1,
R2, R6, R8.

### Story 23.2: Claim-class labeling (infra-stress / robustness / logic-smoke) and the L20 edge refusal

As an agent,
I want every synthetic run's result to carry exactly one machine-readable claim
class that bounds what it may assert, with edge/validation claims refused
outright,
So that synthetic evidence can stress infrastructure and probe robustness without
ever being mistaken for validated edge (L20).

**Acceptance Criteria:**

**Given** the CT-32 result label emitted by the run loop (AR-59; Epic 14)
**When** a synthetic run completes
**Then** its label carries exactly one claim class ∈ {`infra-stress`,
`robustness`, `logic-smoke`} as a field distinct from `world` (B-7; R3).

**Given** claim class is bounded by the generator's provenance
**When** the run's generator is from-scratch (`gbm`)
**Then** only `infra-stress` and `logic-smoke` are permittable and a `robustness`
claim is refused with a typed `policy rejection`
**And** when the generator is history-seeded (`block-bootstrap` /
`gaussian-resample` / `gaussian-noise`), `robustness` is additionally permittable
(R3).

**Given** L20 is encoded as a contract, not a docstring
**When** any caller requests an edge / alpha / validation claim on synthetic data,
under any process
**Then** a typed refusal is returned — no synthetic run of any class may assert
edge (FR-041; L20; R3, R8).

**Given** thresholds and pass batteries are deferred to the GAP-0048/0049 sittings
while interfaces ship now (SC-07; B-14)
**When** a `robustness`-class run reports
**Then** the percentile-band / p-value fields exist as interface only, with NO
numeric pass battery or threshold invented; any pass/fail threshold, when present,
is a config-declared configurable recorded before the run (never chosen after)
(R7; NFR-07/L38).

**Given** the GAP-0048 gate on verdict-bearing claims (SC-06)
**When** a run reads store-persisted synthetic data and is therefore
`world=simulated` (Story 23.3)
**Then** no verdict-bearing claim ships and the result refuses for governed-evidence
use — `infra-stress` and `logic-smoke` only until GAP-0048 closes (B-7; SC-06).

**Given** Gaussian-family processes destroy real market structure
**When** a `gaussian-resample` or `gaussian-noise` result is labeled `robustness`
**Then** the label MUST carry a machine-readable caveat that the process destroys
autocorrelation / volatility clustering / fat tails ("hides Black Swan risk")
(spec §1, R2) — the limitation is stated, never implied.

**Traceability:** FR-041; B-7, B-14; L20; CT-32; AR-59; SC-06, SC-07,
GAP-0048/0049; spec R3, R7, R8.

### Story 23.3: Synthetic taint, store provenance & world derivation

As the operator,
I want every synthetic artifact tagged `origin = synthetic` at the store level
with full provenance and made non-promotable, so that any run reading synthetic
data derives `world=simulated` and no config can bind a replay clock to
synthetic-tainted data,
So that fabricated data can never masquerade as real evidence on the money path.

**Acceptance Criteria:**

**Given** store-level tagging closes the exact gap where a from-scratch generator
writes data files indistinguishable from real data (spec §2A.8, R4)
**When** a synthetic series, tick series, or derived aggregate is persisted
**Then** it carries `origin = synthetic` at the store level (not merely in a
filename), recording process id, seed, `source-dataset id` (or `none`),
generator-config fp1, generation timestamp (UTC-ns), and the QMX generator
version (R4; AR-14).

**Given** world is derived from input-data provenance, never caller-declared (B-7)
**When** any run reads store-persisted synthetic data
**Then** `world=simulated` is derived from provenance and the run is a
`policy rejection` for governed evidence until GAP-0048 — infra-stress and
logic-smoke only (B-7; SC-06).

**Given** a replay clock or replay/live adapters imply real provenance
**When** a resolved run-config binds a replay clock (or replay/live adapters) to
synthetic-tainted data
**Then** config compilation returns a typed `invalid input` refusal — B-7 wins over
B-2 (B-2; B-3).

**Given** synthetic artifacts are non-promotable (R4)
**When** a caller attempts to load synthetic data into a `world=replay` or
`world=live` context, or to promote a synthetic artifact toward live money
**Then** a typed refusal is returned (R4, R8) — the synthetic backdoor (LEAN's
indistinguishable-data gap) is closed by construction.

**Given** procedure-ephemeral perturbation does not persist a synthetic series
into a data room (B-7; B-14)
**When** `block-bootstrap` (or a B-14 trade-shuffle) perturbs a `world=replay` run
without persisting a synthetic series
**Then** `world` stays `replay`, the procedure identity + seed enter the CT-32
label, and the claim class is robustness-only — never edge, never admission
evidence (B-7).

**Given** non-live worlds never write the live namespace and `world=simulated`
writes refuse until GAP-0048 (AR-33)
**When** a generation persists into a room
**Then** it writes only into a synthetic-tainted store partition, never the live
or governed-evidence namespace; a `world=simulated` write into a governed/live
namespace refuses (AR-33; B-7).

**Traceability:** FR-041; B-2, B-3, B-7, B-14; L20; AR-14, AR-33; SC-06;
GAP-0048; spec R4, R8.

### Story 23.4: Deterministic multi-scenario generation with a pinned RNG

As an agent,
I want the generator to use a QMX-owned version-pinned RNG and derive each
scenario's substream deterministically from a master seed, with scenario 0 the
untouched original when a real source exists,
So that any scenario is bit-reproducible in isolation and the
perturbed-vs-original anchor is unambiguous, independent of a runtime's stdlib
Random.

**Acceptance Criteria:**

**Given** determinism is a platform property (NFR-03; R5)
**When** a config sets a seed
**Then** the full artifact is bit-reproducible from
`{process, seed, source-dataset id, generator-config fp1}`, and re-generation
reproduces the artifact fingerprint or returns a typed refusal (R5; B-10
reproduce-or-refuse).

**Given** the Lean portability caveat that `System.Random` is not stable across
runtimes (spec §2A.3)
**When** the generator draws randomness
**Then** it uses a QMX-owned, version-pinned RNG whose algorithm and version are
recorded in the artifact provenance (R4/R5) — never a runtime stdlib `Random`.

**Given** a multi-scenario request
**When** N scenarios are generated
**Then** each scenario's substream is derived deterministically from the master
seed (e.g. master seed + scenario index) so scenario k reproduces in isolation,
and each scenario is tagged by its index so original-vs-synthetic is unambiguous
regardless of completion order (R5; spec §2B).

**Given** a history-seeded process has a real anchor
**When** N scenarios are generated from a history-seeded process
**Then** scenario 0 is the untouched original real path and scenarios >0 are
perturbed (Jesse anchor pattern) (R5; spec §2B).

**Given** from-scratch `gbm` has no real source to anchor
**When** scenarios are generated from `gbm`
**Then** there is no scenario-0 original anchor and NO robustness percentile band
or p-value is computed — the run emits only `infra-stress` / `logic-smoke`
verdicts (spec §5 Q7; R3).

**Given** scenario fan-out runs process-per-run under the orchestrator's governor
(B-5; AR-50; Epic 15)
**When** N scenarios execute concurrently
**Then** the governor spawns them process-per-run bounded by min(cpu, memory)
budgets with enqueue-when-full (never silent oversubscription), and scenario
failures are counted and reported as typed refusals, never silently dropped
beyond an explicit filtered-count line (B-5; R7, R8).

**Traceability:** FR-041; B-5, B-7, B-10; NFR-03; AR-50; spec R3, R5, R7, R8.
