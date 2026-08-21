---
id: GLOSSARY-QMF-V1
title: QMF V1 Glossary
type: glossary
status: ratified
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK]
decisions: [DEC-0001, DEC-0017, DEC-0019, DEC-0024, DEC-0028, DEC-0033, DEC-0035, DEC-0042, DEC-0045, DEC-0048, DEC-0055, DEC-0058, DEC-0059, DEC-0065, DEC-0066, DEC-0074, DEC-0076, DEC-0105, DEC-0106, DEC-0107, DEC-0108, DEC-0109, DEC-0110, DEC-0114, DEC-0115, DEC-0116, DEC-0117, DEC-0118, DEC-0119, DEC-0126, DEC-0128, DEC-0129, DEC-0130, DEC-0131, DEC-0132, DEC-0133, DEC-0134, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0139, DEC-0141, DEC-0142, DEC-0143, DEC-0144, DEC-0145, DEC-0146, DEC-0147, DEC-0148, DEC-0149, DEC-0150, DEC-0151, DEC-0152, DEC-0153, DEC-0154, DEC-0155, DEC-0157, DEC-0158, DEC-0159, DEC-0160, DEC-0161, DEC-0164, DEC-0165, DEC-0169, DEC-0171, DEC-0172, DEC-0173, DEC-0174, DEC-0175, DEC-0176, DEC-0177, DEC-0178, DEC-0179, DEC-0180, DEC-0181, DEC-0182, DEC-0183, DEC-0184, DEC-0185]
sources: [_docwork/ledger.yaml, _docwork/gaps.yaml, docs/registry/variables.yaml, docs/architecture/dependencies.yaml, docs/contracts/, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-21
stale_after: 30d
---

# QMF V1 Glossary

This glossary fixes names for the QMF V1 documentation (corpus signed off by the operator 2026-08-21). A definition containing `GAP(...)` is a boundary marker, not permission to choose the missing design.

## Canonical terms

### Account

A first-class qmf-core noun, distinct from Venue: the nouns Venue and Account are defined in qmf-core, and their records are owned by qmf-registry. One Venue may hold many Accounts, each carrying a role — live, demo, paper-validation, paper-benched, or prop-firm (DEC-0107) — and Books bind to Accounts through a BMS, not directly to Venues (DEC-0143). Live and demo are distinct `(VenueId, account)` command streams, so an outstanding UNKNOWN on one never gates the other (DEC-0149). The account role stays an identity field of the venue account-binding record (DEC-0136); it is deliberately absent from the risk-domain Book-binding tuple, where routing resolves per intent through the **execution target** — computed once at intent mint from (Book mode, seat state, active-control set) and entering the command record's identity (DEC-0143, DEC-0149). A demo or paper Account still carries `world = live` because the account role, not the world label, records money-reality, which keeps paper and demo runs comparable to live for alpha-decay sensing (see **world**). The risk-domain binding onto an Account is `(BookInstanceId, BmsInstanceId, VenueId, AccountId, world)`, and paper-mode transition semantics are ratified as a dated change of the Book-to-BMS execution binding (DEC-0143, DEC-0149).

### Acknowledgement mode

The CT-18-declared way a venue confirms each command kind's outcome, one of three values (`explicit-event | implicit-absence | none`). An outcome is never derived from absence alone: a `cancel_order` resolved by read-back is `accepted-by-venue` only if the read-back also shows no fill for that order at or after the cancel's submit stamp, and otherwise resolves `rejected-by-venue` (**superseded-by-fill**). Each adapter declares its acknowledgement mode per command kind; a consumer never assumes one. (DEC-0137)

### admission_bar

The Book's declared set of named requirements a candidate must meet — 'the Book sets the bar' — never an 'entrance exam' (that phrase is banned). Each requirement carries an opaque `measure_identity`, a mandatory unit, a comparison (`at-least | at-most | within-band`), a threshold as a discriminated union with a pinned tag set (a ruled exact rational, or an explicit not-yet-ruled tag carrying its gap reference — the key always present, so blankness is a declared value), and `evidence_requirements` (world, account role, minimum evidence window, required producer contract format versions). The set is canonically ordered by `measure_identity` with display ordinals separate, so two operators writing the same requirements in different order get the same Book fingerprint. Blank blocks live money: a bar holding any not-yet-ruled threshold registers and binds to non-live roles but is a policy rejection against a live account. No paper role may gate live money, and no composite score, rating, or weighted aggregate may express a bar (DEC-0146, DEC-0144).

### advisory stop proposal

The bot's OPTIONAL protective-stop proposal carried on a CT-23 `entry` intent — a proposed protective-stop price or PriceDelta bound, ADVISORY exactly as proposed_r is: it never sizes and never binds the Book. It lands on CT-23's entry intent as a new optional field through the CT-23 format version 2 mint (DEC-0182). The declared full-loss price stays mandatory at admission but is Book-resolved: derived AT THE BOOK DOOR by the Book executing its own per-family ExitLogicRef, consuming the advisory proposal and the intent's cited evidence, and stamped exactly as the Book resolves requested_r — a single execution site, with no Book module ever injected into bot logic (DEC-0177). By the 2026-08-21 operator veto round a Book MAY declare a per-family adopt-the-bot's-advisory-stop mode on its CT-22 ExitLogicRef — "adopt the bot's advisory stop proposal as-is, validated against the Book's risk rules" — so a bot that carries its own exit/stop methodology is honored rather than overridden; and no inbound-refusal posture exists for a bot-supplied full-loss price, since the advisory stop proposal is the bot's channel (DEC-0185). (DEC-0177, DEC-0182, DEC-0185)

### Anchor span

The frozen payload geometry of a structure object: start instant, end instant, and price bounds, fixed at observation and never revised. An anchor span is explicitly permitted to precede observed-at (an object may describe earlier bars once it becomes derivable) and is excluded from every causality test — causality is judged on observed-at and confirmed-at, never on where the object's geometry points. Anchor span is an identity field, never occurrence-classified. (DEC-0129)

### As-of set

An immutable, fingerprinted set of registry records and fragments delivered to a machine — identified by its `registry_as_of` instant plus a set fingerprint — over a passive file-sync hub, read through the one library-owned registry-read port with no door-side caches. The word "snapshot" is banned for registry state; say "as-of set". A sweep freezes one as-of at batch admission, so every run in the batch reads the same registry state, and the stale-evidence refusal severity is a configurable variable (DEC-0165).

### Attempt accounting

Immutable registry evidence that a governed registration or research attempt occurred. Target, scope, budget, and reset semantics remain `GAP(GAP-0017)`.

### Bar

An asset-neutral qmf-core shared noun for aggregated observations: OHLC plus its interval and its **BarSpec** (DEC-0126). It references an instrument by its ratified `(venue, venue's own symbol)` identity (DEC-0107), and a bar series is well-defined only via its BarSpec, with aggregation itself a fingerprinted qmf-data derivation. The venue-native price basis of provider bars is measured per broker at first connection under the verify-or-refuse suite and stored in the venue-observation profile, never hardcoded; venue-native bars gain a legal BarSpec anchor only once the measured daily boundary is minted as a venue-scoped market-hours calendar identity (DEC-0135, DEC-0138, DEC-0141).

### BarSpec

The qmf-core shared noun that replaces the bare word "timeframe" everywhere — bare "timeframe" is retired vocabulary. A BarSpec is a discriminated aggregation rule (`registry:barspec_kinds`: time-interval, tick-count, volume-threshold, notional-threshold, price-brick, range, or session) carrying exact parameters and, for time-based kinds, the anchoring market-hours calendar identity and version — so the same ticks under two anchors can never share a fingerprint, and non-time bar kinds are first-class in governed evidence. An indicator or family receives its BarSpec as data and never derives bar boundaries itself. (DEC-0126, DEC-0130)

### BENCHED

A bot-seat state only, and never a Book mode. Seat state on the Bot-Book binding is `active | benched`; Book modes are `LIVE | PAPER`; binding state is `live | paper | stood-down` — three vocabularies never interchanged, and a seat-state write never writes a Book-mode row. A benched seat routes to the paired target through its seat record's execution target while the Book stays `LIVE`; the bench event remains on the record after an auto-reset. A seat is benched by the bench fold — a read-time fold over the exit-record stream that counts **qualifying_loss_exit** events over the binding epoch — never a mutable counter. `ADMITTED` is not a state at all: it is the absence of a binding (DEC-0155, DEC-0149).

### Binding identity

Two distinct binding records exist, and their identity tuples differ deliberately. The **venue account-binding record** keeps its ratified identity `(VenueId, AccountId, role, world)`: a binding's secret reference is declared occurrence/display-only and excluded from `fp1` — a credential is a deployment fact, never a market fact — so two bindings that differ only by a rotated credential share one identity (DEC-0136). The **risk-domain Book binding** is `(BookInstanceId, BmsInstanceId, VenueId, AccountId, world)` — aligned with the `(VenueId, account)` command stream and never coarser than it — and `role` is deliberately **not** in that tuple: for routing purposes it rides the per-intent **execution target** instead, which is what lets a paper excursion or a benched seat route to the paired account without silently re-minting the Book binding (DEC-0143, DEC-0149). World is one of live, replay, or simulated (see **World**), and is a constant `live` for every live-path V1 Book binding — a QMB replay run mints its own `world = replay` binding (DEC-0160), a different binding identity, so replay-derived and live evidence are deliberately incomparable by binding (DEC-0143).

### BMS

The account-facing supervising layer of the risk domain: one BMS instance per Account, serving the many Books bound to that account — the BMS is what connects to the account. A Book binds exactly one BMS at a time, a dated append-only binding (re-binding mints a new binding record with a `supersedes` edge and a new binding epoch), and several Books binding one account share that one BMS instance and one command stream. `BmsInstanceId` is content-derived from `(BMS definition fingerprint, AccountId, VenueId, world)`. The BMS owns accounting, constraints, journals, KSA policy, and reporting; the Book owns admission, sizing, doors, leash, and profile selection — the authority split is default v1 verbatim, journal, record, and session machinery having moved QMF-side without the authority moving. A crypto or prop-firm BMS is a new BMS *version*, never a second BMS stacked beside an existing one. The documentation does not expand the initials because the authoritative sources do not fix an expansion. The pre-ruling definition — 'versioned machinery owned within the Book domain', with one Book holding several BMS policies — is superseded (DEC-0143); a BMS definition proves itself through the same three-layer admission as a Book (DEC-0146).

### Book

The account-facing risk and money-management container that controls bots: a Bot binds exactly one Book at a time, a Book binds exactly one BMS, and the authority order is bot -> book -> BMS -> operator (DEC-0143, DEC-0115). A Book is expressed as three identities minted apart (see **Book version / Book instance / binding epoch**): a versioned *template* (a structured configuration artifact identified by its `fp1`), an *instance* (that version instantiated onto one account, carrying an opaque `BookInstanceId`), and a *binding epoch* (the half-open interval a binding record owns). The template declares sections — charter, footprint_requirements, money_rules, `admission_bar`, leash_grammar, capacity_and_sweep, exit_policy, control_policy, protection_windows, and paper — plus `accounting_currency`, `required_venue_capabilities`, `required_producer_contracts`, and a keyed `worked_example`; every variable carries a unit-kind and a `ui-editable | uneditable` flag, numbers live inline and are identity-bearing, and versioning is git logic without git — an append-only version graph on `branches-from` edges (DEC-0144, DEC-0154). The Book owns exit policy for the life of a position; a Bot may only propose exits through the CT-23 door (DEC-0147). A new Book proves itself through three-layer admission — linters, a demo/paper shakedown, and one operator signature — with no trial period or paper-performance gate (DEC-0146). The recovered Scalping Book is one pattern, not the universal Book schema (DEC-0080).

### Book version / Book instance / binding epoch

The identity trinity of a Book, three things minted apart and never fused. A **Book version** is the template's content — grammar plus defaults — identified by its `fp1` fingerprint; UI edits mint a new version on an append-only `branches-from` version graph (multiple heads legal; `current` is a separate dated pointer), never mutate one, and every old version stays readable forever (DEC-0144). A **Book instance** is a minted deployment record — version fingerprint + AccountId + VenueId + world + mint occurrence + creation sequence — carrying an opaque `BookInstanceId`; two copies of one version on one account are distinct by mint and never merged, and an equal-fingerprint binding record is an `invalid-input` refusal, never an idempotent accept. A **binding epoch** is the half-open interval between a binding record and its superseder, identified by the binding record's fingerprint; CT-32 populations and the bench fold cite binding-record fingerprints, never intervals. An instance never spans venues: one strategy at several brokers is several instances of one version, each with its own BMS instance and connection (DEC-0143).

### Bot

A governed bot is exactly TWO artifacts: the **Bot definition** (the declaration — a structured configuration artifact under AD-30 template discipline, registered as CT-33) and the LOGIC (plain Python conforming to the bot runtime protocol, shipped as a versioned distribution under AD-2/AD-22 mechanics). The logic's identity basis is distribution identity + version + a canonical source-manifest fingerprint (a reproducible hash over the source tree, never built-artifact or wheel bytes), so a code change mints a new Bot exactly as a changed number mints a new Book (DEC-0172). The Bot definition's content is six groups: exactly one **strategy family** id; a **Confluence** set (one-or-more CT-34 fingerprints, canonically ordered with display ordinals); the declared parameter space (B-8's schema completed with an AD-40 unit-kind on every variable, one schema never two, whose defaults form the **canonical assignment**); the **footprint** (which contains the stream-set declaration as one locus); the permitted-intent declaration (`entry` always permitted, plus a possibly-empty subset of the ratified CT-23 exit-intent kinds, ids stored as opaque qmf-core-typed values); and the logic reference. IDENTITY CARVE-OUT: the AD-16 header's writer, sequence, stable id, and created-at are ordering/occurrence fields excluded from fp1 — Bot identity is semantic content plus contract format version and at-birth refs (DEC-0173). VERSIONING is AD-30's git logic: an append-only branches-from version graph (multiple heads legal, `current` a separate dated pointer), every version readable forever, continues-performance carrying a track record across versions only when human-signed. PARAMETERIZATION LAW: governed live and paper seats execute the canonical assignment ONLY; non-default assignments exist solely as B-3 run-spec overrides in experimentation, and promoting a tuned assignment mints a NEW Bot version. A Bot binds exactly one Book at a time, the Bot-Book-account binding a separate dated record (DEC-0115); the AD-41 seat record cites the registered Bot definition by fp1. (DEC-0172, DEC-0173, DEC-0115)

### Bot definition

The CT-33 registry artifact — the declaration half of a **Bot** (the other half is the plain-Python logic). It is a qmf-registry per-kind contract filling AD-16's reserved Bot kind, authored via **QML** and owned by qmf-registry like every kind. It carries the six content groups (one **strategy family** id, the **Confluence** set, the declared parameter space with its **canonical assignment**, the **footprint**, the permitted-intent declaration, and the logic reference) and is identity-bearing on semantic content plus contract format version and at-birth refs, with the AD-16 header's writer, sequence, stable id, and created-at excluded from fp1. It carries NO exit_logic field — exit policy is the Book's, per **strategy family** (DEC-0179). The Bot definition mints ONLY when both **conformance** layers pass (registration otherwise refuses, policy rejection), and it is what governed evidence and seats cite by fp1 (DEC-0178). The old name **BotSpec** is retired. (DEC-0173, DEC-0172, DEC-0178, DEC-0179)

### canonical assignment

The set of MANDATORY default values the declared parameter space of a **Bot definition** carries — one default per declared variable, together the definition's canonical assignment. Governed live and paper seats execute the canonical assignment ONLY; non-default assignments exist solely as B-3 run-spec overrides in experimentation runs, each fully labeled and resolvable from the resolved run-config fingerprint. Promoting a tuned assignment mints a NEW **Bot** version (branches-from) whose defaults are the tuned values — one identity locus, so no tuned bot silently wears the original's track record. The admission-side check this enables is the **conformance** admission bar's canonical-assignment evidence, read from the B-3 `assignment_is_canonical` stamp through a B-4 fold qualifier (DEC-0178, DEC-0183). (DEC-0173)

### Canonical sensing feed

The single pinned market-data feed an adapter reads for a given sensing need, carrying a prohibition, not just a capability: no silent sibling-feed failover. A sensing outage fails closed until that same feed gap-replays, never quietly switching to another feed. Market data — ticks, bars, depth, gap-replay backfill, historical paging — enters as **source observation (CT-10)** through qmf-data's CT-15 intake, application-mediated, with no venue-specific market-data contract and no new dependency edge; raw depth is recorded as the verbatim wire payload. (DEC-0138)

### Capability declaration

One of the two artifacts of an adapter's capability surface (the other is the **venue-observation profile**): static, adapter-version-scoped, importable without credentials, containing no measured or tunable value, every field marked `static` or `measured-at-connection`. It carries the venue protocol artifact identity, and its fingerprint is identity-bearing for any artifact whose decode depended on it. CT-18 owns its field roster (market-data kinds, order-parameter subset, command scopes, acknowledgement modes, position model per account, session topology, throttle scope, rate limits, span caps and paging model, token lifecycle class, equity nativeness, server-clock availability, instrument-metadata surface, attribution-label support, protection primitives). Invoking anything undeclared is an `unsupported capability` refusal. (DEC-0138)

### carries-ledger

A human-signed per-binding edge asserting that money-state carries across a new binding — virtual ledger, cycle position, budget remainder, breaker and bench counters — and asserting nothing about comparability. It is one half of the split of the legacy single `continues-as` edge (the other half is **continues-performance**), and the two are never inferred from one another. A changed Book number mints a new identity, a new binding, and a fresh cycle's money *unless* the new binding's **state_carry** declares carry under a `carries-ledger` edge; so a rule change never moves money by accident. carries-ledger moves money-state and moves no track record (DEC-0158, DEC-0143, DEC-0154).

### Causality gate

A qmf-registry registration precondition that checks whether submitted evidence was knowable by the applicable cutoff. Claim fields, comparison rules, and pass evidence remain `GAP(GAP-0016)`. See also **look-ahead**.

### CivilDate

A qmf-core time type for an ordinary civil (wall-clock) day, distinct from **TradingDate**. A CivilDate is display-oriented and never carries trading semantics: it is not a session boundary, not a trading-day identity, and never a causality proxy (causality is compared on Instants only). Civil and trading dates are separate types precisely so a formatted civil day is never mistaken for a trading day. (DEC-0106)

### close reason

The typed reason every close carries, generalized from the QML CloseReason taxonomy, addable never redefined: `protective_stop_fill | target_fill | protection_amendment_fill | bot_intent | hold_time_force_flat | boundary_flat | window_forced_flat | protection_forced_flat | kill_line_flat | venue_liquidation | venue_initiated_close | operator_close`. `kill_line_flat` is minted apart from `protection_forced_flat` because the **kill line** and the **kill switch** are two different things. Every `(control-action kind x issuing authority)` maps to exactly one close reason through a pinned versioned table, and reports partition by close reason so a bot's edge and what the gates cost are one dataset read two ways (DEC-0147).

### cohort key

The declared match key that lets two evidence streams enter one alpha-decay judgment: Bot identity, Book identity + template version, world, the pinned sensing feed, configured producer fingerprints read as refit-series identities, calendar identity + version, instrument identity or declared equivalence, the active-control set, and the active protection-window set. Account role is recorded and deliberately allowed to differ — that is what makes paper-live comparison possible. A judgment spanning mismatched cohorts is a policy rejection, never a silent average, and a decay cohort read is an explicitly permitted cross-role read within `world = live` (DEC-0149, DEC-0158).

### Command stream

The `(VenueId, account)` pair — the unit of **UNKNOWN** blocking, of **WriterId** ownership, and of the gapless per-writer sequence. It is coarser than an account binding (all bindings on an account block together) and strictly finer than a connection (a shared connection never couples distinct accounts' uncertainty); sessions and bindings exist but neither is a stream. A **session epoch** id rides every venue observation; sequences reset only on boot, never on reconnect, and the sequence cursor is durable through the observation sink. Order-path internals below this contract surface are trading-node territory, referenced only as a pointer (`tracker/trading-node-notes.md`), never absorbed here. (DEC-0137, DEC-0142)

### Command-id-binding record

The durable record — `(venue client id, command fp1, account, session epoch)` — persisted through the observation sink **before** submission whenever the CT-18-declared mapping from a command's `fp1` into the venue's client-id field cannot be injective and total over the digest space. It is named reconciliation evidence. Idempotency and collision tests run against the full local fingerprint, never the venue-side id: re-presenting the same command is an idempotent accept, and differing content under a reused identity is refused and alarmed. (DEC-0137)

### Compound command

A command that fans out to N venue submissions. Each child carries a derived identity (parent `fp1` plus a declared ordinal) and is individually observation- and journal-bearing; the parent's outcome is the meet of its children — any child **UNKNOWN** makes the parent UNKNOWN, and any child rejected makes the parent **partially-executed**, a named outcome, never a success. (DEC-0137)

### Compromise drill

The documented, tested recovery when venue credential material may be compromised: venue-side invalidation (on the cTrader-platform profile, cTID re-authorization invalidates all outstanding refresh tokens), application-credential reset, store replacement, and session restart. Expiry and refusal paths ship as tested behavior; testing uses demo credentials only and factory sandboxes never hold live secrets. The drill turns the never-expiring refresh token from a standing hazard into a recoverable one; credential entry and management UI is platform territory. (DEC-0136, DEC-0135)

### Computation identity

The content-derived identity of a computed result, assembled from its result label parts — producer contract identity (the configured producer's fingerprint), producer contract format version, input fingerprints, evidence time range, evidence class, and world — so that identical work from two factory sandboxes deduplicates and merges (DEC-0110, DEC-0131). Computation identity is distinct from the **Occurrence** record (when, where, and by whom the work ran), which is separate provenance held outside identity. Human display names also live outside identity. (DEC-0110, DEC-0114)

### Confirmation

The **confluence leg** role (`confirmation`) that confirms a candidate trading condition: a producer binding plus optional declared parameters, its condition living in the Python logic in V1 (DEC-0175). A **Confluence** carries one-or-more legs of any role mix, so it need not contain a confirmation leg at all (DEC-0175); any structure evidence a confirmation leg consumes is governed by CT-17's lifecycle law (DEC-0129). Distinct from a structure object's **confirmation record**, the append-only lifecycle record carrying confirmed-at.

### Confirmation delay

The declared maximum bound, in observations at the family's **BarSpec**, between a structure object's observed-at and its confirmed-at (unbounded only for families excluded from split-governed evidence). Confirmation delay feeds purge and embargo widths together with **warm-up**, so early-entry research cannot leak evidence a confirmed read would exclude. Distinct from a structure object's confirmation record. (DEC-0129)

### Confluence

A registry artifact (CT-34) of reusable bot-side trading logic, cited by fingerprint. A confluence carries ONE-OR-MORE **confluence leg**s of ANY role mix — at least one leg of any role, never one of each — each leg a `(role, producer binding, optional declared exact parameters)` triple whose role is one of `level | trigger | confirmation | filter`; a leg may cite another confluence (composition). A confluence is its own artifact with lineage to its children (AD-17), NOT a CT-17 causal-structure composite, so AD-25's order-significant-by-default does not reach it: legs follow a fingerprint-ascending default with display-only ordinals, and order-significance is opt-in per confluence, entering the fingerprint ONLY when declared. Condition semantics live in the Python logic in V1. A **Bot** contains one-or-more confluences (DEC-0115); exit ownership is separate — the Book owns exit policy and a Bot may only propose exits through the CT-23 door (DEC-0147). (DEC-0175, DEC-0115, DEC-0147)

### confluence leg

A single element of a **Confluence** (CT-34): a `(role, producer binding, optional declared exact parameters)` triple, where a leg may itself cite another confluence (composition). A confluence carries ONE-OR-MORE legs of ANY role mix — at least one leg of any role, never one of each. The LEG-ROLE VOCABULARY is CT-34's own closed-and-addable contract surface (addable never redefined): `level | trigger | confirmation | filter`. AD-17's three — level, trigger, confirmation — are the seed; `filter` is the FIRST addition, freshly minted: a suppressing condition consuming the same governed producers, not a new species. The old formula's Features are producer bindings consumed by level and trigger legs; the old formula's Filters get their governed home as filter legs. Condition semantics — WHEN a leg is satisfied — live in the Python logic in V1; the declaration carries only WHAT is consumed and WHICH role each leg plays, and a fully declarative predicate grammar is Deferred. (DEC-0175)

### conformance / conformance ticket

Conformance is TECHNICAL, NEVER performance (AD-32's no-probation law mirrored): "conformant" means a bot passed both conformance layers, never "certified" and never "passed an exam". Two layers gate the ticket. Layer 1 is the declaration linter at registration — schema completeness against the declared format version, every parameter unit-kinded with a valid **canonical assignment**, every reference resolvable, **footprint** completeness under the transitive-union law, template completeness, and permitted exit-intent kinds within the ratified CT-23 vocabulary; failures are AD-11 typed refusals, journaled. Layer 2 is sandboxed execution conformance, SPLIT into a QML-owned pure format-versioned contract (the denial set, static AST/import-scan rules, the determinism harness, a deterministic golden-slice generator keyed off the declared footprint, and the verdict function) and a host-owned runner (process spawning and isolation only), so the verdict is host-independent by construction and no Book is present. THE TICKET: the Bot registry kind mints ONLY for artifacts passing both layers (registration otherwise refuses, policy rejection), and that registration is what governed evidence and seats CITE — conformance gates evidence CITATION and SEATS, never tunnel entry, so ungoverned bots keep full tunnel access. V1 enforcement is stated honestly: static scan + capability starvation + host process isolation; hardened OS-level confinement is a named deferred dependency of the node/platform sitting, and a dynamically-evasive malicious bot is out of V1's threat model. (DEC-0178)

### Connection manager

The single named adapter component permitted to hold **SecretValue** material in memory, for a session's lifetime, and the sole owner of venue sessions — no other component may construct a venue client. It receives a core-defined `SecretStore` port (read plus atomic replace) injected by the composition root; secret values never cross back out (no getter, log line, refusal context, health field, or metric label). On the venue path it holds the **WriterId** at granularity `(machine, adapter role, VenueId, account)`, stamps writer and sequence, and calls the injected **sink protocols** synchronously, so it is the component that sees every persistence failure and raises the command-pipe block. (DEC-0136, DEC-0138)

### continues-performance

A human-signed track-record assertion that a performance line continues across a Book change, consumed only by CT-32 population declarations and moving no money. It is one half of the split of the legacy single `continues-as` edge (the other half is **carries-ledger**), and the two are never inferred from one another. The track record travels on continues-performance separately from money, so a rule change never resets the performance line by accident (DEC-0158, DEC-0144).

### currency-exposure record

A dated per-instrument metadata record declaring an instrument's currency exposure, read to resolve protection-window instrument scope — venue-populated where metadata exists, operator-declarable and correctable otherwise. Reading a currency out of a symbol is prohibited; scope is declared, never parsed. A missing record means treated-as-affected: the instrument is blocked while a window of an enabled kind is in force, and the absence is journaled as data quality and alarmed (DEC-0152).

### Dataset release

A reproducible identity and manifest for a fixed dataset partitioning. Splits are fingerprinted, time-ordered, non-overlapping manifests, each pinning exactly one calendar identity and version in-band, with boundaries as explicit stored TradingDates or instants and the seal boundary a frozen TradingDate never re-derived under later tzdata (DEC-0119).

### Day-boundary calendar

One of three distinct named calendar concepts — always write "day-boundary calendar", never bare "calendar" (the other two are **market-hours calendar** and **news calendar**). A day-boundary calendar is an accounting-boundary rule parameterized by **Account**: it answers only "which day does this instant belong to for evaluation," and a prop firm's daily-loss day evaluated in its stated timezone is one example. It is never substituted for a market-hours calendar, and it produces TradingDates carrying its own calendar identity. V1 holds the seam only; no prop firm is modeled. (DEC-0106)

### Denied-locally

One of the four submission outcomes (`accepted-by-venue | rejected-by-venue | denied-locally | UNKNOWN`): a command the adapter declines before it reaches the venue. `denied-locally` is an **outcome, never a refusal** — typed refusals are reserved for malformed commands, undeclared capability, and a blocked stream — and like every outcome it mints an observation record and a journal event. (DEC-0137)

### Derived-series identity

The identity rule for computed or synthetic series: a series produced by a CT-16 or CT-17 configuration is identified by its result label — never by minting an Instrument. Any governed output series is a legal input to any CT-16/CT-17 configuration, and the upstream artifact's fingerprint enters the downstream identity, so chained computations stay individually attributable. (DEC-0126)

### Duration

A qmf-core time type: a signed int64 quantity of nanoseconds. A Duration is clock-agnostic and freely storable; the discipline sits on operations, not on the value. A Duration used for latency, timeout, cooldown, or cadence must be measured monotonically (see **WriterId** and the monotonic-clock rule); a Duration derived by subtracting two wall Instants is an evidence span, never an elapsed-time measurement. (DEC-0106)

### enacts

The typed lineage edge from a command record or outcome observation to the control-action or intent record it enacts. Arbitration, suppression accounting, and standing-intent folds resolve through `enacts` edges, never through `correlation_id` (which is a tracing annotation only). enacts links enactment to intent; correlation_id never does (DEC-0158, DEC-0150).

### Event time

The time at which an observed market or external event occurred. Event time is distinct from knowledge time under CT-10.

### Evidence class

A named part of the result label and a declared identity field with three values (`registry:evidence_classes`): **confirmed** (the object's confirmation rule has fired), **unconfirmed** (emitted before confirmation — legal, separately labeled, linked to its confirmed successor by a typed `confirmed-as` edge), and **provisional** (computed over an incomplete aggregation period — never enters governed evidence). A read requesting confirmed evidence refuses unconfirmed rows (`policy rejection`) rather than filtering silently, so early-entry research and confirmed evidence can never silently mix. (DEC-0129, DEC-0131)

### Exact rational

The parameter idiom extending exact money to every non-integer parameter: a scaled integer or a numerator/denominator pair. Ratios, multiples, and tolerances are exact rationals; binary floats never appear in parameters or identity content, so fingerprints stay deterministic across platforms. (DEC-0126, DEC-0131, DEC-0105)

### execution target

The per-intent record resolving where an intent's order routes — live or paper/demo — resolved once at intent mint from (Book mode, seat state, active-control set) and entering the command record's identity. Role rides the execution-target record rather than the binding tuple, which is what separates routing from binding: live and demo are distinct `(VenueId, account)` command streams, so an outstanding UNKNOWN on one never gates the other. One active paper-routing target per live binding at an instant (DEC-0149, DEC-0143).

### External source adapter (CT-15)

The external-to-middleware provider boundary terminating at `COMP-QMF-DATA-INGEST`. CT-15 does not terminate at `COMP-QMF-DATA`; Data-Ingest translates provider evidence and produces CT-10 into the Data-owned governed boundary. qmf-data defines the source contracts, normalization, validation, and idempotent intake keyed on `(source, source-native id, revision)`, while applications own scheduling, retries, and supervision (DEC-0119). Tick sources are separately identified, bid and ask preserved with source timestamps, and disagreements kept visible via `corroborates` and `disagrees-with` edges, never merged (DEC-0119). The news-calendar recorder keeps provider-native identity and revisions through the same intake (DEC-0119); the provider legal archiving posture remains an open operator item.

### Exit

The policy or action that closes or reduces a trading position. Exit ownership is ratified: the Book owns exit policy for the life of a position, and a Bot may only propose an exit through the versioned risk-evaluation door (CT-23), which the Book executes or refuses with a recorded, journal-bearing reason — fast invalidation is preserved as a proposal path. Exit intents are risk-monotonic by construction — the V1 kinds are `close_full` and `tighten_protective_stop`; `close_partial` is not a V1 kind, and a partial exit is an `unsupported capability` refusal. Every close carries a typed **close reason** (DEC-0147).

### exit-preservation invariant

Spine-level law (constitution L39): no control action, of any authority, at any scope, may block a risk-reducing act — `cancel_order`, `close_position`, `close_all`, a risk-non-increasing `amend_protection`, or a protection action — or the recording of evidence. The blocking half of any control is always entries only, and no control-action kind whose effect is a blanket command-pipe block may be minted. It is why a kill switch or a protection window blocks new entries but never traps open risk behind itself (DEC-0150, DEC-0148).

### Experimentation and backtesting

Settled vocabulary as of the QMB sitting: experimentation is the umbrella research activity and backtest is the verification stage within it, now realized by **QMB** (DEC-0159). The backtest fidelity seams are ruled — separate fill, slippage, and cost ports with financing as a scheduled position-level event, partial fills first-class, lowest-fidelity-wins — while the fidelity taxonomy values and calibration content stay open under `GAP(GAP-0048)`, its own sitting (DEC-0164). See also **QMB** and **Future backtesting library**.

### Fill

An asset-neutral qmf-core market noun for an observed execution result. It references an instrument by its ratified `(venue, venue's own symbol)` identity (DEC-0107); fill price, fill quantity, the venue instant, and the receive instant are mandatory identity fields of a fill observation under CT-20, and reconciliation read-back evidence is CT-20 surface (DEC-0137).

### Future backtesting library

The reserved entry for a modular, on-demand QMF consumer for testing Bot-by-Book behavior, now realized at the planning level by **QMB** (DEC-0159). It remains outside QMF V1 and is not a permanent central service, runtime engine, or Simulator UI; see **QMB** for the ratified shape.

### Final holdout

The sealed recent portion of retained history excluded from the default research path and reserved for a logged final evaluation. The 12-month seal is a no-peek lock enforced as a `policy rejection` refusal at every qmf-data read boundary, including restored backups; its boundary is a frozen TradingDate, and the one permitted final look is journaled as a control-action subtype and never silently recycled (DEC-0119).

### Fingerprint (fp1)

A deterministic, versioned identity derived from a canonical serialization, emitted as the string `fp1:sha256:<hex>`. The canonical serializer and fingerprint function live only in qmf-core; no other package computes a fingerprint except by calling it. The pinned `fp1` recipe is UTF-8 JSON with object keys sorted lexicographically at every depth, no insignificant whitespace, NFC-normalized strings, integer-only identity numerics (floats are refused in identity content), null prohibited (an absent value is an omitted key, never a null), and order-significant arrays, hashed with SHA-256. The `fp1` prefix versions the recipe: a recipe change mints `fp2` and old fingerprints stay valid forever. Every contract field is identity by default; display-only exclusion requires an explicit, versioned contract declaration, never an implementer's judgment. A byte-identical re-write of the same hash is accepted silently (the sandbox-merge normal case); a true collision — same hash, differing bytes — is refused and alarmed, never overwritten. Float-bearing artifacts take label-derived identity (see **Computation identity**) rather than a hash of float bytes. (DEC-0108)

### First-connection verification suite

The named CT-18 contract part that runs post-connect and is **verify-or-refuse** throughout: an unverified spot-timestamp unit refuses spot evidence; an unmeasured daily-bar boundary leaves venue daily bars ungoverned until it is measured and minted as a **venue-scoped market-hours calendar identity**; a failed bar-basis reconciliation refuses bar evidence; a failed pip-formula validation refuses metadata-derived parameters; an absent money exponent refuses that message's money decode. Its measurements and verdicts populate the **venue-observation profile** and journal as `data quality` events. (DEC-0138)

### fold contract

The declaration every read-time fold the spine names must ship: its stream, its ordering key, its knowledge-time bound, and its equal-instant disposition. Across writers, control and mode folds resolve by rank, never by WriterId byte order. No fold on the trading path may refuse — it returns the most restrictive state, journals data quality, and alarms. Runtime state (Book mode, seat state, order state, bench counts, standing protection intent, structure lifecycle) is a read-time fold, never a stored mutable field, and each such fold declares its fold contract (DEC-0150).

### footprint

The single canonical consumption manifest of a **Bot definition**: the stream set (instrument-role + BarSpec list in B-12's shape, trading vs data-only roles, held as one contained locus), the required calendars (identities + versions per AD-8), and the producer bindings — each either a pinned configured-producer fingerprint (CT-16/CT-17 identity) or a **producer template**. COMPLETENESS LAW: the footprint's producer-binding set MUST EQUAL the transitive union of every cited **Confluence**'s leg producer bindings plus any bot-direct producers — a confluence-leg producer absent from the footprint is a Layer-1 registration refusal. Hosts provide ONLY the declared footprint to the logic. The bot's warm-up/embargo horizon is DERIVED at resolution from the resolved producer chain (AD-21/AD-22), never hand-declared. The Book side declares `footprint_requirements` — a set of typed requirements over CT-33 footprint fields under admission_bar's grammar discipline, values in Book templates — checked by the **prediction linter** (DEC-0181). (DEC-0174)

### Foreign-float law

The AD-7 rule extending foreign-money-verbatim to binary floats a venue delivers (cTrader execution prices and conversion rates are raw doubles): a foreign float is evidence, **never identity**. It crosses the named venue-adapter boundary at receipt to a scaled integer at a **per-value-class target scale** with a declared, identity-bearing rounding mode; the raw float is retained only as integrity-checked provenance and is never the value a consumer reads. (DEC-0141, DEC-0138)

### Four-outcome law

The rule that every well-formed venue submission resolves to exactly one of `accepted-by-venue | rejected-by-venue | denied-locally | UNKNOWN`, and every outcome mints an observation record and a journal event. A transport error, timeout, or disconnect yields **UNKNOWN** — a state, not an error; a venue-returned error resolves `rejected-by-venue` only where the CT-18 error table declares that outcome class, and every other path is UNKNOWN. No QMF component retries, assumes an outcome, flattens, or invents a terminal state; flatten is `close_position`/`close_all` executed mechanically, and its authority assignment is risk/node-sitting territory, referenced only as a pointer (`tracker/trading-node-notes.md`). (DEC-0137, DEC-0142)

### Graduation path

The route by which a working plain-Python research experiment enters governed evidence as a CT-16 indicator or CT-17 structure family through the AD-2 extension shape — a separate versioned package outside the seven-package roster, its own SemVer ladder, distribution identity and version as identity fields of every artifact it produces, explicit registration at the composition root — carrying a lineage edge back to the originating research artifact. Authoring outside the framework stays legal always; the graduation path keeps that freedom without losing provenance when an experiment becomes evidence-bearing. (DEC-0133)

### Injected sink / sink protocols

The qmf-core-defined ports (`ObservationSink`, `JournalSink`, `RecordSink`, `SecretStore`) the composition root injects into a venue adapter so its write path creates no dependency edge — sinks are core protocols, not a package import. The **connection manager** holds the **WriterId**, stamps writer and sequence, and calls the sinks synchronously; every sink returns success or a typed refusal to its caller, and a `storage failure` from any sink triggers the command-pipe block in the component that holds the WriterId. The root-mints pattern used for structure emissions does not extend to the venue path, because here the writer must see the failure. (DEC-0138)

### Instant

A qmf-core point in time: int64 UTC nanoseconds since the Unix epoch (POSIX, no-leap-second semantics), representable over 1677–2262. All nanosecond arithmetic is checked — overflow is an `invalid input` typed refusal, never a wrap. Instant `0` is a valid instant, and an absent time is an absent field, never a zero. Local time is display-only and always labelled. A wall clock produces Instants; a monotonic reading is never an Instant. Instants alone never totally order events — see **WriterId** for the ordering rule. (DEC-0106)

### Instrument

An asset-neutral qmf-core market noun for a tradable market object. Identity is `(venue, venue's own symbol)` with the symbol opaque and never parsed; aliases, renames, asset class, and mutable metadata are separate dated records pointing at the identity, and stored history never rewrites. (DEC-0107)

### instrument_class record

A dated instrument-metadata record kind naming an instrument's class, operator-declarable and correctable, never derived by parsing a symbol. SQS reads it to select its per-class hard-block threshold; no class record means the instrument is blocked, the absence journaled as data quality (DEC-0153).

### Interaction record

The only permitted way a structure object's state evolves: an append-only record (instant, price, family-declared interaction measure) referencing the object's fingerprint. The object itself is never mutated; "still valid at T" or "still unmitigated" is a read-time fold over the object's edge stream under CT-17's read-resolution rule. Each interaction instant is an identity field of its own record. (DEC-0129)

### Interval

A qmf-core time type: a half-open interval over Instants, `[start, end)`, supporting `contains` and `overlaps`. Half-open boundaries let adjacent intervals tile a timeline without overlap or gap. (DEC-0106)

### Journal

Durable evidence emitted through qmf-data as N append-only streams — one per producing component, each under its **WriterId** with gapless per-`(writer, boot-epoch)` sequences, where a gap signals loss. The Journal records seven event types: decision, order, fill, risk transition, promotion, data quality, and control action. It is an evidence encoding, not a runtime event bus or arbitrary application-log store; entries store int64 UTC nanoseconds plus writer and sequence (contrast operator logs, which render UTC ISO-8601 with an explicit `Z`). `correlation_id` is a linking annotation excluded from `fp1` identity by explicit versioned declaration, and causal linkage across streams uses typed lineage edges, never timestamps. Retention and trimming rules are set only after measured volume. (DEC-0119, DEC-0112, DEC-0118)

### kill line

A per-Book capital floor: breaching it automatically flattens that binding's scope and stands the Book down — a 3am breach never waits for the operator. The kill line is not the **kill switch**, and the two are never interchanged; a kill-line breach flattens through the pre-declared `book_policy` trigger class and its close reason is `kill_line_flat`, minted apart from `protection_forced_flat`. `loss_floor` is the same number the kill line names — one value, one name, read by both the runway ladder and the breaker, never two floors that drift (DEC-0150, DEC-0154).

### kill switch

The global black-swan authority: it stops all new trading everywhere, live and paper alike, is sensor-fed (MIS and SQS are inputs, never authorities), escalates automatically, and de-escalates only by a human. Its effect may additionally be `drain` or `close_all`, and which effect a severity carries is the node's severity policy to choose — QMF forbids itself both from choosing it and from a contract that cannot express it. The kill switch is not the **kill line** (a per-Book capital floor), and the two are never interchanged. It stops new entries under the exit-preservation invariant; it never blocks a risk-reducing act (DEC-0150).

### Knowable-at

The per-sample instant every CT-16 output carries: the earliest instant at which every contributing input was knowable. Knowable-at is what split manifests and causality reasoning consume for indicator results — a projected or forward-shifted output keeps an honest knowable-at even when its index offset points elsewhere, which is what makes look-ahead visible instead of implicit. (DEC-0126)

### Knowledge time

The time at which an observation became knowable or entered the governed evidence system. Knowledge time is distinct from event time and is required for causality checks under CT-10.

### Level

A confluence or market-structure element representing a causally derived price or market area. As structure evidence it is one of the open family-declared geometries under CT-17's lifecycle law — minted at observation, confirmed by its precise rule, evolved only through interaction records (DEC-0129); as a **confluence leg** role (`level`) it is a producer binding plus optional declared parameters, its satisfaction condition living in the Python logic in V1 (DEC-0175).

### Light and heavy

Two placements of the same CT-16 or CT-17 contract, not two species. A configuration is **light** only when it declares and benchmark-proves four bounds (per-update cost within the live-path latency rung, bounded declared state size, a bounded evidence window or an O(1) anchor-reset rule, and synchronous availability); otherwise it is **heavy**. Until the live-path rung has a recorded baseline, every configuration is heavy by default and a light claim is refused at the gate. A heavy configuration's synchronous entry point returns `unsupported capability`; heavy runs off the trading path, computed once and fanned out through the same contracts, each fanned-out value carrying the instant and input sequence of its last input. Classification is per configuration, never per name, and the light/heavy verdict is display-only, never in identity. (DEC-0128)

### Lineage

Graph-shaped, append-only provenance among versioned identities, variants, and occurrences. At-birth parent references live in the record header; lineage accruing after birth lives in append-only typed edge records — `supersedes`, `promoted-from`, `occurrence-of`, `corroborates`, `disagrees-with` — referencing fingerprints, stored as pinned JSONL with local rebuildable indexes and no database server (DEC-0114).

### Look-ahead

Use **causality gate** for the registration control. Look-ahead is the prohibited use of evidence that was unavailable at the applicable decision cutoff.

### Market-hours calendar

One of three distinct named calendar concepts — always write "market-hours calendar", never bare "calendar" (the other two are **day-boundary calendar** and **news calendar**). A market-hours calendar carries two separately-named facts, each with its own zone: an accounting rollover (which trading date an instant belongs to) and a session schedule (when the market is open). Its calendar identity is the rule set (for example `forex-17NY` v3) plus the tzdata version — only these enter fingerprints — and is separate from its binding to venues or accounts. The forex market-hours calendar ships first: a `registry:forex_rollover` rollover, weekend gaps, and holidays in scope, with swap-Wednesday dropped from V1. Session and trading-day length is data; no consumer may assume a constant. A market-hours calendar ships as a calendar extension outside the seven-package roster, on its own SemVer ladder, with tzdata pinned and verified against the resolved version at import. (DEC-0106)

### MIS

A future trading-node analytical or machine-learning ensemble consumer. MIS is not a QMF V1 library and is not `qmf-indicators`.

### Money path

A taint, not a location. Any value that transitively contributes to an order quantity, price, P&L, or balance is on the money path, regardless of which package computed it. Binary float is banned on the money path; a float crossing back to Money, Price, or Quantity must pass a named conversion boundary with an explicitly stated rounding mode (the venue adapter boundary is one such named boundary). Foreign money — a venue's raw wire integers — is stored verbatim as evidence with its declared scales, and conversions to framework values are derived with lineage, never rewrites. Analytic float series remain permitted off the money path; their identity is label-derived (see **Computation identity**), never a hash of float bytes. (DEC-0105)

### News calendar

One of three distinct named calendar concepts — always write "news calendar", never bare "calendar" (the other two are **market-hours calendar** and **day-boundary calendar**). The news calendar is the economic-events feed recorded by `COMP-CALENDAR-FEED`, the news-calendar recorder, which keeps provider-native event identity and revisions through idempotent `(source, source-native id, revision)` intake. It is never a market-hours or day-boundary calendar. Scheduling, auto-sync (for example FOMC reschedules), and UI are application territory outside QMF; the legal archiving posture remains an open operator item. (DEC-0119)

### Occurrence

A concrete provenance record — when, where, and by whom a computation ran — held separately from and outside artifact identity. In the registry, created-at and other occurrence facts are declared occurrence/display-only so that identical work from two sandboxes deduplicates on **Computation identity** rather than on run metadata. Reserved kinds such as Bot and Book are filled by their own sittings. (DEC-0110, DEC-0114)

### One-refresher-per-credential

The rotation-safety rule making a credential a one-writer stream: exactly one live refresher per credential, so a workstation tool never refreshes a credential a VPS session owns. It is the AD-15 one-writer-per-stream discipline applied to secret material, and it is what prevents two processes racing to rotate the same refresh token. (DEC-0136)

### Orchestrator (QMB)

QMB's one impure component: it spawns a process per run under a `min(cpu, ram)` governor (enqueue-on-full), owns the log sinks, and writes exactly one WriterId-scoped JSONL ledger line per run, aborted runs included. The library `run()` stays pure and returns; the orchestrator is the only part that touches processes, logs, and the ledger — no Ray, no required Docker, no daemon (DEC-0161).

### Order

An asset-neutral qmf-core market noun. The command vocabulary, order-parameter subset, command identity, and the venue client-id mapping are ratified in CT-19 and CT-18; order state is a read-time fold over CT-20 observations, never a stored state machine (DEC-0137, DEC-0138).

### Out-of-sequence edge

The typed annotation attached to an inbound venue observation that has no legal transition in the order-state fold. The observation is still recorded verbatim first (recording precedes interpretation), then annotated with the out-of-sequence edge, and it forces the owning command to **UNKNOWN** pending resolution. Adapters never synthesize venue observations; a derived state is a fold result, never a stored event. (DEC-0137)

### Paired demo

A demo binding run simultaneously alongside a live binding under the venue's declared session topology (two connections where demo and live are separate hosts). Paired-demo bindings are secret-reference-only records identified as ordinary account bindings; a shared-account order-lifecycle merge uses only the caller's sequencer evidence, never a venue-side id. (DEC-0138)

### paper epoch

An operator-signed record opening a fresh paper-money accounting span with a declared starting balance and a lineage edge to its predecessor. A paper reset is not a balance adjustment: it mints a new paper epoch, and the running balance is never mutated. Paper money is frozen evidence — the starting balance is a Book/family-scoped configurable UI-editable default, frozen at flip — and paper P&L never crosses the money boundary and never buys a seat (DEC-0149).

### Paper mode

A Book-level execution mode expressed as a dated change of the Book's execution binding — a record change, not a new object, and never parallel Bot twins. Book modes are `LIVE | PAPER`; `BENCHED` is a bot-seat word only and never a Book mode; per-seat routing rides the seat record, which is what lets a Book stay `LIVE` while one seat routes to the paired account. Paper is a **standing evidence state**, not a waiting room: any declared condition that blocks live execution routes the Book's activity to its paper target and evidence keeps flowing. Every control trigger declares its disposition — `routes-to-paper | blocks-paper` — as a mandatory field: a control that blocks live for market-risk reasons (a protection window, the kill switch) blocks paper too; a control that blocks live for capital or authority reasons (a kill-line stand-down, a benched seat) routes to paper. Routing to paper is never a way around a control — what continues under a control is the recording, not trading. One active paper-routing target per live binding at an instant, resolved through the per-intent **execution target**; the paper target is reconciled as its own binding and a silent outage there raises the same alarm class as a live one. Paper money is frozen evidence: the starting balance is a Book/family-scoped configurable UI-editable default, frozen at flip, never hand-adjusted; a reset mints a new operator-signed **paper epoch** with a fresh declared balance and a lineage edge, the running balance never mutated; paper P&L never crosses the money boundary and never buys a seat. Return to live is automatic only where the clearing cause is itself clocked and mechanical; anything touching real money requires an operator signature, and paper performance never authorizes a return (DEC-0149). Confirms and subsumes the earlier Book-level-paper ruling.

### Partially-executed

A named **compound command** outcome: some child submissions resolved and at least one child was rejected. It is never reported as a success. Any child **UNKNOWN** instead makes the parent UNKNOWN; partially-executed arises only when every child is a definite outcome and the set is mixed. (DEC-0137)

### Per-value-class target scale

The pinned integer scale a foreign value converts to at the named venue-adapter boundary, chosen by value class: an execution price to the instrument's declared digits; money to the account's declared money exponent, an absent exponent being a refusal; market data to the declared wire scale (cTrader's 1/100000). CT-18 pins the scale per value class, and the rounding mode is declared and identity-bearing. (DEC-0138, DEC-0141, DEC-0135)

### Platform-vs-broker distinction

The AD-9 rule that the trading **platform** (cTrader) fixes the wire protocol and the adapter, while the **broker** behind it is a per-deployment fact, never architecture. Opaque VenueId/AccountId identity and account bindings are sufficient — account IDs are enough — and a broker's measured behaviors (its daily-bar boundary, its trend-bar price basis) live in the **venue-observation profile** and per-broker configuration, never in code. No rule anywhere names a specific broker; IC Markets is the operator's stated intent, not a framework commitment. (DEC-0139)

### Position

An asset-neutral qmf-core market noun representing market exposure, referencing an instrument by its ratified `(venue, venue's own symbol)` identity (DEC-0107). The risk domain splits it in two (see **virtual (Book) position vs venue position**): a **venue position** is observation-derived under the venue's declared netting | hedging model; a **virtual (Book) position** is a fold over fills joined by declared command identity — binding-scoped, Bot-attributed, minted at admission, carrying the frozen R faces — and is the unit of exit records, whole-trade attribution, and the bench fold. Every risk record names which of the two it references (DEC-0154).

### prediction linter

A static Book-vs-bot compatibility check, run on demand and at seat time against the CT-28 binding context, filling AD-32's Layer-1 pending slot now that the QML sitting has landed CT-33 (it was formerly a `pending(bot-schema sitting)` slot). Its check list is pinned, addable never redefined: (a) the CT-33 **footprint** satisfies the Book's `footprint_requirements`; (b) the bot's declared permitted EXIT-intent kinds are a subset of the Book's exit_policy permitted exit kinds (`entry` is never gated — a zero-exit-kind Book, the honest V1 default, admits entry-only bots); (c) the bot's **strategy family** resolves an exit_policy entry (explicit or the declared catch-all); (d) the bot's stream set lies within the binding's declared venue capabilities (CT-18, through AD-29's bind-time check). It passes registration and blocks live binding, and is not a performance gate — no trial period, probation window, or paper-performance gate exists (DEC-0178, DEC-0146, DEC-0144).

### Presence map

The parallel integer-encoded map every bulk series carries, marking each position `present`, `provisional`, `not_ready`, `gap`, or `absent_by_schedule` (`registry:presence_map_states`). Positions are never omitted or shifted; NaN and sentinel markers are prohibited; equality compares presence maps first and values only at present positions. A market-hours-closed position is `absent_by_schedule`, never a `gap` — missing means calendar-open with no data. (DEC-0126)

### PriceDelta

The first-class qmf-core value for a price difference: price subtraction is closed and delta-typed, so a `PriceDelta(instrument, scale)` is distinct from a `Price` and never masquerades as one. The instrument-scoped pip or point is defined by instrument-metadata records, never hardcoded, so stop distances and range widths carry honest units. (DEC-0131, DEC-0105)

### Processed data

Data derived from raw evidence through an identified transformation. Processed data does not replace or overwrite raw evidence.

### producer template

One of the two forms a **footprint** producer binding may take (the other is a pinned configured-producer fingerprint): a COMPLETE CT-16/CT-17 configuration minus ONLY the space-bound parameter values. It carries every AD-22 identity field (formula id, contract format version, ordered named input set, calendar requirements, alignment policy, missing-value policy, warm-up, output schema, supported modes, arithmetic-reference configuration) except the parameters bound to named bot-space parameters; an omitted identity field is a Layer-1 registration refusal. Resolution — substituting the space-bound values — is a TOTAL, SINGLE-VALUED function producing one deterministic CT-16/CT-17 fingerprint, so dedup lands on ordinary configured-producer fingerprints and identical canonical runs fingerprint identically on every machine. Template resolution is a declared B-3 config-compiler extension AND a node seat-admission responsibility, composing with B-8's value resolution (DEC-0183). (DEC-0174)

### Promotion

The human-controlled act that moves a registered artifact into the live zone. The registry reserves a promotion-occurrence card kind: a human-only signer, a signed immutable record, and a mandatory plain-words summary declared an identity field; V1 signing is the operator's recorded approval attesting the record's `fp1` string, and the journal's promotion event carries only the card's fingerprint (DEC-0116). The evidence checklist accretes from the data, backtesting, and risk sittings, and the promotion gate itself is platform territory.

### QMB

The QMX experimentation and backtesting product: one pure library plus the `qmb` CLI shipped in one wheel, with a Python API door now and an MCP door post-CLI-v1 (DEC-0159). QMB realizes the former reserved **Future backtesting library** entry and is an application-layer product built on QMF — never a QMF roster package and never a central service. A run over recorded evidence carries `world = replay`, minting its own AD-29 replay binding, so replay-derived evidence stays incomparable to live by binding (DEC-0160); world is provenance-derived, so a run reading store-tainted fabricated data resolves to `world = simulated` — a policy rejection for governed evidence until GAP-0048 (DEC-0164). QMB is a **library** and a **CLI**, never an "engine" or "kernel" — QMF is the only framework (DEC-0159, DEC-0169).

### qmf-core

The definitions-only foundational library `COMP-QMF-CORE`. It owns exact primitive direction, asset-neutral nouns, typed refusals, canonical serialization, fingerprints, and compatibility contracts; it owns no broker, event loop, backtest, download, or trading-node runtime.

### qmf-data

The public data-policy and API library `COMP-QMF-DATA`. Middleware ingest, physical persistence, and backup execution are separate internal seams so business rules do not collapse into adapters or stores.

### qmf-indicators

The two-mode indicator library `COMP-QMF-INDICATORS`: one CT-16 contract, batch and streaming conformant modes bound by the equality law, consumer-blind across bots, structure, MIS, and backtesting. Light and heavy are placements of the same contract, not species — heavy configurations run off the trading path, computed once and fanned out (DEC-0126, DEC-0128).

### qmf-registry

The identity, lineage, and registration-gate library `COMP-QMF-REGISTRY`. Its V1 design does not require a universal card or graph database.

### qmf-structure

The QMX-owned causal chart-object library `COMP-QMF-STRUCTURE`, governed by CT-17's lifecycle law: objects minted once at observation, evolved only through append-only lifecycle and interaction records, evidence class identity-bearing, families admitted only under the precise-rule bar (DEC-0129).

### QMF

The reusable Quant Mind Framework toolbox from which QMX applications are built. QMF is not an application or runtime.

### QMF V1 Blueprint

The current documentation scope: qmf-core, qmf-registry, qmf-data, qmf-indicators, qmf-structure, the Venue module, and the Risk module.

### QML

The QMX bot-authoring library: one uv-installable application-layer distribution (`import qml`) built ON QMF contracts exactly as **QMB** is, never a QMF roster package, never a framework, never an engine, and never again a cross-component contract layer (the old load-bearing-stratum role is retired — QMF's contracts are the shared layer now). Its whole surface is three thin things: author-side types and helpers producing the Bot-domain registry artifacts (**Bot definition** CT-33 and **Confluence** CT-34) on qmf-core nouns; the bot runtime protocol hosts invoke (DEC-0177); and the **conformance** gate (DEC-0178). QML mints NO new QMF-ladder (CT-*) shared contract of its own — CT-33 and CT-34 are qmf-registry kinds it authors, and the runtime protocol and conformance contract are QML-local contracts on QML's own AD-5 format-version ladder. No acronym expansion is minted: the corpus never expands QML and the L reads as Library. Plain Python stays first-class forever — an unregistered bot needs zero QML imports to run in QMB or research lanes, and QML conformance is the ticket into governed evidence and Book seats, nothing else. QML imports qmf-core, qmf-registry, and qmf-risk (CT-23/CT-29 types) and NEVER imports qmf-venue; it is pure per AD-15 (no threads, no I/O, no process spawning), every impure step host-owned. QML builds before the trading node and may build alongside QMB, carrying its own SemVer as display-only provenance and consuming the QMF workspace in lockstep (`uv add qml`) (DEC-0180). (DEC-0171, DEC-0184)

### QMX

The operator's broader algorithmic and quantitative trading platform. QMX applications consume QMF libraries and modules.

### qualifying_loss_exit

The bench breaker's input: a virtual-position close that realized a loss at or beyond the declared full-loss distance — the predicate is `realized_r <= -q`, where `q` is a declared UI-editable per-family template variable defaulting to approximately one R (a configuration the operator sets, never a spine constant). Scratches and partial losses do not count by default; breakevens never count under any `q` and are recorded as their own metric. A forced flat or boundary flat counts only if it realized a qualifying loss, so the system's own protection never benches the bot it just protected. `qualifying_loss_exit` is the bench's input; it is never the bare word 'stop-out', and never **venue_liquidation** (DEC-0155).

### R

The canonical original pre-trade risk unit referenced by `registry:original_risk_unit`. R does not mean realized profit, account equity, or post-trade return.

### r_unit_price

The Money-per-`r_multiple` rate that prices one R, fixed at period start unless the Book declares another cadence. In the ratified sizing ladder (units only, no spine values): `loss_runway = book_capital - loss_floor`; `period_loss_budget = loss_runway / runway_periods`; `r_unit_price = period_loss_budget / seat_loss_run_allowance` (superseding FORM-0004, which computed a rate but was mis-named); `position_risk_amount = requested_r x r_unit_price`, frozen at admission. Money-to-R crossings must name `r_unit_price`; an implicit crossing refuses, and only `r_multiple` averages across instruments and accounts (DEC-0154).

### Raw evidence

Source-preserving observations retained without destructive replacement by processed forms and kept available for verification. Retention is controlled by `registry:raw_history_retention_policy`; this glossary does not duplicate its configured value.

### Read-time fold

The rule that a current state is computed by folding an append-only observation stream at read time, never stored as a mutable record that recording must gate on. A structure object's "still valid at T" or "still unmitigated" is a read-time fold over its edge stream under CT-17's read-resolution rule (DEC-0129). A venue order's state — client-submitted, venue-accepted, partially-filled, filled, cancelled, expired, closed-by-venue — is likewise a read-time fold over the recorded venue-observation stream under CT-20's read-resolution rule, never a state machine that gates recording. (DEC-0129, DEC-0137)

### Reconciliation verdicts

The QMF-owned verdict vocabulary — `reconciled | drift | unknown | out-of-lookback` — of an on-demand complete read-back of venue orders, fills, positions, and balance over a stated lookback (equity derived where the venue has no native field). `out-of-lookback` is minted so 'I cannot see that far back' is never read as 'the position closed' (DEC-0158). Reconciliation gates the command pipe only; the sensing pipe never blocks on it. A standing protection intent satisfies only on a `reconciled` verdict showing the scope flat; `drift`, `unknown`, and `out-of-lookback` alarm and hold the intent open without dispatching, so a protection mechanism can never open a position against state it cannot see (DEC-0150). When reconciliation runs and what a verdict triggers are node/BMS authority, referenced only as a pointer (`tracker/trading-node-notes.md`), not QMF's to decide. The reconciliation verdict `unknown` is a distinct notion from the **UNKNOWN** submission outcome (DEC-0137, DEC-0142, DEC-0158).

### Registration

The qmf-registry act that admits a type-specific identity after applicable lineage and gate preconditions are represented. Object kinds are per-kind record schemas, each its own versioned contract sharing a tiny header (kind, contract format version, at-birth parent references, writer, sequence), with the stable id derived from the record's `fp1` fingerprint and kinds addable but never redefined (DEC-0114). Causality-gate evidence and attempt accounting remain `GAP(GAP-0016)` and `GAP(GAP-0017)`.

### resolve_unknown

The explicit typed call by which an application clears an outstanding **UNKNOWN** block on a command stream — `resolve_unknown(command identity, resolution ∈ observed-accepted | observed-absent | operator-attested)` — itself recorded as an observation. The adapter never clears its own block: while an UNKNOWN is outstanding it refuses new commands on that stream, no QMF component retries or invents a terminal state, and the block clears only on this call, never on a reconciliation verdict. The application reaches its resolution from reconciliation read-back evidence. (DEC-0137)

### Risk module

The reusable, account-facing Book and BMS boundary `COMP-QMF-RISK`. Its risk contracts are ratified as `defined-unwired` surface — Book definition (CT-22), risk evaluation (CT-23), binding transition (CT-24), risk-record projections (CT-25), BMS definition (CT-27), Book binding (CT-28), exit record (CT-29), control action (CT-30), control window (CT-31), and performance result (CT-32) — carrying no implementation code and mediated by the composition root; the former risk-reconciliation fence is resolved. The module owns the risk domain; the former Bot-schema pending slots have filled now that the QML sitting landed CT-33 — `footprint_requirements` takes the QL-4 requirement-set shape through the CT-22 format version 2 mint (DEC-0181) and the **prediction linter** is now defined (DEC-0178), both still passing registration and blocking live binding (DEC-0143, DEC-0146, DEC-0147, DEC-0150, DEC-0155).

### Risk contracts (CT-22..25, CT-27..32)

The ratified risk-domain contract surface owned by `COMP-QMF-RISK`, `defined-unwired`: Book definition (CT-22), risk evaluation / bot-to-Book port (CT-23), binding transition (CT-24), risk-record projection join (CT-25), BMS definition (CT-27), Book binding (CT-28), exit record (CT-29), control action (CT-30), control window (CT-31), and performance result (CT-32). These are ratified schema with no code — no implementation authority flows from them, and they ship through the factory pipeline like every other contract; composition-root-mediated, they create no new package dependency edge. Two former `pending(bot-schema sitting)` surfaces — `footprint_requirements` and the **prediction linter** — have filled now that the QML sitting landed CT-33: `footprint_requirements` takes the QL-4 requirement-set shape through the CT-22 format version 2 mint (DEC-0181) and the prediction linter's pinned four-check list is defined (DEC-0178), both still passing registration and blocking live binding (DEC-0143, DEC-0144, DEC-0145, DEC-0146, DEC-0147, DEC-0150, DEC-0155).

### Run loop

QMB's single event-slice loop, driven by an injected frontier clock that is qmf-core's AD-8 Clock protocol and never itself chooses the world. Backtest, replay, and live differ only by which clock and adapters the resolved run-config binds — the loop is never forked. Its identity-bearing sub-phase order is pinned, forming bars are never actionable, and a golden-slice determinism test guards it (DEC-0169).

### Schedulable duties

The venue adapter's periodic session work — heartbeat, token refresh, reconnect, gap replay, verification monitors — declared by the adapter but driven by the application's scheduler, under the AD-15 carve-out: the adapter defines the work, the application runs it, and QMF never spawns threads or background work. Session recovery never resubmits a command. (DEC-0141)

### Sealed-test / untouched-test

Two names for the same split role: `sealed-test` (CT-12's enum member) is the untouched-test split of DEC-0046. CT-12 is the owning contract. (DEC-0046, DEC-0119)

### seat_loss_run_allowance vs bench_consecutive_loss_threshold

The two typed variables that replace the one legacy symbol `B`, which did two unrelated jobs (bench depth in loss events; a divisor in the money ladder). `bench_consecutive_loss_threshold` is a `[count]` in `leash_grammar`, keyed per bot or bot family — the bench's depth. `seat_loss_run_allowance` is an `[r_multiple]` in `money_rules` — the divisor in `r_unit_price = period_loss_budget / seat_loss_run_allowance`. A Book may declare the second derived from the first as declared fingerprinted data, never a hardcoded identity. `seat_r_ceiling <= seat_loss_run_allowance` supersedes FORM-0006, with no money on either side (DEC-0154).

### Secret reference

An opaque minted id standing in for a credential everywhere QMF handles secrets — components handle references, never values. It is minted under AD-9's identity discipline: stable, never reused, never encoding venue, broker, account, environment, or key material; any human-readable label is a separate field held outside evidence, and construction validates opacity (`invalid input` otherwise). A missing, expired, or rejected credential is an `unavailable dependency` refusal carrying the reference id, never the value. The typed carriers are **SecretRef** and **SecretValue**. (DEC-0136)

### SecretRef

The qmf-core typed value carrying a **secret reference** — an opaque minted id — through QMF code. QMF components pass SecretRef, never secret material; values are injected only at the composition root from the deployment environment's protected store (`systemd-creds`-class on the VPS). Distinct from **SecretValue**, which carries actual material and is held only by the **connection manager**. (DEC-0136)

### SecretValue

The qmf-core typed value that carries actual secret material and **never renders it**: repr, str, serialization, and logging all yield the reference id, and a tier-1 secret-scan gate rides `poe check`. Only the **connection manager** may hold a SecretValue in memory, for a session's lifetime, through the core-defined `SecretStore` port; the value never crosses back out. Secrets never appear in repositories, configuration artifacts, docs, `.env` files, CLI arguments, journals, evidence, fingerprints, or logs. (DEC-0136)

### Session epoch

A session-scoped id, distinct from the boot epoch, that rides every venue observation on a **command stream**. Per-writer sequences reset only on boot, never on reconnect, so the session epoch marks reconnect boundaries without breaking the gapless sequence; the sequence cursor is durable through the observation sink. The session epoch is a declared occurrence/display-only field in CT-20's exclusion list, never identity. (DEC-0137)

### SessionWindow

A qmf-core time type for a market session's open span, expressed over Instants and produced by a **market-hours calendar**'s session schedule. Session and trading-day length is data, never a constant a consumer may assume. (DEC-0106)

### Six latency rungs

The named stages of the live-path latency decomposition — tick received, evidence write, indicator update, decision, risk evaluation, order submitted — recorded as AD-13 rungs with no numeric budgets until measured. A latency rung is a monotonic delta within one boot epoch on one machine; a wall-computed rung is refused as a baseline. The adapter owns the arrival and submit stamps for its stages. No rung carries an invented number. (DEC-0138)

### SQS

Spread Quality Sensor, a CT-16 configured producer (a value per evaluation instant), distinct from news control. The V1 formula is the instrument's historical average spread for a named session window divided by its current live spread — 1 is baseline, above 1 tighter, below 1 wider — a ratio against the instrument's own normal, computed as an exact rational over two scaled-integer spreads so no analytic value crosses into a live-money verdict. The score feeds a per-instrument-class hard-block threshold with a hysteresis band, an outlier guard, and a conservative sentinel (undefined, stale, or refused means hard block, never last-known-good). Every parameter is a configurable UI-editable variable with no spine value — thresholds, band, outlier multiple, cadence, baseline window, refit schedule, staleness horizon; recorded corpus numbers are non-authoritative evidence, never defaults (DEC-0157). The sensor computes, the transport carries, the Book's door decides — SQS never sizes, never authorizes, never blocks itself; V1 blocks only. Its baseline is a fingerprinted input artifact (see **SQS baseline**), and instrument class is read from a dated **instrument_class record**, never parsed from a symbol (DEC-0153).

### SQS baseline

The fingerprinted input artifact SQS divides the live spread against — the instrument's historical spread statistic for a named session window — with its own lineage, separate from the producer's configuration identity. It carries its conditioning window (a market-hours calendar identity + session id, identity-bearing), its statistic (mean, median, or a stated quantile — fingerprinted contract surface, never the bare word 'average'), and its refit cadence. A refit mints a new artifact with a `supersedes` edge; the configuration cites a **refit-series identity** plus the refit-policy fingerprint, so a refit under an unchanged policy does not fork identity while a change to the refit policy does — without that split a daily refit would fork the decay cohort daily. A live binding requires a present baseline artifact, checked at bind time among the admission Layer-2 prerequisites (DEC-0153).

### Source (provenance noun)

A core provenance noun, orthogonal to **VenueId**: a provider you can trade at is a Venue, while a provider you only read from is a source. Every external fact carries event-time, known-at, source, and revision. Tick sources — for example Dukascopy history versus a broker feed — are separately identified, and disagreements between sources stay visible via `corroborates` and `disagrees-with` lineage edges, never merged away. (DEC-0117, DEC-0119)

### Source observation (CT-10)

The Data-owned governed observation boundary. `COMP-QMF-DATA-INGEST` and `COMP-QMF-VENUE` produce CT-10 into `COMP-QMF-DATA`; Indicators, Structure, Venue, and Risk read the governed boundary through their dependency on Data rather than consuming directly from Data-Ingest. Every external fact carries event-time, known-at, source, and revision, with corrections appended and never overwriting evidence (DEC-0117). Intake is idempotent, keyed on `(source, source-native id, revision)` (DEC-0119), and duplicate tick sources stay separately identified with bid and ask preserved and disagreements kept visible via `corroborates` and `disagrees-with` edges (DEC-0119).

### standing intent

A risk-non-increasing act journaled before dispatch, so the intent exists even if nothing reaches the venue — 'is this account under a standing flatten intent' is a read-time fold, restart-proof by construction. On reconnect the node re-evaluates every standing intent against reconciled state and, if still unsatisfied, issues a new command with a new identity: re-deciding is not retrying, and the intent never time-expires. A flatten intent satisfies only on a `reconciled` verdict showing the scope flat; a command outcome never satisfies an intent, and `drift`, `unknown`, and `out-of-lookback` verdicts alarm and hold the intent open without dispatching. A protection act refused by an UNKNOWN block never evaporates — it stands as a standing intent and is re-decided when the block clears (DEC-0150, DEC-0158).

### Standing object

A structure object derived from configuration rather than market observation — an a-priori level such as a round-number grid line. A standing object declares observed-at equal to its configuration instant, which keeps the causality law total: every object has an honest first-derivable instant even when no market data produced it. (DEC-0129)

### state_carry

The mandatory per-counter declaration every binding record carries, stating for each of ledger, cycle, budget, bench_counter, and exposure whether it `carry`s or `reset`s at the new binding. Carry is legal only under a human-signed **carries-ledger** edge; what carries is declared, never inferred. A tuple change mints a new binding, and `state_carry` is how the new binding says what money-state and counters travel with it (DEC-0143, DEC-0158).

### Store-before-discard rotation

The rule that where a venue rotates refresh material on use, the new secret is stored (atomic replace) **before** the old is discarded. A failed store after rotation is both an alarm and a command-pipe block (`unavailable dependency`, after-condition = successful store or operator re-provision), while the sensing pipe stays unaffected; where the venue already invalidated the old material, the session is marked degraded and the **compromise drill** triggers. (DEC-0136)

### Store-to-Backup input (CT-26)

The internal boundary from `COMP-QMF-DATA-STORE` to `COMP-QMF-DATA-BACKUP`. Backups are nightly, encrypted, versioned, and off-machine to an object-storage bucket, with automated sample-restore tests and a periodic full-restore rehearsal, and QMF provides the backup, restore, and verify primitives while applications own schedule and execution (DEC-0118). Raw originals and lineage are kept forever and time-series is partitioned by source, instrument, and time window (DEC-0118); the numeric retention, recovery objectives, and verification cadence await the node/ops sitting. CT-26 does not itself assert successful recovery.

### Stop-out

The bare word 'stop-out' is banned vocabulary — it once conflated two unrelated events. Use **venue_liquidation** for the broker's margin liquidation (cTrader's own 'stop out' meaning, verified against its glossary), **qualifying_loss_exit** for the bench breaker's input (a close that realized a loss at or beyond the declared full-loss distance), or the named close-reason member `protective_stop_fill` for QMX's protective-stop sense. Mechanism and outcome are separate fields on an exit record, so no rule is ever written over the mechanism alone (DEC-0155, DEC-0147).

### Superseded-by-fill

The qualifier on a `rejected-by-venue` outcome when a `cancel_order` resolved by read-back is contradicted by a fill: a cancel is `accepted-by-venue` only if the read-back also shows no fill for that order at or after the cancel's submit stamp; otherwise it resolves `rejected-by-venue (superseded-by-fill)`. Command outcome and order state are separate streams — an order's terminal state is decided by fills and venue lifecycle events only — and this rule is why an outcome is never derived from absence alone. (DEC-0137)

### Tick

An asset-neutral qmf-core market noun for a market observation. Tick sources are separately identified, with bid and ask preserved alongside source timestamps and disagreements kept visible via `corroborates` and `disagrees-with` edges, never merged (DEC-0119). The venue depth surface is a Level-2 resting-liquidity book with no Level-3 tape, recorded as the verbatim wire payload; symbol metadata is declared CT-18 instrument-metadata surface (DEC-0135, DEC-0138).

### strategy family

An opaque operator-minted id under AD-9's discipline plus a dated registry metadata record — the SAME machinery as an **instrument_class record** (a kind under CT-06's addable-kinds law, no new CT number). A strategy family is a KEYING TOKEN WITH NO AUTHORITY: it is the key the ratified law already reaches for — a Book's exit_policy declares an ExitLogicRef per family, `q` and `bench_consecutive_loss_threshold` are per-family variables, and the paper starting balance is family-scoped. Every **Bot definition** declares EXACTLY ONE family id, a deliberate cardinality-one ruling: a family is an attribution key, and one bot keyed to two families would partition every per-family variable and exit-policy resolution two ways. A Book's exit_policy entries key by family id and MAY declare ONE catch-all default entry (ratified into the CT-22 format mint, DEC-0181), with the CT-29 exit record keying the RESOLVED entry (explicit-or-catch-all); a bot whose family resolves no entry fails the **prediction linter** (DEC-0178). The old ArchetypeSpec's constraint powers (permitted feature families, permitted timeframes, mutation allowances) are NOT revived — constraining is the Book's job. **archetype** is the retired alias. (DEC-0176)

### Structure family

A **type of chart object** — the word "family" in QMF means exactly this and nothing else: never a strategy, bot, or Book category, and never a trading-school name (L32). Geometry is family-declared and open (point, level, zone, span, distribution, graph). A family ships into the governed library only when its confirmation rule states "confirmed the moment X happens" with X knowable at that instant; the seed candidates (`registry:structure_seed_family_candidates`) hold no privilege over operator-authored families, which are first-class peers via the extension shape. (DEC-0129, DEC-0132)

### Trading Node

A later QMX application that owns live-trading runtime and orchestration. The Trading Node is not qmf-core and is outside QMF V1 documentation scope.

### TradingDate

A qmf-core time type distinct from **CivilDate**. A TradingDate carries its calendar identity and version in-band; equality is defined only within one calendar identity, and comparing TradingDates across calendar identities is a typed refusal. A TradingDate derives only from a rollover rule — a market-hours calendar or a day-boundary calendar — never from formatting an Instant, and is never a causality proxy, since causality is compared on Instants only. (DEC-0106)

### treasury boundary event

A reserved record kind — `sweep | refund | re_seed | paper_epoch_reset` — through which money moves at a Treasury boundary: no money moves without one. A boundary event never closes a position and never re-bases a frozen R; every other money boundary (rollover, sweep, re-seed, paper flip) leaves positions alone, so a money-accounting boundary is never itself a flatten trigger (DEC-0158, DEC-0150).

### Trigger

The **confluence leg** role (`trigger`) that represents the trade-entry event: a producer binding plus optional declared parameters, its satisfaction condition living in the Python logic in V1 (DEC-0175). Any structure evidence it consumes is governed by CT-17's lifecycle law (DEC-0129).

### Two-phase wiring

The fixed wiring order for an adapter's capability surface: the **capability declaration** is present at construction (importable without credentials), and the **venue-observation profile** must exist before the first command and before any evidence-bearing decode. A `measured-at-connection` capability is `unavailable dependency` until its profile exists, and consuming a measured-but-unverified capability in evidence-bearing work is a `policy rejection`. (DEC-0138)

### Typed close scope

The required scope carried by `close_position` and `close_all`, one of `account | account-binding | instrument-within-binding`. CT-18 declares which scopes a venue supports natively; an unsupported scope is an `unsupported capability` refusal, never emulated at a wider scope. (DEC-0137)

### Typed refusal

A versioned machine-readable failure outcome shared across every public QMF boundary: an operation succeeds or returns a typed refusal carrying a category, machine-readable context, and retryability (yes, no, or after-condition). The seven categories are invalid input, unsupported capability, unavailable dependency, stale evidence, policy rejection, transient venue failure, and storage failure. Categories are addable in later versions but never redefined. Public boundaries return refusals as result unions; exceptions are reserved for programmer error and never carry a refusal across a package boundary. Value-type construction is one pattern everywhere: an unchecked constructor for trusted internal use plus a validating `try_create` factory returning value-or-refusal. (DEC-0109)

### unit-kind vocabulary

The closed, addable-never-redefined set of unit-kinds that makes a second FORM-0006 undeclarable: `money(currency) | price-delta(instrument) | quantity(unit) | value-factor(instrument, currency) | r-multiple | rate(money-per-r) | count | dimensionless-ratio | duration | instant`. Every declared variable carries a unit-kind; every formula declares the unit-kind of each input and its output; a symbolic checker refuses on mismatch, and addition, subtraction, and comparison require identical unit-kinds and tags. Unit-kind additions are spine amendments only, never per-Book. The dead FORM-0006 is kept as the checker's permanent negative case — a dead formula that can still be typed is a dead formula that comes back (DEC-0154).

### UNKNOWN (outcome state)

A submission outcome that is a **state, never an error**: the result of a transport error, timeout, or disconnect, and the outcome of any path the CT-18 error table does not resolve to `rejected-by-venue`. An UNKNOWN is minted as an explicit observation carrying its trigger (`timeout | transport-error | disconnect`), the monotonic elapsed measurement, the wall receive instant, and the submission deadline in force (a declared, application-injected adapter parameter under do-not-default). While an UNKNOWN is outstanding the adapter refuses new commands on that **command stream**; no component retries, assumes an outcome, flattens, or invents a terminal state, and the block clears only through an explicit **resolve_unknown** call. The UNKNOWN outcome is a distinct notion from the reconciliation verdict `unknown`. (DEC-0137)

### value-factor

The tick/point value unit-kind — `value-factor(instrument, currency)`, money per price-delta per quantity — sourced only from venue instrument-metadata snapshots as an exact rational; an absent value factor is an `unavailable-dependency` refusal, never a silent conversion. It is the factor in the reference worked example `original_risk_amount = original_risk_distance x quantity x value_factor` that ships with the unit-kind vocabulary (DEC-0154).

### Venue

An external execution or market-data destination. VenueId is operator-minted, opaque, and stable — a distinct broker or legal entity is a distinct venue even on shared infrastructure (DEC-0107); the capability shape is CT-18's two artifacts, the static capability declaration and the per-`(VenueId, account)` venue-observation profile (DEC-0138).

### Venue module

The middleware seam `COMP-QMF-VENUE` for cTrader Open API in Python and later venue adapters. The module translates capabilities, commands, events, sessions, and refusals; it does not own trading permission or risk policy.

### Venue-native identity key

The declared key every CT-20 venue observation carries — the AD-21 `(source, source-native id, revision)` idiom — so gap-replay redelivery deduplicates under the fingerprint's idempotent split. Receive stamps, monotonic values, epochs, and `correlation_id` are declared occurrence/display-only in CT-20's explicit exclusion list; fill price, fill quantity, the venue instant, and the receive instant are mandatory identity fields of a fill observation. (DEC-0137)

### Venue-observation profile

The second artifact of an adapter's capability surface (the first is the **capability declaration**): per `(VenueId, account)`, produced post-connect by the **first-connection verification suite**, append-only with `supersedes` edges, holding every measured fact and verdict. It is occurrence/provenance only, never identity-bearing downstream, so measured facts never split artifact identity across accounts. A `measured-at-connection` capability is `unavailable dependency` until its profile exists. (DEC-0138)

### Venue-scoped market-hours calendar identity

The **market-hours calendar** identity minted from a venue's daily-bar boundary once that boundary is measured and verified per broker — its identity is the rule set, so a measured boundary qualifies. It gives venue-native bars a legal **BarSpec** anchor. Until the boundary is measured, venue daily bars are ungoverned observations, never assumed aligned to QMF's own forex 17:00-New-York accounting rule (`registry:forex_rollover`), which stays independent of venue bars. (DEC-0138, DEC-0141)

### venue_liquidation

The broker's margin liquidation — cTrader's own 'stop out' meaning, verified live against its glossary — reserved for exactly that event and never written as the bare word 'stop-out'. It is one **close reason** member, distinct from **qualifying_loss_exit** (the bench breaker's input) and from `protective_stop_fill` (QMX's protective-stop sense). Mechanism and outcome are separate fields on an exit record, so a venue_liquidation may realize any sign and no rule is written over the mechanism alone (DEC-0155).

### Verify-or-refuse

The adapter obligation attached to every undocumented or measured-per-broker venue behavior: assert the fact at connection and refuse the dependent evidence on mismatch rather than assume a default. An unverified spot-timestamp unit refuses spot evidence, an absent `moneyDigits` is a refusal never a default of 2, a `pipSize` formula is validated not assumed, and a measured-but-unverified capability used in evidence-bearing work is a `policy rejection`. The **first-connection verification suite** is verify-or-refuse throughout. (DEC-0138)

### veto path vs suppression path

Two symmetric accounting paths for actions that did not execute, never merged. A **veto** is a door refusal *before* authorization: it mints a decision event on the veto path carrying the refusing-door identity, the would-have-been action fingerprint, and the controlling evidence fingerprint. A **suppression** is an already-authorized action discarded because a higher authority won: it carries the suppressing and suppressed authorities, the would-have-been action referenced by its control-action record fingerprint, and the arbitration record. A command identity is minted only at submission, so no phantom command record exists for either. Performance results carry both veto accounting and suppression accounting, so neither the doors nor arbitration ever read as decay (DEC-0150, DEC-0151, DEC-0155).

### virtual (Book) position vs venue position

Two distinct notions of a position, never conflated. A **venue position** is observation-derived under the venue's declared `netting | hedging` model — what the broker reports. A **virtual (Book) position** is a fold over fills joined by declared command identity — binding-scoped, Bot-attributed, minted at admission, carrying the frozen R faces — and is the unit of exit records, whole-trade attribution, and the bench fold. Every risk record names which of the two it references; where the account is netted, the fill-to-virtual-position attribution rule is a mandatory Book declaration whose absence is a bind-time policy rejection (DEC-0154, DEC-0155).

### Warm-up

An integer count of completed input observations in the input series' own sample unit that a configured indicator requires before it emits governed output — identical across batch and streaming modes and at least the arithmetic reference's lookback. Warm-up feeds purge and embargo widths together with a structure family's **confirmation delay**, so a split manifest excludes samples that depend on unavailable history. (DEC-0126)

### window kinds

The kinds of protection window a control-window record (CT-31) may carry, addable never redefined, each Book declaring which it enables. Three are ratified: `news`; `daily_dead_zone` (the daily band in which no session is meaningfully in the market); and `session_handover_buffer` (the pause around a session handover, declaring its anchor side `pre-close | post-open | both`). Both dead-zone kinds exist and are different things. Every kind is calendar-derived (market-hours calendar identity + tzdata, never device or broker location) and therefore absent for 24/7 markets. A window blocks new entries on the instruments in scope and nothing else — never an exit, a protection amendment, a protection action, or observation; widths, anchors, and buffers are configurable UI-editable variables with no spine value (DEC-0152, DEC-0157).

### World

The world label carried by every computed result entering evidence, and one of the identity parts of a result label (DEC-0110, DEC-0131). Three values exist. `live` is real venue clocks and quotes with real or demo money — the **Account** role, not the world label, carries money-reality, so paper and demo runs are `world = live` and stay comparable to live for alpha-decay sensing. `replay` is a data-driven injected clock over recorded history (real UTC instants; implementable today). `simulated` is synthetic data and is reserved but unusable in V1: writing `world = simulated` into governed evidence is a `policy rejection` typed refusal until `GAP(GAP-0048)` defines simulated-time typing — the QMB sitting ruled the fidelity seams and reaffirmed this refusal (DEC-0164). A non-live world may never write into the live evidence namespace, and factory sandboxes never produce timestamps that enter an evidence store; storage separation — not identity distinctness alone — delivers world separation, and data rooms are instantiated per world so a cross-world read is a `policy rejection`. (DEC-0110, DEC-0117)

### WriterId

A first-class qmf-core noun: a stable, durable writer identity minted per `(machine, role, stream)` and accompanied by a boot/epoch id, so a restart is visible without changing writer identity. Every record stream carries a per-writer strictly-increasing sequence, and the tie-break `(instant, writer, sequence)` is a replay-determinism ordering key with no causal meaning — causality tests refuse at equal instants rather than tie-break. The identity of a stored record is its `fp1` fingerprint, never its timestamp; timestamps are never primary or dedup keys. A persisted monotonic reading is an opaque boot-scoped diagnostic carrying its boot/epoch id, never compared across boots or machines and never rendered as a time. The one-writer-per-stream concurrency rule (unlimited readers) binds the holder of a WriterId. (DEC-0106, DEC-0113)

## Retired or prohibited names

### archetype

Retired name. Use **strategy family** — a keying token with no authority, exactly one per **Bot definition**, that a Book's exit_policy keys by. The old ArchetypeSpec's constraint powers (permitted feature families, permitted timeframes, mutation allowances) are NOT revived — constraining is the Book's job, and agent-mutation governance is agentic-sitting territory (DEC-0176, DEC-0184).

### Backtesting engine

Retired name. Use **QMB** — the realization of the former **Future backtesting library** entry. "engine" is banned vocabulary for it — QMB is a library and a CLI, never an engine or kernel — and a permanent central engine is rejected (DEC-0159).

### BotSpec

Retired name. Use **Bot definition** — the CT-33 declaration artifact. The old BotSpec's `exit_logic` slot is deliberately dead: the Bot definition carries no exit_logic field, and exit policy lives in the Book's exit_policy per **strategy family** (DEC-0179, DEC-0173).

### Broker Exam

Retired name. Use **Venue module** for connection and **QMB** for parity work (the parity contracts themselves remain open under `GAP(GAP-0048)`).

### DPR

Dead legacy mechanism. DPR must not appear as a live QMF risk variable or contract.

### FORM-0006

Dead legacy formula. FORM-0006 is dimensionally broken and must not be implemented.

### Kernel

Retired name. Use **qmf-core** for the definitions library and **Trading Node** for application runtime.

### Minimal core

Retired name for the whole agreement. Use **QMF V1 Blueprint**; qmf-core remains intentionally small.

### Program and Campaign

Rejected prop-firm abstractions. Future prop-firm behavior, if revived, is modeled through a new Book after a fresh ruling.

### PRS

Dead legacy mechanism. PRS must not appear as a live QMF performance or risk contract.

### Snapshot Quality Sensor

Incorrect expansion of SQS. Use **SQS**.

### Simulator

A separate, deferred product UI for exploring Bot-by-Book conditions that will consume **QMB** rather than reimplement it (DEC-0159). Simulator does not mean the QMF data or venue layer and is outside QMF V1.
