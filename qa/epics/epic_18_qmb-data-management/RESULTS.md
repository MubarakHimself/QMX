# Epic 18 — QMB data management — Independent verification RESULTS (audit tier T2)

Runner: `uv run --with hypothesis pytest qa/tests/epic_18 -q --tb=short`
(hypothesis is not in the synced dev group, so the property tests run under
`--with hypothesis`; everything else runs under a bare `uv run pytest`.)

**Outcome: 60 tests — 55 PASS, 5 FAIL. Every FAIL is a recorded FINDING, none is
a test-code error.** Source under `qmb/src/qmb/data/` was read as read-only
evidence; no source was edited and no assertion was softened to pass. All tests
live under `qa/`; no git ran; nothing outside `qa/` was modified.

The 5 failures collapse to **3 distinct defects** (each defect is pinned by a
static gate and a behavioural test where possible):

- **E18-F01 / E18-F02 — FIND-001 (HIGH):** `download.py:127` reads the ambient
  `datetime.now(timezone.utc)` below the composition root, and no injection path
  threads a clock into it, so the "reproducible window" (18.1-AC2) is not
  reproducible. `resolve_end_ns` *accepts* `now=` but `parse_download_request`
  never passes it. (RQ-CLOCK, RQ2.)
- **E18-F03 / E18-F04 — price-drop (CRITICAL):** `download` computes a CT-15
  `TickQuote` from bid/ask then submits only the bare `SourceObservation`
  (`foreign_money=None`) and discards the quote — **no bid/ask price is ever
  written to the raw archive.** A governed reader recovers timestamped
  observations with no prices. (RQ5, RQ6, RQ7 / AR-46, CT-01, AR-15.)
- **E18-F05 — second data layer (LOW):** `download` writes a durable
  `.qmb_intake_keys.jsonl` dedup ledger via `qmb.orchestrator.paths`, outside
  the qmf.data contracts, though the content-addressed CT-10 store already
  dedups re-admits. (RQ1 / B-11 "qmb mints no second data layer".)

---

## Per-test ledger

Status legend: **PASS** = requirement held under a falsifiable test; **FINDING**
= the requirement is what was asserted and the source failed it (recorded, not
fixed); **DEFERRED** = clause owned by another epic (seam only here).

### L0 — static / structural gates
| Test | RQ | Status | Meaning |
|---|---|---|---|
| `test_modules_present` | — | PASS | the five data modules under test are present |
| `test_t18_0a_no_ambient_system_clock_read` | RQ-CLOCK | **FINDING (E18-F01)** | AST scan finds `download.py:127 .now(` — ambient clock below the root |
| `test_t18_0b_no_module_global_mutable_state` | RQ34/NFR-02 | PASS | no module-global mutable state anywhere in `qmb/data/` |
| `test_t18_0c_no_second_persistence_engine` | RQ1 | PASS | `qmb/data/` imports no raw pyarrow/duckdb/sqlite3 engine of its own |
| `test_t18_0d_no_vendored_downloader_or_network` | RQ3 | PASS | no `http`/`urllib`/`requests`/`socket`… — no vendored downloader/network code |
| `test_t18_2d_built_wheel_bundles_zero_corpus` | RQ16 | PASS | the built `qmb` wheel bundles zero corpus bytes (gate returned 0) |
| `test_t18_2d_corpus_gate_is_falsifiable` | RQ16 | PASS | the gate refuses a wheel carrying a `.parquet` corpus, passes a clean one |

### L1 — targeted properties (hypothesis where noted)
| Test | RQ | Status | Meaning |
|---|---|---|---|
| `test_t18_p1_resolve_end_can_honor_injected_clock` | RQ-CLOCK | PASS | falsifiability anchor: the frontier helper *can* take an injected clock |
| `test_t18_p1_download_threads_injected_clock_FIND001` | RQ-CLOCK/RQ2 | **FINDING (E18-F02)** | `download` ignores an injected clock; `end` tracked the real wall clock |
| `test_t18_p2_download_idempotent` (hyp) | RQ8 | PASS | a second identical download writes zero duplicate CT-10 observations |
| `test_t18_p3_int_price_passes_through_exact` (hyp) | RQ6/RQ23 | PASS | an exact scaled int passes through the AD-22 boundary unchanged |
| `test_t18_p3_float_price_crosses_as_exact_integer` (hyp) | RQ6/RQ23 | PASS | a float crosses `provider_price_to_exact` as an exact integer, never a float leak |
| `test_t18_p3_non_numeric_price_refused` (hyp) | RQ6/RQ23 | PASS | a non-numeric provider price is refused at the named boundary (refuse arm reachable) |
| `test_t18_p4_license_gate_is_total_and_fails_closed` (hyp) | RQ14 | PASS | gate is a total function; blank⇒unknown⇒block; grant passes only with a matching policy |
| `test_t18_p5_verify_reproduces_verdict` | RQ27 | PASS | verify over the same window reproduces the same verdict (journal cursor excluded) |
| `test_t18_p6_gap_check_deterministic_and_records_version` | RQ31 | PASS | gap-check is deterministic and records the CT-02 calendar version used |

### L2 — download-once (Story 18.1)
| Test | RQ | Status | Meaning |
|---|---|---|---|
| `test_t18_1a_ct10_evidence_lands_through_qmf_data_boundary` | RQ1 | PASS | CT-10 evidence is persisted through the qmf-data store, observed by an independent read |
| `test_t18_1a_no_qmb_authored_second_data_layer_FINDING` | RQ1 | **FINDING (E18-F05)** | a qmb-authored `.qmb_intake_keys.jsonl` ledger is written outside qmf.data |
| `test_t18_1b_request_assembled_from_fields` | RQ2 | PASS | request assembled from (venue,symbols,start,end,side); explicit end honoured verbatim |
| `test_t18_1b_symbol_list_form_accepted` | RQ2 | PASS | a symbol list is accepted alongside the comma-string form |
| `test_t18_1d_port_surface_and_fetch_is_called` | RQ3 | PASS | fetch flows through the injected port (observed via a test-owned fetch recorder) |
| `test_t18_1d_dukascopy_adapter_one_is_a_provider_adapter` | RQ3 | PASS | the QMX Dukascopy adapter #1 satisfies the port and exposes every port member |
| `test_t18_1f_bid_and_ask_preserved_in_ct10_evidence_FINDING` | RQ5/RQ6/RQ7 | **FINDING (E18-F03)** | persisted CT-10 evidence carries neither bid/ask nor foreign_money — prices dropped |
| `test_t18_1i_rerun_writes_no_duplicate` | RQ8 | PASS | a re-download over the overlapping window adds no duplicate observation |
| `test_t18_1j_overwrite_appends_new_revision` | RQ9 | PASS | `--overwrite` appends a new CT-10 revision and retains the original artifact |
| `test_t18_1k_progress_emitted_to_injected_sink` | RQ10 | PASS | machine-observable progress (percent/date-reached) reaches a test-owned sink |
| `test_t18_1l_read_commands_hold_no_provider_port` | RQ12 | PASS | list/verify/gap-check take no adapter and import no ProviderAdapter — rooms only |
| `test_t18_1m_window_records_provenance_and_license_tag` | RQ11 | PASS | each ingested window records provenance + a licence tag (the 18.2 gate input) |

### L2 — licensing gate (Story 18.2)
| Test | RQ | Status | Meaning |
|---|---|---|---|
| `test_t18_2a_granting_tag_passes_with_authority` | RQ13 | PASS | a granting tag with authority passes and carries venue/symbol/tag/authority |
| `test_t18_2a_denied_unknown_absent_refuse_with_context` | RQ13 | PASS | denied/unknown/absent refuse with (venue,symbol,window)+tag as context |
| `test_t18_2a_granting_tag_without_authority_refuses` | RQ13 | PASS | a grant tag with no policy is refused — authority is never adapter-inferred |
| `test_t18_2c_unlicensed_window_ingests_and_is_catalogable` | RQ15 | PASS | an unlicensed window still ingests and is catalogable |
| `test_t18_2c_non_evidence_use_allowed_but_citation_refused` | RQ15 | PASS | infra-stress/strategy-smoke allowed; governed-evidence citation refused |

### L2 — catalog (Story 18.3)
| Test | RQ | Status | Meaning |
|---|---|---|---|
| `test_t18_3a_reports_full_coverage_fields` | RQ18 | PASS | list reports [start,end], count, provenance, tag, revision per (venue,symbol,res,side) |
| `test_t18_3b_view_is_rebuildable_not_authoritative` | RQ19 | PASS | the DuckDB view rebuilds from the Parquet rooms after deletion; non-evidence-bearing |
| `test_t18_3c_absent_window_is_not_present_value` | RQ20 | PASS | an absent window is a "not present" VALUE, never a refusal |
| `test_t18_3d_missing_side_shown_absent` | RQ21 | PASS | both requested, one present ⇒ the missing side is shown absent |
| `test_catalog_aliases_list` | RQ18 | PASS | `catalog` returns the same coverage payload as `list` |

### L2 — verify (Story 18.4)
| Test | RQ | Status | Meaning |
|---|---|---|---|
| `test_t18_4a_clean_window_passes_with_counts` | RQ23 | PASS | a clean window passes with counts; verdict is not an edge claim |
| `test_t18_4a_non_monotonic_and_missing_side_are_defects` | RQ23 | PASS | a non-monotonic timestamp / missing requested side are defects, not a silent pass |
| `test_t18_4b_blank_tolerance_leaves_guard_unarmed_reports_raw_offsets` | RQ24 | PASS | blank edge tolerance ⇒ guard un-armed, raw offsets reported, no fabricated threshold |
| `test_t18_4b_armed_tolerance_exceeded_is_a_defect` | RQ24 | PASS | an armed tolerance exceeded is an `edge_offset_beyond_tolerance` defect |
| `test_t18_4d_interior_gaps_reported_never_filled` | RQ26 | PASS | interior gaps are reported with `filled=false`; verify writes no synthetic observations |

### L2 — gap-check (Story 18.5)
| Test | RQ | Status | Meaning |
|---|---|---|---|
| `test_t18_5a_reports_gaps_and_records_calendar_version` | RQ28/RQ31 | PASS | gaps reported as (start,end,expected,present); CT-02 calendar version recorded |
| `test_t18_5b_closed_absence_is_not_a_gap_open_absence_is` | RQ29 | PASS | closed-session absence is not a gap; open-session absence is — the calendar decides |
| `test_t18_5c_always_open_every_interior_absence_is_a_gap` | RQ30 | PASS | a 24/7 always-open calendar makes every interior absence a gap |
| `test_t18_5c_always_open_calendar_type` | RQ30 | PASS | the always-open path uses the SUT's AlwaysOpenCalendar (no closure exemption) |
| `test_t18_5e_fill_request_is_policy_rejection` | RQ32 | PASS | asking gap-check to write interior fill is a policy rejection (GAP-0048) |
| `test_t18_5e_report_never_marks_fills` | RQ32 | PASS | the report never marks fills — `fills_gaps=false`, every gap `filled=false` |

### L3 — contract conformance
| Test | RQ | Status | Meaning |
|---|---|---|---|
| `test_t18_1e_provider_error_refuses_without_partial_ingest` | RQ4 | PASS | geo-block/maintenance/missing-entitlement ⇒ typed refusal; store observed empty (no partial ingest) |
| `test_t18_1e_real_dukascopy_adapter_translates_bad_bytes` | RQ4 | PASS | fault realism: the real adapter over corrupt non-LZMA bytes returns `invalid input` |
| `test_t18_1h_persisted_rows_are_ct10_shape_conformant` | RQ7 | PASS | persisted rows carry the full CT-10 bitemporal envelope + fingerprint |
| `test_t18_1h_ct10_row_carries_money_path_FINDING` | RQ6/RQ7 | **FINDING (E18-F04)** | no persisted CT-10 observation carries a `foreign_money` price |
| `test_t18_2e_passing_tag_rides_into_ct07_lineage_gate_writes_nothing` | RQ17 | PASS | a passing tag yields a CT-07 OCCURRENCE_OF entitlement edge; the gate takes no store and is pure |
| `test_t18_3e_cli_and_api_door_return_identical_catalog_payload` | RQ22 | PASS | the CLI door and Python API door return byte-identical coverage entries + view payload |
| `test_t18_4c_verify_defects_refuse` | RQ25 | PASS | float-taint / missing-side / empty-return ⇒ returned CT-04 policy refusal, verdict=fail |
| `test_t18_4e_verdict_journaled_ct13_with_correlation` | RQ27 | PASS | the verdict is journaled as CT-13 "data quality" with the correlation_id propagated |
| `test_t18_5f_unresolvable_calendar_refuses_unavailable_dependency` | RQ33 | PASS | an unresolvable calendar ⇒ `unavailable dependency`, never a silent always-open guess |
| `test_t18_6a_all_epic18_refusals_are_valid_ct04_values` | RQ34 | PASS | every refusal across 6 surfaces is a RETURNED CT-04 value (category∈7, non-null context, retryability) |

### L4 — golden lifecycle walk
| Test | RQ | Status | Meaning |
|---|---|---|---|
| `test_t18_6b_download_list_verify_gapcheck_lifecycle` | golden | PASS | download→list(tag+revision)→verify(pass)→gap-check(closure-vs-gap) composes end to end |

---

## Requirement coverage roll-up (RQ1–RQ34 + RQ-CLOCK)

| RQ | Verdict | Note |
|---|---|---|
| RQ-CLOCK | **FINDING** | E18-F01/F02 — ambient clock; window non-reproducible |
| RQ1 | PASS + **FINDING** | CT-10 persistence via boundary (pass); `.qmb_intake_keys.jsonl` second layer (E18-F05) |
| RQ2 | PASS (+FIND) | explicit end honoured; the default-to-today branch is FIND-001 |
| RQ3 | PASS | QMX-authored port; fetch flows through it; no vendored downloader |
| RQ4 | PASS | provider error ⇒ returned CT-04, no partial ingest (real adapter translation too) |
| RQ5 | **FINDING** | E18-F03 — bid/ask not persisted as CT-10 evidence |
| RQ6 | PASS (boundary) + **FINDING** | conversion boundary exact (P3); prices never reach a CT-10 write (E18-F03/F04) |
| RQ7 | PASS (shape) + **FINDING** | CT-10 envelope conformant; carries no price (E18-F04) |
| RQ8 | PASS | idempotent re-download; no duplicate observation |
| RQ9 | PASS | `--overwrite` appends a new revision, retains the original |
| RQ10 | PASS (seam) | emission+shape to an injected sink; real channel DEFERRED (E18-U04) |
| RQ11 | PASS | provenance + licence tag recorded per window |
| RQ12 | PASS (data half) | read commands hold no provider port; run-side DEFERRED (E18-U01) |
| RQ13 | PASS | value-or-typed-refusal with (venue,symbol,window)+tag context |
| RQ14 | PASS | licence taxonomy total; blank⇒unknown⇒block; never adapter-inferred |
| RQ15 | PASS | unlicensed window ingests + catalogable; non-evidence use allowed; citation refused |
| RQ16 | PASS | built wheel bundles zero corpus bytes; gate falsifiable |
| RQ17 | PASS (gate side) | CT-07 entitlement edge produced, gate writes nothing; downstream ride DEFERRED (E18-U02) |
| RQ18 | PASS | list reports the full coverage row per (venue,symbol,res,side) |
| RQ19 | PASS | rebuildable DuckDB view over Parquet rooms, non-evidence-bearing |
| RQ20 | PASS | absent window is a "not present" VALUE |
| RQ21 | PASS | missing side shown absent |
| RQ22 | PASS | CLI door == Python API door coverage payload (shipped doors; MCP out of V1) |
| RQ23 | PASS | verify checks both-present/monotonic/exact-int; typed counts+defects (on prices it can see*) |
| RQ24 | PASS | edge tolerance configurable; blank un-armed, raw offsets |
| RQ25 | PASS | verify defect ⇒ returned CT-04 refusal, never a silent pass |
| RQ26 | PASS (seam) | interior gaps reported never filled; fill CONTENT DEFERRED (E18-U03) |
| RQ27 | PASS | CT-13 data-quality journal + correlation; verify verdict deterministic |
| RQ28 | PASS | expected sessions from the CT-02 calendar; (start,end,expected,present) |
| RQ29 | PASS | closed-vs-gap decided by the calendar |
| RQ30 | PASS | 24/7 always-open ⇒ every interior absence is a gap |
| RQ31 | PASS | deterministic gap set; calendar version recorded |
| RQ32 | PASS (seam) | gap-check refuses to fill; fill CONTENT DEFERRED (E18-U03) |
| RQ33 | PASS | unresolvable calendar ⇒ `unavailable dependency` |
| RQ34 | PASS | every refusal is a valid RETURNED CT-04 value |

\* **RQ23 integration caveat:** verify's price-integrity logic is proven against
injected ticks (float-taint refused, exact ints pass). It cannot be exercised
against *real download output* because that output carries no prices (E18-F03/F04):
a downloaded window verifies "pass" only because there is no price to taint.

## Risk gates
- **R-007 (adversarial input refuses, never Ok):** GREEN. `test_t18_1e_*`,
  `test_t18_4c_*`, `test_t18_5f_*`, `test_t18_6a_*` all pass — every hostile /
  malformed input returns a CT-04 value; no silent partial ingest, no silent
  pass, no always-open guess.
- **R-011 (licence tag gates governed evidence, fails closed):** GREEN.
  `test_t18_1m_*`, `test_t18_2a_*`, `test_t18_p4_*`, `test_t18_2c_*`,
  `test_t18_2e_*` all pass — every window carries a tag; the gate passes a
  granting tag and refuses denied/unknown/**absent**; blank⇒unknown⇒block; the
  gate writes nothing.
- **FIND-001 (P0):** executed and recorded — `test_t18_0a` + `test_t18_p1_*_FIND001`
  fail as predicted (E18-F01/F02). Source not fixed.

## Deferred / scope-narrowed clauses (owned elsewhere — UNPROVEN in Epic 18)
Recorded as `E18-U0x` rows in `findings.csv` (observed=UNPROVEN/DEFERRED):
- **RQ12 run-side** → Epic 14 (run-loop policy rejection). Data half proven.
- **RQ17 downstream ride** → Epics 14/19 (entitlement into a run's CT-32/ledger
  citation). Gate side proven.
- **RQ26 / RQ32 synthetic-fill content** → Epic 23 / GAP-0048. Refuse-to-fill
  seams proven.
- **RQ10 real supervising-agent channel** → Epics 15/16. Emission+shape proven.
- **"retained forever" (RQ7)** is a retention policy owned by Epics 3/5 — Epic 18
  proves the write + idempotent retention across re-runs, not infinite retention.
- **Real FX-session calendar content (RQ28/29)** → Epic 4. Epic 18 tests the
  closed-vs-gap decision against controlled CT-02 calendar fixtures only.

## Plan-integrity finding (E18-U05, INFO)
The two named authorities `_bmad-output/test-artifacts/test-design-qa.md` and
`_bmad-output/test-artifacts/test-design/QMX-handoff.md` are absent from the
worktree (confirmed by full-tree search; PLAN §1/§7.8). The L0–L6 taxonomy, the
T2 tier scope, the R-007/R-011 gates, and FIND-001 were taken from the task
brief and reconstructed from the sibling epic_13/epic_14 PLANs. Recorded, not
worked around.

## L6 adversarial notes (the 3 CRITICAL loci)
- **download orchestration** — beyond FIND-001, the deepest leak coverage found
  is the **silent price drop** (E18-F03/F04): the branch that submits
  `receipt.value.observation` never carries the `TickQuote`/`TickObservation`,
  so bid/ask and the AD-22-converted money-path never reach evidence. The
  refusal path is honest (no partial ingest on provider error, E18-U…/T18-1e).
- **verify integrity** — the multi-arm refusal logic is honest: each defect arm
  returns a CT-04 value; the edge guard is genuinely un-armed by default (no
  fabricated `MAX_MISSING_EDGE_MINUTES`-analog). Its blind spot is upstream: it
  cannot check price integrity on real evidence that has no prices.
- **gap-check classification** — closed-vs-gap is decided by the injected CT-02
  calendar (not the venue string), the 24/7 branch takes no closure exemption,
  and an unknown calendar refuses rather than defaulting open. No inversion found.
