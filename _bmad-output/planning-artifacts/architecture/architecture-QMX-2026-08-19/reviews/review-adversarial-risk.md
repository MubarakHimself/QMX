# Adversarial Review — the risk increment (AD-29 … AD-41 + the AD-16 / AD-21 / AD-27 / AD-28 amendments)

- **Target:** `ARCHITECTURE-SPINE.md` (status: draft, updated 2026-08-20)
- **Scope:** AD-29 (Book/BMS/binding chain), AD-30 (templates + git-logic
  versioning), AD-31 (risk record kinds + per-entity journals), AD-32 (admission),
  AD-33 (exit ownership), AD-34 (`amend_protection`), AD-35 (paper mode), AD-36
  (control actions), AD-37 (same-tick priority), AD-38 (protection windows),
  AD-39 (SQS v1), AD-40 (R + the dimensional law), AD-41 (stop-out, bench,
  performance evidence) — plus the 2026-08-20 amendments those ADs wrote into
  AD-16 (risk record kinds, `continues-as`), AD-21 (`suppressed` subtype, entity
  projections), AD-27 (`amend_protection` mint, flatten authority pointer) and
  AD-28 (protection-capability fields, amend atomicity) — in interaction with the
  hardened AD-1 … AD-28.
- **Prior passes:** `review-adversarial.md`, `-2`, `-3`, `-venue.md`. None of them
  saw AD-29 … AD-41; this increment has never been adversarially reviewed. A high
  critical count here is a signal of youth, not of quality.
- **Date:** 2026-08-20

---

## 1. Method

I am not hunting for omissions or for things the Deferred table already parks. I
am building **pairs of units one level down** — the concrete libraries, records,
templates, doors and adapters a factory agent would write from these ADs — where
*both* units obey every ratified clause to the letter and the two still cannot be
assembled. The recurring pairs for this increment:

| Pair | Unit A | Unit B |
| --- | --- | --- |
| P-α | the `qmf-risk` contract author (CT-22..CT-25, CT-27..CT-32 value types) | the trading node's Book/BMS runtime (doors, ledgers, counters, arbitration) |
| P-β | the Book-template author | the BMS-instance author |
| P-γ | the paper-routing implementer (AD-35) | the reconciliation implementer (AD-27/AD-35) |
| P-δ | the control-action emitter (AD-36/AD-37) | the venue adapter + CM (AD-27/AD-28) |
| P-ε | the SQS configured producer (AD-39) | the Book door that consumes it |
| P-ζ | the CT-29 exit-record author | the CT-32 performance-result author |
| P-η | the registry record-kind author (AD-16/AD-31) | the journal-projection reader (AD-31) |
| P-θ | the dimensional-law checker author (AD-40) | the admission linter author (AD-32) |

**Severity rule, unchanged from reviews 3 and venue:** divergence that fails
loudly at an AD-4 tier is rated lower. Divergence where both units run, both pass
their own gates, and they write **different identities, different numbers, or
different authority into permanent append-only evidence** — or where the
divergence decides whether live money trades or a position closes — is critical.
Fingerprints and journals are forever; an identity fork or a silent money-cycle
reset is the one class of defect this architecture cannot repair later.

**Verdict:** the risk rulings are the right rulings — the authority order is
preserved, the kill switch / kill line split is correct, the dimensional law is
the single best thing in this increment, and the fold-not-flag discipline is
sound. But the increment mints **three new identity concepts (Book instance, BMS
instance, binding epoch) and never defines any of them**, adds a control plane
with **no evidence edge from enactment back to intent**, and closes its own
dimensional law over a vocabulary that cannot type its own admission formula.
Fifty-four places will produce divergent-but-conformant implementations; twenty
of them fork permanent evidence, silently reset money cycles, or decide whether a
position closes.

**Counts: 20 critical, 26 high, 8 medium (54 total).**

The good news is concentrated: five structural roots (§5) account for seventeen
of the twenty criticals, and each root closes with one or two clauses.

---

## 2. Critical — both units conform, both pass their gates, and permanent evidence, money, or a position forks

### C-01 — Two copies of one Book version on one account collapse into a single binding identity

- **Unit A — the Book-template author.** AD-30: *"a copy is that version
  instantiated onto an account as an instance"*; AD-29: *"Several Books may bind
  one account."* A instantiates two copies of Book version V on account X — two
  independent capital pots running the same rules over different bots. Every
  clause permits this.
- **Unit B — the registry record author.** AD-29 pins the risk domain as the
  tuple `(Book definition fingerprint, BMS instance, VenueId, AccountId, role,
  world)`. B computes the binding identity from exactly that tuple, per AD-16
  (*"a record's stable id is derived from its `fp1` fingerprint — never
  minted"*).

**The incompatible build.** A's two Book instances produce **byte-identical**
binding records. AD-10's collision split then does the worst possible thing: same
hash, byte-identical content is *"accepted silently"* as an idempotent re-write.
The second binding is swallowed without a refusal, without an alarm, without a
journal anomaly. AD-29 says *"Virtual ledger, cycle, budget, breaker counters,
exposure, mode and protective scope all live per binding"* — so the two Books now
share one ledger, one cycle, one budget and one breaker counter set. The operator
sees two Books in the UI and one pot of money in reality. Every AD-31 projection
keyed by binding identity merges them.

**Severity: CRITICAL.** Silent money merge, silent evidence merge, and the one
AD-10 path designed never to alarm.

**Closing clause (AD-29).** *"A Book instance is a first-class identity. The
binding tuple gains an operator-minted `BookInstanceId` under AD-9's minting
discipline — opaque, stable, never reused, never derived from the definition
fingerprint — so two copies of one Book version on one account are two bindings.
No two distinct intents-to-bind may ever produce byte-identical binding records;
a binding record that fingerprints equal to an existing one is an `invalid input`
refusal, never an AD-10 idempotent accept."*

---

### C-02 — "BMS instance" is an identity the spine never defines, and both readings are ratified elsewhere

- **Unit A — the `qmf-risk` contract author.** AD-9's minting discipline is
  invoked for `VenueId`, symbols, formula ids, family ids, `measure_identity` and
  secret references. A follows the pattern: `BmsInstanceId` is an operator-minted
  opaque id, stable across BMS template edits. Editing a BMS number therefore
  leaves the binding identity untouched.
- **Unit B — the registry record author.** AD-16 is categorical: *"A record's
  stable id is derived from its `fp1` fingerprint — never minted."* A BMS
  instance is a record. B derives it: `fp1(BMS definition fingerprint, AccountId,
  …)`.

**The incompatible build.** Under B, a single UI edit to a BMS constraint — which
AD-30 guarantees is a legal, expected, UI-editable act — mints a new BMS
definition fingerprint, therefore a new BMS instance identity, therefore a **new
AD-29 binding for every Book on that account**, therefore (AD-30's own chain)
*"a fresh cycle's money"* for all of them. Under A, nothing happens. AD-16's
`continues-as` edge is written only for *"a template version change or a broker
migration"* of a **Book**; nothing in the spine extends it to a BMS version
change, so B's operator has no legal way to declare the continuation. AD-32 makes
the ambiguity load-bearing by requiring *"the resolved BMS fingerprint"* on the
signature page without saying whether that is the definition or the instance.

**Severity: CRITICAL.** A BMS tweak either does nothing or resets every Book on
the account, and the operator cannot tell which system they own.

**Closing clause (AD-29 + AD-16).** *"`BmsInstanceId` is content-derived:
`fp1(BMS definition fingerprint, AccountId, VenueId, world, instance ordinal)`.
A BMS definition version change therefore mints a new binding for every Book
bound to it, exactly as a Book version change does, and `continues-as` coverage
is extended verbatim to BMS re-versioning and BMS swaps."* (See also C-03 and
§5 R1 — one clause closes all of them.)

---

### C-03 — `continues-as` has two unrelated effects and the spine assigns it neither

- **Unit A — the CT-32 performance-result author.** AD-16 defines `continues-as`
  as *"a human-signed assertion that one binding continues another's **performance
  record**."* A consumes it in exactly one place: the CT-32 *declared population*
  (AD-41), deciding which binding epochs are in or out of a report. Trading state
  is untouched.
- **Unit B — the node's money runtime.** AD-30 gives the same edge a different
  job: *"a new binding ⇒ **a fresh cycle's money**, unless a human-signed
  `continues-as` edge declares the continuation."* B therefore reads the edge as a
  **ledger-carry instruction**: on re-binding with `continues-as`, the new binding
  inherits the old binding's virtual ledger balance, cycle position, budget
  remainder and breaker counters.

**The incompatible build.** The sharpest fork is the bench. AD-41: *"The bench
counter is a read-time fold over the exit-record stream."* Over **which** stream?
A's fold stops at the binding boundary — a re-versioned Book starts every seat at
zero qualifying loss exits. B's fold follows the `continues-as` chain — the same
seat is already at the threshold and is benched on the next loss. Two conformant
builds, identical trade history, **opposite answers to "does this bot trade live
money right now."** Identically: A resets the loss budget on a rule tweak, B
carries a drawn-down budget across it.

**Severity: CRITICAL.**

**Closing clause (AD-16 + AD-30 + AD-41).** *"`continues-as` asserts performance
lineage and nothing else; it is consumed only by CT-32 population declarations.
Whether per-binding state carries across a new binding is a **mandatory declared
field on the new binding record** — `state_carry: {ledger, cycle, budget,
bench_counter, …} ∈ carry | reset` per counter, non-defaultable, `invalid input`
if absent — never inferred from the presence of an edge. AD-41's bench fold
declares its stream boundary explicitly as the `state_carry.bench_counter`
decision on the current binding."*

---

### C-04 — Two Book copies aside, `close_position` on a netting account destroys another Book's position

- **Unit A — the control-action emitter (AD-36/AD-37).** Book1's kill line
  breaches. AD-36: *"a kill-line breach flattens that binding's scope
  automatically."* A resolves the CT-30 scope `book` and dispatches.
- **Unit B — the venue adapter.** AD-28 declares the account's position model
  `netting`. On a netting account there is exactly one venue position per
  instrument at the **account** level. B executes the scope it is handed.

**The incompatible build.** AD-29 explicitly permits several Books on one
account, and explicitly names the one coupling it accepts — *"one Book's
`UNKNOWN` blocks the other's commands there. This is permitted and named, never
hidden."* It does **not** name the position coupling. Book1's flatten closes the
netted EURUSD position, which is also Book2's exposure. No authority authorized
that close, no CT-30 record covers it, Book2's virtual ledger realizes a loss
Book2 never decided, and AD-33's whole-trade attribution credits the result to a
Bot that never asked to exit. Both units are conformant: AD-36 mandates the
automatic flatten, AD-28 declares the netting model, and nothing forbids the
combination.

Compounding it: **CT-30's scope vocabulary and CT-19's are different sets and the
mapping is undeclared.** CT-30: `instrument | book | binding | account | venue |
global`. CT-19: `account | account-binding | instrument-within-binding`. AD-36
says the CT-30 scope is *"resolved at dispatch to AD-27 enforcement scopes …
never emulated at a wider scope"* — but the resolution table is left to each
implementer. One implementer maps `book → account-binding`; another maps it to a
compound of `instrument-within-binding` children. On a netting account both
resolve, at the venue, to the same account-level position — which is **wider than
the Book scope**, i.e. exactly the emulation AD-36 forbids, achieved without any
implementer noticing.

**Severity: CRITICAL.**

**Closing clause (AD-29 + AD-36).** Two sentences. *(1)* AD-29 bind-time check:
*"where CT-18 declares `position model = netting`, binding a second Book to an
account whose existing live bindings may trade an overlapping instrument set is a
`policy rejection` unless the Book declares `shared_netting_acknowledged` and the
AD-32 signature page carries it."* *(2)* AD-36: *"the CT-30 → CT-19 scope
resolution is a pinned versioned table in CT-30, not implementer judgment; where
the venue's position model makes a Book- or instrument-scoped enforcement
indistinguishable from a wider scope, the action **refuses**
(`unsupported capability`) rather than executing at the wider scope."*

---

### C-05 — "Position" is never defined as venue-side or virtual, and the bench counter rides on the answer

- **Unit A — the CT-29 exit-record author.** AD-41: *"The exit record, one per
  position close."* A writes one exit record per **venue position** close — the
  thing CT-20's fill observations actually describe.
- **Unit B — the node's Book runtime.** AD-29: the *virtual ledger* lives per
  binding; AD-33: *"the full realized result of a position, in R, credits the Bot
  that opened it"*; AD-40: R's money faces are *"frozen at admission"* per
  position. B writes one exit record per **virtual position** — the
  binding-scoped, Bot-attributed unit admission actually minted.

**The incompatible build.** On a netting account, or wherever two Bots trade one
instrument, A produces strictly fewer exit records than B. AD-41's bench counter
is *"a read-time fold over the exit-record stream"* — so A benches later than B,
or never. AD-33's whole-trade attribution has no answer under A for "which Bot
opened this venue position." AD-40's frozen `original_risk_amount` is per
admission, i.e. per virtual position, so A's exit records cannot carry the frozen
faces AD-41 mandates. Both units are conformant because the spine uses the bare
word "position" in AD-33, AD-34, AD-36, AD-37, AD-40 and AD-41 without ever
minting it as a noun.

**Severity: CRITICAL.**

**Closing clause (AD-40 + AD-41, noun minted in `qmf-core`).** *"`Position` is a
first-class core noun with two named kinds. The **virtual position** —
binding-scoped, Bot-attributed, minted at admission, carrying the frozen R faces
— is the unit of CT-29, of AD-40's R, of AD-33's attribution and of AD-41's
folds. The **venue position** is an observation-side noun only. CT-20 fill
observations attach to virtual positions through a declared, journal-bearing
attribution rule; where CT-18 declares `netting`, that rule is a mandatory Book
declaration and its absence is a bind-time `policy rejection`."*

---

### C-06 — A standing flatten intent can re-issue against unreconciled state and open a position

- **Unit A — the control-action emitter.** AD-36: *"On reconnect the node
  re-evaluates every standing intent against reconciled state and, if still
  unsatisfied, issues a **new command with a new identity**."*
- **Unit B — the reconciliation implementer.** AD-27: the adapter produces *"a
  complete read-back of venue orders, fills, positions, and balance over **a
  stated lookback**"* — stated, but by whom and with what floor is nowhere
  declared, and the do-not-default standing is not invoked for it. B states 24
  hours, a perfectly ordinary choice.

**The incompatible build.** Node outage of 30 hours. The venue-resident
protective stop (AD-33) filled at hour 3 — outside B's lookback. The read-back
shows no position and no fill. A's re-evaluation asks "is the scope flat?" and
gets an answer indistinguishable from "the position closed" and from "I cannot
see that far back." AD-27's verdict vocabulary is `reconciled | drift | unknown`
with no fourth term for *out of lookback*. If A reads *absent ⇒ still
unsatisfied* (defensible: the intent clears only on **observed** satisfaction,
and it observed nothing), it dispatches a new `close_position`. On a **hedging**
account that opens a new opposite position. Nothing in AD-27, AD-34, AD-36 or
AD-37 requires a close command's subject to exist, and `close_position` — unlike
`amend_protection` (AD-34) — is never said to carry its subject reference under
AD-27's identity discipline.

**Severity: CRITICAL.** A protection mechanism that opens a trade is the worst
failure in the increment.

**Closing clause (AD-27 + AD-36).** *"The reconciliation lookback is a mandatory
declared adapter parameter under the do-not-default standing. The verdict
vocabulary gains `out-of-lookback`, distinct from `unknown`. A standing intent
re-evaluates only against a `reconciled` verdict; `drift`, `unknown` and
`out-of-lookback` alarm (AD-14) and hold the intent open without dispatching.
`close_position` carries its subject reference under AD-27's identity discipline
and an absent or terminal referent resolves the command without submission —
never as a naked close."*

---

### C-07 — Six read-time folds, no fold contract; two of them can refuse on the trading path

The spine makes six things read-time folds: order state (AD-27), structure
lifecycle (AD-25), Book mode (AD-35), standing protection intent (AD-36), bench
count (AD-41), seat state (AD-41). AD-27 and AD-25 each name a **read-resolution
rule** as declared contract surface (CT-20's, CT-17's). **AD-35, AD-36 and AD-41
name none.**

- **Unit A — the paper-routing implementer.** A folds the Book-mode transition
  stream by AD-8's deterministic tie-break `(instant, writer, sequence)` — the
  ordering key the spine ships.
- **Unit B — the same implementer, one desk over.** B reads AD-8's other
  sentence: the tie-break is *"a replay-determinism device with no causal
  meaning — causality tests refuse at equal instants rather than tie-break."*
  Resolving *which control is in force* is a causal question, so B refuses at
  equal instants across writers.

**The incompatible build.** Two transitions land at the same instant from two
writers — an operator PAPER flip and an automatic kill-line-triggered paper route
are exactly the pair that will collide. A resolves deterministically (and picks
the winner by `WriterId` byte order, which encodes no authority whatsoever). B
**refuses the read** — and the node now cannot answer "am I live?" on the trading
path. AD-35 says *"live trading is unaffected"* when a paper target is absent;
AD-36 and AD-38 say fail closed. A fold that can refuse is a fold that can either
block all trading or, worse, let the intent-mint side and the AD-31 projection
side resolve **differently** — an intent minted LIVE and recorded as PAPER.

**Severity: CRITICAL.**

**Closing clause (Consistency Conventions + each of AD-35/36/41).** *"Every
read-time fold declares a **fold contract** as pinned versioned surface: the
ordering key, the knowledge-time bound, and the equal-instant disposition. Across
writers, control and mode folds resolve by **AD-37 rank**, never by `WriterId`
order. No fold used on the trading path may refuse: a fold that cannot resolve
returns the most restrictive state (fail closed), journals `data quality`, and
alarms."*

---

### C-08 — The standing-intent satisfaction predicate is undeclared, so `drain` and `suspend_new` can auto-clear

- **Unit A — the control-action emitter.** AD-36: the intent *"clears on observed
  satisfaction or an explicit operator clear."* A defines observed satisfaction
  per kind, mechanically: `flatten` satisfies when the scope is flat;
  `suspend_new` satisfies when no new entries are pending; `drain` satisfies when
  no pending orders remain.
- **Unit B — the same contract, other reading.** AD-36 also says *"`resume` is
  operator-only. Escalation automates; de-escalation does not."* B concludes that
  `suspend_new` and `drain` are standing states that satisfaction never clears —
  only an operator `resume` does.

**The incompatible build.** A's `drain` clears itself the moment the book of
pending orders empties, and new entries resume with no human in the loop. That is
precisely the automated de-escalation AD-36 exists to forbid, reached by
following AD-36's own satisfaction clause. B's build never auto-clears anything —
including `flatten`, which then requires an operator click after every kill-line
event, contradicting *"a 3am breach never waits for the operator."*

Second fork inside the same gap: A clears a `flatten` intent when the dispatched
command resolves `accepted-by-venue`; B clears it only on a reconciled flat
scope. A **partial fill** leaves residual size open with the intent cleared —
silently, permanently, and only visible in a report nobody reads at 3am.

**Severity: CRITICAL.**

**Closing clause (AD-36 / CT-30).** *"Each CT-30 action kind declares a
**mandatory satisfaction predicate** from a closed vocabulary:
`scope-flat-at-reconciled-verdict | no-pending-orders-at-reconciled-verdict |
never-auto`. `suspend_new` and `drain` are `never-auto` by rule — they clear only
by operator `resume`, matching `resume`'s operator-only status. `flatten`
satisfies only on a `reconciled` verdict showing the scope flat; a command
outcome never satisfies an intent."*

---

### C-09 — "The kill switch stops all trading" has no mapping into CT-30's own vocabulary, and one literal build traps every position

- **Unit A — the control-action emitter.** AD-36: the kill switch *"stops **all
  trading** including paper."* CT-30's action kinds are exactly
  `suspend_new | drain | flatten | resume`. A decomposes: kill switch =
  `suspend_new` at global scope. Entries stop; exits, protection amendments and
  protective-stop fills continue.
- **Unit B — the same clause, literal.** B implements "all trading" as a global
  block on the command pipe — the mechanism AD-27 already ships for `UNKNOWN`
  (*"the adapter refuses new commands on that stream"*). Exits are commands.

**The incompatible build.** In a black swan, B's kill switch traps every open
position behind its own protection: `close_position` refuses, `amend_protection`
refuses, and the kill **line** — which AD-37 ranks *below* protection actions at
rank 2 — cannot execute its automatic flatten because rank 1 has blocked the
pipe. The one control designed to save the account destroys it. AD-38 explicitly
protects exits from windows (*"It never blocks an exit, a protection amendment, a
protection action"*); **AD-36 grants the kill switch no such carve-out**, and its
scope is strictly larger.

**Severity: CRITICAL.**

**Closing clause (AD-36, stated once as a spine-level law).** *"**The
exit-preservation invariant:** no control action of any authority, at any scope,
may block a risk-reducing command — `cancel_order`, `close_position`,
`close_all`, or `amend_protection` in the risk-non-increasing direction. No CT-30
kind whose effect is a blanket command-pipe block may be minted. The kill
switch's maximal effect is `suspend_new` at global scope, plus `flatten` at
operator discretion; 'stops all trading' means 'stops all **entering**', in paper
and live alike."*

---

### C-10 — AD-37 permits rank ties, and two Books at one arbitration point bring two rank tables

- **Unit A — the arbitration-point implementer.** AD-37: *"exactly one
  arbitration point per stream"*, and *"Each control-action kind's rank is a
  declared, mandatory, non-defaultable field in **the Book's** control policy."*
  A reads ranks from the issuing Book's table.
- **Unit B — the same implementer, other reading.** AD-29: *"Several Books may
  bind one account: they share one BMS instance and one command stream."* One
  stream, one arbitration point, **two Book rank tables**. B requires a
  stream-level table and takes it from the BMS (the one-per-account layer whose
  cardinality exactly matches the arbitration point's).

**The incompatible build.** Book1 ranks `window_forced_flat` at 2; Book2 ranks it
at 4. A cross-Book collapse — which C-04 shows is reachable on a netting account
— has no defined winner, and AD-37's collapse rule says *"the rank winner supplies
the authority and reason, and every loser journals as a suppressed control
action."* Two conformant builds therefore write **different `closing_authority`
and different close reasons into permanent, append-only exit records** for the
identical market event.

Worse, AD-37's own rank 2 is a **bundle**: *"kill-line stand-down, window
force-flat, hold-time or boundary force-flat"* are four kinds at one rank, and
AD-37 states no intra-rank tie-break. Even inside one Book, two rank-2 actions
colliding leave attribution to arrival order — which AD-8 says carries no causal
meaning.

**Severity: CRITICAL.**

**Closing clause (AD-37).** *"The rank field is a **total order with uniqueness
enforced at AD-32 Layer 1**: two control-action kinds in one policy may not
declare the same rank (`invalid input`). The rank table is **BMS-declared**, one
per command stream, matching the arbitration point's cardinality; a Book bound to
a BMS whose table it contradicts is an `unsupported capability` refusal at bind
time. Arbitration resolves strictly by rank, with no arrival-order input."*

---

### C-11 — The re-decide-not-retry exemption is scoped to CT-30 control actions only, so a blocked protection amendment simply evaporates

- **Unit A — the Book-policy implementer (AD-34's move-to-breakeven ratchet).**
  The ratchet trigger fires while an `UNKNOWN` is outstanding on the stream.
  AD-27: *"protection commands are not exempt from the block."* The
  `amend_protection` refuses (`transient venue failure`). A re-evaluates the
  ratchet on the next tick and re-issues once the block clears.
- **Unit B — the same implementer, reading AD-27's prohibition.** *"Command retry
  is prohibited."* AD-36 rescues re-deciding — *"re-deciding is not retrying —
  AD-27's prohibition binds the command, not the decision"* — but that sentence
  sits inside AD-36, whose subject is **CT-30 control actions**
  (`suspend_new | drain | flatten | resume`). `amend_protection` is a **CT-19
  command**, and AD-33's `close_full` / `close_partial` / `tighten_protective_stop`
  are **CT-23 bot intents**. Neither is a CT-30 kind. B treats the refusal as
  final for that trigger and lets it go.

**The incompatible build.** A is arguably non-conformant (its behaviour is
indistinguishable from retry); B is conformant and leaves the stop un-ratcheted
after every transient blip. Identical price path, two risk postures, and the
divergence is invisible until the trade that needed the breakeven stop. AD-36's
whole standing-intent apparatus — journal-before-dispatch, read-time fold,
never-time-expire, alarm-on-undeliverable — is **denied to every risk-reducing
act that is not a CT-30 kind**, which is most of them.

**Severity: CRITICAL.**

**Closing clause (AD-36, generalized).** *"The standing-intent machinery
(journaled before dispatch, resolved as a read-time fold, re-decided rather than
retried, never time-expiring, alarming loudly when undeliverable) binds **every
risk-non-increasing act**, not only CT-30 kinds — naming `amend_protection`
(AD-34), `close_full` / `close_partial` / `tighten_protective_stop` (AD-33), and
every protective close. AD-27's re-decide exemption is restated at the level of
'protection intents' generally."*

---

### C-12 — An `amend_protection` whose position vanishes to a stop fill: a named outcome in one build, a stream block in the other

- **Unit A — the `amend_protection` implementer (AD-34).** AD-34 states there is
  *"no dedicated response message"* — the outcome arrives on the ordinary
  execution-event surface. The position's protective stop fills between submit
  and read-back. A reasons by exact analogy with AD-27's cancel rule (*"a cancel
  resolved by read-back is `accepted-by-venue` only if the read-back also shows no
  fill … otherwise it resolves `rejected-by-venue (superseded-by-fill)`"*) and
  resolves `rejected-by-venue (superseded-by-fill)`.
- **Unit B — the adapter author.** AD-27's read-back rule is written **for
  cancels** and B declines to extend a rule that the spine scoped. B instead
  applies AD-27's general rule: an observation with no legal transition *"is
  recorded, annotated with a typed `out-of-sequence` edge, and **forces the owning
  command to `UNKNOWN` pending resolution**"* — and the adapter never clears its
  own block, so the stream is blocked until an operator calls `resolve_unknown`.

**The incompatible build.** A stop filling while an amend is in flight is a
**daily** event in live trading. B's build converts it into an operator interrupt
that freezes the whole `(VenueId, account)` command stream — including every
other Book's exits on that account (AD-29's named coupling). A's build keeps
trading. Both write a different outcome class into permanent evidence for the same
market event, so the two systems' reconciliation baselines and CT-32 suppression
accounting diverge forever.

**Severity: CRITICAL.**

**Closing clause (AD-27, extended by AD-34).** *"The read-back resolution rule
generalizes from cancels to **every command whose subject can terminate
independently**: a command whose subject (order or position) is observed terminal
at or after the submit stamp resolves `rejected-by-venue
(superseded-by-terminal-subject)` — a named outcome, never `UNKNOWN`, never a
stream block. The subject-terminal observation is the named resolving evidence."*

---

### C-13 — The account's settlement currency has no declared source, and venue-performed conversions are unnamed

- **Unit A — the binding implementer.** AD-40: *"Numeraire is USD system-wide in
  V1 … binding a Book to an account in another currency is a `policy rejection`."*
  A needs the account's currency. AD-28 makes *"instrument/account metadata
  snapshots"* adapter-produced core value types, so A reads it from there.
- **Unit B — the same implementer.** AD-28's CT-18 field roster is enumerated in
  the spine and **does not contain account currency** — it lists money exponent,
  equity nativeness, position model, and the rest. AD-9's Account noun does not
  declare a currency either. B refuses to invent a field the roster omits and
  takes the currency from the Book's own `accounting_currency` (AD-30), treating
  the venue as untrusted (AD-9: broker identity is deployment configuration).

**The incompatible build.** Where the venue reports a currency the operator did
not expect, A refuses the binding and B accepts it — and B then stamps
`Money(USD)` onto an EUR account's integers. **Every money figure in permanent
evidence is mis-tagged**, `fp1`-sealed, and AD-40's dimensional checker cannot
catch it because the tag it checks is the wrong tag consistently.

**The second, deeper half.** `realized_pnl` (AD-41) comes from venue fills. For a
EURJPY position on a USD account, the venue computes P&L in USD **by converting at
a rate it chose and may not publish**. AD-40 says *"a silent currency conversion
is the one error no report shows"* and *"no rate source is ratified."* Unit A
stores the venue's USD figure verbatim as `Money(USD)`. Unit B refuses it as an
unratified conversion — which makes every non-USD-quoted instrument untradeable in
V1. Both readings are conformant, and the choice silently decides whether the
system can trade more than a handful of pairs.

**Severity: CRITICAL.**

**Closing clause (AD-28 + AD-40).** *"CT-18's field roster gains **account
settlement currency**, `measured-at-connection`, verify-or-refuse; a binding whose
account currency is not the Book's `accounting_currency` is a `policy rejection`
at bind time. Separately: **a money figure the venue itself derived by conversion
is settlement evidence, not a QMX conversion.** It is legal as `Money(numeraire)`
carrying a declared `converted_by = venue` provenance flag and the venue's stated
rate where published, and is explicitly exempt from AD-40's unratified-rate-source
clause — which governs QMX-performed conversions only."*

---

### C-14 — The closed unit-kind vocabulary cannot type AD-40's own admission formula

AD-40 closes the unit-kind vocabulary: `money(currency) | price-delta(instrument)
| quantity(unit) | r-multiple | rate(money-per-r) | count | dimensionless-ratio |
duration | instant`. Exactly one rate kind exists, and it is money-per-R.

- **Unit A — the dimensional-checker author.** A implements the checker as
  specified: *"Every formula declares the unit-kind of each input and of its
  output, and a symbolic checker refuses (`invalid input`) on mismatch."* A then
  attempts to type the admission identity that AD-40 itself requires —
  `original_risk_amount [money]` from `original_risk_distance [price-delta(i)]`
  and the admitted `quantity [quantity(u)]`. The conversion factor is the
  instrument's tick/contract value: **money per price-delta per quantity.** No
  such kind exists. A refuses the formula. **No position can ever be admitted.**
- **Unit B — the Book-template author.** B reads *"a closed unit-kind vocabulary,
  **addable never redefined**"* and adds the kind it needs, naming it locally.
  Another Book adds the same kind under another name.

**The incompatible build.** A's system cannot open a trade; B's two Books declare
formulas typed under incompatible vocabularies, so their `worked_example`s cannot
cross-validate, their template fingerprints encode different unit taxonomies, and
AD-32's Layer 1 parity check passes both. The AD that exists to make a second
FORM-0006 undeclarable is **incomplete on the one formula the whole system
depends on**, and "addable" names no adder.

**Severity: CRITICAL.**

**Closing clause (AD-40).** *"The vocabulary is extended now with the instrument
contract kinds admission arithmetic requires:
`value-per-price-delta(instrument, currency)` — the tick/point value, sourced
from an AD-9 dated instrument-metadata record as an exact rational — and
`quantity-per-lot(unit)` where a venue's quantity unit differs from its contract
unit. The reference worked example ships as
`original_risk_amount [money(c)] = original_risk_distance [price-delta(i)] ×
quantity [quantity(u)] × value_per_price_delta(i,c) [money(c)/(price-delta(i)·quantity(u))]`.
**Unit-kind additions are spine amendments only — never per-Book, never per-template.**"*

---

### C-15 — Exact-rational canonical form is unpinned, so equal values get different fingerprints and AD-10's collision rule cannot see it

- **Unit A — the CT-29 exit-record author.** AD-40: `r_multiple` is *"a
  dimensionless **exact rational**"*. A stores it unreduced as the division
  produced it: `{"n": 6, "d": 4}`.
- **Unit B — the CT-32 performance-result author.** B reduces to lowest terms:
  `{"n": 3, "d": 2}`.

**The incompatible build.** AD-10 pins the `fp1` recipe down to key ordering, NFC
normalization and the prohibition of nulls and floats — but says nothing about the
**canonical form of a rational**. Two mathematically identical results therefore
carry **different fingerprints**, so AD-16's dedup silently fails, sandbox merges
produce two records where one work item happened, and AD-10's collision detector
never fires because the hashes differ rather than colliding. The same hazard runs
through `Money`: AD-7 makes **scale** part of the tag, so `Money(USD, scale=2,
100)` and `Money(USD, scale=4, 10000)` are arithmetically equal under AD-7's
auto-promotion and **identity-distinct** under AD-10. AD-28 pins target scales for
venue *decode* only; every computed Money in `qmf-risk` is unpinned.

**Severity: CRITICAL.** This is the increment's purest identity fork: undetectable,
permanent, and it lands on the two records (CT-29, CT-32) that gate live money.

**Closing clause (AD-7 + AD-10).** *"An exact rational in identity content is
canonical: reduced to lowest terms, denominator strictly positive, sign carried on
the numerator, serialized `{"n": int, "d": int}` with both keys always present.
A `Money`, `Price`, `Quantity` or `PriceDelta` value entering identity content
carries the **declared canonical storage scale for its value class** — pinned in
the owning contract exactly as AD-28 pins venue decode scales — so equal value
implies equal fingerprint by construction."*

---

### C-16 — Paper mode changes the AD-29 binding tuple while AD-35 insists it is "not a new object", and AD-41 needs a routing path the Book-level mode cannot express

- **Unit A — the paper-routing implementer.** AD-35: paper is *"a Book-level
  mode … expressed as a dated change of the Book's **execution binding** — a record
  change, not a new object."* A flips the mode and keeps one Book, one binding,
  one ledger, one cycle.
- **Unit B — the registry author.** AD-29's binding tuple contains `role`, and
  the paper target is a `paper-validation` / `paper-benched` account with a
  different `AccountId` and possibly a different `VenueId`. **A paper flip
  therefore mints a new binding identity.** AD-29: *"Virtual ledger, cycle,
  budget, breaker counters, exposure, mode and protective scope all live per
  binding."* B resets all of them on the flip.

**The incompatible build.** A's flip preserves the loss budget and breaker
counters across the paper excursion; B's resets them. AD-35 says paper balance is
*"frozen at flip"* — which reads as A — and AD-30 says a new binding means *"a
fresh cycle's money"* — which reads as B. Neither is wrong.

**The second half is sharper.** AD-41: *"A benched seat routes to the Book's paper
target and **the Book stays live**."* That requires a **per-seat** routing
override — a bot in paper while its Book is LIVE. AD-35's mode is Book-level and
AD-35 permits exactly *"one active paper-routing target per live binding at an
instant"*. So there are two routing mechanisms (Book-mode paper, seat-bench
paper) and only one is contracted. Unit A, having implemented Book-level mode as
the only mechanism, **cannot express AD-41's own requirement**.

**The third half is an evidence fork.** A benched bot's records land in the paper
role-scoped namespace (AD-12) while its Book's other bots' land in live.
AD-31: *"a projection resolves inside one role-scoped namespace. A projection
spanning roles exists only as the explicitly-declared cross-role read of AD-35."*
AD-35's cross-role permission is scoped to *"a decay cohort read"*. So **reading
your own Book's journal becomes an unpermitted cross-role read** the moment one
seat is benched.

**Severity: CRITICAL.**

**Closing clause (AD-29 + AD-35 + AD-31).** *"Routing is separated from binding.
A per-intent `execution_target` is resolved at intent mint from (Book mode, seat
state, active-control set) and enters the command record's identity (AD-35's
existing once-per-intent rule); Book-mode PAPER and a seat bench both select the
paper target **without changing the AD-29 binding identity**. `role` is carried on
the execution-target record, not in the binding tuple. AD-31's cross-role clause
widens: any entity projection over an entity that operated in more than one role
is a declared cross-role read, permitted, with role carried on every row and never
aggregated across roles without an explicit declaration."*

---

### C-17 — AD-31 requires Book identity on every risk-domain journal event; the neutral venue CM cannot carry it, so the Book journal has no trades in it

- **Unit A — the venue CM author.** AD-28: the connection manager *"holds the
  `WriterId`, stamps writer + sequence, and calls sinks synchronously"*, and
  nothing imports `qmf-venue` or `qmf-risk`. The CM writes the `order`, `fill`
  and `data quality` events. It knows nothing about Books — by design, and the
  Dependency-direction rule forbids it learning.
- **Unit B — the projection reader.** AD-31: *"every risk-domain journal event and
  every risk record carries, as **identity fields**: the Book-definition
  fingerprint, the binding identity, and — where the act concerns one bot — the
  Bot identity plus its seat binding."* B selects the Book journal by entity
  identity.

**The incompatible build.** B's Book journal — *"the operator's logbook"* — contains
decisions, risk transitions, control actions and promotions, and **no orders and
no fills**. The single most important thing an operator opens a logbook to see is
structurally absent. A third implementer resolves it the other way, threading Book
identity into the command payload the CM stamps, creating a de facto
`qmf-venue → qmf-risk` coupling the Dependency-direction rule forbids.

There is a rescue path the spine does not take: the **command record** is minted
above both layers and does carry the binding identity, and the CM's events already
cite the command fingerprint (AD-27's identity discipline). But AD-31 says
*"carries, as identity fields"* — a join is not a carried field — and AD-16 warns
*"readers never union header refs with edges"*, so no implementer will reach for a
join uninvited.

**Severity: CRITICAL.**

**Closing clause (AD-31).** *"Risk-domain journal events split into two classes.
**Risk-authored** events (decision, risk transition, control action, promotion),
minted by the risk/node layer, carry Book-definition fingerprint, binding identity
and — where applicable — Bot identity and seat binding as identity fields.
**Venue-authored** events (order, fill, data quality), minted by the neutral CM,
carry the **command record's content fingerprint**, and the projection joins
through it; the command record carries the binding identity as an identity field.
The join is pinned versioned CT-25 surface, not implementer judgment."*

---

### C-18 — No edge kind links a venue outcome back to the control-action intent it enacts, so AD-36's safety fold rides on `correlation_id`

- **Unit A — the control-action emitter.** AD-36: a protection action is
  *"journaled **before** dispatch"* by the node's writer; *"Is this account under
  a standing flatten intent?"* is a read-time fold over the control-action stream.
- **Unit B — the venue CM.** The command's submission and outcome events, and the
  fill observations that prove satisfaction, are written to a **different**
  writer-scoped stream (AD-21, AD-28).

**The incompatible build.** Satisfaction is therefore a **cross-stream** fold, and
AD-21 is explicit: *"causal linkage across streams uses AD-16 typed edges, never
timestamps."* AD-16's edge kinds are `supersedes | promoted-from | occurrence-of |
corroborates | disagrees-with | confirmed-as | confirmation | invalidation |
interaction | continues-as`, plus AD-27's `out-of-sequence`. **None of them links
an enactment to an intent.** Unit A joins on `correlation_id` — which AD-21
declares *"a linking annotation **excluded from `fp1` identity** by explicit
versioned declaration"* and AD-31 declares tracing-only, never interchangeable
with evidence linkage. Unit B mints an ad-hoc edge kind locally, which AD-16 makes
a spine-amendment act.

So the safety-critical question — *is the flatten I ordered actually done?* —
either depends on a non-identity tracing annotation that no rule guarantees is
present, correct, or preserved through gap replay, or on an edge kind that does
not exist. The same hole swallows AD-37's *"the arbitration record's fingerprint"*
and AD-36's *"the would-have-been action by fingerprint"*.

**Severity: CRITICAL.**

**Closing clause (AD-16).** *"One edge kind is added: **`enacts`** — from a
command record or an outcome observation to the CT-30 control-action record it
enacts, identity-bearing, append-only. AD-36's standing-intent fold, AD-37's
arbitration record and AD-41's suppression accounting resolve through `enacts`
edges and never through `correlation_id`."*

---

### C-19 — A scheduled SQS baseline refit forks the AD-35 decay cohort, daily

- **Unit A — the SQS producer author.** AD-39: *"The baseline is a fingerprinted
  derived artifact … a refit mints a new artifact with a `supersedes` edge."*
  AD-22 is categorical about identity: *"the **ordered named input set**, each
  carrying … for derived inputs — **the upstream artifact's fingerprint**"*, and
  *"an element missing from the fingerprint is a contract defect."* A includes the
  baseline artifact's fingerprint in the SQS configuration identity. It must.
- **Unit B — the decay-cohort implementer.** AD-35's `cohort_key` includes *"the
  configured producers' fingerprints"*. B compares two streams only when they
  match.

**The incompatible build.** AD-39's own recorded corpus evidence mentions *"daily
and weekly refits"*. Every refit mints a new baseline fingerprint, therefore a new
SQS configuration fingerprint, therefore a **new cohort key**. The decay cohort
resets on the refit cadence — daily, in the corpus's own shape. AD-41's entire
purpose (*"the collection that makes it possible starts now, because it cannot be
back-filled"*) is defeated by a mechanism AD-39 ratified in the same sitting.
Both units are perfectly conformant; the contradiction is between AD-39's refit
discipline and AD-22's derived-input identity rule, mediated by AD-35's cohort key.

**Severity: CRITICAL.** It silently destroys the one thing this AD-group exists to
make possible.

**Closing clause (AD-39 + AD-35).** *"A refit-cadenced baseline is a declared
**refit series**: the configuration cites the series identity plus the refit
policy fingerprint (conditioning window, cadence, refit rule) as its derived-input
identity; the concrete baseline artifact rides each sample as occurrence
provenance, cited by fingerprint and fully reconstructible, but outside the
producer's configuration identity. AD-35's `cohort_key` reads the configuration
fingerprint so computed. A change to the refit **policy** still forks the
cohort — a refit under an unchanged policy does not."*

---

### C-20 — AD-24's heavy-by-default plus AD-39's block-on-refusal deadlock at bring-up, and a VPS migration silently blocks every door

- **Unit A — the SQS producer author.** AD-24: *"**Until the live-path rung has a
  recorded baseline, every configuration is heavy by default and a light claim is
  refused at the gate**,"* and *"A heavy configuration's synchronous entry point
  returns `unsupported capability`."* A declares heavy — the only conformant
  declaration before a baseline exists.
- **Unit B — the Book door.** AD-39: *"a **conservative sentinel** — undefined,
  unreachable, stale or refused ⇒ **hard block**, never a last-known-good value,"*
  and *"An unavailable or stale reading returns a typed refusal … and the door
  treats it as a block."* B blocks.

**The incompatible build.** Both units are conformant and the system is dead: the
door calls SQS synchronously at the decision instant, gets `unsupported
capability`, and blocks every entry, forever, until a live-path rung baseline
exists. Nothing in AD-32's three admission layers, AD-29's bind-time capability
check, or AD-13 names "record the live-path rung baseline" as a bring-up
prerequisite, so no implementer is told when to do it.

**The recurrence is worse than the bootstrap.** AD-13 scopes baselines to a
*"declared (OS, CPU-class) tuple."* Move the VPS, or let the provider migrate the
instance to a different CPU generation, and **no baseline exists for the new
tuple** ⇒ every configuration reverts to heavy ⇒ SQS's synchronous entry point
refuses ⇒ every door hard-blocks. A silent, total trading halt caused by an
infrastructure event, with a `policy rejection` as its only symptom.

**Severity: CRITICAL.**

**Closing clause (AD-24 + AD-32).** *"A light claim benchmark-proven on tuple T1
remains in force on a new tuple T2 as a **provisional light claim** — it alarms
(AD-14), journals `data quality`, and requires re-proof within a declared window,
after which it reverts to heavy. It never silently reverts mid-session. AD-32's
Layer 2 shakedown gains a named prerequisite: 'the live-path rung has a recorded
AD-13 baseline on this deployment's declared (OS, CPU-class) tuple' — so the
deadlock surfaces at admission and never at the first tick."*

---

## 3. High — divergence is costly and reaches evidence or reports, but a gate or an operator can still see it

### H-01 — Re-admission scope is undeclared: every UI edit is a new Book requiring a full three-layer admission, or a signature attests a superseded fingerprint

- **Unit A — the platform settings UI author.** AD-30: *"UI edits **mint a new
  version, never mutate** one,"* and configurable means UI-editable. A ships an
  editor that lets the operator change a leash number and re-bind.
- **Unit B — the admission implementer.** AD-32: *"a new Book or BMS proves itself
  in three layers"*; AD-30: a changed number is *"a **new Book identity**"*. B
  therefore demands a fresh Layer 2 demo shakedown and a fresh Layer 3 operator
  signature for every edit.

**Divergence.** B's platform is unusable (a demo shakedown per number tweak);
A's platform binds edited Books live under a signature that attests a **superseded
fingerprint** — which AD-18 forbids in spirit (*"the signature attests the exact
words the human read"*) but which nothing enforces, because the AD-18 card is
never required to cite the Book-definition fingerprint as an identity field.

**Severity: HIGH.**

**Closing clause (AD-30 + AD-32 + AD-18).** *"Every template variable declares
`admission_impact ∈ resign | relint | none` alongside `ui-editable`. Changes
touching `admission_bar`, `money_rules`, `required_venue_capabilities` or
`charter` are `resign`; `leash_grammar` numbers are `relint`. AD-18's card carries
the Book-definition fingerprint as an identity field, making a stale signature
structurally impossible."*

### H-02 — Venue-managed trailing is an unauthorized protective-stop mutator under AD-36's "nobody else"

- **Unit A — the Book-template author.** AD-34: venue-managed trailing *"is legal
  only where declared and explicitly opted into by a Book."* A opts in.
- **Unit B — the AD-36 authority implementer.** AD-33: *"Only Book policy or a
  protection authority moves it."* AD-36's authority list is closed: operator;
  Book policy through pre-declared trigger classes; *"**Nobody else**."* The venue
  is not on the list, and AD-27/AD-36 both say the adapter never initiates.

**Divergence.** B classifies each inbound trailing-stop change as an
unauthorized protective-stop mutation with no CT-30 record behind it — so it
either alarms permanently on normal operation, or attempts to revert it via
`amend_protection`, which AD-34 constrains to risk-non-increasing changes, so
reverting a trail outward **refuses** and the system deadlocks in a permanent
alarm. A treats it as ordinary state.

Second, smaller fork in the same clause: AD-33 says the stop moves *"only toward
entry"*; AD-34's ratchet is move-to-breakeven; a trailing stop moves toward entry
and then **past it** into profit. One build reads "toward entry" as monotone
risk-reduction (past entry allowed); the other reads it literally (entry is the
floor) and cannot implement trailing at all.

**Severity: HIGH.**

**Closing clause (AD-33 + AD-34 + AD-36).** *"Venue-managed trailing is a named
**delegated protection authority** (`authority_kind = venue-delegated`),
admissible only where CT-18 declares it and the Book opts in; each pushed change
mints a CT-30 control-action record of kind `protection_amendment` with that
authority, so the AD-37 arbitration point and AD-36's accounting see it. The
direction rule is restated as **risk-non-increasing relative to the frozen
`original_risk_distance`**, replacing 'toward entry'."*

### H-03 — The bench fold's knowledge-time bound at intent mint is undeclared, so the (N+1)th entry races the Nth exit record

- **Unit A** evaluates the bench fold at intent mint against the persisted
  exit-record stream — missing an exit whose fill observation has arrived but
  whose CT-29 record has not yet landed.
- **Unit B** evaluates against a fold that includes in-flight fills.

**Divergence.** One build lets the entry after the threshold-crossing loss
through; the other benches it. That is precisely the leash's job, and both builds
pass every gate.

**Severity: HIGH.**

**Closing clause (AD-41 + AD-27).** *"The bench fold's knowledge-time bound is
'the last exit record persisted and journaled at the intent-mint instant', and
AD-27's recording-precedes-interpretation rule extends: a fill observation that
closes a virtual position must have its CT-29 exit record persisted before any
subsequent intent on the same (Book, Bot) seat is minted; otherwise the intent
refuses (`stale evidence`)."*

### H-04 — There is no veto accounting to match AD-36's suppression accounting, so door refusals read as decay

AD-41 mandates *"suppression accounting — counts of actions suppressed in the
period by authority and reason, **so gates never read as decay**."* But AD-36
reserves `suppressed` for *"an already-authorized action discarded because a
higher authority won"*, and AD-38 puts window refusals on the **veto path**
instead. SQS blocks (AD-39), admission-bar failures (AD-32), bench blocks (AD-41)
and budget refusals are all veto-path, and **the veto path has no accounting
mandate anywhere**.

- **Unit A — the SQS door implementer.** AD-39 says the door *"treats it as a
  block"* and mandates no journal event. A records nothing.
- **Unit B — the window implementer.** AD-38 mandates the veto `decision` event
  with the refusing door, the would-have-been action and the controlling
  fingerprint. B records everything.

**Divergence.** In A's build, a month of tight-spread blocking is invisible in
CT-32 and the bot's R-denominated decision quality collapses with no recorded
cause — the exact failure AD-41's suppression accounting exists to prevent, taken
in through the one door AD-41 does not cover.

**Severity: HIGH.**

**Closing clause (stated once, in AD-36).** *"**Veto accounting**, symmetric to
suppression accounting: every door refusal — window, SQS, admission bar, bench,
budget, capability — mints a `decision` event on the veto path carrying the
refusing door identity, the would-have-been action fingerprint and the
controlling evidence fingerprint. CT-32 carries veto counts by door alongside
suppression counts by authority."*

### H-05 — `denied-locally` versus a door refusal: one build pollutes the venue observation stream

AD-27: *"`denied-locally` is an **outcome, never a refusal** … every outcome,
`denied-locally` included, mints an **observation record** and a journal event."*
AD-33: the Book door *"executes or refuses with a recorded, journal-bearing
reason."*

- **Unit A** classifies a Book-door refusal as `denied-locally` and mints a CT-20
  observation for it — which AD-27 elsewhere forbids (*"adapters never synthesize
  venue observations"*) and which breaks AD-27's cardinality law and the
  reconciliation baseline with events the venue never saw.
- **Unit B** classifies it as an AD-11 typed refusal plus an AD-38-style veto
  `decision` event, and mints no observation.

**Severity: HIGH.**

**Closing clause (AD-27).** *"`denied-locally` is minted **only by the venue
adapter's own pre-submission checks** — undeclared capability, blocked stream,
malformed command — and is the only local denial that mints a CT-20 observation.
Every authority-layer refusal above the adapter (Book door, admission bar,
window, SQS, bench, budget) is an AD-11 typed refusal plus a veto-path `decision`
event, and never a CT-20 observation."*

### H-06 — `evidence_requirements.account_role` invites the paper-performance gate AD-32 exists to forbid

AD-32: *"**no trial period, probation window, or paper-performance gate exists**
(redemption loops stay dead)."* The very same AD then gives `admission_bar`
requirements an `evidence_requirements` field carrying *"world, **account
role**, minimum evidence window."*

- **Unit A** writes `account_role = live` (consistent with AD-32's intent).
- **Unit B** writes `account_role = paper-validation` and has thereby built a
  paper-performance gate — conformantly, using AD-32's own field.

**Severity: HIGH.**

**Closing clause (AD-32).** *"`evidence_requirements.account_role` may not name a
paper role in a bar that gates a `role = live` binding; such a bar is a
`policy rejection` at Layer 1."*

### H-07 — The paper target's own stream is never reconciled and its `UNKNOWN` never alarms, so paper evidence stops silently

AD-35: *"The target is excluded from the live binding's reconciliation drift
check."*

- **Unit A** reconciles the demo stream on its own terms (it is its own
  `(VenueId, account)` stream).
- **Unit B** reads "excluded" as excluded, full stop: the demo stream is never
  reconciled, so per AD-27 it never gates, never verifies, and an unresolved
  `UNKNOWN` on it blocks it forever with nobody watching — AD-27's block clears
  only by an explicit application `resolve_unknown`.

**Divergence.** In B, AD-35's *"evidence keeps flowing"* quietly stops, and every
subsequent decay verdict rests on a truncated paper series with no marker.

**Severity: HIGH.**

**Closing clause (AD-35).** *"The paper target is reconciled **as its own
binding**; the drift exclusion applies only to comparing demo state against the
live binding's expected state. A block or unresolved `UNKNOWN` on a paper stream
raises the same AD-14 alarm class as a live one — a silent paper outage corrupts
every decay verdict computed after it."*

### H-08 — SQS's input BarSpec is unconstrained, so a bar-stale spread can gate live money and pass every gate

- **Unit A** configures SQS on a quote-sampled channel (AD-39's corpus evidence
  mentions per-quote cadence) with a maximum age inside the live-path rung.
- **Unit B** configures it on a 1-minute BarSpec — fully legal under AD-22, which
  lets a configuration declare any BarSpec — and declares its own maximum age
  accordingly.

**Divergence.** B's sensor is structurally useless at the decision instant, and
the door cannot tell: it sees a score and a hard-block flag. AD-39 exists
precisely to prevent *"a stale spread passed through in the one moment the sensor
exists for"* and does not constrain the one field that decides it.

**Severity: HIGH.**

**Closing clause (AD-39).** *"SQS's live-spread input is constrained to a
tick/quote-sampled channel with a declared maximum age not exceeding the Book's
mandatory, non-defaultable `decision_freshness_bound`; a configured SQS exceeding
it is refused at the door, not blocked-through."*

### H-09 — "Instrument class" (AD-39's threshold key) is defined nowhere

AD-39: *"a hard-block threshold **per instrument class**."* The spine defines
asset class (AD-9 dated metadata), currency exposure (AD-38) — no instrument
class. Unit A keys thresholds on AD-9's asset-class record; Unit B mints a
taxonomy inside the SQS configuration. Both are identity-bearing, so two Books'
thresholds are not comparable and neither can be reused. A missing record: A
blocks (AD-39's conservative sentinel says undefined ⇒ block); B falls back to a
default class, which AD-39's own sentinel forbids in spirit.

**Severity: HIGH.** **Closing clause (AD-39 + AD-9).** *"The class key is a dated
AD-9 instrument-metadata record kind `instrument_class`, operator-declarable and
correctable; AD-38's missing-record rule is mirrored verbatim — a missing class
record means the instrument is treated as blocked and journals `data quality`."*

### H-10 — `supersedes` is a linear correction chain in five ADs and a branching version graph in AD-30

AD-30: *"an append-only version graph; `supersedes` edges as commits; a diff
derivable between any two versions."* A version graph branches. AD-25 (refit),
AD-28 (observation profile), AD-39 (baseline refit) and AD-16 all use
`supersedes` as a linear chain whose **head** must be uniquely resolvable.

- **Unit A** enforces at-most-one-outgoing-and-one-incoming so "current" is
  well-defined — and the operator cannot fork a Book template.
- **Unit B** permits branching — and "the current version" and AD-25's *"the
  lineage head keeping the first observed-at"* become ambiguous system-wide.

**Severity: HIGH.** **Closing clause (AD-16).** *"`supersedes` is linear — at most
one outgoing edge per subject, unique head. AD-30's version graph uses a distinct
edge kind `branches-from`, where multiple heads are legal and 'current' is a
separate dated pointer record, never inferred from the graph."*

### H-11 — Exact-version `required_producer_contracts` cascades a metric bug fix into a money-cycle reset for every Book

AD-30: a Book declares *"`required_producer_contracts` (the format versions of
every measure it reads)"* and *"an uninterpretable contract format version is an
`unsupported capability` refusal."* AD-41: *"an arithmetic change is a
format-version mint."*

**Divergence.** Unit A pins exact versions (what AD-30 says) — so a corrected
Sharpe implementation refuses every Book that cites the old version, forcing a
Book re-version, a new fingerprint, a new binding, and (AD-30) *a fresh cycle's
money* across the estate. Unit B pins a set or a floor, which AD-30's wording does
not clearly permit but does not forbid.

**Severity: HIGH.** **Closing clause (AD-30 + AD-41).** *"Each cited producer
carries `{contract_id, version, on_version_change ∈ refuse |
accept-and-mint-new-book-version | accept-with-continues-as}`. A performance-metric
format-version mint never forces a Book re-version by itself; the CT-32 result
carries both versions so AD-32's parity check stays exact."*

### H-12 — The `decision` event has no declared outcome discriminator, so `veto_ledger` membership is a presence test

AD-31 keeps the legacy `veto_ledger` as a projection over AD-21's seven types.
The veto path uses `decision` events (AD-38) — and so does the ordinary
authorized decision. Unit A discriminates on the presence of a `refusing_door`
key (legal under AD-10's omit-don't-null rule, and fragile); Unit B mints a
declared enum. Two different `veto_ledger`s.

**Severity: HIGH.** **Closing clause (CT-13).** *"The `decision` event declares a
mandatory closed `outcome` field — `authorized | refused-by-door | suppressed` —
with the refusing-door / suppressing-authority reference; all projections select
on the declared field, never on key presence."*

### H-13 — The exit record's "suppressing authority" loses the losers that suppression accounting needs

AD-41's exit record carries *"the suppressing authority where a control caused the
close"*; AD-37's collapse rule says the rank winner supplies authority and reason
and *"every loser journals as a suppressed control action."* Unit A records the
winner in that field (there is no suppressing authority in a collapse — the winner
is the closer); Unit B records the loser list. CT-32's suppression counts need the
losers and would double-count if it read them off exit records.

**Severity: HIGH.** **Closing clause (AD-41 + AD-37).** *"The exit record carries
`closing_authority` (the winner) and a reference to the arbitration record.
Suppression counting reads the control-action stream through `enacts` edges
(C-18), never the exit record; the exit record never carries suppression counts."*

### H-14 — `risk-non-increasing` is undefined per protection side, so target amendment is either free or impossible

AD-34 constrains `amend_protection` *"at contract level to **risk-non-increasing**
changes"*; AD-33 forbids an intent that would *"extend a target beyond the Book's
declared envelope"* — implying targets may move within it. Unit A applies the
constraint to the stop side only (targets carry no risk); Unit B applies it to
both sides, so a target may only move closer — and since AD-34 forbids
cancel-then-place, B's Books **cannot extend a target at all**, ever.

**Severity: HIGH.** **Closing clause (AD-34).** *"`risk-non-increasing` is defined
per side: a stop-side change may not increase `|price − entry|` in the loss
direction relative to the frozen `original_risk_distance`; target-side changes are
governed by the Book's declared envelope (AD-33), not by the risk test. The
contract-level check binds the stop side only."*

### H-15 — AD-32's Layer 1 worked-example recomputation invites linter-local arithmetic, an AD-23 defect

AD-32 Layer 1: *"**worked-example arithmetic recomputed** from the template's own
declared numbers."* Unit A implements the arithmetic inside the linter (fast, no
producer resolution at registration time) — which is a re-implementation of
arithmetic a governed producer publishes, an AD-23 contract defect. Unit B invokes
the cited producers, and cannot lint a template whose producers are unresolvable.

**Severity: HIGH.** **Closing clause (AD-32).** *"Layer 1's recomputation invokes
the **cited producer contracts themselves**, resolved from
`required_producer_contracts`; a producer that cannot be resolved at registration
is an `unavailable dependency` refusal, never a skipped check and never
linter-local arithmetic."*

### H-16 — `admission_bar`'s "ordered set" versus AD-17's canonical order forks Book identity on semantically identical bars

AD-32: *"an **ordered set** of named requirements."* AD-17: collections are
*"canonically ordered by child fingerprint ascending unless the owning contract
explicitly declares the collection order-significant."* Unit A treats AD-32's
wording as that explicit declaration; Unit B canonicalizes. Two operators writing
the same three requirements in different orders get **different Book
fingerprints, different bindings and different money cycles** for identical rules,
and AD-16's dedup silently fails. AD-30's *"Declared sections, ordinal and named"*
carries the same ambiguity for section ordinals.

**Severity: HIGH.** **Closing clause (AD-30 + AD-32).** *"Each template section
declares whether its collections are order-significant. `admission_bar` is a
**set**, canonically ordered by `measure_identity` ascending for fingerprint
purposes, with a separate `display_ordinal` declared display-only. Section
ordinals are display-only."*

### H-17 — `not yet ruled` has no pinned encoding, so blankness is a presence test in one build

AD-32's threshold is *"an exact rational **or the explicit literal `not yet
ruled`**"* — a sentinel in a field AD-10 forbids nulls in and AD-22 forbids
sentinels in. Unit A encodes a discriminated union; Unit B omits the `threshold`
key and relies on a present `gap_ref`. Different fingerprints for the same blank
bar, and in B *"blank blocks live money"* becomes a key-presence test.

**Severity: HIGH.** **Closing clause (AD-32).** *"`threshold` is a mandatory
discriminated union with a pinned tag set — `{"ruled": <exact rational>}` |
`{"not_yet_ruled": {"gap_ref": …}}` — key always present, so blankness is a
declared value and never an absence."*

### H-18 — Widen-never-shrink has no declared enforcement point, and the effective-window fold rule is unstated

AD-38: *"A later revision may pull a start earlier … or push an end later; it may
**never narrow, cancel, or retro-invalidate** a window that has had effect."*
AD-21: *"a provider revision is a new artifact"* and *"corrections are appended,
never overwrite."*

- **Unit A** enforces at intake, refusing a narrowing revision — destroying
  provider evidence AD-21 requires it to keep.
- **Unit B** accepts every revision and enforces at read time — but the effective
  window is now a fold whose rule is unstated: union of all revisions? latest
  revision monotonically widened? Those differ whenever revision 3 narrows below
  revision 1 while revision 2 was wider.

**Severity: HIGH.** **Closing clause (AD-38).** *"Intake never refuses a revision.
The effective window at decision instant T is a **declared read-time fold**: the
union of the bounds of every revision known at T, with any bound already passed
frozen. State the fold rule as CT-31 surface."*

### H-19 — "Binding epoch" (AD-41's population unit) is a noun that appears once and is defined nowhere

CT-32's declared population names *"which **binding epochs** are in or out."*
AD-27 has session epochs and boot epochs; AD-29 has bindings. Unit A defines a
binding epoch as one binding record's dated validity interval; Unit B as a
`continues-as` chain segment. Divergent populations feed divergent admission-bar
satisfaction, which decides live binding.

**Severity: HIGH.** **Closing clause (AD-29).** *"A **binding epoch** is the
half-open interval between a binding record and its superseding record,
identified by the binding record's fingerprint. CT-32 populations cite binding
record fingerprints, never intervals."*

### H-20 — "Measurement never benches" versus the bench counter being a measurement

AD-41: *"**Measurement never mutates trading state** — it may not size, allocate,
promote, demote, **bench**, or change a mode,"* and, four bullets earlier, *"The
bench counter is a read-time fold over the exit-record stream."* A fold over
evidence is a measurement, and it benches.

- **Unit A** (CT-32 author) obeys the letter and refuses to expose the bench fold,
  so the node implements its own — a second implementation of the same arithmetic,
  which AD-23 forbids.
- **Unit B** exposes it and violates the letter.

**Severity: HIGH.** **Closing clause (AD-41).** *"Restated: a measurement producer
never **acts**; it publishes. Authority to act on a published measure belongs to
the Book door (bench) or the operator (promotion). The bench fold is **one
governed producer under AD-23**, published once and consumed by the door."*

### H-21 — A float measure compared to an exact-rational threshold has no declared crossing

AD-41 permits float-bearing results (Sharpe, drawdown) with label-derived
identity. AD-32 compares a presented result against *"a threshold that is an exact
rational"* with `at-least | at-most | within-band`. That comparison **crosses
AD-22's named analytic↔exact boundary** and AD-32 never invokes it. Unit A
descales the rational and compares in float; Unit B demands an exact rational and
cannot compare at all. Boundary cases — a Sharpe exactly at threshold — decide
live money.

**Severity: HIGH.** **Closing clause (AD-32).** *"A bar comparison against a
float-valued measure crosses AD-22's named boundary under a comparison rule
declared **in the bar requirement** — target scale, rounding mode, tie disposition
— identity-bearing; an undeclared comparison is `invalid input` at Layer 1."*

### H-22 — There is no `kill_line_flat` close reason, so the kill line maps to two different reasons in two builds

AD-33's taxonomy: `protective_stop_fill | target_fill | protection_amendment_fill
| bot_intent | hold_time_force_flat | boundary_flat | window_forced_flat |
protection_forced_flat | venue_liquidation | venue_initiated_close |
operator_close`. AD-36 insists the kill switch and the kill line are *"Two
different things, named apart, never merged"* — and the close-reason vocabulary
has one `protection_forced_flat` for both. Unit A maps a kill-line flatten to
`protection_forced_flat`; Unit B to `boundary_flat` (a capital boundary). AD-33's
promise that *"'the bot's edge' and 'what our own gates cost' are the same recorded
dataset read two ways"* then yields **different partitions in two builds**.

**Severity: HIGH.** **Closing clause (AD-33 + AD-36).** *"`kill_line_flat` is
minted as its own close reason, distinct from `protection_forced_flat`
(kill-switch class). Every (CT-30 action kind × authority) maps to exactly one
close reason through a pinned versioned table in CT-29/CT-30, never per
implementer."*

### H-23 — Notional-denominated Book limits require a conversion AD-40 has no rate source for

AD-40: *"Book-level limits are expressed only in R **or in notional in the Book's
numeraire**."* Notional in USD for a EURJPY position requires a EUR/USD rate.
AD-40: *"no rate source is ratified."* Unit A takes the venue's own notional /
margin field (venue-converted — see C-13); Unit B refuses, so notional limits are
unusable for cross-quote instruments and only R limits work.

**Severity: HIGH.** **Closing clause:** same as C-13's second half — venue-derived
conversions are declared settlement evidence with a `converted_by = venue`
provenance flag; a notional limit on an instrument requiring a QMX-side conversion
is a `policy rejection` at template validation until a rate source is ratified.

### H-24 — The compound-command child ordinal rule is undeclared, so the same flatten gets different child identities

AD-27: each child carries *"a derived identity (parent `fp1` + declared
ordinal)"*; *"QMF carries the ordinal field, the node owns the sequencer."* AD-36
routes every fan-out control action through this. Unit A orders children by symbol
string (legal — but AD-9 says symbols are opaque and never parsed, so any ordering
over them is arbitrary); Unit B by child content fingerprint (AD-17's canonical
rule). Divergent permanent command records and divergent reconciliation evidence
for the identical flatten, and replay does not reproduce either.

**Severity: HIGH.** **Closing clause (AD-27).** *"Compound-command children are
ordered by **child content fingerprint ascending** (AD-17's canonical rule); the
ordinal is the index in that order. Compound identity is therefore reproducible
across implementations and across replay."*

### H-25 — `realized_r` is computed twice: once as a CT-29 field, once as a CT-32 governed measure

- **Unit A — the CT-29 author** computes `realized_pnl ÷ original_risk_amount`
  inline; it is a field of the record.
- **Unit B — the CT-32 author** computes R measures through a governed producer,
  because AD-41 says *"A performance metric is a governed producer under AD-23."*

**Divergence.** Two implementations of one formula — an AD-23 defect — and they
diverge at exactly the rational-form and scale points C-15 identifies.

**Severity: HIGH.** **Closing clause (AD-41).** *"`realized_r` is either (a) a
governed-producer output cited by CT-29 by fingerprint, or (b) a declared derived
display of the record's own frozen fields under a pinned formula and canonical
rational form. Pick one in the spine; both implementations may not exist."*

### H-26 — "The would-have-been action **by fingerprint**": a command fingerprint in one build, a control-action fingerprint in the other

AD-36's `suppressed` subtype carries *"the would-have-been action by
fingerprint"* — an action never dispatched. AD-27's command identity includes the
session epoch and the caller's ordinal, neither of which an undispatched action
has. Unit A mints a full command record with a borrowed epoch and fingerprints it,
seeding the command identity space with phantom ids that appear in reconciliation
evidence; Unit B fingerprints the CT-30 control-action record instead.

**Severity: HIGH.** **Closing clause (AD-36).** *"The would-have-been action is
referenced by its **CT-30 control-action record fingerprint**. A command identity
is minted only at submission; no phantom command record may exist."*

---

## 4. Medium — ambiguity that costs rework or an argument, not evidence

### M-01 — A missing currency-exposure record permanently blocks 24/7 instruments with only a journal row
AD-38: *"A missing record means the instrument is treated as affected and blocked."*
Unit A applies it only while a window of an enabled kind is in force; Unit B
applies it unconditionally — so a crypto instrument on a 24/7 calendar (which
AD-38 says produces **no windows at all**) is blocked forever, with a `data
quality` journal line and no alarm. **Closing clause:** scope the rule to *"while
a window of an enabled kind is in force"* and require an AD-14 alarm, not only a
journal row — a permanently blocked instrument is indistinguishable from a quiet
one.

### M-02 — A money-accounting boundary coinciding with a declared window force-flat
AD-36: *"Every other money boundary — rollover, sweep, re-seed, paper flip —
**leaves positions alone**."* The 17:00 NY rollover (AD-8) coincides with the
daily dead zone, and a Book may declare `window_forced_flat` at rank 2 (AD-38).
Unit A honours the window flat; Unit B reads the money-boundary clause as
governing and leaves positions open. **Closing clause:** *"a money-accounting
boundary is never itself a flatten trigger; a coincident declared window
force-flat is a separate trigger and is honoured."*

### M-03 — `worked_example` singular versus AD-40's per-formula worked examples
AD-30 declares one `worked_example` section; AD-40 requires *"Every formula ships
an executable worked example."* One build ships one end-to-end example, the other
one per formula — different section shapes, different fingerprints. **Closing
clause:** make `worked_example` a keyed collection, one entry per declared
formula id, canonically ordered by formula id.

### M-04 — `world` is a constant in the AD-29 binding tuple and absent from the cohort key
In V1 every binding is `world = live` (AD-12 puts paper/demo there). A replay of a
binding mints a different binding identity, and AD-19's cross-world read is a
`policy rejection`, so replay-derived and live evidence are permanently
incomparable by binding — which the backtesting sitting will hit head-on. AD-35's
`cohort_key` carries no world field at all. **Closing clause:** state the
consequence explicitly in AD-29 and add `world` to the cohort key so the
backtesting sitting inherits a stated position rather than an accident.

### M-05 — AD-39's typed availability markers replacing the `-1.0` sentinel are an unnamed vocabulary
AD-39 says *"the legacy `-1.0` sentinel becomes a typed marker"* and never
enumerates the markers. Two builds mint different marker sets, and the door's
"which markers mean block" set differs with them. **Closing clause:** enumerate
the marker vocabulary in CT-16's SQS configuration as addable-never-redefined, and
declare which members the door must treat as a block.

### M-06 — `session_handover_buffer` has no declared anchor side
AD-38: *"the pause **around** a session handover."* Around implies both sides;
"anchor" is a configurable variable with no spine value, but *which instant it
anchors to* (the closing session's close, the opening session's open, or both) is
structure, not width. Two builds produce different windows from one calendar.
**Closing clause:** declare the anchor side as a mandatory CT-31 field
(`pre-close | post-open | both`), separate from the configurable width.

### M-07 — "A stop-out is an exit at **approximately** the full planned loss" has no test
AD-41 types the event and then removes its only possible test: *"Any magnitude
threshold finer than the sign stays unratified."* So `stop_out` as a typed risk
event cannot be computed, while `qualifying_loss_exit` (sign-based) can. Two
builds classify differently or one omits the field. **Closing clause:** either
drop `stop_out` as a computed classification in V1 and keep only
`qualifying_loss_exit` plus the close reason, or declare the tolerance a
configurable UI-editable exact rational with no spine value.

### M-08 — AD-30's section list is closed-by-ordinal but a seventh section is "a contract-format-version mint, never a refusal"
Two builds differ on whether an unrecognised section in a **newer** format version
read by an **older** reader refuses (AD-30's own *"an uninterpretable contract
format version is an `unsupported capability` refusal"*) or is ignored. **Closing
clause:** state that unknown sections under a known format version are ignored,
and an unknown format version refuses — never both readings of the same artifact.

---

## 5. The five structural roots

Seventeen of the twenty criticals reduce to five roots. Fixing the roots is
cheaper than fixing the findings.

**R1 — The AD-29 binding tuple is doing three jobs at once** (identity, state
container, role label) and nothing declares what a change to any component costs.
*Closes C-01, C-02, C-03, C-16, H-19, and the BMS-swap money reset.*
**One clause:** *"Any change to any component of the binding tuple mints a new
binding. Whether per-binding state carries is a mandatory declared `state_carry`
field on the new binding record, per counter, never inferred from an edge.
`BookInstanceId` is operator-minted; `BmsInstanceId` is content-derived; `role`
moves out of the tuple onto the execution-target record; a binding epoch is the
interval between a binding record and its superseder, cited by fingerprint."*

**R2 — Six read-time folds, no fold contract.** AD-27 and AD-25 declare one; AD-35,
AD-36 and AD-41 do not. *Closes C-07, C-08, H-03, H-18.*
**One clause:** the fold contract (ordering key, knowledge-time bound,
equal-instant disposition, rank-not-WriterId across writers, never-refuse on the
trading path, fail-closed on non-resolution) declared as pinned versioned surface
for every fold the spine names.

**R3 — The control plane has no evidence spine.** No edge from enactment to
intent; no CT-30→CT-19 scope table; no rank uniqueness; no veto accounting; no
exit-preservation invariant. *Closes C-04, C-09, C-10, C-18, H-04, H-13, H-24,
H-26.*
**Four clauses:** mint the `enacts` edge kind; pin the scope-resolution table;
make ranks unique and BMS-declared; state the exit-preservation invariant and veto
accounting once, at spine level.

**R4 — The dimensional law is incomplete on its own core formula, and canonical
numeric form is unpinned.** *Closes C-13, C-14, C-15, H-21, H-23.*
**Three clauses:** extend the unit-kind vocabulary with
`value-per-price-delta(instrument, currency)` and make additions spine-amendment
only; pin exact-rational canonical form and per-value-class canonical storage
scale; declare account settlement currency a CT-18 field and venue-performed
conversions named settlement evidence.

**R5 — The neutral-port boundary and AD-31's identity mandate contradict.**
`qmf-venue` cannot carry Book identity and AD-31 requires it on every risk-domain
event. *Closes C-17, H-05, H-25.*
**One clause:** split risk-authored from venue-authored events; venue-authored
events carry the command record's content fingerprint and the projection joins
through it, as pinned CT-25 surface.

---

## 6. Minimal amendment set

Fourteen edits close all twenty criticals:

1. **AD-29** — `BookInstanceId` in the tuple; `BmsInstanceId` content-derived;
   `role` out of the tuple; binding epoch defined; netting bind-time check;
   binding records may never be byte-identical.
2. **AD-16** — `continues-as` is performance lineage only; mint `enacts`; split
   `supersedes` (linear) from `branches-from` (version graph).
3. **AD-30** — `state_carry` on the binding record; `admission_impact` per
   variable; `required_producer_contracts` gains `on_version_change`;
   order-significance declared per section.
4. **AD-31** — risk-authored vs venue-authored event classes; the command-record
   join as CT-25 surface; cross-role projection clause widened.
5. **AD-32** — no paper role in a live-gating bar; `threshold` discriminated
   union; `admission_bar` a canonically-ordered set; Layer 1 invokes cited
   producers; Layer 2 requires a live-path rung baseline on this tuple; float↔exact
   comparison rule declared per requirement.
6. **AD-33** — mint `kill_line_flat`; the (action × authority) → close-reason
   table pinned; direction rule restated as risk-non-increasing.
7. **AD-34** — `risk-non-increasing` defined per protection side; venue trailing
   as a declared `venue-delegated` authority minting CT-30 records.
8. **AD-35** — `execution_target` resolved per intent, separate from the binding;
   paper stream reconciled as its own binding and alarmed like a live one; cohort
   key reads refit-series identity.
9. **AD-36** — the exit-preservation invariant; CT-30→CT-19 scope table pinned;
   per-kind satisfaction predicates with `never-auto` for `suspend_new`/`drain`;
   standing-intent machinery generalized to every risk-non-increasing act; veto
   accounting; would-have-been action cited as a CT-30 fingerprint.
10. **AD-37** — ranks unique and BMS-declared; strictly rank-ordered arbitration.
11. **AD-38** — effective-window read-time fold; missing-record rule scoped and
    alarmed; handover anchor side declared.
12. **AD-39** — refit-series identity; input BarSpec and freshness constrained;
    `instrument_class` as an AD-9 record; marker vocabulary enumerated.
13. **AD-40 / AD-41** — unit-kind vocabulary extended, additions
    spine-amendment-only; `Position` minted as a core noun with two kinds;
    `realized_r` single-sourced; measurement/authority boundary restated; bench
    fold's stream boundary and knowledge-time bound declared.
14. **AD-7 / AD-10 / AD-24 / AD-27** — canonical rational form and storage scale;
    provisional light claim across (OS, CPU-class) tuples; reconciliation lookback
    mandatory and `out-of-lookback` verdict; subject-terminal command resolution;
    compound child ordinal pinned to fingerprint order; `denied-locally` scoped to
    the adapter.

---

*End of review.*
