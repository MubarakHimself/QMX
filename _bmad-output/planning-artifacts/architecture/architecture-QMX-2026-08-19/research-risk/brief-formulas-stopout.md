---
sitting: QMX risk sitting (GAP-0039..0046)
cluster: formulas-stopout
scope: GAP-0044 (R with units, dimensional autopsy of FORM-0004/0006, three capital concepts, replacement SHAPE + dimensional tests) + GAP-0045 (stop-out as a typed risk event, un-overload B, un-overload BENCHED, decay evidence primitives only) + five-hats P-2/A-5, P-7, A-2, A-3
date: 2026-08-20
status: decision brief for operator ratification — proposes nothing numeric
---

# Decision brief — formulas & stop-out

## 0. How to read this

Thirteen decision items (**F-1 … F-13**). Each carries: what the evidence layers say with citations
and precedence applied → bucketing (stays QMF as a seam/contract, or re-buckets to the trading node)
→ recommended ruling with the alternatives weighed → what would change it. Operator questions are
collected in §14, recommendation first, each answerable yes/no or by a short choice.

**Precedence applied throughout** (as instructed): current Desktop/QMX rulings (`docs/`, `tracker/`,
the ratified spine AD-1..28) > old wiki (`Documents/QMX/wiki`) > GitBook capture/live > QMX-discussion
old vault. One refinement is on record and I use it: the recovery addendum's **`[OP-2026-08-17]`**
operator rulings sit *above* the old wiki, because the current corpus already adopted them where they
clashed — the addendum said "SQS means Spread Quality Sensor" (ADDENDUM:64) against the wiki's
"snapshot quality score" (`market-intelligence-service.md:46`), and the current corpus ratified the
addendum's version and retired the wiki's as an *incorrect expansion* (`docs/glossary.md:550-552`,
DEC-0074). The same addendum carries the only complete definition of R in any corpus. That lineage
matters for F-1.

**Standing constraints honoured.** No number in this brief is proposed for ratification (AD-13). The
DO-NOT-REVIVE list is respected: no DPR/PRS, no 0-100 scores, no T1/T2/T3 tiers, no slot auctions, no
global bot pools, no redemption/probation loops, no WF3 mechanics, no parallel Bot paper twins
(DEC-0069), no "house of money" in any form. Legacy values (S=500, K=200, n=5, B=2, b=2, Lbar=0.35R)
appear **only as unratified reference material** for the operator's re-understanding.

---

# PART A — GAP-0044: R, dimensions, capital, replacement shape

## F-1 — R is one relationship with three typed faces, and every formula must say which face it uses

### Evidence

**Current corpus (highest).** R is ratified, and ratified thin:

```yaml
- name: original_risk_unit
  symbol: R
  value: 1
  formula: null
  units: pre-trade-risk-unit
  type: ratio
  decision: DEC-0076
  configurable: false
  notes: "R is exactly one unit of original pre-trade risk; it is not profit, equity, or post-trade return."
```
(`docs/registry/variables.yaml:427-436`; restated `ADR-0010:31`, `docs/components/qmf-risk.md:49`,
`docs/glossary.md:344-346`.)

That entry does three useful things — it fixes the word *original*, the word *pre-trade*, and it
forecloses the three wrong readings (profit, equity, post-trade return). It does one harmful thing:
`units: pre-trade-risk-unit` is a self-referential unit and `type: ratio` names only one of R's faces.
A ratio of *what to what* is not stated anywhere in the current corpus.

**Operator-ruling layer (`[OP-2026-08-17]`, above the old wiki).** The complete definition survives
verbatim, and it is not a ratio — it is three quantities:

> "`1R` price distance is entry to the original protective stop; `1R` in pips is that distance divided
> by the instrument pip size; `1R` in cash is the loss if the original stop fills at the admitted
> quantity; a full original-stop loss is `-1R`; breakeven is `0R`; outcomes may be normalized as
> R-multiples." (ADDENDUM:110-116)

with the consequence stated in the next line: *"This makes `Lbar` intelligible as a dimensionless
average loss expressed in R-multiples."* (ADDENDUM:117).

**Old wiki / GitBook.** R appears only as a *unit tag* on fields — `requested_r` "Units: R"
(`contracts/ct-book-01-trade-intent-envelope.md:22-32`), `scalper_mean_loss_r` units `R`
(`registry/variables.md:19-25`), `oos_expectancy_floor_r = 0.15 R`. No definition anywhere.
**QMX-discussion (oldest).** Only the P&L ladder: "reversal to BE = **0R loss unit**; reversal to
original stop = **1R loss unit**" (`02-Components/03-execution-safety-and-asymmetric-sl-tp.md:28-34`),
and stop math done entirely in **pips** with a per-symbol `PipProfile` (`sltp-authority-spec.md:63-66`).

**Reading applied.** The current one-line registry entry is a *compression* of ADDENDUM:110-116, and
the compression is precisely what lost the units. DEC-0076 is not wrong; it is incomplete. Completing
it does not reopen it.

### Bucketing — **stays QMF**

R's faces are value types and one named conversion, which is exactly `qmf-core` territory under AD-7:
`PriceDelta(instrument, scale)` and the exact-rational type already exist (AD-7 bullet 6);
`Money(currency, scale)` already exists; AD-7 already requires "a named conversion boundary with an
explicitly stated rounding mode" for every crossing. QMF carries the three faces, the boundary, and
the refusal. The *policy* (where a Book puts its stop) is node territory and is not touched here.

### Recommended ruling

**R is not a number. R is a per-position relationship, fixed at admission, with three typed faces:**

| Face | Name | Type | Meaning |
|---|---|---|---|
| definition | `original_risk_distance` | `PriceDelta(instrument, scale)` | entry price → the position's declared original full-loss price |
| money | `original_risk_amount` | `Money(numeraire, scale)` | what a full-loss fill costs at the admitted quantity |
| outcome | `r_multiple` | exact rational, **dimensionless** | `realized_pnl ÷ original_risk_amount`; −1 = full original loss, 0 = breakeven |

Four invariants ride with it:

1. **Frozen at admission.** `original_risk_distance` and `original_risk_amount` are computed once, at
   admission, and never re-based — not by a stop move, not by a trailing amendment, not by an intraday
   budget re-derivation. This is the literal content of "*original* pre-trade risk" (DEC-0076) and it
   is what keeps `−1R` meaning "a full loss" so the breaker signal stays calibrated — the old design's
   own stated rationale (`sltp-authority-spec.md:190-192`, `02-Components/03-…:24-25`).
2. **Only `r_multiple` averages across instruments.** `Lbar` is an average of `r_multiple`s and is
   therefore dimensionless (ADDENDUM:117). Averaging `original_risk_amount` across instruments or
   accounts requires a numeraire (see F-5). Averaging `original_risk_distance` across instruments is
   never legal.
3. **Money ↔ R is a rate, never an equality.** The bridge object is `r_unit_price`
   [`Money` per `r_multiple`]. Every crossing names it. This is AD-7's named-boundary rule applied to
   R, and it is the single discipline that makes a second FORM-0006 impossible.
4. **Incomputable R is a refusal, never a default.** No declared original full-loss price → no
   `original_risk_distance` → `invalid input` refusal (AD-11) at admission. The legacy code already
   carried the weak version of this guard (`Lbar > 0` else unresolved, L-CODE `registry.py:395-436`).

The registry entry becomes three entries with real units, and DEC-0076's sentence survives as the
governing note on all three.

### Alternatives weighed

- **Leave R as the ratified one-liner and let each formula infer the face.** Rejected: that inference
  is exactly what produced FORM-0006 (F-2), and the current corpus has already had to kill a formula
  over it (DEC-0077).
- **Define R in money only** ("1R = X USD per trade"). Rejected: cross-instrument and cross-account
  comparison dies, and `Lbar`, `oos_expectancy_floor_r`, and every exam metric stop being comparable.
- **Define R in pips only** (the oldest vault's habit, `sltp-authority-spec.md:63-66`). Rejected: pips
  are a forex artifact; DEC-0015 says the nouns must not preclude stocks and crypto, and AD-7 makes
  `Quantity(unit)` deliberately opaque for the same reason.
- **Allow a re-based R after a stop move.** Rejected: it silently converts a −1R loss into a −0.4R
  loss and decalibrates every downstream count. Recorded here because the old asymmetric policy moved
  stops (`sltp-authority-spec.md:181-185`) and a future Book will want to again.

### What would change it

Evidence that the operator's own meaning of R is the *account-percentage* reading ("1R = 1% of
equity") rather than the entry-to-stop reading. Nothing in any of the nine dossiers says that, and
DEC-0076 explicitly says R "is not … equity", so I treat it as closed — but it is a one-question
check, and if it flipped, `original_risk_amount` would become a function of equity-at-admission and
would need a stated equity snapshot rule.

---

## F-2 — Dimensional autopsy of FORM-0004 and FORM-0006

### Evidence

**The formulas, verbatim and consistent across four corpora** (`registry/formulas.md:35,50`;
GITBOOK-BASE:134-140; live GitBook `registry/formulas`; L-CODE `registry_census.json:352-557`):

```
FORM-0001 cap_equity          C = cap_multiple * S
FORM-0002 runway              U = E - K
FORM-0003 daily_loss_budget   D = U / n                    "re-derived at rollover, drains intraday"
FORM-0004 offer_per_seat      offer_R_usd = D / (B * b * Lbar)
FORM-0005 take_per_seat       take_R_usd  = min(offer_R_usd, trust_bounded_cost_aware_kelly_R_usd)
FORM-0006 r_max_ceiling       R_max_usd  <= B * b * Lbar
FORM-0007 viability_floor     round_trip_cost_R / expected_edge_R <= v_cost
```

**Declared units of every symbol** (`registry/variables.md:19-25`; live GitBook variables table;
old-planning `book-template-registry-extraction.md:64-92`):

| Symbol | Declared units | Note |
|---|---|---|
| S, K, E, U, D | USD | money |
| n | count | "floor-trader discipline number" |
| **B** | `consecutive_stopouts` | a count of *loss events* |
| **b** | `ratio` | dimensionless; no rationale published anywhere |
| **Lbar** | `R` | `kind: measured`, per bot at exam; 0.35R is "a reference expectation only, never an inherited bot default" |
| v_cost | `fraction_of_R` | |

**The defect, on record in three layers.** `[LEGACY/OP]` ADDENDUM:119: *"`FORM-0006` compares
`R_max_usd` with `B * b * Lbar`, whose right side has no stated USD dimension. Do not implement or
normalize that formula until its intended relationship is explicitly repaired."* GitBook's own
tombstone T-12 (GITBOOK-BASE:425) and "FORM-0004's name itself mixes R and USD" (GITBOOK-BASE:427,
"do not silently normalize", TND-DELTA:172/C-20). Old-planning states it cleanly: *"the RHS
`B·b·Lbar = 2·2·0.35R = 1.4R` is in **R**, while the LHS is named `_usd`"* (old-planning:258).
**Current corpus (highest) closes it:** *"Implement recovered FORM-0006 — dead because it is
dimensionally invalid under the corrected meaning of R (DEC-0077)"* (`ADR-0010:25`); *"FORM-0006 is
dimensionally broken and must not be implemented"* (`docs/glossary.md:530-532`); FM-3 makes any payload
using it inadmissible (`qmf-risk.md:107`). **FORM-0004 was never killed** — it is simply *absent* from
the current corpus (`extract-local-current.md:313`: "FORM-0004, D/B/b/Lbar … not-found anywhere in
the current corpus").

### The autopsy (this is a derived reading, not corpus text — flagged as such)

Substituting the declared units:

```
B * b * Lbar  =  [loss events] × [dimensionless] × [R per loss event]  =  [R]
D / (B*b*Lbar) =  [USD] / [R]                                          =  [USD per R]
```

Three findings follow, and they are different findings:

1. **FORM-0004 is dimensionally *coherent* and *mis-named*.** It does not compute a money amount; it
   computes a **rate — the USD value of one R for this seat**. The name `offer_R_usd` reads as money,
   which is how the error propagated. The corpus's own worked checksum confirms the reading: SCN-0001
   gives S=500, K=200, n=5 → U=300, D=60 (`scn-0001:63`, PRD FR-1 `prd.md:114`); with the legacy
   B=2, b=2, Lbar=0.35R the divisor is 1.4R and the quotient is **$42.86 per R** — and $60 of daily
   budget is exactly 1.4R of permitted loss. The ladder is internally consistent. Its problem is
   naming, not arithmetic.
2. **FORM-0006 is genuinely broken, and only its `_usd` is broken.** `USD ≤ R` is a category error
   with no rate on either side — DEC-0077 is right. But the *relationship* underneath ("one seat may
   not ask for more R than the whole loss-run allowance") is a clean R-space inequality that survives
   translation. The dead thing is the formula; the live thing is the relationship. GAP-0044's own
   wording ("Replace dead FORM-0006 with dimensionally valid formulas") asks for exactly this.
3. **`b` recovers a meaning nobody wrote down.** Under the unit reading, `B × b × Lbar` is *"the depth
   in R of the losing run this seat is sized to survive"*, and `b` is the **safety multiple on the
   bench depth** — with the legacy values, "size so the daily budget covers twice the drawdown that
   would bench you." No corpus states this; it falls out of the units. It is offered for the operator's
   re-understanding, not as a ruling, and it invents no number.

Two secondary hazards the autopsy surfaces:

- **Intraday re-pricing.** FORM-0003's note says D "drains intraday" (`formulas.md:19-28`). If the rate
  is recomputed as D drains, one R is worth more at 09:00 than at 15:00 — which is harmless *only*
  because F-1 freezes R at admission. Without F-1's freeze, `r_multiple`s are not comparable within a
  single day. State the freeze or the ladder is not measurable.
- **E's composition is unstated.** Whether current equity `E` includes unrealized P&L on open positions
  is *not written anywhere* (old-planning:248, citing PE7-MEMO:189-190). Every rung above it inherits
  the ambiguity. This is PE-7-adjacent and belongs to the position-fate cluster, flagged here because
  it lands in *my* formulas.

### Bucketing — **both**

QMF carries the **dimensional law and its executable test suite** (F-4) plus the typed variable
declarations; the trading node carries the runtime that evaluates a Book's declared money rules. The
seam is worth stating precisely: QMF's job is to make it *impossible to declare* a second FORM-0006.

### Recommended ruling

Record the autopsy as the reason for the replacement, adopt the three findings as reading (not law),
and **keep FORM-0006 dead by name while re-expressing its relationship in R-space** (F-4). Do not
"repair" FORM-0004 in place; supersede it with a correctly-typed and correctly-*named* successor —
renaming in place would leave a live formula whose old name is still cited across four corpora.

### What would change it

If the operator's intent for `offer_R_usd` was ever "the dollars a seat may lose today" rather than
"what one R is worth to this seat", the whole ladder re-reads and the divisor's units change. The
SCN-0001 checksum argues against it, but the operator is the only authority on original intent.

---

## F-3 — The three capital concepts, and the typing that keeps them apart

### Evidence

**Current corpus (highest).** ADR-0010's decision line: *"roster state, risk allocation, and any
surviving legacy capital concept remain distinct"* (`ADR-0010:31`, DEC-0078) — and GAP-0044 restates
the requirement without enumerating: *"Replace dead FORM-0006 with dimensionally valid formulas and
distinct capital concepts"* (`qmf-risk.md:81`). The current corpus states the requirement and never
names the three.

**Operator-ruling layer** names them. ADDENDUM:122-131, "Three 'seat' concepts kept separate":
(1) **roster seat** = membership / bot-seat lifecycle in a Book; (2) **risk seat** = "the active Book
allocation to which `offer_R_usd` and `take_R_usd` apply"; (3) **legacy capital slot** = the donor
object carrying DPR auctions and house-money — `DROP` (ADDENDUM:68,129). Open sub-question recorded:
whether a risk seat has persistent identity or is derived from `(book, bot, cycle, allocation version)`
(ADDENDUM:131,195).

**Money-side distinctness, separately documented.** Virtual ledger equity vs broker equity vs frozen
paper balance (CT-BMS-03 `virtual_equity` / `broker_equity` / `explained_delta` / `verdict`,
`ct-bms-03:24-29`; frozen paper balance "never hand-adjusted", `ct-paper-01:30-35`; "paper gains are
not Treasury cash"). Plus the ladder's own set: seed S / kill-line K / cap C / equity E / runway U /
daily budget D / refund reserve (`treasury-desk.md:19-23`; GITBOOK-BASE:228-238).

### Bucketing — **stays QMF**

This is a type vocabulary, not a runtime. QMF declares the kinds and refuses the confusions; the node
runs the ledger.

### Recommended ruling

Ratify DEC-0078's trio by name — **roster state, risk allocation, capital** — and give each exactly
one type, because the type is what enforces the distinctness:

| Concept | Type | Lives on | Never |
|---|---|---|---|
| **Roster state** | a seat-state enum on the `(Book, Bot, binding)` record (F-9) | the AD-17 binding record | holds money, holds an allocation |
| **Risk allocation** | an exact-rational **`r_multiple`** — a *permission to lose*, dimensionless | a dated allocation record derived from `(Book, Bot, period, allocation version)` | is money |
| **Capital** | **`Money(numeraire, scale)`** — virtual ledger equity, broker equity, frozen paper balance, each its own record | Treasury / reconciliation / paper records | is a permission |

And the fourth object that makes the three usable without fusing them: **`r_unit_price`**, a
`Money`-per-`r_multiple` **rate** (F-1, F-4). The dead legacy capital slot is dead *precisely because
it fused a roster seat with a pot of money* — the typing is not decoration, it is the autopsy of why
that object had to die (DEC-0093, `qmf-risk.md:23-24`).

On the open sub-question: recommend **risk allocation is derived, not an identity** — it is
`(Book, Bot, period, allocation-version)` with a content fingerprint, not a minted noun. A minted
"seat" object is one rename away from being a slot again.

### Alternatives weighed

- **Two concepts (money and seat).** Rejected: it is the fusion that produced the slot machine.
- **Mint a first-class `RiskSeat` noun.** Weighed seriously — it makes exposure queries easy. Rejected
  for V1: AD-16 says kinds are addable, so it can be minted later with evidence, and minting it now
  re-creates the object DEC-0093 killed.

### What would change it

An operator statement that a risk allocation should be denominated in money rather than in R. That
would collapse the rate into the allocation and make cross-instrument comparison die (F-1 note 2).

---

## F-4 — Replacement formula SHAPE and the mandatory dimensional tests

### Evidence

GAP-0044 asks for a replacement (`qmf-risk.md:81`). No corpus supplies one — this is **fresh design**,
constrained by: AD-7 (exact money, named conversion boundaries, opaque `Quantity`), AD-13 (no invented
numbers), DEC-0105 (money path is scaled-integer, float banned), AD-11 (typed refusals), PE-4 (the
Kelly term stays unregistered so `take` stays visibly incomputable and is *never* defaulted to `offer`
— `prd.md:188`, SPINE:395, TND-DELTA:90).

### Bucketing — **both**

QMF carries the contract shape, the unit vocabulary, and the test suite. The node computes.

### Recommended ruling — the shape (units in brackets; **no values proposed**)

```
book_capital              [Money(numeraire)]        virtual ledger equity
loss_floor                [Money(numeraire)]        the line below which the Book stops trading live
loss_runway               [Money]      = book_capital − loss_floor
runway_periods            [count]                    how many such periods the runway must last
period_loss_budget        [Money]      = loss_runway ÷ runway_periods
                                        period named by an AD-8 day-boundary calendar (P-6's socket)

seat_loss_run_allowance   [r_multiple]               the depth, in R, of the losing run a seat is
                                                     sized to survive within one period — Book-declared.
                                                     A Book MAY declare it derived from
                                                     (bench_threshold [count] × safety_multiple [ratio]
                                                      × measured_mean_loss [r_multiple per loss]);
                                                     that derivation is declared data, never hardcoded.

r_unit_price              [Money per r_multiple]
                          = period_loss_budget ÷ seat_loss_run_allowance      ← supersedes FORM-0004

seat_r_ceiling            [r_multiple]  ≤ seat_loss_run_allowance             ← supersedes FORM-0006
                                                     (no money appears on either side)

position_risk_amount      [Money]      = requested_r [r_multiple] × r_unit_price   — frozen at admission
position_quantity         [Quantity(unit)]
                          = position_risk_amount ÷ (original_risk_distance [PriceDelta]
                                                    × instrument value-per-point [Money per PriceDelta])
                            crosses AD-7's named boundary with a declared rounding mode; refuses
                            (`unavailable dependency`) if AD-28 instrument metadata is absent

take                      = min(offer, bounded-Kelly)   Kelly term unregistered (PE-4) →
                                                        take stays incomputable, never defaulted
```

Every rung type-checks; every money↔R crossing names `r_unit_price`; nothing is a number.

### Recommended ruling — the mandatory dimensional tests (the "no second FORM-0006" gate)

Eight rules, all enforceable at declaration time, all shippable as AD-4 tier-2 contract tests:

1. **Closed unit-kind vocabulary**, addable never redefined (AD-5/AD-16):
   `money(currency) | price-delta(instrument) | quantity(unit) | r-multiple | rate(money-per-r) |
   count | dimensionless-ratio | duration | instant`.
2. **Every registry variable declares its unit-kind.** A null unit-kind is a refusal, not a default.
3. **Every formula declares the unit-kind of each input and of its output**; a symbolic checker derives
   the output kind and **refuses (`invalid input`) on mismatch**.
4. **FORM-0006 is the suite's canonical negative case**, kept as a permanent regression test: the
   checker must fail it. A dead formula that can still be *typed* is a dead formula that comes back.
5. **Addition, subtraction and comparison require identical unit-kinds** *and* identical currency /
   instrument tags (AD-7's no-implicit-rescale rule, extended to comparison).
6. **Any money ↔ r-multiple crossing must name a `rate` variable explicitly**; an implicit crossing
   refuses. This one rule alone would have caught both FORM-0004's mis-naming and FORM-0006's death.
7. **Money-path taint (AD-7 / DEC-0105).** Any formula whose output transitively reaches an order
   quantity, price, P&L or balance is money-path: exact rationals only, binary float refused.
8. **Every formula ships an executable worked checksum** in the SCN-0001 style, with the unit-kind
   asserted at each step — so the arithmetic and the units are proved by the same test.

Plus one aggregation rule bridging to F-5: **cross-instrument or cross-account aggregation of
`money` / `price-delta` requires a declared numeraire, rate source and knowledge time; aggregation of
`r-multiple` requires none.**

### Alternatives weighed

- **A units library at runtime (pint-class).** Rejected: AD-6 bans platform-imposing dependencies and
  `qmf-core` is zero-dependency; a declared unit-kind string plus a small symbolic checker is enough
  and keeps the check at *declaration* time where refusals are cheap.
- **Leave dimensions to code review.** Rejected on the evidence: FORM-0006 survived review in four
  corpora across roughly ten months before anyone wrote the defect down (ADDENDUM:119).
- **Repair FORM-0004/0006 in place and keep the IDs.** Rejected — see F-2.

### What would change it

A ruling that the money ladder itself is out of scope for this sitting and belongs to a later
Book-schema sitting. In that case F-4's *shape* defers, but rules 1–8 should still land now: they are
the reusable asset and they cost nothing to state early.

---

## F-5 — Numeraire, rate source, knowledge time (five-hats P-2 / A-5)

### Evidence

**Every corpus reports this absent.** Current corpus: no numeraire/base-currency concept anywhere; the
only adjacent fact is an equity-derivation note (`tracker/trading-node-notes.md:15`). Old wiki: *"This
entire topic is absent … record as a clean GAP"* (`extract-old-wiki.md:744`); all money is USD by
default, forex-only (`invariants.md:41`), reconciliation is per-`account_id` with no cross-account
roll-up (`ct-bms-03:24`), the multi-account load balancer is explicitly post-V1
(`connection-manager.md:44`). Recovery: *"cross-currency conversion remains unratified"* (BMAD-SUP:87),
*"must be freshly ratified"* (TND-DELTA:118 / K-54); cross-book cap authority is GAP-0008 (open).
L-STD is blunt: `cross_currency_conversion_in_scope = false`
(`standards/broker-equity-computation.json:50-63`).

**What the spine already supplies.** AD-7 gives `Money(currency, scale)`, bans implicit rescale, and
requires "a named conversion boundary with an explicitly stated rounding mode". AD-19 gives `source`
as a core provenance noun distinct from `VenueId` ("a provider you can trade at is a venue; a provider
you only read from is a source") and requires event-time + known-at + source + revision on every
external fact. So the *mechanism* is ratified and only the *policy* is missing — exactly as the
five-hats sweep says (P-2, A-5).

### Bucketing — **stays QMF**

Three declared fields on the Book charter contract plus one named conversion boundary. The rate *feed*
is a `source` under AD-19/AD-21 (data sitting). Enforcement is node.

### Recommended ruling

**The Book charter declares a numeraire, a rate source, and a knowledge-time rule** — the currency all
of that Book's money is counted in, which registered `source` supplies FX rates, and at which knowledge
time a rate is read (recommended: *the rate knowable at the evaluation instant*, mirroring AD-8's
causality discipline and AD-22's "as-of last value known at or before the evaluation instant"). A
converted figure is a **derived value with lineage across AD-7's named boundary**, never evidence.

**And for V1, fail closed:** binding a Book to an account whose currency differs from the Book's
declared numeraire is a **`policy rejection` refusal**, not a conversion. Reason: no rate source is
ratified, AD-13 forbids inventing one, and a silent conversion is the one failure mode that is
invisible in every report. The seam ships now; the conversion turns on when a source is ratified.

### Alternatives weighed

- **Allow conversion in V1 with an operator-picked rate source.** Weighed: it unblocks multi-broker
  Books immediately. Rejected for now because it forces a rate-source ruling this sitting cannot ground
  in evidence, and P-4 (Book-to-venue cardinality) is itself unruled — converting across venues before
  ruling whether a Book may span venues is out of order (cross-hat conflict X-5's sequencing).
- **Pin the numeraire to the account's currency and drop the charter field.** Rejected: it makes the
  Book's reporting currency a deployment accident, and AD-9 says broker identity is deployment
  configuration, never architecture.

### What would change it

The operator wanting one Book across accounts in different currencies in V1 (P-4). Then the rate source
must be ratified in this sitting and the refusal becomes a conversion.

---

## F-6 — Book limits expressed in R and notional-in-numeraire (five-hats P-7)

### Evidence

No corpus expresses a Book limit in any unit at all — the exposure ledger is door 6 with its predicate
unprinted (`research/book-template-registry-extraction.md:22-33`) and cross-book cap authority is
GAP-0008 (GITBOOK-BASE:355). Constraints that do bind: DEC-0015 (no futures/options ever; nouns must
not preclude stocks/crypto), AD-7 (`Quantity(unit)` deliberately opaque — lot, share, coin, contract),
AD-9 (symbols opaque, never parsed), GAP-0044 (every variable carries units).

### Bucketing — **stays QMF** (vocabulary); enforcement is node

### Recommended ruling

**Book-level limits are expressed in exactly two units and never in an instrument-native quantity:**
(a) **R** — `r_multiple`, the permission-to-lose unit, asset-class-proof by construction; and
(b) **notional in the Book's numeraire** — `Money(numeraire)`, computed from AD-28's declared instrument
metadata across AD-7's named boundary. A limit expressed in lots is a `policy rejection` at charter
validation: the same charter text would silently change meaning the day an equities venue is added.

Corollary worth stating: cross-venue exposure aggregation additionally requires the registry sitting's
**operator-declared equivalence record** (five-hats P-1) — six brokers' EURUSD are six identities under
AD-9 and may never be equated by symbol inference. The risk sitting *consumes* that record; it must not
invent a substitute.

### Alternatives weighed

- **Percent-of-equity limits.** Rejected: percent-of-*which* equity is the same ambiguity as `E`'s
  composition (F-2), and DEC-0076 already forecloses equity semantics for R.
- **Instrument-native quantity with a per-asset-class conversion table.** Rejected: it re-parses what
  AD-9 made opaque.

### What would change it

Nothing in evidence. This is a design conclusion forced by DEC-0015 + AD-7; it is listed as delegate-
quality in §15.

---

# PART B — GAP-0045: stop-out, B, BENCHED, decay primitives

## F-7 — Stop-out as a typed risk event

### Evidence

**Current corpus (highest) — explicitly unresolved and explicitly blocking:**

```yaml
- name: bench_stopout_threshold
  value: null
  units: consecutive-stop-outs
  decision: DEC-0094
  gap: GAP-0045
  notes: "A reported value of two is unusable until stop-out and BENCHED semantics are reconciled."
```
(`docs/registry/variables.yaml:474-484`; `bench_reset_boundary` likewise null, `:486-495`.)
Glossary: *"Stop-out: An unresolved risk event term. Whether breakeven or other closes count and how
stop-out drives BENCHED state remain `GAP(GAP-0045)`."* (`docs/glossary.md:432-434`).

**Old wiki:** PE-3 is a named pre-epic blocker — *"stop-out taxonomy: must remain projection-computable
and blocks breaker/sizing completion"* (`knowledge/gap-report.md:40`); *"Which exits count as stop-outs
for breaker projection and measured `Lbar`?"* (`open-questions.md:18`). **GitBook:** the counter exists
(`B = 2 consecutive_stopouts`) with **no definition of the event it counts** — confirmed on the live
site too ("No formal definition of 'stop-out' itself is given anywhere", `extract-live-gitbook.md:599`).
**Old planning:** Story 6.1's ratification scope names the exact list — *"every exit type (natural stop,
breakeven exit, KSA-forced flat, manual-equivalent close) is explicitly classified as counting or not
counting toward the breaker"*, and the taxonomy *"must stay projection-computable"* — rebuildable from
`trade_journal` + `book_journal` + registry (`epics.md:1234`).

**One hazard no dossier names.** In the venue's own vocabulary, "stop out" means **margin-call
liquidation** — the broker closing you for insufficient margin. QMX's "stop-out" means a protective-stop
fill. Two unrelated events, one word, and the venue one is the more dangerous of the two.

### Bucketing — **both**

QMF carries the **exit-record contract**, the classification **vocabulary** (addable never redefined),
and the **read-time fold rule**. The node classifies at runtime and enforces the breaker. This is the
cleanest QMF/node split in the whole cluster: the noun is framework, the reaction is node.

### Recommended ruling

**Mint a typed exit record — one per position close — and derive everything else from it.**

Working shape (`CT-RISK-EXIT`), a `qmf-core` value type recorded through the composition root per AD-28,
content-fingerprinted by `qmf-core`'s single implementation:

- `position_ref` — fingerprint of the admission record
- `original_risk_distance` [PriceDelta] and `original_risk_amount` [Money] — **carried on the record**,
  frozen at admission (F-1), so `r_multiple` is recomputable forever without re-reading the admission
- fill references — AD-27 fill observations (fill price, fill quantity, venue instant, receive instant
  are already mandatory identity fields there)
- `realized_pnl` [Money] and `realized_r` [r_multiple, exact rational]
- `exit_cause` — a **typed vocabulary of mechanisms**, addable never redefined:
  `protective_stop_fill | target_fill | policy_amendment_fill | hold_time_force_flat |
  protection_forced_flat | boundary_flat | venue_liquidation | operator_close | venue_initiated_close`
- `suppressing_authority` where a control caused the close — the same first-class suppression record
  five-hats A-7 asks for, so "our gates blocked it" never reads as decay
- AD-12 label parts: knowledge time, evidence class, world, **account-binding role**
- `classified_under` — the format version of the Book's declared loss predicate (see F-8)

Three rules ride with it:

1. **Mechanism and outcome are separate fields.** `exit_cause` says *what closed it*; `realized_r` says
   *what it cost*. Fusing them is how "stop-out" became undefinable: a protective-stop fill can be −1R
   or, after a stop move, 0R, and a force-flat can be either sign.
2. **The breaker counter is a read-time fold, never a mutable counter.** The consecutive-qualifying-loss
   run is computed by folding the exit-record stream — the same idiom AD-25 uses for structure lifecycle
   and AD-27 uses for order state. This is not stylistic: the adversarial finding on record is *"stop-out
   #1 journaled; crash; restart; breaker counter = 0; stop-out #2 doesn't bench"*
   (`adversarial-coherence-attack.md:28`, old-planning:273). A fold is crash-proof by construction and
   is exactly the "projection-computable" property PE-3 demands.
3. **Retire the bare word "stop-out" from QMX vocabulary.** Use `qualifying_loss_exit` for the breaker's
   input and reserve `venue_liquidation` for the broker's margin stop-out. The operator's meaning is
   preserved as one named member of the vocabulary; the collision with the venue's meaning is removed
   before it costs something.

### Alternatives weighed

- **Define "stop-out" as a single enum value and count it.** Rejected: it is the current state and it is
  precisely what four corpora could not make work, because the same mechanism produces different outcomes.
- **Define stop-out purely by outcome (`realized_r ≤ threshold`) with no mechanism field.** Weighed and
  partly adopted — the breaker predicate is outcome-based (F-8) — but the mechanism field must exist
  anyway for A-7 suppression accounting, for PE-7 boundary work, and for the venue-liquidation alarm.
- **Leave it to the node entirely.** Rejected: the record is the analyst's only primitive (five-hats A-2)
  and the exam's `mean_loss_r` / `breaker_expectation` fields (`ct-exam-01:22-32`) consume it. A node-only
  definition means every consumer re-invents it.

### What would change it

A ruling that exit ownership (DEC-0067 / GAP-0040) lands with the Bot rather than the Book. The record
shape survives either way — but `exit_cause`'s vocabulary would need a `bot_organ_exit` member and the
attribution convention five-hats A-8 asks for becomes urgent.

---

## F-8 — The breakeven-exit fork

### Evidence

**This is the one item every layer agrees must be *ruled*, not inherited.**

Old wiki, verbatim: *"A breakeven exit and a full original-stop loss are different outcomes, but the
current scalper breaker only says 'consecutive stop-outs.' Whether a BE-out counts is undefined."*
(`topics/position-safety-and-sltp-authority.md:47`; open decision at `:85`).

QMX-discussion clash layer, verbatim: *"The breaker counts 'stop-outs' — but **stop policy DEFINES what
a stop-out is.** … does a breakeven exit count toward `scalper_breaker_threshold`? If yes — benching
accelerates wildly… If no — the one-shot-BE design quietly reduces breaker sensitivity… **This must be
a ruling, not an inheritance.**"* (`clash-report-sltp-vs-book.md:36-45`). A recorded *recommendation*
(explicitly not a ruling) at `:97-100`: *"**no** for the scalper book — count full stops only, keep
BE-outs as a separate measured metric."*

Current corpus: leaves it open by name (`docs/glossary.md:432-434`). Old planning: Story 6.1's scope
requires classifying "natural stop, **breakeven exit**, KSA-forced flat, manual-equivalent close"
(`epics.md:1234`), and notes the stakes: *"`B = 2` is a direct input to FORM-0004 and FORM-0006, so the
stop-out taxonomy flows straight into position sizing."*

**One live complication.** The BE-out only exists if a Book declares a breakeven-move policy — and the
old one-shot-BE-at-+1R policy is explicitly on the **do-not-inherit** list (BT-RECOVERED:261, "BE at +1R
and old SL/TP service"; D-07 globally-uniform stop service dropped). So the question is not "what does
our stop policy do" — it is "what does the breaker count, for any Book, including Books that do not
exist yet."

### Bucketing — **node**, with a narrow QMF seam

The *predicate* is Book-charter data evaluated at runtime → node. QMF carries only (a) the vocabulary
and typed fields it reads (F-7), (b) the requirement that a Book **declare** its predicate rather than
inherit one, and (c) the predicate's own contract format version stamped onto every classified exit
(F-7's `classified_under`), so a predicate change is a visible mint, not a silent re-reading of history.

### Recommended ruling

**A breakeven exit does not count toward the bench counter.** The counter counts **qualifying loss
exits**: exits whose `realized_r` is strictly negative after costs. A breakeven exit cost nothing, and a
breaker that fires on trades that cost nothing is measuring thesis quality, not damage — while the leash
chain's stated job is damage (L16, `system-constitution.md:41`: *"The leash handles damage; sunset review
handles pointlessness"*). BE-outs are recorded as their own measured metric on the exit record and are
available to every analysis without touching the breaker.

**Any magnitude threshold stays unratified.** "Only count exits worse than −0.8R" is a calibration and
AD-13 forbids inventing it. The sign of `realized_r` is a *definition* (loss vs not-loss), not a tuned
number, so it is safe to state now; anything finer waits for measurement.

Second-order consequence to state in the same breath: **a protection-forced flat and a boundary flat are
mechanisms, not verdicts** — if such a close realizes a loss it counts, if it realizes zero or a gain it
does not. That answers PE-3's "KSA-forced flat?" without a special case and without letting the system's
own protection bench the bot it just protected.

### Alternatives weighed

- **Count BE-outs.** The honest argument: for a scalper, repeated BE-outs mean the read is wrong and the
  bot should stop. Rejected because it makes benching hypersensitive exactly where BE-outs are common
  (the clash report's own "benching accelerates wildly"), and because the design intent that *created*
  the BE move was to protect capital — punishing the protection inverts it.
- **Count by mechanism (any protective-stop fill counts, regardless of outcome).** Rejected: after a stop
  move the same mechanism produces a 0R exit, so mechanism-counting silently re-introduces the ambiguity.
- **Refuse to rule and make every Book declare it with no default.** Weighed — it is the most honest and
  it is where the seam lands anyway. Rejected as the *answer* because the operator will need a default
  for the first Book, and an undeclared default becomes an accident.

### What would change it

Measured evidence that BE-out clustering predicts a losing day better than loss clustering does. That is
exactly the kind of thing the exit record (F-7) exists to make measurable — so this ruling is reversible
by evidence, cheaply, which is the main reason to make it now.

---

## F-9 — Un-overloading B: two variables, one optional declared binding

### Evidence

**B does two unrelated jobs with one number, in every corpus.**
Job 1, the breaker: `scalper_breaker_threshold`, symbol B, value 2, units `consecutive_stopouts`,
*"Consecutive stop-outs before bench-to-paper"* (`registry/variables.md:23`; GITBOOK-BASE:124;
L-CODE `registry_census.json:69-80`). Job 2, sizing: the same B appears as a divisor in FORM-0004 and a
ceiling factor in FORM-0006 (`registry/formulas.md:38,53`; gitbook-capture:410 states it plainly:
*"B also feeds sizing"*). Old planning states the consequence: *"`B = 2` is a direct input to FORM-0004
and FORM-0006, so the stop-out taxonomy flows straight into position sizing. An open definition sits
under both the only ratified automatic protection transition and the money ladder."* (old-planning:271).

**Current corpus (highest)** refuses to use the number at all: *"A reported value of two is unusable
until stop-out and BENCHED semantics are reconciled."* (`docs/registry/variables.yaml:484`).

The coupling is real and it is directional: **changing the bench rule silently re-sizes every seat in
the Book.** Nothing in any corpus says that was intended.

### Bucketing — **stays QMF**

Two typed registry variable declarations with distinct unit-kinds, plus the refusal that one may not be
substituted for the other. The node consumes both.

### Recommended ruling

**Split into two variables with different unit-kinds, and make any coupling an explicit declaration.**

| Name | Unit-kind | Job | Owner |
|---|---|---|---|
| `bench_consecutive_loss_threshold` | `count` | how many qualifying loss exits in a row bench a bot's seat | Book charter (leash) |
| `seat_loss_run_allowance` | `r_multiple` | the depth in R a seat is sized to survive in one period | Book charter (money rules) |

A Book **may** declare the second derived from the first (`threshold × safety_multiple × measured_mean_loss`,
F-2's recovered reading) — as **declared data with its own fingerprint**, so the coupling is visible in
the charter and in every artifact that consumed it. It is never a hardcoded identity.

The dimensional checker (F-4 rule 3) enforces the split for free: a `count` cannot appear where an
`r_multiple` is declared. That is the whole point of doing F-4 before F-9.

### Alternatives weighed

- **Keep one number.** The coherent argument for it: sizing against exactly the drawdown depth you
  tolerate before benching makes bench and sizing consistent by construction, and one number is one
  fewer thing to get wrong. This is a real position, not a strawman — which is why it is an operator
  question (§14 Q3) rather than a delegation.
- **Split and forbid any coupling.** Rejected: it throws away the coherence argument for no gain. A
  declared derivation keeps the coherence *and* makes it auditable.

### What would change it

The operator saying the coupling was deliberate and load-bearing. Then the recommendation becomes: one
variable, one unit-kind (`r_multiple`), with the bench threshold *derived from it* rather than the other
way round — because the sizing side is the one that needs real units.

---

## F-10 — Un-overloading BENCHED: seat state is not a Book mode

### Evidence

**Four layers agree, and the current corpus is the only one that has not ratified it.**

Current corpus (highest): *"BENCHED: Do not assign BENCHED a canonical schema yet. The name is
overloaded between Book mode and Bot seat state under `GAP(GAP-0045)`."* (`docs/glossary.md:518-520`);
CT-24 is `wiring_status: reserved-evidence-only` with every field null under GAP-0041
(`docs/contracts/ct-24-book-mode.yaml:1-34`).

Old wiki, verbatim: *"The V1 book-mode map emits only LIVE and PAPER. BENCHED is a bot roster-seat state.
BENCHED and STOOD_DOWN remain reserved values in the wider mode vocabulary…"* (`paper-mode-system.md:32`);
the benched seat *"behaves as paper until next open"* and auto-resets (`system/lifecycle.md:48`,
`ct-paper-01:32`); *"Bot breaker benching does NOT mutate book mode"* (`ct-book-02:37`). ADMITTED is a
**registration state, never a book mode** (`glossary/index.md:19`, AD-40).

Recovery `[WIKI-2026-07]`: *"Active Book modes are `LIVE` and `PAPER`; `BENCHED` is a roster-seat state;
`STOOD_DOWN` is reserved."* (TND-DELTA:72 / K-26), with four state spaces named for separation: Book
mode, bot-seat state, supervision stand-down, admission/activation (TND-HANDOFF:41).

L-STD executable standard: `kill_line_stand_down` is book-scoped LIVE→PAPER; `breaker_bench` is
bot-scoped LIVE→BENCHED with **`book_level_benched_write = false`**; *"A BENCHED bot does not change the
book mode."* (`standards/frozen-counterfactual-paper-semantics.json:37-49`;
`references/ui-exploration/specs/object-lifecycle-bot.md:81`).

**And the structural proof that the split is necessary, not merely tidy** (GITBOOK-BASE:403 / T-06):
CT-PAPER-01 carries an optional `bot_id`, but CT-BOOK-02 and CT-BMS-02 are keyed **only by `book_id`** —
so *"a mixed book (one bot benched, others live) is not representable."* One enum keyed on the Book
literally cannot express the state the breaker produces. The schemas still mix all four values
(TND-DELTA:154 / C-02, `REOPEN`).

### Bucketing — **stays QMF** (two typed vocabularies + record scoping); transitions are node

### Recommended ruling

**Two separate enums on two separate records, with one invariant between them.**

- **Book mode** — scoped to the Book (and its binding): `LIVE | PAPER` in V1. `STOOD_DOWN` is *reserved*
  in the sense AD-16 means it: kinds and values are addable, never redefined, so it is added when it is
  designed and not before. **BENCHED is removed from this enum entirely.**
- **Seat state** — scoped to `(Book, Bot, binding)`, i.e. the AD-17 binding record: `ACTIVE | BENCHED`.
- **ADMITTED lives on neither** — it is a registration state on the registration/promotion record
  (AD-18's promotion-occurrence card), consistent with the old wiki's AD-40 finding.
- **Invariant:** a seat-state write never writes a Book-mode row (L-STD's `book_level_benched_write=false`,
  promoted from a story-local standard to a contract invariant). A transition outside the declared set
  refuses and journals.

**The piece that makes this pay off immediately:** AD-9 already lists `paper-benched` as a first-class
**account role** (live / demo / paper-validation / **paper-benched** / prop-firm), and AD-12 makes
namespaces role-scoped within `world = live`. So a benched seat routes to a `paper-benched` role binding,
whose records write to a role-scoped namespace — benched evidence is separable from live evidence **by
construction**, with no filtering rule to remember. That is the mechanism five-hats A-1 and X-6 need,
and it already exists; the seat-state split is what connects the breaker to it.

### Alternatives weighed

- **One enum, with BENCHED meaning "the Book has at least one benched seat".** Rejected: it is lossy
  (which seat?) and it makes a bot-scoped event mutate a Book-scoped row, which the L-STD standard
  already forbids.
- **Keep all four values in the schema and constrain by prose.** This is the *current* state and it is
  an on-record contradiction in three corpora (C-02, T-06, old-wiki contradictions 2 and 3). Rejected.

### What would change it

Only an operator statement that a benched bot should stand the whole Book down. Nothing in nine dossiers
suggests it, and the breaker's own auto-reset-at-next-open design argues the opposite.

---

## F-11 — Alpha-decay: mint the evidence primitives, defer the math

### Evidence

**The math was never written down, in any layer.** `[WIKI-2026-07]`, verbatim: *"Alpha-decay math |
Never written down | No retrieval possible; future design."* (BT-STATUS:298). Old vault: *"No formula,
weights, lookback lengths, or numeric thresholds are published anywhere in the vault … extraction cannot
supply it because it never existed on paper."* (`alpha-decay-spec.md:36-39`). Old planning: OQ-14, WF3
home, *"expected months after the system is live — a future update, not V1 work"* (`prd.md:598`).

**The old four evidence classes are half-dead.** Rolling CB-fire density (the CB is gone), MAE/MFE drift,
DPR drawdown context (**DPR is dead by operator ruling DEC-0093**), regime/session overlays
(`alpha-decay-spec.md:26-34`; two of four reference dead machinery per
`clash-report-alpha-decay.md:23-26`). The old wiki's detailed page is in **attic/, RULED-OUT**.

**What survives is a definition, not a formula:** *"Alpha decay = sustained, measured divergence of a
bot's live footprint from its certified footprint, and/or measured approach toward its charter's death
condition."* (`clash-report-alpha-decay.md:66-68`) — clash-layer, unratified.

**And a hard constraint:** *"performance/decay evidence flows to Sunday review / sunset review / agentic
analysis — **never to sizing, allocation, or mode changes**"* (`prd.md:471`, SPINE:285); the attic keeps
only *"read-only measurement should not acquire capital/lifecycle authority"* (WIKI-INV:253).

**Current corpus** states only the *reason* decay sensing must stay possible: rebind never mints a new
Bot *"so paper and live performance stay comparable for alpha-decay sensing"* (`qmf-risk.md:59`, DEC-0115).

### Bucketing — **stays QMF** (primitives only); the math, when it exists, is node/analysis territory

### Recommended ruling

**Mint three primitives and no arithmetic.**

1. **The exit record** (F-7) — the per-trade fact every decay measure will consume.
2. **The declared baseline reference** — a fingerprinted pointer from a live binding to the exam
   certificate it was admitted under. CT-EXAM-01's fields are already the right shape:
   `labeler_versions, ev_by_regime, mean_loss_r, fire_rate_band, breaker_expectation, cost_ratio`
   (`ct-exam-01:22-32`). Decay is a *comparison to a declared baseline*; without a durable pointer to
   which baseline, the comparison is unreproducible.
3. **The performance-result container** (F-12) — the object a comparison produces.

**And ratify the non-authority rule as an invariant, now:** measurement never mutates trading state. It
may not size, allocate, promote, demote, bench, or change a mode. This is `prd.md:471` promoted, and it
is the same shape as cross-hat conflict X-3's resolution (QMF *emits* a typed verdict; the node decides
what to do about it).

Explicitly **not** minted: any score, rating, tier, weighted composite, or threshold. DEC-0093 killed
DPR/PRS as risk controls and the six declared weights were correctly called *"opinions wearing math"*
(`clash-report-bot-rating.md:38-41`).

### Alternatives weighed

- **Port the two surviving evidence classes (MAE/MFE drift, regime overlays) now.** Rejected: both need
  lookbacks and thresholds that no source supplies (AD-13), and both are computable from the primitives
  later at no extra cost.
- **Defer everything including the primitives.** Rejected: the primitives are what make the deferral
  *safe*. Without the exit record and the baseline pointer, the evidence needed to design decay later
  is not being collected now, and it cannot be back-filled.

### What would change it

The operator wanting a decay signal in V1. Then the sitting must ground at least one lookback in measured
data, which does not exist yet — so the honest answer would be "collect first", i.e. the same primitives.

---

## F-12 — The performance-result container (five-hats A-2)

### Evidence

Five-hats A-2, verbatim: *"the analyst's central object — a fingerprinted performance result over a
declared population and period, produced by a versioned formula, carrying units — has no owning contract
anywhere … the risk sitting must still mint the **container**: a result kind with an AD-12 label, a
declared population, a declared period, and units per GAP-0044."* No corpus contains such an object;
`qmf-risk` owns Book/BMS semantics, `qmf-data` owns evidence, `qmf-registry` owns identity, backtesting
is deferred. Fresh design, but tightly constrained: AD-12 supplies the label, AD-16 supplies the record
shape and the "kinds addable never redefined" rule, AD-10 supplies float-bearing identity
(label-derived, never a hash of float bytes).

### Bucketing — **stays QMF**

A registry record kind whose schema is a risk-sitting contract. Producers are node/analysis-side.

### Recommended ruling

Mint one kind. Its fields:

- **AD-12 label in full** — producer contract identity, producer **contract format version**, input
  fingerprints, evidence time range, computation/occurrence identity, evidence class, **world**, and
  **account-binding role** (AD-12's role-scoped namespaces).
- **Declared population** — the exact set the number is *about*: Bot identity, which binding epochs are
  included or excluded, which account roles, which instruments, and the cohort rule under which they
  were admitted together. Not a description — a fingerprinted declaration.
- **Declared period** — an AD-8 `Interval` with its calendar identity and version in-band, plus the
  **knowledge-time bound** the result was computed under (five-hats A-4: corrections make every
  performance number a function of when it was run).
- **Units per GAP-0044** — every emitted quantity declares a unit-kind from F-4's closed vocabulary;
  `r_multiple` results carry no currency, `Money` results carry the numeraire (F-5).
- **Suppression accounting** — counts of actions suppressed during the period by authority and reason
  (five-hats A-7 / X-6), so "our gates blocked the trades" can never read as decay.
- **Float discipline** — a Sharpe, a drawdown, a slope is a float; identity is **label-derived** per
  AD-10, with an integrity checksum and (OS, library-version) provenance, never a hash of float bytes.

One rule that is cheap now and expensive later: **a single result may not span account roles.** AD-12's
role-scoped namespaces already forbid mixing at the storage layer; stating it on the container stops
someone assembling the mix in memory and labelling it once.

### Alternatives weighed

- **Defer to the backtesting sitting.** Rejected: five-hats lists A-2 as inherited-not-owned by
  backtesting, and the analyst's V1 workflow (live vs paper comparison) needs it before backtesting
  exists.
- **Let each analysis script define its own shape.** Rejected in the sweep's own words: *"every analysis
  is an unregisterable one-off script and none of it accumulates."*

### What would change it

The comparison-cohort rule (five-hats A-1) landing differently in the neighbouring cluster — the
container's `declared population` field must carry whatever that rule decides, so the two must be
written against each other.

---

## F-13 — Metric arithmetic binds to the contract format version (five-hats A-3)

### Evidence

Five-hats A-3: two runs of "the same metric" under different numpy/statsmodels versions produce one
identity and two values, legitimately, with no signal to the analyst — because AD-10 gives float-bearing
artifacts label-derived identity and AD-12 says package SemVer never enters identity.

**The mechanism is already ratified.** AD-23: *"Where [the pinned reference] does not [implement a
formula] … the QMX implementation is the canonical arithmetic for that formula, pinned by its own
contract format version under the identical upgrade gate"*, and *"an output change for identical
canonical inputs mints the per-configured-indicator contract format version — never a protocol-wide
bump"*, with recorded before/after evidence. AD-5: *"a format version's meaning never changes after the
fact."*

### Bucketing — **stays QMF**

Applying AD-23's existing gate to a new class of producer.

### Recommended ruling

**A performance metric is a governed producer under AD-23.** Its arithmetic is canonical and pinned by
its own contract format version; an arithmetic change is a **format-version mint with recorded
before/after evidence**, never a package release. Identity therefore moves when meaning moves, which is
exactly what A-3 asks for. Where a metric wraps a pinned reference implementation, wrap-not-reimplement
applies; where it does not, the QMX implementation is canonical. Dual-reference checks, where a second
reference exists, are registered comparison artifacts with declared **integer ULP** tolerances.

### Alternatives weighed

- **Put the library version into identity.** Rejected: AD-12 explicitly bans package SemVer from identity
  and it would shatter dedup for every unchanged metric.
- **Ignore it and accept the ambiguity.** Rejected: the same seam is what forced AD-23 to exist for
  indicators (TA-Lib 0.7.1's own MACD/TRIX/ULTOSC change is the recorded precedent).

### What would change it

Nothing — this is mechanical application of a ratified AD. Listed as delegate-quality in §15.

---

# PART C — Summary tables

## 14. Operator questions (recommendation first)

**Q1 — Must every trade declare its full-loss price before it opens?**
*Recommendation: yes.* Every position should write down, before it opens, the exact price at which it
would be a full loss — even when no stop order is parked at the broker. Without that number, position
size, the bench counter, the mean-loss measure, and every performance figure have nothing to measure
against, and we would be guessing. The cost: a strategy that deliberately runs without a planned loss
point could not trade in QMX.
→ **Every position must declare its planned full-loss price before opening: yes / no.**

**Q2 — Does a trade that closes at breakeven push a bot toward the bench?**
*Recommendation: no.* A breakeven exit cost nothing. The bench exists to stop damage, and counting
no-cost trades makes it fire on bots that are not losing money. We would still record every breakeven
exit as its own number so you can watch them, and we can reverse this later from the data if breakeven
clustering turns out to predict bad days.
→ **Breakeven exits count toward the bench counter: no / yes.**

**Q3 — Split the "2" that currently does two jobs?**
*Recommendation: yes, split it.* Today one setting says both "how many losses in a row bench a bot" and
"how deep a losing run each trade is sized against." That means changing the bench rule silently changes
every trade size in the Book. Splitting gives two settings you can move independently, and a Book can
still declare them linked on purpose — the link just becomes visible instead of accidental.
→ **Split into two settings: yes / no (keep one number doing both jobs).**

**Q4 — Is BENCHED something a bot is, or something a Book is?**
*Recommendation: a bot's seat, never the Book.* A Book is only LIVE or PAPER. When a bot gets benched,
it sits out inside a Book that is still live and the other bots keep trading. Every corpus we read says
this, and the current schemas literally cannot express "one bot benched, others live" until we split it.
→ **Ratify BENCHED as a bot seat state, removed from the Book mode list: yes / no.**

**Q5 — Currency: refuse or convert, in V1?**
*Recommendation: each Book names the one currency its money is counted in, and in V1 we refuse to attach
a Book to an account held in a different currency rather than converting.* We have no agreed exchange-rate
source, and a silent conversion is the one error that never shows up in a report. The plumbing for
converting ships now; we switch it on once you pick a rate source.
→ **V1 refuses cross-currency Book bindings: yes / no (allow conversion now — then we must pick a rate
source in this sitting).**

**Q6 — Should a Book price a seat off what the bot's losses actually measure?**
*Recommendation: yes, keep that principle — rebuild the arithmetic from scratch.* The old ladder sized
each seat from the bot's measured average loss at exam rather than from anything the bot claimed about
itself. That principle is sound and worth keeping. The arithmetic around it was broken (it compared
dollars to risk-units), so we rebuild the formulas with proper units and no numbers until we have
evidence.
→ **Keep "price a seat off measured loss behaviour": yes / no (price seats off a flat declared
per-trade risk instead).**

## 15. Items closed on delegation (no operator question)

| Item | Safe to close on delegation because… |
|---|---|
| **F-2** dimensional autopsy | It is a diagnosis of already-ruled facts: DEC-0077 killed FORM-0006, and ADDENDUM:119 / T-12 / old-planning:258 all record the same defect. Nothing new is being decided. |
| **F-4** replacement shape + dimensional tests | The shape proposes no value and every rung is forced by AD-7, AD-11, AD-13, DEC-0105 and PE-4; the eight tests are engineering discipline, not policy. Only the *principle* underneath it (Q6) is a ruling. |
| **F-6** limits in R + notional-in-numeraire | Directly forced by DEC-0015 (nouns must not preclude stocks/crypto) plus AD-7's deliberately opaque `Quantity(unit)`; the alternative (lots) is already foreclosed. |
| **F-7** typed exit record | The contract shape is the *container* for the ruling, not the ruling; PE-3 and Story 6.1's scope already demand exactly this list, and the read-time-fold rule mirrors ratified AD-25/AD-27 idiom. The only ruling inside it is Q2. |
| **F-11** decay primitives, math deferred | Every layer records the math as never-written; the primitives are collection discipline, and DEC-0093 already forecloses everything that would have needed a ruling. |
| **F-12** performance-result container | AD-12 supplies the label, AD-16 the record shape, AD-10 the float-identity rule; the container is assembly, and the one field that needs a ruling (declared population / cohort) belongs to the comparability cluster (five-hats A-1). |
| **F-13** metric arithmetic ↔ format version | Mechanical application of ratified AD-23 to a new producer class; the alternative is banned by AD-12. |

## 16. What QMF carries vs what the node carries

| # | Item | QMF seam / contract | Node |
|---|---|---|---|
| F-1 | R's three faces | `qmf-core` value types (`PriceDelta`, `Money`, exact-rational `r_multiple`), the named admission boundary, the frozen-at-admission invariant, the incomputable-R refusal | where a Book puts its stop |
| F-2 | autopsy | the dimensional law it justifies | — |
| F-3 | three capital concepts | the three types + the `r_unit_price` rate | the ledger |
| F-4 | replacement shape + tests | unit-kind vocabulary, per-formula unit declarations, symbolic checker, FORM-0006 as permanent negative test, worked-checksum tests | evaluating a Book's declared money rules |
| F-5 | numeraire | charter fields (numeraire, rate source, knowledge time) + AD-7 named boundary + V1 cross-currency refusal | applying the rate |
| F-6 | limit units | the limit-expression vocabulary (R, notional-in-numeraire) | enforcement |
| F-7 | exit record | `CT-RISK-EXIT` shape, `exit_cause` vocabulary, read-time-fold rule, `classified_under` stamp | classifying and counting at runtime |
| F-8 | BE-out | the requirement that a Book *declare* its predicate + the format-version stamp | the predicate itself |
| F-9 | un-overload B | two typed variables + the substitution refusal | consuming both |
| F-10 | un-overload BENCHED | two enums, two record scopes, the no-cross-write invariant, the `paper-benched` role wiring | transitions and auto-reset |
| F-11 | decay primitives | exit record, baseline pointer, non-authority invariant | analysis |
| F-12 | result container | the registry record kind | producing results |
| F-13 | metric arithmetic | AD-23 gate applied to metrics | — |

## 17. Cross-cluster dependencies and sequencing hazards

1. **F-5 must not be ruled before Book-to-venue cardinality (five-hats P-4 / X-5).** Converting across
   venues before ruling whether a Book may span venues is out of order. The V1-refusal recommendation is
   deliberately chosen so this sitting can proceed either way.
2. **F-7's `exit_cause` vocabulary needs the same-tick priority cluster (GAP-0046) and PE-7.**
   `protection_forced_flat` and `boundary_flat` are its members; their *ordering* is the other cluster's
   ruling, but the vocabulary members must be minted together or the two lists drift.
3. **F-7 also needs the venue capability set (five-hats T-4, CT-18).** `venue_liquidation` and
   broker-side resting stops are venue-resident facts; the exit vocabulary must be written against
   AD-28's declared protection primitives (`suspend-new | drain | close_all`) and position model
   (`netting | hedging`), not against an assumed one.
4. **F-12's `declared population` is written against the comparison-cohort rule (five-hats A-1).**
5. **F-2's open item — whether equity `E` includes unrealized P&L** (old-planning:248, PE7-MEMO:189-190)
   — belongs to the position-fate cluster but lands in these formulas. It must be answered there and
   consumed here.
6. **Exit ownership (DEC-0067 / GAP-0040)** does not block F-7's record shape, but it decides five-hats
   A-8's P&L attribution convention, which the F-12 container must declare.
7. **AD-2 edge request:** none. Everything proposed here lives in `qmf-core` value types,
   `qmf-risk` contracts, and `qmf-registry` record kinds, all of which depend on `qmf-core` only.
   *(Answering five-hats D-1's "explicit edge request or explicit none" for this cluster.)*
