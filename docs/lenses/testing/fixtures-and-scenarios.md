---
id: LENS-TEST-FIXTURES
title: QMF Fixtures and Golden Scenarios
type: lens
status: provisional
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP, COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, COMP-OBJECT-STORAGE]
decisions: [DEC-0004, DEC-0007, DEC-0026, DEC-0029, DEC-0030, DEC-0033, DEC-0038, DEC-0044, DEC-0045, DEC-0046, DEC-0054, DEC-0096, DEC-0101, DEC-0102, DEC-0106, DEC-0108, DEC-0110, DEC-0117, DEC-0118, DEC-0119, DEC-0121, DEC-0126, DEC-0127, DEC-0128, DEC-0129, DEC-0135, DEC-0136, DEC-0137, DEC-0138]
sources: [_docwork/ledger.yaml, _docwork/gaps.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, docs/constitution.md, docs/architecture/dependencies.yaml, docs/registry/variables.yaml, docs/components/, docs/contracts/, docs/lenses/testing/test-strategy.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# QMF Fixtures and Golden Scenarios

The quality toolchain and three quality tiers are ratified: fixtures run under ruff/pyright-strict/pytest, unit and property fixtures at tier 1, contract and integration fixtures at tier 2 in isolated per-package environments, with reference usage (L27) shipped as a tier-1 artifact (DEC-0101, DEC-0102, DEC-0096). The fixture classes, proof-key formats, metadata mapping, and golden-scenario binding below carry that ratified backing; the exact directory layout inside each package is documentation-time detail. Controlled fixtures are test evidence only; they are not product market data, Bots, or strategies (DEC-0007, DEC-0096).

## Proposed fixture classes

The scheme assigns each fixture one source class and allows several proof references to point to the same case. Fixtures run under the ratified toolchain and tiers (DEC-0101, DEC-0102); the exact proof-key shape is documentation-time convention.

| Class | Stable proof key | Purpose |
|---|---|---|
| Contract valid round-trip | `<contract-id>/round-trip/<case>` | Prove canonical encode/decode and semantic equality for a valid contract value. |
| Contract boundary | `<contract-id>/boundary/<case>` | Prove every ratified enum, unit, nullability, range, version, and compatibility edge. |
| Contract invalid/refusal | `<contract-id>/invalid/<case>` | Prove malformed or prohibited input does not cross the public boundary and produces the ratified refusal/evidence. |
| Component failure mode | `<component-id>/<failure-mode-id>` | Execute one component-spec Condition and assert its Behavior plus absence of prohibited side effects. |
| Law or invariant property | `<decision-id>/property/<case>` or `<contract-id>/invariant/<case>` | Generate or replay inputs that would falsify a constitution law, contract invariant, or component `May never` boundary. |
| External controlled replay | `<component-id>/replay/<case>` | Replay a recorded external response through a QMF adapter without testing provider internals. |
| Synthetic infrastructure | `<component-id>/synthetic/<case>` | Stress parsing, capacity, corruption, outage, retry, or failure handling without making an edge claim. |

The repository layout is ratified: a uv workspace of `src/`-layout packages, each with its own `tests/` and `examples/` (L27 reference usage), and calendar extensions outside the roster (DEC-0100, DEC-0101). The exact per-package fixture and recording subdirectory is documentation-time detail; the selected path must keep fixtures outside shipped QMF product artifacts (DEC-0007).

## Proposed fixture identity and provenance

The proposed binding records existing IDs needed to reproduce its claim. These are candidate test metadata, not application-domain fields.

| Mapping item | Proposed value | Proposed rule |
|---|---|---|
| Proof key | CT, COMP/FM, or DEC key from the fixture classes | Never invent an untraceable test-only requirement. |
| Scenario | `SCN-*` when the fixture implements a golden scenario; otherwise null | One scenario may map to several proof keys. |
| Components | One or more `COMP-*` IDs | Must resolve in `docs/architecture/dependencies.yaml`. |
| Contracts | One or more `CT-*` IDs | Must resolve in `docs/contracts/`. |
| Authority | Applicable `DEC-*` and `GAP-*` IDs | A GAP recommendation is never expected output. |
| Given | Canonical fixture identity plus setup references | Values use CT schemas and registry keys, not duplicated literals. |
| When | One public CT operation or bounded scenario action | Unit cases have no network. |
| Then | Exact output/refusal/evidence and prohibited side effects | Expected fields must exist in a ratified CT schema. |
| Clock | An injected CT-02 clock (int64 UTC ns) or null when time is irrelevant | Time is injected at the composition root; no fixture below the root reads the system clock, and a monotonic reading is never an Instant (DEC-0106). |
| Random seed | Declared seed or null when deterministic without randomness | Replaying the binding with the same seed must reproduce the same inputs. |
| Source class | `source-evidence`, `controlled-replay`, or `synthetic` | Synthetic cannot validate trading edge (DEC-0054). |
| Fingerprint | CT-05 `fp1:sha256:<hex>` identity via the single qmf-core implementation | Canonical bytes are the pinned `fp1` recipe: sorted keys, NFC strings, integer-only identity numerics, floats refused (DEC-0108). |

## Proposed determinism rules

Unit fixtures (tier 1) make no network calls. External outcomes enter unit tests as controlled replays at CT-15, CT-18, CT-19, CT-20, CT-21, or CT-14 boundaries. Integration tests (tier 2) use the ratified store stack (Parquet/DuckDB/SQLite/JSONL behind QMF-owned contracts, DEC-0117) and the ratified backup primitives (DEC-0118); venue sandbox integration uses demo credentials only and factory sandboxes never hold live secrets (DEC-0136, DEC-0138).

Time-dependent fixtures inject a CT-02 instant (int64 UTC ns) and declare the trading-date/market-hours-calendar context; the clock is injected, never read from the system below the composition root (DEC-0106). Randomized and property fixtures declare their seed. Equal semantic inputs replay to equal CT-05 `fp1` identities, computed by the single qmf-core implementation with floats refused in identity content (DEC-0108, DEC-0110, DEC-0029, DEC-0030).

Source fixtures preserve provider identity, event-time, knowledge-time (known-at), source, revision, and raw source material verbatim; `source` is a provenance noun orthogonal to `VenueId` (DEC-0117). Corrections append a new fixture record and relationship rather than rewriting the earlier evidence (DEC-0038, DEC-0044, DEC-0045).

Venue secret handling is ratified: fixtures carry **secret references, never values**; a `SecretValue` never renders its value (repr, str, serialization, and logging all yield the reference id), the reference is excluded from `fp1`, and paired-demo bindings are secret-reference-only records. Testing uses demo credentials only and factory sandboxes never hold live secrets; expiry and refusal secret paths ship as tested behavior (DEC-0136, DEC-0138).

## Proposed golden scenario binding

The proposed format is a `SCN-*` document under `docs/scenarios/` with concrete Given, When, and Then statements. It would map inputs to fixture identities, actions to CT boundaries, and assertions to outputs/refusals, component behavior, laws, or evidence. DEC-0096 requires executable tests and reference usage but does not ratify this exact structure.

If a scenario needs an unresolved field, enum, value, target, or state, it carries the applicable `GAP(GAP-*)` marker and remains blocked. It must not fill CT-01 through CT-26 from a recommendation. A blocked scenario is not test-complete or releasable. The uncertain-submission scenario [SCN-0005](../../scenarios/SCN-0005-uncertain-venue-submission.md) covers a lost-transport submission resolving to UNKNOWN — a state, never an error — whose fixtures draw every deadline, retry, and reconciliation value from a contract field or registry entry, never an invented constant (DEC-0137).

| Scenario domain | Contract fixtures | Proposed assertions | Blocking design areas |
|---|---|---|---|
| Exact values and identity | CT-01 through CT-05 | Scaled-integer money on a taint path, int64-ns time with in-band calendar identity, (venue, opaque symbol) identity, seven-category returned refusal, `fp1` deterministic identity | Ratified (DEC-0103, DEC-0105 through DEC-0110) |
| Registration and lineage | CT-06 through CT-09 | Per-kind admission with `fp1`-derived id, append-only typed JSONL lineage, human-only signed promotion, persistence via the ratified `qmf-registry → qmf-data` edge without a graph database | Records/lineage/promotion ratified (DEC-0114, DEC-0116, DEC-0120); look-ahead gate `GAP(GAP-0016)`, `GAP(GAP-0017)` deferred (DEC-0121) |
| Data acquisition and research access | CT-10 through CT-15, CT-26 | Seven room-roles per world, bitemporal source evidence, no destructive overwrite, split manifests with the seal enforced now, N-stream journals, CT-15 provider↔Data-Ingest roles with idempotent intake, ratified backup primitives | Ratified (DEC-0117, DEC-0118, DEC-0119); the news-calendar recorder's provider legal archiving posture remains an open operator item; the cTrader tick and bar basis is now a first-connection measured per-broker obligation (DEC-0135) |
| Indicators | CT-16 | Warm-up/readiness (integer observation count), the two-mode batch/streaming equality law as a tier-2 contract test (same-process, same-build, integer-ULP comparator, cold initial state) plus restore-equivalence, package-neutral result, canonical TA-Lib arithmetic comparison | Ratified (DEC-0126, DEC-0127, DEC-0128); per-field detail at documentation time |
| Causal structure | CT-17 | Observed-at/confirmed-at ordering with the in-component emission invariant, confirmation, invalidation, evidence-class reads, parameter identity, no look-ahead | Ratified (DEC-0129); per-field detail at documentation time |
| Venue transport | CT-18 through CT-21 | A venue test double proving the port (a FEAT-0023 done-criterion); UNKNOWN-outcome fixtures carrying each trigger (timeout, transport-error, disconnect); out-of-sequence observation fixtures forcing the owning command to UNKNOWN; compound-command meet-law cases (any child UNKNOWN → parent UNKNOWN, any child rejected → parent partially-executed); a superseded-by-fill cancel read-back; paired-demo secret-reference-only records; capability gating and the fail-closed error map | Venue contracts ratified (DEC-0136, DEC-0137, DEC-0138); the command caller stays node/risk territory, `GAP(GAP-0039)` |
| Risk boundary | CT-22 through CT-25 | Multiplicity (DEC-0115) and the promotion skeleton (DEC-0116) are ratified; Book/BMS, risk, mode, and journal cases stay specification-only until the risk sittings | `GAP(GAP-0039)` through `GAP(GAP-0046)` |

## Proposed component failure fixtures

The proposed FM binding references the component file and FM ID without copying prose into a new source of truth, supplies only concrete input allowed by ratified CT fields, and compares the result with documented behavior. When an FM row names a GAP, the binding remains a blocked specification; it is not test-complete or releasable until the GAP is answered and the eventual test gate passes.

External component FM rows become adapter fixtures: the Given is a recorded or generated external outcome, the When invokes the QMF-owned adapter, and the Then asserts QMF behavior. Tests never claim to verify `COMP-CTRADER`, `COMP-DUKASCOPY`, `COMP-CALENDAR-FEED`, or `COMP-OBJECT-STORAGE` internals.

## Proposed causality and final-holdout fixtures

The causality family includes evidence knowable at a cutoff, evidence unavailable at that cutoff, a late correction, and deterministic replay. Each record carries distinct event-time and knowledge-time (known-at) and a source identity — the ratified bitemporal shape (DEC-0117, DEC-0038). The pass/refusal gate itself is deferred with the backtesting sitting (`GAP(GAP-0016)`, DEC-0121); fixtures may build the ingredients but not assert a gate result.

The seal family references `registry:raw_history_retention_policy`, constructs CT-12 fingerprinted split manifests, exercises default research reads, and checks that no sealed identity appears — the 12-month seal is a `policy rejection` refusal at every read boundary, enforced now, with a frozen TradingDate boundary (DEC-0119). Duration is referenced through `registry:historical_holdout_months`; the one logged final look is a `control action` journal subtype (DEC-0044, DEC-0046, DEC-0119).

Synthetic fixtures carry `source class: synthetic` and may test only infrastructure or failure handling. No synthetic fixture, derived result, or golden scenario may satisfy a trading-edge validation assertion (DEC-0054).

## Provisional acceptance guidance

The acceptance check requires ratified CT schemas and registry values, reproducible provenance, named authority, and replayable evidence, run through the ratified tiers (`poe check` at tier 1, `poe check-integration` at tier 2, `poe check-release` at tier 3) with reference usage shipped as a tier-1 artifact (DEC-0101, DEC-0102). A scenario whose own contract is still GAP-open (risk) remains visible with its GAP IDs, is never converted into a pass by inventing fields or values, and is not test-complete or releasable (DEC-0004, DEC-0096).
