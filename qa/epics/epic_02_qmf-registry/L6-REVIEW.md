# L6 — Requirements-fidelity review — Epic 2 (`qmf-registry`)

- **Scope:** one question per test — *does it assert what the requirement demands, or what the implementation happens to do?*
- **Reviewed:** `qa/epics/epic_02_qmf-registry/{PLAN.md, RESULTS.md, findings.csv}` and the 11 files under `qa/tests/epic_02/`.
- **Authorities used (precedence order):** `_bmad-output/planning-artifacts/epics.md` §Epic 2 (Stories 2.1–2.4) → `docs/components/qmf-registry.md` (`COMP-QMF-REGISTRY` May / May-never / FM table), `docs/contracts/CT-06,07,09,13`, `docs/scenarios/SCN-0007-human-promotion.md`, `docs/constitution.md` (L17/L30).
- **Not re-done here:** the source review, and no test was run or edited.

## Verdict: **gaps**

The suite is genuinely strong where it is adversarial. `E2-L4-02`, `E2-L4-03` (both variants, including the swap-to-another-valid-edge line), `E2-L4-07`, and `E2-L5-01` assert what the requirements demand, through the public seam, against real bytes on disk — those are the highest-value tests in the epic and they hold up.

The verdict is `gaps` for three reasons, in order of consequence:

1. **The P0-5 gate is reported GREEN with an untested door.** The `human-only signer` acceptance criterion was deliberately not asserted, on a reading of DEC-0116 that the authorities do not support.
2. **An entire Story 2.3 acceptance criterion (CT-13 promotion event) has zero tests** despite `emit_promotion_event` / `PromotionEvent` being realized, exported public surface. No test file imports either symbol.
3. **Both `findings.csv` rows are bound to the wrong epic.** `epics.md` assigns FR-048 to **Epic 12**, not Epic 2.

Nothing here disturbs the two identity/tamper P0 gates, which are correctly proven. The money gate is *mostly* proven — the no-card refusal, reserved-kind wall, superseded-template refusal, and the SCN-0007 chain are all real — but it is not proven to the standard RESULTS claims for it.

---

## 1. Wrong-expectation tests

Eight items, covering eleven test functions. Ranked by consequence.

### W1 — `E2-L1-13` (both functions) asserts the reserved-kind wall in place of the human-only signer — **and `E2-L3-02` labels itself as covering it**

- **Tests:** `test_l1_promotion.py::test_e2_l1_13_reserved_kind_cannot_be_minted_via_generic_factory`, `::test_e2_l1_13_reserved_kind_cannot_be_registered_in_kind_registry`; `test_l3_contract.py::test_e2_l3_02_ct06_boundary_conditions` (the comment `# human-only promotion occurrence attesting the record's fp1`).
- **What the tests assert:** that `KIND_PROMOTION_OCCURRENCE_CARD` is in `RESERVED_KIND_NAMES` and cannot be minted through `RegistrationRecord.try_create` / registered in a `KindRegistry`. `E2-L3-02` signs a card with `signer="operator:mubarak"` and asserts it authorizes.
- **What the requirement actually says:** three independent authorities make the signer itself an in-scope registry property.
  - `epics.md` Story 2.3 AC1: *"a promotion-occurrence card is minted with a **human-only signer**, a signed immutable record, and a mandatory plain-words summary declared an identity field"* — the human-only signer sits in the same clause as the summary, which **is** tested (`E2-L1-12`).
  - `docs/components/qmf-registry.md` L21 (`May`): *"reserve the promotion-occurrence card kind with a **human-only signer** and a mandatory plain-words summary declared an identity field (DEC-0116)"*; and the FM-4 row L106: *"the **human-only signer** and mandatory plain-words summary (an identity field) are required."*
  - `SCN-0007` L17: *"a **human-only signer**, a signed immutable record, and a mandatory plain-words summary field."*
- **Why the substitution is wrong:** RESULTS L61–68 declines the assertion because *"any human-vs-agent identity check on the signer string is platform territory outside QMF (DEC-0116)."* DEC-0116's carve-out is narrower than that. `docs/components/qmf-registry.md` L56 states it exactly: *"the promotion gate itself (**workflow, UI, and timing**) is platform territory outside QMF (DEC-0116)."* Workflow, UI, and timing — not the signer field of the card. The same DEC-0116 is cited *for* the human-only signer two clauses earlier in the same line.
- **The hole this leaves:** `PromotionCard.sign` is exported public surface. `E2-L1-16` drives it with `signer=""` (refused). No test ever calls `PromotionCard.sign(signer="agent:bot-7", ...)`. The L5 chain passes `"agent:bot-7"` only into `RegistrationRecord.try_create`, where the reserved-kind wall — not the signer — produces the refusal. So the question *"can an agent mint a card that `authorize_live_promotion` accepts?"* is unanswered, and it is the P0-5 question. RESULTS reports P0-5 as **PASS**.
- **Correct handling under the lane rules:** author the assertion the requirement demands and, if it fails, record it as a FINDING. Declining to author an assertion because it would test behaviour that may not exist is the exact failure mode this level exists to catch.

### W2 — `test_l1_bot.py` (both functions) demands FR-048 of Epic 2; `epics.md` assigns FR-048 to Epic 12

- **Tests:** `test_e2_l1_17_18_bot_kind_both_conformance_layers_gate_exists` (`assert surface`, where `surface` is empty), `test_e2_l1_19_20_ct33_bot_definition_kind_and_cardinality_exist` (`assert False`).
- **What the requirement actually says:** `epics.md` L305 — *"FR-048: **Epic 12** — technical-never-performance conformance"*; Epic 12's heading (*QML protocol & conformance, Wave 5*) lists *"FRs covered: FR-048, FR-050"*, with the registration-gate story at L2671. Epic 2's own heading lists *"FRs covered: FR-006, FR-007, FR-008, FR-009"* and its four stories cover only those.
- **Judgement:** the *observation* is correct (no bot surface exists in `qmf.registry`) and the PLAN itself noticed FR-048 is not a Story of Epic 2. But the tests convert a build-order fact into an Epic 2 failure. Under `epics.md` — the top authority — Epic 2 has no FR-048 obligation, and CT-33 is `defined-unwired` with the mint at the composition root under AD-25. These are notes for Epic 12, not Epic 2 findings.
- Two permanently-red tests also mean this epic's suite can never go green, which will read as a regression to anyone who runs it later without the RESULTS narrative in hand.

### W3 — `E2-L3-04` / `E2-L4-06` prove that `rebuild_indexes()` is stable, not that losing an index costs only a rebuild

- **Tests:** `test_l3_contract.py::test_e2_l3_04_ct07_boundary_and_rebuildable_index`, `test_l4_integration.py::test_e2_l4_06_dropped_index_reproduced_by_rebuild`.
- **What they assert:** call `log.rebuild_indexes()`, then assert the view is unchanged; and (L4) read a persisted stream twice and compare.
- **What the requirement actually says:** Story 2.2 AC2 — *"indexes over edges are local and rebuildable, so **losing an index costs a rebuild, never evidence**"* (CT-07, DEC-0114). The demanded proof is destructive: delete the index artifact, then show the edge view reconstructs from the JSONL lines with no evidence lost. Neither test loses anything. `E2-L4-06`'s name (`dropped_index_...`) claims a drop that never happens.
- Also in `E2-L3-04`: `assert log.current_head(a) == log.current_head(a)` compares a call to itself — a no-op that can never fail.

### W4 — `E2-L1-05` proves a `qmf.core` primitive, not the registry's collision behaviour

- **Test:** `test_l1_records.py::test_e2_l1_05_true_collision_refused_and_alarmed`.
- **What it asserts:** `reconcile_write(...)` — a `qmf.core` (Epic 1) function — returns `policy rejection` with `alarm=True`.
- **What the requirement says:** Story 2.1 AC3 is about **two writes to the same fp1 stable id** through the registry. The test's own docstring concedes *"Distinct contents cannot share a stable id through the public register() path"* — i.e. the registry-level assertion was not reachable, so an Epic 1 primitive was substituted.
- **Rescued by:** `E2-L4-07` (`differing_bytes_same_fp1_refused_and_alarmed`), which does prove it at the registry store boundary with a colliding engine. That test carries the P0-4 no-silent-overwrite gate; `E2-L1-05` adds nothing about `qmf.registry` and should not be counted as Epic 2 coverage.

### W5 — `E2-L3-01`'s "round-trip" compares JSON to JSON

- **Test:** `test_l3_contract.py::test_e2_l3_01_ct06_record_canonical_round_trip`.
- **What it asserts:** `json.loads(canonical) == json.loads(json.dumps(rec.fp1_identity(), default=str))`. Both sides derive from the same in-memory object and `default=str` silently coerces anything not JSON-native, so a type that fails to survive a real decode would still pass here.
- **What the requirement says:** CT-06 owner-conformance round-trip means encode → **decode through the contract's own codec** → semantic equality. Mitigated in practice by `E2-L3-05` and `E2-L4-01`, which do a genuine persist-and-read-back; `E2-L3-01` is redundant rather than load-bearing.

### W6 — `E2-L4-04` proves the refusal but not "no partial registration is claimed successful"

- **Test:** `test_l4_integration.py::test_e2_l4_04_store_failure_translates_to_typed_refusal`.
- **What the requirement says:** Story 2.4 AC4 has two halves — *"a `storage failure` typed refusal is returned … **And no partial registration is claimed successful**"* (FM-8). The test asserts the refusal category and stops; it never reads back to show nothing landed under that fingerprint. The second half is the one that protects against a half-written record being visible later.

### W7 — `E2-L4-08` asserts the migration report's self-reported fields for preflight and dry-run

- **Test:** `test_l4_integration.py::test_e2_l4_08_migration_is_staged_and_never_in_place`.
- **Credit where due:** it checks `Path(report.backup_path).is_file()` — a real artifact, not a constant — and confirms the source stays readable. That half is honest.
- **The gap:** *preflight* and *dry-run* (Story 2.4 AC5: *"preflight → backup-first → dry-run → migrate → verify"*) are asserted only via `report.records_only` / `report.verified_count` — the code's own testimony about what it did. A migration that skipped the dry-run entirely and set the field would pass.

### W8 — `E2-L2-06`'s accept-branch is unreachable

- **Test:** `test_l2_properties.py::test_e2_l2_06_one_writer_per_stream`.
- The stream owner is `h.writer("stream-owner", boot="boot-owner")`; the generated `machine`/`boot` are `st.text(max_size=6)`. `"stream-owner"` is 12 characters, so `other == stream_writer` can never hold and the `assert is_ok(out)` branch never executes. The property only ever exercises rejection. Story 2.2 AC6's positive half (the stream's own writer is accepted) is unproven.

---

## 2. Missed requirements

Requirements drawn **only** from `epics.md` §Epic 2, Stories 2.1–2.4, with no test in `qa/tests/epic_02/`.

### Story 2.3 — human-signed promotion (FR-009)

| # | Requirement (epics.md AC) | Status |
|---|---|---|
| **M1** | *"the CT-13 `promotion` event carrying **ONLY** the promotion card's fp1 fingerprint plus `correlation_id` — **never a second schema**, And the registry card is canonical."* (CT-13; CT-06) | **No test.** `emit_promotion_event` and `PromotionEvent` are exported from `qmf.registry.__all__`; **no file under `qa/tests/epic_02/` imports either symbol**, and no test mentions CT-13 or `correlation_id`. The PLAN names `emit_promotion_event` in its §6 fixture list but authors no assertion for it in §4, and §5's traceability matrix has no CT-13 row. Also cited in SCN-0007's Given (L21). |
| **M2** | *"a **human-only signer**"* (Story 2.3 AC1) | **Deliberately not asserted** — see W1. |
| **M3** | *"a **signed immutable record**"* — the card is never edited in place | No test attempts to mutate a signed `PromotionCard`. The supersede-on-correction path is covered (`E2-L1-15`, `E2-L5-01`); immutability of the object itself is not. |
| **M4** | *"carrying **reviewer identity and instant**"* (Story 2.3 AC1; SCN-0007 L21) | No assertion that these fields are present on the card or that they are/aren't identity-bearing. |
| **M5** | *"V1 signing is the operator's recorded approval, **taking no cryptographic dependency**"* | Not asserted. Cheaply provable at L0 — the existing `test_e2_l0_02` banned-dependency list covers database servers only; adding `cryptography`/`pynacl`/`gnupg`/`pyopenssl` would have closed it in one line. |

### Story 2.2 — append-only typed lineage edges (FR-007)

| # | Requirement (epics.md AC) | Status |
|---|---|---|
| **M6** | *"a byte-identical idempotent re-append is accepted while **a true collision on differing bytes is refused and alarmed**"* (AC5, FM-2) | Idempotent re-append is covered (`E2-L3-04`). The **edge** true-collision/alarm half has no test — records got it (`E2-L4-07`), edges did not. |
| **M7** | *"**size-rotated with a monotonic file ordinal**"* (AC2) | No test. `_jsonl_segments()` globs `*.jsonl` implying segments, but nothing asserts rotation occurs or that the ordinal is monotonic. |
| **M8** | *"appended with **fsync**"* (AC2) | No test. Arguably reachable only through the CT-11 seam, but it is stated as a Story 2.2 AC and is unrecorded either way. |
| **M9** | *"`corroborates` and `disagrees-with` edges keep source disagreements visible and are **never merged away**"* (AC4, DEC-0119) | No test. `E2-L3-03` round-trips all 14 types but nothing asserts that two disagreeing edges both survive a read and are not collapsed. |
| **M10** | *"losing an index costs a rebuild, **never evidence**"* (AC2) | No destructive test — see W3. |
| **M11** | *"exactly one writer holding a WriterId and **unlimited readers**"* (AC6) | The one-writer half is covered (rejection only, see W8); "unlimited readers" is unasserted. |

### Story 2.1 — per-kind fingerprint-keyed records (FR-006)

| # | Requirement (epics.md AC) | Status |
|---|---|---|
| **M12** | *"lineage that accrues after a record's birth … is written **ONLY** as CT-07 typed edges and **never back into the record**, And at-birth parent references stay in the header and **readers never union header references with edges**"* (AC5) | **No test.** A reader that unioned header parents with edges would be a real defect nothing in this suite catches. `E2-L3-05` asserts `at_birth_parent_refs` survives a round trip, which is a different property. |
| **M13** | *"the reserved kind names promotion-occurrence-card **and treasury-boundary-event** are honored"* (AC4) | Only `KIND_PROMOTION_OCCURRENCE_CARD` is asserted to be reserved. No test mentions `treasury`. |
| **M14** | *"the module ships its CT-06 contract test plus **reference examples** and meets the **80% coverage floor**"* (AR-19/AR-21/AR-20) | No assertion that reference examples ship. Coverage is called "informational" in PLAN §7 and no coverage number is recorded anywhere in RESULTS, so the 80% exit criterion in PLAN §8 is unevidenced. |

### Story 2.4 — persistence through the qmf-data seam (FR-008)

| # | Requirement (epics.md AC) | Status |
|---|---|---|
| **M15** | *"with **stdlib-typed signatures at the boundary**"* (AC1; CT-09/CT-11/L30) | No test. This is the concrete, checkable half of the single-ratified-edge law — that no `qmf` type leaks across the `qmf-registry → qmf-data` boundary — and it is L0-shaped and cheap. `E2-L0-01` checks import direction only. |
| **M16** | *"**no partial registration is claimed successful**"* (AC4) | Half-covered — see W6. |
| **M17** | *"with a **documented restore path**"* (AC5) | Unasserted (documentation gate, L0-shaped). |
| **M18** | *"the CT-09 contract test runs against the CT-11 store-seam **by both producer and consumer**"* (AC6, AR-18) | `E2-L3-05` exercises the consumer side only. The dual-run is what AR-18 asks for. |

**Correctly excluded, not missed:** CT-08 causality / attempt-gate (FM-3) — the untestable-positive deferral in PLAN §8.1 is right, and `E2-L5-01` covers the negative face. The migration-across-a-real-version-bump limit (PLAN §8.4) is also fairly stated.

---

## 3. `findings.csv` adjudication

| Row | Requirement violation? | Verdict |
|---|---|---|
| **E2-F01** — no both-conformance-layers Bot-mint gate on the `qmf.registry` surface | **No** | **Wrong expectation for this epic.** The observation is accurate — `qmf.registry` exposes no bot/conformance/strategy-family/footprint symbol — but `epics.md` L305 assigns **FR-048 to Epic 12**, and Epic 2's stories cover FR-006/007/008/009 only. CT-33 is `wiring_status: defined-unwired`; QML authors the declaration and the composition root mints under AD-25. Absence here is the ratified build order, not a defect. Re-file against Epic 12 or demote to a PLAN §8 deferral note; do not carry as an Epic 2 finding. |
| **E2-F02** — no `bot-definition` kind, no `strategy_family_id` cardinality rule, no footprint producer-binding rule | **No** | **Same disposition as E2-F01.** Additionally, the `assert False` construction makes this permanently red regardless of any future state, so it cannot even serve as a tripwire for when Epic 12 lands. Note that `DEC-0115` bars hardcoding "exactly one" *anywhere in the bot vocabulary*, so the cardinality expectation would need careful phrasing (a deliberate AD-17 ruling, not a hardcoded assumption) if it is re-authored under Epic 12. |

**Tally: 0 of 2 rows are genuine Epic 2 requirement violations; 2 of 2 are wrong-expectation / mis-scoped.**

Severity labelling on both rows (`low — coverage-gap / documented-deferral`) is honest and the descriptions do not overclaim — the error is the epic binding, not the diagnosis.

**Findings that should exist and do not:** W1 (human-only signer unasserted on a P0-5 surface) and M1 (CT-13 promotion event untested) are both in-scope, both on realized public surface, and neither appears in `findings.csv`. As it stands the findings file records two out-of-scope non-defects and none of the in-scope gaps.

---

## 4. What holds up

Recorded so the re-work is scoped and the good work is not redone:

- **`E2-L4-02` / `E2-L4-03` (both)** — the strongest tests in the epic. Tampering real SQLite bytes and real JSONL lines, including the swap-to-another-*valid*-edge case, is exactly the adversarial shape the read-back-integrity requirement demands, and the assertions are the requirement's, not the code's.
- **`E2-L4-07`** — the colliding-engine fixture proves the no-silent-overwrite half of P0-4 at the registry's own store boundary.
- **`E2-L5-01`** — faithfully tracks SCN-0007's Given/When/Then, including the typo-fix-mints-a-new-card-with-a-`supersedes`-edge tail and the superseded-card-no-longer-authorizes turn. Its only omission is the CT-13 clause of the scenario's Given (M1).
- **`E2-L1-15`'s three variants** — particularly `absent_in_force_template_is_refused_never_skipped`, which asserts a refusal where a silent skip would be the convenient implementation behaviour. That is the right instinct applied correctly.
- **`E2-L0-01/02` and `E2-L2-07`** — read the real tree, assert the L30/AR-14 laws on package shape, and the hash-scan exclusion for the `fp1:sha256:` docstring literal is a correct narrowing, not a weakening.
- **PLAN §8 and RESULTS' untestable sections** — the deferrals are declared rather than hidden, GAP-QA-01 (the absent `_bmad-output/test-artifacts/` tree, independently confirmed in this review) and GAP-QA-02 (the unresolvable AR-52 citation) are both real and correctly recorded.

## 5. Required re-work, ranked

1. **Author the human-only-signer assertion** against `PromotionCard.sign(signer=...)` with a non-human signer, and record the result as a FINDING if it does not refuse. Until then, P0-5 should not be reported GREEN. (W1 / M2)
2. **Author CT-13 coverage** for `emit_promotion_event` / `PromotionEvent`: the event carries the card fp1 and `correlation_id` and nothing else — no second schema. (M1)
3. **Re-file E2-F01/E2-F02 against Epic 12** and remove the two permanently-red bot tests from the Epic 2 suite so it can go green.
4. **Make the index test destructive** — delete the index artifact, rebuild from lines, assert no evidence lost; drop the self-comparing assertion. (W3 / M10)
5. **Close the cheap L0/L1 gaps:** `treasury-boundary-event` reserved (M13), no cryptographic dependency (M5), stdlib-typed boundary signatures (M15), edge true-collision refused and alarmed (M6), header-parents-never-unioned-with-edges (M12).
6. **Complete the two half-covered ACs:** read back after the storage failure to prove no partial registration (M16), and fix the unreachable accept-branch in the one-writer property (W8).
