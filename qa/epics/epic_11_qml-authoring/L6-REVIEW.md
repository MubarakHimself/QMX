# L6 REQUIREMENTS-FIDELITY REVIEW — Epic 11 (qml-authoring)

Reviewer: L6 independent pass. No test run, no test edited, no source touched.

- Authorities read (precedence order): `_bmad-output/planning-artifacts/epics.md`
  §"Epic 11: QML authoring" (Stories 11.1–11.7); `docs/contracts/ct-33-bot-definition.yaml`,
  `ct-34-confluence.yaml`; `docs/components/qml.md`; `docs/AGENTS.md` ratified-QML block.
- `_bmad-output/test-artifacts/test-design-qa.md` and `.../test-design/QMX-handoff.md`
  are **absent from the worktree** (confirmed: `_bmad-output/` contains only
  `planning-artifacts/`). The author recorded this as a blocked input in PLAN.md and
  RESULTS.md and reconstructed R-009/R-011 and the L0–L6 shape from the task prompt.
  That disclosure is correct and is not held against the author.
- Reviewed: `PLAN.md`, `RESULTS.md`, `findings.csv`, and all 10 files under
  `qa/tests/epic_11/`.

---

## VERDICT: **gaps**

The suite is well above the tier-1 hollow-green baseline. Fingerprint expectations are
recomputed through qmf-core rather than pinned to literals; refusals assert CT-04
*category values*, never prose; the two static scanners (A4, A5) carry genuine
self-falsification arms; C2/C3, D6 and E3/E4 carry explicit non-vacuity companions; F7
observes the host writer through a test-owned `_RecordingRegistrar` sink; B3 resolves
through the **real** qmf-risk `ExitPolicy` rather than qml's own map. The three filed
failures are all genuine, all reproduce against wired source, and I confirmed each one
independently in the source.

It is nonetheless **gaps**, on three counts:

1. One requirement (11.1 AC5) is reported **green off a hardcoded literal** — a test
   that cannot fail without editing source. It should be an UNPROVEN row.
2. **Nine AC clauses have no test at all**, and only three of them appear in the
   scope-honesty section. The rest are silent narrowing (contract rule 5).
3. **E11-F04's UNPROVEN reason is factually wrong.** Two-thirds of the clause it
   declares non-falsifiable have a live format-gate refusal sitting in
   `packages/qmf-risk/src/qmf/risk/admission_bar.py:465-469`, falsifiable by the exact
   test pattern the author already wrote for `exit_policy` in `test_g1a_…`. An UNPROVEN
   row with a false reason is worse than a missing test: it launders a coverable gap.

---

## Wrong-expectation / hollow tests

No filed finding rests on a wrong expectation — every red is anchored to real AC text.
The defects below are the reverse failure: **greens that assert what the implementation
declares rather than what the requirement demands.**

### 1. `test_a_scaffold.py::test_a6_ungoverned_tunnel_is_open_without_a_conformance_ticket` — BANNED SHAPE (blocking)

Requirement: 11.1 AC5 — *"Given a plain-Python bot with zero qml imports, When it runs in
QMB or a research lane, Then it executes unchanged, because conformance is never required
for tunnel entry."*

The test asserts `identity["tunnel_open"] is True` and `identity["ticket_required"] is
False`. Source (`qml/src/qml/conformance/registration.py:132-142`):

```python
class UngovernedTunnelAccess:
    def fp1_identity(self) -> dict[str, object]:
        return {..., "ticket_required": False, "citation_allowed": False, "tunnel_open": True}
```

`admit_ungoverned_tunnel()` takes no argument and unconditionally returns
`Ok(UngovernedTunnelAccess())`. The assertion reads back two hardcoded literals — this is
contract rule 2's first banned shape verbatim ("asserting a module's self-declared
constants/flags/markers as proof of behaviour"). **No counter-case is constructible**
except by editing the literal in source, which rule 1 forbids. The second arm
(`cite_ungoverned_bot` refused) does exercise a function, but observes "the tunnel stayed
open" through `refused.context` — the implementation's own trace as sole observer — and
accepts *any* of four categories (`in QML_AUTHORING_CATEGORIES`), which four different
behaviours all satisfy.

**Correct disposition:** 11.1 AC5 is UNPROVEN at Epic-11 scope (the executes-unchanged
half is host-side, Epic 13/14). RESULTS.md says exactly this in its scope-honesty section
— and then still records A6 as **PASS covering 11.1 AC5** and files no UNPROVEN row.
That combination is the rule-5/rule-6 failure the hardened contract exists to catch.

### 2. `test_d_footprint.py::test_d2_omitted_ad22_identity_field_is_layer1_registration_refusal` — implementation's own lookup table

The loop is driven by `AD22_IDENTITY_FIELDS` **imported from `qml.footprint`** — the same
tuple `ProducerTemplate` iterates at `template.py:221` to decide what to reject. The test
therefore checks the implementation against itself (rule 2: "calling a function against
its own lookup table"). I verified `footprint/vocab.py:44-54` currently lists exactly the
ten fields 11.4 AC2 enumerates, so the *expectation happens to be right today* — but by
coincidence, not by anchoring. Drop a field from the tuple and both the production check
and the test shrink together, staying green while the requirement is violated. The
requirement-anchored form is a **test-owned literal tuple quoted from 11.4 AC2**.
`test_x_crosscut.py::test_x3_…` inherits the same coupling at its first assertion.

### 3. `test_f_bot.py::test_f3_confluence_set_is_one_or_more_ordered_by_child_fingerprint` — passes without any sorting

`assert order == sorted(order)` over a two-element list built from `a_confluence("alpha")`
and `a_confluence("omega")` in that order. If the implementation simply preserved input
order and those two fingerprints happen to hash ascending, the assertion holds and the
"canonically ordered by child fingerprint ascending" clause (11.6 AC3) is unproven. There
is no reversed-input arm and no non-vacuity companion — unlike E3/E4/D6, which the same
author *did* equip with one. A reversed-input arm (`confluence_set=[c2, c1]` yielding the
same ascending order) would make it falsifiable.

### 4. `test_e_confluence.py::test_e3_default_ordering_is_fingerprint_ascending_ordinals_excluded` — proves order-*insensitivity*, not *ascending*

`fp_a == fp_b` proves the display ordinal and input order are outside identity — real and
valuable. It does not prove the canonical order is fingerprint-**ascending**; and the
supporting `"display_ordinal" not in default.identity_legs()[0]` reads the
implementation's own identity projection. Partial coverage of 11.5 AC3.

### 5. Minor self-observation (noted, not blocking)

- `test_b4…`: `missing.context.get("journal") is True` — "journaled" observed through the
  refusal's own payload. There is no other surface in a pure library, so this is
  acceptable; it should have been *named* as an observation limit.
- `test_d2…`: `refused.context.get("layer") == 1` — same shape for "Layer-1".
- `test_b2…`: `constraint_powers() == {}` is a self-declared marker; the test is rescued by
  its `validate_family_body(...)` → `policy rejection` arm, which is real behaviour.
- `test_f6_occurrence_facts_never_mint_a_new_bot`: asserts `seat`/`paper`/`rebinding` payload
  keys are *refused*. That is a proxy for "re-binding, seat assignment and paper flips never
  mint a new Bot" (11.6 AC5), not the proposition itself — no test performs a re-binding and
  shows fp1 unchanged. Defensible operationalization; worth a note.
- `test_f1…`: proves two `stable_id`s are equal and no header key is in the payload. It never
  asserts the AC1 sub-clause *"the stable id is **derived from** the fingerprint"* — i.e.
  `stable_id == fingerprint_content()`.

---

## Missed requirements (Epic 11 ACs no test covers)

Ordered by consequence. Only items 6, and partially 9, appear anywhere in RESULTS.md's
scope-honesty section; the rest are silent narrowing.

| # | Requirement (epics.md) | Status |
|---|---|---|
| 1 | **11.7 AC1** — the two `admission_bar.evidence_requirements` fields (`registered_conformant_bot_cite`, `canonical_assignment_evidence`) | **No test.** Mislabelled non-falsifiable by E11-F04 — see below. |
| 2 | **11.7 AC4, 2nd `And`** — *"the two new admission-bar fields land **only through this mint**, never as a silent AD-30 field addition an old parser would ignore and thereby admit the very evidence they exist to refuse"* | **No test.** Named in the author's own PLAN.md G4 row; dropped from the executed G4 with no UNPROVEN row. |
| 3 | **11.4 AC3** — the **transitive** half: *"a footprint plus **every cited confluence's leg producer bindings** and **any bot-direct producers** … the transitive union"* (also CT-33 schema `footprint.producer_bindings`) | **No test.** D3 passes bare `ProducerBinding`s as `confluence_legs`, `bot_direct=()`, and no `catalog`. `compute_transitive_union`'s child-confluence recursion, catalog resolution, acyclicity refusal (`manifest.py:522-548`) and the `bot_direct` merge are entirely unexercised. |
| 4 | **11.1 AC5, 2nd `And`** — *"the `.qml` DSL and its Monaco surface are not revived in V1"* (DEC-0172) | **No test.** Statically checkable in one assertion. |
| 5 | **11.2 AC1, 2nd `And`** — *"qml adds no `qml_*` configurable row and no version pin to the registry"* | **No test.** B1 checks the record body only. |
| 6 | **11.2 AC3** — *"the family-scoped paper starting balance, the per-family bench threshold"* | **Only the `ExitLogicRef` arm tested** (B3). The other two per-family variables the AC names are untested and unrecorded. |
| 7 | **11.1 AC3** — *"pyright-strict and the Tier-2 isolated-environment import check run"*, and the positive *"qml imports qmf-core, qmf-registry, and qmf-risk **only**"* | **Partially tested.** A4 asserts only the *absence of `qmf.venue`*; an `import qmf.data` or an undeclared third party passes A4 unnoticed. (I enumerated every import in `qml/src/qml`: the tree currently complies, so **no finding** — but the assertion does not enforce the requirement.) pyright-strict: no test, no UNPROVEN row. |
| 8 | **11.1 AC1** — *"installs as one wheel **outside the seven-package roster**"* | **No test.** `packages/` holds exactly seven; `qml/` sits outside it. One assertion. |
| 9 | **11.6 AC6** — *"the gapless per-`(writer, kind)` sequence"* | **No test.** F7 registers a first record at `sequence=7` and it succeeds. Arguably host-owned and therefore correctly out of qml's scope — but that judgement is nowhere recorded. |

---

## findings.csv — per-row verdict

### E11-F01 (11.1 AC2, low) — **GENUINE VIOLATION**

`src/qml` ships `host/` and `logic/` beyond AC2's named seven. Verified: the src homes are
`conformance, declaration, families, footprint, host, logic, protocol`. The AC says
*"contains **exactly** the module homes …"*, so the test asserts the requirement, not the
code. Two caveats the finding text already carries and I confirm:
`docs/components/qml.md:112` calls the module list *"the spine's structural seed … the seed
of intent, not a build authorization (DEC-0184)"*, and Story 11.3 mandates a logic-identity
home the AC list omits — so `logic/` reads as a **defect in the AC's list**, while `host/`
is the substantive half and shares a root cause with E11-F02. Severity `low` is right;
this wants an operator ruling on the AC text, not a code change.

### E11-F02 (11.1 AC4 / AD-15, medium) — **GENUINE VIOLATION** (severity if anything under-rated)

Verified at source. `qml/src/qml/host/runner.py` imports `subprocess`, `os`, `tempfile`,
`json`, `uuid` and calls `open()`; `qml/src/qml/host/worker.py` is a spawned child entry
point. `qml/src/qml/host/__init__.py`'s own docstring concedes: *"This package is impure:
it owns stdlib process spawning and isolation."* Independently corroborated by the ratified
docs, which are unambiguous: `docs/components/qml.md:52` — *"The library is pure per AD-15
(no threads, no I/O, no process spawning); every impure step lives at a host composition
root (DEC-0171)"* — and the Hosting seed at `:126` places the conformance sandbox runner at
**QMB's** composition root, not inside the qml distribution. AC4's own wording (*"scans
**any** qml module"*, *"sandbox execution is **left to** a host composition root"*) is
falsified by a module that ships in the qml wheel. Correctly filed, correctly reasoned.

### E11-F03 (11.4 AC5, medium) — **GENUINE VIOLATION**

Verified at source. `Footprint.try_create` (`manifest.py:241-266`) collects `**rejected`,
refuses `FORBIDDEN_HORIZON_FIELDS`, then refuses **any remaining extra** with the message
*"the stream set is nested here, never a second top-level field"*.
`Footprint.try_from_mapping` (`manifest.py:268-300`) checks only `FORBIDDEN_HORIZON_FIELDS`
and `stream_set` presence, then reads exactly three keys and **silently drops everything
else**. The asymmetry is real, and it is reachable: `report_completeness` routes any
non-`Footprint` input through the permissive path (`manifest.py:593`). Severity `medium`
is defensible — the built footprint is still the declared one, so the failure mode is a
silently ignored authoring field, not a corrupted identity.

### E11-F04 (11.7 AC1, low) — **WRONG: UNPROVEN recorded on a false reason**

The row declares all of AC1 *"not runtime-falsifiable without a format-1 reference schema
to diff against"*. That is true **only of the trailing "and nothing more"** clause. AC1's
first and most consequential enumerated addition — the two `admission_bar.evidence_requirements`
fields — is falsifiable *today*, by the identical pattern the author already wrote in
`test_g1a_exit_policy_catch_all_lands_only_through_the_format2_mint`. The gate exists in
source at `packages/qmf-risk/src/qmf/risk/admission_bar.py:452-482`:

```python
if not isinstance(registered_conformant_bot_cite, bool): ...
if not isinstance(canonical_assignment_evidence, bool): ...
if (registered_conformant_bot_cite or canonical_assignment_evidence)   # :465
    ...
    "registered_conformant_bot_cite and canonical_assignment_evidence land only "  # :469
```

Counter-case, concrete: build a format-**1** `AdmissionBar` with
`registered_conformant_bot_cite=True` → must refuse; build the format-**2** one → must
carry it. That is the whole of 11.7 AC4's second `And`. **Correct disposition:** narrow the
UNPROVEN to the *"nothing more"* clause alone and test the two evidence fields green.

### E11-F05 (11.7 AC2, low) — **UNPROVEN correctly recorded, reason weak / narrowing avoidable**

Honest disclosure and correctly filed as UNPROVEN rather than dressed as green — that is
the contract working. But the stated blocker overstates the cost.
`EntryIntent.try_create` (`packages/qmf-risk/src/qmf/risk/door.py:583-591`) needs four
positional values (`Instrument`, `Direction`, `ReasonCode`, `ExecutionTarget`), and the
assertion is one line: `fp1_identity()` carries `advisory_stop_proposal` **only when
present** (`door.py:668-669`), and its absence never blocks
(`_require_advisory_stop_proposal` returns `None` on `None`, `door.py:674-677`). This is
fixture work, not an unprovable requirement. Accept the row; re-classify the reason as
*narrowed, avoidable* rather than *structurally blocked*.

### E11-F06 (11.7 AC3, low) — **UNPROVEN correctly recorded, reason weak / narrowing avoidable**

Same disposition as E11-F05, same blocker, same avoidability. The CT-22 half being proven
via G3a and the newer-than-reader direction via G4 is correctly credited; only the
CT-23-intent direction is open.

**Tally:** 3 genuine violations · 0 findings resting on a wrong expectation ·
1 wrongly-reasoned UNPROVEN (F04) · 2 correctly-recorded-but-avoidable UNPROVEN (F05, F06).
Missing from findings.csv: an UNPROVEN row for 11.1 AC5 (hollow green, §1 above), and rows
for items 2–8 of the missed-requirement table.

---

## Gate re-assessment

- **R-009 (refusal-register conformance): GREEN, and I concur.** X1/X2 collect real
  door-reachable refusals and assert set-membership against the seven-category register
  and equality against the four categories CT-33 §`enums.refusal` and CT-34 §`enums.refusal`
  actually declare — I verified both contract lines (`ct-33-bot-definition.yaml:67`,
  `ct-34-confluence.yaml:51`). The four-member set is test-owned and contract-anchored, and
  X2 carries a non-vacuity equality so the battery cannot pass by emitting nothing.
- **R-011 (`footprint/_coerce.py` pinned by requirement): GREEN on what it covers, but
  narrower than claimed.** D1/D2/D6/X3 do drive public surfaces only, and the totality,
  injectivity and order-stability properties are genuine. Two qualifications: D2's field
  list is the implementation's own tuple (§2 above), and the `_coerce` paths reached
  through `compute_transitive_union` — the recursion, catalog lookup and cycle refusal —
  are untouched (missed-requirement #3). The un-measurable branch-coverage number is
  correctly disclosed with a reproduced cause; that disclosure is sound and I do not
  dispute it.

---

## Single most important gap

**Story 11.7's two `admission_bar.evidence_requirements` fields (AC1) together with AC4's
"land only through this mint" clause.** It is the worst of the set on every axis: it is
named twice in epics.md and once in the author's own PLAN.md G4 row; it is the clause whose
failure is spelled out in the requirement itself — *"a silent AD-30 field addition an old
parser would ignore and thereby **admit the very evidence they exist to refuse**"* — i.e.
unqualified evidence reaching the live-money admission bar; the refusal that proves it is
already sitting in source at `admission_bar.py:465-469`; and the author had already written
the exact test shape for `exit_policy` twelve lines earlier in the same file. Instead it was
recorded as non-falsifiable under E11-F04. **Runner-up:** 11.1 AC5 reported green off two
hardcoded literals (§1) — the one place in this suite where the tier-1 hollow-green pattern
survived.
