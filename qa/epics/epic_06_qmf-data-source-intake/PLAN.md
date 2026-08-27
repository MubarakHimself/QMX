# Epic 6 — qmf-data source intake — Independent Verification PLAN

> Per-epic template compliance: the eight sections below run in the template's
> fixed, load-bearing order. **Section 4 (the independent test list) was authored
> from the requirements corpus BEFORE any `packages/qmf-data/src/**` intake
> implementation body was opened.** Only the public module/file *names* and the
> directory layout were listed prior to Section 4, and `coverage.json` (a data
> artifact) was read for the baseline; no `src/` implementation was read. Oracles
> are `epics.md` §Epic 6, the CT-* YAML, SCN-0002 / SCN-0008, the component specs
> (COMP-QMF-DATA-INGEST, COMP-DUKASCOPY, COMP-CALENDAR-FEED), and the
> constitution — never the code. Source is read-only evidence: a failing planned
> test is a FINDING, never a licence to edit source or weaken a test.

> **Template-provenance caveat (load-bearing for the reader).** The two named
> authorities `_bmad-output/test-artifacts/test-design-qa.md` and
> `.../test-design/QMX-handoff.md` are **absent from this worktree**
> (`_bmad-output/test-artifacts/` does not exist — only `planning-artifacts/`).
> The 8-section per-epic shape, the L0–L6 test-level architecture (L0 static ·
> L1 property · L2 contract · L3 acceptance · L4 participation/scenario · L5
> mutation targets · L6 requirements-fidelity review), the "one behaviour, one
> level — lower level wins" rule, the T2 tier scope, and this epic's R-007
> risk-gate row are taken from the lane task verbatim and reconstructed from
> `docs/lenses/testing/test-strategy.md` + `docs/lenses/testing/fixtures-and-scenarios.md`
> (both ratified) and the sibling PLANs already in `qa/epics/`. If the real
> test-design-qa.md / QMX-handoff.md are later restored, treat them as
> authoritative and reconcile this plan's level names and gate numbering.

---

## Section 1 — Header and baseline

- **Epic:** 6 — `qmf-data` — source intake (Wave 3, priority **M**). After Epic 3; parallel with Epics 5/7/8/9.
- **Tier:** **T2.** Scope = **L2 (contract) + L3 (acceptance) for every AC** as the primary deliverable, **targeted L1 properties** (only the highest-value quantified invariants — the R-007 refusal universals, source-identity fingerprinting, provenance verbatim), a **light L4** (two scenario participations), an **L5 mutation roster**, and the **L6 requirements-fidelity review** seat. L0 structural gates are included. Full L4 participation breadth and L5 mutation execution are lighter than a T1 lane (Section 6/7 record what is deferred).
- **Component under test:** `COMP-QMF-DATA-INGEST` (the middleware source-ingest seam) plus its two active external-provider adapters `COMP-DUKASCOPY` and `COMP-CALENDAR-FEED`.
- **Package / modules in scope** (names + layout only, no body read before Section 4). The intake code is co-located in the `qmf-data` package (`packages/qmf-data/`, import root `qmf.data`, `src/` layout):
  - `ingest.py` — CT-15 adapter seam + idempotent intake + CT-10 producer translation (Story 6.1).
  - `source_boundary.py` — the external-source request/response boundary; source⊥VenueId (Story 6.1).
  - `ticks.py` — bid/ask preservation + source-disagreement edges (Story 6.2).
  - `dukascopy.py` — download-once historical tick adapter (Story 6.3).
  - `calendar_feed.py` — news-calendar feed, fail-closed degradation (Story 6.4).
  - Shared (Epic-3-owned, consumed as producer target — **not** re-verified here): `observation.py` (CT-10 record), `journal_producer.py` / `journal.py` (CT-13 journal), `store/**` (CT-11 governed store).
- **Requirement ids this epic owns** (copied from the `epics.md` FR Coverage Map + Epic 6 story headers — not re-derived):
  - **FR:** FR-015 (idempotent CT-15 intake seam), FR-017 (Dukascopy first historical source), FR-018 (news-calendar feed, fail-closed windows).
  - **CT (owned):** CT-15 (external-source adapter, owner `COMP-QMF-DATA-INGEST`).
  - **CT (consumed / producer-obligation only — epic-binding boundary):** CT-10 (source-observation; produced by ingest, **owned by Epic 3**), CT-07 (lineage-edge `corroborates`/`disagrees-with`; **owned by Epic 2**), CT-13 (journal `data quality` event type; **owned by Epic 3**), CT-03 (instrument mapping; **owned by Epic 1**), CT-04 (typed refusal; owned by Epic 1).
  - **Stories:** 6.1 (AC1–AC6), 6.2 (AC1–AC3), 6.3 (AC1–AC5), 6.4 (AC1–AC5) — 19 acceptance criteria total.
  - **Constitution laws:** L8/L9 (application loops, schedulers, UI stay outside the framework — the seam is a called port), L18 (raw evidence retained locally forever), L20 (synthetic proves infrastructure only, never edge), L30 (default-deny inter-library edges), L34 (secret references never values — touches provider credentials at the adapter edge).
  - **Scenarios:** SCN-0002 (source correction), SCN-0008 (news windows fail-closed — **intake-side half only**; the CT-31 window enforcement is Epic 10's).
- **Owned risk-gate row (from the lane task):** **R-007** — adversarial intake input (malformed, truncated, wrong-schema, hostile filenames) **refuses (typed CT-04) rather than returning Ok**, and every provider/store fault surfaces as a **returned** refusal, never an exception across the seam boundary. Fault fakes MUST raise **real third-party exception types** (fault-realism rule). Epic-specific emphases from the task: **provenance recorded at intake**, **source identity fingerprinted**, **no intake path writes governed namespaces directly**.
- **Evidence baseline** (from `coverage.json`, a data artifact — **no source logic read**):

  | Module | Line cov | Branch cov | Missing branches | Signal |
  |---|---|---|---|---|
  | `ingest.py` | 88.3% (194/210) | 62/80 | **18** | refusal-translation branches likely partial |
  | `source_boundary.py` | 100% (37/37) | 12/12 | 0 | thin boundary, fully covered |
  | `ticks.py` | 80.1% (129/148) | 44/68 | **24** | bid/ask split + disagreement-edge refusal arms |
  | `dukascopy.py` | 83.6% (223/252) | 68/96 | **28** | licence-gate + malformed-refusal + path-safety arms |
  | `calendar_feed.py` | **77.6% (230/273)** | 61/102 | **41** | **below the 80% line at file level**; fail-closed / refusal arms |
  | `observation.py` (Epic-3) | 99.4% | 101/102 | 1 | consumed, not re-verified |
  | `journal_producer.py` (Epic-3) | 98.2% | 33/34 | 1 | consumed, not re-verified |

  The high missing-*branch* counts on the four intake modules are the classic signature of **unexercised error/refusal branches** — precisely the R-007 refusal and fail-closed paths this epic must guarantee.
- **Build/advisory-review report:** Epic 6 < 20, so no epic build/advisory-review report exists (stated explicitly per template).
- **Distribution-unit check** (directory listing only): `packages/qmf-data/` ships `FAILURES.md` **and** an `examples/` directory (`ingest_usage.py`, `dukascopy_usage.py`, `calendar_feed_usage.py`, `ticks_usage.py`, … present). No NFR-11 / L27 distribution-unit gap for this epic — **no invented finding.**

---

## Section 2 — Requirement extract (the oracle)

Acceptance criteria quoted / tightly paraphrased from `epics.md` §Epic 6; contract clauses from the CT-* YAML; scenario clauses from SCN-0002 / SCN-0008. Ambiguities are logged in Section 7, never resolved by reading code.

### 2.1 Story acceptance criteria (`epics.md` §Epic 6)

**Story 6.1 — CT-15 adapter seam and idempotent intake (FR-015).**
- **AC1** — `COMP-QMF-DATA-INGEST` is the QMF owner and caller of CT-15; `COMP-QMF-DATA` does not accept CT-15. A bounded request → response is validated + normalized and submitted as **CT-10 producer observation VALUES to the Data-owned CT-10 boundary — application-routed, creating no package dependency on qmf-data** (DEC-0117/0119/0120).
- **AC2** — Intake is idempotent on `(source, source-native id, revision)`; a duplicate/out-of-order/corrected record → a revision is admitted as **a new artifact with its own fp1, never a collision**, and earlier evidence is **never erased or silently merged** (FM-3, DEC-0119/0108).
- **AC3** — Foreign timestamp stored **verbatim** with declared zone/offset/resolution; foreign money **verbatim** as scaled integers at the source's declared scale; conversions to framework Time/Money are **derived under lineage, corrections appended, never overwritten** (DEC-0106/0105).
- **AC4** — A record lacking event-time, known-at, source key, revision, or a **CT-03 instrument mapping** → **no CT-10 value emitted and an `invalid input` typed refusal** (FM-2/FM-6, DEC-0109/0117).
- **AC5** — Provider unavailable / rate-limited → **no fabricated observation**, and a **`transient venue failure` or `unavailable dependency` typed refusal**; a read-only `source` is never conflated with a tradeable `VenueId` (FM-1/FM-7, DEC-0109/0107).
- **AC6** — A caller asking the seam to run a scheduler/daemon/process-supervisor/retry-loop → **refused as outside the component**; the seam is a called port, not a running downloader (FM-5, DEC-0051/0119).

**Story 6.2 — Bid/ask preservation and source-disagreement edges (FR-015).**
- **AC1** — Tick sources separately identified; **bid and ask preserved separately with source timestamps, never merged into a mid** (DEC-0119/0105).
- **AC2** — Two sources reporting the same fact → **`corroborates` edge** on agreement, **`disagrees-with` edge** on disagreement; **disagreement stays visible, never averaged/merged away** (FM-3, DEC-0119).
- **AC3** — A later revision of a source fact → keyed under idempotent `(source, source-native id, revision)` as **a new artifact linked to the earlier one, never overwriting** (DEC-0119/0108).

**Story 6.3 — Dukascopy download-once historical tick adapter (FR-017).**
- **AC1** — Download-once: the historical corpus is pulled **a single time** under the user's own provider relationship into the QMF **immutable raw archive**; **runs never fetch from providers**; every accepted record retains external source identity and converts to CT-10 (AR-54, DEC-0166/0053).
- **AC2** — Every ingested window records **provenance plus a license tag**; a window **without a recorded usage right offered for governed-evidence use is a typed refusal** — an unlicensed window can never silently become governed evidence; the per-window license-tag mechanism stays in force (AR-54, DEC-0166/0170).
- **AC3** — A malformed / missing-timestamp / **unmappable-to-CT-03** record → **not admitted as valid evidence; an `invalid input` refusal from the seven-category taxonomy** (FM-2, DEC-0038/0109).
- **AC4** — D1 build-our-own law: **no donor code enters the tree** (`dukascopy-node` is reference-only shape); a request to **bulk-download the complete corpus during documentation or a factory pass is refused as outside the component** — only bounded adapter evidence until installation/runbook execution (FM-5, DEC-0166/0013/0051).
- **AC5** — Raw originals + lineage **kept forever, partitioned by source/instrument/time-window**; when a bounded transfer stops or the source is unavailable, **QMF cannot require external recovery** — checkpoint/retry/operator-visible refusal live in the standalone application (FM-1, DEC-0051/0118/0119).

**Story 6.4 — News-calendar feed, fail-closed degradation (FR-018).**
- **AC1** — `COMP-CALENDAR-FEED` (distinct from market-hours + day-boundary calendars) — the recorder keeps **provider-native event identity and revisions** through idempotent `(source, source-native id, revision)`; each revision a new artifact, corrections appended, **never overwriting** (FM-2, DEC-0052/0119/0117).
- **AC2** — Provider **impact labels stored verbatim**; **QMX mints no severity scale in V1**; the event carries event-time/known-at/source/revision under the recorder's own WriterId; **the feed defines no window and holds no permission** — the risk-side blackout is CT-31's, derived from this evidence (DEC-0152/0117).
- **AC3** — Every import is **journaled as a `data quality` event in the ratified CT-13 journal**, not an invented format (FR-018, DEC-0119).
- **AC4** — A failed refresh / unknown coverage → **degrades visibly: journaled as a `data quality` event and alarmed**, treated-as-affected downstream (blocks new entries at the **CT-31** boundary — *Epic 10 territory, see Section 7*); **no live skip button; the feed supplies no permission** (FM-4, DEC-0065/0152; SCN-0008).
- **AC5** — Licensing / long-term retention rights unresolved → the recorder **does not claim operational retention is authorized**; the legal archiving posture stays an open operator item, **recorded not resolved** (FM-3/FM-4, DEC-0119/0052).

### 2.2 Contract clauses (verbatim, load-bearing invariants)

- **CT-15 idempotent intake:** "Intake is idempotent keyed on (source, source-native id, revision); a provider revision is a NEW artifact, never an fp1 collision."
- **CT-15 source⊥VenueId:** "source is a core provenance noun orthogonal to VenueId … a provider you only read from is a source; COMP-DUKASCOPY and COMP-CALENDAR-FEED are sources."
- **CT-15 boundary refusals:** "Boundary failures return typed refusals — transient venue failure, unavailable dependency, or invalid input for a malformed provider payload — **returned, never raised across the boundary**." `boundary_refusal_categories: [transient venue failure, unavailable dependency, invalid input, storage failure]`.
- **CT-15 data-only participation:** "COMP-QMF-DATA does not accept CT-15; it accepts Data-Ingest producer observations through the Data-owned CT-10 boundary."
- **CT-15 bid/ask + edges:** "Tick sources are separately identified … with bid and ask preserved and their source timestamps kept." "Source disagreements stay visible via corroborates / disagrees-with typed edges and are never merged away."
- **CT-15 verbatim evidence:** "Foreign timestamps and foreign money … are stored verbatim as evidence with their declared zone and scale; conversions are derived under lineage and corrections are appended, never overwritten."
- **CT-15 lifecycle boundary:** "Scheduled process lifecycle stays outside the qmf-data library; the adapter is a called port, not a running downloader."
- **CT-15 nullability:** "source, source_native_id, and revision are the intake key and are required; null is prohibited in identity content — an absent value is an omitted key."
- **CT-04 (consumed):** "The refusal category is one of exactly seven … invalid input, unsupported capability, unavailable dependency, stale evidence, policy rejection, transient venue failure, storage failure." "Refusals are RETURNED across public boundaries … exceptions are reserved for programmer error." "storage failure … store-library exceptions are translated into a storage-failure refusal at the qmf-data boundary, never propagated."
- **CT-07 (consumed, edge-type obligation):** "corroborates and disagrees-with edges keep source disagreements visible and are never merged away — the same mechanism tick-source disagreements use."
- **CT-10 (consumed, producer obligation):** identity = fp1; "(instant, writer, sequence) is a replay-ordering key … the record's identity is its fp1 fingerprint"; "Producers (the ingest door and venue-originated facts) submit observation VALUES routed by the application; producing a value creates no package dependency on qmf-data."

### 2.3 Scenario clauses (SCN-0002, SCN-0008)

- **SCN-0002 (source correction):** an original observation + a later correction to the same provider-native occurrence → **two distinct fp1 artifacts joined by an append-only typed lineage edge; the original is preserved.**
- **SCN-0008 (intake-side half only):** "the recorder keeps the provider's native event identity and revisions through the idempotent `(source, source-native id, revision)` intake"; "Enforcement is at read time, never at intake (intake keeps provider evidence verbatim and appends corrections)"; "a failed calendar refresh, unknown coverage … the absence journaled as `data quality` and raising an alarm"; "the feed supplies no permission." *(The widen-never-shrink read-time fold and the entries-only block are CT-31 / Epic 10 — Section 7.)*

---

## Section 3 — Fault-family checklist (+ R-007 gate)

The R-007 risk gate is this epic's spine. Below, each generic fault family is marked present/absent for Epic 6 with the site and the test that carries it. "None" is a result.

| # | Family | In Epic 6? | Where / how it manifests → test |
|---|---|---|---|
| a | Unit-kind / money treated as optional on a numeric path | **YES** | Foreign money must be stored verbatim as scaled-int at the declared scale; a binary float on the money path or a silent rescale is the defect (DEC-0105). Bid/ask are scaled-ints, never a mid. Sites: `ingest.py`, `ticks.py`. → **L1-004, L2-006, L2-008.** |
| b | An exception where a typed refusal was contracted | **YES (the R-007 core)** | CT-15: failures are "returned, never raised." Real third-party exceptions (network, decompression, unpack, JSON, OS) from a provider/transport/store fake must be **translated to a RETURNED CT-04 refusal**. Sites: every adapter + `ingest.py`. → **L1-001, L1-002, L2-003, L2-004, L2-013.** |
| c | A fingerprint that omits a distinguishing input | **YES** | fp1 identity must include the `(source, source-native id, revision)` intake key; a new revision → new fp1, never a collision; a byte-identical re-intake → the same fp1 (idempotent). Occurrence-only fields (receive wall time, monotonic diagnostic) must be excluded from identity. → **L1-003, L2-002, L2-010.** |
| d | A governance gate implemented at one input shape | **YES** | The R-007 refusal must hold over the *whole* adversarial input space (fuzzed), not one hand-picked malformed record; the licence gate must hold over *every* unlicensed window, not one. → **L1-001, L1-006, L2-012.** |
| e | An external input trusted without validation | **YES (the untrusted edge)** | Provider wire (Dukascopy `.bi5` LZMA tick blobs; calendar JSON) is untrusted: truncated blobs, wrong-schema payloads, out-of-range fields, **hostile filenames** (path traversal, NUL, reserved names, absolute paths, overlong). Each must bound-check / refuse and never escape the raw-archive root. → **L1-001, L1-006, L2-013.** |
| f | A capability reachable from one door only | **None (door parity).** | Ingest sits below the door surface (CLI/MCP doors are E16). Recorded as "none" in the door-parity sense; the analogous discipline here is the no-direct-governed-write structural boundary → **L0-001, L3-001.** |
| g | A ledger or journal line missing on a failure path | **YES** | Story 6.4 AC3/AC4: **every** import journals a `data quality` event, and a **failed** refresh must *also* journal `data quality` + alarm (the failure path is exactly the one an implementation forgets to journal). → **L2-017, L3-007.** |
| h | An existing test that pins the implementation rather than the requirement | **SUSPECT — confirm in Section 5.** | The four intake modules carry 18/24/28/**41** missing branches — the refusal / fail-closed / licence-gate arms line coverage cannot see. High prior that `test_calendar_feed.py` and `test_dukascopy.py` assert the happy admit path and pin the code's fold rather than the contract's refusal matrix. |

---

## Section 4 — Independent test list

> **Authored before any `src/` implementation body was read.** Reading a public
> signature to *call* it is permitted afterwards; reading a body before this
> table existed was not. Test ID = `QA-E06-L<level>-<seq>`. Oracle = the exact
> document + clause (never the code). Duplicate-coverage guard: a contract fact
> lives at L2 and is not restated at L3; an epic-specific behaviour or structural
> boundary lives at L3; the cross-package journey lives at L4; a *quantified*
> universal lives at L1. Every boundary **returns** value-or-refusal; a refusal
> assertion checks the CT-04 `category` + machine-readable context, never a
> parsed exception string.
>
> **Epic-binding rule applied.** Where a consumed contract is owned by another
> epic, the test asserts only *this epic's producer/emission obligation*, never
> the other epic's boundary semantics: CT-10 cross-world/seal refusals are
> **Epic 3**'s; CT-07 JSONL append mechanics are **Epic 2**'s; CT-13 stream
> gaplessness is **Epic 3**'s; CT-03 identity is **Epic 1**'s; the CT-31 news
> window is **Epic 10**'s. Each such row is tagged *(producer-obligation only)*.

### L0 — Static / structural gates (oracle = import graph + dependency manifest + directory)

| Test ID | Requirement | Oracle | Pri | Assertion (one sentence) |
|---|---|---|---|---|
| QA-E06-L0-001 | FR-015, DEC-0120, L30 | CT-15 "creates no package dependency on qmf-data"; L30 default-deny | **P0** | The intake modules import only `qmf.core` and the co-located producer-value types, never `qmf.venue` / `qmf.risk`, and introduce no inter-library dependency edge beyond the ratified `qmf-registry → qmf-data`. *(Structural proxy — see F-E06-002 on the co-location limit.)* |
| QA-E06-L0-002 | FR-015, FR-017, L8, DEC-0009/0051 | Story 6.1 AC6 / 6.3 AC4; CT-15 lifecycle | P1 | No intake module exports or contains a scheduler, daemon, event loop, process supervisor, or retry loop (no `asyncio`/`threading`/`sched`/`schedule`/`while True` polling surface) — the seam is a called port. |
| QA-E06-L0-003 | FR-017, DEC-0166/0013 | Story 6.3 AC4; D1 build-our-own law | P1 | No `dukascopy-node` / donor provider code is vendored in the tree and no such runtime dependency is declared in `pyproject.toml`/`DEPENDENCIES.md`; the downloader is build-our-own. |

### L1 — Property / invariant tests (`hypothesis`); oracle = a contract/law invariant, quantified. *Targeted (T2).*

| Test ID | Requirement | Oracle | Pri | Assertion (one sentence) |
|---|---|---|---|---|
| QA-E06-L1-001 | **R-007**, FR-015, CT-15, CT-04 | CT-15 "invalid input for a malformed provider payload"; Story 6.1 AC4 | **P0** | For arbitrary malformed / truncated / wrong-schema / out-of-range provider payloads (fuzzed), intake **always returns a typed CT-04 refusal (`invalid input`)**, **never** admits a CT-10 value, and **never returns Ok** — the input space includes payloads that make the parser raise a real third-party exception. |
| QA-E06-L1-002 | **R-007**, FR-015, CT-15, CT-04 | CT-15 "returned, never raised across the boundary"; CT-04 storage-failure translation | **P0** | Across the full provider/transport/store fault matrix — the fake raising **real third-party exception types** (`requests.exceptions.ConnectionError`/`Timeout`/`HTTPError`(429), `urllib.error.URLError`, `socket.timeout`, `ConnectionResetError`, `lzma.LZMAError`, `EOFError`, `struct.error`, `json.JSONDecodeError`, `UnicodeDecodeError`, `OSError`) — **no exception type escapes the CT-15 boundary**; every fault surfaces as a **returned** refusal (`transient venue failure` \| `unavailable dependency` \| `invalid input` \| `storage failure`). |
| QA-E06-L1-003 | **source identity fingerprinted**, FR-015, CT-15, CT-10 | CT-15 idempotent-intake invariant; CT-10 identity=fp1 | **P0** | The `(source, source-native id, revision)` intake key is identity-bearing: two observations differing in any of the three produce **distinct fp1**; a new revision of the same fact → **a new fp1, never a collision**; a byte-identical re-intake → **the same fp1** (idempotent accept, no second artifact); occurrence-only fields (receive wall time, monotonic diagnostic) are excluded from identity. |
| QA-E06-L1-004 | **provenance recorded**, FR-015, CT-15, CT-10 | CT-15/CT-10 verbatim clauses (DEC-0106/0105) | P1 | For arbitrary payloads, the admitted value stores the foreign timestamp **verbatim** with declared zone/offset/resolution and foreign money **verbatim** as scaled-int at the declared scale; a coarser source resolution is never presented finer; **no binary float ever appears on the money path or in identity**. |
| QA-E06-L1-005 | FR-015, CT-15, DEC-0107/0117 | CT-15 source⊥VenueId invariant; Story 6.1 AC5, FM-7 | P1 | For any generated source id, a read-only `source` is **never conflated with a tradeable `VenueId`** — a route/construction that treats a source as a VenueId is refused/rejected, never silently accepted. |
| QA-E06-L1-006 | **R-007 (hostile filenames)**, FR-017 | Story 6.3 AC3; L18 raw-archive integrity | P1 | For arbitrary adversarial file identifiers offered to the Dukascopy download-once path (path traversal `../`, absolute paths, embedded NUL, reserved names `CON`/`PRN`/…, overlong), the adapter **refuses (`invalid input` \| `storage failure`)**, **never resolves a path outside the immutable raw-archive root**, and never crashes. |
| QA-E06-L1-007 | FR-015, CT-10/CT-15 append-only | CT-10 "never overwritten"; Story 6.1 AC2/AC3, 6.2 AC3, 6.4 AC1 | P1 | Across arbitrary correction/revision sequences, **no earlier admitted observation is ever overwritten or mutated** — a correction/revision only appends a new fp1 artifact carrying the link to the prior. |

### L2 — Contract-conformance tests; oracle = the CT-* YAML clause. *Primary deliverable — every AC family.*

| Test ID | Requirement | Oracle | Pri | Assertion (one sentence) |
|---|---|---|---|---|
| QA-E06-L2-001 | FR-015, CT-15 | CT-15 schema round-trip; Story 6.1 AC1 | P1 | A valid provider response normalizes to a CT-10 producer value carrying `contract_format_version`, `source`, `source_native_id`, `revision`, `event_time`, `known_at`, the foreign-timestamp block, and (price-bearing) `bid`/`ask` scaled-ints — encode/decode semantic equality. |
| QA-E06-L2-002 | FR-015, CT-15 | CT-15 idempotent-intake invariant; Story 6.1 AC2 | **P0** | A duplicate / out-of-order / corrected record keys on `(source, source-native id, revision)`; a revision is a **new artifact with its own fp1, never a collision**, and earlier evidence is never erased or silently merged. |
| QA-E06-L2-003 | FR-015, CT-15, CT-03 | CT-15 refusal enum; Story 6.1 AC4, FM-2/FM-6 | **P0** | A record missing any of {event-time, known-at, source, revision, **CT-03 instrument mapping**} → **`invalid input` refusal and no CT-10 value emitted**. *(CT-03 identity is Epic-1-owned; asserted as the ingest refusal obligation only.)* |
| QA-E06-L2-004 | FR-015, CT-15 | CT-15 `boundary_refusal_categories`; Story 6.1 AC5, FM-1 | **P0** | Provider unavailable / rate-limited → a **returned** `transient venue failure` \| `unavailable dependency` refusal and **no fabricated observation**. |
| QA-E06-L2-005 | FR-015, CT-15 | CT-15 nullability clause | P1 | `source`, `source_native_id`, `revision` are required; null is prohibited in identity content (an absent value is an omitted key, never null). |
| QA-E06-L2-006 | FR-015, CT-15 | CT-15 units/verbatim invariants; Story 6.1 AC3 | P1 | Foreign timestamp stored with declared zone/offset/resolution; foreign money as scaled-int at the declared scale; conversions to Time/Money are derived under lineage; binary float is inadmissible on the money path. |
| QA-E06-L2-007 | FR-015, CT-10 *(producer-obligation only)* | CT-10 producers clause; Story 6.1 AC1 | P1 | The value ingest submits satisfies the CT-10 **producer** schema (distinct event-time/known-at, writer + boot-epoch + strictly-increasing sequence, `world ∈ {live, replay}`, fp1 identity); producing a value creates no package dependency on qmf-data. *(CT-10 cross-world/seal refusals are Epic 3's — not asserted here.)* |
| QA-E06-L2-008 | FR-015, CT-15 | CT-15 bid/ask invariant; Story 6.2 AC1 | **P0** | Tick observations preserve `bid` and `ask` **separately** with their source timestamps and are **never merged into a single mid value**. |
| QA-E06-L2-009 | FR-015, CT-07 *(edge-type obligation only)* | CT-07 corroborates/disagrees-with; Story 6.2 AC2 | P1 | Two sources reporting the same fact select a **`corroborates`** edge on agreement and a **`disagrees-with`** edge on disagreement; the disagreement stays visible and is never averaged/merged. *(CT-07 JSONL append mechanics are Epic 2's.)* |
| QA-E06-L2-010 | FR-015, CT-15 | CT-15 revision-linkage invariant; Story 6.2 AC3 | P1 | A later revision of a source fact keys under idempotent intake as a **new artifact linked to the earlier one**, never overwriting it. |
| QA-E06-L2-011 | FR-017, CT-15 | Dukascopy component + Story 6.3 AC1 (AR-54, DEC-0166) | P1 | The historical corpus is acquired **once** into the immutable raw archive under the user's own provider relationship; every accepted record retains external source identity and converts to CT-10; runs never fetch from providers. |
| QA-E06-L2-012 | **provenance/licence**, FR-017 | Story 6.3 AC2 (DEC-0170, AR-54) | **P0** | Every ingested window records **provenance + a license tag**; a window **without a recorded usage right offered for governed-evidence use is a typed refusal** — an unlicensed window can never silently become governed evidence. |
| QA-E06-L2-013 | **R-007**, FR-017, CT-15, CT-03 | Story 6.3 AC3, FM-2 (DEC-0038/0109) | **P0** | A malformed / missing-timestamp / **unmappable-to-CT-03** Dukascopy record → **not admitted; an `invalid input` refusal** from the seven-category taxonomy. *(Concrete Dukascopy instance of the L1-001 universal.)* |
| QA-E06-L2-014 | FR-017, DEC-0118 | Story 6.3 AC5 (keep-forever partition) | P2 | Raw originals + lineage are recorded to a room **partitioned by source, instrument, and time-window** and marked retained-forever; the accepted evidence record carries that partition identity. |
| QA-E06-L2-015 | FR-018, CT-15 | Story 6.4 AC1; calendar-feed component | P1 | The news-calendar recorder keeps **provider-native event identity + revisions** through `(source, source-native id, revision)`; each revision a new artifact; corrections appended, never overwriting. |
| QA-E06-L2-016 | FR-018, CT-15 | Story 6.4 AC2 (DEC-0152) | P1 | Provider **impact labels are stored verbatim**; **QMX mints no severity scale in V1**; the recorded event carries event-time/known-at/source/revision under the recorder's WriterId; **the feed defines no window and holds no permission**. *(CT-31 window is Epic 10's.)* |
| QA-E06-L2-017 | FR-018, CT-13 *(event-type obligation only)* | Story 6.4 AC3; CT-13 event types | **P0** | **Every** import is journaled as a **`data quality`** event in the ratified CT-13 journal (one of the seven types, not an invented format). *(CT-13 stream gaplessness is Epic 3's.)* |
| QA-E06-L2-018 | FR-018, DEC-0119/0052 | Story 6.4 AC5, FM-4 | P2 | The recorder carries **no claim that operational retention is authorized**; the legal archiving posture rides through intake as recorded-not-resolved evidence, never an authorization. |

### L3 — Acceptance tests; oracle = the `epics.md` AC / SCN sentence (epic-specific behaviour + structural boundary)

| Test ID | Requirement | Oracle | Pri | Assertion (one sentence) |
|---|---|---|---|---|
| QA-E06-L3-001 | **no governed-namespace write**, FR-015, DEC-0117/0119/0120 | Ingest component May-never ("never persist raw evidence directly around CT-10 and CT-11"); Story 6.1 AC1 | **P0** | Driven by an injected fake CT-10 producer boundary **and** an injected fake governed store: the ingest path submits CT-10 producer **VALUES** application-routed and **never calls a store/room writer or writes a CT-10/CT-11 governed namespace directly** — the injected store is asserted untouched by the ingest path. |
| QA-E06-L3-002 | FR-015, Story 6.1 AC6 | Story 6.1 AC6, FM-5 | P1 | A caller asking the seam to operate a scheduler / daemon / process supervisor / retry loop is **refused as outside the component**. |
| QA-E06-L3-003 | FR-015, Story 6.1 AC1 | Story 6.1 AC1 | P1 | With an injected fake provider transport, a bounded request → response is **validated + normalized** and submitted as a CT-10 producer value; the seam is the sole CT-15 caller (COMP-QMF-DATA does not accept CT-15). |
| QA-E06-L3-004 | FR-017, Story 6.3 AC1 | Story 6.3 AC1 | P1 | With an injected fake Dukascopy transport, the corpus is pulled **once** into the immutable raw archive; a **second run reads only qmf-data rooms and does not re-fetch** from the provider. |
| QA-E06-L3-005 | FR-017, Story 6.3 AC4 | Story 6.3 AC4, FM-5 | P1 | A request to **bulk-download the complete corpus during a documentation / factory pass is refused as outside the component** — only bounded adapter evidence is permitted. |
| QA-E06-L3-006 | FR-017, Story 6.3 AC5 | Story 6.3 AC5, FM-1 | P1 | When a bounded transfer stops or the source is unavailable, the seam **returns a refusal and fabricates nothing**; QMF requires no external recovery (checkpoint/retry live in the application). |
| QA-E06-L3-007 | **fail-closed journal**, FR-018, Story 6.4 AC4 | Story 6.4 AC4, FM-4; SCN-0008 | **P0** | A **failed** calendar refresh (or unknown coverage) **journals a `data quality` event and raises an alarm** on the intake side, and the feed **supplies no permission** (no live skip). *(The downstream CT-31 entry block is Epic 10 — Section 7.)* |
| QA-E06-L3-008 | FR-015, Story 6.2 AC1 | Story 6.2 AC1 | P1 | Recording tick observations from two separately-identified sources preserves `bid` + `ask` separately with source timestamps; **no mid is synthesized** and the two sources are never coalesced into one number. |
| QA-E06-L3-009 | FR-015, Story 6.2 AC2 | Story 6.2 AC2 | P1 | Two sources reporting the same fact with differing values keep the disagreement **inspectable via a `disagrees-with` edge**; agreement yields `corroborates`; **nothing is averaged away**. |

### L4 — Scenario / participation tests; oracle = the SCN prose (cross-package journey; light for T2)

| Test ID | Requirement | Oracle | Pri | Assertion (one sentence) |
|---|---|---|---|---|
| QA-E06-L4-001 | SCN-0002, FR-015 | `docs/scenarios/SCN-0002-source-correction.md`; Story 6.1 AC2/AC3 | P1 | End to end over the ingest seam + injected CT-10 producer boundary + edge sink: an original observation and a later correction to the **same provider-native occurrence** produce **two distinct fp1 artifacts joined by an append-only typed lineage edge**, with the original preserved unmutated. |
| QA-E06-L4-002 | SCN-0008 *(intake-side half)*, FR-018 | `docs/scenarios/SCN-0008-pair-scoped-news.md` | P1 | The news-calendar recorder ingests events + revisions keeping provider evidence **verbatim and append-only** (no read-time widening at intake), and a failed refresh **journals `data quality` + alarms** — the intake-side half of SCN-0008. *(CT-31 window resolution/enforcement excluded — Epic 10.)* |

**Planned counts — L0: 3 · L1: 7 · L2: 18 · L3: 9 · L4: 2.** L1–L4 total **36**; with L0 gates **39 planned checks**. Each L2/L3 family expands to several parametrized cases at implementation (per-provider, per-refusal-category, per-field).

---

## Section 5 — Existing-test audit (+ source-reconciliation focus)

The author-written suites in `packages/qmf-data/tests/` produced the Section-1 coverage. For every requirement in Section 2, the lane names the covering test and classifies it **keep** / **suspect** / **contradicts**; every "contradicts" goes to `findings.csv` with the requirement id (this is where R-003 — existing-test audit — gets its evidence). **No source body was read to author Section 4; the reconciliation below is the read that happens after.**

| Existing test module | Requirements it claims | Audit focus (classify per requirement) |
|---|---|---|
| `test_ingest.py` | FR-015, CT-15 (idempotent intake, translation) | Confirm it asserts the **idempotent-key = fp1 identity** (new revision → new fp1; byte-identical → same fp1) and the **returned-refusal** translation, not just a happy admit. Suspect if the malformed set is one hand-picked record rather than the R-007 space. |
| `test_source_boundary.py` | FR-015, CT-15 (source⊥VenueId, boundary) | Confirm source⊥VenueId is asserted and that the boundary **returns** refusals; module is 100% covered — verify the coverage is on behaviour, not just constructors. |
| `test_ticks.py` | FR-015, CT-15 (bid/ask, edges) | **Suspect (24 missing branches).** Confirm bid/ask are never merged to a mid and that `disagrees-with` is emitted on disagreement — the *disagreement* arm is the one branch-coverage suggests is unexercised. |
| `test_dukascopy.py` | FR-017 (download-once, licence, malformed) | **High suspicion (28 missing branches).** Confirm the **licence-gate refusal** (unlicensed window) and the **malformed / unmappable-CT-03 refusal** are asserted, and that **hostile filenames** are covered — likely the missing branches. |
| `test_calendar_feed.py` | FR-018 (recorder, fail-closed) | **Highest suspicion (below 80% line; 41 missing branches).** Confirm the **failed-refresh → `data quality` journal + alarm** path is asserted (the failure journal is family g), not only the happy import; confirm no-severity-minted + no-permission. |
| `test_ct10_contract.py` | CT-10 (producer shape) | Epic-3-owned contract; confirm the ingest producer-value conformance (L2-007) is present and that this module does not silently assert Epic-3 boundary refusals as if they were the ingest's. |

R-007 refusal universals (L1-001/002), source-identity fingerprinting (L1-003), hostile filenames (L1-006), and the no-governed-write structural boundary (L3-001) are **quantified/structural** claims the existing per-behaviour tests cannot make; they are net-new independent tests regardless of the audit outcome. The missing-branch hot-spots (`calendar_feed.py` 41, `dukascopy.py` 28, `ticks.py` 24, `ingest.py` 18) are the branch-hunting focus — each residual partial after the suite runs is recorded as a finding with the missing branch named, never closed by a source edit.

---

## Section 6 — Mutation targets (`mutmut` roster)

Inclusion rule: a surviving mutant here would leave a **governance / evidence / refusal** claim unasserted. (T2 roster — execution is lighter than a T1 lane; the roster is specified so the L6 seat can spot-check.)

| Module | Justification |
|---|---|
| `ingest.py` | The idempotent-key derivation and the exception→refusal translation are the R-007 core; a survivor means a malformed record is admitted or an exception escapes the seam. |
| `ticks.py` | The bid/ask split and the `corroborates`/`disagrees-with` selection; a survivor means two sources coalesce to a mid or a disagreement is merged away. |
| `dukascopy.py` | The licence-tag gate, the malformed-record refusal, and the path-safety check; a survivor means an unlicensed window or a hostile filename slips through. |
| `calendar_feed.py` | The failed-refresh `data quality` journal + alarm and the no-permission posture; a survivor means an outage passes silently or the feed leaks a permission. |
| `source_boundary.py` | The source⊥VenueId guard and the producer-value routing; a survivor means a source is treated as a VenueId or a value is written to a governed namespace directly. |

**Excluded** (reports/formatting/examples): `_bench.py`, `examples/**`, and any pure rendering/logging helper.

---

## Section 7 — Deferred and out of scope (untestable now — blocked specs, not plan gaps)

| Item | Disposition | Reference |
|---|---|---|
| **CT-31 news-blackout window enforcement** — "treated-as-affected downstream (blocks new entries at the CT-31 boundary)", widen-never-shrink read-time fold, currency-exposure scope | **OUT OF SCOPE — owned by Epic 10** (COMP-QMF-RISK, FR-033), ratified-surface **defined-unwired**; no risk runtime exists. This epic tests only the intake-side half (verbatim evidence, `data quality` journal + alarm on failed refresh, no-permission — L3-007, L4-002). The entry block is not this epic's and not runtime-provable here. | epics.md §Epic 10; CT-31; SCN-0008; DEC-0152 |
| **cTrader venue-as-source intake** (CT-15/DEC-0138 homes venue market data here) | **OUT OF SCOPE for Epic 6** — `COMP-CTRADER` is an **intended** provider whose adapter ships through the factory (Epic 8), not wired; Epic 6's active providers are Dukascopy + calendar-feed only. Contract-shape is conformance-testable; a runtime proof over a real venue source is blocked. | CT-15 `intended_providers`; epics.md §Epic 8; DEC-0135/0138 |
| **Legal archiving / long-term retention rights** (Story 6.4 AC5; Dukascopy licence beyond personal use) | **UNRESOLVED / recorded-not-resolved** — an open operator item with no ratified posture. The *behaviour* (the seam claims no authorization; the per-window licence-tag gate holds) is tested (L2-012, L2-018); the legal resolution itself is not a code behaviour to assert. | Story 6.3 AC2 (DEC-0170), 6.4 AC5 (DEC-0052/0119) |
| **Concrete provider wire schemas** (Dukascopy symbol list / `.bi5` layout; calendar provider field roster) | **DOCUMENTATION-TIME DETAIL, not ratified spine** — adapter tests use recorded/generated responses and never assert provider internals. Not a plan gap. | test-strategy external-component rule; fixtures-and-scenarios lens |
| **Numeric rate limits / retry / pacing / batching constants** | **DEFERRED — node values under do-not-default** (DEC-0137); no spine value to assert. The *behaviour* (refuse on rate-limit; fabricate nothing) is tested (L2-004); the numeric ceilings are not QMF surface. | ingest component Configuration note; DEC-0137 |
| **Live provider network** | **OUT OF SCOPE in a verification phase** — no live network in tier-1/2; external outcomes enter only as controlled replays through the CT-15 fake (DEC-0007/0054). | fixtures-and-scenarios determinism rules |

**Testability note (structural).** COMP-QMF-DATA-INGEST is **co-located inside** `packages/qmf-data` (`ingest.py`, `source_boundary.py`, `ticks.py`, `dukascopy.py`, `calendar_feed.py` all under `qmf/data/`), while the architecture models it as a separate middleware component that "creates no package dependency on qmf-data" and submits values "application-routed". Import-graph isolation therefore cannot prove the "no package dependency" invariant the way a separate package would; **L0-001 / L3-001 assert the behavioural proxy** (no direct governed-store write; producer-values-only). Recorded as F-E06-002.

---

## Section 8 — Findings (authored while writing this plan; **no fixes**) + execution & exit

Findings are authored from **data artifacts + directory listings only** — no `src/` body was read. Appended to `qa/epics/epic_06_qmf-data-source-intake/findings.csv`.

| Finding ID | Requirement | Severity | Reproducer | Description |
|---|---|---|---|---|
| F-E06-001 | FR-018, DEC-0101 (coverage) | Medium | `coverage.json` → `calendar_feed.py` line 77.6% (230/273), 41 missing branches | `calendar_feed.py` sits **below the 80% line at the file level**, with 41 unexercised branches concentrated on the fail-closed / refusal arms this epic must guarantee (family g/h). The 80% floor is measured per **package**, so this is the **primary branch-hunting target** and becomes a hard finding if the package aggregate dips or any refusal partial survives the suite. Named, not fixed. |
| F-E06-002 | FR-015, DEC-0117/0119/0120 | Info (testability) | `find packages/qmf-data/src/qmf/data/` → `ingest.py`, `source_boundary.py`, `ticks.py`, `dukascopy.py`, `calendar_feed.py` all under one package | COMP-QMF-DATA-INGEST is co-located inside `qmf-data`, so the "no package dependency on qmf-data / application-routed producer values" invariant cannot be proven by import-graph isolation; the behavioural proxy (no direct governed-store write, L3-001) is the strongest available proof. Not a defect — a testability note shaping the suite. |
| F-E06-003 | FR-018, Story 6.4 AC4 | Info (scope) | epics.md §Epic 6 AC4 cites the CT-31 boundary; CT-31 owner = COMP-QMF-RISK | Story 6.4 AC4's downstream consequence ("blocks new entries at the CT-31 boundary, treated-as-affected") is **Epic 10 territory, defined-unwired**, and is not provable in this epic. The intake-side half (journal `data quality` + alarm + no-permission) is this epic's and is tested (L3-007). |
| F-E06-004 | FR-017/FR-018, R-007 | Info (to confirm in §5) | coverage.json missing-branch counts (28 dukascopy, 24 ticks, 41 calendar_feed) author-written | High prior that `test_dukascopy.py` / `test_calendar_feed.py` / `test_ticks.py` assert the happy admit/import path and pin the code's fold rather than the contract's **refusal / fail-closed / disagreement** matrix. Elevated to a confirmed finding only if the Section 5 audit yields a "contradicts" or "suspect" row. |

**Execution order:** L0 structural gates → L1 property universals (R-007 refusal + fault-realism matrix, source-identity fp, hostile filenames) → L2 contract conformance (every AC family) → L3 acceptance (no-governed-write + fail-closed + bid/ask + Dukascopy posture) → L4 scenario participations (SCN-0002, SCN-0008 intake-half). Findings are recorded, not fixed; a red test that asserts a requirement the code violates is a **defect finding**, and source is never edited to make it pass.

**Exit criteria (T2 sign-off for this epic):**
1. Every Section-4 L2 + L3 test authored and executed (pass or fail); every R-007 assertion (L1-001, L1-002, L1-006, L2-003, L2-004, L2-013) has ≥1 passing property/contract test; the three task emphases — provenance recorded (L1-004, L2-012), source identity fingerprinted (L1-003), no governed-namespace write (L0-001, L3-001) — each have a passing test.
2. The four intake modules' refusal / fail-closed branch partials are covered, or each residual partial is recorded as a finding with the missing branch named; `calendar_feed.py` raised to floor or F-E06-001 confirmed.
3. No planned test converts a defined-unwired contract (CT-31) or an open operator item (legal retention) into a pass; every consumed-contract test asserts the producer-obligation only (epic-binding rule).
4. Traceability complete: every test cites FR / CT / AC / SCN / DEC ids; coverage percentage never substitutes for a named-behaviour assertion (DEC-0109).
5. The **L6 requirements-fidelity review** seat has reviewed the lane (one question per test — *does it assert what the requirement demands, or what the implementation happens to do?*) and its verdict is recorded in `L6-REVIEW.md`.

**Plan caveat carried forward:** `test-design-qa.md` and `QMX-handoff.md` were absent from the worktree; if restored, reconcile this plan's section shape, level names, and the R-007 gate framing against them (they are authoritative over this reconstruction).
