---
id: ADR-0013
title: Exact values, exact time, and artifact identity
type: adr
status: ratified
component: COMP-QMF-CORE
depends_on: [COMP-QMF-CORE, COMP-QMF-CALENDAR-FOREX, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-VENUE, COMP-QMF-RISK]
decisions: [DEC-0105, DEC-0106, DEC-0107, DEC-0108, DEC-0109, DEC-0110]
sources: [DEC-0105, DEC-0106, DEC-0107, DEC-0108, DEC-0109, DEC-0110, DEC-0123, DEC-0124, EXT-2007, EXT-2008, EXT-2009, EXT-2010, EXT-2011, EXT-2012, EXT-2025, EXT-2029, EXT-2030, EXT-2028, "_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md", "archive/qmf-3.txt"]
generated: 2026-08-20
verified: 2026-08-20
stale_after: 1y
---

# ADR-0013: Exact values, exact time, and artifact identity

Date: 2026-08-20. status: ratified — AD-7..AD-12 are operator-ratified in the foundation architecture sitting (2026-08-19/20), two-lens audited and amended by the sitting's contradiction sweep and reviewer gate; this document stays provisional until the knowledge base is re-ratified.

## Context

Five contract families — CT-01 money and quantity, CT-02 time and calendar rule sets, CT-03 instrument identity, CT-04 typed refusals, CT-05 versioning and fingerprints — carry the semantics every other QMF package computes against. Until they were exact, two conformant implementations could disagree, a server move or tzdata update could silently change a result, a broker rename could rewrite history, and merged sandbox evidence could collide with itself. The foundation architecture sitting ratified the five families plus the result label as AD-7 through AD-12, then hardened them through a two-lens time audit (architect and DevOps), an end-of-sitting contradiction sweep, and a reviewer gate that pinned the mechanisms.

## Options considered

1. **Binary float on the money path** — rejected: float drift makes fingerprints non-deterministic and broker disputes unreconcilable; scaled integers with a declared scale were selected, and the money path was defined as a **taint** rather than a location, so a value contributed by any package is governed by where it flows, not by who computed it (DEC-0105).
2. **`Price` tagged with a single currency** — rejected at the contradiction sweep: a price is a ratio quoted for an instrument, so `Price(instrument, scale)` replaced a currency tag (DEC-0105).
3. **Normalizing venue values at ingest** — rejected: a venue's raw integers are stored verbatim with their declared scales as evidence, and conversions are derived with lineage (DEC-0105, mirrored for time in DEC-0106).
4. **Monotonic readings persisted as timestamps** — rejected at the reviewer gate: a monotonic reading is never an Instant; it may persist only as an opaque boot-scoped diagnostic excluded from identity (DEC-0106).
5. **`Duration` restricted to monotonic contexts** — rejected: `Duration` is a clock-agnostic quantity of nanoseconds and is freely storable; the restriction sits on operations, where latency, timeout, cooldown, and cadence must be measured monotonically (DEC-0106).
6. **Market-hours calendar identity as the venue instance** — rejected at the reviewer gate: identity is the **rule set** plus tzdata version, so venues sharing a rule set share the identity and a venue change that does not change the rule set does not change derived-artifact identity (DEC-0106).
7. **Trading date derived by formatting an instant** — rejected: `TradingDate` derives only from a market-hours or day-boundary rule set, carries that rule-set identity and version in-band, and is never a causality proxy (DEC-0106).
8. **Symbols parsed for meaning; venue ids derived from broker attributes** — rejected: symbols and `VenueId` are opaque, operator-minted, stable, and never reused, so a prop firm white-labeling a platform is its own venue (DEC-0107).
9. **Timestamps as primary or dedup keys** — rejected: a stored record's identity is its `fp1` fingerprint, and `(instant, writer, sequence)` is an ordering key only (DEC-0106, DEC-0108).
10. **Hashing float bytes for float-bearing artifacts** — rejected: analytic series take label-derived identity plus an integrity checksum and (OS, library-version) provenance, and cross-OS bit-identity of float content is explicitly not promised (DEC-0108).
11. **Six refusal categories** — the sitting first ratified six; the reviewer gate added a seventh, `storage failure`, once the data area introduced an I/O surface. Seven were selected, with categories addable later and never redefined (DEC-0109).
12. **Refusals raised as exceptions** — rejected: public boundaries **return** refusals as result unions, and exceptions are reserved for programmer error and never carry a refusal across a package boundary (DEC-0109).
13. **`world = simulated` usable in V1** — rejected: simulated is reserved but unusable until the backtesting sitting defines simulated-time typing; writing it into governed evidence is a `policy rejection` refusal (DEC-0110).
14. **Identity distinctness as world separation** — rejected: storage separation delivers world separation, so a non-live world may never write into the live evidence namespace (DEC-0110).

## Decision

**Exact money.** Money, Price, and Quantity are whole-number integer counts at a declared scale (`registry:monetary_representation`): `Money(currency, scale)`, `Price(instrument, scale)`, `Quantity(unit, scale)` with an opaque unit — lot, share, coin, contract. Mixed-scale arithmetic on the same currency or unit auto-promotes losslessly to the finer scale or returns a typed refusal; there is no implicit rescale and no implicit rounding (`registry:money_rounding_mode`). Binary float is banned on the money path, and a float crossing back to a framework value passes a named conversion boundary with an explicitly stated rounding mode — the venue adapter boundary is one such named boundary. Foreign money is evidence: a venue's raw integers are stored verbatim with their declared scales, conversions are derived with lineage, and corrections are annotations rather than rewrites. Analytic float series remain permitted off the money path with label-derived identity. (DEC-0105)

**Exact time.** Every stored timestamp is int64 UTC nanoseconds since the Unix epoch with POSIX no-leap-second semantics (`registry:timestamp_precision`), representable over `registry:timestamp_valid_range`, with all nanosecond arithmetic checked so overflow is an `invalid input` refusal rather than a wrap. Instant `0` is a valid instant and an absent time is an absent field. Local time is display-only and always labelled. Civil date and trading date are distinct types; `TradingDate` carries its calendar rule-set identity and version in-band, equality is defined only within one rule-set identity, and comparison across rule sets is a typed refusal. The core time vocabulary is Instant, CivilDate, TradingDate, Duration, Interval (half-open), SessionWindow. Wall and monotonic clocks are type-separated; clock access is a core-defined protocol, the composition root injects the real clock, replay injects a data-driven one, and nothing below the root reads the system clock. Every record stream carries a per-writer strictly-increasing sequence, and `(instant, writer, sequence)` is a replay-determinism device with no causal meaning — causality tests refuse at equal instants rather than tie-break. `WriterId` is a first-class core noun, minted per (machine, role, stream) and accompanied by a boot or epoch id. (DEC-0106)

**Calendars, three named kinds.** A **market-hours calendar** carries two separately-named facts, each with its own zone: an accounting rollover (which trading date an instant belongs to) and a session schedule (when the market is open); session and trading-day length are data and no consumer may assume a constant. A **day-boundary calendar** is an accounting-boundary rule parameterized by account, answers only which day an instant belongs to for evaluation, is never substituted for a market-hours calendar, and produces TradingDates carrying its own identity — V1 holds the seam only and models no prop firm. A **news calendar** is the third named kind, and COMP-CALENDAR-FEED is the news-calendar feed; the three names are distinct concepts and bare "calendar" is not used (EXT-2030). The forex market-hours calendar ships first with a 17:00 America/New_York rollover (`registry:forex_rollover`), weekend gaps, and holidays in scope; swap-Wednesday is dropped from V1. Market-hours calendar extensions force the timezone path to their pinned `tzdata` package and verify at import that the resolved tzdb version equals the pin, refusing with `unavailable dependency` otherwise, so a fingerprint never attests a tzdb that was not used. (DEC-0106)

**Instrument, venue, and account identity.** Instrument identity is (venue, venue's own symbol) with the symbol opaque and never parsed (`registry:instrument_identity_shape`). `VenueId` is operator-minted, opaque, stable, never derived from a mutable broker attribute, and never reused; a distinct broker or legal entity is a distinct venue even on shared infrastructure. Aliases, renames, asset class, and mutable metadata are separate dated records pointing at identities, and stored history never rewrites. Venue and Account are distinct first-class nouns defined in `qmf-core` with records owned by `qmf-registry`; one venue may hold many accounts, each with a role — live, demo, paper-validation, paper-benched, or prop-firm — and Books bind to accounts. Multi-broker operation — the operator's plan names ~6 venues with per-broker specialization — and broker migration are normal cases, not special ones. (DEC-0107)

**Deterministic fingerprints.** The canonical serializer and fingerprint function live in `qmf-core` and no other package may compute a fingerprint except by calling it. The pinned `fp1` recipe is UTF-8 JSON, object keys sorted lexicographically at every depth, no insignificant whitespace, strings NFC-normalized, all identity numerics integers with floats refused in identity content, null prohibited so an absent value is an omitted key, arrays order-significant, hashed with SHA-256 (`registry:canonical_hash_algorithm`) and emitted as `fp1:sha256:<hex>`. The prefix versions the recipe: an upgrade mints `fp2` and old fingerprints stay valid forever. Every contract field is identity by default, and display-only exclusion requires an explicit versioned declaration in the contract rather than an implementer's judgment. An idempotent re-write with the same hash and byte-identical content — the sandbox-merge normal case — is accepted silently; a true collision with the same hash and differing bytes is refused and alarmed, never overwritten. (DEC-0108)

**Typed refusals.** Every public operation succeeds or returns a typed refusal carrying category, machine-readable context, and retryability (yes, no, or after-condition). The seven categories (`registry:typed_refusal_codes`) are invalid input, unsupported capability, unavailable dependency, stale evidence, policy rejection, transient venue failure, and storage failure. Categories are addable in later versions and never redefined. Value-type construction is one pattern everywhere: an unchecked constructor for trusted internal use plus a validating `try_create` factory returning value-or-refusal. (DEC-0109)

**Result label and worlds.** Every result entering evidence carries producer contract format version, input fingerprints, evidence time range, computation identity, and world; together these are its identity (`registry:result_identity_key`), and human display names live outside identity. Computation identity is content-derived so identical work from two sandboxes deduplicates and merges, while the occurrence record — when, where, by whom it ran — is separate provenance outside identity. The worlds are `live` (real venue clocks and quotes, where the account role carries money-reality so paper and demo runs are `world = live` and stay comparable for alpha-decay sensing), `replay` (a data-driven injected clock over recorded history), and `simulated` (reserved and unusable in V1). Factory sandboxes never produce timestamps that enter an evidence store. (DEC-0110)

**cTrader evidence, not adoption.** The delivered cTrader Open API time research — UTC milliseconds platform-wide, a 17:00 America/New_York daily bar boundary, BID-derived trendbars per staff confirmation, no server-clock primitive, 50/s and 5/s rate limits with a one-week tick span — is recorded evidence for the venue sitting and is not adopted (DEC-0123). Its 17:00 New York finding corroborates the operator-adopted forex rollover at best-available level, and its absence of a server-clock primitive corroborates the receive-time recording rule. No cTrader timestamp is trusted as UTC until venue verification. `GAP(GAP-0037): does venue verification confirm cTrader platform timestamps as UTC and trendbars as bid-derived, and which broker and account type is the first target?`

## Consequences

Determinism becomes checkable rather than hoped for: two conformant producers, or the same producer in two sandboxes, agree on identity or the difference is a refusal. Renames, broker migrations, and tzdata updates stop being identity events — a re-derivation under a newer tzdata version mints a new artifact with a lineage edge (DEC-0103), so the framework can hold both answers and say which rule-set and tzdata version produced each. The taint definition of the money path makes float bans enforceable across package seams instead of per-module. The cost is friction that never goes away: every serialized field must be classified identity or display-only in its contract, every public boundary must carry a refusal union, and every rule-set-derived TradingDate must name the rule set it came from. Three of the six original `qmf-core` freeze choices are now closed by these rulings — the UTC time encoding, instrument identity, and the result-label tuple — while canonical indicator arithmetic, the backtest fidelity taxonomy, and the search-quality threshold stay open for their own sittings (DEC-0124). `world = simulated` remains a reserved token no V1 code may write, so any comparison that would need synthetic-time typing waits for the backtesting sitting.

## Blast radius

- **Contracts filled by this ruling:** CT-01 money and quantity, CT-02 time and calendar rule sets, CT-03 instrument identity, CT-04 typed refusal, CT-05 versioning and fingerprint. Every other contract inherits them: CT-06..CT-09 registry records and lineage, CT-10..CT-15 and CT-26 data, CT-16..CT-17 indicators and structure, CT-18..CT-21 venue, CT-22..CT-25 risk — each stamps a format version, returns typed refusals, and identifies stored artifacts by `fp1`.
- **Component specs:** COMP-QMF-CORE defines the value types, nouns, clock protocol, and the single fingerprint implementation; COMP-QMF-REGISTRY owns Venue, Account, and Instrument records; COMP-QMF-DATA and its seams COMP-QMF-DATA-STORE, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-BACKUP store instants, scales, and fingerprints verbatim; COMP-QMF-VENUE holds the named conversion boundary for foreign money and foreign time; COMP-QMF-RISK computes on the money path; COMP-QMF-INDICATORS and COMP-QMF-STRUCTURE take label-derived identity for float series; COMP-CALENDAR-FEED is renamed apart as the news-calendar feed; COMP-CTRADER and COMP-DUKASCOPY are the foreign-evidence sources.
- **New component:** COMP-QMF-CALENDAR-FOREX, the first market-hours calendar extension.
- **Registry:** `registry:monetary_representation`, `registry:money_decimal_scale`, `registry:price_decimal_scale`, `registry:quantity_decimal_scale`, `registry:money_rounding_mode`, `registry:timestamp_precision`, `registry:timestamp_valid_range`, `registry:forex_rollover`, `registry:instrument_identity_shape`, `registry:canonical_hash_algorithm`, `registry:contract_version_syntax`, `registry:typed_refusal_codes`, `registry:result_identity_key`, `registry:venue_trendbar_price_basis`.
- **Glossary:** market-hours calendar, day-boundary calendar, and news calendar are three separate entries; world, WriterId, source, and result label are ratified terms.

## Architecture preflight

Verdict: **new: COMP-QMF-CALENDAR-FOREX**.

Reasons:

- the roster is frozen at five libraries + two modules (DEC-0024) so no roster package may absorb a market-hours calendar;
- `qmf-core` takes zero outside dependencies (DEC-0104) and the tzdata pin therefore cannot live in core;
- the sitting's architect audit made extensions-outside-roster the explicit fix;
- no `status: dead` ledger entry covers calendar extensions — DEC-0050 is superseded and concerned news-feed capture.

It owns: the forex market-hours calendar rule set + tzdata pin + import-time verification.

It may never: define shared nouns (DEC-0100) or enter the roster's lockstep ladder.

Authority shrink: none — core keeps the protocol, the extension implements it.

Reuse, with authority unchanged: COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-DATA-STORE, COMP-QMF-DATA-INGEST, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-CALENDAR-FEED (renamed apart as the news-calendar feed, scope unchanged), COMP-CTRADER, COMP-DUKASCOPY.
