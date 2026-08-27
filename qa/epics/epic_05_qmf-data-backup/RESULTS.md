# Results — Epic 5: qmf-data backup, restore & verify (FR-014 / CT-14, CT-26)

**Run:** `uv run --with hypothesis pytest qa/tests/epic_05 -q` from the worktree root.
**Outcome:** **72 tests — 69 passed, 2 failed (defect findings), 1 skipped (UNPROVEN on this host).**
Property tests use hypothesis (L1/L2); integration uses the real Parquet/DuckDB/SQLite/JSONL
store engines behind their contracts (L4); L5 runs the SCN-0004 chain.

**Package under test:** the backup surface inside `packages/qmf-data` — `src/qmf/data/backup.py`
(CT-14 / COMP-QMF-DATA-BACKUP), `src/qmf/data/store/backup_input.py` (CT-26 / COMP-QMF-DATA-STORE),
`src/qmf/data/verify.py` (Story 5.3 verify + migration), `src/qmf/data/cycle.py` (Story 5.4 nightly
cycle). Source is read-only evidence; a red test is a FINDING, never a licence to edit source.

> **Plan-vs-implementation note.** PLAN Section 4 was authored against `backup.py` + `backup_input.py`
> only; the implementation ALSO ships `verify.py` (Story 5.3 `OffMachineVerify`, `migrate_evidence`,
> `refuse_snapshot_alone_claim`) and `cycle.py` (Story 5.4 `OffMachineCycle`, `refuse_schedule_ownership`,
> `refuse_numeric_rpo_rto`). The suite tests the real surface: every Story-5.3/5.4 requirement has an
> executable test against these modules, not against absent functions.

---

## Headline findings

| ID | Severity | Requirement | One line |
|---|---|---|---|
| **E5-F01** | medium | 5.1 AC4 / R-007 | `OffMachineBackup.copy_export` **raises `ValueError` across the CT-14 boundary** when remapping a miswired-adapter refusal that carries a `reason` context key (backup.py:299-308) — a boundary leak, not a returned `storage failure`. |
| **E5-F02** | medium | 5.2 AC1 / R-007 | `OffMachineRestore.restore_copy` has the **identical remap defect** on the GET path (backup.py:401-410). |
| E5-F03 | medium | 5.2 AC4 / R-EVIDENCE | Symlink-safe-write clause (5.2-P4 (ii)) **UNPROVEN** on this host — `os.symlink` needs a privilege not held (WinError 1314); the interior-subdir redirect case is unverified (see Scope honesty). |
| E5-F04..F08 | low | 5.1 AC5 / 5.3 AC4 / 5.4 AC2/AC4 | Blocked-spec **UNPROVEN** rows — node/ops numeric targets, crypto strength, object-key layout, schedule execution, rehearsal cadence. The *behaviours* around them are all green. |

### E5-F01 / E5-F02 — the CT-14 remap boundary leak (the real defect)

Both `copy_export` (put) and `restore_copy` (get) contain a **defensive** branch that anticipates a
miswired `ObjectStorage` adapter returning a refusal whose category is not `storage failure`, and tries
to **normalise it** to a `storage failure`:

```python
remapped: dict[str, object] = dict(put.context)   # or dict(fetched.context)
remapped["signal"] = "storage-refused"
remapped["adapter_category"] = put.category.value
remapped["copy_version"] = copy_version
return _storage_failure("object storage refused ...", retryable=..., context=remapped)
```

`_storage_failure` calls `qmf.core.unpersistable(reason, context=remapped)`. But **every** qmf refusal
builder (`policy_rejection`, `invalid_input`, `unpersistable`) populates `context["reason"]`, and
`unpersistable` **rejects a `reason` key inside `context`** (it is reserved, set from the `reason`
argument). So when the adapter's refusal carries a `reason` key — which it always does if built with the
standard helpers — the remap raises `ValueError` **uncaught, across the CT-14 boundary**. That is exactly
the loud, unhandled crash that AC4 / R-007 forbid ("a `storage failure` typed refusal, never raised across
the boundary"). A *conformant* adapter (category already `storage failure`) returns before the remap and
never triggers it — so all other fault-matrix cases pass. Falsifiability confirmed: the tests fail today
and would pass if the remap dropped/renamed the inherited `reason` key before rebuilding the refusal.

---

## Per-test results

Verdict key: **P** pass · **F** fail (finding) · **U** UNPROVEN/skipped.

### L0 — static / documentation gates (`test_l0_static_gates.py`)
| Test | Req | V | Meaning |
|---|---|---|---|
| surface_files_exist | — | P | the four backup-surface modules exist (gate is not vacuous) |
| g1_only_qmf_core_and_own_seam | DEC-0120 | P | surface imports only `qmf.core` + its own `qmf.data.*` seam |
| g1_no_provider_or_crypto_sdk_baked_in | AC5, DEC-0045 | P | no object-storage/crypto SDK imported — target stays external/replaceable |
| g2_no_credential_or_key_literal | AC5, DEC-0136 | P | no credential/key literal embedded in the surface source |
| g3_no_scheduler_or_runtime | FM-6, DEC-0008 | P | no scheduler/thread/cron/event-loop runtime in the surface |

### Story 5.1 — CT-26 input + CT-14 copy (`test_story_51_input_and_copy.py`)
| Test | Req | V | Meaning |
|---|---|---|---|
| 5_1_u1_ct26_read_never_mutates_source | AC1 | P | source fingerprint set is byte-identical before/after a backup read |
| 5_1_u2_every_room_role_presentable | AC1 | P | all seven room-roles (incl. registry) present through CT-26 |
| 5_1_u3_backups_are_distinct_versioned_artifacts | AC2 | P | two backups → distinct monotonic ordinals; both objects persist |
| 5_1_u4_payload_is_cipher_output_not_plaintext | AC2/AC5 | P | payload is cipher OUTPUT; store plaintext never crosses as payload |
| 5_1_u5_cross_world_ct26_read_refused | AC3 (P0-7) | P | cross-world CT-26 read → policy rejection |
| 5_1_u6_simulated_governed_evidence_refused | AC3 (P0-7) | P | world=simulated store/read → policy rejection |
| 5_1_u7_unreachable_bucket_is_storage_failure | AC4 | P | unreachable bucket → returned storage failure, no completion |
| 5_1_u8_rejected_and_corrupt_are_storage_failure | AC4 | P | rejected upload + empty (corrupt) ciphertext → storage failure; nothing stored |
| **5_1_u8_wrong_adapter_category_remapped_to_storage_failure** | **AC4 / R-007** | **F** | **E5-F01: remap RAISES ValueError across the boundary instead of returning storage failure** |
| 5_1_u9_encryption_required_pointer_no_provider | AC5 | P | encryption-required pointer carried; no provider/bucket/credential field |
| 5_1_u10_no_credential_in_evidence | AC5 | P | injected key never in receipt / fp1 / ack |
| 5_1_p1_int64_timestamps_round_trip_verbatim | AC1/AC5 | P | property: arbitrary int64 ns restores bit-for-bit, stays `int` |
| 5_1_p2_no_backup_mutates_only_copy | AC2 | P | property: source fingerprint set invariant under any number of backups |
| 5_1_p3_cross_world_backup_read_refused_every_role | AC3 (P0-7) | P | property: cross-world CT-26 read refuses at EVERY room-role |
| 5_1_p4_transfer_fault_matrix_all_storage_failure | AC4 / R-007 | P | property: unreachable/OSError/timeout/rejected/corrupt → returned storage failure, nothing escapes |
| 5_1_p4_ct26_store_fault_matrix_all_storage_failure | AC4 / R-007 | P | locked/corrupt engine (real StoreEngineError) → storage failure, retryability preserved |
| 5_1_p5_no_credential_in_arbitrary_artifacts | AC5 | P | property: no secret in receipt/fp1 over arbitrary cipher keys |
| 5_1_c1_ct26_round_trip_semantic_equality | AC1 | P | CT-26 export {fmt,world,role,records} + full public round-trip identical |
| 5_1_c2_ct26_boundary_enums_and_nullability | AC1/AC3/AC4 | P | for_world required (invalid input); role enum; governed refusals bounded |
| 5_1_c3_ct14_round_trip_over_world_version_payload | AC2 | P | CT-14 copy {world,copy_version,payload} restores byte/fp identical |
| 5_1_c4_ct14_world_enum_version_and_refusal_categories | AC2/AC3/AC4 | P | simulated reserved; monotonic ordinal; no governed refusal in the 4 out-of-set categories |

### Story 5.2 — restore + seal + world isolation (`test_story_52_restore_seal_world.py`)
| Test | Req | V | Meaning |
|---|---|---|---|
| 5_2_u1_restore_targets_replacement_not_source | AC1 | P | restore lands in a distinct root; source unchanged; version intact |
| 5_2_u1_in_place_restore_refused | AC1 | P | into resolving to the source root → policy rejection (refuse-in-place) |
| 5_2_u2_sealed_read_on_restored_data_refused_like_live | AC2 (P0-6) | P | sealed restored read → policy rejection, identical to live; non-sealed returns real rows |
| 5_2_u3_cross_world_restore_read_refused | AC3 (P0-7) | P | cross-world restore → policy rejection |
| 5_2_u4_simulated_restore_refused | AC3 (P0-7) | P | restore into world=simulated → policy rejection |
| 5_2_u5_discard_local_raw_refused | AC4 | P | discard-only-local-raw → policy rejection; evidence still present |
| 5_2_p1_round_trip_byte_fingerprint_identical | R-INTEGRITY | P | property: arbitrary record sets restore byte/fingerprint identical |
| 5_2_p1_corrupt_copy_refuses_no_partial_restore | R-INTEGRITY | P | corrupt/empty/truncated copy → storage failure, 0 records restored |
| 5_2_p1_fingerprint_mismatch_copy_refuses | R-INTEGRITY | P | canonical-vs-fingerprint mismatch refused at re-admission; no fabricated evidence |
| 5_2_p2_seal_parity_live_vs_restored | R-012 (P0-6) | P | property: restored seal decision MATCHES live at every position (refuse iff sealed) |
| 5_2_p2_seal_fail_closed_on_missing_position | R-012 (P0-6) | P | seal wired + no position → refused (fail-closed) at raw + restored-backup boundaries |
| 5_2_p3_cross_world_read_refused_on_restored_store | AC3 | P | property: cross-world read of restored evidence refuses at every restorable role |
| 5_2_p4_keep_raw_forever_source_untouched | R-EVIDENCE | P | raw+journal+registry source sets invariant across a full cycle + refused delete |
| **5_2_p4_symlinked_into_root_resolving_onto_source_refused** | **AC4 / R-EVIDENCE** | **U** | **E5-F03: SKIPPED — symlink privilege not held on this host; case UNPROVEN** |
| **5_2_restore_wrong_adapter_category_remapped_not_raised** | **AC4 / R-007** | **F** | **E5-F02: restore-side remap RAISES ValueError across the boundary** |

### Story 5.3 — verify primitives + migration (`test_story_53_verify_migrate.py`)
| Test | Req | V | Meaning |
|---|---|---|---|
| 5_3_u1_snapshot_alone_yields_no_claim | AC1 | P | recoverability from a snapshot alone → policy rejection |
| 5_3_u2_both_verify_primitives_run | AC1/AC4 | P | sample-restore AND full-restore rehearsal each run and return a claim |
| 5_3_u3_matching_sample_restore_confirms_recoverable | AC2 | P | a byte/fp-matching sample-restore issues a recoverability claim vs the documented path |
| 5_3_u4_corrupt_restore_no_claim | AC2 | P | corrupt restore → storage failure, never a claim |
| 5_3_u4_mismatch_restore_no_claim | AC2 | P | read-back ≠ expected → storage failure (verify-mismatch), no claim |
| 5_3_u5_migration_ordered_sequence_never_in_place | AC3 | P | preflight→backup-first→dry-run→migrate→verify; source intact; backup precedes migrate |
| 5_3_u5_migration_in_place_refused | AC3 | P | destination == source root → policy rejection |
| 5_3_u6_numeric_targets_unfilled | AC4 | P | node/ops numeric pointers null; claim carries no rpo/rto/retention/cadence field |
| 5_3_p1_verify_never_claims_on_bad_copy | R-INTEGRITY | P | property: corrupt/empty/truncated copy → storage failure, never a claim |
| 5_3_p2_migration_that_cannot_back_up_first_refuses | R-EVIDENCE | P | backup-first failure → migration refuses before any migrate write; source intact |
| 5_3_p2_successful_migration_leaves_source_and_fresh_backup | R-EVIDENCE | P | source intact + a fresh off-machine backup version exists |

### Story 5.4 — application-owned nightly cycle (`test_story_54_cycle.py`)
| Test | Req | V | Meaning |
|---|---|---|---|
| 5_4_u1_backs_up_every_room_role_per_world | AC1/AC3 | P | one cycle backs up all seven roles (incl. registry) per world; no other world leaks |
| 5_4_u2_refuses_to_own_schedule_or_numeric_targets | AC2 | P | own_schedule/start_daemon/set_rpo/set_rto + module refusals → policy rejection |
| 5_4_u3_simulated_cycle_refused_no_simulated_carried | AC3 (P0-7) | P | simulated cycle refused; a governed cycle carries no simulated copy |
| 5_4_u4_encryption_pointer_no_credential_in_report | AC4 | P | encryption pointer + cadence carried; no credential/secret in the report |
| 5_4_p1_no_schedule_or_numeric_input_accepted | AC2 | P | schedule/numeric-owning ops all refuse; run_once accepts no rpo/rto/cadence/schedule param |

### Fault-translation + tamper-isolation branches (`test_fault_branches.py`)
| Test | Req | V | Meaning |
|---|---|---|---|
| backup_cipher_raise_is_storage_failure | AC4 / R-007 | P | cipher raising on encrypt → storage failure (cipher-raised); nothing stored |
| backup_cipher_refusal_is_returned | AC4 | P | cipher returning a refusal (missing key) → surfaced storage failure; nothing stored |
| restore_storage_get_raise_is_storage_failure | AC1 / R-007 | P | storage.get raising → storage failure (storage-raised) |
| restore_cipher_decrypt_raise_is_storage_failure | AC1 / R-007 | P | cipher raising on decrypt → storage failure (cipher-raised) |
| restore_invalid_arguments_are_invalid_input | AC1 | P | malformed role/copy_version/world → invalid input |
| restore_decrypted_world_mismatch_refused | P0-7 / R-INTEGRITY | P | a copy whose decrypted world ≠ requested → policy rejection (no cross-world on restore) |
| restore_decrypted_role_mismatch_refused | R-INTEGRITY | P | a copy whose decrypted room-role ≠ requested → policy rejection |

### L4 — integration (`test_l4_integration.py`)
| Test | Req | V | Meaning |
|---|---|---|---|
| 5_1_i1_object_storage_fault_sim | R-007 | P | every put/get object-storage fault → returned storage failure |
| 5_1_i1_durability_not_inferred_from_ack | AC4 / DEC-0118 | P | a successful put ack alone yields no claim; only a verify primitive does |
| 5_2_i1_real_multi_room_round_trip_identical | R-INTEGRITY | P | real raw+journal+registry round-trip → every record byte/fp identical |
| 5_2_i1_corrupt_in_transit_no_partial_restore | R-INTEGRITY | P | corrupt-in-transit copy → storage failure, 0 records restored |
| 5_2_i2_seal_survives_real_restore | R-012 (P0-6) | P | sealed read through a real restored backup → policy rejection, identical to live |
| 5_3_i1_migration_integration_only_copy_intact | R-EVIDENCE | P | real migration keeps source intact + fresh backup; bad backup-first aborts pre-migrate |
| 5_4_i1_nightly_cycle_wiring | AC1/AC3 | P | app-driven cycle wires CT-14 copy + sample + full rehearsal; simulated refused |

### L5 — acceptance (`test_l5_acceptance.py`)
| Test | Req | V | Meaning |
|---|---|---|---|
| acc_1_scn_0004_backup_restore_migrate_chain | SCN-0004 | P | full chain: verify-only recoverability, ordered non-in-place migration, seal+world isolation on restore, verbatim timestamps, no credential in evidence |

---

## Coverage (worktree branch coverage, `coverage run --branch`)

| File | Cover | Note |
|---|---|---|
| `store/backup_input.py` | **94%** | CT-26 seam; cross-world/simulated refusal arms covered (plan baseline 95.4% line) |
| `backup.py` | **86%** | raised **above** the 80% plan floor (baseline 80%); fault/seal/cross-world/corrupt/tamper branches covered (WS-1/WS-2/WS-3) |
| `verify.py` | 65% | verify + migrate primary paths covered; residual = defensive input-normalisation arms (`_normalize_copies` variants, overlapping-root edge refusals) |
| `cycle.py` | 62% | run_once + all refusal ops covered; residual = `sample_role` resolution variants + overlapping-verify-root edges |

`backup.py` residual partials (36 miss / 29 br-part) are deep restore-writer corrupt-copy sub-arms
(`_unframe_plaintext` truncated/bad-magic variants, registry-envelope body-not-mapping, journal decode
sub-arms). The *observable* corrupt-copy behaviour (→ `storage failure`, no partial restore) is proven at
5.2-P1 / 5.3-P1; the residuals are alternate internal routes to the same refusal, not un-proven
requirements. The module is above the floor, so per PLAN exit-criterion 2 these are recorded here rather
than each filed as a finding. (Coverage measured with `--source=packages/qmf-data/src/qmf/data`; the
module-name form mis-attributes under the src-layout `pythonpath`.)

---

## Scope honesty — UNPROVEN requirements (rule 5)

Each has a `findings.csv` row (observed=UNPROVEN). None is a code defect; each is a blocked spec or an
environment limit. The *behaviours* around them are proven green.

- **E5-F03 — symlink-safe write (5.2-P4 (ii), R-EVIDENCE).** `os.symlink` raises `WinError 1314` (privilege
  not held) on this host, so no symlink fixture can be constructed; the test **skips**. What IS proven:
  the in-place guard uses `Path.resolve()`, so a restore whose `into` **root** resolves onto the source is
  refused (`test_5_2_u1_in_place_restore_refused`, same-resolved-root). What is **UNPROVEN**: a symlinked
  interior namespace subdir redirecting a leaf write **outside** the replacement root — code inspection
  shows no realpath-within-root guard on leaf writes, so this case is neither demonstrably defended nor
  breached here; residual risk on a symlink-capable host.
- **E5-F04 — numeric RPO/RTO/retention/cadence (5.1 AC5, 5.3 AC4, 5.4 AC2).** No ratified value (DEC-0118).
  The refuse-to-own + null-pointer behaviours are green (5.4-U2/P1, 5.3-U6); the numbers have nothing to
  assert against.
- **E5-F05 — encryption strength / crypto algorithm / key custody (5.1 AC5, 5.4 AC4).** Node/ops (DEC-0118,
  AR-37). Opaque-marking (payload = cipher output) + no-credential-in-evidence are green (5.1-U4/U10/P5, G2);
  cryptographic security has no ratified algorithm/key to verify against.
- **E5-F06 — object-key layout (5.1 AC5).** Node/ops (DEC-0045). No-provider-baked-in is green (G1, 5.1-U9);
  the layout has no ratified value.
- **E5-F07 — nightly schedule EXECUTION (5.4 AC2).** App/ops-owned; asserting a QMF-owned firing would
  breach the primitives-only law. Refusal-to-own + app-driven one-cycle are green (5.4-U2, 5.4-I1).
- **E5-F08 — full-restore rehearsal cadence period (5.3 AC4).** Node/ops (DEC-0118). Rehearsal-as-primitive
  + null pointer are green (5.3-U2/U6).

**Prohibited-by-plan honoured:** no test fabricates a numeric RPO/RTO/retention/cadence value; none asserts
a scheduler firing as a QMF primitive; none asserts cryptographic strength; none asserts the seal's or
room-role contract's OWN semantics (Epic 3-owned — only the restore's duty to *preserve* them is tested);
no test treats a byte-transfer ack as a recoverability claim (`5_1_i1_durability_not_inferred_from_ack`).

---

## L6 — requirements-fidelity review (mandatory probes)

Each probe asks: does the assertion bind the requirement, or what the code happens to do?

- **(a) seal-on-restore against sealed rows, evidence-derived position — not a caller `at`.** The restored
  read boundaries (`read_raw`, CT-26 `read_room`) gate the seal on the read's declared knowledge position,
  and are **fail-closed**: a wired seal + omitted position is refused (`5_2_p2_seal_fail_closed_on_missing_position`),
  so a caller can never omit the position to slip the seal. `5_2_p2_seal_parity_live_vs_restored` proves the
  restored decision **equals the live decision at every position** (refuse iff sealed), so the restore path
  never *weakens* the seal — the exact recurrence the Epic-3 L6 review warned of is guarded. **Fidelity note
  (honest):** this boundary is a *position-gate*, not a per-row filter — `read_room` returns the whole room
  when the declared position is outside the sealed window. The seal position on this CT-26 boundary is a
  caller-declared `at` (identical for live and restored), NOT an evidence-derived position; the evidence-
  derived variant (`read_raw_self_guarded`) exists only on the research-door path (Epic 3). Because the
  requirement (5.2 AC2 / FM-4) is preservation-parity ("identical to a live read"), and parity holds, this
  is not filed as an Epic-5 defect; it is recorded so the green is not hollow.
- **(b) fault matrix injects the REAL exception at the true seam.** The CT-14 object-storage port is driven
  with real `ConnectionError` / `OSError` / `TimeoutError` (a real adapter's raise types), which
  `copy_export`/`restore_copy` catch. The CT-26 store seam is driven with the engines' own normalized
  `StoreEngineError` — the documented Protocol raise type that wraps the real pyarrow/sqlite3/OSError one
  layer below — so the injected type IS the true seam type, not qmf-data's already-normalized refusal.
- **(c) round-trip asserts byte/fingerprint identity, not a shape/length check.** `exports_identical`
  compares the `(fingerprint, canonical-bytes, stream)` set record-by-record (test-owned; not the impl's
  `_exports_match`); 5.1-P1 asserts the int64 ns value bit-for-bit and `type is int`.
- **(d) symlink test asserts evidence is untouched, not a syscall.** The fixture asserts a refusal / an
  untouched sentinel — the requirement, not a syscall. UNPROVEN on this host (E5-F03); the mechanism
  (`Path.resolve()`-based in-place guard) is proven via the same-resolved-root case.
- **(e) no fabricated numeric / no app-schedule asserted as a QMF primitive.** Confirmed — see
  Prohibited-by-plan above; the four `NODE_OPS_*` pointers stay `None` and are asserted so; the cycle's
  schedule-owning entry points all refuse.

**Banned-shape audit:** effects are observed through test-owned sinks (the `MemStorage` recorder, a
re-read CT-26 export), never a returned flag alone (absence-of-partial-restore is observed by reading the
replacement store, e.g. `record_count == 0`); fakes raise real third-party types at the object-storage
seam; no test round-trips JSON through a lossy serializer; no test asserts unratified message prose (only
CT-04 `category` + machine-readable `signal`/`field` context). The one self-declared-constant assertion
(`NODE_OPS_* is None`) is corroborated by an independent observation that a real claim carries no numeric
field (`5_3_u6`), so it is not the sole proof.

---

## Exit criteria (PLAN Section 8)

1. Every AC has ≥1 passing L2/L3 assertion; every P0-6/P0-7/R-007/R-012/R-INTEGRITY/R-EVIDENCE gate has a
   passing L2 property + its L4 witness — **met** (except the two AC4/R-007 remap cases, which are the
   E5-F01/F02 findings, and the E5-F03 symlink UNPROVEN sub-clause).
2. `backup.py` raised **above** the 80% floor (86%) with its refusal/verify/migration/tamper branches
   covered; `backup_input.py` cross-world arm covered (94%) — **met**; residual partials named above.
3. No test fabricates a numeric target, asserts a scheduler firing, or asserts Epic-3-owned seal/room
   semantics — **met**.
4. L6 fidelity review recorded with no un-recorded gap; the seal-on-restore parity + fail-closed behaviour
   verified and its position-gate nature disclosed — **met**.
5. Traceability: every test cites FR/CT/AC/FM/R-gate ids — **met**.
