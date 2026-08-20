---
name: 'ICT/SMC edge-case review — can the spine hold a random retail experiment?'
type: review-edge-case
target: ARCHITECTURE-SPINE.md (QMF V1 Foundation, updated 2026-08-20)
scope: 'AD-22..AD-25 (indicator protocol, TA-Lib canonical arithmetic, light/heavy, causal structure lifecycle) walked against 21 concrete ICT/SMC/retail concepts, in the context of AD-7, AD-8, AD-9, AD-10, AD-11, AD-12, AD-13, AD-15, AD-16, AD-17, AD-19, AD-21 and the Deferred table.'
lens: 'a random, creative ICT/SMC retail trader-experimenter — "some experiments will be very random, and if they work we shall use them"'
created: '2026-08-20'
reviewer: ict-edge-cases
findings: 30 (must-fix 11 · should-fix 14 · note 5)
---

# ICT/SMC edge-case review — QMF V1 Foundation spine

## Verdict

**The shape is right and the taxonomy has real teeth — but CT-16 and CT-17 as
currently specified cannot yet express the majority of the operator's own stated
primary use case, and two of the gaps silently destroy evidence rather than
refusing.** Not one finding below asks to reopen a ratified AD's *stance*. AD-25's
observed-at/confirmed-at law is the correct answer to retail repainting, AD-22's
two-mode equality law is the correct answer to research-live drift, and the
"no privileged families" ruling is exactly what a from-scratch SMC author needs.
Every fix in this review is **additive**: something CT-16 or CT-17 must *declare*
before those contracts are written, not something the spine must retract.

But the spine was written along a *primitives* axis and ICT/SMC concepts cut
across it along a *chart-object* axis, and the two axes disagree in eleven places
that a first builder will hit in week one. Three patterns dominate:

1. **The retro-anchored object.** Order blocks, fair value gaps, breakers and
   sweeps are all objects that occupy a price/time region *in the past* relative
   to the instant they become knowable. AD-25 gives two lifecycle instants and no
   home for the anchor. `observed-at` is genuinely ambiguous between "when the
   object came into being on the chart" and "when the system could first derive
   it," and the two readings differ by exactly one displacement leg — which is
   the difference between causal evidence and a repaint.
2. **The undeclared configuration input.** Killzones, midnight open, session
   opens, AMD, IPDA ranges, multi-timeframe nests and SMT divergence all need
   something CT-16/CT-17 never say a component may take: a calendar, a second
   timeframe, a second instrument, a quote side, or another component's output.
   AD-22's dedup tuple is enumerated (`formula + parameters + instrument +
   timeframe`) and reads as exhaustive; taken literally it both forecloses these
   configurations *and* — worse — merges instances that AD-8 says must be
   distinct, because calendar identity and tzdata version are not in the tuple.
3. **The silent merge.** Two findings (MF-02, MF-03) do not refuse, do not warn,
   and do not fail a gate. They dedup two genuinely different things into one
   artifact and AD-10's collision split accepts the second write silently as an
   "idempotent re-write." For an append-only evidence system whose whole promise
   is that history is never lost, silent merge is the worst available failure
   mode, and it is reachable from the most ordinary ICT object there is: a swing
   high that prints twice at the same price.

The plain-Python research lane (test **a**) passes for all 21 concepts, without
exception and without strain. Nothing in AD-22 or AD-25 boxes in an experiment.
The pressure is entirely at the governed-evidence door, which is where the
operator agreed it should be — the problem is that the door is currently too
narrow for objects he has explicitly said he intends to author.

**Bottom line for a non-technical operator:** you can research anything today.
About half of what you'd actually want to *promote* — anything session-scoped,
anything multi-timeframe, anything that partially fills — has no ratified way to
be written down yet. The fixes are small. Make them before qmf-indicators and
qmf-structure are coded, not after.

---

## Severity index

| Severity | Count | Meaning here |
|---|---:|---|
| **must-fix** | 11 | A legitimate ICT experiment is impossible to express in governed evidence, or a ratified AD is contradicted |
| **should-fix** | 14 | Expressible, but two competent builders would guess differently and produce incompatible artifacts |
| **note** | 5 | Worth stating in the contract; includes two things the spine already gets right that a builder will otherwise reinvent |
| **Total** | **30** | |

Owning surface: **CT-16 / AD-22** 9 · **CT-17 / AD-25** 12 · **both** 5 ·
**AD-17 / registry** 2 · **deferred-table scope** 2.

**How to read.** Part 1 walks 21 concepts against the four tests
(a) free research / (b) CT-16 indicator / (c) CT-17 family / (d) breaks the
shape. Part 2 states each finding with the exact clause that blocks or strains
it and the smallest amendment that fixes it. Part 3 runs the operator's
"very random" mixed confluence end to end. Part 4 credits what holds. Part 5 is
the minimal patch set as a checklist.

---

## Part 1 — The concept walk

Legend: **Y** = yes as ratified · **Y\*** = yes only after the named fix ·
**n/a** = wrong shape for that contract, not a defect · **(d)** = breaks the
contract shape.

| # | Concept | (a) plain Python | (b) CT-16 indicator | (c) CT-17 family | Blocked by |
|---:|---|:---:|:---:|:---:|---|
| 1 | Swing point (seed family) | Y | n/a | Y | — |
| 2 | ZigZag / repainting swing labeler | Y | **(d)** | Y (confirmed-swing variant only) | designed exclusion; MF-09 |
| 3 | Order block | Y | n/a | Y\* | MF-01, MF-02, MF-08 |
| 4 | Fair value gap + partial fill / mitigation | Y | n/a | Y\* | MF-08, MF-01, SF-09 |
| 5 | Inversion FVG | Y | n/a | Y\* | MF-08, SF-06 |
| 6 | Breaker block | Y | n/a | Y\* | MF-01, SF-06 |
| 7 | Liquidity pool (equal highs/lows) + tolerance | Y | n/a | Y\* | MF-07, MF-02 |
| 8 | Liquidity sweep / stop hunt | Y | n/a | Y\* | SF-03, SF-11 |
| 9 | BOS / CHoCH (market structure shift) | Y | n/a | Y | — (cleanest pass in the set) |
| 10 | Displacement | Y | Y\* | Y\* | MF-06, MF-07, SF-05 |
| 11 | Killzones (London/NY/Asia windows) | Y | Y\* | Y\* | MF-05, MF-03, N-02 |
| 12 | Midnight open / session & weekly opens | Y | Y\* | Y\* | MF-05, MF-03, SF-08 |
| 13 | Power of three / AMD | Y | n/a | Y\* | MF-05, SF-01, SF-02 |
| 14 | Multi-timeframe nest (H4 OB → M1 entry) | Y | Y\* | Y\* | MF-03, MF-04, MF-10, MF-09 |
| 15 | SMT divergence (cross-instrument) | Y | Y\* | Y\* | MF-03, MF-10 |
| 16 | Premium/discount + OTE fib arrays | Y | n/a | Y\* | MF-07, SF-06, SF-14 |
| 17 | News-anchored levels / release candles | Y | Y\* | Y\* | MF-05, SF-07 |
| 18 | Volume profile / liquidity void | Y | Y\* | Y\* | N-01, SF-05 |
| 19 | Renko / range / tick bars | Y | Y\* | Y\* | MF-04 |
| 20 | IPDA 20/40/60 trading-day ranges | Y | Y\* | Y\* | MF-05, SF-04 |
| 21 | Discretionary daily bias / MM narrative | Y | **(d)** | **(d)** | correctly excluded by design |

**Score: 21/21 pass test (a). 14 of 21 need at least one must-fix before they can
enter governed evidence. Two are honest (d)s, and both (d)s are the taxonomy
working as designed.**

### 1 — Swing point *(the baseline)*

A swing high with fractal degree N is confirmed the moment the Nth bar to its
right closes without exceeding it. Precisely stateable, X knowable at that
instant, confirmation delay = N bars and declarable. This is AD-25's poster
child and it passes cleanly. Degree/rank is just a parameter in the fingerprint
(N-05). The only strain is MF-02 (identity) which every family shares.

### 2 — ZigZag / repainting swing labeler *(the honest (d))*

The retail ZigZag redraws its last leg as new extremes print. As a CT-16
indicator this is a **(d)**: AD-22 gives an output three states — a number, a
marked not-ready warm-up value, and a marked gap — and no fourth state for
"a value I will revise." A ZigZag streaming instance cannot conform without a
revision class, and inventing one would gut the equality law. That is the right
outcome: ZigZag-as-drawn belongs in the research lane, ungoverned, forever.

The *causal* variant — emit only swings already confirmed by N right-hand bars —
is a clean CT-17 family (concept 1). So the spine forces the right refactor.
**But note the asymmetry that MF-09 names:** AD-25 explicitly has an unconfirmed
evidence class that is "never silently mixed" with confirmed; AD-22 has no
equivalent, so an indicator's intra-bar provisional value has nowhere to be
marked — the same repaint that CT-17 kills, CT-16 leaves undefined.

### 3 — Order block

*Bullish OB: the last down-close candle before a displacement leg that breaks
structure.* Three distinct instants exist in reality:

- **T0** — the OB candle itself. This is where the zone is *drawn*: it has a
  start instant, an end instant, and a high/low price band.
- **T1** — the instant the displacement/BOS completes and the candidate becomes
  derivable at all.
- **T1** — confirmation, usually the same instant under a strict rule.

AD-25 offers `observed-at`, `confirmed-at`, `invalidated-at`. **T0 has no
home**, and `observed-at` is read two opposite ways: "the bitemporal law applied
to chart objects" (AD-25's own gloss) makes `observed-at` sound like *event
time* = T0, while the word "observed" makes it sound like *known-at* = T1. A
builder taking T0 has just written an object whose evidence instant precedes the
data that justified it — a repaint, wearing a causal label. A builder taking T1
has no field left to record where the zone is actually drawn, and the trader
cannot render his own chart from his own evidence. → **MF-01**.

Compounding: the object is *identified* by its content, and if the two instants
are classified as occurrence facts (AD-16's created-at precedent), two
same-price OBs on different days fingerprint identically and the second is
silently swallowed. → **MF-02**.

Mitigation ("has price returned into this OB yet?") → **MF-08**.

### 4 — Fair value gap, including partial fill / mitigation

Confirmation rule is beautiful and precise: *"confirmed the instant candle 3
closes with `low(c3) > high(c1)`"*. Zero ambiguity, zero look-ahead, declarable
delay. CT-17 handles the birth perfectly.

**The lifecycle is where it breaks.** An FVG is not born-then-dead; it is
*consumed*. Price trades back into it and the usable remainder shrinks, tick by
tick. Consequent encroachment (the 50% level) is the single most-used entry
trigger in the whole ICT vocabulary and it is a function of the *current
remaining* range. AD-25's lifecycle is a triple — observed / confirmed /
invalidated — and AD-19 says evidence is append-only with corrections as
annotations. So:

- Storing "remaining range" as a mutable field on the object contradicts
  append-only. Correct refusal — this one really is a **(d)** if attempted.
- Minting a new artifact per fill increment mints one artifact per tick that
  touches the zone. Unworkable, and AD-13's artifact-count ladder would light up.
- The right shape — **interaction events as separate append-only records
  referencing the object's fingerprint, with current state as a read-time fold**
  — is not in AD-25's vocabulary and there is no AD-16 edge kind for it
  (`supersedes / promoted-from / occurrence-of / corroborates / disagrees-with`
  are the ratified five, and none of them is "touched at").

→ **MF-08**. And the fold that answers "is this FVG still unmitigated?" runs
straight into the Deferred table's *"until then no package folds corrections
inline"* → **SF-09**.

### 5 — Inversion FVG

Once a bullish FVG is fully filled and price closes through, the same chart
region becomes a bearish reference. This is a **new object whose birth input is
another object's invalidation**. AD-16 gives at-birth parent references that are
identity-bearing — so the inversion can cite the dead FVG's fingerprint. That
part works. What does not: the parent's `invalidated-at` is an *appended* fact
outside the parent's fingerprint, so the child's identity references a parent
record that does not itself encode the death that created the child. Two
inversions born from two successive lives of the same region are
identity-indistinguishable unless the child's own instants are identity fields
(**MF-02** again), and no ruling says whether invalidation of a parent
propagates (**SF-06**).

### 6 — Breaker block

A violated order block that price returns to with opposite polarity. Same shape
as inversion FVG, same two findings, plus the full MF-01 anchor problem (a
breaker is drawn on the *original* OB candle, potentially hundreds of bars back).
This is the concept where the missing anchor span is most visible to a trader:
without it, a governed breaker artifact cannot be drawn on a chart.

### 7 — Liquidity pool (equal highs / equal lows) + tolerance

A cluster object over two or more confirmed swing points within a tolerance.
Composition over children is exactly what AD-17 + AD-25 promise, and confirmation
is precise ("confirmed when the Nth swing lands within tolerance of the pool").

The strain is **tolerance**. "Relatively equal" in ICT is either a fixed
distance (3 pips), a fraction (0.02%), or an ATR multiple (0.15 × ATR14).

- Fixed distance: a *price difference*. AD-7 gives `Price(instrument, scale)` but
  no explicit price-delta type; a scaled integer at the instrument's scale works
  and should just be said.
- Fractional or ATR-multiple: AD-10 refuses floats in identity content, so the
  *parameter* must be a scaled integer (15 @ scale 2). Fine, and unstated.
- But the *derived threshold* is a float multiplied into an exact price, and the
  resulting pool bound is a price a trader will place a limit order at. AD-7's
  taint rule catches it: that bound is on the money path, so it must cross a
  **named conversion boundary with an explicitly stated rounding mode**. Neither
  AD-22 nor AD-25 makes that boundary contract surface for a family.

→ **MF-07**. Two builders rounding half-up vs half-even place their pool one tick
apart, and one tick is the whole question of whether the sweep fired.

### 8 — Liquidity sweep / stop hunt

*"Confirmed at the close of the first bar whose high exceeds the pool and whose
close is back below it."* Precise, causal, delay-declarable. Passes CT-17
cleanly on shape. Two sharp edges:

- **Which price swept?** Retail charts are bid-based; sell-side stops trigger on
  bid, buy-side on ask. AD-21 preserves bid and ask separately at the data layer,
  but a derived structure object's bound carries no quote-side tag and no family
  is required to declare which side it consumed. In forex with a 1-pip spread,
  bid-swept and ask-swept differ on a material fraction of sweeps.
  → **SF-03**.
- **Same-instant consumption.** The sweep confirms at a bar-close instant. A
  scalping bot decides at that same bar-close instant. AD-8 says
  *"causality tests refuse at equal instants rather than tie-break"* — read
  strictly, the bot may never consume evidence confirmed at its own decision
  instant, which forbids every bar-close entry in the system. → **SF-11**.

### 9 — BOS / CHoCH (market structure shift)

*"Confirmed the moment a bar closes beyond the most recent confirmed swing
point."* This is the cleanest pass in the entire set: precise, causal, composes
over an already-governed parent, no calendar, no second timeframe, no float. It
is worth naming in the contract as the reference exemplar, because it shows that
the law is satisfiable by real SMC objects and not just by textbook primitives.
The only shared findings that touch it are MF-01 (where is the broken swing's
level drawn?) and MF-02.

### 10 — Displacement

*A large fast directional leg.* Definition is either `range > k × ATR(n)`, or
N consecutive same-direction closes, or "an FVG exists inside the leg."

- As **CT-16**: emits a per-bar magnitude or boolean series. Legal — float
  arithmetic off the money path is explicitly permitted by AD-22/AD-7.
- As **CT-17**: a span object with a precise confirmation rule. Also legal.
- **Nothing routes it.** No clause says which contract owns a concept expressible
  as both, so one builder's `displacement` is a series and another's is an object,
  and a confluence citing "displacement" is ambiguous. → **SF-05**.
- **The ATR variant is the sharpest finding in the review.** A CT-17 family that
  needs ATR cannot import `qmf-indicators`: AD-2's default-deny says *"no package
  may depend on any package other than `qmf-core`"* and AD-25 repeats
  *"`qmf-structure` depends on `qmf-core` only in V1."* The naive resolution is
  to reimplement ATR inside qmf-structure — which directly contradicts AD-23's
  *"Batch mode wraps the reference (wrap-not-reimplement)"* and produces a second,
  non-canonical ATR whose numbers will not match the indicator package's.
  The clean resolution exists but is nowhere stated: the application computes ATR
  through CT-16, hands the **core-typed bulk series** to the family as a declared
  input, and the input's fingerprint enters the family's result label. No package
  edge required. It just has to be written down. → **MF-06**.
  (The mirror case — a CT-16 indicator scoring "distance to nearest unmitigated
  order block" — has the identical problem in the identical direction.)

### 11 — Killzones (London 02:00–05:00 NY, NY 07:00–10:00 NY, Asia 20:00–00:00)

A time-of-day scoped object, derived purely from a calendar. AD-8 already has
`SessionWindow` in the core vocabulary and market-hours calendars as extensions
that *"implement core protocols"* — so the protocol is typeable from
`qmf-structure` and `qmf-indicators` without any new package edge. **The seam is
implicitly available and never declared.** Nothing in AD-22 or AD-25 says a
configured indicator or family may take a calendar handle as an input.
→ **MF-05**.

Worse, and this one is a direct AD contradiction: AD-8 rules that
*"only the rule set + tzdata version enter fingerprints"* for any calendar-derived
artifact, and AD-21 requires split manifests to *"pin exactly one calendar
identity + version in-band."* AD-22's dedup tuple is
`formula + parameters + instrument + timeframe` — **no calendar slot**. Two
"London killzone high" instances, one under `forex-17NY v3` and one under `v4`,
compute different numbers and fingerprint identically. AD-22's dedup then merges
them into one instance, and AD-10's collision split accepts the second write
silently if bytes match or alarms only if they don't. → **MF-03**.

Also: a killzone's confirmation is degenerate — it is confirmed by the clock, not
by price. The precise-rule bar is satisfied ("confirmed at the instant the window
opens under calendar C"), but a builder reading AD-25's price-shaped seed
families may wrongly demand a market event. → **N-02**.

### 12 — Midnight open / session opens / weekly open

*"The price at 00:00 America/New_York."* Everything from concept 11 applies,
plus a sampling question the spine never rules:

- There is rarely a tick at exactly that nanosecond. First tick at-or-after? Last
  tick at-or-before? The latter is safe; the former can be minutes late on a
  Sunday.
- Which side — bid, ask, or mid? (**SF-03**; and mid is `(bid+ask)/2`, another
  unruled rounding → **MF-07**.)
- **The market may be closed at that instant.** 00:00 NY on a Sunday is inside
  the weekend gap; AD-8 correctly says *"Session and trading-day length is data;
  no consumer may assume a constant"* — so the level is genuinely undefined and
  the family must either refuse (AD-11 `invalid input`? `unavailable dependency`?
  neither is obviously right) or apply a declared gap policy.

→ **SF-08**. Smallest fix is one declared enum on any calendar-anchored level.

### 13 — Power of three / AMD (accumulation → manipulation → distribution)

A composite over a session: session-open level + a sweep of one side + a
displacement back through the open. Precisely stateable if the definitions are
pinned, and AD-25 explicitly permits composites with lineage to children.
Two composite-level rules are missing:

- **`confirmed-at` of a composite is unruled.** A builder could set it to the
  first child's confirmation — which back-dates the composite to before its own
  distribution leg existed. That is exactly the look-ahead AD-25 exists to kill,
  reintroduced through the composition door. → **SF-01**.
- **AD-17's default ordering is wrong-by-default here.** *"Multiplicity
  collections are canonically ordered by child fingerprint ascending unless the
  owning contract explicitly declares the collection order-significant."* For AMD
  the sequence *is* the concept; fingerprint-ascending order destroys it. The
  contract can declare order-significance, but the default should be inverted for
  causal structure composites, where sequence is meaning rather than an
  incidental collection. → **SF-02**.

Also needs the calendar seam for session scoping (**MF-05**).

### 14 — Multi-timeframe nest (H4 order block consumed by an M1 bot)

This is the operator's normal case, and it hits four findings at once.

- **Can a CT-16 indicator or CT-17 family take a higher-timeframe series?**
  AD-22 says "Input series" in the singular and fingerprints on one `timeframe`.
  Nothing forbids multiple inputs; nothing permits them either. → **MF-03**.
- **`timeframe` is an undefined noun that already enters identity.** The spine
  never defines what a timeframe *is*. For forex this is not pedantic: H4 candles
  anchored to 17:00 NY and H4 candles anchored to 00:00 UTC are different candles,
  and every ICT concept built on them is different. Bar aggregation/anchoring is
  not ratified anywhere, so "the H4 series" is not yet a well-defined artifact.
  → **MF-04**.
- **Alignment.** The M1 bot reads the H4 object at an instant that is not an H4
  boundary. The as-of rule (last value known at-or-before, never forward-filled
  from the future, never interpolated) is undeclared, and interpolation between
  two H4 closes is textbook look-ahead that nothing currently forbids.
  → **MF-10**.
- **The forming H4 bar.** At 09:17 the current H4 candle is incomplete. Does the
  streaming instance emit a provisional value for it? AD-22 has no provisional
  class. This is the single largest repaint surface in retail multi-timeframe
  tooling and AD-22 is silent on it. → **MF-09**.

### 15 — SMT divergence (EURUSD makes a higher high, GBPUSD fails)

Cross-instrument structure. AD-9 makes instrument identity `(venue, symbol)`,
opaque, never parsed — good, and both identities can sit in the object's
fingerprint. But:

- CT-16's tuple names **one** `instrument`, so a two-instrument configuration has
  no fingerprint. → **MF-03**.
- The two feeds tick at different nanoseconds, possibly from different venues
  with different calendars. AD-8 forbids tie-breaking for causality, so "at the
  same instant" needs a declared as-of alignment rule. → **MF-10**.

SMT is a first-rank ICT concept and today it is unrepresentable in governed
evidence. Both fixes are one sentence each.

### 16 — Premium / discount arrays and OTE (0.62 / 0.705 / 0.79)

A dealing range object (parents: one swing low, one swing high) emitting derived
levels. Lineage-wise AD-16 + AD-17 handle it: at-birth parent references are
identity-bearing, the composite is its own artifact. Three strains:

- **Every derived level is a rounding decision.** `low + 0.618 × (high − low)`
  is a float on the money path (a trader places a limit order there). AD-7
  demands a named conversion boundary with a stated rounding mode; no clause makes
  that a family's contract surface. Even equilibrium — `(high + low) / 2` with an
  odd sum — is a one-tick coin flip today. → **MF-07**.
- **Parent invalidation does not cascade, or does it?** When a higher high prints
  and the parent swing is invalidated, is the dealing range invalidated? Unruled.
  One builder leaves stale ranges alive forever; another cascades. → **SF-06**.
- **"The most recent swing high and low" is a rolling selection**, so every new
  swing mints a fresh dealing-range artifact with a fresh fingerprint. Correct
  under append-only, but it is an artifact-per-swing churn rate that AD-13's
  ladder has no structure rung to size. → **SF-14**.

### 17 — News-anchored levels / release candles

AD-8 names the news calendar as a distinct concept, AD-21 ratifies a
news-calendar recorder keyed on `(source, source-native id, revision)` — so a
family anchored to an NFP release instant gets correct revision identity by
construction (see **N-03**). Two things are missing:

- The calendar seam again (**MF-05**) — a news calendar is a third calendar kind
  and no component may declare it as an input.
- **Observation vs action is unsplit.** The inherited framework-vs-node ruling
  puts *"news windows"* in node territory. Read narrowly, a builder concludes
  that qmf-structure may not touch news at all — but *acting* on news (blackout,
  halting) is node territory while *observing* a news instant as evidence is
  ordinary data consumption. Say so. → **SF-07**. The forward-dated case matters
  too: a family that uses "next red-folder event in 12 minutes" must bind to the
  revision known at `observed-at`, not the revision known today, or a rescheduled
  FOMC leaks backwards into historical evidence.

### 18 — Volume profile / POC / liquidity void

A distribution over price, not a point, level, zone or break. AD-25 names four
seed shapes and says explicitly they are candidates with no privileged status —
but a builder reading *"a structure family is a type of chart object (swing
point, horizontal level, zone, structure break)"* may reasonably read the
parenthetical as the closed geometry taxonomy. Say that geometry is
family-declared and open (point / level / zone / span / distribution / graph).
→ **N-01**. Forex tick-volume is fine under AD-7's `Quantity(unit, scale)` with
an opaque unit. Whether a per-session profile is CT-16 or CT-17 is **SF-05**.

### 19 — Renko / range bars / tick bars / volume bars

Classic "very random experiment" territory. If `timeframe` is defined as a
`Duration` — the obvious reading, and AD-8's `Duration` is right there — then
non-time bars have no representable timeframe and the whole class is locked out
of governed evidence. → **MF-04**. The fix is to define `Timeframe` as a core
value type with a *kind* (time-period / tick-count / range / volume) plus an
anchoring rule bound to a named calendar identity, rather than leaving an
undefined noun inside a fingerprint.

### 20 — IPDA data ranges (20 / 40 / 60 trading-day lookbacks)

Lookbacks counted in **trading days**, which AD-8 correctly makes calendar-derived
and never derivable by formatting an instant. Needs the calendar seam
(**MF-05**). Also exposes **SF-04**: AD-22 requires a declared warm-up *length*
without declaring its **unit**. Bars? Ticks? A `Duration`? Trading days? The
warm-up enters the fingerprint *and* feeds AD-25's future purge/embargo widths,
so two builders using different units produce embargo widths that are wrong by
orders of magnitude and a split that leaks. Related: a session-scoped indicator
(Asian range high) re-enters not-ready every session, but AD-22 phrases warm-up
as a one-time startup phase — recurring readiness needs saying.

### 21 — Discretionary daily bias / market-maker narrative *(the designed (d))*

"The daily bias is bullish because the narrative aligns." There is no X knowable
at an instant. AD-25 routes it correctly: **stays free in research lanes, plain
Python, ungoverned, forever.** This is the taxonomy working, not failing, and it
is worth stating the consequence to the operator plainly: **a bot whose entry
depends on a discretionary read can never have governed evidence for that leg.**
That is a real trade-off he is making, and he should make it with his eyes open
rather than discovering it at the promotion gate.

---

## Part 2 — Findings

### Must-fix

#### MF-01 — `observed-at` is ambiguous, and retro-anchored objects have no anchor span

**Clause:** AD-25 — *"Every structure output carries **observed-at** and
**confirmed-at** (AD-8 instants — the bitemporal law applied to chart objects);
invalidation appends **invalidated-at**, never deletes."*

The bitemporal gloss makes `observed-at` read as *event time* (when the object
came into being on the chart); the word "observed" makes it read as *known-at*
(when the system could first derive it). For every retro-anchored ICT object —
order block, FVG, breaker, sweep, the swing that a BOS broke — these differ by a
whole displacement leg. Taking the first reading writes an evidence instant that
precedes the data justifying it: a repaint wearing a causal label, produced by a
builder who thought he was following the law. Taking the second reading leaves
the object's drawn location unrecorded, so the operator cannot render his own
chart from his own evidence, and the family cannot express "the OB candle is
bars 412–413" at all. `invalidated-at` carries the same ambiguity (detection
instant vs event instant).

**Smallest amendment.** Three sentences on CT-17:
(1) `observed-at` is defined as *the earliest instant at which the object was
derivable from causally-available data* — known-at, never event time;
(2) a family declares an **anchor span** — start instant, end instant, and price
bounds — as ordinary payload geometry, explicitly permitted to precede
`observed-at`, and explicitly excluded from every causality test;
(3) the emission invariant `anchor.start ≤ anchor.end ≤ observed-at ≤
confirmed-at ≤ invalidated-at`, with `invalidated-at` defined as the detection
instant.

#### MF-02 — Structure-object instants risk occurrence-classification, silently merging distinct market events

**Clause:** AD-16 — *"A record's **stable id is derived from its `fp1`
fingerprint** (never minted); created-at and other occurrence facts are declared
occurrence/display-only per AD-10 — so identical work from two sandboxes
deduplicates."* Plus AD-12's *"the occurrence record (when/where/by whom it ran)
is separate provenance outside identity"* and AD-10's *"an idempotent re-write
(same hash, byte-identical content …) is accepted silently."*

That machinery is designed for **computations**, where deduplicating identical
work across sandboxes is exactly right. Applied to a **chart object** it is
catastrophic: a swing high at 1.20500 on Monday and an identically-shaped swing
high at 1.20500 on Friday are two different facts about the market, and if their
instants are classified as "when it ran" they fingerprint identically and the
second is swallowed **silently**, by design, as an idempotent re-write. Equal
highs (concept 7) make this the *normal* case, not a corner. AD-10's
identity-by-default rule saves a careful builder, but AD-16's created-at
precedent and AD-12's occurrence language actively point the other way, and in
streaming mode the confirmation instant genuinely *is* "when it ran."

**Smallest amendment.** One sentence in AD-25: *a structure object's anchor span,
`observed-at` and `confirmed-at` are **identity fields**; a structure object is a
fact about the market at a time, not a computation, and its instants may never be
declared occurrence-only.* Add the mirror sentence to AD-16's header rule so the
registry does not classify them away.

#### MF-03 — CT-16's dedup tuple omits calendar identity (contradicts AD-8) and forecloses multi-input configurations

**Clause:** AD-22 — *"Instances deduplicate by content fingerprint (formula +
parameters + instrument + timeframe) — count scales with distinct configurations,
not consumers."*

Against AD-8: *"only the rule set + tzdata version enter fingerprints"* for
calendar-derived artifacts, and AD-21's *"each manifest pins exactly one calendar
identity + version in-band."* A session-scoped indicator under `forex-17NY v3`
and the same one under `v4` produce different numbers and identical fingerprints,
so AD-22's dedup **merges two non-equal instances**. That is a flat AD
contradiction with a silent-failure mode.

Against the operator's use case: the tuple names one instrument and one
timeframe, so SMT divergence (two instruments), any MTF confluence (two
timeframes), and any bid-vs-ask-vs-mid distinction (concept 8) have no
fingerprint. Read as exhaustive — and an enumerated parenthetical always is —
the tuple forecloses the majority of "very random" configurations.

**Smallest amendment.** Replace the enumeration with a rule: *an instance's
content fingerprint covers its **entire declared configuration** — formula,
parameters, and the identity of every declared input, where an input identity
includes instrument, timeframe, quote side, and (where the configuration declares
one) calendar rule-set identity + tzdata version. The list is open by
construction; a configuration element that is not in the fingerprint is a
contract defect.* Apply the same rule to CT-17.

#### MF-04 — `timeframe` is an undefined noun that already enters identity; bar anchoring and non-time bars are unruled

**Clause:** AD-22's dedup tuple and AD-24's "per configuration" classification
both key on `timeframe`; nothing in the spine defines it.

For forex this is load-bearing, not pedantic. H4 candles anchored to 17:00 NY and
H4 candles anchored to 00:00 UTC are different candles, and every order block,
FVG and sweep derived from them is a different object — the classic
"my broker's 4H doesn't match yours" problem, and it is the difference between an
ICT setup existing and not existing. Bar aggregation is not ratified anywhere:
"the H4 series" is not currently a well-defined artifact with a fingerprint.
Separately, reading `timeframe` as a `Duration` (the obvious reading given AD-8)
locks out renko, range, tick and volume bars entirely — a whole class of the
random experiments the operator asked to be able to run.

**Smallest amendment.** Define `Timeframe` as a core value type:
`(kind, size, anchoring)` where `kind ∈ {time-period, tick-count, price-range,
volume}`, `size` is an exact value (Duration or Quantity), and `anchoring` names
the calendar identity + rollover the bars are cut against (absent for non-time
kinds). Declare bar aggregation a fingerprinted derivation whose output is an
ordinary input artifact.

#### MF-05 — No component may declare a calendar as an input, so every session-scoped concept is homeless

**Clause:** AD-22 — *"`qmf-indicators` depends on `qmf-core` only"*; AD-25 —
*"`qmf-structure` depends on `qmf-core` only in V1."* Against AD-8's calendar
extensions, which *"implement core protocols"* and are injected at the
composition root.

The seam is **implicitly available** — a calendar protocol lives in `qmf-core`,
both packages depend on `qmf-core`, so both can type against it without a new
package edge. But no clause says a configured indicator or family **may declare a
calendar handle as a configuration input**, and no clause says what happens to
its identity when it does (that half is MF-03). The result: killzones, midnight
open, session and weekly opens, AMD, IPDA ranges, Asian range, and every
news-anchored level are ungoverned-only, and every builder invents his own
injection convention. For a trader whose entire methodology is time-of-day
scoped, this is the largest single blocker in the review.

**Smallest amendment.** One paragraph shared by AD-22 and AD-25: *a configured
indicator or structure family may declare typed configuration inputs beyond its
parameters — market-hours calendar, day-boundary calendar, news calendar, and
other-component output series — supplied by the composition root against
core-defined protocols. Every declared input's identity enters the configuration
fingerprint per MF-03. Declaring an input creates no package dependency edge.*

#### MF-06 — A CT-17 family cannot consume a CT-16 indicator, and the natural workaround contradicts AD-23

**Clause:** AD-2 — *"Until an inter-library edge is ratified, no package may
depend on any package other than `qmf-core`; adding an edge is a spine
amendment."* AD-25 — *"`qmf-structure` depends on `qmf-core` only in V1."*
AD-23 — *"Batch mode wraps the reference (wrap-not-reimplement)."*

Any ATR-, RSI-, or volatility-conditioned structure family (displacement, dynamic
zone width, volatility-scaled equal-high tolerance — all ordinary ICT practice)
needs indicator output. Default-deny forbids the import. The path a competent
builder will take is to reimplement ATR inside `qmf-structure`, producing a second
non-canonical ATR that will not match `qmf-indicators` — silently violating
AD-23's whole purpose. The mirror case is identical: a CT-16 indicator scoring
"distance to the nearest unmitigated order block" cannot import qmf-structure,
and confluence scoring is exactly that shape.

The clean answer needs no new edge and is already half-present: AD-22 defines the
**bulk series form in `qmf-core`**, and AD-25 already routes emissions through the
application layer. Inputs should route the same way. It simply is not written.

**Smallest amendment.** One sentence in AD-25 (mirrored in AD-22): *a family may
declare another governed component's output — indicator series or structure
objects — as a configuration input, supplied by the composition layer in the
`qmf-core` bulk/series form; the input artifact's fingerprint enters the
consumer's AD-12 result label. Consuming an output is not a package dependency
and requires no ratified edge. Re-implementing an arithmetic that CT-16 already
publishes is a contract defect under AD-23.*

#### MF-07 — Derived price levels have no ratified rounding boundary

**Clause:** AD-7 — *"Binary float is banned on the money path; a float crossing
back to Money/Price/Quantity passes a **named conversion boundary with an
explicitly stated rounding mode**."* Neither AD-22 nor AD-25 makes that boundary
contract surface for an indicator or a family.

Every one of these is a float-to-price crossing that a trader places an order at:
FVG consequent encroachment (50%), range equilibrium, OTE 0.62/0.705/0.79, ATR-
multiple zone widths, percentage tolerances for equal highs, midpoint of an order
block. `(high + low) / 2` with an odd tick sum is already a one-tick coin flip.
Two builders choosing half-up vs half-even vs toward-zero produce levels one tick
apart, which is routinely the difference between a limit order filling and not,
and between a sweep confirming and not. Worse, both results are *reproducible* —
so the disagreement never surfaces as a bug, only as two incompatible evidence
sets that AD-10 will happily treat as different artifacts forever.

**Smallest amendment.** One clause on CT-16 and CT-17: *any output value that is a
Price, or that transitively contributes to one, is produced at a **declared
conversion boundary** naming its rounding mode; the rounding mode is contract
surface entering the fingerprint. A component that emits a derived price without
declaring one fails the merge gate.*

#### MF-08 — Object interaction state has no append-only shape and no edge kind

**Clause:** AD-25's lifecycle triple (observed / confirmed / invalidated) against
AD-19's append-only law and AD-16's five ratified edge kinds
(`supersedes / promoted-from / occurrence-of / corroborates / disagrees-with`).

FVG partial fill, order-block mitigation, "unmitigated" filtering, sweep re-tests,
and the entire inversion/breaker family all depend on **how much of an object has
been consumed so far** — a monotonic attribute that evolves between confirmation
and invalidation. Today there are three options and all three are wrong:
mutate the object (contradicts append-only), mint an artifact per touching tick
(artifact explosion), or don't record it (kills the concept). No AD-16 edge kind
expresses "price interacted with this object at instant T to depth D."

**Smallest amendment.** Name a fourth lifecycle element in AD-25: *an
**interaction record** — an append-only observation referencing the object's
fingerprint, carrying instant, price, and a family-declared interaction measure —
is the only permitted way an object's state evolves. The object itself is never
mutated. An object's current state is a read-time fold over its interaction
stream, never a stored field.* Register the corresponding AD-16 edge/record kind.
This one amendment unblocks concepts 4, 5, 6, 8 and 16 simultaneously.

#### MF-09 — CT-16 has no `provisional` output class; intra-bar emission is the surviving repaint vector

**Clause:** AD-22 — output states are a number, a *"marked not-ready value"*
during warm-up, and a *"marked output gap"* for missing input. Against AD-25's
*"unconfirmed outputs are a separately-labeled evidence class, never silently
mixed."*

AD-25 built the confirmed/unconfirmed split precisely because retail structure
repaints. AD-22 did not build the equivalent, so the identical hazard on the
indicator side is undefined. A streaming instance fed tick-by-tick emits values
for a bar that has not closed; those values change until it does. The equality
law — *"Identical canonical inputs MUST produce identical outputs across modes"* —
does not settle it, because batch mode operates on closed bars and "identical
canonical inputs" quietly assumes closed-bar inputs. So the modes can be proven
equal while streaming still leaks provisional numbers into evidence, and a
multi-timeframe bot (concept 14) reading a forming H4 bar is the normal case.

**Smallest amendment.** Add a fourth output state to CT-16: *`provisional` — a
value computed over an incomplete aggregation period, marked as such, which may
never enter governed evidence and may never be compared to a batch-mode result.
An instance declares whether it emits provisional values.* This makes AD-22
symmetric with AD-25 and closes the last repaint door.

#### MF-10 — Multi-series alignment is undeclared, so cross-instrument and multi-timeframe families are ambiguous and interpolation look-ahead is not excluded

**Clause:** AD-22 — *"Input series: the bulk form of exact values is defined in
`qmf-core`"* (singular, one series). AD-8 — *"Causality is compared on instants
only"* and *"causality tests refuse at equal instants rather than tie-break."*

The moment a component takes two series — H4 + M1, EURUSD + GBPUSD, price + a
news schedule — it must combine values that arrive at different instants. Three
plausible rules exist and one of them is look-ahead: as-of last-known-at-or-before
(safe), next-value-forward (look-ahead), linear interpolation (look-ahead, and the
default in most pandas-shaped retail code the operator will borrow from). Nothing
forbids either bad option. CT-17's precise-rule bar gives structure families some
forcing function; CT-16 has none at all.

**Smallest amendment.** One clause on both contracts: *a component consuming more
than one input series declares its alignment rule; only **as-of last value known
at or before the evaluation instant** is permitted for governed evidence. Forward
fill from a future value and any interpolation across the evaluation instant are
`policy rejection` refusals. The alignment rule is contract surface entering the
fingerprint.*

#### MF-11 — AD-24's light/heavy budget binds CT-16 only, leaving the heavier of the two families unbudgeted on the live path

**Clause:** AD-24 — *"**Binds:** CT-16; qmf-indicators; the AD-13 ladder"*, and
*"a configured **indicator** is **light** iff it declares AND benchmark-proves all
four bounds."* AD-25 says nothing about cost, state size, or live-path placement.

AD-24's stated purpose is *"Prevents: heavy computation on the live decision
path."* A structure family is routinely the more expensive of the two: "scan the
last 500 bars for unmitigated order blocks and rank them" is an ordinary ICT
screen, it runs per tick, it holds an unbounded live set of active zones, and
nothing in the spine requires it to declare a bound or prove one at the merge
gate. On a 40-bot node with a ~1-second scalping path, the first family that
forgets is the first outage. Leaving the heavier half of the computation
unbudgeted defeats the AD's own Prevents clause.

**Smallest amendment.** Extend AD-24's Binds line to CT-17 and restate the four
bounds for families: per-update cost within the live-path rung; bounded declared
live-object-set size; bounded declared scan/lookback window; synchronous
availability. Same benchmark policing, same merge-gate refusal for a failed light
claim.

### Should-fix

#### SF-01 — A composite's `confirmed-at` is unruled

AD-25 permits composites (*"composable per AD-17 (a composite is its own artifact
with lineage to its children)"*) but never says when one is confirmed. A builder
setting a composite's `confirmed-at` to its earliest child's back-dates the whole
object, reintroducing look-ahead through the composition door. **Fix:** one
invariant — *a composite's `confirmed-at` is the maximum of its children's
`confirmed-at` and may never precede any child's; a composite's `observed-at` is
the maximum of its children's `observed-at`.*

#### SF-02 — AD-17's default child ordering erases causal sequence in structure composites

*"Multiplicity collections are canonically ordered by child fingerprint ascending
unless the owning contract explicitly declares the collection order-significant."*
For AMD, for a sweep-then-displacement pair, for any narrative composite, the
sequence *is* the meaning; fingerprint-ascending order destroys it and the default
silently applies to whoever forgets. **Fix:** invert the default for CT-17
composites — *children of a causal structure composite are order-significant by
default; a family must explicitly declare a collection unordered.*

#### SF-03 — Price carries no quote-side tag

AD-7's `Price(instrument, scale)` has no bid/ask/mid discriminator, and AD-21
preserves bid and ask separately only at the data layer. A sweep confirmed on the
bid and a sweep confirmed on the ask are different events at a 1-pip spread, and
sell-side vs buy-side stops genuinely trigger on different sides. Input-series
fingerprints prevent a *silent* merge (different input artifacts → different
labels), so this is not MF-grade — but nothing makes the family *declare* which
side its logic assumes, which is what a reader needs. **Fix:** add a declared
`quote side / series kind` (bid / ask / mid / last) to input-series identity, and
require families to declare it; define `mid` as a derived series with a stated
rounding mode (MF-07).

#### SF-04 — Warm-up has no declared unit and is phrased as one-time

AD-22 — *"Every configured indicator declares its **warm-up length** as contract
surface entering its AD-10 fingerprint."* Length in bars, ticks, trading days, or
`Duration`? It enters a fingerprint and feeds AD-25's future purge/embargo widths,
so a unit mismatch produces embargo widths wrong by orders of magnitude and a
split that leaks. Separately, session-scoped indicators (Asian range, daily
opening range) re-enter not-ready every session, which "warm-up" as a startup
phase does not describe — and it interacts with the snapshot/restore promise
(*"restart re-warm never replays a day"*), because a session-reset instance
restarting mid-session genuinely does need that session's data back. **Fix:**
type warm-up as a declared exact quantity with an explicit unit, and state that
readiness is recurring — an instance may declare a calendar-anchored reset
boundary that re-enters not-ready.

#### SF-05 — No routing test between CT-16 and CT-17

Displacement, volume profile, "distance to the nearest OB," and any score-shaped
concept are expressible as either a series or an object, and nothing routes them.
Two builders produce incompatible artifacts for the same word, and a confluence
citing the word is ambiguous. **Fix:** state the test — *if the output is a value
per evaluation instant, it is CT-16; if it is a bounded thing with a birth, a
confirmation and an invalidation, it is CT-17* — and make explicit that either may
consume the other (MF-06).

#### SF-06 — Parent invalidation cascade is unruled

When the swing high that defines a dealing range is invalidated, is the range
invalidated? When an order block dies, do its derived premium/discount levels die?
Unruled; one builder cascades, another leaves stale objects alive forever, and
both are defensible. **Fix:** rule it either way in one sentence — recommended:
*invalidation never cascades automatically (append-only, no action at a distance);
a family declares its own invalidation predicate, which may reference a parent's
lifecycle facts. Readers may compute cascade at read time from lineage edges.*

#### SF-07 — News evidence: the observation/action split is unstated

The inherited framework-vs-node ruling puts *"news windows"* in node territory,
which a builder can read as "qmf-structure may not touch news at all." **Fix:**
one sentence — *acting on news (blackout, halting, sizing) is node territory;
observing a news instant or release as evidence is ordinary input consumption and
is permitted to governed families, bound to the revision known at `observed-at`.*

#### SF-08 — No point-in-time price sampling policy, including inside session gaps

"The price at 00:00 NY" needs a declared sampling rule (last-known-at-or-before is
the only causal one) and a declared behavior when the instant falls inside a
weekend gap or holiday — AD-8 rightly forbids assuming a constant session length,
which makes the undefined case common rather than exotic. **Fix:** a declared enum
on calendar-anchored levels: `{last-known-at-or-before, refuse}` plus a gap policy
`{refuse, nearest-open-instant, carry-previous-session}`, all fingerprinted.

#### SF-09 — The deferred annotation read-resolution rule now blocks the most ordinary ICT query there is

Deferred table: *"Annotation read-resolution rule | … until then no package folds
corrections inline."* Under MF-08's interaction-record shape, "is this order block
still unmitigated?" is exactly a read-time fold — so the deferral does not merely
postpone a data-store detail, it makes the framework unable to answer the question
an ICT trader asks most. **Fix:** scope the deferred item explicitly to include
**lifecycle/interaction folds**, and pull that half forward into the data sitting
rather than documentation time.

#### SF-10 — CT-17 has no state-bound or snapshot/restore obligation, asymmetric with AD-22

AD-22 gives indicators *"declares its state bound and supports snapshot/restore so
restart re-warm never replays a day."* AD-25 gives families nothing — yet a family
is far more stateful, holding a live set of active zones, pools and ranges. AD-25's
*"live in-memory use persists nothing"* means a restart cold-starts and must
re-scan history to rebuild every active object. Restart is the trader's most
frequent incident (five-hats T-7). **Fix:** extend AD-22's state-bound and
snapshot/restore sentence verbatim to CT-17.

#### SF-11 — Same-instant confirmation and consumption collide with AD-8's refuse-at-equal-instants rule

AD-8: *"causality tests refuse at equal instants rather than tie-break."*
AD-25: *"Evidence consumed as confirmed uses confirmed-at."* A bar-close
confirmation and a bar-close decision share an instant, so read strictly, every
bar-close entry in the system is refused. **Fix:** state the consumption rule
explicitly — recommended: *a decision at instant T may consume evidence with
`confirmed-at ≤ T`; equality is permitted for consumption and is not look-ahead.
The refuse-at-equal rule governs causality **tests between two derived
artifacts**, not evidence consumption by a decision.*

#### SF-12 — Mixed-kind composites have no ratified home, and the deferred Bot sitting will assume homogeneity

A real confluence mixes an indicator series, a structure object, and a time
window. AD-25's composites are family-to-family; AD-17's vocabulary is
Bot-level (confluence / level / trigger / confirmation) and binds *"qmf-registry;
the future Bot/QML schema sessions."* Nothing today says a composite's children
may be of **different governed kinds**. **Fix:** one sentence in AD-17 now, so the
deferred sitting inherits it — *composition operates over artifact fingerprints of
any governed kind; a composite declares its children's kinds and may mix indicator
results, structure objects, and calendar windows.*

#### SF-13 — A cheap look-ahead assertion is available now and would not wait for the deferred gate

Deferred table: *"Look-ahead registration gate … Operator-deferred to the
backtesting sitting, consequence accepted: artifacts registered before then carry
no causality evidence."* Accepted — but that leaves AD-25's entire law on the
honor system for V1. A local, emission-time assertion needs no registry, no gate,
no sitting: **`confirmed-at ≥ observed-at ≥ the maximum evidence-time of every
input actually consumed`**, checked inside the component and refused as
`invalid input`. That catches the great majority of accidental look-ahead —
including MF-01's back-dated anchor and SF-01's back-dated composite — at
essentially zero cost. **Fix:** add it as an AD-25 emission invariant now.

#### SF-14 — Structure artifact volume has no rung on the AD-13 ladder

Rolling-selection parents ("the most recent swing high/low") mint a fresh artifact
per new swing; interaction records (MF-08) mint one per meaningful touch. AD-13's
ladder is expressed in *"framework-native units per package (calls/s, series
length, artifact count)"* but no structure rung exists and no sitting owns sizing
it. **Fix:** name the CT-17 rungs when the family contract is written — active
object set size, objects minted per bar, interaction records per bar — alongside
AD-24's live-path rung (MF-11).

### Notes

#### N-01 — The four seed shapes read as a closed geometry taxonomy

AD-25 — *"A structure **family is a type of chart object** (swing point,
horizontal level, zone, structure break)."* The "no privileged families" clause
saves the *set* of families, but the parenthetical still reads as the closed set
of *geometries*, which excludes distributions (volume profile), spans
(displacement legs), and graphs (linked structure chains). **Fix:** say geometry
is family-declared and open.

#### N-02 — Calendar-derived objects have degenerate confirmation, and that is fine

A killzone is confirmed by the clock, not by price. The precise-rule bar is met
("confirmed at the instant the window opens under calendar C"), but a builder
reading four price-shaped seed families may wrongly demand a market event. One
sentence prevents it.

#### N-03 — Input revisions and corrections are already handled by construction — say so

AD-12's result label carries input fingerprints; AD-21 keys intake on
`(source, source-native id, revision)`; AD-5 mints a new artifact with a lineage
edge on re-derivation. Together these mean a structure object computed on a revised
bar automatically gets a different label rather than silently changing — a genuinely
strong property that ICT tooling universally lacks. Name it in CT-17's rationale so
a builder does not invent a second revision mechanism.

#### N-04 — The research lane is genuinely unblocked, and that is the review's main positive result

All 21 concepts pass test (a) with no strain. AD-22's *"Custom indicators are
authorable … as plain Python outside governed evidence; conformance is required
only to enter governed evidence"* and AD-25's *"Imprecise concepts stay free in
research lanes"* are doing real work. The operator's "some experiments might be
very random" requirement is satisfied at the research end; every finding above is
at the promotion end.

#### N-05 — Fractal degree/rank needs no new machinery

Swing-of-degree-N, structure-within-structure, and the operator's own "a level is a
small fractal inside confluence → bot → Book → node" framing are all handled by an
ordinary parameter plus AD-17 composition. No amendment needed; worth an explicit
example in the contract because it is the framing the operator thinks in.

---

## Part 3 — The "very random" confluence, walked end to end

The stress case, stated as the operator would state it:

> *Enter long on M1 when price is inside a **4H bullish order block** that was
> confirmed after a **London-killzone liquidity sweep** of the **Asian session's**
> equal lows, while **M15 RSI(14) on mid-prices** is below 40, within **30 minutes
> after NY midnight open**, with **EURUSD showing SMT divergence against GBPUSD**,
> and **M5 displacement above 1.5 × ATR(14)**.*

Walk it against the contracts:

| Ingredient | Contract it needs | Status today |
|---|---|---|
| 4H order block | CT-17 zone family | Blocked: MF-01 (anchor), MF-02 (identity), MF-04 (what is "4H"?) |
| "price is inside it" now | interaction / read-time state | Blocked: MF-08, SF-09 |
| London killzone scoping | calendar input | Blocked: MF-05, MF-03 |
| Asian session equal lows | calendar input + tolerance | Blocked: MF-05, MF-07 |
| Liquidity sweep confirmation | CT-17 — clean rule | Passes; SF-03 (which side?), SF-11 (same instant) |
| M15 RSI(14) | CT-16 + AD-23 canonical arithmetic | Passes |
| …on **mid** prices | derived series + rounding | Blocked: SF-03, MF-07 |
| "within 30 min after NY midnight open" | calendar-anchored level + Duration | Blocked: MF-05, SF-08 |
| SMT vs GBPUSD | two-instrument configuration | Blocked: MF-03, MF-10 |
| M5 displacement > 1.5 × ATR14 | CT-17 family consuming a CT-16 series | Blocked: MF-06, MF-07, SF-05 |
| M1 evaluation over 4H/M15/M5 inputs | multi-timeframe alignment | Blocked: MF-10, MF-09 (forming bars) |
| The confluence itself | mixed-kind composite | No home: SF-12 (deferred Bot sitting) |
| Live-path cost of all of it | AD-24 budget | Indicators budgeted; structure unbudgeted: MF-11 |

**Result: two of thirteen ingredients are expressible in governed evidence
today.** Every other one is blocked by a finding above, and — this is the
important part — **none of them is blocked by a design decision the operator would
want reversed.** They are blocked by things nobody has written down yet. The
eleven must-fixes are, in total, roughly fifteen sentences of contract surface.
Written before qmf-indicators and qmf-structure are coded, they cost nothing.
Written after, they are format-version mints on every artifact already produced.

The one thing this experiment genuinely cannot have is a discretionary leg
(concept 21) — and that is the system working as the operator agreed it should.

---

## Part 4 — What holds up

Stated deliberately, because a review that only lists holes misrepresents the
spine:

1. **AD-25's confirmation-rule bar is the correct kill for retail repainting**, and
   it survives contact with real ICT concepts. BOS/CHoCH, liquidity sweeps, FVGs
   and swing points all have genuinely precise, causally-knowable confirmation
   rules — the law is satisfiable, not aspirational. The concepts it excludes
   (ZigZag-as-drawn, discretionary bias) are precisely the ones that should be
   excluded.
2. **"No privileged families" is exactly right and is doing real work.** Every one
   of the 21 concepts is an operator-authored family under identical law; the seed
   four get no advantage. The operator's "I don't want to be locked in under any
   circumstance" is honored structurally, not rhetorically.
3. **The research/governed split is clean.** Test (a) passes 21/21 with no strain.
   Nothing about AD-22 or AD-25 makes an experiment harder to *try*.
4. **AD-22's two-mode equality law is the right shape** — research computed on the
   same numbers the live path sees is a discipline most retail stacks never impose
   — and MF-09 is a completion of it, not an objection to it.
5. **AD-23's reference-upgrade-mints-a-contract-version rule is unusually mature**,
   and the TA-Lib 0.7.1 period=1 precedent proves it against a real event.
6. **Revision handling is already correct by construction** (N-03), which is a
   property ICT tooling essentially never has.
7. **AD-7's taint framing survives the domain.** Every ICT price-level derivation
   the review tested is correctly caught as money-path; MF-07 is about naming the
   boundary, not about the boundary being wrong.

---

## Part 5 — Minimal patch set

Eleven amendments, all additive, all before CT-16/CT-17 are written:

**On CT-17 / AD-25**

1. Define `observed-at` = known-at; add **anchor span** as payload geometry
   permitted to precede it; add the ordering invariant including `invalidated-at`
   as a detection instant. *(MF-01)*
2. Declare anchor span, `observed-at` and `confirmed-at` **identity fields**, never
   occurrence-only; mirror in AD-16. *(MF-02)*
3. Name the **interaction record** as the only permitted state evolution; register
   the AD-16 edge/record kind; state that current state is a read-time fold.
   *(MF-08)*
4. State that families may declare **other components' outputs and calendars as
   configuration inputs**, supplied by the composition layer in core bulk form,
   with no package edge; re-implementing a published CT-16 arithmetic is a defect.
   *(MF-05, MF-06)*
5. Extend **AD-24's four bounds to CT-17**; add the CT-17 rungs to AD-13.
   *(MF-11, SF-14)*
6. Add the emission-time look-ahead assertion, composite `confirmed-at` law,
   composite order-significance default, and the non-cascading invalidation rule.
   *(SF-13, SF-01, SF-02, SF-06)*

**On CT-16 / AD-22**

7. Replace the enumerated dedup tuple with **whole-declared-configuration**
   identity, explicitly including calendar identity + tzdata version, quote side,
   and every input's identity. *(MF-03)*
8. Add the **`provisional`** output state for incomplete aggregation periods,
   barred from governed evidence. *(MF-09)*
9. Declare the **as-of alignment rule** for multi-series inputs; forbid forward-fill
   and interpolation across the evaluation instant. *(MF-10)*
10. Type **warm-up** with an explicit unit and state that readiness is recurring.
    *(SF-04)*

**Shared / core**

11. Define **`Timeframe`** as a core value type with kind + size + calendar
    anchoring, and make bar aggregation a fingerprinted derivation; add the
    **declared rounding boundary** for every derived price; add **quote side** to
    input-series identity. *(MF-04, MF-07, SF-03)*

Remaining should-fixes (SF-05 routing test, SF-07 news observation/action split,
SF-08 sampling policy, SF-09 deferral scope, SF-10 snapshot/restore for CT-17,
SF-11 same-instant consumption, SF-12 mixed-kind composites) are one or two
sentences each and can land in the same pass.
