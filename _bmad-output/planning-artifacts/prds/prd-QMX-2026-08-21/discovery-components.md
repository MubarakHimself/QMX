# PRD Discovery Extract — Components

Scope: PRD-relevant content only — per-component purpose, capabilities in operator/user
terms (candidate functional-requirement groups), explicit exclusions and deferred items,
and dependencies. Implementation detail deliberately omitted. One section per component,
each citing its source file under `docs/components/`.

The corpus is a workspace of Python libraries (the seven-package QMF roster plus calendar
extension), two application-layer products built on QMF (QMB experimentation/backtest,
QML bot-authoring), and external-system boundaries (venue, sources, object storage). A
recurring, cross-cutting theme every PRD requirement group must honour: exact-integer
money/time (no binary float on the money path), fingerprinted identity (fp1), seven-category
typed refusals, append-only evidence never overwritten, per-world isolation, human-signed
promotion into live money, and "configurable = UI-editable."

---

## COMP-QMF-CORE — `docs/components/qmf-core.md`

**Purpose.** The definitions-only, zero-dependency library that gives every QMF component
one exact, asset-neutral, versioned domain language. Owns contracts CT-01..CT-05. Everything
downstream (trading node, backtesting, agentic system, UI) is built with these libraries
rather than re-implementing their contracts.

**Capabilities (candidate FR groups).**
- Exact monetary and quantity values: Money, Price, Quantity as whole-number integer counts
  at a declared scale; a PriceDelta type for closed price subtraction; exact-rational
  parameters (scaled integer or numerator/denominator) for every non-integer parameter.
- The money-path taint rule: any value transitively contributing to order quantity, price,
  P&L, or balance is on the money path; binary float is banned there and crosses back only at
  named conversion boundaries that state their rounding mode.
- Foreign values stored verbatim as evidence with declared scales; conversions derived with
  lineage; corrections are annotations, never rewrites.
- A closed unit-kind vocabulary (money, price-delta, quantity, value-factor, r-multiple,
  rate(money-per-r), count, dimensionless-ratio, duration, instant); unit-kind additions are
  spine amendments only.
- Exact time and calendars: int64 UTC nanoseconds; CivilDate vs TradingDate as distinct types;
  Duration and Interval; WriterId as a first-class noun; wall vs monotonic clock kinds
  type-separated; clock access as an injected protocol seam (real clock live, data-driven clock
  in replay).
- Three distinct named calendar concepts kept separate: market-hours calendar, day-boundary
  calendar, and news calendar.
- Market nouns and identity: instrument identity is (venue, venue's own opaque symbol);
  operator-minted opaque VenueId; Venue and Account as distinct nouns (records owned by
  registry); Account carries exactly one role from `live | demo | paper-validation |
  paper-benched | prop-firm`; series vocabulary (Bar, Tick/Quote, BarSpec) defined here;
  Position and Order anchored as shared nouns with a venue-position vs virtual-(Book)-position
  split.
- Typed refusal: seven categories (invalid input, unsupported capability, unavailable
  dependency, stale evidence, policy rejection, transient venue failure, storage failure);
  every public operation succeeds or returns one.
- Canonical identity and versioning: the single fp1 fingerprint implementation; two version
  ladders (SemVer for code; integer contract-format versions for artifacts); the result label
  whose parts (producer identity, evidence class, world, input fingerprints, evidence time
  range) are identity.
- Secret references: SecretRef/SecretValue value types that never render their value and never
  enter fingerprints.
- Composition-root sink protocols (ObservationSink, JournalSink, RecordSink, SecretStore) as
  definitions-only seams.

**Exclusions / never.** Never runs a broker session, event loop, backtest, download job,
scheduler, trading node, product UI, or orchestration. Takes zero outside dependencies
(stdlib-only). Spawns no threads/background work; no async in its pure surface. Assumes no
Forex/cTrader/scalping/single-environment in public contracts. Does not own records/lifecycle
of the shared nouns it defines (registry does).

**Deferred.** `world = simulated` reserved but unusable in V1 (governed until the backtesting
sitting). Per-kind bar-aggregation rule details deferred to documentation time.

**Dependencies.** Depends on nothing. Every other package depends inward on it.

---

## COMP-QMF-DATA — `docs/components/qmf-data.md`

**Purpose.** The public data-policy and API library that preserves source evidence, governs
reproducible research access, and emits durable journal evidence. Owns seven room-roles, each
per world.

**Capabilities (candidate FR groups).**
- Seven room-roles, each instantiated per world: ingest door, immutable raw archive, processed,
  journal, split-governed research door, backup, and the registry room. Only raw archive and
  journal are evidence-bearing; processed/analytics views are rebuildable.
- Worlds: `live` (real venue clocks/quotes; paper and demo runs are world=live carrying money-
  reality via account role), `replay` (injected clock over recorded history), `simulated`
  (reserved-unusable in V1). Cross-world reads are policy-rejection refusals; world isolation is
  by storage separation.
- Bitemporal fact law: every external fact carries event-time, known-at, source, revision;
  corrections appended (annotations referencing fp1), never overwritten. `source` is a
  provenance noun orthogonal to VenueId (a provider only read is a source; one traded at is a
  venue).
- Retention: keep-raw-forever; time-series partitioned by source/instrument/time-window;
  evidence-bearing vs rebuildable distinction; never delete any artifact a result label cites.
- Bar aggregation as a fingerprinted derivation living in the processed room with lineage;
  venue-native bars ungoverned until the venue daily boundary is measured and minted.
- Research access and the seal: CT-12 dataset-split manifests (fingerprinted, time-ordered,
  non-overlapping, one calendar identity in-band); default train/validation/sealed-test split;
  purge and embargo widths as required manifest fields; knowledge-time partitioning; the newest
  ~12-month window sealed as a no-peek lock (not retention), enforced now at every read boundary
  including restored backups, with exactly one logged final look.
- Journal: N append-only per-writer streams; seven event types (decision, order, fill, risk
  transition, promotion, data quality, control action); the `decision` event's closed `outcome`
  field (authorized | refused-by-door | suppressed); treasury boundary events map onto
  risk-transition.
- Entity-journal projections: Book/BMS/per-bot journals ("the operator's logbook") as declared
  read-time projections over writer-scoped streams, selected by entity identity — one recorded
  set, many views. Paper and live separated by construction (role-scoped namespaces). The legacy
  five Records streams (veto_ledger, trade_journal, book_journal, ksa_audit_log,
  correlation_ledger) survive as projection names only.
- Backup requirement: nightly, encrypted, versioned, off-machine, with automated sample-restore
  tests and periodic full-restore rehearsal (primitives here; schedule application/ops-owned).
- Acquisition seam: defines source contracts, normalization, validation, idempotent intake keyed
  on (source, source-native id, revision); supports first-install historical load; keeps bid/ask
  preserved and disagreements visible via corroborates/disagrees-with edges.
- QMB consumer support: QMB data commands are thin fronts over these contracts; every ingested
  window carries a license tag; store-persisted fabricated data is store-tainted (world=simulated).

**Exclusions / never.** Never defines registration/causality/promotion/trading rules; never
selects a store engine/format/provider/encryption without ratification; never erases raw
evidence; never exposes the sealed holdout via default research or reads across worlds; never
validates trading edge with synthetic data; never schedules/supervises acquisition or backup;
never becomes a backtester, event bus, trading node, MIS, or product UI. Depends only on core
and its store seam.

**Deferred.** Look-ahead/causality registration gate (GAP-0016) and attempt counter (GAP-0017)
deferred to the backtesting sitting; annotation read-resolution (inline correction folding)
deferred; numeric RPO/RTO/retention/verification cadence and encryption key custody named at
the node/ops sitting; per-kind bar-aggregation details deferred.

**Dependencies.** Depends on COMP-QMF-CORE and COMP-QMF-DATA-STORE. The single ratified
inter-library edge into the data family is `qmf-registry → qmf-data`.

---

## COMP-QMF-DATA-STORE — `docs/components/qmf-data-store.md`

**Purpose.** The dependency-free data-layer seam that physically persists the seven room-roles
behind QMF-owned contracts (CT-09, CT-11, CT-13, CT-26) without owning their business meaning.

**Capabilities (candidate FR groups).**
- Persist registry identities/lineage (registry room), immutable raw evidence and rebuildable
  processed data, durable journal streams; present room contents to the backup primitive.
- Swappable store engines behind owned contracts — Parquet (columnar time-series), DuckDB (local
  analytics), SQLite (transactional metadata), JSONL (append streams) — with no database server.
- Identity is fp1; byte-identical idempotent re-write accepted silently, true collision refused
  and alarmed; append-only with one-writer-per-stream and unlimited readers; gapless sequence
  per (writer, boot-epoch).
- Persist graph-shaped registry history without a graph database (per-kind records + append-only
  typed edge records; rebuildable local indexes).
- Migrations: preflight → backup-first → dry-run → migrate → verify; never in-place mutation of
  the only copy; every artifact stamps its contract format version.
- Translate store-library exceptions into `storage failure` typed refusals at the boundary.

**Exclusions / never.** Never defines registration/causality/split/holdout/journal-event/
promotion/notification/recovery-orchestration/trading rules; never requires a graph database;
never adopts an engine/format outside the ratified set without ratification; never overwrites raw
evidence or immutable lineage; never reads across worlds or persists world=simulated into
governed evidence; depends on no component; never schedules acquisition/backup.

**Deferred.** Journal trimming, partition, and compaction thresholds set only after measured
volume (no ratified numeric value).

**Dependencies.** Dependency-free. Reached by qmf-data (CT-11), qmf-registry (CT-09/CT-13), and
qmf-data-backup (CT-26).

---

## COMP-QMF-DATA-BACKUP — `docs/components/qmf-data-backup.md`

**Purpose.** Provides QMF's backup, restore, and verify primitives — encrypted, versioned copies
carried off-machine from the store to object storage (CT-14/CT-26).

**Capabilities (candidate FR groups).**
- Receive per-room-role, per-world store input; produce encrypted versioned off-machine copies;
  back up every room-role including the registry room under one retention/backup/migration law.
- Verification as a first-class primitive: automated sample-restore tests plus periodic
  full-restore rehearsal.
- Preserve int64 UTC nanosecond timestamps verbatim across the round-trip; enforce the 12-month
  seal on restored reads exactly as a live read.
- Topology: trading-node VPS records and syncs down; workstation holds the working archive;
  bucket catches nightly copies.

**Exclusions / never.** Never mutates the only copy (each copy is a new version; migrations
back up first); never reads across worlds or restores simulated into governed evidence; never
embeds credentials in evidence; never deletes the only local raw evidence copy; never selects
provider/key-layout/key-custody/numeric RPO-RTO-retention; never owns the schedule or a runtime;
never defines retention policy.

**Deferred.** Numeric RPO/RTO/retention depth, verification cadence, object-key layout,
encryption key custody, and the crypto dependency named at the node/ops sitting.

**Dependencies.** Depends on COMP-QMF-DATA-STORE and COMP-OBJECT-STORAGE.

---

## COMP-QMF-DATA-INGEST — `docs/components/qmf-data-ingest.md`

**Purpose.** The middleware seam that owns and calls the CT-15 external-source port, translating
external historical-tick and news-calendar evidence into source-identified CT-10 observation
values for the data-owned boundary.

**Capabilities (candidate FR groups).**
- Own and call the CT-15 external-provider request/response port; resolve incoming instruments
  through CT-03; translate adapter failures through typed refusals.
- Validate, normalize, and submit CT-10 producer observation values; idempotent intake keyed on
  (source, source-native id, revision).
- Store foreign timestamps and foreign money verbatim with declared zone/scale; keep tick sources
  separately identified with bid/ask preserved and source timestamps kept; keep disagreements
  visible via corroborates/disagrees-with edges.
- Support bounded, idempotent calls used by first-install historical acquisition.
- Serve as caller for active providers Dukascopy (historical ticks) and calendar-feed
  (news calendar). cTrader is an intended future provider (venue market data reaches the same
  CT-10 boundary via the CT-15 intake path).

**Exclusions / never.** Never operates a scheduler/daemon/supervisor/retry loop/operator UI;
never owns the standalone news-calendar recorder application; never invents provider schemas,
rate limits, or legal-retention rights; never merges disagreeing sources without lineage;
never conflates a read-only source with a tradeable VenueId; never mutates data policy; never
persists raw evidence around CT-10/CT-11.

**Deferred.** News-calendar legal archiving posture an open operator item; rate/retry/pacing
constants are node values under do-not-default.

**Dependencies.** Depends on COMP-QMF-CORE, COMP-QMF-DATA, COMP-DUKASCOPY, COMP-CALENDAR-FEED.
No dependency on cTrader (forward broker capture waits for the broker application/connection).

---

## COMP-QMF-INDICATORS — `docs/components/qmf-indicators.md`

**Purpose.** The two-mode indicator library: one contract (CT-16), batch and streaming
conformant modes, consumer-blind across bots/structure/MIS/backtesting, so research and the live
path compute the same numbers by construction.

**Capabilities (candidate FR groups).**
- One CT-16 indicator contract with batch and streaming modes bound by an equality law.
- A configured indicator's identity is its entire declared configuration (formula id, format
  version, exact-rational parameters, input set, BarSpec, calendar requirements, alignment/
  missing-value policies, warm-up, output schema, supported modes, arithmetic-reference config);
  that fp1 is the only dedup key.
- Canonical arithmetic: wrap a pinned reference (TA-Lib) where it implements a formula; own
  canonical arithmetic where it does not (volume-weighted, session-anchored, QMX-original);
  output-changing upgrades mint a per-configured-indicator format version with before/after
  evidence.
- Light-vs-heavy classification per configuration under proven benchmark bounds; heavy runs off
  the trading path, computed once and fanned out; heavy on the synchronous path is an
  unsupported-capability refusal.
- Presence-mapped, index-aligned, full-length outputs; every sample carries a knowable-at
  instant; provisional samples never enter governed evidence; as-of alignment only; market-closed
  positions are `absent_by_schedule`, never gaps.
- The escape hatch: custom indicators always authorable as plain Python outside governed
  evidence; a working experiment graduates as a CT-16 extension (separate versioned package,
  explicit registration, lineage edge back to the originating research artifact).

**Exclusions / never.** Never re-implements arithmetic the reference or another governed producer
provides; never exposes vendor objects across CT-16; never defines the series vocabulary or
performs bar aggregation; never descales/re-enters the money path except through the two named
core boundaries; never runs scheduling/MIS wiring/trading-loop behavior; never ships a global
instance registry; never names a trading school in any rule or vocabulary.

**Deferred.** None called out as a hard gap; escape-hatch/extension mechanics are the intended
route for concepts not yet articulable.

**Dependencies.** Depends only on COMP-QMF-CORE (default-deny). CT-10 source observations and
typed configuration inputs reach it through the composition root, creating no edge.

---

## COMP-QMF-STRUCTURE — `docs/components/qmf-structure.md`

**Purpose.** The QMX-owned library for causal chart-object families (point, level, zone, span,
distribution, graph — a type of chart object, never a strategy/bot/Book). Objects minted once at
observation, evolving only through append-only records, carrying knowledge time and evidence
class as identity so repainted or look-ahead structure can never enter evidence.

**Capabilities (candidate FR groups).**
- Governed families whose confirmation rule states "confirmed the moment X happens" with X
  knowable then; objects minted at observation carrying anchor span and observed-at.
- The emission invariant (anchor.start ≤ anchor.end ≤ observed-at ≤ confirmed-at ≤
  invalidated-at) checked in-component as an interim look-ahead guard.
- Evidence class (confirmed/unconfirmed/provisional) as identity; confirmed reads refuse
  unconfirmed rows rather than filtering silently; unconfirmed links to confirmed via
  confirmed-as edges; confirmation delay feeds split purge/embargo widths.
- Lifecycle, interaction, and comparison records as separate append-only records/edges; "still
  valid at T" is a read-time fold; invalidation never cascades automatically; a refit is a new
  artifact with a supersedes edge.
- Consume indicator results, structure objects, and calendar windows as declared composite
  children; the routing test separating CT-16 (a value per evaluation instant) from CT-17 (a
  discrete object with a birth and a lifetime).
- The escape hatch: any concept a family cannot yet state precisely stays usable in plain Python
  outside governed evidence; operator-authored families are first-class peers to seed candidates;
  family authoring via the extension shape is the primary use case.

**Exclusions / never.** Never mutates a minted object; never classifies anchor span/observed-at/
lifecycle instants as display-only; never admits a family with an imprecise confirmation rule;
never names a trading school; never privileges seed families; never cascades invalidation; never
stamps records itself (the composition root holds the WriterId); never re-implements governed
arithmetic; never emits trading-entry/Bot/Book/exit/risk policy.

**Deferred.** Look-ahead/causality registration gate + CT-08 evidence (GAP-0016) deferred to the
backtesting sitting; the in-component emission invariant is the interim guard.

**Dependencies.** Depends only on COMP-QMF-CORE (default-deny in V1). Registration/lineage/
evidence flow through the composition root.

---

## COMP-QMF-CALENDAR-FOREX — `docs/components/qmf-calendar-forex.md`

**Purpose.** The first market-hours calendar extension: a separate versioned package implementing
the CT-02 calendar-provider protocol for foreign-exchange trading hours; supplies nothing else.
Lives outside the seven-package roster on its own SemVer ladder.

**Capabilities (candidate FR groups).**
- Implement the CT-02 calendar-provider protocol for forex: the accounting rollover (which
  trading date an instant belongs to) at 17:00 America/New_York, and a session schedule
  (weekend gaps and holidays in scope).
- Expose its calendar rule-set identity and pinned tzdata version so both enter downstream
  fingerprints; pin exactly one tzdata version and verify the resolved tzdb at import (refuse
  `unavailable dependency` on mismatch).
- Version independently on its own SemVer ladder; a tzdata pin change is at least a minor bump.

**Exclusions / never.** Never defines a shared noun (all consumed from core); never acts as a
day-boundary or news calendar; never derives a trading date by formatting an instant; never
attests a tzdb it did not resolve; never joins roster lockstep; never ships inside the `qmf.*`
roster namespace.

**Deferred.** Swap-Wednesday dropped from V1 (settlement machinery deferred; operator's accounts
are swap-free). The rollover is QMF's accounting rule, independent of any venue's measured
per-broker daily boundary.

**Dependencies.** Depends only on COMP-QMF-CORE; injected by the application composition root.

---

## COMP-QMF-REGISTRY — `docs/components/qmf-registry.md`

**Purpose.** The identity and lineage library for versioned QMF artifacts: registers each
artifact as a per-kind versioned record whose stable id derives from its fp1, and records lineage
as append-only typed edges — no universal card, no database server.

**Capabilities (candidate FR groups).**
- Per-kind versioned records (each kind its own contract, sharing a tiny common header) via
  CT-06; kinds addable, never redefined.
- Lineage as append-only typed edge records referencing fingerprints (CT-07); V1 edge types
  include supersedes (pinned linear), promoted-from, occurrence-of, corroborates, disagrees-with,
  the lifecycle edges (confirmed-as, confirmation, invalidation, interaction), and the risk-gate
  edges (continues-performance, carries-ledger, enacts, branches-from). `branches-from` supports
  the git-logic version graph (multiple heads; "current" a separate dated pointer).
- Promotion: a promotion-occurrence card kind with a human-only signer, a signed immutable record,
  and a mandatory plain-words summary declared an identity field; promotion into the live zone is
  human-controlled. V1 signing is the operator's recorded approval attesting the card's fp1.
- The nine risk per-kind record contracts (Book definition CT-22, BMS definition CT-27, Book
  binding CT-28, binding transition CT-24, exit record CT-29, control action CT-30, control window
  CT-31, performance result CT-32, instrument currency-exposure), plus instrument_class and the
  treasury boundary-event kind; the four structure-lifecycle kinds; the two Bot-domain kinds
  (Bot definition CT-33, confluence CT-34, authored via QML) and the strategy-family metadata kind.
- Multiplicity law: no bot-vocabulary layer hardcodes exactly-one; composites are own registered
  artifacts with lineage to children; Bot identity is content, its Book binding a separate dated
  record.
- Persist records and lineage through qmf-data's append-store into the per-world registry room;
  fp1-keyed storage (idempotent re-write silent, true collision refused/alarmed).
- QMB delivery: registry state reaches QMB machines as immutable fingerprinted as-of sets over a
  passive file-sync hub; one library-owned registry-read port serves both config compiler and
  CLI autocomplete.

**Exclusions / never.** Never requires a universal card or any database server; never mints an id/
key on a timestamp; never places registry business rules in the data layer; never imported by a
consuming library (default-deny — the application wires registration at the composition root);
never hardcodes "exactly one"; never enforces a look-ahead gate or attempt counter in V1; never
promotes into live without a human decision.

**Deferred.** Look-ahead causality registration gate (GAP-0016) and attempt counter (GAP-0017)
deferred to the backtesting sitting (CT-08 reserved, schema deferred; attempt scope/budget/reset
unresolved). QMB delivers look-ahead prevention structurally, but the proving gate remains
deferred.

**Dependencies.** Depends on COMP-QMF-CORE and COMP-QMF-DATA (the single ratified
`qmf-registry → qmf-data` edge). CT-33/CT-34 kinds owned here but authored via COMP-QML.

---

## COMP-QMF-RISK — `docs/components/qmf-risk.md`

**Purpose.** The ratified risk module: defines the Book, BMS, binding, admission, exit, control,
window, and performance contracts (CT-22..CT-25, CT-27..CT-32) on core nouns, so a Book's
meaning, a binding's identity, R, and every risk record live inside the governed value system.
Not an execution engine.

**Capabilities (candidate FR groups).**
- The binding chain and identity trinity: the constitutional authority order "bots trade; books
  control bots; BMS accounts for and constrains books; nothing above a bot touches the market."
  One BMS per account serving many Books; a Book binds exactly one BMS; a Bot binds exactly one
  Book. Book version (template content), Book instance (deployment record), binding epoch. Risk
  domain is the binding tuple (BookInstanceId, BmsInstanceId, VenueId, AccountId, world).
- Templates as configuration artifacts: declared variables each carrying unit, exact-rational/
  scaled-integer value, a `ui-editable | uneditable` flag, and an `admission_impact ∈ resign |
  relint | none`. Git-logic versioning (append-only branches-from graph; UI edits mint a new
  version). Declared sections: charter, footprint_requirements, money_rules, admission_bar,
  leash_grammar, capacity_and_sweep, exit_policy, control_policy, protection_windows, paper.
- Three-layer admission (no trial period/probation/paper-performance gate): Layer 1 linters at
  registration; Layer 2 technical shakedown on a demo/paper binding (proves machinery, not edge);
  Layer 3 one operator signature on one assembled page. The admission_bar as named requirements,
  each pass/fail on its own terms (no composite score); blank blocks live money; no paper role may
  gate live money.
- Exit ownership and whole-trade attribution: the Book owns exit policy for a position's life; a
  Bot proposes exits through the CT-23 door; exit intents risk-monotonic (V1 kinds close_full and
  tighten_protective_stop; close_partial unsupported); requested_r is Book-resolved; the protective
  stop is Book-owned and moves only risk-non-increasing; exit method declared as ExitLogicRef per
  family; typed close reasons; whole-trade result in R credits the opening Bot regardless of who
  closed.
- amend_protection and the move-to-breakeven ratchet (one-directional, risk-reducing, per-Book).
- Paper mode as a Book-level mode (LIVE|PAPER), a dated change of the execution binding; paper is a
  standing evidence state, not a waiting room; one active paper-routing target per live binding;
  paper money is frozen evidence, a reset mints a new operator-signed paper epoch; decay judged on
  decision quality in R, never realized cash.
- Control actions: the kill switch (global black-swan authority, stops all new trading, human
  de-escalation) vs the kill line (per-Book capital floor, auto-flattens and stands the Book down);
  the exit-preservation invariant (no control ever blocks a risk-reducing act); CT-30 typed action
  kinds (suspend_new, drain, flatten, resume); assigned flatten authority; standing intent
  (journaled before dispatch, restart-proof, re-decided not retried); veto accounting symmetric to
  suppression accounting.
- Same-tick priority: one arbitration point per (VenueId, account) stream; a two-tier deterministic
  order; BMS-declared rank table; collapse and conflict rules.
- Protection windows: one CT-31 contract for every no-trade band; kinds news, daily_dead_zone,
  session_handover_buffer; calendar-derived; blocks new entries only; instrument scope via dated
  currency-exposure records (never symbol-parsed); widen-never-shrink; fail-closed.
- SQS (Spread Quality Sensor): a CT-16 configured producer; V1 score = historical average spread
  for a session window ÷ current live spread; hard-block threshold, hysteresis band, outlier guard,
  conservative sentinel; the sensor computes, the transport carries, the Book door decides — SQS
  never sizes/authorizes/blocks itself.
- R, numeraire, and the dimensional law: R as three typed faces (original_risk_distance,
  original_risk_amount, r_multiple), frozen at admission; USD numeraire system-wide in V1 (Book
  declares accounting_currency); the closed unit-kind vocabulary with a symbolic checker; margin
  decided-deferred (V1 does not size by margin); the sizing-ladder replacement shape carrying units
  only; the "B split" of bench threshold vs seat loss-run allowance.
- Bench counter, exit records, and performance evidence: exit record CT-29 (one per virtual-position
  close); the bench counts qualifying loss exits (realized_r ≤ −q) as a read-time fold; performance
  result CT-32 serving admission-bar evidence and the analyst report; alpha decay shipped as
  evidence primitives only (no score/rating/tier), the mathematics deferred.
- QMB consumer: QMB is the designated CT-32 producer at the replay composition root; a QMB run mints
  a world=replay binding, incomparable to any live binding; R stays single-authored by the Book.

**Exclusions / never.** Never runs an application/trading-node loop or evaluates the sizing ladder
at runtime; never chooses which severity effect a kill-switch level fires; never holds the same-tick
rank-table values; never invents a risk number (all configurable, UI-editable, evidence-backed);
never sizes by margin in V1; never expresses a partial/fractional exit; never blocks a risk-reducing
act; never lets a sensor acquire trade authority; never promotes into live without a human signature;
never reads a currency out of a symbol; never writes a physical store or adds an inter-library edge;
never revives dead machinery (parallel-Bot paper twins, stacked BMS, FORM-0006 live, blackout
simulator, DPR/PRS/auction/legacy slots).

**Deferred.** Alpha-decay mathematics and admission-bar threshold values (GAP-0048); look-ahead
registration and attempt counter (GAP-0016/0017); node runtime material (order path, protection
funnel, severity policy values, door wiring, ledger evaluation) out of scope (tracker note). Every
surfaced number is a configurable UI-editable variable, non-authoritative, with no ratified spine
value.

**Dependencies.** Imports only COMP-QMF-CORE; nothing imports it. Risk records reach the registry
and qmf-data through the composition root. Reads SQS via CT-16 (indicators) and CT-18 venue
capability (venue) at bind time. Consumed by COMP-QMB and COMP-QML (both sides of the CT-23 door).

---

## COMP-QMF-VENUE — `docs/components/qmf-venue.md`

**Purpose.** The ratified neutral venue port: one port exposing four contracts — CT-18 (capability),
CT-19 (command), CT-20 (event and reconciliation), CT-21 (secret and session) — defined on core
nouns, implemented by per-venue adapters, wired by the composition root. First adapter targets the
cTrader Open API. An edge module.

**Capabilities (candidate FR groups).**
- One neutral venue-agnostic port, four contracts; a later crypto or stock adapter slots in by
  declaring a different capability record through the same port.
- Connection manager: sole owner of venue sessions and sole in-memory holder of secret values for a
  session's lifetime; holds the WriterId (machine, adapter role, VenueId, account).
- Injected-sink wiring: the core-defined ObservationSink/JournalSink/RecordSink/SecretStore; every
  sink returns success or a typed refusal so the writer sees every persistence failure (a storage
  failure blocks the command pipe).
- Secret lifecycle: components handle references not values; a SecretValue renders only its
  reference id; values injected at the composition root; one refresher per credential; store-before-
  discard on rotation; a missing/expired/rejected credential is an unavailable-dependency refusal.
- Command surface and the uncertainty law: exactly five command kinds (place_order, cancel_order,
  close_position, close_all, amend_protection); the four-outcome law (accepted-by-venue,
  rejected-by-venue, denied-locally, UNKNOWN); UNKNOWN as an explicit observation that blocks new
  commands on the stream until an explicit resolve_unknown call; no retry/assume/flatten/invent on
  UNKNOWN; compound (fan-out) commands; recording precedes interpretation (order state as a
  read-time fold); reconciliation with verdict vocabulary reconciled/drift/unknown/out-of-lookback.
- Capability discovery: two artifacts wired in fixed order — the static, credential-free capability
  declaration and the per-(VenueId, account) venue-observation profile produced post-connect by a
  verify-or-refuse verification suite; a measured-at-connection capability is unavailable until its
  profile exists.
- Market data: ticks, bars, depth, gap-replay backfill, historical paging enter as CT-10 source
  observations through the CT-15 intake path (the venue is also a source); no silent sibling-feed
  failover (fail closed until the same feed gap-replays); raw depth recorded verbatim.
- The measured venue daily boundary minted as a venue-scoped market-hours calendar identity, giving
  venue-native bars a legal BarSpec anchor.
- The venue adapter boundary is a named money-path conversion boundary (foreign float to scaled
  integer at receipt, raw float retained as provenance; venue-converted money legal as settlement
  evidence under converted_by=venue).
- Six named live-path latency rungs (no numeric budgets until measured).

**Exclusions / never.** Never decides whether a trade is permitted, sizes a position, or owns Book/
BMS/exit/portfolio policy; never runs an application/trading-node loop; never retries a command,
assumes an outcome, initiates a flatten, invents a terminal state, or clears its own UNKNOWN block;
never synthesizes a venue observation; never holds a policy constant (retry/pool/deadline/throttle
are node values under do-not-default); never constructs a second venue client; never writes a store
directly; never absorbs trading-node runtime material. The adapter never initiates a flatten.

**Deferred.** Submission deadline and retry/pool/throttle/health constants are node values;
trading-node runtime material (order path, protection funnel, startup semantics, flatten-authority,
severity policy) out of QMF scope (tracker note); numeric latency budgets deferred until measured.

**Dependencies.** Imports only COMP-QMF-CORE; nothing imports it. Produces market data into
qmf-data via CT-15/CT-10; emits journal evidence through injected sinks. First adapter is
COMP-CTRADER. Consumed by qmf-risk (CT-18) at bind time.

---

## COMP-QMB — `docs/components/qmb.md`

**Purpose.** The QMX experimentation/backtesting product: one pure library plus the `qmb` CLI in a
single wheel, fronted by thin doors, that runs a Bot against a Book and BMS's own rules in
world=replay and publishes the result as a CT-32 performance-result. An application-layer product
built ON QMF, never a roster package. Realizes the glossary's reserved "future backtesting library"
slot (the Simulator UI stays a separate deferred product that will consume QMB).

**Capabilities (candidate FR groups).**
- One library, thin doors: every capability exists once as a pure function; the CLI is the product
  face and ships first; a Python API door for the UI backend and research; an MCP door after CLI v1
  (localhost-bound, never over HTTP). Door parity is a tier-2 contract test.
- The event-slice run loop with an injected frontier clock (the core Clock protocol); a pinned
  per-slice sub-phase order; backtest/replay/live differ only by clock and adapters (one loop, never
  forked); in-loop warm-up with trading locked.
- The config compiler: exactly one fully-resolved, read-only, fingerprinted run-config per run from
  fixed precedence layers (invocation flags > run spec > BMS fragment > Book fragment > workspace
  defaults); Book and BMS fragments in disjoint key namespaces (BMS outranks Book on any overlap);
  fragments are derived artifacts with lineage back to CT-22/CT-27; one world=replay binding per run;
  starting_capital a mandatory run-spec seed.
- Pure run + impure orchestrator + resource governor: run() is pure (returns the artifact and a
  self-assessment, writes no log/ledger); the orchestrator owns log/ledger sinks and appends exactly
  one WriterId-scoped ledger line per run; process-per-run; parallelism bounded by min(cpu, memory)
  with enqueue-on-full (no silent oversubscription); per-run time/memory limits; no Ray/Docker/daemon.
- Reader-derived verdicts and run roles: ledger stores raw unit-kinded measures and the Book-bar
  fingerprint, never a stored pass/fail; the bar verdict is a read-time fold producing per-requirement
  outcomes; run roles confirmation | trial | replicate | aborted; a replay-world verdict never gates
  live money; QMB's ledger + CT-32 artifacts are the designated evidence source for the admission bar
  and the promotion-card causality slot.
- Execution ports (fidelity and calibration-not-invention): separate fill, slippage, cost, and
  financing ports per run-config, calibrated from QMX's own recorded evidence per broker; fidelity
  identity is adapter-id + composition-version + taint; until GAP-0048, all fills carry an optimistic
  taint (cannot spend split budget or claim edge).
- Provenance-derived worlds and claim classes: world derived from input-data provenance, never
  caller-declared; store-persisted fabricated data is world=simulated (policy-rejection for governed
  evidence); procedure-ephemeral perturbation stays replay with a robustness-only claim class.
- Optimize: a declared typed parameter space; a pure generation-stepped sampler reading trial history
  from the ledger view (default TPE-class adapter pinned); every trial a first-class run;
  anti-overfit sensitivity analysis in the sweep artifact.
- The research surface (the library's own pure functions); controlled-room hosts for sealed/governed
  evidence.
- One canonical result artifact that IS a CT-32 performance-result, with declared chart-series and
  trade-event-reference extensions; run trading events as CT-13 journal events in the run's world;
  per-run logs are operational only, never evidence; re-running a run id reproduces the fingerprint.
- Data commands (download, verify, catalog, generate) as thin fronts over qmf-data contracts;
  download-once under the user's own provider relationship (Dukascopy primary); runs never fetch from
  providers; every ingested window carries a license tag.
- Stream sets and permutation batches; versioned uv/pip-installable distribution; the validation
  ladder (backtest, optimize, Monte Carlo, rule-significance test, walk-forward) as versioned library
  functions; registry delivery via immutable as-of sets over a passive hub.
- QML-increment coordination: two config-compiler extensions (an assignment_is_canonical stamp and
  producer-template resolution), a canonical-assignment fold qualifier, and the completed parameter-
  space schema (one schema authoritative in the CT-33 Bot definition).

**Exclusions / never.** Never benches/promotes/binds (publishes only); never stores a frozen pass/fail
verdict or gates live money on a replay-world verdict; never mints a second data or registry layer;
never revives the dead central backtesting service; never forks/adopts donor engine code; never
redefines risk/Book/BMS/binding/R/exit vocabulary; never calls itself an engine/kernel or a part a
plugin; never says "snapshot" for registry state; never accepts a caller-declared world; never claims
edge from an optimistic/synthetic/robustness-only run; never lets the library write a log/ledger line
or spawn a thread; never stacks the MCP door over HTTP or ships it before CLI v1; never adds an edge to
COMP-QMF-VENUE (live adapters are trading-node territory).

**Deferred.** Fidelity taxonomy values, forex fill/slippage/financing calibration content, parity
contracts, simulated-time typing (GAP-0048); SR*/search-quality thresholds and the look-ahead
registration gate (GAP-0049, GAP-0016/0017); pass batteries; MCP door details; live wiring; UI
rendering; cloud-burst compute; hub deployment detail; staged-funnel triage; the locked validation
window as a third split; prop-firm Books socketed upstream. The Dukascopy licensing question ruled
closed under the personal-use posture.

**Dependencies.** Depends on the six backend QMF components (core, registry, data, indicators,
structure, risk) in workspace lockstep; no edge to venue. Consumes and hosts COMP-QML conformant bots
through the QL-7 runtime-protocol adapter.

---

## COMP-QML — `docs/components/qml.md`

**Purpose.** The QMX bot-authoring library: one uv-installable distribution (`import qml`), an
application-layer product built ON QMF contracts exactly as QMB is; never a roster package, framework,
engine, or cross-component contract layer. Whole surface is three thin things: author-side types/
helpers producing the CT-33 Bot definition and CT-34 confluence; the bot runtime protocol; and the
conformance gate. Closes the reserved QML slot (GAP-0047).

**Capabilities (candidate FR groups).**
- Author the two Bot-domain registry artifacts (CT-33 Bot definition, CT-34 confluence) on core nouns;
  a governed bot is exactly two artifacts — a declaration (CT-33) and logic (plain Python conforming
  to the runtime protocol, its source-manifest fingerprint entering identity). Plain Python stays
  first-class forever (an unregistered bot needs zero QML imports).
- The CT-33 Bot definition content: exactly one strategy-family id; a confluence set; the one
  authoritative declared parameter space (whose defaults form the canonical assignment); the footprint
  (containing the stream set); the permitted-intent declaration (entry always permitted; exit kinds a
  subset of CT-23, possibly empty); the logic reference. Git-logic versioning; canonical assignment
  only on governed seats; a tuned assignment mints a new Bot version.
- The footprint as the single canonical consumption manifest (stream set, required calendars, producer
  bindings — pinned fingerprint or a complete template minus space-bound values); the transitive-union
  completeness law; warm-up/embargo derived at resolution.
- The CT-34 confluence: one-or-more legs of any role mix over the closed-and-addable vocabulary
  level | trigger | confirmation | filter (filter the first addition); condition semantics live in
  logic in V1.
- The strategy family: an opaque operator-minted id plus a dated metadata record — a keying token with
  no authority (constraining is the Book's job).
- The bot runtime protocol (QML-owned, format-versioned): a conformant bot is a factory the host drives
  per evaluation instant, receiving only the declared footprint's evidence and returning zero-or-more
  CT-23 intents; the bot never sizes/touches venue commands/reads a clock/performs I-O/network/
  undeclared randomness; conformant logic is deterministic; bounded declared state with scoped
  snapshot/restore. The advisory stop proposal is bot-side; the declared full-loss price is
  Book-resolved (no Book module ever injected into bot logic).
- The conformance gate: Layer 1 declaration linter; Layer 2 sandboxed-execution conformance (QML owns
  the pure denial set, static AST/import scan, determinism harness, golden-slice generator, and verdict
  function; the host owns process spawning/isolation); the ticket — the Bot kind mints only for
  artifacts passing both layers, and that registration is what governed evidence and seats cite;
  conformance gates evidence citation and seats, never tunnel entry. The prediction linter (four pinned
  checks) fills the Book's admission Layer-1 slot.
- Author the CT-22 v2 and CT-23 v2 format-mint semantics (admission-bar +2 evidence fields, exit_policy
  catch-all, footprint_requirements shape; the advisory stop proposal as a new CT-23 entry field).

**Exclusions / never.** Never a roster package/framework/engine/kernel/contract layer; never mints a new
CT-* shared contract of its own; never imports qmf-venue; never spawns a thread/process or performs I-O
(pure library); never lets a bot size/touch venue commands/read a clock; never carries an exit_logic
field on the Bot definition or a second close-reason taxonomy; never gates on performance (conformance
is technical); never gates ungoverned bots' tunnel entry; never revives the .qml file format/Monaco
surface as a second language in V1, ArchetypeSpec's constraint powers, or max_acceptable_complexity_
score as a gate; never adds the admission-bar/footprint_requirements fields as a silent addition (only
through the CT-22 format mint); never mints an acronym expansion for QML.

**Deferred.** The declarative condition/predicate grammar (the .qml successor); Monaco-class editor/UI
authoring and agent-codegen lanes; agent mutation allowances; hardened OS-level sandbox confinement for
Layer 2 (node/platform sitting; V1 uses static scanning + capability starvation + process isolation);
admission-bar threshold values (GAP-0048/0049; interfaces only); the weights-artifact parameter kind;
complexity/quality measures; multi-bot ensemble/portfolio vocabulary; a bot-side qml CLI (V1 is
library-only, a non-blocking open operator question); seat-time runtime enforcement details.

**Dependencies.** Imports COMP-QMF-CORE, COMP-QMF-REGISTRY, and COMP-QMF-RISK (CT-23/CT-29 types) only;
never qmf-venue. Builds before the trading node and may build alongside QMB. Hosted first by QMB
(runtime-protocol adapter + sandbox runner at its composition root); the trading node hosts seats later.
CT-33/CT-34 kinds owned by qmf-registry, authored via QML.

---

## COMP-CTRADER — `docs/components/ctrader.md`

**Purpose.** The external cTrader Open API boundary the first Python venue adapter is designed against.
QMF owns the translation contracts around this system; QMF does not own cTrader behavior, availability,
schemas, accounts, credentials, or execution outcomes.

**Capabilities / ratified facts (candidate FR / constraint groups).**
- cTrader is a platform, not a broker: which broker fronts it is deployment configuration, never
  architecture (opaque VenueId/AccountId identity is sufficient); a broker's measured behaviors live in
  the venue-observation profile. IC Markets is operator intent, not a commitment.
- Protocol pinning: the Spotware openapi-proto-messages package pinned at its integer release tag
  (currently 91); only proto message definitions consumed (data, not code); the OpenApiPy SDK is
  reference-only (its Twisted reactor would impose a platform — zero Spotware code runs in QMX; the
  adapter owns its own transport).
- Documentation-grade venue facts (standing adapter obligations): per-field Unix-ms-UTC timestamps with
  named epoch exceptions; no server clock (mandatory receive-time recording); BID/ASK-selectable
  historical ticks; rate limits 50/s non-historical + 5/s historical per connection; hasMore-only paging
  with a one-week tick-span cap; three independent numeric scale systems (never unified); two
  broker-supplied non-UTC timezone axes; a 10-second heartbeat; gappy-by-design trendbars; swap-free
  accounts still pay a dated rollover commission.
- Demoted-and-measured-per-broker claims: the daily-bar boundary and the BID-derived trendbar basis are
  2013-forum-grade and never hardcoded — measured per broker at first connection, re-verified by a
  continuous monitor, stored as per-broker configuration; once verified, the boundary is minted as a
  venue-scoped market-hours calendar identity.
- Verify-or-refuse obligations for every undocumented behavior (spot-timestamp unit, spot coalescing,
  rate-window semantics, absent moneyDigits, pip formula, live-trendbar semantics, historical
  classification, per-period span caps).
- Protection-amendment mechanics (confirmed-primary, behind amend_protection): one-message absolute
  amend for open positions; own-message amend for pending orders; no dedicated response (confirmation on
  the ordinary execution-event surface); absolute protection NOT supported for MARKET orders
  (entry-relative is the placement path); undocumented native trailing (venue-delegated authority only);
  UNDOCUMENTED amend atomicity (single-sided is the only legal V1 path until verified); a guaranteed-stop
  class where the account offers one.
- Depth and connectivity: a Level-2 resting-liquidity book (recorded verbatim); no Level-3/time-and-sales
  tape; demo and live are separate hosts (two simultaneous connections).
- Secret and token lifecycle: references never values; ~30-day access token; never-expiring refresh token
  as the crown-jewel secret; cTID re-authorization as the invalidation anchor; a documented, tested
  compromise-recovery drill (demo credentials only).

**Exclusions / never.** Never described as QMF-owned/deployed; never assumed available or semantically
stable; never defines QMF risk policy; never makes an acknowledgement equal risk approval; never leaks
cTrader objects into core; never acts as an assigned CT-19 caller. Ratification of design is NOT
authorization to implement — a live/credential-bearing adapter is built only through the factory pipeline
against an operator-approved account.

**Deferred.** Concrete adapter implementation (factory pipeline); node runtime material (order path,
protection funnel, startup, flatten authority) out of scope (tracker note); do-not-default node constants
(submission deadline, retry/pool/health).

**Dependencies.** No QMF dependencies (external boundary). Supplies market data to COMP-QMF-DATA-INGEST
via CT-15; its four venue contracts (CT-18..CT-21) owned by COMP-QMF-VENUE.

---

## COMP-DUKASCOPY — `docs/components/dukascopy.md`

**Purpose.** The external historical tick-source boundary selected directionally for the first backfill
path. QMF owns the adapter and resulting evidence contracts; QMF does not own Dukascopy availability,
schema, licence, corrections, or coverage.

**Capabilities (candidate FR groups).**
- Supply a bounded historical source record to data-ingest through CT-15; every accepted observation
  retains its external source identity and is converted into CT-10.
- Download-once acquisition posture: the historical corpus pulled a single time under the user's own
  provider relationship into the immutable raw archive (QMX owns its stored source; runs never fetch from
  providers). A dukascopy-node-class downloader is a shape reference only (build-our-own; no donor code).
- Bid/ask preserved with source timestamps; disagreements with a later broker feed stay visible via
  corroborates/disagrees-with edges; a later broker feed is a separate source; idempotent
  (source, source-native id, revision) intake.

**Exclusions / never.** Never treated as QMF-owned; never assumed complete or legally retainable; never
replaces later broker-source identity; never silently merges disagreements; never schedules/supervises
QMF ingestion; never triggers a bulk corpus download during documentation or a factory feature pass.

**Deferred.** The concrete provider schema (symbol list, depth, per-symbol specifics) is documentation-
time detail. The Dukascopy licensing-gate question ruled closed under the personal-use posture (reopens
only if a future posture exceeds personal use); the per-window license-tag mechanism stays in force.

**Dependencies.** No QMF dependencies (external boundary). Supplies COMP-QMF-DATA-INGEST via CT-15;
consumed by COMP-QMB data commands.

---

## COMP-CALENDAR-FEED — `docs/components/calendar-feed.md`

**Purpose.** The external provider boundary consumed by the standalone news-calendar recorder. Supplies
external economic-event evidence. This is the news calendar — one of three distinct named calendar
concepts (never conflated with the market-hours calendar or the day-boundary calendar). Answers only
"what economic events happened, when, and how were they revised."

**Capabilities (candidate FR groups).**
- Supply provider-identified event records and revisions to data-ingest through CT-15; the recorder keeps
  the provider's native event identity and revisions through idempotent (source, source-native id,
  revision) intake; each revision a new artifact; corrections appended, never overwritten.
- Event evidence is written under the recorder's own WriterId; the risk-side control that maps this
  evidence to affected instruments is the CT-31 control-window mechanism (this feed defines no window and
  holds no permission).
- Event severity stored as the provider's impact labels verbatim (QMX mints no severity scale in V1).

**Exclusions / never.** Never described as QMF-owned; never defines risk policy or a news blackout by
itself (the blackout is CT-31's); never scheduled inside qmf-data; never assumed complete/timely/stable/
legally retainable; never erases prior revisions; never acts as a market-hours or day-boundary calendar;
never equated with SQS.

**Deferred.** Provider selection and the legal archiving/retention posture remain open operator items.
News blackout before/after widths are configurable UI-editable variables with no spine value (the ±15
minute news buffer is on record as withdrawn).

**Dependencies.** No QMF dependencies (external boundary). Supplies COMP-QMF-DATA-INGEST via CT-15; its
event evidence is consumed by the CT-31 control-window mechanism in COMP-QMF-RISK.

---

## COMP-OBJECT-STORAGE — `docs/components/object-storage.md`

**Purpose.** The external, replaceable destination for QMF's encrypted, versioned backup copies produced
by COMP-QMF-DATA-BACKUP through CT-14. The nightly, encrypted, versioned, off-machine backup design is
ratified; the bucket catches nightly copies while remaining outside QMF ownership.

**Capabilities (candidate FR groups).**
- Accept, retain, and return encrypted, versioned backup objects and provider acknowledgements through
  CT-14; hold copies of every room-role (including the registry room), per world, as opaque encrypted
  payloads.
- Every copy a distinct version (the provider never mutates an existing copy); int64 UTC nanosecond
  timestamps round-trip verbatim; the provider stays external and replaceable.

**Exclusions / never.** Never described as QMF-owned/deployed; never assumed durable merely because an
upload returned (durability established by QMF-side verification, not a byte-transfer acknowledgement);
never decides a backup/restore is valid; never receives secrets in QMF evidence; never silently deletes
evidence; never leaks provider-specific object/acknowledgement/encryption/credential details into QMF
core or data-policy contracts; never replaces the complete local raw evidence copy.

**Deferred.** Provider selection, object-key layout, credential and encryption key custody, the crypto
dependency, and the numeric RPO/RTO/retention depth/verification cadence are named at the node/ops
sitting; this boundary asserts none of them.

**Dependencies.** No QMF dependencies (external boundary). Receives from COMP-QMF-DATA-BACKUP via CT-14.
