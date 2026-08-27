# Results — Epic 3: qmf-data (evidence store & journals)

- **Epic:** Epic 3 — `qmf-data` — FR-010, FR-011, FR-012, FR-013, FR-016
- **Contracts:** CT-10, CT-11, CT-12, CT-13 (owned); CT-04, CT-05, CT-25, CT-09, CT-26 (consumed)
- **Run command:** `uv run --with hypothesis pytest qa/tests/epic_03 -q --tb=short`
- **Tests:** 80 authored / **80 passed** / 0 failed / 0 errored (property tests via `hypothesis`)
- **Findings:** **0** (see `findings.csv` — header only)
- **Author stance:** Section 4 of `PLAN.md` was authored from the requirements corpus before any `packages/qmf-data/**/*.py` source was opened. Source is read-only evidence. No source was edited; no assertion was weakened to pass. The three red tests hit during authoring were all **test-setup** errors (wrong journal reader, seal-wired source blocking a backup read, record positions not matching the manifest scale) — in every case the production code behaved correctly and the test fixture was corrected, never the assertion.

> **Verdict:** every planned Epic-3 assertion — including all P0-6 / P0-7 / R-007 / R-012 property proofs — passes. The `qmf-data` implementation faithfully meets the five FRs and the CT-10/11/12/13 contracts as written. No defect finding was produced.

The 80 pytest nodes cover 72 planned plan-ids (some ids expand to parametrized cases or were split into two focused functions; no plan-id was dropped). Node counts by file: L0=2, 3.1=16, 3.2=20, 3.3=9, 3.4=12, 3.5=10, 3.6=9, L5=2.

---

## L0 — static / documentation gates

| Test id | Node | Req ids | Result |
|---|---|---|---|
| G1 | `test_g1_import_graph_only_qmf_core_and_own_seam` | FR-011, FR-016 / DEC-0120, L30 | PASS — every `qmf.data` module imports only `qmf.core` + its own `qmf.data.*` seam; no other `qmf.*` package. |
| G2 | `test_g2_no_database_server_dependency` | FR-016 / AR-30, DEC-0117 | PASS — no DB-server/graph-DB client declared; runtime deps beyond `qmf-core` are exactly Parquet + DuckDB (SQLite/JSONL are stdlib). |

## Story 3.1 — store seam over swappable engines (FR-016 / CT-11)

| Test id | Node | Req ids | Result |
|---|---|---|---|
| 3.1-U1 | `test_3_1_u1_engine_routing_and_room_roles` | FR-016 / CT-11 AC1; DEC-0117 | PASS — raw→parquet, view→duckdb, records→sqlite, journal→jsonl; seven room-roles. |
| 3.1-U2 | `test_3_1_u2_byte_identical_rewrite_is_idempotent` | CT-11 AC2 | PASS — byte-identical re-write is idempotent, same fp1. |
| 3.1-U3 | `test_3_1_u3_true_collision_refused_and_original_unchanged` | CT-11 AC2, FM-7 | PASS — presented-fp/bytes mismatch refused (`invalid input`); original bytes unchanged. |
| 3.1-U4 | `test_3_1_u4_jsonl_one_object_per_line` | CT-11 AC3 | PASS — one canonical JSON object per LF-terminated line. |
| 3.1-U5 | `test_3_1_u5_second_writer_refused` | CT-11 AC3; DEC-0113 | PASS — a second distinct WriterId is a `policy rejection`. |
| 3.1-U6 | `test_3_1_u6_engine_faults_returned_as_storage_failure[write/read/view]` | CT-11 AC4, FM-6 | PASS (×3) — each engine fault is a **returned** `storage failure`, never raised, never success. |
| 3.1-P1 | `test_3_1_p1_idempotent_iff_identical` | CT-11 AC2 | PASS — property: idempotent iff bytes identical; a mutated re-write never mutates the stored record. |
| 3.1-P2 | `test_3_1_p2_no_engine_exception_escapes` | R-007 / AC4, FM-6 | PASS — property: across the fault matrix no store-library exception escapes the seam. |
| 3.1-C1 | `test_3_1_c1_round_trip_and_receipt_shape`, `test_3_1_c1_evidence_bearing_roles_are_exactly_two` | CT-11 AC1 | PASS (×2) — round-trip; receipt enum/nullability/format-version; only raw+journal evidence-bearing. |
| 3.1-C2 | `test_3_1_c2_empty_artifact_refused`, `test_3_1_c2_read_requires_declared_world_and_missing_is_stale` | CT-11 AC1; M4, M5 | PASS (×2) — empty artifact refused; read must declare world; missing key is `stale evidence`. |
| 3.1-I1 | `test_3_1_i1_rotation_and_index_rebuild_recovers_full_stream` | CT-11 AC3 | PASS — under a small rotation the full append stream is recovered gaplessly after index rebuild (>=2 rotated files). |
| 3.1-I2 | `test_3_1_i2_registry_room_append_only_records_and_lineage` | CT-11 AC5; DEC-0117, DEC-0120 | PASS — registry records fp1-keyed per-kind, lineage append-only JSONL, never rewritten in place. |

## Story 3.2 — bitemporal source observations (FR-010 / CT-10)

| Test id | Node | Req ids | Result |
|---|---|---|---|
| 3.2-U1 | `test_3_2_u1_source_opaque_and_orthogonal_to_venue` | CT-10 AC1; DEC-0117 | PASS — `source` verbatim opaque string, not a VenueId. |
| 3.2-U2 | `test_3_2_u2_foreign_timestamp_verbatim` | CT-10 AC2; DEC-0106 | PASS — foreign timestamp kept byte-for-byte with zone/offset/resolution; separate receive Instant. |
| 3.2-U3 | `test_3_2_u3_foreign_money_verbatim_scaled_integer` | CT-10 AC2; DEC-0105 | PASS — verbatim scaled integer; float/bool/negative-scale refused. |
| 3.2-U4 | `test_3_2_u4_correction_is_distinct_artifact` | CT-10 AC3, FM-2 | PASS — correction is a distinct fp1 with `correction_of`; original unchanged. |
| 3.2-U5 | `test_3_2_u5_missing_required_field_refused[×8]`, `test_3_2_u5_incomplete_never_reaches_boundary` | CT-10 AC4, FM-1 | PASS (×9) — every missing required field → `invalid input`; incomplete value refused at the boundary. |
| 3.2-P1 | `test_3_2_p1_resolution_never_reformatted` | CT-10 AC2 | PASS — property: verbatim + resolution preserved exactly, never presented finer. |
| 3.2-P2 | `test_3_2_p2_corrections_never_overwrite_original` | CT-10 AC3, FM-2 (evidence integrity) | PASS — property: across a correction chain the original raw record is never mutated/overwritten. |
| 3.2-P3 | `test_3_2_p3_malformed_never_admitted_as_ok` | R-007 / FM-1 | PASS — property: a fuzzed observation is a typed CT-04 refusal or a fully-formed Ok, never an admitted-incomplete record. |
| 3.2-C1 | `test_3_2_c1_round_trip_full_roster`, `test_3_2_c1_identity_is_fp1_not_ordering_key`, `test_3_2_c1_tampered_row_refused` | CT-10 AC1; DEC-0108 | PASS (×3) — full roster round-trip; identity is fp1 (not the ordering key); tampered row refused. |
| 3.2-C2 | `test_3_2_c2_world_enum_and_optional_foreign_money` | CT-10 boundary | PASS — world enum enforced; foreign money optional. |

## Story 3.3 — seven room-roles per world, cross-world refusal (FR-011 / CT-11)

| Test id | Node | Req ids | Result |
|---|---|---|---|
| 3.3-U1 | `test_3_3_u1_seven_roles_instantiated_per_world` | CT-11 AC1 | PASS — live+replay each instantiate seven roles; storage separation (a live artifact is absent from replay's room). |
| 3.3-U2 | `test_3_3_u2_simulated_write_refused` | CT-11 AC1, FM-5 (**P0-7**) | PASS — `world=simulated` store request and write are `policy rejection`. |
| 3.3-U3 | `test_3_3_u3_evidence_bearing_and_rebuild_pins` | CT-11 AC2 | PASS — only raw+journal evidence-bearing; a view records engine major + calendar + tzdata; a view without pins refused. |
| 3.3-U4 | `test_3_3_u4_deletion_licensing`, `test_3_3_u4_citation_index_failure_fails_closed` | CT-11 AC3; AR-13 | PASS (×2) — evidence + cited views never deletion-licensed; only an uncited view is; a raising citation index fails closed (`unavailable dependency`). |
| 3.3-U5 | `test_3_3_u5_cross_world_read_refused` | CT-11 AC4, FM-4 (**P0-6** core) | PASS — a cross-world read is a `policy rejection`. |
| 3.3-U6 | `test_3_3_u6_series_resolves_within_partition` | CT-11 AC5; DEC-0118 | PASS — series resolves back to its `(source, instrument, window)`; a different window is a distinct artifact. |
| 3.3-P1 | `test_3_3_p1_no_deletion_path_removes_evidence_or_cited` | CT-11 AC3 (evidence integrity) | PASS — property: deletion never licensed for an evidence/lineage or cited artifact across the receipt space. |
| 3.3-P2 | `test_3_3_p2_cross_world_refused_at_every_read_path` | R-012 / **P0-6**, FM-4 | PASS — property: a cross-world read is `policy rejection` at **every** enumerated read path (raw, processed, journal, registry, research door). |

## Story 3.4 — dataset splits + the 12-month no-peek seal (FR-012 / CT-12)

| Test id | Node | Req ids | Result |
|---|---|---|---|
| 3.4-U1 | `test_3_4_u1_civil_date_boundary_refused` | CT-12 AC1; DEC-0106 | PASS — a civil-date boundary is refused; TradingDate/Instant accepted. |
| 3.4-U2 | `test_3_4_u2_missing_widths_refused` | CT-12 AC2; DEC-0131 | PASS — a manifest omitting purge or embargo width is `invalid input`. |
| 3.4-U3 | `test_3_4_u3_widths_change_fingerprint_and_id_is_derived` | CT-12 AC1/AC2 | PASS — widths enter the fp1; `split_id` is the fp1 (never minted) and re-fingerprints identically. |
| 3.4-U4 | `test_3_4_u4_straddle_refused_unless_embargo_covers` | CT-12 AC3; DEC-0131 | PASS — a boundary-straddling record refuses unless the declared embargo covers the gap. |
| 3.4-U5 | `test_3_4_u5_sealed_read_refused_never_silent_empty` | CT-12 AC4, FM-3 (**P0-6**) | PASS — a sealed-period read is `policy rejection`; a positionless read while sealed is fail-closed; an open read proceeds. |
| 3.4-U6 | `test_3_4_u6_calendar_mismatch_refused` | CT-12 AC5; DEC-0106 | PASS — a foreign calendar identity is `policy rejection`, never rescaled. |
| 3.4-U7 | `test_3_4_u7_single_final_look_journaled` | CT-12 AC6; DEC-0119 | PASS — the one final look is journaled as a `control action` subtype; a second is refused. |
| 3.4-P1 | `test_3_4_p1_sealed_read_refused_at_every_boundary` | R-012 / **P0-6** | PASS — property: for arbitrary seal boundaries a sealed position refuses at **every** ReadBoundary (raw/processed/research-door/restored-backup); an open position is admitted at all. |
| 3.4-P2 | `test_3_4_p2_seal_boundary_frozen_new_derivation_mints_new_manifest` | CT-12 AC5 | PASS — a newer tzdata mints a new manifest fp1; the frozen boundary's calendar is unchanged. |
| 3.4-P3 | `test_3_4_p3_longer_horizon_producer_refused` | CT-12 AC2; DEC-0131 | PASS — property: reuse with a longer-horizon producer refuses rather than leaks. |
| 3.4-C1 | `test_3_4_c1_manifest_contract_shape` | CT-12 AC1 | PASS — default {train, validation, sealed-test}; time-ordered non-overlapping; one pinned calendar; non-increasing segments refused. |
| 3.4-I1 | `test_3_4_i1_seal_survives_restore` | CT-12 AC4 / R-012 | PASS — after a real backup→restore into a replacement store, a sealed-period read still refuses; a non-sealed read of the restored artifact succeeds. |

## Story 3.5 — durable journals, gapless per-writer streams (FR-013 / CT-13)

| Test id | Node | Req ids | Result |
|---|---|---|---|
| 3.5-U1 | `test_3_5_u1_only_seven_event_types` | CT-13 AC1; DEC-0119, DEC-0116 | PASS — the seven types build; a type outside the set is `invalid input`. |
| 3.5-U2 | `test_3_5_u2_sequence_gap_surfaces_loss` | CT-13 AC2 | PASS — a per-(writer,boot-epoch) gap surfaces as a `storage failure` loss signal. |
| 3.5-U3 | `test_3_5_u3_second_writer_refused` | CT-13 AC2; DEC-0113 | PASS — a second writer to a held stream does not proceed. |
| 3.5-U4 | `test_3_5_u4_decision_outcome_closed_field` | CT-13 AC3; DEC-0158, DEC-0150 | PASS — a decision without its closed outcome/reference is invalid; projections select on the declared field. |
| 3.5-U5 | `test_3_5_u5_correlation_and_causality` | CT-13 AC4; DEC-0112, DEC-0114 | PASS — correlation_id excluded from fp1; causality rides typed edges by fp1, never a time/ordering key. |
| 3.5-U6 | `test_3_5_u6_unpersistable_blocks_stream` | CT-13 AC5, FM-6 | PASS — an unpersistable event is a `storage failure` that blocks the stream, retains the event, advances no sequence. |
| 3.5-P1 | `test_3_5_p1_gapless_per_writer` | CT-13 AC2 | PASS — property: contiguous per-writer streams are gapless; an interior hole surfaces loss. |
| 3.5-P2 | `test_3_5_p2_correlation_never_in_identity` | CT-13 AC4 | PASS — property: events differing only in correlation_id share one fp1. |
| 3.5-C1 | `test_3_5_c1_n_stream_journal_round_trip` | CT-13 AC1 | PASS — N one-writer streams; the two wired qmf-data types (data quality, control action) round-trip gaplessly. |
| 3.5-I1 | `test_3_5_i1_partial_multiroom_blocks_and_recovers` | CT-13 AC5 | PASS — a partial multi-room write blocks the stream; recovery replays it to a gapless reconstruction. |

## Story 3.6 — read-time entity-journal projections / logbooks (FR-013 / CT-13, CT-25)

| Test id | Node | Req ids | Result |
|---|---|---|---|
| 3.6-U1 | `test_3_6_u1_entity_journal_is_projection` | CT-25 AC1; DEC-0145 | PASS — a Book journal is a read-time projection over the recorded streams; no entity mints a stream. |
| 3.6-U2 | `test_3_6_u2_command_fingerprint_join` | CT-25 AC2; DEC-0143, DEC-0173 | PASS — venue orders/fills join the Book by command fingerprint; a leaked Book identity in a venue payload is refused. |
| 3.6-U3 | `test_3_6_u3_cross_role_refused_without_declaration`, `test_3_6_u3_role_namespaces_separate_paper_and_live` | CT-25 AC3, FM-11; DEC-0158 | PASS (×2) — cross-role aggregation without a declared read is `policy rejection`; paper never shares the live namespace. |
| 3.6-U4 | `test_3_6_u4_legacy_records_streams_map_via_one_table` | CT-25 AC4; DEC-0145 | PASS — the legacy five names resolve via the one versioned table; `veto_ledger` selects on `outcome=refused-by-door`. |
| 3.6-P1 | `test_3_6_p1_event_class_total_and_stable`, `test_3_6_p1_decay_cohort_is_the_only_other_cross_role_read` | CT-25 AC2/AC3, FM-11 | PASS (×2) — the event-class map is a total risk/venue partition; exactly two declared cross-role reads exist. |
| 3.6-C1 | `test_3_6_c1_ct25_shape_conformance_only`, `test_3_6_entity_journal_requires_selector` | CT-25 (defined-unwired) | PASS (×2) — command-fingerprint join + legacy mapping table round-trip at contract level; conflicting attribution refused. **No runtime assertion over real risk streams** (blocked, PLAN U-B). |

## L5 — acceptance scenarios

| Test id | Node | Req ids | Result |
|---|---|---|---|
| ACC-1 | `test_acc_1_scn_0002_correction_preserves_evidence` | SCN-0002 / FR-010, CT-10, CT-07, CT-11 | PASS — original + correction are two distinct fp1 artifacts joined by an append-only typed lineage edge; original preserved; the complete pair is readable. |
| ACC-2 | `test_acc_2_scn_0003_sealed_holdout_excluded_everywhere` | SCN-0003 / FR-012, CT-12, CT-13 | PASS — the manifest identifies sealed identities; every sealed-period read (raw/processed/research-door/restored-backup) is `policy rejection`; one journaled final look, second refused; evidence stays retained. |

---

## Untestable / deferred (implemented as specified in PLAN Section 8 — not gaps)

No test converts any of these into a pass; they are recorded as blocked specs, per plan.

- **U-A** — CT-08 look-ahead/causality registration gate + attempt counter (GAP-0016/0017, DEC-0121): the gate's own pass/refusal schema is GAP-open. Bitemporal ingredients are tested (3.2-*, ACC-1); the gate result is not asserted.
- **U-B** — Story 3.6 CT-25 risk-authored entity-journal **runtime** (defined-unwired): no `qmf-risk` runtime exists. Only contract-shape conformance and the venue-side join/mapping table are tested (3.6-C1/U2/U4); a runtime proof over real risk streams is blocked.
- **U-C** — numeric backup RPO/RTO/retention-depth + restore-verification cadence: no ratified values. The behaviour "seal survives restore" is tested (3.4-I1); the numeric objectives are not asserted.
- **U-D** — per-kind BarSpec aggregation arithmetic + tick-to-bar builder (DEC-0126/0130): deferred-table rows; no ratified spec. Peripheral to Epic 3's five FRs.
- **U-E** — journal retention/trim numeric thresholds (DEC-0118, post-measured-volume): the append-only + gapless invariants are tested (3.5-P1); the trim numbers are not.

## Process notes

- **Environment:** `hypothesis` is not in the synced dev group; property tests run under `uv run --with hypothesis`. Two `PLAN` authorities (`test-design-qa.md`, `QMX-handoff.md`) are absent from the worktree — the plan's Section shape / L0-L6 levels / P0/R-gate ids are reconstructed from `docs/lenses/testing/*` and the lane task; if those files are later restored, reconcile the numbering (they are authoritative over the reconstruction).
- **Weak-spot probes (PLAN Section 6):** the R-007/R-012 property tests (3.1-P2, 3.2-P3, 3.3-P2, 3.4-P1, 3.5-U6/I1) and the L4 integration (3.4-I1) drive the error/refusal branches (the partial-branch signature in `cycle.py`/`verify.py`, which are the Epic-5 backup/verify modules) through the seal, cross-world, and store-fault paths. No residual refusal-branch failure was observed.
