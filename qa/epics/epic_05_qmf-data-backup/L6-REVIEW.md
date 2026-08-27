# L6 — Requirements-Fidelity Review — Epic 5: qmf-data backup, restore & verify (FR-014 / CT-14, CT-26)

**Reviewer scope.** One question per test: *does it assert what the requirement demands, or what the
implementation happens to do?* Authorities in precedence order: `epics.md` §Epic 5 (Stories 5.1–5.4)
→ `docs/contracts/ct-14-backup-restore.yaml`, `ct-26-store-backup-input.yaml`, `ct-04-typed-refusal.yaml`,
`docs/components/qmf-data-backup.md`, `docs/components/object-storage.md`, `docs/decisions/ADR-0016`
→ the epic's own `PLAN.md`. (`_bmad-output/test-artifacts/test-design-qa.md` and `QMX-handoff.md` are
**absent from this worktree** — confirmed; the PLAN's reconstruction stands, as it did for Epic 3.)
Source read as read-only evidence only. Nothing was run or edited.

Artifacts reviewed: `PLAN.md`, `RESULTS.md`, `findings.csv` (8 data rows × 8 columns, well-formed),
and all 9 files under `qa/tests/epic_05/` (72 `def test_` functions — the count in RESULTS.md is
accurate, and every row of the per-test tables maps to a real function; no phantom tests).

---

## Verdict: **gaps**

The suite is, on the whole, unusually honest work: effects are observed through test-owned sinks
(`MemStorage.put_calls`, re-read CT-26 exports, `record_count == 0` for absence-of-effect), the
transport fakes raise **real** `ConnectionError` / `OSError` / `TimeoutError` and the CT-26 fakes raise
the engines' own `StoreEngineError` (rule 4 satisfied at the true seam), round-trips compare a
test-owned `(fingerprint, canonical, stream)` identity set rather than the implementation's
`_exports_match` (rule 3), hypothesis arms are all reachable, and no test asserts unratified message
prose. The two filed defect findings are real, falsifiable, and correctly refused rather than papered over.

It is *not* adequate, for four reasons, ranked:

1. **One requirement clause was rewritten to match the implementation** (CT-14/CT-26 boundary refusal
   categories) — the suite asserts `invalid input` as the correct answer and then trims `invalid input`
   out of the "forbidden categories" set, which is the tell.
2. **A top-authority clause of 5.1 AC1 / 5.2 AC1 is untested and unrecorded** — "never re-derived under
   a later calendar identity or tzdata version" (DEC-0106). No test varies calendar identity or tzdata;
   the requirement is scored green off a same-context round-trip. Constructible, therefore owed.
3. **Two more clauses were silently narrowed** — CT-26's "unlimited reader under one-writer-per-stream"
   (DEC-0113, named verbatim in PLAN 5.1-U1) and the migration **dry-run** stage (5.3 AC3), the latter
   observed only through the implementation's own report compared with the implementation's own constant.
4. **The PLAN's own mandatory L6 probe (a)** — seal position *derived from resolved evidence, not a
   caller-declared `at`* — failed, and the PLAN says a failed probe is a **FINDING**. The author
   disclosed the miss in RESULTS §L6 prose (creditable) but filed no `findings.csv` UNPROVEN row, which
   rules 5 and 6 require.

None of these overturns a filed finding, and none is a fabricated green in the crude sense. They are
narrowings that were owed a row and did not get one.

---

## 1. Wrong-expectation tests

### W-1 (primary) — CT-14 / CT-26 boundary refusal categories rewritten to fit the code

**Tests:** `test_restore_invalid_arguments_are_invalid_input` (test_fault_branches.py:88),
`test_5_1_c2_ct26_boundary_enums_and_nullability` (:427),
`test_5_1_c4_ct14_world_enum_version_and_refusal_categories` (:469).
**Requirement:** CT-14 `enums.boundary_refusal_categories: [storage failure, policy rejection]  # subset
of the seven (DEC-0109)`; CT-26 identical. PLAN 5.1-C4 restates it: *"`boundary_refusal_categories`
**exactly** {storage failure, policy rejection} — **not** the other five categories."*

What the tests do instead:

- `test_restore_invalid_arguments_are_invalid_input` asserts that a malformed `source_room_role`,
  `copy_version=0`, or `world="mars"` returns **`invalid input`** — a category the ratified CT-14
  boundary set does not contain. The test enshrines the implementation's choice as the requirement.
- `test_5_1_c2` does the same on CT-26 (`for_world=None` → `invalid input`, bad role → `invalid input`),
  then applies the bounded-category assertion **only** to the cross-world refusal.
- `test_5_1_c4` was supposed to prove "not the other five". The authored set is
  `forbidden = {"unsupported capability", "unavailable dependency", "stale evidence", "transient venue
  failure"}` — **four**, with `invalid input` removed. The one category the implementation actually
  emits outside the ratified set is precisely the one dropped from the check.

This is the single clearest instance in the suite of asserting what the code does rather than what the
contract demands. The correct dispositions were either (i) a `findings.csv` defect row — *CT-14/CT-26
return `invalid input`, outside the ratified two-category boundary set* — or (ii) an explicit UNPROVEN /
reinterpretation row arguing that CT-04 caller-error refusals sit outside `boundary_refusal_categories`.
Silently shrinking the forbidden set is neither. **Owed: a row.**

### W-2 — 5.3 AC2 "documented restore path" is the conclusion passed in as an argument

**Test:** `test_5_3_u3_matching_sample_restore_confirms_recoverable` (:106).
`verify.sample_restore(..., source_store=src)` is called, and the test then asserts
`claim.documented_restore_path == str(src.root.resolve())`. The claim echoes an input the test supplied
(banned shape: *passing the conclusion in as an argument*, plus *the implementation's own report as the
only observer*). The load-bearing half of AC2 — that a claim is impossible without a byte/fp match — **is**
proven independently by `test_5_3_u4_mismatch_restore_no_claim` and `5_3_p1`, so the requirement is not
hollow overall; this specific assertion is decorative and should not be counted as evidence.

### W-3 — 5.3 AC3 migration order proven against the implementation's own constant

**Test:** `test_5_3_u5_migration_ordered_sequence_never_in_place` (:167).
`assert report.stages_completed == MIGRATION_SEQUENCE` compares the implementation's report to the
implementation's own module constant — tautological for the ordering clause (banned shapes: *self-declared
constants as proof of behaviour*, *the implementation's own trace as the only observer*). AC3 names the
literal order (preflight → backup-first → dry-run → migrate → verify); the assertion should be against
that literal five-tuple, not an imported symbol.

What *is* independently observed: backup-first genuinely precedes any destination write
(`test_5_3_p2_migration_that_cannot_back_up_first_refuses` shows an unreachable bucket leaves
`dest.record_count == 0`), the source is byte-invariant, and in-place is refused. What is **not**
observed anywhere: that a **dry-run** happened at all. See M-3.

### W-4 (minor) — self-declared constants standing in for behaviour

`assert ENCRYPTION_REQUIRED is True` (5.1-U9), `assert NODE_OPS_* is None` (5.3-U6),
`set(CYCLE_ROOM_ROLES) == set(RoomRole)` (5.4-P1) are module-constant assertions. Each is corroborated by
an independent observation elsewhere (receipt pointer on a produced artifact; a real claim carrying no
numeric field; the storage sink holding all seven role keys), and RESULTS.md discloses the pattern. Noted,
not held against the suite. `report.cadence == BACKUP_CADENCE == "nightly"` is fine — "nightly" is a
ratified value (`docs/components/object-storage.md:47`, `qmf-data-backup.md:64`), so the literal binds.

### Not wrong, but flagged: L4 largely re-runs L2/L1

`5_1_i1_object_storage_fault_sim` ≈ `5_1_p4_transfer_fault_matrix`; `5_2_i1_corrupt_in_transit` ≈
`5_2_p1_corrupt_copy_refuses`; `5_2_i2_seal_survives_real_restore` ≈ `5_2_u2`. The "integration" layer uses
the *same* in-memory doubles as the unit layer (the store engines are real in both), so it adds no
independent observation. Against the system plan's *one behaviour, one level — lower level wins*, these are
duplicates at a higher label rather than integration witnesses. No fidelity error; a coverage-inflation
caution.

---

## 2. Missed requirements (Epic 5 clauses in `epics.md` that no test covers)

| # | Clause (verbatim source) | Owner | Status |
|---|---|---|---|
| **M-1** | 5.1 AC1 / 5.2 AC1: "int64 UTC nanosecond timestamps pass through verbatim, **never re-derived under a later calendar identity or tzdata version** (DEC-0106)" — also a CT-14 and CT-26 invariant | Epic 5 | **Untested, unrecorded.** `5_1_p1` and the L5 chain prove value+`type is int` survive a round-trip in **one** calendar context. No test constructs the counter-case the clause names: a backup taken under one `CalendarIdentity` (version/tzdata) restored or read under a **later** one. The helpers already support it — `H.cal(version, tzdata)` is parameterised and `H.make_store(..., seal=...)` accepts a seal carrying a calendar identity — so the case is **constructible**, not blocked. PLAN 5.1-P1 promised this clause verbatim. |
| **M-2** | 5.1 AC1: "read as an **unlimited reader under one-writer-per-stream**" (DEC-0113; CT-26 invariant) | Epic 5 (mechanism Epic 3) | **Untested, unrecorded.** PLAN 5.1-U1 named it; the authored `5_1_u1` proves only non-mutation. Nothing shows a backup read is unlimited/non-blocking or that it does not contend with the single writer. |
| **M-3** | 5.3 AC3: the **dry-run** stage of "preflight → backup-first → dry-run → migrate → verify" | Epic 5 | **Not independently observed.** Only the implementation's own `stages_completed` names it (W-3). No sink shows a dry-run write that was discarded, or a dry-run that aborted a bad migration. |
| **M-4** | 5.4 AC2: "a caller asks **COMP-QMF-DATA or COMP-QMF-DATA-BACKUP**" to own the schedule / numeric RPO-RTO | Epic 5 | **Narrowed.** Only `cycle.py` (`OffMachineCycle.own_schedule/start_daemon/set_*`, `refuse_schedule_ownership`, `refuse_numeric_rpo_rto`) is exercised. No test asks `OffMachineBackup` / the qmf-data component surface, which AC2 names. |
| **M-5** | 5.2 AC2 via PLAN L6 probe (a): seal position "**derived from the resolved evidence, never a caller-declared position**" (PLAN 5.2-P2) | Epic 5 plan-level | **Failed and disclosed in prose, but no row.** RESULTS §L6(a) states honestly that `read_raw`/`read_room` gate on a caller-declared `at`, and that `read_raw_self_guarded` (the evidence-derived variant) is the Epic-3 research-door path. The parity + fail-closed argument is sound and I accept the *no-Epic-5-defect* conclusion — but the PLAN says a failed probe is a FINDING, and rules 5/6 require an UNPROVEN row. |
| **M-6** | CT-26 invariant: "Store-boundary signatures are **stdlib-typed** so the store engine stays swappable" | Epic 5 (5.1 AC1 authority chain) | **Untested.** A natural L0 gate (the CT-26 seam takes engines/paths, not engine objects) that the G1/G2/G3 set does not include. |
| **M-7** | CT-14 `nullability`: "contract_format_version and world are required; null prohibited in identity content" | Epic 5 | **Untested on CT-14.** Asserted on CT-26 only (`5_1_c2`, and there via the disputed `invalid input` — see W-1). `5_1_c4` checks the world enum, the ordinal and the category set, not nullability. |
| **M-8** | 5.4 AC1 topology: "the trading-node VPS records and syncs down, the workstation holds the working archive, the bucket catches nightly copies" | Epic 5 | **Not code-testable** (an ops arrangement, CT-14 "Topology" invariant). Legitimately unprovable — but it is the one blocked clause with **no** UNPROVEN row (E5-F04..F08 cover the numerics, crypto, key layout, schedule execution, and rehearsal cadence; topology is not among them). |

M-1 through M-4 are behaviour gaps; M-5 through M-8 are recording gaps.

---

## 3. Per-`findings.csv` row verdict

| Row | Requirement | Verdict | Reasoning |
|---|---|---|---|
| **E5-F01** | FR-014 / CT-14 / 5.1 AC4 / R-007 | **Genuine violation** | Verified against source. `backup.py:299-308` builds `remapped = dict(put.context)` and passes it to `_storage_failure(...)` → `qmf.core.unpersistable(reason, context=remapped)` (`backup.py:938-944`). `unpersistable` **raises `ValueError`** when `context` contains the reserved key `reason` (`qmf-core/src/qmf/core/sinks.py:180-185`). The adapter refusal builders this project ships — `qmf/data/store/refusals.py:35` `invalid_input` and `:73` `policy_rejection` — **both** set `context["reason"]` unconditionally, so any adapter refusal built the project's own way trips it. The fake is therefore realistic, not contrived: `WrongCategoryStorage`'s context `{"field": "adapter", "reason": ...}` is byte-for-byte the shape `policy_rejection("adapter", "miswired category")` produces. AC4 and `docs/components/object-storage.md:31` are unconditional — refusals are "returned, never raised across the boundary". Test asserts the requirement (a `pytest.fail` on **any** raise, then a `storage failure` category), not the code. Falsifiable and currently red. *Severity note:* medium is defensible but generous — the trigger requires an off-contract adapter category. The defect is in the boundary's own defensive code, which is why it stands. |
| **E5-F02** | FR-014 / CT-14 / 5.2 AC1 / R-007 | **Genuine violation** | Identical defect on the GET path, `backup.py:401-410`, same `_storage_failure`/`unpersistable` route. Distinct call site, distinct AC, distinct public entry point (`restore_copy`) — correctly filed as its own row rather than folded into E5-F01. |
| **E5-F03** | 5.2 AC4 / R-EVIDENCE (symlink-safe write) | **UNPROVEN — correctly recorded** | `os.symlink` needs `SeCreateSymbolicLink` (WinError 1314) on this host; the test **skips** rather than passing vacuously — exactly rule 1's disposition. The row states what *is* proven (the `Path.resolve()`-based in-place guard, via the non-symlink same-resolved-root case) and what is not (no realpath-within-root guard on interior leaf writes), and names the residual risk. Honest and complete. |
| **E5-F04** | 5.1 AC5 / 5.3 AC4 / 5.4 AC2 — numeric RPO/RTO/retention/cadence | **UNPROVEN — correctly recorded** | Confirmed blocked: DEC-0118 leaves the four `registry:*` numerics at the node/ops sitting (`docs/lenses/ops/runbook.md:43` — "only the numerics … stay null"). The *behaviours* (refuse-to-own, null pointers) are proven; no ratified value exists to assert against. |
| **E5-F05** | 5.1 AC5 / 5.4 AC4 — crypto strength / key custody | **UNPROVEN — correctly recorded** | DEC-0118 + AR-37 leave algorithm and key custody unratified. The testable half (payload is the injected cipher's *output*, no credential in evidence) is green via `5_1_u4/u10/p5` and the G1/G2 gates. |
| **E5-F06** | 5.1 AC5 — object-key layout | **UNPROVEN — correctly recorded** | CT-14 `node_ops_pointer` names object-key layout as unpinned (DEC-0045/DEC-0118). No-provider-baked-in is proven by G1. |
| **E5-F07** | 5.4 AC1/AC2 — nightly schedule **execution** | **UNPROVEN — correctly recorded** | CT-14 invariant 1 makes execution application/ops-owned; asserting a QMF-owned firing would breach the primitives-only law and the PLAN's own prohibition (e). Refuse-to-own + app-driven `run_once` are green. |
| **E5-F08** | 5.3 AC4 — full-restore rehearsal cadence | **UNPROVEN — correctly recorded** | `registry:restore_verification_cadence` is null pending the node/ops sitting. Rehearsal-as-primitive is green; the period has nothing to bind. |

**Tally: 2 genuine violations · 0 wrong-expectation rows · 6 UNPROVEN correctly recorded.**
No filed row is a false positive; every UNPROVEN row is genuinely blocked spec or genuine environment
limit. The defect is on the other side of the ledger — **rows that are owed and missing** (W-1, M-1, M-2,
M-3, M-5, M-8).

---

## 4. Rule-by-rule audit of the hardened author contract

| Rule | Verdict |
|---|---|
| 1 — falsifiability | **Mostly met.** Refusal arms are reachable, both hypothesis arms fire (`5_2_p2` sweeps `pos` across the seal at 1e6), absence-of-effect is observed by reading the sink. The symlink case was correctly demoted to a skip + UNPROVEN rather than a green. **Miss:** M-1's counter-case (later calendar identity / tzdata) is constructible and was never constructed, so that clause is green with no counter-case. |
| 2 — banned shapes | **Partially met.** Real violations found: the impl-constant migration-order assertion (W-3), the echoed `documented_restore_path` (W-2), and the L4/L2 duplication. Mitigated-and-disclosed: the `ENCRYPTION_REQUIRED` / `NODE_OPS_*` / `CYCLE_ROOM_ROLES` constants. No lossy JSON round-trip, no unratified prose asserted, no unreachable generator arm. |
| 3 — independent observation | **Met.** `MemStorage.put_calls`/`objs` and re-read exports are test-owned; `exports_identical` is test-owned rather than the impl's `_exports_match`; no private `_helper` is driven; absence of partial restore is observed as `record_count == 0`, not a returned flag. |
| 4 — fault realism | **Met, and well done.** Transport doubles raise real `ConnectionError`/`OSError`/`TimeoutError`; the CT-26 doubles raise `StoreEngineError`, which is the engines' documented Protocol raise type (the layer that wraps pyarrow/sqlite3/OSError) — i.e. the true seam type, not qmf-data's already-normalized refusal. Retryability propagation is checked in both directions (`5_1_p4_ct26_store_fault_matrix`). |
| 5 — scope honesty | **Not met.** Six clauses narrowed or excluded without a row: W-1 (refusal categories), M-1, M-2, M-3, M-5, M-8. RESULTS' "Scope honesty" section is otherwise strong and its L6 §(a) disclosure is creditable prose — but prose in a review section is not the row the rule asks for. |
| 6 — findings.csv completeness | **Not met**, for the same six. What *is* recorded is recorded correctly. |

---

## 5. What would close the gaps

1. Add the M-1 test: seed under `H.cal("v3","2025a")`, back up, restore into a replacement store whose
   seal carries `H.cal("v4","2026a")`, assert the `int64` `t` values are bit-identical and still `int`.
   If the surface turns out to have no calendar-derivation site at all, that is an **UNPROVEN row**
   ("structurally no re-derivation site"), not silence.
2. Resolve W-1 one way or the other: file a defect row for `invalid input` crossing CT-14/CT-26's ratified
   two-category boundary set, **or** file an UNPROVEN/reinterpretation row; then restore `5_1_c4`'s
   forbidden set to all five non-boundary categories.
3. Assert 5.3 AC3's order against the literal five-stage tuple from the AC, and add an independent
   dry-run witness (a dry-run that leaves the destination empty, or that aborts a migration the real
   migrate step would have accepted).
4. Add the three missing rows: M-2 (one-writer-per-stream), M-5 (seal position not evidence-derived —
   the PLAN's own failed probe), M-8 (topology, not code-testable).
5. Extend 5.4 AC2 to `OffMachineBackup` / the qmf-data surface, which the AC names alongside the cycle.
