# L6 REQUIREMENTS-FIDELITY REVIEW — Epic 14 (qmb-run-loop)

**Reviewer question, asked once per test:** does this test assert what the
*requirement* demands, or what the *implementation* happens to do?

**Inputs reviewed:** `PLAN.md`, `RESULTS.md`, `findings.csv`, and the 11 modules
under `qa/tests/epic_14/`. Authorities: Epic 14 of
`_bmad-output/planning-artifacts/epics.md` (Stories 14.1–14.8), `docs/contracts/`
(CT-04/12/16/23/29/32), `docs/scenarios/SCN-0012-qmb-replay-run.md`, and the FR/AR
rows in epics.md §FRs (FR-036, FR-037, AR-16, AR-56, AR-57, AR-58).
No test was run or edited; no source was re-reviewed beyond confirming whether an
asserted symbol is a literal constant (§2.1).

---

## 1. VERDICT: **gaps**

The suite is large (51 cases), honestly reported, and a substantial part of it is
genuinely requirement-derived — see §5. But it does not yet support the RESULTS
headline that "the run loop satisfies every independently derived requirement
test … including all eleven P0 behaviours."

Three structural problems put the verdict at `gaps`:

1. **The epic's flagship P0 guarantee is asserted only against the
   implementation's self-description.** AR-57 / AC 14.2 says the six sub-phase
   order is pinned *and* identity-bearing. The order is read from the loop's own
   `trace` / `subphase_order()` (T-14.2-a), and "identity-bearing" is proved by
   re-hashing a hand-mutated dict (T-14.2-e) without ever running the loop. See
   §3.1 — this is the single most important gap.
2. **A recurring decorative-assertion pattern.** Twelve `Final[bool]` / `Final[str]`
   compliance constants exported by the source under test are asserted directly
   (`assert FORMING_BAR_ACTIONABLE is False`, `assert PARTIAL_GOVERNED_RESULT_ON_ABORT
   is False`, …). These assert the implementation's declaration of its own
   compliance, which is the definition of asserting what the code happens to do.
3. **Whole AC clauses have no test at all** — sub-phase 2 (financing), ports
   *bound per run-config*, the CT-29 exit actually being *minted* against the
   `world=replay` binding, risk-monotonic exits, the embargo being *sourced from*
   the AD-21 split manifest, and world being *derived* rather than caller-declared
   at the run seam. See §4.

None of this contradicts the "0 findings" result — no requirement-derived test
*failed*. The correct reading is narrower than RESULTS states: **within the
behaviours actually asserted, the loop holds; a material subset of Epic 14's
requirements is not yet asserted at all, and a further subset is asserted in a
form that cannot fail.**

---

## 2. Cross-cutting fidelity problems

### 2.1 Self-declared compliance constants asserted as evidence

Confirmed by inspection of the source symbol definitions (not a code review —
only to establish that each is a literal, not a computed value):

| Constant | Definition in source | Asserted at |
|---|---|---|
| `CLOCK_DOES_NOT_CHOOSE_WORLD` | `frontier.py:37` `Final[bool] = True` | `test_e14_a_frontier.py:88` |
| `COMPLETED_BOUNDARY_ONLY` | `bars.py:84` `Final[bool] = True` | `test_e14_c_bars.py:57` |
| `FORMING_BAR_VISIBLE` / `FORMING_BAR_ACTIONABLE` | `bars.py:85-86` `Final[bool] = False` | `test_e14_c_bars.py:97-98` |
| `LOOKAHEAD_PREVENTION_INDEPENDENT_OF_GAP_0048` | `bars.py:87` `Final[bool] = True` | `test_e14_c_bars.py:127` |
| `WARMUP_ADDS_SECOND_WINDOW` / `PRESEED_IS_WARMUP` | `warmup.py:42-43` `Final[bool] = False` | `test_e14_d_warmup.py:72, 99, 107` |
| `PARTIAL_GOVERNED_RESULT_ON_ABORT` | `observe.py:51` `Final[bool] = False` | `test_e14_f_cancel_observe.py:121` |
| `CLAIMS_EDGE` / `SPENDS_SPLIT_BUDGET` | `ports.py:97-98` `Final[bool] = False` | `test_e14_e_execution.py:129-130` |

A literal `= False` in the module under test can never disagree with
`assert X is False`. These lines carry zero requirement force. They are not
individually severe — in most cases a real behavioural assertion sits beside them
(`act_on_bar` refusing, `preseed_indicator_buffers` refusing) — but two of them
(`PARTIAL_GOVERNED_RESULT_ON_ABORT`, `full_loss_before_open`) are carrying the
*whole* weight of their requirement. See §3.4 and §3.5.

The same pattern appears one level down as **self-reported fields in refusal
contexts and identity dicts**: `context["writes_ledger"] is False`,
`context["partial_governed_result"] is False`, `ident["full_loss_before_open"] is
True`, `self_assessment["evidence_covers_warmup"] is False`. The code asserts its
own conformance in a string-keyed dict and the test reads it back.

### 2.2 Ordering evidence is the loop's own trace, not observed side effects

`_e14.RecordingHandler` (the one instrument that could observe real execution
order) records into **four separate lists** — `stream_updates`, `scheduled`,
`executed`, `closed_updates` (`_e14.py:92-95`). Separate lists destroy the
interleaving. Nothing in the suite can distinguish "phase 3 ran before phase 4"
from "phase 4 ran before phase 3". A single shared, phase-tagged log would have
made AC 14.2's central claim directly observable.

Worse, `handler.scheduled` and `handler.executed` are **never asserted anywhere in
the suite** (verified by grep across `qa/tests/epic_14/`). Sub-phase 2 has no
behavioural coverage at all, and sub-phase 3 is asserted only negatively.

---

## 3. Wrong-expectation tests

Ranked by how much requirement force is lost.

### 3.1 `T-14.2-e` — `test_t142e_subphase_order_is_identity_bearing` (P0, R11)
`test_e14_b_subphases.py:86-95`

**What it asserts:** takes `loop_identity()`, copies the dict, replaces the
`"subphases"` value with a reversed tuple, hashes both, asserts the hashes differ.
`run()` is never called.

**Why this is wrong:** the assertion `fingerprint(d) != fingerprint(d')` for two
different dicts is a property of **sha256**, not of the run loop. It would pass
against a loop that ignored `loop_identity()` entirely, or one whose CT-32
fingerprint were computed from a different payload. The one genuine fact it
establishes is that `loop_identity()` *contains* a `subphases` key — it never
links that dict to the CT-32 fingerprint that `T-14.7-a` measures.

**What the requirement actually says:** AC 14.2 — "**Given** the sub-phase order,
**When** it is altered, **Then** the change is identity-bearing (a different
fingerprint), because the order is pinned spine law (AR-57, B-2)." The PLAN's own
§4 wrote the right test: "a run whose sub-phase order is altered (**via a test-only
reordered driver**) produces a different CT-32 fingerprint than the pinned order."
The implemented test dropped the reordered driver and the run. The requirement
demands a comparison of two **run outputs**; the test compares two **dict hashes**.

### 3.2 `T-14.2-a` — `test_t142a_subphase_order_is_exactly_pinned` (P0, R7)
`test_e14_b_subphases.py:31-35`

**What it asserts:** `tuple(SUBPHASES) == _PINNED` (source constant vs. hard-coded
copy of the same strings), then `out.subphase_order() == _PINNED` and
`len(out.trace) == 6`.

**Why this is weak:** both `SUBPHASES` and `out.subphase_order()` are produced by
the code under test. A loop that executed phases in the order 1,2,4,3,5,6 while
appending trace entries in the pinned order passes this test unchanged. The
strings themselves (`"frontier-advance"`, `"resting-orders"`, …) are
implementation vocabulary, not requirement vocabulary.

**What the requirement actually says:** AC 14.2 / AR-57 / SCN-0012 §Then(5) name
six *effects* in order — frontier advance + stream update; scheduled
position-level events (financing); resting-order execution through the ports;
indicator/structure update on closed data; strategy callbacks minting intents;
new intents resting. The requirement is about the order in which those **effects
occur**, observable at the handler seam. Only one ordering consequence is
independently proven anywhere in the suite (T-14.2-b: a phase-5 intent does not
fill in phase 3) — which is real and valuable, but covers one adjacency out of five.

### 3.3 `T-14.1-i` — `test_t141i_loop_is_never_forked_only_adapter_differs` (P2, R5)
`test_e14_a_frontier.py:117-130`

**What it asserts:** `run(..., clock=clock).fp1_identity() == run(...).fp1_identity()`
— i.e. a run *with* an injected clock and a run with **no clock at all** produce
identical identity; plus `dir(runloop)` contains no `run_backtest/run_replay/run_live`.

**Why this is wrong:** the equality is an invented invariant. No requirement says
two different clock bindings must produce the same fingerprint — B-2 says the
opposite in spirit: replay, backtest and live *differ* by the injected clock, and
their results are legitimately different. What the assertion actually documents is
an implementation fact: **the injected clock is optional and does not participate
in loop identity**. That fact is in tension with AC 14.1 ("time advances only
through an injected frontier clock … it reads only the injected frontier clock")
and with FR-036 ("each run consumes exactly one resolved, fingerprinted run
config") — and the test converts it into a pass.

**What the requirement actually says:** AC 14.1 — "**When** only the injected clock
and adapters change, **Then** backtest, replay, and (deferred) live share
identical loop **code** — the loop is never forked." That is a statement about
code paths, not fingerprints. The `dir()` half of the test is the right idea
(weakly executed); the fingerprint half should be replaced by an assertion that
`run()` **requires** an injected clock, or by a metamorphic check that two
*different* clock adapters traverse the same module path.

### 3.4 `T-14.6-d` — `test_t146d_abort_emits_no_partial_governed_result` (P1, R29)
`test_e14_f_cancel_observe.py:116-126`

**What it asserts:** after an aborted run — `PARTIAL_GOVERNED_RESULT_ON_ABORT is
False` (a literal), `context["partial_governed_result"] is False`,
`context["writes_ledger"] is False`, `context["writes_log"] is False`, and
`"performance_result" not in aborted.context`.

**Why this is wrong:** four of the five assertions read the implementation's own
claim that it wrote nothing. The requirement is about an *absence of writes*; the
test observes a *self-report of an absence of writes*. Only the fifth assertion
touches reality, and weakly.

**What the requirement actually says:** AC 14.6 — "**Then** the pure `run()`
returns a terminal refusal and **writes nothing** — no partial governed result is
emitted (B-4)." SCN-0012 §Then(7) is explicit that the pure `run()` "returns the
canonical result … and writes nothing", with the ledger line owned by the
orchestrator. The honest assertion is an *injected sink* (ledger sink, log sink,
output dir) that records every call and is asserted empty after the abort — the
same technique the suite already uses successfully for the poisoned clock
(T-14.1-g). That test proves a negative properly; this one does not.

### 3.5 `T-14.5-a` — `test_t145a_inbound_is_ct23_intent_never_bot_sized_order` (P1, R21)
`test_e14_e_execution.py:47-58`

**Two distinct problems.**

(a) **Full-loss-before-open is asserted as a metadata flag.**
`assert ident["full_loss_before_open"] is True` reads a key out of
`ports_identity()`. AR-56 and CT-23 demand behaviour: "An admitted entry must
resolve to a declared full-loss price: **no price → no original_risk_distance → no
admission**"; AC 14.5 — "an AD-40 full-loss price is required before any open."
The requirement is that an open **is refused** without the price. RESULTS §Blocked
already concedes the enforcement lives in `qmb/execution/risk.py` and was not
exercised — so R21's second half is untested, and the flag assertion papers over it.

(b) **No positive-admission case exists anywhere.** All three
`require_authorized_intent` calls pass junk — a bare dict, the string
`"eurusd@2.0"`, and `None` — and assert refusal. A `require_authorized_intent`
that refused *every* input, including a valid CT-23 Book-resolved EntryIntent,
passes this test. The requirement is a discrimination ("a CT-23 Book-resolved
authorized intent **or** a typed refusal"); the test only exercises one side of it.
`assert "EntryIntent" in named and "ExitIntent" in named` checks a source string
list, not admission.

### 3.6 `T-14.5-c` — `test_t145c_one_ct29_exit_per_close` (P1, R23)
`test_e14_e_execution.py:101-124`

**What it asserts:** one call to `record_virtual_close` with **every CT-29 payload
field set to `None`** and `closed_refs=(ref,)` — i.e. the caller hands in the
already-closed set — returns a `POLICY_REJECTION`.

**Why this is partial to the point of misleading:** the test proves a duplicate
close is refused *when the caller tells the function the position is already
closed*. It never mints a first exit record, so "exactly one CT-29 exit record"
has no positive assertion; and with all fields `None`, nothing about the record's
CT-29 shape (frozen `original_risk_distance` / `original_risk_amount`,
`close_reason` from the AD-33 taxonomy, `result_label`) is checked. PLAN §6's own
rule — "CT-23/CT-29/CT-32 fakes are shape-faithful to the ratified contracts … a
test that passes against a shape-unfaithful fake is itself a finding" — is
violated here by the test's own standard.

**What the requirement actually says:** AC 14.5 — "**Given** every virtual-position
close, **When** it occurs, **Then** exactly one CT-29 exit record is minted
**against the run's `world=replay` binding**, and bot-proposed exits are
risk-monotonic — risk-reducing only (CT-29, FR-032)." Three clauses; the test
touches a corner of one. The `world=replay` binding clause and the risk-monotonic
clause are covered in §4.

### 3.7 `T-14.2-f` — `test_t142f_order_violation_is_unrepresentable_or_refused` (P0, R11)
`test_e14_b_subphases.py:99-121`

The first half is good and requirement-shaped: `"subphase"`/`"order"` are not
parameters of `run()`/`run_slice()` — the order is not runtime-supplied, which is
exactly "pinned spine law". The second half constructs the **private** `loop_mod._Acc`
and calls the **private** `loop_mod._run_one_phase("bogus-out-of-order-phase", …)`.
No requirement mentions a phase-name dispatcher; this asserts an internal design
choice. It is not *wrong*, but it is implementation-shaped, and it is fragile in
the way L6 exists to flag: a refactor that inlines the dispatcher breaks a test
without any requirement changing.

### 3.8 Minor: assertions with no requirement content

- `test_e14_c_bars.py:118` — `assert isinstance(sample.price, int)` inside the
  same-series test (R14). The fixture built those prices (`_e14`/`_series`); this
  asserts the test's own data.
- `test_e14_d_warmup.py:45` — `out.warmup.embargo.unit == WARMUP_UNIT` compares a
  source constant to itself. (T-14.4-c:71 pins the literal `"observation-count"`,
  which is the assertion that carries the requirement.)
- `test_e14_f_cancel_observe.py:63` — `refused.context["cancel_at"] == CANCEL_AT ==
  "slice-boundary"`: the chained literal is fine; the `CANCEL_AT` term is redundant.
- `test_e14_c_bars.py:28` imports `readable_bars` and never uses it in that module.

---

## 4. Missed requirements — Epic 14 ACs with **no** covering test

Each row cites the epics.md clause that is unasserted. These are *in addition to*
the four blocked Story 14.8 scaffolds, which are legitimately deferred (with one
exception, §4.8).

### 4.1 Sub-phase 2 — scheduled position-level events (financing) — AC 14.2, AR-56
"(2) scheduled position-level events (financing)"; AR-56: "financing is a
scheduled position-level cash event at the accounting rollover". `RecordingHandler.
scheduled_position_event` exists (`_e14.py:110-112`) and `handler.scheduled` is
**never asserted** in any test. One of the six pinned phases has zero behavioural
coverage.

### 4.2 A rested intent actually fills on a **later** slice — AC 14.2, R8
"**Then** it never fills against this slice's path **and rests for a later
slice**." T-14.2-b and the T-14.2-P property both assert `out.filled == ()` — the
absence of a fill. No test drives a second slice with a resting intent and asserts
it *does* fill in sub-phase 3. `handler.executed` is never asserted. **A loop that
never executed a resting order would pass every test in Group B and the Group I
property.** This is the mirror of the epic's most-cited guarantee and it is missing.

### 4.3 Ports **bound per run-config** — AC 14.5, AR-56
"**When** the ports are bound per run-config, **Then** fill, slippage, and cost are
SEPARATE pinned ports". T-14.0-protocol proves three distinct `typing.Protocol`
types exist; `T-14.5-b` calls `classify_fill_quantity` directly. Nothing binds a
port through a `ResolvedRunConfig` or drives a fill *through the loop*. The
per-run-config binding clause of AR-56 is untested.

### 4.4 The CT-29 exit is minted **against the run's `world=replay` binding** — AC 14.5
The binding half of the clause has no assertion (see §3.6). SCN-0012 §Then(6): "the
trade record IS the CT-29 stream of this run's replay binding".

### 4.5 Bot-proposed exits are **risk-monotonic** — AC 14.5, CT-23, FR-032
CT-23: "An intent may never widen a stop, extend a target beyond the Book's
declared envelope, re-open a closed position, or increase size — each is a policy
rejection"; V1 exit kinds are exactly `close_full | tighten_protective_stop`.
RESULTS records this as a "SEAM" deferred to `qmb/execution/risk.py::evaluate_exit`
(Epic 17). That deferral is defensible for the *evaluation content*, but the epic's
own AC states the property at this level and no test asserts even the seam refuses
a risk-widening exit.

### 4.6 Warm-up length is **sourced from** the AD-21 split manifest — AC 14.4, CT-12
"**Then** it is the split-manifest embargo **already declared under AD-21 for the
producers the stream set cites**". Every warm-up test passes `embargo=<int>` as a
`run()` parameter (`test_e14_d_warmup.py:40, 61, 87`). T-14.4-c proves the *unit*
is an observation count and that a Duration is refused — good — but nothing proves
the count is **derived from the split manifest of the cited producers** rather than
supplied by the caller. A caller-supplied embargo is arguably the "second window"
the AC forbids.

### 4.7 `world` is **derived from provenance, never caller-declared** — AC 14.5, FR-036, B-7
FR-036: "`world` derives from data provenance, **never from a flag**"; SCN-0012
Branch B: "world is derived, never caller-declared". `T-14.5-e` proves the pure
function `derive_world_from_provenance` maps `"recorded"→REPLAY` and
`"synthetic-tainted"→SIMULATED` — correct and valuable at unit level. But the test
helper `_e14.config()` sets `data_provenance="recorded"` **and** `world=World.REPLAY`
as two independent constructor arguments (`_e14.py:62-63`), and no test asserts
that a config declaring `world=REPLAY` with synthetic provenance is refused, nor
that `run()` derives world rather than reading the declared field. The seam is
tested; the law is not.

### 4.8 R37 — plain-Python ungoverned bot — AC 14.8, QL-1, FR-047/048 — **mis-classified as blocked**
The PLAN (§4 Group H, §8 matrix) explicitly calls T-14.8-d "the one 14.8 test
executable without QML — plain-Python is a day-one first-class input" and statuses
it `planned`, P2. RESULTS re-classifies it as SKIPPED / "QML tunnel territory …
not assertable in `runloop/` isolation". SCN-0012 §Given states the opposite: "the
bot is a registered **plain-Python** bot (a plain-Python bot is a first-class input
day one and **needs zero QML imports**)". The requirement is precisely that the
QL-7 path is *not* required — which is assertable here, and which the suite in
fact demonstrates incidentally: every Group B/D/F test drives `run()` with a
plain-Python `RecordingHandler` carrying no QML dependency. This is a **coverage
gap recorded as a blocker**, and it should be reclassified: R37 is executable in
Epic 14, and its skip is the one skip of the four that is not justified.
(R34/R35/R36 skips are correct — epics.md itself notes 14.8 "waits for Epics 12
and 13".)

### 4.9 Not a gap, but a plan-vs-implementation deviation worth recording
PLAN §6 required a "**Golden slice corpus** … checked into `qa/` fixtures, never
sourced from a provider at run time (B-11)" as the substrate for T-14.7-a/b/c. The
implemented determinism tests use an inline synthetic `_e14.config()` built by
constructing the frozen `ResolvedRunConfig` dataclass directly, bypassing the B-3
compiler, with no checked-in fixture and no pinned expected fingerprint. The AC
("both produce an identical CT-32 fingerprint") is literally satisfied by
run-vs-run equality, so this is not a wrong expectation — but "golden slice" in
AR-58/SCN-0012 implies a *pinned* artifact that catches identity drift across
commits, and that stronger property is absent.

---

## 5. What the suite gets right (so the verdict is read correctly)

These tests assert requirements, not implementation, and are the reason the
verdict is `gaps` rather than `inadequate`:

- **T-14.0-imports + T-14.1-g** (R1, AR-16) — an AST gate over all five
  `runloop/` modules *plus* a runtime poisoned-clock proof. This is the correct
  way to prove a negative and is the strongest pair in the suite.
- **T-14.1-a/b/c and T-14.1-P** (R2) — monotonicity, min-next-emit, order
  invariance, exhausted-stream handling, and rewind refusal, with a 200-case
  hypothesis property. Directly traceable to AC 14.1 and SCN-0012 §Then(5).
- **T-14.3-e** (R13, P0) — 200-case property over arbitrary tick sequences and
  BarSpec periods asserting forming bars are non-actionable, non-readable, and
  that completed bars close at or before the frontier. Real breadth over the
  named `bars.py` weak spot.
- **T-14.7-c (hashseed)** (R32) — a genuine cross-process determinism check under
  `PYTHONHASHSEED=0` vs `=1`. This is the assertion NFR-02/NFR-03 actually demand.
- **T-14.6-a (mid-run half)** (R26) — an observer signals cancel after slice 1 and
  the run aborts with `slices_completed == 1`. Behavioural, not self-reported.
- **T-14.4-d** (R19) — `evidence_range.start == NS + 1` with `embargo=1`; the
  warm-up frontier is genuinely excluded. Correct reading of AC 14.4 / SC-10.
- **T-14.4-b (integration half)** (R17) — minting under the warm-up lock aborts
  the run with a `POLICY_REJECTION` in `context["field"] == "warmup"`.
- **T-14.7-b** (R31) — reproduce-or-refuse, including the mismatch branch. Matches
  AR-58 and SCN-0012 §Then(7) exactly.

Refusal discipline (PLAN §6) is honoured throughout: every "is refused" assertion
checks a **returned** CT-04 typed refusal with a category, never a raised
exception. That is a real and consistently applied strength.

---

## 6. Adjudication of `findings.csv`

`findings.csv` contains a **header row and zero data rows**.

There is therefore no row to classify as "genuine requirement violation" vs
"wrong test expectation". The adjudication is of the empty result itself:

| Question | Answer |
|---|---|
| Genuine requirement violations recorded | 0 |
| Wrong test expectations recorded as findings | 0 |
| Is the empty file consistent with the suite? | Yes — no test failed, and the lane's rule is that findings are per failing test. |
| Is the empty file a trustworthy statement about the epic? | **Partially.** |

**Why partially.** "Zero findings" is doing more work than the evidence supports,
for two reasons:

1. Several assertions **cannot fail** (§2.1, §3.1, §3.4) — a literal `= False`
   compared to `False`, a hash compared to a different hash. A green result from
   an unfalsifiable assertion is not evidence of conformance.
2. Several requirements were **never asserted** (§4), so no failure was possible
   there either. Notably §4.2: the suite would report zero findings against a loop
   that never executed a resting order at all.

The two process caveats RESULTS records (the missing `test-design-qa.md` and
`QMX-handoff.md`, and the absence of executed mutation testing) are stated
accurately and prominently, and I confirmed both files are absent — the whole
`_bmad-output/test-artifacts/` directory does not exist in this worktree. RESULTS
§Notes(2) claims each P0 guard is "tied to a concrete, non-decorative assertion";
that claim holds for T-14.3-e and the hashseed test, but **not** for T-14.2-e,
which it cites as its first example. Un-run mutation testing is exactly what would
have caught §3.1 and §3.4: flipping the guard behind
`PARTIAL_GOVERNED_RESULT_ON_ABORT` or reordering the loop's phases would leave
those tests green.

**No finding should be *added* on the strength of this review** — an L6 review
judges assertions, and none of the gaps above is evidence that the source is
wrong. They are evidence that the suite does not yet *know* whether the source is
right on those points.

---

## 7. The single most important gap

**AR-57 / AC 14.2 — "the six sub-phase order is pinned and identity-bearing" — the
epic's headline P0 guarantee and the root of every downstream determinism claim,
is nowhere asserted against observable loop behaviour.**

Both halves rest on the implementation's self-description:

- *Pinned order* → read from the loop's own `trace` / `subphase_order()`
  (T-14.2-a), with the one instrument that could observe real execution order
  (`RecordingHandler`) recording into four separate lists so interleaving is
  unobservable, and two of those lists never asserted at all.
- *Identity-bearing* → proved by mutating a dict and re-hashing it (T-14.2-e),
  never by running the loop with a perturbed order and comparing CT-32
  fingerprints — the test the PLAN itself specified.

Consequence: a loop that executed sub-phases 2/3/4 in the wrong order, or whose
CT-32 fingerprint did not incorporate the sub-phase order at all, would pass this
suite green with zero findings. Since every backtest, sweep, MC run and
walk-forward downstream inherits its identity from this loop — and, per the PLAN's
own risk framing, a defect here "cannot be back-filled" — this is the one gap that
should be closed before the epic is treated as audited.

**Closing it needs two tests, both already specified in PLAN §4:** (a) a
phase-tagged single-log handler asserting the six effects occur in the pinned order
at the seam, with sub-phase 2 (financing) and a later-slice fill included; and
(b) T-14.2-e as written in the PLAN — a test-only reordered driver whose **run**
produces a different **CT-32 fingerprint** than the pinned order.
