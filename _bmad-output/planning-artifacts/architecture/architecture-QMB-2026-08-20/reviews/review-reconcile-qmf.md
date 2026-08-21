# QMB Spine Review — Lens: Reconcile vs Parent (QMF AD-1..41)

Reviewer gate, DRAFT QMB spine. Read against the binding, read-only QMF parent
spine (AD-1..41). Question for every B-id: does it weaken, contradict, or
quietly re-decide an inherited AD?

## Verdict

The QMB spine reconciles cleanly with the QMF parent. No B-id genuinely
contradicts or silently re-decides an inherited AD — the hard cases are handled
with visible care (the frontier clock explicitly disclaims AD-8's monotonic
kind; 12–14 runs is declared a motivating reference under AD-13, exactly as the
parent's own ~40-bot number; provenance-derived world *strengthens* AD-12's
anti-relabel rule; the seal and rooms are respected; refusals return-not-raise
per AD-11). Every finding below is a B-id wording or placement amendment, not a
parent-conflict for the operator to rule on. The most material is a recurring
bare-"timeframe" breach of the inherited BarSpec vocabulary ban.

---

## Lens sub-questions — where the spine HOLDS

**Money path — B-6 vs AD-7.** B-6 keeps fills/slippage/costs on exact-integer
money ("itemized costs, exact-integer money"); B-10's money metrics are
exact-money; B-8/B-14 objectives read analytic-float metrics off the money path.
This is precisely AD-7's taint model (integers on the money path, analytic
floats permitted off it). No carve-out is abused. Holds. B-6's forex cost
vocabulary ("financing/admin fee ... 'swap' only colloquially") matches AD-8's
swap-Wednesday drop and AD-41's `cost_components` exactly. Holds.

**Clock — B-2 vs AD-8.** The frontier clock "emits AD-8 wall/replay Instants —
it is NOT AD-8's monotonic diagnostic clock kind." AD-8 permits exactly this:
"replay injects a data-driven one." The "monotonically non-decreasing" advance
is the clock's behavior, not a claim to be AD-8's monotonic *kind* — B-2
disclaims that explicitly. Slice sub-phase/instrument ordering is the
`(instant, writer, sequence)` tie-break device AD-8 mandates. No new clock kind
is minted. Holds.

**Worlds — B-7 vs AD-12 (operator-flagged).** Deriving world from data
provenance is COMPATIBLE with AD-12's label semantics — it is a strengthening,
not a change. AD-12 already correlates world with data nature (replay = recorded
history; simulated = synthetic data); it defines the three worlds but never says
world is caller-declared. B-7 makes the assignment tamper-proof at the store
level, which *serves* AD-12's rule that "a non-live world may never write into
the live evidence namespace" and closes the synthetic backdoor (L20). B-7 keeps
world=simulated a `policy rejection` for governed evidence until GAP-0048,
matching AD-12's "reserved but unusable in V1." Perturbed-real (block-bootstrap)
data stays synthetic-origin → world=simulated, correctly. Not a re-decision of
AD-12 — a mechanical enforcement of it.

**Rooms / seal — B-9 / B-11 vs AD-19 / AD-21.** B-9 keeps governed/sealed
evidence in controlled rooms and the seal's one final look write-gated on the
controlled side — AD-21's 12-month no-peek lock and one logged final look
verbatim. B-11's data commands are thin fronts over CT-10/CT-15 intake, rooms,
bitemporal law, bid+ask preserved, world-scoped rooms — all AD-19/AD-21.
Naming "Dukascopy primary" is NOT an AD-9 broker-in-architecture breach:
Dukascopy is a read-only *source* (AD-19's source-vs-venue split), and the
parent itself names it as the history source in AD-21. Holds.

**Concurrency — B-5 vs AD-15.** Process-per-run with WriterId-scoped append
streams, no threads/daemon, is AD-15's stance (application owns concurrency,
one-writer-per-stream). QMB-as-application (L21) is exactly the layer AD-15
allows to own concurrency. Holds in principle — see Finding 4 for the one
placement gap.

**Refusals — Conventions vs AD-11.** "The Python door RETURNS the library's
refusal unions verbatim (AD-11 return-not-raise; exceptions only for programmer
error)" is AD-11's mechanism verbatim. QMB coins no new refusal category; it
reuses the closed set (policy rejection, unavailable dependency, invalid input,
etc.). Holds.

**Benchmarks — 12–14 target vs AD-13.** A named target is NOT an AD-13
violation when framed as a motivating reference — AD-13 itself uses "~40-bot ...
10/100/200 marks" that way. B-5: "a motivating reference under AD-13, never a
validated budget until a fingerprinted baseline is measured." Textbook-correct.
Holds.

**Registry kinds for config fragments — B-3 vs AD-16.** Answering the operator's
direct question: NO, config fragments do not need a registry kind minted. B-3's
"never a newly minted registry kind" is correct and AD-16-consistent — fragments
are derived data artifacts (like a compiled output), not registry record kinds.
See Finding 6 for the one imprecise word in how their provenance is described.

---

## Findings (most severe first)

### F1 — HIGH — Bare "timeframe"/"resolution" breaches the inherited BarSpec vocabulary ban (AD-22)

QMB's Conventions declare the bans "inherited in full," yet the spine uses the
banned bare word "timeframe" (and its sibling "resolution") repeatedly where the
parent mandates BarSpec:

- **B-12:** "instrument + **timeframe** list, trading vs data-only roles" and
  "bot × symbols × **timeframes** × parameters".
- **B-8:** "Jesse's naive-random-search" section and B-12 cross-ref use
  "**timeframes**".
- **B-11:** "Data addressing follows (venue, symbol) + **resolution** +
  world-scoped rooms".
- **Capability map:** "Multi-**TF** / multi-symbol permutations".

AD-22 is explicit: "`BarSpec` replaces the bare word 'timeframe' everywhere ...
a bar series is well-defined only via its BarSpec." The parent Conventions row
bans it: "`BarSpec`, never bare 'timeframe'." This is the exact drift AD-22
exists to prevent — a bar series identified by a bare word carries no aggregation
rule or anchoring calendar, so two implementers slice "the 1h timeframe"
differently from identical ticks. QMB's own banned list ("engine, kernel, exam,
plugins, fake counterparty") omits BarSpec, so the inheritance is asserted but
not enforced in the text.

**Classification:** B-id amendment, not a parent conflict. Fix: replace every
bare "timeframe"/"resolution"/"TF" with BarSpec across B-8, B-11, B-12 and the
Capability map, and add "bare 'timeframe'/'resolution' (use BarSpec)" to QMB's
explicit banned-vocabulary list.

### F2 — MEDIUM — `name@version` resolution risks colliding with AD-30's "cite by fingerprint, never a version string"

B-13 says "Books and bots are resolved **name@version** from the registry — the
npm-shaped half of distribution"; B-3 and the sequence diagram show
`--book scalping@2` and "resolve Book/BMS fragments (name@version)." AD-30 is
categorical: "A binding cites a Book definition by **fingerprint**, never a
version string," and AD-29 has CT-32 populations "cite binding-record
fingerprints, never intervals." B-13's label section is correct (it carries
"Book/BMS fragment fingerprints"), so the intent is npm-style — name@version is a
resolution *handle* that resolves to an fp1. But the spine never states that
name@version is a non-identity handle whose resolved fp1 alone enters the binding
and the result label. Left implicit, an implementer could store "scalping@2" as
the binding reference and quietly violate AD-30 (the very version-string-in-
identity trap AD-30 inverts the legacy pointer rule to kill).

**Classification:** B-id clarification, not a parent conflict. Fix: state in B-3
/ B-13 that name@version is a door-facing resolution handle only; the resolved
`fp1` is the identity that enters the binding, the ledger key and the result
label (AD-30/AD-10).

### F3 — MEDIUM — B-4's "verdict vs the Book's bar" needs an explicit world/role firewall so a world=replay result is never read as satisfying a live-gating admission bar

B-4 has each run append a verdict "pass/fail against the Book's declared bar."
QMB runs are world=replay (and world=simulated, deferred). AD-12 and AD-29 make
replay and live evidence "deliberately incomparable by binding"; AD-32 admission
is technical + operator-signed, with each bar's `evidence_requirements` declaring
world and account role, and "No paper role may gate live money." A world=replay
backtest passing a Book's bar is published evidence — it must not by itself
satisfy a bar that gates a `role = live` binding. Today QMB is safe because all
admission-bar thresholds are "not yet ruled" (deferred to GAP-0048/0049) and B-4
returns `unrated` for them — so no live gating is possible yet. But the spine
should say so, or B-4's "verdict against the Book bar" can later be misread as an
admission gate once thresholds are ruled.

**Classification:** design caution to surface (and hand to the GAP-0048 sitting),
not a live conflict. Fix: a B-4 note that a QMB replay/simulated verdict is
published measurement evidence only, satisfying a live-gating admission bar
solely where that bar's `evidence_requirements` declare the run's world/role as
acceptable (AD-12/AD-29/AD-32); the backtesting sitting owns the rule.

### F4 — MEDIUM — B-5's process spawner has no home outside the pure library, in tension with the inherited AD-15 row and B-1

B-5 makes concurrent runs "separate OS processes (stdlib process management)"
but never locates the *spawner*. The inherited table restates AD-15 as "The
library never spawns threads/background work"; B-1 says doors are thin and carry
"no domain logic" (only "parsing, transport, refusal rendering, registry
enumeration"). Process orchestration (launch 12–14 runs, isolate output dirs,
reap) is neither a pure-library function nor thin-door adaptation logic. It
appears only once, in the Capability map ("doors/cli + process runner"), and has
no structural-seed module. Left unplaced, the runner either lands in the pure
library (contradicting the inherited AD-15 row) or bloats a door B-1 says must
stay thin.

**Classification:** B-id/structural amendment. Fix: name an explicit non-library
orchestration seam (QMB-as-application owns concurrency per AD-15/L21) — a
`runner/` or `orchestrator/` module distinct from `runloop/` and from the thin
doors — so the "library never spawns" row stays true and B-1's thin-door rule is
not the runner's accidental home.

### F5 — LOW — B-10 "unit-kinded exact-money metrics" understates the analytic-float metric class AD-41 governs

B-10 says every run emits "unit-kinded **exact-money** metrics (the named metric
set, versioned)." Not all metrics are exact-money: a Sharpe or a drawdown *ratio*
is a dimensionless analytic float. AD-41 rules these explicitly — "a Sharpe or a
drawdown takes **label-derived identity** (AD-10), never a hash of float bytes" —
and AD-40's unit-kind vocabulary includes `dimensionless-ratio`. B-10's phrasing
reads as if the whole metric set is exact-money, dropping the float-discipline
half AD-41 requires.

**Classification:** B-id wording. Fix: B-10 should note that money metrics are
exact-integer while float-analytic metrics (ratios, Sharpe, drawdown ratios)
carry AD-40 unit-kinds and take AD-10/AD-41 label-derived identity, off the
money path (AD-7).

### F6 — LOW — B-3 calls fragment provenance "AD-16 lineage edges" where the mechanism is input-fingerprint lineage

B-3: fragments "carry AD-16 lineage edges back to their source Book/BMS
definitions (CT-22/CT-27)." AD-16's enumerated edge kinds (supersedes,
promoted-from, occurrence-of, corroborates, disagrees-with, confirmed-as,
continues-performance, carries-ledger, enacts, branches-from) contain no
"derived-from"/"compiled-from" kind. The natural, already-ratified provenance for
a derived config artifact is input-fingerprint lineage — the fragment cites the
Book/BMS definition fingerprint as an identity-bearing input (AD-10/AD-12), which
AD-5 calls generically "a lineage edge to the old one." The claim is
substantively fine (and "never a newly minted registry kind" is correct), but
"AD-16 lineage edges" invites an implementer to mint a new edge kind (an
amendment) rather than lean on input-fingerprint identity.

**Classification:** B-id wording. Fix: describe fragment provenance as
input-fingerprint lineage (the derived artifact citing the CT-22/CT-27
fingerprint), or, if a named derivation edge is truly wanted, flag it as a parent
edge-kind amendment rather than an existing AD-16 edge.

---

## Not findings (checked, clean)

- B-2 frontier clock is not a new AD-8 clock kind (wall/replay, disclaims
  monotonic). Clean.
- B-7 world-derivation strengthens rather than re-decides AD-12. Clean.
- 12–14 concurrent runs as an AD-13 motivating reference. Clean (mirrors the
  parent's own ~40-bot number).
- Optuna/click as dependencies: not "donor code" (D1/DEC-0084), not
  strategy-family libs, permissive licences, wrapped behind QMB ports; qmf-core
  stays zero-dep (AD-6). Clean.
- "Dukascopy primary" is a source, not a broker-in-architecture (AD-9 vs AD-19
  source split; AD-21 names it too). Clean.
- Refusal categories, return-not-raise, financing/admin-fee vocabulary, seal,
  bid+ask, world-scoped rooms: all match parent. Clean.
- No use of "engine", "kernel", "exam", or "plugins" for QMB parts — the spine
  deliberately uses "tunnel"/"run loop"/"ports"/"adapters". Clean (the one
  vocabulary slip is F1's timeframe/BarSpec).
