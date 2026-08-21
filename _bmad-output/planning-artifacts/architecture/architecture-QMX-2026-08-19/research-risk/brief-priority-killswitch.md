---
brief: priority-killswitch
cluster: GAP-0046 — same-tick priority, control-action contract, flatten authority, hold/overnight/dead-zone, correlation ledger seam
owns: GAP-0046 (whole) · five-hats T-1, T-2 (remainder), T-4, A-7, P-3, P-6 · X-5 (consumed), X-6 (partial)
consumes: AD-27 (venue commands + uncertainty law), AD-28 (capability record), AD-21 (journal event types), AD-8 (calendars, ordering), AD-16 (lineage edges), AD-11 (typed refusals), AD-25 (read-time fold idiom)
date: 2026-08-20
status: recommendations for operator ruling — nothing here is ratified
---

# Decision brief — same-tick priority, kill switch, flatten authority

## Reading note: the gap's own name is wrong

GAP-0046 says "same-tick priority." There is no tick that a venue-resident protective
stop and a node-side force-flat share. AD-8 already rules that "instants alone never
totally order events" and that the `(instant, writer, sequence)` tie-break is "a
replay-determinism device with no causal meaning — causality tests refuse at equal
instants rather than tie-break" (`ARCHITECTURE-SPINE.md:97`). So a literal same-tick
arbitration table is unwritable, and every corpus layer that tried to write one either
failed or wrote something else.

What is writable, and what this brief recommends, is a **node evaluation point**: one
place, per command stream, where every pending control action is arbitrated before
anything is dispatched. Everything below is built on that correction.

Precedence applied throughout: current QMX rulings (`docs/`, `tracker/`, the ratified
spine) > old wiki (`Documents/QMX/wiki`) > GitBook capture > QMX-discussion legacy.

---

## PK-1 — Anchor priority to the AD-27 command stream, not to the Book

### What the evidence layers say

**Current corpus.** Book-to-venue cardinality is genuinely unruled: "Books bind to
accounts. An account carries a role… Venue and Account are first-class nouns"
(`docs/components/qmf-risk.md:61`, DEC-0107), and the extractor confirms "Neither source
states whether one Book may bind accounts at several distinct venues simultaneously —
not addressed either way" (`extract-local-current.md:113`). AD-9 states multi-broker
(≈6 venues) is normal (`ARCHITECTURE-SPINE.md:110`).

**Recovery / old node docs.** V1 is single-venue forex/cTrader; multi-venue is explicitly
out of V1 (`extract-local-recovery.md:98,100`); `venue_platform_instrument_encodings` is a
declared non-goal (`extract-old-node-docs.md:84`).

**The hazard.** Five-hats X-5 says the risk sitting must rule Book-to-venue cardinality
**before** writing the priority rule, because "two venues have two independent tick
streams, two latencies, and no shared clock"
(`reviews/five-hats-sweep.md:264-266`). T-4 adds that the rule must be written against
the real CT-18 capability set (`:214-216`).

**What already exists and dissolves the hazard.** AD-27 defines a stream once: "the unit
of `UNKNOWN` blocking, of `WriterId` ownership, and of the gapless per-writer sequence is
the **(VenueId, account)** pair — coarser than an account binding (all bindings on an
account block together), strictly finer than a connection"
(`ARCHITECTURE-SPINE.md:270`).

### Bucketing proposal

**Stays QMF.** The scope anchor is a contract fact, not behavior: the arbitration record
and every control action declare the command stream they resolve on. The node runs the
arbiter.

### Recommended ruling

**Priority is defined per (VenueId, account) command stream. Cross-stream ordering is
explicitly undefined and is a declared non-guarantee, not an omission.**

Alternatives weighed. (a) *Per Book* — fails the moment one Book binds two venues, and
forecloses the PM's diversification move that AD-9 calls normal. (b) *Per account
binding* — finer than AD-27's stream; would let two bindings on one account race while
their uncertainty is shared, which is exactly the coupling AD-27 chose to keep. (c) *Per
venue* — coarser; couples unrelated accounts' protection, which AD-27 deliberately
refused. (d) *Global total order* — a false promise; AD-8 forbids it.

The decisive argument: anchoring on the AD-27 stream makes the priority rule **correct
under either answer to Book-to-venue cardinality**, so the X-5 sequencing hazard stops
being a blocker. A single-venue Book gets a total order for free. A multi-venue Book gets
per-stream determinism with an honest, named non-guarantee at the boundary — which is
precisely the resolution shape X-5 asked for, obtained without waiting on the cardinality
ruling.

One cardinality claim is being made deliberately, per AD-17: **exactly one arbitration
point per command stream.** AD-17 forbids hardcoded cardinality-one "without a ruling"
(`ARCHITECTURE-SPINE.md:167`); this is that ruling, and it is scoped per stream, so the
system still holds many arbiters.

### What would change it

A ruling that a Book's risk arithmetic (equity, daily budget, exposure) must be evaluated
atomically across venues would force a Book-scoped arbiter and reopen this. Note that
would also reopen multi-currency and cross-account aggregation, both of which the corpus
records as unratified (`extract-old-node-docs.md:339`; `extract-local-recovery.md:389`).

---

## PK-2 — Mint the control-action contract (five-hats T-1)

### What the evidence layers say

**Current corpus.** `docs/` has no KSA contract or definition of any kind — searched
across `qmf-risk.md`, all four CT files, and the glossary: none contain "KSA" or "kill
switch" as a defined term (`extract-local-current.md:267`). The only inherited fact is the
funnel: "MIS senses → KSA decides (escalate-only; human A1 de-escalates) → Adapter
enforces as an effect" (`tracker/trading-node-notes.md:42`).

**Old wiki / GitBook.** KSA is "the global protection state machine. BMS owns policy, the
trading node enforces effects through the adapter, and bots never see KSA directly"
(`extract-gitbook-capture.md:281`, DEC-0008). Five levels GREEN/YELLOW/ORANGE/RED/BLACK
(DEC-0043); four trigger classes `scheduled_news, black_swan, connectivity, unknown_state`
(DEC-0044); automated transitions escalate only, A1 human de-escalates (L8). CT-KSA-01
carries `event_id, level, trigger_class, affected_pairs, evidence_refs, effective_at_utc`
(`extract-gitbook-capture.md:285-301`). The **trigger→level→effect matrix is GAP-0015 and
deliberately empty** — the page says outright "do not invent target state here"
(`extract-local-current.md:273`).

**Effect vocabulary is a real drift.** The checklist's "suspend-new / drain / close_all"
does not exist in the GitBook or wiki layers — only `close_all` matches; the corpus's
actual verbs are the four adapter commands plus prose ("block affected pairs," "hard
block") (`extract-gitbook-capture.md:320,475`; `extract-live-gitbook.md:431-434`).
`suspend-new` and `drain` enter through the **current** venue ruling only
(`tracker/trading-node-notes.md:48`; AD-28 names `suspend-new | drain | close_all` as
CT-18's declared protection primitives, `ARCHITECTURE-SPINE.md:286`). Current wins.

**Scope ladder is also drift.** The GitBook realizes only `affected_pairs` + global
(`extract-gitbook-capture.md:302,476`). The finer ladder the five-hats asks for
(pair/Book/account/venue/global) is not in any old layer; AD-27's typed close scope
(`account | account-binding | instrument-within-binding`) is the only ratified one
(`ARCHITECTURE-SPINE.md:271`).

### Bucketing proposal

**Contract stays QMF; behavior re-buckets to the node** — the standing framework-vs-node
ruling exactly. Concretely:

QMF (a new CT in `qmf-risk`, provisionally **CT-27 control action**) carries:
- **Action kind vocabulary**, QMF-owned, addable-never-redefined per AD-5:
  `suspend_new | drain | flatten | resume`. Nothing more in V1.
- **Authority**: the issuing authority's identity plus its kind
  (`operator | book_policy | adapter_self` — see PK-4), with `resume` declared
  operator-only, mirroring L8's escalate-only law.
- **Two-part scope.** A *subject scope* naming the population addressed
  (`instrument | book | account | account-binding | venue | global`) and, at dispatch, the
  AD-27 *enforcement scope* (`account | account-binding | instrument-within-binding`).
  The node resolves subject → zero-or-more enforcement scopes against CT-18. An
  unresolvable subject scope is an `unsupported capability` refusal and is **never
  emulated at a wider scope** — verbatim reuse of AD-27's existing rule
  (`ARCHITECTURE-SPINE.md:271`).
- **Reason**: a trigger-class reference plus evidence refs (CT-KSA-01's shape, kept).
- **Outcome law**: none of its own. A control action that fans out to venue commands
  **is an AD-27 compound command** — each child observation- and journal-bearing, parent
  outcome = the meet of its children, any child UNKNOWN makes the parent UNKNOWN
  (`ARCHITECTURE-SPINE.md:271`). Do not mint a second outcome vocabulary.
- **Evidence record**: AD-21's existing `control action` journal event type, subtyped
  (PK-6). Not an eighth event type.

Node keeps: the trigger→level→effect matrix (GAP-0015, still deliberately empty), when
an action fires, and the level state machine itself.

### Recommended ruling

**Mint CT-27 with the shape above. Do not mint KSA levels into QMF.** The five levels are
node state; QMF carries the *action* the level produces, not the level. This is what keeps
GAP-0015 legitimately empty while still closing T-1: the framework-vs-node ruling
"correctly withholds the *behavior*; it does not excuse the absence of the *contract*"
(`reviews/five-hats-sweep.md:204`).

Alternatives weighed. (a) *Extend CT-19's four command kinds with a fifth "control"* —
rejected: AD-27 fixed the vocabulary at four and said `amend_order` "arrives only by
explicit later mint"; a control action is upstream of a venue command, not one of them.
(b) *Leave the whole thing node-side* — rejected: then the kill switch has no fingerprinted
contract, no refusal semantics, and no cross-package evidence shape, which is the exact
hole the tracker calls "the one component with unbounded failure cost." (c) *Mint KSA
levels in QMF* — rejected: it would half-fill GAP-0015 and hardcode a five-level ladder
the corpus already shows in three conflicting vocabularies
(`extract-qmx-discussion.md:368-372`).

**Do-not-revive guard.** TIGHTEN / half-size-through-bad-conditions is dead (DEC-0019) and
must not re-enter through `drain` or through a per-level effect. The legacy KSA effect
table's "SL moves to breakeven" at RED and "BE at +1R" are on the explicit DROP list
(`extract-local-recovery.md:397-398`) — the *ordering* idea is a donor, the *effects* are
not.

### What would change it

If the node sitting rules that protection is expressed only as a level and never as a
discrete action, CT-27 collapses into a level-observation contract. I judge that
unlikely: `suspend-new` is already ratified as an action with instant local effect
(`ARCHITECTURE-SPINE.md:273`).

---

## PK-3 — The priority law itself: two tiers, collapse, and suppression

### What the evidence layers say

**Current corpus.** `GAP(GAP-0046): Define deterministic same-tick priority and
Book-specific overnight behavior.` (`docs/components/qmf-risk.md:85`); CT-23 lists
GAP-0046 against its `enums` slot (`docs/contracts/ct-23-risk-evaluation.yaml:29`). The
venue-sitting inheritance adds: "Same-tick priority among protective stops/force-flat/
kill-switch/discretionary exits is explicitly undefined, GAP-0046."

**Old wiki (highest legacy layer).** VERBATIM: "Close-authority ordering. KSA effects,
hold-time force-flat, broker-side stops, and normal amendments can collide on the same
tick; **no current priority contract resolves that race**"
(`extract-old-wiki.md:700-705`, `topics/position-safety-and-sltp-authority.md:49`).

**GitBook.** Two *sequential* chains exist and neither is a priority table: the door
pipeline (`intent → footprint → viability → rmax → budget → breaker → exposure → ksa →
adapter`) and the leash escalation chain (`ambient governor, day closure, bench-to-paper,
chorus flag, kill-line stand-down, classed kill switch, hold-time force-flat`, DEC-0037)
(`extract-gitbook-capture.md:456-457`). The live-site extractor is blunt: this "is an
escalation *sequence over time*, not a same-tick priority arbitration table"
(`extract-live-gitbook.md:665-673`). L12 gives a principle only: "Graduated policy shrinks
before it blocks unless the event class demands instant action" (DEC-0013).

**QMX-discussion (oldest).** A fully specified donor exists: "Kill Switch Authority
(highest priority — always wins) ↓ SL/TP Service ↓ Risk Engine Output ↓ Execution", with
`AmendInstruction.priority`: kill-switch = 0 supersedes normal = 10
(`extract-qmx-discussion.md:342`; `extract-old-recovered.md:494-496`). The 2026-07-18
clash report recommends re-anchoring it: "**KSA ≥ force-flat ≥ stop amendments,
adapter-enforced**" — explicitly "a recommendation, not a ruling"
(`extract-old-recovered.md:499-503`).

**The counter-evidence that must be surfaced.** The leash puts hold-time force-flat
*after* the classed kill switch — "a distinct, strictly later rung than kill-line
stand-down" (`extract-old-planning.md:303`, PE7-MEMO:286). Read as severity, that says
force-flat outranks the kill switch — the opposite of the donor. This is exactly why the
leash must not be read as the priority table.

**What AD-28 forces into the rule (T-4).** CT-18 declares `position model
(netting | hedging) per account` and `protection primitives (suspend-new | drain |
close_all)` (`ARCHITECTURE-SPINE.md:286`). Under hedging, one instrument may hold several
positions, so an instrument-scoped flatten is a fan-out; under netting it is one command.
AD-27 already supplies the fan-out law (compound command, meet of children).

### Bucketing proposal

**Split, cleanly.**
- **QMF carries:** (i) the two-tier law; (ii) the collapse and conflict rules; (iii) the
  arbitration-decision record shape; (iv) the priority rank as a **required,
  non-defaultable declared field** on each control-action kind in the Book's control
  policy — the do-not-default idiom AD-27 already uses for the submission deadline ("its
  existence and declaration are mandatory, its value is not QMF's",
  `ARCHITECTURE-SPINE.md:273`).
- **Node carries:** the arbiter itself, and the actual rank values.

### Recommended ruling

**Tier 1 — venue-resident actions are outside the ordering, by construction.**
A protective stop resting at the venue fires when it fires; nothing asks the node. The node
never assumes it did or did not. Its outcome arrives as an ordinary observation — AD-27
already rules that "server-initiated events [are observed] the same shape, never errors"
and that order state is "a read-time fold over the observation stream"
(`ARCHITECTURE-SPINE.md:274`). The race a node close loses to a venue stop is **already
resolved by ratified law**: a cancel resolved by read-back is `accepted-by-venue` only if
the read-back shows no fill at or after the submit stamp, "otherwise it resolves
`rejected-by-venue (superseded-by-fill)`" (same line). No new mechanism is needed. State
this explicitly, because a builder handed GAP-0046 will otherwise try to rank a
broker-side stop against a node action and invent an arbiter that cannot exist.

**Tier 2 — node-originated actions get one deterministic order, evaluated at one point
per command stream.** Recommended rank, highest first:

1. **Protection actions** (kill-switch class: `suspend_new`, `drain`, `flatten`).
2. **Book force-flat** (kill-line stand-down; hold-time / boundary force-flat, PK-7).
3. **Fast invalidation** (thesis/structure invalidation exits).
4. **Ordinary Bot exits and stop/target amendments.**

**Two rules make the order safe to get slightly wrong:**

- **Collapse rule.** Where two or more pending actions would produce *the same mechanical
  venue command on the same enforcement scope*, exactly **one** command is emitted. The
  rank winner supplies the authority and reason on the journal record; every loser is
  journaled as a suppressed control action (PK-6) carrying its would-have-been action.
  Consequence: rank decides **attribution**, not **whether the position closes**. Both a
  kill-switch flatten and a hold-time force-flat close the position; only the recorded
  reason differs. This is what defuses the leash-vs-donor tension above — it is an
  attribution disagreement, not a safety one.
- **Conflict rule.** Where pending actions would produce *different* commands (a
  stop-tightening amendment against a flatten), the higher rank wins outright and the
  lower is suppressed — never both, never queued behind. And: **a lower-ranked action may
  never undo a higher-ranked one.** No de-escalation by side effect. This mirrors L8's
  escalate-only law at the action layer.

**Scope resolution reads CT-18 before dispatch.** Netting vs hedging decides whether a
Book-scoped or instrument-scoped flatten is one command or a compound command; an
enforcement scope CT-18 does not declare is an `unsupported capability` refusal, never
widened.

Alternatives weighed. (a) *Adopt the leash chain as the priority table* — rejected: three
extractors independently state it is an escalation sequence, not an arbitration table, and
reading it as one inverts the kill switch below force-flat. (b) *Import the donor's
numeric priority integers (0/10)* — rejected in form, adopted in spirit: the integers came
bundled with a dead level vocabulary and dead SL-to-breakeven effects; the ordering idea
survives, the payload does not. (c) *Timestamp tie-break* — rejected by AD-8. (d) *No
ordering; first-writer-wins* — rejected: that is a race, and it produces duplicate closes
under hedging.

### What would change it

Two things. A CT-18 declaration that a venue supports **no** attached protective stop
would empty tier 1 for that venue and make every stop node-resident — more deterministic,
much less safe on a dead node (see PK-10). And a ruling that ordinary Bot exits are
Book-owned (DEC-0067 / GAP-0040, still an open conflict —
`docs/components/qmf-risk.md:73`) would merge ranks 3 and 4; the rank list survives either
way, it just gets shorter.

---

## PK-4 — Flatten authority (AD-27 explicitly left this to this sitting)

### What the evidence layers say

**Current corpus, load-bearing.** "Flatten authority was explicitly unassigned — the venue
sitting's GAP-0036 ruling reserves it as a human-authorized path, never assumed, never
automatic (policy assignment lands in the risk/node sittings)"
(`tracker/trading-node-notes.md:42`). AD-27: "Flatten is `close_position`/`close_all`
executed mechanically; the adapter never initiates it; authority assignment (VPS-death
included) belongs to the risk/node sittings" (`ARCHITECTURE-SPINE.md:276`).

**Old wiki.** VERBATIM, interim: "No position flatten or carry behavior is implemented
anywhere in V1 until PE-7 is ruled"; kill-line stand-down flips book mode with **no
position action** (`extract-old-wiki.md:293-297`). PE-7 covers position fate at rollover,
sweep, re-seed, kill-line, and paper flip (`extract-old-planning.md:304`).

**PE-7 memo (2026-07-28, RECOMMENDED, not ratification).** Architect's lean: "**flatten at
the kill-line specifically, carry elsewhere**", offered as recommendation only, with the
leash ordering flagged as genuine counter-evidence (`extract-old-planning.md:304`).

**QMX-discussion (oldest).** BLACK = "all positions force-closed at next fill"
(`extract-qmx-discussion.md:224`). BLACK survives (DEC-0043 keeps five levels); only
TIGHTEN died.

**Interlock to respect.** Any open position forces reconciliation verdict `unknown`, which
blocks `ledger_reconciles_gate_ready` (`extract-old-planning.md:304`) — but AD-27 already
severs the livelock: the UNKNOWN block "clears on resolution, never on a reconciliation
verdict" (`tracker/trading-node-notes.md:46`).

### Bucketing proposal

**Authority *list* and its declaration shape stay QMF** (a required field set on CT-27 and
on the Book charter). **Which triggers a given Book declares** is node/Book policy.
Critically, this assignment must **not** fill GAP-0015: it names *who may flatten and under
which declared trigger classes*, never *which KSA level flattens*.

### Recommended ruling

**Flatten authority in V1 has exactly three holders, and one of them is "nobody":**

1. **The operator (A1)** — always, unconditional, at any scope including global. Never
   removable, never gated on reconciliation. This is the only authority that is a QMF
   constant.
2. **Book policy, but only through pre-declared trigger classes.** Not "the Book may
   flatten" — "the Book declares that trigger class X, at scope Y, flattens." An
   undeclared trigger produces no flatten, ever: fail-closed and non-acting, which is
   exactly the posture PE-7's interim ruling holds today.
3. **Nobody else.** The adapter never initiates (already AD-27). An automatic detector
   never flattens — it emits a typed verdict and the node decides, which is five-hats X-3's
   resolution shape and keeps DEC-0049 unprejudiced
   (`reviews/five-hats-sweep.md:256-258`). A Bot never flattens another Bot's position.

**Recommended V1 declared set for the scalper Book** (evidence-anchored, all overridable
per Book):
- **kill-line stand-down → flatten** (the PE-7 memo's lean).
- **rollover / sweep / re-seed / paper flip → carry** (the same memo's lean; and the
  interim rule that a mode flip performs no position action).
- **operator-triggered protection at BLACK-class severity → flatten, scope global**
  (the surviving half of the legacy effect table).

**Resume is separate and is human-only.** Flattening is escalation; resuming is
de-escalation; L8 and D-11 (`automatic_resume_allowed: false`) both bind. The same control
action vocabulary carries `resume` with an operator-only authority flag.

Alternatives weighed. (a) *No automatic flatten at all in V1; every flatten is an operator
click* — the safest reading of "never assumed, never automatic," and I nearly recommended
it. Rejected because a kill-line breach at 3am with the operator asleep is precisely the
case the kill line exists for, and the operator's own protection funnel is automatic on the
escalation side. (b) *Flatten at every boundary* — rejected: it churns positions at
rollover for no protective reason and inflates the `explained_delta` open-position item.
(c) *Leave PE-7 open and ship nothing* — rejected: that is the status quo and it means the
kill line is decorative.

### What would change it

Operator preference for a fully manual kill (alternative (a)) flips this. It is a
legitimate choice and costs only latency at the kill line — but the operator should make it
knowingly, not inherit it by silence.

---

## PK-5 — A control action that cannot be delivered (five-hats T-2 remainder)

### What the evidence layers say

Five-hats assigns T-2 to the venue sitting and calls it "the highest-consequence undefined
behavior in the whole surface" (`reviews/five-hats-sweep.md:206-208`). My task is to check
what AD-27's UNKNOWN law already covers.

**Already covered by AD-27** (`ARCHITECTURE-SPINE.md:273,276`):
- `suspend-new` "takes local effect instantly with no venue round-trip" — the
  stop-the-bleeding half never blocks and never needs the venue.
- Protection commands "dispatch ahead of `place_order` on every shared throttle."
- On disconnect, in-flight commands become UNKNOWN; recovered fills commit through
  evidence before a session reports healthy.
- Retry is prohibited; the adapter never clears its own block; unblocking is the
  application's explicit `resolve_unknown(command identity, resolution ∈ observed-accepted
  | observed-absent | operator-attested)`.

**Not covered — and it is risk territory, not venue territory.** Three holes:

1. **There is no durable intent.** AD-27 deliberately gives the adapter no queue and
   forbids retry. So a flatten issued during an outage yields a `transient venue failure`
   refusal and then… nothing durably represents "the operator wants this account flat."
2. **Protection commands are *not* exempt from the UNKNOWN block** — AD-27 says so
   verbatim. Combined with (1) this means: **during an outstanding UNKNOWN, `suspend-new`
   is always available and `flatten` is not.** That is a correct safety choice (firing a
   close against an unknown outcome can double-close) and an operator-visible fact.
3. **No escalation path to the human.** The operator's stated fallback is the broker's own
   web platform, manually (`reviews/five-hats-sweep.md:208`).

### Bucketing proposal

**Re-buckets to the node as *state*; QMF carries the record shape and one law.** QMF
supplies: the control-action record (PK-2), the rule that **standing protection state is a
read-time fold over the control-action stream** — the same idiom AD-25 uses for structure
lifecycle and AD-27 uses for order state — and the "re-deciding is not retrying" law below.
The node holds the standing state and re-evaluates it.

### Recommended ruling

**A protection control action creates a durable standing intent, recorded before any
dispatch, and answered by folding the stream — never by a queue.**

- **Recording precedes delivery.** The control action is journaled first (AD-27's
  "recording precedes interpretation"), so the intent exists even if nothing reaches the
  venue.
- **"Is this account under a standing flatten intent?" is a fold**, not stored mutable
  state. Restart-proof by construction; no new machinery.
- **Re-deciding is not retrying.** On reconnect, the node's session-recovery duty
  re-evaluates every standing intent against reconciled state and, if still unsatisfied,
  issues a **new command with a new identity**. AD-27's retry prohibition binds the
  *command*, not the *decision* — state this explicitly, or a builder will read "command
  retry is prohibited" as "the kill switch gives up."
- **Re-issuing the protective action is automatic; resuming trading is not.** Escalation
  automates (L8); de-escalation is A1-human (L8, D-11, `automatic_resume_allowed: false`).
- **The intent never time-expires.** It clears only on observed evidence that it is
  satisfied, or on an explicit operator clear. Every alternative requires inventing a
  timeout, which AD-13's no-invented-numbers and the do-not-default standing both forbid —
  so this is forced, not chosen.
- **Undeliverable protection raises an alarm** carrying the manual-fallback instruction
  (broker web platform), per AD-14's loud-failure rule. The intent stays open until an
  observation or an `operator-attested` resolution closes it.

Alternatives weighed. (a) *An adapter-side retry queue for protection commands only* —
rejected: it contradicts AD-27's retry prohibition and reintroduces the double-close risk
the UNKNOWN block exists to prevent. (b) *Exempt protection from the UNKNOWN block* —
rejected: AD-27 considered and refused this; the mitigation is `suspend-new` plus PK-10's
venue-resident stop, not an exemption. (c) *Expire the intent after N minutes* — rejected,
invents a number and fails exactly when it matters.

### What would change it

If CT-18 for some venue declares a native "cancel-all-on-disconnect" or server-side
dead-man switch, tier 1 grows and the standing-intent path becomes a backstop rather than
the primary. Whether cTrader offers anything of the kind is **not established in any
corpus layer** and must be a CT-18 declaration, never an assumption.

---

## PK-6 — Suppression as a first-class journal event (five-hats A-7, X-6)

### What the evidence layers say

**Current corpus.** AD-21 fixes the journal at "seven event types (decision, order, fill,
risk transition, promotion, data quality, **control action**)"
(`ARCHITECTURE-SPINE.md:191`). AD-28 already routes adapter-initiated state changes
("suspend-new, drain, session restart, throttle engaged, reconnect") to `control action`
(`:291`). DEC-0048 in the *current* registry governs those seven event types
(`docs/components/qmf-risk.md:111`) — note the numbering collision with the legacy
DEC-0048 (chorus flag), flagged at `extract-local-current.md:464`.

**Old wiki / GitBook.** Refusals already have a home: "Every refusal signs the veto
ledger" (L11 — "a no is not journaled → violation",
`trading-node-order-path-study.md:51`); Records is the sole physical writer of exactly five
streams (`:80`).

**Five-hats.** A-7: suppression is "the counterfactual that separates 'the edge died' from
'our own gates blocked the trades'"; type it with "the suppressing authority, the reason…
and the would-have-been action" (`reviews/five-hats-sweep.md:150-152`). X-6: evidence
produced under an active control comes "from a population the live Book was forbidden to
trade — same world, same label shape, non-comparable content" (`:268-270`).

### Bucketing proposal

**Stays QMF as contract surface, extending what exists.** No eighth journal event type —
adding one is a spine amendment and is unnecessary.

### Recommended ruling

**Extend AD-21's `control action` event type with a declared subtype `suppressed`,
carrying: suppressing authority, suppressed authority, reason code, the would-have-been
action (the full control-action content, by fingerprint), the enforcement scope, and the
arbitration decision's fingerprint.**

**Draw the line between a refusal and a suppression, explicitly:**
- A **door refusal** rejects an intent *before* it becomes an authorized action. That is
  the veto-ledger path and it already exists. Do not duplicate it.
- A **suppression** discards an action that was *already authorized and about to be
  dispatched*, because a competing authority won arbitration. That is the new subtype.

This line is the whole value of the ruling. Without it, a builder either loses the
suppression data (A-7's complaint) or double-writes every door refusal into two streams.

**For X-6, do not touch the AD-12 label.** AD-12 is closed and its label is fixed. Instead,
tag affected evidence with a **typed AD-16 lineage edge** from the result to the
control-action record — AD-16 explicitly holds post-birth facts in "append-only typed edge
records referencing fingerprints" and states "kinds are addable, never redefined"
(`ARCHITECTURE-SPINE.md:161`). Cohort selection then includes or excludes the tagged
population deliberately, instead of averaging two regimes and calling the result decay.

Alternatives weighed. (a) *A new journal event type* — rejected, spine amendment for no
gain. (b) *Generic log text* — rejected, exactly what A-7 says must not happen; AD-14 also
rules "logs are not journals." (c) *A new identity field on the result label* — rejected,
AD-12 is closed and the edge form is strictly better (it can be added after the fact, which
matters because a control can start after a result is minted).

### What would change it

Nothing I can see. This is contract plumbing over already-ratified structures.

---

## PK-7 — Hold limits and no-overnight are one mechanism, not two

### What the evidence layers say

**Not found, everywhere.** No "no-overnight" or flat-by-session-end rule exists in any
layer: current corpus ("not found in any file read", `extract-local-current.md:394`), old
wiki (`extract-old-wiki.md:712-715`), GitBook (`extract-gitbook-capture.md:460`), live site
(`extract-live-gitbook.md:679`), old node docs (`extract-old-node-docs.md:332`).

**Hold-time force-flat exists as a name only.** It is the terminal leash rung (DEC-0037)
and the primer says it is "named once and never defined anywhere in the capture"
(`extract-local-current.md:394`). No numeric value exists in any registry
(`extract-old-planning.md:306`).

**The corpus itself asks the unification question.** ADDENDUM:193, VERBATIM: "Is hold-time
force-flat specifically the maximum-position-age/no-overnight rule?" — disposition
`REOPEN`, "Likely relationship to maximum position age/no-overnight, but not proven"
(`extract-local-recovery.md:370-372`).

### Bucketing proposal

**Behavior re-buckets to the node/Book; QMF carries the rule-expression shape** — a Book
declares zero-or-more force-flat rules as CT-22/CT-23 contract surface, with a rank in the
PK-3 table. No values.

### Recommended ruling

**Unify them: one Book-declared "force-flat rule" with two trigger forms.**

A force-flat rule = (trigger, scope, rank), where trigger is either:
- **position age** exceeding a declared `Duration` — the hold limit; or
- **a calendar instant** from a named calendar identity — the overnight/session rule.

Both produce the same mechanical act (`close_position`/`close_all` at the declared scope)
and both sit at PK-3 rank 2. One mechanism, two triggers, one journal reason vocabulary.

**No numbers.** AD-13 forbids invented numbers and the do-not-default standing forbids QMF
supplying a value; the Duration and the calendar instant are Book-declared, mandatory-to-
declare, defaultless. A Book that declares no force-flat rule has none — which is the V1
status quo (PE-7 interim: no flatten or carry behavior implemented) and is therefore a safe
landing.

**The calendar half needs no new QMF machinery.** AD-8 already ships three distinct named
calendar kinds — market-hours, day-boundary, news — and requires docs to "rename apart"
(`ARCHITECTURE-SPINE.md:98,102`). "Flat by 21:00 New York" is a market-hours-calendar
instant; "flat by the prop firm's day boundary" is a day-boundary-calendar instant. Both
already expressible.

Alternatives weighed. (a) *Two separate mechanisms* — rejected: they produce identical
commands and would need two entries in the priority table, two reason vocabularies, and a
tie-break between themselves. (b) *Ship a default hold time* — rejected by AD-13. (c)
*Leave hold-time force-flat undefined and drop no-overnight* — rejected: it leaves the
terminal leash rung permanently unimplementable, which is how it got to be "named once and
never defined."

### What would change it

Evidence that hold-time force-flat was intended as something else entirely — a *supervisory*
act (stand-down after a stale position) rather than a position-age limit. Nothing in nine
dossiers supports that reading, but the term's total absence of definition means the
operator's own memory outranks the corpus here.

---

## PK-8 — The dead zone (~45 min session handover)

### What the evidence layers say

**Current corpus — the only place it exists.** VERBATIM: "Dead zone: ~45-minute relax
around session handover (analysis-before-execution; from the first QMX version,
operator-solved ~Dec 2025). Operator clarification 2026-08-20: the dead zone pauses
TRADING ONLY — data streaming continues throughout; it is NOT kill-switch logic. Related
note: real session activity starts later than nominal opens… Risk-sitting policy."
(`tracker/trading-node-notes.md:18`).

**Every other layer: not found.** Old wiki: not found; the only "45" is
`order_latency_max_ms = 45` (`extract-old-wiki.md:720-726`). GitBook, live site, old node
docs, recovery corpus: all not found
(`extract-gitbook-capture.md:460`; `extract-live-gitbook.md:684-686`;
`extract-old-node-docs.md:332`; `extract-local-recovery.md:374`).

**QMX-discussion has a near-miss that is a different thing.** "OVERNIGHT | 19:00–20:00 |
None | No | Dead zone — no new positions advised" — a **1-hour** window, and the old WF3
pool-cleaning ran in it (`extract-qmx-discussion.md:350`). Also present in that layer: a
`SESSION_WARMUP` gate with `warmup_seconds=1500`, during which "house money" was disabled
(`:352`) — that machinery is dead (DPR/slot/auction lineage, DEC-0018/DEC-0093), and "house
of money" was audited as never having existed as a QMX concept
(`trading-node-order-path-study.md:110`).

**The collision that must be named.** "Session windows as trading authority" is an explicit
**dead** decision, DEC-0025: "the clock alone does not authorize trades… session context may
only inform them if ratified" (`extract-gitbook-capture.md:460`;
`extract-local-recovery.md:374`). The operator's dead zone is a clock-driven trading pause.

### Bucketing proposal

**Node policy; the QMF seam already exists and needs nothing new.** `SessionWindow` is
already a core AD-8 time noun; calendars already supply a session schedule; AD-22 already
lets a configuration declare a market-hours calendar as a typed input
(`ARCHITECTURE-SPINE.md:95,98,202`). The dead zone is a `SessionWindow` set declared in the
Book's control policy. QMF adds zero machinery.

### Recommended ruling

**Adopt the dead zone as a Book-declared, block-only no-new-entry window, and state its
reconciliation with DEC-0025 in the same breath.**

The reconciliation: DEC-0025 kills the clock as an **authorizer**. Blocking is the opposite
direction, and the corpus already permits clock-driven *widening* of a block (sessions "may
widen but never narrow" a news block, `extract-local-recovery.md:181`). So a block-only
dead zone is consistent with DEC-0025, and saying so is necessary — otherwise a builder
reading DEC-0025 will correctly refuse the operator's own idea.

**One invariant, load-bearing:** a dead zone **blocks new entries only. It never blocks an
exit, a stop amendment, or any protection action.** A window that traps you inside a
position is worse than no window.

**Not a kill-switch level, not a control action.** It is a door-class refusal (it refuses
an intent before it becomes an action), which puts it on the veto-ledger path, not the
suppression path (PK-6's line). It therefore never enters the PK-3 priority table.

**No number in QMF.** ~45 minutes is the operator's value for one handover; it is
Book-declared. The operator's own note that "real session activity starts later than
nominal opens" means the window's anchor must be calendar-declared and adjustable, not
derived from nominal opens.

Alternatives weighed. (a) *Model it as a KSA level or a control action* — rejected: the
operator said explicitly it "is NOT kill-switch logic," and it would then outrank exits,
which is the trap case. (b) *Model it as a news-style blackout directive* — tempting
(same block-both-live-and-paper shape) but rejected: news is pair-scoped and event-driven;
this is calendar-driven and session-scoped, and conflating them makes the news window's
revision handling (T-5) apply to a calendar. (c) *Drop it as unrecoverable legacy* —
rejected: it is a live operator ruling in the current tracker, which outranks every other
layer.

**Guard.** Do not import the QMX-discussion dead zone. Its 1-hour OVERNIGHT window, its
`SESSION_WARMUP` gate, and the "house money disabled during overlap warmup" clause all
belong to the dead slot/DPR machinery.

### What would change it

If the operator's real intent is "the *system* pauses to re-analyse" rather than "entries
are blocked," this becomes a scheduled-work window (compute) rather than a trading gate,
and it leaves the risk domain entirely.

---

## PK-9 — Correlation ledger: computed outside, declared on CT-23, enforced node-side (P-3)

### What the evidence layers say

**Current corpus.** Audited and definitive: "**correlation ledger LIVE** (one of the five
Records streams)" while "DPR + PRS DEAD by operator ruling DEC-0093"
(`tracker/trading-node-notes.md:31`). ADR-0008 assigns COMP-QMF-RISK "correlation
evidence" (`docs/decisions/ADR-0008…:31`), and that is the *only* substantive current-corpus
statement — "correlation does not otherwise appear as a defined term"
(`extract-local-current.md:281`).

**Computed vs enforced, across layers.** Computed at exam: CT-EXAM-02 carries `cohort_id,
book_id, correlation_observations, expected_loss_shape, certified_at_utc`
(`extract-local-recovery.md:246`). Enforced through the chorus flag, which "owns rate and
clustering shape, not amount lost" (DEC-0048 legacy) — but its threshold
`chorus_expected_frequency_rule (F_CHORUS)` is **null under GAP-0012**, so the rung is
"**reachable but inert (never fires)** in V1; no invented threshold"
(`extract-old-planning.md:225`). Old node docs concur: the `correlation_ledger` stream
exists with "correlation values are not money" and payload/event-type "remain OPEN";
`registration_screen_thresholds` deferred and null (`extract-old-node-docs.md:236-237`).

**Three-way name collision — flag hard.** (1) *cohort correlation* (this item);
(2) `correlation_rules` in fill attribution, which is bot-ownership label / `clientMsgId`
matching and is a completely different mechanism (`extract-old-node-docs.md:238`);
(3) AD-14's `correlation_id`, the tracing annotation
(`ARCHITECTURE-SPINE.md:149`). A builder will conflate at least two of these.

### Bucketing proposal

**Exactly P-3's shape, adopted:** the correlation **contract** stays QMF as a declared
input shape on CT-23; the computation happens outside (exam / analytics); enforcement is
node-side (`reviews/five-hats-sweep.md:172-174`).

### Recommended ruling

**QMF carries three things and no more:**
1. A declared **cohort-correlation evidence** input shape on CT-23: the observations, the
   expected loss shape, cohort membership by fingerprint, and a stated as-of knowledge time
   (the last is needed because A-4's correction problem applies here too).
2. The correlation ledger as a record/journal stream **shape**, writer-only, no reader
   invented — matching how the corpus already ships it ("ships writer-only (no reader, no
   invented schema)", `extract-old-planning.md:223`).
3. **No threshold.** F_CHORUS stays null. AD-13 forbids inventing it and every layer
   refuses to.

**Rename apart in the glossary**, using AD-8's own precedent for the three calendar kinds:
*cohort-correlation evidence* (risk), *fill-attribution label* (venue, CT-18/AD-27), and
*`correlation_id`* (tracing, AD-14) are three distinct terms that must never be used for
each other.

**Do-not-revive guard.** The legacy `correlation_multiplier = max(0.3, 1.0 −
correlation_penalty)` (`extract-qmx-discussion.md:246-249`) is part of the dead
multiplier-stack / slot-auction machinery (DEC-0018, DEC-0079, DEC-0093). Correlation does
not size anything.

Alternatives weighed. (a) *Compute correlation inside qmf-risk* — rejected: it would need
qmf-data and qmf-indicators edges, which AD-2's default-deny forbids without a spine
amendment, and it is Book runtime behavior. (b) *Ship an enforcement threshold now* —
rejected by AD-13 and by every layer's explicit refusal. (c) *Leave it entirely node-side* —
rejected: then the PM's most-requested control has no seam at all, which is P-3's exact
complaint.

### What would change it

Nothing pending. The threshold arrives when there is measured cohort evidence to derive it
from, which is a later sitting.

---

## PK-10 — Always attach a venue-resident protective stop where CT-18 declares support

### What the evidence layers say

**QMX-discussion (oldest, but the only layer that states it).** VERBATIM behaviour:
"always-armed broker-side hard SL set at order placement independent of the SL/TP
authority" (`extract-qmx-discussion.md:233`, `09-kill-switch-authority.md:354-374`).

**Current corpus / AD-28.** CT-18's declared field roster includes the order-parameter
vocabulary "order type… time-in-force; **protective-stop attachment**"
(`ARCHITECTURE-SPINE.md:271`) and the protection primitives `suspend-new | drain |
close_all` (`:286`). So the capability is already a declared, fingerprinted fact — this is
also five-hats P-8's point that capabilities must be storable evidence, not a live probe.

**The forcing argument.** From PK-5: during an outstanding UNKNOWN, `flatten` is blocked by
ratified law while `suspend-new` is not. And AD-27's flatten authority explicitly names
"**VPS-death included**" as a case this sitting must answer
(`ARCHITECTURE-SPINE.md:276`). If the node is dead, no node-side authority exists at all.
The only protection that survives a dead node, a dead connection, or an outstanding UNKNOWN
is one that already rests at the venue.

### Bucketing proposal

**Policy is node/Book; QMF carries the declaration and the refusal.** The Book's control
policy declares "protective stop attachment: required | optional"; where required and CT-18
declares no support, order placement is an `unsupported capability` refusal rather than a
silent unprotected order.

### Recommended ruling

**Every live order attaches a venue-resident protective stop at placement, where CT-18
declares support. Where it does not, the Book must declare explicitly whether it still
trades that venue unprotected.**

Consequences worth stating plainly:
- Tier 1 of the PK-3 law becomes non-empty, so a stop exists that no node failure can
  cancel.
- The stop is a *floor*, not the exit policy. Ordinary exits, amendments, and force-flat all
  still operate above it at PK-3 ranks 2–4; the venue stop is what remains when they cannot.
- It does not decide DEC-0067 (exit ownership, still an open conflict). Attaching a
  protective stop is a *placement parameter*, not an exit organ.
- The stop's presence is visible to the broker. That is the real cost and the operator
  should weigh it knowingly.

Alternatives weighed. (a) *Node-resident stops only* — more deterministic ordering (tier 1
empties, PK-3 becomes a clean total order) and no broker visibility, but it means a dead
VPS leaves positions completely unprotected. Rejected on consequence asymmetry. (b) *Attach
only above a size threshold* — invents a number. (c) *Rely on a venue dead-man switch* —
not established for any venue in any corpus layer; may only ever be a CT-18 declaration.

### What would change it

An operator preference for broker-invisible stops, or a CT-18 verification finding that
attached stops behave badly on the actual venue (e.g. widened during volatility). The first
is a values call; the second is measurable at the warm-up week already scheduled
(`tracker/trading-node-notes.md:21`).

---

## PK-11 — Verify the day-boundary socket expresses prop-firm-shaped rules (P-6)

### What the evidence layers say

AD-8 ships the socket deliberately: "a third named kind exists: the **day-boundary
calendar** — an accounting-boundary rule parameterized by **account** (a prop firm's
daily-loss day evaluated in its stated timezone is one) — it answers only 'which day does
this instant belong to for evaluation'… **This holds the seam only; no prop firm is modeled
in V1**" (`ARCHITECTURE-SPINE.md:98`). AD-9 already lists `prop-firm` as an account role
(`:110`); `docs/components/qmf-risk.md:61` repeats it.

P-6 asks the risk sitting to test the socket against the *shape* of real constraints: "a
daily-loss rule needs a day boundary **and** a named baseline (equity at day start versus
intraday high-water), a trailing max-drawdown needs a high-water mark that survives process
restarts and is evaluated while positions are open, and both need evaluation on unrealized
P&L" (`reviews/five-hats-sweep.md:184-186`).

### Bucketing proposal

**Stays QMF as contract surface** on CT-22/CT-23. No firm is modeled; only the rule-
expression shape.

### Recommended ruling — verification verdict, three parts

1. **Day boundary: PASSES.** AD-8's account-scoped day-boundary calendar already answers
   "which day," carries its own identity and version, and produces TradingDates. Nothing to
   add.
2. **Named baseline: FAILS — needs minting.** Nothing in QMF names a baseline as a
   first-class declarable value. Mint a small enum on the Book rule shape, addable-never-
   redefined per AD-5: `day_start_equity | cycle_start_equity | running_high_water`. This
   is the missing half of P-6.
3. **Named quantity: PARTIAL — needs a declared derivation, not just a type.** AD-7 gives
   `Money(currency, scale)`, but "equity including unrealized P&L" is *derived*: the venue
   has no native equity field, so equity is "balance + quote-currency unrealized PnL"
   (`tracker/trading-node-notes.md:15`) with nativeness declared in CT-18
   (`ARCHITECTURE-SPINE.md:275`). The rule must therefore name a **quantity with a declared
   derivation identity**, so two Books evaluating "equity" are provably evaluating the same
   thing.

**Restart survival: solved by construction, no new machinery.** A trailing high-water mark
must not be mutable stored state. Make it a **read-time fold** over the evidence stream —
the same idiom AD-25 uses for structure lifecycle and AD-27 for order state. It is then
restart-proof, rebuild-proof, and correct while positions are open.

**Verdict: the socket is wide enough once the baseline enum and the derivation-identity
requirement are added.** The rule-expression triple — (day-boundary calendar identity +
version, named baseline, named quantity with declared derivation) — expresses a daily-loss
limit, a trailing max-drawdown, and a Book's own kill-line, generically, with no firm
modeled. It also reuses cleanly for PK-7's calendar-triggered force-flat.

Alternatives weighed. (a) *Defer until a real prop firm is onboarded* — rejected: P-6's own
argument is that widening the socket later is a format-version mint, and the cost of adding
two declarations now is near zero. (b) *Model a specific firm's rules* — refused outright by
AD-8's "no prop firm is modeled in V1" and AD-9's broker-identity-is-deployment-config
ruling.

### What would change it

A prop-firm rule shape that evaluates on something other than an account-scoped daily
quantity against a baseline — e.g. a per-trade consistency rule or a profit-split
calculation. Those are reporting/analytics shapes, not risk-gate shapes, and would land in
a different contract rather than widening this one.

---

## Cross-cutting notes for the sitting

**Do-not-revive checks performed.** DPR/PRS, 0-100 scores, T1/T2/T3 tiers, slot auctions,
global bot pools, paper-redemption/probation, WF3 mechanics, and parallel Bot paper twins
were checked against every recommendation above and none is reintroduced. Three near-misses
were specifically guarded: the legacy KSA per-level SL-to-breakeven effects and "BE at +1R"
(PK-2, PK-3); the `SESSION_WARMUP` / "house money" clause attached to the legacy dead zone
(PK-8); the `correlation_multiplier` sizing penalty (PK-9). "House of money" and "reverse
house of money" were confirmed to have never existed in any layer
(`trading-node-order-path-study.md:110-111`) and are not designed here.

**GAP-0015 stays empty.** Nothing above assigns a trigger to a KSA level or a level to an
effect. PK-4 assigns *who may flatten under a declared trigger class* — a different axis.
The matrix remains node territory and remains deliberately unfilled.

**Terminology handed to the glossary as must-rename-apart:** *cohort-correlation evidence*
vs *fill-attribution label* vs *`correlation_id`* (PK-9); *door refusal* vs *suppression*
(PK-6); *market-hours* vs *day-boundary* vs *news* calendar (AD-8, already ruled, restated
because PK-7 and PK-8 both touch it).

**Sequencing note for the sitting chair.** PK-1 removes the X-5 blocker, so this cluster
does not have to wait on Book-to-venue cardinality. It still consumes AD-28's CT-18 roster
(PK-3 scope resolution, PK-10 attachment support), which is already ratified — T-4's
dependency is satisfied.
