---
cluster: exit-ownership
gaps: [GAP-0040, DEC-0067]
touches: [GAP-0039, GAP-0044, GAP-0045, GAP-0046, PE-3, PE-6, PE-7, PE-8]
five-hats: [A-8, A-7, A-2, T-4, T-6, D-1]
date: 2026-08-20
status: decision-brief — recommendations for operator ratification, nothing ruled here
precedence applied: current QMX rulings > old wiki (2026-07 planning delta) > GitBook baseline > QMX-discussion (oldest vault)
---

# Decision brief — exit ownership (GAP-0040 / DEC-0067)

## The shape of the problem, stated once

"Who owns exits" reads like one question and is actually three, and every corpus layer answers a
different subset of the three while using the same words. The three are:

1. **Exit policy authority** — who declares what exit rules a position lives under (stop form,
   target form, whether stops may move, when a position is force-flattened).
2. **Exit signal generation** — who is allowed to say *"this particular trade's thesis is dead,
   get out now"* (the thing the operator himself calls **fast invalidation**,
   `tracker/tickets/002-qmf-minimal-core.md:43`; PRD PE-6 `prd.md:575` names "fast invalidation
   primary vs hybrid with dynamic SL/TP" as the open per-Book exit-policy *shape*).
3. **Exit execution** — who physically sends the close/amend to the venue.

Number 3 is already closed by ratified spine: the adapter executes `close_position` /
`close_all` mechanically and **never initiates** them (AD-27, spine `:276`). Numbers 1 and 2 are
DEC-0067. Reading the corpus as a binary "bots own exits vs Book owns exits" is what has kept this
conflict alive for a month — the layers do not actually disagree about 1, they disagree about 2.

---

## Item E-1 — Exit ownership itself (the DEC-0067 ruling)

### 1. What the evidence layers say, precedence applied

**Layer 1 — current QMX rulings (highest).** Already directional and already operator-spoken:

- Ratified vocabulary, operator, 2026-08-17/18: *"Confluence = Level(s)+Trigger(s)+Confirmation(s),
  multi-variant and nesting, **no Exit — Exit/sizing/risk are Book territory**"* (`tracker/map.md:41`;
  restated `tracker/map.md:56`, `tracker/tickets/003-bot-schema.md:12`).
- Recovery addendum captures the same operator vocabulary: *"a confluence contains no exit; exits,
  sizing, and risk are Book territory"* — and explicitly demotes the GitBook wording:
  *"GitBook's older 'bot owns exit organs' wording is historical tension, not the current QMF
  authoring rule"* (ADDENDUM:153, :69; extract-local-recovery Topic 6).
- Ratified spine AD-17: *"**Exits are Book/risk/node territory.**"* (spine `:167`).
- But the current `docs/` corpus refuses to treat the question as closed: *"Exit ownership remains
  the DEC-0067 conflict"* (`docs/decisions/ADR-0008-book-and-risk-boundary.md:35`); FM-2 *"A request
  depends on unresolved exit ownership. No exit policy may be inferred or routed"*
  (`docs/components/qmf-risk.md:106`); `GAP(GAP-0040): Resolve whether Book owns every exit policy
  **or mediates ordinary Bot exits**` (`docs/components/qmf-risk.md:73`). CT-22 and CT-23 both carry
  `conflicts: [DEC-0067]`.

The gap text itself is the tell: the two live options were never "Book vs Bot", they were
**"Book owns every exit policy"** vs **"Book mediates ordinary Bot exits."**

**Layer 2 — old wiki / 2026-07 planning delta.** *"Dynamic SL/TP belongs in the book grammar, with
BMS as configuration authority"* and *"Stop-policy grammar belongs to the book's money rules. The
template defines permitted rule forms, each book instance owns its registry/formula-backed values,
BMS governs configuration, and enforcement crosses the adapter boundary"*
(`topics/position-safety-and-sltp-authority.md:16,71`; TND-DELTA:88 / K-35). A **globally uniform
stop service is rejected** (TND-DELTA:188 / D-07, legacy DEC-0024). The same wiki still carries the
inherited constitution line *"The bot owns market-facing entry and exit organs"*
(`system/invariants.md:39`) without reconciling it — the wiki is internally split.

**Layer 3 — GitBook baseline.** The single source of the "bots own exits" position, twice, verbatim:
*"A bot owns entry logic and exit organs while book infrastructure owns admission and sizing.
DEC-0002"* (glossary, live site + capture); *"The bot owns market-facing entry and exit organs. The
book owns admission, sizing, doors, leash, and profile selection"* (system-constitution). Its
forced-exit half is unambiguously Book-side: the leash chain *"escalates through ambient governor,
day closure, bench-to-paper, chorus flag, kill-line stand-down, classed kill switch, and hold-time
force-flat. DEC-0037"* (`components/book-template.md:30`). GitBook never says what an "exit organ"
*is*: a whole-corpus grep for `stop loss|take profit|SL|TP|invalidat|position-safety` returns
nothing (extract-gitbook-capture Topic 6:200). The live site confirms: *"Dynamic SL/TP — who moves
stops, when: not documented anywhere on the live site — not found"* (extract-live-gitbook `:276`).

**Layer 4 — QMX-discussion (oldest vault).** Says the **opposite of GitBook**: *"Individual strategy
instances do not own, compute, or amend their own stops; they publish a trade intent that includes
the original stop and target distances, then relinquish control"*
(`02-Components/03-execution-safety-and-asymmetric-sl-tp.md:11`; `sltp-authority-spec.md:21-26`).
Its reason for taking exits away from bots was *"one consistent asymmetric policy; uniform
kill-switch overrides with no per-bot wiring; losers reach their FULL original stop to feed clean
loss signals downstream."* Two of those three rationales survive; the "uniform policy" one is dead
(D-07).

**The honest weighing.** The "bots own exits" answer rests on **exactly one layer** (GitBook,
third of four), is **contradicted by the layer below it** (the oldest vault says bots must
relinquish stops), is **not adopted by the current corpus** (DEC-0067 recorded as a conflict rather
than an inheritance), and is **explicitly demoted by an operator ruling** (ADDENDUM:153). It is not
a long tradition — it is one sentence that survived a copy-paste. Meanwhile the clash report's own
verdict on the receiving system is that this is a hole, not a design: *"the new system has NO
stop-management component — and that absence is not neutral. The book's money math silently assumes
answers about stop behavior in at least three load-bearing places"*
(`clash-report-sltp-vs-book.md:6-10`).

**But the counter-case is real and must not be waved away.** If the Book owns *every* exit
including the discretionary one, then either:

- the Book must contain strategy logic — which violates CT-22's own ratified invariant *"Book and
  BMS express risk and money-management semantics, **not trading-entry logic**"*
  (`docs/contracts/ct-22-book-charter.yaml:34`) and ADR-0008's context line about not collapsing
  entry logic and exit behavior into one thing; or
- strategy-driven exits simply do not exist in QMX — which deletes **fast invalidation**, a
  mechanism the operator named himself as one of the three things that make exits "a whole world",
  and boxes in every strategy family whose edge lives in the exit (DEC-0011 don't-box-in;
  extensibility is the paramount design driver, `tracker/map.md`).

Both branches of a pure binary are wrong. The gap text's second option — **Book mediates ordinary
Bot exits** — is the one the evidence actually supports.

### 2. Bucketing proposal — **both**

- **Re-buckets to the node:** all *runtime* exit behavior. Evaluating a bot's exit signal, running
  the Book's stop policy tick by tick, deciding when hold-time force-flat fires, ordering competing
  authorities on one tick. This is the 2026-08-19 framework-vs-node ruling applied verbatim
  (`tracker/map.md:30`: dynamic SL/TP + Book runtime = node).
- **Stays QMF, as two named seams:**
  1. **The exit-policy declaration** — a fingerprint-bearing block inside the Book-type schema
     (CT-22's territory), declaring *which exit rule forms this Book permits*, with values
     registry-owned per Book instance. QMF owns the grammar and its identity; QMF picks no policy.
  2. **The exit-intent envelope** — a new risk-side contract (id minted by the sitting), the exact
     mirror of the ratified entry envelope CT-BOOK-01, carrying a bot's *request* to exit and a
     typed refusal path. See E-2.

Rationale for keeping the declaration in QMF rather than pushing it wholly to the node: PE-8
requires the **stop-policy version to pin into the exam certificate** (`BT-RECOVERED:124 INV-09`,
O-08:368) — a stop-policy change must invalidate a certificate the way a labeler-version change
does (L10). A thing that must enter a certificate's identity must be a fingerprint-bearing QMF
artifact (AD-10, AD-12). If exit policy lives only as node configuration, certification silently
stops meaning anything.

### 3. Recommended ruling

> **The Book owns exit policy. A Bot may propose an exit; the Book admits or refuses it through a
> door, exactly as it does an entry intent. A Bot never touches a stop, never amends, never closes.**

Concretely, the three-way split:

| Concern | Owner | Where |
| --- | --- | --- |
| Which exit rule forms are legal for this Book | **Book type** (grammar) + **Book instance** (values) | QMF: CT-22 schema block, registry-owned values |
| Which exit rule form this Book actually runs | **Book instance**, BMS as configuration authority | node runtime |
| "This trade's thesis is dead" (fast invalidation) | **Bot** — as a typed *intent*, never an action | QMF: exit-intent envelope; node evaluates |
| Protective stop attached at entry, and any movement of it | **Book policy** | node runtime; QMF owns the order-parameter vocabulary (AD-27) |
| Forced exits — kill-line stand-down, KSA effects, hold-time force-flat, news, boundary flatten | **Book / BMS / KSA**, adapter-enforced | node; QMF owns the four-command vocabulary + typed scope (AD-27) |
| Physically sending the close | **Adapter**, mechanically, never self-initiated | AD-27, already ratified |

**The binding law that makes bot exit signals safe** — and the single sentence that lets the
operator say yes without reopening anything:

> **An exit intent may only reduce risk.** It may close, or reduce, or ask the Book to tighten a
> protective stop toward entry. It may never widen a stop, extend a target beyond the Book's
> declared envelope, re-open, or increase size. Anything else is a `policy rejection` typed refusal
> (AD-11) that signs the veto ledger.

This is the surviving half of the old vault's own conservative fail-safe — *"when in doubt, do not
widen risk"* (`sltp-authority-spec.md:96-102`, listed among what **survives** at
`clash-report-sltp-vs-book.md:85-89`) — promoted from a failure-mode note to the constitutional rule
that separates a bot's *market read* from a bot's *risk authority*.

**Alternatives weighed:**

- **(a) Book owns every exit; bots emit nothing after entry.** Cleanest money math — R stays exactly
  entry-to-original-stop, Lbar stays comparable across bots, the breaker's stop-out counter has one
  producer. Rejected because it deletes fast invalidation, forces strategy logic into the Book (a
  CT-22 invariant violation), and is the maximal boxing-in of an operator whose paramount driver is
  extensibility. If the sitting later discovers the mediation path is too expensive to build in V1,
  this is the correct fallback — and E-2's envelope is designed so falling back costs nothing
  (a Book simply declares zero permitted bot-exit intent kinds).
- **(b) GitBook literal: bots own exit organs outright.** Rejected. It makes R's denominator
  bot-mutable, so `Lbar` (`scalper_mean_loss_r`, *measured per bot at exam*) stops being comparable
  across bots and across exam-vs-live, and every exam certificate's `mean_loss_r` /
  `breaker_expectation` becomes a claim about a policy the bot can change afterwards
  (CT-EXAM-01 fields, GITBOOK-BASE:282-292). It also adds a fifth uncoordinated arm to the
  already-unresolved same-tick race (GAP-0046). One layer supports it; three do not.
- **(c) Old-vault revival: one system-owned SL/TP authority for all Books.** Dead twice over —
  legacy DEC-0024 and DROP D-07 *"globally uniform stop service is rejected"* (TND-DELTA:188).
  Its *mechanics* (one-shot BE at +1R, continuous TP trail) are separately on the do-not-inherit
  list (`BT-RECOVERED:250-261`, :397). Recorded here only so nobody re-imports it as "the recovered
  design."
- **(d) Recommended: Book owns policy, Bot proposes, risk-reducing-only.** Preserves every strategy
  family, keeps R and Lbar single-authored (because the *stop* stays Book-owned even when the *exit*
  is bot-requested), and reuses a door pattern the operator has already ratified on the entry side.

### 4. What would change it

- If the operator says he does **not** want fast invalidation or any strategy-driven exit, collapse
  to alternative (a) immediately — the mediation machinery is then pure cost.
- If the same-tick priority ruling (GAP-0046, another cluster) cannot give the bot exit intent a
  deterministic rank below every protection authority, the intent path must be deferred rather than
  shipped half-ordered.
- If the sitting rules Book-to-venue cardinality as multi-venue (five-hats P-4 / X-5), "the same
  tick" stops being definable across venues and the intent path needs a per-venue-scope
  qualification before it is safe.

---

## Item E-2 — What QMF actually carries: the exit-intent envelope

### 1. Evidence

There is no exit-side contract anywhere in any layer. The entry side has one, ratified and
field-complete — CT-BOOK-01: `book_id, bot_id, pair, side (BUY|SELL), requested_r,
footprint_version, snapshot_version, timestamp_utc`, with the boundary law *"The bot proposes
intent; the book owns doors and sizing and does not let the intent bypass them"*
(`contracts/ct-book-01-trade-intent-envelope.md:22-32,18`). The exit side has only absence:
*"who sets the stop, who may move it, whether TP trails, whether breakeven moves exist... The words
'stop-loss' and 'take-profit' do not appear as owned behavior in any component page"*
(`clash-report-sltp-vs-book.md:29-32`). Current corpus: CT-22 and CT-23 are `wiring_status:
reserved-unwired`, `caller_status: unassigned`, every field `null` under GAP-0039/0044.

### 2. Bucketing — **stays QMF (seam)**

The envelope is a contract shape on qmf-core nouns. Its evaluation is node runtime. No new
inter-library edge is required (see the D-1 note at the end).

### 3. Recommended shape

A new risk-side contract, minted by this sitting, mirroring CT-BOOK-01:

| Field | Notes |
| --- | --- |
| `book_id`, `bot_id` | as CT-BOOK-01 |
| `position_ref` | the position the intent concerns — a fingerprint reference, never a venue-native id alone (AD-27's identity discipline) |
| `intent_kind` | enum, **addable never redefined** (AD-5/AD-16): `close_full`, `close_partial`, `tighten_protective_stop`. Nothing else in V1. |
| `requested_reduction` | for `close_partial`; expressed in the Book's declared unit, exact-integer (AD-7) |
| `reason_code` | typed, versioned per Book type — this is the evidence half of fast invalidation |
| `footprint_version`, `snapshot_version` | which certified envelope and which sensed snapshot produced the read — same provenance discipline as the entry envelope |
| `timestamp_utc` | int64 UTC ns per AD-8 |

Four laws on the contract:

1. **Risk-monotonic:** every `intent_kind` is risk-reducing by construction; a widening kind may
   never be added under AD-5's "addable never redefined" without an explicit operator mint.
2. **Proposal, never action:** the envelope authorizes nothing. The Book evaluates it as a door;
   the outcome is an admitted Book-side action or a typed refusal (AD-11), and **every refusal is
   journal-bearing** — the veto-ledger culture (L11; every entry refusal already emits CT-BMS-05).
3. **Never the stop's author:** a `tighten_protective_stop` intent names a *direction and a bound*,
   not a price the bot computed. The Book's policy resolves it to an actual level. This is what
   keeps R single-authored.
4. **Declarable-empty:** a Book type may declare zero permitted `intent_kind`s. That is the fallback
   to alternative (a) at zero cost, and it is also the honest V1 default for any Book whose exit
   policy is purely static.

Companion QMF surface, inside the Book-type schema (CT-22): an **exit-policy declaration** block —
permitted rule forms, permitted bot intent kinds, whether stop movement is permitted at all — that
is fingerprint-bearing so PE-8's certificate pinning is possible. Values stay registry-owned per
Book instance, matching the ratified never-inline discipline
(`standards/ct-book-03-book-type-schema.json:196-217`).

### 4. What would change it

If the sitting rules that stop-out taxonomy (PE-3) counts bot-requested closes as stop-outs, the
envelope needs a field carrying that classification at intent time rather than leaving it to a
downstream fold. Flagged as a live dependency on the stop-out cluster, not resolved here.

---

## Item E-3 — Who may move a stop (the position-safety half)

### 1. Evidence, precedence applied

Three of four layers agree the bot does not move stops, for three different reasons:

- **Oldest vault (explicit):** *"Bots do not own, compute, or amend stops — they publish intent,
  then relinquish control"* (`sltp-authority-spec.md:21-26`). Its contract made the point
  structurally: `AmendInstruction.source: "sltp_authority"` — **always; never the bot**
  (`sltp-authority-spec.md:52-66`).
- **Old wiki (placement ruling):** stop-policy grammar is the Book's money rules; BMS is the
  configuration authority; enforcement crosses the adapter boundary
  (`position-safety-and-sltp-authority.md:71`; TND-DELTA:88). But *"the bot relinquishes stop
  control after entry; some runtime subcomponent computes post-entry amendments under the book
  policy — WHICH ONE is undefined"* (`:87`).
- **Current rulings:** exits/sizing/risk are Book territory (`tracker/map.md:41`, AD-17).
- **GitBook** is silent on stops entirely — it never claims bots move them.

The load-bearing reason, stated in the corpus rather than invented here: **R is defined by the
original stop.** *"`1R` price distance is entry to the original protective stop... a full
original-stop loss is `-1R`; breakeven is `0R`"* (ADDENDUM:110-116), and the current corpus ratifies
R as `registry:original_risk_unit`, *"exactly one unit of original pre-trade risk; it is not profit,
equity, or post-trade return"* (`docs/registry/variables.yaml:427-436`, DEC-0076). If a bot may move
its own stop, R's denominator is bot-mutable, `Lbar` stops being comparable across bots and between
exam and live, and the breaker's consecutive-stop-out counter counts events of varying size.

### 2. Bucketing — **re-buckets to node**; QMF carries three things

- The **order-parameter vocabulary** — already ratified and already QMF-owned: *"Order-parameter
  vocabulary (order type: market | limit | stop | stop-limit; time-in-force; **protective-stop
  attachment**) is QMF-owned, addable never redefined; each adapter declares its supported subset in
  CT-18"* (AD-27, spine `:271`).
- The **risk-monotonic law** as a contract invariant on whatever amend surface exists (E-4).
- The **exit-policy declaration**'s fingerprint (E-2), so certificates can pin it (PE-8).

Everything else — the actual policy, the tick loop, the thresholds — is node.

### 3. Recommended ruling

> **The protective stop attached at entry is Book-owned for the life of the position. Only Book
> policy or a protection authority may move it, and only toward entry (risk-reducing). A Bot never
> amends a stop; its only stop-adjacent power is the `tighten_protective_stop` intent of E-2, which
> names a direction, never a price.**

**Explicitly not recommended, and named so it is not re-imported by accident:** the old asymmetric
policy (one-shot SL to breakeven at +1R, never reset; continuous TP trailing on continuation
probability). It is verbatim-recoverable (`sltp-authority-spec.md:28-48`) and it is on the
do-not-inherit list — *"do NOT inherit old `BE at +1R`, old SL/TP service, old kill-check
ordering"* (`BT-RECOVERED:250-261`, :397). QMX should ship a Book-type grammar wide enough to
*express* such a policy, and ratify **no** policy here. That respects AD-13's no-invented-numbers
standing and leaves the choice to the Book that carries the money.

**Alternatives weighed:** allowing bot stop authority for "advanced" Books only — rejected, because
a per-Book exception to R's definition makes cross-Book comparison of `Lbar` meaningless and quietly
re-creates the uniform-vs-per-book mess that D-07 just cleaned up. Allowing bots to move stops but
excluding those positions from exam-comparable evidence — rejected as a fiction generator: the
evidence you exclude is exactly the evidence alpha-decay sensing needs (five-hats A-1).

### 4. What would change it

If the stop-out cluster rules that R is re-based at any point in a position's life (e.g. after a
breakeven move), this item must be rewritten — R's definition and stop authority are one ruling
wearing two names. Coordinate before either is finalized.

---

## Item E-4 — The `amend_order` collision (this is the sharpest concrete finding)

### 1. Evidence

The command vocabulary is ratified as **exactly four**: *"Command vocabulary is exactly four
kinds — `place_order`, `cancel_order`, `close_position`, `close_all`... Kinds are addable never
redefined; **`amend_order` arrives only by explicit later mint, never through a payload**"*
(AD-27, spine `:271`). The node corpus says the same and adds the prohibition:
amend/partial-close *"are excluded from the contract; may not be smuggled through the payload"*
(K-44 REOPEN; order-path study `:53`).

But dynamic SL/TP **requires** an amend. The old planning corpus recorded the collision plainly:
*"dynamic SL/TP requires an amend command; CT-ADAPTER-01 has no amend (place/cancel/close/close_all
only). Operator ruled a fifth `amend_order` command; platform capability CONFIRMED (cTrader supports
SL/TP amend incl. server-side trailing). Ratification of `amend_order` into CT-ADAPTER-01 is
deferred"* — and its adversarial review flagged the two ruled requirements as
**"mutually exclusive as written"** (extract-old-planning Topic 6 `:165`, citing PRD FR-31 / PE-6 and
`review-adversarial-general.md:50-51`). The wiki confirms feasibility and the contract gap together:
*"CT-ADAPTER-01 currently permits `place_order, cancel_order, close_position, close_all`; it does NOT
register position amendments; `amend_order` pending explicit ratification, may not be hidden in
`payload`"* + *"cTrader amend-SL/TP feasibility confirmed"*
(`position-safety-and-sltp-authority.md:41`).

So: **if the Book's exit-policy grammar is allowed to require stop movement, the venue contract as
ratified last night cannot execute it.** Nobody has to reopen AD-27 to fix this — AD-27 wrote the
door itself ("addable never redefined... explicit later mint") — but somebody has to walk through
it, deliberately.

### 2. Bucketing — **stays QMF (seam)**

The mint is a `qmf-venue` CT-19 act, requested by the risk sitting. Nothing about it is node
behavior; the node decides *when* to amend, QMF decides *whether the shape exists*.

### 3. Recommended ruling

> **Raise a mint request for a fifth CT-19 command kind, `amend_order`, typed per kind on qmf-core
> nouns (protective-stop level and/or target level, exact prices per AD-7), constrained at contract
> level to risk-non-increasing amendments; CT-18 declares support; an unsupported amend is an
> `unsupported capability` refusal and is NEVER emulated by cancel-then-place.** And simultaneously:
> **V1 Book types may legally declare "static protective stop only", so nothing forces the amend
> path into the first build.**

Alternatives weighed:

- **(b) No amend at all in V1 — static protective stop set at entry, exits by `close_position` only.**
  Genuinely attractive: it keeps R exact, keeps the breaker countable, needs no venue-contract
  change, and is the smallest safe thing. Its cost is that "dynamic SL/TP" — a mechanism the
  operator names as one of the three pillars of the exit world — is unbuildable, and the Book-type
  grammar would have to be widened later, which is a format-version mint on a schema that will by
  then have live instances. Recommended as the **default posture**, not as the ruling.
- **(c) Delegate stop movement to the venue's own server-side trailing stop, declared in CT-18.**
  Rejected as the primary path: behavior then differs per broker, is not reproducible in replay, and
  the state changes arrive as venue events QMX did not author — colliding with AD-28's
  verify-or-refuse posture and *"adapters never synthesize venue observations."* Legitimate as an
  optional declared capability a Book may opt into, never as the mechanism the design assumes.
- **(d) Emulate amend as cancel + place.** Rejected outright. It opens a window where the position is
  naked, and it is the exact sin AD-27 already forbids for scopes: *"an unsupported scope is an
  `unsupported capability` refusal, never emulated at a wider scope."*

### 4. What would change it

If the venue sitting's CT-18 work finds that amend semantics differ enough across the venue families
QMX must eventually carry (cTrader now, CCXT-class crypto later) that one command kind cannot hold
them, the mint should be deferred and posture (b) becomes the V1 ruling rather than the default.

---

## Item E-5 — P&L attribution (five-hats A-8, ruled in the same breath)

### 1. Evidence

Nothing in any layer states an attribution convention. The five-hats sweep names the consequence:
*"if the Bot chose entry and the Book chose exit, per-Bot P&L is a convention, not a fact. The risk
sitting should state the attribution convention in the same breath as the exit ruling, or every
performance report the analyst produces carries an undeclared one"* (five-hats A-8).

Three ratified constraints bound the answer:

- **No fiction.** The exam gates on *"the edge is real after costs, and the candidate is not
  fiction"* (legacy DEC-0036); AD-13 forbids invented numbers. Any attribution scheme that splits a
  trade's result between Bot and Book requires a counterfactual — "what would the bot's own exit have
  returned" — which is fabricated evidence.
- **Comparability is the whole point of the paper-mode design.** Paper/demo runs are `world = live`
  *so paper and live performance stay comparable for alpha-decay sensing* (AD-12, AD-17, DEC-0115).
  An attribution convention that changes when a Book's exit policy changes destroys exactly that.
- **The journal already has the right event types.** Seven ratified types including `fill` and
  `risk transition` (AD-21); five-hats A-7 asks for suppression typed as a first-class journal event
  carrying the suppressing authority and reason.

### 2. Bucketing — **both**

QMF carries the **record shape** (the `exit_cause` enum as contract surface on the closing
observation/journal event, and the attribution field on the performance-result container five-hats
A-2 asks the sitting to mint). The node produces the values.

### 3. Recommended ruling

> **1. Whole-trade attribution, no splitting.** The full realized result of a position, in R,
> belongs to the Bot that opened it — regardless of who closed it. No counterfactual, no
> apportionment between Bot and Book.
>
> **2. Every close carries a typed `exit_cause`,** declared as contract surface, addable never
> redefined (AD-5/AD-16), initial set: `bot_intent` · `book_policy_stop` · `book_policy_target` ·
> `hold_time_force_flat` · `kill_switch_effect` · `news_window` · `boundary_flatten` ·
> `venue_initiated` (the broker's own stop-out class, `isServerEvent`) · `operator`.
>
> **3. Therefore every report is partitionable by cause without a second attribution scheme.**
> "The bot's edge" and "what our own gates did to it" are the same dataset read two ways — which is
> precisely the counterfactual five-hats A-7 says separates real decay from self-inflicted decay.

Alternative weighed: **split attribution** — credit the Bot with the P&L up to the point the Book
intervened, and the Book with the remainder. Rejected: it requires pricing a counterfactual exit,
it makes per-Bot P&L a function of Book policy version (so a policy change silently rewrites
history — an AD-5 violation in spirit), and it gives the operator two numbers where he needs one.
The `exit_cause` partition delivers everything split attribution was reaching for, out of recorded
fact rather than simulation.

Note the free dividend: **`exit_cause` is the substrate the stop-out taxonomy (PE-3) needs.**
Whoever rules "does a breakeven exit count toward the breaker" is ruling a *predicate over
`exit_cause` plus realized R* — which is a one-line rule once this typing exists, and an
unanswerable question without it. Handed over, not ruled here.

### 4. What would change it

If the sitting rules that a Book may hold positions opened by a Bot that has since been rebound or
retired, attribution needs a dated binding lookup rather than a bare `bot_id` — the AD-17 binding
record already supports this, but the performance-result container must cite the binding, not the
Bot alone.

---

## Handoffs this cluster creates (not ruled here)

| To | What |
| --- | --- |
| **Same-tick priority (GAP-0046)** | Bot exit intent becomes a **fifth arm** in the race alongside KSA effects, hold-time force-flat, broker-side stops, and normal amendments. Recommended rank: strictly last — below every protection authority and below Book policy. It is a proposal, so deferring it one tick is safe; deferring a kill switch is not. |
| **Stop-out taxonomy (PE-3 / GAP-0045)** | `exit_cause` (E-5) is the enabling typing. The breaker predicate should be written over `exit_cause` + realized R, never over the word "stop-out". |
| **Money ladder / R (GAP-0044)** | E-3's "stop is Book-owned for the life of the position" is what makes `Lbar` comparable at all. If R is re-based mid-position by any policy, both rulings move together. |
| **Position fate at boundaries (PE-7)** | `boundary_flatten` is reserved in the `exit_cause` enum so PE-7 can land later without a format-version mint. |
| **Backtesting / exam (PE-8)** | The exit-policy declaration must be fingerprint-bearing so a certificate can pin its version; a policy change must invalidate certificates the way a labeler change does (L10). |
| **Venue sitting (CT-18/CT-19)** | The `amend_order` mint request (E-4), plus a CT-18 declaration for venue-native trailing-stop support as an optional capability. |
| **Dead-zone item** | Whoever holds the ~45-min session-handover relax must state whether it touches **open positions** or only new entries. Recommended: entries only — a no-trade band that also force-flattens is a protection action wearing a scheduling name. |

**D-1 edge request (five-hats, mandatory close-out for every sitting):** **none required.** The
exit-intent envelope and the exit-policy declaration are defined by `qmf-risk` on `qmf-core` nouns;
evidence reaches registry and data through the application composition root under default-deny,
exactly as `docs/components/qmf-risk.md` already states for DEC-0120.

---

## Operator questions — three, recommendation first

Everything else in this brief is delegate-quality: it either follows mechanically from these three
answers, or it is a contract shape that mirrors something already ratified.

### Q1 — May a bot ask to get out of a trade? (this is DEC-0067)

**Recommendation: yes — a bot may *ask*, the Book decides.**

Plain words: the Book owns the rules about exits — the safety stop, the target, when the machine
force-closes everything. A bot can never move a stop or close a position itself. But a bot is the
only thing that can tell when its own read has died — that is your **fast invalidation**. So the bot
sends a request ("this trade's reason is gone, please close it"), and the Book either does it or
refuses and writes down why, exactly like it already does with entry requests. The one hard rule:
a bot's request can only ever make risk *smaller* — never wider stops, never bigger positions.

The alternative is the Book owning every exit outright. Cleaner arithmetic, but it deletes fast
invalidation and forces strategy thinking into the Book, which your own rule says the Book must not
contain.

**Answer: yes / no.**

### Q2 — Should we add a fifth broker command, `amend_order`?

**Recommendation: yes, add the shape now — but don't force any Book to use it in V1.**

Plain words: last night we ratified exactly four commands the system may send a broker: place,
cancel, close-one, close-all. There is no "move the stop." That means dynamic SL/TP — one of the
three exit mechanisms you named — is currently unbuildable. The spine already left the door open for
adding a fifth command later. I recommend walking through it now so the grammar exists, while
letting the first Books declare "static stop only" so nothing is forced into the first build. The
one thing we must never do is fake it by cancelling and re-placing — that leaves the position naked
for a moment.

**Answer: yes, add it now / no, keep four and ship static stops only in V1.**

### Q3 — When the bot opened the trade but the Book closed it, whose result is it?

**Recommendation: the whole trade belongs to the bot that opened it — and every close records *why*
it closed.**

Plain words: if we split the profit between "bot's part" and "Book's part", we have to invent what
the bot *would* have made, which is made-up evidence. Instead: one number, credited to the bot, plus
a label on every close saying what ended it (bot asked, stop hit, target hit, kill switch, news,
hold-time, broker's own stop-out, boundary, you). Then any report can be read two ways — "how the
bot performed" and "what our own safety gates cost us" — from the same recorded facts. Without this
label, every news blackout and kill-switch fire looks like the strategy dying.

**Answer: yes, one number plus a why-label / no, split it.**
