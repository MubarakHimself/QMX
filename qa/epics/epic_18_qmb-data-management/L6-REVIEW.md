# Epic 18 — QMB data management — L6 requirements-fidelity review

**Verdict: GAPS.**

The five filed findings are all genuine and well-evidenced (verified against source:
`download.py:127/150`, `download.py:307`, `download.py:369`, `download.py:523-580`,
`packages/qmf-data/src/qmf/data/ingest.py:201-217`). The plan's RQ inventory (RQ1–RQ34)
is a faithful, complete restatement of Epic 18's ACs, the epic-binding argument for
RQ-CLOCK is explicit and defensible, and the UNPROVEN/DEFERRED rows are honest.

What earns `gaps` is the other side: **four green tests certify requirements the source
does not meet**, because they observe the wrong artifact. `qmb data list` answers entirely
from a `qmb-data-coverage` envelope row that `download` mints from the *request* — and the
catalog suite reads that row back and calls it evidence. The suite found the price half of
this defect (E18-F03/F04) and green-lit the licence-tag half (RQ11, a P0 **R-011** row),
the side-coverage half (RQ18/RQ21) and the second-store half (RQ19).

Nothing was run or edited for this review; source was read as read-only evidence.

---

## 1. Wrong-expectation tests

### 1a. Green tests that assert what the implementation does, on requirements it fails

| Test | RQ / AC | What the requirement demands | What the test asserts |
|---|---|---|---|
| `test_t18_1m_window_records_provenance_and_license_tag` | RQ11 / 18.1 AC5 — **P0, R-011** | provenance + licence tag recorded "**as CT-10 source-observation metadata**" | reads them back through `list_data`, i.e. off the `qmb-data-coverage` envelope row. The persisted CT-10 observations carry **no** `license_tag` and no provenance (the same row set E18-F03 shows is envelope-only). The requirement's own artifact is never inspected. |
| `test_t18_3b_view_is_rebuildable_not_authoritative` | RQ19 / 18.3 AC2 | the catalog is a **rebuildable** DuckDB view over the Parquet rooms — "never an authoritative second store" | deletes only `replay/processed/` (the DuckDB materialisation) and rebuilds. The thing it rebuilds *from* is `scan_coverage_rows` — qmb-minted summary rows, the only record of coverage that exists. Delete those and no rebuild from the CT-10 observations is possible. The test green-lights the exact condition the AC forbids. |
| `test_t18_3d_missing_side_shown_absent` | RQ21 / 18.3 AC4 | "both requested but only one side present ⇒ the missing side shown absent, so a run needing both sides detects the shortfall **before it starts**" | seeds with `side="bid"` and queries `side="both"`. Side presence is `_expand_sides(request.side)` copied at download time (`catalog.py:138-151`), so the requirement's real counter-case — *requested `both`, provider delivered bid only* — cannot be constructed and would report `ask: PRESENT`. |
| `test_t18_1k_progress_emitted_to_injected_sink` | RQ10 / 18.1 AC5 | progress carries "percent, date-reached, **ETA**" | asserts `percent`, `date_reached_ns`, `completed_batches`. `download.py:369` hard-codes `eta_ns=None` on every sample. The ETA clause is dropped with no UNPROVEN row — a rule-5 silent narrowing that hides a live in-scope defect. |

### 1b. Banned-shape / unfalsifiable assertions (green, requirement not actually pinned)

| Test | Shape | Effect |
|---|---|---|
| `test_t18_p4_license_gate_is_total_and_fails_closed` | oracle-from-implementation (rule 2: "calling a function against its own lookup table"). `resolved = resolve_license_tag(tag)` is both the expectation *and* the policy tag (`VenueLicensePolicy(..., resolved, ...)`), so policy and window tag can never disagree. | A taxonomy drift where `"junk"` resolved to a granting tag would still pass. RQ14's ratified four-state interface (`redistribution-ok / internal-only / denied / unknown`) is never pinned against the ratified list — the hypothesis strategy samples the enum from itself. No policy-tag ≠ window-tag case exists. |
| `test_t18_5c_always_open_calendar_type` | `assert cal.always_open is True` — a module's self-declared flag as proof of behaviour (rule 2). | Contributes nothing; the behavioural sibling `test_t18_5c_always_open_every_interior_absence_is_a_gap` carries RQ30 alone. |
| `test_t18_1d_port_surface_and_fetch_is_called` / `..._dukascopy_adapter_one_is_a_provider_adapter` | `PROVIDER_ADAPTER_METHODS == (...)` plus `hasattr` — self-declared constant + presence. | The fetch half is real (test-owned recorder, good). `earliest_available`, batch `count`, and `rate-limit` — all four named in 18.1 AC2 — are never observed doing anything. |
| `test_t18_p3_float_price_crosses_as_exact_integer` | early `return` on the refusal arm; asserts only `isinstance(money.verbatim, int)`. | Proves "no float leak" but never checks the converted **value**, so a wrong-but-integer conversion across the AD-22 boundary passes. |
| `test_t18_0a_no_ambient_system_clock_read` | assertion broader than the requirement: bans *any* attribute named `now/utcnow/today/perf_counter/monotonic/process_time`. | The finding it produced is real, but a DEC-0106-compliant implementation calling `injected_clock.now()` would also fail this gate. The assertion is not a faithful statement of "no component below the composition root reads the **system** clock". |
| `test_t18_p1_download_threads_injected_clock_FIND001` | guesses three injection keys (`now`, `clock`, `now_ns`) that no ratified authority defines. | The defect is real and structurally verified (`parse_download_request` calls `resolve_end_ns(...)` with no `now=`), but the test asserts an invented interface rather than the requirement. |

### 1c. Suite-wide scope narrowing, under-recorded (rule 5)

Every `verify` and `gap-check` test drives the SUT with **test-injected `ticks` / `rows`
passed through the request mapping**. `verify.py:536` short-circuits the archive read
whenever `ticks` is present, and `gap_check.py:560` does the same for `rows`. So the AC
precondition "**Given a window in the rooms**" (18.4 AC1) and "computes
expected-bars-minus-present-bars" over the rooms (18.5 AC1) are never exercised on any of
RQ23–RQ32. RESULTS.md carries a prose caveat for RQ23 only; there is no UNPROVEN row for
it and nothing at all for gap-check.

---

## 2. Missed requirements (clause-level)

RQ-level coverage is complete — every AC is represented in the PLAN's RQ table. These are
clauses *inside* covered RQs that no test asserts and no UNPROVEN row records:

1. **18.1 AC5 — ETA.** `eta_ns` is `None` on every emitted sample. Untested, unrecorded;
   this is a live defect the suite should have filed.
2. **18.1 AC5 — "provenance plus a licence tag **as CT-10 source-observation metadata**".**
   The observation half is untested and violated; the tag lives only on the coverage row.
3. **18.1 AC2 — "drawn from a Book/BMS config fragment".** Only the flags/dict form is
   tested. No UNPROVEN row.
4. **18.1 AC2 — `resolution` and `side ∈ {bid, ask, both}` validation.** `resolution` is
   never asserted through `parse_download_request`; no test that an invalid side refuses.
5. **18.1 AC2 — port members `earliest_available`, batch `count`, `rate-limit`.** Presence
   only; no behaviour, and no test that the rate limit is honoured.
6. **18.1 AC1 — "carries only parsing, transport, and adapter-selection logic (B-1)".**
   No test. `download` additionally does intake keying, ledger file IO, and coverage-row
   minting.
7. **18.1 AC3 — "retained forever".** Deferred in RESULTS prose but absent from
   findings.csv; rule 6 wants a row.
8. **18.1 AC4 — "already-present observations **skipped**".** The tests compare
   fingerprint *sets*; the raw archive is content-addressed (`append_store.append_raw`
   → `admit` on fp1), so no-duplication is structurally guaranteed by the store. The
   "download skipped it" half is observable via `DownloadReceipt.idempotent` and is never
   asserted. (Minor — the required outcome is proven.)
9. **18.2 AC2 — the four ratified licence states as an explicit interface.** Never pinned
   against the ratified list (see 1b).
10. **18.3 AC1 — observation/bar count, provenance, revision values.** Type-only /
    not-None assertions. `observation_count` is `len(fetched)` copied at download time and
    never reconciled against the rooms.
11. **18.4 AC1 / 18.5 AC1 — the rooms-read path** for verify and gap-check (see 1c).

---

## 3. findings.csv — per-row adjudication

| Row | RQ | Verdict | Basis |
|---|---|---|---|
| **E18-F01** | RQ-CLOCK | **genuine violation** | `download.py:127` reads `datetime.now(timezone.utc)`. DEC-0106 is ratified and binding: *"No component below the composition root reads the system clock"* (`docs/architecture/overview.md:50`). Two caveats: the assertion is broader than the requirement (1b), and the cited **`AR-16` does not exist anywhere in this worktree** — the finding stands on DEC-0106 alone. |
| **E18-F02** | RQ-CLOCK; RQ2 | **genuine violation** | Verified: `resolve_end_ns` takes `now=` (`download.py:124`), `parse_download_request` calls it without one (`download.py:150`). No injection path exists. Test shape is an invented-interface guess (1b), but the structural defect is real. |
| **E18-F03** | RQ5/6/7 | **genuine violation (CRITICAL, correctly rated)** | Verified at the seam: `IntakeReceipt` carries `quote: TickQuote \| None` and `tick: TickObservation \| None` alongside `observation` (`ingest.py:201-217`); `download.py:307` submits `receipt.value.observation` only. `SourceObservation.foreign_money` is populated from `record.foreign_money`, which the download path never sets. 18.1 AC3 requires prices "written as CT-10 bitemporal source observations". No bid/ask reaches the archive. |
| **E18-F04** | RQ6; RQ7 | **genuine violation — duplicate of E18-F03** | Same root, same code path, different level (L3 shape vs L2 behaviour). Legitimate as a second observer, but it inflates the count: 5 rows, 3 defects. RESULTS.md says so plainly, to its credit. |
| **E18-F05** | RQ1 | **genuine violation (arguable, LOW correctly rated)** | `.qmb_intake_keys.jsonl` is real (`download.py:523-580`, via `qmb.orchestrator.paths`). Whether an intake-key ledger is a "second data layer" under B-11 is a judgment call, and LOW is the right band. Note the asymmetry: the author flagged this side-channel and missed the **coverage-envelope layer** the whole catalog is built on (§4). |
| **E18-U01** | RQ12 | **UNPROVEN, correctly recorded** | Run-loop provider-fetch rejection is Epic 14's section of epics.md. Data half proven green. Epic-binding call is right. |
| **E18-U02** | RQ17 | **UNPROVEN, correctly recorded** | The citing artifact's CT-32/ledger lineage is Epics 14/19. Gate side (edge produced, nothing written) genuinely proven — `entitlement_lineage_edge` takes no store. |
| **E18-U03** | RQ26; RQ32 | **UNPROVEN, correctly recorded** | Synthetic-fill content is Epic 23 / GAP-0048. Refuse-to-fill seams proven, and the absence-of-effect is observed through the store, not a flag. |
| **E18-U04** | RQ10 | **UNPROVEN, correctly recorded — but it defers the wrong half** | The real supervising-agent channel is fairly Epic 15/16's. But the half that *is* Epic 18's and *is* broken — `eta_ns=None` on every sample — is neither tested nor recorded. The row's existence makes RQ10 look scoped when a clause is silently dropped. |
| **E18-U05** | PLAN-INTEGRITY | **UNPROVEN, correctly recorded (verified true)** | Independently confirmed: `_bmad-output/test-artifacts/` does not exist; only `planning-artifacts` is present. Recording it rather than working around it was the right call. |

**Tally: 5 genuine violations (3 distinct defects), 0 wrong-expectation findings, 5
UNPROVEN correctly recorded.** No filed finding is spurious. Empty-findings.csv is not at
issue; the problem is what is *missing* from it.

---

## 4. The single most important gap

**`qmb data list` answers from a qmb-authored `qmb-data-coverage` envelope row minted from
the download *request*, never from the CT-10 observations in the rooms — and four green
tests read that row back and call it evidence.**

The mechanism, verified end to end:

- `download` calls `persist_coverage_windows(...)` with `side` from the request,
  `observation_count = len(fetched.value)`, plus `license_tag`, `revision`, `provenance`
  (`download.py:346-360`).
- `persist_coverage_windows` expands `side="both"` into a `bid` row and an `ask` row,
  stamps `status: PRESENT` on each, and appends them into the Parquet raw archive
  (`catalog.py:138-164`).
- `list_data` reads back **only** rows whose `kind == COVERAGE_KIND` (`catalog.py:168-189`,
  `catalog.py:307-334`). It never reads, counts, or inspects a single CT-10 observation.

So the catalog's entire answer — coverage window, per-side presence, count, provenance,
licence tag, revision — is the download request round-tripping through a summary row that
qmb wrote itself. Consequences the suite certified as green:

- **RQ18**: the reported count is what the provider *returned*, not what the rooms hold.
- **RQ21**: side presence can never diverge from what the operator asked for, so the
  "detect the shortfall before the run starts" purpose is unreachable.
- **RQ19**: the coverage rows *are* the authoritative second store the AC forbids; the
  DuckDB view is a projection of them, and the rebuild test only deletes the projection.
- **RQ11 (P0, R-011)**: the licence tag rides on this row, not on the CT-10 observation
  the AC names.

This is the same defect family as E18-F03/F04 — the CT-10 source observation ends up
carrying *only* the bitemporal envelope, while everything the ACs require to be on it
(bid/ask money-path, licence tag, provenance) is diverted to qmb-authored rows. The suite
caught the price half and certified the rest. It is also the larger sibling of E18-F05: the
author filed the small qmb-authored side-channel (a JSONL dedup ledger) and missed the one
the catalog is built on.

**Consequence for the risk gates:** **R-011 cannot stand as GREEN** on the current
evidence. Its RQ11 leg (`test_t18_1m_*`, "every window carries a tag") observes the tag on
the wrong artifact. R-007 is unaffected — the refusal-path tests are honest, drive public
surfaces, observe absence-of-effect through the store, and `test_t18_1e_real_dukascopy_
adapter_translates_bad_bytes` meets the fault-realism rule.

**Recommended remediation, in order:** (1) re-derive coverage in `list_data` from the CT-10
observations and re-run RQ18/RQ19/RQ21 — expect findings; (2) add the RQ11 assertion
against the persisted observation, not the catalog — expect a finding; (3) assert
`eta_ns` on RQ10 — expect a finding; (4) exercise verify/gap-check without injected
`ticks`/`rows`, or file explicit UNPROVEN rows for the rooms-read clause; (5) pin the
licence taxonomy against the ratified four states instead of sampling the enum from itself.
