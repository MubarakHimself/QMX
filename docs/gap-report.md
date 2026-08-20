---
id: DOC-GAP-REPORT
title: QMF V1 Gap Report
type: gap-report
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK]
decisions: [DEC-0003, DEC-0004, DEC-0011, DEC-0013, DEC-0014, DEC-0015, DEC-0017, DEC-0019, DEC-0020, DEC-0022, DEC-0023, DEC-0032, DEC-0036, DEC-0040, DEC-0041, DEC-0043, DEC-0047, DEC-0049, DEC-0051, DEC-0056, DEC-0057, DEC-0062, DEC-0063, DEC-0064, DEC-0067, DEC-0069, DEC-0071, DEC-0073, DEC-0075, DEC-0077, DEC-0079, DEC-0081, DEC-0082, DEC-0083, DEC-0084, DEC-0085, DEC-0086, DEC-0087, DEC-0088, DEC-0089, DEC-0090, DEC-0091, DEC-0093, DEC-0094, DEC-0095, DEC-0099, DEC-0100, DEC-0101, DEC-0102, DEC-0103, DEC-0104, DEC-0105, DEC-0106, DEC-0107, DEC-0108, DEC-0109, DEC-0110, DEC-0111, DEC-0114, DEC-0115, DEC-0116, DEC-0117, DEC-0118, DEC-0119, DEC-0120, DEC-0121, DEC-0122, DEC-0124, DEC-0125, DEC-0126, DEC-0127, DEC-0128, DEC-0129, DEC-0130, DEC-0131, DEC-0132, DEC-0133, DEC-0134, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0139, DEC-0140, DEC-0141, DEC-0142]
sources: [_docwork/gaps.yaml, _docwork/ledger.yaml, _docwork/ratification-packet.md, docs/constitution.md, docs/architecture/dependencies.yaml, docs/components/, docs/contracts/, docs/decisions/, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/reviews/five-hats-sweep.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# QMF V1 Gap Report

This provisional report preserves the QMF V1 decision surface in a docs-local form. The catalog contains **49 gaps**, now in four states after the 2026-08-19/20 foundation architecture sitting ratified the spine AD-1 through AD-21, the 2026-08-20 indicators/structure sitting extended it to AD-25, and the 2026-08-20 venue sitting extended it to AD-28:

- **36 answered** — `GAP-0001`–`GAP-0015`, `GAP-0018`–`GAP-0034`, and `GAP-0035`–`GAP-0038`, ratified by the operator across the foundation sitting (ledger `DEC-0099`–`DEC-0119`), the indicators/structure sitting (ledger `DEC-0126`–`DEC-0131`), and the venue sitting (ledger `DEC-0135`–`DEC-0139`).
- **2 deferred to the backtesting sitting** — `GAP-0016` (look-ahead/causality registration gate) and `GAP-0017` (attempt counter), per `DEC-0121`.
- **8 open** — `GAP-0039`–`GAP-0046`, each owned by the risk sitting and all eight blocking; `qmf-risk` remains a stub with these open gaps, and nothing in them blocks the ratified QMF documentation. `GAP-0033`, the catalog's sole nonblocking gap, closed with the indicators/structure sitting.
- **3 deferred consumer gaps** — `GAP-0047`–`GAP-0049`, waiting on the QML, backtesting, and research-threshold sittings.

A recommendation is a discussion prompt, not an answer. It grants neither implementation authority nor live-money authority; a blocking gap remains blocking until an operator ruling is recorded in the ledger and its affected contracts are ratified. An **answered** gap records an operator ruling but does not lift the corpus-wide provisional gate: the documents absorbing these rulings stay `provisional` until the knowledge base is re-ratified. (DEC-0003, DEC-0004, DEC-0041)

## How to navigate the decision surface

| Area | Gaps | State | ADRs | Components | Contracts |
|---|---|---|---|---|---|
| Foundation, runtime, contracts, quality | GAP-0001–GAP-0013 | **answered** | [ADR-0012](decisions/ADR-0012-runtime-packaging-quality.md), [ADR-0013](decisions/ADR-0013-exact-values-and-identity.md), [ADR-0014](decisions/ADR-0014-performance-observability-concurrency.md) (+ [ADR-0001](decisions/ADR-0001-authority-and-document-first.md)–[ADR-0003](decisions/ADR-0003-definitions-only-core.md)) | [qmf-core](components/qmf-core.md), [qmf-registry](components/qmf-registry.md), [qmf-data](components/qmf-data.md) | [CT-01](contracts/ct-01-money-quantity.yaml)–[CT-05](contracts/ct-05-version-fingerprint.yaml) |
| Registry and promotion | GAP-0014–GAP-0019 | **answered** (0016/0017 deferred) | [ADR-0015](decisions/ADR-0015-registry-records-and-promotion.md) (+ [ADR-0004](decisions/ADR-0004-registry-identity-lineage.md)) | [qmf-registry](components/qmf-registry.md) | [CT-06](contracts/ct-06-registration.yaml)–[CT-09](contracts/ct-09-registry-persistence.yaml) |
| Data, persistence, acquisition, observability | GAP-0020–GAP-0030 | **answered** | [ADR-0016](decisions/ADR-0016-data-rooms-splits-journal.md) (+ [ADR-0005](decisions/ADR-0005-governed-data-evidence.md)) | [qmf-data](components/qmf-data.md), [ingest](components/qmf-data-ingest.md), [store](components/qmf-data-store.md), [backup](components/qmf-data-backup.md), [qmf-calendar-forex](components/qmf-calendar-forex.md) | [CT-10](contracts/ct-10-source-observation.yaml)–[CT-15](contracts/ct-15-external-source-adapter.yaml), [CT-26](contracts/ct-26-store-backup-input.yaml) |
| Indicators and structure | GAP-0031–GAP-0034 | **answered** | [ADR-0006](decisions/ADR-0006-indicators-and-structure.md) | [qmf-indicators](components/qmf-indicators.md), [qmf-structure](components/qmf-structure.md) | [CT-16](contracts/ct-16-indicator.yaml), [CT-17](contracts/ct-17-causal-structure.yaml) |
| Venue and live boundary | GAP-0035–GAP-0038 | **answered** (venue sitting 2026-08-20) | [ADR-0007](decisions/ADR-0007-venue-neutral-integration.md) | [Venue](components/qmf-venue.md), [cTrader](components/ctrader.md) | [CT-18](contracts/ct-18-venue-capabilities.yaml)–[CT-21](contracts/ct-21-venue-secret-session.yaml) |
| Book, BMS, exits, risk | GAP-0039–GAP-0046 | **open** (risk sitting) | [ADR-0008](decisions/ADR-0008-book-and-risk-boundary.md), [ADR-0009](decisions/ADR-0009-book-level-paper-mode.md), [ADR-0010](decisions/ADR-0010-risk-vocabulary-clean-start.md) | [Risk](components/qmf-risk.md) | [CT-22](contracts/ct-22-book-charter.yaml)–[CT-25](contracts/ct-25-risk-journal.yaml) |
| Deferred consumers | GAP-0047–GAP-0049 | **deferred** | [ADR-0011](decisions/ADR-0011-deferred-consumer-products.md) | [qmf-core](components/qmf-core.md), [qmf-data](components/qmf-data.md), [Risk](components/qmf-risk.md) | No active V1 consumer contract |

## Answered by the architecture sittings — 36

The operator ratified these 36 gaps across the 2026-08-19 and 2026-08-20 sittings. Each answer is the ratified spine rule in one line; the full text is in the cited ledger entry and its ADR. These answers are operator rulings, not implementation authority — the absorbing documents remain `provisional`.

### Foundation, runtime, contracts, and quality — 13

| Gap | Ratified answer | Ledger |
|---|---|---|
| **GAP-0001** | CPython 3.14 pinned across all packages, CI, and factory sandboxes; tier-1 targets Windows 11 x86-64 and Ubuntu LTS x86-64; QMF stays pure-Python and OS-neutral, other platforms untested in V1. | DEC-0099 (AD-1) |
| **GAP-0002** | One uv workspace; seven packages importing as the `qmf.*` PEP 420 namespace (no `qmf/__init__.py`), `src/` layout, `uv_build`, one committed `uv.lock`, lockstep roster versioning; market-hours calendar extensions live outside the roster on their own SemVer ladder. | DEC-0100 (AD-2) |
| **GAP-0003** | ruff (format + lint), pyright strict workspace-wide, pytest; 80% coverage floor with 100% branch coverage on CT-01/CT-02 primitive modules; canonical commands `poe fmt \| lint \| types \| test \| check`. | DEC-0101 (AD-3) |
| **GAP-0004** | Three tiers bound to factory events: tier 1 `poe check` on every work unit, tier 2 `poe check-integration` (adds integration + contract tests in isolated per-package environments) on landing into the integration branch, tier 3 `poe check-release` on ship; host-neutral until a remote exists. | DEC-0102 (AD-4) |
| **GAP-0005** | Two ladders: SemVer lockstep code packages (one-release deprecation window) and per-contract integer format versions whose meaning never mutates — incompatible change mints the next version plus a migration note; history stays append-only and readable forever. | DEC-0103 (AD-5) |
| **GAP-0006** | Permissive licences freely allowed, LGPL only unmodified and separately installed, GPL/AGPL and strategy-family/platform-imposing dependencies prohibited; `qmf-core` takes zero outside dependencies; every dependency registered in `DEPENDENCIES.md`. | DEC-0104 (AD-6) |
| **GAP-0007** | Money/Price/Quantity are scaled integers at a declared scale; Price is instrument-tagged; mixed-scale arithmetic auto-promotes losslessly or refuses; binary float is banned on the money path (a taint rule), crossed only at named conversion boundaries with an explicit rounding mode; foreign money stored verbatim as evidence. | DEC-0105 (AD-7) |
| **GAP-0008** | int64 UTC nanoseconds (POSIX no-leap-second, 1677–2262, checked); CivilDate/TradingDate distinct with calendar identity in-band; wall vs monotonic clocks type-separated; Clock protocol injected at the composition root; forex market-hours calendar ships first with a `registry:forex_rollover` rollover, tzdata pinned in extensions. | DEC-0106 (AD-8) |
| **GAP-0009** | Instrument identity is (venue, venue's own symbol), symbol opaque and never parsed; VenueId operator-minted, opaque, stable (a white-label broker is its own venue); Venue and Account are first-class nouns defined in qmf-core with records owned by qmf-registry. | DEC-0107 (AD-9) |
| **GAP-0010** | The pinned `fp1` recipe (UTF-8 JSON, keys sorted at every depth, NFC strings, integer-only identity numerics, null prohibited, order-significant arrays; SHA-256; `fp1:sha256:<hex>`), one implementation in qmf-core; idempotent re-writes accepted, true collisions refused and alarmed. | DEC-0108 (AD-10) |
| **GAP-0011** | Seven typed-refusal categories (invalid input, unsupported capability, unavailable dependency, stale evidence, policy rejection, transient venue failure, storage failure) with machine-readable context and retryability; refusals returned as result unions; one construction pattern (unchecked constructor + `try_create`). | DEC-0109 (AD-11) |
| **GAP-0012** | Five-part result label, all identity: producer contract format version, input fingerprints, evidence time range, computation identity, and world (live incl. paper/demo via account role; replay; simulated reserved-unusable until the backtesting sitting); non-live worlds never write the live evidence namespace. The indicators/structure increment later expanded the label with producer contract identity and evidence class (DEC-0131). | DEC-0110 (AD-12) |
| **GAP-0013** | Measure-then-budget: no invented numbers; every component ships a benchmark harness measuring speed and peak memory at framework-native load ladders; first measurements become fingerprinted (OS, CPU-class) baselines gating tier-2 merges; `qmf-core` imports in well under one second. Numeric budgets await first baselines. | DEC-0111 (AD-13) |

### Registry and promotion — 4

| Gap | Ratified answer | Ledger |
|---|---|---|
| **GAP-0014** | Per-kind record schemas, each its own versioned contract, sharing a tiny header (kind, contract format version, at-birth parent refs, writer, sequence); stable id derived from the record's `fp1`, never minted; kinds addable never redefined; Bot and Book reserved; no universal recipe card. | DEC-0114 (AD-16) |
| **GAP-0015** | Lineage accruing after birth lives exclusively in append-only typed edge records (supersedes, promoted-from, occurrence-of, corroborates, disagrees-with) referencing fingerprints; pinned JSONL, LF-terminated, append-with-fsync, size-rotated; rebuildable local indexes; no database server. | DEC-0114 (AD-16) |
| **GAP-0018** | A Bot contains one-or-more confluences, generalized recursively — no bot-vocabulary layer hardcodes cardinality one; Bot identity is its content and the Bot–Book–account binding is a separate dated record, so re-binding never mints a new Bot. Full Bot schema remains its own session. | DEC-0115 (AD-17) |
| **GAP-0019** | Skeleton: the registry reserves a promotion-occurrence card kind — human-only signer, immutable record, mandatory plain-words summary declared an identity field; V1 signing is the operator's recorded approval attesting the record's `fp1`; the card is canonical; the gate itself is platform territory. | DEC-0116 (AD-18) |

### Data, persistence, acquisition, and observability — 11

| Gap | Ratified answer | Ledger |
|---|---|---|
| **GAP-0020** | Seven room-roles (ingest door, immutable raw archive, processed, journal, split-governed research door, backup, registry room) instantiated per world; a cross-world read is a policy-rejection refusal; per-room schemas detailed per contract at documentation time. | DEC-0117 (AD-19) |
| **GAP-0021** | Parquet (columnar time-series), DuckDB (local analytics), SQLite (transactional metadata), JSONL (append streams), each behind a QMF-owned contract with stdlib-typed boundaries; no database server; only raw-archive and journal formats are evidence-bearing. | DEC-0117 (AD-19) |
| **GAP-0022** | Migrations run preflight checks → backup first → dry-run → migrate → verify with a documented restore path, never in-place mutation of the only copy; contract format versions stamp every artifact. | DEC-0118 (AD-20) |
| **GAP-0023** | Every external fact carries event-time, known-at, source, and revision; source is a core provenance noun orthogonal to VenueId; corrections are appended, never overwritten; foreign timestamps and money stored verbatim with conversions derived under lineage. | DEC-0117 (AD-19); DEC-0106 |
| **GAP-0024** | Splits are fingerprinted, time-ordered, non-overlapping manifests pinning exactly one calendar identity + version in-band; boundaries are stored TradingDates or instants, never civil dates; the 12-month seal is a no-peek lock enforced now as a policy-rejection refusal at every read boundary, with one logged final look. | DEC-0119 (AD-21) |
| **GAP-0025** | Seven journal event types (decision, order, fill, risk transition, promotion, data quality, control action) in N append-only per-writer streams with gapless per-(writer, boot-epoch) sequences; `correlation_id` excluded from `fp1` identity; causal linkage via typed edges; retention set only after measured volume. | DEC-0119 (AD-21); DEC-0118 |
| **GAP-0026** | Raw originals and lineage kept forever; time-series partitioned by source, instrument, and time window; journal trimming only after measured volume; "rebuildable" licenses deletion only of artifacts no result label cites. | DEC-0118 (AD-20); DEC-0117 |
| **GAP-0027** | Backup design: nightly, encrypted, versioned, off-machine object-storage bucket, automated sample-restore tests plus periodic full-restore rehearsal; QMF provides the backup/restore/verify primitives (CT-14, CT-26), applications own schedule and execution; numeric RPO/RTO await the node/ops sitting. | DEC-0118 (AD-20) |
| **GAP-0028** | qmf-data defines source contracts, normalization, validation, and idempotent intake keyed on (source, source-native id, revision); applications own scheduling, retries, supervision, and UI. | DEC-0119 (AD-21) |
| **GAP-0029** | The news-calendar recorder keeps provider-native identity and revisions through idempotent intake; scheduling stays outside QMF; the legal archiving posture remains an open operator item, recorded not resolved. | DEC-0119 (AD-21) |
| **GAP-0030** | Tick sources are separately identified (Dukascopy history vs the broker feed); bid and ask preserved with source timestamps; disagreements stay visible via corroborates/disagrees-with edges, never merged. Venue depth is a Level-2 resting-liquidity book with no Level-3 tape, recorded verbatim (DEC-0135, DEC-0138). | DEC-0119 (AD-21) |

### Indicators and market structure — 4

Ratified in the 2026-08-20 indicators/structure sitting, then amended by its increment reviewer gate in the same pass (`DEC-0130`, `DEC-0131`); two standing rules bind all documentation prose — school-neutral vocabulary (`DEC-0132`, L32) and the plain-Python escape hatch with its graduation path (`DEC-0133`, L33).

| Gap | Ratified answer | Ledger |
|---|---|---|
| **GAP-0031** | CT-16 is one contract with two conformant modes (batch + streaming) bound by a tier-2 equality law; the series vocabulary (`Bar`, `Tick`/`Quote`, `BarSpec`, exact rationals) lives in qmf-core and `BarSpec` replaces bare "timeframe"; identity is the entire declared configuration and that fingerprint is the only dedup key; outputs are full-length, index-aligned, presence-mapped, and carry per-sample knowable-at; streaming instances are shared per configuration, not per consumer. | DEC-0126 (AD-22); DEC-0130 |
| **GAP-0032** | Canonical arithmetic is TA-Lib 0.7.1 + 0.7.1, pinned as lockfile-resolved artifact hashes plus an identity-bearing reference-configuration record asserted at import; wrap-not-reimplement where the reference implements a formula, the QMX implementation canonical where it does not; upgrades gated with per-configured-indicator format mints; tolerances in integer ULPs. | DEC-0127 (AD-23); DEC-0130 |
| **GAP-0033** | Light iff four declared-and-benchmark-proven bounds hold (per-update cost, state size, window-or-anchor-reset, synchronous availability); classification per configuration, never per name; the verdict is machine-scoped and display-only; heavy by default until the live-path rung has a baseline; the same bounds bind structure families. Was the catalog's sole nonblocking gap. | DEC-0128 (AD-24); DEC-0130 |
| **GAP-0034** | A family is a type of chart object; objects mint once at observation with observed-at (known-at semantics), anchor span, and a precise confirmation rule; lifecycle and interaction records are append-only edges with current state a read-time fold; evidence class is identity-bearing and reads refuse unconfirmed rows; the seed four families are candidates only — operator-authored families are first-class peers via the extension shape. | DEC-0129 (AD-25); DEC-0131 |

### Venue, secrets, and safe operation — 4

Ratified in the 2026-08-20 venue sitting (ledger `DEC-0135`–`DEC-0142`). The cTrader research recorded under `DEC-0123` was re-verified and ratified as the venue-facts sheet `ctrader-venue-facts.md` with **corrected evidence grades**: the 2013-forum-grade claims — the 17:00-New-York daily boundary and BID-derived trendbars — were demoted and replaced by measure-per-broker adapter obligations, so `DEC-0135` supersedes `DEC-0123` (DEC-0135). Trading-node runtime material stays out of these docs; the order path, protection funnel, and flatten authority are node/risk territory recorded in `tracker/trading-node-notes.md`, which these docs reference as a pointer only (DEC-0142).

| Gap | Ratified answer | Ledger | Contract |
|---|---|---|---|
| **GAP-0035** | Venue credentials follow the AD-26 secret lifecycle: QMF components handle typed `SecretRef` references and never values; reference ids are opaque minted ids; binding identity is (VenueId, AccountId, role, world) with the secret reference occurrence-only; the adapter's connection manager is the single component permitted to hold values in memory, through an injected `SecretStore` port; exactly one live refresher per credential rotates store-before-discard; compromise recovery is a documented, tested drill anchored on cTID re-authorization, and testing uses demo credentials only. | DEC-0136 (AD-26) | [CT-21](contracts/ct-21-venue-secret-session.yaml) |
| **GAP-0036** | AD-27 venue commands and the uncertainty law: the command stream is (VenueId, account); the vocabulary is exactly four typed kinds (`place_order`, `cancel_order`, `close_position`, `close_all`) with typed close scopes and the compound-command meet law; command identity is `fp1`-derived with an injective-or-bound venue mapping; every submission resolves to accepted-by-venue, rejected-by-venue, denied-locally, or UNKNOWN — a timeout is never a rejection, UNKNOWN is minted as an explicit observation and blocks its command stream until an explicit `resolve_unknown` call; recording precedes interpretation and order state is a read-time fold; reconciliation gates the command pipe only, command retry is prohibited, and flatten authority is left to the risk/node sittings. | DEC-0137 (AD-27) | [CT-19](contracts/ct-19-venue-command.yaml), [CT-20](contracts/ct-20-venue-event.yaml) |
| **GAP-0037** | Two halves closed. Broker identity is deployment configuration, never architecture (DEC-0139) — opaque VenueId/AccountId identity suffices and IC Markets is the operator's intent, not a framework commitment. The venue facts are ratified (DEC-0135, superseding DEC-0123 with corrected evidence grades): per-field ms-UTC timestamps with named epoch exceptions, no server clock, BID/ASK-selectable historical ticks, and the daily-bar boundary and trendbar price basis measured per broker at first connection as verify-or-refuse obligations, never hardcoded. | DEC-0135 + DEC-0139 | [CT-18](contracts/ct-18-venue-capabilities.yaml) |
| **GAP-0038** | AD-28 adapter contract: one neutral port of four contracts (CT-18 capability, CT-19 command, CT-20 event + reconciliation, CT-21 secret/session) defined by qmf-venue on qmf-core nouns and implemented per venue, wired by the composition root through injected qmf-core sink protocols with no new dependency edge; the capability surface splits into a static capability declaration and a per-account measured venue-observation profile; market data is homed at CT-10/CT-15 with no fifth contract; the first-connection verification suite is verify-or-refuse throughout, and a CCXT-class crypto venue slots in later through the same port without leaking venue concepts into qmf-core. | DEC-0138 (AD-28) | [CT-18](contracts/ct-18-venue-capabilities.yaml) |

## Deferred to the backtesting sitting — 2

The operator deferred both mechanisms to the backtesting sitting, knowingly accepting the consequence (`DEC-0121`). These gaps are **not** closed; they remain owed.

| Gap | Question | Deferral consequence |
|---|---|---|
| **GAP-0016** | What exact causality and look-ahead registration test must an artifact pass, and what evidence proves the pass? | Artifacts registered before the backtesting sitting carry **no causality evidence**, and that evidence is not retroactively reconstructible. The bitemporal ingredients (event-time vs knowledge-time) stay ratified via AD-8 / CT-10, and registry occurrence records still log every run, so the raw material accrues without a policy. (DEC-0121) |
| **GAP-0017** | What does the attempt counter count, at which scope, when does it reset, and how does it constrain registration or research budget? | No attempt-count policy exists before the backtesting sitting; registry occurrence records still log every run, so the tally's raw material accrues without policy. (DEC-0121) |

## Open gaps — 8

Eight blocking gaps, all owned by the risk sitting and not answered by the spine; `qmf-risk` remains a stub with these open gaps, and nothing in them blocks the ratified QMF documentation. The venue sitting closed `GAP-0035`–`GAP-0038` on 2026-08-20 (`DEC-0135`–`DEC-0139`); the catalog's sole nonblocking gap (`GAP-0033`) closed with the indicators/structure sitting.

### Book, BMS, exits, and risk arithmetic — 8 (risk sitting)

| Gap | Question | Needed by | Blocking | Recommendation — non-authorizing |
|---|---|---|---:|---|
| **GAP-0039** | What are the exact Book and BMS schemas, cardinalities, lifecycle states, version-compatibility rules, and ownership boundaries? | [COMP-QMF-RISK](components/qmf-risk.md)<br>[COMP-QMF-REGISTRY](components/qmf-registry.md) | `true` | Make Book the versioned risk container, make BMS a separately versioned policy owned by one Book, and leave multiple-BMS cardinality unimplemented until the operator rules. |
| **GAP-0040** | Do Bots own ordinary exit organs while Books own forced exits, or does the Book own every exit policy and expose only an exit-signal contract to Bots? | [COMP-QMF-RISK](components/qmf-risk.md)<br>[COMP-QMF-REGISTRY](components/qmf-registry.md) | `true` | Choose Book ownership for exit policy with Bot exit signals mediated by the Book contract, because repeated direct corrections place Exit in Book territory. (Open conflict — see DEC-0067.) |
| **GAP-0041** | How does Book-level paper mode map Bots to demo accounts, transition between live and paper, avoid duplicate orders, and preserve comparable evidence? | [COMP-QMF-RISK](components/qmf-risk.md)<br>[COMP-QMF-VENUE](components/qmf-venue.md)<br>[COMP-QMF-DATA](components/qmf-data.md) | `true` | Model paper as an explicit Book state transition with one active execution destination, persist transition cause and account identity, and prohibit simultaneous live and paper twins. |
| **GAP-0042** | What exact before-and-after windows, event severity, currency-to-instrument mapping, open-position behavior, and override rules define the pair-scoped news control? | [COMP-QMF-RISK](components/qmf-risk.md)<br>[COMP-QMF-DATA](components/qmf-data.md) | `true` | Keep the control pair-scoped and data-driven, but do not ratify the tentative ±15-minute window until representative event and spread evidence is reviewed. |
| **GAP-0043** | What inputs, normalization, conditioning, thresholds, sample cadence, hysteresis, and stale-data behavior define the Spread Quality Sensor? | [COMP-QMF-RISK](components/qmf-risk.md)<br>[COMP-QMF-DATA](components/qmf-data.md)<br>[COMP-QMF-VENUE](components/qmf-venue.md) | `true` | Specify SQS as a versioned pure function over observed bid-ask evidence and session context, with explicit stale and unavailable outcomes; design the formula fresh rather than adopting the candidate. |
| **GAP-0044** | What dimensionally valid formulas replace FORM-0006, and how are R, roster seat, risk allocation, and any surviving legacy capital concept represented? | [COMP-QMF-RISK](components/qmf-risk.md)<br>[COMP-QMF-CORE](components/qmf-core.md) | `true` | Start from R as pre-trade risk, define every variable with units, keep the three capital concepts distinct, and accept no replacement formula until dimensional tests pass. |
| **GAP-0045** | What exactly counts as a stop-out, what benchmark state replaces the overloaded B and BENCHED terms, and what fresh alpha-decay evidence is required? | [COMP-QMF-RISK](components/qmf-risk.md)<br>[COMP-QMF-REGISTRY](components/qmf-registry.md)<br>[COMP-QMF-DATA](components/qmf-data.md) | `true` | Define stop-out as a typed risk event first, choose unambiguous names for benchmark and roster state, and design alpha-decay mathematics only after those primitives and units are stable. |
| **GAP-0046** | What deterministic same-tick priority applies among protective stops, Book force-flat, kill-switch actions, fast invalidation, and discretionary exits, and how does no-overnight policy interact with hold limits? | [COMP-QMF-RISK](components/qmf-risk.md)<br>[COMP-QMF-VENUE](components/qmf-venue.md) | `true` | Prioritize venue-confirmed protective execution and emergency risk controls over discretionary actions, record every suppressed action, and define overnight policy per Book rather than globally. |

## Deferred consumer gaps — 3

Deferred consumer gaps are deliberately postponed and nonblocking for the current QMF V1 roster. Their recommendations remain non-authorizing and do not pull the deferred consumer into scope.

| Gap | Question | Needed by | Recommendation — non-authorizing |
|---|---|---|---|
| **GAP-0047** | When QML is revisited, what Bot authoring, confluence composition, Book binding, lineage, and promotion contracts must it consume from QMF V1? | [COMP-QMF-CORE](components/qmf-core.md)<br>[COMP-QMF-REGISTRY](components/qmf-registry.md)<br>[COMP-QMF-RISK](components/qmf-risk.md) | Defer QML implementation until the Bot schema and one-Bot-to-one-Book binding are ratified; then make it a consumer of QMF contracts rather than a new foundation layer. |
| **GAP-0048** | What fidelity levels, fill models, statistics, Bot-by-Book matrix, isolated sandbox, and parity contracts define the future backtesting library? | [COMP-QMF-CORE](components/qmf-core.md)<br>[COMP-QMF-DATA](components/qmf-data.md)<br>[COMP-QMF-INDICATORS](components/qmf-indicators.md)<br>[COMP-QMF-STRUCTURE](components/qmf-structure.md)<br>[COMP-QMF-RISK](components/qmf-risk.md) | Keep bar-close, intrabar, and tick fidelity as candidate labels only, and ratify backtesting in its own session before any central backtesting service is built. This sitting also owns simulated-time typing (unlocks `world = simulated` per DEC-0110) and the deferred GAP-0016/GAP-0017 (DEC-0121). |
| **GAP-0049** | What preregistered search-quality threshold, including any SR* definition, units, evaluation population, and attempt-budget effect, belongs to future research and backtesting? | [COMP-QMF-REGISTRY](components/qmf-registry.md)<br>[COMP-QMF-DATA](components/qmf-data.md)<br>[COMP-QMF-RISK](components/qmf-risk.md) | Defer the threshold until the attempt counter, split policy, result-label tuple, and evaluation statistics are defined; do not treat the proposed SR* label as a contract. |

## Five-hats sweep — input register, not resolved here

The foundation architecture sitting produced a **five-hats sweep** (44 findings) framed against the researcher, developer/QML, analyst, PM, and trader hats: `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/reviews/five-hats-sweep.md`. It is an **input register** feeding the remaining sittings — indicators/structure, venue, risk, backtesting, and ops — and is **referenced by this documentation, not resolved by it** (DEC-0125). The already-answered gaps consumed the sweep items that were in the foundation's scope; the rest stay owed to their owning sittings above. Resolving a sweep item here would pre-empt a sitting the operator has not held.

## Conflicts requiring an operator ruling — 1

The Bot-to-confluence conflict (`DEC-0040`) is **resolved**: the operator's multiplicity ruling (`DEC-0115`, AD-17) supersedes it — a Bot contains one-or-more confluences, generalized recursively. One conflict remains live pending the risk sitting.

| Decision | Status | Competing readings | Recommendation — non-authorizing | Related gap | Navigation |
|---|---|---|---|---|---|
| **DEC-0067 — Exit ownership** | `conflict` | All Exit semantics, including dynamic SL/TP and fast invalidation, belong to the Book and risk module.<br>**versus**<br>Bots own ordinary exit organs, while Books own forced exits and risk overrides. | Make the Book/risk contract authoritative for exit policy and let Bots emit exit signals only through that contract, because the repeated direct corrections place exits in Book territory. | GAP-0040 | [ADR-0008-book-and-risk-boundary.md](decisions/ADR-0008-book-and-risk-boundary.md)<br>[COMP-QMF-RISK](components/qmf-risk.md) |

### Evidence caveat

The direct operator wording behind the dead parallel-Bot-twin rejection (`DEC-0069`) and Book-level paper-mode ruling (`DEC-0070`) is absent from the export. The recorded standing survives through the assistant's immediate recap and requires explicit operator confirmation before a final contract is claimed.

## Out-of-scope topics — 9 ledger decisions

No `gaps.yaml` entry has `status: out-of-scope`. Out-of-scope standing is carried by the nine ledger decisions below; the deferred consumer gaps preserve questions that will matter only if those future areas are reopened.

| Decision | Status | Out-of-scope topic | Navigation |
|---|---|---|---|
| **DEC-0057 — Custom indicator discovery** | `out-of-scope` | Genetic or other custom-indicator discovery belongs to a future research lab, not the V1 indicator library. | [COMP-QMF-INDICATORS](components/qmf-indicators.md) |
| **DEC-0064 — Broker parity checklist** | `out-of-scope` | Broker-versus-simulation parity is deferred to the future backtesting library, not COMP-QMF-VENUE V1 connectivity. | [ADR-0007](decisions/ADR-0007-venue-neutral-integration.md)<br>[COMP-QMF-VENUE](components/qmf-venue.md) |
| **DEC-0081 — Prop-firm Books** | `out-of-scope` | Prop-firm evaluation and funded-account Books are deferred to the agentic era; the account-scoped day-boundary calendar holds the seam only (AD-8). | [COMP-QMF-RISK](components/qmf-risk.md) |
| **DEC-0083 — Backtesting in QMF V1** | `out-of-scope` | Backtesting, fill simulation, and validation statistics are deferred to a separate future design session. | [ADR-0011](decisions/ADR-0011-deferred-consumer-products.md) |
| **DEC-0087 — Future modular backtesting library** | `out-of-scope` | Any future backtesting capability is a modular on-demand library or sandbox that can vary by Book, not a permanent central service. | [ADR-0011](decisions/ADR-0011-deferred-consumer-products.md) |
| **DEC-0088 — Trading simulator product** | `out-of-scope` | A visual simulator for Bot-by-Book and theoretical-condition exploration is a later product UI, not a QMF V1 deliverable. | [ADR-0011](decisions/ADR-0011-deferred-consumer-products.md) |
| **DEC-0089 — MIS as a QMF library** | `out-of-scope` | MIS is a later trading-node component built with qmf-data and qmf-indicators, not a V1 library. | [ADR-0011](decisions/ADR-0011-deferred-consumer-products.md) |
| **DEC-0090 — QML Bot library in V1** | `out-of-scope` | The QML Bot library is deferred until its Bot-to-Book binding contract is designed. | [ADR-0011](decisions/ADR-0011-deferred-consumer-products.md) |
| **DEC-0091 — Agentic runtime organs** | `out-of-scope` | DeepSeek Context, disposers, event buses, autonomous organs, and the full agentic harness are deferred outside QMF V1. | [ADR-0011](decisions/ADR-0011-deferred-consumer-products.md) |

## Open ledger decisions — 4

These ledger entries remain undecided or study-delivered. A delivered study is evidence, not an adopted schema or implementation instruction. Four earlier open entries closed at the foundation sitting: **DEC-0032** (six freeze choices) is superseded by **DEC-0124**, itself now superseded by **DEC-0134** after the indicators/structure sitting — four of the six are ratified (time encoding DEC-0106, instrument identity DEC-0107, result-label tuple DEC-0110, canonical arithmetic DEC-0127) and two stay open under GAP-0048 and GAP-0049; **DEC-0036** (registry identity study) is superseded by **DEC-0114**; **DEC-0043** and **DEC-0047** (data study and stack) are superseded by **DEC-0117**. A fifth open entry, **DEC-0123** (cTrader time research), closed at the 2026-08-20 venue sitting — superseded by **DEC-0135**, recorded in the Superseded baseline chains below (DEC-0135).

| Decision | Status | Unresolved standing | Navigation |
|---|---|---|---|
| **DEC-0049 — Automatic detector action** | `open` | Automated data or quality detectors may notify, but whether they can mutate trading state is not adopted from the data study. | [ADR-0005](decisions/ADR-0005-governed-data-evidence.md)<br>[COMP-QMF-DATA](components/qmf-data.md) |
| **DEC-0075 — SQS calculation** | `open` | The Spread Quality Sensor formula, inputs, thresholds, conditioning, and sampling cadence remain unratified. | [ADR-0010](decisions/ADR-0010-risk-vocabulary-clean-start.md)<br>[COMP-QMF-RISK](components/qmf-risk.md) |
| **DEC-0094 — Recovered benchmark baseline** | `open` | The recovered two-stopouts-per-day baseline, stop-out definition, overloaded B symbol, and BENCHED namespace are not yet valid V1 contracts. | [ADR-0010](decisions/ADR-0010-risk-vocabulary-clean-start.md)<br>[COMP-QMF-RISK](components/qmf-risk.md) |
| **DEC-0095 — Multiple BMS per Book** | `open` | Whether one Book may own multiple BMS instances or policies remains undecided. | [ADR-0008](decisions/ADR-0008-book-and-risk-boundary.md)<br>[COMP-QMF-RISK](components/qmf-risk.md) |

## Dead decisions — 18

Dead entries are prohibitions against resurrection. Their rejected statements are retained only to make the boundary auditable. Never revive a dead decision without a later operator ruling that explicitly replaces it.

| Decision | Rejected statement | Reason | Navigation |
|---|---|---|---|
| **DEC-0014** | QMF may use third-party libraries that define or transplant strategy families. | No third-party strategy-family libraries; QMX builds its own. | [COMP-QMF-CORE](components/qmf-core.md) |
| **DEC-0015** | QMF will support futures and options. | Permanent: no futures and no options; stocks may come later. | [COMP-QMF-CORE](components/qmf-core.md) |
| **DEC-0020** | The whole QMF V1 agreement is called the minimal core. | The phrase "minimal core" was retired for the whole agreement. | [COMP-QMF-CORE](components/qmf-core.md) |
| **DEC-0023** | The qmf-core foundation is described as the QMX kernel. | The word "kernel" is retired. | [ADR-0003](decisions/ADR-0003-definitions-only-core.md)<br>[COMP-QMF-CORE](components/qmf-core.md) |
| **DEC-0034** | Every registered QMF object must implement one universal all-fields recipe-card schema. | Rejected as too abstract; only identity and lineage were accepted, now delivered as per-kind records (DEC-0114). | [ADR-0004](decisions/ADR-0004-registry-identity-lineage.md)<br>[COMP-QMF-REGISTRY](components/qmf-registry.md) |
| **DEC-0037** | qmf-registry V1 requires Neo4j or another graph database for lineage. | The operator declined a graph database for V1; lineage is JSONL edge records (DEC-0114). | [ADR-0004](decisions/ADR-0004-registry-identity-lineage.md)<br>[COMP-QMF-REGISTRY](components/qmf-registry.md) |
| **DEC-0062** | The venue conformance work is named the Broker Exam. | The term "exam" collides with another concept and must not be used for broker conformance. | [COMP-QMF-VENUE](components/qmf-venue.md) |
| **DEC-0063** | Broker connection, parity, and broader broker-conformance work ship as one immediate bundle. | The bundle was denied; connection is separate and parity belongs to future backtesting. | [COMP-QMF-VENUE](components/qmf-venue.md) |
| **DEC-0069** | A live Bot also runs a parallel paper twin, or one Bot attaches to several Books at once. | No parallel Bot twin; a Bot connects to exactly one Book. Direct wording unavailable; survives through recap. | [ADR-0009](decisions/ADR-0009-book-level-paper-mode.md)<br>[COMP-QMF-RISK](components/qmf-risk.md) |
| **DEC-0071** | A special paper simulator must run through news blackouts solely to preserve market observations. | Ordinary recorders never stop, so a special simulation path adds no required evidence. | [ADR-0009](decisions/ADR-0009-book-level-paper-mode.md)<br>[COMP-QMF-RISK](components/qmf-risk.md) |
| **DEC-0073** | SQS expands to Snapshot Quality Sensor. | SQS means Spread Quality Sensor; the snapshot-quality aggregate is semantic drift. | [COMP-QMF-RISK](components/qmf-risk.md) |
| **DEC-0077** | The recovered FORM-0006 expression may be implemented unchanged. | FORM-0006 is dimensionally broken and must never be implemented as-is. | [ADR-0010](decisions/ADR-0010-risk-vocabulary-clean-start.md)<br>[COMP-QMF-RISK](components/qmf-risk.md) |
| **DEC-0079** | Legacy auctions, DPR-driven slot tables, and capital-slot machinery are carried into COMP-QMF-RISK V1. | The legacy slot machinery is donor-only. | [ADR-0010](decisions/ADR-0010-risk-vocabulary-clean-start.md)<br>[COMP-QMF-RISK](components/qmf-risk.md) |
| **DEC-0082** | QMF models prop-firm workflows with generic Program and Campaign state machines. | Rejected as far off; a prop firm is modeled as a new Book. | [COMP-QMF-RISK](components/qmf-risk.md) |
| **DEC-0084** | All agents and Books share one centralized always-on backtesting service. | Centralization could not supply enough compute for concurrent work. | [ADR-0011](decisions/ADR-0011-deferred-consumer-products.md) |
| **DEC-0085** | QMF adopts Nautilus Trader's contracts as its foundation. | The operator does not want the Nautilus contract; QMX-owned semantics stand. | [ADR-0011](decisions/ADR-0011-deferred-consumer-products.md) |
| **DEC-0086** | QMF performs a three-day spike to decide whether to adopt an external trading framework. | The three-day adoption spike was cancelled; locally owned contracts committed. | [ADR-0011](decisions/ADR-0011-deferred-consumer-products.md) |
| **DEC-0093** | The legacy DPR and PRS mechanisms return as current risk controls. | DPR and PRS are legacy-only and must not be revived. | [ADR-0010](decisions/ADR-0010-risk-vocabulary-clean-start.md)<br>[COMP-QMF-RISK](components/qmf-risk.md) |

## Superseded baseline chains

Earlier baselines survive only through recorded successors. The foundation architecture sitting added five supersessions to the six pre-sitting chains; the indicators/structure sitting added two more, and the 2026-08-20 venue sitting added one (marked **new**). `DEC-0123` — the delivered cTrader time research — was re-verified at the venue sitting and superseded by `DEC-0135`, which ratified the research as the venue-facts sheet `ctrader-venue-facts.md` with corrected evidence grades: the 2013-forum-grade claims (the 17:00-New-York daily boundary and BID-derived trendbars) were demoted and replaced by measure-per-broker adapter obligations (DEC-0135).

| Earlier decision | Live successor | Navigation |
|---|---|---|
| DEC-0010 — Constrained-only authoring surface | DEC-0011 — Open Python toolbox | [ADR-0002](decisions/ADR-0002-toolbox-and-v1-roster.md) |
| DEC-0012 — Blanket ban on third-party code | DEC-0013 — Build-own boundary | [ADR-0002](decisions/ADR-0002-toolbox-and-v1-roster.md) |
| DEC-0016 — QML as the framework name | DEC-0017 — QMF umbrella and QML Bot domain | [ADR-0002](decisions/ADR-0002-toolbox-and-v1-roster.md) |
| DEC-0018 — Minimal-core project scope | DEC-0019 — QMF V1 Blueprint | [ADR-0002](decisions/ADR-0002-toolbox-and-v1-roster.md) |
| DEC-0021 — Broad runtime kernel | DEC-0022 — Definitions-only qmf-core | [ADR-0003](decisions/ADR-0003-definitions-only-core.md) |
| DEC-0050 — Calendar/live-feed capture excluded | DEC-0051 — Acquisition plumbing + first-install bulk history | [ADR-0005](decisions/ADR-0005-governed-data-evidence.md) |
| DEC-0032 — Six qmf-core freeze choices | DEC-0124 — Freeze-choice status (three ratified, three open) | [ADR-0013](decisions/ADR-0013-exact-values-and-identity.md) |
| DEC-0036 — Registry identity study model | DEC-0114 — Registry records and lineage | [ADR-0015](decisions/ADR-0015-registry-records-and-promotion.md) |
| DEC-0040 — Bot-to-confluence cardinality | DEC-0115 — Multiplicity at every layer | [ADR-0015](decisions/ADR-0015-registry-records-and-promotion.md) |
| DEC-0043 — Six-layer qmf-data study | DEC-0117 — Data rooms, stores, bitemporal law | [ADR-0016](decisions/ADR-0016-data-rooms-splits-journal.md) |
| DEC-0047 — Proposed local data stack | DEC-0117 — Data rooms, stores, bitemporal law | [ADR-0016](decisions/ADR-0016-data-rooms-splits-journal.md) |
| DEC-0056 — Light and heavy indicator split | **new** DEC-0128 — Light vs heavy: budget-declared, benchmark-policed (AD-24) | [ADR-0006](decisions/ADR-0006-indicators-and-structure.md) |
| DEC-0124 — Freeze-choice status (three ratified) | **new** DEC-0134 — Freeze-choice status (four ratified, two open) | [ADR-0006](decisions/ADR-0006-indicators-and-structure.md) |
| DEC-0123 — cTrader time research (forum-grade evidence) | **new** DEC-0135 — cTrader venue facts ratified with corrected evidence grades | [ADR-0007](decisions/ADR-0007-venue-neutral-integration.md)<br>[COMP-QMF-VENUE](components/qmf-venue.md) |

## Ratification handoff

To close an open gap, the operator must state the ruling, the ledger must record its standing and provenance, affected contracts and component specs must be updated, and validation must pass. Editing a recommendation into imperative prose is not ratification. The 36 answered gaps have crossed the first step — an operator ruling exists in the ledger — but the corpus stays `provisional` until the whole knowledge base is re-ratified; no answered gap authorizes implementation or live money on its own. This report is the docs-local navigation surface, not a signature record.
