# Epic 1 — qmf-core — Verification PLAN (tier T1)

> **Template provenance / authority note.** The two test-artifact authorities named in the
> lane brief — `_bmad-output/test-artifacts/test-design-qa.md` (Per-Epic Test Plan Template +
> L0-L6 architecture) and `_bmad-output/test-artifacts/test-design/QMX-handoff.md` (the 15
> P0/P1 assertions + risk-gate rows) — **do not exist anywhere in the worktree or the session
> scratchpad** (verified by tree-wide search). This plan therefore reconstructs the 8-section
> per-epic template and the L0-L6 level model from the authorities that DO exist and take
> precedence anyway: this epic's section of `_bmad-output/planning-artifacts/epics.md`
> (Stories 1.1-1.9), the ratified `docs/` knowledge base (`docs/contracts/ct-01..ct-05`,
> `docs/components/qmf-core.md` FM-1..FM-9, `docs/constitution.md`, `docs/scenarios/SCN-0001`,
> `docs/lenses/testing/test-strategy.md`), the mutmut survivor listing
> (`…/scratchpad/battery/mutmut/survivors_summary.tsv`), the L0 scanner baseline
> (`…/scratchpad/battery/l0-scanners.txt`), and the R-001/R-002 assignments in the brief.
> The two named files being absent is itself recorded as an audit finding (see §8).
> **Section 4 was authored WITHOUT reading any `packages/qmf-core/src/**` file** — from
> requirements only, per the load-bearing template rule.

---

## Section 1 — Epic scope, authorities & tier

**Epic 1 (qmf-core) — exact domain foundation.** Wave 1, risk routing H, **audit tier T1**
(highest scrutiny: foundation package; two modules held to 100 % branch coverage; owns the
platform's identity/refusal/money/time laws; mutation-adequacy required — the mutmut survivors
below must be pinned). Runs alone; nothing precedes it.

**FRs covered:** FR-001 (exact money), FR-002 (exact time), FR-003 (identity), FR-004 (typed
refusal), FR-005 (fingerprint/versioning). Plus NFR-02 (the two tier-1 static scanners),
NFR-04 (benchmark slot), NFR-11 (failure register).

**Contracts owned (all ratified):** CT-01 money/price/quantity, CT-02 time/calendar, CT-03
instrument/venue/account identity, CT-04 typed refusal, CT-05 version/fingerprint/result-label.

**Stories & module map (from epics.md 430-737):**

| Story | Subject | Primary module(s) under test | Coverage floor |
|---|---|---|---|
| 1.1 | uv-workspace scaffold, dependency graph, SSSF gate stamp, benchmark slots | pyproject/workspace, `_bench` | tier-1 gate |
| 1.2 | Typed refusal envelope (FR-004, CT-04) | `refusal.py` | 80 % |
| 1.3 | Instrument/venue/account identity (FR-003, CT-03) | `identity.py` | 80 % |
| 1.4 | Exact money/price/quantity (FR-001, CT-01) | `exact.py` | **100 % branch** |
| 1.5 | Exact time/calendars/injected Clock (FR-002, CT-02) | `chrono.py` | **100 % branch** |
| 1.6 | Canonical serializer, fp1, result label, worlds (FR-005, CT-05) | `fingerprint.py` | 80 % |
| 1.7 | Money-path float static scanner (NFR-02→FR-001) | scanner (tools) | package floor |
| 1.8 | Ambient-nondeterminism static scanner (NFR-02→FR-002) | scanner (tools) | package floor |
| 1.9 | Core seams — SecretRef/SecretValue + Observation/Journal/Record/SecretStore sinks | `secret.py`, `sinks.py` | 80 % |

**Precedence for every assertion below:** epics.md AC → CT-0x contract → component FM →
constitution law → test-strategy level table. Source code is **read-only evidence**: a failing
assertion is a FINDING, never a reason to weaken the test or edit `src/`.

---

## Section 2 — Risk register & owned risk-gate rows (P0/P1)

The named QMX-handoff "15 P0/P1 assertions" file is absent; the brief explicitly hands this
epic **R-001** and **R-002**, and the remaining foundation-law rows are reconstructed from
`test-strategy.md` "Law and authority property tests". Rows this epic **owns** (must pass at
its gate) — probability×impact scored for a foundation package whose defects propagate to every
downstream consumer, so impact is uniformly **catastrophic**:

| Risk-gate ID | Assertion (owned by Epic 1) | CT / FM / DEC | Prob | Impact | Prio | Verified at |
|---|---|---|---|---|---|---|
| **R-001** | Mixed unit-kind / currency / unit arithmetic **ALWAYS** refuses — never a silent rescale, round, or cross-tag result | CT-01 FM-4, DEC-0154 | Med | Cat | **P0** | §6 E1-P01/P02 (L1 property) |
| **R-002** | **No public callable raises** across the boundary — every public op returns a value or a `TypedRefusal`; exceptions are reserved for programmer error only | CT-04, DEC-0109 | Med | Cat | **P0** | §6 E1-P03 (L1 property) |
| RG-FLOAT | Binary float on the money path or in fp1 identity content → `invalid input` refusal; float re-enters only at a named boundary stating its rounding mode | CT-01 FM-1, DEC-0105/0108 | High | Cat | **P0** | §4 CT-01, §5 |
| RG-INT64 | int64-ns arithmetic overflow (range 1677-2262) → `invalid input` refusal, **never a wrap**; instant 0 valid; absent time ≠ zero | CT-02 FM-2, DEC-0106 | Med | Cat | **P0** | §4 CT-02, §5 (chrono:171) |
| RG-FP1 | Equal semantic value ⇒ equal fp1 by construction; true collision (same hash, diff bytes) refused+alarmed, idempotent re-write silent | CT-05 FM-6, DEC-0108/0158 | Med | Cat | **P0** | §4 CT-05, §7 |
| RG-CROSSCAL | Cross-calendar TradingDate comparison → refusal; TradingDate never a causality proxy; causality on instants only | CT-02 FM-3, DEC-0106 | Med | High | **P1** | §4 CT-02 |
| RG-TZPIN | Calendar-extension resolved tzdb ≠ pinned tzdata at import → `unavailable dependency` refusal (fingerprint never attests an unused tzdb) | CT-02 FM-5, DEC-0106 | Low | High | **P1** | §4 CT-02, §5 (chrono:1022) |
| RG-SIM | `world = simulated` written to governed evidence → `policy rejection` refusal (reserved-unusable V1, GAP-0048); non-live world never writes live namespace | CT-05 FM-7, DEC-0110 | Low | High | **P1** | §4 CT-05 |
| RG-SECRET | `SecretValue` never renders (repr/str/serialization/logging → reference id); SecretRef excluded from fp1 | FM-9, DEC-0136 | Low | High | **P1** | §4 seams |
| RG-DEPGRAPH | qmf-core depends on nothing; default-deny edges hold; nothing imports qmf-venue/qmf-risk; single fp1 implementation | DEC-0104/0120/0108 | Med | High | **P1** | §4 L3 |

**Mutation-adequacy risk (T1-specific).** mutmut PROVED live holes in the existing suite
(survivors_summary.tsv). Surviving mutants on the money and time modules are **P0/P1 evidence
of missing assertions**; each cluster below (§5) gets a pin test. An un-pinned survivor on
`exact.py`/`chrono.py` blocks the epic's T1 sign-off.

---

## Section 3 — Test-level architecture & allocation (L0-L6)

Level model reconciled with `test-strategy.md` "Test levels" and the L0 scanner baseline; the
brief fixes property tests at **L1**. Rule enforced throughout: **one behaviour, one level,
lower level wins** — a behaviour provable as an L1 unit assertion is NOT re-asserted at L2.

| Level | Scope for Epic 1 | Owner event | In this plan |
|---|---|---|---|
| **L0** | Static / scanner gates: ruff fmt+lint, pyright strict, secret-scan, money-path-float scanner, ambient-nondeterminism scanner, mock-data scanner, import-time budget benchmark | `poe check` (tier 1) | §4 L0 (7 items) — not counted in the L1-L4 totals |
| **L1** | **Unit + property/invariant** (tier 1): pure value construction, validation, failure modes, closed-vocabulary enums, generated-input invariants. Injected clock only; declared seed. | `poe check` (tier 1) | **bulk of the plan** |
| **L2** | **Contract conformance** (tier 2): CT-01..CT-05 public-shape round-trip + boundary suites, run by owner and consumers in isolated per-package envs; version-stamp compatibility | `poe check-integration` | 12 cases |
| **L3** | **Integration** (tier 2): dependency-graph / isolated-build discipline, single-fp1-implementation import-graph, SSSF gate-stamp survival | `poe check-integration` | 4 cases |
| **L4** | **Acceptance scenario** (tier 2): bounded golden chains over qmf-core contracts (SCN-0001; cross-producer fp1 determinism) | `poe check-integration` | 2 scenarios |
| L5 | Non-functional beyond import budget (~40-bot workload at 10/100/200) | benchmark | **deferred** — needs Epics 14-15 (§8) |
| L6 | Release / clean-install smoke on both tier-1 OSes | `poe check-release` (tier 3) | out of epic-plan scope |

**Allocation totals (planned): L1 = 67 · L2 = 12 · L3 = 4 · L4 = 2** (L0 = 7 static/scanner
items tracked separately). Breakdown: L1 = 62 unit (E1-U01..U62) + 5 property (E1-P01..P05).

---

## Section 4 — Independent requirements-derived test list  *(authored pre-source, from requirements only)*

IDs: `E1-U##` L1 unit · `E1-P##` L1 property · `E1-C##` L2 contract · `E1-I##` L3 integration ·
`E1-A##` L4 acceptance · `E1-S##` L0 static/scanner. "◆" marks an assertion that pins a proven
mutmut survivor (detailed in §5). Fixtures: `src`=source evidence, `ctrl`=controlled/golden
vector, `gen`=hypothesis-generated, `synth`=synthetic (infra-only, never edge proof, DEC-0054).

### CT-04 — Typed refusal envelope (Story 1.2, `refusal.py`) — L1

| ID | Assertion | Cite | Fix |
|---|---|---|---|
| E1-U01 | `TypedRefusal` is a frozen-dataclass value carrying `category`, `context`, `retryability`; construct + read-back all three | CT-04 schema | ctrl |
| E1-U02 | `category` is exactly one of the seven values (invalid input, unsupported capability, unavailable dependency, stale evidence, policy rejection, transient venue failure, storage failure); an eighth is not representable | CT-04 enums | ctrl |
| E1-U03 | `retryability` is exactly one of `yes / no / after-condition` | CT-04 enums | ctrl |
| E1-U04 | `after_condition_descriptor` is present **only** when `retryability = after-condition` and absent otherwise (both arms) | CT-04 nullability | ctrl |
| E1-U05 | `context` is always present and a structured object (may be empty), **never null** | CT-04, DEC-0112 | ctrl |
| E1-U06 ◆ | Refusal `context` carries the exact documented keys (`field`, `reason`) with the documented values, and `retryability` carries the exact enum member — not merely "a truthy dict" | CT-04, DEC-0112 | ctrl |
| E1-U07 | `try_create(invalid)` returns the refusal arm; the unchecked constructor remains available for trusted internal use | CT-04, DEC-0109 | ctrl |
| E1-U08 | A refusal is **RETURNED** as a result-union arm, never raised across the public boundary; and never swallowed | CT-04, DEC-0109/0112 | ctrl |

### CT-03 — Instrument / venue / account identity (Story 1.3, `identity.py`) — L1

| ID | Assertion | Cite | Fix |
|---|---|---|---|
| E1-U09 | `Instrument` is the opaque pair `(venue, venue-symbol)`; the symbol is stored verbatim and **never parsed** (exotic/unicode symbol round-trips byte-identical) | CT-03 | ctrl |
| E1-U10 | `VenueId` is an opaque, stable token; two tokens differing only in case are **distinct** (never normalized/derived) | CT-03 | ctrl |
| E1-U11 | `Account` carries exactly one role from the fixed set `live \| demo \| paper-validation \| paper-benched \| prop-firm`; any other role value is refused | CT-03 enums | ctrl |
| E1-U12 ◆ | `try_create` for identity with a **missing/empty/blank venue** returns a typed refusal, never a default | CT-03, CT-04, DEC-0109 | ctrl |
| E1-U13 ◆ | `try_create` for identity with a **missing/empty/blank symbol** returns a typed refusal, never a default | CT-03, CT-04, DEC-0109 | ctrl |
| E1-U14 | Null is prohibited in identity content — absent metadata is an omitted key or simply no dated record, never a null field | CT-03 nullability, DEC-0108 | ctrl |
| E1-U15 | A rename/alias/asset-class/metadata change is a **new dated record pointing at the identity**; stored history is not rewritten (append-only; a correction is a new record) | CT-03 | ctrl |

### CT-01 — Exact money / price / quantity (Story 1.4, `exact.py`) — L1 (100 % branch)

| ID | Assertion | Cite | Fix |
|---|---|---|---|
| E1-U16 | Money/Price/Quantity construct as whole-number scaled integers; Price is instrument-tagged (never single-currency-tagged); Quantity's unit is opaque | CT-01 | ctrl |
| E1-U17 | Every value carries a unit-kind from the closed vocabulary; a **null/absent unit-kind is a typed refusal, never a default** | CT-01, DEC-0154 | ctrl |
| E1-U18 | A binary float passed to `try_create(Money/Price/Quantity)` → `invalid input` refusal (FM-1) | CT-01 FM-1, DEC-0105 | ctrl |
| E1-U19 | A float re-enters only through the named conversion boundary that states its rounding mode explicitly (sanctioned crossing constructs; unstated crossing refuses) | CT-01, DEC-0105 | ctrl |
| E1-U20 | Mixed-scale, same currency/unit, losslessly promotable → auto-promotes to the finer scale (result value correct) | CT-01 FM-4 | ctrl |
| E1-U21 | Mixed-scale, same currency/unit, **not** losslessly promotable → typed refusal; never an implicit rescale or silent round (FM-4) | CT-01 FM-4, DEC-0109 | ctrl |
| E1-U22 | Price − Price → first-class `PriceDelta(instrument, scale)`, a type distinct from Price; pip/point comes from CT-03 metadata, never hardcoded | CT-01, DEC-0131 | ctrl |
| E1-U23 | An absent value-factor → `unavailable dependency` refusal, never a silent conversion | CT-01, DEC-0154 | ctrl |
| E1-U24 ◆ | **Rounding direction at the zero boundary**: for a fractional value at/around zero, the CT-01-required rounding mode selects the exact required integer (assert the boundary at value `< 0` vs `>= 0` and at `= 0` explicitly, per required mode — half-away/half-even/floor/ceil as the mode dictates) | CT-01, DEC-0105 | ctrl |
| E1-U25 ◆ | Scale validation: a scale outside `[0, MAX_SCALE]` (negative, or > max) → refusal; both endpoints exercised | CT-01 | ctrl |
| E1-U26 ◆ | NaN and infinity cannot cross the float conversion boundary → `invalid input` refusal | CT-01, DEC-0105 | ctrl |
| E1-U27 ◆ | The named float boundary requires an **explicit** rounding mode; a missing/None rounding mode → refusal listing the allowed modes | CT-01, DEC-0105 | ctrl |
| E1-U28 | Foreign money is stored verbatim as evidence with its declared scales; an absent declared scale/exponent is a refusal, never an assumed default | CT-01, DEC-0105/0141 | ctrl |

### CT-02 — Exact time / calendars / injected Clock (Story 1.5, `chrono.py`) — L1 (100 % branch)

| ID | Assertion | Cite | Fix |
|---|---|---|---|
| E1-U29 | Instant is an int64 UTC-ns count since the Unix epoch (POSIX no-leap-second); **instant 0 is a valid instant** | CT-02, DEC-0106 | ctrl |
| E1-U30 ◆ | int64 **min/max boundary**: `_INT64_MIN` and `_INT64_MAX` are accepted (strict `<`/`>` at the edge, not `<=`/`>=`); one ns beyond the range → `invalid input` refusal, never a wrap (FM-2) | CT-02 FM-2, DEC-0106 | ctrl |
| E1-U31 | An absent time is an absent field, never a zero sentinel | CT-02, DEC-0106 | ctrl |
| E1-U32 | `CivilDate` and `TradingDate` are distinct types | CT-02 | ctrl |
| E1-U33 | `TradingDate` carries calendar identity + version in-band; equality holds **only** within one calendar identity | CT-02 | ctrl |
| E1-U34 | Cross-calendar TradingDate comparison → typed refusal (FM-3) | CT-02 FM-3 | ctrl |
| E1-U35 | A TradingDate is never derived by formatting an instant, and is never used as a causality proxy | CT-02 | ctrl |
| E1-U36 ◆ | `compare_causal` on **equal instants** → refusal (concurrent; the (instant, writer, sequence) key carries no causal meaning — no tie-break); non-Instant input → `invalid input` refusal with the exact field/reason | CT-02, DEC-0106 | ctrl |
| E1-U37 | `Duration` is signed int64 ns, clock-agnostic and freely storable | CT-02 | ctrl |
| E1-U38 | `Interval` is half-open `[start, end)`; `contains`/`overlaps` correct at both boundaries (end exclusive) | CT-02 | ctrl |
| E1-U39 | Wall and monotonic kinds are type-separated; a `MonotonicReading` is never an Instant and is persistable only as a boot-scoped opaque diagnostic | CT-02 | ctrl |
| E1-U40 | Clock access is a core-defined `Clock` protocol seam; `DataDrivenClock` returns its scripted instants in order (replay) | CT-02, DEC-0022 | ctrl |
| E1-U41 ◆ | `DataDrivenClock` **exhaustion boundary**: when the cursor reaches `len(script)` the next `wall_now`/`monotonic_now` raises `LookupError` with the exact documented message (exhaustion is `>= len`, not `> len`) | CT-02 | ctrl |
| E1-U42 ◆ | `DataDrivenClock` **advances exactly one per call** (cursor `+= 1`, not reset to `1`): three sequential reads return script[0], [1], [2] | CT-02 | ctrl |
| E1-U43 ◆ | `WriterSequencer` mints a per-writer strictly-increasing sequence from the declared `start` (default and custom); `OrderingKey` carries the real `instant` and `writer` (not None) | CT-02, DEC-0106 | ctrl |
| E1-U44 ◆ | `verify_tzdb_pin`: resolved ≠ pinned → `unavailable dependency` refusal whose context field is `tzdata_version`; an empty pinned or resolved version string is itself refused | CT-02 FM-5, DEC-0106 | ctrl |
| E1-U45 | `render_utc_iso8601` is display-only and labelled; a non-Instant input → `invalid input` refusal | CT-02, DEC-0108 | ctrl |
| E1-U46 | `WriterId` is minted per (machine, role, stream) with a boot/epoch id; a monotonic reading carries and is scoped to its boot id, never compared across boots | CT-02, DEC-0106 | ctrl |

### CT-05 — Canonical serializer, fp1, result label, worlds (Story 1.6, `fingerprint.py`) — L1

| ID | Assertion | Cite | Fix |
|---|---|---|---|
| E1-U47 | fp1 emits the form `fp1:sha256:<lowercase-hex>` | CT-05 | ctrl |
| E1-U48 | A float anywhere in identity content → refusal (floats refused in identity; never a hash of float bytes) | CT-05, DEC-0108 | ctrl |
| E1-U49 | Null is prohibited: an absent value is an **omitted key**, never serialized as null | CT-05, DEC-0108 | ctrl |
| E1-U50 | Canonical bytes: object keys sorted lexicographically at every depth, no insignificant whitespace, NFC-normalized strings, order-significant arrays (byte-level determinism) | CT-05, DEC-0108 | ctrl |
| E1-U51 | Equal semantic input ⇒ equal fp1; a single differing identity field ⇒ different fp1 | CT-05 | ctrl |
| E1-U52 | Idempotent byte-identical re-write accepted silently; a true collision (same hash, differing bytes) refused **and alarmed**, never overwritten (FM-6) | CT-05 FM-6, DEC-0108 | ctrl |
| E1-U53 | `ResultLabel` identity parts (producer contract identity, format version, input fingerprints, evidence time range, computation identity, evidence class, world) **are** its identity; the occurrence record sits outside identity | CT-05, DEC-0110 | ctrl |
| E1-U54 | `world = simulated` into governed evidence → `policy rejection` refusal (FM-7); world ∈ `live \| replay \| simulated` | CT-05 FM-7, GAP-0048 | ctrl |
| E1-U55 | A non-live world never writes the live evidence namespace (storage separation, not identity alone) | CT-05, DEC-0110 | ctrl |
| E1-U56 | Producer contract identity distinguishes producers — `EMA(20)` and `SMA(20)` can never share a result label | CT-05, DEC-0131 | ctrl |

### Story 1.9 — Core seams: secrets & injected sinks (`secret.py`, `sinks.py`) — L1

| ID | Assertion | Cite | Fix |
|---|---|---|---|
| E1-U57 | `SecretValue` never renders its secret in `repr`, `str`, serialization, or logging — each yields only the reference id (FM-9) | AR-37, DEC-0136 | ctrl |
| E1-U58 | `SecretRef` constructed from a non-opaque reference → `invalid input` refusal | DEC-0136, DEC-0109 | ctrl |
| E1-U59 | The four sink protocols (`ObservationSink`, `JournalSink`, `RecordSink`, `SecretStore`) are `typing.Protocol` seams; `qmf-core` itself performs no I/O and spawns no work | AD-15, DEC-0138 | ctrl |
| E1-U60 | A sink's refusal for an unpersistable write is a **CT-04 typed refusal** (category, context, retryability) the caller can branch on for block-on-unpersistable semantics | CT-04, AR-47 | ctrl |
| E1-U61 | `SecretStore` exposes read + atomic replace only; no getter path returns plaintext outside `SecretValue`'s controlled access | AR-37/38 | ctrl |
| E1-U62 | A `SecretRef`/`SecretValue` is excluded from fp1 identity (a credential is a deployment fact, never a market fact) | DEC-0136, DEC-0108 | ctrl |

### L1 — property / invariant (hypothesis) — see §6 for full spec

`E1-P01` (R-001 mixed-tag refusal) · `E1-P02` (R-001 mixed-scale promote-or-refuse) ·
`E1-P03` (R-002 no-raise total function) · `E1-P04` (float-in-identity always refuses) ·
`E1-P05` (fp1 canonical-form equality: 6/4 ≡ 3/2 and cross-scale ⇒ equal fp1). `gen`.

### L2 — contract conformance (isolated per-package env, owner + consumer)

| ID | Assertion | Cite |
|---|---|---|
| E1-C01 | CT-01 round-trip: scaled-integer canonical encode/decode semantic equality | CT-01 |
| E1-C02 | CT-01 boundary suite: unit-kind vocabulary, scale range, nullability, malformed-payload → refusal | CT-01 |
| E1-C03 | CT-02 round-trip: Instant / TradingDate / Duration / Interval encode/decode | CT-02 |
| E1-C04 | CT-02 boundary suite: range 1677-2262, in-band calendar identity, wall/monotonic separation, malformed | CT-02 |
| E1-C05 | CT-03 round-trip: `(venue, opaque symbol)` + dated records | CT-03 |
| E1-C06 | CT-03 boundary suite: role enum, symbol opacity, nullability | CT-03 |
| E1-C07 | CT-04 round-trip: refusal encode/decode | CT-04 |
| E1-C08 | CT-04 boundary suite: seven categories, retryability enum, after-condition presence rule | CT-04 |
| E1-C09 | CT-05 round-trip: fingerprint string + result label encode/decode | CT-05 |
| E1-C10 | CT-05 boundary suite: recipe determinism, float-refused, null-omission, world enum, collision split | CT-05 |
| E1-C11 | Every serialized CT-01..CT-05 artifact stamps integer **format version = 1** (versioning-from-birth; meaning never mutates) | DEC-0103 |
| E1-C12 | Contract tests execute in an **isolated per-package environment**, run by owner and by a consumer stub (test-only dep is not a runtime edge) | DEC-0100/0102 |

### L3 — integration / dependency discipline

| ID | Assertion | Cite |
|---|---|---|
| E1-I01 | Isolated per-package build: an **undeclared import fails** the isolated build (AR-06/AR-18) | DEC-0100 |
| E1-I02 | Dependency-graph discipline: qmf-core depends on nothing; default-deny edges hold; **nothing imports qmf-venue or qmf-risk**; the sole inter-library edge is qmf-registry→qmf-data | DEC-0104/0120 |
| E1-I03 | **Single fp1 implementation**: no package computes a fingerprint except by calling qmf-core (import-graph / AST check over the workspace) | CT-05, DEC-0108 |
| E1-I04 | SSSF factory-gate stamp preserved: workspace-root `[dependency-groups] dev` and `testpaths = ["adws/tests"]` survive; `ruff/mypy/pytest adws/tests` still pass (gate never RED for inability to run) | Story 1.1 |

### L4 — acceptance scenario (golden chain)

| ID | Assertion | Cite |
|---|---|---|
| E1-A01 | **SCN-0001 core-freeze-gate**: the six ratified boundaries conform to CT-01..CT-05 by construction; the two still-open freeze choices (backtest fidelity taxonomy GAP-0048, SR* threshold GAP-0049) are **not** fixed by code or serialized data — a proposal cannot replace a null contract field | SCN-0001, DEC-0134 |
| E1-A02 | **Cross-producer fp1 determinism** (replay reproducibility as a platform property): two independent conformant producers emit byte-identical fp1 over a golden artifact set; re-derivation under a newer calendar identity / tzdata version mints a new fingerprint **plus a lineage edge**, never a rewrite, never a silent equality | CT-05, DEC-0103 | ctrl |

### L0 — static / scanner gates (tracked, not in L1-L4 totals)

`E1-S01` money-path-float scanner **must-flag** (undeclared float reaching the money path) ·
`E1-S02` money-path scanner **must-not-flag** (sanctioned named-boundary crossing) ·
`E1-S03` ambient-nondeterminism scanner **must-flag** (`datetime.now`, `time.time`/`monotonic`,
unseeded `random` below the composition root) · `E1-S04` ambient scanner **must-not-flag**
(injected `Clock` usage) · `E1-S05` both scanners wired into `poe check`; a flagged violation
fails the gate with nonzero exit · `E1-S06` ruff fmt+lint / pyright strict / secret-scan clean
· `E1-S07` import-time budget benchmark: `import qmf.core` completes well under one second
(`registry:core_import_time_budget`, NFR-04/DEC-0111).

---

## Section 5 — Mutation-survivor pin tests (mutmut-proven holes)

Source: `…/scratchpad/battery/mutmut/survivors_summary.tsv`. Each surviving mutant is a
behaviour the existing suite does not observe. The four holes named in the brief plus the
adjacent survivors on the same money/time surfaces are pinned by the §4 assertions marked ◆.
A pin test must **fail against the mutant and pass against the original** — asserting the exact
value/direction/message, not mere presence.

| Survivor (file:line · symbol) | What the mutant proves is unobserved | Pin test | Exact pin |
|---|---|---|---|
| `exact.py:304` `_round_fraction_to_int` (`< 0` → `<= 0` / `< 1`, and ceil/floor swap) | **Rounding direction at the zero boundary is unpinned** (money-relevant) | **E1-U24** | Feed a fraction at value `< 0`, `= 0`, and `> 0` and assert the exact integer the CT-01 rounding mode requires at each — kills both the `<=0`/`<1` shifts and the ceil/floor swap |
| `chrono.py:171` `_checked_int64` (`<` → `<=`, `>` → `>=`) | **int64 min/max boundary values untested** | **E1-U30** | `_INT64_MIN` and `_INT64_MAX` must be **accepted**; `_INT64_MIN-1` / `_INT64_MAX+1` must refuse (FM-2). Edge-inclusive asserts kill the `<=`/`>=` mutants |
| `chrono.py:756` `DataDrivenClock.wall_now` & `:764` `monotonic_now` (`>=` → `>`; `+= 1` → `= 1`; message→None) | **Exhaustion boundary + advance-per-call untested** | **E1-U41, E1-U42** | Exhaust at exactly `len(script)` and assert `LookupError` with the exact message; read three times and assert script[0],[1],[2] (kills `= 1` reset) |
| `exact.py:251` `_require_instrument` (`!= ""` → `!= "XX"`) | **Instrument symbol/venue emptiness checks weak** | **E1-U12, E1-U13** | Empty, blank (`"  "`), and missing venue **and** symbol each → typed refusal (not default). Strip-then-compare exercised for both fields |
| `exact.py:225` `_bad_scale` (message→None; `repr(scale)`→`repr(None)`; drop `given`) | Scale-range refusal payload unobserved | **E1-U25** | Assert the refusal message text and that `given` echoes the offending scale |
| `exact.py:337` `_coerce_float_to_scaled_int` (NaN/inf branch, missing-rounding branch, messages) | NaN/inf and missing-rounding-mode branches unobserved | **E1-U26, E1-U27** | NaN and inf each refuse; a `None` rounding mode refuses listing `allowed=[modes]` |
| `chrono.py:1022` `verify_tzdb_pin` (empty-string checks, `given=repr(None)`, message keys) | Empty pinned/resolved version + context key unobserved | **E1-U44** | Empty pinned and empty resolved each refuse; mismatch refuses with context field `tzdata_version` and the FM-5 reason text |
| `chrono.py:995` `compare_causal` (message→None, `instant=None`, equal-instant branch) | Equal-instant concurrency + bad-input payload unobserved | **E1-U36** | Equal instants → refusal with the "no tie-break" reason; non-Instant input → `invalid input` with the exact field/reason |
| `chrono.py:881/895` `WriterSequencer` (`start=0`→`1`; `instant=None`, `writer=None`) | Sequence start + OrderingKey field wiring unobserved | **E1-U43** | Default start and a custom start both verified; `OrderingKey.instant`/`.writer` carry the passed values |
| `exact.py:166/182`, `chrono.py:108/125/137` `_invalid`/`_unavailable`/`_policy` (context keys `field`/`reason`; `retryability=NO`→`None`) | Refusal-helper context **structure** unobserved (tests assert presence, not shape) | **E1-U06** | Assert refusal `context == {"field": …, "reason": …}` with real values and the exact `retryability` enum member — kills key-rename and `retryability=None` mutants |

> Note: the remaining survivors are string-literal case/quote mutations inside refusal messages.
> They are pinned wherever a §4 assertion checks the **exact** message text (E1-U06, U24, U26,
> U27, U36, U44); message-only mutants with no behavioural contract are recorded as accepted
> (message wording is not ratified surface) rather than chased with brittle asserts.

---

## Section 6 — Property / invariant tests — R-001 & R-002 (hypothesis, L1)

Run at tier 1 with a **declared seed**; the injected `Clock` only (never the system clock). No
generated result may validate trading edge (DEC-0054). Missing lib: `uv run --with hypothesis`.

**E1-P01 — R-001 (mixed-tag arithmetic ALWAYS refuses).** *Strategy:* generate pairs of exact
values (Money/Price/Quantity/PriceDelta) with **deliberately mismatched** unit-kind, currency,
instrument, or unit tag. *Invariant:* every arithmetic and comparison operation returns a
`TypedRefusal` — **never** a value, never a silent cross-tag coercion, rescale, or round.
*Authority:* CT-01 FM-4, DEC-0154 dimensional unit-kind law. *Anti-cheat:* also assert the
refusal category is from the CT-04 vocabulary, so "refuses" cannot degrade to "raises".

**E1-P02 — R-001 companion (mixed-scale = promote-or-refuse).** *Strategy:* same currency/unit,
generated scale pairs. *Invariant:* losslessly-promotable pairs always yield the finer-scale
value with the mathematically exact result; non-promotable pairs always refuse — the set
`{value, refusal}` is total and disjoint, with **no** silent rounding path.

**E1-P03 — R-002 (no public callable raises across the boundary).** *Strategy:* enumerate the
public callables of `qmf.core` and drive each with generated valid **and** invalid domain inputs
(out-of-range scales, empty tags, floats, overflowing ns, mismatched calendars, malformed
labels). *Invariant:* each call returns **either a value or a `TypedRefusal`** — it never raises
across the boundary. Exceptions are permitted **only** for genuine programmer error (wrong
Python type / arity), which the property classifies and excludes. *Authority:* CT-04, DEC-0109.
This is the epic's widest-blast-radius property: every downstream consumer branches on this.

**E1-P04 — float-in-identity always refuses.** *Strategy:* generate nested identity structures
with a float injected at a random depth/position. *Invariant:* fingerprinting refuses (floats
inadmissible in identity content); no path hashes float bytes. *Authority:* CT-05, DEC-0108.

**E1-P05 — fp1 canonical-form equality.** *Strategy:* generate rationals with common factors
and money-class values stored at differing scales. *Invariant:* semantically equal values
(`6/4` vs `3/2`; one amount at two scales) always produce the **same** fp1; the canonical form
(lowest terms, positive denominator, sign on numerator, declared storage scale) makes equal
value ⇒ equal fingerprint by construction, so no representation fork escapes CT-05's collision
detector. *Authority:* CT-01 canonical form, CT-05, DEC-0158.

---

## Section 7 — Traceability & coverage matrix

| FR / CT | Story | FM proven | L1 | L2 | L3 | L4 | Coverage floor |
|---|---|---|---|---|---|---|---|
| FR-001 / CT-01 | 1.4 | FM-1, FM-4 | U16-U28, P01/P02/P05 | C01/C02/C11 | I03 | A02 | **100 % branch** |
| FR-002 / CT-02 | 1.5 | FM-2, FM-3, FM-5 | U29-U46 | C03/C04/C11 | — | — | **100 % branch** |
| FR-003 / CT-03 | 1.3 | — | U09-U15 | C05/C06/C11 | — | — | 80 % |
| FR-004 / CT-04 | 1.2 | FM-8 | U01-U08, P03 | C07/C08/C11/C12 | — | — | 80 % |
| FR-005 / CT-05 | 1.6 | FM-6, FM-7 | U47-U56, P04/P05 | C09/C10/C11 | I03 | A01/A02 | 80 % |
| NFR-02 scanners | 1.7, 1.8 | — | — | — | — | — | S01-S05 (L0) |
| Seams/secrets | 1.9 | FM-9 | U57-U62 | — | — | — | 80 % |
| Dep graph / gate | 1.1 | — | — | — | I01/I02/I04 | A01 | tier-1 gate |
| NFR-04 import budget | 1.1 | — | — | — | — | — | S07 (L0) |

**Coverage discipline:** the 100 % branch requirement on `exact.py` and `chrono.py` (DEC-0101)
is verified as **branch** coverage, and a coverage number is **never** substituted for a
behaviour assertion (DEC-0096). Mutation adequacy (§5) is the T1 backstop against
high-coverage/low-assertion suites — the very failure the survivors expose.

---

## Section 8 — Untestable requirements, deferrals & exit criteria

**Recorded as untestable now (with reason):**

1. **`world = simulated` positive behaviour / backtest fidelity taxonomy (GAP-0048) and SR*
   threshold (GAP-0049).** The *refusal* (FM-7, E1-U54) is fully testable; the *simulated-time
   typing* it guards is an **open freeze choice** — not test-complete until the backtesting
   sitting (DEC-0134). A test must never turn the open GAP into a passing fixture.
2. **Money-path taint ACROSS package seams (DEC-0026/0105).** In Epic 1 the seam partners
   (qmf-data, qmf-venue, qmf-risk) do not exist. The single-package taint + the L0 money-path
   scanner are testable now; the **cross-seam** taint property is deferred to the epics that
   introduce the downstream packages (3+). Recorded, not asserted here.
3. **~40-bot reference workload benchmark at the 10/100/200 marks (NFR-04/AR-22).** Explicitly
   deferred until the QMB run loop and orchestrator exist (Epics 14-15). Only the import-time
   budget (E1-S07) is measurable in Epic 1.
4. **`after_condition_descriptor` internal field shape (CT-04).** Its presence/absence rule
   (E1-U04) is testable; its field-level shape is **"not pinned by AD-11"** — no ratified schema
   exists, so that sub-structure is untestable by design.
5. **The specific CT-04 category for cross-calendar comparison (FM-3, E1-U34).** The spine pins
   *that a typed refusal is returned* but **not which category**; the test asserts a refusal and
   its context, and must not over-fit a category the spine leaves open.
6. **`prop-firm` account role (CT-03).** Representable in the enum (E1-U11) but a **reserved
   seam only in V1 — no prop firm is modeled**; there is no prop-firm behaviour to assert.

**Process finding (raised by this plan):** the two named test-artifact authorities
(`test-design-qa.md`, `QMX-handoff.md`) are **absent from the worktree** — the template and the
"15 P0/P1 assertions" had to be reconstructed. Logged as an audit finding so the handoff gap is
visible, not silently absorbed.

**Exit criteria for Epic 1 (T1):** (a) all L1 unit + property tests pass; (b) branch coverage =
100 % on `exact.py` and `chrono.py`, ≥ 80 % on every other module (DEC-0101); (c) **zero
surviving mutants** on `exact.py`/`chrono.py` for the clusters in §5 after the pin tests land;
(d) L2 CT-01..CT-05 conformance passes in isolated per-package envs, each stamping format
version 1; (e) L3 dependency-discipline and single-fp1 checks pass; (f) L4 SCN-0001 and the
cross-producer determinism golden pass; (g) L0 scanners + import-budget benchmark green in
`poe check`; (h) reference-usage examples ship for every CT (DEC-0096); (i) every untestable
item above carries an explicit GAP/deferral record — an explicit GAP records why a test cannot
exist but never counts as a passing test (DEC-0004).
