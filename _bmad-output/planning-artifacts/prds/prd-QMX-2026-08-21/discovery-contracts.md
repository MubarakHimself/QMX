# PRD Discovery — Contracts Extract (CT-01 .. CT-34)

Source: `docs/contracts/*.yaml` + `docs/registry/variables.yaml`. One entry per contract.
Scope: PRD-relevant, capability-level obligations only (what the platform must guarantee).
Field-level schema detail deliberately omitted.

---

## COMP-QMF-CORE — value & identity primitives

### CT-01 — Money, price, and quantity value contract
**Owner:** COMP-QMF-CORE.
**Guarantee:** All money, price, and quantity values are exact scaled integers with a declared per-value scale; binary float is banned anywhere on the "money path" (any value transitively feeding an order quantity, price, P&L, or balance). Foreign venue floats are evidence only, converted to scaled integers at named boundaries with a declared rounding mode; every value carries a unit-kind from a closed vocabulary, and equal value implies equal fingerprint by construction.

### CT-02 — Exact time and trading-calendar contract
**Owner:** COMP-QMF-CORE.
**Guarantee:** Time is int64 UTC nanoseconds (range 1677–2262, checked arithmetic, no wrap); civil-date vs trading-date are distinct types; wall vs monotonic clocks are type-separated and injected via a Clock protocol so results are identical across server moves, DST, tzdata updates, and clock corrections. Market-hours / day-boundary / news calendars are versioned rule-sets whose identity (plus pinned tzdata) enters fingerprints.

### CT-03 — Instrument and venue identity contract
**Owner:** COMP-QMF-CORE.
**Guarantee:** Instrument identity is `(venue, opaque venue symbol)`, never parsed; Venue and Account are first-class nouns; VenueId is operator-minted, opaque, stable, never reused. Multi-broker operation and broker migration are normal cases (a migration is a new venue + accounts, old evidence untouched); aliases/renames are separate dated records that never rewrite history.

### CT-04 — Typed refusal contract
**Owner:** COMP-QMF-CORE.
**Guarantee:** Every public operation either succeeds or returns a typed, machine-readable refusal carrying one of exactly seven categories (invalid-input, unsupported-capability, unavailable-dependency, stale-evidence, policy-rejection, transient-venue-failure, storage-failure), structured context, and a retryability answer. Refusals are returned (not raised) across boundaries; exceptions are reserved for programmer error. Categories are addable, never redefined.

### CT-05 — Version, fingerprint, and result-label contract
**Owner:** COMP-QMF-CORE.
**Guarantee:** Every semantic definition and computed result has a deterministic, versioned identity: the pinned `fp1:sha256` fingerprint over canonical bytes, two never-conflated version ladders (package SemVer = display-only; per-artifact integer format version = identity), and a result label (producer identity, format version, input fingerprints, evidence time range, computation identity, evidence class, world). One qmf-core implementation computes all identity; a true hash collision is refused and alarmed. `world ∈ {live, replay, simulated}`; simulated is reserved-unusable in V1.

---

## COMP-QMF-REGISTRY — registration, lineage, causality

### CT-06 — Registry registration contract
**Owner:** COMP-QMF-REGISTRY.
**Guarantee:** Artifacts register as per-kind versioned records whose stable id derives from their fp1 fingerprint (never minted), so identical work from two sandboxes deduplicates. Kinds are addable, never redefined; occurrence facts (created-at) are excluded from identity. Promotion is a human-signed immutable occurrence card with a mandatory plain-words summary that is itself an identity field. Registration needs no database server.

### CT-07 — Registry lineage-edge contract
**Owner:** COMP-QMF-REGISTRY.
**Guarantee:** Lineage accruing after a record's birth lives only in append-only typed edge records referencing fp1 fingerprints (supersedes, promoted-from, corroborates, disagrees-with, confirmed-as, enacts, continues-performance, carries-ledger, branches-from, etc.). Edges are immutable JSONL, never rewritten; source disagreements stay visible and are never merged away. `carries-ledger` (moves money) and `continues-performance` (asserts track record) are separate human-signed edges, never inferred from each other.

### CT-08 — Causality and attempt-gate evidence contract
**Owner:** COMP-QMF-REGISTRY. **(Unresolved / deferred — version null, GAP-0005/0016/0017.)**
**Guarantee (intended):** Look-ahead causality checking and immutable registration-attempt accounting are registration preconditions. Full schema, cutoff comparison, attempt budget/scope/reset, and override semantics are deferred to the backtesting sitting — artifacts registered before then carry no causality evidence.

### CT-09 — Registry persistence contract
**Owner:** COMP-QMF-REGISTRY.
**Guarantee:** Registry records + lineage edges persist through qmf-data's CT-11 append-store (the single ratified inter-library edge), append-only, keyed on fp1, no database server. The registry room is one of qmf-data's room-roles under the same retention/backup/migration law, instantiated per world; cross-world reads refuse.

---

## COMP-QMF-DATA / DATA-INGEST / DATA-STORE / DATA-BACKUP — evidence persistence

### CT-10 — Source-observation and bitemporal fact contract
**Owner:** COMP-QMF-DATA.
**Guarantee:** Every external fact is stored as bitemporal, source-attributed evidence — event-time + known-at + source + revision — with foreign timestamps and foreign money stored verbatim at declared scales/zones. Corrections are appended annotations, never rewrites; a read-only "source" is orthogonal to a tradeable "venue" and never conflated. The framework never loses when, or from whom, a fact was learned.

### CT-11 — Evidence-persistence contract
**Owner:** COMP-QMF-DATA.
**Guarantee:** Evidence persists through a QMF-owned append-store over swappable engines (Parquet/DuckDB/SQLite/JSONL), no database server. Only raw-archive and journal formats are evidence-bearing; analytics are rebuildable views (an engine break costs a rebuild, never evidence). Seven room-roles instantiated per world with cross-world reads refused; anything a result label cites is retained forever; the 12-month no-peek seal is enforced at every read boundary.

### CT-12 — Dataset release, split, and holdout contract
**Owner:** COMP-QMF-DATA.
**Guarantee:** Every dataset split is a fingerprinted, time-ordered, non-overlapping manifest pinning exactly one calendar identity. Research data splits into train/validation/sealed-test; the newest sealed window is a no-peek lock enforced as a read-boundary refusal (one logged final look only), with mandatory purge/embargo widths so research never consumes its own held-out evaluation period or leaks across the knowledge-time boundary.

### CT-13 — Durable journal-evidence contract
**Owner:** COMP-QMF-DATA.
**Guarantee:** Durable operational/research journal evidence is N append-only per-writer streams (one writer per stream, gapless sequence, a gap signals loss), recording exactly seven event types (decision, order, fill, risk-transition, promotion, data-quality, control-action). Journals are distinct from arbitrary logging, carry no runtime event bus, and are instantiated per world; entity journals (Book/BMS/per-bot) are read-time projections, never additional writers.

### CT-14 — Off-machine backup boundary contract
**Owner:** COMP-QMF-DATA-BACKUP.
**Guarantee:** QMF provides encrypted, versioned, off-machine backup/restore/**verify** primitives (verification — sample-restore tests + periodic full-restore rehearsal — is first-class, never optional); a backup never mutates the only copy and every migration backs up first. Restored data still enforces the 12-month seal. Schedule and execution (and RPO/RTO/retention/key custody) are application/ops-owned.

### CT-15 — External data-source adapter contract
**Owner:** COMP-QMF-DATA-INGEST.
**Guarantee:** A QMF-owned request/response port for external providers defines source contracts, normalization, validation, and idempotent intake keyed on `(source, source-native id, revision)` — a revision is a new artifact, never a collision. Tick sources are separately identified (Dukascopy vs broker feed) with bid/ask and source timestamps preserved; source disagreements stay visible; scheduling/retries/lifecycle stay application-owned. Venue market data enters here as source observations (the venue is also a source).

### CT-26 — Store-to-backup input boundary
**Owner:** COMP-QMF-DATA-STORE.
**Guarantee:** An internal data-to-data seam presenting a store's room contents to the backup primitive as a consistent, restorable, read-only input covering every room-role (incl. the registry room), per world, never mutating evidence; cross-world backup reads refuse.

---

## COMP-QMF-INDICATORS / STRUCTURE — analytics producers

### CT-16 — Two-mode indicator contract
**Owner:** COMP-QMF-INDICATORS.
**Guarantee:** One indicator contract with two conformant modes (batch and streaming) so research and the live path compute the same numbers by construction, with identity equal to the entire declared configuration. Outputs are full-length, index-aligned, presence-mapped (no NaN/sentinels); only as-of alignment is legal for governed evidence (no look-ahead fill); canonical arithmetic wraps the pinned reference (TA-Lib) or is QMX-canonical; light-vs-heavy is a per-configuration benchmark-proven verdict. Composition is law (any output can feed any configuration).

### CT-17 — Causal structure lifecycle contract
**Owner:** COMP-QMF-STRUCTURE.
**Guarantee:** QMX-owned chart-object families emit causally justified structure evidence: an object is minted once at observation and never mutated; it evolves only through append-only lifecycle/interaction edges. Evidence class (confirmed/unconfirmed/provisional) and knowledge time are first-class; a family ships to governed evidence only when its confirmation rule states "confirmed the moment X happens" with X knowable at that instant. Emission invariant (anchor ≤ observed-at ≤ confirmed-at ≤ invalidated-at) is checked in-component; no privileged families — operator-authored families are first-class peers.

---

## COMP-QMF-VENUE — execution boundary

### CT-18 — Venue capability-discovery contract
**Owner:** COMP-QMF-VENUE.
**Guarantee:** Every venue is described by two artifacts — a static, credential-free capability declaration (identity-bearing for dependent decodes) and a per-(VenueId, account) measured venue-observation profile — so a caller learns exactly what a venue supports before invoking it, and no measured fact splits artifact identity across accounts. Invoking anything undeclared refuses; a first-connection verify-or-refuse suite measures daily-bar boundary, bar basis, pip formula, money exponent, and timestamp units; consuming a measured-but-unverified capability in evidence work refuses.

### CT-19 — Venue command contract
**Owner:** COMP-QMF-VENUE.
**Guarantee:** A venue-neutral command contract with exactly five typed kinds (place_order, cancel_order, close_position, close_all, amend_protection), each on qmf-core nouns with no free-form payload. Every well-formed submission resolves to exactly one of four outcomes (accepted-by-venue, rejected-by-venue, denied-locally, UNKNOWN); uncertainty is an explicit state, never assumed/retried/flattened/invented. No component retries or invents terminal state on UNKNOWN; protective/close commands dispatch ahead of place_order; amend_protection is contract-constrained to risk-non-increasing changes. No partial close in V1.

### CT-20 — Venue event and reconciliation contract
**Owner:** COMP-QMF-VENUE.
**Guarantee:** Every inbound venue event is recorded verbatim and journaled **before** any interpretation; the order-state machine is a read-time fold over that observation stream (never a gate on recording). Command outcome and order state are separate streams — an order's terminal state is decided only by fills/venue lifecycle events. Reconciliation is an on-demand read-back over a mandatory declared lookback with verdicts reconciled/drift/unknown/out-of-lookback; it gates the command pipe only, never the sensing pipe. Fill identity fields are mandatory.

### CT-21 — Venue secret and session boundary contract
**Owner:** COMP-QMF-VENUE.
**Guarantee:** QMF components handle only opaque secret references; the adapter's connection manager alone holds secret values in memory through an injected SecretStore port; a SecretValue never renders (repr/str/serialize/log all yield the reference id). Credentials never enter code, evidence, logs, fingerprints, or sandboxes; one live refresher per credential; rotation is store-before-discard; missing/expired credentials are typed refusals carrying only the reference id; a compromise recovery drill is documented and tested with demo credentials only.

---

## COMP-QMF-RISK — Book/BMS, sizing, control, evidence

### CT-22 — Book definition (template) contract
**Owner:** COMP-QMF-RISK. *(format version 2)*
**Guarantee:** One Book VERSION is a structured configuration artifact (JSON-Schema-class, ten declared sections) whose every variable carries a unit-kind, an exact-rational value, a `ui-editable` flag, and an `admission_impact` — so a Book's meaning lives inside its fp1 identity, a UI knows what it may change, and a bound account inherits exactly the declared risk/money semantics. Numbers live inline and are identity-bearing; "blank blocks live money" (any not-yet-ruled threshold registers and binds non-live but refuses live binding); versioning is git-logic (branches-from graph, current pointer); a changed number → new identity → new binding → fresh money unless a signed carries-ledger edge is present. Book owns admission/sizing/doors/leash; authority order `bot→book→BMS→operator` may never invert.

### CT-23 — Risk-evaluation door contract (bot-to-Book intent port)
**Owner:** COMP-QMF-RISK. *(format version 2)*
**Guarantee:** The single bot-to-Book inbound door carries exactly two typed intent families (entry, exit) plus declared evidence slots. `requested_r` is Book-resolved, never bot-supplied (a bot proposes, never sizes); an admitted entry must resolve to a declared full-loss price (no price → no admission — a strategy with no planned loss point cannot trade). Exit intents are risk-monotonic by construction (only close_full and tighten_protective_stop; no partial close, no widening stop, no size increase); every intent and door decision mints a journal-bearing recorded reason.

### CT-24 — Book mode and binding-transition contract
**Owner:** COMP-QMF-RISK.
**Guarantee:** An append-only binding-transition record carries a Book between exactly two modes LIVE and PAPER (no Bot twins ever); current mode is a read-time fold, never a stored field. Every trigger declares routes-to-paper vs blocks-paper; routing to paper is never a way around a control (a protection window/kill switch blocks paper exactly as live). Paper money is frozen evidence that never crosses the money boundary; return-to-live is automatic only for clocked mechanical clears, otherwise requires an operator signature (paper performance never authorizes a return).

### CT-25 — Risk and entity journal-projection contract
**Owner:** COMP-QMF-RISK.
**Guarantee:** Entity journals (Book, BMS, per-bot logbook) are read-time projections over writer-scoped journal streams keyed by entity identity — an entity holds no WriterId and writes no stream. Risk-authored events carry Book/binding/bot identity; venue-authored events join through the command record's content fingerprint (a pinned versioned join) so Book identity never has to leak into the venue payload. Paper and live are separated by construction; the decision event carries a mandatory closed outcome (authorized/refused-by-door/suppressed).

### CT-27 — BMS definition (template) contract
**Owner:** COMP-QMF-RISK.
**Guarantee:** One BMS VERSION under the same configuration-artifact grammar as CT-22, holding the account-facing supervising layer's authority (accounting, constraints, KSA policy posture, reporting) and the control-rank table (one per command stream). One BMS instance per account serving many Books; `BmsInstanceId` is content-derived. Control ranks are a total order with uniqueness enforced at admission; a Book whose control policy contradicts the BMS table refuses at bind time.

### CT-28 — Book binding record contract
**Owner:** COMP-QMF-RISK.
**Guarantee:** One append-only binding record couples a Book instance to a BMS instance on one account at one venue, tuple `(BookInstanceId, BmsInstanceId, VenueId, AccountId, world)` aligned with the `(VenueId, account)` command stream. Each binding carries a mandatory per-counter `state_carry` (carry|reset) declaration — carry legal only under a signed carries-ledger edge; the binding epoch is the record's own fingerprint. A bind-time capability check (venue capabilities, settlement currency = accounting_currency, SQS baseline present, rank-table non-contradiction, latency baseline) refuses at bind time, never at trade time.

### CT-29 — Exit-record contract (one record per virtual-position close)
**Owner:** COMP-QMF-RISK.
**Guarantee:** One immutable exit record per virtual (Book) position close, carrying frozen R faces (original_risk_distance, original_risk_amount), fill references, realized P&L, an identity-bearing cost-component set, a single-sourced `realized_r`, exactly one typed close reason from the closed-addable taxonomy, and the closing authority + arbitration reference. Recording precedes interpretation (an exit record must persist before any later same-seat intent, else stale-evidence refusal); mechanism and outcome are separate fields; the bench counter is a read-time fold, not a mutable counter. Collection starts now because it cannot be back-filled.

### CT-30 — Control-action contract
**Owner:** COMP-QMF-RISK.
**Guarantee:** A bounded set of typed control actions (suspend_new, drain, flatten, resume) each issued by a named authority at a resolved scope, journaled **before** dispatch as a standing intent, arbitrated at exactly one point per command stream by a BMS-declared rank. The exit-preservation invariant is spine law: **no control action, of any authority, at any scope, may ever block a risk-reducing act** — blocking is entries-only. Flatten authority is closed (operator always; Book policy only via pre-declared triggers; kill-switch class; never the venue adapter). Kill switch (global authority) and kill line (per-Book capital floor) are named apart, never merged; resume is operator-only.

### CT-31 — Control-window contract
**Owner:** COMP-QMF-RISK.
**Guarantee:** One control-window contract for every no-trade band. A window is carried as two instants (never an offset), a resolved instrument scope, a kind, and a reason class; three calendar-derived kinds (news, daily_dead_zone, session_handover_buffer) each block **new entries only** (live and paper alike) and never block an exit, a protection amendment, a protection action, or the recording of evidence. Instrument scope resolves through dated currency-exposure records (never parsed from a symbol); revisions widen-never-shrink; fail-closed (uncertain window blocks, no live skip button); the blocked decision is still journaled on the veto path.

### CT-32 — Performance-result container contract
**Owner:** COMP-QMF-RISK. *(also produced by COMP-QMB)*
**Guarantee:** One performance-result container serves both admission-bar evidence and the analyst's report: full result label + account role, a fingerprinted declared population (bindings/roles/instruments/decay-cohort key, never prose), a declared period with a knowledge-time bound, an ordered unit-kinded measure set, suppression and veto accounting, and a fingerprinted baseline pointer. Measurement publishes, never acts (no score/rating/tier/weighted composite may express a result); a paper role may never gate live money; a metric is a governed producer whose arithmetic change is a format-version mint.

---

## COMP-QML (authored) / COMP-QMF-REGISTRY (owned) — Bot authoring

### CT-33 — Bot definition (declaration) kind contract
**Owner:** COMP-QMF-REGISTRY (authored via the QML library).
**Guarantee:** One Bot definition is the governed bot's DECLARATION half — a structured configuration artifact plus a reference to the bot's plain-Python logic distribution — whose identity is its semantic content only (exactly one strategy-family id, the confluence set, the declared parameter space, the footprint, the permitted exit-intent declaration, and the logic reference). Governed live/paper seats execute the canonical assignment (the defaults) only; a tuned assignment mints a NEW Bot version so it can never silently wear the original's track record. The bot never sizes and never declares its own full-loss price; the Bot kind mints only when both conformance layers (declaration linter + sandboxed execution) pass — registration is what governed evidence and seats cite.

### CT-34 — Confluence (leg-set) kind contract
**Owner:** COMP-QMF-REGISTRY (authored via the QML library).
**Guarantee:** One confluence is a reusable Bot-domain registry artifact (its own artifact with lineage to children) composed of one-or-more legs of any role mix (level | trigger | confirmation | filter), each naming a role + producer binding (a pinned CT-16/CT-17 fingerprint or a producer template) + optional exact parameters, cited by fingerprint from Bot definitions. It declares WHAT is consumed and WHICH role each plays; WHEN a leg is satisfied lives in the Python logic in V1. Identity is content, so reuse never mints a new confluence.

---

## Variables registry (`docs/registry/variables.yaml`) — configurability surface

The registry governs which platform quantities are fixed contract surface (`configurable: false`) versus UI-editable operator knobs (`configurable: true`), each tied to a decision id and component.

**Fixed / non-configurable (spine invariants):** monetary representation (scaled-integer) and money/price/quantity scales & rounding; timestamp precision (int64 UTC ns) and valid range; instrument identity shape; canonical hash algorithm (fp1:sha256); the seven typed_refusal_codes; the result identity key; python_version (3.14); coverage floor (80%, 100% for CT-01/02 primitives); journal_event_types (seven); local_store_engine set; barspec_kinds; presence_map_states; evidence_classes; the canonical indicator reference (TA-Lib pin); venue trendbar price basis and daily-bar boundary (both measured-per-broker, never hardcoded); venue protocol artifact (Spotware proto tag 91); the numeraire (USD, V1); the SQS formula itself; QMB CLI/sampler pins.

**Configurable / UI-editable (values operator-set, no ratified spine value):** the entire risk/sizing money ladder — kill_line_capital_floor, r_unit_price, seat_loss_run_allowance, seat_r_ceiling, runway_periods, bench_consecutive_loss_threshold, qualifying_loss_threshold (q), decision_freshness_bound; all SQS parameters (per-class hard-block thresholds, hysteresis band, outlier-guard multiple, sample cadence, baseline conditioning/refit, staleness horizon); all protection-window widths/anchors/dispositions (news blackout before/after, daily_dead_zone, session_handover_buffer, window_forced_flat); breakeven-ratchet trigger/offset; paper_starting_balance; hold_time_force_flat_trigger; control_rank_table; state_carry_declaration; backup cadence/RPO/RTO/retention/restore-verification cadence; historical_holdout_months (12); QMB governor CPU/memory budgets and per-run time/memory limits; qmb_stale_evidence_severity; registry attempt budget (deferred).

**Key governance rule:** `configurable: false` = fixed contract surface (a change is a version/contract event); `configurable: true` = UI-editable, and recorded corpus/recollection numbers attached to such a variable are non-authoritative evidence, never ratified constants or spine values. Several sizing/risk variables are deliberately blank ("declared-per-book/family/machine") — the container ships complete with numbers honestly blank, and blank blocks live money.
