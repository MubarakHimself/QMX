# Results — Epic 6: qmf-data — source intake

- **Epic:** 6 — `qmf-data` source intake — FR-015, FR-017, FR-018
- **Contracts:** CT-15 (owned); CT-10, CT-13, CT-07, CT-03, CT-04 (consumed — producer/emission obligation only, per the epic-binding rule)
- **Component(s) under test:** `COMP-QMF-DATA-INGEST` + `COMP-DUKASCOPY` + `COMP-CALENDAR-FEED`
- **Run command:** `uv run --with hypothesis pytest qa/tests/epic_06 -q --tb=short`
- **Tests:** **99 authored / 84 passed / 15 failed / 0 errored** (property tests via `hypothesis`).
- **Findings:** **5** (see `findings.csv`) — **3 confirmed defect findings** (all one root cause: R-007 exception-escape) + **2 UNPROVEN/narrowed requirements**.
- **Author stance:** PLAN Section 4 was authored from the requirements corpus before any `packages/qmf-data/src/**` intake body was opened. Source is read-only evidence. **No source was edited; no assertion was weakened to make a red test pass.** The 15 red tests are the R-007 fault-realism reds — a *defect finding*, not a test-setup error. No test-setup reds were encountered after the fixtures were wired (imports/fakes only).

> **Verdict:** the idempotent-intake, source-identity-fingerprint, verbatim-evidence, bid/ask-preservation, disagreement-edge, license-gate, fail-closed-journal, and no-direct-governed-write obligations of Epic 6 all hold as written. **One ratified MUST is violated:** CT-15's "boundary failures are *returned, never raised across the boundary*" is upheld for payload-parse faults (LZMA / JSON / UTF-8 / struct are caught and translated) but **NOT** for transport-level third-party exceptions — a transport that *raises* a real network/OS exception (`ConnectionResetError`, `socket.timeout`/`TimeoutError`, `OSError`, `BrokenPipeError`, `urllib.error.URLError`, …) sends that exception **across** the CT-15 boundary out of `DukascopyAdapter.fetch`, `CalendarFeedAdapter.fetch`, and `ExternalSourceIngest.fetch_and_intake`. Recorded, not fixed (E6-F01/F02/F03).

Node counts by file: L0 = 16 · L1 = 41 · L2 = 28 · L3 = 12 · L4 = 2 = **99**. (Plan-id families expand to parametrized nodes: e.g. L1-006 → 15 hostile-identifier cases, L2-003/L2-005 → per-field cases.)

---

## The R-007 defect (the 15 reds — one root cause)

| Failing test node | Req | Meaning |
|---|---|---|
| `test_l1_002_dukascopy_transport_raise_returns_refusal[×7]` | R-007, CT-15, FR-017 | A Dukascopy transport raising a **real** third-party exception escapes `DukascopyAdapter.fetch` instead of returning a typed refusal. → **E6-F01** |
| `test_l1_002_calendar_transport_raise_returns_refusal[×7]` | R-007, CT-15, FR-018 | A calendar transport raising a **real** third-party exception escapes `CalendarFeedAdapter.fetch`. → **E6-F02** |
| `test_l1_002_ingest_over_raising_port_returns_refusal` | R-007, CT-15, FR-015 | A provider port that raises escapes `ExternalSourceIngest.fetch_and_intake` (the middleware→application boundary) — same root cause. → **E6-F03** |

The *modelled* provider-failure path — a transport that **returns** `unavailable dependency` / `transient venue failure` — is upheld and green (L2-004, L3-006). The reds are specifically the fault-realism arm (a transport that **raises**), which the shipped seam delegates to the injected transport and does not defensively catch.

---

## L0 — static / structural gates (all PASS)

| Test id | Node | Req | Result |
|---|---|---|---|
| QA-E06-L0-001 | `test_l0_001_no_forbidden_inter_library_import[×5]` | FR-015, DEC-0120, L30 | PASS — every intake module imports only `qmf.core` + own `qmf.data.*`; no `qmf.venue`/`qmf.risk`/`qmf.registry`/`qml`/`qmb`. |
| QA-E06-L0-001 (proxy) | `test_l0_001b_ingest_holds_no_store_reference[×5]` | FR-015, DEC-0117/0119 | PASS — no ingest-side module imports a governed store writer (`append_store`/`parquet`/`facade`); the CT-10 store hand-off lives only in `source_boundary.py`. |
| QA-E06-L0-002 | `test_l0_002_no_scheduler_daemon_or_loop[×5]` | Story 6.1 AC6 / 6.3 AC4, L8 | PASS — no `asyncio`/`threading`/`sched`/`schedule`/`multiprocessing` import and no `while True` poll — the seam is a called port. |
| QA-E06-L0-003 | `test_l0_003_no_dukascopy_node_donor_code` | Story 6.3 AC4, DEC-0166/0013 | PASS — no `dukascopy-node` runtime dep / vendored donor module; the decoder is stdlib-only (`lzma`+`struct`). |

## L1 — property / invariant (hypothesis) — all PASS except the R-007 raise-arm

| Test id | Node | Req | Result |
|---|---|---|---|
| QA-E06-L1-001 | `test_l1_001_malformed_field_always_refuses` | R-007, CT-15, CT-04; AC4 | PASS — corrupting any single required field always yields a typed refusal (invalid input / policy rejection), never Ok, never a raise. |
| QA-E06-L1-001 (control) | `test_l1_001_control_valid_record_is_admitted` | CT-15 | PASS — the uncorrupted control record is admitted (falsifiability control). |
| QA-E06-L1-001 | `test_l1_001_non_provider_record_refused` | CT-15, CT-04 | PASS — a non-`ProviderRecord` value is invalid input, never a raise. |
| QA-E06-L1-002 (payload) | `test_l1_002_bi5_decode_never_raises` | R-007 | PASS — arbitrary bytes into the bi5 decoder surface `lzma.LZMAError`/`struct.error` internally and return a refusal, never raise. |
| QA-E06-L1-002 (payload) | `test_l1_002_calendar_decode_never_raises` | R-007 | PASS — arbitrary bytes into the calendar decoder surface `UnicodeDecodeError`/`json.JSONDecodeError` internally and return a refusal, never raise. |
| **QA-E06-L1-002 (transport)** | `test_l1_002_dukascopy_transport_raise_returns_refusal[×7]` | **R-007, CT-15** | **FAIL — E6-F01** (real exception escapes the boundary). |
| **QA-E06-L1-002 (transport)** | `test_l1_002_calendar_transport_raise_returns_refusal[×7]` | **R-007, CT-15** | **FAIL — E6-F02**. |
| **QA-E06-L1-002 (port)** | `test_l1_002_ingest_over_raising_port_returns_refusal` | **R-007, CT-15** | **FAIL — E6-F03**. |
| QA-E06-L1-003 | `test_l1_003_intake_key_is_identity_bearing` | CT-15, CT-10; source-identity | PASS — every `(source, native id, revision)` triple is identity-bearing; distinct triples never collide, identical triples fingerprint identically. |
| QA-E06-L1-003 | `test_l1_003_new_revision_never_collides_and_idempotent` | CT-15, CT-10 | PASS — a new revision mints a new fp1 (never a collision); the boot-scoped monotonic diagnostic is excluded from identity. |
| QA-E06-L1-004 | `test_l1_004_foreign_money_verbatim_scaled_int` | DEC-0105; provenance | PASS — foreign money is stored verbatim as a scaled integer at the declared scale. |
| QA-E06-L1-004 | `test_l1_004_binary_float_inadmissible_on_money_path` | DEC-0105 | PASS — a binary float / bool / str / None on the money path is invalid input (int is admitted — control). |
| QA-E06-L1-005 | `test_l1_005_source_never_conflated_with_venue` | DEC-0107/0117; FM-7 | PASS — a `VenueId` offered as the intake source is a policy rejection; an equal plain string source is accepted. |
| QA-E06-L1-006 | `test_l1_006_hostile_symbol_refused_no_path_escape[×14]` | R-007, FR-017 | PASS — every adversarial symbol (traversal, NUL, reserved, overlong, shell) is refused (invalid input), never raised. *(Scope: no filesystem-path-from-input surface exists in Epic 6 — see E6-F05.)* |
| QA-E06-L1-006 | `test_l1_006_mapped_hostile_symbol_stays_opaque_data` | R-007, FR-017 | PASS — even a mapped hostile symbol is used only as opaque native-id text; the injected transport is the only I/O surface. |
| QA-E06-L1-007 | `test_l1_007_revisions_never_overwrite_prior` | CT-10 append-only; AC2/AC3 | PASS — across arbitrary revision sequences no earlier artifact is mutated; a re-intake of an earlier revision returns the original unchanged (idempotent). |

## L2 — contract conformance (every AC family) — all PASS

| Test id | Node | Req | Result |
|---|---|---|---|
| QA-E06-L2-001 | `test_l2_001_valid_response_normalizes_and_round_trips` | CT-15; AC1 | PASS — valid response → CT-10 value with required fields + separate bid/ask; to_row/from_row round-trips; a tampered row refuses. |
| QA-E06-L2-002 | `test_l2_002_idempotent_key_revision_new_artifact` | CT-15 idempotent; AC2 | PASS — duplicate is idempotent; a revision is a new fp1, never a collision; earlier evidence not merged. |
| QA-E06-L2-003 | `test_l2_003_missing_required_field_refuses[×5]` | CT-15, CT-03; AC4 | PASS — a record missing event-time / known-at / source / revision / instrument is invalid input, no CT-10 value. |
| QA-E06-L2-004 | `test_l2_004_provider_unavailable_returns_refusal_no_fabrication` | CT-15; AC5, FM-1 | PASS — unavailable/rate-limited → returned `unavailable dependency`/`transient venue failure`, no fabricated observation. |
| QA-E06-L2-005 | `test_l2_005_intake_key_tokens_required[×6]` + `_valid_triple_accepted` | CT-15 nullability | PASS — identity tokens required; null/blank refused; a present triple accepted (control). |
| QA-E06-L2-006 | `test_l2_006_foreign_evidence_stored_verbatim` | CT-15 units; AC3 | PASS — foreign timestamp keeps zone/offset/resolution; money keeps scaled int; float refused. |
| QA-E06-L2-007 | `test_l2_007_producer_value_satisfies_ct10_shape` | CT-10 producer; AC1 | PASS — distinct event/known, writer boot-epoch, non-negative sequence, closed-set world, fp1 identity. |
| QA-E06-L2-008 | `test_l2_008_bid_ask_never_merged_to_mid` | CT-15 bid/ask; AC1 | PASS — bid/ask separate, no `mid` field; a presented mid is a policy rejection. |
| QA-E06-L2-009 | `test_l2_009_agreement_corroborates_disagreement_visible` | CT-07; AC2 | PASS — agreement → `corroborates`, disagreement → `disagrees-with`; both endpoints referenced, nothing averaged. |
| QA-E06-L2-010 | `test_l2_010_revision_linked_new_artifact` | CT-15; AC3 | PASS — a later revision is a new artifact linked to the earlier via a `supersedes` edge (newer→earlier). |
| QA-E06-L2-011 | `test_l2_011_dukascopy_records_retain_source_identity_and_convert` | FR-017; AC1 | PASS — Dukascopy records retain source `dukascopy` and convert to CT-10. |
| QA-E06-L2-012 | `test_l2_012_unlicensed_window_cannot_become_governed_evidence` | FR-017; AC2 | PASS — every window records provenance + tag; unlicensed/denied/unknown → policy rejection; licensed → Ok (control). |
| QA-E06-L2-013 | `test_l2_013_malformed_dukascopy_record_refused` | R-007, FR-017; AC3 | PASS — malformed bi5 + unmappable symbol are invalid input. |
| QA-E06-L2-014 | `test_l2_014_acquired_window_partitioned_by_source_instrument_window` | FR-017; AC5 | PASS (**narrowed**) — the window is keyed by `(source, instrument, time-window)` with download-once provenance. *"Kept forever" retention is the Epic-3 store's L18 property — E6-F04.* |
| QA-E06-L2-015 | `test_l2_015_calendar_keeps_native_identity_and_revisions` | FR-018; AC1 | PASS — provider-native id kept; each revision a new artifact. |
| QA-E06-L2-016 | `test_l2_016_impact_verbatim_no_severity_no_permission` | FR-018; AC2 | PASS — impact labels verbatim; minting a severity scale + a live skip are policy rejections. |
| QA-E06-L2-017 | `test_l2_017_import_journaled_as_data_quality` | FR-018, CT-13; AC3 | PASS — read back through the real journal store: exactly one `data quality` event with the calendar-import signal. |
| QA-E06-L2-018 | `test_l2_018_no_authorized_retention_claim` | FR-018; AC5 | PASS — retention authorization refused; journal payload carries `legal_archiving_posture=open-operator-item`, no window, no permission. |

## L3 — acceptance (epic-specific behaviour + structural boundary) — all PASS

| Test id | Node | Req | Result |
|---|---|---|---|
| QA-E06-L3-001 | `test_l3_001_ingest_path_performs_no_governed_write` | DEC-0117/0119/0120; AC1 | PASS — the ingest path produces VALUES; the injected CT-10 door is touched only by an explicit `submit`, never during intake; ingest holds no store reference; a TattleStore behind a real CT-10 boundary is never touched. |
| QA-E06-L3-002 | `test_l3_002_lifecycle_ownership_refused[×3]` | Story 6.1 AC6, FM-5 | PASS — `start_scheduler`/`run_daemon`/`run_retry_loop` are policy rejections. |
| QA-E06-L3-003 | `test_l3_003_bounded_request_normalized_and_ct10_boundary_rejects_ct15` | Story 6.1 AC1 | PASS — one bounded call normalized to CT-10; the CT-10 boundary refuses a CT-15 request value (data-only participation). |
| QA-E06-L3-004 | `test_l3_004_governed_read_does_not_refetch_provider` | Story 6.3 AC1 | PASS — corpus downloaded once; a governed read of the admitted evidence makes no further provider call. |
| QA-E06-L3-005 | `test_l3_005_bulk_corpus_download_refused` | Story 6.3 AC4, FM-5 | PASS — `download_complete_corpus`, `complete_corpus=true`, and an over-max window are all policy rejections. |
| QA-E06-L3-006 | `test_l3_006_unavailable_source_refuses_and_fabricates_nothing` | Story 6.3 AC5, FM-1 | PASS — unavailable source → returned refusal, no records; checkpoint/recover/retry are policy rejections. |
| QA-E06-L3-007 | `test_l3_007_failed_refresh_journals_and_alarms` | Story 6.4 AC4, SCN-0008 | PASS — a failed refresh returns a fail-closed signal (treated-as-affected + alarm), journals a `data quality` event, and the feed refuses a live skip (no permission). |
| QA-E06-L3-007 | `test_l3_007_unknown_coverage_fails_closed` | Story 6.4 AC4 | PASS — unknown coverage also fails closed and journals `data quality`. |
| QA-E06-L3-008 | `test_l3_008_two_sources_bid_ask_separate_no_mid` | Story 6.2 AC1 | PASS — two sources keep bid/ask separate, no mid, distinct artifacts. |
| QA-E06-L3-009 | `test_l3_009_disagreement_inspectable_nothing_averaged` | Story 6.2 AC2 | PASS — disagreement stays inspectable via `disagrees-with` (both endpoints), agreement `corroborates`, nothing averaged. |

## L4 — scenario participation — all PASS

| Test id | Node | Req | Result |
|---|---|---|---|
| QA-E06-L4-001 | `test_l4_001_source_correction_preserves_original` | SCN-0002; AC2/AC3 | PASS — original + correction → two distinct fp1 artifacts joined by an append-only `supersedes` edge; the original reads back unmutated over a real CT-10 boundary. |
| QA-E06-L4-002 | `test_l4_002_news_intake_verbatim_append_only_and_fail_closed` | SCN-0008 (intake half); FR-018 | PASS — events ingested verbatim/append-only (no read-time widening at intake); a failed refresh journals `data quality` + alarms. |

---

## UNPROVEN / narrowed requirements (scope honesty, rule 5)

- **E6-F04 — L2-014 "raw originals kept forever" (Story 6.3 AC5).** The retain-forever guarantee is a **CT-11 store / L18** property owned by **Epic 3** (`COMP-QMF-DATA-STORE`), not the intake seam. Epic 6 proves the `(source, instrument, time-window)` partition identity and download-once provenance; the durable *kept-forever* marker is out of this epic's code and is recorded UNPROVEN-here.
- **E6-F05 — L1-006 raw-archive path-safety clause (Story 6.3 AC3 / L18).** The plan's "never resolves a path outside the immutable raw-archive root" clause has **no attackable surface in Epic 6**: the Dukascopy adapter never builds a filesystem path from provider input — symbols are opaque instrument-map keys / native-id text and the byte transport is injected. The nearest real surface (a hostile symbol) is tested clean (L1-006, 15 cases pass). Archive path resolution is Epic-3 store territory; recorded UNPROVEN-here (narrowed), not a defect.

## Deferred / out of scope (from PLAN Section 7 — confirmed, not defects)

- **CT-31 news-blackout window enforcement** — Epic 10 (`COMP-QMF-RISK`, FR-033), ratified-surface / defined-unwired. Only the intake-side half is Epic 6's and is green (L3-007, L4-002). No test converts CT-31 into a pass.
- **cTrader venue-as-source intake** — `COMP-CTRADER` is an *intended* provider shipping through Epic 8; not wired. Epic 6's active providers are Dukascopy + calendar-feed.
- **Legal archiving / long-term retention resolution** — an open operator item (recorded-not-resolved). The *behaviour* (no authorization claimed; per-window license-tag gate) is green (L2-012, L2-018); the legal resolution is not a code behaviour.

## Carried-forward planning notes (PLAN Section 8)

- **F-E06-001** (`calendar_feed.py` at 77.6% file line coverage, 41 missing branches) — this lane exercises the fail-closed / refusal / no-permission arms directly (L2-016/17/18, L3-007, L4-002 pass); no coverage delta was re-measured for the audit run.
- **F-E06-002** (co-location testability) — confirmed: `COMP-QMF-DATA-INGEST` is co-located in `qmf-data`, so "no package dependency on qmf-data" is proven by the behavioural proxy (no direct governed write, L3-001), not import-graph isolation.
- **F-E06-003 / F-E06-004** — the CT-31 scope note and the existing-suite suspicion; the independent lane's net-new R-007 / structural tests stand regardless.

## Exit-criteria check (T2)

1. Every L2 + L3 authored and executed. Every R-007 assertion has a property/contract test; the *modelled* refusal path is green (L2-004, L3-006), the *fault-realism raise* path is red and filed (E6-F01/02/03). Provenance-recorded (L1-004, L2-012), source-identity-fingerprinted (L1-003), and no-governed-write (L0-001, L3-001) each have a passing test. ✅ (with the R-007 raise-arm recorded as a defect, per contract).
2. Refusal / fail-closed arms exercised behaviourally; branch partials not re-measured (F-E06-001 carried forward). ✅
3. No defined-unwired contract (CT-31) or open operator item (legal retention) converted into a pass. ✅
4. Every test cites FR / CT / AC / SCN / DEC ids; no coverage % substitutes for a named-behaviour assertion. ✅
5. L6 requirements-fidelity review recorded in `L6-REVIEW.md`. ✅
