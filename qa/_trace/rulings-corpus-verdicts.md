# Corpus verdicts on the twelve open operator rulings

Twelve items from `qa/_trace/operator-rulings-needed.md` were put to the ratified corpus before being
put to the operator. Seven are already answered by decisions the operator made months ago and does
not need to make again. Five are genuinely still open, but four of those five are narrower than the
original question — the corpus fixed the shape and left only a detail.

Every citation below was read at the cited file and line. Statuses:

- **RATIFIED-ANSWER** — the corpus decides it; no operator time needed.
- **PARTIAL** — the corpus constrains it hard but leaves a named residue.
- **OPEN** — the corpus says nothing; a fresh decision is required.

---

## OR-01 — Can a bot tighten its own stop, or only move it to breakeven?

**STATUS: RATIFIED-ANSWER — Option A (the general tighten stands).**

The two acceptance criteria were never about the same act, so there was no real contradiction to
resolve. `docs/contracts/ct-23-risk-evaluation.yaml:26` governs the bot-proposed door verbatim: *"A
tighten_protective_stop names a direction and a bound, never a price; the Book's policy resolves the
level, which keeps R single-authored, and enacts the move through the CT-19 amend_protection command,
risk-non-increasing measured against the frozen original_risk_distance (DEC-0147, DEC-0148,
DEC-0154)."* The only bound is risk-non-increasing — not breakeven. The breakeven rule belongs to a
different machine: `docs/components/qmf-risk.md:103` reads *"V1 dynamic SL/TP is the move-to-breakeven
ratchet only: one-directional, risk-reducing, never reset outward, per-Book configurable... Richer
policies (trailing, laddered targets) are later Book versions expressible through the same
declaration."* That governs the Book's own automatic behaviour, not what a bot may propose.

The corpus also confirms continuous walking-up is deliberately legal, and says why:
`qmf-risk.md:95` — *"moved only by Book policy or a protection authority and only in the
risk-non-increasing direction measured against the frozen `original_risk_distance` (stated that way
so a ratchet passing entry into profit stays legal)."* And the direction of travel is toward more bot
exit authority, not less: the same line records the 2026-08-21 veto round making *"bot-owned exit
methodologies... first-class"* through this door (DEC-0185).

**Plain words.** A bot is allowed to ask for its stop to be pulled in as far as it likes, so long as
every move only ever reduces how much money is at risk and never widens it back out. The
"breakeven only" rule you are worried about was only ever about the Book's *own automatic* stop
behaviour — a separate thing that runs by itself with nobody asking. Both acceptance criteria were
right all along; they were just written as if they governed the same act.

**Fix-card consequence.** Epic-10 exit-door work unblocks on Option A. Keep Story 10.6 AC3's general
`tighten_protective_stop`. Reword Story 10.7 AC6 to "V1 **automatic** dynamic SL/TP" so it stops
reading as a ceiling on the bot door. Re-point the tests: the breakeven guard covers the automatic
path only; the CT-23 door keeps the risk-non-increasing guard. No capability is lost. If the 10.6
test would accept a *widening* move, that specific case remains a real defect.

---

## OR-02 — Is a sweep combo a trial or a confirmation?

**STATUS: RATIFIED-ANSWER — Option B (trial).**

`docs/components/qmb.md:79` decides it and states the exact abuse the code's default enables:
*"optimize trials, Monte Carlo and significance replicates, and walk-forward train windows ledger
`role = trial` or `replicate` plus the objective measure — never a bar verdict — and the Book-bar read
selects `confirmation` lines only, so a trial never masquerades as a confirmation (DEC-0162)."*
`qmb.md:95` closes the loop for the sweep case specifically: *"every trial is a first-class B-3/B-4
run with `role = trial`"*, and that same line rules a non-adaptive grid/Sobol adapter — a plain
sweep — rides the same path. `_docwork/ledger.yaml:1546` (DEC-0165) confirms sweep runs *are* trials:
*"A sweep resolves ONE as-of at batch admission, frozen for every trial and stamped into the sweep
label."* The `role=confirmation` default in `run_sweep_batch` is unratified and contradicts this.

**Plain words.** A sweep is a search — you run two hundred settings to see which ones look
interesting, not to prove any single one works. The corpus already decided that search runs are
"trials," and that only runs you deliberately mark as "confirmations" count toward a strategy's
performance bar — precisely so a wide sweep cannot flood the bar with runs nobody meant as proof. So
a plain sweep combo is a trial, and it stays off the bar until somebody deliberately promotes it.

**Fix-card consequence.** E20-F01 unblocks in the Option B direction. Change `run_sweep_batch`'s
default to `role=trial`. `T20-323`'s `len(bar) == 4` must be dropped or restated (a sweep now
contributes zero confirmation lines). `T20-314`, `T20-316(f)` and `T20-PIN-01` hard-code
`role="confirmation"` on the merge view and break together — re-point all three to `role="trial"`.

---

## OR-03 — When a replay clock runs out of script, is that a bug or a refusal?

**STATUS: PARTIAL — the corpus constrains hard toward Option B (typed refusal); the residue is
whether "script exhausted" counts as programmer error.**

The corpus destroys Option A's *premise*. Option A rests on the replay clock being a test fixture
that CT-04's boundary law does not reach — but `Clock` is a listed core public protocol seam under
CT-02, and its replay implementation is a real governed surface, not a harness gadget. So CT-04's
rule reaches it: `docs/contracts/ct-04-typed-refusal.yaml:16` — *"Every public QMF operation either
succeeds or returns a typed refusal; a refusal carries a category, machine-readable context, and a
retryability answer (DEC-0109)"* — and `:18` — *"Refusals are RETURNED across public boundaries as
one arm of a result union; exceptions are reserved for programmer error and never carry a refusal
across a package boundary (DEC-0109)."*

What the corpus never does is define what counts as *programmer error*. No DEC, AD or contract
classifies "the script ran out" one way or the other. That single classification is the residue.

**Plain words.** The replay clock is not a testing toy — the corpus treats it as a real, public part
of the engine, and the engine's own rule says a public part should hand back a polite typed "no"
instead of crashing. But the same rule keeps crashes for genuine coding mistakes, and nobody ever
wrote down whether "you handed me a script that was too short" is a coding mistake or just the data
running out. Everything points at "polite no," but that last inch was never formally taken.

**Fix-card consequence.** FC-32 / QMX-F042 can be written in the Option B direction now and only
needs a one-word confirmation. Either ruling, two test changes are mandatory and independent of the
fork: stop pinning the exact English message strings (the lane's own plan declared those "not
ratified surface"), and fix the boundary assertion to `>= len` (the surviving `> len` mutant). This
also settles FC-16 as a *different, weaker* case: `observation_journal_event_type`'s `ValueError`
fires on a wrong enum being passed, which is type misuse and squarely programmer error — so an
Option B ruling here does not automatically drag FC-16 along.

---

## OR-04 — Is `qml`'s module list wrong, or is `qml` shipping modules it should not?

**STATUS: RATIFIED-ANSWER — Option A, but the finding must be split in two.**

The word "exactly" cannot bind, because the list it governs was ratified as non-binding.
`docs/components/qml.md:112` (and the QML spine's Structural Seed section) reads verbatim: *"The
module list is the spine's structural seed, carried here as the seed of intent, not a build
authorization (DEC-0184)."* A list ratified as intent-not-authorization cannot make a correct module
read as a violation. So `logic/` — the home Story 11.3 itself mandates — is admissible, and the AC
text is what bends.

`host/` is a different and much harder case, and Option A does not cover it. `qml.md:52` is flat
law: *"The library is pure per AD-15 (no threads, no I/O, no process spawning); every impure step
lives at a host composition root (DEC-0171)."* `host/runner.py` imports `subprocess`, `os` and
`tempfile`, and its own `__init__` concedes the impurity. That is a violation whichever way the
module list is read.

**Plain words.** When the plans were signed off, you explicitly said this folder list was a sketch of
intent, not a rulebook — so a folder the work genuinely needs (`logic/`) is fine, and the word
"exactly" in the story is what should soften. But a folder that launches processes and writes files
(`host/`) breaks a completely separate, hard rule that this library must stay pure, and that stays a
real defect no matter what the list says.

**Fix-card consequence.** Split E11-F01. Amend Story 11.1 AC2 to name `logic/` — a text edit, no code
change, cheap. Route `host/`'s impurity to FC-17 (relocate it to QMB's composition root). Stop
counting one finding across two unlike things. Minor open detail for the card author, not a reopening
of the fork: the corpus names no `logic/` home itself, so whether logic-identity helpers get their
own home or fold into `declaration/` is an AC-wording call.

---

## OR-05 — Does `invalid input` belong inside the backup boundary's refusal set?

**STATUS: RATIFIED-ANSWER — Option A (the contract means what it says).**

The `boundary_refusal_categories` field is an exhaustive per-boundary whitelist, and its own authors
proved it by listing `invalid input` wherever a boundary really emits it. Compare, verbatim:

- `docs/contracts/ct-14-backup-restore.yaml:33` — `boundary_refusal_categories: [storage failure, policy rejection]  # subset of the seven (DEC-0109)`
- `docs/contracts/ct-26-store-backup-input.yaml:32` — identical.
- `docs/contracts/ct-15-external-source-adapter.yaml:49` — `boundary_refusal_categories: [transient venue failure, unavailable dependency, invalid input, storage failure]  # subset of the seven (DEC-0109)`

The sibling contract **includes** `invalid input` exactly because that boundary validates foreign
input. Its absence from CT-14 and CT-26 is a deliberate calibration, not boilerplate — which kills
Option B's claim that the field never covers argument errors. And the corpus already routes the
specific errors the code mislabels: a cross-world restore read is ruled a *policy rejection*
(DEC-0117 / CT-14's own invariant), not `invalid input`.

**Plain words.** These two contracts promise that the backup door only ever fails in one of two named
ways: a storage problem or a policy block. A sister contract shows the team wrote "bad input" into
that promise whenever a door genuinely produced it — so leaving it out here was on purpose. Code
returning "bad input" from the backup door therefore breaks a promise other parts of the system were
built to rely on.

**Fix-card consequence.** Confirmed defect, low-to-medium. Re-categorise the backup/restore
invalid-input refusals as `policy rejection` (the `world="mars"` case is already ratified that way),
or validate `source_room_role` / `copy_version` / `world` *before* the boundary. Independently of the
ruling, restore `5_1_c4`'s forbidden set to all five non-boundary categories — the current
four-of-five shape is a reading of neither option and is simply wrong.

---

## OR-06 — Is CT-33's `defined-unwired` status current, or is the shipped mint authorized?

**STATUS: RATIFIED-ANSWER — Option A (the document is current; the shipped mint is unauthorized).**

This is not one stray status field. The same law is repeated at five independent layers.
`docs/contracts/ct-33-bot-definition.yaml:9` — *"wiring_status: defined-unwired  # the Bot kind is
ratified surface; no code exists; records reach qmf-registry through the composition root under the
AD-25 root-mints pattern; no wiring is authorized from this doc (DEC-0173)."* And `:6` — *"QML
returns fingerprintable content and the composition root mints and persists the record under the
AD-25 root-mints pattern, so no package import edge exists (DEC-0173)."* `docs/architecture/dependencies.yaml`
repeats it; the QML spine's QL-8 diagram repeats it; and Story 12.7's own AC (`epics.md:2697`)
repeats it: *"the host composition root holds the WriterId and mints the record (AD-25 root-mints
pattern); qml returns only the fingerprintable content and the pass/fail verdict, never a stamped
record."*

QML was granted the conformance *gate* only. A top-level `qml.register_bot_definition` that stamps
and persists is precisely the pure-library violation the corpus forbids.

*Citation correction carried from the research:* the dig hint pointed at DEC-0181, which is the CT-22
format-2 mint. CT-33's minting authority is DEC-0173. The ruling is unaffected.

**Plain words.** You ruled that the bot-authoring library only *describes* a bot and *checks* it — it
never *saves* the record itself; the platform's wiring point does the saving. The shipped code has
the library doing the saving, which breaks that rule. The document was right and the code jumped
ahead of it.

**Fix-card consequence.** FC-05 must be rewritten from *gating* to *relocation*. Keep QML's pure
linter and pass/fail verdict; move the actual mint to QMB's composition root, which is where Story
12.7 always put it. Given the platform-live priority, relocate rather than delete so the shipped
reference example keeps working.

---

## OR-07 — Which CT-13 event type carries a financing cash event?

**STATUS: RATIFIED-ANSWER — Option A (map financing onto `risk transition`).**

The precedent the ruling item hoped for is real and is in the contract itself.
`docs/contracts/ct-13-journal.yaml:19` — *"Treasury boundary events (sweep, refund, re_seed,
paper_epoch_reset) map onto the risk transition event type; no money moves without one, and a
boundary event never closes a position and never re-bases a frozen R (DEC-0158)."* That is a ratified
instance of the operator choosing to route a position-level money movement onto `risk transition`
rather than mint a new type.

Financing matches the constraints on that same line by its own definition — Story 17.5 AC1 makes it
*"an exact-integer `Money` debit or credit to each open position — not an order fill"*, and it never
closes a position. Story 17.5 AC4 demands a journal event "separate from fill P&L, slippage cost and
commission" — that is distinctness of the *record*, not a distinct *enum value*; the four treasury
kinds are already told apart by payload inside one type. `ct-13:17` makes the vocabulary *"an enum
addable in later versions but never redefined"*, so Option B is a format-version mint — the heavier
act the corpus deliberately avoided in the identical case.

**Plain words.** Your journal has exactly seven kinds of entry and none is called "financing." You
already decided that other money-in, money-out events — sweeps, re-seeds — get filed under the
"risk transition" kind rather than adding a new kind. Daily swap financing is the same sort of thing,
so it gets filed there too, with a label in the payload so a reader can tell it apart.

**Fix-card consequence.** E17-F01 unblocks toward Option A: map financing to `risk transition`, no
CT-13 change, carry a payload marker distinguishing it from fills and from the four treasury kinds.
The L6 downgrade to low severity is correct. Non-blocking note: the word "financing" is never
literally enumerated, so this applies the ratified treasury rule by analogy — the payload subtype
label is what keeps that honest.

---

## OR-08 — Is the ban on a hand-maintained parity catalog a real requirement?

**STATUS: PARTIAL — the door-parity outcome is ratified and the `data.generate` fix ships either way;
the "derived, not declared" rule is genuinely OPEN.**

The corpus binds the *outcome*. `docs/components/qmb.md:53` (B-1 / DEC-0159): door parity *"is not
aspiration but a tier-2 contract test asserting identical function surface and semantics across
doors."* `epics.md:208` (AR-58) makes it enforced by Tier-2 contract tests, and Story 16.5 AC2
(`epics.md:3322-3324`) is verbatim: *"Given a capability added to one door, When it is not present
with identical semantics in the other, Then the tier-2 parity test fails (B-1)."* The `data.generate`
gap violated that outcome and must be fixed regardless of the fork.

The corpus does **not** bind the *mechanism*. A grep of `docs/`, `_docwork/` and `_bmad-output/` for
`R-006` returns only `FR-006` hits (Epic 2, fingerprint-keyed registration records); the string
"parity derived, not declared" appears only in `qa/epics/epic_16_qmb-cli-doors/findings.csv` and in
the ruling document itself. What B-1 was actually ratified against was *codegen* — "thin hand-written
wrappers" — not hand-maintained catalogs. Choosing to mint the stricter rule now is a new decision.

**Guard confirmed:** `R-006` must never be read as `FR-006`. `epics.md:263` assigns FR-006 to Epic 2.

**Plain words.** The corpus already demands a test that keeps the two front doors identical and fails
loudly the moment one drifts, so the missing link must be fixed no matter what you decide. But it
never wrote down the stricter rule that this test must work the list out for itself rather than read
a list somebody types by hand — that phrase lives only in a working brief, not in anything you
ratified. Making that stricter rule binding is a genuinely new call.

**Fix-card consequence.** FC-13 / FC-01 (E16-F01) is *partially* unblocked: write and ship the
`data.generate` fix now under ratified authority. Leave the derive-vs-catalog half of the card marked
pending until the residue question below is answered.

---

## OR-09 — Which epic owns the `data generate` door-parity defect?

**STATUS: RATIFIED-ANSWER — Option A (Epic 16 owns it; Epic 23 keeps a cross-reference line).**

The obligation is Epic 16's by name. `epics.md:303` — *"FR-046: Epic 16 — qmb CLI, Python API,
optional MCP door."* Epic 23's requirement is a different one (`epics.md:298`, FR-041,
claim-class-labeled synthetic data). The parity machinery that caught the defect lives in Epic 16's
Story 16.5, whose AC2 (`epics.md:3322-3324`) covers this defect squarely.

Decisively, Epic 23's own acceptance criteria never mention the Python door at all. Story 23.1's
Given clause reads *"the `qmb data` command group is a thin front over the ratified QMF data
contracts (CT-10/CT-15) on the click==8.4.2 CLI door (B-11, B-1)"* — and a scan of Epic 23's whole
story block turns up no Python-door AC anywhere. Both L6 reviews independently recommend Epic 16.

**Plain words.** The corpus already hands Epic 16 the job of "every capability must be reachable from
both the command line and the Python door, and a test must prove it." Epic 23's job was only to build
the synthetic-data feature on the command line, and its written checklist never mentions the Python
door once. So the missing-export defect belongs to Epic 16, where the machinery that caught it lives.

**Fix-card consequence.** QMX-F016 lands as **one Epic-16 card**, folded into the parity work (FC-13)
where the root cause sits — not as an Epic-23 export tweak that leaves the parity catalog broken.
Epic 23 keeps a cross-reference line so its coverage story stays honest. Count it as **one P0, not
two**, on whatever scoreboard is read next.

---

## OR-10 — What are the Skylos gate numbers?

**STATUS: PARTIAL — the gate philosophy and the working mode are ratified; the specific numbers are
OPEN by the corpus's own explicit words.**

`pyproject.toml:404-413` is a standing operator ruling, verbatim: *"ANNOTATE-ONLY, by operator
ruling. The quality family is opinion about module structure... exact.py and chrono.py are the
ratified 100%-branch CT-01/CT-02 modules; splitting them to satisfy a line-count default would be a
design change made for a scanner's benefit, which we are not doing. So these are reported,
annotated... and they do not block."* Line 418 sets the working mode: *"Ratchet it down (1000 -> 100
-> 0) as the families are genuinely worked off; it can be lowered freely."* And `epics.md:2691-2693`
kills gate-by-complexity outright: *"any complexity/quality signal is a later measure, never a
registration gate."*

That ratified "no design change for a scanner's benefit" stance generalises **against Option A** (a
standalone complexity campaign touching code nobody asked to change) and **toward Option B** (splits
land as a side effect of fix cards that already open those files) — which is what FC-34 already
proposes and FC-31 echoes.

The numbers are not in the corpus. Today's ratified values are `max_quality = 1000000` and
`max_dead_code` commented out entirely. The gate block itself says the ratchet numbers are the
operator's to set.

**Plain words.** You already ruled that the code-quality score only *annotates* — it never blocks a
merge — because reshaping working code just to please a scanner is off-limits. That same ruling says
work the debt off gradually and tighten the number as you go, which is exactly Option B: fix it while
you are already inside a file for another reason, not as a big cleanup nobody asked for. The one
thing the corpus does not pin is the exact starting numbers, which it explicitly leaves to you.

**Fix-card consequence.** FC-34 is **not blocked** — adopt it as written; it matches ratified policy,
including its "no gate on the overall letter grade" (the letter is dominated by the annotate-only
bucket, so gating it would contradict "they do not block"). Take Option B as the working mode. The
only thing needing a word from the operator is the literal opening pins.

---

## OR-11 — Implement the stochastic slippage seed, or strike the clause?

**STATUS: PARTIAL — the corpus rules out both clean options and points at a hybrid; the residue is a
V1-hygiene wording call.**

No stochastic slippage model ships in V1. The SLIP-2 catalog at `spec-fill-fees.md:272-281` is five
deterministic models — Zero, Constant/percent-of-price, Spread-crossing, Gap/volatility, Size-tiered.
The seed guarantee is real but *conditional*: SLIP-3 (`spec-fill-fees.md:283-284`) — *"Every slippage
model MUST be pure w.r.t. `(order, market_state, params)` and reproducible under replay (same seed →
same draw for any stochastic term)."* The platform-wide discipline is ratified too (QL-7 / DEC-0177:
never undeclared randomness; a stochastic bot declares a seed parameter in its space).

Crucially, the *content* is explicitly deferred, not missing by accident: the QMB reconcile intake
records the SLIP catalog and calibration content as **DEFERRED EXPLICITLY** under GAP-0048, and the
spec's own Open Question #4 (`spec-fill-fees.md:336-338`) leaves the derivation unresolved — *"how is
the seed derived from the Book/BMS identity?"* — which also means `epics.md:3496`'s "derived from run
identity" is not settled.

This rules out both pure options. Option B's `del seed` (discard the parameter) contradicts QL-7's
declare-and-wire discipline and NFR-03's replay guarantee. Option A's "build it now" collides with
GAP-0048 and an unresolved derivation question.

**Plain words.** V1 ships no random slippage at all — all five models are fixed formulas, and the
random one was deliberately parked for a later meeting. The rule "if it is ever random, wire a seed
so replays come out identical" is real and ratified, but it only bites once something random actually
exists. So the requirement is not green and never was: there is genuinely nothing to test yet.

**Fix-card consequence.** FC-30 unblocks as a **hybrid**, not a clean A or B. Keep the seed parameter
threaded (do not `del` it — that breaks QL-7 and NFR-03). Keep AC6's conditional sentence as the
standing SLIP-3 guarantee. Do **not** build a concrete stochastic model or pin a seed-derivation rule
now — that is GAP-0048's, and the derivation itself is disputed. Mark R23 **deferred / UNPROVEN** and
never green; that part is not optional under any reading.

---

## OR-12 — Two qmf-structure clauses look unimplemented: build them, or amend CT-17?

**STATUS: PARTIAL — Option B (mark deferred) is corpus-favoured and Option A is corpus-contradicted;
the residue is the formal act of minting the GAP id.**

Both clauses are ratified as *declarations*, and the declarations are built. CT-17:25 —
*"A sloped or continuous object is identified by integer anchors — (instant, exact Price) pairs —
plus a declared versioned evaluation rule; slope is derived, never stored, never identity; evaluation
at an instant crosses the named analytic-to-exact boundary (DEC-0129, DEC-0126, DEC-0105)."* The
declaration is what this package owes, and `SlopedObject` carries `evaluation_rule`, `target_scale`
and `rounding` as fingerprinted identity. The *evaluation* crosses a named boundary that is one
qmf-core implementation the corpus says structure never re-implements.

CT-17:31 — *"CT-16's state bound and snapshot/restore obligations apply to families verbatim
(DEC-0128, DEC-0129)."* CT-16 attaches snapshot/restore to a *streaming stateful* class. Epic 9's V1
family is a pure batch detector with no stateful, WriterId-holding instance — so there is nothing in
this epic for snapshot/restore to attach to. Confirmed independently: `snapshot` and `restore` appear
zero times in `packages/qmf-structure/src`.

What the corpus never did is stamp either clause deferred, the way it stamps others — GAP-0016 is
flagged deferred right in CT-17's own header (`ct-17:10`), and CT-16:13 records its numeric rungs as
*"a deferred measurement, not a gap."* These two clauses fell between "the contract states it" and
"no story builds it."

**Plain words.** The corpus already says these two things are *written down now, run later* — the
object records its evaluation rule, but the actual arithmetic happens through a shared core component
elsewhere, and the save/restore belongs to a live scanner this epic never built. The contract states
them flatly without the "deferred" stamp it uses elsewhere for exactly this situation. So the answer
is clearly "mark them deferred," but nobody has formally done the marking.

**Fix-card consequence.** Write the card in the Option B direction: mark CT-17:25's evaluation
execution and CT-17:31's family snapshot/restore deferred against a fresh GAP id, following the
GAP-0016 and CT-16-rung precedent. Option A (build now) contradicts ratified design and should not be
scoped. Independently of the fork, soften Epic 9's RESULTS headline to *"no source defect among the
clauses asserted"* — the current headline overclaims.

---

# CLOSED BY CORPUS — no operator time needed

These seven are decided. The fix cards can be written and worked without any further ruling.

1. **OR-01** — Option A. A bot may propose any risk-reducing tighten; "breakeven only" governs the
   *automatic* dynamic stop, a different machine. Epic-10 exit-door work unblocks.
2. **OR-02** — Option B. A sweep combo is a **trial**, off the performance bar by default.
   `run_sweep_batch`'s `role=confirmation` default is a defect; four tests re-point together.
3. **OR-04** — Option A, split in two. `logic/` is admissible (the module list is "seed of intent,
   not a build authorization") and Story 11.1 AC2 is amended. `host/` is a separate hard purity
   violation and routes to FC-17 regardless.
4. **OR-05** — Option A. `invalid input` crossing the CT-14/CT-26 boundary is a real defect;
   re-categorise as `policy rejection` or validate before the boundary. Restore the test's forbidden
   set to all five.
5. **OR-06** — Option A. The document is current; the shipped QML mint is unauthorized. FC-05 becomes
   a **relocation** to QMB's composition root, not a gating change.
6. **OR-07** — Option A. Financing maps onto `risk transition` with a payload marker, following the
   ratified treasury-boundary precedent. No CT-13 change; severity downgrade to low is correct.
7. **OR-09** — Option A. Epic 16 owns the door-parity defect (FR-046 is Epic 16's; Epic 23's ACs
   never mention the Python door). One card, one P0, Epic 23 keeps a cross-reference line.

**Partially closed, worth noting:** OR-08's `data.generate` fix, OR-11's "R23 is not green," OR-12's
"soften the Epic 9 headline," and OR-03's two test corrections all ship under ratified authority right
now, ahead of their residues below.

---

# RESIDUE FOR OPERATOR — five questions

Each is one question. Answering all five closes the remaining backlog.

**1. (OR-03) The replay clock running out of script.**
When we replay old market data, we feed the system a list of timestamps to walk through; if the
system asks for one more timestamp than the list has, it currently crashes on purpose. Should that
instead be a polite "sorry, no more data" answer that the caller can handle — the way every other
part of the system reports a problem — or is running off the end of the list a sign somebody wired
the thing up wrong and deserves the crash? Everything else in the system already answers politely, so
saying "answer politely" here costs nothing and is what we recommend.

**2. (OR-08) How the two front doors are kept identical.**
QMX has two ways in — typing commands, and calling it from Python — and they must offer exactly the
same features. Today a person types out a list of features by hand for the checking test to compare
against, and one feature got left off that hand-typed list, which is how a real gap slipped through
unnoticed. Should we make the test work the list out for itself from both doors, so no human can ever
forget a line again, or keep the hand-typed list and just be careful?

**3. (OR-10) The two code-quality starting numbers.**
We now count two things on every build: leftover unused code (currently 79 items) and code-tidiness
complaints (currently 4,084). We want to lock in "never worse than today" so the numbers can only go
down: set the unused-code limit at 80 and the tidiness limit at 4,084, then lower both as we clean up
during work we are doing anyway. Do you confirm those two opening numbers?

**4. (OR-11) The unused "randomness dial" on slippage.**
Slippage is the small price difference between what you expect to pay and what you actually pay, and
all five ways we calculate it right now give the exact same answer every time — nothing random. There
is a leftover setting for feeding randomness a starting number, which today does nothing because
nothing is random yet. Should we keep that empty setting wired up so a future random model works
correctly on day one, or rip it out now and put it back later?

**5. (OR-12) Two promises in a contract with nothing behind them.**
One of our design contracts promises two things the code does not do, and after checking, both are
things we deliberately decided to do later rather than things we forgot. For example, it promises you
can ask a sloped price line "what is your value at 3pm?", but that arithmetic deliberately lives in a
shared component we have not connected yet. May we stamp both promises "coming later" with a tracking
number, the way we already did for a similar promise, instead of building them now?

---

*Written by the adjudicator pass over twelve researcher reports. Every citation quoted above was
re-read at its cited file and line before being relied on; no citation failed verification.*
