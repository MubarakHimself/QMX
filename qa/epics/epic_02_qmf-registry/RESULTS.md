# Verification RESULTS — Epic 2: qmf-registry (identity, lineage & promotion)

- **Run:** `uv run --with hypothesis pytest qa/tests/epic_02 -q --tb=short` (worktree root)
- **Package under test:** `packages/qmf-registry` (`qmf.registry`) — READ-ONLY evidence.
- **Totals: 54 tests authored & run — 52 PASSED, 2 FAILED (both coverage-gap findings for the unrealized FR-048/CT-33 Bot surface; see `findings.csv`).**
- Source was never edited; no assertion was tuned to match code. Two failures during
  authoring were **test-code** errors (an over-broad hash-string scan matching the
  `fp1:sha256:` format literal in docstrings; a hypothesis strategy generating
  whitespace-only object keys outside the fp1-clean domain) — both fixed in test code,
  never by weakening an assertion.

## Ship-blocking P0 triad — all GREEN

| P0 gate | Assertions | Result |
|---|---|---|
| No live money without a recorded human promotion attesting the record `fp1` | E2-L1-11, E2-L1-13, E2-L2-05, **E2-L5-01** | **PASS** |
| Distinct semantics ⇒ distinct `fp1`, no silent overwrite | E2-L1-04, E2-L1-05, E2-L2-01, E2-L4-07 | **PASS** |
| Tampered persisted records/edges do not read back valid | **E2-L4-02, E2-L4-03** | **PASS** |

---

## Per-test results

Level · Test · Requirement ids · Result. (One line per failure explains its meaning.)

### L0 — static & documentation gates (`test_l0_static.py`)
- **E2-L0-01** `..._registry_imports_only_core_and_data` — L30/AR-06, FR-008 — **PASS** (registry imports only `qmf.core`/`qmf.data`/its own siblings).
- **E2-L0-01** `..._no_library_imports_qmf_registry` — L30/AR-06 — **PASS** (default-deny: nothing imports `qmf.registry`).
- **E2-L0-02** `..._no_database_server_dependency_declared` — CT-06/CT-09 `May never` — **PASS** (no DB-server / graph-DB / duckdb dep in `pyproject`).
- **E2-L2-07** `..._no_registry_local_hashing` — CT-05, AR-14 — **PASS** (no `hashlib`/`hexdigest`/blake/md5 in the registry source; fp1 is computed only in qmf-core).

### L1 — unit — records (`test_l1_records.py`), FR-006 / P0-4
- **E2-L1-01** `..._unknown_kind_is_typed_refusal_not_raise` — FR-006, CT-06, CT-04 — **PASS**.
- **E2-L1-01** `..._undefined_body_field_is_typed_refusal` — FR-006, CT-06 (FM-1) — **PASS**.
- **E2-L1-02** `..._stable_id_equals_fp1_over_canonical_content` — FR-006, CT-06 — **PASS** (stable id derived, never minted).
- **E2-L1-03** `..._occurrence_facts_excluded_from_identity` — FR-006, CT-06, CT-05 — **PASS** (writer/sequence/created-at excluded ⇒ dedup).
- **E2-L1-04 (P0)** `..._changing_any_identity_field_changes_stable_id` — P0-4, CT-05/06 — **PASS** (kind, version, parent, body each shift the fp1).
- **E2-L1-05 (P0)** `..._true_collision_refused_and_alarmed` — P0-4, CT-06/09 (FM-6) — **PASS** (the composed `reconcile_write` decision: differing bytes under one fp1 ⇒ `policy rejection` with `alarm=True`).
- **E2-L1-06** `..._idempotent_rewrite_accepted_silently` — FR-006, CT-06 — **PASS** (byte-identical re-write ⇒ `idempotent`, one record).

### L1 — unit — lineage (`test_l1_lineage.py`), FR-007
- **E2-L1-07** `..._off_enum_edge_type_is_refused` — FR-007, CT-07 (FM-2) — **PASS**.
- **E2-L1-07** `..._ratified_set_is_exactly_fourteen` — FR-007, CT-07 — **PASS** (the 14 ratified types, closed).
- **E2-L1-08** `..._non_fp1_endpoint_is_refused` — FR-007, CT-07 (FM-2) — **PASS**.
- **E2-L1-09** `..._edge_serializes_to_one_lf_terminated_line` — FR-007, CT-07, AR-31 — **PASS** (one canonical, LF-terminated JSONL line == `canonical_bytes(fp1_identity)+\n`).
- **E2-L1-10** `..._supersedes_is_linear_second_outgoing_refused` — FR-007, CT-07 — **PASS**.
- **E2-L1-10** `..._supersedes_second_incoming_refused` — FR-007, CT-07 — **PASS** ("current" never forks).
- **E2-L1-10** `..._branches_from_allows_multi_head` — FR-007, CT-07, DEC-0144 — **PASS**.

### L1 — unit — promotion (`test_l1_promotion.py`), FR-009 / P0-5
- **E2-L1-11 (P0)** `..._no_card_does_not_promote` — P0-5, FR-009, L17 (FM-4) — **PASS** (no card ⇒ `policy rejection`, status unchanged).
- **E2-L1-12 (P0)** `..._missing_summary_is_rejected` — P0-5, FR-009, CT-06 — **PASS** (mandatory identity field).
- **E2-L1-13 (P0)** `..._reserved_kind_cannot_be_minted_via_generic_factory` — P0-5, FR-009, L17, AR-39 — **PASS** (agent-reachable generic path cannot forge the reserved card).
- **E2-L1-13 (P0)** `..._reserved_kind_cannot_be_registered_in_kind_registry` — P0-5, FR-009, L17 — **PASS**.
- **E2-L1-14 (P0)** `..._different_summary_is_a_different_card_fp1` — FR-009, CT-06, SCN-0007 — **PASS**.
- **E2-L1-15 (P0)** `..._changing_attested_template_mints_a_new_card` — FR-009, SCN-0007, DEC-0158 — **PASS**.
- **E2-L1-15 (P0)** `..._superseded_template_does_not_authorize_crossing` — FR-009, DEC-0158, AD-32 — **PASS**.
- **E2-L1-15 (P0)** `..._absent_in_force_template_is_refused_never_skipped` — FR-009, DEC-0158 — **PASS** (absent argument is a refusal, never a silent skip).
- **E2-L1-16** `..._public_ops_return_typed_refusals_never_raise` — CT-04, FM-1/2/8 — **PASS** (7 public entry points; every failure a returned CT-04 refusal in the seven categories).

> **Note on E2-L1-13's literal "human-only signer":** per DEC-0116 the promotion gate's
> workflow/UI (and thus any human-vs-agent identity check on the signer *string*) is
> explicitly platform territory outside QMF. The registry's enforceable "only a human
> promotes" law is the **reserved-kind wall** (an agent using the generic surface cannot
> mint/forge the card) plus the persist-boundary forgery refusal (E2-L4 / existing H2) and
> the gate requiring a genuine signed card — all GREEN. Asserting rejection of an
> "agent"-valued signer string was **not** authored as a failure, because it would test
> behaviour the ratified scope deliberately places outside QMF.

### L1 — unit — Bot mint gate (`test_l1_bot.py`), FR-048 / CT-33  — **2 FAILURES = FINDINGS**
- **E2-L1-17 / E2-L1-18** `..._bot_kind_both_conformance_layers_gate_exists` — FR-048, AR-64, DEC-0178 — **FAIL → E2-F01**. Meaning: no both-conformance-layers Bot-mint path exists on the qmf.registry surface; the ratified CT-33 surface is **defined-unwired / unrealized** in this package (QML authors it; the composition root mints under AD-25). Coverage gap, not a code defect.
- **E2-L1-19 / E2-L1-20 / E2-L3-09** `..._ct33_bot_definition_kind_and_cardinality_exist` — FR-048, CT-33, DEC-0176/0174 — **FAIL → E2-F02**. Meaning: no `bot-definition` kind, `strategy_family_id` cardinality rule, or footprint producer-binding rule exists to test. Coverage gap, not a code defect.

### L2 — property / invariant (`test_l2_properties.py`), derandomized seed
- **E2-L2-01 (P0)** `..._distinct_semantics_distinct_fp1` — P0-4, CT-05 — **PASS** (injective identity; equal canonical form ⇒ equal fp1, else distinct).
- **E2-L2-02 (P0)** `..._fp1_invariant_under_occurrence_and_key_order` — CT-05, AR-14 — **PASS**.
- **E2-L2-03** `..._float_in_identity_is_refused` — CT-05 — **PASS** (floats refused in identity).
- **E2-L2-04 (P0)** `..._edge_log_is_append_only_and_order_preserving` — CT-07, AR-31 — **PASS** (N appends ⇒ exactly those N, in order).
- **E2-L2-05 (P0)** `..._no_card_never_enters_live` — P0-5, L17, FR-009 — **PASS** (∀ target with no card ⇒ never live).
- **E2-L2-06** `..._one_writer_per_stream` — CT-07, AR-17 — **PASS** (a second writer is a `policy rejection`).

### L3 — contract / owner-conformance (`test_l3_contract.py`)
- **E2-L3-01** `..._ct06_record_canonical_round_trip` — CT-06 — **PASS**.
- **E2-L3-02 (P0)** `..._ct06_boundary_conditions` — CT-06 — **PASS** (unknown kind; missing required field; fp1-derived id; human-only card attesting the record fp1; format-version stamped).
- **E2-L3-03** `..._ct07_all_fourteen_types_round_trip` — CT-07 — **PASS** (all 14 types; pinned-JSONL shape; total round trip).
- **E2-L3-04** `..._ct07_boundary_and_rebuildable_index` — CT-07 — **PASS** (non-fp1 refusal; idempotent re-append; drop→rebuild reproduces the edge view/head).
- **E2-L3-05 (P0)** `..._ct09_round_trip_through_the_store_seam` — CT-09, FR-008 — **PASS** (persist through the real `qmf-registry→qmf-data` seam, read back semantically equal).
- **E2-L3-07** `..._ct04_refusals_are_the_seven_categories_returned` — CT-04 — **PASS**.
- **E2-L3-08** `..._ct05_stable_id_is_the_content_fp1_not_a_wrapper` — CT-05, DEC-0138 — **PASS** (storage key IS the record's content fp1, never a wrapping fingerprint).
- **E2-L3-09** CT-33 shape-only — **NOT RUN as a pass** → folded into **E2-F02** (defined-unwired; no realized surface). See findings.
- *E2-L3-06 (CT-09 boundary: migration / storage-failure / world-room)* — covered at the lower winning level by **E2-L4-04/05/08** (one behaviour, one level, lower wins); not duplicated at L3.

### L4 — integration (real store; restart, tamper, migration) (`test_l4_integration.py`)
- **E2-L4-01 (P0)** `..._record_survives_a_process_restart` — CT-09, FR-008 — **PASS** (reopen a fresh store handle over the same root; read back equal).
- **E2-L4-02 (P0)** `..._tampered_record_bytes_do_not_read_back_valid` — FR-008, CT-09, CT-06 — **PASS** (recomputed fp1 ≠ stored key ⇒ `storage failure`; the advisory hotspot `persistence.py` cx 26).
- **E2-L4-03 (P0)** `..._tampered_edge_endpoint_is_tamper_evident` — FR-007, CT-07, CT-09 — **PASS** (byte-edited endpoint ⇒ no witness ⇒ `storage failure`).
- **E2-L4-03 (P0)** `..._swap_to_another_valid_edge_line_is_tamper_evident` — FR-007, CT-07, CT-09 — **PASS** (stored line swapped for another *valid* edge's line ⇒ that edge has no integrity witness ⇒ `storage failure`, never served as good lineage).
- **E2-L4-04** `..._store_failure_translates_to_typed_refusal` — FR-008, FM-8, CT-04 — **PASS** (raising engine ⇒ `storage failure` value, never raised across the seam).
- **E2-L4-05** `..._cross_world_read_is_policy_rejection` — FR-008, FM-7, CT-09 — **PASS**.
- **E2-L4-05** `..._simulated_world_never_opens` — FR-008, FM-7 — **PASS** (`world = simulated` open ⇒ `policy rejection`).
- **E2-L4-06** `..._dropped_index_reproduced_by_rebuild` — FR-007, CT-07, CT-09 — **PASS** (in-memory rebuild reproduces edges + head; durable re-read reconstructs the identical view from lines).
- **E2-L4-07 (P0)** `..._idempotent_persist_yields_one_record` — FR-006, CT-09, FM-6 — **PASS**.
- **E2-L4-07 (P0)** `..._differing_bytes_same_fp1_refused_and_alarmed` — FR-006, CT-09, FM-6 — **PASS** (colliding engine ⇒ `policy rejection` + `alarm`, never overwritten).
- **E2-L4-08** `..._migration_is_staged_and_never_in_place` — CT-09, AR-25 — **PASS** (preflight→backup(real artifact)→dry-run→migrate→verify; source stays readable; records-only).

### L5 — QMF acceptance scenario (`test_l5_scenario.py`)
- **E2-L5-01 (P0)** `..._agent_cannot_promote_only_a_human_card_can` — P0-5, FR-009, SCN-0007, L17 — **PASS**. The full chain: an agent reporting any number of passed checks (and unable to forge the reserved card) cannot move research→live (status unchanged, no live capability); only a human-signed card attesting the record fp1 with plain-words summary + Book-definition fp as identity fields authorizes; a summary typo-fix mints a NEW card with a `supersedes` edge; and once superseded the prior card no longer authorizes while the current one does.

---

## Untestable / deferred requirements (recorded, not silently skipped)

1. **FR-048 / CT-33 Bot mint gate — coverage gap (E2-F01, E2-F02).** `wiring_status:
   defined-unwired`. No `bot-definition` kind or both-conformance-layers mint path exists
   in `qmf.registry` (confirmed by source grep: no `bot`/`conformance`/`strategy_family`/
   `footprint` symbol anywhere in `src/`). FR-048 is also **not a Story of Epic 2** in
   `epics.md` (Stories 2.1–2.4 cover FR-006/007/008/009 only); QML authors the declaration
   and the composition root mints under AD-25. Recorded as coverage-gap findings rather
   than manufactured with a passing fixture (which the PLAN forbids). E2-L1-17/18/19/20 and
   E2-L3-09 have no realized surface to exercise.
2. **CT-08 causality & attempt-gate (FM-3) — untestable-positive.** Schema `null` /
   GAP-0016/0017, deferred to the backtesting sitting (DEC-0121). The positive gate cannot
   be tested; SCN-0007 confirms `registry:registry_attempt_budget` stays null and passing
   agent checks never substitute for human authorization (covered inside E2-L5-01). Exits
   as **documented-deferral** (must stay unenforced) — no finding.
3. **Promotion gate workflow / UI / timing** — platform territory outside QMF (DEC-0116).
   Only the registry card, its identity fields, and the attestation/refusal law are in
   scope; all covered. See the E2-L1-13 note above.
4. **Migration across a real incompatible version bump (E2-L4-08)** — with only ratified
   format v1 live, the test proves the *staged never-in-place mechanism*, not a genuine
   N→N+1 semantic migration.

## Process findings carried from the PLAN (unchanged by this run)
- **GAP-QA-01** — the named authority files `_bmad-output/test-artifacts/test-design-qa.md`
  and `.../test-design/QMX-handoff.md` (and the whole `test-artifacts/` tree) **do not
  exist** in the worktree; the L0–L6 architecture and the 15 P0/P1 set were reconstructed
  from the ratified `docs/lenses/testing/test-strategy.md` + the lane brief.
- **GAP-QA-02** — the brief's **AR-52** citation for P0-4 does not resolve against
  `epics.md` (AR-52 there is the QMB resolved-run-config); P0-4 was bound to AR-14/AR-25 +
  CT-05/CT-06 instead.

*(GAP-QA-01/02 are process/provenance notes, not test failures; they are recorded here and
in the PLAN, and are not emitted as `findings.csv` rows.)*
