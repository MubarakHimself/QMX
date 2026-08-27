# L6 REQUIREMENTS-FIDELITY REVIEW — Epic 10 (qmf-risk)

- Reviewer scope: one question per test — does it assert what the requirement demands, or what the
  implementation happens to do? Plus: which Epic-10 requirements has no test touched?
- Inputs read: `PLAN.md`, `RESULTS.md`, `findings.csv`, all 11 files under `qa/tests/epic_10/`,
  Epic 10 §`epics.md` lines 1958–2282 (Stories 10.1–10.10, ~60 ACs).
- Authority note: `test-design-qa.md` and `QMX-handoff.md` are confirmed absent from this worktree
  (`_bmad-output/` contains `planning-artifacts/` only). The PLAN's Section-7 blocked-input record is
  accurate and honest. Gate rows R-001/R-009 and assertions P0-8/P0-9 are taken from the task prompt,
  as the PLAN did.
- No test was run, edited, or re-reviewed as source. Two source facts were verified by targeted
  reading because the tests' fidelity turns on them; both are cited below.

---

## VERDICT: **gaps**

The suite is well-built and mostly requirement-anchored. Clusters F (door), G (exit records), I
(windows, except AC4), and J2/J4/J6 are genuinely strong: they exercise real evaluators, derive
expectations from requirement text, and would fail if the implementation drifted.

But the verdict cannot be `adequate`, for one reason that outweighs the rest:

> **P0-9 — the exit-preservation invariant, the epic's own highest-damage requirement — is not
> tested at all.** Every P0-9 assertion calls one orphan helper that no code path in the package
> uses. The suite reports P0-9 GREEN. Nothing in the suite entitles it to.

A T1 audit returning 107/107 pass and a zero-row `findings.csv` is exactly the signature this review
exists to catch. The clean sheet is not evidence that `qmf-risk` is clean; it is evidence that the
two cross-cutting gates (P0-9, R-009) were mechanized as assertions that cannot fail.

---

## 1. Wrong-expectation tests

Ranked by damage. "What the requirement says" quotes Epic 10 `epics.md` unless noted.

### 1.1 `test_H1_exit_preservation_never_blocks_a_risk_reducing_act` + `test_H1_entries_are_the_only_blockable_half` — **CRITICAL**

*File:* `qa/tests/epic_10/test_h_control_action.py:113-134`. Also implicated: `test_x_cross_cutting.py:144`
(the L39 capture in X1) and `test_X4...` step 4.

**Why it is wrong.** Three defects compound:

1. **The property has three dead parameters.** The test is declared
   `@given(kind=..., authority=..., scope=..., act=...)` over
   `ControlActionKind × AuthorityKind × SubjectScope × RiskReducingAct`, and RESULTS.md advertises it as
   "Hypothesis property over kind×authority×scope×act". The body is:
   ```python
   result = check_exit_preservation(blocked_act=act)
   ```
   `kind`, `authority` and `scope` are never referenced. The function's real signature is
   `check_exit_preservation(*, blocked_act: object)` (`control_action.py:347`) — it accepts **one**
   argument and has no notion of a control kind, an authority, or a scope. The 200 Hypothesis examples
   explore exactly 6 distinct calls (`len(RiskReducingAct)`), which the sibling deterministic test
   already covers by looping `RISK_REDUCING_ACTS`. The advertised space is not searched. It cannot be.

2. **The assertion is a tautology.** `check_exit_preservation` returns a policy rejection iff its
   argument coerces to a member of `RiskReducingAct`, and `RISK_REDUCING_ACTS` is literally
   `frozenset(RiskReducingAct)` (`control_action.py:215`). The test feeds it members of that enum and
   asserts it rejects them. This asserts `x ∈ S ⟹ x ∈ S`. It is a lookup against its own table.

3. **The guard is an orphan — this is the load-bearing point.** A repo-wide search for
   `check_exit_preservation` across `packages/qmf-risk/src` returns only its definition, its two
   `__all__`/re-export listings, and a docstring mention. **No control path calls it.** Not
   `arbitrate_same_tick`, not `EnforcementScope`, not `mint_control_action`, not
   `resolve_execution_target`. It is an exported advisory helper that any control path may simply
   decline to consult.

**What the requirement actually says** (Story 10.8 AC1, L39, CT-30, SCN-0010):

> **Given** the exit-preservation invariant, **When** any control action of any authority at any scope
> **is applied**, **Then** it may never block a risk-reducing act — cancel_order, close_position,
> close_all, a risk-non-increasing amend_protection, a protection action, or the recording of evidence
> — the blocking half of any control is **entries only** in paper and live alike…

The requirement is quantified over **applied controls**. It is a property of the enforcement path. The
test is a property of a validator that the enforcement path does not call. The correct assertion shape
is: put a control in force, propose each risk-reducing act, and assert the act is **not** withheld.

**The concrete missing assertion, and why it is not hypothetical.** The package *does* contain a path
that withholds acts under an active control: `resolve_execution_target`
(`paper.py:435`). Its signature is act-blind —
`(book_mode, seat_state, active_controls, live_target, paper_target)`, with no intent-family or act
parameter — and its own docstring states the precedence: *"A `blocks-paper` control dominates — a
market-risk control (a protection window, the kill switch) blocks live and paper alike; the outcome is
`BLOCKED`."* `test_E5` confirms this returns `RoutingOutcome.BLOCKED` in practice. Because the function
cannot see what kind of intent it is resolving, the question "does an exit survive an active
blocks-paper control?" is decided entirely by whether exits reach this function — and **no test in the
epic asks.** (`ExitIntent` — `door.py:770` — carries no `execution_target`, unlike `EntryIntent`, so the
answer is one of two findings, not zero: either exits route here and are blocked, which is a live L39
violation; or exits never resolve a target at all, which leaves CT-24 AC2's per-intent execution target
entry-only and unspecified for the exit half.)

**Consequence for the report.** P0-9 must be recorded as **UNPROVEN**, not GREEN, in RESULTS.md.

### 1.2 `test_X1_every_door_reachable_refusal_is_on_the_register` — vacuous (gate R-009)

*File:* `test_x_cross_cutting.py:115-154`.

The test collects refusal categories from 13 hand-picked calls into `emitted`, then asserts
`emitted <= register`. But `X2` (line 100-109) asserts `register == {every member of RefusalCategory}`.
`RefusalCategory` is a closed Python enum, so **every refusal the package can physically produce is
already in `register`**. `emitted <= register` is unfalsifiable — no choice of doors, and no future
source change short of deleting a register entry, can make it fail.

**What the requirement says** (R-009, CT-04): *every **door-reachable** typed refusal has a register
entry* — i.e. the claim has a coverage half ("we enumerated the doors") that the test does not
discharge. The 13 chosen calls are a spot-check with no completeness argument; the PLAN's own X1 wording
("no door emits an off-register category") is guaranteed by the type system, not by this test.

R-009 is in truth satisfied *structurally* (single closed enum, asserted equal to the register by X2).
That is a legitimate finding — but it should be stated as such. X1 as written adds nothing and its
GREEN reads as coverage evidence it does not provide.

### 1.3 `test_B3`, `test_B4`, and `test_X4` step 4 — tautological freeze checks (P0-8)

*Files:* `test_b_r_faces_sizing.py:190-212`; `test_x_cross_cutting.py:321-327`.

Each has the identical shape:
```python
faces = _faces()                      # or RFaces.try_create(...)
amount_before = faces.original_risk_amount
amended = derive_original_risk_distance(...)   # faces is NOT passed in
assert faces.original_risk_amount == amount_before
```
The function under test never receives `faces`. A frozen dataclass is asserted to be unchanged after a
call that could not have reached it. These assertions hold for any implementation, including one that
re-bases R on every stop move through a different entry point.

**What the requirement says** (Story 10.2 AC1): *both money-bearing faces are frozen at admission and
**never re-based by** a stop move, a protection amendment, or a budget re-derivation.* The demanded
assertion is over an **admitted position's lifecycle**: admit → apply a stop move / protection
amendment / budget re-derivation *to that position* → re-read its faces. `test_B2` gets closest (it does
re-derive from the admitted values) but still only compares a free-function result against the
untouched object.

**Aggravating seam gap.** The epic has two disjoint admission entry points: `admit_entry_intent`
(`door.py`, exercised by F3/X4) and `admit_entry_r_faces` (`r_faces.py`, exercised by B2/B13). The door
path yields `original_risk_distance` but the tests never show it yielding a frozen
`original_risk_amount` — X4 has to *fabricate* one (`RFaces.try_create(record.original_risk_distance,
_usd(50_000))`, line 322) with a literal that comes from nowhere in the admission. So the X4
"lifecycle" test does not actually carry the money-bearing face through the door. P0-8's money half is
proven only on a function the door path is never shown to call.

### 1.4 `test_H5` and `test_J3` — "before" is never observed

*Files:* `test_h_control_action.py:190-193`; `test_j_journal_performance.py:215-218`.

Both prove storage-failure-blocks-dispatch by **passing the failure in as an argument**:
`journal_before_dispatch(record, journal_result=unpersistable("disk full"))`. A function handed a
failure returns a failure. Neither test observes ordering, and neither uses the injected sink the PLAN
specified for these two IDs ("L3 — integration (composition-root fakes) … storage-failure-blocks-dispatch").

**What the requirement says** (10.8 AC3 / 10.10 AC3, CT-25): *a control action **is journaled before
dispatch**… a storage failure **blocks the dispatch** rather than losing the intent.* The demanded
assertion is a happens-before: a fake journal + a fake dispatcher recording call order, asserting the
dispatcher is never reached when the journal fails, and that the journal write precedes it when it
succeeds. As written, an implementation that dispatched first and journaled afterwards would pass both
tests.

### 1.5 `test_I4_narrowing_revision_is_accepted_but_never_shrinks_the_effect` — asserts an intake choice the AC does not make

*File:* `test_i_control_window.py:242` — `assert is_ok(second)  # intake never refuses a narrowing revision`.

AC4 constrains **enforcement** (*"enforcement is widen-never-shrink and forward-only… the effective
window at a decision instant is a read-time union fold"*). It is silent on whether a narrowing revision
is accepted or refused at intake; refusing it at intake would satisfy the AC equally. The fold half of
the test is correct and valuable; the `is_ok(second)` line pins an implementation decision as though it
were required.

### 1.6 `test_E7` — refusing a signature on a mechanical clear is not required

*File:* `test_e_paper.py:251-253`.

Asserts `authorize_return_to_live(CLOCKED_MECHANICAL, operator_signature="op")` is a **refusal**. AC6
says return to live *"is automatic only where the clearing cause is clocked and mechanical (minting a
CT-24 transition, never a CT-30 resume); anything touching real money requires an operator signature."*
It constrains what may happen **without** a signature. Nothing in it makes a supplied signature an
error. Defensible design; not a requirement.

### 1.7 `test_C4` and `test_H2` — purpose-built rejecters asserted against themselves

*Files:* `test_c_admission.py:265-274`; `test_h_control_action.py:140-146`.

C4's first half passes `comparison="weighted-aggregate"` to `AdmissionRequirement.try_create` — that is
ordinary enum validation (any non-member string refuses), not a statement about composites. Its second
half calls `reject_bar_aggregate("composite-score")`, a helper written to reject those four strings.
H2 has the same shape with `reject_blanket_command_pipe_block`.

**What the requirements say** (10.3 AC2: *no composite score, rating, tier band, or weighted aggregate
**may express a bar***; 10.8 AC1: *no kind **whose effect** is a blanket command-pipe block may ever be
minted*). Both are structural claims about what can be *expressed*, and both would be better asserted
structurally — e.g. that `AdmissionBar` exposes no aggregate/score field and that a multi-requirement
bar cannot collapse to a single number; that each of the four `ControlActionKind`s has a bounded,
non-universal effect. Rejecting a string by name does not establish either. (Lower severity: the closed
vocabularies do most of this work already.)

### 1.8 `test_E2` — fail-closed-to-PAPER on an empty stream

*File:* `test_e_paper.py:136-140`. Sensible and safe, but no AC states that an empty CT-24 stream folds
to PAPER with `fail_closed=True`. Lowest severity; listed for completeness.

---

## 2. Missed requirements (in this epic's `epics.md` section, no test covers)

Ordered by story. "Partial" = the AC has a tested half and an untested half.

| # | Story / AC | Requirement text not covered by any test | Severity |
|---|---|---|---|
| M1 | **10.8 AC1** | The invariant *as applied* — no test puts a control in force and proposes a risk-reducing act. See §1.1. | **Critical** |
| M2 | **10.8 AC5** | *"colliding actions collapse to one command with **the rank winner supplying authority and reason**"* — H7 asserts 1 emit + 2 suppressed but never asserts **which** action won or that the survivor carries the rank winner's authority and reason. Half of AC5 untested. | High |
| M3 | **10.9 AC4** | *"…never **retro-invalidate a window that has had effect**… a read-time union fold **with passed bounds frozen**"* — I4's generator forces every bound into the future (`start = min(a,b) + 10_000`, `decision_at = 101`). No test revises a window whose bound has already passed. The freeze half is untested. | High |
| M4 | **10.10 AC4** | *"a fingerprinted population (binding-record fingerprints, **never intervals**)"* — J5 builds a valid population; no test asserts an interval-based population is refused. The load-bearing prohibition is untested. | High |
| M5 | **10.3 AC1** | *"Layer 2 technical shakedown **on a demo/paper binding**"* — `run_layer2_shakedown` is imported at `test_c_admission.py:43` and **never called**. No test asserts a LIVE shakedown role refuses. Also untested: the Layer-3 page carries **both proofs** (C1 checks only `binding_identity` and `signer_identity`). | High |
| M6 | **10.4 AC1** | *"a Bot binds exactly one Book, a Book binds exactly one BMS at a time, and one BMS per account serves many Books"* — three cardinality rules, none tested. D1 covers only the tuple's shape. | High |
| M7 | **10.8 AC3** | *"…**never time-expiring**"* — no test advances time and asserts a standing intent survives. | Medium |
| M8 | **10.9 AC5** | *"a standing per-instrument exemption is a **dated fingerprinted record consumed at compile time**"* — I5 asserts the click-exemption is rejected but never exercises the legitimate dated-record exemption path. | Medium |
| M9 | **10.9 AC6** | *"widths, anchors, and buffers are **configurable UI-editable variables with no spine value**"* (L38/FR-035) — I6 covers rank 2 and the V1 default only. | Medium |
| M10 | **10.5 AC5** | *"the starting balance is a **configurable UI-editable default** frozen at flip"* — E6 covers currency/sign validation and the signed reset, but never asserts the balance is a UI-editable template variable with no spine value. | Medium |
| M11 | **10.1 AC4** | *"accounting_currency is declared **so a later currency is a version change**"* — no test shows changing `accounting_currency` mints a new version / changes fp1. | Medium |
| M12 | **10.1 AC5** | *"**supersedes stays linear** elsewhere"* — A11 covers `branches-from`, multiple heads, the dated `current` pointer and readability; the linear-supersedes rule is untested. | Medium |
| M13 | **10.2 AC5** | *"it comes **only from venue instrument-metadata snapshots** as an exact rational"* — B13 covers absence→`unavailable dependency`; provenance is untested (any `ValueFactor` is accepted regardless of origin). B14's margin ban is asserted only as "a string is not a ValueFactor". | Medium |
| M14 | **10.8 AC4** | *"…**escalating automatically** and de-escalating only by a human"* — H6 covers de-escalation (resume operator-only) and scope; automatic escalation is untested. | Medium |
| M15 | **10.4 AC6** | *"the operator signs the shared-flatten limitation (**an identity field of the binding**)"* — D9 asserts the field echoes its value; it never asserts the signature enters the binding's identity/fingerprint. | Low |
| M16 | **10.4 AC2** | *"a Book version **is template fp1**"* — D2 covers the instance and epoch legs of the trinity; the version leg is not asserted. | Low |
| M17 | **10.10 AC6** | *"one governed producer **published once**"* — J7 asserts publish/consume share a fingerprint; single-publication (a second publish refuses) is untested. | Low |
| M18 | **10.5 AC3** | *"(**re-pointable by a superseding dated record**)"* — E4 asserts a second target without a supersedes edge refuses; the successful re-point is untested. | Low |
| M19 | **10.7 AC5** | AC is keyed on *"a later intent… on the same **(Book, Bot) seat**"*; G6 keys on `closed_virtual_position_ref` instead. Seat-scoped behaviour untested. | Low |

**Requirement tension worth surfacing (not a test defect).** `test_F5` accepts an arbitrary tighten
(500→300 is `is_ok` via `check_stop_not_widened`), while `test_G7` refuses the same shape (50→25 via
`check_move_to_breakeven_ratchet`). Both match their own AC — 10.6 AC3 admits
`tighten_protective_stop` generally; 10.7 AC6 says *"V1 dynamic SL/TP is the move-to-breakeven ratchet
only."* The tests correctly encode a contradiction that lives in the requirements. Worth an operator
ruling, not a code fix.

---

## 3. `findings.csv` row-by-row adjudication

`findings.csv` contains **its header line only — zero rows**. There is therefore nothing to classify as
genuine-violation vs wrong-expectation:

- Confirmed genuine requirement violations: **0**
- Wrong test expectations among filed findings: **0**
- Rows total: **0**

**The empty file is itself the review's finding.** A zero-row `findings.csv` from a T1 audit is only
credible if the assertions could have failed. At the two cross-cutting gates they could not:

- **P0-9** was mechanized against an orphan helper's own lookup table (§1.1) — unfalsifiable.
- **R-009 / X1** was mechanized as `emitted <= register` where `register` is asserted equal to the
  closed enum every refusal is drawn from (§1.2) — unfalsifiable.
- **P0-8's freeze half** was mechanized as "a frozen object is unchanged after a call it was not
  passed to" (§1.3) — unfalsifiable.

The remaining ~90 tests are genuinely falsifiable and their passes are real evidence. The RESULTS.md
claim that *"the `qmf-risk` package satisfies the requirement-derived assertions for Epic 10, including
the two P0 invariants and both risk-gate rows"* is not supported for P0-9, and is supported for R-009
only in the weaker structural sense.

### Corrections owed to RESULTS.md

| Row | Currently | Should read |
|-----|-----------|-------------|
| P0-9 | GREEN — "Hypothesis property over kind×authority×scope×act" | **UNPROVEN** — asserted against an uncalled helper; three property dimensions are dead parameters |
| R-009 | GREEN — X1, X2 | GREEN **structurally (X2)**; X1 is vacuous and adds no coverage evidence |
| P0-8 | GREEN — B2,B3,B4,B6,F1,F3,X4 | **PARTIAL** — full-loss-price half is solidly green (B6, F1, F3, X4); the frozen-money-face half rests on B3/B4/X4§4, which are tautological, and never traverses the door path |
| Reconcile note | "no untethered high-complexity branch was observed" | `check_exit_preservation` is dead code within the package — an exported requirement guard with no caller. That is precisely an untethered-complexity finding and should be filed. |

### Findings that should exist in `findings.csv`

Derived from this review, for the parent to route (severities are this reviewer's):

| id | requirement_ids | severity | description |
|----|-----------------|----------|-------------|
| F-10-01 | 10.8 AC1, CT-30, L39, P0-9 | **critical** | `check_exit_preservation` has no caller in `qmf-risk`; the exit-preservation invariant is enforced nowhere. Expected: every control-application path consults the guard before withholding an act. Observed: an exported orphan helper. |
| F-10-02 | 10.8 AC1, CT-24 AC2, L39 | **high** | `resolve_execution_target` withholds acts under an active `blocks-paper` control but takes no intent-family parameter, so it cannot distinguish an exit from an entry. Either exits are blocked (L39 violation) or exits resolve no execution target at all (CT-24 AC2 gap). Untested either way. |
| F-10-03 | 10.8 AC5, SCN-0010 | high | Collapse does not verify the rank winner supplies authority and reason. |
| F-10-04 | 10.9 AC4, CT-31 | high | "Passed bounds frozen" / no retro-invalidation is unexercised; the property generator confines every bound to the future. |
| F-10-05 | 10.10 AC4, CT-32 | high | Interval-based populations are never shown to be refused. |
| F-10-06 | 10.3 AC1 | high | Layer-2 shakedown is never invoked; the demo/paper-binding constraint is untested. |
| F-10-07 | 10.4 AC1, CT-28 | high | The three binding-cardinality rules are untested. |

---

## 4. What the suite gets right

Recorded so the verdict is not read as a blanket dismissal. These clusters assert the requirement, not
the code, and would catch real drift:

- **F1–F7 (door, Story 10.6).** The strongest cluster. F3 drives a real door-side module, proves the
  price is *derived* (105000−500) and that `requested_r` is Book-resolved and distinct from the bot's
  `proposed_r`; F1 asserts structurally that `EntryIntent` carries no `requested_r` field; F7 proves a
  format-2 field on a format-1 artifact is ignored rather than fatal.
- **G1, G2, G5 (exit records).** G2 asserts `realized_r` is *not* a stored dataclass field and that the
  method and free-function agree — a real single-source proof. G5 correctly derives the breakeven rule
  from the stamped `outcome` and probes it at q=1/1000 and q=100 ("never counts under **any** q").
- **I2, I3 (windows).** I2 exercises the real evaluator across LIVE and PAPER and checks the veto record
  carries door + would-have-been action + fingerprint. I3 proves the missing-exposure instrument is
  blocked *and* alarmed, through the real scope resolver.
- **C5, C7 (admission).** C5 is a clean blank-blocks-live proof across four roles. C7 is genuinely good:
  it injects a *wrong* producer and asserts the check fails, proving the linter uses the producer's
  output rather than local arithmetic — the exact demand of 10.3 AC5.
- **J2, J4, J6.** J2 proves a venue event carrying a Book identity is refused at construction; J4 proves
  an undeclared cross-role read refuses while a declared one carries role on every row.
- **D4, D5, D6.** The state-carry / signed-edge / edge-independence trio is precise, including the sharp
  negative that a `continues-performance` edge never unlocks a carry.
- **PLAN discipline.** Section 4 authored before any `src/` read, the absent-authorities blocked-input
  note, and the honest Section-7 untestable list are all exemplary and should be preserved.

---

## 5. Recommendation

1. **Do not accept P0-9 as discharged.** Re-run cluster H with an enforcement-path test: place a
   control in force and assert each of the six `RiskReducingAct`s survives. Start with
   `resolve_execution_target` under a `BLOCKS_PAPER` control with an exit intent (F-10-02) — that single
   test is the highest-value assertion missing from this epic.
2. File F-10-01..F-10-07 into `findings.csv`; correct the four RESULTS.md rows in §3.
3. Rewrite B3/B4/X4§4 as lifecycle assertions that carry an *admitted* position's money face through a
   stop move, a protection amendment, and a budget re-derivation.
4. Either delete X1 or re-scope it to an enumerated door inventory with a completeness argument; keep
   X2 as the structural R-009 proof.
5. Close M2–M6 (the high-severity coverage rows) before this epic's audit is called complete.
