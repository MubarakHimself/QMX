# Epic 1 — qmf-core — Independent Verification RESULTS (tier T1)

**Run command (from worktree root):**
`uv run --with hypothesis pytest qa/tests/epic_01 -q --tb=short`

**Outcome:** 86 tests authored & run — **85 passed, 1 failed, 0 errored** (runtime ~9.7s).
The single failure is a **confirmed finding** (E1-F01), not a test-code defect. No
assertion was weakened to make a test pass; source is read-only evidence.

Tests live under `qa/tests/epic_01/`. Levels per PLAN.md §3: L1 unit (62 `E1-U*`) +
L1 property (5 `E1-P*`) + L2 contract (12 `E1-C*`) + L3 integration (4 `E1-I*`) + L4
acceptance (2 `E1-A*`), plus one L0 behavioural check (`E1-S07` import budget).

| Level | File | Planned | Run | Pass | Fail |
|---|---|---|---|---|---|
| L1 unit | test_ct04_refusal.py | U01–U08 | 8 | 8 | 0 |
| L1 unit | test_ct03_identity.py | U09–U15 | 7 | 7 | 0 |
| L1 unit | test_ct01_exact.py | U16–U28 | 13 | 13 | 0 |
| L1 unit | test_ct02_chrono.py | U29–U46 | 18 | 18 | 0 |
| L1 unit | test_ct05_fingerprint.py | U47–U56 | 10 | 10 | 0 |
| L1 unit | test_seams.py | U57–U62 | 6 | 6 | 0 |
| L1 property | test_properties.py | P01–P05 | 5 | 5 | 0 |
| L2 contract | test_l2_contract.py | C01–C12 | 12 | 12 | 0 |
| L3 integration | test_l3_integration.py | I01–I04 | 4 | 3 | **1** |
| L4 acceptance + L0 | test_l4_acceptance.py | A01, A02, S07 | 3 | 3 | 0 |
| **Total** | | | **86** | **85** | **1** |

---

## Failure (finding)

- **E1-I03** (`test_e1_i03_single_fp1_implementation_only_in_qmf_core`) — **FAIL** →
  **finding E1-F01**. Requirement: CT-05 / DEC-0108 / AR-14 (RG-DEPGRAPH) — the
  canonical serializer and fp1 fingerprint live *only* in qmf-core; no other package
  computes a fingerprint except by calling it. **Meaning:** `qmf-data` ships **two**
  hand-rolled fp1 implementations — `backup.py::_fp1_of` (lines 932–935) and
  `store/backup_input.py::_fp1` (lines 70–72, hashing at line 197) — each running
  `hashlib.sha256(payload).hexdigest()` and emitting `fp1:sha256:{digest}` directly,
  duplicating qmf-core's private recipe. If the recipe ever changes (fp2, a
  canonicalisation rule), these copies silently diverge and fork identity. See
  findings.csv (E1-F01).

---

## Per-test detail (L1 unit)

### CT-04 typed refusal (Story 1.2, `refusal.py`)
| ID | Requirement | Result |
|---|---|---|
| E1-U01 | CT-04 schema — frozen value, three fields read back | PASS |
| E1-U02 | CT-04 enums — exactly seven categories, no eighth | PASS |
| E1-U03 | CT-04 enums — exactly three retryability values | PASS |
| E1-U04 | CT-04 nullability — after-condition descriptor both arms | PASS |
| E1-U05 | CT-04 / DEC-0112 — context present, structured, never null | PASS |
| E1-U06 ◆ | CT-04 / DEC-0112 — exact {field,reason} + enum member (pin exact.py:166) | PASS |
| E1-U07 | CT-04 / DEC-0109 — try_create refusal arm; unchecked ctor available | PASS |
| E1-U08 | CT-04 / DEC-0109/0112 — returned not raised, not swallowed | PASS |

### CT-03 identity (Story 1.3, `identity.py`)
| ID | Requirement | Result |
|---|---|---|
| E1-U09 | CT-03 — opaque (venue, symbol); symbol verbatim, never parsed | PASS |
| E1-U10 | CT-03 — VenueId opaque/stable; case-distinct, never normalized | PASS |
| E1-U11 | CT-03 enums — exactly one role from fixed set; others refused | PASS |
| E1-U12 ◆ | CT-03/CT-04/DEC-0109 — missing/empty/blank venue refuses (pin exact.py:251) | PASS |
| E1-U13 ◆ | CT-03/CT-04/DEC-0109 — missing/empty/blank symbol refuses | PASS |
| E1-U14 | CT-03/DEC-0108 — null prohibited in identity content (any depth) | PASS |
| E1-U15 | CT-03 — change is a new dated record; append-only, frozen | PASS |

### CT-01 exact money/price/quantity (Story 1.4, `exact.py`)
| ID | Requirement | Result |
|---|---|---|
| E1-U16 | CT-01 — scaled integers; Price instrument-tagged; unit opaque | PASS |
| E1-U17 | CT-01/DEC-0154 — closed unit-kind vocab; null unit-kind refuses | PASS |
| E1-U18 | CT-01 FM-1/DEC-0105 — binary float → invalid input refusal | PASS |
| E1-U19 | CT-01/DEC-0105 — float only via named boundary w/ rounding | PASS |
| E1-U20 | CT-01 FM-4 — mixed-scale losslessly promotes to finer scale | PASS |
| E1-U21 | CT-01 FM-4/DEC-0109 — inexact result refuses, never silent round | PASS |
| E1-U22 | CT-01/DEC-0131 — Price−Price → first-class PriceDelta; pip from metadata | PASS |
| E1-U23 | CT-01/DEC-0154 — absent value-factor → unavailable dependency | PASS |
| E1-U24 ◆ | CT-01/DEC-0105 — rounding direction at zero boundary exact (pin exact.py:304) | PASS |
| E1-U25 ◆ | CT-01 — scale range endpoints refused, `given` echoes (pin exact.py:225) | PASS |
| E1-U26 ◆ | CT-01/DEC-0105 — NaN/inf cannot cross (pin exact.py:337) | PASS |
| E1-U27 ◆ | CT-01/DEC-0105 — missing rounding mode refuses, lists allowed | PASS |
| E1-U28 | CT-01/DEC-0105/0141 — foreign money verbatim; absent scale refuses | PASS |

### CT-02 exact time (Story 1.5, `chrono.py`)
| ID | Requirement | Result |
|---|---|---|
| E1-U29 | CT-02/DEC-0106 — int64 UTC-ns; instant 0 valid | PASS |
| E1-U30 ◆ | CT-02 FM-2 — int64 min/max accepted, ±1 refused (pin chrono.py:171) | PASS |
| E1-U31 | CT-02/DEC-0106 — absent time is absent field, not zero sentinel | PASS |
| E1-U32 | CT-02 — CivilDate and TradingDate are distinct types | PASS |
| E1-U33 | CT-02 — TradingDate carries calendar identity; equality within calendar | PASS |
| E1-U34 | CT-02 FM-3 — cross-calendar comparison → refusal | PASS |
| E1-U35 | CT-02 — no from_instant; never a causality proxy | PASS |
| E1-U36 ◆ | CT-02/DEC-0106 — equal-instant refuses; bad input named (pin chrono.py:995) | PASS |
| E1-U37 | CT-02 — Duration signed int64; overflow refused | PASS |
| E1-U38 | CT-02 — Interval half-open; contains/overlaps end-exclusive | PASS |
| E1-U39 | CT-02 — wall/monotonic type-separated; mono excluded from identity | PASS |
| E1-U40 | CT-02/DEC-0022 — Clock protocol; DataDrivenClock replays in order | PASS |
| E1-U41 ◆ | CT-02 — exhaustion boundary, exact message (pin chrono.py:756/764) | PASS |
| E1-U42 ◆ | CT-02 — advances exactly one per call (pin chrono.py:756) | PASS |
| E1-U43 ◆ | CT-02/DEC-0106 — WriterSequencer start + OrderingKey wiring (pin chrono.py:881/895) | PASS |
| E1-U44 ◆ | CT-02 FM-5 — tzdb pin mismatch/empty; context field tzdata_version (pin chrono.py:1022) | PASS |
| E1-U45 | CT-02/DEC-0108 — render_utc_iso8601 display-only; non-Instant refuses | PASS |
| E1-U46 | CT-02/DEC-0106 — WriterId per (machine,role,stream); mono scoped to boot | PASS |

### CT-05 fingerprint/label/worlds (Story 1.6, `fingerprint.py`)
| ID | Requirement | Result |
|---|---|---|
| E1-U47 | CT-05 — fp1:sha256:<lowercase-hex> form | PASS |
| E1-U48 | CT-05/DEC-0108 — float in identity content → refusal | PASS |
| E1-U49 | CT-05/DEC-0108 — null prohibited; absent is omitted key | PASS |
| E1-U50 | CT-05/DEC-0108 — sorted keys, NFC, order-significant arrays | PASS |
| E1-U51 | CT-05 — equal semantic ⇒ equal fp1; single diff differs | PASS |
| E1-U52 | CT-05 FM-6 — idempotent silent; true collision refused+alarmed | PASS |
| E1-U53 | CT-05/DEC-0110 — label parts ARE identity; occurrence outside | PASS |
| E1-U54 | CT-05 FM-7/GAP-0048 — world=simulated → policy rejection | PASS |
| E1-U55 | CT-05/DEC-0110 — non-live world never writes live namespace | PASS |
| E1-U56 | CT-05/DEC-0131 — producer identity distinguishes EMA(20)/SMA(20) | PASS |

### Seams — secrets & sinks (Story 1.9, `secret.py`, `sinks.py`)
| ID | Requirement | Result |
|---|---|---|
| E1-U57 | FM-9/AR-37/DEC-0136 — SecretValue never renders; only ref id | PASS |
| E1-U58 | DEC-0136/0109 — non-opaque SecretRef refuses; secret never echoed | PASS |
| E1-U59 | AD-15/DEC-0138 — the four ports are typing.Protocol seams | PASS |
| E1-U60 | CT-04/AR-47 — sink refusal is a CT-04 storage-failure value | PASS |
| E1-U61 | AR-37/38 — SecretStore read+atomic_replace only; no plaintext getter | PASS |
| E1-U62 | DEC-0136/0108 — SecretRef/SecretValue excluded from fp1 | PASS |

## L1 property (hypothesis, derandomised seed)
| ID | Requirement | Result |
|---|---|---|
| E1-P01 | R-001 / CT-01 FM-4 / DEC-0154 — mixed-tag arithmetic ALWAYS refuses (category in CT-04 vocab) | PASS |
| E1-P02 | R-001 / CT-01 FM-4 — mixed-scale same-currency add is EXACT (no silent round) | PASS |
| E1-P03 | R-002 / CT-04 / DEC-0109 — no public callable raises across the boundary | PASS |
| E1-P04 | CT-05 / DEC-0108 — float anywhere in identity content always refuses | PASS |
| E1-P05 | CT-01 canonical form / CT-05 / DEC-0158 — equal value ⇒ equal fp1 (6/4≡3/2, cross-scale) | PASS |

## L2 contract conformance
| ID | Requirement | Result |
|---|---|---|
| E1-C01 | CT-01 round-trip semantic equality | PASS |
| E1-C02 | CT-01 boundary suite (unit-kind, scale, nullability, malformed) | PASS |
| E1-C03 | CT-02 round-trip (Instant/Duration/Interval/TradingDate) | PASS |
| E1-C04 | CT-02 boundary suite (range, in-band calendar, wall/mono, malformed) | PASS |
| E1-C05 | CT-03 round-trip ((venue,symbol) + dated records) | PASS |
| E1-C06 | CT-03 boundary suite (role enum, symbol opacity, nullability) | PASS |
| E1-C07 | CT-04 round-trip (refusal fields) | PASS |
| E1-C08 | CT-04 boundary suite (seven categories, retryability, after-condition) | PASS |
| E1-C09 | CT-05 round-trip (Fingerprint parse + ResultLabel) | PASS |
| E1-C10 | CT-05 boundary suite (determinism, float-refused, null-omit, world, collision) | PASS |
| E1-C11 | DEC-0103 — every serialized CT-01/02/05 artifact stamps format version 1 | PASS |
| E1-C12 | DEC-0100/0102 — CT surface consumable through the public qmf.core entrypoint | PASS |

## L3 integration / dependency discipline
| ID | Requirement | Result |
|---|---|---|
| E1-I01 | AR-06/18, DEC-0104 — qmf-core stdlib-only (isolated-build soundness proxy) | PASS |
| E1-I02 | DEC-0104/0120 — dep-graph default-deny; sole edge registry→data; nothing imports venue/risk | PASS |
| E1-I03 | CT-05/DEC-0108 — single fp1 implementation (only in qmf-core) | **FAIL → E1-F01** |
| E1-I04 | Story 1.1 — SSSF gate stamp (dev group, testpaths=adws/tests) survives | PASS |

## L4 acceptance + L0 behavioural
| ID | Requirement | Result |
|---|---|---|
| E1-A01 | SCN-0001/DEC-0134 — six boundaries build; open freeze choices stay open (simulated refused, GAP-0048) | PASS |
| E1-A02 | CT-05/DEC-0103 — cross-producer fp1 determinism; newer calendar/tzdata mints new fingerprint | PASS |
| E1-S07 | NFR-04/DEC-0111 — `import qmf.core` well under one second (fresh interpreter) | PASS |

---

## Scope notes, deferrals & untestable items

Carried forward from PLAN.md §8 (recorded, not asserted — an explicit GAP records why
a test cannot exist but never counts as a passing test, DEC-0004):

1. **world=simulated positive behaviour / backtest-fidelity taxonomy (GAP-0048) and
   SR* threshold (GAP-0049).** The *refusal* is fully tested (E1-U54, E1-A01); the
   open freeze choices are deliberately not exercised as passing fixtures.
2. **Money-path taint across package seams (DEC-0026/0105).** Seam partners
   (qmf-data/venue/risk) are out of Epic 1; the single-package taint is tested here,
   cross-seam deferred to Epics 3+.
3. **~40-bot workload benchmark (NFR-04/AR-22).** Deferred to Epics 14–15; only the
   import-time budget (E1-S07) is measurable now.
4. **`after_condition_descriptor` internal field shape (CT-04).** Presence/absence is
   tested (E1-U04); the sub-structure is unpinned by AD-11, untestable by design.
5. **Specific CT-04 category for cross-calendar comparison (FM-3).** The spine pins a
   refusal, not a category; E1-U34 asserts the refusal + context, not a category.
6. **`prop-firm` account role (CT-03).** Representable (E1-U11) but a reserved V1 seam
   with no modelled behaviour to assert.

**L0 static/scanner items E1-S01..S06** (money-path-float scanner, ambient-nondeterminism
scanner, ruff/pyright/secret-scan, `poe check` wiring) are tracked separately per the
level model and are **not part of the L1–L4 ask**; they run through the `poe`/tools
harness (Story 1.7/1.8), not this independent pytest lane. `E1-S07` (import budget) is
included here because it is a clean behavioural assertion. **Not run this pass.**

**E1-I01 / E1-I04 are static proxies.** A true isolated per-package build and a live
`ruff/mypy/pytest adws/tests` run are tier-2 CI concerns; here they are verified as
config + import-graph invariants (qmf-core declares `dependencies = []` and imports only
stdlib; the root pyproject preserves the SSSF gate stamp and adws/tests is present).

**Process finding (carried from PLAN §8, unchanged):** the two named test-artifact
authorities `_bmad-output/test-artifacts/test-design-qa.md` and
`.../test-design/QMX-handoff.md` (the Per-Epic template, L0–L6 model, and the "15
P0/P1 assertions") **do not exist** in the worktree; the template and level model were
reconstructed from `docs/lenses/testing/test-strategy.md`, `docs/components/qmf-core.md`
(FM-1..FM-9), the CT-* contracts, and the mutmut survivor listing. Logged so the handoff
gap is visible, not silently absorbed. (Not itself a code defect; no findings.csv row.)
