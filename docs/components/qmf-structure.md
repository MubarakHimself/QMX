---
id: COMP-QMF-STRUCTURE
title: qmf-structure
type: component-spec
status: ratified
component: COMP-QMF-STRUCTURE
depends_on: [COMP-QMF-CORE]
decisions: [DEC-0009, DEC-0013, DEC-0030, DEC-0033, DEC-0035, DEC-0038, DEC-0039, DEC-0058, DEC-0096, DEC-0101, DEC-0103, DEC-0106, DEC-0107, DEC-0109, DEC-0111, DEC-0112, DEC-0113, DEC-0114, DEC-0117, DEC-0120, DEC-0121, DEC-0126, DEC-0127, DEC-0128, DEC-0129, DEC-0131, DEC-0132, DEC-0133]
sources: [DEC-0009, DEC-0013, DEC-0030, DEC-0033, DEC-0035, DEC-0038, DEC-0039, DEC-0058, DEC-0096, DEC-0101, DEC-0103, DEC-0106, DEC-0107, DEC-0109, DEC-0111, DEC-0112, DEC-0113, DEC-0114, DEC-0117, DEC-0120, DEC-0121, DEC-0126, DEC-0127, DEC-0128, DEC-0129, DEC-0131, DEC-0132, DEC-0133, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, docs/architecture/dependencies.yaml, docs/contracts/ct-02-time-calendar.yaml, docs/contracts/ct-03-instrument-identity.yaml, docs/contracts/ct-04-typed-refusal.yaml, docs/contracts/ct-05-version-fingerprint.yaml, docs/contracts/ct-06-registration.yaml, docs/contracts/ct-07-lineage-edge.yaml, docs/contracts/ct-08-gate-evidence.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-17-causal-structure.yaml]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# qmf-structure

`COMP-QMF-STRUCTURE` is the QMX-owned library for causal chart-object families. A family is a type of chart object — point, level, zone, span, distribution, graph — never a strategy, bot, or Book category. Objects are minted once at observation, evolve only through append-only lifecycle and interaction records, and carry knowledge time and evidence class as identity, so repainted or look-ahead structure can never enter evidence. Its public surface is the CT-17 protocol and core value types; everything else is private. [DEC-0129] [DEC-0058] [DEC-0132]

## Authority boundary

May: implement governed families whose confirmation rule states "confirmed the moment X happens" with X knowable at that instant (clock-confirmed rules included); mint objects at observation with anchor span and observed-at (known-at semantics); check the emission invariant in-component; return fingerprintable content for structure objects, lifecycle records, interaction records, and comparison artifacts; evaluate sloped objects through the named analytic-to-exact boundary; consume indicator results, structure objects, and calendar windows as declared composite children; and expose the family-neutral CT-17 boundary. [DEC-0129] [DEC-0131] [DEC-0126]

May never: mutate a minted object (state evolves only through append-only interaction records; current state is a read-time fold); classify anchor span, observed-at, or any lifecycle instant as occurrence/display-only; admit a family whose confirmation rule is imprecise (those stay in ungoverned research lanes); name a trading school in any rule or vocabulary; privilege the seed families over operator-authored ones; cascade invalidation automatically; stamp records itself (the composition root holds the WriterId and mints registry records); re-implement arithmetic a governed producer publishes (indicators are consumed as declared inputs); emit trading-entry, Bot, Book, exit, or risk policy; or revive the dead third-party strategy-family contract design. [DEC-0129] [DEC-0131] [DEC-0132] [DEC-0127] [DEC-0013] [DEC-0009]

## Interfaces

| Interface | Direction | Contract | Peer |
|---|---|---|---|
| Exact time and trading-calendar values | in | [CT-02](../contracts/ct-02-time-calendar.yaml) | COMP-QMF-CORE |
| Instrument and venue identity | in | [CT-03](../contracts/ct-03-instrument-identity.yaml) | COMP-QMF-CORE |
| Typed refusals | out | [CT-04](../contracts/ct-04-typed-refusal.yaml) | COMP-QMF-CORE |
| Version, fingerprint, and compatibility values | in/out | [CT-05](../contracts/ct-05-version-fingerprint.yaml) | COMP-QMF-CORE |
| Registry registration (structure objects, lifecycle and interaction records as record kinds) | out | [CT-06](../contracts/ct-06-registration.yaml) | Owned by COMP-QMF-REGISTRY; minted by the composition root, not an import edge [DEC-0129] [DEC-0120] |
| Lineage edges (supersedes, confirmed-as, confirmation, invalidation, interaction) | out | [CT-07](../contracts/ct-07-lineage-edge.yaml) | Owned by COMP-QMF-REGISTRY; application-mediated, not an import edge [DEC-0131] [DEC-0120] |
| Causality and attempt-gate evidence | out (deferred) | [CT-08](../contracts/ct-08-gate-evidence.yaml) | The registration gate is deferred to the backtesting sitting (DEC-0121); the in-component emission invariant is the interim guard [DEC-0129] |
| Source observations (values supplied by the application) | in | [CT-10](../contracts/ct-10-source-observation.yaml) | Owned by COMP-QMF-DATA; application-mediated, not an import edge [DEC-0120] |
| Indicator results as declared inputs | in | [CT-16](../contracts/ct-16-indicator.yaml) | Owned by COMP-QMF-INDICATORS; composition-law input via the composition root [DEC-0126] |
| Causal structure lifecycle | out | [CT-17](../contracts/ct-17-causal-structure.yaml) | Consumer-blind; any CT-16/CT-17 configuration may consume via the composition law [DEC-0129] |

## Behavior

An object is minted once, at observation, carrying family identity + version, exact-rational parameters, its declared confirmation rule, its anchor span (frozen at observation, permitted to precede observed-at, excluded from causality tests), and observed-at — the earliest instant the object was derivable from causally-available data. Confirmation, invalidation, and interaction records are separate append-only records/edges referencing the object's fingerprint; "still valid at T" is a read-time fold per CT-17's read-resolution rule. The emission invariant — `anchor.start ≤ anchor.end ≤ observed-at ≤ confirmed-at ≤ invalidated-at`, with observed-at at or after the newest consumed input's evidence time — is checked in-component now, independent of the deferred causality gate. [DEC-0129] [DEC-0121]

Evidence class (`registry:evidence_classes`) is identity and a named label part: unconfirmed outputs link to confirmed successors via `confirmed-as` edges, and a read requesting confirmed evidence refuses unconfirmed rows rather than filtering silently. Confirmation delay is a declared maximum bound in observations at the family's `BarSpec` and feeds split purge/embargo widths; records partition into splits by knowledge time (confirmed-at). [DEC-0129] [DEC-0131]

Sloped objects are integer anchors plus a versioned evaluation rule (slope derived, never stored); calendar-anchored levels declare sampling and schedule-gap policies; standing objects declare observed-at = configuration instant. Composites take the maximum of their children's instants, are order-significant by default, and may hold any governed kind; invalidation never cascades automatically; a refit is a new artifact with a `supersedes` edge. The routing test separates the libraries: a value per evaluation instant is CT-16, a discrete object with a birth and a lifetime is CT-17, and either consumes the other. [DEC-0129] [DEC-0131] [DEC-0115]

The law binds governed evidence only: live in-memory use persists nothing, scanners run ungoverned and promote only confirmed objects — but any object cited by a journal event or result label becomes governed evidence by that act and is persisted. The four light/heavy bounds bind families (per-update cost, live-object-set size, scan window, synchronous availability) under the same benchmark policing as indicators, and CT-16's state bound and snapshot/restore obligations apply verbatim. [DEC-0129] [DEC-0128]

**The escape hatch is the design's point:** any concept a family cannot yet state precisely stays freely usable in plain Python outside governed evidence. The seed candidates (`registry:structure_seed_family_candidates`) hold no privilege — operator-authored from-scratch families are first-class peers under identical law, and family authoring through the extension shape (separate versioned package, explicit registration at the composition root, graduation with a lineage edge to the originating experiment) is the primary use case, not an afterthought. [DEC-0133] [DEC-0129]

### Foundation invariants

`COMP-QMF-STRUCTURE` is a pure-computation library: it holds no external resource, spawns no threads or background work, exposes no async API, and returns immutable values safe to share by construction. Family instances holding live object sets are the named stateful class (one feeder, unlimited readers) and expose `health()`; pure batch functions do not. [DEC-0113] [DEC-0131]

Package dependency is default-deny: the package imports only `COMP-QMF-CORE` in V1. Registration, lineage, and evidence flow through the application composition root, which holds the WriterId and the gapless per-(writer, kind) sequence — the library returns fingerprintable content, never stamped records. Adding an inter-library edge is a spine amendment. [DEC-0120] [DEC-0129]

Every public operation succeeds or returns a CT-04 typed refusal carrying context and retryability; refusals are never swallowed; `correlation_id` is exempt at pure value-contract boundaries and rides the caller's context. [DEC-0112] [DEC-0131] [DEC-0109]

The package ships a benchmark harness with the same standing as its unit tests; its rungs are active object-set size, objects minted per bar, and interaction records per bar, with peak-memory regressions failing the tier-2 gate exactly as slowdowns do. [DEC-0111] [DEC-0129]

QMF's own source is governed by ruff, pyright strict, and pytest; public value types are frozen dataclasses and seams are `typing.Protocol`s; the package ships executable tests and reference usage demonstrating its public contract as tier-1 artifacts. [DEC-0101] [DEC-0096]

`GAP(GAP-0016): DEFERRED to the backtesting sitting (DEC-0121). The look-ahead / causality registration gate and its CT-08 pass/refusal evidence are not defined here; the in-component emission invariant (DEC-0129) is a cheap interim guard, not that gate. Artifacts registered before that sitting carry no causality evidence, a consequence knowingly accepted. Do not close this gap here.`

<!-- no-diagram: CT-17 is one family-neutral lifecycle boundary; family internals are extension territory and drawing a family catalog would privilege the seed candidates against DEC-0129 -->

## Configuration

| Variable | Registry key | Notes |
|---|---|---|
| Seed family candidates | `registry:structure_seed_family_candidates` | Swing points, horizontal levels from confirmed swings, zones, structure breaks — candidates only, each shipping solely once its confirmation rule is precise; no privilege over operator-authored families. [DEC-0129] |
| Evidence classes | `registry:evidence_classes` | confirmed / unconfirmed / provisional; identity-bearing label part; confirmed reads refuse unconfirmed rows. [DEC-0129] |
| Timestamp precision | `registry:timestamp_precision` | int64 UTC nanoseconds (POSIX no-leap-second) with each source's actual resolution stored beside the value. [DEC-0106] |
| Instrument identity shape | `registry:instrument_identity_shape` | Identity is (venue, venue's own symbol), the symbol opaque and never parsed; family and formula ids follow the same minting discipline. [DEC-0107] [DEC-0129] |
| Contract version syntax | `registry:contract_version_syntax` | Two ladders ratified: SemVer for the lockstep code packages, per-contract integer format versions stamped into every artifact. [DEC-0103] |

## Failure modes

| # | Condition | Behavior | Cites |
|---|---|---|---|
| FM-1 | An emission violates the lifecycle ordering invariant, or observed-at precedes the evidence time of a consumed input. | `invalid input` refusal, checked in-component at emission — the interim look-ahead guard, independent of the deferred GAP-0016 gate. | DEC-0129, DEC-0121, DEC-0109 |
| FM-2 | A caller requests a family whose confirmation rule cannot state "confirmed the moment X happens" with X knowable then. | The family is not admitted to the governed library; the concept remains freely usable in the ungoverned research lane. | DEC-0129, DEC-0133 |
| FM-3 | A correction, refit, or state change would overwrite an object or an edge. | The mutation is prohibited: interaction records append, a refit mints a new artifact with a `supersedes` edge and frozen anchors, and earlier evidence remains. | DEC-0129, DEC-0035, DEC-0039 |
| FM-4 | A read requests confirmed evidence over rows whose evidence class is unconfirmed or provisional. | `policy rejection` refusal — never a silent filter; the unconfirmed row's `confirmed-as` edge locates its confirmed successor. | DEC-0129, DEC-0131, DEC-0109 |
| FM-5 | CT-10 input lacks the event-time or knowledge-time evidence causality requires. | `invalid input` refusal; every external fact carries event-time, known-at, source, and revision, and corrections are appended, never overwritten. | DEC-0038, DEC-0117, DEC-0109 |
| FM-6 | A family inlines indicator arithmetic a governed producer publishes. | Contract defect: the indicator is consumed as a declared input through the composition law, never re-implemented. | DEC-0127, DEC-0126 |
| FM-7 | A split manifest receives a record whose observed-at precedes a boundary while its confirmed-at follows it, beyond the declared embargo. | The manifest refuses the record; partitioning is by knowledge time. | DEC-0131, DEC-0119 |
| FM-8 | A family claims light while exceeding a declared bound (object-set size, scan window, per-update cost, availability). | The light claim is refused at the tier-2 benchmark gate; the family is heavy by default until the rung has a baseline. | DEC-0128, DEC-0111 |
| FM-9 | An implementation imports the dead third-party strategy-family contract design, or names a school in a rule. | Conformance failure: families are QMX-owned CT-17 contracts under school-neutral vocabulary. | DEC-0013, DEC-0014, DEC-0132 |

## Related

Decisions: DEC-0129, DEC-0131, DEC-0128, DEC-0133, DEC-0058, DEC-0114. Contracts: [CT-17](../contracts/ct-17-causal-structure.yaml), [CT-16](../contracts/ct-16-indicator.yaml). ADR: [ADR-0006](../decisions/ADR-0006-indicators-and-structure.md). Scenarios: [SCN-0002 source correction](../scenarios/SCN-0002-source-correction.md), [SCN-0009 synthetic stress boundary](../scenarios/SCN-0009-synthetic-stress.md). Knowledge: none drafted.
