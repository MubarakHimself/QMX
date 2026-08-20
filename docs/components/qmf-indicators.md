---
id: COMP-QMF-INDICATORS
title: qmf-indicators
type: component-spec
status: provisional
component: COMP-QMF-INDICATORS
depends_on: [COMP-QMF-CORE]
decisions: [DEC-0009, DEC-0013, DEC-0029, DEC-0030, DEC-0055, DEC-0096, DEC-0100, DEC-0101, DEC-0103, DEC-0109, DEC-0111, DEC-0112, DEC-0113, DEC-0120, DEC-0126, DEC-0127, DEC-0128, DEC-0130, DEC-0132, DEC-0133, DEC-0134]
sources: [DEC-0009, DEC-0013, DEC-0029, DEC-0030, DEC-0055, DEC-0096, DEC-0100, DEC-0101, DEC-0103, DEC-0109, DEC-0111, DEC-0112, DEC-0113, DEC-0120, DEC-0126, DEC-0127, DEC-0128, DEC-0130, DEC-0132, DEC-0133, DEC-0134, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, docs/architecture/dependencies.yaml, docs/contracts/ct-01-money-quantity.yaml, docs/contracts/ct-02-time-calendar.yaml, docs/contracts/ct-03-instrument-identity.yaml, docs/contracts/ct-04-typed-refusal.yaml, docs/contracts/ct-05-version-fingerprint.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-16-indicator.yaml]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# qmf-indicators

`COMP-QMF-INDICATORS` is the two-mode indicator library: one CT-16 contract, batch and streaming conformant modes, consumer-blind across bots, structure families, MIS, and backtesting, so research and the live path compute the same numbers by construction. Its public surface is the CT-16 protocol, the qmf-core series vocabulary it consumes, and the one named catalog surface for extension registration; everything else is private. [DEC-0126] [DEC-0055]

## Authority boundary

May: define and own CT-16; wrap the pinned canonical arithmetic reference and own the canonical arithmetic for formulas the reference lacks; validate configurations and inputs; expose batch and streaming behavior under the equality law; declare and prove light/heavy budgets; ship the catalog surface through which extensions register at the composition root; and return CT-04 refusals without exposing dependency-specific objects. [DEC-0126] [DEC-0127] [DEC-0128] [DEC-0055]

May never: re-implement arithmetic the pinned reference implements (wrap-not-reimplement) or arithmetic another governed producer publishes; expose vendor objects across CT-16; define the series vocabulary (`Bar`, `Tick`/`Quote`, `BarSpec`, exact rationals are qmf-core nouns) or perform bar aggregation (a fingerprinted qmf-data derivation); descale or re-enter the money path except through the two named qmf-core conversion boundaries; run scheduling, MIS fan-out wiring, or trading-loop behavior; ship a global instance registry (dedup is per-process and application-owned); mutate the reference's process-global configuration at runtime; or name a trading school in any rule or vocabulary. [DEC-0127] [DEC-0126] [DEC-0009] [DEC-0132] [DEC-0013]

## Interfaces

| Interface | Direction | Contract | Peer |
|---|---|---|---|
| Exact money, price, and quantity values | in | [CT-01](../contracts/ct-01-money-quantity.yaml) | COMP-QMF-CORE |
| Exact time and trading-calendar values | in | [CT-02](../contracts/ct-02-time-calendar.yaml) | COMP-QMF-CORE |
| Instrument and venue identity | in | [CT-03](../contracts/ct-03-instrument-identity.yaml) | COMP-QMF-CORE |
| Typed refusals | out | [CT-04](../contracts/ct-04-typed-refusal.yaml) | COMP-QMF-CORE |
| Version, fingerprint, and compatibility values | in/out | [CT-05](../contracts/ct-05-version-fingerprint.yaml) | COMP-QMF-CORE |
| Source observations (values supplied by the application) | in | [CT-10](../contracts/ct-10-source-observation.yaml) | Owned by COMP-QMF-DATA; application-mediated, not an import edge [DEC-0120] |
| Two-mode indicator contract | out | [CT-16](../contracts/ct-16-indicator.yaml) | Consumer-blind; consumers reach it through the composition root — intended: COMP-QMF-STRUCTURE via the composition law [DEC-0126] [DEC-0120] |

## Behavior

A configured indicator's identity is the entire declared configuration — formula id, contract format version, exact-rational parameters, the ordered named input set (each input carrying instrument-or-source identity, `BarSpec`, channel kind, quote side, and upstream fingerprints for derived inputs), declared calendar requirements with tzdata version, alignment and missing-value policies, warm-up, output schema, supported modes, and the arithmetic-reference configuration. That `fp1` fingerprint is the only dedup key; an element missing from it is a contract defect. [DEC-0126]

Inputs arrive in the pinned bulk form (read-only `memoryview` over immutable little-endian int64 bytes with per-channel out-of-band metadata); every position carries a `registry:presence_map_states` value; NaN and sentinels are prohibited. Outputs are full-length, index-aligned, presence-mapped, and every sample carries a knowable-at instant; provisional samples never enter governed evidence. Only as-of alignment is legal for governed evidence; a market-hours-closed position is `absent_by_schedule`, never a gap. [DEC-0126] [DEC-0130]

Where both modes are declared, the tier-2 equality law binds them (same-process, same-build, integer-ULP comparator, cold initial state), with restore-equivalence tested separately; snapshots are versioned serialized contracts scoped to a declared (OS, arithmetic-reference build) tuple. A streaming instance has exactly one feeder — one WriterId holder — and unlimited readers; instance count scales with distinct configurations, not consumers. [DEC-0126] [DEC-0113]

Canonical arithmetic: the pinned reference is `registry:canonical_indicator_reference` — TA-Lib 0.7.1 + 0.7.1 as lockfile-resolved artifact hashes plus an identity-bearing reference-configuration record asserted at import. Where the reference implements a formula, wrapping it is mandatory and it is canonical; where it does not (volume-weighted, session-anchored, and QMX-original formulas), this package's implementation is the canonical arithmetic under the identical upgrade gate. An output-changing upgrade mints the per-configured-indicator contract format version with recorded before/after evidence; dual-reference checks are registered comparison artifacts with integer-ULP tolerances. [DEC-0127] [DEC-0134] [DEC-0030]

Light versus heavy is per configuration, never per name: light iff four declared-and-benchmark-proven bounds hold (per-update cost within the live-path rung; bounded state; bounded window or declared anchor-reset rule; synchronous availability, which a marked not-ready value satisfies). The verdict is machine-scoped and display-only — never identity. Every configuration is heavy by default until the live-path rung has a recorded baseline; a heavy configuration's synchronous entry point returns `unsupported capability`, heavy runs off the trading path computed once and fanned out through the same contract, and a fanned-out value past its declared maximum age is a `stale evidence` refusal. [DEC-0128]

**The escape hatch is the design's point:** custom indicators are always authorable as plain Python outside governed evidence — when a concept is ambiguous or the framework cannot yet articulate it, plain Python is the intended route, never a forced fit. A working experiment graduates into governed evidence as a CT-16 extension — a separate versioned package outside the roster on its own SemVer ladder, its distribution identity and version identity fields of every artifact it produces, registered explicitly at the composition root through the catalog surface — with a lineage edge back to the originating research artifact. [DEC-0133] [DEC-0100]

### Foundation invariants

`COMP-QMF-INDICATORS` is a pure-computation library: it holds no external resource, spawns no threads or background work, exposes no async API, and returns immutable values that are safe to share by construction. Streaming indicator instances are the one named stateful class (one feeder, unlimited readers); the application owns all concurrency and wiring. [DEC-0113] [DEC-0126]

Package dependency is default-deny: the package imports only `COMP-QMF-CORE`. Typed configuration inputs (calendars, instrument-metadata snapshots, external event anchors) and all evidence emission reach it through the application composition root — declaring an input creates no package dependency edge. Adding an inter-library edge is a spine amendment. [DEC-0120] [DEC-0126]

Every public operation succeeds or returns a CT-04 typed refusal carrying context and retryability; refusals are never swallowed. `correlation_id` is exempt at pure value-contract boundaries — it rides the caller's context, never a pure signature; streaming instances are AD-14 components (long-lived state) and expose `health()`, while pure batch functions do not. [DEC-0112] [DEC-0131] [DEC-0109]

The package ships a benchmark harness with the same standing as its unit tests. Two rungs per configuration — burst throughput and per-tick latency, denominated per accepted input observation at the configured `BarSpec`, the no-op tick path measured separately — police light claims at the tier-2 gate; peak-memory regressions fail exactly as slowdowns do. [DEC-0111] [DEC-0126] [DEC-0128]

QMF's own source is governed by ruff, pyright strict, and pytest; public value types are frozen dataclasses and seams are `typing.Protocol`s; the package ships executable tests and reference usage demonstrating its public contract as tier-1 artifacts. [DEC-0101] [DEC-0096]

<!-- no-diagram: the component is one protocol plus a canonical-arithmetic wrapper and a catalog surface; internal wrapper structure is implementation detail behind CT-16 -->

## Configuration

| Variable | Registry key | Notes |
|---|---|---|
| Canonical arithmetic reference | `registry:canonical_indicator_reference` | TA-Lib 0.7.1 + 0.7.1, pinned as lockfile artifact hashes plus the identity-bearing reference-configuration record asserted at import. [DEC-0127] |
| BarSpec kinds | `registry:barspec_kinds` | The discriminated aggregation vocabulary replacing bare "timeframe". [DEC-0126] |
| Presence map states | `registry:presence_map_states` | Per-position presence in every bulk series; NaN and sentinels prohibited. [DEC-0126] |
| Contract version syntax | `registry:contract_version_syntax` | Two ladders ratified: SemVer for the lockstep code packages, per-contract integer format versions stamped into every artifact; arithmetic upgrades mint per configured indicator. [DEC-0103] [DEC-0127] |
| Typed refusal codes | `registry:typed_refusal_codes` | Seven-category taxonomy ratified. [DEC-0109] |

## Failure modes

| # | Condition | Behavior | Cites |
|---|---|---|---|
| FM-1 | An input series position is missing where the market-hours calendar says open, or an input cannot align as-of the evaluation instant. | The declared missing-value policy applies — marked gap or typed refusal, never silent filling; forward-fill or interpolation across the evaluation instant is a `policy rejection`. | DEC-0126, DEC-0109 |
| FM-2 | The reference library resolves to different artifacts than the lockfile pin, or its process-global configuration differs from the reference-configuration record at import. | `unavailable dependency` refusal at import; the fingerprint must never attest arithmetic that was not used. | DEC-0127, DEC-0109 |
| FM-3 | A caller invokes a heavy configuration's synchronous entry point on the trading path. | `unsupported capability` refusal; heavy runs off the trading path through the same contract, computed once and fanned out. | DEC-0128, DEC-0109 |
| FM-4 | A dependency upgrade changes output for identical canonical inputs. | The comparison suite catches it before the upgrade lands; the change mints the per-configured-indicator contract format version with before/after evidence — never a silent accept, never a protocol-wide bump. | DEC-0127, DEC-0030 |
| FM-5 | A wrapper exposes a dependency-specific object across CT-16, or a governed producer re-implements arithmetic another governed producer publishes. | Conformance failure — the public interface stays package-neutral and each formula has exactly one canonical owner. | DEC-0126, DEC-0127, DEC-0096 |
| FM-6 | A configuration claims light without a recorded live-path rung baseline, or its benchmark misses a declared bound. | The light claim is refused at the tier-2 gate; the configuration is heavy by default. | DEC-0128, DEC-0111 |
| FM-7 | A snapshot is restored on a different (OS, arithmetic-reference build) tuple. | `unavailable dependency` refusal; results from restored state carry the snapshot fingerprint as an input fingerprint. | DEC-0126, DEC-0109 |
| FM-8 | An extension is discovered by scanning rather than explicit registration, or its artifacts omit its distribution identity and version. | Non-conformant: discovery is explicit registration at the composition root through the one named catalog surface, and extension identity fields are mandatory in every artifact produced. | DEC-0133, DEC-0100 |

## Related

Decisions: DEC-0126, DEC-0127, DEC-0128, DEC-0130, DEC-0133, DEC-0134 (DEC-0056 superseded by DEC-0128). Contracts: [CT-16](../contracts/ct-16-indicator.yaml). ADR: [ADR-0006](../decisions/ADR-0006-indicators-and-structure.md). Scenarios: [SCN-0001 core freeze gate](../scenarios/SCN-0001-core-freeze-gate.md), [SCN-0009 synthetic stress boundary](../scenarios/SCN-0009-synthetic-stress.md). Knowledge: none drafted.
