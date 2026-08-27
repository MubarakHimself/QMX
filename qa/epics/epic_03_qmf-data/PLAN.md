# Verification Plan — Epic 3: qmf-data (evidence store & journals)

- **Epic:** Epic 3 — `qmf-data` — evidence store & journals (Wave 2, priority H)
- **Package under test:** `packages/qmf-data` (`qmf.data.*`)
- **Tier:** T1 (`poe check`: fmt + lint + types + unit + coverage; property fixtures at tier 1)
- **FRs covered:** FR-010, FR-011, FR-012, FR-013, FR-016
- **Contracts:** CT-10 (source observation), CT-11 (evidence persistence), CT-12 (dataset split & seal), CT-13 (journal); consumed: CT-04 (typed refusal), CT-05 (fp1), CT-01/02/03 (values), CT-25 (risk-journal join surface, defined-unwired), CT-26/CT-09 (store/registry-room seams)
- **Author stance:** Section 4 (Independent Test List) was authored from the requirements corpus (epics.md, docs/contracts, docs/components, docs/scenarios, the ratified test-strategy lens) BEFORE any `packages/qmf-data/**/*.py` source file was opened. Source is read-only evidence; a failing planned test is a FINDING, never a licence to edit source or weaken the test.

> **Template-provenance caveat (load-bearing for the reader).** The two named authorities `_bmad-output/test-artifacts/test-design-qa.md` and `.../test-design/QMX-handoff.md` are **absent from this worktree** (`_bmad-output/test-artifacts/` does not exist). The 8-section per-epic shape below, the L0–L6 test-level architecture, and the "one behaviour one level, lower level wins" rule are reconstructed from `docs/lenses/testing/test-strategy.md` + `docs/lenses/testing/fixtures-and-scenarios.md` (both ratified) and from the P0-assertion / risk-gate content embedded verbatim in the lane task. Where a downstream reconciliation against the real test-design-qa.md is possible, treat that file as authoritative over this reconstruction.

---

## Section 1 — Epic Charter & Scope-Under-Test

`qmf-data` is the public data-policy library: it preserves source evidence, governs reproducible research access, and emits durable journal evidence, across seven room-roles instantiated **per world**. It depends only on `qmf-core` and its internal `qmf-data-store` seam; the sole ratified inbound inter-library edge is `qmf-registry → qmf-data` (DEC-0120).

**In scope (this epic, six stories):**

| Story | Title | Primary FR / CT |
|---|---|---|
| 3.1 | Dependency-free store seam over swappable engines | FR-016 / CT-11 (+CT-13, CT-09, CT-26) |
| 3.2 | Bitemporal source observations, append-only corrections | FR-010 / CT-10 |
| 3.3 | Seven room-roles per world, cross-world refusal | FR-011 / CT-11 |
| 3.4 | Dataset splits + 12-month no-peek seal | FR-012 / CT-12 |
| 3.5 | Durable journals — seven event types, gapless per-writer streams | FR-013 / CT-13 |
| 3.6 | Read-time entity-journal projections (logbooks) | FR-013 / CT-13, CT-25 |

**Epic-specific priority — evidence integrity.** Errors in this epic are *unrecoverable*: an overwritten raw observation, a leaked sealed row, or a cross-world read cannot be undone by a later fix. Verification weight is therefore concentrated on the **refusal boundaries** (append-only, seal, world isolation) rather than on happy-path round-trips.

**Explicitly out of scope / deferred (verified as blocked, not gaps in this plan):** the CT-08 look-ahead/causality registration gate and attempt counter (GAP-0016/0017, DEC-0121); numeric backup RPO/RTO/retention (node/ops sitting); per-kind BarSpec aggregation arithmetic and the tick-to-bar builder (Deferred table); journal retention/trim numerics (post-measured-volume). See Section 8.

---

## Section 2 — Authorities, Precedence & Requirement Inventory

**Precedence read (highest first):** epics.md §Epic 3 → `docs/contracts/ct-{10,11,12,13,04}` + `docs/components/qmf-data.md` + `docs/constitution` + `docs/scenarios/SCN-{0002,0003}` → (test-design-qa.md — absent, reconstructed) → (QMX-handoff.md — absent, content taken from lane task).

**Requirement inventory (the map every planned test traces to):**

| Req | Source | Behaviour to prove | FM | SCN |
|---|---|---|---|---|
| FR-010 | CT-10 / Story 3.2 | Bitemporal fact carries event-time, known-at, source⊥VenueId, revision, writer+boot+seq, world, fp1; foreign ts/money verbatim; corrections append-only | FM-1, FM-2 | SCN-0002 |
| FR-011 | CT-11 / Story 3.3 | Seven room-roles per world; cross-world read refuses; `world=simulated` write refuses; evidence-bearing vs rebuildable; keep-raw-forever | FM-4, FM-5, FM-7 | — |
| FR-012 | CT-12 / Story 3.4 | Fingerprinted non-overlapping split manifest; required purge/embargo widths; knowledge-time partition; 12-month seal refuses at every read boundary; frozen seal TradingDate; one journaled final look | FM-3 | SCN-0003 |
| FR-013 | CT-13 / Stories 3.5–3.6 | N append-only per-writer streams; gapless per (writer,boot-epoch); seven event types; decision.outcome closed field; correlation_id/display_time out of fp1; causality via typed edges; unpersistable → storage-failure blocks stream; entity journals as read-time projections | FM-6, FM-11 | — |
| FR-016 | CT-11 / Story 3.1 | Dependency-free append-store over four named engines behind owned contracts; no DB server; fp1-keyed; idempotent vs true-collision; storage exceptions translated to refusals | FM-6, FM-7 | — |

**P0 assertions in scope (from handoff, embedded in task):**
- **P0-6** — Sealed holdout excluded at **every** read boundary, not just the intended one. `FR-012 / CT-12 / L19 / SCN-0003`.
- **P0-7** — Cross-world reads refuse **and** `world=simulated` refuses. `FR-011 / CT-11 / L18`.

**Risk gates in scope:**
- **R-007** — Adversarial / malformed input **refuses (typed CT-04) rather than returning Ok**, and store faults never propagate an exception across the boundary.
- **R-012** — Seal / split / world refusals **hold at every enumerated read path**, not only the canonical one.

(`L18`/`L19` are architecture-law ids from the spine, not test levels; the test levels are L0–L6 per Section 5.)

---

## Section 3 — Risk Assessment & Gates

Risk is scored on *irreversibility × likelihood-of-silent-pass*. The three highest-risk failure shapes each get a **property/invariant test that enumerates boundaries** (not a single happy path), because a point test would pass while a sibling read path leaks.

| Risk | Failure it guards | Gate | Where proven |
|---|---|---|---|
| **R-012** | A sealed row returned through a *non-canonical* path (processed room, restored backup) while the research-door path correctly refuses | Every enumerated read path (raw archive, processed, research door, registry room, restored backup) returns `policy rejection` on a sealed-period read; never a silent empty result | L2 property (path enumeration) + L4 restored-backup + L5 SCN-0003 → tests 3.4-P1, 3.4-P2, 3.4-I1, ACC-2 |
| **R-012** | A cross-world read allowed on one room-role while blocked on another; a `world=simulated` write slips into governed evidence | Cross-world read refuses on every room-role read path; simulated write refuses | L1 + L2 property → 3.3-U5, 3.3-P2, 3.3-U2 |
| **R-007** | A malformed/adversarial observation admitted (returns Ok / silently dropped) instead of a typed refusal; a store-library exception raised across the package seam | Fuzzed malformed observation always → `invalid input`; every store-fault (disk-full/locked/truncated/corrupt) → `storage failure` **returned**, never raised | L2 property (fuzz + fault matrix) + L1 → 3.2-P3, 3.1-P2, 3.2-U5, 3.1-U6 |
| **Evidence integrity** | A correction or re-write overwrites raw evidence; a true fp1 collision overwrites bytes | No write path mutates an earlier raw record; true collision refused+alarmed | L2 property + L1 → 3.2-P2, 3.1-P1, 3.1-U2/U3 |

**Prohibited-by-plan:** no planned test may (a) convert a GAP-open gate (look-ahead) into a passing fixture; (b) use synthetic data to assert trading edge (DEC-0054); (c) assert a defined-unwired risk runtime (CT-25) beyond contract-shape conformance.

---

## Section 4 — Independent Test List (authored from requirements, pre-source)

Notation: `T{story}-U#` unit (L1), `-P#` property/invariant (L2), `-C#` contract (L3), `-I#` integration (L4); `G#` static gate (L0); `ACC#` acceptance scenario (L5). "Assertion" states the observable pass condition. Every public boundary **returns** value-or-refusal; a refusal assertion checks CT-04 `category` + context, never a parsed exception string.

### Static / documentation gates (L0)
- **G1** — Import-graph gate: `qmf.data` imports only `qmf.core` + its own `qmf.data.store` seam; no other `qmf.*` package imported (default-deny, DEC-0120).
- **G2** — No-server gate: no database-server / graph-DB client dependency; the only physical engines are Parquet/DuckDB/SQLite/JSONL, each behind a CT-11-owned contract.

### Story 3.1 — Store seam (FR-016 / CT-11)
- **3.1-U1** (L1) — A persist through the CT-11 append-store routes an artifact to exactly one ratified engine per class (columnar→Parquet, view→DuckDB, metadata→SQLite, append→JSONL); boundary signatures are stdlib-typed. *(AC1)*
- **3.1-U2** (L1) — Byte-identical re-write under an existing fp1 is accepted silently (sandbox-merge normal case). *(AC2, FM-7)*
- **3.1-U3** (L1) — Same fp1 with differing bytes → refused **and** alarm raised; original bytes unchanged; never overwritten. *(AC2, FM-7)*
- **3.1-U4** (L1) — JSONL append writes exactly one fp1-canonical object per line, LF-terminated, under a monotonic ordinal. *(AC3)*
- **3.1-U5** (L1) — A second `WriterId` attempting an already-owned stream does not proceed (one-writer-per-stream). *(AC3, DEC-0113)*
- **3.1-U6** (L1) — Each fault (engine-unavailable, disk-full, locked, truncated, corrupt) is translated to a `storage failure` refusal **returned** at the boundary; no persistence-success reported. *(AC4, FM-6)*
- **3.1-P1** (L2) — Property: for arbitrary artifacts, a re-write is idempotent **iff** bytes are identical; a mutated-byte re-write never mutates the stored record. *(AC2)*
- **3.1-P2** (L2) — Property (**R-007**): across the full store-fault matrix, no store-library exception type escapes the CT-11 boundary; every fault surfaces as a returned `storage failure`. *(AC4, FM-6)*
- **3.1-C1** (L3) — CT-11 contract: evidence round-trip (encode/decode semantic equality); `room_role`/`world`/`is_evidence_bearing`/`retained_forever` enum & nullability boundary; format-version stamp present. *(AC1)*
- **3.1-C2** (L3) — CT-11 invalid/refusal: non-evidence-bearing artifact cannot be marked evidence; missing required key rejected.
- **3.1-I1** (L4) — Integration over the real JSONL engine: size-rotation under monotonic ordinal, locally rebuilt index recovers the full append stream. *(AC3)*
- **3.1-I2** (L4) — Integration: registry-room persistence via the `qmf-registry → qmf-data` CT-11 seam — per-kind fp1-keyed records + pinned JSONL lineage written append-only, never rewritten in place. *(AC5)*

### Story 3.2 — Bitemporal source observations (FR-010 / CT-10)
- **3.2-U1** (L1) — `source` is opaque and never parsed, and is orthogonal to `VenueId` (a source is not a venue). *(AC1)*
- **3.2-U2** (L1) — Foreign timestamp stored verbatim with declared zone/offset/resolution, alongside `receive_wall_time` (int64 UTC ns); no reformat. *(AC2)*
- **3.2-U3** (L1) — Foreign money stored verbatim as scaled integers at the source's declared scale; conversion to Money is a derived value with lineage, never a silent rescale. *(AC2)*
- **3.2-U4** (L1) — A correction keyed on `(source, source-native id, revision)` is admitted as a distinct artifact with its own fp1 carrying `correction_of` = original fp1; the original record's bytes are unchanged. *(AC3, FM-2)*
- **3.2-U5** (L1) — Parametrized: an observation missing any of {event-time, known-at, source, revision, writer, fp1} → `invalid input` refusal and does **not** enter governed CT-10 evidence. *(AC4, FM-1)*
- **3.2-P1** (L2) — Property: a coarser source resolution is never presented finer than received. *(AC2)*
- **3.2-P2** (L2) — Property (**evidence integrity**): across arbitrary correction sequences, no earlier raw observation is ever overwritten or mutated — corrections only append. *(AC3, FM-2)*
- **3.2-P3** (L2) — Property (**R-007**): fuzzed/adversarial malformed observations always yield a typed CT-04 refusal, never an admitted record and never an Ok. *(AC4, FM-1)*
- **3.2-C1** (L3) — CT-10 round-trip: full field roster (event_time, known_at, source, source_native_id, revision, foreign_timestamp block, foreign_money block, writer, boot_epoch_id, sequence, world, fingerprint) encode/decode semantic equality; identity = fp1 only, `(instant,writer,sequence)` an ordering key never identity. *(AC1)*
- **3.2-C2** (L3) — CT-10 boundary: `world` enum, nullability (null prohibited in identity — absent = omitted key), foreign-money present only on money/price-bearing observations.

### Story 3.3 — Seven room-roles per world (FR-011 / CT-11)
- **3.3-U1** (L1) — The seven room-roles (ingest door, immutable raw archive, processed, journal, split-governed research door, backup, registry room) are each instantiated independently for `world=live` and `world=replay`. *(AC1)*
- **3.3-U2** (L1) — A write into `world=simulated` governed evidence → `policy rejection` refusal (**P0-7**). *(AC1, FM-5)*
- **3.3-U3** (L1) — `is_evidence_bearing` is true only for the raw archive and journal; processed/DuckDB view is marked rebuildable with a pinned engine major and pinned rebuild calendar identity + tzdata version. *(AC2)*
- **3.3-U4** (L1) — Deletion is refused for raw evidence and for any rebuildable artifact a result label cites; licensed only for an uncited rebuildable artifact. *(AC3)*
- **3.3-U5** (L1) — A read requesting a world other than the caller's → `policy rejection` refusal (**P0-6 core**). *(AC4, FM-4)*
- **3.3-U6** (L1) — A time-series artifact resolves within its `(source, instrument, time-window)` partition inside its world's room; a rebuildable view is never treated as evidence-bearing. *(AC5)*
- **3.3-P1** (L2) — Property (**evidence integrity**): no reachable deletion path removes a raw original or a cited artifact. *(AC3)*
- **3.3-P2** (L2) — Property (**R-012 / P0-6**): a cross-world read refuses with `policy rejection` at **every** enumerated read path (raw archive, processed, research door, registry room, journal). *(AC4, FM-4)*

### Story 3.4 — Splits & the 12-month seal (FR-012 / CT-12)
- **3.4-U1** (L1) — Split boundaries and the seal boundary are stored TradingDates or Instants; a civil-date boundary → `invalid input`. *(AC1)*
- **3.4-U2** (L1) — Parametrized: a manifest omitting `purge_width` or `embargo_width` → `invalid input`. *(AC2)*
- **3.4-U3** (L1) — Changing `purge_width` or `embargo_width` changes the manifest fp1 (widths enter the split fingerprint); `split_id` is fp1-derived, never minted. *(AC1, AC2)*
- **3.4-U4** (L1) — A record whose observed-at precedes a boundary while its confirmed-at follows it is refused unless the declared embargo covers the gap (knowledge-time partition). *(AC3)*
- **3.4-U5** (L1) — The default research release excludes sealed identities, and any sealed-period read → `policy rejection` (never a silent empty result). *(AC4, FM-3) — **P0-6**.*
- **3.4-U6** (L1) — A row carrying a calendar identity different from the manifest's pinned one → `policy rejection`, never silently rescaled. *(AC5)*
- **3.4-U7** (L1) — The single authorized final look is journaled as a named `control action` subtype in CT-13; a second look / silent recycle is refused. *(AC6)*
- **3.4-P1** (L2) — Property (**R-012 / P0-6**): a sealed-period read refuses with `policy rejection` at **every** read boundary — raw archive, processed, research door, and restored backup — for arbitrary manifests/dates. *(AC4)*
- **3.4-P2** (L2) — Property: the seal boundary is frozen — re-derivation under a newer tzdata/calendar version mints a **new** manifest + lineage edge and never rewrites the frozen TradingDate. *(AC5)*
- **3.4-P3** (L2) — Property: a split reused with a producer whose warm-up+confirmation horizon exceeds the manifest's declared widths refuses rather than leaks. *(AC2)*
- **3.4-C1** (L3) — CT-12 round-trip: fingerprinted, time-ordered, non-overlapping segments; default {train, validation, sealed-test}; one pinned calendar identity+version in-band. *(AC1)*
- **3.4-I1** (L4) — Integration: a read into the sealed period through a **restored backup** → `policy rejection` (seal survives restore). *(AC4) — **R-012**.*

### Story 3.5 — Durable journals (FR-013 / CT-13)
- **3.5-U1** (L1) — An event whose `event_type` is outside the seven ratified types is refused; the enum is addable but never redefined. *(AC1)*
- **3.5-U2** (L1) — A detected gap in a stream's per-(writer,boot-epoch) sequence surfaces loss. *(AC2)*
- **3.5-U3** (L1) — A second writer to a stream already owned by a `WriterId` does not proceed. *(AC2, DEC-0113)*
- **3.5-U4** (L1) — A `decision` event without the closed `outcome` field {authorized|refused-by-door|suppressed} is invalid; a projection selects on the declared `outcome` field, never on key presence. *(AC3)*
- **3.5-U5** (L1) — `correlation_id` and `display_time` are excluded from fp1 identity; causal linkage across streams is carried only by typed edge records, never by timestamps or the `(instant,writer,sequence)` key. *(AC4)*
- **3.5-U6** (L1) — An unpersistable journal event → `storage failure` refusal that blocks the command stream in the WriterId-holding component; no silent loss. *(AC5, FM-6)*
- **3.5-P1** (L2) — Property: for arbitrary append sequences, each stream's sequence is strictly increasing and gapless per `(writer, boot-epoch)`. *(AC2)*
- **3.5-P2** (L2) — Property: two events differing only in `correlation_id`/`display_time` share the same fp1 identity. *(AC4)*
- **3.5-C1** (L3) — CT-13 round-trip: N-stream journal, one stream per producing component under its `WriterId`; the seven event types; wired QMF producers = data-quality + control-action. *(AC1)*
- **3.5-I1** (L4) — Integration: a partial multi-room write → `storage failure` refusal and is journaled on recovery; a restart replays the stream to a gapless reconstruction. *(AC5)*

### Story 3.6 — Entity-journal projections (FR-013 / CT-13, CT-25)
- **3.6-U1** (L1) — An entity journal (Book / BMS / per-bot) is extracted on demand as a read-time projection selected by entity identity from the one recorded set of writer-scoped streams; no entity mints a `WriterId`. *(AC1)*
- **3.6-U2** (L1) — A Book projection joins venue-authored order/fill events through the command record's content fingerprint (CT-25 join); Book identity is never threaded into the neutral venue payload. *(AC2)*
- **3.6-U3** (L1) — A projection that would aggregate rows across account roles without an explicitly declared cross-role read → `policy rejection`; only the two declared exceptions may span roles, each carrying `role` on every row. *(AC3, FM-11)*
- **3.6-U4** (L1) — Each legacy stream name {veto_ledger, trade_journal, book_journal, ksa_audit_log, correlation_ledger} resolves via the one versioned CT-25 mapping table (no second event catalog); `veto_ledger` selects on `decision.outcome = refused-by-door`, never on key presence. *(AC4)*
- **3.6-P1** (L2) — Property (**FM-11**): no write ever crosses role namespaces (writes stay role-scoped without exception). *(AC3)*
- **3.6-C1** (L3) — CT-25 shape conformance (defined-unwired): the command-fingerprint join and legacy-stream mapping table round-trip at the contract level only; **no runtime/integration assertion** (see Section 8).

### Acceptance scenarios (L5)
- **ACC-1** — **SCN-0002**: original observation + a later correction to the same provider-native occurrence → two distinct fp1 artifacts joined by an append-only typed lineage edge; original preserved; CT-11 preserves the complete pair or makes no completion claim.
- **ACC-2** — **SCN-0003**: build a CT-12 release; a default research read excludes sealed identities and any read crossing raw/processed/research-door/restored-backup into the sealed period → `policy rejection`; the one authorized final look is journaled as a `control action` subtype; underlying evidence stays retained.

---

## Section 5 — Test-Level Assignment & Rationale (L0–L6)

**Level architecture (reconstructed):** L0 static/documentation gates · L1 unit (tier 1) · L2 property/invariant (tier 1) · L3 contract conformance (tier 2, isolated per-package env) · L4 integration (tier 2) · L5 QMF acceptance scenario (tier 2) · L6 release/NFR (tier 3). This is a **T1 plan**: L0–L2 are the primary deliverable and run under `poe check`; L3–L5 are specified here for completeness and coverage-of-behaviour but bind at tier 2; L6 is out of scope for T1.

**One behaviour, one level — lower level wins (applied decisions):**
- Refusal *shape* checks (missing-field, cross-world, simulated-write, calendar-mismatch) live at **L1**, not re-asserted at L4 — a pure policy decision needs no store.
- "Refuses at **every** read path" (R-012, P0-6) is a *quantifier over paths*, so it lives at **L2 property** (enumerate the paths) — a single L1 case cannot prove universality. The restored-backup path additionally gets one **L4** case (3.4-I1) because that path physically crosses the backup boundary and cannot be exercised in a pure unit.
- Append-only / no-overwrite (evidence integrity) is a *universal invariant* → **L2** (3.2-P2, 3.3-P1), with representative L1 witnesses (3.2-U4, 3.1-U3).
- CT round-trip / enum / nullability → **L3** contract only (owned by qmf-data, run by producer+consumers at tier 2). Not duplicated as L1.
- Cross-component handoff (registry-room persistence, restore, rotation, partial-write recovery) → **L4** only.
- Golden end-to-end chains (SCN-0002/0003) → **L5** only; their component-level refusals are already covered lower, so L5 asserts *lineage + chain integrity*, not the individual refusals.

**Planned counts by level:**

| Level | Scope | Count |
|---|---|---|
| L0 | static/doc gates | 2 |
| **L1** | unit | **36** |
| **L2** | property/invariant | **13** |
| **L3** | contract conformance | **14** |
| **L4** | integration | **5** |
| L5 | acceptance scenario | 2 |
| L6 | release/NFR | 0 (out of T1 scope) |
| **Total** | | **72** |

(L1 per story: 3.1=6, 3.2=5, 3.3=6, 3.4=7, 3.5=6, 3.6=4, +G-adjacent 3.1 routing already counted = 36. L3 per contract: CT-10=2, CT-11=2, CT-12=1, CT-13=1, CT-25=1, plus CT-04 refusal-shape reuse + CT-10/11/12/13 boundary/invalid split-outs = 14.)

---

## Section 6 — Coverage & Weak-Spot Focus

Coverage floor is **80% per package** (100% branch is required only on the CT-01/CT-02 primitive modules in qmf-core — not applicable to this package). Two qmf-data modules sit below floor and are the branch-hunting focus. **These figures come from `coverage.json` (a data artifact); no source logic was read to author Section 4.**

| File | Line | Branch | Signal |
|---|---|---|---|
| `packages/qmf-data/src/qmf/data/cycle.py` | 63.3% (114/159) | 44.3% (31/70) | 39 missing + **19 partial** branches; 45 missing lines (first at 193, 208, 218, 226, 234, 239, 244, 255…) |
| `packages/qmf-data/src/qmf/data/verify.py` | 69.2% (214/283) | ~55% (72/130) | 58 missing + **40 partial** branches over 130 branches; **complexity ≈ 27**; 69 missing lines (first at 219, 273, 277, 279, 292, 307…) |

**Interpretation against requirements (filename → requirement area, no source read):** `cycle.py` most plausibly implements a lifecycle/rotation/replay cycle (JSONL rotation + index rebuild, or backup/restore cycle — 3.1-I1, 3.5-I1); `verify.py` most plausibly implements a verify primitive (CT-14/CT-26 restore-verify and/or fp1 / manifest verification — 3.1-U6, 3.4-*, ACC-2). The high partial-branch count on both is the classic signature of **error/refusal branches never exercised** — exactly the R-007/R-012 refusal paths this epic must guarantee.

**Weak-spot probes (planned; each is a FINDING if it fails, never a source edit):**
- **WS-1** — Drive every store-fault branch through `verify.py`/`cycle.py` (disk-full, locked, truncated, corrupt, partial-write) so the `storage failure` translation branches (3.1-P2, 3.5-I1) are covered rather than partial. Target: close the 40 partial branches in `verify.py`.
- **WS-2** — Exercise both arms of every seal / cross-world / calendar-mismatch decision the verifier makes (the "refuse" arm is the one currently partial) — ties to 3.4-P1, 3.3-P2. Target: the 19 partial branches in `cycle.py`.
- **WS-3** — Cover the idempotent-vs-true-collision split and the rotation-ordinal boundary (3.1-U2/U3, 3.1-I1) — likely among the missing `cycle.py` lines.
- **Coverage is not behaviour evidence:** a branch counted covered still requires its assertion to check the *returned refusal category*, per DEC-0109. Percentage never substitutes for a named-behaviour assertion.

---

## Section 7 — Fixtures, Data & Environment

- **Determinism:** injected CT-02 clock (int64 UTC ns) at the composition root; **no fixture below the root reads the system clock**; a monotonic reading is never an Instant. Property/randomized fixtures declare a seed; equal semantic inputs replay to equal fp1 (single qmf-core implementation, floats refused in identity).
- **Worlds:** fixtures parametrize `world ∈ {live, replay}` for positive paths and assert `simulated` refuses. World isolation is delivered by **storage separation**, so fixtures instantiate room-roles in separate physical roots per world.
- **Seal manifest:** a CT-12 fingerprinted split with `train/validation/sealed-test`, a **frozen** seal TradingDate from `registry:historical_holdout_months` (~12mo), required `purge_width`/`embargo_width`; membership computed from the manifest, not hardcoded.
- **Refusal harness:** boundaries **return** value-or-refusal; the harness asserts CT-04 `category` + machine-readable context + retryability, never a parsed exception message. A store-fault matrix (unavailable/disk-full/locked/truncated/corrupt) feeds R-007 property tests.
- **Source classes:** every fixture tagged `source-evidence | controlled-replay | synthetic`; **synthetic may prove infrastructure/failure handling only and may never satisfy a trading-edge assertion** (DEC-0054). External outcomes enter as controlled replays at CT-15, never live network in tier-1 units.
- **Engines (L4):** the ratified store stack (Parquet/DuckDB/SQLite/JSONL behind QMF-owned contracts); no database server; per-package isolated env at tier 2 so an undeclared import fails rather than resolving through the shared venv.
- **Run:** `uv run` from the worktree root (`.venv` dev group synced); property fixtures via `uv run --with hypothesis …` if hypothesis is absent.

---

## Section 8 — Execution, Exit Criteria & Untestable / Deferred

**Execution order:** L0 gates → L1 units → L2 properties (R-007/R-012 quantifier proofs) → L3 contract → L4 integration → L5 scenarios. Findings are recorded, not fixed; a red test that asserts a requirement the code violates is a **defect finding**, and the source is never edited to make it pass.

**Exit criteria (T1 sign-off for this epic):**
1. L0–L2 all specified tests authored and executed; every P0-6 / P0-7 / R-007 / R-012 assertion has at least one passing property test.
2. `cycle.py` and `verify.py` raised to ≥80% line and their refusal branches (partials) covered, or each residual partial recorded as a finding with the missing branch named.
3. No planned test converts a GAP-open gate or a defined-unwired risk runtime into a pass.
4. Traceability complete: every test cites FR/CT/AC/FM/SCN/DEC ids.

**Requirements judged untestable now (with reason — these are blocked specs, not plan gaps):**
- **U-A — CT-08 look-ahead/causality registration gate & attempt counter (GAP-0016 / GAP-0017, DEC-0121).** The gate's own pass/refusal semantics are deferred to the backtesting sitting; its contract schema is GAP-open. Bitemporal *ingredients* (event-time vs known-at, late correction) are testable (3.2-*, ACC-1); the **gate result** is not. Naming the GAP preserves the uncertainty but does not satisfy it.
- **U-B — Story 3.6 risk-authored entity-journal runtime (CT-25 command-fingerprint join over real risk events).** CT-25 is ratified surface but **defined-unwired**: no qmf-risk runtime exists and risk-authored events reach qmf-data only through the composition root at factory time. Contract-shape conformance (3.6-C1) and the venue-side join + mapping table (3.6-U2/U4) are testable; a runtime/integration proof over actual risk-authored streams is **blocked** until the node wires risk.
- **U-C — Numeric backup RPO/RTO/retention-depth & restore-verification cadence.** Named at the node/ops sitting; no ratified values. The *behaviours* (seal survives restore — 3.4-I1; backup covers every room-role) are testable; the **numeric objectives** have no spine value to assert.
- **U-D — Per-kind BarSpec aggregation arithmetic (renko/tick-count/volume) and the tick-to-bar builder.** Deferred-table rows (DEC-0126/0130). FM-10 (governed-BarSpec promotion refused before the venue daily boundary is minted) is testable as a refusal; the **aggregation arithmetic** has no ratified spec. Peripheral to Epic 3's five FRs.
- **U-E — Journal retention/trimming numeric thresholds.** Set only after measured volume (DEC-0118); no value to assert. The append-only + gapless invariants (3.5-P1) are fully testable; the trim thresholds are not.

**Plan caveat carried forward:** `test-design-qa.md` and `QMX-handoff.md` were absent from the worktree; if they are later restored, reconcile this plan's section shape, level names, and the P0/R-gate numbering against them (they are authoritative over the reconstruction).
