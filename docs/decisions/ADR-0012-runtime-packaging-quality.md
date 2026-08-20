---
id: ADR-0012
title: Runtime matrix, workspace packaging, and quality gates
type: adr
status: provisional
component: COMP-QMF-CORE
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK]
decisions: [DEC-0099, DEC-0100, DEC-0101, DEC-0102, DEC-0103, DEC-0104]
sources: [DEC-0099, DEC-0100, DEC-0101, DEC-0102, DEC-0103, DEC-0104, DEC-0120, DEC-0122, EXT-2001, EXT-2002, EXT-2003, EXT-2004, EXT-2005, EXT-2006, EXT-2028, "_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md", "archive/qmf-3.txt"]
generated: 2026-08-20
verified: 2026-08-20
stale_after: 1y
---

# ADR-0012: Runtime matrix, workspace packaging, and quality gates

Date: 2026-08-20. Status: provisional — AD-1..AD-6 are operator-ratified in the foundation architecture sitting (2026-08-19/20); this document stays provisional until the knowledge base is re-ratified.

## Context

QMF is written by a software factory running many disposable agent sandboxes in parallel, against an operator workstation on Windows 11 and an always-on Linux VPS. Six build-substrate questions had to be settled before the first package existed, because every sandbox would otherwise answer them differently and results would stop being comparable: which interpreter and operating systems are tested, what shape the repository and its distributions take, which tools govern factory-written source, what "tests pass" means and at which moment, how versions advance for code and for stored artifacts separately, and which dependencies and licences are admissible. The foundation architecture sitting ratified all six as AD-1 through AD-6.

## Options considered

1. **Per-package repositories** — one repository per distribution. Rejected because cross-repo coordination is a tax a solo operator and a single-integration-branch factory cannot pay; the split stays available later, since package import paths do not change when a package moves (DEC-0100).
2. **One monolithic distribution** — a single installable `qmf`. Rejected because a sandbox would install the whole framework to use one library, which breaks the disposable-sandbox model and the sub-second core import constraint (DEC-0100, DEC-0111).
3. **Per-agent tool choice** — each factory agent picks its own formatter, type checker, and test runner. Rejected as guaranteed tool drift across factory-written code (DEC-0101).
4. **Gates bound to Git-host mechanics** — quality tiers expressed as pull-request checks. Rejected because no remote exists yet and a gate must mean the same thing on a local worktree; tiers bind to factory events instead (DEC-0102).
5. **One version ladder** — package SemVer also versioning stored artifacts. Rejected because it makes stored history unreadable as soon as packages evolve (DEC-0103).
6. **Single uv workspace, seven packages, one toolchain, three event-bound tiers, two ladders, tiered dependency policy** — selected.

## Decision

**Runtime.** CPython 3.14 (`registry:python_version`) is pinned across all packages, CI, and factory sandboxes. Tier-1 tested targets are Windows 11 x86-64 and Ubuntu LTS x86-64, CI-gated once a remote exists; until then the factory runs the same gates locally. QMF source stays pure-Python and OS-neutral, so other platforms work by construction and remain untested in V1. (DEC-0099)

**Packaging.** One repository is a uv workspace holding seven installable packages — `qmf-core`, `qmf-registry`, `qmf-data`, `qmf-indicators`, `qmf-structure`, `qmf-venue`, `qmf-risk` — importing as the `qmf.*` PEP 420 implicit namespace. No distribution may ever contain `qmf/__init__.py`. Every package uses `src/` layout; every dependency, sibling packages included, is declared explicitly in that package's `pyproject.toml`; the build backend is `uv_build`; one `uv.lock` is committed; the seven roster packages release in SemVer lockstep. A package may declare a test-only dependency on a contract's owning package purely to run that contract's conformance tests — that is not a ratified runtime edge. Market-hours calendar extensions are separate versioned packages outside the roster, in the same workspace, on their own SemVer ladder, where a tzdata pin change is at minimum a minor bump. Shared nouns (Venue, Account, Instrument, WriterId) are defined in `qmf-core` and their records owned by `qmf-registry`; edge modules never define shared nouns. (DEC-0100)

**Toolchain.** ruff formats and lints, pyright runs strict workspace-wide, pytest runs the tests. Coverage is measured per package on every change with the floor at `registry:coverage_floor_percent`, and the modules implementing CT-01 and CT-02 primitives require 100% branch coverage. Public value types are frozen dataclasses; seams are `typing.Protocol`s. The canonical commands are `poe fmt`, `poe lint`, `poe types`, `poe test`, `poe check`, identical on every machine. Every package ships executable tests and reference usage demonstrating its public contract as tier-1 artifacts (L27). This strictness governs QMF's own source; consumers are never forced into it (DEC-0011). (DEC-0101)

**Gates.** Tier 1 is `poe check` on every factory work unit — worktree or temporary branch. Tier 2 is `poe check-integration` — tier 1 plus integration tests plus contract tests, each package in an isolated environment so an undeclared import fails rather than resolving through the shared workspace venv — on landing into the integration branch. Tier 3 is `poe check-release` — tier 2 plus building all packages plus clean-install smoke on both tier-1 operating systems — on ship. A **contract test** is an executable conformance suite for a `CT-*` contract's public shape, owned by the contract's owning package and run by producer and all consumer packages at tier 2. Commands stay host-neutral and bind to a CI host only when a remote exists. Factory-internal review layers stack on top and are never replaced. (DEC-0102)

**Version ladders.** Code packages use SemVer in lockstep across the roster, 0.x until the V1 blueprint ships, with anything deprecated still working under a warning for one release before removal. Every serialized contract carries its own integer format version (`registry:contract_version_syntax`) stamped into every artifact; a format version's meaning never changes after the fact, and an incompatible change mints the next version plus a migration note. QMF never loses the ability to read old stored evidence. Re-deriving a value under a newer market-hours calendar or tzdata version produces a new artifact with its own fingerprint and a lineage edge to the old one — never a rewrite, never a silent equality. (DEC-0103)

**Dependencies and licences.** Permissive licences (MIT, BSD, Apache, PSF) are freely allowed; LGPL only unmodified and separately installed; GPL and AGPL are prohibited; strategy-family libraries and platform-imposing dependencies that bring their own event loop, runtime, or data model are prohibited. `qmf-core` takes zero outside dependencies, stdlib only. Every dependency gets one line in the workspace-root `DEPENDENCIES.md` register: name, licence, why. Borrowing mental models by study or reverse-engineering is always permitted; adopting code is the governed exception. (DEC-0104)

## Consequences

A sandbox installs one package and gets a working library, which is what makes wide parallel experimentation affordable. The zero-dependency rule forecloses placing the tzdata pin inside `qmf-core`, which is why market-hours calendar rule sets ship as extensions outside the roster (ADR-0013). Adding any inter-library dependency edge is a spine amendment rather than a package-level decision (DEC-0120, ADR-0016). Lockstep versioning means a change in one roster package advances all seven, which trades release granularity for the guarantee that any seven installed together are a tested set. The Ubuntu tier-1 target is declared and not yet proven: tier-3 clean-install smoke on Linux is unexercised until a remote or local Linux runner exists (DEC-0099). Contract format versions are permanent — correcting a mistake costs a new version plus a migration note, forever (DEC-0103). Because everything downstream of QMF is built with these libraries (DEC-0122), the packaging and toolchain choices bind consumers — trading node, backtesting library, agentic system, UI — that do not exist yet.

## Blast radius

- **Component specs (all seven roster packages):** COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK each carry the runtime pin, `src/` layout, namespace rule, toolchain, tier obligations, and lockstep ladder.
- **Data seams:** COMP-QMF-DATA-STORE, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-BACKUP inherit the same obligations as parts of `qmf-data`; their store and adapter dependencies each take a `DEPENDENCIES.md` register line.
- **External boundaries:** COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, COMP-OBJECT-STORAGE are unchanged in shape; any client library an adapter uses is subject to the licence tiers.
- **Contracts:** CT-01 through CT-26 each stamp a contract format version (DEC-0103) and each gains a conformance suite owned by its owning package and run by consumers at tier 2 (DEC-0102).
- **Registry:** `registry:python_version`, `registry:coverage_floor_percent`, `registry:contract_version_syntax`, `registry:core_import_time_budget`.
- **Architecture docs:** the stack table and the dependency register in `docs/architecture/`.

## Architecture preflight

Verdict: **reuse**. No new component, no authority shrink. The ruling changes how existing components are built, packaged, and gated, not what any of them owns: COMP-QMF-CORE (zero-dependency hub, definitions only), COMP-QMF-REGISTRY, COMP-QMF-DATA with its seams COMP-QMF-DATA-STORE, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-BACKUP, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK. Market-hours calendar extensions sit outside this roster and are declared in ADR-0013.
