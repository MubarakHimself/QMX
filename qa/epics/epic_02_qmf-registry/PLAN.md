# Verification PLAN — Epic 2: qmf-registry (identity, lineage & promotion)

- **Tier:** T1
- **Epic:** Epic 2 — `qmf-registry` (Wave 2, H). FRs covered: FR-006, FR-007, FR-008, FR-009 (+ FR-048 Bot-mint gate, kind owned here).
- **Package under test:** `packages/qmf-registry` (`qmf.registry`), READ-ONLY evidence.
- **Epic thesis (from epics.md):** *Every governed artifact registers once, carries lineage forever, and nothing reaches live money without a human-signed promotion.* This is **the only path to live money** — the highest-consequence surface in the roster.

### Provenance & reconstruction note (load-bearing — read before trusting section numbering)

The two authority files named in the lane brief —
`_bmad-output/test-artifacts/test-design-qa.md` (Per-Epic Test Plan Template + L0–L6 architecture) and
`_bmad-output/test-artifacts/test-design/QMX-handoff.md` (15 P0/P1 assertions + risk-gate rows) —
**do not exist in this worktree**; the entire `_bmad-output/test-artifacts/` tree is absent (verified by directory listing and content grep). This plan therefore **reconstructs** the 8-section template and the L0–L6 test-level architecture from the ratified authority that *is* present: `docs/lenses/testing/test-strategy.md` (`LENS-TEST-STRATEGY`, status: ratified) and its Test-levels, Contract, Failure-mode, and Law/authority matrices, plus the task brief's own statement of what section 4 must be and which P0 assertions bind this epic. Every level, matrix, and law cited below traces to a ratified doc, not to the missing files. The absence is itself recorded as **Finding-candidate GAP-QA-01** in section 8.

Section 4 (the independent test list) was authored **in full from requirements only** — the Epic 2 slice of `epics.md`, `docs/contracts/CT-04..09, CT-33`, `docs/components/qmf-registry.md`, `docs/scenarios/SCN-0007`, and `docs/constitution.md` (L17, L30) — **before any `src/qmf/registry/*.py` file was opened**. Sections 5–7's current-state observations were written afterward, from source, and never fed back into section 4. That ordering is the template's core discipline and is preserved here.

---

## 1. Epic scope and requirements binding

| Requirement | Statement (abridged) | Contract / law | Verifies |
|---|---|---|---|
| **FR-006** | Per-kind registration records keyed on `fp1`, dedup by construction; stable id derived never minted; occurrence facts excluded from identity. | CT-06 | records.py |
| **FR-007** | Provenance is append-only typed lineage edges, never rewritten; 14-value edge enum; pinned JSONL; `supersedes` linear. | CT-07 | lineage.py |
| **FR-008** | Registry persists **through qmf-data only** — no DB server; `qmf-registry → qmf-data` is the single ratified inter-library edge. | CT-09, L30 | persistence.py |
| **FR-009** | The **only path to live money** is a human-signed promotion occurrence attesting the record's `fp1`, with a mandatory plain-words summary as an **identity field**. | ADR-0015, SCN-0007, L17 | promotion.py |
| **FR-048 (gate)** | The Bot kind (CT-33) registers **only after both QL-8 conformance layers pass**, else `policy rejection`; a registered Bot `fp1` is exactly what governed evidence and Book seats may cite. | CT-33, AR-64, DEC-0178 | records.py / KindRegistry (defined-unwired) |

**Constitution laws in scope:** **L17** (only a human may promote into the live zone), **L29** (provisional/GAP grants no live-money authority), **L30** (default-deny inter-library dependencies; the one ratified edge is qmf-registry→qmf-data; nothing imports qmf-registry, qmf-venue, or qmf-risk).

**Architecture rules in scope (epics.md AR list):** AR-14 (single qmf-core fp1 implementation; `fp1:sha256:<hex>` over sorted-key NFC UTF-8 JSON, integer-only identity), AR-25 (every serialized contract stamps an integer format version; meanings never mutate), AR-31 (JSONL journals/edges: one fp1-canonical object per line, LF-terminated, append-with-fsync, rebuildable indexes), **AR-39** (only a human promotes; V1 signing is the operator's recorded approval attesting the record's `fp1`), **AR-64** (both conformance layers must pass before a Bot mints), AR-06/L30 (default-deny edges).

**Component authority boundary (`COMP-QMF-REGISTRY`) — the `May never` clauses that become negative assertions:** no universal all-fields card; no database server / graph DB; no id or key minted on a timestamp; no redefining core-owned time/identity/refusal meanings; no registry business rules in the data layer; not imported by any consuming library; no hardcoded "exactly one" in bot vocabulary; no look-ahead gate / attempt counter in V1 (deferred, never open); **no promotion into the live zone without a human decision.**

**Citation reconciliation (recorded, not silently resolved):** the brief cites **AR-52** for P0-4 (fingerprints). In `epics.md`, AR-52 is the QMB resolved-run-config artifact, *not* the fingerprint law — a numbering carried over from the missing handoff. The fingerprint law in the ratified corpus is **AR-14 + AR-25** with **CT-05/CT-06**; P0-4 is bound to those here. Logged as **Finding-candidate GAP-QA-02**.

---

## 2. Risk assessment, priorities, and risk-gate rows

Priority scale: **P0** (a defect here can move real money wrongly or corrupt the identity/lineage of governed evidence) → **P3** (cosmetic). Epic 2 is disproportionately P0 because it is the money gate.

| # | Risk (probability × impact) | Pri | Where it lives | Planned coverage |
|---|---|---|---|---|
| **R1** | A path reaches the live zone without a recorded human promotion attesting the record `fp1` (agent self-promotion, superseded-template attestation, missing/blank summary). | **P0** | promotion.py | E2-L1-11..15, E2-L2-05, **E2-L5-01 (SCN-0007)** |
| **R2** | Two distinct semantic inputs collide to one `fp1`, **or** a true collision silently overwrites (dedup masks a genuine variant; a differing-bytes write clobbers). | **P0** | records.py, lineage.py, persistence.py | E2-L1-04..06, **E2-L2-01..02**, E2-L4-07 |
| **R3** | A tampered persisted record/edge **reads back as valid** (read-back integrity). *This is the epic's advisory-history site — `persistence.py`, cyclomatic complexity 26; source shows a bespoke edge integrity-witness and fp1-recompute-on-read added exactly to close a "canonical-preserving edit re-derives a valid fp1" vector.* | **P0** | persistence.py (`load_record`, `_verify_edge_witness`) | **E2-L4-02, E2-L4-03**, E2-L2-04 |
| **R4** | The Bot kind mints without both conformance layers passing (a bot citable by governed evidence / eligible for a live Book seat that never passed the gate). | **P0** | records.py / KindRegistry, CT-33 | E2-L1-17..20, E2-L3-09 |
| **R5** | A refusal is raised (not returned) across the package seam, or a store exception leaks across the qmf-data boundary instead of a `storage failure` refusal. | **P1** | all four modules, persistence.py | E2-L1-16, E2-L4-04, E2-L3-07 |
| **R6** | World bleed — a cross-world read succeeds, or a non-live world writes the live namespace. | **P1** | persistence.py | E2-L4-05 |
| **R7** | `supersedes` becomes non-linear (ambiguous "current" head), or an edge is admitted with a non-`fp1` endpoint / off-enum type. | **P1** | lineage.py | E2-L1-07..10, E2-L2-06 |
| **R8** | A default-deny import violation (registry imports beyond qmf-core + the one qmf-data edge; something imports qmf-registry; a DB-server dependency appears). | **P1** | package deps | E2-L0-01..02 |

**P0 assertions binding this epic (from the brief):**
- **P0-4** — *distinct semantic inputs produce distinct fingerprints, and no silent overwrite* (FR-005 / CT-05 / CT-06; law family "Typed, versioned identity", DEC-0029/0030/0103/0108). Bound to R2.
- **P0-5** — *NO path reaches live money without a recorded human promotion attesting the record `fp1`* (FR-009 / L17 / AR-39 / SCN-0007; law family "Human promotion", DEC-0041/0116). Bound to R1.

---

## 3. Test-level architecture and routing (L0–L6; one behaviour, one level, lower level wins)

Reconstructed from `LENS-TEST-STRATEGY` "Test levels" (6 ratified rows) mapped onto the brief's L0–L6 spine plus the tier-3 release smoke:

| L | Name (test-strategy row) | Tier | Scope for this epic |
|---|---|---|---|
| **L0** | Static & documentation gates | — | Default-deny import graph; no DB-server dependency; IDs resolve. |
| **L1** | Unit | Tier 1 | Pure values, validation, policy, returned refusals through the public API; injected clock; declared seed. **Most Epic 2 behaviour lands here.** |
| **L2** | Property / invariant | Tier 1 | Generated valid+invalid inputs prove CT invariants and that prohibited side-effects stay absent. |
| **L3** | Contract | Tier 2 | CT-06/07/09 owner-conformance (round-trip + boundary), run in isolated per-package env; CT-04/CT-05 as-consumed; CT-33 shape-only (defined-unwired). |
| **L4** | Integration | Tier 2 | Real store adapter, restart/read-back, migration, world isolation, storage-failure translation. |
| **L5** | QMF acceptance scenario | Tier 2 | SCN-0007 bounded chain (agent-cannot-promote). |
| **L6** | Release smoke | Tier 3 | Clean-install on both tier-1 OSes — not epic-specific; out of scope for this plan's counts. |

**Routing rule applied:** *one behaviour, one level, and the lowest level that can prove it wins.* Consequences for Epic 2:
- "distinct semantics ⇒ distinct `fp1`" and "canonicalization determinism" are **properties → L2** (not re-asserted at L3/L4).
- "true collision refused & alarmed" is a single **unit decision → L1** (the persistence variant, E2-L4-07, adds only the *store-boundary* proof, not the identity logic).
- "record survives a process restart / tamper is caught on read-back" is inherently **integration → L4** (cannot be proven in-memory).
- The full agent-cannot-promote narrative is one **acceptance chain → L5**; its atomic refusals live at **L1** and are not duplicated into L5.

---

## 4. Independent test list (authored from requirements, before any src read)

Each row: ID · level · priority · assertion · requirement trace. Assertions are **what the requirements demand**, not what the code happens to do. IDs are stable planning handles.

### L0 — Static & documentation gates (planned: 2)
- **E2-L0-01** · P1 · `qmf.registry` imports only `qmf.core` and (via the one ratified edge) `qmf.data`; no other roster package is imported, and no library imports `qmf.registry`. — L30/AR-06, FR-008
- **E2-L0-02** · P1 · The package declares no database-server / graph-DB dependency (records are per-kind versioned records; lineage is pinned JSONL). — CT-06/CT-09 `May never`

### L1 — Unit (planned: 20)
- **E2-L1-01** · P1 · Registering a kind or field-set CT-06 does not define **returns a typed refusal** (FM-1), never raises. — FR-006, CT-06, CT-04
- **E2-L1-02** · P0 · A well-formed known-kind registration succeeds; the record's `stable_id` **equals `fp1` over its canonical content** (derived, never minted). — FR-006, CT-06
- **E2-L1-03** · P0 · Two records identical in semantic content but differing only in `created_at` / writer / sequence yield the **same `stable_id`** (occurrence facts excluded from identity ⇒ dedup by construction). — FR-006, CT-06, CT-05
- **E2-L1-04** · **P0** · Changing any one identity-bearing header/body field yields a **different `stable_id`** (distinct semantics ⇒ distinct `fp1`). — **P0-4**, CT-05, CT-06
- **E2-L1-05** · **P0** · A true `fp1` collision (same `stable_id` presented with differing canonical bytes) is **refused and alarmed, never overwritten** (FM-6). — **P0-4**, CT-06, CT-09
- **E2-L1-06** · P0 · A byte-identical idempotent re-write is **accepted silently** — no error, no duplicate (FM-6 complement). — FR-006, CT-06
- **E2-L1-07** · P1 · An edge whose `edge_type` is outside the ratified 14-value CT-07 enum is refused (FM-2). — FR-007, CT-07
- **E2-L1-08** · P1 · An edge referencing an endpoint by anything other than an `fp1:sha256:<hex>` string is refused (FM-2). — FR-007, CT-07
- **E2-L1-09** · P2 · A well-formed edge over the enum with `fp1` from/to serializes to exactly **one canonical JSONL line, LF-terminated**. — FR-007, CT-07, AR-31
- **E2-L1-10** · P1 · `supersedes` is **linear** — a second outgoing `supersedes` from one subject is rejected so "current" stays unambiguous; `branches-from` is allowed multi-head. — FR-007, CT-07
- **E2-L1-11** · **P0** · A live-promotion request with **no** human-signed promotion-occurrence card **does not promote**; status unchanged, no live capability granted (FM-4). — **P0-5**, FR-009, L17
- **E2-L1-12** · **P0** · A promotion card missing its mandatory `plain_words_summary` is rejected (summary is a required **identity field**). — **P0-5**, FR-009, CT-06
- **E2-L1-13** · **P0** · The signer must be **human-only**; an agent/non-human signer cannot author a valid promotion occurrence. — **P0-5**, FR-009, L17, AR-39
- **E2-L1-14** · P0 · The `plain_words_summary` is identity-bearing — a card with a different summary has a **different card `fp1`** (the signature attests the exact words read). — FR-009, CT-06, SCN-0007
- **E2-L1-15** · P0 · A card attesting an AD-32 admission carries the **Book/BMS-definition fingerprint as an identity field**; changing the attested `fp1` mints a **new** card (a signature can never attest a superseded template). — FR-009, SCN-0007, DEC-0158
- **E2-L1-16** · P1 · Every registry public operation returns **value-or-refusal**; each failure returns a CT-04 `TypedRefusal` (category ∈ the seven), never raises across the boundary. — CT-04, FM-1/2/8
- **E2-L1-17** · **P0** · A Bot-kind registration is refused **`policy rejection`** when *either* conformance-layer verdict is fail (verdicts injected). — FR-048, AR-64, DEC-0178
- **E2-L1-18** · P0 · A Bot-kind registration mints the record **only when both** verdicts pass; the minted Bot `fp1` is over **semantic content only** (AD-16 header excluded). — FR-048, CT-33, AR-64
- **E2-L1-19** · P1 · A Bot declaration with `strategy_family_id` cardinality ≠ exactly one is `invalid input` (never registers). — FR-048, CT-33, DEC-0176
- **E2-L1-20** · P1 · A footprint whose producer-binding set is not the transitive union of cited confluence-leg producers + bot-direct producers is a Layer-1 refusal. — FR-048, CT-33, DEC-0174

### L2 — Property / invariant (planned: 7)
- **E2-L2-01** · **P0** · ∀ distinct semantic contents a,b: `fp1(a) ≠ fp1(b)` — injective identity, no accidental collision under canonicalization. — **P0-4**, CT-05
- **E2-L2-02** · P0 · ∀ record r: `fp1` is invariant under object-key reordering, insignificant whitespace, and occurrence-field variation — equal semantics ⇒ equal `fp1`. — CT-05, AR-14
- **E2-L2-03** · P1 · ∀ identity content containing a float: identity construction **refuses** (floats refused in identity). — CT-05
- **E2-L2-04** · P0 · ∀ append sequences: the edge log is **append-only and order-preserving** — after N appends the store holds exactly those N lines in order, none rewritten. — CT-07, AR-31
- **E2-L2-05** · **P0** · ∀ promotion attempts generated without a valid human-signed card: the artifact **never** enters the live namespace (invariant face of P0-5). — **P0-5**, L17, FR-009
- **E2-L2-06** · P1 · ∀ edge streams: exactly one writer holds the WriterId; a second writer to the same stream is rejected (one-writer-per-stream). — CT-07, AR-17
- **E2-L2-07** · P1 · ∀ records: no `fp1` is computed except by qmf-core's single implementation (no registry-local hashing). — CT-05, AR-14

### L3 — Contract (Tier 2, owner-conformance, isolated env) (planned: 9)
- **E2-L3-01** · P1 · CT-06/round-trip — canonical encode/decode semantic equality for each defined kind (header + body). — CT-06
- **E2-L3-02** · P0 · CT-06/boundary — unknown kind; missing required header field; `fp1`-derived stable id; **human-only promotion occurrence attesting the record's `fp1`**; format-version stamping. — CT-06
- **E2-L3-03** · P1 · CT-07/round-trip — typed-edge encode/decode equality; all 14 enum types accepted; pinned-JSONL shape. — CT-07
- **E2-L3-04** · P1 · CT-07/boundary — non-`fp1` endpoint refusal; duplicate edge (idempotent re-append accepted); **rebuildable-index** (drop index → rebuild reproduces the edge view). — CT-07
- **E2-L3-05** · P0 · CT-09/round-trip — persist a record through the `qmf-registry→qmf-data` CT-11 seam and read it back **semantically equal**. — CT-09, FR-008
- **E2-L3-06** · P1 · CT-09/boundary — append/transaction; migration format-version boundary; storage-failure refusal translation; world-room selection. — CT-09
- **E2-L3-07** · P1 · CT-04 conformance on the registry surface — every returned refusal is one of the seven categories with `context` + `retryability`, returned not raised. — CT-04
- **E2-L3-08** · P1 · CT-05 as-consumed — the stable id derives from the **content** `fp1`; for adapter/wrapped artifacts the **content** fingerprint is cited, never the wrapping record's. — CT-05, DEC-0138
- **E2-L3-09** · **P0** · CT-33 shape-only (**defined-unwired**) — bot-definition semantic-content round-trip; header excluded from `fp1`; the both-layers gate as a contract boundary (`policy rejection` on either fail). *Must not turn a `pending` slot into a passing fixture.* — FR-048, CT-33

### L4 — Integration (real store, restart, tamper) (planned: 8)
- **E2-L4-01** · P0 · Persist a record through the real store seam, **restart the process, read it back** — semantic equality preserved. — CT-09, FR-008
- **E2-L4-02** · **P0** · **READ-BACK INTEGRITY** — a persisted record whose on-disk bytes are tampered must **not** read back valid: recomputed `fp1` ≠ stored `stable_id` ⇒ refusal/alarm, never a silently-valid record. *(advisory hotspot: persistence.py cx 26.)* — FR-008, CT-09, CT-06
- **E2-L4-03** · **P0** · A tampered / canonical-preserving-edited JSONL edge line does **not** read back as a valid edge; the integrity witness makes a swapped-to-another-valid-edge line **tamper-evident** rather than served as good lineage. — FR-007, CT-07, CT-09
- **E2-L4-04** · P1 · A store-library failure (disk-full / locked / truncated) is translated to a **`storage failure` typed refusal** at the qmf-data boundary and **never propagated** across the seam (FM-8); no partial registration is claimed successful. — FR-008, FM-8, CT-04
- **E2-L4-05** · P1 · **World isolation at storage** — a cross-world read is a `policy rejection`; a non-live world write never lands in the live namespace (FM-7); rooms per world. — FR-008, FM-7, CT-09
- **E2-L4-06** · P1 · Deleting the local edge index costs **only a rebuild** — a rebuild reproduces the identical edge view, no evidence lost. — FR-007, CT-07, CT-09
- **E2-L4-07** · P0 · Idempotent persistence — persisting the same `fp1` record twice yields **one** stored record (silent accept); a differing-bytes same-`fp1` write is **refused and alarmed at the store boundary**. — FR-006, CT-09, FM-6
- **E2-L4-08** · P1 · Migration — a record stamped at format version N reads after a bump via **preflight → backup → dry-run → migrate → verify**, no in-place mutation of the only copy; old evidence stays readable. — CT-09, AR-25

### L5 — QMF acceptance scenario (planned: 1)
- **E2-L5-01** · **P0** · **SCN-0007 end-to-end** — an agent reports checks passed and attempts to move an artifact from research to live: **the status does not change and no live capability is granted**; only a human-signed promotion occurrence attesting the card `fp1` (with plain-words summary + attested definition `fp1` as identity fields) can authorize the crossing; a summary/attested-`fp` typo fix mints a **new** card with a `supersedes` edge; passing any number of agent-run checks cannot substitute for human authorization. — **P0-5**, FR-009, SCN-0007, L17

**Planned totals: L0=2 · L1=20 · L2=7 · L3=9 · L4=8 · L5=1 → 47.**

---

## 5. Coverage & traceability matrix

| Requirement / FM | Assertions | Lowest level |
|---|---|---|
| FR-006 (registration, dedup) | L1-01,02,03,06 · L2-02 · L3-01,02 · L4-07 | L1 |
| FR-007 (lineage edges) | L1-07,08,09,10 · L2-04,06 · L3-03,04 · L4-03,06 | L1 |
| FR-008 (persist via qmf-data only) | L0-01,02 · L3-05,06 · L4-01,02,04,05,08 | L0 |
| FR-009 (human promotion) | L1-11,12,13,14,15 · L2-05 · L3-02 · **L5-01** | L1 |
| FR-048 (Bot both-layers mint) | L1-17,18,19,20 · L3-09 | L1 |
| P0-4 (distinct fp1 / no overwrite) | L1-04,05 · L2-01,02 · L4-07 | L1 |
| P0-5 (no live money w/o human promo) | L1-11,13 · L2-05 · L5-01 | L1 |
| Read-back integrity (advisory) | **L4-02,03** · L2-04 | L4 |
| CT-04 (typed refusal, returned) | L1-01,16 · L3-07 · L4-04 | L1 |
| CT-05 (fp1 identity discipline) | L1-04 · L2-01,02,03,07 · L3-08 | L2 |
| FM-1 kind/field undefined | L1-01 · L3-02 | L1 |
| FM-2 bad edge type/endpoint | L1-07,08 | L1 |
| FM-3 caller expects deferred gate | **untestable-positive** → section 8 (negative: registration enforces neither gate) | — |
| FM-4 promote w/o card | L1-11 · L5-01 | L1 |
| FM-5 summary corrected after signing | L1-14 · (L5-01 tail) | L1 |
| FM-6 true collision | L1-05,06 · L4-07 | L1 |
| FM-7 world crossing | L4-05 | L4 |
| FM-8 store failure | L4-04 · L3-06 | L4 |
| L30 default-deny | L0-01,02 | L0 |

Every FR and every failure mode FM-1..FM-8 has at least one planned assertion except **FM-3**, which is untestable-positive by ratified deferral (section 8). No coverage percentage substitutes for a behaviour assertion.

---

## 6. Fixtures, data, and environment

- **Runner:** `uv run` from the worktree root (`.venv` has the dev group synced). Property tests need hypothesis: `uv run --with hypothesis pytest ...` (confirmed **not** currently a test dep — L2 is a net-new addition).
- **Clock & determinism:** injected `Clock` at the composition root only — **never** the system clock (AR-16); a declared RNG seed for any hypothesis run so failures reproduce.
- **Public API surface to drive (from `qmf.registry.__init__`, for test authoring only):** `Registrar` / `RegistrationRecord` / `KindRegistry` / `WriteOutcome` (records); `EdgeLog` / `LineageEdge` / `EdgeType` (lineage); `authorize_live_promotion` / `PromotionCard` / `correct_summary` / `emit_promotion_event` (promotion); `RegistryPersistence` / `LoadedRecord` / `migrate_registry_format` / `persistence_fingerprint` (persistence). Tests assert through these public seams, never private helpers.
- **Store fixture (L4):** the real `qmf.data.store` engine (Parquet + DuckDB are provisioned in the env for `qmf.data.store` import); a per-world registry room over a temp dir; process-restart simulated by closing and re-`open`-ing `RegistryPersistence`.
- **Tamper fixture (L4-02/03):** persist a record/edge, then mutate the on-disk bytes out-of-band (byte flip; and a canonical-preserving re-serialization / line swap) and assert read-back refuses. This exercises `load_record`'s recomputed-`fp1`-equals-stored-`stable_id` assertion and `_verify_edge_witness`.
- **Bot-conformance fixture (L1-17/18, L3-09):** conformance verdicts are **injected** (pass/pass, pass/fail, fail/pass, fail/fail) — the plan does not build a real QL-8 sandbox runner (host territory, defined-unwired).
- **Refusal assertions:** assert the returned `TypedRefusal.category` and `context`, **never** a parsed exception message (DEC-0109). A failure mode proof that observes a raised exception across the seam is itself a **finding**.
- **Synthetic-data limit:** synthetic fixtures may exercise infrastructure and failure handling but may never be cited as proof of trading edge (DEC-0007/0054) — not a concern for this epic but honoured.

---

## 7. Execution plan and tooling

1. **L0** — import-graph / dependency assertions (Tier-1 static). `uv run poe types` + a targeted import test.
2. **L1 + L2** — Tier-1 unit + property. `uv run --with hypothesis pytest packages/qmf-registry/tests -q`; coverage measured against the 80% floor (no CT-01/CT-02 primitive here, so no 100%-branch module in this epic).
3. **L3** — Tier-2 contract, each package in an **isolated per-package environment** so an undeclared import fails rather than resolving through the shared venv (`poe check-integration` semantics).
4. **L4** — Tier-2 integration against the real store seam (restart, tamper, migration, world isolation, storage-failure).
5. **L5** — the SCN-0007 acceptance chain (Tier 2).
- **Order matters** only in that a red L1 identity/refusal assertion makes higher-level results uninterpretable; run low→high and record findings at the lowest failing level.
- **Discipline:** source is READ-ONLY evidence. A failing test is a **FINDING to record**, never a reason to edit source or weaken the test. Tests assert what the **requirements** demand.
- **Current-state baseline (from source, informational):** the package already ships **163 tests** across CT-06 (40), CT-07 (31), CT-09 (50), promotion (40), and a registry smoke (2), plus reference-usage `_examples` files — but **zero property/hypothesis tests**. So L1/L3 are largely re-verification of existing coverage, while **L2 (property/invariant), L4-02/03 (adversarial read-back/tamper), and L3-09/L1-17..20 (Bot both-layers gate) are the plan's net-new, highest-value additions** — they sit exactly on the advisory-history site and the money gate.

---

## 8. Untestable requirements, deferrals & exit criteria

**Untestable / blocked (recorded, not silently skipped):**

1. **CT-08 causality & attempt-gate evidence — untestable-positive.** `version: null`, `type_gap: GAP-0016`, all fields/enums/nullability `null`; GAP-0005/0016/0017 deferred to the backtesting sitting (DEC-0121). The *positive* gate (a look-ahead pass, an attempt budget/reset) **cannot be tested** — naming the GAP preserves the uncertainty but does not satisfy a gate (DEC-0004). Only the **negative FM-3** is assertable: registration records occurrence evidence but **enforces neither gate**, and `registry:registry_attempt_budget` remains null. A test that manufactures a passing causality/attempt fixture would be a **finding**, not coverage.

2. **FR-048 / CT-33 runtime — partially untestable in this epic (`wiring_status: defined-unwired`).** No Bot-kind code is authorized to exist yet; QML authors the declaration and the composition root mints under AD-25 root-mints. The both-layers gate is testable at **contract-shape level with injected verdicts** (L1-17/18, L3-09) but **not** as a live wired integration (no L4 Bot proof). If `records.py` / `KindRegistry` contains **no** `bot-definition` mint path at all, E2-L1-17..20 become a **coverage-gap finding** (the ratified surface is unrealized), not a pass.

3. **Promotion gate workflow / UI / timing** is explicitly **platform territory outside QMF** (DEC-0116). Only the registry card, its identity fields, and the attestation/refusal law are in scope here; the end-to-end operator UI is out of scope and not a QMF test target.

4. **Migration verify across an actual incompatible version bump** (E2-L4-08) can be exercised only with a synthesized "format N+1"; with a single ratified format version (v1) live, the test proves the **staged mechanism** (preflight→backup→dry-run→migrate→verify, no in-place mutation), not a real N→N+1 semantic migration.

**Process gaps logged as finding-candidates:**
- **GAP-QA-01** — the named authority files `test-design-qa.md` and `QMX-handoff.md` (and the whole `_bmad-output/test-artifacts/` tree) are **absent**; this plan reconstructs the template and L0–L6 architecture from `LENS-TEST-STRATEGY`. The 15 P0/P1 assertion set and the epic's risk-gate rows could be bound only from the brief, not cross-checked against the handoff.
- **GAP-QA-02** — the brief's **AR-52** citation for P0-4 does not resolve against `epics.md` (AR-52 there is the QMB run-config); P0-4 is bound to AR-14/AR-25 + CT-05/CT-06 instead.

**Exit criteria for the Epic 2 verification run:**
- Every L0–L5 assertion above is executed and each result recorded at its lowest level; each P0 assertion (E2-L1-04/05, E2-L1-11/13, E2-L2-01/05, E2-L4-02/03, E2-L1-17/18, E2-L5-01) is GREEN or carries a written FINDING.
- Coverage ≥ 80% floor for `qmf.registry` (informational; a percentage never substitutes for a behaviour assertion).
- FM-1..FM-8 each resolved to GREEN or FINDING, except FM-3 which exits as **documented-deferral** (must stay unenforced).
- The two P0 gates — *no live money without a recorded human promotion attesting the record `fp1`* and *distinct semantics ⇒ distinct `fp1`, no silent overwrite* — plus *tampered records do not read back valid* are the ship-blocking triad; any FINDING on these blocks the epic regardless of other results.
