---
title: 'Edge-case review — general TA / quant / crypto lens'
type: architecture-review
lens: general-trading-edge-cases
target: ARCHITECTURE-SPINE.md (QMF V1 Foundation)
focus_rulings: [AD-22, AD-23, AD-24, AD-25]
context_rulings: [AD-7, AD-8, AD-9, AD-10, AD-11, AD-12, AD-13, AD-15, AD-16, AD-17, AD-19, AD-21]
reviewer_stance: 'Deliberately school-neutral. General forex, general crypto, general market structure, classic TA, statistical/quant retail. No tradition privileged.'
created: '2026-08-20'
---

# Edge-case review — general TA / quant / crypto lens

## Verdict

**The shape is right; the vocabulary is too narrow.** AD-22/23/24/25 get the *hard* things right —
bitemporal chart objects, a precise-confirmation bar, a mode-equality law, budget-declared
light/heavy, no privileged families. What they get wrong is smaller and more mechanical: the
indicator contract's **identity tuple is a closed four-slot key** (`formula + parameters +
instrument + timeframe`) and its **input form is a single exact series**. Almost every general
trading experiment that is not "one classic indicator on one instrument on one time-based
timeframe" collides with one of those two clauses. Nine findings are must-fix; every one of them
has a small, local amendment. None requires a new architectural layer.

The single most consequential omission: **AD-25 gives chart objects an observed-at/confirmed-at
law and AD-22 gives indicator outputs nothing equivalent.** Multi-timeframe repainting — the most
common look-ahead bug in all of retail TA — is unguarded on the indicator side, and GAP-0016 (the
causality gate) is deferred, so nothing else catches it either.

## How to read this

Each concept is tested on four questions:

- **(a)** freely researchable in plain Python? (the ungoverned lane AD-22/AD-25 both bless)
- **(b)** expressible as a CT-16 indicator?
- **(c)** expressible as a CT-17 structure family with a precisely-stateable causal confirmation rule?
- **(d)** or does it break/strain the contracts?

Severity tiers, as briefed:

- **must-fix** — a legitimate general experiment is impossible, or an AD is contradicted.
- **should-fix** — possible but ambiguous; two competent builders would guess differently.
- **note** — worth recording; includes places where the spine already gets it right and nobody
  should "fix" it.

Findings are labelled `F-n` (must-fix), `S-n` (should-fix), `N-n` (note) and collected in the
tables at the end. The concept walk cross-references them.

---

## Concept walk

### C-1 — Rolling correlation between two instruments

*EURUSD vs DXY; BTC vs ETH; a risk-on filter reading SPX against gold.*

**(a)** Yes, trivially. **(b) No.** **(d) Breaks.**

Two clauses block it. First, AD-22's dedup key: instances "deduplicate by content fingerprint
(**formula + parameters + instrument + timeframe**)". Singular instrument. A two-instrument
indicator has no expressible identity — a builder must either pick one instrument arbitrarily
(two different correlations then share a fingerprint and silently dedup into one another across
sandboxes, exactly the failure AD-10 exists to prevent) or smuggle the second instrument into
"parameters", which is undeclared and unenforced. Second, AD-22's input clause is written in the
singular: "Input series: the **bulk form** of exact values … int64 arrays plus out-of-band
scale/metadata".

There is a third, quieter problem underneath: **alignment**. EURUSD and DXY do not tick together;
BTC and ETH do not print bars at identical instants across two venues. Correlating them requires a
join rule (as-of last-known, forward-fill to a reference clock, intersect-only, resample). That
choice **changes the numbers**, so it is identity-bearing — and no AD anywhere states an alignment
rule or requires one to be declared. AD-8 is correct that "causality is compared on instants only",
which gives the *legal* basis for an instant-level join, but no contract asks for the policy.

AD-22's "exactly one feeder" also reads ambiguously here. If "feeder" means the single writer
object that pushes updates (AD-15's `WriterId` holder), a multi-input instance is fine — the
application fuses both streams and feeds one instance. If it means one input stream, multi-input
streaming is banned outright. Two builders would read this differently.

→ **F-1**, **S-3** (channel metadata), **N-2**.

### C-2 — Spread and pair ratios; and the chaining problem

*EURUSD/GBPUSD, ETH/BTC, a beta-weighted hedge spread, gold priced in EUR.*

**(a)** Yes. **(b) Partially — the first hop only.** **(d) Breaks at the second hop.**

Computing the ratio series is fine: AD-22 permits float arithmetic off the money path, and the
output is an analytic float series whose identity comes from its AD-12 result label (AD-10's
float-bearing-artifact carve-out). Good.

What breaks is **chaining**, and chaining is the normal case in all of TA, not an exotic one:

- Bollinger Bands on a spread, RSI of a ratio, ATR of a synthetic.
- MACD is definitionally EMA-of-EMA; RSI-of-RSI, ADX-of-anything, smoothed stochastics.
- Any z-score, any normalisation, any "indicator of an indicator" experiment.

AD-22 states the input form as exact int64 bulk series and adds "**one representation
workspace-wide**". An indicator's output is an analytic *float* series. Under a literal reading,
an indicator output is not a legal indicator input, and there is no stated path from one to the
other. AD-12 already supplies the identity mechanism ("input fingerprints" are part of every
result label) — the contract just never says chaining is permitted.

A related sub-case: the synthetic instrument. `Price(instrument, scale)` (AD-7) ties a price to an
instrument, and AD-9 makes instrument identity `(venue, venue's own symbol)`, operator-minted and
opaque. A computed spread has no venue and no symbol. Minting a fake `Instrument` for every
synthetic would pollute the registry and violate the spirit of AD-9. The right answer is a
**derived-series identity** — an artifact identified by its result label, usable wherever an input
series is expected, without pretending to be an Instrument.

→ **F-2**.

### C-3 — Alternative bar types: renko, range, tick, volume, dollar, imbalance bars

*Renko and range bars are retail-standard; tick/volume/dollar/imbalance bars are the standard
recommendation in modern quant literature.*

**(a)** Yes. **(b) No — cannot be identified.** **(c) Partially, and interestingly.** **(d) Breaks.**

The word **"timeframe"** appears in AD-22's dedup key and again in AD-24's per-configuration rule.
It is not defined anywhere in the spine, and it is not in the glossary. It reads as, and will be
implemented as, a time-based bar interval. Renko has no timeframe — it has a brick size in price.
Tick bars have a count. Volume bars have a quantity threshold. Dollar bars have a notional
threshold. Range bars have a range. None of these fit a slot called "timeframe", so none of them
can be fingerprinted, so none can enter governed evidence.

**Warm-up is the deeper problem.** AD-22 requires every configured indicator to declare a warm-up
length as fingerprinted contract surface, and AD-24 makes a "bounded declared evidence window (its
warm-up)" one of the four light-tests. A 20-bar warm-up on a 5-minute chart is 100 minutes. A
20-brick warm-up on a 25-pip renko is *unbounded in time* — it might be two minutes or three weeks.
AD-25 then feeds warm-up and confirmation delay into "future split purge/embargo widths", and
AD-21 requires split boundaries to be explicit stored TradingDates or instants — i.e. **time**. The
conversion from a bar-count warm-up to a time-width embargo is undefined, and for event-driven
bars it does not exist as a constant. AD-8 already says the right thing in the adjacent case
("session and trading-day length is data; no consumer may assume a constant") — the same discipline
needs to reach bar counts.

**(c)** is the surprise: a renko brick is a rather good CT-17 chart object. It is a discrete box
with a precise birth rule ("confirmed the moment price closes 25 pips beyond the prior brick's
boundary" — knowable at that instant), it never repaints once confirmed, and it has a lifetime.
AD-25 would model it cleanly. But then downstream indicators must run **on the structure family's
output**, which is the chaining hole of C-2 crossed with the package-boundary silence of C-20.

There is also no named home for the **bar builder** itself. It is not an indicator (its output is a
bar series, not a value per input sample), it is not obviously a chart object, and qmf-data's remit
is "contracts, normalization, validation, idempotent intake" of source facts, not derived
aggregation.

→ **F-3**, **N-7**.

### C-4 — Trendlines and channels (sloped objects)

*Classic trendlines, Andrews pitchfork, regression channels, sloped supply/demand rails.*

**(a)** Yes. **(c) Blocked by an identity contradiction.** **(d) Breaks.**

AD-25 is explicitly non-privileging ("the V1 seed candidates … are candidates only"), so nothing
*forbids* a sloped family. But a sloped object is a function of time: `price = a + b·t`. Its
defining parameter is a **slope** — price per unit time — which is a non-integer ratio.

AD-10 states flatly: "all identity numerics are integers … **floats are refused in identity
content**." So a trendline's slope cannot be an identity field. Exclude it and two trendlines
through different points fingerprint identically — a genuine, silent identity collision in a
system whose merge model (AD-16: "identical work from two sandboxes deduplicates") depends on
fingerprints being complete.

Second collision: AD-7's money-path taint. "Any value that transitively contributes to an order
quantity, price, P&L, or balance is on the money path regardless of which package computed it."
A bot that enters when price touches the trendline is placing an order at the trendline's evaluated
level. That level is a float derived from a slope, crossing back into `Price` — which AD-7 permits
only through "a **named conversion boundary** with an explicitly stated rounding mode". The
mechanism exists; nobody has named the boundary for structure or indicator outputs, and nothing
says a CT-17 family is permitted to declare one.

The fix is clean and preserves both ADs: identify a sloped object by its **anchors** — two
`(instant, exact Price)` pairs, both integers, both fingerprintable — plus a declared, versioned
**evaluation rule** (linear-in-nanoseconds, log-linear, etc.). Slope becomes derived, never stored,
never in identity. Evaluation at time `t` crosses a named AD-7 boundary with a declared rounding
mode and target scale.

→ **F-6**, **S-11**.

### C-5 — Fibonacci retracements and extensions

*Objects derived from other objects — the composition case.*

**(a)** Yes. **(c) Yes in structure, blocked in parameters.** **(d) Strains.**

The good news: AD-17 already supplies exactly the right machinery — "components may compose
(several levels forming one composite level — a composite is its own artifact with lineage to its
children)". A Fib set anchored on a confirmed swing leg is a composite with lineage to two swing
points. And its confirmation rule is precisely stateable: **confirmed at the instant the anchoring
swing leg is confirmed.** No look-ahead, no repainting. AD-25 handles it.

Two things break:

**Parameters.** 0.382, 0.5, 0.618, 1.272, 1.618. These are the object's identity — a 61.8%
retracement is not a 50% retracement — and AD-10 refuses floats in identity content. This is the
same defect as C-4's slope, and it generalises far past Fibonacci: Bollinger's 2.0 or 2.5 standard
deviations, a 0.05 significance level, a 1.5× ATR multiple, a 70% value area, an EMA alpha, a 0.3%
tolerance band. **The spine has no exact non-integer number type**, and every general TA
parameter set needs one. Scaled integers with a declared scale (618 at scale 3), or an explicit
numerator/denominator, solve it entirely — and are already the AD-7 idiom.

**Cascade.** If the anchoring swing is later invalidated (AD-25 appends `invalidated-at`), what
happens to the Fib set derived from it? AD-25 is silent on **invalidation propagation through
composites**. One builder cascades, another leaves the child standing, and the two produce
different evidence from identical inputs.

→ **F-6**, **S-4**.

### C-6 — Pivot points (classic, floor, Camarilla, Woodie, DeMark)

*Session- or day-anchored levels from the prior period's H/L/C — universal in forex and futures retail.*

**(a)** Yes. **(b) Blocked twice.** **(d) Breaks.**

A daily pivot needs the **calendar**: which instants belong to "yesterday". AD-8 is emphatic that
trading date "derives only from a calendar, never from formatting an instant", and that
`TradingDate` carries its calendar identity and version in-band.

CT-16 has no calendar. AD-22's input form is "int64 arrays plus out-of-band scale/metadata" — no
calendar, and no statement that a non-series input of any kind is permitted. Mechanically the
injection is *legal*: calendar extensions "implement core protocols" (AD-8, dependency diagram), so
an injected object typed by a core protocol crosses no import edge and does not violate AD-22's
"qmf-indicators depends on qmf-core only". But nothing says an indicator may take one.

The sharper failure is **identity**. AD-8: "only the rule set + tzdata version enter fingerprints",
and AD-5: "re-deriving a value under a newer calendar/tzdata version produces a new artifact with
its own fingerprint and a lineage edge". AD-22's dedup key has no calendar slot. So daily pivots
computed under `forex-17NY v3` and daily pivots computed under a 00:00-UTC rollover — *different
numbers* — fingerprint identically and silently merge. That is a direct contradiction between
AD-22's key and AD-8's fingerprint rule, and it is not hypothetical: 17:00 New York versus 00:00
UTC is precisely the forex-versus-crypto split this framework must span.

→ **F-4**.

### C-7 — VWAP, session VWAP, anchored VWAP; and the volume-units question

*The most-watched intraday level in equities and crypto; increasingly standard in forex.*

**(a)** Yes. **(b) Yes arithmetically, but AD-24 misclassifies it.** **(d) Strains hard.**

VWAP is O(1) per update: two running accumulators (Σ price·volume, Σ volume). Bounded state, trivial
per-update cost, synchronously available. Three of AD-24's four light-tests pass instantly.

Test (3) fails: "bounded declared **evidence window** (its warm-up)". Session VWAP's window is
"since session open", which is not a constant — AD-8 itself forbids assuming it is ("session and
trading-day length is data; no consumer may assume a constant"). Anchored VWAP is worse: its window
is unbounded by construction, since the anchor may be any past event. By AD-24's letter, **AVWAP is
heavy** — pushed off the trading path to the MIS/research side, computed once and fanned out. For a
level a scalper reads live, that is functionally fatal.

The rule conflates two genuinely different bounds. A running accumulator has **bounded state** and
an **unbounded window**. The same misclassification hits cumulative volume delta, session high/low,
running drawdown, all-time-high distance, ATR-since-anchor, and every "since X" statistic in
general use. Splitting bound (3) into *bounded state* (already bound 2) and *either a bounded window
or a declared O(1) anchor-reset rule* fixes it without weakening the gate — the merge-gate benchmark
still polices the latency claim.

The window bound exists partly to feed AD-25's purge/embargo widths. An anchored indicator can serve
that by declaring its **anchor kind** instead, so the embargo is computed from the anchor rather
than from a window.

**Volume units.** AD-7's `Quantity(unit, scale)` with an opaque unit is the right primitive and
absorbs the forex/crypto split correctly — forex tick-volume is a dimensionless count, spot crypto
volume is base-asset quantity, perp volume is often quote-notional, and all three are different
units. But nothing states that a bulk series *has* a volume channel, or that a channel declares its
kind. VWAP on tick-volume and VWAP on real volume are different numbers under the same name, and
under AD-22's key they share a fingerprint.

→ **F-8**, **S-3**.

### C-8 — Volume profile and market profile (TPO)

*POC, value area high/low, HVN/LVN, developing profile.*

**(a)** Yes. **(b) Output shape undefined.** **(c) Partly — the value area is a zone.** **(d) Strains.**

The output is not a value per sample. It is a **distribution over price bins**: for a given period,
a vector indexed by price. AD-22 never states an output shape at all — it speaks of "outputs" and a
"marked not-ready value" and leaves arity entirely open. That is under-specification rather than
prohibition, but the equality law ("identical canonical inputs MUST produce identical outputs across
modes", enforced as a tier-2 contract test) cannot be implemented against an unstated output shape.

Notice that **multi-output is already mandatory today and still unstated**: AD-23 pins TA-Lib as
canonical, and TA-Lib's MACD returns three series, BBANDS three, STOCH two, AROON two, MAMA two,
HT_PHASOR two. A builder wrapping BBANDS has no contract guidance on how three channels are
represented, named, or fingerprinted.

Volume profile also straddles CT-16 and CT-17. The histogram is indicator-shaped. The **value area**
and the **POC** are chart objects — a zone and a level, with an observed-at and a lifetime, exactly
AD-25's vocabulary. The spine draws no line between the two contracts, so a builder must guess.

Bin width is a price-scaled parameter, and a POC used to place an order is on the money path.

→ **S-1**, **S-2**.

### C-9 — Chart patterns: head-and-shoulders, triangles, wedges, flags, double tops

*Explicitly named in the spine's Deferred table as addable family-by-family.*

**(a)** Yes. **(c) Yes on confirmation; strains on revision.** **(d) Strains.**

Confirmation is fine and this deserves saying plainly, because it is the thing AD-25 was built for:
H&S is "confirmed the moment price closes beyond the neckline" — X is knowable at that instant, no
repainting, no look-ahead. Triangle breakouts are the same modulo sloped-object support (C-4).
Double tops confirm at the intervening-low break. These all clear AD-25's precise-rule bar.

**Subjective parameters are a non-problem** and should not be "fixed": how closely shoulders must
match, how many touches make a trendline, minimum pattern duration — these are declared parameters
entering the fingerprint. Two operators with different tolerances produce two distinct, separately
identified families. That is correct behaviour and AD-25 already delivers it.

What strains is **revision**. A forming triangle's apex moves with every new bar. The object a
human calls "the same triangle" at 10:00 and at 14:00 has different anchors. AD-25 gives
observed-at, confirmed-at, invalidated-at — but **no refit or refinement concept**, and AD-16's edge
kinds (supersedes, promoted-from, occurrence-of, corroborates, disagrees-with) live in the registry,
which AD-25 says qmf-structure reaches only through the application layer. So a builder tracking a
forming pattern across 400 bars either emits 400 artifacts with 399 supersedes edges, or emits
nothing until confirmation and thereby loses the original observed-at that made the object
interesting. Neither is stated; both are defensible; they produce different evidence.

→ **S-5**, **N-6**.

### C-10 — Candlestick patterns

*Engulfing, doji, hammer, morning star, three-line strike — 61 CDL functions in TA-Lib.*

**(a)** Yes. **(b) Yes — by force.** **(c) Arguably better.** **(d) Two distinct problems.**

Because AD-23 pins TA-Lib as canonical arithmetic and AD-22 says batch mode wraps the reference,
candlestick patterns arrive **as indicators by construction**, whether or not that was the
intention. Their output is an integer code (−100/0/+100) — which is fine, and in fact the only
non-float output in the whole reference, so it should be easy. But a candlestick pattern is also
recognisably a *chart object with a birth instant*, which is AD-25's definition of a family. The
CT-16/CT-17 boundary is undrawn and here AD-23 forces a side without saying so.

The second problem is sharper and is a direct contradiction. **TA-Lib carries process-global
configuration state.** `TA_SetCandleSettings` configures body/shadow averaging periods and factors
per pattern at the C level, and the compatibility mode (`talib.set_compatibility`) changes seeding
arithmetic for classic indicators — RSI, EMA and relatives compute differently under
Metastock-compatible seeding. This state is:

- **shared mutable state** inside a package AD-15 declares pure ("purity binds the pure-computation
  libraries (core, indicators, structure)"), and
- **an un-fingerprinted input that changes the numbers**, which AD-10 exists to make impossible.

AD-23 pins "a version pair — C library + Python wrapper". It does not pin the reference's
*configuration*. Two QMF installs on the pinned 0.7.1 + 0.7.1 pair can produce different RSI values
and different candle-pattern hits, with identical fingerprints.

→ **F-9**, **S-2**.

### C-11 — Elliott Wave and Wyckoff phase labeling

*The hardest case for an append-only, causally-confirmed evidence model.*

**(a)** Yes. **(c) Correctly excluded from governed evidence.** **(d) One real strain.**

**AD-25 already answers this, and answers it well.** An Elliott count is revised wholesale when
price invalidates it; Wyckoff phases are assigned retrospectively. Neither states "confirmed the
moment X happens, with X knowable at that instant". AD-25's response — "imprecise concepts stay
free in research lanes (plain Python, ungoverned) per don't-box-in" — is exactly the right ruling
and should be recorded as a deliberate strength, not a gap.

The strain appears when an operator states a **mechanical variant** precisely, which is entirely
legitimate and likely: "wave 2 is confirmed at the instant a swing confirms with retrace ≥ 0.382 and
< 1.000 of wave 1." Now the whole count is a composite of confirmed objects, and invalidating wave
2 must invalidate waves 3–5 built on it — the cascade question of C-5, at scale.

Wyckoff adds a second wrinkle: phases are **mutually exclusive labels over the same span**. You are
in phase C or phase D, never both. Under an append-only law, "the current phase" is a *fold* over an
append-only stream, not stored state. The spine's Deferred table already lists "annotation
read-resolution rule" as open, which is the same shape of problem; the structure case should be
named alongside it.

→ **S-4**, **N-1**.

### C-12 — Harmonic patterns (Gartley, Bat, Butterfly, Crab, Shark)

**(a)** Yes. **(c) Yes — a good fit.** **(d) Inherits F-6.**

XABCD with Fibonacci ratio bands. Confirmation is precisely stateable — "confirmed at D, at the
instant D's swing confirms, when all four ratio bands hold". Composition over four swing points is
exactly AD-17's composite-with-lineage. Invalidation on band violation is exactly AD-25's
`invalidated-at`.

Everything it needs, it needs from other findings: exact rational parameters and tolerance bands
(F-6), sloped-leg evaluation if the scanner projects PRZ rails (F-6), swing points as children
(already ratified as a seed family).

One volume note: a harmonic scanner across 30 instruments × 8 bar-specs emits a large number of
candidate objects, most of which die unconfirmed. AD-25's pressure valve is correct — "the law binds
governed evidence only: live in-memory use persists nothing", and unconfirmed outputs are "a
separately-labeled evidence class". Worth making explicit that a *scanner* is expected to run
ungoverned and promote only what confirms, so nobody reads AD-25 as requiring every candidate to be
persisted forever under AD-19's keep-everything retention.

→ **N-5**.

### C-13 — Round-number and psychological levels

*Big figures in forex (1.1000), 00/50 levels, BTC at $100k, "whole dollar" in equities.*

**(a)** Yes. **(c) Blocked on observed-at.** **(d) Strains.**

This is a chart object derived from **no market observation at all**. It is a function of the price
grid; 1.1000 has existed since the euro. AD-25 requires every structure output to carry observed-at
and confirmed-at. What is observed-at for a round number? Candidate answers a builder might pick:
the instant the family was configured; the instant the price series first covered that level; the
instant price first touched it; the epoch. All four are defensible, all four produce different
fingerprints, and AD-25 gives no guidance.

There is a second dependency: knowing what "round" means requires the instrument's **tick size /
digits / pip definition**. AD-9 keeps that as "separate dated records" owned by qmf-registry, and
qmf-structure depends on qmf-core only. So it must be injected by the application — fine — but it
must also be identity-bearing (a level set computed under 5-digit pricing differs from one under
3-digit), and nothing says so.

→ **S-6**, **S-7**.

### C-14 — Seasonality and time-of-day statistics

*Day-of-week effect, London-open hour, turn-of-month, Monday gap, crypto weekend effect, summer
doldrums.*

**(a)** Yes. **(b) Needs a civil-time key that AD-8 does not sanction.** **(d) Strains.**

The entire content of a seasonality statistic is a **local wall-clock bucket**: "the 08:00
Europe/London hour", "the first Monday", "the Asian session". AD-8 says "local time is display-only
and always labelled" — which is exactly right as an *evidence* rule, and prevents a whole class of
bugs. But here the local bucket is not display; it is the semantic grouping key of the computation.
London open is a different UTC instant in summer and winter, and that difference is the point of the
statistic.

Nothing forbids computing it. But AD-8 gives no sanctioned path, and a strict reading of
"display-only" would have a careful builder refuse to derive a computational key from local time —
while a less careful one derives it with an unrecorded zone and an unrecorded tzdata version, so the
result silently changes meaning when tzdata ships a DST-rule amendment. AD-5 says re-deriving under
newer tzdata must mint a new artifact with a lineage edge; that can only happen if the tzdata
version is in the fingerprint, which requires the zone to be declared contract surface.

Warm-up for a seasonality statistic is measured in years, so AD-24 will correctly classify it heavy.
That part works.

→ **S-9**, and it is the same amendment family as **F-4**.

### C-15 — Crypto specifics: 24/7 structure and non-price input series

*No sessions, no weekends, perpetual funding rates, open interest, liquidations.*

**(a)** Yes. **(b) Values fit; identity and cadence do not.** **(d) Breaks on inputs.**

**24/7 is handled.** AD-8 explicitly says "every calendar supplies a rollover rule (24/7 included)".
Good. What degenerates is everything session-anchored: what is "the session" for BTCUSDT? A
00:00-UTC convention is a *choice*, venue-specific in practice (perp funding at 00:00/08:00/16:00
UTC on most venues), and it must be identity-bearing — which is C-6's calendar-in-fingerprint fix.
The spine knowingly defers "crypto calendar + crypto design pass" to a later release; the point here
is that **F-4 is what makes that later pass non-breaking**. Without a calendar slot in the CT-16
key, the crypto pass will have to mint new contract versions for indicators that already shipped.

**Funding rate as an input series breaks CT-16 in three ways.** The *values* are fine: a funding
rate of 0.01% is a small signed rational and a scaled integer expresses it exactly; open interest is
a `Quantity`. What does not fit:

1. **Cadence.** Funding prints every 8 hours; the price series is per-tick or per-bar. Joining them
   is C-1's alignment gap.
2. **Kind.** The bulk form declares "scale/metadata" but no channel *kind*. A funding rate, an open
   interest, a price, and a tick-count are four different things that all arrive as int64 arrays
   with a scale.
3. **Identity scope.** AD-19/AD-21 draw a genuinely useful distinction — "a provider you can trade
   at is a venue; a provider you only read from is a **source**". A funding rate is `(venue, symbol)`
   -scoped; a reference index or an on-chain metric is `(source, series-kind)`-scoped. AD-22's key
   has one slot, called "instrument", and it cannot express either alternative.

→ **F-1**, **F-4**, **S-3**.

### C-16 — Statistical and quant retail methods

*Z-scores, rolling OLS and Kalman hedge ratios, Hurst exponent, ADF/Engle-Granger cointegration,
GARCH volatility, PCA on a basket, ML feature pipelines.*

**(a)** Yes, and AD-22's rider explicitly blesses it ("custom indicators are authorable … as plain
Python outside governed evidence"). **(b) Locked out of governed evidence by two clauses.**
**(d) Breaks.**

**Problem one: is streaming mode mandatory?** AD-22 opens with "One consumer-blind contract, **two
conformant modes**" and makes the batch≡streaming equality an AD-4 tier-2 contract test. Read
literally, every conformant indicator implements both — otherwise the tier-2 test has nothing to
compare. But ADF has no meaningful incremental form (a rolling-window ADF is a full O(n) re-fit per
update); GARCH re-fits; PCA re-fits; a rolling OLS *can* be incremental but a rolling quantile
regression cannot cheaply. Requiring streaming conformance bans a large, legitimate, entirely
mainstream class of quant indicators from governed evidence — or forces absurd O(n)-per-update
"streaming" implementations that then fail AD-24's light test anyway.

**Problem two: AD-23 has no canonical story for formulas TA-Lib does not implement.** This is a
much bigger hole than it looks. TA-Lib's ~158 functions do **not** include: VWAP, Ichimoku,
SuperTrend, Heikin-Ashi, Keltner channels, Donchian channels, pivot points, volume profile, ADF,
GARCH, Kalman, Hurst — nor anything from any modern structure school. AD-23 says "the canonical
arithmetic reference is TA-Lib" and "batch mode wraps the reference (wrap-not-reimplement)", and
the qmf-indicators component spec hardens this into a failure mode: *FM-2 — "No ratified reference
implementation, version, or tolerance exists → the wrapper must not claim canonical arithmetic or
ship as a completed wrapper."* Under that pairing, **VWAP cannot ship**, and neither can any
QMX-original formula.

The intent is clearly narrower than the text — AD-23 does contemplate QMX-owned streaming
implementations. But the text needs to say what canonical arithmetic *is* when the pinned reference
is silent, and to keep the same upgrade gate (any output change for identical canonical inputs mints
a contract format version) applying to QMX-original formulas.

→ **F-7**.

### C-17 — Multi-timeframe confluence, and the repainting hole

*4H trend filter with 5m entries; daily bias with 15m execution. Universal across every tradition.*

**(a)** Yes. **(b) Yes arithmetically — but unguarded against look-ahead.** **(d) Contradicts the
spirit of AD-25.**

This is the most consequential finding in the review.

A 4H EMA read at 09:05 must use the **last closed** 4H bar. Using the in-progress bar's current
value is repainting: the number changes until 12:00, so a backtest sees a value no live system could
have seen. This is the single most common look-ahead bug in retail TA and it is responsible for a
large share of strategies that backtest beautifully and fail live.

AD-25 solves exactly this problem for chart objects: observed-at, confirmed-at, "confirmed the
moment X happens, with X knowable at that instant", "evidence consumed as confirmed uses
confirmed-at". **AD-22 has no analogue.** An indicator output carries a warm-up marker and a sample
position, and nothing records *when its value became knowable*. AD-8 supplies the principle
("causality is compared on instants only") but nothing in CT-16 asks for the instant. And GAP-0016
— the look-ahead registration gate that would have been the backstop — is explicitly deferred to
the backtesting sitting, with the consequence "artifacts registered before then carry no causality
evidence" knowingly accepted.

So today, an MTF indicator can silently produce look-ahead-contaminated evidence and nothing in the
spine catches it. The amendment is small and mirrors a law the spine already ratified: every CT-16
output sample carries a **knowable-at instant** (the earliest instant at which every input
contributing to it was knowable), plus a declared **bar-closed versus in-progress** policy as
fingerprinted contract surface. One clause, and MTF becomes safe by construction.

→ **F-5**.

### C-18 — The deliberately absurd random experiment

The brief asks for one experiment mixing several concepts across timeframes and instruments. Here
it is, constructed to be exactly the kind of thing an experimental operator might actually try
after reading three forum posts:

> **"Funding-Skew Renko Fib Rails."** Build 25-pip **renko** bricks on EURUSD from **bid** ticks. On
> the renko series compute a 14-brick **RSI**. Take the rolling 90-day **Spearman correlation**
> between that RSI and the 8-hour **Binance BTCUSDT perpetual funding rate**. When |ρ| > 0.4,
> project **Fibonacci extensions** (1.272, 1.618) from the most recent confirmed **XAUUSD daily
> swing leg**, drawn as a **sloped rail decaying 0.3 pips per hour** toward a **VWAP anchored at the
> last FOMC release**. Mark the resulting zone "active" only during the **Tokyo session on the
> second Wednesday of the month**. Size the entry off the rail, in gold, on a **prop-firm account
> whose day boundary is 17:00 Sydney**.

Twelve legs; here is the tally.

| # | Leg | Verdict | Finding |
|---|---|---|---|
| 1 | 25-pip renko bricks | **Breaks** — no BarSpec noun; "timeframe" cannot hold a brick size; bar-builder has no home | F-3, N-7 |
| 2 | Built from bid ticks | **Breaks** — no declared price basis on the series; bid-RSI and mid-RSI share a fingerprint | S-3 |
| 3 | 14-brick RSI | **Breaks** — warm-up is 14 *bricks*, unbounded in time; AD-24's window bound and AD-25's embargo width both need time | F-3, F-8 |
| 4 | RSI feeding a correlation | **Breaks** — indicator output is not a stated legal indicator input | F-2 |
| 5 | Spearman across two instruments, two venues, two cadences | **Breaks** — single-instrument key; no alignment policy | F-1 |
| 6 | Three calendars (forex-17NY, crypto 24/7, metals) | **Works** — AD-8 refuses cross-calendar TradingDate comparison and permits instant-level joining. Correct and useful | N-2 |
| 7 | Fib 1.272 / 1.618 | **Breaks** — floats refused in identity content | F-6 |
| 8 | Sloped rail decaying 0.3 pips/hour | **Breaks** — slope not identifiable; price-per-time is a dimension no core type has; "pip" undefined | F-6, S-8 |
| 9 | VWAP anchored at the last FOMC release | **Breaks** — AVWAP misclassified heavy; and no path for an external event as an anchor input, nor identity for which FOMC record at which revision | F-8, S-12 |
| 10 | Tokyo session, second Wednesday | **Strains** — AD-8 supports both facts, but no calendar path into CT-16/CT-17 and no sanctioned civil bucket key | F-4, S-9 |
| 11 | Prop-firm 17:00 Sydney day boundary | **Works** — AD-8's account-scoped **day-boundary calendar** is precisely this. And AD-25 correctly forbids the account-scoped filter from living in the family (that would be Book vocabulary in a chart-object taxonomy), pushing it to the consuming bot | N-3 |
| 12 | Size the entry off the rail, in gold | **Strains** — AD-7's named conversion boundary is the right mechanism but is unnamed for structure/indicator outputs; rounding a stop up vs down is real money | S-11 |

**Nine of twelve legs break or strain; three work.** But the three that work are the *hard* ones —
multi-calendar causality, account-scoped day boundaries, taxonomy discipline — which is the honest
headline of this review: the spine's deep rulings are sound, and the failures are concentrated in
one under-specified surface (the CT-16 configuration key and series vocabulary) plus one missing
clause (indicator knowable-at). Fix F-1 through F-9 and this entire absurd experiment becomes
expressible.

### C-19 — Order flow: footprint, cumulative delta, order-book imbalance

**(a)** Yes. **(b) Partially — 1-D aggregates only.** **(d) Strains / out of vocabulary.**

Cumulative volume delta needs a per-trade aggressor side; footprint needs volume bucketed by price
within a bar; book imbalance needs L2 depth snapshots. AD-21 preserves bid and ask ticks with source
timestamps, which covers tick-rule delta approximations. L2 depth appears nowhere in the spine.

The bulk series form is defined for **numeric channels** (int64 arrays plus scale). A book snapshot
is nested and variable-arity (N levels × price × size), and a footprint bar is 2-D like C-8's volume
profile. Either the bulk form needs a variable-arity channel concept, or the spine should say plainly
that L2/footprint data is outside the V1 series vocabulary and lives in the ungoverned research lane.
Saying nothing is the worst option, because a builder will invent a representation.

→ **N-4**, **S-1**.

### C-20 — Divergence detection (RSI/MACD divergence)

*One of the most-used constructs in all of retail TA, and the cleanest CT-16 × CT-17 crossing case.*

**(a)** Yes. **(c) Blocked — a family cannot declare an indicator input.** **(d) Breaks.**

A divergence is a structure object *over an indicator series*: swing highs in price compared against
swing highs in RSI. It requires a CT-17 family to consume CT-16 output.

AD-25 says "qmf-structure depends on qmf-core only in V1", which is a *packaging* statement and is
satisfied by the application passing the series in. But nothing in CT-17 says a family may **declare**
an indicator output as an input, and — critically — nothing says the upstream indicator's fingerprint
enters the divergence object's fingerprint. Without that, divergences computed against a 14-RSI and
against a 21-RSI are identical artifacts. AD-12 already requires "input fingerprints" in every result
label; the amendment is to state that this applies across the CT-16/CT-17 seam.

Stated generally, one sentence covers this, C-2's chaining, and C-3's structure-on-renko:
**any CT-16 or CT-17 output series is a legal input to any CT-16 or CT-17 configuration, and
upstream fingerprints enter downstream identity.** No import edge is created; the composition happens
at the application layer as AD-25 already requires. Only the *contract* needs to permit and identify
it.

→ **F-2**.

### C-21 — Bollinger, Keltner, Donchian: price-valued indicator outputs

**(a)** Yes. **(b) Yes.** **(d) Strains on money-path re-entry.**

A Bollinger upper band used as a stop is on the money path by AD-7's taint rule. TA-Lib returns it as
a C double. AD-22 correctly says "re-entry to the money path crosses AD-7's named conversion
boundary" — the mechanism is present. What is absent is the **declaration**: AD-7 requires "an
explicitly stated rounding mode", and rounding a stop up versus down is a real, recurring money
difference across thousands of trades. Nothing says a CT-16 output channel declared as price-kind
must carry a rounding mode and a target scale as fingerprinted contract surface.

This is the same amendment as C-8's output schema: channels get declared kinds, and price-kind
channels get a declared rounding mode and scale.

Donchian is worth a separate note: TA-Lib has MIN/MAX/MINMAX but no Donchian channel as such, and no
Keltner — another instance of C-16's non-TA-Lib gap in a place a builder would not expect it.

→ **S-1**, **S-11**, **F-7**.

### C-22 — Warm-up, seeding, and what "identical canonical inputs" means

*The equality law's own edge case.*

**(d) Strains — the law is under-defined.**

AD-22's equality law says "identical canonical inputs MUST produce identical outputs across modes",
enforced at tier 2. Three edges are unaddressed:

1. **Snapshot/restore versus cold start.** AD-22 explicitly permits snapshot/restore "so restart
   re-warm never replays a day". A restored streaming instance carries state from before the test
   array and will *not* reproduce a batch call over that array from index 0. So "canonical inputs"
   must be defined to include **initial state**, and restore-equivalence must be a *separate* test:
   restore-then-N-updates ≡ cold-warm-then-the-same-N-updates.
2. **Seeding.** TA-Lib seeds EMA with an SMA of the first `n` values and uses Wilder smoothing for
   RSI/ATR/ADX. A naively seeded streaming EMA converges toward the batch result but never equals
   it. Under a declared float tolerance it may pass on a 500-bar fixture and fail on a 50-bar one —
   a flaky merge gate that will get "fixed" by widening the tolerance, which is the wrong repair.
   The seeding rule is part of canonical arithmetic and belongs in the declaration.
3. **Leading-NaN region.** TA-Lib emits a `lookback`-length undefined prefix. AD-22 says warm-up
   output is "a marked not-ready value, never a number" — which is the right rule and directly
   contradicts what the wrapped reference actually returns. The mapping from the reference's prefix
   to QMF's not-ready marker must be stated, or two wrappers will disagree about where warm-up ends.

→ **S-10**.

### C-23 — Missing data, weekend gaps, and holiday half-days

*Forex weekends, crypto exchange outages, equity holidays, broker feed dropouts.*

**(b) Blocked — "missing" is not defined against a schedule.** **(d) Breaks in ordinary use.**

AD-22's missing-value rule is excellent and exactly right in principle: "Missing input yields a
marked output gap or a typed refusal per the indicator's **declared** missing-value policy — never
silent filling." Silent forward-filling is a genuine plague in retail backtests and banning it is
correct.

But the rule has no notion of a **schedule**. A 5-minute EMA over a forex weekend faces 576 absent
samples that are not missing data — the market was closed. AD-8's market-hours calendar knows this
precisely (session schedule, weekend gaps, holidays in scope). CT-16 has no calendar (C-6). Without
one, every indicator on every instrument emits hundreds of gap markers every weekend, or refuses
every Monday. Neither is usable, so builders will quietly special-case it, differently, in each
indicator.

The distinction that must be stated: **absent-by-schedule** (the calendar says closed — the series
simply has no sample there, and this is not a gap) versus **missing** (the calendar says open and no
data arrived — this *is* a gap or a refusal, per the declared policy). Crypto's 24/7 calendar makes
every absence a genuine gap, which is correct and is a good cross-check that the distinction is
real: the same indicator on EURUSD and on BTCUSDT should behave differently at 03:00 Sunday, and
only the calendar knows why.

This shares the calendar-injection amendment with C-6, C-7 and C-14 — one fix, four payoffs.

→ **F-4**.

### C-24 — Ichimoku: the built-in forward projection

*Not in TA-Lib; near-universal in Japanese and much of Asian retail forex.*

**(a)** Yes. **(b) Yes, but it is the perfect trap for the knowable-at hole.** **(d) Strains.**

Senkou Span A and B are *plotted 26 periods into the future*. Chikou Span is plotted 26 periods into
the past. So a single indicator emits three channels whose display index and computation index
differ in both directions.

Under a knowable-at law (F-5) this is trivially safe: the cloud value displayed at index i+26 has
knowable-at equal to the instant of bar i, and a bot reading "the cloud" at bar i correctly gets a
value computed 26 bars ago. Under a naive "output aligns to input sample" reading — which is all the
spine currently offers — a builder writes the cloud into index i+26 of an output array and hands a
future-indexed series to a bot. That is literal look-ahead, produced by a correct-looking
implementation of a standard indicator, with nothing in the spine to catch it.

Ichimoku is therefore the cleanest possible motivating case for F-5, and it doubles as a C-16 case
(it is not in the pinned reference, so it needs the QMX-canonical path too) and a C-8 case (three
channels with different index offsets need a declared output schema).

→ **F-5**, **F-7**, **S-1**.

### C-25 — ATR, pips, and the missing delta vocabulary

*Every stop-loss the operator has ever placed is expressed in pips.*

**(d) Strains — semantic, not mechanical.**

ATR, true range, spread, "distance to the level", "20-pip brick", "1.5× ATR stop" are all **price
differences**, not prices. Mechanically AD-7 copes: subtracting two `Price` values at the same scale
for the same instrument stays an integer. Semantically it does not: a delta has no absolute
reference, can be negative, cannot be meaningfully compared across instruments without
normalisation, and its natural unit — the **pip** or **point** — is defined nowhere in the spine, in
the glossary, or in the registry.

The pip definition is the load-bearing part. It is instrument-scoped (0.0001 on EURUSD, 0.01 on
USDJPY, 0.1 on XAUUSD at many brokers, and broker-dependent for indices), it comes from AD-9's
mutable-metadata records in qmf-registry, and it is unreachable from qmf-indicators and
qmf-structure by import. Every renko brick size, every ATR multiple, every stop distance, every
"minimum swing size" parameter in every structure family needs it, and needs it identity-bearing.

→ **S-7**, **S-8**.

---

## Findings — must-fix

Nine. Each is either "a legitimate general experiment is impossible" or "an AD is contradicted".

### F-1 — CT-16's input and identity are single-series, single-instrument

- **Concepts:** rolling correlation, spreads and ratios, pairs and cointegration, cross-asset
  filters, funding-rate inputs, any relative-strength construct (C-1, C-2, C-15, C-16).
- **Clause:** AD-22 — "Instances deduplicate by content fingerprint (formula + parameters +
  **instrument** + timeframe)"; and "Input series: the bulk form of exact values is defined in
  `qmf-core` — int64 arrays plus out-of-band scale/metadata … **one representation
  workspace-wide**".
- **Why it blocks:** a multi-input indicator has no expressible identity, so it cannot enter
  governed evidence. Forcing the second instrument into "parameters" is undeclared and produces
  fingerprint collisions across sandboxes.
- **Smallest amendment:** CT-16 takes an **ordered, named input set** — one or more
  `(series-reference, role)` entries, where a series-reference names its instrument-or-source, its
  BarSpec (F-3), and its channel (S-3). The input set replaces the single `instrument` slot in the
  configuration fingerprint. Add a **declared alignment policy** (as-of-last-known / intersect /
  reference-clock resample / refuse-on-mismatch) as contract surface entering the fingerprint,
  because the choice changes the numbers. State that AD-22's "exactly one feeder" means one
  *writer*, not one *input stream*.

### F-2 — Indicator and structure outputs are not stated to be legal inputs

- **Concepts:** MACD (EMA of EMA), RSI of a spread, Bollinger on a synthetic, z-scores, divergence
  detection, structure computed on renko (C-2, C-3, C-20).
- **Clause:** AD-22 — inputs are exact int64 bulk series, "one representation workspace-wide"; and
  AD-25's silence on what a family may declare as an input.
- **Why it blocks:** an indicator output is an analytic *float* series. Under a literal reading it
  is not a legal input to anything, which forbids essentially all composed indicators and all
  indicator-derived structure.
- **Smallest amendment:** one sentence, stated once and binding both contracts — **any CT-16 or
  CT-17 output series is a legal input to any CT-16 or CT-17 configuration; the upstream artifact's
  fingerprint enters the downstream configuration's identity** (AD-12's "input fingerprints" already
  supplies the mechanism). No import edge is created — composition stays at the application layer,
  as AD-25 already requires. Add a **derived-series identity**: a computed series is identified by
  its result label and may be referenced wherever an input series is expected, without minting a
  synthetic `Instrument` (which AD-9 would otherwise force).

### F-3 — "Timeframe" is undefined and time-bar-biased; warm-up has no unit

- **Concepts:** renko, range bars, tick bars, volume bars, dollar/imbalance bars, Heikin-Ashi
  (C-3, C-18).
- **Clause:** AD-22 — "(formula + parameters + instrument + **timeframe**)"; AD-24 — "a configured
  indicator" classified per configuration including timeframe; AD-22 — "declares its **warm-up
  length**"; AD-25 — warm-up and confirmation delay "feed future split purge/embargo widths"
  (which AD-21 requires to be TradingDates or instants).
- **Why it blocks:** non-time bars cannot be fingerprinted, so they cannot enter governed evidence.
  And a bar-count warm-up has no bounded time width for event-driven bars, so AD-24's window test
  and AD-25's embargo width are both undefined.
- **Smallest amendment:** define a **BarSpec** noun in `qmf-core` — a discriminated declaration of
  the aggregation rule (`time-interval | tick-count | volume-threshold | notional-threshold |
  price-brick | range | session`) plus its exact parameters — identity-bearing, replacing the bare
  word "timeframe" everywhere it appears. Restate warm-up as **a count in the input series' own
  sample unit**, plus an optional declared *time* bound that is explicitly `null` for event-driven
  specs; a null time bound makes the configuration ineligible for AD-24's window test unless it
  declares a maximum lookback with a stated conversion. Name the bar builder's home explicitly
  (see N-7).

### F-4 — No calendar reaches CT-16/CT-17, and no calendar enters their identity

- **Concepts:** pivot points, session VWAP, daily/weekly levels, ADR, opening ranges, weekend gaps,
  holiday half-days, seasonality, crypto 24/7 (C-6, C-7, C-14, C-15, C-23).
- **Clause:** AD-22 — the fingerprint tuple has no calendar slot, and the input form is series-only;
  against AD-8 — "only the rule set + tzdata version enter fingerprints" — and AD-5 — re-deriving
  under a newer calendar/tzdata "produces a new artifact with its own fingerprint and a lineage
  edge".
- **Why it contradicts:** daily pivots under `forex-17NY v3` and under a 00:00-UTC rollover produce
  different numbers and identical fingerprints. That is precisely the silent equality AD-5 and AD-10
  forbid.
- **Smallest amendment:** state that a CT-16 or CT-17 configuration may declare a **calendar
  requirement**; the calendar instance is injected by the composition root (legal today — extensions
  implement core protocols, so no import edge is created), and its **identity + version + tzdata
  version are identity-bearing configuration fields**. On the same clause, distinguish
  **absent-by-schedule** from **missing**: a sample the market-hours calendar says was closed is not
  a gap and does not trigger the missing-value policy; a sample the calendar says should exist and
  does not, is.

### F-5 — Indicator outputs carry no knowable-at; MTF repainting is unguarded

- **Concepts:** every multi-timeframe construct; Ichimoku's forward and backward projections; any
  higher-timeframe filter (C-17, C-24).
- **Clause:** AD-25 grants chart objects observed-at/confirmed-at and "evidence consumed as confirmed
  uses confirmed-at"; **AD-22 grants indicator outputs no equivalent**. AD-8 supplies the principle
  ("causality is compared on instants only") but no contract asks for the instant. GAP-0016 — the
  look-ahead gate that would have been the backstop — is deferred, "consequence accepted".
- **Why it blocks:** an MTF indicator that reads an in-progress higher-timeframe bar produces
  values no live system could have seen, and nothing in the spine detects it. This is the most
  common look-ahead bug in retail TA and the framework currently ships without a guard.
- **Smallest amendment:** every CT-16 output sample carries a **knowable-at instant** — the earliest
  instant at which every input contributing to it was knowable — mirroring AD-25's law. Plus a
  declared **bar-closed versus in-progress** emission policy as contract surface entering the
  fingerprint. Two clauses; MTF becomes safe by construction and AD-25's discipline becomes uniform
  across both libraries.

### F-6 — Floats are refused in identity, and there is no exact non-integer type

- **Concepts:** Fibonacci ratios, Bollinger deviations, ATR multiples, harmonic ratio bands,
  significance levels, tolerance percentages, trendline and channel slopes, decay rates
  (C-4, C-5, C-12, C-21).
- **Clause:** AD-10 — "all identity numerics are integers … **floats are refused in identity
  content**"; against AD-25's non-privileging of families and AD-22's "parameters" entering the
  fingerprint.
- **Why it contradicts:** a 61.8% retracement and a 50% retracement are different objects; a 2.0-σ
  band and a 2.5-σ band are different indicators; two trendlines with different slopes are different
  objects. If the distinguishing parameter cannot be in identity, the artifacts collide — and AD-16's
  cross-sandbox dedup will silently merge them.
- **Smallest amendment:** two parts, both small. (1) `qmf-core` gains an **exact rational** value
  type — a scaled integer with a declared scale (618 at scale 3), or an explicit numerator/
  denominator — and **all CT-16/CT-17 parameters are required to be exact**, never binary floats.
  This is already the AD-7 idiom, just extended past money. (2) **Sloped and continuous-valued
  chart objects are identified by integer anchors** — two or more `(instant, exact Price)` pairs —
  plus a declared, versioned **evaluation rule**. Slope is derived and never stored in identity;
  evaluation at an instant crosses a named AD-7 conversion boundary (see S-11).

### F-7 — Two-mode conformance appears mandatory, and AD-23 has no canonical story off TA-Lib

- **Concepts:** VWAP, Ichimoku, SuperTrend, Keltner, Donchian, pivot points, volume profile, ADF,
  GARCH, Kalman, Hurst, PCA, every ML feature, every operator-authored formula (C-16, C-21, C-24).
- **Clause:** AD-22 — "One consumer-blind contract, **two conformant modes**" with the equality as a
  tier-2 contract test; AD-23 — "**the canonical arithmetic reference is TA-Lib**", "batch mode
  wraps the reference (wrap-not-reimplement)"; hardened by the component spec's FM-2 — "No ratified
  reference implementation … the wrapper must not claim canonical arithmetic or ship as a completed
  wrapper."
- **Why it blocks:** TA-Lib implements roughly 158 classic functions and none of the above. Read
  together, these clauses say VWAP cannot ship as canonical, and every batch-only statistical method
  is locked out of governed evidence — while AD-22's own rider ("custom indicators are authorable as
  CT-16-conformant extensions") promises the opposite.
- **Smallest amendment:** (1) an indicator **declares its supported modes**; batch-only and
  streaming-only are conformant; the equality contract test binds only when both are declared. A
  batch-only declaration is legitimate and will usually classify heavy under AD-24, which is the
  correct outcome. (2) AD-23 gains one clause: **where the pinned reference implements the formula,
  wrapping it is mandatory and the reference is canonical; where it does not, the QMX implementation
  *is* the canonical arithmetic for that formula**, pinned by its own contract format version, under
  the identical upgrade gate (any output change for identical canonical inputs mints a version with
  recorded before/after evidence). The dual-reference comparison artifact becomes
  required-when-a-reference-exists rather than required-always.

### F-8 — AD-24's "bounded evidence window" misclassifies O(1) anchored indicators as heavy

- **Concepts:** session VWAP, anchored VWAP, cumulative volume delta, session high/low, opening
  range, running drawdown, distance-from-ATH, any "since X" statistic (C-7).
- **Clause:** AD-24 — light requires "(2) bounded declared state size; **(3) bounded declared
  evidence window (its warm-up)**".
- **Why it blocks:** a running accumulator has bounded state and an unbounded window. Session VWAP's
  window is not even a constant — AD-8 explicitly forbids assuming session length is. So the
  most-watched intraday level in the market is forced off the live decision path, which for a
  scalping tool is functionally fatal, on a criterion that measures nothing real about its cost.
- **Smallest amendment:** split bound (3). Light requires bounded state (bound 2) **and either** a
  bounded declared evidence window **or** a declared **anchor-reset rule** whose per-update cost is
  O(1) and whose state stays within bound (2). Because the window bound also feeds AD-25's
  purge/embargo widths, an anchored configuration must declare its **anchor kind** so the embargo is
  computed from the anchor rather than from a window. The merge-gate benchmark still polices the
  latency claim, so nothing is weakened.

### F-9 — The pinned reference's process-global configuration is neither pinned nor fingerprinted

- **Concepts:** all 61 candlestick patterns; RSI, EMA, ATR, ADX and relatives under compatibility
  mode (C-10, C-22).
- **Clause:** AD-23 pins "a version pair — C library + Python wrapper" and nothing else; against
  AD-15 — "purity binds the pure-computation libraries (core, indicators, structure)" — and AD-10's
  requirement that identity be complete.
- **Why it contradicts:** TA-Lib carries process-global state — candle settings (body/shadow
  averaging periods and factors, per pattern) and a compatibility mode that changes seeding
  arithmetic for classic indicators. It is shared mutable state inside a package declared pure, and
  it is an un-fingerprinted input that changes the numbers. Two installs on the identical pinned
  0.7.1 + 0.7.1 pair can produce different RSI values and different pattern hits under identical
  fingerprints.
- **Smallest amendment:** AD-23 pins the reference's **configuration** alongside its version pair —
  a declared, identity-bearing *reference configuration* record (compatibility mode plus every
  candle setting), asserted at import (refusing `unavailable dependency` on mismatch, exactly as
  AD-8 does for tzdata), never mutated at runtime. A configuration change is a contract format
  version mint, identically to a version upgrade.

## Findings — should-fix

Twelve. Possible, but two competent builders would guess differently.

| # | Finding | Clause that strains | Smallest amendment |
|---|---|---|---|
| **S-1** | CT-16 output shape is undefined: multi-channel, vector/profile, integer-code and price-kind outputs all unaddressed — yet AD-23's own pinned reference already returns 2- and 3-channel results (MACD, BBANDS, STOCH, AROON) | AD-22 speaks of "outputs" with no shape vocabulary; the tier-2 equality test cannot be written against it | CT-16 declares an **output schema**: an ordered list of named channels, each with a declared kind (`exact-price` / `exact-quantity` / `float-analytic` / `integer-code` / `boolean` / `categorical`) and arity (scalar-per-sample, fixed vector, or keyed-by-price-bin), identity-bearing |
| **S-2** | The CT-16 / CT-17 boundary is undrawn — volume profile, candlestick patterns, renko bricks and divergences all sit on it | AD-22 and AD-25 each define themselves without reference to the other | State the test once: **CT-16 emits a value aligned to every input sample; CT-17 emits a discrete object with a birth instant and a lifetime.** Anything expressible both ways declares which it is |
| **S-3** | Series channels carry no declared kind or unit — price basis (bid/ask/mid), volume kind (tick-count/base/quote/notional), rate, open interest | AD-22's "int64 arrays plus out-of-band scale/metadata"; AD-7's `Quantity(unit, scale)` is the right primitive but is not required here | The bulk form's out-of-band metadata declares **per-channel kind and unit**, identity-bearing. RSI-on-bid and RSI-on-mid must not share a fingerprint |
| **S-4** | Invalidation does not propagate through composites — a Fib set built on an invalidated swing, an Elliott count on an invalidated wave | AD-25's `invalidated-at`; AD-17's composite-with-lineage | A composite declares its **cascade policy** (`invalidate-with-any-child` / `with-all-children` / `independent`) as contract surface |
| **S-5** | Revisable/re-fitting objects (forming triangles, moving apexes, re-counted waves) have no stated pattern | AD-25 has observed-at/confirmed-at/invalidated-at but no refit concept; AD-16's edges are registry-side and app-mediated | State: **anchors are frozen at observed-at**; a re-fit is a new artifact with a `supersedes` edge, and the lineage head's observed-at is the first fit's. Or permit a family to declare a refit cadence — either ruling works; the silence does not |
| **S-6** | A-priori / generated levels (round numbers, big figures) have no defined observed-at | AD-25 requires observed-at on every output; a round number was never observed | Permit a **standing object** whose observed-at is its configuration instant, or require such levels be expressed as consumer parameters rather than structure artifacts. Pick one and say it |
| **S-7** | Instrument metadata (tick size, digits, pip, contract size, min lot) is unreachable from indicators/structure and unidentified | AD-9 owns it in qmf-registry; AD-22/AD-25 depend on qmf-core only; nothing says it is injected or identity-bearing | An **instrument metadata snapshot** is an injected configuration input; its registry record fingerprint is identity-bearing |
| **S-8** | No `PriceDelta` and no pip/point vocabulary — yet every stop, target, brick size and swing threshold is expressed in pips | AD-7 defines Money/Price/Quantity; a difference of prices is dimensionally distinct and its natural unit is undefined | Name a **`PriceDelta(instrument, scale)`** (or state that price subtraction is closed and delta-typed), and define the instrument-scoped **pip/point** sourced from S-7's metadata |
| **S-9** | Civil/local-time bucket keys have no sanctioned computational path | AD-8 — "local time is display-only and always labelled" — is right for evidence but leaves seasonality and session-of-day statistics without a legal derivation | AD-8 gains one sentence: a **civil-time bucket key** derived from an instant plus a declared zone and tzdata version is a legitimate computed value — never a timestamp, never a causality proxy — and is identity-bearing including its zone and tzdata version |
| **S-10** | "Identical canonical inputs" does not account for initial state, seeding, or the reference's leading-undefined prefix | AD-22's equality law and its snapshot/restore permission pull against each other | Define **canonical inputs = (series, parameters, cold initial state)**. Add a separate **restore-equivalence test**: restore-then-N ≡ cold-warm-then-N. Make the seeding rule and the reference-prefix→not-ready-marker mapping declared contract surface |
| **S-11** | The float→money-path conversion boundary is unnamed for indicator and structure outputs | AD-7 requires "a named conversion boundary with an explicitly stated rounding mode"; AD-22 points at it; nobody names it | Name it: a CT-16 output channel declared `exact-price`, and a CT-17 object's evaluated level, cross **the analytic-to-exact boundary**, declaring rounding mode and target scale as fingerprinted contract surface |
| **S-12** | External event anchors (news releases, FOMC, halvings, earnings) have no input path or identity | AD-8 names the news calendar as a distinct concept; AD-21 keeps provider-native identity and revisions; neither CT-16 nor CT-17 can take one as an anchor | An **anchor input** is a declared, identity-bearing reference `(source, source-native id, revision)` per AD-21, injected like a calendar |

## Findings — notes

| # | Note |
|---|---|
| **N-1** | **AD-25's exclusion of Elliott/Wyckoff is correct and deliberate**, not a gap. The precise-rule bar plus the ungoverned research lane is exactly the right answer for inherently revisable interpretations. Do not "fix" it; do state the mechanical-variant path (S-4, S-5) so a precisely-stated variant is not accidentally excluded too |
| **N-2** | **AD-8's cross-calendar `TradingDate` refusal plus instant-only causality is a genuine strength.** It is what makes a forex × crypto × metals experiment safe — the calendars cannot be silently mixed, but instant-level joining stays legal. Preserve it verbatim through the F-1 alignment amendment |
| **N-3** | **AD-8's account-scoped day-boundary calendar plus AD-25's "never a Book category" combine correctly.** A prop-firm 17:00-Sydney filter cannot live inside a chart-object family and is pushed to the consuming bot. The taxonomy discipline holds under pressure |
| **N-4** | **L2 depth, footprint and order-book imbalance are outside the V1 series vocabulary.** The bulk form handles numeric channels; a book snapshot is nested and variable-arity. Either widen the form or say plainly that this data lives in the ungoverned research lane — saying nothing guarantees a builder invents a representation |
| **N-5** | **Pattern scanners produce high artifact volume.** AD-25's "the law binds governed evidence only; live in-memory use persists nothing" plus the separately-labelled unconfirmed class is the correct pressure valve. Make it explicit that a scanner is *expected* to run ungoverned and promote only confirmed objects, so nobody reads AD-19's keep-forever retention as applying to every candidate |
| **N-6** | **Subjective pattern parameters are a non-problem.** Shoulder-symmetry tolerance, minimum touches, minimum swing size — these are declared parameters entering the fingerprint, and two operators with different values get two distinct identified families. This is already correct; recording it so a later reviewer does not "fix" it into a rigid parameter set |
| **N-7** | **The bar builder has no named home.** Renko/tick/volume bar construction is not an indicator (its output is a bar series, not a value per sample), not obviously a chart object, and beyond qmf-data's stated remit of source-fact normalisation. Name its owner as part of F-3 |
| **N-8** | **AD-22's "exactly one feeder" needs one word of clarification.** Read as "one `WriterId` holder" it permits multi-input streaming instances; read as "one input stream" it bans them. F-1 covers it, but the ambiguity is worth naming separately because it also affects single-instrument multi-channel feeds (a tick feed plus a separate volume feed) |
| **N-9** | **GAP-0016's deferral costs more once indicators can produce evidence.** The look-ahead gate was the backstop for exactly the class of error F-5 describes. With it deferred and F-5 unfixed, MTF indicator evidence has no causality guard at all. F-5 is the cheap partial substitute and materially reduces what the backtesting sitting has to catch retroactively |

## What already works — recorded so it is not disturbed

- **AD-25's bitemporal law is the right shape for chart objects.** Observed-at / confirmed-at /
  appended invalidated-at handles renko bricks, harmonic patterns, H&S confirmations, order-block
  mitigation and zone invalidation without modification.
- **The precise-confirmation bar plus the ungoverned research lane** is the correct resolution of
  rigour versus experimental freedom, and it is what lets an experimental operator adopt a random
  idea from anywhere without corrupting evidence.
- **AD-17's composite-with-lineage** already supports Fibonacci sets, harmonic XABCD, multi-touch
  trendlines, confluence zones and Elliott counts. No amendment needed.
- **AD-7's `Quantity(unit, scale)` with an opaque unit** absorbs the forex-tick-volume versus
  crypto-real-volume split cleanly. It needs declaring (S-3), not changing.
- **AD-8's calendar model** — rule-set identity separate from binding, separate accounting rollover
  and session schedule, 24/7 rollover, account-scoped day boundaries, tzdata in the fingerprint — is
  the strongest part of the spine under this lens and handles every calendar case walked here.
- **AD-22's never-silent-fill rule** is correct and important; it needs the schedule distinction
  (F-4), not weakening.
- **AD-24's "classification is per configuration, never per name"** is exactly right and survives
  every case here. Only bound (3) needs splitting.
- **AD-25's no-privileged-families ruling** does what it was written to do: nothing in this general
  lens is foreclosed by family taxonomy. What is foreclosed is foreclosed by *identity and input
  vocabulary*, never by the family model.

## Amendment summary — the smallest set

Six edits close all nine must-fix findings:

1. **Replace CT-16's four-slot dedup key with an open, versioned declared-configuration record**:
   formula id + contract format version + ordered input set + exact parameters + BarSpec(s) +
   calendar identity/version (if declared) + channel kinds + output schema + missing-value policy +
   warm-up + light/heavy budget + supported modes + alignment policy. (F-1, F-3, F-4, F-7, S-1, S-3)
2. **Add `BarSpec` and an exact-rational value type to `qmf-core`**, and require all CT-16/CT-17
   parameters to be exact. (F-3, F-6)
3. **State the composition sentence**: any CT-16/CT-17 output series is a legal input to any
   CT-16/CT-17 configuration, with upstream fingerprints entering downstream identity; plus
   derived-series identity so synthetics need no fake Instrument. (F-2)
4. **Give CT-16 outputs a knowable-at instant and a bar-closed/in-progress policy.** (F-5)
5. **Split AD-24's bound (3)** into bounded-state and bounded-window-or-declared-anchor-reset. (F-8)
6. **Extend AD-23's pin to the reference's configuration**, asserted at import, mint-on-change. (F-9)

Sloped-object anchoring (F-6 part 2) and the absent-by-schedule distinction (F-4 part 2) ride along
with edits 2 and 1 respectively.

---

*Reviewer lens: general trading — forex, crypto, classic technical analysis, market structure,
statistical/quant retail. No school privileged; every concept tested against the same four
questions. 25 concepts walked.*
