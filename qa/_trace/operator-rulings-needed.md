# Operator rulings needed

Twelve items the verification lanes could not settle on their own. Each is a genuine fork where two
defensible readings exist and picking one is an authority call, not an engineering call. None of them
blocks the whole backlog — but four of them (OR-01, OR-02, OR-06, OR-11) block a specific fix card
from being written correctly, and those are marked.

Each item is one plain-words paragraph: what the tension is, the two options, and what each implies.

---

## OR-01 — Can a bot tighten its own stop, or only move it to breakeven?

**Blocks:** the Epic-10 exit-door work (no fix card until this is settled).
**Raised by:** `qa/epics/epic_10_qmf-risk/L6-REVIEW.md` §2, "Requirement tension worth surfacing".

Two acceptance criteria that both ship today say different things about the same act. Story 10.6 AC3
admits `tighten_protective_stop` as a general capability, and the test that covers it accepts an
arbitrary tighten — a stop moving from 500 to 300 comes back `Ok`. Story 10.7 AC6 says "V1 dynamic
SL/TP is the move-to-breakeven ratchet **only**", and the test that covers *that* refuses the same
shape — 50 to 25 is refused by the breakeven ratchet check. Both tests correctly encode their own AC;
the contradiction is in the requirements, not in the code, and the two guards are different functions
so today the answer depends on which door the intent arrives through. **Option A — the general
tighten stands:** any risk-reducing stop move is admissible in V1 and 10.7 AC6 is narrowed to say the
breakeven ratchet is the only *automatic* dynamic behaviour, not the only permitted one. That keeps
more capability in the operator's hands and is consistent with L39's spirit (never block a
risk-reducing act), but it means a bot can walk a stop up continuously, which is a strategy behaviour
V1 may not want to sanction unexamined. **Option B — the ratchet is the whole of V1:** 10.6 AC3 is
narrowed so `tighten_protective_stop` only accepts a move to breakeven, and anything else is a policy
rejection until a later version. That is the more conservative reading and makes the two guards
agree, but it forecloses a legitimate risk-reducing act and will need an explicit unblock later.
Whichever way it goes, both tests need re-pointing and the losing AC needs amending — leaving them
contradictory means the behaviour is decided by call-site accident.

---

## OR-02 — Is a sweep combo a trial or a confirmation?

**Blocks:** nothing in code today, but it decides whether a currently-green Epic-20 test is asserting
the right number.
**Raised by:** `qa/epics/epic_20_qmb-sweeps/L6-REVIEW.md`, row E20-F01.

Epic 20's four stories never say what ledger role a plain sweep combo takes, and the source picked
one: `run_sweep_batch` defaults every combo to `role=confirmation`, which makes every combo
bar-eligible under the confirmation-only Book-bar fold. Nobody ratified that. **Option A —
confirmation (the current default):** every sweep combo counts toward the Book's performance bar, so
a 200-combo parameter sweep contributes 200 confirmation-role lines to the bar. That treats a sweep
as real evidence, which is defensible when the sweep is the deliberate confirmation of a hypothesis,
but it makes the bar trivially easy to flood — run a wide enough sweep and the bar fills with runs
nobody intended as confirmations. **Option B — trial:** sweep combos are exploratory by default and
are excluded from the bar unless promoted, which protects the bar's meaning and matches the sweeps
epic's stated purpose (search, not adjudication), at the cost of an extra deliberate step whenever a
sweep genuinely *is* the confirmation. Note one practical consequence either way: the test that
carries this (`T20-323`) asserts `len(bar) == 4`, a count that is only true under Option A, while the
same test's docstring says it does not assert which role a combo should take. That assertion must be
dropped or restated so it holds under either ruling — right now the test pins the very default the
finding declares unratified. Three further tests (`T20-314`, `T20-316(f)`, `T20-PIN-01`) read the
merge view with a hard-coded `role="confirmation"` and will all break together on an Option B ruling.

---

## OR-03 — When a replay clock runs out of script, is that a bug or a refusal?

**Raised by:** `qa/epics/epic_01_qmf-core/L6-REVIEW.md` §1.1 (E1-U41); interacts with FC-32.

`DataDrivenClock.wall_now()` raises `LookupError("data-driven clock exhausted its scripted wall
instants")` when a replay run reads past the end of its script, and a test pins both the raise and
that exact English sentence as correct. CT-04 says every public QMF operation either succeeds or
returns a typed refusal, and that exceptions are reserved for **programmer error**; CT-02 makes
`Clock` a core-defined public protocol seam whose replay implementation is data-driven. So the
question is whether running out of script is a programmer error (you wired the wrong script) or a
data condition in replay (the script ended). **Option A — programmer error, the raise stands:** the
clock is treated as a test/replay fixture whose exhaustion means the harness is misconfigured, so
raising is correct and CT-04's boundary rule does not reach it. Simple, and it keeps the failure
loud. **Option B — a data condition, so it must return a typed refusal:** exhaustion becomes an
`unavailable dependency` or `stale evidence` refusal like any other, which makes the clock honour the
same law as every other public callable and lets a caller handle a short script gracefully — at the
cost of a wider `Result` surface on the hottest call in the system. Either way the test must change:
it currently pins two exact English message strings that the lane's own plan declared "not ratified
surface", and it asserts the wrong boundary (`> len` survives mutation where `>= len` is meant). This
also settles whether `observation_journal_event_type`'s `ValueError` in qmf-venue (FC-16) is the same
class of decision or a straightforward defect.

---

## OR-04 — Is `qml`'s module list wrong, or is `qml` shipping modules it should not?

**Raised by:** `qa/epics/epic_11_qml-authoring/L6-REVIEW.md`, row E11-F01; interacts with FC-17.

Story 11.1 AC2 says the qml package "contains **exactly** the module homes" and names seven. The
shipped tree has nine: `conformance, declaration, families, footprint, host, logic, protocol` — with
`host/` and `logic/` beyond the list. The two extras are different cases. `logic/` is the home Story
11.3 itself mandates for logic identity, so the AC's list simply omitted a module its own epic
requires — that reads as a defect in the AC text. `host/` is the substantive one: it ships impure
code (subprocess, file I/O) inside a wheel AD-15 declares pure, which is a separate confirmed finding
(FC-17). **Option A — amend the AC:** add `logic/` to the named seven, acknowledge that
`docs/components/qml.md:112` already calls the module list "the seed of intent, not a build
authorization (DEC-0184)", and let the list describe what the epic actually requires. Cheap, honest,
and it stops a correct module reading as a violation. **Option B — hold the AC and move both:**
treat "exactly seven" as binding, which forces `logic/` somewhere else and is hard to reconcile with
Story 11.3. The practical recommendation is Option A for `logic/` and FC-17 regardless for `host/` —
but the ruling is needed because the finding currently reads as one violation covering two unlike
things, and the fix card cannot be scoped until it is split.

---

## OR-05 — Does `invalid input` belong inside the backup boundary's refusal set?

**Raised by:** `qa/epics/epic_05_qmf-data-backup/L6-REVIEW.md` §1, W-1.

CT-14 and CT-26 both pin `boundary_refusal_categories` to exactly two of the seven CT-04 categories:
`storage failure` and `policy rejection`. The backup and restore boundaries also return
`invalid input` — for a malformed room role, a `copy_version=0`, a `world="mars"` — and the lane's
tests assert that as correct, then quietly trimmed `invalid input` out of the "forbidden categories"
set the test was written to check, leaving four of five. That trim is the tell: the one category the
implementation emits outside the ratified set is precisely the one dropped from the check.
**Option A — the contract means what it says:** `invalid input` crossing a CT-14/CT-26 boundary is a
defect and those refusals must be re-categorised as `policy rejection` (or the argument validated
before the boundary). That keeps the two-category promise a consumer can actually rely on, at the
cost of collapsing caller errors into a category that reads as a governance decision.
**Option B — caller-error refusals sit outside `boundary_refusal_categories`:** the ratified set
describes what the boundary produces about *the operation*, not about a malformed argument, and CT-14
and CT-26 get an explicit clause saying so. That is closer to how the code behaves and arguably more
useful diagnostically, but it means "the boundary returns one of exactly two categories" is no longer
true as written and every consumer branching on that set needs to know. Whichever way, restore the
test's forbidden set to all five non-boundary categories — the current four-of-five shape is not a
reading of either option.

---

## OR-06 — Is CT-33's `defined-unwired` status current, or is the shipped mint authorized?

**Blocks:** FC-05 (the fix is *gating* under one ruling and *removal* under the other).
**Raised by:** `qa/epics/epic_12_qml-protocol/L6-REVIEW.md` §1.

`docs/contracts/ct-33-bot-definition.yaml:9` declares `wiring_status: defined-unwired — no code
exists … no wiring is authorized from this doc`. Meanwhile `qml.register_bot_definition` exists, is
exported from top-level `qml`, stamps and persists a CT-33 Bot-kind record through an injected
registrar, and is driven by the shipped reference example. Both cannot be current. **Option A — the
document is current:** `install_bot_definition_kind` and `register_bot_definition` are unauthorized
wiring of a defined-unwired contract, and the fix is to remove them (or move them behind the AD-25
composition root at QMB, where the mint was always meant to live) rather than to add a conformance
gate to them. That preserves the build order the corpus ratified, but it deletes working code and
pushes the mint into Epic 14's territory. **Option B — the code is current:** the contract's wiring
status is stale and should be updated, in which case the surface stays and Story 12.7 AC1 / CT-33 §44
bite immediately — the mint must consult both conformance layer verdicts and refuse `policy
rejection` when either fails. That is the smaller change and matches what the example already tries
to demonstrate, but it means a governance contract's own status field was wrong, which is worth
knowing. Either branch is a finding; neither is "out of tier", which is how the lane originally
classified it.

---

## OR-07 — Which CT-13 event type carries a financing cash event?

**Raised by:** `qa/epics/epic_17_qmb-execution-ports/L6-REVIEW.md` §3, row E17-F01.

CT-13's journal event vocabulary is a closed set of seven — decision, order, fill, risk transition,
promotion, data quality, control action — and names no financing kind. Story 17.5 AC4 nonetheless
requires financing to be journaled as an exact-integer Money debit or credit to each open position,
explicitly *not* an order fill. So financing needs a home in a closed vocabulary that does not
mention it. **Option A — map it onto `risk transition`:** there is a ratified precedent for exactly
this move — CT-13 line 19 already rules that treasury cash-boundary events (sweep, refund, re_seed,
paper_epoch_reset) map onto the risk-transition type. Financing is the same shape of thing, so the
code is following an existing rule rather than inventing one, and no contract changes. The cost is
that `risk transition` becomes a grab-bag of cash movements and a reader must inspect the payload to
tell them apart. **Option B — mint an eighth event type:** add `financing` (or `cash event`) to
CT-13's enum, which makes the journal self-describing and keeps risk transitions about risk, at the
cost of opening a closed vocabulary that a lot of code branches on exhaustively. Note the lane rated
this medium and L6 recommended downgrading it to low precisely because Option A has precedent — but
it is still a vocabulary decision, and vocabulary decisions in this project are the operator's.

---

## OR-08 — Is the ban on a hand-maintained parity catalog a real requirement?

**Raised by:** `qa/epics/epic_16_qmb-cli-doors/L6-REVIEW.md` §0 and §4, row E16-F01.

The shipped door-parity contract reconciles the CLI and Python surfaces *through* a hand-maintained
15-entry `CAPABILITY_LIBRARY` literal, and that is what let a real asymmetry ship green (the catalog's
`data.generate` row omits its library function, so there was nothing to compare). The finding is
real. The authority behind it is not clean: "parity derived, not declared" comes from the brief's risk
gate `R-006`, which is not in `epics.md`. Story 16.5 AC1 requires "identical function surface and
semantics" and does **not** itself forbid a hand-maintained map. **Option A — R-006 stands as a
project rule:** derived parity becomes a binding requirement, the catalog is replaced by a derived
reconciler (FC-13 already specifies one, and Epic 16's own T-16.5-a is a working example), and R-006
is written into the corpus so it stops being brief-only. That closes the class of defect permanently.
**Option B — R-006 is advisory:** the catalog stays, the specific gap (`data.generate`) is fixed, and
parity is enforced by discipline plus review. Cheaper now, and it leaves the same trap armed for the
next capability. **One guard applies under either option:** `R-006` must never be read as `FR-006`.
`epics.md:263` assigns FR-006 to **Epic 2** (fingerprint-keyed registration records, CT-06), and the
two ids appearing together in one findings file is exactly how a mis-citation propagates.

---

## OR-09 — Which epic owns the `data generate` door-parity defect?

**Raised by:** `qa/epics/epic_23_qmb-synthetic-data/L6-REVIEW.md` §1 (E23-F01) and
`qa/epics/epic_16_qmb-cli-doors/L6-REVIEW.md` §4 (E16-F02).

Two lanes independently found the same defect — `generate` and `has_generator_config` reachable from
the CLI door and absent from the Python door — and both filed it as a P0. It is one defect. It is
merged as QMX-F016 in this inventory, but the ownership question decides where the fix card runs and
how it is counted. **Option A — Epic 16 owns it:** the reachable-from-every-door obligation and
FR-046 are Epic 16's, Epic 23's own ACs name only the CLI door, and Epic 16's derived parity test is
what actually caught it. Epic 23 keeps a cross-reference line so its own coverage story stays honest.
**Option B — Epic 23 owns it:** the missing capability is a synthetic-data capability, so the epic
that owns the capability owns its exposure. The practical difference is small but real: under Option
A the fix lands with the parity-derivation work (FC-13) as one card, which is where the root cause
is; under Option B it lands as an Epic-23 export change and the parity catalog stays broken. The
recommendation in both L6 files is Option A. What matters most is that **one defect is not counted as
two P0s** in whatever scoreboard the operator reads next.

---

## OR-10 — What are the Skylos gate numbers?

**Raised by:** the machine battery (`skylos/SUMMARY.txt`) and fix card FC-34.

The Skylos run over `2c8d495` grades the tree **C+ (77)** overall, driven entirely by the quality
bucket at **8 / F**: 4,084 quality findings, of which 25 are CRITICAL and 361 HIGH, essentially all
of them cyclomatic and cognitive complexity. Every danger bucket is already spotless — security A+,
secrets A+, ai_defects A+, zero dependency vulnerabilities, 2 AI-authored findings out of 4,163. Dead
code is A+ at 79 symbols (0.4 per 1K LOC). The ratchet numbers are the operator's to set; FC-34
proposes `max_dead_code = 80` immediately (a free no-regression lock, since the count is 79 and the
three-way intersection is empty), `max_quality` pinned at today's 4,084 and ratcheted down as
families clear, and **no gate on the overall letter grade** — it is dominated by the quality bucket
and would block every merge from day one while telling you nothing the family counts do not. The
substantive choice is *how* the quality debt gets worked: **Option A — as a campaign**, a dedicated
chunk that splits branches across the seven hot files. Fast, visible, and it touches a lot of code
nobody asked to change. **Option B — as a side effect of the fix cards**, since four of the seven
worst files (`qmb/data/download.py:200` at cyclomatic 35 / cognitive 64, `qmb/data/catalog.py:279`,
`qmb/results/charts.py:863`, `qmb/config/compiler.py`) are already being opened by FC-03, FC-11,
FC-14 and FC-18. Slower, but every split lands inside a change that already has a proving test. Worth
knowing before you choose: `download.py:200` alone carries four confirmed defects (QMX-F004, F018,
F022, F034), which is a reasonable argument that complexity here is a real signal and not a
style score.

---

## OR-11 — Implement the stochastic slippage seed, or strike the clause?

**Blocks:** FC-30 (the card is written both ways and cannot be started until this lands).
**Raised by:** `qa/epics/epic_17_qmb-execution-ports/L6-REVIEW.md` §3, row E17-F07.

Story 17.3 AC6 requires that "any stochastic term draws from a per-run seed … so replay reproduces
the same draw". `slip_fill` does `del seed` — it discards the parameter — and all five V1 slippage
models are deterministic, so the clause has no implementation at all and nothing to reproduce.
**Option A — wire the seed through now:** the plumbing exists and the change is small, so a future
stochastic slippage model is reproducible by construction and NFR-03's replay guarantee holds without
a later retrofit. The cost is carrying a parameter nothing currently uses, which is exactly the kind
of dead weight the dead-code gate is meant to catch. **Option B — strike the clause:** V1 ships no
stochastic slippage model, so AC6's stochastic sentence is aspirational and should be removed from
the AC with a note that it returns when a stochastic model does. Honest, and it stops R23 being
counted green against nothing — but it means a later stochastic model must re-derive the seed
discipline from scratch, at a point where replay determinism is already load-bearing. Either way R23
must stop being reported green: the lane filed this UNPROVEN (correct — there is nothing to test) and
then still counted the requirement met.

---

## OR-12 — Two qmf-structure clauses look unimplemented: build them, or amend CT-17?

**Raised by:** `qa/epics/epic_09_qmf-structure/L6-REVIEW.md` §2, M-5 and M-6.

Two ratified CT-17 clauses appear to have no code behind them, and nobody adjudicated that because no
test looked. CT-17:25 says a sloped object's evaluation at an instant crosses the named
analytic-to-exact boundary with its declared rounding — `SlopedObject` stores `target_scale` and
`rounding` but `geometry.py` exposes only `try_create`, `fp1_identity` and `content_fingerprint`, so
there is no evaluation entry point at all. CT-17:31 says CT-16's state bound and snapshot/restore
obligations apply to families verbatim — and `snapshot` and `restore` appear **zero** times anywhere
in `packages/qmf-structure/src`. **Option A — build them:** both clauses are ratified and a consumer
reading the contract would reasonably expect the surfaces to exist, so implement the sloped
evaluation entry point and the family snapshot/restore. That closes the gap between contract and code
at real cost, and needs its own scoping. **Option B — amend CT-17:** if these were declared in
anticipation of a later sitting and V1 genuinely does not need them, mark them deferred with a GAP id
the way CT-16's numeric rungs are, so the contract stops promising surfaces that do not exist.
Cheaper and honest, provided nothing downstream is already written against them. What is not
acceptable is the current state: Epic 9's RESULTS says "no source defect was found", which is true
only of the clauses that were asserted — and these two were never looked at. Whichever option, the
epic's headline needs softening to "no source defect among the clauses asserted" until it lands.
