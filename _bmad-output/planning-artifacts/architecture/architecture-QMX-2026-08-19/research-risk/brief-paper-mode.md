---
cluster: paper-mode
scope: GAP-0041 — Book-level paper mode; bot→demo-account mapping; live↔paper transitions; duplicate-order prevention; comparable evidence. Plus five-hats A-1 (comparison cohort rule) and X-6 (suppressing condition on evidence).
inherits: AD-12 (paper/demo = world live), AD-17 (binding outside Bot identity), AD-26 (binding identity), AD-27 (command identity + stream), AD-28 (two-connection demo/live; pinned canonical feed), K-27 (paired demo)
standing: framework-vs-node (2026-08-19); DO-NOT-REVIVE list; AD-13 no invented numbers
date: 2026-08-20
status: decision brief for operator ruling — nothing here is ratified
---

# Decision brief — Book-level paper mode (GAP-0041)

## What this cluster actually is

Everything in the corpus about "paper" answers one of four questions, and the four have
been tangled together for two corpus generations:

1. **Where does the paper state live?** (Book, Bot, or seat.)
2. **What is paper FOR?** (A morgue window after a failure, or a standing evidence
   producer for alpha-decay sensing.)
3. **How does an order physically reach a demo account without ever double-firing?**
4. **When is a paper result stream allowed into the same judgment as a live one?**

Question 1 is close to closed. Question 2 is an open operator-level contradiction sitting
in `tracker/trading-node-notes.md:25`. Question 3 is, I think, already solved by the
ratified venue ADs and nobody has noticed. Question 4 is the one that decides whether the
whole paper-mode design delivers the thing it was ratified for — and it is genuinely
undesigned in every corpus layer.

## Precedence applied

Per `tracker/map.md:23`: **current operator rulings > old wiki (2026-07 delta) > GitBook
baseline (2026-07-08/18 capture) > QMX-discussion (oldest vault)**. Two consequences bind
this whole brief:

- The **GitBook "frozen counterfactual / morgue window" framing** (`extract-live-gitbook.md`
  §7 → `components/paper-mode-system.md`, DEC-0014; `extract-old-recovered.md` §7 →
  `clash-report-bot-rating.md:43-47`) is *third* in precedence and is overridden on scope by
  the operator's own 2026-08-18 dictation — but only on **evidence** scope, not on **money**
  scope. Those are separable and both survive (see PM-2, PM-8).
- The **wiki "fail-mechanism-only" narrowing** (K-25; `extract-local-recovery.md` §7 →
  `TND-DELTA:71`; `extract-old-planning.md` §7) is a *V1 build-scope* decision of the old
  trading node, not a semantic ruling about what paper is. It is second in precedence and
  the operator's later dictation outranks it.

## Standing rulings honored

- **Not revived anywhere in this brief:** paper-redemption / probation loops, parallel Bot
  paper twins (DEC-0069), T1/T2/T3 tiers, DPR/PRS, 0-100 scores, WF3, slot auctions.
  The legacy "re-promotion requires ≥10 positive demo trades + manual approval"
  (`extract-qmx-discussion.md` §7 → `08-paper-trading-demotion-service.md:62-73`) is
  **dead donor material** and is deliberately not carried forward.
- **AD-13:** no number in this brief. Every threshold below is a *declared field*, never a
  value.
- **AD-17:** every cardinality-one I recommend is called out as needing an explicit ruling
  rather than being assumed (PM-3).

---

## PM-1 — Confirm DEC-0070: paper is a Book-level mode; twins stay dead

### (1) What the evidence layers say

**Current corpus (highest precedence), but flagged provisional.** ADR-0009 decides: *"Paper
operation is a Book-level state: a Book that cannot trade live directs its attached Bot
activity to the Book's paper account so evidence continues. (DEC-0070)"*
(`docs/decisions/ADR-0009-book-level-paper-mode.md:31`). Its own Consequences say the direct
operator wording is missing from the SRC-01-C0022 export and survives only via the
SRC-01-C0023 recap (`ADR-0009:35`). CT-24 is therefore `wiring_status:
reserved-evidence-only` with an explicit `authority_note` to the same effect
(`docs/contracts/ct-24-book-mode.yaml:24-34`). The glossary repeats the caveat
(`docs/glossary.md:272-274`).

**The missing wording is not actually missing — it is in the tracker.** `tracker/map.md:47`
(evening verdicts, 2026-08-18) records: *"**paper mode is BOOK-level** (Book switches to a
paper account when it can't trade live; bots never run parallel twins; one bot = one
Book)"*. That is an independent, dated, session-verdict record of the same ruling, written
the same evening as the transcript whose export lost it. It corroborates the recap rather
than replacing it.

**The mechanism is already ratified underneath it.** AD-17: *"Bot identity is its content;
the Bot↔Book↔account binding is a separate dated binding record outside Bot identity — one
Bot at exactly one Book at any time, but re-binding (paper → live) never mints a new Bot, so
paper and live performance stay comparable for alpha-decay sensing."*
(`ARCHITECTURE-SPINE.md:167`, DEC-0115). AD-12 supplies the world answer: paper/demo runs are
`world = live` because the **account role** carries money-reality (`SPINE:136`; DEC-0110).
So "Book-level paper mode" reduces to *a dated change of which account the Book's binding
points at* — a record change, not a new object.

**Legacy layers agree structurally.** Old node docs carry a book-mode registry with
`V1_BOOK_MODES = {LIVE, PAPER}` and a per-`book_id` current row plus an append-only
transitions table (`extract-old-node-docs.md` §4 → `mode_registry.py:38-40`,
`mode-registry-...json:42-49`). QMX-discussion's oldest layer had the *opposite* shape — a
per-bot routing table `EXECUTION_LIVE | EXECUTION_DEMO` keyed by bot state
(`extract-qmx-discussion.md` §7 → `08-paper-trading-demotion-service.md:26-33`) — which is
the bot-centric ancestor DEC-0069 killed. Precedence resolves cleanly toward Book-level.

### (2) Bucketing

**Both.** QMF carries: (a) the **account-binding record** and its dated supersession
(qmf-registry, AD-9/AD-16/AD-26 — identity `(VenueId, AccountId, role, world)`); (b) a
**Book-mode record contract** (CT-24) that is a *record shape plus a read-time fold*, not a
state-machine engine — same discipline AD-25 and AD-27 already use for structure lifecycle
and order state. The node carries: when a Book flips, what conditions trigger it, and the
runtime routing table.

Explicitly **not** QMF: a `BookModeMachine` class. CT-24 should mint the transition record
kind and state the read-resolution rule ("current mode = fold over the append-only
transition stream for this `book_id`"), nothing more.

### (3) Recommended ruling

**Confirm DEC-0070 as ratified.** Paper is a Book-scoped execution mode expressed as a dated
change of the Book's account binding. No Bot twin, ever. One Bot, one Book, one active
execution binding at a time.

Alternatives weighed: (a) *per-Bot routing state* (the QMX-discussion ancestor) — rejected,
it is DEC-0069 and it re-splits Bot identity; (b) *leave CT-24 evidence-only until a cleaner
transcript surfaces* — rejected, the corroboration is now two independent dated records plus
a ratified mechanism (AD-17) that only makes sense under this ruling, and every other item in
this cluster is blocked behind it.

### (4) What would change it

A transcript surfacing where the operator describes routing at the **Bot** level rather than
the Book level, or a requirement that one Bot produce live and paper streams *simultaneously*
(which would resurrect twins and would need DEC-0069 reopened, not worked around).

---

## PM-2 — What paper is FOR: standing evidence state, not a morgue window

### (1) What the evidence layers say

This is the **live contradiction on the record**: *"Paper-mode scope: fail-mechanism-only
(K-25 delta) vs standing-state feeding alpha-decay (tracker/map.md, ticket 002). Risk-sitting
item (GAP-0041)."* (`tracker/trading-node-notes.md:25`).

**Operator dictation, verbatim, highest precedence** (`tracker/tickets/002-qmf-minimal-core.md:45`,
2026-08-18): *"Paper trading is a STANDING STATE, not a waiting room: bots paper-trade under
documented conditions (kill switch fired, daily limit hit, prop-firm rules) and results are
recorded continuously regardless — feeding ALPHA-DECAY sensing, which needs uninterrupted
data points."* Reinforced the same day for news: *"while blocked, bots may continue in paper
mode so alpha-decay data keeps flowing"* (`tracker/map.md:78`).

**Wiki layer (second):** trading-node paper is **fail-mechanism-only** — exactly two paths,
kill-line stand-down (book LIVE→PAPER) and breaker bench (bot LIVE→BENCHED); all pre-live
paper relocated to the certification side (`extract-local-recovery.md` §7 → `TND-DELTA:71`,
K-25; `extract-old-planning.md` §7 → SPINE(old):238).

**GitBook layer (third):** *"Paper mode is diagnostic. It freezes the counterfactual balance
at flip and preserves evidence after a breaker, kill-line stand-down, or demotion.
DEC-0014."* (`extract-live-gitbook.md` §7). And the sharpest legacy line: *"Paper is a
morgue window, not a comeback arena"* (`extract-old-recovered.md` §7 →
`clash-report-bot-rating.md:43-47`).

**These are not actually in conflict once you separate money from evidence.** The GitBook
framing is a statement about **money and promotion** (frozen balance, gains are not Treasury
cash, the redemption loop is dead). The operator's framing is a statement about **evidence
continuity**. The only genuine collision is *scope of triggers*: two events (wiki) versus a
class of conditions (operator).

### (2) Bucketing

**Both.** The *trigger set* — which conditions put a Book into paper — is Book runtime
behavior, node territory. QMF carries the consequence: the evidence contracts must treat a
paper stream as **ordinary continuous evidence** (not a special diagnostic artifact), and
the result label must be able to say which conditions were in force (see PM-6).

### (3) Recommended ruling

**Paper is a standing evidence state with frozen money.** Concretely, three clauses:

- **Evidence side (operator's ruling, adopted):** a Book that cannot trade live for *any*
  declared reason routes its Bots' activity to its paper target and keeps producing
  decision, order, and fill evidence continuously. The trigger set is open by class
  ("any condition that blocks live execution"), not a closed enumeration of two.
- **Money side (GitBook's ruling, retained):** paper P&L is evidence only. It never becomes
  Treasury cash, the counterfactual balance is frozen at flip and never hand-adjusted, and
  the kill-line remnant restart stays dead. (PM-8.)
- **Promotion side (DO-NOT-REVIVE, retained):** paper performance **never earns a live
  seat**. Return to live is authorized by a boundary or a human, never by paper results.
  This is what "morgue window, not a comeback arena" was actually protecting, and it stays.

Alternatives weighed: (a) *keep fail-mechanism-only for V1 and widen later* — tempting for
build scope, rejected because the trigger set is a **contract-shape** decision (whether the
transition record's `trigger_kind` is a closed two-value enum or an open addable kind), and
narrowing it now costs a format-version mint later under AD-5 for no benefit; (b) *paper as
a full standing state including promotion* — rejected, that is the dead redemption loop.

### (4) What would change it

The operator saying the standing-state dictation was about the **certification** side (the
lab), not the node — in which case the node keeps only the fail-mechanism transitions and
continuous paper evidence comes from somewhere else entirely. This is the single most
consequential question in the cluster and is why it goes to the operator despite precedence
already pointing one way.

---

## PM-3 — Bot→demo-account mapping: the paper-routing target on the binding

### (1) What the evidence layers say

**Ratified venue facts (current).** *"Demo and live are separate cTrader hosts; serving both
simultaneously REQUIRES two connections (one demo, one live), each carrying unlimited
accounts of its kind. This is the mechanism for the corpus's paired-demo fail-safe rule
(K-27)."* (`tracker/trading-node-notes.md:8`; AD-28 declares session topology as CT-18
surface, `SPINE:286`). Glossary, DEC-0138: *"Paired demo: A demo binding run simultaneously
alongside a live binding under the venue's declared session topology... Paired-demo bindings
are secret-reference-only records identified as ordinary account bindings"*
(`docs/glossary.md:268-270`). AD-26 pins binding identity as `(VenueId, AccountId, role,
world)` with the secret reference excluded from `fp1` (`SPINE:260`).

**Wiki layer, K-27, verbatim:** *"Every live account binding has a paired demo binding for
fail-mechanism fills, while sensing stays on the pinned canonical live feed."*
(`extract-local-recovery.md` §7 → `TND-DELTA:73`).

**Old node docs, the most concrete layer.** `paired-demo-binding-per-live-account-binding.json`
(Story 4.6, *"connection_manager owns pairing"*): live binding requires demo-pair candidates,
**exactly one** demo pair, verification evidence (`:14-27`); demo binding **excluded from live
technical-kill drift checks** — *"paired demo binding is the fail-mechanism paper route, not
a live drift target"* (`:29-33`); proof record carries `live_binding_id, demo_binding_id,
verification_state, routing_consumers`, with routing consumers `kill_line_stand_down,
breaker_bench_paper_routing, promotion_safety_checks` (`:50-70`); secrets metadata-only via
`secret_ref` (`:80-84`). (`extract-old-node-docs.md` §7.) Book↔account is **one account :
many books** (`extract-old-node-docs.md` §3 → `qmx-console-experience-architecture-v0.2.md:159-161`).

**Operator fact:** *"multiple demo accounts expected"* (`tracker/map.md:47`).

**Collision with AD-17.** "Exactly one demo pair" is a hardcoded cardinality-one. AD-17
forbids that *without a ruling* (`SPINE:167`). So it cannot simply be inherited — it must be
ruled here, deliberately, with its reason stated.

### (2) Bucketing

**Both.** QMF carries: a **`paper_routing_target`** field on the account-binding record —
itself a binding reference, dated, superseded by append (AD-16 edges), never inline
credentials (AD-26); plus a typed refusal when a paper transition is attempted with no
resolvable target. The connection manager already owns session pairing under AD-28
(`SPINE:283`, sole owner of venue sessions), so the *pairing act* is adapter/node work; QMF
holds the record shape and the refusal.

Note the AD-19 room implication: demo, paper-validation and paper-benched roles write to
role-scoped namespaces within `world = live` (AD-12, `SPINE:137`). So a paper routing target
is also a **namespace selector**, not just a connection selector.

### (3) Recommended ruling

**Many demo accounts may exist; a live binding declares exactly one *active* paper-routing
target at a time, and that "one" is ruled deliberately because ambiguous routing is how you
get double-fires.**

- The account layer stays plural (AD-17 respected: a Venue holds many Accounts; an operator
  may hold many demo accounts).
- The **binding** layer is single-valued *at an instant*: `live_binding → paper_routing_target`
  resolves to exactly one binding, or the paper transition refuses (`unavailable dependency`).
  It is a dated record, so it can be re-pointed at any time by minting a new binding record
  with a `supersedes` edge — cardinality-one at an instant, never cardinality-one over time.
- The paper target is **excluded from the live binding's reconciliation drift check** —
  carried forward verbatim from `paired-demo-...json:29-33`, and it is the correct answer
  under AD-27's reconciliation rule (`SPINE:275`) because a demo account's equity is *expected*
  to diverge from the live virtual ledger by design.
- **A live binding without a declared paper target is legal to trade** but cannot be ruled
  into paper — the refusal fires at the transition, not at the door. (The old standard made a
  paper target a precondition of *going live*; that is a node deployment policy, not a
  framework invariant, and forcing it into QMF would be the framework legislating node
  behavior.)

Alternatives weighed: (a) *paper target as a per-Book field* — rejected, it duplicates the
same demo binding across the many Books on one account and gives two places to disagree;
(b) *derive the demo pair by convention from the live account* — rejected outright, it is
symbol-parsing by another name and AD-9's opacity discipline forbids deriving identity from
attributes; (c) *allow N paper targets with a selection rule* — rejected as an unforced
choice: nothing in any corpus layer wants it, and it reintroduces the routing ambiguity the
single target exists to kill.

### (4) What would change it

A prop-firm or multi-venue Book (P-4, another cluster) that must fail over to a target at a
*different* venue — then the single target becomes a per-venue-scope single target, and this
ruling needs the Book↔venue cardinality answer first. **Flag this dependency: PM-3 should be
ruled after, or jointly with, Book-to-venue cardinality.**

---

## PM-4 — Duplicate-order prevention: already closed by AD-27; state it and move on

### (1) What the evidence layers say

**Legacy mechanism.** *"Duplicate-order prevention (shared-account command merge): deterministic
ordering by `book_sequencer_sequence`; `duplicate_sequence_refused: true`,
`missing_sequence_refused: true`, `stable_tie_refusal: true`; allowed kinds `place_order,
cancel_order, close_position, close_all`"* (`extract-old-node-docs.md` §7 →
`paired-demo-...json:85-97`). Glossary DEC-0138 keeps the rule: *"a shared-account
order-lifecycle merge uses only the caller's sequencer evidence, never a venue-side id"*
(`docs/glossary.md:270`). Wiki: *"Each Book has a deterministic sequencer for shared live/demo
command ordering"* (K-06, `extract-local-recovery.md` §7). The GitBook and old-vault layers
have **no** duplicate-order concept at all — only `clientMsgId` correlation and `label` fill
attribution (`extract-old-wiki.md` §7 → `connection-manager.md:28`; "partial finding" by that
extractor's own admission).

**Current spine already carries every piece of it.** AD-27 (`SPINE:270-272`):
- the command stream unit is **(VenueId, account)** — so a live account and a demo account are
  *different streams by construction*; they cannot collide with each other, ever;
- command identity is derived from the command record's `fp1`, including the (VenueId,
  account) qualification, session epoch, and **"the caller's opaque ordering ordinal (a
  venue-native id is never sufficient alone; QMF carries the ordinal field, the node owns the
  sequencer)"** — that is `book_sequencer_sequence`, generalized and already ratified;
- *"Idempotency and collision tests run against the full local fingerprint, never the
  venue-side id: re-presenting the same command is an idempotent accept; differing content
  under a reused identity is refused and alarmed."* — that is `duplicate_sequence_refused` +
  `stable_tie_refusal`, already ratified;
- the four allowed kinds match exactly (`SPINE:271`).

### (2) Bucketing

**QMF-seam** — and the seam already exists. The residual work is a *sequencer instance*
obligation on the node: one ordinal source per (VenueId, account), shared by every Book bound
to that account (because Book↔account is one-account-many-books). AD-27 already assigns
sequencer ownership to the node; the risk sitting only needs to record the granularity so a
node implementer does not mint one sequencer per Book on a shared account and reintroduce
tie ambiguity.

### (3) Recommended ruling

**No new mechanism. One clarifying rule.**

> The execution binding is resolved **once per intent**, at intent-mint time, from the Book's
> current mode fold, and the resolved binding is part of the command record's identity content.

That single rule closes the only genuinely new risk the live↔paper seam creates: an intent
in flight while the Book flips. Because the binding is stamped into the fingerprint before
submission, one intent can never produce two submissions; and because live and demo are
different (VenueId, account) streams, a flip cannot make one stream's state gate the other's.

Corollary worth recording: **a mode flip never replays, resubmits, or mirrors a command.**
AD-27 already prohibits retry and adapter-initiated flatten (`SPINE:276`); this states it for
the flip case specifically.

Corollary two: **an outstanding `UNKNOWN` on the live stream does not block paper routing**
(different stream), and equally, the mode-change record is written immediately regardless —
evidence never waits on a venue. What the outstanding UNKNOWN *does* block is any statement
about the open live position's fate, which is PE-7 territory and belongs to another cluster.

### (4) Why this is safe to close on delegation

Every element is either verbatim-ratified in AD-26/AD-27 or a direct derivation from the
(VenueId, account) stream unit. Nothing here is a policy choice the operator would decide
differently with more information; the legacy mechanism maps onto the ratified one with no
residue.

---

## PM-5 — The comparison cohort rule (five-hats A-1)

### (1) What the evidence layers say

**This is the question that decides whether Book-level paper mode delivers what it was
ratified for.** A-1 states it exactly: *"AD-12 deliberately assigns paper and demo runs
`world = live` so they stay comparable to live for alpha-decay sensing — the right call.
Comparability, though, needs more than world equality"* (`five-hats-sweep.md` A-1). Without a
cohort rule, an analyst compares a live scalper against a demo feed and reports the
**execution difference as alpha decay**.

**The corpus contains exactly one line that answers it, and it is a good one.** Wiki layer,
verbatim: *"A paper-phase bot uses the paired demo account binding but judges the same
canonical market feed as live trading"*, with the invariant *"live and paper use the same
pinned canonical sensing feed"* (`extract-old-wiki.md` §7 → `components/paper-mode-system.md:15,44-51`).
Old-vault layer says the same thing from the other side: demotion is *"a routing flip, not a
re-implementation. The code path from bot signal generation to order submission is identical
in both modes."* (`extract-qmx-discussion.md` §7 → `08-...demotion-service.md:33`).

**AD-28 has already ratified the hard half of it:** *"The pinned canonical sensing feed carries
a prohibition, not just a capability: no silent sibling-feed failover — a sensing outage fails
closed until the same feed gap-replays."* (`SPINE:285`). So the *sensing* leg of comparability
is locked. Nothing locks the rest.

**Adjacent ratified parity requirement:** the legacy exam certificate is *invalid if live
labelers differ from exam* (`extract-old-node-docs.md` §7 → `labeler-catalog-...json:64`;
`extract-gitbook-capture.md` §14 → CT-EXAM-01 pins `labeler_versions`). That is the same idea
one layer up: a judgment is only valid across streams computed by the same configured
producers.

**Not found anywhere, any layer:** a cohort definition, an admissibility rule, or a metric
container. A-2 makes the same point from the reporting side (*"nothing in the seven-package
roster owns a performance result"*).

**One seam hazard nobody has flagged.** AD-12 role-scopes namespaces *within* `world = live`:
the live namespace admits only `role = live` records; demo, paper-validation and
paper-benched write to their own role-scoped namespaces (`SPINE:137`). AD-19 refuses reads
that cross **worlds** (`SPINE:179`) — it says nothing about crossing **roles**. If nobody
states that a decay cohort read is a legitimate cross-role read within one world, the
role-scoping designed to keep evidence honest will be read as forbidding the exact comparison
AD-12 exists to enable.

### (2) Bucketing

**QMF-seam, wholly.** This is a contract shape plus a read-time refusal — no runtime
behavior. It belongs on the performance-result container A-2 asks the risk sitting to mint,
and it is enforced where the read happens (qmf-risk / qmf-data), not in the node.

### (3) Recommended ruling

**Mint a declared `cohort_key` on every performance result, and refuse rather than average.**

The cohort key is the tuple that must be **equal** across two streams before they may enter
one decay judgment:

| Part | Why |
| --- | --- |
| Bot identity (content fingerprint, AD-17) | rebind never mints a new Bot, so this is stable across the flip — the whole point |
| Book identity + book-type contract format version | the Book sets the bar; a Book-rule change is a new bar |
| Sensing feed identity (the pinned canonical feed, AD-28) | the legacy comparability guarantee, made checkable |
| Configured-producer fingerprints (indicator/labeler/structure, AD-22/AD-23/AD-12) | the exam↔live labeler-parity rule, generalized |
| Calendar identity + version (AD-8) | TradingDate equality is only defined within one calendar |
| Instrument identity, or an operator-minted equivalence record (P-1) | six brokers' EURUSD are six identities |
| The **suppression set** in force over the evidence range (PM-6) | X-6 |
| **Account role** — recorded, deliberately **not** required equal | this is the one part that is *allowed* to differ; it is what makes paper↔live comparison possible at all |

Three rules ride on it:

1. **Decision-level, not cash-level.** Decay is judged on decision-quality quantities
   denominated in R (`registry:original_risk_unit`, DEC-0076) — expectancy by regime, fire
   rate, mean loss in R, breaker expectation — never on realized account cash. This follows
   necessarily from "paper gains are not Treasury cash" and from the demo account's fills
   being a different execution population. **Execution quality (slippage, spread-at-fill,
   rejection rate) is a binding-scoped fact and is never comparable across the flip** — it is
   measured and reported, never folded into a decay verdict.
2. **Unequal key ⇒ separate cohorts, and a judgment spanning them is a `policy rejection`
   refusal**, not a silent average. Same discipline AD-25 already uses for confirmed vs
   unconfirmed evidence (`SPINE:243`: *"a read requesting confirmed evidence refuses
   unconfirmed rows rather than filtering silently"*).
3. **A decay cohort read is an explicitly permitted cross-role read within `world = live`**,
   with the role recorded as a cohort part. State it, or AD-12's role-scoping accidentally
   forbids it.

Alternatives weighed: (a) *flag rather than refuse* — rejected; a flag on an analytic output
is read by a human at 3am and ignored, and the refusal costs nothing because widening the
cohort is one declared exclusion away; (b) *compare on realized cash with an execution-quality
adjustment* — rejected hard, that is inventing a slippage model to compare against a demo
account, which is exactly the fiction L6/L20 forbid; (c) *no cohort rule, rely on the
analyst's judgment* — rejected, that is the A-1 failure mode verbatim.

### (4) What would change it

If the operator wants decay sensed on realized money rather than R-denominated decision
quality — which would be a legitimate different philosophy, but it would make live↔paper
comparison structurally impossible and would need paper reclassified as non-comparable
evidence, unwinding AD-12's world ruling.

---

## PM-6 — Evidence produced under an active control carries its suppressing condition (X-6)

### (1) What the evidence layers say

**A direct precedence collision sits here.** GitBook constitution L9, verbatim: *"News-affected
currency pairs are blocked for all books in live and paper mode. DEC-0010."*, and SCN-0003
asserts *"no paper data is collected under a known invalid news window"*
(`extract-live-gitbook.md` §7-8; `extract-gitbook-capture.md` §7). The wiki layer carries it
forward identically (`extract-local-recovery.md` §8). **The operator ruled the opposite on
2026-08-18:** *"news is PAIR-SCOPED — block only affected pairs, keep trading everywhere else;
while blocked, bots may continue in paper mode so alpha-decay data keeps flowing"*
(`tracker/map.md:78`). Precedence gives it to the operator.

**X-6 is the consequence nobody priced:** *"paper evidence generated during a blackout comes
from a population the live Book was forbidden to trade — same world, same label shape,
non-comparable content."* A-7 arrives at the same record from the reporting side: *"Suppressed
actions are the highest-value analytic dataset in the system... without it, every news window,
SQS gate, and kill-switch fire looks like decay."*

**The journal already has room for it.** AD-21's seven event types are `decision, order, fill,
risk transition, promotion, data quality, control action` (`SPINE:191`). Adding an eighth
would be a mint; nothing needs one.

### (2) Bucketing

**Both.** QMF carries two shapes: (a) a **suppression annotation** on a `decision` journal
event — suppressing authority, reason class, scope, and the would-have-been action; (b) a
declared, identity-bearing **`active_controls`** field on the AD-12 result label, listing the
controls in force over the result's evidence range. The node produces the events at runtime
and owns the control logic itself (news windows, SQS gate, kill switch are all node
territory by the 2026-08-19 ruling).

Under AD-10 every contract field is identity by default; `active_controls` should stay
identity-bearing, because a result computed over a suppressed population is genuinely a
different result.

### (3) Recommended ruling

**Yes — paper keeps running under an active control, and every record it produces carries the
control that was suppressing it.** Three clauses:

1. A control that blocks live execution does **not** stop paper evidence collection. The
   operator's 2026-08-18 ruling stands over L9/DEC-0010. (L9's real concern — that a refusal
   must be signed into the veto ledger and that paper must never *pretend* the block did not
   exist — is fully preserved by clause 2.)
2. A blocked decision is journaled as a `decision` event carrying a **typed suppression
   annotation**: suppressing authority (news / SQS / kill switch / Book door / breaker /
   hold limit), scope, reason, and the would-have-been action. No new journal event type; the
   control's own firing remains a `control action` event. This is A-7 and X-6 satisfied by
   one record.
3. `active_controls` is a cohort key part (PM-5). News-window paper evidence therefore forms
   its own cohort by construction and is included or excluded **deliberately**, never
   averaged in.

Alternatives weighed: (a) *keep L9 — block paper too* — rejected on precedence, and it
destroys the uninterrupted data points the operator's whole standing-state argument rests on;
(b) *record paper through the block but leave it untagged* — rejected, it is the X-6 failure
mode and produces confidently wrong decay verdicts; (c) *a separate "suppressed" evidence
stream* — rejected, it splits the journal and breaks AD-21's one-event-per-decision
cardinality for no gain over an annotation.

### (4) What would change it

If the operator decides news-window paper data is *actively misleading* rather than
merely non-comparable (i.e. worth not collecting at all) — a defensible position, but then
the tagging machinery is still needed for SQS gates and kill-switch fires, so clause 2 and 3
survive either way. Only clause 1 is genuinely at stake.

---

## PM-7 — Which live↔paper transitions exist, and who authorizes return-to-live

### (1) What the evidence layers say

**Wiki/old-node layer, the most specific.** V1 accepts exactly two transition kinds:
`kill_line_stand_down` (book-scoped, `bot_id` not required, LIVE→PAPER) and `breaker_bench`
(bot-scoped, `bot_id` required, LIVE→BENCHED, no book-level benched write)
(`extract-old-node-docs.md` §4/§7 → `frozen-counterfactual-paper-semantics.json:33-49`).
Return paths: PAPER→LIVE only via cycle-boundary `re_seed`; BENCHED→LIVE by next-open
auto-reset (`extract-old-planning.md` §7; DEC-0032, DEC-0023). CT-PAPER-01's own rule text:
*"A trading-node transition outside this fail-mechanism set refuses and appends veto-class
evidence."* (`extract-old-wiki.md` §7 → `ct-paper-01:30-35`).

**A recorded contradiction inside that layer:** L-UI says *"birth currently creates the book
in PAPER"*, L-STD Story 5.4 says birth yields `live_ready: true, paper_mode_created: false`,
and `mode_registry.py:44` lists `birth-in-paper` as a *relocated* (refused-here) reason marker
(`extract-old-node-docs.md` §Contradictions). The extractor recorded it unadjudicated. Under
the current spine this is moot: **book birth and first entry into live are certification-side
and promotion-gated**, not a node transition.

**Current corpus, ratified and binding:** *"Only a human may promote an artifact into the live
zone."* (`docs/contracts/ct-24-book-mode.yaml:26`); AD-18's human-only signed promotion
occurrence with the plain-words summary as an identity field (`SPINE:173`, DEC-0041/DEC-0116);
SCN-0006: *"where a live-to-live promotion is involved, only a human-signed promotion
occurrence authorizes it"* (`SCN-0006:35`).

**DO-NOT-REVIVE:** paper-redemption / probation loops are dead. The old-vault re-promotion
gate (`≥10 positive demo trades + manual approval`, `extract-qmx-discussion.md` §7) is donor
material only.

### (2) Bucketing

**Both.** QMF carries the **transition record contract** (CT-24): `book_id`, optional
`bot_id`, from/to, `trigger_kind` (an **addable-never-redefined kind**, AD-5/AD-16, not a
closed two-value enum), the resolved binding before and after, the authorizing evidence
reference (boundary record or human-signed promotion occurrence per AD-18), and
`occurred_at` per AD-8. The node owns which conditions fire which trigger, and when.

### (3) Recommended ruling

**Define transitions by class, and split the return authority in two.**

- **Into paper:** open by class. Any declared condition that blocks live execution mints a
  transition record with its `trigger_kind`. Kinds are addable, never redefined. (This is
  PM-2's ruling made concrete; it is also what makes prop-firm daily-loss rules land as a new
  kind rather than a schema change.)
- **Back to live, mechanical:** permitted **only** where the clearing condition is itself
  mechanical and dated — a breaker bench auto-resetting at next open, a daily budget resetting
  at the day boundary. These are the conditions whose end is a calendar fact, not a judgment.
- **Back to live, human:** required wherever the money zone is crossed — a kill-line
  stand-down returning at re-seed, or a Book entering live for the first time. Authorized by
  an AD-18 human-signed promotion occurrence, never by an automatic rule and **never by paper
  performance**.
- **Evidence never waits.** The transition record is appended immediately on the flip; the
  fate of any open live position is a *separate* record and a separate ruling (PE-7, another
  cluster). Coupling them would let a venue outage block the evidence stream.

Alternatives weighed: (a) *keep the closed two-kind enum* — rejected, it cannot express the
operator's own trigger list (kill switch fired, daily limit hit, prop-firm rules) without a
format-version mint; (b) *all returns human-signed* — rejected, it makes a breaker bench a
daily operator chore and turns the human gate into a rubber stamp, which is T-10's failure
mode; (c) *all returns automatic at the next boundary* — rejected, it lets a Book that hit its
kill line walk back into live money with nobody looking.

### (4) What would change it

The operator wanting a Book's *first* entry to live to be automatic once certification passes
(it currently is not — L17/DEC-0041 make promotion human-only and daily). And PE-7's ruling on
open-position fate, which changes what the transition record must carry — but not who
authorizes it.

---

## PM-8 — Paper money is frozen, is never Treasury cash, and never buys a seat

### (1) What the evidence layers say

Unanimous across every layer, which is rare in this corpus. GitBook: *"May never: hand-adjust
paper balance, revive the dead live-restart-from-remnant path, or treat paper gains as
treasury cash. DEC-0014, DEC-0023."* (`extract-gitbook-capture.md` §7 →
`components/paper-mode-system.md:11-13`). Old node docs make it executable: frozen balance
immutable after acceptance, refusal `PAPER_FROZEN_BALANCE_HAND_ADJUSTMENT_REFUSED`;
`paper_gains_enter_ct_bms_01: false` with refusal `PAPER_GAIN_NOT_TREASURY`
(`extract-old-node-docs.md` §7 → `frozen-counterfactual-paper-semantics.json:50-72,84-85`).
Wiki and local-recovery layers repeat both (`extract-local-recovery.md` §7). Old-vault's
redemption loop is *"structurally dead"* (`extract-old-recovered.md` §7).

### (2) Bucketing

**Both.** The Treasury boundary is Book/BMS runtime (node). QMF carries the tag that makes
the rule checkable: the account role on the binding, role-scoped evidence namespaces
(AD-12/AD-19), and the money-path taint rule (AD-7) that already forbids a paper-derived
figure reaching a live balance without crossing a named boundary.

### (3) Recommended ruling

Carry it forward as an invariant, unchanged:

- Paper P&L is **evidence**, never a Treasury event. A paper gain never crosses the
  book-to-treasury boundary.
- The counterfactual balance freezes at the flip and is never hand-adjusted.
- Paper performance never authorizes a return to live (PM-7).

The frozen-balance *mechanic* (the virtual ledger it freezes) belongs to the money-ladder /
treasury cluster, not here. This item claims only the boundary rule.

### (4) Why this is safe to close on delegation

All four corpus layers agree verbatim, the current corpus's DO-NOT-REVIVE list already kills
the redemption loop, and AD-7's money-path taint plus AD-12's role-scoped namespaces already
provide the enforcement surface. There is no live alternative to weigh.

---

## PM-9 — BENCHED is a roster-seat state, not a Book mode

### (1) What the evidence layers say

**Current corpus refuses to settle it and says so:** *"BENCHED: Do not assign BENCHED a
canonical schema yet. The name is overloaded between Book mode and Bot seat state under
`GAP(GAP-0045)`."* (`docs/glossary.md:518-520`).

**GitBook layer (third) is the source of the overload:** one shared enum `[LIVE, PAPER,
BENCHED, STOOD_DOWN]` used identically by CT-BOOK-02, CT-BMS-02 and CT-PAPER-01
(`extract-gitbook-capture.md` §4 → `contracts/ct-book-02:14`).

**Wiki and old-node layers (second and, for code, most concrete) both split it:**
`V1_BOOK_MODES = {LIVE, PAPER}` with `RESERVED_BOOK_MODES = {BENCHED, STOOD_DOWN}` refusing
on write (`extract-old-node-docs.md` §4 → `mode_registry.py:38-40,342-354`); seat states are a
**bot-level** facet `paper-phase | LIVE | BENCHED` with the invariant *"A BENCHED bot does not
change the book mode"* and *"Breaker auto-reset does not erase the bench event"*
(`object-lifecycle-bot.md:34-51,77-84`); `frozen-counterfactual-paper-semantics.json:43-49`
carries the flag `book_level_benched_write: false`. The wiki delta layer flagged the same
split need in its own words (K-26/C-02).

So: **all three layers that examined it agree the split is needed, and two of them state
exactly what the split is.** The current corpus's refusal is a refusal to *inherit*, not a
disagreement.

### (2) Bucketing

**QMF-seam.** This is purely which enum lives in which record. Book mode is a field of the
Book-mode record (CT-24); seat state is a field of the roster-seat record inside the Book
schema (GAP-0039, another cluster). Behavior — what benches a seat, when it resets — is node.

### (3) Recommended ruling

**Ratify the split as the old node code already had it:**

- **Book mode** enum in V1 = `{LIVE, PAPER}`. `STOOD_DOWN` stays reserved (no V1 semantics).
  `BENCHED` is **removed from the Book-mode enum entirely** — not reserved, removed, because
  leaving it reserved is what caused the overload.
- **Seat state** is a Bot-scoped field on the Book's roster seat. A benched seat **routes to
  the Book's paper target and behaves as paper** without writing any Book-mode change.
- Invariant, carried verbatim: *"A BENCHED bot does not change the book mode"*, and *"breaker
  auto-reset does not erase the bench event"* — the bench is an append-only fact even after
  the seat returns.

Alternatives weighed: (a) *keep one enum with a scope field* — rejected, it is exactly the
shared enum that produced the overload and it lets a bot-scoped write mutate a book-scoped
row; (b) *keep BENCHED reserved in Book mode "in case"* — rejected under AD-5/AD-16 (kinds are
addable later without cost, so reserving a name that means something else in a neighbouring
record buys nothing and costs the ambiguity).

Note the boundary: **what counts as a stop-out and what B=2 means are not this cluster's**
(GAP-0045 / the breaker cluster). This ruling only fixes *where the state lives* and *that a
benched seat routes to paper*; it deliberately says nothing about the counter.

### (4) What would change it

A Book-level bench concept genuinely being wanted (an entire Book stood down but not in
paper) — in which case it needs its own name and its own semantics, not the seat's word.

---

## Cross-cluster dependencies I am not ruling

| Depends on | Owned by | Effect on this cluster |
| --- | --- | --- |
| Book↔venue/account cardinality (P-4) | Book/BMS schema cluster | PM-3's single paper target becomes per-venue-scope if a Book may span venues |
| PE-7 open-position fate at boundaries | position-safety cluster | PM-7's transition record gains a position-disposition field; authority is unaffected |
| Stop-out taxonomy / B=2 (GAP-0045) | breaker cluster | PM-9 fixes where the seat state lives; the counter's meaning stays open |
| Performance-result container (A-2) | metrics/result cluster | PM-5's `cohort_key` must land on that container; if it is never minted, PM-5 has nowhere to live |
| Operator-minted instrument equivalence (P-1) | registry sitting | one cohort-key part is unbuildable until it exists |

## Summary: what QMF carries out of this cluster

- **Records:** account binding with a dated `paper_routing_target` (AD-9/AD-26); CT-24
  Book-mode transition record with an addable `trigger_kind` and an authorizing-evidence
  reference; suppression annotation on `decision` journal events.
- **Label fields:** `active_controls` (identity-bearing) on the AD-12 result label;
  `cohort_key` on the performance-result kind.
- **Refusals:** paper transition with no resolvable routing target (`unavailable
  dependency`); cross-cohort decay judgment (`policy rejection`); book-mode write of a
  seat-scoped value (`invalid input`).
- **Read rules:** current Book mode is a fold over the transition stream; a decay cohort read
  is a permitted cross-role read within `world = live`.
- **Nothing else.** No mode machine, no routing table, no trigger logic, no sequencer
  instance, no control implementation — all node.

---

## Operator questions

Recommendation first, each answerable yes/no or by short choice. Seven questions; the first
two are fast confirmations, the rest are real forks.

**Q1 — Book-level paper mode.** *Recommend: yes.* We wrote down that paper is a Book-level
thing — when a Book can't trade live, the whole Book switches to a paper account, and bots
never run a live copy and a paper copy side by side. The exact transcript line got lost in
an export, but the same ruling is written in your own session notes from that evening. Can we
mark it confirmed and stop treating it as provisional?
→ **yes / no**

**Q2 — What paper is for.** *Recommend: standing state.* Two versions of paper are on record.
The narrow one: paper only happens after two specific failures. The wide one, which is your
own dictation: bots paper-trade whenever something stops them trading live — kill switch,
daily limit hit, prop-firm rule — and results keep being recorded the whole time, so
alpha-decay sensing never loses data points. Which one is the rule?
→ **standing state (recommended) / only after a failure**

**Q3 — Paper money and paper's reward.** *Recommend: yes to both.* Paper money stays frozen —
paper profits are evidence only, never real money, never touch the Treasury. And paper
results never earn a bot or Book its way back into live; coming back to live is either a
mechanical boundary (next morning, next cycle) or your signature. Confirm both?
→ **yes / no**

**Q4 — One paper account per live account.** *Recommend: exactly one at a time.* You'll have
several demo accounts. But each live account should point at exactly **one** demo account as
its paper destination at any moment — you can re-point it whenever you like, and the change
is dated and recorded. The reason for insisting on one: two possible destinations is how you
get an order fired twice. Agree?
→ **yes / no**

**Q5 — Keep trading paper through a news block.** *Recommend: yes, with a tag.* The old
written rule says a news window blocks live AND paper. Your later ruling says bots keep
running in paper while a pair is blocked, so decay data keeps flowing. I recommend your
version — and that every record made during a block is stamped with what was blocking it, so
you can later look at "clean" data and "blocked" data separately instead of mixing them.
→ **yes, keep paper running and tag it (recommended) / no, block paper too**

**Q6 — How we judge paper against live.** *Recommend: judge the decisions, not the cash, and
refuse mismatched comparisons.* A demo account fills at different prices than a live one, so
comparing money would report bad fills as a dying strategy. I recommend the system compares
decision quality in risk units (R) — the same feed, same indicators, same calendar on both
sides — and flat-out **refuses** to produce a decay verdict when the two streams don't match
on those things, rather than quietly averaging them.
→ **yes / no — and if no: flag instead of refuse?**

**Q7 — "Benched" belongs to the bot's seat, not the Book.** *Recommend: yes.* The word
"benched" is currently used for two different things — a Book's mode and a single bot's seat
on the roster. I recommend it means only the bot's seat: a benched bot trades on the paper
account and the Book itself stays LIVE. Book modes become just LIVE and PAPER. (This does not
touch what counts as a stop-out or the "2 strikes" number — that's a separate sitting item.)
→ **yes / no**
