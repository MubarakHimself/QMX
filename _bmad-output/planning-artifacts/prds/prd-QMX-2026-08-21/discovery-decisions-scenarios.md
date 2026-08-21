# PRD Discovery — Decisions, Scenarios, NFR Signals (QMX)

Extracted 2026-08-21 from `docs/decisions/` (ADR-0001..0018), `docs/scenarios/`
(SCN-0001..0012), and `docs/lenses/` (bugs, data, observability, ops,
performance, security, testing). This is a PRD-input extract: decision
constraints that bound requirements (with rejected alternatives worth an
addendum), golden scenarios as user-journey / acceptance signals, and
non-functional signals per lens.

**Standing framing that bounds the whole PRD.** QMF V1 is a *reusable Python
toolbox* (five libraries + two modules), never an application runtime; consumer
products (backtesting, node, MIS, Simulator UI, agentic runtime) are deferred.
QMB (backtesting/experimentation library + CLI) and QML (bot-authoring library)
are application-layer products built ON QMF, realized at the planning level but
not yet built. Everything is "ratified design"; **implementation authority
arrives only through the factory pipeline, never from these docs.** Every
numeric business value is a configurable UI-editable variable with *no spine
constant* — recorded numbers are evidence, not ratified values.

---

## Section 1 — ADR constraints (what each decision bounds for the PRD)

### ADR-0001 — Authority and document-first delivery
- Current direct operator rulings govern; historical material contributes only
  where not later changed; research never auto-adopts; documentation + review
  precede implementation. Every normative artifact traces to the decision ledger.
- **Bounds:** requirements cannot cite a study, recommendation, or historical
  summary as a signed contract. Conflicts stay visible until the operator rules.
- *Rejected (addendum-worthy):* flatten all sources into one summary; treat
  completed studies as adopted contracts.

### ADR-0002 — QMF toolbox boundary and V1 roster
- QMF V1 = open Python toolbox: five libraries (qmf-core, qmf-registry,
  qmf-data, qmf-indicators, qmf-structure) + two modules (venue, risk). QML names
  a future Bot domain, not the framework. Consumer apps own runtime lifecycle.
- **Bounds:** the product surface is libraries with stable domain contracts, not
  a runnable trading node. Loops, schedules, orchestration, product UI are out.
- *Rejected:* application/runtime kernel; adopting a foreign platform's contracts.

### ADR-0003 — Definitions-only qmf-core
- qmf-core defines exact money/time primitives, asset-neutral market nouns, typed
  refusals, deterministic fingerprints, version metadata. No broker, event loop,
  backtest, downloader, node runtime, or Forex-specific policy.
- **Bounds:** one versioned shared vocabulary; asset-neutral so later equities/
  crypto need no rewrite. Four of six freeze choices ratified; two still open
  (backtest fidelity taxonomy, SR* search-quality threshold) and block their own
  implementations.
- *Rejected:* broad kernel (dead); asset-specific core.

### ADR-0004 — Type-specific identity and graph-shaped lineage
- qmf-registry owns identity, lineage, causality registration preconditions,
  attempt gates. Results content-addressed with event + knowledge time; Bots/Books
  keep variant lineage; **only a human may promote into the live zone.**
- **Bounds:** per-type identities + append-only edges (no universal card, no graph
  DB in V1). Causality evidence + attempt semantics deferred to backtesting sitting.
- *Rejected:* universal recipe card (dead); mandatory graph database (dead for V1).

### ADR-0005 — Governed data evidence, holdout, durability
- qmf-data separates ingestion evidence, processed data, governed research access,
  journaling, backup. Applies raw-history retention; protects a final holdout via
  `historical_holdout_months`; explicit research splits; off-machine backup.
  Scheduled lifecycle stays application-owned. **Synthetic data may test
  infrastructure/failure handling but may not validate trading edge.**
- **Bounds:** immutable source evidence, reproducible partitions, durable journals,
  recovery beyond one workstation. Recorder/adapters preserve source identity.
- *Rejected:* reduced/local-only evidence; adopting the study stack wholesale.

### ADR-0006 — Indicator protocol, canonical arithmetic, causal structure lifecycle
- **CT-16 (AD-22):** one indicator contract, two conformant modes (batch +
  streaming) bound by a tier-2 equality law; series vocabulary (`Bar`, `Tick`/
  `Quote`, `BarSpec`, exact rationals) in qmf-core; `BarSpec` replaces bare
  "timeframe"; identity is the entire declared configuration; outputs full-length,
  index-aligned, presence-mapped (not NaN), carry per-sample knowable-at; instances
  shared per configuration.
- **Canonical arithmetic (AD-23):** TA-Lib 0.7.1 pinned as lockfile artifact
  hashes + import-asserted reference-config record; wrap-not-reimplement is
  mandatory (reimplementing a reference formula is a contract defect); tolerances
  are integer ULP counts.
- **Light vs heavy (AD-24):** light iff four declared-and-benchmark-proven bounds
  hold; classification per configuration; verdict machine-scoped, display-only,
  never identity; heavy by default until a live-path baseline exists.
- **Causal structure lifecycle (AD-25):** a family is a type of chart object;
  objects minted once at observation with observed-at, anchor span, precise
  confirmation rule; lifecycle/interaction records append-only edges, current state
  a read-time fold; evidence class is identity.
- **Standing rules:** school-neutral vocabulary everywhere; plain-Python escape
  hatch with experiment→extension graduation is a first-class feature.
- *Rejected:* adopt a 3rd-party indicator/structure platform (prohibited);
  reimplement reference arithmetic (rejected).

### ADR-0007 — Venue-neutral integration (secrets, command uncertainty, adapter contract)
- COMP-QMF-VENUE: venue-neutral module, first adapter targets cTrader Open API in
  Python (never MQL). Four contracts: CT-18 capability, CT-19 command, CT-20 event+
  reconciliation, CT-21 secret/session. **Nothing imports qmf-venue; composition
  root wires** through core-defined sink protocols.
- **AD-26 secrets:** QMF handles secret *references*, never values; `SecretValue`
  never renders (repr/str/serialize/log yield the reference id); tier-1 secret-scan
  gate rides the check pipeline; connection manager is the sole in-memory value
  holder; one live refresher per credential; store-before-discard rotation.
- **AD-27 commands + uncertainty:** command stream = `(VenueId, account)`; exactly
  four base command kinds (`place_order`, `cancel_order`, `close_position`,
  `close_all`) — `amend_protection` is a minted fifth (ADR-0008). Every submission
  resolves to `accepted-by-venue | rejected-by-venue | denied-locally | UNKNOWN`.
  **UNKNOWN is a state, not an error**; while outstanding the stream blocks and
  only an explicit `resolve_unknown` clears it; no component retries, flattens, or
  invents terminal state. Recording precedes interpretation; order-state is a
  read-time fold.
- **AD-28 adapter + capability discovery:** two capability artifacts — a static
  credential-free declaration + a per-`(VenueId, account)` venue-observation profile
  produced post-connect by a verify-or-refuse suite. Foreign floats stored verbatim,
  never identity, converted at a named boundary. Six-stage latency decomposition
  recorded as named rungs, no numeric budgets until measured.
- **Broker identity is deployment configuration, never architecture.**
- Venue market data (ticks, bars, depth, backfill, paging) homes at existing
  CT-10/CT-15 intake — no fifth contract, no new edge.
- *Rejected:* adopt Spotware OpenApiPy SDK (imposes Twisted runtime — only proto
  message definitions consumed); mint a fifth market-data contract; hardcode
  17:00-NY boundary / BID-derived bars (measure per broker instead); freeze the
  broker.

### ADR-0008 — Book, BMS, binding chain, risk-control contracts
- **Authority order (constitutional L36):** bots trade; books control bots; BMS
  accounts for and constrains books; nothing above a bot touches the market —
  bot → book → BMS → operator. **One BMS per account** serves many Books; a Book
  binds exactly one BMS at a time (dated, swappable); an instance never spans
  venues; risk domain = `(BookInstanceId, BmsInstanceId, VenueId, AccountId, world)`.
- Templates are structured configuration with inline identity-bearing numbers,
  per-variable `ui-editable | uneditable` flags, git-logic versioning.
- **Book owns exit policy; bots propose risk-monotonic exits through CT-23; every
  close carries a typed reason; whole-trade attribution credits the opening bot.**
- `amend_protection` = minted fifth venue command (never cancel-then-place); V1
  dynamic SL/TP is breakeven ratchet only.
- **Admission = three technical layers** (linters, demo shakedown, one operator
  signature); **no probation, no paper-performance gate.**
- Kill switch (global, sensor-fed, human de-escalates) ≠ kill line (per-Book
  capital floor, auto-flattening). Flatten authority is assigned (operator always;
  Book policy via pre-declared triggers; protection authority per node severity;
  nobody else). Exit-preservation invariant is law (L39). Same-tick priority = one
  BMS-declared rank table per command stream.
- One control-window contract serves news, daily dead zone, session handover —
  entries-only, live and paper alike, widths configurable, no spine value.
- **Standing operator rules:** corpus precedence for risk (GitBook + node docs
  authoritative; QMX-discussion barred); configurable = UI-editable.
- *Rejected:* BMS as rulebook beside Book; one global BMS above all Books (dead —
  one-account assumption); bots owning exit organs (rejected for V1).

### ADR-0009 — Book-level paper mode as a standing evidence state
- **Paper is a Book-level mode** (`LIVE | PAPER`), expressed as a dated change of
  the Book's execution binding minting a new binding epoch, never a new Book.
  `BENCHED` is a bot-seat word only. Every trigger declares `routes-to-paper |
  blocks-paper` (market-risk controls block paper too; capital/authority controls
  route to paper); routing is never a way around a control (blocked decisions are
  journaled). One active paper-routing target per live binding; per-intent
  `execution_target` resolved once at intent mint.
- Paper money is frozen evidence: configurable starting balance, never
  hand-adjusted; a reset mints an operator-signed paper epoch record; paper P&L
  never becomes Treasury cash and never buys a seat. Return to live automatic only
  for clocked mechanical causes; anything touching real money takes an operator
  signature; paper performance never authorizes a return. Decay judged in R.
- *Rejected:* parallel Bot paper twins (dead); blackout simulator (dead); a paper
  target carrying no BMS (overruled).

### ADR-0010 — R, the dimensional law, SQS V1, bench vocabulary
- **R is one relationship, three typed faces:** `original_risk_distance`
  [price-delta], `original_risk_amount` [money], `r_multiple` [dimensionless],
  frozen at admission. **Every position declares its planned full-loss price before
  it opens or admission refuses — no planned loss point means it cannot trade.**
  Numeraire is USD system-wide; non-USD refuses until a rate source is ratified.
- Closed unit-kind vocabulary types every variable/formula; a symbolic checker
  refuses mismatches; every formula ships an executable worked example.
- **SQS V1** = corpus ratio sensor (historical avg spread ÷ current live spread)
  as a CT-16 configured producer; every parameter configurable UI-editable, no
  spine value; sensor computes, transport carries, Book door decides; **V1 blocks
  only** (never sizes, never authorizes).
- Bare word "stop-out" banned: `venue_liquidation` = broker margin stop-out; the
  bench counts `qualifying_loss_exit`s where `realized_r ≤ −q`, q UI-editable
  defaulting to ~1R; breakevens never count. Bench counter is a read-time fold over
  CT-29 exit records bounded by the binding epoch; seat state `active | benched`.
  Alpha decay ships as evidence primitives only — measurement publishes, never acts.
- *Rejected:* implement recovered FORM-0006 (dead — dimensionally invalid, kept as
  a negative test); design SQS fresh (reversed — old ratio sensor adopted); keep
  the overloaded single B.

### ADR-0011 — Defer consumer runtimes and products beyond QMF V1
- Backtesting, modular sandbox, visual Simulator, MIS, QML Bot library, agentic
  runtime organs are outside QMF V1.
- **Bounds:** QMF V1 exposes reusable contracts without pretending to be a
  complete trading node; deferred products need later design sittings. (Note:
  QMB and QML have since been pulled forward — ADR-0017/0018.)
- *Rejected:* central always-on backtesting service (dead); adopt Nautilus / run
  adoption spike (dead).

### ADR-0012 — Runtime matrix, workspace packaging, quality gates
- **Runtime:** CPython 3.14 pinned across all packages/CI/sandboxes. Tier-1 tested
  targets: Windows 11 x86-64 + Ubuntu LTS x86-64. Source stays pure-Python /
  OS-neutral.
- **Packaging:** one uv workspace, seven installable packages importing as `qmf.*`
  PEP 420 namespace (no `qmf/__init__.py` ever); `src/` layout; explicit deps in
  each `pyproject.toml`; `uv_build` backend; one committed `uv.lock`; seven roster
  packages release in **SemVer lockstep**. Calendar extensions are separate
  versioned packages outside the roster.
- **Toolchain:** ruff (format+lint), pyright strict workspace-wide, pytest.
  Coverage floor = `registry:coverage_floor_percent` (80%); CT-01/CT-02 primitive
  modules require **100% branch coverage**. Frozen dataclasses for value types,
  `typing.Protocol` seams. Canonical: `poe fmt|lint|types|test|check`.
- **Gates (event-bound, not Git-host):** Tier 1 `poe check` per work unit; Tier 2
  `poe check-integration` (+ integration + contract tests, each package isolated)
  on landing to integration; Tier 3 `poe check-release` (+ build all + clean-install
  smoke on both tier-1 OSes) on ship. A **contract test** = executable conformance
  suite for a `CT-*` public shape, owned by the owning package, run by producer +
  consumers at tier 2.
- **Version ladders:** SemVer lockstep for code; per-contract integer format version
  stamped in every artifact — meaning never changes after the fact; QMF never loses
  the ability to read old evidence.
- **Dependencies/licences:** permissive (MIT/BSD/Apache/PSF) freely; LGPL only
  unmodified + separately installed; GPL/AGPL prohibited; strategy-family libs +
  platform-imposing deps prohibited. `qmf-core` takes **zero** outside deps (stdlib
  only). Every dep gets one `DEPENDENCIES.md` line.
- *Rejected:* per-package repos; one monolithic distribution; per-agent tool choice;
  gates bound to Git-host mechanics; one version ladder.

### ADR-0013 — Exact values, exact time, artifact identity
- **Exact money:** Money/Price/Quantity are whole-number integer counts at a
  declared scale: `Money(currency, scale)`, `Price(instrument, scale)`,
  `Quantity(unit, scale)`. Mixed-scale auto-promotes losslessly or refuses; no
  implicit rescale/rounding. **Binary float banned on the money path** (money path
  is a *taint*, not a location); foreign money stored verbatim as evidence.
- **Exact time:** every stored timestamp is int64 UTC nanoseconds (POSIX no-leap-
  second); overflow refuses. Civil date and trading date are distinct types;
  `TradingDate` carries calendar rule-set identity + version in-band; cross-rule-set
  comparison refuses. Wall/monotonic clocks type-separated; clock access is a
  core-defined protocol injected at the composition root — nothing below reads the
  system clock. `(instant, writer, sequence)` is a replay-determinism device with no
  causal meaning.
- **Calendars, three named kinds:** market-hours calendar (accounting rollover +
  session schedule), day-boundary calendar (accounting boundary per account),
  news calendar (COMP-CALENDAR-FEED). Forex market-hours calendar ships first with
  a 17:00 America/New_York rollover. Extensions pin tzdata and verify at import.
- **Identity:** instrument identity = (venue, opaque symbol), never parsed; `VenueId`
  operator-minted, opaque, stable, never reused; a distinct broker/legal entity is a
  distinct venue. Venue and Account are distinct core nouns; one venue holds many
  accounts each with a role (live/demo/paper-validation/paper-benched/prop-firm).
  Multi-broker (~6 venues) and migration are normal cases.
- **Deterministic fingerprints:** single canonical serializer + `fp1` recipe in
  qmf-core (UTF-8 JSON, sorted keys, NFC, integer identity numerics, floats refused,
  null prohibited, arrays order-significant, SHA-256, `fp1:sha256:<hex>`). Every
  contract field is identity by default; display-only requires explicit versioned
  declaration. Idempotent re-write accepted silently; true collision refused/alarmed.
- **Typed refusals:** seven categories — invalid input, unsupported capability,
  unavailable dependency, stale evidence, policy rejection, transient venue failure,
  storage failure. **Public boundaries return refusals as result unions, never raise
  across a package boundary.** One construction pattern: unchecked constructor +
  validating `try_create`.
- **Result label + worlds:** every result carries producer contract format version,
  input fingerprints, evidence time range, computation identity, world — together
  its identity. Worlds: `live` (paper/demo runs are `world=live`), `replay`,
  `simulated` (reserved, unusable in V1). Factory sandboxes never produce evidence
  timestamps.
- New component: **COMP-QMF-CALENDAR-FOREX** (first market-hours calendar extension).
- *Rejected (many, addendum-worthy):* binary float on money path; `Price` tagged
  with a single currency; normalizing venue values at ingest; monotonic readings as
  timestamps; six refusal categories (seventh added); refusals as exceptions;
  `world=simulated` usable in V1.

### ADR-0014 — Measured performance, loud failure, application-owned concurrency
- **Measure-then-budget:** QMF invents no performance numbers. Every component ships
  a benchmark harness (same status as unit tests) measuring **speed AND peak memory**
  at a load ladder in framework-native units. First measurements = fingerprinted
  baselines scoped to a declared (OS, CPU-class) tuple; regression threshold stated
  at baseline as a multiple of measured variance; a regression beyond threshold
  fails the tier-2 merge gate (memory equally with speed). One stated constraint:
  **`qmf-core` imports in well under one second.**
- **Loud failure:** errors/refusals always carry context, never swallowed.
  Structured logging carries `correlation_id` propagated across every package
  boundary. Every component exposes a no-argument `health()` returning a typed
  report. **Logs are not journals** (log text = display; journals = evidence).
  Signals must be exportable to Prometheus-class stacks.
- **Concurrency:** QMF values immutable/shareable. Purity binds qmf-core,
  qmf-indicators, qmf-structure. Stateful components (stores, recorders, adapters)
  follow one-writer-per-stream with unlimited readers. **QMF spawns no threads/
  background work — the application owns all concurrency.** Async only at the venue
  network edge.
- *Rejected:* numeric budgets up front; speed as the only axis; global load ladder
  in bot counts; shipped mock/fixture products; choosing the monitoring stack now;
  logs + journals as one stream; async-first public APIs; QMF owning schedulers.

### ADR-0015 — Registry records, multiplicity, promotion skeleton
- **Records/lineage:** per-kind record schemas, each its own versioned contract,
  sharing a tiny common header (kind, format version, at-birth parent refs, writer,
  sequence). Stable id derived from `fp1` (never minted) so identical work
  deduplicates. Lineage that accrues after birth lives in append-only typed edge
  records (supersedes, promoted-from, occurrence-of, corroborates, disagrees-with);
  edge files pinned JSONL, fsync-appended, never rewritten. No database server.
- **Multiplicity at every layer:** a Bot has one-or-more confluences; a confluence
  one-or-more levels/triggers/confirmations; no layer hardcodes exactly-one. Bot
  identity is its content; Bot↔Book↔account binding is a separate dated record; one
  Bot at exactly one Book at a time; re-binding paper→live never mints a new Bot.
- **Promotion skeleton:** a promotion-occurrence card kind with a **human-only
  signer**, signed immutable record, and a mandatory plain-words summary declared an
  identity field. V1 signing = operator's recorded approval attesting the record's
  `fp1` (reviewer identity + instant); no crypto dependency. Registry card is
  canonical; the journal `promotion` event carries only the card fingerprint +
  `correlation_id`. The promotion gate workflow/UI/timing is platform territory.
- Causality/look-ahead registration gate + attempt counter deferred (GAP-0016/0017).
- *Rejected:* universal recipe card (dead); graph DB (dead V1); minted stable ids;
  created-at as identity; lineage in header; free-form edge files; Bot=one confluence
  (dead); Bot identity including binding; crypto signatures for V1 promotion.

### ADR-0016 — Data rooms, splits, journal streams, first ratified edge
- **Seven room-roles per world** (live/replay/simulated): ingest door, immutable raw
  archive, processed, journal, split-governed research door, backup, registry room.
  A cross-world read is a `policy rejection` refusal.
- **Stores:** Parquet (columnar time-series), DuckDB (local analytics — rebuildable
  views only), SQLite (transactional metadata), JSONL (append streams), each behind
  a QMF-owned contract with stdlib-typed boundaries; no database server. Only
  raw-archive and journal formats are evidence-bearing.
- **Migrations/retention/backup:** migrations run preflight → backup → dry-run →
  migrate → verify, never in-place mutation of the only copy. Raw originals + lineage
  kept forever. **Backup design: nightly, encrypted, versioned, off-machine to an
  object-storage bucket, with automated sample-restore tests + periodic full-restore
  rehearsal.** QMF provides primitives; schedule/execution app/ops-owned.
- **Splits + seal:** dataset splits are fingerprinted, time-ordered, non-overlapping
  manifests, each pinning one calendar rule-set identity in-band. The **12-month seal
  is a no-peek lock** (not deletion) enforced NOW as a `policy rejection` refusal at
  every read boundary (raw, processed, research door, restored backups); the sealed
  period gets one logged final look journaled as a `control action` subtype.
- **Journal streams:** N streams, one per producing component under its `WriterId`,
  gapless per-(writer, boot-epoch) sequences. Seven event types: decision, order,
  fill, risk transition, promotion, data quality, control action. `correlation_id`
  excluded from `fp1`.
- **Dependency direction (default-deny):** qmf-core depends on nothing; every package
  may depend on qmf-core; nothing imports qmf-venue or qmf-risk. **Exactly one
  inter-library edge ratified: qmf-registry → qmf-data** (CT-11 append-store).
- Topology: trading-node VPS records + syncs down; workstation holds working archive;
  bucket catches nightly copies.
- *Rejected:* one store for everything; a database server; analytics formats as
  evidence; six room-roles (seventh added); rooms shared across worlds; the seal as
  retention; one journal stream; `correlation_id` as identity; merging disagreeing
  sources; QMF owning the backup schedule; in-place migration; permissive inter-lib
  dependencies.

### ADR-0017 — QMB: experimentation/backtesting library + qmb CLI
- **QMB = one pure library + `qmb` CLI**, an application-layer product built ON QMF
  (never a roster package). Python API door now, MCP door after CLI v1. Hexagonal
  with **config-composition:** every run consumes exactly one resolved, read-only,
  fingerprinted run-config; `run()` is pure and returns a CT-32 performance-result;
  one impure orchestrator owns all writes (per-run operational logs during, exactly
  one WriterId-scoped ledger line at completion). Bar verdicts are reader-derived
  per-requirement folds, never frozen.
- Execution fidelity ships as ports with an honest `optimistic` taint until GAP-0048;
  the fill-model solve is calibration from QMX's own recorded evidence, never
  invention. Registry state arrives as immutable as-of sets over a passive hub.
  Data acquisition is download-once with per-window license tags. Distribution is a
  pinned lockfile dependency (click + optuna pinned exactly).
- New component **COMP-QMB**; QMB publishes but never benches/promotes/binds; it's
  the first sanctioned composition root wiring the risk contracts in `world=replay`.
- Dukascopy data-licensing question ruled CLOSED (personal-use backtesting).
- *Rejected:* adopt/fork a donor engine (Jesse/LEAN — both dead in ledger);
  permanent central backtesting service (dead); keep deferring.

### ADR-0018 — QML: bot-authoring library
- **QML = one uv-installable distribution (`import qml`)**, application-layer library
  built ON QMF, never a roster package/framework/engine, never a cross-component
  contract layer. Surface is three thin things: author-side types/helpers producing
  Bot-domain registry artifacts (CT-33/CT-34), the bot runtime protocol, the
  conformance gate. **QML mints no new QMF-ladder (CT-*) shared contract.** Imports
  qmf-core, qmf-registry, qmf-risk — **never qmf-venue.**
- **A governed bot is exactly two artifacts:** the **declaration** (structured config
  under template discipline, registered as CT-33 Bot definition) + the **logic**
  (plain Python conforming to the runtime protocol, identity = distribution + version
  + canonical source-manifest fingerprint). **Plain Python stays first-class forever**
  — an unregistered bot needs zero QML imports; conformance is the ticket into
  governed evidence and Book seats, nothing else.
- CT-33 Bot definition fills the reserved Bot kind; CT-34 confluence is its own
  reusable registry artifact (legs: `level | trigger | confirmation | filter`).
  Strategy family = opaque operator-minted keying token with no authority; every Bot
  declares exactly one. **Bot never sizes, never touches venue, never reads a clock,
  never does I/O**; the declared full-loss price is derived Book-side at the door
  (single-sited), the entry proposal carries only an advisory stop proposal.
- Conformance gate is technical, never performance: Layer 1 declaration linter at
  registration; Layer 2 sandboxed execution conformance (pure verdict function +
  host-owned runner). Prediction linter's four pinned checks fill the admission-bar
  Layer-1 slot. Governed live/paper seats execute the canonical (default) assignment
  only; a tuned assignment promotes to a new Bot version.
- Parent-contract mints: **CT-22 format version 2** and **CT-23 format version 2**
  (owned by qmf-risk, QML-authored semantics, migration notes mandatory).
- Build order: QML before the trading node, alongside QMB; the node hosts seats later.
- *Rejected:* revive QML as a cross-component contract layer (the old failure);
  revive the `.qml` DSL + Monaco (stated drop); fold authoring into qmf-registry or
  QMB; revive `max_acceptable_complexity_score` gate (stated drop).

---

## Section 2 — Golden scenarios (journey each implies + acceptance signal)

- **SCN-0001 — Core Freeze Choices Block Implementation.** Journey: an agent
  implements a core boundary. Acceptance: ratified CT-01..05 boundaries are built by
  conforming to contracts; the two still-open freeze choices (backtest fidelity, SR*)
  must stop before code fixes a value. Signal: an open freeze choice is not authority.

- **SCN-0002 — Late Source Correction Preserves Earlier Evidence.** Journey: a source
  replay delivers a correction to an earlier observation. Acceptance: original stays
  preserved; correction is a distinct `fp1` artifact via idempotent intake keyed on
  (source, source-native id, revision), linked by an append-only typed edge; foreign
  timestamps/money stored verbatim.

- **SCN-0003 — Default Research Access Excludes the Sealed Holdout.** Journey: a
  research consumer requests the default dataset release. Acceptance: sealed
  identities absent; any read touching the sealed period refuses `policy rejection`
  at every boundary (incl. restored backups); one authorized final look journaled as
  a `control action` subtype.

- **SCN-0004 — Backup Does Not Claim Recoverability Before Its Boundaries Exist.**
  Journey: an agent snapshots, transmits off-machine, restores, migrates, or declares
  DR complete. Acceptance: recoverability claimed only through verify primitives
  (sample-restore + full-restore rehearsal); never mutate the only copy; numeric
  RPO/RTO await the node/ops sitting.

- **SCN-0005 — Uncertain Venue Submission Resolves to UNKNOWN.** Journey: an app
  submits a venue command and transport certainty is lost. Acceptance: outcome is
  UNKNOWN (a recorded state); the `(VenueId, account)` stream blocks; no retry/
  flatten/assumed outcome; only explicit `resolve_unknown` after reconciliation
  read-back clears it; five command kinds; four-outcome law; sensing never blocks.

- **SCN-0006 — Book Paper Transition Is a Dated Binding-Epoch Change.** Journey: the
  operator flips a Book to paper. Acceptance: no new object — a dated binding-record
  change minting a new binding epoch; per-intent execution_target resolved once;
  one active paper target; blocked-for-market-risk controls block paper too; paper
  money is frozen evidence; return to live not symmetric (real money = operator sig).

- **SCN-0007 — An Agent Cannot Promote an Artifact to Live.** Journey: an agent tries
  to move an artifact to the live zone. Acceptance: status doesn't change; only a
  human-signed promotion occurrence attesting the card's `fp1` (+ plain-words summary
  + Book/BMS-definition fingerprint as identity fields) authorizes it; three-layer
  admission packet, no probation/paper-performance gate.

- **SCN-0008 — News Windows Block Entries by Instrument Scope, Live and Paper.**
  Journey: a news window is in force and a bot proposes an entry + an exit.
  Acceptance: entry blocked on in-scope instruments live+paper; exits/protection never
  blocked; scope resolved through dated currency-exposure records (never symbol
  parsing); fail-closed on missing records; widen-never-shrink read-time fold; blocked
  decisions journaled on the veto path.

- **SCN-0009 — Synthetic Stress Evidence Cannot Prove Trading Edge.** Journey: a
  deterministic synthetic generator drives ingest/failure-path tests. Acceptance:
  results support only infrastructure/failure claims — never edge, promotion, fill
  model, or readiness; no fake Bot/strategy/estate shipped; toolchain ratified,
  numeric budgets await baselines.

- **SCN-0010 — Same-Tick Risk Actions Arbitrate by Rank on One Command Stream.**
  Journey: several protection/exit actions fall due on one tick, one stream.
  Acceptance: one arbitration point per stream by BMS-declared rank; colliding
  commands collapse to one emission; composing effects (`suspend_new + flatten`) both
  execute; exit-preservation invariant holds (no control reduces protection a
  lower-ranked act would deliver); suppression is first-class evidence.

- **SCN-0011 — A Day of Exits Benches a Seat by Qualifying-Loss Count.** Journey: a
  bot closes four virtual positions in a day. Acceptance: each mints one CT-29 exit
  record; `realized_r ≤ −q` counts exactly the two qualifying losses (breakeven +
  scratch ignored); read-time bench fold crosses per-family threshold; seat flips
  `active → benched` routing to paper while the Book stays LIVE; next-open reset is a
  clocked CT-24 transition (no operator signature); recording precedes interpretation
  (a later intent refuses `stale evidence` if the prior exit record hasn't persisted).

- **SCN-0012 — An Agent Runs a Replay Backtest Against a Book.** Journey: an agent
  runs `qmb backtest <bot> --book <alias>`. Acceptance: door resolves Book/BMS by
  fp1 through one registry-read port; compiler produces one resolved run-config
  (fingerprint = run-id root = ledger key); `world=replay` binding minted;
  orchestrator spawns one governed isolated process; run loop advances a frontier
  clock through pinned sub-phase order with warm-up trading-locked and all fills
  `optimistic`-tainted; `run()` returns a CT-32 artifact + exactly one
  `role=confirmation` ledger line; later Book-bar read derives per-requirement
  verdict that re-verdicts with no re-run. Failure branches: stale Book ref =
  stale-evidence refusal; store-persisted synthetic = `world=simulated` = policy
  rejection for governed evidence.

---

## Section 3 — NFR signals per lens (concrete numbers, budgets, models)

### Performance (lenses/performance/budgets.md)
- **Method:** measure-then-budget (DEC-0111). No numeric per-component or
  end-to-end budgets exist yet — they await first recorded baselines and may not be
  invented. Every component ships a benchmark harness measuring **speed + peak
  memory** at a load ladder in framework-native units (calls/s, series length,
  artifact count).
- **Reference sizing:** `registry:design_bot_concurrency` = ~40-bot real-workload
  design case with **10 / 100 / 200** load marks (also written 10/40/100/200) — a
  reference for sizing the ladder, never an SLO, percentile, capacity guarantee, or
  pass threshold.
- **Stated constraint (not a measurement):** `qmf-core` imports in **well under one
  second** (`registry:core_import_time_budget`).
- Baselines fingerprinted + scoped to a declared **(OS, CPU-class)** tuple; each
  regression threshold stated at baseline as a multiple of measured run-to-run
  variance. A regression beyond threshold (speed OR peak memory) fails the tier-2
  merge gate.
- **AD-13 rungs (definitions, no numbers):** each CT-16 configuration declares two —
  burst throughput + per-tick latency at the configured BarSpec (no-op tick path
  measured separately). Each CT-17 family declares three — active object-set size,
  objects minted per bar, interaction records per bar. **Light** iff four
  benchmark-proven bounds hold; heavy by default until a live-path baseline exists.
- **Venue:** six-stage live-path latency decomposition (tick received → evidence
  write → indicator update → decision → risk evaluation → order submitted) as named
  rungs, no numeric budgets until measured; each rung a monotonic delta within one
  boot epoch on one machine.
- Backup numerics (`backup_recovery_point_objective`, `..._time_objective`,
  `restore_verification_cadence`, `backup_retention_period`) are **null** pending the
  node/ops sitting; `backup_cadence` = nightly.

### Security (lenses/security/security-model.md)
- Authority concentrated at contract seams; **human-only live promotion.**
- **Secret lifecycle (AD-26, law):** QMF handles opaque `SecretRef`, never values;
  `SecretValue` render-guard (repr/str/serialize/log yield reference id); **tier-1
  secret-scan gate rides `poe check`.** Secrets never in repos, config, `.env`, CLI
  args, journals, evidence, fingerprints, logs, refusal context, health reports, or
  metric labels. Values injected at composition root from a protected store
  (`systemd-creds`-class on VPS). Connection manager = sole in-memory value holder
  through an injected `SecretStore` port. One live refresher per credential;
  store-before-discard rotation; a failed store after rotation alarms + blocks the
  command pipe (sensing unaffected).
- **cTrader token facts (ratified):** ~30-day access token; **never-expiring refresh
  token = crown-jewel secret**; cTID re-authorization invalidates ALL outstanding
  refresh tokens (compromise-drill anchor). Testing uses **demo credentials only.**
- **Supply chain:** zero-dependency core; licence allowlist (permissive free; LGPL
  unmodified+separate; GPL/AGPL + strategy-family + platform-imposing prohibited);
  every dep one `DEPENDENCIES.md` line; per-package tier-2 isolation catches
  undeclared imports.
- **Trust boundaries** table: human→live (human-only signed promotion); middleware→
  backend (translate, never decide); backend→data (data owns no business rule; cross-
  world read = policy rejection); command caller→venue (five command kinds,
  four-outcome law, no live caller assigned in QMF).
- Threats/controls incl. confused-deputy order submission, replay/duplicate command
  (fp1-derived identity, idempotency), look-ahead/stale evidence (12-month seal
  enforced now), evidence tampering (append-only, N journal streams, collision
  refused/alarmed), automated action exceeding authority (no detector grants
  promotion/flatten/exit/restore).

### Observability — logging (lenses/observability/logging-spec.md)
- **Logs are not journals.** Operator/diagnostic **log** text = UTC ISO-8601 with
  explicit `Z`; **journals/evidence** = int64 UTC nanoseconds + `WriterId` +
  per-(writer, boot-epoch) sequence; ISO-8601 admitted only as a display-only field
  excluded from identity.
- `correlation_id` (exact field name) propagates across every package boundary but
  never enters a pure value contract's signature (rides caller context). Every
  component (owner of external resources/long-lived state, incl. streaming indicator
  + structure family instances) exposes `health()`.
- Seven journal event types across N per-component streams; a sequence gap signals
  loss. Venue path binds `data quality` (measurements/verdicts) and `control action`
  (suspend-new, drain, session restart, throttle engaged, reconnect); CT-20
  cardinality law = exactly one event per observation/submission/outcome.
- Entity journals (Book/BMS/per-bot) are **read-time projections** over writer-scoped
  streams, not streams of their own. Operator log-level taxonomy, logger names, paths,
  query system belong to the node/ops sitting.

### Observability — metrics/alerts (lenses/observability/metrics-and-alerts.md)
- **No ratified metrics schema, aggregation window, dashboard, alert threshold,
  severity tier, notification destination, paging route, or auto-remediation.**
- Two binding obligations: signals must be **exportable to Prometheus-class stacks
  with push alerting** (stack choice = node/ops); performance = measure-then-budget.
- DevOps time-audit names concrete signals to export once a node exists: **chrony
  offset, stratum, sync-age; per-venue clock skew; clock step counter** — over a push
  path with **no on-call rotation.**
- Named **state/event-triggered alarms** (no numeric threshold): rotation
  store-failure, unmapped venue error code (default `(transient venue failure,
  retryable=no, outcome=UNKNOWN)`), reused command identity, outstanding UNKNOWN,
  daily-boundary drift, missing scope record, paper-stream outage (**same alarm class
  as a live outage**), undeliverable protection intent, fold-cannot-resolve
  (fails-closed → most-restrictive-state), suppression/veto counts (evidence, not
  alarms).
- **Alert authority:** an alert is evidence, not permission — cannot promote,
  authorize an order, flatten, exit, change Book mode, rotate a secret, restore, or
  command a provider.

### Ops runbook (lenses/ops/runbook.md)
- QMF V1 is **design-only** — no ratified start/stop/restart/deploy/migrate/rollback/
  live-connection command. Grants no permission to init, deploy, access credentials,
  connect, order, promote, change mode, flatten, or operate live money.
- Ratified env/commands: CPython 3.14; uv workspace of seven `src/` packages; local
  validation `poe fmt|lint|types|test|check` (80% coverage floor, 100% branch on
  CT-01/CT-02); three quality tiers; two version ladders.
- **Venue first-connection verify-or-refuse suite:** spot-timestamp unit (assert ms
  by magnitude), daily-boundary measurement (mint venue-scoped market-hours calendar
  identity), bar-basis reconciliation (BID/ASK), pip-formula validation
  (`pipSize = 10^-pipPosition`), money exponent (require per-message `moneyDigits`,
  never default to 2). Session duties (declared schedulable, app drives): heartbeat
  (**10-second** safe bound), token refresh, reconnect, gap replay, verification
  monitors — **session recovery never resubmits a command.**
- **Operator rider:** ~1-week warm-up/observation period before live trading.
- Bind-time capability check; three-layer admission (Layer 3 = one operator
  signature); control-action vocabulary (`suspend_new`, `drain`, `flatten`, `resume`
  — `resume` operator-only). Kill switch (global) vs kill line (per-Book capital
  floor). Paper flip = operator-ratified dated action.
- **Node/ops time-audit obligations (bind later sittings):** VPS OS clock runs chrony
  with **≥4 sources** (iburst, makestep boot-only) as sole authoritative stamper; a
  travelling Windows laptop is unfit to stamp; no-trade-before-sync (`chronyc
  waitsync`); slew-only-while-live; numeric drift bands sized to **~1s decisions**
  (ok / warn / no-new-entry / halt) as typed refusals; gap records for suspect
  windows; RTC in UTC / system tz UTC / `TZ=UTC`; WriterId on the shared VPS.

### Ops incident playbook (lenses/ops/incident-playbook.md)
- Only a human may promote; no agent/detector/alert grants trade/flatten/mode/rotate/
  restore/bypass authority. Venue outage fail-closed (in-flight → UNKNOWN, retry
  prohibited, reconciliation gates command pipe only, recovery never resubmits).
- Kill switch (global black-swan authority, auto-escalate, human-only de-escalate) vs
  kill line (per-Book capital floor, auto-flatten + stand-down). Exit-preservation
  invariant. `resume` operator-only. Standing intent (not a queue): protection action
  journaled before dispatch, re-decided (not retried) on reconnect against reconciled
  state; never time-expires; `flatten` satisfies only on a `reconciled` verdict.
- Two ratified tested procedures: **credential compromise-recovery drill** (cTID
  re-auth → app-credential reset → store replacement → session restart) and the
  **UNKNOWN-resolution procedure** (preserve → honor block → read back → resolve
  explicitly → cancel-vs-fill rule). Reconciliation verdicts: `reconciled | drift |
  unknown | out-of-lookback`.

### Testing strategy (lenses/testing/test-strategy.md)
- **Coverage: 80% floor per package; 100% branch on CT-01 (money) + CT-02 (time)
  primitive modules.** Frozen dataclasses for value types, `typing.Protocol` seams.
- Three tiers bound to factory events: Tier 1 `poe check`; Tier 2
  `poe check-integration` (integration + contract tests, each package isolated so an
  undeclared import fails); Tier 3 `poe check-release` (build all + clean-install
  smoke on both tier-1 OSes). A contract test = executable conformance suite for a
  CT-* public shape, owned by the owning package, run by producer + consumers at
  tier 2.
- Test levels: static/doc gates, unit (injected clock, declared seed, no network),
  property/invariant, contract, integration (demo credentials only), acceptance
  scenario. Public boundaries **return** refusals (assert category + context, never
  parse exception text).
- Risk contracts (CT-22..25, CT-27..32) are **ratified surface, defined-unwired** —
  conformance-testable but no integration/runtime proof until the node wires them; a
  test must never turn a `pending` slot or the deferred look-ahead gate into a passing
  fixture.
- Full contract-test matrix CT-01..CT-32 with per-contract proof + residual blockers.
  Law/authority property-test families (money/time exactness, fp1 determinism, typed
  refusals, concurrency stance, human promotion, seal isolation, synthetic-data limit,
  venue command/uncertainty, exit-preservation, dimensional unit-kind + FORM-0006
  negative test).

### Testing fixtures/scenarios (lenses/testing/fixtures-and-scenarios.md)
- Fixture classes with stable proof keys (contract round-trip / boundary / invalid;
  component failure mode; law/invariant property; external controlled replay;
  synthetic infrastructure). Repo layout: uv workspace, per-package `tests/` +
  `examples/` (L27 reference usage).
- Determinism rules: unit fixtures make no network calls; time-dependent fixtures
  inject a CT-02 int64-ns clock (never system clock below the composition root);
  randomized fixtures declare a seed; equal semantic inputs → equal `fp1`; secret
  handling by reference only, demo credentials only. Source class ∈ {source-evidence,
  controlled-replay, synthetic}; synthetic can never validate edge.
- Golden-scenario binding maps SCN-* documents to fixture identities, CT boundaries,
  and assertions; four risk golden scenarios (SCN-0006/0008/0010/0011) stay
  defined-unwired.

### Data layer (lenses/data/data-layer.md)
- Component ownership map (Data / Data-Ingest / Data-Store / Data-Backup / Registry /
  external). Boundaries normative; default-deny edges with the single ratified
  `qmf-registry → qmf-data` (CT-11) edge.
- **Seven room-roles per world** (ingest door, immutable raw archive, processed,
  journal, split-governed research door, backup, registry room); cross-world read =
  policy rejection. Only raw archive + journal are evidence-bearing.
- **Four-store stack:** Parquet / DuckDB / SQLite / JSONL behind QMF-owned contracts,
  no database server. Lineage edge files pinned JSONL (fp1-canonical, LF-terminated,
  append-with-fsync, size-rotated with monotonic ordinal).
- Venue market data enters as CT-10 source observations via CT-15 intake (venue is a
  `source` per AD-19); raw depth = verbatim wire payload; foreign-float boundary
  converts to scaled integer at receipt with a declared identity-bearing rounding
  mode; **no silent sibling-feed failover**; venue bars ungoverned until the daily
  boundary is measured + verified per broker.
- Bitemporal law (event-time, known-at, source, revision; corrections appended).
  12-month seal enforced now as policy rejection at every read boundary. N journal
  streams; entity journals are read-time projections. Two cross-role READ exceptions
  within `world=live` (decay-cohort read; entity-over-multiple-roles); no write
  exception ever. Treasury boundary-event kind (`sweep | refund | re_seed |
  paper_epoch_reset`) — no money moves without one. Exit record (CT-29) is the
  decay-evidence base, one per virtual (Book) position close.

### Bug triage (lenses/bugs/triage.md)
- No global severity tier / response-time target / numeric impact threshold. Two
  loud-failure invariants govern every bug: public boundaries **return** typed
  refusals (never raise across a package boundary); errors/refusals never swallowed.
  Seven refusal categories are the reference set; a swallowed/context-lost refusal is
  a defect; missing `correlation_id` or broken `health()` is a defect.
- Triage classes: documented-behavior regression; authority-boundary violation;
  unresolved-contract case (open GAP / null registry / `pending` slot); external-
  dependency incident; documentation/traceability defect.
- Ratified risk-domain failure classes (now regressions, not open cases): bind-time
  capability refusal (shortfall refuses at bind time, not trade time); blank-
  admission-bar live binding = policy rejection; fold-fails-closed on the trading path
  (most-restrictive-state, never permissive/raise); stale-evidence intent refusal when
  an exit record lags.
- Reproduction record fields: OS (Windows 11 x86-64 / Ubuntu LTS x86-64), CPython
  3.14, uv-workspace/build identity, `uv.lock` versions; CT-02 clock + event/knowledge
  time; redacted secrets only.

---

## Cross-cutting NFR numbers/budgets index (for quick PRD reference)
- CPython **3.14** pinned; tier-1 OSes: **Windows 11 x86-64**, **Ubuntu LTS x86-64**.
- Coverage floor **80%**; **100% branch** on CT-01/CT-02 primitive modules.
- `qmf-core` import **< ~1 second** (only stated performance constraint).
- Reference workload **~40 bots**, load marks **10 / 100 / 200**.
- Timestamps: **int64 UTC nanoseconds**, POSIX no-leap-second.
- Historical holdout seal: **12 months**, no-peek, enforced now.
- Backup: **nightly**, encrypted, versioned, off-machine; RPO/RTO/retention/
  verification-cadence numerics **null** (node/ops).
- Venue rate limits (evidence, cite-only): **50 req/s** non-historical + **5 req/s**
  historical per connection; **10-second** heartbeat safe bound; **~30-day** access
  token + never-expiring refresh token; **1-week** historical tick-span cap.
- Fingerprint: **SHA-256**, `fp1:sha256:<hex>`.
- Refusal categories: **7**. Journal event types: **7**. Room-roles: **7** (per
  world: live/replay/simulated). Roster packages: **7** (SemVer lockstep). Command
  kinds: **5** (incl. `amend_protection`). Stores: **4**.
- Chrony **≥4 sources**; drift bands sized to **~1s decisions**.
- Numeraire: **USD** system-wide.
- Every risk/sizing/window/bench/SQS number is a configurable UI-editable variable
  with **no spine value** — recorded numbers are evidence, never ratified constants.
- Two open freeze choices block their own code: **backtest fidelity taxonomy
  (GAP-0048)** and **SR* search-quality threshold (GAP-0049)**; look-ahead/causality
  registration gate (GAP-0016) + attempt counter (GAP-0017) deferred to backtesting.
