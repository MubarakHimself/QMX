---
id: LENS-TEST-FIXTURES
title: QMF Fixtures and Golden Scenarios
type: lens
status: ratified
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP, COMP-QMN, COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, COMP-OBJECT-STORAGE]
decisions: [DEC-0004, DEC-0007, DEC-0026, DEC-0029, DEC-0030, DEC-0033, DEC-0038, DEC-0044, DEC-0045, DEC-0046, DEC-0054, DEC-0096, DEC-0101, DEC-0102, DEC-0106, DEC-0108, DEC-0110, DEC-0117, DEC-0118, DEC-0119, DEC-0121, DEC-0126, DEC-0127, DEC-0128, DEC-0129, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0143, DEC-0146, DEC-0147, DEC-0149, DEC-0150, DEC-0151, DEC-0152, DEC-0155, DEC-0157, DEC-0201, DEC-0204, DEC-0205, DEC-0206, DEC-0208, DEC-0209, DEC-0228, DEC-0234, DEC-0236]
sources: [_docwork/ledger.yaml, _docwork/gaps.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-NODE-2026-08-28/ARCHITECTURE-SPINE.md, docs/constitution.md, docs/architecture/dependencies.yaml, docs/decisions/ADR-0019-trading-node.md, docs/components/trading-node.md, docs/registry/variables.yaml, docs/components/, docs/contracts/, docs/lenses/testing/test-strategy.md]
generated: 2026-08-18
verified: 2026-08-29
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
| Venue transport | CT-18 through CT-21 | A venue test double proving the port (a FEAT-0023 done-criterion); UNKNOWN-outcome fixtures carrying each trigger (timeout, transport-error, disconnect); out-of-sequence observation fixtures forcing the owning command to UNKNOWN; compound-command meet-law cases (any child UNKNOWN → parent UNKNOWN, any child rejected → parent partially-executed); a superseded-by-fill cancel read-back; paired-demo secret-reference-only records; capability gating and the fail-closed error map | Venue contracts ratified (DEC-0136, DEC-0137, DEC-0138); the command caller stays node/risk territory (DEC-0142) |
| Risk boundary | CT-22 through CT-25, CT-27 through CT-32 | Book-definition and BMS-definition round-trips with inline identity-bearing numbers and `pending` slots; the bind-time capability check and the blank-admission-bar live-binding `policy rejection`; the CT-23 two-intent-family port with close_partial an `unsupported capability` refusal; the exit record one-per-virtual-position with the bench predicate `realized_r <= -q`; control-action kinds honoring the exit-preservation invariant; the control-window entries-only live-and-paper block; same-tick arbitration strictly by declared rank | Risk contracts ratified surface, defined-unwired (DEC-0143 through DEC-0155); integration and runtime blocked until the node wires them |

The ratified risk surface carries four golden scenarios that draw every value from a contract field or registry entry, never an invented constant, since every risk number is a configurable UI-editable variable with no spine value (DEC-0157). [SCN-0006](../../scenarios/SCN-0006-book-paper-transition.md) walks a Book paper transition as a dated change of the Book-to-BMS binding where any real-money touch is operator-signed and paper performance never authorizes a return to live (DEC-0149). [SCN-0008](../../scenarios/SCN-0008-pair-scoped-news.md) walks a pair-scoped protection window that blocks new entries live and paper alike, its instrument scope resolved through dated currency-exposure records and failing closed on unknown coverage (DEC-0152). [SCN-0010](../../scenarios/SCN-0010-risk-boundary-conflicts.md) walks same-tick risk-boundary conflicts resolved at one arbitration point per command stream, strictly by declared rank, the exit-preservation invariant holding under every arbitration (DEC-0151, DEC-0150). [SCN-0011](../../scenarios/SCN-0011-qualifying-loss-bench.md) walks a qualifying-loss bench sequence where the bench counter is a read-time fold over the exit-record stream, breakevens never count, and a later intent on the same seat refuses `stale evidence` when the prior exit record has not yet persisted (DEC-0155). Each stays defined-unwired: its contract fixtures conform, but no runtime executes it until the node wires the risk contracts (DEC-0143 through DEC-0155). The trading node (COMP-QMN, FEAT-0031) is that wirer: it wires all four golden scenarios and proves them as items on its week-long unattended soak acceptance gate, so the runtime proof lands with the node and nowhere earlier (DEC-0208). The node fixture classes and the golden-scenario binding rows that carry those proofs are set out in "Trading-node fixture classes (TN-23)" below.

## Proposed component failure fixtures

The proposed FM binding references the component file and FM ID without copying prose into a new source of truth, supplies only concrete input allowed by ratified CT fields, and compares the result with documented behavior. When an FM row names a GAP, the binding remains a blocked specification; it is not test-complete or releasable until the GAP is answered and the eventual test gate passes.

External component FM rows become adapter fixtures: the Given is a recorded or generated external outcome, the When invokes the QMF-owned adapter, and the Then asserts QMF behavior. Tests never claim to verify `COMP-CTRADER`, `COMP-DUKASCOPY`, `COMP-CALENDAR-FEED`, or `COMP-OBJECT-STORAGE` internals.

## Proposed causality and final-holdout fixtures

The causality family includes evidence knowable at a cutoff, evidence unavailable at that cutoff, a late correction, and deterministic replay. Each record carries distinct event-time and knowledge-time (known-at) and a source identity — the ratified bitemporal shape (DEC-0117, DEC-0038). The pass/refusal gate itself is deferred with the backtesting sitting (`GAP(GAP-0016)`, DEC-0121); fixtures may build the ingredients but not assert a gate result.

The seal family references `registry:raw_history_retention_policy`, constructs CT-12 fingerprinted split manifests, exercises default research reads, and checks that no sealed identity appears — the 12-month seal is a `policy rejection` refusal at every read boundary, enforced now, with a frozen TradingDate boundary (DEC-0119). Duration is referenced through `registry:historical_holdout_months`; the one logged final look is a `control action` journal subtype (DEC-0044, DEC-0046, DEC-0119).

Synthetic fixtures carry `source class: synthetic` and may test only infrastructure or failure handling. No synthetic fixture, derived result, or golden scenario may satisfy a trading-edge validation assertion (DEC-0054).

## Provisional acceptance guidance

The acceptance check requires ratified CT schemas and registry values, reproducible provenance, named authority, and replayable evidence, run through the ratified tiers (`poe check` at tier 1, `poe check-integration` at tier 2, `poe check-release` at tier 3) with reference usage shipped as a tier-1 artifact (DEC-0101, DEC-0102). A scenario whose own contract is still GAP-open (risk) remains visible with its GAP IDs, is never converted into a pass by inventing fields or values, and is not test-complete or releasable (DEC-0004, DEC-0096).

## Trading-node fixture classes (TN-23)

The trading node (COMP-QMN, FEAT-0031) is the application that wires the risk contracts and the four golden scenarios, and its acceptance is a machinery-proof soak checklist rather than a performance claim (DEC-0208). The fixture classes below carry the node's own proofs; every value is drawn from a contract field or a registry row, never an invented constant, since every risk number is a configurable UI-editable variable with no spine value (DEC-0157, DEC-0208).

| Node fixture class | Stable proof key | What it exercises |
|---|---|---|
| Venue conformance double | `qmn/conformance/<trigger>` | The FEAT-0023 conformance double as the third `VenueClientPort` implementation, driven through the one suite that the double and the live cTrader client both pass, carrying UNKNOWN-outcome fixtures per trigger (`timeout | transport-error | disconnect`) and the superseded-by-fill cancel read-back (DEC-0208, DEC-0228). |
| UNKNOWN per trigger | `qmn/unknown/<trigger>` | Each command-uncertainty trigger mints an explicit UNKNOWN observation carrying its trigger, cleared only by `resolve_unknown` (DEC-0208, DEC-0209). |
| Forced disconnect mid-order | `qmn/disconnect-mid-order` | A disconnect mid-order mints UNKNOWN and **blocks the whole stream, protection included**; a protective close issued under the block stands as a journaled standing protection intent that dispatches on resolution, never refused-and-lost and never dispatched into the uncertainty (DEC-0208, DEC-0209). |
| Operator-signed synthetic kill-line breach | `qmn/kill-line-breach/paper` | An operator-signed synthetic breach against the running paper ledger auto-flattens that binding and stands it down, so the one control that flattens without a human is drilled before live (DEC-0208). |
| News-window narrowing revision | `qmn/news-window/narrowing-revision` | A news-calendar revision that would narrow an in-force window is proven **not** to open entries before that window's declared end, while a widen is honoured forward-only (DEC-0208). |
| AD-37 compose pair | `qmn/compose-pair/suspend-plus-flatten` | A KSA `suspend_new` and a kill-line breach falling on one tick **both execute**, neither suppressing the other (DEC-0208, DEC-0209). |
| Demo-conditioned baseline vs `role = live` | `qmn/baseline/demo-vs-live` | A demo-conditioned SQS baseline is proven **not** to satisfy a `role = live` binding; at the week's end a live-conditioned SQS baseline and a live-path rung baseline on the deployment tuple are present and satisfy the bind-time check (DEC-0208, DEC-0205). |
| Clock-band injection | `qmn/clock-band/breach` | A simulated clock-band breach produces the entry-side `no-new-entry` effect and pushes an alert (DEC-0208). |
| Disk-headroom | `qmn/disk-headroom` | Measured bytes-per-day and the disk budget are recorded, and the hot-room retention purge is proven to require a verified sealed-archive copy and a verified off-host copy before it runs (DEC-0208). |
| Crash-loop and stand-down | `qmn/crash-loop/stand-down` | A crash-loop boots into stand-down with the doors serving; a detected preflight refusal enters stand-down without exiting and without advancing the crash-loop counters; a requested restart exits code 75 and restarts cleanly; and only an operator `resurrect` (journaled under `node_resurrect`) leaves stand-down, a Book-minted exit proving to pass throughout (DEC-0208, DEC-0204). |
| Powers-principal refusal | `qmn/powers/principal-refusal` | The powers door refuses a call whose peer credential is neither declared principal and refuses every trading, protection, promotion and settings power to the ops principal — an agent signer among them (DEC-0208, DEC-0234). |
| Replay diff | `qmn/replay/soak-day` | A replay of a recorded soak day diffs clean from a process outside the node that resolves no credential — decisions only, no fill simulation (DEC-0208, DEC-0206). |

### Golden-scenario binding rows

The four risk golden scenarios stay defined-unwired until the node wires them, and each binds to the soak checklist item(s) that prove it (DEC-0208):

| Scenario | Node fixture binding | Soak checklist proof |
|---|---|---|
| [SCN-0006](../../scenarios/SCN-0006-book-paper-transition.md) — Book paper transition | `qmn/paper-transition` over the CT-24 transition stream and the per-intent execution target | A connectivity escalation on the live connection proven not to block paper routing to the paired demo stream; a restart re-deciding a standing intent without re-arming a Book left in PAPER; and SCN-0006 wired and proven (DEC-0208, DEC-0205). |
| [SCN-0008](../../scenarios/SCN-0008-pair-scoped-news.md) — pair-scoped news window | `qmn/news-window` and `qmn/news-window/narrowing-revision` | A news window and a dead zone block entries while an exit passes; a news-calendar revision proven not to open entries before the in-force window's declared end; and SCN-0008 wired and proven (DEC-0208). |
| [SCN-0010](../../scenarios/SCN-0010-risk-boundary-conflicts.md) — same-tick arbitration | `qmn/compose-pair/suspend-plus-flatten` on one command stream | The AD-37 compose pair (`suspend_new` + kill-line breach) both executing on one tick, neither suppressing the other; and SCN-0010 wired and proven (DEC-0208, DEC-0209). |
| [SCN-0011](../../scenarios/SCN-0011-qualifying-loss-bench.md) — qualifying-loss bench | `qmn/bench-fold` over the CT-29 exit-record stream | The bench fold benching a seat on qualifying losses, the seat routing to the paired target while the Book stays LIVE; and SCN-0011 wired and proven (DEC-0208). |

Each binding draws its values from the CT contract fields and registry rows the scenario cites, never from scenario-local literals; a fixture that cannot resolve a value carries its `GAP(GAP-*)` marker and stays blocked rather than inventing one (DEC-0157, DEC-0208).
